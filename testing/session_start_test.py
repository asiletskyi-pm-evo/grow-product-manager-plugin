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

# --- v3.13.1: a cold start (a store slow to read) keeps the context line from the summary saved last time
import json  # noqa: E402

CACHED_LINE = r"^  context: records 14 · card \d+ lines · .* · cached \d{4}-\d{2}-\d{2} \d{2}:\d{2}$"


def release(fifo):
    """Let every reader thread waiting on the FIFO out of open()."""
    for _ in range(3):
        try:
            os.close(os.open(fifo, os.O_WRONLY | os.O_NONBLOCK))
        except OSError:
            pass
        time.sleep(0.05)


with tempfile.TemporaryDirectory() as d:
    ctxp = with_checked(d, "2026-01-01", TODAY.isoformat())
    cache = co.summary_cache_path(ctxp)
    out1 = ss.digest(ctxp, ss.parse(ctxp, extra_dirs=[]), [], "test")          # warm: writes the cache
    check("a live summary in time writes the cache", os.path.isfile(cache) and "· cached" not in out1
          and "  context: records 14 · card " in out1, out1[-700:])
    saved = json.load(open(cache, encoding="utf-8")) if os.path.isfile(cache) else {}
    check("…with the days of the checks", (saved.get("facts", {}).get("checked") or {}).get("zorg-core", "").startswith(TODAY.isoformat()), saved)
    root = co.store_root_for(open(ctxp, encoding="utf-8").read(), home=os.path.join(d, "home"))
    rec = os.path.join(root, "records", sorted(os.listdir(os.path.join(root, "records")))[0])
    os.remove(rec)
    os.mkfifo(rec)                                        # its read waits for a writer that never comes, like an evicted file
    try:
        t0 = time.time(); out2 = ss.digest(ctxp, ss.parse(ctxp, extra_dirs=[]), [], "test"); took = time.time() - t0
        check("a cold store: the cached line, marked, and the ctx read instruction kept",
              re.search(CACHED_LINE, out2, re.M) and 'ctx.py" read --skill' in out2 and OLD_HINT not in out2 and took < 4, (took, out2[-700:]))
        line = next((l.strip() for l in out2.splitlines() if l.strip().startswith("providers:")), "")
        check("…the providers line takes the day of the last check from the cache", "zorg-core (snapshot, vpn, synced %s)" % TODAY.isoformat() in line, line)
        for name, bad in [("not JSON", "{not json"),
                          ("older than 7 days", json.dumps(dict(saved, at=(datetime.datetime.now().astimezone() - datetime.timedelta(days=8)).isoformat(timespec="seconds")))),
                          ("without a count", json.dumps(dict(saved, facts={k: v for k, v in saved.get("facts", {}).items() if k != "records"})))]:
            open(cache, "w", encoding="utf-8").write(bad)
            out = ss.digest(ctxp, ss.parse(ctxp, extra_dirs=[]), [], "test")
            check("…a cache %s and a cold store: no context line, the digest as without a store" % name,
                  "  context:" not in out and OLD_HINT in out and "FOUND at" in out, out[-500:])
        os.remove(cache)                                  # no cache, the FIFO stays
        out3 = ss.digest(ctxp, ss.parse(ctxp, extra_dirs=[]), [], "test")
        check("…no cache and a cold store: no context line, as before", "  context:" not in out3 and OLD_HINT in out3, out3[-500:])
        check("…and a cold store writes no cache", not os.path.exists(cache))
    finally:
        release(rec)

with tempfile.TemporaryDirectory() as d:                  # a summary that comes back None in time is not replaced by the cache
    ctxp = with_checked(d, "2026-01-01", None)
    ss.digest(ctxp, ss.parse(ctxp, extra_dirs=[]), [], "test")
    cache = co.summary_cache_path(ctxp)
    root = co.store_root_for(open(ctxp, encoding="utf-8").read(), home=os.path.join(d, "home"))
    os.chmod(os.path.join(root, "records"), 0o300)       # the records cannot be listed: the live summary fails at once
    try:
        out = ss.digest(ctxp, ss.parse(ctxp, extra_dirs=[]), [], "test")
    finally:
        os.chmod(os.path.join(root, "records"), 0o700)
    check("a live summary that fails in time: no context line, the cache is not used", os.path.isfile(cache)
          and "  context:" not in out and "cached" not in out, out[-500:])

import inspect  # noqa: E402

with tempfile.TemporaryDirectory() as d:                  # v3.13.1 final review: a warm start whose days miss keeps the saved days
    ctxp = with_checked(d, "2026-01-01", TODAY.isoformat())
    cache = co.summary_cache_path(ctxp)
    ss.digest(ctxp, ss.parse(ctxp, extra_dirs=[]), [], "test")                 # warm, with the days: they are saved
    first = json.load(open(cache, encoding="utf-8")) if os.path.isfile(cache) else {}
    state = os.path.join(co.store_root_for(open(ctxp, encoding="utf-8").read(), home=os.path.join(d, "home")), ".state", "blocks", "zorg-core.json")
    os.remove(state)
    os.mkfifo(state)                                      # the days do not arrive within their half second; the facts do
    try:
        s = ss._store_summary(ctxp)
    finally:
        release(state)
    second = json.load(open(cache, encoding="utf-8")) if os.path.isfile(cache) else {}
    check("a warm start whose days miss: the facts are live, and the days saved before stay in the cache",
          s and s["records"] == 14 and "cached_at" not in s and s["checked"] == {}
          and (first.get("facts") or {}).get("checked", {}).get("zorg-core", "").startswith(TODAY.isoformat())
          and (second.get("facts") or {}).get("checked") == first["facts"]["checked"], str((s, first.get("facts"), second.get("facts"))))
    check("the hook counts through the one budgeted helper of ctx_ops (2 s for the facts, half a second for the days)",
          "ctx_ops.summary_in_time(" in inspect.getsource(ss._store_summary) and "threading" not in inspect.getsource(ss._store_summary)
          and inspect.signature(ss._store_summary).parameters["budget_s"].default == 2.0
          and inspect.signature(ss._store_summary).parameters["dates_s"].default == 0.5, inspect.getsource(ss._store_summary)[-600:])
    rule = next((b for b in re.sub(r"\s+", " ", ss.__doc__).split(" - ") if ".ctx-summary.json" in b), "")
    check("the hook's design rule on writes names both: the summary beside the context and the CLAUDE_ENV_FILE append",
          "CLAUDE_ENV_FILE" in rule and "nothing else" not in rule, rule)

# --- v3.14.0 Task 7: the repos line — the result of the daily sync of every repository registered with `sync: daily`
import ctx_repos as crp  # noqa: E402
import ctx_store as cs  # noqa: E402


def res(outcome, **fields):
    """A sync_result as ctx_synced keeps it in the block state (every key of RESULT_KEYS)."""
    out = {"at": "2026-10-16T07:41:00+03:00", "outcome": outcome, "updated": 0, "added": 0, "removed": 0, "kept_yours": [],
           "took_rule": [], "awaiting": [], "held": [], "rejected": [], "reason": None, "report": None, "snapshot": None}
    out.update(fields)
    return out


def repos_world(d, repos):
    """A migrated store whose registrations are `repos`: [(id, the registration's sync line, its sync_result or None,
    the day of its last successful check or None)]; the registration of with_checked is replaced."""
    ctxp = with_checked(d, "2026-01-01", None)
    home, vault = os.path.join(d, "home"), os.path.join(d, "vault")
    prov = os.path.join(vault, "Notes", "_System", "providers")
    root = co.store_root_for(open(ctxp, encoding="utf-8").read(), home=home)
    os.remove(os.path.join(prov, "zorg-core.yaml"))
    with cs.guard_roots([home, vault]):
        for rid, sync_line, result, checked in repos:
            open(os.path.join(prov, rid + ".yaml"), "w").write(
                (REG % (os.path.join(d, "Core-" + rid), "2026-01-01")).replace("id: zorg-core", "id: " + rid) + sync_line)
            if result is not None or checked:
                state = {"checked": checked and checked + "T10:00:00+03:00", "source": "folder", "version": "0.4", "blocks": {}}
                if result is not None:
                    state.update(sync_attempt=result["at"], sync_result=result)
                cb.save_state(cs.Store(root), rid, state)
    return ctxp


def repos_of(ctxp):
    """The repos line of the digest, or None; and the whole digest."""
    out = ss.digest(ctxp, ss.parse(ctxp, extra_dirs=[]), [], "test")
    return next((l for l in out.splitlines() if l.startswith("  repos:")), None), out


def one(result, checked="2026-10-16", sync_line="sync: daily\n"):
    """The repos line of one repository, zorg-core, with `result`."""
    with tempfile.TemporaryDirectory() as d:
        return repos_of(repos_world(d, [("zorg-core", sync_line, result, checked)]))[0]


REPORT = "_System/context/sync/2026-10-16.md"
check("changed: synced, updated, conflicts kept yours, the report",
      one(res("changed", updated=2, kept_yours=["scope"], report=REPORT))
      == "  repos: zorg-core · synced 2026-10-16 · 2 updated · 1 conflict kept yours · report " + REPORT)
check("…the blocks added and removed are updated too (the sentence of the skill counts them so)",
      one(res("changed", updated=1, added=1, removed=1, report=REPORT)) == "  repos: zorg-core · synced 2026-10-16 · 3 updated · report " + REPORT)
check("…a part with a zero is left out: no conflicts, no report", one(res("changed", updated=1)) == "  repos: zorg-core · synced 2026-10-16 · 1 updated")
check("…only conflicts kept yours", one(res("changed", kept_yours=["a", "b"], report=REPORT))
      == "  repos: zorg-core · synced 2026-10-16 · 2 conflicts kept yours · report " + REPORT)
check("the day is the pass's, whatever the day of the last check", one(res("changed", at="2026-10-15T23:59:00+03:00", updated=1), checked="2026-10-16")
      == "  repos: zorg-core · synced 2026-10-15 · 1 updated")
check("no changes", one(res("no-changes")) == "  repos: zorg-core · synced 2026-10-16 · no changes")
check("…a new block waiting for a decision (and where the report is)", one(res("no-changes", awaiting=["scope", "teams"], report=REPORT))
      == "  repos: zorg-core · synced 2026-10-16 · no changes · report " + REPORT + " · 2 block(s) awaits a decision")
check("…and after a change", one(res("changed", updated=1, awaiting=["scope"]))
      == "  repos: zorg-core · synced 2026-10-16 · 1 updated · 1 block(s) awaits a decision")
check("held removals", one(res("held", held=["a", "b", "c"], reason="the core removed 3 blocks you hold"))
      == "  repos: zorg-core · ⚠ 3 removals held — ctx provider plan zorg-core")
check("…and a block waiting", one(res("held", held=["a", "b"], awaiting=["x"])) == "  repos: zorg-core · ⚠ 2 removals held — ctx provider plan zorg-core · 1 block(s) awaits a decision")
check("unreachable: since the last successful check (not the failed attempt)", one(res("unreachable", reason="no answer"), checked="2026-10-14")
      == "  repos: zorg-core · unreachable since 2026-10-14 (VPN?)")
check("…never checked: no day to name", one(res("unreachable"), checked=None) == "  repos: zorg-core · unreachable (VPN?)")
check("timeout: the attempt's day", one(res("timeout", at="2026-10-16T07:41:00+03:00"), checked="2026-10-14") == "  repos: zorg-core · sync timed out 2026-10-16")
check("broken: the reason, clipped to 80", one(res("broken", reason="x" * 200)) == "  repos: zorg-core · ⚠ source broken — " + "x" * 79 + "…")
check("…a short reason as it is", one(res("broken", reason="the blocks file is empty")) == "  repos: zorg-core · ⚠ source broken — the blocks file is empty")
check("import-conflict", one(res("import-conflict", reason="the edits waiting to be imported need a decision (scope) — `ctx sync` first"))
      == "  repos: zorg-core · ⚠ edits to import first — ctx sync")
check("error: the reason, clipped to 80", one(res("error", reason="store: record scope is not downloaded " + "y" * 100))
      == "  repos: zorg-core · ⚠ sync error — " + ("store: record scope is not downloaded " + "y" * 100)[:79] + "…")
hostile = one(res("error", reason="bad\n\x1b[31mred\r\n‮evil " + "z" * 300))
check("…a reason is one line without control characters or bidi overrides", hostile and "\n" not in hostile and "\x1b" not in hostile
      and "‮" not in hostile and len(hostile) < 140, repr(hostile))
check("an outcome the digest does not know (a newer plugin wrote it) gives no line", one(res("from-the-future")) is None)

for line_ in ("", "sync: off\n", "sync: weekly\n", "sync: yes\n", "sync: true\n", "sync:\n"):
    check("a registration with %r (not daily) gets no part, whatever its old result says" % (line_.strip() or "no key"),
          one(res("changed", updated=2, report=REPORT), sync_line=line_) is None)
for line_ in ("sync: Daily\n", "sync: DAILY\n", "sync: ' daily '\n"):
    check("…%r is daily, as ctx_repos.normalise reads it" % line_.strip(), one(res("no-changes"), sync_line=line_) is not None)
for value in ("daily", "Daily", " DAILY ", "off", "weekly", "", "daily\n", True, 1, None, ["daily"], {"daily": 1}):
    check("the hook's reading of `sync: %r` is ctx_repos.normalise's" % (value,),
          ss._sync_daily(value) == (crp.normalise({"id": "zorg-core", "sync": value})["sync"] == crp.SYNC_DAILY))

with tempfile.TemporaryDirectory() as d:
    ctxp = repos_world(d, [("zorg-core", "sync: daily\n", res("changed", updated=2, report=REPORT), "2026-10-16"),
                           ("zorg-growth", "sync: daily\n", res("unreachable"), "2026-10-14"),
                           ("zorg-idle", "sync: daily\n", None, "2026-10-14"),                  # daily, never synced: no part
                           ("zorg-off", "", res("changed", updated=9), "2026-10-16")])         # switched off: its old result is not shown
    line, out = repos_of(ctxp)
    check("several repositories: one line, joined by '; ', registration order; one without a result or without sync: daily is left out",
          line == "  repos: zorg-core · synced 2026-10-16 · 2 updated · report " + REPORT + "; zorg-growth · unreachable since 2026-10-14 (VPN?)", line)
    check("…the line sits after the context line and before Skills", [l.split(":")[0].strip() for l in out.splitlines()
          if l.startswith(("  context:", "  repos:", "Skills:"))] == ["context", "repos", "Skills"], out[-900:])

with tempfile.TemporaryDirectory() as d:
    four = [("zorg-%s" % n, "sync: daily\n", res("no-changes"), "2026-10-16") for n in ("a", "b", "c", "d")]
    ctxp = repos_world(d, four[:3])
    check("three repositories are all named, no '+'", repos_of(ctxp)[0] == "  repos: " + "; ".join(
        "zorg-%s · synced 2026-10-16 · no changes" % n for n in "abc"), repos_of(ctxp)[0])
with tempfile.TemporaryDirectory() as d:
    ctxp = repos_world(d, four)
    check("a fourth: three are named, the rest is '+1'", repos_of(ctxp)[0] == "  repos: " + "; ".join(
        ["zorg-%s · synced 2026-10-16 · no changes" % n for n in "abc"] + ["+1"]), repos_of(ctxp)[0])

with tempfile.TemporaryDirectory() as d:
    ctxp = repos_world(d, [("zorg-core", "sync: daily\n", res("no-changes"), "2026-10-16")])
    open(os.path.join(co.store_root_for(open(ctxp, encoding="utf-8").read(), home=os.path.join(d, "home")), ".state", "blocks", "zorg-core.json"), "w").write("{ not json")
    check("a block state that cannot be read: no repos line, no failure", repos_of(ctxp)[0] is None and "  context: records 14" in repos_of(ctxp)[1])

with tempfile.TemporaryDirectory() as d:
    ctxp = repos_world(d, [("zorg-core", "sync: daily\n", res("changed", updated="two", kept_yours="scope", awaiting=7, held=None, report=["x"]), "2026-10-16"),
                           ("zorg-growth", "sync: daily\n", res("no-changes", at=None), "2026-10-16"),
                           ("zorg-ops", "sync: daily\n", res("held", held="a"), None)])
    line, out = repos_of(ctxp)
    check("results with values of the wrong kind never fail the digest", "FOUND at" in out and "  context: records 14" in out and line and "\n" not in line, (line, out[-500:]))

with tempfile.TemporaryDirectory() as d:                  # no store, a registration with sync: daily: nothing to read
    ctxp = with_checked(d, "2026-01-01", None, migrate=False)
    check("no store, no repos line", repos_of(ctxp)[0] is None)

with tempfile.TemporaryDirectory() as d:                  # the Skills line: the sync first
    ctxp = repos_world(d, [("zorg-core", "sync: daily\n", res("no-changes"), "2026-10-16")])
    line, out = repos_of(ctxp)
    skills = next((l for l in out.splitlines() if l.startswith("Skills:")), "")
    SYNC_FIRST = ('Skills: run python3 "<plugin root>/scripts/ctx.py" provider sync --if-due (repeat any line it prints that starts '
                  '«Ядро оновило» at the end of your answer), then take this path for Step 0a of references/local-context-protocol.md')
    check("the Skills line (a store exists) starts with the sync, then the v3.13.1 text as it was", skills.startswith(SYNC_FIRST)
          and 'run python3 "<plugin root>/scripts/ctx.py" read --skill <your name> --product' in skills
          and "exits 3" in skills and skills.endswith("Env GROW_PM_CONTEXT_PATH is set for Bash."), skills)
    check("…once", skills.count("provider sync --if-due") == 1)
out_no_store = run(example)
check("…no store: the Skills line as in v3.13.1, no sync", "provider sync" not in out_no_store and OLD_HINT in out_no_store, out_no_store[-400:])

with tempfile.TemporaryDirectory() as d:                  # the same line from the cache on a cold start
    ctxp = repos_world(d, [("zorg-core", "sync: daily\n", res("changed", updated=2, report=REPORT), "2026-10-16"),
                           ("zorg-growth", "sync: daily\n", res("unreachable"), "2026-10-14")])
    cache = co.summary_cache_path(ctxp)
    warm, out1 = repos_of(ctxp)
    saved = json.load(open(cache, encoding="utf-8")) if os.path.isfile(cache) else {}
    check("a warm start saves the results of the sync in the cache", sorted((saved.get("facts") or {}).get("sync") or {}) == ["zorg-core", "zorg-growth"]
          and "· cached" not in out1, (saved.get("facts") or {}).get("sync"))
    root = co.store_root_for(open(ctxp, encoding="utf-8").read(), home=os.path.join(d, "home"))
    rec = os.path.join(root, "records", sorted(os.listdir(os.path.join(root, "records")))[0])
    os.remove(rec)
    os.mkfifo(rec)                                        # its read waits for a writer that never comes, like an evicted file
    try:
        cold, out2 = repos_of(ctxp)
        check("a cold store: the cached digest has the same repos line", re.search(CACHED_LINE, out2, re.M) and cold == warm and warm, (warm, cold))
        old = json.loads(json.dumps(saved))
        old["facts"].pop("sync", None)                    # a cache saved by v3.13.1
        open(cache, "w", encoding="utf-8").write(json.dumps(old))
        cold_old, out3 = repos_of(ctxp)
        check("…a cache of v3.13.1 (no sync): the context line stays, no repos line", re.search(CACHED_LINE, out3, re.M) and cold_old is None, out3[-500:])
    finally:
        release(rec)

with tempfile.TemporaryDirectory() as d:                  # a state that never arrives costs the days and the results, never the context line
    ctxp = repos_world(d, [("zorg-core", "sync: daily\n", res("no-changes"), "2026-10-16")])
    state = os.path.join(co.store_root_for(open(ctxp, encoding="utf-8").read(), home=os.path.join(d, "home")), ".state", "blocks", "zorg-core.json")
    os.remove(state)
    os.mkfifo(state)
    t0 = time.time()
    try:
        line, out = repos_of(ctxp)
    finally:
        release(state)
    took = time.time() - t0
    check("a block state that never arrives: no repos line, the context line is there, within the budget",
          line is None and "  context: records 14 · card " in out and took < 4, (line, took))

# a context outside .grow-pm (a connected folder): the digest works as before and writes nothing beside it
with tempfile.TemporaryDirectory() as d:
    ctxp = with_checked(d, "2026-01-01", None)
    moved = os.path.join(d, "mnt", "zorg", "local-context.md")
    os.makedirs(os.path.dirname(moved))
    os.rename(ctxp, moved)
    out = ss.digest(moved, ss.parse(moved, extra_dirs=[]), [], "test")
    check("a context outside .grow-pm: nothing written beside it", os.listdir(os.path.dirname(moved)) == ["local-context.md"]
          and "FOUND at" in out, (os.listdir(os.path.dirname(moved)), out[-400:]))

print("RESULT:", "GREEN ✅" if not fails else "RED ❌")
sys.exit(1 if fails else 0)
