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
COMMANDS = ("parse", "check", "render-html", "health", "refresh", "tree", "board-layout", "board-state", "board-diff",
            "board-take", "schema")
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


# ------------------------------------------------------------------ the board (§11–§12, since v4.8.0)
BOARD_ROLES = ("cell", "row", "header", "lane_name", "team", "orphan", "frame", "other")
DIFF_CATEGORIES = ("changed", "moved", "added", "removed", "orphaned", "hc_edits", "other", "unrecorded")
TAKE_REFUSED = ("health_check", "metric_move", "no_cell", "needs_drop", "not_removed", "secret", "empty", "not_takeable",
                "unknown")
TAKE_NAMED = ("contact_removed", "link_removed", "no_class", "bad_class", "orphan", "bad_parent", "bad_code")
TEAM_SOURCE = {"uk": "дошка команди", "en": "team board"}
STATE_KIND = "journey-board"
HC_LANES = ("metric", "anomaly")
TEAM_ROW = re.compile(r"^b(\d+)$")
MARKERS = re.compile(r"\[(?:link removed|contact hidden)\]")


def _norm(s):
    return re.sub(r"\s+", " ", str(s or "")).strip()


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
    if _is_hc(r):
        return HC_SOURCE
    if r["lane"] in ("initiative", "experiment") and r["code"].strip():
        return r["code"].strip()
    return ""


def board_rows(note):
    """The rows the board shows — exactly the page's (page_worthy), each with its board text and second line."""
    declared = [s["id"] for s in note["stages"]]
    out = []
    for r in [r for r in note["rows"] if page_worthy(r, declared)]:
        out.append(dict(r, board_text=nt.safe(r["text"]), second=second_line(r), hc=_is_hc(r)))
    return out


def _rendered(r):
    """The texts a row's sticky reads back as: its board text, with its second line after a space."""
    texts = []
    for base in (r["board_text"], (r["board_text"] + " " + r["second"]) if r["second"] else ""):
        if base:
            texts += [_norm(base), _norm(bs.plain(base))]
    return list(dict.fromkeys(texts))


def _heads(note):
    out = set()
    for s in note["stages"]:
        for t in ("%s · %s" % (s["id"], s["name"]), s["name"], s["outcome"], "%s · %s %s" % (s["id"], s["name"], s["outcome"])):
            if _norm(t):
                out.add(_norm(t))
    return out


def _lane_texts():
    return {w.lower() for l in LANE_IDS for w in (l, dict(LANES)[l], LABELS["en"]["lane"][l])}


def _cell(it, declared):
    return parse_cell(it.get("frame_text"), declared) if it.get("frame") else None


def assign_roles(items, note, exclude=()):
    """Give each item its role — cell (with its stage and lane), row (with its id), header, lane_name, team, frame or
    other — by what the note says now. A sticky takes a row of its text in its own cell first, then any row of its text
    (it was moved); two stickies of one text take that text's rows in turn (`ambiguous`)."""
    declared = [s["id"] for s in note["stages"]]
    rows = [r for r in board_rows(note) if r["id"] not in exclude]
    by_text = {}
    for r in rows:
        for t in _rendered(r):
            by_text.setdefault(t, []).append(r)
    heads, lanes = _heads(note), _lane_texts()
    for it in items.values():
        for k in ("role", "row", "stage", "lane", "hc"):
            it.pop(k, None)
        if it["kind"] == "frame":
            own = parse_cell(it["text"], declared)
            if own:
                it["role"], it["stage"], it["lane"] = "cell", own[0], own[1]
            else:
                it["role"] = "header" if _norm(it["text"]) in heads else "frame"
            continue
        c = _cell(it, declared)
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
            it["role"], it["row"] = "row", r["id"]
            if r["hc"]:
                it["hc"] = True
            taken.add(r["id"])
            if len(by_text[_norm(it["text"])]) > 1:
                ambiguous.append(it["id"])
    for it in items.values():
        if it.get("role"):
            continue
        t = _norm(it["text"])
        it["role"] = ("header" if t in heads else "lane_name" if t.lower() in lanes
                      else "team" if it["kind"] == "sticky" else "other")
    return ambiguous


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
            return items, data.get("surface")
    items = bs.read_board(path, surface)
    assign_roles(items, note)
    return items, surface or ("miro" if path.lower().endswith(".svg") else "whiteboard")


def _cell_fields(prefix, c, it):
    return {prefix: it.get("frame_text", "") if c else "", "stage" + ("_" + prefix if prefix != "cell" else ""): c[0] if c else None,
            "lane" + ("_" + prefix if prefix != "cell" else ""): c[1] if c else None}


def board_diff(last, now, note):
    """The board now against its last state, by element id: what the team did to the map's rows, apart from the
    health-check rows (hc_edits — named, never taken), the plugin's stickies of rows the board no longer shows
    (orphaned), other items and the map's own items the state lacks (unrecorded)."""
    declared = [s["id"] for s in note["stages"]]
    on_board = {r["id"]: r for r in board_rows(note)}
    out = {k: [] for k in DIFF_CATEGORIES}
    out["orphaned"] = [{"id": mid, "row": it.get("row"), "text": it["text"], "kind": it["kind"]} for mid, it in sorted(last.items())
                       if it.get("role") in ("row", "orphan") and it.get("row") not in on_board]
    gone = {o["id"] for o in out["orphaned"]}
    mapped = {it.get("row") for it in last.values() if it.get("role") == "row"}
    fresh = {mid: dict(it) for mid, it in now.items() if mid not in last}
    assign_roles(fresh, note, exclude=mapped)
    for mid, it in now.items():
        old = last.get(mid)
        cn_ = _cell(it, declared)
        if old is None:
            f = fresh[mid]
            entry = dict({"id": mid, "kind": it["kind"], "text": it["text"]}, **_cell_fields("cell", cn_, it))
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
        row = old.get("row") if role == "row" else None
        hc = role == "row" and row in on_board and on_board[row]["hc"]
        co = _cell(old, declared)
        if _norm(old["text"]) != _norm(it["text"]):
            e = dict({"id": mid, "row": row, "last": old["text"], "now": it["text"]}, **_cell_fields("cell", cn_, it))
            if hc:
                out["hc_edits"].append(dict(e, change="text"))
            elif role in ("row", "team"):
                out["changed"].append(dict(e, team=role == "team"))
            else:
                out["other"].append(dict(e, role=role, change="text"))
        if role in ("row", "team") and co != cn_:
            e = dict({"id": mid, "row": row, "text": it["text"]}, **_cell_fields("from", co, old))
            e.update(_cell_fields("to", cn_, it))
            out["hc_edits" if hc else "moved"].append(dict(e, change="moved") if hc else dict(e, team=role == "team"))
    for mid, old in last.items():
        if mid in now or mid in gone:
            continue
        role = old.get("role") or "other"
        row = old.get("row") if role == "row" else None
        e = {"id": mid, "row": row, "text": old["text"], "cell": old.get("frame_text", "")}
        if role == "row" and row in on_board and on_board[row]["hc"]:
            out["hc_edits"].append(dict(e, change="removed"))
        elif role == "row":
            out["removed"].append(e)
        else:
            out["other"].append(dict(e, role=role, change="removed"))
    out["counts"] = {k: len(out[k]) for k in ("changed", "moved", "added", "removed", "orphaned", "hc_edits")}
    return out


def _rows_map(items):
    """{row id: element id} of the stickies a state maps to rows — what the next version updates by id."""
    return {it["row"]: mid for mid, it in items.items() if it.get("role") == "row" and it.get("row")}


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
    uk_lanes = any(r["cells"][pos["lane"]].strip().lower() in LANE_ALIAS for r in live)
    applied, refused, named, ask, prop = [], [], [], [], []
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

    def clean(text, i, row=None):
        t = _norm(MARKERS.sub("", str(text or "")))
        if t.startswith("[hidden:") or cn.scan(t):
            refuse(i, "secret", "the sticky holds %s — never written" % (", ".join(cn.scan(t)) or "a hidden secret"))
            return None
        t2 = _norm(nt.CONTACT.sub("", t))
        if t2 != t:
            named.append({"element": i, "row": row, "why": "contact_removed", "detail": "an e-mail or a phone removed before the write"})
        t3 = _norm(nt.LINK.sub("", t2)).strip(" ,;")
        if t3 != t2.strip(" ,;"):
            named.append({"element": i, "row": row, "why": "link_removed", "detail": "a link removed before the write"})
        if not t3:
            refuse(i, "empty", "nothing left to write")
            return None
        return t3

    edits, moves, news, drops = {}, {}, [], set()
    used = {r["id"] for r in note["rows"]}
    for i in take:
        es = ents.get(i)
        if es is None and i in by_row:
            i, es = by_row[i]
        if not es:
            refuse(i, "unknown", "no such element or row in the diff")
            continue
        cats = {c for c, _ in es}
        e0 = es[0][1]
        rid = e0.get("row") if cats & {"changed", "moved", "removed"} else None
        r = by_id.get(rid) if rid else None
        if rid and r is None:
            refuse(i, "unknown", "row %s is not in the note" % rid)
            continue
        if r is not None:
            if _is_hc(r):
                refuse(i, "health_check", "row %s is the health-check's — named, never taken (R25)" % rid)
                continue
            if "removed" in cats:
                refuse(i, "needs_drop", "row %s is gone from the board — dropped only with --drop %s" % (rid, rid))
                continue
            for cat, e in es:
                if cat == "changed":
                    t = e.get("now", "")
                    sec = second_line(r)
                    if sec and _norm(t).endswith(" " + sec):
                        t = _norm(t)[:-len(sec) - 1]
                    code = None
                    if r["lane"] == "initiative":
                        parts = _norm(t).rsplit(" ", 1)
                        if len(parts) == 2 and CODE.match(parts[1]):
                            t, code = parts[0], parts[1]
                    t = clean(t, i, rid)
                    if t is None:
                        break
                    edits[rid] = dict(edits.get(rid, {}), text=t, **({"code": code} if code else {}))
                    applied.append({"element": i, "row": rid, "action": "text", "before": r["text"], "after": t})
                elif cat == "moved":
                    st, ln = e.get("stage_to"), e.get("lane_to")
                    if not st or st not in declared or ln not in LANE_IDS:
                        refuse(i, "no_cell", "row %s was moved out of every cell" % rid)
                        break
                    if (ln in HC_LANES or r["lane"] in HC_LANES) and ln != r["lane"]:
                        refuse(i, "metric_move", "row %s: a move into or out of the metric and anomaly lanes is never taken" % rid)
                        break
                    moves[rid] = (st, ln)
                    applied.append({"element": i, "row": rid, "action": "move", "from": "%s · %s" % (r["stage"], r["lane"]),
                                    "to": "%s · %s" % (st, ln)})
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
        code = ""
        t0 = _norm(text)
        if ln == "initiative":
            parts = t0.rsplit(" ", 1)
            if len(parts) == 2 and CODE.match(parts[1]):
                t0, code = parts[0], parts[1]
        t = clean(t0, i)
        if t is None:
            continue
        n = 1
        while "b%d" % n in used:
            n += 1
        nid = "b%d" % n
        used.add(nid)
        key = i
        cls = picked.get(key, "")
        if cls and (ln not in LANE_CLASSES or cls not in LANE_CLASSES[ln]):
            named.append({"element": i, "row": nid, "why": "bad_class",
                          "detail": "%s takes %s" % (ln, ", ".join(LANE_CLASSES.get(ln, ())) or "no class")})
            cls = ""
        if ln in LANE_CLASSES and not cls:
            named.append({"element": i, "row": nid, "why": "no_class", "detail": "no class from the PM — a finding, never on the page"})
            ask.append({"element": i, "row": nid, "lane": ln, "text": t, "classes": list(LANE_CLASSES[ln]) + [""]})
        par = parents.get(key, "")
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
            named.append({"element": i, "row": nid, "why": "bad_code", "detail": "no epic or feature code on the sticky's second line"})
        source = "%s %s" % (TEAM_SOURCE.get(lang, TEAM_SOURCE["en"]), when)
        news.append((st, {"id": nid, "stage": st, "lane": lane_cell(ln), "text": t, "parent": par, "code": code, "source": source,
                          "class": cls, "date": when}))
        applied.append({"element": i, "row": nid, "action": "add", "cell": cell_title(st, ln, lang), "text": t, "class": cls,
                        "source": source, "parent": par, "code": code})
    removed = {str(e.get("row")) for e in diff.get("removed", []) or [] if isinstance(e, dict) and e.get("row")}
    for rid in drop:
        r = by_id.get(rid)
        if r is None or rid not in removed:
            refuse(rid, "not_removed", "row %s is not gone from the board — a row leaves the note only when the board lost it" % rid)
            continue
        if _is_hc(r):
            refuse(rid, "health_check", "row %s is the health-check's — never dropped from the board" % rid)
            continue
        drops.add(r["line"])
        applied.append({"row": rid, "action": "drop", "text": r["text"]})
    new_line = {}
    for rid in set(edits) | set(moves):
        r = by_id[rid]
        cells = (list(r["cells"]) + [""] * len(cols))[:len(cols)]
        for k, v in edits.get(rid, {}).items():
            cells[pos[k]] = v
        if rid in moves:
            cells[pos["stage"]], cells[pos["lane"]] = moves[rid][0], lane_cell(moves[rid][1])
        new_line[r["line"]] = nt.row_line(cells) + eol
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
    return {"text": "".join(out), "applied": applied, "refused": refused, "named": named, "ask_class": ask, "parents": prop}


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


def cmd_board_layout(args):
    note = load(args.note)
    lang = args.lang or note["lang"]
    declared = [s["id"] for s in note["stages"]]
    rows = board_rows(note)
    names = lane_names(lang)
    live = [r for r in note["rows"] if not r["gap"]]
    stages = [{"id": s["id"], "name": s["name"], "outcome": s["outcome"] or "⚠️ TBD", "title": "%s · %s" % (s["id"], s["name"]),
               "gap": not any(r["stage"] == s["id"] and evidence(r) for r in rows)} for s in note["stages"]]
    cells = []
    for li, lane in enumerate(LANE_IDS):
        for si, s in enumerate(note["stages"]):
            cells.append({"title": cell_title(s["id"], lane, lang), "stage": s["id"], "lane": lane, "column": si, "line": li,
                          "rows": [{"id": r["id"], "text": r["board_text"], "second": r["second"], "health_check": r["hc"]}
                                   for r in rows if r["stage"] == s["id"] and r["lane"] == lane]})
    result(ok=True, title=note["journey"] or note["title"], lang=lang, columns=declared,
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


def cmd_board_state(args):
    note = load(args.note)
    items = bs.read_boards(args.read, args.surface)
    ambiguous = assign_roles(items, note)
    shown_rows = board_rows(note)
    on_board, hc_rows = {r["id"] for r in shown_rows}, {r["id"] for r in shown_rows if r["hc"]}
    if args.last and os.path.exists(args.last):
        last, _ = load_board_state(args.last, note, args.surface)
        mapped = {it["row"] for it in items.values() if it.get("role") == "row"}
        for mid, old in last.items():
            it = items.get(mid)
            if it is None or it.get("role") == "row" or old.get("role") not in ("row", "orphan"):
                continue
            if old.get("row") not in on_board:      # a row the board no longer shows: its sticky stays the plugin's own
                it["role"], it["row"] = "orphan", old.get("row")
            elif old.get("row") not in mapped:      # its row is still there (a refreshed metric): the sticky keeps it by id
                it["role"], it["row"] = "row", old.get("row")
                mapped.add(old["row"])
    for it in items.values():
        it.pop("hc", None)
        if it.get("role") == "row" and it.get("row") in hc_rows:
            it["hc"] = True
    state = {"version": 1, "kind": STATE_KIND, "surface": args.surface, "note": os.path.basename(args.note),
             "at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "elements": items}
    try:
        out = _write_json(args.out, state)
    except OSError as e:
        result(ok=False, error="the state cannot be written: %s" % (e.strerror or type(e).__name__))
        return 1
    rows = _rows_map(items)
    roles = {}
    for it in items.values():
        roles[it["role"]] = roles.get(it["role"], 0) + 1
    lang = note["lang"]
    have = {it["text"] for it in items.values() if it.get("role") == "cell"}
    result(ok=True, out=out, surface=args.surface, rows=rows, cells={it["text"]: mid for mid, it in items.items() if it.get("role") == "cell"},
           roles=roles, unmapped_rows=[r["id"] for r in shown_rows if r["id"] not in rows],
           missing_cells=[cell_title(s["id"], l, lang) for l in LANE_IDS for s in note["stages"]
                          if cell_title(s["id"], l, lang) not in have and cell_title(s["id"], l, "en" if lang == "uk" else "uk") not in have],
           ambiguous=ambiguous, orphans={it["row"]: mid for mid, it in items.items() if it.get("role") == "orphan"})
    return 0


def cmd_board_diff(args):
    if not args.last or not os.path.exists(args.last):
        result(ok=True, state="unknown", why="no last state of the board on this machine")
        return 0
    note = load(args.note)
    last, surface = load_board_state(args.last, note, args.surface)
    if not args.now:
        result(ok=True, state="scope", surface=surface, scope=bs.scope(last), ids=sorted(last), rows=_rows_map(last))
        return 0
    now = bs.read_boards(args.now, args.surface or surface)
    payload = dict(ok=True, state="diff", surface=surface, **board_diff(last, now, note))
    payload.update(scope=bs.scope(last), ids=sorted(last), rows=_rows_map(last))
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
    fd, tmp = tempfile.mkstemp(prefix=".journey-take-", suffix=".md")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        found = [f for f in findings(load(tmp), datetime.date.today()) if f.get("row") in touched]
    finally:
        os.remove(tmp)
    result(ok=True, dry_run=bool(args.dry_run), note_written=written, findings=found, **plan)
    return 0


def cmd_schema(args):
    result(ok=True, fields=list(FIELDS), columns=[list(c) for c in COLUMNS], lanes=[list(l) for l in LANES],
           lanes_order=list(LANE_IDS), levels=list(LEVELS), classes=list(CLASSES), findings=list(FINDINGS),
           model_findings=list(MODEL_FINDINGS), commands=list(COMMANDS), board_roles=list(BOARD_ROLES),
           diff_categories=list(DIFF_CATEGORIES), take_refused=list(TAKE_REFUSED), take_named=list(TAKE_NAMED),
           team_source=TEAM_SOURCE, errors=check_protocol(os.path.dirname(HERE)))
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
    p.add_argument("--class", dest="klass", action="append", help="<element id>=<class> the PM picked in the preview")
    p.add_argument("--parent", action="append", help="<element id>=<row id>")
    p.add_argument("--drop", nargs="*", default=[], help="row ids gone from the board that leave the note")
    p.add_argument("--date", help="YYYY-MM-DD of the team's board (default: today, UTC)")
    p.add_argument("--dry-run", action="store_true", help="the preview: nothing written")
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
          "board-diff": cmd_board_diff, "board-take": cmd_board_take, "schema": cmd_schema}.get(args.cmd)
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
