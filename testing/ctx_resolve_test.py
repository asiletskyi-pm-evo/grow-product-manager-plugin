#!/usr/bin/env python3
"""TC-ctx-3150-resolve — scripts/ctx_resolve.py and ctx_slots.bindings_of: the candidates of a slot (since v3.15.0).

A slot is answered by your own text (outside the managed regions, under any of its catalogue names or a name you
mapped), by a block a binding ties to it (your binding, the `slot=` attribute of the block's base, the plugin's own
binding of the `team` block) wherever that block sits, and — as in v3.14.1 — by an unbound block of the same product or
team record when your text has nothing. Each candidate says where it is, whose it is, which version, when it was checked,
whether you edited it, whether it is a core rule, and whether it can be placed at all. Read only: nothing is written.
On the fictional fixture testing/fixtures/ctx-repos/context.md ("Zorg"), migrated into a temp HOME and vault.
Stdlib only; run from the repo root.
"""
import os, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import ctx_blocks as cb  # noqa: E402
import ctx_common as cc  # noqa: E402
import ctx_ops as co  # noqa: E402
import ctx_read as cr  # noqa: E402
import ctx_repos as crp  # noqa: E402
import ctx_resolve as rv  # noqa: E402
import ctx_slots as sl  # noqa: E402
import ctx_store as cs  # noqa: E402

REPOS_FIX = os.path.join(ROOT, "testing", "fixtures", "ctx-repos")
NOW = "2026-10-20T10:00:00+03:00"
CHECKED = "2026-10-20T10:00:00+03:00"
CAT = sl.load_catalogue()
REPOS = [{"id": "zorg-core", "namespace": "zorg-core", "rank": 1000, "products": []},
         {"id": "zorg-growth", "namespace": "zorg-growth", "rank": 500, "products": []}]
KEYS = {"slot", "source", "level", "record", "block", "ns", "version", "checked", "edited", "overlaid", "rule", "how", "heading",
        "text", "rank", "placed", "place", "sub"}
STATE_LINE = "стан блоків zorg-core не прочитано — атрибути slot= і policy=rule його блоків невідомі"
fails = 0


def check(name, cond, detail=""):
    global fails
    fails += not cond
    print(("✅" if cond else "❌"), name, ("" if cond else "-> " + str(detail)[:900]))


def read(*parts):
    return open(os.path.join(*parts), encoding="utf-8", newline="").read()


FIXTURE = read(REPOS_FIX, "context.md")


def region(text, ns, bid):
    """The whole region `bid` of `ns` in `text`, markers included."""
    return cb.find_regions([{"id": "x", "body": text}], ns)[0][bid]["text"]


TEAM = region(FIXTURE, "zorg-core", "team")
SCOPE = region(FIXTURE, "zorg-core", "scope")
GROWTH = region(FIXTURE, "zorg-growth", "growth-metrics")


class Env:
    """A migrated store over the ctx-repos fixture: temp HOME, temp vault and its mirror."""

    def __init__(self, d, edits=()):
        self.home = os.path.join(d, "home")
        self.vault = os.path.join(d, "vault")
        os.makedirs(os.path.join(self.home, ".grow-pm"))
        os.makedirs(os.path.join(self.vault, "Notes", "_System"))
        self.text = FIXTURE.replace("{{VAULT}}", self.vault)
        for old, new in edits:
            assert old in self.text, old
            self.text = self.text.replace(old, new, 1)
        self.ctx = os.path.join(self.home, ".grow-pm", "local-context.md")
        for p in (self.ctx, os.path.join(self.vault, "Notes", "_System", "local-context.md")):
            open(p, "w", encoding="utf-8", newline="").write(self.text)
        self.copies = co.copies_for(self.ctx, self.text, home=self.home)
        self.store = cs.Store(co.store_root_for(self.text, home=self.home))
        co.migrate(self.ctx, self.store.root, self.copies, self.home, apply=True, now=NOW)

    def records(self):
        return cr._live_view(self.store, self.copies, NOW)[0]

    def state(self, repo, blocks, checked=CHECKED):
        """What adopt/apply leave: per block its version, check and bases — `blocks` {id: (v, [base texts, oldest first])}."""
        with cs.guard_roots(co.allowed_roots(self.home, self.text)):
            entries = {}
            for bid, (v, bases) in blocks.items():
                shas = [cb.put_base(self.store, repo, t) for t in bases]
                entries[bid] = {"base_sha": shas[-1] if shas else None, "bases": shas, "v": v, "host": None,
                                "checked": checked, "user_removed": None}
            cb.save_state(self.store, repo, {"checked": checked, "source": "folder", "version": "0.4", "blocks": entries})


def product_of(recs, title):
    return next((r for r in recs if r["type"] == "product" and r["title"].split(":", 1)[-1].strip() == title), None)


def teams_of(recs, prod):
    """The teams `ctx read` reads for the product (its siblings under the organisation)."""
    return [r for r in recs if r["type"] == "team" and (prod is None or r.get("parent") == prod.get("parent"))]


def cands(e, slot, product="Zorg App", repos=REPOS, mem=None, teams=None, **kw):
    recs = e.records()
    prod = product_of(recs, product) if product else None
    mem = mem or sl.empty_memory()
    binds, _ = sl.bindings_of(e.store, repos, mem)
    return rv.candidates(slot, CAT, recs, prod, teams_of(recs, prod) if teams is None else teams, repos, mem, e.store, binds,
                         **kw)


def memory(*bindings, aliases=()):
    mem = sl.empty_memory()
    for b in bindings:
        sl.add_binding(mem, *b)
    for a in aliases:
        sl.add_alias(mem, *a)
    return mem


def by(cs_, **kw):
    return [c for c in cs_ if all(c.get(k) == v for k, v in kw.items())]


def tree(*roots):
    out = {}
    for root in roots:
        for d, _, files in os.walk(root):
            for f in files:
                p = os.path.join(d, f)
                st = os.stat(p)
                out[p] = (st.st_size, st.st_mtime_ns)
    return out


TEAM_MEMBERS = ("- **Jira Team ID:** <team-uuid>\n",
                "- **Jira Team ID:** <team-uuid>\n\n#### Team Members\n\n| Name | Role |\n|---|---|\n| Own Person | PM |\n")
TEAM_TO_CUSTOM = [(TEAM + "\n\n", ""), ("## Zorg Core Notes\n\n", "## Zorg Core Notes\n\n" + TEAM + "\n\n")]
BETA = ("<!-- zorg-growth:end id=team -->\n", "<!-- zorg-growth:end id=team -->\n\n### Team: Beta (B)\n\n- **Jira Team ID:** <beta-uuid>\n")
LITE = ("### Team: Alpha (A)\n", "### Product: Zorg Lite\n\n- **Jira Project Key:** LITE\n\n### Team: Alpha (A)\n")

# ------------------------------------------------------------------ bindings_of
with tempfile.TemporaryDirectory() as d:
    e = Env(d)
    binds, problems = sl.bindings_of(e.store, REPOS, sl.empty_memory())
    plugin = [{"slot": "team.members", "sub": "Members", "team": None, "how": "plugin"}]
    check("the plugin binds the team block of every registered repository to team.members only (ruling: no jira_project_key)",
          binds == {("zorg-core", "team"): plugin, ("zorg-growth", "team"): plugin} and problems == [], (binds, problems))
    mem = memory(("zorg-core", "team", "Members", "team.members", "team.alpha-a"), ("zorg-core", "scope", None, "product.scope", None))
    binds, problems = sl.bindings_of(e.store, REPOS, mem)
    check("your binding replaces the plugin's for that block, and keys a block by its namespace",
          binds[("zorg-core", "team")] == [{"slot": "team.members", "sub": "Members", "team": "team.alpha-a", "how": "memory"}]
          and binds[("zorg-core", "scope")] == [{"slot": "product.scope", "sub": None, "team": None, "how": "memory"}]
          and binds[("zorg-growth", "team")] == plugin and problems == [], binds)
    other = [{"id": "zorg-x", "namespace": "zorg-core", "rank": 7, "products": []}]
    binds, _ = sl.bindings_of(e.store, other, memory(("zorg-x", "scope", None, "product.scope", None),
                                                    ("zorg-nowhere", "scope", None, "product.scope", None)))
    check("a binding names the repository; the block is keyed by the registration's namespace, else by the id",
          ("zorg-core", "scope") in binds and ("zorg-nowhere", "scope") in binds and ("zorg-x", "scope") not in binds, binds)

    e.state("zorg-core", {"scope": ("0.4", [SCOPE.replace("v=0.4 -->", "v=0.4 slot=product.scope,org.structure -->")]),
                          "team": ("0.2", [TEAM.replace("v=0.2 -->", "v=0.2 slot=team.members -->")]),
                          "teams": ("0.4", [region(FIXTURE, "zorg-core", "teams")])})
    binds, problems = sl.bindings_of(e.store, REPOS, sl.empty_memory())
    check("slot= of a block's base binds it, one binding per slot; it replaces the plugin's for the team block",
          binds[("zorg-core", "scope")] == [{"slot": "product.scope", "sub": None, "team": None, "how": "marker"},
                                            {"slot": "org.structure", "sub": None, "team": None, "how": "marker"}]
          and binds[("zorg-core", "team")] == [{"slot": "team.members", "sub": None, "team": None, "how": "marker"}]
          and ("zorg-core", "teams") not in binds and binds[("zorg-growth", "team")] == plugin and problems == [], binds)
    binds, _ = sl.bindings_of(e.store, REPOS, memory(("zorg-core", "scope", None, "product.key_metrics", None)))
    check("your binding and slot= on one block: only yours (Review Focus 2)",
          binds[("zorg-core", "scope")] == [{"slot": "product.key_metrics", "sub": None, "team": None, "how": "memory"}], binds)

for label, marker, want in (("a word that only ends in slot=", "v=0.4 xslot=product.scope -->", None),
                            ("slot= with nothing after it", "v=0.4 slot= -->", None),
                            ("slot= before v=, empty items skipped", "slot=product.scope,,org.structure v=0.4 -->",
                             ["product.scope", "org.structure"]),
                            ("slot= that is not a slot id", "v=0.4 slot=Scope! -->", None)):
    with tempfile.TemporaryDirectory() as d:
        e = Env(d)
        e.state("zorg-core", {"scope": ("0.4", [SCOPE.replace("v=0.4 -->", marker)])})
        binds, _ = sl.bindings_of(e.store, REPOS, sl.empty_memory())
        got = [b["slot"] for b in binds.get(("zorg-core", "scope"), [])] or None
        check("slot= is read as a whole word: %s" % label, got == want, binds)
check("marker_slots reads the begin marker only, never the text inside",
      sl.marker_slots("<!-- zorg-core:begin id=a v=1 slot=team.members -->\nslot=org.structure\n<!-- zorg-core:end id=a -->")
      == ["team.members"] and sl.marker_slots(None) == [] and sl.marker_slots("slot=team.members") == [], "")

with tempfile.TemporaryDirectory() as d:
    e = Env(d)
    e.state("zorg-core", {"team": ("0.2", [TEAM])})
    open(os.path.join(e.store.state_dir, "blocks", "zorg-core.json"), "w", encoding="utf-8").write("{ not json")
    binds, problems = sl.bindings_of(e.store, REPOS, memory(("zorg-core", "scope", None, "product.scope", None)))
    check("a block state that cannot be read is one line in problems, not an exception; the rest still binds",
          problems == [STATE_LINE] and binds[("zorg-core", "team")] == plugin
          and binds[("zorg-core", "scope")][0]["how"] == "memory", (binds, problems))
    got = cands(e, "team.members")
    check("…and the candidates are still there, with no check date", len(got) == 1 and got[0]["how"] == "plugin"
          and got[0]["version"] == "0.2" and got[0]["checked"] is None and got[0]["rule"] is False, got)

# ------------------------------------------------------------------ candidates: yours and a bound block
with tempfile.TemporaryDirectory() as d:
    e = Env(d, edits=[TEAM_MEMBERS])
    e.state("zorg-core", {"team": ("0.2", [TEAM])})
    before = tree(e.home, e.vault)
    got = cands(e, "team.members")
    check("every candidate carries the agreed keys", got and all(set(c) == KEYS for c in got), [sorted(c) for c in got])
    mine, repo = by(got, level="mine"), by(got, level="repo")
    check("your Team Members and the bound team block are two candidates: mine and repo", len(got) == 2 and len(mine) == 1
          and len(repo) == 1, got)
    m, r = (mine or [{}])[0], (repo or [{}])[0]
    own = cc.strip_managed_regions(next(x for x in e.records() if x["id"] == "team.alpha-a")["body"])
    check("…your text is what ctx_read._subsection gives", m.get("text") == cr._subsection(own, "Team Members"), m)
    check("…yours: source mine, the team record, the heading, its own text", m.get("source") == "mine"
          and m.get("record") == "team.alpha-a" and m.get("heading") == "Team Members" and "Own Person" in m.get("text", "")
          and m.get("block") is None and m.get("how") is None and m.get("placed") is True and m.get("place") == "team.alpha-a", m)
    check("…the block: the plugin's binding, the Members subsection only, its version, check and rank",
          r.get("source") == "zorg-core" and r.get("ns") == "zorg-core" and r.get("block") == "team" and r.get("how") == "plugin"
          and r.get("text", "").startswith("#### Members") and "Bea Two" in r.get("text", "") and "Team card" not in r.get("text", "")
          and "<!--" not in r.get("text", "") and r.get("version") == "0.2" and r.get("checked") == "2026-10-20"
          and r.get("rank") == 1000 and r.get("edited") is False and r.get("rule") is False and r.get("placed") is True
          and r.get("record") == "team.alpha-a" and r.get("place") == "team.alpha-a", r)
    check("…the subsection a binding names is on the candidate (explain prints it and the command that places it): sub",
          r.get("sub") == "Members" and m.get("sub") is None
          and by(cands(e, "org.structure", mem=memory(("zorg-core", "teams", None, "org.structure", None))), block="teams")[0]["sub"] is None, got)
    jira = cands(e, "product.jira_key")
    check("the plugin does not bind the team block's jira_project_key line (ruling): only your Jira Project Key",
          [c["text"] for c in jira] == ["- **Jira Project Key:** PROJ\n"] and [c["level"] for c in jira] == ["mine"], jira)
    JIRA = memory(("zorg-core", "team", None, "product.jira_key", None))
    jira = cands(e, "product.jira_key", mem=JIRA)
    check("one value: your field line, and — when you bind the block — the field line inside the team block",
          [c["text"] for c in jira] == ["- **Jira Project Key:** PROJ\n", "- **jira_project_key:** PROJ (others: LEGACY)\n"]
          and [c["level"] for c in jira] == ["mine", "repo"] and jira[1]["place"] == "product.zorg-app"
          and jira[1]["heading"] == "jira_project_key" and jira[1]["how"] == "memory", jira)
    check("the growth team block, plugin-bound too, has no Members subsection: no candidate", not by(got, source="zorg-growth"), got)
    check("a product slot's block in a team record answers only when that team is read (spec §4.4)",
          [c["level"] for c in cands(e, "product.jira_key", mem=JIRA, teams=[])] == ["mine"], cands(e, "product.jira_key", mem=JIRA, teams=[]))
    check("candidates and bindings_of write nothing", tree(e.home, e.vault) == before, "")
    check("an unknown slot has no candidates", rv.candidates("team.nowhere", CAT, e.records(), None, [], REPOS,
                                                              sl.empty_memory(), e.store, {}) == [], "")

# ------------------------------------------------------------------ the unbound block found by name (as v3.14.1)
with tempfile.TemporaryDirectory() as d:
    e = Env(d)
    e.state("zorg-core", {"team": ("0.2", [TEAM])})
    got = cands(e, "team.members", repos=[])
    body = next(x for x in e.records() if x["id"] == "team.alpha-a")["body"]
    check("without bindings an unbound block of the team record answers by name, as cr._lookup did",
          len(got) == 1 and got[0]["how"] == "name" and got[0]["level"] == "repo"
          and got[0]["text"] == cr._lookup(body, "Members", field=False)[0] and got[0]["block"] == "team"
          and got[0]["source"] == "zorg-core" and got[0]["rank"] is None and got[0]["place"] == "team.alpha-a", got)
with tempfile.TemporaryDirectory() as d:
    e = Env(d, edits=[("## Zorg Core Notes\n\n", "## Zorg Core Notes\n\n" + TEAM + "\n\n")])
    got = cands(e, "team.members")
    body = next(x for x in e.records() if x["id"] == "team.alpha-a")["body"]
    check("a bound block whose id repeats (no sound region) is no bound candidate, but still answers by name",
          len(got) == 1 and got[0]["how"] == "name" and got[0]["record"] == "team.alpha-a"
          and got[0]["text"] == cr._lookup(body, "Members", field=False)[0], got)
with tempfile.TemporaryDirectory() as d:
    e = Env(d, edits=[TEAM_MEMBERS])
    got = cands(e, "team.members", repos=[])
    check("…but only when your text has nothing in that record (P5): no by-name next to yours",
          len(got) == 1 and got[0]["level"] == "mine", got)

# ------------------------------------------------------------------ where a bound block belongs (spec §4.4)
with tempfile.TemporaryDirectory() as d:
    e = Env(d, edits=TEAM_TO_CUSTOM)
    got = cands(e, "team.members")
    check("the team block in a custom record, one team: a team.members candidate for that team",
          len(got) == 1 and got[0]["record"] == "custom.zorg-core-notes" and got[0]["placed"] is True
          and got[0]["place"] == "team.alpha-a" and "Bea Two" in got[0]["text"], got)
with tempfile.TemporaryDirectory() as d:
    e = Env(d, edits=TEAM_TO_CUSTOM + [BETA])
    got = cands(e, "team.members")
    check("…two teams and no --team: unplaced, kept for explain", len(got) == 1 and got[0]["placed"] is False
          and got[0]["place"] is None, got)
    mem = memory(("zorg-core", "team", "Members", "team.members", "team.beta-b"))
    got = cands(e, "team.members", mem=mem)
    check("…a binding that names the team: placed, for that team only", len(got) == 1 and got[0]["placed"] is True
          and got[0]["place"] == "team.beta-b" and got[0]["how"] == "memory", got)
    recs = e.records()
    alpha = [t for t in teams_of(recs, None) if t["id"] == "team.alpha-a"]
    got = cands(e, "team.members", mem=mem, teams=alpha)
    check("…and not a candidate where only the other team is read", got == [], got)
with tempfile.TemporaryDirectory() as d:
    e = Env(d, edits=[LITE])
    mem = memory(("zorg-core", "scope", None, "product.scope", None), ("zorg-growth", "growth-metrics", None, "product.key_metrics", None))
    app, lite = cands(e, "product.scope", mem=mem), cands(e, "product.scope", product="Zorg Lite", mem=mem)
    check("two products, products: [] — the block in a custom record is a candidate for both (Review Focus 3)",
          len(app) == 1 and len(lite) == 1 and app[0]["place"] == "product.zorg-app" and lite[0]["place"] == "product.zorg-lite"
          and app[0]["text"] == "### Scope of work\nThe user works on Zorg App only.\n", (app, lite))
    app, lite = cands(e, "product.key_metrics", mem=mem), cands(e, "product.key_metrics", product="Zorg Lite", mem=mem)
    check("…the block in a product record only for its own product", len(app) == 1 and app[0]["block"] == "growth-metrics"
          and app[0]["source"] == "zorg-growth" and app[0]["rank"] == 500 and lite == [], (app, lite))
    lite_only = [dict(REPOS[0], products=["Zorg Lite"]), REPOS[1]]
    check("a repository that serves one product fills a custom-record slot for it alone",
          cands(e, "product.scope", mem=mem, repos=lite_only) == []
          and len(cands(e, "product.scope", product="Zorg Lite", mem=mem, repos=lite_only)) == 1, "")
    check("serves_product matches the product by id, title or the title after the colon, without case",
          all(crp.serves_product({"products": [p]}, {"id": "product.zorg-lite", "title": "Product: Zorg Lite"})
              for p in ("zorg lite", "PRODUCT.ZORG-LITE", "Product: Zorg Lite"))
          and crp.serves_product({"products": []}, {"id": "product.x", "title": "Product: X"})
          and not crp.serves_product({"products": ["Zorg App"]}, {"id": "product.zorg-lite", "title": "Product: Zorg Lite"}), "")

# ------------------------------------------------------------------ the text a bound block gives (spec §4.5)
SCOPE2 = ("<!-- zorg-core:begin id=scope v=0.4 slot=product.scope,product.key_metrics,product.okrs -->\n### Scope of work\n"
          "The user works on Zorg App only.\n### Key Metrics\n- weekly conversion\n<!-- zorg-core:end id=scope -->")
with tempfile.TemporaryDirectory() as d:
    e = Env(d)
    got = cands(e, "team.members", mem=memory(("zorg-core", "team", "Members", "team.members", None)))
    check("bind with #Members gives only that subsection", len(got) == 1 and got[0]["how"] == "memory"
          and got[0]["text"].startswith("#### Members") and "Team card" not in got[0]["text"]
          and got[0]["heading"].startswith("Members"), got)
    got = cands(e, "org.structure", mem=memory(("zorg-core", "teams", None, "org.structure", None)))
    check("a block bound to one slot gives the whole region, without its markers", len(got) == 1
          and got[0]["text"] == "### Teams map\n- Alpha, Beta\n" and got[0]["heading"] == "Teams map" and got[0]["place"] is None, got)
    got = cands(e, "team.members", mem=memory(("zorg-core", "team", "Nowhere", "team.members", None)))
    check("a binding of yours to a subsection the block lacks is no candidate — and your binding keeps the block out of the by-name answer",
          got == [], got)
with tempfile.TemporaryDirectory() as d:
    e = Env(d, edits=[(SCOPE, SCOPE2)])
    e.state("zorg-core", {"scope": ("0.4", [SCOPE2])})
    scope, metrics, okrs = cands(e, "product.scope"), cands(e, "product.key_metrics"), cands(e, "product.okrs")
    check("a block with slot=a,b in its base gives each slot its own subsection", len(scope) == 1 and len(metrics) == 1
          and scope[0]["text"] == "### Scope of work\nThe user works on Zorg App only.\n"
          and metrics[0]["text"] == "### Key Metrics\n- weekly conversion\n" and scope[0]["how"] == metrics[0]["how"] == "marker", (scope, metrics))
    check("…and a slot it names without such a subsection gets nothing", okrs == [], okrs)
with tempfile.TemporaryDirectory() as d:
    e = Env(d, edits=[(SCOPE, SCOPE.replace("v=0.4 -->", "v=0.4 slot=product.scope -->"))])
    e.state("zorg-core", {"scope": ("0.4", [SCOPE])})
    binds, _ = sl.bindings_of(e.store, REPOS, sl.empty_memory())
    check("slot= in your region but not in the base binds nothing", ("zorg-core", "scope") not in binds
          and cands(e, "product.scope") == [], binds)
with tempfile.TemporaryDirectory() as d:
    e = Env(d)
    e.state("zorg-core", {"scope": ("0.4", [SCOPE.replace("v=0.4 -->", "v=0.4 slot=product.scope -->")])})
    mem = memory(("zorg-core", "scope", None, "product.key_metrics", None))
    check("your binding and slot= on one block: the block answers your slot, not the marker's (Review Focus 2)",
          cands(e, "product.scope", mem=mem) == [] and [c["how"] for c in cands(e, "product.key_metrics", mem=mem)] == ["memory"], "")
with tempfile.TemporaryDirectory() as d:
    e = Env(d)
    got = cands(e, "product.scope", mem=memory(("zorg-core", "gone", None, "product.scope", None),
                                                ("zorg-nowhere", "scope", None, "product.scope", None)))
    check("a binding to a block that is not in the records: no candidate, no exception (Review Focus 1)", got == [], got)
    got = cands(e, "product.key_metrics", mem=memory(("zorg-growth", "growth-metrics", None, "product.key_metrics", None)),
                repos=REPOS[:1])
    check("a block of a registration that was not read: a candidate with no rank", len(got) == 1
          and got[0]["source"] == "zorg-growth" and got[0]["rank"] is None, got)

# ------------------------------------------------------------------ your own names (spec §4.1, §8)
FOCUS = ("- **Jira Project Key:** PROJ\n", "- **Jira Project Key:** PROJ\n- **Platforms:** Web, iOS\n\n"
         "#### Key Metrics (focus)\n- weekly shoppers\n\n#### Focus numbers\n- orders per day\n")
with tempfile.TemporaryDirectory() as d:
    e = Env(d, edits=[FOCUS])
    got = cands(e, "product.key_metrics")
    check("your subsection answers by the start of its heading", len(got) == 1 and got[0]["heading"] == "Key Metrics (focus)"
          and got[0]["text"] == "#### Key Metrics (focus)\n- weekly shoppers\n", got)
    mem = memory(aliases=[("product.zorg-app", "Key Metrics (focus)", "product.okrs")])
    km, okrs = cands(e, "product.key_metrics", mem=mem), cands(e, "product.okrs", mem=mem)
    check("a heading you mapped to another slot is no candidate of this one (Review Focus 5)", km == [], km)
    check("…and it is the other slot's own candidate", len(okrs) == 1 and okrs[0]["level"] == "mine"
          and okrs[0]["heading"] == "Key Metrics (focus)" and okrs[0]["text"] == "#### Key Metrics (focus)\n- weekly shoppers\n", okrs)
    mem = memory(aliases=[("product.zorg-app", "Key Metrics (focus)", "product.okrs"),
                          ("product.zorg-app", "Key Metrics (focus)", "product.key_metrics")])
    check("…unless you mapped it to this slot as well", [c["heading"] for c in cands(e, "product.key_metrics", mem=mem)]
          == ["Key Metrics (focus)"], cands(e, "product.key_metrics", mem=mem))
    mem = memory(aliases=[("product.zorg-app", "Key Metrics (focus)", "product.okrs"),
                          ("product.zorg-app", "focus  NUMBERS", "product.key_metrics")])
    got = cands(e, "product.key_metrics", mem=mem)
    check("a name you mapped answers when no catalogue name does, whatever its case and spacing",
          [c["heading"] for c in got] == ["Focus numbers"] and got[0]["level"] == "mine", got)
    mem = memory(aliases=[("product.zorg-app", "focus  NUMBERS", "product.key_metrics")])
    got = cands(e, "product.key_metrics", mem=mem)
    check("one own candidate per record: a catalogue name that answers comes before a name you mapped (ruling)",
          [c["heading"] for c in got] == ["Key Metrics (focus)"], got)
    mem = memory(aliases=[("product.zorg-app", "Key Metrics", "product.key_metrics")])
    check("the same heading found twice is one candidate", len(cands(e, "product.key_metrics", mem=mem)) == 1, "")
    mem = memory(aliases=[("product.other", "Focus numbers", "product.key_metrics")])
    check("a name mapped in another record does not count here", len(cands(e, "product.key_metrics", mem=mem)) == 1, "")
    got = cands(e, "product.platforms")
    check("a list slot answers by its field line too (Platforms is a typed list field)", len(got) == 1
          and got[0]["text"] == "- **Platforms:** Web, iOS\n" and got[0]["heading"] == "Platforms", got)
    got = cands(e, "product.platforms", field=True)
    check("…and with the manifest's field mode", [c["text"] for c in got] == ["- **Platforms:** Web, iOS\n"], got)

TWO_NAMES = ("- **Jira Project Key:** PROJ\n", "- **Jira Project Key:** PROJ\n\n#### Ключові метрики\n- uk numbers\n\n"
             "#### Key Metrics\n- en numbers\n")
with tempfile.TemporaryDirectory() as d:
    e = Env(d, edits=[TWO_NAMES])
    got = cands(e, "product.key_metrics")
    check("one own candidate per record: the first name in the catalogue's order, not one per name (ruling)",
          len(got) == 1 and got[0]["heading"] == "Key Metrics" and "en numbers" in got[0]["text"], got)

# ------------------------------------------------------------------ the manifest's lookup mode (ruling)
BOTH = ("- **Jira Project Key:** PROJ\n", "- **Jira Project Key:** PROJ\n- **Competitors:** Zorg Rival\n\n"
        "#### Competitors\n- Zorg Other\n")
BLOCK_BOTH = ("#### Growth metrics\n", "- **Competitors:** Block Rival\n\n#### Competitors\n- Block Other\n#### Growth metrics\n")
with tempfile.TemporaryDirectory() as d:
    e = Env(d, edits=[BOTH])
    sec, fld, kind = (cands(e, "product.competitors", field=False), cands(e, "product.competitors", field=True),
                      cands(e, "product.competitors"))
    check("field=False (the manifest's sections) gives the subsection", [c["text"] for c in sec] == ["#### Competitors\n- Zorg Other\n"], sec)
    check("field=True (fields, required) gives the field line", [c["text"] for c in fld] == ["- **Competitors:** Zorg Rival\n"], fld)
    check("no mode: by the slot's kind — a list reads its field line first", [c["text"] for c in kind] == ["- **Competitors:** Zorg Rival\n"], kind)
with tempfile.TemporaryDirectory() as d:
    e = Env(d, edits=[BLOCK_BOTH])
    body = next(x for x in e.records() if x["id"] == "product.zorg-app")["body"]
    sec, fld = cands(e, "product.competitors", field=False), cands(e, "product.competitors", field=True)
    check("the mode holds for a block found by name too, as cr._lookup with the same mode",
          [c["text"] for c in sec] == [cr._lookup(body, "Competitors", field=False)[0]] == ["#### Competitors\n- Block Other\n"]
          and [c["text"] for c in fld] == [cr._lookup(body, "Competitors")[0]] == ["- **Competitors:** Block Rival\n"]
          and sec[0]["how"] == fld[0]["how"] == "name", (sec, fld))
    mem = memory(("zorg-growth", "growth-metrics", None, "product.competitors", None),
                 ("zorg-growth", "growth-metrics", None, "product.platforms", None))
    sec, fld = cands(e, "product.competitors", mem=mem, field=False), cands(e, "product.competitors", mem=mem, field=True)
    check("…and for a block bound to several slots", [c["text"] for c in sec] == ["#### Competitors\n- Block Other\n"]
          and [c["text"] for c in fld] == ["- **Competitors:** Block Rival\n"] and sec[0]["how"] == "memory", (sec, fld))

# ------------------------------------------------------------------ your edits, and a core rule (spec §4.3, §5.1)
EDITED = ("| Bea Two ◌ | Data analyst |", "| Bea Two ◌ | Senior data analyst |")
with tempfile.TemporaryDirectory() as d:
    e = Env(d, edits=[EDITED])
    e.state("zorg-core", {"team": ("0.2", [TEAM])})
    got = cands(e, "team.members")
    check("a block whose text differs from its base: edited", len(got) == 1 and got[0]["edited"] is True
          and got[0]["rule"] is False and got[0]["level"] == "repo", got)
    e.state("zorg-core", {"team": ("0.2", [region(e.text, "zorg-core", "team"), TEAM])})
    got = cands(e, "team.members")
    check("…an older base of it is no edit", len(got) == 1 and got[0]["edited"] is False, got)
    e.state("zorg-core", {})
    check("…a block with no base is no edit", cands(e, "team.members")[0]["edited"] is False, "")
RULE = TEAM.replace("v=0.2 -->", "v=0.2 policy=rule -->")
with tempfile.TemporaryDirectory() as d:
    e = Env(d, edits=[(TEAM, RULE)])
    e.state("zorg-core", {"team": ("0.2", [RULE])})
    got = cands(e, "team.members")
    check("a base with policy=rule: a rule, on the rule level", len(got) == 1 and got[0]["rule"] is True
          and got[0]["level"] == "rule" and got[0]["edited"] is False, got)
GROWTH_RULE = GROWTH.replace("v=0.1 -->", "v=0.1 policy=rule -->").replace("#### Growth metrics", "#### Key Metrics")
with tempfile.TemporaryDirectory() as d:
    e = Env(d, edits=[(GROWTH, GROWTH_RULE)])
    e.state("zorg-growth", {"growth-metrics": ("0.1", [GROWTH_RULE])})
    got = cands(e, "product.key_metrics")
    check("…an unbound block found by name is a rule by its base, but stays on the repository level (a rule is bound)",
          len(got) == 1 and got[0]["how"] == "name" and got[0]["rule"] is True and got[0]["level"] == "repo"
          and got[0]["source"] == "zorg-growth" and got[0]["rank"] == 500, got)

# ------------------------------------------------------------------ the cascade: resolve (spec §5.1, §5.2, §6)
import copy  # noqa: E402

TEXT_SLOT, VALUE_SLOT, LIST_SLOT = "product.key_metrics", "product.jira_key", "team.members"
RESULT_KEYS = {"slot", "kind", "shown", "note", "also", "diverges", "why", "decision", "prefer"}


def cand(source, text="x\n", level=None, rank=500, rule=False, placed=True, slot=TEXT_SLOT):
    """A hand-built candidate with every key of KEYS: `source` "mine" is your text; level "rule" is a bound core rule."""
    level = level or ("mine" if source == "mine" else "repo")
    return {"slot": slot, "source": source, "level": level, "record": "product.zorg-app",
            "block": None if source == "mine" else "blk", "ns": None if source == "mine" else source, "version": None,
            "checked": None, "edited": False, "rule": rule or level == "rule", "how": None if source == "mine" else "memory",
            "heading": None, "text": text, "rank": None if source == "mine" else rank, "placed": placed, "place": "product.zorg-app",
            "sub": None}


def R(slot, cands, mem=None):
    return rv.resolve(slot, CAT, cands, mem)


def src(cs_):
    return [c["source"] for c in cs_]


def sha(s):
    return cs.sha_text(s)


rule = cand("zorg-core", "RULE\n", level="rule", rank=1000)
mine = cand("mine", "MINE\n")
core = cand("zorg-core", "CORE\n", rank=1000)
growth = cand("zorg-growth", "GROWTH\n", rank=500)
r = R(TEXT_SLOT, [growth, mine, rule])
check("resolve returns the agreed keys", set(r) == RESULT_KEYS and r["slot"] == TEXT_SLOT and r["kind"] == "text", sorted(r))
check("a core rule: it is shown, your text is the note, the rest is «також»; the reason is the rule",
      r["shown"] == [rule] and r["note"] is mine and r["also"] == [growth] and r["why"] == "правило ядра"
      and r["diverges"] == [] and r["decision"] is None and r["prefer"] == "mine", r)
r = R(TEXT_SLOT, [growth, rule])
check("…no text of yours: no note", r["shown"] == [rule] and r["note"] is None and r["also"] == [growth], r)
r = R(TEXT_SLOT, [cand("zorg-growth", "RULE\n"), rule, mine])
check("…a candidate that says the same as the rule is not in «також»", r["also"] == [] and r["note"] is mine, r)
r = R(LIST_SLOT, [cand("zorg-growth", "G\n", slot=LIST_SLOT), cand("mine", "M\n", slot=LIST_SLOT),
                  cand("zorg-core", "R\n", level="rule", slot=LIST_SLOT)])
check("…a list too: the rule fully, yours as the note, the rest one line each", src(r["shown"]) == ["zorg-core"]
      and r["note"]["source"] == "mine" and src(r["also"]) == ["zorg-growth"] and r["why"] == "правило ядра", r)
r = R(TEXT_SLOT, [growth, mine, rule], {"prefer": {TEXT_SLOT: "repo:zorg-growth"}})
check("a preference for a repository does not beat a rule", r["shown"] == [rule] and r["prefer"] == "mine" and r["note"] is mine, r)
r = R(TEXT_SLOT, [cand("zorg-aaa", "RULE A\n", level="rule", rank=1000), rule, cand("zorg-low", "RULE L\n", level="rule", rank=10)])
check("several rules: the strongest (rank, then id) is shown; the others with other text are «також»",
      src(r["shown"]) == ["zorg-aaa"] and src(r["also"]) == ["zorg-core", "zorg-low"], r)

r = R(TEXT_SLOT, [growth, mine, core, rule], {"prefer": {TEXT_SLOT: "all"}})
check("prefer all: every candidate in the order of the cascade, the rule first; no note, no «також» (ruling P3)",
      src(r["shown"]) == ["zorg-core", "mine", "zorg-core", "zorg-growth"] and r["shown"][0] is rule and r["shown"][2] is core
      and r["note"] is None and r["also"] == [] and r["diverges"] == [] and r["prefer"] == "all"
      and r["why"] == "перевага: all", r)
r = R(VALUE_SLOT, [growth, core], {"prefer": {VALUE_SLOT: "all"}})
check("…a divergence is shown in full, too, and is no divergence to resolve", src(r["shown"]) == ["zorg-core", "zorg-growth"]
      and r["diverges"] == [], r)

r = R(TEXT_SLOT, [mine, core, growth], {"prefer": {TEXT_SLOT: "repo:zorg-growth"}})
check("prefer repo:<id>: that repository wins, even over your text; the rest differing is «також»",
      r["shown"] == [growth] and src(r["also"]) == ["mine", "zorg-core"] and r["note"] is None and r["prefer"] == "repo:zorg-growth"
      and r["why"] == "перевага: repo:zorg-growth" and r["diverges"] == [], r)
r = R(TEXT_SLOT, [mine, core], {"prefer": {TEXT_SLOT: "repo:zorg-growth"}})
check("…a repository with no candidate: the cascade as usual (yours), and the preference is not the one applied",
      r["shown"] == [mine] and r["prefer"] == "mine" and "перевага" not in r["why"], r)
r = R(TEXT_SLOT, [mine, cand("zorg-growth", "MINE\n", rank=100)], {"prefer": {TEXT_SLOT: "repo:zorg-growth"}})
check("…a candidate with your text is not «також»", r["also"] == [], r)
r = R(TEXT_SLOT, [mine, core], {"prefer": {TEXT_SLOT: "mine"}})
check("prefer mine is the default", r["shown"] == [mine] and r["prefer"] == "mine", r)

lg = [cand("zorg-growth", "G\n", rank=500, slot=LIST_SLOT), cand("mine", "M\n", slot=LIST_SLOT),
      cand("zorg-core", "C\n", rank=1000, slot=LIST_SLOT), cand("zorg-aaa", "A\n", rank=1000, slot=LIST_SLOT),
      cand("zorg-nil", "N\n", rank=None, slot=LIST_SLOT), cand("zorg-zzz", "Z\n", rank=2000, slot=LIST_SLOT),
      cand("zorg-zero", "O\n", rank=0, slot=LIST_SLOT), cand("zorg-growth", "G2\n", rank=500, slot=LIST_SLOT)]
r = R(LIST_SLOT, lg)
check("a list: every candidate, yours first, then the repositories by rank (high first), then by id; a rank not read is last",
      src(r["shown"]) == ["mine", "zorg-zzz", "zorg-aaa", "zorg-core", "zorg-growth", "zorg-growth", "zorg-zero", "zorg-nil"]
      and r["note"] is None and r["also"] == []
      and r["diverges"] == [] and r["kind"] == "list"
      and r["why"] == "список — виводяться всі кандидати; team.members у ctx read склеєно за сутністю", r)
r = R(LIST_SLOT, lg, {"prefer": {LIST_SLOT: "repo:zorg-growth"}})
check("…a list with a preference for a repository: all its candidates, the rest in «також» — but a registration not read is "
      "shown after them (Task 5 ruling)", src(r["shown"]) == ["zorg-growth"] * 2 + ["zorg-nil"]
      and src(r["also"]) == ["mine", "zorg-zzz", "zorg-aaa", "zorg-core", "zorg-zero"], r)

for slot in (TEXT_SLOT, VALUE_SLOT):
    mv = cand("mine", "MINE\n" if slot == TEXT_SLOT else "- **Jira Project Key:** MINE\n", slot=slot)
    other = cand("zorg-core", "CORE\n" if slot == TEXT_SLOT else "- **jira_project_key:** CORE\n", rank=1000, slot=slot)
    r = R(slot, [other, mv])
    check("%s: yours wins over a repository of any rank; the other is «також»" % slot, r["shown"] == [mv] and r["also"] == [other]
          and r["why"] == "твоє перемагає (блок не є правилом ядра)" and r["diverges"] == [] and r["note"] is None, r)
    r = R(slot, [mv])
    check("%s: yours alone: no reason to give but that it is the only one" % slot, r["shown"] == [mv] and r["also"] == []
          and r["why"] == "єдиний кандидат", r)

r = R(TEXT_SLOT, [growth, core])
check("a higher rank wins; the loser is «також»; the reason names both ranks",
      r["shown"] == [core] and r["also"] == [growth] and r["diverges"] == [] and r["decision"] is None
      and r["why"] == "більший ранг: zorg-core 1000 > zorg-growth 500", r)
nil = cand("zorg-nil", "N\n", rank=None)
r = R(TEXT_SLOT, [growth, nil, core])
check("…a rank not read takes no part in the cascade: shown after the winner, never «також» (spec §4.6, Task 5 ruling)",
      r["shown"] == [core, nil] and src(r["also"]) == ["zorg-growth"]
      and r["why"] == "більший ранг: zorg-core 1000 > zorg-growth 500", r)
r = R(TEXT_SLOT, [nil, growth])
check("…so it is never the loser a reason names", r["shown"] == [growth, nil] and r["also"] == [] and r["why"] == "єдиний кандидат", r)
r = R(TEXT_SLOT, [cand("zorg-aaa", "AAA\n", rank=10), cand("zorg-zzz", "ZZZ\n", rank=900)])
check("…by rank, not by id", r["shown"][0]["source"] == "zorg-zzz" and r["why"] == "більший ранг: zorg-zzz 900 > zorg-aaa 10", r)
r = R(TEXT_SLOT, [cand("zorg-nil", "N\n", rank=None), cand("zorg-zero", "O\n", rank=0)])
check("…a rank of 0 is still a rank read", r["shown"][0]["source"] == "zorg-zero" and r["diverges"] == [], r)
r = R(TEXT_SLOT, [core])
check("one repository, one candidate: it wins, with no loser to name", r["shown"] == [core] and r["why"] == "єдиний кандидат"
      and r["also"] == [] and r["diverges"] == [], r)
r = R(TEXT_SLOT, [core, cand("zorg-growth", "CORE   \r\n", rank=1000)])
check("equal rank, the same text up to trailing blanks and line ends: no divergence; the first by id wins; nothing in «також»",
      r["shown"] == [core] and r["also"] == [] and r["diverges"] == [], r)

peer = cand("zorg-growth", "GROWTH\n", rank=1000)
low = cand("zorg-low", "LOW\n", rank=10)
r = R(TEXT_SLOT, [peer, core, low])
check("equal highest rank and a different text: a divergence — both shown, in the order of ids; a lower rank is «також»",
      r["diverges"] == ["zorg-core", "zorg-growth"] and r["shown"] == [core, peer] and r["also"] == [low]
      and r["decision"] is None and r["note"] is None and r["why"] == "рівний ранг 1000, різний текст: zorg-core, zorg-growth", r)
r = R(TEXT_SLOT, [cand("zorg-growth", "GROWTH\n", rank=None), cand("zorg-core", "CORE\n", rank=None)])
check("…two ranks not read, different text: no divergence — both shown without the cascade, as they came",
      r["diverges"] == [] and src(r["shown"]) == ["zorg-growth", "zorg-core"] and r["also"] == [] and r["why"] == rv.WHY_UNREAD, r)
third = cand("zorg-third", "CORE\n", rank=1000)
r = R(TEXT_SLOT, [peer, third, core])
check("…a third at the same rank with the same text as the first still takes part", r["diverges"] == ["zorg-core", "zorg-growth", "zorg-third"], r)
r = R(TEXT_SLOT, [mine, peer, core])
check("…never when you have text of your own", r["diverges"] == [] and r["shown"] == [mine], r)
r = R(TEXT_SLOT, [cand("zorg-core", "ONE\n", rank=1000), cand("zorg-core", "TWO\n", rank=1000)])
check("two blocks of one repository are no divergence between repositories: the first wins, the other is «також»",
      r["diverges"] == [] and r["shown"][0]["text"] == "ONE\n" and [c["text"] for c in r["also"]] == ["TWO\n"], r)

# Task 5 ruling: a candidate whose registration was not read (rank None, a repository's) is shown without the cascade
unread_v = cand("zorg-nil", "- **jira_project_key:** NIL\n", rank=None, slot=VALUE_SLOT)
mine_v = cand("mine", "- **Jira Project Key:** MINE\n", slot=VALUE_SLOT)
r = R(VALUE_SLOT, [unread_v, mine_v])
check("a candidate of a registration not read is never «також»: it joins `shown` after the cascade's own shown",
      r["shown"] == [mine_v, unread_v] and r["also"] == [] and r["why"] == "єдиний кандидат" and r["note"] is None, r)
r = R(VALUE_SLOT, [unread_v])
check("…alone, it is shown, and the reason says the cascade did not rank it", r["shown"] == [unread_v] and r["why"] == rv.WHY_UNREAD
      and r["diverges"] == [] and r["prefer"] == "mine", r)
r = R(TEXT_SLOT, [nil, rule, mine])
check("…a rule still wins, yours is still its note, the unread one follows the rule", r["shown"] == [rule, nil] and r["note"] is mine
      and r["also"] == [], r)
r = R(TEXT_SLOT, [nil, mine, core], {"prefer": {TEXT_SLOT: "repo:zorg-core"}})
check("…a preference does not touch it", r["shown"] == [core, nil] and src(r["also"]) == ["mine"] and r["prefer"] == "repo:zorg-core", r)
r = R(TEXT_SLOT, [dict(nil, placed=False), mine])
check("…an unplaced one is still ignored", r["shown"] == [mine], r)
r = R(TEXT_SLOT, [cand("mine", "MINE\n"), dict(cand("mine", "MINE 2\n"), rank=None)])
check("…your text is never «not read»: the rank is a repository's", src(r["shown"]) == ["mine"] and src(r["also"]) == ["mine"], r)

DEC_HASHES = {"zorg-core": sha("CORE"), "zorg-growth": sha("GROWTH")}
DEC = {"winner": "zorg-growth", "hashes": DEC_HASHES, "at": "2026-10-20"}
mem = {"decisions": {TEXT_SLOT: DEC}}
r = R(TEXT_SLOT, [peer, core], mem)
check("a decision with the same hashes: its winner wins, no divergence, «також» for the other, the reason names the day",
      r["shown"] == [peer] and r["diverges"] == [] and src(r["also"]) == ["zorg-core"] and r["decision"] == DEC
      and r["why"] == "твоє рішення від 2026-10-20", r)
check("…the memory it was given is not changed by it", mem == {"decisions": {TEXT_SLOT: {"winner": "zorg-growth", "hashes": DEC_HASHES, "at": "2026-10-20"}}}, mem)
r = R(TEXT_SLOT, [peer, core], {"decisions": {TEXT_SLOT: {"winner": "zorg-growth", "hashes": DEC_HASHES}}})
check("…a decision with no day: the reason without it", r["shown"] == [peer] and r["why"] == "твоє рішення", r)
r = R(TEXT_SLOT, [cand("zorg-growth", "GROWTH, new\n", rank=1000), core], mem)
check("a new text in a repository (a new hash): the decision no longer acts — the divergence is back",
      r["diverges"] == ["zorg-core", "zorg-growth"] and r["decision"] is None and len(r["shown"]) == 2, r)
r = R(TEXT_SLOT, [peer, core, third], {"decisions": {TEXT_SLOT: {"winner": "zorg-growth", "hashes": DEC_HASHES}}})
check("…so does one more repository at the same rank (the participants are not the same)", r["decision"] is None
      and r["diverges"] == ["zorg-core", "zorg-growth", "zorg-third"], r)
r = R(TEXT_SLOT, [peer, core], {"decisions": {TEXT_SLOT: {"winner": "zorg-third", "hashes": DEC_HASHES}}})
check("…and a winner who is not one of the participants", r["decision"] is None and r["diverges"] == ["zorg-core", "zorg-growth"], r)
r = R(TEXT_SLOT, [peer, core], {"decisions": {VALUE_SLOT: DEC}})
check("…and a decision about another slot", r["decision"] is None and r["diverges"] == ["zorg-core", "zorg-growth"], r)
r = R(TEXT_SLOT, [mine, peer, core], mem)
check("a decision does not outrank yours, nor a core rule", r["shown"] == [mine] and R(TEXT_SLOT, [rule, peer, core], mem)["shown"] == [rule], r)
r = R(TEXT_SLOT, [peer, core], {"prefer": {TEXT_SLOT: "repo:zorg-core"}, "decisions": {TEXT_SLOT: DEC}})
check("a preference for a repository comes before a decision", r["shown"] == [core] and r["decision"] is None, r)

# value slots compare the value after the label, not the line (ruling 2)
a1, a2 = "- **Jira Project Key:** PROJ\n", "- **jira_project_key:** PROJ   \n"
check("compare_key: a field line is its value, stripped; the label does not count",
      rv.compare_key("value", a1) == rv.compare_key("value", a2) == "PROJ" and rv.compare_key("value", "- **Jira Project Key:** OTHER\n") == "OTHER", "")
check("…a subsection used as a value is its text without the heading", rv.compare_key("value", "#### Jira Project Key\nPROJ\n")
      == rv.compare_key("value", "#### jira_project_key\nPROJ  \n\n") == "PROJ", rv.compare_key("value", "#### Jira Project Key\nPROJ\n"))
check("…a text or a list: the text as cb.norm has it, the label kept", rv.compare_key("text", "a  \r\nb\n\n") == "a\nb"
      and rv.compare_key("list", "- **Platforms:** Web\n") == "- **Platforms:** Web"
      and rv.compare_key("list", "- **Platforms:** Web\n") != rv.compare_key("list", "- **platforms:** Web\n"), "")
v_mine, v_core = cand("mine", a1, slot=VALUE_SLOT), cand("zorg-core", a2, rank=1000, slot=VALUE_SLOT)
v_other = cand("zorg-growth", "- **jira_project_key:** OTHER\n", rank=500, slot=VALUE_SLOT)
check("a value slot: the same value under two labels is no «також»", R(VALUE_SLOT, [v_mine, v_core])["also"] == [], "")
check("…another value is", R(VALUE_SLOT, [v_mine, v_other])["also"] == [v_other], "")
r = R(VALUE_SLOT, [v_core, cand("zorg-growth", "- **Jira Project Key:** PROJ\n", rank=1000, slot=VALUE_SLOT)])
check("…two repositories at the same rank, the same value under two labels: no divergence", r["diverges"] == [] and src(r["shown"]) == ["zorg-core"], r)
r = R(VALUE_SLOT, [v_core, cand("zorg-growth", "- **Jira Project Key:** OTHER\n", rank=1000, slot=VALUE_SLOT)])
check("…another value: a divergence", r["diverges"] == ["zorg-core", "zorg-growth"], r)
check("divergence_hashes: per participant the hash of the compared text (the value, for a value slot) — what a decision keeps",
      rv.divergence_hashes("value", r["shown"]) == {"zorg-core": sha("PROJ"), "zorg-growth": sha("OTHER")}
      and rv.divergence_hashes("text", [peer, core]) == DEC_HASHES
      and rv.divergence_hashes("text", [core, cand("zorg-core", "Z\n")]) == {"zorg-core": sha("CORE")}, rv.divergence_hashes("value", r["shown"]))
r2 = R(VALUE_SLOT, r["shown"], {"decisions": {VALUE_SLOT: {"winner": "zorg-growth", "hashes": rv.divergence_hashes("value", r["shown"])}}})
check("…and a decision on a value slot acts on the value: another label for the same value keeps it",
      src(r2["shown"]) == ["zorg-growth"] and r2["diverges"] == [] and R(VALUE_SLOT, [
          cand("zorg-core", "- **Key:** PROJ\n", rank=1000, slot=VALUE_SLOT), cand("zorg-growth", "- **Key:** OTHER\n", rank=1000, slot=VALUE_SLOT)],
          {"decisions": {VALUE_SLOT: {"winner": "zorg-growth", "hashes": rv.divergence_hashes("value", r["shown"])}}})["decision"] is not None, r2)

# what is not placed is not a candidate; an empty cascade; purity
unplaced = dict(cand("zorg-core", "CORE\n", rank=1000), placed=False, place=None)
r = R(TEXT_SLOT, [unplaced, growth])
check("a candidate that is not placed is ignored by resolve", r["shown"] == [growth] and r["also"] == [] and r["diverges"] == []
      and r["why"] == "єдиний кандидат", r)
r = R(TEXT_SLOT, [unplaced])
check("…only such candidates, or none: nothing shown, no reason", r["shown"] == [] and r["note"] is None and r["also"] == [] and r["why"] == ""
      and R(TEXT_SLOT, []) == r and R(TEXT_SLOT, [], None) == r, r)
r = R(TEXT_SLOT, [unplaced, rule], {"prefer": {TEXT_SLOT: "all"}})
check("…also under prefer all", r["shown"] == [rule], r)
inputs = [mine, core, peer, growth, low, rule]
frozen, mem2 = copy.deepcopy(inputs), copy.deepcopy(mem)
for m_ in (None, {}, mem2, {"prefer": {TEXT_SLOT: "all"}}):
    R(TEXT_SLOT, inputs, m_)
check("resolve changes neither the candidates nor the memory", inputs == frozen and mem2 == mem, "")
r = R("team.nowhere", [growth])
check("a slot the catalogue lacks has no kind, and is read as a text: no exception", r["kind"] is None and r["shown"] == [growth], r)

# ------------------------------------------------------------------ slot_context and slot_answers (shared by read, explain, decide)
SCTX_KEYS = {"store", "cat", "records", "notes", "pending", "product", "needs_product", "products", "teams", "repos", "mem",
             "mem_error", "bindings", "dropped", "problems", "regs"}
with tempfile.TemporaryDirectory() as d:
    e = Env(d)
    before = tree(e.home, e.vault)
    x = rv.slot_context(e.store, e.copies, REPOS, "Zorg App", NOW)
    check("slot_context assembles what the resolver needs, with the keys the docstring lists", set(x) == SCTX_KEYS, sorted(x))
    check("…the live records, the product asked for, the teams ctx read would read, the memory and the bindings",
          [r_["id"] for r_ in x["records"]] == [r_["id"] for r_ in e.records()] and x["product"]["id"] == "product.zorg-app"
          and x["needs_product"] is False and x["products"] == ["Zorg App"] and [t_["id"] for t_ in x["teams"]] == ["team.alpha-a"]
          and x["mem"] == sl.empty_memory() and x["mem_error"] is None and x["repos"] == REPOS and x["problems"] == []
          and ("zorg-core", "team") in x["bindings"] and x["pending"] == 0 and x["cat"] == CAT, x)
    x = rv.slot_context(e.store, e.copies, REPOS, None, NOW)
    check("…one product and none asked for: that one", x["product"]["id"] == "product.zorg-app" and x["needs_product"] is False, x["product"])
    x = rv.slot_context(e.store, e.copies, REPOS, "Nowhere", NOW)
    check("…a product that matches none: needs a choice", x["product"] is None and x["needs_product"] is True and x["products"] == ["Zorg App"], x)
    x = rv.slot_context(e.store, e.copies, REPOS, "Zorg App", NOW, mem=memory(("zorg-core", "scope", None, "product.scope", None)))
    check("…a memory handed in is used as it is (the writing command already holds it)", len(x["mem"]["bindings"]) == 1
          and ("zorg-core", "scope") in x["bindings"], x["mem"])
    open(os.path.join(e.store.state_dir, "slots.json"), "w", encoding="utf-8").write("{ not json")
    bad = tree(e.home, e.vault)
    x = rv.slot_context(e.store, e.copies, REPOS, "Zorg App", NOW)
    check("a memory that cannot be read: an empty one and the reason (read works without it; a writing command stops on it)",
          x["mem"] == sl.empty_memory() and (x["mem_error"] or "").startswith("slots memory not valid: .state/slots.json (")
          and ("zorg-core", "team") in x["bindings"], x["mem_error"])
    check("slot_context writes nothing", tree(e.home, e.vault) == bad and bad != before, "")
with tempfile.TemporaryDirectory() as d:
    e = Env(d, edits=[LITE])
    x = rv.slot_context(e.store, e.copies, REPOS, None, NOW)
    check("two products and none asked for: a choice is needed, and they are named",
          x["needs_product"] is True and x["product"] is None and sorted(x["products"]) == ["Zorg App", "Zorg Lite"], (x["needs_product"], x["products"]))
    x = rv.slot_context(e.store, e.copies, REPOS, "Zorg Lite", NOW)
    check("…asked for by name: that one", x["product"]["id"] == "product.zorg-lite" and x["needs_product"] is False, x["product"])
with tempfile.TemporaryDirectory() as d:
    e = Env(d, edits=TEAM_TO_CUSTOM + [BETA])
    x = rv.slot_context(e.store, e.copies, REPOS, "Zorg App", NOW)
    mem3 = memory(("zorg-core", "team", "Members", "team.members", "team.beta-b"))
    x3 = rv.slot_context(e.store, e.copies, REPOS, "Zorg App", NOW, mem=mem3)
    check("slot_answers: one answer per place — a team the block is bound to, with its candidates and the resolved result",
          rv.slot_answers(x, LIST_SLOT) == [] and [(a_["place"], len(a_["candidates"]), a_["result"]["slot"]) for a_ in rv.slot_answers(x3, LIST_SLOT)]
          == [("team.beta-b", 1, LIST_SLOT)], (rv.slot_answers(x, LIST_SLOT), rv.slot_answers(x3, LIST_SLOT)))
    check("…and never a candidate that is not placed", all(c_["placed"] for a_ in rv.slot_answers(x3, LIST_SLOT) for c_ in a_["candidates"]), "")

# ------------------------------------------------------------------ explain, binding_problems, unread_lines (spec §7)
def remember(e, mem):
    """Put a memory into the store, as `ctx slot …` leaves it."""
    with cs.guard_roots(co.allowed_roots(e.home, e.text)):
        sl.save_memory(e.store, mem)


def explain(e, *slots, repos=REPOS, skipped=(), **kw):
    return rv.explain(e.store, e.copies, repos, list(skipped), slots=list(slots) or None, today="2026-10-20", catalogue=CAT, **kw)


def entry(res, slot, record=None):
    return next((s_ for s_ in res["slots"] if s_["slot"] == slot and (record is None or s_["record"] == record)), None)


def outs(s_):
    return [(r_["source"], r_["outcome"]) for r_ in (s_ or {}).get("candidates", [])]


METRICS_OWN = ("- **Jira Project Key:** PROJ\n", "- **Jira Project Key:** PROJ\n\n#### Key Metrics\n- Mine: weekly shoppers\n")
RULE_GROWTH = GROWTH.replace("v=0.1 -->", "v=0.1 policy=rule -->")
BIND_METRICS = ("zorg-growth", "growth-metrics", None, "product.key_metrics", None)
with tempfile.TemporaryDirectory() as d:
    e = Env(d, edits=[METRICS_OWN, (GROWTH, RULE_GROWTH)])
    e.state("zorg-growth", {"growth-metrics": ("0.1", [RULE_GROWTH])})
    remember(e, memory(BIND_METRICS))
    before = tree(e.home, e.vault)
    text, res = explain(e, "product.key_metrics")
    km = entry(res, "product.key_metrics")
    check("explain returns (text, result); the result has the agreed keys", isinstance(text, str) and set(res) == {
        "slots", "unmapped_blocks", "skipped_blocks", "needs_product", "warnings"} and res["warnings"] == [], sorted(res))
    check("…a slot's entry has the agreed keys", set(km) >= {"slot", "kind", "about", "record", "title", "winner", "candidates", "why", "prefer",
          "looked_in", "commands"} and km["about"] == sl.slot_info(CAT, "product.key_metrics")["about"], sorted(km))
    check("a core rule: it won; your text is shown under it as the note — not lost",
          outs(km) == [("zorg-growth", "won"), ("mine", "shown")] and km["candidates"][0]["rule"] is True
          and km["candidates"][1]["reason"] == "твоя примітка до правила" and km["why"] == "правило ядра" and km["winner"] == "zorg-growth",
          (km, text))
    check("…the text marks the rule and says what your text is",
          "  ✔ zorg-growth · блок growth-metrics v0.1 у записі product.zorg-app · станом на 2026-10-20 · прив'язка: твоя · правило ядра\n" in text
          and "  ✔ твоє · product.zorg-app › Key Metrics — твоя примітка до правила\n" in text, text)
    check("explain writes nothing and changes no record", tree(e.home, e.vault) == before, "")
    remember(e, dict(memory(BIND_METRICS), prefer={"product.key_metrics": "all"}))
    text, res = explain(e, "product.key_metrics")
    km = entry(res, "product.key_metrics")
    check("prefer all: every candidate is shown, none won", outs(km) == [("zorg-growth", "shown"), ("mine", "shown")] and km["winner"] is None
          and km["prefer"] == "all" and km["why"] == "перевага: all" and "перевага" in text, (km, text))
    remember(e, dict(memory(BIND_METRICS), prefer={"product.key_metrics": "mine"}))

with tempfile.TemporaryDirectory() as d:
    e = Env(d, edits=[EDITED])
    e.state("zorg-core", {"team": ("0.2", [TEAM])})
    text, res = explain(e, "team.members")
    row = entry(res, "team.members")["candidates"][0]
    check("a block with your edits: the row says so (edited), and so does the line", row["edited"] is True and row["rule"] is False
          and "· з твоїми правками" in text and "правило ядра" not in text, (row, text))
    e.state("zorg-core", {"team": ("0.2", [region(e.text, "zorg-core", "team")])})
    text, res = explain(e, "team.members")
    check("…and a block that is its base is not edited", entry(res, "team.members")["candidates"][0]["edited"] is False
          and "з твоїми правками" not in text, text)

SAME = ("## Zorg Core Notes\n\n", "## Zorg Core Notes\n\n<!-- zorg-growth:begin id=scope2 v=0.1 -->\n### Scope of work\n"
        "The user works on Zorg App only.\n<!-- zorg-growth:end id=scope2 -->\n\n")
with tempfile.TemporaryDirectory() as d:
    e = Env(d, edits=[SAME])
    remember(e, memory(("zorg-core", "scope", None, "product.scope", None), ("zorg-growth", "scope2", None, "product.scope", None)))
    text, res = explain(e, "product.scope")
    sc_ = entry(res, "product.scope")
    check("two repositories that say the same: the stronger won, the other lost by saying it once, and no divergence",
          outs(sc_) == [("zorg-core", "won"), ("zorg-growth", "lost")] and sc_["candidates"][1]["reason"] == "програв: той самий текст, що й у zorg-core"
          and "decision" not in sc_, (sc_, text))
    text, res = explain(e, "product.scope", repos=[dict(REPOS[0], rank=500), dict(REPOS[1], rank=500)])
    check("…at an equal rank too (the same text is no divergence)", [o for _, o in outs(entry(res, "product.scope"))].count("diverges") == 0, outs(entry(res, "product.scope")))
    text, res = explain(e, "product.scope", repos=[{"id": "zorg-core", "namespace": "zorg-core"}], skipped=[("/x/zorg-growth.yaml", "unreadable")])
    sc_ = entry(res, "product.scope")
    check("registrations whose rank is not known: shown without a cascade, each with the reason, and the unread file is named",
          sorted(outs(sc_)) == [("zorg-core", "shown"), ("zorg-growth", "shown")] and sc_["candidates"][0]["reason"].startswith("реєстрацію не прочитано")
          and sc_["winner"] is None and res["warnings"] == [rv.UNREAD_REGISTRATION % "/x/zorg-growth.yaml"]
          and rv.UNREAD_REGISTRATION % "/x/zorg-growth.yaml" in text, (sc_, res["warnings"]))

with tempfile.TemporaryDirectory() as d:
    e = Env(d, edits=[LITE])
    text, res = explain(e, "product.jira_key", "org.structure")
    check("several products and none named: the slots of a product are held back, an organisation's are explained",
          res["needs_product"] is True and res["products"] == ["Zorg App", "Zorg Lite"] and [s_["slot"] for s_ in res["slots"]] == ["org.structure"]
          and "Zorg App, Zorg Lite" in text and "Слотів із кандидатами немає" not in text, (res, text))
    text, res = explain(e, "product.jira_key")
    check("…only product slots asked: nothing is explained, and no «no slots» line either", res["slots"] == [] and res["needs_product"] is True
          and "Слотів із кандидатами немає" not in text, text)
    text, res = explain(e, "product.jira_key", product="Zorg Lite")
    check("…a product named: its slot, for that product", res["needs_product"] is False and "products" not in res
          and [(s_["record"], outs(s_)) for s_ in res["slots"]] == [("product.zorg-lite", [("mine", "won")])], res)
with tempfile.TemporaryDirectory() as d:
    e = Env(d)
    for label, kw, exc in (("an unknown slot", {"slots": ["team.nowhere"]}, ValueError), ("an unknown skill", {"skill": "no-such-skill"}, KeyError)):
        try:
            rv.explain(e.store, e.copies, REPOS, [], today="2026-10-20", catalogue=CAT, **kw)
            got = None
        except Exception as x:  # noqa: BLE001
            got = type(x)
        check("explain: %s is a %s" % (label, exc.__name__), got is exc, got)
    text, res = explain(e, skill="context-connect")
    check("a skill that reads the whole file asks no slot: said once", res["slots"] == [] and rv.WHOLE_SKILL in text and "Слотів із кандидатами немає" not in text, text)
    man = {"every_skill": {"records": ["profile"]}, "skills": {"x": {"product": {"required": ["Jira Project Key"], "fields": ["Description"],
           "sections": ["Key Metrics", "Nonexistent name"]}, "profile": {"required": ["Email"]}, "team": {"sections": ["Members"]}}}}
    check("the slots a skill asks: the profile, then the product, then the team; required, fields, sections; a name with no slot left out",
          rv._asked(cr.manifest_for(man, "x"), CAT) == [("profile.email", True), ("product.jira_key", True), ("product.description", True),
                                                          ("product.key_metrics", False), ("team.members", False)], rv._asked(cr.manifest_for(man, "x"), CAT))
    text, res = explain(e, skill="x", manifest=man)
    check("explain --skill takes the manifest it is given; every place of every slot it asks is there",
          [s_["slot"] for s_ in res["slots"]] == ["profile.email", "product.jira_key", "product.description", "product.key_metrics", "team.members"], [s_["slot"] for s_ in res["slots"]])
    text, res = explain(e, "team.members", "product.jira_key", skill="x", manifest=man)
    check("slots and a skill together: only the slots named, in the order named", [s_["slot"] for s_ in res["slots"]] == ["team.members", "product.jira_key"], res["slots"])
    text, res = explain(e, repos=REPOS[:1] + [dict(REPOS[1], skip_blocks=["growth-metrics", "other"])] )
    check("without arguments: the blocks of skip_blocks of every registration",
          res["skipped_blocks"] == [{"repo": "zorg-growth", "block": "growth-metrics"}, {"repo": "zorg-growth", "block": "other"}], res["skipped_blocks"])
    check("…and the regions no binding takes, each once, with where they are and what they are called",
          [(b_["repo"], b_["block"], b_["version"], b_["heading"]) for b_ in res["unmapped_blocks"]]
          == [("zorg-growth", "growth-metrics", "0.1", "Growth metrics"), ("zorg-core", "scope", "0.4", "Scope of work"), ("zorg-core", "teams", "0.4", "Teams map")],
          res["unmapped_blocks"])
    remember(e, memory(("zorg-core", "scope", None, "product.scope", None)))
    text, res = explain(e)
    check("…a block you bound is not unmapped any more; a region of nobody's repository is never listed",
          "scope" not in [b_["block"] for b_ in res["unmapped_blocks"]], res["unmapped_blocks"])
    remember(e, memory(("zorg-core", "scope", None, "product.retired_metrics", None)))
    text, res = explain(e)
    check("…v3.15.2: a block bound only to a slot the catalogue lacks is still not listed as no slot's — its unknown line says what is wrong",
          "scope" not in [b_["block"] for b_ in res["unmapped_blocks"]], res["unmapped_blocks"])
    remember(e, memory(("zorg-core", "scope", None, "product.scope", None)))
    text, res = explain(e, repos=[REPOS[0]])
    check("…a repository that is not registered owns no unmapped block", [b_["repo"] for b_ in res["unmapped_blocks"]] == ["zorg-core"], res["unmapped_blocks"])

# ------------------------------------------------------------------ the bindings that do nothing
def problems(e, mem, repos=REPOS):
    return rv.binding_problems(rv.slot_context(e.store, e.copies, repos, "Zorg App", NOW, mem=mem))


with tempfile.TemporaryDirectory() as d:
    e = Env(d)
    got = problems(e, memory(("zorg-core", "gone", None, "product.scope", None)))
    check("a binding to a block the core took away: missing (Review Focus 1), with the line that names it",
          [(p_["kind"], p_["slot"], p_["repo"], p_["block"], p_["how"]) for p_ in got] == [("missing", "product.scope", "zorg-core", "gone", "memory")]
          and got[0]["text"] == "прив'язка до блоку, якого немає в записах: zorg-core gone → product.scope", got)
    got = problems(e, memory(("zorg-nowhere", "scope", None, "product.scope", None)))
    check("…a repository nobody registered: said so, not «missing»", [p_["kind"] for p_ in got] == ["unregistered"], got)
    check("…the plugin's own binding of a team block without Members is no problem; nor is a bound block that is fine",
          problems(e, memory(("zorg-core", "scope", None, "product.scope", None))) == [], problems(e, memory()))
    got = problems(e, memory(("zorg-core", "team", "Nowhere", "team.members", None)))
    check("a binding to a subsection the block lacks: empty (spec §4.5)", [(p_["kind"], p_["sub"]) for p_ in got] == [("empty", "Nowhere")]
          and "підсекції «Nowhere»" in got[0]["text"], got)
    got = problems(e, memory(("zorg-core", "scope", None, "product.scope", None), ("zorg-core", "scope", None, "product.key_metrics", None)))
    check("…a block bound to several slots and a part for only one of them: empty for the other",
          [(p_["kind"], p_["slot"]) for p_ in got] == [("empty", "product.key_metrics")], got)
    got = problems(e, memory(("zorg-core", "gone", None, "product.nowhere", None)))
    check("a binding to a slot the catalogue lacks (v3.15.0 Task 7): unknown, whatever else is wrong with it — `validate` names it",
          [(p_["kind"], p_["slot"], p_["repo"], p_["block"], p_["how"]) for p_ in got] == [("unknown", "product.nowhere", "zorg-core", "gone", "memory")]
          and got[0]["text"] == "прив'язка до слоту, якого немає в каталозі: zorg-core gone → product.nowhere", got)
    got = problems(e, memory(("zorg-core", "team", "Members", "team.nowhere", None)))
    check("…with its subsection in the line", [(p_["kind"], p_["sub"]) for p_ in got] == [("unknown", "Members")]
          and got[0]["text"] == "прив'язка до слоту, якого немає в каталозі: zorg-core team#Members → team.nowhere", got)
    check("…and every kind of problem carries `why`, the short reason `validate` prints after the slot",
          all(isinstance(p_.get("why"), str) and p_["why"] for p_ in got), got)
with tempfile.TemporaryDirectory() as d:
    e = Env(d, edits=[("## Zorg Core Notes\n\n", "## Zorg Core Notes\n\n" + SCOPE + "\n\n")])
    got = problems(e, memory(("zorg-core", "scope", None, "product.scope", None)))
    check("a block that is not one sound region (repeated): broken", [p_["kind"] for p_ in got] == ["broken"], got)
    check("…proposals skip it: a block that is not one sound region would take no binding", sl.proposals(e.records(), REPOS, sl.bindings_of(e.store, REPOS, memory())[0], CAT) == [],
          sl.proposals(e.records(), REPOS, {}, CAT))
with tempfile.TemporaryDirectory() as d:
    e = Env(d)
    e.state("zorg-core", {"scope": ("0.4", [SCOPE.replace("v=0.4 -->", "v=0.4 slot=product.scope,org.structure -->")])})
    got = problems(e, memory(("zorg-core", "scope", None, "product.key_metrics", None)))
    check("a block you bound whose base names slots by slot=: every slot it names that you did not bind is ignored, and the line says so (Review Focus 2)",
          [(p_["kind"], p_["slot"], p_["how"]) for p_ in got] == [("ignored", "product.scope", "marker"), ("ignored", "org.structure", "marker")]
          and got[0]["text"] == "атрибут slot=product.scope блоку zorg-core scope ігноровано — блок прив'язано твоєю прив'язкою (до product.key_metrics)", got)
    check("…the slot you did bind with it too is not ignored", [p_["slot"] for p_ in problems(e, memory(("zorg-core", "scope", None, "product.scope", None)))]
          == ["org.structure"], problems(e, memory(("zorg-core", "scope", None, "product.scope", None))))
    got = problems(e, memory())
    check("…the publisher's own slot= that names a slot the block has no part for (a block of several slots): empty, like yours (spec §4.5)",
          [(p_["kind"], p_["slot"], p_["how"]) for p_ in got] == [("empty", "org.structure", "marker")], got)

with tempfile.TemporaryDirectory() as d:
    e = Env(d)
    e.state("zorg-core", {"scope": ("0.4", [SCOPE.replace("v=0.4 -->", "v=0.4 slot=product.nowhere -->")])})
    got = problems(e, memory())
    check("the publisher's slot= that names a slot the catalogue lacks: unknown, with how marker", [(p_["kind"], p_["slot"], p_["how"]) for p_ in got]
          == [("unknown", "product.nowhere", "marker")], got)
    e.state("zorg-core", {"scope": ("0.4", [SCOPE.replace("v=0.4 -->", "v=0.4 slot=product.scope -->")])})
    check("…and a slot= that the block can answer, with nobody binding the block, is no problem", problems(e, memory()) == [], problems(e, memory()))
    e.state("zorg-core", {"scope": ("0.4", [SCOPE.replace("v=0.4 -->", "v=0.4 slot=product.scope,org.structure -->")])})
    mem = memory(("zorg-core", "gone", None, "org.structure", None), ("zorg-core", "scope", None, "product.key_metrics", None))
    remember(e, mem)
    text, res = explain(e)
    check("without arguments a slot with only a note is listed, with the note — and says nothing was found",
          outs(entry(res, "org.structure")) == [] and entry(res, "org.structure")["notes"][0] == problems(e, mem)[0]["text"]
          and "  увага: прив'язка до блоку, якого немає в записах: zorg-core gone → org.structure" in text
          and "org.structure · текст · Organization: Zorg · не знайдено" in text, text)
    check("…the ignored attribute is shown under the slot it names", "увага: атрибут slot=product.scope блоку zorg-core scope ігноровано" in text
          and entry(res, "product.scope")["notes"], text)

# ------------------------------------------------------------------ final review: a binding that gives the slot nothing
TEAM_MEMBERS_HEADING = ("#### Members (registry", "#### Team Members (registry")
with tempfile.TemporaryDirectory() as d:
    e = Env(d, edits=[TEAM_MEMBERS_HEADING])
    e.state("zorg-core", {"team": ("0.2", [region(e.text, "zorg-core", "team")])})
    got = cands(e, "team.members")
    body = next(x for x in e.records() if x["id"] == "team.alpha-a")["body"]
    check("final review: the plugin's team#Members finds nothing under `Team Members` — the block answers by name, as cr._lookup found it",
          len(got) == 1 and got[0]["how"] == "name" and got[0]["block"] == "team" and got[0]["source"] == "zorg-core"
          and got[0]["text"] == cr._lookup(body, "Members", field=False)[0] and got[0]["text"].startswith("#### Team Members")
          and got[0]["level"] == "repo" and got[0]["sub"] is None and got[0]["place"] == "team.alpha-a", got)
    text, res = explain(e, "team.members")
    tm = entry(res, "team.members")
    check("…explain tells the truth: the block is shown by name; nothing «не знайдено», no note (the plugin's binding is no problem)",
          outs(tm) == [("zorg-core", "shown")] and tm["candidates"][0]["how"] == "name" and "notes" not in tm
          and "  ✔ zorg-core · блок team v0.2 у записі team.alpha-a · станом на 2026-10-20 · за назвою, без прив'язки\n" in text
          and rv.NOT_FOUND not in text and rv.NO_BLOCKS not in text, (tm, text))
    mem = memory(("zorg-core", "team", "Members", "team.members", None))
    got = cands(e, "team.members", mem=mem)
    check("…but a binding of yours to the subsection the block lacks is your word on the block: no candidate, no guess by name — "
          "the binding is named as empty", got == [] and [p_["kind"] for p_ in problems(e, mem)] == ["empty"], got)
    mem = memory(("zorg-core", "team", None, "team.members", "team.beta-b"))
    check("…a binding that gives the slot its text but places the block with a team not read: the block is that team's, not found by name here",
          cands(e, "team.members", mem=mem) == [], cands(e, "team.members", mem=mem))
TEAM_ID_IN_BLOCK = [("- **Jira Team ID:** <team-uuid>\n", ""), ("- **jira_team_field:** Alpha\n", "- **jira_team_field:** Alpha\n- **Jira Team ID:** core-uuid\n")]
with tempfile.TemporaryDirectory() as d:
    e = Env(d, edits=TEAM_ID_IN_BLOCK)
    got = cands(e, "team.jira_team_id")
    check("…a block bound to another slot only (the plugin's team#Members) answers this slot by name, as v3.14.1 read it",
          [(c["how"], c["block"], c["text"]) for c in got] == [("name", "team", "- **Jira Team ID:** core-uuid\n")], got)
GROWTH_KM = GROWTH.replace("#### Growth metrics", "#### Key Metrics")
with tempfile.TemporaryDirectory() as d:
    e = Env(d, edits=[(GROWTH, GROWTH_KM)])
    check("follow-up: unbound, the product record's block with a `Key Metrics` heading answers product.key_metrics by name",
          [(c["how"], c["block"]) for c in cands(e, "product.key_metrics")] == [("name", "growth-metrics")], cands(e, "product.key_metrics"))
    mem = memory(("zorg-growth", "growth-metrics", None, "org.key_metrics", None))
    got, org = cands(e, "product.key_metrics", mem=mem), cands(e, "org.key_metrics", mem=mem)
    check("follow-up: bound by you to org.key_metrics, the block is no product.key_metrics candidate by name (two `Key Metrics` are two slots)",
          got == [] and [(c["how"], c["block"]) for c in org] == [("memory", "growth-metrics")], (got, org))
    e.state("zorg-growth", {"growth-metrics": ("0.1", [GROWTH_KM.replace("v=0.1 -->", "v=0.1 slot=org.key_metrics -->")])})
    got, org = cands(e, "product.key_metrics"), cands(e, "org.key_metrics")
    check("…and the same with the publisher's slot=org.key_metrics in the block's base", got == []
          and [(c["how"], c["block"]) for c in org] == [("marker", "growth-metrics")], (got, org))
with tempfile.TemporaryDirectory() as d:
    e = Env(d, edits=[(GROWTH, GROWTH_KM)])
    e.state("zorg-growth", {"growth-metrics": ("0.1", [GROWTH_KM.replace("v=0.1 -->", "v=0.1 slot=org.nowhere -->")])})
    got = cands(e, "product.key_metrics")
    check("v3.15.1: the publisher's slot= to a slot the catalogue lacks does nothing — the block still answers product.key_metrics by name",
          [(c["how"], c["block"]) for c in got] == [("name", "growth-metrics")], got)
    check("…and validate still names that slot= as unknown", [(p_["kind"], p_["slot"], p_["how"]) for p_ in problems(e, memory())]
          == [("unknown", "org.nowhere", "marker")], problems(e, memory()))
    e.state("zorg-growth", {"growth-metrics": ("0.1", [GROWTH_KM])})
    mem = memory(("zorg-growth", "growth-metrics", None, "product.retired_metrics", None))
    got = cands(e, "product.key_metrics", mem=mem)
    check("v3.15.1: your binding to a slot the catalogue no longer has does nothing — the block still answers product.key_metrics by name",
          [(c["how"], c["block"]) for c in got] == [("name", "growth-metrics")], got)
    check("…and validate still names that binding as unknown", [(p_["kind"], p_["slot"], p_["how"]) for p_ in problems(e, mem)]
          == [("unknown", "product.retired_metrics", "memory")], problems(e, mem))

# ------------------------------------------------------------------ v3.15.2: a binding to a slot the catalogue lacks is no binding — the next source binds
PLUGIN_TEAM = [{"slot": "team.members", "sub": "Members", "team": None, "how": "plugin"}]
SCOPE_MARKED = SCOPE.replace("v=0.4 -->", "v=0.4 slot=product.scope -->")
TEAM_AHEAD = TEAM.replace("v=0.2 -->", "v=0.2 slot=team.rituals -->")
with tempfile.TemporaryDirectory() as d:
    e = Env(d)
    e.state("zorg-core", {"scope": ("0.4", [SCOPE_MARKED]), "team": ("0.2", [TEAM])})
    mem = memory(("zorg-core", "scope", None, "product.retired_metrics", None))
    binds, _ = sl.bindings_of(e.store, REPOS, mem)
    check("v3.15.2: your binding to a slot the catalogue lacks does not set the publisher's slot= aside — the marker binds the block",
          binds.get(("zorg-core", "scope")) == [{"slot": "product.scope", "sub": None, "team": None, "how": "marker"}], binds)
    check("…so the block answers that slot through the publisher's binding",
          [(c["how"], c["block"]) for c in cands(e, "product.scope", mem=mem)] == [("marker", "scope")], cands(e, "product.scope", mem=mem))
    check("…and validate names your binding unknown, with no «ignored» line for the publisher's slot=",
          [(p_["kind"], p_["slot"], p_["how"]) for p_ in problems(e, mem)] == [("unknown", "product.retired_metrics", "memory")], problems(e, mem))
    mem = memory(("zorg-core", "scope", None, "product.retired_metrics", None), ("zorg-core", "scope", None, "product.key_metrics", None))
    binds, _ = sl.bindings_of(e.store, REPOS, mem)
    check("…your bindings of one block to a known and an unknown slot: only the known one binds, and yours still wins over slot=",
          binds.get(("zorg-core", "scope")) == [{"slot": "product.key_metrics", "sub": None, "team": None, "how": "memory"}], binds)
    mem = memory(("zorg-core", "team", None, "team.retired", None))
    binds, _ = sl.bindings_of(e.store, REPOS, mem)
    check("…your binding of the team block to a slot the catalogue lacks leaves the plugin's team#Members in force",
          binds.get(("zorg-core", "team")) == PLUGIN_TEAM, binds)
    dropped = []
    try:
        sl.bindings_of(e.store, REPOS, memory(("zorg-core", "scope", None, "product.retired_metrics", None)), dropped=dropped)
    except TypeError as x:
        dropped = x
    check("…bindings_of hands back the bindings it set aside as unknown (`dropped`), so validate can name them",
          dropped == [{"ns": "zorg-core", "block": "scope", "slot": "product.retired_metrics", "sub": None, "team": None, "how": "memory"}], dropped)
with tempfile.TemporaryDirectory() as d:
    e = Env(d)
    e.state("zorg-core", {"scope": ("0.4", [SCOPE.replace("v=0.4 -->", "v=0.4 slot=product.scope,org.nowhere -->")]),
                          "team": ("0.2", [TEAM_AHEAD])})
    binds, _ = sl.bindings_of(e.store, REPOS, memory())
    check("v3.15.2: the publisher's slot= naming a known and an unknown slot binds the known one only",
          binds.get(("zorg-core", "scope")) == [{"slot": "product.scope", "sub": None, "team": None, "how": "marker"}], binds)
    check("…a core ahead of the plugin (slot=team.rituals on the team block) leaves the plugin's team#Members in force",
          binds.get(("zorg-core", "team")) == PLUGIN_TEAM, binds)
    check("…and validate names both unknown slots of the publisher",
          sorted((p_["kind"], p_["slot"], p_["how"]) for p_ in problems(e, memory()))
          == [("unknown", "org.nowhere", "marker"), ("unknown", "team.rituals", "marker")], problems(e, memory()))
with tempfile.TemporaryDirectory() as d:
    e = Env(d, edits=[TEAM_MEMBERS])
    e.state("zorg-core", {"team": ("0.2", [TEAM_AHEAD])})
    got = cands(e, "team.members")
    check("v3.15.2: with your own Team Members table, a core ahead of the plugin no longer drops the core's half of team.members",
          [(c["source"], c["how"]) for c in got] == [("mine", None), ("zorg-core", "plugin")], got)

# ------------------------------------------------------------------ unread_lines
with tempfile.TemporaryDirectory() as d:
    e = Env(d)
    ctx_ = lambda repos, skipped: rv.unread_lines(rv.slot_context(e.store, e.copies, repos, "Zorg App", NOW), skipped)    # noqa: E731
    check("unread_lines: nothing unread, nothing said", ctx_(REPOS, []) == [] and ctx_(REPOS, None) == [], ctx_(REPOS, []))
    check("…a registration not read, while a block carries a namespace no registration read has: one line for the file",
          ctx_(REPOS[:1], [("/p/zorg-growth.yaml", "slow")]) == [rv.UNREAD_REGISTRATION % "/p/zorg-growth.yaml"], ctx_(REPOS[:1], [("/p/zorg-growth.yaml", "slow")]))
    check("…and no line when every namespace in the records is registered", ctx_(REPOS, [("/p/other.yaml", "slow")]) == [], "")
    open(os.path.join(e.store.state_dir, "slots.json"), "w", encoding="utf-8").write("{ not json")
    got = ctx_(REPOS, [])
    check("…a memory that cannot be read: its line", len(got) == 1 and got[0].startswith("пам'ять слотів не прочитано (slots memory not valid: .state/slots.json"), got)
    os.remove(os.path.join(e.store.state_dir, "slots.json"))
    e.state("zorg-core", {"team": ("0.2", [TEAM])})
    open(os.path.join(e.store.state_dir, "blocks", "zorg-core.json"), "w", encoding="utf-8").write("{ not json")
    check("…a block state that cannot be read: its line", ctx_(REPOS, []) == [STATE_LINE], ctx_(REPOS, []))

# ------------------------------------------------------------------ proposals: the bindings `validate` suggests (spec §4.2)
def proposals_of(e, repos=REPOS, mem=None, bindings=None):
    binds = sl.bindings_of(e.store, repos, mem or memory())[0] if bindings is None else bindings
    return sl.proposals(e.records(), repos, binds, CAT)


SCOPE_P = {"repo": "zorg-core", "block": "scope", "sub": None, "slot": "product.scope"}
GROWTH_SUB = ("- **North star:** weekly active shoppers\n<!-- zorg-growth:end id=growth-metrics -->",
              "- **North star:** weekly active shoppers\n\n#### Key Metrics (focus)\n- Weekly active shoppers\n<!-- zorg-growth:end id=growth-metrics -->")
SCOPE_SUBS = ("The user works on Zorg App only.\n<!-- zorg-core:end id=scope -->",
              "The user works on Zorg App only.\n\n#### Key Metrics\n- DAU\n\n#### Ключові метрики\n- WAU\n\n#### Key Metrics\n- again\n<!-- zorg-core:end id=scope -->")
with tempfile.TemporaryDirectory() as d:
    e = Env(d)
    check("an unbound block of a registered repository whose first heading answers a slot's names: proposed — repository, block, no subsection, slot",
          proposals_of(e) == [SCOPE_P], proposals_of(e))
    check("…the plugin's `team` block is never proposed, even where no binding holds it (its Members heading answers team.members); the rest is as before",
          proposals_of(e, bindings={}) == [SCOPE_P] and not [p_ for p_ in proposals_of(e, bindings={}) if p_["block"] == "team"], proposals_of(e, bindings={}))
    check("…a block that has a binding — whatever slot it is bound to — is not proposed",
          proposals_of(e, mem=memory(("zorg-core", "scope", None, "product.key_metrics", None))) == []
          and proposals_of(e, mem=memory(("zorg-core", "scope", "Nowhere", "product.scope", None))) == [], "")
    check("…a repository nobody registered owns no proposal", proposals_of(e, repos=REPOS[1:]) == [], proposals_of(e, repos=REPOS[1:]))
    alias = [dict(REPOS[0], id="zorg-core-mirror")]
    check("…the proposal names the registration (its id), the block carries the namespace",
          proposals_of(e, repos=alias) == [dict(SCOPE_P, repo="zorg-core-mirror")], proposals_of(e, repos=alias))
    check("…nothing to propose in no records or no catalogue", sl.proposals([], REPOS, {}, CAT) == [] and sl.proposals(e.records(), REPOS, {}, {}) == []
          and sl.proposals(e.records(), [], {}, CAT) == [], "")
    check("proposals reads only: the records it was given are as they were", e.records() == e.records(), "")
with tempfile.TemporaryDirectory() as d:
    e = Env(d, edits=[GROWTH_SUB])
    check("a subsection of an unbound block whose heading answers a slot (a qualifier after the name counts): proposed with the heading as `sub`",
          proposals_of(e) == [{"repo": "zorg-growth", "block": "growth-metrics", "sub": "Key Metrics (focus)", "slot": "product.key_metrics"}, SCOPE_P],
          proposals_of(e))
with tempfile.TemporaryDirectory() as d:
    e = Env(d, edits=[SCOPE_SUBS])
    check("the block's first heading is the whole block, a later heading its subsection; each heading once, in both languages",
          proposals_of(e) == [SCOPE_P, {"repo": "zorg-core", "block": "scope", "sub": "Key Metrics", "slot": "product.key_metrics"},
                              {"repo": "zorg-core", "block": "scope", "sub": "Ключові метрики", "slot": "product.key_metrics"}], proposals_of(e))
with tempfile.TemporaryDirectory() as d:
    e = Env(d, edits=[("### Scope of work\n", "### Межі роботи\n")])
    check("a Ukrainian name answers the same slot", proposals_of(e) == [SCOPE_P], proposals_of(e))

# ------------------------------------------------------------------ validate_slots: what `ctx validate` says about slots
def validated(e, repos=REPOS, skipped=(), mem=None):
    if mem is not None:
        remember(e, mem)
    return rv.validate_slots(e.store, e.copies, repos, list(skipped), NOW, cat=CAT)


with tempfile.TemporaryDirectory() as d:
    e = Env(d)
    before = tree(e.home, e.vault)
    errors, warnings, props = validated(e)
    check("validate_slots → (errors, warnings, proposals); a proposal is a warning line and an item", errors == [] and props == [SCOPE_P]
          and warnings == ["proposal: ctx slot bind zorg-core scope product.scope"], (errors, warnings, props))
    check("…it writes nothing", tree(e.home, e.vault) == before, "")
    errors, warnings, props = validated(e, mem=memory(("zorg-core", "scope", None, "product.retired_metrics", None)))
    check("…v3.15.2: a block bound only to a slot the catalogue lacks binds nothing, yet is not proposed again — the unknown line says what is wrong",
          props == [] and "slot binding: zorg-core scope → product.retired_metrics — " + rv.WHY_UNKNOWN in warnings, (props, warnings))
    remember(e, memory())
    errors, warnings, props = validated(e, mem=memory(("zorg-core", "gone", None, "product.nowhere", None), ("zorg-nowhere", "scope", None, "product.scope", None),
                                                      ("zorg-core", "team", "Nowhere", "team.members", None), ("zorg-core", "gone2", None, "product.scope", None)))
    check("bindings that do nothing, one line each — «slot binding: <repo> <block>[#<sub>] → <slot> — <why>» (the unknown slot, the repository nobody registered, the subsection the block lacks, the block that is gone)", sorted(w_ for w_ in warnings if w_.startswith("slot binding: ")) == sorted([
              "slot binding: zorg-core gone → product.nowhere — " + rv.WHY_UNKNOWN,
              "slot binding: zorg-nowhere scope → product.scope — " + rv.WHY_UNREGISTERED,
              "slot binding: zorg-core team#Nowhere → team.members — у блоці немає підсекції «Nowhere»",
              "slot binding: zorg-core gone2 → product.scope — " + rv.WHY_GONE]), warnings)
    errors, warnings, props = validated(e, mem=memory(("zorg-core", "scope", None, "product.scope", None)))
    check("a memory that binds every block there is: nothing to say, nothing to propose", errors == [] and warnings == [] and props == [], (errors, warnings, props))
    open(os.path.join(e.store.state_dir, "slots.json"), "w", encoding="utf-8").write("{ not json")
    errors, warnings, props = validated(e)
    check("a slots memory that cannot be read: one error (it names the file), and nothing guessed from an empty memory — no binding line, no divergence, no proposal",
          len(errors) == 1 and errors[0].startswith("slots memory not valid: .state/slots.json") and warnings == [] and props == [], (errors, warnings, props))
    os.remove(os.path.join(e.store.state_dir, "slots.json"))
    errors, warnings, props = validated(e, repos=REPOS[:1], skipped=[("/p/zorg-growth.yaml", "slow")])
    check("a registration that was not read, while a block carries its namespace: the line `ctx read` prints, as a warning",
          errors == [] and rv.UNREAD_REGISTRATION % "/p/zorg-growth.yaml" in warnings, warnings)
    e.state("zorg-core", {"team": ("0.2", [TEAM])})
    open(os.path.join(e.store.state_dir, "blocks", "zorg-core.json"), "w", encoding="utf-8").write("{ not json")
    errors, warnings, props = validated(e)
    check("a block state that cannot be read: its line as a warning — the slot= attributes it holds are unknown, so the checks are not complete",
          errors == [] and STATE_LINE in warnings, warnings)

print("RESULT:", "GREEN ✅" if not fails else "RED ❌", "(%d failed)" % fails)
sys.exit(1 if fails else 0)
