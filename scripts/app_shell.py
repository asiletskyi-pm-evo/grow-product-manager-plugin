#!/usr/bin/env python3
"""app_shell.py — the desktop app shell (v4.13.0 «Застосунки»): the profiles file and its check.

  schema   the constants the shell and the profiles agree on (levels, permissions, blocks, glyphs)
  check    references/app-profiles.yaml (or --profiles PATH) against them: {"ok": bool, "errors": [...]}

A profile holds shell code and placeholders only (`<jira_project>`, `<dashboard_id>`) — never a user's value. Only the
levels `page` and `app` exist; `full`, `full-access` and `commands` arrive in v4.13.1 and are refused. The file is only
read, never written; local-context.md is never read. Every command ends with one `APP_RESULT {json}` line.
Stdlib only (Python 3.9). Exit 0; 1 when a check fails; 2 for a wrong argument.
"""
import argparse, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROFILES = os.path.join(os.path.dirname(HERE), "references", "app-profiles.yaml")

SHELL_VERSION = 1
LEVELS = ("page", "app")
PERMISSIONS = ("notifications", "menu-bar")
LATER = ("full-access", "shortcuts", "overlay")
BLOCKS = ("table", "list", "number", "chart", "feed", "map")
GLYPHS = ("journey", "os", "chart")
ACTIONS = ("edit", "open-in-claude")
LANGS = ("uk", "en")
LATER_TEXT = "arrives in v4.13.1"
PROFILE_KEYS = ("level", "title", "icon", "permissions", "modules", "menu", "badge", "tray", "notify", "connectors",
                "commands")
MODULE_KEYS = ("id", "block", "source", "home", "title")


class Bad(Exception):
    pass


def result(**kw):
    print("APP_RESULT " + json.dumps(kw, ensure_ascii=False))


# ---- the reader: exactly the shape of references/app-profiles.yaml ------------------------------------------------
# block mappings by indent, block lists of flow or scalar items, and flow values `{k: v, …}` / `[a, b]` / "text".

def _strip_comment(line):
    q = None
    for i, c in enumerate(line):
        if q:
            if c == q:
                q = None
        elif c in "\"'":
            q = c
        elif c == "#" and (i == 0 or line[i - 1] in " \t"):
            return line[:i].rstrip()
    return line.rstrip()


def _scalar(s):
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1]
    if s in ("true", "false"):
        return s == "true"
    if re.fullmatch(r"-?\d+", s):
        return int(s)
    if s in ("", "null", "~"):
        return None
    return s


def _flow(s, i=0):
    """Parse one flow value of `s` from `i`; returns (value, next index)."""
    while i < len(s) and s[i] == " ":
        i += 1
    if i >= len(s):
        raise ValueError("a value is missing")
    c = s[i]
    if c in "{[":
        close, out = ("}" if c == "{" else "]"), ({} if c == "{" else [])
        i += 1
        while True:
            while i < len(s) and s[i] == " ":
                i += 1
            if i >= len(s):
                raise ValueError("unclosed " + c)
            if s[i] == close:
                return out, i + 1
            if c == "{":
                m = re.compile(r"([A-Za-z_][\w.-]*)\s*:\s*").match(s, i)
                if not m:
                    raise ValueError("a flow mapping key is expected")
                v, i = _flow(s, m.end())
                out[m.group(1)] = v
            else:
                v, i = _flow(s, i)
                out.append(v)
            while i < len(s) and s[i] == " ":
                i += 1
            if i < len(s) and s[i] == ",":
                i += 1
            elif i >= len(s) or s[i] != close:
                raise ValueError("',' or '%s' is expected" % close)
    if c in "\"'":
        j = s.find(c, i + 1)
        if j < 0:
            raise ValueError("unclosed quote")
        return s[i + 1:j], j + 1
    j = i
    while j < len(s) and s[j] not in ",}]":
        j += 1
    return _scalar(s[i:j]), j


def _value(text):
    v, end = _flow(text)
    if text[end:].strip():
        raise ValueError("text after the value")
    return v


def read_profiles_text(text):
    """The profiles file as a dict. ValueError('line N: …') on anything outside the shape."""
    root = {}
    stack = [(-1, root)]                 # (indent of the key that owns the container, container)
    pending = None                       # (indent, container, key) — `key:` waiting for its block
    for n, raw in enumerate((text or "").replace("\r\n", "\n").split("\n"), 1):
        if "\t" in raw[:len(raw) - len(raw.lstrip())]:
            raise ValueError("line %d: tab indentation" % n)
        line = _strip_comment(raw)
        if not line.strip():
            continue
        ind, body = len(line) - len(line.lstrip(" ")), line.strip()
        try:
            if pending is not None:
                p_ind, p_cont, p_key = pending
                pending = None
                if ind > p_ind:
                    child = [] if body.startswith("- ") or body == "-" else {}
                    p_cont[p_key] = child
                    stack.append((p_ind, child))
            is_item = body.startswith("- ") or body == "-"
            while len(stack) > 1 and ind <= stack[-1][0] and not (is_item and isinstance(stack[-1][1], list)):
                stack.pop()
            cont = stack[-1][1]
            if body.startswith("- ") or body == "-":
                if not isinstance(cont, list):
                    raise ValueError("a list item outside a list")
                cont.append(_value(body[1:].strip()))
                continue
            m = re.match(r"([A-Za-z_][\w.-]*):(?:\s+(.*))?$", body)
            if not m or not isinstance(cont, dict):
                raise ValueError("unsupported YAML")
            key, val = m.group(1), m.group(2)
            if val is None or not val.strip():
                cont[key] = None
                pending = (ind, cont, key)
            else:
                cont[key] = _value(val)
        except ValueError as e:
            raise ValueError("line %d: %s" % (n, e))
    return root


def load_profiles(path=None):
    """The profiles file as a dict: {version, profiles: {name: profile}}."""
    path = path or PROFILES
    try:
        with open(path, encoding="utf-8") as f:
            return read_profiles_text(f.read())
    except (OSError, ValueError) as e:
        raise Bad("profiles do not read: %s" % e)


# ---- the check ----------------------------------------------------------------------------------------------------

_PLACEHOLDER = re.compile(r"<[^<>\s]+>")
_VALUE_LIKE = (
    ("URL", re.compile(r"[A-Za-z][A-Za-z0-9+.-]*://|\bwww\.|\b[\w-]+\.(?:com|ai|io|net|org|app|dev|atlassian)\b/?", re.I)),
    ("e-mail", re.compile(r"[^\s@]+@[^\s@]+\.[A-Za-z]{2,}")),
    ("UUID", re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I)),
    ("Jira key", re.compile(r"\b[A-Z][A-Z0-9]+-\d+\b")),
)


def _strings(node):
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for k, v in node.items():
            yield from _strings(k)
            yield from _strings(v)
    elif isinstance(node, list):
        for v in node:
            yield from _strings(v)


def _title(t, where, errs):
    if not isinstance(t, dict) or any(not isinstance(t.get(k), str) or not t.get(k).strip() for k in LANGS):
        errs.append("%s: title needs both uk and en" % where)


def check_profile(name, prof):
    """The errors of one profile — [] when it is clean."""
    errs, w = [], "profile %s" % name
    if not isinstance(prof, dict):
        return ["%s: not a mapping" % w]
    for k in prof:
        if k not in PROFILE_KEYS:
            errs.append("%s: unknown key '%s'" % (w, k))
    level = prof.get("level")
    if level == "full":
        errs.append("%s: level full %s" % (w, LATER_TEXT))
    elif level not in LEVELS:
        errs.append("%s: unknown level '%s'" % (w, level))
    _title(prof.get("title"), w, errs)
    glyph = (prof.get("icon") or {}).get("glyph") if isinstance(prof.get("icon"), dict) else None
    if glyph not in GLYPHS:
        errs.append("%s: unknown glyph '%s'" % (w, glyph))
    perms = prof.get("permissions") or []
    for p in perms if isinstance(perms, list) else []:
        if p == "full-access":
            errs.append("%s: permission full-access %s" % (w, LATER_TEXT))
        elif p in LATER:
            errs.append("%s: permission '%s' is unknown for now (later release)" % (w, p))
        elif p not in PERMISSIONS:
            errs.append("%s: unknown permission '%s'" % (w, p))
    if prof.get("commands"):
        errs.append("%s: commands %s" % (w, LATER_TEXT))
    ids, homes = set(), 0
    modules = prof.get("modules") or []
    for i, m in enumerate(modules if isinstance(modules, list) else []):
        mw = "%s module %s" % (w, (m or {}).get("id", i) if isinstance(m, dict) else i)
        if not isinstance(m, dict):
            errs.append("%s: not a mapping" % mw)
            continue
        for k in m:
            if k not in MODULE_KEYS:
                errs.append("%s: unknown key '%s'" % (mw, k))
        mid = m.get("id")
        if not isinstance(mid, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", mid):
            errs.append("%s: bad id" % mw)
        elif mid in ids:
            errs.append("%s: duplicate module id '%s'" % (mw, mid))
        ids.add(mid)
        if m.get("block") not in BLOCKS:
            errs.append("%s: unknown block '%s'" % (mw, m.get("block")))
        if not isinstance(m.get("source"), str) or not m.get("source"):
            errs.append("%s: source is missing" % mw)
        if m.get("home"):
            homes += 1
        _title(m.get("title"), mw, errs)
    if homes > 1:
        errs.append("%s: more than one home module (%d)" % (w, homes))
    menu = prof.get("menu") or []
    for e in menu if isinstance(menu, list) else []:
        if isinstance(e, str):
            if e not in ids:
                errs.append("%s: menu entry '%s' is not a module id" % (w, e))
        elif isinstance(e, dict):
            if e.get("action") not in ACTIONS:
                errs.append("%s: menu action '%s' is unknown" % (w, e.get("action")))
            for k in e:
                if k not in ("action", "accel"):
                    errs.append("%s: menu entry has unknown key '%s'" % (w, k))
            if "accel" in e and not isinstance(e["accel"], str):
                errs.append("%s: menu accel is not text" % w)
        else:
            errs.append("%s: menu entry is neither a module id nor an action" % w)
    for c in prof.get("connectors") or []:
        if not isinstance(c, dict) or not isinstance(c.get("role"), str) or not isinstance(c.get("needs"), str):
            errs.append("%s: a connector needs a role and a needs" % w)
    for s in _strings({k: v for k, v in prof.items()}):
        bare = _PLACEHOLDER.sub("", s)
        for what, rx in _VALUE_LIKE:
            if rx.search(bare):
                errs.append("%s: value in a template (%s): '%s'" % (w, what, s[:40]))
                break
    return errs


def check_doc(doc):
    errs = []
    if not isinstance(doc, dict) or doc.get("version") != SHELL_VERSION:
        errs.append("version must be %d" % SHELL_VERSION)
    profiles = doc.get("profiles") if isinstance(doc, dict) else None
    if not isinstance(profiles, dict) or not profiles:
        return errs + ["no profiles"]
    for name, prof in profiles.items():
        errs += check_profile(name, prof)
    return errs


# ---- the commands -------------------------------------------------------------------------------------------------

def cmd_schema(_a):
    result(ok=True, version=SHELL_VERSION, levels=list(LEVELS), permissions=list(PERMISSIONS), later=list(LATER),
           blocks=list(BLOCKS), glyphs=list(GLYPHS), actions=list(ACTIONS))
    return 0


def cmd_check(a):
    errs = check_doc(load_profiles(a.profiles))
    result(ok=not errs, errors=errs)
    return 1 if errs else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="the desktop app shell: profiles and their check")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("schema").set_defaults(fn=cmd_schema)
    c = sub.add_parser("check")
    c.add_argument("--profiles", default=None)
    c.set_defaults(fn=cmd_check)
    a = ap.parse_args(argv)
    try:
        return a.fn(a)
    except Bad as e:
        result(ok=False, error=str(e))
        return 1


if __name__ == "__main__":
    sys.exit(main())
