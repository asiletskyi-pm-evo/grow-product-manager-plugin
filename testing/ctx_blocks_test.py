#!/usr/bin/env python3
"""TC-ctx-3130-blocks — scripts/ctx_blocks.py: regions in the context records and the class of each block (since v3.13.0).

Pure functions on the fictional "Zorg": `norm` (the text two blocks are compared by), `find_regions` (a
repository's managed regions in the records' bodies — inside a section wrapper too, found in whichever record
holds them now, and the structure errors: a duplicate id, a broken marker, a nested region) and `classify`
(the plan's sign for one block from mine / theirs / the stored base — the golden cases of the spec's tables
B5 and B6, and the order the rules apply in). One test runs on a real migrated store. The persistent side: a
repository's block state (`.state/blocks/<repo>.json`) and the base texts (`.state/blocks/<repo>/<sha>.md`) —
load/save, bases kept to ten, pruning, the write allow-list, refused repository ids and the read-only
`last_checked`. Then `adopt` (the first base of every block already in the records: base / edit / none / has-base),
`plan` (one table per repository, read only: the signs, the questions, the records an apply would rewrite) and `apply`
(one pass: your edits stay, an answer for a ⚠ or a ?, --add for a +, the write order, one snapshot and one journal line).
Semantics: references/context-provider-protocol.md §12. Stdlib only; run from the repo root.
"""
import json, os, re, shutil, sys, tempfile

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
check("? when the repository removed a block you hold and there is no base: nothing says it is the repository's text",
      cb.classify(A, None, None) == "?")
check("⚠ when the repository removed a block you changed: your edit is not dropped without a question",
      cb.classify(B, None, st(A)) == "⚠")
check("− when yours is an older base the repository removed", cb.classify(A0, None, st(A2, bases=[A0, A1, A2])) == "−")
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

# ------------------------------------------------------------------ the state of a repository's blocks, and the bases
def files_under(path):
    """{relative path: bytes} of every file under path, hidden ones too (empty when absent)."""
    out = {}
    for dp, _, fn in os.walk(path):
        for f in fn:
            out[os.path.relpath(os.path.join(dp, f), path)] = open(os.path.join(dp, f), "rb").read()
    return out


def sha_of(text):
    return cs.sha_text(cb.norm(text))


def raises(exc, fn, *a):
    try:
        fn(*a)
    except exc as e:
        return e
    except BaseException as e:
        return type(e).__name__ + ": " + str(e)
    return None


def hexes(n):
    return [cs.sha_text("version %d" % i) for i in range(n)]


with tempfile.TemporaryDirectory() as d:
    store = cs.Store(os.path.join(d, "vault", "_System", "context"))
    blocks_root = os.path.join(store.state_dir, "blocks")
    empty = {"checked": None, "source": None, "version": None, "blocks": {}}
    check("a repository with no state file: the empty state",
          cb.load_state(store, "zorg-core") == empty and not os.path.exists(store.root), cb.load_state(store, "zorg-core"))

    scope_text = region("scope", "0.4", "### Scope\r\nThe user works on Zorg App only.  \r\n")
    sha = cb.put_base(store, "zorg-core", scope_text)
    saved = {"checked": "2026-10-20T10:00:00+03:00", "source": "mcp", "version": "0.4",
             "blocks": {"scope": {"base_sha": sha, "bases": [sha], "v": "0.4", "host": "custom.zorg-core-notes",
                                  "checked": "2026-10-20T10:00:00+03:00", "user_removed": False},
                        "teams": {"base_sha": None, "bases": [], "v": "", "host": None, "checked": None, "user_removed": True}}}
    cb.save_state(store, "zorg-core", saved)
    check("state round trip", cb.load_state(store, "zorg-core") == saved, cb.load_state(store, "zorg-core"))
    state_file = os.path.join(blocks_root, "zorg-core.json")
    raw = open(state_file, encoding="utf-8", newline="").read()
    check("the state is one JSON file per repository under .state/blocks, sorted, ending with a newline",
          os.path.isfile(state_file) and raw.endswith("}\n") and json.loads(raw) == saved
          and raw == json.dumps(saved, ensure_ascii=False, indent=1, sort_keys=True) + "\n", raw[:200])
    check("the version of a marker that carries none is stored as the empty string (unknown)",
          cb.load_state(store, "zorg-core")["blocks"]["teams"]["v"] == "", "")
    check("another repository's state is separate",
          cb.load_state(store, "zorg-growth") == empty and cb.load_state(store, "zorg-core") == saved, "")

    # ---- put_base / get_base
    check("put_base returns the hash of the normalised text and names the file by it",
          sha == sha_of(scope_text) and os.path.isfile(os.path.join(blocks_root, "zorg-core", sha + ".md")), sha)
    check("the base is stored as given — CRLF and trailing spaces stay — and read back byte for byte",
          open(os.path.join(blocks_root, "zorg-core", sha + ".md"), "rb").read() == scope_text.encode("utf-8")
          and cb.get_base(store, "zorg-core", sha) == scope_text, repr(cb.get_base(store, "zorg-core", sha)))
    lf_sha = cb.put_base(store, "zorg-core", scope_text.replace("\r\n", "\n"))
    check("a text equal once normalised is the same base (the first stored stays)",
          lf_sha == sha and cb.get_base(store, "zorg-core", sha) == scope_text
          and len(os.listdir(os.path.join(blocks_root, "zorg-core"))) == 1, lf_sha)
    calls = []
    real_write = cs.atomic_write
    cs.atomic_write = lambda path, text: (calls.append(path), real_write(path, text))[1]
    try:
        again = cb.put_base(store, "zorg-core", scope_text)
        fresh = cb.put_base(store, "zorg-core", "another block text")
    finally:
        cs.atomic_write = real_write
    check("writing the same base twice is a no-op — nothing is written; a new text is",
          again == sha and len(calls) == 1 and calls[0].endswith(sha_of("another block text") + ".md"), calls)
    check("get_base: unknown hash, a repository with no bases, and a hash that is no hash are None",
          cb.get_base(store, "zorg-core", cs.sha_text("never stored")) is None
          and cb.get_base(store, "zorg-growth", sha) is None
          and cb.get_base(store, "zorg-core", "../zorg-core.json") is None
          and cb.get_base(store, "zorg-core", "") is None and cb.get_base(store, "zorg-core", None) is None, "")
    check("an empty base text and None are the same empty base",
          cb.put_base(store, "zorg-core", "") == cb.put_base(store, "zorg-core", None) == cs.sha_text("")
          and cb.get_base(store, "zorg-core", cs.sha_text("")) == "", "")

    # ---- a corrupt state is an error, never a silent reset
    bad = "{\"checked\": \"2026-10-20\", \"blocks\": {oops"
    open(state_file, "w", encoding="utf-8").write(bad)
    e = raises(cs.StoreError, cb.load_state, store, "zorg-core")
    check("a corrupt state file raises StoreError naming the file — and is left as it is",
          isinstance(e, cs.StoreError) and "zorg-core.json" in str(e) and open(state_file, encoding="utf-8").read() == bad, e)
    for label, payload in (("a list", "[]"), ("blocks that are not an object", "{\"blocks\": []}"),
                           ("a block that is not an object", "{\"blocks\": {\"scope\": 3}}"),
                           ("bases that are not a list", "{\"blocks\": {\"scope\": {\"bases\": \"abc\"}}}"),
                           ("a base that is not a hash string", "{\"blocks\": {\"scope\": {\"bases\": [1]}}}")):
        open(state_file, "w", encoding="utf-8").write(payload)
        e = raises(cs.StoreError, cb.load_state, store, "zorg-core")
        check("a state file of the wrong shape (%s) raises StoreError naming the file" % label,
              isinstance(e, cs.StoreError) and "zorg-core.json" in str(e), e)
    cb.save_state(store, "zorg-core", saved)

    # ---- missing keys come back filled; bases are kept to ten, newest last, base_sha the newest of them
    open(state_file, "w", encoding="utf-8").write(json.dumps({"blocks": {"scope": {"base_sha": sha}}}))
    loaded = cb.load_state(store, "zorg-core")
    check("a state with keys missing is filled with their defaults on load",
          loaded == {"checked": None, "source": None, "version": None,
                     "blocks": {"scope": {"base_sha": sha, "bases": [sha], "v": "", "host": None, "checked": None,
                                          "user_removed": False}}}, loaded)
    hs = hexes(12)
    many = {"checked": None, "source": None, "version": None,
            "blocks": {"scope": {"base_sha": hs[11], "bases": list(hs), "v": "0.5", "host": "h", "checked": None, "user_removed": False}}}
    cb.save_state(store, "zorg-core", many)
    state = cb.load_state(store, "zorg-core")
    check("bases are kept to the last 10 — the oldest dropped first", state["blocks"]["scope"]["bases"] == hs[2:], state["blocks"]["scope"]["bases"])
    moved = {"checked": None, "source": None, "version": None,
             "blocks": {"scope": {"base_sha": hs[3], "bases": list(hs[:6]) + [hs[3]], "v": "", "host": None, "checked": None, "user_removed": False}}}
    cb.save_state(store, "zorg-core", moved)
    check("base_sha is always the newest entry of bases, and a hash appears once",
          cb.load_state(store, "zorg-core")["blocks"]["scope"]["bases"] == [hs[0], hs[1], hs[2], hs[4], hs[5], hs[3]],
          cb.load_state(store, "zorg-core")["blocks"]["scope"]["bases"])
    lone = {"checked": None, "source": None, "version": None,
            "blocks": {"scope": {"base_sha": hs[0], "bases": [], "v": "", "host": None, "checked": None, "user_removed": False}}}
    cb.save_state(store, "zorg-core", lone)
    check("a base_sha missing from bases is added to them",
          cb.load_state(store, "zorg-core")["blocks"]["scope"]["bases"] == [hs[0]], "")
    mine_only = {"checked": None, "source": None, "version": None,
                 "blocks": {"scope": {"base_sha": None, "bases": [hs[1]], "v": "", "host": None, "checked": None, "user_removed": False}}}
    cb.save_state(store, "zorg-core", mine_only)
    check("a block with no base_sha keeps its bases as they are",
          cb.load_state(store, "zorg-core")["blocks"]["scope"]["bases"] == [hs[1]], "")

# ---- prune_bases
with tempfile.TemporaryDirectory() as d:
    store = cs.Store(os.path.join(d, "store"))
    texts = ["base text %d" % i for i in range(12)]
    shas = [cb.put_base(store, "zorg-core", t) for t in texts]
    teams_sha = cb.put_base(store, "zorg-core", "the teams block")
    orphan = cb.put_base(store, "zorg-core", "a block the state no longer has")
    other_sha = cb.put_base(store, "zorg-growth", "growth's own base")
    bases_dir = os.path.join(store.state_dir, "blocks", "zorg-core")
    state = {"checked": "2026-10-20T10:00:00+03:00", "source": "folder", "version": "0.5",
             "blocks": {"scope": {"base_sha": shas[11], "bases": list(shas), "v": "0.5", "host": "h", "checked": None, "user_removed": False},
                        "teams": {"base_sha": teams_sha, "bases": [teams_sha], "v": "1", "host": "h", "checked": None, "user_removed": False}}}
    cb.save_state(store, "zorg-core", state)
    open(os.path.join(bases_dir, "notes.txt"), "w").write("not a base")
    cb.prune_bases(store, "zorg-core", state)
    state = cb.load_state(store, "zorg-core")
    left = sorted(f for f in os.listdir(bases_dir) if f.endswith(".md"))
    check("bases kept to 10", len(state["blocks"]["scope"]["bases"]) == 10
          and len([f for f in left if f[:-3] in state["blocks"]["scope"]["bases"]]) == 10, (len(state["blocks"]["scope"]["bases"]), left))
    check("prune keeps exactly the texts of some block's base_sha or bases — the older versions, an orphan and nothing else go",
          set(left) == {s + ".md" for s in shas[2:] + [teams_sha]}, left)
    check("…and its texts are still readable; the pruned ones are gone",
          cb.get_base(store, "zorg-core", shas[11]) == texts[11] and cb.get_base(store, "zorg-core", teams_sha) == "the teams block"
          and cb.get_base(store, "zorg-core", shas[0]) is None and cb.get_base(store, "zorg-core", orphan) is None, "")
    check("a file that is not a base text is left alone; another repository's bases are not touched",
          os.path.isfile(os.path.join(bases_dir, "notes.txt")) and cb.get_base(store, "zorg-growth", other_sha) == "growth's own base", "")
    before = files_under(store.root)
    cb.prune_bases(store, "zorg-core", state)
    check("pruning again changes nothing", files_under(store.root) == before, "")
    cb.prune_bases(store, "zorg-core", {"checked": None, "source": None, "version": None, "blocks": {}})
    check("a state with no blocks prunes every base text of the repository",
          [f for f in os.listdir(bases_dir) if f.endswith(".md")] == [], os.listdir(bases_dir))
    cb.prune_bases(store, "zorg-empty", {"checked": None, "source": None, "version": None, "blocks": {}})
    check("pruning a repository that has no bases is a no-op", not os.path.exists(os.path.join(store.state_dir, "blocks", "zorg-empty")), "")

# ---- the write allow-list: every write and delete passes cs.check_target
with tempfile.TemporaryDirectory() as d:
    store = cs.Store(os.path.join(d, "vault", "context"))
    elsewhere = os.path.join(d, "elsewhere")
    os.makedirs(elsewhere)
    st_ok = {"checked": None, "source": None, "version": None, "blocks": {}}
    with cs.guard_roots([store.root]):
        sha = cb.put_base(store, "zorg-core", "inside the guard")
        cb.save_state(store, "zorg-core", st_ok)
        inside = cb.get_base(store, "zorg-core", sha) == "inside the guard"
    check("inside the guarded root the writes go through", inside, "")
    with cs.guard_roots([elsewhere]):
        r1 = raises(cs.PathRefused, cb.put_base, store, "zorg-core", "outside the guard")
        r2 = raises(cs.PathRefused, cb.save_state, store, "zorg-core", st_ok)
        r3 = raises(cs.PathRefused, cb.prune_bases, store, "zorg-core", st_ok)
    check("outside the guarded roots put_base, save_state and the pruning delete are refused (PathRefused)",
          all(isinstance(r, cs.PathRefused) for r in (r1, r2, r3)) and cb.get_base(store, "zorg-core", sha) == "inside the guard",
          (r1, r2, r3))

# ---- a repository id that could escape .state/blocks is refused everywhere
with tempfile.TemporaryDirectory() as d:
    store = cs.Store(os.path.join(d, "store"))
    st_ok = {"checked": None, "source": None, "version": None, "blocks": {}}
    ok_sha = cb.put_base(store, "zorg-core", "one")
    before = files_under(d)
    refused = {}
    for rid in ("../escape", "..", ".", "a/b", "Zorg-Core", "zorg_core", "-zorg", "", "zorg-core\n", "zorg core", "zorg-core/", None, 7):
        outcome = [raises(cs.StoreError, cb.load_state, store, rid), raises(cs.StoreError, cb.save_state, store, rid, st_ok),
                   raises(cs.StoreError, cb.put_base, store, rid, "x"), raises(cs.StoreError, cb.get_base, store, rid, ok_sha),
                   raises(cs.StoreError, cb.prune_bases, store, rid, st_ok)]
        refused[repr(rid)] = all(isinstance(o, cs.StoreError) for o in outcome)
    check("load_state, save_state, put_base, get_base and prune_bases refuse any id that is not kebab-case with StoreError",
          all(refused.values()), [k for k, v in refused.items() if not v])
    check("…and nothing was written anywhere", files_under(d) == before, set(files_under(d)) ^ set(before))
    check("a kebab-case id with digits and inner dashes is fine",
          cb.load_state(store, "team-2-core") == {"checked": None, "source": None, "version": None, "blocks": {}}
          and cb.put_base(store, "9-zorg", "x") == sha_of("x"), "")

# ---- last_checked: read-only, never raises
with tempfile.TemporaryDirectory() as d:
    store = cs.Store(os.path.join(d, "store"))
    check("last_checked without a state is None", cb.last_checked(store.root, "nope") is None, "")
    check("last_checked in a store root that is not there is None, and nothing is created",
          cb.last_checked(os.path.join(d, "no", "such", "root"), "zorg-core") is None and not os.path.exists(os.path.join(d, "no")), "")
    cb.save_state(store, "zorg-core", {"checked": "2026-10-20T10:00:00+03:00", "source": "mcp", "version": "0.4", "blocks": {}})
    before = files_under(d)
    check("last_checked is the time the repository was last checked",
          cb.last_checked(store.root, "zorg-core") == "2026-10-20T10:00:00+03:00" and cb.last_checked(store.root, "zorg-growth") is None, "")
    check("…and reading it writes nothing", files_under(d) == before, "")
    cb.save_state(store, "zorg-growth", {"checked": None, "source": None, "version": None, "blocks": {}})
    check("a repository that was never checked has None", cb.last_checked(store.root, "zorg-growth") is None, "")
    open(os.path.join(store.state_dir, "blocks", "zorg-core.json"), "w").write("{oops")
    check("a corrupt state file gives None — last_checked never raises",
          cb.last_checked(store.root, "zorg-core") is None, "")
    check("a bad id, a non-string root and a non-string `checked` give None",
          cb.last_checked(store.root, "../x") is None and cb.last_checked(store.root, None) is None
          and cb.last_checked(None, "zorg-core") is None, "")
    open(os.path.join(store.state_dir, "blocks", "zorg-core.json"), "w").write("{\"checked\": 5, \"blocks\": {}}")
    check("…a checked that is not text is None", cb.last_checked(store.root, "zorg-core") is None, "")
    check("a directory in place of the state file gives None", (os.remove(os.path.join(store.state_dir, "blocks", "zorg-core.json")),
          os.makedirs(os.path.join(store.state_dir, "blocks", "zorg-core.json")), cb.last_checked(store.root, "zorg-core") is None)[2], "")


# ------------------------------------------------------------------ adopt: bases for the blocks already in the context
import ctx_repos as crp  # noqa: E402

CHECKED = "2026-10-20T10:00:00+03:00"
REPO = crp.normalise({"id": "zorg-core", "kind": "bundle", "paths": ["/zorg/core"], "team": "team-alpha"})
PRODUCT = region("product", "0.4", "### Product: Zorg App (shared core view)\n- Platforms: web, app")


def migrated(d, patch=()):
    """A migrated store of the fixture context on a temp HOME; `patch` is [(old, new)] applied to the context first."""
    home, vault = os.path.join(d, "home"), os.path.join(d, "vault")
    os.makedirs(os.path.join(home, ".grow-pm"))
    os.makedirs(os.path.join(vault, "Notes", "_System"))
    text = open(os.path.join(FIX, "context.md"), encoding="utf-8", newline="").read().replace("{{VAULT}}", vault)
    for old, new in patch:
        assert old in text, old
        text = text.replace(old, new, 1)
    ctxp = os.path.join(home, ".grow-pm", "local-context.md")
    for p in (ctxp, os.path.join(vault, "Notes", "_System", "local-context.md")):
        open(p, "w", encoding="utf-8", newline="").write(text)
    copies = co.copies_for(ctxp, text, home=home)
    store = cs.Store(co.store_root_for(text, home=home))
    co.migrate(ctxp, store.root, copies, home, apply=True, now=NOW)
    return home, text, copies, store


def published(mine_store, **over):
    """What zorg-core publishes: the very regions the unedited fixture context holds, and a product block it lacks."""
    pristine = {"scope": region("scope", "0.4", "### Scope of work\nThe user works on Zorg App only."),
                "teams": region("teams", "0.4", "### Teams map\n- Alpha, Beta"), "product": PRODUCT}
    team = cb.find_regions(mine_store.load(), "zorg-core")[0]["team"]["text"] if over.pop("team_from_store", True) else None
    f = {"source": "folder", "version": "0.4", "blocks": pristine, "team": team, "team_source": "folder",
         "team_error": None, "error": None, "checked": CHECKED}
    f.update(over)
    return f


def adopt_apply(home, text, copies, store, repo, fetched, apply=True):
    with cs.guard_roots(co.allowed_roots(home, text)):
        return cb.adopt(store, copies, home, repo, fetched, NOW, apply)


EDIT_SCOPE = ("The user works on Zorg App only.", "The user works on Zorg App only. (my note)")
OLD_TEAMS = ("<!-- zorg-core:begin id=teams v=0.4 -->", "<!-- zorg-core:begin id=teams v=0.3 -->")

with tempfile.TemporaryDirectory() as d:                      # the untouched fixture: every block of the context is the repository's
    home, text, copies, store = migrated(d)
    fetched = published(store)
    tree = files_under(d)
    res = adopt_apply(home, text, copies, store, REPO, fetched, apply=False)
    check("adopt dry run: every block that is in your context and in the repository is a base",
          res["blocks"] == {"scope": "base", "teams": "base", "team": "base"} and res["repo"] == "zorg-core", res)
    check("…a dry run writes nothing (no state, no snapshot, no journal) and says so", res["written"] is False
          and res["snapshot"] is None and files_under(d) == tree, [k for k in files_under(d) if k not in tree])
    check("…the block the repository offers and your context lacks is reported, not adopted", res["new"] == ["product"]
          and res["problems"] == [], res)
    check("…the result carries the documented keys only",
          set(res) == {"repo", "blocks", "why", "new", "problems", "written", "snapshot"}, sorted(res))
    check("…and a reason for each block", set(res["why"]) == {"scope", "teams", "team"}, res["why"])

    records_before = files_under(store.records_dir)
    copies_before = [open(c, "rb").read() for c in copies]
    res = adopt_apply(home, text, copies, store, REPO, fetched)
    state = cb.load_state(store, "zorg-core")
    check("adopt --apply: the same outcome, written", res["blocks"] == {"scope": "base", "teams": "base", "team": "base"}
          and res["written"] is True, res)
    check("…the state holds the three blocks, no others", set(state["blocks"]) == {"scope", "teams", "team"}, state)
    check("…each entry: the hash of the repository's text, the host record, the version, the time, nothing removed",
          all(state["blocks"][k] == {"base_sha": sha_of(v), "bases": [sha_of(v)], "v": "0.4" if k != "team" else "0.2",
                                     "host": h, "checked": CHECKED, "user_removed": None}
              for k, v, h in (("scope", fetched["blocks"]["scope"], "custom.zorg-core-notes"),
                              ("teams", fetched["blocks"]["teams"], "custom.zorg-core-notes"),
                              ("team", fetched["team"], "team.alpha-a"))), state["blocks"])
    check("…where and when the repository was checked", state["checked"] == CHECKED and state["source"] == "folder", state)
    check("…the text of every base is kept as the repository published it",
          cb.get_base(store, "zorg-core", state["blocks"]["scope"]["base_sha"]) == fetched["blocks"]["scope"]
          and cb.get_base(store, "zorg-core", state["blocks"]["team"]["base_sha"]) == fetched["team"], "")
    check("…records and compiled copies are not touched",
          files_under(store.records_dir) == records_before and [open(c, "rb").read() for c in copies] == copies_before, "")
    jr = store.journal_entries()[-1]
    check("…one journal line: provider-adopt from repo:zorg-core with the ids and the snapshot",
          jr["op"] == "provider-adopt" and jr["source"] == "repo:zorg-core" and sorted(jr["ids"]) == ["scope", "team", "teams"]
          and jr["snapshot"] == res["snapshot"] and os.path.isdir(res["snapshot"]) and jr["ts"] == NOW, jr)
    check("…the snapshot is the state before the adopt (no block state in it)",
          not os.path.isdir(os.path.join(res["snapshot"], "state", "blocks")), os.listdir(res["snapshot"]))

    n_journal, state_file = len(store.journal_entries()), files_under(store.state_dir)
    res2 = adopt_apply(home, text, copies, store, REPO, published(store, checked="2026-10-21T09:00:00+03:00"))
    check("adopt again: a block that has a base keeps it — reported as already having one",
          res2["blocks"] == {"scope": "has-base", "teams": "has-base", "team": "has-base"}, res2)
    check("…and nothing is written: no snapshot, no journal line, the state as it was",
          res2["written"] is False and res2["snapshot"] is None and len(store.journal_entries()) == n_journal
          and files_under(store.state_dir) == state_file, res2)

with tempfile.TemporaryDirectory() as d:                      # your edit, another version, a block the repository dropped
    home, text, copies, store = migrated(d, patch=[EDIT_SCOPE, OLD_TEAMS])
    res = adopt_apply(home, text, copies, store, REPO, published(store))
    check("same version, your text differs → edit (the repository's text is the base, yours is your edit)",
          res["blocks"]["scope"] == "edit", res)
    check("another version → no base", res["blocks"]["teams"] == "none", res)
    state = cb.load_state(store, "zorg-core")
    check("…the edit has a base (the repository's), the other version has no state entry",
          set(state["blocks"]) == {"scope", "team"}
          and cb.get_base(store, "zorg-core", state["blocks"]["scope"]["base_sha"]) == published(store)["blocks"]["scope"], state)
    check("…and the plan would read it right: mine is not the base, theirs is → ✎ kept; no entry → ?",
          cb.classify(cb.find_regions(store.load(), "zorg-core")[0]["scope"]["text"], published(store)["blocks"]["scope"],
                      state["blocks"]["scope"]) == "✎"
          and cb.classify(cb.find_regions(store.load(), "zorg-core")[0]["teams"]["text"], published(store)["blocks"]["teams"], None) == "?", "")
    check("…the reason names both versions", "0.3" in res["why"]["teams"] and "0.4" in res["why"]["teams"], res["why"])
    check("an adopted edit counts as adopted in the journal; a block with no base does not",
          sorted(store.journal_entries()[-1]["ids"]) == ["scope", "team"], store.journal_entries()[-1])

with tempfile.TemporaryDirectory() as d:                      # what the repository does not offer
    home, text, copies, store = migrated(d)
    fetched = published(store)
    fetched["blocks"].pop("teams")
    res = adopt_apply(home, text, copies, store, REPO, fetched)
    check("the repository does not offer the block → no base", res["blocks"]["teams"] == "none"
          and "does not offer" in res["why"]["teams"] and "teams" not in cb.load_state(store, "zorg-core")["blocks"], res)

with tempfile.TemporaryDirectory() as d:
    home, text, copies, store = migrated(d)
    res = adopt_apply(home, text, copies, store, REPO, published(store, team=None, team_error="team block: the team card is not there"),
                      apply=False)
    check("the team block could not be built → no base for it, the reason is shown, the other blocks are unaffected",
          res["blocks"] == {"scope": "base", "teams": "base", "team": "none"} and "team card" in res["why"]["team"], res)
    res = adopt_apply(home, text, copies, store, REPO, published(store, team=None), apply=False)
    check("the repository offers no team → no base for the team block", res["blocks"]["team"] == "none"
          and "does not offer" in res["why"]["team"], res)

with tempfile.TemporaryDirectory() as d:                      # a team block that comes in the blocks file itself (an MCP repository)
    home, text, copies, store = migrated(d)
    growth = crp.normalise({"id": "zorg-growth", "kind": "mcp", "team": "team-alpha"})
    gm = cb.find_regions(store.load(), "zorg-growth")[0]
    fetched = {"source": "mcp", "version": "0.1", "blocks": {k: v["text"] for k, v in gm.items()}, "team": None, "team_source": None,
               "team_error": None, "error": None, "checked": CHECKED}
    res = adopt_apply(home, text, copies, store, growth, fetched)
    check("the id 'team' of another repository: its own blocks file is where its team block comes from",
          res["blocks"] == {"growth-metrics": "base", "team": "base"} and set(cb.load_state(store, "zorg-growth")["blocks"]) == {"growth-metrics", "team"}
          and cb.load_state(store, "zorg-growth")["blocks"]["team"]["host"] == "team.alpha-a"
          and cb.load_state(store, "zorg-core")["blocks"] == {}, res)

with tempfile.TemporaryDirectory() as d:                      # an unknown version is not a version
    home, text, copies, store = migrated(d)
    host = [r for r in store.load() if r["id"] == "custom.zorg-core-notes"][0]
    store.write(dict(host, body=host["body"].replace("id=scope v=0.4", "id=scope")))
    fetched = published(store)
    fetched["blocks"]["scope"] = fetched["blocks"]["scope"].replace("id=scope v=0.4", "id=scope")
    res = adopt_apply(home, text, copies, store, REPO, fetched, apply=False)
    check("no version on either side, the texts equal → base (equal text is proof enough)", res["blocks"]["scope"] == "base", res)
    fetched["blocks"]["scope"] = fetched["blocks"]["scope"].replace("only.", "only, and Beta.")
    res = adopt_apply(home, text, copies, store, REPO, fetched, apply=False)
    check("no version on either side, the texts differ → no base (nothing says which of them moved)",
          res["blocks"]["scope"] == "none" and "version" in res["why"]["scope"], res)
    fetched["blocks"]["scope"] = region("scope", "0.4", "### Scope of work\nThe user works on Zorg App only, and Beta.")
    res = adopt_apply(home, text, copies, store, REPO, fetched, apply=False)
    check("your region has no version, the repository's has one and the texts differ → no base",
          res["blocks"]["scope"] == "none", res)

with tempfile.TemporaryDirectory() as d:                      # a block that already has a base is left alone
    home, text, copies, store = migrated(d)
    old = region("scope", "0.1", "### Scope of work\nAlpha only.")
    old_sha = cb.put_base(store, "zorg-core", old)
    cb.save_state(store, "zorg-core", {"checked": "2026-10-01T10:00:00+03:00", "source": "mcp", "version": "0.1",
                                       "blocks": {"scope": {"base_sha": old_sha, "bases": [old_sha], "v": "0.1", "host": "custom.zorg-core-notes",
                                                            "checked": "2026-10-01T10:00:00+03:00", "user_removed": None},
                                          "teams": {"base_sha": None, "bases": [], "v": "", "host": None, "checked": None,
                                                    "user_removed": "2026-10-02"}}})
    res = adopt_apply(home, text, copies, store, REPO, published(store))
    state = cb.load_state(store, "zorg-core")
    check("a block with a state entry keeps it (its base is not replaced by the repository's text)",
          res["blocks"]["scope"] == "has-base" and state["blocks"]["scope"]["base_sha"] == old_sha
          and state["blocks"]["scope"]["bases"] == [old_sha] and state["blocks"]["scope"]["v"] == "0.1", state["blocks"]["scope"])
    check("…the others get their base, and the state's checked time is the new one",
          res["blocks"]["teams"] == "base" and res["blocks"]["team"] == "base" and state["checked"] == CHECKED
          and state["source"] == "folder", state)
    check("…an entry with no base (a removal mark on a region you have put back) is not a base: it gets one, the mark goes",
          state["blocks"]["teams"]["base_sha"] == sha_of(published(store)["blocks"]["teams"])
          and state["blocks"]["teams"]["user_removed"] is None, state["blocks"]["teams"])

with tempfile.TemporaryDirectory() as d:                      # skip_blocks, broken regions, a block that is absent from both
    home, text, copies, store = migrated(d)
    skipping = crp.normalise({"id": "zorg-core", "kind": "bundle", "paths": ["/zorg/core"], "skip_blocks": ["teams"]})
    fetched = published(store)
    fetched["blocks"].pop("teams")                           # fetch drops them already
    res = adopt_apply(home, text, copies, store, skipping, fetched, apply=False)
    check("a skipped block is left out of adopt altogether", set(res["blocks"]) == {"scope", "team"}, res)
    host = [r for r in store.load() if r["id"] == "custom.zorg-core-notes"][0]
    dup = host["body"] + "\n" + region("scope", "0.4", "### Scope of work\nAgain.") + "\n"
    store.write(dict(host, body=dup))
    res = adopt_apply(home, text, copies, store, REPO, published(store), apply=False)
    check("a broken or repeated region is reported and left out — never a base, never 'new'",
          "scope" not in res["blocks"] and "scope" not in res["new"] and res["problems"]
          and {(x["block"], x["why"]) for x in res["problems"]} == {("scope", "duplicate")}, res)
    check("…the other blocks go on", res["blocks"] == {"teams": "base", "team": "base"}, res)

with tempfile.TemporaryDirectory() as d:                      # guards
    home, text, copies, store = migrated(d)
    err = raises(ValueError, cb.adopt, store, copies, home, REPO, dict(published(store), error="MCP unreachable: x", blocks={}, team=None), NOW, True)
    check("a fetch that failed cannot be adopted", isinstance(err, ValueError) and "fetch" in str(err), err)
    check("…and nothing was written", not os.path.isdir(os.path.join(store.state_dir, "blocks")), "")
    real_save = cb.save_state

    def boom(*a, **k):
        raise cs.StoreError("disk full")
    cb.save_state = boom
    try:
        err = raises(cs.StoreError, adopt_apply, home, text, copies, store, REPO, published(store))
    finally:
        cb.save_state = real_save
    check("write order: the base texts first — a crash before the state leaves only orphan texts, no state, no journal line",
          isinstance(err, cs.StoreError) and not os.path.exists(os.path.join(store.state_dir, "blocks", "zorg-core.json"))
          and len(os.listdir(os.path.join(store.state_dir, "blocks", "zorg-core"))) == 3
          and not [j for j in store.journal_entries() if j.get("op") == "provider-adopt"], err)
    res = adopt_apply(home, text, copies, store, REPO, published(store))
    check("…and the next adopt completes it (the same texts are not written twice)", res["written"] is True
          and len(os.listdir(os.path.join(store.state_dir, "blocks", "zorg-core"))) == 3
          and set(cb.load_state(store, "zorg-core")["blocks"]) == {"scope", "teams", "team"}, res)


# ------------------------------------------------------------------ plan: one table per repository, read only
SKIPPING = crp.normalise({"id": "zorg-core", "kind": "bundle", "paths": ["/zorg/core"], "team": "team-alpha", "skip_blocks": ["product"]})
HOST_NOTES = "custom.zorg-core-notes"
CONTROL = re.compile(r"[\x00-\x1f\x7f]")


def plan_of(store, copies, fetched, repo=SKIPPING, all_=False):
    return cb.plan(store, copies, repo, fetched, NOW, all_=all_)


def signs_of(p):
    return {r["block"]: r["sign"] for r in p["rows"]}


def row_of(p, bid):
    return [r for r in p["rows"] if r["block"] == bid][0]


def edit_record(store, rid, old, new):
    r = [x for x in store.load() if x["id"] == rid][0]
    assert old in r["body"], old
    store.write(dict(r, body=r["body"].replace(old, new, 1)))


NEW_SCOPE = region("scope", "0.5", "### Scope of work\nThe user works on Zorg App and Zorg Lite.")
HEAD_OLD = "- **Directory node:** `Dev/Shop/Alpha` — head: Alex One"
HEAD_NEW = "- **Directory node:** `Dev/Shop/Alpha` — head: Alex Prime"

with tempfile.TemporaryDirectory() as d:                      # nothing moved since the adopt
    home, text, copies, store = migrated(d)
    adopt_apply(home, text, copies, store, REPO, published(store))
    fetched = published(store)
    everything = files_under(d)
    p = plan_of(store, copies, fetched)
    check("plan: the documented keys", set(p) >= {"repo", "source", "version", "base_version", "rows", "questions", "changes", "errors"}
          and p["repo"] == "zorg-core" and p["source"] == "folder" and p["version"] == "0.4", sorted(p))
    check("…nothing moved: every block is '=', a skipped block is not shown",
          signs_of(p) == {"scope": "=", "teams": "=", "team": "="} and p["questions"] == 0 and p["changes"] == 0 and p["errors"] == [], p["rows"])
    check("…a row carries the block, the sign, the record that holds it, where the repository's text came from, a note",
          all(set(r) >= {"block", "sign", "host", "source", "note"} for r in p["rows"])
          and {r["block"]: r["host"] for r in p["rows"]} == {"scope": HOST_NOTES, "teams": HOST_NOTES, "team": "team.alpha-a"}
          and all(r["source"] == "folder" for r in p["rows"]), p["rows"])
    check("…the base version is the one most blocks were adopted at", p["base_version"] == "0.4", p["base_version"])
    out = cb.render_plan(p)
    lines = out.splitlines()
    check("render: the header names the repository, the source, the repository's version and ours",
          lines[0] == "zorg-core · джерело: тека · ядро v0.4 · база v0.4", lines[0])
    check("render: the last line counts the questions and the records that would change",
          lines[-1] == "Питань: 0 · зміниться записів: 0", lines[-1])
    check("render: one line per block with its sign, block and record",
          any(l.startswith("=") and "scope" in l and HOST_NOTES in l for l in lines)
          and not any("product" in l for l in lines), out)
    check("plan writes nothing: no state, no snapshot, no journal line", files_under(d) == everything, [k for k in files_under(d) if k not in everything])
    pa = plan_of(store, copies, fetched, all_=True)
    check("all_: a skipped block of the repository is listed, as '·' skipped, with no decision",
          signs_of(pa) == {"scope": "=", "teams": "=", "team": "=", "product": "·"} and pa["questions"] == 0 and pa["changes"] == 0
          and row_of(pa, "product")["note"] == "пропущено", pa["rows"])
    check("without all_ the skipped block is dropped even from a fetch that carried it", "product" in fetched["blocks"] and "product" not in signs_of(p), "")
    host = [r for r in store.load() if r["id"] == HOST_NOTES][0]
    store.write(dict(host, body=host["body"] + "\n" + region("product", "0.4", "### Product: mine\n- my words") + "\n"))
    check("…and the user's own region of a skipped block never shows either", "product" not in signs_of(plan_of(store, copies, fetched)), "")
    check("…unless all_ — then it is '·' too, and its host is shown",
          (row_of(plan_of(store, copies, fetched, all_=True), "product")["sign"], row_of(plan_of(store, copies, fetched, all_=True), "product")["host"])
          == ("·", HOST_NOTES), "")

with tempfile.TemporaryDirectory() as d:                      # the signs
    home, text, copies, store = migrated(d)
    adopt_apply(home, text, copies, store, REPO, published(store))
    f_moved = published(store)
    f_moved["blocks"]["scope"] = NEW_SCOPE
    p = plan_of(store, copies, f_moved)
    row = row_of(p, "scope")
    check("the repository moved on, you did not → '~' (no question; one record would be rewritten)",
          row["sign"] == "~" and p["questions"] == 0 and p["changes"] == 1 and row["host"] == HOST_NOTES
          and "0.4" in row["note"] and "0.5" in row["note"], (row, p["changes"]))
    edit_record(store, HOST_NOTES, "- Alpha, Beta", "- Alpha, Beta, Gamma")
    p = plan_of(store, copies, f_moved)
    check("you edited another block of the same record → '✎'; two blocks in one record rewrite it once",
          signs_of(p) == {"scope": "~", "teams": "✎", "team": "="} and p["changes"] == 1 and p["questions"] == 0, (signs_of(p), p["changes"]))
    f_two = published(store, team=published(store)["team"].replace(HEAD_OLD, HEAD_NEW))
    f_two["blocks"]["scope"] = NEW_SCOPE
    p = plan_of(store, copies, f_two)
    check("…a block in another record that moved is another record: two",
          signs_of(p) == {"scope": "~", "teams": "✎", "team": "~"} and p["changes"] == 2, (signs_of(p), p["changes"]))
    f_new = published(store)
    f_new["blocks"]["okr"] = region("okr", "0.1", "### OKR\n- grow")
    p = plan_of(store, copies, f_new)
    check("a block the repository offers and you lack → '+' (a question; it rewrites no record, and has no host)",
          signs_of(p)["okr"] == "+" and p["questions"] == 1 and p["changes"] == 0 and row_of(p, "okr")["host"] is None, p["rows"])
    f_gone = published(store)
    f_gone["blocks"].pop("scope")
    p = plan_of(store, copies, f_gone)
    check("a block the repository no longer has → '−' (one record would be rewritten)",
          signs_of(p)["scope"] == "−" and p["changes"] == 1 and p["questions"] == 0 and row_of(p, "scope")["source"] is None,
          (signs_of(p), p["changes"]))

with tempfile.TemporaryDirectory() as d:                      # you removed it
    home, text, copies, store = migrated(d)
    adopt_apply(home, text, copies, store, REPO, published(store))
    host = [r for r in store.load() if r["id"] == HOST_NOTES][0]
    store.write(dict(host, body=host["body"].replace(cb.find_regions([host], "zorg-core")[0]["teams"]["text"], "")))
    p = plan_of(store, copies, published(store))
    check("you removed a block that has a base → '✂' (no question; no record changes)",
          signs_of(p) == {"scope": "=", "teams": "✂", "team": "="} and p["questions"] == 0 and p["changes"] == 0, (signs_of(p), p["questions"]))
    check("…the record it was in is shown", row_of(p, "teams")["host"] == HOST_NOTES, p["rows"])
    p = plan_of(store, copies, dict(published(store), blocks={}))
    check("…a block that is gone from both sides is no row at all", "teams" not in signs_of(p), signs_of(p))

with tempfile.TemporaryDirectory() as d:                      # no state: nothing says who moved
    home, text, copies, store = migrated(d, patch=[EDIT_SCOPE])
    p = plan_of(store, copies, published(store))
    check("your text differs and there is no base → '?' (a question); equal texts are '=' with no base",
          signs_of(p) == {"scope": "?", "teams": "=", "team": "="} and p["questions"] == 1 and p["changes"] == 0, signs_of(p))
    check("…base_version of a repository with no base is '—', in the data and in the header",
          p["base_version"] == "—" and cb.render_plan(p).splitlines()[0].endswith("база v—"), (p["base_version"], cb.render_plan(p).splitlines()[0]))

with tempfile.TemporaryDirectory() as d:                      # both changed the team block
    home, text, copies, store = migrated(d)
    adopt_apply(home, text, copies, store, REPO, published(store))
    team0 = published(store)["team"]
    edit_record(store, "team.alpha-a", "- **jira_team_field:** Alpha", "- **jira_team_field:** Alpha (mine)")
    f_both = published(store, team=team0.replace(HEAD_OLD, HEAD_NEW))
    p = plan_of(store, copies, f_both)
    row = row_of(p, "team")
    check("both sides changed → '⚠', a question", row["sign"] == "⚠" and p["questions"] == 1 and p["changes"] == 0, (row, p["questions"]))
    check("…the row carries the lines each side changed against the base",
          any("Alex Prime" in x for x in row["diff"]["theirs"]) and not any("Alex One" in x for x in row["diff"]["theirs"])
          and any("Alpha (mine)" in x for x in row["diff"]["mine"]) and not any("Alex Prime" in x for x in row["diff"]["mine"])
          and any("Alex One" in x for x in row["diff"]["base"]), row.get("diff"))
    check("…at most three lines per side, and the markers are not among them",
          all(len(row["diff"][k]) <= 3 for k in ("theirs", "mine", "base"))
          and not any("zorg-core:" in x for k in ("theirs", "mine", "base") for x in row["diff"][k]), row["diff"])
    out = cb.render_plan(p)
    check("render: the three versions are under the row, as the brief words them",
          "    Ядро тепер каже: " in out and "    Ви писали: " in out and "    Раніше обидва казали: " in out
          and out.index("Ядро тепер каже") < out.index("Ви писали") < out.index("Раніше обидва казали"), out)
    check("…each says what changed: the repository's head, your field, the old head",
          "Alex Prime" in out.split("Ядро тепер каже:")[1].split("Ви писали:")[0]
          and "Alpha (mine)" in out.split("Ви писали:")[1].split("Раніше обидва казали:")[0]
          and "Alex One" in out.split("Раніше обидва казали:")[1], out)
    base_sha = cb.load_state(store, "zorg-core")["blocks"]["team"]["base_sha"]
    os.remove(os.path.join(store.state_dir, "blocks", "zorg-core", base_sha + ".md"))
    p = plan_of(store, copies, f_both)
    out = cb.render_plan(p)
    check("the base text is missing → no 'Раніше обидва казали' line; the other two stay, each side against the other",
          row_of(p, "team")["sign"] == "⚠" and row_of(p, "team")["diff"]["base"] is None and "Раніше обидва" not in out
          and "Ядро тепер каже: " in out and "Ви писали: " in out and "Alex Prime" in out and "Alpha (mine)" in out, out)
    f_long = published(store, team=team0.replace(HEAD_OLD, "- **Directory node:** " + "x" * 300))
    out = cb.render_plan(plan_of(store, copies, f_long))
    said = [l for l in out.splitlines() if "Ядро тепер каже:" in l][0].split("Ядро тепер каже: ", 1)[1]
    check("a line of the diff is clipped to 120 characters", 100 < len(said) <= 120, len(said))

with tempfile.TemporaryDirectory() as d:                      # edits that are not imported yet are part of "mine"
    home, text, copies, store = migrated(d)
    adopt_apply(home, text, copies, store, REPO, published(store))
    for path in copies:
        t = open(path, encoding="utf-8", newline="").read()
        assert EDIT_SCOPE[0] in t
        open(path, "w", encoding="utf-8", newline="").write(t.replace(EDIT_SCOPE[0], EDIT_SCOPE[1], 1))
    records_before = files_under(store.records_dir)
    p = plan_of(store, copies, published(store))
    check("a change typed into local-context.md and not imported yet is seen: '✎'", signs_of(p)["scope"] == "✎", signs_of(p))
    check("…and the plan imported nothing", files_under(store.records_dir) == records_before, "")

with tempfile.TemporaryDirectory() as d:                      # the team block cannot be built; broken regions
    home, text, copies, store = migrated(d)
    adopt_apply(home, text, copies, store, REPO, published(store))
    p = plan_of(store, copies, published(store, team=None, team_error="team block: the team card is not there"))
    row = row_of(p, "team")
    check("the team block cannot be built → '·' unavailable with the reason, and no decision",
          row["sign"] == "·" and row["note"] == "недоступний: team block: the team card is not there"
          and p["questions"] == 0 and p["changes"] == 0 and signs_of(p)["scope"] == "=", row)
    f_blocks_team = published(store, team=None, team_error="team block: x")
    f_blocks_team["blocks"]["team"] = published(store)["team"]
    check("…a team region the blocks file itself carries does not undo that", signs_of(plan_of(store, copies, f_blocks_team))["team"] == "·", "")
    p = plan_of(store, copies, published(store, team=None, team_error="team block: x"), repo=crp.normalise(
        {"id": "zorg-core", "kind": "bundle", "paths": ["/zorg/core"], "skip_blocks": ["team"]}))
    check("…and when the repository skips the team block, it is not shown", "team" not in signs_of(p), signs_of(p))
    p = plan_of(store, copies, published(store, team=None))
    check("the repository offers no team and you hold the block → '−'", signs_of(p)["team"] == "−" and p["changes"] == 1, signs_of(p))
    host = [r for r in store.load() if r["id"] == HOST_NOTES][0]
    store.write(dict(host, body=host["body"] + "\n" + region("scope", "0.4", "### Again") + "\n"))
    p = plan_of(store, copies, published(store))
    out = cb.render_plan(p)
    check("a repeated region is an error, no row: listed in errors and shown as a line",
          "scope" not in signs_of(p) and {(x["block"], x["why"]) for x in p["errors"]} == {("scope", "duplicate")}
          and "помилка: scope — duplicate" in out.splitlines(), (p["errors"], out))
    check("…the other blocks go on, and the summary is still the last line",
          signs_of(p) == {"teams": "=", "team": "="} and out.splitlines()[-1].startswith("Питань: "), out)
    skip_scope = crp.normalise({"id": "zorg-core", "kind": "bundle", "paths": ["/zorg/core"], "skip_blocks": ["scope"]})
    check("an error on a skipped block is not shown either", plan_of(store, copies, published(store), repo=skip_scope)["errors"] == [], "")
    p = plan_of(store, copies, published(store), repo=skip_scope, all_=True)
    check("…unless all_ — an error line, still no row", [x["block"] for x in p["errors"]] == ["scope"] and "scope" not in signs_of(p),
          (p["errors"], signs_of(p)))

with tempfile.TemporaryDirectory() as d:                      # what a server controls is cleaned: control characters out, length bounded
    home, text, copies, store = migrated(d)
    adopt_apply(home, text, copies, store, REPO, published(store))
    f = published(store, version="0.4\x1b[31m" + "9" * 200)
    f["blocks"]["scope"] = region("scope", "0.5\x07\x1b[2J", "### Scope of work\nMoved on.\x1b[31m red")
    p = plan_of(store, copies, f)
    out = cb.render_plan(p)
    header = out.splitlines()[0]
    check("a version from the server: no control character reaches the header, and it is clipped to 80",
          not CONTROL.search(out.replace("\n", "")) and len(header.split("ядро v")[1].split(" · база")[0]) <= 80, repr(header))
    check("…nor the note of a row", signs_of(p)["scope"] == "~" and not CONTROL.search(row_of(p, "scope")["note"])
          and len(row_of(p, "scope")["note"]) <= 300, row_of(p, "scope"))
    edit_record(store, HOST_NOTES, "The user works on Zorg App only.", "The user works on Zorg App only. (mine)")
    p = plan_of(store, copies, f)
    out = cb.render_plan(p)
    check("…nor the lines of the diff (data and text)", row_of(p, "scope")["sign"] == "⚠" and not CONTROL.search(out.replace("\n", ""))
          and not CONTROL.search("".join(x for k in ("theirs", "mine", "base") for x in row_of(p, "scope")["diff"][k])), repr(out))
    f = published(store, team=None, team_error="team block: bad\x1b[31m\n" + "z" * 400)
    note = row_of(plan_of(store, copies, f), "team")["note"]
    check("a long reason from the server is bounded to 300 and has no control character",
          len(note) <= 300 and not CONTROL.search(note) and note.startswith("недоступний: team block: bad"), repr(note))

# ------------------------------------------------------------------ base_version
def entry(v, base="x"):
    return {"base_sha": base, "bases": [base] if base else [], "v": v}


check("base_version: the version most blocks have a base at; a tie goes to the first block by id",
      cb.base_version({"blocks": {"a": entry("0.3"), "b": entry("0.4"), "c": entry("0.4")}}) == "0.4"
      and cb.base_version({"blocks": {"a": entry("0.3"), "b": entry("0.4")}}) == "0.3", "")
check("base_version: a block with no base, or with no version, does not count; none at all is None",
      cb.base_version({"blocks": {"a": entry("0.9", base=None), "b": entry("")}}) is None
      and cb.base_version({"blocks": {}}) is None and cb.base_version({}) is None, "")
check("base_version: a version that is not text (a hand-edited state) does not count and does not raise",
      cb.base_version({"blocks": {"a": entry(["x"]), "b": entry({"k": 1}), "c": entry(4), "d": entry("0.2")}}) == "0.2"
      and cb.base_version({"blocks": {"a": entry(["x"]), "b": entry(["y"])}}) is None, "")
check("base_version: the state's own `version` is not consulted (adopt leaves it unset)",
      cb.base_version({"version": "9.9", "blocks": {"a": entry("0.2")}}) == "0.2", "")

with tempfile.TemporaryDirectory() as d:                      # a removal mark with no base; a block in the state that is gone from both sides
    home, text, copies, store = migrated(d)
    cb.save_state(store, "zorg-core", {"checked": CHECKED, "source": "folder", "version": None, "blocks": {
        "teams": {"base_sha": None, "bases": [], "v": "", "host": None, "checked": None, "user_removed": "2026-10-02"},
        "ghost": {"base_sha": sha_of("x"), "bases": [sha_of("x")], "v": "0.1", "host": HOST_NOTES, "checked": CHECKED, "user_removed": None}}})
    host = [r for r in store.load() if r["id"] == HOST_NOTES][0]
    teams_text = cb.find_regions([host], "zorg-core")[0]["teams"]["text"]
    store.write(dict(host, body=host["body"].replace(teams_text, "")))
    p = plan_of(store, copies, published(store))
    check("a removal mark with no base and no region → '✂'; a state entry nobody has any more is no row",
          signs_of(p)["teams"] == "✂" and "ghost" not in signs_of(p) and p["base_version"] == "0.1", (signs_of(p), p["base_version"]))
    host = [r for r in store.load() if r["id"] == HOST_NOTES][0]
    store.write(dict(host, body=host["body"] + "\n" + teams_text.replace("Alpha, Beta", "Alpha, Beta (mine)") + "\n"))
    check("the region put back, different from the repository's, a mark and no base → '?'",
          signs_of(plan_of(store, copies, published(store)))["teams"] == "?", signs_of(plan_of(store, copies, published(store))))

with tempfile.TemporaryDirectory() as d:                      # a release that bumps only the v= of a block you edited
    home, text, copies, store = migrated(d)
    adopt_apply(home, text, copies, store, REPO, published(store))
    team0 = published(store)["team"]
    edit_record(store, "team.alpha-a", "- **jira_team_field:** Alpha", "- **jira_team_field:** Alpha (mine)")
    p = plan_of(store, copies, published(store, team=team0.replace("id=team v=0.2", "id=team v=0.3")))
    row = row_of(p, "team")
    check("a '⚠' whose repository side changed only the version says so, not an empty side",
          row["sign"] == "⚠" and row["diff"]["theirs"] == ["(лише версія v0.2 → v0.3)"]
          and any("Alpha (mine)" in x for x in row["diff"]["mine"]), row.get("diff"))
    check("…and the text shows it on the line 'Ядро тепер каже'",
          "    Ядро тепер каже: (лише версія v0.2 → v0.3)" in cb.render_plan(p).splitlines(), cb.render_plan(p))


DEL_BASE = region("scope", "0.4", "### Scope\n- a\n- b")
DEL_THEIRS = region("scope", "0.5", "### Scope\n- a")                  # the repository removed "- b" and bumped v=
DEL_MINE = region("scope", "0.4", "### Scope\n- a\n- b\n- mine")
dd = cb._differences(DEL_MINE, DEL_THEIRS, DEL_BASE)
check("a release that removed a line and bumped v= is not 'only the version': the repository's side shows no line, the base the removed one",
      dd["theirs"] == [] and dd["mine"] == ["- mine"] and dd["base"] == ["- b"], dd)
dn = cb._differences(DEL_MINE, DEL_THEIRS, None)
check("…and without the base text neither (each side against the other)", dn["theirs"] == [] and "- mine" in dn["mine"], dn)
dv = cb._differences(DEL_MINE, DEL_BASE.replace("v=0.4", "v=0.5"), DEL_BASE)
check("…while the same words with a new v= still say so", dv["theirs"] == ["(лише версія v0.4 → v0.5)"], dv)


# ------------------------------------------------------------------ apply: one pass, your edits kept, one question per conflicting block
OKR = region("okr", "0.1", "### OKR\n- grow")
TODAY = NOW[:10]


def settle(home, text, copies, store):
    """Import what the records and the copies changed (as every writing command does first) — a test that edits a
    record directly must leave the store in sync before apply, which refuses to run over edits waiting."""
    with cs.guard_roots(co.allowed_roots(home, text)):
        co.apply_sync(store, co.plan_sync(store, copies), copies, home, None, "", NOW)


def apply_of(home, text, copies, store, fetched, choose=None, add=None, repo=SKIPPING):
    with cs.guard_roots(co.allowed_roots(home, text)):
        return cb.apply(store, copies, home, repo, fetched, choose or {}, add or [], NOW)


def body_of(store, rid):
    return [r for r in store.load() if r["id"] == rid][0]["body"]


def journal_of(store):
    path = os.path.join(store.state_dir, "journal.jsonl")
    return [json.loads(l) for l in open(path, encoding="utf-8")] if os.path.isfile(path) else []


def base_text(store, bid, repo="zorg-core"):
    return cb.get_base(store, repo, cb.load_state(store, repo)["blocks"][bid]["base_sha"])


with tempfile.TemporaryDirectory() as d:                      # nothing moved: no write but the time of the check
    home, text, copies, store = migrated(d)
    adopt_apply(home, text, copies, store, REPO, published(store))
    everything = files_under(d)
    state_path = os.path.join(store.state_dir, "blocks", "zorg-core.json")
    res = apply_of(home, text, copies, store, published(store, checked="2026-10-21T09:00:00+03:00"))
    changed = sorted(k for k in set(files_under(d)) | set(everything) if files_under(d).get(k) != everything.get(k))
    check("apply with nothing moved: the documented keys, every block '=', nothing waits",
          set(res) >= {"applied", "pending", "snapshot", "written"} and res["applied"] == {"scope": "=", "teams": "=", "team": "="}
          and res["pending"] == [] and res["changed"] is False, res)
    check("…no snapshot, no journal line, no record or copy written: only the state file, for the time of the check",
          res["snapshot"] is None and res["written"] == [] and changed == [os.path.relpath(state_path, d)]
          and cb.load_state(store, "zorg-core")["checked"] == "2026-10-21T09:00:00+03:00", changed)

with tempfile.TemporaryDirectory() as d:                      # the repository moved one block; you edited another; a new block waits
    home, text, copies, store = migrated(d)
    adopt_apply(home, text, copies, store, REPO, published(store))
    edit_record(store, HOST_NOTES, "- Alpha, Beta", "- Alpha, Beta, Gamma")
    settle(home, text, copies, store)
    teams_base = base_text(store, "teams")
    f = published(store)
    f["blocks"]["scope"], f["blocks"]["okr"] = NEW_SCOPE, OKR
    n_journal = len(journal_of(store))
    res = apply_of(home, text, copies, store, f)
    body = body_of(store, HOST_NOTES)
    check("apply: '~' takes the repository's text, '✎' keeps yours, '+' waits for --add",
          res["applied"] == {"scope": "~", "teams": "✎", "team": "="} and res["pending"] == ["okr"]
          and NEW_SCOPE in body and "Alpha, Beta, Gamma" in body and "id=okr" not in body, (res["applied"], res["pending"]))
    check("…the compiled copies carry it", all(NEW_SCOPE in open(c, encoding="utf-8").read() for c in copies), "")
    state = cb.load_state(store, "zorg-core")
    check("…the base of '~' is the new text, with the old one kept in the history; '✎' keeps its base",
          base_text(store, "scope") == NEW_SCOPE and len(state["blocks"]["scope"]["bases"]) == 2 and state["blocks"]["scope"]["v"] == "0.5"
          and base_text(store, "teams") == teams_base and "okr" not in state["blocks"], state["blocks"])
    check("…the state remembers where the repository was read from and its version",
          state["source"] == "folder" and state["version"] == "0.4" and state["checked"] == CHECKED, state)
    j = journal_of(store)
    check("…one journal line: op, source, versions, the records written, the decision on every block, the snapshot",
          len(j) == n_journal + 1 and j[-1]["op"] == "provider-apply" and j[-1]["source"] == "repo:zorg-core"
          and j[-1]["ids"] == [HOST_NOTES] and j[-1]["decisions"] == {"scope": "~", "teams": "✎", "team": "="}
          and j[-1]["from_v"] == "0.4" and j[-1]["to_v"] == "0.4" and j[-1]["snapshot"] == res["snapshot"] and os.path.isdir(res["snapshot"]), j[-1])
    rec = [r for r in store.load() if r["id"] == HOST_NOTES][0]
    check("…the record written names the repository as its source", rec["source"] == "repo:zorg-core" and rec["verified"] == TODAY, rec)
    check("…the snapshot holds what was there before: the old region and the old state",
          "The user works on Zorg App only." in open(os.path.join(res["snapshot"], "records", HOST_NOTES + ".md"), encoding="utf-8").read()
          and json.load(open(os.path.join(res["snapshot"], "state", "blocks", "zorg-core.json"), encoding="utf-8"))["blocks"]["scope"]["v"] == "0.4", "")
    p = plan_of(store, copies, f)
    check("…the next plan asks only what is still open", signs_of(p) == {"scope": "=", "teams": "✎", "team": "=", "okr": "+"}, signs_of(p))
    res = apply_of(home, text, copies, store, f, add=["okr"])
    check("--add puts the new block at the end of the record that holds most of the repository's blocks",
          res["applied"]["okr"] == "+" and res["pending"] == [] and body_of(store, HOST_NOTES).rstrip("\n").endswith(OKR)
          and cb.load_state(store, "zorg-core")["blocks"]["okr"]["host"] == HOST_NOTES, res["applied"])
    f_gone = dict(f, blocks={k: v for k, v in f["blocks"].items() if k != "okr"})
    res = apply_of(home, text, copies, store, f_gone)
    check("'−' removes the region and its state entry; the record is as it was before the block came",
          res["applied"]["okr"] == "−" and body_of(store, HOST_NOTES) == body and "okr" not in cb.load_state(store, "zorg-core")["blocks"],
          repr(body_of(store, HOST_NOTES)[-120:]))
    check("…and the base text nobody refers to is gone",
          OKR.encode("utf-8") not in files_under(os.path.join(store.state_dir, "blocks", "zorg-core")).values(), "")

with tempfile.TemporaryDirectory() as d:                      # you removed a block
    home, text, copies, store = migrated(d)
    adopt_apply(home, text, copies, store, REPO, published(store))
    host = [r for r in store.load() if r["id"] == HOST_NOTES][0]
    teams_text = cb.find_regions([host], "zorg-core")[0]["teams"]["text"]
    store.write(dict(host, body=host["body"].replace(teams_text + "\n\n", "")))
    settle(home, text, copies, store)
    res = apply_of(home, text, copies, store, published(store))
    entry = cb.load_state(store, "zorg-core")["blocks"]["teams"]
    check("'✂': the state marks it removed today, the base stays, no record is written",
          res["applied"]["teams"] == "✂" and entry["user_removed"] == TODAY and entry["base_sha"] and res["written"] == [] and res["snapshot"], (res, entry))
    res = apply_of(home, text, copies, store, published(store))
    check("…and it is not offered again: the next pass changes nothing", res["applied"]["teams"] == "✂" and res["changed"] is False
          and res["pending"] == [], res)

with tempfile.TemporaryDirectory() as d:                      # no base: '?', and the three answers
    home, text, copies, store = migrated(d, patch=[EDIT_SCOPE])
    f = published(store)
    res = apply_of(home, text, copies, store, f)
    check("'?' waits for --choose; the rest is applied", res["pending"] == ["scope"] and res["applied"] == {"teams": "=", "team": "="}
          and "(my note)" in body_of(store, HOST_NOTES), res)
    res = apply_of(home, text, copies, store, f, choose={"scope": "mine"})
    check("'?' mine: your text stays, the repository's becomes the base — the next plan says '✎'",
          res["applied"]["scope"] == "?" and "(my note)" in body_of(store, HOST_NOTES) and base_text(store, "scope") == f["blocks"]["scope"]
          and signs_of(plan_of(store, copies, f))["scope"] == "✎" and journal_of(store)[-1]["decisions"]["scope"] == "? mine", res)

with tempfile.TemporaryDirectory() as d:
    home, text, copies, store = migrated(d, patch=[EDIT_SCOPE])
    f = published(store)
    res = apply_of(home, text, copies, store, f, choose={"scope": "theirs"})
    check("'?' theirs: the repository's text replaces yours; the next plan is all '='",
          "(my note)" not in body_of(store, HOST_NOTES) and f["blocks"]["scope"] in body_of(store, HOST_NOTES)
          and set(signs_of(plan_of(store, copies, f)).values()) == {"="}, res)

with tempfile.TemporaryDirectory() as d:
    home, text, copies, store = migrated(d)
    adopt_apply(home, text, copies, store, REPO, published(store))
    edit_record(store, HOST_NOTES, "The user works on Zorg App only.", "The user works on Zorg App only. (mine)")
    settle(home, text, copies, store)
    f = published(store)
    f["blocks"]["scope"] = NEW_SCOPE
    res = apply_of(home, text, copies, store, f, choose={"scope": "both"})
    body = body_of(store, HOST_NOTES)
    both = cb.find_regions([{"id": HOST_NOTES, "body": body}], "zorg-core")[0]["scope"]["text"]
    check("'⚠' both: one region with the repository's markers, its text then yours, each under its mark",
          res["applied"]["scope"] == "⚠" and both.startswith("<!-- zorg-core:begin id=scope v=0.5 -->\n<!-- ctx:both theirs -->\n### Scope of work\n"
                                                              "The user works on Zorg App and Zorg Lite.\n<!-- ctx:both mine -->\n")
          and both.endswith("The user works on Zorg App only. (mine)\n<!-- zorg-core:end id=scope -->"), both)
    check("…the base is the repository's text; the next plan keeps it as your edit",
          base_text(store, "scope") == NEW_SCOPE and signs_of(plan_of(store, copies, f))["scope"] == "✎", "")

with tempfile.TemporaryDirectory() as d:                      # what apply refuses
    home, text, copies, store = migrated(d)
    adopt_apply(home, text, copies, store, REPO, published(store))
    f = published(store)
    f["blocks"]["scope"] = NEW_SCOPE
    everything = files_under(d)
    for name, choose, add in (("a choice that is none of theirs | mine | both", {"team": "maybe"}, []),
                              ("a --choose of a block the plan does not have", {"nosuch": "mine"}, []),
                              ("an --add of a block the plan does not have", {}, ["nosuch"])):
        try:
            apply_of(home, text, copies, store, f, choose=choose, add=add)
            raised = False
        except ValueError:
            raised = True
        check("%s: ValueError, nothing written" % name, raised and files_under(d) == everything, "")
    for path in copies:
        t = open(path, encoding="utf-8", newline="").read()
        open(path, "w", encoding="utf-8", newline="").write(t.replace("- Alpha, Beta", "- Alpha, Beta, Gamma", 1))
    everything = files_under(d)
    try:
        apply_of(home, text, copies, store, f)
        refused = False
    except co.Refused:
        refused = True
    check("edits to local-context.md that wait to be imported: refused, nothing written (the caller imports first)",
          refused and files_under(d) == everything, "")
    settle(home, text, copies, store)
    res = apply_of(home, text, copies, store, f, choose={"teams": "theirs"})
    check("a --choose for a block that needs no decision is ignored and said so; your edit stays",
          res["ignored"] == {"teams": "✎"} and "Gamma" in body_of(store, HOST_NOTES) and res["applied"]["scope"] == "~", res)

with tempfile.TemporaryDirectory() as d:                      # a repository text that is not one sound region is never written
    home, text, copies, store = migrated(d)
    adopt_apply(home, text, copies, store, REPO, published(store))
    f = published(store)
    f["blocks"]["scope"] = ("<!-- zorg-core:begin id=scope v=0.5 -->\n### Scope\n<!-- zorg-core:begin id=sneak v=1 -->\nx\n"
                            "<!-- zorg-core:end id=sneak -->\n<!-- zorg-core:end id=scope -->")
    f["team"] = f["team"].replace(HEAD_OLD, HEAD_NEW)
    before = body_of(store, HOST_NOTES)
    res = apply_of(home, text, copies, store, f)
    check("a repository region with another region inside: that block is refused into errors, the rest applies",
          "scope" not in res["applied"] and any(x["block"] == "scope" for x in res["errors"]) and body_of(store, HOST_NOTES) == before
          and res["applied"]["team"] == "~" and HEAD_NEW in body_of(store, "team.alpha-a"), res)

with tempfile.TemporaryDirectory() as d:                      # the write order: base texts, records, state — a crash before the state
    home, text, copies, store = migrated(d)
    adopt_apply(home, text, copies, store, REPO, published(store))
    f = published(store)
    f["blocks"]["scope"] = NEW_SCOPE
    state_path = os.path.join(store.state_dir, "blocks", "zorg-core.json")
    state_before, n_journal = open(state_path, encoding="utf-8").read(), len(journal_of(store))
    real = cb.save_state

    def crash(*a, **k):
        raise RuntimeError("crash before the state")
    cb.save_state = crash
    try:
        apply_of(home, text, copies, store, f)
        crashed = False
    except RuntimeError:
        crashed = True
    finally:
        cb.save_state = real
    orphan = os.path.join(store.state_dir, "blocks", "zorg-core", cs.sha_text(cb.norm(NEW_SCOPE)) + ".md")
    check("a crash before the state: the new base text is there (an orphan), the state and the journal are as they were",
          crashed and os.path.isfile(orphan) and open(state_path, encoding="utf-8").read() == state_before
          and len(journal_of(store)) == n_journal and NEW_SCOPE in body_of(store, HOST_NOTES), crashed)
    settle(home, text, copies, store)
    res = apply_of(home, text, copies, store, f)
    check("…the next pass finds your record already at the repository's text and only sets the base",
          res["applied"]["scope"] == "=" and base_text(store, "scope") == NEW_SCOPE
          and set(signs_of(plan_of(store, copies, f)).values()) == {"="}, res)

REMOVED_NOTE = "репозиторій прибрав блок, а у вас правки — theirs прибере, mine лишить текст як ваш"

with tempfile.TemporaryDirectory() as d:                      # the repository removed a block you edited
    home, text, copies, store = migrated(d)
    adopt_apply(home, text, copies, store, REPO, published(store))
    edit_record(store, HOST_NOTES, "- Alpha, Beta", "- Alpha, Beta\n- my own note on Gamma")
    settle(home, text, copies, store)
    f = published(store)
    f["blocks"].pop("teams")
    p = plan_of(store, copies, f)
    row = row_of(p, "teams")
    check("plan: the repository removed a block you edited → '⚠', a question, with a note that says what each answer does",
          row["sign"] == "⚠" and row["note"] == REMOVED_NOTE and p["questions"] == 1 and p["changes"] == 0, row)
    check("…its three lines: the repository has no such block now, what you wrote, what both said",
          row["diff"]["theirs"] == ["(репозиторій прибрав цей блок)"] and row["diff"]["mine"] == ["- my own note on Gamma"], row["diff"])
    before = body_of(store, HOST_NOTES)
    res = apply_of(home, text, copies, store, f)
    check("apply: it waits for --choose; your text stays", res["pending"] == ["teams"] and body_of(store, HOST_NOTES) == before, res)
    everything = files_under(d)
    try:
        apply_of(home, text, copies, store, f, choose={"teams": "both"})
        refused = False
    except ValueError as e:
        refused = "both" in str(e)
    check("both is not an answer for a block the repository removed: ValueError, nothing written", refused and files_under(d) == everything, "")
    res = apply_of(home, text, copies, store, f, choose={"teams": "mine"})
    body = body_of(store, HOST_NOTES)
    check("mine: the markers go, your text stays where it was, as your own text",
          res["applied"]["teams"] == "⚠" and "zorg-core:begin id=teams" not in body and "zorg-core:end id=teams" not in body
          and "### Teams map\n- Alpha, Beta\n- my own note on Gamma\n" in body and journal_of(store)[-1]["decisions"]["teams"] == "⚠ mine", body)
    check("…the state forgets the block, and the next plan has no row for it",
          "teams" not in cb.load_state(store, "zorg-core")["blocks"] and "teams" not in signs_of(plan_of(store, copies, f)), "")

with tempfile.TemporaryDirectory() as d:
    home, text, copies, store = migrated(d)
    adopt_apply(home, text, copies, store, REPO, published(store))
    edit_record(store, HOST_NOTES, "- Alpha, Beta", "- Alpha, Beta\n- my own note on Gamma")
    settle(home, text, copies, store)
    f = published(store)
    f["blocks"].pop("teams")
    res = apply_of(home, text, copies, store, f, choose={"teams": "theirs"})
    check("theirs: the region goes, your edit with it (it stays in the snapshot); the state forgets the block",
          res["applied"]["teams"] == "⚠" and "Teams map" not in body_of(store, HOST_NOTES) and "teams" not in cb.load_state(store, "zorg-core")["blocks"]
          and "my own note on Gamma" in open(os.path.join(res["snapshot"], "records", HOST_NOTES + ".md"), encoding="utf-8").read(), res)

with tempfile.TemporaryDirectory() as d:                      # a region with no base that the repository does not offer
    home, text, copies, store = migrated(d)
    f = published(store)
    f["blocks"].pop("teams")
    p = plan_of(store, copies, f)
    check("plan: no base and the repository does not offer it → '?', not a silent removal",
          row_of(p, "teams")["sign"] == "?" and "theirs прибере, mine лишить текст як ваш" in row_of(p, "teams")["note"], row_of(p, "teams"))
    res = apply_of(home, text, copies, store, f)
    check("apply: it waits; the region stays", res["pending"] == ["teams"] and "id=teams" in body_of(store, HOST_NOTES), res)
    res = apply_of(home, text, copies, store, f, choose={"teams": "mine"})
    check("…mine keeps the text without the markers", "id=teams" not in body_of(store, HOST_NOTES)
          and "### Teams map\n- Alpha, Beta\n" in body_of(store, HOST_NOTES) and "teams" not in signs_of(plan_of(store, copies, f)), res)

# --- v3.13.0 Task 11: the namespace a plan, an adopt and an apply read your regions in
check("namespace_of: the fetch's (a registration with no namespace takes the core manifest's), else the registration's",
      cb.namespace_of({"namespace": "zorg-context"}, {"namespace": "zorg-core"}) == "zorg-core"
      and cb.namespace_of({"namespace": "zorg-context"}, {}) == "zorg-context"
      and cb.namespace_of({"namespace": "zorg-context"}, {"namespace": ""}) == "zorg-context", "")

print("RESULT: GREEN ✅" if not fails else "RESULT: RED ❌")
sys.exit(1 if fails else 0)
