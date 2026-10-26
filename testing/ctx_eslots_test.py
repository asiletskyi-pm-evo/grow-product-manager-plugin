#!/usr/bin/env python3
"""TC-ctx-3181-slots — scripts/ctx_eslots.py, the slots of one entity from its cards (since v3.19.0).

The fictional Zorg vault of testing/fixtures/entity/ is copied to a temp dir, with a local index of the user's
(zorg-brain) built beside it: a person's role by the cascade (yours, then a core's, then a local index's), a team's
members joined by entity — from a section of the core's team card, and derived from each person's winning team —, a
table of roles that is no member, a team's missions and a mission's teams both ways, a metric's owner, a person's body
never read, nothing of a profile outside the People contour. Stdlib only; run from the repo root:

  env -u GROW_PM_CONTEXT_PATH -u GROW_PM_PROVIDER_PATHS python3 testing/ctx_eslots_test.py
"""
import json, os, shutil, sqlite3, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import ctx_index as ci  # noqa: E402
import ctx_resolve as rv  # noqa: E402
import ctx_search as cs_  # noqa: E402
import ctx_slots as sl  # noqa: E402
import ctx_store as cs  # noqa: E402
import ctx_entity as ce  # noqa: E402
try:
    import ctx_eslots as es  # noqa: E402
except ImportError:
    es = None

FIX = os.path.join(ROOT, "testing", "fixtures", "entity")
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


LOCAL_NOTES = (   # path, type, frontmatter — a partner team's cards the user's own local index holds
    ("Partner/People/rhea-g.md", "person", {"type": "person", "email": "rhea@zorg.example", "role": "Growth PM"}),
    ("Partner/People/fay-g.md", "person", {"type": "person", "email": "fay@zorg.example", "role": "Analyst"}),
    ("Notes/People/gus-own.md", "person", {"type": "person", "email": "gus@zorg.example", "role": "Tech lead"}),
    ("ZorgCore/Teams/zorg-pay.md", "team", {"type": "team", "parent": "[[ZorgCore/Teams/team-alpha]]",
                                            "aliases": ["Zorg Pay", "ZP"]}),
)                 # gus-own: a note of your plugin folder iCloud evicted — the local index alone gives its card


def local_index(path, vault):
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE meta(k TEXT, v TEXT)")
    con.execute("INSERT INTO meta VALUES ('vault_root', ?)", (vault,))
    con.execute("CREATE TABLE notes(path TEXT PRIMARY KEY, title TEXT, type TEXT, fm_json TEXT)")
    con.execute("CREATE VIRTUAL TABLE notes_fts USING fts5(path, title, body)")
    for p, t, fm in LOCAL_NOTES:
        title = os.path.basename(p)[:-3]
        con.execute("INSERT INTO notes VALUES (?, ?, ?, ?)", (p, title, t, json.dumps(fm)))
        con.execute("INSERT INTO notes_fts VALUES (?, ?, ?)", (p, title, "text"))
    con.commit()
    con.close()


class Env:
    def __init__(self, d):
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
        write(os.path.join(self.home, ".grow-pm", "local-context.md"), self.text)
        local_index(os.path.join(self.home, "zorg-brain.sqlite"), self.vault)
        self.store = cs.Store(os.path.join(self.vault, "Notes", "_System", "context"))
        self.sctx = cs_.context_for(self.home, self.text, store_root=self.store.root)
        self.idx = ci.Index(self.home)
        self.idx.refresh(self.sctx["roots"], self.sctx["store_rel"], self.sctx["blocks_rels"])
        self.cat = sl.load_catalogue()
        self.reg, _ = ce.load(self.sctx, self.idx, ce.empty_memory())

    def slots(self, path, people=False, only=None):
        return es.slots_of(self.reg, self.idx, self.reg.of(path), self.cat, self.sctx, people=people, only=only)


if es is None:
    check("v3.18.1 scripts/ctx_eslots.py exists", False, "no module ctx_eslots")
    print("RESULT: RED ❌")
    sys.exit(1)

RHEA_OWN, RHEA_CORE, RHEA_G = "Notes/People/rhea.md", "ZorgCore/People/rhea-core.md", "Partner/People/rhea-g.md"
FAY, GUS = "ZorgCore/People/fay.md", "ZorgCore/People/gus.md"
PAY, OLD = "ZorgCore/Teams/zorg-pay.md", "ZorgCore/Teams/zorg-old.md"
FAST, SLOW = "ZorgCore/Missions/fast-pay.md", "ZorgCore/Missions/slow-pay.md"
CONV = "ZorgCore/Metrics/conversion.md"


def labels(ans):
    return [i["label"] for i in (ans or {}).get("items", [])]


def item(ans, path, reg):
    e = reg.of(path)
    return next((i for i in (ans or {}).get("items", []) if e and i["entity"] == e["id"]), None)


with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    reg = env.reg
    rhea = env.slots(RHEA_OWN)
    role = rhea.get("person.role") or {}
    check("v3.18.1 person.role: your note's role wins the cascade, the core's position and a local index's role are «також» "
          "with their source, path and date (C3, C6)",
          role.get("value") == "PM" and role.get("origin", {}).get("level") == "mine" and role["origin"].get("path") == RHEA_OWN
          and {(a["value"], a["source"]) for a in role.get("also", [])} == {("Product lead", "zorg-core"), ("Growth PM", "zorg-brain")}
          and all(a.get("path") and "date" in a for a in role.get("also", [])), role)
    check("…person.team and person.email are slots of the entity too — a team names its entity, shown by its label",
          (rhea.get("person.team") or {}).get("value") == "Zorg Pay" and rhea["person.team"].get("entity") == PAY
          and (rhea.get("person.email") or {}).get("value") == "rhea@zorg.example",
          {k: (v or {}).get("value") for k, v in rhea.items()})
    fay = env.slots(FAY)
    check("…a value no card of yours gives: a core's, else a local index's (Fay's role comes from the partner card)",
          (fay.get("person.role") or {}).get("value") == "Analyst" and fay["person.role"]["origin"]["level"] == "local",
          fay.get("person.role"))

    pay = env.slots(PAY)
    mem = pay.get("team.members") or {}
    ev, fy = item(mem, RHEA_OWN, reg), item(mem, FAY, reg)
    check("v3.18.1 team.members: Rhea is one item — the core card's «Склад команди» names her (repo) and her winning team "
          "derives her (derived, from your note) (C4, C5, C7)",
          ev is not None and {(o["level"], o["path"]) for o in ev["origins"]} == {("repo", PAY), ("derived", RHEA_OWN)}
          and sum(1 for i in mem.get("items", []) if i["entity"] == ev["entity"]) == 1, mem)
    check("…Fay is only derived (her card's team), and says so",
          fy is not None and fy.get("derived_only") is True and [o["level"] for o in fy["origins"]] == ["derived"], fy)
    check("…the table of roles under «Люди» gives no member, nor a line that names no card (Ann Other) — a card's list "
          "keeps the items that point at a person (C4)",
          not any(l in ("PM", "QA", "Роль", "Кількість") or "Ann" in l for l in labels(mem)), labels(mem))
    check("…an item keeps the rows of its sources: the core's line «… — PM» is Rhea's row (C7a)",
          ev is not None and any("PM" in r["text"] and r["source"] == "zorg-core" for r in ev.get("rows", [])), ev)
    check("…an item with a row of yours or a core's comes before one only derived",
          [i["entity"] for i in mem.get("items", [])].index(ev["entity"]) < [i["entity"] for i in mem.get("items", [])].index(fy["entity"])
          if ev and fy else False, labels(mem))
    old = env.slots(OLD).get("team.members") or {}
    check("v3.18.1 R9: members derive from the WINNING person.team — Rhea's core card says zorg-old, your note zorg-pay: "
          "she is no member of zorg-old", item(old, RHEA_OWN, reg) is None, old)
    check("…Gus, whose team is only in his card's body (`## Команда`), is nobody's member — a person's body is never read "
          "(C3)", item(mem, GUS, reg) is None and not (env.slots(GUS).get("person.team") or {}).get("value"),
          (labels(mem), env.slots(GUS).get("person.team")))

    tm = pay.get("team.missions") or {}
    fast, slow = item(tm, FAST, reg), item(tm, SLOW, reg)
    check("v3.18.1 team.missions: fast-pay once (the team's field and the mission's `teams` both name it), slow-pay only "
          "derived (its `teams` names the team, the team's field does not)",
          fast is not None and {o["level"] for o in fast["origins"]} == {"repo", "derived"}
          and slow is not None and slow.get("derived_only") is True, tm)
    mt = env.slots(FAST).get("mission.teams") or {}
    zp = item(mt, PAY, reg)
    check("…and mission.teams the other way: zorg-pay once, from the mission's field and derived from the team's",
          zp is not None and {o["level"] for o in zp["origins"]} == {"repo", "derived"}
          and sum(1 for i in mt.get("items", []) if i["entity"] == zp["entity"]) == 1, mt)
    check("…mission.jira_projects is the mission's own list", [i["label"] for i in (env.slots(FAST).get("mission.jira_projects") or {}).get("items", [])] == ["PROJ"],
          env.slots(FAST).get("mission.jira_projects"))
    own = env.slots(CONV).get("metric.owner") or {}
    check("v3.18.1 metric.owner: a link names a person — the value is their label, with the entity it names",
          own.get("entity") == (reg.of(FAY) or {}).get("id") and own.get("value") == (reg.of(FAY) or {}).get("label"), own)
    check("…team.parent: the core card's parent", (pay.get("team.parent") or {}).get("entity") == (reg.of("ZorgCore/Teams/team-alpha.md") or {}).get("id"),
          pay.get("team.parent"))

    outside = json.dumps(env.slots(RHEA_OWN), ensure_ascii=False)
    check("v3.18.1 outside the People contour a person's slots hold the identity alone — no judgement value of the profile",
          set(env.slots(RHEA_OWN)) <= {"person.role", "person.team", "person.email"} and "D2" not in outside
          and "tired" not in outside, outside[:300])
    check("…`only` keeps the slots asked for", set(env.slots(PAY, only=["team.missions"])) == {"team.missions"}, "")

    for slot_id, path in (("team.members", PAY), ("team.missions", PAY), ("mission.teams", FAST)):
        ans = env.slots(path).get(slot_id) or {}
        cands = es.candidates(reg, env.idx, reg.of(path), slot_id, env.cat, env.sctx)
        ok = True
        for it in ans.get("items", []):
            naming = [c for c in cands if any(es.item_entity(reg, x, es.item_kind(slot_id))[0] == it["entity"]
                                              for x in c["items"])] if it["entity"] else []
            if it["entity"] and len(it["origins"]) != len(naming):
                ok = False
        check("v3.18.1 %s: no item loses a source — as many origins as candidates name its entity" % slot_id, ok, ans)

with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    con = sqlite3.connect(env.idx.db_path)
    con.execute("UPDATE ents SET fields_json = NULL WHERE path = ?", (FAY,))    # read by v3.18.0, evicted since
    con.commit()
    con.close()
    env.reg, _ = ce.load(env.sctx, env.idx, ce.empty_memory())
    check("v3.18.1 Task 1 review I2: a card whose slot fields no walk read yet answers from its identity columns — Fay is "
          "still a member of zorg-pay by her team", item(env.slots(PAY).get("team.members"), FAY, env.reg) is not None,
          env.slots(PAY).get("team.members"))
    check("v3.18.1 Task 2 review M3: …and her answer says which card is not read yet",
          (env.slots(FAY).get("person.team") or {}).get("unread") == [FAY], env.slots(FAY).get("person.team"))

with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    role = env.slots(GUS).get("person.role") or {}
    check("v3.18.1 acceptance: your note the local index gives (its file evicted) is yours — `mine`, it wins over the core",
          role.get("value") == "Tech lead" and role.get("origin", {}).get("level") == "mine", role)

with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    con = sqlite3.connect(env.idx.db_path)
    con.execute("UPDATE ents SET fields_json = NULL WHERE path = ?", (PAY,))    # read by v3.18.0, evicted since
    con.commit()
    con.close()
    env.reg, _ = ce.load(env.sctx, env.idx, ce.empty_memory())
    par = env.slots(PAY).get("team.parent") or {}
    check("v3.18.1 final review M4: a card whose fields no walk read (its file evicted) takes them from the same note's "
          "frontmatter in a local index — its parent is back, not «не прочитано»",
          par.get("entity") == (env.reg.of("ZorgCore/Teams/team-alpha.md") or {}).get("id") and not par.get("unread"), par)
    check("…and the local index's copy is no second card", sum(1 for c in env.reg.of(PAY)["cards"] if c["path"] == PAY) == 1,
          env.reg.of(PAY)["cards"])

# the cascade over the levels of the cards (C6): pure, candidates in, an answer out
cat = sl.load_catalogue()


def cand(level, source, text, rank=None):
    return {"level": level, "source": source, "text": text, "rank": rank, "placed": True}


r = rv.resolve("person.role", cat, [cand("derived", "x.md", "C"), cand("local", "zorg-brain", "B"),
                                    cand("repo", "zorg-core", "A", 1)], None)
check("v3.18.1 the levels of the cards: a repository's card, then a local index's, then the derived (C6)",
      [c["text"] for c in r["shown"]] == ["A"] and sorted(c["text"] for c in r["also"]) == ["B", "C"] and not r["diverges"], r)
r = rv.resolve("person.role", cat, [cand("derived", "x.md", "C"), cand("local", "zorg-brain", "B")], None)
check("…with no repository's card, the local index's wins — it is no «registration not read», and no tie with the derived",
      [c["text"] for c in r["shown"]] == ["B"] and r["why"] != rv.WHY_UNREAD and not r["diverges"], r)
r = rv.resolve("person.role", cat, [cand("repo", "core-a", "A", 1), cand("repo", "core-b", "B", 1)], None)
check("…two cores of one rank with different values diverge (shown both), as the records' blocks do",
      sorted(r["diverges"]) == ["core-a", "core-b"], r)

# C1a: a card's slot stays out of the records' machinery
import ctx as ctx_cli  # noqa: E402
msg = ctx_cli._no_slot("person.role", cat)
check("v3.18.1 `ctx slot prefer|bind|…` and `ctx explain` on a card's slot: a usage line that says the cards' cascade "
      "decides it and how to see it (C1a)", "ctx entity" in msg and "--slot person.role" in msg
      and "no slot" in ctx_cli._no_slot("product.nope", cat), msg)
recs = [{"id": "team-zorg", "type": "team", "body": "## Team\n\n### Team Members\n\n- Bea\n\n#### Люди\n\n| Роль | N |\n|---|---|\n| PM | 1 |\n"}]
props = sl.proposals(recs, [], {}, cat)
check("…and `ctx validate` proposes no binding to a card's slot (`### Team Members` is no `person.team`, «Люди» no "
      "team.members of a record)", not any(p_["slot"] in ("person.team", "team.parent", "team.missions") for p_ in props), props)
r = rv.resolve("person.role", cat, [cand("repo", "core-a", "A", 1), cand("repo", "core-b", "B", 1)], None)
check("…a card slot's divergence is shown both ways and no decision of the memory is applied to it",
      len(r["shown"]) == 2 and r["decision"] is None, r)

# --- v3.18.1 Task 2 review fixes
def card(env, rel, text):
    write(os.path.join(env.vault, rel), text)


with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    card(env, "ZorgCore/Teams/zt-sub.md", "---\ntype: team\nmissions: 3\nmembers: 12\nupdated: 2026-10-01\n---\n# ZT Sub\n\n"
         "## Місії (матриця капасіті)\n\n- [[ZorgCore/Missions/mission-orbit]]\n\n## Склад команди\n\n### Backend\n\n"
         "- [[ZorgCore/People/gus]]\n\n### Frontend\n\n- [[ZorgCore/People/fay]]\n\n## Команди-партнери\n\n- [[zorg-old]]\n")
    card(env, "ZorgCore/People/dup.md", "---\ntype: people\nemail: dup1@zorg.example\n---\n# Dup One\n")
    card(env, "ZorgCore/Other/dup.md", "---\ntype: people\nemail: dup2@zorg.example\n---\n# Dup Two\n")
    card(env, "ZorgCore/Teams/zt-dup.md", "---\ntype: team\n---\n# ZT Dup\n\n## Склад команди\n\n- [[dup]] — who?\n"
         "- [[ZorgCore/People/gus]]\n- [[ZorgCore/People/gus|Gus again]] — lead\n- Ann Other — QA\n- Ann Other — QA\n\n"
         "| Name | Role |\n|-|-|\n| [[ZorgCore/People/fay\\|Fay]] | PM |\n")
    card(env, "ZorgCore/Metrics/churn.md", "---\ntype: metric\n---\n# Churn\n\n## Owner history\n\n2024: someone else\n\n"
         "## Власник\n\n- Gus Five\n")
    env.idx.refresh(env.sctx["roots"], env.sctx["store_rel"], env.sctx["blocks_rels"])
    env.reg, _ = ce.load(env.sctx, env.idx, ce.empty_memory())
    reg = env.reg
    sub = env.slots("ZorgCore/Teams/zt-sub.md")
    check("v3.18.1 Task 2 review I1: a field that names nothing (`missions: 3`, `members: 12`) does not hide the sections "
          "with the real list", item(sub.get("team.missions"), "ZorgCore/Missions/mission-orbit.md", reg) is not None
          and item(sub.get("team.members"), GUS, reg) is not None, sub)
    check("v3.18.1 Task 2 review I3: members under sub-headings of «Склад команди» (`### Backend`, `### Frontend`) count",
          item(sub.get("team.members"), GUS, reg) is not None and item(sub.get("team.members"), FAY, reg) is not None,
          labels(sub.get("team.members")))
    check("v3.18.1 Task 2 review M1: «Команди-партнери» is no «Команди» — a hyphen is no qualifier",
          not (env.slots("ZorgCore/Missions/fast-pay.md").get("mission.teams") or {}).get("items") or
          item(env.slots("ZorgCore/Missions/fast-pay.md").get("mission.teams"), OLD, reg) is None, "")
    dup = env.slots("ZorgCore/Teams/zt-dup.md").get("team.members") or {}
    check("v3.18.1 Task 2 review I2: a link two people's notes answer (`[[dup]]`) joins nobody — never the namesake that "
          "sorts first", not any(i["label"] in ("Dup One", "Dup Two") for i in dup.get("items", [])), labels(dup))
    g = item(dup, GUS, reg)
    check("v3.18.1 Task 2 review M6: two lines of one card that name one person are one item with both rows (one origin)",
          g is not None and len(g["origins"]) == 1 and len(g["rows"]) == 2, g)
    check("v3.18.1 Task 2 review M7: a table with a `|-|-|` rule — its header is no item, its row is (Fay)",
          item(dup, FAY, reg) is not None and not any(i["label"].startswith("| Name") for i in dup.get("items", [])), labels(dup))
    check("…every item says its kind", all(i.get("kind") == "person" for i in dup.get("items", [])), dup.get("items"))
    own = env.slots("ZorgCore/Metrics/churn.md").get("metric.owner") or {}
    check("v3.18.1 Task 2 review M1/M10: a value slot prefers the exact heading («Власник») over a qualified one («Owner "
          "history»), and a value read from a list item loses its marker (Gus Five, his entity)",
          own.get("entity") == (reg.of(GUS) or {}).get("id"), own)
    j = es.join_items([{"level": "mine", "card_source": "own", "path": "a.md", "date": "", "items": ["Ann Other — QA"]},
                       {"level": "repo", "card_source": "zorg-core", "path": "b.md", "date": "", "items": ["Ann Other — QA"]}],
                      reg, "person", strict=False)
    check("v3.18.1 Task 2 review M6: two text items of two sources are never joined by their words", len(j) == 2, j)
    check("v3.18.1 Task 2 review M8: outside the People contour a person's slots are role, team and e-mail at most — a "
          "person slot the catalogue may add later stays out", set(es.PERSON_IDENTITY) == {"person.role", "person.team", "person.email"}
          and set(env.slots(RHEA_OWN)) <= set(es.PERSON_IDENTITY), "")
import types  # noqa: E402
a_ = types.SimpleNamespace(action="prefer", slot="person.role", target="mine", sub=None, team=None, record=None)
try:
    ctx_cli._slot_request(a_, cat)
    msg = ""
except ctx_cli.Usage as e:
    msg = str(e)
check("v3.18.1 Task 2 review M9: `ctx slot prefer person.role mine` itself is the usage line of a card slot",
      "ctx entity" in msg and "--slot person.role" in msg, msg)

# --- v3.20.0 Task 5: the deferred minors of v3.19.0 (plan C10)
OPS = "ZorgCore/Teams/zorg-ops.md"
OPS_TEXT = """---
type: team
aliases: [Zorg Ops]
---
# Zorg Ops

## Люди

| Хто | Роль |
|---|---|
| Fay Four, Bea Two | QA |

## Склад команди

- **Lead:** Rhea One, Bea Two
- Cy Namesake, Gus Five — Dev
- Ann Other і Fay Four — Support
"""
with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    card(env, OPS, OPS_TEXT)
    env.idx.refresh(env.sctx["roots"], env.sctx["store_rel"], env.sctx["blocks_rels"])
    env.reg, _ = ce.load(env.sctx, env.idx, ce.empty_memory())
    ops = env.slots(OPS).get("team.members") or {}
    got = {i["entity"] for i in ops.get("items", []) if i["entity"]}
    ids = {k: (env.reg.of(v) or {}).get("id") for k, v in (("fay", FAY), ("gus", GUS), ("cy", "ZorgCore/People/cy-three.md"),
                                                           ("bea", "ZorgCore/People/bea-two.md"), ("rhea", RHEA_CORE))}
    check("v3.20.0 a row «Ім'я, Ім'я — роль» of a table joins each person, not the first only",
          {ids["fay"], ids["bea"]} <= got, labels(ops))
    check("…an inline `**Lead:** A, B` line is two items, each its entity",
          {ids["rhea"], ids["bea"]} <= got, labels(ops))
    check("…a name of two people (Cy Namesake) keeps the whole line apart: Gus is not joined from it",
          ids["gus"] not in got, labels(ops))
    check("…a part that names nobody (Ann Other) keeps the whole line one item: no Fay from it, no Ann",
          item(ops, FAY, env.reg) is not None and "Ann Other" not in " ".join(labels(ops))
          and not any("Support" in r["text"] for r in item(ops, FAY, env.reg)["rows"]), item(ops, FAY, env.reg))
    fay = item(ops, FAY, env.reg) or {}
    check("…a joined part keeps its line's text as its row", any("Fay Four, Bea Two" in r["text"] for r in fay.get("rows", [])),
          fay)

with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    env.sctx = dict(env.sctx, repos=[r for r in env.sctx["repos"] if r.get("id") != "zorg-core"])
    role = env.slots(RHEA_OWN, only=["person.role"]).get("person.role") or {}
    gus_team = env.slots(GUS, only=["person.role"])
    r = es.candidates(env.reg, env.idx, env.reg.of(RHEA_OWN), "person.role", env.cat, env.sctx)
    core = [c for c in r if c["source"] == "zorg-core"]
    check("v3.20.0 a card of a repository whose registration gives no rank takes its level in the cascade (after the "
          "ranked repositories, before a local index), never «реєстрацію не прочитано»",
          core and all(c["rank"] is not None for c in core)
          and rv.resolve("person.role", env.cat, [dict(c) for c in core] + [cand("local", "zorg-brain", "B")], None)["shown"][0]
          ["source"] == "zorg-core", core)

print("RESULT:", "GREEN ✅" if not fails else "RED ❌")
sys.exit(1 if fails else 0)
