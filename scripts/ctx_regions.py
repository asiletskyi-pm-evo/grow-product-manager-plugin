#!/usr/bin/env python3
"""Grow PM — the generated regions of a note (since v4.0.0): one parser for `ctx audit`, `ctx vault normalize` and the
write gate.

A region is text a script writes between two markers (references/vault-schema.md → Generated regions and layers):

    <!-- <namespace>:begin id=<id> [v=…] [mode=…] -->  …  <!-- <namespace>:end id=<id> -->

or, as a section wrapper, `<namespace>:section:begin` / `:section:end` without an id. A skill or the agent never writes
inside one; its script rewrites it.

- NAMESPACES                    the registry: namespace → who writes it (the table of vault-schema.md is the same set;
                                check_registry compares them); a registered provider's id is a namespace too
- parse(text, providers)        (regions, problems): a region {ns, id (None without one), start, end — the offsets of the
                                begin marker's first character and the end marker's last —, inner, inner_start}; a
                                problem {why, ns, id, at}: unclosed, stray-end, dup-id, no-id (two regions of one
                                namespace without an id; one alone is how the user's own scripts write it), unknown-ns,
                                nested, heading-twice (a heading both inside a region and outside it). Markers in a code
                                block or a code span are text.
- touches(text, old)            does `old` (an edit's old text) lie, at any of its places, on a region or a marker?
- outside_targets(text)        the targets of the links outside every region and code block
- changed(old, new)             do the regions of a new text differ from the old one's (a region's text, a marker, a
                                region gone or added)?
- check_registry(root)          the lines where vault-schema.md's table and NAMESPACES differ

Reads nothing but what it is given (check_registry: vault-schema.md). Stdlib only.
"""
import os
import re

NAMESPACES = {
    "generated": "any generator of the vault (a script's own section)",
    "related": "a «Пов'язане» block a script writes at a note's end (your own scripts write it without an id)",
    "person-context": "the person-context block of a meeting or a card",
    "person-profile": "the profile block of a person card",
    "ff-summary": "a summary a script keeps at a note's top",
    "audit": "an audit's findings in a note",
    "ctx": "the plugin itself: hubs, «Пов'язане», AGENTS.md, the status of a record (ctx vault normalize, ctx)",
}
_MARK = re.compile(r"<!--\s*([a-z][a-z0-9-]*)(:section)?:(begin|end)\b([^>]*?)-->")
_ID = re.compile(r"\bid=([A-Za-z0-9_.-]+)")
_FENCE = re.compile(r"^[ \t]{0,3}(?:>[ \t]?)*(`{3,}|~{3,})(.*)$")
_SPAN = re.compile(r"(?<!`)(`+)(?!`)[^\n]*?(?<!`)\1(?!`)")
_HEADING = re.compile(r"^#{1,6}[ \t]+(.+?)[ \t#]*$", re.M)


def _masked(text):
    """The text with its fenced blocks and code spans turned into spaces, every offset kept."""
    out, fence = [], None
    for line in text.split("\n"):
        m = _FENCE.match(line)
        if fence:
            if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence) and not m.group(2).strip():
                fence = None
            out.append(" " * len(line))
            continue
        if m and not (m.group(1)[0] == "`" and "`" in m.group(2)):
            fence = m.group(1)
            out.append(" " * len(line))
            continue
        out.append(line)
    return _SPAN.sub(lambda m: " " * len(m.group(0)), "\n".join(out))


def parse(text, providers=()):
    """(regions, problems) of a note's text — see the module's doc."""
    text = text or ""
    known = set(NAMESPACES) | {p for p in providers or () if p}
    regions, problems, stack = [], [], []
    for m in _MARK.finditer(_masked(text)):
        ns, kind = m.group(1), m.group(3)
        i = _ID.search(m.group(4) or "")
        rid = i.group(1) if i else None
        if kind == "begin":
            if stack:
                problems.append({"why": "nested", "ns": ns, "id": rid, "at": m.start()})
            stack.append((ns, rid, m))
            continue
        if stack and stack[-1][0] == ns and stack[-1][1] == rid:
            bns, bid, bm = stack.pop()
            regions.append({"ns": ns, "id": rid, "start": bm.start(), "end": m.end(), "inner_start": bm.end(),
                            "inner": text[bm.end():m.start()]})
        else:
            problems.append({"why": "stray-end", "ns": ns, "id": rid, "at": m.start()})
    for ns, rid, bm in stack:
        problems.append({"why": "unclosed", "ns": ns, "id": rid, "at": bm.start()})
    regions.sort(key=lambda r: r["start"])
    seen, bare = set(), {}
    for r in regions:
        if r["ns"] not in known:
            problems.append({"why": "unknown-ns", "ns": r["ns"], "id": r["id"], "at": r["start"]})
        if r["id"] is None:
            bare[r["ns"]] = bare.get(r["ns"], 0) + 1
            if bare[r["ns"]] == 2:
                problems.append({"why": "no-id", "ns": r["ns"], "id": None, "at": r["start"]})
        elif (r["ns"], r["id"]) in seen:
            problems.append({"why": "dup-id", "ns": r["ns"], "id": r["id"], "at": r["start"]})
        seen.add((r["ns"], r["id"]))
    inside, outside = set(), set()
    masked = _masked(text)
    for m in _HEADING.finditer(masked):
        key = re.sub(r"\s+", " ", m.group(1)).strip().casefold()
        (inside if any(r["start"] <= m.start() < r["end"] for r in regions) else outside).add(key)
    for key in sorted(inside & outside):
        problems.append({"why": "heading-twice", "ns": "", "id": key, "at": 0})
    return regions, problems


_WIKI = re.compile(r"!?\[\[([^\]\n]+?)\]\]")


def outside_targets(text):
    """The targets (as written, before `#` and `|`) of the wiki links of `text` outside every region and code block —
    the links a writer that never enters a region may change."""
    masked = _masked(text or "")
    regions, _ = parse(text or "")
    out = set()
    for m in _WIKI.finditer(masked):
        if not any(r["start"] <= m.start() < r["end"] for r in regions):
            out.add(m.group(1).split("|", 1)[0].split("#", 1)[0].strip())
    return out


def _spans(text):
    """[start, end) of every region and of every marker of a broken one — what an edit must not touch."""
    regions, _ = parse(text, providers=())
    out = [(r["start"], r["end"]) for r in regions]
    for m in _MARK.finditer(_masked(text or "")):
        if not any(s <= m.start() < e for s, e in out):
            out.append((m.start(), m.end()))
    return out


def touches(text, old):
    """Does `old` lie, at any place it is found in `text`, on a region or on a marker?"""
    if not old or not text:
        return False
    spans = _spans(text)
    i = text.find(old)
    while i >= 0:
        j = i + len(old)
        if any(i < e and j > s for s, e in spans):
            return True
        i = text.find(old, i + 1)
    return False


def _signature(text):
    regions, _ = parse(text, providers=())
    markers = [m.group(0) for m in _MARK.finditer(_masked(text or ""))]
    return sorted((r["ns"], r["id"] or "", r["inner"]) for r in regions), markers


def changed(old, new):
    """Do the regions (and the markers) of `new` differ from those of `old`?"""
    return _signature(old) != _signature(new)


def check_registry(root):
    """The lines where the namespaces of the registry table in references/vault-schema.md (rows `| \\`ns\\` | …`
    under the line that starts «**Registry.**») and NAMESPACES differ."""
    path = os.path.join(root, "references", "vault-schema.md")
    try:
        text = open(path, encoding="utf-8").read()
    except OSError as e:
        return ["vault-schema.md: %s" % e]
    at = text.find("**Registry.**")
    if at < 0:
        return ["vault-schema.md: no «**Registry.**» table of the region namespaces"]
    table = []
    for line in text[at:].split("\n")[1:]:
        if line.startswith("|"):
            m = re.match(r"^\|\s*`([a-z][a-z0-9-]*)`\s*\|", line)
            if m:
                table.append(m.group(1))
        elif table:
            break
    out = []
    for ns in sorted(set(NAMESPACES) - set(table)):
        out.append("vault-schema.md: namespace %s of ctx_regions.NAMESPACES is not in the Registry table" % ns)
    for ns in sorted(set(table) - set(NAMESPACES)):
        out.append("vault-schema.md: namespace %s of the Registry table is not in ctx_regions.NAMESPACES" % ns)
    return out
