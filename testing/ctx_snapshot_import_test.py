#!/usr/bin/env python3
"""TC-ctx-3210-snapshot-import — `ctx snapshot import` (v3.21.0, plan C14 / R6, review of Tasks 5–6).

A temp HOME with old backups of the fictional typical context: a dry run lists what it would import (local-context.md's
form only, under ~/.grow-pm only), what an imported snapshot already holds, and what it leaves (a zip, a section, a
yaml, a note with only a profile heading, a link, a file too big, one holding a card number) — and writes nothing;
--apply with the report's code writes `<time>-imported` snapshots that the rotation keeps, moves the originals to the
trash (two of one name in one second do not clash), refuses another code; `ctx undo` puts the originals back and
removes their snapshots — but never a snapshot whose original did not come back (its place taken, the trash
purged), and an apply cut short is still taken back.
Stdlib only; run from the repo root:

  env -u GROW_PM_CONTEXT_PATH -u GROW_PM_PROVIDER_PATHS python3 testing/ctx_snapshot_import_test.py
"""
import json, os, shutil, stat, sys, tempfile, time

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


def journal(env):
    return [json.loads(l) for l in read(env.store, ".state", "journal.jsonl").splitlines() if l.strip()]


def printed(out):
    return "\n".join(l for l in out.splitlines() if not l.startswith("CTX_RESULT"))


def luhn_card():
    for d in "0123456789":
        s = "411111111111111" + d
        tot = 0
        for i, c in enumerate(reversed(s)):
            v = int(c) * (2 if i % 2 else 1)
            tot += v - 9 if v > 9 else v
        if tot % 10 == 0:
            return s


def setup(d):
    env = Env(d)
    gp = os.path.join(env.home, ".grow-pm")
    t0 = time.mktime((2026, 5, 5, 13, 52, 21, 0, 0, -1))
    env.texts = {
        "a": env.text.replace("Updated: 2026-09-29", "Updated: 2026-05-05"),
        "b": env.text.replace("Updated: 2026-09-29", "Updated: 2026-06-30"),
        "c": env.text.replace("Updated: 2026-09-29", "Updated: 2026-07-07"),
    }
    put(os.path.join(gp, "backups", "pre-reconfigure", "local-context.md"), env.texts["a"], t0)
    put(os.path.join(gp, "backups", "pre-other", "local-context.md"), "﻿" + env.texts["c"], t0)   # a BOM: still one
    put(os.path.join(gp, "backups", "local-context-history", "2026-06-30.md"), env.texts["b"], t0 + 86400 * 56)
    put(os.path.join(gp, "backups", "local-context-history", "2026-06-30-again.md"), env.texts["b"], t0 + 86400 * 57)
    put(os.path.join(gp, "backups", "cjm_config_section_20260929.md"), "## CJM Configuration\n\n- **Template:** x\n")
    put(os.path.join(gp, "backups", "zorg.yaml"), "id: zorg\n")
    put(os.path.join(gp, "backups", "note.md"), "# Zorg notes\n\n## User Profile\n\nnot a context file\n")
    put(os.path.join(gp, "backups", "with-card.md"), env.texts["a"].replace("Alex One", "Alex One, card " + luhn_card()))
    open(os.path.join(gp, "backups", "vault.zip"), "wb").write(b"PK\x03\x04" + b"\0" * 100)
    with open(os.path.join(gp, "backups", "huge.md"), "w", encoding="utf-8") as f:
        f.write(env.texts["a"] + ("x" * 1024 + "\n") * 4200)
    os.symlink(os.path.join(gp, "backups", "pre-reconfigure", "local-context.md"), os.path.join(gp, "backups", "link.md"))
    put(os.path.join(gp, "local-context.md.bak.20260825"), env.texts["b"], t0 + 86400 * 112)
    put(os.path.join(env.vault, "Notes", "_System", "local-context.md.bak.20260101"), env.texts["a"])   # not ~/.grow-pm
    env.gp = gp
    return env


d = tempfile.mkdtemp(prefix="ctx-snapimp-")
try:
    env = setup(os.path.join(d, "one"))
    gp = env.gp
    rc, out, _ = env.run("snapshot", "import")
    check("0.1 no store → exit 3", rc == 3, (rc, out[-200:]))
    env.run("migrate", "--apply")
    env.run("compile")
    # a regular snapshot holding text «b» is no «already in a snapshot» (it rotates away)
    reg = os.path.join(gp, "snapshots", "20260101T000000-op", "copies")
    os.makedirs(reg)
    open(os.path.join(reg, "0.md"), "w", encoding="utf-8").write(env.texts["b"])
    before = tree(env.home)
    vault_before = tree(env.vault)
    rc, out, res = env.run("snapshot", "import")
    out = printed(out)
    check("1.1 the dry run: 3 to import (one per text — a BOM is no other text), 2 held by one of them, a code",
          rc == 0 and len(res["import"]) == 3 and len(res["known"]) == 2 and ("код звіту: %s" % res["code"]) in out,
          (rc, out[-900:]))
    why = {os.path.basename(r["path"]): r["why"] for r in res["left"]}
    check("1.2 left, each with why: the section, the yaml, the zip, the note with only a profile heading, the file "
          "too big, the one holding a card number",
          why.get("note.md") == "не схоже на local-context" and "завеликий" in why.get("huge.md", "")
          and "банківської картки" in why.get("with-card.md", "") and "zorg.yaml" in why and "vault.zip" in why
          and "cjm_config_section_20260929.md" in why, why)
    paths = [r["path"] for r in res["import"] + res["known"] + res["left"]]
    check("1.3 a link and anything outside ~/.grow-pm are not looked at",
          not any(p.endswith("link.md") for p in paths) and not any(env.vault in p for p in paths), paths)
    check("1.4 a dry run writes nothing", tree(env.home) == before, sorted(tree(env.home) ^ before))
    code = res["code"]
    rc, out, _ = env.run("snapshot", "import", "--apply")
    check("2.1 --apply without --code → exit 3", rc == 3, (rc, out[-200:]))
    rc, out, _ = env.run("snapshot", "import", "--apply", "--code", "deadbeef")
    check("2.2 another code → exit 4 «звіт змінився», nothing moved", rc == 4 and "звіт змінився" in out
          and tree(env.home) == before, (rc, out[-200:]))
    rc, out, res = env.run("snapshot", "import", "--apply", "--code", code)
    root = os.path.join(gp, "snapshots")
    imported = sorted(n for n in os.listdir(root) if co.IMPORTED_RE.match(n))
    check("2.3 three snapshots <time>-imported; one named for 2026-06-30 by its file name",
          rc == 0 and len(imported) == 3 and any(n.startswith("20260630T000000") for n in imported), (out[-500:], imported))
    first = [n for n in imported if n.startswith("20260505T135221")]
    check("2.4 two backups of one second (pre-reconfigure, pre-other): two snapshots, their texts byte for byte, 0600",
          len(first) == 2 and {read(root, n, "copies", "0.md") for n in first} == {env.texts["a"], "﻿" + env.texts["c"]}
          and all(oct(os.stat(os.path.join(root, n, "copies", "0.md")).st_mode & 0o777) == "0o600" for n in first), first)
    trash = sorted(os.listdir(os.path.join(gp, "trash")))
    left = tree(os.path.join(gp, "backups"))
    check("2.5 five originals in the trash, under five names (two local-context.md of one second do not clash)",
          len(trash) == 5 and len(set(trash)) == 5 and "pre-reconfigure/local-context.md" not in left
          and "zorg.yaml" in left and "with-card.md" in left and "link.md" in left, (trash, sorted(left)))
    j = journal(env)[-1]
    check("2.6 one journal line op snapshot-import with every planned move and a snapshot", j["op"] == "snapshot-import"
          and len(j["moves"]) == 5 and all({"path", "sha", "trash", "snapshot", "made"} <= set(m) for m in j["moves"])
          and j.get("snapshot"), j)
    check("2.7 the vault was neither read for backups nor written: its .bak is where it was",
          os.path.exists(os.path.join(env.vault, "Notes", "_System", "local-context.md.bak.20260101")))
    for i in range(25):
        os.makedirs(os.path.join(root, "20261027T%06d-op" % (100000 + i)))
    co.rotate(root)
    check("2.8 the rotation keeps the imported snapshots", all(os.path.isdir(os.path.join(root, n)) for n in imported))
    rc, out, _ = env.run("status")
    check("2.9 status's last snapshot is never an imported one", "imported" not in
          [l for l in out.splitlines() if l.startswith("last snapshot")][0], out[-300:])
    rc, out, _ = env.run("snapshot", "--label", "imported")
    check("2.10 a manual snapshot may not take the label «imported»", rc == 3, (rc, out[-200:]))
    rc, out, res = env.run("snapshot", "import")
    check("2.11 a second dry run: nothing to import", rc == 0 and not res["import"] and not res["known"], out[-300:])
    # undo: the place of one original taken, another's trash copy purged
    taken = os.path.join(gp, "backups", "pre-reconfigure", "local-context.md")
    put(taken, "a newer file of yours\n")
    gone = [m for m in j["moves"] if m["path"].endswith("2026-06-30.md")][0]
    os.remove(gone["trash"])
    rc, out, _ = env.run("undo")
    snaps_now = set(os.listdir(root))
    mine = [m for m in j["moves"] if m["path"] == taken][0]
    check("3.1 undo: an original whose place is taken stays in the trash, its snapshot stays, your newer file stays",
          rc == 0 and read(taken) == "a newer file of yours\n" and os.path.isfile(mine["trash"])
          and mine["snapshot"] in snaps_now, out[-600:])
    check("3.2 undo: an original purged from the trash — its snapshot stays (the text lives there)",
          gone["snapshot"] in snaps_now and not os.path.exists(gone["path"]), sorted(snaps_now))
    other = [m for m in j["moves"] if m["path"].endswith(os.path.join("pre-other", "local-context.md"))][0]
    check("3.3 undo: an original back in its place → its snapshot removed",
          os.path.isfile(other["path"]) and other["snapshot"] not in snaps_now, (out[-400:], sorted(snaps_now)))
    check("3.4 undo says what it kept and why", "лишився" in out, out[-600:])

    # an apply cut short: a read-only backup folder
    env2 = setup(os.path.join(d, "two"))
    env2.run("migrate", "--apply")
    env2.run("compile")
    ro = os.path.join(env2.gp, "backups", "local-context-history")
    rc, out, res = env2.run("snapshot", "import")
    os.chmod(ro, stat.S_IRUSR | stat.S_IXUSR)
    try:
        rc, out, res = env2.run("snapshot", "import", "--apply", "--code", res["code"])
        j2 = journal(env2)[-1]
        check("4.1 a row that cannot move is said, the rest goes on, the journal line lists every planned move",
              rc == 0 and res.get("failed") and j2["op"] == "snapshot-import" and len(j2["moves"]) == 5
              and os.path.isfile(os.path.join(ro, "2026-06-30.md")), (out[-500:], res.get("failed")))
        check("4.2 no file in two places: what could not move has no copy in the trash",
              not any("2026-06-30" in n for n in os.listdir(os.path.join(env2.gp, "trash"))),
              os.listdir(os.path.join(env2.gp, "trash")))
        rc, out, _ = env2.run("undo")
        check("4.3 undo of the cut-short apply puts back what moved; what never moved is where it was",
              rc == 0 and os.path.isfile(os.path.join(env2.gp, "backups", "pre-reconfigure", "local-context.md"))
              and os.path.isfile(os.path.join(ro, "2026-06-30.md")), out[-400:])
    finally:
        os.chmod(ro, 0o755)
finally:
    shutil.rmtree(d, ignore_errors=True)

print("\n%s — %d failure(s)" % ("GREEN" if not fails else "RED", fails))
sys.exit(1 if fails else 0)
