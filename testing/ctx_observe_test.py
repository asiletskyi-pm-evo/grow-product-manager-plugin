#!/usr/bin/env python3
"""TC-ctx-3220-observe — scripts/ctx_observe.py, the observation file a skill hands to ctx (v3.22.0, plan C2–C4, C15).

The fictional observation file (testing/fixtures/bootstrap/observed-zorg.json): the shape it must have; the confidence
ctx decides from where a fact came (a skill cannot pass one); the thresholds of activity, equal in the code and in
references/context-observe.md; the facts dropped — below a threshold, from a connector that did not answer, holding a
secret; and nothing of a meeting or a mail kept — the title of a 1-1 and the subject of a letter appear nowhere.
Stdlib only; run from the repo root:

  env -u GROW_PM_CONTEXT_PATH -u GROW_PM_PROVIDER_PATHS python3 testing/ctx_observe_test.py
"""
import copy, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import ctx_observe as cob  # noqa: E402

FIX = os.path.join(ROOT, "testing", "fixtures", "bootstrap", "observed-zorg.json")
fails = 0


def check(name, cond, detail=""):
    global fails
    fails += not cond
    print(("✅" if cond else "❌"), name, ("" if cond else "-> " + str(detail)[:900]))


def raw():
    return json.load(open(FIX, encoding="utf-8"))


def parse(obj):
    return cob.parse(json.loads(json.dumps(obj)))


# ------------------------------------------------------------------ 1. the file and its facts
obs = parse(raw())
facts, dropped = obs["facts"], obs["dropped"]
by = {(f["type"], f.get("title"), f.get("field") or f.get("list"), f["value"]): f for f in facts}

check("1.1 the fixture parses; every fact carries the confidence ctx gave it",
      facts and all(f["confidence"] in cob.LEVELS for f in facts), facts)
check("1.2 high: who you are (atlassian:user), the site, the mail's domain",
      by[("profile", None, "Name", "Alex One")]["confidence"] == "high"
      and by[("org", "Zorg", "Jira", "https://zorg.atlassian.example")]["confidence"] == "high"
      and by[("org", "Zorg", "Domain", "zorg.example")]["confidence"] == "high")
check("1.3 medium: your activity in Jira and Confluence; the role a provider infers",
      by[("product", "Zorg App", "Jira Project Key", "PROJ")]["confidence"] == "medium"
      and by[("product", "Zorg App", "Confluence Space", "ZAPP")]["confidence"] == "medium"
      and by[("profile", None, "Role", "pm")]["confidence"] == "medium")
check("1.4 high: the team a provider knows your mail in", by[("team", "Alpha (A)", None, "")]["confidence"] == "high",
      [f for f in facts if f["type"] == "team"])
check("1.5 low: co-attendees, Tableau",
      by[("team", "Alpha (A)", "Members", "Cid Three")]["confidence"] == "low"
      and by[("product", "Zorg App", "Dashboards",
              "Zorg funnel — https://tableau.zorg.example/views/funnel")]["confidence"] == "low")
check("1.6 below the threshold → dropped, with why: ADS (2 tasks), Dee Four (1 meeting)",
      not any(f["value"] in ("ADS", "Dee Four") for f in facts)
      and sum(1 for d in dropped if "порог" in d["why"]) == 2, dropped)

# ------------------------------------------------------------------ 2. nothing of a meeting or a mail
text = json.dumps(obs, ensure_ascii=False)
check("2.1 a calendar fact keeps no evidence: the 1-1's title is nowhere", "звільнення" not in text and "1-1 Cid" not in text)
check("2.2 a mail fact keeps no ref: the letter's subject is nowhere", "bonus" not in text)
check("2.3 what stays of them is a count ctx words itself",
      by[("team", "Alpha (A)", "Members", "Cid Three")]["ref"] == "6 спільних зустрічей за 30 днів",
      by[("team", "Alpha (A)", "Members", "Cid Three")])

for name, fact in (("a 1-1's title as a co-attendee's value",
                    {"type": "team", "title": "Alpha (A)", "list": "Members", "value": "1-1 Cid: розмова про звільнення",
                     "from": "calendar:co-attendee", "count": 5}),
                   ("a sentence as a co-attendee's name",
                    {"type": "team", "title": "Alpha (A)", "list": "Members", "value": "Розмова про звільнення",
                     "from": "calendar:co-attendee", "count": 5}),
                   ("a meeting's title as a product's field",
                    {"type": "product", "title": "Zorg App", "field": "Description", "value": "1-1 Cid",
                     "from": "calendar:co-attendee", "count": 5}),
                   ("a letter's subject as the domain", {"type": "org", "title": "Zorg", "field": "Domain",
                                                         "value": "Re: quarterly bonus for Bea", "from": "mail:domain"}),
                   ("a letter's subject as the organisation's name",
                    {"type": "org", "title": "Quarterly bonus", "field": "Domain", "value": "zorg.example",
                     "from": "mail:domain"}),
                   ("an e-mail from Jira activity", {"type": "profile", "field": "Email", "value": "x@zorg.example",
                                                     "from": "jira:active", "count": 9}),
                   ("a value on a fact about the record itself",
                    {"type": "team", "title": "Alpha (A)", "value": "anything", "from": "provider:identity"}),
                   ("a key that is no key", {"type": "product", "title": "Zorg App", "field": "Jira Project Key",
                                             "value": "the zorg project", "from": "jira:active", "count": 9}),
                   ("a dashboard with no link", {"type": "product", "title": "Zorg App", "list": "Dashboards",
                                                 "value": "Zorg funnel", "from": "tableau:owned"}),
                   ("a line break U+2028", {"type": "product", "title": "Zorg App", "field": "URL",
                                            "value": "https://x.example\u2028### Product: Evil", "from": "user"}),
                   ("a list as from", {"type": "profile", "field": "Name", "value": "X", "from": ["user"]})):
    r = raw()
    r["facts"] = [fact]
    o = parse(r)
    check("2.x dropped, the text nowhere: %s" % name, not o["facts"] and len(o["dropped"]) == 1
          and not any(w in json.dumps(o, ensure_ascii=False) for w in ("звільнення", "bonus", "Evil")), o)
r = raw()
r["facts"] = [{"type": "team", "title": "Alpha (A)", "list": "Members", "value": "Cid Three",
               "from": "calendar:co-attendee", "count": 5, "evidence": "x" * 300}]
check("2.y a quiet fact's long evidence is dropped, not the fact", len(parse(r)["facts"]) == 1, parse(r))
r = raw()
r["facts"] = [{"type": "profile", "field": "Name", "value": "X", "from": "user", "evidence": "x" * 201}]
check("2.z an evidence of 201 characters drops the fact", not parse(r)["facts"], parse(r))
r = raw()
r["connectors"]["calendar"] = "errored-but-fine"
try:
    parse(r)
    ok = False
except ValueError:
    ok = True
check("2.w a connector status is ok, absent, error or error: …", ok)

# ------------------------------------------------------------------ 3. the skill cannot decide what ctx decides
r = raw()
r["facts"][0]["confidence"] = "high"
o = parse(r)
check("3.1 a fact that brings its own confidence is refused, the others kept",
      any("певність" in d["why"] for d in o["dropped"]) and len(o["facts"]) == len(facts) - 1, o["dropped"])
r = raw()
r["facts"][5]["from"] = "jira:guess"
o = parse(r)
check("3.2 an unknown source is refused", any("from" in d["why"] for d in o["dropped"]), o["dropped"])
r = raw()
r["connectors"]["atlassian"] = "absent"
o = parse(r)
check("3.3 a fact from a connector that did not answer is refused (atlassian absent → no Jira, Confluence, user, site)",
      not any(f["from"].split(":")[0] in ("atlassian", "jira", "confluence") for f in o["facts"])
      and any("не відповів" in d["why"] for d in o["dropped"]), o["facts"])
r = raw()
r["connectors"]["mail"] = "absent"
o = parse(r)
check("3.3b the mail's domain from Atlassian's address: kept when atlassian answered and mail did not",
      any(f["from"] == "mail:domain" for f in o["facts"]), o["dropped"])
r["connectors"]["atlassian"] = "absent"
o = parse(r)
check("3.3c … dropped when neither answered", not any(f["from"] == "mail:domain" for f in o["facts"]), o["facts"])
r = raw()
r["facts"].append({"type": "product", "title": "Zorg App", "field": "URL", "value": "https://ci.zorg.example/?token=ghp_"
                   + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8", "from": "user"})
o = parse(r)
check("3.4 a secret in a value → the fact dropped, the kind named, the value nowhere",
      any("секрет" in d["why"] for d in o["dropped"]) and "ghp_" not in json.dumps(o), o["dropped"])

# ------------------------------------------------------------------ 4. the shape
for name, mutate in (("schema", lambda r: r.update(schema="context-observed/2")),
                     ("unknown top key", lambda r: r.update(extra=1)),
                     ("connectors not an object", lambda r: r.update(connectors=[])),
                     ("connector status", lambda r: r["connectors"].update(calendar="maybe")),
                     ("unknown connector", lambda r: r["connectors"].update(slack="ok")),
                     ("checks of another shape", lambda r: r["checks"].update({"jira:visible": {"values": "PROJ"}})),
                     ("unknown check", lambda r: r["checks"].update({"slack:people": {}}))):
    r = raw()
    mutate(r)
    try:
        parse(r)
        ok = False
    except ValueError:
        ok = True
    check("4.x the file is refused whole: %s" % name, ok)
for name, fact in (("no type", {"field": "Name", "value": "x", "from": "user"}),
                   ("a team with no title", {"type": "team", "from": "user"}),
                   ("field and list", {"type": "profile", "field": "Name", "list": "X", "value": "x", "from": "user"}),
                   ("two lines", {"type": "profile", "field": "Name", "value": "a\nb", "from": "user"}),
                   ("a heading as a value", {"type": "product", "title": "Z", "list": "Dashboards", "value": "## x",
                                             "from": "user"}),
                   ("a region marker", {"type": "profile", "field": "Name", "value": "<!-- ns:end x -->", "from": "user"}),
                   ("an unknown key", {"type": "profile", "field": "Name", "value": "x", "from": "user", "why": "z"}),
                   ("a count that is no number", {"type": "product", "title": "Z", "field": "Jira Project Key",
                                                  "value": "Z", "from": "jira:active", "count": "many"})):
    r = raw()
    r["facts"] = [fact]
    o = parse(r)
    check("4.y a fact is dropped, the file kept: %s" % name, not o["facts"] and len(o["dropped"]) == 1, o)

checks = obs["checks"]
check("4.9 checks: keys and names normalised; complete kept",
      checks["jira:visible"]["complete"] is True and checks["jira:visible"]["values"][0] == {"key": "PROJ", "name": "Zorg App"}
      and checks["confluence:visible"]["values"] == [{"key": "ZAPP", "name": None}]
      and checks["atlassian:people"]["inactive"] == ["Bea Two"], checks)
r = raw()
del r["checks"]["jira:visible"]["complete"]
check("4.10 a check that does not say it is complete is not complete", parse(r)["checks"]["jira:visible"]["complete"] is False)

# ------------------------------------------------------------------ 5. the thresholds: the code and the document agree
doc = open(os.path.join(ROOT, "references", "context-observe.md"), encoding="utf-8").read()
for kind, n in cob.MIN_COUNT.items():
    check("5.x the document states the threshold of %s as %d" % (kind, n),
          re.search(r"`%s`[^\n]*≥ %d\b" % (re.escape(kind), n), doc), kind)
for f in cob.FROM:
    check("5.y the document names the source %s and its confidence" % f, ("`%s`" % f) in doc)
check("5.z every source has a confidence", all(cob.level_of(f, None) in cob.LEVELS for f in cob.FROM))
LEVEL_WORD = {"high": "high", "medium": "medium", "low": "low"}
rows = {m.group(1): m.group(2) for m in re.finditer(r"^\| `([a-z:-]+)` \|.*\| ([a-z /]+) \|$", doc, re.M)}
for f in cob.FROM:
    want = {cob.level_of(f, None)} | ({cob.level_of(f, "Role")} if f == "provider:identity" else set())
    got = set(w.strip() for w in rows.get(f, "").split("/"))
    check("5.w the document's confidence of %s is the code's (%s)" % (f, ", ".join(sorted(want))), got == want,
          (f, rows.get(f)))
for f, allowed in cob.ALLOWED.items():
    line = next((l for l in doc.splitlines() if l.startswith("| `%s` |" % f)), "")
    for typ, what in allowed:
        word = (what or "").replace("list:", "")
        check("5.v the document's row of %s names what it may give: %s %s" % (f, typ, word or "(the record)"),
              (word in line) if word else True, line)

print("\nRESULT: %s (%d failed)" % ("GREEN ✅" if not fails else "RED ❌", fails))
sys.exit(1 if fails else 0)
