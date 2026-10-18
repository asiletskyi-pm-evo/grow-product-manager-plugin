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

Stdlib only.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx_common as cc  # noqa: E402

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
