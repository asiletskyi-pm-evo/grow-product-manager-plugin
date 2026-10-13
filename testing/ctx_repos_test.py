#!/usr/bin/env python3
"""TC-ctx-3130-repos — scripts/ctx_repos.py: provider registration v1/v2 and `ctx repo list` (since v3.13.0).

The registrations of the fictional "Zorg" (zorg-core: a v1 bundle folder; zorg-growth: a v2 MCP repository)
on a temp HOME and a temp vault, written as `{vault}/Notes/_System/providers/<id>.yaml`. Covers the
normalised keys and their defaults (rank by authority, core_root, namespace, blocks_source, products),
the order and dedupe of registrations, the real HOME never being read, and the command: the table, the
`CTX_RESULT` line, a paused repository, an unreadable registration. No network.
Semantics: references/context-provider-protocol.md §3b. Stdlib only; run from the repo root.
"""
import json, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import ctx as ctxmain  # noqa: E402
import ctx_repos as cr  # noqa: E402

CTX = os.path.join(ROOT, "scripts", "ctx.py")
FIX = os.path.join(ROOT, "testing", "fixtures", "ctx")
fails = 0


def check(name, cond, detail=""):
    global fails
    fails += not cond
    print(("✅" if cond else "❌"), name, ("" if cond else "-> " + str(detail)[:700]))


def read(*parts):
    return open(os.path.join(*parts), encoding="utf-8", newline="").read()


CORE_V1 = """schema: provider-registration/1
id: zorg-core
title: Zorg shared product core
kind: bundle
contract: vault/v1
authority: org
mode: snapshot
access: vpn
paths:
  - {core}
writable:
  - Core/Now.md
index: ""
synced_at: 2026-09-15
source_version: core 0.2, bundle 0.4.0
skip_blocks: []
team: team-alpha
role: pm
jira_write: own
status: active
"""

GROWTH_V2 = """schema: provider-registration/2
id: zorg-growth
title: Zorg Growth
kind: mcp
contract: vault/v1
authority: team
mode: live
access: open
endpoint:
  url: http://127.0.0.1:9/mcp
  root: "ZorgGrowth/"
  headers_env: ZORG_GROWTH_MCP_HEADERS
blocks_file: Growth/_System/context-blocks.md
products:
  - product.zorg-app
blocks_source: mcp
home_record: custom.zorg-growth
skip_blocks:
  - growth.pricing-rules
team: team-alpha
role: pm
jira_write: none
status: active
synced_at: 2026-10-01
source_version: growth 1.4
"""


class Env:
    """A temp HOME with the typical context, a temp vault `Notes` and its providers folder."""

    def __init__(self, d):
        self.home = os.path.join(d, "home")
        self.vault = os.path.join(d, "vault")
        self.core = os.path.join(d, "ZorgCore")
        self.providers = os.path.join(self.vault, "Notes", "_System", "providers")
        os.makedirs(os.path.join(self.home, ".grow-pm"))
        os.makedirs(self.providers)
        os.makedirs(self.core)
        self.text = read(FIX, "typical.md").replace("{{VAULT}}", self.vault)
        self.ctx = os.path.join(self.home, ".grow-pm", "local-context.md")
        open(self.ctx, "w", encoding="utf-8", newline="").write(self.text)

    def reg(self, name, body, home=False):
        d = os.path.join(self.home, ".grow-pm", "providers") if home else self.providers
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, name + ".yaml"), "w", encoding="utf-8", newline="").write(body.replace("{core}", self.core))

    def repos(self):
        return cr.load_repos(self.text, self.home)

    def run(self, *args):
        env = dict(os.environ)
        env.pop("GROW_PM_CONTEXT_PATH", None)
        p = subprocess.run([sys.executable, CTX] + list(args) + ["--home", self.home, "--context", self.ctx],
                           capture_output=True, text=True, env=env, timeout=120)
        lines = [l for l in p.stdout.splitlines() if l.strip()]
        try:
            result = json.loads(lines[-1][len("CTX_RESULT "):]) if lines and lines[-1].startswith("CTX_RESULT ") else None
        except ValueError:
            result = None
        return p.returncode, p.stdout + p.stderr, result


with tempfile.TemporaryDirectory() as d:
    e = Env(d)
    check("no registrations → no repositories", e.repos() == [], e.repos())
    rc, out, res = e.run("repo", "list")
    check("ctx repo list with none says so", rc == 0 and res is not None and res["repos"] == [] and "no repositories" in out, (rc, out))

    e.reg("zorg-core", CORE_V1)
    e.reg("zorg-growth", GROWTH_V2)
    repos = e.repos()
    by_id = {x["id"]: x for x in repos}
    r, g = by_id.get("zorg-core", {}), by_id.get("zorg-growth", {})

    check("v1 registration reads with defaults", r.get("rank") == 1000 and r.get("core_root") == r.get("paths", [None])[0]
          and r.get("namespace") == "zorg-core" and r.get("blocks_source") == "auto" and r.get("products") == [], r)
    check("v1 keys survive", r.get("kind") == "bundle" and r.get("authority") == "org" and r.get("team") == "team-alpha"
          and r.get("role") == "pm" and r.get("jira_write") == "own" and r.get("status") == "active"
          and r.get("synced_at") == "2026-09-15" and r.get("skip_blocks") == [] and r.get("title") == "Zorg shared product core"
          and r.get("access") == "vpn" and r.get("source_version") == "core 0.2, bundle 0.4.0", r)
    check("v1 paths are normalised, _file is the registration", r.get("paths") == [os.path.normpath(e.core)]
          and r.get("_file") == os.path.join(e.providers, "zorg-core.yaml"), r)
    check("v1 has no endpoint: empty url, root and headers_env, no home record",
          r.get("endpoint") == {"url": "", "root": "", "headers_env": ""} and r.get("home_record") == ""
          and r.get("blocks_file") == "", r)
    check("v2 keys are read", g.get("endpoint", {}).get("url") == "http://127.0.0.1:9/mcp"
          and g.get("endpoint", {}).get("root") == "ZorgGrowth/"
          and g.get("blocks_file") == "Growth/_System/context-blocks.md" and g.get("rank") == 500
          and g.get("products") == ["product.zorg-app"], g)
    check("v2 optional keys are read", g.get("endpoint", {}).get("headers_env") == "ZORG_GROWTH_MCP_HEADERS"
          and g.get("blocks_source") == "mcp" and g.get("home_record") == "custom.zorg-growth"
          and g.get("skip_blocks") == ["growth.pricing-rules"] and g.get("namespace") == "zorg-growth"
          and g.get("jira_write") == "none" and g.get("core_root") == "" and g.get("paths") == [], g)
    check("two repos, one product", [x["id"] for x in repos] == ["zorg-core", "zorg-growth"], [x["id"] for x in repos])

    rc, out, res = e.run("repo", "list")
    check("ctx repo list prints both", rc == 0 and "zorg-core" in out and "zorg-growth" in out and res is not None
          and res["repos"][1]["rank"] == 500, (rc, out))
    check("the table has the columns and the dash for what has no state yet",
          all(h in out.splitlines()[0] for h in ("id", "kind", "products", "rank", "access", "blocks", "version", "checked"))
          and "—" in out, out)
    rowc = [l for l in out.splitlines() if l.startswith("zorg-core")][0]
    rowg = [l for l in out.splitlines() if l.startswith("zorg-growth")][0]
    check("a row: kind, products (all / the list), rank, access, registration version",
          "bundle" in rowc and "all" in rowc and "1000" in rowc and "vpn" in rowc and "core 0.2" in rowc
          and "mcp" in rowg and "product.zorg-app" in rowg and "500" in rowg and "open" in rowg and "growth 1.4" in rowg,
          (rowc, rowg))
    check("CTX_RESULT is last and carries command and action", out.splitlines()[-1].startswith("CTX_RESULT ")
          and res["command"] == "repo" and res["action"] == "list" and res["ok"] is True, res)
    rc, out, res = e.run("repo", "list", "--json")
    check("--json is accepted and the result line stays last", rc == 0 and res is not None
          and [x["id"] for x in res["repos"]] == ["zorg-core", "zorg-growth"]
          and res["repos"][1]["endpoint"]["root"] == "ZorgGrowth/", (rc, out))
    check("repo is a reading command: nothing is written", not os.path.exists(os.path.join(e.vault, "Notes", "_System", "context"))
          and not os.path.exists(os.path.join(e.home, ".grow-pm", "snapshots")), os.listdir(os.path.join(e.home, ".grow-pm")))
    rc, out, res = e.run("repo")
    check("repo without an action is a usage error", rc == 3 and res is not None and res["ok"] is False, (rc, out))
    try:
        ctxmain.build_parser().parse_args(["repo"])
        said = None
    except ctxmain.Usage as ex:
        said = str(ex)
    check("…and the parser asks for the action", said is not None and "action" in said, said)
    rc, out, res = e.run("repo", "bogus")
    check("repo with an unknown action is a usage error", rc == 3 and res is not None and res["ok"] is False, (rc, out))

    # --- a paused repository is listed, as paused
    e.reg("zorg-growth", GROWTH_V2.replace("status: active", "status: paused"))
    rc, out_paused, res = e.run("repo", "list")
    check("a paused repo is listed as paused", rc == 0 and "paused" in out_paused and res["repos"][1]["status"] == "paused",
          out_paused)
    check("only the paused repo says paused", "paused" not in [l for l in out_paused.splitlines() if l.startswith("zorg-core")][0],
          out_paused)

    # --- an unreadable registration is named, not silently dropped
    e.reg("zorg-broken", "id: zorg-broken\nendpoint:\n  nested:\n    deeper: 1\n")
    rc, out, res = e.run("repo", "list")
    check("an unreadable registration is named", rc == 0 and "zorg-broken.yaml" in out and "unsupported YAML" in out
          and [x["id"] for x in res["repos"]] == ["zorg-core", "zorg-growth"]
          and res.get("unreadable") and "zorg-broken.yaml" in res["unreadable"][0]["file"], (rc, out))
    os.remove(os.path.join(e.providers, "zorg-broken.yaml"))

with tempfile.TemporaryDirectory() as d:
    e = Env(d)
    # --- ranks: authority decides, an explicit rank wins, bad values fall back
    e.reg("a-personal", "id: a-personal\nkind: mcp\nauthority: personal\n")
    e.reg("b-team", "id: b-team\nkind: mcp\nauthority: team\n")
    e.reg("c-org", "id: c-org\nkind: mcp\nauthority: org\n")
    e.reg("d-none", "id: d-none\nkind: mcp\n")
    e.reg("e-explicit", "id: e-explicit\nkind: mcp\nauthority: org\nrank: 250\n")
    e.reg("f-quoted", "id: f-quoted\nkind: mcp\nauthority: org\nrank: \"750\"\n")
    e.reg("g-bad", "id: g-bad\nkind: mcp\nauthority: team\nrank: high\n")
    ranks = {x["id"]: x["rank"] for x in e.repos()}
    check("rank by authority: personal 100, team 500, org 1000",
          ranks.get("a-personal") == 100 and ranks.get("b-team") == 500 and ranks.get("c-org") == 1000, ranks)
    check("no authority reads as org (the bundle builder's default)", ranks.get("d-none") == 1000, ranks)
    check("an explicit rank wins, quoted or not", ranks.get("e-explicit") == 250 and ranks.get("f-quoted") == 750, ranks)
    check("a rank that is not a whole number falls back to the authority's", ranks.get("g-bad") == 500, ranks)
    check("every rank is an int", all(type(v) is int for v in ranks.values()), ranks)

with tempfile.TemporaryDirectory() as d:
    e = Env(d)
    # --- explicit values of the optional keys, and the fallbacks of the invalid ones
    e.reg("h-full", """id: h-full
kind: folder
authority: team
paths:
  - {core}/Shared
core_root: {core}/Shared/Core
namespace: hcore
blocks_source: paths
products: product.zorg-lite
""")
    e.reg("i-bundle-explicit", """id: i-bundle-explicit
kind: bundle
paths:
  - {core}
core_root: {core}/Inner
blocks_source: sideways
""")
    e.reg("j-folder", "id: j-folder\nkind: folder\npaths:\n  - {core}\n")
    e.reg("k-bundle-nopath", "id: k-bundle-nopath\nkind: bundle\n")
    by = {x["id"]: x for x in e.repos()}
    h, i, j, k = by.get("h-full", {}), by.get("i-bundle-explicit", {}), by.get("j-folder", {}), by.get("k-bundle-nopath", {})
    check("explicit core_root and namespace win; a single product given as text is a list",
          h.get("core_root") == os.path.normpath(os.path.join(e.core, "Shared", "Core")) and h.get("namespace") == "hcore"
          and h.get("blocks_source") == "paths" and h.get("products") == ["product.zorg-lite"], h)
    check("an explicit core_root on a bundle beats paths[0]; an unknown blocks_source reads as auto",
          i.get("core_root") == os.path.normpath(os.path.join(e.core, "Inner")) and i.get("blocks_source") == "auto", i)
    check("core_root defaults to paths[0] for a bundle only", j.get("core_root") == "" and j.get("paths") == [os.path.normpath(e.core)]
          and k.get("core_root") == "" and k.get("paths") == [], (j, k))

with tempfile.TemporaryDirectory() as d:
    e = Env(d)
    # --- registrations kept in ~/.grow-pm/providers (no vault) are read from the given HOME, never the real one
    e.reg("zorg-home", "id: zorg-home\nkind: mcp\nauthority: team\n", home=True)
    e.reg("zorg-dup", "id: zorg-dup\ntitle: from the vault\nkind: mcp\n")
    e.reg("zorg-dup", "id: zorg-dup\ntitle: from home\nkind: mcp\n", home=True)
    repos = e.repos()
    ids = [x["id"] for x in repos]
    check("registrations in the home folder are read; the vault's wins on the same id",
          sorted(ids) == ["zorg-dup", "zorg-home"] and ids.index("zorg-dup") < ids.index("zorg-home")
          and {x["id"]: x["title"] for x in repos}["zorg-dup"] == "from the vault", repos)
    only = cr.load_repos(e.text, e.home, extra_dirs=[])
    check("extra_dirs replaces the home folder (as find_registrations does)", [x["id"] for x in only] == ["zorg-dup"], only)
    skipped = []
    e.reg("zorg-bad", "id: zorg-bad\n\tkind: mcp\n")
    cr.load_repos(e.text, e.home, skipped=skipped)
    check("skipped collects (file, reason) of unreadable registrations",
          len(skipped) == 1 and skipped[0][0].endswith("zorg-bad.yaml") and "unsupported YAML" in skipped[0][1], skipped)

print("RESULT:", "GREEN ✅" if not fails else "RED ❌", "(%d failed)" % fails)
sys.exit(1 if fails else 0)
