#!/usr/bin/env python3
"""Grow PM — typed fields of the context store (since v3.12.0).

The source of truth stays the text line `- **Field:** value` of a record (a `list` field may also
be the bullets under `#### Field`); references/context-fields.yaml declares the types of the fields
the context card and the skills read. Semantics: references/context-protocol.md.

- load_fields                         the schema, {record type: {field: spec}}
- raw_value / parse_value / check_value  read, convert and check one field

Stdlib only.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx_common as cc  # noqa: E402
import ctx_store as cs  # noqa: E402

FIELDS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "references",
                           "context-fields.yaml")
PATTERNS = {"key": (r"^[A-Z][A-Z0-9_]+$", "a Jira key such as PROJ"),
            "date": (r"^\d{4}-\d{2}-\d{2}$", "a date YYYY-MM-DD"),
            "email": (r"^[^@\s]+@[^@\s]+$", "an email address"),
            "url": (r"^https?://", "a URL starting with http:// or https://")}
_COMMENT = re.compile(r"\s*<!--.*?-->\s*")


def load_fields(path=None):
    """{record type: {field name: spec}}; `hats` specs get the Role values as `values`."""
    with open(path or FIELDS_PATH, encoding="utf-8") as f:
        types = cc.read_yaml_tree(f.read()).get("types") or {}
    roles = ((types.get("profile") or {}).get("Role") or {}).get("values") or []
    for fields in types.values():
        for spec in fields.values():
            if spec.get("type") == "hats":
                spec["values"] = list(roles)
    return types


def _clean(v):
    v = _COMMENT.sub(" ", v or "").strip().strip("`").strip()
    if not v or re.match(r"^_.*_$", v):           # empty, or a placeholder such as _(auto-discovered)_
        return None
    return v


def raw_value(body, name, spec):
    """The field's text: its `- **name:** value` line outside managed regions, or for a `list` the
    bullets under `#### name` (outside managed regions) joined by ', '. None when absent."""
    v = _clean(cs.field_get(body, name))
    if v is not None or spec.get("type") != "list":
        return v
    items = [i for i in (_clean(b) for b in cs._bullets_under(cc.strip_managed_regions(body), name)) if i]
    return ", ".join(items) if items else None


def parse_value(spec, raw):
    """list → [str]; int → int; hats → 'all' / 'none' or [role]; anything else → str."""
    t = spec.get("type")
    if raw is None:
        return None
    if t == "list" or (t == "hats" and raw not in ("all", "none")):
        return [x.strip() for x in raw.split(",") if x.strip()]
    if t == "int":
        return int(raw)
    return raw


def check_value(spec, raw):
    """An error text (naming the allowed values or the expected form), or None when the value fits."""
    t = spec.get("type")
    if raw is None or t in (None, "text", "list"):
        return None
    if t == "enum":
        return None if raw in spec.get("values", []) else \
            "%r is not one of: %s" % (raw, ", ".join(spec.get("values", [])))
    if t == "hats":
        bad = [x for x in parse_value(spec, raw) if x not in spec.get("values", [])] if raw not in ("all", "none") else []
        return None if not bad else "%s: use all, none or roles from: %s" % (", ".join(bad), ", ".join(spec.get("values", [])))
    if t == "int":
        return None if raw.isdigit() else "%r is not a whole number" % raw
    pattern, what = PATTERNS.get(t, (None, None))
    if pattern and not re.match(pattern, raw):
        return "%r is not %s" % (raw, what)
    return None
