#!/usr/bin/env python3
"""TC-ctx-3130-repos — scripts/ctx_repos.py: provider registration v1/v2, `ctx repo list` and `fetch` (since v3.13.0).

The registrations of the fictional "Zorg" (zorg-core: a v1 bundle folder; zorg-growth: a v2 MCP repository)
on a temp HOME and a temp vault, written as `{vault}/Notes/_System/providers/<id>.yaml`. Covers the
normalised keys and their defaults (rank by authority, core_root, namespace, blocks_source, products),
the order and dedupe of registrations, the real HOME never being read, and the command: the table, the
`CTX_RESULT` line, a paused repository, an unreadable registration. Then `fetch` — a repository's blocks
("theirs") from the fake MCP server (testing/mcp_fake.py, 127.0.0.1) or from the core folder, the team
block from the folder, the fallback order of blocks_source, errors (a dead server, a server's error, a file
that never arrives, a bad answer), skip_blocks, the most common version, and that nothing is written.
Semantics: references/context-provider-protocol.md §3b. Stdlib only; run from the repo root.
"""
import contextlib, datetime, hashlib, io, json, os, re, shutil, socket, stat, subprocess, sys, tempfile, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "testing"))
os.environ["NO_PROXY"] = "127.0.0.1,localhost"          # the fake is local; a proxy in the environment must not see it
os.environ["no_proxy"] = "127.0.0.1,localhost"
import ctx as ctxmain  # noqa: E402
import ctx_mcp as cm  # noqa: E402
import ctx_repos as cr  # noqa: E402
from mcp_fake import FakeMcp  # noqa: E402

cm.McpClient.BACKOFF = 0.0                                # no pause between retries in tests

CTX = os.path.join(ROOT, "scripts", "ctx.py")
FIX = os.path.join(ROOT, "testing", "fixtures", "ctx")
REPOS_FIX = os.path.join(ROOT, "testing", "fixtures", "ctx-repos")
CORE_FIX = os.path.join(ROOT, "testing", "fixtures", "context-connect", "zorg-core")
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
    e.reg("g-dashes", "id: g-dashes\nkind: mcp\nauthority: org\nrank: --5\n")
    e.reg("g-super", "id: g-super\nkind: mcp\nauthority: personal\nrank: \u00b2\n")
    e.reg("g-super-quoted", "id: g-super-quoted\nkind: mcp\nauthority: team\nrank: \"\u00b2\"\n")
    e.reg("g-float", "id: g-float\nkind: mcp\nauthority: org\nrank: 2.5\n")
    ranks = {x["id"]: x["rank"] for x in e.repos()}
    check("rank by authority: personal 100, team 500, org 1000",
          ranks.get("a-personal") == 100 and ranks.get("b-team") == 500 and ranks.get("c-org") == 1000, ranks)
    check("no authority reads as org (the bundle builder's default)", ranks.get("d-none") == 1000, ranks)
    check("an explicit rank wins, quoted or not", ranks.get("e-explicit") == 250 and ranks.get("f-quoted") == 750, ranks)
    check("a rank that is not a whole number falls back to the authority's", ranks.get("g-bad") == 500
          and ranks.get("g-float") == 1000, ranks)
    check("a rank that only looks like a number (--5, a superscript digit) falls back, and `repo list` survives it",
          ranks.get("g-dashes") == 1000 and ranks.get("g-super") == 100 and ranks.get("g-super-quoted") == 500, ranks)
    rc, out, res = e.run("repo", "list")
    check("…a hand-edited rank never fails the command", rc == 0 and res is not None and res["ok"] is True
          and {x["id"]: x["rank"] for x in res["repos"]}.get("g-dashes") == 1000, (rc, out[-300:]))
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
    e.reg("l-mcp", "id: l-mcp\nkind: mcp\nendpoint:\n  url: http://127.0.0.1:9/mcp\n")
    by = {x["id"]: x for x in e.repos()}
    h, i, j, k = by.get("h-full", {}), by.get("i-bundle-explicit", {}), by.get("j-folder", {}), by.get("k-bundle-nopath", {})
    m = by.get("l-mcp", {})
    check("explicit core_root and namespace win; a single product given as text is a list",
          h.get("core_root") == os.path.normpath(os.path.join(e.core, "Shared", "Core")) and h.get("namespace") == "hcore"
          and h.get("blocks_source") == "paths" and h.get("products") == ["product.zorg-lite"], h)
    check("an explicit core_root on a bundle beats paths[0]; an unknown blocks_source reads as auto",
          i.get("core_root") == os.path.normpath(os.path.join(e.core, "Inner")) and i.get("blocks_source") == "auto", i)
    check("core_root defaults to paths[0] for a bundle and for a folder (its path is the core itself)",
          j.get("core_root") == os.path.normpath(e.core) and j.get("core_root") == j.get("paths", [None])[0]
          and i.get("core_root") != i.get("paths", [None])[0], (i, j))
    check("…a mcp repository has no core folder; a bundle with no path has none either",
          m.get("core_root") == "" and m.get("paths") == [] and k.get("core_root") == "" and k.get("paths") == [], (k, m))

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

# =============================================================================== fetch
GROWTH_PATH = "ZorgGrowth/Growth/_System/context-blocks.md"          # Ruling P1: endpoint.root + blocks_file
GROWTH_FILE = "Growth/_System/context-blocks.md"
GROWTH_TEXT = read(REPOS_FIX, "zorg-growth", *GROWTH_FILE.split("/"))
CORE_BLOCKS_FILE = "Core/_System/context-blocks.md"
HDR_VAR = "ZORG_GROWTH_MCP_HEADERS"
os.environ.pop(HDR_VAR, None)


def tree_state(*roots):
    """Every path under the roots with its mode, size, mtime and (for files) a hash — to prove nothing was written."""
    out = {}
    for r in roots:
        for dp, dn, fn in os.walk(r):
            for n in dn + fn:
                p = os.path.join(dp, n)
                st = os.lstat(p)
                h = hashlib.sha1(open(p, "rb").read()).hexdigest() if stat.S_ISREG(st.st_mode) else ""
                out[p] = (st.st_mode, st.st_size, st.st_mtime_ns, h)
    return out


def repo_of(reg):
    """A registration dict as `find_registrations` reads it → the repository."""
    return cr.normalise(reg)


def region(ns, bid, v, body):
    return "<!-- %s:begin id=%s v=%s -->\n%s\n<!-- %s:end id=%s -->" % (ns, bid, v, body, ns, bid)


def blocks_of(*regions):
    return "# Blocks\n\n" + "\n\n".join(regions) + "\n"


def calls_of(fake):
    return [s["body"]["params"] for s in fake.seen if s["method"] == "tools/call"]


with tempfile.TemporaryDirectory() as d:
    core = os.path.join(d, "ZorgCore")
    growth = os.path.join(d, "ZorgGrowthCore")
    home = os.path.join(d, "home")
    shutil.copytree(CORE_FIX, core)
    shutil.copytree(os.path.join(REPOS_FIX, "zorg-growth"), growth)
    os.makedirs(os.path.join(home, ".grow-pm"))
    before_cores = tree_state(core, growth)

    def core_repo(**kw):
        reg = {"id": "zorg-core", "kind": "bundle", "paths": [core], "blocks_file": CORE_BLOCKS_FILE, "team": "team-alpha",
               "jira_write": "own"}
        reg.update(kw)
        return repo_of(reg)

    def growth_repo(url="", **kw):
        reg = {"id": "zorg-growth", "kind": "mcp", "blocks_file": GROWTH_FILE, "blocks_source": "mcp",
               "endpoint": {"url": url, "root": "ZorgGrowth/", "headers_env": ""}, "team": "team-alpha"}
        reg.update(kw)
        return repo_of(reg)

    # --- the folder
    f = cr.fetch(core_repo())
    check("fetch returns the documented keys",
          set(f) == {"source", "version", "blocks", "team", "team_source", "error", "checked"}, sorted(f))
    check("folder source: the blocks of the core's blocks file and nothing else",
          f["source"] == "folder" and set(f["blocks"]) == {"scope", "product", "teams"} and f["error"] is None, f)
    scope = f["blocks"].get("scope", "")
    check("a block is the whole region, markers included, with no newline after the end marker",
          scope == "<!-- zorg-core:begin id=scope v=0.4 -->\n### Scope of work\nThe user works on Zorg App only.\n"
                   "<!-- zorg-core:end id=scope -->", repr(scope))
    check("the version is the one on the blocks", f["version"] == "0.4", f["version"])
    ff = cr.fetch(core_repo(blocks_source="paths"))
    check("blocks_source paths reads the folder", ff["source"] == "folder" and ff["blocks"] == f["blocks"], ff)
    check("a v1 bundle registration names no blocks_file: the core's manifest does",
          cr.fetch(core_repo(blocks_file=""))["blocks"] == f["blocks"], cr.fetch(core_repo(blocks_file="")))
    f_skip = cr.fetch(core_repo(skip_blocks=["product"]))
    check("skip_blocks are dropped", set(f_skip["blocks"]) == {"scope", "teams"} and f_skip["error"] is None, f_skip["blocks"])
    check("…and the version still tells the source's", f_skip["version"] == "0.4", f_skip["version"])

    # --- the team block: from the folder only
    check("team block from the folder: the core's team region, generated from the card and the people",
          f["team"] is not None and f["team"].startswith("<!-- zorg-core:begin id=team ")
          and f["team"].endswith("<!-- zorg-core:end id=team -->") and f["team_source"] == "folder", f["team"])
    check("…a block the way the connect flow builds it (version of the role model, card, members of the team)",
          "v=0.2 -->" in f["team"].splitlines()[0] and "### Team: Alpha" in f["team"] and "Alex One" in f["team"]
          and "own project (PROJ)" in f["team"], f["team"])
    check("…the registration's team id is team-<key>; the bare key works too",
          cr.fetch(core_repo(team="alpha"))["team"] == f["team"], "")
    check("…jira_write comes from the registration", "read only" in cr.fetch(core_repo(jira_write="none"))["team"], "")
    check("no team in the registration → no team block", cr.fetch(core_repo(team=""))["team"] is None
          and cr.fetch(core_repo(team=""))["team_source"] is None, "")
    check("a team the role model does not know → no team block, blocks still there",
          cr.fetch(core_repo(team="team-nobody"))["team"] is None and cr.fetch(core_repo(team="team-nobody"))["source"] == "folder", "")

    # --- the checked time
    stamp = datetime.datetime(2026, 10, 13, 12, 0, 0, tzinfo=datetime.timezone.utc)
    check("checked is the time given, as ISO", cr.fetch(core_repo(), now=stamp)["checked"] == "2026-10-13T12:00:00+00:00",
          cr.fetch(core_repo(), now=stamp)["checked"])
    got = cr.fetch(core_repo())["checked"]
    try:
        parsed = datetime.datetime.fromisoformat(got)
        fresh = parsed.tzinfo is not None and abs((datetime.datetime.now(datetime.timezone.utc) - parsed).total_seconds()) < 60
    except ValueError:
        fresh = False
    check("…by default now, ISO with the offset", fresh, got)

    # --- MCP
    os.environ.pop(HDR_VAR, None)
    with FakeMcp(tree={GROWTH_PATH: GROWTH_TEXT}) as fake:
        fm = cr.fetch(growth_repo(fake.url))
        fg = cr.fetch(growth_repo(blocks_source="paths", kind="folder", paths=[growth]))
        check("MCP source: the note's content, parsed into blocks of the repository's namespace",
              fm["source"] == "mcp" and set(fm["blocks"]) == {"growth-metrics", "team"} and fm["error"] is None
              and fm["version"] == "0.1", fm)
        check("MCP and folder give the same blocks", fm["blocks"] == fg["blocks"] and fg["source"] == "folder", (fm["blocks"], fg["blocks"]))
        check("the server path is endpoint.root + blocks_file (plain concatenation)",
              [c["name"] for c in calls_of(fake)] == ["vault_get_note"]
              and calls_of(fake)[0]["arguments"] == {"path": GROWTH_PATH}, calls_of(fake))
        check("an MCP repository has no core folder: no team block", fm["team"] is None and fm["team_source"] is None, fm)
        check("the engine only called what the allow-list names", all(c["name"] in cm.ALLOWED for c in calls_of(fake)), calls_of(fake))
        fs = cr.fetch(growth_repo(fake.url, skip_blocks=["team"]))
        check("skip_blocks apply to an MCP repository too", set(fs["blocks"]) == {"growth-metrics"}, fs["blocks"])
        fa = cr.fetch(growth_repo(fake.url, blocks_source="auto"))
        check("auto: the server first when it answers the handshake", fa["source"] == "mcp" and fa["blocks"] == fm["blocks"], fa)
        n = len(calls_of(fake))
        fh = cr.fetch(core_repo(blocks_source="auto", endpoint={"url": fake.url, "root": "ZorgGrowth/", "headers_env": ""},
                                blocks_file=GROWTH_FILE, namespace="zorg-growth"))
        check("blocks from the server, the team block from the core folder", fh["source"] == "mcp"
              and set(fh["blocks"]) == {"growth-metrics", "team"} and fh["team_source"] == "folder"
              and fh["team"].startswith("<!-- zorg-core:begin id=team "), fh)

        seen = []

        def factory(url, headers=None):
            seen.append((url, headers))
            return cm.McpClient(url, headers=headers, probe_timeout=2.0, retries=0)

        cr.fetch(growth_repo(fake.url), client_factory=factory)
        check("client_factory is called with the endpoint url and the (empty) headers", seen == [(fake.url, {})], seen)

    with FakeMcp(tree={GROWTH_PATH: GROWTH_TEXT}, require_headers={"X-Token": "tok-9f3a"}) as fake:
        repo = growth_repo(fake.url, endpoint={"url": fake.url, "root": "ZorgGrowth/", "headers_env": HDR_VAR})
        os.environ[HDR_VAR] = "X-Token: tok-9f3a"
        fh = cr.fetch(repo)
        check("the header named by headers_env is read from the environment and sent", fh["source"] == "mcp" and fh["error"] is None
              and all(s["headers"].get("X-Token") == "tok-9f3a" for s in fake.seen), fh)
        os.environ.pop(HDR_VAR)
        fn = cr.fetch(repo)
        check("without the variable the server says no: unreachable, naming the variable (not a value)",
              fn["source"] is None and "unreachable" in fn["error"] and HDR_VAR in fn["error"] and "tok-9f3a" not in fn["error"], fn)
        os.environ[HDR_VAR] = "X-Token: wrong-1c2d"
        fw = cr.fetch(repo)
        check("a wrong secret never reaches the error", fw["source"] is None and "wrong-1c2d" not in json.dumps(fw), fw)
        os.environ.pop(HDR_VAR)

    # --- errors and fallbacks
    sock = socket.socket()                                  # a port nobody listens on
    sock.bind(("127.0.0.1", 0))
    dead = "http://127.0.0.1:%d/mcp" % sock.getsockname()[1]
    sock.close()
    t0 = time.time()
    fx = cr.fetch(growth_repo(dead))
    check("mcp only and down → error, no blocks", fx["source"] is None and fx["blocks"] == {} and "unreachable" in fx["error"]
          and fx["team"] is None and fx["version"] is None, fx)
    check("…a dead port does not stall it", time.time() - t0 < 8, time.time() - t0)
    fd = cr.fetch(core_repo(blocks_source="auto", endpoint={"url": dead, "root": "", "headers_env": ""}))
    check("auto falls back to the folder when MCP is down", fd["source"] == "folder" and fd["error"] is None
          and fd["blocks"] == f["blocks"] and fd["team_source"] == "folder", fd)
    fdo = cr.fetch(growth_repo(dead, blocks_source="auto"))
    check("auto with MCP down and no folder → both reasons in the error", fdo["source"] is None and "unreachable" in fdo["error"]
          and "folder" in fdo["error"], fdo)
    fne = cr.fetch(growth_repo("", blocks_source="mcp"))
    check("mcp with no endpoint url in the registration says so", fne["source"] is None and "endpoint" in fne["error"], fne)
    fnf = cr.fetch(core_repo(blocks_file="no/such.md"))
    check("a folder repository with no endpoint under auto does not mention MCP", fnf["source"] is None and "such.md" in fnf["error"]
          and "MCP" not in fnf["error"], fnf)

    with FakeMcp(tree={}) as fake:
        fe = cr.fetch(core_repo(blocks_source="auto", endpoint={"url": fake.url, "root": "", "headers_env": ""}))
        check("server answers an error for the path → folder", fe["source"] == "folder" and fe["error"] is None
              and fe["blocks"] == f["blocks"], fe)
        fo = cr.fetch(growth_repo(fake.url))
        check("…mcp only: no blocks, the server's words are in the error", fo["source"] is None and fo["blocks"] == {}
              and "Note not found" in fo["error"], fo)
    with FakeMcp(tree={GROWTH_PATH: GROWTH_TEXT}) as fake:
        fake.handlers["vault_get_note"] = lambda args: ({"path": "x", "content": 5}, False)
        check("a note whose content is not text → error, not a crash", cr.fetch(growth_repo(fake.url))["source"] is None
              and "content" in cr.fetch(growth_repo(fake.url))["error"], cr.fetch(growth_repo(fake.url)))
        fake.handlers["vault_get_note"] = lambda args: ({"path": "x"}, False)
        check("a note with no content at all → error", cr.fetch(growth_repo(fake.url))["source"] is None, "")
        fake.handlers["vault_get_note"] = lambda args: ("this is not json", False)
        check("a tool answer that is not JSON → error", cr.fetch(growth_repo(fake.url))["source"] is None
              and "JSON" in cr.fetch(growth_repo(fake.url))["error"], cr.fetch(growth_repo(fake.url)))
        fake.handlers["vault_get_note"] = lambda args: ("something broke", True)
        check("isError → error", cr.fetch(growth_repo(fake.url))["source"] is None, "")
        fake.handlers["vault_get_note"] = lambda args: ([1, 2], False)
        check("a JSON list instead of the note → error", cr.fetch(growth_repo(fake.url))["source"] is None, "")
        fb = cr.fetch(core_repo(blocks_source="auto", endpoint={"url": fake.url, "root": "", "headers_env": ""}))
        check("…and under auto a bad answer means the folder", fb["source"] == "folder" and fb["blocks"] == f["blocks"], fb)
    for label, kw in (("an HTTP 500", {"fail_status": 500}), ("a JSON-RPC error", {"rpc_error": "boom"}), ("a dropped connection", {"drop": -1})):
        with FakeMcp(tree={GROWTH_PATH: GROWTH_TEXT}, **kw) as fake:
            fr = cr.fetch(growth_repo(fake.url))
            frb = cr.fetch(core_repo(blocks_source="auto", endpoint={"url": fake.url, "root": "", "headers_env": ""}))
            check("%s → error, not a crash; auto → folder" % label, fr["source"] is None and fr["error"]
                  and frb["source"] == "folder" and frb["blocks"] == f["blocks"], (fr, frb))
    with FakeMcp(tree={GROWTH_PATH: GROWTH_TEXT}) as fake:
        fake.raw_result = {"content": 5, "isError": False}
        fr = cr.fetch(growth_repo(fake.url))
        check("a server that sends a number as the content → error, not a TypeError", fr["source"] is None and fr["error"], fr)

    # --- a core file that never arrives
    saved = os.environ.get("GROW_PM_CTX_READ_TIMEOUT")
    os.environ["GROW_PM_CTX_READ_TIMEOUT"] = "0.2"
    fifo_core = os.path.join(d, "FifoCore")
    os.makedirs(os.path.join(fifo_core, "Core", "_System"))
    fifo = os.path.join(fifo_core, "Core", "_System", "context-blocks.md")
    os.mkfifo(fifo)
    t0 = time.time()
    fi = cr.fetch(repo_of({"id": "zorg-fifo", "kind": "folder", "paths": [fifo_core], "blocks_file": CORE_BLOCKS_FILE}))
    took = time.time() - t0
    check("a core file that never arrives → error naming it, within the time budget", fi["source"] is None and fi["blocks"] == {}
          and "not available" in fi["error"] and took < 5, (fi, took))
    try:                                                    # let the reader thread out of open()
        os.close(os.open(fifo, os.O_WRONLY | os.O_NONBLOCK))
    except OSError:
        pass
    if hasattr(os, "geteuid") and os.geteuid() != 0:
        nr = os.path.join(d, "NoReadCore")
        shutil.copytree(CORE_FIX, nr)
        bf = os.path.join(nr, "Core", "_System", "context-blocks.md")
        os.chmod(bf, 0)
        fi2 = cr.fetch(repo_of({"id": "zorg-noread", "kind": "folder", "paths": [nr], "blocks_file": CORE_BLOCKS_FILE}))
        os.chmod(bf, 0o644)
        check("a core file without read permission → error, not available", fi2["source"] is None and "not available" in fi2["error"], fi2)
    # the people of the team come through the same budget: a card that never arrives costs the team block, not the fetch
    slow = os.path.join(d, "SlowCore")
    shutil.copytree(CORE_FIX, slow)
    pipe = os.path.join(slow, "Core", "People", "zz-slow.md")
    os.mkfifo(pipe)
    t0 = time.time()
    fsl = cr.fetch(repo_of({"id": "zorg-slow", "namespace": "zorg-core", "kind": "bundle", "paths": [slow], "blocks_file": CORE_BLOCKS_FILE, "team": "team-alpha"}))
    check("a people card that never arrives → no team block within the budget, the blocks stay",
          fsl["source"] == "folder" and fsl["blocks"] == f["blocks"] and fsl["team"] is None and time.time() - t0 < 5, (fsl, time.time() - t0))
    try:
        os.close(os.open(pipe, os.O_WRONLY | os.O_NONBLOCK))
    except OSError:
        pass
    if saved is None:
        os.environ.pop("GROW_PM_CTX_READ_TIMEOUT")
    else:
        os.environ["GROW_PM_CTX_READ_TIMEOUT"] = saved

    # --- a core whose team block cannot be built
    nomf = os.path.join(d, "NoManifestCore")
    os.makedirs(os.path.join(nomf, "Core", "_System"))
    shutil.copy(os.path.join(CORE_FIX, CORE_BLOCKS_FILE), os.path.join(nomf, CORE_BLOCKS_FILE))
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        fnm = cr.fetch(repo_of({"id": "zorg-core", "kind": "bundle", "paths": [nomf], "blocks_file": CORE_BLOCKS_FILE, "team": "team-alpha"}))
    check("no manifest in the core → blocks yes, team no, and nothing printed (the builder's exit is not ours)",
          fnm["source"] == "folder" and set(fnm["blocks"]) == {"scope", "product", "teams"} and fnm["team"] is None
          and out.getvalue() == "", (fnm, out.getvalue()))
    badj = os.path.join(d, "BadJsonCore")
    shutil.copytree(CORE_FIX, badj)
    open(os.path.join(badj, "Core", "_System", "access-bundles.json"), "w", encoding="utf-8").write("{ not json")
    fbj = cr.fetch(repo_of({"id": "zorg-core", "kind": "bundle", "paths": [badj], "blocks_file": CORE_BLOCKS_FILE, "team": "team-alpha"}))
    check("a role model that is not JSON → no team block, blocks stay", fbj["source"] == "folder" and fbj["team"] is None
          and fbj["blocks"] == f["blocks"], fbj)

    # --- the blocks file: what counts as a block
    def folder_with(text, **kw):
        c = os.path.join(d, "Case%d" % len(os.listdir(d)))
        os.makedirs(os.path.join(c, "Core"))
        open(os.path.join(c, "Core", "blocks.md"), "w", encoding="utf-8", newline="").write(text)
        reg = {"id": "zorg-case", "kind": "folder", "paths": [c], "blocks_file": "Core/blocks.md"}
        reg.update(kw)
        return cr.fetch(repo_of(reg))

    mixed = blocks_of(region("zorg-core", "scope", "0.4", "### Scope"), region("zorg-other", "scope", "9.9", "### Not ours"),
                      region("zorg-core", "growth.pricing-rules", "0.4", "### Pricing"),
                      region("zorg-core", "teams", "0.3", "### Teams"), region("zorg-core", "map", "0.4", "### Map"))
    fm_ = folder_with(mixed, namespace="zorg-core")
    check("only the repository's namespace counts; an id may hold dots", set(fm_["blocks"]) == {"scope", "growth.pricing-rules", "teams", "map"}
          and "Not ours" not in json.dumps(fm_), fm_["blocks"].keys())
    check("the version is the most common one on the blocks", fm_["version"] == "0.4", fm_["version"])
    tie = blocks_of(region("zorg-core", "a", "0.2", "A"), region("zorg-core", "b", "0.3", "B"))
    check("a tie goes to the first one met", folder_with(tie, namespace="zorg-core")["version"] == "0.2", folder_with(tie, namespace="zorg-core"))
    nov = "<!-- zorg-core:begin id=a -->\nA\n<!-- zorg-core:end id=a -->\n"
    fnv = folder_with(nov, namespace="zorg-core")
    check("a block with no version still counts; with no version on any, version is None",
          set(fnv["blocks"]) == {"a"} and fnv["version"] is None, fnv)
    check("namespace defaults to the id: another namespace finds nothing", folder_with(mixed)["blocks"] == {}
          and folder_with(mixed)["source"] == "folder" and folder_with(mixed)["error"] is None, folder_with(mixed))
    dup = blocks_of(region("zorg-core", "a", "0.1", "first"), region("zorg-core", "a", "0.2", "second"))
    check("an id met twice keeps the first", "first" in folder_with(dup, namespace="zorg-core")["blocks"]["a"], "")
    broken = "<!-- zorg-core:begin id=a v=1 -->\nno end\n\n" + region("zorg-core", "b", "1", "B") + "\n"
    check("a region that is never closed is no block", set(folder_with(broken, namespace="zorg-core")["blocks"]) == {"b"},
          folder_with(broken, namespace="zorg-core")["blocks"])
    crlf = mixed.replace("\n", "\r\n")
    check("line endings: CRLF gives the same blocks as LF", folder_with(crlf, namespace="zorg-core")["blocks"] == fm_["blocks"], "")
    check("an empty blocks file is a source with no blocks, not an error", folder_with("", namespace="zorg-core")["blocks"] == {}
          and folder_with("", namespace="zorg-core")["error"] is None and folder_with("", namespace="zorg-core")["source"] == "folder", "")
    bad = os.path.join(d, "CaseBin")
    os.makedirs(os.path.join(bad, "Core"))
    open(os.path.join(bad, "Core", "blocks.md"), "wb").write(b"\xff\xfe\x00bad")
    fbin = cr.fetch(repo_of({"id": "zorg-bin", "kind": "folder", "paths": [bad], "blocks_file": "Core/blocks.md"}))
    check("a blocks file that is not UTF-8 text → error, not a crash", fbin["source"] is None and fbin["error"], fbin)
    check("a blocks file that is not there → error naming the file", cr.fetch(core_repo(blocks_file="Core/none.md"))["source"] is None
          and "none.md" in cr.fetch(core_repo(blocks_file="Core/none.md"))["error"], cr.fetch(core_repo(blocks_file="Core/none.md")))
    check("a blocks_file that leaves the core folder → refused", cr.fetch(core_repo(blocks_file="../ZorgGrowthCore/Growth/_System/context-blocks.md"))["source"] is None
          and "outside" in cr.fetch(core_repo(blocks_file="../ZorgGrowthCore/Growth/_System/context-blocks.md"))["error"],
          cr.fetch(core_repo(blocks_file="../ZorgGrowthCore/Growth/_System/context-blocks.md")))
    check("…an absolute one too", "outside" in (cr.fetch(core_repo(blocks_file=os.path.join(growth, GROWTH_FILE)))["error"] or ""), "")
    check("a registration with no core folder, no endpoint → error that says what is missing",
          cr.fetch(repo_of({"id": "zorg-void", "kind": "mcp"}))["source"] is None
          and "folder" in cr.fetch(repo_of({"id": "zorg-void", "kind": "mcp"}))["error"], cr.fetch(repo_of({"id": "zorg-void", "kind": "mcp"})))
    check("a core folder that is not there → error", cr.fetch(core_repo(paths=[os.path.join(d, "gone")], core_root=""))["source"] is None
          and "folder" in cr.fetch(core_repo(paths=[os.path.join(d, "gone")], core_root=""))["error"], "")

    # --- through the registrations on disk, as the commands read them
    ctx_text = read(REPOS_FIX, "context.md").replace("{{VAULT}}", os.path.join(d, "vault"))
    provdir = os.path.join(home, ".grow-pm", "providers")
    os.makedirs(provdir)
    with FakeMcp(tree={GROWTH_PATH: GROWTH_TEXT}) as fake:
        open(os.path.join(provdir, "zorg-core.yaml"), "w", encoding="utf-8").write(
            "schema: provider-registration/1\nid: zorg-core\nkind: bundle\nauthority: org\npaths:\n  - %s\nteam: team-alpha\nrole: pm\njira_write: own\n" % core)
        open(os.path.join(provdir, "zorg-growth.yaml"), "w", encoding="utf-8").write(
            "schema: provider-registration/2\nid: zorg-growth\nkind: mcp\nauthority: team\nendpoint:\n  url: %s\n  root: \"ZorgGrowth/\"\n"
            "blocks_file: %s\nblocks_source: mcp\nteam: team-alpha\n" % (fake.url, GROWTH_FILE))
        loaded = {r["id"]: r for r in cr.load_repos(ctx_text, home)}
        before_home = tree_state(home)
        fcore, fgrowth = cr.fetch(loaded["zorg-core"]), cr.fetch(loaded["zorg-growth"])
        check("…and the home is untouched by the fetch", tree_state(home) == before_home, "")
        check("registrations read from disk fetch as they should", fcore["source"] == "folder" and fgrowth["source"] == "mcp"
              and set(fcore["blocks"]) == {"scope", "product", "teams"} and set(fgrowth["blocks"]) == {"growth-metrics", "team"}, (fcore, fgrowth))

        # the fixture context holds, as the user's side, the very regions the two repositories offer
        def regions_in(text, ns):
            return {m.group(1): m.group(0) for m in re.finditer(
                r"<!-- %s:begin id=([A-Za-z0-9_.-]+)[^>]*-->.*?<!-- %s:end id=\1 -->" % (ns, ns), text, re.S)}

        mine_core, mine_growth = regions_in(ctx_text, "zorg-core"), regions_in(ctx_text, "zorg-growth")
        check("the fixture context has zorg-core's scope, teams and team, and zorg-growth's growth-metrics and team",
              set(mine_core) == {"scope", "teams", "team"} and set(mine_growth) == {"growth-metrics", "team"}, (list(mine_core), list(mine_growth)))
        check("…each equal to what the repository offers (the baseline of the later tasks)",
              all(mine_core[k] == (fcore["blocks"].get(k) or fcore["team"]) for k in mine_core)
              and all(mine_growth[k] == fgrowth["blocks"][k] for k in mine_growth),
              [k for k in mine_core if mine_core[k] != (fcore["blocks"].get(k) or fcore["team"])])
        check("…in the records the protocol puts them in (custom, team, product, team)",
              "## Zorg Core Notes" in ctx_text and ctx_text.index("## Zorg Core Notes") < ctx_text.index("zorg-core:begin id=scope")
              and ctx_text.index("### Team: Alpha (A)") < ctx_text.index("zorg-core:begin id=team") < ctx_text.index("zorg-growth:begin id=team"), "")

    # --- nothing was written anywhere
    check("fetch writes nothing: the cores are as they were", tree_state(core, growth) == before_cores,
          [k for k, v in tree_state(core, growth).items() if before_cores.get(k) != v])
    check("…and the home holds only the registrations the test put there",
          sorted(os.listdir(os.path.join(home, ".grow-pm"))) == ["providers"]
          and sorted(os.listdir(provdir)) == ["zorg-core.yaml", "zorg-growth.yaml"], os.listdir(os.path.join(home, ".grow-pm")))

print("RESULT:", "GREEN ✅" if not fails else "RED ❌", "(%d failed)" % fails)
sys.exit(1 if fails else 0)
