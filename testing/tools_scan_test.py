#!/usr/bin/env python3
"""TC-tools-4200 — scripts/tools_scan.py, the tools registry (v4.2.0, references/tool-registry.md).

A fictional home («Zorg») holds every host file the scan reads, each with values planted under the names:
arguments, environment variables, headers, URLs, an install path, an account e-mail, a skill's body. The scan
must give the names and nothing else — and a mutated scanner that reads one value must be caught by the same
check. Then: merge (seed, observed rows, user fields kept, not-seen instead of deletion), suggest (one record,
own recommended > team > seed, decline per skill, deprecated, no registry), the never-store filter, the team
list read from a fictional core (read-only, a path outside the core refused) and the export (only shared, only
the listed fields, readable back as a core's list). Every secret-looking value is assembled at run time — none
is written in this file. Stdlib only; run from the repo root:

  env -u GROW_PM_CONTEXT_PATH -u GROW_PM_PROVIDER_PATHS python3 testing/tools_scan_test.py
"""
import hashlib, json, os, re, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "tools_scan.py")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import ctx_common as cc  # noqa: E402

fails = 0


def check(name, cond, detail=""):
    global fails
    fails += not cond
    print(("✅" if cond else "❌"), name, ("" if cond else "-> " + str(detail)[:900]))


def run(*args, script=SCRIPT, stdin=None):
    p = subprocess.run([sys.executable, script] + list(args), capture_output=True, text=True, input=stdin,
                       env={k: v for k, v in os.environ.items() if not k.startswith("GROW_PM_")})
    res = {}
    for line in p.stdout.splitlines():
        if line.startswith("TOOLS_RESULT "):
            res = json.loads(line[len("TOOLS_RESULT "):])
    rows = [json.loads(line) for line in p.stdout.splitlines() if line.startswith("{")]
    return p.returncode, p.stdout + p.stderr, res, rows


def w(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def tree_hash(root):
    h = hashlib.sha256()
    for dp, _, fs in sorted(os.walk(root)):
        for f in sorted(fs):
            p = os.path.join(dp, f)
            h.update(p.encode()); h.update(open(p, "rb").read())
    return h.hexdigest()


# Planted values: a marker each, so a leak names itself. Built here, never written as a literal token.
M = {k: "ZORG-PLANTED-%s-%s" % (k, hashlib.sha1(k.encode()).hexdigest()[:10]) for k in (
    "args", "env", "url", "headers", "installpath", "email", "skillbody", "tomlargs", "tomlenv", "tomlurl",
    "desktopenv", "desktopargs")}

d = tempfile.mkdtemp(prefix="tools-scan-")
try:
    home = os.path.join(d, "home")
    store = os.path.join(d, "store")
    w(os.path.join(home, ".claude", "plugins", "installed_plugins.json"), json.dumps({
        "version": 2, "plugins": {
            "zorg-helper@zorg-market": [{"installPath": "/opt/" + M["installpath"], "gitCommitSha": "0" * 40}],
            "grow-product-manager@zorg-market": [{"installPath": "/opt/x"}]}}))
    w(os.path.join(home, ".claude.json"), json.dumps({
        "oauthAccount": {"emailAddress": M["email"] + "@zorg.example"},
        "mcpServers": {"zorg-crm": {"command": "npx", "args": ["--key", M["args"]], "env": {"ZORG_KEY": M["env"]}}},
        "projects": {"/Users/zorg/app": {"mcpServers": {"zorg-docs": {
            "url": "https://docs.zorg.example/mcp?k=" + M["url"], "headers": {"Authorization": "Bearer " + M["headers"]}}}}}}))
    w(os.path.join(home, "Library", "Application Support", "Claude", "claude_desktop_config.json"), json.dumps({
        "mcpServers": {"zorg-metrics": {"command": "/opt/zorg", "args": [M["desktopargs"]], "env": {"T": M["desktopenv"]}}}}))
    w(os.path.join(home, ".codex", "config.toml"), "\n".join([
        'model = "zorg-model"',
        "[mcp_servers.zorg-search]",
        'command = "zorg-search"',
        'args = ["--key", "%s"]' % M["tomlargs"],
        "[mcp_servers.zorg-search.env]",
        'ZORG_KEY = "%s"' % M["tomlenv"],
        '[mcp_servers."zorg board"]',
        'url = "https://board.zorg.example/?t=%s"' % M["tomlurl"],
        '[plugins."zorg-codex-plugin@zorg-market"]',
        "enabled = true",
        '[plugins."grow-product-manager@zorg-market"]',
        "enabled = true", ""]))
    w(os.path.join(home, ".claude", "skills", "zorg-notes", "SKILL.md"),
      "---\nname: zorg-notes\ndescription: Notes of the Zorg team in one place.\n---\n\nBody " + M["skillbody"] + "\n")
    apps = os.path.join(d, "apps.jsonl")
    w(apps, "\n".join(json.dumps(x) for x in [
        {"source": "scan-mac", "name": "Miro", "bundle_id": "com.electron.realtimeboard", "path": "/Applications/Miro.app"},
        {"source": "scan-mac", "name": "Zorg Shop", "bundle_id": "com.zorg.shop", "path": "/Applications/Zorg Shop.app"},
        {"source": "bookmarks", "name": "Notion", "domain": "notion.so"}]) + "\n")

    # ---------------------------------------------------------------- 1. scan: names only
    rc, out, res, rows = run("scan", "--home", home, "--apps-jsonl", apps)
    names = sorted(r["name"] for r in rows)
    check("1.1 scan exits 0 with a TOOLS_RESULT", rc == 0 and res.get("found") == len(rows), out)
    want = ["Miro", "zorg board", "zorg-codex-plugin", "zorg-crm", "zorg-docs", "zorg-helper", "zorg-metrics",
            "zorg-notes", "zorg-search"]
    check("1.2 every name from the four host files, the skill folder and the matched app", names == want, names)
    leaked = [k for k, v in M.items() if v in out]
    check("1.3 no planted value reaches the output", not leaked, leaked)
    check("1.4 the plugin itself is not a record", "grow-product-manager" not in out, out)
    check("1.5 an app that matches no seed record and a bookmark stay out",
          "Zorg Shop" not in out and "notion.so" not in out, out)
    by = {r["name"]: r for r in rows}
    check("1.6 sources and hosts per file", by["zorg-crm"]["source"] == "scan-claude-code" and
          by["zorg-metrics"]["host"] == "claude-desktop" and by["zorg-search"]["host"] == "codex" and
          by["zorg-codex-plugin"]["kind"] == "plugin" and by["zorg-notes"]["kind"] == "skill" and
          by["Miro"]["source"] == "scan-apps", rows)
    check("1.7 a TOML sub-table ([mcp_servers.x.env]) is not a second server",
          names.count("zorg-search") == 1 and "env" not in names, names)
    rc, out, res, rows = run("scan", "--home", os.path.join(d, "empty-home"), "--no-apps")
    check("1.8 a home with no host files → nothing found, exit 0", rc == 0 and res.get("found") == 0, out)

    # Mutation: a scanner that reads the values under a server's name must be caught by check 1.3.
    mut = os.path.join(d, "mut")
    os.makedirs(mut)
    for f in ("ctx_common.py", "ctx_never.py", "ctx_stem.py", "landscape_scan.sh"):
        if os.path.exists(os.path.join(ROOT, "scripts", f)):
            shutil.copy(os.path.join(ROOT, "scripts", f), mut)
    src = open(SCRIPT, encoding="utf-8").read()
    bad = src.replace("out.extend(str(k) for k in n.keys())", "out.extend(str(k) + json.dumps(v) for k, v in n.items())")
    check("1.9 mutation applies (the key reader is where the test expects it)", bad != src)
    w(os.path.join(mut, "tools_scan.py"), bad)
    shutil.copytree(os.path.join(ROOT, "references"), os.path.join(d, "references"))
    rc, out, res, rows = run("scan", "--home", home, "--no-apps", script=os.path.join(mut, "tools_scan.py"))
    check("1.10 the mutated scanner leaks — and the leak check sees it", any(v in out for v in M.values()), out[:300])

    # ---------------------------------------------------------------- 2. merge
    scanfile = os.path.join(d, "scan.jsonl")
    rc, out, res, rows = run("scan", "--home", home, "--apps-jsonl", apps)
    w(scanfile, out)
    obs = "\n".join(json.dumps(x) for x in [
        {"name": "figma", "state": "connected", "kind": "mcp"},
        {"name": "Atlassian_Rovo", "state": "needs-auth", "kind": "mcp"},
        {"name": "zorg-account-skill", "kind": "skill", "source": "scan-account"}]) + "\n"
    obsfile = os.path.join(d, "obs.jsonl")
    w(obsfile, obs)
    rc, out, res, rows = run("merge", "--store", store, "--scan", scanfile, "--observed", obsfile)
    reg = json.load(open(os.path.join(store, "registry.json")))["tools"]
    by = {t["id"]: t for t in reg}
    seed = cc.read_yaml_records(open(os.path.join(ROOT, "references", "tools-seed.yaml")).read(), "tools")
    check("2.1 merge exits 0; every seed record is in", rc == 0 and all(s["id"] in by for s in seed), out)
    check("2.2 a seed tool seen as an app → installed", by["miro"]["state"] == "installed", by.get("miro"))
    check("2.3 observed rows: connected and needs-auth; an alias finds the seed record",
          by["figma"]["state"] == "connected" and by["atlassian"]["state"] == "needs-auth", (by["figma"], by["atlassian"]))
    check("2.4 a seed tool nobody saw stays not-installed", by["notebooklm"]["state"] == "not-installed", by["notebooklm"])
    check("2.5 a new server becomes a record with its host", by["zorg-crm"]["kind"] == "mcp" and
          by["zorg-crm"]["hosts"] == ["claude-code"] and by["zorg-crm"]["state"] == "installed", by.get("zorg-crm"))
    check("2.6 an account row → host account", "account" in by["zorg-account-skill"]["hosts"], by.get("zorg-account-skill"))
    files = "".join(open(os.path.join(dp, f), encoding="utf-8").read()
                    for dp, _, fs in os.walk(store) for f in fs)
    check("2.7 no planted value in any file of the store", not [k for k, v in M.items() if v in files])
    check("2.8 tools.md is rendered", os.path.isfile(os.path.join(store, "tools.md")) and
          "| zorg-crm |" in open(os.path.join(store, "tools.md")).read())

    rc, out, res, _ = run("set", "--store", store, "--id", "zorg-crm", "verdict=recommended", "shared=true",
                          "recommended_by=я", "skills=product-analysis", "job=CRM of the Zorg team",
                          "connect=ask the Zorg admin for access")
    check("2.9 set the user's fields", rc == 0, out)
    cfg = json.load(open(os.path.join(home, ".claude.json")))
    del cfg["mcpServers"]["zorg-crm"]
    w(os.path.join(home, ".claude.json"), json.dumps(cfg))
    rc, out, res, rows = run("merge", "--store", store, "--rescan", "--home", home, "--apps-jsonl", apps)
    by = {t["id"]: t for t in json.load(open(os.path.join(store, "registry.json")))["tools"]}
    check("2.10 a server gone from the host file → not-seen, never deleted",
          by.get("zorg-crm", {}).get("state") == "not-seen", by.get("zorg-crm"))
    check("2.11 a rescan keeps verdict, shared, recommended_by", by["zorg-crm"].get("verdict") == "recommended" and
          by["zorg-crm"].get("shared") is True and by["zorg-crm"].get("recommended_by") == "я", by["zorg-crm"])
    check("2.12 a source this merge did not read keeps its state (figma stays connected)",
          by["figma"]["state"] == "connected", by["figma"])

    # ---------------------------------------------------------------- 3. suggest / decline
    rc, out, res, rows = run("suggest", "--store", store, "--skill", "diagram-prototyper")
    check("3.1 one record, the seed's likeliest not-installed tool (figma connected, miro installed)",
          rc == 0 and len(rows) == 1 and rows[0]["id"] == "figjam", rows)
    rc, out, res, _ = run("decline", "--store", store, "--skill", "diagram-prototyper", "--id", "figjam")
    rc, out, res, rows = run("suggest", "--store", store, "--skill", "diagram-prototyper")
    check("3.2 after «ні» the next one", rows and rows[0]["id"] == "notebooklm", rows)
    run("set", "--store", store, "--id", "gemini", "verdict=recommended")
    rc, out, res, rows = run("suggest", "--store", store, "--skill", "diagram-prototyper")
    check("3.3 the user's recommended comes first", rows and rows[0]["id"] == "gemini", rows)
    run("set", "--store", store, "--id", "gemini", "verdict=deprecated")
    rc, out, res, rows = run("suggest", "--store", store, "--skill", "diagram-prototyper")
    check("3.4 deprecated is never offered", rows and rows[0]["id"] == "notebooklm", rows)
    by = {t["id"]: t for t in json.load(open(os.path.join(store, "registry.json")))["tools"]}
    check("3.5 a decline is per skill", by["figjam"]["declined"][0]["skill"] == "diagram-prototyper", by["figjam"])
    rc, out, res, rows = run("suggest", "--store", store, "--skill", "meeting-processor")
    check("3.6 another skill still gets its own suggestion", rows and rows[0]["id"] == "fireflies", rows)
    run("decline", "--store", store, "--skill", "diagram-prototyper", "--id", "figjam", "--undo")
    rc, out, res, rows = run("suggest", "--store", store, "--skill", "diagram-prototyper")
    check("3.7 decline --undo brings it back", rows and rows[0]["id"] == "figjam", rows)
    rc, out, res, rows = run("suggest", "--store", os.path.join(d, "no-store"), "--skill", "diagram-prototyper")
    check("3.8 no registry → no record and no error", rc == 0 and not rows and res.get("suggest") is None, out)
    rc, out, res, rows = run("suggest", "--store", store, "--skill", "goal-setter")
    check("3.9 a skill no tool serves → nothing", rc == 0 and not rows, out)
    rc, out, res, rows = run("suggest", "--store", store, "--skill", "product-research")
    check("3.10 product-research gets a market-data tool, not the browser second opinion",
          rows and rows[0]["id"] == "similarweb", rows)

    # ---------------------------------------------------------------- 4. never-store
    tok = "gh" + "p_" + "Zorg0" * 7
    rc, out, res, _ = run("set", "--store", store, "--id", "zorg-docs", "connect=use " + tok)
    reg_text = open(os.path.join(store, "registry.json")).read()
    check("4.1 a key in a connect line is refused by kind, exit 2", rc == 2 and res.get("error") == "refused" and
          res["refused"][0]["kinds"] == ["secret"], out)
    check("4.2 the value is neither echoed nor stored", tok not in out and tok not in reg_text)
    rc, out, res, _ = run("set", "--store", store, "--id", "zorg-docs", "colour=blue")
    check("4.3 a field that is not the user's is refused", rc == 2, out)
    rc, out, res, _ = run("set", "--store", store, "--id", "zorg-docs", "verdict=great")
    check("4.4 a verdict outside the list is refused", rc == 2, out)
    rc, out, res, _ = run("add", "--store", store, "--name", "Zorg Academy course", "--kind", "course",
                          "job=product discovery course", "access=paid", "skills=goal-setter")
    check("4.5 add by hand", rc == 0 and res.get("id") == "zorg-academy-course", out)
    rc, out, res, _ = run("add", "--store", store, "--name", "Zorg Whiteboard", "--kind", "mcp",
                          "--source", "registry-search", "job=team whiteboard")
    by = {t["id"]: t for t in json.load(open(os.path.join(store, "registry.json")))["tools"]}
    check("4.6 a search result the user picked keeps its source", rc == 0 and
          by.get("zorg-whiteboard", {}).get("sources") == ["registry-search"], (out, by.get("zorg-whiteboard")))

    # ---------------------------------------------------------------- 5. export
    rc, out, res, _ = run("export", "--store", store)
    exp = open(res["file"], encoding="utf-8").read() if res.get("file") else ""
    recs = cc.read_yaml_records(exp, "tools") if exp else []
    check("5.1 only the shared record goes out", rc == 0 and res.get("exported") == 1 and len(recs) == 1 and
          recs[0]["name"] == "zorg-crm", (out, exp))
    check("5.2 only the listed fields — no state, hosts, sources, declined, seen",
          recs and not set(recs[0]) - {"name", "kind", "job", "skills", "contours", "access", "connect", "verdict",
                                       "recommended_by", "checked", "publishes"}, recs)

    # ---------------------------------------------------------------- 6. team
    core = os.path.join(d, "zorg-core")
    w(os.path.join(core, "_System", "provider-manifest.yaml"),
      "id: zorg-core\ncontract: vault/v1\nplugin_folder: .\nowner_label: the Zorg core owner\ntools_file: _System/tools.yaml\n")
    w(os.path.join(core, "_System", "tools.yaml"), exp.replace('"zorg-crm"', '"Zorg Planner"').replace(
        '"я"', '"Anna Zorg"').replace('"product-analysis"', '"feedback-triage"') + '  - name: "Figma"\n    kind: "mcp"\n    skills: ["design-bridge"]\n')
    w(os.path.join(home, ".grow-pm", "providers", "zorg-core.yaml"),
      "schema: provider-registration/2\nid: zorg-core\nkind: folder\nauthority: team\npaths:\n  - %s\n" % core)
    before = tree_hash(core)
    rc, out, res, _ = run("team", "--store", store, "--home", home)
    team = json.load(open(os.path.join(store, "team", "zorg-core.json")))["tools"] if rc == 0 and \
        os.path.isfile(os.path.join(store, "team", "zorg-core.json")) else []
    check("6.1 the core's list is read, marked team:zorg-core", rc == 0 and res.get("team") == {"zorg-core": 2} and
          all(t["recommended_by"] == "team:zorg-core" for t in team), (out, team))
    check("6.2 the core is untouched", tree_hash(core) == before)
    check("6.3 tools.md shows «Від команди»", "## Від команди" in open(os.path.join(store, "tools.md")).read())
    rc, out, res, rows = run("suggest", "--store", store, "--skill", "feedback-triage")
    check("6.4 a team record comes before the seed's", rows and rows[0]["name"] == "Zorg Planner" and
          rows[0]["origin"] == "team", rows)
    rc, out, res, _ = run("add", "--store", store, "--from-team", "Zorg Planner")
    by = {t["id"]: t for t in json.load(open(os.path.join(store, "registry.json")))["tools"]}
    check("6.5 «взяти собі» copies the record into the registry", rc == 0 and
          by.get("zorg-planner", {}).get("sources") == ["team:zorg-core"], (out, by.get("zorg-planner")))
    w(os.path.join(core, "_System", "provider-manifest.yaml"),
      "id: zorg-core\ncontract: vault/v1\nplugin_folder: .\ntools_file: ../outside.yaml\n")
    w(os.path.join(d, "outside.yaml"), 'tools:\n  - name: "Outside"\n')
    rc, out, res, _ = run("team", "--store", store, "--home", home)
    check("6.6 a tools_file outside the core is refused", rc == 0 and res.get("team") == {} and
          res.get("skipped") and res["skipped"][0]["core"] == "zorg-core", out)
finally:
    shutil.rmtree(d, ignore_errors=True)

print("\n%s — %d failure(s)" % ("GREEN" if not fails else "RED", fails))
sys.exit(1 if fails else 0)
