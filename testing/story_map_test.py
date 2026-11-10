#!/usr/bin/env python3
"""TC-map-4600 — scripts/story_map.py, the user story map (v4.6.0, references/story-map-protocol.md).

Fictional «Zorg» notes and boards (testing/fixtures/story-map/) are copied into a temp folder:
- parse: activities and steps in the order of their first row, cards ranked inside a step, the slices of the
  frontmatter, the layout of columns and bands, gap rows; English headers too; a CRLF note; a note without the table
  or without a required column, and a row with the wrong number of cells, are named, never a crash;
- check: the clean map has no finding, the map with errors raises each script finding of the protocol once;
- render-html: one self-contained page (no request, no link), every text escaped, a band per slice with its outcome,
  the note's name and the status source and date; Ukrainian and English labels;
- progress: the four canons and `unknown`, the % done, what is blocked, added / removed / moved against the baseline;
  a status that is not a canon is refused;
- baseline: only the `baseline` field changes, every other byte stays (LF and CRLF); another slice's entry is kept;
- board-diff: changed / moved / added / removed by data-miro-id, cards found by their text, the area to read back,
  `unknown` without a state, a board that does not parse refused;
- schema: check 26's check_protocol is clean on a sound tree and names each drift.
Mutations: a script whose baseline rewrites another field, one that skips escaping, and one that skips the skeleton
check are each caught by the same assertions. Stdlib only; run from the repo root:

  env -u GROW_PM_CONTEXT_PATH -u GROW_PM_PROVIDER_PATHS python3 testing/story_map_test.py
"""
import json, os, re, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "story_map.py")
FIX = os.path.join(ROOT, "testing", "fixtures", "story-map")

fails = 0


def check(name, cond, detail=""):
    global fails
    fails += not cond
    print(("✅" if cond else "❌"), name, ("" if cond else "-> " + str(detail)[:900]))


SAFE_HOME = tempfile.mkdtemp(prefix="story-map-home-")


def run(*args, script=SCRIPT):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GROW_PM_")}
    env["HOME"] = SAFE_HOME
    p = subprocess.run([sys.executable, script] + list(args), capture_output=True, text=True, env=env)
    res = {}
    for line in p.stdout.splitlines():
        if line.startswith("MAP_RESULT "):
            res = json.loads(line[len("MAP_RESULT "):])
    return p.returncode, p.stdout + p.stderr, res


def read(p):
    with open(p, "rb") as f:
        return f.read()


def write(p, data):
    with open(p, "wb") as f:
        f.write(data if isinstance(data, bytes) else data.encode("utf-8"))


def mutant(d, name, old, new):
    """A copy of the script (with its sibling modules) where `old` became `new`; None when `old` is not there."""
    src = open(SCRIPT, encoding="utf-8").read()
    if old not in src:
        return None
    mdir = os.path.join(d, "mut-" + name)
    os.makedirs(mdir)
    for f in os.listdir(os.path.dirname(SCRIPT)):
        if f.endswith(".py"):
            shutil.copy(os.path.join(os.path.dirname(SCRIPT), f), mdir)
    with open(os.path.join(mdir, "story_map.py"), "w", encoding="utf-8") as f:
        f.write(src.replace(old, new, 1))
    return os.path.join(mdir, "story_map.py")


d = tempfile.mkdtemp(prefix="story-map-test-")
try:
    for f in os.listdir(FIX):
        shutil.copy(os.path.join(FIX, f), d)
    note = os.path.join(d, "map-parcel-locker.md")
    bad = os.path.join(d, "map-findings.md")
    status = os.path.join(d, "status-zorg.json")

    # 1. parse
    rc, out, res = run("parse", "--note", note)
    check("1.1 parse exits 0 with a MAP_RESULT line", rc == 0 and res.get("ok") is True, out)
    acts = [a["name"] for a in res.get("activities", [])]
    check("1.2 activities in the order of their first row",
          acts == ["Обрати доставку", "Оплатити", "Відстежити", "Забрати"], acts)
    steps = [s for a in res.get("activities", []) for s in a["steps"]]
    check("1.3 eight steps, in order", len(steps) == 8 and steps[0] == "Побачити поштомат у кошику"
          and steps[-1] == "Повернути посилку", steps)
    cards = {c["id"]: c for c in res.get("cards", [])}
    check("1.4 eighteen cards", len(cards) == 18, len(cards))
    check("1.5 a card's rank is its row order inside its step",
          cards.get("c3", {}).get("rank") == 1 and cards.get("c4", {}).get("rank") == 2 and cards.get("c5", {}).get("rank") == 3,
          [cards.get(k, {}).get("rank") for k in ("c3", "c4", "c5")])
    check("1.6 slices from the frontmatter, in order",
          [s["slice"] for s in res.get("slices", [])] == ["mvp", "r1", "r2"], res.get("slices"))
    check("1.7 product and epic read", res.get("product") == "zorg" and res.get("epic") == "PROJ-1234", res)
    check("1.8 a card's epic falls back to the frontmatter's", cards.get("c1", {}).get("epic") == "PROJ-1234", cards.get("c1"))
    lay = res.get("layout", {})
    check("1.9 layout: eight columns, a band per slice plus the backlog",
          len(lay.get("columns", [])) == 8 and [b["slice"] for b in lay.get("bands", [])] == ["mvp", "r1", "r2", ""], lay)
    mvp = lay.get("bands", [{}])[0].get("cells", []) if lay.get("bands") else []
    check("1.10 layout: the MVP band holds c3 under «Вибрати поштомат на карті», c1 under the first step",
          mvp[:2] == [["c1"], ["c3"]], mvp)
    backlog = lay.get("bands", [{}])[-1].get("cells", []) if lay.get("bands") else []
    check("1.11 layout: the card with no slice sits in the backlog band", backlog[-1:] == [["c18"]], backlog)
    check("1.12 baseline read from the frontmatter",
          [b["slice"] for b in res.get("baseline", [])] == ["mvp", "r1"] and "c19" in res["baseline"][0]["cards"],
          res.get("baseline"))
    check("1.13 the clean map parses with no error", res.get("errors") == [], res.get("errors"))

    rc, out, res = run("parse", "--note", bad)
    gaps = res.get("gaps", [])
    check("1.14 a gap row is a gap, not a card", len(gaps) == 1 and gaps[0]["step"] == "Оплатити при отриманні"
          and all(c["id"] for c in res.get("cards", [])), gaps)

    en = os.path.join(d, "map-en.md")
    t = open(note, encoding="utf-8").read()
    t = t.replace("| id | діяльність | крок | картка | зріз | фіча | епік | джерело | edge_of |",
                  "| ID | Activity | Step | Card | Slice | Feature | Epic | Source | edge_of |")
    write(en, t)
    rc, out, res = run("parse", "--note", en)
    check("1.15 English headers parse the same", rc == 0 and len(res.get("cards", [])) == 18, out)
    crlf = os.path.join(d, "map-crlf.md")
    write(crlf, read(note).replace(b"\n", b"\r\n"))
    rc, out, res = run("parse", "--note", crlf)
    check("1.16 a CRLF note parses the same", rc == 0 and len(res.get("cards", [])) == 18
          and len(res.get("slices", [])) == 3, out)
    nt = os.path.join(d, "no-table.md")
    write(nt, "---\ntype: roadmap\nsubtype: story-map\n---\n\n# Nothing here\n")
    rc, out, res = run("parse", "--note", nt)
    check("1.17 a note without the table is exit 2 with a reason", rc == 2 and res.get("ok") is False and res.get("error"), out)
    nc = os.path.join(d, "no-col.md")
    write(nc, t.replace("| ID | Activity | Step | Card |", "| ID | Activity | Stage | Card |"))
    rc, out, res = run("parse", "--note", nc)
    check("1.18 a table without the step column is not the map's (exit 2)", rc == 2, out)
    wc = os.path.join(d, "wrong-cells.md")
    write(wc, open(note, encoding="utf-8").read().replace("| c7 | Оплатити | Оплатити онлайн | Оплата частинами | r2 |",
                                                         "| c7 | Оплатити | Оплатити онлайн | Оплата частинами |"))
    rc, out, res = run("parse", "--note", wc)
    check("1.19 a row with the wrong number of cells is named", rc == 0 and any("c7" in e or "row" in e for e in res.get("errors", [])), res.get("errors"))
    rc, out, res = run("parse", "--note", os.path.join(d, "missing.md"))
    check("1.20 a note that is not there is exit 2", rc == 2 and res.get("ok") is False, out)

    # 2. check
    rc, out, res = run("check", "--note", note)
    check("2.1 the clean map has no finding", rc == 0 and res.get("findings") == [], res.get("findings"))
    rc, out, res = run("check", "--note", bad)
    codes = [f["finding"] for f in res.get("findings", [])]
    want = ["subitem", "work_type", "skeleton_gap", "no_outcome", "no_step", "no_source", "duplicate_id",
            "edge_unknown", "edge_other_step", "unknown_slice", "bad_code", "empty_step"]
    check("2.2 each script finding once", sorted(codes) == sorted(want), codes)
    by = {f["finding"]: f for f in res.get("findings", [])}
    check("2.3 findings name their card", by.get("subitem", {}).get("card") == "f1" and by.get("work_type", {}).get("card") == "f2"
          and by.get("edge_other_step", {}).get("card") == "f7" and by.get("bad_code", {}).get("card") == "f9", by)
    check("2.4 skeleton_gap names the activity", by.get("skeleton_gap", {}).get("activity") == "Оплатити", by.get("skeleton_gap"))
    check("2.5 no_outcome names the slice", by.get("no_outcome", {}).get("slice") == "r1", by.get("no_outcome"))
    m = mutant(d, "skeleton", "if first and not any(", "if False and not any(")
    if m is None:
        check("2.6 M3 the skeleton mutation applies", False, "pattern not in the script")
    else:
        rc, out, res = run("check", "--note", bad, script=m)
        check("2.6 M3 a script that skips the skeleton check is caught",
              "skeleton_gap" not in [f["finding"] for f in res.get("findings", [])], res.get("findings"))

    # 3. render-html
    page = os.path.join(d, "map.html")
    rc, out, res = run("render-html", "--note", note, "--out", page, "--status", status, "--lang", "uk")
    html = open(page, encoding="utf-8").read() if os.path.exists(page) else ""
    check("3.1 render-html writes the page", rc == 0 and html.startswith("<!doctype html>"), out)
    check("3.2 no external request and no link", not re.search(r"https?://|src=|href=|<link|@import|url\(", html, re.I),
          re.findall(r"https?://\S+|src=\S+|href=\S+", html)[:5])
    check("3.3 a band per slice with its outcome", all(s in html for s in ("mvp", "r1", "r2"))
          and "частка замовлень у поштомат ≥ 15 % за 4 тижні після запуску" in html, "")
    check("3.4 the note's name and the status source and date at the top",
          "map-parcel-locker.md" in html and "initiative-status PROJ-1234" in html and "2026-11-10" in html, "")
    check("3.5 light theme declared", "color-scheme:light" in html.replace(" ", ""), "")
    check("3.6 status colours on the cards", "card st-done" in html and "card st-blocked" in html and "card st-unknown" in html, "")
    check("3.7 each card's source is on the page", "концепт §6" in html and "FR-9" in html, "")
    check("3.8 Ukrainian labels on --lang uk", "Мапа історій" in html and "Беклог" in html, "")
    xss = os.path.join(d, "map-xss.md")
    write(xss, open(note, encoding="utf-8").read().replace("Оплата частинами", "<script>alert(1)</script> & <b>x</b>"))
    page2 = os.path.join(d, "xss.html")
    rc, out, res = run("render-html", "--note", xss, "--out", page2, "--lang", "en")
    h2 = open(page2, encoding="utf-8").read() if os.path.exists(page2) else ""
    check("3.9 card text is escaped", "<script>" not in h2 and "&lt;script&gt;alert(1)&lt;/script&gt; &amp; &lt;b&gt;x&lt;/b&gt;" in h2,
          re.findall(r".{0,30}alert.{0,30}", h2))
    check("3.10 English labels on --lang en", "Story map" in h2 and "Backlog" in h2, "")
    check("3.11 without a status file the page says so", "no status" in h2.lower(), "")
    m = mutant(d, "escape", "def esc(s):\n    return html.escape(", "def esc(s):\n    return str(s) or html.escape(")
    if m is None:
        check("3.12 M2 the escaping mutation applies", False, "pattern not in the script")
    else:
        page3 = os.path.join(d, "xss-m.html")
        run("render-html", "--note", xss, "--out", page3, script=m)
        h3 = open(page3, encoding="utf-8").read() if os.path.exists(page3) else "<script>"
        check("3.12 M2 a script that skips escaping is caught", "<script>" in h3, "")

    # 4. progress
    rc, out, res = run("progress", "--note", note, "--status", status)
    sl = {s["slice"]: s for s in res.get("slices", [])}
    mv = sl.get("mvp", {})
    check("4.1 progress exits 0 with the source and date", rc == 0 and res.get("date") == "2026-11-10"
          and "initiative-status" in res.get("source", ""), out)
    check("4.2 MVP spread over the canons", mv.get("spread") == {"done": 2, "in_progress": 1, "planned": 2, "blocked": 1, "unknown": 0},
          mv.get("spread"))
    check("4.3 MVP % done", mv.get("done_pct") == 33, mv.get("done_pct"))
    check("4.4 blocked cards listed", [b["id"] for b in mv.get("blocked", [])] == ["c9"], mv.get("blocked"))
    check("4.5 a feature the status file does not name is unknown",
          sl.get("r1", {}).get("spread", {}).get("unknown") == 1, sl.get("r1", {}).get("spread"))
    check("4.6 MVP against its baseline: c11 moved in from r1, c10 moved out to r1, c19 gone",
          mv.get("added") == ["c11"] and mv.get("moved_in") == [{"id": "c11", "from": "r1"}]
          and mv.get("moved_out") == [{"id": "c10", "to": "r1"}] and mv.get("removed") == [{"id": "c19", "now": "gone"}],
          {k: mv.get(k) for k in ("added", "moved_in", "moved_out", "removed")})
    check("4.7 growth % against the baseline", mv.get("growth_pct") == 14 and sl.get("r1", {}).get("growth_pct") == 33,
          (mv.get("growth_pct"), sl.get("r1", {}).get("growth_pct")))
    check("4.8 a slice with no baseline has no growth", sl.get("r2", {}).get("baseline") is None
          and sl.get("r2", {}).get("growth_pct") is None, sl.get("r2"))
    check("4.9 the backlog is counted apart", res.get("backlog") == 1, res.get("backlog"))
    bs = os.path.join(d, "bad-status.json")
    write(bs, json.dumps({"source": "x", "date": "2026-11-10", "features": {"PROJ-1234.1": "Готово"}}))
    rc, out, res = run("progress", "--note", note, "--status", bs)
    check("4.10 a status that is not a canon is refused (exit 2)", rc == 2 and res.get("ok") is False, out)
    page4 = os.path.join(d, "prog.html")
    run("render-html", "--note", note, "--out", page4, "--status", status, "--lang", "uk")
    h4 = open(page4, encoding="utf-8").read() if os.path.exists(page4) else ""
    check("4.11 the page carries the % and the growth", "33%" in h4 and "+1" in h4, "")

    # 5. baseline
    b0 = read(note)
    rc, out, res = run("baseline", "--note", note, "--slice", "r2", "--date", "2026-11-10")
    b1 = read(note)
    check("5.1 baseline exits 0", rc == 0 and res.get("ok") is True and res.get("cards") == ["c5", "c7", "c12", "c14"], out)
    i0, j0 = b0.index(b"baseline:"), b0.index(b"tags:")
    i1, j1 = b1.index(b"baseline:"), b1.index(b"tags:")
    check("5.2 every byte before the field stays", b0[:i0] == b1[:i1], "")
    check("5.3 every byte after the field stays", b0[j0:] == b1[j1:], "")
    rc, out, res = run("parse", "--note", note)
    check("5.4 the new entry reads back, the other slices' kept",
          [b["slice"] for b in res.get("baseline", [])] == ["mvp", "r1", "r2"]
          and res["baseline"][2]["cards"] == ["c5", "c7", "c12", "c14"] and res["baseline"][2]["date"] == "2026-11-10",
          res.get("baseline"))
    rc, out, res = run("baseline", "--note", note, "--slice", "mvp", "--date", "2026-11-11")
    rc, out, res = run("parse", "--note", note)
    check("5.5 a slice's entry is replaced in place, never doubled",
          [b["slice"] for b in res.get("baseline", [])] == ["mvp", "r1", "r2"] and res["baseline"][0]["date"] == "2026-11-11"
          and "c19" not in res["baseline"][0]["cards"], res.get("baseline"))
    crlf2 = os.path.join(d, "map-crlf2.md")
    write(crlf2, b0.replace(b"\n", b"\r\n"))
    c0 = read(crlf2)
    rc, out, res = run("baseline", "--note", crlf2, "--slice", "r2", "--date", "2026-11-10")
    c1 = read(crlf2)
    check("5.6 CRLF: the rest byte for byte, the field in CRLF",
          rc == 0 and c0[:c0.index(b"baseline:")] == c1[:c1.index(b"baseline:")] and c0[c0.index(b"tags:"):] == c1[c1.index(b"tags:"):]
          and b"\n" not in c1.replace(b"\r\n", b""), out)
    empty = os.path.join(d, "map-findings-copy.md")
    shutil.copy(bad, empty)
    e0 = read(empty)
    rc, out, res = run("baseline", "--note", empty, "--slice", "mvp", "--date", "2026-11-10")
    e1 = read(empty)
    check("5.7 `baseline: []` is replaced by the entry, the rest kept",
          rc == 0 and e1.startswith(e0[:e0.index(b"baseline: []")]) and e1.endswith(e0[e0.index(b"baseline: []") + len(b"baseline: []\n"):]),
          out)
    rc, out, res = run("baseline", "--note", note, "--slice", "r9")
    check("5.8 a slice the map does not declare is refused (exit 2)", rc == 2, out)
    rc, out, res = run("baseline", "--note", note, "--slice", "mvp", "--date", "10.11.2026")
    check("5.9 a date not YYYY-MM-DD is refused (exit 2)", rc == 2, out)
    m = mutant(d, "baseline", 'pub.write_field(path, text, False, "baseline"', 'pub.write_field(path, text.replace("epic: PROJ-1234", "epic: PROJ-1235"), False, "baseline"')
    if m is None:
        check("5.10 M1 the baseline mutation applies", False, "pattern not in the script")
    else:
        mn = os.path.join(d, "map-mut.md")
        write(mn, b0)
        run("baseline", "--note", mn, "--slice", "r2", "--date", "2026-11-10", script=m)
        m1 = read(mn)
        check("5.10 M1 a baseline that rewrites another field is caught by the byte check",
              b0[:b0.index(b"baseline:")] != m1[:m1.index(b"baseline:")], "")

    # 6. board-diff
    last, now = os.path.join(d, "board-last.svg"), os.path.join(d, "board-now.svg")
    rc, out, res = run("board-diff", "--last", last, "--now", now, "--note", note)
    check("6.1 board-diff exits 0 with state diff", rc == 0 and res.get("state") == "diff", out)
    ch = res.get("changed", [])
    check("6.2 one changed card, found by its old text", len(ch) == 1 and ch[0]["id"] == "3458764000000003001"
          and ch[0].get("card") == "c1" and "сторінці товару" in ch[0]["now"], ch)
    ad = res.get("added", [])
    check("6.3 one added item, with the frame it sits in", len(ad) == 1 and ad[0]["id"] == "3458764000000003999"
          and ad[0]["frame"].startswith("MVP"), ad)
    rm = res.get("removed", [])
    check("6.4 one removed card", len(rm) == 1 and rm[0]["id"] == "3458764000000003005" and rm[0].get("card") == "c5", rm)
    mo = res.get("moved", [])
    check("6.5 one moved card, from R1 to MVP", len(mo) == 1 and mo[0]["id"] == "3458764000000003004"
          and mo[0].get("card") == "c4" and mo[0]["frame_from"].startswith("R1") and mo[0]["frame_to"].startswith("MVP"), mo)
    check("6.6 markup inside a sticky (<p>) is not a change", not any(c["id"] == "3458764000000002002" for c in ch), ch)
    check("6.7 counts", res.get("counts") == {"changed": 1, "moved": 1, "added": 1, "removed": 1}, res.get("counts"))
    sc = res.get("scope", {})
    check("6.8 the area to read back covers the last state", sc.get("x", 1) <= 0 and sc.get("y", 1) <= 0
          and sc.get("x", 0) + sc.get("width", 0) >= 2000 and sc.get("y", 0) + sc.get("height", 0) >= 1520, sc)
    rc, out, res = run("board-diff", "--now", now)
    check("6.9 no state → unknown", rc == 0 and res.get("state") == "unknown", out)
    rc, out, res = run("board-diff", "--last", os.path.join(d, "gone.svg"), "--now", now)
    check("6.10 a state file that is not there → unknown", rc == 0 and res.get("state") == "unknown", out)
    rc, out, res = run("board-diff", "--last", last)
    check("6.11 --last alone gives the area to read", rc == 0 and res.get("state") == "scope" and res.get("scope"), out)
    broken = os.path.join(d, "broken.svg")
    write(broken, "<svg><g data-miro-id='1'>")
    rc, out, res = run("board-diff", "--last", last, "--now", broken)
    check("6.12 a board read that does not parse is exit 2", rc == 2 and res.get("ok") is False, out)
    rc, out, res = run("board-diff", "--last", last, "--now", last)
    check("6.13 the same board twice is no change", res.get("counts") == {"changed": 0, "moved": 0, "added": 0, "removed": 0}, res)

    # 7. schema — check 26
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    import story_map as sm  # noqa: E402
    r2 = os.path.join(d, "root")
    for rel in ("references/story-map-protocol.md", "references/planning-core.md", "references/vault-schema.md",
                "references/artifact-publishing.md", "skills/roadmap-architect/SKILL.md"):
        os.makedirs(os.path.dirname(os.path.join(r2, rel)), exist_ok=True)
        shutil.copy(os.path.join(ROOT, rel), os.path.join(r2, rel))
    sk = os.path.join(r2, "skills", "roadmap-architect", "SKILL.md")
    skt = open(sk, encoding="utf-8").read()
    if "story-map-protocol.md" not in skt:                      # before task 4 the skill does not cite it yet
        write(sk, skt + "\n`references/story-map-protocol.md`\n")
    errs = sm.check_protocol(r2)
    check("7.1 check_protocol is clean on a sound tree", errs == [], errs)
    rc, out, res = run("schema")
    check("7.2 schema prints the fields, columns, findings and statuses",
          rc == 0 and res.get("fields") == list(sm.FIELDS) and res.get("statuses") == list(sm.STATUSES)
          and len(res.get("columns", [])) == 9 and len(res.get("findings", [])) == 12, out)

    def drift(rel, old, new, expect, name):
        p = os.path.join(r2, rel)
        t0 = open(p, encoding="utf-8").read()
        if old not in t0:
            check(name, False, "pattern not in %s" % rel)
            return
        write(p, t0.replace(old, new, 1))
        e = sm.check_protocol(r2)
        write(p, t0)
        check(name, any(expect in x for x in e), e)

    drift("references/story-map-protocol.md", "| `baseline` | written only", "| `basis` | written only", "baseline", "7.3 a frontmatter field the protocol renames is named")
    drift("references/story-map-protocol.md", "| `source` | `джерело` |", "| `source` | `звідки` |", "джерело", "7.4 a Ukrainian header that drifts is named")
    drift("references/story-map-protocol.md", "| `empty_step` | script |", "| `empty_step` | model |", "empty_step", "7.5 a script finding the protocol hands to the model is named")
    drift("references/planning-core.md", "| `blocked` |", "| `on_hold` |", "blocked", "7.6 a canon status that drifts in planning-core is named")
    drift("references/vault-schema.md", "structure tree, or story map (subtype in frontmatter; the story map's own fields — `story-map-protocol.md` §4)", "or structure tree (subtype in frontmatter)", "story map", "7.7 vault-schema without the story map is named")
    drift("references/artifact-publishing.md", "| `roadmap-architect` | `roadmap-architect/", "| `roadmap` | `roadmap-architect/", "roadmap-architect", "7.8 artifact-publishing without the key row is named")
    drift("skills/roadmap-architect/SKILL.md", "story-map-protocol.md", "story-map.md", "cite", "7.9 a skill that stops citing the protocol is named")
    drift("references/story-map-protocol.md", "| `board-diff --last", "| `board-compare --last", "board-diff", "7.10 a command the protocol stops naming is named")
    os.remove(os.path.join(r2, "references", "story-map-protocol.md"))
    check("7.11 a missing protocol is an error, not silence", sm.check_protocol(r2) != [], sm.check_protocol(r2))
finally:
    shutil.rmtree(d, ignore_errors=True)
    shutil.rmtree(SAFE_HOME, ignore_errors=True)

print("\nRESULT: %s (%d failed)" % ("GREEN ✅" if not fails else "RED ❌", fails))
sys.exit(1 if fails else 0)
