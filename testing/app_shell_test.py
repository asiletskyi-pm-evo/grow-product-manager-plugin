#!/usr/bin/env python3
"""TC-app-4130 — scripts/app_shell.py, the app profiles and their check (v4.13.0 «Застосунки»).

The repo's references/app-profiles.yaml is checked clean; hand-made profiles (fictional product Zorg) show that
`level: full`, `full-access` and `commands` are refused with «arrives in v4.13.1», that every unknown key is named by its
own error, and that a URL, e-mail, UUID or Jira key is refused while `<placeholder>` values pass. Stdlib only; run from
the repo root. `wrap` turns a Zorg page into an app (manifest, shell, profile); the browser steps (node + global
Playwright, as in journey_page_edit_test.py) are skipped with a line when Playwright is absent:

  env -u GROW_PM_CONTEXT_PATH -u GROW_PM_PROVIDER_PATHS python3 testing/app_shell_test.py
"""
import copy, json, os, re, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "app_shell.py")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import app_shell as sh  # noqa: E402

fails = 0


def check(name, cond, detail=""):
    global fails
    fails += not cond
    print(("✅" if cond else "❌"), name, ("" if cond else "-> " + str(detail)[:900]))


def run(*args):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GROW_PM_")}
    p = subprocess.run([sys.executable, SCRIPT] + list(args), capture_output=True, text=True, env=env)
    res = {}
    for line in p.stdout.splitlines():
        if line.startswith("APP_RESULT "):
            res = json.loads(line[len("APP_RESULT "):])
    return p.returncode, p.stdout + p.stderr, res


def has(errs, *needles):
    return any(all(n in e for n in needles) for e in errs)


BASE = {"level": "app", "title": {"uk": "Zorg", "en": "Zorg"}, "icon": {"glyph": "chart"},
        "permissions": ["notifications", "menu-bar"],
        "modules": [{"id": "a", "block": "table", "source": "a", "home": True, "title": {"uk": "А", "en": "A"}},
                    {"id": "b", "block": "list", "source": "b", "title": {"uk": "Б", "en": "B"}}],
        "menu": ["a", "b", {"action": "edit", "accel": "CmdOrCtrl+E"}, {"action": "open-in-claude"}],
        "connectors": [{"role": "issue-status", "needs": "<jira_project>"}], "commands": []}


def prof(**over):
    p = copy.deepcopy(BASE)
    p.update(over)
    return p


# test_repo_profiles_clean
rc, out, res = run("check")
check("1.1 check on the repo is clean", rc == 0 and res == {"ok": True, "errors": []}, out)
check("1.2 the base profile of this test is clean", sh.check_profile("zorg", BASE) == [], sh.check_profile("zorg", BASE))
rc, out, res = run("schema")
check("1.3 schema prints the constants", res.get("levels") == ["page", "app"] and res.get("later") == list(sh.LATER)
      and res.get("blocks") == list(sh.BLOCKS), out)
doc = sh.load_profiles()
cjm = doc["profiles"]["cjm"]
check("1.4 the reader reads flow mappings and lists", cjm["title"] == {"uk": "CJM", "en": "CJM"} and cjm["menu"][3] ==
      {"action": "edit", "accel": "CmdOrCtrl+E"} and cjm["modules"][0]["home"] is True and cjm["commands"] == []
      and doc["profiles"]["pm-os"]["modules"] == [], cjm)
with tempfile.TemporaryDirectory() as d:
    bad = os.path.join(d, "p.yaml")
    with open(bad, "w") as f:
        f.write("version: 1\nprofiles:\n  x:\n    level: [app\n")
    rc, out, res = run("check", "--profiles", bad)
    check("1.5 an unreadable file is a refusal, not a crash", rc == 1 and res.get("ok") is False and "Traceback" not in out, out)
    with open(bad, "w") as f:
        f.write("version: 1\nprofiles:\n  zorg:\n    level: full\n    title: {uk: \"Z\", en: \"Z\"}\n    icon: {glyph: os}\n")
    rc, out, res = run("check", "--profiles", bad)
    check("1.6 check --profiles PATH reads that file", rc == 1 and has(res.get("errors", []), "level full"), out)

# test_later_refused
for label, p in (("level full", prof(level="full")),
                 ("full-access", prof(permissions=["notifications", "full-access"])),
                 ("commands", prof(commands=["x"]))):
    errs = sh.check_profile("zorg", p)
    check("2 %s is refused with 'arrives in v4.13.1'" % label, has(errs, "arrives in v4.13.1"), errs)
for perm in ("shortcuts", "overlay"):
    errs = sh.check_profile("zorg", prof(permissions=[perm]))
    check("2 permission %s is refused as unknown for now" % perm, has(errs, perm, "unknown for now"), errs)

# test_unknown_keys
cases = (
    ("unknown block", prof(modules=[dict(BASE["modules"][0], block="radar")]), "unknown block 'radar'"),
    ("unknown glyph", prof(icon={"glyph": "rocket"}), "unknown glyph 'rocket'"),
    ("unknown permission", prof(permissions=["camera"]), "unknown permission 'camera'"),
    ("menu entry not a module", prof(menu=["ghost"]), "menu entry 'ghost'"),
    ("menu action unknown", prof(menu=[{"action": "delete"}]), "menu action 'delete'"),
    ("duplicate module id", prof(modules=[BASE["modules"][0], dict(BASE["modules"][1], id="a")]), "duplicate module id 'a'"),
    ("two homes", prof(modules=[BASE["modules"][0], dict(BASE["modules"][1], home=True)]), "more than one home"),
    ("unknown level", prof(level="tablet"), "unknown level 'tablet'"),
    ("title without en", prof(title={"uk": "Z"}), "title needs both uk and en"),
    ("unknown profile key", prof(skin="dark"), "unknown key 'skin'"),
)
for label, p, needle in cases:
    errs = sh.check_profile("zorg", p)
    check("3 %s is named" % label, has(errs, needle), errs)
errs = sh.check_profile("zorg", prof(icon={"glyph": "x"}, permissions=["camera"], menu=["ghost"]))
check("3 several defects are several errors", len(errs) == 3, errs)

# test_no_values
for label, text in (("URL", "https://zorg.example/board"), ("e-mail", "ana@zorg.example"),
                    ("UUID", "123e4567-e89b-12d3-a456-426614174000"), ("Jira key", "ABC-123"),
                    ("artifact link", "claude.ai/artifact/abc")):
    errs = sh.check_profile("zorg", prof(connectors=[{"role": "issue-status", "needs": text}]))
    check("4 %s is refused as 'value in a template'" % label, has(errs, "value in a template"), errs)
errs = sh.check_profile("zorg", prof(connectors=[{"role": "issue-status", "needs": "<jira_project>"},
                                                  {"role": "funnel-numbers", "needs": "<dashboard_id>"},
                                                  {"role": "x", "needs": "<product>"}]))
check("4 placeholders pass", errs == [], errs)
errs = sh.check_profile("zorg", prof(title={"uk": "ABC-123", "en": "Z"}))
check("4 a value in the title is refused too", has(errs, "value in a template"), errs)

# fix round 1: a value hidden in angle brackets, and a scalar where a list belongs
for label, text in (("bracketed URL", "<https://zorg.example/x>"), ("bracketed Jira key", "<ABC-123>"),
                    ("bracketed e-mail", "<a@b.co>"), ("bracketed UUID", "<123e4567-e89b-12d3-a456-426614174000>")):
    errs = sh.check_profile("zorg", prof(connectors=[{"role": "issue-status", "needs": text}]))
    check("4 %s is not a placeholder" % label, has(errs, "value in a template"), errs)
for key in ("permissions", "modules", "menu"):
    errs = sh.check_profile("zorg", prof(**{key: "full-access"}))
    check("5 %s as a scalar is refused" % key, has(errs, key, "must be a list"), errs)
errs = sh.check_profile("zorg", prof(permissions="full-access", modules="x", menu="y"))
check("5 a scalar full-access cannot bypass the gate", len(errs) >= 3, errs)

# ---- Task 2: wrap -----------------------------------------------------------------------------------------------------
ZORG = ('<!doctype html><html lang="uk"><head><meta charset="utf-8"><title>Zorg</title></head>'
        '<body class="z"><h1>Zorg карта</h1><p id="keep">вміст сторінки</p></body></html>')
SHELL_JS = open(os.path.join(ROOT, "scripts", "app_shell", "shell.js"), encoding="utf-8").read() \
    if os.path.exists(os.path.join(ROOT, "scripts", "app_shell", "shell.js")) else ""
CJM_CAPS = {"desktop": {},
            "db": {"rules": [{"path": "", "read": "view", "write": "admin"},
                             {"path": "snapshot", "read": "view", "write": "owner"},
                             {"path": "config", "read": "view", "write": "owner"},
                             {"path": "runs", "read": "view", "write": "owner"}]},
            "user": {"scopes": ["profile"]}}


def wrap(d, page, *extra, name="cjm", out="out.html"):
    src = os.path.join(d, "in.html")
    with open(src, "w", encoding="utf-8") as f:
        f.write(page)
    o = os.path.join(d, out)
    rc, text, res = run("wrap", "--page", src, "--profile", name, "--out", o, *extra)
    return rc, text, res, o


def body_of(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


with tempfile.TemporaryDirectory() as d:
    # test_wrap_manifest
    rc, text, res, o = wrap(d, ZORG)
    html = body_of(o) if os.path.exists(o) else ""
    mans = re.findall(r'<script type="application/json" id="claude-artifacts-manifest">(.*?)</script>', html, re.S)
    check("6.1 wrap succeeds; the manifest is in <head>, exactly one, permissions as the profile's in order",
          rc == 0 and res.get("ok") is True and len(mans) == 1 and json.loads(mans[0]) == {"permissions": cjm["permissions"]}
          and html.index("claude-artifacts-manifest") < html.index("</head>"), (text[-300:], mans))
    check("6.2 the meta and the shell header", '<meta name="grow-pm-app" content="cjm;shell=1">' in html
          and '<header class="gpm-shell">' in html and '<main class="gpm-modules" hidden></main>' in html, html[:600])
    check("6.3 the page's own body sits in .gpm-page, after the header and the empty modules",
          re.search(r'<body class="z"><header class="gpm-shell">.*?</header><main class="gpm-modules" hidden></main>'
                    r'<div class="gpm-page"><h1>Zorg карта</h1><p id="keep">вміст сторінки</p></div>', html, re.S) is not None, html)
    check("6.4 the result line", res.get("out") == o and res.get("bytes") == len(html.encode("utf-8"))
          and res.get("profile") == "cjm" and res.get("shell") == 1 and res.get("permissions") == cjm["permissions"]
          and res.get("capabilities") == CJM_CAPS, res)
    pj = re.findall(r'<script id="gpm-profile" type="application/json">(.*?)</script>', html, re.S)
    prof_in = json.loads(pj[0]) if pj else {}
    check("6.5 gpm-profile: the profile without the needs of its connectors, plus name, lang, shell; safe in <script>",
          len(pj) == 1 and prof_in.get("name") == "cjm" and prof_in.get("lang") == "uk" and prof_in.get("shell") == 1
          and prof_in.get("connectors") == [{"role": "issue-status"}, {"role": "funnel-numbers"}]
          and "<jira_project>" not in pj[0] and "<" not in pj[0] and ">" not in pj[0] and "&" not in pj[0]
          and prof_in.get("title") == cjm["title"], pj)
    rc2, text2, res2, _ = wrap(d, html, out="again.html")
    check("6.6 a second wrap of the result is refused: already an app; nothing written", rc2 == 1 and res2.get("ok") is False
          and "already an app" in res2.get("error", "") and not os.path.exists(os.path.join(d, "again.html")), text2)
    rc3, text3, res3, o3 = wrap(d, ZORG, "--lang", "en", out="en.html")
    en = body_of(o3)
    check("6.7 --lang en: the profile carries lang en", '"lang": "en"' in en and '"name": "cjm"' in en, en[-400:])

    # test_wrap_bytes_fixed
    check("7.1 shell.js and shell.css exist, shell.js has no script-closing text and no note data",
          len(SHELL_JS) > 500 and "</script" not in SHELL_JS.lower(), len(SHELL_JS))
    css = open(os.path.join(ROOT, "scripts", "app_shell", "shell.css"), encoding="utf-8").read() \
        if os.path.exists(os.path.join(ROOT, "scripts", "app_shell", "shell.css")) else ""
    check("7.2 both files are inserted byte for byte; no <script src>", SHELL_JS in html and css and css in html
          and not re.search(r"<script\b[^>]*\bsrc\s*=", html, re.I), len(css))
    rc4, _, _, o4 = wrap(d, ZORG, out="out2.html")
    check("7.3 two runs give the same bytes", body_of(o4) == html)
    check("7.4 shell.js: one IIFE, parts in a registry each in its own try/catch, a shared busy()",
          SHELL_JS.lstrip().startswith("(function") and "busy" in SHELL_JS and "try" in SHELL_JS and "Виконується…" in SHELL_JS
          and "Готово" in SHELL_JS and "--gpm-" in css, "")

    # test_capabilities_rules
    check("8.1 capabilities(cjm) is exactly the rules; no mcp key without a connector",
          sh.capabilities(cjm, []) == CJM_CAPS and "mcp" not in sh.capabilities(cjm, []))
    rc, text, res, _ = wrap(d, ZORG, "--connector", "Zorg Tracker:get_issue,list_issues", "--connector", "Zorg Board:read", out="c.html")
    check("8.2 --connector SERVER:TOOL[,TOOL] (repeatable) goes to capabilities.mcp and nowhere into the page",
          res.get("capabilities", {}).get("mcp") == {"servers": [{"server": "Zorg Tracker", "tools": ["get_issue", "list_issues"]},
                                                                   {"server": "Zorg Board", "tools": ["read"]}]}
          and "Zorg Tracker" not in body_of(os.path.join(d, "c.html")) and "get_issue" not in body_of(os.path.join(d, "c.html")), res)
    for bad in ("nocolon", ":tool", "server:", "s:a,,b"):
        rc, text, res, _ = wrap(d, ZORG, "--connector", bad, out="bad.html")
        check("8.3 a malformed connector '%s' is refused, no file" % bad, rc == 1 and res.get("ok") is False
              and not os.path.exists(os.path.join(d, "bad.html")), text)

    # test_wrap_refuses_foreign_script
    refusals = (
        ("a <script src>", ZORG.replace("</head>", '<script src="https://zorg.example/x.js"></script></head>'), "script"),
        ("an existing manifest", ZORG.replace("</head>", '<script type="application/json" id="claude-artifacts-manifest">{}</script></head>'), "already an app"),
        ("the grow-pm-app meta", ZORG.replace("</head>", '<meta name="grow-pm-app" content="x;shell=1"></head>'), "already an app"),
        ("no <head>", "<html><body>x</body></html>", "head"),
        ("no <body>", "<html><head></head></html>", "body"),
    )
    for label, page, needle in refusals:
        rc, text, res, o = wrap(d, page, out="r.html")
        check("9 %s is refused (%s); no file" % (label, needle), rc == 1 and res.get("ok") is False
              and needle in res.get("error", "") and not os.path.exists(o), text)
    rc, text, res, o = wrap(d, ZORG, name="nope", out="r.html")
    check("9 an unknown profile is refused; no file", rc == 1 and not os.path.exists(o), text)
    bad_prof = os.path.join(d, "bad.yaml")
    with open(bad_prof, "w") as f:
        f.write("version: 1\nprofiles:\n  zorg:\n    level: full\n    title: {uk: \"Z\", en: \"Z\"}\n    icon: {glyph: os}\n")
    src = os.path.join(d, "in.html")
    rc, text, res = run("wrap", "--page", src, "--profile", "zorg", "--profiles", bad_prof, "--out", os.path.join(d, "r.html"))
    check("9 a profile that fails check_profile is refused with its errors; no file", rc == 1 and "arrives in v4.13.1" in res.get("error", "")
          and not os.path.exists(os.path.join(d, "r.html")), text)
    nasty = dict(BASE, title={"uk": "</script><b>&", "en": "Z"})
    check("9 a profile title with markup is escaped in the page", "</script><b>" not in sh.wrap_page(ZORG, "zorg", nasty, "uk").split("<body", 1)[1].split("<script", 1)[0], "")

    # ---- the browser steps ---------------------------------------------------------------------------------------------
    npm = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip() if subprocess.run(
        ["which", "npm"], capture_output=True).returncode == 0 else ""
    try:
        subprocess.run(["node", "-e", "require('playwright')"], check=True, capture_output=True, timeout=30,
                       env=dict(os.environ, NODE_PATH=npm))
        have_pw = True
    except Exception:
        have_pw = False
    if not have_pw:
        print("⏭  10.x the browser pass — skipped: no playwright")
    else:
        rc, _, _, pg = wrap(d, ZORG, out="app.html")
        js = os.path.join(d, "pw.js")
        with open(js, "w") as f:
            f.write(r"""
const { chromium } = require('playwright');
const fakeDesktop = `
  let state = window.__state || 'available'; window.__calls = [];
  window.__release = null;
  const desktop = {install: {
    state: async () => state,
    request: () => new Promise((res, rej) => { window.__calls.push('request'); window.__release = (v, err) => err ? rej(new Error(err)) : res(v); })}};
  window.claude = {use: async (n) => (n === 'desktop' ? (window.__noDesktop ? null : desktop) : null)};`;
(async () => {
  const mode = process.argv[3];
  const b = await chromium.launch();
  const out = {};
  async function open(init, viewport) {
    const p = await b.newPage({viewport: viewport || {width: 1000, height: 700}}); const errs = [];
    p.on('pageerror', e => errs.push(String(e))); p.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
    await p.addInitScript(init); await p.goto('file://' + process.argv[2]); await p.waitForTimeout(300);
    return [p, errs];
  }
  // available -> visible; click -> at once Виконується…, then Готово
  let [p, errs] = await open(fakeDesktop);
  out.visible = await p.isVisible('.gpm-install');
  out.title = await p.textContent('.gpm-shell .gpm-title');
  out.label0 = await p.textContent('.gpm-install');
  await p.click('.gpm-install');
  out.busy = await p.textContent('.gpm-install'); out.disabled = await p.isDisabled('.gpm-install');
  out.callsDuring = await p.evaluate(() => window.__calls.length);
  await p.evaluate(() => window.__release('installed')); await p.waitForTimeout(150);
  out.done = await p.textContent('.gpm-state');
  out.hasPage = await p.isVisible('.gpm-page #keep'); out.modulesHidden = await p.isHidden('.gpm-modules');
  out.errs1 = errs; await p.close();
  // refusal in words
  [p, errs] = await open(fakeDesktop);
  await p.click('.gpm-install'); await p.evaluate(() => window.__release('cancelled')); await p.waitForTimeout(150);
  out.cancelled = await p.textContent('.gpm-state'); out.reenabled = await p.isEnabled('.gpm-install');
  await p.click('.gpm-install'); await p.evaluate(() => window.__release(null, 'EPERM')); await p.waitForTimeout(150);
  out.rejected = await p.textContent('.gpm-state'); await p.close();
  // no request without a click
  [p, errs] = await open(fakeDesktop); out.callsIdle = await p.evaluate(() => window.__calls.length); await p.close();
  // installed / unavailable -> no button
  [p, errs] = await open("window.__state='installed';" + fakeDesktop); out.installedBtn = await p.$$eval('.gpm-install', e => e.length); out.errs2 = errs; await p.close();
  [p, errs] = await open("window.__state='unavailable';" + fakeDesktop); out.unavBtn = await p.$$eval('.gpm-install', e => e.length); await p.close();
  // state() throws -> silent
  [p, errs] = await open(fakeDesktop.replace("state: async () => state", "state: async () => { throw new Error('boom'); }"));
  out.throwBtn = await p.$$eval('.gpm-install', e => e.length); out.errs3 = errs; out.pageThrow = await p.isVisible('.gpm-page #keep'); await p.close();
  // no desktop (use -> null)
  [p, errs] = await open("window.__noDesktop = true;" + fakeDesktop);
  out.noDesk = {btn: await p.$$eval('.gpm-install', e => e.length), page: await p.isVisible('.gpm-page #keep'), errs, head: await p.isVisible('.gpm-shell')}; await p.close();
  // no window.claude at all (a plain browser)
  [p, errs] = await open('');
  out.plain = {btn: await p.$$eval('.gpm-install', e => e.length), page: await p.isVisible('.gpm-page #keep'), errs, title: await p.textContent('.gpm-title')}; await p.close();
  // phone width: no horizontal scroll, the button is inside the screen
  [p, errs] = await open(fakeDesktop, {width: 360, height: 640});
  out.phone = await p.evaluate(() => ({sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth,
    right: document.querySelector('.gpm-install').getBoundingClientRect().right, h: document.querySelector('.gpm-shell').getBoundingClientRect().height}));
  await p.close();

  // ---- Task 3: the data channel — a fake database with a collection listener
  const fakeDb = (docs, mode) => `
    window.__docs = ${JSON.stringify(docs)}; window.__subs = []; window.__marker = 'same-page';
    const qs = () => ({docs: Object.keys(window.__docs).sort().map(id => ({id, exists: true, data: () => window.__docs[id]})),
                       size: Object.keys(window.__docs).length, empty: false, docChanges: () => []});
    window.__push = (id, data) => { window.__docs[id] = data; window.__subs.forEach(f => f(qs())); };
    const db = {collection: (n) => ({onSnapshot: (next, err) => {
      if ('${mode}' === 'throws') { throw new Error('boom'); }
      if ('${mode}' === 'error') { setTimeout(() => err && err({code: 'permission_denied'}), 0); return () => {}; }
      window.__subs.push(next); setTimeout(() => next(qs()), 0); return () => {}; }})};
    const _use = window.claude.use; window.claude.use = async (n) => (n === 'db' ? (${mode === 'nodb' ? 'null' : 'db'}) : _use(n));`;
  const META = {v: 1, made: '2026-11-26T10:00:00Z', products: [], thresholds: {warning: 0.1, critical: 0.25}, sections: {'portfolio--zorg': '2026-11-26T10:00:00Z'}};
  const SEC = (rows, made) => ({v: 1, product: 'zorg', section: 'portfolio', made, data: {columns: [], rows}});
  [p, errs] = await open(fakeDesktop + fakeDb({'meta': META, 'portfolio--zorg': SEC([{a: 1}, {a: 2}, {a: 3}], '2026-11-26T10:00:00Z'), 'theme': {v: 1}}, 'ok'));
  const read = () => p.evaluate(() => { const g = window.__gpm; const d = g && g.data;
    return {meta: d && d.meta && d.meta.made, rows: d && d.sections && d.sections['portfolio--zorg'] && d.sections['portfolio--zorg'].data.rows.length,
            keys: d && Object.keys(d.sections).sort(), fresh: (document.querySelector('.gpm-fresh') || {}).textContent || '',
            marker: window.__marker, ro: (() => { try { window.__gpm = 1; window.__gpm.data = 1; } catch (e) {} return !!(window.__gpm && window.__gpm.data); })()}; });
  out.live0 = await read();
  await p.evaluate(() => {
    window.__gotEvent = 0; window.__push('portfolio--zorg', {v: 1, product: 'zorg', section: 'portfolio', made: '2026-12-01T09:00:00Z', data: {columns: [], rows: [{a: 9}]}});
    window.__push('meta', {v: 1, made: '2026-12-01T09:00:00Z', products: [], thresholds: {warning: 0.1, critical: 0.25}, sections: {'portfolio--zorg': '2026-12-01T09:00:00Z'}}); });
  await p.waitForTimeout(150);
  out.live1 = await read(); out.liveErrs = errs; out.livePage = await p.isVisible('.gpm-page #keep'); await p.close();
  [p, errs] = await open('window.__en = 1;' + fakeDesktop + fakeDb({'meta': META}, 'ok'));
  out.liveNoSec = await read(); await p.close();
  // foreign input: nothing is trusted, nothing is thrown
  const evil = {'meta': {v: 1, made: '<img src=x onerror=window.__pwned=1>', products: 'x', sections: 5}, 'portfolio--zorg': 'a string', '../x--y': {data: {}},
                'theme': 'x', 'bad id--zorg': {v: 1, data: {}}, 'map.q--zorg': {v: 1, product: 7, section: null, made: {}, data: []}};
  [p, errs] = await open(fakeDesktop + fakeDb(evil, 'ok'));
  out.evil = {state: await read(), pwned: await p.evaluate(() => !!window.__pwned), imgs: await p.$$eval('.gpm-shell img', e => e.length), errs, page: await p.isVisible('.gpm-page #keep')}; await p.close();
  for (const mode of ['throws', 'error', 'nodb']) {
    [p, errs] = await open(fakeDesktop + fakeDb({'meta': META}, mode));
    out['db_' + mode] = {fresh: (await p.$$eval('.gpm-fresh', e => e.map(x => x.textContent).join(''))), errs, page: await p.isVisible('.gpm-page #keep'), install: await p.$$eval('.gpm-install', e => e.length)}; await p.close();
  }
  // a part that never settles does not hold the others back
  [p, errs] = await open(fakeDesktop.replace("state: async () => state", "state: () => new Promise(() => {})") + fakeDb({'meta': META}, 'ok'));
  out.hang = {fresh: (await p.$$eval('.gpm-fresh', e => e.map(x => x.textContent).join(''))), errs}; await p.close();
  [p, errs] = await open(fakeDesktop + fakeDb({'meta': META}, 'ok'), {width: 360, height: 640});
  out.livePhone = await p.evaluate(() => ({sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth})); await p.close();
  console.log(JSON.stringify(out)); await b.close();
})();""")
        pr = subprocess.run(["node", js, pg], capture_output=True, text=True, timeout=180, env=dict(os.environ, NODE_PATH=npm))
        try:
            br = json.loads(pr.stdout.strip().splitlines()[-1])
        except (ValueError, IndexError):
            br = {}
        err = pr.stderr[-400:]
        check("10.1 pw_install_button: state 'available' -> the button is visible, in the profile's language, titled", br.get("visible") is True
              and br.get("title") == "CJM" and br.get("label0") == "Встановити як застосунок", (br, err))
        check("10.2 a click: at once «Виконується…» and disabled, one request; then «Готово» next to it",
              br.get("busy") == "Виконується…" and br.get("disabled") is True and br.get("callsDuring") == 1
              and br.get("done") == "Готово" and not br.get("errs1"), br)
        check("10.3 the page's own content is on screen and the modules area stays hidden", br.get("hasPage") is True and br.get("modulesHidden") is True, br)
        check("10.4 a refusal is told in words and the button works again", "Скасовано" in (br.get("cancelled") or "")
              and br.get("reenabled") is True and (br.get("rejected") or "") not in ("", "Готово"), br)
        check("10.5 install.request() is never called without a click", br.get("callsIdle") == 0, br)
        check("10.6 'installed' and 'unavailable' -> no button; a throwing state() -> no button, no error, page intact",
              br.get("installedBtn") == 0 and br.get("unavBtn") == 0 and br.get("throwBtn") == 0
              and not br.get("errs2") and not br.get("errs3") and br.get("pageThrow") is True, br)
        nd, pl = br.get("noDesk") or {}, br.get("plain") or {}
        check("10.7 pw_no_desktop: use('desktop') = null -> no error, no button, the page is there",
              nd.get("btn") == 0 and nd.get("page") is True and nd.get("errs") == [] and nd.get("head") is True, nd)
        check("10.8 no window.claude at all (a browser): no error, no button, the page is there, the title is drawn",
              pl.get("btn") == 0 and pl.get("page") is True and pl.get("errs") == [] and pl.get("title") == "CJM", pl)
        ph = br.get("phone") or {}
        check("10.9 at phone width: no horizontal scroll, the button is on screen, the header is small",
              ph and ph.get("sw") <= ph.get("cw") and ph.get("right") <= ph.get("cw") and ph.get("h") < 120, ph)

        l0, l1 = br.get("live0") or {}, br.get("live1") or {}
        check("10.10 pw_live_update: the data the shell holds is read from the database (meta + section), the freshness line shows the date",
              l0.get("meta") == "2026-11-26T10:00:00Z" and l0.get("rows") == 3 and l0.get("keys") == ["portfolio--zorg"]
              and l0.get("fresh") == "дані від 26.11.2026", l0)
        check("10.11 pw_live_update: a new snapshot/portfolio--zorg and a new snapshot/meta change the held data and the line, no reload, no error",
              l1.get("meta") == "2026-12-01T09:00:00Z" and l1.get("rows") == 1 and l1.get("fresh") == "дані від 01.12.2026"
              and l1.get("marker") == "same-page" and br.get("liveErrs") == [] and br.get("livePage") is True, (l1, br.get("liveErrs")))
        check("10.12 window.__gpm.data is read-only for the page's own code", l0.get("ro") is True, l0)
        check("10.13 a database with meta only: no section, the line is still shown", (br.get("liveNoSec") or {}).get("keys") == []
              and (br.get("liveNoSec") or {}).get("fresh") == "дані від 26.11.2026", br.get("liveNoSec"))
        ev = br.get("evil") or {}
        check("10.14 foreign input: a malformed meta, section, id or theme gives an empty result, no error, nothing put into the page as HTML",
              ev.get("errs") == [] and ev.get("pwned") is False and ev.get("imgs") == 0 and (ev.get("state") or {}).get("fresh") == ""
              and (ev.get("state") or {}).get("keys") == [] and ev.get("page") is True, ev)
        for mode in ("throws", "error", "nodb"):
            dm = br.get("db_" + mode) or {}
            check("10.15 a database that %s: no error, no line, the page is there, the install button still works" % mode,
                  dm.get("errs") == [] and dm.get("fresh") == "" and dm.get("page") is True and dm.get("install") == 1, dm)
        check("10.16 a part that never settles (install.state) does not hold the data part back",
              (br.get("hang") or {}).get("fresh") == "дані від 26.11.2026" and (br.get("hang") or {}).get("errs") == [], br.get("hang"))
        lp = br.get("livePhone") or {}
        check("10.17 at phone width the freshness line adds no horizontal scroll", lp and lp.get("sw") <= lp.get("cw"), lp)

# ---- Task 3: the data channel (snapshot) --------------------------------------------------------------------------------
FIX = os.path.join(ROOT, "testing", "fixtures", "app")
PORT, MAP, THEME = (os.path.join(FIX, n) for n in ("zorg-portfolio.json", "zorg-map.json", "zorg-theme.json"))
MADE = "2026-11-26T10:00:00Z"
ZP = ["--product", "zorg:Zorg:#2f6fde", "--product", "zorg-pay:Zorg Pay"]


def snap(d, *args, out="snap"):
    o = os.path.join(d, out)
    rc, text, res = run("snapshot", "--profile", "cjm", "--out", o, "--at", MADE, *args)
    return rc, text, res, o


def jread(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as f:
        return json.load(f)


with tempfile.TemporaryDirectory() as d:
    # test_snapshot_paths
    rc, text, res, o = snap(d, *ZP, "--section", "portfolio:zorg:" + PORT, "--section", "portfolio:zorg-pay:" + PORT,
                            "--section", "map.first-order:zorg:" + MAP, "--section", "map.first-order:zorg-pay:" + MAP,
                            "--theme", THEME)
    paths = sorted(x.get("path") for x in res.get("docs", []))
    want = sorted(["snapshot/meta", "snapshot/theme", "runs/2026-11-26T10-00-00Z"] + ["snapshot/%s--%s" % (a, b) for a in
                  ("portfolio", "map.first-order") for b in ("zorg", "zorg-pay")])
    check("11.1 snapshot: 4 section documents + meta + theme + runs/<made>, exactly; ok, over empty", rc == 0
          and res.get("ok") is True and paths == want and res.get("over") == [], (text, paths))
    files = sorted(os.path.relpath(os.path.join(r, f), o) for r, _, fs in os.walk(o) for f in fs)
    check("11.2 one JSON file per document under DIR/<collection>/<id>.json, bytes as printed", files == sorted(
          x + ".json" for x in want) and all(os.path.getsize(os.path.join(o, x["path"] + ".json")) == x["bytes"]
                                            for x in res.get("docs", [])), files)
    meta = jread(o, "snapshot", "meta.json")
    check("11.3 meta: v, made, products with colour or null, thresholds, sections has all 4 with made", meta == {
          "v": 1, "made": MADE, "products": [{"id": "zorg", "label": "Zorg", "color": "#2f6fde"},
                                             {"id": "zorg-pay", "label": "Zorg Pay", "color": None}],
          "thresholds": {"warning": 0.10, "critical": 0.25},
          "sections": {"portfolio--zorg": MADE, "portfolio--zorg-pay": MADE, "map.first-order--zorg": MADE,
                       "map.first-order--zorg-pay": MADE}}, meta)
    sec = jread(o, "snapshot", "portfolio--zorg.json")
    check("11.4 a section document: {v, product, section, made, data}; data is the file", sec == {
          "v": 1, "product": "zorg", "section": "portfolio", "made": MADE, "data": jread(PORT)}, sec)
    check("11.5 runs/<made path-safe>: {at, sections, ok}", jread(o, "runs", "2026-11-26T10-00-00Z.json") == {
          "at": MADE, "sections": sorted(meta["sections"]), "ok": True}, jread(o, "runs", "2026-11-26T10-00-00Z.json"))
    check("11.6 theme is written as the file's theme; meta has no connectors key without the option",
          jread(o, "snapshot", "theme.json") == jread(THEME) and "connectors" not in meta, "")
    api = sh.build_snapshot([("portfolio", "zorg", {"rows": []})], [{"id": "zorg", "label": "Zorg", "color": None}], None, MADE)
    check("11.7 build_snapshot(sections, products, theme, made) -> {path: document}; no theme -> no theme document",
          sorted(api) == ["runs/2026-11-26T10-00-00Z", "snapshot/meta", "snapshot/portfolio--zorg"], sorted(api))
    rc, text, res, o2 = snap(d, "--product", "zorg:Зорг:#2f6fde", "--section", "portfolio:zorg:" + PORT, out="uk")
    check("11.8 a label may be non-Latin and have spaces", rc == 0 and jread(o2, "snapshot", "meta.json")["products"][0]["label"] == "Зорг", text)

    # test_snapshot_size
    big = os.path.join(d, "big.json")
    with open(big, "w") as f:
        json.dump({"rows": [{"t": "x" * 1000} for _ in range(300)]}, f)
    rc, text, res, o = snap(d, *ZP, "--section", "portfolio:zorg:" + PORT, "--section", "feed:zorg:" + big, out="size")
    over = res.get("over") or []
    check("11.9 a section over 256 KiB is not written, named in over with its size, ok false; the rest is written",
          rc == 1 and res.get("ok") is False and len(over) == 1 and over[0].get("path") == "snapshot/feed--zorg"
          and over[0].get("bytes", 0) > 256 * 1024 and not os.path.exists(os.path.join(o, "snapshot", "feed--zorg.json"))
          and os.path.exists(os.path.join(o, "snapshot", "portfolio--zorg.json"))
          and "feed--zorg" not in jread(o, "snapshot", "meta.json")["sections"], (text, over))

    # test_snapshot_ids
    cases = (
        ("a product id with a capital", ["--product", "Zorg:Zorg"], ["--section", "portfolio:Zorg:" + PORT], "product"),
        ("a product id with an underscore", ["--product", "zorg_pay:Zorg"], ["--section", "portfolio:zorg_pay:" + PORT], "product"),
        ("a section name with a slash", ZP, ["--section", "a/b:zorg:" + PORT], "section"),
        ("a section name over 64", ZP, ["--section", "a" * 65 + ":zorg:" + PORT], "section"),
        ("a section name starting with a dot", ZP, ["--section", ".x:zorg:" + PORT], "section"),
        ("a section of an unknown product", ZP, ["--section", "portfolio:ghost:" + PORT], "ghost"),
        ("a label with 25 characters", ["--product", "zorg:" + "я" * 25], ["--section", "portfolio:zorg:" + PORT], "label"),
        ("a bad colour", ["--product", "zorg:Zorg:red"], ["--section", "portfolio:zorg:" + PORT], "color"),
        ("the same section twice", ZP, ["--section", "portfolio:zorg:" + PORT, "--section", "portfolio:zorg:" + PORT], "twice"),
        ("a missing data file", ZP, ["--section", "portfolio:zorg:" + os.path.join(d, "nope.json")], "nope.json"),
        ("a connector role the profile does not declare", ZP, ["--section", "portfolio:zorg:" + PORT, "--connector", "ghost-role:Zorg Tracker:get"], "ghost-role"),
        ("a malformed connector", ZP, ["--section", "portfolio:zorg:" + PORT, "--connector", "issue-status:only"], "connector"),
    )
    for i, (label, prods, secs, needle) in enumerate(cases):
        rc, text, res, o = snap(d, *prods, *secs, out="bad%d" % i)
        check("11.10 %s: an error before anything is written" % label, rc == 1 and res.get("ok") is False
              and needle in res.get("error", "") and not os.path.exists(o), text)
    for seg in ("x" * 201,):
        try:
            sh.build_snapshot([("a", "b" * 201, {})], [{"id": "b" * 201, "label": "B", "color": None}], None, MADE)
            ok = False
        except sh.Bad:
            ok = True
        check("11.11 a segment over 200 bytes is refused by build_snapshot", ok, "")

    # connectors (R1) and the theme check (R2)
    rc, text, res, o = snap(d, *ZP, "--section", "portfolio:zorg:" + PORT, "--connector", "issue-status:Zorg Tracker:get_issue",
                            "--connector", "funnel-numbers:Zorg Board:read", out="conn")
    check("11.12 --connector ROLE:SERVER:TOOL -> meta.connectors {role: {server, tool}}", rc == 0 and jread(o, "snapshot", "meta.json").get(
          "connectors") == {"issue-status": {"server": "Zorg Tracker", "tool": "get_issue"},
                            "funnel-numbers": {"server": "Zorg Board", "tool": "read"}}, text)
    good = jread(THEME)
    check("11.13 check_theme: the Zorg theme is clean", sh.check_theme(good) == [], sh.check_theme(good))
    for label, mut in (("a missing key", lambda t: t.pop("font")), ("an extra key", lambda t: t.update(css="x")),
                       ("a colour that is not #rrggbb", lambda t: t["light"].update(bg="red")),
                       ("a 3-digit colour", lambda t: t["dark"].update(bg="#fff")),
                       ("a radius of 25", lambda t: t.update(radius=25)), ("a fractional radius", lambda t: t.update(radius=4.5)),
                       ("a boolean radius", lambda t: t.update(radius=True)), ("v 2", lambda t: t.update(v=2)),
                       ("light as a list", lambda t: t.update(light=[]))):
        t = copy.deepcopy(good)
        mut(t)
        check("11.14 check_theme names %s" % label, sh.check_theme(t) != [], "")
    badt = os.path.join(d, "bad-theme.json")
    with open(badt, "w") as f:
        json.dump(dict(good, radius=99), f)
    rc, text, res, o = snap(d, *ZP, "--section", "portfolio:zorg:" + PORT, "--theme", badt, out="badtheme")
    check("11.15 a bad --theme file is an error before anything is written", rc == 1 and "theme" in res.get("error", "")
          and not os.path.exists(o), text)

    # test_snapshot_no_people
    ppl = os.path.join(d, "people.json")
    with open(ppl, "w") as f:
        json.dump({"rows": [{"title": "T1", "Email": "a@zorg.example", "Author": "A", "meta": {"assignee": "B", "keep": 1,
                   "deep": [{"PERSON": "C", "owner": "D", "reporter": "E", "e-mail": "F", "name_of_person": "stays"}]}}],
                   "weakest": {"title": "W", "score": 1}}, f)
    rc, text, res, o = snap(d, *ZP, "--section", "portfolio:zorg:" + ppl, out="ppl")
    sec = jread(o, "snapshot", "portfolio--zorg.json")
    blob = json.dumps(sec["data"])
    gone = ("a@zorg.example", '"Author"', '"assignee"', '"PERSON"', '"owner"', '"reporter"', '"e-mail"', '"Email"')
    check("11.16 the keys email, e-mail, author, assignee, person, owner, reporter are dropped at any depth, any case",
          rc == 0 and not any(g in blob for g in gone) and sec["data"]["rows"][0]["meta"]["keep"] == 1
          and sec["data"]["rows"][0]["meta"]["deep"][0] == {"name_of_person": "stays"}, sec)
    dropped = res.get("dropped") or []
    check("11.17 dropped lists 'section: key-path' for each; the document id is the section label", len(dropped) == 7
          and "portfolio--zorg: rows.0.Email" in dropped and "portfolio--zorg: rows.0.meta.deep.0.PERSON" in dropped
          and all(": " in x for x in dropped), dropped)
    check("11.18 sources are not touched", jread(ppl)["rows"][0]["Email"] == "a@zorg.example", "")
    rc, text, res, o = snap(d, *ZP, "--section", "portfolio:zorg:" + PORT, out="clean")
    check("11.19 nothing to drop -> dropped is []", res.get("dropped") == [], res)
    rc, text, res = run("snapshot", "--profile", "cjm", "--out", os.path.join(d, "def"), *ZP, "--section", "portfolio:zorg:" + PORT)
    made_default = jread(d, "def", "snapshot", "meta.json").get("made", "")
    check("11.20 --at omitted: made is now in UTC as publications.py writes it", re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", made_default) is not None, made_default)


print("\nRESULT: %s (%d failed)" % ("GREEN ✅" if not fails else "RED ❌", fails))
sys.exit(1 if fails else 0)
