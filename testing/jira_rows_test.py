#!/usr/bin/env python3
"""TC-jira-4122 — scripts/jira_rows.py, a saved Jira response as compact rows (v4.12.2).

Atlassian MCP v2 moved an issue's custom fields from `fields.customfield_N` to `fields.customFields`, keyed by the
field's display name, and leaves a field with no value out. The patterns references/jira-data-protocol.md used to
`Grep -o` a saved search with matched nothing on v2, so a sprint report read every Story Point as missing. This test
keeps the reader honest on the fictional «Zorg» responses under testing/fixtures/jira/:

1. v2: every row, the custom fields by id, a user as {id, name}, the closed sprints as a count;
2. v1 gives the same rows for the same issues;
3. nothing of a person but the account id and the display name reaches a row; no description, no comment text;
4. the page line: the next page token, the shape, the names of the custom fields;
5. `--sprint-history`, one issue (getJiraIssue), stdin, several files;
6. a file that is not a Jira response is exit 2, never a crash and never an empty report;
7. the protocol names the script and the v2 shape, and its no-shell patterns match the v2 fixture.
Mutations: a reader that looks only at `fields.customfield_N` (the v4.11.0 behaviour), and one that keeps the user
object whole, are each caught. Stdlib only; run from the repo root:

  python3 testing/jira_rows_test.py
"""
import importlib.util, json, os, re, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "jira_rows.py")
FIX = os.path.join(ROOT, "testing", "fixtures", "jira")

fails = 0


def check(name, cond, detail=""):
    global fails
    fails += not cond
    print(("✅" if cond else "❌"), name, ("" if cond else "-> " + str(detail)[:900]))


def load(path, name="jira_rows"):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run(*args, stdin=None):
    p = subprocess.run([sys.executable, SCRIPT] + list(args), input=stdin, capture_output=True, text=True)
    lines = [json.loads(l) for l in p.stdout.splitlines() if l.strip()]
    return p.returncode, [l for l in lines if "_page" not in l], [l["_page"] for l in lines if "_page" in l], p


def fixture(name):
    return open(os.path.join(FIX, name), encoding="utf-8").read()


check("0.1 scripts/jira_rows.py exists", os.path.exists(SCRIPT))
if not os.path.exists(SCRIPT):
    print("\nRESULT: RED ❌ (%d failed)" % fails)
    sys.exit(1)
jr = load(SCRIPT)

# 1. v2
code, rows, pages, p = run(os.path.join(FIX, "search-v2.json"))
by = {r["key"]: r for r in rows}
check("1.1 v2: exit 0, a row per issue, in the response's order", code == 0 and [r["key"] for r in rows] == ["PROJ-101", "PROJ-102", "PROJ-103"], (code, p.stderr))
a = by.get("PROJ-101", {})
check("1.2 the custom fields are read from fields.customFields, by id", a.get("cf", {}).get("customfield_10036") == 3
      and a["cf"].get("customfield_10014") == "PROJ-90" and a["cf"].get("customfield_10043") == "PROJ_101_PARCEL_LOCKER_AB", a.get("cf"))
check("1.3 a fraction of a Story Point stays a fraction", by.get("PROJ-102", {}).get("cf", {}).get("customfield_10036") == 0.5, by.get("PROJ-102"))
check("1.4 a user field is {id, name}", a["cf"].get("customfield_10041") == {"id": "acc-zorg-dev", "name": "Zorg Dev"}
      and a.get("assignee") == {"id": "acc-zorg-dev", "name": "Zorg Dev"}, (a["cf"].get("customfield_10041"), a.get("assignee")))
check("1.5 the Team field is {id, name}", a["cf"].get("customfield_10001") == {"id": "team-zorg-0001", "name": "Zorg Checkout"}, a["cf"].get("customfield_10001"))
check("1.6 closed sprints are a count, the sprints printed are the ones not closed", a.get("closed_sprints") == 2
      and a["cf"].get("customfield_10020") == [{"id": 902, "name": "Zorg sprint 12", "state": "active"}]
      and by["PROJ-102"].get("closed_sprints") == 0, (a.get("closed_sprints"), a["cf"].get("customfield_10020")))
check("1.7 the system fields: status and its category, type, resolved, versions, labels, components, parent",
      (a.get("status"), a.get("category"), a.get("type"), a.get("resolved", "")[:10], a.get("labels"), a.get("components"), a.get("parent"))
      == ("Closed", "done", "Task", "2026-11-25", ["checkout"], ["Cart"], "PROJ-90")
      and a.get("versions") == [{"name": "web: v2026.48", "releaseDate": "2026-11-27", "released": True}], a)
c = by.get("PROJ-103", {})
check("1.8 a field with no value has no key: no estimate, no assignee", c.get("cf") == {} and c.get("assignee") is None
      and c.get("closed_sprints") == 0, c)
check("1.9 a quote inside a summary survives", by["PROJ-102"].get("summary") == 'Кнопка "Оплатити" не реагує на другий дотик', by["PROJ-102"].get("summary"))

# 2. v1 reads the same
code1, rows1, pages1, p1 = run(os.path.join(FIX, "search-v1.json"))
by1 = {r["key"]: r for r in rows1}
check("2.1 v1: exit 0 and the shape is named", code1 == 0 and pages1 and pages1[0].get("shape") == "v1", (code1, pages1, p1.stderr))
check("2.2 v1 gives the same custom fields as v2 for the same issue",
      {k: v for k, v in a["cf"].items() if k != "customfield_10001"} == by1.get("PROJ-101", {}).get("cf"), by1.get("PROJ-101"))
check("2.3 a null on v1 is the absent key of v2", by1.get("PROJ-103", {}).get("cf") == {}
      and by1["PROJ-101"].get("closed_sprints") == 2, by1.get("PROJ-103"))

# 3. what never reaches a row
out = p.stdout + p1.stdout
check("3.1 no e-mail address, no avatar, no API link, no time zone", not re.search(r"@example\.com|avatars|rest/api|timeZone|accountType", out), out[:300])
check("3.2 no description and no comment text: comments are a count", "never print" not in out and a.get("comments") == 2
      and "description" not in a, a)

# 4. the page line
pg = pages[0] if pages else {}
check("4.1 the page: file, issues, shape, the next page token", (pg.get("file"), pg.get("issues"), pg.get("shape"), pg.get("has_next"),
      pg.get("next_page_token")) == ("search-v2.json", 3, "v2", True, "cursor-page-2"), pg)
check("4.2 the page names each custom field id (v2)", pg.get("cf_names", {}).get("customfield_10036") == "Story Points"
      and pg["cf_names"].get("customfield_10020") == "Sprint", pg.get("cf_names"))
check("4.3 the last page says so", pages1[0].get("has_next") is False and pages1[0].get("next_page_token") is None, pages1)

# 5. the other ways in
_, rows_h, _, _ = run(os.path.join(FIX, "search-v2.json"), "--sprint-history")
hist = rows_h[0]["cf"]["customfield_10020"]
check("5.1 --sprint-history prints every sprint with its dates", [s["state"] for s in hist] == ["active", "closed", "closed"]
      and hist[1].get("completeDate") == "2026-11-16" and hist[0].get("startDate") == "2026-11-16" and rows_h[0]["closed_sprints"] == 2, hist)
code5, rows5, pages5, _ = run(os.path.join(FIX, "issue-v2.json"))
check("5.2 one issue (getJiraIssue) is one row, with no next page", code5 == 0 and [r["key"] for r in rows5] == ["PROJ-102"]
      and pages5[0].get("has_next") is False, (code5, rows5, pages5))
code6, rows6, pages6, _ = run("-", stdin=fixture("search-v2.json"))
check("5.3 stdin reads the same", code6 == 0 and rows6 == rows and pages6[0].get("file") == "stdin", (code6, pages6))
code7, rows7, pages7, _ = run(os.path.join(FIX, "search-v2.json"), os.path.join(FIX, "search-v1.json"))
check("5.4 several files: the rows of each, then its page line", code7 == 0 and len(rows7) == 5
      and [pg_["file"] for pg_ in pages7] == ["search-v2.json", "search-v1.json"], (code7, pages7))

# 6. not a Jira response
code8, rows8, _, p8 = run(os.path.join(FIX, "not-jira.json"))
check("6.1 a file that is not a Jira response: exit 2 and a reason, no rows", code8 == 2 and not rows8 and "not a Jira response" in p8.stderr, (code8, p8.stderr))
d = tempfile.mkdtemp(prefix="jira-rows-test-")
broken = os.path.join(d, "cut.json")
open(broken, "w", encoding="utf-8").write(fixture("search-v2.json")[:400])
code9, rows9, _, p9 = run(broken)
check("6.2 a response cut in the middle: exit 2, no rows", code9 == 2 and not rows9 and "not JSON" in p9.stderr, (code9, p9.stderr))
code10, rows10, _, p10 = run(os.path.join(d, "absent.json"), os.path.join(FIX, "search-v1.json"))
check("6.3 a missing file is exit 2, and the other file is still read", code10 == 2 and len(rows10) == 2, (code10, p10.stderr))
code11, _, _, p11 = run()
check("6.4 no file: usage, exit 2", code11 == 2 and "usage" in p11.stderr, (code11, p11.stderr))

# 7. the protocol
proto = open(os.path.join(ROOT, "references", "jira-data-protocol.md"), encoding="utf-8").read()
check("7.1 jira-data-protocol.md names the script and the v2 shape", "scripts/jira_rows.py" in proto and "fields.customFields" in proto, "")
block = proto.split("No shell", 1)[1] if "No shell" in proto else ""
pats = [l.split("   #")[0].strip() for l in re.findall(r"```\n(.*?)```", block, re.S)[0].splitlines()] if "```" in block else []
pats = [x for x in pats if x]
raw = json.dumps(json.loads(fixture("search-v2.json")), ensure_ascii=False, separators=(",", ":"))
dead = [x for x in pats if not re.search(x, raw)]
check("7.2 every no-shell pattern of the protocol matches the v2 fixture", pats and not dead, dead or "no patterns found")
sp = [m for x in pats if "customfield_10036" in x for m in re.findall(x, raw)]
check("7.3 the Story Points pattern finds both estimates", len(sp) == 2, sp)

# mutations
src = open(SCRIPT, encoding="utf-8").read()


def mutant(tag, old, new):
    if old not in src:
        return None
    path = os.path.join(d, "jira_rows_%s.py" % tag)
    open(path, "w", encoding="utf-8").write(src.replace(old, new, 1))
    return load(path, "jira_rows_" + tag)


m1 = mutant("v1only", 'if name == "customFields" and isinstance(value, dict):', 'if name == "customFields" and False:')
r1 = m1.read(fixture("search-v2.json"))[0] if m1 else None
check("M1 a reader of fields.customfield_N alone loses the v2 estimates — caught", m1 is not None
      and "customfield_10036" not in r1[0]["cf"], "the mutation did not apply")
m2 = mutant("wholeuser", 'if "accountId" in v:', 'if "accountId" in v and False:')
r2 = json.dumps(m2.read(fixture("search-v2.json"))[0]) if m2 else ""
check("M2 a reader that does not reduce a user — caught by 1.4", m2 is not None and '"name": "Zorg Dev"' not in r2.replace('"id": "acc-zorg-dev", ', ""), "the mutation did not apply")

print("\nRESULT: %s (%d failed)" % ("GREEN ✅" if not fails else "RED ❌", fails))
sys.exit(1 if fails else 0)
