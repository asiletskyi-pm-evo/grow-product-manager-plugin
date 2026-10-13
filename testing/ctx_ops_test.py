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
import ctx_blocks as cb  # noqa: E402

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

# --- v3.13 Task 5: the block state and the bases are in every snapshot, and come back on restore
with tempfile.TemporaryDirectory() as d:
    st, copy = seeded_store(d)
    home = os.path.join(d, "home")
    text = "<!-- zorg-core:begin id=scope v=0.4 -->\n### Scope\nThe user works on Zorg App only.\n<!-- zorg-core:end id=scope -->"
    sha = cb.put_base(st, "zorg-core", text)
    growth = cb.put_base(st, "zorg-growth", "growth base")
    saved = {"checked": "2026-10-20T10:00:00+03:00", "source": "folder", "version": "0.4",
             "blocks": {"scope": {"base_sha": sha, "bases": [sha], "v": "0.4", "host": "custom.zorg-core-notes",
                                  "checked": "2026-10-20T10:00:00+03:00", "user_removed": False}}}
    cb.save_state(st, "zorg-core", saved)
    before = tree(st.root)
    snap = co.snapshot(st, [copy], home, "blocks")
    check("snapshot copies state subfolders",
          os.path.isfile(os.path.join(snap, "state", "blocks", "zorg-core", sha + ".md"))
          and os.path.isfile(os.path.join(snap, "state", "blocks", "zorg-growth", growth + ".md"))
          and os.path.isfile(os.path.join(snap, "state", "blocks", "zorg-core.json"))
          and os.path.isfile(os.path.join(snap, "state", "compiled.json")), sorted(tree(snap)))
    check("a nested base is copied byte for byte",
          os.path.isfile(os.path.join(snap, "state", "blocks", "zorg-core", sha + ".md"))
          and read(snap, "state", "blocks", "zorg-core", sha + ".md") == text, "")
    check("a snapshot with the same files, nested ones too, is reused", co.snapshot(st, [copy], home, "again") == snap, "")
    # a hidden file (a temp file of an interrupted write), a hidden folder and a linked folder are never captured
    blocks = os.path.join(st.state_dir, "blocks")
    elsewhere = os.path.join(d, "elsewhere"); os.makedirs(elsewhere)
    open(os.path.join(elsewhere, "outside.md"), "w").write("outside")
    os.makedirs(os.path.join(blocks, "zorg-core", ".cache")); os.makedirs(os.path.join(blocks, ".hidden"))
    open(os.path.join(blocks, "zorg-core", ".halfway.md.tmp"), "w").write("half")
    open(os.path.join(blocks, "zorg-core", ".cache", "x.md"), "w").write("x")
    open(os.path.join(blocks, ".hidden", "y.md"), "w").write("y")
    os.symlink(elsewhere, os.path.join(blocks, "zorg-linked"))
    check("a hidden file or folder and a linked folder under state/ are skipped — the snapshot is the same",
          co.snapshot(st, [copy], home, "hidden") == snap
          and sorted(tree(os.path.join(snap, "state", "blocks"))) == sorted(
              ["zorg-core.json", "zorg-core/" + sha + ".md", "zorg-growth/" + growth + ".md"]), sorted(tree(os.path.join(snap, "state", "blocks"))))
    os.remove(os.path.join(blocks, "zorg-linked"))
    shutil.rmtree(os.path.join(blocks, ".hidden")); shutil.rmtree(os.path.join(blocks, "zorg-core", ".cache"))
    os.remove(os.path.join(blocks, "zorg-core", ".halfway.md.tmp"))
    # undo: the bases are gone from the store, restore brings them back
    shutil.rmtree(os.path.join(st.state_dir, "blocks"))
    check("(setup) the bases are gone", cb.get_base(st, "zorg-core", sha) is None and cb.load_state(st, "zorg-core")["blocks"] == {}, "")
    co.restore(snap, st, [copy])
    check("undo restores the bases", cb.get_base(st, "zorg-core", sha) == text and cb.get_base(st, "zorg-growth", growth) == "growth base", "")
    check("…and the block state, and the store byte for byte", cb.load_state(st, "zorg-core") == saved and tree(st.root) == before,
          set(tree(st.root)) ^ set(before))
    # a change in a nested base is a change of the snapshot
    cb.put_base(st, "zorg-core", "a second version of the block")
    snap2 = co.snapshot(st, [copy], home, "second")
    check("a new base makes a new snapshot that holds both bases",
          snap2 != snap and os.path.isfile(os.path.join(snap2, "state", "blocks", "zorg-core", sha + ".md"))
          and os.path.isfile(os.path.join(snap2, "state", "blocks", "zorg-core", cs.sha_text("a second version of the block") + ".md")), snap2)
    # undo an operation that pruned: restore from the older snapshot gives back the pruned base
    cb.prune_bases(st, "zorg-core", saved)
    check("(setup) pruning dropped the second version", cb.get_base(st, "zorg-core", cs.sha_text("a second version of the block")) is None, "")
    co.restore(snap2, st, [copy])
    check("undo of a pruning gives the pruned base back", cb.get_base(st, "zorg-core", cs.sha_text("a second version of the block"))
          == "a second version of the block", "")

# a snapshot made before v3.13 (the state folder holds files only) restores as it did
with tempfile.TemporaryDirectory() as d:
    st, copy = seeded_store(d)
    home = os.path.join(d, "home")
    old_tree = tree(st.root)
    snap = os.path.join(d, "snap-v312")
    for rel, data in old_tree.items():
        p = os.path.join(snap, rel.replace(".state", "state", 1) if rel.startswith(".state") else rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "wb").write(data)
    os.makedirs(os.path.join(snap, "copies"))
    open(os.path.join(snap, "copies", "0.md"), "w", encoding="utf-8", newline="").write(read(copy))
    json.dump({"label": "old", "created": "2026-09-01T10:00:00+03:00", "store": st.root, "store_existed": True,
               "copies": [{"path": copy, "file": "copies/0.md", "existed": True}], "hash": "x"},
              open(os.path.join(snap, "manifest.json"), "w", encoding="utf-8"))
    sha = cb.put_base(st, "zorg-core", "made after the snapshot")
    cb.save_state(st, "zorg-core", {"checked": "x", "source": None, "version": None, "blocks": {}})
    rec = st.load()[4]
    st.write(dict(rec, body=rec["body"].replace("PROJ", "XXX")))
    co.restore(snap, st, [copy])
    check("a snapshot made before v3.13 (no state subfolders) restores the store as it was",
          tree(st.root) == {k: v for k, v in old_tree.items()}, set(tree(st.root)) ^ set(old_tree))
    check("…and what was added since is gone, as before", cb.get_base(st, "zorg-core", sha) is None, "")

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

# --- Task 6: migrate, compile, sync
NOW = "2026-10-20T10:00:00+03:00"


class Env:
    """A temp HOME with the typical context, a temp vault with its mirror, and the store paths."""

    def __init__(self, d, fixture="typical"):
        self.home = os.path.join(d, "home")
        self.vault = os.path.join(d, "vault")
        os.makedirs(os.path.join(self.home, ".grow-pm"))
        os.makedirs(os.path.join(self.vault, "Notes", "_System"))
        self.text = read(FIX, fixture + ".md").replace("{{VAULT}}", self.vault)
        self.ctx = os.path.join(self.home, ".grow-pm", "local-context.md")
        self.mirror = os.path.join(self.vault, "Notes", "_System", "local-context.md")
        for p in (self.ctx, self.mirror):
            open(p, "w", encoding="utf-8", newline="").write(self.text)
        self.copies = co.copies_for(self.ctx, self.text, home=self.home)
        self.store = cs.Store(co.store_root_for(self.text, home=self.home))

    def migrate(self, apply=True):
        return co.migrate(self.ctx, self.store.root, self.copies, self.home, apply=apply, now=NOW)

    def sync(self, **kw):
        return co.apply_sync(self.store, co.plan_sync(self.store, self.copies), self.copies, self.home,
                             kw.pop("source", "test"), kw.pop("reason", ""), NOW, **kw)

    def edit(self, path, old, new):
        t = read(path)
        assert old in t, old
        open(path, "w", encoding="utf-8", newline="").write(t.replace(old, new, 1))


def body_of(env, rid):
    return {r["id"]: r for r in env.store.load()}[rid]["body"]


with tempfile.TemporaryDirectory() as d:
    e = Env(d)
    check("copies are the home file and the vault mirror, as real paths",
          e.copies == [os.path.realpath(e.ctx), os.path.realpath(e.mirror)]
          and e.store.root == os.path.join(e.vault, "Notes", "_System", "context"), (e.copies, e.store.root))
    rep = e.migrate(apply=False)
    check("migrate dry run reports identical", rep["identical"] is True and len(rep["records"]) == 14
          and rep["custom"] == [] and not os.path.exists(e.store.root), rep)
    rep = e.migrate()
    check("migrate apply leaves copies byte-identical", read(e.ctx) == e.text and read(e.mirror) == e.text
          and len(os.listdir(e.store.records_dir)) == 14 and os.path.isfile(e.store.card_path)
          and e.store.journal_entries()[-1]["op"] == "migrate", rep)
    try:
        e.migrate(); refused = False
    except co.Refused:
        refused = True
    check("a second migrate is refused", refused)

with tempfile.TemporaryDirectory() as d:
    e = Env(d); e.migrate()
    e.edit(e.ctx, "- **Jira Project Key:** PROJ", "- **Jira Project Key:** PRJ")
    e.sync()
    check("edit in the home copy imports", "PRJ" in body_of(e, "product.zorg-app")
          and e.store.journal_entries()[-1]["source"] == "test" and read(e.mirror) == read(e.ctx))

with tempfile.TemporaryDirectory() as d:
    e = Env(d); e.migrate()
    open(e.ctx, "a", encoding="utf-8").write("\n## Zorg notes\n- x\n")
    e.sync()
    recs = e.store.load()
    check("new section becomes a record", recs[-1]["id"] == "custom.zorg-notes" and read(e.ctx).endswith("## Zorg notes\n- x\n")
          and read(e.mirror) == read(e.ctx), [r["id"] for r in recs][-3:])

TEMPLATES = "## Templates\n\n- **Preference:** builtin\n- **Default language:** en\n\n"
PLANNING = "## Planning (planning-suite)\n\n- **Sprint length:** 2 weeks\n- **Quarter start:** 2026-10-01\n\n"
FOCUS = "## Focus (focus-advisor)\n\n- **Cadence:** daily\n\n"
with tempfile.TemporaryDirectory() as d:
    e = Env(d); e.migrate()
    e.edit(e.ctx, TEMPLATES, "")
    res = e.sync()
    snap = res["snapshot"]
    check("one removal goes to the snapshot", "setting.templates" not in [r["id"] for r in e.store.load()]
          and res["removed"] == ["setting.templates"]
          and os.path.isfile(os.path.join(snap, "records", "setting.templates.md")), res)

with tempfile.TemporaryDirectory() as d:
    e = Env(d); e.migrate()
    for s in (TEMPLATES, PLANNING, FOCUS):
        e.edit(e.ctx, s, "")
    before = tree(e.store.root)
    try:
        e.sync(); conflict = None
    except co.Conflict as x:
        conflict = x.payload
    check("three removals are a conflict", conflict is not None and conflict.get("suspicious_removal")
          and tree(e.store.root) == before, conflict)
    e.sync(accept_removals=True)
    check("accepted removals apply", len(e.store.load()) == 11)

with tempfile.TemporaryDirectory() as d:
    e = Env(d); e.migrate()
    e.edit(e.ctx, "### Team: Alpha (A)", "### Team: Alpha Squad (A)")
    e.sync()
    team = {r["id"]: r for r in e.store.load()}.get("team.alpha-a")
    check("rename keeps the id", team is not None and team["title"] == "Team: Alpha Squad (A)"
          and "team.alpha-squad-a" not in [r["id"] for r in e.store.load()], [r["id"] for r in e.store.load()])

with tempfile.TemporaryDirectory() as d:
    e = Env(d); e.migrate()
    p = os.path.join(e.store.records_dir, "product.zorg-app.md")
    e.edit(p, "- **Jira Project Key:** PROJ", "- **Jira Project Key:** REC")
    e.edit(e.ctx, "- **Jira Project Key:** PROJ", "- **Jira Project Key:** FILE")
    try:
        e.sync(); conflict = None
    except co.Conflict as x:
        conflict = x.payload
    ids = [c["id"] for c in (conflict or {}).get("conflicts", [])]
    check("record and copy both changed is a conflict", ids == ["product.zorg-app"], conflict)
    e.sync(resolve={"product.zorg-app": "file"})
    check("resolve=file takes the file", "FILE" in body_of(e, "product.zorg-app") and "FILE" in read(e.mirror))

with tempfile.TemporaryDirectory() as d:
    e = Env(d); e.migrate()
    e.edit(e.ctx, "- **Jira Project Key:** PROJ", "- **Jira Project Key:** H")
    e.edit(e.mirror, "- **Jira Project Key:** PROJ", "- **Jira Project Key:** M")
    try:
        e.sync(); conflict = None
    except co.Conflict as x:
        conflict = x.payload
    check("two copies changed differently is a conflict",
          [c["id"] for c in (conflict or {}).get("conflicts", [])] == ["product.zorg-app"], conflict)

with tempfile.TemporaryDirectory() as d:
    e = Env(d); e.migrate()
    e.edit(os.path.join(e.store.records_dir, "product.zorg-app.md"), "- **Jira Project Key:** PROJ", "- **Jira Project Key:** R")
    plan = co.plan_sync(e.store, e.copies)
    e.sync()
    check("record edited directly compiles out", plan["record_changes"] == ["product.zorg-app"]
          and "- **Jira Project Key:** R" in read(e.ctx) and read(e.mirror) == read(e.ctx), plan)

with tempfile.TemporaryDirectory() as d:
    e = Env(d); e.migrate()
    os.remove(e.mirror)
    e.sync()
    check("compile creates a missing mirror", os.path.isfile(e.mirror) and read(e.mirror) == read(e.ctx))

with tempfile.TemporaryDirectory() as d:
    e = Env(d); e.migrate()
    open(e.ctx, "w", encoding="utf-8", newline="").write(e.text.replace("\n", "\r\n"))
    plan = co.plan_sync(e.store, e.copies)
    e.sync()
    check("CRLF rewrite imports as edits", plan["removes"] == [] and plan["adds"] == [] and plan["conflicts"] == []
          and len(plan["edits"]) == 14 and read(e.mirror) == read(e.ctx), {k: plan[k] for k in ("removes", "adds")})

with tempfile.TemporaryDirectory() as d:
    e = Env(d); e.migrate()
    before = tree(e.store.root), read(e.ctx), read(e.mirror)
    res = e.sync()
    check("a sync with nothing to do writes nothing", res["snapshot"] is None
          and (tree(e.store.root), read(e.ctx), read(e.mirror)) == before)

# --- Final review: a compile never drops, reverts or overwrites without a snapshot and a journal line
def attempt(env, **kw):
    try:
        return env.sync(**kw), None
    except (cs.StoreError, co.Conflict) as x:
        return None, x


with tempfile.TemporaryDirectory() as d:
    e = Env(d); e.migrate()
    os.remove(os.path.join(e.store.records_dir, "setting.templates.md"))
    before = read(e.ctx), read(e.mirror)
    digest = co.status_summary(e.ctx, home=e.home)
    res, err = attempt(e)
    check("a record file missing on disk stops the sync, copies untouched", isinstance(err, cs.StoreError)
          and "setting.templates" in str(err) and (read(e.ctx), read(e.mirror)) == before, err)
    check("the digest flags a missing record", digest is not None and digest["conflicts"] >= 1, digest)
    res, err = attempt(e, accept_removals=True)
    check("--accept-removals drops a missing record after a snapshot that holds its section",
          err is None and res["removed"] == ["setting.templates"] and "## Templates" not in read(e.ctx)
          and "## Templates" in read(res["snapshot"], "copies", "0.md"), err or res)

with tempfile.TemporaryDirectory() as d:
    e = Env(d); e.migrate()
    shutil.rmtree(e.store.records_dir); os.makedirs(e.store.records_dir)
    before = read(e.ctx), read(e.mirror)
    res, err = attempt(e)
    check("an emptied records folder never empties the copies", isinstance(err, cs.StoreError)
          and (read(e.ctx), read(e.mirror)) == before and len(before[0]) > 0, err)

with tempfile.TemporaryDirectory() as d:
    e = Env(d); e.migrate()
    moved = e.text.replace(TEMPLATES, "").replace(FOCUS, FOCUS + TEMPLATES)
    open(e.ctx, "w", encoding="utf-8", newline="").write(moved)
    digest = co.status_summary(e.ctx, home=e.home)
    res, err = attempt(e)
    ids = [r["id"] for r in e.store.load()]
    check("a reorder in the copy is imported, not reverted", err is None and read(e.ctx) == moved
          and read(e.mirror) == moved and ids.index("setting.templates") > ids.index("setting.focus-focus-advisor")
          and res["snapshot"] and e.store.journal_entries()[-1]["op"] == "sync", (err, ids))
    check("the digest counts a reorder as an edit to import", digest is not None and digest["pending"] >= 1, digest)

with tempfile.TemporaryDirectory() as d:
    e = Env(d)
    e.edit(e.mirror, "- **Cadence:** daily", "- **Cadence:** hourly")      # the mirror drifted before the move
    e.migrate()
    e.edit(e.mirror, "- **Cadence:** hourly", "- **Cadence:** minutely")   # and was edited again in Obsidian
    res, err = attempt(e)
    j = e.store.journal_entries()[-1]
    held = j.get("snapshot") and "minutely" in read(j["snapshot"], "copies", "1.md")
    check("a copy without a baseline is rewritten only after a snapshot that holds it, with a journal line",
          err is None and read(e.mirror) == read(e.ctx) and j["op"] == "compile" and held, (err, j))

with tempfile.TemporaryDirectory() as d:
    e = Env(d)
    os.remove(e.ctx); os.symlink(e.mirror, e.ctx)                         # one file, reached from both places
    copies = co.copies_for(e.ctx, e.text, home=e.home)
    co.migrate(e.ctx, e.store.root, copies, e.home, apply=True, now=NOW)
    e.edit(e.mirror, "- **Cadence:** daily", "- **Cadence:** weekly")
    res = co.apply_sync(e.store, co.plan_sync(e.store, copies), copies, e.home, "test", "", NOW)
    check("a home copy linked to the mirror is one copy and stays a link", len(copies) == 1
          and os.path.islink(e.ctx) and "weekly" in body_of(e, "setting.focus-focus-advisor"), copies)

with tempfile.TemporaryDirectory() as d:
    st, copy = seeded_store(d)
    home = os.path.join(d, "home")
    root = os.path.join(home, ".grow-pm", "snapshots"); os.makedirs(root)
    for day in range(30):
        t = datetime.datetime.now() - datetime.timedelta(days=day + 20)
        os.makedirs(os.path.join(root, t.strftime("%Y%m%dT%H%M%S") + "-op"))
    snap = co.snapshot(st, [copy], home, "new")
    check("every new snapshot rotates the folder", os.path.isdir(snap) and len(os.listdir(root)) == 20,
          len(os.listdir(root)))

# --- v3.12 Task 0: write allow-list (spec §7a)
with tempfile.TemporaryDirectory() as d:
    e = Env(d); e.migrate()
    open(os.path.join(e.store.records_dir, "..md"), "w", encoding="utf-8").write(e.text[:200])
    ids = [r["id"] for r in e.store.load()]
    check("an id with a slash or .. is never a record file", cs.ID_RE.match("../x") is None
          and cs.ID_RE.match("a/b") is None and "." not in ids and ".." not in ids, ids)

# --- v3.12 Task 4: freshness
import ctx_schema as sc  # noqa: E402

TODAY = NOW[:10]
check("a record past its TTL is stale", sc.is_stale({"type": "product", "verified": "2026-01-01"}, {}, TODAY)
      and not sc.is_stale({"type": "setting", "verified": "2026-05-01"}, {}, TODAY))
check("ttl_days 0 is never stale", not sc.is_stale({"type": "product", "verified": "2020-01-01", "ttl_days": 0}, {}, TODAY))
check("garbage verified falls back", sc.verified_of({"type": "team", "verified": "soon"}, {"freshness_since": "2026-10-01"}) == "2026-10-01"
      and sc.ttl_of({"type": "team", "ttl_days": "x"}) == 90)

with tempfile.TemporaryDirectory() as d:
    e = Env(d); e.migrate()
    st = e.store.state()
    fresh_at_migrate = st.get("freshness_since")
    st.pop("freshness_since", None); e.store.save_state(st)
    e.sync()
    check("first v3.12 compile sets freshness_since", fresh_at_migrate == TODAY
          and e.store.state().get("freshness_since") == TODAY, (fresh_at_migrate, e.store.state().get("freshness_since")))

with tempfile.TemporaryDirectory() as d:
    e = Env(d); e.migrate()
    e.edit(e.ctx, "- **Jira Project Key:** PROJ", "- **Jira Project Key:** PRJ")
    e.sync()
    rec = {r["id"]: r for r in e.store.load()}["product.zorg-app"]
    check("an imported edit refreshes verified", rec.get("verified") == TODAY, rec.get("verified"))

with tempfile.TemporaryDirectory() as d:
    e = Env(d); e.migrate()
    p = os.path.join(e.store.records_dir, "product.zorg-app.md")
    e.edit(p, "- **Jira Project Key:** PROJ", "- **Jira Project Key:** R")
    body_before = {r["id"]: r for r in e.store.load()}["product.zorg-app"]["body"]
    e.sync()
    rec = {r["id"]: r for r in e.store.load()}["product.zorg-app"]
    check("an Obsidian record edit refreshes verified without touching the body", rec.get("verified") == TODAY
          and rec["body"] == body_before and "- **Jira Project Key:** R" in read(e.ctx), rec.get("verified"))

with tempfile.TemporaryDirectory() as d:
    e = Env(d); e.migrate()
    st = e.store.state(); st["freshness_since"] = "2025-01-01"; e.store.save_state(st)
    done = co.verify(e.store, e.copies, e.home, [], NOW, stale=True)
    recs = {r["id"]: r for r in e.store.load()}
    ops = [j["op"] for j in e.store.journal_entries()]
    check("verify --stale refreshes all stale and journals once", "product.zorg-app" in done and "profile" in done
          and "header" not in done and all(recs[i].get("verified") == TODAY for i in done)
          and ops.count("verify") == 1, (done, ops))

with tempfile.TemporaryDirectory() as d:
    e = Env(d); e.migrate()
    co.compile_store(e.store, e.copies, NOW, e.home)
    before = read(e.store.card_path)
    co.compile_store(e.store, e.copies, "2027-03-01T10:00:00+02:00", e.home)
    after = read(e.store.card_path)
    check("card marks stale rows and rebuilds when the stale set changes", "⚠" not in before and "⚠ 2026-10-20" in after
          and "Застарілі:" in after and "product.zorg-app" in e.store.state().get("stale", []), after[:400])

# --- v3.12 Task 5: lifecycle — invalidate, archive, trash, restore
def copies_text(env):
    return read(env.ctx), read(env.mirror)


def refused(fn, *a):
    try:
        fn(*a)
    except co.Refused:
        return True
    return False


with tempfile.TemporaryDirectory() as d:
    e = Env(d); e.migrate()
    before = copies_text(e)
    co.invalidate(e.store, e.copies, e.home, "team.alpha-a", "reorg", NOW)
    h, m = copies_text(e)
    rec = {r["id"]: r for r in e.store.load()}["team.alpha-a"]
    check("invalidate adds the region, keeps the section and journals", "> ⚠ Неактуально з 2026-10-20: reorg" in h
          and h == m and "### Team: Alpha (A)" in h and rec.get("status") == "invalid"
          and e.store.journal_entries()[-1]["op"] == "invalidate", rec.get("status"))
    co.restore_record(e.store, e.copies, e.home, "team.alpha-a", NOW)
    check("restore clears an invalid record byte for byte", copies_text(e) == before
          and {r["id"]: r for r in e.store.load()}["team.alpha-a"].get("status") is None)
    check("invalidate the header is refused", refused(co.invalidate, e.store, e.copies, e.home, "header", "x", NOW))

with tempfile.TemporaryDirectory() as d:
    e = Env(d); e.migrate()
    before = copies_text(e)
    co.archive(e.store, e.copies, e.home, "setting.templates", "old", NOW)
    gone = "## Templates" not in read(e.ctx) and os.path.isfile(os.path.join(e.store.root, "archive", "2026", "setting.templates.md"))
    co.restore_record(e.store, e.copies, e.home, "setting.templates", NOW)
    check("archive removes the section and restore puts it back at its place byte for byte", gone
          and copies_text(e) == before and not os.path.exists(os.path.join(e.store.root, "archive", "2026", "setting.templates.md")))

with tempfile.TemporaryDirectory() as d:
    e = Env(d); e.migrate()
    co.archive(e.store, e.copies, e.home, "setting.templates", "", NOW)
    open(e.ctx, "a", encoding="utf-8").write("\n" + TEMPLATES)
    e.sync()
    ids = [r["id"] for r in e.store.load()]
    co.restore_record(e.store, e.copies, e.home, "setting.templates", NOW)
    ids2 = [r["id"] for r in e.store.load()]
    check("archived ids are reserved", "setting.templates-2" in ids and "setting.templates" not in ids
          and {"setting.templates", "setting.templates-2"} <= set(ids2), (ids, ids2))

with tempfile.TemporaryDirectory() as d:
    e = Env(d); e.migrate()
    before = copies_text(e)
    e.edit(e.ctx, TEMPLATES, "")
    e.sync()
    trashed = [r["id"] for _, r in co.trash_entries(e.home)]
    co.restore_record(e.store, e.copies, e.home, "setting.templates", NOW)
    check("a removed section lands in the trash and restores", trashed == ["setting.templates"]
          and copies_text(e) == before, trashed)

with tempfile.TemporaryDirectory() as d:
    e = Env(d); e.migrate()
    os.remove(os.path.join(e.store.records_dir, "setting.templates.md"))
    e.sync(accept_removals=True)
    entry = [r for _, r in co.trash_entries(e.home) if r["id"] == "setting.templates"]
    check("accept-removals of a missing record trashes the copy's text", len(entry) == 1 and entry[0]["body"] == TEMPLATES,
          entry[:1])

with tempfile.TemporaryDirectory() as d:
    home = os.path.join(d, "home"); root = os.path.join(home, ".grow-pm", "trash"); os.makedirs(root)
    t = datetime.datetime(2026, 10, 20, 10, 0, 0)
    old = (t - datetime.timedelta(days=40)).strftime("%Y%m%dT%H%M%S") + "-setting.old.md"
    new = (t - datetime.timedelta(days=3)).strftime("%Y%m%dT%H%M%S") + "-setting.new.md"
    for n in (old, new):
        open(os.path.join(root, n), "w").write("x")
    gone = [os.path.basename(p) for p in co.purge_trash(home, now=t)]
    check("trash older than 30 days is purged", gone == [old] and os.listdir(root) == [new], (gone, os.listdir(root)))

with tempfile.TemporaryDirectory() as d:
    e = Env(d); e.migrate()
    e.edit(e.ctx, TEMPLATES, ""); e.sync()
    open(e.ctx, "a", encoding="utf-8").write("\n" + TEMPLATES); e.sync()
    check("restore refuses an id that is taken", "setting.templates" in [r["id"] for r in e.store.load()]
          and refused(co.restore_record, e.store, e.copies, e.home, "setting.templates", NOW))

with tempfile.TemporaryDirectory() as d:
    e = Env(d); e.migrate()
    co.invalidate(e.store, e.copies, e.home, "team.alpha-a", "reorg", NOW)
    t = read(e.ctx)
    a, b = t.index(cs.STATUS_BEGIN), t.index(cs.STATUS_END) + len(cs.STATUS_END) + 1
    open(e.ctx, "w", encoding="utf-8", newline="").write(t[:a] + t[b:])
    res = e.sync()
    rec = {r["id"]: r for r in e.store.load()}["team.alpha-a"]
    check("removing the status region reactivates", rec.get("status") is None and not cs.has_status_region(rec["body"])
          and "team.alpha-a" in res["changed"], (rec.get("status"), res["changed"]))

# --- v3.12 Task 8: v3.11 review minors
def env_with(d, extra):
    e = Env(d)
    e.text += extra
    for path in (e.ctx, e.mirror):
        open(path, "w", encoding="utf-8", newline="").write(e.text)
    e.migrate()
    return e


with tempfile.TemporaryDirectory() as d:
    e = env_with(d, "\n## Zorg Notes\n\n- one\n- two\n- three\n\n")
    e.edit(e.ctx, "## Zorg Notes", "## Feedback (Zorg)")
    e.sync()
    rec = {r["id"]: r for r in e.store.load()}.get("custom.zorg-notes")
    check("a section renamed to a schema title becomes a setting", rec is not None and rec["type"] == "setting"
          and rec["title"] == "Feedback (Zorg)", rec and (rec["type"], rec["title"]))

with tempfile.TemporaryDirectory() as d:
    e = env_with(d, "\n## Organization: Other\n\n")
    t = read(e.ctx)
    lite = t[t.index("### Product: Zorg Lite"):t.index("### Team: Alpha (A)")]
    open(e.ctx, "w", encoding="utf-8", newline="").write(t.replace(lite, "") + lite)
    e.sync()
    rec = {r["id"]: r for r in e.store.load()}["product.zorg-lite"]
    check("a product moved under another organisation gets the new parent", rec["parent"] == "org.other", rec["parent"])

with tempfile.TemporaryDirectory() as d:
    e = Env(d); e.migrate()
    p = os.path.join(e.store.records_dir, "product.zorg-app.md")
    e.edit(p, "- **Jira Project Key:** PROJ", "- **Jira Project Key:** OBS")
    e.sync()
    rec = {r["id"]: r for r in e.store.load()}["product.zorg-app"]
    check("an Obsidian record edit is journalled with its id and a fresh sha",
          "product.zorg-app" in e.store.journal_entries()[-1]["ids"] and rec["sha"] == cs.sha_text(rec["body"]),
          e.store.journal_entries()[-1])

with tempfile.TemporaryDirectory() as d:
    e = Env(d); e.migrate()
    e.edit(e.ctx, "- **Jira Project Key:** PROJ", "- **Jira Project Key:** CMP")
    co.apply_sync(e.store, co.plan_sync(e.store, e.copies), e.copies, e.home, "compile", "", NOW)
    rec = {r["id"]: r for r in e.store.load()}["product.zorg-app"]
    check("compile imports carry import:home", rec["source"] == "import:home"
          and e.store.journal_entries()[-1]["source"] == "compile", rec["source"])

with tempfile.TemporaryDirectory() as d:
    e = Env(d); e.migrate()
    noted = co.store_unavailable(e.text, e.home)
    os.rename(e.vault, e.vault + "-away")
    gone = co.store_unavailable(e.text, e.home)
    check("the last store is noted and an unmounted vault is reported", noted is None
          and gone == e.store.root, (noted, gone))

# --- v3.12 final review fixes
def no_final_newline(d):
    e = Env(d)
    e.text = e.text.rstrip("\n")
    for path in (e.ctx, e.mirror):
        open(path, "w", encoding="utf-8", newline="").write(e.text)
    e.migrate()
    return e


with tempfile.TemporaryDirectory() as d:
    e = no_final_newline(d)
    co.archive(e.store, e.copies, e.home, "setting.custom-sections", "", NOW)
    open(e.ctx, "a", encoding="utf-8").write("\n## Zorg Extra\n\n- one\n")
    e.sync()
    co.restore_record(e.store, e.copies, e.home, "setting.custom-sections", NOW)
    glued = "_none_## Zorg Extra" in read(e.ctx)
    e.edit(e.ctx, "- **Cadence:** daily", "- **Cadence:** weekly")
    res = e.sync()
    check("a restored record never glues onto the next heading", not glued and res["removed"] == []
          and "custom.zorg-extra" in [r["id"] for r in e.store.load()], (glued, res["removed"]))

with tempfile.TemporaryDirectory() as d:
    e = Env(d); e.migrate()
    for rid in ("product.zorg-lite", "team.alpha-a", "team.beta-b", "product.zorg-app"):
        co.archive(e.store, e.copies, e.home, rid, "", NOW)
    co.restore_record(e.store, e.copies, e.home, "product.zorg-lite", NOW)
    t = read(e.ctx)
    inside = t.index("## Organization: Zorg") < t.index("### Product: Zorg Lite") < t.index("## CJM Configuration")
    e.edit(e.ctx, "- **Cadence:** daily", "- **Cadence:** weekly")
    res = e.sync()
    rec = {r["id"]: r for r in e.store.load()}.get("product.zorg-lite")
    check("a product restored without its neighbours stays inside its organisation", inside and res["removed"] == []
          and rec is not None and rec["parent"] == "org.zorg", (inside, res["removed"], rec and rec["parent"]))

with tempfile.TemporaryDirectory() as d:
    e = Env(d); e.migrate()
    os.remove(os.path.join(e.store.records_dir, "product.zorg-app.md"))
    e.sync(accept_removals=True)
    co.restore_record(e.store, e.copies, e.home, "product.zorg-app", NOW)
    rec = {r["id"]: r for r in e.store.load()}["product.zorg-app"]
    check("a record restored from the trash gets its organisation back", rec["parent"] == "org.zorg", rec["parent"])

with tempfile.TemporaryDirectory() as d:
    e = Env(d); e.migrate()
    arch = os.path.join(e.store.root, "archive", "2026", "setting.templates.md")
    res = co.archive(e.store, e.copies, e.home, "setting.templates", "", NOW)
    co.restore(res["snapshot"], e.store, e.copies)
    undone_archive = not os.path.exists(arch) and "setting.templates" in [r["id"] for r in e.store.load()]
    co.archive(e.store, e.copies, e.home, "setting.templates", "", NOW)
    res = co.restore_record(e.store, e.copies, e.home, "setting.templates", NOW)
    co.restore(res["snapshot"], e.store, e.copies)
    undone_restore = os.path.exists(arch) and "setting.templates" not in [r["id"] for r in e.store.load()]
    check("undo keeps the archive in step", undone_archive and undone_restore, (undone_archive, undone_restore))

with tempfile.TemporaryDirectory() as d:
    e = Env(d); e.migrate()
    shutil.rmtree(e.store.root)
    check("a store removed while the vault is present is 'no store', not 'unavailable'",
          co.store_unavailable(e.text, e.home) is None, co.store_unavailable(e.text, e.home))

print("RESULT:", "GREEN ✅" if not fails else "RED ❌", "(%d failed)" % fails)
sys.exit(1 if fails else 0)
