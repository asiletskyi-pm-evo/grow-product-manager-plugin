#!/usr/bin/env python3
"""Grow PM — helpers shared by the context-provider scripts (since v3.10.0).

Used by session_start.py (digest), write_gate.py (provider write boundary) and
provider_bundle.py (bundle builder). Semantics: references/context-provider-protocol.md.

- read_yaml_subset    manifests and registrations: scalars, lists, one nesting level.
                      Deliberately NOT PyYAML: the same file must parse the same way
                      on every host (CI has PyYAML, a user's sandbox may not).
- strip_managed_regions  blank out <!-- <ns>:begin … --> … <!-- <ns>:end … --> regions,
                      keeping line numbers, so headings inside them are never counted.
- vault_entries / vault_search_bullets  the two local-context.md sections providers use.
- find_registrations / provider_roots / boundary_hit / is_under  the write boundary.
- slugify / vault_modes / storage_root / find_context / managed_spans  the context store
                      (since v3.11.0, references/context-protocol.md).

Stdlib only. Callers that run as hooks must fail open; these helpers raise only
ValueError (bad YAML) and never touch the network.
"""
import fnmatch
import glob
import json
import os
import re
import unicodedata

N = lambda s: unicodedata.normalize("NFC", s or "")

# Ukrainian → Latin, shared by slugify() and the bundle builder's name matching.
TRANSLIT = {"а": "a", "б": "b", "в": "v", "г": "h", "ґ": "g", "д": "d", "е": "e", "є": "ie", "ж": "zh", "з": "z",
            "и": "y", "і": "i", "ї": "i", "й": "i", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p",
            "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh",
            "щ": "shch", "ю": "iu", "я": "ia", "ь": "", "ʼ": "", "'": "", "’": ""}


# ---------------------------------------------------------------- YAML subset
def _strip_comment(s):
    out, q = [], None
    for i, ch in enumerate(s):
        if q:
            out.append(ch)
            if ch == q and (q == "'" or s[i - 1] != "\\"):
                q = None
        elif ch in "\"'":
            q = ch; out.append(ch)
        elif ch == "#" and (i == 0 or s[i - 1] in " \t"):
            break
        else:
            out.append(ch)
    return "".join(out).rstrip()


def _scalar(v, lineno):
    v = v.strip()
    if v == "":
        return ""
    if v == "[]":
        return []
    if v.startswith('"'):
        if not v.endswith('"') or len(v) < 2:
            raise ValueError("line %d: unsupported YAML (unterminated string)" % lineno)
        return json.loads(v)
    if v.startswith("'"):
        if not v.endswith("'") or len(v) < 2:
            raise ValueError("line %d: unsupported YAML (unterminated string)" % lineno)
        return v[1:-1].replace("''", "'")
    if v[0] in "[{&*!|>":
        raise ValueError("line %d: unsupported YAML (flow style, anchor or block scalar)" % lineno)
    if re.fullmatch(r"-?\d+", v):
        return int(v)
    if v in ("true", "false"):
        return v == "true"
    return v


def read_yaml_subset(text):
    """`key: value`; `key:` + `  - item` list; `key:` + `  sub: value` (one level).
    Anything else raises ValueError('line N: unsupported YAML …')."""
    data, cur_key, cur_kind = {}, None, None
    for lineno, raw in enumerate((text or "").replace("\r\n", "\n").split("\n"), 1):
        line = _strip_comment(raw)
        if not line.strip():
            continue
        if line.strip() in ("---", "..."):
            continue
        indent = len(line) - len(line.lstrip(" "))
        body = line.strip()
        if "\t" in raw[:indent + 1]:
            raise ValueError("line %d: unsupported YAML (tab indentation)" % lineno)
        if indent == 0:
            m = re.match(r"^([A-Za-z_][\w.-]*):(?:\s+(.*))?$", body)
            if not m:
                raise ValueError("line %d: unsupported YAML" % lineno)
            key, val = m.group(1), m.group(2)
            if val is None or val.strip() == "":
                data[key] = None; cur_key, cur_kind = key, None
            else:
                data[key] = _scalar(val, lineno); cur_key, cur_kind = None, None
            continue
        if cur_key is None:
            raise ValueError("line %d: unsupported YAML (indented line without a parent key)" % lineno)
        if body.startswith("- ") or body == "-":
            if cur_kind == "map":
                raise ValueError("line %d: unsupported YAML (list inside a mapping)" % lineno)
            item = body[1:].strip()
            if re.match(r"^[A-Za-z_][\w.-]*:(\s|$)", item):
                raise ValueError("line %d: unsupported YAML (mapping inside a list)" % lineno)
            if data[cur_key] is None:
                data[cur_key] = []
            cur_kind = "list"
            data[cur_key].append(_scalar(item, lineno))
            continue
        m = re.match(r"^([A-Za-z_][\w.-]*):(?:\s+(.*))?$", body)
        if not m or cur_kind == "list":
            raise ValueError("line %d: unsupported YAML" % lineno)
        if m.group(2) is None or m.group(2).strip() == "":
            raise ValueError("line %d: unsupported YAML (nesting deeper than one level)" % lineno)
        if data[cur_key] is None:
            data[cur_key] = {}
        cur_kind = "map"
        data[cur_key][m.group(1)] = _scalar(m.group(2), lineno)
    for k, v in data.items():
        if v is None:
            data[k] = ""
    return data


# --------------------------------------------------------- managed regions
REGION_RE = re.compile(
    r"<!--\s*([a-z][a-z0-9-]*(?::section)?):begin(?:\s+id=([A-Za-z0-9_.-]+))?[^>]*-->"
    r".*?"
    r"<!--\s*\1:end(?:\s+id=\2)?\s*-->", re.S)


def strip_managed_regions(text):
    """Replace every managed region with as many newlines as it spanned."""
    return REGION_RE.sub(lambda m: "\n" * m.group(0).count("\n"), text or "")


def managed_spans(text):
    """[start, end) character offsets of every managed region, begin marker to end marker."""
    return [(m.start(), m.end()) for m in REGION_RE.finditer(text or "")]


# ------------------------------------------------ local-context.md sections
def _section(text, heading_re, level):
    m = re.search(heading_re, text, re.M)
    if not m:
        return ""
    rest = text[m.end():]
    stop = re.search(r"^#{1,%d} " % level, rest, re.M)
    return rest[:stop.start()] if stop else rest


def vault_entries(context_text):
    """[(vault_path, plugin_folder)] from `## Obsidian Vaults` — table rows and/or
    `- path:` / `plugin_folder:` YAML items. Paths are expanded and normalised."""
    sec = _section(context_text or "", r"^## Obsidian Vaults.*$", 2)
    out = []
    for row in re.findall(r"^\|\s*\d+\s*\|([^\n]*)$", sec, re.M):
        cells = [c.strip() for c in row.split("|")]
        if len(cells) >= 2 and cells[0] and cells[1]:
            out.append((cells[0], cells[1]))
    for m in re.finditer(r"^\s*-\s*path:\s*(.+?)\s*$((?:\n\s+\w+:.*)*)", sec, re.M):
        p = m.group(1).strip().strip('"').strip("'")
        f = re.search(r"plugin_folder:\s*\"?([^\"\n#]+?)\"?\s*(?:#.*)?$", m.group(2), re.M)
        out.append((p, f.group(1).strip() if f else ""))
    seen, uniq = set(), []
    for p, f in out:
        key = (os.path.normpath(os.path.expanduser(N(p))), N(f))
        if key not in seen:
            seen.add(key); uniq.append(key)
    return uniq


def vault_modes(context_text):
    """[(vault_path, plugin_folder, sync_mode)] from `## Obsidian Vaults`, table rows first, then
    `- path:` items; paths expanded and normalised, sync_mode lowercased (YAML default `auto`)."""
    sec = _section(context_text or "", r"^## Obsidian Vaults.*$", 2)
    out = []
    for row in re.findall(r"^\|\s*\d+\s*\|([^\n]*)$", sec, re.M):
        cells = [c.strip() for c in row.split("|")]
        if len(cells) >= 2 and cells[0] and cells[1]:
            out.append((cells[0], cells[1], cells[3].lower() if len(cells) > 3 else ""))
    for m in re.finditer(r"^\s*-\s*path:\s*(.+?)\s*$((?:\n\s+\w+:.*)*)", sec, re.M):
        p = m.group(1).strip().strip('"').strip("'")
        f = re.search(r"plugin_folder:\s*\"?([^\"\n#]+?)\"?\s*(?:#.*)?$", m.group(2), re.M)
        s = re.search(r"sync_mode:\s*\"?([A-Za-z-]+)", m.group(2))
        out.append((p, f.group(1).strip() if f else "", s.group(1).lower() if s else "auto"))
    seen, uniq = set(), []
    for p, f, s in out:
        key = (os.path.normpath(os.path.expanduser(N(p))), N(f))
        if key not in seen:
            seen.add(key); uniq.append(key + (s,))
    return uniq


def storage_root(context_text, home=None):
    """`storage_root` of persistent-storage.md: the first vault whose sync mode is not `off`
    → {vault_path}/{plugin_folder}; otherwise ~/.grow-pm."""
    for p, f, s in vault_modes(context_text):
        if s != "off":
            return os.path.join(p, f) if f else p
    return os.path.join(home or os.path.expanduser("~"), ".grow-pm")


def find_context(explicit=None, home=None):
    """The user's local-context.md: an explicit path — that one only, None when it does not exist —
    else $GROW_PM_CONTEXT_PATH, else ~/.grow-pm/local-context.md — the first that exists, or None."""
    if explicit:
        p = os.path.expanduser(explicit)
        return p if os.path.isfile(p) else None
    for p in (os.environ.get("GROW_PM_CONTEXT_PATH"),
              os.path.join(home or os.path.expanduser("~"), ".grow-pm", "local-context.md")):
        if p and os.path.isfile(os.path.expanduser(p)):
            return os.path.expanduser(p)
    return None


def slugify(text):
    """Lower-case ASCII slug: Cyrillic through TRANSLIT, any other run of characters → '-'."""
    s = "".join(TRANSLIT.get(ch, ch) for ch in N(text).lower())
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "section"


def _split_items(s):
    """Split on , and ; outside parentheses and double quotes (a quoted title keeps its commas)."""
    items, depth, cur, inq = [], 0, [], False
    for i, ch in enumerate(s):
        if ch == '"' and (i == 0 or s[i - 1] != "\\"):
            inq = not inq
        elif not inq and ch == "(":
            depth += 1
        elif not inq and ch == ")":
            depth = max(0, depth - 1)
        if ch in ",;" and depth == 0 and not inq:
            items.append("".join(cur).strip()); cur = []
        else:
            cur.append(ch)
    items.append("".join(cur).strip())
    return [i for i in items if i]


def vault_search_bullets(context_text):
    """Providers declared in `### Vault Search MCP` (protocol §3c)."""
    sec = _section(context_text or "", r"^### Vault Search MCP\s*$", 3)
    out = []
    for m in re.finditer(r"^-\s+([a-z0-9][a-z0-9-]*):\s*(.+)$", sec, re.M):
        d = {"id": m.group(1), "scope": "", "tools": "", "index": "", "mode": "", "access": "", "read_only": False}
        for item in _split_items(m.group(2)):
            kv = re.match(r"^(scope|tools|index|mode|access)\s*=\s*(.+)$", item, re.I)
            low = item.lower()
            if kv:
                d[kv.group(1).lower()] = kv.group(2).strip()
            elif low == "read-only":
                d["read_only"] = True
            elif low in ("vpn only", "vpn"):
                d["access"] = "vpn"
            elif low in ("live", "snapshot"):
                d["mode"] = low
        if d["index"].lower() == "none":
            d["index"] = ""
        d["mode"] = d["mode"] or "live"
        d["access"] = d["access"] or ("local" if d["index"] else "open")
        out.append(d)
    return out


# ----------------------------------------------------------- registrations
def find_registrations(entries, extra_dirs=None, skipped=None):
    """Read `{vault}/{plugin_folder}/_System/providers/*.yaml` for every vault entry,
    plus `~/.grow-pm/providers/*.yaml` (or `extra_dirs` when given). Unreadable or
    invalid files are skipped — and listed as (path, reason) in `skipped` when a list
    is given. Returns dicts with normalised `paths`, `writable`."""
    dirs = [os.path.join(v, f, "_System", "providers") for v, f in entries]
    dirs += [os.path.expanduser("~/.grow-pm/providers")] if extra_dirs is None else list(extra_dirs)
    regs, seen = [], set()
    for d in dirs:
        for p in sorted(glob.glob(os.path.join(d, "*.yaml"))):
            why = None
            try:
                r = read_yaml_subset(open(p, encoding="utf-8").read())
            except UnicodeDecodeError:
                why = "not UTF-8 text"
            except ValueError as e:
                why = str(e)
            except OSError as e:
                why = e.strerror or "cannot be opened"
            if why:
                if skipped is not None:
                    skipped.append((p, why))
                continue
            rid = r.get("id")
            if not rid:
                if skipped is not None:
                    skipped.append((p, "no id"))
                continue
            if rid in seen:
                continue
            seen.add(rid)
            paths = r.get("paths") or ([r["path"]] if r.get("path") else [])
            r["paths"] = [os.path.normpath(os.path.expanduser(N(str(x)))) for x in paths if str(x).strip()]
            r["writable"] = [N(str(x)) for x in (r.get("writable") or []) if str(x).strip()]
            r["_file"] = p
            regs.append(r)
    return regs


def provider_roots(regs):
    """Existing local roots of active registrations, unique, in order."""
    out = []
    for r in regs:
        if str(r.get("status", "active")) == "paused":
            continue
        for p in r.get("paths", []):
            if os.path.isdir(p) and p not in out:
                out.append(p)
    return out


def _norm(p):
    """Absolute, symlinks resolved (vaults in iCloud/Dropbox are often symlinked; /tmp is /private/tmp on macOS), NFC."""
    return N(os.path.realpath(os.path.abspath(os.path.expanduser(N(p)))))


def is_under(path, roots):
    """Component-wise containment: '/v/a-b/x' is not under '/v/a'."""
    p = _norm(path)
    for r in roots:
        r = _norm(r)
        if p == r or p.startswith(r.rstrip(os.sep) + os.sep):
            return True
    return False


def _writable(rel, globs):
    rel = rel.replace(os.sep, "/")
    for g in globs:
        g = g.replace(os.sep, "/")
        if g.endswith("/"):
            if rel == g.rstrip("/") or rel.startswith(g):
                return True
        elif fnmatch.fnmatchcase(rel, g):
            return True
    return False


def boundary_hit(path, regs):
    """The registration whose read-only root contains `path` outside its `writable`
    globs, or None when the path is free to write."""
    p = _norm(path)
    for r in regs:
        if str(r.get("status", "active")) == "paused":
            continue
        for root in r.get("paths", []):
            if is_under(p, [root]):
                rel = os.path.relpath(p, _norm(root))
                if not _writable(rel, r.get("writable", [])):
                    return r
    return None
