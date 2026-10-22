#!/usr/bin/env python3
"""TC-ctx-3160-search — scripts/ctx_search.py: the sources of a question, their fusion and the priors (since v3.16.0).

The fictional Zorg vault of testing/fixtures/search/ (the plugin folder Notes/, the core ZorgCore/ registered as
zorg-core, the team glossary under home/.grow-pm/) is copied to a temp dir. A user's own local index, zorg-brain.sqlite,
is built here from a part of the fixture notes in the shape such an index has in the wild (`path` in `notes_fts`) and in
the shape of context-provider-protocol.md §10 (`notes_fts` + `notes`, `rowid = notes.id`). Checked: every variant ×
source is a list of its own, a glossary list beside it; a local-index hit under the context store is dropped; MCP is
asked only for a repository with no folder on disk, an unreachable or slow server is one line and the search goes on;
an index of another shape is one line; RRF with the glossary at half weight; the priors (skill type, product, hub,
`застаріле` by status, `станом на <день>` by the class TTL of the core's manifest, the snapshot's day, glossary only,
one word); without duplicates (the five keys, near copies among them); `--get`; `search_types` in the manifest and the
check behind validator check 19. Nothing is written to the vault or the store.
Stdlib only; run from the repo root:

  env -u GROW_PM_CONTEXT_PATH -u GROW_PM_PROVIDER_PATHS python3 testing/ctx_search_test.py
"""
import datetime, hashlib, inspect, json, os, shutil, sqlite3, subprocess, sys, tempfile, time, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "testing"))
import ctx_hints as ch  # noqa: E402
import ctx_index as ci  # noqa: E402
import ctx_read as cr  # noqa: E402
import ctx_search as cs_  # noqa: E402
import ctx_stem as st  # noqa: E402
from mcp_fake import FakeMcp  # noqa: E402

FIX = os.path.join(ROOT, "testing", "fixtures", "search")
NOW = datetime.datetime(2026, 10, 20, 12, 0)
VARIANTS = ["кошик мобільний", "корзина мобильная", "mobile cart"]
BRAIN_NOTES = ["Notes/Кошик — графік роботи продавця.md", "Notes/Корзина 2.0 (mobile).md", "Notes/Mobile cart notes.md",
               "Notes/_System/context/records/x.md", "Growth/Cart experiments.md"]
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
            s = os.stat(p)
            out[os.path.relpath(p, top)] = (s.st_size, s.st_mtime)
    return out


class Env:
    """A temp home (the fixture's, with its glossary) and a temp vault: {{VAULT}} and {{HOME}} filled in. A mirror-only
    note Growth/Cart experiments.md lies outside the plugin folder: only the local index knows it."""

    def __init__(self, d):
        self.d = d
        self.home = os.path.join(d, "home")
        self.vault = os.path.join(d, "vault")
        shutil.copytree(os.path.join(FIX, "home"), self.home)
        shutil.copytree(os.path.join(FIX, "vault"), self.vault)
        for dirpath, _, names in os.walk(self.vault):
            for n in names:
                p = os.path.join(dirpath, n)
                if n.endswith(".yaml") and "{{VAULT}}" in read(p):
                    write(p, read(p).replace("{{VAULT}}", self.vault))
        write(self.note("Growth/Cart experiments.md"),
              "---\ntype: ab-test-results\nproduct: Zorg App\ndate: 2026-08-01\n---\n# Cart experiments\n\n"
              "The mobile cart test: the seller's hours under each block lifted the paid orders.\n")
        self.text = read(FIX, "context.md").replace("{{VAULT}}", self.vault).replace("{{HOME}}", self.home)
        self.store = os.path.join(self.vault, "Notes", "_System", "context")
        self.brain = os.path.join(self.home, "zorg-brain.sqlite")
        self.providers = os.path.join(self.vault, "Notes", "_System", "providers")

    def note(self, rel):
        return os.path.join(self.vault, *rel.split("/"))

    def reg(self, rid, text):
        write(os.path.join(self.providers, rid + ".yaml"), text)

    def sctx(self, **kw):
        return cs_.context_for(self.home, self.text, self.store, **kw)

    def refresh(self, sctx):
        return ci.Index(self.home).refresh(sctx["roots"], sctx["store_rel"], sctx["blocks_rels"])


def build_brain(path, vault, rels, form="wild", junk=(), mtimes=None):
    """A user's own local index over `rels` (vault-relative): "wild" — `path` in notes_fts, meta k/v with `vault`;
    "s10" — context-provider-protocol.md §10, notes_fts rowid = notes.id, meta key/value with `vault_root`; "foreign" —
    neither. `junk` rows (wild only) carry a path that is no path; `mtimes` {rel: seconds} fills `notes.mtime`."""
    if os.path.exists(path):
        os.remove(path)
    con = sqlite3.connect(path)
    if form == "foreign":
        con.executescript("CREATE TABLE documents(path TEXT, body TEXT);"
                          "CREATE VIRTUAL TABLE docs_fts USING fts5(body);")
        con.commit()
        con.close()
        return
    if form == "wild":
        con.executescript(
            "CREATE TABLE notes(path TEXT PRIMARY KEY, top TEXT, folder TEXT, title TEXT, type TEXT, kind TEXT, date TEXT,"
            " status TEXT, mtime REAL, size INTEGER, hash TEXT, fm_json TEXT, headings TEXT, n_words INTEGER, indexed_at TEXT);"
            "CREATE VIRTUAL TABLE notes_fts USING fts5(path UNINDEXED, title, aliases, tags, headings, body,"
            " tokenize='unicode61 remove_diacritics 2');"
            "CREATE TABLE meta(k TEXT PRIMARY KEY, v TEXT);")
        con.execute("INSERT INTO meta VALUES ('vault', ?)", (vault,))
    else:
        con.executescript(
            "CREATE TABLE notes(id INTEGER PRIMARY KEY, path TEXT UNIQUE, vault TEXT, title TEXT, type TEXT, hash TEXT,"
            " mtime REAL, frontmatter_json TEXT);"
            "CREATE VIRTUAL TABLE notes_fts USING fts5(title, headings, body, tokenize='unicode61 remove_diacritics 2');"
            "CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT);")
        con.execute("INSERT INTO meta VALUES ('schema', '1')")
        con.execute("INSERT INTO meta VALUES ('vault_root', ?)", (vault,))
    for i, rel in enumerate(rels, 1):
        text = read(vault, *rel.split("/"))
        m = ci.note_meta(rel, text)
        if form == "wild":
            con.execute("INSERT INTO notes(path, top, title, type, date, status, fm_json, mtime) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (rel, rel.split("/")[0], m["title"], m["type"], m["date"], m["status"],
                         json.dumps({"updated": m["ttl_date"]}) if m["ttl_date"] else None, (mtimes or {}).get(rel)))
            con.execute("INSERT INTO notes_fts(path, title, aliases, tags, headings, body) VALUES (?, ?, '', '', '', ?)",
                        (rel, m["title"], text))
        else:
            con.execute("INSERT INTO notes(id, path, vault, title, type, frontmatter_json, mtime) VALUES (?, ?, 'Zorg', ?, ?, ?, ?)",
                        (i, rel, m["title"], m["type"], json.dumps(dict({"date": m["date"], "status": m["status"]},
                                                                         **({"updated": m["ttl_date"]} if m["ttl_date"] else {}))),
                         (mtimes or {}).get(rel)))
            con.execute("INSERT INTO notes_fts(rowid, title, headings, body) VALUES (?, ?, '', ?)", (i, m["title"], text))
    for p in junk:
        con.execute("INSERT INTO notes_fts(path, title, aliases, tags, headings, body) VALUES (?, 'junk', '', '', '', ?)",
                    (p, "кошик мобільний mobile cart"))
    con.commit()
    con.close()


def hit(path, heading="", lst="own|v0", **kw):
    return cs_.Hit(path, heading, lst.split("|")[0], 1, list=lst, **kw)


def paths(lists, key):
    return [h["path"] for h in lists.get(key, [])]


def cand(path, **kw):
    """A candidate as the caller builds it from the fused lists, before dedup: the hits that found it, score 1."""
    c = {"path": path, "heading": "", "score": 1.0, "flags": [], "hits": [hit(path)]}
    c.update(kw)
    return c


def deadline(s=60):
    return time.monotonic() + s


# ------------------------------------------------------------------ the spec's numbers
check("RRF k 60, glossary 0.5, 50 a list, 20 s a source, 5 s to open a local index",
      (cs_.RRF_K, cs_.GLOSSARY_W, cs_.LIST_LIMIT, cs_.SOURCE_S, cs_.OPEN_S) == (60, 0.5, 50, 20.0, 5.0))
check("B2: a search lists 30 candidates unless told otherwise; the eval's pool stays 50",
      cs_.LIMIT == 30 and inspect.signature(cs_.run).parameters["limit"].default == 30 and ch.POOL == 50,
      (getattr(cs_, "LIMIT", None), inspect.signature(cs_.run).parameters["limit"].default, ch.POOL))

# ------------------------------------------------------------------ fuse
fused = cs_.fuse({"own|v0": [hit("a.md")], "own|g0": [hit("b.md", lst="own|g0")]})
check("a glossary list weighs half", abs(fused[("a.md", "")] - 1 / 61) < 1e-9 and abs(fused[("b.md", "")] - 0.5 / 61) < 1e-9,
      fused)
fused = cs_.fuse({"own|v0": [hit("a.md"), hit("b.md")], "zorg-brain|v1": [hit("b.md", lst="zorg-brain|v1")]})
check("RRF sums a key over the lists, by its place in each", abs(fused[("b.md", "")] - (1 / 62 + 1 / 61)) < 1e-9
      and abs(fused[("a.md", "")] - 1 / 61) < 1e-9, fused)
fused = cs_.fuse({"own|v0": [hit("a.md", "H1"), hit("a.md", "H2"), hit("a.md", "H1")]})
check("a section is its own key, and counts once a list", set(fused) == {("a.md", "H1"), ("a.md", "H2")}
      and abs(fused[("a.md", "H1")] - 1 / 61) < 1e-9 and abs(fused[("a.md", "H2")] - 1 / 62) < 1e-9, fused)

# ------------------------------------------------------------------ the search context
with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    sx = env.sctx()
    check("context_for: home, text, store, vaults, repositories, roots, blocks files",
          {"home", "text", "store_rel", "vaults", "repos", "blocks_rels", "roots"} <= set(sx)
          and sx["home"] == env.home and sx["text"] == env.text, sorted(sx))
    check("…the store and the core's blocks file as the index names them", sx["store_rel"] == "Notes/_System/context"
          and "ZorgCore/_System/context-blocks.md" in sx["blocks_rels"], (sx["store_rel"], sx["blocks_rels"]))
    check("…the roots of the index: the plugin folder and the core", [(r["source"], os.path.basename(r["path"]))
                                                                     for r in sx["roots"]] == [("own", "Notes"), ("zorg-core", "ZorgCore")],
          sx["roots"])
    check("…the repositories are loaded when not given", [r["id"] for r in sx["repos"]] == ["zorg-core"], sx["repos"])
    check("…and taken as given", env.sctx(repos=[])["repos"] == [] and len(env.sctx(repos=[])["roots"]) == 1)

    # ---------------------------------------------------------- sources
    check("no local index file: own only", [(s["id"], s["kind"]) for s in cs_.sources(env.text, sx["repos"])]
          == [("own", "own")], cs_.sources(env.text, sx["repos"]))
    build_brain(env.brain, env.vault, BRAIN_NOTES)
    srcs = cs_.sources(env.text, sx["repos"])
    check("the Vault Search MCP line with an index file is a local source",
          [(s["id"], s["kind"]) for s in srcs] == [("own", "own"), ("zorg-brain", "local")], srcs)
    check("MCP is not asked for a repository whose folder is on disk", all(s["kind"] != "mcp" for s in srcs), srcs)
    check("which= picks the kinds", [s["id"] for s in cs_.sources(env.text, sx["repos"], which=("local",))] == ["zorg-brain"]
          and [s["id"] for s in cs_.sources(env.text, sx["repos"], which=("own",))] == ["own"])

    # ---------------------------------------------------------- gather: own index + the local index, three variants
    env.refresh(sx)
    before_vault, before_home_glossary = tree(env.vault), tree(os.path.join(env.home, ".grow-pm", "knowledge-library"))
    t0 = time.monotonic()
    lists, notes = cs_.gather(sx, VARIANTS, srcs, deadline())
    check("each variant × source is its own list", {"own|v0", "own|v1", "own|v2", "zorg-brain|v0"} <= set(lists),
          sorted(lists))
    check("a local index hit under the store is dropped",
          not any(h["path"].startswith("Notes/_System/context/") for l in lists.values() for h in l))
    check("…while the local index answered with the rest",
          "Notes/Кошик — графік роботи продавця.md" in paths(lists, "zorg-brain|v0")
          and "Growth/Cart experiments.md" in paths(lists, "zorg-brain|v2"), {k: paths(lists, k) for k in lists})
    check("a glossary list beside each variant that names a group", {"own|g0", "own|g1", "own|g2", "zorg-brain|g0"}
          <= set(lists), sorted(lists))
    check("…the glossary finds the note the variant's own words miss («кошик» → «корзина»)",
          "Notes/Корзина 2.0 (mobile).md" in paths(lists, "own|g0"), paths(lists, "own|g0"))
    g0 = lists["own|v0"]
    check("hits carry the variant, the list, the place, the source", all(h["variant"] == 0 and h["list"] == "own|v0"
                                                                        and h["source"] == "own" for h in g0)
          and [h["rank"] for h in g0] == list(range(1, len(g0) + 1)), g0[:2])
    concept = next((h for h in g0 if h["path"] == "Notes/Кошик — графік роботи продавця.md"
                    and h["heading"].endswith("Рішення")), None)
    check("an own hit is a section with its id, title, type and date", concept and concept["heading"]
          and isinstance(concept["section_id"], int) and concept["title"] == "Кошик — графік роботи продавця"
          and concept["type"] == "concept" and concept["date"].startswith("2026-09-15"), concept)
    check("…and how many of the variant's terms it holds", concept and concept["terms"] == 2 and concept["asked"] == 2,
          concept)
    korzyna = next((h for h in lists["own|g0"] if h["path"] == "Notes/Корзина 2.0 (mobile).md"), None)
    check("…and the date a class TTL reads: its own updated; a note dated by `date` alone has none",
          concept and concept.get("ttl_date") == "2026-09-15" and korzyna and korzyna.get("ttl_date") == "", (concept, korzyna))
    style = next((h for h in lists["own|v0"] if h["path"] == "Notes/Zorg Style Guide.md"), None)
    check("…one of two for a note that names only the cart", style and style["terms"] == 1 and style["asked"] == 2, style)
    brain = next((h for h in lists["zorg-brain|v0"] if h["path"] == "Notes/Кошик — графік роботи продавця.md"), None)
    check("a local-index hit is a note: no heading, its title, type and date", brain and brain["heading"] == ""
          and brain["title"] == "Кошик — графік роботи продавця" and brain["type"] == "concept"
          and brain["date"].startswith("2026-09-15") and brain["source"] == "zorg-brain", brain)
    check("…a snippet with the match in «»", brain and "«" in (brain["snippet"] or ""), brain)
    check("…the terms it holds, as the local index matches them (unstemmed words, prefix)",
          brain and brain["terms"] == 1 and brain["asked"] == 2, brain)
    brain_k = next((h for h in lists["zorg-brain|v1"] if h["path"] == "Notes/Корзина 2.0 (mobile).md"), None)
    check("…the TTL date from its frontmatter JSON (updated | snapshot | generated only)", brain.get("ttl_date") == "2026-09-15"
          and brain_k and brain_k.get("ttl_date") == "" and brain_k["date"].startswith("2026-08-20"), (brain, brain_k))
    check("own paths are in scope only: Notes/ and ZorgCore/", all(h["path"].split("/")[0] in ("Notes", "ZorgCore")
                                                                   for k, l in lists.items() if k.startswith("own|")
                                                                   for h in l))
    check("nothing to say about a sound search", notes == [], notes)
    lists_m, notes_m = cs_.gather(sx, ["картка товару", "commission for small sellers"], srcs, deadline())
    check("a glossary name of several words (product detail page) is an AND group every source takes",
          notes_m == [] and {"own|g0", "zorg-brain|g0"} <= set(lists_m), (notes_m, sorted(lists_m)))
    pricing = next((h for h in lists_m.get("own|v1", []) if h["path"] == "Notes/Meetings/Pricing review 2026-09-30.md"), None)
    check("an own hit says whether its note is sensitive", pricing and pricing["sensitive"] is True
          and concept and concept["sensitive"] is False, pricing)
    check("gather writes nothing to the vault or the glossary", tree(env.vault) == before_vault
          and tree(os.path.join(env.home, ".grow-pm", "knowledge-library")) == before_home_glossary)

    # ---------------------------------------------------------- a removed registration's rows do not answer
    lists_all, _ = cs_.gather(sx, ["seller working hours"], cs_.sources(env.text, sx["repos"], which=("own",)), deadline())
    no_core = env.sctx(repos=[])
    lists_cut, _ = cs_.gather(no_core, ["seller working hours"], [cs_.Source("own", "own")], deadline())
    check("the core answers while it is registered", any(p.startswith("ZorgCore/") for p in paths(lists_all, "own|v0")),
          paths(lists_all, "own|v0"))
    check("…an own hit names the source of its root: own for the plugin folder, the repository for the core",
          all(h["source"] == ("zorg-core" if h["path"].startswith("ZorgCore/") else "own") for h in lists_all["own|v0"]),
          [(h["path"], h["source"]) for h in lists_all["own|v0"]])
    check("index rows of a root no longer in scope do not answer",
          paths(lists_cut, "own|v0") and not any(p.startswith("ZorgCore/") for p in paths(lists_cut, "own|v0")),
          paths(lists_cut, "own|v0"))

    # ---------------------------------------------------------- a stop-word variant asks nothing and fails nothing
    lists_stop, notes_stop = cs_.gather(sx, ["що і як?"], srcs, deadline())
    check("an all-stop variant: empty lists, no error", lists_stop.get("own|v0") == [] and lists_stop.get("zorg-brain|v0") == []
          and notes_stop == [], (lists_stop, notes_stop))

    # ---------------------------------------------------------- the local index in the §10 shape
    build_brain(env.brain, env.vault, BRAIN_NOTES, form="s10")
    lists10, notes10 = cs_.gather(sx, VARIANTS, srcs, deadline())
    check("the §10 shape (notes_fts + notes, rowid = notes.id) reads as the wild one",
          {k: sorted(paths(lists10, k)) for k in lists10 if k.startswith("zorg-brain|")}
          == {k: sorted(paths(lists, k)) for k in lists if k.startswith("zorg-brain|")} and notes10 == [],
          ({k: paths(lists10, k) for k in lists10 if k.startswith("zorg-brain")}, notes10))
    b10 = next((h for h in lists10["zorg-brain|v0"] if h["path"] == "Notes/Кошик — графік роботи продавця.md"), None)
    check("…title and type from notes, the date from its frontmatter", b10 and b10["title"] == "Кошик — графік роботи продавця"
          and b10["type"] == "concept" and (b10["date"] or "").startswith("2026-09-15") and b10.get("ttl_date") == "2026-09-15",
          b10)

    # ---------------------------------------------------------- an index of another shape
    build_brain(env.brain, env.vault, [], form="foreign")
    lists_f, notes_f = cs_.gather(sx, VARIANTS, srcs, deadline())
    check("an index of another shape: one line, the search goes on",
          notes_f == ["індекс zorg-brain має незнайому схему — без нього"] and lists_f.get("own|v0")
          and not any(k.startswith("zorg-brain|") for k in lists_f), (notes_f, sorted(lists_f)))
    write(env.brain, "this is no database at all\n" * 40)
    _, notes_x = cs_.gather(sx, VARIANTS, srcs, deadline())
    check("…and so does a file that is no SQLite", notes_x == ["індекс zorg-brain має незнайому схему — без нього"], notes_x)

    # ---------------------------------------------------------- results without a usable path are skipped
    build_brain(env.brain, env.vault, BRAIN_NOTES[:1], junk=("", None, 7))
    lists_j, notes_j = cs_.gather(sx, VARIANTS[:1], srcs, deadline())
    check("a local hit with no usable path is skipped silently",
          paths(lists_j, "zorg-brain|v0") == ["Notes/Кошик — графік роботи продавця.md"] and notes_j == [],
          (paths(lists_j, "zorg-brain|v0"), notes_j))

    # ---------------------------------------------------------- the glossary that cannot be read
    write(os.path.join(env.home, ".grow-pm", "knowledge-library", "glossary", "zorg-app.yaml"), "terms:\n\tbroken\n")
    lists_b, notes_b = cs_.gather(sx, VARIANTS[:1], [cs_.Source("own", "own")], deadline())
    check("a glossary file that cannot be read: one line, the _org groups still widen",
          len([n for n in notes_b if "zorg-app.yaml" in n]) == 1 and "own|g0" in lists_b, (notes_b, sorted(lists_b)))

# ------------------------------------------------------------------ a vault-wide own root (Task 6 fix round 1)
with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    text = env.text.replace("| %s | Notes |" % env.vault, "| %s | . |" % env.vault)
    ext = os.path.join(d, "ext-core")
    write(os.path.join(ext, "Seller hours.md"), "---\ntype: page\n---\n# Seller hours\n\nThe seller hours in the cart.\n")
    reg = os.path.join(env.home, ".grow-pm", "providers", "zorg-ext.yaml")
    write(reg, "schema: provider-registration/2\nid: zorg-ext\ntitle: Zorg external core\nkind: folder\nauthority: org\n"
               "core_root: %s\nstatus: active\n" % ext)
    sx = cs_.context_for(env.home, text)
    check("plugin folder `.`: the own root is the whole vault, the external core a root of its own",
          [(r["source"], r["path"]) for r in sx["roots"]] == [("own", env.vault), ("zorg-ext", ext)], sx["roots"])
    ci.Index(env.home).refresh(sx["roots"], sx["store_rel"], sx["blocks_rels"])
    own = [cs_.Source("own", "own")]
    before, _ = cs_.gather(sx, ["seller hours"], own, deadline())
    check("…the external core answers while it is registered", "@zorg-ext/Seller hours.md" in paths(before, "own|v0"),
          paths(before, "own|v0"))
    os.remove(reg)
    sx2 = cs_.context_for(env.home, text)
    after, _ = cs_.gather(sx2, ["seller hours"], own, deadline())
    check("…a vault-wide root does not keep a removed core's rows: no @<repository>/… name answers",
          paths(after, "own|v0") and not any(p.startswith(("@", "/")) for p in paths(after, "own|v0")),
          paths(after, "own|v0"))

# ------------------------------------------------------------------ A4: _System/_scratch/ answers from no source
with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    SCRATCH = "Notes/_System/_scratch/people_digests/bea-two.md"
    write(env.note(SCRATCH), "---\ntype: note\n---\n# Bea Two\n\nThe mobile cart: what Bea said in the 1-1s.\n")
    build_brain(env.brain, env.vault, [SCRATCH, "Notes/Mobile cart notes.md"])
    sx = env.sctx()
    env.refresh(sx)
    lists_s, _ = cs_.gather(sx, ["mobile cart"], cs_.sources(env.text, sx["repos"]), deadline())
    check("A4: a per-person digest under <plugin folder>/_System/_scratch/ is no candidate of any source",
          paths(lists_s, "zorg-brain|v0") == ["Notes/Mobile cart notes.md"]
          and not any(h["path"] == SCRATCH for l in lists_s.values() for h in l), {k: paths(lists_s, k) for k in lists_s})

# ------------------------------------------------------------------ MCP sources
def growth_reg(url, core_root=""):
    return ("schema: provider-registration/2\nid: zorg-growth\ntitle: Zorg growth\nkind: mcp\nauthority: team\n"
            + ("core_root: %s\n" % core_root if core_root else "")
            + "endpoint:\n  url: %s\n  root: \"Growth/\"\nblocks_file: _System/context-blocks.md\nstatus: active\n" % url)


with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    seen = []

    def search(args):
        seen.append(args)
        return {"results": [{"path": "Growth/Cart experiments.md", "title": "Cart experiments", "snippet": "the «mobile cart» test"},
                            {"path": "Growth/Pricing.md", "title": "Pricing"},
                            {"path": "Growth/_System/context-blocks.md", "title": "blocks"},
                            {"path": "Growth/diagram.png"},
                            {"path": ""}, {"title": "no path"}, {"path": 7}, {"error": "a server's complaint"}]}, False

    with FakeMcp() as s:
        s.handlers["vault_search"] = search
        env.reg("zorg-growth", growth_reg(s.url))
        sx = env.sctx()
        env.refresh(sx)
        srcs = cs_.sources(env.text, sx["repos"])
        check("a repository with an endpoint and no folder on disk is an MCP source",
              [(x["id"], x["kind"]) for x in srcs] == [("own", "own"), ("zorg-growth", "mcp")], srcs)
        only = cs_.sources(env.text, sx["repos"], which=("mcp",))
        check("--sources mcp asks every repository with an endpoint (and no other kind)",
              [(x["id"], x["kind"]) for x in only] == [("zorg-growth", "mcp")], only)
        lists, notes = cs_.gather(sx, VARIANTS, srcs, deadline())
        got = paths(lists, "zorg-growth|v2")
        check("MCP: a path with no core folder is @<repository>/<path under endpoint.root>",
              got == ["@zorg-growth/Cart experiments.md", "@zorg-growth/Pricing.md"], got)
        check("…the blocks file, a file that is not a note and results with no usable path are dropped silently",
              notes == [] and all(len(paths(lists, k)) == 2 for k in lists if k.startswith("zorg-growth|")),
              (notes, {k: paths(lists, k) for k in lists}))
        first = lists["zorg-growth|v2"][0]
        check("…a hit keeps the server's path, title and snippet", first.get("remote") == "Growth/Cart experiments.md"
              and first["title"] == "Cart experiments" and first["snippet"] == "the «mobile cart» test", first)
        queries = [a.get("query") for a in seen]
        check("vault_search gets the any-word expression of the unstemmed words, limit 50",
              st.fts_or(st.raw_terms("mobile cart")) in queries and all(a.get("limit") == 50 for a in seen), seen[:3])
        check("…and the glossary expression of each variant that names a group", "zorg-growth|g0" in lists
              and len(seen) == 6, (len(seen), sorted(lists)))
    with FakeMcp() as s:
        s.handlers["vault_search"] = lambda args: ({"results": [
            {"path": "Growth/_System/_scratch/people_digests/bea-two.md", "title": "Bea Two"},
            {"path": "Growth/Cart experiments.md", "title": "Cart experiments"}]}, False)
        env.reg("zorg-growth", growth_reg(s.url))
        sx = env.sctx()
        lists, notes = cs_.gather(sx, ["mobile cart"], cs_.sources(env.text, sx["repos"], which=("mcp",)), deadline())
        check("R8 (A4): a server's hit under _System/_scratch/ is dropped too", paths(lists, "zorg-growth|v0")
              == ["@zorg-growth/Cart experiments.md"] and notes == [], (paths(lists, "zorg-growth|v0"), notes))
    with FakeMcp() as s:
        s.handlers["vault_search"] = search
        env.reg("zorg-growth", growth_reg(s.url, core_root=os.path.join(env.vault, "Growth")))
        sx = env.sctx()
        srcs = cs_.sources(env.text, sx["repos"], which=("mcp",))
        lists, notes = cs_.gather(sx, ["mobile cart"], srcs, deadline())
        check("--sources mcp asks a repository whose folder is on disk too", [x["id"] for x in srcs] == ["zorg-growth"])
        check("MCP: a path maps through endpoint.root → core_root → the vault's name of the file",
              paths(lists, "zorg-growth|v0") == ["Growth/Cart experiments.md", "Growth/Pricing.md"],
              paths(lists, "zorg-growth|v0"))
        check("…the blocks file is dropped under its vault name too", "Growth/_System/context-blocks.md" in sx["blocks_rels"]
              and notes == [], (sx["blocks_rels"], notes))
    with FakeMcp(fail_status=503) as s:
        env.reg("zorg-growth", growth_reg(s.url))
        sx = env.sctx()
        lists, notes = cs_.gather(sx, VARIANTS, cs_.sources(env.text, sx["repos"]), deadline())
        check("an unreachable MCP: one line, the other lists are there",
              notes == ["zorg-growth не відповів — без нього"] and "own|v0" in lists
              and not any(k.startswith("zorg-growth|") for k in lists), (notes, sorted(lists)))
    with FakeMcp(delay=25) as s:
        s.handlers["vault_search"] = search
        env.reg("zorg-growth", growth_reg(s.url))
        sx = env.sctx()
        t0 = time.monotonic()
        lists, notes = cs_.gather(sx, VARIANTS[:1], cs_.sources(env.text, sx["repos"]), deadline())
        took = time.monotonic() - t0
        check("a slow MCP is cut at 20 s: one line, the other lists are there",
              19.0 <= took < 23.0 and notes == ["zorg-growth не відповів — без нього"] and "own|v0" in lists, (took, notes))
    with FakeMcp(delay=25) as s:
        s.handlers["vault_search"] = search
        env.reg("zorg-growth", growth_reg(s.url))
        sx = env.sctx()
        t0 = time.monotonic()
        lists, notes = cs_.gather(sx, VARIANTS[:1], cs_.sources(env.text, sx["repos"]), time.monotonic() + 3)
        took = time.monotonic() - t0
        check("…and at the command's deadline when that comes first", took < 5.0
              and notes == ["zorg-growth не відповів — без нього"], (took, notes))

# ------------------------------------------------------------------ priors
check("a hub weighs half and is marked", (lambda c: (cs_.priors([c], [], None, NOW, {}), c)[1])(cand("a.md", hub=True))
      ["score"] == 0.5)
c = cand("Notes/Zorg Style Guide.md", title="Zorg Style Guide", type="style-guide")
cs_.priors([c], [], None, NOW, {})
check("…a hub by its title when the source said nothing", c["score"] == 0.5 and "хаб" in c["flags"], c)
c = cand("ZorgCore/People/bea-two.md", type="person", hub=None)
cs_.priors([c], [], None, NOW, {})
check("…a hub by its type", c["score"] == 0.5 and c["flags"] == ["хаб"], c)
c = cand("Notes/Checkout flow (old).md", status="outdated", type="concept")
cs_.priors([c], ["concept"], None, NOW, {})
check("outdated by status weighs half, the skill's type 1.2", abs(c["score"] - 0.6) < 1e-9 and c["flags"] == ["застаріле"], c)
for status in ("archived", "deprecated", "former", "superseded", "Outdated"):
    c = cand("x.md", status=status)
    cs_.priors([c], [], None, NOW, {})
    check("status %s is outdated" % status, c["score"] == 0.5 and "застаріле" in c["flags"], c)
c = cand("x.md", type="Requirements")
cs_.priors([c], ["requirements", "concept"], None, NOW, {})
check("the skill's type × 1.2 (any case), no mark", abs(c["score"] - 1.2) < 1e-9 and c["flags"] == [], c)
a, b, n = cand("a.md", product="Zorg App"), cand("b.md", product="Other App"), cand("n.md")
cs_.priors([a, b, n], [], "zorg app", NOW, {})
check("the same product × 1.1, another × 0.7, none as it is", abs(a["score"] - 1.1) < 1e-9
      and abs(b["score"] - 0.7) < 1e-9 and n["score"] == 1.0, (a, b, n))
a = cand("a.md", product="Zorg App")
cs_.priors([a], [], None, NOW, {})
check("…no product asked: no product weight", a["score"] == 1.0, a)
c = cand("a.md", hub=True, status="outdated", type="concept")
cs_.priors([c], ["concept"], None, NOW, {})
cs_.priors([c], ["concept"], None, NOW, {})
check("a second pass never repeats a mark", c["flags"] == ["хаб", "застаріле"], c)

c = cand("g.md", hits=[hit("g.md", lst="own|g0"), hit("g.md", lst="zorg-brain|g1")])
m = cand("m.md", hits=[hit("m.md", lst="own|g0"), hit("m.md", lst="own|v1")])
cs_.priors([c, m], [], None, NOW, {})
check("found only by glossary lists: marked, the score as it is", c["flags"] == ["лише глосарій"] and c["score"] == 1.0
      and m["flags"] == [], (c, m))
one = cand("o.md", hits=[hit("o.md", terms=1, asked=3), hit("o.md", lst="own|v1", terms=1, asked=2)])
two = cand("t.md", hits=[hit("t.md", terms=1, asked=3), hit("t.md", lst="own|v1", terms=2, asked=2)])
solo = cand("s.md", hits=[hit("s.md", terms=1, asked=1)])
unknown = cand("u.md", hits=[hit("u.md", lst="zorg-growth|v0", terms=None, asked=2)])
cs_.priors([one, two, solo, unknown], [], None, NOW, {})
check("one word: the best match held one term of several", one["flags"] == ["одне слово"] and two["flags"] == []
      and solo["flags"] == [] and unknown["flags"] == [], (one, two, solo, unknown))

with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    sx = env.sctx()
    ttl = cs_.class_ttl(sx["repos"], sx["vaults"])
    check("class_ttl: the folder of a class the core's manifest names → its days", ttl == {"ZorgCore/Teams": 14}, ttl)
    check("…without the vaults the folder is named as outside every vault", cs_.class_ttl(sx["repos"])
          == {"@zorg-core/Teams": 14}, cs_.class_ttl(sx["repos"]))
    team = cand("ZorgCore/Teams/team-alpha.md", type="team", date="2026-01-01", ttl_date="2026-01-01")
    fresh = cand("ZorgCore/Teams/team-beta.md", type="team", date="2026-10-10", ttl_date="2026-10-10")
    person = cand("ZorgCore/People/bea-two.md", type="note", date="2025-01-01", ttl_date="2025-01-01")
    created = cand("ZorgCore/Teams/team-gamma.md", type="team", date="2025-01-01", ttl_date="")
    gone = cand("ZorgCore/Teams/team-delta.md", type="team", status="archived", date="2026-01-01", ttl_date="2026-01-01")
    cs_.priors([team, fresh, person, created, gone], [], None, NOW, ttl)
    check("B1: a team card older than its class's 14 days is marked `станом на <its day>`, its score as it is — "
          "never `застаріле`", team["score"] == 1.0 and team["flags"] == ["станом на 2026-01-01"], team)
    check("…a fresh one is not, nor a note of a class with no TTL", fresh["flags"] == [] and person["flags"] == [],
          (fresh, person))
    check("…nor one with no updated | snapshot | generated, however old its date", created["flags"] == []
          and created["score"] == 1.0, created)
    check("…`застаріле` (× 0.5) stays for a status alone, beside the as-of mark", gone["score"] == 0.5
          and gone["flags"] == ["застаріле", "станом на 2026-01-01"], gone)
    write(env.note("ZorgCore/Teams/team-beta.md"), "---\ntype: team\ncreated: 2025-01-01\n---\n# Team Beta\n\nOwns the delivery slots.\n")
    env.refresh(sx)
    found, _ = cs_.gather(sx, ["team owns"], [cs_.Source("own", "own")], deadline())
    cards = {}
    for h in found.get("own|v0", []):
        cards.setdefault(h["path"], dict({k: h.get(k) for k in ("path", "heading", "type", "product", "status", "hub",
                                                                 "title", "date", "ttl_date")},
                                         score=1.0, flags=[], hits=[h]))
    cs_.priors(list(cards.values()), [], None, NOW, ttl)
    alpha, beta = cards.get("ZorgCore/Teams/team-alpha.md"), cards.get("ZorgCore/Teams/team-beta.md")
    check("from the index: the card with an old `updated` is `станом на 2026-01-01`, the one dated only by an old "
          "`created` is not marked", alpha and alpha["flags"] == ["станом на 2026-01-01"] and alpha["score"] == 1.0
          and beta and beta["flags"] == [] and beta["date"] == "2025-01-01", (alpha, beta))
    os.remove(os.path.join(env.vault, "ZorgCore", "_System", "provider-manifest.yaml"))
    check("no manifest: no class TTL", cs_.class_ttl(sx["repos"], sx["vaults"]) == {})

with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    reg = os.path.join(env.providers, "zorg-core.yaml")
    write(reg, read(reg) + "synced_at: 2026-01-01\n")
    sx = env.sctx()
    snaps = cs_.snapshots(sx, NOW)
    check("snapshots: a repository older than stale_after_days → its folder and day", snaps == {"ZorgCore": "2026-01-01"},
          snaps)
    core, own = cand("ZorgCore/Epics/Epic — PROJ-77.md"), cand("Notes/Epics/Epic — PROJ-77.md")
    cs_.priors([core, own], [], None, NOW, {}, snaps)
    check("a candidate of that repository is marked with the snapshot's day, its score as it is",
          core["flags"] == ["знімок від 2026-01-01"] and core["score"] == 1.0 and own["flags"] == [], (core, own))
    write(os.path.join(env.store, ".state", "blocks", "zorg-core.json"),
          json.dumps({"checked": "2026-10-19T09:00:00+03:00"}))
    check("the later of synced_at and the day the store last checked it counts", cs_.snapshots(env.sctx(), NOW) == {},
          cs_.snapshots(env.sctx(), NOW))
    write(os.path.join(env.store, ".state", "blocks", "zorg-core.json"), json.dumps({"checked": "2026-02-01T09:00:00+03:00"}))
    check("…a check later than synced_at but still old is the day shown", cs_.snapshots(env.sctx(), NOW)
          == {"ZorgCore": "2026-02-01"}, cs_.snapshots(env.sctx(), NOW))
    write(reg, read(reg).replace("synced_at: 2026-01-01\n", ""))
    os.remove(os.path.join(env.store, ".state", "blocks", "zorg-core.json"))
    check("no day known: no mark", cs_.snapshots(env.sctx(), NOW) == {})

# ------------------------------------------------------------------ search_types and check 19
check("skill_types: the manifest's search_types", cs_.skill_types("cjm-research")
      == ["cjm-analysis", "cjm-health-check", "funnel-anomaly", "ab-test-results", "hypothesis"], cs_.skill_types("cjm-research"))
check("…write-concept: the main types, not the build-first ones", cs_.skill_types("write-concept")
      == ["competitive-analysis", "market-research", "ux-benchmark", "hypothesis", "decision", "requirements"],
      cs_.skill_types("write-concept"))
check("…a (none …) row is []; an unknown skill or none at all is []", cs_.skill_types("template-library") == []
      and cs_.skill_types("no-such-skill") == [] and cs_.skill_types(None) == [])
check("…context-navigator: the types before the remark", cs_.skill_types("context-navigator")
      == ["decision", "meeting-notes", "knowledge-source"], cs_.skill_types("context-navigator"))
table = cr.skill_context_map()
check("SKILL_CONTEXT_MAP is read for every skill", sorted(table) == sorted(
    n for n in os.listdir(os.path.join(ROOT, "skills")) if os.path.isdir(os.path.join(ROOT, "skills", n))), sorted(table))
check("check 19 is clean on the repo", cr.check_search_types(ROOT) == [], cr.check_search_types(ROOT))
check("check_manifest is clean with search_types", cr.check_manifest(ROOT) == [], cr.check_manifest(ROOT))
MANIFEST = read(ROOT, "references", "context-manifest.yaml")
with tempfile.TemporaryDirectory() as d:
    path = os.path.join(d, "context-manifest.yaml")
    head, tail = MANIFEST.split("  cjm-research:\n", 1)
    body, rest = tail.split("    product:\n", 1)
    write(path, head + "  cjm-research:\n    product:\n" + rest)
    errs = cr.check_search_types(ROOT, manifest_path=path)
    check("check 19 is red on a manifest without search_types in one skill",
          len(errs) == 1 and errs[0].startswith("cjm-research:"), errs)
    write(path, MANIFEST.replace("      - funnel-anomaly\n", "", 1))
    errs = cr.check_search_types(ROOT, manifest_path=path)
    check("…and on one whose types differ from its row", len(errs) == 1 and errs[0].startswith("cjm-research:")
          and "funnel-anomaly" in errs[0], errs)
    write(path, MANIFEST.replace("  template-library:\n    search_types: []\n", "  template-library:\n    search_types:\n      - roadmap\n", 1))
    errs = cr.check_search_types(ROOT, manifest_path=path)
    check("…and on a (none …) row that got types", len(errs) == 1 and errs[0].startswith("template-library:"), errs)
    write(path, MANIFEST.replace("  template-library:\n    search_types: []\n", "  template-library:\n    search_types: roadmap\n", 1))
    errs = cr.check_manifest(ROOT, manifest_path=path)
    check("check_manifest: search_types is a list of names", any(e.startswith("template-library:") and "search_types" in e
                                                                  for e in errs), errs)
    proto = os.path.join(d, "vault-protocol.md")
    write(proto, read(ROOT, "references", "vault-protocol.md").replace(
        "| knowledge-library | knowledge-source |\n", "| knowledge-library | knowledge-source, |\n"))
    check("…an empty item in a row is no type", cr.check_search_types(ROOT, map_path=proto) == [],
          cr.check_search_types(ROOT, map_path=proto))
    write(proto, read(ROOT, "references", "vault-protocol.md").replace(
        "| knowledge-library | knowledge-source |\n", "| knowledge-library | knowledge source |\n"))
    errs = cr.check_search_types(ROOT, map_path=proto)
    check("…a row that is not a list of type names is an error naming the skill",
          len(errs) == 1 and errs[0].startswith("knowledge-library:"), errs)

# ------------------------------------------------------------------ Task 7: without duplicates — the five keys of dedup
def entry(path, heading="", score=1.0, source="own", sid=None, flags=(), **kw):
    """An entry as run hands it to dedup: one (path, heading) of the fused lists, weighed by the priors — its score, its
    marks, the hits that found it and, for an own section, its id."""
    h = cs_.Hit(path, heading, source, 1, section_id=sid, list="%s|v0" % source, terms=None, asked=1)
    e = {"path": path, "heading": heading, "score": score, "flags": list(flags), "hits": [h], "section_id": sid,
         "title": path.rsplit("/", 1)[-1][:-3], "type": "", "product": "", "date": ""}
    e.update(kw)
    return e


def meta_of(path, **kw):
    m = {"path": path, "title": path.rsplit("/", 1)[-1][:-3], "date": "2026-10-01", "confluence_id": "", "hash": path,
         "size": 100, "links": [], "version_key": None, "sensitive": False}
    m.update(kw)
    return m


P = "Notes/Кошик — графік роботи продавця.md"
check("candidate_id: the first 10 hex digits of sha1(path#heading)", cs_.candidate_id(P, "A › B")
      == hashlib.sha1((P + "#A › B").encode("utf-8")).hexdigest()[:10] and len(cs_.candidate_id("a.md", "")) == 10)
out = cs_.dedup([entry(P, "K › Рішення", 0.05, sid=1), entry(P, "K › Проблема", 0.04, sid=2),
                 entry(P, "K › Метрики", 0.03, sid=3), entry(unicodedata.normalize("NFD", P), "", 0.02, source="zorg-brain"),
                 entry("Notes/b.md", "", 0.06, sid=9)], {})
k = next((c for c in out if c["path"] == P), None)
check("key 1: one candidate per file (NFC), whatever the source or the section; best first",
      [c["path"] for c in out] == [P, "Notes/b.md"], [(c["path"], c["score"]) for c in out])
check("…its sources a list, the own index first", k and k["source"] == ["own", "zorg-brain"], k and k["source"])
check("…its heading the best own section; at most two sections of one note",
      k and k["heading"] == "K › Рішення" and [s["heading"] for s in k["sections"]] == ["K › Рішення", "K › Проблема"],
      k and k["sections"])
check("…its score the sum of what it keeps: two sections and the other source's note", k and abs(k["score"] - 0.11) < 1e-9,
      k and k["score"])
g = entry("g.md", "A", 0.02, sid=1, flags=["лише глосарій"])
g["hits"][0]["list"] = "own|g0"
out = cs_.dedup([g, entry("g.md", "B", 0.01, sid=2)], {})
check("…a mark of the hits is the whole note's: found by a variant too, it is not «лише глосарій»", out[0]["flags"] == [],
      out[0]["flags"])
out = cs_.dedup([entry("s.md", "A", 0.02, sid=1, sensitive=True), entry("s.md", "", 0.01, source="zorg-brain")], {})
check("…sensitive when any source says so", out[0].get("sensitive") is True, out[0])

D1, D2 = "Notes/Knowledge/Delivery slots (900100200).md", "ZorgCore/Pages/Delivery slots (900100200).md"
metas = [meta_of(D1, confluence_id="900100200", date="2026-10-05", size=300),
         meta_of(D2, confluence_id="900100200", date="2026-09-01", size=120)]
out = cs_.dedup([entry(D2, "Delivery slots", 0.05, sid=1), entry(D1, "Delivery slots", 0.02, sid=2)], metas)
check("key 2: one Confluence page twice on disk — the newer stays, at the better place, the other named its twin",
      [c["path"] for c in out] == [D1] and out[0]["flags"] == ["двійник " + D2] and abs(out[0]["score"] - 0.05) < 1e-9, out)
M1, M2 = "Notes/Mobile cart notes.md", "Notes/Archive/Mobile cart notes (copy).md"
out = cs_.dedup([entry(M1, "", 0.03, sid=1), entry(M2, "", 0.02, sid=2)],
                {M1: meta_of(M1, hash="h"), M2: meta_of(M2, hash="h")})
check("key 3: the same content twice — the better one stays, the other named its twin",
      [c["path"] for c in out] == [M1] and out[0]["flags"] == ["двійник " + M2], out)
E1, E2 = "Notes/Epics/Epic — PROJ-77.md", "ZorgCore/Epics/Epic — PROJ-77.md"
metas = {E1: meta_of(E1, title="Epic — PROJ-77", links=["epic — proj-77"], size=180, date="2026-10-01"),
         E2: meta_of(E2, title="Epic — PROJ-77", size=640, date="2026-09-28")}
out = cs_.dedup([entry(E1, "", 0.04, sid=1), entry(E2, "Epic — PROJ-77 › Goal", 0.03, sid=2)], metas)
check("key 4: the hub of your layer and the core page it links — the one with more text stays, the other its twin",
      [c["path"] for c in out] == [E2] and out[0]["flags"] == ["двійник " + E1] and abs(out[0]["score"] - 0.04) < 1e-9, out)
metas[E1]["links"] = []
out = cs_.dedup([entry(E1, "", 0.04, sid=1), entry(E2, "Epic — PROJ-77 › Goal", 0.03, sid=2)], metas)
check("…the same title with no link between them is two notes", sorted(c["path"] for c in out) == sorted([E1, E2]), out)
R1, R2, R3 = ("Notes/Roadmap Q4 — draft v1.md", "Notes/Roadmap Q4 — draft v2.md", "Notes/Roadmap Q4 — draft v3.md")
metas = {R2: meta_of(R2, version_key="Notes/roadmap q4", date="2026-09-10"),
         R3: meta_of(R3, version_key="Notes/roadmap q4", date="2026-10-05")}
out = cs_.dedup([entry(R2, "Themes", 0.05, sid=1), entry(R3, "Themes", 0.01, sid=2)], metas)
check("key 5: versions — the newer stays, at the better place, and says how many older ones there are",
      [c["path"] for c in out] == [R3] and out[0]["flags"] == ["є старіші версії: 1"] and abs(out[0]["score"] - 0.05) < 1e-9, out)
metas[R1] = meta_of(R1, version_key="Notes/roadmap q4", date="2026-08-01")
out = cs_.dedup([entry(R2, "Themes", 0.05, sid=1)], metas)
check("…an older version found alone is named the older version of the newest, and its own older ones are counted",
      [c["path"] for c in out] == [R2] and out[0]["flags"] == ["старіша версія " + R3, "є старіші версії: 1"], out)
out = cs_.dedup([entry(D2, "Delivery slots", 0.05, sid=1), entry(D1, "Delivery slots", 0.02, sid=2)],
                [meta_of(D1, confluence_id="900100200", date="2026-10-05"),
                 meta_of(D2, confluence_id="900100200", date="2026-09-01", sensitive=True)])
check("key 2: a folded twin the index calls sensitive leaves the mark on the one that stays",
      [c["path"] for c in out] == [D1] and out[0]["flags"] == ["двійник " + D2, "sensitive"] and out[0]["sensitive"], out)
out = cs_.dedup([entry(R2, "Themes", 0.05, sid=1, sensitive=True), entry(R3, "Themes", 0.01, sid=2)],
                {R2: meta_of(R2, version_key="Notes/roadmap q4", date="2026-09-10"),
                 R3: meta_of(R3, version_key="Notes/roadmap q4", date="2026-10-05")})
check("key 5: an older version its source called sensitive leaves the mark on the newer", [c["path"] for c in out] == [R3]
      and out[0]["flags"] == ["є старіші версії: 1", "sensitive"], out)
S1, S2 = "Notes/Meetings/Standup 2026-10-01.md", "Notes/Meetings/Standup 2026-10-08.md"
out = cs_.dedup([entry(S1, "", 0.02, sid=1), entry(S2, "", 0.01, sid=2)],
                {S1: meta_of(S1, date="2026-10-01"), S2: meta_of(S2, date="2026-10-08")})
check("…a series by date is no set of versions: both stay", [c["path"] for c in out] == [S1, S2], out)

# ------------------------------------------------------------------ Task 7: the snippet
long_text = (("Вступ без потрібних слів. " * 30) + "Показувати графік роботи продавця прямо в кошику мобільного застосунку. "
             + ("Хвіст тексту без них. " * 40))
s = cs_.snippet(long_text, st.query_terms("кошик мобільний"))
check("snippet: a window around the first match, ≤ 300 characters, the matches in «», a cut end marked",
      len(s) <= 300 and s.startswith("…") and s.endswith("…") and "«кошику» «мобільного»" in s, s)
check("…the window starts near the match, not at the text's start", s.find("«кошику»") < 120, s)
check("…a narrower width holds", len(cs_.snippet(long_text, st.query_terms("кошик"), width=60)) <= 60)
check("…no match: the start of the text, whole when it is short", cs_.snippet("Перше речення. Друге.", ["зовсім"])
      == "Перше речення. Друге.")
check("…the lines folded into one", cs_.snippet("Рядок один.\n\n- кошик тут\n", ["кошик"]) == "Рядок один. - «кошик» тут")
check("…a word written decomposed (NFD) is matched", "«Мій»" in cs_.snippet(unicodedata.normalize("NFD", "Це Мій кошик"),
                                                                          st.query_terms("мій")))
check("…a short term matches a whole word only, as the index matched it", cs_.snippet("q4 q42 x", ["q4"]) == "«q4» q42 x")
check("last_path: <home>/.grow-pm/index/last.json", cs_.last_path("/h") == os.path.join("/h", ".grow-pm", "index", "last.json"))

# ------------------------------------------------------------------ Task 7: run, last.json, get
FIELDS = ("id", "path", "heading", "title", "type", "product", "date", "source", "flags", "matched", "snippet", "score")


def damage(idx, table, inside=False):
    """Overwrite the pages of one table of the index (SQLite's dbstat names them); [] when this SQLite has no dbstat."""
    con = sqlite3.connect(idx.db_path)
    try:
        pages = [r[0] for r in con.execute("SELECT pageno FROM dbstat WHERE name = ? AND pagetype = 'leaf'", (table,))]
        size = con.execute("PRAGMA page_size").fetchone()[0]
    except sqlite3.Error:
        pages, size = [], 0
    con.close()
    with open(idx.db_path, "r+b") as f:
        for pg in pages:
            f.seek((pg - 1) * size + (100 if inside else 0))
            f.write(b"\xff" * (size - 200 if inside else size))
    return pages


with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    build_brain(env.brain, env.vault, BRAIN_NOTES)
    sx = env.sctx()
    before_vault = tree(env.vault)
    check("(no index before the first search)", not os.path.exists(os.path.join(env.home, ".grow-pm", "index", "sections.sqlite")))
    res = cs_.run(sx, ["графік роботи продавця", "seller working hours"], now=NOW)
    check("run: candidates, notes, sources, index", {"candidates", "notes", "sources", "index"} <= set(res), sorted(res))
    check("…the index is refreshed first", (res.get("index") or {}).get("files") == 19, res.get("index"))
    check("…the sources asked, each with whether it answered", res["sources"] == [
        {"id": "own", "kind": "own", "answered": True}, {"id": "zorg-brain", "kind": "local", "answered": True}], res["sources"])
    cands = res["candidates"]
    check("…every candidate has its fields", cands and all(set(FIELDS) <= set(c) for c in cands), cands[:1])
    check("…one candidate per file", len({c["path"] for c in cands}) == len(cands), [c["path"] for c in cands])
    k = next((c for c in cands if c["path"] == P), None)
    check("…the note of both sources is one candidate of both, its heading an own section",
          k and k["source"] == ["own", "zorg-brain"] and k["heading"].startswith("Кошик — графік роботи продавця › "), k)
    check("…its id the hash of its path and heading", k and k["id"] == cs_.candidate_id(P, k["heading"]), k)
    check("…its snippet from the section, the matches in «», ≤ 300", k and "«" in k["snippet"] and len(k["snippet"]) <= 300, k)
    check("…the variants that found it, counted from 1", k and k["matched"] == [1, 2], k)
    check("…its title, type, product and date from the own index", k and (k["title"], k["type"], k["product"], k["date"][:10])
          == ("Кошик — графік роботи продавця", "concept", "Zorg App", "2026-09-15"), k)
    gc = next((c for c in cands if c["path"] == "Growth/Cart experiments.md"), None)
    check("…a note only the local index knows: its source, no heading, the snippet the index gave",
          gc and gc["source"] == ["zorg-brain"] and gc["heading"] == "" and "«" in gc["snippet"], gc)
    check("…the scores best first", [c["score"] for c in cands] == sorted((c["score"] for c in cands), reverse=True))
    last = res.get("last") or {}
    check("…the ids of the search for last.json: source, path, heading, kind", k and k["id"] in last
          and all({"source", "path", "heading", "kind"} <= set(v) for v in last.values())
          and last[k["id"]]["kind"] == "own" and gc and last[gc["id"]]["kind"] == "local", last)
    check("…limit", len(cs_.run(sx, ["seller working hours"], limit=2, now=NOW)["candidates"]) == 2)
    stop = cs_.run(sx, ["що і як?"], now=NOW)
    check("…an all-stop query: no candidates, no error", stop["candidates"] == [] and stop["notes"] == []
          and all(s["answered"] for s in stop["sources"]), stop)

    cs_.save_last(env.home, last)
    check("save_last writes <home>/.grow-pm/index/last.json", json.load(open(cs_.last_path(env.home), encoding="utf-8")) == last)
    header, text = cs_.get(sx, k["id"])
    check("get: the provenance line `> [own · <path> › <heading> · <day>]` and the section's text",
          header == "> [own · %s › %s · 2026-09-15]" % (P, k["heading"]) and text.strip()
          and text.strip() in read(env.vault, *P.split("/")), (header, text))
    check("…the second section of the note too", len(k["sections"]) == 2
          and cs_.get(sx, k["sections"][1]["id"])[0].startswith("> [own · %s › " % P), k["sections"])
    hg, tg = cs_.get(sx, gc["id"])
    check("…a note only the local index knows is read from the vault, its type from its frontmatter on the line",
          hg == "> [zorg-brain · Growth/Cart experiments.md · 2026-08-01 · ab-test-results]"
          and "seller's hours" in tg and "type:" not in tg, (hg, tg))
    os.remove(cs_.last_path(env.home))
    check("…an own section no search listed is found in the index by its id", cs_.get(sx, k["id"]) == (header, text))
    ep = cs_.run(sx, ["Epic PROJ-77"], now=NOW)
    core = next((c for c in ep["candidates"] if c["path"] == "ZorgCore/Epics/Epic — PROJ-77.md"), None)
    check("a core page's candidate names its repository as its source", core and core["source"] == ["zorg-core"]
          and ep["last"][core["id"]]["source"] == "zorg-core", core)
    cs_.save_last(env.home, ep["last"])
    check("…and so does its --get line", core and cs_.get(sx, core["id"])[0].startswith(
        "> [zorg-core · ZorgCore/Epics/Epic — PROJ-77.md › "), core and cs_.get(sx, core["id"])[0])
    try:
        cs_.get(sx, "0000000000")
        got = None
    except cs_.GetError as e:
        got = e
    check("…an unknown id: GetError, code 3, one line", got is not None and got.code == 3 and "\n" not in str(got), got)
    check("run, save_last and get write nothing to the vault", tree(env.vault) == before_vault)

    # ---------------------------------------------------------- last.json: merged, trimmed, never a failure
    home2 = os.path.join(d, "home2")
    check("save_last merges: the ids of an earlier search stay", cs_.save_last(home2, {"a": {"path": "1"}}) is None
          and cs_.save_last(home2, {"b": {"path": "2"}}) is None
          and json.load(open(cs_.last_path(home2), encoding="utf-8")) == {"a": {"path": "1"}, "b": {"path": "2"}})
    keep = cs_.LAST_KEEP
    cs_.LAST_KEEP = 3
    try:
        cs_.save_last(home2, {"a": {"path": "1b"}, "c": {}, "d": {}})
    finally:
        cs_.LAST_KEEP = keep
    check("…the newest LAST_KEEP ids stay, an id seen again is new", list(json.load(open(cs_.last_path(home2), encoding="utf-8")))
          == ["a", "c", "d"], json.load(open(cs_.last_path(home2), encoding="utf-8")))
    os.remove(cs_.last_path(home2))
    os.makedirs(cs_.last_path(home2))
    why = cs_.save_last(home2, {"x": {}})
    check("…a save that cannot be done returns why, it raises nothing and leaves no temp file", isinstance(why, str) and why
          and not [n for n in os.listdir(os.path.dirname(cs_.last_path(home2))) if n.endswith(".tmp")], why)
    home3 = os.path.join(d, "home3")
    code = ("import sys; sys.path.insert(0, %r); import ctx_search as cs_\n"
            "bad = [w for w in (cs_.save_last(sys.argv[1], {'%%s-%%d' %% (sys.argv[2], i): {'path': 'x' * 2000}})"
            " for i in range(150)) if w]\nprint(len(bad))\n" % os.path.join(ROOT, "scripts"))
    procs = [subprocess.Popen([sys.executable, "-c", code, home3, str(n)], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              text=True) for n in range(4)]
    outs = [p.communicate(timeout=120) + (p.returncode,) for p in procs]
    check("four writers of last.json at once: none fails, the file parses, no temp file is left",
          all(rc == 0 and so.strip() == "0" for so, se, rc in outs)
          and isinstance(json.load(open(cs_.last_path(home3), encoding="utf-8")), dict)
          and not [n for n in os.listdir(os.path.dirname(cs_.last_path(home3))) if n.endswith(".tmp")],
          [(so.strip(), se[-200:], rc) for so, se, rc in outs])

    # ---------------------------------------------------------- an own index that was not read is no answer
    calls = []
    real_query, real_rebuild = ci.Index.query, ci.Index.rebuild

    def problem_query(note):
        def query(self, expr, limit, *a, **kw):
            self.problem = note
            return []
        return query

    ci.Index.rebuild = lambda self, *a, **kw: calls.append(1) or real_rebuild(self, *a, **kw)
    try:
        ci.Index.query = problem_query(ci.BUSY_NOTE)
        busy = cs_.run(sx, ["графік роботи продавця"], which=("own",), now=NOW)
        both = cs_.run(sx, ["графік роботи продавця"], now=NOW)
        rebuilt_before = len(calls)
        ci.Index.query = problem_query(ci.BROKEN_NOTE % "database disk image is malformed")
        broken = cs_.run(sx, ["графік роботи продавця"], which=("own",), now=NOW)
    finally:
        ci.Index.query, ci.Index.rebuild = real_query, real_rebuild
    check("a busy own index has not answered: its line, no candidates, never a rebuild",
          busy["sources"] == [{"id": "own", "kind": "own", "answered": False}] and ci.BUSY_NOTE in busy["notes"]
          and busy["candidates"] == [] and rebuilt_before == 0, (busy, calls))
    check("…beside zorg-brain, the other source still answers", both["sources"] == [
        {"id": "own", "kind": "own", "answered": False}, {"id": "zorg-brain", "kind": "local", "answered": True}]
          and both["candidates"] and all(c["source"] == ["zorg-brain"] for c in both["candidates"]), both["sources"])
    check("an own index still damaged after its one rebuild has not answered, its line stays",
          broken["sources"] == [{"id": "own", "kind": "own", "answered": False}] and len(calls) == 1
          and any(n.startswith("індекс пошуку не читається (") for n in broken["notes"]), (broken["notes"], calls))

    idx = ci.Index(env.home)
    for table, inside in (("sections_fts_idx", False), ("sections_fts_data", True)):
        ci.Index(env.home).rebuild(sx["roots"], sx["store_rel"], sx["blocks_rels"])
        if not damage(idx, table, inside):
            print("⚠️  skipped: this SQLite has no dbstat — the damaged-index check needs it")
            break
        idx.refresh(sx["roots"], sx["store_rel"], sx["blocks_rels"])
        idx.query(st.fts_or(st.query_terms("кошик")), 5)
        check("(%s damaged: the refresh does not see it, a query does)" % table,
              (idx.problem or "").startswith("індекс пошуку не читається ("), idx.problem)
        res_b = cs_.run(sx, ["графік роботи продавця"], now=NOW)
        check("a damaged index (%s): run rebuilds it once and answers, one line says so" % table,
              any(c["path"] == P for c in res_b["candidates"]) and cs_.REBUILT_NOTE in res_b["notes"]
              and not any(n.startswith("індекс пошуку не читається") for n in res_b["notes"]), res_b["notes"])

with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    NOTE = ("---\ntype: ab-test-results\nupdated: 2026-08-01\n---\n# Cart experiments\n\n## Result\n\n"
            "The mobile cart test lifted the paid orders.\n")
    with FakeMcp(tree={"Growth/Cart experiments.md": NOTE}) as s:
        s.handlers["vault_search"] = lambda args: ([{"path": "Growth/Cart experiments.md", "title": "Cart experiments",
                                                     "updated": "2026-08-01", "snippet": "the «mobile cart» test"}], False)
        env.reg("zorg-growth", growth_reg(s.url))
        sx = env.sctx()
        res = cs_.run(sx, ["mobile cart test"], which=("mcp",), now=NOW)
        c = next((x for x in res["candidates"] if x["path"] == "@zorg-growth/Cart experiments.md"), None)
        check("run, MCP only: the server's note is a candidate of its repository", c and c["source"] == ["zorg-growth"]
              and res["sources"] == [{"id": "zorg-growth", "kind": "mcp", "answered": True}] and res["index"] is None,
              (res["sources"], res["candidates"], res.get("index")))
        cs_.save_last(env.home, res["last"])
        header, text = cs_.get(sx, c["id"])
        check("get of an MCP candidate: vault_get_note, the note's text without its frontmatter",
              header == "> [zorg-growth · @zorg-growth/Cart experiments.md · 2026-08-01 · ab-test-results]"
              and text.startswith("# Cart experiments")
              and "lifted the paid orders" in text and "type:" not in text, (header, text))
        asked = [json.dumps(x.get("body"), ensure_ascii=False) for x in s.seen]
        check("…asked for the path exactly as the server gave it",
              any("vault_get_note" in b and "Growth/Cart experiments.md" in b for b in asked), asked[-2:])
    try:
        cs_.get(sx, c["id"])
        got = None
    except cs_.GetError as e:
        got = e
    check("…a server that does not answer: GetError, code 5, naming the repository", got is not None and got.code == 5
          and "zorg-growth" in str(got), got)
    with FakeMcp(fail_status=503) as s:
        env.reg("zorg-growth", growth_reg(s.url))
        res = cs_.run(env.sctx(), ["mobile cart test"], which=("mcp",), now=NOW)
        check("run: a source that does not answer is marked so, with its line", res["sources"] == [
            {"id": "zorg-growth", "kind": "mcp", "answered": False}] and res["notes"] == ["zorg-growth не відповів — без нього"]
              and res["candidates"] == [], res)

# ------------------------------------------------------------------ final review fix wave
BUILDING = "індекс пошуку ще будується (інший процес) — цього разу без нього"
Q = ["графік роботи продавця"]
OWN_UNREAD = [{"id": "own", "kind": "own", "answered": False}]
COUNTS0 = {"files": 0, "sections": 0, "pending": 0, "skipped_dataless": 0}


def index_file(home, name=""):
    return os.path.join(home, ".grow-pm", "index", *([name] if name else []))


def hold_lock(home):
    """index.lock as a live process holds it: this test's own pid, now."""
    write(index_file(home, "index.lock"), json.dumps({"pid": os.getpid(), "at": time.time()}))


def ddl_db(home):
    """A sections.sqlite with the schema's tables only (ctx_index.DDL): no meta row yet, as a first build has it."""
    os.makedirs(index_file(home), exist_ok=True)
    con = sqlite3.connect(index_file(home, "sections.sqlite"))
    con.executescript(ci.DDL)
    con.commit()
    con.close()


def unread(res, line):
    return res["sources"] == OWN_UNREAD and res["candidates"] == [] and line in res["notes"]


# C1: an own index that does not exist yet, or that another process is building, has not answered
with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    sx = env.sctx()
    hold_lock(env.home)
    a = cs_.run(sx, Q, which=("own",), now=NOW)
    check("C1: no index yet while another process holds its lock: own has not answered, the building line, index.locked",
          unread(a, BUILDING) and (a["index"] or {}).get("locked") is True
          and {k: (a["index"] or {}).get(k) for k in COUNTS0} == COUNTS0, (a["sources"], a["notes"], a["index"]))
    ddl_db(env.home)
    write(index_file(env.home, "index.json"), json.dumps({"schema": ci.SCHEMA, "updated": "2026-01-02T09:00:00+02:00",
                                                          "files": 19, "sections": 60, "pending": 0, "skipped_dataless": 0}))
    b = cs_.run(sx, Q, which=("own",), now=NOW)
    check("…a database still being filled (no `updated` in its meta) beside an old index.json: not answered, and the index's "
          "day is the database's own (none), not the old one", unread(b, BUILDING) and b["index"]["updated"] is None
          and b["index"]["files"] == 0, (b["notes"], b["index"]))
    os.remove(index_file(env.home, "index.lock"))
    c = cs_.run(sx, Q, which=("own",), now=NOW)
    check("…the lock gone, this search builds the index and answers", c["sources"] == [{"id": "own", "kind": "own", "answered": True}]
          and any(x["path"] == P for x in c["candidates"]) and BUILDING not in c["notes"], (c["sources"], c["notes"]))

with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    sx = env.sctx()
    write(index_file(env.home), "not a folder\n")       # <home>/.grow-pm/index is a file: the refresh cannot make the folder
    e = cs_.run(sx, Q, which=("own",), now=NOW)
    gone = [n for n in e["notes"] if n.startswith("індексу пошуку ще немає (") and n.endswith(") — ctx index rebuild")]
    check("C1: a refresh that cannot make the index's folder: own has not answered, one line «індексу пошуку ще немає (<why>) — "
          "ctx index rebuild», never «пошук по тому, що є»", e["sources"] == OWN_UNREAD and e["candidates"] == []
          and len(gone) == 1 and not any(n.startswith("індекс пошуку не оновлено") for n in e["notes"]), e["notes"])

with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    sx = env.sctx()
    env.refresh(sx)
    hold_lock(env.home)
    real_query, seen = ci.Index.query, []

    def broken_once(self, expr, limit, *a, **kw):
        seen.append(expr)
        if len(seen) == 1:
            self.problem = ci.BROKEN_NOTE % "database disk image is malformed"
            return []
        return real_query(self, expr, limit, *a, **kw)

    def busy_query(self, expr, limit, *a, **kw):
        self.problem = ci.BUSY_NOTE
        return []

    ci.Index.query = broken_once
    try:
        r = cs_.run(sx, Q, which=("own",), now=NOW)
    finally:
        ci.Index.query = real_query
    check("129: a damaged index whose rebuild another process's lock refused: never «збудовано наново», the building line, "
          "own has not answered", cs_.REBUILT_NOTE not in r["notes"] and BUILDING in r["notes"] and r["sources"] == OWN_UNREAD
          and r["index"]["locked"] is True and r["index"]["rebuilt"] is False, (r["notes"], r["index"]))
    os.remove(index_file(env.home, "index.json"))
    ci.Index.query = busy_query
    try:
        r = cs_.run(sx, Q, which=("own",), now=NOW)
    finally:
        ci.Index.query = real_query
    check("137: own busy and no index.json: the counts of `index` are 0, never None", ci.BUSY_NOTE in r["notes"]
          and {k: r["index"].get(k) for k in COUNTS0} == COUNTS0, r["index"])
    os.remove(index_file(env.home, "index.lock"))
    calls, real_refresh = [], ci.Index.refresh
    ci.Index.refresh = lambda self, *a, **kw: calls.append(1) or real_refresh(self, *a, **kw)
    try:
        r = cs_.run(sx, Q, which=("own",), now=NOW, refresh=False)
    finally:
        ci.Index.refresh = real_refresh
    check("154: run(refresh=False) reads the index as it is, without a refresh", calls == []
          and r["sources"] == [{"id": "own", "kind": "own", "answered": True}] and any(x["path"] == P for x in r["candidates"])
          and (r["index"]["added"], r["index"]["locked"]) == (0, False), (calls, r["sources"], r["index"]))

# the own index counts the terms a hit holds as the index matched it — never by stemming a whole long section
with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    write(env.note("Notes/Long note.md"), "# Long note\n\n## Body\n\nzebrafish comes first. " + "lorem ipsum dolor sit amet " * 250
          + "and quokkaland only at the end.\n")
    sx = env.sctx()
    env.refresh(sx)
    lens, real_stem_text = [], cs_.st.stem_text
    cs_.st.stem_text = lambda text: lens.append(len(text or "")) or real_stem_text(text)
    try:
        lists, notes = cs_.gather(sx, ["zebrafish quokkaland"], [{"id": "own", "kind": "own"}], deadline())
    finally:
        cs_.st.stem_text = real_stem_text
    long_hit = next((h for h in lists.get("own|v0", []) if h["path"] == "Notes/Long note.md"), None)
    check("_own: a section of ~7 000 characters holds both terms (the second at its end), counted without stemming it",
          long_hit and long_hit["terms"] == 2 and long_hit["asked"] == 2 and max(lens or [0]) <= 2000,
          (long_hit and long_hit["terms"], max(lens or [0])))

# I1: --get of a note a local index or a server gave says what its frontmatter says
with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    write(env.note("Growth/Bea Two — 1-1.md"), "---\ntype: Person\nstatus: Archived\nsensitive: yes\nupdated: 2026-07-01\n---\n"
          "# Bea Two\n\nNotes of the last 1-1.\n")
    write(env.note("Growth/Plain.md"), "# Plain\n\nNothing marked here.\n")
    sx = env.sctx()
    cs_.save_last(env.home, {
        "aaaaaaaaaa": {"source": "zorg-brain", "path": "Growth/Bea Two — 1-1.md", "heading": "", "kind": "local",
                       "title": "Bea Two", "date": "2026-07-01"},
        "bbbbbbbbbb": {"source": "zorg-brain", "path": "Growth/Plain.md", "heading": "", "kind": "local", "title": "Plain",
                       "date": "2026-07-02"}})
    h1, t1 = cs_.get(sx, "aaaaaaaaaa")
    check("I1: --get of a local note: ` · sensitive`, ` · застаріле` (its status) and its type on the provenance line",
          h1 == "> [zorg-brain · Growth/Bea Two — 1-1.md · 2026-07-01 · sensitive · застаріле · person]"
          and "Notes of the last 1-1." in t1, h1)
    check("…a note whose frontmatter says none of it: the line as it was",
          cs_.get(sx, "bbbbbbbbbb")[0] == "> [zorg-brain · Growth/Plain.md · 2026-07-02]", cs_.get(sx, "bbbbbbbbbb")[0])
    OLD = "# Old sync\n\nThe old sync notes.\n"
    with FakeMcp(tree={"Growth/Old sync.md": OLD}) as s:
        s.handlers["vault_get_note"] = lambda args: ({
            "path": args.get("path"), "title": "Old sync", "tags": [], "headings": [], "content": OLD, "outgoing_links": [],
            "frontmatter": {"sensitive": True, "status": "Superseded", "type": "Meeting", "updated": "2026-06-01"}}, False)
        env.reg("zorg-growth", growth_reg(s.url))
        sx = env.sctx()
        cs_.save_last(env.home, {"cccccccccc": {"source": "zorg-growth", "path": "@zorg-growth/Old sync.md", "heading": "",
                                                "kind": "mcp", "title": "Old sync", "date": "", "remote": "Growth/Old sync.md"}})
        h3, t3 = cs_.get(sx, "cccccccccc")
    check("…of a server's note, from vault_get_note's frontmatter", h3 ==
          "> [zorg-growth · @zorg-growth/Old sync.md · 2026-06-01 · sensitive · застаріле · meeting]" and "old sync notes" in t3, h3)

# ------------------------------------------------------------------ acceptance fix wave
CRUMB = "↑ [[Delivery (900100100)|Delivery]]  ·  `Zorg / Delivery / Slot rules`"
SLOTS = "Notes/Knowledge/Slot rules (900100300).md"
WHO = "A shopper sees the two-hour slots of a seller who is open. " * 12
CLOSED = "The slots of a closed seller are hidden until it opens again. " * 20
SLOT_PAGE = ("---\ntype: page\nconfluence_id: 900100300\nmodified: 2026-10-05\n---\n" + CRUMB + "\n\n# Slot rules\n\n"
             "![[slot-diagram.png]]\n\n## Who sees a slot\n\n" + WHO + "\n\n## Closed sellers\n\n" + CLOSED + "\n\n"
             "## Appendix\n\n" + "Tail text that is never reached. " * 10 + "\n")
SHORT = "секція коротка — додано наступні: Slot rules › Who sees a slot · Slot rules › Closed sellers"

# A1: a Confluence-like page — its breadcrumb is a section of its own (Q1); --get of a short section goes on
with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    write(env.note(SLOTS), SLOT_PAGE)
    sx = env.sctx()
    env.refresh(sx)
    idx = ci.Index(env.home)
    secs = [(sid, h) for sid, p, h in idx.headings() if p == SLOTS]
    check("Q1: the breadcrumb before the H1 is a section of its own, and so is the image-only H1 section", [h for _, h in secs]
          == ["", "Slot rules", "Slot rules › Who sees a slot", "Slot rules › Closed sellers", "Slot rules › Appendix"], secs)
    hc, tc = cs_.get(sx, cs_.candidate_id(SLOTS, ""))
    check("Q1: --get of the breadcrumb goes on with the sections after it, up to 1 500, under its provenance line",
          hc == "> [own · %s · 2026-10-05]" % SLOTS and tc.startswith(CRUMB) and "секція коротка — додано наступні: Slot rules · "
          "Slot rules › Who sees a slot · Slot rules › Closed sellers" in tc and WHO.strip() in tc and "Tail text" not in tc,
          (hc, tc[:400]))
    res = cs_.run(sx, ["Delivery"], which=("own",), now=NOW)
    sl = next((c for c in res["candidates"] if c["path"] == SLOTS), None)
    check("Q2: a candidate whose best section is the breadcrumb takes its snippet from the sections after it — never the "
          "breadcrumb", sl and sl["heading"] == "" and sl["snippet"].startswith("A shopper sees the two-hour slots")
          and not any(x in sl["snippet"] for x in ("↑", "[[", "Zorg / ")), sl)
    res = cs_.run(sx, ["slot rules"], which=("own",), now=NOW)
    sl = next((c for c in res["candidates"] if c["path"] == SLOTS), None)
    check("Q2: …an image-only best section too: the snippet is the first real text, its match marked", sl
          and "«slots»" in sl["snippet"] and not any(x in sl["snippet"] for x in ("↑", "[[", "slot-diagram")), sl)
    top = cs_.candidate_id(SLOTS, "Slot rules")
    head, text = cs_.get(sx, top)
    check("A1: --get of a section under 200 characters goes on with the next ones up to 1 500, under the same "
          "provenance line, with one line naming them", head == "> [own · %s › Slot rules · 2026-10-05]" % SLOTS
          and text.startswith("![[slot-diagram.png]]") and SHORT in text and WHO.strip() in text and CLOSED.strip() in text
          and "Tail text" not in text and text.count("секція коротка") == 1, (head, text[:400]))
    marks = (SHORT, "## Who sees a slot\n\n", "## Closed sellers\n\n")
    check("…each added section under its heading, in the note's order", all(m in text for m in marks)
          and text.index(marks[0]) < text.index(marks[1]) < text.index(marks[2]), text[:600])
    head2, text2 = cs_.get(sx, cs_.candidate_id(SLOTS, "Slot rules › Who sees a slot"))
    check("…a section of 200 characters or more is given as it is", text2.strip() == WHO.strip() and "секція коротка" not in text2,
          text2[:200])
    head3, text3 = cs_.get(sx, cs_.candidate_id(SLOTS, "Slot rules › Appendix"))
    check("…a short last section has nothing to add: as it is, no line", "секція коротка" not in text3, text3)
    cs_.save_last(env.home, {top: {"source": "own", "path": SLOTS, "heading": "Slot rules", "kind": "own",
                                   "section_id": 999999, "title": "Slot rules", "date": "2026-10-05"}})
    head4, text4 = cs_.get(sx, top)
    check("…read from its file (the index's section gone): the same text", (head4, text4) == (head, text), text4[:300])

    # A2: --get never reads a file iCloud has not downloaded; every other read is time-budgeted
    reads, real_read, real_dataless = [], cs_.cst.read_text, ci.is_dataless
    cs_.cst.read_text = lambda p, *a, **kw: reads.append(p) or real_read(p, *a, **kw)
    ci.is_dataless = lambda p: unicodedata.normalize("NFC", p).endswith("Slot rules (900100300).md")
    try:
        try:
            cs_.get(sx, top)
            got = None
        except cs_.GetError as e:
            got = e
        check("A2: a dataless file with no local index: exit 3 and the one line, the file never opened", got is not None
              and got.code == 3 and str(got) == "файл не завантажено з iCloud: %s — відкрий його в Obsidian або ctx index "
              "rebuild --download" % SLOTS and reads == [], (got, reads))
        build_brain(env.brain, env.vault, [SLOTS])
        reads[:] = []
        head5, text5 = cs_.get(sx, top)
        check("A2: …with a registered local index that holds it: its text from there, said in one line",
              head5 == head and text5.startswith("файл не завантажено з iCloud — текст із локального індексу zorg-brain\n\n")
              and "![[slot-diagram.png]]" in text5 and SHORT in text5 and reads == [], (head5, text5[:300], reads))
        gone = "aaaaaaaaaa"
        cs_.save_last(env.home, {gone: {"source": "own", "path": SLOTS, "heading": "Slot rules › Gone section",
                                        "kind": "own", "section_id": 999999, "title": "Slot rules", "date": "2026-10-05"}})
        try:
            head6, text6 = cs_.get(sx, gone)
        except cs_.GetError as e:
            head6, text6 = None, "GetError %d: %s" % (e.code, e)
        check("R3: …the local copy has no such section: the whole note from it, under the same line, never «no section»",
              head6 and text6.startswith("файл не завантажено з iCloud — текст із локального індексу zorg-brain\n\n")
              and "![[slot-diagram.png]]" in text6 and WHO.strip() in text6 and "Tail text" in text6
              and "modified:" not in text6 and reads == [], (head6, text6[:300]))
        build_brain(env.brain, env.vault, [SLOTS], form="s10")
        head7, text7 = cs_.get(sx, top)
        check("R8: …the local index in the §10 shape (notes_fts.rowid = notes.id) gives it the same way",
              (head7, text7) == (head5, text5) and reads == [], (head7, text7[:300]))
    finally:
        cs_.cst.read_text, ci.is_dataless = real_read, real_dataless
    real_open, old_timeout = cs_.cst.__dict__.get("open"), os.environ.get("GROW_PM_CTX_READ_TIMEOUT")
    cs_.cst.open = lambda *a, **kw: (time.sleep(3), open(*a, **kw))[1]
    os.environ["GROW_PM_CTX_READ_TIMEOUT"] = "0.3"
    t0 = time.monotonic()
    try:
        try:
            cs_.get(sx, top)
            got = None
        except cs_.GetError as e:
            got = e
    finally:
        if real_open is None:
            del cs_.cst.open
        else:
            cs_.cst.open = real_open
        if old_timeout is None:
            os.environ.pop("GROW_PM_CTX_READ_TIMEOUT", None)
        else:
            os.environ["GROW_PM_CTX_READ_TIMEOUT"] = old_timeout
    took = time.monotonic() - t0
    check("A2: a file that does not arrive within the read budget is one line (exit 3), never a hang", got is not None
          and got.code == 3 and "\n" not in str(got) and SLOTS in str(got) and took < 2.0, (got, took))

# Q2: a local index's or a server's snippet never shows the breadcrumb
with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    LOCAL_SLOTS = "Growth/Slot rules (900100300).md"
    write(env.note(LOCAL_SLOTS), SLOT_PAGE)
    build_brain(env.brain, env.vault, [LOCAL_SLOTS])
    sx = env.sctx()
    res = cs_.run(sx, ["Delivery"], which=("local",), now=NOW)
    sl = next((c for c in res["candidates"] if c["path"] == LOCAL_SLOTS), None)
    check("Q2: a local hit whose snippet would be the breadcrumb: the text after it", sl and sl["snippet"]
          and not any(x in sl["snippet"] for x in ("↑", "[[", "Zorg / ")) and "two-hour slots" in sl["snippet"], sl)
    mcp_c = {"path": "@zorg-growth/Slot rules.md", "heading": "", "title": "Slot rules", "text": None, "source": ["zorg-growth"],
             "flags": [], "hits": [], "score": 1.0, "sections": [{"heading": "", "section_id": None}],
             "snippet": "…" + CRUMB + "\n\nThe slots of a closed seller are hidden."}
    check("Q2: …a server's snippet loses its breadcrumb lines", cs_._public(mcp_c, [])["snippet"]
          == "The slots of a closed seller are hidden.", cs_._public(mcp_c, [])["snippet"])

# S1: a local hit keeps the index's window when its match is in the text — only a match that lived in link-only lines
# (a breadcrumb) gives the note's opening
with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    PRICING = "Growth/Pricing notes.md"
    INTRO = "The pricing team met to talk about many unrelated topics of the quarter, one after another. " * 4
    write(env.note(PRICING), "# Pricing notes\n\n" + INTRO + "\n\n---\n\n## Decisions\n\n"
          "We chose the zebrafish commission for small sellers.\n\n---\n\nMore text later.\n")
    build_brain(env.brain, env.vault, [PRICING])
    sx = env.sctx()
    res = cs_.run(sx, ["zebrafish"], which=("local",), now=NOW)
    pn = next((c for c in res["candidates"] if c["path"] == PRICING), None)
    check("S1: a match in `## Decisions` beside a `---` rule keeps the index's window, the match marked, the rule gone",
          pn and "«zebrafish» commission" in pn["snippet"] and "---" not in pn["snippet"], pn)

# S2: the snippet and --get of a short section ask the index only for what the fill needs
with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    BIG = "Notes/Knowledge/Big page (900100400).md"
    write(env.note(BIG), CRUMB + "\n\n# Big page\n\n" + "".join("## Part %02d\n\n%s\n\n" % (i, "w" * 500) for i in range(40)))
    sx = env.sctx()
    env.refresh(sx)
    got, real_following = [], ci.Index.following
    ci.Index.following = lambda self, *a, **kw: (lambda out: got.append(len(out)) or out)(real_following(self, *a, **kw))
    try:
        hb, tb = cs_.get(sx, cs_.candidate_id(BIG, ""))
        got_get, got[:] = list(got), []
        res = cs_.run(sx, ["Delivery"], which=("own",), now=NOW)
    finally:
        ci.Index.following = real_following
    big = next((c for c in res["candidates"] if c["path"] == BIG), None)
    check("S2: --get of a breadcrumb before 40 long sections reads 3 of them — 1 500 characters — and gives the same fill",
          got_get == [3] and "секція коротка — додано наступні: Big page › Part 00 · Big page › Part 01 · "
          "Big page › Part 02" in tb and "Part 03" not in tb, (got_get, tb[:200]))
    check("…and so does the snippet of a search whose best section is that breadcrumb", big and big["heading"] == ""
          and got and max(got) == 3 and big["snippet"].startswith("w" * 20), (got, big))

# A3: a local hit with no date in its frontmatter takes the local index's file time, as a day
with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    UNDATED = "Growth/Zebrafish idea.md"
    write(env.note(UNDATED), "# Zebrafish idea\n\nA zebrafish mascot next to the mobile cart.\n")
    MT = 1760000000.0
    DAY = datetime.date.fromtimestamp(MT).isoformat()
    sx = env.sctx()
    brain_src = [cs_.Source("zorg-brain", "local", path=env.brain)]
    for form in ("wild", "s10"):
        build_brain(env.brain, env.vault, [UNDATED, "Notes/Mobile cart notes.md"], form=form,
                    mtimes={UNDATED: MT, "Notes/Mobile cart notes.md": MT})
        found, _ = cs_.gather(sx, ["zebrafish", "mobile cart"], brain_src, deadline())
        z = next((h for h in found.get("zorg-brain|v0", []) if h["path"] == UNDATED), None)
        mc = next((h for h in found.get("zorg-brain|v1", []) if h["path"] == "Notes/Mobile cart notes.md"), None)
        check("A3 (%s shape): no date in the frontmatter — the day of notes.mtime" % form, z and z["date"] == DAY, z)
        check("…a frontmatter date stays the date (%s shape)" % form, mc and mc["date"] == "2026-07-02", mc)
    con = sqlite3.connect(env.brain)
    con.executescript("DROP TABLE notes; DROP TABLE notes_fts; DROP TABLE meta;"
                      "CREATE TABLE notes(path TEXT PRIMARY KEY, title TEXT, type TEXT, date TEXT, status TEXT, fm_json TEXT);"
                      "CREATE VIRTUAL TABLE notes_fts USING fts5(path UNINDEXED, title, body);"
                      "CREATE TABLE meta(k TEXT PRIMARY KEY, v TEXT);")
    con.execute("INSERT INTO meta VALUES ('vault', ?)", (env.vault,))
    con.execute("INSERT INTO notes(path, title, date) VALUES (?, 'Zebrafish idea', '2026-03-04')", (UNDATED,))
    con.execute("INSERT INTO notes_fts(path, title, body) VALUES (?, 'Zebrafish idea', 'A zebrafish mascot.')", (UNDATED,))
    con.commit()
    con.close()
    found, _ = cs_.gather(sx, ["zebrafish"], brain_src, deadline())
    z = next((h for h in found.get("zorg-brain|v0", []) if h["path"] == UNDATED), None)
    check("A3: …a notes table with no mtime: its date column", z and z["date"] == "2026-03-04", z)

# A5: near copies — the same text but for a back-link line, a date line, a «Повʼязане» block, the frontmatter
STUDY = "The cart shows the seller's working hours under each block, so a shopper knows when the order moves. " * 5
COPY_A = ("---\ntype: research\nupdated: 2026-10-01\n---\n# Cart study\n\n" + STUDY + "\n\n## Findings\n\n"
          "Shoppers wait less when they see the hours.\n\n## Повʼязане\n\n- [[Cart MOC]]\n- [[Seller hours]]\n")
COPY_B = ("# Cart study\n\nUp:: [[Research MOC]]\n2026-10-07\n\n" + STUDY + "\n\n## Findings\n\n"
          "Shoppers wait less when they see the hours.\n\nRelated:\n- [[Cart MOC]] — the map of the cart\n")
N1, N2, C1 = "Notes/Knowledge/sources/Cart study.md", "Growth/Cart study.md", "ZorgCore/Pages/Cart study.md"
out = cs_.dedup([entry(N1, "", 0.02, source="zorg-brain", near="k1", date="2026-09-01"),
                 entry(N2, "", 0.05, source="zorg-brain", near="k1", date="2026-10-07")], {}, own=["Notes"])
check("R4 dedup: your layer is where the path lies — a plugin-folder copy only the local index found beats a newer one",
      [c["path"] for c in out] == [N1] and out[0]["flags"] == ["двійник " + N2], out)
out = cs_.dedup([entry(N1, "", 0.02, source="zorg-brain", near="k1", date="2026-09-01"),
                 entry(N2, "", 0.05, source="zorg-brain", near="k1", date="2026-10-07")], {}, own=[""])
check("Q3: …a plugin folder that is the whole vault holds both: the older (the original) stays", [c["path"] for c in out] == [N1]
      and out[0]["flags"] == ["двійник " + N2], out)
N3, N4 = "Notes/Research/Cart study.md", "Archive/Cart study.md"
out = cs_.dedup([entry(N1, "", 0.05, source="zorg-brain", near="k1", date="2026-10-01"),
                 entry(N3, "", 0.01, source="zorg-brain", near="k1", date="2026-09-01"),
                 entry(N4, "", 0.03, source="zorg-brain", near="k1", date="2026-01-01")], {}, own=["Notes"])
check("Q3: your layer first, and within it the older copy — an older one elsewhere does not win",
      [c["path"] for c in out] == [N3] and out[0]["flags"] == ["двійник " + N1, "двійник " + N4]
      and abs(out[0]["score"] - 0.05) < 1e-9, out)
out = cs_.dedup([entry(N2, "", 0.05, source="zorg-brain", near="k1", date=""),
                 entry(N4, "", 0.01, source="zorg-brain", near="k1", date="2026-10-07")], {}, own=["Notes"])
check("Q3: a copy with no date never wins over a dated one", [c["path"] for c in out] == [N4], out)
out = cs_.dedup([entry(N2, "", 0.01, source="zorg-brain", near="k1", date="2026-10-07"),
                 entry(N4, "", 0.05, source="zorg-brain", near="k1", date="2026-10-07")], {}, own=["Notes"])
check("Q3: the same date: the higher score stays", [c["path"] for c in out] == [N4], out)
out = cs_.dedup([entry(N2, "", 0.05, source="zorg-brain", near="k1", date="2026-10-07"),
                 entry(N1, "Cart study", 0.02, sid=1)], {N1: meta_of(N1, near="k1", date="2026-09-01")})
check("A5 dedup: near copies fold — your layer's copy stays, though older and lower, the other its twin",
      [c["path"] for c in out] == [N1] and out[0]["flags"] == ["двійник " + N2] and abs(out[0]["score"] - 0.05) < 1e-9, out)
out = cs_.dedup([entry(C1, "Cart study", 0.05, source="zorg-core", sid=2),
                 entry(N2, "", 0.02, source="zorg-brain", near="k1", date="2026-10-07")],
                {C1: meta_of(C1, near="k1", date="2026-09-01")})
check("Q3: …neither in your layer: the older by date stays", [c["path"] for c in out] == [C1]
      and out[0]["flags"] == ["двійник " + N2], out)
out = cs_.dedup([entry(N1, "Cart study", 0.05, sid=1), entry(N2, "", 0.02, source="zorg-brain", near="k1", sensitive=True)],
                {N1: meta_of(N1, near="k1")})
check("…a folded copy that is sensitive leaves the mark", [c["path"] for c in out] == [N1]
      and out[0]["flags"] == ["двійник " + N2, "sensitive"], out)
out = cs_.dedup([entry(N1, "Cart study", 0.05, sid=1), entry(N2, "", 0.02, source="zorg-brain", near=None)],
                {N1: meta_of(N1, near=None)})
check("…no key (a short note) never folds", sorted(c["path"] for c in out) == sorted([N1, N2]), out)
with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    write(env.note(N1), COPY_A)
    write(env.note(N2), COPY_B)
    write(env.note("Notes/Short a.md"), "# Short a\n\nThe zebra cart rule in one line.\n")
    write(env.note("Notes/Short b.md"), "# Short b\n\n↑ [[Zorg MOC]]\nThe zebra cart rule in one line.\n")
    build_brain(env.brain, env.vault, [N2])
    sx = env.sctx()
    res = cs_.run(sx, ["seller working hours cart study"], now=NOW)
    got = {c["path"]: c for c in res["candidates"]}
    check("A5 run: a copy only the local index knows folds into your layer's copy, named its twin",
          N1 in got and N2 not in got and "двійник " + N2 in got[N1]["flags"], [(c["path"], c["flags"]) for c in res["candidates"]])
    write(env.note(N2), "---\nupdated: 2026-10-15\n---\n" + COPY_B)
    build_brain(env.brain, env.vault, [N1, N2])
    res = cs_.run(sx, ["seller working hours cart study"], which=("local",), now=NOW)
    got = {c["path"]: c for c in res["candidates"]}
    check("R4 run: the local index alone found both — the plugin-folder copy stays, though older, the other its twin",
          N1 in got and N2 not in got and "двійник " + N2 in got[N1]["flags"] and got[N1]["source"] == ["zorg-brain"],
          [(c["path"], c["source"], c["flags"]) for c in res["candidates"]])
    res = cs_.run(sx, ["zebra cart rule"], now=NOW)
    check("A5 run: two short notes with the same words never fold", {"Notes/Short a.md", "Notes/Short b.md"}
          <= {c["path"] for c in res["candidates"]}, [(c["path"], c["flags"]) for c in res["candidates"]])

# T1/T3 (fix round 4): --get takes a note's path too — a twin, a newer version, a note a hub links to can be read
with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    build_brain(env.brain, env.vault, BRAIN_NOTES)
    write(env.note("Growth/Only on disk.md"), "---\ntype: note\nupdated: 2026-10-02\n---\n# Only on disk\n\nA zebra note no index holds.\n")
    sx = env.sctx()
    env.refresh(sx)
    D2 = "ZorgCore/Pages/Delivery slots (900100200).md"
    reads, real_read, real_dataless = [], cs_.cst.read_text, ci.is_dataless
    cs_.cst.read_text = lambda p_, *a, **kw: reads.append(p_) or real_read(p_, *a, **kw)
    try:
        def get_or(code_of, arg):
            try:
                return cs_.get(sx, arg)
            except cs_.GetError as e:
                code_of.append(e.code)
                return None, str(e)
        h1, t1 = cs_.get(sx, D2)
        check("T1: --get <a twin's path> gives the whole note from the own index, its provenance and its marks, no file read",
              h1 == "> [zorg-core · %s · 2026-09-01 · page]" % D2 and t1.startswith("# Delivery slots\n\n")
              and "Shoppers pick a two-hour delivery slot at checkout." in t1 and "confluence_id" not in t1 and reads == [],
              (h1, t1, reads))
        h1n, t1n = cs_.get(sx, unicodedata.normalize("NFD", P))
        check("…a path written decomposed (NFD) is the same note", h1n.startswith("> [own · %s · 2026-09-15" % P)
              and "## Рішення" in t1n and reads == [], (h1n, t1n[:200]))
        h2, t2 = cs_.get(sx, "Growth/Cart experiments.md")
        check("T1/U7: …a path only a local index knows, its file on disk and downloaded: the file first (one budgeted read), "
              "its source the root it lies under — `vault` outside every root",
              h2 == "> [vault · Growth/Cart experiments.md · 2026-08-01 · ab-test-results]"
              and "seller's hours under each block" in t2 and "type:" not in t2 and len(reads) == 1
              and reads[0].endswith("Cart experiments.md"), (h2, t2, reads))
        reads[:] = []
        h3, t3 = cs_.get(sx, "Growth/Only on disk.md")
        check("T1: …a path no index holds: the file, through the time-budgeted reader",
              h3 == "> [vault · Growth/Only on disk.md · 2026-10-02 · note]" and "A zebra note no index holds." in t3
              and len(reads) == 1 and reads[0].endswith("Only on disk.md"), (h3, t3, reads))
        reads[:] = []
        ci.is_dataless = lambda p_: unicodedata.normalize("NFC", p_).endswith(("Cart experiments.md", "Only on disk.md"))
        h4, t4 = cs_.get(sx, "Growth/Cart experiments.md")
        check("T1: …a dataless file a local index holds: the ICLOUD_LOCAL line, then its text; the file never opened",
              t4.startswith("файл не завантажено з iCloud — текст із локального індексу zorg-brain\n\n")
              and "seller's hours under each block" in t4 and reads == [], (h4, t4, reads))
        codes = []
        h5, t5 = get_or(codes, "Growth/Only on disk.md")
        check("T1: …a dataless file nothing else holds: exit 3, ICLOUD_MISSING, the file never opened",
              codes == [3] and t5 == getattr(cs_, "ICLOUD_OPEN", "-") % "Growth/Only on disk.md" and reads == [], (codes, t5, reads))
    finally:
        cs_.cst.read_text, ci.is_dataless = real_read, real_dataless
    codes = []
    h6, t6 = get_or(codes, "Notes/No such note.md")
    check("T1: …an unknown path: exit 3, one line naming it", codes == [3] and "Notes/No such note.md" in t6 and "\n" not in t6,
          (codes, t6))
    sid = next(s_ for s_, p_, h_ in ci.Index(env.home).headings() if p_ == P and h_.endswith("Рішення"))
    hid, tid = cs_.get(sx, cs_.candidate_id(P, ci.Index(env.home).section(sid)["heading"]))
    check("T1: …an id still gives its section", hid.startswith("> [own · %s › " % P) and hid.endswith("Рішення · 2026-09-15]")
          and tid.startswith("Показувати графік роботи продавця"), (hid, tid[:200]))
    check("T1: a path --get writes nothing: no last.json", not os.path.exists(cs_.last_path(env.home)))

# U1–U8 (fix round 5): --get by a note's name, a heading after a path, the 20 000 cap, an excluded path, the file before
# a local index's body, the header's source, `@<repo>/…` through the server, key 4 with an unknown size, key 3a by the day
TEAM = "ZorgCore/Teams/team-alpha.md"
SCRATCH5 = "Notes/_System/_scratch/people_digests/zed-nine.md"
LONG = "Notes/Long/Long zebra.md"
D1, D2 = "Notes/Knowledge/Delivery slots (900100200).md", "ZorgCore/Pages/Delivery slots (900100200).md"
with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    write(env.note(SCRATCH5), "---\ntype: note\n---\n# Zed Nine\n\nDigest of the 1-1s.\n")
    write(env.note(LONG), "---\ntype: note\nupdated: 2026-10-03\n---\n# Long zebra\n\n## Part 1\n\n" + "z" * 15000
          + "\n\n## Part 2\n\n" + "y" * 10000 + "\n")
    for i in range(1, 7):
        write(env.note("Notes/Z%d/Zebra twin.md" % i), "# Zebra twin\n\nCopy %d of the zebra note.\n" % i)
    build_brain(env.brain, env.vault, BRAIN_NOTES + [SCRATCH5])
    sx = env.sctx()
    env.refresh(sx)
    reads, real_read, codes = [], cs_.cst.read_text, []
    cs_.cst.read_text = lambda p_, *a, **kw: reads.append(p_) or real_read(p_, *a, **kw)

    def get_or(arg):
        try:
            return cs_.get(sx, arg)
        except cs_.GetError as e:
            codes.append(e.code)
            return None, str(e)
    try:
        h, t = cs_.get(sx, "team-alpha")
        check("U1: --get <name> finds the note by its name key in the own index — the whole note, as a path --get gives it",
              h == "> [zorg-core · %s · 2026-01-01 · team]" % TEAM and t.startswith("# Team Alpha\n\n") and reads == [], (h, t[:120]))
        same = [cs_.get(sx, a)[0] for a in ("Team-Alpha.md", "[[team-alpha]]", "[[Team-Alpha|the team]]",
                                            unicodedata.normalize("NFD", "team-alpha"))]
        check("…`Name.md`, `[[Name]]`, `[[Name|alias]]` and a decomposed name give the same note", all(x == h for x in same), same)
        hm, tm = cs_.get(sx, "[[team-alpha#Members]]")
        check("U1: `[[Name#Heading]]` gives that section under its heading path, as an id with a heading does",
              hm == "> [zorg-core · %s › Team Alpha › Members · 2026-01-01 · team]" % TEAM
              and tm.startswith("- Alex One — product manager") and "Owns the cart" not in tm, (hm, tm))
        check("U6: …and so does `<шлях>#<заголовок>`", cs_.get(sx, TEAM + "#Members") == (hm, tm), cs_.get(sx, TEAM + "#Members"))
        hl, tl = cs_.get(sx, "[[ZorgCore/Epics/Epic — PROJ-77|core page]]")
        check("U1: a link with a folder, as a hub writes it, is that path (`.md` added)",
              hl == "> [zorg-core · ZorgCore/Epics/Epic — PROJ-77.md · 2026-09-28 · epic]" and "## Goal" in tl, (hl, tl[:120]))
        hc, tc = cs_.get(sx, "Cart experiments")
        check("U1/U7: a name only a local index knows (by its file's name): that note — its file first, as it is on disk",
              hc == "> [vault · Growth/Cart experiments.md · 2026-08-01 · ab-test-results]" and "seller's hours" in tc
              and len(reads) == 1, (hc, tc[:120], reads))
        hs, ts = get_or("Delivery slots (900100200)")
        check("U1: a name two notes carry: exit 3, one line naming them, `--get` one of the paths", codes == [3]
              and ts == "кілька нотаток із назвою «Delivery slots (900100200)»: %s · %s — --get один зі шляхів" % (D1, D2), (codes, ts))
        codes[:] = []
        hs, ts = get_or("Zebra twin.md")
        check("…more than five: the first five, then `· ще N`", codes == [3] and ts == "кілька нотаток із назвою «Zebra twin»: "
              + " · ".join("Notes/Z%d/Zebra twin.md" % i for i in range(1, 6)) + " · ще 1 — --get один зі шляхів", (codes, ts))
        codes[:] = []
        hn, tn = get_or("No such zebra")
        check("U1: an unknown name: exit 3, one line naming it", codes == [3] and "No such zebra" in tn and "\n" not in tn, (codes, tn))
        codes[:] = []
        got = [get_or(p)[1] for p in ("Notes/_System/context/records/x.md", SCRATCH5, "ZorgCore/_System/context-blocks.md")]
        check("U5: a path the index excludes — the store, _System/_scratch/, a blocks file — is exit 3 `шлях виключено з пошуку`",
              codes == [3, 3, 3] and got == ["шлях виключено з пошуку: Notes/_System/context/records/x.md",
                                            "шлях виключено з пошуку: " + SCRATCH5,
                                            "шлях виключено з пошуку: ZorgCore/_System/context-blocks.md"], (codes, got))
        codes[:] = []
        hz, tz = get_or("zed-nine")
        check("U5: …a name whose only note a local index holds under _System/_scratch/: the same line, nothing read",
              codes == [3] and tz == "шлях виключено з пошуку: " + SCRATCH5 and len(reads) == 1, (codes, tz, reads))
        hg, tg = cs_.get(sx, LONG)
        whole6 = cs_._note_of(sx, LONG)[5]
        check("U6 (v3.16.1): a whole note is cut at 20 000 characters, then how much of how many, the heading the cut falls "
              "under and the --get of a section or --full",
              hg == "> [own · %s · 2026-10-03 · note]" % LONG and tg.startswith("## Part 1\n\n") and tg == whole6[:20000]
              + "\n\nнотатка довга — показано 20 000 знаків із %s; далі: Part 2 — --get \"%s#<заголовок>\" або --full "
              "(до 60 000)" % ("{:,}".format(len(whole6)).replace(",", " "), LONG), (hg, len(tg), tg[-200:]))
        hp, tp = cs_.get(sx, LONG + "#Part 2")
        check("…a section of it is whole, with no such line", hp == "> [own · %s › Long zebra › Part 2 · 2026-10-03 · note]" % LONG
              and tp == "y" * 10000 and cs_.get(sx, "[[Long zebra#Part 2]]") == (hp, tp), (hp, len(tp), tp[-100:]))
        codes[:] = []
        hx, tx = get_or(LONG + "#Part 9")
        check("…a heading the note does not have: exit 3 `no section`", codes == [3] and tx == "no section Part 9 in %s" % LONG, (codes, tx))
        check("U1: a name --get writes nothing: no last.json", not os.path.exists(cs_.last_path(env.home)))
    finally:
        cs_.cst.read_text = real_read

# U4 (M2): the header of a path read from a local index names the root the path lies under; the index only in ICLOUD_LOCAL
with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    build_brain(env.brain, env.vault, [TEAM])
    sx = env.sctx()                                   # no own index yet: the local index is the only copy
    reads, real_read, real_dataless = [], cs_.cst.read_text, ci.is_dataless
    cs_.cst.read_text = lambda p_, *a, **kw: reads.append(p_) or real_read(p_, *a, **kw)
    ci.is_dataless = lambda p_: unicodedata.normalize("NFC", p_).endswith("team-alpha.md")
    try:
        h4, t4 = cs_.get(sx, TEAM)
        check("U4: a core page a local index holds (its file dataless) is cited by its repository; the index in the ICLOUD_LOCAL line",
              h4 == "> [zorg-core · %s · 2026-01-01 · team]" % TEAM
              and t4.startswith(cs_.ICLOUD_LOCAL % "zorg-brain" + "\n\n# Team Alpha") and reads == [], (h4, t4[:160], reads))
    finally:
        cs_.cst.read_text, ci.is_dataless = real_read, real_dataless

# U2 (I2): `@<repo>/<rel>` of a repository with an endpoint and no folder on disk is read through vault_get_note
PAGE5 = ("---\ntype: page\nupdated: 2026-09-20\n---\n# Delivery slots\n\nShoppers pick a two-hour delivery slot at checkout.\n\n"
         "## Rules\n\nThe slots of a closed seller are hidden.\n")
with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    codes = []
    with FakeMcp(tree={"Growth/Pages/Delivery slots.md": PAGE5}) as s:
        env.reg("zorg-growth", growth_reg(s.url))
        sx = env.sctx()
        h5, t5 = cs_.get(sx, "@zorg-growth/Pages/Delivery slots.md")
        check("U2: --get @<repo>/<rel> reads the note through the server at endpoint.root/<rel>, under the repository's line with its marks",
              h5 == "> [zorg-growth · @zorg-growth/Pages/Delivery slots.md · 2026-09-20 · page]"
              and t5.startswith("# Delivery slots\n\n") and "type:" not in t5 and "closed seller" in t5, (h5, t5))
        asked = [json.dumps(x.get("body"), ensure_ascii=False) for x in s.seen]
        check("…asked for the server's path", any("vault_get_note" in b and "Growth/Pages/Delivery slots.md" in b for b in asked), asked[-2:])
        hr, tr = cs_.get(sx, "@zorg-growth/Pages/Delivery slots.md#Rules")
        check("…with a heading: that section", hr == "> [zorg-growth · @zorg-growth/Pages/Delivery slots.md › Delivery slots › Rules · "
              "2026-09-20 · page]" and tr == "The slots of a closed seller are hidden.", (hr, tr))
        try:
            cs_.get(sx, "@zorg-growth/Pages/No such.md")
            got = None
        except cs_.GetError as e:
            got = e
        check("…a note the server does not have: exit 3, naming it", got is not None and got.code == 3
              and "Growth/Pages/No such.md" in str(got), got)
    try:
        cs_.get(sx, "@zorg-growth/Pages/Delivery slots.md")
        got = None
    except cs_.GetError as e:
        got = e
    check("…the server gone: exit 5, as for an id", got is not None and got.code == 5 and str(got) == "zorg-growth не відповів — без нього", got)
    try:
        cs_.get(sx, "@nobody/Pages/x.md")
        got = None
    except cs_.GetError as e:
        got = e
    check("…a repository nobody registered: exit 3, one line", got is not None and got.code == 3 and "@nobody/Pages/x.md" in str(got), got)

# U2 (I2) key 4: a candidate whose size is unknown (a server's note) is not the smaller one
E1, E2 = "Notes/Epics/Epic — PROJ-77.md", "ZorgCore/Epics/Epic — PROJ-77.md"
E3 = "@zorg-growth/Epics/Epic — PROJ-77.md"
metas = {E1: meta_of(E1, title="Epic — PROJ-77", links=["epic — proj-77"], size=180, date="2026-10-01")}
out = cs_.dedup([entry(E1, "", 0.03, sid=1), entry(E3, "", 0.04, source="zorg-growth", title="Epic — PROJ-77")], metas)
check("U2 key 4: the hub of your layer and a server's page of the same title — the size unknown, the better score stays",
      [c["path"] for c in out] == [E3] and out[0]["flags"] == ["двійник " + E1], out)
out = cs_.dedup([entry(E1, "", 0.05, sid=1, flags=["хаб"]), entry(E3, "", 0.04, source="zorg-growth", title="Epic — PROJ-77")], metas)
check("…a non-hub over a hub, before the score", [c["path"] for c in out] == [E3] and out[0]["flags"] == ["двійник " + E1], out)
metas[E2] = meta_of(E2, title="Epic — PROJ-77", size=640, date="2026-09-28")
out = cs_.dedup([entry(E1, "", 0.05, sid=1), entry(E2, "Epic — PROJ-77 › Goal", 0.03, sid=2)], metas)
check("…both sizes known: the bigger stays, as before", [c["path"] for c in out] == [E2] and out[0]["flags"] == ["двійник " + E1], out)

# U8 (M6) key 3a: the day decides, not the full date — the same day, the better score
N2, N4 = "Growth/Cart study.md", "Archive/Cart study.md"
out = cs_.dedup([entry(N2, "", 0.01, source="zorg-brain", near="k1", date="2026-10-07"),
                 entry(N4, "", 0.05, source="zorg-brain", near="k1", date="2026-10-07T09:30:00")], {}, own=["Notes"])
check("U8 key 3a: a date-only copy and a copy with a time on the same day: the better score stays",
      [c["path"] for c in out] == [N4] and out[0]["flags"] == ["двійник " + N2], out)
out = cs_.dedup([entry(N2, "", 0.05, source="zorg-brain", near="k1", date="2026-10-06T23:59:00"),
                 entry(N4, "", 0.01, source="zorg-brain", near="k1", date="2026-10-07")], {}, own=["Notes"])
check("…an earlier day still wins", [c["path"] for c in out] == [N2] and out[0]["flags"] == ["двійник " + N4], out)

# V1–V5 (round 5b): a vault-root path is a path first, `#` in a `.md` path, exclusion of non-canonical spellings, `vault`
# whichever source gave the text, a note named like an id
ROOT_TEAM = "---\ntype: note\ndate: 2026-10-10\n---\n# My root copy of team alpha\n\nROOT-LEVEL NOTE TEXT.\n"
SHARP = "Growth/C# notes.md"
with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    write(env.note("team-alpha.md"), ROOT_TEAM)
    write(env.note("Root memo.md"), "# Root memo\n\nroot one\n")
    write(env.note("Growth/Root memo.md"), "# Root memo\n\ngrowth one\n")
    write(env.note(SHARP), "# C# notes\n\nsharp text\n\n## Sharp\n\nThe sharp section.\n")
    write(env.note(SCRATCH5), "---\ntype: note\n---\n# Zed Nine\n\nDigest of the 1-1s.\n")
    write(env.note("Notes/deadbeef12.md"), "# deadbeef12\n\nA note named like an id.\n")
    build_brain(env.brain, env.vault, BRAIN_NOTES + ["team-alpha.md", "Root memo.md", "Growth/Root memo.md", SHARP])
    sx = env.sctx()
    env.refresh(sx)
    reads, real_read, real_dataless, codes = [], cs_.cst.read_text, ci.is_dataless, []
    cs_.cst.read_text = lambda p_, *a, **kw: reads.append(p_) or real_read(p_, *a, **kw)

    def get_or(arg):
        try:
            return cs_.get(sx, arg)
        except cs_.GetError as e:
            codes.append(e.code)
            return None, str(e)
    try:
        h, t = cs_.get(sx, "team-alpha.md")
        check("V1: a vault-root path with no `/`, as the list prints it, is that note — never the own-index note of the same name",
              h == "> [vault · team-alpha.md · 2026-10-10 · note]" and "ROOT-LEVEL NOTE TEXT." in t, (h, t[:80]))
        check("…and the bare name is the exact path first", cs_.get(sx, "team-alpha") == (h, t), cs_.get(sx, "team-alpha")[0])
        hr, tr = cs_.get(sx, "Root memo.md")
        check("V1: two notes named Root memo: the root-level path reads itself, the other its own",
              hr.startswith("> [vault · Root memo.md · ") and "root one" in tr
              and "growth one" in cs_.get(sx, "Growth/Root memo.md")[1], (hr, tr[:60]))
        check("V1: _by_name prefers the exact path among several", cs_._by_name(sx, "Root memo") == "Root memo.md",
              cs_._by_name(sx, "Root memo"))
        hs, ts = cs_.get(sx, SHARP)
        check("V2: a path with `#` in its name is a path (it ends in .md)", hs.startswith("> [vault · %s · " % SHARP)
              and "sharp text" in ts, (hs, ts[:60]))
        hs2, ts2 = cs_.get(sx, SHARP + "#Sharp")
        check("…and `<such a path>#<heading>` is its section", hs2.startswith("> [vault · %s › C# notes › Sharp · " % SHARP)
              and ts2 == "The sharp section.", (hs2, ts2))
        reads[:] = []
        got = [get_or(p)[1] for p in ("Notes/_System/./_scratch/people_digests/zed-nine.md",
                                      "Notes/_System/context/../_scratch/people_digests/zed-nine.md",
                                      "Notes/_system/_scratch/people_digests/zed-nine.md", "notes/_system/context/records/x.md")]
        check("V3: an excluded path spelt with `.`, `..` or another case is exit 3 `шлях виключено з пошуку`, nothing read",
              codes == [3, 3, 3, 3] and got == [cs_.EXCLUDED_NOTE % SCRATCH5, cs_.EXCLUDED_NOTE % SCRATCH5,
                                                cs_.EXCLUDED_NOTE % "Notes/_system/_scratch/people_digests/zed-nine.md",
                                                cs_.EXCLUDED_NOTE % "notes/_system/context/records/x.md"] and reads == [], (codes, got, reads))
        check("V3 (v3.16.2 C3): …the walk folds the folder names too (`_system/_scratch`), the store stays exact unless "
              "`fold`", ci.excluded("Notes/_system/_scratch/x.md", "Notes/_System/context", [])
              and not ci.excluded("notes/_system/context/records/x.md", "Notes/_System/context", [])
              and ci.excluded("notes/_system/context/records/x.md", "Notes/_System/context", [], fold=True))
        ci.is_dataless = lambda p_: unicodedata.normalize("NFC", p_).endswith("Cart experiments.md")
        reads[:] = []
        h4, t4 = cs_.get(sx, "Growth/Cart experiments.md")
        check("V4: a note outside every root, its text from a local index (the file dataless): `vault` in the header, the index "
              "only in the ICLOUD_LOCAL line", h4 == "> [vault · Growth/Cart experiments.md · 2026-08-01 · ab-test-results]"
              and t4.startswith(cs_.ICLOUD_LOCAL % "zorg-brain" + "\n\n") and reads == [], (h4, t4[:120], reads))
        ci.is_dataless = real_dataless
        h5, t5 = cs_.get(sx, "deadbeef12")
        check("V5: a note named like an id (ten hex digits) is read by its name when no search gave that id",
              h5.startswith("> [own · Notes/deadbeef12.md · ") and "A note named like an id." in t5, (h5, t5[:60]))
        codes[:] = []
        h6, t6 = get_or("0000000000")
        check("…an id no search gave and no note is named by: exit 3, one line", codes == [3] and "0000000000" in t6 and "\n" not in t6,
              (codes, t6))
        check("V1–V5: nothing written — no last.json", not os.path.exists(cs_.last_path(env.home)))
    finally:
        cs_.cst.read_text, ci.is_dataless = real_read, real_dataless

# the protocols say what the fixes do
import re  # noqa: E402


def flat(*parts):
    return re.sub(r"\s+", " ", read(ROOT, *parts))


def section(text, n):
    """The text of `## <n>.` up to the next `## `."""
    m = re.search(r"## %d\. (.*?)(?= ## \d+\. |$)" % n, text)
    return m.group(1) if m else ""


SP = flat("references", "search-protocol.md")
PP = flat("references", "context-provider-protocol.md")
check("search-protocol §3: the building and the not-built lines, and index.locked",
      all(x in section(SP, 3) for x in ("`індекс пошуку ще будується (інший процес) — цього разу без нього`",
                                        "`індексу пошуку ще немає (…) — ctx index rebuild`", "`index.locked`")),
      section(SP, 3)[-1500:])
check("search-protocol §7: an own index being built or not built yet is the base not read; nothing taken while the index "
      "reports files not yet seen is a doubt, with `повторити пошук`",
      all(x in section(SP, 7) for x in ("`index.locked`", "`індекс оновлюється: N файлів ще не переглянуто`", "`повторити пошук")),
      section(SP, 7))
check("search-protocol §4: a --get header with sensitive or застаріле is the flag; a local/mcp candidate's flags are complete "
      "only after --get; a product's version number makes a version key",
      all(x in section(SP, 4) for x in ("` · sensitive`", "` · застаріле`", "complete only after `--get`", "`API v2`")),
      section(SP, 4)[-1500:])
check("context-provider-protocol §2: --get reads status and sensitive of a server's note; the OR expression is search-protocol §12",
      "`ctx search --get` reads them from the note's frontmatter" in section(PP, 2)
      and "joined by `OR` (`\"кошик\"* OR \"мобільний\"*`) — because plain words would be read as \"all of them\" "
          "(`search-protocol.md` §12)" in section(PP, 2), section(PP, 2)[-1800:])
CP = flat("references", "context-protocol.md")
check("acceptance fix wave — search-protocol §3: the pool of 30; §4: `застаріле` by status alone, the `станом на <день>` "
      "row, the --get lines as the code prints them; §5: the as-of citation; §6: as-of alone does not forbid",
      "the pool of 30" in section(SP, 3)
      and "| `застаріле` | `status` outdated, archived, deprecated, former or superseded |" in section(SP, 4)
      and "| `%s` |" % (cs_.AS_OF % "<день>") in section(SP, 4)
      and all("`%s`" % x in section(SP, 4) for x in (cs_.SHORT_NOTE % "<заголовки>", cs_.ICLOUD_LOCAL % "<id>",
                                                    cs_.ICLOUD_MISSING % "<шлях>", getattr(cs_, "ICLOUD_OPEN", "-") % "<шлях>"))
      and "`(<джерело>, станом на <день>)`" in section(SP, 5)
      and "`знімок від <день>` or `станом на <день>` alone does not forbid it" in section(SP, 6), section(SP, 4)[:1200])
check("…context-provider-protocol §5: near copies are key 3a, an outdated status × 0.5; §6: a class TTL marks "
      "`станом на <день>` and lowers nothing; context-protocol §3: the best N (30), eval 50",
      "**Near copies** count as the same content (key 3a)" in section(PP, 5)
      and "a note whose `status` says it is outdated × 0.5" in section(PP, 5)
      and "marks a search candidate `станом на <день>`" in section(PP, 6) and "its score is not lowered" in section(PP, 6)
      and "the best N (30; `search eval` reads 50)" in section(CP, 3), section(PP, 6)[-1200:])
check("fix round 1 — provider §5: a navigation label only, an update date only, your layer by its path, headings count; "
      "search-protocol §4: the whole note from a local copy without the section",
      all(x in section(PP, 5) for x in ("`Owner: [[X]]` is text", "`Deadline: …` is text",
                                        "its path under the plugin folder, whichever source found it", "the same headings and text"))
      and "the whole note when that copy has no such section" in section(SP, 4), section(PP, 5)[-1500:])
check("fix round 2 — provider §5: your layer first, then the older; the headings do not count toward 400; §10: a breadcrumb "
      "is a section of its own; search-protocol §3: a breadcrumb is never the snippet",
      all(x in section(PP, 5) for x in ("stays first, and of those the older by its day",
                                        "a copy with no date never wins over a dated one", "the headings do not count"))
      and "is a section of its own, a mirror page's breadcrumb too" in section(PP, 10)
      and "so a breadcrumb is never the snippet" in section(SP, 3), section(PP, 10)[-1500:])
check("fix round 4 — search-protocol §4: a twin, a newer version and a hub's link are read with `ctx search --get <шлях>`; "
      "context-protocol §3: --get ID|PATH", all(x in section(SP, 4) for x in (
          "read the newer one with `ctx search --get \"<шлях>\" --json`", "read the twin too (`ctx search --get \"<шлях>\" --json`)",
          "a note it links to is read with `ctx search --get \"<назва або шлях>\" --json`", "Never open a vault file by its path yourself"))
      and "from its path" not in section(SP, 4) and "`search --get ID\\|PATH\\|NAME [--json]`" in section(CP, 3), section(SP, 4)[-1200:])
check("fix round 5 — search-protocol §4: a hub's link by name or path, the name forms, the several-notes and excluded lines, "
      "the 20 000 cap and the section after `#`, the source `vault`, the never-open sentence scoped to Step 0.5 with SHELL; §5: `vault`",
      all(x in section(SP, 4) for x in (
          "`Name`, `Name.md`, `[[Name]]`, `[[Name|alias]]`, `[[Name#Heading]]`",
          "`%s`" % (cs_.SEVERAL_NOTE % ("<назва>", "<шлях> · <шлях> …")), "`%s`" % (cs_.EXCLUDED_NOTE % "<шлях>"),
          "`vault` for a file outside every root", "read through its server (exit 5",
          "Never open a vault file by its path yourself in Step 0.5 on a host with SHELL", "without SHELL §12 applies"))
      and "`vault` is a file outside every root" in section(SP, 5), section(SP, 4)[-2600:])
check("fix round 5 — provider §2 (U3): a server's note is `застаріле` by status only, `станом на <день>` by its class age; §5: key 4 "
      "a non-hub first and an unknown size never the smaller, key 3a by the day; context-protocol §3, the usage line and the module "
      "docstring: --get ID|PATH|NAME",
      "never marked `застаріле` (its status), and `sensitive` only when its `type` is a people type (since v3.17.0); the age of its class marks it `станом на <день>`" in section(PP, 2)
      and all(x in section(PP, 5) for x in ("a note that is not a hub stays over a hub",
                                            "a server's note has no size, and is not the smaller for it", "the older by its day"))
      and "`search --get ID\\|PATH\\|NAME [--json]`" in section(CP, 3) and "search --get ID|PATH|NAME [--json]" in read(ROOT, "scripts", "ctx.py")
      and "--get ID|PATH|NAME" in cs_.__doc__, (section(PP, 2)[-700:], section(PP, 5)[-1200:]))
check("round 5b — search-protocol §4 (V6): a --get of a twin, a newer version or a hub's link that exits non-zero — rate on what "
      "you have; a path is tried before a name",
      all(x in section(SP, 4) for x in ("a twin you could not read is not a conflict", "leaves the older one in the block, not taken",
                                        "a hub's link you could not read is not taken", "tried as a path first")), section(SP, 4)[-1800:])
check("vault-protocol «In short»: the level-2 triggers are in search-protocol §8",
      "maybe live sources (level 2; triggers in search-protocol §8)" in read(ROOT, "references", "vault-protocol.md"))

# v3.16.1 Task 2: every --get form is cut at 20 000 characters (60 000 with --full), a line saying how much of how many
# and naming the headings past the cut
def heading_names_after(text, cut, dup_full=None):
    """The names the line should carry, worked out from the text alone: the heading the cut falls under — only when
    --get of it would show 2 000 characters more than the cut text does (v3.16.2) —, then every heading line that
    starts past the cut (the last part; the full path for a last part that repeats)."""
    import re as _re
    pos, names, stack, last_before, heads = 0, [], [], None, []
    for line in text.split("\n"):
        m = _re.match(r"^(#{1,3})[ \t]+(.+?)[ \t]*$", line)
        if m:
            level = len(m.group(1))
            stack = [s for s in stack if s[0] < level] + [(level, m.group(2))]
            name = " › ".join(s[1] for s in stack) if dup_full and m.group(2) in dup_full else m.group(2)
            heads.append(pos)
            if pos >= cut:
                names.append(name)
            else:
                last_before = (name, pos, len(line) + 1)
        pos += len(line) + 1
    if last_before:
        name, at, head = last_before
        nxt = next((h for h in heads if h > at), len(text))
        if min(nxt - at - head, cut) - (cut - at) >= 2000:
            return [name] + names
    return names


def long_line(path, shown, total, names, full):
    n = lambda v: "{:,}".format(v).replace(",", " ")
    head = "нотатка довга — показано %s знаків із %s; " % (n(shown), n(total))
    more = " --full" if full else " або --full (до 60 000)"
    if names:
        return head + "далі: " + " · ".join(names) + " — --get \"%s#<заголовок>\"" % path + more
    return head + "заголовків далі немає" + (" — --full (до 60 000)" if not full else "")


PARTS = "Notes/Long/Long parts.md"          # 20 sections, ~45 000 characters
HUGE = "Notes/Long/Huge parts.md"           # 32 sections, ~70 000
MANY = "Notes/Long/Many parts.md"           # 40 short sections past the cut
DUP = "Notes/Long/Dup parts.md"             # two `Notes` under two parents past the cut
SEC = "Notes/Long/Long section.md"          # one 30 000-character section
FLAT = "Notes/Long/Flat zebra.md"           # no heading, 34 000 characters
OUT = "Growth/Zebra long.md"                # outside the plugin folder: only the local index knows it
with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    write(env.note(PARTS), "---\ntype: note\nupdated: 2026-10-05\n---\n# Long parts\n\n"
          + "".join("## Part %d\n\n%s\n\n" % (i, "p" * 2200) for i in range(1, 21)))
    write(env.note(HUGE), "# Huge parts\n\n" + "".join("## Chunk %d\n\n%s\n\n" % (i, "h" * 2200) for i in range(1, 33)))
    write(env.note(MANY), "# Many parts\n\n" + "m" * 20500 + "\n\n" + "".join("## Bit %d\n\nshort\n\n" % i for i in range(1, 41)))
    write(env.note(DUP), "# Dup parts\n\n" + "d" * 20500 + "\n\n## Alpha\n\nalpha text\n\n### Notes\n\na\n\n## Beta\n\nbeta text\n\n### Notes\n\nb\n")
    write(env.note(SEC), "# Long section\n\n## Big\n\n" + "b" * 30000 + "\n\n## Small\n\nsmall text\n")
    write(env.note(FLAT), "Flat zebra stripes of the cart. " + "f" * 34000 + "\n")
    write(env.note(OUT), "---\ntype: note\nupdated: 2026-09-09\n---\n# Zebra long\n\nLong zebra stripes of the cart.\n\n"
          + "".join("## Leg %d\n\n%s\n\n" % (i, "o" * 2200) for i in range(1, 21)))
    build_brain(env.brain, env.vault, BRAIN_NOTES + [OUT])
    sx = env.sctx()
    env.refresh(sx)

    def cut_of(arg, full=False):
        try:
            return cs_.get(sx, arg, full=full)
        except TypeError as e:              # no `full` yet
            return None, "TypeError %s" % e

    h, t = cut_of(PARTS)
    full_text = cs_._note_of(sx, PARTS)[5]
    want = full_text[:20000] + "\n\n" + long_line(PARTS, 20000, len(full_text), heading_names_after(full_text, 20000), False)
    check("v3.16.1 C6: --get <path> of a 45 000-character note — 20 000 characters, then how much of how many and the headings "
          "from the one the cut falls under", t == want, (len(t or ""), (t or "")[-400:], want[-400:]))
    h, t = cut_of(PARTS, full=True)
    check("…--full: the whole 45 000, no line", t == full_text, (len(t or ""), (t or "")[-200:]))
    huge = cs_._note_of(sx, HUGE)[5]
    h, t = cut_of(HUGE, full=True)
    check("…--full of a 70 000-character note: 60 000, the line without the --full hint",
          t == huge[:60000] + "\n\n" + long_line(HUGE, 60000, len(huge), heading_names_after(huge, 60000), True),
          (len(t or ""), (t or "")[-300:]))
    many = cs_._note_of(sx, MANY)[5]
    h, t = cut_of(MANY)
    names = heading_names_after(many, 20000)
    check("…more than 20 names: the first 20, then `· ще N`", t is not None and t.endswith(
        "далі: " + " · ".join(names[:20]) + " · ще %d — --get \"%s#<заголовок>\" або --full (до 60 000)" % (len(names) - 20, MANY)),
        (t or "")[-500:])
    dup = cs_._note_of(sx, DUP)[5]
    h, t = cut_of(DUP)
    check("…a last part that repeats (Task 2 fix: by the shortest end of its path that `--get` takes back to it)",
          t == dup[:20000] + "\n\n" + long_line(DUP, 20000, len(dup), ["Alpha", "Notes", "Beta", "Beta › Notes"],
                                                False), (t or "")[-300:])
    h, t = cut_of(SEC + "#Big")
    check("…a section after `#` is cut too: 20 000, the line (no headings past the cut inside it)",
          t == "b" * 20000 + "\n\n" + long_line(SEC, 20000, 30000, [], False), (len(t or ""), (t or "")[-200:]))
    h, t = cut_of(SEC + "#Big", full=True)
    check("…with --full the 30 000-character section is whole", t == "b" * 30000, (len(t or ""), (t or "")[-100:]))
    res = cs_.run(sx, ["flat zebra stripes"], now=NOW)
    flat = next((c for c in res["candidates"] if c["path"] == FLAT), None)
    h, t = cut_of(flat["id"]) if flat else (None, "")
    flat_text = cs_._note_of(sx, FLAT)[5]
    check("…--get <id> of an own section with no heading, 34 000 characters: 20 000, «заголовків далі немає»",
          flat and len(flat_text) > 34000 and t == flat_text[:20000] + "\n\n" + long_line(FLAT, 20000, len(flat_text), [], False),
          (len(t or ""), (t or "")[-200:]))
    res = cs_.run(sx, ["long zebra stripes"], now=NOW)
    cs_.save_last(env.home, res["last"])
    out = next((c for c in res["candidates"] if c["path"] == OUT), None)
    h, t = cut_of(out["id"]) if out else (None, "")
    body = cs_._note_of(sx, OUT)[5]
    check("…--get <id> of a note-level local-index candidate: the same cut and line",
          out and out["source"] == ["zorg-brain"] and t == body[:20000] + "\n\n"
          + long_line(OUT, 20000, len(body), heading_names_after(body, 20000), False), (out, len(t or ""), (t or "")[-300:]))
    real_dataless = ci.is_dataless
    ci.is_dataless = lambda p_: unicodedata.normalize("NFC", p_).endswith("Zebra long.md")
    try:
        h, t = cut_of(OUT)
        body_l = cs_._note_of(sx, OUT)[5]
    finally:
        ci.is_dataless = real_dataless
    said = cs_.ICLOUD_LOCAL % "zorg-brain" + "\n\n"
    check("…the ICLOUD_LOCAL line comes first and is not counted", t == said + body_l[:20000] + "\n\n"
          + long_line(OUT, 20000, len(body_l), heading_names_after(body_l, 20000), False), (t or "")[:200])
    h, t = cut_of(PARTS + "#Part 2")
    check("…a text within the cut: no line", t == "p" * 2200, (len(t or ""), (t or "")[-100:]))

check("v3.16.1 C6 — search-protocol §4: every --get form is cut at 20 000, the line's two shapes, --full up to 60 000 for a "
      "candidate taken as «прямо» and when, never for a hub, a twin's check or one not rated «прямо»; context-protocol §3",
      all(x in section(SP, 4) for x in (
          "`%s`" % cs_.long_note("<шлях>", 20000, "<усього>", ["<заголовок>", "…"], False),
          "`%s`" % cs_.long_note("<шлях>", 20000, "<усього>", [], False),
          "Any form of `--get`", "a section after `#` too", "`--full`", "60 000", "rated «прямо»",
          "never for a hub, a twin's check or a candidate not rated «прямо»"))
      and "--full" in section(CP, 3), section(SP, 4)[-2600:])

# v3.16.1 Task 3: --get reads a link as a hub writes it — an embed, nested headings, a block reference, a folder in the link
CONCEPT = "Notes/Concepts/Zorg cart concept.md"
IZMIR = "Notes/İzmir notes.md"
with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    para = lambda w: (" ".join([w] * 60)) + "."              # a section long enough to be given alone (no fill)
    write(env.note(CONCEPT), "---\ntype: concept\nupdated: 2026-10-04\n---\n# Zorg cart concept\n\n" + para("intro")
          + "\n\n## Pricing\n\n" + para("pricing") + "\n\n### Fees\n\n" + para("pricefee")
          + "\n\n## Delivery\n\n" + para("delivery") + "\n\n### Fees\n\n" + para("deliveryfee") + " ^a1b2c3"
          + "\n\n## C# tips\n\n" + para("sharp") + "\n")
    write(env.note(IZMIR), "# İzmir notes\n\n## Plan\n\n" + para("plan") + "\n\n## lan\n\n" + para("other") + "\n")
    write(env.note("Notes/A/Shared/Dup end.md"), "# Dup end\n\n" + para("dupa") + "\n")
    write(env.note("Notes/B/Shared/Dup end.md"), "# Dup end\n\n" + para("dupb") + "\n")
    write(env.note("Notes/_System/_scratch/Tail only.md"), "# Tail only\n\n" + para("scratch") + "\n")
    write(env.note("Growth/Deep/Local only.md"), "---\ntype: note\n---\n# Local only\n\n" + para("localonly") + "\n")
    write(env.note("Concepts/Other.md"), "# Other\n\n" + para("rootother") + "\n")
    write(env.note("Notes/Concepts/Other.md"), "# Other\n\n" + para("notesother") + "\n")
    build_brain(env.brain, env.vault, BRAIN_NOTES + ["Growth/Deep/Local only.md", "Notes/_System/_scratch/Tail only.md"])
    sx = env.sctx()
    env.refresh(sx)

    def got(arg):
        try:
            return cs_.get(sx, arg)
        except cs_.GetError as e:
            return "exit %d" % e.code, str(e)

    whole = cs_.get(sx, "[[Zorg cart concept]]")
    pricing = cs_.get(sx, "[[Zorg cart concept#Pricing]]")
    check("v3.16.1 C8: an embed `![[Name]]` is the note, `![[Name#H]]` its section",
          got("![[Zorg cart concept]]") == whole and got("![[Zorg cart concept#Pricing]]") == pricing
          and whole[0].startswith("> [own · %s · 2026-10-04" % CONCEPT), (got("![[Zorg cart concept]]")[0], whole[0]))
    h, t = got("[[Zorg cart concept#Delivery#Fees]]")
    check("…`#H1#H2` is the end of a heading path: Delivery › Fees, not the first Fees",
          h == "> [own · %s › Zorg cart concept › Delivery › Fees · 2026-10-04 · concept]" % CONCEPT
          and t.startswith("deliveryfee"), (h, t[:80]))
    check("…` › ` in the asked heading is a path too", got("Zorg cart concept#Delivery › Fees") == (h, t),
          got("Zorg cart concept#Delivery › Fees")[0])
    h1, t1 = got("[[Zorg cart concept#Fees]]")
    check("…a bare `#Fees` is still the first one (Pricing › Fees)", h1.endswith("› Zorg cart concept › Pricing › Fees · 2026-10-04 · concept]")
          and t1.startswith("pricefee"), h1)
    check("…a block reference `#^id` is the section that holds the block (round 3b), an unknown one the whole note; "
          "`#H#^id` that section", got("[[Zorg cart concept#^a1b2c3]]") == got("[[Zorg cart concept#Delivery#Fees]]")
          and got("[[Zorg cart concept#^zzz999]]") == whole and got("[[Zorg cart concept#Pricing#^a1b2c3]]") == pricing,
          (got("[[Zorg cart concept#^a1b2c3]]")[0], got("[[Zorg cart concept#Pricing#^a1b2c3]]")[0]))
    h2, t2 = got("[[Zorg cart concept#C# tips]]")
    check("…a heading with `#` in it is tried whole first", h2.endswith("› Zorg cart concept › C# tips · 2026-10-04 · concept]")
          and t2.startswith("sharp"), h2)
    h3, t3 = got(IZMIR + "#Plan")
    check("…`İ` (U+0130) before `.md#` does not shift the heading: Plan, not «lan»",
          h3.startswith("> [own · %s › İzmir notes › Plan · " % IZMIR) and t3.startswith("plan"), (h3, t3[:40]))
    h4, t4 = got("[[Concepts/Zorg cart concept]]")
    check("v3.16.1 C7: a link with a folder that no source holds as a path — the one note whose path ends in it",
          (h4, t4) == whole, h4)
    check("…`../` before it is dropped; a heading after it works",
          got("[[../Concepts/Zorg cart concept]]") == whole and got("[[Concepts/Zorg cart concept#Pricing]]") == pricing,
          got("[[../Concepts/Zorg cart concept]]")[0])
    check("…case and NFD do not matter", got("[[concepts/zorg CART concept]]") == whole
          and got(unicodedata.normalize("NFD", "[[Concepts/Zorg cart concept]]")) == whole, got("[[concepts/zorg CART concept]]")[0])
    h5, t5 = got("[[Shared/Dup end]]")
    check("…two notes end in it: exit 3, the line naming both (round 3b: a path's own line)", h5 == "exit 3"
          and t5 == getattr(cs_, "SEVERAL_TAIL", "%s %s") % ("Shared/Dup end", "Notes/A/Shared/Dup end.md · Notes/B/Shared/Dup end.md")
          and t5.startswith("кілька нотаток, чий шлях закінчується на «Shared/Dup end»"), (h5, t5))
    h6, t6 = got("[[_scratch/Tail only]]")
    check("…only an excluded note ends in it: exit 3 `шлях виключено з пошуку`",
          (h6, t6) == ("exit 3", cs_.EXCLUDED_NOTE % "Notes/_System/_scratch/Tail only.md"), (h6, t6))
    h7, t7 = got("[[Deep/Local only]]")
    check("…a note only a local index knows ends in it: read through it",
          h7.startswith("> [vault · Growth/Deep/Local only.md · ") and "localonly" in t7,
          (h7, t7[:80]))
    h8, t8 = got("[[Concepts/Other]]")
    check("…the exact path wins over the end of a path", h8.startswith("> [vault · Concepts/Other.md · ") and "rootother" in t8,
          (h8, t8[:60]))
    h9, t9 = got("[[Nowhere/Zorg cart concept]]")
    check("…nothing ends in it: exit 3 `no candidate`", h9 == "exit 3" and "Nowhere/Zorg cart concept" in t9, (h9, t9))
    check("…`../` never reads a file outside the vault", got("[[../../outside]]")[0] == "exit 3", got("[[../../outside]]"))

check("v3.16.1 C7/C8 — search-protocol §4: the link forms as a hub writes them — an embed, `#H1#H2`, `#^block`, a folder in "
      "the link tried as a path, then as the end of one; context-protocol §3 and the usage name them",
      all(x in section(SP, 4) for x in ("`![[Name]]`", "`[[Name#H1#H2]]`", "`[[Name#^block]]`",
                                        "a link with a folder in it is tried as a path, then as the end of one",
                                        "`%s`" % cs_.SEVERAL_TAIL % ("<посилання>", "<шлях> · <шлях> …"),
                                        "the plugin folder's `<папка плагіна>/<посилання>` first",
                                        "the section that holds the block, else the whole note"))
      and "`![[Name]]`" in section(CP, 3) and "as the end of a path" in read(ROOT, "scripts", "ctx.py"),
      section(SP, 4)[-2600:])

# Task 2 review fix: every name the LONG_NOTE line gives is one `--get "<path>#<name>"` takes back to that very section;
# --full by id
def line_names(t):
    """The names a LONG_NOTE line gives (without `ще N`)."""
    tail = (t or "").rsplit("\n\n", 1)[-1]
    if "; далі: " not in tail:
        return []
    listed = tail.split("; далі: ", 1)[1].rsplit(" — --get ", 1)[0]
    return [n for n in listed.split(" · ") if not n.startswith("ще ")]


LOG = "Notes/Long/Zorg log.md"                # empty date headings: split_sections drops them
LOGF = "Growth/Zorg log file.md"              # the same note read from its file (a local index's note)
CASE = "Notes/Long/Case dup.md"               # `Action Items` before the cut, `Action items` past it
TWO = "Notes/Long/Two bigs.md"                # `Early › Big` and `Late › Big`; the short `Late` fills into `Late › Big`
SAME = "Notes/Long/Same path.md"              # the same full path twice; a heading with `|`
FENCE = "Notes/Long/Fenced.md"                # past the cut: a `##` inside a code fence and a `####` heading
log_text = ("# Zorg log\n\n" + "l" * 20500 + "\n\n## 2026-10-01\n\n### Action items\n\n" + "one " * 60
            + "\n\n## 2026-10-08\n\n### Action items\n\n" + "two " * 60 + "\n")
with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    write(env.note(LOG), log_text)
    write(env.note(LOGF), log_text.replace("# Zorg log\n\n", "# Zorg log\n\nThe file copy of the log, read through a local index.\n\n", 1))
    write(env.note(CASE), "# Case dup\n\n## Action Items\n\n" + "early " * 60 + "\n\n## Body\n\n" + "c" * 20500
          + "\n\n## Action items\n\n" + "late " * 60 + "\n")
    write(env.note(TWO), "# Two bigs\n\n## Early\n\n### Big\n\n" + "e" * 500 + "\n\n## Late\n\nshort\n\n### Big\n\n"
          + "b" * 30000 + "\n")
    write(env.note(SAME), "# Same path\n\n## Dup\n\n" + "first " * 60 + "\n\n## Body\n\n" + "s" * 20500
          + "\n\n## Dup\n\n" + "second " * 60 + "\n\n## A | B\n\n" + "pipe " * 60 + "\n")
    write(env.note(FENCE), "# Fenced\n\n" + "f" * 20500 + "\n\n```\n## Not a heading\n```\n\n#### Deep\n\n" + "deep " * 60
          + "\n\n## Real\n\n" + "real " * 60 + "\n")
    build_brain(env.brain, env.vault, BRAIN_NOTES + [LOGF])
    sx = env.sctx()
    env.refresh(sx)

    def back(path, name):
        try:
            return cs_.get(sx, "%s#%s" % (path, name))
        except cs_.GetError as e:
            return "exit %d" % e.code, str(e)

    for label, path in (("an own note", LOG), ("the same note from its file", LOGF)):
        h, t = cs_.get(sx, path)
        names = line_names(t)
        got = [back(path, n) for n in names]
        check("Task 2 fix I1(a/b): %s whose date headings have no text — every name the line gives is read back by "
              "`--get \"<path>#<name>\"`, each a section of its own" % label,
              names and all(not g[0].startswith("exit") for g in got) and len({g[1] for g in got}) == len(got)
              and any(g[1].startswith("two ") for g in got), (names, [g[0] for g in got]))
    h, t = cs_.get(sx, CASE)
    names = line_names(t)
    check("Task 2 fix I1(c): a past-the-cut heading another one of the note shadows (`Action Items` / `Action items`) "
          "is not named — no name brings back the earlier section",
          all(not back(CASE, n)[1].startswith("early ") for n in names) and "Action items" not in names, names)
    sid = cs_.candidate_id(TWO, "Two bigs › Late")
    h, t = cs_.get(sx, sid)
    names = line_names(t)
    check("Task 2 fix I1(d): a filled section past the cut is never named `Big` (the earlier one); it begins near the top "
          "of the text, so (v3.16.2 C8) it is not named at all", "Big" not in names and "Late › Big" not in names
          and "заголовків далі немає" in t and back(TWO, "Late › Big")[1].startswith("b"), (h, names))
    h, t = cs_.get(sx, SAME)
    names = line_names(t)
    check("Task 2 fix I1(e): a section no name reaches (the same full path twice, `|` in its heading) is left out",
          "Dup" not in names and "Same path › Dup" not in names and not any("|" in n for n in names)
          and all(not back(SAME, n)[0].startswith("exit") for n in names), names)
    h, t = cs_.get(sx, FENCE)
    names = line_names(t)
    check("Task 2 fix M3: a `##` inside a code fence and a `####` heading past the cut are not named; `Real` is",
          names == ["Real"], names)
    flat = "Notes/Long/Flat full.md"
    write(env.note(flat), "Flat full stripes. " + "g" * 34000 + "\n")
    env.refresh(sx)
    fid = cs_.candidate_id(flat, "")
    h1, t1 = cs_.get(sx, fid)
    h2, t2 = cs_.get(sx, fid, full=True)
    check("Task 2 fix I2: `--get <id> --full` of a 34 000-character own section — whole, no line (20 000 and the line without)",
          len(t1) > 20000 and "нотатка довга" in t1 and "нотатка довга" not in t2 and len(t2) > 34000, (len(t1), len(t2)))
    res = cs_.run(sx, ["zorg log"], now=NOW)
    cs_.save_last(env.home, res["last"])
    loc = next((c for c in res["candidates"] if c["path"] == LOGF), None)
    h3, t3 = cs_.get(sx, loc["id"], full=True) if loc else (None, "")
    check("…`--get <id> --full` of a note-level local-index candidate: whole, no line",
          loc and loc["source"] == ["zorg-brain"] and "two " in t3 and "нотатка довга" not in t3, (loc, len(t3 or "")))

check("Task 2 fix M5 — search-protocol §4: the 600-character bound of the names; the by-id paragraph points at the cut; "
      "context-protocol has no «server ;»",
      "the first 20 or 600 characters of them" in section(SP, 4)
      and "is cut at 20 000 characters" in section(SP, 4).split("`--get` also takes a note's path")[0]
      and "server ;" not in read(ROOT, "references", "context-protocol.md"), section(SP, 4)[:600])

# Task 3 review, round 3b: the end of a path never silently swaps in another note; an exact heading path first
PLAN, ARCH = "Notes/Concepts/Zorg plan.md", "Notes/Archive/Concepts/Zorg plan.md"
with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    para3 = lambda w: (" ".join([w] * 60)) + "."
    write(env.note(PLAN), "---\ntype: concept\n---\n# Zorg plan\n\n" + para3("current") + "\n")
    write(env.note(ARCH), "---\ntype: concept\n---\n# Zorg plan\n\n" + para3("archived") + "\n")
    write(env.note("Notes/xa/Zorg tail.md"), "# Zorg tail\n\n" + para3("xa") + "\n")
    write(env.note("Notes/@zorg/Zorg at.md"), "# Zorg at\n\n" + para3("atfolder") + "\n")
    write(env.note("Notes/Nest.md"), "# X\n\n## A\n\n### B\n\n" + para3("xab") + "\n\n# A\n\n## B\n\n" + para3("ab") + "\n")
    build_brain(env.brain, env.vault, BRAIN_NOTES + [PLAN])
    sx = env.sctx()

    def got3(arg):
        try:
            return cs_.get(sx, arg)
        except cs_.GetError as e:
            return "exit %d" % e.code, str(e)

    real_dataless = ci.is_dataless
    ci.is_dataless = lambda p_: unicodedata.normalize("NFC", p_).endswith("Notes/Concepts/Zorg plan.md")
    try:
        env.refresh(sx)                                  # the current plan evicted: never indexed, the local index holds it
        hb, tb = got3("[[Concepts/Zorg plan]]")
        build_brain(env.brain, env.vault, BRAIN_NOTES)   # …and no local index holds it either
        hc, tc = got3("[[Concepts/Zorg plan]]")
    finally:
        ci.is_dataless = real_dataless
    check("round 3b I1: an evicted plugin-folder note only a local index holds — `[[Concepts/Zorg plan]]` is that note "
          "(through the local index), never the archived one", hb.startswith("> [own · %s · " % PLAN) and "current" in tb
          and "archived" not in tb, (hb, tb[:120]))
    check("…held by no index at all: the iCloud line for that note, never the archived one",
          hc == "exit 3" and tc == cs_.ICLOUD_MISSING % PLAN, (hc, tc))
    build_brain(env.brain, env.vault, BRAIN_NOTES + [PLAN])
    env.refresh(sx)
    ha, ta = got3("[[Concepts/Zorg plan]]")
    check("…both indexed: the link is the plugin folder's path, not «кілька нотаток»", ha.startswith("> [own · %s · " % PLAN)
          and "current" in ta, (ha, ta[:120]))
    check("round 3b M2: the end of a path starts at a `/` — `[[a/Zorg tail]]` is not `Notes/xa/Zorg tail.md`",
          got3("[[a/Zorg tail]]")[0] == "exit 3", got3("[[a/Zorg tail]]"))
    check("…an `@<repo>/…` name is never the end of another path (a vault folder named `@zorg` too)",
          got3("[[@zorg/Zorg at]]")[0] == "exit 3", got3("[[@zorg/Zorg at]]"))
    hn, tn = got3("Notes/Nest.md#A › B")
    hx, tx = got3("Notes/Nest.md#B")
    check("round 3b M1: a whole heading path asked is that section before an end of a longer one (`A › B`, not `X › A › B`); "
          "a bare `#B` is still the first one (`X › A › B`)", "Nest.md › A › B ·" in hn and tn.startswith("ab")
          and "Nest.md › X › A › B ·" in hx and tx.startswith("xab"), (hn, hx))

# v3.16.2 Task 2: a fold records what it stands for; the folder-name exclusions hold for every source; the real-path
# re-check names a core's file through its root
out = cs_.dedup([entry(N1, "", 0.05, source="zorg-brain", near="k1", date="2026-10-01"),
                 entry(N3, "", 0.01, source="zorg-brain", near="k1", date="2026-09-01"),
                 entry(N4, "", 0.03, source="zorg-brain", near="k1", date="2026-01-01")], {}, own=["Notes"])
check("v3.16.2 C2 (M8): the survivor of a fold records the paths it stands for (`twins`)",
      [c["path"] for c in out] == [N3] and sorted(out[0].get("twins") or []) == sorted([N1, N4]), out)
V1, V2, V3 = "Notes/Roadmap Q4 — draft v1.md", "Notes/Roadmap Q4 — draft v2.md", "Notes/Roadmap Q4 — draft v3.md"
out = cs_.dedup([entry(V1, "", 0.03, sid=1), entry(V2, "", 0.02, sid=2), entry(V3, "", 0.01, sid=3)],
                {V1: meta_of(V1, version_key="vk", date="2026-08-01"), V2: meta_of(V2, version_key="vk", date="2026-09-01"),
                 V3: meta_of(V3, version_key="vk", date="2026-10-01")})
check("…a version fold (key 5) too: the newest stands for the older ones", [c["path"] for c in out] == [V3]
      and sorted(out[0].get("twins") or []) == sorted([V1, V2]), out)
out = cs_.dedup([entry(N2, "", 0.05, source="zorg-brain", near="k1", date="2026-10-07"),
                 entry(N1, "", 0.02, source="zorg-brain", near="k1", date="2026-09-01"),
                 entry(N4, "", 0.01, source="zorg-brain", hash="h4")], {}, own=["Notes"])
pub = [cs_._public(dict(c, source={"zorg-brain"}, sections=[], text=None, snippet=""), []) for c in out]
check("…the public form carries `twins` only when the candidate stands for others",
      pub[0].get("twins") == [N2] and "twins" not in next(p for p in pub if p["path"] == N4), pub)
with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    write(env.note("Growth/_Backup 2025/Kiwi plan.md"), "---\ntype: note\n---\n# Kiwi plan\n\nThe kiwi plan of the cart.\n")
    write(env.note("Growth/Plans/Kiwi plan.md"), "---\ntype: note\n---\n# Kiwi plan\n\nThe kiwi plan of the cart, current.\n")
    build_brain(env.brain, env.vault, ["Growth/_Backup 2025/Kiwi plan.md", "Growth/Plans/Kiwi plan.md"])
    sx = env.sctx()
    env.refresh(sx)
    res = cs_.run(sx, ["kiwi plan"], now=NOW)
    got = [c["path"] for c in res["candidates"]]
    check("v3.16.2 C3 (9, N5): a local hit under `_Backup 2025/` is no candidate — the stale backup can no longer win a fold",
          "Growth/Plans/Kiwi plan.md" in got and not any("_Backup" in p for p in got), got)
with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    ext = os.path.join(d, "_backups", "zorg-ext")
    write(os.path.join(ext, "Teams", "team-numbat.md"), "---\ntype: team\n---\n# Team Numbat\n\nThe numbat team.\n")
    write(os.path.join(ext, "_System", "context-blocks.md"), "# Blocks\n\nThe core's blocks.\n")
    write(os.path.join(env.home, ".grow-pm", "providers", "zorg-ext.yaml"),
          "schema: provider-registration/2\nid: zorg-ext\ntitle: Zorg external core\nkind: folder\nauthority: org\n"
          "core_root: %s\nblocks_file: _System/context-blocks.md\nstatus: active\n" % ext)
    dev = os.path.join(d, "dev", "zorg-dev")
    write(os.path.join(dev, "Pages", "Dev page.md"), "# Dev page\n\nA page of the dev core.\n")
    write(os.path.join(dev, "_System", "context-blocks.md"), "# Blocks\n\nThe dev core's blocks.\n")
    write(os.path.join(env.home, ".grow-pm", "providers", "zorg-dev.yaml"),
          "schema: provider-registration/2\nid: zorg-dev\ntitle: Zorg dev core\nkind: folder\nauthority: org\n"
          "core_root: %s\nblocks_file: _System/context-blocks.md\nstatus: active\n" % dev)
    os.makedirs(env.note("Notes/Links"), exist_ok=True)
    os.symlink(os.path.join(dev, "_System", "context-blocks.md"), env.note("Notes/Links/blocks.md"))
    sx = env.sctx()
    env.refresh(sx)
    write(os.path.join(ext, "Teams", "team-new.md"), "---\ntype: team\n---\n# Team New\n\nA team added after the refresh.\n")

    def got10(arg):
        try:
            return cs_.get(sx, arg)
        except cs_.GetError as e:
            return "exit %d" % e.code, str(e)

    ha, ta = got10("@zorg-ext/Teams/team-numbat.md")
    hb, tb = got10("@zorg-ext/Teams/team-new.md")
    hc, tc = got10("Notes/Links/blocks.md")
    check("v3.16.2 C3 (10): a core under `_backups/` — a note the index holds and one only its file holds read alike",
          "numbat team" in ta and "added after the refresh" in tb, (ha, hb, tb))
    check("…an in-vault link to a core's blocks file is excluded by its real name (`@zorg-dev/_System/context-blocks.md`)",
          hc == "exit 3" and tc.startswith("шлях виключено з пошуку"), (hc, tc))

# v3.16.2 Task 3: every name a search lists is read back from the source that holds it
def got3b(sx, arg):
    try:
        return cs_.get(sx, arg)
    except cs_.GetError as e:
        return "exit %d" % e.code, str(e)


INROOT = "---\ntype: page\n---\n# Zorg pricing\n\nThe pricing page under the root.\n"
OUTROOT = "---\ntype: page\n---\n# Zorg pricing\n\nThe pricing page outside the root.\n"
ONLYOUT = "---\ntype: page\n---\n# Zorg lonely\n\nA page only outside the root.\n"
with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    with FakeMcp(tree={"Growth/Shared/Zorg pricing.md": INROOT, "Shared/Zorg pricing.md": OUTROOT,
                       "Shared/Zorg lonely.md": ONLYOUT}) as s:
        s.handlers["vault_search"] = lambda args: ({"results": [
            {"path": "Growth/Shared/Zorg pricing.md", "title": "Zorg pricing"},
            {"path": "Shared/Zorg pricing.md", "title": "Zorg pricing"}]}, False)
        env.reg("zorg-growth", growth_reg(s.url))
        sx = env.sctx()
        lists, _ = cs_.gather(sx, ["zorg pricing"], cs_.sources(env.text, sx["repos"], which=("mcp",)), deadline())
        names5 = paths(lists, "zorg-growth|v0")
        check("v3.16.2 C5 (5, N3): a server's hit outside endpoint.root is `@<repo>/:/<path as given>` — no collision with "
              "the note under the root", names5 == ["@zorg-growth/Shared/Zorg pricing.md", "@zorg-growth/:/Shared/Zorg pricing.md"],
              names5)
        ha, ta = got3b(sx, "@zorg-growth/Shared/Zorg pricing.md")
        hb, tb = got3b(sx, "@zorg-growth/:/Shared/Zorg pricing.md")
        hc, tc = got3b(sx, "@zorg-growth/Shared/Zorg lonely.md")
        check("…each read back by its path with its own text", "under the root" in ta and "outside the root" in tb, (ta, tb))
        check("…a v3.16.1 name of a note outside the root (no `:`) is an honest «no note» (review I1: no retry that could "
              "swap in another note)", hc == "exit 3" and "only outside the root" not in tc, (hc, tc))

OLD = "---\ntype: team\n---\n# Team Wombat\n\nAn OLD copy of the wombat team, ZORG-1.\n"
NEW = "---\ntype: team\n---\n# Team Wombat\n\nThe wombat team as the server has it, ZORG-2.\n"
with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    core = os.path.join(env.vault, "WombatCore")
    write(os.path.join(core, "Teams", "team-wombat.md"), OLD)
    build_brain(env.brain, env.vault, BRAIN_NOTES + ["WombatCore/Teams/team-wombat.md"])
    shutil.rmtree(core)                                  # the core folder is gone; the local index still holds the old copy
    with FakeMcp(tree={"Core/Teams/team-wombat.md": NEW}) as s:
        s.handlers["vault_search"] = lambda args: ({"results": [{"path": "Core/Teams/team-wombat.md", "title": "Team Wombat"}]}, False)
        env.reg("zorg-wombat", "schema: provider-registration/2\nid: zorg-wombat\ntitle: Zorg wombat\nkind: mcp\nauthority: team\n"
                "core_root: %s\nendpoint:\n  url: %s\n  root: \"Core/\"\nstatus: active\n" % (core, s.url))
        sx = env.sctx()
        env.refresh(sx)
        res = cs_.run(sx, ["team wombat"], now=NOW)
        cs_.save_last(env.home, res["last"])
        cand = next((c for c in res["candidates"] if c["path"] == "WombatCore/Teams/team-wombat.md"), None)
        hi, ti = got3b(sx, cand["id"]) if cand else (None, "")
        hp, tp = got3b(sx, "WombatCore/Teams/team-wombat.md")
        hn, tn = got3b(sx, "team-wombat")
    check("v3.16.2 C6 (6, N4): a core in the vault that is not on disk — id, path and name read through its server",
          cand and "ZORG-2" in ti and "ZORG-2" in tp and "ZORG-2" in tn, (cand, ti[:80], tp[:80], tn[:80]))
    check("…never the local index's old copy served as current; the header names the repository",
          "ZORG-1" not in ti + tp + tn and hp.startswith("> [zorg-wombat · WombatCore/Teams/team-wombat.md"), (hi, hp, hn))

with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    write(env.note("Notes/Zorg kiwi.md"), "---\ntype: note\n---\n# Zorg kiwi\n\nThe kiwi note of the plugin folder.\n")
    build_brain(env.brain, os.path.join(env.vault, "Notes"), ["Zorg kiwi.md"])      # a local index rooted at Notes/
    sx = env.sctx()
    env.refresh(sx)
    hk, tk = got3b(sx, "Zorg kiwi")
    hk2, tk2 = got3b(sx, "Zorg kiwi.md")
    check("v3.16.2 C7 (11): a local index rooted in a subfolder never answers a vault path by its own relative one — "
          "`Zorg kiwi` is `Notes/Zorg kiwi.md`", hk.startswith("> [own · Notes/Zorg kiwi.md · ")
          and hk2.startswith("> [own · Notes/Zorg kiwi.md · ") and "kiwi note" in tk, (hk, hk2))

with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    ext = os.path.join(d, "ext-notes")
    write(os.path.join(ext, "Research", "Zorg quokka study.md"),
          "---\ntype: research\n---\n# Zorg quokka study\n\nThe quokka study of the cart, outside every vault.\n")
    build_brain(env.brain, ext, ["Research/Zorg quokka study.md"])
    sx = env.sctx()
    env.refresh(sx)
    reads13, real_read13 = [], cs_.cst.read_text
    cs_.cst.read_text = lambda p_, *a, **kw: reads13.append(p_) or real_read13(p_, *a, **kw)
    try:
        res = cs_.run(sx, ["quokka study"], now=NOW)
        cs_.save_last(env.home, res["last"])
        q = next((c for c in res["candidates"] if c["path"] == "@zorg-brain/Research/Zorg quokka study.md"), None)
        out13 = [got3b(sx, a) for a in ((q or {}).get("id", "-"), "@zorg-brain/Research/Zorg quokka study.md", "Zorg quokka study",
                                         "[[Zorg quokka study]]")]
    finally:
        cs_.cst.read_text = real_read13
    check("v3.16.2 C7 (13): a local index outside every vault — its candidate read by id, path and name from the index's "
          "own text; the file outside the vault is never opened",
          q and all("outside every vault" in t for _, t in out13) and not any("quokka" in r for r in reads13),
          (q, [h for h, _ in out13], [r for r in reads13 if "quokka" in r]))

# v3.16.2 Task 2 review fixes: twin keys, transitive twins, the innermost core, the backup that could have won
X, Y, Z = "Archive/Zorg plan x.md", "Archive/Zorg plan y.md", "Notes/Zorg plan z.md"
out = cs_.dedup([entry(X, "", 0.05, source="zorg-brain", near="kz", date="2026-09-01"),
                 entry(Y, "", 0.04, source="zorg-brain", date="2026-09-02"),
                 entry(Z, "", 0.01, source="zorg-brain", near="kz", date="2026-10-01")],
                {X: meta_of(X, hash="hh", near="kz"), Y: meta_of(Y, hash="hh")}, own=["Notes"])
check("v3.16.2 review M2: twins are transitive — a survivor stands for the notes folded into what it folded",
      [c["path"] for c in out] == [Z] and out[0].get("twins") == [X, Y], out)
check("…each twin keeps the kind of fold that brought it (internal `twin_keys`: same text — hash, near)",
      out[0].get("twin_keys") == {X: "near", Y: "near"} and "twin_keys" not in cs_._public(
          dict(out[0], source={"zorg-brain"}, sections=[], text=None, snippet=""), []), out[0].get("twin_keys"))
out = cs_.dedup([entry(V1, "", 0.03, sid=1), entry(V3, "", 0.01, sid=3)],
                {V1: meta_of(V1, version_key="vk", date="2026-08-01"), V3: meta_of(V3, version_key="vk", date="2026-10-01")})
check("…a version fold records `version`", out[0].get("twin_keys") == {V1: "version"}, out)
with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    a = os.path.join(d, "zorg-a")
    b = os.path.join(a, "_backups", "zorg-b")
    write(os.path.join(a, "Pages", "A page.md"), "# A page\n\nA page of core a.\n")
    write(os.path.join(b, "Teams", "team-bilby.md"), "# Team Bilby\n\nThe bilby team of core b.\n")
    for rid, folder in (("zorg-a", a), ("zorg-b", b)):
        write(os.path.join(env.home, ".grow-pm", "providers", "%s.yaml" % rid),
              "schema: provider-registration/2\nid: %s\ntitle: %s\nkind: folder\nauthority: org\ncore_root: %s\nstatus: active\n"
              % (rid, rid, folder))
    sx = env.sctx()
    env.refresh(sx)
    write(os.path.join(b, "Teams", "team-new.md"), "# Team New\n\nA team of core b added after the refresh.\n")
    try:
        hb, tb = cs_.get(sx, "@zorg-b/Teams/team-new.md")
    except cs_.GetError as e:
        hb, tb = "exit %d" % e.code, str(e)
    check("v3.16.2 review M1: a core nested under another's `_backups/` — a note only its file holds reads by the innermost "
          "core's name", "added after the refresh" in tb, (hb, tb))
with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    LONGP = "The kiwi plan of the cart: the seller's hours under each block, the paid orders after the test. " * 6
    write(env.note("Growth/_Backup 2025/Kiwi plan.md"), "---\ntype: note\nupdated: 2025-01-01\n---\n# Kiwi plan\n\n" + LONGP + "\n")
    write(env.note("Growth/Plans/Kiwi plan.md"), "---\ntype: note\nupdated: 2026-10-01\n---\n# Kiwi plan\n\n" + LONGP + "\n")
    build_brain(env.brain, env.vault, ["Growth/_Backup 2025/Kiwi plan.md", "Growth/Plans/Kiwi plan.md"])
    sx = env.sctx()
    env.refresh(sx)
    res = cs_.run(sx, ["kiwi plan"], now=NOW)
    plan = next((c for c in res["candidates"] if c["path"] == "Growth/Plans/Kiwi plan.md"), None)
    check("v3.16.2 review M3: an older near copy under `_Backup 2025/` no longer wins the fold as «the original» — the "
          "current plan is listed, with no twin from the backup", plan and not any("_Backup" in f for f in plan["flags"])
          and not any("_Backup" in c["path"] for c in res["candidates"]), [(c["path"], c["flags"]) for c in res["candidates"]])

check("v3.16.2 review M6 — search-protocol §3: `twins` serve your picks and eval; what a mark names is what is read",
      "`twins` serve your remembered picks and `ctx search eval`" in section(SP, 3)
      and "never read a twin because it is listed there" in section(SP, 3), section(SP, 3)[-700:])

# v3.16.2 Task 3 review fixes: no retry that swaps a note; a vanished core's rows go; the id header names the server;
# a real `~` folder; a deleted vault file is not served from a local index by id
with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    with FakeMcp(tree={"Growth/~/Zorg tilde.md": "# Zorg tilde\n\nUnder the root, in a folder named ~.\n",
                       "Zorg tilde.md": "# Zorg tilde\n\nOutside the root.\n",
                       "Shared/Zorg readme.md": "# Zorg readme\n\nThe whole vault's readme, not the core's.\n"}) as s:
        s.handlers["vault_search"] = lambda args: ({"results": [{"path": "Growth/~/Zorg tilde.md", "title": "Zorg tilde"},
                                                                {"path": "Zorg tilde.md", "title": "Zorg tilde"}]}, False)
        env.reg("zorg-growth", growth_reg(s.url))
        sx = env.sctx()
        lists, _ = cs_.gather(sx, ["zorg tilde"], cs_.sources(env.text, sx["repos"], which=("mcp",)), deadline())
        names_t = paths(lists, "zorg-growth|v0")
        ht1, tt1 = got3b(sx, "@zorg-growth/~/Zorg tilde.md")
        ht2, tt2 = got3b(sx, "@zorg-growth/:/Zorg tilde.md")
        hr, tr = got3b(sx, "@zorg-growth/Shared/Zorg readme.md")
    check("v3.16.2 review M1: a real folder named `~` under the root is its own name; outside the root is `@<repo>/:/…`",
          names_t == ["@zorg-growth/~/Zorg tilde.md", "@zorg-growth/:/Zorg tilde.md"] and "folder named ~" in tt1
          and "Outside the root" in tt2, (names_t, tt1[:60], tt2[:60]))
    check("v3.16.2 review I1: no retry — an under-root name the server does not have is exit 3, never the whole vault's "
          "note of that path", hr == "exit 3" and "whole vault" not in tr, (hr, tr))

with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    core = os.path.join(env.vault, "WombatCore")
    write(os.path.join(core, "Teams", "team-wombat.md"), OLD)
    with FakeMcp(tree={"Core/Teams/team-wombat.md": "---\ntype: team\nupdated: 2026-10-01\n---\n" + NEW.split("---\n", 2)[2]}) as s:
        s.handlers["vault_search"] = lambda args: ({"results": [{"path": "Core/Teams/team-wombat.md", "title": "Team Wombat"}]}, False)
        env.reg("zorg-wombat", "schema: provider-registration/2\nid: zorg-wombat\ntitle: Zorg wombat\nkind: mcp\nauthority: team\n"
                "core_root: %s\nendpoint:\n  url: %s\n  root: \"Core/\"\nstatus: active\n" % (core, s.url))
        sx = env.sctx()
        env.refresh(sx)                                  # the core indexed while it is on disk …
        held = "WombatCore/Teams/team-wombat.md" in ci.Index(env.home).paths()
        shutil.rmtree(core)                              # … then it moves away
        sx = env.sctx()
        env.refresh(sx)
        gone = "WombatCore/Teams/team-wombat.md" not in ci.Index(env.home).paths()
        hp, tp = got3b(sx, "WombatCore/Teams/team-wombat.md")
        res = cs_.run(sx, ["team wombat"], now=NOW)
        cs_.save_last(env.home, res["last"])
        cand = next((c for c in res["candidates"] if c["path"] == "WombatCore/Teams/team-wombat.md"), None)
        hi, ti = got3b(sx, cand["id"]) if cand else (None, "")
    check("v3.16.2 review I2: a core indexed, then gone from disk — its rows leave the index at the next refresh, and its "
          "path reads through the server", held and gone and "ZORG-2" in tp and "ZORG-1" not in tp, (held, gone, hp, tp[:80]))
    check("v3.16.2 review I3: …by id too, under the server's line and day", cand and "ZORG-2" in ti
          and hi.startswith("> [zorg-wombat · WombatCore/Teams/team-wombat.md · 2026-10-01"), (hi, ti[:60]))

with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    write(env.note("Growth/Zorg gone.md"), "---\ntype: note\n---\n# Zorg gone\n\nA note that will be deleted from the vault.\n")
    build_brain(env.brain, env.vault, BRAIN_NOTES + ["Growth/Zorg gone.md"])
    sx = env.sctx()
    env.refresh(sx)
    res = cs_.run(sx, ["zorg gone"], now=NOW)
    cs_.save_last(env.home, res["last"])
    gc = next((c for c in res["candidates"] if c["path"] == "Growth/Zorg gone.md"), None)
    os.remove(env.note("Growth/Zorg gone.md"))
    hg, tg = got3b(sx, gc["id"]) if gc else (None, "")
    check("v3.16.2 review M2: by id, a vault file deleted since the search is exit 3 «not on disk» — a local index's copy "
          "of it is not served", gc and hg == "exit 3" and "not on disk" in tg, (gc, hg, tg))

# v3.16.2 Task 4: the LONG_NOTE names aligned by heading path, found by a map, the cut-under one only when it helps;
# `#H#C# tips`
with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    EMPTYF = "Growth/Zorg empty notes.md"                 # read from its file: an empty `## Notes` before the cut
    write(env.note(EMPTYF), "# Zorg empty notes\n\n" + "z" * 12000 + "\n\n## Notes\n\n## B\n\n" + "b" * 12000
          + "\n\n### Notes\n\n" + "n " * 200 + "\n")
    TOPF = "Notes/Long/Zorg top heavy.md"                 # one section from the top, past the cut
    write(env.note(TOPF), "# Zorg top heavy\n\n## A\n\n" + "a" * 30000 + "\n")
    MANYH = "Notes/Long/Zorg many headings.md"
    write(env.note(MANYH), "# Zorg many headings\n\n" + "".join("## H%d\n\n%s\n\n" % (i, "h" * 480) for i in range(4000)))
    TIPS = "Notes/Zorg tips.md"
    write(env.note(TIPS), "# Zorg tips\n\n## Delivery\n\n" + "d " * 120 + "\n\n### C# tips\n\n" + "sharp " * 60 + "\n")
    sx = env.sctx()
    env.refresh(sx)
    h, t = cs_.get(sx, EMPTYF)
    names = line_names(t)
    check("v3.16.2 C8 (final M1): an empty heading before the cut named like a sub-heading past it does not take that "
          "sub-heading's place — the section the cut falls under (`B`) is named", "B" in names and "B › Notes" in names
          or ("B" in names and "Notes" in names), names)
    h, t = cs_.get(sx, TOPF)
    check("v3.16.2 C8 (Task 2 review M4): the section the cut falls under is named only when --get of it shows 2 000 "
          "characters more — a section from the top of the note is not", "заголовків далі немає" in t and "далі: A" not in t,
          t[-200:])
    whole_many = cs_._note_of(sx, MANYH)[5]
    t0 = time.monotonic()
    capped = cs_._cap(whole_many, MANYH, False, cs_._note_of(sx, MANYH)[4])
    took = time.monotonic() - t0
    check("v3.16.2 C8 (final M2): the names past the cut of a note with 4 000 headings in well under a second (a map, not "
          "a scan per name)", took < 1.5 and "· ще " in capped, (round(took, 2), capped[-160:]))
    ht, tt = got3b(sx, "[[Zorg tips#Delivery#C# tips]]")
    check("v3.16.2 C9 (Task 3 review M4): `[[Name#Delivery#C# tips]]` — parts joined back with `#` — is `Delivery › C# tips`",
          ht.endswith("› Zorg tips › Delivery › C# tips · " + ht.rsplit(" · ", 1)[-1]) and tt.startswith("sharp"), (ht, tt[:40]))

# Task 4 review fixes: empty heading lines are left out as split_sections leaves them out; the layouts of the review
LAYOUTS = {
    "log": "# Zorg log\n\n## 2026-09-01\n\n### Agenda\n\n" + "a" * 6000 + "\n\n### Notes\n\n## 2026-10-01\n\n### Agenda\n\n"
           + "b" * 20000 + "\n\n### Notes\n\n" + "n " * 300 + "\n\n## 2026-10-08\n\n### Agenda\n\n" + "c " * 300 + "\n",
    "samepath": "# Zorg T\n\n## Notes\n\n## B\n\n" + "b" * 25000 + "\n\n## Notes\n\n" + "n " * 300 + "\n\n## C\n\n" + "c " * 300 + "\n",
    "twoh1": "# Zorg T\n\n## Notes\n\n## B\n\n" + "b" * 25000 + "\n\n# Other\n\n" + "o " * 300 + "\n\n## Notes\n\n" + "n " * 300 + "\n",
    "skip": "# Zorg skip\n\n" + "p" * 3000 + "\n\n### X\n\n" + "x" * 25000 + "\n\n### Y\n\n" + "y " * 300 + "\n\n## Z\n\n" + "z " * 300 + "\n",
    "m1": "# Zorg empty notes\n\n" + "z" * 12000 + "\n\n## Notes\n\n## B\n\n" + "b" * 12000 + "\n\n### Notes\n\n" + "n " * 200 + "\n",
    "render": "# Zorg R\n\n" + "r" * 3000 + "\n\n# Empty parent\n\n## A\n\n" + "a" * 25000 + "\n\n# Empty two\n\n## B\n\n" + "b " * 300 + "\n",
    "log2": "# Zorg log2\n\n" + "i" * 3000 + "\n\n## 2026-10-01\n\n### Notes\n\n" + "n" * 25000 + "\n\n## 2026-10-08\n\n### Agenda\n\n"
            + "a " * 300 + "\n\n## Notes\n\n" + "g " * 300 + "\n",
}
with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    for k, text in LAYOUTS.items():
        write(env.note("Growth/Zorg %s.md" % k), text)
        write(env.note("Notes/Long/Zorg %s.md" % k), text)
    sx = env.sctx()
    env.refresh(sx)
    bad = []
    for k in LAYOUTS:
        got = {}
        for p in ("Growth/Zorg %s.md" % k, "Notes/Long/Zorg %s.md" % k):
            h, t = cs_.get(sx, p)
            names = line_names(t)
            back_ok = all(not got3b(sx, "%s#%s" % (p, n))[0].startswith("exit") for n in names)
            got[p] = names
            if not back_ok or not names:
                bad.append((p, names, t.rsplit("\n\n", 1)[-1][:120]))
        if len(set(map(tuple, got.values()))) != 1:
            bad.append((k, got))
    check("v3.16.2 review I1 (Task 4): seven layouts of empty headings — a file read and the own index's render name the "
          "same headings, each reads back, and none says «заголовків далі немає» while sections lie past the cut", bad == [], bad)
    h, t = cs_.get(sx, "Notes/Long/Zorg samepath.md")
    check("…an empty `## Notes` before the cut never takes the place of the real `## Notes` after it",
          line_names(t) == ["Notes", "C"] and got3b(sx, "Notes/Long/Zorg samepath.md#Notes")[1].startswith("n "), line_names(t))
with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    write(env.note(TWO), "# Two bigs\n\n## Early\n\n### Big\n\n" + "e" * 3500 + "\n\n## Late\n\nshort\n\n### Big\n\n" + "b" * 30000 + "\n")
    sx = env.sctx()
    env.refresh(sx)
    h, t = cs_.get(sx, TWO)
    check("v3.16.2 review M3 (Task 4): a section past the cut whose last part an earlier one shares is named by the end "
          "of its path that reaches it — `Late › Big`, never `Big`", line_names(t) == ["Late › Big"], line_names(t))
    write(env.note("Notes/Zorg chunks.md"), "# Zorg chunks\n\n" + "".join("## Chunk %d\n\n%s\n\n" % (i, "h" * 2200) for i in range(1, 33)))
    env.refresh(sx)
    h, t = cs_.get(sx, "Notes/Zorg chunks.md", full=True)
    check("v3.16.2 review M4 (Task 4): after --full the hint carries --full — the read it names is cut like this one",
          t.rsplit("\n\n", 1)[-1].endswith(' — --get "Notes/Zorg chunks.md#<заголовок>" --full'), t[-160:])
    write(env.note("Notes/Zorg blocks.md"), "# Zorg blocks\n\n## X\n\n" + "x " * 120 + "\n\n### A#B\n\n" + "ab " * 80
          + "\n\n### A\n\n" + "a " * 80 + "\n")
    env.refresh(sx)
    hb, tb = got3b(sx, "[[Zorg blocks#X#A#^blk#B]]")
    check("v3.16.2 review M5 (Task 4): no join across a block part — `#X#A#^blk#B` is not `X › A#B`",
          not tb.startswith("ab "), (hb, tb[:40]))

# v3.16.1: only `ctx index rebuild --download` brings a file down — a search and every form of --get never do
with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    build_brain(env.brain, env.vault, BRAIN_NOTES)
    sx = env.sctx()
    env.refresh(sx)
    pulled, real_download, real_fetch, real_dataless = [], ci.download, ci._fetch, ci.is_dataless
    ci.download = lambda *a, **k: pulled.append(("download", a)) or real_download(*a, **k)
    ci._fetch = lambda *a, **k: pulled.append(("fetch", a)) or "ok"
    ci.is_dataless = lambda p_: True                  # every file evicted
    try:
        res = cs_.run(sx, ["графік роботи продавця"], now=NOW)
        ids = [c["id"] for c in res["candidates"]][:3]
        for arg in ids + [P, "Кошик — графік роботи продавця", "[[Кошик — графік роботи продавця#Рішення]]",
                          "Growth/Cart experiments.md", "![[Кошик — графік роботи продавця]]", "[[Knowledge/Slot rules]]",
                          "[[Notes/Mobile cart notes#^blk]]"]:
            try:
                cs_.get(sx, arg)
            except cs_.GetError:
                pass
        check("v3.16.1: a search and --get by id, path, name and link, every file evicted — nothing brought down from iCloud",
              pulled == [] and res["candidates"], pulled[:3])
    finally:
        ci.download, ci._fetch, ci.is_dataless = real_download, real_fetch, real_dataless
check("v3.16.1: ICLOUD_MISSING names ctx index rebuild --download — a note of the plugin folder, the one it brings down; "
      "fix I2: ICLOUD_OPEN for any other path names Obsidian alone",
      cs_.ICLOUD_MISSING == "файл не завантажено з iCloud: %s — відкрий його в Obsidian або ctx index rebuild --download"
      and getattr(cs_, "ICLOUD_OPEN", None) == "файл не завантажено з iCloud: %s — відкрий його в Obsidian")

# ------------------------------------------------------------------ v3.17.0 Task 1: people notes are sensitive (Q2)
BEA = "ZorgCore/People/bea-two.md"
with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    sx = env.sctx()
    env.refresh(sx)
    con = sqlite3.connect(os.path.join(env.home, ".grow-pm", "index", "sections.sqlite"))
    con.execute("UPDATE notes SET sensitive = 0 WHERE path = ?", (BEA,))
    con.commit()
    con.close()
    res = cs_.run(sx, ["Bea Two data analyst"], now=NOW, refresh=False)
    bea = next((c for c in res["candidates"] if c["path"] == BEA), None)
    check("v3.17.0 Q2: an own candidate of a people type is `sensitive`, whatever the row's column says",
          bea is not None and "sensitive" in bea["flags"], bea)

with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    write(env.note("Growth/Bea profile.md"), "---\ntype: person\nupdated: 2026-07-03\n---\n# Bea profile\n\n"
          "Quokkaplan coaching of the cart funnel.\n")
    build_brain(env.brain, env.vault, BRAIN_NOTES + ["Growth/Bea profile.md"])
    sx = env.sctx()
    srcs = cs_.sources(env.text, sx["repos"], which=("local",))
    lists, _ = cs_.gather(sx, ["Quokkaplan"], srcs, deadline())
    hit_ = next((h for k, l in lists.items() if k.startswith("zorg-brain|") for h in l
                 if h["path"] == "Growth/Bea profile.md"), None)
    check("v3.17.0 Q2: a local-index hit whose frontmatter says `type: person` is sensitive", hit_ is not None
          and hit_.get("sensitive") is True, (hit_, sorted(lists)))
    write(env.note("Growth/Coach.md"), "---\nd_type: D2\nupdated: 2026-07-04\n---\n# Coach\n\nThe coaching log.\n")
    cs_.save_last(env.home, {"dddddddddd": {"source": "zorg-brain", "path": "Growth/Coach.md", "heading": "",
                                            "kind": "local", "title": "Coach", "date": "2026-07-04"}})
    h4, _ = cs_.get(sx, "dddddddddd")
    check("v3.17.0 Q2: --get of a local note with a Step-P field (`d_type`) and no type says ` · sensitive`",
          h4 == "> [zorg-brain · Growth/Coach.md · 2026-07-04 · sensitive]", h4)
    CARD = "# Bea card\n\nThe card.\n"
    with FakeMcp(tree={"Growth/Bea card.md": CARD}) as s:
        s.handlers["vault_get_note"] = lambda args: ({
            "path": args.get("path"), "title": "Bea card", "tags": [], "headings": [], "content": CARD,
            "outgoing_links": [], "frontmatter": {"type": "Person", "updated": "2026-06-02"}}, False)
        env.reg("zorg-growth", growth_reg(s.url))
        sx = env.sctx()
        cs_.save_last(env.home, {"eeeeeeeeee": {"source": "zorg-growth", "path": "@zorg-growth/Bea card.md", "heading": "",
                                                "kind": "mcp", "title": "Bea card", "date": "", "remote": "Growth/Bea card.md"}})
        h5, _ = cs_.get(sx, "eeeeeeeeee")
    check("…of a server's note whose frontmatter says `type: Person`, with no `sensitive`",
          h5 == "> [zorg-growth · @zorg-growth/Bea card.md · 2026-06-02 · sensitive · person]", h5)

with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    BODY = "# Onboarding plan\n\n" + ("Quokkaplan onboarding: the first weeks, the cart funnel, the checkout dashboards. " * 8) + "\n"
    write(env.note("Notes/Onboarding plan.md"), "---\ntype: note\n---\n" + BODY)
    write(env.note("Notes/People/Onboarding plan copy.md"), "---\ntype: person\n---\n" + BODY)
    sx = env.sctx()
    env.refresh(sx)
    res = cs_.run(sx, ["Quokkaplan onboarding"], now=NOW, refresh=False)
    holder = next((c for c in res["candidates"] if c["path"] == "Notes/People/Onboarding plan copy.md"
                   or "Notes/People/Onboarding plan copy.md" in (c.get("twins") or [])), None)
    check("v3.17.0 Q2: a person note folded into another note leaves `sensitive` on the one that stays",
          holder is not None and "sensitive" in holder["flags"], [(c["path"], c["flags"], c.get("twins")) for c in res["candidates"][:4]])

with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    with FakeMcp() as s:
        s.handlers["vault_search"] = lambda args: ({"results": [
            {"path": "Growth/Bea card.md", "title": "Bea card", "type": "Person"},
            {"path": "Growth/Pricing.md", "title": "Pricing", "type": "concept"}]}, False)
        env.reg("zorg-growth", growth_reg(s.url))
        sx = env.sctx()
        lists, _ = cs_.gather(sx, ["Quokkaplan"], cs_.sources(env.text, sx["repos"], which=("mcp",)), deadline())
        got = {h["path"]: h.get("sensitive") for k, l in lists.items() for h in l}
    check("v3.17.0 Q2: a server's hit of a people type (`type: Person`) is sensitive before --get; another type is "
          "not known yet", got.get("@zorg-growth/Bea card.md") is True and got.get("@zorg-growth/Pricing.md") is None, got)

# --- v3.17.0 Task 1 review fixes
for form in ("wild", "s10"):
    with tempfile.TemporaryDirectory() as d:
        env = Env(d)
        write(env.note("Growth/Bea profile.md"), "---\ntype: note\nupdated: 2026-07-03\n---\n# Bea profile\n\n"
              "Quokkaplan coaching of the cart funnel.\n")
        build_brain(env.brain, env.vault, BRAIN_NOTES + ["Growth/Bea profile.md"], form=form)
        con = sqlite3.connect(env.brain)
        col = "fm_json" if form == "wild" else "frontmatter_json"
        con.execute("UPDATE notes SET %s = ?, type = 'person' WHERE path = 'Growth/Bea profile.md'" % col,
                    (json.dumps({"type": "person", "d_type": "D2", "updated": "2026-07-03"}),))
        if form == "s10":
            nid = con.execute("SELECT id FROM notes WHERE path = 'Growth/Bea profile.md'").fetchone()[0]
            con.execute("UPDATE notes_fts SET body = ? WHERE rowid = ?",
                        ("# Bea profile\n\nQuokkaplan coaching of the cart funnel.\n", nid))    # §10 keeps no frontmatter
        else:
            con.execute("UPDATE notes_fts SET body = ? WHERE path = 'Growth/Bea profile.md'",
                        ("# Bea profile\n\nQuokkaplan coaching of the cart funnel.\n",))
        con.commit()
        con.close()
        sx = env.sctx()
        real_dataless = ci.is_dataless
        ci.is_dataless = lambda p_: str(p_).endswith("Bea profile.md")      # evicted: --get serves the index's body
        try:
            heads = []
            for arg in ("Growth/Bea profile.md", "Bea profile"):
                try:
                    heads.append(cs_.get(sx, arg)[0])
                except cs_.GetError as e:
                    heads.append("GetError %s" % e)
            cs_.save_last(env.home, {"ffffffffff": {"source": "zorg-brain", "path": "Growth/Bea profile.md", "heading": "",
                                                    "kind": "local", "title": "Bea profile", "date": "2026-07-03"}})
            heads.append(cs_.get(sx, "ffffffffff")[0])
        finally:
            ci.is_dataless = real_dataless
        check("v3.17.0 review I4 (%s): --get by path, name and id of an evicted note a local index serves says ` · sensitive` "
              "and its type from the index's frontmatter, dated by it" % form,
              all(" · sensitive" in h and h.rstrip("]").endswith("person") and "2026-07-03" in h for h in heads), heads)
with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    write(env.note("Growth/Coach log.md"), "---\ntype: note\nupdated: 2026-07-05\n---\n# Coach log\n\nQuokkaplan coaching.\n")
    build_brain(env.brain, env.vault, BRAIN_NOTES + ["Growth/Coach log.md"])
    con = sqlite3.connect(env.brain)
    con.execute("UPDATE notes SET fm_json = ? WHERE path = 'Growth/Coach log.md'",
                (json.dumps({"type": "note", "d_type": "D2", "updated": "2026-07-05"}),))
    con.commit()
    con.close()
    sx = env.sctx()
    lists, _ = cs_.gather(sx, ["Quokkaplan"], cs_.sources(env.text, sx["repos"], which=("local",)), deadline())
    hit_ = next((h for k, l in lists.items() for h in l if h["path"] == "Growth/Coach log.md"), None)
    check("v3.17.0 review M3: a local-index hit whose frontmatter JSON has a Step-P field (and no people type) is sensitive",
          hit_ is not None and hit_.get("sensitive") is True, hit_)

# ------------------------------------------------------------------ v3.17.0 Task 2: the search the user asks for
SP17 = " ".join(read(ROOT, "references", "search-protocol.md").split())    # `flat` is a name of a test above by now
S13 = section(SP17, 13)
check("v3.17.0 §13: the search the user asks for — every connected context (an unregistered vault/v1 provider joined by "
      "RRF), the nothing-to-search line, an answer of at most five sections, a list of at most ten lines with no --get, "
      "level 2 at once on --all or a named source, the «Де шукав» line, a person by identity only, /find with no text",
      all(x in S13 for x in (
          "A search the user asks for (since v3.17.0)", "`--skill context-navigator`", "reciprocal-rank fusion (k = 60)",
          "`Немає де шукати: підключи вейлт (plugin-configurator) або спільне ядро (context-connect)`",
          "at most **five** sections", "At most ten numbered lines", "This form calls no `--get`", "`--all`",
          "`Де шукав: <id> · <id> (не відповів) · … · живі: <назви>`",
          "`Що шукати? /grow-product-manager:find <запит> [--list] [--all]`", "identity only")), S13[:600])
check("…§1 sends context-navigator's own searches to §13",
      "context-navigator runs Step 0.5 for its \"anything else\" route and for every search the user asks for (§13)"
      in section(SP17, 1), section(SP17, 1)[-600:])
NAV = read(ROOT, "skills", "context-navigator", "SKILL.md")
NAV_FM = NAV.split("\n---", 1)[0]
check("v3.17.0: context-navigator 0.3.0 searches your whole context — the description says so, a missing shared core is "
      "one line and the search goes on, §13 and the «Де шукав» line are named",
      "version: 0.3.0" in NAV_FM and "знайди в моєму контексті" in NAV_FM and len(NAV_FM.split("description: ", 1)[-1].split("\n")[0]) <= 400
      and "`Спільне ядро не підключене — шукаю у твоїй базі`" in NAV and "§13" in NAV and "`Де шукав: …`" in NAV
      and "None → say that no shared context is connected and offer `context-connect`; never invent" not in NAV)

with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    with FakeMcp() as s:
        s.handlers["vault_search"] = lambda args: ({"results": [
            {"path": "Growth/Old plan.md", "title": "Old plan", "type": "concept", "updated": "2026-01-02"}]}, False)
        env.reg("zorg-growth", growth_reg(s.url))
        sx = env.sctx()
        lists, _ = cs_.gather(sx, ["Quokkaplan roadmap"], cs_.sources(env.text, sx["repos"], which=("mcp",)), deadline())
        old = next((h for k, l in lists.items() for h in l if h["path"] == "@zorg-growth/Old plan.md"), None)
    check("v3.17.0 review X1: a server's hit keeps the date its class TTL counts from, `terms` unknown and `asked`",
          old is not None and old.get("ttl_date") == "2026-01-02" and "terms" in old and old["terms"] is None
          and old.get("asked") == 2, old)

# --- v3.17.0 Task 2 review fixes
SP17b = " ".join(read(ROOT, "references", "search-protocol.md").split())
S13b = section(SP17b, 13)
check("v3.17.0 review (Task 2): §13 — a list has no numbered block (I1), only the plugin folder of a vault is indexed "
      "(I2), a person is the card's frontmatter identity, never its body (I3), a server line without a known mark has no "
      "snippet and a line is read before it is remembered (I4), a refreshing index never says the bare «нічого» (I5), a "
      "named source is that source (I6), a usage error stops (M11), a declined live source is named (M12)",
      all(x in S13b for x in (
          "**No numbered block.**", "the rest of a vault only through a registered local index of it",
          "never the card's body", "from its title and heading alone, with no snippet and no «навіщо»",
          "`--get` of that note first", "`Поки нічого прямо про це — індекс оновлюється: N файлів ще не переглянуто`",
          "→ that source, besides the base", "`Пошук не виконано: <помилка>`, and nothing more", "`(пропущено)`",
          "a doubt or a conflict alone offers `живе джерело: …` instead")), S13b[-1500:])
DP = " ".join(read(ROOT, "references", "data-policy.md").split())
check("…data-policy rule 1 names the one exception: a person's directory identity from a registry card",
      "a person's identity — name, e-mail, team and role as a registry card's frontmatter states them, and the card's path"
      in DP, DP[DP.find("1. **Sensitive"):][:900])
NAVb = read(ROOT, "skills", "context-navigator", "SKILL.md")
check("…context-navigator: the person row is identity only, decisions go to decision-log with or without a provider, a "
      "list calls no --get, no-SHELL hosts take §12, «the base» cannot answer",
      "identity only (`references/search-protocol.md` §13)" in NAVb and "with or without a provider" in NAVb
      and "for a list, call no `--get`" in NAVb and "§12 — the files on an FS host" in NAVb
      and "A question the base cannot answer" in NAVb and "A question the core cannot answer" not in NAVb)

# --- v3.17.0 Task 3 review fixes: /find and §13 say one rule
SP17c = " ".join(read(ROOT, "references", "search-protocol.md").split())
check("v3.17.0 review (Task 3) I1: naming a live source or --all answers only §8's breadth question; a VPN or a login, "
      "mail, person profiles and private channels are still asked first (spec criterion 5)",
      "answers §8's question about the breadth" in section(SP17c, 13)
      and "a VPN or a login the session lacks, and the data — mail, person profiles, private channels" in section(SP17c, 13)
      and "is the user's answer to §8's question about the data and the breadth" not in section(SP17c, 13), section(SP17c, 13)[-1600:])
FIND = read(ROOT, "commands", "find.md")
FIND_FM = FIND.split("\n---", 1)[0]
check("…commands/find.md: the guard names the conversational «знайди», the description says notes (not the vault), the "
      "navigator is followed whole, --all keeps §8's questions, the writes are §10's and the index's, a flag is an exact "
      "word and an unknown one stops, the Path rule covers the skill's path",
      "never for a conversational «знайди…»" in FIND_FM and "your vault" not in FIND_FM
      and len(FIND_FM.split("description: ", 1)[-1].split("\n")[0]) <= 260
      and "Follow `skills/context-navigator/SKILL.md` whole" in FIND
      and "A VPN or a login the session lacks, and mail, person profiles or private channels" in FIND
      and "the choices §10 remembers" in FIND and "`Невідомий прапорець: <слово>" in FIND
      and "A bare `skills/<name>/SKILL.md` is read from the same root" in FIND)

# --- v3.17.0 acceptance fix wave: 1-1 notes in every source
with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    write(env.note("Notes/Meetings/Meeting - 2026-09-29 - 1-1 Zorg-Cy.md"),
          "---\ntype: meeting\ndate: 2026-09-29\n---\n# 1-1 Zorg-Cy\n\nQuokkaflat: rent the flat, sign the lease.\n")
    write(env.note("Growth/1on1 Bea/2026-09-22.md"), "---\ntype: meeting\nupdated: 2026-09-22\n---\n# Sync\n\nQuokkaflat items.\n")
    build_brain(env.brain, env.vault, BRAIN_NOTES + ["Growth/1on1 Bea/2026-09-22.md"])
    sx = env.sctx()
    env.refresh(sx)
    res = cs_.run(sx, ["Quokkaflat"], now=NOW, refresh=False)
    own = next((c for c in res["candidates"] if "1-1 Zorg-Cy" in c["path"]), None)
    loc = next((c for c in res["candidates"] if c["path"] == "Growth/1on1 Bea/2026-09-22.md"), None)
    check("v3.17.0 acceptance: a 1-1 note typed `meeting` — own (by its title) and a local index's (by its folder) — is "
          "`sensitive`", own is not None and "sensitive" in own["flags"] and loc is not None and "sensitive" in loc["flags"],
          [(c["path"], c["flags"]) for c in res["candidates"][:5]])
with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    with FakeMcp() as s:
        s.handlers["vault_search"] = lambda args: ({"results": [
            {"path": "Growth/Sync.md", "title": "1:1 — Bea & Zorg", "type": "meeting"}]}, False)
        env.reg("zorg-growth", growth_reg(s.url))
        sx = env.sctx()
        lists, _ = cs_.gather(sx, ["Quokkaflat"], cs_.sources(env.text, sx["repos"], which=("mcp",)), deadline())
        got = {h["path"]: h.get("sensitive") for k, l in lists.items() for h in l}
    check("…a server's hit titled «1:1 — …» is sensitive before --get", got.get("@zorg-growth/Sync.md") is True, got)

# --- v3.17.0 final review fixes in the prose
NAVc = read(ROOT, "skills", "context-navigator", "SKILL.md")
check("v3.17.0 final I2: inside the navigator, recording or revisiting a decision goes to decision-log, asking what "
      "was decided is §13 (decisions in meeting notes too)",
      "recording a decision, or revisiting one the user names → `decision-log`" in NAVc
      and "what was decided about something → §13" in NAVc
      and "the user's own decisions → `decision-log`, with or without a provider" not in NAVc)
FINDc = read(ROOT, "commands", "find.md")
check("v3.17.0 final M2: /find — a dash standing alone is part of the request; only `--word` or `—word` is a flag",
      "A dash standing alone (`—`, `-`) is part of the request" in FINDc
      and "Any other word that starts with `--` or `—` followed by a letter" in FINDc)

# --- v3.18.0 Task 4: who someone or something is comes from `ctx entity`
SP18 = " ".join(read(ROOT, "references", "search-protocol.md").split())
S13e = section(SP18, 13)
check("v3.18.0 §13: «who / what it is» — a question about a person, a team, a mission, a module, a metric, a work item "
      "or a Jira key, or who links to one, asks `ctx entity` first; its lines are the answer with the path; several → its "
      "list; «Не знаю такої сутності» → §13 as usual; a sensitive line outside People as `ctx entity` gives it",
      all(x in S13e for x in ('`ctx entity "<X>" --skill context-navigator`', "**Who or what it is",
                              "`Не знаю такої сутності: «…»`", "`уточни, кого саме`", " · sensitive`")), S13e[-1500:])
check("…the person bullet takes the identity from `ctx entity`, not a card read by hand",
      "the identity `ctx entity` gives" in S13e, S13e[-900:])
NAV18 = read(ROOT, "skills", "context-navigator", "SKILL.md")
check("v3.18.0 context-navigator: a person, a team, a mission or a Jira key goes to `ctx entity` first (§13), and its "
      "Routing names «хто такий» and «що таке <ключ>»",
      '`ctx entity "<X>" --skill context-navigator`' in NAV18 and "«хто такий X»" in NAV18 and "«що таке PROJ-1234»" in NAV18,
      NAV18[-800:])

print("\nRESULT: %s (%d failed)" % ("GREEN ✅" if not fails else "RED ❌", fails))
sys.exit(1 if fails else 0)
