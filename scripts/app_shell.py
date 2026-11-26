#!/usr/bin/env python3
"""app_shell.py — the desktop app shell (v4.13.0 «Застосунки»): the profiles file and its check.

  schema   the constants the shell and the profiles agree on (levels, permissions, blocks, glyphs)
  check    references/app-profiles.yaml (or --profiles PATH) against them: {"ok": bool, "errors": [...]}
  wrap     an HTML page + a profile -> an installable app: the permission manifest, the shell (shell.js, shell.css),
           the profile as JSON; the page's own body goes into <div class="gpm-page">. Writes nothing on a refusal.
  theme    token files of the products' design systems -> theme candidates (light, dark, contrast check, the built-in
           `neutral`); --pick ID writes the one theme that `snapshot --theme` takes
  snapshot sections + products (+ a theme, + connector bindings) -> one JSON file per database document under
           DIR/<collection>/<id>.json, ready for a batch write into the artifact's database. Writes nothing on a refusal.

A profile holds shell code and placeholders only (`<jira_project>`, `<dashboard_id>`) — never a user's value. Only the
levels `page` and `app` exist; `full`, `full-access` and `commands` arrive in v4.13.1 and are refused. The file is only
read, never written; local-context.md is never read. Every command ends with one `APP_RESULT {json}` line.
Stdlib only (Python 3.9). Exit 0; 1 when a check fails; 2 for a wrong argument.
"""
import argparse, colorsys, copy, datetime, html, json, math, os, re, sys

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
SECTION = re.compile(r"^[a-z0-9][a-z0-9.-]{0,63}$")
PRODUCT = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
DOC_MAX = 256 * 1024          # a database document, serialized
SEGMENT_MAX = 200             # a path segment, in bytes
LABEL_MAX = 24
THRESHOLDS = {"warning": 0.10, "critical": 0.25}
PEOPLE_KEYS = ("email", "e-mail", "author", "assignee", "person", "owner", "reporter")
THEME_KEYS = ("v", "id", "light", "dark", "font", "radius")
TOKENS = ("bg", "surface", "text", "muted", "accent", "border", "ok", "warn", "crit")
FONTS = ("Inter", "Roboto", "Open Sans", "Montserrat", "Manrope", "Rubik", "Nunito", "PT Sans", "Fira Sans",
         "IBM Plex Sans", "Noto Sans", "Golos Text")      # Google Fonts with Cyrillic; shell.js carries the same list
# The built-in theme: the default of every app. shell.css holds the same values as the defaults of the --gpm-*
# variables (a test compares them); the system font stack, so no network request.
NEUTRAL = {"v": 1, "id": "neutral",
           "light": {"bg": "#f6f6f4", "surface": "#ffffff", "text": "#1f2328", "muted": "#5c646d", "accent": "#2f6fde",
                     "border": "#d0d7de", "ok": "#1a7f37", "warn": "#9a6700", "crit": "#cf222e"},
           "dark": {"bg": "#121417", "surface": "#1b1e23", "text": "#e8eaed", "muted": "#a7adb5", "accent": "#6aa0f5",
                    "border": "#2c3138", "ok": "#3fb950", "warn": "#d29922", "crit": "#f85149"},
           "font": "", "radius": 8}
# token -> backgrounds it is read on, and the WCAG ratio it needs there
NEEDS = {"text": (("bg", 4.5), ("surface", 4.5)), "muted": (("bg", 4.5), ("surface", 4.5)),
         "accent": (("surface", 3.0),), "ok": (("surface", 3.0),), "warn": (("surface", 3.0),), "crit": (("surface", 3.0),)}
TOKEN_FILE_KEYS = ("product", "light", "dark", "font", "radius") + TOKENS


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


# ---- snapshot -----------------------------------------------------------------------------------------------------

def check_theme(theme):
    """The errors of one theme `{v: 1, id, light: {<TOKENS>}, dark: {<TOKENS>}, font, radius}` — [] when it is clean:
    exactly the nine tokens, each #rrggbb, in light and in dark; font "" (the system font) or one of FONTS; radius a
    whole number 0-24. Contrast is a different question: see theme_weak."""
    if not isinstance(theme, dict):
        return ["theme: not a mapping"]
    errs = ["theme: unknown key '%s'" % k for k in theme if k not in THEME_KEYS]
    errs += ["theme: '%s' is missing" % k for k in THEME_KEYS if k not in theme]
    if theme.get("v") != 1 or isinstance(theme.get("v"), bool):
        errs.append("theme: v must be 1")
    if not isinstance(theme.get("id"), str) or not theme.get("id"):
        errs.append("theme: id must be text")
    f = theme.get("font")
    if "font" in theme and (not isinstance(f, str) or (f != "" and f not in FONTS)):
        errs.append("theme: font must be \"\" (the system font) or one of: %s" % ", ".join(FONTS))
    for side in ("light", "dark"):
        tokens = theme.get(side)
        if side not in theme:
            continue
        if not isinstance(tokens, dict):
            errs.append("theme: %s must be a mapping of tokens" % side)
            continue
        errs += ["theme: %s has an unknown token '%s'" % (side, k) for k in tokens if k not in TOKENS]
        errs += ["theme: %s.%s is missing" % (side, k) for k in TOKENS if k not in tokens]
        for k in TOKENS:
            if k in tokens and (not isinstance(tokens[k], str) or not COLOR.match(tokens[k])):
                errs.append("theme: %s.%s must be #rrggbb" % (side, k))
    r = theme.get("radius")
    if "radius" in theme and (isinstance(r, bool) or not isinstance(r, int) or not 0 <= r <= 24):
        errs.append("theme: radius must be a whole number 0-24")
    return errs


# ---- theme: contrast, dark derivation, candidates -------------------------------------------------------------------

def _rgb(h):
    return tuple(int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))


def _lum(h):
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in _rgb(h)]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def _ratio(a, b):
    hi, lo = sorted((_lum(a), _lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def contrast(a, b):
    """The WCAG 2.x contrast ratio of two #rrggbb colours, 1.0-21.0, to two decimals."""
    return round(_ratio(a, b), 2)


def hls(h):
    """(hue, lightness, saturation) of a #rrggbb colour, each 0-1."""
    return colorsys.rgb_to_hls(*_rgb(h))


def _hex(hue, light, sat):
    r, g, b = colorsys.hls_to_rgb(hue, min(1.0, max(0.0, light)), sat)
    return "#%02x%02x%02x" % (round(r * 255), round(g * 255), round(b * 255))


def _passes(token, color, tokens):
    return all(_ratio(color, tokens[bg]) >= need for bg, need in NEEDS[token])


def _suggest(token, mode, tokens):
    """The nearest colour of the token's hue and saturation that passes its thresholds on `tokens`' backgrounds: lightness
    moves in 0.5% steps, towards the contrast first (darker in light mode, lighter in dark). None when nothing does."""
    hue, light, sat = hls(tokens[token])
    toward = (-1, 1) if mode == "light" else (1, -1)
    for k in range(1, 201):
        for sign in toward:
            c = _hex(hue, light + sign * k * 0.005, sat)
            if _passes(token, c, tokens):
                return c
    return None


def theme_weak(theme):
    """The tokens of a theme that are under their contrast threshold, one entry per mode and token:
    [{mode, token, ratio, need, suggest}] (ratio: the lowest of its pairs, cut to two decimals so it never shows
    a passing number for a failing pair)."""
    out = []
    for mode in ("light", "dark"):
        tokens = theme[mode]
        for tok, pairs in NEEDS.items():
            ratio = min(_ratio(tokens[tok], tokens[bg]) for bg, _ in pairs)
            if not _passes(tok, tokens[tok], tokens):
                out.append({"mode": mode, "token": tok, "ratio": math.floor(ratio * 100) / 100,
                            "need": max(n for _, n in pairs), "suggest": _suggest(tok, mode, tokens)})
    return out


def _weak_text(weak):
    return "; ".join("%s.%s %.2f < %s (suggest %s)" % (w["mode"], w["token"], w["ratio"], w["need"], w["suggest"]) for w in weak)


def derive_dark(light):
    """The dark side of a theme that brought none: the neutral dark bg, surface, text, muted, border; the product's
    accent, ok, warn, crit lightened in 2% HSL steps until they pass their threshold on the dark surface."""
    dark = dict(NEUTRAL["dark"])
    for tok in ("accent", "ok", "warn", "crit"):
        hue, lt, sat = hls(light[tok])
        c = light[tok]
        for _ in range(50):
            if _passes(tok, c, dark):
                break
            lt = min(1.0, lt + 0.02)
            c = _hex(hue, lt, sat)
        dark[tok] = c
    return dark


def _read_tokens(path):
    """One token file -> a candidate (without `weak`). Bad on anything that is not clean."""
    raw = _read_json(path, "tokens")
    if not isinstance(raw, dict):
        raise Bad("tokens %s: not a mapping" % path)
    for k in raw:
        if k not in TOKEN_FILE_KEYS:
            raise Bad("tokens %s: unknown key '%s'" % (path, k))
    product = raw.get("product")
    if not isinstance(product, str) or not PRODUCT.match(product):
        raise Bad("tokens %s: product must be an id like 'zorg' (lowercase letters, digits, '-')" % path)
    if product == NEUTRAL["id"]:
        raise Bad("tokens %s: the product id 'neutral' is the built-in theme's" % path)
    top = [k for k in TOKENS if k in raw]
    if "light" in raw and top:
        raise Bad("tokens %s: give the tokens either in 'light' or at the top level, not both (%s)" % (path, ", ".join(top)))
    sides = {}
    for side, src in (("light", raw.get("light") if "light" in raw else {k: raw[k] for k in top}), ("dark", raw.get("dark"))):
        if side == "dark" and "dark" not in raw:
            continue
        if not isinstance(src, dict):
            raise Bad("tokens %s: %s must be a mapping of the nine tokens" % (path, side))
        for k in src:
            if k not in TOKENS:
                raise Bad("tokens %s: %s has an unknown token '%s'" % (path, side, k))
        for k in TOKENS:
            if k not in src:
                raise Bad("tokens %s: %s.%s is missing" % (path, side, k))
            if not isinstance(src[k], str) or not COLOR.match(src[k]):
                raise Bad("tokens %s: %s.%s must be #rrggbb" % (path, side, k))
        sides[side] = {k: src[k].lower() for k in TOKENS}
    font, radius = raw.get("font", NEUTRAL["font"]), raw.get("radius", NEUTRAL["radius"])
    if not isinstance(font, str) or (font != "" and font not in FONTS):
        raise Bad("tokens %s: font must be \"\" or one of: %s" % (path, ", ".join(FONTS)))
    if isinstance(radius, bool) or not isinstance(radius, int) or not 0 <= radius <= 24:
        raise Bad("tokens %s: radius must be a whole number 0-24" % path)
    return {"v": 1, "id": product, "product": product, "light": sides["light"],
            "dark": sides.get("dark") or derive_dark(sides["light"]), "font": font, "radius": radius}


def theme_candidates(token_files):
    """One candidate per token file, in the order given, and always `neutral` last:
    [{v, id, product, light, dark, font, radius, weak}]. Bad on a file that does not pass."""
    out, seen = [], set()
    for path in token_files:
        c = _read_tokens(path)
        if c["id"] in seen:
            raise Bad("tokens %s: the product '%s' is given twice" % (path, c["id"]))
        seen.add(c["id"])
        out.append(c)
    out.append(dict(copy.deepcopy(NEUTRAL), product=NEUTRAL["id"]))
    for c in out:
        c["weak"] = theme_weak(c)
    return out


def strip_people(data, label):
    """`data` without the keys that name a person (any depth, any case) -> (clean copy, ['label: key.path', …])."""
    dropped = []

    def walk(node, path):
        if isinstance(node, dict):
            out = {}
            for k, v in node.items():
                if isinstance(k, str) and k.lower() in PEOPLE_KEYS:
                    dropped.append("%s: %s" % (label, ".".join(path + [k])))
                else:
                    out[k] = walk(v, path + [k])
            return out
        if isinstance(node, list):
            return [walk(v, path + [str(i)]) for i, v in enumerate(node)]
        return node
    return walk(data, []), dropped


def _size(doc):
    return len(json.dumps(doc, ensure_ascii=False).encode("utf-8"))


def _path_safe(made):
    return re.sub(r"[^A-Za-z0-9._-]", "-", made)


def _build(sections, products, theme, made, connectors=None):
    """-> (documents {path: doc}, over [{path, bytes}], dropped [text]). Bad before anything is built on a wrong id."""
    if not isinstance(made, str) or not made.strip():
        raise Bad("made is missing")
    ids = set()
    for p in products:
        if not isinstance(p.get("id"), str) or not PRODUCT.match(p["id"]):
            raise Bad("product id '%s' must match %s" % (p.get("id"), PRODUCT.pattern))
        if p["id"] in ids:
            raise Bad("product '%s' is given twice" % p["id"])
        ids.add(p["id"])
        label = p.get("label")
        if not isinstance(label, str) or not label.strip() or ":" in label or len(label) > LABEL_MAX:
            raise Bad("product '%s': label must be 1-%d characters, no colon" % (p["id"], LABEL_MAX))
        if p.get("color") is not None and not (isinstance(p["color"], str) and COLOR.match(p["color"])):
            raise Bad("product '%s': color must be #rrggbb" % p["id"])
    docs, over, dropped, written = {}, [], [], {}
    seen = set()
    for name, product, data in sections:
        if not isinstance(name, str) or not SECTION.match(name):
            raise Bad("section name '%s' must match %s" % (name, SECTION.pattern))
        if product not in ids:
            raise Bad("section '%s': product '%s' is not one of the products" % (name, product))
        did = "%s--%s" % (name, product)
        if len(did.encode("utf-8")) > SEGMENT_MAX:
            raise Bad("section '%s': the document id is longer than %d bytes" % (did, SEGMENT_MAX))
        if did in seen:
            raise Bad("section '%s' is given twice" % did)
        seen.add(did)
        clean, drop = strip_people(data, did)
        dropped += drop
        doc = {"v": 1, "product": product, "section": name, "made": made, "data": clean}
        if _size(doc) > DOC_MAX:
            over.append({"path": "snapshot/" + did, "bytes": _size(doc)})
            continue
        docs["snapshot/" + did] = doc
        written[did] = made
    meta = {"v": 1, "made": made,
            "products": [{"id": p["id"], "label": p["label"], "color": p.get("color")} for p in products],
            "thresholds": dict(THRESHOLDS), "sections": written}
    if connectors:
        meta["connectors"] = {role: dict(b) for role, b in connectors.items()}
    docs["snapshot/meta"] = meta
    if theme is not None:
        errs = check_theme(theme)
        if errs:
            raise Bad("; ".join(errs))
        weak = theme_weak(theme)
        if weak:
            raise Bad("theme under the contrast threshold: " + _weak_text(weak))
        docs["snapshot/theme"] = theme
    run_id = _path_safe(made)
    if len(run_id.encode("utf-8")) > SEGMENT_MAX:
        raise Bad("made is longer than %d bytes" % SEGMENT_MAX)
    docs["runs/" + run_id] = {"at": made, "sections": sorted(written), "ok": not over}
    for path, doc in docs.items():
        if _size(doc) > DOC_MAX:
            raise Bad("document %s is over %d KiB" % (path, DOC_MAX // 1024))
    return docs, over, dropped


def build_snapshot(sections, products, theme, made, connectors=None):
    """The database documents of one snapshot: {path: document}. `sections` = [(name, product id, data)], `products` =
    [{id, label, color|None}]. A section over 256 KiB is left out (and out of meta.sections); people's keys are dropped."""
    return _build(sections, products, theme, made, connectors)[0]


def _now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_product(spec):
    """`ID:LABEL[:#rrggbb]` -> {id, label, color}."""
    parts = (spec or "").split(":")
    if len(parts) not in (2, 3) or not parts[0] or not parts[1]:
        raise Bad("product '%s': expected ID:LABEL[:#rrggbb] (a label has no colon)" % spec)
    color = parts[2] if len(parts) == 3 else None
    if color is not None and not COLOR.match(color):
        raise Bad("product '%s': color must be #rrggbb" % parts[0])
    return {"id": parts[0], "label": parts[1], "color": color}


def parse_section(spec):
    """`NAME:PRODUCT:FILE` -> (name, product, data)."""
    name, _, rest = (spec or "").partition(":")
    product, _, path = rest.partition(":")
    if not name or not product or not path:
        raise Bad("section '%s': expected NAME:PRODUCT:FILE" % spec)
    return name, product, _read_json(path, "section %s" % name)


def _read_json(path, what):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        raise Bad("%s: the file %s does not read as JSON (%s)" % (what, path, e))


def cmd_snapshot(a):
    doc = load_profiles(a.profiles)
    prof = (doc.get("profiles") or {}).get(a.profile)
    if prof is None:
        raise Bad("no profile '%s' (there are: %s)" % (a.profile, ", ".join(sorted(doc.get("profiles") or {}))))
    roles = [c.get("role") for c in prof.get("connectors") or [] if isinstance(c, dict)]
    connectors = {}
    for spec in a.connector:
        parts = spec.split(":")
        if len(parts) != 3 or not all(x.strip() for x in parts):
            raise Bad("connector '%s': expected ROLE:SERVER:TOOL" % spec)
        if parts[0] not in roles:
            raise Bad("connector role '%s' is not declared by profile '%s' (it declares: %s)" % (parts[0], a.profile, ", ".join(roles) or "none"))
        connectors[parts[0]] = {"server": parts[1].strip(), "tool": parts[2].strip()}
    products = [parse_product(x) for x in a.product]
    sections = [parse_section(x) for x in a.section]
    theme = _read_json(a.theme, "theme") if a.theme else None
    made = a.at or _now()
    if a.at and not re.fullmatch(r"\d{4}-\d\d-\d\dT[0-9:.]+(Z|[+-]\d\d:\d\d)?", a.at):
        raise Bad("--at must be an ISO time, e.g. 2026-11-26T10:00:00Z")
    docs, over, dropped = _build(sections, products, theme, made, connectors)
    out = []
    try:
        for path, d in docs.items():
            target = os.path.join(a.out, path + ".json")
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "w", encoding="utf-8", newline="") as f:
                json.dump(d, f, ensure_ascii=False)
            out.append({"path": path, "bytes": os.path.getsize(target)})
    except OSError as e:
        raise Bad("the snapshot does not write: %s" % e)
    result(ok=not over, docs=out, over=over, dropped=dropped, made=made)
    return 1 if over else 0


def cmd_theme(a):
    cands = theme_candidates(a.tokens)
    if a.pick is None:
        data = {"candidates": cands}
    else:
        c = next((x for x in cands if x["id"] == a.pick), None)
        if c is None:
            raise Bad("no theme '%s' (there are: %s)" % (a.pick, ", ".join(x["id"] for x in cands)))
        if c["weak"]:
            raise Bad("the theme '%s' has tokens under the contrast threshold, replace them first: %s" % (a.pick, _weak_text(c["weak"])))
        data = {k: c[k] for k in THEME_KEYS}
        errs = check_theme(data)
        if errs:
            raise Bad("; ".join(errs))
    try:
        with open(a.out, "w", encoding="utf-8", newline="") as f:
            json.dump(data, f, ensure_ascii=False)
    except OSError as e:
        raise Bad("the theme does not write: %s" % e)
    result(ok=True, out=a.out, candidates=cands, **({"picked": a.pick} if a.pick is not None else {}))
    return 0


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
    n = sub.add_parser("snapshot")
    n.add_argument("--profile", required=True)
    n.add_argument("--section", action="append", default=[], metavar="NAME:PRODUCT:FILE")
    n.add_argument("--product", action="append", default=[], metavar="ID:LABEL[:#rrggbb]")
    n.add_argument("--connector", action="append", default=[], metavar="ROLE:SERVER:TOOL")
    n.add_argument("--theme", default=None)
    n.add_argument("--at", default=None)
    n.add_argument("--out", required=True)
    n.add_argument("--profiles", default=None)
    n.set_defaults(fn=cmd_snapshot)
    t = sub.add_parser("theme")
    t.add_argument("--tokens", action="append", default=[], metavar="FILE")
    t.add_argument("--pick", default=None, metavar="ID")
    t.add_argument("--out", required=True)
    t.set_defaults(fn=cmd_theme)
    a = ap.parse_args(argv)
    try:
        return a.fn(a)
    except Bad as e:
        result(ok=False, error=str(e))
        return 1


if __name__ == "__main__":
    sys.exit(main())
