#!/usr/bin/env python3
"""journey_map.py — the journey map's note: parse, check, render, health trend, scheduled refresh, opportunity tree
(references/journey-protocol.md, since v4.7.0).

  parse        the row table of the note as stages × lanes, the gap rows and each stage's opportunity tree
  check        the script's findings of the protocol (§6), each with its row or stage — proposals, never a block
  render-html  one self-contained HTML page of the map: no request, no link, every text escaped, light theme
  health       the `health` field from the health-check snapshots' frontmatter — every other byte of the note kept
  refresh      the scheduled health-check's refresh: only the health-check rows replaced by id, the health point, the page
  tree         a stage's opportunity tree as Mermaid text (diagram-prototyper renders it)
  board-layout the board's grid (v4.8.0): stages across, lanes down, a cell per lane of every stage, the rows the page shows
  board-state  the board read back after a publication, kept with which element is which cell, row, header or team item
  board-diff   the board's last state against a read-back: what the team changed, moved, added and removed, the
               health-check edits apart (named, never taken)
  board-take   what the PM took from the board into the note — every other byte kept; --dry-run is the preview
  nest         the nesting (v4.10.0): the map's subtree of child maps by their `parent` links, each child's roll-up
               (pains by class, anomalies, outcome metric, last health point) — never a copy of a row — and the
               findings of the nesting; nothing written
  schema       the fields, columns, lanes, levels, findings, board roles and commands the protocol must agree with
               (checks 28 and 29)

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
import board_state as bs  # noqa: E402  — a board read back (shared with story_map.py, v4.8.0)
import ctx_never as cn  # noqa: E402
import note_table as nt  # noqa: E402
import publications as pub  # noqa: E402

FIELDS = ("product", "journey", "owner", "reviewed", "stages", "parent", "parent_stage", "parent_step", "health", "published")
NEST_FIELDS = ("parent", "parent_stage", "parent_step")                       # the link lives in the child (§14)
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
COMMANDS = ("parse", "check", "render-html", "health", "refresh", "tree", "board-layout", "board-state", "board-diff",
            "board-take", "nest", "schema")
NEST_FINDINGS = ("orphan_child", "nest_cycle", "too_deep", "other_product_parent", "self_parent")
ORPHAN_WHY = ("no_parent", "no_stage", "no_stage_in_parent", "no_step")       # why a child hangs on nothing (§14)
MAX_DEPTH = 3                                    # root → child → grandchild (R38); deeper is a reference by name only
OUTCOME_TBD = "⚠️ TBD"
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
            "rows": rows, "errors": errors, "type": nt.fm_scalar(fm, "type"),
            "parent": nt.fm_scalar(fm, "parent"), "parent_stage": nt.fm_scalar(fm, "parent_stage"),
            "parent_step": nt.fm_scalar(fm, "parent_step")}


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
            "parent": note["parent"], "parent_stage": note["parent_stage"], "parent_step": note["parent_step"],
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


def hc_status(text):
    """The health-check status a refreshed anomaly row ends with — «— <label>» by REFRESH's own labels, in either
    language (the portfolio and the nesting read it alike); None for any other ending — a word inside the text, or a
    row the PM wrote, is no status."""
    t = str(text or "").rstrip()
    for L in REFRESH.values():
        for code, label in L["status"].items():
            if t.endswith("— " + label):
                return code
    return None


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
.wrap{overflow:auto;margin-top:12px;max-height:max(320px,80vh);border:1px solid #dee2e6;border-radius:8px;background:#f7f7f5;cursor:grab;touch-action:pan-x pan-y}
.wrap.panning{cursor:grabbing;user-select:none}.wrap:focus-visible{outline:2px solid #1c7ed6;outline-offset:2px}
table.grid{border-collapse:separate;border-spacing:6px}
th,td{vertical-align:top}th.stage{position:sticky;top:0;z-index:2;background:#d0ebff;border-radius:6px;padding:6px 8px;text-align:left;min-width:190px;box-shadow:0 -6px 0 #f7f7f5}
th.stage .o{color:#57606a;font-size:12px;font-weight:400}th.lane{position:sticky;left:0;z-index:1;background:#fff;border-left:4px solid #868e96;border-radius:4px;padding:6px 8px;text-align:left;width:140px;font-weight:600;box-shadow:-6px 0 0 #f7f7f5}
th.corner{position:sticky;top:0;left:0;z-index:3;background:#f7f7f5}
.item{background:#fff;border-radius:6px;padding:6px 8px;margin-bottom:6px;border-left:4px solid #adb5bd;max-width:240px}
.item .m{color:#57606a;font-size:11px;margin-top:2px}.item.gap{border:1px dashed #e8590c;color:#e8590c}
.l-pain{border-left-color:#e03131}.l-metric,.l-anomaly{border-left-color:#1c7ed6}.l-opportunity{border-left-color:#f08c00}
.l-solution{border-left-color:#2f9e44}.l-experiment{border-left-color:#7048e8}.l-initiative{border-left-color:#495057}
.target{font-weight:700}svg.spark{background:#fff;border:1px solid #dee2e6;border-radius:4px}
table.pts{border-collapse:collapse;margin-top:6px;background:#fff}table.pts td{border:1px solid #dee2e6;padding:2px 8px}"""


# The page's one script (since v4.8.0, R29): the grid pans with the mouse held down. Fixed bytes — no data of the note
# ever goes into it — and no request.
PAN = ('(function(){var w=document.querySelector(".wrap");if(!w)return;var p=null;'
       'w.addEventListener("pointerdown",function(e){if(e.button!==0)return;'
       'p={x:e.clientX,y:e.clientY,l:w.scrollLeft,t:w.scrollTop,i:e.pointerId,m:false};});'
       'w.addEventListener("pointermove",function(e){if(!p)return;var dx=e.clientX-p.x,dy=e.clientY-p.y;'
       'if(!p.m&&Math.abs(dx)+Math.abs(dy)<4)return;if(!p.m){p.m=true;try{w.setPointerCapture(p.i)}catch(_){}'
       'w.classList.add("panning");}w.scrollLeft=p.l-dx;w.scrollTop=p.t-dy;});'
       'function end(){if(!p)return;if(p.m){try{w.releasePointerCapture(p.i)}catch(_){}}p=null;w.classList.remove("panning");}'
       'w.addEventListener("pointerup",end);w.addEventListener("pointercancel",end);})();')


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


# The tree page's one script (since v4.10.0, §14) — on a page that has child maps only, so a map without children keeps
# the v4.8.0 page byte for byte: every grid pans as PAN's one does, and a roll-up chip (or Enter on it) opens its child's
# <details> and the ones around it. Fixed bytes — no data of a note ever goes into it — and no request.
PAN_TREE = ('(function(){document.querySelectorAll(".wrap").forEach(function(w){var p=null;'
            'w.addEventListener("pointerdown",function(e){if(e.button!==0)return;w._moved=false;'
            'p={x:e.clientX,y:e.clientY,l:w.scrollLeft,t:w.scrollTop,i:e.pointerId,m:false};});'
            'w.addEventListener("pointermove",function(e){if(!p)return;var dx=e.clientX-p.x,dy=e.clientY-p.y;'
            'if(!p.m&&Math.abs(dx)+Math.abs(dy)<4)return;if(!p.m){p.m=true;try{w.setPointerCapture(p.i)}catch(_){}'
            'w.classList.add("panning");}w.scrollLeft=p.l-dx;w.scrollTop=p.t-dy;});'
            'function end(){if(!p)return;if(p.m){w._moved=true;try{w.releasePointerCapture(p.i)}catch(_){}}p=null;'
            'w.classList.remove("panning");}w.addEventListener("pointerup",end);w.addEventListener("pointercancel",end);});'
            'function open(id){var d=document.getElementById(id);if(!d)return;for(var x=d;x;x=x.parentElement){'
            'if(x.tagName==="DETAILS")x.open=true;}d.scrollIntoView({block:"start"});}'
            'document.querySelectorAll("[data-open]").forEach(function(c){var go=function(){var w=c.closest(".wrap");'
            'if(w&&w._moved){w._moved=false;return;}open(c.getAttribute("data-open"));};c.addEventListener("click",go);'
            'c.addEventListener("keydown",function(e){if(e.key==="Enter"||e.key===" "){e.preventDefault();go();}});});})();')
CSS_TREE = """
.item.chip{border-left-color:#7048e8;background:#f3f0ff;cursor:pointer}.item.chip:focus-visible{outline:2px solid #7048e8}
.item.ref{border-left-color:#868e96;border-style:dashed;font-style:italic}
details.child{margin:16px 0 0;border-left:3px solid #d0bfff;padding-left:12px}details.child>summary{cursor:pointer;font-weight:600;margin:4px 0}
details.child>summary .m{color:#57606a;font-weight:400;font-size:12px}"""
TREE_LABELS = {"uk": {"children": "Дочірні карти", "above": "Над нею: %s", "level": "рівень %d", "deeper": "окрема карта, рівень %d — "
                      "відкрий її нотатку (глибше трьох рівнів — лише назва)", "deeper_list": "Глибше — окремі карти: %s"},
               "en": {"children": "Child maps", "above": "Above it: %s", "level": "level %d", "deeper": "a map of its own, level %d — "
                      "open its note (past three levels — a name only)", "deeper_list": "Deeper — maps of their own: %s"}}


def _grid(note, L, chips=None):
    """The lines of one map's grid: the rows the page may show, the gap marks, and — on a tree page — the chips of its
    child maps at the top of their stage's first lane (`chips`: {stage id: [html]})."""
    chips = chips or {}
    out = []
    live = [r for r in note["rows"] if not r["gap"]]
    stages = note["stages"]
    declared = [s["id"] for s in stages]
    hidden = sum(1 for r in live if not page_worthy(r, declared))
    if hidden:
        out.append('<p class="meta">%s</p>' % esc(L["not_shown"] % hidden))
    out.append('<div class="wrap" tabindex="0"><table class="grid"><thead><tr><th class="corner"></th>')
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
            if li == 0:
                out.extend(chips.get(s["id"], []))
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
    out.append("</tbody></table></div>")
    return out


def _tree_parts(nest, lang):
    """(chips of the map's own grid, the lines of its children's <details>) of a tree page — each child's grid, its
    own chips and children nested, the first level past MAX_DEPTH as references by name."""
    L, T, NL = LABELS.get(lang, LABELS["en"]), TREE_LABELS.get(lang, TREE_LABELS["en"]), NEST_LABELS.get(lang, NEST_LABELS["en"])
    maps, counter = nest["maps"], [0]

    def parts(n):
        chips, body = {}, []
        for k in n["children"]:
            counter[0] += 1
            nid = "n%d" % counter[0]
            step = (" · %s «%s»" % (NL["step"], k["step"])) if k["step"] else ""
            chips.setdefault(k["stage"], []).append(
                '<div class="item chip" data-open="%s" role="button" tabindex="0"><div class="t">↳ «%s»%s</div>'
                '<div class="m">%s · %s</div></div>' % (nid, esc(k["journey"]), esc(step), esc(k["note"] + ".md"),
                                                         esc(_rollup_words(k["rollup"], NL))))
            kn = maps[k["note"]]
            kchips, kbody = parts(k)
            body.append('<details class="child" id="%s"><summary>%s%s → «%s» · %s<span class="m"> · %s · %s</span></summary>' % (
                nid, esc(k["stage"]), esc(step), esc(k["journey"]), esc(T["level"] % k["level"]), esc(k["note"] + ".md"),
                esc(_rollup_words(k["rollup"], NL))))
            body.append('<p class="meta">%s: %s · %s · %s: %s · %s: %s</p>' % (
                esc(L["note"]), esc(k["note"] + ".md"), shown(kn["product"]), esc(L["owner"]), shown(kn["owner"] or "⚠️"),
                esc(L["reviewed"]), shown(kn["reviewed"] or "⚠️")))
            body.extend(_grid(kn, L, kchips))
            body.extend(kbody)
            body.append("</details>")
        for x in n["deeper"]:
            chips.setdefault(x["stage"], []).append(
                '<div class="item ref"><div class="t">↳ «%s»%s</div><div class="m">%s · %s</div></div>' % (
                    esc(x["journey"]), esc((" · %s «%s»" % (NL["step"], x["step"])) if x["step"] else ""),
                    esc(x["note"] + ".md"), esc(T["deeper"] % x["level"])))
        if n["deeper"]:
            body.append('<p class="meta">%s</p>' % esc(T["deeper_list"] % ", ".join(
                "«%s» (%s.md)" % (x["journey"], x["note"]) for x in n["deeper"])))
        return chips, body
    return parts(nest["tree"])


def render_html(note, note_name, lang, nest=None):
    """The page of the map — and, given its nesting (`nest_of`) with child maps, maps above it or references past the
    depth, the tree page of §14: the same grid with a roll-up chip on each child's step and each child's grid in a
    <details> below. A map without any of them is the page of v4.9.0, byte for byte."""
    L = LABELS.get(lang, LABELS["en"])
    tree = nest is not None and bool(nest["tree"]["children"] or nest["tree"]["deeper"] or nest["ancestors"])
    T = TREE_LABELS.get(lang, TREE_LABELS["en"])
    title = note["journey"] or note["title"] or note_name
    out = ["<!doctype html>", '<html lang="%s"><head><meta charset="utf-8">' % esc(lang),
           '<meta name="viewport" content="width=device-width,initial-scale=1">',
           "<title>%s — %s</title><style>%s</style></head><body>" % (esc(L["title"]), shown(title), CSS + (CSS_TREE if tree else "")),
           "<h1>%s: %s</h1>" % (esc(L["title"]), shown(title)),
           '<p class="meta">%s: %s · %s · %s: %s · %s: %s</p>' % (
               esc(L["note"]), shown(note_name), shown(note["product"]), esc(L["owner"]), shown(note["owner"] or "⚠️"),
               esc(L["reviewed"]), shown(note["reviewed"] or "⚠️")),
           '<p class="meta">%s: %s</p>' % (esc(L["generated"]), esc(datetime.date.today().isoformat()))]
    if tree and nest["ancestors"]:
        out.append('<p class="meta">%s</p>' % esc(T["above"] % " → ".join(
            "«%s» (%s)" % (a["journey"], a["note"]) for a in nest["ancestors"])))
    out.append("<h2>%s</h2>" % esc(L["health"]))
    pts = [p for p in note["health"] if p["score"] is not None and day(p["date"])]
    if pts:
        out.append(sparkline(pts))
        out.append('<table class="pts"><tr>%s</tr><tr>%s</tr><tr>%s</tr></table>' % (
            "".join("<td>%s</td>" % esc(p["date"]) for p in pts), "".join("<td>%s</td>" % esc(p["score"]) for p in pts),
            "".join('<td class="m">%s</td>' % shown(p["snapshot"]) for p in pts)))
    else:
        out.append('<p class="meta">%s</p>' % esc(L["no_trend"]))
    chips, body = _tree_parts(nest, lang) if tree else ({}, [])
    out.extend(_grid(note, L, chips))
    if body:
        out.append("<h2>%s</h2>" % esc(T["children"]))
        out.extend(body)
    out.append("<script>%s</script>" % (PAN_TREE if tree else PAN))
    out.append("</body></html>")
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


# ------------------------------------------------------------------ nesting (§14, since v4.10.0)
NEST_LABELS = {
    "uk": {"head": "Дерево «%s» (%s) · рівень %d · дочірніх карт у дереві %d", "pains": "болі", "anomalies": "аномалії",
           "critical": "критичних %d", "outcome": "результат", "health": "здоров'я", "no_snapshot": "немає знімка",
           "reviewed": "рев'ю", "step": "крок", "deeper": "глибше — лише посилання, рівень %d (too_deep)",
           "findings": "Знахідки вкладеності:", "skipped": "Пропущено", "ancestors": "Над нею: %s", "none": "дочірніх карт немає",
           "level": "рівень"},
    "en": {"head": "Tree «%s» (%s) · level %d · child maps in the tree %d", "pains": "pains", "anomalies": "anomalies",
           "critical": "critical %d", "outcome": "outcome", "health": "health", "no_snapshot": "no snapshot",
           "reviewed": "reviewed", "step": "step", "deeper": "deeper — a reference only, level %d (too_deep)",
           "findings": "Findings of the nesting:", "skipped": "Skipped", "ancestors": "Above it: %s", "none": "no child maps",
           "level": "level"},
}
NEST_SKIPS = ("unreadable", "wrong_type", "sensitive", "duplicate")


def link_name(value):
    """A map's name from a `parent` value: `journey-<slug>`, also written as `[[journey-<slug>]]` (an alias or a heading
    after it dropped), with `.md` or a folder before it — the name alone."""
    s = str(value or "").strip()
    m = re.match(r"^\[\[([^\]|#]*)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]$", s)
    if m:
        s = m.group(1).strip()
    s = s.replace("\\", "/").rsplit("/", 1)[-1].strip()
    return s[:-3] if s.lower().endswith(".md") else s


def _product_key(p):
    import ctx_search as cs_                         # one product is one key, as `ctx search --type` compares it
    return cs_.product_key(p)


def nest_maps(note_path, maps=(), dirs=()):
    """({name: note}, skipped, counts) — the journey maps the nesting reads: the note itself, the maps given and every .md
    directly inside each folder — with neither maps nor folders, the note's own folder (§7: the product's maps live in
    one). A file is read once (two spellings of one file are one); a file iCloud has not downloaded is never opened; a
    note the search marks sensitive is never read in; a note of another type is no map (a hand CJM note never nests);
    the first map of a name is kept — the link is by name. Only read, never written."""
    import ctx_index as ci
    items = [(note_path, True)] + [(p, True) for p in maps or ()]
    folders = list(dirs or ()) if (maps or dirs) else [os.path.dirname(os.path.abspath(note_path))]
    for f in folders:
        if not os.path.isdir(f):
            raise Bad("%s is not a folder" % f)
        try:
            names = sorted(os.listdir(f))
        except OSError as e:
            raise Bad("the folder does not read: %s" % (e.strerror or type(e).__name__))
        items += [(os.path.join(f, n), False) for n in names if n.lower().endswith(".md")]
    out, skipped, seen = {}, [], set()
    counts = {"ignored": 0, "undownloaded": 0}

    def skip(path, reason, detail):
        skipped.append({"note": os.path.basename(path), "reason": reason, "detail": detail})
    for path, named in items:
        try:
            st = os.stat(path)
            ident = (st.st_dev, st.st_ino)
        except OSError:
            ident = os.path.realpath(path)
        if ident in seen:
            continue
        seen.add(ident)
        if os.path.isfile(path) and ci.is_dataless(path):     # never opened: opening it would start a download
            if named:
                skip(path, "unreadable", "the file is not downloaded from iCloud — open it in Obsidian")
            else:
                counts["undownloaded"] += 1
            continue
        try:
            raw, fm, _ = nt.read_note(path)
        except Bad as e:
            if named:
                skip(path, "unreadable", str(e))
            else:
                counts["ignored"] += 1               # a folder's plain markdown is no map
            continue
        kind = nt.fm_scalar(fm, "type").strip().lower()
        if kind != "cjm-journey":
            if named:
                skip(path, "wrong_type", "type: %s — not a journey map" % (nt.safe(kind) or "—"))
            else:
                counts["ignored"] += 1
            continue
        if ci.note_meta(path.replace(os.sep, "/"), raw)["sensitive"]:
            skip(path, "sensitive", "a sensitive note — never read into the tree")
            continue
        try:
            note = load(path)
        except Bad as e:
            skip(path, "unreadable", str(e))
            continue
        name = os.path.splitext(os.path.basename(path))[0]
        if name in out:
            skip(path, "duplicate", "a second map named %s — the first is kept (a link is by name)" % name)
            continue
        out[name] = note
    return out, skipped, counts


def nest_forest(maps):
    """The nesting of the maps (§14): {parent: {child: parent}, children: {parent: [children]}, level: {map: n},
    findings}. A child's link attaches it only when its parent is a map of the same product that declares its
    `parent_stage` and, with a `parent_step`, has a row of that step on that stage — else a finding, never a guess. A
    cycle is named once and broken: each map of it stands alone. A level counts from the top root; past MAX_DEPTH a
    map is too_deep — a reference by name only."""
    found, par = [], {}

    def f(code, name, detail, **more):
        found.append(dict({"finding": code, "note": name, "detail": detail}, **more))
    for name in sorted(maps):
        n = maps[name]
        p = link_name(n.get("parent"))
        if not p:
            continue
        if p == name:
            f("self_parent", name, "the map names itself as its parent")
            continue
        pn = maps.get(p)
        if pn is None:
            f("orphan_child", name, "parent %s is no map found — renamed, deleted or not given" % p, why="no_parent", parent=p)
            continue
        a, b = _product_key(n["product"]), _product_key(pn["product"])
        if a and b and a != b:
            f("other_product_parent", name, "its parent %s is a map of another product — a nesting stays in one product" % p, parent=p)
            continue
        stage = str(n.get("parent_stage") or "").strip()
        if not stage:
            f("orphan_child", name, "no parent_stage — the stage of %s it opens from" % p, why="no_stage", parent=p)
            continue
        if stage not in [s["id"] for s in pn["stages"]]:
            f("orphan_child", name, "%s declares no stage %s" % (p, stage), why="no_stage_in_parent", parent=p)
            continue
        step = _norm(n.get("parent_step")).casefold()
        if step and not any(r["stage"] == stage and _norm(r["step"]).casefold() == step for r in pn["rows"] if not r["gap"]):
            f("orphan_child", name, "no row of %s on %s has the step «%s»" % (p, stage, nt.safe(_norm(n.get("parent_step")))),
              why="no_step", parent=p)
            continue
        par[name] = p
    ring_of = set()
    for name in sorted(par):                         # walk up from every map: a map met again on its walk closes a cycle
        walk, seen, cur = [name], {name}, par.get(name)
        while cur is not None:
            if cur in seen:
                ring = walk[walk.index(cur):]
                if not set(ring) & ring_of:
                    ring_of |= set(ring)
                    f("nest_cycle", sorted(ring)[0], "the maps hang under each other in a ring — each stands alone "
                      "until a link is fixed", maps=sorted(ring))
                break
            if cur in ring_of:
                break
            seen.add(cur)
            walk.append(cur)
            cur = par.get(cur)
    for name in ring_of:
        par.pop(name, None)
    level = {}
    for name in maps:
        k, cur, seen = 1, par.get(name), {name}
        while cur is not None and cur not in seen:
            seen.add(cur)
            k += 1
            cur = par.get(cur)
        level[name] = k
    children = {}
    for c in sorted(par):
        children.setdefault(par[c], []).append(c)

    def place(c):
        pn, n = maps[par[c]], maps[c]
        ids = [s["id"] for s in pn["stages"]]
        stage, step = str(n.get("parent_stage") or "").strip(), _norm(n.get("parent_step")).casefold()
        first = next((i for i, r in enumerate(pn["rows"]) if r["stage"] == stage and step and _norm(r["step"]).casefold() == step), -1)
        return (ids.index(stage) if stage in ids else len(ids), first, c)
    for p in children:
        children[p].sort(key=place)
    for name in sorted(maps):
        if level[name] > MAX_DEPTH:
            up = name
            for _ in range(level[name] - MAX_DEPTH):
                up = par[up]
            f("too_deep", name, "level %d, under %s (level %d) — shown by a reference only, never its grid (R38)"
              % (level[name], up, MAX_DEPTH), level=level[name], under=up)
    return {"parent": par, "children": children, "level": level, "findings": found}


def rollup(note, lang="uk"):
    """A child's roll-up on its parent's step (R30) — numbers and one metric, never a copy of a row: the pains its page
    shows, by class (a simulated or unsourced pain is none; a health-check row is no pain); the anomalies its page
    shows, the critical ones by the label `refresh` ends a row with (§10) — a row the PM wrote is counted unrated; its
    journey-level metric (§4), else ⚠️ TBD; its last health point, else «немає знімка»; its review date."""
    declared = [s["id"] for s in note["stages"]]
    shown = [r for r in note["rows"] if not r["gap"] and page_worthy(r, declared)]
    pains, an = {}, {"total": 0, "critical": 0, "warning": 0, "positive": 0, "unrated": 0}
    for r in shown:
        if r["lane"] == "pain":
            cls = r["class"].strip().lower()
            pains[cls] = pains.get(cls, 0) + 1
    for r in shown:
        if r["lane"] == "anomaly":
            an["total"] += 1
            st = hc_status(r["text"]) if _is_hc(r) else None
            an[st or "unrated"] += 1
    outcome = next((_norm(nt.safe(r["text"])) for r in shown if r["lane"] == "metric" and r["level"].strip().lower() == "journey"), "")
    pts = sorted((p for p in note["health"] if isinstance(p.get("score"), (int, float)) and day(p.get("date"))),
                 key=lambda p: (p["date"], p.get("snapshot") or ""))
    last = pts[-1] if pts else None
    return {"pains": dict(sorted(pains.items())), "pains_total": sum(pains.values()), "anomalies": an,
            "outcome": outcome or OUTCOME_TBD,
            "health": {"score": last["score"], "date": last["date"]} if last else None,
            "health_label": "" if last else NEST_LABELS.get(lang, NEST_LABELS["en"])["no_snapshot"],
            "reviewed": note["reviewed"] if day(note["reviewed"]) else ""}


def _journey_name(note, name):
    return _norm(nt.safe(note["journey"] or note["title"] or name))


def nest_node(name, maps, forest, lang, seen=None):
    """The node of a map in its tree: its link, its roll-up, its children while their level is MAX_DEPTH or less, and the
    first level past it as references (`deeper`) — never a row of any map."""
    seen = set() if seen is None else seen
    seen.add(name)
    n = maps[name]
    linked = name in forest["parent"]
    out = {"note": name, "journey": _journey_name(n, name), "level": forest["level"][name],
           "stage": str(n.get("parent_stage") or "").strip() if linked else "",
           "step": _norm(nt.safe(n.get("parent_step"))) if linked else "", "rollup": rollup(n, lang), "children": [], "deeper": []}
    for c in forest["children"].get(name, []):
        if c in seen:
            continue
        if forest["level"][c] > MAX_DEPTH:
            out["deeper"].append({"note": c, "journey": _journey_name(maps[c], c), "level": forest["level"][c],
                                  "stage": str(maps[c].get("parent_stage") or "").strip(),
                                  "step": _norm(nt.safe(maps[c].get("parent_step")))})
        else:
            out["children"].append(nest_node(c, maps, forest, lang, seen))
    return out


def ancestors(name, maps, forest):
    """The maps above `name`, the top root first — each with the stage and step the next one opens from."""
    chain, cur, seen = [], forest["parent"].get(name), {name}
    while cur is not None and cur not in seen:
        seen.add(cur)
        chain.append({"note": cur, "journey": _journey_name(maps[cur], cur), "level": forest["level"][cur]})
        cur = forest["parent"].get(cur)
    return chain[::-1]


def nest_of(note_path, maps=(), dirs=(), lang=None):
    """Everything the nesting of one map needs: {name, note, maps, forest, tree, ancestors, skipped, counts} — raises Bad
    when the note is no journey map."""
    note = load(note_path)
    if note["type"].strip().lower() != "cjm-journey":
        raise Bad("%s is not a journey map (type: %s)" % (os.path.basename(note_path), note["type"] or "—"))
    found, skipped, counts = nest_maps(note_path, maps, dirs)
    name = os.path.splitext(os.path.basename(note_path))[0]
    found[name] = note if name not in found else found[name]
    forest = nest_forest(found)
    lang = lang or note["lang"]
    return {"name": name, "note": found[name], "maps": found, "forest": forest, "lang": lang,
            "tree": nest_node(name, found, forest, lang), "ancestors": ancestors(name, found, forest),
            "skipped": skipped, "counts": counts}


def _rollup_words(ru, L):
    pains = "%s %d" % (L["pains"], ru["pains_total"]) + (" (%s)" % " · ".join("%s %d" % kv for kv in ru["pains"].items()) if ru["pains"] else "")
    an = ru["anomalies"]
    anom = "%s %d" % (L["anomalies"], an["total"]) + (" (%s)" % (L["critical"] % an["critical"]) if an["critical"] else "")
    health = ("%s %s (%s)" % (L["health"], ru["health"]["score"], ru["health"]["date"]) if ru["health"]
              else "%s: %s" % (L["health"], ru["health_label"]))
    parts = [pains, anom, "%s: %s" % (L["outcome"], ru["outcome"]), health]
    if ru["reviewed"]:
        parts.append("%s %s" % (L["reviewed"], ru["reviewed"]))
    return " · ".join(parts)


def nest_text(nest):
    """The tree for the chat: the map, its children indented by level with their roll-up, the references past the
    depth, then the findings of the nesting."""
    L = NEST_LABELS.get(nest["lang"], NEST_LABELS["en"])
    t = nest["tree"]

    def count(n):
        return len(n["children"]) + sum(count(k) for k in n["children"])
    out = [L["head"] % (t["journey"], t["note"], t["level"], count(t))]
    if nest["ancestors"]:
        out.append(L["ancestors"] % " → ".join("«%s» (%s)" % (a["journey"], a["note"]) for a in nest["ancestors"]))

    def walk(n, depth):
        for k in n["children"]:
            where = k["stage"] + (" · %s «%s»" % (L["step"], k["step"]) if k["step"] else "")
            out.append("%s- %s · «%s» (%s): %s" % ("  " * depth, where, k["journey"], k["note"], _rollup_words(k["rollup"], L)))
            walk(k, depth + 1)
        for x in n["deeper"]:
            out.append("%s- «%s» (%s): %s" % ("  " * depth, x["journey"], x["note"], L["deeper"] % x["level"]))
    walk(t, 0)
    if not t["children"] and not t["deeper"]:
        out.append(L["none"])
    if nest["forest"]["findings"]:
        out += ["", L["findings"]]
        for f_ in nest["forest"]["findings"]:
            out.append("- %s: %s — %s" % (f_["finding"], ", ".join(f_.get("maps") or [f_["note"]]), f_["detail"]))
    for s_ in nest["skipped"]:
        out.append("%s: %s — %s" % (L["skipped"], s_["note"], s_["detail"]))
    return "\n".join(out) + "\n"


# ------------------------------------------------------------------ the board (§11–§12, since v4.8.0)
BOARD_ROLES = ("cell", "row", "header", "lane_name", "team", "orphan", "frame", "other")
DIFF_CATEGORIES = ("changed", "moved", "added", "removed", "orphaned", "hc_edits", "other", "unrecorded")
TAKE_REFUSED = ("health_check", "metric_lane", "no_cell", "needs_drop", "not_removed", "taken", "secret", "empty",
                "not_takeable", "unknown")
TAKE_NAMED = ("contact_removed", "link_removed", "no_class", "bad_class", "orphan", "bad_parent", "bad_code", "unused")
COUNTED = ("changed", "moved", "added", "removed", "orphaned", "hc_edits")
TEAM_SOURCE = {"uk": "дошка команди", "en": "team board"}
STATE_KIND = "journey-board"
HC_LANES = ("metric", "anomaly")
MARKERS = re.compile(r"\[(?:link removed|contact hidden)\]")


def _norm(s):
    return re.sub(r"\s+", " ", str(s or "")).strip()


def _lines(s):
    return [l for l in (_norm(x) for x in str(s or "").split("\n")) if l]


def lane_names(lang):
    if lang == "uk":
        return dict(LANES)
    return {k: v.lower() for k, v in LABELS["en"]["lane"].items()}


def lane_of(word):
    """A lane by its id, its Ukrainian name (§2) or its English label — None for anything else."""
    w = _norm(word).lower()
    if w in LANE_IDS:
        return w
    if w in LANE_ALIAS:
        return LANE_ALIAS[w]
    return next((k for k, v in LABELS["en"]["lane"].items() if v.lower() == w), None)


def cell_title(sid, lane, lang):
    return "%s · %s" % (sid, lane_names(lang)[lane])


def parse_cell(title, declared):
    """(stage, lane) of a cell's title «s3 · болі» — None when it names no declared stage and known lane."""
    m = re.match(r"^\s*(\S+?)\s*(?:·|•|\||—|–|:|\s-\s)\s*(.+?)\s*$", str(title or ""))
    if not m:
        return None
    lane = lane_of(m.group(2))
    return (m.group(1), lane) if m.group(1) in declared and lane else None


def second_line(r):
    """A sticky's second line: «health-check» on a health-check row; an initiative's or an experiment's code, page-safe."""
    if _is_hc(r):
        return HC_SOURCE
    if r["lane"] in ("initiative", "experiment") and r["code"].strip():
        return nt.safe(r["code"].strip())
    return ""


def note_rows(note):
    """Every row of the note with an id, as the board knows it: its board text, second line, whether it is the
    health-check's and whether the board shows it (`shown` — exactly the page's rows)."""
    declared = [s["id"] for s in note["stages"]]
    return [dict(r, board_text=nt.safe(r["text"]), second=second_line(r), hc=_is_hc(r), shown=page_worthy(r, declared))
            for r in note["rows"] if not r["gap"] and r["id"]]


def board_rows(note):
    """The rows the board shows — exactly the page's (page_worthy), each with its board text and second line."""
    declared = [s["id"] for s in note["stages"]]
    return [dict(r, board_text=nt.safe(r["text"]), second=second_line(r), hc=_is_hc(r), shown=True)
            for r in note["rows"] if page_worthy(r, declared)]


def _rendered(r):
    """The texts a row's sticky reads back as: its board text, with its second line after it."""
    texts = []
    for base in (r["board_text"], (r["board_text"] + " " + r["second"]) if r["second"] else ""):
        if base:
            texts += [_norm(base), _norm(bs.plain(base))]
    return list(dict.fromkeys(texts))


def _heads(note):
    """The texts the board's headers read back as — a stage's «<id> · <name>» (with its gap mark), its name, its
    outcome, the map's title and journey name — lower case."""
    out = set()
    for s in note["stages"]:
        for t in ("%s · %s" % (s["id"], s["name"]), "%s · %s ⚠️" % (s["id"], s["name"]), s["name"], s["outcome"],
                  "%s · %s %s" % (s["id"], s["name"], s["outcome"])):
            if _norm(t):
                out.add(_norm(nt.safe(t)).lower())
    for t in (note.get("title"), note.get("journey")):
        if _norm(t):
            out.add(_norm(nt.safe(t)).lower())
    return out


def team_row(r):
    """A row the team wrote on the board — its source the team board's (an earlier take)."""
    return r["source"].strip().lower().startswith(tuple(w.lower() for w in TEAM_SOURCE.values()))


def _lane_texts():
    return {w.lower() for l in LANE_IDS for w in (l, dict(LANES)[l], LABELS["en"]["lane"][l])}


def _cell(it, declared, items):
    """((stage, lane), its title) of the cell an element sits in — up through the frames it is nested in (a team's own
    section inside a cell keeps its stickies in that cell) — or (None, "")."""
    seen, f, title = set(), it.get("frame"), it.get("frame_text")
    while f and f not in seen:
        seen.add(f)
        c = parse_cell(title, declared)
        if c:
            return c, title
        fr = items.get(f)
        if fr is None:
            break
        f, title = fr.get("frame"), fr.get("frame_text")
    return None, ""


def safe_items(items):
    """Every text of a read page-safe before it is compared, kept or printed: a link removed, a contact hidden, a text
    holding a secret hidden whole — a state or a diff never keeps what the page would not show."""
    for it in items.values():
        it["text"] = nt.safe(it.get("text", ""))
        it["frame_text"] = nt.safe(it.get("frame_text", ""))
    return items


def assign_roles(items, note, exclude=(), lookup=None):
    """Give each item its role — cell (with its stage and lane), row (with its id), header, lane_name, team, frame or
    other — by what the note says now, and an `origin`: the plugin's sticky of a row the board shows, or the team's (a
    team sticky, or one whose row the board does not show — a row an earlier take made of it). A sticky takes a row of
    its text in its own cell first, then any row of its text (it was moved); two stickies of one text take that text's
    rows in turn (`ambiguous`)."""
    declared = [s["id"] for s in note["stages"]]
    lookup = items if lookup is None else lookup
    by_text = {}
    for r in note_rows(note):
        if r["id"] in exclude:
            continue
        for t in _rendered(r):
            by_text.setdefault(t, []).append(r)
    heads, lanes = _heads(note), _lane_texts()
    for it in items.values():
        for k in ("role", "row", "stage", "lane", "hc", "origin"):
            it.pop(k, None)
        if it["kind"] == "frame":
            own = parse_cell(it["text"], declared)
            if own:
                it["role"], it["stage"], it["lane"] = "cell", own[0], own[1]
            else:
                it["role"] = "header" if _norm(it["text"]).lower() in heads else "frame"
            continue
        c, _ = _cell(it, declared, lookup)
        if c:
            it["stage"], it["lane"] = c
    taken, ambiguous = set(), []
    stickies = [it for it in items.values() if it["kind"] == "sticky"]
    for exact in (True, False):
        for it in stickies:
            if it.get("role"):
                continue
            cands = [r for r in by_text.get(_norm(it["text"]), []) if r["id"] not in taken]
            if exact:
                cands = [r for r in cands if (r["stage"], r["lane"]) == (it.get("stage"), it.get("lane"))]
            if not cands:
                continue
            r = cands[0]
            team = not r["shown"] or team_row(r) or it.get("type") == "note"    # a team sticky stays the team's
            it["role"], it["row"], it["origin"] = "row", r["id"], "team" if team else "plugin"
            if r["hc"]:
                it["hc"] = True
            taken.add(r["id"])
            if len(by_text[_norm(it["text"])]) > 1:
                ambiguous.append(it["id"])
    for it in items.values():
        if it.get("role"):
            continue
        t = _norm(it["text"])
        it["role"] = ("header" if t.lower() in heads else "lane_name" if t.lower() in lanes
                      else "team" if it["kind"] == "sticky" else "other")
        if it["role"] == "team":
            it["origin"] = "team"
    return ambiguous


def _valid_state(items):
    for mid, it in items.items():
        if not (isinstance(it, dict) and isinstance(it.get("kind"), str) and isinstance(it.get("text"), str)
                and isinstance(it.get("x"), (int, float)) and isinstance(it.get("y"), (int, float))):
            raise Bad("the board's state has an element without its kind, text or place (%s) — keep the state again" % mid)
        it.setdefault("id", mid)
        it.setdefault("frame", None)
        it.setdefault("frame_text", "")
    return items


def load_board_state(path, note, surface=None):
    """(items, surface) of the last state: a board-state JSON, or a board read whose roles are taken from the note now."""
    if not os.path.isdir(path) and path.lower().endswith(".json"):
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            raise Bad("the board's state does not read")
        if isinstance(data, dict) and data.get("kind") == STATE_KIND:
            items = data.get("elements")
            if not isinstance(items, dict):
                raise Bad("the board's state has no elements")
            return _valid_state(items), data.get("surface"), {"rebuilt": bool(data.get("rebuilt"))}
    items = safe_items(bs.read_board(path, surface, lines=True))
    assign_roles(items, note)
    return items, surface or ("miro" if path.lower().endswith(".svg") else "whiteboard"), {"rebuilt": True}


def _cell_fields(prefix, c, title):
    return {prefix: title if c else "", "stage" + ("_" + prefix if prefix != "cell" else ""): c[0] if c else None,
            "lane" + ("_" + prefix if prefix != "cell" else ""): c[1] if c else None}


def table_sig(note):
    """The note's identity for a diff: the journey, the product and a digest of its rows — a diff taken into another
    note, or into this one after it changed, is refused."""
    import hashlib
    rows = json.dumps([r["cells"] for r in note["rows"]], ensure_ascii=False)
    return {"journey": note["journey"], "product": note["product"], "table": hashlib.sha256(rows.encode("utf-8")).hexdigest()[:16]}


def missing_cells(last, now):
    """The cell titles the last state holds that a read lacks — a read of one page, or a stale folder: never a diff."""
    return sorted(it["text"] for mid, it in last.items() if it.get("role") == "cell" and mid not in now)


def board_diff(last, now, note):
    """The board now against its last state, by element id: what the team did to the map's rows, apart from the
    health-check rows (hc_edits — named, never taken), the plugin's stickies of rows the board no longer shows
    (orphaned), other items and the map's own items the state lacks (unrecorded)."""
    declared = [s["id"] for s in note["stages"]]
    rows = {r["id"]: r for r in note_rows(note)}
    shown = {rid for rid, r in rows.items() if r["shown"]}
    out = {k: [] for k in DIFF_CATEGORIES}

    def plugin(it):
        return it.get("origin", "plugin") != "team"
    for mid, it in sorted(last.items()):
        if it.get("role") in ("row", "orphan") and plugin(it) and it.get("row") not in shown:
            e = {"id": mid, "row": it.get("row"), "text": it["text"], "kind": it["kind"]}
            if mid in now:
                c, title = _cell(now[mid], declared, now)
                co, _ = _cell(it, declared, last)
                e.update(now=now[mid]["text"], cell=title, changed=_norm(now[mid]["text"]) != _norm(it["text"]) or c != co)
            out["orphaned"].append(e)
    gone = {o["id"] for o in out["orphaned"]}
    mapped = {it.get("row") for it in last.values() if it.get("role") == "row"}
    # a team sticky the note does not hold is offered as added every time until it is taken — one the PM left, or one a
    # state rebuilt with no history (§12 «No state») recorded, is never absorbed by a state
    fresh = {mid: dict(it) for mid, it in now.items() if mid not in last or last[mid].get("role") == "team"}
    assign_roles(fresh, note, exclude=mapped, lookup=now)
    for mid, it in now.items():
        old = None if mid in fresh else last.get(mid)
        cn_, tn = _cell(it, declared, now)
        if old is None:
            f = fresh[mid]
            entry = dict({"id": mid, "kind": it["kind"], "text": it["text"]}, **_cell_fields("cell", cn_, tn))
            if f.get("role") in ("row", "cell", "header", "lane_name"):
                out["unrecorded"].append(dict(entry, role=f["role"], row=f.get("row")))
            elif f.get("role") == "team":
                out["added"].append(entry)
            else:
                out["other"].append(dict(entry, change="added"))
            continue
        if mid in gone:
            continue
        role = old.get("role") or ("team" if old["kind"] == "sticky" else "other")
        if role == "row" and old.get("row") not in rows:      # a team sticky whose row the PM deleted is the team's again
            role = "team"
        row = old.get("row") if role == "row" else None
        hc = role == "row" and rows[row]["hc"]
        co, to = _cell(old, declared, last)
        if _norm(old["text"]) != _norm(it["text"]):
            e = dict({"id": mid, "row": row, "last": old["text"], "now": it["text"]}, **_cell_fields("cell", cn_, tn))
            if hc:
                out["hc_edits"].append(dict(e, change="text"))
            elif role in ("row", "team"):
                out["changed"].append(dict(e, team=role == "team"))
            else:
                out["other"].append(dict(e, role=role, change="text"))
        if role in ("row", "team") and co != cn_:
            e = dict({"id": mid, "row": row, "text": it["text"]}, **_cell_fields("from", co, to))
            e.update(_cell_fields("to", cn_, tn))
            out["hc_edits" if hc else "moved"].append(dict(e, change="moved") if hc else dict(e, team=role == "team"))
    for mid, old in last.items():
        if mid in now or mid in gone:
            continue
        role = old.get("role") or "other"
        row = old.get("row") if role == "row" and old.get("row") in rows else None
        e = {"id": mid, "row": row, "text": old["text"], "cell": old.get("frame_text", "")}
        if row and rows[row]["hc"]:
            out["hc_edits"].append(dict(e, change="removed"))
        elif row:
            out["removed"].append(e)
        else:
            out["other"].append(dict(e, role=role, change="removed"))
    out["counts"] = {k: len(out[k]) for k in COUNTED}
    return out


def _rows_map(items):
    """{row id: element id} of the stickies a state maps to rows — what the next version updates by id."""
    return {it["row"]: mid for mid, it in items.items() if it.get("role") == "row" and it.get("row") and not it.get("gone")}


def read_diff(path):
    """A board-diff result kept by `board-diff --out`, or a text holding its JOURNEY_RESULT line — raises Bad."""
    try:
        with open(path, encoding="utf-8") as fh:
            raw = fh.read()
    except OSError as e:
        raise Bad("the diff does not read: %s" % (e.strerror or type(e).__name__))
    line = next((l for l in raw.splitlines() if l.startswith("JOURNEY_RESULT ")), None)
    try:
        data = json.loads(line[len("JOURNEY_RESULT "):] if line else raw)
    except ValueError:
        raise Bad("the diff is not a board-diff result")
    if not isinstance(data, dict) or data.get("state") != "diff":
        raise Bad("the diff is not a board-diff result with state «diff»")
    return data


EXP_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{1,79}$")      # an experiment's registry id: one word, no marker


def code_line(lane, ls, i, row, named, own=""):
    """(the lines without a code line, the code) — an initiative's or an experiment's sticky has its code on its own
    last line: the row's own code is no change; an initiative takes an epic or feature code, an experiment a registry
    id; a last line that is no code (words, a marker) stays in the text — a code is never read from the text."""
    if lane not in ("initiative", "experiment") or len(ls) < 2:
        return ls, None
    last = ls[-1]
    if own and last == own:
        return ls[:-1], None
    if (CODE if lane == "initiative" else EXP_ID).match(last):
        return ls[:-1], last
    return ls, None


def _locked(r):
    """Why a row never changes from the board (R25) — the health-check's, or any metric or anomaly row — else None."""
    if _is_hc(r):
        return "health_check"
    if r["lane"] in HC_LANES:
        return "metric_lane"
    return None


def _pairs(values, flag):
    out = {}
    for v in values or []:
        k, sep, val = v.partition("=")
        if not sep or not k.strip():
            raise Bad("%s takes <id>=<value>: %r" % (flag, v))
        out[k.strip()] = val.strip()
    return out


def take_note(note, diff, take, picked, parents, drop, when):
    """The note's text with what the PM took from the board — the plan of board-take (§12), never written here."""
    lang = note["lang"]
    declared = [s["id"] for s in note["stages"]]
    lines, eol, cols = list(note["lines"]), note["eol"], note["cols"]
    pos = {c: i for i, c in enumerate(cols) if c}
    live = [r for r in note["rows"] if not r["gap"] and r["id"]]
    by_id = {}
    for r in live:
        by_id.setdefault(r["id"], r)
    uk_lanes = any(r["cells"][pos["lane"]].strip().lower() in LANE_ALIAS for r in live if pos["lane"] < len(r["cells"]))
    team_source = "%s %s" % (TEAM_SOURCE.get(lang, TEAM_SOURCE["en"]), when)
    applied, refused, named, ask, prop = [], [], [], [], []
    used_keys = set()
    ents = {}
    for cat in ("changed", "moved", "added", "removed", "hc_edits", "orphaned", "other", "unrecorded"):
        for e in diff.get(cat, []) or []:
            if isinstance(e, dict) and e.get("id") is not None:   # a health-check edit reads as what it did — the row decides
                c = {"text": "changed", "moved": "moved", "removed": "removed"}.get(e.get("change"), cat) if cat == "hc_edits" else cat
                ents.setdefault(str(e["id"]), []).append((c, e))
    by_row = {}
    for k, es in ents.items():
        for cat, e in es:
            if e.get("row") and cat in ("changed", "moved", "removed"):
                by_row.setdefault(str(e["row"]), (k, es))

    def refuse(i, why, detail=""):
        refused.append({"id": i, "why": why, "detail": detail})

    def lane_cell(lane):
        return dict(LANES)[lane] if uk_lanes else lane

    def pick(table, *keys):
        for k in keys:
            if k and k in table:
                used_keys.add((id(table), k))
                return table[k]
        return ""

    def clean(text, i, row=None):
        raw = str(text or "")
        for marker, why, what in (("[link removed]", "link_removed", "a link"), ("[contact hidden]", "contact_removed", "an e-mail or a phone")):
            if marker in raw:
                named.append({"element": i, "row": row, "why": why, "detail": "%s the board had hidden is not written back" % what})
        t = _norm(MARKERS.sub("", raw))
        if t.startswith("[hidden:") or cn.scan(t):
            refuse(i, "secret", "the sticky holds %s — never written" % (", ".join(cn.scan(t)) or "a hidden secret"))
            return None
        t2 = _norm(nt.CONTACT.sub("", t))
        if t2 != t:
            named.append({"element": i, "row": row, "why": "contact_removed", "detail": "an e-mail or a phone removed before the write"})
        t3 = _norm(nt.LINK.sub("", t2)).strip(" ,;")
        if t3 != t2.strip(" ,;"):
            named.append({"element": i, "row": row, "why": "link_removed", "detail": "a link removed before the write"})
        t3 = t3.strip(" ,;")
        if not t3:
            refuse(i, "empty", "nothing left to write")
            return None
        return t3

    def klass(i, rid, lane, text):
        """The class the PM picked for a row the team wrote, checked against its lane (§2) — never one of ours."""
        if lane not in LANE_CLASSES:
            if pick(picked, i, "row:%s" % rid, rid):
                named.append({"element": i, "row": rid, "why": "bad_class", "detail": "%s takes no class (§2)" % lane})
            return ""
        cls = picked.get(i, picked.get("row:%s" % rid, picked.get(rid, "")))
        pick(picked, i, "row:%s" % rid, rid)
        if cls and cls not in LANE_CLASSES[lane]:
            named.append({"element": i, "row": rid, "why": "bad_class", "detail": "%s takes %s" % (lane, ", ".join(LANE_CLASSES[lane]))})
            cls = ""
        if not cls:
            named.append({"element": i, "row": rid, "why": "no_class", "detail": "no class from the PM — a finding, never on the page"})
            ask.append({"element": i, "row": rid, "lane": lane, "text": text, "classes": list(LANE_CLASSES[lane]) + [""]})
        return cls

    edits, moves, news, drops = {}, {}, [], set()
    used = {r["id"] for r in note["rows"]}
    new_ids = {}                                     # a new row's id by the diff's order — the preview's and the take's agree
    for cat in ("added", "changed", "moved"):
        for e in diff.get(cat, []) or []:
            if isinstance(e, dict) and e.get("id") is not None and not e.get("row") and str(e["id"]) not in new_ids:
                n = 1
                while "b%d" % n in used:
                    n += 1
                new_ids[str(e["id"])] = "b%d" % n
                used.add("b%d" % n)
    done = set()
    for i in list(dict.fromkeys(take)):
        es = ents.get(i)
        if i.startswith("row:") and i[4:] in by_row:   # a row by its id — never confused with an element of that id
            i, es = by_row[i[4:]]
        if not es:
            refuse(i, "unknown", "no such element in the diff (a row: «row:<id>»)")
            continue
        if i in done:                                # an element and its own row taken together are one change
            continue
        done.add(i)
        cats = {c for c, _ in es}
        e0 = es[0][1]
        rid = e0.get("row") if cats & {"changed", "moved", "removed"} else None
        r = by_id.get(rid) if rid else None
        if rid and r is None:
            refuse(i, "unknown", "row %s is not in the note" % rid)
            continue
        if r is not None:
            why = _locked(r)
            if why:
                refuse(i, why, "row %s (%s) — its edits on the board are named, never taken (R25)" % (rid, r["lane"]))
                continue
            if "removed" in cats:
                refuse(i, "needs_drop", "row %s is gone from the board — dropped only with --drop %s" % (rid, rid))
                continue
            for cat, e in es:
                if cat == "changed":
                    ls, code = code_line(r["lane"], _lines(e.get("now", "")), i, rid, named, _norm(second_line(r)))
                    t = clean(" ".join(ls), i, rid)
                    if t is None:
                        break
                    cls = klass(i, rid, r["lane"], t)
                    ed = {"text": t, "source": team_source, "date": when, "class": cls}
                    if code:
                        ed["code"] = code
                    edits[rid] = dict(edits.get(rid, {}), **ed)
                    applied.append({"element": i, "row": rid, "action": "text", "before": r["text"], "after": t,
                                    "source": team_source, "class": cls})
                elif cat == "moved":
                    st, ln = e.get("stage_to"), e.get("lane_to")
                    if not st or st not in declared or ln not in LANE_IDS:
                        refuse(i, "no_cell", "row %s was moved out of every cell" % rid)
                        break
                    if ln in HC_LANES:
                        refuse(i, "metric_lane", "row %s: a move into the metric and anomaly lanes is never taken" % rid)
                        break
                    moves[rid] = (st, ln)
                    applied.append({"element": i, "row": rid, "action": "move", "from": "%s · %s" % (r["stage"], r["lane"]),
                                    "to": "%s · %s" % (st, ln)})
                    cls_now = r["class"].strip().lower()
                    if ln in LANE_CLASSES and cls_now not in LANE_CLASSES[ln]:      # its class does not fit the new lane
                        edits[rid] = dict(edits.get(rid, {}), **{"class": klass(i, rid, ln, edits.get(rid, {}).get("text", r["text"]))})
                    elif ln not in LANE_CLASSES and cls_now:
                        named.append({"element": i, "row": rid, "why": "bad_class", "detail": "%s takes no class (§2) — %s cleared" % (ln, cls_now)})
                        edits[rid] = dict(edits.get(rid, {}), **{"class": ""})
            continue
        if not cats & {"added", "changed", "moved"}:
            refuse(i, "not_takeable", "%s is not a team's sticky (%s)" % (i, ", ".join(sorted(cats))))
            continue
        text, st, ln = e0.get("text") or e0.get("now"), None, None
        for cat, e in es:
            if cat == "changed":
                text = e.get("now") or text
            if cat in ("added", "changed"):
                st, ln = e.get("stage"), e.get("lane")
        for cat, e in es:
            if cat == "moved":
                st, ln = e.get("stage_to"), e.get("lane_to")
        if not st or st not in declared or ln not in LANE_IDS:
            refuse(i, "no_cell", "the sticky sits in no cell of the map")
            continue
        ls, code = code_line(ln, _lines(text), i, None, named)
        code = code or ""
        t = clean(" ".join(ls), i)
        if t is None:
            continue
        if any(r["stage"] == st and r["lane"] == ln and _norm(r["text"]) == t for r in live):
            refuse(i, "taken", "the note already holds this row on %s — an earlier take" % cell_title(st, ln, lang))
            continue
        nid = new_ids.get(i)
        if nid is None:
            refuse(i, "unknown", "no new row for %s in the diff" % i)
            continue
        cls = klass(i, nid, ln, t)
        par = pick(parents, i, nid)
        if par:
            pr = by_id.get(par)
            if pr is None or ln not in PARENTS or pr["lane"] not in PARENTS[ln] or pr["stage"] != st:
                named.append({"element": i, "row": nid, "why": "bad_parent", "detail": "%s cannot hang under %s" % (ln, par)})
                par = ""
        if not par and ln in NEEDS_PARENT:
            cands = [r["id"] for r in live if r["stage"] == st and r["lane"] in PARENTS[ln]]
            named.append({"element": i, "row": nid, "why": "orphan", "detail": "%s needs its parent" % _a(ln)})
            prop.append({"element": i, "row": nid, "lane": ln, "candidates": cands})
        if ln == "initiative" and not code:
            named.append({"element": i, "row": nid, "why": "bad_code", "detail": "no epic or feature code on the sticky's own second line"})
        news.append((st, {"id": nid, "stage": st, "lane": lane_cell(ln), "text": t, "parent": par, "code": code, "source": team_source,
                          "class": cls, "date": when}))
        applied.append({"element": i, "row": nid, "action": "add", "cell": cell_title(st, ln, lang), "text": t, "class": cls,
                        "source": team_source, "parent": par, "code": code})
    removed = {str(e.get("row")) for e in diff.get("removed", []) or [] if isinstance(e, dict) and e.get("row")}
    for rid in drop:
        r = by_id.get(rid)
        if r is None:
            refuse(rid, "unknown", "row %s is not in the note" % rid)
            continue
        why = _locked(r)
        if why:
            refuse(rid, why, "row %s (%s) — never dropped from the board" % (rid, r["lane"]))
            continue
        if r is None or rid not in removed:
            refuse(rid, "not_removed", "row %s is not gone from the board — a row leaves the note only when the board lost it" % rid)
            continue
        drops.add(r["line"])
        applied.append({"row": rid, "action": "drop", "text": r["text"]})
    for table in (picked, parents):
        for k in table:
            if (id(table), k) not in used_keys:
                named.append({"element": k, "row": None, "why": "unused", "detail": "%s=%s matches no taken element or new row" % (k, table[k])})
    new_line = {}
    for rid in set(edits) | set(moves):
        r = by_id[rid]
        cells = (list(r["cells"]) + [""] * len(cols))[:len(cols)]
        for k, v in edits.get(rid, {}).items():
            if k in pos:
                cells[pos[k]] = v
            elif v:
                named.append({"element": None, "row": rid, "why": "bad_code" if k == "code" else "unused",
                              "detail": "the table has no %s column — %s not written" % (k, v)})
        if rid in moves:
            cells[pos["stage"]], cells[pos["lane"]] = moves[rid][0], lane_cell(moves[rid][1])
        new_line[r["line"]] = nt.row_line(cells) + eol
    for _, values in news:
        if values.get("code") and "code" not in pos:
            named.append({"element": None, "row": values["id"], "why": "bad_code", "detail": "the table has no code column — %s not written" % values["code"]})
    last_of = {}
    for r in note["rows"]:
        if r["line"] in drops:
            continue
        st = moves[r["id"]][0] if r["id"] in moves and by_id.get(r["id"]) is r else r["stage"]
        last_of[st] = max(last_of.get(st, -1), r["line"])
    inserts = {}
    for st, values in news:
        inserts.setdefault(last_of.get(st, note["table_end"]), []).append(nt.row_line([values.get(c, "") if c else "" for c in cols]) + eol)
    out = []
    for n, line in enumerate(lines):
        if n not in drops:
            out.append(new_line.get(n, line))
        if n in inserts:
            if out and not out[-1].endswith("\n"):
                out[-1] += eol
            out.extend(inserts[n])
    taken = {a.get("element") for a in applied} | {a.get("row") for a in applied}
    left = []
    for cat in ("changed", "moved", "removed", "hc_edits", "added"):
        for e in diff.get(cat, []) or []:
            if isinstance(e, dict) and e.get("id") is not None and str(e["id"]) not in taken and (e.get("row") or None) not in taken:
                left.append({"id": e["id"], "row": e.get("row"), "category": cat, "change": e.get("change")})
    return {"text": "".join(out), "applied": applied, "refused": refused, "named": named, "ask_class": ask, "parents": prop,
            "left": left}


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


# ------------------------------------------------------------------ check 29
def check_board_protocol(root):
    """Errors for validate-consistency.sh check 29 (v4.8.0) — the board's roles, diff categories and board-take rules
    are journey-protocol.md §11–§12's; artifact-publishing.md names the journey map as a board consumer and the host's
    typed board as a candidate; the seed's board record serves cjm-research; both maps read boards through board_state;
    cjm-research has its step J6, pointing to §12."""
    errs, texts = [], {}
    for rel in ("references/journey-protocol.md", "references/artifact-publishing.md", "references/tools-seed.yaml",
                "scripts/story_map.py", "scripts/journey_map.py", "skills/cjm-research/SKILL.md"):
        try:
            with open(os.path.join(root, rel), encoding="utf-8") as fh:
                texts[rel] = fh.read()
        except OSError:
            errs.append("%s is missing" % rel)
    skill = texts.get("skills/cjm-research/SKILL.md")
    if skill is not None and not re.search(r"^- \*\*J6\b.*§12", skill, re.M):
        errs.append("skills/cjm-research/SKILL.md has no step J6 that points to journey-protocol.md §12 (what the team changed on the board)")
    proto = texts.get("references/journey-protocol.md")
    if proto is not None:
        s11, s12 = nt.section(proto, "11. The board"), nt.section(proto, "12. What the team changed")
        if not s11 or "board-layout" not in s11:
            errs.append("journey-protocol.md has no §11 «The board» that builds the board from board-layout")
        roles = [nt.tick(r[0]) or "?" for r in nt.table_after(s12, r"\| Role \| What it is \|")]
        if roles != list(BOARD_ROLES):
            errs.append("journey-protocol.md §12: the board roles %s ≠ journey_map.py BOARD_ROLES %s" % ("|".join(roles), "|".join(BOARD_ROLES)))
        rows = nt.table_after(s12, r"\| Category \| Counted \| What \|")
        cats = [nt.tick(r[0]) or "?" for r in rows]
        counted = sorted(nt.tick(r[0]) or "?" for r in rows if len(r) > 1 and r[1].strip() == "yes")
        if cats != list(DIFF_CATEGORIES):
            errs.append("journey-protocol.md §12: the diff categories %s ≠ journey_map.py DIFF_CATEGORIES %s" % ("|".join(cats), "|".join(DIFF_CATEGORIES)))
        if counted != sorted(COUNTED):
            errs.append("journey-protocol.md §12: the categories counted %s ≠ journey_map.py COUNTED %s" % ("|".join(counted), "|".join(sorted(COUNTED))))
        take = nt.table_after(s12, r"\| Code \| board-take \| What \|")
        for word, const in (("refused", TAKE_REFUSED), ("named", TAKE_NAMED)):
            got = sorted(nt.tick(r[0]) or "?" for r in take if len(r) > 1 and r[1].strip() == word)
            if got != sorted(const):
                errs.append("journey-protocol.md §12: board-take %s %s ≠ journey_map.py TAKE_%s %s" % (
                    word, "|".join(got), word.upper(), "|".join(sorted(const))))
        for word in TEAM_SOURCE.values():
            if word not in s12:
                errs.append("journey-protocol.md §12 does not name the team's source «%s <date>» (journey_map.py TEAM_SOURCE)" % word)
    ap = texts.get("references/artifact-publishing.md")
    if ap is not None:
        if not re.search(r"^\|\s*`board`\s*\|.*`cjm-research`", nt.section(ap, "1. The kind"), re.M):
            errs.append("artifact-publishing.md §1: the `board` row does not name its consumer `cjm-research` (the journey map)")
        if not re.search(r"ARTIFACT `typed` when it has this kind \([^)]*\bboard\b", nt.section(ap, "2. The candidates")):
            errs.append("artifact-publishing.md §2: ARTIFACT `typed` does not list the board kind (the host's own board)")
    seed = texts.get("references/tools-seed.yaml")
    if seed is not None:
        m = re.search(r"^  - id: miro\n(?:    .*\n)*?    skills: \[([^\]]*)\]", seed, re.M)
        if not (m and "cjm-research" in m.group(1)):
            errs.append("tools-seed.yaml: the miro record's skills do not include cjm-research (the journey map's board)")
    for rel in ("scripts/story_map.py", "scripts/journey_map.py"):
        src = texts.get(rel)
        if src is None:
            continue
        if re.search(r"^def (?:read_board|read_miro_svg|read_whiteboard)\(", src, re.M) or re.search(r"^\s*(?:import|from) xml\.etree", src, re.M):
            errs.append("%s defines a board reader of its own — read a board through scripts/board_state.py" % rel)
        if not re.search(r"^(?:import board_state\b|from board_state import )", src, re.M):
            errs.append("%s does not import scripts/board_state.py" % rel)
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


def page_nest(note, maps=(), dirs=(), lang=None):
    """The nesting a map's page shows (§14), or None: a note that is not typed `cjm-journey` renders the page of v4.9.0,
    and so does one whose own folder cannot be read (maps or folders named are read, or the command stops)."""
    if str(note.get("type") or "").strip().lower() != "cjm-journey":
        return None
    try:
        return nest_of(note["path"], maps, dirs, lang)
    except Bad:
        if maps or dirs:
            raise
        return None


def _render_to(note, out, lang, maps=(), dirs=()):
    """(bytes written, the nesting shown) — the map's page, with its child maps when it has any (§14)."""
    nest = page_nest(note, maps, dirs, lang)
    page = render_html(note, os.path.basename(note["path"]), lang, nest)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(page)
    return len(page.encode("utf-8")), nest


def _shown_count(n):
    return len(n["children"]) + sum(_shown_count(k) for k in n["children"])


def _deeper_of(n):
    return [x["note"] for x in n["deeper"]] + [y for k in n["children"] for y in _deeper_of(k)]


def cmd_render(args):
    note = load(args.note)
    try:
        size, nest = _render_to(note, args.out, args.lang, args.map, args.dir)
    except OSError as e:
        result(ok=False, error="the page cannot be written: %s" % (e.strerror or type(e).__name__))
        return 1
    declared = [s["id"] for s in note["stages"]]
    live = [r for r in note["rows"] if not r["gap"]]
    result(ok=True, out=args.out, bytes=size, rows=len(live), not_shown=sum(1 for r in live if not page_worthy(r, declared)),
           stages=len(note["stages"]), health=len(note["health"]),
           children=_shown_count(nest["tree"]) if nest else 0, deeper=_deeper_of(nest["tree"]) if nest else [],
           above=[a["note"] for a in nest["ancestors"]] if nest else [],
           nest_findings=len(nest["forest"]["findings"]) if nest else 0, errors=note["errors"])
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
        _, nest = _render_to(load(args.note), out, lang)
        above = []                                   # the pages of the maps above it show its roll-up: rendered again,
        for a in (nest["ancestors"] if nest else []):    # beside each map's note, locally — never published (§10, §14)
            an = nest["maps"][a["note"]]
            page = os.path.splitext(an["path"])[0] + ".html"
            _render_to(load(an["path"]), page, lang)
            above.append(page)
        if above:
            summary["pages_above"] = above
    except OSError as e:                             # the note is refreshed; only a page is not
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


def cmd_board_layout(args):
    note = load(args.note)
    lang = args.lang or note["lang"]
    declared = [s["id"] for s in note["stages"]]
    rows = board_rows(note)
    names = lane_names(lang)
    live = [r for r in note["rows"] if not r["gap"]]
    stages = [{"id": s["id"], "name": nt.safe(s["name"]), "outcome": nt.safe(s["outcome"] or "⚠️ TBD"),
               "title": nt.safe("%s · %s" % (s["id"], s["name"])),
               "gap": not any(r["stage"] == s["id"] and evidence(r) for r in rows)} for s in note["stages"]]
    cells = []
    for li, lane in enumerate(LANE_IDS):
        for si, s in enumerate(note["stages"]):
            cells.append({"title": cell_title(s["id"], lane, lang), "stage": s["id"], "lane": lane, "column": si, "line": li,
                          "rows": [{"id": r["id"], "text": r["board_text"], "second": r["second"], "health_check": r["hc"]}
                                   for r in rows if r["stage"] == s["id"] and r["lane"] == lane]})
    result(ok=True, title=nt.safe(note["journey"] or note["title"]), lang=lang, columns=declared,
           lanes=[{"id": l, "name": names[l]} for l in LANE_IDS], stages=stages, cells=cells,
           titles=[c["title"] for c in cells], hidden=[r["id"] for r in live if r["id"] and not page_worthy(r, declared)],
           rows=len(rows), sticky={"row": "yellow", "health_check": "blue"}, errors=note["errors"])
    return 0


def _write_json(path, data):
    out = os.path.abspath(path)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    tmp = out + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, out)
    return out


def _read_now(paths, surface):
    items = safe_items(bs.read_boards(paths, surface, lines=True))
    if not items:
        raise Bad("the read-back holds no element — read the board again before anything is compared or kept")
    return items


def cmd_board_state(args):
    note = load(args.note)
    items = _read_now(args.read, args.surface)
    declared = [s["id"] for s in note["stages"]]
    if not any(it["kind"] == "frame" and parse_cell(it["text"], declared) for it in items.values()):
        raise Bad("the read holds no cell of the map — read the board again (an error the tool returned, or another board?)")
    ambiguous = assign_roles(items, note)
    rows = {r["id"]: r for r in note_rows(note)}
    shown = {rid for rid, r in rows.items() if r["shown"]}
    rebuilt, last_ignored = True, False
    if args.last and os.path.exists(args.last):
        last, _, _ = load_board_state(args.last, note, args.surface)
        if not set(last) & set(items):              # a new board (answer 3): its first state, the old one set aside
            last_ignored = True
        else:
            rebuilt = False
            lost = missing_cells(last, items)
            if lost:
                raise Bad("the read lacks %d cell(s) the last state holds (%s) — read the board again, every page, into a "
                          "fresh folder; a state is never kept from a partial read" % (len(lost), ", ".join(lost[:3])))
            keep_last(items, last, note, rows, shown, declared)
    for it in items.values():
        it.pop("hc", None)
        if it.get("role") == "row" and it.get("row") in rows and rows[it["row"]]["hc"]:
            it["hc"] = True
    state = {"version": 1, "kind": STATE_KIND, "surface": args.surface, "note": os.path.basename(args.note), "rebuilt": rebuilt,
             "at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "elements": items}
    try:
        out = _write_json(args.out, state)
    except OSError as e:
        result(ok=False, error="the state cannot be written: %s" % (e.strerror or type(e).__name__))
        return 1
    rmap = _rows_map(items)
    roles = {}
    for it in items.values():
        roles[it["role"]] = roles.get(it["role"], 0) + 1
    lang = note["lang"]
    have = {it["text"] for it in items.values() if it.get("role") == "cell"}
    result(ok=True, out=out, surface=args.surface, rows=rmap, cells={it["text"]: mid for mid, it in items.items() if it.get("role") == "cell"},
           roles=roles, unmapped_rows=[rid for rid in rows if rid in shown and rid not in rmap],
           missing_cells=[cell_title(s["id"], l, lang) for l in LANE_IDS for s in note["stages"]
                          if cell_title(s["id"], l, lang) not in have and cell_title(s["id"], l, "en" if lang == "uk" else "uk") not in have],
           ambiguous=ambiguous, orphans={it["row"]: mid for mid, it in items.items() if it.get("role") == "orphan"},
           rebuilt=rebuilt, last_ignored=last_ignored, gone=sorted(it["row"] for it in items.values() if it.get("gone")))
    return 0


def keep_last(items, last, note, rows, shown, declared):
    """The state kept again over the last one: a sticky keeps its row by its element id (a refreshed metric), the plugin's
    sticky of a row the board no longer shows stays the plugin's (orphan), a team sticky stays the team's — and every
    edit the note has not taken stays a difference: its last text and cell are kept, a row's sticky gone from the board
    is kept as gone, so the next diff names them again (nothing of the team's work is absorbed by a re-keep)."""
    mapped = {it["row"] for it in items.values() if it.get("role") == "row"}
    for mid, old in last.items():
        it = items.get(mid)
        rid = old.get("row")
        if it is None:
            if old.get("role") == "row" and rid in rows and rows[rid]["shown"] and rid not in mapped:
                items[mid] = dict(old, gone=True)          # removed on the board, still in the note: removed again next time
                mapped.add(rid)
            continue
        if old.get("origin") == "team" and it.get("role") in ("row", "team"):
            it["origin"] = "team"                          # a team sticky stays the team's, whatever row a take made of it
        if it.get("role") != "row" and old.get("role") in ("row", "orphan"):
            if old.get("origin", "plugin") != "team" and rid not in shown:
                it["role"], it["row"], it["origin"] = "orphan", rid, "plugin"   # the plugin's sticky of a row the board no longer shows
            elif rid in rows and rid not in mapped:        # its row is still there: the sticky keeps it by its id
                it["role"], it["row"], it["origin"] = "row", rid, old.get("origin", "plugin")
                mapped.add(rid)
        if it.get("role") == "row" and it.get("row") == rid and rid in rows and old.get("role") == "row":
            r = rows[rid]
            if _norm(it["text"]) not in _rendered(r) and _norm(old["text"]) != _norm(it["text"]):
                it["text"] = old["text"]                   # a text edit the note has not taken stays one
            cn_, _ = _cell(it, declared, items)
            co, _ = _cell(old, declared, last)
            if cn_ != (r["stage"], r["lane"]) and co != cn_:
                for k in ("x", "y", "rx", "ry", "frame", "frame_text"):
                    it[k] = old.get(k)                     # a move the note has not taken stays one
    return items


def cmd_board_diff(args):
    if not args.last or not os.path.exists(args.last):
        result(ok=True, state="unknown", why="no last state of the board on this machine")
        return 0
    note = load(args.note)
    last, surface, meta = load_board_state(args.last, note, args.surface)
    if not args.now:
        result(ok=True, state="scope", surface=surface, scope=bs.scope(last), ids=sorted(last), rows=_rows_map(last))
        return 0
    now = _read_now(args.now, args.surface or surface)
    lost = missing_cells(last, now)
    if lost:                                       # the plugin never deletes a cell: a partial read, never «removed»
        result(ok=True, state="partial", surface=surface, missing_cells=lost, ids=sorted(last), scope=bs.scope(last),
               why="the read lacks %d cell(s) the state holds — read the board again, every page, into a fresh folder" % len(lost))
        return 0
    payload = dict(ok=True, state="diff", surface=surface, **board_diff(last, now, note))
    payload.update(scope=bs.scope(last), ids=sorted(last), rows=_rows_map(last), note=table_sig(note))
    if args.out:
        try:
            payload["out"] = _write_json(args.out, payload)
        except OSError as e:
            result(ok=False, error="the diff cannot be written: %s" % (e.strerror or type(e).__name__))
            return 1
    result(**payload)
    return 0


def cmd_board_take(args):
    note = load(args.note)
    diff = read_diff(args.diff)
    sig = diff.get("note")
    if isinstance(sig, dict):
        now = table_sig(note)
        if sig.get("journey") != now["journey"] or sig.get("product") != now["product"]:
            raise Bad("the diff is of another journey (%s / %s) — run board-diff on this note" % (sig.get("product"), sig.get("journey")))
        if sig.get("table") != now["table"]:
            raise Bad("the note changed since the diff — run board-diff again before taking anything")
    missing_cols = [c for c in ("source", "class", "date") if c not in note["cols"]]
    if missing_cols:
        raise Bad("the table has no %s column — a row from the board needs its source, class and date (§7)" % ", ".join(missing_cols))
    when = args.date or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    if day(when) is None:
        raise Bad("--date is not YYYY-MM-DD")
    picked, parents = _pairs(args.klass, "--class"), _pairs(args.parent, "--parent")
    plan = take_note(note, diff, args.take or [], picked, parents, args.drop or [], when)
    text = plan.pop("text")
    written = False
    if not args.dry_run and text != note["text"]:
        try:
            write_text(args.note, text)
            written = True
        except OSError as e:
            result(ok=False, error="the note cannot be written: %s" % (e.strerror or type(e).__name__))
            return 1
    touched = {a.get("row") for a in plan["applied"]}
    moved = {a.get("row") for a in plan["applied"] if a.get("action") in ("move", "drop")}
    touched |= {r["id"] for r in note["rows"] if r.get("parent") in moved}      # a moved row's children may hang wrong now
    fd, tmp = tempfile.mkstemp(prefix=".journey-take-", suffix=".md")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        found = [f for f in findings(load(tmp), datetime.date.today()) if f.get("row") in touched]
    finally:
        os.remove(tmp)
    result(ok=True, dry_run=bool(args.dry_run), note_written=written, findings=found, **plan)
    return 0


def cmd_nest(args):
    n = nest_of(args.note, args.map, args.dir, args.lang)
    if not args.json:
        sys.stdout.write(nest_text(n))
    t = n["tree"]
    result(ok=True, note=n["name"], journey=t["journey"], product=nt.safe(n["note"]["product"]), level=t["level"],
           ancestors=n["ancestors"], tree=t, maps=len(n["maps"]), depth=MAX_DEPTH, findings=n["forest"]["findings"],
           skipped=n["skipped"], ignored=n["counts"]["ignored"], undownloaded=n["counts"]["undownloaded"],
           note_written=False, errors=n["note"]["errors"])
    return 0


def cmd_schema(args):
    result(ok=True, fields=list(FIELDS), columns=[list(c) for c in COLUMNS], lanes=[list(l) for l in LANES],
           lanes_order=list(LANE_IDS), levels=list(LEVELS), classes=list(CLASSES), findings=list(FINDINGS),
           model_findings=list(MODEL_FINDINGS), commands=list(COMMANDS), board_roles=list(BOARD_ROLES),
           diff_categories=list(DIFF_CATEGORIES), take_refused=list(TAKE_REFUSED), take_named=list(TAKE_NAMED),
           team_source=TEAM_SOURCE, nest_fields=list(NEST_FIELDS), nest_findings=list(NEST_FINDINGS), orphan_why=list(ORPHAN_WHY),
           max_depth=MAX_DEPTH, errors=check_protocol(os.path.dirname(HERE)))
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
    p.add_argument("--map", action="extend", nargs="+", default=[], help="a journey map that may nest (default: the note's folder)")
    p.add_argument("--dir", action="extend", nargs="+", default=[], help="a folder: every .md directly inside it")
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
    p = sub.add_parser("board-layout")
    p.add_argument("--note", required=True)
    p.add_argument("--lang", choices=sorted(LABELS), help="default: the language of the note's table headers")
    p = sub.add_parser("board-state")
    p.add_argument("--read", required=True, nargs="+", help="the board read back: a Miro SVG, or the host board's element list")
    p.add_argument("--note", required=True)
    p.add_argument("--surface", required=True, choices=bs.SURFACES)
    p.add_argument("--last", help="the previous state: a row the board no longer shows keeps its sticky as an orphan")
    p.add_argument("--out", required=True, help="~/.grow-pm/journey-maps/<product>/journey-<slug>.<surface>.board.json")
    p = sub.add_parser("board-diff")
    p.add_argument("--last", help="the board's state (board-state JSON) or an older read")
    p.add_argument("--now", nargs="+", help="the board read back now: by the state's ids, then over its area")
    p.add_argument("--note", required=True)
    p.add_argument("--surface", choices=bs.SURFACES, help="default: the state's")
    p.add_argument("--out", help="keep the diff for board-take")
    p = sub.add_parser("board-take")
    p.add_argument("--note", required=True)
    p.add_argument("--diff", required=True, help="the board-diff result (--out, or its JOURNEY_RESULT line)")
    p.add_argument("--take", nargs="*", default=[], help="element ids (or row ids) the PM takes")
    p.add_argument("--class", dest="klass", action="extend", nargs="+", help="<element id>=<class> the PM picked in the preview")
    p.add_argument("--parent", action="extend", nargs="+", help="<element id>=<row id>")
    p.add_argument("--drop", nargs="*", default=[], help="row ids gone from the board that leave the note")
    p.add_argument("--date", help="YYYY-MM-DD of the team's board (default: today, UTC)")
    p.add_argument("--dry-run", action="store_true", help="the preview: nothing written")
    p = sub.add_parser("nest")
    p.add_argument("--note", required=True, help="the map whose subtree is shown — a root, or a child at its own level")
    p.add_argument("--map", action="extend", nargs="+", default=[], help="a journey map that may nest — ctx search --type cjm-journey's files")
    p.add_argument("--dir", action="extend", nargs="+", default=[], help="a folder: every .md directly inside it")
    p.add_argument("--lang", choices=sorted(LABELS), help="default: the language of the note's table headers")
    p.add_argument("--json", action="store_true", help="the result line alone, no tree for the chat")
    sub.add_parser("schema")
    try:
        args = ap.parse_args(argv)
    except SystemExit as e:                          # a wrong argument still ends with the result line
        if e.code in (0, None):
            return 0
        result(ok=False, error="wrong arguments — see journey_map.py <command> --help")
        return 2
    fn = {"parse": cmd_parse, "check": cmd_check, "render-html": cmd_render, "health": cmd_health,
          "refresh": cmd_refresh, "tree": cmd_tree, "board-layout": cmd_board_layout, "board-state": cmd_board_state,
          "board-diff": cmd_board_diff, "board-take": cmd_board_take, "nest": cmd_nest, "schema": cmd_schema}.get(args.cmd)
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
