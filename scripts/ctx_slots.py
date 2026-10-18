#!/usr/bin/env python3
"""Grow PM — the slots of the context store (since v3.15.0).

A slot is the place in a record where an answer to a question lives: `team.members` is "who is on the team",
whatever heading the text carries and wherever it sits. references/context-slots.yaml is the catalogue — per
slot its kind (value, text or list), the kind of record it is looked for in, the names it answers to (English and
Ukrainian) and one line of what it holds. The manifest (references/context-manifest.yaml) names what a skill
reads; each of its names has a slot here, and validator check 16 keeps the two in step. Semantics:
references/context-protocol.md.

- CATALOGUE_PATH, KINDS, RECORDS    where the catalogue is, and the values `kind` and `record` may take
- load_catalogue                    the catalogue as a tree; a file that cannot be read is a ValueError
- check_catalogue                   the errors in a catalogue (none: it is clean)
- slot_for                          the slot a record kind answers to a name with
- slot_info                         a slot's own entry (kind, record, names, about), or None

What you decided about slots is kept in the store, in `<store>/.state/slots.json` (schema context-slots-memory/1) —
not in a record and not in a registration. `ctx slot bind|map|prefer|forget` write it (a snapshot first, a journal
line; `ctx undo` puts it back), the resolver reads it. Its shape:
  {"schema", "bindings": [{"repo", "block", "sub": str|None, "slot", "team": str|None}],
   "aliases": [{"record": a record id, "heading", "slot"}], "prefer": {slot: "mine"|"repo:<id>"|"all"},
   "decisions": {slot: {"winner": repo id, "hashes": {repo id: sha}}}}

- MEMORY_SCHEMA, MEMORY_FILE        the schema, and the file name inside `.state/`
- load_memory, save_memory          read it (no file: an empty memory; a file that cannot be read, is not JSON, is of
                                    another schema or not of this shape: a cs.StoreError that names `.state/slots.json`);
                                    write it (sorted, indented, atomic; a memory of the wrong shape is not written)
- add_binding, add_alias,           change a loaded memory in place: True when something changed, False when it already
  set_prefer, drop_slot             said so (a repeated bind or map adds nothing)
- in_memory                         is the slot anywhere in the memory

Stdlib only.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx_common as cc  # noqa: E402
import ctx_store as cs  # noqa: E402

PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOGUE_PATH = os.path.join(PLUGIN_ROOT, "references", "context-slots.yaml")
SCHEMA = "context-slots/1"
KINDS = ("value", "text", "list")
RECORDS = ("product", "team", "profile", "org")
_SLOT_ID = re.compile(r"(?P<record>[a-z]+)\.(?P<name>[a-z0-9_]+)\Z")


def load_catalogue(path=None):
    """The catalogue (`path`, else the plugin's own) as the tree cc.read_yaml_tree makes of it. A file that cannot
    be read, or is not YAML that reader takes, is a ValueError."""
    path = path or CATALOGUE_PATH
    try:
        with open(path, encoding="utf-8") as f:
            return cc.read_yaml_tree(f.read())
    except OSError as e:
        raise ValueError("cannot read %s: %s" % (path, e.strerror or e))


def _norm(name):
    """A name as slots compare them: without regard to case, to the space around it or between its words."""
    return " ".join(str(name).split()).casefold()


def _slots(cat):
    s = cat.get("slots") if isinstance(cat, dict) else None
    return s if isinstance(s, dict) else {}


def _names(slot):
    n = slot.get("names") if isinstance(slot, dict) else None
    return [x for x in n if isinstance(x, str) and x.strip()] if isinstance(n, list) else []


def check_catalogue(cat):
    """Errors, one string each: a slot whose `kind` or `record` is none of the allowed values, whose id is not
    `<record>.<name>` of its own record, with no `names` or no `about`; a name (without regard to case) two slots of
    one record both answer to, which would leave `slot_for` to guess; a `schema` other than context-slots/1."""
    errs = []
    if isinstance(cat, dict) and "schema" in cat and cat["schema"] != SCHEMA:
        errs.append("schema is %r, not %r" % (cat["schema"], SCHEMA))
    slots = _slots(cat)
    if not slots:
        return errs + ["the catalogue has no slots"]
    owner = {}                                     # (record, normalised name) → the first slot that answers to it
    for sid, slot in slots.items():
        if not isinstance(slot, dict):
            errs.append("slot %s: not a mapping of kind, record, names and about" % sid)
            continue
        m = _SLOT_ID.match(sid)
        record = slot.get("record")
        if slot.get("kind") not in KINDS:
            errs.append("slot %s: kind %r is none of %s" % (sid, slot.get("kind"), ", ".join(KINDS)))
        if record not in RECORDS:
            errs.append("slot %s: record %r is none of %s" % (sid, record, ", ".join(RECORDS)))
        elif not m:
            errs.append("slot %r: the id is not <record>.<name> (lower case, digits and _)" % sid)
        elif m.group("record") != record:
            errs.append("slot %s: the id starts with %r but the record is %r" % (sid, m.group("record"), record))
        raw = slot.get("names")
        if not isinstance(raw, list) or not raw:
            errs.append("slot %s: names is not a list with a name in it" % sid)
        elif len(_names(slot)) != len(raw):
            errs.append("slot %s: names has a name that is blank or not text" % sid)
        about = slot.get("about")
        if not isinstance(about, str) or not about.strip():
            errs.append("slot %s: about is empty — one line on what the slot holds" % sid)
        elif "\n" in about:
            errs.append("slot %s: about is more than one line" % sid)
        for n in (_names(slot) if record in RECORDS else ()):
            first = owner.setdefault((record, _norm(n)), sid)
            if first != sid:
                errs.append("name %r is answered to by both %s and %s — slot_for could not tell them apart" % (n, first, sid))
    return errs


def slot_for(cat, record, name):
    """The id of the slot of `record` (product, team, profile or org) that answers to `name`, without regard to
    case — or None. Names are the catalogue's `names`, so `Team Members` and `Members` find the same slot. In a
    catalogue check_catalogue would fault for a shared name, the first slot in file order wins."""
    want = _norm(name or "")
    if not want:
        return None
    for sid, slot in _slots(cat).items():
        if isinstance(slot, dict) and slot.get("record") == record and want in [_norm(n) for n in _names(slot)]:
            return sid
    return None


def slot_info(cat, slot_id):
    """The catalogue's entry for `slot_id` (a mapping of kind, record, names and about), or None."""
    s = _slots(cat).get(slot_id)
    return s if isinstance(s, dict) else None


# ------------------------------------------------------------------ the memory of your decisions
MEMORY_SCHEMA = "context-slots-memory/1"
MEMORY_FILE = "slots.json"
MEMORY_WHERE = ".state/" + MEMORY_FILE
_MEMORY_KEYS = ("schema", "bindings", "aliases", "prefer", "decisions")


def empty_memory():
    return {"schema": MEMORY_SCHEMA, "bindings": [], "aliases": [], "prefer": {}, "decisions": {}}


def _text(v):
    return isinstance(v, str) and bool(v.strip())


def valid_preference(who):
    """`mine`, `all` or `repo:<id>` (an id with something in it)."""
    return who in ("mine", "all") or (isinstance(who, str) and who.startswith("repo:") and _text(who[5:]))


def _clean_memory(data):
    """`data` as the canonical memory: every part there (a part the file lacks is empty), bindings and names in a fixed
    order with none twice. Anything else — a schema that is not MEMORY_SCHEMA, a part of the wrong shape, a key nobody
    knows — is a ValueError that says which."""
    if not isinstance(data, dict):
        raise ValueError("not an object")
    if data.get("schema") != MEMORY_SCHEMA:
        raise ValueError("schema is %r, not %r" % (data.get("schema"), MEMORY_SCHEMA))
    extra = sorted(str(k) for k in data if k not in _MEMORY_KEYS)
    if extra:
        raise ValueError("unknown key: %s" % ", ".join(extra))
    out = empty_memory()
    bindings = data.get("bindings", [])
    if not isinstance(bindings, list):
        raise ValueError("bindings is not a list")
    seen = set()
    for i, b in enumerate(bindings):
        if not isinstance(b, dict):
            raise ValueError("binding %d is not an object" % (i + 1))
        for key in ("repo", "block", "slot"):
            if not _text(b.get(key)):
                raise ValueError("binding %d has no %s" % (i + 1, key))
        for key in ("sub", "team"):
            if b.get(key) is not None and not _text(b.get(key)):
                raise ValueError("binding %d: %s is neither text nor null" % (i + 1, key))
        one = {"repo": b["repo"], "block": b["block"], "sub": b.get("sub"), "slot": b["slot"], "team": b.get("team")}
        key = (one["repo"], one["block"], one["sub"], one["slot"], one["team"])
        if key not in seen:
            seen.add(key)
            out["bindings"].append(one)
    out["bindings"].sort(key=lambda b: (b["repo"], b["block"], b["sub"] or "", b["slot"], b["team"] or ""))
    aliases = data.get("aliases", [])
    if not isinstance(aliases, list):
        raise ValueError("aliases is not a list")
    seen = set()
    for i, a in enumerate(aliases):
        if not isinstance(a, dict):
            raise ValueError("alias %d is not an object" % (i + 1))
        for key in ("record", "heading", "slot"):
            if not _text(a.get(key)):
                raise ValueError("alias %d has no %s" % (i + 1, key))
        key = (a["record"], _norm(a["heading"]), a["slot"])
        if key not in seen:
            seen.add(key)
            out["aliases"].append({"record": a["record"], "heading": a["heading"], "slot": a["slot"]})
    out["aliases"].sort(key=lambda a: (a["record"], _norm(a["heading"]), a["slot"]))
    prefer = data.get("prefer", {})
    if not isinstance(prefer, dict):
        raise ValueError("prefer is not an object")
    for slot, who in prefer.items():
        if not valid_preference(who):
            raise ValueError("prefer for %s is %r, not mine, all or repo:<id>" % (slot, who))
        out["prefer"][slot] = who
    decisions = data.get("decisions", {})
    if not isinstance(decisions, dict):
        raise ValueError("decisions is not an object")
    for slot, d in decisions.items():
        if not isinstance(d, dict) or sorted(d) != ["hashes", "winner"]:
            raise ValueError("the decision for %s is not {winner, hashes}" % slot)
        if not _text(d["winner"]):
            raise ValueError("the decision for %s has no winner" % slot)
        h = d["hashes"]
        if not isinstance(h, dict) or not all(_text(k) and isinstance(v, str) for k, v in h.items()):
            raise ValueError("the hashes of the decision for %s are not {repository: hash}" % slot)
        out["decisions"][slot] = {"winner": d["winner"], "hashes": dict(h)}
    return out


def _memory_error(kind, why):
    return cs.StoreError("slots memory %s: %s (%s)" % (kind, MEMORY_WHERE, " ".join(str(why).split())[:300]))


def load_memory(store):
    """What you decided about slots, from `<store>/.state/slots.json`, in canonical form. No file is an empty memory. A
    file that cannot be read (or does not arrive in time) → cs.StoreError "slots memory not readable: .state/slots.json
    (<why>)"; one that is not JSON, is of another schema or not of the shape above → "slots memory not valid: …". It is
    never reset silently."""
    path = os.path.join(store.state_dir, MEMORY_FILE)
    if not os.path.lexists(path):
        return empty_memory()
    try:
        raw = cs.read_text(path)
    except FileNotFoundError:
        return empty_memory()
    except (OSError, UnicodeDecodeError, cs.StoreError) as e:
        raise _memory_error("not readable", getattr(e, "strerror", None) or e)
    try:
        return _clean_memory(json.loads(raw))
    except ValueError as e:
        raise _memory_error("not valid", e)


def save_memory(store, mem):
    """Write the memory (canonical, sorted, indented, atomic) and return what was written. A memory of the wrong shape →
    cs.StoreError "slots memory not valid: …", nothing written."""
    try:
        clean = _clean_memory(mem)
    except ValueError as e:
        raise _memory_error("not valid", e)
    cs.atomic_write(os.path.join(store.state_dir, MEMORY_FILE),
                    json.dumps(clean, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
    cs.remove_stale_tmp(store.state_dir)
    return clean


def add_binding(mem, repo, block, sub, slot, team):
    """Bind the block (or its subsection `sub`) of a repository to `slot`, in `mem`, in place. The same bind again changes
    nothing; so does one without a team when the binding has one. A bind that names another team sets the team of the
    binding it repeats. True when `mem` changed."""
    for b in mem["bindings"]:
        if (b["repo"], b["block"], b["sub"], b["slot"]) == (repo, block, sub, slot):
            if team is None or b["team"] == team:
                return False
            b["team"] = team
            return True
    mem["bindings"].append({"repo": repo, "block": block, "sub": sub, "slot": slot, "team": team})
    return True


def add_alias(mem, record, heading, slot):
    """Let the heading `heading` in the record `record` (an id) answer for `slot`, in `mem`, in place; the same name again —
    whatever its case or spacing — changes nothing. True when `mem` changed."""
    for a in mem["aliases"]:
        if (a["record"], _norm(a["heading"]), a["slot"]) == (record, _norm(heading), slot):
            return False
    mem["aliases"].append({"record": record, "heading": heading, "slot": slot})
    return True


def set_prefer(mem, slot, who):
    """Whose answer a slot gives first: `mine`, `repo:<id>` or `all`. True when `mem` changed."""
    if mem["prefer"].get(slot) == who:
        return False
    mem["prefer"][slot] = who
    return True


def in_memory(mem, slot):
    """Is anything about `slot` in the memory?"""
    return (any(b["slot"] == slot for b in mem["bindings"]) or any(a["slot"] == slot for a in mem["aliases"])
            or slot in mem["prefer"] or slot in mem["decisions"])


def drop_slot(mem, slot):
    """Take everything about `slot` out of `mem`, in place: bindings, names, preference, decision. True when anything went."""
    found = in_memory(mem, slot)
    mem["bindings"] = [b for b in mem["bindings"] if b["slot"] != slot]
    mem["aliases"] = [a for a in mem["aliases"] if a["slot"] != slot]
    mem["prefer"].pop(slot, None)
    mem["decisions"].pop(slot, None)
    return found
