#!/usr/bin/env python3
"""TC-ctx-3200-bridges — scripts/ctx_bridges.py, bridges in your notes (v3.20.0): `ctx entity apply`.

The fictional Zorg vault of testing/fixtures/entity/ (the plugin folder Notes/, the core ZorgCore/ registered as
zorg-core) is copied to a temp dir and widened there: the plan of the bridges a dry run reports (only a join by an
e-mail or your `same`, never a «maybe»), what it skips and why, the field someone else keeps, the report's code.
Stdlib only; run from the repo root:

  env -u GROW_PM_CONTEXT_PATH -u GROW_PM_PROVIDER_PATHS python3 testing/ctx_bridges_test.py
"""
import hashlib, json, os, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import ctx_index as ci  # noqa: E402
import ctx_search as cs_  # noqa: E402
import ctx_store as cs  # noqa: E402
import ctx_entity as ce  # noqa: E402
try:
    import ctx_bridges as cb_  # noqa: E402
except ImportError:
    cb_ = None

FIX = os.path.join(ROOT, "testing", "fixtures", "entity")
CTX = os.path.join(ROOT, "scripts", "ctx.py")
fails = 0


def check(name, cond, detail=""):
    global fails
    fails += not cond
    print(("✅" if cond else "❌"), name, ("" if cond else "-> " + str(detail)[:900]))


def read(*parts):
    return open(os.path.join(*parts), encoding="utf-8", newline="").read()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8", newline="").write(text)


def tree_hash(top):
    h = hashlib.sha1()
    for dirpath, dirs, names in sorted(os.walk(top)):
        dirs.sort()
        for n in sorted(names):
            p = os.path.join(dirpath, n)
            h.update(os.path.relpath(p, top).encode() + b"\0" + open(p, "rb").read() + b"\0")
    return h.hexdigest()


class Env:
    """A temp home and vault with the entity fixture, {{VAULT}} and {{HOME}} filled in, a store, no local index."""

    def __init__(self, d, extra=None, local=None):
        self.d = d
        self.home = os.path.join(d, "home")
        self.vault = os.path.join(d, "vault")
        os.makedirs(os.path.join(self.home, ".grow-pm"))
        shutil.copytree(os.path.join(FIX, "vault"), self.vault)
        for dirpath, _, names in os.walk(self.vault):
            for n in names:
                p = os.path.join(dirpath, n)
                if n.endswith(".yaml") and "{{VAULT}}" in read(p):
                    write(p, read(p).replace("{{VAULT}}", self.vault))
        for rel, text in (extra or {}).items():
            write(os.path.join(self.vault, rel), text)
        text = read(FIX, "context.md").replace("{{VAULT}}", self.vault).replace("{{HOME}}", self.home)
        if local is None:
            text = text.replace("### Vault Search MCP\n- zorg-brain: scope = own vault, index = %s/zorg-brain.sqlite\n" % self.home, "")
        else:                                       # a local index of the user's: (path, frontmatter) of its notes
            import sqlite3
            con = sqlite3.connect(os.path.join(self.home, "zorg-brain.sqlite"))
            con.execute("CREATE TABLE meta(k TEXT, v TEXT)")
            con.execute("INSERT INTO meta VALUES ('vault_root', ?)", (self.vault,))
            con.execute("CREATE TABLE notes(path TEXT PRIMARY KEY, title TEXT, type TEXT, fm_json TEXT)")
            con.execute("CREATE VIRTUAL TABLE notes_fts USING fts5(path, title, body)")
            for rel, fm in local:
                title = os.path.basename(rel)[:-3]
                con.execute("INSERT INTO notes VALUES (?, ?, ?, ?)", (rel, title, fm.get("type"), json.dumps(fm)))
                con.execute("INSERT INTO notes_fts VALUES (?, ?, ?)", (rel, title, "text"))
            con.commit()
            con.close()
        self.ctx = os.path.join(self.home, ".grow-pm", "local-context.md")
        write(self.ctx, text)
        self.text = text
        self.store = cs.Store(os.path.join(self.vault, "Notes", "_System", "context"))
        rc, out, _ = self.cli("migrate", "--apply")                  # the store: records from local-context.md
        assert rc == 0, out[-400:]

    def sctx(self):
        return cs_.context_for(self.home, read(self.ctx), store_root=self.store.root)

    def plan(self, mem=None, ledger=None, kind=None):
        sctx = self.sctx()
        idx = ci.Index(self.home)
        idx.refresh(sctx["roots"], sctx["store_rel"], sctx["blocks_rels"])
        reg, _ = ce.load(sctx, idx, mem or ce.empty_memory())
        return cb_.bridge_plan(sctx, idx, reg, ledger or cb_.empty_ledger(), mem or ce.empty_memory(), kind=kind)

    def cli(self, *args):
        env = dict(os.environ)
        env.pop("GROW_PM_CONTEXT_PATH", None)
        env.pop("GROW_PM_PROVIDER_PATHS", None)
        p = subprocess.run([sys.executable, CTX] + list(args) + ["--home", self.home, "--context", self.ctx],
                           capture_output=True, text=True, env=env, timeout=120)
        lines = [l for l in p.stdout.splitlines() if l.strip()]
        try:
            res = json.loads(lines[-1][len("CTX_RESULT "):]) if lines and lines[-1].startswith("CTX_RESULT ") else None
        except ValueError:
            res = None
        return p.returncode, p.stdout + p.stderr, res


def rows(plan):
    return {(r["path"], r["target"]) for r in plan["rows"]}


RHEA = ("Notes/People/rhea.md", "ZorgCore/People/rhea-core.md")
CY = ("Notes/People/cy.md", "ZorgCore/People/cy-three.md")

if cb_ is None:
    check("v3.20.0 scripts/ctx_bridges.py exists", False, "no module ctx_bridges")
    print("RESULT: RED ❌")
    sys.exit(1)

with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    p = env.plan()
    check("an e-mail join with no bridge in your note is one bridge to write: Rhea → the core's card",
          rows(p) == {RHEA}, p)
    r = next((r for r in p["rows"] if r["path"] == RHEA[0]), {})
    check("…the line is `same_as` with one link to the card, its title as the label, the key that joined them",
          r.get("line") == 'same_as: "[[ZorgCore/People/rhea-core|Rhea One]]"' and r.get("key") == "e-mail", r)
    check("…a note bridged already (Bea's `home_card`, corroborated by her e-mail) is counted, not written",
          "Notes/People/bea.md" in p["skipped"].get(cb_.BRIDGED, []), p["skipped"])
    check("…a «maybe the same» pair (Cy by name) and an uncorroborated bridge (Dee → Bea) give no bridge",
          not any(x[0] in ("Notes/People/cy.md", "Notes/People/dee.md") for x in rows(p)), p)
    check("…the report has a code of 8 hex digits, the same on a second run",
          len(p["code"]) == 8 and int(p["code"], 16) >= 0 and env.plan()["code"] == p["code"], p["code"])
    check("…no field kept by someone else", p["foreign"] == [], p["foreign"])

    mem = ce.empty_memory()
    ce.answer(mem, CY[0], CY[1], True, "2026-10-26")
    p2 = env.plan(mem=mem)
    check("your `same` joins Cy: a bridge to write, its key «твоє same»",
          CY in rows(p2) and next(r for r in p2["rows"] if r["path"] == CY[0])["key"] == "твоє same", p2)
    check("…and the code changes with the plan", p2["code"] != p["code"], (p["code"], p2["code"]))

    mem3 = ce.empty_memory()
    ce.answer(mem3, RHEA[0], RHEA[1], False, "2026-10-26")
    check("your `not-same` keeps Rhea apart: no bridge", RHEA not in rows(env.plan(mem=mem3)), "")
    check("…a kind asked for keeps only its cards", env.plan(kind="team")["rows"] == [], "")

    before = read(env.vault, RHEA[0])
    write(os.path.join(env.vault, RHEA[0]), before.replace("Leads the payments squad.", "Leads the squad."))
    check("a change to the note changes the code (what the dry run showed is what --apply writes)",
          env.plan()["code"] != p["code"], "")
    write(os.path.join(env.vault, RHEA[0]), before)

with tempfile.TemporaryDirectory() as d:
    zorg = '---\ntype: person\nemail: rhea@zorg.example\nzorg_card: "[[ZorgCore/People/rhea-core]]"\n---\n# Rhea One\n'
    env = Env(d, {"Notes/People/rhea.md": zorg})
    p = env.plan()
    check("a bridge another script keeps under its own name (zorg_card) is a bridge: nothing to write",
          rows(p) == set() and RHEA[0] in p["skipped"].get(cb_.BRIDGED, []), p)

with tempfile.TemporaryDirectory() as d:
    fay = "---\ntype: person\nemail: fay@zorg.example\nsame_as: \"[[ZorgCore/People/fay]]\"\n---\n# Fay\n"
    env = Env(d, {"Notes/People/fay-note.md": fay})
    p = env.plan()
    check("one `same_as` the plugin did not write: the field is someone else's — no bridge anywhere",
          p["rows"] == [] and p["foreign"] == ["Notes/People/fay-note.md"], p)
    led = cb_.empty_ledger()
    led["written"].append(["Notes/People/fay-note.md", "same_as", 'same_as: "[[ZorgCore/People/fay]]"', "2026-10-26"])
    p2 = env.plan(ledger=led)
    check("…the ledger says the plugin wrote it: the field is ours, Rhea's bridge is planned",
          p2["foreign"] == [] and RHEA in rows(p2), p2)
    text = cb_.render(dict(p, command="entity", action="apply"))
    check("…the report says so once, with the count", "поле `same_as` веде хтось інший — пропущено" in text
          and text.count("веде хтось інший") == 1, text)

with tempfile.TemporaryDirectory() as d:
    text_field = "---\ntype: person\nemail: rhea@zorg.example\nSame_As: Rhea One of the core\n---\n# Rhea One\n"
    env = Env(d, {"Notes/People/rhea.md": text_field})
    p = env.plan()
    check("a `same_as` written as text (no link: the index does not see it) in the note itself is someone else's too",
          p["rows"] == [] and p["foreign"] == [RHEA[0]], p)

with tempfile.TemporaryDirectory() as d:
    other = os.path.join(d, "other-core")
    write(os.path.join(other, "People", "ola.md"), "---\ntype: people\nemail: ola@zorg.example\n---\n# Ola\n")
    reg = ("schema: provider-registration/2\nid: other-core\ntitle: Other core\nkind: folder\nauthority: org\n"
           "core_root: %s\nstale_after_days: 30\nstatus: active\n" % other)
    env = Env(d, {"Notes/_System/providers/other-core.yaml": reg,
                  "Notes/People/ola.md": "---\ntype: person\nemail: ola@zorg.example\n---\n# Ola\n"})
    p = env.plan()
    check("a card outside the vault (an @repo path) is no target: Obsidian cannot open such a link",
          "Notes/People/ola.md" in p["skipped"].get(cb_.OUTSIDE, []) and not any(x[0] == "Notes/People/ola.md" for x in rows(p)), p)

with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    env.plan()                                                     # the index built
    path = os.path.join(env.vault, RHEA[0])
    os.chmod(path, 0)
    try:
        p = env.plan()
    finally:
        os.chmod(path, 0o644)
    check("a note that cannot be read (iCloud has not downloaded it) is skipped and said",
          RHEA[0] in p["skipped"].get(cb_.UNREAD, []) and RHEA not in rows(p), p)

with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    vault0, store0 = tree_hash(env.vault), None
    code, out, res = env.cli("entity", "apply")
    check("`ctx entity apply`: exit 0, the report with `запишу 1 міст` and `код звіту:`",
          code == 0 and "запишу 1 міст" in out and "код звіту: " in out and "Notes/People/rhea.md" in out, out)
    check("…CTX_RESULT carries the rows and the code", res and res.get("action") == "apply" and len(res.get("rows", [])) == 1
          and len(res.get("code", "")) == 8, res)
    check("…a dry run writes nothing in the vault, the store included", tree_hash(env.vault) == vault0, "")
    code, out, _ = env.cli("entity", "apply", "--kind", "zorg")
    check("…an unknown --kind is exit 3", code == 3, out)

with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    shutil.rmtree(env.store.root)
    code, out, _ = env.cli("entity", "apply")
    check("no store: exit 3 — undo lives in the store", code == 3, out)

# ------------------------------------------------------------------ Task 3: --apply (plan C1, C6–C8)
def journal(env):
    path = os.path.join(env.store.state_dir, "journal.jsonl")
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()] if os.path.isfile(path) else []


def hashes(top, skip=()):
    out = {}
    for dirpath, dirs, names in os.walk(top):
        for n in names:
            p = os.path.join(dirpath, n)
            rel = os.path.relpath(p, top)
            if not any(rel.startswith(s) for s in skip):
                out[rel] = hashlib.sha1(open(p, "rb").read()).hexdigest() if not os.path.islink(p) else "link"
    return out


STORE_REL = os.path.join("Notes", "_System", "context")
MIRROR_REL = os.path.join("Notes", "_System", "local-context.md")   # the compiled copy every writing ctx run keeps

with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    _, _, res = env.cli("entity", "apply")
    code = res["code"]
    before_all = hashes(env.vault, skip=(STORE_REL, MIRROR_REL))
    rc, out, _ = env.cli("entity", "apply", "--apply")
    check("`--apply` without --code: exit 3, the report first", rc == 3 and "--code" in out, out)
    rc, out, _ = env.cli("entity", "apply", "--apply", "--code", "deadbeef")
    check("…another code: exit 4 «звіт змінився», nothing written",
          rc == 4 and "звіт змінився" in out and hashes(env.vault, skip=(STORE_REL, MIRROR_REL)) == before_all, out)
    rhea0 = read(env.vault, RHEA[0])
    rc, out, res = env.cli("entity", "apply", "--apply", "--code", code)
    rhea1 = read(env.vault, RHEA[0])
    line = 'same_as: "[[ZorgCore/People/rhea-core|Rhea One]]"'
    check("the code of the report: exit 0, `записано 1 міст`", rc == 0 and "записано 1 міст" in out, out)
    check("…Rhea's note gets one line, the last of its frontmatter; every other byte as it was",
          rhea1 == rhea0.replace("updated: 2026-10-10\n---\n", "updated: 2026-10-10\n" + line + "\n---\n", 1)
          and rhea1 != rhea0, rhea1[:300])
    after_all = hashes(env.vault, skip=(STORE_REL, MIRROR_REL))
    check("…no other file of the vault changed, the core's untouched",
          {k for k in after_all if after_all[k] != before_all.get(k)} == {RHEA[0]} and set(after_all) == set(before_all), "")
    led = cb_.load_ledger(env.store)
    check("…the ledger holds the line (path, field, line, day)",
          [x[:3] for x in led["written"]] == [[RHEA[0], "same_as", line]], led)
    j = journal(env)[-1]
    check("…one journal line op entity-apply with the note's hashes before and after, and a snapshot",
          j.get("op") == "entity-apply" and j.get("notes") and j["notes"][0]["path"] == RHEA[0]
          and j["notes"][0]["before"] == hashlib.sha1(rhea0.encode()).hexdigest()
          and j["notes"][0]["after"] == hashlib.sha1(rhea1.encode()).hexdigest() and j["notes"][0]["line"] == line
          and os.path.isdir(j.get("snapshot") or ""), j)
    snap = j["snapshot"]
    man = json.load(open(os.path.join(snap, "manifest.json"), encoding="utf-8"))
    check("…the snapshot holds the note as it was before the write",
          [n["path"] for n in man.get("notes", [])] == [RHEA[0]]
          and open(os.path.join(snap, man["notes"][0]["file"]), encoding="utf-8", newline="").read() == rhea0, man.get("notes"))
    _, out, res = env.cli("entity", "apply")
    check("…a second dry run: nothing to write, Rhea «уже мають міст» (the plugin's own bridge is a bridge)",
          res["rows"] == [] and RHEA[0] in res["skipped"].get(cb_.BRIDGED, []) and res["foreign"] == [], res)
    p = env.plan(ledger=led)
    reg_ok = p["rows"] == []
    sctx = env.sctx()
    idx = ci.Index(env.home)
    reg, _ = ce.load(sctx, idx, ce.empty_memory())
    check("…the registry still joins Rhea's two cards (now by the bridge too)",
          {c["path"] for c in reg.of(RHEA[0])["cards"]} >= set(RHEA) and reg_ok, "")
    rc, out, _ = env.cli("entity", "apply", "--apply", "--code", res["code"])
    check("…--apply with nothing to write: exit 0, «нічого не записано», no journal line",
          rc == 0 and "нічого не записано" in out and journal(env)[-1] == j, out)

with tempfile.TemporaryDirectory() as d:
    pia_core = "---\ntype: people\nemail: pia@zorg.example\n---\n# Pia Core\n"
    pia = "﻿---\r\ntype: person\r\nemail: pia@zorg.example\r\n---\r\n# Pia\r\n\r\nNo newline at the end"
    env = Env(d, {"ZorgCore/People/pia.md": pia_core, "Notes/People/pia.md": pia})
    _, _, res = env.cli("entity", "apply")
    rc, out, _ = env.cli("entity", "apply", "--apply", "--code", res["code"])
    got = open(os.path.join(env.vault, "Notes/People/pia.md"), "rb").read().decode("utf-8")
    check("a BOM, CRLF and no final newline: kept byte for byte, the line in the note's own line ending",
          rc == 0 and got == pia.replace("pia@zorg.example\r\n---", 'pia@zorg.example\r\nsame_as: "[[ZorgCore/People/pia|Pia Core]]"\r\n---'), repr(got[:200]))

with tempfile.TemporaryDirectory() as d:
    outside = os.path.join(d, "outside.md")
    write(outside, "---\ntype: person\nemail: rhea@zorg.example\n---\n# Rhea elsewhere\n")
    env = Env(d)
    os.remove(os.path.join(env.vault, RHEA[0]))
    os.symlink(outside, os.path.join(env.vault, RHEA[0]))
    out0 = read(outside)
    _, _, res = env.cli("entity", "apply")
    rc, out, res2 = env.cli("entity", "apply", "--apply", "--code", res["code"])
    check("a note of your layer that is a symlink is never written (plan C7)",
          read(outside) == out0 and not any(r["path"] == RHEA[0] for r in (res2 or {}).get("written", [])), out)

with tempfile.TemporaryDirectory() as d:
    sub = ("schema: provider-registration/2\nid: sub-core\ntitle: Sub core\nkind: folder\nauthority: team\n"
           "core_root: {{VAULT}}/Notes/SubCore\nstale_after_days: 30\nstatus: active\n")
    kai = "---\ntype: person\nemail: kai@zorg.example\n---\n# Kai\n"
    env = Env(d, {"Notes/_System/providers/sub-core.yaml": sub.replace("{{VAULT}}", os.path.join(d, "vault")),
                  "Notes/SubCore/People/kai.md": kai,
                  "ZorgCore/People/kai.md": "---\ntype: people\nemail: kai@zorg.example\n---\n# Kai Core\n",
                  "Notes/_System/People/sys.md": "---\ntype: person\nemail: rhea@zorg.example\n---\n# Rhea sys\n"})
    _, _, res = env.cli("entity", "apply")
    rc, out, _ = env.cli("entity", "apply", "--apply", "--code", res["code"])
    check("a core registered inside your plugin folder is never written, nor `_System/` (plan C7)",
          read(env.vault, "Notes/SubCore/People/kai.md") == kai
          and "same_as" not in read(env.vault, "Notes/_System/People/sys.md"), out)

    sctx = env.sctx()
    refusal = lambda rel: cb_.write_refusal(sctx, [], env.store.root, env.home, rel)  # noqa: E731
    write(os.path.join(d, "elsewhere.md"), kai)
    os.symlink(os.path.join(d, "elsewhere.md"), os.path.join(env.vault, "Notes/People/linked.md"))
    os.makedirs(os.path.join(d, "real-dir"))
    os.symlink(os.path.join(d, "real-dir"), os.path.join(env.vault, "Notes/Linked"))
    write(os.path.join(d, "real-dir", "x.md"), kai)
    check("plan C7 itself: your note is writable; a core inside the plugin folder, `_System/`, the store, a symlink, a "
          "folder that is a symlink and a note outside the plugin folder are not",
          refusal("Notes/People/rhea.md") is None
          and "sub-core" in (refusal("Notes/SubCore/People/kai.md") or "")
          and refusal("Notes/_System/People/sys.md") == "_System/"
          and refusal("Notes/_System/context/records/x.md") is not None
          and "symlink" in (refusal("Notes/People/linked.md") or "")
          and "symlink" in (refusal("Notes/Linked/x.md") or "")
          and refusal("ZorgCore/People/kai.md") == "не в теці плагіна",
          [refusal(x) for x in ("Notes/People/rhea.md", "Notes/SubCore/People/kai.md", "Notes/_System/People/sys.md",
                                "Notes/_System/context/records/x.md", "Notes/People/linked.md", "Notes/Linked/x.md",
                                "ZorgCore/People/kai.md")])
    fake = {"rows": [{"path": "Notes/SubCore/People/kai.md", "target": "ZorgCore/People/kai.md", "label": "Kai Core",
                      "line": 'same_as: "[[ZorgCore/People/kai|Kai Core]]"', "key": "e-mail", "kind": "person",
                      "entity": "Kai", "sha": hashlib.sha1(kai.encode()).hexdigest()}]}
    done = cb_.apply_plan(sctx, env.store, [], env.home, fake, [], "2026-10-26", lambda notes: None,
                          lambda entry: None, "2026-10-26T10:00:00+03:00")
    rhea_text = read(env.vault, RHEA[0])
    stale = {"rows": [dict(fake["rows"][0], path=RHEA[0], sha="0" * 40)]}
    done2 = cb_.apply_plan(sctx, env.store, [], env.home, stale, [], "2026-10-26", lambda notes: None,
                           lambda entry: None, "2026-10-26T10:00:00+03:00")
    check("…a note whose bytes are not the plan's (changed while writing) is skipped and said, never written",
          done2["written"] == [] and RHEA[0] in done2["skipped"].get(cb_.MOVED, []) and read(env.vault, RHEA[0]) == rhea_text,
          done2)
    check("…apply_plan given a row in a core never writes it, and says why",
          done["written"] == [] and read(env.vault, "Notes/SubCore/People/kai.md") == kai
          and any("sub-core" in k for k in done["skipped"]), done)

with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    _, _, res = env.cli("entity", "apply")
    write(os.path.join(env.vault, "Notes/People/zed.md"),
          '---\ntype: person\nsame_as: "[[ZorgCore/People/fay]]"\n---\n# Zed\n')
    rc, out, _ = env.cli("entity", "apply", "--apply", "--code", res["code"])
    check("a `same_as` someone added between the report and --apply: another code, nothing written",
          rc == 4 and "same_as" not in read(env.vault, RHEA[0]), out)

# ------------------------------------------------------------------ Task 4: `ctx undo` (plan C9, R4)
LINE = 'same_as: "[[ZorgCore/People/rhea-core|Rhea One]]"'


def applied(d, extra=None):
    env = Env(d, extra)
    _, _, res = env.cli("entity", "apply")
    rc, out, _ = env.cli("entity", "apply", "--apply", "--code", res["code"])
    assert rc == 0, out
    return env


with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    rhea0 = read(env.vault, RHEA[0])
    _, _, res = env.cli("entity", "apply")
    env.cli("entity", "apply", "--apply", "--code", res["code"])
    rc, out, res = env.cli("undo")
    check("`ctx undo` after apply: the note as it was, byte for byte, and said",
          rc == 0 and read(env.vault, RHEA[0]) == rhea0 and "повернуто нотаток: 1" in out, out)
    check("…the ledger is back as it was (empty)", cb_.load_ledger(env.store)["written"] == [], "")
    check("…the undo's journal line holds the note it reverted", (journal(env)[-1].get("notes") or [{}])[0].get("path") == RHEA[0],
          journal(env)[-1])
    rc, out, _ = env.cli("undo")
    check("`ctx undo` again (the undo taken back): the bridge is in the note again, the ledger holds it",
          rc == 0 and LINE in read(env.vault, RHEA[0]) and len(cb_.load_ledger(env.store)["written"]) == 1, out)
    rc, out, _ = env.cli("undo")
    check("…and once more: gone again", rc == 0 and read(env.vault, RHEA[0]) == rhea0, out)

with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    rhea0 = read(env.vault, RHEA[0])
    _, _, res = env.cli("entity", "apply")
    env.cli("entity", "apply", "--apply", "--code", res["code"])
    write(os.path.join(env.vault, RHEA[0]), read(env.vault, RHEA[0]) + "\nMy own line after the apply.\n")
    rc, out, _ = env.cli("undo")
    check("a note you changed after apply: undo takes out our line alone, your change stays (R4)",
          rc == 0 and read(env.vault, RHEA[0]) == rhea0 + "\nMy own line after the apply.\n", read(env.vault, RHEA[0]))

with tempfile.TemporaryDirectory() as d:
    env = applied(d)
    edited = read(env.vault, RHEA[0]).replace(LINE, 'same_as: "[[ZorgCore/People/rhea-core|Rhea]]"')
    write(os.path.join(env.vault, RHEA[0]), edited)
    rc, out, _ = env.cli("undo")
    check("our line changed by hand: the note is left as it is, and said «не повернуто»",
          rc == 0 and read(env.vault, RHEA[0]) == edited and "не повернуто: %s" % RHEA[0] in out, out)

with tempfile.TemporaryDirectory() as d:
    env = applied(d)
    env.cli("undo")
    mine = read(env.vault, RHEA[0]).replace("updated: 2026-10-10\n", "updated: 2026-10-10\n" + LINE + "\n") + "\nMine.\n"
    write(os.path.join(env.vault, RHEA[0]), mine)
    rc, out, _ = env.cli("undo")
    check("undo of an undo is a whole-file restore only: a note you changed since (our line typed back by hand) stays",
          rc == 0 and read(env.vault, RHEA[0]) == mine and "не повернуто: %s" % RHEA[0] in out, out)

with tempfile.TemporaryDirectory() as d:
    env = applied(d)
    os.remove(os.path.join(env.vault, RHEA[0]))
    rc, out, _ = env.cli("undo")
    _, _, res_gone = env.cli("entity", "apply")
    check("the note is gone: undo says so and restores the store anyway; the next report is not blocked (final I2: "
          "a gone note's line stays ours — it may live on under another name)",
          rc == 0 and "не повернуто: %s" % RHEA[0] in out and not os.path.exists(os.path.join(env.vault, RHEA[0]))
          and res_gone["foreign"] == [], (out, res_gone.get("foreign")))

with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    rhea0 = read(env.vault, RHEA[0])
    _, _, res = env.cli("entity", "apply")
    env.cli("entity", "apply", "--apply", "--code", res["code"])
    env.cli("entity", "same", CY[0], CY[1])
    rc, out, _ = env.cli("undo", "--steps", "2")
    check("`undo --steps 2` over apply and `entity same`: the note back, the answer gone",
          rc == 0 and read(env.vault, RHEA[0]) == rhea0 and not ce.load_memory(env.store)["same"], out)

with tempfile.TemporaryDirectory() as d:
    env = applied(d)
    core = os.path.join(env.vault, RHEA[1])
    core0 = read(core)
    jpath = os.path.join(env.store.state_dir, "journal.jsonl")
    lines = open(jpath, encoding="utf-8").read().splitlines()
    last = json.loads(lines[-1])
    last["notes"] = [{"path": RHEA[1], "line": "type: people", "before": last["notes"][0]["before"],
                      "after": hashlib.sha1(core0.encode()).hexdigest()}]
    lines[-1] = json.dumps(last, ensure_ascii=False, sort_keys=True)
    open(jpath, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    rc, out, _ = env.cli("undo")
    check("a journal line that names a core's card: undo never writes it (plan C7 in undo too)",
          read(core) == core0 and "не повернуто: %s" % RHEA[1] in out, out)

# ------------------------------------------------------------------ Task 2–3 review (review-v3.20.0-task-2-3.md)
def vault_with(d, extra):
    return Env(d, extra)


with tempfile.TemporaryDirectory() as d:                                       # I1: case and an unparsed registration
    sub = ("schema: provider-registration/2\nid: sub-core\ntitle: Sub core\nkind: folder\nauthority: team\n"
           "core_root: %s\nstale_after_days: 30\nstatus: active\n" % os.path.join(d, "vault", "notes", "subcore"))
    broken = "foo: [unclosed\ncore_root: %s\n" % os.path.join(d, "vault", "Notes", "Broken")
    kai = "---\ntype: person\nemail: kai@zorg.example\n---\n# Kai\n"
    lia = "---\ntype: person\nemail: lia@zorg.example\n---\n# Lia\n"
    env = Env(d, {"Notes/_System/providers/sub-core.yaml": sub, "Notes/_System/providers/broken.yaml": broken,
                  "Notes/SubCore/People/kai.md": kai, "Notes/Broken/People/lia.md": lia,
                  "ZorgCore/People/kai.md": "---\ntype: people\nemail: kai@zorg.example\n---\n# Kai Core\n",
                  "ZorgCore/People/lia.md": "---\ntype: people\nemail: lia@zorg.example\n---\n# Lia Core\n"})
    _, _, res = env.cli("entity", "apply")
    rc, out, _ = env.cli("entity", "apply", "--apply", "--code", res["code"])
    check("review I1: a core registered in another letter case, or by a registration that does not parse, is never "
          "written — nor planned", read(env.vault, "Notes/SubCore/People/kai.md") == kai
          and read(env.vault, "Notes/Broken/People/lia.md") == lia
          and not any(r["path"].startswith(("Notes/SubCore", "Notes/Broken")) for r in res["rows"]), (res["rows"], out))

with tempfile.TemporaryDirectory() as d:                                       # I2: `...` closes a frontmatter
    dots = "---\ntype: person\nemail: rhea@zorg.example\n...\n# Rhea One\n\nIntro.\n\n---\n\nMore.\n"
    env = Env(d, {RHEA[0]: dots})
    _, _, res = env.cli("entity", "apply")
    env.cli("entity", "apply", "--apply", "--code", res["code"])
    got = read(env.vault, RHEA[0])
    _, _, res2 = env.cli("entity", "apply")
    check("review I2: a frontmatter closed by `...` (as the index reads it) gets the line before the `...`, the body "
          "untouched, and the next run sees the bridge", got == dots.replace("\n...\n", "\n" + LINE + "\n...\n", 1)
          and res2["rows"] == [] and RHEA[0] in res2["skipped"].get(cb_.BRIDGED, []), (got, res2))
    t1, t2 = "\ufeff\ufeff--- \na: 1\n...\nbody\n---\nmore\n", "---\na: 1\n--- \r\nbody\n"
    check("…frontmatter() and the index agree: BOMs, an opening `--- `, a close at `...` or `--- `, a body `---` no end",
          t1[cb_.frontmatter(t1)[1]:].split("\n", 1)[1] == ci._frontmatter(t1)[1] == "body\n---\nmore\n"
          and t2[cb_.frontmatter(t2)[1]:].split("\n", 1)[1] == ci._frontmatter(t2)[1] == "body\n"
          and cb_.frontmatter("---\na: 1\n---\t\n") is None, (cb_.frontmatter(t1), ci._frontmatter(t1)))

with tempfile.TemporaryDirectory() as d:                                       # I3: a second same_as key never
    env = applied(d)
    os.rename(os.path.join(env.vault, RHEA[1]), os.path.join(env.vault, "ZorgCore/People/rhea-one.md"))
    _, _, res = env.cli("entity", "apply")
    check("review I3: our `same_as` whose card moved: no second key — skipped and said",
          res["rows"] == [] and RHEA[0] in res["skipped"].get(cb_.HAS_FIELD, []), res)

with tempfile.TemporaryDirectory() as d:                                       # I4: a second vault
    v2 = os.path.join(d, "vault2")
    write(os.path.join(v2, "Notes2", "People", "ola.md"), "---\ntype: person\nemail: ola@zorg.example\n---\n# Ola\n")
    write(os.path.join(v2, "Core2", "People", "ola.md"), "---\ntype: people\nemail: ola@zorg.example\n---\n# Ola Core\n")
    reg2 = ("schema: provider-registration/2\nid: core-two\ntitle: Core two\nkind: folder\nauthority: org\n"
            "core_root: %s\nstale_after_days: 30\nstatus: active\n" % os.path.join(v2, "Core2"))
    env = Env(d, {"Notes/_System/providers/core-two.yaml": reg2})
    text = read(env.ctx).replace("| 1 | %s | Notes | all | auto | never |" % env.vault,
                                 "| 1 | %s | Notes | all | auto | never |\n| 2 | %s | Notes2 | all | auto | never |"
                                 % (env.vault, v2))
    write(env.ctx, text)
    _, _, res = env.cli("entity", "apply")
    rc, out, res2 = env.cli("entity", "apply", "--apply", "--code", res["code"])
    check("review I4: a note of another vault's plugin folder (outside the storage root) is skipped in the report, and "
          "--apply writes the rest: exit 0, not «refused»",
          rc == 0 and LINE in read(env.vault, RHEA[0]) and "same_as" not in read(v2, "Notes2", "People", "ola.md")
          and not any(r["path"].endswith("ola.md") for r in res["rows"]), (rc, out[-400:], res["rows"]))

with tempfile.TemporaryDirectory() as d:                                       # I5: your answers not read
    env = Env(d)
    env.cli("entity", "not-same", RHEA[0], RHEA[1])
    mem_path = os.path.join(env.store.state_dir, "entities.json")
    os.chmod(mem_path, 0)
    try:
        rc, out, res = env.cli("entity", "apply")
        rc2, out2, _ = env.cli("entity", "apply", "--apply", "--code", (res or {}).get("code") or "x")
    finally:
        os.chmod(mem_path, 0o644)
    check("review I5: your answers not read — the report says so and gives no code; --apply writes nothing",
          "записати:" not in out and not (res or {}).get("code") and rc2 != 0 and "same_as" not in read(env.vault, RHEA[0]),
          (out[-300:], out2[-300:]))

with tempfile.TemporaryDirectory() as d:                                       # I6, I7, M5: the write itself
    env = Env(d)
    path = os.path.join(env.vault, RHEA[0])
    os.chmod(path, 0o600)
    ino = os.stat(path).st_ino
    _, _, res = env.cli("entity", "apply")
    env.cli("entity", "apply", "--apply", "--code", res["code"])
    st = os.stat(path)
    check("review I7: the note keeps its mode (0600) and its inode (its extended attributes with it)",
          (st.st_mode & 0o777) == 0o600 and st.st_ino == ino and LINE in read(path), oct(st.st_mode))

    env2 = Env(os.path.join(d, "two"))
    sctx = env2.sctx()
    p2 = env2.plan()
    target = os.path.join(env2.vault, RHEA[0])

    def edit_during_snapshot(notes):
        write(target, read(target) + "\nSaved by Obsidian meanwhile.\n")
        return None
    done = cb_.apply_plan(sctx, env2.store, [], env2.home, p2, [], "2026-10-26", edit_during_snapshot,
                          lambda entry: None, "2026-10-26T10:00:00+03:00")
    check("review I6: a save that lands while the snapshot runs is kept — the note is skipped, never overwritten",
          done["written"] == [] and "Saved by Obsidian meanwhile." in read(target) and LINE not in read(target), done)

    env3 = Env(os.path.join(d, "three"), {"ZorgCore/People/pia.md": "---\ntype: people\nemail: pia@zorg.example\n---\n# Pia Core\n",
                                          "Notes/People/pia.md": "---\ntype: person\nemail: pia@zorg.example\n---\n# Pia\n"})
    p3 = env3.plan()
    lines, calls = [], []
    real = cb_.insert_line

    def second_fails(text, line):
        calls.append(line)
        if len(calls) == 2:
            raise OSError("disk full")
        return real(text, line)
    cb_.insert_line = second_fails
    try:
        cb_.apply_plan(env3.sctx(), env3.store, [], env3.home, p3, [], "2026-10-26", lambda notes: "snap",
                       lambda entry: lines.append(entry), "2026-10-26T10:00:00+03:00")
    except OSError:
        pass
    finally:
        cb_.insert_line = real
    check("review M5: a failure after one note is written: the journal line and the ledger hold that note",
          len(p3["rows"]) == 2 and lines and len(lines[0]["notes"]) == 1
          and len(cb_.load_ledger(env3.store)["written"]) == 1, (p3["rows"], lines))

with tempfile.TemporaryDirectory() as d:                                       # I6: the snapshot's copy itself
    env = Env(d)
    sctx = env.sctx()
    p = env.plan()
    target = os.path.join(env.vault, RHEA[0])
    import ctx_ops as co  # noqa: E402

    def save_during_snapshot(notes):
        before = read(target)
        write(target, before + "\nA save the snapshot caught.\n")
        snap = co.snapshot(env.store, [], env.home, "entity-apply", notes=notes)
        write(target, before)                                          # and undone before the write
        return snap
    done = cb_.apply_plan(sctx, env.store, [], env.home, p, [], "2026-10-26", save_during_snapshot,
                          lambda entry: None, "2026-10-26T10:00:00+03:00")
    check("review I6: a snapshot whose copy of the note is not the plan's bytes: the note is skipped (undo could not "
          "put it back byte for byte)", done["written"] == [] and RHEA[0] in done["skipped"].get(cb_.MOVED, []), done)

with tempfile.TemporaryDirectory() as d:                                       # M7 at the index's level
    env = applied(d)
    low = ("schema: provider-registration/2\nid: zorg-low\ntitle: Low core\nkind: folder\nauthority: personal\n"
           "core_root: %s\nstale_after_days: 30\nstatus: active\n" % os.path.join(env.vault, "LowCore"))
    write(os.path.join(env.vault, "Notes/_System/providers/zorg-low.yaml"), low)
    write(os.path.join(env.vault, "LowCore/People/rhea-low.md"), "---\ntype: people\nemail: rhea@zorg.example\n---\n# Rhea Low\n")
    write(os.path.join(env.vault, RHEA[0]), read(env.vault, RHEA[0]).replace(LINE, 'same_as: "[[LowCore/People/rhea-low|Rhea Low]]"'))
    _, _, res = env.cli("entity", "apply")
    check("review M7: our `same_as` turned by hand to another card of the same entity (a bridge still, no row): the "
          "index sees a target the ledger does not hold — someone else's", RHEA[0] in res["foreign"], res)

with tempfile.TemporaryDirectory() as d:                                       # M6, M7
    env = applied(d)
    env.cli("undo")
    _, _, res = env.cli("entity", "apply")
    check("review M6: after apply and undo the next report plans the bridge again — our line is no one else's",
          res["foreign"] == [] and [r["path"] for r in res["rows"]] == [RHEA[0]], res)
    env2 = applied(os.path.join(d, "two"))
    write(os.path.join(env2.vault, RHEA[0]), read(env2.vault, RHEA[0]).replace(LINE, 'same_as: "[[ZorgCore/People/fay|Fay]]"'))
    _, _, res2 = env2.cli("entity", "apply")
    check("review M7: our `same_as` turned by hand to another card: someone else's now (the ledger's target differs)",
          RHEA[0] in res2["foreign"], res2)

check("review M9: the line takes the ending of the line before the closing one; a label loses control characters",
      cb_.insert_line("---\na: 1\nb: 2\r\n---\n", "x: 1") == "---\na: 1\nb: 2\r\nx: 1\r\n---\n"
      and cb_.insert_line("---\r\na: 1\n---\n", "x: 1") == "---\r\na: 1\nx: 1\n---\n"
      and cb_.bridge_line("P/x.md", "Ann One\u0007") == 'same_as: "[[P/x|AnnOne]]"', "")
check("review M1: the result shows every reason — a note changed while writing too",
      cb_.MOVED in cb_.render({"rows": [], "skipped": {cb_.MOVED: ["a.md"]}}, written=True), "")

with tempfile.TemporaryDirectory() as d:                                       # M10, M11
    env = Env(d)
    rc, out, _ = env.cli("entity", "apply", "--code", "abcd1234")
    check("review M10: `--code` without `--apply` is exit 3", rc == 3, out)
    _, _, res = env.cli("entity", "apply")
    write(os.path.join(env.vault, RHEA[1]), read(env.vault, RHEA[1]).replace("# Rhea One", "# Rhea One-Core"))
    _, _, res2 = env.cli("entity", "apply")
    check("review M11: the code changes when only the line changes (the card's title)", res2["code"] != res["code"],
          (res["code"], res2["code"]))
    write(env.ctx, read(env.ctx).replace("- **Role:** pm", "- **Role:** pm\n- **Team note:** waiting edit"))
    store0 = hashes(env.store.root)
    copy0 = read(env.ctx)
    rc, out, _ = env.cli("entity", "apply", "--apply", "--code", "deadbeef")
    check("review M11: a refused --apply leaves an edit of local-context.md waiting — the store and the copy untouched",
          rc == 4 and hashes(env.store.root) == store0 and read(env.ctx) == copy0, out)
    mem = ce.empty_memory()
    ce.answer(mem, "Notes/People/bea.md", "ZorgCore/People/bea-two.md", False, "2026-10-26")
    p = env.plan(mem=mem)
    check("review M11: a bridge of yours your not-same denies is shown",
          ("Notes/People/bea.md", "ZorgCore/People/bea-two.md") in [tuple(x) for x in p["denied"]], p["denied"])
    low = ("schema: provider-registration/2\nid: zorg-low\ntitle: Low core\nkind: folder\nauthority: personal\n"
           "core_root: %s\nstale_after_days: 30\nstatus: active\n" % os.path.join(env.vault, "LowCore"))
    write(os.path.join(env.vault, "Notes/_System/providers/zorg-low.yaml"), low)
    write(os.path.join(env.vault, "LowCore/People/rhea-low.md"), "---\ntype: people\nemail: rhea@zorg.example\n---\n# Rhea Low\n")
    p = env.plan()
    check("review M11: the strongest card is the target — the org core (rank 1000) over a personal one (100)",
          any(r["path"] == RHEA[0] and r["target"] == RHEA[1] for r in p["rows"]), p["rows"])

# ------------------------------------------------------------------ Task 4–6 review (review-v3.20.0-task-4-6.md)
with tempfile.TemporaryDirectory() as d:                                       # I1: a note undo cannot write
    env = applied(d)
    j_before = journal(env)
    path = os.path.join(env.vault, RHEA[0])
    os.chmod(path, 0o444)
    try:
        rc, out, res = env.cli("undo")
    finally:
        os.chmod(path, 0o644)
    ops = [x.get("op") for x in journal(env)]
    check("review I1: a note undo cannot write — said per note, the journal keeps its history and the undo line, the "
          "ledger keeps our line still in the note", rc == 0 and "не повернуто: %s" % RHEA[0] in out
          and ops[:len(j_before)] == [x.get("op") for x in j_before] and ops[-1] == "undo"
          and [x[0] for x in cb_.load_ledger(env.store)["written"]] == [RHEA[0]], (rc, out[-300:], ops))
    _, _, res = env.cli("entity", "apply")
    check("…and the next report is not blocked by our own line", res["foreign"] == [], res)

with tempfile.TemporaryDirectory() as d:                                       # I2: a note apply cannot write
    env = Env(d, {"ZorgCore/People/pia.md": "---\ntype: people\nemail: pia@zorg.example\n---\n# Pia Core\n",
                  "Notes/People/pia.md": "---\ntype: person\nemail: pia@zorg.example\n---\n# Pia\n"})
    _, _, res = env.cli("entity", "apply")
    os.chmod(os.path.join(env.vault, RHEA[0]), 0o444)
    try:
        rc, out, res2 = env.cli("entity", "apply", "--apply", "--code", res["code"])
    finally:
        os.chmod(os.path.join(env.vault, RHEA[0]), 0o644)
    check("review I2: a note apply cannot write is skipped and said; the rest is written, exit 0",
          rc == 0 and "same_as" in read(env.vault, "Notes/People/pia.md") and "same_as" not in read(env.vault, RHEA[0])
          and cb_.NOT_WRITTEN.split(":")[0] in out, (rc, out[-400:]))

with tempfile.TemporaryDirectory() as d:                                       # I3a: a renamed note
    env = applied(d, {"ZorgCore/People/pia.md": "---\ntype: people\nemail: pia@zorg.example\n---\n# Pia Core\n"})
    os.rename(os.path.join(env.vault, RHEA[0]), os.path.join(env.vault, "Notes/People/rhea-one.md"))
    write(os.path.join(env.vault, "Notes/People/pia.md"), "---\ntype: person\nemail: pia@zorg.example\n---\n# Pia\n")
    _, _, res = env.cli("entity", "apply")
    check("review I3: a note you renamed after apply keeps our line ours — the next report plans the new pair",
          res["foreign"] == [] and [r["path"] for r in res["rows"]] == ["Notes/People/pia.md"], res)

with tempfile.TemporaryDirectory() as d:                                       # I3b: redo, edit, undo
    env = applied(d)
    env.cli("undo")
    env.cli("undo")                                                            # the bridge is back
    write(os.path.join(env.vault, RHEA[0]), read(env.vault, RHEA[0]) + "\nMine.\n")
    rc, out, _ = env.cli("undo")
    _, _, res = env.cli("entity", "apply")
    check("review I3: apply, undo, undo, an edit, undo — our line goes (the redo added it), your edit stays, nothing "
          "blocked later", LINE not in read(env.vault, RHEA[0]) and read(env.vault, RHEA[0]).endswith("\nMine.\n")
          and res["foreign"] == [], (out[-300:], res.get("foreign")))

with tempfile.TemporaryDirectory() as d:                                       # M1: a write that fails rolls back
    env = Env(d)
    path = os.path.join(env.vault, RHEA[0])
    before = read(path)
    real_write = os.write

    class Boom(object):
        pass
    import builtins
    real_open = builtins.open

    def failing_open(p, mode="r", *a, **k):
        f = real_open(p, mode, *a, **k)
        if p == path and "+" in mode:
            orig = f.write
            state = {"n": 0}

            def w(data):
                state["n"] += 1
                if state["n"] == 1:
                    orig(b"#GARBAGE#" + data[:10])               # half a write: other bytes than the note's
                    raise OSError(28, "No space left on device")
                return orig(data)
            f.write = w
        return f
    builtins.open = failing_open
    try:
        cb_.write_note(path, before.replace("---\n# Rhea", "x: 1\n---\n# Rhea"), original=before.encode("utf-8"))
        raised = False
    except OSError:
        raised = True
    finally:
        builtins.open = real_open
    check("review M1: an in-place write that fails half-way puts the note's bytes back, then raises",
          raised and read(path) == before, read(path)[:120])

with tempfile.TemporaryDirectory() as d:                                       # M2: the snapshot's copy
    env = Env(d)
    os.chmod(os.path.join(env.vault, RHEA[0]), 0o600)
    _, _, res = env.cli("entity", "apply")
    env.cli("entity", "apply", "--apply", "--code", res["code"])
    snap = journal(env)[-1]["snapshot"]
    st = os.stat(os.path.join(snap, "notes", "0.md"))
    check("review M2: the snapshot's copy of a note is readable by you alone (0600)", (st.st_mode & 0o777) == 0o600,
          oct(st.st_mode))

with tempfile.TemporaryDirectory() as d:                                       # M4: evicted, yet bridged already
    env = Env(d, {"ZorgCore/People/vic.md": "---\ntype: people\nemail: vic@zorg.example\n---\n# Vic Core\n"},
              local=[("Notes/People/vic.md", {"type": "person", "email": "vic@zorg.example",
                                              "zorg_card": "[[ZorgCore/People/vic]]"})])
    p = env.plan()
    check("review M4: a note iCloud keeps that is bridged already is «уже мають міст», never sent to download",
          "Notes/People/vic.md" in p["skipped"].get(cb_.BRIDGED, []) and "Notes/People/vic.md" not in p["skipped"].get(cb_.EVICTED, []),
          p["skipped"])

with tempfile.TemporaryDirectory() as d:                                       # M6a: one line per note
    env = applied(d)
    write(os.path.join(env.vault, RHEA[0]), read(env.vault, RHEA[0]).replace(LINE + "\n", ""))
    _, _, res = env.cli("entity", "apply")
    env.cli("entity", "apply", "--apply", "--code", res["code"])
    rc, out, _ = env.cli("undo", "--steps", "2")
    check("review M6: one note, two applies, `undo --steps 2`: said once — put back, never «не повернуто» too",
          "повернуто нотаток: 1" in out and "не повернуто" not in out and LINE not in read(env.vault, RHEA[0]), out[-400:])

with tempfile.TemporaryDirectory() as d:                                       # M8: undo's copy check
    env = applied(d)
    j = journal(env)[-1]
    man = json.load(open(os.path.join(j["snapshot"], "manifest.json"), encoding="utf-8"))
    write(os.path.join(j["snapshot"], man["notes"][0]["file"]), "tampered\n")
    rc, out, _ = env.cli("undo")
    check("review M8: a snapshot copy whose sha1 is not `before` is never written back — our line alone goes",
          read(env.vault, RHEA[0]) != "tampered\n" and LINE not in read(env.vault, RHEA[0]), read(env.vault, RHEA[0])[:80])

with tempfile.TemporaryDirectory() as d:                                       # M8: a core's marker
    env = Env(d, {"Notes/Imported/_System/provider-manifest.yaml": "id: imported\n",
                  "Notes/Imported/People/kai.md": "---\ntype: person\nemail: kai@zorg.example\n---\n# Kai\n",
                  "Notes/Cloned/.git/HEAD": "ref: refs/heads/main\n",
                  "Notes/Cloned/People/lia.md": "---\ntype: person\nemail: lia@zorg.example\n---\n# Lia\n"})
    sctx = env.sctx()
    check("review M8: a folder of your plugin folder holding a core's manifest or `.git` is never written",
          "тека ядра" in (cb_.write_refusal(sctx, [], env.store.root, env.home, "Notes/Imported/People/kai.md") or "")
          and "тека ядра" in (cb_.write_refusal(sctx, [], env.store.root, env.home, "Notes/Cloned/People/lia.md") or ""), "")

# ------------------------------------------------------------------ final review (review-v3.20.0-final.md)
with tempfile.TemporaryDirectory() as d:                                       # I1: a same_as in a note iCloud keeps
    env = Env(d, local=[("Notes/People/zed.md", {"type": "person", "email": "zed@zorg.example",
                                                 "same_as": "[[ZorgCore/People/fay|Fay]]"})])
    p = env.plan()
    check("final I1: a `same_as` someone keeps in a note iCloud keeps (your local index gives it) stops every bridge",
          p["rows"] == [] and "Notes/People/zed.md" in p["foreign"], p)

with tempfile.TemporaryDirectory() as d:                                       # I1: notes nobody could read
    env = Env(d)
    real = ci.evicted
    ci.evicted = lambda roots, store_rel, blocks_rels: ["Notes/People/far.md", "Notes/People/away.md"]
    try:
        res = cb_.plan_result(env.sctx(), env.store)
    finally:
        ci.evicted = real
    check("final I1: notes of your layer iCloud keeps and no local index gives — said, no code (their `same_as` "
          "unchecked), `ctx index rebuild --download`", not res["code"] and res.get("blocked")
          and "2" in res["blocked"] and "--download" in res["blocked"], res.get("blocked"))
    env2 = Env(os.path.join(d, "two"), local=[("Partner/x.md", {"type": "note"})])
    ci.evicted = lambda roots, store_rel, blocks_rels: ["Notes/People/far.md"]
    try:
        res2 = cb_.plan_result(env2.sctx(), env2.store)
    finally:
        ci.evicted = real
    check("…with a local index of yours (it gives their frontmatter) — said, the code stays",
          res2["code"] and not res2.get("blocked") and any("iCloud" in n for n in res2["notes"]), res2["notes"])

with tempfile.TemporaryDirectory() as d:                                       # I2: rename, then undo
    env = applied(d, {"ZorgCore/People/pia.md": "---\ntype: people\nemail: pia@zorg.example\n---\n# Pia Core\n"})
    os.rename(os.path.join(env.vault, RHEA[0]), os.path.join(env.vault, "Notes/People/rhea-one.md"))
    env.cli("undo")
    write(os.path.join(env.vault, "Notes/People/pia.md"), "---\ntype: person\nemail: pia@zorg.example\n---\n# Pia\n")
    _, _, res = env.cli("entity", "apply")
    check("final I2: apply, rename, undo — our line stays ours, the new pair is planned",
          res["foreign"] == [] and [r["path"] for r in res["rows"]] == ["Notes/People/pia.md"], res)
    check("…and a note both bridged and someone else's is listed once, as someone else's (final M5)",
          not (set(res["skipped"].get(cb_.BRIDGED, [])) & set(res["foreign"])), res["skipped"])

with tempfile.TemporaryDirectory() as d:                                       # M5: bridged and someone else's
    both = ('---\ntype: person\nemail: rhea@zorg.example\nzorg_card: "[[ZorgCore/People/rhea-core]]"\n'
            'same_as: "[[ZorgCore/People/fay|Fay]]"\n---\n# Rhea One\n')
    p = Env(d, {RHEA[0]: both}).plan()
    check("final M5: a note bridged already that holds someone else's `same_as` is listed once — as someone else's",
          RHEA[0] in p["foreign"] and RHEA[0] not in p["skipped"].get(cb_.BRIDGED, []), p["skipped"])

with tempfile.TemporaryDirectory() as d:                                       # M1: a core inside the plugin folder
    sub = ("schema: provider-registration/2\nid: sub-core\ntitle: Sub core\nkind: folder\nauthority: team\n"
           "core_root: %s\nstale_after_days: 30\nstatus: active\n" % os.path.join(d, "vault", "Notes", "SubCore"))
    env = Env(d, {"Notes/_System/providers/sub-core.yaml": sub,
                  "Notes/SubCore/People/kai.md": "---\ntype: people\nemail: kai@zorg.example\n---\n# Kai Core\n",
                  "Notes/People/kai.md": "---\ntype: person\nemail: kai@zorg.example\n---\n# Kai\n"})
    p = env.plan()
    check("final M1: a registered core inside the plugin folder is a core — its card is a bridge's target",
          ("Notes/People/kai.md", "Notes/SubCore/People/kai.md") in rows(p), p)

with tempfile.TemporaryDirectory() as d:                                       # M2: the store in ~/.grow-pm
    env = Env(d)
    sctx = env.sctx()
    sctx = dict(sctx, text=sctx["text"].replace("| Notes | all | auto |", "| Notes | all | off |"))
    why = cb_.write_refusal(sctx, [], env.store.root, env.home, RHEA[0])
    check("final M2: with the vault's sync off the reason says the store is in ~/.grow-pm, not «інший вейлт»",
          why and "~/.grow-pm" in why and "інший вейлт" not in why, why)

with tempfile.TemporaryDirectory() as d:                                       # M5: the result of --apply
    env = Env(d, {"ZorgCore/People/pia.md": "---\ntype: people\nemail: pia@zorg.example\n---\n# Pia Core\n",
                  "Notes/People/pia.md": "---\ntype: person\nemail: pia@zorg.example\n---\n# Pia\n"})
    _, _, res = env.cli("entity", "apply")
    os.chmod(os.path.join(env.vault, RHEA[0]), 0o444)
    try:
        rc, out, res2 = env.cli("entity", "apply", "--apply", "--code", res["code"])
    finally:
        os.chmod(os.path.join(env.vault, RHEA[0]), 0o644)
    check("final M5: CTX_RESULT `rows` after --apply is what was written", [r["path"] for r in res2["rows"]] ==
          ["Notes/People/pia.md"], res2 and res2.get("rows"))

import ctx as ctx_cli  # noqa: E402
doc = " ".join((ctx_cli.__doc__ or "").split())
check("final M4: ctx's usage text knows `entity apply` and that undo puts notes back; `entity apply --apply` writes",
      "entity apply [--kind K]" in doc and "entity apply --apply --code C" in doc and "the notes `entity apply` wrote" in doc
      and "`entity same|not-same` and `entity apply --apply`) take no store lock" in doc, "")

# ------------------------------------------------------------------ acceptance finding: notes of yours iCloud keeps
with tempfile.TemporaryDirectory() as d:
    env = Env(d, {"ZorgCore/People/vic.md": "---\ntype: people\nemail: vic@zorg.example\n---\n# Vic Core\n",
                  "Notes/People/wen.md": "---\ntype: person\nemail: wen@zorg.example\n---\n# Wen\n"},
              local=[("Notes/People/vic.md", {"type": "person", "email": "vic@zorg.example"}),
                     ("Notes/People/wen-old.md", {"type": "person", "email": "wen@zorg.example"})])
    p = env.plan()
    check("a note of yours only a local index gives (iCloud keeps the file) is no row, and said; a note of yours is "
          "never a bridge's target", not any(r["target"].startswith("Notes/") or r["path"] == "Notes/People/vic.md"
                                              for r in p["rows"])
          and "Notes/People/vic.md" in p["skipped"].get(cb_.EVICTED, [])
          and not any(r["path"] == "Notes/People/wen.md" for r in p["rows"]), p)

# ------------------------------------------------------------------ Task 5: a busy index answers at once (plan C10.4)
import time  # noqa: E402

with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    _, _, res = env.cli("entity", "apply")
    rhea0 = read(env.vault, RHEA[0])
    folder = os.path.join(env.home, ".grow-pm", "index")
    db = next(os.path.join(folder, f) for f in os.listdir(folder) if f.endswith(".sqlite"))
    holder = subprocess.Popen([sys.executable, "-c", "import sqlite3, sys, time\n"
                               "c = sqlite3.connect(sys.argv[1], isolation_level=None)\n"
                               "c.execute('BEGIN EXCLUSIVE')\nprint('held', flush=True)\ntime.sleep(120)", db],
                              stdout=subprocess.PIPE, text=True)
    try:
        holder.stdout.readline()
        t0 = time.monotonic()
        rc, out, _ = env.cli("entity", "Rhea")
        t1 = time.monotonic()
        rc2, out2, _ = env.cli("entity", "apply", "--apply", "--code", res["code"])
        t2 = time.monotonic()
    finally:
        holder.kill()
        holder.wait()
    limit = cs_.OPEN_S + 2.5
    check("v3.20.0 `ctx entity` on a busy index: exit 5 «зайнятий» within OPEN_S + a moment, not ~26 s (C10.4)",
          rc == 5 and "зайнятий" in out and t1 - t0 < limit, (rc, round(t1 - t0, 1), out[:300]))
    check("…`entity apply --apply` on a busy index: exit 5, nothing written, as quickly",
          rc2 == 5 and read(env.vault, RHEA[0]) == rhea0 and t2 - t1 < limit, (rc2, round(t2 - t1, 1), out2[:300]))

print("RESULT: %s" % ("GREEN ✅" if not fails else "RED ❌ (%d)" % fails))
sys.exit(1 if fails else 0)
