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

Reads only — the vaults, the cores, the index under <home>/.grow-pm/index/, a local index (mode=ro), the glossary, the
block states of the store; the network only for an MCP source. Writes nothing. Stdlib only.
"""
import datetime
import json
import os
import sqlite3
import sys
import threading
import time
import unicodedata
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx_common as cc  # noqa: E402
import ctx_glossary as gl  # noqa: E402
import ctx_index as ci  # noqa: E402
import ctx_mcp as cm  # noqa: E402
import ctx_ops as co  # noqa: E402
import ctx_read as cr  # noqa: E402
import ctx_repos as crp  # noqa: E402
import ctx_stem as st  # noqa: E402

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
_CLASS_DIR = {"teams": "team_card_dir", "people": "people_dir"}     # any other class: `<class>_dir`
_FM_DATES = ("updated", "modified", "snapshot", "generated", "date", "created")


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
    """One section (the own index) or note (a local index, MCP) a list gave: `rank` its place in the list (1 first),
    `variant` the variant's number, `list` the list's key. Optional extras: type, product, status, hub and sensitive
    (None: the source did not say), text (an own hit's section), terms (how many of the expression's terms the hit
    holds; None when not known — an MCP hit, a glossary list), asked (how many terms the expression had), remote (an
    MCP hit's path on the server, for vault_get_note)."""
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
    return any(p == "" or rel == p or rel.startswith(p + "/") for p in prefixes)


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
                     "hub": bool(r.get("hub")), "sensitive": bool(r.get("sensitive")), "text": r.get("text") or "",
                     "terms": None, "asked": len(terms)}
            if terms:
                words = st.stem_text(" ".join([r.get("title") or "", r.get("heading") or "", r.get("text") or ""]
                                              + list(r.get("tags") or []) + list(r.get("aliases") or []))).split()
                extra["terms"] = _held(terms, words)
            hits.append(Hit(rel, r.get("heading") or "", src["id"], 0, section_id=r.get("id"), title=r.get("title"),
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
                date = (_text_or_none(r["date"]) if "date" in keys else None) or next(
                    (_text_or_none(str(fm[k])) for k in _FM_DATES if fm.get(k) not in (None, "")), None)
                h = Hit(rel, "", src["id"], 0, title=meta["title"], date=date,
                        snippet=_text_or_none(r["snip"]) if "snip" in keys else None, variant=i, list=key,
                        type=(meta["type"] or "").lower(), product=meta["product"] or "",
                        status=(meta["status"] or "").lower(), hub=True if _yes(fm.get("search_hub")) else None,
                        sensitive=_yes(fm.get("sensitive")) if "sensitive" in fm else None, terms=None,
                        asked=len(terms))
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
                            sensitive=None, terms=None, asked=asked, remote=N(r["path"])))
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
    from the type and the title, as the index decides it), `title`, `date` — plus `hits` (the Hits that found it) and
    `flags` (made when missing). `score` is multiplied by:
    - TYPE_W when its type is one of `skill_types` (any case);
    - SAME_PRODUCT_W for the product asked, OTHER_PRODUCT_W for another (no product asked or none on the note: 1);
    - HUB_W for a hub, marked `хаб`;
    - OUTDATED_W, marked `застаріле`, for a status of OUTDATED, or a date older than the TTL of the folder class it lies
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
        day = _day(c.get("date"))
        if str(c.get("status") or "").lower() in OUTDATED or (days is not None and day is not None
                                                                and (today - day).days > days):
            score *= OUTDATED_W
            _flag(c, STALE)
        snap = _longest(path, snaps)
        if snap:
            _flag(c, SNAPSHOT % snap)
        hits = c.get("hits") or []
        if hits and all(_glossary_key(h.get("list")) for h in hits):
            _flag(c, GLOSSARY_ONLY)
        known = [h for h in hits if not _glossary_key(h.get("list")) and isinstance(h.get("terms"), int)]
        if known and max(h["terms"] for h in known) == 1 and max(h.get("asked") or 0 for h in known) >= 2:
            _flag(c, ONE_WORD)
        c["score"] = score


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
