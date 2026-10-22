#!/usr/bin/env python3
"""TC-ctx-3180-entity — scripts/ctx_entity.py, who is who: one registry of people, teams, missions and work (v3.18.0).

The fictional Zorg vault of testing/fixtures/entity/ (the plugin folder Notes/, the core ZorgCore/ registered as zorg-core)
is copied to a temp dir, with a local index of the user's (zorg-brain, the shape seen in the wild) built beside it: the
three keys of a merge — your answer, the e-mail, a bridge by shape —, the pairs that only look alike, the memory of
your answers, a Growth team that is related or the same, a work item with two homes, the link resolver and the order a
request is looked up in. Stdlib only; run from the repo root:

  env -u GROW_PM_CONTEXT_PATH -u GROW_PM_PROVIDER_PATHS python3 testing/ctx_entity_test.py
"""
import json, os, shutil, sqlite3, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import ctx_index as ci  # noqa: E402
import ctx_search as cs_  # noqa: E402
import ctx_store as cs  # noqa: E402
try:
    import ctx_entity as ce  # noqa: E402
except ImportError:
    ce = None

FIX = os.path.join(ROOT, "testing", "fixtures", "entity")
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


LOCAL_NOTES = (   # path, type, frontmatter — the user's own local index holds Growth, which the plugin's index does not
    ("Growth/People/bea-g.md", "person", {"type": "person", "email": "bea.two@zorg.example", "team": "Growth"}),
    ("Growth/Team/Alpha squad.md", "team", {"type": "team", "name": "Alpha squad",
                                            "core_team": "[[ZorgCore/Teams/team-alpha]]"}),
    ("Growth/Team/Team Alpha.md", "team", {"type": "team", "core_team": "[[ZorgCore/Teams/team-alpha]]"}),
    ("Growth/Notes/plan.md", "note", {"type": "note"}),
)


def local_index(path, vault, shape="wild"):
    """A local index of the user's: `notes_fts` with a path column beside `notes(path, title, type, fm_json)`, meta
    `vault_root` — or, with shape "odd", a `notes` table with no path."""
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE meta(k TEXT, v TEXT)")
    con.execute("INSERT INTO meta VALUES ('vault_root', ?)", (vault,))
    if shape == "odd":
        con.execute("CREATE TABLE notes(id INTEGER PRIMARY KEY, name TEXT)")
        con.execute("CREATE VIRTUAL TABLE notes_fts USING fts5(name, body)")
    else:
        con.execute("CREATE TABLE notes(path TEXT PRIMARY KEY, title TEXT, type TEXT, fm_json TEXT)")
        con.execute("CREATE VIRTUAL TABLE notes_fts USING fts5(path, title, body)")
        for p, t, fm in LOCAL_NOTES:
            title = os.path.basename(p)[:-3]
            con.execute("INSERT INTO notes VALUES (?, ?, ?, ?)", (p, title, t, json.dumps(fm)))
            con.execute("INSERT INTO notes_fts VALUES (?, ?, ?)", (p, title, "text"))
    con.commit()
    con.close()


class Env:
    """A temp home and vault: the entity fixture, {{VAULT}} and {{HOME}} filled in, the local index built."""

    def __init__(self, d, shape="wild"):
        self.home = os.path.join(d, "home")
        self.vault = os.path.join(d, "vault")
        os.makedirs(os.path.join(self.home, ".grow-pm"))
        shutil.copytree(os.path.join(FIX, "vault"), self.vault)
        for dirpath, _, names in os.walk(self.vault):
            for n in names:
                p = os.path.join(dirpath, n)
                if n.endswith(".yaml") and "{{VAULT}}" in read(p):
                    write(p, read(p).replace("{{VAULT}}", self.vault))
        self.text = read(FIX, "context.md").replace("{{VAULT}}", self.vault).replace("{{HOME}}", self.home)
        self.ctx = os.path.join(self.home, ".grow-pm", "local-context.md")
        write(self.ctx, self.text)
        local_index(os.path.join(self.home, "zorg-brain.sqlite"), self.vault, shape)
        self.store = cs.Store(os.path.join(self.vault, "Notes", "_System", "context"))
        self.sctx = cs_.context_for(self.home, self.text, store_root=self.store.root)
        self.idx = ci.Index(self.home)
        self.idx.refresh(self.sctx["roots"], self.sctx["store_rel"], self.sctx["blocks_rels"])

    def registry(self, mem=None):
        return ce.load(self.sctx, self.idx, mem or ce.empty_memory())


def ent(reg, path):
    e = reg.of(path)
    return {c["path"] for c in e["cards"]} if e else set()


if ce is None:
    check("v3.18.0 scripts/ctx_entity.py exists", False, "no module ctx_entity")
    print("RESULT: RED ❌")
    sys.exit(1)

BEA_CORE, BEA_OWN, BEA_G = "ZorgCore/People/bea-two.md", "Notes/People/bea.md", "Growth/People/bea-g.md"
CY_OWN, CY_CORE = "Notes/People/cy.md", "ZorgCore/People/cy-three.md"
DEE_OWN, DEE_CORE = "Notes/People/dee.md", "ZorgCore/People/dee-real.md"
NAMESAKES = ("ZorgCore/People/cy-namesake.md", "ZorgCore/People/cy-namesake-2.md")
EPIC, SPEC, DESIGN = "Notes/Epics/Epic — PROJ-1234.md", "ZorgCore/Pages/PROJ-1234 Spec.md", "ZorgCore/Pages/PROJ-1234 Design.md"
ALPHA = "ZorgCore/Teams/team-alpha.md"

with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    reg, notes = env.registry()
    bea = reg.of(BEA_CORE)
    check("v3.18.0 e-mail: Bea of your layer, of the core and of Growth (the local index) is one entity of three cards, "
          "its id the core's card", ent(reg, BEA_CORE) == {BEA_CORE, BEA_OWN, BEA_G} and bea["id"] == BEA_CORE
          and bea["kind"] == "person", (ent(reg, BEA_CORE), bea and bea["id"]))
    check("…the Growth card carries the local index as its source",
          any(c["path"] == BEA_G and c["source"] == "zorg-brain" for c in bea["cards"]), bea["cards"])
    check("v3.18.0 bridge by shape needs corroboration: Dee's `home_card` points at Bea's card (other name, no e-mail) — "
          "Dee stays apart", DEE_OWN not in ent(reg, BEA_CORE) and ent(reg, DEE_OWN) == {DEE_OWN}, ent(reg, DEE_OWN))
    check("…and Bea's `manager` (one link, another source, the same kind, other e-mails) merges nothing (Review Focus 1)",
          CY_CORE not in ent(reg, BEA_CORE), ent(reg, BEA_CORE))
    check("v3.18.0 namesakes of the core with no e-mail are two entities", ent(reg, NAMESAKES[0]) == {NAMESAKES[0]}
          and ent(reg, NAMESAKES[1]) == {NAMESAKES[1]}, (ent(reg, NAMESAKES[0]), ent(reg, NAMESAKES[1])))
    found, how = reg.find("Cy Namesake", None)
    check("…a request by their name gives both (Review Focus 2)", how == "name" and {e["id"] for e in found} == set(NAMESAKES),
          (how, [e["id"] for e in found]))
    pairs = {frozenset((a["path"], b["path"])) for a, b in reg.pairs()}
    check("v3.18.0 maybe the same: Cy of your layer and Cy Three of the core (names alike, no e-mail on yours); Dee and "
          "Dee Real — open pairs, on both entities", frozenset((CY_OWN, CY_CORE)) in pairs
          and frozenset((DEE_OWN, DEE_CORE)) in pairs
          and any(c["path"] == CY_CORE for c in reg.of(CY_OWN)["maybe"])
          and any(c["path"] == CY_OWN for c in reg.of(CY_CORE)["maybe"]), sorted(map(sorted, pairs)))
    check("…never a pair inside one source (the namesakes) nor one already merged",
          frozenset(NAMESAKES) not in pairs and frozenset((BEA_OWN, BEA_CORE)) not in pairs, sorted(map(sorted, pairs)))
    check("v3.18.0 Q1: Growth's «Team Alpha» links to the core's team and its name is the team's alias — one entity",
          "Growth/Team/Team Alpha.md" in ent(reg, ALPHA), ent(reg, ALPHA))
    squad = reg.of("Growth/Team/Alpha squad.md")
    check("…«Alpha squad» links to it under another name — an entity of its own, related to the core's team",
          squad is not None and ent(reg, "Growth/Team/Alpha squad.md") == {"Growth/Team/Alpha squad.md"}
          and any(c["path"] == ALPHA for c in squad["related"]), squad)
    epic = reg.of(EPIC)
    check("v3.18.0 C7: the epic and the core page its `core_page` names (the same key in its name) are one work entity "
          "with the key, its id the epic (a page is a home, never the id); the other page with the key is no home",
          epic is not None and epic["key"] == "PROJ-1234" and epic["id"] == EPIC
          and ent(reg, EPIC) == {EPIC, SPEC} and DESIGN not in ent(reg, EPIC), (epic and epic["key"], ent(reg, EPIC)))
    check("…the feature whose `epic:` names the key is a work entity of its own",
          ent(reg, "Notes/Features/Fast cart.md") == {"Notes/Features/Fast cart.md"}, ent(reg, "Notes/Features/Fast cart.md"))
    check("…a local index note that is no card is no entity", reg.of("Growth/Notes/plan.md") is None)
    check("v3.18.0 known prefixes: a team's `jira`, a mission's `jira_projects`, a work card's key",
          {"PROJ", "QQ"} <= ce.known_prefixes([c for e in reg.entities for c in e["cards"]]),
          ce.known_prefixes([c for e in reg.entities for c in e["cards"]]))

    order = []
    for q_ in ("BEA.TWO@zorg.example", "PROJ-1234", "proj-1234", "ZorgCore/People/bea-two.md", "[[ZorgCore/People/bea-two]]",
               "Alpha", "TA", "Two Bea", "Nobody Here"):
        found, how = reg.find(q_, None)
        order.append((q_, how, sorted(e["id"] for e in found)))
    want = [("BEA.TWO@zorg.example", "email", [BEA_CORE]), ("PROJ-1234", "key", [EPIC]),
            ("proj-1234", "key", [EPIC]), ("ZorgCore/People/bea-two.md", "path", [BEA_CORE]),
            ("[[ZorgCore/People/bea-two]]", "path", [BEA_CORE]), ("Alpha", "name", [ALPHA]), ("TA", "name", [ALPHA]),
            ("Two Bea", "similar", [BEA_CORE]), ("Nobody Here", "none", [])]
    check("v3.18.0 C14: a request is an e-mail, a key (any case), a path or a link, a name or an alias, then something "
          "alike", order == want, [o for o, w in zip(order, want) if o != w])
    found, how = reg.find("Cy", "team")
    check("…--kind narrows it: «Cy» among teams is nothing", (found, how) == ([], "none"), (found, how))

    ce_mem = ce.empty_memory()
    check("v3.18.0 memory: an answer changes it once", ce.answer(ce_mem, CY_OWN, CY_CORE, True, "2026-10-22") is True
          and ce.answer(ce_mem, CY_CORE, CY_OWN, True, "2026-10-22") is False, ce_mem)
    reg2, _ = env.registry(ce_mem)
    pairs2 = {frozenset((a["path"], b["path"])) for a, b in reg2.pairs()}
    check("…`same` merges Cy and Cy Three, and the pair is gone", ent(reg2, CY_OWN) == {CY_OWN, CY_CORE}
          and frozenset((CY_OWN, CY_CORE)) not in pairs2, (ent(reg2, CY_OWN), sorted(map(sorted, pairs2))))
    ce.answer(ce_mem, BEA_OWN, BEA_CORE, False, "2026-10-22")
    reg3, _ = env.registry(ce_mem)
    check("v3.18.0 C3: `not-same` parts Bea of your layer from the core's Bea though their e-mails are equal",
          BEA_OWN not in ent(reg3, BEA_CORE) and BEA_G in ent(reg3, BEA_CORE), (ent(reg3, BEA_CORE), ent(reg3, BEA_OWN)))
    check("…and the answered pair is no open pair", frozenset((BEA_OWN, BEA_CORE)) not in
          {frozenset((a["path"], b["path"])) for a, b in reg3.pairs()})
    ce.answer(ce_mem, BEA_CORE, BEA_OWN, True, "2026-10-23")
    check("…the opposite answer replaces it", ce_mem["not_same"] == [] and [BEA_OWN, BEA_CORE] in
          [sorted(x[:2], key=lambda p: (p != BEA_OWN)) for x in ce_mem["same"]], ce_mem)

    os.makedirs(env.store.state_dir, exist_ok=True)
    saved = ce.save_memory(env.store, ce_mem)
    check("v3.18.0 memory: saved and read back the same (schema context-entity-memory/1)",
          ce.load_memory(env.store) == saved and saved["schema"] == "context-entity-memory/1", saved)
    path = os.path.join(env.store.state_dir, "entities.json")
    for bad in ('{"schema": "context-entity-memory/2", "same": [], "not_same": []}',
                '{"schema": "context-entity-memory/1", "same": [], "not_same": [], "later": 1}', "not json"):
        write(path, bad)
        try:
            ce.load_memory(env.store)
            raised = False
        except cs.StoreError:
            raised = True
        check("…a memory of another schema, with a key this build does not know, or not JSON is refused, never reset: %s"
              % bad[:40], raised and read(path) == bad)

    titles = {p: os.path.basename(p)[:-3] for p in ("Notes/People/bea.md", "ZorgCore/People/bea.md", "Notes/People/cy.md",
                                                    "ZorgCore/Pages/PROJ-1234 Spec.md", "Notes/Roadmap.md")}
    r = ce.Resolver(titles, ["Notes"])
    got = [r.resolve(t) for t in ("Notes/People/bea", "People/cy", "Pages/PROJ-1234 Spec.md", "bea", "../People/cy",
                                  "Roadmap", "Nowhere/x", "nothing")]
    check("v3.18.0 C5 resolver: the exact path, the plugin folder's path, the end of a path, a name two notes carry → "
          "both, `../` dropped, a name, none",
          got == ["Notes/People/bea.md", "Notes/People/cy.md", "ZorgCore/Pages/PROJ-1234 Spec.md",
                  sorted(["Notes/People/bea.md", "ZorgCore/People/bea.md"]), "Notes/People/cy.md", "Notes/Roadmap.md",
                  None, None], got)

with tempfile.TemporaryDirectory() as d:
    env = Env(d, shape="odd")
    reg, notes = env.registry()
    check("v3.18.0 C12: a local index of another shape — no cards from it, and one line that says so",
          reg.of(BEA_G) is None and ent(reg, BEA_CORE) == {BEA_CORE, BEA_OWN}
          and any("незнайому схему" in n for n in notes), (notes, ent(reg, BEA_CORE)))

print("RESULT:", "GREEN ✅" if not fails else "RED ❌")
sys.exit(1 if fails else 0)
