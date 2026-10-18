#!/usr/bin/env python3
"""TC-ctx-3150-slots — scripts/ctx_slots.py: the catalogue of slots (since v3.15.0).

references/context-slots.yaml names the places in a record where an answer to a question lives; this checks
the catalogue loads, is clean, finds a slot by the name a manifest or a person uses, and says what is wrong
with a bad one. Fictional names only ("Zorg"). Stdlib only; run from the repo root.
"""
import os, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import ctx_slots as sl  # noqa: E402

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
        "org.key_metrics": "text", "org.data_sources": "text", "org.structure": "text", "org.people_rules": "text"}
got = {k: v.get("kind") for k, v in (cat.get("slots") or {}).items()}
check("the catalogue holds the 22 slots of the plan, with their kinds", got == want, (sorted(set(want) ^ set(got)), [k for k in want if got.get(k) != want[k]]))
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

print("RESULT:", "GREEN ✅" if not fails else "RED ❌", "(%d failed)" % fails)
sys.exit(1 if fails else 0)
