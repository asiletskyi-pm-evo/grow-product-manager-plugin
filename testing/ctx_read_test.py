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
