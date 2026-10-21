#!/usr/bin/env python3
"""Grow PM — the search's memory of your choices, and the golden set it is measured on (since v3.16.0).

A hint is what you chose in a search's block of options (search-protocol.md): "for this request the right note is
this one" (`good`), or "this one is not it" (`bad`). It is kept in the store, `<store>/.state/search.json` (schema
context-search-memory/1), never in a record — and with the discipline of `.state/slots.json`: a key this version does
not know is refused, never dropped (a save would lose what a newer version wrote; a new key needs
context-search-memory/2); a file that cannot be read is never reset — the search goes on without hints and says so in
one line. Its shape:
  {"schema", "hints": [{"q": the request as asked, "terms": [its stems, sorted], "product": "" | a product,
                        "good": [path[#heading]], "bad": [path[#heading]], "at": "YYYY-MM-DD"}]}
A hint is one per request and product: the same stems and the same product are one hint, whatever the words' order
and form.

- SCHEMA, FILE, WHERE           the schema, the file name inside `.state/`, how a message names it
- empty, load, save             read it (no file: an empty memory; a file that cannot be read, is not JSON, is of another
                                schema or not of this shape: a cs.StoreError «search memory not readable|not valid:
                                .state/search.json (<why>)»); write it (canonical, sorted, indented, atomic)
- terms, jaccard, similar       a request's stem set (ctx_stem.query_terms); the Jaccard similarity of two sets; is it
                                JACCARD (0.6) or more
- same_product                  two products are one (by name or slug; "Org: Product" is its product) or one is none
- match                         the hints that serve a new request: its stems (the first `--q` — the request, not its
                                variants) similar to a hint's, the products not different
- apply                         weigh the candidates of a search: a `good` note × GOOD_W (1.5), marked `твій вибір від
                                <день>`; a `bad` one marked `ти казав «не те»` (never taken silently; its weight stays)
- remember, forget              change a loaded memory in place (`ctx search remember|forget`)
- resolve                       a `--pick`/`--not` value: an id of the last searches (last.json) is its section,
                                `path#heading`; anything else is a path
- note_of, names                the note an entry `path[#heading]` names; does an entry name a note's path
- load_golden                   the golden set (schema search-golden/1): {store}/search/golden.yaml, the user's file —
                                read only, never written by ctx
- hint_rows                     the hints as rows of the golden set, `source: choice` (class `вибір`)
- evaluate                      the level-1 numbers of `ctx search eval`: recall50 (a `good` or `ok` among the first 50,
                                with the row's frozen variants), recall50_q_only, mrr (by the first `good`), by_class, n;
                                for the rows with no answer (class порожній) the mean number of candidates in the top 5

A pick names a note: one candidate per note (ctx_search.dedup), so a `path#heading` entry weighs the whole note, and
the golden set's `#heading` is read the same way. Reads and writes only `.state/search.json` (the writing commands of
ctx.py take the lock, the snapshot and the journal line); the golden set is only read. Stdlib only.
"""
import datetime
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx_common as cc  # noqa: E402
import ctx_stem as st  # noqa: E402
import ctx_store as cs  # noqa: E402

N = cc.N
SCHEMA = "context-search-memory/1"
GOLDEN_SCHEMA = "search-golden/1"
FILE = "search.json"
WHERE = ".state/" + FILE
JACCARD = 0.6                   # a hint serves a request whose stem set is this similar to its own, or more
_J_NUM, _J_DEN = 3, 5           # …the same, as a fraction: |a ∩ b| / |a ∪ b| ≥ 3/5, counted exactly
GOOD_W = 1.5                    # the weight of a `good` note of a hint that serves the request
CHOICE = "твій вибір від %s"
NOT_THAT = "ти казав «не те»"
UNREAD_NOTE = "пам'ять пошуку не прочитано (%s) — без підказок"
EMPTY_CLASS = "порожній"        # a golden row about what the base does not hold: `good: []`
CHOICE_CLASS = "вибір"          # the class of a hint read as a golden row
CHOICE_SOURCE = "choice"
POOL = 50                       # recall counts the first POOL candidates
TOP = 5                         # an empty row counts the candidates of its first TOP
_KEYS = ("schema", "hints")
_HINT_KEYS = ("q", "terms", "product", "good", "bad", "at")
_ROW_KEYS = ("q", "variants", "class", "product", "skill", "good", "ok", "bad", "source", "added", "note")
_LISTS = ("variants", "good", "ok", "bad")
_TEXTS = ("product", "skill", "source", "added")
_DAY = re.compile(r"\d{4}-\d{2}-\d{2}\Z")
_ID = re.compile(r"[0-9a-f]{10}\Z")
_SCHEMA_LINE = re.compile(r"""^schema\s*:\s*(?P<v>"[^"]*"|'[^']*'|[^\s#]+)\s*(?:#.*)?$""")


# ------------------------------------------------------------------ the memory
def empty():
    return {"schema": SCHEMA, "hints": []}


def _text(v):
    return isinstance(v, str) and bool(v.strip())


def _entries(v, what):
    if not isinstance(v, list) or not all(_text(x) for x in v):
        raise ValueError("%s is not a list of paths" % what)
    return list(dict.fromkeys(N(x.strip()) for x in v))


def _clean(data):
    """`data` as the canonical memory: hints sorted by their stems and product, each once — two of the same request and
    product are one, their good and bad merged (the later one's word wins for a note both name) and the later day.
    A schema that is not SCHEMA, a part of the wrong shape or a key nobody knows is a ValueError that says which."""
    if not isinstance(data, dict):
        raise ValueError("not an object")
    if data.get("schema") != SCHEMA:
        raise ValueError("schema is %r, not %r" % (data.get("schema"), SCHEMA))
    extra = sorted(str(k) for k in data if k not in _KEYS)
    if extra:
        raise ValueError("unknown key: %s" % ", ".join(extra))
    hints = data.get("hints", [])
    if not isinstance(hints, list):
        raise ValueError("hints is not a list")
    out = empty()
    for i, h in enumerate(hints, 1):
        if not isinstance(h, dict):
            raise ValueError("hint %d is not an object" % i)
        extra = sorted(str(k) for k in h if k not in _HINT_KEYS)
        if extra:
            raise ValueError("hint %d: unknown key: %s" % (i, ", ".join(extra)))
        if not _text(h.get("q")):
            raise ValueError("hint %d has no q" % i)
        stems = h.get("terms")
        if not isinstance(stems, list) or not stems or not all(_text(t) for t in stems):
            raise ValueError("hint %d: terms is not a list of stems" % i)
        product = h.get("product", "")
        if not isinstance(product, str):
            raise ValueError("hint %d: product is not text" % i)
        good, bad = _entries(h.get("good", []), "hint %d: good" % i), _entries(h.get("bad", []), "hint %d: bad" % i)
        if not good and not bad:
            raise ValueError("hint %d has neither good nor bad" % i)
        if not isinstance(h.get("at"), str) or not _DAY.match(h["at"]):
            raise ValueError("hint %d: at is not YYYY-MM-DD" % i)
        one = {"q": N(h["q"].strip()), "terms": sorted(set(N(t) for t in stems)), "product": N(product.strip()),
               "good": good, "bad": bad, "at": h["at"]}
        twin = _find(out, one["terms"], one["product"])
        if twin is None:
            out["hints"].append(one)
        else:
            _merge(twin, one["good"], one["bad"])
            if one["at"] >= twin["at"]:
                twin["at"], twin["q"] = one["at"], one["q"]
    out["hints"].sort(key=lambda h: (h["terms"], _product_key(h["product"])))
    return out


def _error(kind, why):
    return cs.StoreError("search memory %s: %s (%s)" % (kind, WHERE, " ".join(str(why).split())[:300]))


def load(store, timeout=None):
    """The memory of `store` (a ctx_store.Store), canonical. No file is an empty memory. A file that cannot be read
    within `timeout` (cs.read_timeout when None) → cs.StoreError «search memory not readable: .state/search.json
    (<why>)»; one that is not JSON, is of another schema or not of the shape → «search memory not valid: …». It is never
    reset silently."""
    path = os.path.join(store.state_dir, FILE)
    if not os.path.lexists(path):
        return empty()
    try:
        raw = cs.read_text(path, timeout=timeout)
    except FileNotFoundError:
        return empty()
    except (OSError, UnicodeDecodeError, cs.StoreError) as e:
        raise _error("not readable", getattr(e, "strerror", None) or e)
    try:
        return _clean(json.loads(raw))
    except ValueError as e:
        raise _error("not valid", e)


def save(store, mem):
    """Write the memory (canonical, sorted, indented, atomic) and return what was written. A memory of the wrong shape →
    cs.StoreError «search memory not valid: …», nothing written."""
    try:
        clean = _clean(mem)
    except ValueError as e:
        raise _error("not valid", e)
    cs.atomic_write(os.path.join(store.state_dir, FILE), json.dumps(clean, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
    cs.remove_stale_tmp(store.state_dir)
    return clean


# ------------------------------------------------------------------ similarity and products
def terms(q):
    """The stem set of a request, sorted (ctx_stem.query_terms: no stop words, no repeats)."""
    return sorted(set(st.query_terms(q or "")))


def jaccard(a, b):
    """|a ∩ b| / |a ∪ b|; 0 when both are empty."""
    a, b = set(a), set(b)
    return len(a & b) / len(a | b) if a | b else 0.0


def similar(a, b):
    """Is the Jaccard similarity of the two sets JACCARD or more — counted on whole numbers, so 3 of 5 is 0.6 exactly."""
    a, b = set(a), set(b)
    return bool(a | b) and _J_DEN * len(a & b) >= _J_NUM * len(a | b)


def _product_names(product):
    s = N(str(product or "")).strip()
    return {cc.slugify(x) for x in (s, s.split(":", 1)[-1]) if x.strip()} - {""} if s else set()


def _product_key(product):
    """A hint's product as its identity: the slug of the product ("Org: Product" is its product); "" for none."""
    s = N(str(product or "")).strip()
    return cc.slugify(s.split(":", 1)[-1]) if s else ""


def same_product(a, b):
    """No product on one side, or the same product on both (by name or slug; "Org: Product" is its product)."""
    na, nb = _product_names(a), _product_names(b)
    return not na or not nb or bool(na & nb)


def match(mem, query, product=None):
    """The hints of `mem` that serve `query` (the request — the first `--q`, not its variants): their stems similar
    (JACCARD) and their products not different (same_product)."""
    qt = set(terms(query))
    if not qt:
        return []
    return [h for h in (mem or {}).get("hints") or [] if similar(qt, h.get("terms") or ())
            and same_product(h.get("product"), product)]


# ------------------------------------------------------------------ entries and notes
def note_of(entry):
    """The note an entry names: `path#heading` → path (the first `.md#` ends it, so a `#` in a folder's or a file's name
    stays), a path → itself."""
    entry = N(str(entry or "")).strip()
    i = entry.find(".md#")
    return entry[:i + 3] if i >= 0 else entry


def names(entry, path):
    """Does the entry (`path` or `path#heading`) name the note at `path`?"""
    entry, path = N(str(entry or "")).strip(), N(str(path or "")).strip()
    return bool(path) and (entry == path or entry.startswith(path + "#"))


def _flag(cand, mark):
    flags = cand.setdefault("flags", [])
    if mark not in flags:
        flags.append(mark)


def apply(cands, hints, today):
    """Weigh the candidates of a search in place by the hints that serve it (`match`): a note one of them names `good` —
    any of its sections, or the note itself, or a note it stands for (its `twins`: folded into it, since v3.16.2) —
    gets × GOOD_W once, however many name it, and the mark `твій вибір від <день>` (the latest day of those hints;
    `today` for a hint with none); a note one names `bad` gets the mark `ти казав «не те»` and keeps its weight. The
    caller sorts again before it cuts the best N."""
    if not hints:
        return
    day = today.isoformat() if isinstance(today, (datetime.date, datetime.datetime)) else str(today or "")[:10]
    for c in cands or []:
        paths = [c.get("path")] + list(c.get("twins") or [])
        goods = [h for h in hints if any(names(e, p) for e in h.get("good") or [] for p in paths)]
        if goods:
            c["score"] = float(c.get("score") or 0.0) * GOOD_W
            _flag(c, CHOICE % max(h.get("at") or day for h in goods))
        if any(names(e, p) for h in hints for e in h.get("bad") or [] for p in paths):
            _flag(c, NOT_THAT)


def _find(mem, stems, product):
    key = _product_key(product)
    return next((h for h in mem["hints"] if h["terms"] == list(stems) and _product_key(h["product"]) == key), None)


def _merge(h, good, bad):
    """Put `good` and `bad` into the hint: a note now good leaves its bad, and the other way round."""
    for new, mine, other in ((good, "good", "bad"), (bad, "bad", "good")):
        for e in new:
            h[other] = [x for x in h[other] if note_of(x) != note_of(e)]
            h[mine] = [x for x in h[mine] if note_of(x) != note_of(e)] + [e]


def remember(mem, q, product, good, bad, day):
    """Remember in `mem` (in place) that for the request `q` (of `product`, or none) the notes `good` are right and
    `bad` are not. The same request — the same stems — and the same product is one hint: the new words go into it
    (a note named again moves to the side it is named on now) and it takes the day and the request as asked now.
    True when the memory changed; False when it already said so. A request with no words (stop words only), or neither
    a good nor a bad note, is a ValueError."""
    stems = terms(q)
    if not stems:
        raise ValueError("the request %r has no words to remember (only stop words)" % q)
    good = list(dict.fromkeys(N(e) for e in good or []))
    bad = list(dict.fromkeys(N(e) for e in bad or []))
    if not good and not bad:
        raise ValueError("nothing to remember for %r: neither a right note nor a wrong one" % q)
    product = N(str(product or "").strip())
    h = _find(mem, stems, product)
    if h is None:
        mem["hints"].append({"q": N(q.strip()), "terms": stems, "product": product, "good": [], "bad": [], "at": day})
        h = mem["hints"][-1]
        _merge(h, good, bad)
        return True
    before = (list(h["good"]), list(h["bad"]))
    _merge(h, good, bad)
    if (sorted(h["good"]), sorted(h["bad"])) == (sorted(before[0]), sorted(before[1])):
        h["good"], h["bad"] = before
        return False
    h["q"], h["at"] = N(q.strip()), day
    return True


def forget(mem, q, product=None):
    """Drop from `mem` (in place) the hints of the request `q` (the same stems): of `product` only when it is named,
    else of every product. Returns how many were dropped."""
    stems = terms(q)
    key = _product_key(product) if product else None
    keep = [h for h in mem["hints"] if not (h["terms"] == stems and (key is None or _product_key(h["product"]) == key))]
    gone = len(mem["hints"]) - len(keep)
    mem["hints"] = keep
    return gone


def resolve(value, last_file):
    """A `--pick` or `--not` value as the memory keeps it. An id of the last searches (10 hex digits; `last_file` is
    ctx_search.last_path, the ids `ctx search` saved) is the section it names, `path#heading` (a note-level candidate:
    its path); an id no search gave is a ValueError. Anything else is a note's path as the search names it, its `\\`
    turned into `/` and a leading `./` dropped."""
    v = N(str(value or "")).strip()
    if _ID.match(v.lower()):
        try:
            with open(last_file, encoding="utf-8") as f:
                entry = json.load(f).get(v.lower())
        except (OSError, ValueError, AttributeError):
            entry = None
        if not isinstance(entry, dict) or not _text(entry.get("path")):
            raise ValueError("no candidate %s in the last searches — search again, or give the note's path" % v)
        heading = entry.get("heading") or ""
        return N(entry["path"]) + ("#" + heading if heading else "")
    v = v.replace("\\", "/")
    while v.startswith("./"):
        v = v[2:]
    if not v:
        raise ValueError("an empty path")
    return v


# ------------------------------------------------------------------ the golden set
def _scalar_text(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v) if isinstance(v, int) else v


def _row(i, rec, where):
    """One row of the golden set, canonical, or a ValueError that names it."""
    name = "%s: row %d" % (where, i)
    extra = sorted(k for k in rec if k not in _ROW_KEYS)
    if extra:
        raise ValueError("%s: unknown key: %s" % (name, ", ".join(extra)))
    out = {}
    for key in ("q", "class"):
        v = _scalar_text(rec.get(key))
        if not _text(v):
            raise ValueError("%s has no %s" % (name, key))
        out[key] = N(v.strip())
    if "good" not in rec:
        raise ValueError("%s has no good (an empty row: class %s, good: [])" % (name, EMPTY_CLASS))
    for key in _LISTS:
        v = rec.get(key, [])
        v = [] if v == "" else [v] if not isinstance(v, list) else v
        v = [_scalar_text(x) for x in v]
        if not all(_text(x) for x in v):
            raise ValueError("%s: %s is not a list of texts" % (name, key))
        out[key] = [N(x.strip()) for x in v]
    for key in _TEXTS:
        v = _scalar_text(rec.get(key, ""))
        if not isinstance(v, str):
            raise ValueError("%s: %s is not text" % (name, key))
        out[key] = N(v.strip())
    if out["class"] == EMPTY_CLASS and out["good"]:
        raise ValueError("%s: a row of class %s has no good answers (good: [])" % (name, EMPTY_CLASS))
    if out["class"] != EMPTY_CLASS and not out["good"]:
        raise ValueError("%s: good is empty — only a row of class %s has no answer" % (name, EMPTY_CLASS))
    return {k: out[k] for k in _ROW_KEYS if k in out}


def load_golden(path):
    """The rows of a golden set (`schema: search-golden/1`, its rows under `queries:`; ctx_common.read_yaml_records),
    each {q, variants, class, product, skill, good, ok, bad, source, added} — the lists [] and the texts "" when a row
    leaves them out. Read with `utf-8-sig`: a file that starts with a BOM reads the same. `q`, `class` and `good` are
    required; `good: []` is a row of class порожній and only that (and the other way round); a key nobody knows, another
    schema or none, a YAML this reader does not take: a ValueError that names the file (and the row). OSError when the
    file cannot be read."""
    with open(path, encoding="utf-8-sig") as f:
        text = f.read()
    where = os.path.basename(path)
    schema = None
    for raw in text.replace("\r\n", "\n").split("\n"):
        m = _SCHEMA_LINE.match(raw)
        if m:
            schema = m.group("v").strip("'\"")
            break
    if schema != GOLDEN_SCHEMA:
        raise ValueError("%s: schema is %r, not %r" % (where, schema, GOLDEN_SCHEMA))
    try:
        recs = cc.read_yaml_records(text, "queries")
    except ValueError as e:
        raise ValueError("%s: %s" % (where, e))
    return [_row(i, rec, where) for i, rec in enumerate(recs, 1)]


def hint_rows(mem):
    """The hints of `mem` as rows of the golden set: `source: choice`, class `вибір`, no variants, `good` and `bad` as
    remembered, `added` the hint's day. A hint with no `good` (only «не те») is no row: it has no answer to look for."""
    return [{"q": h["q"], "variants": [], "class": CHOICE_CLASS, "product": h.get("product") or "", "skill": "",
             "good": list(h["good"]), "ok": [], "bad": list(h.get("bad") or []), "source": CHOICE_SOURCE,
             "added": h.get("at") or ""} for h in (mem or {}).get("hints") or [] if h.get("good")]


def _rank(cands, entries):
    """The place (from 1) of the first of the first POOL candidates that one of `entries` names — the candidate or a
    note folded into it (`twins`, since v3.16.2); None when none does."""
    for i, c in enumerate((cands or [])[:POOL], 1):
        if any(names(e, p) for e in entries for p in [c.get("path")] + list(c.get("twins") or [])):
            return i
    return None


def _share(rows, key):
    return sum(1 for r in rows if r[key] is not None) / len(rows) if rows else None


def evaluate(rows, ask):
    """The level-1 numbers of a golden set. `ask(queries, row)` is one search — ctx_search.run's result, of which
    `candidates` (best first), `notes` and `sources` are read. For each row with an answer: the question and its frozen
    variants (`[q] + variants`), and the question alone (one search when it has no variants); for each empty row the
    question and its variants. Returns {n, recall50, recall50_q_only, mrr, by_class {class: {n, recall50,
    recall50_q_only, mrr}}, empty_n, empty_top5_mean, rows [{q, class, source, rank, rank_q_only, rank_good} | {q, class,
    source, top5}], notes} — recall: a `good` or `ok` entry names one of the first 50; mrr: 1 / the place of the first
    `good` (0 when none); None for a number with no row behind it."""
    done, gone, every, notes = [], [], [], []

    def search(queries, row):
        res = ask(queries, row) or {}
        for n in res.get("notes") or []:
            if n not in notes:
                notes.append(n)
        return res.get("candidates") or []

    for row in rows or []:
        q, variants = row["q"], list(row.get("variants") or [])
        if not row.get("good"):
            cands = search([q] + variants, row)
            gone.append({"q": q, "class": row["class"], "source": row.get("source") or "", "top5": min(TOP, len(cands))})
            every.append(gone[-1])
            continue
        right = list(row["good"]) + list(row.get("ok") or [])
        cands = search([q] + variants, row)
        alone = search([q], row) if variants else cands
        done.append({"q": q, "class": row["class"], "source": row.get("source") or "", "rank": _rank(cands, right),
                     "rank_q_only": _rank(alone, right), "rank_good": _rank(cands, row["good"])})
        every.append(done[-1])

    def numbers(part):
        return {"n": len(part), "recall50": _share(part, "rank"), "recall50_q_only": _share(part, "rank_q_only"),
                "mrr": sum(1.0 / r["rank_good"] for r in part if r["rank_good"]) / len(part) if part else None}

    by_class = {}
    for r in done:
        by_class.setdefault(r["class"], []).append(r)
    out = numbers(done)
    out.update(by_class={k: numbers(v) for k, v in by_class.items()}, empty_n=len(gone),
               empty_top5_mean=sum(r["top5"] for r in gone) / len(gone) if gone else None,
               rows=every,
               notes=notes)
    return out
