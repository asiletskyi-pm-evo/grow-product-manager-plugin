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
    bk = [l for l in text.splitlines() if "копій у ~/.grow-pm/backups" in l or "local-context.md.bak*" in l
          or "тек _backup_*" in l]
    check("2.4 the copies outside the snapshots, a line per kind with its total: the backups folder, the .bak "
          "(unreadable — measured by stat), the vault's _backup_ folder (named only)",
          len(bk) == 3 and "pre-zorg (3.1 КБ)" in bk[0] and "ctx snapshot import" in bk[0]
          and "local-context.md.bak.20260101 (2.9 КБ)" in bk[1] and "_backup_before_zorg (8.8 КБ)" in bk[2]
          and "лише названо" in bk[2], bk)
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

# ----------------------------------------------------------------------- every line of health(), one at a time
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import datetime  # noqa: E402
import ctx_show as csh  # noqa: E402
rec = {"id": "product.zorg-app", "type": "product", "title": "Product: Zorg App", "source": "x", "modified": "2026-10-01",
       "verified": "2026-10-01", "ttl": 90, "stale": False, "invalid": False, "read_by": None}
mem = {"slots": 0, "entities": 0, "search": 0, "bridges": 0, "inbox": {"entries": 0, "urgent": 0, "old": 0}}
fresh = {"updated": datetime.datetime.now().astimezone().isoformat(timespec="seconds"), "skipped_dataless": 0}


def H(**kw):
    a = dict(recs=[rec], mem=mem, repo_rows=[], pending=0, conflicts=0, missing=0, stray=0, warnings=[], errors=[],
             idx=fresh, snaps=["20261027T100000-set"], baks=[], today="2026-10-27")
    a.update(kw)
    return [(l, t, f) for l, t, f in csh.health(**a)]


def has(lines, level, part):
    return any(l == level and part in t for l, t, f in lines)


row = {"id": "zorg-core", "kind": "folder", "sync": "daily", "paused": False, "blocks": 3, "version": "1",
       "checked": "2026-10-20", "outcome": None, "error": None}
check("5.1 a sync that did not end well → ⚠ with ctx provider plan",
      has(H(repo_rows=[dict(row, outcome="unreachable")]), "warn", "останній синк — unreachable"))
check("5.2 a repository's state that does not read → ✋", has(H(repo_rows=[dict(row, error="bad json")]), "act", "стан не читається"))
check("5.3 a secret in your record (validate's warning) → ✋",
      has(H(warnings=["profile: схоже на IBAN — таке не варто тримати в контексті, прибери це з запису"]), "act", "profile"))
old_idx = {"updated": (datetime.datetime.now().astimezone() - datetime.timedelta(days=3)).isoformat(timespec="seconds"),
           "skipped_dataless": 0}
check("5.4 an index older than 36 h → ⚠, a fresh one ✅",
      has(H(idx=old_idx), "warn", "індекс пошуку") and has(H(), "ok", "індекс пошуку"))
check("5.5 an invalidated record → ⚠ неактуальні", has(H(recs=[dict(rec, invalid=True)]), "warn", "неактуальні"))
check("5.6 a memory that does not read → ✋", has(H(mem=dict(mem, slots="slots memory not valid")), "act", "пам'ять slots"))
check("5.7 a conflict or a missing record file → ✋; edits waiting alone → ⚠",
      has(H(conflicts=1), "act", "конфліктів: 1") and has(H(missing=1), "act", "файлів записів немає")
      and has(H(pending=2), "warn", "правок чекає імпорту: 2"))
lines = H(pending=1, warnings=["1 change(s) waiting — `ctx sync`"])
check("5.8 an edit waiting is said once, not again as a validate warning",
      sum(1 for l, t, f in lines if "чекає" in t or "validate" in t) == 1, lines)
check("5.9 a registration that does not read → ✋", has(H(unread_regs=[("zorg.yaml", "not YAML")]), "act", "zorg.yaml"))
check("5.10 a store error and no records → no «усі свіжі» beside it",
      not has(H(recs=[], errors=["record not valid: x.md"]), "ok", "усі свіжі"))
big = os.path.join(tempfile.mkdtemp(prefix="ctx-walk-"), "_backup_x")
for i in range(30):
    os.makedirs(os.path.join(big, "d%02d" % i, "e"))
import time  # noqa: E402
size, complete = csh._size(big, time.monotonic() - 1)
check("5.11 the walk's budget holds (a tree of empty folders too): over it → not complete", not complete, (size, complete))
shutil.rmtree(os.path.dirname(big), ignore_errors=True)
idx_bad = os.path.join(tempfile.mkdtemp(prefix="ctx-idx-"), ".grow-pm", "index")
os.makedirs(idx_bad)
open(os.path.join(idx_bad, "index.json"), "w").write("[1, 2]")
check("5.12 an index.json that is not an object → no index, no crash",
      csh.index_state(os.path.dirname(os.path.dirname(idx_bad))) is None)

print("\n%s — %d failure(s)" % ("GREEN" if not fails else "RED", fails))
sys.exit(1 if fails else 0)
