#!/usr/bin/env python3
"""Grow PM — a light Ukrainian/Russian/English stemmer and a safe FTS5 any-word expression (since v3.16.0).

The words of a note and the words of a question meet only if "компенсації" and "компенсація", "корзины" and
"корзина", "reviews" and "review" come out as one token. This module cuts a word to its stem the cheap way — no
dictionary, no model, the same result on every host — and builds the FTS5 expression a question becomes.

- STOP         the stop words of the three languages: they are dropped from a question, kept in the index text.
- tokens       the words of a text (letters, digits, apostrophes), NFC.
- norm / stem  one word: lower case, no apostrophe, ё -> е; then, for a Cyrillic word, the longest ending off.
- stem_text    the stems of a whole text, for the index.
- query_terms  the stems of a question without the stop words and the repeats, in the order they appear.
- raw_terms    the same words without the stem, for an index the plugin does not own (it stems nothing there).
- fts_or       an "any word" FTS5 expression where every term is a quoted phrase — so no word a person types
               is read as an operator, a column filter or a syntax error. No terms: "" (the caller does not search).

Stdlib only; reads and writes nothing; no network. The text functions raise nothing on any str or None, so a caller
that runs as a hook need not guard them.
"""
import re
import unicodedata

# Stop words: the least the spec names, plus the pronouns and prepositions the 2026-10-20 spike measured.
STOP = frozenset("""
і й та в у на з із зі за до по про для як що коли це не ми я чи від о а але або раз ще вже
и с как что
the a an to of in for and on how what is are by with
ти він вона вони наш наша які який яка яке скільки наскільки усі всі між через при після під над так також його її їх
""".split())

# A word is a run of digits, Latin and Ukrainian/Russian letters; an apostrophe (any of three) is part of a word.
_TOKEN = re.compile(r"[0-9A-Za-zА-Яа-яЁёЇїІіЄєҐґ'ʼ’]+")
_CYRILLIC = re.compile(r"[а-яіїєґ]")
_APOSTROPHES = ("'", "ʼ", "’")

# The noun, adjective and case endings of the 2026-10-20 spike (recon_scripts/lex.py), longest first: the longest that
# matches and leaves at least 3 letters is the one that goes. Ukrainian and Russian side by side — a Russian ending
# cannot be mistaken for a Ukrainian word's, and a mixed note is the usual case. No verb endings (-ти -ть -ться -ся -ла
# -ли -ло): they would cut the plurals «клієнти», «продукти», «запити», «роботи» to a stem the singular does not start
# with, and prefix matching only works from the shorter stem to the longer. No -ння either: «замовлення» loses its -я
# like any noun, and stem() then drops one н of the doubled нн, so that «замовлення», «замовлень», «замовленням» and
# «замовленнях» are one stem «замовлен» (the genitive plural has no second н), as «щоденний» and «щоденна» are «щоден».
ENDS = tuple(sorted(set("""
ами ями ові еві ого ому ими іми ій ий их іх им ім ою ею ої ей ів їв ах ях ом ем єм ам ям
его ему ыми ая яя ое ее ые ие ой ый ов ев
а я у ю і ї и е є о ь ы
""".split()), key=lambda e: (-len(e), e)))


def tokens(text):
    """The words of a text, in order, as they are written (case kept). NFC first, so a file name from macOS
    (a decomposed «й», «ї») reads as the same letters as one typed."""
    return _TOKEN.findall(unicodedata.normalize("NFC", text or ""))


def norm(word):
    """Lower case, the apostrophes (' ʼ ’) removed, ё -> е."""
    w = unicodedata.normalize("NFC", word or "").lower()
    for a in _APOSTROPHES:
        w = w.replace(a, "")
    return w.replace("ё", "е")


def stem(word):
    """The stem of one word (norm first). A Cyrillic word longer than 3 letters loses the longest ending of ENDS that
    leaves 3 letters at least, and if what is left ends in a doubled «нн» (only after a cut) one «н» goes too; a Latin
    word longer than 4 letters loses a final `s`; digits and short words stay."""
    w = norm(word)
    if len(w) > 3 and _CYRILLIC.search(w):
        for e in ENDS:
            if w.endswith(e) and len(w) - len(e) >= 3:
                w = w[:-len(e)]
                return w[:-1] if w.endswith("нн") else w
        return w
    if len(w) > 4 and w.endswith("s"):
        return w[:-1]
    return w


def stem_text(text):
    """The stems of all the words of a text, one space between — the text the index holds (stop words stay: a phrase
    keeps its shape). A word that is nothing but an apostrophe is not a word."""
    return " ".join(s for s in (stem(t) for t in tokens(text)) if s)


def query_terms(text):
    """The stems of a question without the stop words and without repeats, in the order they appear."""
    seen, out = set(), []
    for t in tokens(text):
        n = norm(t)
        if not n or n in STOP:
            continue
        s = stem(n)
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


def raw_terms(text):
    """The words of a question, normalised but not stemmed, without the stop words — for an index of someone else's
    that holds the words as written."""
    return [n for n in (norm(t) for t in tokens(text)) if n and n not in STOP]


def fts_or(terms, prefix=True):
    """An FTS5 expression that matches a note with any one of the terms: every term a double-quoted phrase (a quote
    inside it removed, so nothing a person types is an operator or breaks the syntax), with a `*` after the quotes when
    `prefix` and the term has 4 letters or more. No terms: "" — the caller then searches nothing, it does not send
    an empty MATCH."""
    parts = []
    for term in terms:
        t = (term or "").replace('"', "")
        if t:
            parts.append('"%s"%s' % (t, "*" if prefix and len(t) >= 4 else ""))
    return " OR ".join(parts)
