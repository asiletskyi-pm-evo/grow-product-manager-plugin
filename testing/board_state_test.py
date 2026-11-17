#!/usr/bin/env python3
"""TC-board-4800 — scripts/board_state.py, a board read back in one item format (v4.8.0).

Fictional «Zorg» boards (testing/fixtures/board/, testing/fixtures/story-map/):
- read_miro_svg: the story map's board SVG reads as before the move (the items of story_map.read_board at v4.7.0,
  checked byte for byte through story-map-golden.json in story_map_test.py; here the item fields and frames);
- read_whiteboard: the host board type's `list elements`, saved inline ({id, data, …} rows) or one file per element
  (an out_dir folder) — a section is a frame, a person's `note` and the plugin's rounded shape are stickies, an
  element sits in the SMALLEST section that holds its centre, its place relative to that section; an element's
  author, author id, votes and anything else it carries never reach an item;
- read_board / read_boards: the reader by the file (or the surface named), the first read of an element wins;
- scope: the area to read back around the items;
- a read that does not parse is Bad, never a crash.
Mutations: a reader that takes the first section holding the centre instead of the smallest, and one that keeps the
element's author, are each caught. Stdlib only; run from the repo root:

  env -u GROW_PM_CONTEXT_PATH -u GROW_PM_PROVIDER_PATHS python3 testing/board_state_test.py
"""
import importlib.util, json, os, shutil, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
FIX = os.path.join(ROOT, "testing", "fixtures")

fails = 0


def check(name, cond, detail=""):
    global fails
    fails += not cond
    print(("✅" if cond else "❌"), name, ("" if cond else "-> " + str(detail)[:900]))


def load(path, name="board_state"):
    if not os.path.exists(path):
        return None
    sys.path.insert(0, os.path.dirname(path))
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        sys.path.pop(0)


def mutant(d, tag, old, new):
    """board_state.py with `old` → `new`, in a folder of its own (with its sibling modules); None when `old` is absent."""
    src = open(os.path.join(SCRIPTS, "board_state.py"), encoding="utf-8").read()
    if old not in src:
        return None
    mdir = os.path.join(d, "mut-" + tag)
    os.makedirs(mdir)
    for f in os.listdir(SCRIPTS):
        if f.endswith(".py"):
            shutil.copy(os.path.join(SCRIPTS, f), mdir)
    with open(os.path.join(mdir, "board_state.py"), "w", encoding="utf-8") as fh:
        fh.write(src.replace(old, new, 1))
    return load(os.path.join(mdir, "board_state.py"), "board_state_" + tag)


bs = load(os.path.join(SCRIPTS, "board_state.py"))
check("0.1 scripts/board_state.py exists and imports", bs is not None, "missing")
if bs is None:
    print("\nRESULT: RED ❌ (%d failed)" % fails)
    sys.exit(1)

d = tempfile.mkdtemp(prefix="board-state-test-")
try:
    B = os.path.join(FIX, "board")
    last = os.path.join(FIX, "story-map", "board-last.svg")

    # 1. Miro SVG
    it = bs.read_miro_svg(last)
    check("1.1 read_miro_svg reads every element with a data-miro-id", len(it) == 12 and "3458764000000003001" in it, len(it))
    c1 = it.get("3458764000000003001", {})
    check("1.2 a sticky: kind, text without markup, absolute and frame-relative place, its frame",
          c1.get("kind") == "sticky" and c1.get("text") == "Поштомат як спосіб доставки в кошику PROJ-1234.1"
          and (c1.get("x"), c1.get("y"), c1.get("rx"), c1.get("ry")) == (20.0, 620.0, 20.0, 20.0)
          and c1.get("frame") == "3458764000000001002" and c1.get("frame_text", "").startswith("MVP"), c1)
    fr = it.get("3458764000000001002", {})
    check("1.3 a frame: kind frame, its title, its size", fr.get("kind") == "frame" and fr.get("text", "").startswith("MVP")
          and fr.get("w") == 2000.0 and fr.get("h") == 280.0, fr)
    check("1.4 one item format: id kind text x y rx ry w h frame frame_text",
          all(set(v) == {"id", "kind", "text", "x", "y", "rx", "ry", "w", "h", "frame", "frame_text"} for v in it.values()),
          [sorted(v) for v in it.values()][:2])

    # 2. the host board type's element list, inline
    wb = bs.read_whiteboard(os.path.join(B, "wb-basic.json"))
    check("2.1 read_whiteboard reads every element of the list", len(wb) == 12, sorted(wb))
    sec = wb.get("e4", {})
    check("2.2 a section is a frame with its title", sec.get("kind") == "frame" and sec.get("text") == "s2 · болі"
          and (sec.get("w"), sec.get("h")) == (360.0, 220.0), sec)
    note = wb.get("mwkxzorg-1a2b3", {})
    check("2.3 a person's note is a sticky; its words with the spaces collapsed", note.get("kind") == "sticky"
          and note.get("type") == "note" and note.get("text") == "Немає оплати частинами", note)
    check("2.4 it sits in the SMALLEST section that holds its centre (s2 · болі), not the outer one",
          note.get("frame") == "e4" and note.get("frame_text") == "s2 · болі", (note.get("frame"), note.get("frame_text")))
    check("2.5 its place is absolute and relative to its section", (note.get("x"), note.get("y")) == (433.5, 150.25)
          and (note.get("rx"), note.get("ry")) == (33.5, 30.25), note)
    blob = json.dumps(wb, ensure_ascii=False)
    check("2.6 an author's name and id never reach an item", "Zorg QA" not in blob and "u_ZorgQa" not in blob
          and not any(k in v for v in wb.values() for k in ("author", "authorId", "tilt", "color")), blob[:300])
    st = wb.get("e6", {})
    check("2.7 the plugin's rounded shape is a sticky in its section", st.get("kind") == "sticky" and st.get("type") == "shape"
          and st.get("frame") == "e3" and st.get("frame_text") == "s1 · болі", st)
    check("2.8 a second line stays in the text as one line", wb.get("e7", {}).get("text") == "visit → search: 41% (база 45%) health-check",
          wb.get("e7"))
    check("2.9 another shape is a shape, not a sticky", wb.get("e8", {}).get("kind") == "shape", wb.get("e8"))
    check("2.10 an arrow is a connector with its label, placed nowhere", wb.get("e9", {}).get("kind") == "connector"
          and wb.get("e9", {}).get("text") == "веде до" and wb.get("e9", {}).get("frame") is None, wb.get("e9"))
    check("2.11 a section inside a bigger section has that section as its frame", wb.get("e3", {}).get("frame") == "e2"
          and wb.get("e2", {}).get("frame") is None, (wb.get("e3"), wb.get("e2")))
    check("2.12 a note outside every grid section sits in the outer one", wb.get("mwkxzorg-9z8y7", {}).get("frame") == "e2", wb.get("mwkxzorg-9z8y7"))
    check("2.13 a text with no size sits by its point (outside every section: no frame)", wb.get("e1", {}).get("frame") is None
          and wb.get("e1", {}).get("kind") == "text", wb.get("e1"))
    check("2.14 one item format, plus the element's own type",
          all(set(v) == {"id", "kind", "text", "x", "y", "rx", "ry", "w", "h", "frame", "frame_text", "type"} for v in wb.values()),
          [sorted(v) for v in wb.values()][:2])

    # 3. the out_dir form: one file per element, the data only, the id the file's name
    wd = bs.read_whiteboard(os.path.join(B, "wb-dir"))
    check("3.1 a folder of <id>.json files (or its elements/ subfolder) reads the same items",
          sorted(wd) == sorted(["e1", "e2", "e3", "e4", "e5", "e6", "e7", "mwkxzorg-1a2b3"])
          and wd.get("mwkxzorg-1a2b3") == wb.get("mwkxzorg-1a2b3"), sorted(wd))
    check("3.2 the elements/ folder itself reads the same", bs.read_whiteboard(os.path.join(B, "wb-dir", "elements")) == wd, "")
    dict_form = os.path.join(d, "wb-dict.json")
    with open(os.path.join(B, "wb-basic.json"), encoding="utf-8") as fh:
        rows = json.load(fh)
    with open(dict_form, "w", encoding="utf-8") as fh:
        json.dump({"elements": {r["id"]: r["data"] for r in rows}}, fh, ensure_ascii=False)
    check("3.3 a mapping id → element (under `elements`) reads the same", bs.read_whiteboard(dict_form) == wb, "")

    # 4. dispatch, merge, scope
    check("4.1 read_board: .svg is a Miro board, .json or a folder the host board type's list",
          bs.read_board(last) == it and bs.read_board(os.path.join(B, "wb-basic.json")) == wb
          and bs.read_board(os.path.join(B, "wb-dir")) == wd, "")
    check("4.2 a surface named wins over the file name", bs.read_board(os.path.join(B, "wb-basic.json"), "whiteboard") == wb, "")
    two = os.path.join(d, "wb-second.json")
    with open(two, "w", encoding="utf-8") as fh:
        json.dump([{"id": "mwkxzorg-1a2b3", "data": dict(rows[9]["data"], text="Друге читання")},
                   {"id": "e99", "data": {"type": "note", "x": 0, "y": 900, "w": 180, "h": 180, "text": "ще"}}], fh, ensure_ascii=False)
    merged = bs.read_boards([os.path.join(B, "wb-basic.json"), two])
    check("4.3 read_boards: the first read of an element wins, a new one is added",
          merged["mwkxzorg-1a2b3"]["text"] == "Немає оплати частинами" and "e99" in merged and len(merged) == 13, len(merged))
    sc = bs.scope(wb)
    check("4.4 scope: the items' box with a margin", sc == {"x": -40 - bs.SCOPE_MARGIN, "y": -bs.SCOPE_MARGIN,
                                                          "width": 1600 + 2 * bs.SCOPE_MARGIN, "height": 980 + 2 * bs.SCOPE_MARGIN}, sc)
    check("4.5 scope of nothing is None", bs.scope({}) is None, "")

    # 5. what does not read
    bad = os.path.join(d, "bad.json")
    with open(bad, "w", encoding="utf-8") as fh:
        fh.write("[{\"id\": ")
    for name, path in (("5.1 a list that is not JSON", bad), ("5.2 a file that is not there", os.path.join(d, "gone.json"))):
        try:
            bs.read_whiteboard(path)
            check(name + " is Bad", False, "no error")
        except bs.Bad:
            check(name + " is Bad", True)
    odd = os.path.join(d, "odd.json")
    with open(odd, "w", encoding="utf-8") as fh:
        json.dump([{"id": "e1", "data": "not an element"}, {"data": {"type": "note"}}, {"id": "e2", "data": {"type": "note", "x": "a", "y": 1, "text": 5}}], fh)
    try:
        o = bs.read_whiteboard(odd)
        check("5.3 a row without an id or with no element object is skipped; a non-number place is 0, a non-text text empty",
              list(o) == ["e2"] and o["e2"]["x"] == 0.0 and o["e2"]["text"] == "", o)
    except bs.Bad as e:
        check("5.3 odd rows do not stop the read", False, e)
    try:
        bs.read_miro_svg(bad)
        check("5.4 an SVG that does not parse is Bad", False, "no error")
    except bs.Bad:
        check("5.4 an SVG that does not parse is Bad", True)

    # 7. review 1 (frozen 5e67bdf): each finding reproduced first
    def bad(name, payload):
        f = os.path.join(d, name + ".json")
        with open(f, "w", encoding="utf-8") as fh:
            fh.write(payload if isinstance(payload, str) else json.dumps(payload))
        try:
            got = bs.read_whiteboard(f)
            return "no error: %d items" % len(got)
        except bs.Bad:
            return True
    check("7.1 I-5 an error payload is Bad, never an empty board", bad("err", {"error": "rate limited"}) is True, bad("err", {"error": "rate limited"}))
    check("7.2 I-5 a single {id, data} record is Bad, not an element named «data»",
          bad("one", {"id": "e1", "data": {"type": "note", "x": 0, "y": 0, "text": "t"}}) is True, "")
    check("7.3 I-5 rows none of which is an element is Bad", bad("none", [{"id": "e1", "data": {"oops": 1}}]) is True, "")
    check("7.4 I-5 `elements` that is not a collection is Bad", bad("elnum", {"elements": 5}) is True, "")
    emp = os.path.join(d, "empty.json")
    with open(emp, "w", encoding="utf-8") as fh:
        fh.write("[]")
    check("7.5 an empty list is an empty board (the command decides)", bs.read_whiteboard(emp) == {}, "")
    lw = bs.read_whiteboard(os.path.join(B, "wb-basic.json"), lines=True)
    check("7.6 I-1 lines=True keeps a sticky's line break (the second line stays apart)",
          lw.get("e7", {}).get("text") == "visit → search: 41% (база 45%)\nhealth-check" and wb.get("e7", {}).get("text") == "visit → search: 41% (база 45%) health-check",
          lw.get("e7"))
    lm = bs.read_miro_svg(last, lines=True)
    check("7.7 I-1 lines=True on a Miro SVG: <br> is a line break; the default keeps the story map's one line",
          lm.get("3458764000000003001", {}).get("text") == "Поштомат як спосіб доставки в кошику\nPROJ-1234.1"
          and it.get("3458764000000003001", {}).get("text") == "Поштомат як спосіб доставки в кошику PROJ-1234.1", lm.get("3458764000000003001"))
    nan = os.path.join(d, "nan.json")
    with open(nan, "w", encoding="utf-8") as fh:
        fh.write('[{"id": "e1", "data": {"type": "note", "x": NaN, "y": Infinity, "w": 10, "h": 10, "text": "t"}}]')
    try:
        nn = bs.read_whiteboard(nan)
        check("7.8 M-4 a non-finite place reads as 0 and scope does not crash", nn["e1"]["x"] == 0.0 and bs.scope(nn) is not None, nn)
    except (bs.Bad, ValueError) as e:
        check("7.8 M-4 a non-finite place reads as 0 and scope does not crash", False, e)

    # 6. mutations
    m1 = mutant(d, "first", "key=lambda c: c[\"w\"] * c[\"h\"]", "key=lambda c: 0")
    if m1 is None:
        check("6.1 M1 mutation site present (the smallest section)", False, "pattern not found")
    else:
        n1 = m1.read_whiteboard(os.path.join(B, "wb-basic.json")).get("mwkxzorg-1a2b3", {})
        check("6.1 M1 a reader taking the first section, not the smallest, is caught by 2.4", n1.get("frame") != "e4", n1)
    m2 = mutant(d, "author", "out = {\"id\": eid", "out = {\"author\": data.get(\"author\"), \"id\": eid")
    if m2 is None:
        check("6.2 M2 mutation site present (the item built from fields named)", False, "pattern not found")
    else:
        b2 = json.dumps(m2.read_whiteboard(os.path.join(B, "wb-basic.json")), ensure_ascii=False)
        check("6.2 M2 a reader that keeps the author is caught by 2.6", "Zorg QA" in b2, b2[:200])
finally:
    shutil.rmtree(d, ignore_errors=True)

print("\nRESULT: %s (%d failed)" % ("GREEN ✅" if not fails else "RED ❌", fails))
sys.exit(1 if fails else 0)
