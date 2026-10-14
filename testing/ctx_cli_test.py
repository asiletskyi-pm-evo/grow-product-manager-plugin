#!/usr/bin/env python3
"""TC-ctx-3110-cli — scripts/ctx.py, the context store's command line (since v3.11.0).

Every command end to end on a temp HOME (the fictional typical context) and a temp vault with
its mirror: the output contract (`CTX_RESULT {json}` last, `CTX_CONFLICT` before it), the exit
codes (0 ok, 2 conflict, 3 bad input / no store / unreadable, 4 refused) and the safety rules
(import before write, snapshot, lock, managed regions, the provider boundary).
Semantics: references/context-protocol.md. Stdlib only; run from the repo root.
"""
import json, os, re, shutil, stat, subprocess, sys, tempfile, time

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

# --- v3.13.0 Task 10: undo after a record edit made in the file (Obsidian) reverts it
def add_line(path, line):
    t = read(path)
    open(path, "w", encoding="utf-8", newline="").write(t + ("" if t.endswith("\n") else "\n") + line + "\n")


def in_sync(e):
    rc, out, r = run_ok(e, "status")
    return "to import: nothing — in sync" in out and r["conflicts"] == []


with tempfile.TemporaryDirectory() as d:
    e = Env(d)
    run_ok(e, "migrate", "--apply")
    rec_path = os.path.join(e.store, "records", "setting.templates.md")
    rec_before, ctx_before, mirror_before = read(rec_path), read(e.ctx), read(e.mirror)
    add_line(rec_path, "- obsidian edit")
    rc_s, out_s, _ = run_ok(e, "sync")
    check("setup: sync imports the record edit into both copies",
          rc_s == 0 and "obsidian edit" in read(e.ctx) and "obsidian edit" in read(e.mirror), (rc_s, out_s[-300:]))
    rc, out, r = run_ok(e, "undo")
    check("undo after an Obsidian record edit reverts it", rc == 0 and "obsidian edit" not in e.record("setting.templates")
          and "obsidian edit" not in read(e.ctx) and "obsidian edit" not in read(e.mirror) and in_sync(e), (rc, out[-400:]))
    check("…the record, both copies are what they were before the edit, byte for byte",
          e.record("setting.templates") == rec_before and (read(e.ctx), read(e.mirror)) == (ctx_before, mirror_before),
          (e.record("setting.templates")[-300:], rc))
    check("…the edit stays in the pre-undo snapshot", "obsidian edit" in read(r["snapshot"], "records", "setting.templates.md"), r)
    check("…the result and the message name the record that was put back",
          r.get("records_reverted") == ["setting.templates"] and "setting.templates" in out, (r, out[-400:]))
    rc, out, r2 = run_ok(e, "undo")
    check("undoing that undo brings the edit back, and the store is in sync",
          rc == 0 and "obsidian edit" in e.record("setting.templates") and "obsidian edit" in read(e.ctx)
          and r2.get("records_reverted") == [] and in_sync(e), (rc, out[-400:], r2))

with tempfile.TemporaryDirectory() as d:        # two edits, two syncs: one undo takes back the last only
    e = Env(d)
    run_ok(e, "migrate", "--apply")
    rec_path = os.path.join(e.store, "records", "setting.templates.md")
    add_line(rec_path, "- first edit")
    run_ok(e, "sync")
    add_line(rec_path, "- second edit")
    run_ok(e, "sync")
    rc, out, r = run_ok(e, "undo")
    check("undo takes back the last Obsidian edit and keeps the earlier one",
          rc == 0 and "first edit" in e.record("setting.templates") and "second edit" not in e.record("setting.templates")
          and "first edit" in read(e.ctx) and "second edit" not in read(e.ctx) and in_sync(e), (rc, out[-400:]))

with tempfile.TemporaryDirectory() as d:        # a record edit and a copy edit in one sync
    e = Env(d)
    run_ok(e, "migrate", "--apply")
    rec_path = os.path.join(e.store, "records", "setting.templates.md")
    rec_before, ctx_before = read(rec_path), read(e.ctx)
    add_line(rec_path, "- obsidian edit")
    e.edit(e.ctx, "- **Jira Project Key:** PROJ", "- **Jira Project Key:** EDIT")
    rc_s, out_s, _ = run_ok(e, "sync")
    rc, out, r = run_ok(e, "undo")
    check("undo of a sync that took a record edit and a copy edit reverts both",
          rc_s == 0 and rc == 0 and e.record("setting.templates") == rec_before and read(e.ctx) == ctx_before
          and read(e.mirror) == ctx_before and in_sync(e), (rc_s, rc, out[-400:]))

with tempfile.TemporaryDirectory() as d:        # a later ctx write: undo --steps 2 reaches back past it
    e = Env(d)
    run_ok(e, "migrate", "--apply")
    rec_path = os.path.join(e.store, "records", "setting.templates.md")
    rec_before, ctx_before = read(rec_path), read(e.ctx)
    add_line(rec_path, "- obsidian edit")
    run_ok(e, "sync")
    run_ok(e, "set", "product.zorg-app", "Jira Project Key", "NEW")
    rc, out, r = run_ok(e, "undo", "--steps", "2")
    check("undo --steps 2 over a ctx write and an Obsidian edit reverts both",
          rc == 0 and e.record("setting.templates") == rec_before and read(e.ctx) == ctx_before and in_sync(e),
          (rc, out[-400:]))

with tempfile.TemporaryDirectory() as d:        # frontmatter edited in the same save: only the body is put back
    e = Env(d)
    run_ok(e, "migrate", "--apply")
    rec_path = os.path.join(e.store, "records", "setting.templates.md")
    add_frontmatter(e, "setting.templates", 'aliases: ["obsidian alias"]')
    add_line(rec_path, "- obsidian edit")
    run_ok(e, "sync")
    rc, out, r = run_ok(e, "undo")
    check("undo puts the body back and keeps the frontmatter the file has",
          rc == 0 and "obsidian edit" not in e.record("setting.templates") and "obsidian alias" in e.record("setting.templates")
          and "obsidian edit" not in read(e.ctx) and in_sync(e), (rc, out[-400:], e.record("setting.templates")[:400]))

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


def repos_env(d, url, patch=(), core_extra=""):
    """The fixture context with zorg-core (a folder: a run-time copy of the core fixture) and zorg-growth (an MCP
    server at `url`) registered, and zorg-dead (a server nobody answers). `patch` is [(old, new)] applied to both copies;
    `core_extra` is more lines for zorg-core's registration."""
    e = Env(d, fixture="context", fix=REPOS_FIX)
    for old_, new_ in patch:
        edit_both(e, old_, new_)
    core = os.path.join(d, "ZorgCore")
    shutil.copytree(CORE_FIX, core)
    prov = os.path.join(e.home, ".grow-pm", "providers")
    os.makedirs(prov)
    open(os.path.join(prov, "zorg-core.yaml"), "w", encoding="utf-8").write(
        "schema: provider-registration/1\nid: zorg-core\nkind: bundle\nauthority: org\npaths:\n  - %s\nteam: team-alpha\n"
        "role: pm\njira_write: own\n%s" % (core, core_extra))
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


# --- v3.13.0: ctx provider plan — one table per repository, read only
CORE_BLOCKS = os.path.join("Core", "_System", "context-blocks.md")
CORE_CARD = os.path.join("Core", "Teams", "team-alpha.md")
SKIP_PRODUCT = "skip_blocks:\n  - product\n"


def signs_in(res):
    return {r["block"]: r["sign"] for r in res["rows"]}


untouched = []


def plan_run(e, core, *args):
    """A plan run, with the proof that it wrote nothing: the home, the vault and the core are the same bytes after it."""
    before = tree_of(e.home, e.vault, core)
    rc, out, res = run_ok(e, "provider", "plan", *args)
    untouched.append(tree_of(e.home, e.vault, core) == before)
    return rc, out, res


def change(path, old, new):
    t = read(path)
    assert old in t, old
    open(path, "w", encoding="utf-8", newline="").write(t.replace(old, new, 1))


with FakeMcp(tree={GROWTH_PATH: GROWTH_TEXT}) as fake:
    with tempfile.TemporaryDirectory() as d:
        e = repos_env(d, fake.url, core_extra=SKIP_PRODUCT)
        core = os.path.join(d, "ZorgCore")
        blocks_file, card = os.path.join(core, CORE_BLOCKS), os.path.join(core, CORE_CARD)
        pristine_blocks, pristine_card = read(blocks_file), read(card)
        rc, out, res = plan_run(e, core, "zorg-core")
        check("plan without a store: exit 3, nothing created", rc == 3 and "no store" in out and not os.path.exists(e.store), (rc, out[-300:]))
        run_ok(e, "migrate", "--apply")
        rc, out, res = plan_run(e, core, "no-such-repo")
        check("plan of an unknown repository: exit 3", rc == 3 and "no-such-repo" in out, (rc, out[-300:]))
        rc, out, res = run_ok(e, "provider", "plan", "zorg-core", "--product")
        check("a flag without its value is a usage error", rc == 3, (rc, out[-200:]))
        run_ok(e, "provider", "adopt", "zorg-core", "--apply")
        run_ok(e, "provider", "adopt", "zorg-growth", "--apply")

        rc, out, res = plan_run(e, core, "zorg-core")
        check("nothing moved: exit 0, every block '=', a skipped block is not shown",
              rc == 0 and set(signs_in(res).values()) == {"="} and set(signs_in(res)) == {"scope", "teams", "team"}
              and "Питань: 0 · зміниться записів: 0" in out, (rc, out[-500:]))
        check("…the header and the last line are the table's own",
              out.splitlines()[0] == "zorg-core · джерело: тека · ядро v0.4 · база v0.4"
              and out.splitlines()[-2] == "Питань: 0 · зміниться записів: 0", out)
        check("…the data: the documented keys and rows",
              res["repo"] == "zorg-core" and res["questions"] == 0 and res["changes"] == 0 and res["errors"] == []
              and res["rows"][0].keys() >= {"block", "sign", "host", "source", "note"} and res["base_version"] == "0.4", res)
        rc, out, res = plan_run(e, core, "zorg-core", "--all")
        check("--all shows the skipped block: '·'", signs_in(res).get("product") == "·" and "пропущено" in out and res["questions"] == 0, (rc, out[-400:]))
        rc, out, res = plan_run(e, core, "zorg-core", "--json", "--store", e.store)
        check("--json and --store are accepted: a read command", rc == 0 and res["rows"], (rc, out[-300:]))

        change(blocks_file, "<!-- zorg-core:begin id=scope v=0.4 -->\n### Scope of work\nThe user works on Zorg App only.",
               "<!-- zorg-core:begin id=scope v=0.5 -->\n### Scope of work\nThe user works on Zorg App and Zorg Lite.")
        rc, out, res = plan_run(e, core, "zorg-core")
        check("the core changed a block you did not touch → '~', one record would change",
              rc == 0 and signs_in(res)["scope"] == "~" and "Питань: 0 · зміниться записів: 1" in out
              and res["version"] in ("0.4", "0.5"), (rc, out[-500:]))
        open(blocks_file, "w", encoding="utf-8", newline="").write(pristine_blocks.replace(
            "<!-- zorg-core:begin id=scope v=0.4 -->\n### Scope of work\nThe user works on Zorg App only.\n<!-- zorg-core:end id=scope -->\n\n", ""))
        rc, out, res = plan_run(e, core, "zorg-core")
        check("the core no longer has a block you hold → '−'", signs_in(res)["scope"] == "−" and "зміниться записів: 1" in out, (rc, out[-500:]))
        open(blocks_file, "w", encoding="utf-8", newline="").write(pristine_blocks.rstrip("\n") + "\n\n"
              "<!-- zorg-core:begin id=okr v=0.1 -->\n### OKR\n- grow\n<!-- zorg-core:end id=okr -->\n")
        rc, out, res = plan_run(e, core, "zorg-core")
        check("a new block in the core → '+', a question", signs_in(res)["okr"] == "+" and "Питань: 1 · зміниться записів: 0" in out
              and signs_in(res)["scope"] == "=", (rc, out[-500:]))
        open(blocks_file, "w", encoding="utf-8", newline="").write(pristine_blocks)

        edit_both(e, "- Alpha, Beta", "- Alpha, Beta, Gamma")
        rc, out, res = plan_run(e, core, "zorg-core")
        check("you edited a block in local-context.md (not imported yet) → '✎'", signs_in(res)["teams"] == "✎" and rc == 0
              and "Питань: 0 · зміниться записів: 0" in out, (rc, out[-500:]))
        run_ok(e, "sync")
        rc, out, res = plan_run(e, core, "zorg-core")
        check("…and after the import too", signs_in(res)["teams"] == "✎" and signs_in(res)["scope"] == "=", (rc, out[-500:]))

        change(card, 'head: "Alex One"', 'head: "Alex Prime"')
        edit_both(e, "- **jira_team_field:** Alpha", "- **jira_team_field:** Alpha (mine)")
        rc, out, res = plan_run(e, core, "zorg-core")
        check("both sides changed the team block → '⚠', with the three versions under the row",
              signs_in(res)["team"] == "⚠" and "    Ядро тепер каже: " in out and "    Ви писали: " in out
              and "    Раніше обидва казали: " in out and "Alex Prime" in out and "Alpha (mine)" in out, (rc, out[-900:]))
        check("…a question for it", "Питань: 1 · зміниться записів: 0" in out and res["questions"] == 1, out[-200:])
        open(card, "w", encoding="utf-8", newline="").write(pristine_card)

        rc, out, res = run_ok(e, "repo", "status", "zorg-core")
        row = res["repos"][0]
        check("repo status shows the base version the plan reads", rc == 0 and "base: 0.4" in out and row["base_version"] == "0.4", (rc, out[-300:]))
        rc, out, res = run_ok(e, "repo", "status", "zorg-dead")
        check("…and '—' where nothing was adopted", rc == 0 and "base: —" in out and res["repos"][0]["base_version"] is None, (rc, out[-300:]))

        rc, out, res = plan_run(e, core)
        check("no repository named: one table per registered repository, the unreachable one named; exit 5, the others printed",
              rc == 5 and "zorg-core · джерело: тека" in out and "zorg-growth · джерело: MCP (127.0.0.1)" in out
              and "zorg-dead · недоступний" in out and res["ok"] is False
              and [r["repo"] for r in res["repos"]] == ["zorg-core", "zorg-dead", "zorg-growth"], (rc, out[-900:]))
        check("…the unreachable one carries its reason in the data", [x for x in res["repos"] if x["repo"] == "zorg-dead"][0].get("error"), res["repos"])
        rc, out, res = plan_run(e, core, "zorg-dead")
        check("an unreachable repository: exit 5, 'недоступний', nothing written", rc == 5 and "недоступний" in out and res["ok"] is False
              and "error" in res, (rc, out[-400:]))

        prov = os.path.join(e.home, ".grow-pm", "providers")
        for rid, names in (("zorg-core", ["Zorg App"]), ("zorg-growth", ["Other Product"])):
            with open(os.path.join(prov, rid + ".yaml"), "a", encoding="utf-8") as f:
                f.write("products:\n" + "".join("  - %s\n" % n for n in names))
        rc, out, res = plan_run(e, core, "--product", "zorg app")
        check("--product: the repositories of that product (matched like `ctx read`), and those that serve every product",
              "zorg-core · джерело" in out and "zorg-growth" not in out and "zorg-dead · недоступний" in out and rc == 5, (rc, out[-600:]))
        rc, out, res = plan_run(e, core, "--product", "No Such Product")
        check("--product that is none of the products: exit 3", rc == 3 and "No Such Product" in out, (rc, out[-300:]))
        rc, out, res = plan_run(e, core, "zorg-growth", "--product", "Zorg App")
        check("a named repository is planned whatever --product says", rc == 0 and res["repo"] == "zorg-growth"
              and set(signs_in(res).values()) == {"="}, (rc, out[-400:]))
        check("plan never wrote anything: not the store, the home, the vault or the core", untouched and all(untouched), untouched)


# --- v3.13.0: ctx provider apply — one pass, your edits kept, one question per conflicting block
SCOPE_04 = "<!-- zorg-core:begin id=scope v=0.4 -->\n### Scope of work\nThe user works on Zorg App only."
SCOPE_05 = "<!-- zorg-core:begin id=scope v=0.5 -->\n### Scope of work\nThe user works on Zorg App and Zorg Lite."
SCOPE_06 = "<!-- zorg-core:begin id=scope v=0.6 -->\n### Scope of work\nThe user works on Zorg App, Zorg Lite and Zorg Max."
OKR = "<!-- zorg-core:begin id=okr v=0.1 -->\n### OKR\n- grow\n<!-- zorg-core:end id=okr -->"
core_untouched = []


def apply_run(e, core, *args):
    """An apply run, with the proof that it wrote nothing into the core folder."""
    before = tree_of(core)
    rc, out, res = run_ok(e, "provider", "apply", *args)
    core_untouched.append(tree_of(core) == before)
    return rc, out, res


def mtimes(*paths):
    """{path: mtime in ns} of the files given and of every file under the folders given."""
    out = {}
    for p in paths:
        for dp, _, fn in os.walk(p) if os.path.isdir(p) else [(os.path.dirname(p), None, [os.path.basename(p)])]:
            for n in fn:
                out[os.path.join(dp, n)] = os.stat(os.path.join(dp, n)).st_mtime_ns
    return out


def region_in(text, ns, bid):
    """The region `bid` of namespace `ns` in `text`, markers included, or None (`id=team` never matches `id=teams`)."""
    m = re.search(r"<!-- %s:begin id=%s[ -].*?<!-- %s:end id=%s -->" % (ns, re.escape(bid), ns, re.escape(bid)), text, re.S)
    return m.group(0) if m else None


def changed_records(before, after):
    return {os.path.basename(p)[:-3] for p in set(before) | set(after) if before.get(p) != after.get(p)}


def snapshot_names(e):
    root = os.path.join(e.home, ".grow-pm", "snapshots")
    return sorted(os.listdir(root)) if os.path.isdir(root) else []


def journal_len(e):
    return len(read(e.store, ".state", "journal.jsonl").splitlines())


with FakeMcp(tree={GROWTH_PATH: GROWTH_TEXT}) as fake:
    with tempfile.TemporaryDirectory() as d:
        e = repos_env(d, fake.url, core_extra=SKIP_PRODUCT)
        core = os.path.join(d, "ZorgCore")
        blocks_file, card = os.path.join(core, CORE_BLOCKS), os.path.join(core, CORE_CARD)
        records_dir, blocks_dir = os.path.join(e.store, "records"), os.path.join(e.store, ".state", "blocks")
        rc, out, r = apply_run(e, core, "zorg-core")
        check("apply without a store: exit 3, nothing created", rc == 3 and "no store" in out and not os.path.exists(e.store), (rc, out[-300:]))
        run_ok(e, "migrate", "--apply")
        run_ok(e, "provider", "adopt", "zorg-core", "--apply")
        run_ok(e, "provider", "adopt", "zorg-growth", "--apply")

        before_m, ctx_before, mirror_before = mtimes(records_dir, e.ctx, e.mirror), read(e.ctx), read(e.mirror)
        n_journal, snaps, checked_before = journal_len(e), snapshot_names(e), block_state(e, "zorg-core")["checked"]
        time.sleep(1.1)                                 # the time of the check is to the second
        rc, out, r = apply_run(e, core, "zorg-core")
        check("criterion 2: no change → 0 record writes, 0 questions", rc == 0 and mtimes(records_dir, e.ctx, e.mirror) == before_m
              and read(e.ctx) == ctx_before and read(e.mirror) == mirror_before and "без змін" in out and r["pending"] == [], (rc, out[-500:]))
        check("…no snapshot, no journal line; only the time of the check moves", journal_len(e) == n_journal and snapshot_names(e) == snaps
              and r["snapshot"] is None and r["written"] == [] and block_state(e, "zorg-core")["checked"] != checked_before, r)
        check("…the output is the header and one line", [l for l in out.splitlines() if not l.startswith("CTX_RESULT")]
              == ["zorg-core · джерело: тека · ядро v0.4 · база v0.4", "без змін"], out)

        ctx_before_apply, bases_before, recs_before = read(e.ctx), tree_of(blocks_dir), tree_of(records_dir)
        growth_region_before = {b: region_in(read(e.ctx), "zorg-growth", b) for b in ("growth-metrics", "team")}
        change(blocks_file, SCOPE_04, SCOPE_05)
        rc, out, r = apply_run(e, core, "zorg-core")
        changed_hosts = changed_records(recs_before, tree_of(records_dir))
        check("criterion 3: core changed one block → only its host changes", rc == 0 and changed_hosts == {"custom.zorg-core-notes"}
              and last_journal(e)["op"] == "provider-apply" and last_journal(e)["decisions"]["scope"] == "~", (rc, changed_hosts, out[-500:]))
        check("…the new text is in both copies; one journal line names the repository, the versions and the record",
              SCOPE_05 in read(e.ctx) and SCOPE_05 in read(e.mirror) and journal_len(e) == n_journal + 1
              and last_journal(e)["source"] == "repo:zorg-core" and last_journal(e)["ids"] == ["custom.zorg-core-notes"]
              and last_journal(e)["from_v"] == "0.4" and "to_v" in last_journal(e), last_journal(e))
        check("…the data: what was applied, nothing waits, the snapshot", r["applied"]["scope"] == "~" and r["pending"] == []
              and r["written"] == ["custom.zorg-core-notes"] and os.path.isdir(r["snapshot"]) and r["rows"], r)
        rc_p, out_p, r_p = run_ok(e, "provider", "plan", "zorg-core")
        signs_final = signs_in(r_p)
        check("idempotent: plan after apply is all =", set(signs_final.values()) == {"="}, out_p[-400:])
        growth_region_after = {b: region_in(read(e.ctx), "zorg-growth", b) for b in ("growth-metrics", "team")}
        check("criterion 8: two repos, one product — growth untouched by core apply", growth_region_before == growth_region_after
              and all(growth_region_after.values()) and set(signs_in(run_ok(e, "provider", "plan", "zorg-growth")[2]).values()) == {"="},
              growth_region_after)
        rc, out, r = apply_run(e, core, "zorg-core", "--choose", "scope=theirs")
        check("a --choose for a block that needs no decision is ignored, and said so", rc == 0 and "scope" in out and "не потрібне" in out
              and r["ignored"] == {"scope": "="} and "без змін" not in [l for l in out.splitlines()][:1], (rc, out[-300:]))

        rc, out, r = run_ok(e, "undo")
        check("criterion 9: undo returns records, copies and bases", rc == 0 and read(e.ctx) == ctx_before_apply
              and read(e.mirror) == ctx_before_apply and tree_of(blocks_dir) == bases_before, (rc, out[-300:]))
        check("criterion 9: …and the records, byte for byte — an undo that rebuilds from records finds nothing to put back",
              tree_of(records_dir) == recs_before and r.get("records_reverted") == [], (rc, r))

        change(blocks_file, SCOPE_05, SCOPE_06)         # the core moved on again; you never took 0.5
        rc, out, r = apply_run(e, core, "zorg-core")
        check("criterion 5: skipped releases, no edits → no question", rc == 0 and r["applied"]["scope"] == "~" and r["pending"] == []
              and SCOPE_06 in read(e.ctx) and "v0.4 → v0.6" in out, (rc, out[-500:]))

        growth_team_before = region_in(read(e.ctx), "zorg-growth", "team")
        change(card, 'head: "Alex One"', 'head: "Alex Prime"')
        edit_both(e, "- **jira_team_field:** Alpha\n", "- **jira_team_field:** Alpha (mine)\n")
        rc, out, r = apply_run(e, core, "zorg-core")
        team_now = region_in(read(e.ctx), "zorg-core", "team")
        check("criterion 4: both changed → exactly one question, exit 2", rc == 2 and r["pending"] == ["team"] and r["ok"] is False
              and "Ядро тепер каже: " in out and "Alex Prime" in out and "--choose team=theirs|mine|both" in out, (rc, out[-700:]))
        check("…the block in question is not touched", "Alex One" in team_now and "Alpha (mine)" in team_now, team_now)
        rc, out, r = apply_run(e, core, "zorg-core", "--choose", "team=mine")
        base_team = read(blocks_dir, "zorg-core", block_state(e, "zorg-core")["blocks"]["team"]["base_sha"] + ".md")
        check("criterion 4: --choose team=mine applies in the same pass", rc == 0 and "Alpha (mine)" in read(e.ctx)
              and "Alex Prime" in base_team and "Alex Prime" not in read(e.ctx) and last_journal(e)["decisions"]["team"] == "⚠ mine", (rc, out[-500:]))
        rc, out, r = run_ok(e, "provider", "plan", "zorg-core")
        signs_after = signs_in(r)
        check("keep mine is not asked again", signs_after["team"] == "✎" and r["questions"] == 0, out[-400:])
        growth_team_after = region_in(read(e.ctx), "zorg-growth", "team")
        check("same block id in two repos: core apply leaves zorg-growth:team as is", growth_team_before == growth_team_after
              and growth_team_after is not None, growth_team_after)

        ctx_pre_okr = read(e.ctx)
        open(blocks_file, "a", encoding="utf-8").write("\n" + OKR + "\n")
        rc, out, r = apply_run(e, core, "zorg-core")
        check("a new block waits for --add: exit 2, nothing added", rc == 2 and r["pending"] == ["okr"] and "--add okr" in out
              and "id=okr" not in read(e.ctx), (rc, out[-400:]))
        rc, out, r = apply_run(e, core, "zorg-core", "--add", "okr")
        check("+ goes to home_record", "<!-- zorg-core:begin id=okr " in e.record("custom.zorg-core-notes") and rc == 0
              and OKR in read(e.ctx) and r["applied"]["okr"] == "+", (rc, out[-400:]))
        change(blocks_file, "\n" + OKR + "\n", "")
        rc, out, r = apply_run(e, core, "zorg-core")
        check("− removes the region, and the record is as it was before the block came", rc == 0 and r["applied"]["okr"] == "−"
              and read(e.ctx) == ctx_pre_okr and "okr" not in block_state(e, "zorg-core")["blocks"], (rc, out[-400:]))

        teams_region = region_in(read(e.ctx), "zorg-core", "teams")
        edit_both(e, teams_region + "\n\n", "")
        rc_cut, out_cut, r_cut = apply_run(e, core, "zorg-core")
        signs_after_cut = signs_in(run_ok(e, "provider", "plan", "zorg-core")[2])
        check("✂ you removed a block — not offered again", signs_after_cut["teams"] == "✂" and rc_cut == 0
              and r_cut["applied"]["teams"] == "✂" and "id=teams" not in read(e.ctx)
              and block_state(e, "zorg-core")["blocks"]["teams"]["user_removed"] == time.strftime("%Y-%m-%d"), (rc_cut, out_cut[-400:]))
        rc, out, r = apply_run(e, core, "zorg-core")
        check("…the next pass asks nothing and changes nothing", rc == 0 and "без змін" in out and r["pending"] == [], (rc, out[-300:]))

        everything = tree_of(e.home, e.vault, core)
        rc, out, r = run_ok(e, "provider", "apply", "zorg-core", "--choose", "team=maybe")
        check("--choose takes theirs|mine|both: anything else is exit 3, nothing written", rc == 3 and tree_of(e.home, e.vault, core) == everything,
              (rc, out[-300:]))
        rc, out, r = run_ok(e, "provider", "apply", "zorg-core", "--choose", "nosuch=mine")
        check("--choose of a block the plan does not have: exit 3, nothing written", rc == 3 and "nosuch" in out
              and tree_of(e.home, e.vault, core) == everything, (rc, out[-300:]))
        rc, out, r = run_ok(e, "provider", "apply", "--choose", "team=mine")
        check("--choose without a repository while several are in scope: exit 3", rc == 3 and tree_of(e.home, e.vault, core) == everything,
              (rc, out[-300:]))
        rc, out, r = run_ok(e, "provider", "apply", "zorg-dead")
        check("an unreachable repository: exit 5, nothing written", rc == 5 and "недоступний" in out and r["ok"] is False
              and tree_of(e.home, e.vault, core) == everything, (rc, out[-300:]))
        rc, out, r = run_ok(e, "provider", "apply")
        check("no repository named and one of them unreachable: exit 5 before anything is written", rc == 5 and "zorg-dead" in out
              and "нічого не записано" in out and tree_of(e.home, e.vault, core) == everything, (rc, out[-400:]))
        rc, out, r = run_ok(e, "provider", "apply", "zorg-core", "--store", e.store)
        check("--store is refused: apply always writes", rc == 3 and "--store is for read commands only" in out, (rc, out[-300:]))

        with open(os.path.join(e.home, ".grow-pm", "providers", "zorg-dead.yaml"), "a", encoding="utf-8") as f:
            f.write("status: paused\n")
        rc, out, r = run_ok(e, "provider", "plan")
        check("a paused repository is left out of plan when none is named, with one line", rc == 0 and "призупинено: zorg-dead" in out
              and "zorg-dead · недоступний" not in out and r["paused"] == ["zorg-dead"]
              and [x["repo"] for x in r["repos"]] == ["zorg-core", "zorg-growth"], (rc, out[-500:]))
        rc, out, r = apply_run(e, core)
        check("…and out of apply: the others are applied", rc == 0 and "призупинено: zorg-dead" in out and r["paused"] == ["zorg-dead"]
              and [x["repo"] for x in r["repos"]] == ["zorg-core", "zorg-growth"], (rc, out[-500:]))
        rc, out, r = run_ok(e, "provider", "plan", "zorg-dead")
        check("…a paused repository named explicitly still works", rc == 5 and "недоступний" in out, (rc, out[-300:]))

    with tempfile.TemporaryDirectory() as d:            # a section wrapper; both texts kept
        e = repos_env(d, fake.url, core_extra=SKIP_PRODUCT, patch=[
            ("## Zorg Core Notes\n\n", "## Zorg Core Notes\n\n<!-- zorg-core:section:begin -->\n"),
            ("<!-- zorg-core:end id=teams -->\n", "<!-- zorg-core:end id=teams -->\n<!-- zorg-core:section:end -->\n")])
        core = os.path.join(d, "ZorgCore")
        blocks_file = os.path.join(core, CORE_BLOCKS)
        run_ok(e, "migrate", "--apply")
        run_ok(e, "provider", "adopt", "zorg-core", "--apply")
        change(blocks_file, SCOPE_04, SCOPE_05)
        rc, out, r = apply_run(e, core, "zorg-core")
        body_w = e.record("custom.zorg-core-notes")
        check("a block inside a section wrapper is replaced in place", "<!-- zorg-core:section:begin -->" in body_w
              and body_w.index("<!-- zorg-core:begin id=scope ") > body_w.index("<!-- zorg-core:section:begin -->")
              and rc == 0 and SCOPE_05 in body_w and body_w.index("<!-- zorg-core:end id=teams -->") < body_w.index("<!-- zorg-core:section:end -->"),
              (rc, body_w[-500:]))
        open(blocks_file, "a", encoding="utf-8").write("\n" + OKR + "\n")
        rc, out, r = apply_run(e, core, "zorg-core", "--add", "okr")
        body_w = e.record("custom.zorg-core-notes")
        check("+ goes inside the wrapper of its home record", rc == 0
              and body_w.index("<!-- zorg-core:end id=teams -->") < body_w.index("id=okr") < body_w.index("<!-- zorg-core:section:end -->"),
              (rc, body_w[-400:]))
        edit_both(e, "The user works on Zorg App and Zorg Lite.", "The user works on Zorg App and Zorg Lite (and my notes).")
        change(blocks_file, SCOPE_05, SCOPE_06)
        rc, out, r = apply_run(e, core, "zorg-core", "--choose", "scope=both")
        body = e.record("custom.zorg-core-notes")
        check("both keeps the two texts marked", "<!-- ctx:both theirs -->" in body and "<!-- ctx:both mine -->" in body
              and rc == 0 and body.count("<!-- zorg-core:begin id=scope ") == 1 and "<!-- zorg-core:begin id=scope v=0.6 -->" in body
              and body.index("Zorg Lite and Zorg Max") < body.index("<!-- ctx:both mine -->") < body.index("(and my notes)"), (rc, body[-600:]))
        rc, out, r = run_ok(e, "provider", "plan", "zorg-core")
        check("…one region, the repository's markers: the next plan keeps it as your edit", rc == 0 and signs_in(r)["scope"] == "✎", out[-400:])
        rc, out, r = run_ok(e, "status")
        check("…and the copies apply wrote read back as the records: nothing waits to be imported", rc == 0
              and "to import: nothing — in sync" in out and r["conflicts"] == [], out[-400:])

    with tempfile.TemporaryDirectory() as d:            # a broken marker
        e = repos_env(d, fake.url, core_extra=SKIP_PRODUCT, patch=[("<!-- zorg-core:end id=teams -->", "<!-- zorg-core:end id=teams x -->")])
        core = os.path.join(d, "ZorgCore")
        blocks_file = os.path.join(core, CORE_BLOCKS)
        run_ok(e, "migrate", "--apply")
        run_ok(e, "provider", "adopt", "zorg-core", "--apply")
        ctx_b = read(e.ctx)
        rc, out, r = apply_run(e, core, "zorg-core")
        check("a broken marker and nothing else to do: exit 4, nothing written", rc == 4 and "помилка: teams — broken marker" in out
              and read(e.ctx) == ctx_b and r["snapshot"] is None, (rc, out[-400:]))
        change(blocks_file, SCOPE_04, SCOPE_05)
        rc_b, out_b, r_b = apply_run(e, core, "zorg-core")
        check("a broken marker refuses that block, the rest applies", (rc_b == 4 or (rc_b in (0, 2) and "scope" in r_b["applied"]))
              and any(x["block"] == "teams" and x["why"] == "broken marker" for x in r_b["errors"]), (rc_b, out_b[-400:]))
        check("…here the rest is a change: exit 0, the block applied, the broken one as it was", rc_b == 0 and r_b["applied"]["scope"] == "~"
              and SCOPE_05 in read(e.ctx) and "<!-- zorg-core:end id=teams x -->" in read(e.ctx), (rc_b, out_b[-400:]))

    with tempfile.TemporaryDirectory() as d:            # a repository whose blocks you never had, and no home record
        gm, gt = region_in(GROWTH_TEXT, "zorg-growth", "growth-metrics"), region_in(GROWTH_TEXT, "zorg-growth", "team")
        e = repos_env(d, fake.url, core_extra=SKIP_PRODUCT, patch=[(gm + "\n\n", ""), (gt + "\n\n", "")])
        with open(os.path.join(e.home, ".grow-pm", "providers", "zorg-growth.yaml"), "a", encoding="utf-8") as f:
            f.write("title: Zorg Growth\n")
        core = os.path.join(d, "ZorgCore")
        rec_path = lambda rid: os.path.join(e.store, "records", rid + ".md")
        run_ok(e, "migrate", "--apply")
        rc, out, r = apply_run(e, core, "zorg-growth")
        check("blocks you never had wait for --add", rc == 2 and r["pending"] == ["growth-metrics", "team"], (rc, out[-400:]))
        rc, out, r = apply_run(e, core, "zorg-growth", "--add", "growth-metrics", "--add", "team")
        check("+ without home_record creates the repo's custom record", os.path.isfile(rec_path("custom.zorg-growth")) and rc == 0
              and "\n## Zorg Growth\n\n" + gm + "\n\n" + gt + "\n" in read(e.ctx) and read(e.ctx).rstrip("\n").endswith(gt), (rc, read(e.ctx)[-400:]))
        rc, out, r = run_ok(e, "provider", "plan", "zorg-growth")
        check("…the next plan is all '='", rc == 0 and set(signs_in(r).values()) == {"="}, out[-400:])
        rc, out, r = run_ok(e, "status")
        check("…the new record reads back from the copies as it was written: nothing waits to be imported", rc == 0
              and "to import: nothing — in sync" in out and r["conflicts"] == [], out[-400:])

CORE_BLOCKS_PATH = "ZorgCore/" + "Core/_System/context-blocks.md"          # endpoint.root + blocks_file of a v2 zorg-core

with FakeMcp(tree={CORE_BLOCKS_PATH: read(CORE_FIX, CORE_BLOCKS)}) as fake:
    with tempfile.TemporaryDirectory() as d:            # the blocks from MCP, the team block from a core folder that is not here
        e = Env(d, fixture="context", fix=REPOS_FIX)
        core = os.path.join(d, "ZorgCore")
        shutil.copytree(CORE_FIX, core)
        prov = os.path.join(e.home, ".grow-pm", "providers")
        os.makedirs(prov)
        open(os.path.join(prov, "zorg-core.yaml"), "w", encoding="utf-8").write(
            "schema: provider-registration/2\nid: zorg-core\nkind: mcp\nauthority: org\nendpoint:\n  url: %s\n  root: \"ZorgCore/\"\n"
            "blocks_file: Core/_System/context-blocks.md\nblocks_source: auto\ncore_root: %s\nteam: team-alpha\nrole: pm\n"
            "jira_write: own\n%s" % (fake.url, core, SKIP_PRODUCT))
        run_ok(e, "migrate", "--apply")
        run_ok(e, "provider", "adopt", "zorg-core", "--apply")
        rc, out, r = apply_run(e, core, "zorg-core")
        check("an MCP repository with its core folder: nothing moved, 'без змін'", rc == 0 and "без змін" in out, (rc, out[-300:]))
        os.rename(core, core + ".away")                 # the core folder is not on this machine now; the server still answers
        team_before = region_in(read(e.ctx), "zorg-core", "team")
        rc, out, r = apply_run(e, core + ".away", "zorg-core")
        check("the core folder gone and MCP up: the team block is unavailable ('·'), never removed",
              rc == 0 and region_in(read(e.ctx), "zorg-core", "team") == team_before and team_before is not None
              and signs_in(r).get("team") == "·" and "team" not in r["applied"], (rc, out[-500:]))
        shown = [l for l in out.splitlines() if not l.startswith("CTX_RESULT")]
        check("…and the text says so under 'без змін': the team block was not checked", "без змін" in shown
              and any(l.startswith("·") and "team" in l and "core folder not found" in l for l in shown), shown)

with FakeMcp(tree={GROWTH_PATH: GROWTH_TEXT}) as fake:
    with tempfile.TemporaryDirectory() as d:            # the repository removed a block you edited
        e = repos_env(d, fake.url, core_extra=SKIP_PRODUCT)
        core = os.path.join(d, "ZorgCore")
        blocks_file = os.path.join(core, CORE_BLOCKS)
        run_ok(e, "migrate", "--apply")
        run_ok(e, "provider", "adopt", "zorg-core", "--apply")
        edit_both(e, "- Alpha, Beta\n", "- Alpha, Beta\n- my own note on Gamma\n")
        change(blocks_file, "\n" + region_in(read(blocks_file), "zorg-core", "teams") + "\n", "")
        rc, out, r = apply_run(e, core, "zorg-core")
        check("the repository removed a block you edited: a question, exit 2, your text as it is",
              rc == 2 and r["pending"] == ["teams"] and "my own note on Gamma" in read(e.ctx) and "--choose teams=theirs|mine" in out
              and "--choose teams=theirs|mine|both" not in out and "theirs прибере, mine лишить текст як ваш" in out, (rc, out[-500:]))
        rc, out, r = apply_run(e, core, "zorg-core", "--choose", "teams=both")
        check("…both is no answer for a removed block: exit 3", rc == 3 and "both" in out and "id=teams" in read(e.ctx), (rc, out[-300:]))
        rc, out, r = apply_run(e, core, "zorg-core", "--choose", "teams=mine")
        check("…mine keeps your text in place without the markers", rc == 0 and "zorg-core:begin id=teams" not in read(e.ctx)
              and "### Teams map\n- Alpha, Beta\n- my own note on Gamma\n" in read(e.ctx), (rc, out[-400:]))
        rc, out, r = run_ok(e, "provider", "plan", "zorg-core")
        check("…and the next plan has no row for it", rc == 0 and "teams" not in signs_in(r) and r["questions"] == 0, out[-400:])

    with tempfile.TemporaryDirectory() as d:            # the core's provider manifest is not there (iCloud evicted it)
        e = repos_env(d, fake.url, core_extra=SKIP_PRODUCT)
        core = os.path.join(d, "ZorgCore")
        run_ok(e, "migrate", "--apply")
        run_ok(e, "provider", "adopt", "zorg-core", "--apply")
        rc, out, r = apply_run(e, core, "zorg-core")
        sysdir = os.path.join(core, "Core", "_System")
        os.rename(os.path.join(sysdir, "provider-manifest.yaml"), os.path.join(sysdir, ".provider-manifest.yaml.icloud"))
        team_before = region_in(read(e.ctx), "zorg-core", "team")
        before = tree_of(e.home, e.vault)
        rc, out, r = apply_run(e, core, "zorg-core")
        check("…a registration that takes its blocks_file from that manifest: unreachable, exit 5, nothing written",
              rc == 5 and tree_of(e.home, e.vault) == before, (rc, out[-300:]))
        with open(os.path.join(e.home, ".grow-pm", "providers", "zorg-core.yaml"), "a", encoding="utf-8") as f:
            f.write("blocks_file: Core/_System/context-blocks.md\n")
        rc, out, r = apply_run(e, core, "zorg-core")
        check("the core's provider manifest evicted: apply exits 0, the team region byte-identical, its row '·'",
              rc == 0 and team_before is not None and region_in(read(e.ctx), "zorg-core", "team") == team_before
              and signs_in(r).get("team") == "·" and "team" not in r["applied"]
              and any(l.startswith("·") and "provider manifest" in l for l in out.splitlines()), (rc, out[-500:]))

    with tempfile.TemporaryDirectory() as d:            # one people card of the core evicted by iCloud
        e = repos_env(d, fake.url, core_extra=SKIP_PRODUCT)
        core = os.path.join(d, "ZorgCore")
        run_ok(e, "migrate", "--apply")
        run_ok(e, "provider", "adopt", "zorg-core", "--apply")
        rc, out, r = apply_run(e, core, "zorg-core")
        people = os.path.join(core, "Core", "People")
        os.rename(os.path.join(people, "a-one.md"), os.path.join(people, ".a-one.md.icloud"))
        team_before = region_in(read(e.ctx), "zorg-core", "team")
        rc, out, r = apply_run(e, core, "zorg-core")
        check("a people card evicted by iCloud: apply exits 0, the team region byte-identical, its row '·' — never a degraded update",
              rc == 0 and team_before is not None and region_in(read(e.ctx), "zorg-core", "team") == team_before
              and signs_in(r).get("team") == "·" and "team" not in r["applied"]
              and any(l.startswith("·") and "1 file not downloaded" in l for l in out.splitlines()), (rc, out[-500:]))

check("apply never writes into the core folder", core_untouched and all(core_untouched), core_untouched)


# --- v3.13.0 Task 9: ctx read says where a block comes from; the card lists the repositories
with FakeMcp(tree={GROWTH_PATH: GROWTH_TEXT}) as fake:
    with tempfile.TemporaryDirectory() as d:
        e = repos_env(d, fake.url, core_extra=SKIP_PRODUCT)
        core = os.path.join(d, "ZorgCore")
        run_ok(e, "migrate", "--apply")
        card_of = lambda: read(e.store, "INDEX.md")
        check("before any check the card still says how many blocks each repository put in (a registered repository with none is left out)",
              "- **Repos:** zorg-core: 3 блоки; zorg-growth: 2 блоки\n" in card_of(), card_of()[:600])
        run_ok(e, "provider", "adopt", "zorg-core", "--apply")
        day = block_state(e, "zorg-core")["checked"][:10]
        check("adopt --apply puts the check on the card: no compile follows an adopt, so the card is refreshed",
              "- **Repos:** zorg-core: 3 блоки · v0.4 · перевірено %s; zorg-growth: 2 блоки\n" % day in card_of(), card_of()[:600])
        run_ok(e, "provider", "adopt", "zorg-growth", "--apply")
        line = "- **Repos:** zorg-core: 3 блоки · v0.4 · перевірено %s; zorg-growth: 2 блоки · v0.1 · перевірено %s\n" % (day, day)
        check("…each repository once, with the version most of its blocks have a base at", line in card_of() and card_of().count("**Repos:**") == 1
              and "Alpha (A) — 2 members" in card_of(), card_of()[:900])
        rc, out, res = run_ok(e, "card")
        check("ctx card says the same", rc == 0 and line in card_of(), card_of()[:900])
        mtime = os.stat(os.path.join(e.store, "INDEX.md")).st_mtime_ns
        time.sleep(1.1)
        rc, out, r = run_ok(e, "provider", "apply", "zorg-core")
        check("an apply that changes nothing leaves the card alone: the line has not moved", rc == 0 and "без змін" in out
              and os.stat(os.path.join(e.store, "INDEX.md")).st_mtime_ns == mtime, (rc, out[-300:]))
        state_path = os.path.join(e.store, ".state", "blocks", "zorg-core.json")
        good_state = read(state_path)
        hand = json.loads(good_state)
        hand["blocks"]["scope"]["v"] = ["x"]                            # a hand-edited state: a version that is a list
        open(state_path, "w", encoding="utf-8").write(json.dumps(hand))
        rc, out, res = run_ok(e, "card")
        check("a state with a version that is not text: ctx card still builds, and still lists the repository",
              rc == 0 and "zorg-core: 3 блоки" in card_of(), (rc, out[-300:], card_of()[:600]))
        open(state_path, "w", encoding="utf-8").write(good_state)
        run_ok(e, "card")
        rc, out, res = run_ok(e, "read", "--skill", "hiring-designer")
        check("ctx read puts the repository, the version and the day of the check before a block",
              rc == 0 and "> [zorg-core · v0.2 · станом на %s]\n#### Members" % day in out, (rc, out[-600:]))
        check("…and carries the card with the repositories", line in out, out[:900])

# --- v3.13.0 Task 9 fix: a card that cannot be refreshed costs one line, never the report or the exit code of the command
import contextlib, io  # noqa: E402

sys.path.insert(0, os.path.join(ROOT, "scripts"))
import ctx as ctx_cli  # noqa: E402
import ctx_ops as ctx_ops_mod  # noqa: E402


def in_process(e, *args):
    """A `ctx` run in this process (so a function can be replaced): (exit code, output, CTX_RESULT)."""
    saved = os.environ.pop("GROW_PM_CONTEXT_PATH", None)
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            rc = ctx_cli.main(list(args) + ["--home", e.home, "--context", e.ctx])
    finally:
        if saved is not None:
            os.environ["GROW_PM_CONTEXT_PATH"] = saved
    out = buf.getvalue()
    last = [l for l in out.splitlines() if l.startswith("CTX_RESULT ")]
    return rc, out, json.loads(last[-1][len("CTX_RESULT "):]) if last else None


def refresh_fails(reason):
    def boom(*a, **k):
        raise cs_mod.StoreError(reason)
    return boom


import ctx_store as cs_mod  # noqa: E402

with FakeMcp(tree={GROWTH_PATH: GROWTH_TEXT}) as fake:
    with tempfile.TemporaryDirectory() as d:
        e = repos_env(d, fake.url, core_extra=SKIP_PRODUCT)
        core = os.path.join(d, "ZorgCore")
        blocks_file = os.path.join(core, CORE_BLOCKS)
        run_ok(e, "migrate", "--apply")
        real = ctx_ops_mod.refresh_card_repos
        ctx_ops_mod.refresh_card_repos = refresh_fails("INDEX.md is not available locally (read timeout)")
        try:
            rc, out, res = in_process(e, "provider", "adopt", "zorg-core", "--apply")
        finally:
            ctx_ops_mod.refresh_card_repos = real
        check("adopt: a card that cannot be refreshed is one line; the adopt, its report and its exit code stand",
              rc == 0 and res is not None and res["ok"] is True and res["written"] is True and "adopted 3 block(s)" in out
              and "card not refreshed: INDEX.md is not available locally (read timeout)" in out.splitlines()
              and block_state(e, "zorg-core") is not None, (rc, out[-500:]))
        ctx_ops_mod.refresh_card_repos = refresh_fails("INDEX.md is not available locally (read timeout)")
        try:
            rc, out, res = in_process(e, "provider", "apply", "zorg-core")
            quiet = (rc, out, res)
            change(blocks_file, SCOPE_04, SCOPE_05)
            rc, out, res = in_process(e, "provider", "apply", "zorg-core")
        finally:
            ctx_ops_mod.refresh_card_repos = real
        check("apply with nothing to do: 'без змін' and exit 0 stay, with the one line about the card",
              quiet[0] == 0 and "без змін" in quiet[1] and "card not refreshed: INDEX.md" in quiet[1] and quiet[2]["ok"] is True, quiet[:2])
        check("apply that wrote records: the report, the exit code and the result are kept, the card line comes after the report",
              rc == 0 and res is not None and res["ok"] is True and res["changes"] == 1 and "записано: custom.zorg-core-notes" in out
              and SCOPE_05 in read(e.ctx) and out.index("записано:") < out.index("card not refreshed:"), (rc, out[-600:]))
        change(blocks_file, SCOPE_05, SCOPE_04.replace("v=0.4", "v=0.6"))
        ctx_ops_mod.refresh_card_repos = refresh_fails("odd")
        try:
            rc, out, res = in_process(e, "provider", "apply", "zorg-core", "--choose", "nosuch=mine")
        finally:
            ctx_ops_mod.refresh_card_repos = real
        check("…and a refused command is still refused: the card line does not turn exit 3 into anything else",
              rc == 3 and "nosuch" in out and "card not refreshed" not in out, (rc, out[-300:]))

# --- v3.13.0 Task 11: a registration without a namespace takes the core manifest's
NS_WARNING = "registration has no namespace \u2014 the core's manifest says zorg-core; add `namespace: zorg-core`"


def shown(out):
    """The text of a run, without its CTX_RESULT line."""
    return out.split("CTX_RESULT")[0]


def renamed_core(d, rid, extra=""):
    """repos_env with the core's v1 registration under another id (a v1 registration names no namespace, so the id would
    stand in for it); the markers in the context and in the core's blocks file stay `zorg-core`."""
    e = repos_env(d, "http://127.0.0.1:9/mcp", core_extra=SKIP_PRODUCT + extra)
    prov = os.path.join(e.home, ".grow-pm", "providers")
    old = os.path.join(prov, "zorg-core.yaml")
    text = read(old).replace("id: zorg-core", "id: " + rid)
    os.remove(old)
    os.remove(os.path.join(prov, "zorg-growth.yaml"))
    os.remove(os.path.join(prov, "zorg-dead.yaml"))
    open(os.path.join(prov, rid + ".yaml"), "w", encoding="utf-8").write(text)
    return e


with tempfile.TemporaryDirectory() as d:
    e = renamed_core(d, "zorg-context")
    core = os.path.join(d, "ZorgCore")
    blocks_file = os.path.join(core, CORE_BLOCKS)
    run_ok(e, "migrate", "--apply")
    rc, out, res = run_ok(e, "repo", "list")
    check("repo list: one warning for a registration with no namespace whose core says another",
          rc == 0 and shown(out).count(NS_WARNING) == 1 and res["repos"][0].get("namespace_warning") == NS_WARNING, (rc, out[-500:]))
    rc, out, res = run_ok(e, "repo", "status", "zorg-context")
    check("repo status: the same warning, and the version on the source is read in the core's namespace",
          rc == 0 and shown(out).count(NS_WARNING) == 1 and res["repos"][0]["source_version"] == "0.4"
          and res["repos"][0].get("namespace_warning") == NS_WARNING, (rc, out[-500:]))
    rc, out, res = run_ok(e, "provider", "adopt", "zorg-context")
    check("adopt (dry run) sees the three blocks of the core's namespace in your context",
          rc == 0 and res["blocks"] == {"scope": "base", "teams": "base", "team": "base"} and res["new"] == []
          and "block(s) of zorg-core in your context" in out, (rc, out[-500:], res))
    rc, out, res = run_ok(e, "provider", "adopt", "zorg-context", "--apply")
    st = block_state(e, "zorg-context")
    check("adopt --apply records the bases under the registration's id", rc == 0 and res["written"] is True
          and st is not None and set(st["blocks"]) == {"scope", "teams", "team"}, (rc, out[-400:], st))
    rc, out, res = run_ok(e, "provider", "plan", "zorg-context")
    check("plan: the blocks are found and nothing moved ('='); the warning follows the table",
          rc == 0 and set(signs_in(res).values()) == {"="} and set(signs_in(res)) == {"scope", "teams", "team"}
          and shown(out).count(NS_WARNING) == 1 and res.get("namespace_warning") == NS_WARNING
          and "warning: " + NS_WARNING in out.splitlines() and "Питань: 0 \u00b7 зміниться записів: 0" in out.splitlines()
          and out.splitlines().index("warning: " + NS_WARNING) > out.splitlines().index("Питань: 0 \u00b7 зміниться записів: 0"), (rc, out[-600:]))
    change(blocks_file, SCOPE_04, SCOPE_05)
    rc, out, res = run_ok(e, "provider", "plan", "zorg-context")
    check("the core changed a block you did not touch → '~'", signs_in(res).get("scope") == "~" and res["changes"] == 1, (rc, out[-400:]))
    rc, out, res = run_ok(e, "provider", "apply", "zorg-context")
    check("apply writes it into your records, in the core's namespace", rc == 0 and res["written"] == ["custom.zorg-core-notes"]
          and SCOPE_05 in read(e.ctx) and NS_WARNING not in shown(out), (rc, out[-500:]))
    rc, out, res = run_ok(e, "provider", "plan", "zorg-context")
    check("…and the next plan is all '='", rc == 0 and set(signs_in(res).values()) == {"="}, (rc, out[-400:]))

for label, extra, rid in (("a registration that names its namespace", "namespace: zorg-core\n", "zorg-context"),
                          ("a registration whose id is the core's namespace", "", "zorg-core")):
    with tempfile.TemporaryDirectory() as d:
        e = renamed_core(d, rid, extra)
        run_ok(e, "migrate", "--apply")
        rc, out, res = run_ok(e, "repo", "list")
        rc2, out2, res2 = run_ok(e, "repo", "status", rid)
        rc3, out3, res3 = run_ok(e, "provider", "plan", rid)
        shown = [o.split("CTX_RESULT")[0] for o in (out, out2, out3)]
        check("%s: no warning anywhere, the blocks are found" % label,
              all("namespace" not in s for s in shown) and res["repos"][0].get("namespace_warning", "x") is None
              and res2["repos"][0].get("namespace_warning", "x") is None and res3.get("namespace_warning", "x") is None
              and set(signs_in(res3)) == {"scope", "teams", "team"}, (shown, res3))

with tempfile.TemporaryDirectory() as d:            # an explicit namespace that is not the core's: the repository finds only its own regions
    e = renamed_core(d, "zorg-context", "namespace: zorg-elsewhere\n")
    run_ok(e, "migrate", "--apply")
    rc, out, res = run_ok(e, "provider", "plan", "zorg-context")
    check("an explicit namespace beats the manifest's: the core's scope and teams blocks are not this repository's, and no warning",
          rc == 0 and "scope" not in signs_in(res) and "teams" not in signs_in(res) and "namespace" not in out.split("CTX_RESULT")[0],
          (rc, out[-300:]))

# --- v3.13 Task 12: the protocol documents say what the commands do
def lacks(text, needed):
    return [s for s in needed if s not in text]


cp_flat = re.sub(r"\s+", " ", read(ROOT, "references", "context-protocol.md"))
pp_flat = re.sub(r"\s+", " ", read(ROOT, "references", "context-provider-protocol.md"))
hp_flat = re.sub(r"\s+", " ", read(ROOT, "references", "host-profiles.md"))
need_cp = ["`repo list", "`repo status", "`provider adopt", "`provider plan", "`provider apply", "5 a repository is unreachable",
           "records_reverted", "a record created in Obsidian and imported is not removed", ".state/blocks/",
           "Human edits in a block are kept", "Agent edits are not written", "One snapshot and one journal line per repository",
           "`ctx undo` takes back the last repository's pass only", "a snapshot with no journal line", "`--json` is accepted and changes nothing",
           "> [<repo-id> · v<version> · станом на <date>]", "⚠ конфлікт: файл і запис різняться — ctx sync", "**Repos:**",
           "`provider adopt --apply` does not import first and does not compile"]
check("context-protocol documents repo and provider commands, exit 5, the undo clause, snapshots with .state/blocks, one snapshot per repository",
      not lacks(cp_flat, need_cp), lacks(cp_flat, need_cp))
need_pp = ["provider-registration/2", "## 12. Blocks and merge", "`core_root`", "`namespace`", "`blocks_file`", "`rank`", "`products`",
           "`endpoint.url`", "`endpoint.root`", "`endpoint.headers_env`", "`blocks_source`", "`home_record`", "`skip_blocks`", "`status`",
           "`base`", "`edit`", "`none`", "`has-base`", "`duplicate`", "`broken marker`", "`nested`",
           "| `=` |", "| `~` |", "| `✎` |", "| `⚠` |", "| `+` |", "| `−` |", "| `✂` |", "| `?` |", "| `·` |",
           "| 5 | a repository is unreachable, nothing is written |", "`{repo, error}`", "paused",
           "`vault_get_note`, `vault_list_by_folder`, `vault_search`, `brain_status` and `brain_recent_changes`", "check 17",
           "No redirect is followed", "never goes to the network", "`<!-- ctx:both theirs -->`", "detaches", "no journal line",
           "its own snapshot and journal line"]
check("context-provider-protocol: registration v2 key table, §12 with the first base, signs, exit codes, result shapes, the allow-list",
      not lacks(pp_flat, need_pp), lacks(pp_flat, need_pp))
need_hp = ["Context repositories", "`repo status`", "`vault_get_note`", "never goes to the network"]
check("host-profiles: the network use of ctx and the host without SHELL", not lacks(hp_flat, need_hp), lacks(hp_flat, need_hp))
check("ctx_store.Store documents .state/blocks/", ".state/blocks/" in (cs_mod.Store.__doc__ or ""), cs_mod.Store.__doc__)

check("every command ends with a CTX_RESULT line", contract_ok)
print("RESULT:", "GREEN ✅" if not fails else "RED ❌", "(%d failed)" % fails)
sys.exit(1 if fails else 0)
