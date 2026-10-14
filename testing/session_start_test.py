#!/usr/bin/env python3
"""TC-hook-350-role — the SessionStart digest prints the role layer line.

Builds three variants of local-context.example.md in a temp dir (enum role,
legacy free-text role, no role) and asserts the digest line
`user.role: <enum | legacy | absent> | level_home: <Lx | derived at Step 0i>`.
The free-text label must never reach the digest. Stdlib only; run from the repo root.
"""
import datetime, importlib.util, os, re, sys, tempfile

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
    uni = os.path.join(d, "Ядро спільне")
    open(envf, "w").close()
    ss.export_env("/tmp/ctx.md", [uni])
    import subprocess
    got = subprocess.run(["bash", "-c", '. "$1"; printf %s "$GROW_PM_PROVIDER_PATHS"', "x", envf], capture_output=True, text=True).stdout
    check("env export keeps non-ASCII paths readable by bash", got == uni, got)
    del os.environ["CLAUDE_ENV_FILE"]

# --- v3.10.1: short meta columns, an index path that needs URI escapes, placeholder steps, unreadable registration
import sqlite3
def brain(dirpath, cols=("key", "value")):
    os.makedirs(dirpath, exist_ok=True)
    p = os.path.join(dirpath, "brain.sqlite")
    con = sqlite3.connect(p)
    con.execute("CREATE TABLE meta(%s TEXT PRIMARY KEY, %s TEXT)" % cols)
    con.execute("INSERT INTO meta VALUES ('last_index', '2026-10-01T08:00:00')")
    con.commit(); con.close()
    return p

def with_index(p):
    b = "### Vault Search MCP\n- zorg-brain: scope = own vault (Notes/), tools = vault_* + brain_*, index = %s\n" % p
    return example.replace("## People (Optional)", b + "\n## People (Optional)", 1)

with tempfile.TemporaryDirectory() as d:
    out = run(with_index(brain(os.path.join(d, "kv"), cols=("k", "v"))))
    check("index date read from a meta table with k/v columns", "zorg-brain (live, local, index 2026-10-01" in out, out)
    out = run(with_index(brain(os.path.join(d, "odd ?dir %41"))))
    check("index path with ? and % still read", "zorg-brain (live, local, index 2026-10-01" in out, out)

t5 = re.sub(r"^- \*\*Deferred steps:\*\*\n(?:  - .+\n)+", "- **Deferred steps:** _none_\n", example, count=1, flags=re.M)
out = run(t5)
check("a _none_ placeholder is not a deferred step", "- **Deferred steps:** _none_" in t5 and "deferred onboarding steps" not in out, out)

with tempfile.TemporaryDirectory() as d:
    regdir = os.path.join(d, "Notes", "_System", "providers"); os.makedirs(regdir)
    open(os.path.join(regdir, "broken.yaml"), "w").write("schema: provider-registration/1\nid: broken\npaths: [one, two]\n")
    t6 = re.sub(r"## Obsidian Vaults \(Optional\).*?(?=\n---\n)", table.replace("/tmp/zorg-vault", d), example, count=1, flags=re.S)
    out = run(t6)
    check("an unreadable registration is named in the digest", "broken.yaml" in out and "line 3" in out, out)

# --- v3.11.0: the context store line (read-only)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import ctx_ops as co  # noqa: E402

with tempfile.TemporaryDirectory() as d:
    home, vault = os.path.join(d, "home"), os.path.join(d, "vault")
    os.makedirs(os.path.join(home, ".grow-pm")); os.makedirs(os.path.join(vault, "Notes", "_System"))
    text = open(os.path.join(ROOT, "testing", "fixtures", "ctx", "typical.md"), encoding="utf-8").read().replace("{{VAULT}}", vault)
    ctxp = os.path.join(home, ".grow-pm", "local-context.md")
    mirror = os.path.join(vault, "Notes", "_System", "local-context.md")
    for p in (ctxp, mirror):
        open(p, "w", encoding="utf-8").write(text)
    out = ss.digest(ctxp, ss.parse(ctxp, extra_dirs=[]), [], "test")
    check("no context line without a store", "context:" not in out, out)
    copies = co.copies_for(ctxp, text, home=home)
    co.migrate(ctxp, co.store_root_for(text, home=home), copies, home, apply=True, now="2026-10-20T10:00:00+03:00")
    out = ss.digest(ctxp, ss.parse(ctxp, extra_dirs=[]), [], "test")
    check("context line with a store", "  context: records 14 · card " in out and " lines · in sync" in out, out)
    open(ctxp, "w", encoding="utf-8").write(text.replace("- **Cadence:** daily", "- **Cadence:** weekly"))
    out = ss.digest(ctxp, ss.parse(ctxp, extra_dirs=[]), [], "test")
    check("one direct edit waits to be imported", " · 1 edit to import" in out, out)

# --- v3.12.0: stale count, the ctx read hint, an unavailable store
OLD_HINT = ("still parse the file for 0c–0j (product selection, required fields, vault level, role, judgment "
            "contract). Env GROW_PM_CONTEXT_PATH is set for Bash.")
out = run(example)
check("v3.11 hint without a store", OLD_HINT in out and "read --skill" not in out, out[-300:])

with tempfile.TemporaryDirectory() as d:
    home, vault = os.path.join(d, "home"), os.path.join(d, "vault")
    os.makedirs(os.path.join(home, ".grow-pm")); os.makedirs(os.path.join(vault, "Notes", "_System"))
    text = open(os.path.join(ROOT, "testing", "fixtures", "ctx", "typical.md"), encoding="utf-8").read().replace("{{VAULT}}", vault)
    ctxp = os.path.join(home, ".grow-pm", "local-context.md")
    for p in (ctxp, os.path.join(vault, "Notes", "_System", "local-context.md")):
        open(p, "w", encoding="utf-8").write(text)
    root = co.store_root_for(text, home=home)
    co.migrate(ctxp, root, co.copies_for(ctxp, text, home=home), home, apply=True, now="2026-10-20T10:00:00+03:00")
    import ctx_store as cs  # noqa: E402
    st = cs.Store(root); state = st.state(); state["freshness_since"] = "2025-01-01"; st.save_state(state)
    out = ss.digest(ctxp, ss.parse(ctxp, extra_dirs=[]), [], "test")
    line = next((l for l in out.splitlines() if "context:" in l), "")
    check("stale count in the context line", " stale" in line and "records 14" in line, line)
    check("ctx read hint with a store", 'ctx.py" read --skill <your name> --product' in out and OLD_HINT not in out
          and "instead of reading local-context.md" in out and "exits 3" in out, out[-400:])
    os.rename(vault, vault + "-away")
    out = ss.digest(ctxp, ss.parse(ctxp, extra_dirs=[]), [], "test")
    check("unavailable store line", "context: store at %s unavailable — vault not mounted?" % root in out
          and "records" not in next((l for l in out.splitlines() if "context:" in l), ""), out[-400:])

# --- v3.12.1: custom records nobody reads
with tempfile.TemporaryDirectory() as d:
    home, vault = os.path.join(d, "home"), os.path.join(d, "vault")
    os.makedirs(os.path.join(home, ".grow-pm")); os.makedirs(os.path.join(vault, "Notes", "_System"))
    text = open(os.path.join(ROOT, "testing", "fixtures", "ctx", "typical.md"), encoding="utf-8").read().replace("{{VAULT}}", vault)
    text = text.rstrip("\n") + "\n\n## Zorg Partner Rules\n\n- Always say Zorg Partner.\n"
    ctxp = os.path.join(home, ".grow-pm", "local-context.md")
    for p in (ctxp, os.path.join(vault, "Notes", "_System", "local-context.md")):
        open(p, "w", encoding="utf-8").write(text)
    root = co.store_root_for(text, home=home)
    co.migrate(ctxp, root, co.copies_for(ctxp, text, home=home), home, apply=True, now="2026-10-20T10:00:00+03:00")
    out = ss.digest(ctxp, ss.parse(ctxp, extra_dirs=[]), [], "test")
    line = next((l for l in out.splitlines() if "context:" in l), "")
    check("digest counts unassigned custom", "· 1 custom unassigned" in line, line)
    import ctx_store as cs  # noqa: E402
    st = cs.Store(root)
    rec = next(r for r in st.load() if r["type"] == "custom")
    st.write(dict(rec, read_by="all"))
    out = ss.digest(ctxp, ss.parse(ctxp, extra_dirs=[]), [], "test")
    line_after_assign = next((l for l in out.splitlines() if "context:" in l), "")
    check("no unassigned → no tail", "custom unassigned" not in line_after_assign and "records" in line_after_assign, line_after_assign)

# --- v3.13.0: the providers line takes the day of the last check from the store when it is newer than synced_at
import ctx_blocks as cb  # noqa: E402

TODAY = datetime.date.today()
REG = ("schema: provider-registration/1\nid: zorg-core\nkind: bundle\nmode: snapshot\naccess: vpn\npaths:\n  - %s\n"
       "synced_at: %s\nstale_after_days: 30\nstatus: active\n")


def with_checked(d, synced, checked, migrate=True):
    """A migrated store, zorg-core registered with `synced_at`, and (when `checked`) a block state saying it was checked then."""
    home, vault = os.path.join(d, "home"), os.path.join(d, "vault")
    os.makedirs(os.path.join(home, ".grow-pm")); os.makedirs(os.path.join(vault, "Notes", "_System", "providers"))
    text = open(os.path.join(ROOT, "testing", "fixtures", "ctx", "typical.md"), encoding="utf-8").read().replace("{{VAULT}}", vault)
    ctxp = os.path.join(home, ".grow-pm", "local-context.md")
    for p in (ctxp, os.path.join(vault, "Notes", "_System", "local-context.md")):
        open(p, "w", encoding="utf-8").write(text)
    open(os.path.join(vault, "Notes", "_System", "providers", "zorg-core.yaml"), "w").write(REG % (os.path.join(d, "ZorgCore"), synced))
    root = co.store_root_for(text, home=home)
    if migrate:
        co.migrate(ctxp, root, co.copies_for(ctxp, text, home=home), home, apply=True, now="2026-10-20T10:00:00+03:00")
    if checked:
        import ctx_store as cs  # noqa: E402
        with cs.guard_roots([home, vault]):
            cb.save_state(cs.Store(root), "zorg-core", {"checked": checked + "T10:00:00+03:00", "source": "folder", "version": "0.4", "blocks": {}})
    return ctxp


def providers_line(ctxp):
    out = ss.digest(ctxp, ss.parse(ctxp, extra_dirs=[]), [], "test")
    return next((l.strip() for l in out.splitlines() if l.strip().startswith("providers:")), "")


with tempfile.TemporaryDirectory() as d:
    line = providers_line(with_checked(d, "2026-01-01", TODAY.isoformat()))
    check("digest uses last_checked", "zorg-core (snapshot, vpn, synced %s)" % TODAY.isoformat() in line and "stale" not in line, line)

with tempfile.TemporaryDirectory() as d:
    old = (TODAY - datetime.timedelta(days=40)).isoformat()
    line = providers_line(with_checked(d, (TODAY - datetime.timedelta(days=90)).isoformat(), old))
    check("…and stale is counted from it", "zorg-core (snapshot, vpn, synced %s, stale)" % old in line, line)

with tempfile.TemporaryDirectory() as d:
    line = providers_line(with_checked(d, TODAY.isoformat(), (TODAY - datetime.timedelta(days=5)).isoformat()))
    check("a check older than synced_at changes nothing", "zorg-core (snapshot, vpn, synced %s)" % TODAY.isoformat() in line, line)

with tempfile.TemporaryDirectory() as d:
    line = providers_line(with_checked(d, "2026-01-01", None))
    check("a store with no block state: synced_at as before", "zorg-core (snapshot, vpn, synced 2026-01-01, stale)" in line, line)

with tempfile.TemporaryDirectory() as d:
    line = providers_line(with_checked(d, "2026-01-01", None, migrate=False))
    check("no store at all: synced_at as before", "zorg-core (snapshot, vpn, synced 2026-01-01, stale)" in line, line)

with tempfile.TemporaryDirectory() as d:
    ctxp = with_checked(d, "2026-01-01", TODAY.isoformat())
    real_mod = sys.modules.get("ctx_blocks")
    sys.modules["ctx_blocks"] = None                      # the module that reads the checks cannot be imported
    try:
        out = ss.digest(ctxp, ss.parse(ctxp, extra_dirs=[]), [], "test")
    finally:
        sys.modules["ctx_blocks"] = real_mod
    line = next((l.strip() for l in out.splitlines() if l.strip().startswith("providers:")), "")
    check("an import that fails costs the days of the checks, not the context line",
          "  context: records 14 · card " in out and "zorg-core (snapshot, vpn, synced 2026-01-01, stale)" in line, out[-700:])

with tempfile.TemporaryDirectory() as d:
    ctxp = with_checked(d, "2026-01-01", TODAY.isoformat())
    import ctx_store as cs  # noqa: E402
    open(os.path.join(co.store_root_for(open(ctxp, encoding="utf-8").read(), home=os.path.join(d, "home")), ".state", "blocks", "zorg-core.json"), "w").write("{ not json")
    line = providers_line(ctxp)
    check("a block state that cannot be read: synced_at, no failure", "zorg-core (snapshot, vpn, synced 2026-01-01, stale)" in line, line)

# --- v3.13.0 final review: a block state that never arrives (iCloud) costs the days of the checks, never the context line
import time  # noqa: E402

with tempfile.TemporaryDirectory() as d:
    ctxp = with_checked(d, "2026-01-01", TODAY.isoformat())
    state = os.path.join(co.store_root_for(open(ctxp, encoding="utf-8").read(), home=os.path.join(d, "home")), ".state", "blocks", "zorg-core.json")
    os.remove(state)
    os.mkfifo(state)                                      # its read waits for a writer that never comes, like an evicted file
    t0 = time.time()
    out = ss.digest(ctxp, ss.parse(ctxp, extra_dirs=[]), [], "test")
    took = time.time() - t0
    try:                                                  # let the reader thread out of open()
        os.close(os.open(state, os.O_WRONLY | os.O_NONBLOCK))
    except OSError:
        pass
    line = next((l.strip() for l in out.splitlines() if l.strip().startswith("providers:")), "")
    check("a block state that never arrives: the context line is still there, the providers line falls back to synced_at",
          "  context: records 14 · card " in out and "zorg-core (snapshot, vpn, synced 2026-01-01, stale)" in line, out[-700:])
    check("…and the digest stays within its budget (2 s for the store, half a second more for the days)", took < 4, took)

with tempfile.TemporaryDirectory() as d:                  # the days still come when they are quick
    ctxp = with_checked(d, "2026-01-01", TODAY.isoformat())
    s = ss._store_summary(ctxp)
    check("the summary carries the days of the checks as before", s and s.get("checked", {}).get("zorg-core", "").startswith(TODAY.isoformat())
          and s["records"] == 14, s)

print("RESULT:", "GREEN ✅" if not fails else "RED ❌")
sys.exit(1 if fails else 0)
