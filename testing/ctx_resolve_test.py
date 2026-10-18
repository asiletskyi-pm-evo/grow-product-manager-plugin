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
KEYS = {"slot", "source", "level", "record", "block", "ns", "version", "checked", "edited", "rule", "how", "heading",
        "text", "rank", "placed", "place"}
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


def cands(e, slot, product="Zorg App", repos=REPOS, mem=None, teams=None):
    recs = e.records()
    prod = product_of(recs, product) if product else None
    mem = mem or sl.empty_memory()
    binds, _ = sl.bindings_of(e.store, repos, mem)
    return rv.candidates(slot, CAT, recs, prod, teams_of(recs, prod) if teams is None else teams, repos, mem, e.store, binds)


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
    plugin = [{"slot": "team.members", "sub": "Members", "team": None, "how": "plugin"},
              {"slot": "product.jira_key", "sub": None, "team": None, "how": "plugin"}]
    check("the plugin binds the team block of every registered repository", binds == {("zorg-core", "team"): plugin,
          ("zorg-growth", "team"): plugin} and problems == [], (binds, problems))
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
    jira = cands(e, "product.jira_key")
    check("one value: your field line, and the field line inside the team block (the plugin's jira_project_key)",
          [c["text"] for c in jira] == ["- **Jira Project Key:** PROJ\n", "- **jira_project_key:** PROJ (others: LEGACY)\n"]
          and [c["level"] for c in jira] == ["mine", "repo"] and jira[1]["place"] == "product.zorg-app"
          and jira[1]["heading"] == "jira_project_key", jira)
    check("the growth team block, plugin-bound too, has no Members subsection: no candidate", not by(got, source="zorg-growth"), got)
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
    check("a binding to a subsection the block lacks is no candidate", got == [], got)
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
    mem = memory(aliases=[("product.zorg-app", "Key Metrics (focus)", "org.key_metrics")])
    check("a heading you mapped to another slot is no candidate of this one (Review Focus 5)",
          cands(e, "product.key_metrics", mem=mem) == [], cands(e, "product.key_metrics", mem=mem))
    mem = memory(aliases=[("product.zorg-app", "Key Metrics (focus)", "org.key_metrics"),
                          ("product.zorg-app", "Key Metrics (focus)", "product.key_metrics")])
    check("…unless you mapped it to this slot as well", [c["heading"] for c in cands(e, "product.key_metrics", mem=mem)]
          == ["Key Metrics (focus)"], cands(e, "product.key_metrics", mem=mem))
    mem = memory(aliases=[("product.zorg-app", "focus  NUMBERS", "product.key_metrics")])
    got = cands(e, "product.key_metrics", mem=mem)
    check("a name you mapped adds a candidate, whatever its case and spacing", [c["heading"] for c in got]
          == ["Key Metrics (focus)", "Focus numbers"] and all(c["level"] == "mine" for c in got), got)
    mem = memory(aliases=[("product.zorg-app", "Key Metrics", "product.key_metrics")])
    check("the same heading found twice is one candidate", len(cands(e, "product.key_metrics", mem=mem)) == 1, "")
    mem = memory(aliases=[("product.other", "Focus numbers", "product.key_metrics")])
    check("a name mapped in another record does not count here", len(cands(e, "product.key_metrics", mem=mem)) == 1, "")
    got = cands(e, "product.platforms")
    check("a list slot answers by its field line too (Platforms is a typed list field)", len(got) == 1
          and got[0]["text"] == "- **Platforms:** Web, iOS\n" and got[0]["heading"] == "Platforms", got)

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

print("RESULT:", "GREEN ✅" if not fails else "RED ❌", "(%d failed)" % fails)
sys.exit(1 if fails else 0)
