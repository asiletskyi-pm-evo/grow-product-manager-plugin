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
CTX = os.path.join(ROOT, "scripts", "ctx.py")
FIX = os.path.join(ROOT, "testing", "fixtures", "ctx")
fails = 0


def check(name, cond, detail=""):
    global fails
    fails += not cond
    print(("✅" if cond else "❌"), name, ("" if cond else "-> " + str(detail)[:700]))


def read(*parts):
    return open(os.path.join(*parts), encoding="utf-8", newline="").read()


class Env:
    def __init__(self, d, fixture="typical"):
        self.home = os.path.join(d, "home")
        self.vault = os.path.join(d, "vault")
        os.makedirs(os.path.join(self.home, ".grow-pm"))
        os.makedirs(os.path.join(self.vault, "Notes", "_System"))
        self.text = read(FIX, fixture + ".md").replace("{{VAULT}}", self.vault)
        self.ctx = os.path.join(self.home, ".grow-pm", "local-context.md")
        self.mirror = os.path.join(self.vault, "Notes", "_System", "local-context.md")
        self.store = os.path.join(self.vault, "Notes", "_System", "context")
        open(self.ctx, "w", encoding="utf-8", newline="").write(self.text)
        if "{{VAULT}}" in read(FIX, fixture + ".md"):
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

check("every command ends with a CTX_RESULT line", contract_ok)
print("RESULT:", "GREEN ✅" if not fails else "RED ❌", "(%d failed)" % fails)
sys.exit(1 if fails else 0)
