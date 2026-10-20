#!/usr/bin/env python3
"""Grow PM — the team glossary read for the section search (since v3.16.0).

A team calls one thing by several names — «кошик», «корзина», "cart", "basket" — and a note holds only one of them. The
glossary of the knowledge library (`skills/knowledge-library/references/glossary-workflows.md`) lists those names; the
search widens a question with the other names of a thing it already names, so the note that uses another word is
found as well (as a list of its own, at half weight — that is the caller's business).

- load      the approved terms of `<home>/.grow-pm/knowledge-library/glossary/_org.yaml` and of the product's file as
            groups of names, plus the reason when a file could not be read.
- expand    the stems of the other names of every group a question names.

The product's file is `<product_id>.yaml`, else `slugify(product).yaml`, else the only file that is not `_org.yaml`;
a product term replaces the `_org` term of the same `term`, whatever its status. A group is the `term`, the `en` (and
every abbreviation in its brackets — "product detail page (PDP)" is "product detail page" and "pdp"), the `variants` and
the `avoid` phrasings: a phrasing the team does not use is still one a source may use. Only `status: approved` entries
count; the `phrases:` list is the lint's. A file that cannot be read or is broken loses only itself: the other file is
loaded, and the reason names the broken one. Reads only; no network. Stdlib only.
"""
import functools
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx_common as cc  # noqa: E402
import ctx_stem as st  # noqa: E402

ORG = "_org.yaml"
_BRACKETS = re.compile(r"\(([^()]*)\)")


def _name(text):
    """A name the way a group holds it: NFC, one space between words, lower case."""
    return " ".join(cc.N(str(text)).split()).lower()


def _texts(value):
    """The strings of a field, whether it came as a list, as one scalar or empty."""
    if value is None or value == "":
        return []
    items = value if isinstance(value, list) else [value]
    return [str(v) for v in items if v is not None and str(v).strip()]


def _split_en(en):
    """("product detail page (PDP)") -> ("product detail page", ["PDP"]): what is outside the brackets, and each
    comma-, semicolon- or slash-separated piece inside them that is one word (a gloss with spaces is no abbreviation)."""
    abbreviations = []
    for inner in _BRACKETS.findall(en):
        for part in re.split(r"[,;/]", inner):
            part = part.strip()
            if part and not any(c.isspace() for c in part):
                abbreviations.append(part)
    return _BRACKETS.sub(" ", en), abbreviations


def _group(term, rec):
    names = [term]
    for en in _texts(rec.get("en")):
        name, abbreviations = _split_en(en)
        names.append(name)
        names.extend(abbreviations)
    names.extend(_texts(rec.get("variants")))
    names.extend(_texts(rec.get("avoid")))
    out = []
    for n in (_name(x) for x in names):
        if n and n not in out:
            out.append(n)
    return out


def _product_file(files, product, product_id):
    """The product's file among the names of the files that are not `_org.yaml`; None when none can be told."""
    by_name = {cc.N(f).casefold(): f for f in files}
    wanted = [str(product_id) if product_id else "", cc.slugify(product) if product and str(product).strip() else ""]
    for w in wanted:
        if w and cc.N(w + ".yaml").casefold() in by_name:       # a lookup in the listing: no id can walk out of the folder
            return by_name[cc.N(w + ".yaml").casefold()]
    return files[0] if len(files) == 1 else None


def _why(file, err):
    if isinstance(err, UnicodeDecodeError):
        reason = "not valid UTF-8"
    elif isinstance(err, OSError):
        reason = err.strerror or err.__class__.__name__
    else:
        reason = str(err)
    return "%s: %s" % (file, reason)


def _records(folder, file):
    with open(os.path.join(folder, file), encoding="utf-8-sig") as f:
        return cc.read_yaml_records(f.read(), "terms")


def load(home, product=None, product_id=None):
    """(groups, why). groups: a list of the names of one thing, lower case, the term first. why: None when every file
    that exists was read; else "<file>: <reason>" for each one that was not (joined with "; ") — the groups of the
    others are still returned. No glossary folder or no file in it: ([], None)."""
    folder = os.path.join(home, ".grow-pm", "knowledge-library", "glossary")
    try:
        files = sorted(f for f in os.listdir(folder) if f.endswith(".yaml") and os.path.isfile(os.path.join(folder, f)))
    except (FileNotFoundError, NotADirectoryError):
        return [], None
    except OSError as err:
        return [], _why("glossary", err)
    product_file = _product_file([f for f in files if f != ORG], product, product_id)
    merged, problems = {}, []
    for file in ([ORG] if ORG in files else []) + ([product_file] if product_file else []):
        try:
            records = _records(folder, file)
        except (OSError, ValueError) as err:
            problems.append(_why(file, err))
            continue
        for rec in records:
            term = (_texts(rec.get("term")) or [""])[0]
            if _name(term):
                merged[_name(term)] = rec                       # a later file (the product's) replaces, in place
    groups = []
    for key, rec in merged.items():
        if _name((_texts(rec.get("status")) or [""])[0]) == "approved":
            groups.append(_group(key, rec))
    return groups, "; ".join(problems) or None


@functools.lru_cache(maxsize=8192)
def _stems(name):
    """The stems of a name without the stop words — what a question's terms are made of, so the two compare."""
    return tuple(s for s in (st.stem(t) for t in st.tokens(name) if st.norm(t) not in st.STOP) if s)


def expand(terms, groups):
    """The other names of the groups a question names. `terms`: the stems of the question (ctx_stem.query_terms). A
    group is named when all the stems of at least one of its names are among the terms; the answer is the stems of its
    other names (each name a tuple of stems, in the order of the group), without repeats and without a name the
    question already holds. A name with no stems (stop words only) neither names a group nor is returned."""
    have = set(terms)
    out, seen = [], set()
    for group in groups:
        stems = [_stems(name) for name in group]
        if not any(s and have.issuperset(s) for s in stems):
            continue
        for s in stems:
            if s and s not in seen and not have.issuperset(s):
                seen.add(s)
                out.append(s)
    return out
