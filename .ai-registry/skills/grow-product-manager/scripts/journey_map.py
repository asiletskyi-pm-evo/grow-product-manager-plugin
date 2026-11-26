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
  page-diff    the edits made on the map's page (v4.12.0) — a file the page saved, or the text it copied — as a diff
               board-take reads: one preview for the board's and the page's edits, a child's rows into its own note
  nest         the nesting (v4.10.0): the map's subtree of child maps by their `parent` links, each child's roll-up
               (pains by class, anomalies, outcome metric, last health point) — never a copy of a row — and the
               findings of the nesting; nothing written
  app-data     the map as the data of one section of an app's snapshot (v4.13.0): the rows, cells and attributes its
               page shows, its health and its child maps — what the app's map.js draws and EDIT edits; no person
  schema       the fields, columns, lanes, levels, findings, board roles and commands the protocol must agree with
               (checks 28 and 29)

The note is the source of truth: a markdown table of rows under its frontmatter (`product`, `journey`, `owner`,
`reviewed`, `stages`, `health`, `published`). The `health` field is written through publications.write_field — the
same code that writes `published` — so a field is replaced and nothing else moves. Table parsing, escaping, link
removal and secret hiding are note_table.py's, shared with story_map.py. Every command ends with one
`JOURNEY_RESULT {json}` line. Stdlib only (Python 3.9). Exit 0; 2 for a wrong argument or a note or snapshot that does
not read; 1 when a file cannot be written.
"""
import argparse, datetime, json, os, re, sys, tempfile, unicodedata

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
            "board-take", "page-diff", "nest", "app-data", "schema")
NEST_FINDINGS = ("orphan_child", "nest_cycle", "too_deep", "other_product_parent", "self_parent")
ORPHAN_WHY = ("no_parent", "bad_parent", "no_stage", "no_stage_in_parent", "no_step")       # why a child hangs on nothing (§14)
MAX_DEPTH = 3                                    # root → child → grandchild (R38); deeper is a reference by name only
UNSAFE_MARKS = ("·", "•", "|", "—", "–", ":", "#")   # what a tree board's cell titles and row keys are split by (§14)
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
            "parent": parent_field(fm)[0], "parent_bad": parent_field(fm)[1], "parent_stage": nt.fm_scalar(fm, "parent_stage"),
            "parent_step": nt.fm_scalar(fm, "parent_step"),
            "parent_step_bad": bool(re.search(r"^parent_step[ \t]*:[ \t]*\S", fm, re.M)) and not nt.fm_scalar(fm, "parent_step")}


NO_VALUE = ("", "null", "~", '""', "''")


def parent_field(fm):
    """(the `parent` value, why it does not read — or "") from a frontmatter (§14, C2a): a scalar, a wiki link written
    with or without quotes (YAML reads `[[x]]` unquoted as a list), or Obsidian's list property of one item. Two or more
    parents, or a value that is no name, are named (`bad_parent`), never read as no parent; `null` or `~` is none."""
    m = re.search(r"^parent[ \t]*:[ \t]*(.*?)[ \t]*$", fm, re.M)
    if not m:
        return "", ""
    raw = m.group(1)
    if raw.split(" #")[0].strip().lower() in NO_VALUE:
        items = []
        for line in fm[m.end():].split("\n")[1:]:
            it = re.match(r"^[ \t]+-[ \t]*(.*?)[ \t]*$", line)
            if not it:
                if line.strip() == "":
                    continue
                if line[:1] in " \t" and not items:  # `parent:` written as a mapping: no map's name
                    return "", "the value is a mapping, not a map's name"
                break
            items.append(it.group(1).strip().strip("\"'").strip())
        items = [i for i in items if i.lower() not in NO_VALUE]
        if len(items) == 1:
            return items[0], ""
        return ("", "") if not items else ("", "%d parents — one map hangs under one" % len(items))
    v = nt.fm_scalar(fm, "parent")
    if v:
        return v, ""
    if re.match(r"^\[\[[^\[\]]+\]\]$", raw):            # an unquoted wiki link
        return raw, ""
    flow = re.match(r"^\[(.*)\]$", raw)
    if flow:
        items = [i.strip().strip("\"'").strip() for i in flow.group(1).split(",") if i.strip()]
        if len(items) == 1:
            return items[0], ""
        if len(items) > 1:
            return "", "%d parents — one map hangs under one" % len(items)
    return "", "the value does not read as a map's name"


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
            "map": link_name(nt.fm_scalar(fm, "map")),
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
    "uk": {"lang": "uk", "title": "Карта шляху", "note": "Нотатка", "owner": "Власник", "reviewed": "Рев'ю", "generated": "Згенеровано",
           "health": "Здоров'я", "no_trend": "тренду немає — у знімках немає health_score у frontmatter",
           "gap": "немає доказів", "target": "ціль", "no_outcome": "⚠️ TBD", "lanes": "Доріжки",
           "not_shown": "Рядків не показано: %d — без джерела чи доказу, поза етапами або доріжками; їх називають знахідки нотатки",
           "lane": dict(LANES)},
    "en": {"lang": "en", "title": "Journey map", "note": "Note", "owner": "Owner", "reviewed": "Reviewed", "generated": "Generated",
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


# ------------------------------------------------------------------ editing on the page (v4.12.0, §9)
# The switch «Редагувати» on every page of the map (the user's decision, 2026-11-25): the page reads what it may edit from
# the attributes of its markup (`edit_attrs`), keeps the edits in memory and hands them over as a file of edits — saved, or
# copied as text — never a request; `page-diff` turns that file into a diff the board's take reads (§12). The script is
# fixed bytes: no data of a note ever goes into it.
EDIT_KIND = "journey-page-edits"
EDIT_VERSION = 1
EDIT_OPS = ("text", "move", "add", "remove", "parent", "code", "target")
EDIT_ATTRS = ("map", "digest", "stage", "lane", "title", "row", "parent", "code", "target", "locked")
PAGE_SOURCE = {"uk": "сторінка команди", "en": "team page"}
EDIT_LABELS = {
    "uk": {"on": "Редагувати", "off": "Готово", "save": "Зберегти правки", "copy": "Скопіювати правки",
           "count": "Правок: %d", "copied": "Скопійовано. Встав правки в чат із PM: вони потраплять у карту після його перегляду.",
           "copyfail": "Копіювання заблоковане — виділи текст у полі нижче й скопіюй його.",
           "saved": "Файл правок збережено — надішли його PM.",
           "savefail": "Збереження заблоковане — скористайся «Скопіювати правки».",
           "locked": "Цей рядок не редагується тут: метрики й рядки health-check оновлює сам health-check.",
           "unsaved": "Є незбережені правки.", "moved": "Рядок перенесено. Щоб повернути, відкрий його й натисни «Відмінити правки рядка».",
           "help": "Перетягни картку в іншу клітинку, щоб перенести її. Клацни картку, щоб змінити текст і звʼязки. «+ Додати» "
                   "в клітинці створює новий рядок. Сторінка нічого не надсилає: коли закінчиш, натисни «Скопіювати правки» "
                   "й передай їх PM — у карту вони потраплять лише після його перегляду («забери правки зі сторінки карти шляху»).",
           "t-row": "Редагування рядка", "t-new": "Новий рядок", "text": "Текст", "stage": "Етап", "lane": "Доріжка",
           "parent": "Належить до (parent)", "ph": "Рядок цього етапу, з якого виростає цей: біль і рішення — з можливості, "
           "експеримент — з рішення, ініціатива — з болю, можливості чи рішення.",
           "pnone": "На цьому етапі ще немає рядка, до якого можна привʼязати цей. Спершу додай його.",
           "c-init": "Код епіка чи фічі в Jira, наприклад PROJ-123", "c-exp": "Id експерименту з реєстру, наприклад exp-назва-20261020",
           "target": "Цільова можливість етапу (лише одна на етап)", "remove": "Прибрати рядок з карти",
           "restore": "Повернути рядок", "reset": "Відмінити правки рядка", "close": "Закрити",
           "apply": "Застосувати", "cancel": "Скасувати", "none": "— не вказано —", "add": "+ Додати",
           "b-edit": "змінено", "b-new": "новий", "b-gone": "прибрано",
           "you": "ти", "someone": "колега", "by": "Останню правку зробив(ла): %s", "syncfail": "Правку не збережено у спільне сховище — перевір доступ і спробуй ще раз.",
           "s-wait": "Підключаю спільні правки…", "s-slow": "Спільні правки поки недоступні — можливо, немає звʼязку.",
           "s-on": "Спільні правки: усі бачать їх одразу", "s-off": "Спільні правки недоступні", "s-stale": "%d старих правок не показано",
           "help-shared": "Правки зберігаються одразу, і всі, хто має доступ до редагування, бачать їх наживо. Перетягни картку, щоб перенести; клацни, щоб змінити текст і звʼязки; «+ Додати» створює рядок. У карту правки потрапляють лише після перегляду PM («забери правки зі сторінки карти шляху»)."},
    "en": {"on": "Edit", "off": "Done", "save": "Save edits", "copy": "Copy edits",
           "count": "Edits: %d", "copied": "Copied. Paste the edits into a chat with the PM: they reach the map after the PM's preview.",
           "copyfail": "Copying is blocked — select the text in the field below and copy it.",
           "saved": "The file of edits is saved — send it to the PM.",
           "savefail": "Saving is blocked — use «Copy edits».",
           "locked": "This row is not edited here: the health-check updates metrics and its own rows.",
           "unsaved": "There are unsaved edits.", "moved": "The row is moved. To undo, open it and press «Undo this row's edits».",
           "help": "Drag a card into another cell to move it. Click a card to change its text and links. «+ Add» in a cell "
                   "creates a row. The page sends nothing: when you are done, press «Copy edits» and give them to the PM — "
                   "they reach the map only after the PM's preview («take the edits from the journey map's page»).",
           "t-row": "Edit the row", "t-new": "New row", "text": "Text", "stage": "Stage", "lane": "Lane",
           "parent": "Belongs to (parent)", "ph": "A row of this stage it grows from: a pain or a solution from an opportunity, "
           "an experiment from a solution, an initiative from a pain, an opportunity or a solution.",
           "pnone": "This stage has no row this one can belong to yet. Add it first.",
           "c-init": "The epic's or feature's Jira code, e.g. PROJ-123", "c-exp": "The experiment's registry id, e.g. exp-name-20261020",
           "target": "The stage's target opportunity (one per stage)", "remove": "Remove the row from the map",
           "restore": "Bring the row back", "reset": "Undo this row's edits", "close": "Close",
           "apply": "Apply", "cancel": "Cancel", "none": "— not set —", "add": "+ Add",
           "b-edit": "edited", "b-new": "new", "b-gone": "removed",
           "you": "you", "someone": "a colleague", "by": "Last edited by: %s", "syncfail": "The edit is not saved to the shared store — check your access and try again.",
           "s-wait": "Connecting the shared edits…", "s-slow": "The shared edits are not reachable yet — maybe no connection.",
           "s-on": "Shared edits: everyone sees them at once", "s-off": "The shared edits are unavailable", "s-stale": "%d old edits not shown",
           "help-shared": "Edits are saved at once, and everyone who may edit sees them live. Drag a card to move it; click it to change its text and links; «+ Add» creates a row. Edits reach the map only after the PM's preview («take the edits from the journey map's page»)."},
}
CSS_EDIT = r"""
.edit-bar{margin:10px 0 0;display:flex;flex-wrap:wrap;gap:8px;align-items:center}.edit-bar button,.edit-form button{font:inherit;padding:6px 12px;border:1px solid #adb5bd;border-radius:6px;background:#fff;color:#1f2328;cursor:pointer}
.edit-bar button:hover,.edit-form button:hover{background:#f1f3f5}.edit-bar .edit-toggle{border-color:#1c7ed6;color:#1c7ed6;font-weight:600}.edit-bar .edit-toggle::before{content:"\270E  "}
body.editing .edit-bar{position:sticky;top:0;z-index:20;background:#fff;border:1px solid #d0d7de;border-radius:10px;padding:10px 12px;box-shadow:0 4px 14px rgba(0,0,0,.08)}
body.editing .edit-bar .edit-toggle{background:#1c7ed6;color:#fff}body.editing .edit-bar .edit-toggle::before{content:"\2713  "}
.edit-bar .edit-copy{border-color:#2b8a3e;color:#2b8a3e;font-weight:600}.edit-count{padding:3px 10px;border-radius:999px;background:#f1f3f5;color:#57606a;font-size:13px}.edit-count.some{background:#fff3bf;color:#7c5800;font-weight:600}
.edit-msg{display:none;flex-basis:100%;padding:8px 10px;border-radius:6px;background:#e7f5ff;color:#1864ab;font-size:13px}.edit-msg.shown{display:block}
.edit-bar .edit-help{flex-basis:100%;margin:0;color:#57606a;font-size:13px;line-height:1.5}
.edit-bar .edit-save,.edit-bar .edit-copy,.edit-bar .edit-count,.edit-bar .edit-help{display:none}body.editing .edit-bar .edit-save,body.editing .edit-bar .edit-copy,body.editing .edit-bar .edit-count{display:inline-block}body.editing .edit-bar .edit-help{display:block}
.edit-sync{display:none;font-size:13px;color:#2b8a3e}body.shared .edit-sync{display:inline-block}body.shared .edit-sync::before{content:"\25CF  "}
body.readonly .edit-toggle{display:none}body.shared.editing .edit-bar .edit-save,body.shared.editing .edit-bar .edit-copy{display:none}
body:not(.shared) .edit-bar .edit-help-shared,body.shared.editing .edit-bar .edit-help:not(.edit-help-shared){display:none!important}
.f-who{margin:-8px 0 0;color:#868e96;font-size:12px}.f-who:empty{display:none}
.edit-out{flex-basis:100%;min-height:70px;max-height:140px;font:12px monospace}body.has-edits .edit-bar .edit-help{display:none}
@media (min-width:900px){body.panel{padding-right:396px}}
.edit-add{display:none;width:100%;margin-top:4px;font:inherit;font-size:12px;border:1px dashed #ced4da;border-radius:6px;background:transparent;color:#868e96;cursor:pointer;padding:3px 6px;text-align:left}
body.editing .edit-add{display:block;opacity:.3}body.editing td:hover>.edit-add,body.editing .edit-add:focus{opacity:1}@media (hover:none){body.editing .edit-add{opacity:1}}.edit-add:hover{border-color:#1c7ed6;color:#1c7ed6;background:#e7f5ff}
body.editing .item[data-row],body.editing .item.added{cursor:grab;user-select:none;-webkit-user-select:none;touch-action:none;position:relative}body.editing .item[data-row]:hover,body.editing .item.added:hover{box-shadow:0 0 0 2px #74c0fc}
body.editing .item[data-locked]{cursor:not-allowed;opacity:.65;touch-action:auto}body.editing .item[data-locked]:hover{box-shadow:none}body.drag-on,body.drag-on *{cursor:grabbing!important}
.item.dragging{opacity:.35}.drag-ghost{position:fixed;z-index:50;margin:0;pointer-events:none;transform-origin:0 0;transform:rotate(1deg);box-shadow:0 8px 24px rgba(0,0,0,.2);opacity:.95}
td.drop-ok{background:#e7f5ff!important;outline:2px dashed #1c7ed6;outline-offset:-3px}
.item.edited{box-shadow:0 0 0 2px #f08c00}.item.removed{opacity:.45;text-decoration:line-through}.item.added{border-left-color:#f08c00;background:#fff9db}.item.current{box-shadow:0 0 0 3px #1c7ed6!important}
.item[data-eb]::after{content:attr(data-eb);position:absolute;top:-8px;right:6px;padding:0 6px;border-radius:999px;background:#f08c00;color:#fff;font-size:10px;line-height:16px;text-decoration:none}
.edit-form{position:fixed;top:0;right:0;bottom:0;z-index:30;width:min(380px,100vw);background:#fff;border-left:1px solid #d0d7de;box-shadow:-8px 0 24px rgba(0,0,0,.12);padding:16px;display:flex;flex-direction:column;gap:12px;overflow:auto;box-sizing:border-box}
.edit-form[hidden],.edit-form [hidden]{display:none}.f-head{display:flex;align-items:center;justify-content:space-between;gap:8px}.f-title{font-size:16px}.edit-form .f-close{border:0;font-size:20px;padding:0 6px;line-height:1}
.f-where{margin:-6px 0 0;color:#57606a;font-size:13px}.edit-form label{display:flex;flex-direction:column;font-size:13px;font-weight:600;color:#343a40;gap:4px}.edit-form label.chk{flex-direction:row;align-items:center;gap:8px;font-weight:400}
.edit-form small{font-weight:400;color:#868e96;line-height:1.4}.f-two{display:flex;gap:8px}.f-two label{flex:1;min-width:0}
.edit-form textarea{min-height:80px;font:inherit;font-weight:400;padding:6px;border:1px solid #ced4da;border-radius:6px}.edit-form select,.edit-form input:not([type]){font:inherit;font-weight:400;padding:5px;border:1px solid #ced4da;border-radius:6px;min-width:0}
.f-acts{display:flex;gap:8px}.edit-form .f-apply{background:#1c7ed6;border-color:#1c7ed6;color:#fff;font-weight:600}.edit-form .f-apply:hover{background:#1971c2}
.f-more{margin-top:auto;padding-top:12px;border-top:1px solid #e9ecef;display:flex;flex-direction:column;gap:6px;align-items:flex-start}.edit-form .f-more button{border:0;padding:4px 0;background:none;color:#57606a}.edit-form .f-remove{color:#c92a2a!important}
@media (max-width:640px){.edit-form{top:auto;left:0;width:100%;max-height:85vh;border-left:0;border-top:1px solid #d0d7de;border-radius:12px 12px 0 0}}"""
# Fixed bytes — no data of a note in it — and no request: the page's edits, a file or a copied text, nothing sent.
EDIT = r'''(function(){var bar=document.querySelector(".edit-bar");if(!bar)return;
function q(s,r){return(r||document).querySelector(s);}
function qa(s,r){return Array.prototype.slice.call((r||document).querySelectorAll(s));}
function A(e,k){return(e&&e.getAttribute("data-"+k))||"";}
function L(k){return A(bar,"l-"+k);}
var P={pain:["opportunity"],solution:["opportunity"],experiment:["solution"],initiative:["pain","opportunity","solution"]};
var CODE={initiative:"c-init",experiment:"c-exp"},LOCK={metric:1,anomaly:1},FLAG="🎯 ",SEP="\u0001";
var ed={},meta={},adds={},nadd=0,cur=null,dirty=false,drag=null,dragged=false,home={},items={},names={};
var shared=null,me=null,canWrite=true,stale=0;
var form=q(".edit-form",bar),out=q(".edit-out",bar),cnt=q(".edit-count",bar),msg=q(".edit-msg",bar),tog=q(".edit-toggle",bar),
sync=q(".edit-sync",bar);
var f={title:q(".f-title",form),where:q(".f-where",form),who:q(".f-who",form),text:q(".f-text",form),stage:q(".f-stage",form),
lane:q(".f-lane",form),parent:q(".f-parent",form),phint:q(".f-phint",form),code:q(".f-code",form),clabel:q(".f-clabel",form),
target:q(".f-target",form),remove:q(".f-remove",form),reset:q(".f-reset",form)};
function on(){return document.body.classList.contains("editing");}
function say(k,keep){msg.textContent=k?L(k):"";msg.className="edit-msg"+(k?" shown":"");clearTimeout(say.t);
if(k&&!keep)say.t=setTimeout(function(){say("");},6000);}
function box(el,show){(el.closest(".f-box")||el).hidden=!show;}
function wrapOf(e){return e.closest(".wrap");}
function own(list,w){return list.filter(function(e){return e.closest(".wrap")===w;});}
function key(w,row){return A(w,"map")+SEP+row;}
function wrapByMap(m){return qa(".wrap[data-map]").filter(function(x){return A(x,"map")===m;})[0];}
function txt(it){var t=q(".t",it).textContent;return t.indexOf(FLAG)===0?t.slice(FLAG.length):t;}
function cellOf(it){var td=it.closest("td");return{stage:A(td,"stage"),lane:A(td,"lane")};}
function stagesOf(w){var tr=own(qa("tbody tr",w),w)[0],ths=own(qa("thead th.stage",w),w);if(!tr)return[];
return own(qa("td[data-stage]",tr),w).map(function(td,i){var th=ths[i],n=th&&th.firstChild&&th.firstChild.nodeType===3?th.firstChild.nodeValue:A(td,"stage");
return{id:A(td,"stage"),name:n};});}
function lanesOf(w){return own(qa("tbody tr",w),w).map(function(tr){var td=q("td[data-lane]",tr),th=q("th",tr);
return td?{id:A(td,"lane"),name:th?th.textContent:A(td,"lane")}:null;}).filter(function(x){return x&&!LOCK[x.id];});}
function nameOf(list,id){for(var i=0;i<list.length;i++){if(list[i].id===id)return list[i].name;}return id;}
function tdOf(w,stage,lane){return own(qa("td[data-stage]",w),w).filter(function(t){return A(t,"stage")===stage&&A(t,"lane")===lane;})[0];}
function place(it,td){if(td&&it.parentNode!==td)td.insertBefore(it,q(".edit-add",td));}
qa("td[data-stage]").forEach(function(td){if(LOCK[A(td,"lane")])return;var b=document.createElement("button");
b.type="button";b.className="edit-add";b.textContent=L("add");td.appendChild(b);});
qa(".item[data-row]").forEach(function(it,i){var w=wrapOf(it);if(!w)return;var c=cellOf(it),k=key(w,A(it,"row"));items[k]=it;
home[k]={o:{text:txt(it),stage:c.stage,lane:c.lane,parent:A(it,"parent"),code:A(it,"code"),target:A(it,"target")==="1"},
td:it.parentNode,ord:i,t:q(".t",it).textContent};it._ord=i;});
function now(k){var h=home[k],e=ed[k]||{},v={};for(var x in h.o){v[x]=e.hasOwnProperty(x)?e[x]:h.o[x];}v.remove=!!e.remove;return v;}
function who(by){return by?(by===me?L("you"):names[by]||L("someone")):"";}
function badge(it,k,by){if(k){it.setAttribute("data-eb",L(k)+(shared&&by?" · "+who(by):""));}else{it.removeAttribute("data-eb");}}
function render(){var tds=[];for(var k in home){if(!home.hasOwnProperty(k))continue;var it=items[k],h=home[k];
if(it.parentNode!==h.td){h.td.insertBefore(it,q(".edit-add",h.td));if(tds.indexOf(h.td)<0)tds.push(h.td);}
q(".t",it).textContent=h.t;it.classList.remove("edited");it.classList.remove("removed");badge(it,"");}
tds.forEach(function(td){qa(":scope > .item[data-row]",td).sort(function(a,b){return a._ord-b._ord;}).forEach(function(it){
td.insertBefore(it,q(".edit-add",td));});});
qa(".item.added").forEach(function(d){d.remove();});
for(var j in ed){if(!ed.hasOwnProperty(j)||!items[j])continue;var e=ed[j],it2=items[j],v=now(j),w=wrapOf(it2);
if(e.hasOwnProperty("text")||e.hasOwnProperty("target"))q(".t",it2).textContent=(v.target?FLAG:"")+v.text;
if(e.hasOwnProperty("stage")||e.hasOwnProperty("lane"))place(it2,tdOf(w,v.stage,v.lane));
it2.classList.toggle("edited",!e.remove);it2.classList.toggle("removed",!!e.remove);badge(it2,e.remove?"b-gone":"b-edit",(meta[j]||{}).by);}
Object.keys(adds).sort().forEach(function(id){var a=adds[id],w2=wrapByMap(a.map);if(!w2)return;var d=document.createElement("div");
d.className="item added";d.setAttribute("data-add",id);d.setAttribute("tabindex","0");badge(d,"b-new",a.by);
var t=document.createElement("div");t.className="t";t.textContent=(a.target?FLAG:"")+a.text;d.appendChild(t);place(d,tdOf(w2,a.stage,a.lane));});
count2();}
function count2(){var n=Object.keys(adds).length+Object.keys(ed).length;
cnt.textContent=L("count").replace("%d",n);cnt.classList.toggle("some",n>0);document.body.classList.toggle("has-edits",n>0);dirty=!shared&&n>0;}
function docId(s){return s.replace(/[^A-Za-z0-9_\-.:+]/g,function(c){return"~"+c.charCodeAt(0).toString(16)+"~";}).slice(0,190);}
function stamp(){return{by:me||"",at:new Date().toISOString()};}
function commitRow(k,e){var has=false;for(var y in e){if(e.hasOwnProperty(y))has=true;}
if(has){ed[k]=e;meta[k]=stamp();}else{delete ed[k];delete meta[k];}render();
if(shared){var p=k.split(SEP),w=wrapByMap(p[0]),ref=shared.collection("edits").doc(docId("r~"+p[0]+"~"+p[1]));
(has?ref.set({kind:"row",map:p[0],row:p[1],digest:A(w,"digest"),edit:e,by:me||"",at:meta[k].at}):ref.delete()).catch(fail);}}
function commitAdd(id,a){if(a){a.by=me||"";adds[id]=a;}else{delete adds[id];}render();
if(shared){var w=a?wrapByMap(a.map):null,ref=shared.collection("edits").doc(id);
(a?ref.set({kind:"add",map:a.map,digest:A(w,"digest"),add:{stage:a.stage,lane:a.lane,text:a.text,parent:a.parent,code:a.code,
target:!!a.target},by:me||"",at:new Date().toISOString()}):ref.delete()).catch(fail);}}
function fail(){say("syncfail",1);}
function opt(sel,value,label,pick){var o=document.createElement("option");o.value=value;o.textContent=label;if(pick)o.selected=true;
sel.appendChild(o);}
function fillSel(sel,list,value){sel.innerHTML="";list.forEach(function(x){opt(sel,x.id,x.name,x.id===value);});}
function fillParents(w,stage,lane,value,self){f.parent.innerHTML="";opt(f.parent,"",L("none"),!value);var ok=P[lane]||[],n=0,ls=lanesOf(w);
own(qa(".item[data-row]",w),w).forEach(function(it){var c=cellOf(it);if(c.stage!==stage||ok.indexOf(c.lane)<0||A(it,"row")===self||
it.classList.contains("removed"))return;n++;var t=txt(it);opt(f.parent,A(it,"row"),nameOf(ls,c.lane)+": "+(t.length>60?t.slice(0,58)+"…":t),
A(it,"row")===value);});if(value&&f.parent.value!==value)opt(f.parent,value,value,true);
f.phint.textContent=n?L("ph"):L("pnone");box(f.parent,!!P[lane]);}
function lanes(){if(!cur)return;var st=f.stage.value,ln=f.lane.value;box(f.code,!!CODE[ln]);f.clabel.textContent=CODE[ln]?L(CODE[ln]):"";
box(f.target,ln==="opportunity");fillParents(cur.w,st,ln,f.parent.value||cur.v.parent,cur.row||"");
f.where.textContent=nameOf(cur.ss,st)+" · "+nameOf(cur.ls,ln);}
f.stage.addEventListener("change",lanes);f.lane.addEventListener("change",lanes);
function open(c){cur=c;var v=c.v;c.ss=stagesOf(c.w);c.ls=lanesOf(c.w);f.text.value=v.text;fillSel(f.stage,c.ss,v.stage);fillSel(f.lane,c.ls,v.lane);
fillParents(c.w,v.stage,v.lane,v.parent,c.row||"");f.code.value=v.code;f.target.checked=!!v.target;
f.title.textContent=c.row?L("t-row"):L("t-new");f.remove.textContent=c.row&&v.remove?L("restore"):L("remove");
var by=c.row?(meta[c.k]||{}).by:c.add!=null?adds[c.add].by:"";f.who.textContent=shared&&by?L("by").replace("%s",who(by)):"";
box(f.remove,!!c.row||c.add!=null);box(f.reset,!!c.row&&!!ed[c.k]);lanes();form.hidden=false;document.body.classList.add("panel");
qa(".item.current").forEach(function(x){x.classList.remove("current");});if(c.it)c.it.classList.add("current");f.text.focus();}
function close(){form.hidden=true;document.body.classList.remove("panel");qa(".item.current").forEach(function(x){x.classList.remove("current");});cur=null;}
function openRow(it){var w=wrapOf(it),k=key(w,A(it,"row"));open({w:w,it:it,row:A(it,"row"),k:k,v:now(k)});}
function openAdd(td,id,it){var w=wrapOf(td);var a=id!=null?adds[id]:{map:A(w,"map"),stage:A(td,"stage"),lane:A(td,"lane"),text:"",parent:"",code:"",target:false};
open({w:w,td:td,add:id,it:it||null,v:{text:a.text,stage:a.stage,lane:a.lane,parent:a.parent,code:a.code,target:a.target,remove:false}});}
function diff(k,v){var o=home[k].o,e={};["text","stage","lane","parent","code","target"].forEach(function(x){if(v[x]!==o[x])e[x]=v[x];});
return v.remove?{remove:true}:e;}
function vals(){var st=f.stage.value,ln=f.lane.value,o=cur.row?home[cur.k].o:{parent:"",code:"",target:false};
return{text:f.text.value.replace(/\s+/g," ").trim(),stage:st,lane:ln,parent:P[ln]?f.parent.value:o.parent,
code:CODE[ln]?f.code.value.trim():o.code,target:ln==="opportunity"?f.target.checked:o.target,remove:false};}
function newId(){nadd++;return"a~"+(me?docId(me).slice(-12):"local")+"~"+Date.now().toString(36)+nadd;}
function apply(){if(!cur)return;var v=vals();if(!v.text){f.text.focus();return;}
if(cur.row){commitRow(cur.k,diff(cur.k,v));}
else{commitAdd(cur.add!=null?cur.add:newId(),{map:A(cur.w,"map"),stage:v.stage,lane:v.lane,text:v.text,parent:v.parent,code:v.code,target:v.target});}
close();}
function remove(){if(!cur)return;if(cur.row){var v=now(cur.k);v.remove=!v.remove;commitRow(cur.k,diff(cur.k,v));}
else if(cur.add!=null){commitAdd(cur.add,null);}close();}
function reset(){if(!cur||!cur.row)return;commitRow(cur.k,{});close();}
q(".f-apply",form).addEventListener("click",apply);q(".f-cancel",form).addEventListener("click",close);q(".f-close",form).addEventListener("click",close);
f.remove.addEventListener("click",remove);f.reset.addEventListener("click",reset);
form.addEventListener("keydown",function(e){if(e.key==="Escape"){e.preventDefault();close();}
else if(e.key==="Enter"&&(e.ctrlKey||e.metaKey)){e.preventDefault();apply();}});
function target(x,y){var el=document.elementFromPoint(x,y),td=el&&el.closest("td[data-stage]");
return td&&drag&&wrapOf(td)===drag.w&&!LOCK[A(td,"lane")]?td:null;}
function lit(td){qa("td.drop-ok").forEach(function(t){if(t!==td)t.classList.remove("drop-ok");});if(td)td.classList.add("drop-ok");}
document.addEventListener("pointerdown",function(ev){if(!on()||ev.button!==0)return;var it=ev.target.closest(".item[data-row],.item.added");
if(!it||it.closest(".edit-bar")||A(it,"locked")||it.classList.contains("chip"))return;ev.stopPropagation();
var rb=it.getBoundingClientRect();drag={it:it,x:ev.clientX,y:ev.clientY,ox:ev.clientX-rb.left,oy:ev.clientY-rb.top,go:false,w:wrapOf(it),g:null,cx:0,cy:0};},true);
document.addEventListener("pointermove",function(ev){if(!drag)return;var dx=ev.clientX-drag.x,dy=ev.clientY-drag.y;
if(!drag.go){if(Math.abs(dx)+Math.abs(dy)<6)return;drag.go=true;var g=drag.it.cloneNode(true);g.className+=" drag-ghost";
g.style.width=drag.it.offsetWidth+"px";g.style.left="0px";g.style.top="0px";document.body.appendChild(g);drag.g=g;var z=g.getBoundingClientRect();drag.cx=z.left;drag.cy=z.top;
drag.it.classList.add("dragging");document.body.classList.add("drag-on");}
ev.preventDefault();drag.g.style.left=(ev.clientX-drag.ox-drag.cx)+"px";drag.g.style.top=(ev.clientY-drag.oy-drag.cy)+"px";
var w=drag.w,r=w.getBoundingClientRect();if(ev.clientX>r.right-40)w.scrollLeft+=18;else if(ev.clientX<r.left+40)w.scrollLeft-=18;
if(ev.clientY>window.innerHeight-40)window.scrollBy(0,18);else if(ev.clientY<40)window.scrollBy(0,-18);
lit(target(ev.clientX,ev.clientY));},{passive:false});
function drop(ev){if(!drag)return;var d=drag,td=d.go&&ev?target(ev.clientX,ev.clientY):null;drag=null;if(!d.go)return;dragged=true;
setTimeout(function(){dragged=false;},0);lit(null);d.g.remove();d.it.classList.remove("dragging");document.body.classList.remove("drag-on");
if(!td||td===d.it.parentNode)return;if(d.it.hasAttribute("data-row")){var k=key(d.w,A(d.it,"row")),v=now(k);v.stage=A(td,"stage");v.lane=A(td,"lane");
if(!P[v.lane])v.parent=home[k].o.parent;commitRow(k,diff(k,v));}else{var id=A(d.it,"add"),a=adds[id];
commitAdd(id,{map:a.map,text:a.text,stage:A(td,"stage"),lane:A(td,"lane"),parent:a.parent,code:a.code,target:a.target&&A(td,"lane")==="opportunity"});}
say("moved");}
document.addEventListener("pointerup",drop);document.addEventListener("pointercancel",function(){drop(null);});
document.addEventListener("click",function(ev){if(!on()||dragged)return;
var t=ev.target;if(t.closest(".edit-form")||t.closest(".edit-bar"))return;var w=t.closest(".wrap");if(w&&w._moved)return;
var b=t.closest(".edit-add");if(b){openAdd(b.closest("td"),null);return;}
var a=t.closest(".item.added");if(a){openAdd(a.closest("td"),A(a,"add"),a);return;}
var it=t.closest(".item[data-row]");if(!it)return;if(A(it,"locked")){say("locked");return;}say("");openRow(it);});
document.addEventListener("keydown",function(ev){if(!on()||ev.key!=="Enter")return;var t=ev.target;
if(t.matches&&t.matches(".item[data-row],.item.added")){ev.preventDefault();t.click();}});
tog.addEventListener("click",function(){var go=document.body.classList.toggle("editing");tog.textContent=go?L("off"):L("on");
qa(".item[data-row]").forEach(function(it){if(go)it.setAttribute("tabindex","0");else if(!it.classList.contains("chip"))it.removeAttribute("tabindex");});
if(!go)close();say("");});
function build(){var day=new Date().toISOString().slice(0,10),maps={},n=0;
function m(name){var w=wrapByMap(name);if(!maps[name])maps[name]={digest:A(w,"digest"),edits:[]};return maps[name].edits;}
for(var k in ed){if(!ed.hasOwnProperty(k))continue;var p=k.split(SEP),e=ed[k],l=m(p[0]),r=p[1],o=home[k].o;
if(e.remove){l.push({op:"remove",row:r});continue;}
if(e.hasOwnProperty("text"))l.push({op:"text",row:r,text:e.text});
if(e.hasOwnProperty("stage")||e.hasOwnProperty("lane"))l.push({op:"move",row:r,stage:e.hasOwnProperty("stage")?e.stage:o.stage,
lane:e.hasOwnProperty("lane")?e.lane:o.lane});
if(e.hasOwnProperty("parent"))l.push({op:"parent",row:r,parent:e.parent});
if(e.hasOwnProperty("code"))l.push({op:"code",row:r,code:e.code});
if(e.hasOwnProperty("target"))l.push({op:"target",row:r,target:!!e.target});}
Object.keys(adds).sort().forEach(function(id){var a=adds[id];n++;m(a.map).push({op:"add",id:"p"+n,stage:a.stage,lane:a.lane,text:a.text,
parent:a.parent,code:a.code,target:!!a.target});});
return JSON.stringify({kind:"journey-page-edits",version:1,product:A(bar,"product"),root:A(bar,"root"),made:day,maps:maps},null,1);}
function put(){out.value=build();out.hidden=true;return out.value;}
q(".edit-save",bar).addEventListener("click",function(){var s=put();try{var u=URL.createObjectURL(new Blob([s],
{type:"application/json"}));var a=document.createElement("a");a.href=u;a.download=A(bar,"root")+".page-edits.json";
document.body.appendChild(a);a.click();a.remove();setTimeout(function(){URL.revokeObjectURL(u);},1000);dirty=false;say("saved",1);}
catch(_){out.hidden=false;say("savefail",1);}});
q(".edit-copy",bar).addEventListener("click",function(){var s=put();function fb(){out.hidden=false;try{out.focus();out.select();
if(document.execCommand("copy")){out.hidden=true;dirty=false;say("copied",1);}else say("copyfail",1);}catch(_){say("copyfail",1);}}
try{navigator.clipboard.writeText(s).then(function(){dirty=false;say("copied",1);},fb);}catch(_){fb();}});
window.addEventListener("beforeunload",function(e){if(dirty){e.preventDefault();e.returnValue=L("unsaved");return L("unsaved");}});
function names2(ids,u){ids=ids.filter(function(x){return x&&!names.hasOwnProperty(x)&&x!==me;});if(!ids.length||!u)return;
u.profiles(ids).then(function(ps){ids.forEach(function(x){names[x]=(ps[x]&&ps[x].name)||"";});render();},function(){});}
function live(db,u){shared=db;document.body.classList.add("shared");sync.textContent=L("s-wait");var t=setTimeout(function(){sync.textContent=L("s-slow");},10000);
db.collection("edits").onSnapshot(function(s){if(!s.metadata.fromCache){clearTimeout(t);sync.textContent=L("s-on");}
var e2={},m2={},a2={},by=[];stale=0;s.docs.forEach(function(d){var x=d.data()||{},w=wrapByMap(String(x.map||""));
if(!w){return;}if(x.digest!==A(w,"digest")){stale++;return;}
if(x.kind==="row"&&x.edit&&typeof x.edit==="object"){var k=key(w,String(x.row||""));if(!home[k])return;e2[k]=x.edit;m2[k]={by:x.by,at:x.at};}
else if(x.kind==="add"&&x.add&&typeof x.add==="object"){var a=x.add;a2[d.id]={map:String(x.map),stage:String(a.stage||""),lane:String(a.lane||""),
text:String(a.text||""),parent:String(a.parent||""),code:String(a.code||""),target:!!a.target,by:x.by};}
else return;by.push(String(x.by||""));});
ed=e2;meta=m2;adds=a2;render();names2(by,u);if(stale)sync.textContent=L("s-on")+" · "+L("s-stale").replace("%d",stale);},
function(){clearTimeout(t);sync.textContent=L("s-off");});}
var C=window.claude;if(C&&typeof C.use==="function"){Promise.all([C.use("db"),C.use("user")]).then(function(r){var db=r[0],u=r[1];if(!db)return;
var ask=u?Promise.all([u.id(),u.canEdit()]):Promise.resolve([null,true]);ask.then(function(x){me=x[0];canWrite=x[1]!==false;
if(!canWrite){document.body.classList.add("readonly");}live(db,u);});},function(){});}
count2();})();'''


def edit_attrs(**kw):
    """The page's editing attributes (§9): ` data-<k>="<v>"` for every value that is not empty, in the order given —
    page-safe values only (the caller passes them through nt.safe), escaped here."""
    return "".join(' data-%s="%s"' % (k, esc(v)) for k, v in kw.items() if v not in ("", None))


def edit_bar(note, note_name, lang):
    """The switch «Редагувати» and what it shows (§9): one line of markup, its words in the page's language — the
    script reads them from the bar's attributes, never carries them. Since the user's review of 2026-11-25: cards are
    dragged between cells, a side panel with labelled fields edits a row, «+ Додати» adds one."""
    E = EDIT_LABELS.get(lang, EDIT_LABELS["en"])
    words = "".join(' data-l-%s="%s"' % (k, esc(E[k])) for k in (
        "on", "off", "count", "copied", "copyfail", "saved", "savefail", "locked", "unsaved", "moved", "none", "ph", "pnone",
        "c-init", "c-exp", "t-row", "t-new", "remove", "restore", "add", "b-edit", "b-new", "b-gone", "you", "someone", "by",
        "syncfail", "s-wait", "s-slow", "s-on", "s-off", "s-stale"))
    return ('<div class="edit-bar"%s%s><button type="button" class="edit-toggle">%s</button><span class="edit-count"></span>'
            '<button type="button" class="edit-copy">%s</button><button type="button" class="edit-save">%s</button>'
            '<span class="edit-sync"></span><span class="edit-msg" role="status"></span><p class="edit-help">%s</p><p class="edit-help edit-help-shared">%s</p>'
            '<div class="edit-form" hidden role="dialog"><div class="f-head"><b class="f-title"></b>'
            '<button type="button" class="f-close" aria-label="%s">\u00d7</button></div><p class="f-where"></p><p class="f-who"></p>'
            '<label>%s<textarea class="f-text"></textarea></label>'
            '<div class="f-two"><label>%s<select class="f-stage"></select></label><label>%s<select class="f-lane"></select></label></div>'
            '<label class="f-box">%s<select class="f-parent"></select><small class="f-phint"></small></label>'
            '<label class="f-box"><span class="f-clabel"></span><input class="f-code"></label>'
            '<label class="chk f-box"><input type="checkbox" class="f-target">%s</label>'
            '<div class="f-acts"><button type="button" class="f-apply">%s</button><button type="button" class="f-cancel">%s</button></div>'
            '<div class="f-more"><button type="button" class="f-reset">%s</button><button type="button" class="f-remove">%s</button></div></div>'
            '<textarea class="edit-out" readonly hidden></textarea></div>') % (
        edit_attrs(product=nt.safe(note["product"]), root=nt.safe(os.path.splitext(note_name)[0])), words,
        esc(E["on"]), esc(E["copy"]), esc(E["save"]), esc(E["help"]), esc(E["help-shared"]), esc(E["close"]), esc(E["text"]), esc(E["stage"]),
        esc(E["lane"]), esc(E["parent"]), esc(E["target"]), esc(E["apply"]), esc(E["cancel"]), esc(E["reset"]), esc(E["remove"]))


EDIT_ATTR_RE = re.compile(r' data-(?:%s)="[^"]*"' % "|".join(EDIT_ATTRS))


def strip_edit(page):
    """The page without its editing (v4.12.0): the bar, its CSS, its script and its attributes — what is left is the page of
    v4.10.0 byte for byte (the tests' regression)."""
    page = page.replace(CSS_EDIT, "", 1).replace("\n<script>%s</script>" % EDIT, "", 1)
    page = re.sub(r'\n<div class="edit-bar"[^\n]*', "", page, count=1)
    return EDIT_ATTR_RE.sub("", page)


def _grid(note, L, chips=None, name=None):
    """The lines of one map's grid: the rows the page may show, the gap marks, and — on a tree page — the chips of its
    child maps at the top of their stage's first lane (`chips`: {stage id: [html]}). Since v4.12.0 the grid carries what
    the page's editing reads (§9): the map's name and the digest of its rows on its frame, each cell's stage, lane and
    title, each row's id, lane, parent, code, target and whether it is locked — attributes of the markup, page-safe, never
    in the script."""
    chips = chips or {}
    name = name if name is not None else os.path.splitext(os.path.basename(note.get("path") or ""))[0]
    out = []
    live = [r for r in note["rows"] if not r["gap"]]
    stages = note["stages"]
    declared = [s["id"] for s in stages]
    hidden = sum(1 for r in live if not page_worthy(r, declared))
    if hidden:
        out.append('<p class="meta">%s</p>' % esc(L["not_shown"] % hidden))
    out.append('<div class="wrap" tabindex="0"%s><table class="grid"><thead><tr><th class="corner"></th>' % edit_attrs(
        map=nt.safe(name), digest=table_sig(note)["table"]))
    for s in stages:
        out.append('<th class="stage">%s · %s<div class="o">%s</div></th>' % (
            shown(s["id"]), shown(s["name"]), shown(s["outcome"] or L["no_outcome"])))
    out.append("</tr></thead><tbody>")
    has_evidence = {s["id"]: any(r["stage"] == s["id"] and evidence(r) and page_worthy(r, declared) for r in live) for s in stages}
    for li, (lane, _) in enumerate(LANES):
        out.append('<tr><th class="lane">%s</th>' % esc(L["lane"][lane]))
        for s in stages:
            out.append("<td%s>" % edit_attrs(stage=nt.safe(s["id"]), lane=lane, title=nt.safe(cell_title(s["id"], lane, L["lang"]))))
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
                out.append('<div class="item l-%s%s"%s><div class="t">%s%s</div><div class="m">%s</div></div>' % (
                    esc(lane), " target" if tg else "", edit_attrs(
                        row=nt.safe(r["id"]), lane=lane, parent=nt.safe(r["parent"]), code=nt.safe(r["code"].strip()),
                        target="1" if tg else "", locked="1" if (_locked(r) or not r["id"]) else ""),
                    "🎯 " if tg else "", shown(r["text"]), shown(meta)))
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
            chips.setdefault(k["stage"], []).append(                    # the parent's stage id: its own grid's key
                '<div class="item chip" data-open="%s" role="button" tabindex="0"><div class="t">↳ «%s»%s</div>'
                '<div class="m">%s · %s</div></div>' % (nid, esc(k["journey"]), esc(step), esc(k["note"] + ".md"),
                                                         esc(_rollup_words(k["rollup"], NL))))
            kn = maps[k["note"]]
            kchips, kbody = parts(k)
            body.append('<details class="child" id="%s"><summary>%s%s → «%s» · %s<span class="m"> · %s · %s</span></summary>' % (
                nid, shown(k["stage"]), esc(step), esc(k["journey"]), esc(T["level"] % k["level"]), esc(k["note"] + ".md"),
                esc(_rollup_words(k["rollup"], NL))))
            body.append('<p class="meta">%s: %s · %s · %s: %s · %s: %s</p>' % (
                esc(L["note"]), esc(k["note"] + ".md"), shown(kn["product"]), esc(L["owner"]), shown(kn["owner"] or "⚠️"),
                esc(L["reviewed"]), shown(kn["reviewed"] or "⚠️")))
            body.extend(_grid(kn, L, kchips, k["note"]))
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
    <details> below. A map without any of them is the page of v4.9.0, byte for byte — apart from the editing of v4.12.0
    (§9): the switch «Редагувати», its CSS, its one fixed script and the attributes it reads (`strip_edit` removes exactly
    them)."""
    L = LABELS.get(lang, LABELS["en"])
    tree = nest is not None and bool(nest["tree"]["children"] or nest["tree"]["deeper"] or nest["ancestors"])
    T = TREE_LABELS.get(lang, TREE_LABELS["en"])
    title = note["journey"] or note["title"] or note_name
    out = ["<!doctype html>", '<html lang="%s"><head><meta charset="utf-8">' % esc(lang),
           '<meta name="viewport" content="width=device-width,initial-scale=1">',
           "<title>%s — %s</title><style>%s</style></head><body>" % (esc(L["title"]), shown(title), CSS + (CSS_TREE if tree else "") + CSS_EDIT),
           "<h1>%s: %s</h1>" % (esc(L["title"]), shown(title)),
           '<p class="meta">%s: %s · %s · %s: %s · %s: %s</p>' % (
               esc(L["note"]), shown(note_name), shown(note["product"]), esc(L["owner"]), shown(note["owner"] or "⚠️"),
               esc(L["reviewed"]), shown(note["reviewed"] or "⚠️")),
           '<p class="meta">%s: %s</p>' % (esc(L["generated"]), esc(datetime.date.today().isoformat())),
           edit_bar(note, note_name, lang)]
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
    out.extend(_grid(note, L, chips, os.path.splitext(note_name)[0]))
    if body:
        out.append("<h2>%s</h2>" % esc(T["children"]))
        out.extend(body)
    out.append("<script>%s</script>" % (PAN_TREE if tree else PAN))
    out.append("<script>%s</script>" % EDIT)
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
           "level": "рівень", "subtree": "з дочірніми картами (%d): %s %d · %s %d"},
    "en": {"head": "Tree «%s» (%s) · level %d · child maps in the tree %d", "pains": "pains", "anomalies": "anomalies",
           "critical": "critical %d", "outcome": "outcome", "health": "health", "no_snapshot": "no snapshot",
           "reviewed": "reviewed", "step": "step", "deeper": "deeper — a reference only, level %d (too_deep)",
           "findings": "Findings of the nesting:", "skipped": "Skipped", "ancestors": "Above it: %s", "none": "no child maps",
           "level": "level", "subtree": "with its child maps (%d): %s %d · %s %d"},
}
NEST_SKIPS = ("unreadable", "wrong_type", "sensitive", "duplicate", "unsafe_name")


def link_name(value):
    """A map's name from a `parent` value: `journey-<slug>`, also written as `[[journey-<slug>]]` (an alias or a heading
    after it dropped), with `.md` or a folder before it — the name alone."""
    s = str(value or "").strip()
    m = re.match(r"^\[\[([^\]|#]*)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]$", s)
    if m:
        s = m.group(1).strip()
    s = s.replace("\\", "/").rsplit("/", 1)[-1].strip()
    return unicodedata.normalize("NFC", s[:-3] if s.lower().endswith(".md") else s)


def name_key(name):
    """A map's name as a link resolves it — Obsidian and the disk both ignore case and Unicode form (NFC/NFD)."""
    return unicodedata.normalize("NFC", str(name or "")).casefold()


def unsafe_name(name):
    """Is a map's file name no fit for a page, a board key or a link — a link, a contact or a secret in it, a space, or a
    separator a tree board's cell title or row key is split by («·», «#», «:», «|», a dash)?"""
    return nt.safe(name) != name or any(c.isspace() or c in UNSAFE_MARKS for c in name) or not name.strip()


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
        skipped.append({"note": nt.safe(os.path.basename(path)), "reason": reason, "detail": detail})
    keys = set()
    for n_, (path, named) in enumerate(items):
        subject = n_ == 0                            # the note asked about: never skipped — the command is about it
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
            if named or str(e) != "the note has no frontmatter":
                skip(path, "unreadable", str(e))     # a map that does not read is named, never taken for plain markdown
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
        name = unicodedata.normalize("NFC", os.path.splitext(os.path.basename(path))[0])
        if not subject and ci.note_meta(path.replace(os.sep, "/"), raw)["sensitive"]:
            skip(path, "sensitive", "a sensitive note — never read into the tree")
            continue
        if not subject and unsafe_name(name):
            skip(path, "unsafe_name", "a file name holding a link, a contact, a secret, a space or a separator (%s) — rename the "
                 "file to nest it" % ", ".join("«%s»" % m_ for m_ in UNSAFE_MARKS))
            continue
        try:
            note = load(path)
        except Bad as e:
            skip(path, "unreadable", str(e))
            continue
        if name_key(name) in keys:
            skip(path, "duplicate", "a second map named %s — the first is kept (a link is by name)" % nt.safe(name))
            continue
        keys.add(name_key(name))
        out[name] = note
    return out, skipped, counts


def nest_forest(maps, skipped=None):
    """The nesting of the maps (§14): {parent: {child: parent}, children: {parent: [children]}, level: {map: n},
    findings}. A child's link attaches it only when its parent is a map of the same product that declares its
    `parent_stage` and, with a `parent_step`, has a row of that step on that stage — else a finding, never a guess. A
    cycle is named once and broken: each map of it stands alone. A level counts from the top root; past MAX_DEPTH a
    map is too_deep — a reference by name only."""
    found, par = [], {}
    fold = {}
    for n_ in maps:                                  # the first map of a name wins — as nest_maps keeps it
        fold.setdefault(name_key(n_), n_)

    def f(code, name, detail, **more):
        found.append(dict({"finding": code, "note": nt.safe(name), "detail": detail}, **more))
    for name in sorted(maps):
        n = maps[name]
        if n.get("parent_bad"):
            f("orphan_child", name, "parent: %s" % n["parent_bad"], why="bad_parent", parent="")
            continue
        p = link_name(n.get("parent"))
        if not p:
            continue
        if name_key(p) == name_key(name):
            f("self_parent", name, "the map names itself as its parent")
            continue
        pn = maps.get(fold.get(name_key(p), ""))
        if pn is None:
            sp, why_ = nt.safe(p), (skipped or {}).get(name_key(p))
            f("orphan_child", name, ("parent %s was skipped (%s) — see skipped" % (sp, why_)) if why_ else
              "parent %s is no map found — renamed, deleted or not given" % sp, why="no_parent", parent=sp)
            continue
        p = fold[name_key(p)]
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
        if n.get("parent_step_bad"):
            f("orphan_child", name, "parent_step does not read as one step (a list or a mapping) — write the step as the "
              "parent's rows write it", why="no_step", parent=nt.safe(p))
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
    if out["children"]:                              # R27: the child's numbers with its own children's (C4c)
        sub, todo = {"maps": 0, "pains_total": out["rollup"]["pains_total"], "anomalies": out["rollup"]["anomalies"]["total"],
                     "critical": out["rollup"]["anomalies"]["critical"]}, list(out["children"])
        while todo:
            k = todo.pop(0)
            sub["maps"] += 1
            sub["pains_total"] += k["rollup"]["pains_total"]
            sub["anomalies"] += k["rollup"]["anomalies"]["total"]
            sub["critical"] += k["rollup"]["anomalies"]["critical"]
            todo += k["children"]
        out["rollup"]["subtree"] = sub
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
    name = unicodedata.normalize("NFC", os.path.splitext(os.path.basename(note_path))[0])
    found[name] = note if name not in found else found[name]
    forest = nest_forest(found, {name_key(os.path.splitext(s_["note"])[0]): s_["reason"] for s_ in skipped})
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
    sub = ru.get("subtree")
    if sub:
        parts.append(L["subtree"] % (sub["maps"], L["pains"], sub["pains_total"], L["anomalies"], sub["anomalies"])
                     + (" (%s)" % (L["critical"] % sub["critical"]) if sub["critical"] else ""))
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
BOARD_ROLES = ("cell", "row", "header", "lane_name", "rollup", "team", "orphan", "frame", "other")
DIFF_CATEGORIES = ("changed", "moved", "added", "removed", "relinked", "recoded", "retargeted", "orphaned", "hc_edits",
                   "other", "unrecorded")
LINK_CATEGORIES = ("relinked", "recoded", "retargeted")       # only from the page (v4.12.0): a board's sticky carries no link
TAKE_REFUSED = ("health_check", "metric_lane", "no_cell", "needs_drop", "not_removed", "taken", "secret", "empty",
                "not_takeable", "unknown", "other_note", "conflict")
TAKE_NAMED = ("contact_removed", "link_removed", "no_class", "bad_class", "orphan", "bad_parent", "bad_code", "bad_target",
              "unused")
COUNTED = ("changed", "moved", "added", "removed", "relinked", "recoded", "retargeted", "orphaned", "hc_edits")
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
    if m.group(1) in declared and lane:
        return m.group(1), lane
    t = re.match(r"^\s*(\S+?)\s*·\s*(\S+?)\s*(?:·|•|\||—|–|:|\s-\s)\s*(.+?)\s*$", str(title or ""))
    if t:                                            # a child's cell on a tree board (§14): «<child> · <stage> · <lane>»
        sid, lane = "%s · %s" % (t.group(1), t.group(2)), lane_of(t.group(3))
        if sid in declared and lane:
            return sid, lane
    return None


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
    for t in (note.get("title"), note.get("journey")) + tuple(note.get("extra_heads", ())):
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
        for k in ("role", "row", "stage", "lane", "hc", "origin", "child"):
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
    marks = note.get("rollup_marks") or {}
    for it in items.values():
        if it.get("role"):
            continue
        t = _norm(it["text"])
        rm = ROLLUP_HEAD.match(t) if marks and it["kind"] == "sticky" and t.lower() not in heads else None
        if rm and name_key(rm.group(1)) in marks:      # a child map's roll-up or reference on a tree board (§14), by its note's
            it["role"], it["origin"], it["child"] = "rollup", "plugin", marks[name_key(rm.group(1))][0]   # name
            continue
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
            return _valid_state(items), data.get("surface"), {"rebuilt": bool(data.get("rebuilt")), "tree": data.get("tree") or []}
    items = safe_items(bs.read_board(path, surface, lines=True))
    assign_roles(items, note)
    return items, surface or ("miro" if path.lower().endswith(".svg") else "whiteboard"), {"rebuilt": True, "tree": []}


def _cell_fields(prefix, c, title):
    return {prefix: title if c else "", "stage" + ("_" + prefix if prefix != "cell" else ""): c[0] if c else None,
            "lane" + ("_" + prefix if prefix != "cell" else ""): c[1] if c else None}


def table_sig(note):
    """The note's identity for a diff: the journey, the product and a digest of its rows — a diff taken into another
    note, or into this one after it changed, is refused."""
    import hashlib
    rows = json.dumps([r["cells"] for r in note["rows"]], ensure_ascii=False)
    return {"journey": note["journey"], "product": note["product"], "table": hashlib.sha256(rows.encode("utf-8")).hexdigest()[:16]}


def tree_blocks(nest):
    """The child maps a tree board shows (§14) — the ones the page shows as grids — depth first, the page's order."""
    out = []

    def walk(n):
        for k in n["children"]:
            out.append(k)
            walk(k)
    walk(nest["tree"])
    return out


def _deeper_all(n):
    return list(n["deeper"]) + [x for k in n["children"] for x in _deeper_all(k)]


def block_title(k, lang):
    """The title of a child's block on a tree board — its journey, its note, its level."""
    return "↳ «%s» · %s · %s" % (k["journey"], k["note"], TREE_LABELS.get(lang, TREE_LABELS["en"])["level"] % k["level"])


def _arrow_head(x, lang):
    NL = NEST_LABELS.get(lang, NEST_LABELS["en"])
    return "↳ «%s» · %s" % (x["journey"], x["note"]) + (" · %s «%s»" % (NL["step"], x["step"]) if x["step"] else "")


def rollup_text(k, lang):
    """A roll-up sticky (§14): the child and its step on the first line, its numbers on the second — never a row."""
    return _arrow_head(k, lang) + "\n" + _rollup_words(k["rollup"], NEST_LABELS.get(lang, NEST_LABELS["en"]))


def reference_text(x, lang):
    """A reference sticky past the depth (R38): the map's name and level, no grid, no link."""
    return _arrow_head(x, lang) + "\n" + TREE_LABELS.get(lang, TREE_LABELS["en"])["deeper"] % x["level"]


def tree_note(nest, lang):
    """The whole tree as one note, the way its board holds it (§14): the map's own stages and rows as they are, and each
    child map the board shows with its stages as `<child> · <id>` and its rows as `<child>#<id>` (C7) — so the board's
    own code (roles, states, diffs) reads a tree board unchanged. Only read: never written, never a page."""
    root = nest["note"]
    stages, rows, heads, marks = list(root["stages"]), list(root["rows"]), [], {}
    for k in tree_blocks(nest):
        n, pre = nest["maps"][k["note"]], k["note"]
        stages += [dict(s_, id="%s · %s" % (pre, s_["id"])) for s_ in n["stages"]]
        for r in n["rows"]:
            rows.append(dict(r, id=("%s#%s" % (pre, r["id"])) if r["id"] else "", stage="%s · %s" % (pre, r["stage"]),
                             parent=("%s#%s" % (pre, r["parent"])) if r["parent"] else "", note=pre))
        heads += [block_title(k, lang), k["journey"]]
        marks[name_key(k["note"])] = (k["note"], "rollup")
    for x in _deeper_all(nest["tree"]):
        marks[name_key(x["note"])] = (x["note"], "reference")
    return dict(root, stages=stages, rows=rows, extra_heads=heads, rollup_marks=marks,
                tree=[k["note"] for k in tree_blocks(nest)])


ROLLUP_HEAD = re.compile(r"^↳ «.*?» · (\S+)")       # a roll-up or reference sticky's first words: the child by its note's name


def rollup_ids(items, note):
    """({child: the element id of its roll-up sticky}, {map: the element id of its reference sticky}) of a tree board —
    what a new version updates by id (§11, §14)."""
    marks = note.get("rollup_marks") or {}
    kinds = {n_: k_ for n_, k_ in marks.values()}
    ups, refs = {}, {}
    for mid, it in sorted(items.items()):
        c = it.get("child")
        if it.get("role") == "rollup" and c in kinds:
            (ups if kinds[c] == "rollup" else refs).setdefault(c, mid)
    return ups, refs


def tree_sigs(nest):
    """{child: its table_sig} of the children a tree board shows — a take into a child checks its own note."""
    return {k["note"]: table_sig(nest["maps"][k["note"]]) for k in tree_blocks(nest)}


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
    out = {k: [] for k in DIFF_CATEGORIES if k not in LINK_CATEGORIES}     # a sticky carries no link: the page's alone

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
            if f.get("role") in ("row", "cell", "header", "lane_name", "rollup"):
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
    out["counts"] = {k: len(out[k]) for k in COUNTED if k not in LINK_CATEGORIES}
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
    page_source = "%s %s" % (PAGE_SOURCE.get(lang, PAGE_SOURCE["en"]), when)

    def source_of(e):                                # an edit from the page (v4.12.0) is the team page's, else the board's
        return page_source if isinstance(e, dict) and e.get("via") == "page" else team_source
    applied, refused, named, ask, prop = [], [], [], [], []
    used_keys = set()
    ents = {}
    for cat in ("changed", "moved", "added", "removed") + LINK_CATEGORIES + ("hc_edits", "orphaned", "other", "unrecorded"):
        for e in diff.get(cat, []) or []:
            if isinstance(e, dict) and e.get("id") is not None:   # a health-check edit reads as what it did — the row decides
                c = {"text": "changed", "moved": "moved", "removed": "removed"}.get(e.get("change"), cat) if cat == "hc_edits" else cat
                ents.setdefault(str(e["id"]), []).append((c, e))
    by_row = {}
    for k, es in ents.items():
        for cat, e in es:
            if e.get("row") and cat in ("changed", "moved", "removed") + LINK_CATEGORIES:
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

    edits, moves, news, drops, links, new_targets, new_pars = {}, {}, [], set(), [], [], []
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
    done, planned = set(), set()
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
        rid = e0.get("row") if cats & ({"changed", "moved", "removed"} | set(LINK_CATEGORIES)) else None
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
                    ed = {"text": t, "source": source_of(e), "date": when, "class": cls}
                    if code:
                        ed["code"] = code
                    edits[rid] = dict(edits.get(rid, {}), **ed)
                    applied.append({"element": i, "row": rid, "action": "text", "before": r["text"], "after": t,
                                    "source": source_of(e), "class": cls})
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
                elif cat in LINK_CATEGORIES:             # a link the page changed (v4.12.0): checked once the moves are known
                    links.append((i, rid, cat, e))
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
        page_code = _norm(e0.get("code")) if e0.get("via") == "page" else ""
        if page_code and not code:                   # the page's own code field (v4.12.0), checked as the sticky's line is
            if ln in ("initiative", "experiment") and (CODE if ln == "initiative" else EXP_ID).match(page_code) and not cn.scan(page_code):
                code = page_code
            else:
                named.append({"element": i, "row": None, "why": "bad_code", "detail": "%r is no %s" % (
                    nt.safe(page_code), "epic or feature code" if ln == "initiative" else "registry id" if ln == "experiment" else "code of this lane")})
        t = clean(" ".join(ls), i)
        if t is None:
            continue
        if any(r["stage"] == st and r["lane"] == ln and _norm(r["text"]) == t for r in live):
            refuse(i, "taken", "the note already holds this row on %s — an earlier take" % cell_title(st, ln, lang))
            continue
        if (st, ln, t) in planned:                   # the same sticky on two boards (§14) is one row
            refuse(i, "taken", "the same sticky on another board is taken in this take — one row on %s" % cell_title(st, ln, lang))
            continue
        planned.add((st, ln, t))
        nid = new_ids.get(i)
        if nid is None:
            refuse(i, "unknown", "no new row for %s in the diff" % i)
            continue
        cls = klass(i, nid, ln, t)
        if e0.get("via") == "page" and ln in HC_LANES:   # the page adds no metric or anomaly row (R25), as a board's move cannot
            refuse(i, "metric_lane", "a new row in the metric and anomaly lanes is never taken — the health-check writes them")
            continue
        par = pick(parents, i, nid) or (_norm(e0.get("parent")) if e0.get("via") == "page" else "")
        if ln == "initiative" and not code:
            named.append({"element": i, "row": nid, "why": "bad_code", "detail": "no epic or feature code on the sticky's own second line"})
        values = {"id": nid, "stage": st, "lane": lane_cell(ln), "text": t, "parent": par, "code": code, "source": source_of(e0),
                  "class": cls, "date": when}
        if e0.get("via") == "page" and e0.get("target"):
            if ln == "opportunity":
                new_targets.append((i, nid, st, values))
            else:
                named.append({"element": i, "row": nid, "why": "bad_target", "detail": "%s is no opportunity — a target only on one" % _a(ln)})
        news.append((st, values))
        applied.append({"element": i, "row": nid, "action": "add", "cell": cell_title(st, ln, lang), "text": t, "class": cls,
                        "source": source_of(e0), "parent": par, "code": code})
        new_pars.append((i, nid, st, ln, par, values, applied[-1]))
    yes = "так" if lang == "uk" else "yes"

    def stage_lane(r):
        return moves.get(r["id"], (r["stage"], r["lane"])) if by_id.get(r["id"]) is r else (r["stage"], r["lane"])
    for i, nid, st, ln, par, values, a in new_pars:  # a new row's parent: where the parent stands once the moves are taken
        if par:
            pr = by_id.get(par)
            if pr is None or ln not in PARENTS or stage_lane(pr)[1] not in PARENTS[ln] or stage_lane(pr)[0] != st:
                named.append({"element": i, "row": nid, "why": "bad_parent", "detail": "%s cannot hang under %s" % (ln, nt.safe(par))})
                par = values["parent"] = a["parent"] = ""
        if not par and ln in NEEDS_PARENT:
            cands = [r["id"] for r in live if stage_lane(r)[0] == st and stage_lane(r)[1] in PARENTS[ln]]
            named.append({"element": i, "row": nid, "why": "orphan", "detail": "%s needs its parent" % _a(ln)})
            prop.append({"element": i, "row": nid, "lane": ln, "candidates": cands})
    target_now = {r["id"]: r["target"].strip().lower() in YES for r in live}
    for i, rid, cat, e in links:                     # the page's links (v4.12.0): §5's rules, as check names them
        r = by_id[rid]
        st, ln = stage_lane(r)
        if cat == "relinked":
            v = _norm(e.get("parent_now"))
            pr = by_id.get(v) if v else None
            if v and (pr is None or ln not in PARENTS or stage_lane(pr)[1] not in PARENTS[ln] or stage_lane(pr)[0] != st or v == rid):
                named.append({"element": i, "row": rid, "why": "bad_parent", "detail": "%s cannot hang under %s (§5)" % (ln, nt.safe(v))})
                continue
            if not v and ln in NEEDS_PARENT:
                named.append({"element": i, "row": rid, "why": "orphan", "detail": "%s needs its parent — not cleared" % _a(ln)})
                prop.append({"element": i, "row": rid, "lane": ln, "candidates": [x["id"] for x in live if stage_lane(x)[0] == st
                                                                                   and stage_lane(x)[1] in PARENTS[ln]]})
                continue
            edits[rid] = dict(edits.get(rid, {}), parent=v)
            applied.append({"element": i, "row": rid, "action": "parent", "before": r["parent"], "after": v})
        elif cat == "recoded":
            v = _norm(e.get("code_now"))
            ok = ln in ("initiative", "experiment") and v and (CODE if ln == "initiative" else EXP_ID).match(v) and not cn.scan(v)
            if not ok:
                named.append({"element": i, "row": rid, "why": "bad_code", "detail": "%r is no %s — not written" % (
                    nt.safe(v), "epic or feature code" if ln == "initiative" else "registry id" if ln == "experiment" else "code of this lane")})
                continue
            edits[rid] = dict(edits.get(rid, {}), code=v)
            applied.append({"element": i, "row": rid, "action": "code", "before": r["code"], "after": v})
        else:
            v = bool(e.get("target_now"))
            if ln != "opportunity":
                named.append({"element": i, "row": rid, "why": "bad_target", "detail": "%s is no opportunity — a target only on one" % _a(ln)})
                continue
            target_now[rid] = v
            edits[rid] = dict(edits.get(rid, {}), target=yes if v else "")
            applied.append({"element": i, "row": rid, "action": "target", "before": r["target"], "after": yes if v else ""})
    for st in {stage_lane(r)[0] for r in live}:      # one target per stage (§5): a second one the take would make is not set
        on = [r["id"] for r in live if target_now.get(r["id"]) and stage_lane(r)[0] == st]
        if len(on) > 1:
            for a in [a for a in applied if a.get("action") == "target" and a["after"] and a["row"] in on]:
                applied.remove(a)
                edits[a["row"]].pop("target", None)
                named.append({"element": a["element"], "row": a["row"], "why": "bad_target",
                              "detail": "a second target on %s — one target opportunity per stage" % st})
                target_now[a["row"]] = False
        on = [x for x in on if target_now.get(x)]
        if len(on) > 1:                              # still two: a move brought a target onto a stage that has one
            for rid in [x for x in on if x in moves and moves[x][0] != by_id[x]["stage"]]:
                edits[rid] = dict(edits.get(rid, {}), target="")
                named.append({"element": rid, "row": rid, "why": "bad_target",
                              "detail": "moved onto %s, which has its target — the moved row's target is cleared" % st})
                target_now[rid] = False
    for i, nid, st, values in new_targets:
        if any(target_now.get(r["id"]) and stage_lane(r)[0] == st for r in live) or any(
                x[2] == st and x[3].get("target") for x in new_targets if x[1] != nid):
            named.append({"element": i, "row": nid, "why": "bad_target", "detail": "a second target on %s — one target opportunity per stage" % st})
        else:
            values["target"] = yes
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
    for cat in ("changed", "moved", "removed") + LINK_CATEGORIES + ("hc_edits", "added"):
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
    errs += _check_nest(proto, skill, texts.get("references/artifact-publishing.md", ""), rep)
    errs += _check_page(proto, skill)
    return errs


def _check_page(proto, skill):
    """Check 28's page part (v4.12.0 — no new check): §9 «Editing on the page» names the page's ops as the script does;
    §15 keeps the page from any request and from a write past §12's preview; the skill's Step J9 runs `page-diff`."""
    errs = []
    s9 = nt.section(proto, "9. The script")
    if "**Editing on the page**" not in s9:
        errs.append("journey-protocol.md §9 has no «Editing on the page» (v4.12.0)")
    ops = [nt.tick(r[0]) or "?" for r in nt.table_after(s9, r"\| Op \| What \|")]
    if ops != list(EDIT_OPS):
        errs.append("journey-protocol.md §9: the page's ops %s ≠ journey_map.py EDIT_OPS %s" % ("|".join(ops), "|".join(EDIT_OPS)))
    if EDIT_KIND not in s9:
        errs.append("journey-protocol.md §9 does not name the file of edits' kind «%s»" % EDIT_KIND)
    s15 = nt.section(proto, "15. What never happens")
    if "A request from the page" not in s15:
        errs.append("journey-protocol.md §15 does not keep the page from any request (v4.12.0)")
    if skill is not None and not re.search(r"^- \*\*J9\b.*page-diff", skill, re.M):
        errs.append("skills/cjm-research/SKILL.md has no step J9 that runs page-diff (the page's edits, v4.12.0)")
    return errs


def _check_nest(proto, skill, ap, rep=""):
    """Check 28's nesting part (v4.10.0, C13 — no new check): §14 «Nested maps» names the script's findings, the why
    codes of orphan_child and the depth; «What never happens» is §15; the skill's Step J runs `nest`; artifact-publishing
    §4 asks two places of two keys in one question."""
    errs = []
    s14 = nt.section(proto, "14. Nested maps")
    if not s14:
        return ["journey-protocol.md has no §14 «Nested maps» (v4.10.0)"]
    got = [nt.tick(r[0]) or "?" for r in nt.table_after(s14, r"\| Finding \| What \| Proposal \|")]
    if got != list(NEST_FINDINGS):
        errs.append("journey-protocol.md §14: the nesting's findings %s ≠ journey_map.py NEST_FINDINGS %s" % ("|".join(got) or "—", "|".join(NEST_FINDINGS)))
    why = [nt.tick(r[0]) or "?" for r in nt.table_after(s14, r"\| Why \| When \|")]
    if why != list(ORPHAN_WHY):
        errs.append("journey-protocol.md §14: orphan_child's why codes %s ≠ journey_map.py ORPHAN_WHY %s" % ("|".join(why) or "—", "|".join(ORPHAN_WHY)))
    words = {3: "three"}
    if "%s levels at most" % words.get(MAX_DEPTH, MAX_DEPTH) not in s14:
        errs.append("journey-protocol.md §14 does not say «%s levels at most» (journey_map.py MAX_DEPTH)" % words.get(MAX_DEPTH, MAX_DEPTH))
    for f in NEST_FIELDS:
        if "`%s`" % f not in s14:
            errs.append("journey-protocol.md §14 does not name the child's field `%s` (journey_map.py NEST_FIELDS)" % f)
    for m_ in UNSAFE_MARKS:
        if "«%s»" % m_ not in s14:
            errs.append("journey-protocol.md §14 does not name the unsafe-name mark «%s» (journey_map.py UNSAFE_MARKS)" % m_)
    sub = NEST_LABELS["uk"]["subtree"].split(" (")[0]
    if "«%s (N)" % sub not in s14:
        errs.append("journey-protocol.md §14 does not quote the subtree line «%s (N)…» (journey_map.py NEST_LABELS)" % sub)
    if skill:
        for want in ("board-layout --with-children", "board-take --note <child> --diff"):
            if want not in skill:
                errs.append("skills/cjm-research/SKILL.md: J8 does not run `%s` (journey-protocol.md §14)" % want)
    if rep and not re.search(r"^(?=.*journey_map\.py refresh)(?=.*without a `parent`).*$", rep, re.M):
        errs.append("cjm-reports.md: the scheduled refresh does not say it refreshes the maps without a `parent` (journey-protocol.md §14)")
    if not nt.section(proto, "15. What never happens"):
        errs.append("journey-protocol.md: «What never happens» is not §15 (§14 is «Nested maps» since v4.10.0)")
    if skill and "journey_map.py nest" not in skill:
        errs.append("skills/cjm-research/SKILL.md: Step J does not run `journey_map.py nest` for a child map (journey-protocol.md §14)")
    if ap and not re.search(r"\*\*Two places of two keys in one question\*\*.*journey-protocol\.md` §14", nt.section(ap, "4. One question")):
        errs.append("artifact-publishing.md §4: no «Two places of two keys in one question» rule for a child map (journey-protocol.md §14)")
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
        for word in PAGE_SOURCE.values():
            if word not in s12:
                errs.append("journey-protocol.md §12 does not name the page's source «%s <date>» (journey_map.py PAGE_SOURCE)" % word)
    ap = texts.get("references/artifact-publishing.md")
    if ap is not None:
        if not re.search(r"^\|\s*`board`\s*\|.*`cjm-research`", nt.section(ap, "1. The kind"), re.M):
            errs.append("artifact-publishing.md §1: the `board` row does not name its consumer `cjm-research` (the journey map)")
        if not re.search(r"ARTIFACT `typed` when it has this kind \([^)]*\bboard\b", nt.section(ap, "2. The candidates")):
            errs.append("artifact-publishing.md §2: ARTIFACT `typed` does not list the board kind (the host's own board)")
    order = (("references/journey-protocol.md", "then the host's own board, then a registry record's board"),
             ("references/artifact-publishing.md", "the host's own first, then a registry record's"),
             ("skills/cjm-research/SKILL.md", "the host's own before a registry record's"))
    for rel, want in order:                          # the user's rule (v4.10.0): the host's own tools first, a paid
        if texts.get(rel) is not None and want not in texts[rel]:     # board tool never needed
            errs.append("%s: the journey map's boards are not offered with the host's own board first (%s)" % (rel, want))
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
           stages=len(note["stages"]), health=len(note["health"]), errors=note["errors"],
           **({"children": _shown_count(nest["tree"]), "deeper": _deeper_of(nest["tree"]), "above": [a["note"] for a in nest["ancestors"]]}
              if nest and (nest["tree"]["children"] or nest["tree"]["deeper"] or nest["ancestors"]) else {}))
    return 0


# ------------------------------------------------------------------ the map inside the app (v4.13.0)
# An installed app (app_shell.py) takes the map from its artifact's database, and its page code (app_shell/map.js) draws
# it from this data: the same rows, the same cells and the same attributes `_grid` writes for EDIT (§9) — so EDIT goes
# into the app unchanged. Only what the page shows (page_worthy, page-safe texts, the page's own words) and no person.
APP_DATA_VERSION = 1
APP_DATA_MAX = 256 * 1024 - 1024        # one map's data: a database document holds 256 KiB, its own fields the last KiB


def app_section(note_name):
    """The snapshot section of a map: `map.<slug>` — the note's name without `journey-` and `.md`, lower case, only
    [a-z0-9.-], at most 64 characters in all (app_shell.py's SECTION); a name with none of them left is named by a
    digest of it."""
    import hashlib
    stem = unicodedata.normalize("NFC", os.path.splitext(os.path.basename(note_name))[0])
    s = re.sub(r"^journey-", "", stem.lower())
    s = re.sub(r"-{2,}", "-", re.sub(r"[^a-z0-9.-]+", "-", s)).strip("-.")[:60].strip("-.")
    if not s:
        s = "m" + hashlib.sha256(stem.encode("utf-8")).hexdigest()[:8]
    return "map." + s


def _app_grid(note, name, L):
    """One grid as data — the rows `_grid` shows with the attributes it writes, each cell's title, the gap marks."""
    live = [r for r in note["rows"] if not r["gap"]]
    declared = [s["id"] for s in note["stages"]]
    worthy = [r for r in live if page_worthy(r, declared)]
    stages = [{"id": nt.safe(s["id"]), "title": nt.safe(s["name"]), "outcome": nt.safe(s["outcome"] or L["no_outcome"]),
               "gap": not any(r["stage"] == s["id"] and evidence(r) for r in worthy),
               "cells": [nt.safe(cell_title(s["id"], lane, L["lang"])) for lane in LANE_IDS]} for s in note["stages"]]
    rows = []
    for r in worthy:
        lane = r["lane"]
        tg = r["target"].strip().lower() in YES and lane == "opportunity"
        meta = " · ".join(x for x in (r["step"], r["level"] if lane == "metric" else "", r["code"], r["source"],
                                      r["class"], r["date"], L["target"] if tg else "") if x)
        rows.append({"id": nt.safe(r["id"]), "stage": nt.safe(r["stage"]), "lane": lane, "text": nt.safe(r["text"]),
                     "parent": nt.safe(r["parent"]), "code": nt.safe(r["code"].strip()), "target": tg,
                     "locked": bool(_locked(r) or not r["id"]), "meta": nt.safe(meta)})
    hidden = len(live) - len(worthy)
    return {"map": nt.safe(name), "product": nt.safe(note["product"]), "table_sig": table_sig(note)["table"],
            "stages": stages, "rows": rows, "not_shown": hidden, "not_shown_text": L["not_shown"] % hidden if hidden else ""}


def _app_tree(nest, lang):
    """The child maps as data, as `_tree_parts` draws them: each child's grid, chip and summary, its own children nested,
    the first level past MAX_DEPTH as references by name — never its owner."""
    L, T, NL = LABELS.get(lang, LABELS["en"]), TREE_LABELS.get(lang, TREE_LABELS["en"]), NEST_LABELS.get(lang, NEST_LABELS["en"])
    maps = nest["maps"]

    def parts(n):
        kids, refs = [], []
        for k in n["children"]:
            kn = maps[k["note"]]
            step = (" · %s «%s»" % (NL["step"], k["step"])) if k["step"] else ""
            words = _rollup_words(k["rollup"], NL)
            g = _app_grid(kn, k["note"], L)
            g.update({"note": k["note"], "journey": k["journey"], "level": k["level"], "stage": nt.safe(k["stage"]), "step": k["step"],
                      "chip": {"t": "↳ «%s»%s" % (k["journey"], step), "m": "%s · %s" % (k["note"] + ".md", words)},
                      "summary": "%s%s → «%s» · %s" % (nt.safe(k["stage"]), step, k["journey"], T["level"] % k["level"]),
                      "summary_m": " · %s · %s" % (k["note"] + ".md", words),
                      "meta": "%s: %s · %s · %s: %s" % (L["note"], k["note"] + ".md", nt.safe(kn["product"]), L["reviewed"],
                                                        nt.safe(kn["reviewed"] or "⚠️"))})
            g.update(parts(k))
            kids.append(g)
        for x in n["deeper"]:
            refs.append({"note": x["note"], "journey": x["journey"], "level": x["level"], "stage": nt.safe(x["stage"]),
                         "t": "↳ «%s»%s" % (x["journey"], (" · %s «%s»" % (NL["step"], x["step"])) if x["step"] else ""),
                         "m": "%s · %s" % (x["note"] + ".md", T["deeper"] % x["level"])})
        return {"children": kids, "deeper": refs, "deeper_text": T["deeper_list"] % ", ".join(
            "«%s» (%s.md)" % (x["journey"], x["note"]) for x in n["deeper"]) if n["deeper"] else ""}
    return parts(nest["tree"])


def app_data(note, note_name, lang, nest=None):
    """The data of one map's snapshot section (§9): the map's grid as `render_html` draws it, its health, its child maps
    to three levels and the maps above it — the page's words in `lang`, every value page-safe, no person."""
    L, T = LABELS.get(lang, LABELS["en"]), TREE_LABELS.get(lang, TREE_LABELS["en"])
    name = os.path.splitext(note_name)[0]
    tree = nest is not None and bool(nest["tree"]["children"] or nest["tree"]["deeper"] or nest["ancestors"])
    title = note["journey"] or note["title"] or note_name
    pts = [{"date": p["date"], "score": p["score"], "snapshot": nt.safe(p["snapshot"])}
           for p in note["health"] if p["score"] is not None and day(p["date"])]
    above = [{"note": a["note"], "journey": a["journey"], "level": a["level"]} for a in nest["ancestors"]] if tree else []
    out = {"v": APP_DATA_VERSION}
    out.update(_app_grid(note, name, L))
    out.update({"note": note_name, "journey": nt.safe(title), "reviewed": nt.safe(note["reviewed"]), "lang": lang,
                "lanes": [{"id": lane, "title": L["lane"][lane]} for lane in LANE_IDS],
                "health": {"points": pts, "trend": trend(pts)},
                "tree": _app_tree(nest, lang) if tree else {"children": [], "deeper": [], "deeper_text": ""},
                "above": above,
                "texts": {"title": "%s: %s" % (L["title"], nt.safe(title)),
                          "meta": "%s: %s · %s · %s: %s" % (L["note"], nt.safe(note_name), nt.safe(note["product"]), L["reviewed"],
                                                            nt.safe(note["reviewed"] or "⚠️")),
                          "above": T["above"] % " → ".join("«%s» (%s)" % (a["journey"], a["note"]) for a in above) if above else "",
                          "health": L["health"], "no_trend": L["no_trend"], "gap": "⚠️ " + L["gap"], "children": T["children"]}})
    return out


def cmd_app_data(args):
    note = load(args.note)
    if str(note.get("type") or "").strip().lower() != "cjm-journey":
        raise Bad("%s is not a journey map (type: %s)" % (os.path.basename(args.note), note.get("type") or "—"))
    lang = args.lang or note["lang"]
    nest = page_nest(note, args.map, args.dir, lang)
    name = os.path.basename(note["path"])
    data = app_data(note, name, lang, nest)
    raw = json.dumps(data, ensure_ascii=False)
    size = len(raw.encode("utf-8"))
    info = {"section": app_section(name), "map": data["map"], "product": data["product"], "rows": len(data["rows"]),
            "not_shown": data["not_shown"], "children": _shown_count(nest["tree"]) if nest else 0,
            "deeper": _deeper_of(nest["tree"]) if nest else []}
    if size > APP_DATA_MAX:
        result(ok=False, error="the map's data is %d bytes — over the 256 KiB of one database document: it stays out of the app, "
                               "open its page" % size, bytes=size, **info)
        return 1
    try:
        with open(args.out, "w", encoding="utf-8", newline="") as fh:
            fh.write(raw)
    except OSError as e:
        result(ok=False, error="the data cannot be written: %s" % (e.strerror or type(e).__name__))
        return 1
    result(ok=True, out=args.out, bytes=size, **info)
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
    mine = unicodedata.normalize("NFC", os.path.splitext(os.path.basename(args.note))[0])
    if snap["map"] and name_key(snap["map"]) != name_key(mine):
        raise Bad("the snapshot is of map %s, not of %s — a snapshot made for one map (`map:`) refreshes that map only (§14)"
                  % (nt.safe(snap["map"]), nt.safe(mine)))
    if not snap["map"] and (link_name(note["parent"]) or note.get("parent_bad")):
        raise Bad("%s is a child map — its stages are its own, so the funnel's snapshot never refreshes it; a snapshot made "
                  "for it names it in its frontmatter (`map: %s`, §14)" % (nt.safe(mine), nt.safe(mine)))
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
    except OSError as e:                             # the note is refreshed; only its page is not
        result(ok=False, error="the note is refreshed, the page cannot be written: %s" % (e.strerror or type(e).__name__), **summary)
        return 1
    above, failed = [], []                           # the pages of the maps above it show its roll-up: rendered again,
    for a in (nest["ancestors"] if nest else []):    # beside each map's note, locally — never published (§10, §14)
        an = nest["maps"][a["note"]]
        page = os.path.splitext(an["path"])[0] + ".html"
        try:
            note_a = load(an["path"])
            _render_to(note_a, page, args.lang or note_a["lang"])     # each page in its own map's language
            above.append(page)
        except (OSError, Bad) as e:                  # one page above that cannot be written never fails the refresh
            failed.append({"page": page, "error": getattr(e, "strerror", None) or str(e) or type(e).__name__})
    if above:
        summary["pages_above"] = above
    if failed:
        summary["pages_above_failed"] = failed
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
    payload = dict(ok=True, title=nt.safe(note["journey"] or note["title"]), lang=lang, columns=declared,
                   lanes=[{"id": l, "name": names[l]} for l in LANE_IDS], stages=stages, cells=cells,
                   titles=[c["title"] for c in cells], hidden=[r["id"] for r in live if r["id"] and not page_worthy(r, declared)],
                   rows=len(rows), sticky={"row": "yellow", "health_check": "blue"}, errors=note["errors"])
    if args.with_children:
        payload.update(tree_layout(nest_of(args.note, args.map, args.dir, lang), lang))
        payload["titles"] = payload["titles"] + [c["title"] for b in payload["blocks"] for c in b["cells"]]
        payload["sticky"] = dict(payload["sticky"], rollup="purple")
    result(**payload)
    return 0


def tree_layout(nest, lang):
    """The child maps' part of a tree board (§14, C6): a block of cells per child the page shows, below the map's grid,
    depth first — its cells «<child> · <stage> · <lane>», its rows keyed «<child>#<id>» (C7), the rows its page shows
    only —; a roll-up sticky per child in its parent's cell «<stage> · дії» with the child's numbers, on Miro linked to
    the child's first cell (`link_to`); a reference sticky per map past the depth — a name, no grid, no link."""
    blocks, rollups, refs = [], [], []
    par = nest["forest"]["parent"]
    root = nest["name"]

    def parent_cell(child, stage):
        p = par.get(child)
        return cell_title(stage if p == root else "%s · %s" % (p, stage), "action", lang)
    for b, k in enumerate(tree_blocks(nest), 1):
        n, pre = nest["maps"][k["note"]], k["note"]
        rows = board_rows(n)
        declared = [s_["id"] for s_ in n["stages"]]
        cells = []
        for li, lane in enumerate(LANE_IDS):
            for si, s_ in enumerate(n["stages"]):
                cells.append({"title": cell_title("%s · %s" % (pre, s_["id"]), lane, lang), "stage": s_["id"], "lane": lane,
                              "column": si, "line": li,
                              "rows": [{"id": "%s#%s" % (pre, r["id"]), "text": r["board_text"], "second": r["second"],
                                        "health_check": r["hc"]} for r in rows if r["stage"] == s_["id"] and r["lane"] == lane]})
        blocks.append({"block": b, "note": pre, "journey": k["journey"], "level": k["level"], "parent": nt.safe(par.get(pre) or ""),
                       "stage": k["stage"], "step": k["step"], "title": block_title(k, lang), "columns": declared,
                       "stages": [{"id": s_["id"], "name": nt.safe(s_["name"]), "outcome": nt.safe(s_["outcome"] or OUTCOME_TBD),
                                   "title": nt.safe("%s · %s · %s" % (pre, s_["id"], s_["name"])),
                                   "gap": not any(r["stage"] == s_["id"] and evidence(r) for r in rows)} for s_ in n["stages"]],
                       "cells": cells,
                       "hidden": ["%s#%s" % (pre, r["id"]) for r in n["rows"] if r["id"] and not r["gap"] and not page_worthy(r, declared)]})
        rollups.append({"cell": parent_cell(pre, k["stage"]), "child": pre, "text": rollup_text(k, lang),
                        "link_to": cells[0]["title"] if cells else ""})

    def walk(n):
        for x in n["deeper"]:
            refs.append({"cell": parent_cell(x["note"], x["stage"]), "child": x["note"], "text": reference_text(x, lang)})
        for k in n["children"]:
            walk(k)
    walk(nest["tree"])
    return {"blocks": blocks, "rollups": rollups, "references": refs}


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


def board_note(args, tree=False):
    """(the note the board reads against, the nesting or None): the note itself, or — on a tree board (§14) — the whole
    tree as one note (`tree_note`)."""
    note = load(args.note)
    if not (tree or getattr(args, "with_children", False)):
        return note, None
    nest = nest_of(args.note, getattr(args, "map", ()), getattr(args, "dir", ()), note["lang"])
    return tree_note(nest, note["lang"]), nest


def _state_tree(path):
    """The children a kept tree state names — [] for a plain state, a read, or no file."""
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError, TypeError):
        return []
    return data.get("tree") or [] if isinstance(data, dict) and data.get("kind") == STATE_KIND else []


def cmd_board_state(args):
    note, nest = board_note(args, tree=bool(args.last and _state_tree(args.last)))   # a tree state stays a tree
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
    if nest is not None:
        state["tree"] = note["tree"]                 # a tree board (§14): the children it holds
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
           rebuilt=rebuilt, last_ignored=last_ignored, gone=sorted(it["row"] for it in items.values() if it.get("gone")),
           **({"tree": note["tree"], "rollups": rollup_ids(items, note)[0], "references": rollup_ids(items, note)[1]}
              if nest is not None else {}))
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
        if old.get("role") == "rollup" and it.get("role") in ("team", "rollup"):
            it["role"], it["origin"] = "rollup", "plugin"  # a child's roll-up stays the plugin's, its child gone or renamed,
            it["child"] = it.get("child") or old.get("child")   # and keeps its child by its element id
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
    plain = load(args.note)
    last, surface, meta = load_board_state(args.last, plain, args.surface)
    note, nest = board_note(args, tree=bool(meta.get("tree")))
    if nest is not None and meta.get("rebuilt") and not meta.get("tree"):
        last, _, _ = load_board_state(args.last, note, args.surface)   # an older read: its roles by the tree
    ups = dict(zip(("rollups", "references"), rollup_ids(last, note))) if nest is not None else {}
    if not args.now:
        result(ok=True, state="scope", surface=surface, scope=bs.scope(last), ids=sorted(last), rows=_rows_map(last), **ups)
        return 0
    now = _read_now(args.now, args.surface or surface)
    lost = missing_cells(last, now)
    if lost:                                       # the plugin never deletes a cell: a partial read, never «removed»
        result(ok=True, state="partial", surface=surface, missing_cells=lost, ids=sorted(last), scope=bs.scope(last),
               why="the read lacks %d cell(s) the state holds — read the board again, every page, into a fresh folder" % len(lost))
        return 0
    payload = dict(ok=True, state="diff", surface=surface, **board_diff(last, now, note))
    payload.update(scope=bs.scope(last), ids=sorted(last), rows=_rows_map(last), note=table_sig(plain), **ups)
    if nest is not None:
        payload["map"] = nt.safe(unicodedata.normalize("NFC", os.path.splitext(os.path.basename(args.note))[0]))
        payload["tree"] = tree_sigs(nest)            # a take into a child checks its own note (§14, C8)
    if args.out:
        try:
            payload["out"] = _write_json(args.out, payload)
        except OSError as e:
            result(ok=False, error="the diff cannot be written: %s" % (e.strerror or type(e).__name__))
            return 1
    result(**payload)
    return 0


def _owner(e, tree):
    """The child map an entry of a tree board's diff belongs to — by its row `<child>#<id>`, else by its cell's stage
    `<child> · <stage>` — or None: the diff's own map."""
    rid = str(e.get("row") or "")
    if rid:
        head = rid.split("#", 1)[0]
        return head if "#" in rid and head in tree else None
    for key in ("stage", "stage_to"):
        st = str(e.get(key) or "")
        if st:
            head = st.split(" · ", 1)[0]
            return head if " · " in st and head in tree else None
    return None


def _plain(e, child):
    """An entry of a tree board made the child's own: its row id, stages and cell titles without the child's prefix; a
    cell of another map is no cell of the child (its stage left empty — the take names it no_cell)."""
    pre_r, pre_s = child + "#", child + " · "
    out = dict(e)
    rid = str(e.get("row") or "")
    if rid.startswith(pre_r):
        out["row"] = rid[len(pre_r):]
    for key in ("parent", "parent_now", "parent_last"):         # a link the page changed (v4.12.0) names a row of the child
        v = str(e.get(key) or "")
        if v.startswith(pre_r):
            out[key] = v[len(pre_r):]
    for key in ("stage", "stage_to", "stage_from"):
        v = str(e.get(key) or "")
        if v:
            out[key] = v[len(pre_s):] if v.startswith(pre_s) else None
            if out[key] is None and key != "stage_from":
                out[key.replace("stage", "lane")] = None
    for key in ("cell", "to", "from"):
        v = str(e.get(key) or "")
        if v.startswith(pre_s):
            out[key] = v[len(pre_s):]
    return out


def take_diffs(note, name, diffs):
    """One diff for the note out of every board's diff given (§12, §14, C8): the entries that are this note's — of its
    own board as they are; of a tree board it is a child on, its `<name>#…` rows and `<name> · …` cells made plain —,
    every other map's entries apart (`elsewhere`, never taken here), an element id two diffs share prefixed with its
    diff's number, and the rows two boards changed differently (`conflicts`: the PM takes one version or none, never
    both, never automatically). Raises Bad for a diff of another journey or one older than the note."""
    now = table_sig(note)
    parts = []
    import hashlib
    for d in diffs:                                  # one order whatever the command line's: by board, then by content
        d["_tag"] = "%s@%s" % (nt.safe(str(d.get("map") or name)), str(d.get("surface") or "?"))
        d["_dig"] = hashlib.sha256(json.dumps(d, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")).hexdigest()[:8]
    diffs = sorted(diffs, key=lambda d: (d["_tag"], d["_dig"]))
    tags = [d["_tag"] for d in diffs]
    for d in diffs:
        if tags.count(d["_tag"]) > 1:
            d["_tag"] += "#" + d["_dig"]
    for i, d in enumerate(diffs, 1):
        sig, tree = d.get("note"), d.get("tree") if isinstance(d.get("tree"), dict) else {}
        mine = next((k for k in tree if name_key(k) == name_key(name)), None)   # the name as the tree resolved it
        if mine is not None:
            name, t = mine, tree[mine]
            if not isinstance(t, dict) or (t.get("journey"), t.get("product")) != (now["journey"], now["product"]):
                raise Bad("diff %d holds %s as another journey — run board-diff again" % (i, name))
            if t.get("table") != now["table"]:
                raise Bad("the note changed since diff %d — run board-diff again before taking anything" % i)
            parts.append((i, d, name, tree))
            continue
        if isinstance(sig, dict):
            if sig.get("journey") != now["journey"] or sig.get("product") != now["product"]:
                raise Bad("the diff is of another journey (%s / %s) — run board-diff on this note" % (sig.get("product"), sig.get("journey")))
            if sig.get("table") != now["table"]:
                raise Bad("the note changed since the diff — run board-diff again before taking anything")
        parts.append((i, d, None, tree))
    ids = {}
    for i, d, _, _ in parts:
        for cat in DIFF_CATEGORIES:
            for e in d.get(cat) or []:
                if isinstance(e, dict) and e.get("id") is not None:
                    ids.setdefault(str(e["id"]), set()).add(i)
    shared = {k for k, v in ids.items() if len(v) > 1}
    merged, elsewhere = {k: [] for k in DIFF_CATEGORIES}, []
    for i, d, child, tree in parts:
        for cat in DIFF_CATEGORIES:
            for e in d.get(cat) or []:
                if not isinstance(e, dict):
                    continue
                e = dict(e)
                if e.get("id") is not None and str(e["id"]) in shared:
                    e["id"] = "%s:%s" % (d["_tag"], e["id"])   # an id two boards share, named by its board
                owner = _owner(e, tree)
                if owner == child:
                    merged[cat].append(dict(_plain(e, child) if child else e, board=i))
                elif e.get("id") is not None:
                    elsewhere.append({"id": str(e["id"]), "category": cat, "row": e.get("row"),
                                      "note": owner or str(d.get("map") or "?"), "board": i})
    groups = {}
    for cat, what in (("changed", "text"), ("moved", "cell"), ("relinked", "parent"), ("recoded", "code"), ("retargeted", "target")):
        for e in merged[cat]:
            if e.get("row"):
                groups.setdefault((what, str(e["row"])), []).append(e)
    conflicts = []
    for (what, rid), es in sorted(groups.items()):
        def val(e):
            if what == "text":
                return _norm(e.get("now"))
            if what == "cell":
                return (e.get("stage_to"), e.get("lane_to"))
            return json.dumps(e.get(what + "_now"))
        vals = {val(e) for e in es}
        if len({e["board"] for e in es}) > 1 and len(vals) > 1:
            conflicts.append({"row": rid, "what": what, "versions": [
                dict({"id": str(e["id"]), "board": e["board"]}, **({"now": e.get("now")} if what == "text" else {"to": e.get("to")}
                                                                   if what == "cell" else {"now": e.get(what + "_now")}))
                for e in es]})
    for e in merged["removed"]:                      # gone from one board, changed or moved on another: the PM decides
        rid = str(e.get("row") or "")
        other = [x for (w_, r_), xs in groups.items() if r_ == rid for x in xs if x["board"] != e["board"]]
        if rid and other:
            conflicts.append({"row": rid, "what": "removed", "versions": [{"id": str(e["id"]), "board": e["board"], "removed": True}]
                              + [dict({"id": str(x["id"]), "board": x["board"]}, **({"now": x["now"]} if x.get("now") else {"to": x.get("to")}))
                                 for x in other]})
    return merged, elsewhere, conflicts


def cmd_board_take(args):
    note = load(args.note)
    name = unicodedata.normalize("NFC", os.path.splitext(os.path.basename(args.note))[0])
    diff, elsewhere, conflicts = take_diffs(note, name, [read_diff(p_) for p_ in args.diff])
    missing_cols = [c for c in ("source", "class", "date") if c not in note["cols"]]
    if missing_cols:
        raise Bad("the table has no %s column — a row from the board needs its source, class and date (§7)" % ", ".join(missing_cols))
    when = args.date or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    if day(when) is None:
        raise Bad("--date is not YYYY-MM-DD")
    picked, parents = _pairs(args.klass, "--class"), _pairs(args.parent, "--parent")
    take, early = list(args.take or []), []
    away = {e["id"]: e for e in elsewhere}
    for i in list(take):
        if i in away:                                # another map's row on a tree board: taken only into its own note
            take.remove(i)
            early.append({"id": i, "why": "other_note", "detail": "%s belongs to %s — take it with --note %s.md"
                          % (i, nt.safe(away[i]["note"]), nt.safe(away[i]["note"]))})
    drop = list(args.drop or [])
    for c in conflicts:                              # two boards, two versions of one row: one or none, never both
        hit = [v["id"] for v in c["versions"] if v["id"] in take] + [i for i in take if i == "row:%s" % c["row"]]
        if c["what"] == "removed":
            hit = [h for h in hit if h not in [v["id"] for v in c["versions"] if v.get("removed")]]
            dropped = c["row"] in drop
            refuse_all = bool(hit) and dropped      # the change and the drop of one row: never both
            if refuse_all:
                drop.remove(c["row"])
                early.append({"id": c["row"], "why": "conflict", "detail": "row %s is gone from one board and changed on another "
                              "— drop it or take the change, not both" % c["row"]})
        else:
            refuse_all = len(hit) > 1 or any(h.startswith("row:") for h in hit)
        if refuse_all:
            for i in hit:
                if i in take:
                    take.remove(i)
                early.append({"id": i, "why": "conflict", "detail": "row %s was changed differently on two boards — take "
                              "one version by its element (%s) or none" % (c["row"], ", ".join(v["id"] for v in c["versions"]))})
    plan = take_note(note, diff, take, picked, parents, drop, when)
    plan["refused"] = early + plan["refused"]
    if elsewhere:
        plan["elsewhere"] = elsewhere
    if conflicts:
        plan["conflicts"] = conflicts
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


EDIT_MAX_BYTES = 2 * 1024 * 1024                  # a file of edits past this is no page's — refused unread
EDIT_MAX_TEXT = 4000
PAGE_SKIPS = ("stale", "unknown_map", "unknown_row", "bad_edit", "locked")


def read_edits(path):
    """The file of edits a page saved, or a text holding it (pasted into the chat, a copy with words around it) — its JSON
    object checked for its kind and version; raises Bad. It is another person's input: nothing in it is trusted."""
    try:
        if os.path.getsize(path) > EDIT_MAX_BYTES:
            raise Bad("the file of edits is larger than %d bytes — no page's" % EDIT_MAX_BYTES)
        with open(path, encoding="utf-8") as fh:
            raw = fh.read()
    except OSError as e:
        raise Bad("the file of edits does not read: %s" % (e.strerror or type(e).__name__))
    except UnicodeDecodeError:
        raise Bad("the file of edits is not UTF-8 text")
    start, end = raw.find("{"), raw.rfind("}")
    try:
        data = json.loads(raw[start:end + 1]) if start >= 0 and end > start else None
    except ValueError:
        data = None
    if not isinstance(data, dict) or data.get("kind") != EDIT_KIND:
        raise Bad("the text is not a file of edits from a journey map's page (kind «%s»)" % EDIT_KIND)
    if data.get("version") != EDIT_VERSION:
        raise Bad("the file of edits is version %r — this plugin reads version %d" % (data.get("version"), EDIT_VERSION))
    if not isinstance(data.get("maps"), dict):
        raise Bad("the file of edits holds no maps")
    return data


SHARED_MAX_DOCS = 5000


def read_shared(path):
    """The page's shared edits (since v4.12.0, the user's decision of 2026-11-25): a folder of the artifact's `edits`
    documents, one JSON file each, as the host's database tool saves them. Another person's input: each document is read
    on its own, a file too large, unreadable or not an object skipped. Returns [(doc id, body)]."""
    docs = []
    names = sorted(x for x in os.listdir(path) if x.endswith(".json"))[:SHARED_MAX_DOCS]
    for fn in names:
        fp = os.path.join(path, fn)
        try:
            if os.path.getsize(fp) > EDIT_MAX_BYTES:
                continue
            with open(fp, encoding="utf-8") as fh:
                body = json.load(fh)
        except (OSError, ValueError, UnicodeDecodeError):
            continue
        if isinstance(body, dict):
            # the host's database tool spells an id's "~" as "@" in the file name; the page's ids never hold an "@" (docId)
            docs.append((unicodedata.normalize("NFC", fn[:-5]).replace("@", "~"), body))
    return docs


def shared_edits(docs, sigs):
    """The shared documents as a file of edits (§9): a row's document becomes its ops, an added row's an `add`; a document
    made on an older version of its map (its digest) or of an unknown map is named, never read. `sigs`: {name_key: (name,
    digest)}. Returns (data, docs by row key and by add, skipped)."""
    maps, rows, skipped, n = {}, {}, [], 0
    for did, b in docs:
        m = _s(b.get("map")) or ""
        hit = sigs.get(name_key(m))
        if hit is None:
            skipped.append({"why": "unknown_map", "map": nt.safe(m), "row": None, "doc": nt.safe(did),
                            "detail": "no map of this page is named so — the document is not read"})
            continue
        real, digest = hit
        if b.get("digest") != digest:
            skipped.append({"why": "stale", "map": nt.safe(real), "row": nt.safe(str(b.get("row"))) if b.get("row") else None,
                            "doc": nt.safe(did), "detail": "made on an older version of the map — edit its fresh page again"})
            continue
        ops = maps.setdefault(real, {"digest": digest, "edits": []})["edits"]
        if b.get("kind") == "row" and isinstance(b.get("edit"), dict) and _s(b.get("row")):
            r, e = _s(b.get("row")), b["edit"]
            rows.setdefault((real, r), []).append(did)
            if e.get("remove") is True:
                ops.append({"op": "remove", "row": r})
                continue
            for k in ("text", "parent", "code"):
                if k in e:
                    ops.append({"op": k, "row": r, k: e[k]})
            if "stage" in e or "lane" in e:
                ops.append({"op": "move", "row": r, "stage": e.get("stage"), "lane": e.get("lane")})
            if "target" in e:
                ops.append({"op": "target", "row": r, "target": e["target"] is True})
        elif b.get("kind") == "add" and isinstance(b.get("add"), dict):
            n += 1
            a = b["add"]
            ops.append({"op": "add", "id": "p%d" % n, "stage": a.get("stage"), "lane": a.get("lane"), "text": a.get("text"),
                        "parent": a.get("parent"), "code": a.get("code"), "target": a.get("target") is True, "doc": did})
        else:
            skipped.append({"why": "bad_edit", "map": nt.safe(real), "row": None, "doc": nt.safe(did),
                            "detail": "a document that is no row's edit and no added row"})
    return {"kind": EDIT_KIND, "version": EDIT_VERSION, "maps": maps}, rows, skipped


def _s(v):
    """A value of the file as a short string, or None when it is not one (another person's input)."""
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, (int, float)):
        v = str(v)
    if not isinstance(v, str) or len(v) > EDIT_MAX_TEXT:
        return None
    return unicodedata.normalize("NFC", v)


def page_diff(note, name, nest, data, lang):
    """The page's edits as a diff the board's take reads (§12): one element per row the page changed (`p<n>`), its entries
    in the categories of board-diff plus the links of v4.12.0 (relinked, recoded, retargeted), each `via: page`; a child
    map's rows and cells keyed as on a tree board (`<child>#<id>`, `<child> · <stage>`), so `board-take --note <child>`
    takes them into the child's own note. Texts page-safe, as a board's are. Returns (diff, skipped)."""
    maps = {name_key(name): (name, note, "")}
    for k in (tree_blocks(nest) if nest else []):
        maps[name_key(k["note"])] = (k["note"], nest["maps"][k["note"]], k["note"])
    out = {k: [] for k in DIFF_CATEGORIES}
    skipped, seq, seen = [], [0], set()

    def skip(why, mp, detail, row=None):
        skipped.append({"why": why, "map": nt.safe(str(mp)), "row": nt.safe(str(row)) if row is not None else None, "detail": detail})

    for mname in sorted(data["maps"], key=lambda x: (name_key(x) != name_key(name), str(x))):
        block = data["maps"][mname]
        hit = maps.get(name_key(str(mname)))
        if hit is None:
            skip("unknown_map", mname, "no map of this page is named so — its edits are not read")
            continue
        real, n, pre = hit
        if sum(1 for x in data["maps"] if name_key(str(x)) == name_key(str(mname))) > 1:   # one map named twice: neither read
            if name_key(str(mname)) not in seen:
                skip("bad_edit", real, "the map is named twice in the file — none of its edits is read")
            seen.add(name_key(str(mname)))
            continue
        if not isinstance(block, dict) or not isinstance(block.get("edits"), list):
            skip("bad_edit", real, "the map's entry holds no list of edits")
            continue
        if block.get("digest") != table_sig(n)["table"]:
            skip("stale", real, "the page was made from an older version of the map — edit its fresh page again")
            continue
        declared = [st["id"] for st in n["stages"]]
        rows = {r["id"]: r for r in n["rows"] if not r["gap"] and r["id"] and page_worthy(r, declared)}   # the page's rows only
        el = {}

        def K(rid):
            return ("%s#%s" % (pre, rid)) if pre and rid else rid

        def S(st):
            return ("%s · %s" % (pre, st)) if pre and st else st

        def elem(rid):
            if rid not in el:
                seq[0] += 1
                el[rid] = "p%d" % seq[0]
            return el[rid]

        def cell(st, ln):
            return cell_title(S(st), ln, lang) if st in declared and ln in LANE_IDS else ""
        for e in block["edits"]:
            op = e.get("op") if isinstance(e, dict) else None
            if op not in EDIT_OPS:
                skip("bad_edit", real, "an edit whose op is not one of %s" % ", ".join(EDIT_OPS))
                continue
            if op == "add":
                st, ln, text = _s(e.get("stage")), _s(e.get("lane")), _s(e.get("text"))
                if not st or not ln or not text or not text.strip():
                    skip("bad_edit", real, "an added row without its cell or text")
                    continue
                seq[0] += 1
                ent = {"id": "p%d" % seq[0], "kind": "sticky", "text": nt.safe(text), "cell": cell(st, ln),
                       "stage": S(st) if st in declared else None, "lane": lane_of(ln), "via": "page"}
                par, code = _s(e.get("parent")) or "", _s(e.get("code")) or ""
                if par:
                    ent["parent"] = K(nt.safe(par))
                if code:
                    ent["code"] = nt.safe(code)
                if e.get("target") is True:
                    ent["target"] = True
                if _s(e.get("doc")):
                    ent["doc"] = nt.safe(_s(e.get("doc")))
                out["added"].append(ent)
                continue
            rid = _s(e.get("row"))
            r = rows.get(rid) if rid else None
            if r is None:
                skip("unknown_row", real, "the page shows no row %s of the map" % nt.safe(str(rid)), rid)
                continue
            mid, base = elem(rid), {"row": K(rid), "via": "page"}
            hc = _is_hc(r)
            safe_now = nt.safe(r["text"])
            if op == "text":
                v = _s(e.get("text"))
                if v is None or _norm(nt.safe(v)) == _norm(safe_now):
                    continue
                ent = dict(base, id=mid, last=safe_now, now=nt.safe(v), **_cell_fields("cell", (S(r["stage"]), r["lane"]),
                                                                                       cell(r["stage"], r["lane"])))
                out["hc_edits" if hc else "changed"].append(dict(ent, change="text") if hc else dict(ent, team=False))
            elif op == "move":
                st, ln = _s(e.get("stage")) or r["stage"], lane_of(_s(e.get("lane")) or r["lane"])
                if (st, ln) == (r["stage"], r["lane"]):
                    continue
                to = (S(st), ln) if st in declared and ln else None
                ent = dict(base, id=mid, text=safe_now, **_cell_fields("from", (S(r["stage"]), r["lane"]), cell(r["stage"], r["lane"])))
                ent.update(_cell_fields("to", to, cell(st, ln) if to else ""))
                out["hc_edits" if hc else "moved"].append(dict(ent, change="moved") if hc else dict(ent, team=False))
            elif op == "remove":
                ent = dict(base, id=mid, text=safe_now, cell=cell(r["stage"], r["lane"]))
                out["hc_edits" if hc else "removed"].append(dict(ent, change="removed") if hc else ent)
            else:
                field, cat = {"parent": ("parent", "relinked"), "code": ("code", "recoded"), "target": ("target", "retargeted")}[op]
                if op == "target":
                    v, last = e.get("target") is True, r["target"].strip().lower() in YES
                else:
                    v = _s(e.get(field))
                    if v is None:
                        skip("bad_edit", real, "an edit of %s without its value" % field, rid)
                        continue
                    v, last = _norm(nt.safe(v)), _norm(nt.safe(r[field]))
                if v == last:
                    continue
                if _locked(r):
                    skip("locked", real, "row %s (%s) — its links never change from the page (R25)" % (rid, r["lane"]), rid)
                    continue
                if op == "parent":
                    v, last = K(v) if v else "", K(last) if last else ""
                out[cat].append(dict(base, id=mid, **{field + "_last": last, field + "_now": v}))
    out["counts"] = {k: len(out[k]) for k in COUNTED}
    return out, skipped


def cmd_page_diff(args):
    note = load(args.note)
    name = unicodedata.normalize("NFC", os.path.splitext(os.path.basename(args.note))[0])
    lang = args.lang or note["lang"]
    nest = page_nest(note, args.map, args.dir, lang)
    nested = nest is not None and bool(nest["tree"]["children"])
    shared, pre_skipped = None, []
    if os.path.isdir(args.edits):                   # the shared edits of a published page (§9): the artifact's documents
        sigs = {name_key(name): (name, table_sig(note)["table"])}
        for k in (tree_blocks(nest) if nested else []):
            sigs[name_key(k["note"])] = (k["note"], table_sig(nest["maps"][k["note"]])["table"])
        data, shared, pre_skipped = shared_edits(read_shared(args.edits), sigs)
    else:
        data = read_edits(args.edits)
    root = _s(data.get("root")) or ""
    if root and name_key(root) != name_key(name):
        raise Bad("the edits are of the page of %s — run page-diff with --note %s.md" % (nt.safe(root), nt.safe(root)))
    prod = _s(data.get("product"))
    if prod is not None and _product_key(prod) != _product_key(nt.safe(note["product"])):
        raise Bad("the edits are of another product's map — never taken into this one")
    diff, skipped = page_diff(note, name, nest if nested else None, data, lang)
    skipped = pre_skipped + skipped
    made = _s(data.get("made"))
    payload = dict(ok=True, state="diff", surface="page", made=made if made and day(made) else None, **diff)
    payload.update(note=table_sig(note), skipped=skipped, map=nt.safe(name))
    if nested:
        payload["tree"] = tree_sigs(nest)            # a take into a child checks its own note (§14)
    if shared is not None:                           # which documents each element came from: cleared after a written take
        docs = {}
        for cat in DIFF_CATEGORIES:
            for e in diff.get(cat, []):
                if e.get("doc"):
                    docs.setdefault(e["id"], []).append(e["doc"])
                elif e.get("row"):
                    mp, _, rid = e["row"].rpartition("#")
                    for did in shared.get((mp or name, rid), []):
                        if did not in docs.setdefault(e["id"], []):
                            docs[e["id"]].append(nt.safe(did))
        payload["docs"] = docs
    if args.out:
        try:
            payload["out"] = _write_json(args.out, payload)
        except OSError as e:
            result(ok=False, error="the diff cannot be written: %s" % (e.strerror or type(e).__name__))
            return 1
    result(**payload)
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
           team_source=TEAM_SOURCE, page_source=PAGE_SOURCE, edit_ops=list(EDIT_OPS), edit_kind=EDIT_KIND, nest_fields=list(NEST_FIELDS), nest_findings=list(NEST_FINDINGS), orphan_why=list(ORPHAN_WHY),
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
    p.add_argument("--with-children", action="store_true", help="a tree board: each child map's block below the map's grid (§14)")
    p.add_argument("--map", action="extend", nargs="+", default=[], help="a journey map that may nest (default: the note's folder)")
    p.add_argument("--dir", action="extend", nargs="+", default=[], help="a folder: every .md directly inside it")
    p = sub.add_parser("board-state")
    p.add_argument("--read", required=True, nargs="+", help="the board read back: a Miro SVG, or the host board's element list")
    p.add_argument("--note", required=True)
    p.add_argument("--surface", required=True, choices=bs.SURFACES)
    p.add_argument("--last", help="the previous state: a row the board no longer shows keeps its sticky as an orphan")
    p.add_argument("--out", required=True, help="~/.grow-pm/journey-maps/<product>/journey-<slug>.<surface>.board.json")
    p.add_argument("--with-children", action="store_true", help="a tree board: the child maps' blocks too (§14)")
    p.add_argument("--map", action="extend", nargs="+", default=[], help="a journey map that may nest (default: the note's folder)")
    p.add_argument("--dir", action="extend", nargs="+", default=[], help="a folder: every .md directly inside it")
    p = sub.add_parser("board-diff")
    p.add_argument("--last", help="the board's state (board-state JSON) or an older read")
    p.add_argument("--now", nargs="+", help="the board read back now: by the state's ids, then over its area")
    p.add_argument("--note", required=True)
    p.add_argument("--surface", choices=bs.SURFACES, help="default: the state's")
    p.add_argument("--out", help="keep the diff for board-take")
    p.add_argument("--with-children", action="store_true", help="a tree board (default: as its state says, §14)")
    p.add_argument("--map", action="extend", nargs="+", default=[], help="a journey map that may nest (default: the note's folder)")
    p.add_argument("--dir", action="extend", nargs="+", default=[], help="a folder: every .md directly inside it")
    p = sub.add_parser("board-take")
    p.add_argument("--note", required=True)
    p.add_argument("--diff", required=True, action="extend", nargs="+",
                   help="the board-diff result (--out, or its JOURNEY_RESULT line) — one per board: its own and a tree board it is a child on")
    p.add_argument("--take", nargs="*", default=[], help="element ids (or row ids) the PM takes")
    p.add_argument("--class", dest="klass", action="extend", nargs="+", help="<element id>=<class> the PM picked in the preview")
    p.add_argument("--parent", action="extend", nargs="+", help="<element id>=<row id>")
    p.add_argument("--drop", nargs="*", default=[], help="row ids gone from the board that leave the note")
    p.add_argument("--date", help="YYYY-MM-DD of the team's board (default: today, UTC)")
    p.add_argument("--dry-run", action="store_true", help="the preview: nothing written")
    p = sub.add_parser("page-diff")
    p.add_argument("--note", required=True, help="the map whose page the edits were made on — its root on a tree page")
    p.add_argument("--edits", required=True, help="the file of edits the page saved, a text file holding the copied edits, or a folder of the published page's shared edits (one JSON document each)")
    p.add_argument("--out", help="keep the diff for board-take")
    p.add_argument("--lang", choices=sorted(LABELS), help="default: the language of the note's table headers")
    p.add_argument("--map", action="extend", nargs="+", default=[], help="a journey map that may nest (default: the note's folder)")
    p.add_argument("--dir", action="extend", nargs="+", default=[], help="a folder: every .md directly inside it")
    p = sub.add_parser("nest")
    p.add_argument("--note", required=True, help="the map whose subtree is shown — a root, or a child at its own level")
    p.add_argument("--map", action="extend", nargs="+", default=[], help="a journey map that may nest — ctx search --type cjm-journey's files")
    p.add_argument("--dir", action="extend", nargs="+", default=[], help="a folder: every .md directly inside it")
    p.add_argument("--lang", choices=sorted(LABELS), help="default: the language of the note's table headers")
    p.add_argument("--json", action="store_true", help="the result line alone, no tree for the chat")
    p = sub.add_parser("app-data")
    p.add_argument("--note", required=True)
    p.add_argument("--out", required=True, help="the section's data: app_shell.py snapshot --section map.<slug>:<product>:FILE")
    p.add_argument("--lang", choices=sorted(LABELS), help="default: the language of the note's table headers")
    p.add_argument("--map", action="extend", nargs="+", default=[], help="a journey map that may nest (default: the note's folder)")
    p.add_argument("--dir", action="extend", nargs="+", default=[], help="a folder: every .md directly inside it")
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
          "board-diff": cmd_board_diff, "board-take": cmd_board_take, "page-diff": cmd_page_diff, "nest": cmd_nest,
          "app-data": cmd_app_data, "schema": cmd_schema}.get(args.cmd)
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
