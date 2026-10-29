#!/usr/bin/env python3
"""TC-ctx-3240-copy-pass — `ctx repo copy <id>` (scripts/ctx.py over scripts/ctx_copy.py), the pass end to end (since v3.24.0).

A temp HOME and vault (testing/ctx_testenv.py, the typical fictional context) and an MCP-only registration of the
fictional "Zorg" (`~/.grow-pm/providers/zorg-growth.yaml`: an endpoint, no folder) against the fake server
(testing/mcp_fake.py, 127.0.0.1). Covers: the copy from nothing in one command; a rerun with no change writes no note
(mtime as it was) and nothing in the store; an incomplete index (under half of the last complete listing, or none) is
held — 0 notes written, 0 moved; more notes failed than a complete pass allows is partial — writes stand, 0 moved; a note
gone from two complete listings in a row, at least 20 h apart, moves into `.removed/<day>/` (never deleted) and
`--restore` brings it back for good; the lock (busy, a stale one taken over); exits 3 (no such repository, one with its own
folder, no endpoint), 5 (the server does not answer); progress on stderr; and no branch of the code deletes a note.
Semantics: references/context-provider-protocol.md §12.12. Stdlib only; run from the repo root.
"""
import datetime, json, os, re, shutil, sys, tempfile, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "testing"))
os.environ["NO_PROXY"] = "127.0.0.1,localhost"
os.environ["no_proxy"] = "127.0.0.1,localhost"
import ctx_copy as cp  # noqa: E402
import ctx_mcp as cm  # noqa: E402
from ctx_testenv import Env  # noqa: E402
from mcp_fake import FakeMcp  # noqa: E402

cm.McpClient.BACKOFF = 0.0
fails = 0


def check(name, cond, detail=""):
    global fails
    fails += not cond
    print(("✅" if cond else "❌"), name, ("" if cond else "-> " + str(detail)[:900]))


REG = """schema: provider-registration/2
id: zorg-growth
title: Zorg Growth
kind: mcp
contract: vault/v1
authority: team
mode: live
access: open
endpoint:
  url: {url}
  root: Growth/
blocks_file: _System/context-blocks.md
sync: daily
status: active
"""
CORE = """schema: provider-registration/1
id: zorg-core
title: Zorg core
kind: bundle
paths:
  - {core}
status: active
"""


def tree(n=12):
    t = {"Growth/_System/context-blocks.md": "# Zorg Growth blocks\n"}
    for i in range(n):
        t["Growth/Notes/note-%02d.md" % i] = {"frontmatter": {"type": "note", "n": i}, "content": "# Zorg note %d\n" % i}
    return t


def mtimes(folder):
    out = {}
    for dp, dn, fn in os.walk(folder):
        dn[:] = [d for d in dn if not d.startswith(".")]
        for f in fn:
            p = os.path.join(dp, f)
            out[os.path.relpath(p, folder)] = os.stat(p).st_mtime_ns
    return out


def journal(env):
    p = os.path.join(env.store, ".state", "journal.jsonl")
    return open(p, encoding="utf-8").read() if os.path.isfile(p) else ""


tmp = tempfile.mkdtemp(prefix="ctx-copy-pass-")
try:
    env = Env(tmp)
    prov = os.path.join(env.home, ".grow-pm", "providers")
    os.makedirs(prov)
    folder = cp.copy_dir(env.home, "zorg-growth")
    with FakeMcp(tree=tree()) as fake:
        open(os.path.join(prov, "zorg-growth.yaml"), "w", encoding="utf-8").write(REG.format(url=fake.url))

        print("— 1. a copy in one command")
        rc, out, res = env.run("repo", "copy", "zorg-growth", "--now", "2026-10-29T09:00:00+02:00")
        check("exit 0, outcome complete", rc == 0 and res and res.get("outcome") == "complete", out)
        check("13 new notes (the blocks file too)", res and res["counts"]["new"] == 13 and res["listed"] == 13, res)
        check("the summary line", re.search(r"копія zorg-growth: нових 13 · оновлено 0 · без змін 0 · лишено твоє 0 · "
                                            r"конфліктів 0 · не прийшло 0 · перенесено в \.removed 0 — .*cores/zorg-growth · ", out), out)
        check("the copy is at ~/.grow-pm/cores/zorg-growth/, mirroring the root",
              os.path.isfile(os.path.join(folder, "Notes", "note-03.md")) and os.path.isfile(os.path.join(folder, "_System", "context-blocks.md")))
        check("the result names the folder", res and res.get("folder") == folder, res)
        j0, m0 = journal(env), mtimes(folder)

        print("— 2. a rerun with no change writes nothing")
        rc, out, res = env.run("repo", "copy", "zorg-growth", "--now", "2026-10-29T10:00:00+02:00")
        check("exit 0, complete, 13 same", rc == 0 and res["outcome"] == "complete" and res["counts"]["same"] == 13
              and res["counts"]["new"] + res["counts"]["updated"] == 0, res)
        check("no note written (mtime as it was)", mtimes(folder) == m0)
        check("nothing in the store's journal", journal(env) == j0)
        check("no sync report", not os.path.exists(os.path.join(env.vault, "Notes", "_System", "context", "sync")))

        print("— 3. an incomplete index is held")
        fake.list_cap = 5                                       # 5 of 13: under half
        rc, out, res = env.run("repo", "copy", "zorg-growth", "--now", "2026-10-30T10:00:00+02:00")
        check("held, exit 0", rc == 0 and res["outcome"] == "held" and "under half of the last complete listing (13)" in res["reason"], res)
        check("0 notes written, 0 moved", mtimes(folder) == m0 and res["counts"]["removed"] == 0
              and not os.path.exists(os.path.join(folder, ".removed")), res)
        check("the summary says why", "не оновлено" in out and "incomplete index" in out, out)
        fake.list_cap = 0                                       # none at all
        rc, out, res = env.run("repo", "copy", "zorg-growth", "--now", "2026-10-30T11:00:00+02:00")
        check("an empty listing is held too", res["outcome"] == "held" and mtimes(folder) == m0, res)
        check("held twice in a row is counted", res.get("held_in_row") == 2, res)
        fake.list_cap = None

        print("— 4. a partial pass moves nothing")
        fake.hidden = {"Growth/Notes/note-00.md"}
        fake.broken = {"Growth/Notes/note-%02d.md" % i for i in range(1, 7)}   # 6 failed > max(5, 1 %)
        rc, out, res = env.run("repo", "copy", "zorg-growth", "--now", "2026-10-31T10:00:00+02:00")
        check("partial, exit 0", rc == 0 and res["outcome"] == "partial" and res["counts"]["failed"] == 6, res)
        st = cp.load_state(folder)
        check("the vanished note is not marked missing on a partial pass",
              "missing_since" not in st["notes"]["Notes/note-00.md"] and os.path.isfile(os.path.join(folder, "Notes", "note-00.md")))
        check("the last complete pass stays where it was", st["complete_at"].startswith("2026-10-29T10:00"), st["complete_at"])
        fake.broken = set()

        print("— 5. gone from two complete listings → .removed/")
        rc, out, res = env.run("repo", "copy", "zorg-growth", "--now", "2026-11-01T10:00:00+02:00")
        st = cp.load_state(folder)
        check("first complete listing without it: missing since, still in place", res["outcome"] == "complete"
              and st["notes"]["Notes/note-00.md"].get("missing_since", "").startswith("2026-11-01")
              and os.path.isfile(os.path.join(folder, "Notes", "note-00.md")), res)
        rc, out, res = env.run("repo", "copy", "zorg-growth", "--now", "2026-11-01T20:00:00+02:00")
        check("a second listing within 20 h moves nothing", res["counts"]["removed"] == 0
              and os.path.isfile(os.path.join(folder, "Notes", "note-00.md")), res)
        rc, out, res = env.run("repo", "copy", "zorg-growth", "--now", "2026-11-02T10:00:00+02:00")
        moved = os.path.join(folder, ".removed", "2026-11-02", "Notes", "note-00.md")
        check("the next complete listing ≥ 20 h later moves it into .removed/<day>/", res["counts"]["removed"] == 1
              and res["removed"] == ["Notes/note-00.md"] and os.path.isfile(moved)
              and not os.path.exists(os.path.join(folder, "Notes", "note-00.md")), res)
        check("the summary names the move", "перенесено в .removed 1" in out, out)
        check("the state forgets it", "Notes/note-00.md" not in cp.load_state(folder)["notes"])
        fake.hidden = {"Growth/Notes/note-00.md", "Growth/Notes/note-01.md"}
        env.run("repo", "copy", "zorg-growth", "--now", "2026-11-03T10:00:00+02:00")
        fake.hidden = {"Growth/Notes/note-00.md"}
        env.run("repo", "copy", "zorg-growth", "--now", "2026-11-04T10:00:00+02:00")
        check("back on the server before the move: no longer missing",
              "missing_since" not in cp.load_state(folder)["notes"]["Notes/note-01.md"])

        print("— 6. --restore")
        check("still gone from the server, still in .removed/", os.path.isfile(moved))
        rc, out, res = env.run("repo", "copy", "zorg-growth", "--restore", "Notes/note-00.md", "--now", "2026-11-04T11:00:00+02:00")
        check("restored, exit 0", rc == 0 and os.path.isfile(os.path.join(folder, "Notes", "note-00.md"))
              and not os.path.exists(moved), out)
        st = cp.load_state(folder)
        check("the state marks it restored", st["notes"]["Notes/note-00.md"].get("restored") == "2026-11-04", st["notes"].get("Notes/note-00.md"))
        fake.hidden = {"Growth/Notes/note-00.md"}
        env.run("repo", "copy", "zorg-growth", "--now", "2026-11-05T10:00:00+02:00")
        env.run("repo", "copy", "zorg-growth", "--now", "2026-11-06T10:00:00+02:00")
        check("a restored note is never moved again", os.path.isfile(os.path.join(folder, "Notes", "note-00.md")))
        rc, out, res = env.run("repo", "copy", "zorg-growth", "--restore", "Notes/note-05.md")
        check("restoring what is not in .removed/ — exit 3", rc == 3 and "not in .removed" in out, out)
        fake.hidden = set()

        print("— 7. the lock")
        lock = os.path.join(folder, ".ctx-copy", "lock")
        open(lock, "w").write(json.dumps({"pid": os.getpid(), "at": time.time()}))
        rc, out, res = env.run("repo", "copy", "zorg-growth")
        check("a live lock → busy, exit 4", rc == 4 and res.get("outcome") == "busy", out)
        open(lock, "w").write(json.dumps({"pid": os.getpid(), "at": time.time() - 16 * 60}))
        rc, out, res = env.run("repo", "copy", "zorg-growth", "--now", "2026-11-07T10:00:00+02:00")
        check("a stale lock is taken over", rc == 0 and res["outcome"] == "complete" and not os.path.exists(lock), out)
        open(lock, "w").write(json.dumps({"pid": 999999, "at": time.time()}))
        rc, out, res = env.run("repo", "copy", "zorg-growth", "--now", "2026-11-07T11:00:00+02:00")
        check("a lock of a process that is gone is taken over", rc == 0 and res["outcome"] == "complete", out)

        print("— 8. what is refused")
        rc, out, res = env.run("repo", "copy", "zorg-nobody")
        check("no such repository — exit 3", rc == 3 and "zorg-nobody" in out, out)
        core = os.path.join(tmp, "zorg-core-folder")
        os.makedirs(core)
        open(os.path.join(prov, "zorg-core.yaml"), "w", encoding="utf-8").write(CORE.format(core=core))
        rc, out, res = env.run("repo", "copy", "zorg-core")
        check("a registration with its own folder — exit 3, «тека на диску»", rc == 3 and "тека на диску" in out, out)
        open(os.path.join(prov, "zorg-plain.yaml"), "w", encoding="utf-8").write(
            "schema: provider-registration/2\nid: zorg-plain\nkind: mcp\nstatus: active\n")
        rc, out, res = env.run("repo", "copy", "zorg-plain")
        check("no endpoint url — exit 3", rc == 3 and "endpoint" in out, out)
        check("…no folder made for either", not os.path.exists(cp.copy_dir(env.home, "zorg-core"))
              and not os.path.exists(cp.copy_dir(env.home, "zorg-plain")))
    rc, out, res = env.run("repo", "copy", "zorg-growth", "--now", "2026-11-08T10:00:00+02:00")
    check("the server does not answer — exit 5, unreachable, nothing written", rc == 5 and res["outcome"] == "unreachable", out)

    print("— 9. progress on stderr, in process")
    with FakeMcp(tree=tree(5)) as fake:
        lines = []
        old = cp.SAVE_EVERY
        cp.SAVE_EVERY = 2
        try:
            repo = {"id": "zorg-progress", "endpoint": {"url": fake.url, "root": "Growth/", "headers_env": ""}, "writable": []}
            cp.run(env.home, repo, datetime.datetime(2026, 10, 29, 9, tzinfo=datetime.timezone.utc), progress=lines.append)
        finally:
            cp.SAVE_EVERY = old
        check("«копія: N з M…» every SAVE_EVERY notes", lines[:2] == ["копія: 2 з 6…", "копія: 4 з 6…"], lines)
    with FakeMcp(tree={}) as fake:
        repo = {"id": "zorg-empty", "endpoint": {"url": fake.url, "root": "Growth/", "headers_env": ""}, "writable": []}
        res = cp.run(env.home, repo, datetime.datetime(2026, 10, 29, 9, tzinfo=datetime.timezone.utc))
        check("a first copy whose listing is empty is held, no complete pass", res["outcome"] == "held"
              and not cp.load_state(cp.copy_dir(env.home, "zorg-empty"))["complete_at"], res)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("— 10. no branch deletes a note")
src = open(os.path.join(ROOT, "scripts", "ctx_copy.py"), encoding="utf-8").read()
funcs = re.split(r"\n(?=\s*def )", src)
removers = {}
for f in funcs:
    name = re.match(r"\s*def (\w+)", f)
    for call in ("os.remove(", "os.unlink(", "shutil.rmtree(", "os.rmdir(", ".unlink("):
        if call in f:
            removers.setdefault(name.group(1) if name else "<module>", set()).add(call)
check("os.remove and os.rmdir are never called", not any("os.remove(" in c or "os.rmdir(" in c for c in removers.values()), removers)
check("os.unlink only on the lock file (take_lock, release_lock)",
      {k for k, v in removers.items() if "os.unlink(" in v} <= {"take_lock", "release_lock"}, removers)
check("shutil.rmtree only on the copy's old backups (_prune_backups)",
      {k for k, v in removers.items() if "shutil.rmtree(" in v} == {"_prune_backups"}, removers)

print("RESULT:", "GREEN ✅" if not fails else "RED ❌", "(%d failed)" % fails)
sys.exit(1 if fails else 0)
