#!/usr/bin/env python3
"""Grow PM — `ctx search`: where a question goes, how the answers become one list, and what weighs them (v3.16.0).

A question and the variants the session's model wrote for it (Ukrainian, Russian, English, a synonym) go to every
source at once: the plugin's own section index (ctx_index), a local index the user registered (a user's own local
index — an SQLite file, read only) and the MCP server of a repository whose folder is not on disk. Each variant is a
list of its own in each source, and so is the glossary's widening of it (the other names of what the variant names,
ctx_glossary). Reciprocal-rank fusion makes one score of all the lists (k = 60, a glossary list at half weight); the
priors then weigh a candidate by what it is — the skill's artifact types × 1.2, the same product × 1.1 and another
× 0.7, a hub × 0.5, an outdated note × 0.5 — and mark what the reader should know (`знімок від <день>`, `лише
глосарій`, `одне слово`).

- context_for       the search context (`sctx`) of a local-context.md — the vaults, the repositories, the roots of the
                    index, the store and the blocks files as the index names them; `ctx index` builds its scope from it.
- class_ttl         folder prefix → `ttl_days` for the classes whose folder a core's provider manifest names.
- snapshots         folder prefix → day, for the repositories whose snapshot is older than `stale_after_days`.
- Source / sources  where a question goes: `own`, `local` (an index file), `mcp` (a server).
- Hit / gather      one section or note an answer gave; every variant × source, the sources in parallel.
- fuse              RRF over the lists.
- priors            the weights and the marks of the candidates.
- skill_types       a skill's artifact types: `search_types` of references/context-manifest.yaml.
- dedup             one candidate per note (the five keys of spec §6: the same path, Confluence page, content, a twin
                    of your layer and the core, versions), at most two sections of a note.
- candidate_id      a section's stable id: sha1(`path#heading`)[:10].
- snippet           ≤ 300 characters around the first match, the matches in «».
- run               a whole search: the index refreshed, gather → fuse → priors → dedup → the remembered picks
                    (ctx_hints) → the best `limit`.
- last_path / save_last / get   the ids of the last search beside the index, and `--get`: one section with its line
                    of provenance `> [<source> · <path> › <heading> · <day>]`.
- render            the human output of `ctx search`.

Reads the vaults, the cores, the index under <home>/.grow-pm/index/, a local index (mode=ro), the glossary, the block
states and the search memory (`.state/search.json`) of the store; the network only for an MCP source. Writes only
<home>/.grow-pm/index/ — the index (run refreshes it) and last.json (save_last) — never the store or a vault. Stdlib
only.
"""
import datetime
import hashlib
import json
import os
import sqlite3
import sys
import tempfile
import threading
import time
import unicodedata
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx_common as cc  # noqa: E402
import ctx_glossary as gl  # noqa: E402
import ctx_hints as ch  # noqa: E402
import ctx_index as ci  # noqa: E402
import ctx_mcp as cm  # noqa: E402
import ctx_ops as co  # noqa: E402
import ctx_read as cr  # noqa: E402
import ctx_repos as crp  # noqa: E402
import ctx_stem as st  # noqa: E402
import ctx_store as cst  # noqa: E402

N = cc.N
KINDS = ("own", "local", "mcp")
RRF_K = 60                      # reciprocal-rank fusion: Σ w / (RRF_K + rank)
GLOSSARY_W = 0.5                # the weight of a glossary list in the fusion
LIST_LIMIT = 50                 # hits asked of a source for one list
SOURCE_S = 20.0                 # one source's time, all its lists together
OPEN_S = 5.0                    # opening a local index (SQLite's busy timeout)
TYPE_W, SAME_PRODUCT_W, OTHER_PRODUCT_W, HUB_W, OUTDATED_W = 1.2, 1.1, 0.7, 0.5, 0.5
OUTDATED = frozenset(("outdated", "archived", "deprecated", "former", "superseded"))
STALE_AFTER_DAYS = 30           # a registration's `stale_after_days` when it names none (context-provider-protocol.md §6)
SILENT_NOTE = "%s не відповів — без нього"
SCHEMA_NOTE = "індекс %s має незнайому схему — без нього"
PENDING_NOTE = "індекс оновлюється: %d файлів ще не переглянуто"
GLOSSARY_NOTE = "глосарій прочитано не весь: %s"
HUB, STALE, SNAPSHOT, GLOSSARY_ONLY, ONE_WORD = "хаб", "застаріле", "знімок від %s", "лише глосарій", "одне слово"
TWIN, OLDER, NEWER_EXISTS, SENSITIVE = "двійник %s", "є старіші версії: %d", "старіша версія %s", "sensitive"
REBUILT_NOTE = "індекс пошуку був зіпсований або старий — збудовано наново"
REFRESH_NOTE = "індекс пошуку не оновлено (%s) — пошук по тому, що є"
COMMAND_S = 60.0                # the whole search
SNIPPET_W = 300                 # a snippet's characters at most
MAX_SECTIONS = 2                # sections of one note in the list
LAST_NAME = "last.json"
LAST_KEEP = 1000                # ids last.json keeps — the newest; ids are stable, so the searches merge into it
LAST_NOTE = "ідентифікатори пошуку не збережено (%s) — --get знайде лише секції свого індексу"
_META = ("title", "type", "product", "status", "date", "ttl_date")
STATUS_KEYS = ("schema", "updated", "files", "sections", "pending", "skipped_dataless")
_BROKEN = ci.BROKEN_NOTE.split("%s")[0]      # Index.problem of a file SQLite cannot read (a busy one is BUSY_NOTE)
_CLASS_DIR = {"teams": "team_card_dir", "people": "people_dir"}     # any other class: `<class>_dir`
_FM_DATES = ci.DATE_KEYS      # a local hit's date from its frontmatter, in the index's order


# ------------------------------------------------------------------ the search context
def _folder(repo):
    """A repository's core folder as the index takes it: `core_root`, else its first path ("" for none)."""
    return repo.get("core_root") or next(iter(repo.get("paths") or []), "")


def _repo_name(repo, rest, vaults):
    """The index's name of `rest` (a path under the core) for a repository: through its core folder when it has one
    (the vault's name of the file, or `@<id>/…` outside every vault), else `@<id>/<rest>`."""
    rest = N(rest).replace("\\", "/").strip("/")
    folder = _folder(repo)
    if folder:
        return ci.rel_path(os.path.join(folder, rest) if rest else folder, vaults, ci.Root(repo["id"], folder))
    return "@%s%s" % (repo["id"], "/" + rest if rest else "")


def context_for(home, context_text, store_root=None, repos=None):
    """The search context of a local-context.md: {home, text, store_root, store_rel, vaults, repos, roots,
    blocks_rels}. `repos` is crp.load_repos(...) when not given; `roots` is ctx_index.scope; `store_root` is the
    context's store when not given and `store_rel` its index name; `blocks_rels` the index name of the blocks file of
    every repository — the registration's, else (for a repository whose folder is a root) its core manifest's. A caller
    may add `product` (and `product_id`): gather reads the glossary of that product."""
    home = home or os.path.expanduser("~")
    if repos is None:
        repos = crp.load_repos(context_text, home)
    vaults = [v for v, _ in cc.vault_entries(context_text)]
    roots = ci.scope(context_text, repos)
    store_root = store_root or co.store_root_for(context_text, home)
    by_source = {r["source"]: r for r in roots}
    blocks = []
    for r in repos:
        name = r.get("blocks_file") or ""
        root = by_source.get(r.get("id"))
        if not name and root:
            manifest, _ = crp._manifest(root["path"])
            name = manifest.s("blocks_file") if manifest is not None else ""
        if name:
            rel = _repo_name(r, name, vaults)
            if rel not in blocks:
                blocks.append(rel)
    return {"home": home, "text": context_text, "store_root": store_root, "store_rel": ci.rel_path(store_root, vaults),
            "vaults": vaults, "repos": repos, "roots": roots, "blocks_rels": blocks}


def _whole(v):
    """A whole number from an int or a text of digits, else None."""
    if isinstance(v, int) and not isinstance(v, bool):
        return v
    if isinstance(v, str) and v.strip().isdigit():
        return int(v.strip())
    return None


def class_ttl(repos, vaults=None):
    """{folder prefix: days} — for every repository whose core folder is on disk and whose provider manifest
    (crp._manifest) reads, each `ttl_days` class whose folder the manifest names: `teams` → `team_card_dir`, `people`
    → `people_dir` (the bundle builder's defaults Teams/People count as named), any other class → `<class>_dir`. A
    class with no such key (`playbook`, `metrics`) or no positive whole number of days has no TTL. The prefix is the
    folder as the index names it — pass `vaults` (sctx["vaults"]); without them it is `@<id>/…`. A manifest that does
    not read gives nothing."""
    out = {}
    for repo in repos or []:
        folder = _folder(repo)
        if not folder or not os.path.isdir(folder):
            continue
        manifest, _ = crp._manifest(folder)
        ttl = manifest.get("ttl_days") if manifest is not None else None
        if not isinstance(ttl, dict):
            continue
        for cls, days in ttl.items():
            days = _whole(days)
            sub = manifest.get(_CLASS_DIR.get(str(cls), "%s_dir" % cls))
            if days is None or days <= 0 or not isinstance(sub, str) or not sub.strip():
                continue
            prefix = ci.rel_path(os.path.join(folder, sub.strip()), vaults or [], ci.Root(repo["id"], folder))
            out[prefix.rstrip("/")] = days
    return out


def _day(value):
    """The date a value names: a date, a datetime, or a text that starts with YYYY-MM-DD; else None."""
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    try:
        return datetime.date.fromisoformat(str(value or "").strip()[:10])
    except ValueError:
        return None


def _today(now):
    return _day(now) or datetime.date.today()


def snapshots(sctx, now=None):
    """{folder prefix: day} of every repository whose snapshot is older than its `stale_after_days` (30 when it names
    none): the day is the later of the registration's `synced_at` and the day the store last checked the repository
    (its block state, as the session digest counts it, context-provider-protocol.md §6). A repository with neither day
    is not marked. The prefix is its core folder as the index names it, or `@<id>` for one with no folder (its MCP
    hits are named so)."""
    checked = co.checked_by_repo(sctx["store_root"]) if sctx.get("store_root") else {}
    today, out = _today(now), {}
    for repo in sctx.get("repos") or []:
        days = [d for d in (_day(repo.get("synced_at")), _day(checked.get(repo.get("id")))) if d]
        if not days:
            continue
        day = max(days)
        limit = _whole(repo.get("stale_after_days"))
        if (today - day).days > (STALE_AFTER_DAYS if limit is None else limit):
            out[_repo_name(repo, "", sctx.get("vaults") or [])] = day.isoformat()
    return out


# ------------------------------------------------------------------ sources
def Source(id, kind, **extra):
    """Where a question goes: `own` (the section index), `local` (`path`: an index file) or `mcp` (`repo`: the
    registration, with its endpoint)."""
    return dict(extra, id=id, kind=kind)


def _index_file(value):
    path = os.path.expanduser(N(str(value or "")).strip())
    return path if path and os.path.isfile(path) else ""


def sources(context_text, repos, which=KINDS):
    """The sources of a search, in this order: `own` when the index has a root; `local` for every registration with
    `index:` and every `### Vault Search MCP` line with `index = …` whose file exists (a registration first; an id is
    taken once); `mcp` for every registration with `endpoint.url` whose core folder (`core_root`, else its first path)
    is not on disk — its notes are not in the section index — and, when `which` is `mcp` alone, for every one with
    `endpoint.url`. `which` keeps the kinds it names."""
    which = tuple(which or ())
    out, ids = [], set()

    def add(src):
        if src["id"] and src["id"] not in ids:
            ids.add(src["id"])
            out.append(src)

    if "own" in which and ci.scope(context_text, repos):
        add(Source("own", "own"))
    if "local" in which:
        for repo in repos or []:
            path = _index_file(repo.get("index"))
            if path:
                add(Source(repo["id"], "local", path=path))
        for line in cc.vault_search_bullets(context_text):
            path = _index_file(line.get("index"))
            if path:
                add(Source(line["id"], "local", path=path))
    if "mcp" in which:
        alone = set(which) == {"mcp"}
        for repo in repos or []:
            folder = _folder(repo)
            if (repo.get("endpoint") or {}).get("url") and (alone or not (folder and os.path.isdir(folder))):
                add(Source(repo["id"], "mcp", repo=repo))
    return out


# ------------------------------------------------------------------ hits
def Hit(path, heading, source, rank, section_id=None, title=None, date=None, snippet=None, variant=0, list="", **extra):
    """One section (the own index) or note (a local index, MCP) a list gave: `source` the source that holds it — for the
    own index the source of the root its file lies in (`own` for a plugin folder, a repository id for a core folder;
    the list's key still names the source asked, `own|…`), else the local index's or the repository's id; `rank` its
    place in the list (1 first),
    `variant` the variant's number, `list` the list's key. Optional extras: type, product, status, hub and sensitive
    (None: the source did not say), ttl_date (the note's own `updated` | `snapshot` | `generated`, what a class TTL
    counts from; "" when it has none or the source did not say), text (an own hit's section), terms (how many of the
    expression's terms the hit holds; None when not known — an MCP hit, a glossary list), asked (how many terms the
    expression had), remote (an MCP hit's path on the server, for vault_get_note)."""
    return dict(extra, path=path, heading=heading, source=source, rank=rank, section_id=section_id, title=title,
                date=date, snippet=snippet, variant=variant, list=list)


def _fold(word):
    """A word as FTS5's unicode61 with remove_diacritics 2 compares it: the combining marks gone («й» is «и»)."""
    return "".join(c for c in unicodedata.normalize("NFD", word) if not unicodedata.combining(c))


def _held(terms, words):
    """How many of the distinct `terms` the `words` hold, as an FTS5 prefix query matches them: a word equal to the
    term, or starting with it when the term has 4 letters or more."""
    words = {_fold(w) for w in words}
    n = 0
    for t in dict.fromkeys(_fold(t) for t in terms if t):
        if t in words or (len(t) >= 4 and any(w.startswith(t) for w in words)):
            n += 1
    return n


def _glossary_expr(members):
    """An FTS5 expression for the glossary's names: any one of them; a name of several words is all of its words."""
    parts = []
    for m in members:
        if len(m) == 1:
            parts.append(st.fts_or(m))
        elif m:
            parts.append("(%s)" % " AND ".join(st.fts_or([t]) for t in m))
    return " OR ".join(p for p in parts if p)


def _plans(variants, groups):
    """One plan per variant: its number, the stems and the unstemmed words, and the glossary's expression ("" when the
    variant names no group)."""
    out = []
    for i, v in enumerate(variants or []):
        stems = st.query_terms(v)
        raw = list(dict.fromkeys(st.raw_terms(v)))
        out.append({"i": i, "stems": stems, "raw": raw,
                    "glossary": _glossary_expr(gl.expand(stems, groups)) if groups and stems else ""})
    return out


def _usable(path):
    return isinstance(path, str) and bool(path.strip())


def _keep(sctx, rel):
    return not ci.excluded(rel, sctx.get("store_rel"), sctx.get("blocks_rels"))


def _in_scope(rel, prefixes):
    """Is the index name `rel` under one of the roots' names? A root that is a whole vault (its name "") holds the
    vault's names only — never `@<repository>/…` or an absolute path, the names of a core outside every vault that may
    no longer be registered."""
    return any((rel == p or rel.startswith(p + "/")) if p else not rel.startswith(("@", "/")) for p in prefixes)


def _add(lists, key, hits):
    """lists[key] = the hits without a repeated (path, heading), ranked by their place."""
    out, seen = [], set()
    for h in hits:
        k = (h["path"], h["heading"])
        if k not in seen:
            seen.add(k)
            h["rank"] = len(out) + 1
            out.append(h)
    lists[key] = out


# -- the own index
def _own(sctx, src, plans, until, box):
    idx = ci.Index(sctx["home"])
    vaults = sctx.get("vaults") or []
    prefixes = [ci.rel_path(r["path"], vaults, r) for r in sctx.get("roots") or []]
    lists, problems = {}, []

    def ask(key, expr, i, terms):
        rows = idx.query(expr, LIST_LIMIT) if expr else []
        if idx.problem and idx.problem not in problems:
            problems.append(idx.problem)
        hits = []
        for r in rows:
            rel = N(r.get("path") or "")
            if not _usable(rel) or not _in_scope(rel, prefixes) or not _keep(sctx, rel):
                continue
            extra = {"type": r.get("type") or "", "product": r.get("product") or "", "status": r.get("status") or "",
                     "hub": bool(r.get("hub")), "sensitive": bool(r.get("sensitive")),
                     "ttl_date": r.get("ttl_date") or "", "text": r.get("text") or "", "terms": None, "asked": len(terms)}
            if terms:
                words = st.stem_text(" ".join([r.get("title") or "", r.get("heading") or "", r.get("text") or ""]
                                              + list(r.get("tags") or []) + list(r.get("aliases") or []))).split()
                extra["terms"] = _held(terms, words)
            hits.append(Hit(rel, r.get("heading") or "", r.get("source") or src["id"], 0, section_id=r.get("id"), title=r.get("title"),
                            date=r.get("date"), variant=i, list=key, **extra))
        _add(lists, key, hits)

    for p in plans:
        ask("%s|v%d" % (src["id"], p["i"]), st.fts_or(p["stems"]), p["i"], p["stems"])
        if p["glossary"]:
            ask("%s|g%d" % (src["id"], p["i"]), p["glossary"], p["i"], [])
    box["lists"], box["notes"] = lists, problems


# -- a local index
class _Shape(Exception):
    """A local index of neither shape this reader knows."""


def _busy(e):
    text = str(e).lower()
    return "locked" in text or "busy" in text or "interrupted" in text


def _columns(con, table):
    return [r[1] for r in con.execute("PRAGMA table_info(%s)" % table).fetchall()]


def _local_root(con):
    """The folder the index's paths are relative to: meta `vault_root`, else `vault` (columns key/value or k/v)."""
    for key, value in (("key", "value"), ("k", "v")):
        for name in ("vault_root", "vault"):
            try:
                row = con.execute("SELECT %s FROM meta WHERE %s = ?" % (value, key), (name,)).fetchone()
            except sqlite3.OperationalError:
                break
            if row and isinstance(row[0], str) and row[0].strip():
                return os.path.expanduser(N(row[0].strip()))
    return ""


def _local_sql(con):
    """The query of a local index in one of its two shapes, or _Shape: `notes_fts` with a `path` column (the shape a
    user's own local index has in the wild; `notes` joined by path when it has one), or context-provider-protocol.md
    §10 — `notes_fts` beside `notes`, `notes_fts.rowid = notes.id`. Title, type, date, status and product come from
    `notes` (else from `notes_fts`) when a column has them, the rest from its frontmatter JSON when it keeps one."""
    fts = _columns(con, "notes_fts")
    notes = _columns(con, "notes")
    if "path" in fts:
        join = "LEFT JOIN notes ON notes.path = notes_fts.path" if "path" in notes else ""
        path = "notes_fts.path"
    elif "id" in notes and "path" in notes:
        join, path = "JOIN notes ON notes.id = notes_fts.rowid", "notes.path"
    else:
        raise _Shape()
    cols = ["notes_fts.rowid AS rid", "%s AS path" % path]
    for c in ("title", "type", "date", "status", "product"):
        if join and c in notes:
            cols.append("notes.%s AS %s" % (c, c))
        elif c in fts:
            cols.append("notes_fts.%s AS %s" % (c, c))
    fm = next((c for c in ("fm_json", "frontmatter_json") if join and c in notes), None)
    if fm:
        cols.append("notes.%s AS fm" % fm)
    if "body" in fts:
        cols.append("snippet(notes_fts, %d, '«', '»', '…', 24) AS snip" % fts.index("body"))
    return ("SELECT %s FROM notes_fts %s WHERE notes_fts MATCH ? ORDER BY bm25(notes_fts) LIMIT ?"
            % (", ".join(cols), join))


def _fm(raw):
    try:
        data = json.loads(raw) if isinstance(raw, str) and raw.strip() else {}
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def _text_or_none(v):
    return N(v).strip() if isinstance(v, str) and v.strip() else None


def _first_date(data, keys):
    """The first of `keys` that `data` (a frontmatter or a result, as a dict) gives a value for, as text; else None."""
    return next((_text_or_none(str(data[k])) for k in keys if data.get(k) not in (None, "")), None)


def _yes(v):
    """A frontmatter yes (`true`, `yes`, `1`, any case — as the index reads `sensitive` and `search_hub`)."""
    return str(v).strip().lower() in ci.TRUE if v is not None else False


def _local(sctx, src, plans, until, box):
    vaults = sctx.get("vaults") or []
    try:
        con = sqlite3.connect("file:%s?mode=ro" % urllib.parse.quote(src["path"]), uri=True, timeout=OPEN_S)
    except sqlite3.Error:
        box["silent"] = True
        return
    con.row_factory = sqlite3.Row
    con.set_progress_handler(lambda: time.monotonic() > until, 10000)
    try:
        try:
            sql = _local_sql(con)
            folder = _local_root(con)
        except _Shape:
            box["schema"] = True
            return
        except sqlite3.DatabaseError as e:
            box["silent" if _busy(e) else "schema"] = True
            return
        root = ci.Root(src["id"], folder) if folder else None
        lists = {}

        def name(p):
            p = N(p).strip().replace("\\", "/")
            if os.path.isabs(p):
                return ci.rel_path(p, vaults, root)
            if folder:
                return ci.rel_path(os.path.join(folder, p), vaults, root)
            return p.lstrip("/")

        def ask(key, expr, i, terms):
            rows = con.execute(sql, (expr, LIST_LIMIT)).fetchall() if expr else []
            hits, by_rid = [], {}
            for r in rows:
                if not _usable(r["path"]):
                    continue
                rel = name(r["path"])
                if not _usable(rel) or not _keep(sctx, rel):
                    continue
                keys = r.keys()
                fm = _fm(r["fm"]) if "fm" in keys else {}
                meta = {c: (_text_or_none(r[c]) if c in keys else None) or _text_or_none(fm.get(c))
                        for c in ("title", "type", "status", "product")}
                date = (_text_or_none(r["date"]) if "date" in keys else None) or _first_date(fm, _FM_DATES)
                h = Hit(rel, "", src["id"], 0, title=meta["title"], date=date,
                        snippet=_text_or_none(r["snip"]) if "snip" in keys else None, variant=i, list=key,
                        type=(meta["type"] or "").lower(), product=meta["product"] or "",
                        status=(meta["status"] or "").lower(), hub=True if _yes(fm.get("search_hub")) else None,
                        sensitive=_yes(fm.get("sensitive")) if "sensitive" in fm else None,
                        ttl_date=_first_date(fm, ci.TTL_DATE_KEYS) or "", terms=None, asked=len(terms))
                hits.append(h)
                by_rid.setdefault(r["rid"], []).append(h)
            if terms and by_rid:                        # what each hit holds, as the index itself matches it
                marks = ",".join("?" * len(by_rid))
                held = dict.fromkeys(by_rid, 0)
                for t in terms:
                    for (rid,) in con.execute("SELECT rowid FROM notes_fts WHERE notes_fts MATCH ? AND rowid IN (%s)"
                                              % marks, [st.fts_or([t])] + list(by_rid)).fetchall():
                        held[rid] = held.get(rid, 0) + 1
                for rid, hs in by_rid.items():
                    for h in hs:
                        h["terms"] = held.get(rid, 0)
            _add(lists, key, hits)

        try:
            for p in plans:
                ask("%s|v%d" % (src["id"], p["i"]), st.fts_or(p["raw"]), p["i"], p["raw"])
                if p["glossary"]:
                    ask("%s|g%d" % (src["id"], p["i"]), p["glossary"], p["i"], [])
        except sqlite3.DatabaseError as e:
            box["silent" if _busy(e) else "schema"] = True
            return
        box["lists"] = lists
    finally:
        con.close()


# -- an MCP server
def _remote_name(sctx, repo, path):
    """The index's name of a path a server gave: under `endpoint.root` it is the core's — through `core_root` the vault's
    name of the file, `@<repo>/<path>` without one; outside `endpoint.root`, `@<repo>/<path as given>`."""
    p = N(path).strip().replace("\\", "/").lstrip("/")
    root = N(repo["endpoint"].get("root") or "").replace("\\", "/").strip("/")
    if not root:
        return _repo_name(repo, p, sctx.get("vaults") or [])
    if p == root or p.startswith(root + "/"):
        return _repo_name(repo, p[len(root):], sctx.get("vaults") or [])
    return "@%s/%s" % (repo["id"], p)


def _mcp(sctx, src, plans, until, box):
    repo = src["repo"]
    ep = repo["endpoint"]
    jobs = []
    for p in plans:
        jobs.append(("%s|v%d" % (src["id"], p["i"]), st.fts_or(p["raw"]), p["i"], len(p["raw"])))
        if p["glossary"]:
            jobs.append(("%s|g%d" % (src["id"], p["i"]), p["glossary"], p["i"], 0))
    lists, client = {}, None
    for key, expr, i, asked in jobs:
        rows = []
        if expr:
            if client is None:
                client = cm.McpClient(ep["url"], headers=cm.headers_from_env(ep["headers_env"]) if ep["headers_env"]
                                      else {}, deadline=until)
            rows = client.call_list("vault_search", {"query": expr, "limit": LIST_LIMIT})
        hits = []
        for r in rows:
            if not _usable(r.get("path")):
                continue
            rel = _remote_name(sctx, repo, r["path"])
            if not _keep(sctx, rel):
                continue
            date = next((_text_or_none(r.get(k)) for k in ("date", "updated", "modified") if _text_or_none(r.get(k))),
                        None)
            hits.append(Hit(rel, "", src["id"], 0, title=_text_or_none(r.get("title")), date=date,
                            snippet=_text_or_none(r.get("snippet")), variant=i, list=key,
                            type=(_text_or_none(r.get("type")) or "").lower(), product="", status="", hub=None,
                            sensitive=None, ttl_date=_first_date(r, ci.TTL_DATE_KEYS) or "", terms=None, asked=asked,
                            remote=N(r["path"])))
        _add(lists, key, hits)
    box["lists"] = lists


_WORKERS = {"own": _own, "local": _local, "mcp": _mcp}


def _work(fn, sctx, src, plans, until, box):
    try:
        fn(sctx, src, plans, until, box)
    except Exception:  # noqa: BLE001 — a source that fails is one line, never the search
        box.pop("lists", None)
        box["silent"] = True


def gather(sctx, variants, sources, deadline):
    """(lists, notes): every variant × source as a list of Hits, best first — the key `<source>|v<i>`, and
    `<source>|g<i>` for the glossary's other names of what variant i names (the groups of ctx_glossary.load for
    sctx["product"]) — and the lines to print. The sources run in parallel, each in a daemon thread with SOURCE_S
    seconds and never past `deadline` (a time.monotonic() moment); one that fails or does not finish gives
    `<id> не відповів — без нього` and no list, a local index of an unknown shape `індекс <id> має незнайому схему — без
    нього`. Every list of a source that answered is there, empty or not.
    - own: ctx_index.Index.query of the variant's stems (ctx_stem.fts_or of query_terms), LIST_LIMIT sections; rows
      whose path is under no root of the current scope (a registration since removed) do not answer.
    - local: the file opened read only (OPEN_S), either shape of `_local_sql`; the unstemmed words (raw_terms),
      LIST_LIMIT notes; a path relative to the index's meta `vault_root` | `vault` gets the vault's name.
    - mcp: `vault_search` {query: the unstemmed words' expression, limit: LIST_LIMIT}; the header of
      `endpoint.headers_env`; a path is named by `_remote_name`.
    A hit with no usable path is dropped silently, and so is one ctx_index.excluded leaves out (a user's own local index
    also holds the store). A stop-word variant asks nothing: its lists are empty. `notes` also carries the index's
    problem (Index.problem), `індекс оновлюється: N файлів ще не переглянуто` while the own index's last refresh left
    files behind, and the glossary file that could not be read."""
    notes = []
    groups, why = gl.load(sctx["home"], product=sctx.get("product"), product_id=sctx.get("product_id"))
    plans = _plans(variants, groups)
    start = time.monotonic()
    runs = []
    for src in sources or []:
        fn = _WORKERS.get(src.get("kind"))
        if fn is None:
            continue
        until = min(deadline, start + SOURCE_S) if deadline is not None else start + SOURCE_S
        box = {}
        t = threading.Thread(target=_work, args=(fn, sctx, src, plans, until, box), daemon=True)
        t.start()
        runs.append((src, t, until, box))
    lists = {}
    for src, t, until, box in runs:
        t.join(max(0.0, until - time.monotonic()))
        if t.is_alive() or box.get("silent"):
            notes.append(SILENT_NOTE % src["id"])
        elif box.get("schema"):
            notes.append(SCHEMA_NOTE % src["id"])
        else:
            lists.update(box.get("lists") or {})
            notes.extend(n for n in box.get("notes") or [] if n not in notes)
    if any(src.get("kind") == "own" for src, _, _, _ in runs):
        pending = ci.Index(sctx["home"]).status().get("pending") or 0
        if pending:
            notes.append(PENDING_NOTE % pending)
    if why:
        notes.append(GLOSSARY_NOTE % why)
    return lists, notes


# ------------------------------------------------------------------ fusion and priors
def _glossary_key(key):
    return str(key).rsplit("|", 1)[-1].startswith("g")


def fuse(lists):
    """{(path, heading): score} — reciprocal-rank fusion over the lists: Σ w / (RRF_K + rank), the rank a key's place
    in a list (1 first; a key met again in the same list counts once), w GLOSSARY_W for a glossary list (`…|g<i>`), 1
    for the rest. The path is NFC."""
    out = {}
    for key, hits in (lists or {}).items():
        w = GLOSSARY_W if _glossary_key(key) else 1.0
        seen = set()
        for h in hits or []:
            k = (N(h["path"]), h.get("heading") or "")
            if k in seen:
                continue
            seen.add(k)
            out[k] = out.get(k, 0.0) + w / (RRF_K + len(seen))
    return out


def _product_names(product):
    s = N(str(product or "")).strip()
    if not s:
        return set()
    return {cc.slugify(x) for x in (s, s.split(":", 1)[-1]) if x.strip()} - {""}


def _under(path, prefix):
    return path == prefix or path.startswith(prefix.rstrip("/") + "/")


def _longest(path, table):
    """The value of the longest prefix of `table` that holds `path`, or None."""
    best = max((p for p in (table or {}) if _under(path, p)), key=len, default=None)
    return None if best is None else table[best]


def _flag(cand, mark):
    if mark not in cand["flags"]:
        cand["flags"].append(mark)


def priors(cands, skill_types, product, now, ttl, snaps=None):
    """Weigh the candidates in place — before the duplicates are folded (fuse → priors → dedup). A candidate is a dict
    with `path`, `score` and what its source said — `type`, `product`, `status`, `hub` (None or missing: decided here
    from the type and the title, as the index decides it), `title`, `ttl_date` — plus `hits` (the Hits that found it)
    and `flags` (made when missing). `score` is multiplied by:
    - TYPE_W when its type is one of `skill_types` (any case);
    - SAME_PRODUCT_W for the product asked, OTHER_PRODUCT_W for another (no product asked or none on the note: 1);
    - HUB_W for a hub, marked `хаб`;
    - OUTDATED_W, marked `застаріле`, for a status of OUTDATED, or a `ttl_date` (the note's own `updated` | `snapshot`
      | `generated`; a note with none of them is never outdated by age) older than the TTL of the folder class it lies
      in (`ttl`: class_ttl's {prefix: days}).
    Marks that leave the score as it is: `знімок від <день>` for a note under a repository of `snaps` (snapshots'
    {prefix: day}); `лише глосарій` when every hit came from a glossary list; `одне слово` when the variants' hits held
    one term at best of an expression of two or more (hits whose `terms` is not known do not count). A mark is never
    added twice."""
    types = {str(t).lower() for t in skill_types or ()}
    asked = _product_names(product)
    today = _today(now)
    for c in cands or []:
        c.setdefault("flags", [])
        score = float(c.get("score") or 0.0)
        ctype = str(c.get("type") or "").lower()
        if ctype and ctype in types:
            score *= TYPE_W
        mine = _product_names(c.get("product"))
        if asked and mine:
            score *= SAME_PRODUCT_W if asked & mine else OTHER_PRODUCT_W
        hub = c.get("hub")
        if hub is None:
            hub = ctype in ci.HUB_TYPES or bool(ci.HUB_TITLE.search(str(c.get("title") or "")))
        if hub:
            score *= HUB_W
            _flag(c, HUB)
        path = N(c.get("path") or "")
        days = _longest(path, ttl)
        day = _day(c.get("ttl_date"))
        if str(c.get("status") or "").lower() in OUTDATED or (days is not None and day is not None
                                                                and (today - day).days > days):
            score *= OUTDATED_W
            _flag(c, STALE)
        snap = _longest(path, snaps)
        if snap:
            _flag(c, SNAPSHOT % snap)
        for mark in _hit_marks(c.get("hits") or []):
            _flag(c, mark)
        c["score"] = score


def _hit_marks(hits):
    """The marks a candidate owes to the hits that found it: `лише глосарій` when every hit came from a glossary list;
    `одне слово` when the variants' hits held one term at best of an expression of two or more (hits whose `terms` is
    not known do not count)."""
    out = []
    if hits and all(_glossary_key(h.get("list")) for h in hits):
        out.append(GLOSSARY_ONLY)
    known = [h for h in hits if not _glossary_key(h.get("list")) and isinstance(h.get("terms"), int)]
    if known and max(h["terms"] for h in known) == 1 and max(h.get("asked") or 0 for h in known) >= 2:
        out.append(ONE_WORD)
    return out


def skill_types(skill):
    """The artifact types a skill searches for: `search_types` of its entry in references/context-manifest.yaml
    (cr.load_manifest). No skill, an unknown one, an entry without the field or a manifest that cannot be read: []."""
    if not skill:
        return []
    try:
        entry = ((cr.load_manifest().get("skills") or {}).get(skill)) or {}
    except (OSError, ValueError):
        return []
    v = entry.get("search_types") if isinstance(entry, dict) else None
    return [str(x) for x in v] if isinstance(v, list) else []


# ------------------------------------------------------------------ one candidate per note
def candidate_id(path, heading):
    """A candidate's id: the first 10 hex digits of sha1(`path#heading`) — a section has the same id in every search."""
    return hashlib.sha1(("%s#%s" % (path, heading or "")).encode("utf-8")).hexdigest()[:10]


def _entries(lists, fused):
    """One entry per key of the fusion (NFC path, heading), for the priors and dedup: its score, the hits that found it
    and what the sources said of the note — the own index's word first (the local copy), else the first that said it;
    an own section's id and text, an MCP hit's server path (`remote`), the first snippet a source gave."""
    by = {}
    for hits in (lists or {}).values():
        for h in hits or []:
            by.setdefault((N(h["path"]), h.get("heading") or ""), []).append(h)
    out = []
    for (path, heading), score in fused.items():
        hits = by.get((path, heading), [])
        own = next((h for h in hits if h.get("section_id") is not None), None)
        said = ([own] if own else []) + [h for h in hits if h is not own]
        e = {"path": path, "heading": heading, "score": score, "hits": hits, "flags": [],
             "section_id": own["section_id"] if own else None, "text": own.get("text") if own else None,
             "own_source": own["source"] if own else None,
             "hub": own.get("hub") if own else next((h["hub"] for h in hits if h.get("hub") is not None), None),
             "sensitive": any(h.get("sensitive") is True for h in hits),
             "remote": next((h["remote"] for h in hits if h.get("remote")), None),
             "snippet": next((h["snippet"] for h in hits if h.get("snippet")), None)}
        for k in _META:
            e[k] = next((h[k] for h in said if h.get(k)), "")
        out.append(e)
    return out


def _metas(notes_meta):
    """{NFC path: metadata} of Index.notes() (a list) or of a dict by path."""
    if isinstance(notes_meta, dict):
        return {N(p): m for p, m in notes_meta.items() if isinstance(m, dict)}
    return {N(m["path"]): m for m in notes_meta or [] if isinstance(m, dict) and m.get("path")}


def _order(c):
    return (-c["score"], c["path"], c.get("heading") or "")


def _merge(path, entries):
    """Key 1 — the entries of one file are one candidate: its heading the best own section (the local copy), at most
    MAX_SECTIONS sections of it kept, its score the sum of what it keeps (those sections and the note as another source
    found it), its sources a list (those of the own index first — `own` or the core's repository — then the others,
    each by name), its marks those of its entries — the marks of the hits counted again over all of them — and
    `sensitive` when any source says so."""
    entries = sorted(entries, key=_order)
    secs = [e for e in entries if e.get("section_id") is not None]
    rest = [e for e in entries if e.get("section_id") is None]
    kept = secs[:MAX_SECTIONS] + rest
    c = dict((secs or rest)[0])
    for k in _META:
        c[k] = next((e[k] for e in [c] + entries if e.get(k)), "")
    hits = [h for e in entries for h in e.get("hits") or []]
    mine = sorted({h["source"] for h in hits if h.get("section_id") is not None and h.get("source")})
    names = mine + sorted({h["source"] for h in hits if h.get("source")} - set(mine))
    flags = []
    for e in entries:
        flags += [f for f in e.get("flags") or [] if f not in flags and f not in (GLOSSARY_ONLY, ONE_WORD)]
    c.update(path=path, score=sum(e["score"] for e in kept), hits=hits, source=names,
             flags=flags + _hit_marks(hits), sensitive=any(e.get("sensitive") for e in entries),
             sections=[{"heading": e["heading"], "section_id": e["section_id"]} for e in secs[:MAX_SECTIONS]]
             or [{"heading": c["heading"], "section_id": None}],
             remote=next((e["remote"] for e in entries if e.get("remote")), None),
             snippet=c.get("snippet") or next((e["snippet"] for e in entries if e.get("snippet")), None))
    return c


def _title_key(title):
    return " ".join(N(str(title or "")).split()).casefold()


def dedup(cands, notes_meta):
    """The candidates without duplicates, best first — the keys of the spec (§6) in turn:
    1. the same path (NFC) — one candidate (`_merge`);
    2. the same `confluence_id` in two files of the index — the newer by its date stays, marked `двійник <path>` of
       the other;
    3. the same `hash` — the better one stays, marked `двійник <path>`;
    4. the same title (normalised) when the `links` of one hold the file name of the other (a hub of your layer and
       the core page) — the one with more text (`size`) stays, marked `двійник <path>`;
    5. the same `version_key` — the newer by its date stays, marked `є старіші версії: N` (the older ones the index
       holds); a version that is not the newest the index holds is marked `старіша версія <path of the newest>`.
    A candidate that stays keeps the best score of those it stands for, and their `sensitive`. `cands` are entries (one per path and heading,
    weighed by the priors: path, heading, score, flags, hits, section_id, title, …); `notes_meta` Index.notes() — the
    keys 2–5 read hash, size, links, version_key, confluence_id and date there, so they hold for files of the index.
    `sensitive` (any source, or the index) is a mark too."""
    groups = {}
    for e in cands or []:
        groups.setdefault(N(e["path"]), []).append(e)
    out = sorted((_merge(p, es) for p, es in groups.items()), key=_order)
    metas = _metas(notes_meta)
    gone = set()

    def meta(c):
        return metas.get(c["path"]) or {}

    def when(c):
        return str(meta(c).get("date") or c.get("date") or "")

    def fold(keep, others, mark=None):
        for o in others:
            if o is not keep and id(o) not in gone:
                gone.add(id(o))
                keep["score"] = max(keep["score"], o["score"])
                if o.get("sensitive") or meta(o).get("sensitive"):
                    keep["sensitive"] = True            # what it stands for is sensitive: the mark stays (spec §7.4)
                if mark:
                    _flag(keep, mark % o["path"])

    def grouped(key):
        by = {}
        for c in out:
            k = key(c) if id(c) not in gone else None
            if k:
                by.setdefault(k, []).append(c)
        return [g for g in by.values() if len(g) > 1]

    for g in grouped(lambda c: str(meta(c).get("confluence_id") or "").strip()):
        fold(max(g, key=lambda c: (when(c), c["score"])), g, TWIN)
    for g in grouped(lambda c: meta(c).get("hash")):
        fold(g[0], g, TWIN)
    for g in grouped(lambda c: _title_key(meta(c).get("title") or c.get("title"))):
        comp = {id(c): id(c) for c in g}

        def root(i):
            while comp[i] != i:
                i = comp[i]
            return i
        for a in g:
            for b in g:
                if a is not b and ci.name_key(b["path"]) in (meta(a).get("links") or []):
                    comp[root(id(a))] = root(id(b))
        parts = {}
        for c in g:
            parts.setdefault(root(id(c)), []).append(c)
        for part in parts.values():
            if len(part) > 1:
                fold(max(part, key=lambda c: (meta(c).get("size") or 0, c["score"])), part, TWIN)
    for g in grouped(lambda c: meta(c).get("version_key")):
        fold(max(g, key=lambda c: (when(c), c["score"])), g)
    live = [c for c in out if id(c) not in gone]
    for c in live:
        vk = meta(c).get("version_key")
        if vk:
            mine = when(c)
            versions = [m for m in metas.values() if m.get("version_key") == vk]
            newest = max(versions, key=lambda m: (str(m.get("date") or ""), N(m.get("path") or "")))
            if str(newest.get("date") or "") > mine:
                _flag(c, NEWER_EXISTS % N(newest["path"]))
            older = sum(1 for m in versions if str(m.get("date") or "") < mine)
            if older:
                _flag(c, OLDER % older)
        if c.get("sensitive") or meta(c).get("sensitive"):
            c["sensitive"] = True
            _flag(c, SENSITIVE)
    return sorted(live, key=_order)


# ------------------------------------------------------------------ the snippet
def _fits(word, keys):
    """Does the word's stem meet one of the keys as the index matched it: equal, or starting with a key of 4 letters
    or more (the diacritics folded, as FTS5's remove_diacritics does)?"""
    s = _fold(st.stem(word))
    return any(s == k or (len(k) >= 4 and s.startswith(k)) for k in keys)


def _cut(text, room):
    """`text` cut to `room` characters at a space, with `…` (room counts it)."""
    if len(text) <= room:
        return text
    part = text[:max(0, room - 1)]
    space = part.rfind(" ")
    return (part[:space] if space > 0 else part).rstrip() + "…"


def snippet(text, terms, width=SNIPPET_W):
    """At most `width` characters of `text` on one line (its whitespace folded, NFC): a window that starts a little before
    the first word whose stem begins with one of `terms` (a term shorter than 4 letters: the whole stem), every such
    word in the window in «»; `…` where the text is cut. No word matches: the start of the text."""
    flat = " ".join(N(text or "").split())
    if not flat or width < 1:
        return ""
    keys = [k for k in dict.fromkeys(_fold(st.norm(t)) for t in terms or [] if t) if k]
    spans = [(m.start(), m.end()) for m in st._TOKEN.finditer(flat) if keys and _fits(m.group(), keys)]
    start = 0
    if spans and spans[0][0] > width // 4:
        space = flat.find(" ", spans[0][0] - width // 4)
        start = spans[0][0] if space < 0 or space >= spans[0][0] else space + 1
    out, pos = ("…" if start else ""), start
    for s, e in spans:
        if s < pos:
            continue
        piece = flat[pos:s] + "«" + flat[s:e] + "»"
        if len(out) + len(piece) + (1 if e < len(flat) else 0) > width:
            break
        out, pos = out + piece, e
    return out + _cut(flat[pos:], width - len(out))


# ------------------------------------------------------------------ run
def _note(notes, more):
    for n in more or []:
        if n not in notes:
            notes.append(n)


def _kind(c):
    """(kind, source) of the text a candidate is read from: `own` (an own section; its source the root's — `own` or the
    core's repository), `local` (the file on disk a local index named) or `mcp` (the server)."""
    if c.get("section_id") is not None:
        return "own", c.get("own_source") or "own"
    hits = c.get("hits") or []
    local = next((h for h in hits if not h.get("remote")), None)
    if local is not None:
        return "local", local["source"]
    return "mcp", next((h["source"] for h in hits if h.get("remote")), (c.get("source") or [""])[0])


def _public(c, terms):
    """A candidate as the search prints it."""
    path = c["path"]
    if c.get("text") is not None:
        snip = snippet(c["text"], terms)
    else:
        snip = _cut(" ".join(N(c.get("snippet") or "").split()), SNIPPET_W)
    return {"id": candidate_id(path, c["heading"]), "path": path, "heading": c["heading"], "title": c.get("title") or "",
            "type": c.get("type") or "", "product": c.get("product") or "", "date": c.get("date") or "",
            "source": list(c["source"]), "flags": list(c["flags"]),
            "matched": sorted({h.get("variant", 0) + 1 for h in c.get("hits") or []}), "snippet": snip,
            "score": round(c["score"], 6),
            "sections": [{"id": candidate_id(path, s["heading"]), "heading": s["heading"]} for s in c["sections"]]}


def _last(c):
    """The last.json entries of a candidate: {id: {source, path, heading, kind, title, date[, section_id][, remote]}}
    — one per section it lists."""
    kind, src = _kind(c)
    base = {"source": src, "path": c["path"], "kind": kind, "title": c.get("title") or "", "date": c.get("date") or ""}
    if c.get("remote"):
        base["remote"] = c["remote"]
    if kind != "own":
        return {candidate_id(c["path"], c["heading"]): dict(base, heading=c["heading"])}
    return {candidate_id(c["path"], s["heading"]): dict(base, heading=s["heading"], section_id=s["section_id"])
            for s in c["sections"]}


def _refresh(idx, sctx, budget, notes):
    """Index.refresh within `budget`; what it did, or None when SQLite could not do it (a line says so)."""
    try:
        res = idx.refresh(sctx["roots"], sctx["store_rel"], sctx["blocks_rels"], budget=budget)
    except (sqlite3.Error, OSError) as e:
        _note(notes, [REFRESH_NOTE % e])
        return None
    if res.get("rebuilt"):
        _note(notes, [REBUILT_NOTE])
    return res


def run(sctx, queries, skill=None, product=None, limit=LIST_LIMIT, which=KINDS, use_hints=True, now=None):
    """One search: {candidates, notes, sources, index, last}.
    - The own index is refreshed first (ctx_index.REFRESH_S, never past the command's COMMAND_S); then every query ×
      source (`gather`, the sources of `which`), RRF (`fuse`), the priors (`skill`'s types, `product`, the classes'
      TTL and the repositories' snapshots), `dedup`, the best `limit`.
    - The remembered picks (ctx_hints) of the request — the first query, not its variants — weigh the candidates
      after dedup and before the best `limit` are cut, so a pick can rise into them: a `good` note × 1.5 and
      `твій вибір від <день>`, a `bad` one `ти казав «не те»`; with `use_hints` False they are not read. A memory that
      cannot be read in OPEN_S is no hint and one line, `пам'ять пошуку не прочитано (<why>) — без підказок`.
    - A query that finds the own index damaged (Index.problem: a file SQLite cannot read, never a busy one) rebuilds
      it once and asks the own index again; REBUILT_NOTE says so. An own index that stays unread — busy (BUSY_NOTE;
      never rebuilt) or still damaged — has not answered: its lists are dropped, and its line stays.
    - candidates: {id, path, heading, title, type, product, date, source [ids], flags, matched [the queries that
      found it, from 1], snippet, score, sections [{id, heading}: the candidate's own first, at most MAX_SECTIONS]};
      a source of the own index is the root's (`own` for a plugin folder, the repository's id for a core folder).
    - notes: the lines to print under the list; sources: [{id, kind, answered}] (none answered: the caller exits 5;
      none at all: there is no place to search); index: the own index's state and what the refresh did (None when the
      own index was not asked); last: what save_last keeps for `--get`.
    Writes only the index; nothing else."""
    start = time.monotonic()
    deadline = start + COMMAND_S
    queries = [q for q in queries or [] if isinstance(q, str)]
    if product:
        sctx = dict(sctx, product=product)
    srcs = sources(sctx["text"], sctx["repos"], tuple(which or KINDS))
    notes, index, done = [], None, None
    idx = ci.Index(sctx["home"])
    own = [s for s in srcs if s["kind"] == "own"]
    if own:
        done = _refresh(idx, sctx, max(0.0, min(ci.REFRESH_S, deadline - time.monotonic())), notes)
    lists, more = gather(sctx, queries, srcs, deadline) if srcs else ({}, [])
    if own and any(n.startswith(_BROKEN) for n in more):
        try:
            idx.rebuild(sctx["roots"], sctx["store_rel"], sctx["blocks_rels"],
                        budget=max(0.0, min(ci.REFRESH_S, deadline - time.monotonic())))
            again, more2 = gather(sctx, queries, own, deadline)
        except (sqlite3.Error, OSError):
            again, more2 = None, []
        if again is not None and not any(n.startswith(_BROKEN) for n in more2):
            lists = dict({k: v for k, v in lists.items() if not k.startswith("own|")}, **again)
            more = [n for n in more if not n.startswith(_BROKEN)] + [REBUILT_NOTE] + more2
    busy = own and ci.BUSY_NOTE in more
    if own and (busy or any(n.startswith(_BROKEN) for n in more)):
        lists = {k: v for k, v in lists.items() if not k.startswith("own|")}     # the base was not read: no answer
    _note(notes, more)
    hints = []
    if use_hints and queries and sctx.get("store_root"):
        try:
            hints = ch.match(ch.load(cst.Store(sctx["store_root"]), timeout=OPEN_S), queries[0], product)
        except cst.StoreError as e:
            _note(notes, [ch.UNREAD_NOTE % e])
    answered = {k.split("|", 1)[0] for k in lists}
    entries = _entries(lists, fuse(lists))
    priors(entries, skill_types(skill), product, now, class_ttl(sctx["repos"], sctx["vaults"]), snapshots(sctx, now))
    metas = idx.notes() if os.path.isfile(idx.db_path) and not busy else []
    cands = dedup(entries, metas)
    if hints:
        ch.apply(cands, hints, _today(now))
        cands.sort(key=_order)
    cands = cands[:max(1, int(limit))]
    terms = list(dict.fromkeys(t for q in queries for t in st.query_terms(q)))
    last = {}
    for c in cands:
        last.update(_last(c))
    if own:
        state = idx.status() if not busy else {k: idx._state().get(k) for k in STATUS_KEYS}   # busy: no second wait
        index = dict(state, **{k: (done or {}).get(k, 0) for k in ("added", "changed", "removed")},
                     locked=bool((done or {}).get("locked")), rebuilt=bool((done or {}).get("rebuilt")) or REBUILT_NOTE in notes)
    return {"candidates": [_public(c, terms) for c in cands], "notes": notes,
            "sources": [{"id": s["id"], "kind": s["kind"], "answered": s["id"] in answered} for s in srcs],
            "index": index, "last": last}


def last_path(home):
    """`<home>/.grow-pm/index/last.json` — the ids of the last search: {id: {source, path, heading, kind, …}}."""
    return os.path.join(ci.index_dir(home), LAST_NAME)


def save_last(home, last):
    """Merge `run`'s `last` into last.json beside the index (the only file the search writes outside the index itself):
    ids are stable, so one session's search keeps another's ids for `--get`; the newest LAST_KEEP stay. Written through
    a temp file of its own in the same folder (`.last.json.<random>.tmp`, the shape ctx_store sweeps), then replaced —
    two searches at once never take each other's temp file. Returns None, or why it could not save: the search's
    result and exit code never depend on it."""
    path, tmp = last_path(home), None
    try:
        cst.check_target(path)
        folder = os.path.dirname(path)
        os.makedirs(folder, exist_ok=True)
        merged = _load_last(home)
        for k, v in (last or {}).items():
            merged.pop(k, None)
            merged[k] = v
        fd, tmp = tempfile.mkstemp(prefix=".%s." % LAST_NAME, suffix=".tmp", dir=folder)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(dict(list(merged.items())[-LAST_KEEP:]), f, ensure_ascii=False, indent=1)
            f.write("\n")
        os.replace(tmp, path)
        return None
    except (OSError, ValueError, cst.PathRefused) as e:
        if tmp:
            try:
                os.remove(tmp)
            except OSError:
                pass
        return str(e) or e.__class__.__name__


# ------------------------------------------------------------------ --get
class GetError(Exception):
    """`--get` cannot print the section: `code` 3 (no such candidate, no such note or section) or 5 (its server did
    not answer); the message is one line."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def _load_last(home):
    try:
        with open(last_path(home), encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _in_index(idx, cid):
    """The last.json entry of an own section whose id is `cid`, found among the sections of the index; else None."""
    for sid, path, heading in idx.headings():
        if candidate_id(N(path), heading) == cid:
            return {"source": "own", "path": N(path), "heading": heading, "kind": "own", "section_id": sid}
    return None


def _section_of(text, heading):
    """The text under `heading` (a heading path as ctx_index.split_sections names it); "" — the note without its
    frontmatter. None when the note has no such heading."""
    if not heading:
        return ci._frontmatter((text or "").replace("\r\n", "\n"))[1].strip("\n")
    return next((body for h, body in ci.split_sections(text) if h == heading), None)


def _inside(path, folders):
    real = os.path.realpath(path)
    return any(real == f or real.startswith(f.rstrip(os.sep) + os.sep) for f in (os.path.realpath(x) for x in folders if x))


def _from_disk(sctx, entry):
    """(text, date) of a note on disk, by its index name: a vault's file, or `@<repository>/…` under its core folder.
    Only a `.md` file inside a vault or a core folder is read."""
    path = entry["path"]
    folders = list(sctx.get("vaults") or []) + [_folder(r) for r in sctx.get("repos") or []]
    if path.startswith("@"):
        rid, _, rest = path[1:].partition("/")
        repo = next((r for r in sctx.get("repos") or [] if r.get("id") == rid), None)
        files = [os.path.join(_folder(repo), *rest.split("/"))] if repo and _folder(repo) and rest else []
    else:
        files = [os.path.join(v, *path.split("/")) for v in sctx.get("vaults") or []]
    found = next((f for f in files if f.lower().endswith(".md") and _inside(f, folders) and os.path.isfile(f)), None)
    if not found:
        raise GetError(3, "the note is not on disk: %s" % path)
    try:
        text = cst.read_text(found)
    except (OSError, UnicodeError, cst.StoreError) as e:
        raise GetError(3, "the note cannot be read: %s (%s)" % (path, e))
    return text, ci.note_meta(path, text).get("date") or ""


def _from_mcp(sctx, entry):
    """(text, date) of an MCP candidate: vault_get_note on the path as the server gave it."""
    repo = next((r for r in sctx.get("repos") or [] if r.get("id") == entry.get("source")), None)
    ep = (repo or {}).get("endpoint") or {}
    if not ep.get("url") or not entry.get("remote"):
        raise GetError(3, "%s: no MCP endpoint to read %s" % (entry.get("source"), entry["path"]))
    try:
        client = cm.McpClient(ep["url"], headers=cm.headers_from_env(ep["headers_env"]) if ep.get("headers_env") else {},
                              deadline=time.monotonic() + SOURCE_S)
        note = client.call("vault_get_note", {"path": entry["remote"]})
    except Exception:  # noqa: BLE001 — a server that fails is one line, as in the search
        raise GetError(5, SILENT_NOTE % entry.get("source"))
    content = note.get("content")
    if not isinstance(content, str):
        raise GetError(3, "%s has no note %s" % (entry.get("source"), entry["remote"]))
    fm = note.get("frontmatter") if isinstance(note.get("frontmatter"), dict) else {}
    return content, _first_date(fm, ci.DATE_KEYS) or ""


def get(sctx, cid):
    """(header, text) of a candidate's section: the header `> [<source> · <path> › <heading> · <day>]` (an own section
    names the index's source of its note: `own`, or the repository of a core page), the text under
    the heading (a note-level candidate: the note without its frontmatter). The id is looked up in last.json (the last
    search), else among the sections of the own index. An own section is read from the index (from its file when the
    note changed since); a note only a local index knows from the vault; an MCP one through vault_get_note. GetError:
    3 — no such id, note or section; 5 — the server did not answer. Reads only."""
    cid = str(cid or "").strip().lower()
    idx = ci.Index(sctx["home"])
    entry = _load_last(sctx["home"]).get(cid)
    if not isinstance(entry, dict) or not entry.get("path"):
        entry = _in_index(idx, cid)
    if not entry:
        raise GetError(3, "no candidate %s in the last search or the section index — search again" % cid)
    heading, date, text = entry.get("heading") or "", entry.get("date") or "", None
    if entry.get("kind") == "own":
        sec = idx.section(entry.get("section_id")) if entry.get("section_id") is not None else None
        if sec and N(sec["path"]) == entry["path"] and (sec.get("heading") or "") == heading:
            text, date = sec.get("text") or "", sec.get("date") or date
            entry = dict(entry, source=sec.get("source") or entry.get("source"))
    if text is None:
        body, day = _from_mcp(sctx, entry) if entry.get("kind") == "mcp" else _from_disk(sctx, entry)
        text, date = _section_of(body, heading), date or day
        if text is None:
            raise GetError(3, "no section %s in %s" % (heading, entry["path"]))
    return "> [%s · %s%s · %s]" % (entry.get("source") or "own", entry["path"], " › " + heading if heading else "",
                                   (date or "—")[:10]), text


# ------------------------------------------------------------------ the human output
def _variants_word(n):
    if n % 10 == 1 and n % 100 != 11:
        return "варіант"
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return "варіанти"
    return "варіантів"


def _shown(title, heading):
    """A heading as the list shows it: without its first part when that is the note's title."""
    parts = [p for p in (heading or "").split(" › ") if p]
    if parts and title and parts[0].casefold() == str(title).casefold():
        parts = parts[1:]
    return " › ".join(parts)


def render(res, queries):
    """The human output of `run`'s result: `Пошук: <n> варіант(и) · джерела: <ids> · кандидатів <k>`; per candidate
    `N. <title> › <heading> · <sources> · <type> · <date>[ · <mark>…]`, its snippet, `id <id> · варіанти <i,…>` and,
    for a second section of the note, `також: <heading> · id <id>`; then the notes."""
    n = len(queries or [])
    said = [s["id"] for s in res.get("sources") or [] if s.get("answered")]
    cands = res.get("candidates") or []
    lines = ["Пошук: %d %s · джерела: %s · кандидатів %d" % (n, _variants_word(n), ", ".join(said) or "—", len(cands))]
    for i, c in enumerate(cands, 1):
        head = c["title"] or c["path"]
        shown = _shown(c["title"], c["heading"])
        parts = [head + (" › " + shown if shown else ""), ", ".join(c["source"]), c["type"] or "—",
                 (c["date"] or "")[:10] or "—"] + list(c["flags"])
        lines.append("%d. %s" % (i, " · ".join(parts)))
        if c["snippet"]:
            lines.append("   " + c["snippet"])
        lines.append("   id %s · варіанти %s" % (c["id"], ",".join(str(v) for v in c["matched"]) or "—"))
        for s in c.get("sections", [])[1:]:
            lines.append("   також: %s · id %s" % (_shown(c["title"], s["heading"]) or s["heading"] or "—", s["id"]))
    lines.extend(res.get("notes") or [])
    return "\n".join(lines) + "\n"
