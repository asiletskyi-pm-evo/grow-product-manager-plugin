#!/usr/bin/env python3
"""TC-ctx-3110-ops — scripts/ctx_ops.py: the context store's operations (since v3.11.0).

Lock, snapshots, rotation and restore; migrate, compile and the sync of direct edits to
local-context.md. Every case runs on temp copies of the fictional fixtures
(testing/fixtures/ctx/, "Zorg") with a temp HOME and a temp vault; semantics:
references/context-protocol.md. Stdlib only; run from the repo root.
"""
import datetime, json, os, shutil, sys, tempfile, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import ctx_store as cs  # noqa: E402
import ctx_ops as co  # noqa: E402

FIX = os.path.join(ROOT, "testing", "fixtures", "ctx")
fails = 0


def check(name, cond, detail=""):
    global fails
    fails += not cond
    print(("✅" if cond else "❌"), name, ("" if cond else "-> " + str(detail)[:600]))


def read(*parts):
    return open(os.path.join(*parts), encoding="utf-8", newline="").read()


def tree(path):
    """{relative path: bytes} of every file under path (empty when absent)."""
    out = {}
    for dp, _, fn in os.walk(path):
        for f in fn:
            p = os.path.join(dp, f)
            out[os.path.relpath(p, path)] = open(p, "rb").read()
    return out


def seeded_store(d):
    st = cs.Store(os.path.join(d, "store"))
    for r in cs.assign_ids(cs.split_sections(read(FIX, "typical.md"))):
        st.write(dict(r, ctx=1, owner="user", source="migrated", modified="2026-10-20T10:00:00+03:00", body=r["text"]))
    st.save_state({"compiled_at": "2026-10-20"})
    copy = os.path.join(d, "home", ".grow-pm", "local-context.md")
    os.makedirs(os.path.dirname(copy))
    open(copy, "w", encoding="utf-8", newline="").write(read(FIX, "typical.md"))
    return st, copy


# --- Task 5: lock, snapshots, rotation, restore
with tempfile.TemporaryDirectory() as d:
    st, copy = seeded_store(d)
    home = os.path.join(d, "home")
    before_store, before_copy = tree(st.root), read(copy)
    snap = co.snapshot(st, [copy], home, "test")
    check("snapshot is under ~/.grow-pm/snapshots", snap.startswith(os.path.join(home, ".grow-pm", "snapshots") + os.sep)
          and os.path.isfile(os.path.join(snap, "manifest.json")), snap)
    check("two snapshots without changes are one", co.snapshot(st, [copy], home, "again") == snap)
    rec = st.load()[4]
    st.write(dict(rec, body=rec["body"].replace("PROJ", "XXX")))
    open(copy, "w", encoding="utf-8").write("changed\n")
    co.restore(snap, st, [copy])
    check("restore gives the bytes back", tree(st.root) == before_store and read(copy) == before_copy)

with tempfile.TemporaryDirectory() as d:
    home = os.path.join(d, "home"); os.makedirs(os.path.join(home, ".grow-pm"))
    st = cs.Store(os.path.join(d, "vault", "Notes", "_System", "context"))
    copy = os.path.join(home, ".grow-pm", "local-context.md")
    open(copy, "w", encoding="utf-8").write(read(FIX, "typical.md"))
    snap = co.snapshot(st, [copy], home, "pre-migrate")
    st.write({"id": "profile", "type": "profile", "title": "User Profile", "parent": None, "order": 10, "ctx": 1,
              "owner": "user", "source": "migrated", "modified": "x", "body": "## User Profile\n"})
    st.save_state({})
    co.restore(snap, st, [copy])
    check("restoring a pre-store snapshot empties the store", tree(st.root) == {} and read(copy) == read(FIX, "typical.md"),
          tree(st.root))

with tempfile.TemporaryDirectory() as d:
    root = os.path.join(d, "snapshots"); os.makedirs(root)
    now = datetime.datetime(2026, 10, 30, 15, 0, 0)
    made = []
    for day in range(30):
        for hour in ((12, 13) if day < 10 else (12,)):
            t = now.replace(hour=hour) - datetime.timedelta(days=day)
            name = t.strftime("%Y%m%dT%H%M%S") + "-op"
            os.makedirs(os.path.join(root, name)); made.append(name)
    removed = sorted(os.path.basename(p) for p in co.rotate(root, now=now))
    expect = sorted((now.replace(hour=12) - datetime.timedelta(days=day)).strftime("%Y%m%dT%H%M%S") + "-op"
                    for day in range(14, 30))
    check("rotation keeps the last 20 and one per day for 14 days", len(made) == 40 and removed == expect
          and len(os.listdir(root)) == 24, (len(removed), removed[:3]))

with tempfile.TemporaryDirectory() as home:
    os.makedirs(os.path.join(home, ".grow-pm"))
    lockf = os.path.join(home, ".grow-pm", ".ctx.lock")
    open(lockf, "w").write(json.dumps({"pid": os.getpid(), "at": time.time()}))
    try:
        with co.lock(home):
            busy = False
    except co.Busy:
        busy = True
    check("a live lock is busy", busy)
    open(lockf, "w").write(json.dumps({"pid": os.getpid(), "at": time.time() - 200}))
    with co.lock(home):
        held = os.path.isfile(lockf)
    check("a lock older than 120 s is taken over and released", held and not os.path.exists(lockf))
    open(lockf, "w").write(json.dumps({"pid": 999999, "at": time.time()}))
    with co.lock(home):
        pass
    check("a dead process's lock is taken over", not os.path.exists(lockf))

print("RESULT:", "GREEN ✅" if not fails else "RED ❌", "(%d failed)" % fails)
sys.exit(1 if fails else 0)
