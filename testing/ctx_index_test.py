#!/usr/bin/env python3
"""TC-ctx-3160-index — scripts/ctx_index.py, the section index of the search, and `ctx index` (since v3.16.0).

The fictional Zorg vault of testing/fixtures/search/ (the plugin folder Notes/ and the core ZorgCore/, registered as
zorg-core in Notes/_System/providers/) is copied to a temp dir: what is indexed and what is not, sections, metadata,
version keys, the incremental refresh (a changed file, a removed one, the time budget and its queue, the lock, a broken
index, a file iCloud has not downloaded, an NFD file name), `ctx index status|rebuild`, and that nothing but
<home>/.grow-pm/index/ is ever written. Stdlib only; run from the repo root:

  env -u GROW_PM_CONTEXT_PATH -u GROW_PM_PROVIDER_PATHS python3 testing/ctx_index_test.py
"""
import json, os, shutil, sqlite3, subprocess, sys, tempfile, time, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import ctx_common as cc  # noqa: E402
import ctx_index  # noqa: E402
import ctx_ops as co  # noqa: E402
import ctx_repos as crp  # noqa: E402
import ctx_stem  # noqa: E402

CTX = os.path.join(ROOT, "scripts", "ctx.py")
FIX = os.path.join(ROOT, "testing", "fixtures", "search")
fails = 0


def check(name, cond, detail=""):
    global fails
    fails += not cond
    print(("✅" if cond else "❌"), name, ("" if cond else "-> " + str(detail)[:700]))


def read(*parts):
    return open(os.path.join(*parts), encoding="utf-8", newline="").read()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8", newline="").write(text)


def tree(top):
    """{relative path: (size, mtime)} of every file under `top`."""
    out = {}
    for dirpath, _, names in os.walk(top):
        for n in names:
            p = os.path.join(dirpath, n)
            st = os.stat(p)
            out[os.path.relpath(p, top)] = (st.st_size, st.st_mtime)
    return out


class Env:
    """A temp home (home/.grow-pm) and a temp vault: the fixture vault copied, {{VAULT}} and {{HOME}} filled in."""

    def __init__(self, d, fixture="context"):
        self.home = os.path.join(d, "home")
        self.vault = os.path.join(d, "vault")
        os.makedirs(os.path.join(self.home, ".grow-pm"))
        shutil.copytree(os.path.join(FIX, "vault"), self.vault)
        for dirpath, _, names in os.walk(self.vault):
            for n in names:
                p = os.path.join(dirpath, n)
                if n.endswith(".yaml") and "{{VAULT}}" in read(p):
                    write(p, read(p).replace("{{VAULT}}", self.vault))
        self.text = read(FIX, fixture + ".md").replace("{{VAULT}}", self.vault).replace("{{HOME}}", self.home)
        self.ctx = os.path.join(self.home, ".grow-pm", "local-context.md")
        self.mirror = os.path.join(self.vault, "Notes", "_System", "local-context.md")
        self.store = os.path.join(self.vault, "Notes", "_System", "context")
        write(self.ctx, self.text)
        write(self.mirror, self.text)
        self.index = os.path.join(self.home, ".grow-pm", "index")

    def run(self, *args):
        env = dict(os.environ)
        env.pop("GROW_PM_CONTEXT_PATH", None)
        p = subprocess.run([sys.executable, CTX] + list(args) + ["--home", self.home, "--context", self.ctx],
                           capture_output=True, text=True, env=env, timeout=120)
        lines = [l for l in p.stdout.splitlines() if l.strip()]
        try:
            result = json.loads(lines[-1][len("CTX_RESULT "):]) if lines and lines[-1].startswith("CTX_RESULT ") else None
        except ValueError:
            result = None
        return p.returncode, p.stdout + p.stderr, result

    def scope(self):
        """(roots, store_rel, blocks_rels) as `ctx index` builds them."""
        repos = crp.load_repos(self.text, self.home)
        roots = ctx_index.scope(self.text, repos)
        vaults = [v for v, _ in cc.vault_entries(self.text)]
        store_rel = ctx_index.rel_path(co.store_root_for(self.text, self.home), vaults)
        by = {r["source"]: r for r in roots}
        blocks = [ctx_index.rel_path(os.path.join(by[r["id"]]["path"], r["blocks_file"]), vaults, by[r["id"]])
                  for r in repos if r["id"] in by and r["blocks_file"]]
        return roots, store_rel, blocks

    def note(self, rel):
        return os.path.join(self.vault, *rel.split("/"))


INDEXED = {
    "Notes/Broken frontmatter.md", "Notes/Checkout flow (old).md", "Notes/Epics/Epic — PROJ-77.md", "Notes/Inbox.md",
    "Notes/Knowledge/Delivery slots (900100200).md", "Notes/Meetings/Pricing review 2026-09-30.md",
    "Notes/Meetings/Standup 2026-10-01.md", "Notes/Meetings/Standup 2026-10-08.md", "Notes/Mobile cart notes.md",
    "Notes/Roadmap Q4 — draft v2.md", "Notes/Roadmap Q4 — draft v3.md", "Notes/Tasks/ZORG-1234.2 checkout timeout.md",
    "Notes/Zorg Style Guide.md", "Notes/Кошик — графік роботи продавця.md", "Notes/Корзина 2.0 (mobile).md",
    "ZorgCore/Epics/Epic — PROJ-77.md", "ZorgCore/Pages/Delivery slots (900100200).md", "ZorgCore/People/bea-two.md",
    "ZorgCore/Teams/team-alpha.md",
}


def q(text):
    """An FTS5 expression for a question, as the search builds it."""
    return ctx_stem.fts_or(ctx_stem.query_terms(text))


# ------------------------------------------------------------------ the pure functions
check("schema, budget and size limit are the spec's", (ctx_index.SCHEMA, ctx_index.REFRESH_S, ctx_index.MAX_BYTES)
      == ("search-index/1", 30.0, 2_000_000))
check("the index folder is <home>/.grow-pm/index", ctx_index.index_dir("/h") == os.path.join("/h", ".grow-pm", "index"))

check("sections stop at level 3", [h for h, _ in ctx_index.split_sections("# A\nx\n## B\ny\n#### C\nz\n")] == ["A", "A › B"])
check("…and a level-4 heading stays in the body", ctx_index.split_sections("# A\nx\n## B\ny\n#### C\nz\n")[1][1].startswith("y\n#### C"))
check("a note without headings is one section", ctx_index.split_sections("plain\ntext\n") == [("", "plain\ntext")],
      ctx_index.split_sections("plain\ntext\n"))
check("the frontmatter is cut", ctx_index.split_sections("---\ntype: x\n---\n# A\nbody\n") == [("A", "body")],
      ctx_index.split_sections("---\ntype: x\n---\n# A\nbody\n"))
check("a heading path skips a missing level", [h for h, _ in ctx_index.split_sections("## B\nb\n# A\na\n### C\nc\n")]
      == ["B", "A", "A › C"], ctx_index.split_sections("## B\nb\n# A\na\n### C\nc\n"))
check("a # inside a code fence is no heading", [h for h, _ in ctx_index.split_sections("# A\n```\n# not\n```\nx\n")] == ["A"])
LONG_INTRO = ("An introduction long enough to stand alone. " * 6).strip()
check("text before the first heading is its own section", ctx_index.split_sections(LONG_INTRO + "\n# A\nx\n")
      == [("", LONG_INTRO), ("A", "x")], ctx_index.split_sections(LONG_INTRO + "\n# A\nx\n"))

# A1 (fix round 2, Q1): a breadcrumb or a short preamble before the first heading stays a section of its own — on a
# mirror page that short row carries the title and ranks on it; `ctx search --get` of it and its snippet go on with the
# sections after it (ctx_search_test). link_only / strip_links tell a breadcrumb line for near_key and that fill.
CRUMB = "↑ [[Delivery (900100100)|Delivery]]  ·  `Zorg / Delivery / Slots`"
check("link_only: a breadcrumb, a line of links, an embed, a backticked path, a line of separators",
      all(ctx_index.link_only(x) for x in (CRUMB, "[[A]] · [[B|b]]", "![[diagram.png]]", "![](att/x.png)",
                                           "`Zorg / Delivery`", "---", "[Doc](https://x.test/a) | [[B]]")), CRUMB)
check("…not a line with words of its own, nor an empty one; a `Label:` before the links only with label=True",
      not any(ctx_index.link_only(x) for x in ("See [[A]] for the rules", "Owner: [[Bea Two]]", "plain words", ""))
      and ctx_index.link_only("Up:: [[Zorg MOC]]", label=True) and ctx_index.link_only("**MOC:** [[Research]]", label=True)
      and not ctx_index.link_only("See [[A]] for the rules", label=True))
check("R6: a backticked span is a breadcrumb only when it is a path — `a/b/c.md`, or `Space / Parent / Page`",
      ctx_index.link_only("`docs/zorg/slots.md`") and ctx_index.link_only("`Zorg / Delivery / Slots`")
      and not ctx_index.link_only("`npm install zorg`") and not ctx_index.link_only("`zorg`")
      and not ctx_index.link_only("`a / b` and `npm i`"))
check("R6: …strip_links keeps a code span and drops a backticked path",
      ctx_index.strip_links("`npm install zorg`\n`Zorg / Delivery / Slots`\nrun it") == "`npm install zorg`\nrun it")
check("Q1: a short preamble is its own section", ctx_index.split_sections("intro\n# A\nx\n")
      == [("", "intro"), ("A", "x")], ctx_index.split_sections("intro\n# A\nx\n"))
check("Q1: …and so is a breadcrumb alone, or a breadcrumb and a line", ctx_index.split_sections(CRUMB + "\n\n# Slots\n\nThe slots.\n")
      == [("", CRUMB), ("Slots", "The slots.")]
      and ctx_index.split_sections("---\ntype: page\n---\n" + CRUMB + "\nDraft of the team.\n# Slots\n\nThe slots.\n")
      == [("", CRUMB + "\nDraft of the team."), ("Slots", "The slots.")],
      ctx_index.split_sections(CRUMB + "\n\n# Slots\n\nThe slots.\n"))
check("Q1: …a code span alone too; an empty first heading is left out as before",
      ctx_index.split_sections("`npm install zorg`\n# Setup\n\nThen run it.\n") == [("", "`npm install zorg`"), ("Setup", "Then run it.")]
      and ctx_index.split_sections("intro\n# A\n## B\ny\n") == [("", "intro"), ("A › B", "y")],
      ctx_index.split_sections("intro\n# A\n## B\ny\n"))

check("a draft mark makes a version key, a date series does not",
      ctx_index.version_key("Roadmap Q4 — draft v2", "Notes") == ctx_index.version_key("Roadmap Q4 — draft v3", "Notes")
      and ctx_index.version_key("Roadmap Q4 — draft v2", "Notes") is not None
      and ctx_index.version_key("Standup 2026-10-01", "Notes") is None)
check("драфт №N, rev N, ревізія N are version marks; the folder is part of the key",
      ctx_index.version_key("План — драфт №2", "Notes") == ctx_index.version_key("План — драфт №3", "Notes")
      and ctx_index.version_key("Spec rev5", "Notes") == ctx_index.version_key("Spec rev6", "Notes")
      and ctx_index.version_key("Специфікація ревізія 5", "Notes") is not None
      and ctx_index.version_key("Roadmap — draft v2", "Notes") != ctx_index.version_key("Roadmap — draft v2", "Other"))
check("…a date in a versioned title is dropped from the key, a dotted date series is no version",
      ctx_index.version_key("Plan v2 2026-10-01", "N") == ctx_index.version_key("Plan v3 2026-10-08", "N")
      and ctx_index.version_key("Замір 01.08.2026", "N") is None and ctx_index.version_key("Review", "N") is None)

m = ctx_index.note_meta("Notes/a.md", "---\ntitle: From front\n---\n# Heading\n")
check("title: the frontmatter's first", m["title"] == "From front", m)
check("…else the first # heading, else the file name", ctx_index.note_meta("Notes/a.md", "x\n# Heading\n")["title"] == "Heading"
      and ctx_index.note_meta("Notes/Some name.md", "just text")["title"] == "Some name")
m = ctx_index.note_meta("Notes/a.md", "---\ncreated: 2026-01-01\ndate: 2026-02-02\nmodified: 2026-03-03\nupdated: 2026-04-04\n---\nx")
check("date: updated before modified, date, created", m["date"] == "2026-04-04", m)
m = ctx_index.note_meta("Notes/a.md", "---\ncreated: 2026-01-01\ndate: 2026-02-02\n---\nx")
check("…date before created", m["date"] == "2026-02-02", m)
m = ctx_index.note_meta("Notes/a.md", "---\ncreated: 2026-01-01\ndate: 2026-02-02\ngenerated: 2026-03-03\nsnapshot: 2026-04-04\n---\nx")
check("…snapshot before generated, generated before date (fix round 1: the class TTL reads them)", m["date"] == "2026-04-04"
      and ctx_index.note_meta("Notes/a.md", "---\ndate: 2026-02-02\ngenerated: 2026-03-03\n---\nx")["date"] == "2026-03-03"
      and ctx_index.note_meta("Notes/a.md", "---\nsnapshot: 2026-04-04\nmodified: 2026-05-05\n---\nx")["date"] == "2026-05-05", m)
check("ttl_date (Task 6 fix round 1): the note's own updated, else snapshot, else generated — never another date",
      ctx_index.note_meta("Notes/a.md", "---\ncreated: 2026-01-01\nupdated: 2026-04-04\nsnapshot: 2026-05-05\n---\nx")["ttl_date"]
      == "2026-04-04"
      and ctx_index.note_meta("Notes/a.md", "---\ngenerated: 2026-03-03\nsnapshot: 2026-04-04\n---\nx")["ttl_date"] == "2026-04-04"
      and ctx_index.note_meta("Notes/a.md", "---\ndate: 2026-02-02\ngenerated: 2026-03-03\n---\nx")["ttl_date"] == "2026-03-03"
      and ctx_index.note_meta("Notes/a.md", "---\ncreated: 2026-01-01\ndate: 2026-02-02\nmodified: 2026-03-03\n---\nx")["ttl_date"]
      == ""
      and ctx_index.note_meta("Notes/a.md", "no frontmatter", mtime=time.time())["ttl_date"] == "")
m = ctx_index.note_meta("Notes/m.md", "---\ntype: meeting\nsensitive: true\ntags:\n- cart\n- pricing\naliases:\n- One\n---\n# M\nbody\n")
check("a YAML list at the margin (PyYAML's own style) keeps every key", m["type"] == "meeting" and m["sensitive"] is True
      and m["tags"] == ["cart", "pricing"] and m["aliases"] == ["One"], m)
check("…a margin list item after a key that has a value is still no YAML",
      ctx_index.note_meta("Notes/m.md", "---\ntype: meeting\n- stray\n---\n# M\n")["type"] in ("", None))
m = ctx_index.note_meta("Notes/a.md", "no frontmatter", mtime=time.mktime((2026, 5, 6, 12, 0, 0, 0, 0, -1)))
check("…none of them: the file's mtime", str(m["date"]).startswith("2026-05-06"), m)
check("confluence_id from the frontmatter, else (digits).md",
      ctx_index.note_meta("Notes/a.md", "---\nconfluence_id: 900100200\n---\nx")["confluence_id"] == "900100200"
      and ctx_index.note_meta("Notes/Page (1234567).md", "x")["confluence_id"] == "1234567"
      and not ctx_index.note_meta("Notes/Page (12345).md", "x")["confluence_id"])
m = ctx_index.note_meta("Notes/a.md", "---\ntags: [cart, \"seller-hours\"]\naliases:\n  - One\n  - Two\nsensitive: Yes\n---\nx")
check("tags and aliases as lists, sensitive true/yes/1 in any case", m["tags"] == ["cart", "seller-hours"]
      and m["aliases"] == ["One", "Two"] and m["sensitive"] is True, m)
check("…sensitive: no is false", ctx_index.note_meta("Notes/a.md", "---\nsensitive: no\n---\nx")["sensitive"] is False)
check("hub: a hub type, search_hub: true, or a hub word in the title",
      ctx_index.note_meta("Notes/p.md", "---\ntype: person\n---\nx")["hub"] is True
      and ctx_index.note_meta("Notes/a.md", "---\nsearch_hub: true\n---\nx")["hub"] is True
      and ctx_index.note_meta("Notes/Глосарій продукту.md", "x")["hub"] is True
      and ctx_index.note_meta("Notes/a.md", "---\ntype: concept\n---\n# Cart\n")["hub"] is False)
m = ctx_index.note_meta("Notes/h.md", "---\ncore_page: \"ZorgCore/Epics/Big Page.md\"\n---\nSee [[Other note#Part|alias]] and [[x/Third]].")
check("links: the wiki-link targets and core_page, by file name", set(m["links"]) == {"big page", "other note", "third"}, m)
m = ctx_index.note_meta("Notes/u.md", "---\ntype: x\n# Head\ntext\n")
check("a frontmatter never closed: no metadata, the text read as text", m["type"] in ("", None) and m["title"] == "Head", m)
m = ctx_index.note_meta("Notes/t.md", "---\ntitle: T\n\ttype: meeting\n---\n# Head\n")
check("a frontmatter with a tab: no metadata at all", m["title"] == "Head" and m["type"] in ("", None), m)

check("excluded: the store, _System/providers, the blocks file",
      ctx_index.excluded("Notes/_System/context/records/x.md", "Notes/_System/context", [])
      and ctx_index.excluded("Notes/_System/context/INDEX.md", "Notes/_System/context", [])
      and ctx_index.excluded("Notes/_System/providers/p.md", "Notes/_System/context", [])
      and ctx_index.excluded("ZorgCore/_System/context-blocks.md", "", ["ZorgCore/_System/context-blocks.md"]))
check("….obsidian, .trash, _backup*, not .md, local-context.md",
      all(ctx_index.excluded(p, "Notes/_System/context", []) for p in (
          "Notes/.obsidian/x.md", "Notes/a/.trash/x.md", "_backup_x/y.md", "Notes/_backup 2/y.md", "Notes/a.txt",
          "Notes/_System/local-context.md")))
check("A4: anything under a `_System/_scratch/` folder (per-person digests) is left out",
      all(ctx_index.excluded(p, "Notes/_System/context", []) for p in (
          "Notes/_System/_scratch/people_digests/bea-two.md", "ZorgCore/_System/_scratch/x.md", "_System/_scratch/y.md",
          "@zorg-ext/_System/_scratch/z.md")))
check("…and nothing else", not any(ctx_index.excluded(p, "Notes/_System/context", ["ZorgCore/_System/context-blocks.md"])
                                   for p in ("Notes/a.md", "Notes/_System/other.md", "Notes/backup/a.md",
                                             "Notes/_System/contexts/a.md", "ZorgCore/_System/x.md", "Notes/A.MD",
                                             "Notes/_scratch/a.md", "Notes/_System/scratch/a.md")))

nfd = unicodedata.normalize("NFD", "/v/Notes/Йогурт і їжа.md")
check("rel_path: from the vault's root with the top folder, NFC, /",
      ctx_index.rel_path(nfd, ["/v"]) == "Notes/Йогурт і їжа.md" and ctx_index.rel_path("/v/ZorgCore/a/b.md", ["/x", "/v"]) == "ZorgCore/a/b.md")
check("…outside every vault: @<source>/<path from the root>",
      ctx_index.rel_path("/core/zx/a/b.md", ["/v"], ctx_index.Root("zorg-x", "/core/zx", "")) == "@zorg-x/a/b.md")
check("is_dataless is false for a file on disk", ctx_index.is_dataless(os.path.abspath(__file__)) is False)

# ------------------------------------------------------------------ A5: the key of near copies
STUDY = "The cart shows the seller's working hours under each block, so a shopper knows when the order moves. " * 5
COPY_A = ("---\ntype: research\nupdated: 2026-10-01\n---\n# Cart study\n\n" + STUDY + "\n\n## Findings\n\n"
          "Shoppers wait less when they see the hours.\n\n## Повʼязане\n\n- [[Cart MOC]]\n- [[Seller hours]]\n")
COPY_B = ("# Cart study\n\nUp:: [[Research MOC]]\n2026-10-07\n\n" + STUDY + "\n\n## Findings\n\n"
          "Shoppers wait less when they see the hours.\n\nRelated:\n- [[Cart MOC]] — the map of the cart\n")


def near(text):
    return ctx_index.near_key(ctx_index.split_sections(text))


check("A5: near_key — the same text without its frontmatter, back-link and date lines and trailing «Повʼязане» / "
      "«Related» block is one key", near(COPY_A) and near(COPY_A) == near(COPY_B) and len(near(COPY_A)) == 40,
      (near(COPY_A), near(COPY_B)))
check("…a word changed is another key", near(COPY_A.replace("moves", "ships")) not in (None, near(COPY_A)))
check("…fewer than 400 characters left: no key (short notes never fold)",
      near("# Short\n\nOnly a line.\n") is None and near("# S\n\n" + "x" * 390 + "\n\n- [[A MOC]]\n2026-10-01\n") is None
      and near("# S\n\n" + "x" * 400 + "\n") is not None)
check("Q4: the headings go into the key but not into the 400 characters — long headings over a short text give no key",
      near("# " + "Heading of the cart study " * 12 + "\n\n## " + "Findings of the study " * 10 + "\n\nOnly a line.\n") is None
      and near("# H\n\n" + "x" * 400 + "\n") is not None)
check("…the first 20 000 characters count", near("# L\n\n" + "y" * 20000 + "a\n") == near("# L\n\n" + "y" * 20000 + "b\n")
      and near("# L\n\n" + "y" * 19990 + "a\n") != near("# L\n\n" + "y" * 19990 + "b\n"))
FACTS = STUDY + "\n\n"
check("R1: a labelled link line stays in the text unless its label is a navigation one — Owner A and Owner B are two notes",
      near("# Cart study\n\nOwner: [[Alex One]]\n\n" + FACTS) != near("# Cart study\n\nOwner: [[Bea Two]]\n\n" + FACTS)
      and near("# Cart study\n\nКоманда: [[Alpha]]\n\n" + FACTS) != near("# Cart study\n\n" + FACTS))
check("R1: …a navigation label (Up, MOC, Parent, Related, Back, Source, Index, Hub, Повʼязане, Зв'язки, Назад, "
      "Батьківська, Джерело) is still set aside", all(
          near("# Cart study\n\n%s [[Research MOC]]\n\n" % lab + FACTS) == near("# Cart study\n\n" + FACTS)
          for lab in ("Up::", "**MOC:**", "Parent:", "Related:", "Back:", "Source:", "Index:", "Hub:", "Пов'язане:",
                      "Повʼязані:", "Зв'язки:", "Назад:", "Батьківська:", "**Джерело:**")))
check("R2: a labelled date line stays unless its label says when the note was updated or made — Deadline A and B are two notes",
      near("# Cart study\n\nDeadline: 2026-10-07\n\n" + FACTS) != near("# Cart study\n\nDeadline: 2026-12-01\n\n" + FACTS)
      and near("# Cart study\n\nДедлайн: 01.12.2026\n\n" + FACTS) != near("# Cart study\n\n" + FACTS)
      and near("# Cart study\n\n- Launch: 2026-11-15\n\n" + FACTS) != near("# Cart study\n\n" + FACTS))
check("R2: …an update or creation date (any of the labels), or a bare date, is still set aside", all(
          near("# Cart study\n\n%s\n\n" % line + FACTS) == near("# Cart study\n\n" + FACTS)
          for line in ("Оновлено: 07.10.2026", "Оновлено: 08.10.2026", "**Updated:** 2026-10-07", "Last modified:: 2026-10-07",
                       "Created: 2026-01-02", "Дата оновлення: 2026-10-07", "Станом на 07.10.2026", "Snapshot: 2026-10-01",
                       "2026-10-07", "- 2026-10-07 10:30")))
check("R5: the headings count — copies that differ only in a heading are two notes",
      near("# Cart study\n\n" + FACTS + "## Findings\n\nShoppers wait less.\n")
      != near("# Cart study\n\n" + FACTS + "## Results\n\nShoppers wait less.\n"))
with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    write(env.note("Notes/Knowledge/sources/Cart study.md"), COPY_A)
    write(env.note("Notes/Research/Cart study.md"), COPY_B)
    idx = ctx_index.Index(env.home)
    idx.refresh(*env.scope())
    notes = {n["path"]: n for n in idx.notes()}
    check("A5: the index keeps each note's near key, from its sections",
          notes["Notes/Knowledge/sources/Cart study.md"]["near"] == notes["Notes/Research/Cart study.md"]["near"] == near(COPY_A)
          and notes["Notes/Mobile cart notes.md"]["near"] is None, {p: n.get("near") for p, n in notes.items()})

# ------------------------------------------------------------------ S2: following() stops at what the fill needs
with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    BIG = "Notes/Knowledge/Big page (900100400).md"
    write(env.note(BIG), CRUMB + "\n\n# Big page\n\n" + "".join("## Part %02d\n\n%s\n\n" % (i, "w" * 500) for i in range(40)))
    idx = ctx_index.Index(env.home)
    idx.refresh(*env.scope())
    sid = next(s_ for s_, p_, h_ in idx.headings() if p_ == BIG and h_ == "")
    sec = idx.section(sid)
    every, capped = idx.following(sec["note_id"], sec["ord"]), idx.following(sec["note_id"], sec["ord"], chars=1500)
    check("S2: following() with chars= stops once the text it gathered (link-only lines aside) holds that many",
          len(every) == 40 and len(capped) == 3 and sum(len(t) for _, t in capped) == 1500, (len(every), len(capped)))
    check("…a cap of nothing is no cap; an unknown note is none", len(idx.following(sec["note_id"], sec["ord"], chars=None)) == 40
          and idx.following(999999, 0, chars=1500) == [])

# ------------------------------------------------------------------ A4: the walk never enters _System/_scratch/
with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    write(env.note("Notes/_System/_scratch/people_digests/bea-two.md"), "---\ntype: note\n---\n# Bea Two\n\nDigest of the 1-1s.\n")
    write(env.note("ZorgCore/_System/_scratch/x.md"), "# Scratch\n\nA draft of the core.\n")
    idx = ctx_index.Index(env.home)
    idx.refresh(*env.scope())
    paths = {n["path"] for n in idx.notes()}
    check("A4: a note under <plugin folder>/_System/_scratch/ or a core's is not indexed", paths == INDEXED, sorted(paths ^ INDEXED))

# ------------------------------------------------------------------ the index over the fixture
with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    roots, store_rel, blocks_rels = env.scope()
    check("scope: own for the plugin folder, the repository id for its core folder",
          [(r["source"], r["path"], r["vault"]) for r in roots]
          == [("own", os.path.join(env.vault, "Notes"), env.vault), ("zorg-core", os.path.join(env.vault, "ZorgCore"), env.vault)],
          roots)
    check("store_rel and blocks_rels from the context", store_rel == "Notes/_System/context"
          and blocks_rels == ["ZorgCore/_System/context-blocks.md"], (store_rel, blocks_rels))
    gone = crp.load_repos(env.text, env.home) + [{"id": "zorg-gone", "core_root": os.path.join(d, "nowhere"), "paths": []}]
    check("a registration whose folder is not on disk is no root",
          [r["source"] for r in ctx_index.scope(env.text, gone)] == ["own", "zorg-core"])

    vault_before = tree(env.vault)
    idx = ctx_index.Index(env.home)
    check("an index that was never built answers nothing", idx.query(q("кошик"), 5) == [] and idx.notes() == [])
    r = idx.refresh(roots, store_rel, blocks_rels)
    paths = {n["path"] for n in idx.notes()}
    check("own layer and the core are indexed", "Notes/Roadmap Q4 — draft v3.md" in paths and any(p.startswith("ZorgCore/") for p in paths))
    check("U1 (fix round 5): Index.paths() is every note's path, NFC, sorted — what `ctx search --get <name>` looks through",
          idx.paths() == sorted(paths) and all(p == unicodedata.normalize("NFC", p) for p in idx.paths()), idx.paths()[:5])
    check("the store, blocks file, .obsidian and _backup are not", not any(
        p.startswith(("Notes/_System/context/", "_backup")) or "/_backup" in "/" + p or "/.obsidian/" in p
        or p == "ZorgCore/_System/context-blocks.md" for p in paths), sorted(paths))
    check("exactly the fixture's notes", paths == INDEXED, sorted(paths ^ INDEXED))
    check("the first refresh adds them all", r["added"] == len(INDEXED) and r["changed"] == 0 and r["removed"] == 0
          and r["pending"] == 0 and r["locked"] is False and r["rebuilt"] is False and r["skipped_dataless"] == 0, r)
    check("a refresh writes nothing to the vault", tree(env.vault) == vault_before)
    check("…and only index files in the home", sorted(os.listdir(os.path.join(env.home, ".grow-pm"))) == ["index", "local-context.md"]
          and set(os.listdir(env.index)) <= {"sections.sqlite", "index.json"}, os.listdir(env.index))
    state = json.loads(read(env.index, "index.json"))
    con = sqlite3.connect(os.path.join(env.index, "sections.sqlite"))
    n_sections = con.execute("SELECT count(*) FROM sections").fetchone()[0]
    tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master")}
    meta = dict(con.execute("SELECT key, value FROM meta").fetchall())
    con.close()
    check("index.json: schema, updated, files, sections, skipped_dataless, pending",
          {"schema", "updated", "files", "sections", "skipped_dataless", "pending"} <= set(state)
          and state["schema"] == "search-index/1" and state["files"] == len(INDEXED) and state["sections"] == n_sections
          and state["pending"] == 0 and state["updated"][:2] == "20", state)
    check("the tables and meta of search-index/1", {"notes", "sections", "sections_fts", "meta"} <= tables
          and meta.get("schema") == "search-index/1" and meta.get("updated"), (tables, meta))
    st = idx.status()
    check("status: the counts", st["schema"] == "search-index/1" and st["files"] == len(INDEXED) and st["sections"] == n_sections
          and st["pending"] == 0 and st["skipped_dataless"] == 0, st)

    notes = {n["path"]: n for n in idx.notes()}
    k = notes["Notes/Кошик — графік роботи продавця.md"]
    check("metadata of a note", k["source"] == "own" and k["title"] == "Кошик — графік роботи продавця" and k["type"] == "concept"
          and k["product"] == "Zorg App" and k["date"] == "2026-09-15" and k["tags"] == ["cart", "seller-hours"]
          and k["aliases"] == ["Графік продавця в кошику"] and k["sensitive"] is False and k["hub"] is False
          and k["hash"] and k["size"] > 0 and k["mtime"] > 0, k)
    check("the core's notes carry the repository id", notes["ZorgCore/Teams/team-alpha.md"]["source"] == "zorg-core"
          and notes["ZorgCore/Teams/team-alpha.md"]["date"] == "2026-01-01")
    check("ttl_date is kept: the team card's updated; a note dated by `date` alone has none",
          notes["ZorgCore/Teams/team-alpha.md"]["ttl_date"] == "2026-01-01"
          and notes["Notes/Корзина 2.0 (mobile).md"]["ttl_date"] == "" and notes["Notes/Корзина 2.0 (mobile).md"]["date"]
          == "2026-08-20", (notes["ZorgCore/Teams/team-alpha.md"], notes["Notes/Корзина 2.0 (mobile).md"]))
    check("…and a query row carries it too", any(x["ttl_date"] == "2026-01-01" for x in idx.query(q("team alpha"), 5)
                                                 if x["path"] == "ZorgCore/Teams/team-alpha.md"))
    check("sensitive, hub, outdated", notes["Notes/Meetings/Pricing review 2026-09-30.md"]["sensitive"] is True
          and notes["ZorgCore/People/bea-two.md"]["hub"] is True and notes["Notes/Zorg Style Guide.md"]["hub"] is True
          and notes["Notes/Checkout flow (old).md"]["status"] == "outdated")
    check("two copies of one Confluence page: the same id, different dates",
          notes["Notes/Knowledge/Delivery slots (900100200).md"]["confluence_id"] == "900100200"
          == notes["ZorgCore/Pages/Delivery slots (900100200).md"]["confluence_id"]
          and notes["Notes/Knowledge/Delivery slots (900100200).md"]["date"] == "2026-10-05"
          and notes["ZorgCore/Pages/Delivery slots (900100200).md"]["date"] == "2026-09-01")
    hub = notes["Notes/Epics/Epic — PROJ-77.md"]
    check("the epic hub links the core page of the same name", hub["title"] == notes["ZorgCore/Epics/Epic — PROJ-77.md"]["title"]
          == "Epic — PROJ-77" and "epic — proj-77" in hub["links"], hub)
    check("the drafts share a version key, the standups do not",
          notes["Notes/Roadmap Q4 — draft v2.md"]["version_key"] == notes["Notes/Roadmap Q4 — draft v3.md"]["version_key"]
          and notes["Notes/Roadmap Q4 — draft v2.md"]["version_key"]
          and notes["Notes/Meetings/Standup 2026-10-01.md"]["version_key"] is None)
    b = notes["Notes/Broken frontmatter.md"]
    check("a broken frontmatter note is indexed as text", "Notes/Broken frontmatter.md" in paths and b["title"] == "Broken frontmatter"
          and not b["type"] and b["sensitive"] is False, b)
    check("…and its frontmatter lines are text", idx.query('"broken" "one"', 5)
          and idx.query('"broken" "one"', 5)[0]["path"] == "Notes/Broken frontmatter.md")
    check("a note without headings: one section, title from the file name, date from mtime",
          notes["Notes/Inbox.md"]["title"] == "Inbox" and str(notes["Notes/Inbox.md"]["date"])[:2] == "20")

    hits = idx.query('"zorg" "1234" "2"', 5)
    check("a Jira key is found by phrase", hits and hits[0]["path"] == "Notes/Tasks/ZORG-1234.2 checkout timeout.md", hits[:1])
    hits = idx.query(q("графіку роботи продавців"), 5)
    check("a word form finds its stem, the title ranks first", hits and hits[0]["path"] == "Notes/Кошик — графік роботи продавця.md",
          [h["path"] for h in hits])
    h = hits[0]
    check("a hit carries the note's metadata and the raw text of its section",
          {"id", "path", "source", "title", "heading", "text", "type", "date", "rank"} <= set(h) and h["text"].strip()
          and h["heading"].startswith("Кошик — графік роботи продавця › ") and h["type"] == "concept"
          and any("графік роботи продавця прямо" in x["text"] for x in hits), h)
    s = idx.section(h["id"])
    check("section(id) gives the same section", s and s["text"] == h["text"] and s["heading"] == h["heading"]
          and s["path"] == h["path"], s)
    check("…an unknown id is None", idx.section(10 ** 9) is None)
    check("a store record, the blocks file and a backup are never found",
          all(x["path"] in INDEXED for x in idx.query(q("record context store never indexed backup copy scope of work"), 50)))
    check("an empty expression answers nothing", idx.query("", 5) == [])

    # --- incremental: unchanged, touched, changed, removed
    calls = []
    real_split = ctx_index.split_sections
    ctx_index.split_sections = lambda text: calls.append(1) or real_split(text)
    r = idx.refresh(roots, store_rel, blocks_rels)
    check("nothing changed: nothing re-read", r["added"] == r["changed"] == r["removed"] == 0 and not calls, (r, len(calls)))
    f = env.note("Notes/Mobile cart notes.md")
    t = os.stat(f).st_mtime
    os.utime(f, (t, t + 10))
    r = idx.refresh(roots, store_rel, blocks_rels)
    check("a touched file with the same bytes is not counted as changed", r["changed"] == 0 and not calls, (r, len(calls)))
    os.utime(f, (t, t + 20)); open(f, "a", encoding="utf-8").write("\nnew line про кошик\n")
    r = idx.refresh(roots, store_rel, blocks_rels)
    check("a changed file is re-read, an unchanged one is not", r["changed"] == 1 and r["added"] == 0 and len(calls) == 1, (r, len(calls)))
    ctx_index.split_sections = real_split
    check("…and its new text is found", any("new line" in x["text"] for x in idx.query('"new" "line"', 5)))
    os.remove(env.note("Notes/Inbox.md"))
    before = idx.status()["sections"]
    r = idx.refresh(roots, store_rel, blocks_rels)
    check("a removed file leaves the index", r["removed"] == 1 and "Notes/Inbox.md" not in {n["path"] for n in idx.notes()}
          and idx.status()["sections"] == before - 1, r)
    live = INDEXED - {"Notes/Inbox.md"}

    # --- the time budget: two runs out of time, then one without a limit
    open(env.note("Notes/Zorg Style Guide.md"), "a", encoding="utf-8").write("\n- \"shopper\", not \"buyer\".\n")
    open(env.note("ZorgCore/Teams/team-alpha.md"), "a", encoding="utf-8").write("\n- Cy Three — designer\n")
    os.remove(env.note("Notes/Meetings/Standup 2026-10-08.md"))
    r1 = idx.refresh(roots, store_rel, blocks_rels, budget=0.0)
    s1 = json.loads(read(env.index, "index.json"))
    r2 = idx.refresh(roots, store_rel, blocks_rels, budget=0.0)
    paths = {n["path"] for n in idx.notes()}
    check("out of time twice: pending > 0, no row removed, nothing re-read",
          r1["pending"] > 0 and r2["pending"] > 0 and r1["removed"] == r2["removed"] == 0
          and r1["changed"] == r2["changed"] == 0 and paths == live, (r1, r2, sorted(live - paths)))
    check("…the queue and the count are in index.json", s1["pending"] == r1["pending"] and s1.get("queue"), s1)
    r3 = idx.refresh(roots, store_rel, blocks_rels)
    live -= {"Notes/Meetings/Standup 2026-10-08.md"}
    paths = {n["path"] for n in idx.notes()}
    check("the third run, without a limit, does it all", r3["changed"] == 2 and r3["removed"] == 1 and r3["pending"] == 0
          and paths == live and json.loads(read(env.index, "index.json"))["pending"] == 0, (r3, sorted(paths ^ live)))

    # --- a budget that runs out mid-walk: each run goes on from where the last one stopped
    for rel in ("Notes/Корзина 2.0 (mobile).md", "ZorgCore/People/bea-two.md"):
        open(env.note(rel), "a", encoding="utf-8").write("\nОновлено.\n")
    os.remove(env.note("Notes/Meetings/Standup 2026-10-01.md"))
    tick = [0.0]

    def clock():
        tick[0] += 1.0
        return tick[0]

    real_clock = ctx_index._clock
    ctx_index._clock = clock
    total, runs, kept, pend = {"changed": 0, "removed": 0}, 0, True, []
    while runs < 80:
        runs += 1
        r = idx.refresh(roots, store_rel, blocks_rels, budget=4.0)
        total["changed"] += r["changed"]; total["removed"] += r["removed"]; pend.append(r["pending"])
        now_paths = {n["path"] for n in idx.notes()}
        kept = kept and (live - {"Notes/Meetings/Standup 2026-10-01.md"}) <= now_paths
        if r["pending"] == 0:
            break
    ctx_index._clock = real_clock
    live -= {"Notes/Meetings/Standup 2026-10-01.md"}
    check("a walk cut by its budget goes on in the next run and ends", runs > 2 and pend[0] > 0 and pend[-1] == 0
          and total == {"changed": 2, "removed": 1} and {n["path"] for n in idx.notes()} == live, (runs, pend, total))
    check("…no row of a file still on disk was removed on the way", kept)

    # --- the lock
    lock = os.path.join(env.index, "index.lock")
    open(env.note("Notes/Mobile cart notes.md"), "a", encoding="utf-8").write("\nlocked edit\n")
    write(lock, json.dumps({"pid": os.getpid(), "at": time.time()}))
    r = idx.refresh(roots, store_rel, blocks_rels)
    check("a held lock: no update, locked", r["locked"] is True and r["changed"] == 0 and os.path.isfile(lock), r)
    check("…the query works on what is there", idx.query(q("графік роботи"), 5))
    write(lock, json.dumps({"pid": os.getpid(), "at": time.time() - 700}))
    r = idx.refresh(roots, store_rel, blocks_rels)
    check("a lock older than 600 s is abandoned: taken over, then released", r["locked"] is False and r["changed"] == 1
          and not os.path.exists(lock), r)

    # --- iCloud: a file not downloaded is not read and its row stays
    f = env.note("Notes/Mobile cart notes.md")
    open(f, "a", encoding="utf-8").write("\ndataless edit\n")
    real_dataless = ctx_index.is_dataless
    ctx_index.is_dataless = lambda p: unicodedata.normalize("NFC", p).endswith("Mobile cart notes.md")
    r = idx.refresh(roots, store_rel, blocks_rels)
    ctx_index.is_dataless = real_dataless
    check("a dataless file is skipped and counted, its row stays", r["skipped_dataless"] == 1 and r["changed"] == 0
          and "Notes/Mobile cart notes.md" in {n["path"] for n in idx.notes()}
          and not any("dataless edit" in x["text"] for x in idx.query(q("dataless edit"), 50)) and json.loads(read(env.index, "index.json"))["skipped_dataless"] == 1, r)
    r = idx.refresh(roots, store_rel, blocks_rels)
    check("…downloaded, it is read", r["changed"] == 1 and r["skipped_dataless"] == 0
          and any("dataless edit" in x["text"] for x in idx.query(q("dataless edit"), 50)), r)

    # --- an NFD file name, a file over 2 MB, a .trash folder
    name = unicodedata.normalize("NFD", "Йогурт і їжа.md")
    write(os.path.join(env.vault, "Notes", name), "# Йогурт\n\nНотатка про їжу і йогурт.\n")
    write(os.path.join(env.vault, "Notes", "Huge.md"), "# Huge\n" + "x" * ctx_index.MAX_BYTES)
    write(os.path.join(env.vault, "Notes", ".trash", "z.md"), "# Trash\n")
    r = idx.refresh(roots, store_rel, blocks_rels)
    paths = {n["path"] for n in idx.notes()}
    check("an NFD file name is kept in NFC", "Notes/Йогурт і їжа.md" in paths
          and all(p == unicodedata.normalize("NFC", p) for p in paths) and r["added"] == 1, (r, sorted(paths - live)))
    check("a file over 2 MB and a .trash folder are not indexed; the big one is counted", "Notes/Huge.md" not in paths
          and not any("/.trash/" in p for p in paths) and r["skipped_large"] == 1, r)
    check("…and a typed word finds the NFD one", any(x["path"] == "Notes/Йогурт і їжа.md" for x in idx.query(q("йогурт"), 5)))
    r = idx.refresh(roots, store_rel, blocks_rels)
    check("…the next run sees the same file, not a new one", r["added"] == r["changed"] == r["removed"] == 0, r)
    os.remove(os.path.join(env.vault, "Notes", "Huge.md"))

    # --- a broken or older index is put aside and built again
    live |= {"Notes/Йогурт і їжа.md"}
    db = os.path.join(env.index, "sections.sqlite")
    open(db, "wb").write(b"not a database at all, a few bytes of rubbish")
    check("a query on a broken index answers nothing and does not fail", idx.query(q("кошик"), 5) == [])
    r = idx.refresh(roots, store_rel, blocks_rels)
    check("a broken sections.sqlite is put aside and rebuilt", r["rebuilt"] is True and os.path.isfile(db + ".broken")
          and r["added"] == len(live) and {n["path"] for n in idx.notes()} == live, r)
    con = sqlite3.connect(db); con.execute("UPDATE meta SET value='search-index/0' WHERE key='schema'"); con.commit(); con.close()
    r = idx.refresh(roots, store_rel, blocks_rels)
    check("another schema is rebuilt too", r["rebuilt"] is True and idx.status()["schema"] == "search-index/1"
          and {n["path"] for n in idx.notes()} == live, r)
    os.remove(db)                                        # an index of an earlier build: the same schema name, no ttl_date
    con = sqlite3.connect(db); con.executescript(ctx_index.DDL.replace(" ttl_date TEXT,", ""))
    con.execute("INSERT INTO meta(key, value) VALUES ('schema', 'search-index/1')"); con.commit(); con.close()
    r = idx.refresh(roots, store_rel, blocks_rels)
    check("an index whose notes table lacks a column is rebuilt (Task 6 fix round 1: ttl_date)", r["rebuilt"] is True
          and {n["path"] for n in idx.notes()} == live and all("ttl_date" in n for n in idx.notes()), r)
    r = idx.rebuild(roots, store_rel, blocks_rels)
    check("rebuild: everything again", r["rebuilt"] is True and r["added"] == len(live) and r["pending"] == 0, r)

    # --- fix round 1: damage inside the file that the open checks do not see, met by the walk or a query
    def damage_notes_table():
        """Overwrite the notes table's own page (not its path index): counts still answer, reading the rows does not."""
        con = sqlite3.connect(db)
        page = con.execute("PRAGMA page_size").fetchone()[0]
        root_page = con.execute("SELECT rootpage FROM sqlite_master WHERE name='notes'").fetchone()[0]
        con.close()
        with open(db, "r+b") as f:
            f.seek((root_page - 1) * page)
            f.write(b"\x55" * page)

    def malformed_rows():
        con = sqlite3.connect(db)
        try:
            con.execute("SELECT count(*) FROM notes").fetchone()
            try:
                con.execute("SELECT id, path, mtime, size, hash FROM notes").fetchall()
                return False
            except sqlite3.DatabaseError:
                return True
        finally:
            con.close()

    os.remove(db + ".broken")
    damage_notes_table()
    check("(the damage passes the counts and breaks the rows)", malformed_rows())
    hits = idx.query(q("графік роботи"), 5)
    check("a query on a damaged index answers nothing and says so", hits == [] and idx.problem
          and "ctx index rebuild" in idx.problem, (hits, idx.problem))
    r = idx.refresh(roots, store_rel, blocks_rels)
    check("a damaged index met during the walk is put aside and built again in the same run",
          r["rebuilt"] is True and os.path.isfile(db + ".broken") and r["added"] == len(live)
          and {n["path"] for n in idx.notes()} == live and json.loads(read(env.index, "index.json"))["files"] == len(live), r)
    check("…and the query works again, with no problem to report", idx.query(q("графік роботи"), 5) and idx.problem is None)
    real_file = ctx_index._Walk._file
    os.remove(db + ".broken")
    open(env.note("Notes/Mobile cart notes.md"), "a", encoding="utf-8").write("\nbusy edit\n")

    def busy(self, ri, path, rel):
        raise sqlite3.OperationalError("database is locked")

    ctx_index._Walk._file = busy
    try:
        idx.refresh(roots, store_rel, blocks_rels)
        raised = None
    except sqlite3.OperationalError as e:
        raised = str(e)
    ctx_index._Walk._file = real_file
    check("a busy database is no broken one: the error goes up, nothing is put aside, the lock is released",
          raised == "database is locked" and not os.path.exists(db + ".broken") and not os.path.exists(lock)
          and {n["path"] for n in idx.notes()} == live, raised)
    r = idx.refresh(roots, store_rel, blocks_rels)
    check("…the next run goes on as usual", r["rebuilt"] is False and r["changed"] == 1, r)
    check("no index file ever lands in the vault",
          not any(os.path.basename(p) in ("sections.sqlite", "sections.sqlite.broken", "index.json", "index.lock")
                  for p in tree(env.vault)))

    # --- the command line
    rc, out, res = env.run("index", "status")
    check("ctx index status: exit 0 and the counters", rc == 0 and res and res.get("command") == "index"
          and res.get("action") == "status" and res.get("files") == len(live) and res.get("sections", 0) > 0
          and res.get("schema") == "search-index/1" and res.get("pending") == 0 and res.get("skipped_dataless") == 0
          and res.get("updated"), (rc, out[-500:]))
    rc, out, res = env.run("index", "rebuild")
    check("ctx index rebuild: exit 0 and the same counters", rc == 0 and res and res.get("action") == "rebuild"
          and res.get("files") == len(live), (rc, out[-500:]))
    check("…the store and the vault are not written", not os.path.isdir(os.path.join(env.store, ".state"))
          and not os.path.exists(os.path.join(env.home, ".grow-pm", ".ctx.lock")))
    write(lock, json.dumps({"pid": os.getpid(), "at": time.time()}))
    rc, out, res = env.run("index", "rebuild")
    check("rebuild while another process holds the index lock: exit 4", rc == 4 and os.path.isfile(lock), (rc, out[-300:]))
    rc, out, res = env.run("index", "status")
    check("status while it is held: exit 0, the index as it is", rc == 0 and res.get("files") == len(live), (rc, out[-300:]))
    os.remove(lock)
    damage_notes_table()
    rc, out, res = env.run("index", "status")
    check("ctx index status on a damaged index: built again, exit 0", rc == 0 and res and res.get("files") == len(live)
          and "built again" in out and os.path.isfile(db + ".broken"), (rc, out[-400:]))
    heads = ctx_index.Index(env.home).headings()
    check("headings(): (section id, path, heading) of every section", len(heads) == ctx_index.Index(env.home).status()["sections"]
          and all(isinstance(s, int) and isinstance(p, str) and isinstance(h, str) for s, p, h in heads)
          and any(p == "Notes/Кошик — графік роботи продавця.md" and h.endswith("› Рішення") for _, p, h in heads), heads[:3])
    idx_d = ctx_index.Index(env.home)
    con = sqlite3.connect(idx_d.db_path)
    try:
        pages = [r[0] for r in con.execute("SELECT pageno FROM dbstat WHERE name = 'sections_fts_data' AND pagetype = 'leaf'")]
        size = con.execute("PRAGMA page_size").fetchone()[0]
    except sqlite3.Error:
        pages = []
    con.close()
    if pages:
        with open(idx_d.db_path, "r+b") as f:
            for pg in pages:
                f.seek((pg - 1) * size + 100)
                f.write(b"\xff" * (size - 200))
        idx_d.query(q("кошик продавця"), 5)
        check("an FTS5 corruption is a damaged index (rebuild), not an expression the index did not take",
              (idx_d.problem or "").startswith("індекс пошуку не читається (") and "fts5" in idx_d.problem, idx_d.problem)
    else:
        print("⚠️  skipped: this SQLite has no dbstat — the FTS5-corruption check needs it")
    import ctx as ctx_cli  # noqa: E402
    a = ctx_cli.build_parser().parse_args(["index", "status"])
    check("index is no writing command of the store", "index" not in ctx_cli.WRITING and not ctx_cli.writes(a))

# --- fix round 1: a root that is the vault itself (its index names have no top folder) and a core outside every vault
with tempfile.TemporaryDirectory() as d:
    v, outside = os.path.join(d, "vault"), os.path.join(d, "outside-core")
    for rel, text in (("a.md", "# A\nalpha\n"), ("Sub/b.md", "# B\nbeta\n"), ("keep.md", "# K\nkeep\n"),
                      ("keep2.md", "# K2\nkeep two\n"), ("@Bea Two.md", "# Bea Two\nA people note named the Obsidian way.\n")):
        write(os.path.join(v, *rel.split("/")), text)
    write(os.path.join(outside, "c.md"), "# C\ngamma\n")
    vtext = "## Obsidian Vaults\n\n- path: %s\n" % v
    roots = ctx_index.scope(vtext, []) + [ctx_index.Root("zorg-x", outside, "")]
    check("(the root is the vault itself)", [r["path"] for r in roots][:1] == [v] and ctx_index.rel_path(v, [v]) == "")
    idx = ctx_index.Index(os.path.join(d, "home"))
    r = idx.refresh(roots, "_System/context", [])
    check("a vault-level root names its files without a top folder",
          {n["path"] for n in idx.notes()} == {"a.md", "Sub/b.md", "keep.md", "keep2.md", "@Bea Two.md", "@zorg-x/c.md"},
          idx.notes())
    os.remove(os.path.join(v, "a.md"))
    os.remove(os.path.join(v, "@Bea Two.md"))
    shutil.rmtree(os.path.join(v, "Sub"))
    r = idx.refresh(roots, "_System/context", [], budget=0.0)
    check("…out of time it counts the files it holds there, not one folder",
          r["pending"] == 6 and r["removed"] == 0, r)
    r = idx.refresh(roots, "_System/context", [])
    check("…files (an @-named one too) and a folder deleted at its top level leave the index; the core outside stays",
          r["removed"] == 3 and {n["path"] for n in idx.notes()} == {"keep.md", "keep2.md", "@zorg-x/c.md"}, (r, idx.notes()))

with tempfile.TemporaryDirectory() as d:
    home = os.path.join(d, "home"); os.makedirs(os.path.join(home, ".grow-pm"))
    ctxp = os.path.join(home, ".grow-pm", "local-context.md")
    write(ctxp, read(ROOT, "testing", "fixtures", "ctx", "minimal.md"))
    env2 = dict(os.environ); env2.pop("GROW_PM_CONTEXT_PATH", None)
    p = subprocess.run([sys.executable, CTX, "index", "status", "--home", home, "--context", ctxp],
                       capture_output=True, text=True, env=env2, timeout=60)
    check("no vault and no repository folder: exit 3, nothing created", p.returncode == 3
          and not os.path.exists(os.path.join(home, ".grow-pm", "index")), (p.returncode, p.stdout[-300:]))

# --- final review: status() reports the database's own day, never index.json's for a database without one
with tempfile.TemporaryDirectory() as d:
    idx = ctx_index.Index(os.path.join(d, "home"))
    write(idx.state_path, json.dumps({"schema": ctx_index.SCHEMA, "updated": "2026-01-02T09:00:00+02:00", "files": 19,
                                      "sections": 60, "pending": 3, "skipped_dataless": 1}))
    s0 = idx.status()
    check("status(): no database beside an old index.json — no day, no schema, no counts of its own; pending from the queue",
          (s0["updated"], s0["schema"], s0["files"], s0["sections"], s0["pending"]) == (None, None, 0, 0, 3), s0)
    con = sqlite3.connect(idx.db_path)
    con.executescript(ctx_index.DDL)
    con.commit()
    con.close()
    s1 = idx.status()
    check("…a database still being filled (no `updated` in its meta): its day is none, not index.json's",
          s1["updated"] is None and s1["files"] == 0, s1)
    check("built(): False with no `updated` row in the meta", idx.built() is False)
    os.remove(idx.db_path)
    check("…and with no database", idx.built() is False and idx.problem is None)
    write(idx.db_path, "not a database at all, longer than one header of sixteen bytes\n" * 4)
    check("…None for a file SQLite cannot read, with the problem said", idx.built() is None
          and (idx.problem or "").startswith("індекс пошуку не читається ("), idx.problem)

print("RESULT:", "GREEN ✅" if not fails else "RED ❌")
sys.exit(1 if fails else 0)
