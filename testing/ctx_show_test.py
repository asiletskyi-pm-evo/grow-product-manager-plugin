#!/usr/bin/env python3
"""TC-ctx-3210-show — `ctx show` and `ctx health` (v3.21.0, plan C8–C9).

The fictional typical context in a temp HOME + vault: show lists every record with who wrote it last and when it
was verified, your answers and the inbox, and a record's text on request; health says, a line each with the command
that fixes it, a stale record, an urgent inbox, the copies outside the snapshots (with their sizes, from stat alone —
an unreadable file is still measured), a vault's `_backup_*` folder and a missing index. Both read only: not one
byte of the store, the copies or the home changes.
Stdlib only; run from the repo root:

  env -u GROW_PM_CONTEXT_PATH -u GROW_PM_PROVIDER_PATHS python3 testing/ctx_show_test.py
"""
import hashlib, json, os, re, shutil, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "testing"))
from ctx_testenv import Env, read  # noqa: E402

fails = 0


def check(name, cond, detail=""):
    global fails
    fails += not cond
    print(("✅" if cond else "❌"), name, ("" if cond else "-> " + str(detail)[:900]))


def fingerprint(*roots):
    out = {}
    for root in roots:
        for r, _, files in os.walk(root):
            for f in files:
                p = os.path.join(r, f)
                try:
                    out[p] = hashlib.sha1(open(p, "rb").read()).hexdigest()
                except OSError:
                    out[p] = "unreadable:%d" % os.lstat(p).st_size
    return out


SRC = {"kind": "derived:jira", "ref": "PROJ-1234", "at": "2026-10-27"}
d = tempfile.mkdtemp(prefix="ctx-show-")
locked = None
try:
    env = Env(d)
    rc, out, _ = env.run("show")
    check("1.0 no store → exit 3", rc == 3, (rc, out[-200:]))
    env.run("migrate", "--apply")
    env.run("compile")
    env.run("set", "product.zorg-app", "Confluence Space", "ZAPP2")
    env.run("propose", "--skill", "task-creator", "--delta", json.dumps(
        {"op": "UPDATE", "record": "product.zorg-app", "field": "Jira Project Key", "value": "ZORG",
         "reason": "the board moved", "source": SRC}))
    # a stale record: its verified day far back
    p = os.path.join(env.store, "records", "team.alpha-a.md")
    t = read(p)
    t = re.sub(r'verified: "[^"]*"', 'verified: "2025-01-01"', t) if "verified:" in t else \
        t.replace("\nsha:", '\nverified: "2025-01-01"\nsha:', 1)
    open(p, "w", encoding="utf-8").write(t)
    gp = os.path.join(env.home, ".grow-pm")
    os.makedirs(os.path.join(gp, "backups", "pre-zorg"))
    open(os.path.join(gp, "backups", "pre-zorg", "local-context.md"), "w").write("# Local Context\n" * 200)
    locked = os.path.join(gp, "local-context.md.bak.20260101")
    open(locked, "w").write("x" * 3000)
    os.chmod(locked, 0)
    os.makedirs(os.path.join(env.vault, "_backup_before_zorg", "Notes"))
    open(os.path.join(env.vault, "_backup_before_zorg", "Notes", "n.md"), "w").write("y" * 9000)
    before = fingerprint(env.home, env.vault)
    # ----------------------------------------------------------------------- show
    rc, out, res = env.run("show")
    lines = [l for l in out.splitlines() if " — " in l and not l.startswith("CTX_")]
    check("1.1 one line a record, each with who wrote it last and when it was verified",
          rc == 0 and len(res["records"]) == 14 and all("писав" in l and "перевірено" in l for l in lines[:14]),
          (rc, out[-600:]))
    zl = [l for l in lines if l.startswith("product.zorg-app ")]
    check("1.2 the record you set says ctx-set", zl and "писав ctx-set" in zl[0], zl)
    al = [l for l in lines if l.startswith("team.alpha-a ")]
    check("1.3 a stale record says so", al and "застаріле" in al[0], al)
    check("1.4 your answers and the inbox, one line", "скринька 1 (термінових 1)" in out, out[-300:])
    rc, out, res = env.run("show", "product.zorg-app")
    check("1.5 show <id> → that record's text", rc == 0 and "**Confluence Space:** ZAPP2" in out
          and len(res["records"]) == 1, out[-400:])
    rc, out, _ = env.run("show", "product.nope")
    check("1.6 an unknown id → exit 3", rc == 3, (rc, out[-200:]))
    # ----------------------------------------------------------------------- health
    rc, out, res = env.run("health")
    text = "\n".join(l for l in out.splitlines() if not l.startswith("CTX_"))
    check("2.1 exit 0, ✅ ⚠ ✋ counted in the result", rc == 0 and res["act"] >= 1 and res["warn"] >= 1, (rc, text))
    check("2.2 a stale record → ⚠ with ctx verify --stale",
          re.search(r"^⚠ застарілі записи: 1 \(team\.alpha-a\) — ctx verify --stale$", text, re.M), text)
    check("2.3 an urgent entry in the inbox → ✋ /context inbox",
          re.search(r"^✋ у скриньці 1, термінових 1 — /context inbox$", text, re.M), text)
    bk = [l for l in text.splitlines() if "копій поза знімками" in l]
    check("2.4 the copies outside the snapshots: the backups folder, the .bak (unreadable — measured by stat) and "
          "the vault's _backup_ folder, each with a size",
          bk and "pre-zorg (3.1 КБ)" in bk[0] and "local-context.md.bak.20260101 (2.9 КБ)" in bk[0]
          and "_backup_before_zorg (8.8 КБ)" in bk[0] and "ctx snapshot import" in bk[0], bk)
    check("2.5 no search index → ⚠ ctx index rebuild", "⚠ індексу пошуку немає — ctx index rebuild" in text, text)
    check("2.6 snapshots counted", re.search(r"^✅ знімків: \d+, найновіший ", text, re.M), text)
    after = fingerprint(env.home, env.vault)
    check("3.1 show and health change nothing — not one byte in the home, the store or the vault",
          before == after, sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))[:5])
    open(os.path.join(env.store, "records", "setting.templates.md"), "w").write("")
    rc, out, res = env.run("health")
    check("3.2 a record that does not parse → health still answers (exit 0), the error a ✋ line",
          rc == 0 and re.search(r"^✋ помилки сховища: .*setting\.templates", out, re.M), (rc, out[-500:]))
finally:
    if locked and os.path.exists(locked):
        os.chmod(locked, 0o600)
    shutil.rmtree(d, ignore_errors=True)

print("\n%s — %d failure(s)" % ("GREEN" if not fails else "RED", fails))
sys.exit(1 if fails else 0)
