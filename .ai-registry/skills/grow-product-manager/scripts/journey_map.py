#!/usr/bin/env python3
"""journey_map.py — the journey map's note: parse, check, render, health trend, scheduled refresh, opportunity tree
(references/journey-protocol.md, since v4.7.0).

  parse        the row table of the note as stages × lanes, the gap rows and each stage's opportunity tree
  check        the script's findings of the protocol (§6), each with its row or stage — proposals, never a block
  render-html  one self-contained HTML page of the map: no request, no link, every text escaped, light theme
  health       the `health` field from the health-check snapshots' frontmatter — every other byte of the note kept
  refresh      the scheduled health-check's refresh: only the health-check rows replaced by id, the health point, the page
  tree         a stage's opportunity tree as Mermaid text (diagram-prototyper renders it)
  schema       the fields, columns, lanes, levels, findings and commands the protocol must agree with (check 28)

The note is the source of truth: a markdown table of rows under its frontmatter (`product`, `journey`, `owner`,
`reviewed`, `stages`, `health`, `published`). The `health` field is written through publications.write_field — the
same code that writes `published` — so a field is replaced and nothing else moves. Table parsing, escaping, link
removal and secret hiding are note_table.py's, shared with story_map.py. Every command ends with one
`JOURNEY_RESULT {json}` line. Stdlib only (Python 3.9). Exit 0; 2 for a wrong argument or a note or snapshot that does
not read; 1 when a file cannot be written.
"""
import argparse, datetime, json, os, re, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ctx_common as cc  # noqa: E402
import ctx_never as cn  # noqa: E402
import note_table as nt  # noqa: E402
import publications as pub  # noqa: E402

FIELDS = ("product", "journey", "owner", "reviewed", "stages", "health", "published")
COLUMNS = (("id", "id"), ("stage", "етап"), ("step", "крок"), ("lane", "доріжка"), ("text", "текст"), ("level", "рівень"),
           ("target", "ціль"), ("parent", "parent"), ("code", "код"), ("source", "джерело"), ("class", "клас"),
           ("date", "дата"))
REQUIRED = ("id", "stage", "lane", "text")
LANES = (("action", "дії"), ("touchpoint", "точки контакту"), ("experience", "досвід"), ("pain", "болі"),
         ("metric", "метрики"), ("anomaly", "аномалії"), ("opportunity", "можливості"), ("solution", "рішення"),
         ("initiative", "ініціативи"), ("experiment", "експерименти"))
LANE_IDS = tuple(l for l, _ in LANES)
LANE_ALIAS = {uk: lid for lid, uk in LANES}                                    # a lane written by its §2 name
LEVELS = ("stage", "transition", "journey")
CLASSES = ("measured", "observed", "reported", "external", "simulated", "assumed")
REAL = ("measured", "observed", "reported", "external")
LANE_CLASSES = {"action": REAL, "touchpoint": REAL, "experience": REAL, "pain": REAL,
                "metric": ("measured",), "anomaly": ("measured",)}          # the evidence lanes (§2)
PARENTS = {"pain": ("opportunity",), "solution": ("opportunity",), "experiment": ("solution",),
           "initiative": ("pain", "opportunity", "solution")}               # §5; any other lane takes no parent
NEEDS_PARENT = ("solution", "experiment")
DATED = ("pain", "metric", "anomaly")
FINDINGS = ("no_owner", "stale_review", "no_outcome", "empty_stage", "undeclared_stage", "unknown_lane", "no_source",
            "no_class", "wrong_class", "simulated_pain", "bad_level", "bad_target", "bad_date", "bad_code", "orphan",
            "pain_no_action", "few_solutions", "stale_metric", "duplicate_id", "link", "secret", "contact")
MODEL_FINDINGS = ("opportunity_no_story", "two_pains", "person_name")
COMMANDS = ("parse", "check", "render-html", "health", "refresh", "tree", "schema")
REVIEW_DAYS, PAIN_DAYS, MIN_SOLUTIONS = 90, 182, 3
HC_SOURCE = "health-check"
ANOMALY_STATUSES = ("warning", "critical", "positive")
YES = ("так", "yes", "true", "y", "x", "✓", "✅")
NO = ("", "ні", "no", "false", "n", "—", "-")
CODE = re.compile(r"^[A-Z][A-Z0-9]*-\d+(?:\.\d+)*$")
DAY = nt.DAY
Bad = nt.Bad
esc, shown = nt.esc, nt.shown


def _a(word):
    return ("an " if str(word)[:1] in "aeiou" else "a ") + str(word)


def result(**kw):
    print("JOURNEY_RESULT " + json.dumps(kw, ensure_ascii=False))


def day(s):
    """A datetime.date from YYYY-MM-DD, else None."""
    s = str(s or "").strip()
    if not DAY.match(s):
        return None
    try:
        return datetime.date.fromisoformat(s)
    except ValueError:
        return None


def number(s):
    try:
        f = float(str(s).strip().rstrip("%"))
    except (TypeError, ValueError):
        return None
    return int(f) if f.is_integer() else f


# ------------------------------------------------------------------ the note
def _canon(header):
    h = header.strip().strip("`*_ ").lower()
    for name, uk in COLUMNS:
        if h in (name, uk):
            return name
    return None


def load(path):
    """The note as a dict — raises Bad. Row lines keep their index in the note's lines, for an in-place refresh."""
    text, fm, _ = nt.read_note(path)
    try:
        stages = cc.read_yaml_records(fm, "stages")
        health = cc.read_yaml_records(fm, "health")
    except ValueError as e:
        raise Bad("the frontmatter does not read: %s" % e)
    start, end, eol = pub._frontmatter(text)
    lines = text.splitlines(True)
    first = text[:end].count("\n")                  # the line index of the frontmatter's closing line
    title = ""
    table, cols, rows, errors = None, None, [], []
    run = []
    for i in range(first + 1, len(lines) + 1):
        line = lines[i].rstrip("\r\n") if i < len(lines) else ""
        if i < len(lines) and line.strip().startswith("|"):
            run.append((i, line))
            continue
        if not title and i < len(lines) and line.startswith("# "):
            title = line[2:].strip()
        if run and table is None:
            names = [_canon(h) for h in nt.cells(run[0][1])]
            if all(r in names for r in REQUIRED):
                table, cols = run, names
        run = []
    if table is None:
        raise Bad("no row table: a table whose header has %s" % ", ".join(REQUIRED))
    for n, (i, line) in enumerate(table[1:], 2):
        cs = nt.cells(line)
        if nt.is_separator(cs):
            continue
        if len(cs) != len(cols):
            errors.append("row %d (%s): %d cells, the header has %d — %s" % (
                n, cs[0] if cs else "?", len(cs), len(cols),
                "padded with empty cells" if len(cs) < len(cols) else "the extra cells dropped"))
            cs = (cs + [""] * len(cols))[:len(cols)]
        row = {name: "" for name, _ in COLUMNS}
        for name, val in zip(cols, cs):
            if name:
                row[name] = val
        lane = row["lane"].strip().lower()
        row["lane"] = LANE_ALIAS.get(lane, lane)
        row["row"], row["line"], row["cells"] = n, i, cs
        row["gap"] = not row["text"] or row["text"].startswith("⚠")
        if not row["id"] and not row["gap"]:
            errors.append("row %d: a row without an id — named, never checked or refreshed" % n)
        rows.append(row)
    st = []
    for s in stages:
        sid = str(s.get("id") or "").strip()
        if sid:
            st.append({"id": sid, "name": str(s.get("name") or "").strip(), "outcome": str(s.get("outcome") or "").strip()})
    hp = []
    for h in health:
        hp.append({"date": str(h.get("date") or ""), "score": number(h.get("score")), "snapshot": str(h.get("snapshot") or "")})
    header = [h.strip().strip("`*_ ").lower() for h in nt.cells(table[0][1])]
    lang = "uk" if any(h in (uk for _, uk in COLUMNS if uk not in ("id", "parent")) for h in header) else "en"
    return {"path": path, "text": text, "eol": eol, "lines": lines, "cols": cols, "table_end": table[-1][0], "lang": lang,
            "title": title, "product": nt.fm_scalar(fm, "product"), "journey": nt.fm_scalar(fm, "journey"),
            "owner": nt.fm_scalar(fm, "owner"), "reviewed": nt.fm_scalar(fm, "reviewed"), "stages": st, "health": hp,
            "rows": rows, "errors": errors}


def _public(r):
    return {k: r[k] for k in [c for c, _ in COLUMNS] + ["row"]}


def evidence(r):
    """A row that counts as evidence: an evidence lane, a source, a class the lane takes, and a date where the lane
    needs one — never a simulated pain, an unsourced number or a guess."""
    lane = r["lane"]
    return (not r["gap"] and lane in LANE_CLASSES and bool(r["source"]) and r["class"].strip().lower() in LANE_CLASSES[lane]
            and (lane not in DATED or day(r["date"]) is not None))


def page_worthy(r, declared):
    """A row the page shows: placed on a declared stage and a known lane, with its source; in an evidence lane, evidence."""
    if r["gap"] or not r["id"] or r["stage"] not in declared or r["lane"] not in LANE_IDS or not r["source"]:
        return False
    return evidence(r) if r["lane"] in LANE_CLASSES else True


def tree(note, sid):
    rows = [r for r in note["rows"] if not r["gap"] and r["stage"] == sid]
    outcome = next((s["outcome"] for s in note["stages"] if s["id"] == sid), "")

    def kids(pid, lane):
        return [r for r in rows if r["parent"] == pid and r["lane"] == lane]

    def node(r, **more):
        return dict({"id": r["id"], "text": r["text"]}, **more)
    opps = []
    for o in [r for r in rows if r["lane"] == "opportunity"]:
        sols = [node(s, experiments=[node(x, code=x["code"]) for x in kids(s["id"], "experiment")],
                     initiatives=[node(i, code=i["code"]) for i in kids(s["id"], "initiative")])
                for s in kids(o["id"], "solution")]
        pains = [node(p, **{"class": p["class"], "initiatives": [node(i, code=i["code"]) for i in kids(p["id"], "initiative")]})
                 for p in kids(o["id"], "pain")]
        opps.append(node(o, target=o["target"].strip().lower() in YES, pains=pains, solutions=sols,
                         initiatives=[node(i, code=i["code"]) for i in kids(o["id"], "initiative")]))
    target = next((o["id"] for o in opps if o["target"]), None)
    return {"stage": sid, "outcome": outcome, "target": target, "opportunities": opps}


def parse(note):
    declared = [s["id"] for s in note["stages"]]
    grid = {}
    for r in note["rows"]:
        if r["gap"]:
            continue
        grid.setdefault(r["stage"], {l: [] for l in LANE_IDS}).setdefault(r["lane"], []).append(r["id"])
    return {"title": note["title"], "product": note["product"], "journey": note["journey"], "owner": note["owner"],
            "reviewed": note["reviewed"], "stages": note["stages"], "health": note["health"], "lanes": list(LANE_IDS),
            "rows": [_public(r) for r in note["rows"] if not r["gap"]],
            "gaps": [{"row": r["id"], "stage": r["stage"], "lane": r["lane"], "text": r["text"]} for r in note["rows"] if r["gap"]],
            "grid": grid, "trees": {s: tree(note, s) for s in declared}, "errors": note["errors"]}


# ------------------------------------------------------------------ findings
def _chain(rows_by_id, children, pain):
    """The ids of a pain's chain: the pain, the opportunity it hangs under, and everything under either of them."""
    start = [pain["id"]]
    par = rows_by_id.get(pain["parent"])
    if par is not None and par["lane"] == "opportunity" and par["stage"] == pain["stage"]:
        start.append(par["id"])
    seen, todo = set(start), list(start)
    while todo:
        for k in children.get(todo.pop(), []):
            if k["id"] not in seen:
                seen.add(k["id"])
                todo.append(k["id"])
    return seen


def findings(note, today, newest=None):
    out = []

    def f(code, row=None, stage=None, detail=""):
        e = {"finding": code, "detail": detail}
        if row is not None:
            e["row"] = row
        if stage is not None:
            e["stage"] = stage
        out.append(e)
    if not note["owner"]:
        f("no_owner", detail="the note has no owner — a role or a team")
    elif nt.CONTACT.search(note["owner"]):
        f("contact", detail="the owner holds an e-mail or a phone — a role or a team, never a person")
    rv = day(note["reviewed"])
    if rv is None:
        f("stale_review", detail="no review date (YYYY-MM-DD)")
    elif (today - rv).days > REVIEW_DAYS:
        f("stale_review", detail="reviewed %s, %d days ago" % (note["reviewed"], (today - rv).days))
    declared = [s["id"] for s in note["stages"]]
    live = [r for r in note["rows"] if not r["gap"] and r["id"]]
    for s in note["stages"]:
        if not s["outcome"] or "TBD" in s["outcome"]:
            f("no_outcome", stage=s["id"], detail="a stage without its outcome metric and target")
        if not any(r["stage"] == s["id"] and evidence(r) for r in live):
            f("empty_stage", stage=s["id"], detail="no row of evidence — a gap")
    by_id, children = {}, {}
    for r in live:
        if r["id"] in by_id:
            f("duplicate_id", row=r["id"], stage=r["stage"], detail="row %d repeats the id" % r["row"])
        else:
            by_id[r["id"]] = r
    for r in live:
        if r["parent"]:
            children.setdefault(r["parent"], []).append(r)
    newest_day = day(newest)
    for h in note["health"]:
        d = day(h["date"])
        if d and (newest_day is None or d > newest_day):
            newest_day = d
    targets = {}
    for r in live:
        rid, sid, lane, cls = r["id"], r["stage"], r["lane"], r["class"].strip().lower()
        if sid not in declared:
            f("undeclared_stage", row=rid, stage=sid, detail="the stage %s is not in `stages`" % (sid or "(empty)"))
        if lane not in LANE_IDS:
            f("unknown_lane", row=rid, stage=sid, detail="%s is not one of the ten lanes" % (lane or "(empty)"))
        if not r["source"]:
            f("no_source", row=rid, stage=sid, detail="a row without a source marker")
        if lane in LANE_CLASSES:
            if not cls:
                f("no_class", row=rid, stage=sid, detail="an evidence row without its class")
            elif lane == "pain" and cls == "simulated":
                f("simulated_pain", row=rid, stage=sid, detail="simulated input is never a pain")
            elif cls not in LANE_CLASSES[lane]:
                f("wrong_class", row=rid, stage=sid, detail="%s does not take %s (it takes %s)" % (lane, cls, ", ".join(LANE_CLASSES[lane])))
        elif cls and lane in LANE_IDS:
            f("wrong_class", row=rid, stage=sid, detail="%s takes no class (§2) — %s is for the evidence lanes" % (lane, cls))
        elif cls and cls not in CLASSES:
            f("wrong_class", row=rid, stage=sid, detail="%s is not an evidence class" % cls)
        lv = r["level"].strip().lower()
        if lv and (lane != "metric" or lv not in LEVELS):
            f("bad_level", row=rid, stage=sid, detail="level %s on %s row" % (lv, _a(lane or "?")))
        tg = r["target"].strip().lower()
        if tg not in NO:
            if lane != "opportunity" or tg not in YES:
                f("bad_target", row=rid, stage=sid, detail="ціль %r on %s row" % (r["target"], _a(lane or "?")))
            elif sid in targets:
                f("bad_target", row=rid, stage=sid, detail="a second target on %s (the first is %s)" % (sid, targets[sid]))
            else:
                targets[sid] = rid
        dv = day(r["date"])
        if r["date"] and dv is None:
            f("bad_date", row=rid, stage=sid, detail="%r is not YYYY-MM-DD" % r["date"])
        elif not r["date"] and lane in DATED:
            f("bad_date", row=rid, stage=sid, detail="%s without the date of its evidence" % _a(lane))
        if lane == "initiative" and not CODE.match(r["code"].strip()):
            f("bad_code", row=rid, stage=sid, detail="%r is not an epic or feature code" % r["code"] if r["code"] else "an initiative without its code")
        if r["parent"]:
            par = by_id.get(r["parent"])
            if lane not in PARENTS:
                f("orphan", row=rid, stage=sid, detail="%s row takes no parent" % _a(lane or "?"))
            elif par is None:
                f("orphan", row=rid, stage=sid, detail="parent %s names no row" % r["parent"])
            elif par["lane"] not in PARENTS[lane]:
                f("orphan", row=rid, stage=sid, detail="%s cannot hang under %s" % (_a(lane), _a(par["lane"])))
            elif par["stage"] != sid:
                f("orphan", row=rid, stage=sid, detail="parent %s is on another stage (%s)" % (r["parent"], par["stage"]))
        elif lane in NEEDS_PARENT:
            f("orphan", row=rid, stage=sid, detail="%s needs its parent" % _a(lane))
        if lane == "pain" and dv is not None and (today - dv).days > PAIN_DAYS and by_id.get(rid) is r:
            chain = _chain(by_id, children, r)
            if not any(by_id[c]["lane"] in ("initiative", "experiment") for c in chain if c in by_id):
                f("pain_no_action", row=rid, stage=sid, detail="%d days, no initiative or experiment in its chain" % (today - dv).days)
        if lane == "metric" and _is_hc(r) and dv is not None and newest_day is not None and dv < newest_day:
            f("stale_metric", row=rid, stage=sid, detail="%s, older than the newest snapshot %s" % (r["date"], newest_day.isoformat()))
        cells = [r[k] or "" for k in ("text", "step", "source", "code", "parent")]
        if any(nt.LINK.search(x) for x in cells):
            f("link", row=rid, stage=sid, detail="a link in the row's cells — a row carries no link")
        kinds = cn.scan(" \n".join(cells))
        if kinds:
            f("secret", row=rid, stage=sid, detail="the row holds %s — never on the page" % ", ".join(kinds))
        if any(nt.CONTACT.search(x) for x in cells):
            f("contact", row=rid, stage=sid, detail="an e-mail or a phone in the row — a person's contact never on the map")
    for r in live:
        if r["lane"] == "opportunity" and r["target"].strip().lower() in YES:
            n = sum(1 for k in children.get(r["id"], []) if k["lane"] == "solution" and k["stage"] == r["stage"])
            if n < MIN_SOLUTIONS:
                f("few_solutions", row=r["id"], stage=r["stage"], detail="%d solution(s) — compare at least %d" % (n, MIN_SOLUTIONS))
    return out


# ------------------------------------------------------------------ snapshots and health
def inspect_snapshot(path):
    """(a health-check snapshot's frontmatter as a dict, or None; why it is not one)."""
    try:
        text, fm, _ = nt.read_note(path)
    except Bad:
        return None, "no frontmatter — a snapshot saved before v4.7.0, or not a snapshot"
    kind = nt.fm_scalar(fm, "type")
    if kind != "cjm-health-check":
        return None, "type is %s, not cjm-health-check" % (kind or "missing")
    try:
        stages = cc.read_yaml_records(fm, "stages")
    except ValueError:
        stages = []
    score = nt.fm_scalar(fm, "health_score")
    return {"name": os.path.basename(path), "product": nt.fm_scalar(fm, "product"), "date": nt.fm_scalar(fm, "date"),
            "period": nt.fm_scalar(fm, "period"), "score": number(score) if score else None, "stages": stages}, ""


def read_snapshot(path):
    return inspect_snapshot(path)[0]


def _same_product(a, b):
    return a.strip().lower() == b.strip().lower()


def snapshots(folder, product):
    """(points, skipped, newest date, other products' files) of the folder — raises Bad when it does not read. Every
    .md that is not a usable snapshot of the product is named with why, except another product's (kept apart)."""
    if not os.path.exists(folder):                   # no health-check has run yet: an empty trend, never a stop
        return [], [], None, [], True
    try:
        names = sorted(os.listdir(folder))
    except OSError as e:
        raise Bad("the snapshots folder does not read: %s" % (e.strerror or type(e).__name__))
    points, skipped, newest, other = [], [], None, []
    for n in names:
        if not n.endswith(".md"):
            continue
        s, why = inspect_snapshot(os.path.join(folder, n))
        if s is None:
            skipped.append({"snapshot": n, "why": why})
            continue
        if not s["product"]:
            skipped.append({"snapshot": n, "why": "no product in its frontmatter"})
            continue
        if not _same_product(s["product"], product):
            other.append(n)
            continue
        if day(s["date"]) is None:
            skipped.append({"snapshot": n, "why": "no date (YYYY-MM-DD) in its frontmatter"})
            continue
        newest = max(newest or s["date"], s["date"])
        if s["score"] is None:
            skipped.append({"snapshot": n, "why": "no health_score in its frontmatter — never read from the text"})
            continue
        points.append({"date": s["date"], "score": s["score"], "snapshot": n})
    points.sort(key=lambda p: (p["date"], p["snapshot"]))
    return points, skipped, newest, other, False


def merge_points(kept, fresh):
    """The note's points joined with fresh ones: a fresh point replaces the note's point of the same snapshot; the
    note's other points stay (the note is the truth — a folder that lost a snapshot never erases the trend)."""
    by, loose = {}, []
    for p in kept:
        if p.get("snapshot"):
            by[p["snapshot"]] = p
        else:
            loose.append(p)                          # a point the note keeps without its snapshot's name stays as it is
    for p in fresh:
        by[p["snapshot"]] = p
    return sorted(list(by.values()) + loose, key=lambda p: (str(p.get("date") or ""), str(p.get("snapshot") or "")))


def render_health(points, eol):
    if not points:
        return "health: []" + eol
    lines = ["health:"]
    for p in points:
        lines.append("  - date: %s" % json.dumps(p["date"]))
        lines.append("    score: %s" % json.dumps(p["score"]))
        lines.append("    snapshot: %s" % json.dumps(p["snapshot"], ensure_ascii=False))
    return eol.join(lines) + eol


def write_health(path, note, points):
    pub.write_field(path, note["text"], False, "health", lambda eol: render_health(points, eol))


def trend(points):
    points = [p for p in points if isinstance(p.get("score"), (int, float)) and day(p.get("date"))]
    if not points:
        return None
    return {"count": len(points), "first": points[0], "last": points[-1],
            "delta": (points[-1]["score"] - points[0]["score"]) if len(points) > 1 else 0}


# ------------------------------------------------------------------ refresh
def slug(s):
    """A metric's id part: lower case, every run of characters that are not letters or digits one hyphen."""
    return re.sub(r"[\W_]+", "-", str(s or "").lower(), flags=re.U).strip("-")


REFRESH = {
    "uk": {"metric": "{metric}: {value} (база {baseline}, {deviation})", "metric_bare": "{metric}: {value}",
           "anomaly": "{metric}: {deviation} від бази — {status}",
           "status": {"warning": "попередження", "critical": "критично", "positive": "позитивна"},
           "line": "Карту шляху оновлено локально — опублікувати можна в наступному прогоні."},
    "en": {"metric": "{metric}: {value} (baseline {baseline}, {deviation})", "metric_bare": "{metric}: {value}",
           "anomaly": "{metric}: {deviation} vs baseline — {status}",
           "status": {"warning": "warning", "critical": "critical", "positive": "positive"},
           "line": "The journey map was refreshed locally — it can be published in the next run."},
}


def _is_hc(r):
    return r["lane"] in ("metric", "anomaly") and r["source"].startswith(HC_SOURCE)


def wanted_rows(snap, lang, declared):
    """([(id, stage, lane, text)], skipped stages, skipped entries) — a metric per stage entry and an anomaly per
    warning/critical/positive one, for the stages the note declares; ids by the metric's slug (§10)."""
    L = REFRESH.get(lang, REFRESH["en"])
    out, skipped_stages, skipped_entries, seen = [], [], [], set()
    for e in snap["stages"]:
        sid, metric = str(e.get("id") or "").strip(), str(e.get("metric") or "").strip()
        if not sid:
            skipped_entries.append({"stage": "", "why": "an entry without its stage id"})
            continue
        if sid not in declared:
            if sid not in skipped_stages:
                skipped_stages.append(sid)
            continue
        if not metric or not slug(metric):
            skipped_entries.append({"stage": sid, "why": "an entry without its metric — its status is not on the map"})
            continue
        mid = "m-%s-%s" % (sid, slug(metric))
        if mid in seen:
            skipped_entries.append({"stage": sid, "why": "the same metric slug as another entry (%s) — one row per id" % mid})
            continue
        seen.add(mid)
        v = {k: str(e.get(k) or "").strip() for k in ("value", "baseline", "deviation", "status")}
        v["metric"] = metric
        fmt = L["metric"] if v["baseline"] else L["metric_bare"]
        out.append(("m-%s-%s" % (sid, slug(metric)), sid, "metric", fmt.format(**v)))
        if v["status"].lower() in ANOMALY_STATUSES:
            out.append(("a-%s-%s" % (sid, slug(metric)), sid, "anomaly",
                        L["anomaly"].format(metric=metric, deviation=v["deviation"], status=L["status"][v["status"].lower()])))
    return out, skipped_stages, skipped_entries


def refresh_text(note, snap, lang):
    """The note's text with the health-check rows replaced, added and removed — every other byte as it was."""
    source = "%s %s, %s" % (HC_SOURCE, snap["date"], snap["period"]) if snap["period"] else "%s %s" % (HC_SOURCE, snap["date"])
    lines, eol, cols = list(note["lines"]), note["eol"], note["cols"]
    declared = [s["id"] for s in note["stages"]]
    by_id, twice = {}, set()
    for r in note["rows"]:
        if r["id"] in by_id:
            twice.add(r["id"])
        by_id.setdefault(r["id"], r)
    wanted, skipped_stages, skipped_entries = wanted_rows(snap, lang, declared)
    want_ids = {w[0] for w in wanted}
    covered = {w[1] for w in wanted}
    replaced, added, removed, kept = [], [], [], []
    new_line, drop, after = {}, set(), {}
    pos = {c: i for i, c in enumerate(cols) if c}

    def new_row(values):
        return nt.row_line([values.get(c, "") if c else "" for c in cols]) + eol

    for wid, sid, lane, txt in wanted:
        r = by_id.get(wid)
        if r is None:
            after.setdefault(sid, []).append(new_row({"id": wid, "stage": sid, "lane": lane, "text": txt,
                                                     "level": "transition" if lane == "metric" else "",
                                                     "source": source, "class": "measured", "date": snap["date"]}))
            added.append(wid)
        elif wid not in twice and _is_hc(r) and r["lane"] == lane:
            vals = {"text": txt, "source": source, "class": "measured", "date": snap["date"]}
            if any(vals[k] != r[k] for k in vals):
                cells = list(r["cells"])                     # the PM's cells, an unknown column too, stay
                for k, v in vals.items():
                    cells[pos[k]] = v
                new_line[r["line"]] = nt.row_line(cells) + eol
            replaced.append(wid)
        else:
            kept.append(wid)
    for r in note["rows"]:
        if (_is_hc(r) and r["lane"] == "anomaly" and r["stage"] in covered and r["id"].startswith("a-%s-" % r["stage"])
                and r["id"] not in want_ids and r["id"] not in twice):
            drop.add(r["line"])
            removed.append(r["id"])
    last_of = {}
    for r in note["rows"]:
        if r["line"] not in drop:
            last_of[r["stage"]] = r["line"]
    tail = note["table_end"]
    out, inserts = [], {}
    for sid, ls in after.items():
        inserts.setdefault(last_of.get(sid, tail), []).extend(ls)
    for i, line in enumerate(lines):
        if i in drop:
            if i in inserts:
                out.extend(inserts[i])
            continue
        out.append(new_line.get(i, line))
        if i in inserts:
            if not out[-1].endswith("\n"):
                out[-1] += eol
            out.extend(inserts[i])
    return {"text": "".join(out), "replaced": replaced, "added": added, "removed": removed, "kept": kept,
            "skipped_stages": skipped_stages, "skipped_entries": skipped_entries}


def write_text(path, text):
    real = os.path.realpath(path)
    mode = os.stat(real).st_mode & 0o7777
    fd, tmp = tempfile.mkstemp(prefix=".journey-", dir=os.path.dirname(real))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        os.chmod(tmp, mode)
        os.replace(tmp, real)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


# ------------------------------------------------------------------ html
LABELS = {
    "uk": {"title": "Карта шляху", "note": "Нотатка", "owner": "Власник", "reviewed": "Рев'ю", "generated": "Згенеровано",
           "health": "Здоров'я", "no_trend": "тренду немає — у знімках немає health_score у frontmatter",
           "gap": "немає доказів", "target": "ціль", "no_outcome": "⚠️ TBD", "lanes": "Доріжки",
           "not_shown": "Рядків не показано: %d — без джерела чи доказу, поза етапами або доріжками; їх називають знахідки нотатки",
           "lane": dict(LANES)},
    "en": {"title": "Journey map", "note": "Note", "owner": "Owner", "reviewed": "Reviewed", "generated": "Generated",
           "health": "Health", "no_trend": "no trend — no snapshot has health_score in its frontmatter",
           "gap": "no evidence", "target": "target", "no_outcome": "⚠️ TBD", "lanes": "Lanes",
           "not_shown": "Rows not shown: %d — no source or evidence, off the stages or lanes; the note's findings name them",
           "lane": {"action": "Actions", "touchpoint": "Touchpoints", "experience": "Experience", "pain": "Pains",
                    "metric": "Metrics", "anomaly": "Anomalies", "opportunity": "Opportunities", "solution": "Solutions",
                    "initiative": "Initiatives", "experiment": "Experiments"}},
}
CSS = """:root{color-scheme:light}
*{box-sizing:border-box}body{margin:0;padding:24px;background:#f7f7f5;color:#1f2328;font:14px/1.4 -apple-system,"Segoe UI",Roboto,Arial,sans-serif}
h1{font-size:20px;margin:0 0 4px}h2{font-size:16px;margin:18px 0 6px}.meta{color:#57606a;margin:2px 0}
.wrap{overflow-x:auto;margin-top:12px}table.grid{border-collapse:separate;border-spacing:6px}
th,td{vertical-align:top}th.stage{background:#d0ebff;border-radius:6px;padding:6px 8px;text-align:left;min-width:190px}
th.stage .o{color:#57606a;font-size:12px;font-weight:400}th.lane{background:#fff;border-left:4px solid #868e96;border-radius:4px;padding:6px 8px;text-align:left;width:140px;font-weight:600}
.item{background:#fff;border-radius:6px;padding:6px 8px;margin-bottom:6px;border-left:4px solid #adb5bd;max-width:240px}
.item .m{color:#57606a;font-size:11px;margin-top:2px}.item.gap{border:1px dashed #e8590c;color:#e8590c}
.l-pain{border-left-color:#e03131}.l-metric,.l-anomaly{border-left-color:#1c7ed6}.l-opportunity{border-left-color:#f08c00}
.l-solution{border-left-color:#2f9e44}.l-experiment{border-left-color:#7048e8}.l-initiative{border-left-color:#495057}
.target{font-weight:700}svg.spark{background:#fff;border:1px solid #dee2e6;border-radius:4px}
table.pts{border-collapse:collapse;margin-top:6px;background:#fff}table.pts td{border:1px solid #dee2e6;padding:2px 8px}"""


def sparkline(points):
    w, h, pad = 260, 56, 6
    n = len(points)
    xs = [pad + (w - 2 * pad) * (i / (n - 1) if n > 1 else 0.5) for i in range(n)]
    ys = [h - pad - (h - 2 * pad) * max(0.0, min(100.0, float(p["score"]))) / 100.0 for p in points]
    pts = " ".join("%.1f,%.1f" % (x, y) for x, y in zip(xs, ys))
    dots = "".join('<circle cx="%.1f" cy="%.1f" r="3" fill="#1c7ed6"><title>%s: %s</title></circle>' % (x, y, esc(p["date"]), esc(p["score"]))
                   for x, y, p in zip(xs, ys, points))
    return ('<svg class="spark" width="%d" height="%d" viewBox="0 0 %d %d" role="img">'
            '<polyline fill="none" stroke="#1c7ed6" stroke-width="2" points="%s"/>%s</svg>' % (w, h, w, h, pts, dots))


def render_html(note, note_name, lang):
    L = LABELS.get(lang, LABELS["en"])
    live = [r for r in note["rows"] if not r["gap"]]
    title = note["journey"] or note["title"] or note_name
    out = ["<!doctype html>", '<html lang="%s"><head><meta charset="utf-8">' % esc(lang),
           '<meta name="viewport" content="width=device-width,initial-scale=1">',
           "<title>%s — %s</title><style>%s</style></head><body>" % (esc(L["title"]), shown(title), CSS),
           "<h1>%s: %s</h1>" % (esc(L["title"]), shown(title)),
           '<p class="meta">%s: %s · %s · %s: %s · %s: %s</p>' % (
               esc(L["note"]), shown(note_name), shown(note["product"]), esc(L["owner"]), shown(note["owner"] or "⚠️"),
               esc(L["reviewed"]), shown(note["reviewed"] or "⚠️")),
           '<p class="meta">%s: %s</p>' % (esc(L["generated"]), esc(datetime.date.today().isoformat())),
           "<h2>%s</h2>" % esc(L["health"])]
    pts = [p for p in note["health"] if p["score"] is not None and day(p["date"])]
    if pts:
        out.append(sparkline(pts))
        out.append('<table class="pts"><tr>%s</tr><tr>%s</tr><tr>%s</tr></table>' % (
            "".join("<td>%s</td>" % esc(p["date"]) for p in pts), "".join("<td>%s</td>" % esc(p["score"]) for p in pts),
            "".join('<td class="m">%s</td>' % shown(p["snapshot"]) for p in pts)))
    else:
        out.append('<p class="meta">%s</p>' % esc(L["no_trend"]))
    stages = note["stages"]
    declared = [s["id"] for s in stages]
    hidden = sum(1 for r in live if not page_worthy(r, declared))
    if hidden:
        out.append('<p class="meta">%s</p>' % esc(L["not_shown"] % hidden))
    out.append('<div class="wrap"><table class="grid"><thead><tr><th></th>')
    for s in stages:
        out.append('<th class="stage">%s · %s<div class="o">%s</div></th>' % (
            shown(s["id"]), shown(s["name"]), shown(s["outcome"] or L["no_outcome"])))
    out.append("</tr></thead><tbody>")
    has_evidence = {s["id"]: any(r["stage"] == s["id"] and evidence(r) and page_worthy(r, declared) for r in live) for s in stages}
    for li, (lane, _) in enumerate(LANES):
        out.append('<tr><th class="lane">%s</th>' % esc(L["lane"][lane]))
        for s in stages:
            out.append("<td>")
            if li == 0 and not has_evidence[s["id"]]:
                out.append('<div class="item gap">⚠️ %s</div>' % esc(L["gap"]))
            for r in live:
                if r["stage"] != s["id"] or r["lane"] != lane or not page_worthy(r, declared):
                    continue
                tg = r["target"].strip().lower() in YES and lane == "opportunity"
                meta = " · ".join(x for x in (r["step"], r["level"] if lane == "metric" else "", r["code"], r["source"],
                                              r["class"], r["date"], L["target"] if tg else "") if x)
                out.append('<div class="item l-%s%s"><div class="t">%s%s</div><div class="m">%s</div></div>' % (
                    esc(lane), " target" if tg else "", "🎯 " if tg else "", shown(r["text"]), shown(meta)))
            out.append("</td>")
        out.append("</tr>")
    out.append("</tbody></table></div></body></html>")
    return "\n".join(out) + "\n"


# ------------------------------------------------------------------ mermaid
def _mid(rid, used):
    base = "n_" + (re.sub(r"[^A-Za-z0-9_]", "_", rid) or "x")
    m, k = base, 2
    while m in used and used[m] != rid:
        m, k = "%s_%d" % (base, k), k + 1
    used[m] = rid
    return m


def _label(prefix, text):
    s = re.sub(r"\s+", " ", nt.safe(text)).strip()
    if len(s) > 90:
        s = s[:89] + "…"
    s = s.replace('"', "#quot;")
    return '"%s%s"' % (prefix, s)


def mermaid(t):
    used, lines = {}, ["flowchart TD"]
    root = _mid("outcome-" + t["stage"], used)
    lines.append("  %s[%s]" % (root, _label("Outcome: ", t["outcome"] or "⚠️ TBD")))
    for o in t["opportunities"]:
        on = _mid(o["id"], used)
        lines.append("  %s[%s]" % (on, _label(("🎯 " if o["target"] else "") + o["id"] + ": ", o["text"])))
        lines.append("  %s --> %s" % (root, on))
        for p in o["pains"]:
            pn = _mid(p["id"], used)
            lines.append("  %s([%s])" % (pn, _label(p["id"] + ": ", p["text"] + (" (%s)" % p["class"] if p["class"] else ""))))
            lines.append("  %s -.-> %s" % (pn, on))
            for i in p["initiatives"]:
                inn = _mid(i["id"], used)
                lines.append("  %s[[%s]]" % (inn, _label(i["id"] + ": ", "%s %s" % (i["text"], i["code"]))))
                lines.append("  %s --> %s" % (pn, inn))
        for i in o["initiatives"]:
            inn = _mid(i["id"], used)
            lines.append("  %s[[%s]]" % (inn, _label(i["id"] + ": ", "%s %s" % (i["text"], i["code"]))))
            lines.append("  %s --> %s" % (on, inn))
        for s in o["solutions"]:
            sn = _mid(s["id"], used)
            lines.append("  %s[%s]" % (sn, _label(s["id"] + ": ", s["text"])))
            lines.append("  %s --> %s" % (on, sn))
            for x in s["experiments"] + s["initiatives"]:
                xn = _mid(x["id"], used)
                shape = "[/%s/]" if x in s["experiments"] else "[[%s]]"
                lines.append("  %s%s" % (xn, shape % _label(x["id"] + ": ", "%s %s" % (x["text"], x["code"]))))
                lines.append("  %s --> %s" % (sn, xn))
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------------ check 28
def check_protocol(root):
    """Errors for validate-consistency.sh check 28 — the protocol, the script, the vault schema, the publication key
    and the skill's citation agree."""
    errs, texts = [], {}
    for rel in ("references/journey-protocol.md", "references/vault-schema.md", "references/artifact-publishing.md",
                "skills/cjm-research/SKILL.md", "references/vault-protocol.md", "skills/cjm-research/references/cjm-reports.md"):
        try:
            with open(os.path.join(root, rel), encoding="utf-8") as fh:
                texts[rel] = fh.read()
        except OSError:
            errs.append("%s is missing" % rel)
    if "references/journey-protocol.md" not in texts:
        return errs
    proto = texts["references/journey-protocol.md"]
    skill = texts.get("skills/cjm-research/SKILL.md", "")
    if skill and "journey-protocol.md" not in skill:
        errs.append("skills/cjm-research/SKILL.md does not cite references/journey-protocol.md")
    if skill and not re.search(r"^### Step J\b", skill, re.M):
        errs.append("skills/cjm-research/SKILL.md has no «### Step J» — the journey mode's steps")
    vp = texts.get("references/vault-protocol.md", "")
    if vp and not ('IF artifact.type == "cjm-journey":' in vp and "CJM/journeys/{key_slug}/journey-{topic_slug}.md" in vp):
        errs.append("vault-protocol.md: no save-by-name rule for cjm-journey (CJM/journeys/{key_slug}/journey-{topic_slug}.md)")
    rep = texts.get("skills/cjm-research/references/cjm-reports.md", "")
    if rep and "journey_map.py refresh" not in rep:
        errs.append("cjm-reports.md: the automated health-check does not run journey_map.py refresh (journey-protocol.md §10)")
    s7 = nt.section(proto, "7. The note")
    fields = [nt.tick(r[0]) for r in nt.table_after(s7, r"\| Field \| What \|")]
    if fields != list(FIELDS):
        errs.append("journey-protocol.md §7: the frontmatter fields %s ≠ journey_map.py FIELDS %s" % (
            "|".join(f or "?" for f in fields), "|".join(FIELDS)))
    cols = [(nt.tick(r[0]), nt.tick(r[1]) if len(r) > 1 else None) for r in nt.table_after(s7, r"\| Column \| Ukrainian header \| What \|")]
    if cols != list(COLUMNS):
        errs.append("journey-protocol.md §7: the columns %s ≠ journey_map.py COLUMNS %s" % (
            "|".join("%s/%s" % c for c in cols), "|".join("%s/%s" % c for c in COLUMNS)))
    s2 = nt.section(proto, "2. The lanes")
    lanes = [(nt.tick(r[0]), nt.tick(r[1]) if len(r) > 1 else None) for r in nt.table_after(s2, r"\| Lane \| Ukrainian name \|")]
    if lanes != list(LANES):
        errs.append("journey-protocol.md §2: the lanes %s ≠ journey_map.py LANES %s" % (
            "|".join("%s/%s" % l for l in lanes), "|".join("%s/%s" % l for l in LANES)))
    classes = {nt.tick(r[0]): set(re.findall(r"`([a-z]+)`", r[2].split("(")[0])) for r in nt.table_after(s2, r"\| Lane \| Ukrainian name \|")
               if len(r) > 2 and nt.tick(r[0])}
    want = {l: set(LANE_CLASSES.get(l, ())) for l in LANE_IDS}
    for l in LANE_IDS:
        if classes.get(l, set()) != want[l]:
            errs.append("journey-protocol.md §2: lane %s takes %s ≠ journey_map.py LANE_CLASSES %s" % (
                l, "|".join(sorted(classes.get(l, set()))) or "—", "|".join(sorted(want[l])) or "—"))
    s5 = nt.section(proto, "5. The opportunity tree")
    parents, needs = {}, set()
    for r in nt.table_after(s5, r"\| Lane \| Its parent \|"):
        lane = nt.tick(r[0])
        if lane and len(r) > 1:
            parents[lane] = tuple(sorted(re.findall(r"`([a-z]+)`", r[1])))
            if "required" in r[1]:
                needs.add(lane)
    if parents != {k: tuple(sorted(v)) for k, v in PARENTS.items()} or needs != set(NEEDS_PARENT):
        errs.append("journey-protocol.md §5: the parents %s (required: %s) ≠ journey_map.py PARENTS %s (required: %s)" % (
            parents, "|".join(sorted(needs)), {k: tuple(sorted(v)) for k, v in PARENTS.items()}, "|".join(NEEDS_PARENT)))
    s4 = nt.section(proto, "4. Metrics by level")
    levels = [nt.tick(r[0]) or "?" for r in nt.table_after(s4, r"\| Level \| Where \|")]
    if levels != list(LEVELS):
        errs.append("journey-protocol.md §4: the levels %s ≠ journey_map.py LEVELS %s" % ("|".join(levels), "|".join(LEVELS)))
    s6 = nt.section(proto, "6. Checks")
    rows6 = nt.table_after(s6, r"\| Finding \| Who \|")
    script = sorted(nt.tick(r[0]) or "?" for r in rows6 if len(r) > 1 and r[1].strip() == "script")
    model = sorted(nt.tick(r[0]) or "?" for r in rows6 if len(r) > 1 and r[1].strip() == "model")
    if script != sorted(FINDINGS):
        errs.append("journey-protocol.md §6: the script's findings %s ≠ journey_map.py FINDINGS %s" % (
            "|".join(script), "|".join(sorted(FINDINGS))))
    if model != sorted(MODEL_FINDINGS):
        errs.append("journey-protocol.md §6: the model's findings %s ≠ journey_map.py MODEL_FINDINGS %s" % (
            "|".join(model), "|".join(sorted(MODEL_FINDINGS))))
    rule = {nt.tick(r[0]): r[2] if len(r) > 2 else "" for r in rows6}
    words = {3: "three"}
    for code, phrase, const in (("stale_review", "older than %d days" % REVIEW_DAYS, "REVIEW_DAYS"),
                                ("pain_no_action", "older than %d days" % PAIN_DAYS, "PAIN_DAYS"),
                                ("few_solutions", "fewer than %s solutions" % words.get(MIN_SOLUTIONS, MIN_SOLUTIONS), "MIN_SOLUTIONS")):
        if phrase not in rule.get(code, ""):
            errs.append("journey-protocol.md §6: %s does not say «%s» (journey_map.py %s)" % (code, phrase, const))
    s9 = nt.section(proto, "9. The script")
    cmds = sorted({nt.cmd_name(r[0]) for r in nt.table_after(s9, r"\| Command \| What \|")})
    if cmds != sorted(COMMANDS):
        errs.append("journey-protocol.md §9: the commands %s ≠ journey_map.py COMMANDS %s" % (
            "|".join(cmds), "|".join(sorted(COMMANDS))))
    vs = texts.get("references/vault-schema.md", "")
    if vs:
        if not re.search(r"^\| cjm-journey \| cjm-research \| CJM/journeys/ \|", vs, re.M):
            errs.append("vault-schema.md: no `cjm-journey` type row (cjm-research, CJM/journeys/)")
        if '"cjm-journey": "CJM/journeys/"' not in vs:
            errs.append("vault-schema.md: TYPE_FOLDER_MAP has no cjm-journey → CJM/journeys/")
        m = re.search(r"^#### cjm-health-check\n(.*?)(?=^#### |\Z)", vs, re.M | re.S)
        block = m.group(1) if m else ""
        missing = [k for k in ("health_score", "date", "period", "stages") if not re.search(r"^%s:" % k, block, re.M)]
        if missing:
            errs.append("vault-schema.md: the cjm-health-check fields lack %s (a journey map reads them)" % ", ".join(missing))
    ap = nt.section(texts.get("references/artifact-publishing.md", ""), "5. Publish and record")
    if texts.get("references/artifact-publishing.md") and not re.search(
            r"^\|\s*`cjm-research`\s*\|.*`cjm-research/<product>/journey-", ap, re.M):
        errs.append("artifact-publishing.md §5: the `cjm-research` key row has no `journey-` key")
    return errs


# ------------------------------------------------------------------ commands
def _today(args):
    if not getattr(args, "today", None):
        return datetime.date.today()
    d = day(args.today)
    if d is None:
        raise Bad("--today is not YYYY-MM-DD")
    return d


def cmd_parse(args):
    result(ok=True, **parse(load(args.note)))
    return 0


def cmd_check(args):
    note = load(args.note)
    today = _today(args)
    newest = None
    if args.snapshots:
        _, _, newest, _, missing = snapshots(args.snapshots, note["product"])
    result(ok=True, findings=findings(note, today, newest), newest_snapshot=newest,
           folder="missing" if args.snapshots and missing else "read" if args.snapshots else None, errors=note["errors"])
    return 0


def _render_to(note, out, lang):
    page = render_html(note, os.path.basename(note["path"]), lang)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(page)
    return len(page.encode("utf-8"))


def cmd_render(args):
    note = load(args.note)
    try:
        size = _render_to(note, args.out, args.lang)
    except OSError as e:
        result(ok=False, error="the page cannot be written: %s" % (e.strerror or type(e).__name__))
        return 1
    declared = [s["id"] for s in note["stages"]]
    live = [r for r in note["rows"] if not r["gap"]]
    result(ok=True, out=args.out, bytes=size, rows=len(live), not_shown=sum(1 for r in live if not page_worthy(r, declared)),
           stages=len(note["stages"]), health=len(note["health"]), errors=note["errors"])
    return 0


def cmd_health(args):
    note = load(args.note)
    if not note["product"]:
        raise Bad("the note names no product")
    fresh, skipped, _, other, missing = snapshots(args.snapshots, note["product"])
    points = merge_points(note["health"], fresh)
    names = {p["snapshot"] for p in fresh}
    kept = [p for p in points if p["snapshot"] not in names]
    try:
        write_health(args.note, note, points)
    except OSError as e:
        result(ok=False, error="the note cannot be written: %s" % (e.strerror or type(e).__name__))
        return 1
    result(ok=True, points=points, kept=kept, skipped=skipped, other_products=other, trend=trend(points),
           folder="missing" if missing else "read", errors=note["errors"])
    return 0


def cmd_refresh(args):
    note = load(args.note)
    snap = read_snapshot(args.snapshot)
    if snap is None:
        raise Bad("%s is not a health-check snapshot (type: cjm-health-check)" % os.path.basename(args.snapshot))
    if not _same_product(snap["product"], note["product"]):
        raise Bad("the snapshot is of product %r, the note of %r" % (snap["product"], note["product"]))
    if day(snap["date"]) is None:
        raise Bad("the snapshot has no date (YYYY-MM-DD) in its frontmatter")
    hc_dates = [r["date"] for r in note["rows"] if not r["gap"] and _is_hc(r) and day(r["date"])]
    if hc_dates and max(hc_dates) > snap["date"]:
        raise Bad("the snapshot (%s) is older than the map's health-check rows (%s) — a refresh never rolls them back"
                  % (snap["date"], max(hc_dates)))
    missing_cols = [c for c in ("source", "class", "date") if c not in note["cols"]]
    if missing_cols:
        raise Bad("the table has no %s column — a health-check row needs its source, class and date (§7)" % ", ".join(missing_cols))
    lang = args.lang or note["lang"]
    done = refresh_text(note, snap, lang)
    text = done["text"]
    point, skipped = None, []
    try:
        if snap["score"] is None:
            skipped.append({"snapshot": snap["name"], "why": "no health_score in its frontmatter — never read from the text"})
            if text != note["text"]:
                write_text(args.note, text)
        else:
            point = {"date": snap["date"], "score": snap["score"], "snapshot": snap["name"]}
            points = merge_points(note["health"], [point])
            note["text"] = text
            write_health(args.note, note, points)
    except OSError as e:
        result(ok=False, error="the note cannot be written: %s" % (e.strerror or type(e).__name__))
        return 1
    out = args.out or os.path.splitext(args.note)[0] + ".html"
    summary = dict(snapshot=snap["name"], date=snap["date"], replaced=done["replaced"], added=done["added"],
                   removed=done["removed"], kept=done["kept"], skipped_stages=done["skipped_stages"],
                   skipped_entries=done["skipped_entries"], health=point, skipped=skipped, out=out, published=False,
                   note_written=True, errors=note["errors"])
    try:
        _render_to(load(args.note), out, lang)
    except OSError as e:                             # the note is refreshed; only its page is not
        result(ok=False, error="the note is refreshed, the page cannot be written: %s" % (e.strerror or type(e).__name__), **summary)
        return 1
    result(ok=True, line=REFRESH.get(lang, REFRESH["en"])["line"], **summary)
    return 0


def cmd_tree(args):
    note = load(args.note)
    declared = [s["id"] for s in note["stages"]]
    if args.stage not in declared:
        raise Bad("the map declares no stage %r (stages: %s)" % (args.stage, ", ".join(declared) or "none"))
    t = tree(note, args.stage)
    mm = mermaid(t)
    if args.out:
        try:
            with open(args.out, "w", encoding="utf-8") as fh:
                fh.write(mm)
        except OSError as e:
            result(ok=False, error="the Mermaid file cannot be written: %s" % (e.strerror or type(e).__name__))
            return 1
    found = [f for f in findings(note, datetime.date.today()) if f["finding"] == "few_solutions" and f.get("stage") == args.stage]
    tg = next((o for o in t["opportunities"] if o["id"] == t["target"]), None)
    result(ok=True, stage=args.stage, outcome=t["outcome"], target=t["target"],
           solutions=len(tg["solutions"]) if tg else None, opportunities=len(t["opportunities"]), mermaid=mm,
           findings=found, out=args.out, errors=note["errors"])
    return 0


def cmd_schema(args):
    result(ok=True, fields=list(FIELDS), columns=[list(c) for c in COLUMNS], lanes=[list(l) for l in LANES],
           lanes_order=list(LANE_IDS), levels=list(LEVELS), classes=list(CLASSES), findings=list(FINDINGS),
           model_findings=list(MODEL_FINDINGS), commands=list(COMMANDS), errors=check_protocol(os.path.dirname(HERE)))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="journey_map.py", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("parse").add_argument("--note", required=True)
    p = sub.add_parser("check")
    p.add_argument("--note", required=True)
    p.add_argument("--snapshots", help="the health-check folder: a metric older than its newest snapshot is stale")
    p.add_argument("--today", help="YYYY-MM-DD (default: today)")
    p = sub.add_parser("render-html")
    p.add_argument("--note", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--lang", default="en", choices=sorted(LABELS))
    p = sub.add_parser("health")
    p.add_argument("--note", required=True)
    p.add_argument("--snapshots", required=True, help="~/.grow-pm/knowledge-library/health-checks/")
    p = sub.add_parser("refresh")
    p.add_argument("--note", required=True)
    p.add_argument("--snapshot", required=True, help="the health-check snapshot the scheduled run just saved")
    p.add_argument("--out", help="the page (default: next to the note, .html)")
    p.add_argument("--lang", choices=sorted(LABELS), help="default: the language of the note's table headers")
    p = sub.add_parser("tree")
    p.add_argument("--stage", required=True)
    p.add_argument("--note", required=True)
    p.add_argument("--out", help="write the Mermaid text to this file too")
    sub.add_parser("schema")
    try:
        args = ap.parse_args(argv)
    except SystemExit as e:                          # a wrong argument still ends with the result line
        if e.code in (0, None):
            return 0
        result(ok=False, error="wrong arguments — see journey_map.py <command> --help")
        return 2
    fn = {"parse": cmd_parse, "check": cmd_check, "render-html": cmd_render, "health": cmd_health,
          "refresh": cmd_refresh, "tree": cmd_tree, "schema": cmd_schema}.get(args.cmd)
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
