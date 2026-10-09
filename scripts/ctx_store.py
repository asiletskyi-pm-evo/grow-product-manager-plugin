#!/usr/bin/env python3
"""Grow PM — the context store's model (since v3.11.0).

The user's local-context.md is cut into section records that together cover every byte
exactly once, so compiling the records gives the file back byte for byte. Semantics:
references/context-protocol.md. Used by ctx_ops.py and the `ctx` command line.

- split_sections / assign_ids   the split rules and stable record ids
- render_record / parse_record  the record file: frontmatter + the section text as is
- compile_records               the compiled local-context.md

Stdlib only.
"""
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx_common as cc  # noqa: E402

# A `##` heading that starts with one of these is a `setting` record; any other is `custom`.
SETTING_TITLES = ("Judgment", "CJM Configuration", "Knowledge Library", "Templates", "Obsidian Vaults", "People",
                  "Planning", "Focus", "Release", "Terminology & Style", "Landscape", "Experiments", "Feedback",
                  "Custom Sections")
RECORD_KEYS = ("ctx", "id", "type", "title", "parent", "order", "owner", "source", "modified", "sha")


def sha_text(s):
    return hashlib.sha256((s or "").encode("utf-8")).hexdigest()


def _h2_type(title):
    if title == "User Profile":
        return "profile"
    if title == "Onboarding Status":
        return "onboarding"
    if title.startswith("Organization:"):
        return "org"
    if title.startswith(SETTING_TITLES):
        return "setting"
    return "custom"


def split_sections(text):
    """Fragments {type, title, heading, parent_index, text} in file order; their texts concatenate to `text`.

    A `## ` line starts a fragment; inside `## Organization:` so does `### Product: ` / `### Team: `.
    Lines inside fenced code and inside managed regions never split — except that a region whose
    begin marker is followed, after blank lines only, by a `## ` heading starts a fragment itself."""
    lines = text.splitlines(keepends=True)
    starts, pos = [], 0
    for ln in lines:
        starts.append(pos)
        pos += len(ln)
    spans = cc.managed_spans(text)
    begins = {a for a, _ in spans}

    def inside(off):
        return any(a < off < b for a, b in spans)

    cuts, fence, org_open = [], False, False
    for i, ln in enumerate(lines):
        s = ln.rstrip("\r\n")
        off = starts[i]
        if inside(off):
            continue
        if s.lstrip().startswith("```"):
            fence = not fence
            continue
        if fence:
            continue
        if s.startswith("## "):
            title = s[3:].strip()
            cuts.append((i, "h2", title, s))
            org_open = title.startswith("Organization:")
        elif org_open and (s.startswith("### Product: ") or s.startswith("### Team: ")):
            cuts.append((i, "h3", s[4:].strip(), s))
        elif off in begins:
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines) and lines[j].startswith("## "):
                head = lines[j].rstrip("\r\n")
                title = head[3:].strip()
                cuts.append((i, "h2", title, head))
                org_open = title.startswith("Organization:")

    frags = []
    first = cuts[0][0] if cuts else len(lines)
    if first > 0:
        head = next((l.rstrip("\r\n").lstrip("﻿") for l in lines[:first] if l.lstrip("﻿").startswith("# ")), "")
        frags.append(dict(type="header", title=head[2:].strip() if head else "header", heading=head or None,
                          parent_index=None, text="".join(lines[:first])))
    org_index = None
    for k, (i, kind, title, head) in enumerate(cuts):
        end = cuts[k + 1][0] if k + 1 < len(cuts) else len(lines)
        if kind == "h2":
            typ, parent = _h2_type(title), None
            org_index = len(frags) if typ == "org" else None
        else:
            typ, parent = ("product" if title.startswith("Product:") else "team"), org_index
        frags.append(dict(type=typ, title=title, heading=head, parent_index=parent, text="".join(lines[i:end])))
    return frags


def assign_ids(frags, taken=frozenset()):
    """Add `id`, `parent` (id or None) and `order` (10, 20, …) to each fragment."""
    used, out = set(taken), []
    for k, f in enumerate(frags):
        typ = f["type"]
        if typ in ("header", "profile", "onboarding"):
            base = typ
        else:
            name = f["title"]
            for pre in ("Organization:", "Product:", "Team:"):
                if name.startswith(pre):
                    name = name[len(pre):].strip()
                    break
            base = typ + "." + cc.slugify(name)
        rid, n = base, 2
        while rid in used:
            rid, n = "%s-%d" % (base, n), n + 1
        used.add(rid)
        pi = f.get("parent_index")
        out.append(dict(f, id=rid, order=(k + 1) * 10, parent=out[pi]["id"] if pi is not None else None))
    return out


def render_record(rec):
    """Frontmatter in RECORD_KEYS order (strings JSON-quoted, None as ""), then the body as is."""
    out = ["---"]
    for k in RECORD_KEYS:
        v = rec.get(k)
        if isinstance(v, bool) or v is None:
            v = "" if v is None else str(v).lower()
        out.append("%s: %s" % (k, v if isinstance(v, int) else json.dumps(v, ensure_ascii=False)))
    return "\n".join(out) + "\n---\n" + (rec.get("body") or "")


def parse_record(text):
    """Inverse of render_record. Raises ValueError when the frontmatter is missing or unreadable."""
    if not text.startswith("---\n"):
        raise ValueError("no frontmatter")
    end = text.find("\n---\n", 3)
    if end < 0:
        raise ValueError("frontmatter not closed")
    meta = cc.read_yaml_subset(text[4:end])
    rec = {k: meta.get(k) for k in RECORD_KEYS}
    rec["parent"] = rec["parent"] or None
    if not rec.get("id") or not isinstance(rec.get("order"), int):
        raise ValueError("frontmatter lacks id or order")
    rec["body"] = text[end + 5:]
    return rec


def compile_records(records):
    """The compiled local-context.md: record bodies in ascending `order`."""
    return "".join(r["body"] for r in sorted(records, key=lambda r: r["order"]))
