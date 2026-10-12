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
import ctx_ops as co  # noqa: E402
import ctx_read as cr  # noqa: E402
import ctx_store as cs  # noqa: E402

FIX = os.path.join(ROOT, "testing", "fixtures", "ctx")
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

    def __init__(self, d, fixture="typical", extra="", edit=None):
        self.home = os.path.join(d, "home")
        self.vault = os.path.join(d, "vault")
        os.makedirs(os.path.join(self.home, ".grow-pm"))
        os.makedirs(os.path.join(self.vault, "Notes", "_System"))
        self.text = read(FIX, fixture + ".md").replace("{{VAULT}}", self.vault) + extra
        if edit:
            assert edit[0] in self.text, edit[0]
            self.text = self.text.replace(edit[0], edit[1], 1)
        self.ctx = os.path.join(self.home, ".grow-pm", "local-context.md")
        for p in (self.ctx, os.path.join(self.vault, "Notes", "_System", "local-context.md")):
            open(p, "w", encoding="utf-8", newline="").write(self.text)
        self.copies = co.copies_for(self.ctx, self.text, home=self.home)
        self.store = cs.Store(co.store_root_for(self.text, home=self.home))
        co.migrate(self.ctx, self.store.root, self.copies, self.home, apply=True, now=NOW)

    def view(self, skill, product=None, today=TODAY):
        return cr.read_view(self.store, self.copies, skill, product=product, today=today)

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
