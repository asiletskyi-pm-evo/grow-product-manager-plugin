#!/usr/bin/env python3
"""TC-ctx-3110-cli — scripts/ctx.py, the context store's command line (since v3.11.0).

Every command end to end on a temp HOME (the fictional typical context) and a temp vault with
its mirror: the output contract (`CTX_RESULT {json}` last, `CTX_CONFLICT` before it), the exit
codes (0 ok, 2 conflict, 3 bad input / no store / unreadable, 4 refused) and the safety rules
(import before write, snapshot, lock, managed regions, the provider boundary).
Semantics: references/context-protocol.md. Stdlib only; run from the repo root.
"""
import json, os, shutil, stat, subprocess, sys, tempfile, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "testing"))
os.environ["NO_PROXY"] = "127.0.0.1,localhost"          # the fake MCP server is local; a proxy in the environment must not see it
os.environ["no_proxy"] = "127.0.0.1,localhost"
from mcp_fake import FakeMcp  # noqa: E402

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


class Env:
    def __init__(self, d, fixture="typical", fix=FIX):
        self.home = os.path.join(d, "home")
        self.vault = os.path.join(d, "vault")
        os.makedirs(os.path.join(self.home, ".grow-pm"))
        os.makedirs(os.path.join(self.vault, "Notes", "_System"))
        self.text = read(fix, fixture + ".md").replace("{{VAULT}}", self.vault)
        self.ctx = os.path.join(self.home, ".grow-pm", "local-context.md")
        self.mirror = os.path.join(self.vault, "Notes", "_System", "local-context.md")
        self.store = os.path.join(self.vault, "Notes", "_System", "context")
        open(self.ctx, "w", encoding="utf-8", newline="").write(self.text)
        if "{{VAULT}}" in read(fix, fixture + ".md"):
            open(self.mirror, "w", encoding="utf-8", newline="").write(self.text)
        else:
            self.store = os.path.join(self.home, ".grow-pm", "_System", "context")

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

    def edit(self, path, old, new):
        t = read(path)
        assert old in t, old
        open(path, "w", encoding="utf-8", newline="").write(t.replace(old, new, 1))

    def record(self, rid):
        return read(self.store, "records", rid + ".md")


contract_ok = True

def run_ok(env, *args):
    global contract_ok
    rc, out, res = env.run(*args)
    contract_ok = contract_ok and res is not None
    return rc, out, res


with tempfile.TemporaryDirectory() as d:
    e = Env(d)
    rc, out, res = run_ok(e, "status")
    check("status without store", rc == 3 and "no store" in out, (rc, out[-300:]))
    rc, out, res = run_ok(e, "sync")
    check("sync without a store is a no-op", rc == 0 and "nothing to sync" in out, (rc, out[-300:]))
    rc, out, res = run_ok(e, "migrate")
    check("migrate dry run", rc == 0 and "round trip: identical" in out and not os.path.exists(e.store), (rc, out[-400:]))
    rc, out, res = run_ok(e, "migrate", "--apply")
    check("migrate --apply creates the store", rc == 0 and os.path.isdir(os.path.join(e.store, "records"))
          and read(e.ctx) == e.text and read(e.mirror) == e.text, (rc, out[-300:]))
    rc, out, res = run_ok(e, "migrate", "--apply")
    check("a second migrate --apply exits 4", rc == 4, (rc, out[-300:]))
    rc, out, res = run_ok(e, "set", "product.zorg-app", "Jira Project Key", "NEW")
    jr = [json.loads(l) for l in open(os.path.join(e.store, ".state", "journal.jsonl"), encoding="utf-8")]
    check("set reaches the record and both copies", rc == 0 and "- **Jira Project Key:** NEW" in e.record("product.zorg-app")
          and "- **Jira Project Key:** NEW" in read(e.ctx) and read(e.mirror) == read(e.ctx)
          and jr[-1]["source"] == "ctx-set", (rc, out[-300:]))
    rc, out, res = run_ok(e, "get", "product.zorg-app", "Jira Project Key")
    check("get prints the value", rc == 0 and out.splitlines()[0].strip() == "NEW", out[:200])
    rc, out, res = run_ok(e, "append", "product.zorg-app", "--text", "- Android", "--under", "#### Platforms")
    check("append under a subsection", rc == 0 and "- iOS\n- Android\n" in read(e.ctx), (rc, out[-300:]))
    rc, out, res = run_ok(e, "add", "product", "Zorg Max", "--parent", "org.zorg")
    t = read(e.ctx)
    check("add places a product after its last sibling", rc == 0
          and t.index("### Product: Zorg Lite") < t.index("### Product: Zorg Max") < t.index("### Team: Alpha (A)"),
          (rc, out[-300:]))
    rc, out, res = run_ok(e, "list", "--type", "product", "--json")
    check("list --type product", rc == 0 and res and [r["id"] for r in res.get("records", [])]
          == ["product.zorg-app", "product.zorg-lite", "product.zorg-max"], res)
    before = read(e.ctx), read(e.mirror)
    run_ok(e, "snapshot", "--label", "manual")
    run_ok(e, "set", "product.zorg-lite", "Jira Project Key", "LLL")
    rc, out, res = run_ok(e, "undo")
    check("undo restores the copies", rc == 0 and (read(e.ctx), read(e.mirror)) == before, (rc, out[-300:]))
    rc, out, res = run_ok(e, "card")
    card = read(e.store, "INDEX.md")
    check("card regenerates INDEX.md without touching the copies", rc == 0 and card.count("\n") <= 200
          and (read(e.ctx), read(e.mirror)) == before, (rc, out[-200:]))
    e.edit(e.ctx, "- **Confluence Space:** ZAPP", "- **Confluence Space:** ZZZ")
    rc, out, res = run_ok(e, "set", "product.zorg-app", "Jira Project Key", "BOTH")
    rec = e.record("product.zorg-app")
    check("set after a direct edit imports it first", rc == 0 and "ZZZ" in rec and "BOTH" in rec, (rc, out[-300:]))
    e.edit(os.path.join(e.store, "records", "product.zorg-app.md"), "BOTH", "REC")
    e.edit(e.ctx, "BOTH", "FILE")
    rc, out, res = run_ok(e, "sync")
    lines = [l for l in out.splitlines() if l.strip()]
    check("a conflict exits 2 with CTX_CONFLICT before CTX_RESULT", rc == 2 and len(lines) >= 2
          and lines[-2].startswith("CTX_CONFLICT ") and "product.zorg-app" in lines[-2], (rc, out[-400:]))
    rc, out, res = run_ok(e, "sync", "--resolve", "product.zorg-app=record")
    check("--resolve=record keeps the record", rc == 0 and "REC" in read(e.ctx), (rc, out[-300:]))
    os.chmod(os.path.join(e.store, "records", "setting.templates.md"), 0)
    snap = read(e.ctx), read(e.mirror)
    e.edit(e.ctx, "- **Cadence:** daily", "- **Cadence:** weekly")
    rc, out, res = run_ok(e, "compile")
    os.chmod(os.path.join(e.store, "records", "setting.templates.md"), stat.S_IRUSR | stat.S_IWUSR)
    check("unreadable record aborts compile", rc == 3 and "setting.templates.md" in out
          and read(e.mirror) == snap[1], (rc, out[-300:]))
    open(os.path.join(e.store, "records", "product.zorg-app 2.md"), "w", encoding="utf-8").write(e.record("product.zorg-app"))
    rc, out, res = run_ok(e, "validate")
    check("validate reports stray files", rc == 0 and "product.zorg-app 2.md" in out, (rc, out[-300:]))
    open(os.path.join(e.store, "records", "product.zorg-copy.md"), "w", encoding="utf-8").write(e.record("product.zorg-app"))
    rc, out, res = run_ok(e, "validate")
    check("a record whose id differs from its file name fails validate", rc == 3 and "product.zorg-copy.md" in out,
          (rc, out[-300:]))
    os.remove(os.path.join(e.store, "records", "product.zorg-copy.md"))
    lockf = os.path.join(e.home, ".grow-pm", ".ctx.lock")
    open(lockf, "w").write(json.dumps({"pid": os.getpid(), "at": time.time()}))
    rc, out, res = run_ok(e, "set", "product.zorg-app", "Jira Project Key", "XX")
    os.remove(lockf)
    check("a held lock exits 4", rc == 4, (rc, out[-300:]))
    rc, out, res = e.run("set", "--nope")
    check("an unknown flag exits 3", rc == 3, (rc, out[-300:]))

with tempfile.TemporaryDirectory() as d:
    e = Env(d)
    run_ok(e, "migrate", "--apply")
    rc, out, res = run_ok(e, "undo")
    left = [f for dp, _, fn in os.walk(e.store) for f in fn]
    check("undo right after migrate removes the store", rc == 0 and left == [] and read(e.ctx) == e.text
          and read(e.mirror) == e.text, (rc, left, out[-300:]))

with tempfile.TemporaryDirectory() as d:
    e = Env(d, "rich")
    run_ok(e, "migrate", "--apply")
    rc, out, res = run_ok(e, "set", "team.alpha-a", "Lead", "X")
    check("a field inside a managed region is refused", rc == 4 and read(e.ctx) == e.text, (rc, out[-300:]))

with tempfile.TemporaryDirectory() as d:
    e = Env(d)
    run_ok(e, "migrate", "--apply")
    regdir = os.path.join(e.vault, "Notes", "_System", "providers"); os.makedirs(regdir)
    open(os.path.join(regdir, "zorg-core.yaml"), "w").write(
        "schema: provider-registration/1\nid: zorg-core\nkind: bundle\npaths:\n  - %s\nstatus: active\n"
        % os.path.join(e.vault, "Notes"))
    rc, out, res = run_ok(e, "set", "product.zorg-app", "Jira Project Key", "XX")
    check("store under a provider root is refused", rc == 4 and "PROJ" in read(e.ctx), (rc, out[-300:]))

# --- Final review: undo bounds, explicit paths, a file without a final newline, a record that never loads
def raw(env, args, cwd=None, extra_env=None, timeout=120):
    e2 = dict(os.environ); e2.pop("GROW_PM_CONTEXT_PATH", None); e2.update(extra_env or {})
    try:
        p = subprocess.run([sys.executable, CTX] + args, capture_output=True, text=True, env=e2, cwd=cwd, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, "still running after %d s" % timeout
    return p.returncode, p.stdout + p.stderr


def migrated_with_set(d):
    e = Env(d)
    run_ok(e, "migrate", "--apply")
    run_ok(e, "set", "product.zorg-app", "Jira Project Key", "ONE")
    return e


with tempfile.TemporaryDirectory() as d:
    e = migrated_with_set(d)
    after_set = read(e.ctx)
    rc, out, res = run_ok(e, "undo", "--steps", "0")
    check("undo --steps 0 is a usage error and changes nothing", rc == 3 and read(e.ctx) == after_set
          and os.path.isdir(os.path.join(e.store, ".state")), (rc, out[-300:]))

with tempfile.TemporaryDirectory() as d:
    e = migrated_with_set(d)
    e.edit(e.ctx, "- **Cadence:** daily", "- **Cadence:** weekly")
    rc, out, res = run_ok(e, "undo")
    check("undo with a direct edit not imported yet is refused and keeps the edit", rc == 4
          and "weekly" in read(e.ctx) and "ONE" in read(e.ctx), (rc, out[-300:]))

with tempfile.TemporaryDirectory() as d:
    e = migrated_with_set(d)
    rc, out = raw(e, ["set", "product.zorg-app", "Jira Project Key", "TYPO", "--home", e.home,
                      "--context", os.path.join(d, "no-such-context.md")])
    check("an explicit --context that does not exist is exit 3, never another file", rc == 3
          and "TYPO" not in read(e.ctx) and "no-such-context.md" in out, (rc, out[-300:]))

with tempfile.TemporaryDirectory() as d:
    e = migrated_with_set(d)
    e.edit(e.ctx, "- **Cadence:** daily", "- **Cadence:** weekly")
    rc, out = raw(e, ["sync", "--home", e.home, "--context", "local-context.md"], cwd=os.path.dirname(e.ctx))
    check("a relative --context imports the edit instead of overwriting it", rc == 0 and "weekly" in read(e.ctx)
          and "weekly" in e.record("setting.focus-focus-advisor"), (rc, out[-300:]))

with tempfile.TemporaryDirectory() as d:
    e = Env(d)
    for p in (e.ctx, e.mirror):
        open(p, "w", encoding="utf-8", newline="").write(e.text.rstrip("\n"))
    run_ok(e, "migrate", "--apply")
    rc, out, res = run_ok(e, "add", "custom", "Zorg Notes")
    check("add after a last line without a newline starts its own line", rc == 0
          and "_none_\n## Zorg Notes\n" in read(e.ctx), (rc, read(e.ctx)[-80:]))

with tempfile.TemporaryDirectory() as d:
    e = Env(d)
    run_ok(e, "migrate", "--apply")
    fifo = os.path.join(e.store, "records", "custom.zorg-slow.md")
    os.mkfifo(fifo)                         # open() blocks like an iCloud-evicted record
    before = read(e.ctx), read(e.mirror)
    t0 = time.time()
    rc, out = raw(e, ["compile", "--home", e.home, "--context", e.ctx], extra_env={"GROW_PM_CTX_READ_TIMEOUT": "1"},
                  timeout=30)
    took = time.time() - t0
    os.remove(fifo)
    check("a record that never loads is exit 3 within the read budget, copies untouched", rc == 3
          and "custom.zorg-slow.md" in out and took < 20 and (read(e.ctx), read(e.mirror)) == before, (rc, took, out[-300:]))

writers = ["references/context-protocol.md", "references/local-context-protocol.md", "skills/plugin-configurator/SKILL.md",
           "skills/plugin-configurator/references/maintenance-modes.md", "skills/context-connect/references/connect-steps.md"]
lacking = [w for w in writers if not any("context: records" in l and "without the digest" in l
                                         for l in read(ROOT, w).splitlines())]
check("every writer's sync step also covers a host without the session digest", lacking == [], lacking)
matrix = read(ROOT, "testing", "host-matrix.md")
check("the host matrix says what the ctx engine needs (spec §10)", "`ctx`" in matrix and "SHELL" in matrix
      and "ctx_cli_test" not in matrix, "no ctx note")

# --- v3.12 Task 0: write allow-list and safe undo (spec §7a)
with tempfile.TemporaryDirectory() as d:
    e = Env(d)
    run_ok(e, "migrate", "--apply")
    outside = os.path.join(d, "outside.md")
    open(outside, "w", encoding="utf-8", newline="").write(read(e.ctx))
    os.remove(e.ctx); os.symlink(outside, e.ctx)
    e.edit(e.mirror, "- **Cadence:** daily", "- **Cadence:** weekly")
    before = read(outside)
    rc, out, res = run_ok(e, "compile")
    check("a home copy linked outside the allowed roots is refused", rc == 4 and read(outside) == before,
          (rc, out[-300:]))

with tempfile.TemporaryDirectory() as d:
    e = Env(d)
    run_ok(e, "migrate", "--apply")
    elsewhere = os.path.join(d, "elsewhere")
    shutil.move(os.path.join(e.store, "records"), elsewhere)
    os.symlink(elsewhere, os.path.join(e.store, "records"))
    before = read(elsewhere, "product.zorg-app.md")
    rc, out, res = run_ok(e, "set", "product.zorg-app", "Jira Project Key", "OUT")
    check("a records folder linked outside is refused", rc == 4 and read(elsewhere, "product.zorg-app.md") == before,
          (rc, out[-300:]))

with tempfile.TemporaryDirectory() as d:
    e = migrated_with_set(d)
    victim = os.path.join(d, "victim.txt"); open(victim, "w").write("precious")
    last = [json.loads(l) for l in open(os.path.join(e.store, ".state", "journal.jsonl"), encoding="utf-8")][-1]["snapshot"]
    m = json.load(open(os.path.join(last, "manifest.json"), encoding="utf-8"))
    m["copies"].append({"path": victim, "file": "copies/0.md", "existed": True})
    json.dump(m, open(os.path.join(last, "manifest.json"), "w", encoding="utf-8"))
    rc, out, res = run_ok(e, "undo")
    check("undo never writes a path from the snapshot manifest", rc == 0 and open(victim).read() == "precious"
          and "skipped (not a current copy)" in out, (rc, out[-300:]))

with tempfile.TemporaryDirectory() as d:
    e = Env(d)
    run_ok(e, "migrate", "--apply")
    rc, out, res = run_ok(e, "set", "product.zorg-app", "Jira Project Key", "S", "--store", e.store)
    check("--store with a writing command is exit 3", rc == 3 and "PROJ" in e.record("product.zorg-app")
          and "- **Jira Project Key:** S" not in read(e.ctx), (rc, out[-300:]))

with tempfile.TemporaryDirectory() as d:
    e = Env(d)
    shutil.rmtree(e.vault)
    rc, out, res = run_ok(e, "migrate", "--apply")
    check("migrate --apply with a missing vault folder is exit 3 and creates nothing", rc == 3
          and not os.path.exists(e.vault), (rc, out[-300:]))

with tempfile.TemporaryDirectory() as d:
    e = Env(d)
    os.remove(e.ctx); os.symlink(e.mirror, e.ctx)
    run_ok(e, "migrate", "--apply")
    e.edit(e.mirror, "- **Cadence:** daily", "- **Cadence:** weekly")
    rc, out, res = run_ok(e, "sync")
    check("the home copy linked to the vault mirror still works", rc == 0 and os.path.islink(e.ctx)
          and "weekly" in e.record("setting.focus-focus-advisor"), (rc, out[-300:]))

# --- v3.12 Task 7: read, lifecycle, verify, typed set/get
def journal_ops(env):
    return [json.loads(l)["op"] for l in open(os.path.join(env.store, ".state", "journal.jsonl"), encoding="utf-8")]


with tempfile.TemporaryDirectory() as d:
    e = Env(d)
    run_ok(e, "migrate", "--apply")
    rc, out, res = run_ok(e, "read", "--skill", "requirements-creator", "--product", "Zorg App")
    check("read prints the card and the product block", rc == 0 and "# Context card" in out
          and "- **Jira Project Key:** PROJ" in out and res and res.get("tokens_est", 10 ** 6) <= 6000, (rc, out[-300:]))
    rc, out, res = run_ok(e, "read", "--skill", "no-such-skill")
    check("read of an unknown skill is exit 3", rc == 3 and "no manifest entry" in out, (rc, out[-200:]))
    rc, out, res = run_ok(e, "status")
    check("status shows the last snapshot", rc == 0 and "last snapshot:" in out, out[-400:])
    ok = []
    for args, op in ((("invalidate", "team.alpha-a", "--reason", "reorg"), "invalidate"),
                     (("archive", "setting.templates", "--reason", "old"), "archive"),
                     (("restore", "setting.templates"), "restore"),
                     (("verify", "product.zorg-app"), "verify")):
        rc, out, res = run_ok(e, *args)
        ok.append(rc == 0 and journal_ops(e)[-1] == op)
    check("invalidate / archive / restore / verify exit 0 and journal", all(ok), ok)
    rc, out, res = run_ok(e, "verify")
    check("verify without ids is exit 3", rc == 3, (rc, out[-200:]))
    run_ok(e, "archive", "setting.templates")
    e.edit(e.ctx, "## Focus (focus-advisor)\n\n- **Cadence:** daily\n\n", "")
    run_ok(e, "sync")
    rc1, out1, _ = run_ok(e, "list", "--archived")
    rc2, out2, _ = run_ok(e, "list", "--trash")
    check("list --archived and --trash", rc1 == 0 and "setting.templates" in out1 and rc2 == 0
          and "setting.focus-focus-advisor" in out2, (out1[-300:], out2[-300:]))
    rc, out, res = run_ok(e, "set", "profile", "Role", "Senior PM")
    check("set refuses a role outside the enum", rc == 3 and "head_of_product" in out
          and "- **Role:** pm" in read(e.ctx) and "- **Role:** pm" in read(e.mirror), (rc, out[-300:]))
    rc, out, res = run_ok(e, "get", "product.zorg-app", "Platforms", "--json")
    check("get --json returns a list for Platforms", rc == 0 and res and res.get("value") == ["web", "iOS"], (rc, res))

with tempfile.TemporaryDirectory() as d:
    e = Env(d)
    run_ok(e, "migrate", "--apply")
    fifo = os.path.join(e.store, "records", "custom.zorg-slow.md")
    os.mkfifo(fifo)
    t0 = time.time()
    rc, out = raw(e, ["read", "--skill", "requirements-creator", "--product", "Zorg App", "--home", e.home,
                      "--context", e.ctx], extra_env={"GROW_PM_CTX_READ_TIMEOUT": "1"}, timeout=30)
    took = time.time() - t0
    os.remove(fifo)
    check("read with an evicted record is exit 3", rc == 3 and took < 20 and "custom.zorg-slow.md" in out, (rc, took, out[-200:]))

with tempfile.TemporaryDirectory() as d:
    e = Env(d)
    import io, contextlib  # noqa: E401
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    import ctx as ctx_cli  # noqa: E402
    real = ctx_cli.co.migrate
    ctx_cli.co.migrate = lambda *a, **k: dict(real(*a, **k), identical=False)
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            rc = ctx_cli.main(["migrate", "--home", e.home, "--context", e.ctx])
    finally:
        ctx_cli.co.migrate = real
    check("migrate dry run DIFFERENT is exit 3", rc == 3 and '"ok": false' in buf.getvalue(), (rc, buf.getvalue()[-200:]))

# --- v3.12 Task 8: a half-migrated store
with tempfile.TemporaryDirectory() as d:
    e = Env(d)
    os.makedirs(os.path.join(e.store, "records"))
    open(os.path.join(e.store, "records", "profile.md"), "w").write("x")
    rc1, out1, _ = run_ok(e, "status")
    rc2, out2, _ = run_ok(e, "migrate", "--apply")
    check("a half-migrated store says what to remove", rc1 == 3 and "half-migrated store" in out1
          and "records" in out1 and rc2 == 4 and "half-migrated store" in out2, (out1[-300:], out2[-300:]))

# --- v3.12 Task 10: docs
lcp = read(ROOT, "references", "local-context-protocol.md")
check("Step 0c names ctx read and the fallback", 'ctx.py" read --skill' in lcp and "exit 3" in lcp
      and "whole" in lcp and "станом на" in lcp and "only on exit 3" in lcp
      and "the product the request names" in lcp, "Step 0c")
check("configurator lists the stale review item",
      "Review stale records" in read(ROOT, "skills", "plugin-configurator", "references", "maintenance-modes.md"))
cp = read(ROOT, "references", "context-protocol.md")
check("context-protocol documents every new command", all(("`%s" % c) in cp for c in
      ("read --skill", "invalidate", "archive", "restore", "verify")) and "--trash" in cp, "commands")
check(".gitignore ignores .codex/config.toml", ".codex/config.toml" in read(ROOT, ".gitignore").splitlines())

# --- v3.12 final review: undo of a migration, get --section
with tempfile.TemporaryDirectory() as d:
    e = Env(d)
    run_ok(e, "migrate", "--apply")
    run_ok(e, "undo")
    check("undo of a migration forgets the noted store", not os.path.exists(os.path.join(e.home, ".grow-pm", ".ctx-last-store")))

with tempfile.TemporaryDirectory() as d:
    e = Env(d)
    run_ok(e, "migrate", "--apply")
    rc, out, res = run_ok(e, "get", "product.zorg-app", "--section", "#### Platforms")
    check("get --section prints the subsection", rc == 0 and "#### Platforms" in out and "- web" in out, (rc, out[-200:]))

# --- v3.12.1: ctx assign
CUSTOM = "\n## Zorg Partner Rules\n\n- Always say Zorg Partner.\n- Detail: never Partner Zorg in print.\n"


def with_custom(e, extra=CUSTOM):
    for p in (e.ctx, e.mirror):
        if os.path.exists(p):
            text = read(p).rstrip("\n") + "\n" + extra
            open(p, "w", encoding="utf-8", newline="").write(text)
    run_ok(e, "migrate", "--apply")
    return "custom.zorg-partner-rules"


def last_journal(e):
    return json.loads(read(e.store, ".state", "journal.jsonl").strip().splitlines()[-1])


with tempfile.TemporaryDirectory() as d:
    e = Env(d)
    cid = with_custom(e)
    before = read(e.ctx)
    rc, out, r = run_ok(e, "assign", cid, "all")
    check("assign all", rc == 0 and r["read_by"] == "all" and 'read_by: "all"' in e.record(cid), (rc, out[-300:]))
    check("assign writes the journal", last_journal(e)["op"] == "assign", last_journal(e))
    check("assign leaves local-context.md as is", read(e.ctx) == before)
    rc, out, r = run_ok(e, "read", "--skill", "product-analysis", "--product", "Zorg App")
    check("an assigned record is read", "never Partner Zorg in print" in out, out[-400:])
    rc, out, r = run_ok(e, "assign", cid, "write-concept,product-analysis")
    check("assign names, sorted", rc == 0 and r["read_by"] == "product-analysis, write-concept", r)
    rc, out, r = run_ok(e, "assign", cid, "none")
    check("assign none removes the key", rc == 0 and "read_by" not in e.record(cid), e.record(cid)[:400])
    rc, out, r = run_ok(e, "assign", cid, "no-such-skill")
    check("unknown skill is exit 3", rc == 3 and "unknown skill" in out and "no-such-skill" in out, (rc, out[-300:]))
    rc, out, r = run_ok(e, "assign", "product.zorg-app", "all")
    check("product record is refused", rc == 3 and "custom and setting" in out, (rc, out[-300:]))
    run_ok(e, "assign", cid, "all")
    rc, out, r = run_ok(e, "undo")
    check("undo removes read_by", rc == 0 and "read_by" not in e.record(cid), (rc, out[-300:]))
    e.edit(e.ctx, "never Partner Zorg in print.", "never Partner Zorg — pending.")
    rc, out, r = run_ok(e, "assign", cid, "all")
    check("assign imports pending edits first", rc == 0 and "pending" in e.record(cid), (rc, out[-300:]))

# --- v3.12.1: validate, status count custom records nobody reads
with tempfile.TemporaryDirectory() as d:
    e = Env(d)
    cid = with_custom(e)
    sp = os.path.join(e.store, "records", "setting.templates.md")
    st = read(sp)
    open(sp, "w", encoding="utf-8", newline="").write(st.replace("\n---\n", '\nread_by: "no-such-skill"\n---\n', 1))
    rc, out, r = run_ok(e, "validate")
    check("validate names unassigned custom", "custom without read_by: 1" in out and "ctx assign" in out, out[-500:])
    check("validate warns on an unknown reader", "read_by names unknown skill(s): no-such-skill" in out, out[-500:])
    rc, out_status, r = run_ok(e, "status")
    check("status lists unassigned", "custom without read_by: " + cid in out_status and r["unassigned"] == [cid], out_status[-400:])

# --- v3.12.1 minors
def edit_both(e, old, new):
    for p in (e.ctx, e.mirror):
        if os.path.exists(p):
            e.edit(p, old, new)


def add_frontmatter(e, rid, lines):
    p = os.path.join(e.store, "records", rid + ".md")
    text = read(p).replace("\n---\n", "\n" + lines + "\n---\n", 1)
    open(p, "w", encoding="utf-8", newline="").write(text)


with tempfile.TemporaryDirectory() as d:      # m1: ctx card keeps the stale and archive marks
    e = Env(d)
    run_ok(e, "migrate", "--apply")
    add_frontmatter(e, "setting.templates", 'verified: "2025-01-01"\nttl_days: 30')
    run_ok(e, "archive", "setting.planning-planning-suite", "--reason", "old")
    rc, out, r = run_ok(e, "card")
    card = read(e.store, "INDEX.md")
    check("ctx card keeps stale and archive marks", rc == 0 and "⚠ 2025-01-01" in card and "**Архів:** 1" in card, card[-600:])

with tempfile.TemporaryDirectory() as d:      # m3: a typed get of a placeholder
    e = Env(d)
    edit_both(e, "- **Jira Project Key:** PROJ", "- **Jira Project Key:** _(not set)_")
    run_ok(e, "migrate", "--apply")
    rc, out, r = run_ok(e, "get", "product.zorg-app", "Jira Project Key")
    check("typed get of a placeholder", rc == 0 and "_(not set)_" in out and r["value"] is None and r.get("not_set") is True,
          (rc, out[-300:]))

with tempfile.TemporaryDirectory() as d:      # m5: an internal KeyError in read is not "no manifest entry"
    e = Env(d)
    run_ok(e, "migrate", "--apply")
    import contextlib, io
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    import ctx as ctxmod  # noqa: E402
    orig = ctxmod.cr.read_view

    def boom(*a, **k):
        raise KeyError("internal")
    ctxmod.cr.read_view = boom
    buf, raised = io.StringIO(), False
    os.environ.pop("GROW_PM_CONTEXT_PATH", None)
    try:
        with contextlib.redirect_stdout(buf):
            ctxmod.main(["read", "--skill", "product-analysis", "--home", e.home, "--context", e.ctx])
    except KeyError:
        raised = True
    finally:
        ctxmod.cr.read_view = orig
    check("an internal KeyError in read is not masked", raised and "no manifest entry" not in buf.getvalue(), buf.getvalue()[-300:])
    rc, out, r = run_ok(e, "read", "--skill", "no-such-skill")
    check("unknown skill in read is exit 3", rc == 3 and "no manifest entry for no-such-skill" in out, out[-300:])

with tempfile.TemporaryDirectory() as d:      # m6: card platforms match by heading prefix
    e = Env(d)
    edit_both(e, "#### Platforms\n", "#### Platforms (mobile first)\n")
    run_ok(e, "migrate", "--apply")
    run_ok(e, "card")
    check("card platforms match by heading prefix", "platforms web, iOS" in read(e.store, "INDEX.md"), read(e.store, "INDEX.md")[:900])

# --- v3.12.1: undo after an import leaves the store consistent (compressed acceptance S8/S9)
with tempfile.TemporaryDirectory() as d:
    e = Env(d)
    run_ok(e, "migrate", "--apply")
    before = read(e.ctx)
    t = read(e.ctx); i = t.index("## Templates"); j = t.index("\n## ", i + 3)
    open(e.ctx, "w", encoding="utf-8", newline="").write(t[:i] + t[j + 1:])
    run_ok(e, "sync")
    rc, out, r = run_ok(e, "undo")
    rc_s, out_s, r_s = run_ok(e, "status")
    check("undo after an imported removal brings the section back in both copies",
          rc == 0 and read(e.ctx) == before and read(e.mirror) == before, (rc, out[-300:]))
    check("undo after an import leaves the store in sync", "to import: nothing — in sync" in out_s and r_s["conflicts"] == [],
          out_s[-300:])
    e.edit(e.ctx, "- **Jira Project Key:** PROJ", "- **Jira Project Key:** EDIT")
    run_ok(e, "sync")
    rc, out, r_undo = run_ok(e, "undo")
    check("undo after an imported edit reverts it in the copies", "PROJ" in read(e.ctx) and "EDIT" not in read(e.ctx)
          and "EDIT" not in read(e.mirror))
    check("the edit is kept in the pre-undo snapshot", "EDIT" in read(r_undo["snapshot"], "copies", "0.md"), r_undo)
    run_ok(e, "set", "product.zorg-app", "Locales", "uk")
    rc, out, r = run_ok(e, "undo")
    check("undo of a ctx write unchanged", rc == 0 and "Locales:** uk" not in read(e.ctx), out[-300:])

# --- v3.12.1 final review: undo of a compile snapshot; assign does not verify
with tempfile.TemporaryDirectory() as d:
    e = Env(d)
    run_ok(e, "migrate", "--apply")
    os.remove(e.mirror)
    run_ok(e, "compile")
    recreated = os.path.exists(e.mirror)
    rc, out, r = run_ok(e, "undo")
    check("undo of a compile snapshot takes the compile back", recreated and rc == 0 and not os.path.exists(e.mirror),
          (recreated, rc, out[-300:]))

with tempfile.TemporaryDirectory() as d:
    e = Env(d)
    cid = with_custom(e)
    add_frontmatter(e, cid, 'verified: "2025-01-01"')
    rc, out, r = run_ok(e, "assign", cid, "all")
    check("assign keeps the verified date", rc == 0 and 'verified: "2025-01-01"' in e.record(cid), e.record(cid)[:500])

# --- v3.13.0: ctx provider adopt — bases for the blocks already in your context
GROWTH_FILE = "Growth/_System/context-blocks.md"
GROWTH_PATH = "ZorgGrowth/" + GROWTH_FILE                       # endpoint.root + blocks_file
GROWTH_TEXT = read(REPOS_FIX, "zorg-growth", *GROWTH_FILE.split("/"))
CORE_SCOPE = "<!-- zorg-core:begin id=scope v=0.4 -->\n### Scope of work\nThe user works on Zorg App only.\n<!-- zorg-core:end id=scope -->"


def tree_of(*roots):
    """{path: bytes} of every file under the roots — to prove that a run wrote nothing."""
    out = {}
    for r in roots:
        for dp, _, fn in os.walk(r):
            for n in fn:
                out[os.path.join(dp, n)] = open(os.path.join(dp, n), "rb").read()
    return out


def repos_env(d, url, patch=()):
    """The fixture context with zorg-core (a folder: a run-time copy of the core fixture) and zorg-growth (an MCP
    server at `url`) registered, and zorg-dead (a server nobody answers). `patch` is [(old, new)] applied to both copies."""
    e = Env(d, fixture="context", fix=REPOS_FIX)
    for old_, new_ in patch:
        edit_both(e, old_, new_)
    core = os.path.join(d, "ZorgCore")
    shutil.copytree(CORE_FIX, core)
    prov = os.path.join(e.home, ".grow-pm", "providers")
    os.makedirs(prov)
    open(os.path.join(prov, "zorg-core.yaml"), "w", encoding="utf-8").write(
        "schema: provider-registration/1\nid: zorg-core\nkind: bundle\nauthority: org\npaths:\n  - %s\nteam: team-alpha\n"
        "role: pm\njira_write: own\n" % core)
    reg = ("schema: provider-registration/2\nid: %s\nkind: mcp\nauthority: team\nendpoint:\n  url: %s\n  root: \"ZorgGrowth/\"\n"
           "blocks_file: %s\nblocks_source: mcp\nteam: team-alpha\n")
    open(os.path.join(prov, "zorg-growth.yaml"), "w", encoding="utf-8").write(reg % ("zorg-growth", url, GROWTH_FILE))
    open(os.path.join(prov, "zorg-dead.yaml"), "w", encoding="utf-8").write(reg % ("zorg-dead", "http://127.0.0.1:9/mcp", GROWTH_FILE))
    return e


def block_state(e, repo):
    path = os.path.join(e.store, ".state", "blocks", repo + ".json")
    return json.loads(read(path)) if os.path.isfile(path) else None


with FakeMcp(tree={GROWTH_PATH: GROWTH_TEXT}) as fake:
    with tempfile.TemporaryDirectory() as d:
        e = repos_env(d, fake.url)
        blocks_dir = os.path.join(e.store, ".state", "blocks")
        rc, out, res = run_ok(e, "provider", "adopt", "zorg-core")
        check("adopt without a store: exit 3, nothing created", rc == 3 and "no store" in out and not os.path.exists(e.store)
              and not os.path.exists(os.path.join(e.home, ".grow-pm", "snapshots")), (rc, out[-300:]))
        rc, out, res = run_ok(e, "provider", "adopt", "zorg-core", "--apply")
        check("…--apply too", rc == 3 and "no store" in out and not os.path.exists(e.store)
              and not os.path.exists(os.path.join(e.home, ".grow-pm", "snapshots")), (rc, out[-300:]))
        run_ok(e, "migrate", "--apply")
        rc, out, res = run_ok(e, "provider")
        check("provider without an action is a usage error", rc == 3, (rc, out[-200:]))
        rc, out, res = run_ok(e, "provider", "adopt", "no-such-repo", "--apply")
        check("an unknown repository: exit 3, nothing written", rc == 3 and "no-such-repo" in out and not os.path.isdir(blocks_dir), (rc, out[-300:]))

        ctx_before, mirror_before = read(e.ctx), read(e.mirror)
        records_before = tree_of(os.path.join(e.store, "records"))
        everything = tree_of(e.home, e.vault)
        rc, out, res = run_ok(e, "provider", "adopt", "zorg-core")
        check("adopt dry run writes nothing", rc == 0 and not os.path.isdir(blocks_dir) and "dry run" in out
              and tree_of(e.home, e.vault) == everything, (rc, out[-400:]))
        check("…and says what it would do: the blocks and what they become", res is not None and res["written"] is False
              and res["blocks"] == {"scope": "base", "teams": "base", "team": "base"} and res["new"] == ["product"]
              and "scope" in out and "product" in out, (res, out[-500:]))

        rc, out, res = run_ok(e, "provider", "adopt", "zorg-core", "--apply")
        st = block_state(e, "zorg-core")
        check("adopt --apply records bases, no record changes", rc == 0 and res["written"] is True
              and tree_of(os.path.join(e.store, "records")) == records_before and read(e.ctx) == ctx_before
              and read(e.mirror) == mirror_before and st is not None and set(st["blocks"]) == {"scope", "teams", "team"}, (rc, out[-400:]))
        check("…the base of a block is the repository's text, kept by its hash",
              read(blocks_dir, "zorg-core", st["blocks"]["scope"]["base_sha"] + ".md") == CORE_SCOPE
              and st["blocks"]["scope"]["host"] == "custom.zorg-core-notes" and st["blocks"]["team"]["host"] == "team.alpha-a"
              and st["blocks"]["scope"]["user_removed"] is None and st["source"] == "folder", st)
        check("adopt is journalled", last_journal(e)["op"] == "provider-adopt" and last_journal(e)["source"] == "repo:zorg-core"
              and sorted(last_journal(e)["ids"]) == ["scope", "team", "teams"] and os.path.isdir(last_journal(e)["snapshot"]), last_journal(e))
        check("…and the state is in the snapshot's successor, not in the snapshot taken before it",
              not os.path.isdir(os.path.join(last_journal(e)["snapshot"], "state", "blocks")), "")

        state_file = read(blocks_dir, "zorg-core.json")
        n_lines = len(read(e.store, ".state", "journal.jsonl").splitlines())
        rc, out, res = run_ok(e, "provider", "adopt", "zorg-core", "--apply")
        check("adopt again: every block already has a base, and nothing changes", rc == 0 and "already has a base" in out
              and set(res["blocks"].values()) == {"has-base"} and read(blocks_dir, "zorg-core.json") == state_file
              and len(read(e.store, ".state", "journal.jsonl").splitlines()) == n_lines, (rc, out[-400:]))

        rc, out, res = run_ok(e, "provider", "adopt", "zorg-growth", "--apply")
        sg = block_state(e, "zorg-growth")
        check("an MCP repository: its blocks get bases too, apart from the core's block of the same id",
              rc == 0 and res["blocks"] == {"growth-metrics": "base", "team": "base"} and set(sg["blocks"]) == {"growth-metrics", "team"}
              and sg["source"] == "mcp" and block_state(e, "zorg-core") == json.loads(state_file), (rc, out[-400:], sg))
        rc, out, res = run_ok(e, "undo")
        check("undo takes an adopt back: the state of that repository is gone, the other's stays",
              rc == 0 and block_state(e, "zorg-growth") is None and block_state(e, "zorg-core") == json.loads(state_file), (rc, out[-300:]))
        rc, out, res = run_ok(e, "undo", "--steps", "3")        # the undo above is itself a change in the journal
        check("…and the adopt before it: no block state at all", rc == 0 and block_state(e, "zorg-core") is None
              and not os.path.isdir(os.path.join(blocks_dir, "zorg-core")), (rc, out[-300:]))

        e.edit(e.ctx, "The user works on Zorg App only.", "The user works on Zorg App only (typed in the file).")
        rc, out, res = run_ok(e, "provider", "adopt", "zorg-core")
        check("edits to local-context.md that are not imported yet are mentioned, so adopt is not run on a stale view",
              rc == 0 and "not imported" in out and res["pending"] > 0, (rc, out[-400:]))
        rc, out, res = run_ok(e, "provider", "adopt", "zorg-core", "--apply", "--store", e.store)
        check("--store is refused for adopt --apply, as for every writing command", rc == 3 and "--store is for read commands only" in out
              and block_state(e, "zorg-core") is None, (rc, out[-300:]))
        rc, out, res = run_ok(e, "provider", "adopt", "zorg-core", "--store", e.store)
        check("…and allowed for the dry run", rc == 0 and "dry run" in out, (rc, out[-300:]))

        before = tree_of(e.home, e.vault)
        rc5, out5, res5 = run_ok(e, "provider", "adopt", "zorg-dead", "--apply")
        check("an unreachable repository: exit 5, nothing written", rc5 == 5 and not os.path.isdir(blocks_dir)
              and tree_of(e.home, e.vault) == before and res5["ok"] is False and "unreachable" in out5, (rc5, out5[-400:]))
        rc5, out5, res5 = run_ok(e, "provider", "adopt", "zorg-dead")
        check("…a dry run too", rc5 == 5 and tree_of(e.home, e.vault) == before, (rc5, out5[-300:]))

    with tempfile.TemporaryDirectory() as d:            # a block you edited, a block of another version
        e = repos_env(d, fake.url, patch=[("The user works on Zorg App only.", "The user works on Zorg App only. (my note)"),
                                          ("zorg-core:begin id=teams v=0.4", "zorg-core:begin id=teams v=0.3")])
        run_ok(e, "migrate", "--apply")
        rc, out, res = run_ok(e, "provider", "adopt", "zorg-core", "--apply")
        st = block_state(e, "zorg-core")
        check("an edited block is adopted as your edit", rc == 0 and res["blocks"]["scope"] == "edit" and "edit" in out, (rc, out[-400:], res))
        check("another version → no base", res["blocks"]["teams"] == "none" and "teams" not in st["blocks"], (res, st))
        check("…the repository's text is the base of the edit, not yours",
              read(e.store, ".state", "blocks", "zorg-core", st["blocks"]["scope"]["base_sha"] + ".md") == CORE_SCOPE
              and "(my note)" in e.record("custom.zorg-core-notes"), st)
        check("…the block with no base is named, with the two versions", "teams" in out and "0.3" in out and "0.4" in out, out[-500:])
        check("the team block is a base", res["blocks"]["team"] == "base" and "team" in st["blocks"], res)


check("every command ends with a CTX_RESULT line", contract_ok)
print("RESULT:", "GREEN ✅" if not fails else "RED ❌", "(%d failed)" % fails)
sys.exit(1 if fails else 0)
