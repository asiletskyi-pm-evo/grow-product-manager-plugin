#!/usr/bin/env python3
"""TC-pm-os — the profile `pm-os` of references/app-profiles.yaml, its sections and references/pm-os-protocol.md.

The profile passes the shell's check and has the five modules of the protocol; every section a block reads has a fixture
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
MODULES = ["today", "directions", "metrics", "rhythms", "context"]
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


def shaped(block, data):
    """True when `data` has what the block shows (references/pm-os-protocol.md §2)."""
    if block == "table":
        return (isinstance(data.get("columns"), list) and data["columns"] and isinstance(data.get("rows"), list)
                and all(set(c) == {"key", "title"} for c in data["columns"]) and all(isinstance(r, dict) for r in data["rows"]))
    if block in ("list", "feed"):
        items = data.get("items")
        ok = isinstance(items, list) and items and all(isinstance(i, dict) and i.get("title") for i in items)
        return bool(ok and (block == "list" or all(i.get("at") for i in items)))
    if block == "number":
        return isinstance(data.get("value"), (int, float)) and not isinstance(data.get("value"), bool)
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
check("1.2 five modules, in the protocol's order", [m.get("id") for m in mods] == MODULES, [m.get("id") for m in mods])
check("1.3 today is the home module, and the only one", [m.get("id") for m in mods if m.get("home")] == ["today"])
check("1.4 every module is composed (a blocks list), none takes a map or the page's edits",
      all(isinstance(m.get("blocks"), list) and m["blocks"] and "block" not in m for m in mods)
      and not any(b.get("block") == "map" or str(b.get("source", "")).startswith("@") for m in mods for b in m.get("blocks") or []))
pairs = [(m["id"], b.get("block"), b.get("source")) for m in mods for b in m.get("blocks") or []]
sources = [s for _, _, s in pairs]
check("1.5 a section is read by one block only", len(sources) == len(set(sources)), sources)
check("1.6 today opens with what needs the user", pairs[:1] == [("today", "feed", "needs-you")], pairs[:1])
check("1.7 every title is in both languages",
      all(set((x.get("title") or {})) == set(sh.LANGS) for m in mods for x in [m] + list(m.get("blocks") or [])))
check("1.8 no full access, no commands, no permission beyond the shell's", prof.get("level") == "app" and prof.get("commands") == []
      and set(prof.get("permissions") or []) <= set(sh.PERMISSIONS))
check("1.9 the menu names the modules only, then the action to open the chat",
      prof.get("menu") == MODULES + [{"action": "open-in-claude"}], prof.get("menu"))
check("1.10 a connector is a role and a placeholder, never a value",
      all(set(c) == {"role", "needs"} and re.fullmatch(r"<[a-z][a-z0-9_]*>", c["needs"]) for c in prof.get("connectors") or []))

# ---- 2. the sections: fixtures and the protocol ---------------------------------------------------------------------
have = sorted(f[len("zorg-"):-len(".json")] for f in os.listdir(FIX) if f.startswith("zorg-") and f.endswith(".json"))
check("2.1 a fixture for every section the profile reads, and no other", have == sorted(sources), (have, sorted(sources)))
bad = [(s, b) for _, b, s in pairs if s in have and not shaped(b, fixture(s))]
check("2.2 every fixture has the shape of the block that shows it", not bad, bad)
with open(PROTOCOL, encoding="utf-8") as f:
    protocol = f.read()
rows = re.findall(r"^\| `([a-z-]+)` \| `([a-z0-9.-]+)` \| ([a-z]+) \|", protocol, re.M)
check("2.3 the protocol's table of sections is the profile's blocks: module, section, block, in order",
      rows == [(m, s, b) for m, b, s in pairs], (rows, pairs))
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
    args = ["snapshot", "--profile", "pm-os", "--at", MADE, "--out", os.path.join(d, "db")]
    for p in PRODUCTS:
        args += ["--product", "%s:%s:%s" % (p["id"], p["label"], p["color"])]
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
    check("4.2 the page carries the five modules", [x.get("id") for x in shown.get("modules") or []] == MODULES)
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
    const db = {collection: (c) => ({onSnapshot: (next) => { setTimeout(() => next(qs(c)), 0); return () => {}; }})};
    window.claude = {use: async (n) => (n === 'db' ? db : null)};`;
  const html = fs.readFileSync(process.argv[2], 'utf8').replace('<head>', '<head><script>' + fake + '</script>');
  const b = await chromium.launch(); const out = {};
  const p = await b.newPage({viewport: {width: 1100, height: 800}});
  const errs = []; p.on('pageerror', e => errs.push(e.message));
  await p.setContent(html, {waitUntil: 'load'}); await p.waitForTimeout(500);
  const q = (sel) => p.$$eval(sel, e => e.map(x => x.textContent.trim()));
  const visible = (sel) => p.$$eval(sel, e => e.filter(x => x.offsetParent !== null).map(x => x.textContent.trim()));
  out.tabs = await q('[role=tab]');
  out.todayTitles = await visible('.gpm-modules h2, .gpm-modules h3');
  out.todayText = await p.$eval('.gpm-modules', e => e.innerText);
  out.switch = await q('.gpm-products button');
  const pay = await p.$('.gpm-products button[data-product="zorg-pay"]'); if (pay) { await pay.click(); await p.waitForTimeout(200); }
  out.payText = await p.$eval('.gpm-modules', e => e.innerText);
  const tabs = await p.$$('[role=tab]'); if (tabs[1]) { await tabs[1].click(); await p.waitForTimeout(200); }
  out.dirText = await p.$eval('.gpm-modules', e => e.innerText);
  out.overflow = await p.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  out.errs = errs;
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
        check("5.2 five tabs, in the profile's order and in Ukrainian",
              br.get("tabs") == ["Сьогодні", "Напрямки", "Метрики", "Ритми", "Контекст"], br.get("tabs"))
        tt = br.get("todayTitles") or []
        order = [t for t in tt if t in ("Потребує тебе", "Фокуси дня", "Зустрічі дня", "Сигнали метрик")]
        check("5.3 today shows its four blocks one under another, what needs the user first",
              order == ["Потребує тебе", "Фокуси дня", "Зустрічі дня", "Сигнали метрик"], tt)
        check("5.4 with all products the rows of both are there",
              "A mention in ZORG-214" in br.get("todayText", "") and "A review request on the checkout" in br.get("todayText", ""))
        check("5.5 the switch has «Усі» and both products", br.get("switch") == ["Усі", "Zorg", "Zorg Pay"], br.get("switch"))
        check("5.6 a product picked: its rows stay, the other product's go",
              "A review request on the checkout" in br.get("payText", "") and "A mention in ZORG-214" not in br.get("payText", ""),
              br.get("payText", "")[:400])
        check("5.7 the directions tab shows the table and the list under it, for the picked product",
              "ZPAY-40" in br.get("dirText", "") and "Gift cards" in br.get("dirText", "") and "ZORG-100" not in br.get("dirText", ""),
              br.get("dirText", "")[:400])
        check("5.8 the page never scrolls sideways", br.get("overflow") == 0, br.get("overflow"))

print("\nRESULT: %s (%d failed)" % ("GREEN ✅" if not fails else "RED ❌", fails))
sys.exit(1 if fails else 0)
