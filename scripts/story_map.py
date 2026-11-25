#!/usr/bin/env python3
"""story_map.py — the user story map's note: parse, check, render, progress, baseline, board diff
(references/story-map-protocol.md, since v4.6.0).

  parse        the card table of the note as activities → steps, cards, slices, gap rows and a layout
  check        the script's findings of the protocol's quality rule (§3), each with its card
  render-html  one self-contained HTML page of the map: no request, no link, every text escaped, light theme
  progress     per slice: the status spread, % done, what is blocked, added / removed / moved against the baseline
  baseline     a slice's baseline into the frontmatter field `baseline` — every other byte of the note kept
  board-state  the board read back after a publication, kept with which sticky is which card, activity, step or slice
  board-diff   a board's last state against a read-back, by element id: card changes apart from backbone and other items;
               on the host's board a read lacking a slice section or a backbone block is `partial`, never «removed»

Both board commands read a Miro board's SVG (`--surface miro`, the default, its bytes as at v4.6.0) or, since v4.11.2,
the host's own board type's element list (`--surface whiteboard`); board-diff takes the surface from the state.
  schema       the fields, columns, findings, statuses and commands the protocol must agree with (check 26)

The note is the source of truth: a markdown table of cards under its frontmatter (`product`, `epic`, `slices`,
`baseline`, `published`). The frontmatter field is written through publications.write_field — the same code that
writes `published` — so a field is replaced and nothing else moves. Every command ends with one
`MAP_RESULT {json}` line. Stdlib only (Python 3.9). Exit 0; 2 for a wrong argument or a note, a status file or a board
that does not read; 1 when a file cannot be written.
"""
import argparse, datetime, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ctx_common as cc  # noqa: E402
import ctx_never as cn  # noqa: E402
import board_state as bs  # noqa: E402  — a board read back and its area (shared, v4.8.0)
import note_table as nt  # noqa: E402  — reading the note, table cells, page-safe text, protocol tables (shared, v4.7.0)
import publications as pub  # noqa: E402

FIELDS = ("product", "epic", "slices", "baseline", "published")
COLUMNS = (("id", "id"), ("activity", "діяльність"), ("step", "крок"), ("card", "картка"), ("slice", "зріз"),
           ("feature", "фіча"), ("epic", "епік"), ("source", "джерело"), ("edge_of", "edge_of"))
REQUIRED = ("id", "activity", "step", "card")
FINDINGS = ("subitem", "work_type", "skeleton_gap", "no_outcome", "no_step", "no_source", "duplicate_id",
            "edge_unknown", "edge_other_step", "unknown_slice", "bad_code", "empty_step", "duplicate_feature", "link",
            "secret")
STATUSES = ("done", "in_progress", "planned", "blocked")
COMMANDS = ("parse", "check", "render-html", "progress", "baseline", "board-state", "board-diff", "schema")

SUBITEM = re.compile(r"<br\s*/?>|•|[:;]\s*[-*]\s+\S", re.I)
WORK = r"(?:FE|BE|QA|iOS|Android|Design|DevOps)"
WORK_TYPE = re.compile(r"^\s*(?:\[%s\]|\(%s\)|%s\s*:)" % (WORK, WORK, WORK))
LINK = nt.LINK
FEATURE_CODE = re.compile(r"^([A-Z][A-Z0-9]*-\d+)((?:\.\d+)+)$")
EPIC_KEY = re.compile(r"^[A-Z][A-Z0-9]*-\d+$")
SLICE_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,31}$")
DAY = nt.DAY
MOVE_EPS = 5.0


def result(**kw):
    print("MAP_RESULT " + json.dumps(kw, ensure_ascii=False))


Bad = nt.Bad   # a note, a status file or a board that does not read — exit 2


# ------------------------------------------------------------------ the note
_fm_scalar, _cells, _tables = nt.fm_scalar, nt.cells, nt.tables


def _canon(header):
    h = header.strip().strip("`*_ ").lower()
    for name, uk in COLUMNS:
        if h in (name, uk, name.replace("_", " ")):
            return name
    return None


def load(path):
    """The note as a dict — raises Bad."""
    text, fm, body = nt.read_note(path)
    try:
        slices = cc.read_yaml_records(fm, "slices")
        baseline = cc.read_yaml_records(fm, "baseline")
    except ValueError as e:
        raise Bad("the frontmatter does not read: %s" % e)
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
        if nt.is_separator(cells):
            continue
        if len(cells) != len(cols):                  # as GFM: a short row gets empty cells, the excess is dropped
            errors.append("row %d (%s): %d cells, the header has %d — %s" % (
                n, cells[0] if cells else "?", len(cells), len(cols),
                "padded with empty cells" if len(cells) < len(cols) else "the extra cells dropped"))
            cells = (cells + [""] * len(cols))[:len(cols)]
        row = {name: "" for name, _ in COLUMNS}
        for name, val in zip(cols, cells):
            if name:
                row[name] = val
        row["row"] = n
        rows.append(row)
    sl = []
    for s in slices:
        sid = str(s.get("slice") or "").strip()
        if sid and not SLICE_ID.match(sid):
            errors.append("slice id %r is not a lower-case id (a-z, 0-9, -)" % sid)
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
                      "edge_of": r["edge_of"], "rank": rank[(a, s)], "row": r["row"], "board_text": safe(r["card"])})
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
    ids, where, feats = set(), {}, {}
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
            if c["edge_of"] == c["id"]:
                f("edge_unknown", card=c["id"], detail="edge_of points at its own card")
            elif c["edge_of"] not in where:
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
        if c["feature"]:
            if c["feature"] in feats:
                f("duplicate_feature", card=c["id"], detail="feature %s is also card %s" % (c["feature"], feats[c["feature"]]))
            else:
                feats[c["feature"]] = c["id"]
        cells = [c[k] or "" for k in ("card", "source", "feature", "epic", "slice", "edge_of")]
        if any(LINK.search(x) for x in cells):
            f("link", card=c["id"], detail="a link in the card's cells — a card carries no link")
        kinds = cn.scan(" \n".join(cells))
        if kinds:
            f("secret", card=c["id"], detail="the card holds %s — never on the board or the page" % ", ".join(kinds))
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


esc, safe, shown = nt.esc, nt.safe, nt.shown


def render_html(p, st, prog, backlog, note_name, lang):
    L = LABELS.get(lang, LABELS["en"])
    cols = p["layout"]["columns"]
    byid = {}
    for c in p["cards"]:
        byid.setdefault(c["id"], c)
    out = ["<!doctype html>", '<html lang="%s"><head><meta charset="utf-8">' % esc(lang),
           '<meta name="viewport" content="width=device-width,initial-scale=1">',
           "<title>%s — %s</title><style>%s</style></head><body>" % (esc(L["title"]), shown(p["title"] or note_name), CSS),
           "<h1>%s: %s</h1>" % (esc(L["title"]), shown(p["title"] or note_name)),
           '<p class="meta">%s: %s · %s · %s</p>' % (esc(L["note"]), shown(note_name), shown(p["product"]), shown(p["epic"]))]
    if st:
        out.append('<p class="meta">%s: %s · %s</p>' % (esc(L["status"]), shown(st["source"]), shown(st["date"])))
    else:
        out.append('<p class="meta">%s: %s</p>' % (esc(L["status"]), esc(L["no_status"])))
    out.append('<p class="meta">%s: %s</p>' % (esc(L["generated"]), esc(datetime.date.today().isoformat())))
    out.append('<div class="wrap"><table class="map"><thead><tr><th></th>')
    for a in p["activities"]:
        out.append('<th class="act" colspan="%d">%s</th>' % (len(a["steps"]), shown(a["name"])))
    out.append("</tr><tr><th></th>")
    for c in cols:
        out.append('<th class="step">%s</th>' % shown(c["step"]))
    out.append("</tr></thead><tbody>")
    gaps = {(g["activity"], g["step"]) for g in p["gaps"]}
    pr = {r["slice"]: r for r in prog}
    for bi, band in enumerate(p["layout"]["bands"]):
        sid = band["slice"]
        if sid:
            r = pr.get(sid, {})
            head = '<div class="s">%s</div><div class="o">%s</div>' % (shown(sid), shown(band["outcome"] or L["no_outcome"]))
            line = "%d %s" % (r.get("cards", 0), L["cards"])
            if st and r.get("done_pct") is not None:
                line += " · %s %d%%" % (L["done"], r["done_pct"])
            if r.get("growth_pct") is not None:
                line += " · +%d %s (%d%%)" % (len(r["added"]), L["growth"], r["growth_pct"])
            head += '<div class="p">%s</div>' % shown(line)
        else:
            head = '<div class="s">%s</div><div class="o">%d %s</div>' % (esc(L["backlog"]), backlog, esc(L["cards"]))
        out.append('<tr class="slice"><th class="band">%s</th>' % head)
        for ci, cell in enumerate(band["cells"]):
            out.append("<td>")
            for cid in cell:
                c = byid[cid]
                k = card_status(c, st) if st else "planned"
                cls = "card st-%s%s" % (k, " edge" if c["edge_of"] else "")
                code = c["feature"] if c["feature"] and c["feature"] not in c["source"] else ""
                meta = " · ".join(x for x in (code, c["source"], (L["edge"] + " " + c["edge_of"]) if c["edge_of"] else "",
                                              L[k] if st else "") if x)
                out.append('<div class="%s"><div class="t">%s</div><div class="m">%s</div></div>' % (cls, shown(c["card"]), shown(meta)))
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
            out.append("<tr><td>%s</td>" % shown(r["slice"]))
            for k in STATUSES + ("unknown",):
                out.append("<td>%d</td>" % r["spread"][k])
            g = "" if r["growth_pct"] is None else "+%d (%d%%)" % (len(r["added"]), r["growth_pct"])
            out.append("<td>%d%%</td><td>%s</td><td>%s</td></tr>" % (
                r["done_pct"], shown(", ".join("%s %s" % (b["id"], b["card"]) for b in r["blocked"])), esc(g)))
        out.append("</table>")
    out.append('<p class="legend meta">%s</p>' % "".join(
        '<span class="st-%s">%s</span>' % (k, esc(L[k])) for k in STATUSES + ("unknown",)))
    out.append("</body></html>")
    return "\n".join(out) + "\n"


# ------------------------------------------------------------------ baseline
def render_baseline(entries, eol):
    lines = ["baseline:"]
    for b in entries:
        lines.append("  - slice: %s" % json.dumps(b["slice"], ensure_ascii=False))
        lines.append("    date: %s" % json.dumps(b["date"]))
        lines.append("    cards: [%s]" % ", ".join(json.dumps(c, ensure_ascii=False) for c in b["cards"]))
    return eol.join(lines) + eol


# ------------------------------------------------------------------ board
# Reading a board back is scripts/board_state.py's since v4.8.0 (shared with journey_map.py); the roles of the map's
# stickies and the diff stay here. Since v4.11.2 a story map's board is a Miro board (its SVG) or the host's own board
# type (its element list, `--surface whiteboard`); the Miro path keeps its bytes — `surface` is named only for the host's.
_plain, _scope = bs.plain, bs.scope
HOST_FIRST = "the host's own board first, then a registry record's board"   # check 26: the user's rule (v4.11.2)
BACKBONE = ("slice", "backlog", "activity", "step")   # the plugin never deletes these: one gone from a host read = partial


def read_boards(paths, surface="miro"):
    """{id: item} of the reads on one surface. The host's board is read whole, page by page: an empty read is refused
    (an error the tool returned, a folder of nothing) — never a board where everything was removed."""
    items = bs.read_boards(paths, surface)
    if surface != "miro" and not items:
        raise Bad("the read-back holds no element — read the board again, every page, into a fresh folder")
    return items


def missing_backbone(last, now, p=None):
    """The slice sections and backbone blocks of the last state a host read lacks — what the note still has; [] when the
    read shares no element with the state (a new board, its first state)."""
    if not set(last) & set(now):
        return []
    slices = {s["slice"] for s in p["slices"]} if p else None
    names = ({a["name"] for a in p["activities"]} | {s for a in p["activities"] for s in a["steps"]}) if p else None
    out = []
    for mid, it in sorted(last.items()):
        role = it.get("role")
        if mid in now or role not in BACKBONE:
            continue
        if p is not None and ((role == "slice" and it.get("slice") not in slices) or
                              (role in ("activity", "step") and it["text"] not in names)):
            continue                                # the note dropped it: its block may go with it
        out.append({"id": mid, "role": role, "text": it["text"], "slice": it.get("slice")})
    return out


def _surf(surface):
    return {"surface": surface} if surface != "miro" else {}


def _rendered(c):
    texts = []
    for base in dict.fromkeys((c["card"], c.get("board_text") or c["card"])):
        texts += [_plain(base), _plain((base + " " + c["feature"]).strip())]
    return list(dict.fromkeys(texts))


def assign_roles(items, p):
    """Give each item its role — card (with its id), activity, step, slice (with its id), backlog, frame, sticky or
    other — by what the note says now. Two stickies of one text take that text's cards in order (`ambiguous`)."""
    by_text, ambiguous = {}, []
    for c in (p["cards"] if p else []):
        for t in dict.fromkeys(_rendered(c)):
            by_text.setdefault(t, []).append(c["id"])
    acts = {a["name"] for a in (p["activities"] if p else [])}
    steps = {s for a in (p["activities"] if p else []) for s in a["steps"]}
    slices = [s["slice"] for s in (p["slices"] if p else [])]
    taken = set()
    for it in items.values():                      # frames first: a sticky's frame says whether it is a card's place
        it.pop("card", None); it.pop("slice", None)
        if it["kind"] == "frame":
            low = it["text"].lower()
            sid = next((s for s in slices if re.match(r"%s(?:[\s—:–-]|$)" % re.escape(s.lower()), low)), None)
            it["role"] = "slice" if sid else "backlog" if low.startswith(("backlog", "беклог")) else "frame"
            if sid:
                it["slice"] = sid

    def as_card(it):
        cands = [cid for cid in by_text.get(it["text"], []) if cid not in taken]
        if not cands:
            return False
        it["role"], it["card"] = "card", cands[0]
        taken.add(cands[0])
        if len(by_text[it["text"]]) > 1:
            ambiguous.append(it["id"])
        return True

    def as_backbone(it):
        it["role"] = "activity" if it["text"] in acts else "step" if it["text"] in steps else None
        return it["role"] is not None
    for it in items.values():
        if it["kind"] == "frame":
            continue
        if it["kind"] != "sticky":
            it["role"] = "other"
            continue
        parent = items.get(it.get("frame") or "")
        in_band = parent is not None and parent.get("role") in ("slice", "backlog")
        if not ((as_card(it) or as_backbone(it)) if in_band else (as_backbone(it) or as_card(it))):
            it["role"] = "sticky"
    return ambiguous


def _state(path):
    """The board-state JSON at `path` — a mapping `elements` and a `note` field — or None: anything else is a read."""
    if os.path.isdir(path) or not path.lower().endswith(".json"):
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) and isinstance(data.get("elements"), dict) and "note" in data else None


def load_state(path, p, surface=None):
    """(items, surface) of the last state: a board-state JSON (its surface its own, Miro when it names none), or a board
    read — a Miro SVG, or with `--surface whiteboard` the host's list — whose roles are read against the note now."""
    data = _state(path)
    if data is not None:
        return data["elements"], data.get("surface") or "miro"
    if (surface or "miro") == "miro":
        if path.lower().endswith(".json"):          # the Miro path as at v4.6.0: a .json is a state or nothing
            try:
                with open(path, encoding="utf-8") as fh:
                    items = json.load(fh)["elements"]
                if not isinstance(items, dict):
                    raise ValueError
            except (OSError, ValueError, KeyError, TypeError):
                raise Bad("the board's state does not read")
            return items, "miro"
        items = bs.read_miro_svg(path)
    else:
        items = read_boards([path], surface)
    assign_roles(items, p)
    return items, surface or "miro"


def board_diff(last, now, p):
    changed, moved, added, removed, backbone, other, unrecorded = [], [], [], [], [], [], []
    card_now = {}
    for c in (p["cards"] if p else []):
        for t in _rendered(c):
            card_now.setdefault(t, c["id"])
    mapped = {it.get("card") for it in last.values() if it.get("card")}
    in_note = {c["id"] for c in p["cards"]} if p else None
    orphaned = [{"id": mid, "card": it.get("card"), "text": it["text"], "kind": it["kind"]} for mid, it in sorted(last.items())
                if in_note is not None and it.get("role") in ("card", "orphan") and it.get("card") not in in_note]
    gone = {o["id"] for o in orphaned}
    fresh = {mid: dict(it) for mid, it in now.items() if mid not in last}
    assign_roles(fresh, dict(p, cards=[c for c in p["cards"] if c["id"] not in mapped]) if p else None)

    def card_of(old):
        return old.get("card") or card_now.get(old["text"])
    for mid, it in now.items():
        old = last.get(mid)
        if old is None:
            entry = {"id": mid, "kind": it["kind"], "text": it["text"], "at": [round(it["x"]), round(it["y"])],
                     "frame": it["frame_text"]}
            role = fresh[mid].get("role")
            if role in ("card", "activity", "step", "slice", "backlog"):   # the map's own, missing from the state
                unrecorded.append(dict(entry, role=role, card=fresh[mid].get("card"), slice=fresh[mid].get("slice")))
            elif it["kind"] == "sticky":
                added.append(entry)
            elif it["kind"] == "frame":
                backbone.append(dict(entry, role="frame", change="added"))
            else:
                other.append(dict(entry, change="added"))
            continue
        role = old.get("role") or ("sticky" if old["kind"] == "sticky" else "other")
        if mid in gone:                            # the plugin's own sticky of a card the note no longer has
            continue
        is_card = role in ("card", "sticky")
        if old["text"] != it["text"]:
            entry = {"id": mid, "kind": it["kind"], "role": role, "last": old["text"], "now": it["text"]}
            if is_card:
                changed.append(dict(entry, card=card_of(old)))
            elif role == "other":
                other.append(dict(entry, change="text"))
            else:
                backbone.append(dict(entry, change="text", slice=old.get("slice")))
        if old.get("frame") != it["frame"] or abs(old.get("rx", old["x"]) - it["rx"]) > MOVE_EPS \
                or abs(old.get("ry", old["y"]) - it["ry"]) > MOVE_EPS:
            entry = {"id": mid, "kind": it["kind"], "role": role, "text": it["text"],
                     "from": [round(old["x"]), round(old["y"])], "to": [round(it["x"]), round(it["y"])],
                     "frame_from": old.get("frame_text", ""), "frame_to": it["frame_text"]}
            if is_card:
                moved.append(dict(entry, card=card_of(old)))
            elif role == "other":
                other.append(dict(entry, change="moved"))
            else:
                backbone.append(dict(entry, change="moved"))
    for mid, old in last.items():
        if mid in now or mid in gone:
            continue
        role = old.get("role") or "other"
        entry = {"id": mid, "kind": old["kind"], "role": role, "text": old["text"]}
        if role in ("card", "sticky"):
            removed.append(dict(entry, card=card_of(old)))
        elif role == "other":
            other.append(dict(entry, change="removed"))
        else:
            backbone.append(dict(entry, change="removed"))
    return changed, moved, added, removed, backbone, other, unrecorded, orphaned


# ------------------------------------------------------------------ check 26
_section, _table_after, _tick, _cmd = nt.section, nt.table_after, nt.tick, nt.cmd_name


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
    for row in _table_after(s10, r"\| Command \| What \|"):     # the board commands name the surfaces the script reads
        if _cmd(row[0]) in ("board-state", "board-diff"):
            m = re.search(r"--surface ([a-z\\|]+)", row[0])
            got = m.group(1).replace("\\", "").split("|") if m else []
            if got != list(bs.SURFACES):
                errs.append("story-map-protocol.md §10: `%s` does not name `--surface %s` (board_state.SURFACES)" % (
                    _cmd(row[0]), "|".join(bs.SURFACES)))
    try:
        with open(os.path.join(root, "scripts", "story_map.py"), encoding="utf-8") as fh:
            own = fh.read()
    except OSError:
        own = ""
    if own and len(re.findall(r'"--surface", choices=bs\.SURFACES', own)) < 2:
        errs.append("scripts/story_map.py: board-state and board-diff do not take `--surface` from board_state.SURFACES")
    host = (("references/story-map-protocol.md", _section(proto, "7. Publication")),
            ("references/artifact-publishing.md", _section(texts.get("references/artifact-publishing.md", ""), "3. The order")),
            ("skills/roadmap-architect/SKILL.md", skill))
    for rel, text in host:                          # the user's rule: the whole map on the host's own tools, a paid board
        if rel in texts and HOST_FIRST not in text:  # tool never needed
            errs.append("%s: the story map's boards are not offered with the host's own board first (%s)" % (rel, HOST_FIRST))
    if "not the story map's" in _section(proto, "11. What never happens"):
        errs.append("story-map-protocol.md §11 still excludes the host's own board from the story map")
    if "only the journey map offers it" in _section(texts.get("references/artifact-publishing.md", ""), "2. The candidates"):
        errs.append("artifact-publishing.md §2 still offers the host's own board to the journey map only")
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
    result(ok=True, out=args.out, bytes=len(page.encode("utf-8")), cards=len(p["cards"]), status=bool(st), errors=p["errors"])
    return 0


def cmd_progress(args):
    _, p = _loaded(args)
    st = load_status(args.status)
    prog, backlog = progress(p, st)
    result(ok=True, source=st["source"], date=st["date"], slices=prog, backlog=backlog, errors=p["errors"])
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
    result(ok=True, slice=args.slice, date=day, cards=ids, errors=p["errors"])
    return 0


def cmd_board_state(args):
    p = parse(load(args.note))
    items = read_boards(args.read, args.surface)
    ambiguous = assign_roles(items, p)
    if args.last and _there(args.last, args.surface):   # a card the note dropped keeps its sticky as the plugin's own
        in_note = {c["id"] for c in p["cards"]}
        last, _ = load_state(args.last, p, args.surface)
        lost = missing_backbone(last, items, p) if args.surface != "miro" else []
        if lost:
            raise Bad("the read lacks %d slice section(s) or backbone block(s) the last state holds (%s) — read the board "
                      "again, every page, into a fresh folder; a state is never kept from a partial read"
                      % (len(lost), ", ".join(x["text"] for x in lost[:3])))
        for mid, old in last.items():
            it = items.get(mid)
            if it is not None and old.get("role") in ("card", "orphan") and old.get("card") not in in_note \
                    and it.get("role") != "card":
                it["role"], it["card"] = "orphan", old.get("card")
    state = dict({"version": 1}, **_surf(args.surface))
    state.update({"note": os.path.basename(args.note),
                  "at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "elements": items})
    out = os.path.abspath(args.out)
    try:
        os.makedirs(os.path.dirname(out), exist_ok=True)
        tmp = out + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(state, fh, ensure_ascii=False, indent=1)
        os.replace(tmp, out)
    except OSError as e:
        result(ok=False, error="the state cannot be written: %s" % (e.strerror or type(e).__name__))
        return 1
    cards = {it["card"]: mid for mid, it in items.items() if it.get("role") == "card"}
    roles = {}
    for it in items.values():
        roles[it["role"]] = roles.get(it["role"], 0) + 1
    result(ok=True, out=out, **dict(_surf(args.surface), cards=cards, slices={it["slice"]: mid for mid, it in items.items() if it.get("slice")},
           roles=roles, unmapped_cards=[c["id"] for c in p["cards"] if c["id"] not in cards], ambiguous=ambiguous,
           orphans={it["card"]: mid for mid, it in items.items() if it.get("role") == "orphan"}))
    return 0


def _card_ids(items):
    """{card id: element id} of the stickies a state maps to cards — what the next version updates by id."""
    return {it["card"]: mid for mid, it in items.items() if it.get("role") == "card" and it.get("card")}


def _there(path, surface):
    """A last state or read to compare with: a file — or, on the host's board, a folder of its elements too."""
    return os.path.isfile(path) or (surface not in (None, "miro") and os.path.isdir(path))


def cmd_board_diff(args):
    if not args.last or not _there(args.last, args.surface):
        result(ok=True, state="unknown", why="no last state of the board on this machine")
        return 0
    p = parse(load(args.note)) if args.note else None
    last, surface = load_state(args.last, p, args.surface)
    surface = args.surface or surface              # the state's own surface unless one is named
    if not args.now:
        result(ok=True, state="scope", **dict(_surf(surface), scope=_scope(last), ids=sorted(last), cards=_card_ids(last)))
        return 0
    now = read_boards(args.now, surface)
    lost = missing_backbone(last, now, p) if surface != "miro" else []
    if lost:                                       # the plugin never deletes a slice or a backbone block: a partial read
        result(ok=True, state="partial", surface=surface, missing=lost, ids=sorted(last), cards=_card_ids(last),
               why="the read lacks %d slice section(s) or backbone block(s) the state holds — read the board again, every "
                   "page, into a fresh folder; nothing is offered from a partial read" % len(lost))
        return 0
    changed, moved, added, removed, backbone, other, unrecorded, orphaned = board_diff(last, now, p)
    result(ok=True, state="diff", **_surf(surface), changed=changed, moved=moved, added=added, removed=removed, backbone=backbone,
           other=other, unrecorded=unrecorded, orphaned=orphaned,
           counts={"changed": len(changed), "moved": len(moved), "added": len(added), "removed": len(removed),
                   "backbone": len(backbone), "orphaned": len(orphaned)},
           scope=_scope(last), ids=sorted(last), cards=_card_ids(last))
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
    p = sub.add_parser("board-state")
    p.add_argument("--read", required=True, nargs="+", help="the board read back (Miro: by ids first, then the area; "
                   "the host's board: every page of its list)")
    p.add_argument("--surface", choices=bs.SURFACES, default="miro", help="the read's format (default: miro)")
    p.add_argument("--note", required=True)
    p.add_argument("--last", help="the previous state: a card the note dropped keeps its sticky as an orphan")
    p.add_argument("--out", required=True, help="~/.grow-pm/story-maps/<key>.board.json (the host's board: "
                   "<key>.artifact.board.json)")
    p = sub.add_parser("board-diff")
    p.add_argument("--last", help="the board's state (board-state JSON) or an older board SVG")
    p.add_argument("--now", nargs="+", help="the board read back now: by the state's ids, then over its area (Miro), "
                   "or every page of the host's list")
    p.add_argument("--surface", choices=bs.SURFACES, help="the reads' format (default: the state's, else miro)")
    p.add_argument("--note")
    sub.add_parser("schema")
    args = ap.parse_args(argv)
    fn = {"parse": cmd_parse, "check": cmd_check, "render-html": cmd_render, "progress": cmd_progress,
          "baseline": cmd_baseline, "board-state": cmd_board_state, "board-diff": cmd_board_diff,
          "schema": cmd_schema}.get(args.cmd)
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
