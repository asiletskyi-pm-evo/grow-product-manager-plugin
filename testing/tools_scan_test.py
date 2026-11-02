#!/usr/bin/env python3
"""TC-tools-4200 — scripts/tools_scan.py, the tools registry (v4.2.0, references/tool-registry.md).

A fictional home («Zorg») holds every host file the scan reads, each with values planted under the names:
arguments, environment variables, headers, URLs, an install path, an account e-mail, a skill's body, and in the
TOML file values that look like table headers inside multi-line strings and arrays. The scan must give the
names and nothing else — and a mutated scanner that reads one value must be caught by the same check. Then:
merge (seed, observed rows sanitised field by field, nothing refused in the journal, user fields kept, a
cleared field never refilled, not-seen only for a file read this time, an app never sets a connector's state,
the session's `connected` kept by a files-only merge), an unreadable registry never reset, suggest (one record,
own recommended > team > seed, the skill named first, `--need`, `via`, decline per skill, deprecated, no
registry, a skill that is not the plugin's), the never-store filter (whole value before any cut, never echoed),
add from a search with its state, the team list (read-only, checked, a «ні» kept beside it, a list no core
publishes removed, a path outside the core refused) and the export (only shared, only the listed fields,
no file for nothing, the cores' owners named). Every secret-looking value is assembled at run time — none is
written in this file. Stdlib only; run from the repo root:

  env -u GROW_PM_CONTEXT_PATH -u GROW_PM_PROVIDER_PATHS python3 testing/tools_scan_test.py
"""
import hashlib, json, os, shutil, subprocess, sys, tempfile

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


def store_text(store):
    return "".join(open(os.path.join(dp, f), encoding="utf-8").read() for dp, _, fs in os.walk(store) for f in fs)


def reg(store):
    return {t["id"]: t for t in json.load(open(os.path.join(store, "registry.json")))["tools"]}


# Planted values: a marker each, so a leak names itself. Built here, never written as a literal token.
M = {k: "ZORG-PLANTED-%s-%s" % (k, hashlib.sha1(k.encode()).hexdigest()[:10]) for k in (
    "args", "env", "url", "headers", "installpath", "email", "skillbody", "tomlargs", "tomlenv", "tomlurl",
    "desktopenv", "desktopargs", "mlbasic", "mlliteral", "mlarray")}
TOK = "gh" + "p_" + "Zorg0" * 7                       # looks like a key to the never-store filter

d = tempfile.mkdtemp(prefix="tools-scan-")
try:
    home = os.path.join(d, "home")
    store = os.path.join(d, "store")
    w(os.path.join(home, ".claude", "plugins", "installed_plugins.json"), json.dumps({
        "version": 2, "plugins": {
            "zorg-helper@zorg-market": [{"installPath": "/opt/" + M["installpath"], "gitCommitSha": "0" * 40}],
            "grow-product-manager@zorg-market": [{"installPath": "/opt/x"}]}}))
    claude_json = {
        "oauthAccount": {"emailAddress": M["email"] + "@zorg.example"},
        "mcpServers": {"zorg-crm": {"command": "npx", "args": ["--key", M["args"]], "env": {"ZORG_KEY": M["env"]}},
                       "https://mcp.zorg.example/?t=" + TOK: {"command": "x"}},
        "projects": {"/Users/zorg/app": {"mcpServers": {"zorg-docs": {
            "url": "https://docs.zorg.example/mcp?k=" + M["url"], "headers": {"Authorization": "Bearer " + M["headers"]}}}}}}
    w(os.path.join(home, ".claude.json"), json.dumps(claude_json))
    w(os.path.join(home, "Library", "Application Support", "Claude", "claude_desktop_config.json"), json.dumps({
        "mcpServers": {"zorg-metrics": {"command": "/opt/zorg", "args": [M["desktopargs"]], "env": {"T": M["desktopenv"]}}}}))
    w(os.path.join(home, ".codex", "config.toml"), "\n".join([
        'model = "zorg-model"',
        "mcp_servers.zorg-dotted.command = \"zorg\"",
        "[mcp_servers.zorg-search]",
        'command = "zorg-search"',
        'args = ["--key", "%s"]' % M["tomlargs"],
        'instructions = """',
        "[mcp_servers.%s]" % M["mlbasic"],
        '"""',
        "literal = '''",
        '[plugins."%s@m"]' % M["mlliteral"],
        "'''",
        "matrix = [",
        '  ["mcp_servers", "%s"],' % M["mlarray"],
        "[mcp_servers.%s-x]" % M["mlarray"],
        "]",
        "[mcp_servers.zorg-search.env]",
        'ZORG_KEY = "%s"' % M["tomlenv"],
        '[mcp_servers."zorg board"]',
        'url = "https://board.zorg.example/?t=%s"' % M["tomlurl"],
        "[[mcp_servers.zorg-array.tools]]",
        'name = "x"',
        "[mcp_servers]",
        'zorg-table-key = { command = "zorg" }',
        '[plugins."zorg-codex-plugin@zorg-market"]',
        "enabled = true",
        '[plugins."grow-product-manager@zorg-market"]',
        "enabled = true", ""]))
    w(os.path.join(home, ".claude", "skills", "zorg-notes", "SKILL.md"),
      "---\nname: zorg-notes\ndescription: Notes of the Zorg team in one place.\n---\n\nBody " + M["skillbody"] + "\n")
    w(os.path.join(home, ".claude", "skills", "zorg-folded", "SKILL.md"),
      "---\nname: zorg-folded\ndescription: >-\n  Folded text.\n---\n")
    w(os.path.join(home, ".claude", "skills", "zorg-open", "SKILL.md"),
      "---\nname: zorg-open\n\nbody\n" + "line\n" * 40 + "---\ndescription: from the body\n")
    apps = os.path.join(d, "apps.jsonl")
    w(apps, "\n".join(json.dumps(x) for x in [
        {"source": "scan-mac", "name": "Miro", "bundle_id": "com.electron.realtimeboard", "path": "/Applications/Miro.app"},
        {"source": "scan-mac", "name": "zoom.us", "bundle_id": "us.zoom.xos", "path": "/Applications/zoom.us.app"},
        {"source": "scan-mac", "name": "draw.io", "bundle_id": "com.jgraph.drawio.desktop", "path": "/Applications/draw.io.app"},
        {"source": "scan-mac", "name": "Zorg Shop", "bundle_id": "com.zorg.shop", "path": "/Applications/Zorg Shop.app"},
        {"source": "bookmarks", "name": "Notion", "domain": "notion.so"}]) + "\n")
    w(os.path.join(d, "empty.jsonl"), "")

    # ---------------------------------------------------------------- 1. scan: names only
    rc, out, res, rows = run("scan", "--home", home, "--apps-jsonl", apps)
    names = sorted(r["name"] for r in rows)
    check("1.1 scan exits 0 with a TOOLS_RESULT", rc == 0 and res.get("found") == len(rows), out)
    want = sorted(["Miro", "Zoom", "draw.io", "zorg board", "zorg-array", "zorg-codex-plugin", "zorg-crm", "zorg-docs",
                   "zorg-dotted", "zorg-folded", "zorg-helper", "zorg-metrics", "zorg-notes", "zorg-open", "zorg-search",
                   "zorg-table-key"])
    check("1.2 every name from the host files (dotted keys, array tables, keys of [mcp_servers]), skills and apps",
          names == want, names)
    leaked = [k for k, v in M.items() if v in out]
    check("1.3 no planted value reaches the output — not even one shaped like a header inside a multi-line string "
          "or array", not leaked, leaked)
    check("1.4 the plugin itself is not a record", "grow-product-manager" not in out, out)
    check("1.5 an app that matches no seed record and a bookmark stay out",
          "Zorg Shop" not in out and "notion.so" not in out, out)
    by = {r["name"]: r for r in rows}
    check("1.6 one source per file, its host", by["zorg-crm"]["source"] == "scan-claude-code-mcp" and
          by["zorg-helper"]["source"] == "scan-claude-code-plugins" and by["zorg-metrics"]["host"] == "claude-desktop"
          and by["zorg-search"]["source"] == "scan-codex-mcp" and by["zorg-codex-plugin"]["source"] == "scan-codex-plugins"
          and by["zorg-notes"]["source"] == "scan-claude-code-skills" and by["Miro"]["source"] == "scan-apps", rows)
    check("1.7 a TOML sub-table ([mcp_servers.x.env]) is not a second server",
          names.count("zorg-search") == 1 and "env" not in names, names)
    check("1.8 a server named like a key is refused, counted, never shown", TOK not in out and res.get("refused", 0) >= 1, res)
    check("1.9 a folded description and one past an unclosed frontmatter are not kept",
          "description" not in by["zorg-folded"] and "description" not in by["zorg-open"], (by["zorg-folded"], by["zorg-open"]))
    rc, out, res, rows = run("scan", "--home", os.path.join(d, "empty-home"), "--no-apps")
    check("1.10 a home with no host files → nothing found, nothing read, exit 0",
          rc == 0 and res.get("found") == 0 and res.get("sources_read") == [], out)

    # Valid TOML where a value is shaped like a header (whole-branch review): the real server(s) only.
    for k in "ABCDEF":
        h = os.path.join(d, "toml-" + k)
        os.makedirs(os.path.join(h, ".codex"))
        shutil.copy(os.path.join(ROOT, "testing", "fixtures", "tools", "toml", k + ".toml"),
                    os.path.join(h, ".codex", "config.toml"))
        rc, out, res, rows = run("scan", "--home", h, "--no-apps")
        got = sorted(r["name"] for r in rows)
        check("1.10%s TOML %s: the real server only, never the value shaped like a header" % (k.lower(), k),
              got == (["real", "real two"] if k == "F" else ["real"]) and "LEAK" not in out, got)
    h = os.path.join(d, "names-home")
    w(os.path.join(h, ".claude.json"), json.dumps({"mcpServers": {
        "https://mcp.zorg.example/x": {}, "anna@zorg.example": {}, "/opt/zorg/server": {}, "localhost:8080": {},
        "zorg-fine": {}}}))
    w(os.path.join(h, ".claude", "skills", "zorg-links", "SKILL.md"),
      "---\nname: zorg-links\ndescription: See https://zorg.example/docs or write to anna@zorg.example\n---\n")
    w(os.path.join(h, ".claude", "skills", "zorg-bidi", "SKILL.md"),
      "---\nname: zorg-bidi\ndescription: Notes \u202eevil\u202c of the team\n---\n")
    w(os.path.join(h, ".claude", "skills", "knowledge-library", "SKILL.md"),
      "---\nname: knowledge-library\ndescription: a copy of this plugin's own skill\n---\n")
    rc, out, res, rows = run("scan", "--home", h, "--no-apps")
    by = {r["name"]: r for r in rows}
    check("1.10g a URL, an e-mail, a path or host:port is no name", sorted(by) == ["zorg-bidi", "zorg-fine", "zorg-links"]
          and res.get("refused") == 4, (sorted(by), res))
    check("1.10h a description with a URL or an e-mail is dropped; bidi controls are stripped",
          "description" not in by["zorg-links"] and "\u202e" not in by["zorg-bidi"].get("description", "") and
          "evil" in by["zorg-bidi"].get("description", ""), (by["zorg-links"], by["zorg-bidi"]))
    check("1.10i this plugin's own skill under its bare name is no record", "knowledge-library" not in by, sorted(by))

    # Mutation: a scanner that reads the values under a server's name must be caught by check 1.3.
    mut = os.path.join(d, "mut")
    os.makedirs(mut)
    for f in ("ctx_common.py", "ctx_never.py", "landscape_scan.sh"):
        shutil.copy(os.path.join(ROOT, "scripts", f), mut)
    src = open(SCRIPT, encoding="utf-8").read()
    bad = src.replace("out.extend(str(k) for k in n.keys())",          # a reader that takes a value shaped like a name
                      "out.extend(str(v['args'][-1]) for v in n.values() if isinstance(v, dict) and v.get('args'))")
    check("1.11 mutation applies (the key reader is where the test expects it)", bad != src)
    w(os.path.join(mut, "tools_scan.py"), bad)
    shutil.copytree(os.path.join(ROOT, "references"), os.path.join(d, "references"))
    shutil.copytree(os.path.join(ROOT, "skills"), os.path.join(d, "skills"))
    rc, out, res, rows = run("scan", "--home", home, "--no-apps", script=os.path.join(mut, "tools_scan.py"))
    check("1.12 the mutated scanner leaks — and the leak check sees it", any(v in out for v in M.values()), out[:300])

    # ---------------------------------------------------------------- 2. merge
    scanfile = os.path.join(d, "scan.jsonl")
    rc, out, res, rows = run("scan", "--home", home, "--apps-jsonl", apps)
    w(scanfile, out)
    obs = "\n".join(json.dumps(x) for x in [
        {"name": "figma", "state": "connected", "kind": "mcp"},
        {"name": "Atlassian_Rovo", "state": "needs-auth", "kind": "mcp"},
        {"name": "zorg-crm", "state": "connected", "kind": "mcp"},
        {"name": "zorg-account-skill", "kind": "skill", "source": "scan-account"},
        {"name": "https://mcp.zorg.example/x?token=" + TOK, "kind": "mcp", "state": "connected"},
        {"name": "zorg-ok", "kind": "mcp", "host": TOK, "id": TOK, "source": TOK},
        {"name": "3fa85f64-5717-4562-b3fc-2c963f66afa6", "kind": "mcp", "state": "connected"},
        {"name": "grow-product-manager:knowledge-library", "kind": "skill"}]) + "\n"
    obsfile = os.path.join(d, "obs.jsonl")
    w(obsfile, obs)
    rc, out, res, rows = run("merge", "--store", store, "--scan", scanfile, "--observed", obsfile)
    by = reg(store)
    seed = cc.read_yaml_records(open(os.path.join(ROOT, "references", "tools-seed.yaml")).read(), "tools")
    check("2.1 merge exits 0; every seed record is in", rc == 0 and all(s["id"] in by for s in seed), out)
    check("2.2 an app counts for an app (draw.io installed) and never for a connector (Miro, Zoom stay as they were)",
          by["drawio"]["state"] == "installed" and by["zoom"]["state"] == "not-installed" and
          by["miro"]["state"] == "not-installed" and "standalone" in by["zoom"]["hosts"], (by["drawio"], by["zoom"], by["miro"]))
    check("2.3 observed rows: connected and needs-auth; an alias finds the seed record",
          by["figma"]["state"] == "connected" and by["atlassian"]["state"] == "needs-auth", (by["figma"], by["atlassian"]))
    check("2.4 a seed tool nobody saw stays not-installed", by["notebooklm"]["state"] == "not-installed", by["notebooklm"])
    check("2.5 a new server becomes a record with its host; the session's connected wins over the file's installed",
          by["zorg-crm"]["kind"] == "mcp" and set(by["zorg-crm"]["hosts"]) == {"claude-code", "session"} and
          by["zorg-crm"]["state"] == "connected", by.get("zorg-crm"))
    check("2.6 an account row → host account", "account" in by["zorg-account-skill"]["hosts"], by.get("zorg-account-skill"))
    text = store_text(store)
    check("2.7 no planted value in any file of the store", not [k for k, v in M.items() if v in text])
    check("2.8 a refused row reaches no file — the journal included; host, id and source come from closed lists",
          TOK not in text and by["zorg-ok"]["hosts"] == ["session"] and res.get("refused", 0) >= 3, res)
    check("2.9 an opaque id and the plugin's own skill are no records",
          "3fa85f64" not in text and "grow-product-manager:" not in text)
    check("2.10 tools.md is rendered", "| zorg-crm |" in open(os.path.join(store, "tools.md")).read())

    rc, out, res, _ = run("set", "--store", store, "--id", "zorg-crm", "verdict=recommended", "shared=true",
                          "recommended_by=я", "skills=product-analysis", "job=CRM of the Zorg team",
                          "connect=ask the Zorg admin for access")
    check("2.11 set the user's fields", rc == 0, out)
    run("set", "--store", store, "--id", "semrush", "connect=")
    cfg = dict(claude_json)
    cfg["mcpServers"] = {k: v for k, v in claude_json["mcpServers"].items() if k != "zorg-crm"}
    w(os.path.join(home, ".claude.json"), json.dumps(cfg))
    rc, out, res, rows = run("merge", "--store", store, "--rescan", "--home", home, "--apps-jsonl", apps)
    by = reg(store)
    check("2.12 a files-only merge keeps the session's connected (the session is not here to say otherwise)",
          by["figma"]["state"] == "connected" and by["zorg-crm"]["state"] == "connected", (by["figma"], by["zorg-crm"]))
    check("2.13 a rescan keeps verdict, shared, recommended_by", by["zorg-crm"].get("verdict") == "recommended" and
          by["zorg-crm"].get("shared") is True and by["zorg-crm"].get("recommended_by") == "я", by["zorg-crm"])
    check("2.14 a field the user cleared is never filled back by the seed", "connect" not in by["semrush"], by["semrush"])
    rc, out, res, rows = run("merge", "--store", store, "--rescan", "--home", home, "--apps-jsonl", apps,
                             "--observed", os.path.join(d, "empty.jsonl"))
    by = reg(store)
    check("2.15 gone from the host file and not in the session → not-seen, never deleted",
          by.get("zorg-crm", {}).get("state") == "not-seen", by.get("zorg-crm"))
    w(os.path.join(home, ".claude.json"), json.dumps(claude_json)[:40])            # half-written by the host
    rc, out, res, rows = run("merge", "--store", store, "--rescan", "--home", home,
                             "--apps-jsonl", os.path.join(d, "no-apps.jsonl"))
    by = reg(store)
    check("2.16 a half-written file and a failed app scan read nothing — their tools keep their state",
          by["zorg-docs"]["state"] == "installed" and by["drawio"]["state"] == "installed"
          and "scan-claude-code-mcp" not in res.get("sources_covered", []) and "scan-apps" not in res.get("sources_covered", []),
          (by["zorg-docs"], by["drawio"], res))
    w(os.path.join(home, ".claude.json"), json.dumps(claude_json))

    # ---------------------------------------------------------------- 3. suggest / decline
    run("merge", "--store", store, "--observed", obsfile)            # the session sees Figma again
    rc, out, res, rows = run("suggest", "--store", store, "--skill", "diagram-prototyper")
    check("3.1 one record — not FigJam, which comes with the connected Figma (via), not draw.io (installed)",
          rc == 0 and len(rows) == 1 and rows[0]["id"] == "miro", rows)
    rc, out, res, rows = run("suggest", "--store", store, "--skill", "diagram-prototyper", "--need", "mind-map")
    check("3.2 --need mind-map → a mind-map tool", rows and rows[0]["id"] == "miro", rows)
    run("decline", "--store", store, "--skill", "diagram-prototyper", "--id", "miro")
    rc, out, res, rows = run("suggest", "--store", store, "--skill", "diagram-prototyper", "--need", "mind-map")
    check("3.3 after «ні» the next mind-map tool", rows and rows[0]["id"] == "notebooklm", rows)
    run("set", "--store", store, "--id", "gemini", "verdict=recommended")
    rc, out, res, rows = run("suggest", "--store", store, "--skill", "diagram-prototyper", "--need", "mind-map")
    check("3.4 the user's recommended comes first", rows and rows[0]["id"] == "gemini", rows)
    run("set", "--store", store, "--id", "gemini", "verdict=deprecated")
    rc, out, res, rows = run("suggest", "--store", store, "--skill", "diagram-prototyper", "--need", "mind-map")
    check("3.5 deprecated is never offered", rows and rows[0]["id"] == "notebooklm", rows)
    by = reg(store)
    check("3.6 a decline is per skill", by["miro"]["declined"][0]["skill"] == "diagram-prototyper", by["miro"])
    rc, out, res, rows = run("suggest", "--store", store, "--skill", "brainstorm-features")
    check("3.7 another skill still gets the declined tool", rows and rows[0]["id"] == "miro", rows)
    run("decline", "--store", store, "--skill", "meeting-processor", "--id", "fireflies")
    rc, out, res, rows = run("suggest", "--store", store, "--skill", "meeting-processor", "--need", "transcript")
    check("3.8 --need transcript after «ні» to Fireflies → Zoom, not the calendar", rows and rows[0]["id"] == "zoom", rows)
    run("decline", "--store", store, "--skill", "diagram-prototyper", "--id", "miro", "--undo")
    rc, out, res, rows = run("suggest", "--store", store, "--skill", "diagram-prototyper", "--need", "mind-map")
    check("3.9 decline --undo brings it back", rows and rows[0]["id"] == "miro", rows)
    rc, out, res, rows = run("suggest", "--store", os.path.join(d, "no-store"), "--skill", "diagram-prototyper")
    check("3.10 no registry → no record and no error", rc == 0 and not rows and res.get("suggest") is None, out)
    rc, out, res, rows = run("suggest", "--store", store, "--skill", "goal-setter")
    check("3.11 a skill no tool serves → nothing", rc == 0 and not rows, out)
    rc, out, res, rows = run("suggest", "--store", store, "--skill", "diagram-prototyper", "--need", "mind-map",
                             "--exclude", "gemini,chatgpt,notebooklm,figma,drawio,miro")
    check("3.12a --exclude drops what the step's own question offers (nothing else does mind maps here)",
          rc == 0 and not rows, rows)
    rc, out, res, rows = run("suggest", "--store", store, "--skill", "product-research", "--need", "market-data")
    check("3.12 product-research gets a market-data tool", rows and rows[0]["id"] == "similarweb", rows)
    before = open(os.path.join(store, "registry.json")).read()
    rc, out, res, _ = run("decline", "--store", store, "--skill", "use " + TOK, "--id", "miro")
    check("3.13 a --skill that is not the plugin's: exit 2, nothing written, nothing echoed",
          rc == 2 and TOK not in out and open(os.path.join(store, "registry.json")).read() == before, out)

    # ---------------------------------------------------------------- 4. never-store, add
    rc, out, res, _ = run("set", "--store", store, "--id", "zorg-docs", "connect=use " + TOK)
    reg_text = open(os.path.join(store, "registry.json")).read()
    check("4.1 a key in a connect line is refused by kind, exit 2", rc == 2 and "secret" in json.dumps(res), out)
    check("4.2 the value is neither echoed nor stored", TOK not in out and TOK not in reg_text)
    rc, out, res, _ = run("set", "--store", store, "--id", "zorg-docs", "connect=" + "a" * 292 + " " + TOK)
    check("4.3 a key past the length cut is still refused — the whole value is checked first",
          rc == 2 and "ghp_Zor" not in open(os.path.join(store, "registry.json")).read(), out)
    rc, out, res, _ = run("set", "--store", store, "--id", "zorg-docs", "connect: " + TOK)
    check("4.4 a field without «=» is refused without echoing it", rc == 2 and TOK not in out, out)
    rc, out, res, _ = run("set", "--store", store, "--id", "zorg-docs", "colour=blue")
    check("4.5 a field that is not the user's is refused", rc == 2, out)
    rc, out, res, _ = run("set", "--store", store, "--id", "zorg-docs", "verdict=great")
    check("4.6 a verdict outside the list is refused", rc == 2, out)
    rc, out, res, _ = run("add", "--store", store, "--name", "Zorg Academy course", "--kind", "course",
                          "job=product discovery course", "access=paid", "skills=goal-setter")
    check("4.7 add by hand", rc == 0 and res.get("id") == "zorg-academy-course", out)
    rc, out, res, _ = run("add", "--store", store, "--name", "Zorg Whiteboard", "--kind", "mcp",
                          "--source", "registry-search", "--state", "connected", "job=team whiteboard")
    by = reg(store)
    check("4.8 a search result the user picked keeps its source and the state the search gave", rc == 0 and
          by.get("zorg-whiteboard", {}).get("sources") == ["registry-search"] and
          by["zorg-whiteboard"]["state"] == "connected", (out, by.get("zorg-whiteboard")))
    rc, out, res, _ = run("add", "--store", store, "--name", "Zorg Other", "--kind", "mcp", "--state", "connected")
    check("4.9 --state without a search source is refused", rc == 2, out)
    rc, out, res, rows = run("suggest", "--store", store, "--skill", "diagram-prototyper", "--need", "spaceship")
    check("4.10 a need the registry does not know → exit 2, no record", rc == 2 and not rows, out)
    s2 = os.path.join(d, "store-search")
    run("add", "--store", s2, "--name", "Zorg Whiteboard", "--kind", "mcp", "--source", "registry-search",
        "--state", "connected")
    run("merge", "--store", s2, "--observed", os.path.join(d, "empty.jsonl"))
    check("4.11 a search result added as connected becomes not-seen when a session no longer sees it",
          reg(s2)["zorg-whiteboard"]["state"] == "not-seen", reg(s2)["zorg-whiteboard"])

    # ---------------------------------------------------------------- 5. an unreadable registry is never reset
    bad_store = os.path.join(d, "bad-store")
    shutil.copytree(store, bad_store)
    full = open(os.path.join(bad_store, "registry.json")).read()
    w(os.path.join(bad_store, "registry.json"), full[:2000])
    cut = open(os.path.join(bad_store, "registry.json")).read()
    codes = [run("merge", "--store", bad_store, "--rescan", "--home", home, "--no-apps")[0],
             run("add", "--store", bad_store, "--name", "Zorg Wiki", "--kind", "site")[0],
             run("set", "--store", bad_store, "--id", "miro", "verdict=tried")[0],
             run("decline", "--store", bad_store, "--skill", "diagram-prototyper", "--id", "miro")[0],
             run("export", "--store", bad_store, "--home", home)[0]]
    check("5.1 every writing command stops with exit 1 and leaves the file byte for byte",
          codes == [1, 1, 1, 1, 1] and open(os.path.join(bad_store, "registry.json")).read() == cut, codes)
    rc, out, res, rows = run("suggest", "--store", bad_store, "--skill", "diagram-prototyper")
    check("5.2 suggest says nothing, exit 0", rc == 0 and not rows, out)
    rc, out, res, _ = run("merge", "--store", store, "--observed", os.path.join(d, "missing.jsonl"))
    check("5.3 an input file that is not there → exit 2 with a TOOLS_RESULT", rc == 2 and res.get("error"), out)

    # ---------------------------------------------------------------- 6. export
    rc, out, res, _ = run("export", "--store", store, "--home", home)
    exp = open(res["file"], encoding="utf-8").read() if res.get("file") else ""
    recs = cc.read_yaml_records(exp, "tools") if exp else []
    check("6.1 only the shared record goes out", rc == 0 and res.get("exported") == 1 and len(recs) == 1 and
          recs[0]["name"] == "zorg-crm", (out, exp))
    check("6.2 only the listed fields — no state, hosts, sources, declined, seen; «я» never goes out",
          recs and not set(recs[0]) - {"name", "kind", "job", "skills", "contours", "needs", "access", "connect",
                                       "verdict", "recommended_by", "checked", "publishes"}
          and "recommended_by" not in recs[0], recs)
    rc, out, res, _ = run("export", "--store", os.path.join(d, "fresh-store"), "--home", home)
    check("6.3 nothing shared → no file", rc == 0 and res.get("exported") == 0 and res.get("file") is None, out)

    # ---------------------------------------------------------------- 7. team
    core = os.path.join(d, "zorg-core")
    w(os.path.join(core, "_System", "provider-manifest.yaml"),
      "id: zorg-core\ncontract: vault/v1\nplugin_folder: .\nowner_label: the Zorg core owner\ntools_file: _System/tools.yaml\n")
    w(os.path.join(core, "_System", "tools.yaml"), exp.replace('"zorg-crm"', '"Zorg Planner"').replace(
        '"я"', '"Anna Zorg"').replace('"product-analysis"', '"feedback-triage"')
      + '  - name: "Figma"\n    kind: "mcp"\n    skills: ["design-bridge"]\n'
      + '  - name: "Zorg Rocket"\n    kind: "spaceship"\n    verdict: "amazing"\n    skills: "feedback-triage"\n'
      + '  - name: "Zorg Leaky"\n    connect: "use %s"\n    skills: ["feedback-triage"]\n' % TOK)
    w(os.path.join(home, ".grow-pm", "providers", "zorg-core.yaml"),
      "schema: provider-registration/2\nid: zorg-core\nkind: folder\nauthority: team\npaths:\n  - %s\n" % core)
    before = tree_hash(core)
    rc, out, res, _ = run("team", "--store", store, "--home", home)
    tfile = os.path.join(store, "team", "zorg-core.json")
    team = json.load(open(tfile))["tools"] if os.path.isfile(tfile) else []
    rocket = next((t for t in team if t["name"] == "Zorg Rocket"), {})
    check("7.1 the core's list is read, marked team:zorg-core, an unsound record dropped",
          rc == 0 and res.get("team") == {"zorg-core": 3} and res.get("dropped") == 1 and
          all(t["recommended_by"] == "team:zorg-core" for t in team), (out, team))
    check("7.2 a core's fields from closed lists only; a scalar skill becomes a list",
          "kind" not in rocket and "verdict" not in rocket and rocket.get("skills") == ["feedback-triage"], rocket)
    check("7.3 the core is untouched; no key reached the store", tree_hash(core) == before and TOK not in store_text(store))
    check("7.4 tools.md shows «Від команди»", "## Від команди" in open(os.path.join(store, "tools.md")).read())
    rc, out, res, rows = run("suggest", "--store", store, "--skill", "feedback-triage")
    check("7.5 a team record comes before the seed's", rows and rows[0]["name"] == "Zorg Planner" and
          rows[0]["origin"] == "team", rows)
    rc, out, res, rows = run("suggest", "--store", store, "--skill", "feedback-triage", "--need", "board")
    check("7.5a with --need, a team record that names no need still comes before the seed's",
          rows and rows[0]["name"] == "Zorg Planner", rows)
    n_before = len(reg(store))
    rc, out, res, _ = run("decline", "--store", store, "--skill", "feedback-triage", "--id", "zorg-planner")
    rc2, out2, res2, rows2 = run("suggest", "--store", store, "--skill", "feedback-triage")
    check("7.6 «ні» to a team record is kept beside the list — the registry does not grow",
          rc == 0 and res.get("team") is True and len(reg(store)) == n_before and
          not (rows2 and rows2[0]["name"] == "Zorg Planner"), (out, rows2))
    run("decline", "--store", store, "--skill", "feedback-triage", "--id", "zorg-planner", "--undo")
    rc, out, res, _ = run("add", "--store", store, "--from-team", "Zorg Planner")
    check("7.7 «взяти собі» copies the record into the registry", rc == 0 and
          reg(store).get("zorg-planner", {}).get("sources") == ["team:zorg-core"], out)
    rc, out, res, _ = run("export", "--store", store, "--home", home)
    check("7.8 the export names the cores' owners", {"core": "zorg-core", "owner_label": "the Zorg core owner"}
          in (res.get("cores") or []), res)
    w(os.path.join(core, "_System", "provider-manifest.yaml"),
      "id: zorg-core\ncontract: vault/v1\nplugin_folder: .\ntools_file: ../outside.yaml\n")
    w(os.path.join(d, "outside.yaml"), 'tools:\n  - name: "Outside"\n')
    rc, out, res, _ = run("team", "--store", store, "--home", home)
    check("7.9 a tools_file outside the core is refused, and the list read before is removed",
          rc == 0 and res.get("team") == {} and res.get("skipped") and res["skipped"][0]["core"] == "zorg-core"
          and not os.path.isfile(tfile) and "## Від команди" not in open(os.path.join(store, "tools.md")).read(), out)
    kit = os.path.join(ROOT, "examples", "provider-kit", "zorg-core")
    home2 = os.path.join(d, "home2")
    w(os.path.join(home2, ".grow-pm", "providers", "zorg-core.yaml"),
      "schema: provider-registration/2\nid: zorg-core\nkind: folder\npaths:\n  - %s\n" % kit)
    kit_before = tree_hash(kit)
    rc, out, res, _ = run("team", "--store", os.path.join(d, "store2"), "--home", home2)
    check("7.10 the example kit's tools list is read through its manifest", rc == 0 and res.get("team") == {"zorg-core": 2}
          and tree_hash(kit) == kit_before, out)
finally:
    shutil.rmtree(d, ignore_errors=True)

print("\nRESULT: %s (%d failed)" % ("GREEN ✅" if not fails else "RED ❌", fails))
sys.exit(1 if fails else 0)
