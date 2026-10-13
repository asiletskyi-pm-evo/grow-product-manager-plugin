#!/usr/bin/env python3
"""TC-ctx-3130-blocks — scripts/ctx_blocks.py: regions in the context records and the class of each block (since v3.13.0).

Pure functions on the fictional "Zorg": `norm` (the text two blocks are compared by), `find_regions` (a
repository's managed regions in the records' bodies — inside a section wrapper too, found in whichever record
holds them now, and the structure errors: a duplicate id, a broken marker, a nested region) and `classify`
(the plan's sign for one block from mine / theirs / the stored base — the golden cases of the spec's tables
B5 and B6, and the order the rules apply in). One test runs on a real migrated store. Semantics:
references/context-provider-protocol.md. Stdlib only; run from the repo root.
"""
import os, shutil, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import ctx_blocks as cb  # noqa: E402
import ctx_ops as co  # noqa: E402
import ctx_store as cs  # noqa: E402

FIX = os.path.join(ROOT, "testing", "fixtures", "ctx-repos")
NOW = "2026-10-20T10:00:00+03:00"
fails = 0


def check(name, cond, detail=""):
    global fails
    fails += not cond
    print(("✅" if cond else "❌"), name, ("" if cond else "-> " + str(detail)[:700]))


NS = "zorg-core"


def region(bid, v, body, ns=NS):
    return "<!-- %s:begin id=%s v=%s -->\n%s\n<!-- %s:end id=%s -->" % (ns, bid, v, body, ns, bid)


def rec(rid, body):
    return {"id": rid, "type": "custom", "title": rid, "parent": None, "order": 10, "body": body}


def st(base, bases=None, user_removed=None):
    """What the state holds for a block: the hash of the base and of the last bases (the texts are never kept here)."""
    h = lambda t: cs.sha_text(cb.norm(t))
    return {"base_sha": h(base), "bases": [h(t) for t in (bases if bases is not None else [base])], "user_removed": user_removed}


# ------------------------------------------------------------------ norm
check("norm: CRLF becomes LF", cb.norm("a\r\nb\r\n") == "a\nb", repr(cb.norm("a\r\nb\r\n")))
check("norm: trailing spaces and tabs go, indentation and inner spaces stay",
      cb.norm("  a  b \t\n    c  \n") == "  a  b\n    c", repr(cb.norm("  a  b \t\n    c  \n")))
check("norm: trailing blank lines go, blank lines inside and before stay",
      cb.norm("\n\na\n\n\nb\n  \n\n") == "\n\na\n\n\nb", repr(cb.norm("\n\na\n\n\nb\n  \n\n")))
check("norm: only spaces, tabs and a stray CR are trailing whitespace — other characters are content",
      cb.norm("a\u00a0\nb\r") == "a\u00a0\nb", repr(cb.norm("a\u00a0\nb\r")))
check("norm: nothing is the empty text, and it is idempotent",
      cb.norm(None) == "" and cb.norm("") == "" and cb.norm(" \n \r\n") == ""
      and cb.norm(cb.norm("a \r\n\r\nb  \n\n")) == cb.norm("a \r\n\r\nb  \n\n"), "")

# ------------------------------------------------------------------ classify
A0 = region("scope", "0.1", "### Scope\nAlpha only.")
A1 = region("scope", "0.2", "### Scope\nAlpha and Beta.")
A2 = region("scope", "0.3", "### Scope\nAlpha, Beta and Gamma.")
A = A0
B = region("scope", "0.1", "### Scope\nAlpha only. (my note)")
C = region("scope", "0.2", "### Scope\nSomething else entirely.")

check("= same", cb.classify(A, A, st(A)) == "=")
check("~ fast-forward", cb.classify(A, B, st(A)) == "~")
check("~ after skipped releases", cb.classify(A0, C, st(A2, bases=[A0, A1, A2])) == "~")
check("✎ mine kept", cb.classify(B, A, st(A)) == "✎")
check("⚠ both changed", cb.classify(B, C, st(A)) == "⚠")
check("+ new block", cb.classify(None, A, None) == "+")
check("− removed upstream", cb.classify(A, None, st(A)) == "−")
check("✂ removed by you", cb.classify(None, A, st(A, user_removed="2026-10-13")) == "✂")
check("? no base", cb.classify(B, A, None) == "?")
check("CRLF and trailing spaces are equal", cb.classify(A.replace("\n", "\r\n") + "  ", A, st(A)) == "=")

check("= even without a base, when the texts are equal", cb.classify(A, A, None) == "="
      and cb.classify(A + "   \n\n", A.replace("\n", "\r\n"), None) == "=")
check("✂ also when the base is there but the removal was not flagged", cb.classify(None, A, st(A)) == "✂")
check("✂ stays ✂ whatever upstream did since", cb.classify(None, C, st(A, user_removed="2026-10-13")) == "✂")
check("+ means no base: a block with a base and no copy of yours is not new", cb.classify(None, A, st(A)) != "+")
check("− with no base too", cb.classify(A, None, None) == "−")
check("− even when you changed the block", cb.classify(B, None, st(A)) == "−")
check("~ wins when both texts are known bases: yours is the older one",
      cb.classify(A0, A1, st(A2, bases=[A0, A1, A2])) == "~")
check("✎ when upstream is back at an older base and you changed it", cb.classify(B, A0, st(A2, bases=[A0, A1, A2])) == "✎")
check("⚠ when yours is no known base and neither is theirs", cb.classify(B, C, st(A2, bases=[A0, A1, A2])) == "⚠")
check("⚠ when the base list is empty", cb.classify(B, C, {"base_sha": cs.sha_text(cb.norm(A)), "bases": [], "user_removed": None}) == "⚠")
check("~ on the base_sha alone, with no list of bases", cb.classify(A, C, {"base_sha": cs.sha_text(cb.norm(A)), "bases": None}) == "~")
check("a base compared whitespace-blind: yours differs by trailing spaces only → ~",
      cb.classify(A.replace("\n", "  \n"), C, st(A)) == "~")
try:
    cb.classify(None, None, None)
    both_none = False
except ValueError:
    both_none = True
check("neither side and no base is no block at all → ValueError", both_none)
check("neither side but a base → the block is gone for good: ✂", cb.classify(None, None, st(A)) == "✂")

# ------------------------------------------------------------------ find_regions
ID_SCOPE = region("scope", "0.4", "### Scope of work\nThe user works on Zorg App only.")
ID_TEAMS = region("teams", "0.3", "### Teams map\n- Alpha, Beta")
recs = [
    rec("custom.zorg-notes-a", "## Notes\n\nSome of my text.\n\n" + ID_SCOPE + "\n\nMore of my text.\n"),
    rec("team.alpha", "### Team: Alpha\n\n" + region("team", "0.2", "### Team: Alpha\n- card", NS) + "\n\n"
        + region("growth-metrics", "0.1", "#### Growth metrics", "zorg-growth") + "\n"),
]
found, errs = cb.find_regions(recs, NS)
check("a region is found: host, text with markers and no final newline, version",
      found.get("scope") == {"host": "custom.zorg-notes-a", "text": ID_SCOPE, "v": "0.4"}, found)
check("every block of the namespace, none of another namespace's", set(found) == {"scope", "team"} and errs == [], (found.keys(), errs))
check("other namespaces are ignored", "growth-metrics" not in found, found.keys())
fg, eg = cb.find_regions(recs, "zorg-growth")
check("…and the other namespace sees its own; the same id in two namespaces is no duplicate",
      set(fg) == {"growth-metrics"} and eg == [] and fg["growth-metrics"]["host"] == "team.alpha", (fg, eg))
check("a namespace that is only the start of another finds nothing", cb.find_regions(recs, "zorg") == ({}, []), cb.find_regions(recs, "zorg"))
check("the text of the region is byte-exact (the slice of the body)", recs[1]["body"].count(found["team"]["text"]) == 1, found["team"])

wrapper = ("<!-- zorg-core:section:begin -->\n## Zorg shared product core (reference — shared core)\n\n> The blocks below come from the core.\n\n"
           + ID_SCOPE + "\n\n" + ID_TEAMS + "\n<!-- zorg-core:section:end -->\n")
recs_wrapped = [rec("custom.zorg-core", wrapper)]
fw, ew = cb.find_regions(recs_wrapped, NS)
check("regions found inside a section wrapper", "scope" in fw, fw)
check("the wrapper itself is no block, and nothing is an error", set(fw) == {"scope", "teams"} and ew == [], (fw.keys(), ew))
check("the wrapper's lines are not in a block's text", fw["scope"]["text"] == ID_SCOPE and "shared core" not in fw["scope"]["text"], fw["scope"])

recs_moved = [rec("custom.zorg-core", "## Zorg\n\nnothing here now\n"),
              rec("custom.zorg-notes", "## My notes\n\n" + ID_SCOPE + "\n")]
check("a moved region is found in its new host", cb.find_regions(recs_moved, NS)[0]["scope"]["host"] == "custom.zorg-notes", "")

nov = "<!-- zorg-core:begin id=bare -->\nB\n<!-- zorg-core:end id=bare -->"
more = "<!-- zorg-core:begin id=dotted.rule_1 v=0.4 src=core -->\nD\n<!-- zorg-core:end id=dotted.rule_1 -->"
fv, ev = cb.find_regions([rec("r", nov + "\n" + more)], NS)
check("a region with no version has v ''; other attributes do not leak into v; an id may hold dots and underscores",
      fv["bare"]["v"] == "" and fv["dotted.rule_1"]["v"] == "0.4" and ev == [], (fv, ev))
check("a wide gap in the markers is fine: spaces after the comment opener and before its end",
      cb.find_regions([rec("r", "<!--   zorg-core:begin   id=a   v=1   -->\nA\n<!--  zorg-core:end   id=a  -->")], NS)[0].keys() == {"a"}, "")
check("CRLF bodies give the same blocks and classify equal to LF",
      cb.find_regions([rec("r", ("x\n" + ID_SCOPE + "\ny\n").replace("\n", "\r\n"))], NS)[0]["scope"]["v"] == "0.4"
      and cb.classify(cb.find_regions([rec("r", ID_SCOPE.replace("\n", "\r\n"))], NS)[0]["scope"]["text"], ID_SCOPE, None) == "=", "")
check("records with no body, a None body, or no regions are fine",
      cb.find_regions([{"id": "a"}, rec("b", None), rec("c", ""), rec("d", "# Plain")], NS) == ({}, []), "")
check("no records, no regions", cb.find_regions([], NS) == ({}, []))

# --- duplicates
recs_dup = [rec("custom.zorg-a", ID_SCOPE + "\n\n" + ID_TEAMS), rec("custom.zorg-b", "## Mine\n" + ID_SCOPE.replace("0.4", "0.5"))]
fd, ed = cb.find_regions(recs_dup, NS)
check("duplicate id is an error", ed and ed[0]["why"] == "duplicate", ed)
check("the error names the block and the host of the occurrence after the first",
      ed == [{"block": "scope", "host": "custom.zorg-b", "why": "duplicate"}], ed)
check("the duplicated id is dropped from the result; the others stay", set(fd) == {"teams"}, fd.keys())
recs_dup2 = [rec("custom.zorg-a", ID_SCOPE + "\n" + ID_SCOPE + "\n" + ID_SCOPE), rec("custom.zorg-b", ID_SCOPE)]
fd2, ed2 = cb.find_regions(recs_dup2, NS)
check("every occurrence after the first is reported, in one record and across records, in order",
      [(e["block"], e["host"], e["why"]) for e in ed2] == [("scope", "custom.zorg-a", "duplicate")] * 2 + [("scope", "custom.zorg-b", "duplicate")]
      and fd2 == {}, ed2)
check("the same id in two namespaces is not a duplicate", cb.find_regions(
    [rec("a", region("team", "1", "A", "zorg-core")), rec("b", region("team", "1", "B", "zorg-growth"))], "zorg-core")[1] == [], "")

# --- broken markers
unclosed = rec("custom.zorg-core", "## Zorg\n\n<!-- zorg-core:begin id=scope v=0.4 -->\n### Scope\nno end here\n")
fb, eb = cb.find_regions([unclosed], NS)
check("broken end marker is an error: a begin with no end", eb and eb[0]["why"] == "broken marker", eb)
check("…naming the block and its host; the block is no block", eb == [{"block": "scope", "host": "custom.zorg-core", "why": "broken marker"}]
      and fb == {}, (eb, fb))
orphan = rec("custom.zorg-core", "## Zorg\n\n### Scope\nlost\n<!-- zorg-core:end id=scope -->\n\n" + ID_TEAMS)
fo, eo = cb.find_regions([orphan], NS)
check("an end with no begin is an error; a good block next to it stays",
      eo == [{"block": "scope", "host": "custom.zorg-core", "why": "broken marker"}] and set(fo) == {"teams"}, (eo, fo))
wrong = rec("custom.zorg-core", "<!-- zorg-core:begin id=scope v=0.4 -->\nA\n<!-- zorg-core:end id=scopes -->\n")
fx, ex = cb.find_regions([wrong], NS)
check("an end whose id differs is an error — both ids are reported and neither is a block",
      {e["block"] for e in ex} == {"scope", "scopes"} and {e["why"] for e in ex} == {"broken marker"} and fx == {}, (ex, fx))
noid = rec("custom.zorg-core", "<!-- zorg-core:begin v=0.4 -->\nA\n<!-- zorg-core:end id=a -->\n" + ID_TEAMS)
fn, en = cb.find_regions([noid], NS)
check("a begin marker with no id is a broken marker, not silence",
      en and {e["why"] for e in en} == {"broken marker"} and set(fn) == {"teams"}, (en, fn))
check("a broken marker in a record does not touch the other records",
      set(cb.find_regions([unclosed, rec("custom.zorg-x", ID_TEAMS)], NS)[0]) == {"teams"}, "")
fgo, ego = cb.find_regions([rec("g", ID_SCOPE), orphan], NS)
check("an id with a broken occurrence is not a block even if another record holds a good one",
      "scope" not in fgo and [e["block"] for e in ego] == ["scope"] and set(fgo) == {"teams"}, (fgo.keys(), ego))
check("a broken marker of another namespace is not ours",
      cb.find_regions([rec("g", "<!-- zorg-growth:begin id=x v=1 -->\nnever closed\n" + ID_SCOPE)], NS) == (cb.find_regions([rec("g", ID_SCOPE)], NS)[0], []), "")

# --- nested
outer = ("<!-- zorg-core:begin id=outer v=0.4 -->\nOuter text\n" + ID_TEAMS + "\nmore outer\n<!-- zorg-core:end id=outer -->")
recs_nested = [rec("custom.zorg-core", "## Zorg\n\n" + outer + "\n\n" + ID_SCOPE + "\n")]
fnest, enest = cb.find_regions(recs_nested, NS)
check("a begin inside another region is nested", enest and enest[0]["why"] == "nested", enest)
check("…both the outer and the inner block are reported and dropped; a separate block stays",
      {(e["block"], e["host"], e["why"]) for e in enest} == {("outer", "custom.zorg-core", "nested"), ("teams", "custom.zorg-core", "nested")}
      and set(fnest) == {"scope"}, (enest, fnest))
check("a region of the same id inside itself is nested, not a duplicate",
      [e["why"] for e in cb.find_regions([rec("r", "<!-- zorg-core:begin id=a v=1 -->\n<!-- zorg-core:begin id=a v=1 -->\nX\n<!-- zorg-core:end id=a -->\n<!-- zorg-core:end id=a -->")], NS)[1]]
      .count("nested") >= 1, "")
swallow = rec("r", "<!-- zorg-core:begin id=a v=1 -->\nA lost its end\n\n" + ID_TEAMS + "\n\n" + ID_SCOPE)
fs_, es_ = cb.find_regions([swallow], NS)
check("an unclosed begin swallows the regions after it: it is a broken marker, they are nested",
      {(e["block"], e["why"]) for e in es_} == {("a", "broken marker"), ("teams", "nested"), ("scope", "nested")} and fs_ == {}, (es_, fs_))
check("a region of another namespace inside ours is no nesting",
      cb.find_regions([rec("r", "<!-- zorg-core:begin id=a v=1 -->\n" + region("x", "1", "X", "zorg-growth") + "\n<!-- zorg-core:end id=a -->")], NS)[0].keys() == {"a"}, "")
check("every error has exactly block, host and why",
      all(set(e) == {"block", "host", "why"} for e in ed + eb + eo + ex + en + enest + es_), "")

# ------------------------------------------------------------------ on a real migrated store
with tempfile.TemporaryDirectory() as d:
    home, vault = os.path.join(d, "home"), os.path.join(d, "vault")
    os.makedirs(os.path.join(home, ".grow-pm"))
    os.makedirs(os.path.join(vault, "Notes", "_System"))
    text = open(os.path.join(FIX, "context.md"), encoding="utf-8", newline="").read().replace("{{VAULT}}", vault)
    ctxp = os.path.join(home, ".grow-pm", "local-context.md")
    for p in (ctxp, os.path.join(vault, "Notes", "_System", "local-context.md")):
        open(p, "w", encoding="utf-8", newline="").write(text)
    copies = co.copies_for(ctxp, text, home=home)
    store = cs.Store(co.store_root_for(text, home=home))
    co.migrate(ctxp, store.root, copies, home, apply=True, now=NOW)
    loaded = store.load()
    fr, er = cb.find_regions(loaded, "zorg-core")
    check("on a migrated store: the core's blocks, each in the record that holds it",
          {k: v["host"] for k, v in fr.items()} == {"team": "team.alpha-a", "scope": "custom.zorg-core-notes", "teams": "custom.zorg-core-notes"}
          and er == [], ({k: v["host"] for k, v in fr.items()}, er))
    fg, eg = cb.find_regions(loaded, "zorg-growth")
    check("…and the growth repository's, which shares the id 'team' without clashing",
          {k: v["host"] for k, v in fg.items()} == {"growth-metrics": "product.zorg-app", "team": "team.alpha-a"} and eg == [],
          ({k: v["host"] for k, v in fg.items()}, eg))
    check("the found text is what the repository would publish, so an untouched block classifies =",
          cb.classify(fr["scope"]["text"], region("scope", "0.4", "### Scope of work\nThe user works on Zorg App only."), None) == "=", fr["scope"])

print("RESULT: GREEN ✅" if not fails else "RESULT: RED ❌")
sys.exit(1 if fails else 0)
