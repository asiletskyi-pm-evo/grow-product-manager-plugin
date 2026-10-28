#!/usr/bin/env python3
"""TC-ctx-3230-overlay — scripts/ctx_overlay.py: the declared overlay to a repository's blocks (since v3.23.0).

Pure functions on the fictional "Zorg": `parse` / `dump` (the file `overlays/<repo>.yaml`, schema `context-overlay/1`:
an unknown key is refused, never dropped; a file that cannot be read raises Unreadable), `locate` (the four forms of a
target's path — the whole block, `#Subsection`, `field:Label`, `match:"text"`) and `overlay` (the five operations on a
region's text: replace, remove, append change the text; ignore and alias never do; `expects` against what is found —
an operation whose count differs is held; two operations that touch the same lines are both refused), then `load` /
`save` on disk (an unreadable file is never rewritten). Semantics: references/context-protocol.md §5n.
Stdlib only; run from the repo root.
"""
import os, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import ctx_overlay as ov  # noqa: E402

fails = 0


def check(name, cond, detail=""):
    global fails
    fails += not cond
    print(("✅" if cond else "❌"), name, ("" if cond else "-> " + str(detail)[:700]))


def raises(fn, *a, **k):
    try:
        fn(*a, **k)
    except ov.Unreadable as e:
        return str(e)
    return None


NS = "zorg-core"


def region(bid, body, v="0.4", ns=NS):
    return "<!-- %s:begin id=%s v=%s -->\n%s\n<!-- %s:end id=%s -->" % (ns, bid, v, body, ns, bid)


GOOD = '''schema: context-overlay/1
repo: zorg-core
ops:
  - id: team-members
    target: {block: team, path: "#Members"}
    op: replace
    value_ref: "team.alpha-a#Team Members"
    expects: 1
    reason: "у ядрі заглушки без ролей"
    created: 2026-10-28
  - id: okr-target
    target: {block: okr, path: 'match:"Revenue +38%"'}
    op: ignore
    reason: "першоджерело каже +30%"   # a comment
    created: 2026-10-28
  - target: {block: team, path: "field:Team"}
    op: alias
    value: ["Alpha (A)", "Alpha Team (A)"]
  - id: notes
    target: {block: scope}
    op: append
    value:
      - "- also: the Q&A widget"
      - "- also: comparison, A, B"
'''

# ------------------------------------------------------------------ parse
doc = ov.parse(GOOD)
ops = doc["ops"]
check("parse: schema, repo and four operations", doc["schema"] == "context-overlay/1" and doc["repo"] == "zorg-core"
      and [o["op"] for o in ops] == ["replace", "ignore", "alias", "append"], doc)
check("parse: a flow map target with a quoted path, a quoted path inside single quotes",
      ops[0]["target"] == {"block": "team", "path": "#Members"} and ops[1]["target"] == {"block": "okr", "path": 'match:"Revenue +38%"'},
      [o["target"] for o in ops])
check("parse: expects defaults to 1, a given one is an integer", ops[0]["expects"] == 1 and ops[1]["expects"] == 1, ops[:2])
check("parse: a missing id is made from block and path, kebab-case", ops[2]["id"] == "team-field-team", ops[2]["id"])
check("parse: a flow list and a block list of lines are lists of strings",
      ops[2]["value"] == ["Alpha (A)", "Alpha Team (A)"] and ops[3]["value"] == ["- also: the Q&A widget", "- also: comparison, A, B"],
      (ops[2].get("value"), ops[3].get("value")))
check("parse: a comment after a quoted value is dropped", ops[1]["reason"] == "першоджерело каже +30%", ops[1]["reason"])
check("parse: a path with a comma inside quotes stays whole",
      ov.parse(GOOD.replace('Revenue +38%', 'Revenue +38%, EBITDA'))["ops"][1]["target"]["path"] == 'match:"Revenue +38%, EBITDA"', "")
check("parse: no ops is an empty list", ov.parse("schema: context-overlay/1\nrepo: zorg-core\nops: []\n")["ops"] == [], "")

BAD = {
    "an unknown top key": GOOD.replace("repo: zorg-core", "repo: zorg-core\nowner: me"),
    "an unknown key of an operation": GOOD.replace("    expects: 1\n", "    expects: 1\n    priority: 50\n", 1),
    "an unknown key of a target": GOOD.replace('{block: team, path: "#Members"}', '{block: team, path: "#Members", rank: 1}'),
    "another schema": GOOD.replace("context-overlay/1", "context-overlay/2"),
    "an unknown operation": GOOD.replace("op: ignore", "op: hide"),
    "a target without a block": GOOD.replace('{block: team, path: "#Members"}', '{path: "#Members"}'),
    "a path of no known form": GOOD.replace('"#Members"', '"Members"'),
    "replace without value or value_ref": GOOD.replace('    value_ref: "team.alpha-a#Team Members"\n', ""),
    "replace with both value and value_ref": GOOD.replace('    value_ref: "team.alpha-a#Team Members"\n',
                                                         '    value_ref: "team.alpha-a#Team Members"\n    value: "x"\n'),
    "a value_ref without #": GOOD.replace("team.alpha-a#Team Members", "team.alpha-a"),
    "ignore with a value": GOOD.replace("    op: ignore\n", "    op: ignore\n    value: x\n"),
    "a negative expects": GOOD.replace("expects: 1", "expects: -1"),
    "a text expects": GOOD.replace("expects: 1", "expects: one"),
    "a repeated id": GOOD.replace("id: notes", "id: team-members"),
    "a repeated key": GOOD.replace("    op: replace\n", "    op: replace\n    op: remove\n"),
    "tab indentation": GOOD.replace("    op: replace", "\top: replace"),
    "a repository id that is not kebab-case": GOOD.replace("repo: zorg-core", "repo: ../evil"),
    "an alias without value": GOOD.replace('    value: ["Alpha (A)", "Alpha Team (A)"]\n', ""),
    "no schema": GOOD.replace("schema: context-overlay/1\n", ""),
}
for what, text in BAD.items():
    why = raises(ov.parse, text)
    check("parse refuses %s" % what, why is not None, why)

# ------------------------------------------------------------------ dump
again = ov.parse(ov.dump(doc))
check("dump → parse gives the same document", again == doc, (again, doc))
check("dump is canonical: dumping twice is the same text", ov.dump(again) == ov.dump(doc), "")
check("dump writes the made id, quotes every string and keeps the key order",
      "  - id: team-field-team\n    target: {block: team, path: \"field:Team\"}\n    op: alias\n" in ov.dump(doc), ov.dump(doc))
weird = dict(doc, ops=[dict(ops[0], reason='a "quoted" # not a comment: \\ back')])
check("dump → parse keeps quotes, # and a backslash inside a reason", ov.parse(ov.dump(weird))["ops"][0]["reason"]
      == 'a "quoted" # not a comment: \\ back', ov.dump(weird))

# ------------------------------------------------------------------ locate
TEAM = "\n".join([
    "### Team: Alpha (A)",
    "- **Team:** Alpha (A)",
    "- **Jira:** PROJ",
    "",
    "#### Members",
    "| Name | Role |",
    "|---|---|",
    "| Ann Zorg | — |",
    "",
    "#### Members (former)",
    "| Bob Zorg | — |",
    "",
    "#### Scope",
    "Revenue +38% this year.",
    "Lists and filters.",
])
lines = TEAM.split("\n")
spans = lambda p: ov.locate(lines, p)
check("locate: the whole block is one span", spans("") == [(0, len(lines))], spans(""))
check("locate: #Members — the heading, a qualifier answers too, each up to the next heading of its level",
      spans("#Members") == [(4, 9), (9, 12)], spans("#Members"))
check("locate: #members — without regard to case", spans("#members") == spans("#Members"), "")
check("locate: #Team: Alpha (A) — a level-3 heading spans the subsections under it", spans("#Team: Alpha (A)") == [(0, 15)],
      spans("#Team: Alpha (A)"))
check("locate: field:Jira — the field line, label without regard to case", spans("field:jira") == [(2, 3)], spans("field:jira"))
check("locate: match — lines that hold the text, case and runs of spaces aside",
      spans('match:"revenue   +38%"') == [(13, 14)], spans('match:"revenue   +38%"'))
check("locate: match without quotes reads the rest as the text", spans("match:Zorg") == [(7, 8), (10, 11)], spans("match:Zorg"))
check("locate: nothing found is an empty list", spans("#Budget") == [] and spans("field:Owner") == [] and spans('match:"x y z"') == [], "")

# ------------------------------------------------------------------ overlay
def op(**k):
    base = {"id": k.pop("id", "o"), "target": {"block": "team", "path": k.pop("path", "")}, "op": k.pop("op"),
            "expects": k.pop("expects", 1), "reason": k.pop("reason", "r"), "created": "2026-10-28"}
    base.update(k)
    return base


R = region("team", TEAM)
REFS = {"team.alpha-a#Team Members"}
has = lambda ref: ref in REFS

out, res = ov.overlay(R, [op(op="replace", path="#Members", value_ref="team.alpha-a#Team Members", id="m", expects=2)], has)
check("replace by value_ref: the subsection's lines become one pointer line, both headings stay, the markers too",
      out.startswith("<!-- zorg-core:begin id=team v=0.4 -->\n") and out.endswith("\n<!-- zorg-core:end id=team -->")
      and "| Ann Zorg | — |" not in out and "| Bob Zorg | — |" not in out and out.count("#### Members") == 2
      and "> [оверлей m: замінено на team.alpha-a › Team Members — r]" in out and res[0]["state"] == "applied"
      and res[0]["found"] == 2, (out, res))
check("replace keeps the blank line before the next heading", "> [оверлей m: замінено на team.alpha-a › Team Members — r]\n\n#### Members (former)" in out, out)

out, res = ov.overlay(R, [op(op="replace", path="#Members", value_ref="team.gone#Team Members", expects=2)], has)
check("a value_ref that names nothing is held: the text stays the core's", out == R and res[0]["state"] == "held"
      and "value_ref" in res[0]["why"], res)

out, res = ov.overlay(R, [op(op="replace", path="field:Jira", value="PROJ, ZORG")], has)
check("replace a field: the value goes after the label, the line's prefix kept", "- **Jira:** PROJ, ZORG" in out
      and "- **Jira:** PROJ\n" not in out, out)
out, res = ov.overlay(R, [op(op="replace", path='match:"Revenue +38%"', value=["Revenue +30% this year."])], has)
check("replace a matched line by the value's lines", "Revenue +30% this year.\nLists and filters." in out and "+38%" not in out, out)
out, res = ov.overlay(R, [op(op="replace", value=["### Team: Alpha (A)", "Only this."])], has)
check("replace the whole block keeps the markers", out == region("team", "### Team: Alpha (A)\nOnly this."), out)

out, res = ov.overlay(R, [op(op="remove", path="#Members", expects=2)], has)
check("remove a subsection: its heading and lines go, no doubled blank line",
      "Members" not in out and "\n\n\n" not in out and "- **Jira:** PROJ\n\n#### Scope" in out, out)
out, res = ov.overlay(R, [op(op="remove", path='match:"Revenue +38%"')], has)
check("remove a matched line", "+38%" not in out and "#### Scope\nLists and filters." in out, out)
out, res = ov.overlay(region("team", "A\n\nX\n\nB"), [op(op="remove", path='match:"X"')], has)
check("remove a line between two blank lines keeps one of them", out == region("team", "A\n\nB"), repr(out))
out, res = ov.overlay(region("team", "A\n\nX"), [op(op="remove", path='match:"X"')], has)
check("remove the last line leaves no trailing blank line", out == region("team", "A"), repr(out))
out, res = ov.overlay(R, [op(op="remove", path="field:Jira")], has)
check("remove a field line", "Jira" not in out and "- **Team:** Alpha (A)\n\n#### Members" in out, out)

out, res = ov.overlay(R, [op(op="append", path="#Scope", value=["Q&A widget."])], has)
check("append to a subsection: after its last line", out.endswith("Lists and filters.\nQ&A widget.\n<!-- zorg-core:end id=team -->"), out)
out, res = ov.overlay(R, [op(op="append", path="#Members", value="| Cid Zorg | QA |", expects=2)], has)
check("append to two matches: after the last line of each, before the blank line",
      "| Ann Zorg | — |\n| Cid Zorg | QA |\n\n#### Members (former)" in out and "| Bob Zorg | — |\n| Cid Zorg | QA |\n\n#### Scope" in out, out)
out, res = ov.overlay(R, [op(op="append", value="Added at the end.")], has)
check("append to the whole block: at its end", out.endswith("Lists and filters.\nAdded at the end.\n<!-- zorg-core:end id=team -->"), out)

out, res = ov.overlay(R, [op(op="ignore", path='match:"+38%"'), op(op="alias", path="field:Team", value=["Alpha Team (A)"], id="a")], has)
check("ignore and alias never change the text, and are applied", out == R and [r["state"] for r in res] == ["applied", "applied"], res)

out, res = ov.overlay(R, [op(op="remove", path="#Members")], has)
check("expects 1, found 2 → held, the text stays", out == R and res[0]["state"] == "held" and res[0]["found"] == 2
      and res[0]["expects"] == 1, res)
out, res = ov.overlay(R, [op(op="ignore", path='match:"EBITDA +38%"')], has)
check("expects 1, found 0 (the core fixed it) → held", res[0]["state"] == "held" and res[0]["found"] == 0, res)
out, res = ov.overlay(R, [op(op="remove", path="#Members", expects=2, id="x"), op(op="remove", path="field:Jira", id="y")], has)
check("an operation held does not stop another: the field goes, the subsections too (expects 2)",
      "Jira" not in out and "Members" not in out and [r["state"] for r in res] == ["applied", "applied"], res)
out, res = ov.overlay(R, [op(op="remove", path="#Scope", id="x"), op(op="replace", path='match:"Lists"', value="L", id="y")], has)
check("two operations on the same lines → both refused, the text stays", out == R
      and [r["state"] for r in res] == ["error", "error"] and "y" in res[0]["why"] and "x" in res[1]["why"], res)
out, res = ov.overlay(R, [op(op="ignore", path="#Scope", id="x"), op(op="replace", path='match:"Lists"', value="L", id="y")], has)
check("an ignore over the same lines as a replace is no clash (ignore changes no text)", "\nL\n" in out
      and [r["state"] for r in res] == ["applied", "applied"], res)
out, res = ov.overlay(R, [op(op="remove", path="field:Owner", expects=0)], has)
check("expects 0 found 0 → applied with nothing to do", out == R and res[0]["state"] == "applied", res)
out, res = ov.overlay(R, [], has)
check("no operations: the text is the core's, byte for byte", out == R and res == [], res)
CR = R.replace("\n", "\r\n")
out, res = ov.overlay(CR, [op(op="remove", path="field:Jira")], has)
check("a CRLF region: the operation applies, line ends stay CRLF", "Jira" not in out and "\r\n" in out and "\n\n" not in out.replace("\r\n", ""), repr(out[:120]))
check("ops of another block do nothing here", ov.overlay(R, [dict(op(op="remove", path="field:Jira"), target={"block": "okr", "path": "field:Jira"})], has)[0] == R, "")

check("ignored: the lines an applied ignore names, per block; a held one none",
      ov.ignored(R, [op(op="ignore", path='match:"+38%"')], has) == ["Revenue +38% this year."]
      and ov.ignored(R, [op(op="ignore", path='match:"EBITDA"')], has) == [], ov.ignored(R, [op(op="ignore", path='match:"+38%"')], has))
check("ignored: a whole-block ignore is the marker ALL", ov.ignored(R, [op(op="ignore")], has) == ov.ALL, "")
check("aliases: the names an applied alias adds, with the value its path finds",
      ov.aliases(R, [op(op="alias", path="field:Team", value=["Alpha Team (A)"])], has) == [("Alpha (A)", ["Alpha Team (A)"])],
      ov.aliases(R, [op(op="alias", path="field:Team", value=["Alpha Team (A)"])], has))

check("aliases: a held alias (found 2, expects 1) adds nothing",
      ov.aliases(R, [op(op="alias", path="#Members", value=["X"])], has) == [], "")

# ------------------------------------------------------------------ load / save
with tempfile.TemporaryDirectory() as d:
    check("load: no file → None", ov.load(d, "zorg-core") is None, "")
    ov.save(d, "zorg-core", doc)
    p = ov.path_of(d, "zorg-core")
    check("save writes overlays/<repo>.yaml in the canonical form", p == os.path.join(d, "overlays", "zorg-core.yaml")
          and open(p, encoding="utf-8").read() == ov.dump(doc), p)
    check("load reads it back", ov.load(d, "zorg-core") == doc, "")
    with open(p, "w", encoding="utf-8") as f:
        f.write(GOOD.replace("op: ignore", "op: hide"))
    why = raises(ov.load, d, "zorg-core")
    check("load: an unreadable file raises, naming the file", why is not None and "zorg-core.yaml" in why, why)
    with open(p, "w", encoding="utf-8") as f:
        f.write(GOOD.replace("repo: zorg-core", "repo: zorg-growth"))
    check("load: a file whose repo is another repository's is unreadable", raises(ov.load, d, "zorg-core") is not None, "")
    with open(p, "w", encoding="utf-8") as f:
        f.write("broken: [\n")
    before = open(p, encoding="utf-8").read()
    why = None
    try:
        ov.save(d, "zorg-core", doc, replace_unreadable=False)
    except ov.Unreadable as e:
        why = str(e)
    check("save never rewrites a file that cannot be read", why is not None and open(p, encoding="utf-8").read() == before, why)
    check("path_of refuses a repository id that is not kebab-case", raises(ov.path_of, d, "../x") is not None, "")

print("RESULT: GREEN ✅" if not fails else "RESULT: RED ❌")
sys.exit(1 if fails else 0)
