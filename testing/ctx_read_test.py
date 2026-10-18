#!/usr/bin/env python3
"""TC-ctx-3120-read — scripts/ctx_read.py: the context manifest and `ctx read` (since v3.12.0).

Every skill's read view on migrated fictional fixtures (testing/fixtures/ctx/, "Zorg") with a temp
HOME and a temp vault: the token budget, product choice, settings by title prefix, read-through of
edits not imported yet and of records missing on disk, archived records hidden, stale and invalid
marks, missing fields; the manifest check behind validator check 16. Semantics:
references/context-protocol.md. Stdlib only; run from the repo root.
"""
import os, shutil, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import ctx_blocks as cb  # noqa: E402
import ctx_ops as co  # noqa: E402
import ctx_read as cr  # noqa: E402
import ctx_store as cs  # noqa: E402

FIX = os.path.join(ROOT, "testing", "fixtures", "ctx")
REPOS_FIX = os.path.join(ROOT, "testing", "fixtures", "ctx-repos")
NOW = "2026-10-20T10:00:00+03:00"
TODAY = NOW[:10]
SKILLS = sorted(n for n in os.listdir(os.path.join(ROOT, "skills")) if os.path.isdir(os.path.join(ROOT, "skills", n)))
fails = 0


def check(name, cond, detail=""):
    global fails
    fails += not cond
    print(("✅" if cond else "❌"), name, ("" if cond else "-> " + str(detail)[:600]))


def read(*parts):
    return open(os.path.join(*parts), encoding="utf-8", newline="").read()


class Env:
    """A migrated store over a fixture: temp HOME, temp vault and its mirror."""

    def __init__(self, d, fixture="typical", extra="", edit=None, fix=FIX, edits=()):
        self.home = os.path.join(d, "home")
        self.vault = os.path.join(d, "vault")
        os.makedirs(os.path.join(self.home, ".grow-pm"))
        os.makedirs(os.path.join(self.vault, "Notes", "_System"))
        self.text = read(fix, fixture + ".md").replace("{{VAULT}}", self.vault) + extra
        for old, new in ([edit] if edit else []) + list(edits):
            assert old in self.text, old
            self.text = self.text.replace(old, new, 1)
        self.ctx = os.path.join(self.home, ".grow-pm", "local-context.md")
        for p in (self.ctx, os.path.join(self.vault, "Notes", "_System", "local-context.md")):
            open(p, "w", encoding="utf-8", newline="").write(self.text)
        self.copies = co.copies_for(self.ctx, self.text, home=self.home)
        self.store = cs.Store(co.store_root_for(self.text, home=self.home))
        co.migrate(self.ctx, self.store.root, self.copies, self.home, apply=True, now=NOW)

    def view(self, skill, product=None, today=TODAY, **kw):
        return cr.read_view(self.store, self.copies, skill, product=product, today=today, **kw)

    def edit(self, path, old, new):
        t = read(path)
        assert old in t, old
        open(path, "w", encoding="utf-8", newline="").write(t.replace(old, new, 1))


with tempfile.TemporaryDirectory() as d:
    t = Env(os.path.join(d, "t"))
    r = Env(os.path.join(d, "r"), "rich")
    over = []
    for s in SKILLS:
        for env, prod in ((t, "Zorg App"), (r, None)):
            text, res = env.view(s, product=prod)
            if res["tokens_est"] > 6000 or res["needs_product"]:
                over.append((s, res["tokens_est"], res["needs_product"]))
    check("every skill reads within 6000 tokens", over == [] and len(SKILLS) == 33, over)
    text, res = t.view("requirements-creator", product="Zorg App")
    check("requirements-creator gets its required fields", "- **Jira Project Key:** PROJ" in text
          and "#### Platforms" in text and "#### Competitors" not in text and "product.zorg-app" in res["records"], text[:900])
    text, res = t.view("requirements-creator")
    check("two products need a choice", res["needs_product"] and "Zorg App" in text and "Zorg Lite" in text
          and "- **Jira Project Key:**" not in text
          and 'ctx.py" read --skill requirements-creator --product "<' in text, text[-500:])
    text, res = t.view("requirements-creator", product="Zorg")
    check("ambiguous product needs a choice", res["needs_product"], res)
    text, res = t.view("requirements-creator", product="product.zorg-lite")
    check("--product by id", "Product: Zorg Lite" in text and "product.zorg-lite" in res["records"], res["records"])
    try:
        t.view("no-such-skill"); unknown = False
    except KeyError:
        unknown = True
    check("unknown skill is exit 3", unknown)

with tempfile.TemporaryDirectory() as d:
    e = Env(d, "minimal")
    text, res = e.view("requirements-creator")
    check("one product is chosen automatically", not res["needs_product"]
          and any(i.startswith("product.") for i in res["records"]), res)

with tempfile.TemporaryDirectory() as d:
    e = Env(d, extra="\n## Terminology & Style (мова команди)\n\n- **Glossary:** zorg terms\n\n")
    text, res = e.view("requirements-creator", product="Zorg App")
    check("settings by title prefix", "Glossary:** zorg terms" in text, res["records"])

with tempfile.TemporaryDirectory() as d:
    e = Env(d)
    e.edit(e.ctx, "- **Jira Project Key:** PROJ", "- **Jira Project Key:** PENDING")
    text, res = e.view("requirements-creator", product="Zorg App")
    check("a pending edit is read through with a note", "- **Jira Project Key:** PENDING" in text
          and "ctx sync" in text and res["pending"] >= 1, text[:400])

with tempfile.TemporaryDirectory() as d:
    e = Env(d)
    os.remove(os.path.join(e.store.records_dir, "setting.templates.md"))
    text, res = e.view("requirements-creator", product="Zorg App")
    check("a record missing on disk is read from the copy with a note", "- **Preference:** builtin" in text
          and "немає на диску" in text, text[-700:])

with tempfile.TemporaryDirectory() as d:
    e = Env(d)
    co.archive(e.store, e.copies, e.home, "setting.templates", "old", NOW)
    text, res = e.view("requirements-creator", product="Zorg App")
    check("an archived record is not shown", "- **Preference:** builtin" not in text
          and "setting.templates" not in res["records"], res["records"])

with tempfile.TemporaryDirectory() as d:
    e = Env(d)
    co.invalidate(e.store, e.copies, e.home, "setting.templates", "old", NOW)
    prod = {x["id"]: x for x in e.store.load()}["product.zorg-app"]
    e.store.write(dict(prod, verified="2026-01-01"))
    text, res = e.view("requirements-creator", product="Zorg App")
    head = [l for l in text.splitlines() if l.startswith("## ")]
    check("stale and invalid marks in the header line",
          any("product.zorg-app" in l and "⚠ застаріле (TTL 90 д)" in l for l in head)
          and any("setting.templates" in l and "⚠ неактуально: old" in l for l in head), head)

with tempfile.TemporaryDirectory() as d:
    e = Env(d)
    e.edit(e.ctx, "- **Jira Project Key:** PROJ\n", "")
    co.apply_sync(e.store, co.plan_sync(e.store, e.copies), e.copies, e.home, "test", "", NOW)
    text, res = e.view("requirements-creator", product="Zorg App")
    check("missing required field is listed", "Jira Project Key (обов'язкове)" in text
          and "Jira Project Key" in res["missing"], text[-400:])

with tempfile.TemporaryDirectory() as d:
    e = Env(d, edit=("#### Platforms", "#### Platforms (mobile first)"))
    text, res = e.view("requirements-creator", product="Zorg App")
    check("subsections match by the start of their heading", "#### Platforms (mobile first)" in text
          and "Platforms" not in res["missing"], res["missing"])

with tempfile.TemporaryDirectory() as d:
    e = Env(d, "minimal")
    t = read(e.ctx)
    at = t.index("### Product: Zorg App")
    new = "### Product: Zorg Lite\n\n- **Jira Project Key:** LITE\n\n"
    open(e.ctx, "w", encoding="utf-8", newline="").write(t[:at] + new + t[at:])
    text, res = e.view("requirements-creator")
    text2, res2 = e.view("requirements-creator", product="Zorg Lite")
    check("a new section not imported yet is read through", res["needs_product"]
          and "- **Jira Project Key:** LITE" in text2 and "ctx sync" in text2 and not res2["needs_product"], (res, res2))

# --- v3.12.1: read_by — the custom and setting records a skill reads
CUSTOM = "\n## Zorg Partner Rules\n\n- Always say Zorg Partner.\n- Detail: never Partner Zorg in print.\n\n"   # the card shows line 1 only


def rec_titled(e, title):
    return next(r for r in e.store.load() if r["title"] == title)


def set_meta(e, title, **kw):
    e.store.write(dict(rec_titled(e, title), **kw))


with tempfile.TemporaryDirectory() as d:
    e = Env(d, extra=CUSTOM)
    cid = rec_titled(e, "Zorg Partner Rules")["id"]
    text, res = e.view("product-analysis", product="Zorg App")
    check("unassigned custom is named, not read",
          "Власні секції без призначення: Zorg Partner Rules (%s)" % cid in text
          and "never Partner Zorg" not in text and res["unassigned"] == [cid], text[-600:])
    set_meta(e, "Zorg Partner Rules", read_by="all")
    text, res = e.view("product-analysis", product="Zorg App")
    check("read_by all → read whole", "never Partner Zorg" in text and cid in res["records"]
          and "без призначення" not in text and res["unassigned"] == [], text[-600:])
    set_meta(e, "Zorg Partner Rules", read_by="product-analysis")
    pa_text, _ = e.view("product-analysis", product="Zorg App")
    wc_text, _ = e.view("write-concept", product="Zorg App")
    check("read_by names one skill", "never Partner Zorg" in pa_text and "never Partner Zorg" not in wc_text
          and "без призначення" not in wc_text, wc_text[-400:])
    cfg_text, _ = e.view("plugin-configurator")
    check("full skill: no custom block, no unassigned line",
          "never Partner Zorg" not in cfg_text and "без призначення" not in cfg_text)
    set_meta(e, "Zorg Partner Rules", read_by="all", verified="2025-01-01", ttl_days=30)
    text_stale, _ = e.view("product-analysis", product="Zorg App")
    check("assigned stale record keeps its mark", "⚠ застаріле" in text_stale, text_stale[-600:])
    e.edit(e.ctx, "never Partner Zorg in print.", "never Partner Zorg — edited.")
    text_p, _ = e.view("product-analysis", product="Zorg App")
    check("pending edit of a custom section is read through", "never Partner Zorg — edited" in text_p
          and "ctx sync" in text_p, text_p[-600:])

with tempfile.TemporaryDirectory() as d:
    big = "\n## Zorg Big Appendix\n\n" + "- filler line about Zorg partners and their programmes\n" * 600 + "\n"
    e = Env(d, extra=CUSTOM + big)
    big_id = rec_titled(e, "Zorg Big Appendix")["id"]
    set_meta(e, "Zorg Big Appendix", read_by="all")
    text, res = e.view("product-analysis", product="Zorg App")
    check("over budget is flagged", res["over_budget"] and res["largest"] == big_id
          and "більше за 8000; найбільший запис: %s" % big_id in text, (res.get("over_budget"), res.get("largest")))

check("readers normalises three forms", cr.readers({"read_by": "Product-Analysis , write-concept"})
      == cr.readers({"read_by": ["product-analysis", "write-concept"]})
      == cr.readers({"read_by": "[product-analysis, write-concept]"}) == frozenset({"product-analysis", "write-concept"}))
check("readers unset", cr.readers({}) is None and cr.readers({"read_by": ""}) is None)

# --- v3.12.1 minor m2: --product on a context without products
with tempfile.TemporaryDirectory() as d:
    e = Env(d, "minimal", edit=("### Product: Zorg App\n\n- **Jira Project Key:** PROJ\n", ""))
    text, res = e.view("requirements-creator", product="Zorg App")
    check("--product on a context without products", not res["needs_product"] and "продукт (обов'язкове)" in text, text[-400:])

# --- v3.13.0: where a repository's text comes from — a provenance line, own text before a block, a conflict mark
CHECKED = "2026-10-20T10:00:00+03:00"
REPOS = [{"id": "zorg-core", "namespace": "zorg-core"}, {"id": "zorg-growth", "namespace": "zorg-growth"}]
OWN_LEAD = ("- **Jira Team ID:** <team-uuid>\n", "- **Jira Team ID:** <team-uuid>\n- **Lead:** Own Lead\n")
BLOCK_LEAD = ("### Team: Alpha\n\n- **Team card", "### Team: Alpha\n\n- **Lead:** Block Lead\n- **Team card")
LEAD_SKILL = {"schema": "context-manifest/1", "skills": {"lead-skill": {"team": {"fields": ["Lead"]}}}}
LEAD_REQ = {"schema": "context-manifest/1", "skills": {"lead-skill": {"team": {"required": ["Lead"]}}}}


def block_state(env, repo, blocks, checked=CHECKED):
    """What `ctx provider adopt/apply` leaves in the store: the repository's check and, per block, its version and check."""
    entry = lambda v: {"base_sha": None, "bases": [], "v": v, "host": None, "checked": checked, "user_removed": None}
    with cs.guard_roots(co.allowed_roots(env.home, env.text)):
        cb.save_state(env.store, repo, {"checked": checked, "source": "folder", "version": "0.4",
                                        "blocks": {b: entry(v) for b, v in blocks.items()}})


def read_by(env, title, who):
    rec = next(r for r in env.store.load() if r["title"] == title)
    env.store.write(dict(rec, read_by=who))


with tempfile.TemporaryDirectory() as d:
    e = Env(d, "context", fix=REPOS_FIX)
    block_state(e, "zorg-core", {"scope": "0.4", "teams": "0.4", "team": "0.2"})
    read_by(e, "Zorg Core Notes", "all")
    text_rb, _ = e.view("product-analysis", product="Zorg App", repos=REPOS)
    check("provenance line before a repo region", "> [zorg-core · v0.4 · станом на 2026-10-20]\n<!-- zorg-core:begin id=scope v=0.4 -->" in text_rb
          and "> [zorg-core · v0.4 · станом на 2026-10-20]\n<!-- zorg-core:begin id=teams v=0.4 -->" in text_rb, text_rb[-700:])
    check("a region in a read_by record is shown once", text_rb.count("<!-- zorg-core:begin id=scope ") == 1
          and text_rb.count("[zorg-core ·") == 2, text_rb[-700:])
    text_none, _ = e.view("product-analysis", product="Zorg App")
    check("a namespace nobody registered gets its name, the version and no date",
          "> [zorg-core · v0.4]\n<!-- zorg-core:begin id=scope" in text_none and "станом на" not in text_none, text_none[-500:])
    block_state(e, "zorg-core", {"scope": "0.4"}, checked=None)
    text_nd, _ = e.view("product-analysis", product="Zorg App", repos=REPOS)
    check("a block never checked has no date", "> [zorg-core · v0.4]\n<!-- zorg-core:begin id=scope" in text_nd
          and "станом на" not in text_nd, text_nd[-500:])
    open(os.path.join(e.store.state_dir, "blocks", "zorg-core.json"), "w", encoding="utf-8").write("{ not json")
    text_bad, _ = e.view("product-analysis", product="Zorg App", repos=REPOS)
    check("a state file that cannot be read is no date and no failure", "> [zorg-core · v0.4]\n<!-- zorg-core:begin id=scope" in text_bad, text_bad[-500:])

with tempfile.TemporaryDirectory() as d:
    e = Env(d, "context", fix=REPOS_FIX)
    block_state(e, "zorg-core", {"scope": "0.4", "teams": "0.4", "team": "0.2"})
    text_hd, res_hd = e.view("hiring-designer", repos=REPOS)
    check("Members falls back to the team block, labelled", "#### Members" in text_hd
          and "> [zorg-core · v0.2 · станом на 2026-10-20]\n#### Members" in text_hd and "Bea Two" in text_hd
          and "Members" not in res_hd["missing"], text_hd[-900:])
    check("…and only the subsection: not the rest of the block, no region marker", "Team card (source of truth)" not in text_hd
          and "<!-- zorg-core" not in text_hd and "Growth squad" not in text_hd, text_hd[-900:])

SHARED = ("<!-- zorg-core:section:begin -->\n## Zorg shared core (reference)\n\n> From the core.\n\n"
          "<!-- zorg-core:begin id=scope v=0.4 -->\n### Scope of work\nZorg App only.\n<!-- zorg-core:end id=scope -->\n\n"
          "<!-- zorg-core:begin id=teams v=0.3 -->\n### Teams map\n- Alpha\n<!-- zorg-core:end id=teams -->\n"
          "<!-- zorg-core:section:end -->\n")
with tempfile.TemporaryDirectory() as d:
    e = Env(d, "minimal", extra="\n" + SHARED)
    read_by(e, "Zorg shared core (reference)", "all")
    text_w, _ = e.view("product-analysis", repos=REPOS)
    check("a section wrapper is no block: each block of it is labelled, the wrapper is not", text_w.count("> [zorg-core ·") == 2
          and "> [zorg-core · v0.3]\n<!-- zorg-core:begin id=teams" in text_w and "> [zorg-core · v0.4]\n<!-- zorg-core:begin id=scope" in text_w
          and "section:begin" in text_w and "]\n<!-- zorg-core:section:begin" not in text_w, text_w[-700:])

with tempfile.TemporaryDirectory() as d:
    e = Env(d, "context", fix=REPOS_FIX, edits=[OWN_LEAD, BLOCK_LEAD])
    block_state(e, "zorg-core", {"team": "0.2"})
    text, _ = e.view("lead-skill", repos=REPOS, manifest=LEAD_SKILL)
    check("own field wins over the block", "**Lead:** Own Lead" in text and text.count("**Lead:**") == 1
          and "Block Lead" not in text and "> [zorg-core" not in text, text[-500:])

with tempfile.TemporaryDirectory() as d:
    e = Env(d, "context", fix=REPOS_FIX, edits=[BLOCK_LEAD])
    block_state(e, "zorg-core", {"team": "0.2"})
    text, res = e.view("lead-skill", repos=REPOS, manifest=LEAD_REQ)
    check("a field only the block has is read from it, labelled", "> [zorg-core · v0.2 · станом на 2026-10-20]\n- **Lead:** Block Lead" in text
          and res["missing"] == [], (text[-500:], res["missing"]))
    e.edit(os.path.join(e.store.records_dir, "team.alpha-a.md"), "- **Lead:** Block Lead\n", "")
    text, res = e.view("lead-skill", repos=REPOS, manifest=LEAD_REQ)
    check("…and when neither has it, it is missing", "Lead" in res["missing"] and "Lead (обов'язкове)" in text, (text[-400:], res["missing"]))

with tempfile.TemporaryDirectory() as d:
    e = Env(d, "context", fix=REPOS_FIX, edits=[OWN_LEAD, BLOCK_LEAD])
    e.edit(os.path.join(e.store.records_dir, "team.alpha-a.md"), "- **Lead:** Own Lead\n", "")
    text, _ = e.view("lead-skill", repos=REPOS, manifest=LEAD_SKILL)
    check("a field in a region is read, even when an own line of the same name sits after it", "- **Lead:** Block Lead" in text, text[-400:])

with tempfile.TemporaryDirectory() as d:        # a region with no id is still a region: left out of your text, so it must be found where it is
    e = Env(d, "context", fix=REPOS_FIX, edits=[("<!-- zorg-core:begin id=team v=0.2 -->", "<!-- zorg-core:begin v=0.2 -->"),
                                                 ("<!-- zorg-core:end id=team -->", "<!-- zorg-core:end -->"),
                                                 BLOCK_LEAD])
    text, res = e.view("lead-skill", repos=REPOS, manifest=LEAD_REQ)
    check("a region with no block id: found, labelled with the namespace's repository and the version", res["missing"] == []
          and "> [zorg-core · v0.2]\n- **Lead:** Block Lead" in text, (text[-500:], res["missing"]))

PRODUCT_KEY = {"schema": "context-manifest/1", "skills": {"key-skill": {"product": {"fields": ["Jira Project Key"]}}}}
with tempfile.TemporaryDirectory() as d:        # a begin marker nothing closes is no region: what follows it is yours
    e = Env(d, "minimal", edit=("- **Jira Project Key:** PROJ", "<!-- zorg-core:begin id=open v=0.1 -->\n- **Jira Project Key:** PROJ"))
    text, res = e.view("key-skill", repos=REPOS, manifest=PRODUCT_KEY)
    check("an unclosed begin marker is no region", res["missing"] == [] and "- **Jira Project Key:** PROJ" in text
          and "> [zorg-core" not in text, (text[-500:], res["missing"]))

with tempfile.TemporaryDirectory() as d:
    e = Env(d)
    e.edit(e.ctx, "- **Jira Project Key:** PROJ", "- **Jira Project Key:** FROM-FILE")
    e.edit(os.path.join(e.store.records_dir, "product.zorg-app.md"), "- **Jira Project Key:** PROJ", "- **Jira Project Key:** FROM-RECORD")
    text_conflict, res = e.view("requirements-creator", product="Zorg App")
    head = [l for l in text_conflict.splitlines() if l.startswith("## ") and "product.zorg-app" in l]
    other = [l for l in text_conflict.splitlines() if l.startswith("## ") and "product.zorg-app" not in l]
    check("conflicting section is marked", len(head) == 1 and "⚠ конфлікт: файл і запис різняться — ctx sync" in head[0]
          and not any("конфлікт" in l for l in other), head)
    check("…the record is what is read, the file's text is not", "FROM-RECORD" in text_conflict and "FROM-FILE" not in text_conflict, text_conflict[:900])

# --- v3.14.1: a subsection nobody has is listed, and `Team Members` answers `Members`
SECTION_SKILL = {"schema": "context-manifest/1", "skills": {"sec-skill": {"product": {"sections": ["Nowhere Section"]}}}}
with tempfile.TemporaryDirectory() as d:
    e = Env(d)
    text, res = e.view("sec-skill", product="Zorg App", manifest=SECTION_SKILL)
    check("a missing subsection is listed, not as obligatory", "Nowhere Section" in res["missing"]
          and "Відсутнє: Nowhere Section — " in text and "Nowhere Section (обов'язкове)" not in text, (text[-400:], res["missing"]))
    text, res = e.view("hiring-designer", product="Zorg App")
    check("a team without the subsection is named with the team when there are several", "Members (Team: Beta (B))" in res["missing"]
          and "Members (Team: Alpha (A))" not in res["missing"] and "Members" not in res["missing"]
          and "Відсутнє: Members (Team: Beta (B))" in text, (text[-400:], res["missing"]))

with tempfile.TemporaryDirectory() as d:
    e = Env(d, edit=("#### Members\n", "#### Team Members\n"))
    text, res = e.view("task-creator", product="Zorg App")
    check("Team Members answers Members", "#### Team Members" in text and "Alex One" in text
          and "Members (Team: Alpha (A))" not in res["missing"], (text[-700:], res["missing"]))

TEAM_MEMBERS = ("- **Jira Team ID:** <team-uuid>\n", "- **Jira Team ID:** <team-uuid>\n\n#### Team Members\n\n| Name | Role |\n|---|---|\n| Own Person | PM |\n")
with tempfile.TemporaryDirectory() as d:
    e = Env(d, "context", fix=REPOS_FIX, edits=[TEAM_MEMBERS])
    block_state(e, "zorg-core", {"team": "0.2"})
    text, res = e.view("hiring-designer", repos=REPOS)
    check("your own Team Members wins over the block's Members", "Own Person" in text and "#### Team Members" in text
          and "Bea Two" not in text and "> [zorg-core" not in text
          and not any(m.startswith("Members") for m in res["missing"]), (text[-700:], res["missing"]))
with tempfile.TemporaryDirectory() as d:
    e = Env(d, "context", fix=REPOS_FIX)
    block_state(e, "zorg-core", {"team": "0.2"})
    text, res = e.view("hiring-designer", repos=REPOS)
    check("…and without it the block's Members is read as before", "> [zorg-core · v0.2 · станом на 2026-10-20]\n#### Members" in text
          and not any(m.startswith("Members") for m in res["missing"]), (text[-700:], res["missing"]))

check("check_manifest is clean on the repo", cr.check_manifest(ROOT) == [], cr.check_manifest(ROOT))
with tempfile.TemporaryDirectory() as d:
    src = read(cr.MANIFEST_PATH)
    start = src.index("\n  decision-log:")
    end = src.index("\n  delegation-coach:")
    path = os.path.join(d, "context-manifest.yaml")
    open(path, "w", encoding="utf-8").write(src[:start] + src[end:])
    errs = cr.check_manifest(ROOT, manifest_path=path)
    check("check_manifest flags a skill without an entry", any("decision-log" in x for x in errs), errs)

print("RESULT:", "GREEN ✅" if not fails else "RED ❌", "(%d failed)" % fails)
sys.exit(1 if fails else 0)
