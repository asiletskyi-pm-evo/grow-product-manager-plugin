#!/usr/bin/env python3
"""Grow PM — where each field of your context came from (since v3.22.0).

A record carries one `source` — who wrote it last. Since v3.22.0 a field (`- **Field:** value`) and a line a write
added keep their own, in `<store>/.state/sources.json` (schema context-sources/1): what wrote them (`user`,
`derived:jira`, `inbox:<skill>` …), where (`ref`), the day and, for what the configurator derived, how sure it was. The
entry holds a hash of the value it was written with: once the value changes by any other way (your edit in Obsidian, an
import) the entry no longer applies and the field falls back to its record's `source`. So every field has a source.
Semantics: references/context-protocol.md §5k.

- SCHEMA, FILE, WHERE     the file; load(store) / save(store, mem): a key this build does not know is refused, a file
                          that cannot be read stops the run — never reset
- field_key(name), line_key(line)   the key of a field, of a line
- note(mem, rid, key, value, kind, ref, at, confidence)   remember one
- adopt(mem, rec)         before a record is rewritten: its fields with no entry keep the record's present source
- note_import(mem, old, new_body, kind, at)   an imported edit: the fields it changed are the editor's
- of(mem, rec)            [{key, label, kind, ref, at, confidence, own}] — every field of the record (and every line
                          an entry knows) with the source that applies; own=False → the record's
- coverage(mem, recs)     (fields with their own source, all fields)

Writes nothing itself: the lock, the snapshot and the journal are ctx.py's. Stdlib only.
"""
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx_common as cc  # noqa: E402
import ctx_store as cs  # noqa: E402

SCHEMA = "context-sources/1"
FILE = "sources.json"
WHERE = ".state/" + FILE
_KEYS = ("schema", "records")
_ENTRY_KEYS = ("kind", "ref", "at", "confidence", "v")
_DAY = re.compile(r"\d{4}-\d{2}-\d{2}\Z")
LEVELS = ("high", "medium", "low")


def empty():
    return {"schema": SCHEMA, "records": {}}


def _error(kind, why):
    return cs.StoreError("sources %s: %s (%s)" % (kind, WHERE, " ".join(str(why).split())[:300]))


def _norm(s):
    return " ".join((s or "").split())


def _h(s):
    return hashlib.sha1(_norm(s).encode("utf-8")).hexdigest()[:12]


def field_key(name):
    return "field:" + _norm(name)


def line_key(line):
    return "line:" + _h(line)


def _clean(raw):
    if not isinstance(raw, dict) or raw.get("schema") != SCHEMA:
        raise ValueError("not of schema %s" % SCHEMA)
    unknown = sorted(set(raw) - set(_KEYS))
    if unknown:
        raise ValueError("unknown key(s) %s — a newer plugin wrote it" % ", ".join(unknown))
    recs = raw.get("records", {})
    if not isinstance(recs, dict):
        raise ValueError("records is an object")
    out = empty()
    for rid, fields in recs.items():
        if not isinstance(rid, str) or not cs.ID_RE.match(rid) or not isinstance(fields, dict):
            raise ValueError("a record entry of another shape")
        for key, e in fields.items():
            if not (isinstance(key, str) and key.startswith(("field:", "line:"))) or not isinstance(e, dict) \
                    or sorted(set(e) - set(_ENTRY_KEYS)) or not isinstance(e.get("kind"), str) or not e["kind"] \
                    or not isinstance(e.get("v"), str):
                raise ValueError("an entry of another shape")
            if e.get("at") is not None and not (isinstance(e["at"], str) and _DAY.match(e["at"])):
                raise ValueError("an entry's day is not YYYY-MM-DD")
            if e.get("confidence") is not None and e["confidence"] not in LEVELS:
                raise ValueError("an entry's confidence is one of %s" % ", ".join(LEVELS))
            if e.get("ref") is not None and not isinstance(e["ref"], str):
                raise ValueError("an entry's ref is text")
            out["records"].setdefault(rid, {})[key] = {k: e.get(k) for k in _ENTRY_KEYS}
    return out


def load(store, timeout=None):
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
    try:
        clean = _clean(mem)
    except ValueError as e:
        raise _error("not valid", e)
    cs.atomic_write(os.path.join(store.state_dir, FILE), json.dumps(clean, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
    return clean


def note(mem, rid, key, value, kind, ref=None, at=None, confidence=None):
    mem["records"].setdefault(rid, {})[key] = {"kind": kind, "ref": ref or None, "at": (at or None) and at[:10],
                                                "confidence": confidence, "v": _h(value)}


def note_body(mem, rid, body, kind, ref=None, at=None, confidence=None):
    """Every field of a body (a record just added) from one source."""
    for name, value in fields(body):
        note(mem, rid, field_key(name), value, kind, ref, at, confidence)


def fields(body):
    """[(name, value)] of the `- **Field:** value` lines outside managed regions, in order, first of each name."""
    spans, seen, out = cc.managed_spans(body), set(), []
    for off, core, _ in cs._lines(body):
        m = cs.FIELD_RE.match(core)
        if m and not cs._in_region(off, spans):
            name = m.group("name").strip()
            if name not in seen:
                seen.add(name)
                out.append((name, m.group("value").strip()))
    return out


def _lines_of(body):
    spans = cc.managed_spans(body)
    return [core for off, core, _ in cs._lines(body) if core.strip() and not cs._in_region(off, spans)]


def adopt(mem, rec):
    """Before `rec` is rewritten: each of its fields with no entry that applies keeps the source it had — the record's,
    as it is now — so a later write by someone else does not become theirs."""
    have = mem["records"].get(rec["id"], {})
    for name, value in fields(rec["body"]):
        e = have.get(field_key(name))
        if not (e and e["v"] == _h(value)):
            note(mem, rec["id"], field_key(name), value, rec.get("source") or "migrated",
                 at=(rec.get("modified") or "")[:10] or None)


def note_import(mem, old, new_body, kind, at):
    """An edit imported from a compiled copy: a field whose value changed is the editor's (`kind`, e.g. import:home);
    one that did not keeps what it had."""
    adopt(mem, old)
    for name, value in fields(new_body):
        if value != (cs.field_get(old["body"], name) or None):
            note(mem, old["id"], field_key(name), value, kind, at=at)


def forget(mem, rid):
    mem["records"].pop(rid, None)


def of(mem, rec):
    """The source of every field of `rec`, and of every line an entry still matches."""
    have = mem["records"].get(rec["id"], {})
    fallback = rec.get("source") or "—"
    out = []
    for name, value in fields(rec["body"]):
        e = have.get(field_key(name))
        own = bool(e) and e["v"] == _h(value)
        out.append(dict(key=field_key(name), label=name, own=own,
                        **({k: e[k] for k in ("kind", "ref", "at", "confidence")} if own else
                           {"kind": fallback, "ref": None, "at": (rec.get("modified") or "")[:10] or None,
                            "confidence": None})))
    for line in _lines_of(rec["body"]):
        e = have.get(line_key(line))
        if e and e["v"] == _h(line) and not cs.FIELD_RE.match(line):
            out.append(dict(key=line_key(line), label=_norm(line)[:80], own=True,
                            **{k: e[k] for k in ("kind", "ref", "at", "confidence")}))
    return out


def coverage(mem, recs):
    own = total = 0
    for r in recs:
        for x in of(mem, r):
            if x["key"].startswith("field:"):
                total += 1
                own += x["own"]
    return own, total


def describe(x):
    """`← jira:active · PROJ… · 2026-10-27 · середня` (own) or `← migrated (джерело запису)`."""
    if not x["own"]:
        return "← %s (джерело запису)" % x["kind"]
    lvl = {"high": "висока", "medium": "середня", "low": "низька"}.get(x["confidence"] or "")
    return "← " + " · ".join(p for p in (x["kind"], cc.clip(x["ref"], 60) if x["ref"] else None, x["at"], lvl) if p)
