#!/usr/bin/env python3
"""TC-pm-os — the profile `pm-os` of references/app-profiles.yaml, its sections and references/pm-os-protocol.md.

The profile passes the shell's check and has the modules of the protocol — five in the rail, the screen of one metric
under the metrics module and the settings at the rail's foot; every section a block reads has a fixture
of the block's shape (fictional products Zorg and Zorg Pay) and a row in the protocol's table, and the table names no
section the profile does not read; a snapshot of all sections for two products writes one document per section and
product, drops a person's key, and the wrapped page holds the profile but no data. The browser step (node + global
Playwright, as in app_shell_test.py) is skipped with a line when Playwright is absent. Stdlib only; run from the root:

  env -u GROW_PM_CONTEXT_PATH -u GROW_PM_PROVIDER_PATHS python3 testing/pm_os_test.py
"""
import json, os, re, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "app_shell.py")
FIX = os.path.join(ROOT, "testing", "fixtures", "app", "pm-os")
PROTOCOL = os.path.join(ROOT, "references", "pm-os-protocol.md")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import app_shell as sh  # noqa: E402

fails = 0
MODULES = ["today", "directions", "metrics", "rhythms", "context"]        # the rail's entries
ALL = ["today", "directions", "metrics", "metric", "rhythms", "context", "settings"]
PRODUCTS = [{"id": "zorg", "label": "Zorg", "color": "#2f6fed"}, {"id": "zorg-pay", "label": "Zorg Pay", "color": "#0e7490"}]
MADE = "2026-11-26T10:00:00Z"


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


def fixture(section):
    with open(os.path.join(FIX, "zorg-%s.json" % section), encoding="utf-8") as f:
        return json.load(f)


COLUMN_KEYS = {"key", "title", "kind", "sub", "parts", "last", "scale", "limit", "group"}
TIME = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def shaped(block, data):
    """True when `data` has what the block shows (references/pm-os-protocol.md §2)."""
    if block == "table":
        return (isinstance(data.get("columns"), list) and data["columns"] and isinstance(data.get("rows"), list)
                and all({"key", "title"} <= set(c) <= COLUMN_KEYS and c.get("kind") in (None, "num", "segments", "meter") for c in data["columns"])
                and all(isinstance(r, dict) for r in data["rows"]))
    if block == "bars":
        if data.get("kind") == "delta":
            return bool(data.get("groups")) and all(g.get("rows") and all(r.get("label") and number(r.get("value")) for r in g["rows"]) for g in data["groups"])
        if data.get("kind") == "compare":
            return bool(data.get("rows")) and all(r.get("label") and r.get("values") and all(number(v) for v in r["values"]) for r in data["rows"])
        return data.get("kind") == "columns" and bool(data.get("cols")) and all(c.get("label") and number(c.get("value")) for c in data["cols"])
    if block == "line":
        x, series = data.get("x") or [], data.get("series") or []
        return len(x) >= 2 and 1 <= len(series) <= 4 and all(len(s.get("values") or []) == len(x) for s in series)
    if block == "day":
        items = data.get("items") or []
        return (bool(re.match(r"^\d{4}-\d{2}-\d{2}$", str(data.get("date")))) and all(TIME.match(str(data.get(k))) for k in ("start", "end"))
                and bool(items) and all(i.get("title") and TIME.match(str(i.get("from"))) and TIME.match(str(i.get("to"))) for i in items))
    if block in ("list", "feed"):
        items = data.get("items")
        ok = isinstance(items, list) and items and all(isinstance(i, dict) and i.get("title") for i in items)
        return bool(ok and (block == "list" or all(i.get("at") for i in items)))
    if block == "number":
        return isinstance(data.get("value"), (int, float)) and not isinstance(data.get("value"), bool)
    if block == "lead":
        return isinstance(data.get("text"), str) and bool(data["text"].strip())
    return False


def walk(node):
    if isinstance(node, dict):
        for k, v in node.items():
            yield k, v
            yield from walk(v)
    elif isinstance(node, list):
        for v in node:
            yield from walk(v)


# ---- 1. the profile -------------------------------------------------------------------------------------------------
prof = (sh.load_profiles().get("profiles") or {}).get("pm-os") or {}
errs = sh.check_profile("pm-os", prof)
check("1.1 the profile pm-os passes the shell's check", errs == [], errs)
mods = prof.get("modules") or []
check("1.2 the modules in the protocol's order: five stand in the rail, one screen under the metrics module, the settings at the rail's foot",
      [m.get("id") for m in mods] == ALL and [m["id"] for m in mods if not m.get("under") and not m.get("foot")] == MODULES
      and [(m["id"], m.get("under")) for m in mods if m.get("under")] == [("metric", "metrics")]
      and [m["id"] for m in mods if m.get("foot")] == ["settings"], [m.get("id") for m in mods])
check("1.3 today is the home module, and the only one", [m.get("id") for m in mods if m.get("home")] == ["today"])
check("1.4 every module is composed (a blocks list), none takes a map or the page's edits",
      all(isinstance(m.get("blocks"), list) and m["blocks"] and "block" not in m for m in mods)
      and not any(b.get("block") == "map" or b.get("source") == "@edits" for m in mods for b in m.get("blocks") or []))
every = [(m["id"], b.get("block"), b.get("source")) for m in mods for b in m.get("blocks") or []]
pairs = [x for x in every if not str(x[2]).startswith("@")]     # the blocks that read a section
sources = [s for _, _, s in pairs]
check("1.5 a section is read by one block only", len(sources) == len(set(sources)), sources)
check("1.6 today opens with the sentence the shell counts, then with what needs the user",
      every[:2] == [("today", "lead", "@summary"), ("today", "feed", "needs-you")], every[:2])
blocks = [(m["id"], b) for m in mods for b in m.get("blocks") or []]
seen, untitled = set(), []
for mid, b in blocks:                 # a block with no title: a module's sentence, or a block under its group's title
    first = b.get("group") and (mid, b["group"]) not in seen
    seen.add((mid, b.get("group")))
    if "title" not in b and b.get("block") != "lead" and (not b.get("group") or first):
        untitled.append((mid, b.get("source")))
check("1.7 every title is in both languages; a sentence has none, a group is named by its first block, and only the goal's band names itself",
      all(set(m.get("title") or {}) == set(sh.LANGS) for m in mods)
      and all(set(b["title"]) == set(sh.LANGS) for _, b in blocks if "title" in b)
      and all("title" not in b for _, b in blocks if b.get("block") == "lead") and untitled == [("metrics", "goal")], untitled)
check("1.11 the side rail, the signals and then the sources beside the home module, the products and the data's updates beside the settings, the plugin's own mark with a glyph to fall back on",
      prof.get("layout") == "rail" and [(mid, b["source"]) for mid, b in blocks if b.get("place") == "aside"] == [("today", "signals"), ("today", "sources"), ("settings", "settings-products"), ("settings", "settings-refresh")]
      and prof.get("icon") == {"glyph": "os", "image": "plugin"}, (prof.get("layout"), prof.get("icon")))
check("1.13 every module opens with a sentence: the home's is counted by the shell, the others read a section; the groups stand in the metrics module and on the screen under it",
      [b.get("source") for mid, b in blocks if b.get("block") == "lead"] == ["@summary", "directions-lead", "metrics-lead", "metric-lead", "rhythms-lead", "context-lead", "settings-lead"]
      and [(mid, b["group"], b["source"]) for mid, b in blocks if b.get("group")] == [("metrics", "main", "metrics-change"), ("metrics", "main", "metrics-compare"),
          ("metrics", "main", "metrics"), ("metrics", "pace", "metrics-pace"), ("metrics", "pace", "metrics-periods"), ("metric", "trend", "metric-value"), ("metric", "trend", "metrics-trend")])
check("1.14 a module's counter words are in both languages; the home, the context, the settings and the screen of a metric have none",
      [m["id"] for m in mods if "counts" in m] == ["directions", "metrics", "rhythms"]
      and all(set(m["counts"]) == set(sh.LANGS) for m in mods if "counts" in m))
def broken(change):
    """The check's errors for the profile with one module changed by `change(module) -> module`."""
    return sh.check_profile("x", dict(prof, modules=[change(json.loads(json.dumps(m))) if m["id"] == "metrics" else m for m in mods]))
def with_block(m, i, **kv):
    m["blocks"][i].update(kv)
    return m
check("1.15 a group's name is a short id: anything else is refused, and so is a group on a block that reads the shell",
      any("group" in e for e in broken(lambda m: with_block(m, 2, group="Main group")))
      and any("group" in e for e in sh.check_profile("x", dict(prof, modules=[dict(mods[0], blocks=[dict(mods[0]["blocks"][0], group="a")] + mods[0]["blocks"][1:])] + mods[1:]))))
check("1.16 counter words that are not two or three short words per language are refused",
      any("counts" in e for e in broken(lambda m: dict(m, counts={"uk": ["сигнал"], "en": ["signal", "signals"]})))
      and any("counts" in e for e in broken(lambda m: dict(m, counts={"uk": ["сигнал", "сигнали", "сигналів"]}))))
bad_sum = sh.check_profile("x", dict(prof, modules=[dict(mods[0], blocks=[{"block": "list", "source": "@summary", "title": {"uk": "а", "en": "a"}}])] + mods[1:]))
check("1.12 the source @summary under any block but lead is refused", any("@summary" in e for e in bad_sum), bad_sum)
def changed(mid, **kv):
    """The check's errors for the profile with the module `mid` given the keys `kv`."""
    return sh.check_profile("x", dict(prof, modules=[dict(m, **kv) if m["id"] == mid else m for m in mods]))
check("1.17 the settings stand at the rail's foot, one module only, never the home one and never under another",
      any("foot" in e for e in changed("context", foot=True)) and any("foot" in e for e in changed("today", foot=True))
      and any("foot" in e or "under" in e for e in changed("settings", under="metrics")))
check("1.18 a screen under a module names a module of the rail — not itself, not the foot, not another screen — and only it has the way back",
      any("under" in e for e in changed("metric", under="nowhere")) and any("under" in e for e in changed("metric", under="settings"))
      and any("under" in e for e in changed("rhythms", under="metric")) and any("back" in e for e in changed("rhythms", back={"uk": "Назад", "en": "Back"})))
check("1.19 the words a module gives the shell — where, about, back — are short and in both languages",
      any("where" in e for e in changed("metrics", where={"uk": "метриках"})) and any("about" in e for e in changed("metrics", about={"uk": "а" * 121, "en": "a"}))
      and [m["id"] for m in mods if "where" in m] == ["directions", "metrics", "rhythms"] and [m["id"] for m in mods if "about" in m] == MODULES)
asks = [(mid, b["source"], b["ask"].get("when")) for mid, b in blocks if "ask" in b]
check("1.20 a phrase for Claude is the profile's own: a label and a phrase in both languages, on the goal while it has no value and under the data's updates; "
      "an unknown `when` or a missing phrase is refused",
      asks == [("metrics", "goal", "empty"), ("settings", "settings-refresh", None)]
      and all(set(b["ask"]["label"]) == set(sh.LANGS) and set(b["ask"]["say"]) == set(sh.LANGS) for _, b in blocks if "ask" in b)
      and any("ask" in e for e in broken(lambda m: with_block(m, 1, ask={"label": {"uk": "а", "en": "a"}, "say": {"uk": "а", "en": "a"}, "when": "later"})))
      and any("ask" in e for e in broken(lambda m: with_block(m, 1, ask={"label": {"uk": "а", "en": "a"}}))), asks)
rf = prof.get("refresh") or {}
check("1.21 the rail's foot asks for fresh data with the profile's phrase and reads one sentence on the next update; a refresh without a phrase or with a bad source is refused",
      set(rf) == {"source", "label", "say"} and set(rf["label"]) == set(sh.LANGS) and set(rf["say"]) == set(sh.LANGS)
      and any("refresh" in e for e in sh.check_profile("x", dict(prof, refresh={"label": rf["label"]})))
      and any("refresh" in e for e in sh.check_profile("x", dict(prof, refresh=dict(rf, source="@summary")))), rf)
bad_at = [sh.check_profile("x", dict(prof, modules=[dict(m, blocks=[dict(b, block="table") if b.get("source") == src else b for b in m["blocks"]]) for m in mods]))
          for src in ("@modules", "@theme")]
check("1.22 the switches of the modules and the theme are the shell's own, shown as a list in the settings and under no other block",
      [(mid, b["block"]) for mid, b in blocks if b.get("source") in ("@modules", "@theme")] == [("settings", "list")] * 2
      and all(any(src in e for e in errs_) for src, errs_ in zip(("@modules", "@theme"), bad_at)), bad_at)
check("1.8 no full access, no commands, no permission beyond the shell's", prof.get("level") == "app" and prof.get("commands") == []
      and set(prof.get("permissions") or []) <= set(sh.PERMISSIONS))
check("1.9 the menu names the modules only", prof.get("menu") == MODULES, prof.get("menu"))
check("1.10 a connector is a role and a placeholder, never a value",
      all(set(c) == {"role", "needs"} and re.fullmatch(r"<[a-z][a-z0-9_]*>", c["needs"]) for c in prof.get("connectors") or []))

# ---- 2. the sections: fixtures and the protocol ---------------------------------------------------------------------
have = sorted(f[len("zorg-"):-len(".json")] for f in os.listdir(FIX) if f.startswith("zorg-") and f.endswith(".json"))
sources = sources + [rf.get("source")]          # the sentence of the rail's foot is a section too, read by no block
check("2.1 a fixture for every section the profile reads, and no other", have == sorted(sources), (have, sorted(sources)))
bad = [(s, b) for _, b, s in pairs + [("", "lead", rf.get("source"))] if s in have and not shaped(b, fixture(s))]
check("2.2 every fixture has the shape of the block that shows it", not bad, bad)
with open(PROTOCOL, encoding="utf-8") as f:
    protocol = f.read()
rows = re.findall(r"^\| `([a-z-]+)` \| `(@?[a-z0-9.-]+)` \| ([a-z]+) \|", protocol, re.M)
check("2.9 the protocol names the section of the rail's foot, which no block reads", "`%s`" % rf.get("source") in protocol)
check("2.3 the protocol's table of sections is the profile's blocks: module, section, block, in order",
      rows == [(m, s, b) for m, b, s in every], (rows, every))
check("2.8 the protocol gives the shape of every block the profile uses", all(("- `%s` — " % b) in protocol or ("`%s` — " % b) in protocol for b in {b for _, b, _ in every}),
      sorted({b for _, b, _ in every}))
people = [k for s in have for k, _ in walk(fixture(s)) if k in sh.PEOPLE_KEYS]
check("2.4 no fixture holds a person's key", not people, people)
text = json.dumps([fixture(s) for s in have], ensure_ascii=False)
check("2.5 the fixtures are fictional: Zorg only, no address, no e-mail",
      not re.search(r"https?://|@[a-z0-9-]+\.[a-z]{2,}", text, re.I) and "zorg" in text.lower())
check("2.6 the protocol names the standing consent's limits: private only, data documents only, a local schedule, taken back",
      all(n in protocol for n in ("standing consent", "`private`", "`snapshot/*` and `runs/*`", "SCHEDULE `local`", "Відклич згоду")))
for ref, needle in (("data-policy.md", "pm-os-protocol.md` §5"), ("native-surfaces.md", "pm-os-protocol.md` §5")):
    with open(os.path.join(ROOT, "references", ref), encoding="utf-8") as f:
        check("2.7 %s points at the consent's section" % ref, needle in f.read())

# ---- 3. a snapshot of the pult --------------------------------------------------------------------------------------
sections = [(s, p["id"], fixture(s)) for s in sources for p in PRODUCTS]
docs = sh.build_snapshot(sections, PRODUCTS, None, MADE)
want = {"snapshot/%s--%s" % (s, p["id"]) for s in sources for p in PRODUCTS} | {"snapshot/meta", "runs/2026-11-26T10-00-00Z"}
check("3.1 one document per section and product, the meta and the run — nothing else", set(docs) == want, sorted(set(docs) ^ want))
check("3.2 the meta lists both products and every section written",
      [p["id"] for p in docs["snapshot/meta"]["products"]] == ["zorg", "zorg-pay"]
      and len(docs["snapshot/meta"]["sections"]) == len(sources) * 2)
check("3.3 no theme document without a theme: the shell's neutral one is the default", "snapshot/theme" not in docs)
with_person = dict(fixture("directions"))
with_person["rows"] = [dict(r, assignee="Somebody", owner="Somebody") for r in with_person["rows"]]
d2, over, dropped = sh._build([("directions", "zorg", with_person)], PRODUCTS, None, MADE)
check("3.4 a person's key in a section is dropped and named",
      not any(k in sh.PEOPLE_KEYS for k, _ in walk(d2["snapshot/directions--zorg"])) and dropped and not over, dropped)
LATER = "2026-11-26T11:00:00Z"
part = sh.build_snapshot([("meetings", "zorg", fixture("meetings"))], PRODUCTS, None, LATER, prev_meta=docs["snapshot/meta"])
kept = part["snapshot/meta"]["sections"]
check("3.6 a partial run keeps the dates of the sections it did not write (protocol §4, step 4)",
      set(part) == {"snapshot/meetings--zorg", "snapshot/meta", "runs/2026-11-26T11-00-00Z"}
      and kept.get("meetings--zorg") == LATER and kept.get("directions--zorg") == MADE
      and len(kept) == len(sources) * 2 and "--prev-meta" in protocol, kept)
with tempfile.TemporaryDirectory() as d:
    pf = os.path.join(d, "products.json")
    with open(pf, "w", encoding="utf-8") as f:
        json.dump(PRODUCTS, f)
    args = ["snapshot", "--profile", "pm-os", "--at", MADE, "--products", pf, "--out", os.path.join(d, "db")]
    for s in sources:
        for p in PRODUCTS:
            args += ["--section", "%s:%s:%s" % (s, p["id"], os.path.join(FIX, "zorg-%s.json" % s))]
    rc, out, res = run(*args)
    check("3.5 the command writes the same documents as files", rc == 0 and res.get("ok") is True
          and {x["path"] for x in res.get("docs", [])} == want and res.get("dropped") == [], out)

    # ---- 4. the page ------------------------------------------------------------------------------------------------
    page = os.path.join(d, "page.html")
    with open(page, "w", encoding="utf-8") as f:
        f.write('<!doctype html>\n<html lang="uk"><head><meta charset="utf-8"><title>Zorg</title></head>'
                "<body><p>Zorg</p></body></html>\n")
    app = os.path.join(d, "app.html")
    rc, out, res = run("wrap", "--page", page, "--profile", "pm-os", "--out", app)
    html = open(app, encoding="utf-8").read() if rc == 0 else ""
    m = re.search(r'<script id="gpm-profile" type="application/json">(.*?)</script>', html, re.S)
    shown = json.loads(m.group(1)) if m else {}
    check("4.1 the page wraps as the app pm-os", rc == 0 and res.get("profile") == "pm-os", out)
    check("4.2 the page carries the modules and the ask for fresh data", [x.get("id") for x in shown.get("modules") or []] == ALL
          and (shown.get("refresh") or {}).get("say") == rf.get("say"))
    check("4.3 the page holds no data: no fixture title, no connector placeholder",
          "ZORG-100" not in html and "Refund" not in html and "<jira_project>" not in html)
    check("4.4 no map script for a profile without a map", 'id="gpm-map"' not in html)

    # ---- 5. the browser ---------------------------------------------------------------------------------------------
    npm = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip() if subprocess.run(
        ["which", "npm"], capture_output=True).returncode == 0 else ""
    try:
        subprocess.run(["node", "-e", "require('playwright')"], check=True, capture_output=True, timeout=30,
                       env=dict(os.environ, NODE_PATH=npm))
        have_pw = rc == 0
    except Exception:
        have_pw = False
    if not have_pw:
        print("⏭  5.x the browser pass — skipped: no playwright")
    else:
        colls = {"snapshot": {k.split("/", 1)[1]: v for k, v in docs.items() if k.startswith("snapshot/")}, "config": {}}
        js = os.path.join(d, "pw.js")
        with open(js, "w", encoding="utf-8") as f:
            f.write(r"""
const { chromium } = require('playwright'); const fs = require('fs');
(async () => {
  const fake = `window.__colls = ${fs.readFileSync(process.argv[3], 'utf8')};
    const qs = (c) => { const m = window.__colls[c] || {}; return {docs: Object.keys(m).sort().map(id => ({id, exists: true, data: () => m[id]})), size: Object.keys(m).length, empty: false, docChanges: () => []}; };
    window.__subs = {}; window.__writes = [];
    const db = {collection: (c) => ({onSnapshot: (next) => { (window.__subs[c] = window.__subs[c] || []).push(next); setTimeout(() => next(qs(c)), 0); return () => {}; },
      doc: (id) => ({set: async (d) => { window.__writes.push(c + '/' + id + ' ' + JSON.stringify(d)); (window.__colls[c] = window.__colls[c] || {})[id] = d; (window.__subs[c] || []).forEach(f => f(qs(c))); }})})};
    window.claude = {use: async (n) => (n === 'db' ? db : n === 'user' ? {isOwner: async () => OWNER} : null)};`;
  const page = fs.readFileSync(process.argv[2], 'utf8');
  const html = page.replace('<head>', '<head><script>' + fake.replace('OWNER', 'true') + '</script>');
  const b = await chromium.launch(); const out = {};
  const p = await b.newPage({viewport: {width: 1100, height: 800}, timezoneId: 'UTC'});
  const errs = []; p.on('pageerror', e => errs.push(e.message));
  await p.clock.setFixedTime(new Date('2026-11-26T13:30:00Z'));   // the day of the fixture, inside its focus time
  await p.setContent(html, {waitUntil: 'load'}); await p.waitForTimeout(500);
  const q = (sel) => p.$$eval(sel, e => e.map(x => x.textContent.trim()));
  const visible = (sel) => p.$$eval(sel, e => e.filter(x => x.offsetParent !== null).map(x => x.textContent.trim()));
  out.tabs = await q('[role=tab] .gpm-tab-title');
  const counts = () => p.$$eval('[role=tab]', e => e.map(x => { const c = x.querySelector('.gpm-tab-count'); return c ? c.textContent.trim() : ''; }));
  const sections = () => p.$$eval('.gpm-modules section.gpm-block', e => e.map(x => [(x.querySelector('.gpm-block-title') || {textContent: ''}).textContent,
    (x.querySelector('.gpm-block-side') || {textContent: ''}).textContent, x.querySelectorAll('.gpm-block-head .gpm-chip').length].join('|')));
  out.counts = await counts();
  out.fresh = await p.$eval('.gpm-fresh', e => e.textContent).catch(() => null);
  out.today = await sections();
  out.rail = await p.evaluate(() => ({cls: document.documentElement.classList.contains('gpm-layout-rail'),
    inHeader: !!document.querySelector('header.gpm-shell [role=tablist]'), vertical: document.querySelector('[role=tablist]').getAttribute('aria-orientation'),
    left: document.querySelector('header.gpm-shell').getBoundingClientRect().right <= document.querySelector('.gpm-modules').getBoundingClientRect().left + 1,
    logo: (document.querySelector('header.gpm-shell > img.gpm-logo') || {src: ''}).src.slice(0, 22)}));
  out.todayTitles = await visible('.gpm-modules h2, .gpm-modules h3');
  out.todayText = await p.$eval('.gpm-modules', e => e.innerText);
  out.lead = await p.$eval('.gpm-lead-text', e => e.textContent).catch(() => null);
  out.aside = await q('.gpm-col-aside .gpm-block-title');
  out.day = await p.evaluate(() => ({blocks: document.querySelectorAll('.gpm-c-day .gpm-c-day-block').length, focus: document.querySelectorAll('.gpm-c-day .gpm-c-day-block.gpm-c-fill-3').length,
    rows: Array.from(document.querySelectorAll('.gpm-c-day-row')).map(r => r.querySelector('.gpm-at').textContent + ' ' + r.querySelector('.gpm-item-title').textContent),
    text: document.querySelector('.gpm-c-day').innerText}));
  out.pairs = await p.$$eval('.gpm-col-aside .gpm-item-pair', e => e.map(x => x.querySelector('.gpm-item-title').textContent + '=' + x.querySelector('.gpm-item-value').textContent + (x.querySelector('.gpm-item-value.gpm-ink-warn') ? '!' : '')));
  out.rowChips = await p.$$eval('.gpm-col-aside li', e => e.map(x => x.querySelectorAll('.gpm-chip').length));
  out.switch = await q('.gpm-products button');
  out.foot = await p.evaluate(() => { const f = document.querySelector('header.gpm-shell .gpm-foot'); return f ? Array.from(f.children).map(x => x.className.split(' ')[0] + ':' + (x.querySelector('button') || x).textContent.trim()) : null; });
  await p.click('.gpm-ask-refresh button'); await p.waitForTimeout(100);
  out.said = await p.$eval('.gpm-ask-refresh .gpm-ask-note', e => e.hidden ? null : e.textContent).catch(() => null);
  const tab = async (i) => { const t = (await p.$$('[role=tab]'))[i]; if (t) { await t.click(); await p.waitForTimeout(200); } };
  await tab(2);
  out.metricsSections = await sections();
  out.intro = await p.$eval('.gpm-panel:not([hidden]) .gpm-lead-text', e => e.textContent).catch(() => null);
  out.groups = await p.$$eval('.gpm-group', e => e.map(g => Array.from(g.children).map(c => c.className.replace('gpm-group-part gpm-group-', '')).join(',')));
  out.colGroups = await p.$$eval('.gpm-col-groups th', e => e.map(x => x.textContent + ':' + x.colSpan));
  out.goalHead = await p.$$eval('.gpm-goal-head', e => e.map(x => x.textContent));
  out.metrics = await p.evaluate(() => ({titles: Array.from(document.querySelectorAll('.gpm-panel:not([hidden]) .gpm-block-title')).map(x => x.textContent),
    goal: (document.querySelector('.gpm-goal-title') || {}).textContent || null, deltaRows: document.querySelectorAll('.gpm-c-delta-row').length,
    ref: document.querySelectorAll('.gpm-c-ref').length, warnBars: document.querySelectorAll('.gpm-c-hbar.gpm-c-fill-warn').length,
    compareBars: document.querySelectorAll('.gpm-c-bars .gpm-c-hbar').length, lines: document.querySelectorAll('svg.gpm-c-line polyline').length,
    open: document.querySelectorAll('svg.gpm-c-line .gpm-c-line-dot-open').length, cols: document.querySelectorAll('.gpm-c-col').length,
    paleCols: document.querySelectorAll('.gpm-c-col-bar.gpm-c-fill-3').length, twins: document.querySelectorAll('details.gpm-c-table').length,
    marked: Array.from(document.querySelectorAll('td.gpm-ink-warn')).map(x => x.textContent), stateCols: Array.from(document.querySelectorAll('.gpm-panel:not([hidden]) th')).filter(x => x.textContent === 'Стан').length,
    colours: Array.from(document.querySelectorAll('.gpm-c-chart [style]')).map(x => x.getAttribute('style')).filter(v => /#|rgb|url|var\(/.test(v))}));
  out.more = await q('.gpm-more-link');
  out.goalAsk = await p.$$eval('.gpm-ask-beside', e => e.length);
  await p.click('[data-open=metric]'); await p.waitForTimeout(200);
  out.metric = await p.evaluate(() => ({back: (document.querySelector('.gpm-back') || {}).textContent || null, title: document.querySelector('.gpm-module-title').textContent,
    focused: document.activeElement === document.querySelector('.gpm-module-title'),
    selected: Array.from(document.querySelectorAll('[role=tab][aria-selected=true]')).map(x => x.id),
    groups: Array.from(document.querySelectorAll('.gpm-group')).map(g => Array.from(g.children).map(c => c.className.replace('gpm-group-part gpm-group-', '')).join(',')),
    value: Array.from(document.querySelectorAll('.gpm-num-value')).map(x => x.textContent.replace(/\u00a0/g, ' ')),
    lines: document.querySelectorAll('svg.gpm-c-line').length, open: document.querySelectorAll('svg.gpm-c-line .gpm-c-line-dot-open').length,
    legend: Array.from(document.querySelectorAll('.gpm-block-line .gpm-c-legend-item')).map(x => x.textContent), twins: document.querySelectorAll('details.gpm-c-table').length}));
  out.metricSections = await sections();
  const line = await p.$('svg.gpm-c-line'); if (line) { await line.focus(); await p.keyboard.press('ArrowLeft'); await p.waitForTimeout(50); }
  out.tip = await p.$eval('.gpm-c-line-wrap > .gpm-tip', e => getComputedStyle(e).display + '|' + e.textContent).catch(() => null);
  await p.click('.gpm-back'); await p.waitForTimeout(200);
  out.backAt = await p.$eval('.gpm-module-title', e => e.textContent);
  await tab(3);
  out.rhythmsSections = await sections();
  out.rhythms = await p.evaluate(() => ({meters: document.querySelectorAll('.gpm-c-meter').length, limits: document.querySelectorAll('.gpm-c-meter-limit').length,
    warn: document.querySelectorAll('.gpm-c-meter-fill.gpm-c-fill-warn').length, when: Array.from(document.querySelectorAll('.gpm-panel:not([hidden]) .gpm-item-timed .gpm-at')).map(x => x.textContent)}));
  await tab(0);
  const pay = await p.$('.gpm-products button[data-product="zorg-pay"]'); if (pay) { await pay.click(); await p.waitForTimeout(200); }
  out.payText = await p.$eval('.gpm-modules', e => e.innerText);
  out.payLead = await p.$eval('.gpm-lead-text', e => e.textContent).catch(() => null);
  out.payCounts = await counts();
  out.paySections = await sections();
  await tab(1);
  out.dirSections = await sections();
  out.dirText = await p.$eval('.gpm-modules', e => e.innerText);
  out.segs = await p.evaluate(() => ({bars: document.querySelectorAll('.gpm-panel:not([hidden]) .gpm-c-seg').length, legend: Array.from(document.querySelectorAll('.gpm-panel:not([hidden]) .gpm-c-legend-item')).map(x => x.textContent)}));
  out.overflow = await p.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  await p.setViewportSize({width: 390, height: 800}); await p.waitForTimeout(200);
  out.narrow = await p.evaluate(() => ({overflow: document.documentElement.scrollWidth - window.innerWidth,
    above: document.querySelector('header.gpm-shell').getBoundingClientRect().bottom <= document.querySelector('.gpm-modules').getBoundingClientRect().top + 1}));
  await p.setViewportSize({width: 1100, height: 800});
  await p.click('#gpm-foot-link'); await p.waitForTimeout(200);
  const switches = () => p.$$eval('.gpm-switch', e => e.map(x => x.getAttribute('data-module') + ':' + x.getAttribute('aria-checked') + (x.disabled ? ':off' : '')));
  out.settings = await p.evaluate(() => ({title: document.querySelector('.gpm-module-title').textContent, current: document.querySelector('#gpm-foot-link').getAttribute('aria-current'),
    selected: document.querySelectorAll('[role=tab][aria-selected=true]').length, fixed: Array.from(document.querySelectorAll('.gpm-switch-fixed')).map(x => x.textContent),
    names: Array.from(document.querySelectorAll('.gpm-switch-text')).map(x => x.querySelector('.gpm-item-title').textContent + ' / ' + (x.querySelector('.gpm-note') || {textContent: ''}).textContent),
    themeIn: document.querySelectorAll('.gpm-panel .gpm-theme-box .gpm-theme').length, themeAll: document.querySelectorAll('.gpm-theme').length,
    notes: Array.from(document.querySelectorAll('.gpm-item-pair-note')).length, ask: Array.from(document.querySelectorAll('.gpm-panel .gpm-ask-btn')).map(x => x.textContent),
    products: Array.from(document.querySelectorAll('.gpm-col-aside .gpm-item')).filter(x => x.querySelector('.gpm-chip')).map(x => x.querySelector('.gpm-item-title').textContent)}));
  out.settingsSections = await sections();
  out.switches = await switches();
  await p.click('.gpm-switch[data-module=rhythms]'); await p.waitForTimeout(200);
  out.off = {tabs: await q('[role=tab] .gpm-tab-title'), switches: await switches(), side: (await sections())[1], writes: await p.evaluate(() => window.__writes),
    focus: await p.evaluate(() => (document.activeElement && document.activeElement.getAttribute('data-module')) || null)};
  await p.click('.gpm-switch[data-module=rhythms]'); await p.waitForTimeout(200);
  out.on = {tabs: await q('[role=tab] .gpm-tab-title'), last: await p.evaluate(() => window.__writes[window.__writes.length - 1])};
  await p.click('.gpm-panel .gpm-ask-btn'); await p.waitForTimeout(100);
  out.saidBack = await p.$eval('.gpm-panel .gpm-ask-note', e => e.hidden ? null : e.textContent).catch(() => null);
  out.errs = errs;
  // a viewer who is not the owner, and a goal with no value yet
  const colls2 = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
  delete colls2.snapshot['goal--zorg'].data.value; delete colls2.snapshot['goal--zorg-pay'].data.value;
  const p2 = await b.newPage({viewport: {width: 1100, height: 800}, timezoneId: 'UTC'});
  p2.on('pageerror', e => errs.push(e.message));
  await p2.setContent(page.replace('<head>', '<head><script>' + fake.replace('OWNER', 'false').replace(fs.readFileSync(process.argv[3], 'utf8'), () => JSON.stringify(colls2)) + '</script>'), {waitUntil: 'load'}); await p2.waitForTimeout(500);
  await p2.click('#gpm-tab-metrics'); await p2.waitForTimeout(200);
  out.guest = {goalAsk: await p2.$$eval('.gpm-goal-ask .gpm-ask-beside .gpm-ask-btn', e => e.map(x => x.textContent))};
  await p2.click('.gpm-ask-beside .gpm-ask-btn'); await p2.waitForTimeout(100);
  out.guest.said = await p2.$eval('.gpm-ask-beside .gpm-ask-note', e => e.hidden ? null : e.textContent).catch(() => null);
  await p2.click('#gpm-foot-link'); await p2.waitForTimeout(200);
  out.guest.switches = await p2.$$eval('.gpm-switch', e => e.map(x => x.disabled));
  out.guest.note = await p2.$eval('.gpm-block-switches .gpm-ask-note', e => e.textContent).catch(() => null);
  out.guest.writes = await p2.evaluate(() => window.__writes.length);
  await b.close(); console.log('PW ' + JSON.stringify(out));
})();
""")
        cj = os.path.join(d, "colls.json")
        with open(cj, "w", encoding="utf-8") as f:
            json.dump(colls, f, ensure_ascii=False)
        pr = subprocess.run(["node", js, app, cj], capture_output=True, text=True, timeout=120, env=dict(os.environ, NODE_PATH=npm))
        br = {}
        for line in pr.stdout.splitlines():
            if line.startswith("PW "):
                br = json.loads(line[3:])
        check("5.1 the browser pass ran without a page error", br.get("errs") == [], pr.stdout[-600:] + pr.stderr[-600:])
        check("5.2 five modules in the rail, in the profile's order and in Ukrainian; the settings and the metric's screen are not among them",
              br.get("tabs") == ["Сьогодні", "Напрямки", "Метрики", "Ритми", "Контекст"], br.get("tabs"))
        rl = br.get("rail") or {}
        check("5.3 the rail: the modules stand in the header as a column at the left, with the plugin's mark as a PNG of the page itself",
              rl.get("cls") is True and rl.get("inHeader") is True and rl.get("vertical") == "vertical" and rl.get("left") is True
              and rl.get("logo") == "data:image/png;base64,", rl)
        tt = br.get("todayTitles") or []
        check("5.4 today: what waits first, the day, the focuses; the signals and the sources' freshness stand in the side column",
              tt == ["Сьогодні", "Чекає на тебе", "День за часом", "Фокуси дня", "Сигнали", "Свіжість джерел"]
              and br.get("aside") == ["Сигнали", "Свіжість джерел"], (tt, br.get("aside")))
        # every fixture is written for both products, so a count here is twice the fixture's
        check("5.5 the opening sentence is counted by the shell: four rows wait, four signals (the stale source beside them is not one) in the modules "
              "their rows name, the calendar's now; a counter says its module's own word",
              br.get("lead") == "Чотири речі чекають на тебе. Є чотири сигнали: у метриках і в напрямках. Зараз час фокусу, до 15:00."
              and br.get("counts") == ["4", "2 застигли", "2 сигнали", "4 застаріли", ""], (br.get("lead"), br.get("counts")))
        check("5.16 the rail's foot says the time of the data and the run's sentence on the next one, over the ask for fresh data and the settings; "
              "the day's head says its source and when it was read",
              br.get("fresh") == "Дані від 10:00. " + fixture("refresh-note")["text"]
              and br.get("foot") == ["gpm-fresh:" + (br.get("fresh") or ""), "gpm-ask:Оновити зараз", "gpm-foot-link:Налаштування"] and "День за часом|calendar, 10:00|0" in (br.get("today") or []), (br.get("fresh"), br.get("today")))
        check("5.17 a section holds the products together: one head per block, no product chip on it; a row shows the product it names, "
              "a row that names none shows none; a pair row sets its value to the right, in the colour of its attention",
              br.get("today") == ["||0", "Чекає на тебе||0", "День за часом|calendar, 10:00|0", "Фокуси дня||0", "Сигнали||0", "Свіжість джерел||0"]
              and br.get("rowChips") == [1] * 6 + [0] * 6
              and br.get("pairs") == ["Calendar=09:40", "Issue tracker=09:55", "Funnel tracker=Увага: 16.11, 10 days ago!"] * 2,
              (br.get("today"), br.get("rowChips"), br.get("pairs")))
        dy = br.get("day") or {}
        check("5.6 the day, per product: three blocks on the strip, one of them focus time, the rows in time order, the running one with what is left of it",
              dy.get("blocks") == 6 and dy.get("focus") == 2
              and dy.get("rows") == ["11:00–11:45 Checkout sync", "13:00–15:00 Focus time", "15:00–16:00 Weekly planning"] * 2
              and "Зараз 13:30" in dy.get("text", "") and "Триває, лишилось 1 год 30 хв." in br.get("todayText", ""), dy)
        check("5.7 with all products the rows of both are there; the switch has «Усі» and both products",
              "A mention in ZORG-214" in br.get("todayText", "") and "A review request on the checkout" in br.get("todayText", "")
              and br.get("switch") == ["Усі", "Zorg", "Zorg Pay"], br.get("switch"))
        mt = br.get("metrics") or {}
        check("5.8 metrics: the module's sentence, the goal's band under the product and «Ціль», then a section per group and product "
              "named by its documents, with the product and the period at the right; the way to the screen of one metric last",
              br.get("intro") == fixture("metrics-lead")["text"] and mt.get("goal") == "Orders a week" and br.get("goalHead") == ["ZorgЦіль", "Zorg PayЦіль"]
              and br.get("metricsSections") == ["||0", "||0", "Conversion to order|Zorgthe last 4 weeks|1", "Conversion to order|Zorg Paythe last 4 weeks|1",
                                                "Release pace|Zorg|1", "Release pace|Zorg Pay|1", "Докладніше||0"] and br.get("more") == ["Orders"],
              (br.get("metricsSections"), br.get("goalHead"), br.get("more")))
        check("5.18 a group stands side by side: the two charts over their table, the number beside its columns; the table's columns under a shared head",
              br.get("groups") == ["bars,bars,table"] * 2 + ["number,bars"] * 2 and br.get("colGroups") == ["Conversion:2"] * 2,
              (br.get("groups"), br.get("colGroups")))
        check("5.9 the charts draw the fixtures: 8 change rows with 2 threshold lines per product pair and one bar of attention, 8 compared bars, 4 columns with a pale one; the line stands on the metric's own screen",
              mt.get("deltaRows") == 8 and mt.get("ref") == 8 and mt.get("warnBars") == 2 and mt.get("compareBars") == 8
              and mt.get("lines") == 0 and mt.get("cols") == 8 and mt.get("paleCols") == 2, mt)
        check("5.10 a chart has the same numbers as a table of its own unless its group shows the table beside it; a cell says its own attention, "
              "with no state column; no colour comes from a document",
              mt.get("twins") == 2 and mt.get("marked") == ["Увага: −12.0%"] * 2 and mt.get("stateCols") == 0 and mt.get("colours") == [], mt)
        check("5.11 the line answers the keyboard: the arrow moves to the week before, its value in the tip",
              (br.get("tip") or "").startswith("block|16.11") and "1 410" in (br.get("tip") or "").replace("\u00a0", " "), br.get("tip"))
        ms = br.get("metric") or {}
        check("5.19 the screen of one metric opens from the metrics module and stays under its entry in the rail: the way back, the metric's own name as the "
              "heading with the focus on it, the number beside its line per product, the lines by segment with a legend, the last periods as a table",
              ms.get("back") == "Усі метрики" and ms.get("title") == "Orders" and ms.get("focused") is True and ms.get("selected") == ["gpm-tab-metrics"]
              and ms.get("groups") == ["number,line"] * 2 and ms.get("lines") == 4 and ms.get("open") == 2 and ms.get("legend") == ["Web", "App"] * 2
              and br.get("metricSections") == ["||0", "Orders by week|Zorg8 weeks|1", "Orders by week|Zorg Pay8 weeks|1", "За розрізами||0", "Останні періоди таблицею|4 weeks|0"]
              and br.get("backAt") == "Метрики", (ms, br.get("metricSections"), br.get("backAt")))
        check("5.20 a number of five digits and more is written with its thousands apart", ms.get("value") == ["61 200"] * 2, ms.get("value"))
        st = br.get("settings") or {}
        check("5.21 the settings open from the rail's foot, which then is the current place: a switch per module of the rail with what it shows, the home one "
              "always on; the theme switch stands here and nowhere else; the products and the data's updates beside",
              st.get("title") == "Налаштування" and st.get("current") == "page" and st.get("selected") == 0 and st.get("fixed") == ["Завжди увімкнено"]
              and [n.split(" / ")[0] for n in st.get("names") or []] == ["Сьогодні", "Напрямки", "Метрики", "Ритми", "Контекст"]
              and all(n.split(" / ")[1] for n in st.get("names") or []) and st.get("themeIn") == 1 and st.get("themeAll") == 1
              and br.get("settingsSections") == ["||0", "Модулі|5 увімкнено|0", "Тема||0", "Продукти|2 products|0", "Оновлення даних||0"]
              and br.get("switches") == ["directions:true", "metrics:true", "rhythms:true", "context:true"] and st.get("notes") == 4
              and st.get("ask") == ["Відкликати згоду"] and st.get("products") == ["Zorg", "Zorg Pay"] * 2, (st, br.get("settingsSections"), br.get("switches")))
        off, on = br.get("off") or {}, br.get("on") or {}
        check("5.22 a switch turned off writes the owner's config/app, takes the module out of the rail and keeps the focus; turned on, the module is back",
              off.get("tabs") == ["Сьогодні", "Напрямки", "Метрики", "Контекст"] and off.get("side") == "Модулі|4 увімкнено|0" and off.get("focus") == "rhythms"
              and off.get("writes") == ['config/app {"v":1,"modules":[{"id":"rhythms","on":false}],"custom":[]}']
              and on.get("tabs") == ["Сьогодні", "Напрямки", "Метрики", "Ритми", "Контекст"]
              and on.get("last") == 'config/app {"v":1,"modules":[{"id":"rhythms","on":true}],"custom":[]}', (off, on))
        said = [br.get("said") or "", br.get("saidBack") or "", (br.get("guest") or {}).get("said") or ""]
        check("5.23 a button for Claude starts nothing by itself: it hands over the profile's phrase — copied, or said when the page may not copy",
              all("«%s»" % w in t and (t.startswith("Скопійовано: ") or t.startswith("Скажи Claude: "))
                  for w, t in zip(("Онови пульт", "Відклич згоду на пульт", "Задай базу для головної цілі пульта"), said)), said)
        gs = br.get("guest") or {}
        check("5.24 a goal with a value shows no ask; one without shows it in its band; a viewer who is not the owner sees the switches closed, "
              "is told why, and writes nothing",
              br.get("goalAsk") == 0 and gs.get("goalAsk") == ["Задати базу"] and gs.get("switches") == [True] * 4
              and gs.get("note") == "Змінювати модулі може лише власник." and gs.get("writes") == 0, (br.get("goalAsk"), gs))
        rh = br.get("rhythms") or {}
        check("5.12 rhythms: one table for the products, a meter per source with the limit marked, the stale one in the colour of attention; "
              "the journal says the time alone for today",
              br.get("rhythmsSections") == ["||0", "Джерела||0", "Оновлення пульта||0"]
              and rh.get("meters") == 4 and rh.get("limits") == 4 and rh.get("warn") == 2 and rh.get("when") == ["10:00", "09:00"] * 2, rh)
        check("5.13 a product picked: its rows stay, the other product's go; the sentence and the counters are counted again",
              "A review request on the checkout" in br.get("payText", "") and "A mention in ZORG-214" not in br.get("payText", "")
              and br.get("payLead") == "Одна річ чекає на тебе. Сигналів немає. Зараз час фокусу, до 15:00." and br.get("payCounts") == ["1", "", "", "", ""]
              and "Weekly planning" not in br.get("payText", "") and "Checkout sync" in br.get("payText", ""),
              (br.get("payLead"), br.get("payCounts"), br.get("payText", "")[:300]))
        sg = br.get("segs") or {}
        check("5.14 the directions module shows the table with a bar of parts and its legend, and the list under it, for the picked product",
              "ZPAY-40" in br.get("dirText", "") and "Gift cards" in br.get("dirText", "") and "ZORG-100" not in br.get("dirText", "")
              and sg.get("bars") == 1 and sg.get("legend") == ["Closed", "In work", "No movement over 14 days"]
              and br.get("dirSections") == ["||0", "У роботі||0", "На паузі й закриті|2 directions|0"] and "ZPAY-12, closed" in br.get("dirText", ""),
              (sg, br.get("dirSections"), br.get("dirText", "")[:300]))
        nr = br.get("narrow") or {}
        check("5.15 the page never scrolls sideways, wide or narrow; in a narrow window the rail folds over the modules",
              br.get("overflow") == 0 and nr.get("overflow") == 0 and nr.get("above") is True, (br.get("overflow"), nr))

print("\nRESULT: %s (%d failed)" % ("GREEN ✅" if not fails else "RED ❌", fails))
sys.exit(1 if fails else 0)
