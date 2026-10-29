#!/usr/bin/env python3
"""TC-ctx-3240-copy — scripts/ctx_copy.py, the core of the plugin's own copy of an MCP-only repository (since v3.24.0).

What a pass is made of, without the command: which server paths the copy takes (`rel_of`: the root, `.md` only, no
absolute path, no `..`, no control character, no hidden part, not the registration's writable globs; two spellings of
one name on APFS — `fold`); the frontmatter it writes without PyYAML (`dump_frontmatter` / `render`), read back the same
by the three readers of the plugin (`ctx_index`, `provider_bundle.fget`, `ctx_common.read_yaml_subset`) from
testing/fixtures/copy/frontmatter-forms.json; the server hash (prom_sync's formula); the decision for one note — same,
new, updated, kept, conflict — and `failed` for one that does not arrive, against the fake server (testing/mcp_fake.py,
127.0.0.1, the fictional Zorg only); and the target guard: someone else's folder, a symbolic link, a folder inside a
registration's — CopyError, nothing written. Semantics: references/context-provider-protocol.md §12.12. Stdlib only.
"""
import datetime, hashlib, json, os, re, shutil, sys, tempfile, time, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "testing"))
os.environ["NO_PROXY"] = "127.0.0.1,localhost"
os.environ["no_proxy"] = "127.0.0.1,localhost"
import ctx_common as cc  # noqa: E402
import ctx_copy as cp  # noqa: E402
import ctx_index as ci  # noqa: E402
import ctx_mcp as cm  # noqa: E402
import provider_bundle as pb  # noqa: E402
from mcp_fake import FakeMcp  # noqa: E402

cm.McpClient.BACKOFF = 0.0
FORMS = json.load(open(os.path.join(ROOT, "testing", "fixtures", "copy", "frontmatter-forms.json"), encoding="utf-8"))
NOW = datetime.datetime(2026, 10, 29, 9, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=2)))
fails = 0


def check(name, cond, detail=""):
    global fails
    fails += not cond
    print(("✅" if cond else "❌"), name, ("" if cond else "-> " + str(detail)[:700]))


def read(p):
    return open(p, encoding="utf-8", newline="").read()


def tree_files(folder):
    out = {}
    for dp, dn, fn in os.walk(folder):
        for f in fn:
            p = os.path.join(dp, f)
            out[os.path.relpath(p, folder)] = os.stat(p).st_mtime_ns
    return out


# ------------------------------------------------------------------ 1. paths
print("— 1. which server paths the copy takes")
ROOTP = "Zorg/"
cases = [
    ("Zorg/Products/Zorg App/Missions/Reviews everywhere.md", "Products/Zorg App/Missions/Reviews everywhere.md"),
    ("Zorg/Teams/Команда Альфа.md", "Teams/Команда Альфа.md"),
    ("Zorg/Dashboard.MD", "Dashboard.MD"),
    ("Other/Dashboard.md", None),                        # outside the root
    ("Zorg/_System/provider-manifest.yaml", None),       # not a note
    ("Zorg/People/photo.png", None),
    ("Zorg//People/x.md", None),                         # an empty part
    ("Zorg/../escape.md", None),
    ("Zorg/People/../../x.md", None),
    ("Zorg/.obsidian/workspace.md", None),               # a hidden part
    ("Zorg/People/.secret.md", None),
    ("Zorg/People/a\x07b.md", None),                     # a control character
    ("Zorg/People/a\nb.md", None),
    ("Zorg/People\\x.md", None),
    ("Zorg//abs.md", None),
    ("Zorg/C:/x.md", None),
    ("Zorg/Now.md", None),                               # the registration's writable layer
    ("Zorg/_personal/diary.md", None),
    (None, None),
    ("", None),
]
for path, want in cases:
    got, why = cp.rel_of(path, ROOTP, ["Now.md", "_personal/"])
    check("rel_of(%r) → %r" % (path, want), got == want and (want is not None or why), (got, why))
nfd = unicodedata.normalize("NFD", "Zorg/Teams/Команда Йота.md")
check("an NFD path is taken as NFC", cp.rel_of(nfd, ROOTP)[0] == unicodedata.normalize("NFC", "Teams/Команда Йота.md"))
check("an empty root takes every note", cp.rel_of("Dashboard.md", "")[0] == "Dashboard.md")
check("two spellings of one name share a key (case, NFC)",
      cp.fold("Teams/Alpha.md") == cp.fold("teams/ALPHA.md") and cp.fold(nfd) == cp.fold("Zorg/Teams/Команда Йота.md"))

# ------------------------------------------------------------------ 2. frontmatter
print("— 2. the frontmatter, read back by the three readers")
fm = dict(FORMS["scalars"])
fm.update(FORMS["lists"])
text = cp.render(fm, "# Body\n\nText.")
check("render: --- frontmatter --- then the text with a final newline",
      text.startswith("---\n") and "\n---\n# Body\n\nText.\n" in text and text.endswith("Text.\n"))
meta, body = ci._frontmatter(text)
check("ctx_index reads the frontmatter (not None) and the body", meta is not None and body.startswith("# Body"), meta)
for k, v in FORMS["scalars"].items():
    want = v if isinstance(v, str) else ("true" if v is True else "false" if v is False else str(v))
    check("ctx_index: %s" % k, (meta or {}).get(k.lower()) == want, ((meta or {}).get(k.lower()), want))
for k, v in FORMS["lists"].items():
    got = (meta or {}).get(k.lower())
    check("ctx_index: list %s" % k, (got or []) == v or (v == [] and got in ([], "")), (got, v))
front, _ = pb.split_fm(text)
for k, v in FORMS["scalars"].items():
    want = v if isinstance(v, str) else ("true" if v is True else "false" if v is False else str(v))
    check("provider_bundle.fget: %s" % k, pb.fget(front, k) == want, (pb.fget(front, k), want))
for k, v in FORMS["lists"].items():                 # one line, the kit's own form: fget never reads the next line
    got = pb.fget(front, k)
    check("provider_bundle.fget: list %s on its own line" % k, got == json.dumps(v, ensure_ascii=False), got)
check("provider_bundle.fget: the aliases a team card gives read back", re.findall(r'"([^"]+)"', pb.fget(front, "aliases"))
      == FORMS["lists"]["aliases"], pb.fget(front, "aliases"))
fn = cp.dump_frontmatter({"head": None, "node": "Growth"})
check("None is written as an empty text, fget never takes the next line", pb.fget(fn, "head") == "" and pb.fget(fn, "node") == "Growth", fn)
scal = cp.dump_frontmatter(FORMS["scalars"])         # read_yaml_subset reads the wrappers' frontmatter: scalars
try:
    sub = cc.read_yaml_subset(scal)
except ValueError as e:
    sub = {"_error": str(e)}
for k, v in FORMS["scalars"].items():
    check("ctx_common.read_yaml_subset: %s" % k, sub.get(k) == v, (sub.get(k), v))
nested = cp.render({"title": "Zorg", "signals": {"mood": "ok", "n": 2}, "mixed": ["a", {"b": 1}], "none": None}, "x")
m2, _ = ci._frontmatter(nested)
check("nested values are JSON flow, the note still reads", m2 is not None and m2.get("title") == "Zorg"
      and "signals: {\"mood\": \"ok\", \"n\": 2}" in nested and '\nnone: ""\n' in nested, nested)
check("no frontmatter → the text alone", cp.render({}, "plain") == "plain\n")
check("a text that opens with a rule keeps the server's frontmatter",
      cp.render({"type": "note"}, "---\nAfter a rule") == "---\ntype: note\n---\n---\nAfter a rule\n")
check("a text with its own frontmatter (and none apart) is written as it is",
      cp.render({}, "---\ntype: note\n---\nBody") == "---\ntype: note\n---\nBody\n")
check("a date, a number and a reserved word in text are quoted (a YAML 1.1 reader would change their type)",
      'updated: "2026-10-28"' in text and 'version: "0.2"' in text and 'word_yes: "yes"' in text
      and 'number_text: "1234"' in text and "count: 12" in text and "flag: true" in text, text)
check("odd keys are quoted", '"a: b": 1' in cp.dump_frontmatter({"a: b": 1}) and "Команда: 1" in cp.dump_frontmatter({"Команда": 1}))

# ------------------------------------------------------------------ 3. hashes
print("— 3. the server hash is prom_sync's")
fmh = {"b": 1, "a": "Команда"}
want = hashlib.sha1((json.dumps(fmh, ensure_ascii=False, sort_keys=True, default=str) + "\n␞\n"
                     + unicodedata.normalize("NFC", "Тіло\n\n").rstrip()).encode("utf-8")).hexdigest()
check("server_hash = sha1(canon_json(fm) + '\\n␞\\n' + NFC(body).rstrip())", cp.server_hash(fmh, "Тіло\n\n") == want)
check("the key order does not change it", cp.server_hash({"a": "Команда", "b": 1}, "Тіло") == want)
check("a change of a value does", cp.server_hash({"a": "Команда", "b": 2}, "Тіло") != want)
check("NFD and NFC bodies hash alike", cp.server_hash({}, unicodedata.normalize("NFD", "Йота")) == cp.server_hash({}, "Йота"))

# ------------------------------------------------------------------ 4. decisions against the fake server
print("— 4. one decision per note")
REPO = {"id": "zorg-growth", "endpoint": {"url": "", "root": "Growth/", "headers_env": ""}, "writable": []}
tmp = tempfile.mkdtemp(prefix="ctx-copy-")
try:
    home = os.path.join(tmp, "home")
    os.makedirs(os.path.join(home, ".grow-pm"))
    tree = {"Growth/Dashboard.md": {"frontmatter": {"type": "dashboard", "tags": ["zorg"]}, "content": "# Zorg dash\n"},
            "Growth/Teams/team-alpha.md": "# Team Alpha\n",
            "Growth/Teams/team-beta.md": "# Team Beta\n",
            "Growth/People/pat-moss.md": {"frontmatter": {"type": "person", "email": "pm@zorg.example"}, "content": "Pat\n"},
            "Growth/Broken.md": "never served"}
    with FakeMcp(tree=tree, broken={"Growth/Broken.md"}) as fake:
        repo = dict(REPO, endpoint=dict(REPO["endpoint"], url=fake.url))
        res = cp.run(home, repo, NOW)
        folder = cp.copy_dir(home, "zorg-growth")
        check("first pass: 4 new, 1 failed, complete", res["counts"]["new"] == 4 and res["counts"]["failed"] == 1
              and res["outcome"] == "complete" and res["failed"] == ["Broken.md"], res)
        check("the copy mirrors the root", read(os.path.join(folder, "Teams", "team-alpha.md")) == "# Team Alpha\n"
              and read(os.path.join(folder, "Dashboard.md")).startswith('---\ntype: dashboard\ntags: ["zorg"]\n---\n'))
        check("a failed note writes nothing", not os.path.exists(os.path.join(folder, "Broken.md")))
        before = tree_files(folder)
        alpha = os.path.join(folder, "Teams", "team-alpha.md")
        beta = os.path.join(folder, "Teams", "team-beta.md")
        with open(alpha, "a", encoding="utf-8") as f:               # changed here only → kept
            f.write("my note\n")
        with open(beta, "a", encoding="utf-8") as f:                # changed here and on the server → conflict
            f.write("mine\n")
        fake.tree["Growth/Teams/team-beta.md"] = "# Team Beta v2\n"
        fake.tree["Growth/People/pat-moss.md"] = {"frontmatter": {"type": "person", "email": "pm@zorg.example"},
                                                  "content": "Pat Moss, PM\n"}                    # server only → updated
        later = NOW + datetime.timedelta(days=1)
        res2 = cp.run(home, repo, later)
        c = res2["counts"]
        check("second pass: same 1 · kept 1 · conflict 1 · updated 1 · failed 1",
              (c["same"], c["kept"], c["conflict"], c["updated"], c["failed"]) == (1, 1, 1, 1, 1), c)
        check("kept: yours stays", read(alpha).endswith("my note\n"))
        check("conflict: yours stays, the server's goes to conflicts/<id>/<day>/",
              read(beta).endswith("mine\n") and read(os.path.join(cp.conflicts_dir(home, "zorg-growth"), "2026-10-30",
                                                                    "Teams", "team-beta.md")) == "# Team Beta v2\n")
        check("updated: the old file is backed up first", res2["backup"] and
              read(os.path.join(res2["backup"], "People", "pat-moss.md")).endswith("Pat\n")
              and read(os.path.join(folder, "People", "pat-moss.md")).endswith("Pat Moss, PM\n"))
        dash_before = before["Dashboard.md"]
        check("same: not written (mtime as it was)", tree_files(folder)["Dashboard.md"] == dash_before)
        res3 = cp.run(home, repo, later + datetime.timedelta(hours=2))
        c3 = res3["counts"]
        check("after a conflict the next pass keeps yours (kept), writes nothing",
              c3["conflict"] == 0 and c3["kept"] == 2 and c3["updated"] == 0 and c3["new"] == 0, c3)
        st = cp.load_state(folder)
        check("the state is context-copy/1 with a row per note", st["schema"] == "context-copy/1"
              and set(st["notes"]) == {"Dashboard.md", "Teams/team-alpha.md", "Teams/team-beta.md", "People/pat-moss.md"})
        check("the service files stay in .ctx-copy/ (no lock left)", os.path.isfile(cp.state_path(folder))
              and not os.path.exists(os.path.join(folder, ".ctx-copy", "lock")))
        # a pass cut after it wrote a file but before its state did: the file is taken as it is (same, not conflict)
        st["notes"].pop("Dashboard.md")
        cp.save_state(folder, st)
        res4 = cp.run(home, repo, later + datetime.timedelta(hours=3))
        check("a file the state lost, equal to the server's, is same (a cut pass resumes)",
              res4["counts"]["same"] == 2 and res4["counts"]["conflict"] == 0, res4["counts"])
        # a server that serves the frontmatter inside the text
        fake.tree["Growth/Whole.md"] = "---\ntype: whole\n---\nBody\n"
        cp.run(home, repo, later + datetime.timedelta(hours=4))
        check("a note served whole is written as it is", read(os.path.join(folder, "Whole.md")) == "---\ntype: whole\n---\nBody\n")
        for name in ("20260901-000000", "20261025-000000", "keep-me"):
            os.makedirs(os.path.join(folder, ".backup", name, "Teams"))
            open(os.path.join(folder, ".backup", name, "Teams", "x.md"), "w").write("old\n")
        cp.run(home, repo, later + datetime.timedelta(hours=4, minutes=30))
        check("backups older than 30 days are pruned, newer ones and other names kept",
              sorted(os.listdir(os.path.join(folder, ".backup"))) == sorted(
                  ["20261025-000000", "keep-me", os.path.basename(res2["backup"])]), os.listdir(os.path.join(folder, ".backup")))
        print("— 4b. what the review found (v3.24.0)")
        t0 = later + datetime.timedelta(hours=6)
        long_name = "Notes/" + "Зорг" * 62 + ".md"                       # 252 characters, legal on APFS
        fake.tree["Growth/" + long_name] = "# long\n"
        open(os.path.join(folder, "Blocked"), "w").write("a file where a folder would go\n")
        fake.tree["Growth/Blocked/x.md"] = "# blocked\n"
        r = cp.run(home, repo, t0)
        check("a long name is written (a short temp name)", os.path.isfile(os.path.join(folder, long_name)), r)
        check("a file error is one failed note, the pass goes on", r["outcome"] == "complete" and "Blocked/x.md" in r["failed"], r)
        del fake.tree["Growth/Blocked/x.md"]
        dash = os.path.join(folder, "Dashboard.md")
        fake.tree["Growth/Dashboard.md"] = {"frontmatter": {"type": "dashboard"}, "content": "# v2\n"}
        open(dash, "w", encoding="utf-8", newline="").write(cp.render({"type": "dashboard"}, "# v2\n"))   # written, state not saved
        r = cp.run(home, repo, t0 + datetime.timedelta(hours=1))
        check("a pass cut after its write: the file equals the server's → same, no conflict",
              "Dashboard.md" not in r["conflicts"] and r["counts"]["conflict"] == 0, r)
        fake.tree["Growth/Dashboard.md"] = {"frontmatter": {"type": "dashboard"}, "content": "# v3\n"}
        r = cp.run(home, repo, t0 + datetime.timedelta(hours=2))
        check("…and the next change on the server updates it", read(dash).endswith("# v3\n") and r["counts"]["updated"] == 1, r)
        mine = os.path.join(folder, "Teams", "team-gamma.md")
        os.makedirs(os.path.dirname(mine), exist_ok=True)
        open(mine, "w", encoding="utf-8").write("MINE\n")
        fake.tree["Growth/Teams/team-gamma.md"] = "# Gamma 1\n"
        r = cp.run(home, repo, t0 + datetime.timedelta(hours=3))
        check("a file the state did not know, unlike the server's: conflict", "Teams/team-gamma.md" in r["conflicts"], r)
        fake.tree["Growth/Teams/team-gamma.md"] = "# Gamma 2\n"
        cp.run(home, repo, t0 + datetime.timedelta(hours=4))
        cp.run(home, repo, t0 + datetime.timedelta(hours=5))
        check("…stays yours when the server changes again", read(mine) == "MINE\n", read(mine))
        alpha_txt = fake.tree.pop("Growth/Teams/team-alpha.md")
        fake.tree["Growth/Teams/Team-Alpha.md"] = alpha_txt             # a rename that changes only the case
        cp.run(home, repo, t0 + datetime.timedelta(days=1))
        cp.run(home, repo, t0 + datetime.timedelta(days=2))
        st = cp.load_state(folder)
        check("a case-only rename moves nothing into .removed/", not os.path.exists(os.path.join(folder, ".removed"))
              and os.path.isfile(os.path.join(folder, "Teams", "Team-Alpha.md")) and "Teams/team-alpha.md" not in st["notes"],
              (os.listdir(os.path.join(folder, "Teams")), sorted(st["notes"])))
        lockp = cp.take_lock(folder)
        open(lockp, "w").write(json.dumps({"pid": os.getpid() + 1, "at": time.time(), "token": "theirs"}))
        cp.release_lock(lockp)
        check("release_lock leaves a lock that is not ours", os.path.isfile(lockp))
        os.unlink(lockp)
        # a dead server
    res5 = cp.run(home, repo, later + datetime.timedelta(hours=5))
    check("a server that does not answer: unreachable, nothing written", res5["outcome"] == "unreachable"
          and sum(res5["counts"].values()) == 0, res5)

    # ------------------------------------------------------------------ 5. the target guard
    print("— 5. the copy writes only into its own folder")
    other = cp.copy_dir(home, "zorg-core")
    os.makedirs(other)
    open(os.path.join(other, "mine.md"), "w").write("someone else's\n")
    try:
        cp.check_folder(home, "zorg-core")
        check("someone else's folder (not empty, no state) is refused", False)
    except cp.CopyError as e:
        check("someone else's folder (not empty, no state) is refused", "not a copy of the plugin" in str(e), e)
    check("…and left as it was", os.listdir(other) == ["mine.md"])
    real = os.path.join(tmp, "elsewhere")
    os.makedirs(real)
    os.symlink(real, cp.copy_dir(home, "zorg-link"))
    for rid, want in (("zorg-link", "symbolic link"), ("../up", "plain name"), ("a/b", "plain name"), ("", "plain name")):
        try:
            cp.check_folder(home, rid)
            check("refused: %r" % rid, False)
        except cp.CopyError as e:
            check("refused: %r (%s)" % (rid, want), want in str(e), e)
    check("…nothing written through the link", os.listdir(real) == [])
    vault_core = os.path.join(home, ".grow-pm", "cores")
    regs = [{"id": "zorg-core", "paths": [vault_core], "core_root": ""}]
    try:
        cp.check_folder(home, "zorg-new", regs)
        check("a folder inside a registration's folder is refused", False)
    except cp.CopyError as e:
        check("a folder inside a registration's folder is refused", "inside the folder of the registration zorg-core" in str(e), e)
    check("…and not created", not os.path.exists(cp.copy_dir(home, "zorg-new")))
    regs2 = [{"id": "zorg-growth", "paths": [], "core_root": cp.copy_dir(home, "zorg-growth"), "core_from": "copy"}]
    check("its own copy as a core folder is no refusal", cp.check_folder(home, "zorg-growth", regs2) == cp.copy_dir(home, "zorg-growth"))
    # a pass refused by the guard writes nothing
    with FakeMcp(tree=tree) as fake:
        repo = dict(REPO, id="zorg-core", endpoint=dict(REPO["endpoint"], url=fake.url))
        try:
            cp.run(home, repo, NOW)
            check("a pass into someone else's folder raises CopyError", False)
        except cp.CopyError:
            check("a pass into someone else's folder raises CopyError", os.listdir(other) == ["mine.md"])
        check("…and never reached the server", fake.methods() == [], fake.methods())
    real_r = os.path.join(tmp, "elsewhere-removed")
    os.makedirs(os.path.join(real_r, "Notes"))
    open(os.path.join(real_r, "Notes", "outside.md"), "w").write("outside\n")
    rem = os.path.join(cp.copy_dir(home, "zorg-growth"), ".removed")
    os.makedirs(rem, exist_ok=True)
    os.symlink(real_r, os.path.join(rem, "2026-11-01"))
    try:
        cp.restore(home, "zorg-growth", "Notes/outside.md", NOW)
        check("restore refuses a linked day folder of .removed/", False)
    except (cp.CopyError, Exception) as e:
        check("restore refuses a linked day folder of .removed/", os.path.isfile(os.path.join(real_r, "Notes", "outside.md")), e)
    try:
        cp.restore(home, "zorg-core", "x.md", NOW)
        check("restore into someone else's folder is a refusal", False)
    except cp.Refused:
        check("restore into someone else's folder is a refusal", True)
    except cp.CopyError as e:
        check("restore into someone else's folder is a refusal", False, e)
    # a state that cannot be read is no fresh start
    open(cp.state_path(cp.copy_dir(home, "zorg-growth")), "w").write("{broken")
    try:
        cp.load_state(cp.copy_dir(home, "zorg-growth"))
        check("an unreadable state raises CopyError", False)
    except cp.CopyError as e:
        check("an unreadable state raises CopyError", "cannot be read" in str(e), e)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("RESULT:", "GREEN ✅" if not fails else "RED ❌", "(%d failed)" % fails)
sys.exit(1 if fails else 0)
