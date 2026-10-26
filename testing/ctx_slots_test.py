#!/usr/bin/env python3
"""TC-ctx-3150-slots — scripts/ctx_slots.py: the catalogue of slots and the memory of what you decided (since v3.15.0).

references/context-slots.yaml names the places in a record where an answer to a question lives; this checks
the catalogue loads, is clean, finds a slot by the name a manifest or a person uses, and says what is wrong
with a bad one. The memory (`.state/slots.json` of the store: your bindings, your names, your preference, your
answers) is read and written here: an absent file is an empty memory, an unreadable or foreign one is a StoreError,
a repeated bind or map adds nothing. Fictional names only ("Zorg"). Stdlib only; run from the repo root.
"""
import json, os, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import ctx_slots as sl  # noqa: E402
import ctx_store as cs  # noqa: E402

fails = 0


def check(name, cond, detail=""):
    global fails
    fails += not cond
    print(("✅" if cond else "❌"), name, ("" if cond else "-> " + str(detail)[:600]))


def one(slot_id="product.x", **kw):
    """A catalogue of one slot, with the parts `kw` changes."""
    s = {"kind": "text", "record": "product", "names": ["X"], "about": "x"}
    s.update(kw)
    return {"slots": {slot_id: s}}


cat = sl.load_catalogue()
check("the repo catalogue is clean", sl.check_catalogue(cat) == [], sl.check_catalogue(cat))
check("the catalogue sits where the plugin keeps its references", sl.CATALOGUE_PATH == os.path.join(ROOT, "references", "context-slots.yaml")
      and os.path.isfile(sl.CATALOGUE_PATH), sl.CATALOGUE_PATH)
check("the catalogue states its schema", cat.get("schema") == "context-slots/1", cat.get("schema"))
check("a manifest name finds its slot, case-insensitive", sl.slot_for(cat, "team", "members") == "team.members"
      and sl.slot_for(cat, "team", "Team Members") == "team.members" and sl.slot_for(cat, "product", "Members") is None)
check("the Ukrainian names find their slots too", sl.slot_for(cat, "team", "Склад команди") == "team.members"
      and sl.slot_for(cat, "product", "ключові метрики") == "product.key_metrics"
      and sl.slot_for(cat, "org", "Метрики компанії") == "org.key_metrics", "")
check("the same name in another record is another slot", sl.slot_for(cat, "product", "Key Metrics") == "product.key_metrics"
      and sl.slot_for(cat, "org", "Company Metrics") == "org.key_metrics" and sl.slot_for(cat, "org", "Key Metrics") is None, "")
check("a name with nothing behind it finds no slot", sl.slot_for(cat, "product", "Nowhere") is None
      and sl.slot_for(cat, "no-such-record", "Description") is None and sl.slot_for(cat, "product", "") is None, "")
check("a manifest field name that is not a heading text still finds its slot", sl.slot_for(cat, "product", "jira_project_key") == "product.jira_key"
      and sl.slot_for(cat, "product", "Jira Project Key") == "product.jira_key", "")

want = {"product.description": "value", "product.url": "value", "product.jira_key": "value", "product.confluence_space": "value",
        "product.confluence_template_name": "value", "product.confluence_template_url": "value", "product.platforms": "list",
        "product.locales": "list", "product.key_metrics": "text", "product.okrs": "text", "product.competitors": "list",
        "product.analytics_dashboards": "text", "product.design_system": "text", "product.test_accounts": "text",
        "product.scope": "text", "team.jira_team_id": "value", "team.members": "list", "profile.email": "value",
        "org.key_metrics": "text", "org.data_sources": "text", "org.structure": "text", "org.people_rules": "text",
        "person.role": "value", "person.team": "value", "person.email": "value", "team.missions": "list",
        "team.parent": "value", "mission.teams": "list", "mission.jira_projects": "list", "module.owner": "value",
        "metric.owner": "value"}           # v3.18.1: the slots of an entity's cards (plan R2, C1)
got = {k: v.get("kind") for k, v in (cat.get("slots") or {}).items()}
check("the catalogue holds the 22 slots of the plan and the 9 of the cards (v3.18.1), with their kinds", got == want, (sorted(set(want) ^ set(got)), [k for k in want if got.get(k) != want[k]]))
check("every slot says what it holds, in one line", all(isinstance(s.get("about"), str) and s["about"].strip() and "\n" not in s["about"]
                                                           for s in cat["slots"].values()), "")
check("team.members is described in the plan's words", cat["slots"]["team.members"]["about"] == "склад команди: люди, ролі, контакти"
      and cat["slots"]["org.key_metrics"]["about"] == "метрики компанії: виручка, обсяги, бізнес-план", "")

# --- a bad catalogue is named
errs = sl.check_catalogue(one(kind="blob"))
check("a bad slot is named", any("kind" in e for e in errs) and any("product.x" in e for e in errs), errs)
check("a bad kind is not what a good one gets", sl.check_catalogue(one(kind="value")) == [] and sl.check_catalogue(one(kind="list")) == []
      and sl.check_catalogue(one(kind="text")) == [], "")
errs = sl.check_catalogue(one(record="bogus"))
check("a bad record is named", any("record" in e for e in errs), errs)
errs = sl.check_catalogue(one(slot_id="team.x"))
check("an id must start with its record", any("team.x" in e and "product" in e for e in errs), errs)
check("an id with nothing after the record is bad", any("product." in e for e in sl.check_catalogue(one(slot_id="product."))), "")
check("an id that names no record is bad", sl.check_catalogue(one(slot_id="x")) != [], "")
errs = sl.check_catalogue(one(names=[]))
check("a slot with no names is named", any("names" in e for e in errs), errs)
check("a slot whose names is no list is named", any("names" in e for e in sl.check_catalogue(one(names="X"))), "")
check("a blank name is named", any("names" in e for e in sl.check_catalogue(one(names=["X", " "]))), "")
errs = sl.check_catalogue(one(about=""))
check("a slot with no about is named", any("about" in e for e in errs), errs)
check("a slot with no about key is named", any("about" in e for e in sl.check_catalogue({"slots": {"product.x": {"kind": "text", "record": "product", "names": ["X"]}}})), "")
check("a schema that is not context-slots/1 is named, a missing one is not", any("schema" in e for e in sl.check_catalogue(dict(one(), schema="context-slots/9")))
      and sl.check_catalogue(dict(one(), schema="context-slots/1")) == [], "")
check("an empty catalogue is no catalogue", sl.check_catalogue({}) != [] and sl.check_catalogue({"slots": {}}) != [], "")
check("a slot that is no mapping is named", any("product.x" in e for e in sl.check_catalogue({"slots": {"product.x": "x"}})), "")

# --- ruling P1: a name two slots of one record share would make slot_for ambiguous
two = {"slots": {"product.a": {"kind": "text", "record": "product", "names": ["Shared", "A"], "about": "a"},
                 "product.b": {"kind": "text", "record": "product", "names": ["shared"], "about": "b"}}}
errs = sl.check_catalogue(two)
check("a name two slots of one record share is named (case-insensitive)", any("shared" in e.lower() and "product.a" in e and "product.b" in e for e in errs), errs)
other = {"slots": {"product.a": {"kind": "text", "record": "product", "names": ["Shared"], "about": "a"},
                   "team.b": {"kind": "text", "record": "team", "names": ["Shared"], "about": "b"}}}
check("…but the same name in two records is fine", sl.check_catalogue(other) == [], sl.check_catalogue(other))
dup = {"slots": {"product.a": {"kind": "text", "record": "product", "names": ["Same", "same"], "about": "a"}}}
check("a name twice in one slot is not a clash between slots", sl.check_catalogue(dup) == [], sl.check_catalogue(dup))

# --- load_catalogue reads a file, and names what is wrong with one
with tempfile.TemporaryDirectory() as d:
    p = os.path.join(d, "slots.yaml")
    open(p, "w", encoding="utf-8").write("schema: context-slots/1\nslots:\n  product.zorg:\n    kind: value\n    record: product\n"
                                         "    names:\n      - Zorg Field\n    about: поле Zorg\n")
    mine = sl.load_catalogue(p)
    check("load_catalogue reads another path", sl.slot_for(mine, "product", "zorg field") == "product.zorg" and sl.check_catalogue(mine) == [], mine)
    open(p, "w", encoding="utf-8").write("slots: [not, a, block]\n")
    try:
        sl.load_catalogue(p); bad = None
    except ValueError as e:
        bad = str(e)
    check("a file that is not the YAML we read is a ValueError", bad is not None and "unsupported YAML" in bad, bad)
    try:
        sl.load_catalogue(os.path.join(d, "nope.yaml")); gone = None
    except ValueError as e:
        gone = str(e)
    check("a file that cannot be read is a ValueError too", gone is not None and "nope.yaml" in gone, gone)

# --- the memory: .state/slots.json of the store
EMPTY = {"schema": "context-slots-memory/1", "bindings": [], "aliases": [], "prefer": {}, "decisions": {}}
check("the memory states its schema", sl.MEMORY_SCHEMA == "context-slots-memory/1", sl.MEMORY_SCHEMA)


def bad_memory(d, text):
    """What load_memory says about a slots.json holding `text` (None: it loaded)."""
    store = cs.Store(os.path.join(d, "context"))
    os.makedirs(store.state_dir, exist_ok=True)
    open(os.path.join(store.state_dir, "slots.json"), "w", encoding="utf-8").write(text)
    try:
        sl.load_memory(store)
        return None
    except cs.StoreError as e:
        return str(e)


with tempfile.TemporaryDirectory() as d:
    store = cs.Store(os.path.join(d, "context"))
    os.makedirs(store.state_dir)
    path = os.path.join(store.state_dir, "slots.json")
    check("no file is an empty memory", sl.load_memory(store) == EMPTY and not os.path.exists(path), sl.load_memory(store))
    mem = sl.load_memory(store)
    check("a bind adds a binding, and says so", sl.add_binding(mem, "zorg-core", "team", "Members", "team.members", None) is True
          and mem["bindings"] == [{"repo": "zorg-core", "block": "team", "sub": "Members", "slot": "team.members", "team": None}], mem)
    check("…the same bind again adds nothing", sl.add_binding(mem, "zorg-core", "team", "Members", "team.members", None) is False
          and len(mem["bindings"]) == 1, mem)
    check("…another subsection, another slot, or the whole block is another binding",
          sl.add_binding(mem, "zorg-core", "team", None, "team.members", None) and sl.add_binding(mem, "zorg-core", "team", "Members", "org.structure", None)
          and sl.add_binding(mem, "zorg-growth", "team", "Members", "team.members", None) and len(mem["bindings"]) == 4, mem)
    check("a repeat that names the team sets the team of that binding, not a second binding",
          sl.add_binding(mem, "zorg-core", "team", "Members", "team.members", "team.alpha") is True
          and sl.add_binding(mem, "zorg-core", "team", "Members", "team.members", "team.alpha") is False
          and [b["team"] for b in mem["bindings"] if b["repo"] == "zorg-core" and b["sub"] == "Members" and b["slot"] == "team.members"] == ["team.alpha"]
          and len(mem["bindings"]) == 4, mem)
    check("a map adds a name once, whatever its case or spacing",
          sl.add_alias(mem, "product.zorg-app", "Key Metrics (focus)", "product.key_metrics") is True
          and sl.add_alias(mem, "product.zorg-app", "key  metrics (FOCUS)", "product.key_metrics") is False
          and sl.add_alias(mem, "product.zorg-app", "Key Metrics (focus)", "product.okrs") is True
          and sl.add_alias(mem, "product.other", "Key Metrics (focus)", "product.key_metrics") is True and len(mem["aliases"]) == 3, mem)
    check("a preference is set once; a different one replaces it",
          sl.set_prefer(mem, "team.members", "all") is True and sl.set_prefer(mem, "team.members", "all") is False
          and sl.set_prefer(mem, "team.members", "repo:zorg-core") is True and mem["prefer"] == {"team.members": "repo:zorg-core"}, mem)
    mem["decisions"]["team.members"] = {"winner": "zorg-core", "hashes": {"zorg-core": "a" * 64, "zorg-growth": "b" * 64}}
    sl.save_memory(store, mem)
    text = open(path, encoding="utf-8").read()
    check("save_memory writes JSON with an indent, sorted, ending in a newline, and leaves no temp file",
          text.endswith("}\n") and "\n " in text and json.loads(text)["schema"] == sl.MEMORY_SCHEMA
          and not [n for n in os.listdir(store.state_dir) if n.endswith(".tmp")], text[:300])
    again = sl.load_memory(store)
    check("the memory reads back as it was saved", again["prefer"] == mem["prefer"] and again["decisions"] == mem["decisions"]
          and len(again["bindings"]) == 4 and len(again["aliases"]) == 3, again)
    check("…bindings and names come back in a fixed order, whatever order they were added in",
          [(b["repo"], b["block"], b["sub"] or "", b["slot"]) for b in again["bindings"]] == sorted(
              (b["repo"], b["block"], b["sub"] or "", b["slot"]) for b in again["bindings"])
          and [(a["record"], a["slot"]) for a in again["aliases"]] == sorted((a["record"], a["slot"]) for a in again["aliases"]), again)
    sl.save_memory(store, again)
    check("saving what was read changes nothing", open(path, encoding="utf-8").read() == text)
    dup = json.loads(text)
    dup["bindings"] = dup["bindings"] + dup["bindings"]
    dup["aliases"] = dup["aliases"] + dup["aliases"]
    open(path, "w", encoding="utf-8").write(json.dumps(dup))
    sl.save_memory(store, sl.load_memory(store))
    check("a file with a record twice is saved with it once", open(path, encoding="utf-8").read() == text)
    two = {"schema": sl.MEMORY_SCHEMA, "bindings": [
        {"repo": "zorg-core", "block": "team", "sub": "Members", "slot": "team.members", "team": "team.alpha"},
        {"repo": "zorg-core", "block": "team", "sub": "Members", "slot": "team.members", "team": "team.beta"},
        {"repo": "zorg-core", "block": "team", "sub": "Members", "slot": "team.members", "team": None}]}
    open(path, "w", encoding="utf-8").write(json.dumps(two))
    check("a binding is one per (repo, block, sub, slot): the first team is kept, the others dropped",
          sl.load_memory(store)["bindings"] == [{"repo": "zorg-core", "block": "team", "sub": "Members", "slot": "team.members",
                                                 "team": "team.alpha"}], sl.load_memory(store)["bindings"])
    sl.save_memory(store, again)
    check("forget takes everything about a slot, and nothing about another",
          sl.drop_slot(mem, "team.members") is True and not [b for b in mem["bindings"] if b["slot"] == "team.members"]
          and "team.members" not in mem["prefer"] and "team.members" not in mem["decisions"]
          and [b["slot"] for b in mem["bindings"]] == ["org.structure"] and len(mem["aliases"]) == 3, mem)
    check("…a slot the memory knows nothing of is nothing to forget", sl.drop_slot(mem, "team.members") is False
          and sl.drop_slot(mem, "product.okrs") is True and [a["slot"] for a in mem["aliases"]].count("product.okrs") == 0, mem)
    check("in_memory says whether a slot is anywhere in the memory", sl.in_memory(mem, "org.structure") is True
          and sl.in_memory(mem, "team.members") is False and sl.in_memory(again, "team.members") is True, mem)

with tempfile.TemporaryDirectory() as d:
    why = bad_memory(d, "{ not json")
    check("a file that is not JSON is a StoreError that names the file", why is not None
          and why.startswith("slots memory not valid: .state/slots.json ("), why)
with tempfile.TemporaryDirectory() as d:
    store = cs.Store(os.path.join(d, "context"))
    os.makedirs(os.path.join(store.state_dir, "slots.json"))
    try:
        sl.load_memory(store); why = None
    except cs.StoreError as e:
        why = str(e)
    check("a file that cannot be read is a StoreError that names the file", why is not None
          and why.startswith("slots memory not readable: .state/slots.json ("), why)
for label, doc in (("another schema", {"schema": "context-slots-memory/9"}), ("no schema", {"bindings": []}),
                   ("not an object", ["schema"]), ("bindings that are no list", {"schema": sl.MEMORY_SCHEMA, "bindings": {}}),
                   ("a binding with no repo", {"schema": sl.MEMORY_SCHEMA, "bindings": [{"block": "team", "slot": "team.members"}]}),
                   ("a binding that is no object", {"schema": sl.MEMORY_SCHEMA, "bindings": ["team"]}),
                   ("a binding whose sub is a number", {"schema": sl.MEMORY_SCHEMA, "bindings": [{"repo": "r", "block": "b", "slot": "s", "sub": 3}]}),
                   ("a name with no heading", {"schema": sl.MEMORY_SCHEMA, "aliases": [{"record": "product.x", "slot": "product.okrs"}]}),
                   ("a preference that is none of the three", {"schema": sl.MEMORY_SCHEMA, "prefer": {"team.members": "theirs"}}),
                   ("a preference for a repository with no id", {"schema": sl.MEMORY_SCHEMA, "prefer": {"team.members": "repo:"}}),
                   ("prefer that is no object", {"schema": sl.MEMORY_SCHEMA, "prefer": []}),
                   ("a decision with no winner", {"schema": sl.MEMORY_SCHEMA, "decisions": {"team.members": {"hashes": {}}}}),
                   ("a decision whose hashes are no object", {"schema": sl.MEMORY_SCHEMA, "decisions": {"team.members": {"winner": "r", "hashes": []}}}),
                   ("a decision whose date is no date", {"schema": sl.MEMORY_SCHEMA, "decisions": {"team.members": {"winner": "r", "hashes": {}, "at": "yesterday"}}}),
                   ("a decision with a key nobody knows", {"schema": sl.MEMORY_SCHEMA, "decisions": {"team.members": {"winner": "r", "hashes": {}, "by": "me"}}}),
                   ("a key nobody knows", {"schema": sl.MEMORY_SCHEMA, "extra": 1})):
    with tempfile.TemporaryDirectory() as d:
        why = bad_memory(d, json.dumps(doc))
        check("%s is a StoreError that names the file" % label, why is not None and why.startswith("slots memory not valid: .state/slots.json ("), why)
with tempfile.TemporaryDirectory() as d:
    why = bad_memory(d, json.dumps({"schema": sl.MEMORY_SCHEMA, "decisions": {
        "team.members": {"winner": "zorg-core", "hashes": {"zorg-core": "a" * 64}, "at": "2026-10-20"},
        "product.scope": {"winner": "zorg-core", "hashes": {"zorg-core": "a" * 64}}}}))
    again = sl.load_memory(cs.Store(os.path.join(d, "context"))) if why is None else None
    check("a decision may carry the day it was taken (at, YYYY-MM-DD); one without it is as valid", why is None
          and again["decisions"]["team.members"]["at"] == "2026-10-20" and "at" not in again["decisions"]["product.scope"], (why, again))
with tempfile.TemporaryDirectory() as d:
    why = bad_memory(d, json.dumps({"schema": sl.MEMORY_SCHEMA}))
    store = cs.Store(os.path.join(d, "context"))
    check("a file that holds only its schema is an empty memory", why is None and sl.load_memory(store) == EMPTY, why)
    path = os.path.join(store.state_dir, "slots.json")
    before = open(path, encoding="utf-8").read()
    bad = dict(EMPTY, prefer={"team.members": "theirs"})
    try:
        sl.save_memory(store, bad); why = None
    except cs.StoreError as e:
        why = str(e)
    check("a memory of the wrong form is not saved, and the file stays", why is not None and "slots memory" in why
          and open(path, encoding="utf-8").read() == before, why)

# --- v3.18.1 Task 1: the slots of an entity's cards (plan C1, C1a)
ons = {k: (v.get("answered_on") or "records") for k, v in cat["slots"].items()}
check("v3.18.1 the cards' own slots say `answered_on: cards`, team.members `answered_on: both`, the rest are the records' (C1a)",
      ons["person.role"] == ons["team.missions"] == ons["team.parent"] == ons["mission.teams"] == ons["metric.owner"] == "cards"
      and ons["team.members"] == "both" and ons["product.url"] == ons["team.jira_team_id"] == "records", ons)
check("v3.18.1 a card-only slot is no record's: slot_for and slot_info do not see it, the records' slots do not list it",
      sl.slot_for(cat, "team", "missions") is None and sl.slot_info(cat, "person.role") is None
      and "team.parent" not in sl.record_slots(cat) and "team.members" in sl.record_slots(cat), "")
check("v3.18.1 card_slot_for finds a card's slot by a field or heading name — `position`, «Посада», `jira_projects`, and the "
      "card-only names of team.members («Люди», «Склад»), which no record answers to",
      sl.card_slot_for(cat, "person", "position") == "person.role" and sl.card_slot_for(cat, "person", "Посада") == "person.role"
      and sl.card_slot_for(cat, "mission", "jira_projects") == "mission.jira_projects"
      and sl.card_slot_for(cat, "team", "Люди") == "team.members" and sl.card_slot_for(cat, "team", "Склад") == "team.members"
      and sl.card_slot_for(cat, "team", "members") == "team.members" and sl.slot_for(cat, "team", "Люди") is None
      and sl.card_slot_for(cat, "team", "Jira Team ID") is None and sl.card_slot_for(cat, "work", "owner") is None, "")
check("v3.18.1 card_slots: the slots of a kind of card, in the catalogue's order",
      sl.card_slots(cat, "person") == ["person.role", "person.team", "person.email"]
      and sl.card_slots(cat, "team") == ["team.members", "team.missions", "team.parent"] and sl.card_slots(cat, "work") == [], "")
errs = sl.check_catalogue({"schema": sl.SCHEMA, "slots": {
    "person.x": {"kind": "value", "record": "person", "names": ["X"], "about": "x"},
    "person.y": {"kind": "value", "record": "person", "answered_on": "cards", "names": ["Y"], "card_names": ["Job_role"], "about": "y"},
    "person.w": {"kind": "value", "record": "person", "answered_on": "cards", "names": ["job role"], "about": "w"},
    "team.z": {"kind": "list", "record": "team", "answered_on": "sometimes", "names": ["Z"], "card_names": "Q", "about": "z"}}})
check("v3.18.1 check_catalogue: a card kind is a record only for `on: cards`; `answered_on` is records|cards|both; card_names is a "
      "list; a card name two slots of a kind share is named",
      any("person.x" in e and "record" in e for e in errs) and any("team.z" in e and "answered_on" in e for e in errs)
      and any("team.z" in e and "card_names" in e for e in errs) and any("person.y" in e and "person.w" in e for e in errs), errs)

PINNED_CARD_NAMES = (1, "3d69b30c8de81216a1efb9f2d11a8471c6808fa1")     # (card_names_version, card_names_digest): change the names, raise the version
check("v3.18.1 Task 1 review I1: the card names are pinned to card_names_version — names or kinds of a card slot changed "
      "without raising the version (so the index would not read the cards again) fail here",
      (sl.card_names_version(cat), sl.card_names_digest(cat)) == PINNED_CARD_NAMES,
      (sl.card_names_version(cat), sl.card_names_digest(cat)))
check("…check_catalogue names a card_names_version that is no whole number from 1",
      any("card_names_version" in e for e in sl.check_catalogue(dict(cat, card_names_version="two")))
      and any("card_names_version" in e for e in sl.check_catalogue(dict(cat, card_names_version=0)))
      and sl.check_catalogue(dict(cat, card_names_version=3)) == [], "")

print("RESULT:", "GREEN ✅" if not fails else "RED ❌", "(%d failed)" % fails)
sys.exit(1 if fails else 0)
