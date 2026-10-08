#!/usr/bin/env python3
"""TC-hook-350-role — the SessionStart digest prints the role layer line.

Builds three variants of local-context.example.md in a temp dir (enum role,
legacy free-text role, no role) and asserts the digest line
`user.role: <enum | legacy | absent> | level_home: <Lx | derived at Step 0i>`.
The free-text label must never reach the digest. Stdlib only; run from the repo root.
"""
import importlib.util, os, re, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("session_start", os.path.join(ROOT, "scripts", "session_start.py"))
ss = importlib.util.module_from_spec(spec); spec.loader.exec_module(ss)
example = open(os.path.join(ROOT, "local-context.example.md"), encoding="utf-8").read()

def variant(role_line, level_line):
    t = re.sub(r"^- \*\*Role:\*\*.*$", role_line, example, count=1, flags=re.M)
    return re.sub(r"^- \*\*Level home:\*\*.*$\n?", level_line, t, count=1, flags=re.M)

cases = [
    ("enum role", variant("- **Role:** head_of_product", "- **Level home:** L3\n"), "user.role: head_of_product | level_home: L3"),
    ("enum role + trailing comment", variant("- **Role:** cpo <!-- set by Step 4a -->", "- **Level home:** L4\n"), "user.role: cpo | level_home: L4"),
    ("legacy free text", variant("- **Role:** Senior PM, Area 1", ""), "user.role: legacy | level_home: derived at Step 0i"),
    ("no role", variant("", ""), "user.role: absent | level_home: derived at Step 0i"),
]
fails = 0
for name, text, expected in cases:
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(text); path = f.name
    out = ss.digest(path, ss.parse(path, extra_dirs=[]), [], "test")
    os.unlink(path)
    ok = expected in out and "Area 1" not in out
    fails += not ok
    print(("✅" if ok else "❌"), name, "->", next((l.strip() for l in out.splitlines() if "user.role" in l), "(no role line)"))

# --- v3.10.0: managed regions, vault table, providers, bundle, env export (TC-hook-3100-*)
def run(text, extra_dirs=()):
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(text); path = f.name
    try:
        return ss.digest(path, ss.parse(path, extra_dirs=list(extra_dirs)), [], "test")
    finally:
        os.unlink(path)

def check(name, cond, detail=""):
    global fails
    fails += not cond
    print(("✅" if cond else "❌"), name, ("" if cond else "-> " + detail))

ORG = "## Organization: Your Company Name"
region = ("<!-- zorg-core:begin id=team v=0.4 -->\n### Product: Zorg App\n### Team: Zorg Team (ZT)\n"
          "<!-- zorg-core:end id=team -->\n")
t1 = example.replace(ORG, ORG + "\n" + region, 1) + "\n## Landscape\n### Product: Your Product Name\n- category: Shopping\n"
out = run(t1)
check("no double count for any namespace", "products (2): Your Product Name; Second Product Name" in out
      and "teams: Product Team Name\n" in out + "\n" and "Zorg" not in out, out)

table = ("## Obsidian Vaults (Optional)\n\n| # | Vault Path | Folder Name | Products | Sync Mode | Last Artifact |\n"
         "|---|---|---|---|---|---|\n| 1 | /tmp/zorg-vault | Notes | all | auto | never |\n\n")
t2 = re.sub(r"## Obsidian Vaults \(Optional\).*?(?=\n---\n)", table, example, count=1, flags=re.S)
check("vault flag from table format", "vault: configured" in run(t2), run(t2))

bullets = ("\n### Vault Search MCP\n- zorg-brain: scope = own vault (Notes/, ZorgCore/), tools = vault_* + brain_*, "
           "index = ~/.zorg-brain/brain.sqlite\n- zorg-core: scope = shared core snapshot, mode = snapshot, VPN only, read-only\n")
t3 = example.replace("## People (Optional)", bullets.lstrip("\n") + "\n## People (Optional)", 1)
check("providers line from vault search mcp", "providers: zorg-brain (live, local), zorg-core (snapshot, vpn)" in run(t3), run(t3))
check("providers none", "providers: none declared" in run(example), run(example))

with tempfile.TemporaryDirectory() as d:
    core = os.path.join(d, "ZorgCore"); os.makedirs(os.path.join(core, "Core", "_System"))
    open(os.path.join(core, "Core", "_System", "bundle-manifest.md"), "w").write(
        '---\ntype: bundle-manifest\nteam: "team-alpha"\nrole_profile: pm\ncore_version: "0.2"\n---\n# Bundle\n')
    regdir = os.path.join(d, "Notes", "_System", "providers"); os.makedirs(regdir)
    open(os.path.join(regdir, "zorg-core.yaml"), "w").write(
        "schema: provider-registration/1\nid: zorg-core\nkind: bundle\nmode: snapshot\naccess: vpn\n"
        "paths:\n  - %s\nsynced_at: 2026-01-01\nstale_after_days: 30\nstatus: active\n" % core)
    t4 = re.sub(r"## Obsidian Vaults \(Optional\).*?(?=\n---\n)", table.replace("/tmp/zorg-vault", d), example, count=1, flags=re.S)
    out = run(t4)
    check("registration adds synced date and stale", "zorg-core (snapshot, vpn, synced 2026-01-01, stale)" in out, out)
    check("bundle line", "bundle: team=team-alpha role=pm core=0.2" in out, out)
    envf = os.path.join(d, "env.sh"); os.environ["CLAUDE_ENV_FILE"] = envf
    ss.export_env("/tmp/ctx.md", [core])
    got = open(envf).read()
    check("env export", "GROW_PM_CONTEXT_PATH" in got and "GROW_PM_PROVIDER_PATHS" in got and core in got, got)
    del os.environ["CLAUDE_ENV_FILE"]

print("RESULT:", "GREEN ✅" if not fails else "RED ❌")
sys.exit(1 if fails else 0)
