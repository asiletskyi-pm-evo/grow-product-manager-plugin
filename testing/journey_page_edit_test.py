#!/usr/bin/env python3
"""TC-journey-4110-page — editing the journey map on its page (v4.11.0, references/journey-protocol.md §9, §12, §14).

The fictional «Zorg» maps (testing/fixtures/journey/) are copied into a temp folder.

- the page (§9): the switch «Редагувати» on every page, the published one too; one more fixed script (EDIT) — the same
  bytes whatever the note, no request, no data of a note; what it edits read from the markup's attributes (the map's
  name and digest, each cell's stage and lane, each row's id, parent, code, target and lock); a health-check, metric or
  anomaly row locked; without its editing (`strip_edit`) the page is the v4.10.0 golden byte for byte.
- page-diff (§9): the file of edits, or a text holding it, checked as another person's input — its kind, version, size,
  product and root; a map changed since the page is `stale`, an unknown map, row or op named; texts page-safe; each op
  in board-diff's categories plus relinked, recoded, retargeted; a health-check row's edit is hc_edits.
- board-take (§12): the page's text and new rows take «сторінка команди <date>» and the PM's class; a parent, a code and
  a target checked as `check` would (bad_parent, orphan, bad_code, bad_target); a removed row only on --drop; a secret
  refused, a link and a contact removed; every other byte of the note kept.
- the tree page (§14): a child's row edited on the root's page goes into the child's note alone; another map's entries
  are other_note; two pages that changed one row differently are a conflict — one version or none.
- check 28 / 29 drift: «Editing on the page», the ops table, §15's «A request from the page», Step J9, the page's source.
- a browser pass (when Playwright is installed): the switch, a row edited, a row added, the copy — the JSON the page
  hands over is what page-diff reads.
Mutations — the digest not checked, a parent not checked, the page's source lost, the lock lost, a request in the
script — each go red. Stdlib only (the browser pass skipped without Playwright); run from the repo root:

  env -u GROW_PM_CONTEXT_PATH -u GROW_PM_PROVIDER_PATHS python3 testing/journey_page_edit_test.py
"""
import json, os, re, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "journey_map.py")
FIX = os.path.join(ROOT, "testing", "fixtures", "journey")
GOLD = os.path.join(FIX, "nest", "golden")
sys.path.insert(0, os.path.dirname(SCRIPT))
import journey_map as jm  # noqa: E402

fails = 0


def check(name, cond, detail=""):
    global fails
    fails += not cond
    print(("✅" if cond else "❌"), name, ("" if cond else "-> " + str(detail)[:900]))


SAFE_HOME = tempfile.mkdtemp(prefix="journey-page-home-")


def run(*args, script=SCRIPT, timeout=60):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GROW_PM_")}
    env["HOME"] = SAFE_HOME
    try:
        p = subprocess.run([sys.executable, script] + list(args), capture_output=True, text=True, env=env, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, "timeout after %ds" % timeout, {}
    res = {}
    for line in p.stdout.splitlines():
        if line.startswith("JOURNEY_RESULT "):
            res = json.loads(line[len("JOURNEY_RESULT "):])
    return p.returncode, p.stdout + p.stderr, res


def text(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def write(p, s):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="") as f:
        f.write(s)


def date_free(s):
    return re.sub(r"(Згенеровано|Generated): \d{4}-\d{2}-\d{2}", r"\1: DATE", s)


def mutant(d, name, old, new):
    sdir = os.path.dirname(SCRIPT)
    src = text(os.path.join(sdir, "journey_map.py"))
    if old not in src:
        return None
    mdir = os.path.join(d, "mut-" + name)
    os.makedirs(mdir)
    for f in os.listdir(sdir):
        if f.endswith(".py"):
            shutil.copy(os.path.join(sdir, f), mdir)
    write(os.path.join(mdir, "journey_map.py"), src.replace(old, new, 1))
    return os.path.join(mdir, "journey_map.py")


def edits(note_path, ops, root="journey-first-order", product="zorg", maps=None, digest=None):
    n = jm.load(note_path)
    name = os.path.splitext(os.path.basename(note_path))[0]
    body = maps or {name: {"digest": digest or jm.table_sig(n)["table"], "edits": ops}}
    return {"kind": "journey-page-edits", "version": 1, "product": product, "root": root, "made": "2026-12-01", "maps": body}


def put(d, name, data, words=False):
    p = os.path.join(d, name)
    raw = json.dumps(data, ensure_ascii=False, indent=1)
    write(p, ("Ось правки зі сторінки:\n" + raw + "\nДякую!") if words else raw)
    return p


def rows_of(path):
    return {r["id"]: r for r in jm.load(path)["rows"] if r["id"]}


d = tempfile.mkdtemp(prefix="journey-page-test-")
try:
    main_src = os.path.join(FIX, "journey-first-order.md")
    note = os.path.join(d, "m", "journey-first-order.md")
    write(note, text(main_src))
    before = text(note)

    # 1. the page (§9)
    pu, pe = os.path.join(d, "p-uk.html"), os.path.join(d, "p-en.html")
    rc, out, res = run("render-html", "--note", note, "--out", pu, "--lang", "uk")
    rc2, out2, _ = run("render-html", "--note", note, "--out", pe, "--lang", "en")
    hu, he = (text(pu) if os.path.exists(pu) else ""), (text(pe) if os.path.exists(pe) else "")
    check("1.1 render-html: exit 0, the switch «Редагувати» on the page", rc == 0 and rc2 == 0
          and '<button type="button" class="edit-toggle">Редагувати</button>' in hu
          and '<button type="button" class="edit-toggle">Edit</button>' in he, out[-300:])
    scripts_u, scripts_e = re.findall(r"<script>(.*?)</script>", hu, re.S), re.findall(r"<script>(.*?)</script>", he, re.S)
    check("1.2 two fixed scripts — the pan and EDIT — the same bytes in both languages (no data of a note)",
          scripts_u == [jm.PAN, jm.EDIT] and scripts_e == scripts_u, [len(x) for x in scripts_u])
    check("1.3 EDIT sends nothing: no fetch, XMLHttpRequest, sendBeacon, WebSocket, import, src= or http",
          not re.search(r"fetch|XMLHttpRequest|sendBeacon|WebSocket|import\(|src=|https?:|\.open\(", jm.EDIT),
          re.findall(r".{20}(?:fetch|XMLHttp|http|src=).{20}", jm.EDIT)[:3])
    check("1.4 EDIT holds no word of the note — its journey, a stage, a row", not any(w in jm.EDIT for w in (
        "Zorg", "zorg", "Перше замовлення", "s3", "Фільтри", "o2", "journey-first-order")), "")
    check("1.5 without its editing the page is the v4.10.0 golden byte for byte (uk and en)",
          date_free(jm.strip_edit(hu)) == text(os.path.join(GOLD, "page-uk-first-order.html"))
          and date_free(jm.strip_edit(he)) == text(os.path.join(GOLD, "page-en-first-order.html")), "")
    sig = jm.table_sig(jm.load(note))["table"]
    check("1.6 the grid's frame names its map and the digest of its rows", 'data-map="journey-first-order" data-digest="%s"' % sig in hu, sig)
    check("1.7 each cell names its stage, lane and title", 'data-stage="s3" data-lane="pain" data-title="s3 · болі"' in hu
          and 'data-stage="s3" data-lane="pain" data-title="s3 · pains"' in he, "")
    check("1.8 a row names its id, lane, parent and code; the target opportunity says so",
          'data-row="i1" data-lane="initiative" data-parent="p2" data-code="PROJ-1234"' in hu
          and re.search(r'data-row="o2" data-lane="opportunity" data-target="1"', hu) is not None, "")
    locked = set(re.findall(r'data-row="([^"]+)"[^>]*data-locked="1"', hu))
    check("1.9 every health-check, metric and anomaly row is locked, nothing else",
          locked == {"m-s1-visit-search", "m-s2-search-cart", "a-s2-search-cart", "m-s3-cart-checkout", "m-s4-checkout-payment"}, locked)
    check("1.10 the bar's words come from the page's language, in its attributes", 'data-l-copied="Скопійовано' in hu
          and 'data-l-copied="Copied' in he and 'data-root="journey-first-order"' in hu and 'data-product="zorg"' in hu, "")
    check("1.11 the page says it sends nothing and how the edits come back", "Сторінка нічого не надсилає" in hu
          and "забери правки зі сторінки карти шляху" in hu, "")
    xss = os.path.join(d, "x", "journey-first-order.md")
    write(xss, before.replace("| i1 | s3 | | initiative | Епік «Прозора доставка» | | | p2 | PROJ-1234 |",
                              '| i1 | s3 | | initiative | Епік «Прозора доставка» | | | p2" onclick="x | PROJ-1234 |'))
    run("render-html", "--note", xss, "--out", os.path.join(d, "x.html"), "--lang", "uk")
    hx = text(os.path.join(d, "x.html")) if os.path.exists(os.path.join(d, "x.html")) else ""
    check("1.12 an attribute value is escaped — a quote never opens an attribute of its own", 'onclick="x' not in hx
          and "p2&quot; onclick=&quot;x" in hx, re.findall(r'data-row="i1"[^>]*>', hx)[:1])

    # 2. page-diff (§9)
    ops = [{"op": "text", "row": "p1", "text": "Фільтри скидаються після кроку назад"},
           {"op": "move", "row": "e2", "stage": "s3", "lane": "experience"},
           {"op": "parent", "row": "i1", "parent": "o2"},
           {"op": "code", "row": "i1", "code": "PROJ-77"},
           {"op": "target", "row": "o1", "target": True},
           {"op": "remove", "row": "t1"},
           {"op": "text", "row": "m-s1-visit-search", "text": "60%"},
           {"op": "add", "id": "p1", "stage": "s3", "lane": "solution", "text": "Ще одне рішення https://evil.example/x", "parent": "o2"},
           {"op": "add", "id": "p2", "stage": "s3", "lane": "initiative", "text": "Нова ініціатива", "code": "PROJ-88", "parent": "o2"},
           {"op": "text", "row": "e1", "text": jm.nt.safe(rows_of(note)["e1"]["text"])}]
    ef = put(d, "e1.json", edits(note, ops), words=True)
    df = os.path.join(d, "d1.json")
    rc, out, res = run("page-diff", "--note", note, "--edits", ef, "--out", df)
    check("2.1 page-diff reads the file inside a pasted text: exit 0, a diff of the page", rc == 0 and res.get("state") == "diff"
          and res.get("surface") == "page" and os.path.exists(df), out[-300:])
    c = res.get("counts", {})
    check("2.2 each op in its category — the board's and the links of v4.11.0", (c.get("changed"), c.get("moved"), c.get("added"),
          c.get("removed"), c.get("relinked"), c.get("recoded"), c.get("retargeted"), c.get("hc_edits")) == (1, 1, 2, 1, 1, 1, 1, 1), c)
    check("2.3 an unchanged text is no edit; one element per row (i1's parent and code share it)",
          not any(e.get("row") == "e1" for e in res.get("changed", []))
          and [e["id"] for e in res.get("relinked", [])] == [e["id"] for e in res.get("recoded", [])], res.get("relinked"))
    check("2.4 every entry is the page's, texts page-safe", all(e.get("via") == "page" for k in jm.DIFF_CATEGORIES for e in res.get(k, []))
          and "evil.example" not in json.dumps(res, ensure_ascii=False) and "[link removed]" in json.dumps(res, ensure_ascii=False), "")
    check("2.5 the note is untouched by page-diff", text(note) == before, "")
    check("2.6 the diff names the note as it is now (board-take checks it)", res.get("note") == jm.table_sig(jm.load(note)), res.get("note"))
    stale = put(d, "stale.json", edits(note, ops[:1], digest="0000000000000000"))
    rc, out, res = run("page-diff", "--note", note, "--edits", stale)
    check("2.7 a page older than the note: `stale`, nothing of it read", rc == 0 and res.get("counts", {}).get("changed") == 0
          and [s["why"] for s in res.get("skipped", [])] == ["stale"], res.get("skipped"))
    odd = edits(note, [{"op": "text", "row": "zz9", "text": "x"}, {"op": "rename", "row": "p1"}, {"op": "add", "stage": "s1"},
                       {"op": "code", "row": "i1"}, {"op": "text", "row": "p1", "text": 5 * "x" * 1000}])
    odd["maps"]["journey-elsewhere"] = {"digest": "x", "edits": []}
    rc, out, res = run("page-diff", "--note", note, "--edits", put(d, "odd.json", odd))
    whys = sorted(s["why"] for s in res.get("skipped", []))
    check("2.8 an unknown row, op, map and a broken or too long edit are named, never read", rc == 0
          and whys == ["bad_edit", "bad_edit", "bad_edit", "unknown_map", "unknown_row"] and res.get("counts", {}).get("changed") == 0, whys)
    for n_, data, want in (("2.9 another kind", dict(edits(note, []), kind="journey-board"), "not a file of edits"),
                           ("2.10 another version", dict(edits(note, []), version=2), "version"),
                           ("2.11 another product", edits(note, [], product="acme"), "another product"),
                           ("2.12 another page's root", edits(note, [], root="journey-payment"), "journey-payment")):
        rc, out, res = run("page-diff", "--note", note, "--edits", put(d, "bad.json", data))
        check(n_ + " is refused: exit 2, its reason", rc == 2 and want in (res.get("error") or ""), res.get("error"))
    big = os.path.join(d, "big.json")
    write(big, json.dumps(edits(note, [])) + " " * (jm.EDIT_MAX_BYTES + 1))
    rc, out, res = run("page-diff", "--note", note, "--edits", big)
    check("2.13 a file past 2 MB is refused unread", rc == 2 and "larger" in (res.get("error") or ""), res.get("error"))
    rc, out, res = run("page-diff", "--note", note, "--edits", put(d, "junk.json", {"hello": 1}))
    check("2.14 a text without a file of edits is refused", rc == 2 and "not a file of edits" in (res.get("error") or ""), res.get("error"))

    # 3. board-take of the page's diff (§12)
    d1 = json.loads(text(df))
    el = {e["row"]: e["id"] for k in ("changed", "moved", "removed", "relinked", "retargeted", "hc_edits") for e in d1[k]}
    adds = [e["id"] for e in d1["added"]]
    take = [el["p1"], el["e2"], el["i1"], el["o1"], el["t1"], el["m-s1-visit-search"]] + adds
    rc, out, res = run("board-take", "--note", note, "--diff", df, "--take", *take, "--dry-run")
    check("3.1 the preview: nothing written, the class of the changed pain asked, never guessed", rc == 0 and text(note) == before
          and [a["row"] for a in res.get("ask_class", [])] == ["p1"], res.get("ask_class"))
    refused = {(r["id"], r["why"]) for r in res.get("refused", [])}
    check("3.2 a health-check row is refused; a removed row needs --drop", (el["m-s1-visit-search"], "health_check") in refused
          and (el["t1"], "needs_drop") in refused, refused)
    rc, out, res = run("board-take", "--note", note, "--diff", df, "--take", *take, "--class", "%s=observed" % el["p1"],
                       "--drop", "t1", "--date", "2026-12-01")
    r = rows_of(note)
    check("3.3 the take: exit 0, the note written", rc == 0 and res.get("note_written") is True, out[-300:])
    check("3.4 a text the page changed: its words, «сторінка команди <date>», the PM's class, the date",
          (r["p1"]["text"], r["p1"]["source"], r["p1"]["class"], r["p1"]["date"]) == (
              "Фільтри скидаються після кроку назад", "сторінка команди 2026-12-01", "observed", "2026-12-01"), r["p1"])
    check("3.5 a move keeps the row's source and class", (r["e2"]["stage"], r["e2"]["source"]) == ("s3", "feedback-triage 2026-10-30, тема «доставка», pain 7.5"), r["e2"])
    check("3.6 links: i1 hangs under o2 with PROJ-77; o1 is s2's target — no source or class changed by a link",
          (r["i1"]["parent"], r["i1"]["code"], r["i1"]["source"]) == ("o2", "PROJ-77", "roadmap-architect PROJ-1234")
          and r["o1"]["target"] == "так", (r["i1"], r["o1"]["target"]))
    check("3.7 the removed row is gone (--drop); the health-check row untouched", "t1" not in r
          and r["m-s1-visit-search"]["text"] == rows_of(main_src)["m-s1-visit-search"]["text"], "")
    new = [x for x in r.values() if x["id"].startswith("b")]
    check("3.8 the added rows: page-safe text, the page's parent and code, «сторінка команди <date>»",
          sorted((x["lane"], x["text"], x["parent"], x["code"], x["source"]) for x in new) == sorted([
              ("solution", "Ще одне рішення", "o2", "", "сторінка команди 2026-12-01"),
              ("initiative", "Нова ініціатива", "o2", "PROJ-88", "сторінка команди 2026-12-01")]), [(x["text"], x["code"]) for x in new])
    check("3.9 a link the page had is named, never written", any(n["why"] == "link_removed" for n in res.get("named", [])), res.get("named"))
    keep = [l for l in before.split("\n") if not re.match(r"\| (p1|e2|i1|o1|t1) \|", l)]
    check("3.10 every other line of the note byte for byte", all(l in text(note).split("\n") for l in keep), "")
    rc, out, res = run("page-diff", "--note", note, "--edits", ef)
    check("3.11 the same file again: the map changed — stale, nothing taken twice", [s["why"] for s in res.get("skipped", [])] == ["stale"], res.get("skipped"))

    # 4. the links checked as `check` would (§5)
    n2 = os.path.join(d, "n2", "journey-first-order.md")
    write(n2, before)
    bad = [{"op": "parent", "row": "p2", "parent": "o1"},          # o1 is on s2, p2 on s3
           {"op": "parent", "row": "h1", "parent": ""},            # a solution without a parent
           {"op": "parent", "row": "a1", "parent": "o2"},          # an action takes no parent
           {"op": "code", "row": "i1", "code": "проєкт 5"},
           {"op": "code", "row": "p2", "code": "PROJ-9"},
           {"op": "target", "row": "p3", "target": True},          # a pain
           {"op": "add", "id": "p1", "stage": "s3", "lane": "opportunity", "text": "Друга ціль", "target": True},
           {"op": "add", "id": "p2", "stage": "s3", "lane": "initiative", "text": "Ще ініціатива", "code": "ghp_" + "A1b2C3d4" * 5}]
    df2 = os.path.join(d, "d2.json")
    run("page-diff", "--note", n2, "--edits", put(d, "e2.json", edits(n2, bad)), "--out", df2)
    d2 = json.loads(text(df2)) if os.path.exists(df2) else {}
    ids = sorted({e["id"] for k in jm.DIFF_CATEGORIES for e in d2.get(k, [])})
    rc, out, res = run("board-take", "--note", n2, "--diff", df2, "--take", *ids, "--dry-run")
    named = sorted((n["row"] or "", n["why"]) for n in res.get("named", []) if n["why"] in ("bad_parent", "orphan", "bad_code", "bad_target"))
    check("4.1 a parent on another stage, a solution left without one, a parent on an action: bad_parent, orphan, bad_parent",
          ("p2", "bad_parent") in named and ("h1", "orphan") in named and ("a1", "bad_parent") in named, named)
    check("4.2 a code that is none, and a code on a pain: bad_code", ("i1", "bad_code") in named and ("p2", "bad_code") in named, named)
    check("4.3 a target on a pain, a second target on s3: bad_target", ("p3", "bad_target") in named
          and any(w == "bad_target" and rw.startswith("b") for rw, w in named), named)
    check("4.4 a secret in a code is never written (bad_code), nothing applied of the refused links", not any(
        a.get("action") in ("parent", "code", "target") for a in res.get("applied", [])), res.get("applied"))
    swap = [{"op": "target", "row": "o2", "target": False},
            {"op": "add", "id": "p1", "stage": "s3", "lane": "opportunity", "text": "Нова ціль етапу", "target": True}]
    df3 = os.path.join(d, "d3.json")
    run("page-diff", "--note", n2, "--edits", put(d, "e3.json", edits(n2, swap)), "--out", df3)
    d3 = json.loads(text(df3)) if os.path.exists(df3) else {}
    rc, out, res = run("board-take", "--note", n2, "--diff", df3, "--take", *sorted({e["id"] for k in jm.DIFF_CATEGORIES for e in d3.get(k, [])}),
                       "--date", "2026-12-01")
    r2 = rows_of(n2)
    nb = [x for x in r2.values() if x["id"].startswith("b")]
    check("4.5 the target moved in one take: o2 no longer, the new opportunity is", rc == 0 and r2["o2"]["target"] == ""
          and len(nb) == 1 and nb[0]["target"] == "так", (r2["o2"]["target"], [x["target"] for x in nb]))

    def take_all(nf, ops, tag, dry=True, note_text=None):
        write(nf, note_text or before)
        dfx = os.path.join(d, "d-%s.json" % tag)
        run("page-diff", "--note", nf, "--edits", put(d, "e-%s.json" % tag, edits(nf, ops)), "--out", dfx)
        dx = json.loads(text(dfx)) if os.path.exists(dfx) else {}
        ids = sorted({e["id"] for k in jm.DIFF_CATEGORIES for e in dx.get(k, [])})
        return run("board-take", "--note", nf, "--diff", dfx, "--take", *ids, *(("--dry-run",) if dry else ("--date", "2026-12-01")))[2]

    n4 = os.path.join(d, "n4", "journey-first-order.md")
    res = take_all(n4, [{"op": "move", "row": "p3", "stage": "s3", "lane": "opportunity"},
                        {"op": "parent", "row": "h2", "parent": "p3"},
                        {"op": "move", "row": "o1", "stage": "s3", "lane": "opportunity"},
                        {"op": "parent", "row": "p2", "parent": "o1"}], "mv")
    nm = {(n["row"], n["why"]) for n in res.get("named", [])}
    ap = {(a["row"], a["action"]) for a in res.get("applied", [])}
    check("4.6 a parent is checked where it stands after the take's moves: lane and stage", ("h2", "parent") in ap
          and ("p2", "parent") in ap and ("h2", "bad_parent") not in nm and ("p2", "bad_parent") not in nm, (nm, ap))
    res = take_all(n4, [{"op": "move", "row": "o2", "stage": "s4", "lane": "opportunity"},
                        {"op": "add", "id": "p1", "stage": "s3", "lane": "solution", "text": "Рішення під o2", "parent": "o2"}], "mvadd")
    nw = [n for n in res.get("named", []) if n["why"] in ("bad_parent", "orphan") and (n["row"] or "").startswith("b")]
    check("4.7 a new row under a parent the same take moves away: bad_parent, then orphan — its parent not written",
          sorted(n["why"] for n in nw) == ["bad_parent", "orphan"] and all(
              a.get("parent") == "" for a in res.get("applied", []) if a["action"] == "add"), (nw, res.get("applied")))
    res = take_all(n4, [{"op": "add", "id": "p1", "stage": "s2", "lane": "metric", "text": "search -> cart: 99%"},
                        {"op": "add", "id": "p2", "stage": "s2", "lane": "anomaly", "text": "вигадана аномалія"}], "hc")
    check("4.8 the page adds no metric or anomaly row: metric_lane, nothing applied",
          sorted(r["why"] for r in res.get("refused", [])) == ["metric_lane", "metric_lane"] and not res.get("applied"), res.get("refused"))
    tgt = before.replace("| o1 | s2 | | opportunity | Не губити вибір покупця між кроками | | |",
                         "| o1 | s2 | | opportunity | Не губити вибір покупця між кроками | | так |")
    res = take_all(n4, [{"op": "move", "row": "o1", "stage": "s3", "lane": "opportunity"}], "tmv", dry=False, note_text=tgt)
    r4 = rows_of(n4)
    check("4.9 a move that brings a target onto a stage with its target: the moved row's target cleared, named bad_target",
          tgt != before and r4["o1"]["stage"] == "s3" and r4["o1"]["target"] == "" and r4["o2"]["target"] == "так"
          and any(n["why"] == "bad_target" and n["row"] == "o1" for n in res.get("named", [])), (r4["o1"], res.get("named")))
    n5 = os.path.join(d, "n5", "journey-first-order.md")
    write(n5, before.replace("| Строк доставки на картці товару | | | o2 | | Hypotheses/hypothesis-delivery-date-on-card |",
                             "| Строк доставки на картці товару | | | o2 | | |"))
    dg = jm.table_sig(jm.load(n5))["table"]
    two = {"journey-first-order": {"digest": dg, "edits": [{"op": "text", "row": "p2", "text": "Перша версія"}]},
           "Journey-First-Order": {"digest": dg, "edits": [{"op": "text", "row": "p2", "text": "Друга версія"}]}}
    rc, out, res = run("page-diff", "--note", n5, "--edits", put(d, "e-two.json", edits(n5, [], maps=two)))
    check("4.10 one map named twice in a file: neither entry is read (bad_edit, once)",
          not res.get("changed") and [s["why"] for s in res.get("skipped", [])] == ["bad_edit"],
          (res.get("changed"), res.get("skipped")))
    rc, out, res = run("page-diff", "--note", n5, "--edits", put(d, "e-hid.json", edits(n5, [{"op": "text", "row": "h3", "text": "Не з цієї сторінки"}])))
    check("4.11 a row the page does not show is no row of the page (unknown_row)", not res.get("changed")
          and [s["why"] for s in res.get("skipped", [])] == ["unknown_row"], res.get("skipped"))

    # 5. the tree page (§14)
    t = os.path.join(d, "tree")
    shutil.copytree(os.path.join(FIX, "nest"), t)
    shutil.rmtree(os.path.join(t, "golden"))
    root, pay = os.path.join(t, "journey-first-order.md"), os.path.join(t, "journey-payment.md")
    rc, out, res = run("render-html", "--note", root, "--out", os.path.join(t, "root.html"), "--lang", "uk")
    th = text(os.path.join(t, "root.html")) if os.path.exists(os.path.join(t, "root.html")) else ""
    frames = re.findall(r'data-map="([^"]+)" data-digest="([^"]+)"', th)
    check("5.1 each grid of the tree page names its own map and digest", [f[0] for f in frames] == [
        "journey-first-order", "journey-shipping", "journey-payment", "journey-3ds"]
          and dict(frames)["journey-payment"] == jm.table_sig(jm.load(pay))["table"], frames)
    check("5.2 a reference past the depth has no editable row", "journey-3ds-retry" not in [f[0] for f in frames], "")
    pay_before, root_before = text(pay), text(root)
    tree_ed = {"journey-payment": {"digest": dict(frames).get("journey-payment"), "edits": [
        {"op": "text", "row": "pc2", "text": "Незрозуміло, чому банк відхилив картку"}, {"op": "parent", "row": "pc2", "parent": "o1"}]}}
    tdf = os.path.join(d, "td.json")
    rc, out, res = run("page-diff", "--note", root, "--edits", put(d, "te.json", edits(root, [], maps=tree_ed)), "--out", tdf)
    check("5.3 a child's row keyed as on a tree board, its parent too", rc == 0
          and [e.get("row") for e in res.get("changed", [])] == ["journey-payment#pc2"]
          and [e.get("parent_now") for e in res.get("relinked", [])] == ["journey-payment#o1"]
          and "journey-payment" in (res.get("tree") or {}), out[-300:])
    pid = (res.get("changed") or [{}])[0].get("id")
    rc, out, res = run("board-take", "--note", root, "--diff", tdf, "--take", pid, "--dry-run")
    check("5.4 the root's take refuses it: other_note", [x["why"] for x in res.get("refused", [])] == ["other_note"], res.get("refused"))
    rc, out, res = run("board-take", "--note", pay, "--diff", tdf, "--take", pid, "--class", "%s=reported" % pid, "--date", "2026-12-01")
    rp = rows_of(pay)
    check("5.5 the child's take writes the child's note alone", rc == 0 and rp["pc2"]["text"] == "Незрозуміло, чому банк відхилив картку"
          and rp["pc2"]["parent"] == "o1" and rp["pc2"]["source"] == "сторінка команди 2026-12-01" and text(root) == root_before, rp["pc2"])
    write(pay, pay_before)
    other = dict(tree_ed["journey-payment"], edits=[{"op": "text", "row": "pc2", "text": "Банк мовчить, чому відхилив"}])
    tdf2 = os.path.join(d, "td2.json")
    run("page-diff", "--note", root, "--edits", put(d, "te2.json", edits(root, [], maps={"journey-payment": other})), "--out", tdf2)
    rc, out, res = run("board-take", "--note", pay, "--diff", tdf, tdf2, "--dry-run")
    cf = res.get("conflicts") or []
    check("5.6 two pages that changed one row differently: a conflict with both versions", rc == 0 and len(cf) == 1
          and cf[0]["row"] == "pc2" and cf[0]["what"] == "text" and len(cf[0]["versions"]) == 2, cf)
    both = [v["id"] for v in cf[0]["versions"]] if cf else []
    rc, out, res = run("board-take", "--note", pay, "--diff", tdf, tdf2, "--take", *both, "--dry-run")
    check("5.7 both versions taken: refused conflict, nothing applied", [x["why"] for x in res.get("refused", [])].count("conflict") == 2
          and not [a for a in res.get("applied", []) if a.get("action") == "text"], res.get("refused"))

    # 6. check 28 / 29 drift
    r28 = os.path.join(d, "r28")
    for rel in ("references/journey-protocol.md", "references/artifact-publishing.md", "references/vault-schema.md", "references/vault-protocol.md",
                "references/tools-seed.yaml", "scripts/story_map.py", "scripts/journey_map.py", "skills/cjm-research/SKILL.md",
                "skills/cjm-research/references/cjm-reports.md"):
        if os.path.exists(os.path.join(ROOT, rel)):
            write(os.path.join(r28, rel), text(os.path.join(ROOT, rel)))
    check("6.1 checks 28 and 29 are clean on the tree", jm.check_protocol(r28) == [] and jm.check_board_protocol(r28) == [],
          (jm.check_protocol(r28), jm.check_board_protocol(r28)))
    for rel, old, new, want, label in (
            ("references/journey-protocol.md", "**Editing on the page**", "**Editing**", "Editing on the page", "6.2 «Editing on the page» lost"),
            ("references/journey-protocol.md", "| `target` | the stage's target", "| `goal` | the stage's target", "page's ops", "6.3 an op renamed"),
            ("references/journey-protocol.md", "- A request from the page", "- Anything from the page", "request", "6.4 §15's request rule lost"),
            ("skills/cjm-research/SKILL.md", "- **J9 The page's edits**", "- **J10 The page's edits**", "J9", "6.5 Step J9 lost"),
            ("references/journey-protocol.md", "takes the source «сторінка команди <date>» (`team page <date>`) and the class", "takes the page's source and the class",
             "PAGE_SOURCE", "6.6 the page's source unnamed in §12")):
        p_ = os.path.join(r28, rel)
        t0 = text(p_)
        if old not in t0:
            check(label + ": its site is in %s" % rel, False, old)
            continue
        write(p_, t0.replace(old, new, 1))
        e = jm.check_protocol(r28) + jm.check_board_protocol(r28)
        write(p_, t0)
        check(label + " is named", any(want in x for x in e), e)

    # 7. a browser pass — the page's own JSON is what page-diff reads
    try:
        subprocess.run(["node", "-e", "require('playwright')"], check=True, capture_output=True, timeout=30,
                       env=dict(os.environ, NODE_PATH=subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip()))
        have_pw = True
    except Exception:
        have_pw = False
    if not have_pw:
        print("⏭  7.x the browser pass — Playwright is not installed here")
    else:
        n3 = os.path.join(d, "n3", "journey-first-order.md")
        write(n3, before)
        pg = os.path.join(d, "n3", "page.html")
        run("render-html", "--note", n3, "--out", pg, "--lang", "uk")
        js = os.path.join(d, "pw.js")
        write(js, r"""
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch(); const p = await b.newPage(); const errs = [];
  p.on('pageerror', e => errs.push(String(e))); const req = [];
  p.on('request', r => { if (!r.url().startsWith('file:')) req.push(r.url()); });
  await p.goto('file://' + process.argv[2]);
  const before = await p.isVisible('.edit-save');
  await p.click('.edit-toggle');
  await p.click('.item[data-row="p2"]'); await p.fill('.f-text', 'Вартість доставки не видно до кінця'); await p.click('.f-apply');
  await p.click('.item[data-row="m-s2-search-cart"]', {force: true}); const locked = await p.textContent('.edit-msg');
  const form = await p.isHidden('.edit-form');
  await p.click('td[data-stage="s3"][data-lane="solution"] .edit-add'); await p.fill('.f-text', 'Доставка в кошику одразу');
  const opts = await p.$$eval('.f-parent option', o => o.map(x => x.value)); await p.selectOption('.f-parent', 'o2'); await p.click('.f-apply');
  const plus = await p.$$eval('td[data-lane="metric"] .edit-add, td[data-lane="anomaly"] .edit-add', x => x.length);
  await p.click('.edit-copy'); await p.waitForTimeout(200);
  console.log(JSON.stringify({before, locked, form, opts, plus, count: await p.textContent('.edit-count'), out: await p.inputValue('.edit-out'), errs, req}));
  await b.close();
})();""")
        pr = subprocess.run(["node", js, pg], capture_output=True, text=True, timeout=120,
                            env=dict(os.environ, NODE_PATH=subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip()))
        try:
            br = json.loads(pr.stdout.strip().splitlines()[-1])
        except (ValueError, IndexError):
            br = {}
        check("7.1 the page loads with no error and asks nothing of the network", br and not br.get("errs") and not br.get("req"), (br, pr.stderr[-300:]))
        check("7.2 off, the switch hides the save; a locked row opens no editor and says why", br.get("before") is False
              and "health-check" in (br.get("locked") or "") and br.get("form") is True, br)
        check("7.3 the parent's choice: the stage's opportunities only; no «+» in the metric and anomaly lanes",
              br.get("opts") == ["", "o2"] and br.get("plus") == 0, (br.get("opts"), br.get("plus")))
        check("7.4 two edits counted", br.get("count") == "Правок: 2", br.get("count"))
        ep = os.path.join(d, "n3", "copied.txt")
        write(ep, br.get("out") or "")
        rc, out, res = run("page-diff", "--note", n3, "--edits", ep)
        check("7.5 what the page copied is what page-diff reads: a text changed, a solution added under o2", rc == 0
              and [e["row"] for e in res.get("changed", [])] == ["p2"]
              and [(e["lane"], e.get("parent")) for e in res.get("added", [])] == [("solution", "o2")] and not res.get("skipped"), out[-400:])

        n6 = os.path.join(d, "n6", "journey-first-order.md")
        write(n6, before.replace("| Строк доставки на картці товару | | | o2 |", "| Строк доставки на картці товару | | | o1 |"))
        pg6 = os.path.join(d, "n6", "page.html")
        run("render-html", "--note", n6, "--out", pg6, "--lang", "uk")
        js6 = os.path.join(d, "pw6.js")
        write(js6, r"""
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch(); const p = await b.newPage();
  await p.goto('file://' + process.argv[2]); await p.click('.edit-toggle');
  await p.click('.item[data-row="h3"]'); await p.fill('.f-text', 'Строк доставки видно на картці'); await p.click('.f-apply');
  await p.click('.edit-copy'); await p.waitForTimeout(200);
  console.log(JSON.stringify({out: await p.inputValue('.edit-out')})); await b.close();
})();""")
        pr6 = subprocess.run(["node", js6, pg6], capture_output=True, text=True, timeout=120,
                             env=dict(os.environ, NODE_PATH=subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip()))
        try:
            ops6 = [e["op"] for m in json.loads(json.loads(pr6.stdout.strip().splitlines()[-1])["out"])["maps"].values() for e in m["edits"]]
        except (ValueError, IndexError, KeyError, TypeError):
            ops6 = None
        check("7.6 a text edit keeps a parent the list does not offer — only the text goes into the file", ops6 == ["text"], (ops6, pr6.stderr[-300:]))

        js7 = os.path.join(d, "pw7.js")
        write(js7, r"""
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch(); const p = await b.newPage({viewport: {width: 1400, height: 900}}); const errs = [];
  p.on('pageerror', e => errs.push(String(e)));
  await p.goto('file://' + process.argv[2]); await p.click('.edit-toggle');
  await p.$eval('.item[data-row="p2"]', e => e.scrollIntoView({block: 'center'}));
  const sb = await (await p.$('.item[data-row="p2"]')).boundingBox(), db = await (await p.$('td[data-stage="s4"][data-lane="pain"]')).boundingBox();
  await p.mouse.move(sb.x + 20, sb.y + 10); await p.mouse.down(); await p.mouse.move(db.x + 40, db.y + 20, {steps: 12}); await p.mouse.up();
  const moved = await p.$eval('.item[data-row="p2"]', e => [e.closest('td').getAttribute('data-stage'), e.getAttribute('data-eb')]);
  await p.click('.item[data-row="p3"]');
  const panel = {title: await p.textContent('.f-title'), where: await p.textContent('.f-where'),
    stages: await p.$$eval('.f-stage option', o => o.map(x => x.textContent)), lanes: await p.$$eval('.f-lane option', o => o.map(x => x.value))};
  await p.click('.f-cancel');
  await p.click('.edit-copy'); await p.waitForTimeout(200);
  const one = await p.inputValue('.edit-out');
  await p.click('.item[data-row="p2"]'); await p.click('.f-reset');
  const back = await p.$eval('.item[data-row="p2"]', e => e.closest('td').getAttribute('data-stage'));
  console.log(JSON.stringify({moved, panel, one, back, count: await p.textContent('.edit-count'), errs})); await b.close();
})();""")
        pr7 = subprocess.run(["node", js7, pg], capture_output=True, text=True, timeout=120,
                             env=dict(os.environ, NODE_PATH=subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip()))
        try:
            b7 = json.loads(pr7.stdout.strip().splitlines()[-1])
            ops7 = [e for m in json.loads(b7["one"])["maps"].values() for e in m["edits"]]
        except (ValueError, IndexError, KeyError, TypeError):
            b7, ops7 = {}, None
        check("7.7 a card dragged into another cell is a move, marked on the page; no error", b7.get("moved") == ["s4", "змінено"]
              and ops7 == [{"op": "move", "row": "p2", "stage": "s4", "lane": "pain"}] and not b7.get("errs"), (b7, pr7.stderr[-300:]))
        check("7.8 the panel names the row by the stage's and lane's own names; no metric or anomaly lane to pick",
              b7.get("panel", {}).get("title") == "Редагування рядка" and "Кошик" in (b7.get("panel", {}).get("where") or "")
              and any("Кошик" in x for x in b7.get("panel", {}).get("stages", []))
              and not {"metric", "anomaly"} & set(b7.get("panel", {}).get("lanes", [])), b7.get("panel"))
        check("7.9 «Відмінити правки рядка» puts the card back and the count to zero", b7.get("back") == "s3"
              and b7.get("count") == "Правок: 0", (b7.get("back"), b7.get("count")))

    # mutations
    for name, old, new, args, test in (
            ("no-digest", 'if block.get("digest") != table_sig(n)["table"]:', "if False:",
             ("page-diff", "--note", note, "--edits", stale), lambda r: not r.get("skipped")),
            ("no-parent-check", "if v and (pr is None or ln not in PARENTS", "if False and (pr is None or ln not in PARENTS",
             ("board-take", "--note", n2, "--diff", df2, "--take", *ids, "--dry-run"),
             lambda r: any(a.get("action") == "parent" and a.get("row") == "p2" for a in r.get("applied", []))),
            ("lost-lock", 'locked="1" if (_locked(r) or not r["id"]) else ""', 'locked=""',
             ("render-html", "--note", note, "--out", os.path.join(d, "mut.html"), "--lang", "uk"),
             lambda r: 'data-locked="1"' not in (text(os.path.join(d, "mut.html")) if os.path.exists(os.path.join(d, "mut.html")) else ""))):
        m = mutant(d, name, old, new)
        if m is None:
            check("M.%s the mutation's pattern is in journey_map.py" % name, False, old)
            continue
        rc, out, res = run(*args, script=m)
        check("M.%s a mutant is caught by the same assertions" % name, rc != 0 or test(res), out[-300:])
    m = mutant(d, "page-source", "return page_source if isinstance(e, dict) and e.get(\"via\") == \"page\" else team_source", "return team_source")
    if m is None:
        check("M.page-source the mutation's pattern is in journey_map.py", False, "")
    else:
        n4 = os.path.join(d, "n4", "journey-first-order.md")
        write(n4, before)
        df4 = os.path.join(d, "d4.json")
        run("page-diff", "--note", n4, "--edits", put(d, "e4.json", edits(n4, ops[:1])), "--out", df4)
        pid4 = (json.loads(text(df4)).get("changed") or [{}])[0].get("id") if os.path.exists(df4) else "p1"
        run("board-take", "--note", n4, "--diff", df4, "--take", pid4, "--class", "%s=observed" % pid4, script=m)
        check("M.page-source a mutant is caught: the page's row is not «сторінка команди»", not rows_of(n4)["p1"]["source"].startswith("сторінка команди"), "")
    sys.path.insert(0, os.path.dirname(SCRIPT))
    check("M.request a request put into EDIT is caught by 1.3's own pattern",
          re.search(r"fetch|XMLHttpRequest|sendBeacon|WebSocket|import\(|src=|https?:|\.open\(", jm.EDIT.replace("count2();})();", "fetch('/x');count2();})();")) is not None, "")
finally:
    shutil.rmtree(d, ignore_errors=True)
    shutil.rmtree(SAFE_HOME, ignore_errors=True)

print("\nRESULT: %s (%d failed)" % ("GREEN ✅" if not fails else "RED ❌", fails))
sys.exit(1 if fails else 0)
