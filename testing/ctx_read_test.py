#!/usr/bin/env python3
"""TC-ctx-3120-read — scripts/ctx_read.py: the context manifest and `ctx read` (since v3.12.0).

Every skill's read view on migrated fictional fixtures (testing/fixtures/ctx/, "Zorg") with a temp
HOME and a temp vault: the token budget, product choice, settings by title prefix, read-through of
edits not imported yet and of records missing on disk, archived records hidden, stale and invalid
marks, missing fields; the manifest check behind validator check 16. Semantics:
references/context-protocol.md. Stdlib only; run from the repo root.
"""
import hashlib, json, os, re, shutil, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import ctx_blocks as cb  # noqa: E402
import ctx_ops as co  # noqa: E402
import ctx_read as cr  # noqa: E402
import ctx_slots as sl  # noqa: E402
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


CHECKED = "2026-10-20T10:00:00+03:00"
REPOS = [{"id": "zorg-core", "namespace": "zorg-core"}, {"id": "zorg-growth", "namespace": "zorg-growth"}]


def block_state(env, repo, blocks, checked=CHECKED, bases=None):
    """What `ctx provider adopt/apply` leaves in the store: the repository's check and, per block, its version and check;
    `bases` {block id: text} — the repository's text of the block, kept as its base (its marker attributes, the edited mark)."""
    with cs.guard_roots(co.allowed_roots(env.home, env.text)):
        shas = {b: cb.put_base(env.store, repo, t) for b, t in (bases or {}).items()}
        entry = lambda b, v: {"base_sha": shas.get(b), "bases": [shas[b]] if b in shas else [], "v": v, "host": None,
                              "checked": checked, "user_removed": None}
        cb.save_state(env.store, repo, {"checked": checked, "source": "folder", "version": "0.4",
                                        "blocks": {b: entry(b, v) for b, v in blocks.items()}})


def read_by(env, title, who):
    rec = next(r for r in env.store.load() if r["title"] == title)
    env.store.write(dict(rec, read_by=who))


# --- v3.15.0: the golden read views — without bindings or memory, every view of v3.14.1 stays as it was (Task 5)
GOLDEN = os.path.join(ROOT, "testing", "fixtures", "ctx-read-golden.json")
GOLDEN_REPOS = [{"id": "zorg-core", "namespace": "zorg-core", "rank": 1000, "products": []},
                {"id": "zorg-growth", "namespace": "zorg-growth", "rank": 500, "products": []}]
GOLDEN_FIXTURES = (("typical", FIX, "typical", "Zorg App"), ("rich", FIX, "rich", None), ("ctx-repos", REPOS_FIX, "context", None))
SLOT_TAG = re.compile(r" · слот [a-z]+\.[a-z0-9_]+ — [^\]\n]*?(?= · |\])")


def golden_text(text, vault):
    """A read view as v3.14.1 and v3.15 must agree on it when nothing is bound but the plugin's own `team#Members`: the temp
    vault path is {{VAULT}}; the «Відсутнє» line (its long form is new) is dropped; the origin additions « · за назвою, без
    прив'язки» and « · слот <slot> — <about>» (the plugin binds the team block always) are taken out."""
    text = text.replace(vault, "{{VAULT}}")
    text = "\n".join(line for line in text.split("\n") if not line.startswith("Відсутнє:"))
    return SLOT_TAG.sub("", text.replace(" · за назвою, без прив'язки", ""))


def golden_key(text, vault):
    return hashlib.sha256(golden_text(text, vault).encode("utf-8")).hexdigest()


def golden_views(d, texts=False):
    """{"<fixture>/<skill>": golden_key} for every skill on typical (--product "Zorg App"), rich and ctx-repos/context (no
    --product) — 99 views; the ctx-repos store has the block state of zorg-core and its notes record is read by all skills.
    `texts`: the normalised texts instead of their keys."""
    out = {}
    for name, fix, fixture, prod in GOLDEN_FIXTURES:
        env = Env(os.path.join(d, name), fixture, fix=fix)
        if name == "ctx-repos":
            block_state(env, "zorg-core", {"scope": "0.4", "teams": "0.4", "team": "0.2"})
            read_by(env, "Zorg Core Notes", "all")
        for s in SKILLS:
            text, _ = env.view(s, product=prod, repos=GOLDEN_REPOS)
            out[name + "/" + s] = golden_text(text, env.vault) if texts else golden_key(text, env.vault)
    return out


if "--write-golden" in sys.argv:            # once, from the code of v3.14.1 (Task 5 Step 1); never to make a red test green
    with tempfile.TemporaryDirectory() as d:
        views = golden_views(d)
    with open(GOLDEN, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(views, indent=1, sort_keys=True) + "\n")
    print("wrote %d read views to %s" % (len(views), os.path.relpath(GOLDEN, ROOT)))
    sys.exit(0)

with tempfile.TemporaryDirectory() as d:
    want = json.load(open(GOLDEN, encoding="utf-8")) if os.path.isfile(GOLDEN) else {}
    got = golden_views(d)
    mismatches = sorted(k for k in set(want) | set(got) if want.get(k) != got.get(k))
check("without bindings or memory every read view is v3.14.1's", mismatches == [] and len(want) == 99, (len(want), mismatches))

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
OWN_LEAD = ("- **Jira Team ID:** <team-uuid>\n", "- **Jira Team ID:** <team-uuid>\n- **Lead:** Own Lead\n")
BLOCK_LEAD = ("### Team: Alpha\n\n- **Team card", "### Team: Alpha\n\n- **Lead:** Block Lead\n- **Team card")
LEAD_SKILL = {"schema": "context-manifest/1", "skills": {"lead-skill": {"team": {"fields": ["Lead"]}}}}
LEAD_REQ = {"schema": "context-manifest/1", "skills": {"lead-skill": {"team": {"required": ["Lead"]}}}}


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
    check("Members falls back to the team block, labelled", "#### Members" in text_hd     # v3.15: the slot the plugin binds it to
          and "> [zorg-core · v0.2 · станом на 2026-10-20 · слот team.members — склад команди: люди, ролі, контакти]\n#### Members" in text_hd and "Bea Two" in text_hd
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
          and "Відсутнє: Members (шукав: Members, Team Members, Склад команди, Учасники у Team: Beta (B); блоків із цим слотом немає)"
          in text, (text[-400:], res["missing"]))

with tempfile.TemporaryDirectory() as d:
    e = Env(d, edit=("#### Members\n", "#### Team Members\n"))
    text, res = e.view("task-creator", product="Zorg App")
    check("Team Members answers Members", "#### Team Members" in text and "Alex One" in text
          and "Members (Team: Alpha (A))" not in res["missing"], (text[-700:], res["missing"]))

TEAM_MEMBERS = ("- **Jira Team ID:** <team-uuid>\n", "- **Jira Team ID:** <team-uuid>\n\n#### Team Members\n\n| Name | Role |\n|---|---|\n| Own Person | PM |\n")
with tempfile.TemporaryDirectory() as d:
    e = Env(d, "context", fix=REPOS_FIX, edits=[TEAM_MEMBERS])
    block_state(e, "zorg-core", {"team": "0.2"})
    text, res = e.view("hiring-designer")        # v3.15: no registration, no plugin binding — with them, both halves (below)
    check("your own Team Members wins over the block's Members", "Own Person" in text and "#### Team Members" in text
          and "Bea Two" not in text and "> [zorg-core" not in text
          and not any(m.startswith("Members") for m in res["missing"]), (text[-700:], res["missing"]))
with tempfile.TemporaryDirectory() as d:
    e = Env(d, "context", fix=REPOS_FIX)
    block_state(e, "zorg-core", {"team": "0.2"})
    text, res = e.view("hiring-designer", repos=REPOS)
    check("…and without it the block's Members is read as before", "> [zorg-core · v0.2 · станом на 2026-10-20 · слот team.members — склад команди: люди, ролі, контакти]\n#### Members" in text
          and not any(m.startswith("Members") for m in res["missing"]), (text[-700:], res["missing"]))

# --- v3.15.0: ctx read resolves slots — both halves of a list, one line for the rest, no duplicates, where it looked
MEMBERS_SHOWN = "> [блок team › Members (registry `Core/People/`, field `team`; ◌ — registry stub) — у слоті team.members вище]"
RANKED = [{"id": "zorg-core", "namespace": "zorg-core", "rank": 1000, "products": []},
          {"id": "zorg-growth", "namespace": "zorg-growth", "rank": 500, "products": []}]
TIED = [dict(RANKED[0]), dict(RANKED[1], rank=1000)]
TEAM_TAG = " · слот team.members — склад команди: люди, ролі, контакти"
FIXTURE_TEXT = read(REPOS_FIX, "context.md")
TEAM_REGION = FIXTURE_TEXT[FIXTURE_TEXT.index("<!-- zorg-core:begin id=team "):
                           FIXTURE_TEXT.index("<!-- zorg-core:end id=team -->") + len("<!-- zorg-core:end id=team -->")]
MOVE_TEAM = [(TEAM_REGION + "\n", ""),                   # the team block in a custom record, as on the recon store
             ("<!-- zorg-core:end id=teams -->\n", "<!-- zorg-core:end id=teams -->\n\n" + TEAM_REGION + "\n")]
KEY = "- **Jira Project Key:** PROJ\n"
KEYS_BLOCK = (KEY, KEY + "\n<!-- zorg-core:begin id=keys v=0.1 -->\n- **jira_project_key:** CORE\n<!-- zorg-core:end id=keys -->\n")
RULE_REGION = ("<!-- zorg-core:begin id=metrics v=0.3 policy=rule slot=product.key_metrics -->\n#### Key Metrics\n"
               "- Core: GMV per month\n<!-- zorg-core:end id=metrics -->")
RULE_BLOCK = (KEY, KEY + "\n#### Key Metrics\n- Mine: weekly active shoppers\n\n" + RULE_REGION + "\n")
CORE_METRICS = (KEY, KEY + "\n<!-- zorg-core:begin id=metrics v=0.3 -->\n#### Key Metrics\n- Core: GMV per month\n"
                "<!-- zorg-core:end id=metrics -->\n")
BY_NAME = ("#### Growth metrics", "#### Key Metrics (growth)")


def remember(env, *bindings):
    """Your bindings (ctx slot bind) in the store's slots memory."""
    mem = sl.empty_memory()
    for b in bindings:
        sl.add_binding(mem, *b)
    with cs.guard_roots(co.allowed_roots(env.home, env.text)):
        sl.save_memory(env.store, mem)


with tempfile.TemporaryDirectory() as d:
    e = Env(d, "context", fix=REPOS_FIX, edits=[TEAM_MEMBERS])
    block_state(e, "zorg-core", {"team": "0.2"})
    text, res = e.view("task-creator", repos=RANKED)
    check("task-creator gets both halves of team.members, each with its source", "> [твоє · team.alpha-a]" in text
          and "> [zorg-core · v0.2 · станом на 2026-10-20 · слот team.members — " in text
          and text.index("Own Person") < text.index("Bea Two") and not any(m.startswith("Members") for m in res["missing"]),
          (text[-1600:], res["missing"]))
    check("…res slots names the sources of each slot", res.get("slots", {}).get("team.members") == {"shown": ["mine", "zorg-core"],
          "also": [], "diverges": []}, res.get("slots"))
    check("…a lone text of yours has no origin line, as in v3.14.1", "> [твоє · product.zorg-app]" not in text
          and "\n- **Jira Team ID:** <team-uuid>" in text, text[-1600:])

with tempfile.TemporaryDirectory() as d:
    e = Env(d, "context", fix=REPOS_FIX, edits=MOVE_TEAM)
    block_state(e, "zorg-core", {"scope": "0.4", "teams": "0.4", "team": "0.2"})
    read_by(e, "Zorg Core Notes", "all")
    for skill in ("hiring-designer", "task-creator"):
        text, res = e.view(skill, repos=RANKED)
        notes = text[text.index("## Zorg Core Notes"):]
        check("%s: a bound block's subsection shown in a slot is not repeated in a read_by record — only that subsection "
              "is replaced (fix round 1)" % skill, text.count("Bea Two") == 1 and text.count("Members' Jira accountIds") == 1
              and text.index("Bea Two") < text.index("## Zorg Core Notes") and MEMBERS_SHOWN in notes
              and "> [zorg-core · v0.2 · станом на 2026-10-20%s]\n#### Members" % TEAM_TAG in text, text[-1800:])
        check("…the rest of that block stays, under its own provenance line, and so does the rest of the record",
              "Team card (source of truth)" in notes and "jira_write_scope" in notes and "Team missions" in notes
              and "> [zorg-core · v0.2 · станом на 2026-10-20%s]\n<!-- zorg-core:begin id=team " % TEAM_TAG in notes
              and "> [zorg-core · v0.4 · станом на 2026-10-20]\n<!-- zorg-core:begin id=scope" in notes
              and "> [блок team — у слоті" not in text, notes[:1500])
    other, _ = e.view("product-analysis", repos=RANKED)
    check("a skill that does not ask the slot still gets the record whole, with the slot tag", "Bea Two" in other
          and "· слот team.members — " in other and "у слоті" not in other
          and "> [zorg-core · v0.2 · станом на 2026-10-20%s]\n<!-- zorg-core:begin id=team " % TEAM_TAG in other, other[-1800:])

with tempfile.TemporaryDirectory() as d:          # fix round 1: no-duplicates replaces exactly what the slot used
    e = Env(d, "context", fix=REPOS_FIX, edits=MOVE_TEAM)
    block_state(e, "zorg-core", {"scope": "0.4", "teams": "0.4", "team": "0.2"})
    read_by(e, "Zorg Core Notes", "all")
    remember(e, ("zorg-core", "team", None, "team.members", None))
    text, _ = e.view("hiring-designer", repos=RANKED)
    notes = text[text.index("## Zorg Core Notes"):]
    check("a whole-region binding: the whole region is one line in the read_by record", "> [блок team — у слоті team.members вище]" in notes
          and text.count("Team card (source of truth)") == 1 and text.count("Bea Two") == 1 and "<!-- zorg-core:begin id=team " not in notes
          and "Team card (source of truth)" not in notes, notes[:1200])

KEYS_NOTES = ("<!-- zorg-core:end id=teams -->\n", "<!-- zorg-core:end id=teams -->\n\n<!-- zorg-core:begin id=keys v=0.1 -->\n"
              "- **jira_project_key:** CORE\n<!-- zorg-core:end id=keys -->\n")
SUB_METRICS = ("<!-- zorg-core:end id=teams -->\n", "<!-- zorg-core:end id=teams -->\n\n<!-- zorg-core:begin id=metrics v=0.3 -->\n"
               "### Core metrics\n- **Owner:** Core team\n\n#### Key Metrics\n- Core: GMV per month\n\n#### Targets\n- Target: 10%\n"
               "<!-- zorg-core:end id=metrics -->\n")
MINE_METRICS = (KEY, KEY + "\n#### Key Metrics\n- Mine: weekly active shoppers\n")
with tempfile.TemporaryDirectory() as d:
    e = Env(d, "context", fix=REPOS_FIX, edits=[KEYS_NOTES])
    block_state(e, "zorg-core", {"keys": "0.1"})
    read_by(e, "Zorg Core Notes", "all")
    remember(e, ("zorg-core", "keys", None, "product.jira_key", None))
    text, _ = e.view("requirements-creator", repos=RANKED)
    notes = text[text.index("## Zorg Core Notes"):]
    check("a value slot's block (here a «також») removes nothing: the block stays whole in the read_by record",
          "також: zorg-core каже інакше — ctx explain product.jira_key" in text and "- **jira_project_key:** CORE" in notes
          and "<!-- zorg-core:begin id=keys " in notes and "у слоті" not in text, notes[:1200])
    e2 = Env(os.path.join(d, "m"), "context", fix=REPOS_FIX, edits=[MINE_METRICS, SUB_METRICS])
    block_state(e2, "zorg-core", {"metrics": "0.3"})
    read_by(e2, "Zorg Core Notes", "all")
    remember(e2, ("zorg-core", "metrics", "Key Metrics", "product.key_metrics", None))
    text, _ = e2.view("product-analysis", repos=RANKED)
    notes = text[text.index("## Zorg Core Notes"):]
    check("a bound block shown only as a «також» line: its subsection is replaced in the read_by record, the rest stays",
          "також: zorg-core каже інакше — ctx explain product.key_metrics" in text and "- Mine: weekly active shoppers" in text
          and "> [блок metrics › Key Metrics — у слоті product.key_metrics вище]" in notes and "- **Owner:** Core team" in notes
          and "GMV per month" not in text and "<!-- zorg-core:begin id=metrics " in notes, notes[:1200])
    check("…the subsection runs to the next heading of its level: what follows stays, its blank line too",
          "> [блок metrics › Key Metrics — у слоті product.key_metrics вище]\n\n#### Targets\n- Target: 10%\n<!-- zorg-core:end id=metrics -->"
          in notes, notes[:1200])

with tempfile.TemporaryDirectory() as d:
    e = Env(d, "context", fix=REPOS_FIX)
    block_state(e, "zorg-core", {"team": "0.2"})
    text, _ = e.view("context-navigator", repos=RANKED)
    check("a binding that yields no text names no slot on any provenance line (zorg-growth's team block has no Members)",
          "> [zorg-growth · v0.1]\n<!-- zorg-growth:begin id=team" in text
          and not any(l.startswith("> [zorg-growth") and "слот" in l for l in text.splitlines())
          and "> [zorg-core · v0.2 · станом на 2026-10-20%s]\n<!-- zorg-core:begin id=team " % TEAM_TAG in text, text[-1500:])

ROSTER = ("\n## Zorg Roster\n\n<!-- zorg-core:begin id=roster v=0.1 -->\n#### Members\n\n| Name |\n|---|\n| Cy Three |\n"
          "<!-- zorg-core:end id=roster -->\n")
with tempfile.TemporaryDirectory() as d:
    e = Env(d, extra=ROSTER)
    remember(e, ("zorg-core", "roster", None, "team.members", None))
    text, res = e.view("hiring-designer", product="Zorg App", repos=RANKED)
    check("a missing slot with an unplaced bound block says so, not «блоків немає»",
          "Members (шукав: Members, Team Members, Склад команди, Учасники у Team: Beta (B); є нерозміщений блок — ctx explain team.members)"
          in text and "Cy Three" not in text and "Members (Team: Beta (B))" in res["missing"], text[-700:])

with tempfile.TemporaryDirectory() as d:
    e = Env(d, "context", fix=REPOS_FIX, edits=[KEYS_BLOCK])
    block_state(e, "zorg-core", {"keys": "0.1"})
    remember(e, ("zorg-core", "keys", None, "product.jira_key", None))
    t, res = e.view("requirements-creator", repos=RANKED)
    check("one value: the winner, and one line for the rest", "також: zorg-core каже інакше — ctx explain product.jira_key" in t
          and "> [твоє · product.zorg-app]\n- **Jira Project Key:** PROJ\nтакож: zorg-core" in t and "CORE" not in t
          and res.get("slots", {}).get("product.jira_key") == {"shown": ["mine"], "also": ["zorg-core"], "diverges": []}, (t[-1400:], res.get("slots")))
    e.edit(os.path.join(e.store.records_dir, "product.zorg-app.md"), "- **jira_project_key:** CORE", "- **jira_project_key:** PROJ")
    t, res = e.view("requirements-creator", repos=RANKED)
    check("…the same value under another label is no «також»: your text alone, as in v3.14.1", "також:" not in t
          and "> [твоє" not in t and "\n- **Jira Project Key:** PROJ\n" in t, t[-1400:])

with tempfile.TemporaryDirectory() as d:
    e = Env(d, "context", fix=REPOS_FIX, edits=[RULE_BLOCK])
    block_state(e, "zorg-core", {"metrics": "0.3"}, bases={"metrics": RULE_REGION})
    t, res = e.view("product-analysis", repos=RANKED)
    check("a rule wins and your text follows it as a note", "правило ядра" in t and "твоя примітка до правила" in t
          and t.index("правило ядра") < t.index("твоя примітка до правила")
          and t.index("- Core: GMV per month") < t.index("твоя примітка до правила") < t.index("- Mine: weekly active shoppers")
          and "> [zorg-core · v0.3 · станом на 2026-10-20 · слот product.key_metrics — ключові метрики продукту: що міряємо і яка ціль"
              " · правило ядра]\n#### Key Metrics\n- Core: GMV per month" in t
          and "твоя примітка до правила\n> [твоє · product.zorg-app]\n#### Key Metrics\n- Mine: weekly active shoppers" in t, t[-1400:])

with tempfile.TemporaryDirectory() as d:
    e = Env(d, "context", fix=REPOS_FIX, edits=[CORE_METRICS])
    block_state(e, "zorg-core", {"metrics": "0.3"})
    remember(e, ("zorg-core", "metrics", None, "product.key_metrics", None),
             ("zorg-growth", "growth-metrics", None, "product.key_metrics", None))
    t, res = e.view("product-analysis", repos=TIED)
    check("a divergence shows both and the way to decide", "⚠ розбіжність між репозиторіями — вирішити: ctx slot decide product.key_metrics zorg-core" in t
          and t.count("⚠ розбіжність") == 1 and "- Core: GMV per month" in t and "weekly active shoppers" in t
          and res.get("slots", {}).get("product.key_metrics", {}).get("diverges") == ["zorg-core", "zorg-growth"], (t[-1400:], res.get("slots")))
    t, res = e.view("product-analysis", repos=RANKED)
    check("…a higher rank wins quietly, the other is one line", "розбіжність" not in t and "- Core: GMV per month" in t
          and "weekly active shoppers" not in t and "також: zorg-growth каже інакше — ctx explain product.key_metrics" in t, t[-1400:])

with tempfile.TemporaryDirectory() as d:
    e = Env(d)
    text, res = e.view("hiring-designer", product="Zorg App")
    check("a missing slot says where it looked", "Members (шукав: Members, Team Members, Склад команди, Учасники у Team: Beta (B); "
          "блоків із цим слотом немає)" in text and "Members (Team: Beta (B))" in res["missing"], (text[-500:], res["missing"]))
    e2 = Env(os.path.join(d, "x"), edit=("- **Jira Project Key:** PROJ\n", ""))
    text, res = e2.view("requirements-creator", product="Zorg App")
    check("…an obligatory one says so before where it looked", "Jira Project Key (обов'язкове) (шукав: Jira Project Key, "
          "jira_project_key у Product: Zorg App; блоків із цим слотом немає)" in text and "Jira Project Key" in res["missing"], text[-500:])

with tempfile.TemporaryDirectory() as d:
    e = Env(d, "context", fix=REPOS_FIX)
    block_state(e, "zorg-core", {"team": "0.2"})
    os.makedirs(e.store.state_dir, exist_ok=True)
    open(os.path.join(e.store.state_dir, "slots.json"), "w", encoding="utf-8").write("{ not json")
    t, res = e.view("task-creator", repos=RANKED)
    check("an unreadable memory is one line, the read goes on", "пам'ять слотів не прочитано" in t and res["records"]
          and "— прив'язки й рішення не застосовано" in t and t.count("пам'ять слотів") == 1 and "Bea Two" in t, t[-900:])

with tempfile.TemporaryDirectory() as d:
    e = Env(d, "context", fix=REPOS_FIX, edits=[("| Bea Two ◌ | Data analyst |", "| Bea Two ◌ | Data scientist |")])
    block_state(e, "zorg-core", {"team": "0.2"}, bases={"team": TEAM_REGION})
    t_edit, _ = e.view("hiring-designer", repos=RANKED)
    e2 = Env(os.path.join(d, "n"), "context", fix=REPOS_FIX, edits=[BY_NAME])
    t_name, _ = e2.view("product-analysis", repos=RANKED)
    check("origin marks: your edits inside a block, found by name", "· з твоїми правками" in t_edit and "· за назвою, без прив'язки" in t_name
          and "> [zorg-core · v0.2 · станом на 2026-10-20%s · з твоїми правками]\n#### Members" % TEAM_TAG in t_edit
          and "> [zorg-growth · v0.1 · за назвою, без прив'язки]\n#### Key Metrics (growth)" in t_name, (t_edit[-900:], t_name[-900:]))
    e3 = Env(os.path.join(d, "s"), "context", fix=REPOS_FIX)
    os.makedirs(os.path.join(e3.store.state_dir, "blocks"), exist_ok=True)
    open(os.path.join(e3.store.state_dir, "blocks", "zorg-core.json"), "w", encoding="utf-8").write("{ not json")
    t_state, res = e3.view("task-creator", repos=RANKED)
    check("an unreadable block state is one line, its marker attributes unknown", "стан блоків zorg-core не прочитано" in t_state
          and t_state.count("стан блоків") == 1 and "Bea Two" in t_state, t_state[-900:])
    t_reg, _ = e2.view("product-analysis", repos=RANKED[:1], skipped=[("/zorg/providers/zorg-growth.yaml", "not available locally")])
    check("an unread registration is one line naming its file, its candidates shown without the cascade",
          "реєстрацію /zorg/providers/zorg-growth.yaml не прочитано — ранги й правила її блоків невідомі; кандидати з неї показано без каскаду"
          in t_reg and "#### Key Metrics (growth)" in t_reg, t_reg[-900:])
    t_all, _ = e2.view("product-analysis", repos=RANKED, skipped=[("/zorg/providers/zorg-old.yaml", "no id")])
    t_none, _ = e2.view("product-analysis", repos=RANKED[:1])
    check("…and no line when every namespace in the records is registered, or nothing was skipped",
          "реєстрацію" not in t_all and "реєстрацію" not in t_none, (t_all[-500:], t_none[-500:]))


with tempfile.TemporaryDirectory() as d:          # ruling: the lookup mode follows the manifest key, as v3.14.1's _parts did
    e = Env(d, "context", fix=REPOS_FIX, edits=[(KEY, KEY + "- **Key Metrics:** inline line\n")])
    text, res = e.view("product-analysis", repos=RANKED)
    check("a `sections` name is a subsection only: a field line of that name does not answer it", "inline line" not in text
          and "Key Metrics" in res["missing"], (text[-500:], res["missing"]))
    text, res = e.view("lead-skill", repos=RANKED, manifest={"schema": "context-manifest/1",
                                                             "skills": {"lead-skill": {"product": {"fields": ["Key Metrics"]}}}})
    check("…and a `fields` name takes the field line first", "- **Key Metrics:** inline line" in text and res["missing"] == [], text[-500:])


def tree_of(*roots):
    """Every directory and file under `roots`, a file with its size and modification time: a created empty directory counts."""
    out = {}
    for root in roots:
        for d, _, files in os.walk(root):
            out[d] = "dir"
            for f in files:
                st = os.stat(os.path.join(d, f))
                out[os.path.join(d, f)] = (st.st_size, st.st_mtime_ns)
    return out


with tempfile.TemporaryDirectory() as d:
    e = Env(d, "context", fix=REPOS_FIX, edits=[TEAM_MEMBERS, KEYS_BLOCK])
    block_state(e, "zorg-core", {"team": "0.2", "keys": "0.1"}, bases={"team": TEAM_REGION})
    remember(e, ("zorg-core", "keys", None, "product.jira_key", None))
    before = tree_of(e.home, e.vault)
    texts = [e.view(s, repos=RANKED, skipped=[("/zorg/providers/zorg-old.yaml", "no id")])[0] for s in ("task-creator", "hiring-designer")]
    check("ctx read writes nothing — store, memory, block states, copies (criterion 6)", tree_of(e.home, e.vault) == before
          and all("Own Person" in t for t in texts), "")
    shipped, sl.CATALOGUE_PATH = sl.CATALOGUE_PATH, os.path.join(d, "gone.yaml")
    try:
        text, res = e.view("hiring-designer", repos=RANKED)
    finally:
        sl.CATALOGUE_PATH = shipped
    check("a catalogue that cannot be read: every name is read as in v3.14.1, the read goes on", "> [твоє" not in text
          and "Bea Two" not in text and "Own Person" in text and res["slots"] == {} and "слот team.members" not in text, text[-700:])

# --- v3.15.0 final review: a bound block that gives a slot nothing answers by name; a whole region with a blank line after its
# begin marker; a required field of a record read whole; one read budget, each block state and base read once
import ctx_resolve as rv  # noqa: E402

with tempfile.TemporaryDirectory() as d:
    e = Env(d, "context", fix=REPOS_FIX, edits=[("#### Members (registry", "#### Team Members (registry")])
    block_state(e, "zorg-core", {"team": "0.2"})
    text, res = e.view("task-creator", repos=RANKED)
    body = next(r for r in e.store.load() if r["id"] == "team.alpha-a")["body"]
    check("final review: the plugin-bound team block whose heading reads `Team Members` answers by name, as v3.14.1 found it — "
          "the members are there and the false «блоків із цим слотом немає» is gone",
          "> [zorg-core · v0.2 · станом на 2026-10-20 · за назвою, без прив'язки]\n#### Team Members (registry" in text
          and cr._lookup(body, "Members", field=False)[0].rstrip("\n") in text and text.count("Bea Two") == 1
          and "Members (шукав" not in text and not any(m.startswith("Members") for m in res["missing"])
          and res["slots"].get("team.members") == {"shown": ["zorg-core"], "also": [], "diverges": []}, (text[-1500:], res["missing"]))

SCOPE_BLANK = ("<!-- zorg-core:begin id=scope v=0.4 -->\n### Scope of work\nThe user works on Zorg App only.\n",
               "<!-- zorg-core:begin id=scope v=0.4 -->\n\n### Scope of work\nThe user works on Zorg App only.\n\n### Out of scope\nZorg Lite.\n")
SCOPE_SKILL = {"schema": "context-manifest/1", "skills": {"lead-skill": {"product": {"sections": ["Scope of work"]}}}}
with tempfile.TemporaryDirectory() as d:
    e = Env(d, "context", fix=REPOS_FIX, edits=[SCOPE_BLANK])
    block_state(e, "zorg-core", {"scope": "0.4"})
    read_by(e, "Zorg Core Notes", "all")
    remember(e, ("zorg-core", "scope", None, "product.scope", None))
    text, res = e.view("lead-skill", repos=RANKED, manifest=SCOPE_SKILL)
    view, notes = text[text.index("## Product: Zorg App"):], text[text.index("## Zorg Core Notes"):]     # the card above quotes the record
    check("final review: a whole region with a blank line after its begin marker, shown in its slot, is the one line in the read_by "
          "record — its second section is not printed twice", view.count("Zorg Lite.") == 1 and view.count("The user works on Zorg App only.") == 1
          and "> [блок scope — у слоті product.scope вище]\n" in notes and "<!-- zorg-core:begin id=scope " not in notes
          and view.index("Zorg Lite.") < view.index("## Zorg Core Notes"), notes[:1200])

CONTACT = ("<!-- zorg-core:end id=teams -->\n", "<!-- zorg-core:end id=teams -->\n\n<!-- zorg-core:begin id=contact v=0.1 -->\n"
           "- **Email:** core@zorg.example\n<!-- zorg-core:end id=contact -->\n")
EMAIL_SKILL = {"schema": "context-manifest/1", "every_skill": {"records": ["profile"]},
               "skills": {"lead-skill": {"profile": {"required": ["Email"]}}}}
with tempfile.TemporaryDirectory() as d:
    e = Env(d, "context", fix=REPOS_FIX, edits=[CONTACT])
    block_state(e, "zorg-core", {"contact": "0.1"})
    remember(e, ("zorg-core", "contact", None, "profile.email", None))
    text, res = e.view("lead-skill", repos=RANKED, manifest=EMAIL_SKILL)
    check("final review: a required field of a record read whole is there only when that record has it — a block bound to the slot in "
          "another record does not make the profile's Email present, and «Відсутнє» says where the block is",
          res["missing"] == ["Email"] and "core@zorg.example" not in text
          and "Email (обов'язкове) (шукав: Email у User Profile; є блок в іншому записі — ctx explain profile.email)" in text, (text[-900:], res["missing"]))
    e.edit(os.path.join(e.store.records_dir, "profile.md"), "- **Work Email:** a.one@zorg.example\n",
           "- **Work Email:** a.one@zorg.example\n- **Email:** a.one@zorg.example\n")
    text, res = e.view("lead-skill", repos=RANKED, manifest=EMAIL_SKILL)
    check("…and the profile's own Email is there", res["missing"] == [] and "Відсутнє" not in text, (text[-900:], res["missing"]))

with tempfile.TemporaryDirectory() as d:
    e = Env(d, "context", fix=REPOS_FIX, edits=[TEAM_MEMBERS, KEYS_NOTES])
    block_state(e, "zorg-core", {"team": "0.2", "keys": "0.1", "scope": "0.4", "teams": "0.4"}, bases={"team": TEAM_REGION})
    block_state(e, "zorg-growth", {"team": "0.1", "growth-metrics": "0.1"})
    remember(e, ("zorg-core", "keys", None, "product.jira_key", None))
    read_by(e, "Zorg Core Notes", "all")
    want, _ = e.view("task-creator", repos=RANKED)
    seen = {"read": [], "explain": []}
    real_state, real_base = cb.load_state, cb.get_base

    def counted(kind, real):
        def call(store, *args):
            seen[at[0]].append(((kind,) + args, cs.budget_until()))
            return real(store, *args)
        return call

    at = ["read"]
    cb.load_state, cb.get_base = counted("state", real_state), counted("base", real_base)
    try:
        got, _ = e.view("task-creator", repos=RANKED)
        at[0] = "explain"
        rv.explain(e.store, e.copies, RANKED, [], skill="task-creator", today=TODAY)
    finally:
        cb.load_state, cb.get_base = real_state, real_base
    for run, calls in sorted(seen.items()):
        what = [c for c, _ in calls]
        check("final review: %s reads the block state of each repository once and each base once (one assembly, one _Repos)" % run,
              len(what) == len(set(what)) and ("state", "zorg-core") in what and ("state", "zorg-growth") in what, what)
        budgets = [b for _, b in calls]
        check("…all of it within one read budget (cs.read_budget, as a snapshot reads)", budgets and None not in budgets
              and len(set(budgets)) == 1, budgets)
    check("…and the read prints what it printed before", got == want, "")

check("check_manifest is clean on the repo", cr.check_manifest(ROOT) == [], cr.check_manifest(ROOT))
with tempfile.TemporaryDirectory() as d:
    src = read(cr.MANIFEST_PATH)
    start = src.index("\n  decision-log:")
    end = src.index("\n  delegation-coach:")
    path = os.path.join(d, "context-manifest.yaml")
    open(path, "w", encoding="utf-8").write(src[:start] + src[end:])
    errs = cr.check_manifest(ROOT, manifest_path=path)
    check("check_manifest flags a skill without an entry", any("decision-log" in x for x in errs), errs)

# --- v3.15.0: every name the manifest reads has a slot in references/context-slots.yaml
def without_slot(src, slot_id):
    """The catalogue text with the slot `slot_id` cut out (a slot runs to the next two-space-indented key)."""
    lines, out, skip = src.split("\n"), [], False
    for line in lines:
        if line.startswith("  ") and not line.startswith("   "):
            skip = line.strip() == slot_id + ":"
        elif not line.startswith(" "):
            skip = False
        if not skip:
            out.append(line)
    return "\n".join(out)


with tempfile.TemporaryDirectory() as d:
    src = read(os.path.join(ROOT, "references", "context-slots.yaml"))
    path = os.path.join(d, "context-slots.yaml")
    open(path, "w", encoding="utf-8").write(without_slot(src, "team.members"))
    errs = cr.check_manifest(ROOT, catalogue_path=path)
    check("check_manifest flags a manifest name with no slot", any("Members" in x and "team" in x and "no slot" in x for x in errs), errs)
    check("…once per skill that reads it, naming the skill and the record", "hiring-designer: team name 'Members' has no slot in context-slots.yaml" in errs
          and "task-creator: team name 'Members' has no slot in context-slots.yaml" in errs, errs)
    check("…and nothing else is flagged", errs and all("'Members'" in x for x in errs), errs)
    for slot_id, name, skill in (("product.jira_key", "Jira Project Key", "product-reporter"),      # required
                                 ("product.description", "Description", "decision-log"),            # a field
                                 ("product.key_metrics", "Key Metrics", "write-concept"),           # a section
                                 ("profile.email", "Email", "context-connect"),                     # the profile
                                 ("team.jira_team_id", "Jira Team ID", "task-creator")):            # a team field
        open(path, "w", encoding="utf-8").write(without_slot(src, slot_id))
        errs = cr.check_manifest(ROOT, catalogue_path=path)
        check("check_manifest flags %s as having no slot" % name, any(x.startswith(skill + ":") and repr(name) in x and "no slot" in x for x in errs), errs)
    open(path, "w", encoding="utf-8").write(src.replace("kind: list", "kind: blob", 1))
    errs = cr.check_manifest(ROOT, catalogue_path=path)
    check("check_manifest carries the errors check_catalogue finds", any("kind" in x and "context-slots.yaml" in x for x in errs), errs)
    open(path, "w", encoding="utf-8").write("slots: [not, a, block]\n")
    errs = cr.check_manifest(ROOT, catalogue_path=path)
    check("check_manifest says the catalogue cannot be read", len(errs) == 1 and errs[0].startswith("context-slots.yaml:"), errs)
    errs = cr.check_manifest(ROOT, catalogue_path=os.path.join(d, "gone.yaml"))
    check("…and when it is missing", len(errs) == 1 and errs[0].startswith("context-slots.yaml:"), errs)
check("check_manifest reads the repo catalogue by default", cr.check_manifest(ROOT) == cr.check_manifest(ROOT, catalogue_path=os.path.join(ROOT, "references", "context-slots.yaml")), "")

print("RESULT:", "GREEN ✅" if not fails else "RED ❌", "(%d failed)" % fails)
sys.exit(1 if fails else 0)
