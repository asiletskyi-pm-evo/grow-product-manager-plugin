#!/usr/bin/env python3
"""TC-ctx-3232-overlay-read — what the overlay's `ignore` and `alias` do to what a skill reads (since v3.23.0).

`ignore` changes no text: the resolver gives no slot a block candidate that holds a line an applied ignore finds (the
whole block for an ignore with no path) — no «також», no divergence — and `ctx explain` shows the candidate as lost to the
overlay with its reason. A held ignore (its line is gone from the core) gives the candidate back. `alias` changes no
text either: the names it adds join the entity card the path names (`ctx_entity`), and `ctx_overlay.store_aliases`
reads them from the store's regions. On the fictional fixture testing/fixtures/ctx-repos/context.md ("Zorg").
Semantics: references/context-protocol.md §5n. Stdlib only; run from the repo root.
"""
import os, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import ctx_entity as ce  # noqa: E402
import ctx_ops as co  # noqa: E402
import ctx_overlay as ov  # noqa: E402
import ctx_resolve as rv  # noqa: E402
import ctx_slots as sl  # noqa: E402
import ctx_store as cs  # noqa: E402

FIX = os.path.join(ROOT, "testing", "fixtures", "ctx-repos")
NOW = "2026-10-20T10:00:00+03:00"
REPOS = [{"id": "zorg-core", "namespace": "zorg-core", "rank": 1000, "products": []},
         {"id": "zorg-growth", "namespace": "zorg-growth", "rank": 500, "products": []}]
fails = 0


def check(name, cond, detail=""):
    global fails
    fails += not cond
    print(("✅" if cond else "❌"), name, ("" if cond else "-> " + str(detail)[:900]))


MINE_KM = ("- **Jira Project Key:** PROJ\n", "- **Jira Project Key:** PROJ\n\n#### Key Metrics\n- my own numbers: CR 3.1%\n")
GROWTH_KM = ("#### Growth metrics\n- **North star:** weekly active shoppers\n",
             "#### Key Metrics\n- **North star:** weekly active shoppers\n- Revenue +38% this year\n")


def migrated(d, edits):
    home, vault = os.path.join(d, "home"), os.path.join(d, "vault")
    os.makedirs(os.path.join(home, ".grow-pm"))
    os.makedirs(os.path.join(vault, "Notes", "_System"))
    text = open(os.path.join(FIX, "context.md"), encoding="utf-8", newline="").read().replace("{{VAULT}}", vault)
    for old, new in edits:
        assert old in text, old
        text = text.replace(old, new, 1)
    ctxp = os.path.join(home, ".grow-pm", "local-context.md")
    for p in (ctxp, os.path.join(vault, "Notes", "_System", "local-context.md")):
        open(p, "w", encoding="utf-8", newline="").write(text)
    copies = co.copies_for(ctxp, text, home=home)
    store = cs.Store(co.store_root_for(text, home=home))
    co.migrate(ctxp, store.root, copies, home, apply=True, now=NOW)
    return home, text, copies, store


def put(home, text, store, repo, ops):
    with cs.guard_roots(co.allowed_roots(home, text)):
        ov.save(store.root, repo, ov.parse(ov.dump({"schema": ov.SCHEMA, "repo": repo, "ops": [
            dict({"expects": 1}, **o) for o in ops]})))


def answer(store, copies, slot, mem):
    sctx = rv.slot_context(store, copies, REPOS, "Zorg App", NOW, mem=mem)
    got = rv.slot_answers(sctx, slot)
    return got[0]["result"] if got else None


def explain_rows(store, copies, slot, mem):
    sctx = rv.slot_context(store, copies, REPOS, "Zorg App", NOW, mem=mem)
    got = rv.slot_answers(sctx, slot)
    return rv._rows(got[0]["result"], got[0]["candidates"], [], None)


with tempfile.TemporaryDirectory() as d:
    home, text, copies, store = migrated(d, [MINE_KM, GROWTH_KM])
    mem = sl.empty_memory()
    sl.add_binding(mem, "zorg-growth", "growth-metrics", None, "product.key_metrics", None)
    r = answer(store, copies, "product.key_metrics", mem)
    check("without an overlay: yours wins, the bound block is «також»",
          r["shown"][0]["level"] == "mine" and [c["source"] for c in r["also"]] == ["zorg-growth"], r)

    put(home, text, store, "zorg-growth", [{"id": "rev", "target": {"block": "growth-metrics", "path": 'match:"+38%"'},
                                            "op": "ignore", "reason": "першоджерело каже +30%"}])
    r = answer(store, copies, "product.key_metrics", mem)
    check("an applied ignore: the block is no candidate any more — no «також»",
          r["shown"][0]["level"] == "mine" and r["also"] == [] and r["why"] == rv.WHY_ONLY, r)
    rows = explain_rows(store, copies, "product.key_metrics", mem)
    lost = [x for x in rows if x["outcome"] == "lost"]
    check("explain: the block is shown as lost to the overlay, with its reason",
          len(lost) == 1 and lost[0]["source"] == "zorg-growth" and lost[0]["reason"] == "оверлей: ignore rev — першоджерело каже +30%",
          rows)

    put(home, text, store, "zorg-growth", [{"id": "rev", "target": {"block": "growth-metrics", "path": 'match:"EBITDA +38%"'},
                                            "op": "ignore", "reason": "r"}])
    r = answer(store, copies, "product.key_metrics", mem)
    check("a held ignore (the line is not in the block): the block is a candidate again",
          [c["source"] for c in r["also"]] == ["zorg-growth"], r)

    put(home, text, store, "zorg-growth", [{"id": "all", "target": {"block": "growth-metrics"}, "op": "ignore", "reason": "r"}])
    r = answer(store, copies, "product.key_metrics", mem)
    check("an ignore of the whole block: no candidate", r["also"] == [], r)

    put(home, text, store, "zorg-core", [{"id": "x", "target": {"block": "growth-metrics"}, "op": "ignore", "reason": "r"}])
    r = answer(store, copies, "product.key_metrics", mem)
    check("an ignore in another repository's overlay does nothing to this one's block (the growth file still ignores)",
          r["also"] == [], r)
    os.remove(ov.path_of(store.root, "zorg-growth"))
    r = answer(store, copies, "product.key_metrics", mem)
    check("…and with the growth overlay gone, the block is back", [c["source"] for c in r["also"]] == ["zorg-growth"], r)

    open(ov.path_of(store.root, "zorg-core"), "w", encoding="utf-8").write("not: [valid\n")
    r = answer(store, copies, "product.key_metrics", mem)
    check("an unreadable overlay ignores nothing and does not break the read", [c["source"] for c in r["also"]] == ["zorg-growth"], r)

    # mine removed: with the block ignored the slot is empty, not a divergence
    with tempfile.TemporaryDirectory() as d2:
        home2, text2, copies2, store2 = migrated(d2, [GROWTH_KM])
        put(home2, text2, store2, "zorg-growth", [{"id": "all", "target": {"block": "growth-metrics"}, "op": "ignore"}])
        r = answer(store2, copies2, "product.key_metrics", mem)
        check("your text absent and the only block ignored: nothing is shown", r is None or r["shown"] == [], r)

# --- review v3.23.0 tasks 3–4, I1: positions, not line texts
TWO = ("#### Growth metrics\n- **North star:** weekly active shoppers\n",
       "#### Key Metrics\n| a | b |\n|---|---|\n| CR | 3% |\n\n#### OKR\n| a | b |\n|---|---|\n| Revenue | +38% |\n")
with tempfile.TemporaryDirectory() as d:
    home, text, copies, store = migrated(d, [MINE_KM, TWO])
    m1 = sl.empty_memory()
    sl.add_binding(m1, "zorg-growth", "growth-metrics", "Key Metrics", "product.key_metrics", None)
    put(home, text, store, "zorg-growth", [{"id": "okr", "target": {"block": "growth-metrics", "path": "#OKR"}, "op": "ignore"}])
    r = answer(store, copies, "product.key_metrics", m1)
    check("an ignore of a sibling subsection that shares a table separator leaves this one a candidate",
          [c["source"] for c in r["also"]] == ["zorg-growth"], r)
    m2 = sl.empty_memory()
    sl.add_binding(m2, "zorg-growth", "growth-metrics", None, "product.key_metrics", None)
    r = answer(store, copies, "product.key_metrics", m2)
    t = r["also"][0]["text"] if r["also"] else ""
    check("a candidate bound to the whole block keeps its other parts; the ignored subsection is cut out",
          "| CR | 3% |" in t and "Revenue" not in t and "#### OKR" not in t, t)

# ------------------------------------------------------------------ alias
with tempfile.TemporaryDirectory() as d:
    home, text, copies, store = migrated(d, [])
    put(home, text, store, "zorg-core", [{"id": "names", "target": {"block": "team", "path": "#Team: Alpha"}, "op": "alias",
                                          "value": ["Alpha (A)", "Alpha Team (A)"]}])
    got = ov.store_aliases(store.root, REPOS)
    check("store_aliases: the names an alias adds, with the heading it names", got == [("Team: Alpha", ["Alpha (A)", "Alpha Team (A)"])], got)
    check("store_aliases never raises: a store that is not there gives none", ov.store_aliases(os.path.join(d, "nope"), REPOS) == [], "")
    cards = [{"path": "Core/Teams/team-alpha.md", "label": "Alpha", "slug": "team-alpha", "aliases": ["Team: Alpha"], "kind": "team"},
             {"path": "Core/Teams/team-beta.md", "label": "Beta", "slug": "team-beta", "aliases": [], "kind": "team"}]
    out = ce.with_overlay_aliases(cards, got)
    check("with_overlay_aliases: the card the name answers gets the names, the other none, the input untouched",
          out[0]["aliases"] == ["Team: Alpha", "Alpha (A)", "Alpha Team (A)"] and out[1]["aliases"] == []
          and cards[0]["aliases"] == ["Team: Alpha"], out)
    out = ce.with_overlay_aliases(cards, [("Alpha", ["Alpha (A)"])])
    check("…a name that is the card's label answers too", out[0]["aliases"] == ["Team: Alpha", "Alpha (A)"], out)

print("RESULT: GREEN ✅" if not fails else "RESULT: RED ❌")
sys.exit(1 if fails else 0)
