#!/usr/bin/env python3
"""app_shell.py — the desktop app shell (v4.13.0 «Застосунки»): the profiles file and its check.

  schema   the constants the shell and the profiles agree on (levels, permissions, blocks, glyphs)
  check    references/app-profiles.yaml (or --profiles PATH) against them: {"ok": bool, "errors": [...]}
  wrap     an HTML page + a profile -> an installable app: the permission manifest, the shell (shell.js, shell.css),
           the profile as JSON; the page's own body goes into <div class="gpm-page">. Writes nothing on a refusal.

A profile holds shell code and placeholders only (`<jira_project>`, `<dashboard_id>`) — never a user's value. Only the
levels `page` and `app` exist; `full`, `full-access` and `commands` arrive in v4.13.1 and are refused. The file is only
read, never written; local-context.md is never read. Every command ends with one `APP_RESULT {json}` line.
Stdlib only (Python 3.9). Exit 0; 1 when a check fails; 2 for a wrong argument.
"""
import argparse, html, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROFILES = os.path.join(os.path.dirname(HERE), "references", "app-profiles.yaml")
SHELL_DIR = os.path.join(HERE, "app_shell")

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

_PLACEHOLDER = re.compile(r"<[a-z][a-z0-9_]*>")
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
    if not isinstance(perms, list):
        errs.append("%s: permissions must be a list" % w)
        perms = []
    for p in perms:
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
    if not isinstance(modules, list):
        errs.append("%s: modules must be a list" % w)
        modules = []
    for i, m in enumerate(modules):
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
    if not isinstance(menu, list):
        errs.append("%s: menu must be a list" % w)
        menu = []
    for e in menu:
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


# ---- wrap ---------------------------------------------------------------------------------------------------------

DB_RULES = [{"path": "", "read": "view", "write": "admin"},
            {"path": "snapshot", "read": "view", "write": "owner"},
            {"path": "config", "read": "view", "write": "owner"},
            {"path": "runs", "read": "view", "write": "owner"}]


def parse_connector(spec):
    """`SERVER:TOOL[,TOOL]` -> {server, tools}. Bad -> Bad."""
    server, sep, tools = (spec or "").partition(":")
    names = [x.strip() for x in tools.split(",")] if sep else []
    if not server.strip() or not names or not all(names):
        raise Bad("connector '%s': expected SERVER:TOOL[,TOOL]" % spec)
    return {"server": server.strip(), "tools": names}


def capabilities(prof, connectors):
    """The `capabilities` the skill passes to the publication, verbatim. `connectors` = ['SERVER:TOOL[,TOOL]', …]."""
    caps = {"desktop": {}, "db": {"rules": [dict(r) for r in DB_RULES]}, "user": {"scopes": ["profile"]}}
    servers = []
    for spec in connectors or []:
        c = parse_connector(spec)
        same = [x for x in servers if x["server"] == c["server"]]
        if same:
            same[0]["tools"] += [t for t in c["tools"] if t not in same[0]["tools"]]
        else:
            servers.append(c)
    if servers:
        caps["mcp"] = {"servers": servers}
    return caps


def _read(name):
    with open(os.path.join(SHELL_DIR, name), encoding="utf-8", newline="") as f:
        return f.read()


def _json_in_script(obj):
    """JSON that cannot close or open anything inside a <script> element."""
    return (json.dumps(obj, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
            .replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))


def wrap_page(page, name, prof, lang):
    """The page as an app: manifest + meta + style in <head>, header + modules + the page's body in .gpm-page, the
    profile and the shell script at the end of <body>. Bad on anything it cannot wrap; the same input, the same bytes."""
    if lang not in LANGS:
        raise Bad("unknown language '%s'" % lang)
    errs = check_profile(name, prof)
    if errs:
        raise Bad("profile '%s' does not pass the check: %s" % (name, "; ".join(errs)))
    if "claude-artifacts-manifest" in page or re.search(r"""name\s*=\s*["']?grow-pm-app""", page, re.I):
        raise Bad("already an app: the page has a manifest or the grow-pm-app meta")
    if re.search(r"<script\b[^>]*\bsrc\s*=", page, re.I):
        raise Bad("the page has a <script src>: a published page takes inline scripts only")
    head_end = re.search(r"</head\s*>", page, re.I)
    body_open = re.search(r"<body\b[^>]*>", page, re.I)
    body_ends = list(re.finditer(r"</body\s*>", page, re.I))
    if not re.search(r"<head\b[^>]*>", page, re.I) or not head_end:
        raise Bad("the page has no <head>")
    if not body_open or not body_ends or body_open.start() < head_end.end():
        raise Bad("the page has no <body>")
    body_end = body_ends[-1]
    manifest = '<script type="application/json" id="claude-artifacts-manifest">%s</script>' % _json_in_script(
        {"permissions": list(prof.get("permissions") or [])})
    meta = '<meta name="grow-pm-app" content="%s;shell=%d">' % (html.escape(name, quote=True), SHELL_VERSION)
    style = '<style id="gpm-style">\n%s</style>' % _read("shell.css")
    shown = dict(prof)
    shown["connectors"] = [{"role": c.get("role")} for c in prof.get("connectors") or []]
    shown.update(name=name, lang=lang, shell=SHELL_VERSION)
    title = html.escape((prof.get("title") or {}).get(lang, ""), quote=False)
    shell = ('<header class="gpm-shell"><span class="gpm-title">%s</span><div class="gpm-actions"></div></header>'
             '<main class="gpm-modules" hidden></main><div class="gpm-page">' % title)
    tail = ('</div><script id="gpm-profile" type="application/json">%s</script>\n<script id="gpm-shell">\n%s</script>'
            % (_json_in_script(shown), _read("shell.js")))
    return (page[:head_end.start()] + manifest + meta + style + page[head_end.start():body_open.end()] + shell
            + page[body_open.end():body_end.start()] + tail + page[body_end.start():])


# ---- the commands -------------------------------------------------------------------------------------------------

def cmd_schema(_a):
    result(ok=True, version=SHELL_VERSION, levels=list(LEVELS), permissions=list(PERMISSIONS), later=list(LATER),
           blocks=list(BLOCKS), glyphs=list(GLYPHS), actions=list(ACTIONS))
    return 0


def cmd_check(a):
    errs = check_doc(load_profiles(a.profiles))
    result(ok=not errs, errors=errs)
    return 1 if errs else 0


def cmd_wrap(a):
    doc = load_profiles(a.profiles)
    prof = (doc.get("profiles") or {}).get(a.profile)
    if prof is None:
        raise Bad("no profile '%s' (there are: %s)" % (a.profile, ", ".join(sorted(doc.get("profiles") or {}))))
    try:
        with open(a.page, encoding="utf-8", newline="") as f:
            page = f.read()
    except (OSError, ValueError) as e:
        raise Bad("the page does not read: %s" % e)
    caps = capabilities(prof, a.connector)
    out = wrap_page(page, a.profile, prof, a.lang)
    try:
        with open(a.out, "w", encoding="utf-8", newline="") as f:
            f.write(out)
    except OSError as e:
        raise Bad("the app does not write: %s" % e)
    result(ok=True, out=a.out, bytes=len(out.encode("utf-8")), profile=a.profile, shell=SHELL_VERSION,
           permissions=list(prof.get("permissions") or []), capabilities=caps)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="the desktop app shell: profiles and their check")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("schema").set_defaults(fn=cmd_schema)
    c = sub.add_parser("check")
    c.add_argument("--profiles", default=None)
    c.set_defaults(fn=cmd_check)
    w = sub.add_parser("wrap")
    w.add_argument("--page", required=True)
    w.add_argument("--profile", required=True)
    w.add_argument("--out", required=True)
    w.add_argument("--lang", default="uk", choices=LANGS)
    w.add_argument("--connector", action="append", default=[], metavar="SERVER:TOOL[,TOOL]")
    w.add_argument("--profiles", default=None)
    w.set_defaults(fn=cmd_wrap)
    a = ap.parse_args(argv)
    try:
        return a.fn(a)
    except Bad as e:
        result(ok=False, error=str(e))
        return 1


if __name__ == "__main__":
    sys.exit(main())
