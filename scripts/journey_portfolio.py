#!/usr/bin/env python3
"""journey_portfolio.py — the journey portfolio of a product (references/journey-protocol.md §13, since v4.9.0): every
journey map of the product and its hand CJM notes in one list, computed from the notes every time — no portfolio note,
no board.

  list         the portfolio: a row per journey map — owner, stages, health with its delta and date, review, pains by
               class, anomalies with the critical ones apart, gaps, findings, where it is published — and the reasons it
               needs attention, the maps that need it first; the hand CJM notes (`type: cjm`) partly: funnel, stages,
               the metric rows per stage, snapshot. A markdown table for the chat, then the result line.
  render-html  the same portfolio as one self-contained page: numbers only — no row text, no link, no request
  schema       the commands, columns, attention reasons, hand-CJM fields and findings, skip reasons the protocol must
               agree with (validate-consistency.sh check 30)

The notes are the truth and are only read — never written. A journey map is read by journey_map.py (load, findings, the
health-check's status labels, the page's pan script — imported, never copied); a hand CJM gives its frontmatter
`title` (else `name`), `funnel`, `stages`, `snapshot`, its stage headings `## <ID> — <name>` and the row count of the
first metric table under each — never a link, a dashboard, a module, an owner, a team, a mission, a meeting or its text.
A product is compared as `ctx search --type` compares it (ctx_search._product_names). Every command ends with one
`PORTFOLIO_RESULT {json}` line. Stdlib only (Python 3.9). Exit 0; 2 for a wrong argument; 1 when the page cannot be
written.
"""
import argparse, datetime, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ctx_search as cs_  # noqa: E402  — the product compared as `ctx search --type` compares it
import journey_map as jm  # noqa: E402  — a journey note: load, findings, the health-check's labels, the page's script
import note_table as nt  # noqa: E402
import publications as pub  # noqa: E402

COMMANDS = ("list", "render-html", "schema")
COLUMNS = (("journey", "шлях"), ("owner", "власник"), ("stages", "етапи"), ("health", "здоров'я"), ("delta", "зміна"),
           ("health_date", "дата точки"), ("reviewed", "рев'ю"), ("pains", "болі"), ("anomalies", "аномалії"),
           ("gaps", "розриви"), ("findings", "знахідки"), ("published", "опубліковано"), ("attention", "увага"))
EN_COLUMNS = {"journey": "journey", "owner": "owner", "stages": "stages", "health": "health", "delta": "change",
              "health_date": "point date", "reviewed": "review", "pains": "pains", "anomalies": "anomalies", "gaps": "gaps",
              "findings": "findings", "published": "published", "attention": "attention"}
ATTENTION = (("health_drop", "здоров'я впало"), ("stale_review", "рев'ю застаріло"), ("no_owner", "немає власника"),
             ("critical_anomaly", "критична аномалія"), ("empty_stage", "етап без доказів"))
EN_ATTENTION = {"health_drop": "health dropped", "stale_review": "review stale", "no_owner": "no owner",
                "critical_anomaly": "critical anomaly", "empty_stage": "stage without evidence"}
DROP = 10            # health points: a drop of MORE than this between the last two points raises a map — the health-check's
                     # own escalation (cjm-reports.md: «dropped by >10 points»), so the two never disagree
CJM_FIELDS = ("title", "funnel", "stages", "stage_headings", "metrics", "snapshot")
CJM_FINDINGS = ("stage_count", "no_snapshot")
SKIPS = (("not_cjm_map", "не CJM-карта — немає воронки чи стадій"), ("other_product", "нотатка іншого продукту"),
         ("wrong_type", "не карта шляху й не CJM-нотатка"), ("unreadable", "нотатка не читається"))
EN_SKIPS = {"not_cjm_map": "no CJM map — no funnel or stages", "other_product": "another product's note",
            "wrong_type": "neither a journey map nor a CJM note", "unreadable": "the note does not read"}
JOURNEY_TYPE, CJM_TYPE = "cjm-journey", "cjm"
STAGE_HEAD = re.compile(r"^##[ \t]+([^\s—–#|]{1,24})[ \t]+[—–][ \t]+(.+?)[ \t#]*$")     # `## <ID> — <name>` (R32)
METRIC_HEAD = ("метрика", "metric")         # the first header cell of a stage's metrics table
FENCE = re.compile(r"^[ \t]{0,3}(```|~~~)")
LABELS = {
    "uk": {"title": "Портфель шляхів", "generated": "Згенеровано", "maps": "Карти шляху", "attention": "Потребують уваги",
           "none": "Карт шляху немає", "stale": "застаріло", "critical": "критичних %d", "cjm": "Ручні CJM-нотатки",
           "mark": "ручна CJM — частково: без джерел, класів і здоров'я", "funnel": "воронка", "snapshot": "знімок",
           "stages_of": "%d з %d оголошених", "metrics": "метрик", "no_product": "продукт не вказано",
           "skipped": "Пропущено", "other": "Іншого продукту — не показано: %d", "empty": "без доказів",
           "no_outcome": "без метрики результату", "no_point": "—", "head": "Портфель шляхів: %s · %s · карт %d · "
           "потребують уваги %d · ручних CJM %d · пропущено %d · іншого продукту %d", "cjm_cols": ("CJM", "воронка",
           "етапи", "метрик на етап", "знімок", "знахідки"), "missing": "теки ще немає: %s"},
    "en": {"title": "Journey portfolio", "generated": "Generated", "maps": "Journey maps", "attention": "Needs attention",
           "none": "No journey maps", "stale": "stale", "critical": "critical %d", "cjm": "Hand CJM notes",
           "mark": "hand CJM — partly: no sources, classes or health", "funnel": "funnel", "snapshot": "snapshot",
           "stages_of": "%d of %d declared", "metrics": "metrics", "no_product": "no product named",
           "skipped": "Skipped", "other": "Another product — not shown: %d", "empty": "no evidence",
           "no_outcome": "no outcome metric", "no_point": "—", "head": "Journey portfolio: %s · %s · maps %d · "
           "needing attention %d · hand CJMs %d · skipped %d · another product %d", "cjm_cols": ("CJM", "funnel",
           "stages", "metrics per stage", "snapshot", "findings"), "missing": "no folder yet: %s"},
}
esc, shown = nt.esc, nt.shown
Bad = nt.Bad


def result(**kw):
    print("PORTFOLIO_RESULT " + json.dumps(kw, ensure_ascii=False))


def plain(s):
    """A field's or a heading's words for the portfolio: a wiki link as the name it shows, a markdown link as its text,
    then page-safe — a link removed (and its marker), a person's e-mail or phone hidden, a string holding a secret hidden
    whole (note_table.safe)."""
    s = re.sub(r"!?\[\[([^\]|#]*)(?:#[^\]|]*)?(?:\|([^\]]*))?\]\]", lambda m: m.group(2) or m.group(1), str(s or ""))
    s = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", s)
    s = nt.safe(s)
    return re.sub(r"[ \t]*\[link removed\]", "", s).strip()


def _same_product(note_product, asked):
    """Is a note of the product asked — compared as `ctx search --type` compares it; a note that names no product stays."""
    mine, want = cs_._product_names(note_product), cs_._product_names(asked)
    return not mine or not want or bool(mine & want)


def _labels(lang):
    return LABELS.get(lang, LABELS["en"])


def _attention_label(code, lang):
    return dict(ATTENTION)[code] if lang == "uk" else EN_ATTENTION[code]


def _skip_label(code, lang):
    return dict(SKIPS)[code] if lang == "uk" else EN_SKIPS[code]


# ------------------------------------------------------------------ a journey map's row
def status_of(text):
    """The health-check status a refreshed anomaly row ends with — `— <label>` by journey_map's own labels (REFRESH), in
    either language; None for any other ending. A word inside the text is no status."""
    t = str(text or "").rstrip()
    for L in jm.REFRESH.values():
        for code, label in L["status"].items():
            if t.endswith("— " + label):
                return code
    return None


def _num(x):
    if isinstance(x, float):
        x = round(x, 1)
        return int(x) if x.is_integer() else x
    return x


def published_of(path):
    """The places of the note's `published` mirror: surface, kind, level, version, audience — never its link or id.
    A field that does not read is no place."""
    try:
        entries = pub.load(path)[2]
    except (pub.Unreadable, pub.Foreign, OSError, UnicodeDecodeError, ValueError):
        return []
    return [{k: e[k] for k in ("surface", "kind", "level", "version", "audience") if e.get(k) not in (None, "")}
            for e in entries]


def map_row(note, today, newest):
    """The portfolio's row of one journey map (§13): its fields — never a row's text, source or name."""
    live = [r for r in note["rows"] if not r["gap"] and r["id"]]
    found = jm.findings(note, today, newest)
    codes = [f["finding"] for f in found]
    pts = sorted(({"date": p["date"], "score": _num(p["score"])} for p in note["health"]
                  if isinstance(p.get("score"), (int, float)) and jm.day(p.get("date"))), key=lambda p: p["date"])
    last = pts[-1] if pts else None
    prev = pts[-2] if len(pts) > 1 else None
    health = {"score": last["score"] if last else None, "delta": _num(last["score"] - prev["score"]) if prev else None,
              "date": last["date"] if last else "", "points": pts}
    pains = {}
    for r in live:
        if r["lane"] == "pain":
            k = r["class"].strip().lower() or "—"
            pains[k] = pains.get(k, 0) + 1
    an = {"total": 0, "critical": 0, "warning": 0, "positive": 0, "unrated": 0}
    for r in live:
        if r["lane"] == "anomaly":
            an["total"] += 1
            st = status_of(r["text"]) if jm._is_hc(r) else None
            an[st or "unrated"] += 1
    gaps = {"empty_stage": [f["stage"] for f in found if f["finding"] == "empty_stage"],
            "no_outcome": [f["stage"] for f in found if f["finding"] == "no_outcome"]}
    by = {}
    for c in codes:
        by[c] = by.get(c, 0) + 1
    attention = []
    if prev and prev["score"] - last["score"] > DROP:
        attention.append({"reason": "health_drop", "detail": "%s → %s" % (prev["score"], last["score"])})
    if "stale_review" in codes:
        attention.append({"reason": "stale_review", "detail": note["reviewed"] or ""})
    if "no_owner" in codes:
        attention.append({"reason": "no_owner", "detail": ""})
    if an["critical"]:
        attention.append({"reason": "critical_anomaly", "detail": str(an["critical"])})
    if gaps["empty_stage"]:
        attention.append({"reason": "empty_stage", "detail": ", ".join(gaps["empty_stage"])})
    name = os.path.basename(note["path"])
    return {"journey": plain(note["journey"] or note["title"] or os.path.splitext(name)[0]), "note": name,
            "path": note["path"], "product": plain(note["product"]), "product_missing": not note["product"],
            "owner": plain(note["owner"]), "stages": len(note["stages"]), "health": health,
            "reviewed": note["reviewed"] if jm.day(note["reviewed"]) else "", "stale_review": "stale_review" in codes,
            "pains": pains, "anomalies": an, "gaps": gaps, "findings": {"total": len(found), "by": by},
            "published": published_of(note["path"]), "attention": attention}


# ------------------------------------------------------------------ a hand CJM note (R32)
def _metric_rows(run):
    """The row count of a table run whose first header cell is «Метрика» / «Metric», else None — only that cell is read."""
    head = nt.cells(run[0])
    if not head or head[0].strip().strip("`*_ ").lower() not in METRIC_HEAD:
        return None
    return sum(1 for line in run[1:] if not nt.is_separator(nt.cells(line)) and any(c for c in nt.cells(line)))


def read_cjm(path, fm, body, lang):
    """The fields §13 reads of a hand CJM note, or None when it is no CJM map — no `funnel`, or no stage heading
    `## <ID> — <name>` (a cjm-research report is `type: cjm` too)."""
    funnel = nt.fm_scalar(fm, "funnel")
    stages, cur, fence, run = [], None, False, []

    def close():
        if cur is not None and cur["metrics"] is None and run:
            cur["metrics"] = _metric_rows(run)
    for line in body.split("\n") + [""]:
        if FENCE.match(line):
            fence = not fence
            continue
        if fence:
            continue
        if line.strip().startswith("|"):
            run.append(line)
            continue
        close()
        run = []
        if re.match(r"^#{1,2}[ \t]", line):          # a level-1 or level-2 heading ends a stage; a stage heading opens one
            m = STAGE_HEAD.match(line)
            cur = {"id": plain(m.group(1)), "name": plain(m.group(2)), "metrics": None} if m else None
            if cur is not None:
                stages.append(cur)
    if not funnel or not stages:
        return None
    for s in stages:
        s["metrics"] = s["metrics"] or 0
    declared = nt.fm_scalar(fm, "stages")
    declared = int(declared) if declared.isdigit() else None
    snapshot = nt.fm_scalar(fm, "snapshot")
    snapshot = snapshot if jm.day(snapshot) else ""
    findings = []
    if declared is not None and declared != len(stages):
        findings.append({"finding": "stage_count", "detail": "stages: %d, headings: %d" % (declared, len(stages))})
    if not snapshot:
        findings.append({"finding": "no_snapshot", "detail": "no snapshot date (YYYY-MM-DD) in the frontmatter"})
    product = nt.fm_scalar(fm, "product")
    name = os.path.basename(path)
    return {"title": plain(nt.fm_scalar(fm, "title") or nt.fm_scalar(fm, "name") or os.path.splitext(name)[0]),
            "note": name, "path": path, "funnel": plain(funnel), "stages_declared": declared, "stages": stages,
            "snapshot": snapshot, "product": plain(product), "product_missing": not product, "findings": findings,
            "mark": _labels(lang)["mark"]}


# ------------------------------------------------------------------ the portfolio
def collect(paths, dirs, product, today, newest, lang):
    """The portfolio of the notes named and the `.md` notes directly inside each folder: {maps, cjm, skipped,
    other_products, ignored, missing_dirs}. A note is read once; its `type` decides what it is."""
    items, missing = [(p, True) for p in paths or []], []
    for d in dirs or []:
        if not os.path.isdir(d):
            if os.path.exists(d):
                raise Bad("%s is not a folder" % d)
            missing.append(d)
            continue
        try:
            names = sorted(os.listdir(d))
        except OSError as e:
            raise Bad("the folder does not read: %s" % (e.strerror or type(e).__name__))
        items += [(os.path.join(d, n), False) for n in names if n.lower().endswith(".md")]
    seen, maps, cjms, skipped, other, ignored = set(), [], [], [], 0, 0
    for path, named in items:
        real = os.path.realpath(path)
        if real in seen:
            continue
        seen.add(real)
        name = os.path.basename(path)
        try:
            _, fm, body = nt.read_note(path)
        except Bad as e:
            skipped.append({"note": name, "reason": "unreadable", "detail": str(e)})
            continue
        kind = nt.fm_scalar(fm, "type").strip().lower()
        if kind not in (JOURNEY_TYPE, CJM_TYPE):
            if named:
                skipped.append({"note": name, "reason": "wrong_type", "detail": "type: %s" % (kind or "—")})
            else:
                ignored += 1
            continue
        if not _same_product(nt.fm_scalar(fm, "product"), product):
            other += 1
            continue
        if kind == JOURNEY_TYPE:
            try:
                maps.append(map_row(jm.load(path), today, newest))
            except Bad as e:
                skipped.append({"note": name, "reason": "unreadable", "detail": str(e)})
            continue
        c = read_cjm(path, fm, body, lang)
        if c is None:
            skipped.append({"note": name, "reason": "not_cjm_map", "detail": _skip_label("not_cjm_map", lang)})
            continue
        cjms.append(c)

    def key(m):
        return (m["journey"].casefold(), m["note"])
    maps = sorted((m for m in maps if m["attention"]), key=lambda m: (-len(m["attention"]), key(m))) + \
        sorted((m for m in maps if not m["attention"]), key=key)
    cjms.sort(key=lambda c: (c["title"].casefold(), c["note"]))
    return {"maps": maps, "cjm": cjms, "skipped": skipped, "other_products": other, "ignored": ignored,
            "missing_dirs": missing}


def counts(p):
    return {"maps": len(p["maps"]), "attention": sum(1 for m in p["maps"] if m["attention"]), "cjm": len(p["cjm"]),
            "skipped": len(p["skipped"]), "other_products": p["other_products"]}


# ------------------------------------------------------------------ the cells, shared by the chat table and the page
def _pains(m):
    return " · ".join("%s %d" % (k, n) for k, n in sorted(m["pains"].items())) or "0"


def _anomalies(m, L):
    a = m["anomalies"]
    return "%d" % a["total"] + (" (%s)" % (L["critical"] % a["critical"]) if a["critical"] else "")


def _gaps(m, L):
    g = m["gaps"]
    parts = (["%s: %s" % (L["empty"], ", ".join(g["empty_stage"]))] if g["empty_stage"] else []) + \
        (["%s: %s" % (L["no_outcome"], ", ".join(g["no_outcome"]))] if g["no_outcome"] else [])
    return " · ".join(parts) or "—"


def _published(m):
    return ", ".join(" ".join(str(x) for x in (e.get("surface"), e.get("kind"), e.get("level"),
                                               "v%s" % e.get("version") if e.get("version") else "") if x)
                     for e in m["published"]) or "—"


def _delta(m):
    d = m["health"]["delta"]
    return "—" if d is None else ("+%s" % d if d > 0 else "−%s" % abs(d) if d < 0 else "0")


def _review(m, L):
    return (m["reviewed"] or "⚠️") + (" (%s)" % L["stale"] if m["stale_review"] else "")


def _cells(m, lang):
    L = _labels(lang)
    h = m["health"]
    return {"journey": m["journey"], "owner": m["owner"] or "⚠️", "stages": str(m["stages"]),
            "health": "—" if h["score"] is None else str(h["score"]), "delta": _delta(m), "health_date": h["date"] or "—",
            "reviewed": _review(m, L), "pains": _pains(m), "anomalies": _anomalies(m, L), "gaps": _gaps(m, L),
            "findings": str(m["findings"]["total"]), "published": _published(m),
            "attention": "; ".join(_attention_label(a["reason"], lang) for a in m["attention"]) or "—"}


def _cjm_stages(c, L):
    return " · ".join("%s %s %d" % (s["id"], s["name"], s["metrics"]) for s in c["stages"])


def _cjm_count(c, L):
    return L["stages_of"] % (len(c["stages"]), c["stages_declared"]) if c["stages_declared"] is not None else str(len(c["stages"]))


def chat_table(p, product, today, lang):
    """The portfolio as markdown for the chat: the head line, the maps' table, the hand CJMs' block, what was skipped."""
    L = _labels(lang)
    c = counts(p)
    out = [L["head"] % (product, today, c["maps"], c["attention"], c["cjm"], c["skipped"], c["other_products"]), ""]
    heads = [uk if lang == "uk" else EN_COLUMNS[k] for k, uk in COLUMNS]
    if p["maps"]:
        out += [nt.row_line(heads), nt.row_line(["---"] * len(heads))]
        for m in p["maps"]:
            cl = _cells(m, lang)
            out.append(nt.row_line([cl[k] for k, _ in COLUMNS]))
    else:
        out.append(L["none"])
    if p["cjm"]:
        out += ["", "%s · %s" % (L["cjm"], L["mark"]), "", nt.row_line(list(L["cjm_cols"])),
                nt.row_line(["---"] * len(L["cjm_cols"]))]
        for x in p["cjm"]:
            out.append(nt.row_line([x["title"] + (" (%s)" % L["no_product"] if x["product_missing"] else ""), x["funnel"],
                                    _cjm_count(x, L), _cjm_stages(x, L), x["snapshot"] or "⚠️",
                                    ", ".join(f["finding"] for f in x["findings"]) or "—"]))
    if p["skipped"] or p["other_products"] or p["missing_dirs"]:
        out.append("")
    for s in p["skipped"]:
        out.append("%s: %s — %s" % (L["skipped"], s["note"], s["detail"]))
    if p["other_products"]:
        out.append(L["other"] % p["other_products"])
    for d in p["missing_dirs"]:
        out.append(L["missing"] % d)
    return "\n".join(out) + "\n"


# ------------------------------------------------------------------ the page
CSS = """:root{color-scheme:light}
*{box-sizing:border-box}body{margin:0;padding:24px;background:#f7f7f5;color:#1f2328;font:14px/1.4 -apple-system,"Segoe UI",Roboto,Arial,sans-serif}
h1{font-size:20px;margin:0 0 4px}h2{font-size:16px;margin:18px 0 6px}.meta{color:#57606a;margin:2px 0}
.wrap{overflow:auto;margin-top:12px;max-height:max(320px,80vh);border:1px solid #dee2e6;border-radius:8px;background:#fff;cursor:grab;touch-action:pan-x pan-y}
.wrap.panning{cursor:grabbing;user-select:none}.wrap:focus-visible{outline:2px solid #1c7ed6;outline-offset:2px}
table.pf{border-collapse:separate;border-spacing:0;min-width:100%}
table.pf th,table.pf td{padding:6px 8px;border-bottom:1px solid #eef0f2;vertical-align:top;text-align:left;white-space:nowrap}
table.pf thead th{position:sticky;top:0;z-index:2;background:#d0ebff}
table.pf th.j{position:sticky;left:0;z-index:1;background:#fff;font-weight:600;white-space:normal;min-width:160px}
table.pf thead th.j{z-index:3;background:#d0ebff}
.m{color:#57606a;font-size:11px;font-weight:400}tr.attn th.j{border-left:4px solid #e03131}.reason{color:#c92a2a}.stale{color:#e8590c}.ok{color:#2f9e44}
svg.spark{background:#fff;border:1px solid #dee2e6;border-radius:4px;vertical-align:middle}
.cjm{background:#fff;border:1px solid #dee2e6;border-radius:8px;padding:10px 12px;margin:10px 0}
.cjm .mark{color:#57606a;font-size:12px}table.st{border-collapse:collapse;margin-top:6px}table.st td{border:1px solid #dee2e6;padding:2px 8px}"""


def _spark(points):
    """journey_map's sparkline, a smaller copy for the table's cell — each point's date and score."""
    return jm.sparkline(points).replace('width="260" height="56"', 'width="130" height="32"', 1)


def render_html(p, product, today, lang):
    L = _labels(lang)
    c = counts(p)
    heads = [(k, uk if lang == "uk" else EN_COLUMNS[k]) for k, uk in COLUMNS]
    out = ["<!doctype html>", '<html lang="%s"><head><meta charset="utf-8">' % esc(lang),
           '<meta name="viewport" content="width=device-width,initial-scale=1">',
           "<title>%s — %s</title><style>%s</style></head><body>" % (esc(L["title"]), shown(product), CSS),
           "<h1>%s: %s</h1>" % (esc(L["title"]), shown(product)),
           '<p class="meta">%s: %s</p>' % (esc(L["generated"]), esc(today)),
           '<p class="meta">%s</p>' % esc(L["head"] % (product, today, c["maps"], c["attention"], c["cjm"], c["skipped"],
                                                      c["other_products"])),
           "<h2>%s</h2>" % esc(L["maps"])]
    if p["maps"]:
        out.append('<div class="wrap" tabindex="0"><table class="pf"><thead><tr>%s</tr></thead><tbody>' % "".join(
            '<th%s>%s</th>' % (' class="j"' if k == "journey" else "", esc(h)) for k, h in heads))
        for m in p["maps"]:
            cl = _cells(m, lang)
            tds = []
            for k, _ in heads:
                if k == "journey":                   # the note is each number's source (artifact-publishing.md §9)
                    tds.append('<th class="j">%s<div class="m">%s</div></th>' % (esc(cl[k]), esc(m["note"])))
                elif k == "health" and m["health"]["points"]:
                    tds.append("<td>%s %s</td>" % (_spark(m["health"]["points"]), esc(cl[k])))
                elif k == "reviewed":
                    tds.append('<td%s>%s</td>' % (' class="stale"' if m["stale_review"] else "", esc(cl[k])))
                elif k == "attention":
                    tds.append('<td class="%s">%s</td>' % ("reason" if m["attention"] else "ok", esc(cl[k])))
                else:
                    tds.append("<td>%s</td>" % esc(cl[k]))
            out.append('<tr%s>%s</tr>' % (' class="attn"' if m["attention"] else "", "".join(tds)))
        out.append("</tbody></table></div>")
    else:
        out.append('<p class="meta">%s</p>' % esc(L["none"]))
    if p["cjm"]:
        out.append("<h2>%s</h2>" % esc(L["cjm"]))
        for x in p["cjm"]:
            meta = " · ".join(v for v in ("%s: %s" % (L["funnel"], x["funnel"]), _cjm_count(x, L),
                                          "%s: %s" % (L["snapshot"], x["snapshot"] or "⚠️"),
                                          L["no_product"] if x["product_missing"] else "",
                                          ", ".join(f["finding"] for f in x["findings"])) if v)
            rows = "".join("<tr><td>%s</td><td>%s</td><td>%d %s</td></tr>" % (esc(s["id"]), esc(s["name"]), s["metrics"],
                                                                              esc(L["metrics"])) for s in x["stages"])
            out.append('<div class="cjm"><b>%s</b> <span class="m">%s</span><div class="mark">%s</div><p class="meta">%s</p>'
                       '<table class="st">%s</table></div>' % (esc(x["title"]), esc(x["note"]), esc(L["mark"]), esc(meta), rows))
    if p["skipped"]:
        by = {}
        for s in p["skipped"]:
            by[s["reason"]] = by.get(s["reason"], 0) + 1
        out.append('<p class="meta">%s: %s</p>' % (esc(L["skipped"]), esc(" · ".join(
            "%s — %d" % (_skip_label(k, lang), n) for k, n in by.items()))))
    if p["other_products"]:
        out.append('<p class="meta">%s</p>' % esc(L["other"] % p["other_products"]))
    if p["maps"]:
        out.append("<script>%s</script>" % jm.PAN)
    out.append("</body></html>")
    return "\n".join(out) + "\n"


# ------------------------------------------------------------------ commands
def _today(args):
    if not getattr(args, "today", None):
        return datetime.date.today()
    d = jm.day(args.today)
    if d is None:
        raise Bad("--today is not YYYY-MM-DD")
    return d


def _portfolio(args):
    today = _today(args)
    newest = None
    if args.snapshots:
        newest = jm.snapshots(args.snapshots, args.product)[2]
    return collect(args.note, args.dir, args.product, today, newest, args.lang), today


def cmd_list(args):
    p, today = _portfolio(args)
    sys.stdout.write(chat_table(p, args.product, today.isoformat(), args.lang))
    result(ok=True, product=args.product, today=today.isoformat(), lang=args.lang, counts=counts(p), **p)
    return 0


def cmd_render(args):
    p, today = _portfolio(args)
    page = render_html(p, args.product, today.isoformat(), args.lang)
    try:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(page)
    except OSError as e:
        result(ok=False, error="the page cannot be written: %s" % (e.strerror or type(e).__name__))
        return 1
    result(ok=True, out=args.out, bytes=len(page.encode("utf-8")), maps=len(p["maps"]), cjm=len(p["cjm"]),
           skipped=len(p["skipped"]), other_products=p["other_products"], missing_dirs=p["missing_dirs"])
    return 0


def cmd_schema(args):
    result(ok=True, commands=list(COMMANDS), columns=[list(c) for c in COLUMNS], attention=[list(a) for a in ATTENTION],
           drop=DROP, cjm_fields=list(CJM_FIELDS), cjm_findings=list(CJM_FINDINGS), skips=[list(s) for s in SKIPS])
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="journey_portfolio.py", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd")
    for name in ("list", "render-html"):
        p = sub.add_parser(name)
        p.add_argument("--product", required=True, help="the product of the portfolio — another product's note is left out")
        p.add_argument("--note", action="extend", nargs="+", default=[], help="a journey map or a hand CJM note — its type decides")
        p.add_argument("--dir", action="extend", nargs="+", default=[], help="a folder: every .md directly inside it")
        p.add_argument("--snapshots", help="the health-check folder: a metric older than its newest snapshot is stale")
        p.add_argument("--today", help="YYYY-MM-DD (default: today)")
        p.add_argument("--lang", default="en", choices=sorted(LABELS))
        if name == "render-html":
            p.add_argument("--out", required=True, help="CJM/journeys/<product>/portfolio.html")
    sub.add_parser("schema")
    try:
        args = ap.parse_args(argv)
    except SystemExit as e:                          # a wrong argument still ends with the result line
        if e.code in (0, None):
            return 0
        result(ok=False, error="wrong arguments — see journey_portfolio.py <command> --help")
        return 2
    fn = {"list": cmd_list, "render-html": cmd_render, "schema": cmd_schema}.get(args.cmd)
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
