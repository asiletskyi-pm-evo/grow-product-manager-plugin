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
- schema: check 26's check_protocol is clean on a sound tree and names each drift;
- v4.11.2 (§12): the board on the host's own board type (`--surface whiteboard`, fixtures story-map/wb-*) — the same
  roles as on Miro, the diff's categories, a person's note always the team's, `partial` on a read missing a page,
  an empty read refused, the state's surface taken on `--last`; the Miro replay still byte for byte.
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


def mutant(d, name, old, new, target="story_map.py"):
    """A copy of the script (with its sibling modules) where `old` became `new` in `target` — the script itself, or a
    module it imports (note_table.py holds the escaping since v4.7.0); None when `old` is not there."""
    src = open(os.path.join(os.path.dirname(SCRIPT), target), encoding="utf-8").read()
    if old not in src:
        return None
    mdir = os.path.join(d, "mut-" + name)
    os.makedirs(mdir)
    for f in os.listdir(os.path.dirname(SCRIPT)):
        if f.endswith(".py"):
            shutil.copy(os.path.join(os.path.dirname(SCRIPT), f), mdir)
    with open(os.path.join(mdir, target), "w", encoding="utf-8") as f:
        f.write(src.replace(old, new, 1))
    return os.path.join(mdir, "story_map.py")


d = tempfile.mkdtemp(prefix="story-map-test-")
try:
    for f in os.listdir(FIX):
        (shutil.copytree if os.path.isdir(os.path.join(FIX, f)) else shutil.copy)(os.path.join(FIX, f), os.path.join(d, f))
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
    check("1.19 a short row is padded as GFM does — kept, and named", rc == 0 and any("c7" in e for e in res.get("errors", []))
          and any(c["id"] == "c7" and c["slice"] == "" for c in res.get("cards", [])), (res.get("errors"), len(res.get("cards", []))))
    rc, out, res = run("parse", "--note", os.path.join(d, "missing.md"))
    check("1.20 a note that is not there is exit 2", rc == 2 and res.get("ok") is False, out)

    # 2. check
    rc, out, res = run("check", "--note", note)
    check("2.1 the clean map has no finding", rc == 0 and res.get("findings") == [], res.get("findings"))
    rc, out, res = run("check", "--note", bad)
    codes = [f["finding"] for f in res.get("findings", [])]
    want = ["subitem", "work_type", "skeleton_gap", "no_outcome", "no_step", "no_source", "duplicate_id",
            "edge_unknown", "edge_other_step", "unknown_slice", "bad_code", "empty_step", "duplicate_feature", "link"]
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
    m = mutant(d, "escape", "def esc(s):\n    return html.escape(", "def esc(s):\n    return str(s) or html.escape(", target="note_table.py")
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
    check("6.7 counts", res.get("counts") == {"changed": 1, "moved": 1, "added": 1, "removed": 1, "backbone": 0, "orphaned": 0}, res.get("counts"))
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
    check("6.13 the same board twice is no change", res.get("counts") == {"changed": 0, "moved": 0, "added": 0, "removed": 0, "backbone": 0, "orphaned": 0}, res)

    # 8. review 1 (frozen cbd5714): each finding reproduced first
    # I-2 a short row is kept (GFM pads it) — render and baseline keep its card
    sr = os.path.join(d, "short-row.md")
    write(sr, open(note, encoding="utf-8").read().replace("| c3 | Обрати доставку | Вибрати поштомат на карті | Список найближчих поштоматів за адресою | mvp | PROJ-1234.2 |  | концепт §3 |  |",
                                                        "| c3 | Обрати доставку | Вибрати поштомат на карті | Список найближчих поштоматів за адресою | mvp | PROJ-1234.2 |"))
    page5 = os.path.join(d, "short.html")
    rc, out, res = run("render-html", "--note", sr, "--out", page5)
    h5 = open(page5, encoding="utf-8").read() if os.path.exists(page5) else ""
    check("8.1 I-2 a short row's card is on the page and the page result names the row", "Список найближчих поштоматів" in h5
          and any("c3" in e for e in res.get("errors", [])), res.get("errors"))
    rc, out, res = run("baseline", "--note", sr, "--slice", "mvp", "--date", "2026-11-10")
    check("8.2 I-2 baseline keeps a short row's card", "c3" in res.get("cards", []), res.get("cards"))
    sep = os.path.join(d, "short-sep.md")
    write(sep, open(note, encoding="utf-8").read().replace("|---|---|---|---|---|---|---|---|---|", "|--|--|--|--|--|--|--|--|--|"))
    rc, out, res = run("parse", "--note", sep)
    check("8.3 m-7 a separator of two dashes is no card", not any(c["id"].startswith("-") for c in res.get("cards", []))
          and len(res.get("cards", [])) == 18, [c["id"] for c in res.get("cards", [])][:3])

    # I-3 the board's state maps each sticky to its card while note and board agree
    state = os.path.join(d, "state.board.json")
    rc, out, res = run("board-state", "--read", last, "--note", note, "--out", state)
    check("8.4 I-3 board-state maps stickies to cards, activities, steps and slices", rc == 0
          and res.get("cards", {}).get("c1") == "3458764000000003001" and res.get("cards", {}).get("c5") == "3458764000000003005"
          and res.get("roles", {}).get("activity") == 1 and res.get("roles", {}).get("step") == 2
          and res.get("slices", {}).get("mvp") == "3458764000000001002", res)
    check("8.5 I-3 cards without a sticky are named for the next version", "c6" in res.get("unmapped_cards", []), res.get("unmapped_cards"))
    edited = os.path.join(d, "map-edited.md")
    write(edited, open(note, encoding="utf-8").read().replace("Поштомат як спосіб доставки в кошику", "Поштомат першим у списку доставок"))
    rc, out, res = run("board-diff", "--last", state, "--now", now, "--note", edited)
    ch = res.get("changed", [])
    check("8.6 I-3 after the PM edits the note, the team's change still names its card (from the state)",
          len(ch) == 1 and ch[0].get("card") == "c1", ch)

    # I-4 dragging a frame moves the frame, not every card in it
    dragged = os.path.join(d, "board-dragged.svg")
    write(dragged, open(last, encoding="utf-8").read().replace('transform="translate(0,600)"', 'transform="translate(0,700)"'))
    rc, out, res = run("board-diff", "--last", state, "--now", dragged)
    check("8.7 I-4 a dragged slice frame is one backbone move and no card moves",
          res.get("counts", {}).get("moved") == 0 and res.get("counts", {}).get("backbone") == 1 and len(res.get("backbone", [])) == 1
          and res["backbone"][0].get("kind") == "frame", (res.get("counts"), res.get("backbone")))

    # I-5 a card moved out of the area still comes back when read by id; two reads merge
    rc, out, res = run("board-diff", "--last", state)
    check("8.8 I-5 the state gives the ids to read back as well as the area", "3458764000000003005" in res.get("ids", [])
          and res.get("scope"), res)
    far = os.path.join(d, "board-far.svg")
    write(far, '<svg xmlns="http://www.w3.org/2000/svg"><rect data-type="sticky" data-miro-id="3458764000000003005" '
               'x="9000" y="9000" width="199" height="228" data-content="Поштомат переповнений — запропонувати сусідній" /></svg>')
    rc, out, res = run("board-diff", "--last", state, "--now", now, far, "--note", note)
    check("8.9 I-5 a card read back by id far away is moved, not removed", res.get("counts", {}).get("removed") == 0
          and any(m.get("card") == "c5" for m in res.get("moved", [])), (res.get("counts"), res.get("moved")))

    # m-10 backbone and other items are not counted as card changes
    nb = os.path.join(d, "board-backbone.svg")
    nbt = open(now, encoding="utf-8").read().replace('data-content="Вибрати поштомат на карті"', 'data-content="Вибрати поштомат"')
    nbt = nbt.replace("</svg>", '<text data-miro-id="3458764000000009001" x="10" y="1700">нотатка команди</text>\n</svg>')
    write(nb, nbt)
    rc, out, res = run("board-diff", "--last", state, "--now", nb, "--note", note)
    check("8.10 m-10 a step's sticky renamed is a backbone change; loose text is other; card counts unchanged",
          res.get("counts") == {"changed": 1, "moved": 1, "added": 1, "removed": 1, "backbone": 1, "orphaned": 0}
          and any(b.get("role") == "step" for b in res.get("backbone", [])) and len(res.get("other", [])) == 1,
          (res.get("counts"), res.get("backbone"), res.get("other")))

    # I-6 a link never reaches the page; a secret is redacted; check names the link
    tok = "glpat-" + "Zx9" * 7
    lk = os.path.join(d, "map-link.md")
    write(lk, open(note, encoding="utf-8").read().replace("| FR-9 |", "| https://user:pw@zorg.example.com/wiki/x?token=abc |")
          .replace("Оплата частинами", "Оплата частинами, ключ " + tok))
    page6 = os.path.join(d, "link.html")
    run("render-html", "--note", lk, "--out", page6)
    h6 = open(page6, encoding="utf-8").read() if os.path.exists(page6) else "http"
    check("8.11 I-6 no URL and no secret reaches the page", "zorg.example.com" not in h6 and "http" not in h6 and tok not in h6, "")
    rc, out, res = run("check", "--note", lk)
    check("8.12 I-6 check names a link in a card's cells", any(f["finding"] == "link" and f.get("card") == "c14" for f in res.get("findings", [])),
          res.get("findings"))

    # m-8 a slice id is written quoted and reads back as written
    q = os.path.join(d, "map-true.md")
    write(q, open(note, encoding="utf-8").read().replace("  - slice: r2\n", '  - slice: "true"\n').replace("| r2 |", "| true |"))
    run("baseline", "--note", q, "--slice", "true", "--date", "2026-11-10")
    run("baseline", "--note", q, "--slice", "mvp", "--date", "2026-11-10")
    rc, out, res = run("parse", "--note", q)
    check("8.13 m-8 a slice id like «true» survives a baseline round trip", any(b["slice"] == "true" for b in res.get("baseline", [])),
          res.get("baseline"))
    up = os.path.join(d, "map-upper.md")
    write(up, open(note, encoding="utf-8").read().replace("  - slice: r2\n", "  - slice: R2 next\n"))
    rc, out, res = run("parse", "--note", up)
    check("8.14 m-8 a slice id that is not a lower-case id is named", any("R2 next" in e for e in res.get("errors", [])), res.get("errors"))

    # m-12 edge_of itself, one feature on two cards, work-type forms
    m12 = os.path.join(d, "map-m12.md")
    write(m12, open(note, encoding="utf-8").read()
          .replace("| концепт §3 | c3 |", "| концепт §3 | c5 |")
          .replace("| c7 | Оплатити | Оплатити онлайн | Оплата частинами | r2 |  |", "| c7 | Оплатити | Оплатити онлайн | [FE] Екран оплати частинами | r2 | PROJ-1234.3 |")
          .replace("Оплата карткою на терміналі поштомата", "Android — оплата карткою на терміналі"))
    rc, out, res = run("check", "--note", m12)
    fs = [(f["finding"], f.get("card")) for f in res.get("findings", [])]
    check("8.15 m-12 edge_of pointing at its own card is named", ("edge_unknown", "c5") in fs, fs)
    check("8.16 m-12 one feature code on two cards is named", ("duplicate_feature", "c7") in fs, fs)
    check("8.17 m-12 «[FE] …» is a work type, «Android — …» is not", ("work_type", "c7") in fs and ("work_type", "c8") not in fs, fs)

    # m-13 a note that is not UTF-8 is exit 2, never a traceback
    nu = os.path.join(d, "not-utf8.md")
    write(nu, read(note).replace("Zorg".encode(), b"\xff\xfe"))
    rc, out, res = run("parse", "--note", nu)
    check("8.18 m-13 a note that is not UTF-8 is exit 2 with a reason", rc == 2 and res.get("ok") is False and "Traceback" not in out, out[-300:])

    # 9. review 2 (frozen d953560)
    # I-2b a partial state (one frame) never turns the map's own stickies into the team's additions
    part = os.path.join(d, "board-mvp-only.svg")
    lt = open(last, encoding="utf-8").read()
    i0 = lt.index('<g id="mvp"'); i1 = lt.index("</g>", i0) + 4
    write(part, '<svg xmlns="http://www.w3.org/2000/svg">\n' + lt[i0:i1] + "\n</svg>\n")
    pstate = os.path.join(d, "partial.board.json")
    run("board-state", "--read", part, "--note", note, "--out", pstate)
    rc, out, res = run("board-diff", "--last", pstate, "--now", last, "--note", note)
    unrec = res.get("unrecorded", [])
    check("9.1 I-2 stickies and frames the note names are «unrecorded», not added by the team",
          res.get("counts", {}).get("added") == 0 and any(u.get("card") == "c2" for u in unrec)
          and any(u.get("role") == "activity" for u in unrec) and any(u.get("role") == "slice" for u in unrec),
          (res.get("counts"), [(u.get("role"), u.get("card")) for u in unrec]))
    # I-2a after «лише забрати в мапу» the team's sticky is the note's new card — a second diff adds no card again
    taken = os.path.join(d, "map-taken.md")
    tt = open(note, encoding="utf-8").read()
    a19 = "| c18 | Забрати | Повернути посилку | Оцінити поштомат після отримання |  |  |  | зі слів PM |  |\n"
    write(taken, tt.replace(a19, a19 + "| c19 | Обрати доставку | Вибрати поштомат на карті | Показати години роботи поштомата | mvp |  |  | дошка команди 2026-11-10 |  |\n"))
    rc, out, res = run("board-diff", "--last", state, "--now", now, "--note", taken)
    check("9.2 I-2 a team sticky already taken into the note is unrecorded with its card, never «added» twice",
          res.get("counts", {}).get("added") == 0 and any(u.get("card") == "c19" for u in res.get("unrecorded", [])),
          (res.get("counts"), res.get("unrecorded")))
    # I-4 a renamed activity counts: «nothing changed» is never said over a backbone edit
    ren = os.path.join(d, "board-renamed.svg")
    write(ren, lt.replace('data-content="Обрати доставку"', 'data-content="Обрати спосіб доставки"'))
    rc, out, res = run("board-diff", "--last", state, "--now", ren, "--note", note)
    check("9.3 I-4 a renamed activity is a counted backbone change", res.get("counts", {}).get("backbone") == 1
          and sum(v for k, v in res.get("counts", {}).items() if k != "backbone") == 0, res.get("counts"))
    # m-10 a card holding a secret is named by check — it never reaches the board
    sec = os.path.join(d, "map-secret.md")
    write(sec, open(note, encoding="utf-8").read().replace("Оплата частинами", "Оплата частинами, токен " + "glpat-" + "Qw8" * 7))
    rc, out, res = run("check", "--note", sec)
    check("9.4 m-10 check names a card holding a secret", any(f["finding"] == "secret" and f.get("card") == "c7" for f in res.get("findings", [])),
          res.get("findings"))
    # the card's caption names its feature code once, even when its source names it too
    dup = os.path.join(d, "map-dup.md")
    write(dup, open(note, encoding="utf-8").read().replace("| PROJ-1234.1 |  | концепт §2 |", "| PROJ-1234.1 |  | концепт §2 · PROJ-1234.1 |"))
    page7 = os.path.join(d, "dup.html")
    run("render-html", "--note", dup, "--out", page7)
    h7 = open(page7, encoding="utf-8").read() if os.path.exists(page7) else ""
    check("9.5 a feature code shown once in a card's caption", h7.count("PROJ-1234.1") == 1, h7.count("PROJ-1234.1"))

    # 10. review of the whole branch (frozen 79f263d)
    # I-1 a card named like its step maps to its own sticky, never to the step's
    sn = os.path.join(d, "map-stepname.md")
    write(sn, open(note, encoding="utf-8").read().replace("Список найближчих поштоматів за адресою", "Вибрати поштомат на карті"))
    sb = os.path.join(d, "board-stepname.svg")
    write(sb, lt.replace("Список найближчих поштоматів за адресою&lt;br&gt;", "Вибрати поштомат на карті&lt;br&gt;"))
    snst = os.path.join(d, "stepname.board.json")
    rc, out, res = run("board-state", "--read", sb, "--note", sn, "--out", snst)
    check("10.1 I-1 a card named like its step maps to the sticky in its slice frame, the step to the spine's",
          res.get("cards", {}).get("c3") == "3458764000000003003" and res.get("roles", {}).get("step") == 2, res)
    # I-2 a link with no scheme, or with credentials, never reaches the page, and check names it
    nl = os.path.join(d, "map-noscheme.md")
    write(nl, open(note, encoding="utf-8").read()
          .replace("| FR-9 |", "| bob:hunter2@wiki.zorg.example/pages/9 |")
          .replace("Оплата частинами", "Оплата частинами, див. confluence.zorg.example/pages/123?access_token=xyz987"))
    page8 = os.path.join(d, "noscheme.html")
    run("render-html", "--note", nl, "--out", page8)
    h8 = open(page8, encoding="utf-8").read() if os.path.exists(page8) else "zorg.example"
    check("10.2 I-2 links without a scheme or with credentials are removed from the page", "zorg.example" not in h8
          and "hunter2" not in h8 and "xyz987" not in h8, re.findall(r".{0,20}zorg\.example.{0,20}", h8)[:3])
    rc, out, res = run("check", "--note", nl)
    fl = {(f["finding"], f.get("card")) for f in res.get("findings", [])}
    check("10.3 I-2 check names both cards", ("link", "c7") in fl and ("link", "c14") in fl, fl)
    rc, out, res = run("parse", "--note", nl)
    bt = {c["id"]: c.get("board_text", "") for c in res.get("cards", [])}
    check("10.4 I-2 the parse gives each card the text the board may carry — no link in it",
          "zorg.example" not in bt.get("c7", "zorg.example") and bt.get("c1") == "Поштомат як спосіб доставки в кошику", bt.get("c7"))
    rc, out, res = run("parse", "--note", note)
    check("10.5 I-2 «README.md» or a feature code is no link", not any("[link removed]" in c.get("board_text", "") for c in res.get("cards", [])),
          [c.get("board_text") for c in res.get("cards", []) if "[" in c.get("board_text", "")])
    # I-4 a card dropped from the note leaves a named orphan, kept as one in the next state
    dr = os.path.join(d, "map-dropped.md")
    write(dr, "\n".join(l for l in open(note, encoding="utf-8").read().split("\n") if not l.startswith("| c5 |")))
    rc, out, res = run("board-diff", "--last", state, "--now", last, "--note", dr)
    check("10.6 I-4 a card removed from the note names its sticky as orphaned (counted)", res.get("counts", {}).get("orphaned") == 1
          and [o.get("card") for o in res.get("orphaned", [])] == ["c5"], (res.get("counts"), res.get("orphaned")))
    ost = os.path.join(d, "orphan.board.json")
    rc, out, res = run("board-state", "--read", last, "--note", dr, "--last", state, "--out", ost)
    check("10.7 I-4 the next state keeps the orphan as the plugin's own, never a team sticky", res.get("orphans") == {"c5": "3458764000000003005"}
          and res.get("roles", {}).get("orphan") == 1, res)
    # m-7 the stored state prints which card is which sticky
    rc, out, res = run("board-diff", "--last", state)
    check("10.8 m-7 the state's card → sticky map is printed for the next version", res.get("cards", {}).get("c1") == "3458764000000003001"
          and len(res.get("cards", {})) == 5, res.get("cards"))
    # m-6 a team copy of a mapped card's sticky is the team's addition; two equal texts take two cards; the first read wins
    cp = os.path.join(d, "board-copy.svg")
    write(cp, lt.replace("</svg>", '<rect data-type="sticky" data-miro-id="3458764000000007777" x="3000" y="3000" width="199" height="228" '
                                    'data-content="Карта поштоматів з фільтром «працює цілодобово»" />\n</svg>'))
    rc, out, res = run("board-diff", "--last", state, "--now", cp, "--note", note)
    check("10.9 m-6 a copy of a mapped card's sticky is added by the team, not unrecorded",
          [a["id"] for a in res.get("added", [])] == ["3458764000000007777"], (res.get("added"), res.get("unrecorded")))
    tw = os.path.join(d, "map-twins.md")
    write(tw, open(note, encoding="utf-8").read().replace("Ціна й строк доставки в поштомат поруч зі способом", "Карта поштоматів з фільтром «працює цілодобово»"))
    tb = os.path.join(d, "board-twins.svg")
    write(tb, lt.replace('data-content="Ціна й строк доставки в поштомат поруч зі способом"', 'data-content="Карта поштоматів з фільтром «працює цілодобово»"'))
    rc, out, res = run("board-state", "--read", tb, "--note", tw, "--out", os.path.join(d, "twins.board.json"))
    cm = res.get("cards", {})
    check("10.10 m-6 two cards of one text take two stickies (named ambiguous)", cm.get("c2") and cm.get("c4") and cm["c2"] != cm["c4"]
          and len(res.get("ambiguous", [])) == 2, res)
    r1 = os.path.join(d, "read-first.svg")
    write(r1, lt.replace('data-content="Карта поштоматів з фільтром «працює цілодобово»"', 'data-content="Перше читання"'))
    rc, out, res = run("board-diff", "--last", state, "--now", r1, last, "--note", note)
    check("10.11 m-6 of two reads, the first read of an element wins", any(c.get("now") == "Перше читання" for c in res.get("changed", [])),
          res.get("changed"))
    # v4.7.0: the shared safe() also hides a person's e-mail or phone (note_table.CONTACT)
    ct = os.path.join(d, "map-contact.md")
    write(ct, open(note, encoding="utf-8").read().replace("Оплата частинами", "Оплата частинами, пишіть ivan@zorg.example"))
    page_ct = os.path.join(d, "contact.html")
    run("render-html", "--note", ct, "--out", page_ct)
    hct = open(page_ct, encoding="utf-8").read() if os.path.exists(page_ct) else "ivan@"
    check("10.12 v4.7.0 a person's e-mail never reaches the map's page", "ivan@zorg.example" not in hct and "[contact hidden]" in hct, "")

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
          and len(res.get("columns", [])) == 9 and res.get("findings") == list(sm.FINDINGS)
          and "board-state" in res.get("commands", []), out)

    def drift(rel, old, new, expect, name, count=1):
        p = os.path.join(r2, rel)
        t0 = open(p, encoding="utf-8").read()
        if old not in t0:
            check(name, False, "pattern not in %s" % rel)
            return
        write(p, t0.replace(old, new, count))
        e = sm.check_protocol(r2)
        write(p, t0)
        check(name, any(expect in x for x in e), e)

    drift("references/story-map-protocol.md", "| `baseline` | written only", "| `basis` | written only", "baseline", "7.3 a frontmatter field the protocol renames is named")
    drift("references/story-map-protocol.md", "| `source` | `джерело` |", "| `source` | `звідки` |", "джерело", "7.4 a Ukrainian header that drifts is named")
    drift("references/story-map-protocol.md", "| `empty_step` | script |", "| `empty_step` | model |", "empty_step", "7.5 a script finding the protocol hands to the model is named")
    drift("references/planning-core.md", "| `blocked` |", "| `on_hold` |", "blocked", "7.6 a canon status that drifts in planning-core is named")
    drift("references/vault-schema.md", "structure tree, or story map (subtype in frontmatter; the story map's own fields — `story-map-protocol.md` §4)", "or structure tree (subtype in frontmatter)", "story map", "7.7 vault-schema without the story map is named")
    drift("references/artifact-publishing.md", "| `roadmap-architect` | `roadmap-architect/", "| `roadmap` | `roadmap-architect/", "roadmap-architect", "7.8 artifact-publishing without the key row is named")
    drift("skills/roadmap-architect/SKILL.md", "story-map-protocol.md", "story-map.md", "cite", "7.9 a skill that stops citing the protocol is named", count=-1)
    drift("references/story-map-protocol.md", "| `board-diff --last", "| `board-compare --last", "board-diff", "7.10 a command the protocol stops naming is named")
    # v4.11.2: the user's rule — the host's own board first, no board excluded from the story map, `--surface` named
    drift("references/story-map-protocol.md", sm.HOST_FIRST, "a registry record's board, then the host's own", "host's own board first",
          "7.12 the protocol's §7 without the host's own board first is named")
    drift("skills/roadmap-architect/SKILL.md", sm.HOST_FIRST, "the board tool's", "host's own board first",
          "7.12b the skill's 7d without the host's own board first is named")
    drift("references/story-map-protocol.md", "- A map on FigJam;", "- A map on FigJam, or on the host's own board type (not the story map's in this release);",
          "§11 still excludes", "7.13 a §11 that excludes the host's own board again is named")
    drift("references/artifact-publishing.md", "Both maps offer it:", "In this release only the journey map offers it; Both maps offer it:",
          "journey map only", "7.13b artifact-publishing §2 offering the host's board to the journey map only is named")
    drift("references/story-map-protocol.md", "[--surface miro\\|whiteboard] [--last S]", "[--surface miro] [--last S]", "--surface",
          "7.14 a §10 board command without both surfaces is named")
    drift("references/story-map-protocol.md", "`story_map.py board-layout ", "`story_map.py lay-out ", "laid out by",
          "7.15 a §6 whose host board is not laid out by board-layout is named")
    drift("skills/roadmap-architect/SKILL.md", "board-layout", "lay-out", "laid out by",
          "7.15b a skill whose host board is not laid out by board-layout is named", count=-1)
    os.makedirs(os.path.join(r2, "scripts"), exist_ok=True)
    shutil.copy(SCRIPT, os.path.join(r2, "scripts", "story_map.py"))
    drift("scripts/story_map.py", '"--surface", choices=bs.SURFACES, default="miro"', '"--surface", choices=("miro",), default="miro"',
          "board_state.SURFACES", "7.14b a board command whose surfaces are not board_state.SURFACES is named")
    os.remove(os.path.join(r2, "references", "story-map-protocol.md"))
    check("7.11 a missing protocol is an error, not silence", sm.check_protocol(r2) != [], sm.check_protocol(r2))

    # 11. v4.8.0: the board code moved to scripts/board_state.py — the map's board-state / board-diff give the same bytes
    #     as story_map.py at b5cd7ff (v4.7.0), every case of testing/fixtures/board/story-map-golden.json replayed
    def replay(script, tag):
        with open(os.path.join(ROOT, "testing", "fixtures", "board", "story-map-golden.json"), encoding="utf-8") as fh:
            gold = json.load(fh)["cases"]
        gd = os.path.join(d, "golden-" + tag)
        os.makedirs(gd)
        env = {k: v for k, v in os.environ.items() if not k.startswith("GROW_PM_")}
        env["HOME"] = SAFE_HOME
        bad = []
        for c in gold:
            args = [a.replace("<F>", os.path.join(ROOT, "testing", "fixtures")).replace("<D>", gd) for a in c["args"]]
            p = subprocess.run([sys.executable, script] + args, capture_output=True, text=True, env=env)
            got = re.sub(r'"at": "[^"]*"', '"at": "<AT>"', p.stdout.replace(gd, "<D>"))
            if p.returncode != c["rc"] or got != c["stdout"]:
                bad.append(" ".join(c["args"][:3]))
                continue
            if c.get("file"):
                with open(c["file"].replace("<D>", gd), encoding="utf-8") as fh:
                    content = re.sub(r'"at": "[^"]*"', '"at": "<AT>"', fh.read().replace(gd, "<D>"))
                if content != c["content"]:
                    bad.append("state " + c["file"])
        return len(gold), bad
    n, bad = replay(SCRIPT, "now")
    check("11.1 the map's board-state and board-diff print and keep the same bytes as at v4.7.0 (%d cases)" % n,
          n >= 14 and not bad, bad)
    src = open(SCRIPT, encoding="utf-8").read()
    check("11.2 story_map.py imports board_state and defines no reader of its own",
          re.search(r"^import board_state", src, re.M) is not None and not re.search(r"^def (?:read_board|read_miro_svg)\(", src, re.M), "")
    mb = mutant(d, "relframe", '"rx": (x or 0.0) + nox - ox, "ry": (y or 0.0) + noy - oy', '"rx": (x or 0.0) + nox, "ry": (y or 0.0) + noy',
                target="board_state.py") \
        if os.path.exists(os.path.join(os.path.dirname(SCRIPT), "board_state.py")) else None
    if mb is None:
        check("11.3 M4 mutation site present (a sticky's place relative to its frame)", False, "pattern not in board_state.py")
    else:
        n, bad = replay(mb, "relframe")
        check("11.3 M4 a reader whose stickies lose their frame-relative place is caught by the replay", bool(bad), bad)

    # 12. v4.11.2: the story map's board on the host's own board type (`--surface whiteboard`, plan C6–C8, C13).
    #     wb-last.json — the Zorg board as the host's list (activity and steps rounded blocks outside sections, a
    #     section per slice, cards rounded blocks); wb-now/ — an element folder: c1 moved MVP → R2, c4 retitled, a step
    #     renamed, a person's note in MVP; wb-partial.json — a read with the R2 page skipped.
    wl, wn, wp = (os.path.join(d, n) for n in ("wb-last.json", "wb-now", "wb-partial.json"))
    rc, out, res = run("board-state", "--surface", "whiteboard", "--read", os.path.join(d, "board-last.svg"), "--note", note,
                       "--out", os.path.join(d, "m.board.json"))
    miro_roles = res.get("roles")
    wst = os.path.join(d, "wb.artifact.board.json")
    rc, out, res = run("board-state", "--surface", "whiteboard", "--read", wl, "--note", note, "--out", wst)
    check("12.1 the host's board gives every element the role it has on Miro (5 cards, 3 slices, the backbone)",
          rc == 0 and res.get("roles") == {"other": 1, "activity": 1, "step": 2, "slice": 3, "card": 5}
          and res.get("cards") == {"c1": "wb-c1", "c3": "wb-c3", "c2": "wb-c2", "c4": "wb-c4", "c5": "wb-c5"}
          and res.get("slices") == {"mvp": "wb-mvp", "r1": "wb-r1", "r2": "wb-r2"}, (rc, out))
    rc2, out2, res2 = run("board-state", "--read", os.path.join(d, "board-last.svg"), "--note", note, "--out", os.path.join(d, "m2.board.json"))
    mr = dict(res2.get("roles") or {})
    mr.pop("frame", None)                           # the Miro fixture also has the backbone's frame
    check("12.2 the same map on Miro: the same cards, slices and backbone", {k: v for k, v in mr.items()} ==
          {"activity": 1, "step": 2, "slice": 3, "card": 5} and set(res2.get("cards", {})) == set(res.get("cards", {})),
          (res2.get("roles"), miro_roles))
    st = json.loads(read(wst).decode("utf-8")) if os.path.exists(wst) else {}
    check("12.3 the host's state names its surface; a Miro state never does", st.get("surface") == "whiteboard"
          and res.get("surface") == "whiteboard" and "surface" not in res2
          and os.path.exists(os.path.join(d, "m2.board.json"))
          and "surface" not in json.loads(read(os.path.join(d, "m2.board.json")).decode("utf-8")), (res.get("surface"), list(st)[:3]))
    check("12.4 the host's state keeps no author of a person's note", os.path.exists(wst) and b"author" not in read(wst), "")
    rc, out, res = run("board-diff", "--last", wst, "--now", wn, "--note", note)
    cnt = res.get("counts", {})
    check("12.5 board-diff on the host's board: changed 1, moved 1 (c1 MVP → R2), added 1, removed 0, backbone 1",
          res.get("state") == "diff" and res.get("surface") == "whiteboard"
          and cnt == {"changed": 1, "moved": 1, "added": 1, "removed": 0, "backbone": 1, "orphaned": 0}
          and [m.get("card") for m in res.get("moved", [])] == ["c1"]
          and res["moved"][0]["frame_to"].startswith("R2") and [c.get("card") for c in res.get("changed", [])] == ["c4"], (cnt, out))
    check("12.6 a person's note on the host's board is the team's addition, never a card of the plugin",
          [a["id"] for a in res.get("added", [])] == ["mwkxzorg-n1"] and res.get("unrecorded") == []
          and res["added"][0]["frame"].startswith("MVP"), (res.get("added"), res.get("unrecorded")))
    check("12.7 a renamed step is a backbone change, named with its old and new text",
          [(b.get("role"), b.get("change"), b.get("now")) for b in res.get("backbone", [])] == [("step", "text", "Обрати поштомат на карті")],
          res.get("backbone"))
    rc, out, res = run("board-diff", "--last", wst, "--now", wp, "--note", note)
    check("12.8 a read missing a page is `partial`, naming the slice section and the step it lacks — never «removed»",
          res.get("state") == "partial" and sorted(m["id"] for m in res.get("missing", [])) == ["wb-r2", "wb-s2"]
          and "removed" not in res and "counts" not in res, out)
    rc, out, res = run("board-state", "--surface", "whiteboard", "--read", wp, "--last", wst, "--note", note,
                       "--out", os.path.join(d, "wb-p.board.json"))
    check("12.9 board-state refuses a partial read of the host's board (exit 2, no state written)",
          rc == 2 and "partial" in res.get("error", "") and not os.path.exists(os.path.join(d, "wb-p.board.json")), (rc, out))
    em = os.path.join(d, "wb-empty")
    os.makedirs(em)
    rc, out, res = run("board-diff", "--last", wst, "--now", em, "--note", note)
    rc2, out2, _ = run("board-state", "--surface", "whiteboard", "--read", os.path.join(d, "wb-empty-list.json"), "--note", note,
                       "--out", os.path.join(d, "wb-e.board.json")) if write(os.path.join(d, "wb-empty-list.json"), "[]") is None else (0, "", {})
    check("12.10 an empty read of the host's board exits 2 — on board-diff and board-state", rc == 2 and rc2 == 2, (out, out2))
    rc, out, res = run("board-diff", "--last", wst, "--now", os.path.join(d, "wb-now", "elements"), "--note", note)
    check("12.11 `--last` takes the surface from the state: a host read needs no `--surface`", rc == 0
          and res.get("state") == "diff" and res.get("surface") == "whiteboard", out)
    rc, out, res = run("board-diff", "--last", wl, "--surface", "whiteboard", "--now", wn, "--note", note)
    check("12.12 a host list as `--last` is a read with `--surface whiteboard`, its roles by the note now",
          res.get("state") == "diff" and res.get("counts", {}).get("moved") == 1 and res.get("counts", {}).get("added") == 1, out)
    rc, out, res = run("board-diff", "--last", wst)
    check("12.13 the host state's area answer names its surface and the card → element map",
          res.get("state") == "scope" and res.get("surface") == "whiteboard" and res.get("cards", {}).get("c1") == "wb-c1", out)
    rc, out, res = run("board-state", "--surface", "whiteboard", "--read", wn, "--last", wst, "--note", note,
                       "--out", os.path.join(d, "wb2.artifact.board.json"))
    st2 = json.loads(read(os.path.join(d, "wb2.artifact.board.json")).decode("utf-8")) if rc == 0 else {}
    check("12.14 the next state of the host's board keeps the person's note as a sticky, never a card, c1 by its id",
          rc == 0 and st2.get("elements", {}).get("mwkxzorg-n1", {}).get("role") == "sticky"
          and res.get("cards", {}).get("c1") == "wb-c1", out)
    rc, out, res = run("board-state", "--surface", "figjam", "--read", wl, "--note", note, "--out", os.path.join(d, "x.json"))
    check("12.15 an unknown surface is refused by the command line", rc == 2 and not os.path.exists(os.path.join(d, "x.json")), out)

    # review of v4.11.2: a person's note whose text is a card's or a step's stays the team's; a read sharing nothing with
    # the state is partial, never «everything removed»; a folder as `--last` is the host's; a surface that is not the state's
    nn = os.path.join(d, "wb-note-twin")
    shutil.copytree(wn, nn)
    os.remove(os.path.join(nn, "elements", "wb-c1.json"))
    nj = os.path.join(nn, "elements", "mwkxzorg-n1.json")
    nd = json.loads(read(nj).decode("utf-8"))
    nd["text"] = "Поштомат як спосіб доставки в кошику\nPROJ-1234.1"
    write(nj, json.dumps(nd, ensure_ascii=False))
    nk = os.path.join(nn, "elements", "mwkxzorg-n2.json")
    write(nk, json.dumps({"type": "note", "x": 900, "y": 360, "w": 180, "h": 180, "text": "Оплатити онлайн"}, ensure_ascii=False))
    rc, out, res = run("board-state", "--surface", "whiteboard", "--read", nn, "--note", note, "--out", os.path.join(d, "twin.artifact.board.json"))
    check("12.17 a person's note with a card's text never becomes that card in the state", rc == 0
          and res.get("cards", {}).get("c1") != "mwkxzorg-n1" and "c1" in res.get("unmapped_cards", []), out)
    rc, out, res = run("board-diff", "--last", wst, "--now", nn, "--note", note)
    check("12.18 a person's note with a step's text is `added`, never `unrecorded`",
          "mwkxzorg-n2" in [a["id"] for a in res.get("added", [])] and res.get("unrecorded") == [], (res.get("added"), res.get("unrecorded")))
    lone = os.path.join(d, "wb-lone.json")
    write(lone, json.dumps([{"id": "mwkxzorg-z9", "data": {"type": "note", "x": 0, "y": 0, "text": "нова нотатка"}}], ensure_ascii=False))
    rc, out, res = run("board-diff", "--last", wst, "--now", lone, "--note", note)
    check("12.19 a host read that shares no element with the state is `partial`, never «everything removed»",
          res.get("state") == "partial" and "removed" not in res, out)
    rc, out, res = run("board-diff", "--last", os.path.join(d, "wb-now"), "--now", wn, "--note", note)
    check("12.20 a host folder as `--last` without `--surface` is read as the host's list", rc == 0 and res.get("state") == "diff"
          and res.get("surface") == "whiteboard", out)
    rc, out, res = run("board-diff", "--last", wst, "--surface", "miro", "--now", os.path.join(d, "board-now.svg"), "--note", note)
    check("12.21 a host state compared on another surface is refused with its reason", rc == 2 and "surface" in res.get("error", ""), out)

    # mutations of §12
    def mrun(script, *args):
        return run(*args, script=script)
    mm = mutant(d, "wbmiro", 'items = bs.read_boards(paths, surface)', 'items = bs.read_boards(paths, "miro")')
    if mm is None:
        check("12.M1 mutation site present (the host's read)", False, "pattern not in story_map.py")
    else:
        rc, out, res = mrun(mm, "board-state", "--surface", "whiteboard", "--read", wl, "--note", note, "--out", os.path.join(d, "mm.json"))
        check("12.M1 a host read through the Miro reader is caught (12.1)", not (rc == 0 and res.get("roles", {}).get("card") == 5), out)
    mm = mutant(d, "wbnopartial", 'lost = missing_backbone(last, now, p) if surface != "miro" else []', 'lost = []')
    if mm is None:
        check("12.M2 mutation site present (the partial guard)", False, "pattern not in story_map.py")
    else:
        rc, out, res = mrun(mm, "board-diff", "--last", wst, "--now", wp, "--note", note)
        check("12.M2 no partial guard: the read's skipped page counts as removed — caught (12.8)",
              res.get("state") != "partial" and res.get("counts", {}).get("removed", 0) > 0, out)
    mm = mutant(d, "wbdefault", 'p.add_argument("--surface", choices=bs.SURFACES, default="miro"',
                'p.add_argument("--surface", choices=bs.SURFACES, default="whiteboard"')
    if mm is None:
        check("12.M3 mutation site present (board-state's default surface)", False, "pattern not in story_map.py")
    else:
        n, bad = replay(mm, "wbdefault")
        check("12.M3 a default of `whiteboard` turns the Miro replay red (11.1)", bool(bad), bad)
    mm = mutant(d, "wbstate", 'return data["elements"], own', 'return data["elements"], "miro"')
    if mm is None:
        check("12.M4 mutation site present (the state's surface on --last)", False, "pattern not in story_map.py")
    else:
        rc, out, res = mrun(mm, "board-diff", "--last", wst, "--now", os.path.join(d, "wb-now", "elements"), "--note", note)
        check("12.M4 the state's surface ignored on `--last` is caught (12.11)", not (rc == 0 and res.get("surface") == "whiteboard"), out)
    mm = mutant(d, "wbnote", '        if it.get("type") == "note":', '        if False:')
    if mm is None:
        check("12.M5 mutation site present (a person's note stays theirs)", False, "pattern not in story_map.py")
    else:
        rc, out, res = mrun(mm, "board-state", "--surface", "whiteboard", "--read", nn, "--note", note, "--out", os.path.join(d, "mn.json"))
        check("12.M5 a note taken as the plugin's card is caught (12.17)", res.get("cards", {}).get("c1") == "mwkxzorg-n1", out)
    # §13 — the host board laid out by the script (board-layout, v4.11.2): no hand-moved column, nothing deleted
    def apply(batches, folder, base=None):
        """The board after the writes: a copy of `base` (a read folder) with every set and update applied."""
        els = {}
        if base:
            for f in sorted(os.listdir(os.path.join(base, "elements"))):
                els[f[:-5]] = json.loads(read(os.path.join(base, "elements", f)).decode("utf-8"))
        for b in batches:
            for w in b:
                if w["collection"] != "elements":
                    continue
                if w["op"] == "set":
                    els[w["doc_id"]] = dict(w["data"])
                elif w["op"] == "update":
                    els[w["doc_id"]].update(w["data"])
        os.makedirs(os.path.join(folder, "elements"))
        for k, v in els.items():
            write(os.path.join(folder, "elements", k + ".json"), json.dumps(v, ensure_ascii=False))
        return els

    def overlaps(els, ids):
        boxes = [(k, els[k]["x"], els[k]["y"], els[k]["x"] + els[k]["w"], els[k]["y"] + els[k]["h"]) for k in ids]
        return [(a[0], b[0]) for i, a in enumerate(boxes) for b in boxes[i + 1:]
                if a[1] < b[3] and b[1] < a[3] and a[2] < b[4] and b[2] < a[4]]

    def layout(*extra):
        out = os.path.join(d, "lay-%d.json" % len(os.listdir(d)))
        rc, o, r = run("board-layout", "--note", note, "--out", out, *extra)
        return rc, o, r, (json.loads(read(out).decode("utf-8")) if rc == 0 and os.path.exists(out) else {})

    rc, out, res, lay = layout()
    flat = [w for b in lay.get("batches", []) for w in b]
    els = apply(lay.get("batches", []), os.path.join(d, "lay-r1")) if lay else {}
    blocks = [w["doc_id"] for w in flat if w.get("data", {}).get("type") == "shape"]
    secs = [w["doc_id"] for w in flat if w.get("data", {}).get("type") == "container"]
    first_of = {k: i for i, k in enumerate(w["doc_id"] for w in flat)}
    check("13.1 a new host board: the meta first, one block per card, step and activity, a section per slice and the "
          "backlog, each written before its cards", rc == 0 and flat and flat[0]["collection"] == "board"
          and res.get("counts", {}).get("new") == len(blocks) + len(secs) + 2 and len(secs) == 4
          and len(res.get("cards", {})) == 18 and all(first_of[res["cards"][c]] > min(first_of[s] for s in secs)
                                                      for c in res.get("cards", {})), (rc, out))
    cards_blocks = [res["cards"][c] for c in res.get("cards", {})]
    check("13.2 no two of the plugin's blocks overlap, and no two sections", els and not overlaps(els, blocks)
          and not overlaps(els, secs), overlaps(els, blocks)[:3] if els else out)
    st1 = os.path.join(d, "lay.artifact.board.json")
    rc, out, res = run("board-state", "--surface", "whiteboard", "--read", os.path.join(d, "lay-r1"), "--note", note, "--out", st1)
    check("13.3 the board it lays out reads back as the map: every card in its slice's section", rc == 0
          and res.get("unmapped_cards") == [] and len(res.get("slices", {})) == 3, out)
    rc, out, res, lay2 = layout("--last", st1, "--now", os.path.join(d, "lay-r1"))
    check("13.4 the same note on the board it laid out writes nothing (a fixed point)", rc == 0
          and lay2.get("batches") == [] and res.get("counts", {}).get("updated") == 0, out)
    # the team adds a note under c2 (R1, column 1) and one below the map; the PM adds a card under c1 and a new step
    r1 = os.path.join(d, "lay-r1")
    sec_r1 = next(k for k in secs if els[k]["text"].startswith("R1"))
    c2 = els[res["cards"]["c2"]] if res.get("cards") else {}
    write(os.path.join(r1, "elements", "team-n1.json"), json.dumps({"type": "note", "x": c2.get("x", 0) + 10,
          "y": c2.get("y", 0) + c2.get("h", 0) + 24, "w": 180, "h": 100, "text": "Ідея команди"}, ensure_ascii=False))
    sec_mvp = next((k for k in secs if els[k]["text"].startswith("MVP")), None)
    write(os.path.join(r1, "elements", "team-n3.json"), json.dumps({"type": "note", "x": 3 * 224 + 6,
          "y": els[sec_mvp]["y"] + 3 if sec_mvp else 0, "w": 180, "h": 180, "text": "картка для тесту"}, ensure_ascii=False))
    bottom = max(els[k]["y"] + els[k]["h"] for k in secs) if els else 0
    write(os.path.join(r1, "elements", "team-n2.json"), json.dumps({"type": "note", "x": 0, "y": bottom + 200, "w": 180,
          "h": 100, "text": "Нотатка під мапою"}, ensure_ascii=False))
    grown = os.path.join(d, "map-grown.md")
    write(grown, read(note).decode("utf-8").replace(
        "| c2 | Обрати доставку |",
        "| c19 | Обрати доставку | Побачити поштомат у кошику | Позначка «найближчий» біля поштомата | mvp |  |  | дошка |  |\n"
        "| c20 | Обрати доставку | Порівняти ціни | Ціни служб доставки поруч | r1 |  |  | дошка |  |\n| c2 | Обрати доставку |", 1))
    out3 = os.path.join(d, "lay-grown.json")
    rc, out, res3 = run("board-layout", "--note", grown, "--last", st1, "--now", r1, "--out", out3)
    lay3 = json.loads(read(out3).decode("utf-8")) if rc == 0 else {}
    flat3 = [w for b in lay3.get("batches", []) for w in b]
    els3 = apply(lay3.get("batches", []), os.path.join(d, "lay-r3"), r1) if lay3 else {}
    own3 = [k for k, v in els3.items() if v.get("type") in ("shape", "container") and not k.startswith("team-")]
    check("13.5 a new card and a new step: the columns widen and the section grows — nothing of the plugin overlaps",
          rc == 0 and res3.get("counts", {}).get("new") == 3 and els3
          and not overlaps(els3, [k for k in own3 if els3[k]["type"] == "shape"])
          and not overlaps(els3, [k for k in own3 if els3[k]["type"] == "container"]), (out, overlaps(els3, own3)[:3]))
    check("13.6 nothing is deleted, and the team's notes only move (x, y) — their text is theirs",
          all(w["op"] in ("set", "update") for w in flat3)
          and all(set(w["data"]) <= {"x", "y"} for w in flat3 if w["doc_id"].startswith("team-"))
          and els3.get("team-n1", {}).get("text") == "Ідея команди", [w for w in flat3 if w["doc_id"].startswith("team-")])
    st3 = os.path.join(d, "lay3.artifact.board.json")
    rc, out, res = run("board-state", "--surface", "whiteboard", "--read", os.path.join(d, "lay-r3"), "--note", grown,
                       "--out", st3)
    s3 = json.loads(read(st3).decode("utf-8"))["elements"] if rc == 0 else {}
    n1 = s3.get("team-n1", {})
    col = [k for k, v in s3.items() if v.get("role") == "card" and v.get("card") == "c2"]
    check("13.7 the team's note stays in its section and column, under its card, overlapping no card of the plugin",
          n1.get("frame") == sec_r1 and n1.get("role") == "sticky" and col and abs(s3[col[0]]["x"] - n1["x"] + 10) < 1
          and not overlaps(els3, ["team-n1"] + [k for k, v in s3.items() if v.get("role") == "card"]), (n1, col))
    sec_bottom = max(els3[k]["y"] + els3[k]["h"] for k in own3 if els3[k]["type"] == "container") if els3 else 0
    check("13.8 a note below the map moves down with its edge — the gap stays as it was",
          els3 and abs((els3["team-n2"]["y"] - sec_bottom) - 200) < 1, (els3.get("team-n2"), sec_bottom))
    check("13.9 every card of the grown map is on the board", rc == 0 and res.get("unmapped_cards") == [], out)
    n3 = s3.get("team-n3", {})
    st_col = [v for v in s3.values() if v.get("role") == "step" and v.get("text") == "Оплатити при отриманні"]
    check("13.11 a note in a later column moves right with its column when a step is added before it, at the same "
          "height in its section; the section grows to hold it, its numbers whole",
          n3.get("frame") == sec_mvp and st_col and abs(n3["x"] - st_col[0]["x"] - 6) < 1 and abs(n3["ry"] - 3) < 1
          and els3[sec_mvp]["h"] >= 3 + 180 + 24 and all(isinstance(els3[k][f], int) for k in own3 for f in ("x", "y", "w", "h")),
          (n3, st_col[:1], els3.get(sec_mvp)))
    rc, out, res, _ = layout("--last", st1)
    rc2, out2, res2 = run("board-layout", "--note", note, "--last", st1, "--now", wp, "--out", os.path.join(d, "lay-p.json"))
    check("13.10 no layout without a fresh whole read, nor from a partial or another board's read (exit 2)",
          rc == 2 and rc2 == 2 and "partial" in res2.get("error", "") and not os.path.exists(os.path.join(d, "lay-p.json")),
          (out, out2))
    mm = mutant(d, "nogrow", 'inner = max([g["card_min"]] + heights)', 'inner = g["card_min"]')
    if mm is None:
        check("13.M1 mutation site present (a section as tall as its tallest cell)", False, "pattern not in story_map.py")
    else:
        mo = os.path.join(d, "lay-m1.json")
        rc, out, res = run("board-layout", "--note", grown, "--out", mo, script=mm)
        em = apply(json.loads(read(mo).decode("utf-8"))["batches"], os.path.join(d, "lay-m1")) if rc == 0 else {}
        check("13.M1 a section that does not grow with its cells is caught (13.2: its cards overlap the next section's)",
              bool(em) and bool(overlaps(em, [k for k, v in em.items() if v.get("type") == "shape"])), out)
    n, bad = replay(SCRIPT, "after12")
    check("12.16 after the host's board the Miro replay is still byte for byte (%d cases)" % n, n >= 14 and not bad, bad)
finally:
    shutil.rmtree(d, ignore_errors=True)
    shutil.rmtree(SAFE_HOME, ignore_errors=True)

print("\nRESULT: %s (%d failed)" % ("GREEN ✅" if not fails else "RED ❌", fails))
sys.exit(1 if fails else 0)
