#!/usr/bin/env python3
"""TC-ctx-3130-blocks — scripts/ctx_blocks.py: regions in the context records and the class of each block (since v3.13.0).

Pure functions on the fictional "Zorg": `norm` (the text two blocks are compared by), `find_regions` (a
repository's managed regions in the records' bodies — inside a section wrapper too, found in whichever record
holds them now, and the structure errors: a duplicate id, a broken marker, a nested region) and `classify`
(the plan's sign for one block from mine / theirs / the stored base — the golden cases of the spec's tables
B5 and B6, and the order the rules apply in). One test runs on a real migrated store. The persistent side: a
repository's block state (`.state/blocks/<repo>.json`) and the base texts (`.state/blocks/<repo>/<sha>.md`) —
load/save, bases kept to ten, pruning, the write allow-list, refused repository ids and the read-only
`last_checked`. Semantics: references/context-provider-protocol.md. Stdlib only; run from the repo root.
"""
import json, os, shutil, sys, tempfile

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


print("RESULT: GREEN ✅" if not fails else "RESULT: RED ❌")
sys.exit(1 if fails else 0)
