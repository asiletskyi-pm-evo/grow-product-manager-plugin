#!/usr/bin/env python3
"""TC-ctx-3160-glossary — scripts/ctx_glossary.py: the team glossary read for the section search (since v3.16.0).

The approved terms of <home>/.grow-pm/knowledge-library/glossary/_org.yaml and of the file of the product (a product term
replaces the organisation one of the same `term`) become groups of names for one thing — the term, its English
equivalent and the abbreviation in the brackets of it, the variants and the phrasings the team avoids — and a question
that holds one of the names is widened with the others, by stem. The fictional Zorg glossary of testing/fixtures/search/home/
is read as it is; the cases that break or move files work on a temp copy. Stdlib only; run from the repo root:

  env -u GROW_PM_CONTEXT_PATH -u GROW_PM_PROVIDER_PATHS python3 testing/ctx_glossary_test.py
"""
import os, shutil, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import ctx_glossary as gl  # noqa: E402
import ctx_stem as st  # noqa: E402

HOME = os.path.join(ROOT, "testing", "fixtures", "search", "home")
GDIR = os.path.join(".grow-pm", "knowledge-library", "glossary")
fails = 0


def check(name, cond, detail=""):
    global fails
    fails += not cond
    print(("✅" if cond else "❌"), name, ("" if cond else "-> " + str(detail)[:900]))


def members(groups):
    return [m for g in groups for m in g]


def temp_home(*files):
    """A temp home with the given glossary files (name -> text), or none at all."""
    home = tempfile.mkdtemp(prefix="gl-")
    if files:
        os.makedirs(os.path.join(home, GDIR))
        for name, text in files:
            with open(os.path.join(home, GDIR, name), "w", encoding="utf-8", newline="") as f:
                f.write(text)
    return home


def tup(text):
    """A member the way expand() reads it."""
    return tuple(st.stem(t) for t in st.tokens(text) if st.norm(t) not in st.STOP)


# --- load: the fixture ---------------------------------------------------------------------------------------------
groups, why = gl.load(HOME, product="Zorg App")
check("the fixture is read without a problem", why is None, why)
check("approved only; the product replaces _org", ["кошик", "cart", "корзина", "basket"] in groups and not any("кандидат" in g for g in groups), groups)
check("a candidate is left out, whatever the member", not any("кандидат" in m or "претендент" in m for m in members(groups)), groups)
check("a deprecated term is left out", not any("гаджет" in m or "gadget" in m for m in members(groups)), groups)
check("the _org entry of the same term is gone, its words with it", ["кошик", "basket", "торба"] not in groups and "торба" not in members(groups), groups)
check("an _org term the product does not touch stays, in every spelling of its lists",
      ["замовлення", "order", "покупка", "заказ", "order form"] in groups and ["відгук", "review", "рев'ю", "фідбек", "ревью"] in groups, groups)
check("PDP from the brackets of en is a member, the name without them too",
      any("pdp" in m for g in groups for m in g) and ["картка товару", "product detail page", "pdp", "кт", "сторінка товару", "продуктова картка", "item card"] in groups, groups)
check("an unquoted value with an apostrophe and a comment does not break the entry", ["слот доставки", "delivery slot"] in groups, groups)
check("the lists of phrases: are not terms", not any("реалізувати" in m or "у цій фічі" in m for m in members(groups)), groups)
check("a group is lower case, one name once", all(m == m.lower() for m in members(groups)) and all(len(set(g)) == len(g) for g in groups), groups)
check("order: _org entries in file order (a replaced one in its place), then the new ones of the product",
      [g[0] for g in groups] == ["кошик", "замовлення", "відгук", "картка товару", "слот доставки"], [g[0] for g in groups])

# --- load: which file is the product's -----------------------------------------------------------------------------
check("no product named: the only file that is not _org is the product's", gl.load(HOME) == (groups, None))
check("the product named by its id: <product_id>.yaml", gl.load(HOME, product_id="zorg-app") == (groups, None))
check("the id is the first choice, then the slug of the name",
      gl.load(HOME, product="Something Else", product_id="zorg-app") == (groups, None))
only_org = gl.load(HOME, product="Zorg App", product_id="missing-id")[0]
check("an id with no file falls through to the slug of the name", only_org == groups)

more = temp_home(("_org.yaml", "terms:\n  - term: a\n    en: b\n    status: approved\n"),
                 ("one.yaml", "terms:\n  - term: c\n    en: d\n    status: approved\n"),
                 ("two.yaml", "terms:\n  - term: e\n    en: f\n    status: approved\n"))
g_more, w_more = gl.load(more, product="No Match")
check("two product files and none named: the _org terms only, no complaint", g_more == [["a", "b"]] and w_more is None, (g_more, w_more))
g_more, w_more = gl.load(more, product="Two")
check("the slug of the name picks the file among several", g_more == [["a", "b"], ["e", "f"]] and w_more is None, (g_more, w_more))
g_more, w_more = gl.load(more, product_id="../two")
check("an id that is a path picks nothing and writes nothing", g_more == [["a", "b"]] and w_more is None, (g_more, w_more))
shutil.rmtree(more)

# --- load: no glossary, a broken one ---------------------------------------------------------------------------------
empty = temp_home()
check("no .grow-pm at all: ([], None)", gl.load(empty, product="Zorg App") == ([], None))
os.makedirs(os.path.join(empty, GDIR))
check("an empty glossary folder: ([], None)", gl.load(empty, product="Zorg App") == ([], None))
check("a home that is not a folder: ([], None)", gl.load(os.path.join(empty, "nope")) == ([], None))
shutil.rmtree(empty)

good_org = "terms:\n  - term: кошик\n    en: cart\n    status: approved\n"
broken = temp_home(("_org.yaml", good_org), ("zorg-app.yaml", "terms:\n  - term: a\n    avoid:\n      - x: y\n"))
res = gl.load(broken, product="Zorg App")
check("a broken product file: the _org terms still load, the reason names the file and the line",
      res[0] == [["кошик", "cart"]] and res[1] is not None and res[1].startswith("zorg-app.yaml: line 4") , res)
shutil.rmtree(broken)

broken = temp_home(("_org.yaml", "terms:\n\t- term: a\n"), ("zorg-app.yaml", "terms:\n  - term: a\n    en: b\n    status: approved\n"))
res = gl.load(broken, product="Zorg App")
check("a broken _org file: the product terms load, the reason names _org.yaml", res[0] == [["a", "b"]] and (res[1] or "").startswith("_org.yaml: line 2"), res)
shutil.rmtree(broken)

broken = temp_home(("_org.yaml", "terms: [\n"), ("zorg-app.yaml", "terms: oops\n"))
res = gl.load(broken, product="Zorg App")
check("both broken: no groups, both named", res[0] == [] and "_org.yaml: line 1" in res[1] and "zorg-app.yaml: line 1" in res[1], res)
shutil.rmtree(broken)

broken = temp_home(("_org.yaml", good_org))
with open(os.path.join(broken, GDIR, "zorg-app.yaml"), "wb") as f:
    f.write(b"terms:\n  - term: \xff\xfe\n")
res = gl.load(broken, product="Zorg App")
check("a file that is not UTF-8 is a reason too, not a crash", res[0] == [["кошик", "cart"]] and (res[1] or "").startswith("zorg-app.yaml: "), res)
shutil.rmtree(broken)

odd = temp_home(("_org.yaml", "﻿terms:\n  - term: кошик\n    en: cart\n    status: APPROVED\n  - term:\n    en: nameless\n    status: approved\n  - term: x\n    status: approved\n"))
res = gl.load(odd)
check("a BOM, an upper-case status, an entry without a term, an entry with a term alone",
      res == ([["кошик", "cart"], ["x"]], None), res)
shutil.rmtree(odd)

odd = temp_home(("_org.yaml", "terms:\n  - term: a\n    en: \"cart (PDP, ПДП) (a basket)\"\n    variants: single\n    avoid: \"\"\n    status: approved\n"))
check("brackets: each abbreviation without a space is a member, a gloss with spaces is not; a scalar list is one name",
      gl.load(odd)[0] == [["a", "cart", "pdp", "пдп", "single"]], gl.load(odd))
shutil.rmtree(odd)

odd = temp_home(("_org.yaml", "terms:\n  - term: a\n    en: x\n    status: approved\n"),
                ("p.yaml", "terms:\n  - term: A\n    en: y\n    status: deprecated\n"))
check("a product entry of the same term hides the _org one whatever its status",
      gl.load(odd, product_id="p")[0] == [], gl.load(odd, product_id="p"))
shutil.rmtree(odd)

# --- expand ------------------------------------------------------------------------------------------------------
exp = gl.expand(st.query_terms("порожній кошик"), groups)
check("expansion brings the other members", ("cart",) in exp, exp)
check("…all of them, as stems, once each, in the order of the group", exp == [tup("cart"), tup("корзина"), tup("basket")], exp)
check("the stems of a member are those of ctx_stem", gl.expand(["кошик"], [["кошик", "корзини"]]) == [("корзин",)])
check("the term itself is not repeated", ("кошик",) not in exp and ("порожн",) not in exp, exp)
check("a question already holding another member does not get it again",
      gl.expand(st.query_terms("кошик cart"), groups) == [tup("корзина"), tup("basket")], gl.expand(st.query_terms("кошик cart"), groups))
check("a member with several words matches when all of them are in the question",
      ("pdp",) in gl.expand(st.query_terms("картка товару"), groups) and gl.expand(st.query_terms("картка"), groups) == [], gl.expand(st.query_terms("картка"), groups))
check("any form of a name matches: «корзини» finds the group of «корзина»", tup("кошик") in gl.expand(st.query_terms("корзини"), groups))
check("the abbreviation matches as a name: «PDP» brings the term", tup("картка товару") in gl.expand(st.query_terms("що таке PDP"), groups))
check("two groups naming the same other name: it is returned once", gl.expand(["xx", "yy"], [["xx", "aa", "bb"], ["yy", "bb", "cc"]]) == [("aa",), ("bb",), ("cc",)])
check("a question that holds no name gets nothing", gl.expand(st.query_terms("розклад змін"), groups) == [])
check("no terms, no groups: nothing", gl.expand([], groups) == [] and gl.expand(["кошик"], []) == [] and gl.expand([], []) == [])
check("a name of stop words only (no stems) matches nothing", gl.expand(["кошик"], [["що", "як"], ["чи"]]) == [])
check("a name of stop words only is still not a way in for the rest",
      gl.expand(["кошик"], [["як", "кошик", "cart"]]) == [("cart",)], gl.expand(["кошик"], [["як", "кошик", "cart"]]))
check("a name that shares a stem with another group's name brings both", gl.expand(["xx"], [["xx", "aa"], ["xx", "bb"]]) == [("aa",), ("bb",)])
before = [list(g) for g in groups]
gl.expand(st.query_terms("кошик"), groups)
check("expand changes neither its groups", groups == before)

print("RESULT:", "GREEN ✅" if not fails else "RED ❌", "(%d failed)" % fails)
sys.exit(1 if fails else 0)
