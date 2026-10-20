#!/usr/bin/env python3
"""TC-ctx-3160-stem — scripts/ctx_stem.py: the light Ukrainian/Russian/English stemmer and the safe FTS5 any-word
expression the section search (since v3.16.0) is built on.

A word is cut to its stem (a Cyrillic ending off, a Latin plural `s` off, digits as they are), the stop words fall out of a
query, and the stems become an OR expression of quoted terms — so that no word the user types can be read by FTS5 as an
operator, a column filter or a syntax error. A query of stop words alone gives an empty expression, not an error.
Stdlib only (sqlite3 with FTS5 for the acceptance cases); run from the repo root.
"""
import os, re, sqlite3, sys, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import ctx_stem as st  # noqa: E402

fails = 0


def check(name, cond, detail=""):
    global fails
    fails += not cond
    print(("✅" if cond else "❌"), name, ("" if cond else "-> " + str(detail)[:900]))


# --- the stemmer: forms of one word meet in one stem ---------------------------------------------------------------
same = [("компенсація", "компенсації"), ("кабінеті", "кабінет"), ("конверсія", "конверсії"), ("кошику", "кошик"),
        ("продавцями", "продавця"), ("корзина", "корзины"), ("заказов", "заказы"), ("reviews", "review"),
        ("зв'язки", "звʼязки"),
        # noun plurals and case forms must not be cut as if they were verb forms (-ти, -ть, -ться, -ся, -ла, -ли, -ло, -ння)
        ("клієнт", "клієнти"), ("продукт", "продукти"), ("запит", "запити"), ("тест", "тести"), ("робота", "роботи"),
        ("замовлення", "замовленням")]
for a, b in same:
    check("same stem: %s ~ %s" % (a, b), st.stem(a) == st.stem(b), (st.stem(a), st.stem(b)))
check("a different word keeps a different stem", st.stem("відгук") != st.stem("відхід") and st.stem("кошик") != st.stem("кабінет"),
      (st.stem("відгук"), st.stem("відхід")))

# --- the stemmer: the rules, one by one ----------------------------------------------------------------------------
check("a Cyrillic word of up to 3 letters is left whole", st.stem("зуб") == "зуб" and st.stem("ліс") == "ліс" and st.stem("дім") == "дім",
      (st.stem("зуб"), st.stem("ліс"), st.stem("дім")))
check("the longest ending goes: -ами off «рамами», not only -и", st.stem("рамами") == "рам" and st.stem("продавцями") == "продавц",
      (st.stem("рамами"), st.stem("продавцями")))
check("an ending that would leave under 3 letters is not cut; a shorter one that leaves 3 still is",
      st.stem("мами") == "мам" and st.stem("води") == "вод" and st.stem("зона") == "зон",
      (st.stem("мами"), st.stem("води"), st.stem("зона")))
check("a word with no ending of the list is as it is", st.stem("кабінет") == "кабінет" and st.stem("відгук") == "відгук",
      (st.stem("кабінет"), st.stem("відгук")))
check("a Latin word loses a final s only when longer than 4 letters", st.stem("reviews") == "review" and st.stem("tests") == "test"
      and st.stem("tags") == "tags" and st.stem("bus") == "bus" and st.stem("seller") == "seller",
      [st.stem(w) for w in ("reviews", "tests", "tags", "bus", "seller")])
check("digits and codes are as they are", st.stem("3930") == "3930" and st.stem("1") == "1" and st.stem("ZORG") == "zorg",
      (st.stem("3930"), st.stem("1"), st.stem("ZORG")))
check("stem lowers the case, drops the apostrophes and turns ё into е", st.stem("КОМПЕНСАЦІЇ") == st.stem("компенсація")
      and st.stem("ЁЛКА") == st.stem("елка") and st.norm("Зв'язок") == "звязок",
      (st.stem("КОМПЕНСАЦІЇ"), st.stem("ЁЛКА"), st.norm("Зв'язок")))

# --- norm and tokens -----------------------------------------------------------------------------------------------
check("norm: lower case, apostrophes (' ʼ ’) off, ё -> е",
      st.norm("Зв'язок") == "звязок" and st.norm("звʼязок") == "звязок" and st.norm("зв’язок") == "звязок"
      and st.norm("Ёлка") == "елка" and st.norm("Ґанок") == "ґанок" and st.norm("ЇЖАК") == "їжак",
      [st.norm(w) for w in ("Зв'язок", "звʼязок", "зв’язок", "Ёлка", "Ґанок", "ЇЖАК")])
check("a Jira key splits into its parts", st.tokens("ZORG-3930.2") == ["ZORG", "3930", "2"])
check("tokens keep the case and the apostrophe, drop the punctuation",
      st.tokens("Зв'язок, «відгуки»! (Q3)") == ["Зв'язок", "відгуки", "Q3"], st.tokens("Зв'язок, «відгуки»! (Q3)"))
check("tokens read a decomposed й and ї (macOS NFD) as whole letters",
      st.tokens(unicodedata.normalize("NFD", "міжнародний їжак")) == ["міжнародний", "їжак"],
      st.tokens(unicodedata.normalize("NFD", "міжнародний їжак")))
check("tokens of nothing are nothing", st.tokens("") == [] and st.tokens(None) == [] and st.tokens("?!… —") == [])

# --- stop words ----------------------------------------------------------------------------------------------------
MUST_STOP = ("і й та в у на з із зі за до по про для як що коли це не ми я чи від о а але або раз ще вже і и с как что "
             "the a an to of in for and on how what is are by with").split()
check("STOP holds the stop words of the brief", isinstance(st.STOP, frozenset) and all(w in st.STOP for w in MUST_STOP),
      [w for w in MUST_STOP if w not in st.STOP])
check("STOP keeps the content words out", not any(w in st.STOP for w in ("відгук", "кабінет", "продавець", "review", "1")))
check("stop words drop out of a query", st.query_terms("як ми відсікаємо фейкові відгуки") == [st.stem("відсікаємо"), st.stem("фейкові"), st.stem("відгуки")])
check("an all-stop query is empty, and its expression too", st.query_terms("що і як?") == [] and st.fts_or([]) == "")
check("a query of punctuation or nothing is empty", st.query_terms("?!…") == [] and st.query_terms("") == [] and st.query_terms(None) == [])
check("1:1 keeps its digits", st.query_terms("1:1") == ["1"])
check("query_terms: no repeats, in the order of appearance", st.query_terms("відгуки продавця відгук Продавцям")
      == [st.stem("відгуки"), st.stem("продавця")], st.query_terms("відгуки продавця відгук Продавцям"))
check("query_terms: the case of a stop word does not matter", st.query_terms("The Review AND How") == ["review"], st.query_terms("The Review AND How"))
check("a lone apostrophe is not a term", st.query_terms("' ʼ ’ відгук") == [st.stem("відгук")] and st.raw_terms("' відгук") == ["відгук"])

# --- stem_text, raw_terms ------------------------------------------------------------------------------------------
check("stem_text: the stems of all tokens, stop words kept, one space between",
      st.stem_text("Як ми відсікаємо фейкові відгуки") == " ".join(st.stem(w) for w in ("Як", "ми", "відсікаємо", "фейкові", "відгуки")),
      st.stem_text("Як ми відсікаємо фейкові відгуки"))
check("stem_text of nothing is empty", st.stem_text("") == "" and st.stem_text(None) == "" and st.stem_text("?!") == "")
check("stem_text and query_terms stem a word the same way", st.stem_text("Компенсації") == st.query_terms("компенсація")[0])
check("raw_terms: norm without stop words and without a stem",
      st.raw_terms("Як ми відсікаємо ЗВ'ЯЗКИ та Ёлки") == ["відсікаємо", "звязки", "елки"], st.raw_terms("Як ми відсікаємо ЗВ'ЯЗКИ та Ёлки"))

# --- fts_or --------------------------------------------------------------------------------------------------------
check("fts_or: quoted terms joined by OR, a star after a term of 4 letters or more",
      st.fts_or(["відгук", "кіт", "1"]) == '"відгук"* OR "кіт" OR "1"', st.fts_or(["відгук", "кіт", "1"]))
check("fts_or: prefix=False gives no star", st.fts_or(["відгук", "кабінет"], prefix=False) == '"відгук" OR "кабінет"',
      st.fts_or(["відгук", "кабінет"], prefix=False))
check("fts_or: 4 letters is the threshold", st.fts_or(["abcd"]) == '"abcd"*' and st.fts_or(["abc"]) == '"abc"')
check("fts_or: inner quotes are gone", st.fts_or(['a"b"c', '"']) == '"abc"' and st.fts_or(['"ab"cd']) == '"abcd"*',
      (st.fts_or(['a"b"c', '"']), st.fts_or(['"ab"cd'])))
check("fts_or of nothing is empty", st.fts_or([]) == "" and st.fts_or([""]) == "" and st.fts_or(['"', '""']) == "")
check("operators and quotes are inert", st.fts_or(st.query_terms('NEAR "OR" a:b ^x *y')) .count('"') % 2 == 0
      and " AND " not in st.fts_or(st.query_terms("AND NOT")))
HOSTILE = 'NEAR "OR" a:b ^x *y (z) NOT col:val -w'
check("every piece of the expression is one quoted term (a star after it at most), nothing else",
      all(re.fullmatch(r'"[^"]+"\*?', piece) for piece in st.fts_or(st.query_terms(HOSTILE)).split(" OR ")), st.fts_or(st.query_terms(HOSTILE)))

# --- FTS5 takes every expression ------------------------------------------------------------------------------------
QUERIES = ["як ми відсікаємо фейкові відгуки", "що і як?", "1:1", "ZORG-3930.2", 'NEAR "OR" a:b ^x *y', "AND NOT",
           'NEAR "OR" a:b ^x *y (z) NOT col:val -w', "", "?!…", "' ʼ ’", 'a "b" "', "OR", "NOT", "AND", "NEAR", "title:відгук",
           "відгук*", "{body}: x", "x + y", "(((", "))) ---", "компенсація 'продавцям' «кабінеті»", "ё Ёлка зв'язки Ґанок їжак"]
EXTRA_TERMS = [['"'], ['""'], ["a*b"], ["x-y"], ["NEAR("], ["'"], ["ʼ"], ["відгук", ""], ["\n"], ["a b"], ["^x"], ["OR"], ["AND", "NOT"]]
try:
    db = sqlite3.connect(":memory:")
    db.execute("CREATE VIRTUAL TABLE t USING fts5(body, tokenize='unicode61 remove_diacritics 2')")
    bad, tried = [], 0
    for q in QUERIES:
        for prefix in (True, False):
            expr = st.fts_or(st.query_terms(q), prefix)
            for e in ([expr] if expr else []):
                tried += 1
                try:
                    list(db.execute("SELECT rowid FROM t WHERE t MATCH ?", (e,)))
                except sqlite3.OperationalError as err:
                    bad.append((q, prefix, e, str(err)))
    for terms in EXTRA_TERMS:
        for prefix in (True, False):
            expr = st.fts_or(terms, prefix)
            for e in ([expr] if expr else []):
                tried += 1
                try:
                    list(db.execute("SELECT rowid FROM t WHERE t MATCH ?", (e,)))
                except sqlite3.OperationalError as err:
                    bad.append((terms, prefix, e, str(err)))
    # an empty expression is never sent to MATCH: the callers test for "" first (that is what "" is for)
    check("FTS5 accepts every expression (MATCH on an empty table raises no OperationalError)", bad == [] and tried >= 30, (bad, tried))

    # --- the two halves meet: stem_text into an index, fts_or out of it ---------------------------------------------
    db.execute("CREATE VIRTUAL TABLE s USING fts5(body, tokenize='unicode61 remove_diacritics 2')")
    DOCS = {1: "Компенсація продавцям за фейкові відгуки", 2: "Налаштування кабінету продавця", 3: "Корзина покупця і заказы",
            4: "Reviews of the seller: ZORG-3930.2", 5: "Щотижневий 1:1 з командою", 6: "Зв'язки з клієнтами"}
    for i, text in DOCS.items():
        db.execute("INSERT INTO s(rowid, body) VALUES (?, ?)", (i, st.stem_text(text)))

    def hits(q, prefix=True):
        expr = st.fts_or(st.query_terms(q), prefix)
        return [r[0] for r in db.execute("SELECT rowid FROM s WHERE s MATCH ? ORDER BY rowid", (expr,))] if expr else []

    check("a query in another form finds the note: «компенсації» -> 1", hits("компенсації") == [1], hits("компенсації"))
    check("other cases of a noun meet: «кабінеті» -> 2, «продавцями» -> 1 and 2",
          hits("кабінеті") == [2] and hits("продавцями") == [1, 2], (hits("кабінеті"), hits("продавцями")))
    check("Russian forms meet: «корзины заказов» -> 3", hits("корзины заказов") == [3], hits("корзины заказов"))
    check("English plural meets singular: «review» -> 4, «reviews» -> 4", hits("review") == [4] and hits("reviews") == [4], (hits("review"), hits("reviews")))
    check("a Jira key is found by its number: «ZORG-3930» -> 4", 4 in hits("ZORG-3930"), hits("ZORG-3930"))
    check("«1:1» finds the note with that digit", hits("1:1") == [5], hits("1:1"))
    check("the apostrophe forms meet: «зв'язки» and «звʼязки» -> 6", hits("зв'язки") == [6] and hits("звʼязки") == [6], (hits("зв'язки"), hits("звʼязки")))
    check("an OR expression finds a note for any one word", set(hits("фейкові кабінету")) == {1, 2}, hits("фейкові кабінету"))
    check("a query of stop words finds nothing and does not fail", hits("що і як?") == [], hits("що і як?"))
except sqlite3.OperationalError as err:
    check("FTS5 is available in this Python's sqlite3 (the section search needs it)", False, err)

print("RESULT:", "GREEN ✅" if not fails else "RED ❌", "(%d failed)" % fails)
sys.exit(1 if fails else 0)
