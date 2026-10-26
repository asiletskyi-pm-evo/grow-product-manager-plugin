#!/usr/bin/env python3
"""TC-ctx-3110-cli — scripts/ctx.py, the context store's command line (since v3.11.0).

Every command end to end on a temp HOME (the fictional typical context) and a temp vault with
its mirror: the output contract (`CTX_RESULT {json}` last, `CTX_CONFLICT` before it), the exit
codes (0 ok, 2 conflict, 3 bad input / no store / unreadable, 4 refused) and the safety rules
(import before write, snapshot, lock, managed regions, the provider boundary).
Semantics: references/context-protocol.md. Stdlib only; run from the repo root.
"""
import datetime, hashlib, json, os, re, shutil, stat, subprocess, sys, tempfile, time

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
          and r2.get("records_reverted") == [] and r2.get("records_not_reverted") == [] and in_sync(e), (rc, out[-400:], r2))

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

with tempfile.TemporaryDirectory() as d:        # v3.13.1: a record edited in its file AND the copies edited too: nothing to put back, and undo says so
    e = Env(d)
    run_ok(e, "migrate", "--apply")
    rid = "product.zorg-app"
    e.edit(os.path.join(e.store, "records", rid + ".md"), "- **Jira Project Key:** PROJ", "- **Jira Project Key:** REC")
    e.edit(e.ctx, "- **Jira Project Key:** PROJ", "- **Jira Project Key:** FILE")
    e.edit(e.mirror, "- **Jira Project Key:** PROJ", "- **Jira Project Key:** FILE")   # since v3.14 the mirror is asked too
    rc_s, out_s, _ = run_ok(e, "sync", "--resolve", rid + "=record")
    rc, out, res = run_ok(e, "undo")
    check("undo names what it could not put back", rc == 0 and rc_s == 0
          and "not put back (no matching text in local-context.md): %s — check them: ctx get <id>" % rid in out
          and res.get("records_not_reverted") == [rid], (rc_s, rc, out[-500:], res))
    check("…and an undo that put every record back says nothing of the kind",
          run_ok(e, "undo")[2].get("records_not_reverted") == [], "")

with tempfile.TemporaryDirectory() as d:        # v3.14.0 Task 9: only copy 0 edited — the vault mirror still holds the section
    e = Env(d)
    run_ok(e, "migrate", "--apply")
    rid = "product.zorg-app"
    e.edit(os.path.join(e.store, "records", rid + ".md"), "- **Jira Project Key:** PROJ", "- **Jira Project Key:** REC")
    e.edit(e.ctx, "- **Jira Project Key:** PROJ", "- **Jira Project Key:** FILE")
    rc_s, out_s, _ = run_ok(e, "sync", "--resolve", rid + "=record")
    rc, out, res = run_ok(e, "undo")
    check("undo puts the record back from the mirror's section when copy 0 no longer holds it",
          rc == 0 and rc_s == 0 and res.get("records_reverted") == [rid] and res.get("records_not_reverted") == []
          and "- **Jira Project Key:** PROJ" in e.record(rid) and "- **Jira Project Key:** PROJ" in read(e.ctx), (rc_s, rc, out[-400:]))

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

        n = len([o for o in res["blocks"].values() if o in ("base", "edit")])
        today = datetime.date.today().isoformat()
        state_file = read(blocks_dir, "zorg-core.json")
        everything, seen_before = tree_of(e.home, e.vault), len(fake.seen)
        rc, out, res = run_ok(e, "repo", "list")
        row = {r["id"]: r for r in res["repos"]}
        check("repo list: blocks, version and checked come from the block state",
              rc == 0 and row["zorg-core"]["blocks"] == n and row["zorg-core"]["base_version"] == "0.4"
              and (row["zorg-core"]["checked"] or "")[:10] == today
              and re.search(r"^zorg-core\s.*\s%d\s+0\.4\s+%s\s*$" % (n, today), out, re.M), (rc, out))
        check("…a repository never adopted: '—' in all three, None in the data",
              row["zorg-dead"]["blocks"] is None and row["zorg-dead"]["base_version"] is None and row["zorg-dead"]["checked"] is None
              and re.search(r"^zorg-dead\s.*—\s+—\s+—\s*$", out, re.M), out)
        check("…and it stays offline and writes nothing: no request to a server, not a byte in the home or the vault",
              len(fake.seen) == seen_before and tree_of(e.home, e.vault) == everything, (len(fake.seen), seen_before))
        open(os.path.join(blocks_dir, "zorg-core.json"), "w", encoding="utf-8", newline="").write("{")
        rc, out, res = run_ok(e, "repo", "list")
        check("a block state that is not JSON: '!' in its row, one line under the table, exit 0",
              rc == 0 and "block state unreadable: zorg-core (" in out
              and [r for r in res["repos"] if r["id"] == "zorg-core"][0].get("state_error")
              and re.search(r"^zorg-core\s.*\s!\s+!\s+!\s*$", out, re.M)
              and re.search(r"^zorg-dead\s.*—\s+—\s+—\s*$", out, re.M), (rc, out))
        open(os.path.join(blocks_dir, "zorg-core.json"), "w", encoding="utf-8", newline="").write(state_file)
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


with FakeMcp(tree={}) as bare:
    with tempfile.TemporaryDirectory() as d:
        e = repos_env(d, bare.url)
        run_ok(e, "migrate", "--apply")
        rc, out, res = run_ok(e, "repo", "status", "zorg-growth")
        check("reachable, blocks file not read: no version on the source, the reason on its own line",
              rc == 0 and "version on source: — · base:" in out and "  blocks file: " in out
              and res["repos"][0]["source_version"] is None and res["repos"][0]["fetch_error"]
              and "registration_version" in res["repos"][0], (rc, out))

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
              tree_of(records_dir) == recs_before and r.get("records_reverted") == [] and r.get("records_not_reverted") == [], (rc, r))

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
        # v3.13.1: an answer for a block the plan refuses is reported, not silently dropped
        ctx_c = read(e.ctx)
        for flag, args in (("--choose", ("--choose", "teams=mine")), ("--add", ("--add", "teams"))):
            rc_x, out_x, r_x = apply_run(e, core, "zorg-core", *args)
            lines_x = out_x.splitlines()
            said = "не застосовано: --choose/--add teams — у блоку зламані маркери (рядок «помилка» вище)"
            check("an answer for a block with broken markers is reported, not dropped (%s)" % flag,
                  said in lines_x and r_x["ignored"].get("teams") == "!"
                  and [i for i, l in enumerate(lines_x) if l.startswith("помилка: teams")][0] < lines_x.index(said), out_x[-500:])
            check("…and nothing is written for it (%s)" % flag, rc_x == 4 and read(e.ctx) == ctx_c and r_x["snapshot"] is None, (rc_x, out_x[-300:]))

    with tempfile.TemporaryDirectory() as d:            # v3.13.1: one --choose takes several answers; an answer is no repository
        e = repos_env(d, fake.url, core_extra=SKIP_PRODUCT)
        core = os.path.join(d, "ZorgCore")
        blocks_file = os.path.join(core, CORE_BLOCKS)
        run_ok(e, "migrate", "--apply")
        run_ok(e, "provider", "adopt", "zorg-core", "--apply")
        edit_both(e, "The user works on Zorg App only.", "The user works on Zorg App only (mine).")
        edit_both(e, "- Alpha, Beta\n", "- Alpha, Beta (mine)\n")
        change(blocks_file, SCOPE_04, SCOPE_05)
        change(blocks_file, "- Alpha, Beta\n<!-- zorg-core:end id=teams -->", "- Alpha, Beta, Gamma\n<!-- zorg-core:end id=teams -->")
        rc, out, res = apply_run(e, core, "zorg-core", "--choose", "scope=mine", "teams=theirs")
        check("one --choose takes several answers", rc == 0 and res["decisions"].get("scope") == "⚠ mine"
              and res["decisions"].get("teams") == "⚠ theirs", (rc, out[-600:]))
        check("…and each answer is acted on", "(mine)" in region_in(read(e.ctx), "zorg-core", "scope")
              and "Gamma" in region_in(read(e.ctx), "zorg-core", "teams") and "(mine)" not in region_in(read(e.ctx), "zorg-core", "teams"), read(e.ctx)[-600:])
        before = journal_len(e)
        rc, out, res = apply_run(e, core, "--choose", "scope=mine", "zorg-core")
        check("the repository after --choose is no answer: exit 3, nothing written",
              rc == 3 and "--choose takes BLOCK=" in out and journal_len(e) == before, (rc, out[-300:]))
        rc, out, res = apply_run(e, core, "scope=mine")
        check("an answer in the repository's place: exit 3, it says so",
              rc == 3 and "'scope=mine' looks like an answer, not a repository — put the repository first: "
              "ctx provider apply <repo> --choose BLOCK=… [BLOCK=…]" in out and journal_len(e) == before, (rc, out[-300:]))
        rc, out, res = apply_run(e, core, "zorg-core", "--add", "okr", "other", "--choose", "scope=mine", "teams=mine")
        check("--add takes several blocks too, and the flags can be repeated: an unknown one is the usual error, nothing written",
              rc == 3 and "okr" in out and "no block" in out and journal_len(e) == before, (rc, out[-300:]))

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
        check("ctx read puts the repository, the version and the day of the check before a block",      # v3.15: and its slot
              rc == 0 and "> [zorg-core · v0.2 · станом на %s · слот team.members — склад команди: люди, ролі, контакти]\n#### Members"
              % day in out, (rc, out[-600:]))
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
    check("an explicit namespace beats the manifest's: the core's scope and teams blocks are not this repository's — its file "
          "holds no block of it, so the repository is unavailable (exit 5), and no warning",
          rc == 5 and "rows" not in res and "holds no zorg-elsewhere block" in out and "namespace:" not in out.split("CTX_RESULT")[0],
          (rc, out[-300:]))

# --- v3.13.0 final review: an empty, cut or foreign blocks file is an unavailable repository, never "every block removed"
def text_of(out):
    return out.split("CTX_RESULT")[0]


with FakeMcp(tree={GROWTH_PATH: GROWTH_TEXT}) as fake:
    with tempfile.TemporaryDirectory() as d:
        e = repos_env(d, fake.url, core_extra=SKIP_PRODUCT)
        core = os.path.join(d, "ZorgCore")
        blocks_file = os.path.join(core, CORE_BLOCKS)
        pristine = read(blocks_file)
        run_ok(e, "migrate", "--apply")
        run_ok(e, "provider", "adopt", "zorg-core", "--apply")
        run_ok(e, "provider", "adopt", "zorg-growth", "--apply")
        held = lambda ns, ids: {b: region_in(read(e.ctx), ns, b) for b in ids}
        core_regions, growth_regions = held("zorg-core", ("scope", "teams", "team")), held("zorg-growth", ("growth-metrics", "team"))
        check("setup: the context holds the core's and the growth repository's regions, each with a base",
              all(core_regions.values()) and all(growth_regions.values())
              and set(block_state(e, "zorg-core")["blocks"]) == {"scope", "teams", "team"}, (core_regions, growth_regions))
        for label, text, why in (("an empty (0-byte) blocks file", "", "the blocks file holds no zorg-core block"),
                                 ("a blocks file cut inside its last region",
                                  pristine[:pristine.index("<!-- zorg-core:end id=teams -->")], "the blocks file is cut at block teams"),
                                 ("a blocks file of another namespace", pristine.replace("zorg-core", "zorg-other"),
                                  "the blocks file holds no zorg-core block"),
                                 ("a blocks file of this namespace that holds none of the blocks you have a base for", OKR + "\n",
                                  "holds none of the 2 blocks you have a base for (scope, teams)")):
            open(blocks_file, "w", encoding="utf-8", newline="").write(text)
            before = tree_of(e.home, e.vault)
            rc, out, res = run_ok(e, "provider", "plan", "zorg-core")
            check("%s: plan exits 5 — the repository is unavailable, with the reason, and no row at all" % label,
                  rc == 5 and "zorg-core · недоступний: " in text_of(out) and why in text_of(out) and "rows" not in res
                  and res["ok"] is False, (rc, out[-500:]))
            rc, out, res = run_ok(e, "provider", "apply", "zorg-core")
            check("%s: apply exits 5, nothing written, every region intact" % label,
                  rc == 5 and "нічого не записано" in out and why in text_of(out) and tree_of(e.home, e.vault) == before
                  and held("zorg-core", ("scope", "teams", "team")) == core_regions, (rc, out[-500:]))
        open(blocks_file, "w", encoding="utf-8", newline="").write(pristine)
        fake.tree[GROWTH_PATH] = ""
        before = tree_of(e.home, e.vault)
        rc, out, res = run_ok(e, "provider", "plan", "zorg-growth")
        check("MCP content \"\": plan exits 5 with the reason, no '−' rows", rc == 5 and "rows" not in res
              and "holds no zorg-growth block" in text_of(out), (rc, out[-400:]))
        rc, out, res = run_ok(e, "provider", "apply", "zorg-growth")
        check("…apply exits 5, nothing written, the growth regions intact", rc == 5 and tree_of(e.home, e.vault) == before
              and held("zorg-growth", ("growth-metrics", "team")) == growth_regions, (rc, out[-400:]))
        fake.tree[GROWTH_PATH] = GROWTH_TEXT
        open(blocks_file, "w", encoding="utf-8", newline="").write(pristine.replace(
            "<!-- zorg-core:begin id=scope v=0.4 -->\n### Scope of work\nThe user works on Zorg App only.\n<!-- zorg-core:end id=scope -->\n\n", ""))
        rc, out, res = run_ok(e, "provider", "plan", "zorg-core")
        check("a genuine removal of one block still plans '−' (the others are still published)",
              rc == 0 and signs_in(res) == {"scope": "−", "teams": "=", "team": "="}, (rc, out[-400:]))
        rc, out, res = run_ok(e, "provider", "apply", "zorg-core")
        check("…and apply removes that region alone", rc == 0 and region_in(read(e.ctx), "zorg-core", "scope") is None
              and held("zorg-core", ("teams", "team")) == {b: core_regions[b] for b in ("teams", "team")}, (rc, out[-400:]))

# --- v3.13.0 final review: a search-only MCP registration (connect-steps §7) is not a block repository
BRAIN_REG = ("schema: provider-registration/2\nid: zorg-brain\ntitle: Zorg brain (own index)\nkind: mcp\ncontract: vault/v1\n"
             "authority: personal\nmode: live\naccess: local\nendpoint:\n  url: http://127.0.0.1:9/mcp\n"
             "index: ~/.zorg-brain/brain.sqlite\nstatus: active\n")
INDEX_REG = "schema: provider-registration/1\nid: zorg-index\nkind: mcp\nauthority: personal\nmode: live\naccess: local\nindex: ~/x.sqlite\n"
with tempfile.TemporaryDirectory() as d:
    e = repos_env(d, "http://127.0.0.1:9/mcp", core_extra=SKIP_PRODUCT)
    prov = os.path.join(e.home, ".grow-pm", "providers")
    os.remove(os.path.join(prov, "zorg-growth.yaml"))
    dead_reg = read(prov, "zorg-dead.yaml")
    os.remove(os.path.join(prov, "zorg-dead.yaml"))
    open(os.path.join(prov, "zorg-brain.yaml"), "w", encoding="utf-8").write(BRAIN_REG)
    open(os.path.join(prov, "zorg-index.yaml"), "w", encoding="utf-8").write(INDEX_REG)
    run_ok(e, "migrate", "--apply")
    run_ok(e, "provider", "adopt", "zorg-core", "--apply")
    for args in (("plan",), ("apply",), ("plan", "--product", "Zorg App"), ("apply", "--product", "Zorg App")):
        rc, out, res = run_ok(e, "provider", *args)
        check("bare `provider %s`: a search-only registration is left out with one line, the block repository is served (exit 0)"
              % " ".join(args), rc == 0 and "лише пошук: zorg-brain" in out and "лише пошук: zorg-index" in out
              and "zorg-core · джерело: тека" in out and "недоступний" not in out
              and sorted(res.get("search_only") or []) == ["zorg-brain", "zorg-index"]
              and [r["repo"] for r in res["repos"]] == ["zorg-core"], (rc, out[-600:]))
    for args in (("plan", "zorg-brain"), ("apply", "zorg-brain"), ("adopt", "zorg-brain"), ("plan", "zorg-index")):
        before = tree_of(e.home, e.vault)
        rc, out, res = run_ok(e, "provider", *args)
        check("`provider %s` names a search-only registration: exit 3 with the reason, nothing written" % " ".join(args),
              rc == 3 and "search-only" in out and "no blocks_file" in out and tree_of(e.home, e.vault) == before, (rc, out[-400:]))
    open(os.path.join(prov, "zorg-dead.yaml"), "w", encoding="utf-8").write(dead_reg)
    rc, out, res = run_ok(e, "provider", "plan")
    check("…a repository that publishes blocks and does not answer is still exit 5", rc == 5 and "zorg-dead · недоступний" in out
          and "лише пошук: zorg-brain" in out, (rc, out[-500:]))

# --- v3.13.0 final review: adopt --apply imports the edits waiting first, so undo across an adopt keeps an earlier edit
def journal_ops_of(e):
    return [json.loads(l)["op"] for l in read(e.store, ".state", "journal.jsonl").splitlines() if l.strip()]


for kind in ("a record file edited in Obsidian", "local-context.md edited by hand"):
    with tempfile.TemporaryDirectory() as d:
        e = repos_env(d, "http://127.0.0.1:9/mcp")
        run_ok(e, "migrate", "--apply")
        if kind.startswith("a record"):
            add_line(os.path.join(e.store, "records", "product.zorg-app.md"), "- obsidian edit")
        else:
            edit_both(e, "- **Jira Project Key:** PROJ", "- **Jira Project Key:** PROJ\n- obsidian edit")
        rc, out, res = run_ok(e, "provider", "adopt", "zorg-core", "--apply")
        check("%s, then adopt --apply: the edit is imported first (record, both copies, nothing waits), then the bases" % kind,
              rc == 0 and res["written"] is True and "obsidian edit" in e.record("product.zorg-app") and "obsidian edit" in read(e.ctx)
              and "obsidian edit" in read(e.mirror) and in_sync(e) and journal_ops_of(e)[-2:] == ["sync", "provider-adopt"],
              (rc, out[-400:], journal_ops_of(e)))
        run_ok(e, "set", "product.zorg-app", "Jira Project Key", "ZNEW")
        rc, out, res = run_ok(e, "undo", "--steps", "2")
        check("…undo --steps 2 takes back the later write and the adopt; the edit made before them stays",
              rc == 0 and "obsidian edit" in e.record("product.zorg-app") and "obsidian edit" in read(e.ctx)
              and "ZNEW" not in read(e.ctx) and block_state(e, "zorg-core") is None and in_sync(e), (rc, out[-400:]))

# --- v3.13 Task 12: the protocol documents say what the commands do
def lacks(text, needed):
    return [s for s in needed if s not in text]


cp_flat = re.sub(r"\s+", " ", read(ROOT, "references", "context-protocol.md"))
pp_flat = re.sub(r"\s+", " ", read(ROOT, "references", "context-provider-protocol.md"))
hp_flat = re.sub(r"\s+", " ", read(ROOT, "references", "host-profiles.md"))
need_cp = ["`repo list", "`repo status", "`provider adopt", "`provider plan", "`provider apply", "5 a repository is unavailable",
           "records_reverted", "a record created in Obsidian and imported is not removed", ".state/blocks/",
           "Human edits in a block are kept", "Agent edits are not written", "One snapshot and one journal line per repository",
           "`ctx undo` takes back the last repository's pass only", "a snapshot with no journal line", "`--json` is accepted and changes nothing",
           "> [<repo-id> · v<version> · станом на <date>]", "⚠ конфлікт: файл і запис різняться — ctx sync", "**Repos:**",
           "`provider adopt --apply` imports first like every writing command"]
check("context-protocol documents repo and provider commands, exit 5, the undo clause, snapshots with .state/blocks, one snapshot per repository",
      not lacks(cp_flat, need_cp), lacks(cp_flat, need_cp))
need_pp = ["provider-registration/2", "## 12. Blocks and merge", "`core_root`", "`namespace`", "`blocks_file`", "`rank`", "`products`",
           "`endpoint.url`", "`endpoint.root`", "`endpoint.headers_env`", "`blocks_source`", "`home_record`", "`skip_blocks`", "`status`",
           "`base`", "`edit`", "`none`", "`has-base`", "`duplicate`", "`broken marker`", "`nested`",
           "| `=` |", "| `~` |", "| `✎` |", "| `⚠` |", "| `+` |", "| `−` |", "| `✂` |", "| `?` |", "| `·` |",
           "| 5 | a repository is unreachable, or its blocks file is no source", "`{repo, error}`", "paused",
           "`vault_get_note`, `vault_list_by_folder`, `vault_search`, `brain_status` and `brain_recent_changes`", "check 17",
           "No redirect is followed", "never goes to the network", "`<!-- ctx:both theirs -->`", "detaches", "no journal line",
           "its own snapshot and journal line"]
check("context-provider-protocol: registration v2 key table, §12 with the first base, signs, exit codes, result shapes, the allow-list",
      not lacks(pp_flat, need_pp), lacks(pp_flat, need_pp))
need_hp = ["Context repositories", "`repo status`", "`vault_get_note`", "never goes to the network"]
check("host-profiles: the network use of ctx and the host without SHELL", not lacks(hp_flat, need_hp), lacks(hp_flat, need_hp))
check("ctx_store.Store documents .state/blocks/", ".state/blocks/" in (cs_mod.Store.__doc__ or ""), cs_mod.Store.__doc__)

# --- v3.13.1: the usage (the head of ctx.py) and the protocols say what the answers, undo and the exit 5 do
import ast  # noqa: E402
ctx_usage = re.sub(r"\s+", " ", ast.get_docstring(ast.parse(read(CTX))) or "")
check("ctx usage names both readings of exit 5",
      "5 a repository is unreachable, or its blocks file is no source (empty, cut, foreign, or none of your based blocks) "
      "— nothing written (provider commands)" in ctx_usage, ctx_usage[-700:])
check("ctx usage shows several answers per --choose and several blocks per --add",
      "provider apply [REPO] [--product P] [--choose BLOCK=theirs|mine|both [BLOCK=… …]] [--add BLOCK [BLOCK …]] [--json]" in ctx_usage, ctx_usage[:3000])
need_1301 = {
    "context-protocol": (cp_flat, ["records_not_reverted", "not put back (no matching text in local-context.md): <ids> — check them: ctx get <id>"]),
    "context-provider-protocol": (pp_flat, ["[--choose BLOCK=theirs|mine|both [BLOCK=… …]] [--add BLOCK [BLOCK …]]",
                                            "retired every block you hold", "remove those regions by hand (context-provider-protocol.md §12.2)",
                                            "не застосовано", "looks like an answer, not a repository"]),
}
for doc_name, (flat, needed) in need_1301.items():
    check("%s says what v3.13.1 changed" % doc_name, not lacks(flat, needed), lacks(flat, needed))

# --- v3.13.0 final review: the documents say what the fixes do, and no rule about managed regions contradicts §12
vs = read(ROOT, "references", "vault-schema.md")
vs_regions = re.sub(r"\s+", " ", vs[vs.index("## Generated regions and layers"):vs.index("## Tag Taxonomy")])
check("vault-schema: the ban is scoped — a skill or the agent never writes inside a region; a human's edit in a provider's block is kept with a store",
      "never edited by hand or by a skill" not in vs_regions and "never writes inside one" in vs_regions
      and "kept by `ctx provider apply`" in vs_regions and "§12" in vs_regions, vs_regions[:700])
pp_terms = pp_flat[pp_flat.index("## 1. Terms"):pp_flat.index("## 2. Contract")]
pp_8 = pp_flat[pp_flat.index("## 8. Generated regions"):pp_flat.index("## 9. Provider kit")]
check("context-provider-protocol §1 and §8: no 'written only by'; a human's edit in a provider block is kept with a store (§12)",
      "written only by" not in pp_terms + pp_8 and all("§12" in s and "kept" in s and "never writes inside" in s for s in (pp_terms, pp_8)),
      (pp_terms[-700:], pp_8))
need_final_pp = ["`plan` never exits 2", "the blocks file holds no <ns> block (empty, cut, or another namespace)",
                 "the blocks file is cut at block <id>", "holds none of the N blocks you have a base for", "never \"the repository removed every block\"",
                 "джерело позаду вашої бази (v<theirs> < v<yours>)", "лише пошук: <id>", "search_only: [ids]", "**search-only**",
                 "imports the edits waiting first", "`imported`", "joined by `; `", "a new `v=` on every block", "half a second"]
check("context-provider-protocol documents the fixes of the final review (empty/cut/foreign/lost source, a lagging source, search-only, "
      "adopt imports first, plan never exits 2, the card line, the digest's dates)", not lacks(pp_flat, need_final_pp), lacks(pp_flat, need_final_pp))
gone_pp = ["a region that is never closed is no region", "Shown in plans", "a new `v=` on the blocks that changed",
           "A state file that cannot be read or is not valid stops the command", "`adopt` says so (`ctx sync` first, so it sees them)",
           "one line per registered repository", "| 2 | decisions are waiting (`apply`: the rest was applied)"]
check("context-provider-protocol: none of the outdated sentences stays", [s for s in gone_pp if s in pp_flat] == [], [s for s in gone_pp if s in pp_flat])
need_final_cp = ["imports the edits waiting first", "signs: `context-provider-protocol.md` §12.5", "joined by `; `", "half a second",
                 "лише пошук", "holds none of the blocks you have a base for"]
gone_cp = ["a skill has no other way into one", "does not import first", "one line `- **Repos:** <id>: <N> блок/блоки/блоків · v<version> · перевірено <date>` per",
           "inside the same budget", "the plan signs: `context-provider-protocol.md` §12.7"]
check("context-protocol: adopt imports first, §12.5 for the signs, the card line, the digest's dates, an unavailable source; no overclaim",
      not lacks(cp_flat, need_final_cp) and [s for s in gone_cp if s in cp_flat] == [],
      (lacks(cp_flat, need_final_cp), [s for s in gone_cp if s in cp_flat]))
cst = re.sub(r"\s+", " ", read(ROOT, "skills", "context-connect", "references", "connect-steps.md"))
skl = re.sub(r"\s+", " ", read(ROOT, "skills", "context-connect", "SKILL.md"))
check("connect-steps: plan exits 0 or 5 and never 2; apply's codes apart; rank is core-derived only; no confusing skip_blocks aside; §7 search-only",
      "`plan` exits 0" in cst and "never 2" in cst and "Exit codes of `plan` and `apply`" not in cst and "the rank of the authority" not in cst
      and "keeps as passed" not in cst and "лише пошук" in cst[cst.index("## §7"):], cst[cst.index("4. Exit codes"):][:600] if "4. Exit codes" in cst else cst[:300])
check("SKILL.md Step 6.1 says one line per key, as connect-steps does", "one line per key" in skl[skl.index("## Step 6"):skl.index("## What is forbidden")],
      skl[skl.index("## Step 6"):][:900])
tp_flat = re.sub(r"\s+", " ", read(ROOT, "testing", "Testing-process.md"))
check("Testing-process.md carries no host-specific process rule (a scanner on the repository, re-running a time-limit check alone)",
      "scanner on the repository" not in tp_flat and "re-run alone" not in tp_flat and "Every test is run once per release" not in tp_flat,
      tp_flat[tp_flat.find("Every test is run"):][:300])

# --- v3.13.1: a writing command saves the digest's summary next to the context; a reading one does not
with tempfile.TemporaryDirectory() as d:
    e = Env(d)
    cache = os.path.join(e.home, ".grow-pm", ".ctx-summary.json")
    rc, out, res = run_ok(e, "sync")
    check("a writing command without a store saves no summary", rc == 0 and not os.path.exists(cache), (rc, out[-300:]))
    run_ok(e, "migrate", "--apply")
    check("migrate --apply saves the summary too", os.path.isfile(cache))
    if os.path.exists(cache):
        os.remove(cache)
    e.edit(e.ctx, "- **Cadence:** daily", "- **Cadence:** weekly")
    rc, out, res = run_ok(e, "sync")
    records_now = len([n for n in os.listdir(os.path.join(e.store, "records")) if n.endswith(".md")])
    saved = json.load(open(cache, encoding="utf-8")) if os.path.isfile(cache) else {}
    check("a writing command saves the summary next to the context", rc == 0 and saved.get("facts", {}).get("records") == records_now,
          (rc, out[-300:]))
    check("…for this context, after the import: nothing waits", saved.get("schema") == 1 and saved.get("context") == os.path.realpath(e.ctx)
          and saved["facts"]["pending"] == 0 and saved["facts"]["conflicts"] == 0 and records_now == 14, saved)
    if os.path.exists(cache):
        os.remove(cache)
    rc, out, res = run_ok(e, "read", "--skill", "focus-advisor")
    check("a reading command writes no summary", not os.path.exists(cache), (rc, out[-300:]))
    rc, out, res = run_ok(e, "set", "product.no-such", "Jira Project Key", "X")
    check("a writing command that fails writes no summary", rc != 0 and not os.path.exists(cache), (rc, out[-300:]))
    os.makedirs(cache)                                  # the summary cannot be saved: the command's own result stands
    rc, out, res = run_ok(e, "set", "product.zorg-app", "Jira Project Key", "SUM")
    check("a summary that cannot be saved never changes the exit code", rc == 0 and res and res.get("ok") is True
          and os.path.isdir(cache) and "- **Jira Project Key:** SUM" in read(e.ctx), (rc, out[-300:]))
    os.rmdir(cache)
    env = dict(os.environ); env.pop("GROW_PM_CONTEXT_PATH", None)
    p = subprocess.run([sys.executable, CTX, "sync", "--home", e.home, "--context", e.mirror],
                       capture_output=True, text=True, env=env, timeout=120)
    written = [os.path.join(dp, n) for r in (e.home, e.vault) for dp, _, fn in os.walk(r) for n in fn if n == ".ctx-summary.json"]
    check("a context outside .grow-pm (the vault's copy): the command runs, no summary anywhere", p.returncode == 0 and written == [],
          (p.returncode, written, p.stdout[-300:]))

cp_1 = cp_flat[cp_flat.index("## 1. Where things live"):cp_flat.index("## 2. Records")]
cp_7 = cp_flat[cp_flat.index("## 7. The session digest"):cp_flat.index("## 8. Snapshots")]
need_7 = ["· cached YYYY-MM-DD HH:MM", "two seconds", "older than 7 days", "every writing `ctx` command", "never goes to the network",
          "`~/.grow-pm/.ctx-summary.json`", "not available locally (still downloading?)"]
check("context-protocol §1 names the summary file and §7 the cached line, its age limit, who writes it, no network",
      "`~/.grow-pm/.ctx-summary.json`" in cp_1 and not lacks(cp_7, need_7), (cp_1[-600:], lacks(cp_7, need_7)))

# --- v3.13.1 final review: the summary after a write is counted on the digest's budget; a skipped registration is
# never silent; an answer that names a repository; the cache in the linked layout
NOT_LOCAL = "not available locally (still downloading?)"


def unblock(fifo):
    """Let a reader waiting on the FIFO out of open() (a reader left in this process, or none)."""
    for _ in range(3):
        try:
            os.close(os.open(fifo, os.O_WRONLY | os.O_NONBLOCK))
        except OSError:
            pass
        time.sleep(0.05)


with tempfile.TemporaryDirectory() as d:
    e = Env(d)
    run_ok(e, "migrate", "--apply")
    t0 = time.time(); rc0, _, _ = run_ok(e, "set", "product.zorg-app", "Jira Project Key", "BASE"); base = time.time() - t0
    blocks = os.path.join(e.store, ".state", "blocks")
    os.makedirs(blocks, exist_ok=True)
    fifo = os.path.join(blocks, "zorg-slow.json")
    os.mkfifo(fifo)                                     # a block state iCloud has evicted: its read waits for a download
    try:
        t0 = time.time(); rc, out, res = run_ok(e, "set", "product.zorg-app", "Jira Project Key", "FIFO"); took = time.time() - t0
    finally:
        unblock(fifo)
        os.remove(fifo)
    saved = json.load(open(os.path.join(e.home, ".grow-pm", ".ctx-summary.json"), encoding="utf-8"))
    check("a block state that never arrives does not hold a writing command: exit 0 within the summary's budget (2 s + 0.5 s) and a margin",
          rc0 == 0 and rc == 0 and res and res.get("ok") is True and took < base + 2.5 + 3.0, (rc, round(took, 2), round(base, 2), out[-300:]))
    check("…and the summary is still saved, its facts counted after the write", saved["facts"]["records"] == 14 and saved["facts"]["pending"] == 0, saved)

with tempfile.TemporaryDirectory() as d:                 # the home copy is a link into the vault's mirror (one copy)
    e = Env(d)
    os.remove(e.ctx)
    os.symlink(e.mirror, e.ctx)
    run_ok(e, "migrate", "--apply")
    cache = os.path.join(e.home, ".grow-pm", ".ctx-summary.json")
    if os.path.exists(cache):
        os.remove(cache)
    rc, out, res = run_ok(e, "set", "product.zorg-app", "Jira Project Key", "LINK")
    check("the linked layout: a writing command saves the summary beside the link, in ~/.grow-pm",
          rc == 0 and os.path.islink(e.ctx) and os.path.isfile(cache) and not os.path.exists(os.path.join(os.path.dirname(e.mirror), ".ctx-summary.json")),
          (rc, os.listdir(os.path.dirname(e.ctx)), out[-300:]))
    via_link = ctx_ops_mod.load_summary(e.ctx)
    via_real_home = ctx_ops_mod.load_summary(os.path.join(os.path.realpath(e.home), ".grow-pm", "local-context.md"))
    check("…and load_summary finds it through either spelling of the link (the home as given, the home resolved)",
          via_link and via_real_home and via_link["records"] == via_real_home["records"] == 14
          and json.load(open(cache, encoding="utf-8"))["context"] == os.path.realpath(e.mirror), (via_link, via_real_home))

with tempfile.TemporaryDirectory() as d:                 # a registration the 3 s budget skipped is named, never silent
    e = repos_env(d, "http://127.0.0.1:9/mcp", core_extra=SKIP_PRODUCT)
    prov = os.path.join(e.home, ".grow-pm", "providers")
    os.remove(os.path.join(prov, "zorg-growth.yaml"))
    os.remove(os.path.join(prov, "zorg-dead.yaml"))
    run_ok(e, "migrate", "--apply")
    run_ok(e, "provider", "adopt", "zorg-core", "--apply")
    rc_plain, out_plain, _ = run_ok(e, "provider", "plan")
    card_line = lambda: next((l for l in read(e.store, "INDEX.md").splitlines() if l.startswith("- **Repos:**")), None)
    line_before = card_line()
    slow = os.path.join(prov, "zorg-slow.yaml")
    os.mkfifo(slow)                                     # a registration iCloud has evicted: it does not arrive within 3 s
    said = "unreadable registration: %s (%s)" % (slow, NOT_LOCAL)
    try:
        rc, out, res = run_ok(e, "provider", "plan")
        check("plan without REPO names the registration it could not read, as repo list does; the exit code of the readable one stands",
              rc_plain == 0 and rc == 0 and said in out.splitlines() and "zorg-core · джерело: тека" in out
              and res.get("unreadable") == [{"file": slow, "reason": NOT_LOCAL}] and [r["repo"] for r in res["repos"]] == ["zorg-core"],
              (rc_plain, rc, out[-600:], res and res.get("unreadable")))
        rc, out, res = run_ok(e, "provider", "apply", "zorg-slow")
        check("apply naming a registration that could not be read: exit 3, and it says it may still be downloading",
              rc == 3 and "no repository 'zorg-slow' is registered — `ctx.py repo list` — a registration could not be read: %s (%s); "
              "it may still be downloading" % (slow, NOT_LOCAL) in out, (rc, out[-500:]))
    finally:
        unblock(slow)
        os.remove(slow)
    # a bare apply under the lock also checks the provider boundary, which still reads registrations without a time limit
    # (v3.14): the apply paths are shown with a registration that cannot be read at once
    broken = os.path.join(prov, "zorg-broken.yaml")
    open(broken, "w", encoding="utf-8").write("id: zorg-broken\nendpoint:\n  nested:\n    deeper: 1\n")
    rc, out, res = run_ok(e, "provider", "apply")
    why = ((res or {}).get("unreadable") or [{}])[0].get("reason") or "?"
    check("apply without REPO names a registration it could not read, in the output and the result; the readable one is applied (exit 0)",
          rc == 0 and "unreadable registration: %s (%s)" % (broken, why) in out.splitlines() and why != "?"
          and res["unreadable"] == [{"file": broken, "reason": why}] and [r["repo"] for r in res["repos"]] == ["zorg-core"], (rc, out[-600:]))
    unread_line = "реєстрацію %s не прочитано — ранги й правила її блоків невідомі; кандидати з неї показано без каскаду" % broken
    rc, out, res = run_ok(e, "read", "--skill", "product-analysis")    # v3.15: zorg-growth's blocks have no registration read
    check("ctx read names a registration it could not read, once, when a block in the records has no registration read",
          rc == 0 and out.splitlines().count(unread_line) == 1, (rc, out[-600:]))
    rc, out, res = run_ok(e, "provider", "apply", "zorg-core")
    check("…and the card keeps its Repos line, with one line saying why it was not refreshed",
          rc == 0 and card_line() == line_before and line_before
          and "card not refreshed: a registration could not be read: %s (%s)" % (broken, why) in out.splitlines(), (rc, out[-500:], card_line()))
    state_file = os.path.join(e.store, ".state", "blocks", "zorg-core.json")
    st = json.loads(read(state_file))
    st["checked"] = "2026-01-01T10:00:00+03:00"                         # a line rebuilt now would say another day
    open(state_file, "w", encoding="utf-8").write(json.dumps(st))
    rc, out, res = run_ok(e, "card")
    check("`ctx card` with a registration skipped keeps the Repos line too (not rebuilt)", rc == 0 and card_line() == line_before
          and "перевірено 2026-01-01" not in (card_line() or ""), (rc, out[-300:], card_line()))
    os.remove(broken)
    rc, out, res = run_ok(e, "card")
    check("…and with every registration read, `ctx card` rebuilds it", rc == 0 and "zorg-core: 3 блоки · v0.4 · перевірено 2026-01-01" in (card_line() or ""),
          (rc, card_line()))
    rc, out, res = run_ok(e, "read", "--skill", "product-analysis")
    check("…and ctx read no longer names one", rc == 0 and "не прочитано — ранги" not in out, (rc, out[-400:]))

with FakeMcp(tree={GROWTH_PATH: GROWTH_TEXT}) as fake:   # an answer or a block that names a repository
    with tempfile.TemporaryDirectory() as d:
        e = repos_env(d, fake.url, core_extra="status: paused\n")
        os.remove(os.path.join(e.home, ".grow-pm", "providers", "zorg-dead.yaml"))
        run_ok(e, "migrate", "--apply")
        e.edit(e.ctx, "- **Jira Project Key:** PROJ\n", "- **Jira Project Key:** PROJW\n")      # an edit waiting to be imported
        waiting, journal, asked = read(e.ctx), journal_len(e), len(fake.seen)
        for args, said in (
                (("--add", "okr", "zorg-core"), "'zorg-core' is a repository, not a block — put the repository first: "
                                                "ctx provider apply <repo> --add BLOCK [BLOCK …]"),
                (("--add", "growth-metrics", "zorg-growth"), "'zorg-growth' is a repository, not a block — put the repository first: "
                                                             "ctx provider apply <repo> --add BLOCK [BLOCK …]"),
                (("--choose", "zorg-growth=theirs"), "'zorg-growth' is a repository, not a block — put the repository first: "
                                                     "ctx provider apply <repo> --choose BLOCK=…")):
            rc, out, res = run_ok(e, "provider", "apply", *args)
            check("`provider apply %s`: exit 3 before anything — the message, journal unchanged, the edit still waiting, no request"
                  % " ".join(args), rc == 3 and said in out and journal_len(e) == journal and read(e.ctx) == waiting
                  and len(fake.seen) == asked, (rc, out[-400:], journal_len(e) - journal, len(fake.seen) - asked))

cp_7 = re.sub(r"\s+", " ", read(ROOT, "references", "context-protocol.md"))
cp_7 = cp_7[cp_7.index("## 7. The session digest"):cp_7.index("## 8. Snapshots")]
need_7b = ["`repo list`", "`repo status`", "`provider adopt|plan|apply`", "`read`", "the card's `Repos` line",
           "unreadable registration: <path> (<reason>)", "it may still be downloading", "card not refreshed:"]
check("context-protocol §7 names the ctx paths that read registrations within three seconds and what each says of one skipped",
      not lacks(cp_7, need_7b) and "the `ctx` commands that list repositories: three" not in cp_7, lacks(cp_7, need_7b))
mcp_doc = re.sub(r"\s+", " ", ast.get_docstring(ast.parse(read(ROOT, "testing", "ctx_mcp_test.py"))) or "")
check("ctx_mcp_test's docstring says what repo status shows now (no fallback to the registration's version)",
      "registration's own as the fallback" not in mcp_doc and "registration_version" in mcp_doc, mcp_doc[-500:])
check("repo list tests the state error by `is not None`", "if error is not None:" in read(CTX), "")

# --- v3.14.0 Task 1: --choose theirs on a ✎ takes the repository's text; plan and apply show a core rule
import ctx_blocks as cb_mod  # noqa: E402

with FakeMcp(tree={GROWTH_PATH: GROWTH_TEXT}) as fake:
    with tempfile.TemporaryDirectory() as d:
        e = repos_env(d, fake.url, core_extra=SKIP_PRODUCT)
        core = os.path.join(d, "ZorgCore")
        blocks_file = os.path.join(core, CORE_BLOCKS)
        core_teams_text = region_in(read(blocks_file), "zorg-core", "teams")
        run_ok(e, "migrate", "--apply")
        run_ok(e, "provider", "adopt", "zorg-core", "--apply")
        edit_both(e, "- Alpha, Beta\n", "- Alpha, Beta (mine)\n")
        rc, out, res = apply_run(e, core, "zorg-core", "--choose", "teams=mine")
        check("--choose mine on a ✎ is still not needed, and said so", rc == 0 and res["ignored"] == {"teams": "✎"}
              and "не потрібне: --choose/--add teams — знак ✎" in out and "(mine)" in region_in(read(e.ctx), "zorg-core", "teams"), (rc, out[-500:]))
        rc, out, res = apply_run(e, core, "zorg-core", "--choose", "teams=theirs")   # teams is ✎ (yours edited, core unchanged)
        check("--choose theirs on a ✎ takes the repository's text", rc == 0 and res["decisions"]["teams"] == "✎ theirs"
              and region_in(read(e.ctx), "zorg-core", "teams") == core_teams_text, (rc, out[-500:]))
        check("…in both copies; the journal names the text taken; the next plan is '='",
              region_in(read(e.mirror), "zorg-core", "teams") == core_teams_text and res["ignored"] == {}
              and last_journal(e)["taken"] == {"teams": cs_mod.sha_text(cb_mod.norm(core_teams_text))}
              and signs_in(run_ok(e, "provider", "plan", "zorg-core")[2])["teams"] == "=", last_journal(e))
        change(blocks_file, "<!-- zorg-core:begin id=scope v=0.4 -->", "<!-- zorg-core:begin id=scope v=0.4 policy=rule -->")
        rc, out, res = plan_run(e, core, "zorg-core")
        scope_row = [r for r in res["rows"] if r["block"] == "scope"][0]
        check("plan shows a core rule: the row's note ends with (правило ядра), rule: true in the result",
              rc == 0 and scope_row.get("rule") is True and any(l.startswith("~") and "scope" in l and l.endswith("(правило ядра)")
                                                                for l in out.splitlines()), (rc, out[-500:]))
        rc, out, res = apply_run(e, core, "zorg-core")
        check("…and so does apply, which takes a '~' of a rule as any other", rc == 0 and res["applied"].get("scope") == "~"
              and "(правило ядра)" in out and "policy=rule" in region_in(read(e.ctx), "zorg-core", "scope"), (rc, out[-500:]))

def reject(e, repo, texts):
    """Write `rejected` into the repository's block state: {block: repository text or None (a removal)} — what undoing a
    sync pass will leave there (Task 6)."""
    path = os.path.join(e.store, ".state", "blocks", repo + ".json")
    state = json.loads(read(path))
    state["rejected"] = {b: [cb_mod.offered(t)] for b, t in texts.items()}
    open(path, "w", encoding="utf-8").write(json.dumps(state, ensure_ascii=False, indent=1, sort_keys=True) + "\n")


with FakeMcp(tree={GROWTH_PATH: GROWTH_TEXT}) as fake:   # fix round 1: a manual apply never re-applies a text you rejected
    with tempfile.TemporaryDirectory() as d:
        e = repos_env(d, fake.url, core_extra=SKIP_PRODUCT)
        core = os.path.join(d, "ZorgCore")
        blocks_file = os.path.join(core, CORE_BLOCKS)
        run_ok(e, "migrate", "--apply")
        run_ok(e, "provider", "adopt", "zorg-core", "--apply")
        old_a, old_b = region_in(read(e.ctx), "zorg-core", "scope"), region_in(read(e.ctx), "zorg-core", "teams")
        change(blocks_file, SCOPE_04, SCOPE_05)
        change(blocks_file, "- Alpha, Beta\n<!-- zorg-core:end id=teams -->", "- Alpha, Beta, Gamma\n<!-- zorg-core:end id=teams -->")
        new_a, new_b = region_in(read(blocks_file), "zorg-core", "scope"), region_in(read(blocks_file), "zorg-core", "teams")
        reject(e, "zorg-core", {"scope": new_a, "teams": new_b})
        n_journal = journal_len(e)
        rc, out, r = apply_run(e, core, "zorg-core")
        check("apply over two rejected '~' blocks writes neither: both held, nothing asked, exit 0",
              rc == 0 and r["held"] == {"scope": "~", "teams": "~"} and r["pending"] == [] and r["written"] == []
              and region_in(read(e.ctx), "zorg-core", "scope") == old_a and region_in(read(e.ctx), "zorg-core", "teams") == old_b
              and journal_len(e) == n_journal, (rc, out[-600:]))
        check("…its text says each is held and how to take it",
              "утримано: ~ scope — цей прохід його не чіпав · взяти текст ядра: --choose scope=theirs" in out.splitlines()
              and "утримано: ~ teams — цей прохід його не чіпав · взяти текст ядра: --choose teams=theirs" in out.splitlines(), out[-600:])
        rc, out, r = apply_run(e, core, "zorg-core", "--choose", "scope=theirs")
        check("--choose A=theirs takes A, B stays held", rc == 0 and r["decisions"].get("scope") == "~ theirs" and r["held"] == {"teams": "~"}
              and region_in(read(e.ctx), "zorg-core", "scope") == new_a and region_in(read(e.ctx), "zorg-core", "teams") == old_b, (rc, out[-600:]))
        rc, out, r = plan_run(e, core, "zorg-core")
        rows = {x["block"]: x for x in r["rows"]}
        check("…the next plan shows A without the rejected mark, B still with it",
              rows["scope"]["sign"] == "=" and "rejected" not in rows["scope"] and rows["teams"].get("rejected") is True
              and rows["teams"]["sign"] == "~" and r["changes"] == 0, out[-500:])
        open(blocks_file, "a", encoding="utf-8").write("\n" + OKR + "\n")
        reject(e, "zorg-core", {"teams": new_b, "okr": OKR})
        rc, out, r = apply_run(e, core, "zorg-core")
        check("a rejected '+' is held too: not awaited, exit 0", rc == 0 and r["held"] == {"teams": "~", "okr": "+"} and r["pending"] == []
              and "id=okr" not in read(e.ctx), (rc, out[-500:]))
        rc, out, r = apply_run(e, core, "zorg-core", "--add", "okr")
        check("…--add of the rejected '+' takes it", rc == 0 and r["applied"].get("okr") == "+" and OKR in read(e.ctx)
              and r["held"] == {"teams": "~"}, (rc, out[-500:]))

pp_now = re.sub(r"\s+", " ", read(ROOT, "references", "context-provider-protocol.md"))
need_1314_t1 = ["policy=rule", "(правило ядра)", "`--choose <block>=theirs` on a `✎`", "`✎ theirs`", "`taken`", "`\"removed\"`",
                "`rejected`", "відкинуто вами — не застосовується, доки ядро не змінить блок", "`hold`", "`held`", "`provider-sync`",
                "утримано: <sign> <block> — цей прохід його не чіпав"]
check("context-provider-protocol documents v3.14.0's apply: policy=rule, theirs on ✎, taken, rejected, hold, the op label",
      not lacks(pp_now, need_1314_t1), lacks(pp_now, need_1314_t1))
check("ctx usage says a ✎ takes --choose BLOCK=theirs", "a ✎ takes --choose BLOCK=theirs" in re.sub(r"\s+", " ", ast.get_docstring(ast.parse(read(CTX))) or ""),
      "")
usage_now = re.sub(r"\s+", " ", ast.get_docstring(ast.parse(read(CTX))) or "")
need_fix1_usage = ["A text you rejected by undoing a sync pass is held (\"утримано: …\"), never re-applied, unless taken: --choose BLOCK=theirs (any sign)", "CTX_RESULT: the plan with applied, decisions, pending, ignored, held, written, snapshot"]
need_fix1_pp = ["`ctx provider apply` does not take it again either", "· взяти текст ядра: --choose <block>=theirs",
                "`--choose <block>=theirs` on a rejected row of any sign that offers"]
check("fix round 1: the usage and §12.6 say a manual apply holds a rejected text and how to take it",
      not lacks(usage_now, need_fix1_usage) and not lacks(pp_now, need_fix1_pp)
      and "`ctx provider apply` passes neither (its `held` is `{}`)" not in pp_now and "neither makes `apply` act differently" not in pp_now,
      (lacks(usage_now, need_fix1_usage), lacks(pp_now, need_fix1_pp)))

# --- v3.14.0 Task 4: ctx provider sync — the daily pass, due once a day, within 20 seconds, never waiting on a lock
import threading  # noqa: E402
import ctx_mcp as cm_mod  # noqa: E402
import ctx_repos as crp_mod  # noqa: E402
import ctx_synced as sy_mod  # noqa: E402

DAY0 = "2026-10-14T09:00:00+03:00"
DAY1 = "2026-10-16T09:00:00+03:00"
DAY1_PLUS_1H = "2026-10-16T10:00:00+03:00"
DAY2 = "2026-10-17T09:00:00+03:00"
DAY2_PLUS_1M = "2026-10-17T09:01:00+03:00"
DAY2_PLUS_31M = "2026-10-17T09:31:00+03:00"
DAY2_PLUS_2H = "2026-10-17T11:02:00+03:00"
G_METRICS = ("<!-- zorg-growth:begin id=growth-metrics v=0.1 -->\n#### Growth metrics\n- **North star:** weekly active shoppers\n"
             "<!-- zorg-growth:end id=growth-metrics -->")
G_TEAM = "<!-- zorg-growth:begin id=team v=0.1 -->\n### Team: Alpha (growth view)\n- **Growth squad:** Alpha\n<!-- zorg-growth:end id=team -->"
G_OKR = "<!-- zorg-growth:begin id=growth-okr v=0.2 -->\n#### Growth OKR\n- double weekly buyers\n<!-- zorg-growth:end id=growth-okr -->"
SYNC_KEYS = {"repo", "at", "outcome", "updated", "added", "removed", "kept_yours", "took_rule", "awaiting", "held", "held_behind", "rejected",
             "reason", "report", "snapshot"}
assert G_METRICS in GROWTH_TEXT and G_TEAM in GROWTH_TEXT


def set_sync(e, rid, value):
    """`sync: <value>` at the end of the registration of `rid` (the home providers folder of repos_env)."""
    with open(os.path.join(e.home, ".grow-pm", "providers", rid + ".yaml"), "a", encoding="utf-8") as f:
        f.write("sync: %s\n" % value)


def checked_at(e, rid, when):
    """Put the repository's last check at `when`: an adopt checks too (now, on the real clock), so a test whose days are
    fixed puts it days before its first one."""
    path = os.path.join(e.store, ".state", "blocks", rid + ".json")
    state = json.loads(read(path))
    state["checked"] = when
    open(path, "w", encoding="utf-8").write(json.dumps(state, ensure_ascii=False, indent=1, sort_keys=True) + "\n")


def growth_blocks(*regions):
    return "# Context blocks — Zorg Growth\n\n" + "\n\n".join(regions) + "\n"


def sha_of(text):
    return cs_mod.sha_text(cb_mod.norm(text))


fake = FakeMcp(tree={GROWTH_PATH: GROWTH_TEXT})
try:
    with tempfile.TemporaryDirectory() as d:
        e = repos_env(d, fake.url)
        set_sync(e, "zorg-growth", "daily")
        set_sync(e, "zorg-dead", "off")                 # zorg-core has no sync key: off too
        run_ok(e, "migrate", "--apply")
        run_ok(e, "provider", "adopt", "zorg-growth", "--apply")
        checked_at(e, "zorg-growth", DAY0)
        rc, out, res = run_ok(e, "provider", "sync", "--if-due", "--now", "2026-10-15T08:00:00+03:00")
        check("--if-due a day after the adopt's check (23 h): not due — an adopt and an apply count as a check",
              rc == 0 and res == {"command": "provider", "action": "sync", "synced": [], "ok": True}, (rc, out[-300:]))
        core_before = block_state(e, "zorg-core")
        new_metrics = G_METRICS.replace("v=0.1", "v=0.2").replace("weekly active shoppers", "monthly active shoppers")
        fake.tree[GROWTH_PATH] = GROWTH_TEXT.replace(G_METRICS, new_metrics)
        cache = os.path.join(e.home, ".grow-pm", ".ctx-summary.json")
        if os.path.exists(cache):
            os.remove(cache)
        rc, out, res = run_ok(e, "provider", "sync", "--if-due", "--now", DAY1)
        check("first run: due, the core's change applied, one sentence for the skill",
              rc == 0 and res["synced"] == ["zorg-growth"] and "Ядро оновило 1 блок у zorg-growth" in out, (rc, out[-700:]))
        check("…only the registration with sync: daily: sync: off and a registration without the key are not touched",
              [r["repo"] for r in res["results"]] == ["zorg-growth"] and block_state(e, "zorg-core") == core_before
              and block_state(e, "zorg-dead") is None, res.get("results"))
        r0 = res["results"][0]
        check("…a run that went ahead says nothing of skipping", "skipped" not in res, res)
        check("…the result: changed, 1 updated, every key of the contract", set(r0) == SYNC_KEYS and r0["outcome"] == "changed"
              and r0["updated"] == 1 and r0["added"] == 0 and r0["removed"] == 0 and r0["at"] == DAY1
              and r0["report"] == "_System/context/sync/2026-10-16.md"
              and r0["snapshot"] and os.path.isdir(r0["snapshot"]), r0)
        check("…the region is the core's text in both copies; one journal line, op provider-sync, naming the text taken",
              region_in(read(e.ctx), "zorg-growth", "growth-metrics") == new_metrics
              and region_in(read(e.mirror), "zorg-growth", "growth-metrics") == new_metrics
              and last_journal(e)["op"] == "provider-sync" and last_journal(e)["taken"] == {"growth-metrics": sha_of(new_metrics)}
              and last_journal(e)["snapshot"] == r0["snapshot"], last_journal(e))
        st = block_state(e, "zorg-growth")
        check("…the state: the check and the attempt at the pass's time, sync_result as in the result",
              st["checked"] == DAY1 and st["sync_attempt"] == DAY1
              and st["sync_result"] == {k: v for k, v in r0.items() if k != "repo"}, st)
        check("…a sync that synced saves the digest's summary (v3.13.1)", os.path.isfile(cache))
        j_before, snaps_before, state_before = journal_len(e), snapshot_names(e), read(e.store, ".state", "blocks", "zorg-growth.json")
        os.remove(cache)
        seen = len(fake.seen)
        rc, out, res = run_ok(e, "provider", "sync", "--if-due", "--now", DAY1_PLUS_1H)
        check("not due an hour later: nothing printed but CTX_RESULT, nothing written",
              res["synced"] == [] and out.strip().count("\n") == 0 and journal_len(e) == j_before, (rc, out))
        check("…exit 0, the result is the short one, no request to the server, not a byte in the state, no snapshot",
              rc == 0 and res == {"command": "provider", "action": "sync", "synced": [], "ok": True} and len(fake.seen) == seen
              and read(e.store, ".state", "blocks", "zorg-growth.json") == state_before and snapshot_names(e) == snaps_before, res)
        check("…and no summary saved: nothing was synced", not os.path.exists(cache))


        fake.close()                                     # VPN off
        t0 = time.time()
        rc, out, res = run_ok(e, "provider", "sync", "--if-due", "--now", DAY2_PLUS_1M)
        took = time.time() - t0
        check("unreachable: within the budget, outcome unreachable, retried no sooner than an hour", rc == 0 and res["synced"] == ["zorg-growth"]
              and res["results"][0]["outcome"] == "unreachable" and took < 25, (rc, round(took, 2), out[-500:]))
        st = block_state(e, "zorg-growth")
        check("…only the attempt is recorded: checked stays the last successful check, the reason is said, no sentence",
              st["checked"] == DAY1 and st["sync_attempt"] == DAY2_PLUS_1M and st["sync_result"]["outcome"] == "unreachable"
              and st["sync_result"]["reason"] and "Ядро оновило" not in out and journal_len(e) == j_before, (st, out[-300:]))
        check("…and not again 30 minutes later", run_ok(e, "provider", "sync", "--if-due", "--now", DAY2_PLUS_31M)[2]["synced"] == [])
        rc, out, res = run_ok(e, "provider", "sync", "--if-due", "--now", DAY2_PLUS_2H)
        check("…but again two hours later (still unreachable)", res["synced"] == ["zorg-growth"]
              and res["results"][0]["outcome"] == "unreachable" and block_state(e, "zorg-growth")["sync_attempt"] == DAY2_PLUS_2H, res)

        rc, out, res = run_ok(e, "provider", "sync", "zorg-core")
        check("naming a repository whose sync is off: a usage error (exit 3) — the daily sync touches only sync: daily",
              rc == 3 and "sync: daily" in out and block_state(e, "zorg-core") == core_before, (rc, out[-300:]))
        rc, out, res = run_ok(e, "provider", "sync", "--now", "tomorrow morning")
        check("--now that is no ISO time: exit 3", rc == 3 and "--now" in out, (rc, out[-300:]))
        rc, out, res = run_ok(e, "provider", "sync", "--store", e.store)
        check("--store is refused: the sync is a writing command", rc == 3 and "--store is for read commands only" in out, (rc, out[-300:]))
        with open(os.path.join(e.home, ".grow-pm", "providers", "zorg-growth.yaml"), "a", encoding="utf-8") as f:
            f.write("status: paused\n")
        growth_state = block_state(e, "zorg-growth")
        rc, out, res = run_ok(e, "provider", "sync", "zorg-growth", "--now", DAY2_PLUS_2H)
        check("naming a paused repository (sync: daily, status: paused): exit 3, nothing synced",
              rc == 3 and "paused" in out and block_state(e, "zorg-growth") == growth_state, (rc, out[-300:]))
finally:
    fake.close()

with FakeMcp(tree={GROWTH_PATH: GROWTH_TEXT}) as fake:   # the lock, a guard that refuses, an import conflict, one repository down
    with tempfile.TemporaryDirectory() as d:
        e = repos_env(d, fake.url)
        set_sync(e, "zorg-growth", "daily")
        set_sync(e, "zorg-dead", "daily")
        run_ok(e, "migrate", "--apply")
        run_ok(e, "provider", "adopt", "zorg-growth", "--apply")
        new_metrics = G_METRICS.replace("v=0.1", "v=0.2").replace("weekly active shoppers", "monthly active shoppers")
        fake.tree[GROWTH_PATH] = GROWTH_TEXT.replace(G_METRICS, new_metrics)
        j, records, ctx_text, seen = journal_len(e), tree_of(os.path.join(e.store, "records")), read(e.ctx), len(fake.seen)
        state = read(e.store, ".state", "blocks", "zorg-growth.json")
        lockf = os.path.join(e.home, ".grow-pm", ".ctx.lock")
        open(lockf, "w").write(json.dumps({"pid": os.getpid(), "at": time.time()}))   # another session holds the lock
        try:
            t0 = time.time()
            rc, out, res = run_ok(e, "provider", "sync", "--now", DAY1)
            took = time.time() - t0
        finally:
            os.remove(lockf)
        check("a lock another session holds: skipped at once — nothing synced, nothing written, exit 0",
              rc == 0 and res["synced"] == [] and res["results"] == [] and journal_len(e) == j and read(e.ctx) == ctx_text
              and read(e.store, ".state", "blocks", "zorg-growth.json") == state and len(fake.seen) == seen and took < 10,
              (rc, round(took, 2), out[-400:]))
        check("…and CTX_RESULT says why: skipped busy", res.get("skipped") == "busy", res)

        real_guard = ctx_cli.Ctx.guard

        def refusing_guard(self):
            raise ctx_ops_mod.Refused("a registration could not be read: zorg-x.yaml — the provider boundary cannot be checked")

        ctx_cli.Ctx.guard = refusing_guard
        try:
            rc, out, res = in_process(e, "provider", "sync", "--now", DAY1)
        finally:
            ctx_cli.Ctx.guard = real_guard
        check("a guard that refuses (a registration still downloading) is a busy lock: nothing synced, nothing recorded, exit 0",
              rc == 0 and res["synced"] == [] and journal_len(e) == j and read(e.store, ".state", "blocks", "zorg-growth.json") == state
              and len(fake.seen) == seen, (rc, out[-400:]))
        check("…and CTX_RESULT says why: skipped guard: <why>",
              res.get("skipped") == "guard: a registration could not be read: zorg-x.yaml — the provider boundary cannot be checked", res)

        e.edit(e.ctx, "- **Jira Project Key:** PROJ\n", "- **Jira Project Key:** PROJ-HOME\n")
        e.edit(e.mirror, "- **Jira Project Key:** PROJ\n", "- **Jira Project Key:** PROJ-VAULT\n")
        rc, out, res = run_ok(e, "provider", "sync", "--now", DAY1)
        outcomes = {r["repo"]: r["outcome"] for r in (res or {}).get("results") or []}
        check("an import conflict (both copies edited differently): every repository import-conflict, the records unchanged, exit 0",
              rc == 0 and outcomes == {"zorg-dead": "import-conflict", "zorg-growth": "import-conflict"}
              and tree_of(os.path.join(e.store, "records")) == records and journal_len(e) == j, (rc, out[-500:]))
        st = block_state(e, "zorg-growth")
        check("…the core's change waits; the reason says `ctx sync` first; only the attempt is recorded",
              region_in(read(e.ctx), "zorg-growth", "growth-metrics") == G_METRICS and "ctx sync" in res["results"][0]["reason"]
              and st["sync_result"]["outcome"] == "import-conflict" and st["sync_attempt"] == DAY1
              and st["checked"] == json.loads(state)["checked"] and "Ядро оновило" not in out, (st, res["results"]))
        e.edit(e.mirror, "PROJ-VAULT", "PROJ-HOME")      # the two copies agree again: the import goes through
        rc, out, res = run_ok(e, "provider", "sync", "--now", DAY1)
        outcomes = {r["repo"]: r["outcome"] for r in res["results"]}
        check("one repository unreachable does not stop the next: zorg-dead unreachable, zorg-growth changed (the edit imported first)",
              rc == 0 and outcomes == {"zorg-dead": "unreachable", "zorg-growth": "changed"}
              and region_in(read(e.ctx), "zorg-growth", "growth-metrics") == new_metrics and "PROJ-HOME" in e.record("product.zorg-app")
              and "Ядро оновило 1 блок у zorg-growth" in out
              and not [l for l in out.splitlines() if "zorg-dead" in l and not l.startswith("CTX_RESULT ")], (rc, outcomes, out[-600:]))
        j, snaps = journal_len(e), snapshot_names(e)
        rc, out, res = run_ok(e, "provider", "sync", "--now", DAY1_PLUS_1H)
        outcomes = {r["repo"]: r["outcome"] for r in res["results"]}
        check("without --if-due the sync runs whatever the time: nothing new in the core → no-changes, no sentence, no journal line",
              rc == 0 and res["synced"] == ["zorg-dead", "zorg-growth"] and outcomes == {"zorg-dead": "unreachable", "zorg-growth": "no-changes"}
              and "Ядро оновило" not in out and journal_len(e) == j and snapshot_names(e) == snaps, (rc, out[-500:]))
        check("…the check moved to its time", block_state(e, "zorg-growth")["checked"] == DAY1_PLUS_1H
              and block_state(e, "zorg-growth")["sync_result"]["outcome"] == "no-changes", block_state(e, "zorg-growth"))

with tempfile.TemporaryDirectory() as d:                 # a provider-registration/1 (a folder) with sync: daily; two removals held
    e = repos_env(d, "http://127.0.0.1:9/mcp", core_extra="sync: daily\n")
    core = os.path.join(d, "ZorgCore")
    blocks_file = os.path.join(core, CORE_BLOCKS)
    run_ok(e, "migrate", "--apply")
    run_ok(e, "provider", "adopt", "zorg-core", "--apply")
    checked_at(e, "zorg-core", DAY0)
    rc, out, res = run_ok(e, "provider", "sync", "--if-due", "--now", DAY1)
    r0 = (res or {}).get("results", [{}])[0]
    check("a provider-registration/1 with sync: daily is synced: the core's new block is added",
          rc == 0 and res["synced"] == ["zorg-core"] and r0.get("outcome") == "changed" and r0.get("added") == 1
          and region_in(read(e.ctx), "zorg-core", "product") and "Ядро оновило 1 блок у zorg-core" in out, (rc, out[-500:]))
    pristine = read(blocks_file)
    open(blocks_file, "w", encoding="utf-8", newline="").write(
        pristine.replace(region_in(pristine, "zorg-core", "scope") + "\n\n", "").replace(region_in(pristine, "zorg-core", "teams"), ""))
    j, ctx_text = journal_len(e), read(e.ctx)
    rc, out, res = run_ok(e, "provider", "sync", "--if-due", "--now", DAY2)
    r0 = (res or {}).get("results", [{}])[0]
    check("two blocks the core removed: outcome held, both regions in place, nothing written",
          rc == 0 and r0.get("outcome") == "held" and r0.get("held") == ["scope", "teams"] and read(e.ctx) == ctx_text
          and region_in(read(e.ctx), "zorg-core", "scope") and region_in(read(e.ctx), "zorg-core", "teams") and journal_len(e) == j
          and "Ядро оновило" not in out, (rc, out[-500:], r0))
    check("…a successful check: checked moves, so the next try is a day later", block_state(e, "zorg-core")["checked"] == DAY2
          and block_state(e, "zorg-core")["sync_result"]["outcome"] == "held"
          and run_ok(e, "provider", "sync", "--if-due", "--now", DAY2_PLUS_2H)[2]["synced"] == [], block_state(e, "zorg-core"))
    open(blocks_file, "w", encoding="utf-8", newline="").write(pristine.replace(region_in(pristine, "zorg-core", "scope"),
                                                                             region_in(pristine, "zorg-core", "teams").replace("id=teams", "id=other")))
    rc, out, res = run_ok(e, "provider", "sync", "--now", DAY2)
    check("…a lone removal goes through (scope gone from the core, no edit of yours)",
          (res or {}).get("results", [{}])[0].get("outcome") == "changed" and (res or {}).get("results", [{}])[0].get("removed") == 1
          and region_in(read(e.ctx), "zorg-core", "scope") is None, (rc, out[-500:]))

with FakeMcp(tree={GROWTH_PATH: GROWTH_TEXT}) as fake:   # end to end: plan → decide → apply, ⚠ kept yours, + added, ~ updated
    with tempfile.TemporaryDirectory() as d:
        e = repos_env(d, fake.url)
        set_sync(e, "zorg-growth", "daily")
        run_ok(e, "migrate", "--apply")
        run_ok(e, "provider", "adopt", "zorg-growth", "--apply")
        edit_both(e, "- **North star:** weekly active shoppers\n", "- **North star:** weekly active shoppers (mine)\n")
        core_metrics = G_METRICS.replace("v=0.1", "v=0.2").replace("weekly active shoppers", "weekly buyers")
        core_team = G_TEAM.replace("v=0.1", "v=0.2").replace("- **Growth squad:** Alpha", "- **Growth squad:** Alpha Prime")
        fake.tree[GROWTH_PATH] = growth_blocks(core_metrics, core_team, G_OKR)
        mine_metrics = G_METRICS.replace("weekly active shoppers", "weekly active shoppers (mine)")
        rc, out, res = run_ok(e, "provider", "sync", "--now", DAY1)
        r0 = (res or {}).get("results", [{}])[0]
        jl = last_journal(e)
        check("end to end, one pass: ⚠ kept yours, + added, ~ updated — outcome changed, the counts",
              rc == 0 and r0.get("outcome") == "changed" and r0.get("kept_yours") == ["growth-metrics"] and r0.get("updated") == 1
              and r0.get("added") == 1 and r0.get("removed") == 0 and r0.get("took_rule") == [] and r0.get("awaiting") == [], (rc, r0, out[-600:]))
        check("…the records, both copies: your metrics, the core's team, the new block",
              all(region_in(read(p), "zorg-growth", "growth-metrics") == mine_metrics and region_in(read(p), "zorg-growth", "team") == core_team
                  and region_in(read(p), "zorg-growth", "growth-okr") == G_OKR for p in (e.ctx, e.mirror)), read(e.ctx)[-1500:])
        check("…the journal: one provider-sync line with the decisions, `taken` naming the core's texts written (not yours)",
              jl["op"] == "provider-sync" and jl["source"] == "repo:zorg-growth"
              and jl["decisions"] == {"growth-metrics": "⚠ mine", "team": "~", "growth-okr": "+"}
              and jl["taken"] == {"team": sha_of(core_team), "growth-okr": sha_of(G_OKR)} and jl["snapshot"] == r0.get("snapshot"), jl)
        check("…the sentence: two blocks, one conflict kept yours", "Ядро оновило 2 блоки у zorg-growth, конфліктів 1 (лишено твоє)" in out, out[-400:])
        rc, out, res = run_ok(e, "provider", "plan", "zorg-growth")
        check("…the next plan: ✎ for yours (its base is the core's text now), = for the others — nothing asks again",
              signs_in(res) == {"growth-metrics": "✎", "team": "=", "growth-okr": "="} and res["questions"] == 0, out[-500:])
        j, snaps = journal_len(e), snapshot_names(e)
        rc, out, res = run_ok(e, "provider", "sync", "--now", DAY2)
        check("…a second sync with nothing new is idempotent: no-changes, no journal line, no snapshot, no sentence",
              rc == 0 and res["results"][0]["outcome"] == "no-changes" and journal_len(e) == j and snapshot_names(e) == snaps
              and "Ядро оновило" not in out, (rc, out[-400:]))

with FakeMcp(tree={GROWTH_PATH: GROWTH_TEXT}) as fake:   # the hard bound: a fetch that never returns costs the budget, not the skill
    with tempfile.TemporaryDirectory() as d:
        e = repos_env(d, fake.url, core_extra="sync: daily\n")
        set_sync(e, "zorg-growth", "daily")
        run_ok(e, "migrate", "--apply")
        core_state = block_state(e, "zorg-core")
        release = threading.Event()
        real_fetch, real_budget = crp_mod.fetch, sy_mod.BUDGET_S

        hung = []
        real_min = sy_mod.APPLY_MIN_S

        def hanging_fetch(repo, **kw):                   # zorg-core first (registration order): a DNS lookup that never returns
            if repo["id"] == "zorg-core":
                hung.append(repo["id"])
                release.wait(60)
            return real_fetch(repo, **kw)

        # a 2 s budget (1 s of work after the reserve): the 3 s floor for a plan is lowered so that the fetch starts at all
        crp_mod.fetch, sy_mod.BUDGET_S, sy_mod.APPLY_MIN_S = hanging_fetch, 2.0, 0.5
        try:
            t0 = time.time()
            rc, out, res = in_process(e, "provider", "sync", "--now", DAY1)
            took = time.time() - t0
        finally:
            crp_mod.fetch, sy_mod.BUDGET_S, sy_mod.APPLY_MIN_S = real_fetch, real_budget, real_min
            release.set()
        outcomes = {r["repo"]: r["outcome"] for r in (res or {}).get("results") or []}
        check("a fetch that never returns: timeout within the budget, and the repository after it times out too (no time left)",
              rc == 0 and outcomes == {"zorg-core": "timeout", "zorg-growth": "timeout"} and hung == ["zorg-core"] and took < 8,
              (rc, round(took, 2), outcomes, hung))
        st = block_state(e, "zorg-core") or {}
        check("…the attempt is recorded (retry in an hour), the check is not", st.get("sync_attempt") == DAY1
              and st.get("checked") == (core_state or {}).get("checked") and st.get("sync_result", {}).get("outcome") == "timeout"
              and (block_state(e, "zorg-growth") or {}).get("sync_attempt") == DAY1, st)

        def deadline_fetch(repo, **kw):                  # the client gave up at the deadline: its error says so
            if repo["id"] == "zorg-growth":
                return {"source": None, "version": None, "blocks": {}, "namespace": repo["namespace"], "team": None, "team_source": None,
                        "team_error": None, "error": "MCP: " + cm_mod.DEADLINE, "unsound": None, "checked": kw.get("now")}
            return real_fetch(repo, **kw)

        crp_mod.fetch = deadline_fetch
        try:
            rc, out, res = in_process(e, "provider", "sync", "--now", DAY2)
        finally:
            crp_mod.fetch = real_fetch
        outcomes = {r["repo"]: r["outcome"] for r in (res or {}).get("results") or []}
        check("a fetch error that says the deadline was reached is a timeout, not unreachable; the other repository is synced",
              rc == 0 and outcomes.get("zorg-growth") == "timeout" and outcomes.get("zorg-core") in ("changed", "no-changes"), (rc, outcomes))

# --- v3.14.0 Task 4 fix round 1: a broken source, the due check under the lock, the 3 s floor, the error outcome
DAY1_PLUS_2H = "2026-10-16T11:00:00+03:00"
DAY1_PLUS_25H = "2026-10-17T10:00:00+03:00"

with tempfile.TemporaryDirectory() as d:                 # an empty or cut blocks file in the core folder: broken, a check
    e = repos_env(d, "http://127.0.0.1:9/mcp", core_extra="sync: daily\n")
    blocks_file = os.path.join(d, "ZorgCore", CORE_BLOCKS)
    pristine = read(blocks_file)
    run_ok(e, "migrate", "--apply")
    run_ok(e, "provider", "adopt", "zorg-core", "--apply")
    for label, text, said in (("an empty blocks file", "", "holds no zorg-core block"),
                              ("a blocks file cut inside a block", pristine[:pristine.index("<!-- zorg-core:end id=teams -->")],
                               "cut at block teams")):
        checked_at(e, "zorg-core", DAY0)
        open(blocks_file, "w", encoding="utf-8", newline="").write(text)
        j, ctx_text = journal_len(e), read(e.ctx)
        rc, out, res = run_ok(e, "provider", "sync", "--if-due", "--now", DAY1)
        r0 = ((res or {}).get("results") or [{}])[0]
        st = block_state(e, "zorg-core")
        check("%s: broken — a successful check (checked = now), the reason says why, nothing written" % label,
              rc == 0 and r0.get("outcome") == "broken" and said in (r0.get("reason") or "") and st["checked"] == DAY1
              and st["sync_attempt"] == DAY1 and st["sync_result"]["outcome"] == "broken" and journal_len(e) == j and read(e.ctx) == ctx_text
              and "Ядро оновило" not in out, (rc, r0, out[-300:]))
        check("…not due 2 h later (a broken source is not retried every hour)",
              run_ok(e, "provider", "sync", "--if-due", "--now", DAY1_PLUS_2H)[2]["synced"] == [])
        rc, out, res = run_ok(e, "provider", "sync", "--if-due", "--now", DAY1_PLUS_25H)
        check("…due again 25 h later", res["synced"] == ["zorg-core"] and res["results"][0]["outcome"] == "broken", res)
    open(blocks_file, "w", encoding="utf-8", newline="").write(pristine)

with FakeMcp(tree={GROWTH_PATH: GROWTH_TEXT}) as fake:   # two sessions: the due check is made again under the lock
    with tempfile.TemporaryDirectory() as d:
        e = repos_env(d, fake.url)
        set_sync(e, "zorg-growth", "daily")
        run_ok(e, "migrate", "--apply")
        run_ok(e, "provider", "adopt", "zorg-growth", "--apply")
        checked_at(e, "zorg-growth", DAY0)
        fake.tree[GROWTH_PATH] = GROWTH_TEXT.replace(G_METRICS, G_METRICS.replace("v=0.1", "v=0.2").replace("weekly", "daily"))
        c = ctx_cli.Ctx(ctx_cli.build_parser().parse_args(["provider", "sync", "--home", e.home, "--context", e.ctx]))
        picked = sy_mod.pick_due(c.store, [r for r in crp_mod.load_repos(c.text, c.home) if r["sync"] == "daily"], DAY1)
        rc, out, res = run_ok(e, "provider", "sync", "--if-due", "--now", DAY1)      # the other session, between our check and our lock
        state, j, seen = read(e.store, ".state", "blocks", "zorg-growth.json"), journal_len(e), len(fake.seen)
        with cs_mod.guard_roots(ctx_ops_mod.allowed_roots(c.home, c.text)):
            again = sy_mod.run(c, picked, DAY1, time.monotonic() + 20, only_due=True)
        check("--if-due was due before the lock; the other session synced meanwhile: under the lock it is not due — [], no second pass",
              [r["id"] for r in picked] == ["zorg-growth"] and res["results"][0]["outcome"] == "changed" and again == []
              and read(e.store, ".state", "blocks", "zorg-growth.json") == state and journal_len(e) == j and len(fake.seen) == seen,
              (picked and [r["id"] for r in picked], again))
        check("…its sync_result stays the first pass's (changed), not overwritten by no-changes",
              block_state(e, "zorg-growth")["sync_result"]["outcome"] == "changed")

with FakeMcp(tree={GROWTH_PATH: GROWTH_TEXT}) as fake:   # the 3 s floor, and the error outcome (a pass, the import)
    with tempfile.TemporaryDirectory() as d:
        e = repos_env(d, fake.url, core_extra="sync: daily\n")
        set_sync(e, "zorg-growth", "daily")
        blocks_file = os.path.join(d, "ZorgCore", CORE_BLOCKS)
        run_ok(e, "migrate", "--apply")
        run_ok(e, "provider", "adopt", "zorg-core", "--apply")
        run_ok(e, "provider", "adopt", "zorg-growth", "--apply")
        change(blocks_file, SCOPE_04, SCOPE_05)          # an apply would write
        check("the floor is 3 s: no plan and no write start with less of the budget left", sy_mod.APPLY_MIN_S == 3)
        fetched = []

        def slow_fetch(repo, **kw):                      # a fetch that answers, but late: less than 3 s of the budget is left
            fetched.append(repo["id"])
            time.sleep(2.5)
            return real_fetch(repo, **kw)

        records, j, core_state = tree_of(os.path.join(e.store, "records")), journal_len(e), block_state(e, "zorg-core")
        real_fetch, real_budget = crp_mod.fetch, sy_mod.BUDGET_S
        crp_mod.fetch, sy_mod.BUDGET_S = slow_fetch, 6.0
        try:
            rc, out, res = in_process(e, "provider", "sync", "zorg-core", "--now", DAY1)
        finally:
            crp_mod.fetch, sy_mod.BUDGET_S = real_fetch, real_budget
        r0 = ((res or {}).get("results") or [{}])[0]
        st = block_state(e, "zorg-core")
        check("a fetch that leaves less than 3 s: timeout, nothing planned or written (records, journal, the check)",
              rc == 0 and fetched == ["zorg-core"] and r0.get("outcome") == "timeout" and "nothing written" in (r0.get("reason") or "")
              and "once its last 1 s, kept for writing down the results, is set aside" in (r0.get("reason") or "")
              and tree_of(os.path.join(e.store, "records")) == records and journal_len(e) == j and st["checked"] == core_state["checked"]
              and st["sync_attempt"] == DAY1, (rc, fetched, r0))

        real_plan = cb_mod.plan

        def failing_plan(store, copies, repo, fetched, now, all_=False):
            if repo["id"] == "zorg-core":
                raise RuntimeError("boom in the plan")
            return real_plan(store, copies, repo, fetched, now, all_=all_)

        cb_mod.plan = failing_plan
        try:
            rc, out, res = in_process(e, "provider", "sync", "--now", DAY1)
        finally:
            cb_mod.plan = real_plan
        by = {r["repo"]: r for r in (res or {}).get("results") or []}
        st = block_state(e, "zorg-core")
        check("an unexpected failure in a pass: outcome error with its message, the attempt recorded, the check unchanged",
              rc == 0 and by.get("zorg-core", {}).get("outcome") == "error" and by["zorg-core"]["reason"] == "boom in the plan"
              and st["checked"] == core_state["checked"] and st["sync_attempt"] == DAY1 and st["sync_result"]["outcome"] == "error"
              and tree_of(os.path.join(e.store, "records")) == records, (rc, by))
        check("…and the next repository is synced all the same", by.get("zorg-growth", {}).get("outcome") in ("changed", "no-changes"), by)

        real_import = ctx_cli.Ctx.import_first

        def failing_import(self):
            raise cs_mod.StoreError("not available locally: product.zorg-app.md did not load within 0.4 s")

        ctx_cli.Ctx.import_first = failing_import
        try:
            rc, out, res = in_process(e, "provider", "sync", "--now", DAY2)
        finally:
            ctx_cli.Ctx.import_first = real_import
        outcomes = {r["repo"]: r["outcome"] for r in (res or {}).get("results") or []}
        reasons = {r["repo"]: r["reason"] for r in (res or {}).get("results") or []}
        check("an import that fails for the store (not a conflict): error, reason store: <message>, records unchanged",
              rc == 0 and outcomes == {"zorg-core": "error", "zorg-growth": "error"}
              and reasons["zorg-core"].startswith("store: not available locally: product.zorg-app.md")
              and tree_of(os.path.join(e.store, "records")) == records and block_state(e, "zorg-core")["sync_attempt"] == DAY2
              and block_state(e, "zorg-core")["checked"] == core_state["checked"], (rc, outcomes, reasons))

# --- v3.14.0 Task 4 fix round 2: an endpoint-only registration's bad note is broken; a lock that cannot be taken; a fetch that raises
with FakeMcp(tree={GROWTH_PATH: GROWTH_TEXT}) as fake:
    with tempfile.TemporaryDirectory() as d:
        e = repos_env(d, fake.url)
        reg = os.path.join(e.home, ".grow-pm", "providers", "zorg-growth.yaml")
        text = read(reg)
        assert "blocks_source: mcp\n" in text
        open(reg, "w", encoding="utf-8").write(text.replace("blocks_source: mcp\n", "") + "sync: daily\n")   # connect-steps' shape
        run_ok(e, "migrate", "--apply")
        run_ok(e, "provider", "adopt", "zorg-growth", "--apply")
        checked_at(e, "zorg-growth", DAY0)
        fake.tree[GROWTH_PATH] = ""                      # the server serves an empty note
        j, ctx_text = journal_len(e), read(e.ctx)
        rc, out, res = run_ok(e, "provider", "sync", "--if-due", "--now", DAY1)
        r0 = ((res or {}).get("results") or [{}])[0]
        st = block_state(e, "zorg-growth")
        check("an endpoint-only registration (auto, no core folder) whose server serves an empty note: broken, checked moves",
              rc == 0 and r0.get("outcome") == "broken" and "holds no zorg-growth block" in (r0.get("reason") or "")
              and st["checked"] == DAY1 and st["sync_attempt"] == DAY1 and journal_len(e) == j and read(e.ctx) == ctx_text, (rc, r0))
        check("…not due 2 h later", run_ok(e, "provider", "sync", "--if-due", "--now", DAY1_PLUS_2H)[2]["synced"] == [])

        real_lock = ctx_ops_mod.lock

        def unwritable_lock(home, stale_s=120):
            raise PermissionError(13, "Permission denied", os.path.join(home, ".grow-pm", ".ctx.lock"))

        ctx_ops_mod.lock = unwritable_lock
        try:
            rc, out, res = in_process(e, "provider", "sync", "--now", DAY2)
        finally:
            ctx_ops_mod.lock = real_lock
        check("a lock that cannot be taken (~/.grow-pm not writable) is not 'busy': skipped lock: <why>, nothing synced, exit 0",
              rc == 0 and res["synced"] == [] and (res.get("skipped") or "").startswith("lock: ") and "Permission denied" in res["skipped"]
              and block_state(e, "zorg-growth")["sync_attempt"] == DAY1, res)

        fake.tree[GROWTH_PATH] = GROWTH_TEXT
        real_fetch = crp_mod.fetch

        def raising_fetch(repo, **kw):                   # fetch is documented never to raise: one that does is a bug, not a VPN
            raise ValueError("a bug in the fetch")

        crp_mod.fetch = raising_fetch
        try:
            rc, out, res = in_process(e, "provider", "sync", "--now", DAY2)
        finally:
            crp_mod.fetch = real_fetch
        r0 = ((res or {}).get("results") or [{}])[0]
        st = block_state(e, "zorg-growth")
        check("a fetch that raises: error (not unreachable) with its message, the attempt recorded, the check unchanged",
              rc == 0 and r0.get("outcome") == "error" and "ValueError: a bug in the fetch" in (r0.get("reason") or "")
              and st["checked"] == DAY1 and st["sync_attempt"] == DAY2, (rc, r0))

# --- v3.14.0 Task 5: the sync's report — every decision, both texts of a conflict, how to take it back
def report_of(e, day):
    path = os.path.join(e.store, "sync", day + ".md")
    return read(path) if os.path.isfile(path) else None


def unbase(e, repo, bid):
    """Forget the base of one block (a block of a context that came from somewhere else): the plan shows a '?' for it."""
    path = os.path.join(e.store, ".state", "blocks", repo + ".json")
    state = json.loads(read(path))
    state["blocks"][bid]["base_sha"], state["blocks"][bid]["bases"] = None, []
    open(path, "w", encoding="utf-8").write(json.dumps(state, ensure_ascii=False, indent=1, sort_keys=True) + "\n")


def table_rows(text):
    return [l for l in text.splitlines() if l.startswith("| `")]


with FakeMcp(tree={GROWTH_PATH: GROWTH_TEXT}) as fake:   # one pass: ⚠ kept yours, ~ updated, + added — then a second the same day
    with tempfile.TemporaryDirectory() as d:
        e = repos_env(d, fake.url)
        set_sync(e, "zorg-growth", "daily")
        run_ok(e, "migrate", "--apply")
        run_ok(e, "provider", "adopt", "zorg-growth", "--apply")
        edit_both(e, "- **North star:** weekly active shoppers\n", "- **North star:** weekly active shoppers (mine)\n")
        core_metrics = G_METRICS.replace("v=0.1", "v=0.2").replace("weekly active shoppers", "weekly buyers")
        core_team = G_TEAM.replace("v=0.1", "v=0.2").replace("- **Growth squad:** Alpha", "- **Growth squad:** Alpha Prime")
        fake.tree[GROWTH_PATH] = growth_blocks(core_metrics, core_team, G_OKR)
        rc, out, res = run_ok(e, "provider", "sync", "--now", DAY1)
        r0 = (res or {}).get("results", [{}])[0]
        rep = report_of(e, "2026-10-16") or ""
        rows = table_rows(rep)
        okr_host = block_state(e, "zorg-growth")["blocks"]["growth-okr"]["host"]
        check("the pass writes the day's report in the vault: its path is in the result, in the state's sync_result and in the sentence",
              rc == 0 and r0.get("report") == "_System/context/sync/2026-10-16.md" and rep
              and block_state(e, "zorg-growth")["sync_result"]["report"] == r0["report"]
              and "Ядро оновило 2 блоки у zorg-growth, конфліктів 1 (лишено твоє) — звіт: _System/context/sync/2026-10-16.md" in out,
              (rc, r0, out[-500:]))
        check("…a file with frontmatter (type system, kind context-sync, date, repos) and the title `# Синк контексту — YYYY-MM-DD`",
              rep.startswith("---\ntype: system\nkind: context-sync\ndate: 2026-10-16\nrepos: [zorg-growth]\n---\n\n# Синк контексту — 2026-10-16\n\n"), rep[:300])
        check("…the section: `## <id> · HH:MM · джерело <label> · ядро v<v> · база v<a> → v<b>` (the version the pass moved the bases to), "
              "each version as code",
              re.search(r"^## zorg-growth · 09:00 · джерело .+ · ядро v`[^`\s]+` · база v`0\.1` → v`0\.2`$", rep, re.M), rep[:400])
        check("…three rows: ⚠ kept yours, ~ updated, + added — each in the cascade's words, with the record it is in",
              len(rows) == 3 and "| Блок | Знак | Рішення | Чому | Запис |" in rep
              and "`growth-metrics`" in rows[0] and "⚠" in rows[0] and "змінили обидва → лишено твоє: блок не є правилом ядра" in rows[0]
              and "`team`" in rows[1] and "~" in rows[1] and "текст ядра" in rows[1]
              and "`growth-okr`" in rows[2] and "новий блок у ядрі → додано" in rows[2] and "`%s`" % okr_host in rows[2], rows)
        check("…the conflict: its own part with BOTH texts (yours as you wrote it, the core's as it is now)",
              "### Конфлікт: `growth-metrics` — лишено твоє" in rep and "weekly active shoppers (mine)" in rep and "weekly buyers" in rep
              and "Твій текст (v`0.1`)" in rep and "Текст ядра (v`0.2`)" in rep, rep)
        check("…the command that takes the core's text, ready, and the way back with the snapshot folder as the last line",
              "Взяти текст ядра: ctx provider apply zorg-growth --choose growth-metrics=theirs" in rep.splitlines()
              and rep.rstrip("\n").splitlines()[-1] == "Відкотити цей прохід: ctx undo (знімок %s)" % r0["snapshot"], rep[-400:])
        check("…the command works: it takes the core's text for the ✎ the next plan shows",
              run_ok(e, "provider", "apply", "zorg-growth", "--choose", "growth-metrics=theirs")[0] == 0
              and region_in(read(e.ctx), "zorg-growth", "growth-metrics") == core_metrics, region_in(read(e.ctx), "zorg-growth", "growth-metrics"))
        check("a snapshot of the pass does not hold the report (it is in the vault, not in the store's state)",
              not any("2026-10-16.md" in n for _, _, fs in os.walk(r0["snapshot"]) for n in fs), r0["snapshot"])
        rc, out, res = run_ok(e, "status")
        check("`ctx status` does not list the report folder as a stray file", rc == 0 and res["stray"] == [] and "stray file" not in out, (res or {}).get("stray"))
        rc, out, res = run_ok(e, "validate")
        check("…nor does `ctx validate`: no warning or error names the folder or a stray file",
              not any("stray" in w or "2026-10-16.md" in w or "sync/" in w for w in res["warnings"] + res["errors"]), res)
        # the same day again: a second part of the same file
        before = rep
        core_team2 = core_team.replace("v=0.2", "v=0.3").replace("Alpha Prime", "Alpha Prime Two")
        fake.tree[GROWTH_PATH] = growth_blocks(core_metrics, core_team2, G_OKR)
        rc, out, res = run_ok(e, "provider", "sync", "--now", DAY1_PLUS_1H)
        r1 = (res or {}).get("results", [{}])[0]
        rep2 = report_of(e, "2026-10-16") or ""
        check("a second pass the same day appends a second part to the same file: the first part untouched, repos not doubled",
              r1.get("outcome") == "changed" and r1.get("report") == "_System/context/sync/2026-10-16.md"
              and rep2.startswith(before.rstrip("\n")) and rep2.count("\n## zorg-growth · ") == 2 and "## zorg-growth · 10:00 ·" in rep2
              and rep2.count("repos: [zorg-growth]") == 1 and len(table_rows(rep2)) == 4, (r1, rep2[-600:]))
        j, snaps = journal_len(e), snapshot_names(e)
        rc, out, res = run_ok(e, "provider", "sync", "--now", DAY2)
        check("a pass with no change writes no report: no file for the day, no report in the result or in the sentence",
              res["results"][0]["outcome"] == "no-changes" and res["results"][0]["report"] is None and report_of(e, "2026-10-17") is None
              and "звіт" not in out and os.listdir(os.path.join(e.store, "sync")) == ["2026-10-16.md"], (res["results"], out[-300:]))
        check("…and the sync_result of that pass names no report", block_state(e, "zorg-growth")["sync_result"]["report"] is None)
        rc, out, res = run_ok(e, "undo")
        check("`ctx undo` takes the records back and leaves the report where it is (it says how it was taken)",
              rc == 0 and report_of(e, "2026-10-16") is not None, (rc, out[-300:]))

with FakeMcp(tree={GROWTH_PATH: GROWTH_TEXT}) as fake:   # 100 lines on each side: 40 shown, then «… ще 60 рядків»
    with tempfile.TemporaryDirectory() as d:
        e = repos_env(d, fake.url)
        set_sync(e, "zorg-growth", "daily")
        run_ok(e, "migrate", "--apply")
        run_ok(e, "provider", "adopt", "zorg-growth", "--apply")
        edit_both(e, "- **North star:** weekly active shoppers\n", "".join("- mine %d\n" % i for i in range(1, 100)))
        long_core = G_METRICS.replace("v=0.1", "v=0.2").replace("- **North star:** weekly active shoppers\n",
                                                               "".join("- core %d\n" % i for i in range(1, 100)))
        fake.tree[GROWTH_PATH] = GROWTH_TEXT.replace(G_METRICS, long_core)
        rc, out, res = run_ok(e, "provider", "sync", "--now", DAY1)
        r0 = (res or {}).get("results", [{}])[0]
        rep = report_of(e, "2026-10-16") or ""
        check("a conflict whose texts are 100 lines each: 40 lines of each shown, line 41 not",
              r0.get("kept_yours") == ["growth-metrics"] and "- mine 39" in rep and "- mine 40" not in rep and "- core 39" in rep
              and "- core 40" not in rep, (r0, rep[-500:]))
        check("…`… ще 60 рядків` for each side: yours whole in the snapshot, the core's at the core",
              rep.count("… ще 60 рядків") == 2 and "… ще 60 рядків — повністю у знімку %s" % r0["snapshot"] in rep
              and "… ще 60 рядків — повністю у джерелі ядра" in rep, rep[-700:])
        snap_rec = [read(r0["snapshot"], "records", n) for n in os.listdir(os.path.join(r0["snapshot"], "records"))]
        check("…and it is true: the snapshot holds your whole text", any("- mine 99" in t for t in snap_rec))

with FakeMcp(tree={GROWTH_PATH: GROWTH_TEXT}) as fake:   # two repositories one day; a core rule overwrites yours; a ? waits
    with tempfile.TemporaryDirectory() as d:
        e = repos_env(d, fake.url, core_extra="sync: daily\n")
        set_sync(e, "zorg-growth", "daily")
        blocks_file = os.path.join(d, "ZorgCore", CORE_BLOCKS)
        run_ok(e, "migrate", "--apply")
        run_ok(e, "provider", "adopt", "zorg-core", "--apply")
        run_ok(e, "provider", "adopt", "zorg-growth", "--apply")
        edit_both(e, "The user works on Zorg App only.\n", "The user works on Zorg App, my way.\n")
        edit_both(e, "- Alpha, Beta\n", "- Alpha, Beta (my teams)\n")
        unbase(e, "zorg-core", "teams")
        change(blocks_file, SCOPE_04, "<!-- zorg-core:begin id=scope v=0.5 policy=rule -->\n### Scope of work\nThe user works on Zorg App and Zorg Lite.")
        change(blocks_file, "- Alpha, Beta\n<!-- zorg-core:end id=teams -->", "- Alpha, Beta, Gamma\n<!-- zorg-core:end id=teams -->")
        fake.tree[GROWTH_PATH] = growth_blocks(G_METRICS, G_TEAM.replace("v=0.1", "v=0.2").replace("Alpha", "Alpha Prime"))
        rc, out, res = run_ok(e, "provider", "sync", "--now", DAY1)
        by = {r["repo"]: r for r in (res or {}).get("results", [])}
        rep = report_of(e, "2026-10-16") or ""
        check("two repositories synced the same day: one file, the parts in registration order, both in `repos`",
              rc == 0 and by["zorg-core"]["outcome"] == "changed" and by["zorg-growth"]["outcome"] == "changed"
              and "repos: [zorg-core, zorg-growth]" in rep and rep.index("\n## zorg-core · ") < rep.index("\n## zorg-growth · ")
              and by["zorg-core"]["report"] == by["zorg-growth"]["report"] == "_System/context/sync/2026-10-16.md", (by, rep[:300]))
        check("a ⚠ of a core rule: the core's text won — and the report holds the text you wrote, which the record no longer does",
              by["zorg-core"]["took_rule"] == ["scope"] and "my way" not in read(e.ctx)
              and "правило ядра → текст ядра" in rep and "The user works on Zorg App, my way." in rep
              and "The user works on Zorg App and Zorg Lite." in rep and "### Конфлікт: `scope` — правило ядра, взято текст ядра" in rep, rep[:1800])
        check("…a ? waits: yours stays in the record, the report names the block once with both texts and both commands",
              by["zorg-core"]["awaiting"] == ["teams"] and "(my teams)" in read(e.ctx) and rep.count("### Конфлікт: `teams`") == 1
              and "- Alpha, Beta (my teams)" in rep and "- Alpha, Beta, Gamma" in rep
              and "Взяти текст ядра: ctx provider apply zorg-core --choose teams=theirs" in rep
              and "Лишити своє: ctx provider apply zorg-core --choose teams=mine" in rep, rep)
        check("…the table row of the ? says it waits", any("`teams`" in r and "?" in r and "чекає рішення" in r for r in table_rows(rep)), table_rows(rep))
        check("…the core part ends with its own way back; the growth part has its own",
              rep.count("Відкотити цей прохід: ctx undo (знімок ") == 2, rep[-300:])

with tempfile.TemporaryDirectory() as d:                 # the safeguard: held is reported once; a new set is reported again; old reports go
    e = repos_env(d, "http://127.0.0.1:9/mcp", core_extra="sync: daily\n")
    core = os.path.join(d, "ZorgCore")
    blocks_file = os.path.join(core, CORE_BLOCKS)
    run_ok(e, "migrate", "--apply")
    run_ok(e, "provider", "adopt", "zorg-core", "--apply")
    checked_at(e, "zorg-core", DAY0)
    today = datetime.date(2026, 10, 16)
    old91, old89 = [(today - datetime.timedelta(days=k)).isoformat() for k in (91, 89)]
    os.makedirs(os.path.join(e.store, "sync"))
    for day in (old91, old89):
        open(os.path.join(e.store, "sync", day + ".md"), "w", encoding="utf-8").write("an old report of %s\n" % day)
    open(os.path.join(e.store, "sync", "my-notes.md"), "w", encoding="utf-8").write("not a report\n")
    rc, out, res = run_ok(e, "provider", "sync", "--if-due", "--now", DAY1)
    trash = os.path.join(e.home, ".grow-pm", "trash")
    moved = [n for n in (os.listdir(trash) if os.path.isdir(trash) else []) if old91 in n]
    check("a report 91 days old goes to ~/.grow-pm/trash/ at the start of a sync, one 89 days old stays, a note of yours is not touched",
          rc == 0 and len(moved) == 1 and read(trash, moved[0]) == "an old report of %s\n" % old91
          and not os.path.exists(os.path.join(e.store, "sync", old91 + ".md")) and os.path.exists(os.path.join(e.store, "sync", old89 + ".md"))
          and os.path.exists(os.path.join(e.store, "sync", "my-notes.md")), (rc, moved, os.listdir(os.path.join(e.store, "sync"))))
    rc, out, res = run_ok(e, "list", "--trash")
    check("…the trash listing copes with a file that is no record", rc == 0, (rc, out[-300:]))
    pristine = read(blocks_file)
    open(blocks_file, "w", encoding="utf-8", newline="").write(
        pristine.replace(region_in(pristine, "zorg-core", "scope") + "\n\n", "").replace(region_in(pristine, "zorg-core", "teams"), ""))
    rc, out, res = run_ok(e, "provider", "sync", "--if-due", "--now", DAY2)
    r0 = (res or {}).get("results", [{}])[0]
    rep = report_of(e, "2026-10-17") or ""
    check("two blocks the core removed: outcome held, and a report says so — the blocks, the table, what to do",
          r0.get("outcome") == "held" and r0.get("report") == "_System/context/sync/2026-10-17.md"
          and "### Не застосовано: ядро прибрало 2 блоки" in rep and "- `scope`" in rep and "- `teams`" in rep
          and "запобіжник: ядро прибрало 2 блоки — не прибрано" in rep
          and "Подивитись: ctx provider plan zorg-core" in rep and "Прибрати руками: ctx provider apply zorg-core" in rep
          and rep.rstrip("\n").splitlines()[-1] == "Знімка цього проходу немає: відкочувати нічого.", (r0, rep))
    check("…held with nothing else written has no snapshot to point at", r0.get("snapshot") is None)
    rc, out, res = run_ok(e, "provider", "sync", "--now", DAY2_PLUS_2H)
    r1 = (res or {}).get("results", [{}])[0]
    check("the same safeguard going off again (same set, same reason): no part added; the result says no report",
          r1.get("outcome") == "held" and r1.get("report") is None and read(e.store, "sync", "2026-10-17.md") == rep, (r1, read(e.store, "sync", "2026-10-17.md")[-400:]))
    rc, out, res = run_ok(e, "provider", "sync", "--now", "2026-10-18T09:00:00+03:00")
    check("…not the next day either: no file for the day", res["results"][0]["outcome"] == "held" and res["results"][0]["report"] is None
          and report_of(e, "2026-10-18") is None, res["results"])
    check("…and the state still says held (the digest keeps its mark)", block_state(e, "zorg-core")["sync_result"]["outcome"] == "held"
          and block_state(e, "zorg-core")["sync_result"]["held"] == ["scope", "teams"])
    open(blocks_file, "w", encoding="utf-8", newline="").write(
        pristine.replace(region_in(pristine, "zorg-core", "product") + "\n\n", "").replace(region_in(pristine, "zorg-core", "teams"), ""))
    rc, out, res = run_ok(e, "provider", "sync", "--now", "2026-10-19T09:00:00+03:00")
    r2 = (res or {}).get("results", [{}])[0]
    rep3 = report_of(e, "2026-10-19") or ""
    check("a new set of blocks (product and teams, not scope and teams) is reported again",
          r2.get("outcome") == "held" and sorted(r2.get("held") or []) == ["product", "teams"] and r2.get("report") == "_System/context/sync/2026-10-19.md"
          and "- `product`" in rep3 and "- `teams`" in rep3, (r2, rep3[:300]))

with tempfile.TemporaryDirectory() as d:                 # broken, an import that needs ctx sync, an unexpected failure — each once
    e = repos_env(d, "http://127.0.0.1:9/mcp", core_extra="sync: daily\n")
    blocks_file = os.path.join(d, "ZorgCore", CORE_BLOCKS)
    pristine = read(blocks_file)
    run_ok(e, "migrate", "--apply")
    run_ok(e, "provider", "adopt", "zorg-core", "--apply")
    checked_at(e, "zorg-core", DAY0)
    open(blocks_file, "w", encoding="utf-8", newline="").write("")
    rc, out, res = run_ok(e, "provider", "sync", "--if-due", "--now", DAY1)
    r0 = (res or {}).get("results", [{}])[0]
    rep = report_of(e, "2026-10-16") or ""
    check("a broken source: a part with the reason, nothing written, the next check a day away",
          r0.get("outcome") == "broken" and r0.get("report") == "_System/context/sync/2026-10-16.md"
          and "## zorg-core · 09:00\n" in rep and "### Джерело ядра не прийнято" in rep and "holds no zorg-core block" in rep
          and "Знімка цього проходу немає" in rep and "Ядро оновило" not in out, (r0, rep))
    rc, out, res = run_ok(e, "provider", "sync", "--if-due", "--now", DAY1_PLUS_25H)
    check("…the same break the next day: no new part", res["results"][0]["outcome"] == "broken" and res["results"][0]["report"] is None
          and report_of(e, "2026-10-17") is None, res["results"])
    open(blocks_file, "w", encoding="utf-8", newline="").write(pristine)
    run_ok(e, "provider", "sync", "--now", "2026-10-17T12:00:00+03:00")
    e.edit(e.ctx, "- **Jira Project Key:** PROJ\n", "- **Jira Project Key:** PROJ-HOME\n")
    e.edit(e.mirror, "- **Jira Project Key:** PROJ\n", "- **Jira Project Key:** PROJ-VAULT\n")
    rc, out, res = run_ok(e, "provider", "sync", "--now", "2026-10-18T09:00:00+03:00")
    r1 = (res or {}).get("results", [{}])[0]
    rep = report_of(e, "2026-10-18") or ""
    check("an import that needs a decision: a part that says «спершу `ctx sync`», nothing written",
          r1.get("outcome") == "import-conflict" and r1.get("report") == "_System/context/sync/2026-10-18.md"
          and "### Спершу `ctx sync`" in rep and "Знімка цього проходу немає" in rep, (r1, rep))
    rc, out, res = run_ok(e, "provider", "sync", "--now", "2026-10-18T10:30:00+03:00")
    check("…asked again an hour later with the same conflict: no second part", res["results"][0]["outcome"] == "import-conflict"
          and res["results"][0]["report"] is None and read(e.store, "sync", "2026-10-18.md") == rep, res["results"])
    e.edit(e.mirror, "PROJ-VAULT", "PROJ-HOME")
    real_plan = cb_mod.plan

    def failing_plan2(store, copies, repo, fetched, now, all_=False):
        raise RuntimeError("boom in the plan")

    cb_mod.plan = failing_plan2
    try:
        rc, out, res = in_process(e, "provider", "sync", "--now", "2026-10-19T09:00:00+03:00")
        rc2, out2, res2 = in_process(e, "provider", "sync", "--now", "2026-10-19T11:00:00+03:00")
    finally:
        cb_mod.plan = real_plan
    r2 = (res or {}).get("results", [{}])[0]
    rep = report_of(e, "2026-10-19") or ""
    check("an unexpected failure: a part with the reason; the same failure two hours later adds none",
          r2.get("outcome") == "error" and r2.get("report") == "_System/context/sync/2026-10-19.md" and "### Несподівана помилка" in rep
          and "boom in the plan" in rep and res2["results"][0]["outcome"] == "error" and res2["results"][0]["report"] is None
          and rep.count("\n## zorg-core · ") == 1, (r2, rep, res2["results"]))
    check("…it does not claim there is nothing to undo (the pass may have written before it failed): the snapshot is unknown, `ctx status`",
          "Знімок цього проходу невідомий" in rep and "`ctx status`" in rep and "відкочувати нічого" not in rep.split("### Несподівана помилка")[1], rep)

with FakeMcp(tree={GROWTH_PATH: GROWTH_TEXT}) as fake:   # a text you rejected by undoing a pass is held, and the report says how to take it
    with tempfile.TemporaryDirectory() as d:
        e = repos_env(d, fake.url)
        set_sync(e, "zorg-growth", "daily")
        run_ok(e, "migrate", "--apply")
        run_ok(e, "provider", "adopt", "zorg-growth", "--apply")
        core_team = G_TEAM.replace("v=0.1", "v=0.2").replace("- **Growth squad:** Alpha", "- **Growth squad:** Alpha Prime")
        fake.tree[GROWTH_PATH] = growth_blocks(G_METRICS, core_team, G_OKR)
        reject(e, "zorg-growth", {"team": core_team})
        rc, out, res = run_ok(e, "provider", "sync", "--now", DAY1)
        r0 = (res or {}).get("results", [{}])[0]
        rep = report_of(e, "2026-10-16") or ""
        check("a text rejected by an earlier undo is held (the + goes through): «утримано», «відкинуто вами раніше», and the way to take it",
              r0.get("outcome") == "changed" and r0.get("rejected") == ["team"] and r0.get("added") == 1
              and any("`team`" in r and "утримано" in r and "відкинуто вами раніше" in r for r in table_rows(rep))
              and "Взяти текст ядра: ctx provider apply zorg-growth --choose team=theirs" in rep.splitlines()
              and "Alpha Prime" not in read(e.ctx), (r0, rep))

with FakeMcp(tree={GROWTH_PATH: GROWTH_TEXT}) as fake:   # a block that begins to wait on a ?: named once, though nothing changed
    with tempfile.TemporaryDirectory() as d:
        e = repos_env(d, fake.url)
        set_sync(e, "zorg-growth", "daily")
        run_ok(e, "migrate", "--apply")
        run_ok(e, "provider", "adopt", "zorg-growth", "--apply")
        unbase(e, "zorg-growth", "team")                 # no base for the block: the plan cannot tell who changed it
        core_team = G_TEAM.replace("v=0.1", "v=0.2").replace("- **Growth squad:** Alpha", "- **Growth squad:** Alpha Prime")
        fake.tree[GROWTH_PATH] = growth_blocks(G_METRICS, core_team)
        records, j = tree_of(os.path.join(e.store, "records")), journal_len(e)
        rc, out, res = run_ok(e, "provider", "sync", "--now", DAY1)
        r0 = (res or {}).get("results", [{}])[0]
        rep1 = report_of(e, "2026-10-16") or ""
        check("day 1: a ? appears — the pass changes nothing (no-changes, no snapshot, no journal line, records as they were) …",
              r0.get("outcome") == "no-changes" and r0.get("awaiting") == ["team"] and r0.get("snapshot") is None and journal_len(e) == j
              and tree_of(os.path.join(e.store, "records")) == records and "Alpha Prime" not in read(e.ctx), (r0, out[-300:]))
        check("… but a part names the block once: one row «чекає рішення», both texts, both commands, nothing to undo",
              r0.get("report") == "_System/context/sync/2026-10-16.md" and len(table_rows(rep1)) == 1
              and "чекає рішення" in table_rows(rep1)[0] and rep1.count("### Конфлікт: `team` — чекає рішення") == 1
              and "Growth squad:** Alpha\n" in rep1 and "Growth squad:** Alpha Prime" in rep1
              and "Взяти текст ядра: ctx provider apply zorg-growth --choose team=theirs" in rep1
              and "Лишити своє: ctx provider apply zorg-growth --choose team=mine" in rep1
              and rep1.rstrip("\n").splitlines()[-1] == "Знімка цього проходу немає: відкочувати нічого."
              and block_state(e, "zorg-growth")["sync_result"]["report"] == r0["report"], (r0, rep1))
        check("…no sentence for the skill (nothing of yours changed)", "Ядро оновило" not in out and "звіт" not in out, out[-300:])
        rc, out, res = run_ok(e, "provider", "sync", "--now", DAY2)
        r1 = (res or {}).get("results", [{}])[0]
        check("day 2: the same ? still waits — still no-changes, and no new part or file",
              r1.get("outcome") == "no-changes" and r1.get("awaiting") == ["team"] and r1.get("report") is None
              and report_of(e, "2026-10-17") is None and report_of(e, "2026-10-16") == rep1, (r1, os.listdir(os.path.join(e.store, "sync"))))
        unbase(e, "zorg-growth", "growth-metrics")        # a second block loses its base, and the core says something else about it
        core_metrics = G_METRICS.replace("v=0.1", "v=0.2").replace("weekly active shoppers", "weekly buyers")
        fake.tree[GROWTH_PATH] = growth_blocks(core_metrics, core_team)
        rc, out, res = run_ok(e, "provider", "sync", "--now", "2026-10-18T09:00:00+03:00")
        r2 = (res or {}).get("results", [{}])[0]
        rep3 = report_of(e, "2026-10-18") or ""
        check("day 3: a second block waits — a part for the NEW one only (`team` was named on day 1), still no-changes",
              r2.get("outcome") == "no-changes" and r2.get("awaiting") == ["growth-metrics", "team"]
              and r2.get("report") == "_System/context/sync/2026-10-18.md" and len(table_rows(rep3)) == 1
              and "### Конфлікт: `growth-metrics` — чекає рішення" in rep3 and "`team`" not in rep3 and "weekly buyers" in rep3, (r2, rep3))
        rc, out, res = run_ok(e, "provider", "sync", "--now", "2026-10-19T09:00:00+03:00")
        check("day 4: both still wait — nothing more is written", res["results"][0]["report"] is None and report_of(e, "2026-10-19") is None
              and read(e.store, "sync", "2026-10-18.md") == rep3)

with FakeMcp(tree={GROWTH_PATH: GROWTH_TEXT}) as fake:   # a report folder that is a symlink to somewhere else: nothing goes through it
    with tempfile.TemporaryDirectory() as d:
        e = repos_env(d, fake.url)
        set_sync(e, "zorg-growth", "daily")
        run_ok(e, "migrate", "--apply")
        run_ok(e, "provider", "adopt", "zorg-growth", "--apply")
        outside = os.path.join(d, "Elsewhere")
        os.makedirs(outside)
        stale = os.path.join(outside, "2020-01-01.md")
        open(stale, "w", encoding="utf-8").write("not a report of the sync\n")
        os.symlink(outside, os.path.join(e.store, "sync"))
        fake.tree[GROWTH_PATH] = GROWTH_TEXT.replace(G_METRICS, G_METRICS.replace("v=0.1", "v=0.2").replace("weekly active shoppers", "daily buyers"))
        rc, out, res = run_ok(e, "provider", "sync", "--now", DAY1)
        r0 = (res or {}).get("results", [{}])[0]
        trash = os.path.join(e.home, ".grow-pm", "trash")
        check("sync/ is a symlink out of the vault: its files are not read or copied to the trash, nothing is written through it, the pass stands",
              rc == 0 and r0.get("outcome") == "changed" and r0.get("report") is None and "звіт не записано" in (r0.get("reason") or "")
              and sorted(os.listdir(outside)) == ["2020-01-01.md"] and read(stale) == "not a report of the sync\n"
              and not (os.path.isdir(trash) and os.listdir(trash)) and "daily buyers" in read(e.ctx), (rc, r0, os.listdir(outside)))

with FakeMcp(tree={GROWTH_PATH: GROWTH_TEXT}) as fake:   # a report that cannot be written does not undo or hide the pass
    with tempfile.TemporaryDirectory() as d:
        e = repos_env(d, fake.url)
        set_sync(e, "zorg-growth", "daily")
        run_ok(e, "migrate", "--apply")
        run_ok(e, "provider", "adopt", "zorg-growth", "--apply")
        open(os.path.join(e.store, "sync"), "w", encoding="utf-8").write("a file where the folder should be\n")
        fake.tree[GROWTH_PATH] = GROWTH_TEXT.replace(G_METRICS, G_METRICS.replace("v=0.1", "v=0.2").replace("weekly active shoppers", "daily buyers"))
        rc, out, res = run_ok(e, "provider", "sync", "--now", DAY1)
        r0 = (res or {}).get("results", [{}])[0]
        check("the vault will not take the report: the pass stands (changed, written), the reason says the report was not written",
              rc == 0 and r0.get("outcome") == "changed" and r0.get("report") is None and "звіт не записано" in (r0.get("reason") or "")
              and "daily buyers" in read(e.ctx) and "Ядро оновило 1 блок у zorg-growth, конфліктів 0 (лишено твоє)" in out
              and "звіт:" not in out and block_state(e, "zorg-growth")["sync_result"]["report"] is None, (rc, r0, out[-400:]))

# --- v3.14.0 Task 6: undoing a sync pass is final until the core publishes something new in those blocks (spec §5.4)
def core_metrics_v(v, text):
    return G_METRICS.replace("v=0.1", "v=" + v).replace("weekly active shoppers", text)


with FakeMcp(tree={GROWTH_PATH: GROWTH_TEXT}) as fake:   # the brief's story: applied → undone → not repeated → the core's new text goes in
    with tempfile.TemporaryDirectory() as d:
        e = repos_env(d, fake.url)
        set_sync(e, "zorg-growth", "daily")
        run_ok(e, "migrate", "--apply")
        run_ok(e, "provider", "adopt", "zorg-growth", "--apply")
        old_scope = region_in(read(e.ctx), "zorg-growth", "growth-metrics")
        v2 = core_metrics_v("0.2", "weekly buyers")
        fake.tree[GROWTH_PATH] = GROWTH_TEXT.replace(G_METRICS, v2)
        rc, out, res = run_ok(e, "provider", "sync", "--now", DAY1)         # the core changed the block: applied
        check("a pass applied the core's text", rc == 0 and region_in(read(e.ctx), "zorg-growth", "growth-metrics") == v2
              and last_journal(e)["op"] == "provider-sync", (rc, out[-300:]))
        rc, out, res = run_ok(e, "undo")
        check("undo of a sync pass: back, and the text remembered as rejected",
              rc == 0 and region_in(read(e.ctx), "zorg-growth", "growth-metrics") == old_scope
              and res["rejected"] == {"zorg-growth": ["growth-metrics"]} and res["rejected_failed"] == {}, (rc, out[-400:], res))
        check("…its output names the repository and the blocks that will not be applied",
              "не застосовуватиметься, доки ядро не змінить блок: zorg-growth: growth-metrics" in out.splitlines(), out[-400:])
        st = block_state(e, "zorg-growth")
        check("…written after the restore: the state is the one before the pass (its base, its check) with the core's text hash in `rejected`",
              st["rejected"] == {"growth-metrics": [sha_of(v2)]} and st["blocks"]["growth-metrics"]["v"] == "0.1"
              and st["checked"] != DAY1, st)
        j, snaps = journal_len(e), snapshot_names(e)
        rc, out, res = run_ok(e, "provider", "sync", "--now", DAY2)
        r0 = res["results"][0]
        check("the next day's sync does not re-apply it: your text stays, the block is named as rejected, nothing written",
              rc == 0 and region_in(read(e.ctx), "zorg-growth", "growth-metrics") == old_scope and "growth-metrics" in r0["rejected"]
              and r0["updated"] == 0 and journal_len(e) == j and snapshot_names(e) == snaps and "Ядро оновило" not in out, (rc, r0, out[-300:]))
        rc, out, res = run_ok(e, "provider", "plan", "zorg-growth")
        row = {x["block"]: x for x in res["rows"]}["growth-metrics"]
        check("…`plan` marks it: rejected, with the note",
              row.get("rejected") is True and "відкинуто вами — не застосовується, доки ядро не змінить блок" in row["note"], row)
        fake.tree[GROWTH_PATH] = GROWTH_TEXT.replace(G_METRICS, core_metrics_v("0.3", "weekly paying buyers"))   # something new in that block
        rc, out, res = run_ok(e, "provider", "sync", "--now", DAY2_PLUS_2H)
        check("a new text in that block is applied again", rc == 0 and "weekly paying buyers" in region_in(read(e.ctx), "zorg-growth", "growth-metrics")
              and res["results"][0]["updated"] == 1 and res["results"][0]["rejected"] == [], (rc, res["results"][0], out[-300:]))
        check("…the old rejection stays in the state (it is only a hash), the new text is not in it",
              block_state(e, "zorg-growth")["rejected"] == {"growth-metrics": [sha_of(v2)]})

with FakeMcp(tree={GROWTH_PATH: GROWTH_TEXT}) as fake:   # --steps 3 across two passes and a manual apply; an earlier rejection stays
    with tempfile.TemporaryDirectory() as d:
        e = repos_env(d, fake.url)
        set_sync(e, "zorg-growth", "daily")
        run_ok(e, "migrate", "--apply")
        run_ok(e, "provider", "adopt", "zorg-growth", "--apply")
        older = core_metrics_v("0.15", "weekly signed-up buyers")
        reject(e, "zorg-growth", {"growth-metrics": older})                    # an earlier undo left this
        v2 = core_metrics_v("0.2", "weekly buyers")
        team2 = G_TEAM.replace("v=0.1", "v=0.2").replace("- **Growth squad:** Alpha", "- **Growth squad:** Alpha Prime")
        fake.tree[GROWTH_PATH] = growth_blocks(v2, G_TEAM)
        run_ok(e, "provider", "sync", "--now", DAY1)                           # pass 1 takes growth-metrics
        fake.tree[GROWTH_PATH] = growth_blocks(v2, team2)
        run_ok(e, "provider", "sync", "--now", DAY1_PLUS_1H)                   # pass 2 takes team
        team3 = team2.replace("v=0.2", "v=0.3").replace("Alpha Prime", "Alpha Prime Two")
        fake.tree[GROWTH_PATH] = growth_blocks(v2, team3)
        rc, out, res = run_ok(e, "provider", "apply", "zorg-growth")           # a manual apply: not a sync pass
        check("a manual apply took the third text of team (op provider-apply)", rc == 0 and last_journal(e)["op"] == "provider-apply"
              and last_journal(e)["taken"] == {"team": sha_of(team3)}, (rc, out[-300:]))
        rc, out, res = run_ok(e, "undo", "--steps", "3")
        check("--steps 3 takes back both sync passes and the apply: the blocks the passes took are remembered, once each, per repository",
              rc == 0 and res["rejected"] == {"zorg-growth": ["growth-metrics", "team"]}
              and "не застосовуватиметься, доки ядро не змінить блок: zorg-growth: growth-metrics, team" in out.splitlines()
              and region_in(read(e.ctx), "zorg-growth", "team") == G_TEAM, (rc, out[-400:], res.get("rejected")))
        check("…the texts: the earlier rejection kept, the pass's added after it (oldest first); team has the pass's, not the apply's",
              block_state(e, "zorg-growth")["rejected"] == {"growth-metrics": [sha_of(older), sha_of(v2)], "team": [sha_of(team2)]},
              block_state(e, "zorg-growth").get("rejected"))
        rc, out, res = run_ok(e, "provider", "sync", "--now", DAY2)
        r0 = res["results"][0]
        check("…the sync holds the metrics text, and applies team's third text (new in that block: not among the rejected)",
              region_in(read(e.ctx), "zorg-growth", "growth-metrics") == G_METRICS and r0["rejected"] == ["growth-metrics"]
              and region_in(read(e.ctx), "zorg-growth", "team") == team3, (r0, out[-300:]))

with FakeMcp(tree={GROWTH_PATH: GROWTH_TEXT}) as fake:   # a manual apply is not a sync pass: undoing it remembers nothing
    with tempfile.TemporaryDirectory() as d:
        e = repos_env(d, fake.url)
        set_sync(e, "zorg-growth", "daily")
        run_ok(e, "migrate", "--apply")
        run_ok(e, "provider", "adopt", "zorg-growth", "--apply")
        fake.tree[GROWTH_PATH] = GROWTH_TEXT.replace(G_METRICS, core_metrics_v("0.2", "weekly buyers"))
        before = block_state(e, "zorg-growth")
        rc, out, res = run_ok(e, "provider", "apply", "zorg-growth")
        rc2, out2, res2 = run_ok(e, "undo")
        check("undoing a provider-apply: rejected {}, no line about the sync, the state as it was (no `rejected`)",
              rc == 0 and rc2 == 0 and res2["rejected"] == {} and "не застосовуватиметься" not in out2
              and block_state(e, "zorg-growth") == before and "rejected" not in block_state(e, "zorg-growth"), (rc, rc2, out2[-300:]))

with FakeMcp(tree={GROWTH_PATH: GROWTH_TEXT}) as fake:   # a block the core removed: undoing that pass remembers "removed"
    with tempfile.TemporaryDirectory() as d:
        e = repos_env(d, fake.url)
        set_sync(e, "zorg-growth", "daily")
        run_ok(e, "migrate", "--apply")
        run_ok(e, "provider", "adopt", "zorg-growth", "--apply")
        fake.tree[GROWTH_PATH] = growth_blocks(G_METRICS, G_TEAM, G_OKR)
        run_ok(e, "provider", "sync", "--now", DAY1)                           # the core's new block is added (a base for it)
        added = region_in(read(e.ctx), "zorg-growth", "growth-okr") == G_OKR
        fake.tree[GROWTH_PATH] = growth_blocks(G_METRICS, G_TEAM)
        rc, out, res = run_ok(e, "provider", "sync", "--now", DAY1_PLUS_1H)    # …and removed again, a lone removal
        removed_ok = region_in(read(e.ctx), "zorg-growth", "growth-okr") is None and last_journal(e)["taken"] == {"growth-okr": "removed"}
        rc, out, res = run_ok(e, "undo")
        check("a removal undone is remembered as removed: the region is back, rejected growth-okr ['removed']",
              added and removed_ok and region_in(read(e.ctx), "zorg-growth", "growth-okr") == G_OKR
              and res["rejected"] == {"zorg-growth": ["growth-okr"]}
              and block_state(e, "zorg-growth")["rejected"] == {"growth-okr": ["removed"]}, (added, removed_ok, rc, out[-300:]))
        rc, out, res = run_ok(e, "provider", "sync", "--now", DAY2)
        check("…and the next sync does not remove it again", region_in(read(e.ctx), "zorg-growth", "growth-okr") == G_OKR
              and res["results"][0]["rejected"] == ["growth-okr"] and res["results"][0]["removed"] == 0, (res["results"][0], out[-300:]))

def e_journal(e):
    return [json.loads(l) for l in read(e.store, ".state", "journal.jsonl").strip().splitlines() if l.strip()]


with FakeMcp(tree={GROWTH_PATH: GROWTH_TEXT}) as fake:   # v3.14.0 Task 9: a copy that lags behind your bases is never taken
    with tempfile.TemporaryDirectory() as d:
        e = repos_env(d, fake.url)
        set_sync(e, "zorg-growth", "daily")
        run_ok(e, "migrate", "--apply")
        run_ok(e, "provider", "adopt", "zorg-growth", "--apply")
        v2 = core_metrics_v("0.2", "weekly buyers")
        fake.tree[GROWTH_PATH] = growth_blocks(v2, G_TEAM)
        run_ok(e, "provider", "sync", "--now", DAY1)                           # your base of growth-metrics is now v0.2
        took_v2 = region_in(read(e.ctx), "zorg-growth", "growth-metrics") == v2
        before, n_journal = read(e.ctx), len(e_journal(e))
        older = core_metrics_v("0.1", "weekly visitors")                         # a v0.1 wording you never held: a "~" back
        fake.tree[GROWTH_PATH] = growth_blocks(older, G_TEAM)                   # …from a mirror not updated yet
        rc, out, res = run_ok(e, "provider", "sync", "--now", DAY2)
        r0 = res["results"][0]
        check("a lagging copy offering an older text for a block your base has at v0.2: the sync takes nothing — the "
              "region, the copies and the journal's record writes stay; the reason says the source is behind",
              took_v2 and rc == 0 and read(e.ctx) == before and region_in(read(e.ctx), "zorg-growth", "growth-metrics") == v2
              and r0["outcome"] in ("no-changes", "changed") and r0["updated"] == 0 and r0["removed"] == 0
              and not any(j.get("ids") for j in e_journal(e)[n_journal:])
              and (r0["reason"] or "").startswith("the source is behind your bases") and "1 block not taken" in r0["reason"]
              and "Ядро оновило" not in out, (r0, out[-300:]))
        rc, out, res = run_ok(e, "provider", "plan", "zorg-growth")
        check("…a manual plan still shows the row as it is ('~'), for a person to decide",
              rc == 0 and any(l.startswith("~") and "growth-metrics" in l for l in out.splitlines()), out[-400:])
        v3 = core_metrics_v("0.3", "weekly loyal buyers")
        fake.tree[GROWTH_PATH] = growth_blocks(v3, G_TEAM)                      # the current copy: newer than your base
        rc, out, res = run_ok(e, "provider", "sync", "--now", DAY2_PLUS_2H)
        r0 = res["results"][0]
        check("…a current copy is unaffected: the sync takes its v0.3 text as usual",
              rc == 0 and region_in(read(e.ctx), "zorg-growth", "growth-metrics") == v3 and r0["updated"] == 1
              and not (r0["reason"] or "").startswith("the source is behind"), (r0, out[-300:]))

with tempfile.TemporaryDirectory() as d:                 # an undo with no sync pass in it says nothing of the kind
    e = Env(d)
    run_ok(e, "migrate", "--apply")
    run_ok(e, "set", "product.zorg-app", "Jira Project Key", "NEW")
    rc, out, res = run_ok(e, "undo")
    check("an ordinary undo: rejected {}, no line about the sync, no state file written",
          rc == 0 and res["rejected"] == {} and res["rejected_failed"] == {} and "не застосовуватиметься" not in out
          and not os.path.isdir(os.path.join(e.store, ".state", "blocks")), (rc, out[-300:], res))

SHA_X = "a" * 64
check("sync_rejections: only provider-sync lines with a well-formed source and hashes count; the rest is skipped",
      ctx_cli.sync_rejections([
          {"op": "provider-sync", "source": "repo:zorg-growth", "taken": {"b1": SHA_X, "b2": "removed"}},
          {"op": "provider-apply", "source": "repo:zorg-growth", "taken": {"b3": SHA_X}},
          {"op": "provider-sync", "source": "repo:zorg-growth"},                                # an older line: no `taken`
          {"op": "provider-sync", "source": "repo:zorg-growth", "taken": None},
          {"op": "provider-sync", "source": "repo:Bad Id", "taken": {"b4": SHA_X}},
          {"op": "provider-sync", "source": "undo", "taken": {"b5": SHA_X}},
          {"op": "provider-sync", "source": 7, "taken": {"b6": SHA_X}},
          {"op": "provider-sync", "source": "repo:zorg-core", "taken": {"b7": "not-a-hash", "b8": 5, "b9": SHA_X}},
          {"op": "provider-sync", "source": "repo:zorg-growth", "taken": {"b1": "b" * 64}},
          {"op": "sync", "source": "ctx-sync"}])
      == {"zorg-growth": {"b1": [SHA_X, "b" * 64], "b2": ["removed"]}, "zorg-core": {"b9": [SHA_X]}}, "")

with FakeMcp(tree={GROWTH_PATH: GROWTH_TEXT}) as fake:   # the state cannot take the memory: the undo stands, and says the sync may apply the text again
    with tempfile.TemporaryDirectory() as d:
        e = repos_env(d, fake.url)
        set_sync(e, "zorg-growth", "daily")
        run_ok(e, "migrate", "--apply")
        run_ok(e, "provider", "adopt", "zorg-growth", "--apply")
        fake.tree[GROWTH_PATH] = GROWTH_TEXT.replace(G_METRICS, core_metrics_v("0.2", "weekly buyers"))
        run_ok(e, "provider", "sync", "--now", DAY1)
        snap = last_journal(e)["snapshot"]
        open(os.path.join(snap, "state", "blocks", "zorg-growth.json"), "w", encoding="utf-8").write("{not json")
        rc, out, res = run_ok(e, "undo")
        check("a state that cannot be read: the undo is done (exit 0), nothing is remembered, and the output says so",
              rc == 0 and region_in(read(e.ctx), "zorg-growth", "growth-metrics") == G_METRICS and res["rejected"] == {}
              and list(res["rejected_failed"]) == ["zorg-growth"]
              and any(l.startswith("не вдалося запам'ятати відкинуте в zorg-growth:") and "наступний синк може застосувати це знову" in l
                      for l in out.splitlines()) and "не застосовуватиметься" not in out, (rc, out[-500:], res.get("rejected_failed")))

# --- v3.14.0 Task 8: registrations read on a shared deadline everywhere; unknown blocks refused before the lock; repo status
# without the team build
import ctx_repos as crp_mod  # noqa: E402

BOUNDARY_SAID = ("a registration could not be read: %s — the provider boundary cannot be checked; "
                 "try again when it has downloaded")


def bounded(e, timeout, *args):
    """`e.run(*args)` that gives up after `timeout` seconds: (None, "still running after N s", {}) then — a run that waits
    on a registration forever fails its check instead of holding the test. A run with no CTX_RESULT line gives {} too."""
    rc, out = raw(e, list(args) + ["--home", e.home, "--context", e.ctx], timeout=timeout)
    last = [l for l in out.splitlines() if l.startswith("CTX_RESULT ")]
    return rc, out, json.loads(last[-1][len("CTX_RESULT "):]) if last else {}

with tempfile.TemporaryDirectory() as d:                 # a writing command: the guard cannot check the boundary, so it refuses
    e = Env(d)
    run_ok(e, "migrate", "--apply")
    prov = os.path.join(e.home, ".grow-pm", "providers")
    os.makedirs(prov)
    slow = os.path.join(prov, "zorg-slow.yaml")
    os.mkfifo(slow)                                     # a registration iCloud has evicted: it does not arrive within 3 s
    records, ctx_text, mirror_text, j = tree_of(os.path.join(e.store, "records")), read(e.ctx), read(e.mirror), journal_len(e)
    try:
        t0 = time.time(); rc, out, res = bounded(e, 30, "set", "product.zorg-app", "Jira Project Key", "SLOW"); took = time.time() - t0
    finally:
        unblock(slow)
        os.remove(slow)
    check("`ctx set` with a registration not read in time: exit 4, 'could not be read', nothing written — within 3 s and a margin",
          rc == 4 and BOUNDARY_SAID % slow in out and tree_of(os.path.join(e.store, "records")) == records
          and read(e.ctx) == ctx_text and read(e.mirror) == mirror_text and journal_len(e) == j and took < 9,
          (rc, round(took, 2), out[-400:]))
    rc, out, res = run_ok(e, "set", "product.zorg-app", "Jira Project Key", "SLOW")
    check("…and without it the same command goes through", rc == 0 and "- **Jira Project Key:** SLOW" in read(e.ctx), (rc, out[-300:]))

with FakeMcp(tree={GROWTH_PATH: GROWTH_TEXT}) as fake:   # the daily sync: a real registration still downloading, the guard refuses
    with tempfile.TemporaryDirectory() as d:
        e = repos_env(d, fake.url)
        set_sync(e, "zorg-growth", "daily")
        run_ok(e, "migrate", "--apply")
        run_ok(e, "provider", "adopt", "zorg-growth", "--apply")
        fake.tree[GROWTH_PATH] = GROWTH_TEXT.replace(G_METRICS, G_METRICS.replace("v=0.1", "v=0.2"))
        j, ctx_text, seen = journal_len(e), read(e.ctx), len(fake.seen)
        state = read(e.store, ".state", "blocks", "zorg-growth.json")
        slow = os.path.join(e.home, ".grow-pm", "providers", "zorg-slow.yaml")
        os.mkfifo(slow)
        try:
            t0 = time.time(); rc, out, res = bounded(e, 40, "provider", "sync", "--now", DAY1); took = time.time() - t0
        finally:
            unblock(slow)
            os.remove(slow)
        check("the daily sync with a registration iCloud has not downloaded: the guard refuses — nothing synced, nothing recorded, "
              "no request, exit 0, within the budget",
              rc == 0 and res.get("synced") == [] and journal_len(e) == j and read(e.ctx) == ctx_text
              and read(e.store, ".state", "blocks", "zorg-growth.json") == state and len(fake.seen) == seen and took < 20,
              (rc, round(took, 2), out[-400:]))
        check("…and CTX_RESULT says why: skipped guard: <why>",
              res.get("skipped") == "guard: " + cb_mod.clip(BOUNDARY_SAID % slow, cb_mod.NOTE_CLIP), res)

with FakeMcp(tree={GROWTH_PATH: GROWTH_TEXT}) as fake:   # an unknown block is refused before the lock: nothing is imported
    with tempfile.TemporaryDirectory() as d:
        e = repos_env(d, fake.url, core_extra=SKIP_PRODUCT)
        core = os.path.join(d, "ZorgCore")
        run_ok(e, "migrate", "--apply")
        run_ok(e, "provider", "adopt", "zorg-core", "--apply")
        e.edit(e.ctx, "- **Jira Project Key:** PROJ\n", "- **Jira Project Key:** PROJW\n")      # an edit waiting to be imported
        records, j, snaps = tree_of(os.path.join(e.store, "records")), journal_len(e), snapshot_names(e)
        state = read(e.store, ".state", "blocks", "zorg-core.json")
        for args in (("--add", "nosuch"), ("--choose", "nosuch=theirs"), ("--add", "scope", "nosuch")):
            rc, out, res = apply_run(e, core, "zorg-core", *args)
            check("`provider apply zorg-core %s` with an edit waiting: exit 3 before the lock — no import, no snapshot, no journal line"
                  % " ".join(args), rc == 3 and "no block nosuch in the plan of zorg-core — `ctx provider plan zorg-core` lists them" in out
                  and tree_of(os.path.join(e.store, "records")) == records and journal_len(e) == j and snapshot_names(e) == snaps
                  and read(e.store, ".state", "blocks", "zorg-core.json") == state, (rc, out[-400:]))
        rc, out, res = run_ok(e, "status")
        check("…the edit still waits to be imported", rc == 0 and sum(res["pending"].values()) > 0 and "PROJW" in read(e.ctx)
              and "PROJW" not in e.record("product.zorg-app"), (rc, out[-300:]))
        rc, out, res = apply_run(e, core, "zorg-core", "--add", "scope")
        check("…a known block passes the check: the apply runs (the edit imported first), the answer not needed for an '='",
              rc == 0 and res["ignored"] == {"scope": "="} and "PROJW" in e.record("product.zorg-app"), (rc, out[-400:]))

with FakeMcp(tree={GROWTH_PATH: GROWTH_TEXT}) as fake:   # --product: a repository outside the product is still a repository
    with tempfile.TemporaryDirectory() as d:
        e = repos_env(d, fake.url, patch=[("### Product: Zorg App\n", "### Product: Other\n\n- **Jira Project Key:** OTH\n\n"
                                                                     "### Product: Zorg App\n")],
                      core_extra="products:\n  - Zorg App\n")
        run_ok(e, "migrate", "--apply")
        e.edit(e.ctx, "- **Jira Project Key:** PROJ\n", "- **Jira Project Key:** PROJW\n")
        records, j, asked = tree_of(os.path.join(e.store, "records")), journal_len(e), len(fake.seen)
        for args, flag in ((("--add", "okr", "zorg-core"), "--add BLOCK [BLOCK …]"), (("--choose", "zorg-core=theirs"), "--choose BLOCK=…")):
            rc, out, res = run_ok(e, "provider", "apply", "--product", "Other", *args)
            check("`provider apply --product Other %s` (zorg-core serves Zorg App only): exit 3, it is a repository — nothing "
                  "imported, no request" % " ".join(args),
                  rc == 3 and "'zorg-core' is a repository, not a block — put the repository first: ctx provider apply <repo> %s" % flag in out
                  and tree_of(os.path.join(e.store, "records")) == records and journal_len(e) == j and len(fake.seen) == asked,
                  (rc, out[-400:]))

with tempfile.TemporaryDirectory() as d:                 # repo status: the hint, and the version without the team build
    e = repos_env(d, "http://127.0.0.1:9/mcp")
    run_ok(e, "migrate", "--apply")
    slow = os.path.join(e.home, ".grow-pm", "providers", "zorg-slow.yaml")
    os.mkfifo(slow)
    try:
        rc, out, res = bounded(e, 30, "repo", "status", "nosuch")
    finally:
        unblock(slow)
        os.remove(slow)
    check("repo status of an unknown id while a registration was not read: exit 3, and it may still be downloading",
          rc == 3 and "no repository 'nosuch' is registered — `ctx.py repo list` — a registration could not be read: %s (%s); "
          "it may still be downloading" % (slow, NOT_LOCAL) in out, (rc, out[-500:]))
    rc, out, res = run_ok(e, "repo", "status", "nosuch")
    check("…and with every registration read, no hint", rc == 3 and "no repository 'nosuch' is registered — `ctx.py repo list`" in out
          and "may still be downloading" not in out, (rc, out[-300:]))
    slows = [os.path.join(e.home, ".grow-pm", "providers", "zorg-slow%d.yaml" % k) for k in range(5)]   # 15 s without the deadline
    for s in slows:
        os.mkfifo(s)
    try:
        t0 = time.time(); rc, out, res = bounded(e, 30, "repo", "list"); took = time.time() - t0
    finally:
        for s in slows:
            unblock(s)
            os.remove(s)
    check("repo list with five registrations that never arrive: one 6 s deadline for all of them (not 5 × 3 s), each named",
          rc == 0 and took < 10 and all("unreadable registration: %s (%s)" % (s, NOT_LOCAL) in out.splitlines() for s in slows)
          and [r["id"] for r in res["repos"]] == ["zorg-core", "zorg-dead", "zorg-growth"], (rc, round(took, 2), out[-600:]))
    built, real_team = [], crp_mod.pb.team_context

    def counting_team(*args, **kw):
        built.append(1)
        return real_team(*args, **kw)

    crp_mod.pb.team_context = counting_team
    try:
        rc, out, res = in_process(e, "repo", "status", "zorg-core")
        by_status = len(built)
        in_process(e, "provider", "plan", "zorg-core")
    finally:
        crp_mod.pb.team_context = real_team
    check("repo status reads the source's version from the blocks file alone: the team block is not built (it is for a plan)",
          rc == 0 and by_status == 0 and len(built) > 0 and res["repos"][0]["source_version"] == "0.4"
          and "version on source: 0.4 · base: —" in out, (rc, by_status, len(built), out[-400:]))

# --- v3.14.0 Task 10: the protocols, step 0c and context-connect 0.4.0 say what the daily sync does (doc pins)
def doc(*parts):
    return re.sub(r"\s+", " ", read(ROOT, *parts))


def between(text, start, end):
    """The part of `text` from `start` up to `end` ("" when `start` is not there)."""
    i = text.find(start)
    return text[i:text.index(end, i + len(start))] if i >= 0 and end in text[i + len(start):] else (text[i:] if i >= 0 else "")


lcp3 = doc("references", "local-context-protocol.md")
cp3 = doc("references", "context-protocol.md")
pp3 = doc("references", "context-provider-protocol.md")
cst3 = doc("skills", "context-connect", "references", "connect-steps.md")
skl3 = doc("skills", "context-connect", "SKILL.md")

# step 0c: the sync first, then the read; the one sentence at the end of the answer; the skill never waits on it
s0c = between(lcp3, "### 0c.", "### 0d.")
need_0c = ["provider sync --if-due", "Ядро оновило <N> блоків у <repo>, конфліктів <K> (лишено твоє) — звіт: <path>", "before `ctx read`",
           "never stops the skill", "as the last line of its answer", "`sync: daily`", "a host without hooks"]
check("step 0c runs `provider sync --if-due` before `ctx read`, repeats «Ядро оновило …» at the end, and a failed sync never stops the skill",
      not lacks(s0c, need_0c) and 0 <= s0c.find("provider sync --if-due") < s0c.find("scripts/ctx.py\" read --skill"), lacks(s0c, need_0c))

# context-protocol: the sync/ folder, the command, the repos: line, the bounded reads, undoing a pass
need_cp = ["├── sync/", "`provider sync [REPO] [--if-due] [--now ISO]`", "exits 0 whatever the repositories did", "`skipped`",
           "lock: <why>", "guard: <why>", "repos: <id> · synced <YYYY-MM-DD>", "no changes", "unreachable since <YYYY-MM-DD> (VPN?)",
           "⚠ <N> removals held — ctx provider plan <id>", "<N> block(s) awaits a decision", "sync timed out <YYYY-MM-DD>",
           "⚠ source broken — <reason>", "⚠ sync error — <reason>", "⚠ edits to import first — ctx sync", "`+N`",
           "names `ctx provider sync --if-due` before `ctx read`", "three seconds each and six for all of them",
           "two seconds for all of them", "`provider-sync`", "`taken`", "`rejected_failed`",
           "prefer `ctx provider apply <repo> --choose <block>=theirs` to `ctx undo`", "v3.18"]
check("context-protocol documents the sync/ folder, `provider sync`, the repos: line, the shared read deadlines and undoing a sync pass",
      not lacks(cp3, need_cp) and "├── sync/" in cp3[:cp3.index("- **Compiled copies:**")], lacks(cp3, need_cp))

# context-provider-protocol: the sync key (§3b), the owner's line (§12.2), §12.11 with every sign of the table
sec11 = between(pp3, "### 12.11 ", "### 12.12 ") if "### 12.12 " in pp3 else pp3[pp3.find("### 12.11 "):] if "### 12.11 " in pp3 else ""
signs = ["=", "~", "✎", "⚠", "?", "+", "−", "✂", "·"]
need_sec11 = ["`ctx provider sync [REPO] [--if-due] [--now ISO]`", "`sync: daily`", "24 h", "an hour", "20 s", "3 s", "`policy=rule`",
              "more than one", "`changed`", "`no-changes`", "`unreachable`", "`broken`", "`held`", "`import-conflict`", "`timeout`", "`error`",
              "_System/context/sync/YYYY-MM-DD.md", "Взяти текст ядра: ctx provider apply <repo> --choose <block>=theirs",
              "Відкотити цей прохід: ctx undo (знімок <folder>)", "# Синк контексту — YYYY-MM-DD", "40 lines", "500 characters", "90 days",
              "prefer `ctx provider apply <repo> --choose <block>=theirs` to `ctx undo`", "`sync_result`", "`sync_attempt`",
              "Ядро оновило", "never waits", "the first skill of the day"]
check("context-provider-protocol §12.11 exists with a row for every sign, the outcomes, the safeguards, the report, the way back and the --choose advice",
      sec11 != "" and not lacks(sec11, need_sec11) and all(("| `%s` |" % s) in sec11 for s in signs),
      (sec11[:80], lacks(sec11, need_sec11), [s for s in signs if ("| `%s` |" % s) not in sec11]))
need_pp3 = ["sync: off # off | daily", "| `sync` | `off` |", "One key is the exception, and only by your own word: `sync`",
            "`.yaml`/`.json`", "`ctx provider adopt|plan|apply|sync`", "`sync_result`"]
check("context-provider-protocol: the `sync` key and its carve-out in §3b, the owner's line in §12.2, the network list of §12.8",
      not lacks(pp3, need_pp3), lacks(pp3, need_pp3))

# connect-steps and the skill: the question about the daily sync, the `?` rows first, the carve-out, several answers per --choose
i_q, i_first = cst3.find("the daily sync question"), cst3.find("Settle every `?`")
need_cst = ["`sync: daily`", "`sync: off`", "except `sync`", "`--choose <block>=theirs|mine|both [<block>=… …]`",
            "One `--choose` takes several answers", "ctx provider sync <repo>"]
check("connect-steps asks about `sync: daily` once, settles every `?` before it, carves `sync` out of the kept-keys rule and shows several answers per --choose",
      not lacks(cst3, need_cst) and 0 <= i_first < i_q, (lacks(cst3, need_cst), i_first, i_q))
need_skl = ["version: 0.5.0", "`sync: daily`", "Settle every `?`", "only on the user's own yes"]
check("the skill is 0.5.0 (slots, v3.15.0) and asks the daily-sync question only on the user's own yes", not lacks(skl3, need_skl), lacks(skl3, need_skl))

# the registry: one case per area, above v3.13.1
tc = read(ROOT, "testing", "test-cases.md")
ids3140 = ["TC-ctx-3140-%s" % k for k in ("apply", "decide", "mcp", "sync", "report", "undo", "digest", "reads", "state", "docs")]
head3140 = "## Release v3.14.0 — daily core sync (added 2026-10-16)"
check("test-cases.md has the v3.14.0 section above v3.13.1 with one TC-ctx-3140-* row per area",
      head3140 in tc and 0 <= tc.index(head3140) < tc.index("## Release v3.13.1") and not [i for i in ids3140 if "**%s**" % i not in tc],
      [i for i in ids3140 if "**%s**" % i not in tc])

# Task 10, fix round 1: the sentences say only what the code does (a pass that writes, a retry no sooner than an hour, a rule decides a `?`)
cp_f1, pp_f1, cst_f1, skl_f1, lcp_f1 = doc("references", "context-protocol.md"), doc("references", "context-provider-protocol.md"), \
    doc("skills", "context-connect", "references", "connect-steps.md"), doc("skills", "context-connect", "SKILL.md"), \
    doc("references", "local-context-protocol.md")
sec11_f1 = between(pp_f1, "### 12.11 ", "### 12.12 ") if "### 12.12 " in pp_f1 else pp_f1[pp_f1.find("### 12.11 "):]
need_f1 = [
    (cp_f1, ["Every pass that changes something has a snapshot and a journal line (`provider-sync`)",
             "a `?` is left waiting unless the block is a rule (then the core's text)", "prints only the `CTX_RESULT` line",
             "but not under one where the core removed the block"]),
    (sec11_f1, ["every pass that changes something can be taken back (`ctx undo`) and is explained in a report",
                "prints only the `CTX_RESULT` line", "not under a `⚠` of a block the core removed",
                "Знімка цього проходу немає: відкочувати нічого."]),
    (pp_f1, ["unless your blocks note carries a `team` region itself", "The proposal a refresh builds carries no `sync`"]),
    (cst_f1, ["every pass that changes something has a snapshot", "tried again at the first skill start an hour or more later",
              "unless the block is a core rule (`policy=rule`", "unless the core marked the block a rule (`policy=rule`)",
              "The proposal a refresh builds carries no `sync`", "An explicit request to turn the daily sync on or off comes here whatever the key says",
              "turning it off needs no `?` settling and no question", "`context-provider-protocol.md` §12.11"]),
    (skl_f1, ["the sync leaves a `?` waiting (unless the block is a core rule)", "turning it off needs no `?` settling and no question",
              "`references/context-provider-protocol.md` §12.11"]),
    (lcp_f1, ["prints only its `CTX_RESULT` line"]),
]
gone_f1 = [(cp_f1, ["Every pass has a snapshot", "never decided", "prints nothing when none is"]),
           (sec11_f1, ["every pass can be taken back", "prints nothing and writes nothing", "who has only your server gets `·` (not available) for it, never"]),
           (cst_f1, ["tried again within the hour", "the sync never decides it", "every pass has a snapshot,", "(the proposal carries none)"]),
           (skl_f1, ["a `?` is never decided by the sync", "removes at most one block"]),
           (lcp_f1, ["costs milliseconds and prints nothing"]),
           (pp_f1, ["a refresh neither adds nor changes it (the proposal carries none)"])]
check("fix round 1: every pass that WRITES (not every pass); a retry no sooner than an hour; a rule decides a `?`; --if-due prints only CTX_RESULT; "
      "the report's command and last line as the code prints them",
      all(not lacks(text, needed) for text, needed in need_f1) and all(not [s for s in bad if s in text] for text, bad in gone_f1),
      ([lacks(text, needed) for text, needed in need_f1], [[s for s in bad if s in text] for text, bad in gone_f1]))

# --- v3.14.0 final review: the write starts only with its floor left; a lagging source is visible; the card's registrations on
# the sync's deadline
import session_start as ss_mod  # noqa: E402
SCOPE_06 = SCOPE_05.replace("v=0.5", "v=0.6").replace("Zorg App and Zorg Lite.", "Zorg App, Zorg Lite and Zorg Pro.")


def sync_ctx(e):
    """The command line's context of a `provider sync` run in this process, for sy_mod.run with a deadline of the test's own."""
    return ctx_cli.Ctx(ctx_cli.build_parser().parse_args(["provider", "sync", "--home", e.home, "--context", e.ctx]))


def run_by(c, repos, now, deadline):
    with cs_mod.guard_roots(ctx_ops_mod.allowed_roots(c.home, c.text)):
        return sy_mod.run(c, repos, now, deadline)


def first_plan_until(moment):
    """cb_mod.plan whose first call — the pass's own plan (the apply plans again) — returns at the time.monotonic() `moment`."""
    calls, real = [], cb_mod.plan

    def plan(store, copies, repo, fetched, now, all_=False):
        calls.append(repo["id"])
        if len(calls) == 1:
            time.sleep(max(0.0, moment - time.monotonic()))
        return real(store, copies, repo, fetched, now, all_=all_)
    return plan


def repos_card_line(e):
    return next((l for l in read(e.store, "INDEX.md").splitlines() if l.startswith("- **Repos:**")), None)


with tempfile.TemporaryDirectory() as d:                 # Important 1: no write without its floor, and the write keeps its floor
    e = repos_env(d, "http://127.0.0.1:9/mcp", core_extra="sync: daily\n")
    blocks_file = os.path.join(d, "ZorgCore", CORE_BLOCKS)
    run_ok(e, "migrate", "--apply")
    run_ok(e, "provider", "adopt", "zorg-core", "--apply")
    change(blocks_file, SCOPE_04, SCOPE_05)              # an apply would write
    c = sync_ctx(e)
    repos = [r for r in crp_mod.load_repos(c.text, c.home) if r["id"] == "zorg-core"]
    records, j, before = tree_of(os.path.join(e.store, "records")), journal_len(e), block_state(e, "zorg-core")
    real_plan, real_apply, budgets = cb_mod.plan, cb_mod.apply, []

    def watched_apply(*args, **kw):
        budgets.append(cs_mod.read_timeout())            # the time the apply has for its reads, as it starts
        return real_apply(*args, **kw)

    deadline = time.monotonic() + 8
    cb_mod.plan, cb_mod.apply = first_plan_until(deadline - sy_mod.RESERVE_S - 2.0), watched_apply   # the plan leaves 2 s
    try:
        out = run_by(c, repos, DAY1, deadline)
    finally:
        cb_mod.plan, cb_mod.apply = real_plan, real_apply
    r0, st = (out or [{}])[0], block_state(e, "zorg-core")
    check("final review: a plan that leaves less than 3 s of the work time: timeout before the write — no apply; records, journal, "
          "bases and the check unchanged; the reason says nothing was written",
          r0.get("outcome") == "timeout" and budgets == [] and "nothing written" in (r0.get("reason") or "")
          and tree_of(os.path.join(e.store, "records")) == records and journal_len(e) == j
          and st["checked"] == before["checked"] and st["blocks"] == before["blocks"] and st["sync_attempt"] == DAY1, (r0, budgets))
    deadline = time.monotonic() + 8
    cb_mod.plan, cb_mod.apply = first_plan_until(deadline - sy_mod.RESERVE_S - 3.6), watched_apply   # …and one that leaves 3.6 s
    try:
        out = run_by(c, repos, DAY2, deadline)
    finally:
        cb_mod.plan, cb_mod.apply = real_plan, real_apply
    r0, jl = (out or [{}])[0], last_journal(e)
    check("…a plan that leaves the floor: the write starts with at least 3 s for its reads and completes — the record, its journal "
          "line (provider-sync, the pass's snapshot), the check",
          r0.get("outcome") == "changed" and len(budgets) == 1 and budgets[0] >= sy_mod.APPLY_MIN_S - 0.1
          and jl["op"] == "provider-sync" and jl["snapshot"] == r0.get("snapshot") and journal_len(e) == j + 1
          and region_in(read(e.ctx), "zorg-core", "scope").startswith(SCOPE_05) and block_state(e, "zorg-core")["checked"] == DAY2,
          (r0, budgets, jl))

with tempfile.TemporaryDirectory() as d:                 # Important 3: the card's registrations are read on the sync's deadline
    e = repos_env(d, "http://127.0.0.1:9/mcp", core_extra="sync: daily\n")
    blocks_file = os.path.join(d, "ZorgCore", CORE_BLOCKS)
    run_ok(e, "migrate", "--apply")
    run_ok(e, "provider", "adopt", "zorg-core", "--apply")
    line_before = repos_card_line(e)
    c = sync_ctx(e)
    repos = [r for r in crp_mod.load_repos(c.text, c.home) if r["id"] == "zorg-core"]
    slows = [os.path.join(e.home, ".grow-pm", "providers", "zorg-evicted%d.yaml" % k) for k in range(2)]
    real_guard = c.guard

    def guard_then_evict():                              # the guard has read every registration; then iCloud evicts two
        real_guard()
        for s in slows:
            os.mkfifo(s)

    def released():
        for s in slows:
            if os.path.exists(s):
                unblock(s)
                os.remove(s)

    change(blocks_file, SCOPE_04, SCOPE_05)              # the pass writes: a compile, and the card with it
    c.guard = guard_then_evict
    deadline = time.monotonic() + 10
    try:
        out = run_by(c, repos, DAY1, deadline)
        late = time.monotonic() - deadline
    finally:
        released()
    r0 = (out or [{}])[0]
    check("final review: two registrations evicted during a writing pass — the run returns by its deadline (before the fix the card "
          "build and the card refresh took 6 s each on top), the pass is written with its journal line, the card keeps its Repos line",
          r0.get("outcome") == "changed" and late < 1.0 and last_journal(e)["op"] == "provider-sync"
          and line_before and repos_card_line(e) == line_before, (r0.get("outcome"), round(late, 2), line_before, repos_card_line(e)))
    change(blocks_file, SCOPE_05, SCOPE_06)
    real_min, real_plan = sy_mod.APPLY_MIN_S, cb_mod.plan
    deadline = time.monotonic() + 8
    sy_mod.APPLY_MIN_S = 0.5                             # the floor lowered, so that the write may start with 1.5 s left
    cb_mod.plan = first_plan_until(deadline - sy_mod.RESERVE_S - 1.5)
    try:
        out = run_by(c, repos, DAY2, deadline)
        late = time.monotonic() - deadline
    finally:
        sy_mod.APPLY_MIN_S, cb_mod.plan = real_min, real_plan
        released()
    r0 = (out or [{}])[0]
    check("…a write that starts late: the card it builds reads the registrations on the write's budget, not on a fresh 6 s — the "
          "run returns by its deadline, the pass is written, the card keeps its Repos line",
          r0.get("outcome") == "changed" and late < 1.0 and "Zorg Pro" in (region_in(read(e.ctx), "zorg-core", "scope") or "")
          and repos_card_line(e) == line_before, (r0.get("outcome"), round(late, 2), repos_card_line(e)))

with FakeMcp(tree={GROWTH_PATH: GROWTH_TEXT}) as fake:   # Important 2: a lagging source is visible — the digest, the report once, the ?
    with tempfile.TemporaryDirectory() as d:
        e = repos_env(d, fake.url)
        set_sync(e, "zorg-growth", "daily")
        run_ok(e, "migrate", "--apply")
        run_ok(e, "provider", "adopt", "zorg-growth", "--apply")
        fake.tree[GROWTH_PATH] = growth_blocks(core_metrics_v("0.2", "weekly buyers"), G_TEAM)
        run_ok(e, "provider", "sync", "--now", DAY1)                           # your base of growth-metrics is v0.2 now
        unbase(e, "zorg-growth", "team")                                        # team has no base: the plan cannot tell who moved
        old_team = G_TEAM.replace("- **Growth squad:** Alpha", "- **Growth squad:** Alpha Old")
        fake.tree[GROWTH_PATH] = growth_blocks(core_metrics_v("0.1", "weekly visitors"), old_team)   # a mirror not refreshed yet
        rc, out, res = run_ok(e, "provider", "sync", "--now", DAY2)
        r0 = (res or {}).get("results", [{}])[0]
        st = block_state(e, "zorg-growth")
        rep = report_of(e, "2026-10-17") or ""
        part = ss_mod._sync_part("zorg-growth", st.get("sync_result"), st.get("checked"))
        check("final review: a lagging pass — held_behind in the result and the state, a ? on it still awaits a decision, nothing taken",
              rc == 0 and r0.get("outcome") == "no-changes" and sorted(r0.get("held_behind") or []) == ["growth-metrics", "team"]
              and r0.get("awaiting") == ["team"] and sorted((st.get("sync_result") or {}).get("held_behind") or []) == ["growth-metrics", "team"]
              and "Alpha Old" not in read(e.ctx) and "weekly visitors" not in read(e.ctx), (rc, r0))
        check("…the digest says the source is behind (not a plain «no changes»), names the report and keeps the awaits count",
              part == "zorg-growth · synced 2026-10-17 · ⚠ source behind — nothing taken · no changes · report "
                      "_System/context/sync/2026-10-17.md · 1 block(s) awaits a decision", part)
        check("…the report has one part for the lag: «Джерело позаду вашої бази» naming both blocks, nothing to undo",
              r0.get("report") == "_System/context/sync/2026-10-17.md" and rep.count("\n## zorg-growth · ") == 1
              and rep.count("### Джерело позаду вашої бази") == 1 and "- `growth-metrics`" in rep and "- `team`" in rep
              and rep.rstrip("\n").splitlines()[-1] == "Знімка цього проходу немає: відкочувати нічого.", (r0.get("report"), rep))
        rc, out, res = run_ok(e, "provider", "sync", "--now", DAY2_PLUS_2H)
        r1 = (res or {}).get("results", [{}])[0]
        check("…a second pass over the same lagging copy (the same held set): no second part, and the state keeps the mark",
              rc == 0 and r1.get("outcome") == "no-changes" and r1.get("report") is None and (report_of(e, "2026-10-17") or "") == rep
              and sorted((block_state(e, "zorg-growth").get("sync_result") or {}).get("held_behind") or []) == ["growth-metrics", "team"],
              (r1, (report_of(e, "2026-10-17") or "")[-300:]))

# --- v3.15.0: ctx slot bind|map|prefer|forget — what you decided about slots is kept in .state/slots.json
def slots_memory(e):
    path = os.path.join(e.store, ".state", "slots.json")
    return json.loads(read(path)) if os.path.isfile(path) else None


with FakeMcp(tree={GROWTH_PATH: GROWTH_TEXT}) as fake:
    with tempfile.TemporaryDirectory() as d:
        e = repos_env(d, fake.url)
        mem_path = os.path.join(e.store, ".state", "slots.json")
        rc, out, res = run_ok(e, "slot", "bind", "zorg-core", "team#Members", "team.members")
        check("slot without a store: exit 3, nothing created", rc == 3 and "no store" in out and not os.path.exists(e.store)
              and not os.path.exists(os.path.join(e.home, ".grow-pm", "snapshots")), (rc, out[-300:]))
        run_ok(e, "migrate", "--apply")
        rc, out, res = run_ok(e, "slot")
        check("slot without an action is a usage error", rc == 3, (rc, out[-200:]))
        records_before, copies_before = tree_of(os.path.join(e.store, "records")), (read(e.ctx), read(e.mirror))
        n_journal = len(read(e.store, ".state", "journal.jsonl").splitlines())

        rc, out, res = run_ok(e, "slot", "bind", "zorg-core", "team#Members", "team.members")
        check("slot bind writes the memory, a snapshot and a journal line", rc == 0 and res["changed"]
              and res["memory"]["bindings"] == [{"repo": "zorg-core", "block": "team", "sub": "Members", "slot": "team.members", "team": None}]
              and last_journal(e)["op"] == "slot", (rc, out[-300:], res))
        check("…the result: command, action, slot, snapshot (a folder), the memory; the file holds that memory",
              res["command"] == "slot" and res["action"] == "bind" and res["slot"] == "team.members" and os.path.isdir(res["snapshot"])
              and res["memory"]["schema"] == "context-slots-memory/1" and slots_memory(e) == res["memory"], res)
        j = last_journal(e)
        check("…one journal line: op slot, the action and the slot, no record ids, the source, the snapshot taken before the write",
              len(read(e.store, ".state", "journal.jsonl").splitlines()) == n_journal + 1 and j["action"] == "bind"
              and j["slot"] == "team.members" and j["ids"] == [] and j["source"] == "ctx-slot" and j["snapshot"] == res["snapshot"]
              and not os.path.exists(os.path.join(j["snapshot"], "state", "slots.json")), j)
        check("…and it says what it did and how to take it back", "slot bind: zorg-core team#Members → team.members · snapshot " in out
              and "(back: ctx undo)" in out, out[-300:])
        check("…no record and no copy changes: it is not a content change", tree_of(os.path.join(e.store, "records")) == records_before
              and (read(e.ctx), read(e.mirror)) == copies_before, "")
        snaps, n_journal = sorted(os.listdir(os.path.join(e.home, ".grow-pm", "snapshots"))), len(read(e.store, ".state", "journal.jsonl").splitlines())
        before = read(mem_path)
        rc, out, res = run_ok(e, "slot", "bind", "zorg-core", "team#Members", "team.members")
        check("the same bind again: exit 0, changed false, no snapshot, no journal line, the file as it was",
              rc == 0 and res["changed"] is False and res["snapshot"] is None and read(mem_path) == before
              and len(read(e.store, ".state", "journal.jsonl").splitlines()) == n_journal
              and sorted(os.listdir(os.path.join(e.home, ".grow-pm", "snapshots"))) == snaps and len(res["memory"]["bindings"]) == 1
              and "unchanged — slot bind: zorg-core team#Members → team.members" in out, (rc, out[-300:]))
        rc, _, _ = run_ok(e, "undo")
        check("undo takes the memory back", rc == 0 and not os.path.exists(mem_path), rc)
        n_journal = len(read(e.store, ".state", "journal.jsonl").splitlines())

        for label, args, said in (
                ("an unknown slot", ("bind", "zorg-core", "team", "team.nowhere"), "no slot 'team.nowhere'"),
                ("an unknown repository", ("bind", "no-such-repo", "team", "team.members"), "no-such-repo"),
                ("a block id that is no id", ("bind", "zorg-core", "te am", "team.members"), "not a block id"),
                ("an empty subsection", ("bind", "zorg-core", "team#", "team.members"), "nothing follows the '#'"),
                ("a team that is no record", ("bind", "zorg-core", "team", "team.members", "--team", "team.no-such"), "no record team.no-such"),
                ("a team that is a product record", ("bind", "zorg-core", "team", "team.members", "--team", "product.zorg-app"), "team record, not product"),
                ("a team for a slot that is not a team slot", ("bind", "zorg-core", "scope", "org.structure", "--team", "team.alpha-a"), "--team is for the team.* slots"),
                ("a name for an unknown slot", ("map", "product.zorg-app", "Key Metrics (focus)", "product.nowhere"), "no slot 'product.nowhere'"),
                ("a name for a record that is not there", ("map", "product.no-such", "Key Metrics (focus)", "product.key_metrics"), "no record product.no-such"),
                ("a name for a record of another kind than the slot's", ("map", "team.alpha-a", "Key Metrics (focus)", "product.key_metrics"), "team.alpha-a is a team record"),
                ("a blank name", ("map", "product.zorg-app", "  ", "product.key_metrics"), "heading of your subsection is empty"),
                ("a preference for an unknown slot", ("prefer", "team.nowhere", "all"), "no slot 'team.nowhere'"),
                ("a preference that is none of the three", ("prefer", "team.members", "theirs"), "mine, all or repo:<id>"),
                ("a preference for a repository that is not registered", ("prefer", "team.members", "repo:no-such-repo"), "no-such-repo"),
                ("forgetting an unknown slot", ("forget", "team.nowhere"), "no slot 'team.nowhere'")):
            rc, out, res = run_ok(e, "slot", *args)
            check("slot %s: %s is exit 3, nothing written" % (args[0], label), rc == 3 and said in out and not os.path.exists(mem_path)
                  and len(read(e.store, ".state", "journal.jsonl").splitlines()) == n_journal, (rc, out[-300:]))

        rc, out, res = run_ok(e, "slot", "bind", "zorg-core", "team#Members", "team.members", "--team", "team.alpha-a")
        check("bind --team names the record of a team", rc == 0 and res["memory"]["bindings"][0]["team"] == "team.alpha-a", (rc, out[-300:], res))
        rc, out, res = run_ok(e, "slot", "bind", "zorg-core", "team#Members", "team.members")
        check("…the same bind without the team changes nothing", rc == 0 and res["changed"] is False
              and res["memory"]["bindings"][0]["team"] == "team.alpha-a", (rc, res))
        rc, out, res = run_ok(e, "slot", "bind", "zorg-growth", "growth-metrics", "product.key_metrics")
        check("bind a whole block, from another repository", rc == 0 and res["changed"]
              and {"repo": "zorg-growth", "block": "growth-metrics", "sub": None, "slot": "product.key_metrics", "team": None}
              in res["memory"]["bindings"] and len(res["memory"]["bindings"]) == 2, (rc, out[-300:], res))

        rc, out, res = run_ok(e, "slot", "map", "product.zorg-app", "Key Metrics (focus)", "product.key_metrics")
        check("slot map keeps your name for a slot: the record, the heading, the slot", rc == 0 and res["changed"] and res["action"] == "map"
              and res["memory"]["aliases"] == [{"record": "product.zorg-app", "heading": "Key Metrics (focus)", "slot": "product.key_metrics"}]
              and last_journal(e)["action"] == "map" and last_journal(e)["op"] == "slot", (rc, out[-300:], res))
        rc, out, res = run_ok(e, "slot", "map", "product.zorg-app", "key metrics (FOCUS)", "product.key_metrics")
        check("…the same name again (case, spacing aside) adds nothing", rc == 0 and res["changed"] is False and res["snapshot"] is None
              and len(res["memory"]["aliases"]) == 1, (rc, res))

        rc, out, res = run_ok(e, "slot", "prefer", "team.members", "repo:zorg-core")
        check("slot prefer keeps whose answer a slot gives first", rc == 0 and res["changed"] and res["memory"]["prefer"] == {"team.members": "repo:zorg-core"}
              and last_journal(e)["action"] == "prefer", (rc, out[-300:], res))
        rc, out, res = run_ok(e, "slot", "prefer", "team.members", "all")
        check("…another preference replaces it", rc == 0 and res["changed"] and res["memory"]["prefer"] == {"team.members": "all"}, (rc, res))
        rc, out, res = run_ok(e, "slot", "prefer", "team.members", "all")
        check("…the same one again changes nothing", rc == 0 and res["changed"] is False and res["snapshot"] is None, (rc, res))
        rc, out, res = run_ok(e, "slot", "prefer", "org.structure", "mine")
        check("…mine is a preference too, kept as it is", rc == 0 and res["memory"]["prefer"].get("org.structure") == "mine", (rc, res))

        n_journal = len(read(e.store, ".state", "journal.jsonl").splitlines())
        rc, out, res = run_ok(e, "slot", "forget", "team.members")
        mem = res["memory"]
        check("slot forget takes everything about the slot — bindings, names, preference — and only that slot",
              rc == 0 and res["changed"] and not [b for b in mem["bindings"] if b["slot"] == "team.members"] and "team.members" not in mem["prefer"]
              and len(mem["bindings"]) == 1 and len(mem["aliases"]) == 1 and mem["prefer"] == {"org.structure": "mine"}
              and last_journal(e)["action"] == "forget" and last_journal(e)["slot"] == "team.members"
              and len(read(e.store, ".state", "journal.jsonl").splitlines()) == n_journal + 1, (rc, out[-300:], res))
        rc, out, res = run_ok(e, "slot", "forget", "team.members")
        check("…a slot the memory knows nothing of: exit 0, changed false, no snapshot", rc == 0 and res["changed"] is False
              and res["snapshot"] is None and len(read(e.store, ".state", "journal.jsonl").splitlines()) == n_journal + 1, (rc, res))
        rc, out, res = run_ok(e, "undo")
        check("undo of a forget brings back what it took", rc == 0 and any(b["slot"] == "team.members" for b in slots_memory(e)["bindings"]), (rc, out[-300:]))

        # a direct edit waiting is imported first, as in every writing command
        e.edit(e.ctx, "- **Jira Project Key:** PROJ", "- **Jira Project Key:** PROJ2")
        rc, out, res = run_ok(e, "slot", "prefer", "product.okrs", "all")
        check("slot imports the edits waiting first, like every writing command", rc == 0 and "PROJ2" in e.record("product.zorg-app"), (rc, out[-300:]))
        cache = os.path.join(e.home, ".grow-pm", ".ctx-summary.json")
        if os.path.exists(cache):
            os.remove(cache)
        run_ok(e, "slot", "prefer", "product.okrs", "mine")
        check("…and, as a writing command that exited 0, saves the digest's summary", os.path.isfile(cache))
        rc, out, res = run_ok(e, "slot", "prefer", "product.okrs", "all", "--store", e.store)
        check("…--store is for read commands only", rc == 3 and "--store is for read commands only" in out, (rc, out[-300:]))

        # an unreadable memory stops every slot command, and is left as it is
        for text, label in (("{ not json", "not JSON"), ('{"schema": "context-slots-memory/9"}', "another schema"),
                            ('{"schema": "context-slots-memory/1", "prefer": []}', "the wrong shape")):
            open(mem_path, "w", encoding="utf-8", newline="").write(text)
            n_journal = len(read(e.store, ".state", "journal.jsonl").splitlines())
            rcs = [run_ok(e, "slot", *args) for args in (("bind", "zorg-core", "team#Members", "team.members"),
                                                         ("map", "product.zorg-app", "Key Metrics (focus)", "product.key_metrics"),
                                                         ("prefer", "team.members", "all"), ("decide", "team.members", "zorg-core"),
                                                         ("forget", "team.members"))]
            check("an unreadable memory (%s) stops every slot command: exit 3, the file named, nothing written" % label,
                  all(r[0] == 3 and "slots memory" in r[1] and ".state/slots.json" in r[1] for r in rcs) and read(mem_path) == text
                  and len(read(e.store, ".state", "journal.jsonl").splitlines()) == n_journal, [(r[0], r[1][-200:]) for r in rcs])
        os.remove(mem_path)
        os.mkdir(mem_path)
        rc, out, res = run_ok(e, "slot", "prefer", "team.members", "all")
        check("…a memory that is not a file cannot be read: exit 3", rc == 3 and "slots memory not readable" in out, (rc, out[-300:]))

# --- v3.15.0: ctx slot decide — the answer to a divergence between repositories (spec §6): remembered with the hash of
# every side, so that a new text from either repository asks again
def sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


SCOPE_NORM = "### Scope of work\nThe user works on Zorg App only."                              # zorg-core's `scope` block, as cb.norm has it
METRICS_NORM = "#### Growth metrics\n- **North star:** weekly active shoppers"                   # zorg-growth's `growth-metrics`
DIVERGE = "product.scope"


def equal_ranks(e):
    """zorg-growth at the rank zorg-core has (org: 1000): the two repositories tie."""
    open(os.path.join(e.home, ".grow-pm", "providers", "zorg-growth.yaml"), "a", encoding="utf-8", newline="").write("rank: 1000\n")


def journal_len(e):
    return len(read(e.store, ".state", "journal.jsonl").splitlines())


with FakeMcp(tree={GROWTH_PATH: GROWTH_TEXT}) as fake:
    with tempfile.TemporaryDirectory() as d:
        e = repos_env(d, fake.url)
        equal_ranks(e)
        mem_path = os.path.join(e.store, ".state", "slots.json")
        rc, out, res = run_ok(e, "slot", "decide", DIVERGE, "zorg-core")
        check("decide without a store: exit 3, nothing created", rc == 3 and "no store" in out and not os.path.exists(e.store), (rc, out[-300:]))
        run_ok(e, "migrate", "--apply")
        n_journal, snaps = journal_len(e), sorted(os.listdir(os.path.join(e.home, ".grow-pm", "snapshots")))
        rc, out, res = run_ok(e, "slot", "decide", DIVERGE, "zorg-core")
        check("no divergence (nothing bound to the slot): exit 3 «no divergence for <slot>», nothing written",
              rc == 3 and "no divergence for product.scope" in out and not os.path.exists(mem_path) and journal_len(e) == n_journal
              and sorted(os.listdir(os.path.join(e.home, ".grow-pm", "snapshots"))) == snaps, (rc, out[-300:]))
        rc, out, res = run_ok(e, "slot", "decide", "team.nowhere", "zorg-core")
        check("…a slot the catalogue lacks: exit 3", rc == 3 and "no slot 'team.nowhere'" in out, (rc, out[-300:]))
        run_ok(e, "slot", "bind", "zorg-core", "scope", DIVERGE)
        rc, out, res = run_ok(e, "slot", "decide", DIVERGE, "zorg-core")
        check("…one repository bound is no divergence either", rc == 3 and "no divergence for product.scope" in out, (rc, out[-300:]))
        run_ok(e, "slot", "bind", "zorg-growth", "growth-metrics", DIVERGE)
        n_journal, mem_before = journal_len(e), read(mem_path)
        for label, who, said in (("a repository that is registered but is not one of the sides", "zorg-dead", "zorg-dead"),
                                 ("a repository nobody registered", "no-such-repo", "no-such-repo")):
            rc, out, res = run_ok(e, "slot", "decide", DIVERGE, who)
            check("decide for %s: exit 3, the sides named, nothing written" % label, rc == 3 and said in out
                  and "zorg-core, zorg-growth" in out and read(mem_path) == mem_before and journal_len(e) == n_journal, (rc, out[-300:]))

        rc, out, res = run_ok(e, "slot", "decide", DIVERGE, "zorg-growth")
        day = datetime.date.today().isoformat()
        want = {"winner": "zorg-growth", "hashes": {"zorg-core": sha256(SCOPE_NORM), "zorg-growth": sha256(METRICS_NORM)}, "at": day}
        check("decide writes the winner and the hash of the normalised text of every side, and the day", rc == 0 and res["changed"] is True
              and res["memory"]["decisions"] == {DIVERGE: want} and slots_memory(e) == res["memory"], (rc, out[-300:], res))
        j = last_journal(e)
        check("…the sequence of every slot command: a snapshot folder, one journal line (op slot, action decide, the slot), what to type to undo",
              res["command"] == "slot" and res["action"] == "decide" and res["slot"] == DIVERGE and os.path.isdir(res["snapshot"])
              and j["op"] == "slot" and j["action"] == "decide" and j["slot"] == DIVERGE and j["ids"] == [] and j["source"] == "ctx-slot"
              and j["snapshot"] == res["snapshot"] and journal_len(e) == n_journal + 1
              and "slot decide: product.scope → zorg-growth · snapshot " in out and "(back: ctx undo)" in out, (j, out[-300:]))
        check("…the bindings are as they were", len(res["memory"]["bindings"]) == 2, res["memory"])
        n_journal = journal_len(e)
        rc, out, res = run_ok(e, "slot", "decide", DIVERGE, "zorg-core")
        check("a divergence you have answered is none: decide again is exit 3 «no divergence», the answer kept",
              rc == 3 and "no divergence for product.scope" in out and slots_memory(e)["decisions"] == {DIVERGE: want}
              and journal_len(e) == n_journal, (rc, out[-300:]))

        rc, out, res = run_ok(e, "undo")
        check("undo takes the decision back — and leaves the bindings", rc == 0 and slots_memory(e)["decisions"] == {}
              and len(slots_memory(e)["bindings"]) == 2, (rc, out[-300:], slots_memory(e)))
        rc, out, res = run_ok(e, "slot", "decide", DIVERGE, "zorg-core")
        check("…and the slot diverges again: the other side may be chosen", rc == 0 and res["memory"]["decisions"][DIVERGE]["winner"] == "zorg-core"
              and res["memory"]["decisions"][DIVERGE]["hashes"] == want["hashes"], (rc, out[-300:]))
        rc, out, res = run_ok(e, "slot", "decide", DIVERGE, "zorg-core")
        check("…and that answer settles it again", rc == 3 and "no divergence for product.scope" in out, (rc, out[-300:]))

        edit_both(e, "weekly active shoppers", "weekly active buyers")
        rc_s, out_s, _ = run_ok(e, "sync")
        rc, out, res = run_ok(e, "slot", "decide", DIVERGE, "zorg-growth")
        new_hash = sha256(METRICS_NORM.replace("shoppers", "buyers"))
        check("a new text in zorg-growth (a new hash): the slot diverges again, and the new answer keeps the new hash",
              rc_s == 0 and rc == 0 and res["memory"]["decisions"][DIVERGE]["winner"] == "zorg-growth"
              and res["memory"]["decisions"][DIVERGE]["hashes"] == {"zorg-core": sha256(SCOPE_NORM), "zorg-growth": new_hash}
              and new_hash != want["hashes"]["zorg-growth"], (rc_s, rc, out_s[-200:], out[-300:]))

# a skill that reads one product: several products and none named is a question, not a guess
LITE_PRODUCT = ("### Team: Alpha (A)\n", "### Product: Zorg Lite\n\n- **Jira Project Key:** LITE\n\n### Team: Alpha (A)\n")
with FakeMcp(tree={GROWTH_PATH: GROWTH_TEXT}) as fake:
    with tempfile.TemporaryDirectory() as d:
        e = repos_env(d, fake.url, patch=[LITE_PRODUCT])
        equal_ranks(e)
        run_ok(e, "migrate", "--apply")
        for args in (("zorg-core", "scope", DIVERGE), ("zorg-growth", "growth-metrics", DIVERGE),
                     ("zorg-core", "teams", "org.structure"), ("zorg-growth", "team", "org.structure")):
            run_ok(e, "slot", "bind", *args)
        n_journal = journal_len(e)
        rc, out, res = run_ok(e, "slot", "decide", DIVERGE, "zorg-core")
        check("a product slot with several products and no --product: exit 3, the products named, nothing written",
              rc == 3 and "Zorg App" in out and "Zorg Lite" in out and "--product" in out and journal_len(e) == n_journal
              and not (slots_memory(e) or {}).get("decisions"), (rc, out[-300:]))
        rc, out, res = run_ok(e, "slot", "decide", DIVERGE, "zorg-core", "--product", "Zorg Lite")
        check("…--product names the one whose slot it is: for Zorg Lite only zorg-core answers, so no divergence",
              rc == 3 and "no divergence for product.scope" in out, (rc, out[-300:]))
        rc, out, res = run_ok(e, "slot", "decide", DIVERGE, "zorg-core", "--product", "Nowhere")
        check("…a product that is none: exit 3, the products named", rc == 3 and "Nowhere" in out and "Zorg App" in out, (rc, out[-300:]))
        rc, out, res = run_ok(e, "slot", "decide", DIVERGE, "zorg-core", "--product", "Zorg App")
        check("…for Zorg App both repositories answer: the decision is written", rc == 0 and res["memory"]["decisions"][DIVERGE]["winner"] == "zorg-core"
              and sorted(res["memory"]["decisions"][DIVERGE]["hashes"]) == ["zorg-core", "zorg-growth"], (rc, out[-300:]))
        rc, out, res = run_ok(e, "slot", "decide", "org.structure", "zorg-growth")
        check("an organisation slot does not depend on the product: decide needs no --product", rc == 0
              and res["memory"]["decisions"]["org.structure"]["winner"] == "zorg-growth", (rc, out[-300:]))

# --- v3.15.0 Task 6: ctx explain — where each slot came from and why it won (spec §7); reads only: no lock, no network, no write
def full_tree(*roots):
    """Every directory and file under the roots, a file with its bytes and modification time: a created empty directory counts."""
    out = {}
    for root in roots:
        for dp, _, fn in os.walk(root):
            out[dp] = "dir"
            for n in fn:
                p = os.path.join(dp, n)
                out[p] = (open(p, "rb").read(), os.stat(p).st_mtime_ns)
    return out


def slot_in(res, slot, record=None):
    return next((s for s in (res or {}).get("slots", []) if s["slot"] == slot and (record is None or s["record"] == record)), None)


def outcomes_of(s):
    return [(c["source"], c["outcome"]) for c in (s or {}).get("candidates", [])]


def printed(out, prefix):
    """The command a line of the explanation prints from `prefix` on (to run it as it stands)."""
    return next((l[l.index(prefix):] for l in out.splitlines() if prefix in l), None)


def ctx_args(command):
    """`ctx slot bind …` as the arguments `run_ok` takes (the text between double quotes is one argument)."""
    import shlex
    return shlex.split(command)[1:]


TEAM_OWN = ("- **Jira Team ID:** <team-uuid>\n", "- **Jira Team ID:** <team-uuid>\n\n#### Team Members\n\n| Name | Role |\n|---|---|\n| Own Person | PM |\n")
KEY_METRICS_OWN = ("- **Jira Project Key:** PROJ\n", "- **Jira Project Key:** PROJ\n\n#### Key Metrics\n- Mine: weekly active shoppers\n")
CORE_NUMBERS = ("- **Jira Project Key:** PROJ\n", "- **Jira Project Key:** PROJ\n\n#### Core numbers\n- Mine: weekly active shoppers\n")
FIXTURE_TEXT_CLI = read(REPOS_FIX, "context.md")
TEAM_REGION_CLI = region_in(FIXTURE_TEXT_CLI, "zorg-core", "team")
TEAM_TO_NOTES = [(TEAM_REGION_CLI + "\n\n", ""), ("## Zorg Core Notes\n\n", "## Zorg Core Notes\n\n" + TEAM_REGION_CLI + "\n\n"),
                 ("<!-- zorg-growth:end id=team -->\n", "<!-- zorg-growth:end id=team -->\n\n### Team: Beta (B)\n\n- **Jira Team ID:** <beta-uuid>\n")]

with FakeMcp(tree={GROWTH_PATH: GROWTH_TEXT}) as fake:
    with tempfile.TemporaryDirectory() as d:
        e = repos_env(d, fake.url, core_extra=SKIP_PRODUCT, patch=[TEAM_OWN])
        rc, out, res = run_ok(e, "explain")
        check("explain without a store: exit 3, nothing created", rc == 3 and "no store" in out and not os.path.exists(e.store)
              and not os.path.exists(os.path.join(e.home, ".grow-pm", "snapshots")), (rc, out[-300:]))
        run_ok(e, "migrate", "--apply")
        run_ok(e, "provider", "adopt", "zorg-core", "--apply")
        check("explain is not a writing command", "explain" not in ctx_cli.WRITING and not ctx_cli.writes(ctx_cli.build_parser().parse_args(["explain"])), "")

        # ---- reads only: no write of any kind (files, directories, times), no lock
        before = full_tree(e.home, e.store, e.vault)
        for args in ((), ("--skill", "task-creator"), ("team.members", "product.scope"), ("--json",)):
            rc, out, res = run_ok(e, "explain", *args)
            check("explain %s writes nothing: the home, the store and the vault, directories included" % (" ".join(args) or "(no arguments)"),
                  rc == 0 and full_tree(e.home, e.store, e.vault) == before, (rc, out[-300:]))
        with ctx_ops_mod.lock(e.home):
            rc, out, res = run_ok(e, "explain", "--skill", "task-creator")
            rc_w, out_w, _ = run_ok(e, "slot", "prefer", "team.members", "all")
        check("explain takes no lock: another run holds it and explain exits 0, while a writing command is refused (exit 4)",
              rc == 0 and rc_w == 4 and "another ctx run holds" in out_w and slot_in(res, "team.members"), (rc, rc_w, out[-300:], out_w[-200:]))
        rc, out, res = run_ok(e, "explain", "--skill", "task-creator", "--store", e.store)
        check("…--store is accepted, as for every read command", rc == 0 and slot_in(res, "team.members"), (rc, out[-200:]))

        # ---- --skill: the slots the skill asks, in the manifest's order, and only those
        rc, out, res = run_ok(e, "explain", "--skill", "task-creator")
        check("--skill task-creator: exactly the slots it asks, in the manifest's order",
              rc == 0 and [s["slot"] for s in res["slots"]] == ["product.jira_key", "product.confluence_space", "team.jira_team_id", "team.members"],
              (rc, [s["slot"] for s in res.get("slots", [])]))
        members = slot_in(res, "team.members")
        check("…team.members: your Team Members and the core's Members, both shown (a list shows every candidate), the header says what it is",
              outcomes_of(members) == [("mine", "shown"), ("zorg-core", "shown")] and members["kind"] == "list" and members["record"] == "team.alpha-a"
              and members["winner"] is None and members["why"] == "список — виводяться всі кандидати; team.members у ctx read склеєно за сутністю"
              and "team.members · список · Team: Alpha (A)\n" in out and "  чому: список — виводяться всі кандидати" in out, (members, out[:1500]))
        mine_row, core_row = members["candidates"]
        check("…your row says where your text is; the block's — which block, which version, in which record, checked when",
              mine_row["record"] == "team.alpha-a" and mine_row["heading"] == "Team Members" and "block" not in mine_row
              and core_row["block"] == "team" and core_row["sub"] == "Members" and core_row["version"] == "0.2" and core_row["record"] == "team.alpha-a"
              and core_row["rule"] is False and core_row["edited"] is False and core_row["how"] == "plugin" and core_row["checked"]
              and "✔ твоє · team.alpha-a › Team Members" in out and "✔ zorg-core · блок team#Members v0.2 у записі team.alpha-a · станом на %s" % core_row["checked"] in out,
              (mine_row, core_row, out[:1500]))
        check("…looked_in says the names and the record", members["looked_in"] == {"names": ["Members", "Team Members", "Склад команди", "Учасники"],
              "records": ["Team: Alpha (A)"]}, members["looked_in"])
        check("…a skill's explanation lists no unmapped or skipped blocks: only the slots it asks", res["unmapped_blocks"] == [] and res["skipped_blocks"] == [], res)
        confl = slot_in(res, "product.confluence_space")
        check("a slot nobody answers: «не знайдено», «шукав:» with the names and the record, and the command that maps your own subsection",
              confl["candidates"] == [] and confl["winner"] is None and confl["looked_in"]["names"] == ["Confluence Space"]
              and "product.confluence_space · одне значення · Product: Zorg App · не знайдено\n" in out
              and "  шукав: Confluence Space — у Product: Zorg App; блоків із цим слотом немає" in out
              and '  прив\'язати свою підсекцію: ctx slot map product.zorg-app "<Назва>" product.confluence_space' in out, out[-1500:])
        key = slot_in(res, "product.jira_key")
        check("a value your text answers: one candidate, it won, «єдиний кандидат»", outcomes_of(key) == [("mine", "won")] and key["winner"] == "mine"
              and key["why"] == "єдиний кандидат" and "  ✔ твоє · product.zorg-app › Jira Project Key" in out, (key, out[:600]))
        rc, out_s, res_s = run_ok(e, "explain", "--skill", "no-such-skill")
        check("an unknown skill: exit 3, as ctx read says it", rc == 3 and "no manifest entry for no-such-skill" in out_s, (rc, out_s[-200:]))

        # ---- slots named: only those, in the order given; an unknown one is exit 3
        rc, out, res = run_ok(e, "explain", "product.scope", "team.members", "product.scope")
        check("explain <slot> …: only those, in the order given, none twice", rc == 0 and [s["slot"] for s in res["slots"]] == ["product.scope", "team.members"]
              and res["unmapped_blocks"] == [] and res["skipped_blocks"] == [], (rc, [s["slot"] for s in res.get("slots", [])]))
        rc, out, res = run_ok(e, "explain", "team.nowhere")
        check("an unknown slot: exit 3, the catalogue named", rc == 3 and "no slot 'team.nowhere'" in out, (rc, out[-200:]))

        # ---- nothing asked: every slot with a candidate, then the blocks no slot takes and the blocks you switched off
        rc, out, res = run_ok(e, "explain")
        names = [s["slot"] for s in res["slots"]]
        check("explain with no arguments: the slots that have a candidate (not the ones nobody answers)", rc == 0 and "team.members" in names
              and "product.jira_key" in names and "product.confluence_space" not in names and all(s["candidates"] for s in res["slots"]), names)
        check("…skipped_blocks: the block of skip_blocks, with its repository", {"repo": "zorg-core", "block": "product"} in res["skipped_blocks"], res["skipped_blocks"])
        scope = next((b for b in res["unmapped_blocks"] if b["block"] == "scope"), None)
        check("…unmapped_blocks: a region of a registered repository that no slot takes (scope), not the team block the plugin binds",
              scope is not None and scope == {"repo": "zorg-core", "block": "scope", "record": scope["record"], "version": "0.4", "heading": "Scope of work"}
              and scope["record"] and sorted(b["block"] for b in res["unmapped_blocks"]) == ["growth-metrics", "scope", "teams"], res["unmapped_blocks"])
        check("…and the text lists both", "scope" in out.split("Блоки без прив'язки", 1)[-1] and "Вимкнені блоки" in out
              and "zorg-core · блок product" in out.split("Вимкнені блоки", 1)[-1], out[-900:])
        rc, out_j, res_j = run_ok(e, "explain", "--json")
        check("--json puts the printed text into CTX_RESULT as read does", rc == 0 and res_j.get("text") == out_j.split("CTX_RESULT ")[0]
              and res_j["command"] == "explain" and res_j["ok"] is True and res.get("text") is None, (rc, res_j.get("text", "")[:100]))

with FakeMcp(tree={GROWTH_PATH: GROWTH_TEXT}) as fake:           # who won, who lost, and what you can do about it
    with tempfile.TemporaryDirectory() as d:
        e = repos_env(d, fake.url, core_extra=SKIP_PRODUCT, patch=[KEY_METRICS_OWN])
        run_ok(e, "migrate", "--apply")
        run_ok(e, "provider", "adopt", "zorg-growth", "--apply")
        run_ok(e, "slot", "bind", "zorg-growth", "growth-metrics", "product.key_metrics")
        rc, out, res = run_ok(e, "explain", "product.key_metrics")
        km = slot_in(res, "product.key_metrics")
        check("your text over a block that is not a rule: yours won, the block lost and the reason is said as the spec has it",
              rc == 0 and outcomes_of(km) == [("mine", "won"), ("zorg-growth", "lost")] and km["winner"] == "mine" and km["kind"] == "text"
              and km["candidates"][1]["reason"] == "програв: твоє перемагає (блок не є правилом ядра)"
              and "product.key_metrics · текст · Product: Zorg App\n" in out and "  ✔ твоє · product.zorg-app › Key Metrics\n" in out
              and "  ✗ zorg-growth · блок growth-metrics v0.1 у записі product.zorg-app · станом на " in out
              and "— програв: твоє перемагає (блок не є правилом ядра)" in out and "  чому: твоє перемагає (блок не є правилом ядра)" in out,
              (km, out[:1200]))
        check("…the block's row: its binding is yours, its rank is known", km["candidates"][1]["how"] == "memory" and km["candidates"][1]["rank"] == 500
              and "прив'язка: твоя" in out, km["candidates"][1])
        check("…what you decided about the slot is shown, with the command that takes it all back",
              km["memory"]["bindings"][0]["block"] == "growth-metrics" and "ctx slot forget product.key_metrics" in out
              and km["commands"][-1] == "ctx slot forget product.key_metrics", (km.get("memory"), out[-500:]))
        run_ok(e, "slot", "prefer", "product.key_metrics", "repo:zorg-growth")
        rc, out, res = run_ok(e, "explain", "product.key_metrics")
        km = slot_in(res, "product.key_metrics")
        check("a preference for a repository: the block won, your text lost, the preference is named",
              outcomes_of(km) == [("zorg-growth", "won"), ("mine", "lost")] and km["prefer"] == "repo:zorg-growth"
              and km["candidates"][1]["reason"] == "програв: перевага: repo:zorg-growth" and "перевага: repo:zorg-growth" in out, (km, out[:900]))
        rc_f, out_f, _ = run_ok(e, *ctx_args(printed(out, "ctx slot forget product.key_metrics")))
        rc, out, res = run_ok(e, "explain", "product.key_metrics")
        km = slot_in(res, "product.key_metrics")
        check("…the printed forget command runs, and the slot is as it was without it", rc_f == 0 and outcomes_of(km) == [("mine", "won")]
              and km.get("memory") is None and "ctx slot forget" not in out, (rc_f, out_f[-200:], km))

with FakeMcp(tree={GROWTH_PATH: GROWTH_TEXT}) as fake:           # a divergence, the answer, the answer taken back
    with tempfile.TemporaryDirectory() as d:
        e = repos_env(d, fake.url)
        equal_ranks(e)
        run_ok(e, "migrate", "--apply")
        run_ok(e, "slot", "bind", "zorg-core", "scope", DIVERGE)
        run_ok(e, "slot", "bind", "zorg-growth", "growth-metrics", DIVERGE)
        rc, out, res = run_ok(e, "explain", DIVERGE)
        sc_ = slot_in(res, DIVERGE)
        check("two repositories at an equal rank with different text: both shown as a divergence, no winner",
              rc == 0 and outcomes_of(sc_) == [("zorg-core", "diverges"), ("zorg-growth", "diverges")] and sc_["winner"] is None
              and sc_["why"] == "рівний ранг 1000, різний текст: zorg-core, zorg-growth" and "decision" not in sc_, (sc_, out[:900]))
        check("…each side's row carries the reason and the command that settles it for that side",
              "  ⚠ zorg-core · блок scope v0.4 у записі " in out and "— розбіжність: рівний ранг 1000, різний текст — вирішити: ctx slot decide product.scope zorg-core" in out
              and "— вирішити: ctx slot decide product.scope zorg-growth" in out, out[:1200])
        rc_d, out_d, _ = run_ok(e, *ctx_args(printed(out, "ctx slot decide product.scope zorg-growth")))
        rc, out, res = run_ok(e, "explain", DIVERGE)
        sc_ = slot_in(res, DIVERGE)
        day = datetime.date.today().isoformat()
        check("the printed decide command runs: the answer wins, the other side lost by it, the decision is shown with its day and the way back",
              rc_d == 0 and outcomes_of(sc_) == [("zorg-growth", "won"), ("zorg-core", "lost")] and sc_["decision"]["winner"] == "zorg-growth"
              and sc_["decision"]["at"] == day and sc_["why"] == "твоє рішення від " + day
              and sc_["candidates"][1]["reason"] == "програв: твоє рішення від " + day and "ctx slot forget product.scope" in out
              and "рішення про розбіжність: zorg-growth" in out, (rc_d, sc_, out[:1200]))
        edit_both(e, "weekly active shoppers", "weekly active buyers")
        run_ok(e, "sync")
        rc, out, res = run_ok(e, "explain", DIVERGE)
        sc_ = slot_in(res, DIVERGE)
        check("a new text from a side: the answer no longer holds, the slot diverges again and the stale decision is named",
              outcomes_of(sc_) == [("zorg-core", "diverges"), ("zorg-growth", "diverges")] and "decision" not in sc_
              and "зараз не діє" in out and sc_["memory"]["decision"]["winner"] == "zorg-growth", (sc_, out[:1400]))

with FakeMcp(tree={GROWTH_PATH: GROWTH_TEXT}) as fake:           # a block that cannot be given to one team
    with tempfile.TemporaryDirectory() as d:
        e = repos_env(d, fake.url, patch=TEAM_TO_NOTES)
        run_ok(e, "migrate", "--apply")
        rc, out, res = run_ok(e, "explain", "team.members")
        alpha, beta = slot_in(res, "team.members", "team.alpha-a"), slot_in(res, "team.members", "team.beta-b")
        check("two teams and the core's team block in a record of its own: for each team the slot is not found, and the block is shown as unplaced",
              rc == 0 and alpha and beta and outcomes_of(alpha) == [("zorg-core", "unplaced")] and outcomes_of(beta) == [("zorg-core", "unplaced")]
              and alpha["winner"] is None and "не знайдено" in out, (rc, res.get("slots"), out[:1500]))
        row = alpha["candidates"][0]
        check("…the unplaced row says why and carries the command that places it with the team (the team's record filled in)",
              row["reason"].startswith("не розміщено") and row["block"] == "team" and row["sub"] == "Members"
              and "  · zorg-core · блок team#Members v0.2 у записі " in out and "— прив'язати: ctx slot bind zorg-core team#Members team.members --team team.alpha-a" in out
              and "--team team.beta-b" in out and "ctx slot bind zorg-core team#Members team.members --team team.alpha-a" in alpha["commands"]
              and "є нерозміщений блок" in out, (row, out[:1500]))
        rc_b, out_b, _ = run_ok(e, *ctx_args(printed(out, "ctx slot bind zorg-core team#Members team.members --team team.alpha-a")))
        rc, out, res = run_ok(e, "explain", "team.members")
        alpha, beta = slot_in(res, "team.members", "team.alpha-a"), slot_in(res, "team.members", "team.beta-b")
        check("the printed bind command runs: the block is shown for that team, and the other team has nothing placed",
              rc_b == 0 and outcomes_of(alpha) == [("zorg-core", "shown")] and alpha["candidates"][0]["how"] == "memory"
              and outcomes_of(beta) == [] and "прив'язка: твоя" in out, (rc_b, out_b[-200:], res.get("slots")))

with FakeMcp(tree={GROWTH_PATH: GROWTH_TEXT}) as fake:           # your own name for a slot
    with tempfile.TemporaryDirectory() as d:
        e = repos_env(d, fake.url, patch=[CORE_NUMBERS])
        run_ok(e, "migrate", "--apply")
        rc, out, res = run_ok(e, "explain", "product.key_metrics")
        km = slot_in(res, "product.key_metrics")
        check("a subsection under a name of your own: the slot is not found, and the command is printed to map it", km["candidates"] == []
              and "  шукав: Key Metrics, Ключові метрики — у Product: Zorg App; блоків із цим слотом немає" in out
              and km["commands"] == ['ctx slot map product.zorg-app "<Назва>" product.key_metrics'], (km, out[:800]))
        rc_m, out_m, _ = run_ok(e, *ctx_args(printed(out, "ctx slot map").replace("<Назва>", "Core numbers")))
        rc, out, res = run_ok(e, "explain", "product.key_metrics")
        km = slot_in(res, "product.key_metrics")
        check("…once mapped it is found, the name is among those looked for, and the memory line says how to take it back",
              rc_m == 0 and outcomes_of(km) == [("mine", "won")] and km["candidates"][0]["heading"] == "Core numbers"
              and km["looked_in"]["names"] == ["Key Metrics", "Ключові метрики", "Core numbers"] and "ctx slot forget product.key_metrics" in out
              and "назва “Core numbers” у product.zorg-app" in out, (rc_m, km, out[:900]))

with FakeMcp(tree={GROWTH_PATH: GROWTH_TEXT}) as fake:           # what could not be read, and several products
    with tempfile.TemporaryDirectory() as d:
        e = repos_env(d, fake.url, patch=[LITE_PRODUCT])
        run_ok(e, "migrate", "--apply")
        rc, out, res = run_ok(e, "explain", "product.jira_key", "org.structure")
        check("several products and none named: the product and team slots are held back with the products named, the organisation's are explained",
              rc == 0 and res["needs_product"] is True and res["products"] == ["Zorg App", "Zorg Lite"] and [s["slot"] for s in res["slots"]] == ["org.structure"]
              and "Zorg App, Zorg Lite" in out and "--product" in out, (rc, res, out[:800]))
        rc, out, res = run_ok(e, "explain", "product.jira_key", "--product", "Zorg Lite")
        check("…--product names the one: its slot is explained", rc == 0 and not res.get("needs_product") and slot_in(res, "product.jira_key")["record"] == "product.zorg-lite"
              and outcomes_of(slot_in(res, "product.jira_key")) == [("mine", "won")], (rc, res.get("slots")))
        mem_path = os.path.join(e.store, ".state", "slots.json")
        os.makedirs(os.path.dirname(mem_path), exist_ok=True)
        open(mem_path, "w", encoding="utf-8", newline="").write("{ not json")
        rc, out, res = run_ok(e, "explain", "product.jira_key", "--product", "Zorg App")
        check("a slots memory that cannot be read: explain goes on without it and says so in one line",
              rc == 0 and "пам'ять слотів не прочитано (slots memory not valid: .state/slots.json" in out and "прив'язки й рішення не застосовано" in out
              and read(mem_path) == "{ not json", (rc, out[:600]))

# --- v3.15.0 Task 7: ctx validate names the bindings that do nothing and the divergences, and proposes bindings (spec §4.2, §4.4, §6, §8)
GROWTH_SUB = ("- **North star:** weekly active shoppers\n<!-- zorg-growth:end id=growth-metrics -->",
              "- **North star:** weekly active shoppers\n\n#### Key Metrics (focus)\n- Weekly active shoppers\n<!-- zorg-growth:end id=growth-metrics -->")
SCOPE_PROPOSAL = {"repo": "zorg-core", "block": "scope", "sub": None, "slot": "product.scope"}
SUB_PROPOSAL = {"repo": "zorg-growth", "block": "growth-metrics", "sub": "Key Metrics (focus)", "slot": "product.key_metrics"}
BINDING_LINE = "warning: slot binding: "


def put_memory(e, *bindings):
    """A slots memory written by hand — the way a catalogue that changed, or a core that took a block away, leaves one."""
    path = os.path.join(e.store, ".state", "slots.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8", newline="").write(json.dumps({"schema": "context-slots-memory/1", "bindings": [
        {"repo": r, "block": b, "sub": s, "slot": x, "team": t} for r, b, s, x, t in bindings]}))


def command_args(out, prefix, **fill):
    """The arguments of the command the output prints from `prefix` on (an empty `ctx slot` when it prints none: a usage error, not a wait on stdin)."""
    command = printed(out, prefix) or "ctx slot"
    for old_, new_ in fill.items():
        command = command.replace("<" + old_ + ">", new_)
    return ctx_args(command)


def lines_with(out, prefix):
    return [l for l in out.splitlines() if l.startswith(prefix)]


with FakeMcp(tree={GROWTH_PATH: GROWTH_TEXT}) as fake:
    with tempfile.TemporaryDirectory() as d:
        e = repos_env(d, fake.url, patch=[GROWTH_SUB])
        run_ok(e, "migrate", "--apply")
        before = full_tree(e.home, e.store, e.vault)
        rc, out, res = run_ok(e, "validate")
        check("validate proposes a binding for each unbound block of a registered repository whose heading answers a slot's names; exit 0 (warnings only)",
              rc == 0 and res.get("slot_proposals") == [SUB_PROPOSAL, SCOPE_PROPOSAL]
              and "warning: proposal: ctx slot bind zorg-core scope product.scope" in out.splitlines()
              and "warning: proposal: ctx slot bind zorg-growth \"growth-metrics#Key Metrics (focus)\" product.key_metrics" in out.splitlines()
              and "proposal: ctx slot bind zorg-core scope product.scope" in res["warnings"], (rc, res.get("slot_proposals"), out[-600:]))
        check("…a block whose heading answers no slot is not proposed (teams, a block of the growth squad's team), and neither is the `team` block — the plugin binds it",
              not any(p["block"] in ("team", "teams") for p in res.get("slot_proposals") or []) and text_of(out).count("warning: proposal:") == 2, res.get("slot_proposals"))
        check("…validate wrote nothing: the home, the store and the vault, directories and times included", full_tree(e.home, e.store, e.vault) == before, "")
        check("…and it proposes nothing about a binding that does nothing: no «slot binding» line, no divergence", BINDING_LINE not in out and "diverges" not in out, out[-500:])

        rc_b, out_b, _ = run_ok(e, *command_args(out, "ctx slot bind zorg-growth"))
        rc, out, res = run_ok(e, "validate")
        check("the printed command runs (a heading with spaces is quoted), and the block is not proposed any more",
              rc_b == 0 and rc == 0 and res.get("slot_proposals") == [SCOPE_PROPOSAL] and text_of(out).count("warning: proposal:") == 1, (rc_b, out_b[-200:], res.get("slot_proposals")))
        rc, out_x, res_x = run_ok(e, "explain", "product.key_metrics")
        km = slot_in(res_x, "product.key_metrics")
        check("…the subsection it bound is the candidate of the slot", km is not None and km["candidates"] and (km["candidates"] or [{}])[0].get("sub") == "Key Metrics (focus)"
              and km["candidates"][0].get("how") == "memory", km)
        run_ok(e, *command_args(out, "ctx slot bind zorg-core scope"))
        rc, out, res = run_ok(e, "validate")
        check("every proposal accepted: none left, slot_proposals is an empty list, nothing else changed", rc == 0 and res.get("slot_proposals") == []
              and "proposal" not in text_of(out) and BINDING_LINE not in out and res["errors"] == [], (rc, out[-400:]))

        # ---- a slots memory that cannot be read is an error: exit 3, the file named, no guesses about bindings
        mem_path = os.path.join(e.store, ".state", "slots.json")
        good = read(mem_path)
        os.chmod(mem_path, 0)
        rc, out, res = run_ok(e, "validate")
        os.chmod(mem_path, stat.S_IRUSR | stat.S_IWUSR)
        check("a slots memory that cannot be read: exit 3, «error: slots memory not readable: .state/slots.json …»; no proposal is guessed from it",
              rc == 3 and "error: slots memory not readable: .state/slots.json" in out and any(x.startswith("slots memory not readable") for x in res["errors"])
              and "proposal" not in text_of(out) and res.get("slot_proposals") == [], (rc, out[-500:]))
        for text, label in (("{ not json", "not JSON"), ('{"schema": "context-slots-memory/9"}', "another schema")):
            open(mem_path, "w", encoding="utf-8", newline="").write(text)
            rc, out, res = run_ok(e, "validate")
            check("…a memory that is %s: the same, exit 3" % label, rc == 3 and "error: slots memory not valid: .state/slots.json" in out
                  and "proposal" not in text_of(out) and read(mem_path) == text, (rc, out[-400:]))
        open(mem_path, "w", encoding="utf-8", newline="").write(good)
        rc, out, res = run_ok(e, "validate")
        check("…the memory back: validate is as it was", rc == 0 and res["errors"] == [], (rc, out[-300:]))

with FakeMcp(tree={GROWTH_PATH: GROWTH_TEXT}) as fake:
    with tempfile.TemporaryDirectory() as d:
        e = repos_env(d, fake.url)
        run_ok(e, "migrate", "--apply")
        rc, out, res = run_ok(e, "validate")
        check("a store with no memory and no growth heading to propose: only the scope block is proposed, and the exit stays 0",
              rc == 0 and res.get("slot_proposals") == [SCOPE_PROPOSAL], (rc, res.get("slot_proposals")))
        put_memory(e, ("zorg-core", "scope", None, "product.nowhere", None), ("zorg-nowhere", "scope", None, "product.scope", None),
                   ("zorg-core", "gone", None, "product.scope", None), ("zorg-core", "team", "Nowhere", "team.members", None))
        before = full_tree(e.home, e.store, e.vault)
        rc, out, res = run_ok(e, "validate")
        said = lines_with(out, BINDING_LINE)
        check("a binding to a slot the catalogue lacks: «warning: slot binding: <repo> <block> → <slot> — <why>»",
              any(l.startswith(BINDING_LINE + "zorg-core scope → product.nowhere — ") and "каталозі" in l for l in said), said)
        check("…to a repository nobody registered", any(l.startswith(BINDING_LINE + "zorg-nowhere scope → product.scope — ") and "не зареєстровано" in l for l in said), said)
        check("…to a block the records lack (the core took it away)", any(l.startswith(BINDING_LINE + "zorg-core gone → product.scope — ") and "блоку немає в записах" in l for l in said), said)
        check("…to a subsection the block lacks: the sub is in the line", any(l.startswith(BINDING_LINE + "zorg-core team#Nowhere → team.members — ")
              and "підсекції «Nowhere»" in l for l in said), said)
        check("…the exit stays 0, each line is in CTX_RESULT warnings without the prefix, validate wrote nothing",
              rc == 0 and len(said) == 4 and all(l[len("warning: "):] in res["warnings"] for l in said) and full_tree(e.home, e.store, e.vault) == before, (rc, said))
        check("…a block that has a binding, even one that does nothing, is not proposed again (the line above says what is wrong with it)",
              res.get("slot_proposals") == [], res.get("slot_proposals"))

        put_memory(e)
        run_ok(e, "slot", "bind", "zorg-core", "scope", "product.scope")
        run_ok(e, "slot", "bind", "zorg-core", "scope", "product.key_metrics")
        rc, out, res = run_ok(e, "validate")
        said = lines_with(out, BINDING_LINE)
        check("a block bound to several slots with a part for only one of them: the other is named — no subsection or line by the slot's names",
              rc == 0 and len(said) == 1 and said[0].startswith(BINDING_LINE + "zorg-core scope → product.key_metrics — ")
              and "підсекції чи рядка за назвами слоту" in said[0], (rc, said))

with FakeMcp(tree={GROWTH_PATH: GROWTH_TEXT}) as fake:           # a block that cannot be given to one team
    with tempfile.TemporaryDirectory() as d:
        e = repos_env(d, fake.url, patch=TEAM_TO_NOTES)
        run_ok(e, "migrate", "--apply")
        rc, out, res = run_ok(e, "validate")
        said = lines_with(out, BINDING_LINE)
        check("team.* without a placement (two teams, the core's team block in a record of its own): a warning that says so, with the teams and the command that places it",
              rc == 0 and len(said) == 1 and said[0].startswith(BINDING_LINE + "zorg-core team#Members → team.members — не розміщено: ")
              and "(team.alpha-a, team.beta-b)" in said[0] and said[0].endswith("— ctx slot bind zorg-core team#Members team.members --team <запис>"),
              (rc, said))
        check("…and the plugin's block is not a proposal", not any(p["block"] == "team" for p in res.get("slot_proposals") or []), res.get("slot_proposals"))
        rc_b, out_b, _ = run_ok(e, *command_args(out, "ctx slot bind zorg-core team#Members", запис="team.alpha-a"))
        rc, out, res = run_ok(e, "validate")
        check("the command, with the team filled in, places the block: no warning is left", rc_b == 0 and rc == 0 and BINDING_LINE not in out, (rc_b, out_b[-200:], out[-400:]))

with FakeMcp(tree={GROWTH_PATH: GROWTH_TEXT}) as fake:           # a divergence between repositories (spec §6)
    with tempfile.TemporaryDirectory() as d:
        e = repos_env(d, fake.url)
        equal_ranks(e)
        run_ok(e, "migrate", "--apply")
        run_ok(e, "slot", "bind", "zorg-core", "scope", DIVERGE)
        run_ok(e, "slot", "bind", "zorg-growth", "growth-metrics", DIVERGE)
        before = full_tree(e.home, e.store, e.vault)
        rc, out, res = run_ok(e, "validate")
        line = "warning: slot product.scope diverges between zorg-core, zorg-growth — ctx slot decide product.scope zorg-core"
        check("two repositories at an equal rank with different text: «slot <slot> diverges between <a>, <b> — ctx slot decide <slot> <repo>», exit 0",
              rc == 0 and line in out.splitlines() and text_of(out).count("diverges between") == 1 and line[len("warning: "):] in res["warnings"], (rc, out[-500:]))
        check("…validate wrote nothing", full_tree(e.home, e.store, e.vault) == before, "")
        rc_d, out_d, _ = run_ok(e, *command_args(out, "ctx slot decide product.scope zorg-core"))
        rc, out, res = run_ok(e, "validate")
        check("the printed command answers it: the divergence is no longer named", rc_d == 0 and rc == 0 and "diverges" not in out, (rc_d, out_d[-200:], out[-300:]))
        edit_both(e, "weekly active shoppers", "weekly active buyers")
        run_ok(e, "sync")
        rc, out, res = run_ok(e, "validate")
        check("…a new text from a side brings the question back (a new hash)", rc == 0 and line in out.splitlines(), (rc, out[-400:]))

with FakeMcp(tree={GROWTH_PATH: GROWTH_TEXT}) as fake:
    with tempfile.TemporaryDirectory() as d:
        e = repos_env(d, fake.url)
        run_ok(e, "migrate", "--apply")
        run_ok(e, "slot", "bind", "zorg-core", "scope", DIVERGE)
        run_ok(e, "slot", "bind", "zorg-growth", "growth-metrics", DIVERGE)
        rc, out, res = run_ok(e, "validate")
        check("different ranks: the stronger wins silently, so there is no divergence to name", rc == 0 and "diverges" not in out, out[-400:])

with FakeMcp(tree={GROWTH_PATH: GROWTH_TEXT}) as fake:           # several products: every product is checked, a divergence is named once
    with tempfile.TemporaryDirectory() as d:
        e = repos_env(d, fake.url, patch=[LITE_PRODUCT])
        equal_ranks(e)
        run_ok(e, "migrate", "--apply")
        run_ok(e, "slot", "bind", "zorg-core", "scope", DIVERGE)
        run_ok(e, "slot", "bind", "zorg-growth", "growth-metrics", DIVERGE)
        rc, out, res = run_ok(e, "validate")
        check("several products and none asked for: validate needs no --product — a divergence only one product sees (the growth block sits in its record, the core's serves all) is named",
              rc == 0 and text_of(out).count("warning: slot product.scope diverges between zorg-core, zorg-growth — ctx slot decide product.scope zorg-core") == 1, (rc, out[-500:]))

GROWTH_REGION_CLI = region_in(FIXTURE_TEXT_CLI, "zorg-growth", "growth-metrics")
GROWTH_TO_NOTES = [(GROWTH_REGION_CLI + "\n\n", ""), ("## Zorg Core Notes\n\n", "## Zorg Core Notes\n\n" + GROWTH_REGION_CLI + "\n\n")]
with FakeMcp(tree={GROWTH_PATH: GROWTH_TEXT}) as fake:
    with tempfile.TemporaryDirectory() as d:
        e = repos_env(d, fake.url, patch=[LITE_PRODUCT] + GROWTH_TO_NOTES)
        equal_ranks(e)
        run_ok(e, "migrate", "--apply")
        run_ok(e, "slot", "bind", "zorg-core", "scope", DIVERGE)
        run_ok(e, "slot", "bind", "zorg-growth", "growth-metrics", DIVERGE)
        rc, out, res = run_ok(e, "validate")
        check("…a divergence both products see (both blocks serve every product) is named once, not once for each",
              rc == 0 and text_of(out).count("diverges between") == 1 and sum("diverges between" in w for w in res["warnings"]) == 1, (rc, out[-500:]))

with tempfile.TemporaryDirectory() as d:                           # no repository registered: nothing to propose, nothing new to say
    e = Env(d)
    run_ok(e, "migrate", "--apply")
    rc, out, res = run_ok(e, "validate")
    check("a store with no registered repository: slot_proposals is an empty list, and no slot line is printed",
          rc == 0 and res.get("slot_proposals") == [] and "proposal" not in text_of(out) and "slot " not in text_of(out), (rc, out[-300:]))

# the documents say what the code does now
pp_fr, cp_fr, lcp_fr = doc("references", "context-provider-protocol.md"), doc("references", "context-protocol.md"), \
    doc("references", "local-context-protocol.md")
sec11_fr = between(pp_fr, "### 12.11 ", "### 12.12 ") if "### 12.12 " in pp_fr else pp_fr[pp_fr.find("### 12.11 "):]
need_fr = [(sec11_fr, ["no fetch, plan or write begins with less than 3 s of the work time left, and a write, once begun, has at least "
                       "those 3 s for its reads", "`held_behind`", "Джерело позаду вашої бази", "the same blocks held behind"]),
           (pp_fr, ["kept_yours, took_rule, awaiting, held, held_behind, rejected, reason, report, snapshot"]),
           (cp_fr, ["⚠ source behind — nothing taken"]),
           (lcp_fr, ["usually milliseconds; up to a few seconds while a registration is still downloading"])]
gone_fr = [(lcp_fr, ["for most runs it costs milliseconds"])]
check("final review: §12.11 (the floor, held_behind, the lag's report part once), §12.7's result keys, the digest's lag mark and step 0c's cost",
      all(not lacks(text, needed) for text, needed in need_fr) and all(not [x for x in bad if x in text] for text, bad in gone_fr),
      ([lacks(text, needed) for text, needed in need_fr], [[x for x in bad if x in text] for text, bad in gone_fr]))

# --- v3.15.0 Task 8: the protocols, step 0c, context-connect 0.5.0 and the configurator say what the resolver does (doc pins)
import ctx_resolve as rv_mod  # noqa: E402
import ctx_slots as sl_mod  # noqa: E402

cp15, pp15, lcp15 = doc("references", "context-protocol.md"), doc("references", "context-provider-protocol.md"), \
    doc("references", "local-context-protocol.md")
cst15, skl15 = doc("skills", "context-connect", "references", "connect-steps.md"), doc("skills", "context-connect", "SKILL.md")
mm15, cfg15 = doc("skills", "plugin-configurator", "references", "maintenance-modes.md"), doc("skills", "plugin-configurator", "SKILL.md")
readme15, hp15 = doc("README.md"), doc("references", "host-profiles.md")


def as_doc(template):
    """A string the code prints with `%s` where a name goes, as a pattern for the documents, which write `<name>` there."""
    return re.escape(template).replace("%s", "<[^>]+>")


def quoted_in(text, templates):
    return [s for s in templates if not re.search(as_doc(s), text)]


# every output string the documents quote is the one the code prints
printed_15 = [rv_mod.ALSO_LINE, rv_mod.DIVERGE_LINE, rv_mod.SHOWN_LINE, rv_mod.SHOWN_SUB_LINE, rv_mod.UNREAD_REGISTRATION,
              rv_mod.UNREAD_MEMORY, sl_mod.STATE_UNREAD, rv_mod.NOTE_LINE, rv_mod.BY_NAME_MARK,
              rv_mod.EDITED_MARK, rv_mod.RULE_MARK, rv_mod.NO_BLOCKS, rv_mod.WHY_LIST, rv_mod.WHY_ONLY, rv_mod.WHY_MINE,
              rv_mod.GONE_BLOCK.split(":")[0]]
check("context-protocol §5f quotes every line of ctx read and ctx explain as the code prints it (ctx_resolve.py, ctx_slots.py)",
      not quoted_in(between(cp15, "## 5f. ", "## 6. "), printed_15), quoted_in(between(cp15, "## 5f. ", "## 6. "), printed_15))
reads_15 = [rv_mod.ALSO_LINE, rv_mod.DIVERGE_LINE, rv_mod.SHOWN_LINE, rv_mod.SHOWN_SUB_LINE, rv_mod.NOTE_LINE, rv_mod.NO_BLOCKS,
            rv_mod.UNPLACED_BLOCK, rv_mod.ELSEWHERE_BLOCK]
check("context-protocol §5a quotes the line of a bound block that cannot be given to one team as the code prints it",
      not quoted_in(between(cp15, "## 5a. ", "## 5b. "), [rv_mod.UNPLACED_BLOCK, rv_mod.NO_BLOCKS, rv_mod.ELSEWHERE_BLOCK]),
      quoted_in(between(cp15, "## 5a. ", "## 5b. "), [rv_mod.UNPLACED_BLOCK, rv_mod.NO_BLOCKS, rv_mod.ELSEWHERE_BLOCK]))
check("step 0c quotes the lines a skill reads as the code prints them", not quoted_in(between(lcp15, "### 0c.", "### 0d."), reads_15),
      quoted_in(between(lcp15, "### 0c.", "### 0d."), reads_15))
check("context-provider-protocol §12.9 quotes the provenance additions and the «також» and divergence lines as the code prints them",
      not quoted_in(between(pp15, "### 12.9 ", "### 12.10 "), [rv_mod.ALSO_LINE, rv_mod.DIVERGE_LINE, rv_mod.NOTE_LINE, rv_mod.BY_NAME_MARK,
                                                              rv_mod.EDITED_MARK, rv_mod.RULE_MARK]),
      quoted_in(between(pp15, "### 12.9 ", "### 12.10 "), [rv_mod.ALSO_LINE, rv_mod.DIVERGE_LINE, rv_mod.NOTE_LINE, rv_mod.BY_NAME_MARK]))

need_15 = [
    (cp15, ["## 5f. Slots, the cascade and `explain` (since v3.15.0)", "`references/context-slots.yaml` (`schema: context-slots/1`)",
            "| `explain [SLOT …] [--skill S] [--product P] [--json]` |", "`slot bind REPO BLOCK[#Subsection] SLOT [--team ID]`",
            "├── slots.json", "`.state/slots.json` since v3.15.0", "adds `op` `slot` with `action`",
            "A guess from a heading never binds a block", "its `jira_project_key` and `jira_team_field` lines are not bound",
            "under the first of the slot's `names` that answers, in the catalogue's order",
            "your explicit mapping beats a name of the catalogue",
            "the first block of that same record that has a subsection or a field under one of the slot's names",
            "A `value` slot compares the value after `**<label>:**`, not the whole line",
            "only when the slot shows more than one candidate or has a «також» line, a note or a divergence",
            "for a `value` slot nothing is taken away", "it is shown in full after those that do",
            "One answer is kept per slot — a second `decide` for another product or team replaces the first",
            "the slots of a product and of a team are held back and one line says `Продукти: …`",
            "`ctx read` and `ctx explain` go on without it and say so in one line", "`ctx validate` reports it as an error and skips the other slot checks",
            "Only the headings are read — not the slot's `about`",
            "a block in `skip_blocks` is not in the records, but one already there is proposed whether or not its id is listed",
            "stays in the memory and has no candidate", "There is no `ctx explain` there, no cascade and no `ctx slot …`",
            "`Key Metrics (focus)` mapped to `product.okrs` is no candidate of `product.key_metrics`",
            "A block that neither you nor its publisher bound to any slot (`ctx slot bind`, `slot=`) answers by its heading",
            "unless the plugin's own `team#Members` gives it the slot's text (a team block whose heading reads `Team Members` still answers by name)",
            "An explicit binding says what the block is, as a heading you mapped to another slot is no candidate of this one",
            "a block you bound to `org.key_metrics` is never a `product.key_metrics` guess", "The plugin's own `team#Members` is no such word",
            "unless a binding of the block gives this slot its text (then it answers through that binding only, even where the binding does not place it)",
            "For a `product.*` slot, and for a `team.*` slot whose binding names no team, a block in another product's record is no candidate",
            "a `team.*` slot's block in the active product's own record needs exactly one team or a binding that names the team, else it is unplaced",
            "places the block with that team wherever it sits, while that team is read", "An `org.*` or `profile.*` slot takes the block from wherever it sits — another product's record too",
            "can carry more than the product's own key (the team's other projects, when the team has more than one), so its value can differ whatever the label",
            "in a slot, the slot shown; in a record read whole, one for each slot the block answers",
            "a new key, or a new meaning of one, needs a new schema, `context-slots-memory/2`", "v3.15.0 treats a `/2` file as a memory it cannot read",
            "One line, printed once before `Відсутнє:` and not under each candidate", "`jira_team_field` is a team's name, not a Jira Team ID",
            "a block id that is not an id (`bind` does not check that the block exists", "the publisher's `slot=` in the begin marker of the block's base",
            "Search — Step 0.5 across several repositories", "entities and cross-links, which also join the items of a list",
            "the overlay, the person and the provider kit — v3.18", "the configurator as a loop", "— v3.18"]),
    (pp15, ["**A slot — `slot=`** (since v3.15.0)", "`<!-- <namespace>:begin id=<block> v=<version> slot=<slot> -->`", "`xslot=` is no attribute",
            "A holder's own binding of the block (`ctx slot bind`) wins over the attribute for the whole block",
            "the plugin binds the block itself", "nothing else of the block is bound",
            "can carry more than a product's own `Jira Project Key` (the team's other projects, when the team has more than one), so its value can differ whatever the label",
            "in a slot, the slot shown; in a record read whole — through `read_by` too — one for each slot the block answers",
            "**A second, narrower exception since v3.15.0: `skip_blocks`.**", "only on your explicit yes for that block",
            "One key is the exception, and only by your own word: `sync`", "since v3.15.0 `ctx read` and `ctx explain` decide a slot by it",
            "`ctx explain` (since v3.15.0), `ctx slot …`, `ctx validate`", "`ctx provider adopt|plan|apply|sync`"]),
    (lcp15, ["**Reading the slots (since v3.15.0).**", "Rely on both and name both sources", "do not choose between them and do not ask the user in the middle of the work",
             "the user's text below it is a note on the rule", "never fill it from memory", "that `ctx slot bind … --team` places it",
             "there is no cascade, no `ctx explain` and no «також» line there", "the block is a fact only if its record is printed in this read"]),
    (cst15, ["### §4c Slots after a refresh (with a store, since v3.15.0)", "**Blocks the user switched off — at a refresh, one message.**",
             "is offered again at the next refresh", "This skill binds nothing without the user's yes", "recommend no side", "`ctx slot bind <repo> <block>[#<Підсекція>] <slot>` first, so that a refusal (exit 3) has changed nothing else",
             "take that one id out of `skip_blocks`", "An id is never added to `skip_blocks` here", "`ctx slot decide <slot> <repo>`",
             "for the second kind keep `ctx slot bind <repo> <block> <slot> --team <team record>` ready",
             "holds for every key except `sync` (and, since v3.15.0, the taking of one id out of `skip_blocks`, below)",
             "**The second exception: one id out of `skip_blocks`** (since v3.15.0)"]),
    (skl15, ["version: 0.5.0", "## Step 4a — slots after a refresh (with a store, since v3.15.0)", "this skill binds only what the user confirms (`ctx slot bind`)", "the publisher's `slot=` and the plugin's own `team#Members` bind without a yes",
             "offered at a refresh, in one message (a no is offered again at the next refresh)", "except a divergence, which recommends no side",
             "and the removal of one id from `skip_blocks` on the user's yes for that block (Step 4a)", "adding an id to `skip_blocks` in Step 4a",
             "(the second exception of `references/context-provider-protocol.md` §3b)", "a no changes nothing",
             "without the user's own yes for that block or slot"]),
    (mm15, ["since v3.15.0 the slots (`references/context-protocol.md` §5f)", "the answer per slot being `ctx slot decide <slot> <repo>`",
            "a yes being `ctx slot bind …` for each confirmed one", "### Context slots (only with a context store)"]),
    (cfg15, ["version: 2.15.2"]),
    (readme15, ["### 32. Context Connect (v0.5.0)", "| Context Connect | v0.5.0 |", "### 10. Plugin Configurator (v2.15.2)", "| Plugin Configurator | v2.15.2 |",
                "**Slots, the cascade and `ctx explain`** (since v3.15.0)", "and — at a refresh — the blocks you had switched off", "since v3.15.0 `explain` and `slot bind|map|prefer|decide|forget`"]),
    (hp15, ["since v3.15.0 slots and the cascade in `ctx read`, `ctx explain`, `ctx slot …`"]),
]
gone_15 = [(pp15, ["no command decides by it yet", "a bound line would put a «також» into every skill that reads the key. The template"]),
           (cp15, ["The resolver (slots, the cascade, `ctx explain`) — v3.15;"]),
           (skl15, ["version: 0.4.0", "offered once, in one message", "and binding is the user's"]),
           (cst15, ["once, one message", "first the one with the later version"]),
           (cp15, ["mapped to `org.key_metrics`"]),
           (cp15, ["A block with no binding (or one that is not one sound region) answers by its heading", "A block in another product's record is no candidate",
                   "needs exactly one team, else it is unplaced", "unless the block has a binding and is one sound region",
                   "carries more than the product's own key", "so its value differs whatever the label", "one for each slot it answers, wherever it is printed",
                   "A block that no binding gives the slot a text", "A block bound to other slots only, or whose binding finds nothing for this slot"]),
           (pp15, ["carries more than a product's own `Jira Project Key`", "so its value differs whatever the label",
                   "wherever it is printed — a record read whole through `read_by` too", "no binding of it gives this slot a text"]),
           (readme15, ["and — once — the blocks you had switched off", "Context Connect (v0.4.0)", "| Context Connect | v0.4.0 |", "Plugin Configurator (v2.15.1)"])]
check("v3.15.0 docs: §5f, the §3 rows, the memory in §1 and §8, the host row and the roadmap of context-protocol; slot= and the second exception in "
      "context-provider-protocol; step 0c; connect-steps §4c; the skill's Step 4a; Validate; the README; none of the outdated sentences stays",
      all(not lacks(text, needed) for text, needed in need_15) and all(not [x for x in bad if x in text] for text, bad in gone_15),
      ([lacks(text, needed) for text, needed in need_15], [[x for x in bad if x in text] for text, bad in gone_15]))
i_s, i_f = lcp15.find("**Reading the slots (since v3.15.0).**"), lcp15.find("- **FS without SHELL:**")
i_r = lcp15.find("- **SHELL available — then the read:**")
check("step 0c: the slot lines come after the read and before the host without a shell", 0 <= i_r < i_s < i_f, (i_r, i_s, i_f))
i_4, i_4a, i_5 = skl15.find("## Step 4 — "), skl15.find("## Step 4a — "), skl15.find("## Step 5 — ")
check("the skill: Step 4a between Step 4 and Step 5", 0 <= i_4 < i_4a < i_5, (i_4, i_4a, i_5))

ids3150 = ["TC-ctx-3150-%s" % k for k in ("slots", "resolve", "read", "explain", "validate", "slot", "docs", "acceptance")]
head3150 = "## Release v3.15.0 — slots, the cascade and explain (added 2026-10-19)"
check("test-cases.md has the v3.15.0 section above v3.14.0 with one TC-ctx-3150-* row per area; Testing-process lists the two new test files",
      head3150 in tc and 0 <= tc.index(head3150) < tc.index("## Release v3.14.0") and not [i for i in ids3150 if "**%s**" % i not in tc]
      and "testing/ctx_slots_test.py" in read(ROOT, "testing", "Testing-process.md") and "testing/ctx_resolve_test.py" in read(ROOT, "testing", "Testing-process.md"),
      [i for i in ids3150 if "**%s**" % i not in tc])

# --- v3.16.0 Task 7: ctx search — one candidate per note, flags and provenance, --get for one section
import socket, sqlite3, unicodedata  # noqa: E402

SEARCH_FIX = os.path.join(ROOT, "testing", "fixtures", "search")
BRAIN_RELS = ("Notes/Кошик — графік роботи продавця.md", "Notes/Roadmap Q4 — draft v3.md", "Notes/Mobile cart notes.md",
              "Growth/Cart experiments.md")


def search_brain(path, vault, rels, extra=()):
    """A user's own local index (zorg-brain) in the shape it has in the wild: `path` in notes_fts, meta k/v `vault`.
    `extra`: (path, text) pairs for notes whose file is not read here."""
    if os.path.exists(path):
        os.remove(path)
    con = sqlite3.connect(path)
    con.executescript("CREATE TABLE notes(path TEXT PRIMARY KEY, title TEXT, type TEXT, date TEXT, status TEXT, fm_json TEXT);"
                      "CREATE VIRTUAL TABLE notes_fts USING fts5(path UNINDEXED, title, body,"
                      " tokenize='unicode61 remove_diacritics 2');"
                      "CREATE TABLE meta(k TEXT PRIMARY KEY, v TEXT);")
    con.execute("INSERT INTO meta VALUES ('vault', ?)", (vault,))
    for rel, text in [(r, read(vault, *r.split("/"))) for r in rels] + list(extra):
        title = rel.rsplit("/", 1)[-1][:-3]
        con.execute("INSERT INTO notes(path, title) VALUES (?, ?)", (rel, title))
        con.execute("INSERT INTO notes_fts(path, title, body) VALUES (?, ?, ?)", (rel, title, text))
    con.commit()
    con.close()


class SearchEnv(Env):
    """The fictional Zorg vault of testing/fixtures/search/ (the plugin folder Notes/, the core ZorgCore/ registered as
    zorg-core) and its home (the team glossary), a mirror-only note Growth/Cart experiments.md, and — unless brain is
    False, then local-context.md has no Vault Search MCP line — a user's own local index zorg-brain over a part of it."""

    def __init__(self, d, brain=True):
        self.home, self.vault = os.path.join(d, "home"), os.path.join(d, "vault")
        shutil.copytree(os.path.join(SEARCH_FIX, "home"), self.home)
        shutil.copytree(os.path.join(SEARCH_FIX, "vault"), self.vault)
        for dp, _, names in os.walk(self.vault):
            for n in names:
                text = read(dp, n) if n.endswith(".yaml") else ""
                if "{{VAULT}}" in text:
                    open(os.path.join(dp, n), "w", encoding="utf-8").write(text.replace("{{VAULT}}", self.vault))
        self.add("Growth/Cart experiments.md", "---\ntype: ab-test-results\nproduct: Zorg App\ndate: 2026-08-01\n---\n"
                 "# Cart experiments\n\nThe mobile cart test: the seller's hours under each block lifted the paid orders.\n")
        text = read(SEARCH_FIX, "context.md").replace("{{VAULT}}", self.vault).replace("{{HOME}}", self.home)
        self.text = text if brain else text[:text.index("### Vault Search MCP")]
        self.ctx = os.path.join(self.home, ".grow-pm", "local-context.md")
        open(self.ctx, "w", encoding="utf-8", newline="").write(self.text)
        self.store = os.path.join(self.vault, "Notes", "_System", "context")
        self.brain = os.path.join(self.home, "zorg-brain.sqlite")
        self.index = os.path.join(self.home, ".grow-pm", "index")
        if brain:
            search_brain(self.brain, self.vault, BRAIN_RELS)

    def add(self, rel, text):
        p = os.path.join(self.vault, *rel.split("/"))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "w", encoding="utf-8", newline="").write(text)


def tree(top):
    return tree_of(top)


def by_title(res, title):
    return next((c for c in (res or {}).get("candidates", []) if c["title"] == title), None)


def by_path(res, path):
    return next((c for c in (res or {}).get("candidates", []) if c["path"] == path), None)


def closed_url():
    """An MCP endpoint on a local port nothing listens on: the network is not there."""
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return "http://127.0.0.1:%d/mcp" % port


KOSHYK = "Notes/Кошик — графік роботи продавця.md"
with tempfile.TemporaryDirectory() as d:
    env = SearchEnv(d)
    before = tree(env.store)
    home_before = {p: b for p, b in tree_of(env.home).items() if not p.startswith(env.index)}
    rc, out, res = run_ok(env, "search", "--q", "графік роботи продавця", "--q", "seller working hours", "--json")
    check("ctx search --json: exit 0, nothing but the CTX_RESULT line", rc == 0 and res
          and out.strip().startswith("CTX_RESULT ") and out.strip().count("\n") == 0, (rc, out[-500:]))
    check("…CTX_RESULT: command search, candidates, notes, sources, index", res and res.get("command") == "search"
          and {"candidates", "notes", "sources", "index"} <= set(res) and "last" not in res, res and sorted(res))
    paths = [c["path"] for c in res["candidates"]]
    check("one candidate per file across own index and zorg-brain", len(paths) == len(set(paths)), paths)
    k = by_path(res, KOSHYK)
    check("…the note both found is one candidate of both sources", k and k["source"] == ["own", "zorg-brain"], k)
    check("…at most two sections of one note, the first its own heading", k and len(k["sections"]) == 2
          and k["sections"][0] == {"id": k["id"], "heading": k["heading"]}
          and all(1 <= len(c["sections"]) <= 2 for c in res["candidates"]), k and k["sections"])
    c = by_title(res, "Roadmap Q4 — draft v3")
    check("the newer draft stays, the older is named", c and "є старіші версії: 1" in c["flags"]
          and not by_title(res, "Roadmap Q4 — draft v2"), [(x["title"], x["flags"]) for x in res["candidates"]])
    check("every candidate: id, path, heading, title, type, product, date, source, flags, matched, snippet, score",
          res["candidates"] and all({"id", "path", "heading", "title", "type", "product", "date", "source", "flags", "matched",
                                     "snippet", "score"} <= set(x) for x in res["candidates"]), res["candidates"][:1])
    check("…the id is the first 10 hex of sha1(path#heading)", all(x["id"] == hashlib.sha1(
        ("%s#%s" % (x["path"], x["heading"])).encode("utf-8")).hexdigest()[:10] for x in res["candidates"]))
    check("…the sources asked, each with whether it answered", res["sources"] == [
        {"id": "own", "kind": "own", "answered": True}, {"id": "zorg-brain", "kind": "local", "answered": True}], res["sources"])
    check("…the index state: refreshed before the search", (res.get("index") or {}).get("files") == 19
          and (res.get("index") or {}).get("added") == 19, res.get("index"))
    rc2, out2, res2 = run_ok(env, "search", "--q", "standup seller notice")
    check("a date series is not folded", by_title(res2, "Standup 2026-10-01") and by_title(res2, "Standup 2026-10-08"),
          res2 and [x["title"] for x in res2["candidates"]])
    rc3, out3, res3 = run_ok(env, "search", "--q", "Epic PROJ-77")
    check("the core page and its hub are one candidate", sum(1 for x in res3["candidates"] if x["title"] == "Epic — PROJ-77") == 1,
          res3 and [(x["path"], x["flags"]) for x in res3["candidates"]])
    e3 = by_title(res3, "Epic — PROJ-77")
    check("…the one with more text stays, the hub named as its twin", e3 and e3["path"] == "ZorgCore/Epics/Epic — PROJ-77.md"
          and "двійник Notes/Epics/Epic — PROJ-77.md" in e3["flags"], e3)
    check("…a core page names its repository as its source", e3 and e3["source"] == ["zorg-core"], e3)
    rc, out, _ = run_ok(env, "search", "--get", e3["id"]) if e3 else (None, "", None)
    check("…and so does its --get line", rc == 0 and out.startswith("> [zorg-core · ZorgCore/Epics/Epic — PROJ-77.md › "),
          (rc, out[:200]))
    check("search writes nothing to the store", tree(env.store) == before)
    rc4, out4, res4 = run_ok(env, "search", "--q", "що і як?")
    check("an all-stop query is exit 0 with no candidates", rc4 == 0 and res4 and res4["candidates"] == [], (rc4, out4[-300:]))
    h, t = run_ok(env, "search", "--get", res["candidates"][0]["id"])[1:3]
    check("--get prints the provenance line and the section", "> [own · " in h, h[-400:])
    check("…the line `> [<source> · <path> › <heading> · <day>]` first, then the section's text; CTX_RESULT action get",
          re.match(r"^> \[own · %s › .+ · \d{4}-\d{2}-\d{2}\]\n" % re.escape(res["candidates"][0]["path"]), h)
          and t and t.get("action") == "get" and t.get("id") == res["candidates"][0]["id"], (h[:300], t))
    rc5, out5, res5 = run_ok(env, "search", "--get", res["candidates"][0]["id"], "--json")
    check("…--get --json: the header and the text in CTX_RESULT", rc5 == 0 and res5 and res5.get("text")
          and res5.get("header", "").startswith("> [own · ") and out5.strip().count("\n") == 0, (rc5, out5[-300:]))
    rc, out, _ = run_ok(env, "search", "--get", "0000000000")
    check("--get of an id no search gave: exit 3, one line why", rc == 3 and "0000000000" in out, (rc, out[-300:]))
    check("search writes only <home>/.grow-pm/index/ — last.json beside the index",
          {p: b for p, b in tree_of(env.home).items() if not p.startswith(env.index)} == home_before
          and os.path.isfile(os.path.join(env.index, "last.json")))

    rc, out, res = run_ok(env, "search", "--q", "графік роботи продавця", "--q", "seller working hours")
    lines = out.splitlines()
    k = by_path(res, KOSHYK)
    check("human output: `Пошук: <n> варіант(и) · джерела: <ids> · кандидатів <k>` first", rc == 0
          and lines[0] == "Пошук: 2 варіанти · джерела: own, zorg-brain · кандидатів %d" % len(res["candidates"]), lines[:2])
    head = next((l for l in lines if l.startswith("%d. " % (res["candidates"].index(k) + 1))), "") if k else ""
    check("…`N. <title> › <heading> · <sources> · <type> · <date>`", head.startswith("%d. Кошик — графік роботи продавця › "
                                                                                       % (res["candidates"].index(k) + 1))
          and head.endswith(" · own, zorg-brain · concept · 2026-09-15"), head)
    i = lines.index(head) if head in lines else -1
    check("…then the snippet in «» and `id <id> · варіанти <i,…>`", i >= 0 and "«" in lines[i + 1]
          and lines[i + 2].strip() == "id %s · варіанти 1,2" % k["id"], lines[i:i + 4])
    check("…and the CTX_RESULT line last", lines[-1].startswith("CTX_RESULT "))
    rc, out, res = run_ok(env, "search", "--q", "seller working hours", "--limit", "3", "--json")
    check("--limit 3 gives at most 3", rc == 0 and 0 < len(res["candidates"]) <= 3, res and len(res["candidates"]))
    rc, out, res = run_ok(env, "search", "--q", "delivery slot", "--json")
    ds = [x for x in res["candidates"] if x["title"] == "Delivery slots"]
    check("key 2: the Confluence page twice on disk is one candidate, the newer, the other named its twin",
          len(ds) == 1 and ds[0]["path"] == "Notes/Knowledge/Delivery slots (900100200).md"
          and "двійник ZorgCore/Pages/Delivery slots (900100200).md" in ds[0]["flags"], ds)
    rc, out, res = run_ok(env, "search", "--q", "commission small sellers", "--json")
    pr = by_title(res, "Pricing review 2026-09-30")
    check("a sensitive note is marked `sensitive`", pr and "sensitive" in pr["flags"], pr)
    rc, out, res = run_ok(env, "search", "--q", "Bea Two data analyst", "--json")
    bea = by_path(res, "ZorgCore/People/bea-two.md")
    check("a person card is a hub", bea and "хаб" in bea["flags"], bea)
    rc, out, res = run_ok(env, "search", "--q", "seller merchant tone", "--json")
    sg = by_title(res, "Zorg Style Guide")
    check("…and so is the Zorg Style Guide", sg and "хаб" in sg["flags"], sg)

    env.add("Notes/Archive/Mobile cart notes (copy).md", read(env.vault, "Notes", "Mobile cart notes.md"))
    rc, out, res = run_ok(env, "search", "--q", "mobile cart interviews", "--json")
    mc = [x for x in res["candidates"] if x["title"] == "Mobile cart notes"]
    check("key 3: the same content twice is one candidate, the other named its twin", len(mc) == 1
          and mc[0]["path"] == "Notes/Mobile cart notes.md" and "двійник Notes/Archive/Mobile cart notes (copy).md" in mc[0]["flags"],
          [(x["path"], x["flags"]) for x in res["candidates"]])

    nfc = "Мій кошик — відгуки покупців.md"
    nfd = unicodedata.normalize("NFD", nfc)
    body = "# Мій кошик — відгуки покупців\n\nВідгуки покупців про мобільний кошик: графік продавця видно не всім.\n"
    env.add("Notes/" + nfd, body)
    search_brain(env.brain, env.vault, BRAIN_RELS, extra=[("Notes/" + nfc, body)])
    check("(the file name is decomposed on disk)", nfd in os.listdir(os.path.join(env.vault, "Notes")) and nfd != nfc)
    rc, out, res = run_ok(env, "search", "--q", "відгуки покупців", "--json")
    mine = [x for x in res["candidates"] if unicodedata.normalize("NFC", x["path"]) == "Notes/" + nfc]
    check("NFD on disk and NFC in zorg-brain: one candidate of both, its path NFC", len(mine) == 1
          and mine[0]["path"] == "Notes/" + nfc and mine[0]["source"] == ["own", "zorg-brain"], mine)

    for args, why in ((("search",), "neither --q nor --get"), (("search", "--q", "x", "--sources", "own,web"), "an unknown source"),
                      (("search", "--q", "x", "--limit", "0"), "a limit below 1"), (("search", "--q", "x", "--skill", "no-such-skill"),
                                                                                  "an unknown skill")):
        rc, out, res = run_ok(env, *args)
        check("search with %s: exit 3" % why, rc == 3 and res and res.get("ok") is False, (rc, out[-300:]))
    rc, out, res = run_ok(env, "search", "--q", "seller", "--skill", "write-concept", "--product", "Zorg App", "--no-hints", "--json")
    check("--skill, --product and --no-hints are taken", rc == 0 and res["candidates"], (rc, out[-300:]))

    shutil.rmtree(env.store)
    rc, out, res = run_ok(env, "search", "--q", "графік роботи продавця", "--json")
    check("no store: search still works", rc == 0 and by_path(res, KOSHYK), (rc, out[-300:]))
    import ctx as ctx_cli  # noqa: E402
    a = ctx_cli.build_parser().parse_args(["search", "--q", "x"])
    check("search is no writing command of the store", "search" not in ctx_cli.WRITING and not ctx_cli.writes(a))

with tempfile.TemporaryDirectory() as d:
    env = SearchEnv(d)
    open(os.path.join(env.vault, "Notes", "_System", "providers", "zorg-growth.yaml"), "w", encoding="utf-8").write(
        "schema: provider-registration/2\nid: zorg-growth\ntitle: Zorg growth\nkind: mcp\nauthority: team\n"
        "endpoint:\n  url: %s\n  root: \"Growth/\"\nstatus: active\n" % closed_url())
    rc, out, res = run_ok(env, "search", "--q", "mobile cart", "--sources", "mcp")
    check("--sources mcp with no network: exit 5, one line about the repository", rc == 5 and res and res.get("ok") is False
          and "zorg-growth не відповів — без нього" in out, (rc, out[-400:]))
    rc, out, res = run_ok(env, "search", "--q", "mobile cart", "--json")
    check("…without --sources the other sources answer: exit 0 with the line", rc == 0 and res["candidates"]
          and "zorg-growth не відповів — без нього" in res["notes"], (rc, res and res["notes"]))

with tempfile.TemporaryDirectory() as d:
    env = SearchEnv(d, brain=False)
    rc, out, res = run_ok(env, "search", "--q", "графік роботи продавця", "--q", "seller working hours", "--json")
    check("without zorg-brain and without network: the section index alone", rc == 0 and res["sources"] == [
        {"id": "own", "kind": "own", "answered": True}] and by_path(res, KOSHYK), (rc, res and res["sources"]))
    rc, out, _ = run_ok(env, "search", "--get", by_path(res, KOSHYK)["id"])
    check("…and --get of what it found", rc == 0 and out.startswith("> [own · %s › " % KOSHYK), (rc, out[:300]))

with tempfile.TemporaryDirectory() as d:            # fix round 1: searches at once; a save that fails; a busy index
    env = SearchEnv(d)
    run_ok(env, "search", "--q", "seller")             # the index built once
    penv = dict(os.environ)
    penv.pop("GROW_PM_CONTEXT_PATH", None)
    runs = []
    for _ in range(2):
        ps = [subprocess.Popen([sys.executable, CTX, "search", "--q", q, "--json", "--home", env.home, "--context", env.ctx],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=penv)
              for q in ("seller working hours", "графік роботи продавця", "delivery slot", "mobile cart", "Epic PROJ-77",
                        "standup")]
        runs += [p.communicate(timeout=120) + (p.returncode,) for p in ps]
    check("six searches at the same moment, twice: every one exits 0 with its CTX_RESULT",
          all(rc == 0 and so.strip().splitlines()[-1].startswith("CTX_RESULT ") for so, se, rc in runs),
          [(rc, so[-200:], se[-200:]) for so, se, rc in runs if rc != 0][:2])
    check("…last.json parses and no temp file is left beside it",
          isinstance(json.load(open(os.path.join(env.index, "last.json"), encoding="utf-8")), dict)
          and not [n for n in os.listdir(env.index) if n.endswith(".tmp")], os.listdir(env.index))
    rc, out, res = run_ok(env, "search", "--q", "cart experiments", "--json")
    gx = by_path(res, "Growth/Cart experiments.md")
    run_ok(env, "search", "--q", "standup")
    rc, out, _ = run_ok(env, "search", "--get", gx["id"]) if gx else (None, "", None)
    check("one search keeps another's ids: --get of a zorg-brain note an earlier search found still works",
          rc == 0 and out.startswith("> [zorg-brain · Growth/Cart experiments.md · "), (rc, out[:200]))
    os.remove(os.path.join(env.index, "last.json"))
    os.makedirs(os.path.join(env.index, "last.json"))
    rc, out, res = run_ok(env, "search", "--q", "seller working hours", "--json")
    check("last.json that cannot be written: the search still exits 0 with its candidates, one line says so",
          rc == 0 and res["candidates"] and any(n.startswith("ідентифікатори пошуку не збережено (") for n in res["notes"]),
          (rc, res and res["notes"]))
    os.rmdir(os.path.join(env.index, "last.json"))
    db = os.path.join(env.index, "sections.sqlite")
    hold = sqlite3.connect(db, timeout=1)
    hold.execute("BEGIN EXCLUSIVE")
    try:
        rc, out, res = run_ok(env, "search", "--q", "seller", "--sources", "own")
    finally:
        hold.rollback()
        hold.close()
    check("the own index busy (another process writes it) as the only source: exit 5 and the busy line, no rebuild",
          rc == 5 and "індекс пошуку зайнятий іншим процесом — цього разу без нього" in out and res
          and res["sources"] == [{"id": "own", "kind": "own", "answered": False}] and not os.path.exists(db + ".broken"),
          (rc, out[-500:]))
    rc, out, res = run_ok(env, "search", "--q", "seller", "--sources", "own", "--json")
    check("…once it is free the same index answers", rc == 0 and res["candidates"] and res["index"]["files"] == 19,
          (rc, res and res.get("index")))

with tempfile.TemporaryDirectory() as d:
    env = SearchEnv(d, brain=False)
    env.text = env.text[:env.text.index("## Obsidian Vaults")]
    open(env.ctx, "w", encoding="utf-8").write(env.text)
    rc, out, res = run_ok(env, "search", "--q", "seller")
    check("no vault, no repository and no source: exit 3", rc == 3 and res and res.get("ok") is False, (rc, out[-300:]))

# --- v3.16.0 Task 8: remembered picks (ctx search remember|forget), the golden set and ctx search eval
GOLDEN_ZORG = os.path.join(SEARCH_FIX, "golden.zorg.yaml")
AGENT_EVAL = os.path.join(ROOT, "testing", "search_agent_eval.py")
# (n, recall50, recall50_q_only) of `ctx search eval` on golden.zorg.yaml without hints — pinned once, when the set was
# built (13 rows with an answer; with their variants only «плата за продаж» misses, the question alone also misses
# «години відкриття магазину», «Беа Ту аналітик», «чекаут таймаут» and «слоти»). Re-pinned only deliberately, with a line
# in the run's journal.
PINNED = (13, 0.923, 0.615)
MOBILE = "Notes/Mobile cart notes.md"


def memory_of(env):
    return json.loads(read(env.store, ".state", "search.json"))


with tempfile.TemporaryDirectory() as d:
    env = SearchEnv(d)
    rc, out, res = run_ok(env, "search", "remember", "--q", "мобільний кошик", "--pick", MOBILE)
    check("no store: remember exits 3 «немає сховища — підказку не збережено»", rc == 3 and res and res.get("ok") is False
          and "немає сховища — підказку не збережено" in out and not os.path.exists(os.path.join(env.store, ".state")), (rc, out[-300:]))
    rc, out, res = run_ok(env, "search", "eval", "--json")
    check("no store and no --golden: eval exits 3", rc == 3 and res and res.get("ok") is False and "--golden" in out, (rc, out[-300:]))
    shutil.rmtree(os.path.join(env.store, "records"))
    rc, out, _ = run_ok(env, "migrate", "--apply")
    check("(the fixture's store migrated)", rc == 0, out[-300:])

    rc, _, res = run_ok(env, "search", "remember", "--q", "мобільний кошик", "--pick", "Notes/Mobile cart notes.md")
    check("remember writes the memory, a snapshot and a journal line", rc == 0 and last_journal(env)["op"] == "search")
    j = last_journal(env)
    check("…the journal line: op search, action, q, source ctx-search, the snapshot",
          (j.get("action"), j.get("q"), j.get("source")) == ("remember", "мобільний кошик", "ctx-search")
          and j.get("snapshot") and os.path.isdir(j["snapshot"]) and res.get("snapshot") == j["snapshot"], j)
    mem = memory_of(env)
    check("….state/search.json: context-search-memory/1, the request's stems sorted, good, the day", mem["schema"]
          == "context-search-memory/1" and len(mem["hints"]) == 1 and mem["hints"][0]["terms"] == ["кошик", "мобільн"]
          and mem["hints"][0]["good"] == [MOBILE] and mem["hints"][0]["bad"] == []
          and re.match(r"^\d{4}-\d{2}-\d{2}$", mem["hints"][0]["at"]), mem)
    c = by_path(run_ok(env, "search", "--q", "мобільний кошик", "--json")[2], "Notes/Mobile cart notes.md")
    check("a remembered pick is boosted and named", c and any(f.startswith("твій вибір від ") for f in c["flags"]))
    n = len(read(env.store, ".state", "journal.jsonl").splitlines())
    rc, out, res = run_ok(env, "search", "remember", "--q", "кошик мобільний", "--pick", MOBILE)
    check("the same pick again: unchanged, no snapshot, no journal line", rc == 0 and res.get("changed") is False
          and "unchanged" in out and len(read(env.store, ".state", "journal.jsonl").splitlines()) == n, (rc, out[-300:]))
    check("undo takes the hint back", run_ok(env, "undo")[0] == 0 and not os.path.exists(os.path.join(env.store, ".state", "search.json")))

    before_vault = tree(env.vault)
    home_before = {p: b for p, b in tree_of(env.home).items() if not p.startswith(env.index)}
    last_before = read(env.index, "last.json")
    res = run_ok(env, "search", "eval", "--golden", GOLDEN_ZORG, "--no-hints", "--json")[2]
    check("eval on the Zorg set gives the pinned numbers", (res["n"], round(res["recall50"], 3), round(res["recall50_q_only"], 3)) == PINNED,
          res and (res.get("n"), res.get("recall50"), res.get("recall50_q_only"), [r for r in res.get("rows", []) if r.get("rank") is None]))
    check("…CTX_RESULT {command search, action eval, mrr, by_class, the empty rows}", res.get("command") == "search"
          and res.get("action") == "eval" and isinstance(res.get("mrr"), float) and res.get("empty_n") == 2
          and isinstance(res.get("empty_top5_mean"), float) and set(res.get("by_class") or {}) == {
              "форма", "синонім", "англ", "рос", "питання", "абревіатура", "транслітерація", "ключ", "коротко", "справжній"}
          and res["by_class"]["синонім"]["n"] == 2 and res.get("hints") == 0, res and {k: res.get(k) for k in ("mrr", "empty_n", "by_class")})
    check("…eval writes nothing but the index: the vault (the store in it) and the home as they were, last.json too",
          tree(env.vault) == before_vault and {p: b for p, b in tree_of(env.home).items() if not p.startswith(env.index)}
          == home_before and read(env.index, "last.json") == last_before)
    rc, out, _ = run_ok(env, "search", "eval", "--golden", GOLDEN_ZORG, "--no-hints")
    check("…the human output: the set, recall@50 with the variants and of the question alone, MRR, a line per class",
          rc == 0 and "recall@50" in out and "лише q" in out and "MRR" in out and "\n  синонім: 2 · " in out
          and "порожні: 2" in out, out[-900:])
    rc, out, res = run_ok(env, "search", "eval", "--json")
    check("eval without --golden reads <store>/search/golden.yaml: none there is exit 3", rc == 3
          and "search/golden.yaml" in out, (rc, out[-300:]))
    os.makedirs(os.path.join(env.store, "search"))
    shutil.copy(GOLDEN_ZORG, os.path.join(env.store, "search", "golden.yaml"))
    rc, out, res = run_ok(env, "search", "eval", "--json")
    check("…with it there, the same numbers", rc == 0 and (res["n"], round(res["recall50"], 3), round(res["recall50_q_only"], 3))
          == PINNED, (rc, out[-300:]))

    found = run_ok(env, "search", "--q", "корзина мобильная", "--json")[2]
    kz = by_path(found, "Notes/Корзина 2.0 (mobile).md")
    rc, out, res = run_ok(env, "search", "remember", "--q", "мобільна корзина", "--pick", kz["id"], "--not", MOBILE,
                          "--product", "Zorg App")
    hint = next((h for h in memory_of(env)["hints"] if h["q"] == "мобільна корзина"), {})
    check("remember --pick ID: the id of the last search is its section, `path#heading`; --not and --product kept",
          rc == 0 and hint.get("good") == ["Notes/Корзина 2.0 (mobile).md#" + kz["heading"]] and hint.get("bad") == [MOBILE]
          and hint.get("product") == "Zorg App", (rc, hint, out[-300:]))
    res = run_ok(env, "search", "--q", "мобільна корзина", "--product", "Zorg App", "--json")[2]
    check("…a `--not` note is marked `ти казав «не те»`, the pick `твій вибір від <день>`",
          "ти казав «не те»" in (by_path(res, MOBILE) or {}).get("flags", [])
          and any(f.startswith("твій вибір від ") for f in (by_path(res, "Notes/Корзина 2.0 (mobile).md") or {}).get("flags", [])),
          res and [(c["path"], c["flags"]) for c in res["candidates"][:4]])
    rc, out, res = run_ok(env, "search", "eval", "--golden", GOLDEN_ZORG, "--json")
    check("eval with the hints: each hint with a pick is one more row `source: choice`, class вибір",
          rc == 0 and res["n"] == PINNED[0] + 1 and res["hints"] == 1 and res["by_class"]["вибір"]["n"] == 1
          and any(r["source"] == "choice" for r in res["rows"]), res and (res.get("n"), res.get("hints")))
    rc, out, res = run_ok(env, "search", "forget", "--q", "корзина мобільна")
    j = last_journal(env)
    check("forget removes the hint of the request: snapshot, journal line action forget", rc == 0 and res.get("changed") is True
          and (j.get("op"), j.get("action"), j.get("q")) == ("search", "forget", "корзина мобільна")
          and not [h for h in memory_of(env)["hints"] if h["q"] == "мобільна корзина"], (rc, j, out[-300:]))
    rc, out, res = run_ok(env, "search", "forget", "--q", "корзина мобільна")
    check("…nothing left to forget: unchanged, exit 0", rc == 0 and res.get("changed") is False and "unchanged" in out, (rc, out[-300:]))
    for args, why in ((("search", "remember", "--q", "кошик"), "remember without --pick or --not"),
                      (("search", "remember", "--q", "кошик", "--pick", "fedcba9876"), "an id no search gave"),
                      (("search", "remember", "--q", "що і як", "--pick", MOBILE), "a request with no words to remember"),
                      (("search", "forget", "--q", "кошик", "--pick", MOBILE), "forget with --pick"),
                      (("search", "eval", "--q", "кошик"), "eval with --q"),
                      (("search", "--q", "кошик", "--pick", MOBILE), "a plain search with --pick"),
                      (("search", "remember", "--q", "кошик", "--pick", MOBILE, "--store", env.store), "remember with --store")):
        rc, out, res = run_ok(env, *args)
        check("search: %s is exit 3" % why, rc == 3 and res and res.get("ok") is False, (rc, out[-300:]))
    import ctx as ctx_cli  # noqa: E402
    p = ctx_cli.build_parser()
    check("writes(): search remember and forget write the store; eval and a plain search do not",
          ctx_cli.writes(p.parse_args(["search", "remember", "--q", "x", "--pick", "a.md"]))
          and ctx_cli.writes(p.parse_args(["search", "forget", "--q", "x"]))
          and not ctx_cli.writes(p.parse_args(["search", "eval"])) and not ctx_cli.writes(p.parse_args(["search", "--q", "x"])))

    # the model level: search_agent_eval.py prepares the batches and scores the answers (criteria 1–3 of the spec)
    out_dir = os.path.join(d, "batches")
    penv = dict(os.environ)
    penv.pop("GROW_PM_CONTEXT_PATH", None)
    p = subprocess.run([sys.executable, AGENT_EVAL, "prepare", "--golden", GOLDEN_ZORG, "--out", out_dir, "--home", env.home,
                        "--context", env.ctx, "--batch", "6"], capture_output=True, text=True, env=penv, timeout=600)
    files = sorted(os.listdir(out_dir)) if os.path.isdir(out_dir) else []
    items = [x for f in files for x in json.load(open(os.path.join(out_dir, f), encoding="utf-8"))]
    check("prepare: the rows in batches of --batch, each {q, variants, candidates}", p.returncode == 0
          and files == ["batch-001.json", "batch-002.json", "batch-003.json"] and len(items) == 15
          and all({"q", "variants", "candidates"} <= set(x) for x in items), (p.returncode, files, p.stdout[-300:], p.stderr[-300:]))
    check("…never the answers: no good, ok or bad in a batch", not any({"good", "ok", "bad"} & set(x) for x in items))
    first = next((x for x in items if x["q"] == "графіком роботи продавців"), {})
    check("…the candidates of `ctx search --json` for the question and its variants",
          first.get("variants") == ["графік роботи продавця", "график работы продавца", "seller working hours"]
          and any(c["path"] == "Notes/Кошик — графік роботи продавця.md" for c in first.get("candidates", [])), first)
    answers = os.path.join(d, "answers")
    os.makedirs(answers)
    open(os.path.join(answers, "a.json"), "w", encoding="utf-8").write(json.dumps({
        "графіком роботи продавців": {"taken": ["Notes/Кошик — графік роботи продавця.md#Кошик — графік роботи продавця › Рішення"],
                                      "variants": [], "nothing": False},
        "години відкриття магазину": {"taken": ["Notes/Checkout flow (old).md"], "variants": [MOBILE], "nothing": False},
        "seller hours in the cart": {"taken": [], "variants": [], "nothing": True},
        "програма лояльності для покупців": {"taken": [], "variants": [], "nothing": True}}, ensure_ascii=False))
    open(os.path.join(answers, "b.json"), "w", encoding="utf-8").write(json.dumps({
        "інтеграція з бухгалтерією 1С": {"taken": ["Notes/Inbox.md"], "variants": [], "nothing": False},
        "Q4": {"taken": ["Notes/Roadmap Q4 — draft v3.md", "Notes/Roadmap Q4 — draft v2.md"], "variants": [], "nothing": False}},
        ensure_ascii=False))
    p = subprocess.run([sys.executable, AGENT_EVAL, "score", "--golden", GOLDEN_ZORG, "--answers", answers],
                       capture_output=True, text=True, env=penv, timeout=120)
    last = (p.stdout.strip().splitlines() or [""])[-1]
    score = json.loads(last[len("SCORE "):]) if last.startswith("SCORE ") else {}
    check("score: precision_taken 2/5, empty_clean 1/2, hit 3/4 on the synthetic answers",
          p.returncode == 0 and (score.get("precision_taken"), score.get("empty_clean"), score.get("hit")) == (0.4, 0.5, 0.75),
          (p.returncode, p.stdout[-600:], p.stderr[-300:]))
    check("…the rows with no answer are counted apart, and a `bad` one taken is named", score.get("missing") == 9
          and score.get("bad_taken") == 1 and "precision_taken" in p.stdout and "без відповіді: 9" in p.stdout, score)

# --- v3.16.0 final review: an own index not built yet, or being built by another process, has not answered (exit 5)
import ctx_index as ci_mod  # noqa: E402

BUILDING = "індекс пошуку ще будується (інший процес) — цього разу без нього"
with tempfile.TemporaryDirectory() as d:
    env = SearchEnv(d, brain=False)
    os.makedirs(env.index)
    lock, db = os.path.join(env.index, "index.lock"), os.path.join(env.index, "sections.sqlite")
    open(lock, "w", encoding="utf-8").write(json.dumps({"pid": os.getpid(), "at": time.time()}))   # a live process: this one
    OWN_ONLY = ("search", "--q", "графік роботи продавця", "--sources", "own", "--json")

    def own_unread(rc, res):
        return (rc == 5 and res and res["sources"] == [{"id": "own", "kind": "own", "answered": False}]
                and res["candidates"] == [] and BUILDING in res["notes"] and res["index"]["locked"] is True)

    rc, out, res = run_ok(env, *OWN_ONLY)
    check("C1 A: the index's lock held by a live process and no database: exit 5, own not answered, the building line",
          own_unread(rc, res), (rc, res and res.get("notes"), res and res.get("index")))
    con = sqlite3.connect(db)
    con.executescript(ci_mod.DDL)
    con.commit()
    con.close()
    rc, out, res = run_ok(env, *OWN_ONLY)
    check("C1 B: …a database with the schema's tables only (no meta row) and no index.json: the same", own_unread(rc, res),
          (rc, res and res.get("notes"), res and res.get("index")))
    open(os.path.join(env.index, "index.json"), "w", encoding="utf-8").write(json.dumps(
        {"schema": "search-index/1", "updated": "2026-01-02T09:00:00+02:00", "files": 19, "sections": 60, "pending": 0}))
    rc, out, res = run_ok(env, *OWN_ONLY)
    check("C1 D: …and an old index.json beside it: the same, and index.updated is the database's (none), not the old day",
          own_unread(rc, res) and res["index"]["updated"] is None, (rc, res and res.get("notes"), res and res.get("index")))
    rc, out, _ = run_ok(env, *OWN_ONLY[:-1])
    check("…the human output says the building line", rc == 5 and BUILDING in out, (rc, out[-400:]))
    os.remove(lock)
    rc, out, res = run_ok(env, *OWN_ONLY)
    check("C1 control: no lock — the search builds the index and finds the note", rc == 0 and res
          and res["sources"] == [{"id": "own", "kind": "own", "answered": True}] and by_path(res, KOSHYK)
          and BUILDING not in res["notes"], (rc, res and res.get("notes")))

    # 154: eval refreshes the index once, not twice a row
    calls, real_refresh = [], ci_mod.Index.refresh
    ci_mod.Index.refresh = lambda self, *a, **kw: calls.append(1) or real_refresh(self, *a, **kw)
    try:
        rc, out, res = in_process(env, "search", "eval", "--golden", GOLDEN_ZORG, "--no-hints", "--json")
    finally:
        ci_mod.Index.refresh = real_refresh
    check("154: eval refreshes the index once per eval, and its numbers stay the pinned ones", rc == 0 and len(calls) == 1
          and res and (res["n"], round(res["recall50"], 3), round(res["recall50_q_only"], 3)) == PINNED,
          (rc, len(calls), res and (res.get("n"), res.get("recall50"), res.get("recall50_q_only"))))

    # 152: forget says forget
    rc, out, res = run_ok(env, "search", "forget", "--q", "що і як")
    check("152: forget of a request of stop words only: exit 3, a message about forgetting, not remembering",
          rc == 3 and "forget" in out and "remember" not in out, (rc, out[-300:]))

# --- v3.16.0 acceptance fix wave B2: `ctx search` lists 30 candidates unless --limit says otherwise; eval reads 50
with tempfile.TemporaryDirectory() as d:
    env = SearchEnv(d, brain=False)
    for i in range(40):
        env.add("Notes/Zebra/Zebra note %02d.md" % i, "# Zebra note %02d\n\nThe zebrafish of the cart. %s\n" % (i, "filler " * i))
    rc, out, res = run_ok(env, "search", "--q", "zebrafish", "--no-hints", "--json")
    check("B2: ctx search lists 30 candidates by default (40 notes match)", rc == 0 and res and len(res["candidates"]) == 30
          and res["counts"]["candidates"] == 30, (rc, res and len(res.get("candidates") or [])))
    rc, out, res = run_ok(env, "search", "--q", "zebrafish", "--no-hints", "--limit", "50", "--json")
    check("…--limit 50 lists them all", rc == 0 and res and len(res["candidates"]) == 40, (rc, res and len(res.get("candidates") or [])))
    far = res["candidates"][34]["path"] if res and len(res["candidates"]) == 40 else ""
    golden = os.path.join(d, "golden.yaml")
    open(golden, "w", encoding="utf-8").write(
        "schema: search-golden/1\nqueries:\n  - q: \"zebrafish\"\n    variants: []\n    class: форма\n"
        "    good: [\"%s\"]\n    source: reviewed\n    added: 2026-10-21\n" % far)
    rc, out, res = run_ok(env, "search", "eval", "--golden", golden, "--no-hints", "--json")
    check("B2: eval still reads the first 50 — an answer at place 35 is found", rc == 0 and res and res["n"] == 1
          and res["recall50"] == 1.0 and res["rows"][0].get("rank") == 35, (rc, res and res.get("rows"), out[-300:]))
    last_before = os.path.exists(os.path.join(env.index, "last.json")) and read(env.index, "last.json")
    rc, out, res = run_ok(env, "search", "--get", "Notes/Zebra/Zebra note 07.md", "--json")
    check("T1: --get takes a note's path: exit 0, the whole note under `> [own · <path> · <day>]`, last.json as it was",
          rc == 0 and res and res["header"].startswith("> [own · Notes/Zebra/Zebra note 07.md · ")
          and res["text"].startswith("# Zebra note 07\n\nThe zebrafish of the cart.")
          and (os.path.exists(os.path.join(env.index, "last.json")) and read(env.index, "last.json")) == last_before,
          (rc, res, out[-300:]))
    rc, out, res = run_ok(env, "search", "--get", "Notes/Zebra/No such note.md")
    check("…an unknown path: exit 3, one line", rc == 3 and "search: no candidate Notes/Zebra/No such note.md" in out,
          (rc, out[-300:]))
    # fix round 5: --get by a note's name, a section after `#`, an excluded path
    TEAM5 = "ZorgCore/Teams/team-alpha.md"
    rc, out, res = run_ok(env, "search", "--get", "[[team-alpha|the team]]", "--json")
    check("U1: --get takes a note's name, as a hub links it: exit 0, the whole note under the repository's line",
          rc == 0 and res and res["header"] == "> [zorg-core · %s · 2026-01-01 · team]" % TEAM5
          and res["text"].startswith("# Team Alpha\n\n"), (rc, res, out[-300:]))
    rc, out, res = run_ok(env, "search", "--get", TEAM5 + "#Members")
    check("U6: …`<шлях>#<заголовок>` prints that section under its heading path", rc == 0
          and out.startswith("> [zorg-core · %s › Team Alpha › Members · 2026-01-01 · team]\n- Alex One" % TEAM5), (rc, out[:300]))
    rc, out, res = run_ok(env, "search", "--get", "Delivery slots (900100200)")
    check("U1: a name two notes carry: exit 3, the line naming them", rc == 3 and out.startswith(
        "search: кілька нотаток із назвою «Delivery slots (900100200)»: Notes/Knowledge/Delivery slots (900100200).md · "
        "ZorgCore/Pages/Delivery slots (900100200).md — --get один зі шляхів") and res and res["error"].startswith("кілька нотаток"),
        (rc, out[-300:]))
    rc, out, res = run_ok(env, "search", "--get", "Notes/_System/context/records/x.md")
    check("U5: a path under the store: exit 3 `шлях виключено з пошуку`", rc == 3
          and out.startswith("search: шлях виключено з пошуку: Notes/_System/context/records/x.md"), (rc, out[-300:]))
    # round 5b: a vault-root path with no `/` is a path first, never a name's lookup
    env.add("Root memo.md", "# Root memo\n\nroot one\n")
    env.add("Growth/Root memo.md", "# Root memo\n\ngrowth one\n")
    rc, out, res = run_ok(env, "search", "--get", "Root memo.md", "--json")
    check("V1: --get of a vault-root path with no `/`: exit 0, that note under `> [vault · Root memo.md · …]`",
          rc == 0 and res and res["header"].startswith("> [vault · Root memo.md · ") and "root one" in res["text"], (rc, res, out[-300:]))
    rc, out, res = run_ok(env, "search", "--get", "Root memo", "--json")
    check("…and its bare name is that path first", rc == 0 and res and res["header"].startswith("> [vault · Root memo.md · "),
          (rc, res, out[-300:]))

# --- v3.16.1 Task 2: --get is cut at 20 000 characters, --full at 60 000; --full goes with --get alone
with tempfile.TemporaryDirectory() as d:
    env = SearchEnv(d, brain=False)
    env.add("Notes/Long/Long parts.md", "# Long parts\n\n" + "".join("## Part %d\n\n%s\n\n" % (i, "p" * 2200) for i in range(1, 21)))
    rc, out, res = run_ok(env, "search", "--get", "Notes/Long/Long parts.md", "--json")
    check("C6: ctx search --get of a 45 000-character note — the first 20 000 and the line with --full",
          rc == 0 and res and "\n\nнотатка довга — показано 20 000 знаків із " in res["text"] and "## Part 20" not in res["text"]
          and res["text"].endswith(" або --full (до 60 000)"), (rc, res and res["text"][-300:]))
    rc, out, res = run_ok(env, "search", "--get", "Notes/Long/Long parts.md", "--full", "--json")
    check("…--full: the whole note, no line", rc == 0 and res and "## Part 20" in (res.get("text") or "")
          and "нотатка довга" not in res["text"], (rc, res and (res.get("text") or out)[-200:]))
    rc, out, res = run_ok(env, "search", "--q", "parts", "--full")
    check("…--full without --get is bad usage (exit 3)", rc == 3 and "--full" in out, (rc, out[-300:]))
    rc, out, res = run_ok(env, "search", "eval", "--full")
    rc2, out2, res2 = run_ok(env, "search", "forget", "--q", "parts", "--full")
    check("Task 2 fix M2: eval and forget take no --full either (exit 3, the flag named)", rc == 3 and rc2 == 3
          and "--full" in out and "--full" in out2, (rc, out[-200:], rc2, out2[-200:]))

check("every command ends with a CTX_RESULT line", contract_ok)
print("RESULT:", "GREEN ✅" if not fails else "RED ❌", "(%d failed)" % fails)
sys.exit(1 if fails else 0)
