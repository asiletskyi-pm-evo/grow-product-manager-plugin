#!/usr/bin/env python3
"""Grow PM — the declared overlay to a repository's blocks (since v3.23.0; references/context-protocol.md §5n).

Your corrections to a core live in `{store}/overlays/<repo>.yaml`, schema `context-overlay/1`:

    schema: context-overlay/1
    repo: zorg-core
    ops:
      - id: team-members
        target: {block: team, path: "#Members"}
        op: replace
        value_ref: "team.alpha-a#Team Members"
        expects: 1
        reason: "у ядрі заглушки без ролей"
        created: 2026-10-28

A target's `path` is one of four forms: empty (the whole block), `#Subsection` (the heading — a qualifier after the
name answers too — up to the next heading of its level or a higher one), `field:Label` (the line `- **Label:** …`) or
`match:"text"` (every line that holds the text, case and runs of spaces aside). `expects` (default 1) is how many
times the path is found in the core's text. An operation:

- replace   what the path finds becomes `value` (lines; for a field, the value after its label) — or, with
            `value_ref: "<record id>#<Subsection>"`, one pointer line to your own subsection (your text is never copied
            into a block): `> [оверлей <id>: замінено на <record> › <Subsection> — <reason>]`. A subsection keeps its
            heading.
- remove    what the path finds goes, with no doubled blank line left behind.
- append    `value` goes after the last line the path finds (the end of the block for no path).
- ignore    no text changes; the resolver gives no slot what the path finds (`ignored`).
- alias     no text changes; the names in `value` join the entity the path names (`aliases`).

The pure part — `parse`, `dump`, `locate`, `overlay`, `ignored`, `aliases` — reads and writes nothing. An operation
whose count differs from `expects` is held (`state` "held"): it changes nothing and the others still apply. Two
text-changing operations whose lines meet are both refused (`state` "error"). A value_ref that names no subsection of
yours holds its operation.

On disk — `path_of`, `load`, `save`: a file that cannot be read (not this subset of YAML, an unknown key, another
schema or another repository) raises Unreadable and is never rewritten; a new key or a new meaning of one needs a new
schema, `context-overlay/2`. Stdlib only.
"""
import json
import os
import re

import ctx_common as cc
import ctx_store as cs

SCHEMA = "context-overlay/1"
OPS = ("replace", "remove", "append", "alias", "ignore")
TEXT_OPS = ("replace", "remove", "append")
TOP_KEYS = ("schema", "repo", "ops")
OP_KEYS = ("id", "target", "op", "value", "value_ref", "expects", "reason", "created")
TARGET_KEYS = ("block", "path")
REPO_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
OP_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
FIELD = re.compile(r"^(\s*[-*]\s+\*\*(.+?):\*\*)(.*)$")
BEGIN = re.compile(r"<!--\s*[a-z][a-z0-9-]*:begin\s+id=([A-Za-z0-9_.-]+)")
ALL = "ALL"                                             # `ignored`: the whole block


class Unreadable(ValueError):
    """The overlay file cannot be read — it is left exactly as it is."""


# ------------------------------------------------------------------ parse
def _split_flow(body, lineno):
    """The items of a flow collection's inside, split at commas outside quotes (a quote may open anywhere)."""
    parts, cur, q, i = [], [], None, 0
    while i < len(body):
        ch = body[i]
        if q:
            cur.append(ch)
            if q == '"' and ch == "\\" and i + 1 < len(body):
                cur.append(body[i + 1]); i += 2
                continue
            if ch == q:
                if q == "'" and body[i + 1:i + 2] == "'":
                    cur.append("'"); i += 1
                else:
                    q = None
        elif ch in "\"'":
            q = ch; cur.append(ch)
        elif ch == ",":
            parts.append("".join(cur)); cur = []
        elif ch in "[]{}":
            raise Unreadable("line %d: a collection inside a collection" % lineno)
        else:
            cur.append(ch)
        i += 1
    if q:
        raise Unreadable("line %d: an unterminated string" % lineno)
    parts.append("".join(cur))
    items = [p.strip() for p in parts]
    if items and not items[-1]:
        items.pop()
    if any(not it for it in items):
        raise Unreadable("line %d: an empty item" % lineno)
    return items


def _scalar(v, lineno):
    try:
        return cc._scalar(v, lineno)
    except (ValueError, json.JSONDecodeError) as e:
        raise Unreadable(str(e) if str(e).startswith("line") else "line %d: %s" % (lineno, e))


def _value(v, lineno):
    v = v.strip()
    if v.startswith("{"):
        if not v.endswith("}"):
            raise Unreadable("line %d: a flow map must close on its line" % lineno)
        out = {}
        for item in _split_flow(v[1:-1], lineno):
            k, sep, rest = item.partition(":")
            k = k.strip()
            if not sep or not k:
                raise Unreadable("line %d: a flow map item must be key: value" % lineno)
            if k in out:
                raise Unreadable("line %d: the key %r twice" % (lineno, k))
            out[k] = _scalar(rest, lineno)
        return out
    if v.startswith("["):
        if not v.endswith("]"):
            raise Unreadable("line %d: a flow list must close on its line" % lineno)
        return [_scalar(it, lineno) for it in _split_flow(v[1:-1], lineno)]
    return _scalar(v, lineno)


KEY_LINE = re.compile(r"^([A-Za-z_][\w-]*):(?:\s+(.*))?$")


def _lines(text):
    for lineno, raw in enumerate((text or "").replace("\r\n", "\n").split("\n"), 1):
        line = cc._strip_value_comment(raw)
        if not line.strip() or line.strip() in ("---", "..."):
            continue
        lead = line[:len(line) - len(line.lstrip(" \t"))]
        if "\t" in lead:
            raise Unreadable("line %d: tab indentation" % lineno)
        yield lineno, len(lead), line.strip()


def _raw(text):
    """{top key: value} with `ops` a list of {key: value}; structure only, the meaning is `_check`'s."""
    top, ops = {}, None
    item = item_ind = key_col = pend = pend_ind = None
    for lineno, ind, body in _lines(text):
        if ind == 0:
            m = KEY_LINE.match(body)
            if not m:
                raise Unreadable("line %d: not key: value" % lineno)
            k, v = m.group(1), (m.group(2) or "").strip()
            if k in top:
                raise Unreadable("line %d: the key %r twice" % (lineno, k))
            if k not in TOP_KEYS:
                raise Unreadable("line %d: unknown key %r" % (lineno, k))
            if k == "ops":
                if v not in ("", "[]"):
                    raise Unreadable("line %d: ops must be a list of operations" % lineno)
                ops = top[k] = []
                if v == "[]":
                    ops = None                          # `ops: []` — no item may follow
            else:
                top[k] = _scalar(v, lineno)
            item = pend = None
            continue
        if ops is None or top.get("ops") is not ops or list(top)[-1] != "ops":
            raise Unreadable("line %d: an indented line outside ops" % lineno)
        is_item = body == "-" or body.startswith("- ")
        if item is None or (is_item and ind == item_ind):
            if not is_item:
                raise Unreadable("line %d: an operation must start with -" % lineno)
            item, item_ind, pend = {}, ind, None
            ops.append(item)
            rest = body[1:]
            first = rest.strip()
            key_col = ind + 1 + len(rest) - len(rest.lstrip(" ")) if first else None
            if first:
                pend = _put(item, first, lineno)
                pend_ind = None
            continue
        if ind <= item_ind:
            raise Unreadable("line %d: an indent that matches no level" % lineno)
        if is_item:
            if pend is None or ind < (key_col or 0) or (pend_ind is not None and ind != pend_ind):
                raise Unreadable("line %d: a list item without its key" % lineno)
            pend_ind = ind
            if not isinstance(item[pend], list):
                item[pend] = []
            item[pend].append(_scalar(body[1:].strip(), lineno))
            continue
        if key_col is None:
            key_col = ind
        elif ind != key_col:
            raise Unreadable("line %d: an indent that matches no level" % lineno)
        pend, pend_ind = _put(item, body, lineno), None
    return top


def _put(item, body, lineno):
    m = KEY_LINE.match(body)
    if not m:
        raise Unreadable("line %d: not key: value" % lineno)
    k, v = m.group(1), (m.group(2) or "").strip()
    if k in item:
        raise Unreadable("line %d: the key %r twice in one operation" % (lineno, k))
    if k not in OP_KEYS:
        raise Unreadable("line %d: unknown key %r" % (lineno, k))
    if not v:
        item[k] = ""
        return k
    item[k] = _value(v, lineno)
    return None


def parse_path(path):
    """("all", None) | ("heading", name) | ("field", label) | ("match", text); ValueError for any other form."""
    p = (path or "").strip()
    if not p:
        return "all", None
    if p.startswith("#"):
        name = p.lstrip("#").strip()
        if name:
            return "heading", name
    elif p.startswith("field:"):
        label = p[6:].strip()
        if label:
            return "field", label
    elif p.startswith("match:"):
        text = p[6:].strip()
        if len(text) >= 2 and text[0] == text[-1] == '"':
            text = json.loads(text)
        elif len(text) >= 2 and text[0] == text[-1] == "'":
            text = text[1:-1].replace("''", "'")
        if text.strip():
            return "match", text
    raise ValueError("path %r is none of: empty, #Subsection, field:Label, match:\"text\"" % path)


def _check(top):
    if top.get("schema") != SCHEMA:
        raise Unreadable("schema is %r, not %s" % (top.get("schema"), SCHEMA))
    repo = top.get("repo")
    if not isinstance(repo, str) or not REPO_ID.match(repo):
        raise Unreadable("repo %r is not a repository id" % (repo,))
    out, ids, made = [], set(), []
    for n, raw in enumerate(top.get("ops") or [], 1):
        where = "operation %d" % n
        kind = raw.get("op")
        if kind not in OPS:
            raise Unreadable("%s: op %r is none of %s" % (where, kind, ", ".join(OPS)))
        tgt = raw.get("target")
        if not isinstance(tgt, dict):
            raise Unreadable("%s: target must be {block: …, path: …}" % where)
        bad = [k for k in tgt if k not in TARGET_KEYS]
        if bad:
            raise Unreadable("%s: unknown key %r in target" % (where, bad[0]))
        block, path = tgt.get("block"), tgt.get("path", "")
        if not isinstance(block, str) or not block.strip():
            raise Unreadable("%s: target has no block" % where)
        if not isinstance(path, str):
            raise Unreadable("%s: path must be a string" % where)
        try:
            parse_path(path)
        except ValueError as e:
            raise Unreadable("%s: %s" % (where, e))
        exp = raw.get("expects", 1)
        if isinstance(exp, bool) or not isinstance(exp, int) or exp < 0:
            raise Unreadable("%s: expects must be a whole number from 0" % where)
        val, ref = raw.get("value"), raw.get("value_ref")
        if val is not None and not (isinstance(val, str) or (isinstance(val, list) and all(isinstance(x, str) for x in val))):
            raise Unreadable("%s: value must be text or a list of lines" % where)
        if ref is not None and (not isinstance(ref, str) or "#" not in ref or not ref.split("#", 1)[0].strip()
                                or not ref.split("#", 1)[1].strip()):
            raise Unreadable("%s: value_ref must be \"<record id>#<Subsection>\"" % where)
        if kind == "replace" and (val is None) == (ref is None):
            raise Unreadable("%s: replace takes value or value_ref — exactly one" % where)
        if kind in ("remove", "ignore") and (val is not None or ref is not None):
            raise Unreadable("%s: %s takes no value" % (where, kind))
        if kind in ("append", "alias") and (val is None or ref is not None or val in ("", [])):
            raise Unreadable("%s: %s takes value (and no value_ref)" % (where, kind))
        oid = raw.get("id")
        if oid is not None:
            if not isinstance(oid, str) or not OP_ID.match(oid):
                raise Unreadable("%s: id %r is not kebab-case" % (where, oid))
            if oid in ids:
                raise Unreadable("%s: the id %r twice" % (where, oid))
            ids.add(oid)
        for k in ("reason", "created"):
            if raw.get(k) is not None and not isinstance(raw.get(k), (str, int)):
                raise Unreadable("%s: %s must be text" % (where, k))
        op = {"id": oid, "target": {"block": block.strip(), "path": path} if path else {"block": block.strip()},
              "op": kind, "expects": exp}
        if val is not None:
            op["value"] = [val] if (kind == "alias" and isinstance(val, str)) else val
        if ref is not None:
            op["value_ref"] = ref
        for k in ("reason", "created"):
            if raw.get(k) not in (None, ""):
                op[k] = str(raw[k])
        out.append(op)
        if oid is None:
            made.append(op)
    for op in made:                                     # a made id: block + path, unique among the others
        base = cc.slugify("%s %s" % (op["target"]["block"], op["target"].get("path", "")))[:60].strip("-") or "op"
        oid, k = base, 2
        while oid in ids:
            oid, k = "%s-%d" % (base, k), k + 1
        ids.add(oid)
        op["id"] = oid
    return {"schema": SCHEMA, "repo": repo, "ops": out}


def parse(text):
    """The overlay document of `text`: {"schema", "repo", "ops": [{id, target {block[, path]}, op, expects, value?,
    value_ref?, reason?, created?}]}. Raises Unreadable."""
    return _check(_raw(text))


# ------------------------------------------------------------------ dump
def _q(s):
    return json.dumps(str(s), ensure_ascii=False)


def dump(doc):
    """The canonical text of a document: keys in a fixed order, every string quoted."""
    out = ["schema: %s" % SCHEMA, "repo: %s" % doc["repo"]]
    if not doc.get("ops"):
        return "\n".join(out + ["ops: []"]) + "\n"
    out.append("ops:")
    for op in doc["ops"]:
        tgt = op["target"]
        t = "{block: %s%s}" % (_q(tgt["block"]) if not REPO_ID.match(tgt["block"]) else tgt["block"],
                               (", path: %s" % _q(tgt["path"])) if tgt.get("path") else "")
        out += ["  - id: %s" % op["id"], "    target: %s" % t, "    op: %s" % op["op"]]
        if "value" in op:
            v = op["value"]
            out.append("    value: %s" % ("[%s]" % ", ".join(_q(x) for x in v) if isinstance(v, list) else _q(v)))
        if "value_ref" in op:
            out.append("    value_ref: %s" % _q(op["value_ref"]))
        out.append("    expects: %d" % op["expects"])
        for k in ("reason", "created"):
            if op.get(k):
                out.append("    %s: %s" % (k, _q(op[k])))
    return "\n".join(out) + "\n"


# ------------------------------------------------------------------ locate
def _ws(s):
    return " ".join((s or "").split()).casefold()


def _heading_is(text, name):
    t, n = _ws(text), _ws(name)
    return t == n or (t.startswith(n) and t[len(n):].lstrip().startswith("("))


def locate(lines, path):
    """[(start, end)] — line ranges of `lines` (a region's inside, split at "\\n") that `path` finds, in order."""
    kind, what = parse_path(path)
    if kind == "all":
        return [(0, len(lines))]
    out = []
    for i, line in enumerate(lines):
        if kind == "heading":
            m = HEADING.match(line.rstrip("\r"))
            if m and _heading_is(m.group(2), what):
                level, j = len(m.group(1)), i + 1
                while j < len(lines):
                    h = HEADING.match(lines[j].rstrip("\r"))
                    if h and len(h.group(1)) <= level:
                        break
                    j += 1
                out.append((i, j))
        elif kind == "field":
            m = FIELD.match(line.rstrip("\r"))
            if m and _ws(m.group(2)) == _ws(what):
                out.append((i, i + 1))
        elif _ws(what) in _ws(line):
            out.append((i, i + 1))
    return out


# ------------------------------------------------------------------ overlay
def _inner(region):
    """(head, the lines between the markers, tail, crlf): head and tail are the markers with their line breaks."""
    crlf = "\r\n" in region
    text = region.replace("\r\n", "\n")
    a = text.index("-->") + 3
    b = text.rindex("<!--")
    head, body, tail = text[:a], text[a:b], text[b:]
    if body.startswith("\n"):
        head, body = head + "\n", body[1:]
    if body.endswith("\n"):
        body, tail = body[:-1], "\n" + tail
    return head, (body.split("\n") if body else []), tail, crlf


def _join(head, lines, tail, crlf):
    text = head + "\n".join(lines) + tail
    return text.replace("\n", "\r\n") if crlf else text


def block_of(region):
    m = BEGIN.search(region or "")
    return m.group(1) if m else None


def _last(lines, s, e):
    """The end of what a span holds: after its last non-blank line (s + 1 at least, the heading or the line itself)."""
    j = e
    while j > s + 1 and not lines[j - 1].strip():
        j -= 1
    return j


def _vlines(v):
    return list(v) if isinstance(v, list) else [v]


def _ref_name(ref):
    rec, _, head = ref.partition("#")
    return rec.strip(), head.strip()


def _evaluate(region, ops, ref_exists):
    """(the lines, [(op, spans, result)]) — what each operation of this block finds and whether it may apply."""
    head, lines, tail, crlf = _inner(region)
    bid = block_of(region)
    out = []
    for op in ops:
        if op["target"]["block"] != bid:
            continue
        spans = locate(lines, op["target"].get("path", ""))
        res = {"id": op["id"], "op": op["op"], "block": bid, "found": len(spans), "expects": op["expects"],
               "state": "applied", "why": ""}
        if len(spans) != op["expects"]:
            res["state"], res["why"] = "held", "знайдено %d, очікувалось %d" % (len(spans), op["expects"])
        elif op.get("value_ref") and not ref_exists(op["value_ref"]):
            res["state"], res["why"] = "held", "value_ref %s — такої підсекції у твоїх записах немає" % op["value_ref"]
        out.append((op, spans, res))
    live = [(op, spans, res) for op, spans, res in out if res["state"] == "applied" and op["op"] in TEXT_OPS]
    for i, (a, sa, ra) in enumerate(live):
        for b, sb, rb in live[i + 1:]:
            if any(x0 < y1 and y0 < x1 for x0, x1 in sa for y0, y1 in sb):
                for r, other in ((ra, b["id"]), (rb, a["id"])):
                    r["state"] = "error"
                    r["why"] = (r["why"] + "; " if r["why"] else "") + "ті самі рядки, що в %s" % other
    return (head, lines, tail, crlf), out


def overlay(region, ops, ref_exists=lambda ref: True):
    """(the region text with this block's operations applied, [result]) — `region` is a whole region (markers
    included); only operations whose target's block is the region's id count. A result is {id, op, block, found,
    expects, state: "applied" | "held" | "error", why}. The markers never change; CRLF stays CRLF."""
    (head, lines, tail, crlf), evald = _evaluate(region, ops, ref_exists)
    edits = []                                          # (start, end, new lines) on the original lines
    for op, spans, res in evald:
        if res["state"] != "applied" or op["op"] not in TEXT_OPS:
            continue
        kind = parse_path(op["target"].get("path", ""))[0]
        for s, e in spans:
            if op["op"] == "replace":
                if op.get("value_ref"):
                    rec, sub = _ref_name(op["value_ref"])
                    new = ["> [оверлей %s: замінено на %s › %s%s]" % (op["id"], rec, sub,
                                                                       (" — " + op["reason"]) if op.get("reason") else "")]
                else:
                    new = _vlines(op["value"])
                if kind == "heading":
                    edits.append((s + 1, _last(lines, s, e), new))
                elif kind == "field" and not isinstance(op["value"] if not op.get("value_ref") else None, list) and not op.get("value_ref"):
                    prefix = FIELD.match(lines[s]).group(1)
                    edits.append((s, s + 1, ["%s %s" % (prefix, op["value"])]))
                else:
                    edits.append((s, e, new))
            elif op["op"] == "remove":
                if kind in ("heading", "all"):
                    a, b = s, e
                else:
                    a, b = s, s + 1
                if (a == 0 or not lines[a - 1].strip()) and (b < len(lines) and not lines[b].strip()):
                    b += 1                              # a blank line on each side: keep one
                elif b >= len(lines) and a > 0 and not lines[a - 1].strip():
                    a -= 1                              # nothing after it: no trailing blank line
                edits.append((a, b, []))
            else:                                       # append
                at = _last(lines, s, e) if kind in ("heading", "all") and e > s else s + 1
                if kind == "all":
                    at = e
                    while at > s and not lines[at - 1].strip():
                        at -= 1
                edits.append((at, at, _vlines(op["value"])))
    for a, b, new in sorted(edits, key=lambda x: (x[0], x[1]), reverse=True):
        lines[a:b] = new
    return _join(head, lines, tail, crlf), [res for _, _, res in evald]


def ignored(region, ops, ref_exists=lambda ref: True):
    """What applied `ignore` operations of this block take from the slots: ALL (the whole block) or the non-blank lines
    their paths find — [] when none applies."""
    (head, lines, tail, crlf), evald = _evaluate(region, ops, ref_exists)
    out = []
    for op, spans, res in evald:
        if op["op"] != "ignore" or res["state"] != "applied":
            continue
        if parse_path(op["target"].get("path", ""))[0] == "all":
            return ALL
        for s, e in spans:
            out += [ln.rstrip("\r") for ln in lines[s:e] if ln.strip() and ln.rstrip("\r") not in out]
    return out


def aliases(region, ops, ref_exists=lambda ref: True):
    """[(the name the path finds, [names])] of the applied `alias` operations of this block: a field's value, a
    heading's text, a matched line."""
    (head, lines, tail, crlf), evald = _evaluate(region, ops, ref_exists)
    out = []
    for op, spans, res in evald:
        if op["op"] != "alias" or res["state"] != "applied":
            continue
        kind = parse_path(op["target"].get("path", ""))[0]
        for s, e in spans:
            line = lines[s].rstrip("\r")
            if kind == "field":
                name = FIELD.match(line).group(3).strip()
            elif kind == "heading":
                name = HEADING.match(line).group(2)
            else:
                name = line.strip()
            out.append((name, list(op["value"])))
    return out


def refs_in(records):
    """`ref_exists` for `overlay`: does "<record id>#<Subsection>" name a subsection of your own text — outside every
    managed region — in `records` (dicts with `id` and `body`)?"""
    bodies = {r.get("id"): cc.strip_managed_regions(r.get("body") or "").replace("\r\n", "\n").split("\n") for r in records}

    def exists(ref):
        rec, sub = _ref_name(ref)
        return rec in bodies and bool(locate(bodies[rec], "#" + sub))
    return exists


def for_block(ops, bid):
    """The operations of `ops` whose target is block `bid`."""
    return [o for o in ops or () if o["target"]["block"] == bid]


def _regions_of(body, ns):
    """The whole regions (markers included) of namespace `ns` in a record's body, in order."""
    rx = re.compile(r"<!--\s*%s:begin\s+id=([A-Za-z0-9_.-]+)[^>]*-->.*?<!--\s*%s:end\s+id=\1\s*-->"
                    % (re.escape(ns), re.escape(ns)), re.S)
    return [m.group(0) for m in rx.finditer(body or "")]


def store_aliases(store_root, repos):
    """[(name, [names])] of every applied `alias` operation of every repository's overlay, on the regions the store's
    records hold. Reads only and never raises: a store, a record or an overlay that cannot be read gives nothing."""
    repos = [r for r in repos or () if os.path.isfile(os.path.join(store_root, "overlays", "%s.yaml" % r.get("id")))]
    if not repos:                                       # no overlay: nothing to read, the records are not loaded
        return []
    try:
        records = cs.Store(store_root).load()
    except Exception:  # noqa: BLE001 — a reader of names must not fail over the store
        return []
    refs, out = refs_in(records), []
    for repo in repos or ():
        try:
            doc = load(store_root, repo["id"])
        except (Unreadable, KeyError):
            continue
        ops = [o for o in (doc or {}).get("ops") or () if o["op"] == "alias"]
        if not ops:
            continue
        for rec in records:
            for region in _regions_of(rec.get("body"), repo.get("namespace") or repo["id"]):
                out.extend(aliases(region, ops, refs))
    return out


# ------------------------------------------------------------------ on disk
def path_of(store_root, repo_id):
    if not isinstance(repo_id, str) or not REPO_ID.match(repo_id):
        raise Unreadable("%r is not a repository id" % (repo_id,))
    return os.path.join(store_root, "overlays", repo_id + ".yaml")


def load(store_root, repo_id):
    """The document of `overlays/<repo>.yaml`, or None when there is none. Raises Unreadable — naming the file — when it
    does not parse, holds an unknown key, another schema or another repository's operations, or does not arrive."""
    p = path_of(store_root, repo_id)
    if not os.path.isfile(p):
        return None
    try:
        text = cs.read_text(p)
    except (OSError, cs.StoreError, UnicodeDecodeError) as e:
        raise Unreadable("%s: not readable (%s)" % (p, e))
    try:
        doc = parse(text)
    except Unreadable as e:
        raise Unreadable("%s: %s" % (p, e))
    if doc["repo"] != repo_id:
        raise Unreadable("%s: holds the operations of %s, not of %s" % (p, doc["repo"], repo_id))
    return doc


def save(store_root, repo_id, doc, replace_unreadable=False):
    """Write `doc` as `overlays/<repo>.yaml` in the canonical form (through the write allow-list). A file there that
    cannot be read is never replaced (Unreadable) unless `replace_unreadable`. Returns the path."""
    p = path_of(store_root, repo_id)
    if not replace_unreadable:
        load(store_root, repo_id)                       # raises for a file that cannot be read
    text = dump(dict(doc, repo=repo_id))
    parse(text)                                         # what is written is always readable
    os.makedirs(cs.check_target(os.path.dirname(p)), exist_ok=True)
    cs.atomic_write(p, text)
    return p
