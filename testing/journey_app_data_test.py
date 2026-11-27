#!/usr/bin/env python3
"""TC-journey-4130-app — the journey map inside the app (v4.13.0, references/journey-protocol.md §9, §13, §14).

The fictional «Zorg» maps (testing/fixtures/journey/ and its nest/) are copied into a temp folder.

- `journey_map.py app-data` (§9): one map — with its child maps to three levels — as the data of one snapshot section
  `map.<slug>`; only what the page shows (the page's own filters: page_worthy, page-safe texts), no person; the rows
  and the digest of each grid the same as the attributes `render-html` writes; a map over 256 KiB is refused, nothing
  written; the fixture testing/fixtures/app/zorg-map.json is this command's own output.
- `journey_portfolio.py app-data` (§13): the portfolio as a `table` block's data and the funnel of the newest funnel-level
  health-check snapshot as a `chart` block's data — numbers, never a person.
- `app_shell.py wrap` with a map block: CSS_EDIT in the style, EDIT as a fixed non-executed text, the edit bar as a
  template — and none of them without a map block.
- a browser pass (when Playwright is installed): `pw_map_parity` — the DOM map.js draws from the data and the DOM of
  `render-html` give the same (row id, stage, lane, parent, code, target, locked) lists and the same digest on every
  grid, child maps included; `pw_map_edit_shared` — a text edit in the app writes the same document into `edits` as
  the v4.12.0 page writes; `pw_stale_map_locks_edit` — edits of another version of a map in the database lock that
  map's editing with a hint; several maps, one at a time; data is text; a new snapshot while open locks the old map.
Stdlib only (the browser pass skipped without Playwright); run from the repo root:

  env -u GROW_PM_CONTEXT_PATH -u GROW_PM_PROVIDER_PATHS python3 testing/journey_app_data_test.py
"""
import json, os, re, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
JM = os.path.join(SCRIPTS, "journey_map.py")
JP = os.path.join(SCRIPTS, "journey_portfolio.py")
SH = os.path.join(SCRIPTS, "app_shell.py")
FIX = os.path.join(ROOT, "testing", "fixtures", "journey")
APPFIX = os.path.join(ROOT, "testing", "fixtures", "app")
sys.path.insert(0, SCRIPTS)
import journey_map as jm  # noqa: E402
import journey_portfolio as jp  # noqa: E402

fails = 0


def check(name, cond, detail=""):
    global fails
    fails += not cond
    print(("✅" if cond else "❌"), name, ("" if cond else "-> " + str(detail)[:900]))


SAFE_HOME = tempfile.mkdtemp(prefix="journey-app-home-")


def run(script, prefix, *args, timeout=60):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GROW_PM_")}
    env["HOME"] = SAFE_HOME
    try:
        p = subprocess.run([sys.executable, script] + list(args), capture_output=True, text=True, env=env, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, "timeout after %ds" % timeout, {}
    res = {}
    for line in p.stdout.splitlines():
        if line.startswith(prefix + " "):
            res = json.loads(line[len(prefix) + 1:])
    return p.returncode, p.stdout + p.stderr, res


def jmr(*a):
    return run(JM, "JOURNEY_RESULT", *a)


def jpr(*a):
    return run(JP, "PORTFOLIO_RESULT", *a)


def text(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def write(p, s):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="") as f:
        f.write(s)


def jload(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def keys_deep(node, out=None):
    out = set() if out is None else out
    if isinstance(node, dict):
        for k, v in node.items():
            out.add(k)
            keys_deep(v, out)
    elif isinstance(node, list):
        for v in node:
            keys_deep(v, out)
    return out


def frames_of(page):
    """[(map, digest, [row ids])] of a render-html page, in its order — read from the attributes EDIT reads."""
    out = []
    for m in re.finditer(r'<div class="wrap" tabindex="0" data-map="([^"]+)" data-digest="([^"]+)">(.*?)</table></div>', page, re.S):
        out.append((m.group(1), m.group(2), re.findall(r'<div class="item [^"]*" data-row="([^"]+)"', m.group(3))))
    return out


def frames_data(data):
    """The same list from an app-data object: the map itself, then its child maps depth first (the page's order)."""
    out = [(data["map"], data["table_sig"], [r["id"] for r in data["rows"]])]

    def walk(n):
        for k in n["children"]:
            out.append((k["map"], k["table_sig"], [r["id"] for r in k["rows"]]))
            walk(k)
    walk(data["tree"])
    return out


def page_order(data_rows, stages, lanes):
    """Row ids as the grid shows them: lane by lane, stage by stage, the note's order inside a cell."""
    return [r["id"] for ln in lanes for s in stages for r in data_rows if r["lane"] == ln and r["stage"] == s]


d = tempfile.mkdtemp(prefix="journey-app-test-")
try:
    flat = os.path.join(d, "flat", "journey-first-order.md")
    write(flat, text(os.path.join(FIX, "journey-first-order.md")))
    nest = os.path.join(d, "nest")
    shutil.copytree(os.path.join(FIX, "nest"), nest)
    shutil.rmtree(os.path.join(nest, "golden"))
    root = os.path.join(nest, "journey-first-order.md")

    # 1. app-data: the command and its result line
    out1 = os.path.join(d, "a1.json")
    rc, out, res = jmr("app-data", "--note", flat, "--lang", "uk", "--out", out1)
    data = jload(out1) if os.path.exists(out1) else {}
    check("1.1 app-data: exit 0; the result line names the section map.<slug>, the map, its product, rows, not shown, children, deeper",
          rc == 0 and res.get("ok") is True and res.get("section") == "map.first-order" and res.get("map") == "journey-first-order"
          and res.get("product") == "zorg" and set(res) >= {"ok", "out", "bytes", "section", "map", "product", "rows", "not_shown", "children", "deeper"}
          and res.get("bytes") == os.path.getsize(out1), out[-400:])
    check("1.2 the file holds the brief's object: v 1, map, product, table_sig, lang, stages, lanes, rows, health, tree, above",
          data.get("v") == 1 and set(data) >= {"v", "map", "product", "table_sig", "lang", "stages", "lanes", "rows", "health", "tree", "above"}
          and data.get("lang") == "uk" and data.get("table_sig") == jm.table_sig(jm.load(flat))["table"]
          and set(data.get("tree") or {}) >= {"children", "deeper"} and isinstance(data.get("above"), list), sorted(data))
    row0 = (data.get("rows") or [{}])[0]
    check("1.3 a row: id, stage, lane, text, parent, code, target and locked (booleans)", set(row0) >= {
        "id", "stage", "lane", "text", "parent", "code", "target", "locked"} and isinstance(row0.get("target"), bool)
          and isinstance(row0.get("locked"), bool), row0)
    rich = os.path.join(d, "rich", "journey-first-order.md")
    write(rich, text(flat).replace("health: []\n", 'health:\n  - date: "2026-10-05"\n    score: 71\n    snapshot: "2026-10-05.md"\n'
                                   '  - date: "2026-11-02"\n    score: 68.5\n    snapshot: "2026-11-02.md"\n')
          .replace("| a1 | s1 |", "| q1 | s1 | | action | Без джерела | | | | | | | |\n"
                   "| q2 | s2 | | pain | Вигаданий біль | | | | | персона | simulated | 2026-10-01 |\n"
                   "| q3 | s9 | | action | Поза етапами | | | | | walkthrough | observed | 2026-10-12 |\n| a1 | s1 |", 1))
    rc, out, res = jmr("app-data", "--note", rich, "--lang", "uk", "--out", os.path.join(d, "rich.json"))
    rdata = jload(os.path.join(d, "rich.json")) if os.path.exists(os.path.join(d, "rich.json")) else {}
    n1 = jm.load(rich)
    declared = [s["id"] for s in n1["stages"]]
    worthy = [r["id"] for r in n1["rows"] if not r["gap"] and jm.page_worthy(r, declared)]
    hidden = [r["id"] for r in n1["rows"] if not r["gap"] and not jm.page_worthy(r, declared)]
    check("1.4 only the rows the page shows: page_worthy; the others counted, never sent", sorted(hidden) == ["q1", "q2", "q3"]
          and sorted(r["id"] for r in rdata.get("rows", [])) == sorted(worthy) and res.get("not_shown") == 3 and res.get("rows") == len(worthy)
          and "q1" not in json.dumps(rdata) and "Вигаданий" not in json.dumps(rdata, ensure_ascii=False) and "3" in rdata.get("not_shown_text", ""), (hidden, res))
    locked = {r["id"]: r["locked"] for r in data.get("rows", [])}
    check("1.5 the health-check, metric and anomaly rows are locked, the others not",
          all(locked[i] == bool(jm._locked(r)) for i, r in ((r["id"], r) for r in n1["rows"] if r["id"] in locked)) and any(locked.values())
          and not all(locked.values()), locked)
    check("1.6 the lanes are the ten of §2 in their order; the stages are the note's", [l.get("id") for l in data.get("lanes", [])] == list(jm.LANE_IDS)
          and [s.get("id") for s in data.get("stages", [])] == declared, (data.get("lanes"), data.get("stages")))
    blob1 = json.dumps(data, ensure_ascii=False)
    check("1.7 no person: no owner key, the owner's words nowhere", not keys_deep(data) & {"owner", "author", "email", "e-mail", "assignee", "person", "reporter"}
          and (n1["owner"] or "x") not in blob1, sorted(keys_deep(data)))
    check("1.8 the health points and their trend", [p.get("score") for p in (rdata.get("health") or {}).get("points", [])] == [71, 68.5]
          and ((rdata.get("health") or {}).get("trend") or {}).get("delta") == -2.5 and (data.get("health") or {}).get("points") == []
          and (data.get("health") or {}).get("trend") is None, (rdata.get("health"), data.get("health")))
    again = os.path.join(d, "a1b.json")
    jmr("app-data", "--note", flat, "--lang", "uk", "--out", again)
    check("1.9 the same note, the same bytes (no date in the data)", os.path.exists(again) and text(again) == text(out1), "")
    check("1.10 testing/fixtures/app/zorg-map.json is this command's own output for the Zorg fixture note",
          os.path.exists(os.path.join(APPFIX, "zorg-map.json")) and jload(os.path.join(APPFIX, "zorg-map.json")) == data, "")
    out_en = os.path.join(d, "a1en.json")
    rc, out, res = jmr("app-data", "--note", flat, "--lang", "en", "--out", out_en)
    den = jload(out_en) if os.path.exists(out_en) else {}
    check("1.11 --lang en: the lanes' and the cells' words in English", rc == 0 and den.get("lang") == "en"
          and (den.get("lanes") or [{}])[3].get("title") == "Pains" and "s3 · pains" in json.dumps(den, ensure_ascii=False), out[-300:])

    # test_app_data_page_safe
    hostile = os.path.join(d, "hostile", "journey-first-order.md")
    secret = "glpat-" + "Qw8" * 7
    write(hostile, text(flat).replace("| p2 | s3 | | pain | Не видно вартості доставки до оформлення |",
                                      "| p2 | s3 | | pain | Не видно вартості <b>доставки</b> https://evil.example/p bea@zorg.example |")
          .replace("| e2 | s4 | | experience | Тривога: чи не задорого вийде з доставкою |",
                   "| e2 | s4 | | experience | Тривога токен %s |" % secret)
          .replace('name: "Кошик"', 'name: "Кошик https://evil.example/s"'))
    hp, ho = os.path.join(d, "hostile", "page.html"), os.path.join(d, "hostile", "data.json")
    jmr("render-html", "--note", hostile, "--out", hp, "--lang", "uk")
    rc, out, res = jmr("app-data", "--note", hostile, "--lang", "uk", "--out", ho)
    hd = text(ho) if os.path.exists(ho) else ""
    hpage = text(hp) if os.path.exists(hp) else ""
    check("1.12 test_app_data_page_safe: a link, a contact and a secret in a row and a stage are not in the JSON — as on the page",
          rc == 0 and hd and "evil.example" not in hd and "bea@zorg" not in hd and secret not in hd and "glpat-" not in hd
          and "evil.example" not in hpage and secret not in hpage and "[link removed]" in hd and "[hidden:" in hd, re.findall(r".{20}(?:evil|bea@|glpat).{20}", hd)[:3])
    check("1.13 HTML in a row's text stays text in the data (the page escapes it; map.js sets it as text)",
          "<b>доставки</b>" in hd and "&lt;b&gt;доставки&lt;/b&gt;" in hpage, "")

    # test_app_data_rows_match_page — the flat map and the tree of three levels
    pf = os.path.join(d, "flat", "page.html")
    jmr("render-html", "--note", flat, "--out", pf, "--lang", "uk")
    fp = frames_of(text(pf)) if os.path.exists(pf) else []
    check("1.14 test_app_data_rows_match_page: the row ids and table_sig of app-data = the page's attributes, in the page's order",
          fp and data and [(m, dg, ids) for m, dg, ids in fp] == [(data["map"], data["table_sig"], page_order(
              data["rows"], [s["id"] for s in data["stages"]], [l["id"] for l in data["lanes"]]))], (fp, data.get("table_sig")))
    tp, to = os.path.join(d, "nest-page.html"), os.path.join(d, "nest-data.json")
    jmr("render-html", "--note", root, "--out", tp, "--lang", "uk")
    rc, out, res = jmr("app-data", "--note", root, "--lang", "uk", "--out", to)
    td = jload(to) if os.path.exists(to) else {"map": "", "table_sig": "", "rows": [], "tree": {"children": []}}
    ftp = frames_of(text(tp)) if os.path.exists(tp) else []
    fdt = frames_data(td) if td.get("map") else []
    check("1.15 the tree: every grid's map, digest and row set the same — the root, its children, a grandchild (three levels)",
          rc == 0 and [m for m, _, _ in ftp] == ["journey-first-order", "journey-shipping", "journey-payment", "journey-3ds"]
          and [(m, dg, sorted(ids)) for m, dg, ids in ftp] == [(m, dg, sorted(ids)) for m, dg, ids in fdt], (ftp, fdt))
    check("1.16 the reference past the depth is a name only: in deeper, no grid, no rows", res.get("children") == 3
          and res.get("deeper") == ["journey-3ds-retry"] and "journey-3ds-retry" not in [m for m, _, _ in fdt], res)
    check("1.17 a child map in the data names its note and level, never its owner", td.get("tree", {}).get("children")
          and all(set(k) >= {"note", "journey", "level", "map", "table_sig", "stages", "rows", "children", "deeper"}
                  for k in td["tree"]["children"]) and "owner" not in keys_deep(td)
          and "Команда платежів Zorg" not in json.dumps(td, ensure_ascii=False), [sorted(k) for k in td.get("tree", {}).get("children", [])])
    rc, out, res = jmr("app-data", "--note", os.path.join(nest, "journey-payment.md"), "--lang", "uk", "--out", os.path.join(d, "pay.json"))
    pdata = jload(os.path.join(d, "pay.json")) if os.path.exists(os.path.join(d, "pay.json")) else {}
    check("1.18 a child's own app-data names the maps above it", rc == 0 and [a.get("note") for a in pdata.get("above", [])] == ["journey-first-order"]
          and res.get("section") == "map.payment", (res, pdata.get("above")))

    # the cap and the arguments
    big = os.path.join(d, "big", "journey-first-order.md")
    rows = "".join("| x%d | s1 | | action | %s | | | | | walkthrough 2026-10-12, крок 1 | observed | 2026-10-12 |\n" % (i, "Довгий текст " * 40)
                   for i in range(700))
    write(big, text(flat).replace("| a1 | s1 |", rows + "| a1 | s1 |", 1))
    bo = os.path.join(d, "big", "data.json")
    rc, out, res = jmr("app-data", "--note", big, "--lang", "uk", "--out", bo)
    check("1.19 a map over 256 KiB: ok false, nothing written, the size named", res.get("ok") is False and not os.path.exists(bo)
          and (res.get("bytes") or 0) > 256 * 1024 and "256" in res.get("error", ""), out[-300:])
    rc, out, res = jmr("app-data", "--note", os.path.join(FIX, "hypotheses-zorg.md"), "--out", os.path.join(d, "x.json"))
    check("1.20 a note that is no journey map: exit 2 with the result line", rc == 2 and res.get("ok") is False, out[-300:])
    check("1.21 COMMANDS has app-data; checks 28 and 30 are clean on the repository", "app-data" in jm.COMMANDS and "app-data" in jp.APP_COMMANDS
          and jm.check_protocol(ROOT) == [] and jp.check_protocol(ROOT) == [], (jm.check_protocol(ROOT), jp.check_protocol(ROOT)))
    rc, out, res = jmr("app-data", "--note", root, "--lang", "uk", "--out", os.path.join(d, "slug.json"), "--map", os.path.join(nest, "journey-payment.md"))
    check("1.22 --map limits the candidates as for render-html", rc == 0 and res.get("children") == 1, res)

    import app_shell as sh
    names = {n: jm.app_section(n) for n in ("journey-first-order.md", "journey-Оплата.md", "journey-" + "very-long-" * 12 + ".md",
                                            "Journey_Pay By Card.md", "journey-...md")}
    check("1.23 the section name fits app_shell's SECTION for any note name: map.first-order; a name with no Latin letters by a digest",
          names["journey-first-order.md"] == "map.first-order" and all(sh.SECTION.match(v) for v in names.values())
          and names["journey-Оплата.md"].startswith("map.m") and names["Journey_Pay By Card.md"] == "map.journey-pay-by-card", names)

    # 2. journey_portfolio.py app-data
    pdir = os.path.join(d, "port")
    snapd = os.path.join(d, "hc")
    shutil.copytree(os.path.join(FIX, "health-checks"), snapd)
    write(os.path.join(snapd, "2026-11-20-map.md"), text(os.path.join(snapd, "2026-11-02.md")).replace(
        "date: 2026-11-02\n", "date: 2026-11-20\nmap: \"[[journey-first-order]]\"\n").replace("health_score: 71", "health_score: 12"))
    rc, out, res = jpr("app-data", "--product", "zorg", "--dir", os.path.join(FIX, "portfolio", "journeys", "zorg"),
                       "--snapshots", snapd, "--today", "2026-11-24", "--lang", "uk", "--out-dir", pdir)
    po = jload(os.path.join(pdir, "portfolio.json")) if os.path.exists(os.path.join(pdir, "portfolio.json")) else {}
    fu = jload(os.path.join(pdir, "funnel.json")) if os.path.exists(os.path.join(pdir, "funnel.json")) else {}
    check("2.1 portfolio app-data: exit 0, portfolio.json and funnel.json written; the result names them",
          rc == 0 and res.get("ok") is True and res.get("funnel") is True and res.get("maps") == len(po.get("rows", [])) and po
          and res.get("out_dir") == pdir and "weakest" in res, out[-400:])
    check("2.2 portfolio.json is a table block's data: four columns in Ukrainian — the health a meter (scale 100, mark 75, its number beside), the change a number",
          [(c["key"], c["title"]) for c in po.get("columns", [])] == [("journey", "Шлях"), ("score", "Здоров'я"), ("delta", "Зміна"), ("state", "Стан")]
          and po["columns"][1].get("kind") == "meter" and po["columns"][1].get("scale") == 100 and po["columns"][1].get("limit") == 75
          and po["columns"][1].get("sub") == "score_text" and po["columns"][2].get("kind") == "num", po.get("columns"))
    prow = (po.get("rows") or [{}])[0]
    check("2.3 a row: journey, map (the note's name), score and its text, the change signed, the state in words, attention ok|warn|crit, the product",
          set(prow) >= {"journey", "map", "score", "score_text", "delta", "state", "reviewed", "attention", "product"}
          and all(r["attention"] in ("ok", "warn", "crit") for r in po["rows"]) and all(not r["map"].endswith(".md") for r in po["rows"])
          and all(r["product"] == "zorg" for r in po["rows"]) and all(r["delta"] == "—" or r["delta"][0] in "+\u22120" for r in po["rows"]), po.get("rows"))
    by = {r["map"]: r for r in po.get("rows", [])}
    check("2.3b the state cell is marked at the row's level, the meter warns under 75; the state names a stage count as one",
          all((r.get("marks") or {}).get("state") == (r["attention"] if r["attention"] != "ok" else None) for r in po.get("rows", []))
          and all(((r.get("marks") or {}).get("score") == "warn") == (isinstance(r["score"], (int, float)) and r["score"] < 75) for r in po.get("rows", []))
          and "1 стадія без доказів" in (by.get("journey-returns") or {}).get("state", ""), po.get("rows"))
    lead = jload(os.path.join(pdir, "portfolio-lead.json")) if os.path.exists(os.path.join(pdir, "portfolio-lead.json")) else {}
    chg = jload(os.path.join(pdir, "portfolio-changes.json")) if os.path.exists(os.path.join(pdir, "portfolio-changes.json")) else {}
    check("2.3c portfolio-lead.json: one sentence — how many journeys, how many need attention, the weakest; no product label without --products",
          lead.get("text", "").startswith("3 шляхи, 2 потребують уваги.") and "Найслабший" in lead.get("text", ""), lead)
    check("2.3d portfolio-changes.json: a list item per map that moved or needs attention, its level, its product",
          chg.get("items") and all(set(i) == {"title", "attention", "product"} for i in chg["items"])
          and any("здоров'я" in i["title"] for i in chg["items"]), chg)
    scored = [r for r in po.get("rows", []) if r["score"] is not None]
    check("2.4 weakest: the row with the lowest score", scored and po.get("weakest") == {
        "title": min(scored, key=lambda r: r["score"])["journey"], "map": min(scored, key=lambda r: r["score"])["map"],
        "score": min(scored, key=lambda r: r["score"])["score"]}, po.get("weakest"))
    check("2.5 no person in the portfolio: no owner key, no owner's words", "owner" not in keys_deep(po)
          and "Команда" not in json.dumps(po, ensure_ascii=False), json.dumps(po, ensure_ascii=False)[:300])
    check("2.6 funnel.json: the newest snapshot without map: — its stages, metric as title, values parsed, unit %, its score",
          fu.get("date") == "2026-11-02" and fu.get("score") == 71 and fu.get("stages", [{}])[1] == {
              "id": "s2", "title": "search -> cart", "value": 31.0, "baseline": 35.0, "unit": "%"}, fu)
    write(os.path.join(snapd, "2026-11-09.md"), text(os.path.join(snapd, "2026-11-02.md")).replace("date: 2026-11-02", "date: 2026-11-09")
          .replace('value: "44.0%"', 'value: "n/a"'))
    rc, out, res = jpr("app-data", "--product", "zorg", "--dir", os.path.join(FIX, "portfolio", "journeys", "zorg"),
                       "--snapshots", snapd, "--today", "2026-11-24", "--out-dir", os.path.join(d, "port2"))
    fu2 = jload(os.path.join(d, "port2", "funnel.json")) if os.path.exists(os.path.join(d, "port2", "funnel.json")) else {}
    po2 = jload(os.path.join(d, "port2", "portfolio.json")) if os.path.exists(os.path.join(d, "port2", "portfolio.json")) else {}
    check("2.7 a value that does not parse is null and its stage is kept; --lang en titles the columns in English",
          fu2.get("date") == "2026-11-09" and fu2.get("stages", [{}])[0].get("value") is None and len(fu2.get("stages", [])) == 4
          and [c["title"] for c in po2.get("columns", [])] == ["Journey", "Health", "Change", "State"], (fu2, po2.get("columns")))
    rc, out, res = jpr("app-data", "--product", "zorg", "--dir", os.path.join(FIX, "portfolio", "journeys", "zorg"),
                       "--today", "2026-11-24", "--out-dir", os.path.join(d, "port3"))
    rc, out, res = jpr("app-data", "--product", "zorg", "--products", os.path.join(APPFIX, "zorg-products.json"), "--dir", os.path.join(FIX, "portfolio", "journeys", "zorg"),
                       "--today", "2026-11-24", "--lang", "uk", "--out-dir", os.path.join(d, "port4"))
    l4 = jload(os.path.join(d, "port4", "portfolio-lead.json")) if os.path.exists(os.path.join(d, "port4", "portfolio-lead.json")) else {}
    check("2.7b --products: the product's label, read from the products file (never a command-line value), opens the lead", l4.get("text", "").startswith("Zorg: 3 шляхи"), l4)
    rc5, out5, res5 = jpr("app-data", "--product", "zorg", "--products", os.path.join(d, "nope.json"), "--dir", os.path.join(FIX, "portfolio", "journeys", "zorg"),
                          "--today", "2026-11-24", "--out-dir", os.path.join(d, "port5"))
    check("2.7c a products file that does not read: exit 2, the reason in the result line, nothing written", rc5 == 2 and res5.get("ok") is False
          and "products" in res5.get("error", "") and not os.path.exists(os.path.join(d, "port5")), out5[-300:])
    check("2.8 without a funnel snapshot: no funnel.json, funnel false", rc == 0 and res.get("funnel") is False
          and os.path.exists(os.path.join(d, "port3", "portfolio.json")) and not os.path.exists(os.path.join(d, "port3", "funnel.json")), out[-300:])
    check("2.9 the sections go through the snapshot command", run(SH, "APP_RESULT", "snapshot", "--profile", "cjm", "--out", os.path.join(d, "snap"),
          "--at", "2026-11-26T10:00:00Z", "--products", os.path.join(ROOT, "testing", "fixtures", "app", "zorg-products.json"), "--section", "portfolio:zorg:" + os.path.join(pdir, "portfolio.json"),
          "--section", "funnel:zorg:" + os.path.join(pdir, "funnel.json"), "--section", "map.first-order:zorg:" + out1)[2].get("ok") is True, "")

    # 3. wrap: the edit mode goes into the app only with a map block
    zorg = ('<!doctype html><html lang="uk"><head><meta charset="utf-8"><title>Zorg</title></head>'
            '<body><h1>Zorg</h1><p id="keep">вміст сторінки</p></body></html>')
    write(os.path.join(d, "in.html"), zorg)
    rc, out, res = run(SH, "APP_RESULT", "wrap", "--page", os.path.join(d, "in.html"), "--profile", "cjm", "--out", os.path.join(d, "app.html"))
    app = text(os.path.join(d, "app.html")) if os.path.exists(os.path.join(d, "app.html")) else ""
    rc2, _, _ = run(SH, "APP_RESULT", "wrap", "--page", os.path.join(d, "in.html"), "--profile", "pm-os", "--out", os.path.join(d, "pmos.html"))
    pmos = text(os.path.join(d, "pmos.html")) if os.path.exists(os.path.join(d, "pmos.html")) else ""
    src = re.search(r'<script type="text/plain" id="gpm-edit-src">(.*?)</script>', app, re.S)
    check("3.1 a map block: CSS_EDIT in a style, EDIT byte for byte as a non-executed text, the edit bar as a template, then map.js",
          rc == 0 and "<style id=\"gpm-edit-style\">%s</style>" % jm.CSS_EDIT in app and src and src.group(1) == jm.EDIT
          and '<template id="gpm-edit-bar"><div class="edit-bar"' in app and '<script id="gpm-map">' in app
          and app.index("gpm-edit-src") < app.index('<script id="gpm-map">'), out[-300:])
    check("3.2 EDIT can sit in a text block: it never closes a script nor opens a comment or a script",
          "</script" not in jm.EDIT.lower() and "<!--" not in jm.EDIT and "<script" not in jm.EDIT.lower(), "")
    check("3.3 no map block: no EDIT, no CSS_EDIT, no bar, no map.js", rc2 == 0 and "gpm-edit-src" not in pmos and jm.CSS_EDIT not in pmos
          and "gpm-edit-bar" not in pmos and 'id="gpm-map"' not in pmos, "")
    mj = text(os.path.join(SCRIPTS, "app_shell", "map.js")) if os.path.exists(os.path.join(SCRIPTS, "app_shell", "map.js")) else ""
    check("3.4 map.js: fixed bytes — no innerHTML, no eval, no request, no word of a note; one IIFE",
          mj.lstrip().startswith("(function") and "innerHTML" not in mj and "insertAdjacentHTML" not in mj and "eval(" not in mj
          and not re.search(r"fetch|XMLHttpRequest|sendBeacon|WebSocket|import\(", mj)
          and not any(w in mj for w in ("Zorg", "zorg", "Перше замовлення", "journey-first-order")), len(mj))
    lanes_js = re.search(r"var LANES = \[(.*?)\];", mj)
    check("3.5 map.js knows the ten lanes in journey_map.py's order", lanes_js and re.findall(r'"([a-z]+)"', lanes_js.group(1)) == list(jm.LANE_IDS),
          lanes_js.group(1) if lanes_js else "")

    # 4. the browser pass
    npm = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip() if shutil.which("npm") else ""
    try:
        subprocess.run(["node", "-e", "require('playwright')"], check=True, capture_output=True, timeout=30, env=dict(os.environ, NODE_PATH=npm))
        have_pw = True
    except Exception:
        have_pw = False
    if not have_pw:
        print("⏭  4.x the browser pass — Playwright is not installed here")
    else:
        MADE = "2026-11-26T10:00:00Z"

        def sec(name, product, data_, made=MADE):
            return {"v": 1, "product": product, "section": name, "made": made, "data": data_}
        two = json.loads(json.dumps(data))
        two_pay = jload(os.path.join(d, "pay.json")) if os.path.exists(os.path.join(d, "pay.json")) else {}
        evil = json.loads(json.dumps(data))
        if evil.get("rows"):
            evil["rows"][0]["text"] = "<img src=x onerror=window.__pwned=1>"
            evil["stages"][0]["title"] = "<b>bold</b>"
        meta = lambda secs, prods: {"v": 1, "made": MADE, "products": prods, "thresholds": {"warning": 0.1, "critical": 0.25},
                                    "sections": {k: MADE for k in secs}}
        P1 = [{"id": "zorg", "label": "Zorg", "color": "#2f6fde"}]
        P2 = P1 + [{"id": "zorg-pay", "label": "Zorg Pay", "color": None}]
        tree_secs = {"map.first-order--zorg": sec("map.first-order", "zorg", td)}
        cfg = {
            "page": tp, "app": os.path.join(d, "app.html"),
            "tree": dict(tree_secs, meta=meta(tree_secs, P1)),
            "stale": dict(tree_secs, meta=meta(tree_secs, P1)),
            "staleDoc": {"kind": "row", "map": "journey-first-order", "row": "p2", "digest": "0000000000000000", "edit": {"text": "x"}, "by": "u_b", "at": MADE},
            "multi": dict({"map.first-order--zorg": sec("map.first-order", "zorg", two), "map.payment--zorg-pay": sec("map.payment", "zorg-pay", two_pay)},
                          meta=meta(["map.first-order--zorg", "map.payment--zorg-pay"], P2)),
            "evil": {"map.first-order--zorg": sec("map.first-order", "zorg", evil), "meta": meta(["map.first-order--zorg"], P1)},
            "junk": {"map.first-order--zorg": sec("map.first-order", "zorg", {"v": 1, "rows": "x"}), "meta": meta(["map.first-order--zorg"], P1)},
            "newer": sec("map.first-order", "zorg", dict(td, table_sig="1111111111111111"), made="2026-11-27T10:00:00Z"),
        }
        port_secs = {n + "--zorg": sec(n, "zorg", jload(os.path.join(pdir, n + ".json")))
                     for n in ("portfolio", "portfolio-lead", "portfolio-changes", "funnel") if os.path.exists(os.path.join(pdir, n + ".json"))}
        cfg["port"] = dict(port_secs, meta=meta(port_secs, P1))
        cf = os.path.join(d, "cfg.json")
        write(cf, json.dumps(cfg, ensure_ascii=False))
        js = os.path.join(d, "pw.js")
        write(js, r"""
const { chromium } = require('playwright');
const fs = require('fs');
const C = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const MOCK = (seed) => `window.__seed = ${JSON.stringify(seed)};
(function(){var colls=window.__seed,subs={};
function snap(c){var m=colls[c]||{};return{docs:Object.keys(m).sort().map(function(id){return{id:id,exists:true,data:function(){return JSON.parse(JSON.stringify(m[id]));},metadata:{fromCache:false,hasPendingWrites:false}};}),size:Object.keys(m).length,empty:!Object.keys(m).length,metadata:{fromCache:false,hasPendingWrites:false},docChanges:function(){return[];}};}
function emit(c){var s=snap(c);(subs[c]||[]).forEach(function(f){setTimeout(function(){f(s);},0);});}
var db={collection:function(c){return{doc:function(id){return{set:function(d){(colls[c]=colls[c]||{})[id]=JSON.parse(JSON.stringify(d));emit(c);return Promise.resolve();},delete:function(){if(colls[c])delete colls[c][id];emit(c);return Promise.resolve();}};},onSnapshot:function(n){(subs[c]=subs[c]||[]).push(n);setTimeout(function(){n(snap(c));},0);return function(){};}};}};
var user={id:function(){return Promise.resolve("u_me");},canEdit:function(){return Promise.resolve(true);},profiles:function(ids){var r={};ids.forEach(function(i){r[i]={name:"Оля"};});return Promise.resolve(r);}};
window.__mock={colls:colls,put:function(c,id,d){(colls[c]=colls[c]||{})[id]=d;emit(c);}};
window.claude={use:function(n){return Promise.resolve(n==="db"?db:n==="user"?user:null);}};})();`;
const GRIDS = () => {
  const q = (s, r) => Array.from((r || document).querySelectorAll(s));
  const A = (e, k) => e.getAttribute('data-' + k);
  const own = (s, w) => q(s, w).filter(e => e.closest('.wrap') === w);
  return q('.wrap[data-map]').filter(w => !w.closest('[hidden]')).map(w => ({
    map: A(w, 'map'), digest: A(w, 'digest'),
    stages: own('thead th.stage', w).map(th => [th.firstChild.nodeValue, (th.querySelector('.o') || {}).textContent]),
    lanes: own('tbody th.lane', w).map(th => th.textContent),
    cells: own('td[data-stage]', w).map(td => [A(td, 'stage'), A(td, 'lane'), A(td, 'title')]),
    rows: own('.item[data-row]', w).map(it => { const td = it.closest('td');
      return [A(it, 'row'), A(td, 'stage'), A(td, 'lane'), A(it, 'lane'), A(it, 'parent'), A(it, 'code'), A(it, 'target'), A(it, 'locked'),
              it.className, it.querySelector('.t').textContent, (it.querySelector('.m') || {}).textContent]; }),
    gaps: own('.item.gap', w).map(g => [A(g.closest('td'), 'stage'), g.textContent]),
    gapHeads: own('thead th.stage.gap', w).map(th => [th.firstChild.nodeValue, (th.querySelector('.gpm-stage-mark') || {}).textContent || null]),
    heads: own('thead th.stage', w).map(th => [th.firstChild.nodeValue, (th.querySelector('.n') || {}).textContent || null, (th.querySelector('.o') || {}).textContent]),
    chips: own('.item.chip', w).map(c => [A(c.closest('td'), 'stage'), c.querySelector('.t').textContent, c.querySelector('.m').textContent]),
    refs: own('.item.ref', w).map(c => [A(c.closest('td'), 'stage'), c.textContent]),
    adds: own('.edit-add', w).length}));
};
const SUMS = () => Array.from(document.querySelectorAll('details.child > summary')).filter(s => !s.closest('[hidden]')).map(s => s.textContent);
(async () => {
  const b = await chromium.launch(); const out = {};
  async function open(file, init, vp) {
    const p = await b.newPage({viewport: vp || {width: 1400, height: 900}}); const errs = [], reqs = [];
    p.on('pageerror', e => errs.push(String(e))); p.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
    p.on('request', r => { if (!r.url().startsWith('file:')) reqs.push(r.url()); });
    await p.route(/^https?:/, r => r.fulfill({status: 200, contentType: 'text/css', body: ''}));
    if (init) await p.addInitScript(init);
    await p.goto('file://' + file); await p.waitForTimeout(300);
    return [p, errs, reqs];
  }
  const tx = (p, sel) => p.$$eval(sel, x => x.length ? x[0].textContent : null);
  const toMap = async (p) => { await p.click('.gpm-tabs [data-tab="map"]'); await p.waitForTimeout(300); };
  // pw_map_parity: the v4.12.0 page and the app, the same note
  let [p, errs, reqs] = await open(C.page, MOCK({}));
  out.page = await p.evaluate(GRIDS); out.pageSums = await p.evaluate(SUMS); out.pageErrs = errs;
  out.pts = await p.$$eval('table.pts td', x => x.map(e => e.textContent));
  // pw_map_edit_shared — the page writes
  await p.click('.edit-toggle'); await p.click('.item[data-row="p2"]'); await p.fill('.f-text', 'Вартість доставки видно лише в кінці');
  await p.click('.f-apply'); await p.waitForTimeout(150);
  out.pageStore = await p.evaluate(() => JSON.parse(JSON.stringify(window.__mock.colls.edits || {}))); await p.close();
  [p, errs, reqs] = await open(C.app, MOCK({snapshot: C.tree})); await toMap(p);
  out.app = await p.evaluate(GRIDS); out.appSums = await p.evaluate(SUMS);
  out.appPts = await p.$$eval('.gpm-modules table.pts td', x => x.map(e => e.textContent));
  out.appSum = await tx(p, '.gpm-map:not([hidden]) .gpm-map-sum'); out.appSpark = await p.$$eval('.gpm-map:not([hidden]) svg.spark', x => x.length);
  out.appTitle = await tx(p, '.gpm-map:not([hidden]) .gpm-map-title');
  out.appModuleTitle = await p.$eval('.gpm-module-title', e => e.className);
  out.appBars = await p.$$eval('.gpm-modules .edit-bar', x => x.length); out.pageHidden = await p.isHidden('.gpm-page');
  out.appToggle = await tx(p, '.gpm-modules .edit-toggle');
  // a chip opens its child's <details>
  out.closed = await p.$eval('details.child', d => d.open);
  await p.click('.item.chip'); await p.waitForTimeout(80); out.opened = await p.$eval('details.child', d => d.open);
  // pw_map_edit_shared — the app writes
  await p.click('.edit-toggle'); await p.click('.item[data-row="p2"]'); await p.fill('.f-text', 'Вартість доставки видно лише в кінці');
  await p.click('.f-apply'); await p.waitForTimeout(150);
  out.appStore = await p.evaluate(() => JSON.parse(JSON.stringify(window.__mock.colls.edits || {})));
  out.appSync = await tx(p, '.edit-sync'); out.appEditedMark = await p.$eval('.item[data-row="p2"]', e => e.getAttribute('data-eb'));
  // a colleague's edit arrives live
  await p.evaluate(d => window.__mock.put('edits', 'a~x', {kind: 'add', map: 'journey-first-order', digest: d, add: {stage: 's3', lane: 'solution', text: 'Від колеги', parent: ''}, by: 'u_olya'}),
                   C.tree['map.first-order--zorg'].data.table_sig);
  await p.waitForTimeout(150); out.appAdded = await p.$$eval('.item.added', x => x.map(e => [e.textContent, e.getAttribute('data-eb')]));
  // a tab away and back keeps the same map and its edits (EDIT runs once)
  await p.click('.gpm-tabs [data-tab="portfolio"]'); await p.waitForTimeout(80); await toMap(p);
  out.back = {mark: await p.$eval('.item[data-row="p2"]', e => e.getAttribute('data-eb')), adds: await p.$$eval('.edit-add', x => x.length),
              bars: await p.$$eval('.edit-bar', x => x.length)};
  // a new snapshot while the map is open: the old map stays, locked, with a reload
  await p.evaluate(s => window.__mock.put('snapshot', 'map.first-order--zorg', s), C.newer); await p.waitForTimeout(200);
  out.newer = {hint: await tx(p, '.gpm-map-note'), reload: await p.$$eval('.gpm-map-reload', x => x.length),
               editing: await p.evaluate(() => document.body.classList.contains('editing')), digest: await p.$eval('.wrap[data-map]', w => w.getAttribute('data-digest'))};
  await p.click('.edit-toggle'); await p.click('.item[data-row="a1"]', {force: true}); await p.waitForTimeout(80);
  out.newer.form = await p.isHidden('.edit-form');
  out.appErrs = errs; out.appReqs = reqs; await p.close();
  // pw_stale_map_locks_edit
  [p, errs] = await open(C.app, MOCK({snapshot: C.stale, edits: {'r~stale': C.staleDoc}})); await toMap(p);
  out.stale = {hint: await tx(p, '.gpm-map-note'), adds: await p.$$eval('.gpm-map-locked .edit-add', x => x.filter(e => getComputedStyle(e).display !== 'none').length)};
  await p.click('.edit-toggle'); await p.click('.item[data-row="p2"]', {force: true}); await p.waitForTimeout(80);
  out.stale.form = await p.isHidden('.edit-form'); out.stale.store = await p.evaluate(() => Object.keys(window.__mock.colls.edits));
  out.stale.otherOpen = await p.evaluate(() => { const w = document.querySelector('.wrap[data-map="journey-payment"]'); return !!w && !w.closest('.gpm-map-locked'); });
  out.staleErrs = errs; await p.close();
  // several maps: a picker, one map at a time; the product switch
  [p, errs] = await open(C.app, MOCK({snapshot: C.multi})); await toMap(p);
  const vis = () => p.evaluate(() => Array.from(document.querySelectorAll('.gpm-map')).filter(m => !m.hidden).map(m => m.getAttribute('data-map')));
  out.multi = {pick: await p.$$eval('.gpm-map-pick button', x => x.map(e => [e.textContent, e.getAttribute('aria-pressed')])), shown: await vis(),
               bars: await p.$$eval('.edit-bar', x => x.length)};
  await p.click('.gpm-map-pick button:nth-child(2)'); await p.waitForTimeout(80); out.multi.shown2 = await vis();
  await p.click('.gpm-products [data-product="zorg"]'); await p.waitForTimeout(80);
  out.multi.zorg = {shown: await vis(), pick: await p.$$eval('.gpm-map-pick button', x => x.filter(b => !b.closest('[hidden]')).length)};
  out.multiErrs = errs; await p.close();
  // foreign data: text stays text; a junk section shows the empty state
  [p, errs] = await open(C.app, MOCK({snapshot: C.evil})); await toMap(p);
  out.evil = {imgs: await p.$$eval('.gpm-modules img', x => x.length), bolds: await p.$$eval('.gpm-modules th.stage b', x => x.length),
              pwned: await p.evaluate(() => !!window.__pwned), t: await p.$eval('.item[data-row] .t', e => e.textContent)}; out.evilErrs = errs; await p.close();
  [p, errs] = await open(C.app, MOCK({snapshot: C.junk})); await toMap(p);
  out.junk = {empties: await p.$$eval('.gpm-empty', x => x.map(e => e.textContent)), bars: await p.$$eval('.edit-bar', x => x.length)}; out.junkErrs = errs; await p.close();
  // the portfolio on the rail: the lead sentence, the table with its meter, what changed beside it; the funnel's change to base
  [p, errs] = await open(C.app, MOCK({snapshot: C.port}));
  out.port = {lead: await tx(p, '.gpm-lead-text'), heads: await p.$$eval('.gpm-modules .gpm-table th', x => x.map(e => e.textContent)),
              meters: await p.$$eval('.gpm-modules .gpm-c-meter', x => x.length), aside: await p.$$eval('.gpm-col-aside .gpm-item-title', x => x.map(e => e.textContent)),
              asideHead: await tx(p, '.gpm-col-aside .gpm-block-title'), weakest: await p.$$eval('.gpm-weakest', x => x.filter(e => getComputedStyle(e).display !== 'none').length)};
  await p.click('.gpm-tabs [data-tab="funnel"]'); await p.waitForTimeout(150);
  out.port.deltas = await p.$$eval('.gpm-stage-delta', x => x.map(e => e.textContent)); out.port.funnelHead = await tx(p, '.gpm-block-chart .gpm-block-title');
  out.portErrs = errs; await p.close();
  // phone width
  [p, errs] = await open(C.app, MOCK({snapshot: C.tree}), {width: 360, height: 640}); await toMap(p);
  out.phone = await p.evaluate(() => ({sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth})); await p.close();
  console.log(JSON.stringify(out)); await b.close();
})();""")
        pr = subprocess.run(["node", js, cf], capture_output=True, text=True, timeout=240, env=dict(os.environ, NODE_PATH=npm))
        try:
            br = json.loads(pr.stdout.strip().splitlines()[-1])
        except (ValueError, IndexError):
            br = {}
        if not br:
            print(pr.stderr[-1500:])
        pg, ap = br.get("page") or [], br.get("app") or []

        def proj(grids, idx):
            return [(g["map"], g["digest"], [tuple(r[i] for i in idx) for r in g["rows"]]) for g in grids]
        check("4.1 pw_map_parity: (row id, stage, lane, parent, code, target, locked) and the digest of every grid — the same in the app as on the page",
              pg and proj(pg, (0, 1, 2, 4, 5, 6, 7)) == proj(ap, (0, 1, 2, 4, 5, 6, 7)) and len(pg) == 4, (proj(pg, (0, 1, 2, 4, 5, 6, 7))[:1], proj(ap, (0, 1, 2, 4, 5, 6, 7))[:1]))
        check("4.2 …the child maps to three levels: the same grids in the same order", [g["map"] for g in ap] == [
            "journey-first-order", "journey-shipping", "journey-payment", "journey-3ds"], [g["map"] for g in ap])
        rows10 = lambda g: [r[:10] for r in g["rows"]]
        check("4.3 …and the same markup EDIT reads: lanes, cells with their titles, each row's class and text",
              pg and all(a[k] == b_[k] for a, b_ in zip(pg, ap) for k in ("lanes", "cells")) and all(rows10(a) == rows10(b_) for a, b_ in zip(pg, ap))
              and len(pg) == len(ap), [(k, a[k][:2], b_[k][:2]) for a, b_ in zip(pg, ap) for k in ("lanes", "cells", "rows") if a[k] != b_[k]][:2])
        st0 = td.get("stages") or []
        check("4.3b the app's stage header: the stage's name first (what EDIT reads), «Стадія N» over it, its target as a sentence or «Ціль ще не задана»",
              ap and [h[0] for h in ap[0]["heads"]] == [x["title"] for x in st0]
              and [h[1] for h in ap[0]["heads"]] == ["Стадія %d" % (i + 1) for i in range(len(st0))]
              and [h[2] for h in ap[0]["heads"]] == [x["goal"] or "Ціль ще не задана" for x in st0]
              and any(x["goal"].startswith("Від ") for x in st0), (ap[0]["heads"] if ap else None, [x.get("goal") for x in st0]))
        srcs = {r["id"]: r["src"] for r in td.get("rows", [])}
        check("4.3c under each piece of evidence its source and how it was obtained (the data's `src`), never the page's raw line",
              ap and all((r[10] or "") == (srcs.get(r[0]) or "") for r in ap[0]["rows"] if r[0] in srcs)
              and any("побачено в продукті" in (r[10] or "") for r in ap[0]["rows"]), [r[10] for r in ap[0]["rows"]][:4] if ap else None)
        check("4.4 …the roll-up chips, the references past the depth and the children's summaries the same; a gap is marked in its stage's header",
              pg and all(a[k] == b_[k] for a, b_ in zip(pg, ap) for k in ("chips", "refs")) and br.get("pageSums") == br.get("appSums")
              and all(len(a["gaps"]) == len(b_["gapHeads"]) and not b_["gaps"] for a, b_ in zip(pg, ap))
              and all(h[1] == "Немає доказів" for g in ap for h in g["gapHeads"])
              and any(g["chips"] for g in ap) and any(g["refs"] for g in ap),
              [(k, a[k], b_[k]) for a, b_ in zip(pg, ap) for k in ("chips", "refs") if a[k] != b_[k]][:2] or [(a["gaps"], b_["gapHeads"]) for a, b_ in zip(pg, ap)])
        check("4.5 EDIT ran in the app: the same «+ Додати» in every grid, one edit bar, the switch in the page's words, the page behind hidden",
              pg and [g["adds"] for g in pg] == [g["adds"] for g in ap] and br.get("appBars") == 1 and br.get("appToggle") == "Редагувати"
              and br.get("pageHidden") is True, ([g["adds"] for g in pg], [g["adds"] for g in ap], br.get("appBars")))
        pts = br.get("pts") or []
        n_ = len(pts) // 3
        last_, prev_ = (pts[2 * n_ - 1], pts[2 * n_ - 2]) if n_ >= 2 else ("", "")
        check("4.6 the health in words over the map: the last point and its change since the previous one; the trend line, no table of points",
              n_ >= 2 and ("Здоровʼя %s," % last_) in (br.get("appSum") or "") and (("%+g" % (float(last_) - float(prev_))).replace("-", "\u2212") in (br.get("appSum") or ""))
              and br.get("appSpark") == 1 and br.get("appPts") == [], (pts, br.get("appSum"), br.get("appSpark"), br.get("appPts")))
        check("4.6b the map names itself: the journey's name as its heading; the module's own heading only for a screen reader",
              br.get("appTitle") == td.get("journey") and "gpm-vh" in (br.get("appModuleTitle") or ""), (br.get("appTitle"), br.get("appModuleTitle")))
        check("4.7 a roll-up chip opens its child's map", br.get("closed") is False and br.get("opened") is True, (br.get("closed"), br.get("opened")))

        def norm(store):
            return {k: {x: v[x] for x in v if x != "at"} for k, v in (store or {}).items()}
        check("4.8 pw_map_edit_shared: a text edit in the app writes into `edits` the document the v4.12.0 page writes — the same id and fields",
              br.get("pageStore") and norm(br.get("pageStore")) == norm(br.get("appStore"))
              and list(norm(br.get("appStore")).values())[0].get("edit") == {"text": "Вартість доставки видно лише в кінці"}
              and list(br.get("appStore").values())[0].get("at"), (br.get("pageStore"), br.get("appStore")))
        check("4.9 …marked on the card; the shared edits are on; a colleague's row appears live with their name",
              br.get("appEditedMark") == "змінено · ти" and "Спільні правки" in (br.get("appSync") or "")
              and br.get("appAdded") == [["Від колеги", "новий · Оля"]], (br.get("appEditedMark"), br.get("appSync"), br.get("appAdded")))
        bk = br.get("back") or {}
        check("4.10 another tab and back: the same map with its marks, one bar, no second «+ Додати» (EDIT runs once)",
              bk.get("mark") == "змінено · ти" and bk.get("bars") == 1 and bk.get("adds") == sum(g["adds"] for g in ap), bk)
        nw = br.get("newer") or {}
        check("4.11 a new snapshot while open: the old map stays, its editing off and locked, a line and a reload button",
              "онов" in (nw.get("hint") or "").lower() and nw.get("reload") == 1 and nw.get("editing") is False and nw.get("form") is True
              and nw.get("digest") == (ap[0]["digest"] if ap else None), nw)
        check("4.12 the app: no error, no request", not br.get("appErrs") and not br.get("appReqs") and not br.get("pageErrs"), (br.get("appErrs"), br.get("appReqs")))
        st = br.get("stale") or {}
        check("4.13 pw_stale_map_locks_edit: edits of another version of the map in the database — its editing off with a hint; no «+», no editor, nothing written",
              "іншій версії" in (st.get("hint") or "") and st.get("adds") == 0 and st.get("form") is True and st.get("store") == ["r~stale"]
              and not br.get("staleErrs"), st)
        check("4.14 …a child map without such edits stays editable", st.get("otherOpen") is True, st)
        mu = br.get("multi") or {}
        check("4.15 several maps: a picker with each map's name and product, one map at a time, one edit bar",
              [x[1] for x in mu.get("pick", [])] == ["true", "false"] and "Перше замовлення" in mu.get("pick", [["", ""]])[0][0]
              and "Zorg Pay" in mu.get("pick", [["", ""], ["", ""]])[1][0] and mu.get("shown") == ["journey-first-order"]
              and mu.get("shown2") == ["journey-payment"] and mu.get("bars") == 1 and not br.get("multiErrs"), mu)
        check("4.16 the product switch: only that product's maps, no picker for one", (mu.get("zorg") or {}).get("shown") == ["journey-first-order"]
              and (mu.get("zorg") or {}).get("pick") == 0, mu.get("zorg"))
        ev = br.get("evil") or {}
        check("4.17 data is text: HTML in a row and a stage shows as text, nothing injected", ev.get("imgs") == 0 and ev.get("bolds") == 0
              and ev.get("pwned") is False and "<img" in (ev.get("t") or "") and not br.get("evilErrs"), ev)
        jk = br.get("junk") or {}
        check("4.18 a section that is no map: the empty state, no bar, no error", jk.get("empties") and jk.get("bars") == 0 and not br.get("junkErrs"), jk)
        pt = br.get("port") or {}
        check("4.20 the portfolio in the app: the lead sentence over it, the table Шлях · Здоров'я (a meter per row) · Зміна · Стан, «Що змінилось» beside it, no second «weakest» line",
              (pt.get("lead") or "").startswith("3 шляхи, 2 потребують уваги.") and pt.get("heads") == ["Шлях", "Здоров'я", "Зміна", "Стан"]
              and pt.get("meters") == len(po.get("rows", [])) and pt.get("asideHead") == "Що змінилось" and len(pt.get("aside") or []) == len(chg.get("items", []))
              and pt.get("weakest") == 0 and not br.get("portErrs"), (pt, br.get("portErrs")))
        check("4.21 the funnel: each stage with a base says its change to it — «до бази −11,4%»; the block titled",
              pt.get("deltas") and all(x.startswith("до бази ") for x in pt["deltas"]) and "до бази \u221211,4%" in pt["deltas"]
              and pt.get("funnelHead") == "Переходи між стадіями", pt)
        ph = br.get("phone") or {}
        check("4.19 phone width: no sideways scroll of the page (the grid scrolls in its frame)", ph and ph.get("sw", 9e9) <= ph.get("cw", 0), ph)
finally:
    shutil.rmtree(d, ignore_errors=True)
    shutil.rmtree(SAFE_HOME, ignore_errors=True)

print("\nRESULT: %s (%d failed)" % ("GREEN ✅" if not fails else "RED ❌", fails))
sys.exit(1 if fails else 0)
