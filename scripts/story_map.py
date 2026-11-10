#!/usr/bin/env python3
"""story_map.py — the user story map's note: parse, check, render, progress, baseline, board diff
(references/story-map-protocol.md, since v4.6.0).

  parse        the card table of the note as activities → steps, cards, slices, gap rows and a layout
  check        the script's findings of the protocol's quality rule (§3), each with its card
  render-html  one self-contained HTML page of the map: no request, no link, every text escaped, light theme
  progress     per slice: the status spread, % done, what is blocked, added / removed / moved against the baseline
  baseline     a slice's baseline into the frontmatter field `baseline` — every other byte of the note kept
  board-diff   a board's last state against a read-back, by data-miro-id: changed, moved, added, removed
  schema       the fields, columns, findings, statuses and commands the protocol must agree with (check 26)

The note is the source of truth: a markdown table of cards under its frontmatter (`product`, `epic`, `slices`,
`baseline`, `published`). The frontmatter field is written through publications.write_field — the same code that
writes `published` — so a field is replaced and nothing else moves. Every command ends with one
`MAP_RESULT {json}` line. Stdlib only (Python 3.9). Exit 0; 2 for a wrong argument or a note, a status file or a board
that does not read; 1 when a file cannot be written.
"""
import argparse, datetime, html, json, os, re, sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ctx_common as cc  # noqa: E402
import publications as pub  # noqa: E402

FIELDS = ("product", "epic", "slices", "baseline", "published")
COLUMNS = (("id", "id"), ("activity", "діяльність"), ("step", "крок"), ("card", "картка"), ("slice", "зріз"),
           ("feature", "фіча"), ("epic", "епік"), ("source", "джерело"), ("edge_of", "edge_of"))
REQUIRED = ("id", "activity", "step", "card")
FINDINGS = ("subitem", "work_type", "skeleton_gap", "no_outcome", "no_step", "no_source", "duplicate_id",
            "edge_unknown", "edge_other_step", "unknown_slice", "bad_code", "empty_step")
STATUSES = ("done", "in_progress", "planned", "blocked")
COMMANDS = ("parse", "check", "render-html", "progress", "baseline", "board-diff", "schema")

SUBITEM = re.compile(r"<br\s*/?>|•|[:;]\s*[-*]\s+\S", re.I)
WORK_TYPE = re.compile(r"^\s*[\[(]?(?:FE|BE|QA|iOS|Android|Design|DevOps)[\])]?\s*[:\-–—]\s")
FEATURE_CODE = re.compile(r"^([A-Z][A-Z0-9]*-\d+)((?:\.\d+)+)$")
EPIC_KEY = re.compile(r"^[A-Z][A-Z0-9]*-\d+$")
SLICE_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,31}$")
DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MOVE_EPS = 5.0
SCOPE_MARGIN = 200


def result(**kw):
    print("MAP_RESULT " + json.dumps(kw, ensure_ascii=False))


class Bad(Exception):
    """A note, a status file or a board that does not read — exit 2."""


# ------------------------------------------------------------------ the note
def _fm_scalar(fm, name):
    m = re.search(r"^%s[ \t]*:[ \t]*(.*?)[ \t]*$" % re.escape(name), fm, re.M)
    if not m:
        return ""
    try:
        v = cc._scalar(cc._strip_comment(m.group(1)), 0)
    except (ValueError, json.JSONDecodeError):
        return ""
    return str(v).strip() if isinstance(v, (str, int)) else ""


def _cells(line):
    """The cells of one markdown table row; `\\|` is a pipe inside a cell."""
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|") and not s.endswith("\\|"):
        s = s[:-1]
    return [c.replace("\\|", "|").strip() for c in re.split(r"(?<!\\)\|", s)]


def _canon(header):
    h = header.strip().strip("`*_ ").lower()
    for name, uk in COLUMNS:
        if h in (name, uk, name.replace("_", " ")):
            return name
    return None


def _tables(body):
    """[(first line number, [lines])] — every run of lines that starts with `|`."""
    out, cur, start = [], [], 0
    for i, line in enumerate(body.split("\n")):
        if line.strip().startswith("|"):
            if not cur:
                start = i
            cur.append(line.rstrip("\r"))
        elif cur:
            out.append((start, cur))
            cur = []
    if cur:
        out.append((start, cur))
    return out


def load(path):
    """The note as a dict — raises Bad."""
    try:
        with open(path, encoding="utf-8", newline="") as f:
            text = f.read()
    except OSError as e:
        raise Bad("the note does not read: %s" % (e.strerror or type(e).__name__))
    span = pub._frontmatter(text)
    if not span:
        raise Bad("the note has no frontmatter")
    start, end, _ = span
    fm = text[start:end].replace("\r\n", "\n")
    try:
        slices = cc.read_yaml_records(fm, "slices")
        baseline = cc.read_yaml_records(fm, "baseline")
    except ValueError as e:
        raise Bad("the frontmatter does not read: %s" % e)
    body = text[end:].replace("\r\n", "\n")
    title = ""
    m = re.search(r"^# (.+)$", body, re.M)
    if m:
        title = m.group(1).strip()
    table, cols = None, None
    for _, lines in _tables(body):
        names = [_canon(h) for h in _cells(lines[0])]
        if all(r in names for r in REQUIRED):
            table, cols = lines, names
            break
    if table is None:
        raise Bad("no card table: a table whose header has %s" % ", ".join(REQUIRED))
    rows, errors = [], []
    for n, line in enumerate(table[1:], 2):
        cells = _cells(line)
        if all(re.fullmatch(r":?-{3,}:?", c) for c in cells if c):
            continue
        if len(cells) != len(cols):
            errors.append("row %d (%s): %d cells, the header has %d" % (n, cells[0] if cells else "?", len(cells), len(cols)))
            continue
        row = {name: "" for name, _ in COLUMNS}
        for name, val in zip(cols, cells):
            if name:
                row[name] = val
        row["row"] = n
        rows.append(row)
    sl = []
    for s in slices:
        sid = str(s.get("slice") or "").strip()
        if sid:
            sl.append({"slice": sid, "outcome": str(s.get("outcome") or "").strip(), "label": str(s.get("label") or "").strip()})
    bl = []
    for b in baseline:
        cards = b.get("cards") or []
        bl.append({"slice": str(b.get("slice") or ""), "date": str(b.get("date") or ""),
                   "cards": [str(c) for c in (cards if isinstance(cards, list) else [cards])]})
    return {"path": path, "text": text, "title": title, "product": _fm_scalar(fm, "product"),
            "epic": _fm_scalar(fm, "epic"), "slices": sl, "baseline": bl, "rows": rows, "errors": errors}


def _is_gap(card):
    return not card or card.startswith("⚠")


def parse(note):
    """The parse of a loaded note: activities, steps, cards, gaps, layout."""
    acts, steps_of, cards, gaps = [], {}, [], []
    rank = {}
    for r in note["rows"]:
        a, s = r["activity"], r["step"]
        if a and s:
            if a not in steps_of:
                acts.append(a)
                steps_of[a] = []
            if s not in steps_of[a]:
                steps_of[a].append(s)
        if _is_gap(r["card"]):
            gaps.append({"row": r["row"], "activity": a, "step": s, "card": r["card"]})
            continue
        if not r["id"]:
            note["errors"].append("row %d: a card without an id" % r["row"])
            continue
        rank[(a, s)] = rank.get((a, s), 0) + 1
        cards.append({"id": r["id"], "activity": a, "step": s, "card": r["card"], "slice": r["slice"],
                      "feature": r["feature"], "epic": r["epic"] or note["epic"], "source": r["source"],
                      "edge_of": r["edge_of"], "rank": rank[(a, s)], "row": r["row"]})
    columns = [{"activity": a, "step": s} for a in acts for s in steps_of[a]]
    col_ix = {(c["activity"], c["step"]): i for i, c in enumerate(columns)}
    known = [s["slice"] for s in note["slices"]]
    bands = [{"slice": s["slice"], "outcome": s["outcome"], "cells": [[] for _ in columns]} for s in note["slices"]]
    bands.append({"slice": "", "outcome": "", "cells": [[] for _ in columns]})
    seen = set()
    for c in cards:
        if c["id"] in seen or (c["activity"], c["step"]) not in col_ix:
            continue
        seen.add(c["id"])
        b = known.index(c["slice"]) if c["slice"] in known else len(known)
        bands[b]["cells"][col_ix[(c["activity"], c["step"])]].append(c["id"])
    return {"title": note["title"], "product": note["product"], "epic": note["epic"],
            "activities": [{"name": a, "steps": steps_of[a]} for a in acts], "slices": note["slices"],
            "baseline": note["baseline"], "cards": cards, "gaps": gaps,
            "layout": {"columns": columns, "bands": bands}, "errors": note["errors"]}


def findings(p):
    out = []

    def f(code, **kw):
        out.append(dict(finding=code, **kw))
    known = [s["slice"] for s in p["slices"]]
    for s in p["slices"]:
        if not s["outcome"] or "TBD" in s["outcome"]:
            f("no_outcome", slice=s["slice"], detail="a slice without a metric and a target")
    ids, where = set(), {}
    for c in p["cards"]:
        if c["id"] in ids:
            f("duplicate_id", card=c["id"], detail="row %d repeats the id" % c["row"])
        else:
            ids.add(c["id"])
            where[c["id"]] = (c["activity"], c["step"])
    for c in p["cards"]:
        if SUBITEM.search(c["card"]):
            f("subitem", card=c["id"], detail="a sub-item inside the card")
        if WORK_TYPE.search(c["card"]):
            f("work_type", card=c["id"], detail="a card named by a type of work")
        if not c["activity"] or not c["step"]:
            f("no_step", card=c["id"], detail="a card without its activity or step")
        if not c["source"]:
            f("no_source", card=c["id"], detail="a card without a source marker")
        if c["edge_of"]:
            if c["edge_of"] not in where:
                f("edge_unknown", card=c["id"], detail="edge_of %s names no card" % c["edge_of"])
            elif where[c["edge_of"]] != (c["activity"], c["step"]):
                f("edge_other_step", card=c["id"], detail="its card %s is under another step" % c["edge_of"])
        if c["slice"] and c["slice"] not in known:
            f("unknown_slice", card=c["id"], slice=c["slice"], detail="a slice the frontmatter does not declare")
        if c["feature"]:
            m = FEATURE_CODE.match(c["feature"])
            if not m:
                f("bad_code", card=c["id"], detail="feature %s does not parse" % c["feature"])
            elif c["epic"] and EPIC_KEY.match(c["epic"]) and m.group(1) != c["epic"]:
                f("bad_code", card=c["id"], detail="feature %s is not of epic %s" % (c["feature"], c["epic"]))
        if c["epic"] and not EPIC_KEY.match(c["epic"]):
            f("bad_code", card=c["id"], detail="epic %s does not parse" % c["epic"])
    first = known[0] if known else None
    for a in p["activities"]:
        if first and not any(c["activity"] == a["name"] and c["slice"] == first for c in p["cards"]):
            f("skeleton_gap", activity=a["name"], slice=first, detail="an activity with no card in the first slice")
    for g in p["gaps"]:
        f("empty_step", activity=g["activity"], step=g["step"], detail="a step with no card yet")
    return out


# ------------------------------------------------------------------ statuses and progress
def load_status(path):
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError) as e:
        raise Bad("the status file does not read: %s" % (getattr(e, "strerror", None) or type(e).__name__))
    feats = data.get("features") if isinstance(data, dict) else None
    if not isinstance(feats, dict):
        raise Bad("the status file has no `features` mapping")
    wrong = sorted("%s=%s" % (k, v) for k, v in feats.items() if v not in STATUSES)
    if wrong:
        raise Bad("not a canon of planning-core.md §3 (normalize first): %s" % ", ".join(wrong[:5]))
    return {"source": str(data.get("source") or ""), "date": str(data.get("date") or ""),
            "features": {str(k): v for k, v in feats.items()}}


def card_status(c, st):
    if not c["feature"]:
        return "planned"
    return st["features"].get(c["feature"], "unknown")


def progress(p, st):
    known = [s["slice"] for s in p["slices"]]
    now_slice = {}
    for c in p["cards"]:
        now_slice.setdefault(c["id"], c["slice"] if c["slice"] in known else "")
    base = {b["slice"]: b for b in p["baseline"]}
    base_of = {}
    for b in p["baseline"]:
        for cid in b["cards"]:
            base_of.setdefault(cid, b["slice"])
    out = []
    for s in p["slices"]:
        sid = s["slice"]
        mine = [c for c in p["cards"] if c["slice"] == sid]
        spread = {k: 0 for k in STATUSES + ("unknown",)}
        blocked = []
        for c in mine:
            k = card_status(c, st) if st else "planned"
            spread[k] += 1
            if k == "blocked":
                blocked.append({"id": c["id"], "card": c["card"], "feature": c["feature"]})
        row = {"slice": sid, "outcome": s["outcome"], "cards": len(mine), "spread": spread if st else None,
               "done_pct": (round(100.0 * spread["done"] / len(mine)) if mine else 0) if st else None,
               "blocked": blocked, "baseline": None, "added": [], "moved_in": [], "moved_out": [], "removed": [],
               "growth_pct": None}
        b = base.get(sid)
        if b:
            ids_now = [c["id"] for c in mine]
            ids_base = b["cards"]
            row["baseline"] = {"date": b["date"], "cards": len(ids_base)}
            row["added"] = [i for i in ids_now if i not in ids_base]
            row["moved_in"] = [{"id": i, "from": base_of[i]} for i in row["added"] if base_of.get(i) not in (None, sid)]
            for i in ids_base:
                if i in ids_now:
                    continue
                cur = now_slice.get(i)
                if cur:
                    row["moved_out"].append({"id": i, "to": cur})
                else:
                    row["removed"].append({"id": i, "now": "backlog" if i in now_slice else "gone"})
            row["growth_pct"] = round(100.0 * len(row["added"]) / len(ids_base)) if ids_base else None
        out.append(row)
    backlog = sum(1 for c in p["cards"] if not (c["slice"] in known))
    return out, backlog


# ------------------------------------------------------------------ html
LABELS = {
    "uk": {"title": "Мапа історій", "backlog": "Беклог", "note": "Нотатка", "status": "Статуси",
           "no_status": "статусів немає — прогрес не показано", "generated": "Згенеровано",
           "done": "готово", "in_progress": "у роботі", "planned": "заплановано", "blocked": "заблоковано",
           "unknown": "невідомо ⚠️", "edge": "крайній випадок", "gap": "немає картки", "progress": "Прогрес",
           "blocked_list": "Заблоковано", "growth": "після базової лінії", "cards": "карток", "no_outcome": "⚠️ TBD"},
    "en": {"title": "Story map", "backlog": "Backlog", "note": "Note", "status": "Statuses",
           "no_status": "no status data — progress not shown", "generated": "Generated",
           "done": "done", "in_progress": "in progress", "planned": "planned", "blocked": "blocked",
           "unknown": "unknown ⚠️", "edge": "edge case", "gap": "no card", "progress": "Progress",
           "blocked_list": "Blocked", "growth": "since the baseline", "cards": "cards", "no_outcome": "⚠️ TBD"},
}
CSS = """:root{color-scheme:light}
*{box-sizing:border-box}body{margin:0;padding:24px;background:#f7f7f5;color:#1f2328;font:14px/1.4 -apple-system,"Segoe UI",Roboto,Arial,sans-serif}
h1{font-size:20px;margin:0 0 4px}.meta{color:#57606a;margin:2px 0}
.wrap{overflow-x:auto;margin-top:16px}table.map{border-collapse:separate;border-spacing:6px}
th,td{vertical-align:top}th.act{background:#ffd8a8;border-radius:6px;padding:6px 8px;text-align:left}
th.step{background:#d0ebff;border-radius:6px;padding:6px 8px;text-align:left;min-width:170px;font-weight:600}
th.band{width:190px;text-align:left;padding:8px;background:#fff;border-left:4px solid #868e96;border-radius:4px;font-weight:400}
th.band .s{font-weight:700;text-transform:uppercase}th.band .o{color:#57606a;font-size:12px}th.band .p{font-size:12px;margin-top:4px}
tr.slice td{border-top:2px dashed #ced4da;padding-top:8px}
.card{background:#fff3bf;border-radius:6px;padding:6px 8px;margin-bottom:6px;border-left:4px solid #adb5bd;max-width:220px}
.card .m{color:#57606a;font-size:11px;margin-top:2px}.card.edge{margin-left:14px}
.card.gap{background:#fff;border:1px dashed #e8590c;color:#e8590c}
.st-done{border-left-color:#2f9e44}.st-in_progress{border-left-color:#1c7ed6}.st-planned{border-left-color:#adb5bd}
.st-blocked{border-left-color:#e03131}.st-unknown{border-left-color:#f08c00}
table.prog{border-collapse:collapse;margin-top:16px;background:#fff}table.prog td,table.prog th{border:1px solid #dee2e6;padding:4px 8px;text-align:left}
.legend span{display:inline-block;margin-right:12px;padding-left:6px;border-left:4px solid}"""


def esc(s):
    return html.escape(str(s), quote=True)


def render_html(p, st, prog, backlog, note_name, lang):
    L = LABELS.get(lang, LABELS["en"])
    cols = p["layout"]["columns"]
    byid = {}
    for c in p["cards"]:
        byid.setdefault(c["id"], c)
    out = ["<!doctype html>", '<html lang="%s"><head><meta charset="utf-8">' % esc(lang),
           '<meta name="viewport" content="width=device-width,initial-scale=1">',
           "<title>%s — %s</title><style>%s</style></head><body>" % (esc(L["title"]), esc(p["title"] or note_name), CSS),
           "<h1>%s: %s</h1>" % (esc(L["title"]), esc(p["title"] or note_name)),
           '<p class="meta">%s: %s · %s · %s</p>' % (esc(L["note"]), esc(note_name), esc(p["product"]), esc(p["epic"]))]
    if st:
        out.append('<p class="meta">%s: %s · %s</p>' % (esc(L["status"]), esc(st["source"]), esc(st["date"])))
    else:
        out.append('<p class="meta">%s: %s</p>' % (esc(L["status"]), esc(L["no_status"])))
    out.append('<p class="meta">%s: %s</p>' % (esc(L["generated"]), esc(datetime.date.today().isoformat())))
    out.append('<div class="wrap"><table class="map"><thead><tr><th></th>')
    for a in p["activities"]:
        out.append('<th class="act" colspan="%d">%s</th>' % (len(a["steps"]), esc(a["name"])))
    out.append("</tr><tr><th></th>")
    for c in cols:
        out.append('<th class="step">%s</th>' % esc(c["step"]))
    out.append("</tr></thead><tbody>")
    gaps = {(g["activity"], g["step"]) for g in p["gaps"]}
    pr = {r["slice"]: r for r in prog}
    for bi, band in enumerate(p["layout"]["bands"]):
        sid = band["slice"]
        if sid:
            r = pr.get(sid, {})
            head = '<div class="s">%s</div><div class="o">%s</div>' % (esc(sid), esc(band["outcome"] or L["no_outcome"]))
            line = "%d %s" % (r.get("cards", 0), L["cards"])
            if st and r.get("done_pct") is not None:
                line += " · %s %d%%" % (L["done"], r["done_pct"])
            if r.get("growth_pct") is not None:
                line += " · +%d %s (%d%%)" % (len(r["added"]), L["growth"], r["growth_pct"])
            head += '<div class="p">%s</div>' % esc(line)
        else:
            head = '<div class="s">%s</div><div class="o">%d %s</div>' % (esc(L["backlog"]), backlog, esc(L["cards"]))
        out.append('<tr class="slice"><th class="band">%s</th>' % head)
        for ci, cell in enumerate(band["cells"]):
            out.append("<td>")
            for cid in cell:
                c = byid[cid]
                k = card_status(c, st) if st else "planned"
                cls = "card st-%s%s" % (k, " edge" if c["edge_of"] else "")
                meta = " · ".join(x for x in (c["feature"], c["source"], (L["edge"] + " " + c["edge_of"]) if c["edge_of"] else "",
                                              L[k] if st else "") if x)
                out.append('<div class="%s"><div class="t">%s</div><div class="m">%s</div></div>' % (cls, esc(c["card"]), esc(meta)))
            col = cols[ci]
            if bi == 0 and (col["activity"], col["step"]) in gaps:
                out.append('<div class="card gap">⚠️ %s</div>' % esc(L["gap"]))
            out.append("</td>")
        out.append("</tr>")
    out.append("</tbody></table></div>")
    if st:
        out.append("<h2>%s</h2><table class=\"prog\"><tr><th></th>" % esc(L["progress"]))
        for k in STATUSES + ("unknown",):
            out.append("<th>%s</th>" % esc(L[k]))
        out.append("<th>%%</th><th>%s</th><th>%s</th></tr>" % (esc(L["blocked_list"]), esc(L["growth"])))
        for r in prog:
            out.append("<tr><td>%s</td>" % esc(r["slice"]))
            for k in STATUSES + ("unknown",):
                out.append("<td>%d</td>" % r["spread"][k])
            g = "" if r["growth_pct"] is None else "+%d (%d%%)" % (len(r["added"]), r["growth_pct"])
            out.append("<td>%d%%</td><td>%s</td><td>%s</td></tr>" % (
                r["done_pct"], esc(", ".join("%s %s" % (b["id"], b["card"]) for b in r["blocked"])), esc(g)))
        out.append("</table>")
    out.append('<p class="legend meta">%s</p>' % "".join(
        '<span class="st-%s">%s</span>' % (k, esc(L[k])) for k in STATUSES + ("unknown",)))
    out.append("</body></html>")
    return "\n".join(out) + "\n"


# ------------------------------------------------------------------ baseline
def render_baseline(entries, eol):
    lines = ["baseline:"]
    for b in entries:
        lines.append("  - slice: %s" % b["slice"])
        lines.append("    date: %s" % json.dumps(b["date"]))
        lines.append("    cards: [%s]" % ", ".join(json.dumps(c, ensure_ascii=False) for c in b["cards"]))
    return eol.join(lines) + eol


# ------------------------------------------------------------------ board
def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _translate(tr):
    m = re.search(r"translate\(\s*([-\d.eE]+)(?:[\s,]+([-\d.eE]+))?\s*\)", tr or "")
    if m:
        return float(m.group(1)), float(m.group(2) or 0)
    m = re.search(r"matrix\(([^)]*)\)", tr or "")
    if m:
        parts = [float(x) for x in re.split(r"[\s,]+", m.group(1).strip()) if x]
        if len(parts) == 6:
            return parts[4], parts[5]
    return 0.0, 0.0


def _plain(s):
    s = re.sub(r"<br\s*/?>|</p>\s*<p[^>]*>", " ", s or "", flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def _own_text(el):
    parts = [el.text or ""]
    for ch in el:
        if ch.get("data-miro-id") is None:
            parts.append(_own_text(ch))
        parts.append(ch.tail or "")
    return "".join(parts)


def read_board(path):
    """{id: item} of the elements of a board SVG that carry a data-miro-id — raises Bad."""
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError) as e:
        raise Bad("the board does not read: %s" % (getattr(e, "strerror", None) or str(e)[:120]))
    items = {}

    def walk(el, ox, oy, frame, frame_text):
        tag = el.tag.split("}")[-1]
        dx, dy = _translate(el.get("transform")) if tag == "g" else (0.0, 0.0)
        nox, noy = ox + dx, oy + dy
        mid = el.get("data-miro-id")
        is_frame = tag == "g" and el.get("data-frame") is not None
        if is_frame:
            rect = next((c for c in el if c.get("data-type") == "frame"), None)
            title = el.get("data-frame") or (rect.get("data-title") if rect is not None else "") or ""
            mid = mid or (rect.get("data-miro-id") if rect is not None else None)
            w = _num(rect.get("width")) if rect is not None else None
            h = _num(rect.get("height")) if rect is not None else None
            if mid:
                items[mid] = {"id": mid, "kind": "frame", "text": _plain(title), "x": nox, "y": noy, "w": w, "h": h,
                              "frame": frame, "frame_text": frame_text}
            for c in el:
                if c is not rect:
                    walk(c, nox, noy, mid or frame, _plain(title) if mid else frame_text)
            return
        if mid and el.get("data-type") != "frame":
            x = _num(el.get("x")) if el.get("x") is not None else _num(el.get("cx"))
            y = _num(el.get("y")) if el.get("y") is not None else _num(el.get("cy"))
            text = el.get("data-content")
            if text is None:
                text = el.get("data-title") or _own_text(el)
            items[mid] = {"id": mid, "kind": el.get("data-type") or tag, "text": _plain(text),
                          "x": (x or 0.0) + nox, "y": (y or 0.0) + noy, "w": _num(el.get("width")),
                          "h": _num(el.get("height")), "frame": frame, "frame_text": frame_text}
        for c in el:
            walk(c, nox, noy, frame, frame_text)

    walk(root, 0.0, 0.0, None, "")
    return items


def _scope(items):
    xs, ys, xe, ye = [], [], [], []
    for it in items.values():
        xs.append(it["x"]); ys.append(it["y"])
        xe.append(it["x"] + (it["w"] or 0)); ye.append(it["y"] + (it["h"] or 0))
    if not xs:
        return None
    x0, y0 = int(min(xs)) - SCOPE_MARGIN, int(min(ys)) - SCOPE_MARGIN
    return {"x": x0, "y": y0, "width": int(max(xe)) + SCOPE_MARGIN - x0, "height": int(max(ye)) + SCOPE_MARGIN - y0}


def _card_of(text, cards):
    t = _plain(text)
    for c in cards:
        if t in (_plain(c["card"]), _plain((c["card"] + " " + c["feature"]).strip())):
            return c["id"]
    return None


def board_diff(last, now, cards):
    changed, moved, added, removed = [], [], [], []
    for mid, it in now.items():
        old = last.get(mid)
        if old is None:
            added.append({"id": mid, "kind": it["kind"], "text": it["text"], "at": [round(it["x"]), round(it["y"])],
                          "frame": it["frame_text"]})
            continue
        if old["text"] != it["text"]:
            changed.append({"id": mid, "kind": it["kind"], "card": _card_of(old["text"], cards), "last": old["text"],
                            "now": it["text"]})
        if abs(old["x"] - it["x"]) > MOVE_EPS or abs(old["y"] - it["y"]) > MOVE_EPS or old["frame"] != it["frame"]:
            moved.append({"id": mid, "kind": it["kind"], "card": _card_of(old["text"], cards), "text": it["text"],
                          "from": [round(old["x"]), round(old["y"])], "to": [round(it["x"]), round(it["y"])],
                          "frame_from": old["frame_text"], "frame_to": it["frame_text"]})
    for mid, old in last.items():
        if mid not in now:
            removed.append({"id": mid, "kind": old["kind"], "card": _card_of(old["text"], cards), "text": old["text"]})
    return changed, moved, added, removed


# ------------------------------------------------------------------ check 26
def _section(text, head):
    m = re.search(r"^## %s.*?(?=^## |\Z)" % re.escape(head), text, re.M | re.S)
    return m.group(0) if m else ""


def _table_after(sec, header_re):
    m = re.search(header_re + r".*?(?=\n\n|\Z)", sec, re.S)
    if not m:
        return []
    rows = []
    for line in m.group(0).split("\n")[2:]:
        if line.strip().startswith("|"):
            rows.append(_cells(line))
    return rows


def _tick(cell):
    m = re.match(r"\s*`([^`]+)`", cell or "")
    return m.group(1) if m else None


def _cmd(cell):
    m = re.match(r"\s*`([a-z-]+)", cell or "")
    return m.group(1) if m else "?"


def check_protocol(root):
    """Errors for validate-consistency.sh check 26 — the protocol, the script, planning-core's canons, the vault schema,
    the publication key and the skill's citation agree."""
    errs, texts = [], {}
    for rel in ("references/story-map-protocol.md", "references/planning-core.md", "references/vault-schema.md",
                "references/artifact-publishing.md", "skills/roadmap-architect/SKILL.md"):
        try:
            with open(os.path.join(root, rel), encoding="utf-8") as fh:
                texts[rel] = fh.read()
        except OSError:
            errs.append("%s is missing" % rel)
    if "references/story-map-protocol.md" not in texts:
        return errs
    proto = texts["references/story-map-protocol.md"]
    skill = texts.get("skills/roadmap-architect/SKILL.md", "")
    if skill and "story-map-protocol.md" not in skill:
        errs.append("skills/roadmap-architect/SKILL.md does not cite references/story-map-protocol.md")
    s4 = _section(proto, "4. The note")
    fields = [_tick(r[0]) for r in _table_after(s4, r"\| Field \| What \|")]
    if fields != list(FIELDS):
        errs.append("story-map-protocol.md §4: the frontmatter fields %s ≠ story_map.py FIELDS %s" % (
            "|".join(f or "?" for f in fields), "|".join(FIELDS)))
    cols = [(_tick(r[0]), _tick(r[1]) if len(r) > 1 else None) for r in _table_after(s4, r"\| Column \| Ukrainian header \| What \|")]
    if cols != list(COLUMNS):
        errs.append("story-map-protocol.md §4: the columns %s ≠ story_map.py COLUMNS %s" % (
            "|".join("%s/%s" % c for c in cols), "|".join("%s/%s" % c for c in COLUMNS)))
    s3 = _section(proto, "3. Quality")
    script_rows = sorted(_tick(r[0]) or "?" for r in _table_after(s3, r"\| Finding \| Who \|")
                         if len(r) > 1 and r[1].strip() == "script")
    if script_rows != sorted(FINDINGS):
        errs.append("story-map-protocol.md §3: the script's findings %s ≠ story_map.py FINDINGS %s" % (
            "|".join(script_rows), "|".join(sorted(FINDINGS))))
    s10 = _section(proto, "10. The script")
    cmds = sorted({_cmd(r[0]) for r in _table_after(s10, r"\| Command \| What \|")})
    if cmds != sorted(COMMANDS):
        errs.append("story-map-protocol.md §10: the commands %s ≠ story_map.py COMMANDS %s" % (
            "|".join(cmds), "|".join(sorted(COMMANDS))))
    pc = _section(texts.get("references/planning-core.md", ""), "3. Status normalization")
    canons = sorted(_tick(r[0]) or "?" for r in _table_after(pc, r"\| Canon \| Signals \|"))
    if canons != sorted(STATUSES):
        errs.append("planning-core.md §3: the canons %s ≠ story_map.py STATUSES %s" % (
            "|".join(canons), "|".join(sorted(STATUSES))))
    vs = texts.get("references/vault-schema.md", "")
    row = re.search(r"^\| roadmap \|.*$", vs, re.M)
    if vs and not (row and "story map" in row.group(0)):
        errs.append("vault-schema.md: the `roadmap` type row does not name the story map")
    ap = _section(texts.get("references/artifact-publishing.md", ""), "5. Publish and record")
    if texts.get("references/artifact-publishing.md") and not re.search(r"^\|\s*`roadmap-architect`\s*\|\s*`roadmap-architect/", ap, re.M):
        errs.append("artifact-publishing.md §5: the key table has no `roadmap-architect` row")
    return errs


# ------------------------------------------------------------------ commands
def _loaded(args):
    note = load(args.note)
    return note, parse(note)


def cmd_parse(args):
    _, p = _loaded(args)
    result(ok=True, **p)
    return 0


def cmd_check(args):
    _, p = _loaded(args)
    result(ok=True, findings=findings(p), errors=p["errors"])
    return 0


def cmd_render(args):
    _, p = _loaded(args)
    st = load_status(args.status) if args.status else None
    prog, backlog = progress(p, st)
    page = render_html(p, st, prog, backlog, os.path.basename(args.note), args.lang)
    try:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(page)
    except OSError as e:
        result(ok=False, error="the page cannot be written: %s" % (e.strerror or type(e).__name__))
        return 1
    result(ok=True, out=args.out, bytes=len(page.encode("utf-8")), cards=len(p["cards"]), status=bool(st))
    return 0


def cmd_progress(args):
    _, p = _loaded(args)
    st = load_status(args.status)
    prog, backlog = progress(p, st)
    result(ok=True, source=st["source"], date=st["date"], slices=prog, backlog=backlog)
    return 0


def cmd_baseline(args):
    note, p = _loaded(args)
    known = [s["slice"] for s in p["slices"]]
    if args.slice not in known:
        result(ok=False, error="the map declares no slice %r (slices: %s)" % (args.slice, ", ".join(known) or "none"))
        return 2
    day = args.date or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    if not DAY.match(day):
        result(ok=False, error="--date is not YYYY-MM-DD")
        return 2
    ids = []
    for c in p["cards"]:
        if c["slice"] == args.slice and c["id"] not in ids:
            ids.append(c["id"])
    entries = [dict(b) for b in p["baseline"] if b["slice"]]
    entry = {"slice": args.slice, "date": day, "cards": ids}
    for i, b in enumerate(entries):
        if b["slice"] == args.slice:
            entries[i] = entry
            break
    else:
        entries.append(entry)
    path, text = args.note, note["text"]
    try:
        pub.write_field(path, text, False, "baseline", lambda eol: render_baseline(entries, eol))
    except OSError as e:
        result(ok=False, error="the note cannot be written: %s" % (e.strerror or type(e).__name__))
        return 1
    result(ok=True, slice=args.slice, date=day, cards=ids)
    return 0


def cmd_board_diff(args):
    if not args.last or not os.path.isfile(args.last):
        result(ok=True, state="unknown", why="no last state of the board on this machine")
        return 0
    last = read_board(args.last)
    if not args.now:
        result(ok=True, state="scope", scope=_scope(last))
        return 0
    now = read_board(args.now)
    cards = parse(load(args.note))["cards"] if args.note else []
    changed, moved, added, removed = board_diff(last, now, cards)
    result(ok=True, state="diff", changed=changed, moved=moved, added=added, removed=removed,
           counts={"changed": len(changed), "moved": len(moved), "added": len(added), "removed": len(removed)},
           scope=_scope(last))
    return 0


def cmd_schema(args):
    result(ok=True, fields=list(FIELDS), columns=[list(c) for c in COLUMNS], findings=list(FINDINGS),
           statuses=list(STATUSES), commands=list(COMMANDS), errors=check_protocol(os.path.dirname(HERE)))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="story_map.py", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd")
    for name in ("parse", "check"):
        sub.add_parser(name).add_argument("--note", required=True)
    p = sub.add_parser("render-html")
    p.add_argument("--note", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--status")
    p.add_argument("--lang", default="en", choices=sorted(LABELS))
    p = sub.add_parser("progress")
    p.add_argument("--note", required=True)
    p.add_argument("--status", required=True)
    p = sub.add_parser("baseline")
    p.add_argument("--note", required=True)
    p.add_argument("--slice", required=True)
    p.add_argument("--date")
    p = sub.add_parser("board-diff")
    p.add_argument("--last")
    p.add_argument("--now")
    p.add_argument("--note")
    sub.add_parser("schema")
    args = ap.parse_args(argv)
    fn = {"parse": cmd_parse, "check": cmd_check, "render-html": cmd_render, "progress": cmd_progress,
          "baseline": cmd_baseline, "board-diff": cmd_board_diff, "schema": cmd_schema}.get(args.cmd)
    if fn is None:
        ap.print_help()
        return 2
    try:
        return fn(args)
    except Bad as e:
        result(ok=False, error=str(e))
        return 2


if __name__ == "__main__":
    sys.exit(main())
