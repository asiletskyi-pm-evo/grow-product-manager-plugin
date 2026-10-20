#!/usr/bin/env python3
"""TC-ctx-3160-search — scripts/ctx_search.py: the sources of a question, their fusion and the priors (since v3.16.0).

The fictional Zorg vault of testing/fixtures/search/ (the plugin folder Notes/, the core ZorgCore/ registered as
zorg-core, the team glossary under home/.grow-pm/) is copied to a temp dir. A user's own local index, zorg-brain.sqlite,
is built here from a part of the fixture notes in the shape such an index has in the wild (`path` in `notes_fts`) and in
the shape of context-provider-protocol.md §10 (`notes_fts` + `notes`, `rowid = notes.id`). Checked: every variant ×
source is a list of its own, a glossary list beside it; a local-index hit under the context store is dropped; MCP is
asked only for a repository with no folder on disk, an unreachable or slow server is one line and the search goes on;
an index of another shape is one line; RRF with the glossary at half weight; the priors (skill type, product, hub,
outdated by status or by the class TTL of the core's manifest, the snapshot's day, glossary only, one word);
`search_types` in the manifest and the check behind validator check 19. Nothing is written to the vault or the store.
Stdlib only; run from the repo root:

  env -u GROW_PM_CONTEXT_PATH -u GROW_PM_PROVIDER_PATHS python3 testing/ctx_search_test.py
"""
import datetime, hashlib, json, os, shutil, sqlite3, subprocess, sys, tempfile, time, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "testing"))
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


def build_brain(path, vault, rels, form="wild", junk=()):
    """A user's own local index over `rels` (vault-relative): "wild" — `path` in notes_fts, meta k/v with `vault`;
    "s10" — context-provider-protocol.md §10, notes_fts rowid = notes.id, meta key/value with `vault_root`; "foreign" —
    neither. `junk` rows (wild only) carry a path that is no path."""
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
            con.execute("INSERT INTO notes(path, top, title, type, date, status, fm_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (rel, rel.split("/")[0], m["title"], m["type"], m["date"], m["status"],
                         json.dumps({"updated": m["ttl_date"]}) if m["ttl_date"] else None))
            con.execute("INSERT INTO notes_fts(path, title, aliases, tags, headings, body) VALUES (?, ?, '', '', '', ?)",
                        (rel, m["title"], text))
        else:
            con.execute("INSERT INTO notes(id, path, vault, title, type, frontmatter_json) VALUES (?, ?, 'Zorg', ?, ?, ?)",
                        (i, rel, m["title"], m["type"], json.dumps(dict({"date": m["date"], "status": m["status"]},
                                                                         **({"updated": m["ttl_date"]} if m["ttl_date"] else {})))))
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
    cs_.priors([team, fresh, person, created], [], None, NOW, ttl)
    check("a team card older than 14 days is outdated", team["score"] == 0.5 and team["flags"] == ["застаріле"], team)
    check("…a fresh one is not, nor a note of a class with no TTL", fresh["flags"] == [] and person["flags"] == [],
          (fresh, person))
    check("…nor one with no updated | snapshot | generated, however old its date", created["flags"] == []
          and created["score"] == 1.0, created)
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
    check("from the index: the card with an old `updated` is outdated, the one dated only by an old `created` is not",
          alpha and alpha["flags"] == ["застаріле"] and beta and beta["flags"] == [] and beta["date"] == "2025-01-01",
          (alpha, beta))
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
check("vault-protocol «In short»: the level-2 triggers are in search-protocol §8",
      "maybe live sources (level 2; triggers in search-protocol §8)" in read(ROOT, "references", "vault-protocol.md"))

print("\nRESULT: %s (%d failed)" % ("GREEN ✅" if not fails else "RED ❌", fails))
sys.exit(1 if fails else 0)
