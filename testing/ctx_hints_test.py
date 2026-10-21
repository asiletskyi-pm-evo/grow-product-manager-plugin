#!/usr/bin/env python3
"""TC-ctx-3160-hints — scripts/ctx_hints.py: the remembered picks of the search and the golden set (since v3.16.0).

The memory of your choices (`.state/search.json` of the store, schema context-search-memory/1) is read and written
here: no file is an empty memory; a file of another schema, with a key nobody knows, not JSON or not readable is a
StoreError that names it, and is never reset. A hint matches a new request when the Jaccard similarity of their stem
sets is 0.6 or more and the products do not differ; its `good` notes are weighed × 1.5 and marked
`твій вибір від <день>`, its `bad` ones marked `ти казав «не те»`. `ctx_search.run` applies them before the best N are
cut, and a memory it cannot read is one line, never the search. The golden set (`search-golden/1`) is read with its
BOM, its rows checked, and `evaluate` gives the level-1 numbers of `ctx search eval`. The fictional Zorg vault of
testing/fixtures/search/ is copied to a temp dir; nothing else is written. Stdlib only; run from the repo root:

  env -u GROW_PM_CONTEXT_PATH -u GROW_PM_PROVIDER_PATHS python3 testing/ctx_hints_test.py
"""
import datetime, json, os, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import ctx_hints as ch  # noqa: E402
import ctx_search as cs_  # noqa: E402
import ctx_store as cs  # noqa: E402

FIX = os.path.join(ROOT, "testing", "fixtures", "search")
GOLDEN_ZORG = os.path.join(FIX, "golden.zorg.yaml")
CTX = os.path.join(ROOT, "scripts", "ctx.py")
NOW = datetime.datetime(2026, 10, 20, 12, 0)
MOBILE = "Notes/Mobile cart notes.md"
fails = 0


def check(name, cond, detail=""):
    global fails
    fails += not cond
    print(("✅" if cond else "❌"), name, ("" if cond else "-> " + str(detail)[:700]))


def read(*parts):
    return open(os.path.join(*parts), encoding="utf-8", newline="").read()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8", newline="").write(text)


def raises(fn, *args, **kw):
    """The exception `fn` raises, or None."""
    try:
        fn(*args, **kw)
    except Exception as e:  # noqa: BLE001 — the test looks at which one
        return e
    return None


class Env:
    """A temp home (the fixture's, with its glossary) and a temp vault: {{VAULT}} and {{HOME}} filled in; no local index
    (local-context.md without its Vault Search MCP line)."""

    def __init__(self, d):
        self.home, self.vault = os.path.join(d, "home"), os.path.join(d, "vault")
        shutil.copytree(os.path.join(FIX, "home"), self.home)
        shutil.copytree(os.path.join(FIX, "vault"), self.vault)
        for dirpath, _, names in os.walk(self.vault):
            for n in names:
                p = os.path.join(dirpath, n)
                if n.endswith(".yaml") and "{{VAULT}}" in read(p):
                    write(p, read(p).replace("{{VAULT}}", self.vault))
        text = read(FIX, "context.md").replace("{{VAULT}}", self.vault).replace("{{HOME}}", self.home)
        self.text = text[:text.index("### Vault Search MCP")]
        self.ctx = os.path.join(self.home, ".grow-pm", "local-context.md")
        write(self.ctx, self.text)
        self.store = os.path.join(self.vault, "Notes", "_System", "context")
        self.memory = os.path.join(self.store, ".state", "search.json")

    def sctx(self):
        return cs_.context_for(self.home, self.text, self.store)

    def cli(self, *args):
        env = dict(os.environ)
        env.pop("GROW_PM_CONTEXT_PATH", None)
        p = subprocess.run([sys.executable, CTX] + list(args) + ["--home", self.home, "--context", self.ctx],
                           capture_output=True, text=True, env=env, timeout=120)
        last = (p.stdout.strip().splitlines() or [""])[-1]
        res = json.loads(last[len("CTX_RESULT "):]) if last.startswith("CTX_RESULT ") else None
        return p.returncode, p.stdout + p.stderr, res


def hint(q, good=(), bad=(), product="", at="2026-10-19"):
    return {"q": q, "terms": ch.terms(q), "product": product, "good": list(good), "bad": list(bad), "at": at}


def memory(*hints):
    return {"schema": ch.SCHEMA, "hints": list(hints)}


# ------------------------------------------------------------------ the spec's numbers and words
check("schemas context-search-memory/1 and search-golden/1; Jaccard 0.6; good × 1.5",
      (ch.SCHEMA, ch.GOLDEN_SCHEMA, ch.JACCARD, ch.GOOD_W) == ("context-search-memory/1", "search-golden/1", 0.6, 1.5))
check("the marks and the line, word for word", (ch.CHOICE % "2026-10-19", ch.NOT_THAT, ch.UNREAD_NOTE % "x")
      == ("твій вибір від 2026-10-19", "ти казав «не те»", "пам'ять пошуку не прочитано (x) — без підказок"))

# ------------------------------------------------------------------ the memory: load and save
with tempfile.TemporaryDirectory() as d:
    store = cs.Store(os.path.join(d, "context"))
    path = os.path.join(store.state_dir, "search.json")
    check("no file: an empty memory", ch.load(store) == {"schema": ch.SCHEMA, "hints": []}, ch.load(store))
    mem = memory(hint("мобільний кошик", good=[MOBILE]))
    saved = ch.save(store, mem)
    check("save writes .state/search.json and gives back what it wrote", os.path.isfile(path) and saved == ch.load(store))
    got = ch.load(store)
    check("…and it reads back: q, the stems sorted, product, good, bad, the day",
          got["hints"] == [{"q": "мобільний кошик", "terms": ["кошик", "мобільн"], "product": "", "good": [MOBILE],
                            "bad": [], "at": "2026-10-19"}], got)
    text = read(path)
    check("…sorted, indented JSON with a newline at the end", text.endswith("}\n") and text.startswith("{\n")
          and json.loads(text) == got and text.index('"hints"') < text.index('"schema"'), text[:200])

    def refused(raw, kind, why):
        write(path, raw)
        e = raises(ch.load, store)
        return isinstance(e, cs.StoreError) and str(e).startswith("search memory %s: .state/search.json (" % kind) and why in str(e), e

    ok, e = refused(json.dumps({"schema": "context-search-memory/2", "hints": []}), "not valid", "context-search-memory/2")
    check("another schema → StoreError «search memory not valid: .state/search.json (…)»", ok, e)
    ok, e = refused(json.dumps({"schema": ch.SCHEMA, "hints": [], "later": 1}), "not valid", "unknown key: later")
    check("a key nobody knows → StoreError, never dropped", ok, e)
    ok, e = refused(json.dumps(memory(dict(hint("кошик", good=["a.md"]), weight=2))), "not valid", "weight")
    check("…in a hint too", ok, e)
    ok, e = refused("{not json", "not valid", "")
    check("not JSON → StoreError «not valid»", ok, e)
    ok, e = refused(json.dumps(memory(hint("кошик"))), "not valid", "neither good nor bad")
    check("a hint with neither good nor bad → StoreError", ok, e)
    ok, e = refused(json.dumps(memory(dict(hint("кошик", good=["a.md"]), at="20.10.2026"))), "not valid", "YYYY-MM-DD")
    check("a day that is not YYYY-MM-DD → StoreError", ok, e)
    os.remove(path)
    os.makedirs(path)
    e = raises(ch.load, store)
    check("a file that cannot be read → StoreError «search memory not readable: .state/search.json (…)»",
          isinstance(e, cs.StoreError) and str(e).startswith("search memory not readable: .state/search.json ("), e)
    os.rmdir(path)
    e = raises(ch.save, store, {"schema": ch.SCHEMA, "hints": "no"})
    check("a memory of the wrong shape is not saved: StoreError, no file", isinstance(e, cs.StoreError)
          and not os.path.exists(path), e)
    write(path, json.dumps(memory(hint("кошик мобільний", good=["a.md"]), hint("мобільний кошик", good=["b.md"],
                                                                                    bad=["a.md"], at="2026-10-20"))))
    got = ch.load(store)["hints"]
    check("two hints of the same request and product read as one: good and bad merged, the later day",
          len(got) == 1 and got[0]["good"] == ["b.md"] and got[0]["bad"] == ["a.md"] and got[0]["at"] == "2026-10-20", got)

# ------------------------------------------------------------------ Jaccard
A, B = {"a", "b", "c"}, {"a", "b", "c", "d", "e"}
check("Jaccard {a,b,c} vs {a,b,c,d,e} = 0.6 — on the boundary, it matches", ch.jaccard(A, B) == 0.6 and ch.similar(A, B))
check("{a,b,c} vs {a,b,x,y} = 0.4 — no", abs(ch.jaccard(A, {"a", "b", "x", "y"}) - 0.4) < 1e-9
      and not ch.similar(A, {"a", "b", "x", "y"}))
check("{a,b,c,d} vs {a,b,x,y} = 0.33 — no", abs(ch.jaccard({"a", "b", "c", "d"}, {"a", "b", "x", "y"}) - 1 / 3) < 1e-9
      and not ch.similar({"a", "b", "c", "d"}, {"a", "b", "x", "y"}))
check("nothing on either side: 0, no match", ch.jaccard(set(), set()) == 0 and not ch.similar(set(), set()))

mem = memory(hint("мобільний кошик", good=[MOBILE]))
check("match: the same words in another order and form", [h["q"] for h in ch.match(mem, "кошик мобільного", None)]
      == ["мобільний кошик"])
check("…2 of 3 stems (0.67)", len(ch.match(mem, "мобільний кошик продавця", None)) == 1)
check("…1 of 4 stems (0.25): no", ch.match(mem, "кошик продавця графік роботи", None) == [])
check("…a request of stop words only: no", ch.match(mem, "що і як?", None) == [])
pm = memory(hint("мобільний кошик", good=[MOBILE], product="Zorg App"))
check("a hint of a product: the same product (by its name or slug) matches, another does not",
      len(ch.match(pm, "мобільний кошик", "Zorg App")) == 1 and len(ch.match(pm, "мобільний кошик", "zorg-app")) == 1
      and len(ch.match(pm, "мобільний кошик", "Org: Zorg App")) == 1 and ch.match(pm, "мобільний кошик", "Zorg Lite") == [])
check("…a search with no product takes it; a hint with no product serves every product",
      len(ch.match(pm, "мобільний кошик", None)) == 1 and len(ch.match(mem, "мобільний кошик", "Zorg Lite")) == 1)

# ------------------------------------------------------------------ apply
cands = [{"path": "a.md", "heading": "A", "score": 1.0, "flags": []}, {"path": "b.md", "heading": "", "score": 1.0, "flags": []},
         {"path": "c.md", "heading": "", "score": 1.0, "flags": ["хаб"]}, {"path": "Notes/C# guide.md", "heading": "", "score": 2.0,
                                                                          "flags": []}]
hs = [{"good": ["a.md#A › x"], "bad": ["b.md"], "at": "2026-10-01"}, {"good": ["a.md", "Notes/C"], "bad": [], "at": "2026-10-05"}]
ch.apply(cands, hs, datetime.date(2026, 10, 20))
check("apply: a good note × 1.5 once, however many hints name it, marked with the latest day",
      cands[0]["score"] == 1.5 and cands[0]["flags"] == ["твій вибір від 2026-10-05"], cands[0])
check("…a `path#heading` pick is its note", cands[0]["score"] == 1.5)
check("…a bad note marked `ти казав «не те»`, its score as it was", cands[1]["score"] == 1.0
      and cands[1]["flags"] == ["ти казав «не те»"], cands[1])
check("…the others untouched; a path that is only a prefix of another is not it", cands[2] == {"path": "c.md", "heading": "",
      "score": 1.0, "flags": ["хаб"]} and cands[3]["score"] == 2.0 and cands[3]["flags"] == [], cands[2:])
c = [{"path": "Notes/C# guide.md", "heading": "", "score": 1.0, "flags": []}]
ch.apply(c, [{"good": ["Notes/C# guide.md#Intro"], "bad": []}], datetime.date(2026, 10, 20))
check("…a note whose name has a # in it; a hint with no day: today", c[0]["score"] == 1.5
      and c[0]["flags"] == ["твій вибір від 2026-10-20"], c)

# v3.16.2 Task 2 (M8, N7): a pick of a note folded as a twin weighs and marks its survivor; eval counts it there
c = [{"path": "Notes/Research/Cart study.md", "heading": "", "score": 1.0, "flags": [],
      "twins": ["Notes/Knowledge/Cart study.md"]},
     {"path": "Notes/Other.md", "heading": "", "score": 1.0, "flags": [], "twins": ["Notes/Old other.md"],
      "twin_keys": {"Notes/Old other.md": "near"}}]
ch.apply(c, [{"good": ["Notes/Knowledge/Cart study.md#Findings"], "bad": ["Notes/Old other.md"], "at": "2026-10-10"}],
         datetime.date(2026, 10, 20))
check("v3.16.2 C2 (M8): `good` on a note folded as a twin — its survivor × 1.5 and «твій вибір від <день>»; `bad` — «ти казав «не те»»",
      c[0]["score"] == 1.5 and c[0]["flags"] == ["твій вибір від 2026-10-10"] and c[1]["score"] == 1.0
      and c[1]["flags"] == ["ти казав «не те»"], c)
check("v3.16.2 C2 (N7): eval finds a golden note folded as a twin at its survivor's place",
      ch._rank([{"path": "A.md"}, {"path": "B.md", "twins": ["C.md"]}], ["C.md"]) == 2
      and ch._rank([{"path": "A.md"}], ["C.md"]) is None)

# v3.16.2 Task 2 review fixes: a verdict on the candidate's own path outranks a carried one; `bad` crosses only a
# same-text fold; eval says when it found an answer through a twin
c = [{"path": "Notes/Roadmap v2.md", "score": 1.0, "flags": [], "twins": ["Notes/Roadmap v1.md"],
      "twin_keys": {"Notes/Roadmap v1.md": "version"}},
     {"path": "Notes/Copy A.md", "score": 1.0, "flags": [], "twins": ["Notes/Copy B.md"],
      "twin_keys": {"Notes/Copy B.md": "near"}},
     {"path": "Notes/Picked.md", "score": 1.0, "flags": [], "twins": ["Notes/Other twin.md"],
      "twin_keys": {"Notes/Other twin.md": "hash"}},
     {"path": "Notes/Refused.md", "score": 1.0, "flags": [], "twins": ["Notes/Liked twin.md"],
      "twin_keys": {"Notes/Liked twin.md": "near"}}]
hints = [{"good": [], "bad": ["Notes/Roadmap v1.md"], "at": "2026-10-01"},
         {"good": [], "bad": ["Notes/Copy B.md"], "at": "2026-10-02"},
         {"good": ["Notes/Picked.md"], "bad": ["Notes/Other twin.md"], "at": "2026-10-03"},
         {"good": ["Notes/Liked twin.md"], "bad": ["Notes/Refused.md"], "at": "2026-10-04"}]
ch.apply(c, hints, datetime.date(2026, 10, 20))
check("v3.16.2 review I1: «не те» on an older version does not mark the newer one (a version fold carries no `bad`)",
      c[0]["flags"] == [] and c[0]["score"] == 1.0, c[0])
check("…«не те» crosses a same-text fold (a near copy, the same hash)", c[1]["flags"] == ["ти казав «не те»"], c[1])
check("…your pick of the candidate itself outranks a «не те» carried from its twin", c[2]["score"] == 1.5
      and c[2]["flags"] == ["твій вибір від 2026-10-03"], c[2])
check("…your «не те» of the candidate itself outranks a pick carried from its twin", c[3]["score"] == 1.0
      and c[3]["flags"] == ["ти казав «не те»"], c[3])
ev = ch.evaluate([{"q": "zorg q", "class": "форма", "good": ["G.md"], "ok": []}],
                 lambda qs, row: {"candidates": [{"path": "A.md", "twins": ["G.md"]}]})
check("v3.16.2 review M4: an eval row found through a twin says so (`via_twin`), and the result counts them",
      ev["rows"][0]["rank"] == 1 and ev["rows"][0].get("via_twin") is True and ev.get("via_twin") == 1, ev)

# ------------------------------------------------------------------ remember, forget, resolve
mem = ch.empty()
check("remember: a new hint", ch.remember(mem, "мобільний кошик", None, [MOBILE], [], "2026-10-19") is True
      and mem["hints"] == [hint("мобільний кошик", good=[MOBILE])], mem)
check("…the same again changes nothing", ch.remember(mem, "мобільний кошик", None, [MOBILE], [], "2026-10-20") is False
      and mem["hints"][0]["at"] == "2026-10-19")
check("…the same request (another order, another form) merges: «не те» moves a note from good to bad",
      ch.remember(mem, "кошика мобільний", None, [], [MOBILE], "2026-10-20") is True and len(mem["hints"]) == 1
      and mem["hints"][0]["good"] == [] and mem["hints"][0]["bad"] == [MOBILE] and mem["hints"][0]["at"] == "2026-10-20", mem)
check("…and a pick moves it back (a section of it is the note)",
      ch.remember(mem, "мобільний кошик", None, [MOBILE + "#Mobile cart notes › Quotes"], [], "2026-10-21") is True
      and mem["hints"][0]["good"] == [MOBILE + "#Mobile cart notes › Quotes"] and mem["hints"][0]["bad"] == [], mem)
check("…another product is another hint", ch.remember(mem, "мобільний кошик", "Zorg App", ["x.md"], [], "2026-10-21")
      and len(mem["hints"]) == 2)
check("…a request of stop words only is a ValueError", isinstance(raises(ch.remember, mem, "що і як", None, ["x.md"], [],
                                                                         "2026-10-21"), ValueError))
check("…neither a good nor a bad note is a ValueError", isinstance(raises(ch.remember, mem, "кошик", None, [], [], "2026-10-21"),
                                                                    ValueError))
check("forget with a product: only that product's hint", ch.forget(mem, "мобільний кошик", "Zorg App") == 1
      and len(mem["hints"]) == 1 and mem["hints"][0]["product"] == "")
ch.remember(mem, "мобільний кошик", "Zorg App", ["x.md"], [], "2026-10-21")
check("forget without one: every hint of the request", ch.forget(mem, "кошик мобільний", None) == 2 and mem["hints"] == [])
check("…nothing left to forget: 0", ch.forget(mem, "кошик мобільний", None) == 0)

with tempfile.TemporaryDirectory() as d:
    last = os.path.join(d, "last.json")
    write(last, json.dumps({"abcdef0123": {"source": "own", "path": "Notes/x.md", "heading": "X › Y", "kind": "own"},
                            "0123456789": {"source": "zorg-brain", "path": "Growth/y.md", "heading": "", "kind": "local"}}))
    check("resolve: an id of the last searches is its section, `path#heading`", ch.resolve("abcdef0123", last) == "Notes/x.md#X › Y"
          and ch.resolve(" ABCDEF0123 ", last) == "Notes/x.md#X › Y")
    check("…a note-level id is its path", ch.resolve("0123456789", last) == "Growth/y.md")
    e = raises(ch.resolve, "fedcba9876", last)
    check("…an id no search gave: ValueError that names it", isinstance(e, ValueError) and "fedcba9876" in str(e), e)
    check("…a path as written, its separators and a leading ./ tidied", ch.resolve(" ./Notes\\Mobile cart notes.md ", last) == MOBILE)
    e = raises(ch.resolve, "abcdef0123", os.path.join(d, "none.json"))
    check("…no last.json: an id is not known", isinstance(e, ValueError), e)

# ------------------------------------------------------------------ the golden set
rows = ch.load_golden(GOLDEN_ZORG)
check("the Zorg golden set: 15 rows, two of them empty", len(rows) == 15
      and sum(1 for r in rows if r["class"] == "порожній" and r["good"] == []) == 2, len(rows))
check("…every class of the spec is there", {r["class"] for r in rows} == {"форма", "синонім", "англ", "рос", "питання",
                                                                         "абревіатура", "транслітерація", "ключ", "коротко",
                                                                         "справжній", "порожній"}, {r["class"] for r in rows})
r0 = rows[0]
check("…a row read whole: q, variants, class, product, skill, good, ok, bad, source, added",
      (r0["q"], r0["variants"][2], r0["class"], r0["product"], r0["skill"], r0["good"], r0["ok"][0], r0["bad"], r0["source"],
       r0["added"]) == ("графіком роботи продавців", "seller working hours", "форма", "Zorg App", "",
                        ["Notes/Кошик — графік роботи продавця.md"], "Notes/Корзина 2.0 (mobile).md",
                        ["Notes/Checkout flow (old).md"], "reviewed", "2026-10-20"), r0)
check("…the lists a row leaves out are empty", rows[1]["bad"] == [] and rows[9]["ok"] == [], (rows[1], rows[9]))
with tempfile.TemporaryDirectory() as d:
    g = os.path.join(d, "golden.yaml")
    base = read(GOLDEN_ZORG)
    write(g, "﻿" + base)
    check("a file that starts with a BOM reads the same", ch.load_golden(g) == rows)

    def bad(text, why):
        write(g, text)
        e = raises(ch.load_golden, g)
        return isinstance(e, ValueError) and why in str(e), e

    one = "schema: search-golden/1\nqueries:\n  - q: \"кошик\"\n    class: форма\n    good: [\"a.md\"]\n"
    check("one row of the shape reads", (write(g, one), ch.load_golden(g))[1] == [
        {"q": "кошик", "variants": [], "class": "форма", "product": "", "skill": "", "good": ["a.md"], "ok": [], "bad": [],
         "source": "", "added": ""}])
    for text, why, name in ((one.replace("search-golden/1", "search-golden/2"), "search-golden/2", "another schema"),
                            (one.replace("schema: search-golden/1\n", ""), "schema", "no schema"),
                            (one.replace("  - q: \"кошик\"\n    class", "  - class"), "q", "a row without q"),
                            (one.replace("    class: форма\n", ""), "class", "a row without class"),
                            (one.replace("    good: [\"a.md\"]\n", ""), "good", "a row without good"),
                            (one.replace("good: [\"a.md\"]", "good: []"), "порожній", "no good outside the empty class"),
                            (one.replace("class: форма", "class: порожній"), "порожній", "good in the empty class"),
                            (one + "    weight: 2\n", "weight", "a key nobody knows"),
                            (one.replace("queries:", "queries: x"), "queries", "queries that are no list")):
        ok, e = bad(text, why)
        check("the golden set refuses %s: ValueError that says so" % name, ok, e)

hm = memory(hint("мобільний кошик", good=[MOBILE], product="Zorg App"), hint("кошик", bad=["b.md"]))
check("hint_rows: a hint with good is a row `source: choice` (class вибір, no variants); one with only bad is none",
      ch.hint_rows(hm) == [{"q": "мобільний кошик", "variants": [], "class": "вибір", "product": "Zorg App", "skill": "",
                            "good": [MOBILE], "ok": [], "bad": [], "source": "choice", "added": "2026-10-19"}], ch.hint_rows(hm))

# ------------------------------------------------------------------ evaluate: the level-1 numbers
def res(*paths):
    return {"candidates": [{"path": p, "heading": ""} for p in paths], "notes": ["n1"], "sources": [{"id": "own", "answered": True}]}


asked = []
answers = {("qa", "va"): res("x.md", "a.md"), ("qa",): res("x.md"), ("qb",): res("c.md", "b.md"),
           ("qe", "ve"): res("x.md", "y.md", "z.md"), ("qf",): res(*["f%d.md" % i for i in range(54)] + ["g.md"])}


def ask(queries, row):
    asked.append(tuple(queries))
    return answers[tuple(queries)]


rows = [{"q": "qa", "variants": ["va"], "class": "A", "good": ["a.md"], "ok": [], "source": "reviewed"},
        {"q": "qb", "variants": [], "class": "B", "good": ["b.md#B › 1"], "ok": ["c.md"], "source": "reviewed"},
        {"q": "qe", "variants": ["ve"], "class": "порожній", "good": [], "ok": [], "source": "reviewed"},
        {"q": "qf", "variants": [], "class": "B", "good": ["g.md"], "ok": [], "source": "choice"}]
m = ch.evaluate(rows, ask)
check("evaluate: n counts the rows with an answer; recall50 with the variants, recall50_q_only without",
      (m["n"], m["recall50"], m["recall50_q_only"]) == (3, 2 / 3, 1 / 3), m)
check("…mrr by the first good (ok counts for recall only); a good at 55 is no hit", abs(m["mrr"] - (1 / 2 + 1 / 2 + 0) / 3) < 1e-9, m)
check("…by_class", m["by_class"] == {"A": {"n": 1, "recall50": 1.0, "recall50_q_only": 0.0, "mrr": 0.5},
                                     "B": {"n": 2, "recall50": 0.5, "recall50_q_only": 0.5, "mrr": 0.25}}, m["by_class"])
check("…the empty rows: how many candidates their top 5 has, on average", (m["empty_n"], m["empty_top5_mean"]) == (1, 3.0), m)
check("…a row with no variants is asked once", asked.count(("qb",)) == 1 and asked.count(("qf",)) == 1, asked)
check("…each row's ranks, and the notes once", m["rows"][0] == {"q": "qa", "class": "A", "source": "reviewed", "rank": 2,
                                                                "rank_q_only": None, "rank_good": 2, "via_twin": False}
      and m["rows"][2] == {"q": "qe", "class": "порожній", "source": "reviewed", "top5": 3} and m["notes"] == ["n1"], m["rows"])
check("…no rows: no numbers, no error", ch.evaluate([], ask)["recall50"] is None)

# ------------------------------------------------------------------ ctx_search.run applies the hints
with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    sx = env.sctx()
    plain = cs_.run(sx, ["мобільний кошик"], now=NOW)
    order = [c["path"] for c in plain["candidates"]]
    check("(without a hint the mobile cart notes are not among the best two)", MOBILE in order and order.index(MOBILE) >= 2, order)
    before = next(c for c in plain["candidates"] if c["path"] == MOBILE)
    write(env.memory, json.dumps(memory(hint("мобільний кошик", good=[MOBILE], at="2026-10-19"))))
    got = cs_.run(sx, ["кошик мобільного", "mobile cart"], now=NOW)
    mc = next((c for c in got["candidates"] if c["path"] == MOBILE), None)
    check("run: a remembered pick of a similar request (the first --q) is marked `твій вибір від <день>`",
          mc and "твій вибір від 2026-10-19" in mc["flags"], mc)
    flip = cs_.run(sx, ["mobile cart", "мобільний кошик"], now=NOW)
    check("…a variant that matches the hint is not the request: no hint", not any(f.startswith("твій вибір")
                                                                                   for c in flip["candidates"] for f in c["flags"]))
    two = cs_.run(sx, ["мобільний кошик"], limit=2, now=NOW)
    check("…and weighed × 1.5 before the best N are cut: with --limit 2 it is one of the two",
          [c["path"] for c in two["candidates"]] == [order[0], MOBILE]
          and abs(two["candidates"][1]["score"] - before["score"] * 1.5) < 1e-5, (two["candidates"], before["score"]))
    off = cs_.run(sx, ["мобільний кошик"], use_hints=False, now=NOW)
    check("…use_hints=False: as without the memory", [(c["path"], c["flags"], c["score"]) for c in off["candidates"]]
          == [(c["path"], c["flags"], c["score"]) for c in plain["candidates"]])
    write(env.memory, json.dumps(memory(hint("мобільний кошик", good=[MOBILE], product="Zorg Lite"))))
    other = cs_.run(sx, ["мобільний кошик"], product="Zorg App", now=NOW)
    check("…a hint of another product does nothing", not any(f.startswith("твій вибір") for c in other["candidates"]
                                                             for f in c["flags"]), other["candidates"][:3])
    write(env.memory, json.dumps(memory(hint("мобільний кошик", bad=[MOBILE]))))
    nb = cs_.run(sx, ["мобільний кошик"], now=NOW)
    mc = next((c for c in nb["candidates"] if c["path"] == MOBILE), None)
    check("…a `bad` note is marked `ти казав «не те»`, its place as without the memory",
          mc and "ти казав «не те»" in mc["flags"] and mc["score"] == before["score"]
          and [c["path"] for c in nb["candidates"]] == order, mc)
    write(env.memory, "{not json")
    broken = cs_.run(sx, ["мобільний кошик"], now=NOW)
    line = [n for n in broken["notes"] if n.startswith("пам'ять пошуку не прочитано (")]
    check("…a memory that cannot be read: the search goes on without hints and one line says why",
          [c["path"] for c in broken["candidates"]] == order and line
          and line[0].endswith(") — без підказок") and "search memory not valid: .state/search.json" in line[0], broken["notes"])

    # the command line: an unreadable memory never stops `ctx search`, and `remember` never rewrites it
    shutil.rmtree(env.store)                      # the fixture's half-migrated records/ and the memories written above
    rc, out, _ = env.cli("migrate", "--apply")
    check("(the fixture's store migrated)", rc == 0, out[-300:])
    write(env.memory, "{not json")
    rc, out, r = env.cli("search", "--q", "мобільний кошик", "--json")
    check("ctx search with an unreadable .state/search.json: exit 0, the candidates and the line", rc == 0 and r
          and r["candidates"] and any(n.startswith("пам'ять пошуку не прочитано (") for n in r["notes"]), (rc, out[-400:]))
    journal = read(env.store, ".state", "journal.jsonl")
    rc, out, r = env.cli("search", "remember", "--q", "мобільний кошик", "--pick", MOBILE)
    check("ctx search remember with it: exit 3, the file not rewritten, no journal line", rc == 3
          and read(env.memory) == "{not json" and read(env.store, ".state", "journal.jsonl") == journal
          and "search memory not valid" in out, (rc, out[-400:]))

    g = os.path.join(d, "golden-skill.yaml")
    write(g, read(GOLDEN_ZORG).replace("skill: write-concept", "skill: no-such-skill"))
    rc, out, r = env.cli("search", "eval", "--golden", g, "--no-hints", "--json")
    check("eval: a golden row's skill nobody knows is one line, not the run", rc == 0 and r
          and "еталонний набір: скіла no-such-skill немає — його рядки без ваги типів" in r["notes"], (rc, out[-400:]))

print("RESULT:", "GREEN ✅" if not fails else "RED ❌", "(%d failed)" % fails)
sys.exit(1 if fails else 0)
