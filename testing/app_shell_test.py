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
        _, _, _, pg_en = wrap(d, ZORG, "--lang", "en", out="app-en.html")
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
  async function open(init, viewport, file) {
    const p = await b.newPage({viewport: viewport || {width: 1000, height: 700}}); const errs = [];
    p.__reqs = []; p.__url = 'file://' + (file || process.argv[2]);
    p.on('pageerror', e => errs.push(String(e))); p.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
    p.on('request', r => p.__reqs.push(r.url()));
    await p.route(/^https?:/, r => r.fulfill({status: 200, contentType: 'text/css', body: ''}));
    await p.addInitScript(init); await p.goto(p.__url); await p.waitForTimeout(300);
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
  out.live1 = await read(); out.liveErrs = errs; out.livePage = (await p.isVisible('.gpm-modules')) && (await p.isHidden('.gpm-page')); await p.close();   // R5: with a snapshot the modules replace the page
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

  // ---- Task 4: the theme (snapshot/theme), the switch
  const GOOD = {v: 1, id: 'zorg-calm', font: 'Inter', radius: 12,
    light: {bg: '#f7f6f2', surface: '#fefefe', text: '#1d2127', muted: '#5f6770', accent: '#2f6fde', border: '#d8dce1', ok: '#1f8a4c', warn: '#a8691a', crit: '#c53030'},
    dark: {bg: '#1b1f24', surface: '#242a31', text: '#e8eaed', muted: '#9aa3ad', accent: '#6aa0f5', border: '#39414a', ok: '#4cc38a', warn: '#e0a53a', crit: '#f06a6a'}};
  const TH = (t) => fakeDesktop + fakeDb({'meta': META, 'theme': t}, 'ok');
  const vars = (pg) => pg.evaluate(() => { const cs = getComputedStyle(document.documentElement), g = n => cs.getPropertyValue('--gpm-' + n).trim();
    return {bg: g('bg'), surface: g('surface'), text: g('text'), muted: g('muted'), accent: g('accent'), border: g('border'), ok: g('ok'), warn: g('warn'),
            crit: g('crit'), radius: g('radius'), font: g('font'), mode: document.documentElement.getAttribute('data-theme'),
            links: Array.from(document.querySelectorAll('link[rel=stylesheet]')).map(l => l.href),
            headBg: getComputedStyle(document.querySelector('.gpm-shell')).backgroundColor,
            keep: getComputedStyle(document.querySelector('.gpm-page #keep')).color,
            style: document.documentElement.getAttribute('style') || ''}; });
  const foreign = (pg) => pg.__reqs.filter(u => u !== pg.__url);
  const sw = (mode) => '.gpm-theme button[data-mode="' + mode + '"]';
  [p, errs] = await open(fakeDesktop);                     // no database, no theme: the neutral defaults
  await p.emulateMedia({colorScheme: 'light'}); await p.waitForTimeout(80);
  out.th_none = await vars(p); out.th_none_errs = errs;
  out.th_group = await p.evaluate(() => { const g = document.querySelector('.gpm-theme');
    return g ? {label: g.getAttribute('aria-label'), n: g.querySelectorAll('button').length,
                texts: Array.from(g.querySelectorAll('button')).map(x => x.textContent), pressed: Array.from(g.querySelectorAll('button')).map(x => x.getAttribute('aria-pressed')),
                tags: Array.from(g.querySelectorAll('button')).map(x => x.tagName), inHeader: !!g.closest('header.gpm-shell')} : null; });
  await p.emulateMedia({colorScheme: 'dark'}); await p.waitForTimeout(80);
  out.th_none_dark = await vars(p); await p.close();
  [p, errs] = await open(TH(GOOD));
  await p.emulateMedia({colorScheme: 'light'}); await p.waitForTimeout(80);
  out.th_sys_light = await vars(p); out.th_reqs = foreign(p);
  await p.emulateMedia({colorScheme: 'dark'}); await p.waitForTimeout(80);
  out.th_sys_dark = await vars(p);
  await p.click(sw('light')); out.th_pick_light = await vars(p);
  out.th_pressed = await p.$$eval('.gpm-theme button', e => e.map(x => x.getAttribute('aria-pressed')));
  await p.click(sw('dark')); out.th_pick_dark = await vars(p); out.th_stored = await p.evaluate(() => localStorage.getItem('gpm-theme'));
  await p.reload(); await p.waitForTimeout(300); out.th_reload = await vars(p);
  await p.click(sw('system')); await p.waitForTimeout(50); out.th_back_sys = await vars(p);
  await p.focus(sw('light')); await p.keyboard.press('Enter'); out.th_key_enter = (await vars(p)).mode;
  await p.focus(sw('dark')); await p.keyboard.press('Space'); out.th_key_space = (await vars(p)).mode;
  out.th_errs = errs;
  await p.evaluate(() => window.__push('theme', Object.assign({}, window.__docs.theme, {font: 'PT Sans', radius: 4})));
  await p.waitForTimeout(100); out.th_live = await vars(p);
  await p.evaluate(() => window.__push('theme', Object.assign({}, window.__docs.theme, {font: '', radius: 0})));
  await p.waitForTimeout(100); out.th_live_sys = await vars(p);
  await p.close();
  // foreign values: nothing applied, nothing requested
  const EVIL = Object.assign({}, GOOD, {font: 'Evil', radius: '9999'});
  EVIL.light = Object.assign({}, GOOD.light, {accent: 'red; background:url(x)', bg: 'url(x)', text: '#12345'});
  EVIL.dark = Object.assign({}, GOOD.dark, {accent: 'red; background:url(x)', bg: '#12345g'});
  [p, errs] = await open(TH(EVIL));
  await p.emulateMedia({colorScheme: 'light'}); await p.waitForTimeout(80);
  out.th_evil = await vars(p); out.th_evil_reqs = foreign(p); out.th_evil_errs = errs; await p.emulateMedia({colorScheme: 'dark'}); await p.waitForTimeout(80);
  out.th_evil_dark = await vars(p); await p.close();
  for (const bad of [{font: 'Inter&family=Evil'}, {font: 'inter'}, {font: 12}, {radius: 25}, {radius: -1}, {radius: 4.5}, {radius: null}]) {
    [p, errs] = await open(TH(Object.assign({}, GOOD, bad)));
    const v = await vars(p); out['th_bad_' + JSON.stringify(bad)] = {links: v.links, radius: v.radius, font: v.font, reqs: foreign(p), errs}; await p.close();
  }
  // a storage that throws: the page renders, the switch works for the session
  [p, errs] = await open("Object.defineProperty(window, 'localStorage', {get() { throw new Error('denied'); }});" + TH(GOOD));
  out.th_nostore0 = await vars(p); await p.click(sw('dark')); out.th_nostore1 = await vars(p);
  out.th_nostore_page = await p.isVisible('.gpm-modules'); out.th_nostore_errs = errs; await p.close();
  // English
  [p, errs] = await open(fakeDesktop, null, process.argv[4]);
  out.th_en = await p.evaluate(() => { const g = document.querySelector('.gpm-theme'); return {label: g.getAttribute('aria-label'), texts: Array.from(g.querySelectorAll('button')).map(x => x.textContent)}; }); await p.close();
  // phone width with the switch and the install button
  [p, errs] = await open(TH(GOOD), {width: 360, height: 640});
  out.th_phone = await p.evaluate(() => ({sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth,
    right: document.querySelector('.gpm-theme').getBoundingClientRect().right, h: document.querySelector('.gpm-shell').getBoundingClientRect().height})); await p.close();

  // ---- Task 5: modules, blocks, products, config
  const fs = require('fs');
  const fx = (n) => JSON.parse(fs.readFileSync(process.argv[5] + '/' + n, 'utf8'));
  const PRODS = [{id: 'zorg', label: 'Zorg', color: '#2f6fde'}, {id: 'zorg-pay', label: 'Zorg Pay', color: null}];
  const D5 = (section, product, data, made) => ({v: 1, product, section, made: made || '2026-11-26T10:00:00Z', data});
  const payTable = {columns: [{key: 'journey', title: 'Journey'}, {key: 'health', title: 'Health'}], rows: [{journey: 'Top up', health: 70, attention: 'ok'}]};
  function snapDocs(extra, products, thresholds) {
    const docs = Object.assign({
      'portfolio--zorg': D5('portfolio', 'zorg', fx('zorg-portfolio.json'), '2026-11-20T08:00:00Z'),
      'portfolio--zorg-pay': D5('portfolio', 'zorg-pay', payTable),
      'funnel--zorg': D5('funnel', 'zorg', fx('zorg-funnel.json')),
      'funnel--zorg-pay': D5('funnel', 'zorg-pay', fx('zorg-funnel.json')),
      'score--zorg': D5('score', 'zorg', fx('zorg-score.json')),
      'risks--zorg': D5('risks', 'zorg', fx('zorg-risks.json')),
      'news--zorg': D5('news', 'zorg', fx('zorg-feed.json'))}, extra || {});
    const sections = {}; Object.keys(docs).forEach(id => { if (docs[id]) { sections[id] = docs[id].made; } else { delete docs[id]; } });
    docs.meta = {v: 1, made: '2026-11-26T10:00:00Z', products: products || PRODS, thresholds: thresholds || {warning: 0.1, critical: 0.25}, sections};
    return docs;
  }
  const fakeDb2 = (colls, mode) => `
    window.__colls = ${JSON.stringify(colls)}; window.__subs2 = {};
    const qs2 = (c) => { const m = window.__colls[c] || {}; return {docs: Object.keys(m).sort().map(id => ({id, exists: true, data: () => m[id]})), size: Object.keys(m).length, empty: false, docChanges: () => []}; };
    window.__push2 = (c, id, data) => { window.__colls[c] = window.__colls[c] || {}; if (data === null) { delete window.__colls[c][id]; } else { window.__colls[c][id] = data; } (window.__subs2[c] || []).forEach(f => f(qs2(c))); };
    const db2 = {collection: (c) => ({onSnapshot: (next, err) => {
      if ('${mode}' === 'throws') { throw new Error('boom'); }
      (window.__subs2[c] = window.__subs2[c] || []).push(next); setTimeout(() => next(qs2(c)), 0); return () => {}; }})};
    const _use2 = window.claude.use; window.claude.use = async (n) => (n === 'db' ? ${mode === 'nodb' ? 'null' : 'db2'} : _use2(n));`;
  const APP = (docs, cfg, mode) => fakeDesktop + fakeDb2({snapshot: docs, config: cfg ? {app: cfg} : {}}, mode || 'ok');
  const mod = (pg) => pg.evaluate(() => {
    const q = (s, r) => Array.from((r || document).querySelectorAll(s));
    const txt = (e) => (e.textContent || '').trim();
    const shown = (s) => { const e = document.querySelector(s); return !!e && !e.hidden && getComputedStyle(e).display !== 'none'; };
    const ls = (k) => { try { return window.localStorage.getItem(k); } catch (e) { return 'ERR'; } };
    const act = document.activeElement;
    return {
      tabs: q('.gpm-tabs [role=tab]').map(b => b.getAttribute('data-tab')), tabTexts: q('.gpm-tabs [role=tab]').map(txt),
      selected: q('.gpm-tabs [aria-selected=true]').map(b => b.getAttribute('data-tab')),
      modulesShown: shown('.gpm-modules'), pageShown: shown('.gpm-page'),
      cards: q('.gpm-panel .gpm-card').map(c => ({product: c.getAttribute('data-product'), chip: (c.querySelector('.gpm-card-head .gpm-chip') || {}).textContent || null, text: txt(c)})),
      chips: q('.gpm-panel .gpm-chip').map(txt), switchBtns: q('.gpm-products button').map(b => ({text: txt(b), pressed: b.getAttribute('aria-pressed'), product: b.getAttribute('data-product')})),
      fresh: (document.querySelector('.gpm-fresh-module') || {}).textContent || '', empties: q('.gpm-empty').map(txt), unsupported: q('.gpm-unsupported').map(txt),
      placeholders: q('.gpm-placeholder').map(txt), rows: q('.gpm-panel tbody tr').map(r => q('td', r).map(txt)), panel: (document.querySelector('.gpm-panel') || {textContent: ''}).textContent.trim(),
      blockTitles: q('.gpm-block-title').map(txt), imgs: q('.gpm-modules img').length, pwned: !!window.__pwned,
      tab: ls('gpm-tab'), prod: ls('gpm-product'), active: act ? (act.getAttribute('data-tab') || act.getAttribute('data-product') || act.tagName) : null,
      headerSwitch: !!document.querySelector('.gpm-shell .gpm-products')};
  });
  const tab = async (pg, id) => { await pg.click('.gpm-tabs [data-tab="' + id + '"]'); await pg.waitForTimeout(60); };
  // order and defaults
  const CFG_ORDER = {v: 1, modules: [{id: 'funnel', on: false, order: 3}, {id: 'edits', on: true, order: 0}]};
  [p, errs] = await open(APP(snapDocs(), null)); out.t5_default = await mod(p); out.t5_default_errs = errs;
  await p.close();
  [p, errs] = await open(APP(snapDocs(), CFG_ORDER)); out.t5_order = await mod(p); await tab(p, 'edits'); out.t5_edits = await mod(p); out.t5_order_errs = errs; await p.close();
  // the fixture config: hides funnel, edits first, two custom modules
  const FIXCFG = fx('zorg-config.json');
  [p, errs] = await open(APP(snapDocs(), FIXCFG)); out.t5_fix = await mod(p);
  await tab(p, 'score'); out.t5_score = await mod(p);
  out.t5_score_dom = await p.evaluate(() => { const s = document.querySelector('.gpm-spark'); return {ns: s && s.namespaceURI, pts: s && s.querySelector('polyline') ? s.querySelector('polyline').getAttribute('points').split(' ').length : 0,
    value: document.querySelector('.gpm-num-value').textContent, unit: document.querySelector('.gpm-num-unit').textContent, delta: document.querySelector('.gpm-num-delta').textContent}; });
  await tab(p, 'watch'); out.t5_watch = await mod(p); out.t5_fix_errs = errs; await p.close();
  // foreign config: bad entries are ignored or marked, text stays text
  const EVILCFG = {v: 1, modules: ['junk', {id: 'portfolio', on: 'no'}, {id: 'funnel', on: false}, {id: 'map', on: true, order: 1.5}],
    custom: [{id: 'm1', title: 'Map try', block: 'map', source: 'map'}, {id: 'u1', title: '<b>x</b>', block: 'number', source: 'https://evil.example/x'},
      {id: 'h1', title: '<img src=x onerror=window.__pwned=1>', block: 'number', source: 'score'}, {id: 'long', title: 'x'.repeat(100), block: 'number', source: 'score'},
      {id: 'both', title: 'B', block: 'list', source: 'risks', blocks: [{block: 'list', source: 'risks'}]}, {id: 'Bad Id', title: 'z', block: 'list', source: 'risks'}, 'junk',
      {id: 'cm', title: 'CM', blocks: [{block: 'list', source: 'risks'}, {block: 'map', source: 'map'}]}, {id: 'cs', title: 'CS', block: 'list', source: '../x'},
      {id: 'cb', title: 'CB', block: 'pie', source: 'risks'}, {id: 'portfolio', title: 'dup', block: 'list', source: 'risks'}, {id: 'num', title: 5, block: 'number', source: 'score'}]};
  [p, errs] = await open(APP(snapDocs(), EVILCFG)); out.t5_evil = await mod(p); out.t5_evil_bits = {};
  for (const id of ['m1', 'u1', 'both', 'cm', 'cs', 'cb']) { await tab(p, id); const r = await mod(p); out.t5_evil_bits[id] = r.unsupported; }
  await tab(p, 'h1'); out.t5_evil_h1 = await mod(p); await tab(p, 'num'); out.t5_evil_num = await mod(p);
  out.t5_evil_title = await p.evaluate(() => Array.from(document.querySelectorAll('.gpm-tab')).map(b => b.textContent));
  out.t5_evil_errs = errs; await p.close();
  // product switch and labels
  [p, errs] = await open(APP(snapDocs(), null)); out.t5_all = await mod(p);
  out.t5_chipstyle = await p.evaluate(() => Array.from(document.querySelectorAll('.gpm-card-head .gpm-chip')).map(c => { const s = getComputedStyle(c); return {t: c.textContent, bg: s.backgroundColor, fg: s.color}; }));
  out.t5_btnpos = await p.evaluate(() => { const b = document.querySelector('.gpm-products').getBoundingClientRect(); return {inHeader: !!document.querySelector('.gpm-shell .gpm-products'), h: b.height}; });
  await p.click('.gpm-products [data-product="zorg"]'); await p.waitForTimeout(60); out.t5_zorg = await mod(p);
  await p.focus('.gpm-products [data-product="zorg-pay"]'); await p.keyboard.press('Enter'); await p.waitForTimeout(60); out.t5_pay_key = await mod(p);
  await p.reload(); await p.waitForTimeout(300); out.t5_reload = await mod(p);
  await p.click('.gpm-products [data-product=""]'); await p.waitForTimeout(60); out.t5_back_all = await mod(p); out.t5_all_errs = errs; await p.close();
  [p, errs] = await open("window.localStorage.setItem('gpm-product', 'ghost');" + APP(snapDocs(), null)); out.t5_ghost_prod = await mod(p); await p.close();
  [p, errs] = await open(APP(snapDocs({}, [PRODS[0]]), null)); out.t5_one = await mod(p); await p.close();
  [p, errs] = await open(APP(snapDocs({}, [{id: 'zorg', label: 'Zorg', color: '#ffe08a'}, {id: 'zorg-pay', label: 'Zorg Pay', color: '#123456'}]), null));
  out.t5_chipcontrast = await p.evaluate(() => Array.from(document.querySelectorAll('.gpm-card-head .gpm-chip')).map(c => { const s = getComputedStyle(c); return {t: c.textContent, bg: s.backgroundColor, fg: s.color}; })); await p.close();
  // unknown product, and a document with no product
  const ghost = {'risks--ghost': D5('risks', 'ghost', {items: [{title: 'Ghost risk'}]}), 'risks--lost': Object.assign(D5('risks', 'x', {items: [{title: 'Lost risk'}]}), {product: undefined})};
  [p, errs] = await open(APP(snapDocs(ghost), FIXCFG)); await tab(p, 'watch'); out.t5_unknown = await mod(p);
  await p.click('.gpm-products [data-product="zorg"]'); await p.waitForTimeout(60); out.t5_unknown_zorg = await mod(p); out.t5_unknown_errs = errs; await p.close();
  // empty states, placeholders
  [p, errs] = await open(APP(snapDocs(), null)); await tab(p, 'map'); out.t5_map_empty = await mod(p); await p.close();
  [p, errs] = await open(APP(snapDocs({'map--zorg': D5('map', 'zorg', {x: 1}), 'map.checkout--zorg': D5('map.checkout', 'zorg', {x: 2})}), null)); await tab(p, 'map'); out.t5_map = await mod(p); await p.close();
  // freshness: the oldest document shown
  [p, errs] = await open(APP(snapDocs(), null)); out.t5_fresh_all = (await mod(p)).fresh;
  await p.click('.gpm-products [data-product="zorg-pay"]'); await p.waitForTimeout(60); out.t5_fresh_pay = (await mod(p)).fresh; await p.close();
  // no snapshot, no database, a database that throws, a profile without modules
  [p, errs] = await open(APP({}, null)); out.t5_nosnap = await mod(p); out.t5_nosnap_errs = errs; await p.close();
  [p, errs] = await open(APP(snapDocs(), null, 'nodb')); out.t5_nodb = await mod(p); out.t5_nodb_errs = errs; await p.close();
  [p, errs] = await open(APP(snapDocs(), null, 'throws')); out.t5_throws = await mod(p); out.t5_throws_errs = errs; await p.close();
  [p, errs] = await open(fakeDesktop); out.t5_plain = await mod(p); await p.close();
  [p, errs] = await open(APP(snapDocs(), null), null, process.argv[6]); out.t5_pmos = await mod(p); out.t5_pmos_errs = errs; await p.close();
  // storage: the last tab, a tab that is gone, storage that throws
  [p, errs] = await open(APP(snapDocs(), null)); await tab(p, 'funnel'); out.t5_tab_click = await mod(p); await p.reload(); await p.waitForTimeout(300); out.t5_tab_reload = await mod(p); await p.close();
  [p, errs] = await open("window.localStorage.setItem('gpm-tab', 'zzz');" + APP(snapDocs(), null)); out.t5_tab_gone = await mod(p); await p.close();
  [p, errs] = await open("Object.defineProperty(window, 'localStorage', {get() { throw new Error('denied'); }});" + APP(snapDocs(), null));
  out.t5_nostore0 = await mod(p); await tab(p, 'funnel'); out.t5_nostore1 = await mod(p); await p.click('.gpm-products [data-product="zorg"]'); await p.waitForTimeout(60); out.t5_nostore2 = await mod(p); out.t5_nostore_errs = errs; await p.close();
  // keyboard: the arrows move between tabs
  [p, errs] = await open(APP(snapDocs(), null)); await p.focus('.gpm-tabs [data-tab="portfolio"]'); await p.keyboard.press('ArrowRight'); await p.waitForTimeout(60); out.t5_arrow = await mod(p);
  await p.keyboard.press('End'); await p.waitForTimeout(60); out.t5_end = await mod(p); await p.close();
  // the chart
  [p, errs] = await open(APP(snapDocs(), null)); await tab(p, 'funnel');
  const stages = (pg) => pg.evaluate(() => Array.from(document.querySelectorAll('.gpm-card')[0].querySelectorAll('.gpm-stage')).map(s => ({cls: s.className, head: s.querySelector('.gpm-stage-head').textContent,
    ns: s.querySelector('svg').namespaceURI, bar: parseFloat(s.querySelector('.gpm-bar').getAttribute('width')), barcls: s.querySelector('.gpm-bar').getAttribute('class'),
    attn: (s.querySelector('.gpm-attn-text') || {}).textContent || null, tag: s.querySelector('.gpm-bar').tagName, base: !!s.querySelector('.gpm-bar-base')})));
  out.t5_chart = await stages(p); out.t5_chart_all = await mod(p); await p.close();
  [p, errs] = await open(APP(snapDocs({}, null, {warning: 0.2, critical: 0.5}), null)); await tab(p, 'funnel'); out.t5_chart_th = (await stages(p)).map(s => s.cls); await p.close();
  const noth = snapDocs(); delete noth.meta.thresholds;
  [p, errs] = await open(APP(noth, null)); await tab(p, 'funnel'); out.t5_chart_noth = (await stages(p)).map(s => s.cls); await p.close();
  // table: status marks with a word, text from the data is only text, numbers only when finite
  const evilTable = {'portfolio--zorg': D5('portfolio', 'zorg', {columns: [{key: 'journey', title: '<i>Journey</i>'}, {key: 'health', title: 'Health'}, {key: '__proto__', title: 'P'}],
    rows: [{journey: '<img src=x onerror=window.__pwned=1>', health: 5, attention: 'crit'}, {journey: 'B', health: null, attention: 'weird'}, {journey: {a: 1}, health: [1], attention: 'warn'}, 'junk', {journey: 'C', health: 'x'.repeat(900), attention: 'ok', product: 'zorg'}]})};
  [p, errs] = await open(APP(snapDocs(evilTable), null)); out.t5_table_evil = await mod(p);
  out.t5_table_marks = await p.evaluate(() => Array.from(document.querySelectorAll('.gpm-table tbody tr')).map(r => ({cls: (r.querySelector('.gpm-attn') || {className: ''}).className, text: (r.querySelector('.gpm-attn-text') || {textContent: ''}).textContent,
    cellLen: Array.from(r.querySelectorAll('td')).map(t => t.textContent.length)}))); out.t5_table_heads = await p.evaluate(() => Array.from(document.querySelectorAll('.gpm-table th')).map(t => t.textContent));
  out.t5_table_errs = errs; await p.close();
  [p, errs] = await open(APP(snapDocs(), null)); out.t5_marks = await p.evaluate(() => Array.from(document.querySelectorAll('.gpm-table tbody tr')).map(r => ({ok: !!r.querySelector('.gpm-attn-ok'), warn: !!r.querySelector('.gpm-attn-warn'), crit: !!r.querySelector('.gpm-attn-crit'),
    text: (r.querySelector('.gpm-attn-text') || {textContent: ''}).textContent, shape: r.querySelector('.gpm-mark') ? getComputedStyle(r.querySelector('.gpm-mark')).backgroundColor : ''})));
  out.t5_weakest = await p.evaluate(() => (document.querySelector('.gpm-weakest') || {textContent: ''}).textContent); await p.close();
  // numbers
  const nums = {'score--zorg': D5('score', 'zorg', {value: '74', unit: 'pts'}), 'risks--zorg': D5('risks', 'zorg', {items: 'x'})};
  [p, errs] = await open(APP(snapDocs(nums), FIXCFG)); await tab(p, 'score'); out.t5_num_bad = await mod(p); await tab(p, 'watch'); out.t5_list_bad = await mod(p); await p.close();
  const nums2 = {'score--zorg': D5('score', 'zorg', {value: 5, delta: 5, trend: [1, 'x', 3]}), 'score--zorg-pay': D5('score', 'zorg-pay', {value: 1.5, delta: 0, trend: [2, 2, 2]})};
  [p, errs] = await open(APP(snapDocs(nums2), FIXCFG)); await tab(p, 'score'); out.t5_num2 = await p.evaluate(() => Array.from(document.querySelectorAll('.gpm-number')).map(n => ({v: n.querySelector('.gpm-num-value').textContent, d: (n.querySelector('.gpm-num-delta') || {textContent: null}).textContent,
    u: !!n.querySelector('.gpm-num-unit'), spark: n.querySelectorAll('.gpm-spark').length, pts: n.querySelector('polyline') ? n.querySelector('polyline').getAttribute('points') : null}))); await p.close();
  // live: a new section and a new config change what is shown, no reload
  [p, errs] = await open(APP(snapDocs(), null));
  await p.evaluate(() => { window.__push2('snapshot', 'portfolio--zorg-pay', {v: 1, product: 'zorg-pay', section: 'portfolio', made: '2026-12-02T08:00:00Z', data: {columns: [{key: 'journey', title: 'J'}], rows: [{journey: 'Live row'}]}});
    const m = window.__colls.snapshot.meta; m.sections['portfolio--zorg-pay'] = '2026-12-02T08:00:00Z'; window.__push2('snapshot', 'meta', m); });
  await p.waitForTimeout(100); out.t5_live1 = await mod(p);
  await p.evaluate(() => window.__push2('config', 'app', {v: 1, modules: [{id: 'portfolio', on: false}]})); await p.waitForTimeout(100); out.t5_live2 = await mod(p);
  await p.evaluate(() => window.__push2('config', 'app', null)); await p.waitForTimeout(100); out.t5_live3 = await mod(p); out.t5_live_errs = errs; await p.close();
  // phone width
  const wide = {'portfolio--zorg': D5('portfolio', 'zorg', {columns: Array.from({length: 10}, (_, i) => ({key: 'c' + i, title: 'Column number ' + i})), rows: [Object.fromEntries(Array.from({length: 10}, (_, i) => ['c' + i, 'value ' + i]))]})};
  [p, errs] = await open(APP(snapDocs(wide), FIXCFG), {width: 360, height: 640}); await tab(p, 'portfolio');
  out.t5_phone = await p.evaluate(() => { const d = document.documentElement, sc = document.querySelector('.gpm-scroll'), tb = document.querySelector('.gpm-tabs'), pr = document.querySelector('.gpm-products');
    return {sw: d.scrollWidth, cw: d.clientWidth, scrollInner: sc.scrollWidth, scrollOuter: sc.clientWidth, tabsInner: tb.scrollWidth, tabsOuter: tb.clientWidth, tabsOverflow: getComputedStyle(tb).overflowX, prRight: pr.getBoundingClientRect().right}; });
  out.t5_phone_errs = errs; await p.close();
  // English
  [p, errs] = await open(APP(snapDocs({}, null), EVILCFG), null, process.argv[4]); out.t5_en = await mod(p); await tab(p, 'm1'); out.t5_en_unsup = (await mod(p)).unsupported; await tab(p, 'edits'); out.t5_en_edits = (await mod(p)).placeholders; await p.close();
  [p, errs] = await open(APP(snapDocs({}, null), null), null, process.argv[4]); await tab(p, 'map'); out.t5_en_empty = (await mod(p)).empties;
  out.t5_en_sw = await p.evaluate(() => document.querySelector('.gpm-products').getAttribute('aria-label')); await p.close();
  console.log(JSON.stringify(out)); await b.close();
})();""")
        _, _, _, pg_pm = wrap(d, ZORG, name="pm-os", out="pmos-app.html")
        pr = subprocess.run(["node", js, pg, "x", pg_en, os.path.join(ROOT, "testing", "fixtures", "app"), pg_pm], capture_output=True, text=True, timeout=180, env=dict(os.environ, NODE_PATH=npm))
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

        NL, ND = sh.NEUTRAL["light"], sh.NEUTRAL["dark"]
        GOOD_LIGHT = {'bg': '#f7f6f2', 'surface': '#fefefe', 'text': '#1d2127', 'muted': '#5f6770', 'accent': '#2f6fde', 'border': '#d8dce1', 'ok': '#1f8a4c', 'warn': '#a8691a', 'crit': '#c53030'}
        GOOD_DARK = {'bg': '#1b1f24', 'surface': '#242a31', 'text': '#e8eaed', 'muted': '#9aa3ad', 'accent': '#6aa0f5', 'border': '#39414a', 'ok': '#4cc38a', 'warn': '#e0a53a', 'crit': '#f06a6a'}
        TOK = sh.TOKENS

        def only(v, side):
            return all(v.get(k) == side[k] for k in TOK)
        n0, n1 = br.get("th_none") or {}, br.get("th_none_dark") or {}
        check("10.18 pw_theme_defaults: with no theme (and no database) the neutral light values; the OS in dark -> the neutral dark values; radius 8px, system font",
              only(n0, NL) and only(n1, ND) and n0.get("radius") == "8px" and "system-ui" in n0.get("font", "") and not n0.get("links")
              and not br.get("th_none_errs"), (n0, n1))
        g = br.get("th_group") or {}
        check("10.19 the switch: one group in the header, three real <button>s «Світла / Темна / Як у системі», the default (system) is the pressed one",
              g.get("inHeader") is True and g.get("n") == 3 and g.get("texts") == ["Світла", "Темна", "Як у системі"] and g.get("label") == "Тема"
              and g.get("tags") == ["BUTTON"] * 3 and g.get("pressed") == ["false", "false", "true"], g)
        sl, sd = br.get("th_sys_light") or {}, br.get("th_sys_dark") or {}
        check("10.20 pw_theme_apply: the theme from snapshot/theme sets --gpm-<token>, --gpm-radius and --gpm-font on <html> (light OS) ",
              only(sl, GOOD_LIGHT) and sl.get("radius") == "12px" and sl.get("font", "").startswith('"Inter"') and sl.get("mode") == "system", sl)
        check("10.21 «as in the system» follows prefers-color-scheme live: the OS turns dark -> the dark tokens, no reload",
              only(sd, GOOD_DARK) and sd.get("mode") == "system", sd)
        pl, pd = br.get("th_pick_light") or {}, br.get("th_pick_dark") or {}
        check("10.22 pw_theme_switch: «Світла» / «Темна» set data-theme on <html> and choose the tokens against the OS; the pressed state shows it",
              pl.get("mode") == "light" and only(pl, GOOD_LIGHT) and pd.get("mode") == "dark" and only(pd, GOOD_DARK)
              and br.get("th_pressed") == ["true", "false", "false"], (pl, pd, br.get("th_pressed")))
        check("10.23 the choice is kept in localStorage under gpm-theme and comes back after a reload",
              br.get("th_stored") == "dark" and (br.get("th_reload") or {}).get("mode") == "dark" and only(br.get("th_reload") or {}, GOOD_DARK), (br.get("th_stored"), br.get("th_reload")))
        check("10.24 «Як у системі» again; the switch is usable by keyboard (Enter and Space on a focused button)",
              (br.get("th_back_sys") or {}).get("mode") == "system" and br.get("th_key_enter") == "light" and br.get("th_key_space") == "dark"
              and not br.get("th_errs"), (br.get("th_back_sys"), br.get("th_key_enter"), br.get("th_key_space"), br.get("th_errs")))
        check("10.25 the header is painted with the theme's surface; the wrapped page keeps its own colours (R5), in light and in dark",
              sl.get("headBg") == "rgb(254, 254, 254)" and pl.get("keep") == pd.get("keep") == n0.get("keep"), (sl.get("headBg"), pl.get("keep"), pd.get("keep")))
        check("10.26 one <link rel=stylesheet> to Google Fonts, built from the list's spelling; it is the only request outside the page",
              sl.get("links") == ["https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap"]
              and br.get("th_reqs") == sl.get("links"), (sl.get("links"), br.get("th_reqs")))
        lv, ls = br.get("th_live") or {}, br.get("th_live_sys") or {}
        check("10.27 a new snapshot/theme changes the variables live: another font replaces the link (still one), radius follows; font '' removes the link",
              lv.get("links") == ["https://fonts.googleapis.com/css2?family=PT+Sans:wght@400;700&display=swap"] and lv.get("radius") == "4px"
              and lv.get("font", "").startswith('"PT Sans"') and ls.get("links") == [] and ls.get("radius") == "0px" and "system-ui" in ls.get("font", ""), (lv, ls))
        ev, evd = br.get("th_evil") or {}, br.get("th_evil_dark") or {}
        check("10.28 test_theme_rejects_foreign_values: accent 'red; background:url(x)', font 'Evil', radius '9999' -> the default values, no request, no error",
              ev.get("accent") == NL["accent"] and ev.get("radius") == "8px" and "Evil" not in ev.get("font", "") and not ev.get("links")
              and br.get("th_evil_reqs") == [] and not br.get("th_evil_errs") and "url(" not in ev.get("style", "") and "red" not in ev.get("style", ""), (ev, br.get("th_evil_reqs")))
        check("10.29 a bad colour keeps only that token's default, the good tokens of the same theme apply (light and dark)",
              ev.get("bg") == NL["bg"] and ev.get("text") == NL["text"] and ev.get("muted") == GOOD_LIGHT["muted"]
              and evd.get("bg") == ND["bg"] and evd.get("accent") == ND["accent"] and evd.get("text") == GOOD_DARK["text"], (ev, evd))
        bads = {k: v for k, v in br.items() if k.startswith("th_bad_")}
        check("10.30 a font off the list (injection, wrong case, a number) or a radius that is not a whole 0-24 -> default, no link, no request",
              len(bads) == 7 and all(v["reqs"] == v["links"] and not v["errs"] and (v["links"] == [] or v["links"][0].split("family=")[1].startswith("Inter:"))
                                     for v in bads.values())
              and all(v["radius"] in ("8px", "12px") and ("Evil" not in v["font"]) for v in bads.values())
              and all(v["font"].startswith('"Inter"') or "system-ui" in v["font"] for v in bads.values()), bads)
        n0s, n1s = br.get("th_nostore0") or {}, br.get("th_nostore1") or {}
        check("10.31 pw_theme_switch without localStorage (it throws): the page renders, no error, the switch still works for the session",
              n0s.get("mode") == "system" and n1s.get("mode") == "dark" and only(n1s, GOOD_DARK) and br.get("th_nostore_page") is True
              and not br.get("th_nostore_errs"), (n0s, n1s, br.get("th_nostore_errs")))
        check("10.32 the switch is labelled in English on an English page", (br.get("th_en") or {}) == {"label": "Theme", "texts": ["Light", "Dark", "System"]}, br.get("th_en"))
        tp = br.get("th_phone") or {}
        check("10.33 at phone width the switch adds no horizontal scroll, stays on screen, the header stays small",
              tp and tp.get("sw") <= tp.get("cw") and tp.get("right") <= tp.get("cw") and tp.get("h") < 120, tp)

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

    # ---- Task 4: the theme ---------------------------------------------------------------------------------------------
    TZ, TP = (os.path.join(FIX, n) for n in ("zorg-tokens.json", "zorg-pay-tokens.json"))

    def theme(*args, out="th.json"):
        o = os.path.join(d, out)
        if os.path.exists(o):
            os.remove(o)
        rc, text, res = run("theme", *args, "--out", o)
        return rc, text, res, o

    def passes(t, mode):
        c = t[mode]
        return all(sh.contrast(c[k], c[b]) >= 4.5 - 1e-9 for k in ("text", "muted") for b in ("bg", "surface")) and \
            all(sh.contrast(c[k], c["surface"]) >= 3.0 - 1e-9 for k in ("accent", "ok", "warn", "crit"))

    # test_contrast_known
    check("12.1 contrast: black on white is 21.0, #777777 on white ~4.48, symmetric",
          sh.contrast("#000000", "#ffffff") == 21.0 and abs(sh.contrast("#777777", "#ffffff") - 4.48) < 0.01
          and sh.contrast("#ffffff", "#777777") == sh.contrast("#777777", "#ffffff") and sh.contrast("#abcdef", "#abcdef") == 1.0,
          (sh.contrast("#000000", "#ffffff"), sh.contrast("#777777", "#ffffff")))
    check("12.2 the constants: nine tokens in the brief's order, twelve fonts with Cyrillic",
          sh.TOKENS == ("bg", "surface", "text", "muted", "accent", "border", "ok", "warn", "crit")
          and sh.FONTS == ("Inter", "Roboto", "Open Sans", "Montserrat", "Manrope", "Rubik", "Nunito", "PT Sans", "Fira Sans",
                           "IBM Plex Sans", "Noto Sans", "Golos Text"), (sh.TOKENS, sh.FONTS))

    # test_candidates_two_products
    rc, text, res, o = theme("--tokens", TZ, "--tokens", TP)
    cands = res.get("candidates") or []
    check("12.3 test_candidates_two_products: two files -> zorg, zorg-pay, neutral; ok; the file holds {candidates}",
          rc == 0 and res.get("ok") is True and [c["id"] for c in cands] == ["zorg", "zorg-pay", "neutral"]
          and [c["product"] for c in cands] == ["zorg", "zorg-pay", "neutral"] and jread(o) == {"candidates": cands}, text)
    check("12.4 a candidate is {v, id, product, light, dark, font, radius, weak}; the tokens are the nine in each mode",
          all(set(c) == {"v", "id", "product", "light", "dark", "font", "radius", "weak"} and c["v"] == 1
              and set(c["light"]) == set(sh.TOKENS) == set(c["dark"]) for c in cands), cands[:1])
    zc, pc, nc = (cands + [{}, {}, {}])[:3]
    check("12.5 zorg (tokens at top level) keeps its light values, font and radius; zorg-pay keeps its own dark; both clean",
          zc.get("light", {}).get("accent") == "#2f6fde" and zc.get("font") == "Inter" and zc.get("radius") == 8
          and pc.get("dark", {}).get("accent") == "#3fc1b3" and pc.get("font") == "Manrope" and pc.get("radius") == 12
          and zc.get("weak") == [] and pc.get("weak") == [] and nc.get("weak") == [], (zc.get("weak"), pc.get("weak")))

    # test_dark_derived
    ND = sh.NEUTRAL["dark"]
    check("12.6 test_dark_derived: no dark -> neutral bg/surface/text/muted/border, every pair passes its threshold",
          all(zc.get("dark", {}).get(k) == ND[k] for k in ("bg", "surface", "text", "muted", "border")) and passes(zc, "dark")
          and ND["bg"] == "#121417" and ND["surface"] == "#1b1e23" and ND["text"] == "#e8eaed" and ND["muted"] == "#a7adb5" and ND["border"] == "#2c3138", zc.get("dark"))
    dark_tokens = os.path.join(d, "dark-tokens.json")
    with open(dark_tokens, "w") as f:   # an accent and a crit that are too dark for the dark surface
        json.dump(dict(jread(TZ), accent="#1a3a7a", ok="#145c34", warn="#7a4a00", crit="#8a1f1f"), f)
    rc, text, res, o = theme("--tokens", dark_tokens, out="dk.json")
    dz = res["candidates"][0]
    check("12.7 the product's accent/ok/warn/crit that fail on the dark surface are lightened in 2% HSL steps until they pass; the hue stays",
          passes(dz, "dark") and all(dz["dark"][k] != jread(dark_tokens)[k] for k in ("accent", "ok", "warn", "crit")) and dz["weak"] == []
          and all(abs(sh.hls(dz["dark"][k])[0] - sh.hls(jread(dark_tokens)[k])[0]) < 0.02 for k in ("accent", "ok", "warn", "crit"))
          and all(round((sh.hls(dz["dark"][k])[1] - sh.hls(jread(dark_tokens)[k])[1]) * 100) % 2 == 0 for k in ("accent", "ok", "warn", "crit")), dz["dark"])
    rc, text2, res2, o2 = theme("--tokens", TZ, "--tokens", TP, out="th2.json")
    check("12.8 deterministic: the same input twice gives the same bytes", open(o, "rb").read() == open(theme("--tokens", dark_tokens, out="dk2.json")[3], "rb").read()
          and open(os.path.join(d, "th.json"), "rb").read() == open(o2, "rb").read(), "")

    # test_weak_token_named
    weak_file = os.path.join(d, "weak-tokens.json")
    with open(weak_file, "w") as f:
        json.dump(dict(jread(TZ), muted="#9aa0a6", surface="#ffffff", bg="#ffffff"), f)
    rc, text, res, o = theme("--tokens", weak_file, out="wk.json")
    wz = res["candidates"][0]
    w = [x for x in wz["weak"] if x["token"] == "muted"]
    check("12.9 test_weak_token_named: muted #9aa0a6 on white -> weak {mode: light, token: muted, need: 4.5} with a ratio below it; it is a finding, not an error",
          rc == 0 and res.get("ok") is True and len(w) == 1 and w[0]["mode"] == "light" and w[0]["need"] == 4.5 and w[0]["ratio"] < 4.5
          and set(w[0]) == {"mode", "token", "ratio", "need", "suggest"} and len(wz["weak"]) == 1, wz["weak"])
    sg = w[0]["suggest"] if w else "#000000"
    check("12.10 its suggest passes the threshold on bg and surface, is the same hue, and is the nearest (one 0.5% step lighter fails)",
          re.fullmatch(r"#[0-9a-f]{6}", sg) is not None and sh.contrast(sg, "#ffffff") >= 4.5 and abs(sh.hls(sg)[0] - sh.hls("#9aa0a6")[0]) < 0.01
          and sh.hls(sg)[1] < sh.hls("#9aa0a6")[1], sg)
    # text and accent weak on a dark surface are named by mode as well
    both = os.path.join(d, "both.json")
    with open(both, "w") as f:
        json.dump({"product": "zorg", "light": {k: jread(TZ)[k] for k in sh.TOKENS},
                   "dark": dict({k: jread(TP)["dark"][k] for k in sh.TOKENS}, text="#556070", accent="#223344")}, f)
    rc, text, res, o = theme("--tokens", both, out="both-out.json")
    ws = {(x["mode"], x["token"]): x for x in res["candidates"][0]["weak"]}
    check("12.11 weak entries are per mode and token: dark text (4.5) and dark accent (3.0) are named, each with a passing suggest",
          set(ws) == {("dark", "text"), ("dark", "accent")} and ws[("dark", "text")]["need"] == 4.5 and ws[("dark", "accent")]["need"] == 3.0
          and sh.contrast(ws[("dark", "text")]["suggest"], jread(TP)["dark"]["surface"]) >= 4.5
          and sh.contrast(ws[("dark", "accent")]["suggest"], jread(TP)["dark"]["surface"]) >= 3.0, ws)

    # the built-in neutral theme
    nt = sh.NEUTRAL
    check("12.12 neutral: a complete light + dark pair that passes every threshold, system font, a whole radius; it is the neutral candidate",
          passes(nt, "light") and passes(nt, "dark") and nt["font"] == "" and nt["radius"] == 8 and set(nt["light"]) == set(sh.TOKENS) == set(nt["dark"])
          and all(nc.get(k) == nt[k] for k in ("light", "dark", "font", "radius")) and nc.get("weak") == [], nt)
    css_text = open(os.path.join(ROOT, "scripts", "app_shell", "shell.css"), encoding="utf-8").read()

    def css_block(selector_re):
        m = re.search(selector_re + r"\s*\{([^{}]*)\}", css_text)
        return dict(re.findall(r"--gpm-([a-z-]+):\s*([^;]+);", m.group(1))) if m else {}
    lightv, darkv = css_block(r"(?m)^:root"), css_block(r':root\[data-theme="dark"\]')
    mediav = css_block(r'(?m)^\s+:root:not\(\[data-theme="light"\]\)')
    check("12.13 neutral lives once: shell.css :root holds the Python light values, :root[data-theme=dark] the dark ones (and the OS-dark rule the same), radius 8px",
          all(lightv.get(k) == nt["light"][k] for k in sh.TOKENS) and all(darkv.get(k) == nt["dark"][k] for k in sh.TOKENS)
          and all(mediav.get(k) == nt["dark"][k] for k in sh.TOKENS) and lightv.get("radius") == "8px" and "system-ui" in lightv.get("font", ""),
          (lightv, darkv, mediav))
    check("12.14 the CSS sets no colour of its own beyond the variables: no '#' literal outside the :root blocks",
          not re.search(r"#[0-9a-fA-F]{3,8}\b", re.sub(r"[^{}]*:root[^{}]*\{[^{}]*\}", "", css_text)), "")

    # --pick (R2)
    rc, text, res, o = theme("--tokens", TZ, "--tokens", TP, "--pick", "zorg-pay", out="pick.json")
    pk = jread(o) if os.path.exists(o) else {}
    check("12.15 --pick zorg-pay writes that one theme: exactly the theme keys (product and weak dropped), check_theme clean",
          rc == 0 and res.get("ok") is True and res.get("picked") == "zorg-pay" and list(pk) == list(sh.THEME_KEYS) and pk["id"] == "zorg-pay"
          and pk["v"] == 1 and sh.check_theme(pk) == [] and pk["light"] == jread(TP)["light"], (text, pk))
    rc, text, res, o2 = theme("--tokens", TZ, "--pick", "neutral", out="pickn.json")
    check("12.16 --pick neutral works with no token file other than the one given; the written theme is the built-in one",
          rc == 0 and jread(o2) == sh.NEUTRAL and sh.check_theme(jread(o2)) == [], (text, jread(o2) if os.path.exists(o2) else None))
    rc, text, res, o3 = theme("--tokens", TZ, "--pick", "nope", out="p3.json")
    check("12.17 --pick of an unknown id is refused, naming the ids there are; no file", rc == 1 and res.get("ok") is False
          and "nope" in res.get("error", "") and "zorg" in res.get("error", "") and not os.path.exists(o3), text)
    rc, text, res, o3 = theme("--tokens", weak_file, "--pick", "zorg", out="p4.json")
    check("12.18 --pick of a candidate with weak tokens is refused: it names the token, the mode and its suggest; no file",
          rc == 1 and res.get("ok") is False and "muted" in res.get("error", "") and "light" in res.get("error", "") and sg in res.get("error", "")
          and not os.path.exists(o3), text)
    rc, text, res = run("snapshot", "--profile", "cjm", "--out", os.path.join(d, "withpick"), "--at", MADE, *ZP, "--section", "portfolio:zorg:" + PORT, "--theme", o)
    check("12.19 the picked theme goes into snapshot --theme as snapshot/theme", rc == 0 and jread(d, "withpick", "snapshot", "theme.json") == pk, text)
    rc, text, res, o3 = theme("--tokens", TZ, out="nofile.json")
    check("12.20 a lone token file still gets the neutral candidate (2 candidates)", rc == 0 and [c["id"] for c in res["candidates"]] == ["zorg", "neutral"], text)

    # a token input is checked strictly
    def refused(label, mut, needle):
        t = jread(TZ)
        mut(t)
        f = os.path.join(d, "tok-bad.json")
        with open(f, "w") as fh:
            json.dump(t, fh)
        rc, text, res, o = theme("--tokens", f, out="tb.json")
        check("12.21 a token file with %s is refused naming it; no output file" % label, rc == 1 and res.get("ok") is False and needle in res.get("error", "")
              and not os.path.exists(o), text)
    refused("a missing token (warn)", lambda t: t.pop("warn"), "warn")
    refused("a missing token inside light", lambda t: t.update(light={k: t[k] for k in sh.TOKENS if k != "ok"}) or [t.pop(k) for k in sh.TOKENS], "ok")
    refused("an unknown key", lambda t: t.update(shadow="x"), "shadow")
    refused("both light and top-level tokens", lambda t: t.update(light={k: t[k] for k in sh.TOKENS}), "light")
    refused("a colour that is not #rrggbb", lambda t: t.update(accent="red"), "accent")
    refused("a 3-digit colour", lambda t: t.update(bg="#fff"), "bg")
    refused("a font off the list", lambda t: t.update(font="Evil"), "font")
    refused("a radius of 25", lambda t: t.update(radius=25), "radius")
    refused("a fractional radius", lambda t: t.update(radius=2.5), "radius")
    refused("no product", lambda t: t.pop("product"), "product")
    refused("the product named neutral", lambda t: t.update(product="neutral"), "neutral")
    refused("a product that is not an id", lambda t: t.update(product="Zorg Pay"), "product")
    refused("a dark that is not nine tokens", lambda t: t.update(dark={"bg": "#000000"}), "dark")
    rc, text, res, o3 = theme("--tokens", TZ, "--tokens", TZ, out="dup.json")
    check("12.22 the same product twice is refused", rc == 1 and "zorg" in res.get("error", "") and not os.path.exists(o3), text)
    rc, text, res, o3 = theme("--tokens", os.path.join(d, "no-such.json"), out="nf.json")
    check("12.23 a token file that is not there is an error, not a traceback", rc == 1 and res.get("ok") is False and "Traceback" not in text, text)
    rc, text, res = run("theme", "--out", os.path.join(d, "x.json"))
    check("12.24 theme without --tokens: the neutral theme alone is a valid result (1 candidate)", rc == 0 and [c["id"] for c in res.get("candidates", [])] == ["neutral"], text)

    # check_theme, tightened (R2)
    good = jread(THEME)
    check("12.25 check_theme: the Zorg theme (font '') is clean and passes the thresholds", sh.check_theme(good) == [] and passes(good, "light") and passes(good, "dark"), sh.check_theme(good))
    for label, mut in (("a tenth token in light", lambda t: t["light"].update(shadow="#000000")),
                       ("a missing token in dark", lambda t: t["dark"].pop("crit")),
                       ("the font 'system'", lambda t: t.update(font="system")),
                       ("a font off the list", lambda t: t.update(font="Evil")),
                       ("a font in the wrong case", lambda t: t.update(font="inter")),
                       ("a number as the font", lambda t: t.update(font=12))):
        t = copy.deepcopy(good)
        mut(t)
        check("12.26 check_theme names %s" % label, sh.check_theme(t) != [], "")
    for fnt in [""] + list(sh.FONTS):
        t = dict(good, font=fnt)
        check("12.27 check_theme accepts the font '%s'" % fnt, sh.check_theme(t) == [], sh.check_theme(t))
    for r in (0, 24):
        check("12.28 check_theme accepts radius %d" % r, sh.check_theme(dict(good, radius=r)) == [], "")
    weak_theme = dict(good, light=dict(good["light"], muted="#9aa0a6"))
    rc, text, res, o3 = snap(d, *ZP, "--section", "portfolio:zorg:" + PORT, "--theme", (lambda f: (json.dump(weak_theme, open(f, "w")), f)[1])(os.path.join(d, "weak-theme.json")), out="weaksnap")
    check("12.29 snapshot --theme with a token under the contrast threshold is refused before anything is written, naming the token",
          rc == 1 and "muted" in res.get("error", "") and not os.path.exists(o3), text)

    # the page's list of fonts is the same as the script's
    js_src = open(os.path.join(ROOT, "scripts", "app_shell", "shell.js"), encoding="utf-8").read()
    m = re.search(r"var FONTS = \[([^\]]*)\]", js_src)
    check("12.30 shell.js: the fonts list and the nine tokens are the same as app_shell.py's, in the same order",
          m is not None and re.findall(r'"([^"]+)"', m.group(1)) == list(sh.FONTS)
          and re.findall(r'"([a-z]+)"', re.search(r"var TOKENS = \[([^\]]*)\]", js_src).group(1)) == list(sh.TOKENS), "")
    check("12.31 shell.js: the only address that is built is fonts.googleapis.com; localStorage is touched only in try/catch under gpm-theme",
          len(re.findall(r"https?://", js_src)) == 1 and "https://fonts.googleapis.com/css2?family=" in js_src and '"gpm-theme"' in js_src
          and js_src.count("localStorage") == 2, len(re.findall(r"https?://", js_src)))


# ---- Task 5: modules, blocks, products, config ---------------------------------------------------------------------------
FUNNEL, SCORE, RISKS, FEED, CONFIG = (os.path.join(FIX, n) for n in ("zorg-funnel.json", "zorg-score.json", "zorg-risks.json",
                                                                       "zorg-feed.json", "zorg-config.json"))
SHELL_DIR = os.path.join(ROOT, "scripts", "app_shell")
COMPOSED = {"id": "watch", "title": {"uk": "Стеження", "en": "Watch"},
            "blocks": [{"block": "list", "source": "risks", "title": {"uk": "Ризики", "en": "Risks"}},
                       {"block": "feed", "source": "news"}]}

with tempfile.TemporaryDirectory() as d:
    # test_wrap_embeds_every_file: shell.js, then blocks.js (each its own inline <script>), byte for byte
    rc, text, res, o = wrap(d, ZORG, out="t5.html")
    html5 = body_of(o) if os.path.exists(o) else ""
    names = [n for n in ("shell.js", "blocks.js", "map.js", "desk.js") if os.path.exists(os.path.join(SHELL_DIR, n))]
    srcs = {n: open(os.path.join(SHELL_DIR, n), encoding="utf-8", newline="").read() for n in names}
    scripts5 = re.findall(r'<script id="gpm-(\w+)">\n(.*?)</script>', html5, re.S)
    check("13.1 blocks.js exists and is embedded right after shell.js, each as its own inline <script>, byte for byte",
          "blocks.js" in srcs and [n for n, _ in scripts5][:2] == ["shell", "blocks"]
          and all(src in html5 for src in srcs.values() if "</script" not in src.lower()), (names, [n for n, _ in scripts5]))
    check("13.2 every embedded file is one IIFE, never closes a script, no <script src>, map.js only with a map block",
          all(s.lstrip().startswith("(function") and "</script" not in s.lower() for s in srcs.values())
          and not re.search(r"<script\b[^>]*\bsrc\s*=", html5, re.I)
          and ("map.js" not in srcs or "gpm-map" in html5), names)
    pm = wrap(d, ZORG, name="pm-os", out="pmos.html")
    check("13.3 a profile without a map block does not get map.js", "gpm-map" not in body_of(pm[3]) and pm[0] == 0, pm[1])
    two = wrap(d, ZORG, out="t5b.html")
    check("13.4 two runs give the same bytes with every file", body_of(two[3]) == html5, "")
    check("13.5 shell.js exposes the registry window.__gpmShell and starts the parts on DOMContentLoaded",
          "__gpmShell" in srcs["shell.js"] and "DOMContentLoaded" in srcs["shell.js"], "")
    bj = srcs.get("blocks.js", "")
    check("13.6 blocks.js: only the SVG namespace as an address; storage only in try/catch under gpm-tab and gpm-product; no innerHTML",
          len(re.findall(r"https?://", bj)) == 1 and "http://www.w3.org/2000/svg" in bj and '"gpm-tab"' in bj and '"gpm-product"' in bj
          and "innerHTML" not in bj and "insertAdjacentHTML" not in bj and "createElementNS" in bj and "eval(" not in bj, len(bj))
    check("13.7 blocks.js: the block names are the same as app_shell.py's BLOCKS",
          re.findall(r'"([a-z]+)"', (re.search(r"var BLOCK_NAMES = \[([^\]]*)\]", bj) or re.search("(x)", "x")).group(1)) == list(sh.BLOCKS), "")

    # test_module_forms: the short and the composed form (R9)
    def mods(*ms):
        return prof(modules=list(ms), menu=[])
    short = {"id": "a", "block": "table", "source": "a", "home": True, "title": {"uk": "А", "en": "A"}}
    check("13.8 'blocks' is a module key", "blocks" in sh.MODULE_KEYS, sh.MODULE_KEYS)
    check("13.9 the composed form is clean", sh.check_profile("zorg", mods(short, COMPOSED)) == [], sh.check_profile("zorg", mods(short, COMPOSED)))
    both = dict(COMPOSED, block="table", source="risks")
    check("13.10 both forms in one module are refused", has(sh.check_profile("zorg", mods(both)), "both"), sh.check_profile("zorg", mods(both)))
    check("13.11 a module with neither form is refused", sh.check_profile("zorg", mods({"id": "x", "title": {"uk": "Х", "en": "X"}})) != [], "")
    for label, blocks in (("an empty blocks list", []), ("blocks that is not a list", "table"), ("a block entry that is not a mapping", ["table"]),
                          ("an unknown block", [{"block": "pie", "source": "risks"}]),
                          ("a URL as source", [{"block": "list", "source": "https://zorg.example/x"}]),
                          ("a source outside the section names", [{"block": "list", "source": "Not A Section"}]),
                          ("a missing source", [{"block": "list"}]),
                          ("an unknown key in a block", [{"block": "list", "source": "risks", "code": "x"}]),
                          ("a block title without both languages", [{"block": "list", "source": "risks", "title": {"uk": "Р"}}]),
                          ("a map next to another block", [{"block": "map", "source": "map"}, {"block": "list", "source": "risks"}])):
        errs = sh.check_profile("zorg", mods(dict(COMPOSED, blocks=blocks)))
        check("13.12 composed module with %s is refused" % label, errs != [], errs)
    check("13.13 a map as the single block of a composed module is allowed",
          sh.check_profile("zorg", mods(dict(COMPOSED, blocks=[{"block": "map", "source": "map"}]))) == [], "")
    check("13.14 the source @edits is allowed; a URL or a path as a short source is refused",
          sh.check_profile("zorg", mods(dict(short, block="feed", source="@edits"))) == []
          and sh.check_profile("zorg", mods(dict(short, source="https://zorg.example"))) != []
          and sh.check_profile("zorg", mods(dict(short, source="../x"))) != [], "")
    # the repo's profiles are still clean, and a composed profile wraps
    check("13.15 wrap takes a profile with a composed module", sh.wrap_page(ZORG, "zorg", mods(short, COMPOSED), "uk").count('"blocks"') == 1, "")

    # test_config_check (rules shared with the page)
    cfg = json.load(open(CONFIG, encoding="utf-8"))
    check("13.16 the Zorg config fixture is clean", sh.check_config(cfg) == [], sh.check_config(cfg))
    html_cfg = dict(cfg, custom=[dict(cfg["custom"][0], title="<img src=x onerror=alert(1)>")])
    check("13.17 HTML in a title is not an error: it is just text", sh.check_config(html_cfg) == [], sh.check_config(html_cfg))
    def bad_custom(**over):
        return dict(cfg, custom=[dict(cfg["custom"][0], **over)])
    for label, c, needle in (
            ("an unknown block", bad_custom(block="pie"), "block"),
            ("the block map", bad_custom(block="map", source="map"), "map"),
            ("a URL as source", bad_custom(source="https://zorg.example/x"), "source"),
            ("a source with a slash", bad_custom(source="a/b"), "source"),
            ("a title that is not text", bad_custom(title=5), "title"),
            ("a title over 80 characters", bad_custom(title="x" * 81), "title"),
            ("both forms", bad_custom(blocks=[{"block": "list", "source": "risks"}]), "both"),
            ("an empty blocks list", {"v": 1, "custom": [{"id": "w", "title": "W", "blocks": []}]}, "blocks"),
            ("a map inside blocks", {"v": 1, "custom": [{"id": "w", "title": "W", "blocks": [{"block": "map", "source": "map"}]}]}, "map"),
            ("a bad custom id", bad_custom(id="Not Ok"), "id"),
            ("a bad version", dict(cfg, v=2), "v"),
            ("modules that is not a list", dict(cfg, modules="x"), "modules"),
            ("an entry with 'on' that is not a boolean", dict(cfg, modules=[{"id": "funnel", "on": "no"}]), "on"),
            ("an entry with a fractional order", dict(cfg, modules=[{"id": "funnel", "on": True, "order": 1.5}]), "order"),
            ("a config that is not a mapping", ["x"], "mapping")):
        errs = sh.check_config(c)
        check("13.18 check_config names %s" % label, has(errs, needle), errs)
    check("13.19 @edits is a legal custom source", sh.check_config(bad_custom(block="feed", source="@edits")) == [], "")
    rc, out, res = run("check", "--config", CONFIG)
    check("13.20 check --config FILE on the fixture: ok, no errors", rc == 0 and res == {"ok": True, "errors": []}, out)
    badf = os.path.join(d, "bad-config.json")
    json.dump(bad_custom(block="pie", source="https://zorg.example"), open(badf, "w"))
    rc, out, res = run("check", "--config", badf)
    check("13.21 check --config with an unknown block and a bad source: exit 1, both named", rc == 1 and res.get("ok") is False
          and has(res.get("errors", []), "block") and has(res.get("errors", []), "source"), out)
    htmlf = os.path.join(d, "html-config.json")
    json.dump(html_cfg, open(htmlf, "w"))
    rc, out, res = run("check", "--config", htmlf)
    check("13.22 check --config with HTML in a title: ok", rc == 0 and res.get("ok") is True, out)
    rc, out, res = run("check", "--config", os.path.join(d, "nope.json"))
    check("13.23 check --config on a missing file: exit 1 with the reason", rc == 1 and res.get("ok") is False and res.get("error"), out)
    notjson = os.path.join(d, "notjson.json")
    open(notjson, "w").write("{oops")
    rc, out, res = run("check", "--config", notjson)
    check("13.24 check --config on text that is not JSON: exit 1 with the reason", rc == 1 and res.get("ok") is False and res.get("error"), out)
    # the Zorg section fixtures take the snapshot builder
    rc, out, res = run("snapshot", "--profile", "cjm", *ZP, "--section", "funnel:zorg:" + FUNNEL, "--section", "funnel:zorg-pay:" + FUNNEL,
                       "--section", "score:zorg:" + SCORE, "--section", "risks:zorg:" + RISKS, "--section", "news:zorg:" + FEED,
                       "--at", MADE, "--out", os.path.join(d, "s5"))
    check("13.25 the funnel (both products), score, risks and feed fixtures go through the snapshot command", rc == 0 and res.get("ok") is True, out)


if have_pw:
    ALL_ORDER = ["portfolio", "map", "funnel", "edits"]
    def g(k):
        return br.get(k) or {}
    df = g("t5_default")
    check("14.1 no config: the tabs are the profile's modules in its order, the home module is open, the modules replace the page",
          df.get("tabs") == ALL_ORDER and df.get("selected") == ["portfolio"] and df.get("modulesShown") is True and df.get("pageShown") is False
          and df.get("tabTexts") == ["Портфель", "Карти", "Воронка", "Правки команди"] and not br.get("t5_default_errs"), df)
    od = g("t5_order")
    check("14.2 pw_modules_order: config hides funnel and puts edits first -> tabs edits, portfolio, map; the home module still opens first",
          od.get("tabs") == ["edits", "portfolio", "map"] and od.get("selected") == ["portfolio"] and not br.get("t5_order_errs"), od)
    check("14.3 the source @edits shows the placeholder for now", g("t5_edits").get("placeholders") == ["Правки команди з'являться тут"], g("t5_edits"))
    fx_ = g("t5_fix")
    check("14.4 the fixture config: funnel off, edits first, then the two custom modules last",
          fx_.get("tabs") == ["edits", "portfolio", "map", "score", "watch"] and fx_.get("tabTexts")[3:] == ["Health score", "Risks and news"], fx_)
    sd = g("t5_score_dom")
    check("14.5 pw_custom_block: a custom number block draws its section: value, unit, delta with a sign, a sparkline built with createElementNS",
          sd.get("value") == "74" and sd.get("unit") == "pts" and sd.get("delta") == "-3" and sd.get("ns") == "http://www.w3.org/2000/svg" and sd.get("pts") == 5, sd)
    wt = g("t5_watch")
    check("14.6 a composed custom module shows its blocks one under another, each with its title; list and feed are plain lists",
          wt.get("blockTitles") == ["Risks", "News"] and "Refund takes too long" in wt.get("panel", "") and "Funnel stage renamed" in wt.get("panel", "")
          and "25.11.2026" in wt.get("panel", "") and "Median 6 days" in wt.get("panel", ""), wt)
    ev = g("t5_evil")
    check("14.7 foreign config: bad modules entries are ignored, a bad custom id, a duplicate id and junk are dropped, a bad custom block keeps its tab",
          ev.get("tabs") == ["portfolio", "map", "edits", "m1", "u1", "h1", "long", "both", "cm", "cs", "cb", "num"] and not br.get("t5_evil_errs"), ev)
    bits = g("t5_evil_bits")
    check("14.8 pw_custom_block: a custom `map`, a URL as source, both forms, a map next to a block, a source outside the names and an unknown block each show «блок не підтримується»",
          all(bits.get(k) == ["блок не підтримується"] for k in ("m1", "u1", "both", "cm", "cs", "cb")), bits)
    h1 = g("t5_evil_h1")
    check("14.9 a title with HTML is shown as text; nothing is injected; the block still renders", h1.get("imgs") == 0 and h1.get("pwned") is False
          and "<img src=x onerror=window.__pwned=1>" in br.get("t5_evil_title", []) and "74" in h1.get("panel", ""), (h1, br.get("t5_evil_title")))
    tt = br.get("t5_evil_title") or []
    check("14.10 a title is cut to 80 characters; a title that is not text falls back to the id", len(tt) > 7 and len(tt[6]) == 80 and tt[11] == "num", tt)
    al = g("t5_all")
    check("14.11 pw_product_switch: «Усі» shows the cards of both products, each with its label, in the order of the products",
          [c.get("chip") for c in al.get("cards", [])] == ["Zorg", "Zorg Pay"] and al.get("headerSwitch") is True
          and [(b["text"], b["pressed"]) for b in al.get("switchBtns", [])] == [("Усі", "true"), ("Zorg", "false"), ("Zorg Pay", "false")], al)
    check("14.12 the row that names its own product carries its label", any("Zorg Pay" in " ".join(r) for r in al.get("rows", [])) and len(al.get("chips", [])) >= 3, al.get("chips"))
    cs = br.get("t5_chipstyle") or []
    check("14.13 the chip is the product's colour with white or black text; a product without a colour takes the palette colour by position",
          cs == [{"t": "Zorg", "bg": "rgb(47, 111, 222)", "fg": "rgb(255, 255, 255)"}, {"t": "Zorg Pay", "bg": "rgb(26, 127, 55)", "fg": "rgb(255, 255, 255)"}], cs)
    cc = br.get("t5_chipcontrast") or []
    check("14.14 a light product colour gets black text, a dark one white", [(c["bg"], c["fg"]) for c in cc] == [
          ("rgb(255, 224, 138)", "rgb(0, 0, 0)"), ("rgb(18, 52, 86)", "rgb(255, 255, 255)")], cc)
    zg = g("t5_zorg")
    check("14.15 choosing `zorg` hides the cards of zorg-pay and the rows of another product; the choice is kept in gpm-product",
          [c.get("chip") for c in zg.get("cards", [])] == ["Zorg"] and not any("Pay by card" in " ".join(r) for r in zg.get("rows", []))
          and any("First order" in " ".join(r) for r in zg.get("rows", [])) and zg.get("prod") == "zorg"
          and [b["pressed"] for b in zg.get("switchBtns", [])] == ["false", "true", "false"], zg)
    pk = g("t5_pay_key")
    check("14.16 the switch works from the keyboard (Enter), and the focus stays on the button", [c.get("chip") for c in pk.get("cards", [])] == ["Zorg Pay"]
          and pk.get("prod") == "zorg-pay" and pk.get("active") == "zorg-pay", pk)
    check("14.17 the product survives a reload; «Усі» brings both back", [c.get("chip") for c in g("t5_reload").get("cards", [])] == ["Zorg Pay"]
          and [c.get("chip") for c in g("t5_back_all").get("cards", [])] == ["Zorg", "Zorg Pay"] and g("t5_back_all").get("prod") == "", (g("t5_reload"), g("t5_back_all")))
    check("14.18 a stored product that meta does not know falls back to «Усі»", len(g("t5_ghost_prod").get("cards", [])) == 2, g("t5_ghost_prod"))
    check("14.19 with one product there is no switch", g("t5_one").get("switchBtns") == [] and g("t5_one").get("headerSwitch") is False, g("t5_one"))
    un, uz = g("t5_unknown"), g("t5_unknown_zorg")
    check("14.20 pw_unknown_product: a document of a product that meta lacks, and one with no product, go under «Без продукту»; «Усі» shows them",
          sorted(c.get("chip") for c in un.get("cards", [])) == ["Zorg", "Zorg", "Без продукту", "Без продукту"]    # the list block, then the feed block
          and "Ghost risk" in un.get("panel", "") and "Lost risk" in un.get("panel", ""), un)
    check("14.21 …and choosing a product hides them", [c.get("chip") for c in uz.get("cards", [])] == ["Zorg", "Zorg"] and "Ghost risk" not in uz.get("panel", "") and "Lost risk" not in uz.get("panel", "")
          and not br.get("t5_unknown_errs"), uz)
    check("14.22 a module with no data shows the empty state in words", g("t5_map_empty").get("empties") == ["Ще немає даних — Claude додасть їх після наступного прогону"], g("t5_map_empty"))
    mp = g("t5_map")
    check("14.23 the block map shows its placeholder for each map section (map and map.*)", mp.get("placeholders") == ["Карта з'явиться тут"] * 2 and mp.get("empties") == [], mp)
    check("14.24 a module shows «дані від» with the oldest date of what it shows, and follows the product choice",
          "дані від 20.11.2026" in br.get("t5_fresh_all", "") and "дані від 26.11.2026" in br.get("t5_fresh_pay", ""), (br.get("t5_fresh_all"), br.get("t5_fresh_pay")))
    for key in ("t5_nosnap", "t5_nodb", "t5_throws", "t5_plain", "t5_pmos"):
        r = g(key)
        check("14.25 %s: the page stays as it was, the modules stay hidden, no switch, no error" % key, r.get("pageShown") is True and r.get("modulesShown") is False
              and r.get("tabs") == [] and r.get("headerSwitch") is False and not br.get(key + "_errs"), r)
    tc, tr_ = g("t5_tab_click"), g("t5_tab_reload")
    check("14.26 the last tab is kept in gpm-tab and opens again after a reload", tc.get("tab") == "funnel" and tr_.get("selected") == ["funnel"], (tc, tr_))
    check("14.27 a stored tab that is gone opens the home module", g("t5_tab_gone").get("selected") == ["portfolio"], g("t5_tab_gone"))
    n0, n1, n2 = g("t5_nostore0"), g("t5_nostore1"), g("t5_nostore2")
    check("14.28 with a storage that throws everything works for the session, no error", n0.get("selected") == ["portfolio"] and n1.get("selected") == ["funnel"]
          and [c.get("chip") for c in n2.get("cards", [])] == ["Zorg"] and not br.get("t5_nostore_errs"), (n0, n1, n2))
    check("14.29 the arrow keys and End move between tabs and keep the focus", g("t5_arrow").get("selected") == ["map"] and g("t5_arrow").get("active") == "map"
          and g("t5_end").get("selected") == ["edits"] and g("t5_end").get("active") == "edits", (g("t5_arrow"), g("t5_end")))
    ch = br.get("t5_chart") or []
    check("14.30 the chart: one horizontal bar per stage as SVG, value and baseline as text, cart warn, pay crit, done and visit ok, a stage with no baseline plain",
          len(ch) == 5 and all(c.get("ns") == "http://www.w3.org/2000/svg" and c.get("tag") == "rect" for c in ch)
          and [("warn" in c["cls"], "crit" in c["cls"]) for c in ch] == [(False, False), (True, False), (False, True), (False, False), (False, False)]
          and "700" in ch[1]["head"] and "800" in ch[1]["head"] and "база" not in ch[4]["head"] and "база" in ch[1]["head"], ch)
    check("14.31 …the status is also a word (never colour alone); bar widths follow the values", len(ch) == 5 and ch[1]["attn"] == "Увага" and ch[2]["attn"] == "Критично"
          and ch[0]["bar"] == 100 and abs(ch[4]["bar"] - 1.2) < 0.01 and ch[1]["base"] and not ch[4]["base"], ch)
    check("14.32 meta.thresholds move the marks; with none the defaults 0.10 / 0.25 apply", br.get("t5_chart_th") == ["gpm-stage gpm-stage-ok", "gpm-stage gpm-stage-ok", "gpm-stage gpm-stage-warn", "gpm-stage gpm-stage-ok", "gpm-stage"]
          and (br.get("t5_chart_noth") or [""] * 3)[1] == "gpm-stage gpm-stage-warn" and br.get("t5_chart_noth")[2] == "gpm-stage gpm-stage-crit", (br.get("t5_chart_th"), br.get("t5_chart_noth")))
    mk = br.get("t5_marks") or []
    check("14.33 table: an attention mark per row with its own shape colour and a word", [(m["ok"], m["warn"], m["crit"]) for m in mk[:3]] == [(True, False, False), (False, True, False), (False, False, True)]
          and [m["text"] for m in mk[:3]] == ["Усе гаразд", "Увага", "Критично"] and len({m["shape"] for m in mk}) == 3, mk)
    check("14.34 the weakest line of a table is shown", "Pay by card" in (br.get("t5_weakest") or "") and "44" in br.get("t5_weakest", ""), br.get("t5_weakest"))
    te = g("t5_table_evil")
    check("14.35 table data is text: HTML shows as text, no element, no script; a cell that is not text or a finite number is empty; long text is cut",
          te.get("imgs") == 0 and te.get("pwned") is False and any("<img src=x onerror=window.__pwned=1>" in " ".join(r) for r in te.get("rows", []))
          and not br.get("t5_table_errs") and max([max(r["cellLen"] or [0]) for r in br.get("t5_table_marks", [])] or [9999]) <= 500 and "<i>Journey</i>" in br.get("t5_table_heads", []), (te, br.get("t5_table_heads")))
    check("14.36 an unknown attention value shows no mark; a junk row is skipped", [m["text"] for m in br.get("t5_table_marks", [])] == ["Критично", "", "Увага", "Усе гаразд", "Усе гаразд"], br.get("t5_table_marks"))
    check("14.37 a number block whose value is not a finite number, and a list with no items, show the empty state",
          g("t5_num_bad").get("empties") == ["Ще немає даних — Claude додасть їх після наступного прогону"] and len(g("t5_list_bad").get("empties", [])) >= 1, (g("t5_num_bad"), g("t5_list_bad")))
    n2s = br.get("t5_num2") or []
    check("14.38 number: a positive delta has a +, zero none, a trend needs two numbers; a flat trend is a flat line",
          [(n["v"], n["d"], n["u"], n["spark"]) for n in n2s] == [("5", "+5", False, 1), ("1.5", "0", False, 1)] and len(n2s) == 2 and n2s[1]["pts"].split(" ")[0].split(",")[1] == n2s[1]["pts"].split(" ")[1].split(",")[1], n2s)
    l1, l2, l3 = g("t5_live1"), g("t5_live2"), g("t5_live3")
    check("14.39 live: a new section document shows without a reload; a new config reorders and hides; deleting the config restores the profile's order",
          any("Live row" in " ".join(r) for r in l1.get("rows", [])) and l2.get("tabs") == ["map", "funnel", "edits"] and l3.get("tabs") == ALL_ORDER
          and not br.get("t5_live_errs"), (l1, l2, l3))
    ph = g("t5_phone")
    check("14.40 at phone width the page never scrolls sideways; tabs scroll in their own strip, the wide table in its own container",
          ph and ph["sw"] <= ph["cw"] and ph["scrollInner"] > ph["scrollOuter"] and ph["tabsInner"] > ph["tabsOuter"] and ph["tabsOverflow"] in ("auto", "scroll")
          and ph["prRight"] <= ph["cw"] and not br.get("t5_phone_errs"), ph)
    en = g("t5_en")
    check("14.41 an English page: tabs, the switch label, the unsupported line and the placeholders are in English",
          br.get("t5_en_unsup") == ["this block is not supported"] and br.get("t5_en_edits") == ["Team edits will appear here"]
          and br.get("t5_en_empty") == ["No data yet — Claude will add it after the next run"] and br.get("t5_en_sw") == "Product"
          and [b["text"] for b in en.get("switchBtns", [])][:1] == ["All"], (en, br.get("t5_en_unsup"), br.get("t5_en_empty")))

print("\nRESULT: %s (%d failed)" % ("GREEN ✅" if not fails else "RED ❌", fails))
sys.exit(1 if fails else 0)
