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
A product is compared as `ctx search --type` compares it (ctx_search.same_product); a note the search marks
sensitive (ctx_index.note_meta) is never read into the portfolio. Every command ends with one
`PORTFOLIO_RESULT {json}` line. Stdlib only (Python 3.9). Exit 0; 2 for a wrong argument; 1 when the page cannot be
written.
"""
import argparse, datetime, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ctx_index as ci  # noqa: E402  — is_dataless: a file iCloud has not downloaded is never opened
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
CJM_FIELDS = ("title", "funnel", "stages_declared", "stages", "snapshot")     # the result's keys of a hand CJM
CJM_FINDINGS = ("stage_count", "no_snapshot")
SKIPS = (("not_cjm_map", "не CJM-карта — немає воронки чи стадій"), ("other_product", "нотатка іншого продукту"),
         ("wrong_type", "не карта шляху й не CJM-нотатка"), ("sensitive", "чутлива нотатка — лише для People-контуру"),
         ("unreadable", "нотатка не читається"))
EN_SKIPS = {"not_cjm_map": "no CJM map — no funnel or stages", "other_product": "another product's note",
            "wrong_type": "neither a journey map nor a CJM note", "sensitive": "a sensitive note — the People contour's only",
            "unreadable": "the note does not read"}
JOURNEY_TYPE, CJM_TYPE = "cjm-journey", "cjm"
STAGE_HEAD = re.compile(r"^##[ \t]+([A-Za-zА-ЯІЇЄҐа-яіїєґ]{0,4}\d{1,3}[A-Za-z]?)[ \t]+[—–][ \t]+(.+?)[ \t#]*$")
                                            # `## <ID> — <name>` (R32), the ID a short code with a digit: B1, S2, s3a —
                                            # never a year («## 2026 — …»)
METRIC_HEAD = ("метрика", "metric")         # the first header cell of a stage's metrics table
FENCE = re.compile(r"^[ \t]{0,3}(`{3,}|~{3,})(.*)$")
COMMENT = re.compile(r"<!--.*?-->|%%.*?%%", re.S)    # an HTML or Obsidian comment: nothing in it is read
LABELS = {
    "uk": {"title": "Портфель шляхів", "generated": "Згенеровано", "maps": "Карти шляху", "attention": "Потребують уваги",
           "none": "Карт шляху немає", "stale": "застаріло", "critical": "критичних %d", "cjm": "Ручні CJM-нотатки",
           "mark": "ручна CJM — частково: без джерел, класів і здоров'я", "funnel": "воронка", "snapshot": "знімок",
           "stages_of": "%d з %d оголошених", "metrics": "метрик", "no_product": "продукт не вказано",
           "skipped": "Пропущено", "other": "Іншого продукту — не показано: %d", "empty": "без доказів",
           "icloud": "файл не завантажено з iCloud — відкрий його в Obsidian",
           "icloud_n": "файлів у теках не завантажено з iCloud: %d — відкрий теку в Obsidian",
           "no_outcome": "без метрики результату", "no_point": "—", "kids": "діти: %d · уваги потребують %d",
           "head": "Портфель шляхів: %s · %s · карт %d · "
           "потребують уваги %d · ручних CJM %d · пропущено %d", "head_other": " · іншого продукту %d", "cjm_cols": ("CJM", "воронка",
           "етапи", "метрик на етап", "знімок", "знахідки"), "missing": "теки ще немає: %s"},
    "en": {"title": "Journey portfolio", "generated": "Generated", "maps": "Journey maps", "attention": "Needs attention",
           "none": "No journey maps", "stale": "stale", "critical": "critical %d", "cjm": "Hand CJM notes",
           "mark": "hand CJM — partly: no sources, classes or health", "funnel": "funnel", "snapshot": "snapshot",
           "stages_of": "%d of %d declared", "metrics": "metrics", "no_product": "no product named",
           "skipped": "Skipped", "other": "Another product — not shown: %d", "empty": "no evidence",
           "icloud": "the file is not downloaded from iCloud — open it in Obsidian",
           "icloud_n": "files in the folders not downloaded from iCloud: %d — open the folder in Obsidian",
           "no_outcome": "no outcome metric", "no_point": "—", "kids": "children: %d · needing attention %d",
           "head": "Journey portfolio: %s · %s · maps %d · "
           "needing attention %d · hand CJMs %d · skipped %d", "head_other": " · another product %d", "cjm_cols": ("CJM", "funnel",
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
    """Is a note of the product asked — compared as `ctx search --type` compares it (ctx_search.same_product: one
    whole key, never a part of a name); a note that names no product stays."""
    return cs_.same_product(note_product, asked)


def _labels(lang):
    return LABELS.get(lang, LABELS["en"])


def _attention_label(code, lang):
    return dict(ATTENTION)[code] if lang == "uk" else EN_ATTENTION[code]


def _skip_label(code, lang):
    return dict(SKIPS)[code] if lang == "uk" else EN_SKIPS[code]


# ------------------------------------------------------------------ a journey map's row
def status_of(text):
    """The health-check status a refreshed anomaly row ends with — `— <label>` by journey_map's own labels (REFRESH), in
    either language; None for any other ending. A word inside the text is no status. Since v4.10.0 journey_map's
    `hc_status` — one reading for the portfolio and a child's roll-up (§14)."""
    return jm.hc_status(text)


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
    out = []
    for e in entries:                                # each value the record's own words only — anything else is «?»
        surface, kind, level = str(e.get("surface") or ""), str(e.get("kind") or ""), str(e.get("level") or "")
        audience = str(e.get("audience") or "")
        place = {"surface": surface if surface in pub.SURFACES or pub.SLUG.match(surface) else "?",
                 "kind": kind if kind in pub.KINDS else "?"}
        if level:
            place["level"] = level if level in pub.LEVELS else "?"
        place["version"] = e.get("version")
        if audience:
            place["audience"] = audience if audience in pub.AUDIENCES or re.match(r"^space:[A-Z][A-Z0-9_]{0,31}$", audience) else "?"
        out.append(place)
    return out


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
            cls = r["class"].strip().lower()
            k = cls if cls in jm.CLASSES else "?" if cls else "—"     # a class's own word, never the cell's text
            pains[k] = pains.get(k, 0) + 1
    an = {"total": 0, "critical": 0, "warning": 0, "positive": 0, "unrated": 0}
    for r in live:
        if r["lane"] == "anomaly":
            an["total"] += 1
            st = status_of(r["text"]) if jm._is_hc(r) else None
            an[st or "unrated"] += 1
    gaps = {"empty_stage": [plain(f["stage"]) or "?" for f in found if f["finding"] == "empty_stage"],
            "no_outcome": [plain(f["stage"]) or "?" for f in found if f["finding"] == "no_outcome"]}
    reviewed = note["reviewed"] if jm.day(note["reviewed"]) else ""
    by = {}
    for c in codes:
        by[c] = by.get(c, 0) + 1
    attention = []
    if prev and prev["score"] - last["score"] > DROP:
        attention.append({"reason": "health_drop", "detail": "%s → %s" % (prev["score"], last["score"])})
    if "stale_review" in codes:
        attention.append({"reason": "stale_review", "detail": reviewed})
    if "no_owner" in codes:
        attention.append({"reason": "no_owner", "detail": ""})
    if an["critical"]:
        attention.append({"reason": "critical_anomaly", "detail": str(an["critical"])})
    if gaps["empty_stage"]:
        attention.append({"reason": "empty_stage", "detail": ", ".join(gaps["empty_stage"])})
    name = os.path.basename(note["path"])
    return {"journey": plain(note["journey"] or note["title"] or os.path.splitext(name)[0]), "note": name,
            "path": note["path"], "product": plain(note["product"]) if cs_.product_key(note["product"]) else "",
            "product_missing": not cs_.product_key(note["product"]),
            "owner": plain(note["owner"]), "stages": len(note["stages"]), "health": health,
            "reviewed": reviewed, "stale_review": "stale_review" in codes,
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
    stages, cur, fence, run = [], None, "", []

    def close():
        if cur is not None and cur["metrics"] is None and run:
            cur["metrics"] = _metric_rows(run)
    for line in COMMENT.sub("", body).split("\n") + [""]:
        f = FENCE.match(line)
        if f and (not fence or (f.group(1)[0] == fence[0] and len(f.group(1)) >= len(fence) and not f.group(2).strip())):
            close()                                   # a fence ends a table run: two tables never join into one
            run = []
            fence = "" if fence else f.group(1)       # closed only by the same character, at least as long
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
    try:
        declared = int(declared) if declared.isascii() and declared.isdigit() else None
    except ValueError:
        declared = None
    snapshot = nt.fm_scalar(fm, "snapshot")
    snapshot = snapshot if jm.day(snapshot) else ""
    findings = []
    if declared is not None and declared != len(stages):
        findings.append({"finding": "stage_count", "detail": "stages: %d, headings: %d" % (declared, len(stages))})
    if not snapshot:
        findings.append({"finding": "no_snapshot", "detail": "no snapshot date (YYYY-MM-DD) in the frontmatter"})
    product = nt.fm_scalar(fm, "product")
    product = product if cs_.product_key(product) else ""      # `null`, `~`: no product
    name = os.path.basename(path)
    return {"title": plain(nt.fm_scalar(fm, "title") or nt.fm_scalar(fm, "name") or os.path.splitext(name)[0]),
            "note": name, "path": path, "funnel": plain(funnel), "stages_declared": declared, "stages": stages,
            "snapshot": snapshot, "product": plain(product), "product_missing": not product, "findings": findings,
            "mark": _labels(lang)["mark"]}


# ------------------------------------------------------------------ the portfolio
def collect(paths, dirs, product, today, snapshots, lang):
    """The portfolio of the notes named and the `.md` notes directly inside each folder: {maps, cjm, skipped,
    other_products, ignored, missing_dirs}. A note is read once; its `type` decides what it is. `snapshots` — the
    health-check folder: each map's newest snapshot is its own product's, as `journey_map.py check` reads it."""
    newest_of = {}

    def newest(prod):
        if not snapshots:
            return None
        if prod not in newest_of:
            newest_of[prod] = jm.snapshots(snapshots, prod)[2]
        return newest_of[prod]
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
    seen, maps, cjms, skipped, other, ignored, undownloaded = set(), [], [], [], 0, 0, 0
    notes = {}                                       # the journey maps by name — their nesting (§14), the first of a name
    for path, named in items:
        try:
            st = os.stat(path)
            ident = (st.st_dev, st.st_ino)            # one file by two spellings (a case-insensitive disk) is one
        except OSError:
            ident = os.path.realpath(path)
        if ident in seen:
            continue
        seen.add(ident)
        name = os.path.basename(path)
        if os.path.isfile(path) and ci.is_dataless(path):    # never opened: opening it would start a download
            if named:
                skipped.append({"note": name, "reason": "unreadable", "detail": _labels(lang)["icloud"]})
            else:
                undownloaded += 1                     # a folder's file is counted — it may be anyone's, never named
            continue
        try:
            text, fm, body = nt.read_note(path)
        except Bad as e:
            if str(e) == "the note has no frontmatter" and _opens_frontmatter(path):
                skipped.append({"note": name, "reason": "unreadable", "detail": "the frontmatter is not closed"})
            elif not named and str(e) == "the note has no frontmatter":
                ignored += 1                          # a folder's plain markdown is no note of the portfolio
            else:
                skipped.append({"note": name, "reason": "unreadable", "detail": str(e)})
            continue
        kind = nt.fm_scalar(fm, "type").strip().lower()
        if kind not in (JOURNEY_TYPE, CJM_TYPE):
            if not named:
                ignored += 1
            elif not _same_product(nt.fm_scalar(fm, "product"), product):
                other += 1                            # another product's note is never named, whatever its type
            else:
                skipped.append({"note": name, "reason": "wrong_type", "detail": "type: %s" % (plain(kind) or "—")})
            continue
        if not _same_product(nt.fm_scalar(fm, "product"), product):
            other += 1
            continue
        if ci.note_meta(path.replace(os.sep, "/"), text)["sensitive"]:     # the search's own mark (data-policy.md)
            skipped.append({"note": name, "reason": "sensitive", "detail": _skip_label("sensitive", lang)})
            continue
        if kind == JOURNEY_TYPE:
            try:
                note = jm.load(path)
            except Bad as e:
                skipped.append({"note": name, "reason": "unreadable", "detail": str(e)})
                continue
            maps.append(map_row(note, today, newest(note["product"])))     # its own product's, as `check` reads it
            notes.setdefault(os.path.splitext(name)[0], note)
            continue
        c = read_cjm(path, fm, body, lang)
        if c is None:
            skipped.append({"note": name, "reason": "not_cjm_map", "detail": _skip_label("not_cjm_map", lang)})
            continue
        cjms.append(c)

    def key(m):
        return (m["journey"].casefold(), m["note"])
    maps = tree_order(maps, notes, key)
    cjms.sort(key=lambda c: (c["title"].casefold(), c["note"]))
    return {"maps": maps, "cjm": cjms, "skipped": skipped, "other_products": other, "ignored": ignored,
            "undownloaded": undownloaded, "missing_dirs": missing}


def tree_order(maps, notes, key):
    """The maps in tree order (§13, §14, C10): the roots — maps hanging on no map of the list — the ones that need
    attention first, as before; under each root its children in the parent's stage order, every level deeper. Each row
    gets `nest`: its parent, its level, how many maps hang under it at any depth and how many of them need attention, and
    its finding of the nesting. A map's attention and health stay its own."""
    forest = jm.nest_forest(notes)
    par, kids, level = forest["parent"], forest["children"], forest["level"]
    found = {}
    for f in forest["findings"]:
        for n in f.get("maps") or [f["note"]]:
            found.setdefault(n, f["finding"])
    rows = {}
    for m in maps:
        n = os.path.splitext(m["note"])[0]
        if n in notes and notes[n]["path"] == m["path"]:
            rows[n] = m
    for m in maps:
        n = os.path.splitext(m["note"])[0]
        m["nest"] = {"parent": par.get(n, "") if rows.get(n) is m else "", "level": level.get(n, 1) if rows.get(n) is m else 1,
                     "children": 0, "children_attention": 0, "finding": found.get(n, "") if rows.get(n) is m else ""}

    def under(n, seen):
        out = []
        for c in kids.get(n, []):
            if c in rows and c not in seen:
                seen.add(c)
                out.append(rows[c])
                out += under(c, seen)
        return out
    for n, m in rows.items():
        sub = under(n, {n})
        m["nest"]["children"], m["nest"]["children_attention"] = len(sub), sum(1 for x in sub if x["attention"])
    roots = [m for m in maps if not m["nest"]["parent"]]
    roots = sorted((m for m in roots if m["attention"]), key=lambda m: (-len(m["attention"]), key(m))) + \
        sorted((m for m in roots if not m["attention"]), key=key)
    out = []
    for m in roots:
        out.append(m)
        n = os.path.splitext(m["note"])[0]
        if rows.get(n) is m:
            out += under(n, {n})
    return out


def _opens_frontmatter(path):
    """Does the file open a frontmatter (`---` on its first line, after a BOM) that is never closed?"""
    try:
        with open(path, encoding="utf-8-sig", newline="") as fh:
            return fh.readline().rstrip("\r\n") == "---"
    except (OSError, UnicodeDecodeError):
        return False


def head(p, product, today, L):
    c = counts(p)
    return L["head"] % (product, today, c["maps"], c["attention"], c["cjm"], c["skipped"]) + \
        (L["head_other"] % c["other_products"] if c["other_products"] else "")


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
    nest = m.get("nest") or {}
    lv = nest.get("level") or 1
    return {"journey": ("↳" * (lv - 1) + " " if lv > 1 else "") + m["journey"]
            + (" (%s)" % L["no_product"] if m["product_missing"] else "")
            + (" (%s)" % (L["kids"] % (nest["children"], nest["children_attention"])) if nest.get("children") else "")
            + (" (⚠️ %s)" % nest["finding"] if nest.get("finding") else ""),
            "owner": m["owner"] or "⚠️", "stages": str(m["stages"]),
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
    out = [head(p, product, today, L), ""]
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
    if p.get("undownloaded"):
        out.append(L["icloud_n"] % p["undownloaded"])
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


CSS_TREE = """
tr.d1 th.j{padding-left:22px}tr.d2 th.j{padding-left:38px}tr.d3 th.j{padding-left:54px}"""


def _spark(points):
    """journey_map's sparkline, a smaller copy for the table's cell — each point's date and score."""
    return jm.sparkline(points).replace('width="260" height="56"', 'width="130" height="32"', 1)


def render_html(p, product, today, lang):
    L = _labels(lang)
    c = counts(p)
    heads = [(k, uk if lang == "uk" else EN_COLUMNS[k]) for k, uk in COLUMNS]
    out = ["<!doctype html>", '<html lang="%s"><head><meta charset="utf-8">' % esc(lang),
           '<meta name="viewport" content="width=device-width,initial-scale=1">',
           "<title>%s — %s</title><style>%s</style></head><body>" % (esc(L["title"]), shown(product), CSS + (CSS_TREE if any(
               (m.get("nest") or {}).get("level", 1) > 1 for m in p["maps"]) else "")),
           "<h1>%s: %s</h1>" % (esc(L["title"]), shown(product)),
           '<p class="meta">%s: %s</p>' % (esc(L["generated"]), esc(today)),
           '<p class="meta">%s</p>' % esc(head(p, product, today, L)),
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
            lv = (m.get("nest") or {}).get("level") or 1
            cls = " ".join(c for c in ("d%d" % min(lv - 1, 3) if lv > 1 else "", "attn" if m["attention"] else "") if c)
            out.append('<tr%s>%s</tr>' % (' class="%s"' % cls if cls else "", "".join(tds)))
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


# ------------------------------------------------------------------ check 30
def _rows(sec, header_re):
    return [(nt.tick(r[0]) or "?", nt.tick(r[1]) if len(r) > 1 else None) for r in nt.table_after(sec, header_re)]


def check_protocol(root):
    """Errors for validate-consistency.sh check 30 (v4.9.0) — journey-protocol.md §13 is this script's: its commands,
    the map's columns, the attention reasons and the drop threshold, the hand CJM's fields, findings and mark, the
    skips, and how the notes are found; artifact-publishing.md §5 has the portfolio's key, native-surfaces.md §2 its
    row, cjm-reports.md re-renders the page on schedule, context-protocol.md documents `search --type`, cjm-research
    has its step J7; this script imports journey_map.py and copies none of it."""
    errs, texts = [], {}
    for rel in ("references/journey-protocol.md", "references/artifact-publishing.md", "references/native-surfaces.md",
                "references/context-protocol.md", "skills/cjm-research/references/cjm-reports.md",
                "skills/cjm-research/SKILL.md", "scripts/journey_portfolio.py"):
        try:
            with open(os.path.join(root, rel), encoding="utf-8") as fh:
                texts[rel] = fh.read()
        except OSError:
            errs.append("%s is missing" % rel)
    proto = texts.get("references/journey-protocol.md")
    if proto is not None:
        s13 = nt.section(proto, "13. The portfolio")
        if not s13:
            errs.append("journey-protocol.md has no §13 «The portfolio»")
        crow = nt.table_after(s13, r"\| Command \| What \|")
        cmds = [nt.cmd_name(r[0]) for r in crow]
        if cmds != list(COMMANDS):
            errs.append("journey-protocol.md §13: the commands %s ≠ journey_portfolio.py COMMANDS %s" % ("|".join(cmds), "|".join(COMMANDS)))
        have = flags_of()
        for r in crow:
            name = nt.cmd_name(r[0])
            got = sorted(set(re.findall(r"--[a-z][a-z-]*", r[0])))
            if name in have and got != have[name]:
                errs.append("journey-protocol.md §13: `%s` takes %s ≠ journey_portfolio.py %s" % (name, " ".join(got) or "—", " ".join(have[name]) or "—"))
        words = " or ".join("«%s»" % w.capitalize() for w in METRIC_HEAD)
        if "first header cell is %s" % words not in s13:
            errs.append("journey-protocol.md §13 does not say the metric table's first header cell is %s (journey_portfolio.py METRIC_HEAD)" % words)
        if "under its own key `cjm-research/<product>/portfolio`" not in s13 or "**without `--note`**" not in s13:
            errs.append("journey-protocol.md §13: the dashboard is not under its own key `cjm-research/<product>/portfolio`, recorded **without `--note`**")
        for what, header, want in (("the columns", r"\| Column \| Ukrainian header \| What \|", list(COLUMNS)),
                                   ("the attention reasons", r"\| Reason \| Ukrainian label \| When \|", list(ATTENTION)),
                                   ("the skips", r"\| Skip \| Ukrainian line \| When \|", list(SKIPS))):
            got = _rows(s13, header)
            if got != want:
                errs.append("journey-protocol.md §13: %s %s ≠ journey_portfolio.py %s" % (
                    what, "|".join("%s/%s" % g for g in got) or "—", "|".join("%s/%s" % w for w in want)))
        for what, header, want in (("the hand CJM's fields", r"\| Field \| What \|", list(CJM_FIELDS)),
                                   ("the hand CJM's findings", r"\| Finding \| What \|", list(CJM_FINDINGS))):
            got = [g for g, _ in _rows(s13, header)]
            if got != want:
                errs.append("journey-protocol.md §13: %s %s ≠ journey_portfolio.py %s" % (what, "|".join(got) or "—", "|".join(want)))
        when = {nt.tick(r[0]): r[2] for r in nt.table_after(s13, r"\| Reason \| Ukrainian label \| When \|") if len(r) > 2}
        if "more than %d points below" % DROP not in when.get("health_drop", ""):
            errs.append("journey-protocol.md §13: health_drop does not say «more than %d points below» (journey_portfolio.py DROP)" % DROP)
        if "«%s»" % LABELS["uk"]["mark"] not in s13:
            errs.append("journey-protocol.md §13 does not name the hand CJM's mark «%s»" % LABELS["uk"]["mark"])
        if "ctx.py search --type %s --type %s" % (JOURNEY_TYPE, CJM_TYPE) not in s13:
            errs.append("journey-protocol.md §13 does not find the notes with `ctx.py search --type %s --type %s`" % (JOURNEY_TYPE, CJM_TYPE))
    skill = texts.get("skills/cjm-research/SKILL.md")
    if skill is not None and not re.search(r"^- \*\*J7\b(?=.*journey_portfolio\.py)(?=.*§13)", skill, re.M):
        errs.append("skills/cjm-research/SKILL.md has no step J7 that runs journey_portfolio.py and points to journey-protocol.md §13")
    ap = texts.get("references/artifact-publishing.md")
    if ap is not None and not re.search(r"^\|\s*`cjm-research`\s*\|.*`cjm-research/<product>/portfolio`", nt.section(ap, "5. Publish and record"), re.M):
        errs.append("artifact-publishing.md §5: the `cjm-research` key row has no `cjm-research/<product>/portfolio`")
    ns = texts.get("references/native-surfaces.md")
    if ns is not None and not re.search(r"^\| The journey portfolio \(`cjm-research` Step J7\b", nt.section(ns, "2. Routing"), re.M):
        errs.append("native-surfaces.md §2: no row «The journey portfolio (`cjm-research` Step J7…)»")
    rep = texts.get("skills/cjm-research/references/cjm-reports.md")
    if rep is not None and "journey_portfolio.py render-html" not in rep:
        errs.append("cjm-reports.md: the automated health-check does not re-render the portfolio (journey_portfolio.py render-html)")
    cp = texts.get("references/context-protocol.md")
    if cp is not None and not re.search(r"^\| `search --type TYPE", cp, re.M):
        errs.append("context-protocol.md §3: no row for `search --type TYPE` (the portfolio finds its notes with it)")
    src = texts.get("scripts/journey_portfolio.py")
    if src is not None:
        if not re.search(r"^import journey_map as jm\b", src, re.M):
            errs.append("journey_portfolio.py does not import journey_map — a journey note is read by journey_map.py, never copied")
        own = [n for n in ("load", "findings", "parse", "evidence", "page_worthy", "sparkline", "snapshots")
               if re.search(r"^def %s\(" % n, src, re.M)]
        if own:
            errs.append("journey_portfolio.py defines %s of its own — import them from journey_map.py" % ", ".join(own))
    return errs


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
    if any(not n.strip() for n in args.note) or any(not d.strip() for d in args.dir):
        raise Bad("an empty --note or --dir — a note ctx search lists without a file on disk is named, never passed")
    if args.snapshots:
        jm.snapshots(args.snapshots, args.product)    # a folder that does not read stops here (exit 2), never per map
    return collect(args.note, args.dir, args.product, today, args.snapshots, args.lang), today


def cmd_list(args):
    p, today = _portfolio(args)
    sys.stdout.write(chat_table(p, args.product, today.isoformat(), args.lang))
    result(ok=True, product=args.product, today=today.isoformat(), lang=args.lang, counts=counts(p), **p)
    return 0


def cmd_render(args):
    out = os.path.realpath(args.out)                 # a folder's notes are .md — the first test covers them
    if out.lower().endswith(".md") or out in {os.path.realpath(n) for n in args.note}:
        result(ok=False, error="--out would overwrite a note — the page is an .html file beside the notes, never a note")
        return 2
    p, today = _portfolio(args)
    page = render_html(p, args.product, today.isoformat(), args.lang)
    try:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)   # the first run: no maps' folder yet
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
           drop=DROP, cjm_fields=list(CJM_FIELDS), cjm_findings=list(CJM_FINDINGS), skips=[list(s) for s in SKIPS],
           errors=check_protocol(os.path.dirname(HERE)))
    return 0


def build_parser():
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
    return ap, sub


def flags_of():
    """{command: [its long options]} — what check 30 compares with §13's command table."""
    _, sub = build_parser()
    return {name: sorted(o for a in p._actions for o in a.option_strings if o.startswith("--") and o != "--help")
            for name, p in sub.choices.items()}


def main(argv=None):
    ap, _ = build_parser()
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
        result(ok=False, error="a command is needed: %s" % "|".join(COMMANDS))
        return 2
    try:
        return fn(args)
    except Bad as e:
        result(ok=False, error=str(e))
        return 2


if __name__ == "__main__":
    sys.exit(main())
