#!/usr/bin/env python3
"""TC-ctx-3210-snapshot-import — `ctx snapshot import` (v3.21.0, plan C14 / R6).

A temp HOME with old backups of the fictional typical context: a dry run lists what it would import (local-context.md's
form only), what a snapshot already holds, and what it leaves (a zip, a section, a yaml) — and writes nothing; --apply
with the report's code writes `<time>-imported` snapshots that the rotation keeps, moves the originals to the trash,
and refuses another code; `ctx undo` puts the originals back and removes the imported snapshots.
Stdlib only; run from the repo root:

  env -u GROW_PM_CONTEXT_PATH -u GROW_PM_PROVIDER_PATHS python3 testing/ctx_snapshot_import_test.py
"""
import json, os, shutil, sys, tempfile, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "testing"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from ctx_testenv import Env, read  # noqa: E402
import ctx_ops as co  # noqa: E402

fails = 0


def check(name, cond, detail=""):
    global fails
    fails += not cond
    print(("✅" if cond else "❌"), name, ("" if cond else "-> " + str(detail)[:900]))


def tree(root):
    out = set()
    for r, _, files in os.walk(root):
        for f in files:
            out.add(os.path.relpath(os.path.join(r, f), root))
    return out


def put(path, text, mtime=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8").write(text)
    if mtime:
        os.utime(path, (mtime, mtime))


d = tempfile.mkdtemp(prefix="ctx-snapimp-")
try:
    env = Env(d)
    gp = os.path.join(env.home, ".grow-pm")
    old_a = env.text.replace("Updated: 2026-09-29", "Updated: 2026-05-05")
    old_b = env.text.replace("Updated: 2026-09-29", "Updated: 2026-06-30")
    t0 = time.mktime((2026, 5, 5, 13, 52, 21, 0, 0, -1))
    put(os.path.join(gp, "backups", "pre-reconfigure", "local-context.md"), old_a, t0)
    put(os.path.join(gp, "backups", "local-context-history", "2026-06-30.md"), old_b, t0 + 86400 * 56)
    put(os.path.join(gp, "backups", "local-context-history", "2026-06-30-again.md"), old_b, t0 + 86400 * 57)
    put(os.path.join(gp, "backups", "cjm_config_section_20260929.md"), "## CJM Configuration\n\n- **Template:** x\n")
    put(os.path.join(gp, "backups", "zorg.yaml"), "id: zorg\n")
    open(os.path.join(gp, "backups", "vault.zip"), "wb").write(b"PK\x03\x04" + b"\0" * 100)
    put(os.path.join(gp, "local-context.md.bak.20260825"), old_b, t0 + 86400 * 112)
    rc, out, _ = env.run("snapshot", "import")
    check("0.1 no store → exit 3", rc == 3, (rc, out[-200:]))
    env.run("migrate", "--apply")
    env.run("compile")
    before = tree(env.home)
    rc, out, res = env.run("snapshot", "import")
    out = "\n".join(l for l in out.splitlines() if not l.startswith("CTX_RESULT"))
    check("1.1 the dry run: 2 to import (one copy of each text), 2 already held, 3 left, a code",
          rc == 0 and len(res["import"]) == 2 and len(res["known"]) == 2 and len(res["left"]) == 3
          and ("код звіту: %s" % res["code"]) in out, (rc, out[-900:]))
    check("1.2 what is left says why", out.count("не схоже на local-context") == 3, out[-600:])
    check("1.3 a dry run writes nothing", tree(env.home) == before, sorted(tree(env.home) ^ before))
    code = res["code"]
    rc, out, _ = env.run("snapshot", "import", "--apply")
    check("2.1 --apply without --code → exit 3", rc == 3, (rc, out[-200:]))
    rc, out, _ = env.run("snapshot", "import", "--apply", "--code", "deadbeef")
    check("2.2 another code → exit 4 «звіт змінився», nothing moved", rc == 4 and "звіт змінився" in out
          and tree(env.home) == before, (rc, out[-200:]))
    rc, out, res = env.run("snapshot", "import", "--apply", "--code", code)
    snaps = sorted(os.listdir(os.path.join(gp, "snapshots")))
    imported = [n for n in snaps if n.endswith("-imported")]
    check("2.3 two snapshots <their time>-imported, the first named for 2026-05-05",
          rc == 0 and len(imported) == 2 and imported[0].startswith("20260505T135221"), (out[-500:], snaps))
    check("2.4 the snapshot holds the old text byte for byte, mode 0600",
          read(gp, "snapshots", imported[0], "copies", "0.md") == old_a
          and oct(os.stat(os.path.join(gp, "snapshots", imported[0], "copies", "0.md")).st_mode & 0o777) == "0o600")
    trash = sorted(os.listdir(os.path.join(gp, "trash")))
    left = tree(os.path.join(gp, "backups"))
    check("2.5 the four originals in the trash; the zip, the section, the yaml where they were",
          len(trash) == 4 and left == {"cjm_config_section_20260929.md", "zorg.yaml", "vault.zip"}
          and not os.path.exists(os.path.join(gp, "local-context.md.bak.20260825")), (trash, left))
    j = [json.loads(l) for l in read(env.store, ".state", "journal.jsonl").splitlines() if l.strip()][-1]
    check("2.6 one journal line op snapshot-import with the moves and the snapshots, and a snapshot",
          j["op"] == "snapshot-import" and len(j["moves"]) == 4 and len(j["snapshots"]) == 2 and j.get("snapshot"), j)
    root = os.path.join(gp, "snapshots")
    for i in range(25):
        os.makedirs(os.path.join(root, "20261027T%06d-op" % (100000 + i)))
    co.rotate(root)
    check("2.7 the rotation keeps the imported snapshots", all(os.path.isdir(os.path.join(root, n)) for n in imported))
    for i in range(25):
        p = os.path.join(root, "20261027T%06d-op" % (100000 + i))
        if os.path.isdir(p):
            shutil.rmtree(p)
    rc, out, res = env.run("snapshot", "import")
    check("2.8 a second dry run: nothing to import", rc == 0 and not res["import"] and not res["known"]
          and "нічого імпортувати" in out, out[-300:])
    rc, out, _ = env.run("undo")
    check("3.1 ctx undo → the four originals back, the imported snapshots gone, the trash empty of them",
          rc == 0 and "повернуто бекапів: 4" in out and tree(env.home) - before == {n for n in tree(env.home) - before
                                                                                    if n.startswith(".grow-pm/snapshots/")}
          and not [n for n in os.listdir(root) if n.endswith("-imported")]
          and read(gp, "backups", "pre-reconfigure", "local-context.md") == old_a, (out[-500:], sorted(tree(env.home) - before)))
finally:
    shutil.rmtree(d, ignore_errors=True)

print("\n%s — %d failure(s)" % ("GREEN" if not fails else "RED", fails))
sys.exit(1 if fails else 0)
