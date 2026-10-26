#!/usr/bin/env python3
"""TC-ctx-3180-entity — scripts/ctx_entity.py, who is who: one registry of people, teams, missions and work (v3.18.0).

The fictional Zorg vault of testing/fixtures/entity/ (the plugin folder Notes/, the core ZorgCore/ registered as zorg-core)
is copied to a temp dir, with a local index of the user's (zorg-brain, the shape seen in the wild) built beside it: the
three keys of a merge — your answer, the e-mail, a bridge by shape —, the pairs that only look alike, the memory of
your answers, a partner team that is related or the same, a work item with two homes, the link resolver and the order a
request is looked up in. Stdlib only; run from the repo root:

  env -u GROW_PM_CONTEXT_PATH -u GROW_PM_PROVIDER_PATHS python3 testing/ctx_entity_test.py
"""
import json, os, shutil, sqlite3, stat, subprocess, sys, tempfile

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


LOCAL_NOTES = (   # path, type, frontmatter — the user's own local index holds partner, which the plugin's index does not
    ("Partner/People/bea-g.md", "person", {"type": "person", "email": "bea.two@zorg.example", "team": "partner"}),
    ("Partner/Team/Alpha squad.md", "team", {"type": "team", "name": "Alpha squad",
                                            "core_team": "[[ZorgCore/Teams/team-alpha]]"}),
    ("Partner/Team/Team Alpha.md", "team", {"type": "team", "core_team": "[[ZorgCore/Teams/team-alpha]]"}),
    ("Partner/Notes/plan.md", "note", {"type": "note"}),
    ("Notes/People/cy.md", "person", {"type": "person", "team": "team-alpha"}),   # a note of yours it also holds
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

    def cli(self, *args):
        """(exit code, output, CTX_RESULT) of `ctx.py <args> --home --context`."""
        env = dict(os.environ)
        env.pop("GROW_PM_CONTEXT_PATH", None)
        p = subprocess.run([sys.executable, CTX] + list(args) + ["--home", self.home, "--context", self.ctx],
                           capture_output=True, text=True, env=env, timeout=120)
        lines = [l for l in p.stdout.splitlines() if l.strip()]
        try:
            res = json.loads(lines[-1][len("CTX_RESULT "):]) if lines and lines[-1].startswith("CTX_RESULT ") else None
        except ValueError:
            res = None
        return p.returncode, p.stdout + p.stderr, res

    def registry(self, mem=None):
        return ce.load(self.sctx, self.idx, mem or ce.empty_memory())


def ent(reg, path):
    e = reg.of(path)
    return {c["path"] for c in e["cards"]} if e else set()


if ce is None:
    check("v3.18.0 scripts/ctx_entity.py exists", False, "no module ctx_entity")
    print("RESULT: RED ❌")
    sys.exit(1)

BEA_CORE, BEA_OWN, BEA_G = "ZorgCore/People/bea-two.md", "Notes/People/bea.md", "Partner/People/bea-g.md"
CY_OWN, CY_CORE = "Notes/People/cy.md", "ZorgCore/People/cy-three.md"
DEE_OWN, DEE_CORE = "Notes/People/dee.md", "ZorgCore/People/dee-real.md"
NAMESAKES = ("ZorgCore/People/cy-namesake.md", "ZorgCore/People/cy-namesake-2.md")
EPIC, SPEC, DESIGN = "Notes/Epics/Epic — PROJ-1234.md", "ZorgCore/Pages/PROJ-1234 Spec.md", "ZorgCore/Pages/PROJ-1234 Design.md"
ALPHA = "ZorgCore/Teams/team-alpha.md"

with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    reg, notes = env.registry()
    bea = reg.of(BEA_CORE)
    check("v3.18.0 e-mail: Bea of your layer, of the core and of partner (the local index) is one entity of three cards, "
          "its id the core's card", ent(reg, BEA_CORE) == {BEA_CORE, BEA_OWN, BEA_G} and bea["id"] == BEA_CORE
          and bea["kind"] == "person", (ent(reg, BEA_CORE), bea and bea["id"]))
    check("…the partner card carries the local index as its source",
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
    check("v3.18.0 Q1: a partner team's «Team Alpha» links to the core's team and its name is the team's alias — one entity",
          "Partner/Team/Team Alpha.md" in ent(reg, ALPHA), ent(reg, ALPHA))
    squad = reg.of("Partner/Team/Alpha squad.md")
    check("…«Alpha squad» links to it under another name — an entity of its own, related to the core's team",
          squad is not None and ent(reg, "Partner/Team/Alpha squad.md") == {"Partner/Team/Alpha squad.md"}
          and any(c["path"] == ALPHA for c in squad["related"]), squad)
    epic = reg.of(EPIC)
    check("v3.18.0 C7: the epic and the core page its `core_page` names (the same key in its name) are one work entity "
          "with the key, its id the epic (a page is a home, never the id); the other page with the key is no home",
          epic is not None and epic["key"] == "PROJ-1234" and epic["id"] == EPIC
          and ent(reg, EPIC) == {EPIC, SPEC} and DESIGN not in ent(reg, EPIC), (epic and epic["key"], ent(reg, EPIC)))
    check("…the feature whose `epic:` names the key is a work entity of its own",
          ent(reg, "Notes/Features/Fast cart.md") == {"Notes/Features/Fast cart.md"}, ent(reg, "Notes/Features/Fast cart.md"))
    check("…a local index note that is no card is no entity", reg.of("Partner/Notes/plan.md") is None)
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


# --- v3.18.0 Task 3: `ctx entity` (plan C8, C9, C10, C13, C14)
def tree(*tops):
    out = {}
    for top in tops:
        for dirpath, _, names in os.walk(top):
            for n in names:
                p_ = os.path.join(dirpath, n)
                out[p_] = (os.stat(p_).st_size, os.stat(p_).st_mtime)
    return out


with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    rc, out, res = env.cli("entity", "bea.two@zorg.example", "--json")
    e0 = (res or {}).get("entities") or [{}]
    items = (e0[0].get("backlinks") or {}).get("items") or []
    one = [i for i in items if i["path"] == "Notes/Meetings/1-1 Bea 2026-10-01.md"]
    check("v3.18.0 `ctx entity <e-mail>`: exit 0, one entity of three cards, who links to it",
          rc == 0 and len(e0) == 1 and len(e0[0].get("cards") or []) == 3 and (e0[0].get("backlinks") or {}).get("count", 0) >= 2,
          (rc, out[-600:]))
    check("…the 1-1 note that links to Bea is a line marked sensitive, without its field (C8)",
          len(one) == 1 and one[0]["sensitive"] is True and "field" not in one[0], one)
    rc, out, _ = env.cli("entity", "bea.two@zorg.example")
    check("…the text: ` · sensitive` on that line, never a judgement value (`D3`) nor the note's text (Review Focus 5, C9)",
          rc == 0 and "1-1 Bea 2026-10-01 — Notes/Meetings/1-1 Bea 2026-10-01.md" in out and " · sensitive" in out
          and "D3" not in out and "growth plan" not in out and "Action items" not in out, out[-900:])
    check("…the identity: e-mail, team, role (each once), the cards with their source",
          "bea.two@zorg.example" in out and "Data analyst" in out and "zorg-core · ZorgCore/People/bea-two.md" in out
          and "zorg-brain · Partner/People/bea-g.md" in out, out[-900:])
    rc, out, res = env.cli("entity", "bea.two@zorg.example", "--skill", "one-on-one", "--json")
    items = ((res or {}).get("entities") or [{}])[0].get("backlinks", {}).get("items") or []
    one = [i for i in items if i["path"] == "Notes/Meetings/1-1 Bea 2026-10-01.md"]
    rc2, out2, _ = env.cli("entity", "bea.two@zorg.example", "--skill", "one-on-one")
    check("v3.18.0 C8: a People skill (`--skill one-on-one`) sees the field of that line; the note's text is printed never",
          rc == 0 and len(one) == 1 and one[0].get("field") == "" and "Action items" not in out2 and "growth plan" not in out2,
          (one, out2[-400:]))
    rc, out, _ = env.cli("entity", "Bea", "--skill", "no-such-skill")
    check("…an unknown skill is a usage error (exit 3)", rc == 3 and "no such skill" in out, (rc, out[-300:]))

    rc, out, res = env.cli("entity", "PROJ-9999", "--json")
    check("v3.18.0 C6: a key with no card — «картки немає, згадується в 1 нотатках» and the roadmap",
          rc == 0 and ((res or {}).get("mention") or {}).get("count") == 1, (rc, out[-500:]))
    rc, out, _ = env.cli("entity", "PROJ-9999")
    check("…in the text too", "PROJ-9999 — картки немає, згадується в 1 нотатках" in out and "Notes/Roadmap.md" in out, out[-500:])
    rc, out, res = env.cli("entity", "QQ-7", "--json")
    check("…a /browse/ key is a mention (QQ is known, and the link says it is Jira)",
          ((res or {}).get("mention") or {}).get("count") == 1, out[-400:])
    rc, out, res = env.cli("entity", "GPT-4", "--json")
    rc2, out2, _ = env.cli("entity", "GPT-4")
    check("…an unknown prefix is no mention: «Не знаю такої сутності»", rc == 0 and not (res or {}).get("mention")
          and not (res or {}).get("entities") and "Не знаю такої сутності: «GPT-4»" in out2, (rc, out2[-300:]))
    rc, out, res = env.cli("entity", "PROJ-1234", "--json")
    e1 = ((res or {}).get("entities") or [{}])[0]
    check("v3.18.0 a work entity: its key, its two homes, the notes that mention the key (the roadmap) or link to it",
          e1.get("key") == "PROJ-1234" and {c["path"] for c in e1.get("cards") or []} == {EPIC, SPEC}
          and any(i["path"] == "Notes/Roadmap.md" for i in (e1.get("mentions") or {}).get("items") or [])
          and any(i["path"] == "Notes/Features/Fast cart.md" for i in (e1.get("backlinks") or {}).get("items") or []),
          e1)
    rc, out, res = env.cli("entity", "Cy Namesake", "--json")
    rc2, out2, _ = env.cli("entity", "Cy Namesake")
    check("v3.18.0 several entities: two lines `— ctx entity \"<шлях>\"`, no block",
          rc == 0 and len((res or {}).get("entities") or []) == 2 and out2.count('— ctx entity "ZorgCore/People/cy-namesake') == 2,
          out2[-400:])
    rc, out, _ = env.cli("entity", "Alpha")
    check("v3.18.0 a team: «пов'язана з» the partner squad linked under another name", rc == 0
          and "пов'язана з: Alpha squad — Partner/Team/Alpha squad.md" in out, out[-600:])

    before = tree(env.vault, os.path.join(env.home, ".grow-pm"))
    rc, out, res = env.cli("entity", "pairs", "--json")
    pairs_ = {frozenset((x["a"]["path"], x["b"]["path"])) for x in (res or {}).get("pairs") or []}
    check("v3.18.0 `ctx entity pairs`: the open pairs, Cy ↔ Cy Three among them",
          rc == 0 and frozenset((CY_OWN, CY_CORE)) in pairs_, (rc, out[-500:]))
    rc, out, _ = env.cli("entity", CY_CORE)
    after = tree(env.vault, os.path.join(env.home, ".grow-pm"))
    changed = sorted(p_ for p_ in set(before) | set(after) if before.get(p_) != after.get(p_)
                     and not p_.startswith(os.path.join(env.home, ".grow-pm", "index") + os.sep))
    check("v3.18.0 a request and `pairs` write nothing but <home>/.grow-pm/index/", changed == [], changed)
    check("…and the pair shows on the entity: `можливо той самий: … — ctx entity same|not-same`",
          "можливо той самий:" in out and "ctx entity same|not-same" in out, out[-600:])

    rc, out, _ = env.cli("entity", "same", CY_OWN, CY_CORE)
    check("v3.18.0 C10: no store — `same` exits 3 «немає сховища — відповідь не збережено»",
          rc == 3 and "немає сховища — відповідь не збережено" in out, (rc, out[-300:]))
    rc, out, _ = env.cli("migrate", "--apply")
    check("(the store migrated)", rc == 0, out[-300:])
    rc, out, res = env.cli("entity", "same", CY_OWN, CY_CORE)
    mem = json.loads(read(env.store.state_dir, "entities.json")) if os.path.isfile(os.path.join(env.store.state_dir, "entities.json")) else {}
    journal = read(env.store.state_dir, "journal.jsonl").strip().splitlines() if os.path.isfile(os.path.join(env.store.state_dir, "journal.jsonl")) else []
    last = json.loads(journal[-1]) if journal else {}
    check("v3.18.0 `ctx entity same`: the answer in .state/entities.json, a snapshot, a journal line op entity",
          rc == 0 and [x[:2] for x in mem.get("same") or []] == [sorted([CY_OWN, CY_CORE])] and last.get("op") == "entity"
          and last.get("action") == "same" and last.get("snapshot"), (rc, out[-400:], mem, last))
    rc, out, res = env.cli("entity", "Cy Three", "--json")
    check("…and the next request sees one entity", len(((res or {}).get("entities") or [{}])[0].get("cards") or []) == 2, out[-400:])
    rc, out, _ = env.cli("entity", "same", CY_CORE, CY_OWN)
    check("…the same answer again changes nothing", rc == 0 and "unchanged" in out, out[-300:])
    rc, out, _ = env.cli("undo")
    mem = json.loads(read(env.store.state_dir, "entities.json")) if os.path.isfile(os.path.join(env.store.state_dir, "entities.json")) else {"same": []}
    check("…`ctx undo` takes it back", rc == 0 and not mem.get("same"), (rc, mem))
    rc, out, _ = env.cli("entity", "not-same", "Cy Namesake", CY_CORE)
    check("v3.18.0 an answer by a name several cards carry is a usage error that names them (exit 3)",
          rc == 3 and "cy-namesake" in out, (rc, out[-300:]))
    rc, out, _ = env.cli("entity", "same", CY_OWN, ALPHA)
    check("…two cards of different kinds: exit 3 that says so", rc == 3 and "різних видів" in out, (rc, out[-300:]))
    rc, out, _ = env.cli("entity", "--q", "pairs")
    check("v3.18.0 `--q pairs` asks for an entity named «pairs», not the list", rc == 0 and "Не знаю такої сутності: «pairs»" in out,
          out[-300:])

with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    write(os.path.join(env.vault, "Notes", "People", "eve.md"), "---\ntype: person\nemail: eve@zorg.example\n---\n# Eve New\n")
    res = ce.run(env.sctx, "eve@zorg.example", budget=0)
    check("v3.18.0 C13: while the index still has files to look at, «Поки не знаю» and the line of the refresh",
          not res["entities"] and any(n.startswith("індекс оновлюється") for n in res["notes"])
          and "Поки не знаю «eve@zorg.example» — індекс оновлюється" in ce.render(res), (res["notes"], ce.render(res)))
with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    os.remove(os.path.join(env.home, "zorg-brain.sqlite"))
    db = os.path.join(env.home, ".grow-pm", "index", "sections.sqlite")
    write(db, "not a database")
    folder = os.path.dirname(db)
    os.chmod(folder, stat.S_IRUSR | stat.S_IXUSR)
    try:
        rc, out, _ = env.cli("entity", "Bea")
    finally:
        os.chmod(folder, stat.S_IRWXU)
    check("v3.18.0 C13: an index that cannot be read nor built again, and nothing else to read — exit 5 «Базу не прочитано»",
          rc == 5 and "Базу не прочитано" in out, (rc, out[-400:]))


# --- v3.18.0 Task 2 review fixes
with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    write(os.path.join(env.vault, "ZorgCore", "People", "boss.md"), "---\ntype: people\nemail: boss@zorg.example\n---\n# Una Boss\n")
    write(os.path.join(env.vault, "Notes", "People", "ivy.md"),
          "---\ntype: person\nemail: ivy@zorg.example\nmanager_email: boss@zorg.example\n---\n# Ivy Lee\n")
    write(os.path.join(env.vault, "ZorgCore", "Epics", "PROJ-1234 hub.md"), "---\ntype: epic\n---\n# PROJ-1234 hub\n")
    write(os.path.join(env.vault, "ZorgCore", "ann.md"), "---\ntype: people\n---\n# Ann Core\n")
    write(os.path.join(env.vault, "Notes", "ann.md"), "---\ntype: person\nhome_card: \"[[ann]]\"\n---\n# Ann Core\n")
    env.idx.refresh(env.sctx["roots"], env.sctx["store_rel"], env.sctx["blocks_rels"])
    reg, _ = env.registry()
    check("v3.18.0 review I3 (Task 2): only a person's own address fields are a key — `manager_email` merges nobody",
          ent(reg, "Notes/People/ivy.md") == {"Notes/People/ivy.md"}, ent(reg, "Notes/People/ivy.md"))
    found, how = reg.find("ZorgCore/Pages/cy.md", None)
    found2, how2 = reg.find("ZorgCore/Pages/PROJ-1234 Design.md", None)
    check("v3.18.0 review I1 (Task 2): a path that names no card is no name request — nothing, never another note's entity",
          (found, found2) == ([], []) and how == how2 == "path", (how, [e["id"] for e in found], how2, [e["id"] for e in found2]))
    pairs = {frozenset((a["path"], b["path"])) for a, b in reg.pairs()}
    check("v3.18.0 review I5 (Task 2): two work cards of one Jira key in different sources are an open pair",
          frozenset((EPIC, "ZorgCore/Epics/PROJ-1234 hub.md")) in pairs, sorted(map(sorted, pairs)))
    r = reg.resolver
    check("v3.18.0 review I4 (Task 2): a bare name is never the plugin folder's guess — two notes `ann` are two, as --get "
          "says; the bridge of `[[ann]]` merges nothing", r.resolve("ann") == ["Notes/ann.md", "ZorgCore/ann.md"]
          and ent(reg, "Notes/ann.md") == {"Notes/ann.md"}, (r.resolve("ann"), ent(reg, "Notes/ann.md")))
    rl = ce.Resolver({"Notes/x.md": {"title": "x", "source": "own"}, "Partner/x.md": {"title": "x", "source": "zorg-brain",
                                                                                     "origin": "local"}}, ["Notes"])
    check("…and a name the own index holds once wins over a local index's note of that name, as --get prefers",
          rl.resolve("x") == "Notes/x.md", rl.resolve("x"))
    mem = ce.empty_memory()
    mem["not_same"].append([CY_OWN, CY_CORE, "2026-10-20"])
    mem["same"].append(sorted([CY_CORE, "ZorgCore/People/cy-namesake.md"]) + ["2026-10-21"])
    mem["same"].append(sorted([CY_OWN, "ZorgCore/People/cy-namesake.md"]) + ["2026-10-22"])
    reg2, _ = env.registry(mem)
    skipped = [tuple(x["cards"]) for x in getattr(reg2, "skipped", [])]
    check("v3.18.0 review I2 (Task 2): your answers apply newest first; one a `not-same` blocks is reported, never dropped "
          "silently", ent(reg2, CY_OWN) == {CY_OWN, "ZorgCore/People/cy-namesake.md"}
          and skipped == [tuple(sorted([CY_CORE, "ZorgCore/People/cy-namesake.md"]))], (ent(reg2, CY_OWN), skipped))
    os.makedirs(env.store.state_dir, exist_ok=True)
    ce.save_memory(env.store, mem)
    res = ce.run(env.sctx, CY_CORE, store=env.store)
    check("…`ctx entity` says which answer it could not apply", any(n.startswith("твою відповідь same %s ↔ %s"
          % tuple(sorted([CY_CORE, "ZorgCore/People/cy-namesake.md"]))) and "not-same" in n for n in res["notes"]), res["notes"])


# --- v3.18.0 acceptance fix: a link two notes of one name answer is counted for neither, and breaks nothing
with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    write(os.path.join(env.vault, "ZorgCore", "ann.md"), "---\ntype: people\n---\n# Ann Core\n")
    write(os.path.join(env.vault, "Notes", "ann.md"), "---\ntype: person\n---\n# Ann Mine\n")
    write(os.path.join(env.vault, "Notes", "x.md"), "# X\n\nSee [[ann]].\n")
    try:
        res = ce.run(env.sctx, "Notes/ann.md")
        err = None
    except Exception as e:  # noqa: BLE001
        res, err = None, e
    check("v3.18.0 acceptance: an ambiguous link (`[[ann]]`, two notes) breaks no request and counts for neither",
          err is None and res["entities"][0]["backlinks"]["count"] == 0, err or res["entities"][0]["backlinks"])

with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    write(os.path.join(env.vault, "ZorgCore", "People", "una-a.md"), "---\ntype: people\nemail: una.a@zorg.example\n---\n# Una Same\n")
    write(os.path.join(env.vault, "Notes", "People", "una-b.md"), "---\ntype: person\nemail: una.b@zorg.example\n---\n# Una Same\n")
    env.idx.refresh(env.sctx["roots"], env.sctx["store_rel"], env.sctx["blocks_rels"])
    reg, _ = env.registry()
    pairs = {frozenset((a["path"], b["path"])) for a, b in reg.pairs()}
    check("v3.18.0 acceptance: two people whose e-mails differ are no «maybe the same» pair, however alike their names "
          "(605 of 679 pairs on the real data); a card without one still is",
          frozenset(("ZorgCore/People/una-a.md", "Notes/People/una-b.md")) not in pairs
          and frozenset((CY_OWN, CY_CORE)) in pairs, sorted(map(sorted, pairs)))


# --- v3.18.0 Task 3 review fixes
with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    write(os.path.join(env.vault, "Notes", "Other", "bea-two.md"), "# Not Bea\n")
    write(os.path.join(env.vault, "Notes", "Elsewhere.md"), "# Elsewhere\n\n[[Notes/Other/bea-two]]\n")
    for i in range(22):
        write(os.path.join(env.vault, "Notes", "Log", "day-%02d.md" % i),
              "---\ndate: 2026-09-%02d\n---\n# Day %02d\n\n[[ZorgCore/People/bea-two]]\n" % (i + 1, i))
    env.idx.refresh(env.sctx["roots"], env.sctx["store_rel"], env.sctx["blocks_rels"])
    res = ce.run(env.sctx, BEA_CORE)
    bl = res["entities"][0]["backlinks"]
    paths = [i["path"] for i in bl["items"]]
    check("v3.18.0 review (Task 3): a link to another note of the card's name is not a backlink; the entity's own cards "
          "are not either", "Notes/Elsewhere.md" not in paths and BEA_OWN not in paths, paths)
    dates = [i["date"] for i in bl["items"]]
    check("…newest first, 20 lines, `ще N` for the rest", len(bl["items"]) == 20 and bl["count"] > 20
          and dates == sorted(dates, reverse=True) and paths.index("Notes/Log/day-21.md") < paths.index("Notes/Log/day-20.md") and ("    ще %d" % (bl["count"] - 20)) in ce.render(res), (bl["count"], paths[:3]))
    ep = ce.run(env.sctx, "PROJ-1234")["entities"][0]
    check("…a work entity's own cards are not among the notes that mention its key",
          EPIC not in [i["path"] for i in ep["mentions"]["items"]], ep["mentions"])
    reg, _ = env.registry()
    try:
        ce.card_of(reg, "ZorgCore/Pages/cy.md")
        raised = False
    except ValueError:
        raised = True
    env.cli("migrate", "--apply")
    rc, out, _ = env.cli("entity", "same", "ZorgCore/Pages/cy.md", CY_CORE)
    check("v3.18.0 review I1 (Task 3): an answer naming a path that is no card is refused — never another card by its "
          "name", raised and rc == 3, (raised, rc, out[-300:]))
    rc, out, res = env.cli("entity", "PROJ-1234", "--kind", "team", "--json")
    check("…`--kind team PROJ-1234` never says «картки немає» about a key a work card holds",
          rc == 0 and not (res or {}).get("mention"), (res or {}).get("mention"))
    real_cards = ci.Index.cards

    def busy(self):
        self.problem = ci.BUSY_NOTE
        return []
    os.remove(os.path.join(env.home, "zorg-brain.sqlite"))      # only the own index could answer
    ci.Index.cards = busy
    try:
        res = ce.run(env.sctx, BEA_CORE)
    finally:
        ci.Index.cards = real_cards
    check("v3.18.0 review I2 (Task 3): an index busy when its cards are read has not answered — `read` False (exit 5), "
          "never «Не знаю»", res["read"] is False and any(ci.BUSY_NOTE in n for n in res["notes"]), (res["read"], res["notes"]))


# --- v3.18.0 final review fixes
with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    write(os.path.join(env.vault, "Notes", "People", "eve.md"), "---\ntype: person\nemail: eve@zorg.example\n---\n# Eve Same\n")
    write(os.path.join(env.vault, "ZorgCore", "People", "eve.md"), "---\ntype: people\nemail: eve@zorg.example\n---\n# Eve Same\n")
    write(os.path.join(env.vault, "ZorgCore", "People", "eve-namesake.md"), "---\ntype: people\n---\n# Eve Same\n")
    env.idx.refresh(env.sctx["roots"], env.sctx["store_rel"], env.sctx["blocks_rels"])
    out = ce.render(ce.run(env.sctx, "eve@zorg.example"))
    check("v3.18.0 final I1: the «maybe the same» line names the two cards that paired, so its command closes the pair",
          'ctx entity same|not-same "Notes/People/eve.md" "ZorgCore/People/eve-namesake.md"' in out, out)
    env.cli("migrate", "--apply")
    env.cli("entity", "not-same", "Notes/People/eve.md", "ZorgCore/People/eve-namesake.md")
    rc, out2, _ = env.cli("entity", "eve@zorg.example")
    check("…and once answered, the pair is gone", "можливо той самий" not in out2, out2[-400:])
    res = ce.run(env.sctx, "Two Bea")
    check("v3.18.0 final I2: a near match says so before the entity — «схоже на «…» — не точний збіг»",
          ce.render(res).startswith("схоже на «Two Bea» — не точний збіг:"), ce.render(res)[:200])
    real_cards = ci.Index.cards

    def busy(self):
        self.problem = ci.BUSY_NOTE
        return []
    ci.Index.cards = busy
    try:
        res = ce.run(env.sctx, "Nobody Here")
    finally:
        ci.Index.cards = real_cards
    check("v3.18.0 final M2 (re-graded): the own index busy, a local index answering — «Поки не знаю … індекс пошуку "
          "зайнятий», never the bare «Не знаю»", "Поки не знаю «Nobody Here» — " + ci.BUSY_NOTE in ce.render(res)
          and "Не знаю такої сутності" not in ce.render(res), ce.render(res))
with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    con = sqlite3.connect(env.idx.db_path)
    for tb in ("ents", "links", "mentions"):
        con.execute("DROP TABLE %s" % tb)
    con.execute("UPDATE meta SET value = '2' WHERE key = 'meta_version'")
    con.commit()
    con.close()
    real = ci.is_dataless
    ci.is_dataless = lambda p_: str(p_).endswith(os.path.join("Notes", "People", "cy.md"))
    try:
        env.idx.refresh(env.sctx["roots"], env.sctx["store_rel"], env.sctx["blocks_rels"])
    finally:
        ci.is_dataless = real
    reg, _ = env.registry()
    c = next((c for c in (reg.of(CY_OWN) or {}).get("cards", []) if c["path"] == CY_OWN), None)
    check("v3.18.0 final M1 (re-graded): a card iCloud evicted before its identity was read comes from the local index "
          "meanwhile", c is not None and c["origin"] == "local", c)

# --- v3.18.1 Task 1: a local index's card of a note the own index holds, named in another case (v3.18.0 minor M5)
with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    con = sqlite3.connect(os.path.join(env.home, "zorg-brain.sqlite"))
    con.execute("UPDATE notes SET path = 'notes/people/CY.md' WHERE path = 'Notes/People/cy.md'")
    con.commit()
    con.close()
    reg, _ = env.registry()
    paths = {c["path"] for e in reg.entities for c in e["cards"]}
    check("v3.18.1 a local index's note the own index holds under another case is not a card of its own",
          CY_OWN in paths and not any(p_.casefold() == CY_OWN.casefold() and p_ != CY_OWN for p_ in paths), sorted(paths))

# --- v3.18.1 Task 3: `ctx entity` — slots, --slot, several requests, the hints of a local index (C9, C10, C11)
import io, contextlib  # noqa: E402
import ctx as ctx_cli  # noqa: E402
RHEA_OWN, PAY, FAY_CORE = "Notes/People/rhea.md", "ZorgCore/Teams/zorg-pay.md", "ZorgCore/People/fay.md"


def in_process(env, *args):
    """(exit code, output, CTX_RESULT) of `ctx` run in this process, so a function can be replaced."""
    saved = os.environ.pop("GROW_PM_CONTEXT_PATH", None)
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            try:
                rc = ctx_cli.main(list(args) + ["--home", env.home, "--context", env.ctx])
            except SystemExit as e:
                rc = e.code
    finally:
        if saved is not None:
            os.environ["GROW_PM_CONTEXT_PATH"] = saved
    out = buf.getvalue()
    lines = [l for l in out.splitlines() if l.startswith("CTX_RESULT ")]
    return rc, out, json.loads(lines[-1][len("CTX_RESULT "):]) if lines else None


def hints_index(path, vault, edges=True, odd=False):
    """The wild local index of zorg-brain, with its own `entities` and `edges` (C10) — `odd`: tables of another shape."""
    if os.path.exists(path):
        os.remove(path)
    local_index(path, vault)
    con = sqlite3.connect(path)
    for p_, t, fm in (("Partner/Notes/plan.md", "note", {"type": "note"}),
                      ("Partner/People/kai.md", "person", {"type": "person", "sensitive": True}),
                      ("Notes/_System/context/team-alpha.md", "team", {"type": "team"})):
        con.execute("INSERT OR REPLACE INTO notes VALUES (?, ?, ?, ?)", (p_, os.path.basename(p_)[:-3], t, json.dumps(fm)))
    if odd:
        con.execute("CREATE TABLE entities(name TEXT)")
        con.execute("CREATE TABLE edges(a TEXT, b TEXT)")
    else:
        con.execute("CREATE TABLE entities(key TEXT, kind TEXT, path TEXT, label TEXT)")
        con.executemany("INSERT INTO entities VALUES (?, ?, ?, ?)", [
            ("person:gus", "person", "Notes/People/cy.md", "Cy"), ("person:gus", "person", "ZorgCore/People/gus.md", "Gus")])
        if edges:
            con.execute("CREATE TABLE edges(src TEXT, dst TEXT, kind TEXT)")
            con.executemany("INSERT INTO edges VALUES (?, ?, ?)", [
                ("Partner/Notes/plan.md", ALPHA, "wikilink"), ("Partner/People/kai.md", ALPHA, "fm:team"),
                ("Notes/_System/context/team-alpha.md", ALPHA, "wikilink"), ("Notes/Roadmap.md", ALPHA, "wikilink")])
    con.commit()
    con.close()


with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    rc, out, res = env.cli("entity", "Rhea One")
    check("v3.18.1 C9a: one entity's answer has its slots — the role (yours) with its «також», the team by its label, the "
          "e-mail — each with its source", rc == 0 and "слоти:" in out and "роль: PM" in out and "також: Product lead (zorg-core" in out
          and "команда: Zorg Pay" in out and "e-mail: rhea@zorg.example" in out, out[-900:])
    rc, out, res = env.cli("entity", "Zorg Pay")
    e0 = ((res or {}).get("entities") or [{}])[0]
    check("…a team's members, one line each with its origins, the derived-only marked; its missions",
          rc == 0 and "склад (2):" in out and "Rhea One — " in out and "Fay Four — " in out and "лише виведене" in out
          and "місії (2):" in out and set(e0.get("slots", {})) >= {"team.members", "team.missions", "team.parent"}, out[-1200:])
    rc, out, res = env.cli("entity", "Zorg Pay", "--slot", "team.members", "--slot", "team.missions")
    e0 = ((res or {}).get("entities") or [{}])[0]
    check("v3.18.1 C9b: --slot keeps the slots asked for, and no «хто посилається» or mentions",
          rc == 0 and set(e0.get("slots", {})) == {"team.members", "team.missions"} and "хто посилається" not in out
          and "backlinks" not in e0, (out[-600:], list(e0)))
    rc, out, _ = env.cli("entity", "Zorg Pay", "--slot", "team.nope")
    check("…an unknown --slot is a usage error that lists the slots of the cards (exit 3)",
          rc == 3 and "team.members" in out and "person.role" in out, out[-400:])
    calls = []
    real = ce.cs_._refresh
    ce.cs_._refresh = lambda *a_, **k_: (calls.append(1), real(*a_, **k_))[1]
    try:
        rc, out, res = in_process(env, "entity", "--q", "Rhea One", "--q", "fay@zorg.example", "--slot", "person.team",
                                  "--slot", "person.role")
    finally:
        ce.cs_._refresh = real
    check("v3.18.1 C9c: --q twice — one refresh of the index, one block per request, each with its slot",
          rc == 0 and len(calls) == 1 and len((res or {}).get("requests") or []) == 2
          and "«Rhea One»" in out and "«fay@zorg.example»" in out and out.count("команда: Zorg Pay") == 2
          and "роль: —" in out, (rc, len(calls), out[-700:]))
    check("…a slot asked for and not answered says so («роль: —»), never the identity line instead",
          "команда: zorg-pay" not in out, out[-500:])
    rc, out, res = env.cli("entity", "Team Alpha")
    check("v3.18.1 C11: a backlink from a field says its field in the text (` · поле parent`); a sensitive note outside "
          "the People contour never does", "ZorgCore/Teams/zorg-pay.md · 2026-10-01 · поле parent" in out
          and not any("Notes/People/bea.md" in l and "поле" in l for l in out.splitlines()), out[-1200:])

with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    hints_index(os.path.join(env.home, "zorg-brain.sqlite"), env.vault)
    rc, out, res = env.cli("entity", "pairs")
    check("v3.18.1 C10: the local index's `entities` pair two cards the plugin's keys did not join — «можливо той самий "
          "(підказка zorg-brain)», in the list of pairs", rc == 0 and any("підказка zorg-brain" in l and "ZorgCore/People/gus.md" in l
                                                                     and "Notes/People/cy.md" in l for l in out.splitlines()), out[-800:])
    rc, out, res = env.cli("entity", "ZorgCore/People/gus.md")
    check("…and on the entity", "можливо той самий" in out and "підказка zorg-brain" in out and "Notes/People/cy.md" in out, out[-600:])
    env.cli("migrate", "--apply")                    # a store, as `same` needs one
    rc, out, _ = env.cli("entity", "not-same", "Notes/People/cy.md", "ZorgCore/People/gus.md")
    rc2, out2, _ = env.cli("entity", "pairs")
    check("…your not-same closes a hint's pair as any other", rc == 0 and "ZorgCore/People/gus.md" not in out2, (out[-300:], out2[-500:]))
    rc, out, res = env.cli("entity", "Team Alpha")
    lines = [l for l in out.splitlines() if not l.startswith("CTX_RESULT")]
    check("v3.18.1 C10: an edge of the local index from a note the plugin's index does not hold is a «хто посилається» "
          "line with ` · zorg-brain`; a sensitive one outside People is title, path and ` · sensitive` (no field)",
          any("Partner/Notes/plan.md" in l and "· zorg-brain" in l for l in lines)
          and any("Partner/People/kai.md" in l and "sensitive" in l and "поле" not in l for l in lines), out[-1200:])
    check("…never from the store (a record of `_System/context`), never twice for a note the plugin's index holds",
          not any("_System/context" in l for l in lines) and sum("Notes/Roadmap.md" in l for l in lines) <= 1,
          [l for l in lines if "_System/context" in l or "Notes/Roadmap.md" in l])
with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    hints_index(os.path.join(env.home, "zorg-brain.sqlite"), env.vault, odd=True)
    rc, out, res = env.cli("entity", "Team Alpha")
    check("v3.18.1 C10: a local index whose `entities`/`edges` are of another shape — one line that says so, the answer "
          "the same; one with no such tables says nothing", rc == 0 and "zorg-brain: підказок немає — незнайома схема" in out
          and "Team Alpha" in out, out[-500:])
    rc0, out0, _ = Env(os.path.join(d, "x")).cli("entity", "Team Alpha") if os.makedirs(os.path.join(d, "x")) is None else (0, "", None)
    check("…(the wild index without the tables: no such line)", "підказок немає" not in out0, out0[-300:])

with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    env.cli("migrate", "--apply")
    real_cards = ci.Index.cards

    def busy(self):
        self.problem = ci.BUSY_NOTE
        return []
    os.remove(os.path.join(env.home, "zorg-brain.sqlite"))
    ci.Index.cards = busy
    try:
        rc, out, res = in_process(env, "entity", "same", CY_OWN, CY_CORE)
    finally:
        ci.Index.cards = real_cards
    check("v3.18.1 C11: `same` while the index is busy — exit 5 «індекс зайнятий», never «не картка сутності», nothing kept",
          rc == 5 and "зайнят" in out and "не картка сутності" not in out
          and not os.path.isfile(os.path.join(env.store.state_dir, "entities.json")), (rc, out[-300:]))

# --- v3.18.1 Task 3 review fixes
def human(out):
    return "\n".join(l for l in out.splitlines() if not l.startswith("CTX_RESULT"))


with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    write(os.path.join(env.vault, "ZorgCore", "Teams", "zt-secret.md"),
          "---\ntype: team\nsensitive: true\nparent: \"[[ZorgCore/Teams/team-alpha]]\"\n"
          "members:\n  - \"[[ZorgCore/People/fay|Fay Four]] — on PIP, leaving in Nov\"\n---\n# ZT Secret\n")
    write(os.path.join(env.vault, "Notes", "Teams", "zorg-pay-mine.md"),
          "---\ntype: team\nmembers:\n  - \"[[Notes/People/rhea|Rhea One]] — Lead PM (mine)\"\n---\n# Zorg Pay mine\n")
    env.idx.refresh(env.sctx["roots"], env.sctx["store_rel"], env.sctx["blocks_rels"])
    rc, out, res = env.cli("entity", "ZorgCore/Teams/zt-secret.md")
    check("v3.18.1 Task 3 review I1: a sensitive team card outside the People contour gives its members as names and "
          "sources only — never its text («on PIP»), never its values", rc == 0 and "PIP" not in out and "Fay Four" in out
          and "батьківська команда" not in human(out) and "parent" not in json.dumps((res or {}).get("entities")), out[-900:])
    rc, out, res = env.cli("entity", "ZorgCore/Teams/zt-secret.md", "--skill", "one-on-one")
    check("…the People contour sees its rows", "PIP" in out, out[-600:])
    env.cli("migrate", "--apply")
    env.cli("entity", "same", "Notes/Teams/zorg-pay-mine.md", PAY)
    rc, out, _ = env.cli("entity", "Zorg Pay")
    rl = [l for l in out.splitlines() if l.strip().startswith("Rhea One — ")]
    check("v3.18.1 Task 3 review I3: a list item's row is your card's («Lead PM (mine)»), the core's other row a «також»",
          rl and "Lead PM (mine)" in rl[0] and "також" in out and "— PM" in out, (rl, out[-900:]))
    rc, out, _ = env.cli("entity", "Rhea One", "--slot", "team.members")
    check("v3.18.1 Task 3 review M2: --slot of another kind — «склад: —», never the identity line",
          "склад: —" in out and "e-mail: rhea" not in out and "команда:" not in out, out[-500:])
    rc, out, _ = env.cli("entity", "Zorg Pay", "--slot", "person.role")
    check("…and a team asked for a person's slot says «роль: —»", "роль: —" in out, out[-400:])
    rc, out, _ = env.cli("entity", "pairs", "--slot", "person.role")
    check("v3.18.1 Task 3 review M7: --slot with pairs, same or not-same is a usage error (exit 3)", rc == 3, (rc, out[-300:]))
    rc, out, _ = env.cli("entity", "Rhea One")
    check("v3.18.1 Task 3 review M4: a slot's date is a day, never a time", "T1" not in "".join(
        l for l in out.splitlines() if l.startswith("    ")) and "T0" not in "".join(l for l in out.splitlines() if l.startswith("    ")), out[-700:])

with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    hints_index(os.path.join(env.home, "zorg-brain.sqlite"), env.vault)
    con = sqlite3.connect(os.path.join(env.home, "zorg-brain.sqlite"))
    con.executemany("INSERT INTO entities VALUES (?, ?, ?, ?)", [
        ("person:x", "person", "ZorgCore/People/rhea-core.md", "x"), ("person:x", "person", "ZorgCore/People/fay.md", "x"),
        ("person:y", "person", "ZorgCore/People/cy-namesake.md", "y"), ("person:y", "person", "ZorgCore/People/dee-real.md", "y")])
    con.executemany("INSERT INTO edges VALUES (?, ?, ?)", [("Partner/Notes/plan.md", ALPHA, "mention"),
                                                           ("Partner/Notes/note2.md", ALPHA, "epic")])
    con.execute("INSERT OR REPLACE INTO notes VALUES (?, ?, ?, ?)", ("Partner/Notes/note2.md", "note2", "note", "{}"))
    con.commit()
    con.close()
    rc, out, _ = env.cli("entity", "pairs")
    out = human(out)
    check("v3.18.1 Task 3 review I2: a hint never pairs two people whose e-mails differ, nor two cards of one source",
          "rhea-core.md ↔ ZorgCore/People/fay.md" not in out and "cy-namesake.md ↔ ZorgCore/People/dee-real.md" not in out
          and "ZorgCore/People/dee-real.md ↔ ZorgCore/People/cy-namesake.md" not in out, out[-900:])
    rc, out, _ = env.cli("entity", "Team Alpha")
    out = human(out)
    check("v3.18.1 Task 3 review M3: an edge that is no link (`mention`, `epic`) is no «хто посилається» line",
          "note2" not in out, out[-700:])
with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    hints_index(os.path.join(env.home, "zorg-brain.sqlite"), env.vault, odd=True)
    rc, out, _ = env.cli("entity", "Team Alpha")
    check("v3.18.1 Task 3 review M1: the unknown-schema line comes once", human(out).count("незнайома схема") == 1, out[-500:])

print("RESULT:", "GREEN ✅" if not fails else "RED ❌")
sys.exit(1 if fails else 0)
