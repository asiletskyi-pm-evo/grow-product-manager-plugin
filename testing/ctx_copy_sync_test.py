#!/usr/bin/env python3
"""TC-ctx-3240-copy-sync — the daily pass of the copy, started by `ctx provider sync` (since v3.24.0).

A temp HOME and vault (testing/ctx_testenv.py, the typical fictional context) with a store, an MCP-only registration of
the fictional "Zorg" with `sync: daily` against the fake server (testing/mcp_fake.py, 127.0.0.1), and its copy. Covers:
not due (a complete pass under a day old), due, busy (a live lock) — in CTX_RESULT `copy`; the sync reads the copy as it
was (yesterday's complete one) before it starts the pass, so a change on the server reaches the blocks a day later;
`--if-due` with nothing due answers within the budget without the network; a part «копія ядра» in the day's report only on
a change, a held or a partial pass, never twice for the same held; health ✋ after two helds and ⚠ for a stale copy;
`repo status` and `repo list` name the copy; the background never makes the first copy, nor runs for a paused or
`sync: off` repository; and one real `--background` pass that outlives the sync, ends and releases its lock.
The passes inside the sync run in the foreground (GROW_PM_COPY_FOREGROUND=1) except the last one.
Semantics: references/context-provider-protocol.md §12.11–§12.12. Stdlib only; run from the repo root.
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
blocks_source: paths
sync: {sync}
status: {status}
"""


def blocks(v, line):
    return ("# Zorg Growth blocks\n\n<!-- zorg-growth:begin id=growth-metrics v=%s -->\n#### Growth metrics\n- **North star:** %s\n"
            "<!-- zorg-growth:end id=growth-metrics -->\n" % (v, line))


def tree():
    t = {"Growth/_System/context-blocks.md": blocks("0.1", "weekly active shoppers")}
    for i in range(6):
        t["Growth/Notes/note-%d.md" % i] = "# Zorg note %d\n" % i
    return t


def at(days, hours=0):
    return (datetime.datetime(2026, 10, 29, 9, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=2)))
            + datetime.timedelta(days=days, hours=hours)).isoformat()


def report(env, day):
    p = os.path.join(env.store, "sync", day + ".md")
    return open(p, encoding="utf-8").read() if os.path.isfile(p) else ""


tmp = tempfile.mkdtemp(prefix="ctx-copy-sync-")
os.environ["GROW_PM_COPY_FOREGROUND"] = "1"
try:
    env = Env(tmp)
    rc, out, _ = env.run("migrate", "--apply")
    check("a store", rc == 0, out)
    prov = os.path.join(env.home, ".grow-pm", "providers")
    os.makedirs(prov)
    reg = os.path.join(prov, "zorg-growth.yaml")
    folder = cp.copy_dir(env.home, "zorg-growth")
    with FakeMcp(tree=tree()) as fake:
        open(reg, "w", encoding="utf-8").write(REG.format(url=fake.url, sync="daily", status="active"))
        print("— 1. no copy: the sync never makes one")
        rc, out, res = env.run("provider", "sync", "--if-due", "--now", at(0))
        check("no copy key, no folder", rc == 0 and "copy" not in res and not os.path.exists(folder), res)
        rc, out, res = env.run("repo", "copy", "zorg-growth", "--background", "--now", at(0))
        check("repo copy --background without a copy — exit 3", rc == 3 and "not in the background" in out, out)

        rc, out, res = env.run("repo", "copy", "zorg-growth", "--now", at(0))
        check("the first copy, by the command", rc == 0 and res["outcome"] == "complete", out)
        rc, out, res = env.run("provider", "apply", "zorg-growth", "--add", "growth-metrics")
        check("a block held from the copy", rc == 0 and "weekly active shoppers" in open(env.ctx, encoding="utf-8").read(), out)

        print("— 2. not due, then due")
        rc, out, res = env.run("provider", "sync", "--now", at(0, 2))
        check("a copy under a day old: not-due", res.get("copy") == {"zorg-growth": "not-due"}, res)
        fake.tree["Growth/_System/context-blocks.md"] = blocks("0.2", "monthly active shoppers")
        rc, out, res = env.run("provider", "sync", "--now", at(1, 1))
        check("a day later: started", res.get("copy") == {"zorg-growth": "started"}, res)
        check("…the blocks were read from yesterday's copy (no change yet)",
              "monthly active shoppers" not in open(env.ctx, encoding="utf-8").read(), res.get("results"))
        st = cp.load_state(folder)
        check("…and then the copy was brought up to date", st["complete_at"] == at(1, 1)
              and "monthly" in open(os.path.join(folder, "_System", "context-blocks.md"), encoding="utf-8").read(), st["complete_at"])
        day1 = at(1)[:10]
        check("a change earns a part «копія ядра» in the day's report",
              "## zorg-growth · копія ядра" in report(env, day1) and "оновлено 1" in report(env, day1), report(env, day1))
        rc, out, res = env.run("provider", "sync", "--now", at(2, 2))
        check("the next day's sync takes the block from the fresh copy",
              "monthly active shoppers" in open(env.ctx, encoding="utf-8").read(), out)
        check("a pass with no change adds no part", "копія ядра" not in report(env, at(2)[:10]), report(env, at(2)[:10]))

        print("— 3. held, twice")
        fake.list_cap = 1
        env.run("provider", "sync", "--now", at(3, 3))
        env.run("provider", "sync", "--now", at(3, 5))
        r3 = report(env, at(3)[:10])
        check("a held pass earns one part; the same held again adds none", r3.count("## zorg-growth · копія ядра") == 1
              and "не оновлено" in r3, r3)
        rc, out, res = env.run("health", "--json")
        check("health ✋ after two helds in a row", "✋" in out and "копія zorg-growth: сервер 2 рази поспіль" in out, out[-1200:])
        fake.list_cap = None

        print("— 4. busy, and --if-due with nothing due")
        lockp = os.path.join(folder, ".ctx-copy", "lock")
        open(lockp, "w").write(json.dumps({"pid": os.getpid(), "at": time.time(), "token": "test"}))
        rc, out, res = env.run("provider", "sync", "--now", at(5))
        check("a live lock: busy", res.get("copy") == {"zorg-growth": "busy"}, res)
        os.unlink(lockp)
        env.run("repo", "copy", "zorg-growth", "--now", at(6))
    open(reg, "w", encoding="utf-8").write(REG.format(url="http://127.0.0.1:9/mcp", sync="daily", status="active"))
    t0 = time.monotonic()
    rc, out, res = env.run("provider", "sync", "--if-due", "--now", at(6, 3))
    took = time.monotonic() - t0
    check("--if-due with nothing due: only CTX_RESULT, not-due, no network, within the budget",
          rc == 0 and res.get("copy") == {"zorg-growth": "not-due"} and out.strip().startswith("CTX_RESULT") and took < 4, (took, out))

    print("— 5. status, list, health")
    rc, out, res = env.run("repo", "status", "zorg-growth")
    check("repo status names the copy", re.search(r"копія: 2026-11-04 · \d+ нотаток · complete", out), out)
    rc, out, res = env.run("repo", "list")
    check("repo list names the copy", "zorg-growth · копія: 2026-11-04" in out, out)
    st = cp.load_state(folder)
    five = (datetime.datetime.now().astimezone() - datetime.timedelta(days=5)).isoformat(timespec="seconds")
    st["complete_at"] = five
    cp.save_state(folder, st)
    rc, out, res = env.run("health")
    check("health ⚠ for a copy older than 3 days with sync: daily", "копія zorg-growth від %s — старша за 3 дні" % five[:10] in out, out[-900:])
    os.makedirs(os.path.join(cp.conflicts_dir(env.home, "zorg-growth"), "2026-11-04", "Notes"))
    open(os.path.join(cp.conflicts_dir(env.home, "zorg-growth"), "2026-11-04", "Notes", "note-1.md"), "w").write("x\n")
    rc, out, res = env.run("health")
    check("health ⚠ for conflicts waiting", "копія zorg-growth: конфліктів 1" in out, out[-900:])

    print("— 6. paused, sync off")
    for sync, status in (("off", "active"), ("daily", "paused")):
        open(reg, "w", encoding="utf-8").write(REG.format(url="http://127.0.0.1:9/mcp", sync=sync, status=status))
        rc, out, res = env.run("provider", "sync", "--if-due", "--now", at(9))
        check("sync %s / %s: no background" % (sync, status), "copy" not in res, res)
        if sync == "off":
            rc, out, res = env.run("provider", "plan", "zorg-growth")
            check("plan of a copy without sync: daily says how to bring it up to date", "оновити: ctx repo copy zorg-growth" in out, out)

    print("— 7. a real background pass")
    del os.environ["GROW_PM_COPY_FOREGROUND"]
    with FakeMcp(tree=tree()) as fake:
        open(reg, "w", encoding="utf-8").write(REG.format(url=fake.url, sync="daily", status="active"))
        st = cp.load_state(folder)
        old = (datetime.datetime.now().astimezone() - datetime.timedelta(days=2)).isoformat(timespec="seconds")
        st["complete_at"] = st["attempt_at"] = old
        cp.save_state(folder, st)
        t0 = time.monotonic()
        rc, out, res = env.run("provider", "sync", "--if-due")
        took = time.monotonic() - t0
        check("the sync starts it and returns", res.get("copy") == {"zorg-growth": "started"}, res)
        done = False
        for _ in range(200):
            time.sleep(0.1)
            st = cp.load_state(folder)
            if st["complete_at"] != old and not os.path.exists(os.path.join(folder, ".ctx-copy", "lock")):
                done = True
                break
        check("the background pass ends, its lock released, the copy complete", done, st.get("outcome"))
        log = open(os.path.join(folder, ".ctx-copy", "log"), encoding="utf-8").read()
        check("its output went to .ctx-copy/log", "копія zorg-growth:" in log, log[-500:])
finally:
    os.environ.pop("GROW_PM_COPY_FOREGROUND", None)
    shutil.rmtree(tmp, ignore_errors=True)

print("RESULT:", "GREEN ✅" if not fails else "RED ❌", "(%d failed)" % fails)
sys.exit(1 if fails else 0)
