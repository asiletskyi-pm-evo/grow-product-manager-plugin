#!/usr/bin/env python3
"""TC-ctx-4000-graph — the graph of the index (since v4.0.0): names, edges and unresolved links, and `ctx graph`.

The fictional Zorg vault of testing/fixtures/graph/ (the plugin folder Notes/ and the core ZorgCore/, registered as
zorg-core) is copied to a temp dir, one note «evicted» by iCloud: every file a link may land on is a name (an evicted
note and a picture too), every link resolved as `ctx search --get` resolves it — a wiki link, an embed, a frontmatter
field, a `same_as` bridge, a Jira key a work card carries —, a name two notes share is an ambiguous link to both, a link
to nothing is unresolved with the notes of the same name as its candidates; a refresh with nothing changed writes no edge,
a changed note re-resolves its own links only, a name gone re-resolves them all; an index of v3.24.0 gets the tables in
place without reading a file again. Then `ctx graph`: hops, directions, kinds, the cap, sensitivity, the time of a
query on a generated vault of 6 500 notes. Stdlib only; run from the repo root:

  env -u GROW_PM_CONTEXT_PATH -u GROW_PM_PROVIDER_PATHS python3 testing/ctx_graph_test.py
"""
import json, os, shutil, sqlite3, subprocess, sys, tempfile, time, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import ctx_index as ci  # noqa: E402
import ctx_search as cs_  # noqa: E402
import ctx_entity as ce  # noqa: E402
try:
    import ctx_graph as cg  # noqa: E402
except ImportError:
    cg = None

FIX = os.path.join(ROOT, "testing", "fixtures", "graph")
CTX = os.path.join(ROOT, "scripts", "ctx.py")
fails = 0


def check(name, cond, detail=""):
    global fails
    fails += not cond
    print(("✅" if cond else "❌"), name, ("" if cond else "-> " + str(detail)[:700]))


def read(*parts):
    return open(os.path.join(*parts), encoding="utf-8", newline="").read()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8", newline="").write(text)


EVICTED = "Evicted note.md"
STANDUP, STANDUP2 = "Notes/Meetings/Standup 2026-10-01.md", "Notes/Meetings/Standup 2026-10-08.md"
BEA_OWN, BEA_CORE = "Notes/People/bea.md", "ZorgCore/People/bea.md"
ALPHA, WORK_CORE = "ZorgCore/Teams/team-alpha.md", "ZorgCore/Work/PROJ-1234.md"
EPIC, ROADMAP, ORPHAN = "Notes/Epics/Epic — PROJ-1234.md", "Notes/Roadmap.md", "Notes/Orphan.md"
EVICT, PICTURE = "Notes/Evicted note.md", "Notes/Assets/diagram.png"


class Env:
    """A temp home and vault: the graph fixture, {{VAULT}} filled in, one note evicted (ci.is_dataless replaced)."""

    def __init__(self, d, evicted=True):
        self.home = os.path.join(d, "home")
        self.vault = os.path.join(d, "vault")
        os.makedirs(os.path.join(self.home, ".grow-pm"))
        shutil.copytree(os.path.join(FIX, "vault"), self.vault)
        reg = os.path.join(self.vault, "Notes", "_System", "providers", "zorg-core.yaml")
        write(reg, read(reg).replace("{{VAULT}}", self.vault))
        self.text = read(FIX, "context.md").replace("{{VAULT}}", self.vault)
        self.ctx = os.path.join(self.home, ".grow-pm", "local-context.md")
        write(self.ctx, self.text)
        self.evicted = evicted
        self.sctx = cs_.context_for(self.home, self.text)
        self.idx = ci.Index(self.home)
        self.db = os.path.join(self.home, ".grow-pm", "index", "sections.sqlite")

    def refresh(self):
        real = ci.is_dataless
        if self.evicted:
            ci.is_dataless = lambda p: unicodedata.normalize("NFC", p).endswith(EVICTED)
        try:
            return self.idx.refresh(self.sctx["roots"], self.sctx["store_rel"], self.sctx["blocks_rels"])
        finally:
            ci.is_dataless = real

    def q(self, sql, args=()):
        con = sqlite3.connect(self.db)
        try:
            return con.execute(sql, args).fetchall()
        finally:
            con.close()

    def edges(self):
        """{(src path, dst path, kind, ambiguous)}."""
        return {(s, d, k, bool(a)) for s, d, k, a in self.q(
            "SELECT n.path, e.dst, e.kind, e.ambiguous FROM edges e JOIN notes n ON n.id = e.src_id")}

    def unresolved(self):
        return {(s, t): json.loads(c or "[]") for s, t, c in self.q(
            "SELECT n.path, u.target, u.candidates_json FROM unresolved u JOIN notes n ON n.id = u.src_id")}

    def why(self):
        return {(s, t): w for s, t, w in self.q(
            "SELECT n.path, u.target, u.why FROM unresolved u JOIN notes n ON n.id = u.src_id")}

    def note(self, rel):
        return os.path.join(self.vault, *rel.split("/"))

    def cli(self, *args):
        env = dict(os.environ)
        env.pop("GROW_PM_CONTEXT_PATH", None)
        env.pop("GROW_PM_PROVIDER_PATHS", None)
        p = subprocess.run([sys.executable, CTX] + list(args) + ["--home", self.home, "--context", self.ctx],
                           capture_output=True, text=True, env=env, timeout=180)
        lines = [l for l in p.stdout.splitlines() if l.strip()]
        try:
            res = json.loads(lines[-1][len("CTX_RESULT "):]) if lines and lines[-1].startswith("CTX_RESULT ") else None
        except ValueError:
            res = None
        return p.returncode, p.stdout + p.stderr, res


if cg is None:
    check("v4.0.0 scripts/ctx_graph.py exists", False, "no module ctx_graph")
    print("RESULT: RED ❌")
    sys.exit(1)

# ---------------------------------------------------------------- 1. names, edges, unresolved
with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    env.refresh()
    names = {p: (bool(dl), bool(md)) for p, dl, md in env.q("SELECT path, dataless, md FROM names")}
    check("v4.0.0 names: every file a link may land on — the notes of your layer and of the core, the evicted note "
          "(dataless), a picture (not .md)", {STANDUP, BEA_OWN, BEA_CORE, ALPHA, EVICT, PICTURE} <= set(names)
          and names[EVICT] == (True, True) and names[PICTURE] == (False, False) and names[STANDUP] == (False, True),
          sorted(names))
    check("…the evicted note has no row in notes (it is never opened), its name has one",
          not env.q("SELECT 1 FROM notes WHERE path = ?", (EVICT,)) and EVICT in names)
    check("…a registration under _System/providers/ is no name (the index never enters that folder)",
          not any("providers" in p for p in names), sorted(names))
    e = env.edges()
    check("v4.0.0 edges: a wiki link of the text → the core's team card (wikilink)", (STANDUP, ALPHA, "wikilink", False) in e, sorted(e))
    check("…a link to the evicted note resolves (it is a name): no dead link", (STANDUP, EVICT, "wikilink", False) in e, sorted(e))
    check("…a name two notes share — `[[bea]]` in `participants` — is an ambiguous edge to both, kind fm:participants",
          {(STANDUP, BEA_OWN, "fm:participants", True), (STANDUP, BEA_CORE, "fm:participants", True)} <= e, sorted(e))
    check("…a Jira key a work card carries is a mention edge to every work card of that key",
          {(STANDUP, EPIC, "mention", False), (STANDUP, WORK_CORE, "mention", False),
           (STANDUP2, EPIC, "mention", False)} <= e, sorted(e))
    check("…an embed of a picture is an embed edge", (ROADMAP, PICTURE, "embed", False) in e, sorted(e))
    check("…a frontmatter field with one link is fm:<field>", (EPIC, ALPHA, "fm:team", False) in e, sorted(e))
    check("…`same_as` is its own kind (a bridge of v3.20.0)", (BEA_OWN, BEA_CORE, "same_as", False) in e, sorted(e))
    check("…a link to itself is no edge, a link inside a code block neither",
          not any(s == d_ for s, d_, _, _ in e) and not any("code" in d_ for _, d_, _, _ in e), sorted(e))
    check("…a MOC's list links to the three meetings",
          {("Notes/_MOC/Meetings MOC.md", p, "wikilink", False) for p in
           (STANDUP, STANDUP2, "Notes/Meetings/Pricing review.md")} <= e, sorted(e))
    check("…the orphan has no edge either way", not any(ORPHAN in (s, d_) for s, d_, _, _ in e))
    u = env.unresolved()
    check("v4.0.0 unresolved: a link to nothing has no candidate", u.get((STANDUP, "Nowhere at all")) == [], u)
    check("…a link to a path that is not there has the one note of its name as its candidate (fixable)",
          u.get((STANDUP, "Notes/Old/Roadmap")) == [ROADMAP], u)
    check("…an ambiguous link is unresolved too, with both candidates", u.get((STANDUP, "bea")) == sorted([BEA_CORE, BEA_OWN]), u)
    w = env.why()
    check("…each says why: dead or ambiguous", w.get((STANDUP, "bea")) == "ambiguous"
          and w.get((STANDUP, "Nowhere at all")) == "dead" and w.get((STANDUP, "Notes/Old/Roadmap")) == "dead", w)
    check("…the meta says which rules built the edges", env.q("SELECT value FROM meta WHERE key='graph_version'")
          == [(str(cg.GRAPH_VERSION),)])

    rid = env.q("SELECT id FROM notes WHERE path = ?", (ROADMAP,))[0][0]

    def mark():                                      # a row no build writes: only a build of everything removes it
        con = sqlite3.connect(env.db)
        con.execute("INSERT INTO edges(src_id, dst, kind, field, anchor, ambiguous) VALUES (?, 'MARK', 'mark', '', '', 0)",
                    (rid,))
        con.commit()
        con.close()

    def marked():
        return bool(env.q("SELECT 1 FROM edges WHERE kind = 'mark'"))

    mark()
    before = env.q("SELECT rowid, src_id, dst, kind FROM edges ORDER BY rowid")
    built = env.q("SELECT value FROM meta WHERE key='graph_built'")
    res = env.refresh()
    check("v4.0.0 a refresh with nothing changed writes no edge: the same rows, the same `graph_built`",
          env.q("SELECT rowid, src_id, dst, kind FROM edges ORDER BY rowid") == before
          and env.q("SELECT value FROM meta WHERE key='graph_built'") == built and res["changed"] == 0 and marked(), res)

    write(env.note(STANDUP2), read(env.note(STANDUP2)).replace("still open.", "still open. Ask [[Orphan]]."))
    time.sleep(0.01)
    os.utime(env.note(STANDUP2), (time.time() + 5, time.time() + 5))
    keep = {r for r in env.q("SELECT e.rowid, e.src_id, e.dst, e.kind FROM edges e JOIN notes n ON n.id = e.src_id "
                             "WHERE n.path != ?", (STANDUP2,))}
    env.refresh()
    check("v4.0.0 a changed note re-resolves its own links only: its new edge is there, every other row untouched",
          (STANDUP2, ORPHAN, "wikilink", False) in env.edges()
          and keep <= set(env.q("SELECT rowid, src_id, dst, kind FROM edges")) and marked(), sorted(env.edges()))

    os.remove(env.note(ORPHAN))
    env.refresh()
    check("v4.0.0 a name gone: the links that name it are resolved again — unresolved now —, the other notes' rows "
          "untouched (review I-5: no build of everything)",
          (STANDUP2, ORPHAN, "wikilink", False) not in env.edges() and (STANDUP2, "Orphan") in env.unresolved()
          and ORPHAN not in {p for p, in env.q("SELECT path FROM names")} and marked(), env.unresolved())

    os.remove(env.note(PICTURE))
    env.refresh()
    check("…a file that is not .md gone: its name goes too, the embed is unresolved",
          PICTURE not in {p for p, in env.q("SELECT path FROM names")} and (ROADMAP, "diagram.png") in env.unresolved(),
          env.unresolved())

with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    env.refresh()
    con = sqlite3.connect(env.db)                    # an index of v3.24.0: no names, edges or unresolved, no graph meta
    con.executescript("DROP TABLE names; DROP TABLE edges; DROP TABLE unresolved; DROP TABLE graph_src; "
                      "DELETE FROM meta WHERE key IN ('graph_version', 'graph_built', 'graph_work');")
    con.commit()
    con.close()
    res = env.refresh()
    check("v4.0.0 an index of v3.24.0 gets the tables in place, filled — no file read again, nothing rebuilt",
          res["changed"] == 0 and res["added"] == 0 and not res["rebuilt"]
          and (STANDUP, ALPHA, "wikilink", False) in env.edges() and env.q("SELECT count(*) FROM names")[0][0] > 10, res)

with tempfile.TemporaryDirectory() as d:               # review of tasks 1–3: the hazards it reproduced
    env = Env(d)
    env.refresh()
    con = sqlite3.connect(env.db)                    # the graph of an earlier rule set: a table of another shape
    con.executescript("DROP TABLE unresolved; CREATE TABLE unresolved(src_id INTEGER, target TEXT, field TEXT, "
                      "candidates_json TEXT); UPDATE meta SET value = '1' WHERE key = 'graph_version';")
    con.commit()
    con.close()
    res = env.refresh()
    check("v4.0.0 review: graph tables of other rules are made anew — the section index is never set aside for them",
          not res["rebuilt"] and not os.path.exists(env.db + ".broken") and (STANDUP, "bea") in env.unresolved(), res)
    real_build = cg.build

    def broken(*a, **k):
        raise sqlite3.OperationalError("too many SQL variables")

    cg.build = broken
    try:
        write(env.note(STANDUP2), read(env.note(STANDUP2)) + "\nSee [[Roadmap]].\n")
        os.utime(env.note(STANDUP2), (time.time() + 9, time.time() + 9))
        res = env.refresh()
    finally:
        cg.build = real_build
    check("…a fault of the graph build costs the graph alone: the index is kept, the rules' version dropped",
          not res["rebuilt"] and res["changed"] == 1 and not env.q("SELECT 1 FROM meta WHERE key = 'graph_version'"), res)
    env.refresh()
    check("…and the next refresh builds the graph again, the new link in it",
          (STANDUP2, ROADMAP, "wikilink", False) in env.edges(), sorted(env.edges()))
    cg.build = lambda *a, **k: 0                     # an older build sharing the index: it reads a note, no edges
    try:
        write(env.note(STANDUP2), read(env.note(STANDUP2)) + "\nAnd [[Epic — PROJ-1234]].\n")
        os.utime(env.note(STANDUP2), (time.time() + 19, time.time() + 19))
        env.refresh()
    finally:
        cg.build = real_build
    env.refresh()
    check("v4.0.0 review I-2: a note an older build read again (its hash not the one its edges came from) is resolved "
          "again", (STANDUP2, EPIC, "wikilink", False) in env.edges(), sorted(e for e in env.edges() if e[0] == STANDUP2))
    p = env.note("ZorgCore/Work/PROJ-1234.md")
    write(p, read(p).replace("type: epic\njira: PROJ-1234\n", "type: page\n"))
    os.utime(p, (time.time() + 29, time.time() + 29))
    env.refresh()
    check("v4.0.0 review I-1: a work card that is one no more takes its mention edges with it",
          not any(d_ == WORK_CORE and k == "mention" for _, d_, k, _ in env.edges()) and (STANDUP, EPIC, "mention", False)
          in env.edges(), sorted(e for e in env.edges() if e[2] == "mention"))
    write(os.path.join(env.vault, "Notes", ".git", "index"), "git")
    write(os.path.join(env.vault, "Notes", ".git", "refs", "heads", "main"), "abc")
    write(env.note("Notes/LICENSE"), "MIT")
    write(env.note("Notes/License.md"), "# License\n")
    write(env.note("Notes/Index.md"), "# Index\n\n[[License]] · [[main]] · [[LICENSE]]\n")
    env.refresh()
    names = {p_ for p_, in env.q("SELECT path FROM names")}
    e = env.edges()
    check("v4.0.0 review I-3: a dot-folder is no name; a file without .md answers only its whole name",
          not any("/.git/" in p_ for p_ in names) and "Notes/LICENSE" in names
          and ("Notes/Index.md", "Notes/License.md", "wikilink", False) in e
          and ("Notes/Index.md", "main") in env.unresolved(), (sorted(x for x in e if x[0] == "Notes/Index.md"),
                                                              env.unresolved()))

check("v4.0.0 the link resolver is one class: ctx_entity.Resolver is ctx_graph.Resolver", ce.Resolver is cg.Resolver)
r = cg.Resolver({"Notes/a.md": "a", "Notes/Assets/p.png": "p.png", "Notes/v1.2.md": "v1.2"}, ["Notes"])
check("…a path to a file that is not .md resolves as written, a note named like one with a dot still as a note",
      r.resolve("Notes/Assets/p.png") == "Notes/Assets/p.png" and r.resolve("Assets/p.png") == "Notes/Assets/p.png"
      and r.resolve("v1.2") == "Notes/v1.2.md", (r.resolve("Notes/Assets/p.png"), r.resolve("Assets/p.png")))

# ---------------------------------------------------------------- 2. `ctx graph`
with tempfile.TemporaryDirectory() as d:
    env = Env(d, evicted=False)
    rc, out, res = env.cli("graph", "Notes/Meetings/Standup 2026-10-01.md", "--json")
    nodes = {n["path"]: n for n in (res or {}).get("nodes", [])}
    check("v4.0.0 `ctx graph <path>`: hop 1 — the notes it links to (→) and that link to it (←), with the kinds",
          rc == 0 and res["how"] == "path" and nodes.get(ALPHA, {}).get("dirs") == ["→"]
          and nodes[ALPHA]["kinds"] == ["wikilink"] and nodes.get("Notes/_MOC/Meetings MOC.md", {}).get("dirs") == ["←"]
          and nodes.get(WORK_CORE, {}).get("kinds") == ["mention"] and all(n["hop"] == 1 for n in nodes.values()),
          (rc, out[-800:]))
    check("…an ambiguous link's targets are marked so; a person card is sensitive (title and path only)",
          nodes.get(BEA_CORE, {}).get("ambiguous") is True and nodes[BEA_CORE]["sensitive"] is True
          and set(nodes[BEA_CORE]) == {"path", "title", "source", "type", "hop", "dirs", "kinds", "via", "ambiguous",
                                       "sensitive", "dataless"}, nodes.get(BEA_CORE))
    check("…`elapsed_ms` is the query alone", isinstance(res.get("elapsed_ms"), (int, float)), res)
    rc, out, res = env.cli("graph", "Notes/Meetings/Standup 2026-10-01.md", "--depth", "2", "--json")
    hop2 = {n["path"]: n for n in res["nodes"] if n["hop"] == 2}
    check("v4.0.0 --depth 2: the notes two hops away, each with the hop-1 node it is joined through, none twice",
          rc == 0 and STANDUP2 in hop2 and hop2[STANDUP2]["via"] and len({n["path"] for n in res["nodes"]}) == len(res["nodes"])
          and STANDUP not in {n["path"] for n in res["nodes"]}, sorted(hop2))
    rc, out, res = env.cli("graph", "Notes/Meetings/Standup 2026-10-01.md", "--kind", "mention", "--json")
    check("v4.0.0 --kind keeps those kinds alone", rc == 0 and {tuple(n["kinds"]) for n in res["nodes"]} == {("mention",)},
          [(n["path"], n["kinds"]) for n in res["nodes"]])
    rc, out, res = env.cli("graph", "Notes/Epics/Epic — PROJ-1234.md", "--kind", "fm", "--json")
    check("…`fm` takes every frontmatter field", rc == 0 and [n["kinds"] for n in res["nodes"]] == [["fm:team"]],
          [(n["path"], n["kinds"]) for n in res["nodes"]])
    rc, out, res = env.cli("graph", "--kind", "links", "Roadmap")
    check("…an unknown kind is a usage error (exit 3)", rc == 3 and "--kind takes" in out, out[-300:])
    rc, out, res = env.cli("graph", "ZorgCore/Teams/team-alpha.md", "--depth", "2", "--json")
    bea = {n["path"]: n for n in res["nodes"]}.get(BEA_CORE, {})
    check("v4.0.0 review I-4: a sensitive node — no type, its edge kind without the field (fm, never fm:team) — and the "
          "walk never goes on through it", rc == 0 and bea.get("sensitive") and bea.get("type") == ""
          and "fm" in bea.get("kinds", []) and not any(k.startswith("fm:") for k in bea.get("kinds", []))
          and not any(BEA_CORE in n["via"] for n in res["nodes"] if n["hop"] == 2),
          (bea, [(n["path"], n["via"]) for n in res["nodes"] if n["hop"] == 2]))
    rc, out, res = env.cli("graph", BEA_CORE, "--json")
    check("v4.0.0 review I-6 (tasks 4–6): a sensitive start shows who links to it, never what its own text links",
          rc == 0 and res["nodes"] and all(n["dirs"] == ["←"] for n in res["nodes"]),
          [(n["path"], n["dirs"]) for n in (res or {}).get("nodes", [])])
    rc, out, res = env.cli("graph", "diagram.png", "--json")
    check("v4.0.0 review M-9: a name alone (a picture) is a start too", rc == 0 and res["how"] == "path"
          and [n["path"] for n in res["nodes"]] == [ROADMAP], res and res.get("nodes"))
    rc, out, res = env.cli("graph", "bea@zorg.example", "--json")
    check("v4.0.0 an entity request (an e-mail) starts from all its cards", rc == 0 and res["how"] == "entity"
          and {s_["path"] for s_ in res["start"]} == {BEA_OWN, BEA_CORE}, res and res.get("start"))
    rc, out, res = env.cli("graph", "bea")
    check("v4.0.0 a name two notes share: exit 3 with both paths to choose from",
          rc == 3 and BEA_OWN in out and BEA_CORE in out and "кілька збігів" in out, out[-400:])
    rc, out, res = env.cli("graph", "no such thing anywhere")
    check("…nothing found: exit 3 and what it takes", rc == 3 and "нічого не знайдено" in out, out[-300:])
    rc, out, res = env.cli("graph", "Roadmap")
    check("v4.0.0 the lines: the start, the hops with direction, kind, title and path, the query's time",
          rc == 0 and "граф: Roadmap — Notes/Roadmap.md" in out and "крок 1" in out
          and "→ embed  diagram.png — Notes/Assets/diagram.png" in out and "запит графа:" in out, out[-600:])
    before = {p_: os.stat(os.path.join(dp, p_)).st_mtime for dp, _, fs in os.walk(env.vault) for p_ in fs}
    env.cli("graph", "Roadmap", "--depth", "2")
    after = {p_: os.stat(os.path.join(dp, p_)).st_mtime for dp, _, fs in os.walk(env.vault) for p_ in fs}
    check("…`ctx graph` writes nothing in the vault", before == after)

# a vault of 6 500 notes and ~60 000 edges, straight into the tables: the time of a query of two hops from a hub
with tempfile.TemporaryDirectory() as d:
    db = os.path.join(d, "big.sqlite")
    con = sqlite3.connect(db)
    con.executescript(ci.DDL + ci.ENTITY_DDL + ci.GRAPH_DDL + cg.EDGE_DDL)
    n_notes = 6500
    con.executemany("INSERT INTO notes(id, path, source, title, type, sensitive) VALUES (?, ?, 'own', ?, 'note', 0)",
                    [(i, "Notes/n%05d.md" % i, "n%05d" % i) for i in range(1, n_notes + 1)])
    con.executemany("INSERT INTO names(path, source, dataless, md) VALUES (?, 'own', 0, 1)",
                    [("Notes/n%05d.md" % i,) for i in range(1, n_notes + 1)])
    rows = []
    for i in range(1, n_notes + 1):                  # each note: 9 links on, one to a hub of 100 notes
        for k in range(1, 10):
            rows.append((i, "Notes/n%05d.md" % ((i * 7 + k * 131) % n_notes + 1), "wikilink", "", "", 0))
        rows.append((i, "Notes/n%05d.md" % ((i % 100) + 1), "fm:hub", "hub", "", 0))
    con.executemany("INSERT INTO edges(src_id, dst, kind, field, anchor, ambiguous) VALUES (?, ?, ?, ?, ?, ?)", rows)
    con.commit()
    times = []
    for _ in range(5):
        t0 = time.perf_counter()
        nodes, more = cg.neighbourhood(con, ["Notes/n00001.md"], depth=2)
        times.append((time.perf_counter() - t0) * 1000)
    con.execute("UPDATE notes SET type = 'person' WHERE id = 2")      # a row an older build wrote: no sensitive flag
    con.execute("UPDATE notes SET title = '1-1 Bea' WHERE id = 3")
    about = cg._about(con, ["Notes/n00002.md", "Notes/n00003.md", "Notes/n00004.md"])
    con.close()
    check("…a people type or a 1-1 note is sensitive even when its row says not (an older build's row)",
          about["Notes/n00002.md"]["sensitive"] and about["Notes/n00003.md"]["sensitive"]
          and not about["Notes/n00004.md"]["sensitive"], about)
    times.sort()
    check("v4.0.0 a query of two hops from a hub on %d notes and %d edges takes < 300 ms (median %.0f ms), at most %d "
          "nodes a hop with the rest counted" % (n_notes, len(rows), times[2], cg.LIMIT),
          times[2] < 300 and len([n for n in nodes if n["hop"] == 2]) == cg.LIMIT and more.get(2, 0) > 0, (times, more))

print("RESULT:", "GREEN ✅ — 0 failure(s)" if not fails else "RED ❌ — %d failure(s)" % fails)
sys.exit(1 if fails else 0)
