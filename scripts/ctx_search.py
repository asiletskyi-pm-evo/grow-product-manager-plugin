#!/usr/bin/env python3
"""Grow PM — `ctx search`: where a question goes, how the answers become one list, and what weighs them (v3.16.0).

A question and the variants the session's model wrote for it (Ukrainian, Russian, English, a synonym) go to every
source at once: the plugin's own section index (ctx_index), a local index the user registered (a user's own local
index — an SQLite file, read only) and the MCP server of a repository whose folder is not on disk. Each variant is a
list of its own in each source, and so is the glossary's widening of it (the other names of what the variant names,
ctx_glossary). Reciprocal-rank fusion makes one score of all the lists (k = 60, a glossary list at half weight); the
priors then weigh a candidate by what it is — the skill's artifact types × 1.2, the same product × 1.1 and another
× 0.7, a hub × 0.5, a note whose status says it is outdated × 0.5 — and mark what the reader should know (`станом на
<день>` for a note older than its class's TTL, `знімок від <день>`, `лише глосарій`, `одне слово`).

- context_for       the search context (`sctx`) of a local-context.md — the vaults, the repositories, the roots of the
                    index, the store and the blocks files as the index names them; `ctx index` builds its scope from it.
- class_ttl         folder prefix → `ttl_days` for the classes whose folder a core's provider manifest names.
- snapshots         folder prefix → day, for the repositories whose snapshot is older than `stale_after_days`.
- Source / sources  where a question goes: `own`, `local` (an index file), `mcp` (a server).
- Hit / gather      one section or note an answer gave; every variant × source, the sources in parallel.
- fuse              RRF over the lists.
- priors            the weights and the marks of the candidates.
- skill_types       a skill's artifact types: `search_types` of references/context-manifest.yaml.
- dedup             one candidate per note (the five keys of spec §6: the same path, Confluence page, content — a near
                    copy too —, a twin of your layer and the core, versions), at most two sections of a note.
- candidate_id      a section's stable id: sha1(`path#heading`)[:10].
- snippet           ≤ 300 characters around the first match, the matches in «».
- run               a whole search: the index refreshed, gather → fuse → priors → dedup → the remembered picks
                    (ctx_hints) → the best `limit`; an own index not built yet (or being built by another process)
                    has not answered.
- last_path / save_last / get   the ids of the last search beside the index, and `--get ID|PATH|NAME`: one section
                    with its line of provenance `> [<source> · <path> › <heading> · <day>]` — for a note of a local
                    index or a server, followed by what its frontmatter says (` · sensitive`, ` · застаріле`, its
                    type); a short section goes on with the next ones; a file iCloud has not downloaded is never read.
                    By a path or a name (as a hub links it: `Name`, `[[Name|alias]]`, `[[Name#Heading]]`, since
                    v3.16.1 `![[Name]]`, `[[Name#H1#H2]]`, `[[Name#^block]]`, a link with a folder — the plugin
                    folder's path first, else the end of a path) the whole note or the section after `#`; an
                    `@<repository>/…` name through the server. Any form gives 20 000
                    characters at most (60 000 with --full), then the LONG_NOTE line (long_note, since v3.16.1).
- render            the human output of `ctx search`.

Reads the vaults, the cores, the index under <home>/.grow-pm/index/, a local index (mode=ro), the glossary, the block
states and the search memory (`.state/search.json`) of the store; the network only for an MCP source. Writes only
<home>/.grow-pm/index/ — the index (run refreshes it) and last.json (save_last) — never the store or a vault. Stdlib
only.
"""
import datetime
import hashlib
import itertools
import json
import os
import posixpath
import re
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
LIST_LIMIT = 50                 # hits asked of a source for one list; also the pool `ctx search eval` reads
LIMIT = 30                      # candidates a search lists unless --limit says otherwise (Step 0.5 reads them)
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
AS_OF = "станом на %s"           # a note older than its class's ttl_days: its own day — cited with it, never devalued
REBUILT_NOTE = "індекс пошуку був зіпсований або старий — збудовано наново"
REFRESH_NOTE = "індекс пошуку не оновлено (%s) — пошук по тому, що є"
BUILDING_NOTE = "індекс пошуку ще будується (інший процес) — цього разу без нього"
NO_INDEX_NOTE = "індексу пошуку ще немає (%s) — ctx index rebuild"
NO_DB_WHY, UNFINISHED_WHY = "немає файлу індексу", "індекс не добудовано"    # the <why> of NO_INDEX_NOTE without an error
COMMAND_S = 60.0                # the whole search
SNIPPET_W = 300                 # a snippet's characters at most
MAX_SECTIONS = 2                # sections of one note in the list
LAST_NAME = "last.json"
LAST_KEEP = 1000                # ids last.json keeps — the newest; ids are stable, so the searches merge into it
LAST_NOTE = "ідентифікатори пошуку не збережено (%s) — --get знайде лише секції свого індексу"
FILL_CHARS = 1500               # --get: a short section goes on with the next ones up to this many characters
SHORT_NOTE = "секція коротка — додано наступні: %s"
ICLOUD_LOCAL = "файл не завантажено з iCloud — текст із локального індексу %s"
ICLOUD_MISSING = "файл не завантажено з iCloud: %s — відкрий його в Obsidian або ctx index rebuild --download"
ICLOUD_OPEN = "файл не завантажено з iCloud: %s — відкрий його в Obsidian"   # a path --download never brings down
GET_CHARS = 20000               # --get, any form (a section after `#` too): the characters of its text at most
FULL_CHARS = 60000              # --get --full (a note the model took as «прямо», search-protocol §4): at most
LONG_NOTE = "нотатка довга — показано %s знаків із %s; %s"
LONG_NEXT = "далі: %s — --get \"%s#<заголовок>\""
LONG_NONE = "заголовків далі немає"
LONG_FULL = "--full (до 60 000)"
LONG_NAMES, LONG_NAMES_CHARS = 20, 600      # the headings LONG_NOTE names at most, and their characters
LONG_GAIN = 2000                # the section the cut falls under is named only when --get of it shows this much more
EXCLUDED_NOTE = "шлях виключено з пошуку: %s"
SEVERAL_NOTE = "кілька нотаток із назвою «%s»: %s — --get один зі шляхів"
SEVERAL_TAIL = "кілька нотаток, чий шлях закінчується на «%s»: %s — --get один зі шляхів"
SEVERAL_MAX = 5                 # paths SEVERAL_NOTE names, then `· ще N`
NO_CANDIDATE = "no candidate %s in the last search or the section index — search again"
OUTSIDE_ROOT = ":"              # `@<repo>/:/<path>`: a server's note outside its endpoint.root (v3.16.2; no Obsidian
                                # name holds a `:`, so no folder of the core can be taken for it)
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
    """A word with every combining mark gone (NFD): «é» is «e», as FTS5's unicode61 remove_diacritics 2 has it — but
    also «й» is «и» and «ї» is «і», which that tokenizer does not fold (SQLite 3.54 keeps the Cyrillic letters whole).
    Only `snippet` uses it, on both sides of every comparison — the text and the terms — so it stays consistent with
    itself: a snippet may mark a word that differs from a term only by such a letter."""
    return "".join(c for c in unicodedata.normalize("NFD", word) if not unicodedata.combining(c))


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
        held = [st.fts_or([t]) for t in dict.fromkeys(terms) if t]      # what a hit holds, as the index matches it
        rows = idx.query(expr, LIST_LIMIT, held=held) if expr else []
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
                extra["terms"] = r.get("held", 0)
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
    `notes` (else from `notes_fts`) when a column has them, the rest from its frontmatter JSON when it keeps one; the
    file time from `notes.mtime` when there is one; the note's text from `notes_fts.body` when there is one."""
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
    for c in ("title", "type", "date", "status", "product", "mtime"):
        if join and c in notes:
            cols.append("notes.%s AS %s" % (c, c))
        elif c in fts:
            cols.append("notes_fts.%s AS %s" % (c, c))
    fm = next((c for c in ("fm_json", "frontmatter_json") if join and c in notes), None)
    if fm:
        cols.append("notes.%s AS fm" % fm)
    if "body" in fts:
        cols.append("snippet(notes_fts, %d, '«', '»', '…', 24) AS snip" % fts.index("body"))
        cols.append("notes_fts.body AS body")
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


def _file_day(v):
    """The day of a local index's file time — seconds since the epoch (a number, or a text of one) or an ISO text — as
    YYYY-MM-DD; None when it names none."""
    if isinstance(v, str) and _day(v):
        return _day(v).isoformat()
    try:
        return datetime.date.fromtimestamp(float(v)).isoformat() if v not in (None, "") else None
    except (TypeError, ValueError, OverflowError, OSError):
        return None


def _local_name(p, vaults, folder, root):
    """The index name of a path a local index keeps: an absolute one through the vaults (ctx_index.rel_path — the
    index's own `root` for a file outside them), a relative one from the index's `folder`, else as it is."""
    p = N(p).strip().replace("\\", "/")
    if os.path.isabs(p):
        return ci.rel_path(p, vaults, root)
    if folder:
        return ci.rel_path(os.path.join(folder, p), vaults, root)
    return p.lstrip("/")


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
        lists, near = {}, {}

        def near_of(r):
            """The near key of a note's text (ctx_index.near_key of its sections), once per note."""
            if r["rid"] not in near:
                body = r["body"] if "body" in r.keys() else None
                text = isinstance(body, str) and body.strip()
                near[r["rid"]] = ci.near_key(ci.split_sections(body)) if text else None
            return near[r["rid"]]

        def name(p):
            return _local_name(p, vaults, folder, root)

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
                date = ((_text_or_none(r["date"]) if "date" in keys else None) or _first_date(fm, _FM_DATES)
                        or (_file_day(r["mtime"]) if "mtime" in keys else None))
                snip = _text_or_none(r["snip"]) if "snip" in keys else None
                body = r["body"] if "body" in keys else None
                h = Hit(rel, "", src["id"], 0, title=meta["title"], date=date, snippet=snip, variant=i, list=key,
                        type=(meta["type"] or "").lower(), product=meta["product"] or "",
                        status=(meta["status"] or "").lower(), hub=True if _yes(fm.get("search_hub")) else None,
                        sensitive=True if ci.sensitive_of(fm) or (meta["type"] or "").lower() in ci.PEOPLE_TYPES
                        else (_yes(fm.get("sensitive")) if "sensitive" in fm else None),
                        ttl_date=_first_date(fm, ci.TTL_DATE_KEYS) or "", terms=None, asked=len(terms), near=near_of(r))
                if snip and isinstance(body, str) and _lost(snip):    # the match was in a breadcrumb or a link line
                    h["preview"] = _preview(ci.split_sections(body))
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
    name of the file, `@<repo>/<path>` without one; outside `endpoint.root`, `@<repo>/:/<path as given>` (since v3.16.2:
    a name of its own, never the one of a note under the root)."""
    p = N(path).strip().replace("\\", "/").lstrip("/")
    root = N(repo["endpoint"].get("root") or "").replace("\\", "/").strip("/")
    if not root:
        return _repo_name(repo, p, sctx.get("vaults") or [])
    if p == root or p.startswith(root + "/"):
        return _repo_name(repo, p[len(root):], sctx.get("vaults") or [])
    return "@%s/%s/%s" % (repo["id"], OUTSIDE_ROOT, p)


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
            rtype = (_text_or_none(r.get("type")) or "").lower()
            hits.append(Hit(rel, "", src["id"], 0, title=_text_or_none(r.get("title")), date=date,
                            snippet=_text_or_none(r.get("snippet")), variant=i, list=key,
                            type=rtype, product="", status="", hub=None,
                            sensitive=True if rtype in ci.PEOPLE_TYPES else None,   # a people type (v3.17.0)
                            ttl_date=_first_date(r, ci.TTL_DATE_KEYS) or "", terms=None, asked=asked,
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
    - OUTDATED_W, marked `застаріле`, for a status of OUTDATED — and only for that.
    Marks that leave the score as it is: `станом на <день>` for a `ttl_date` (the note's own `updated` | `snapshot` |
    `generated`; a note with none of them is never marked by age) older than the TTL of the folder class it lies in
    (`ttl`: class_ttl's {prefix: days}) — the day is that date: such a note may be taken, and is cited with it;
    `знімок від <день>` for a note under a repository of `snaps` (snapshots' {prefix: day}); `лише глосарій` when every
    hit came from a glossary list; `одне слово` when the variants' hits held one term at best of an expression of two
    or more (hits whose `terms` is not known do not count). A mark is never added twice."""
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
        if str(c.get("status") or "").lower() in OUTDATED:
            score *= OUTDATED_W
            _flag(c, STALE)
        if days is not None and day is not None and (today - day).days > days:
            _flag(c, AS_OF % day.isoformat())
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
    an own section's id and text, an MCP hit's server path (`remote`), the first snippet a source gave, the near key a
    local index's text gave (`near`)."""
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
             "section_id": own["section_id"] if own else None,
             "text": own.get("text") if own else next((h["preview"] for h in hits if h.get("preview")), None),
             "own_source": own["source"] if own else None,
             "hub": own.get("hub") if own else next((h["hub"] for h in hits if h.get("hub") is not None), None),
             "sensitive": any(h.get("sensitive") is True for h in hits),
             "remote": next((h["remote"] for h in hits if h.get("remote")), None),
             "snippet": next((h["snippet"] for h in hits if h.get("snippet")), None),
             "near": next((h["near"] for h in hits if h.get("near")), None)}
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
             snippet=c.get("snippet") or next((e["snippet"] for e in entries if e.get("snippet")), None),
             near=next((e["near"] for e in entries if e.get("near")), None))
    return c


def _title_key(title):
    return " ".join(N(str(title or "")).split()).casefold()


SAME_TEXT = ("hash", "near")     # the folds of the same text: a «не те» of one copy is of the other (ctx_hints)


def _chain(outer, inner):
    """The kind of a twin folded twice (into a candidate, then that one into another): the same text only when both
    folds were (SAME_TEXT), else the one that was not."""
    if outer in SAME_TEXT and inner in SAME_TEXT:
        return outer
    return outer if outer not in SAME_TEXT else inner


def dedup(cands, notes_meta, own=None):
    """The candidates without duplicates, best first — the keys of the spec (§6) in turn:
    1. the same path (NFC) — one candidate (`_merge`);
    2. the same `confluence_id` in two files of the index — the newer by its date stays, marked `двійник <path>` of
       the other;
    3. the same `hash` — the better one stays, marked `двійник <path>`;
    3a. the same text but for what near copies differ by (ctx_index.near_key: frontmatter, back-link and update-date
       lines, the trailing «Повʼязане» block; 400 characters of text at least) — the copy of your layer stays (its path
       under one of `own`, the index names of the plugin folders — whichever source found it; or a source `own`), and
       of those the older by its day (the first ten characters of its date): the original, as a copy is made later
       (one with no date never wins over a dated one; the same day — the better score); marked `двійник <path>`; the
       key is the index's for its files, a local index's text for a note only it knows;
    4. the same title (normalised) when the `links` of one hold the file name of the other (a hub of your layer and
       the core page) — a note that is not a hub stays over a hub, then the one with more text (`size`, when every
       one's is known: a server's note has none, and is not the smaller for it), then the better score; marked
       `двійник <path>`;
    5. the same `version_key` — the newer by its date stays, marked `є старіші версії: N` (the older ones the index
       holds); a version that is not the newest the index holds is marked `старіша версія <path of the newest>`.
    A candidate that stays keeps the best score of those it stands for, their `sensitive`, and their paths (`twins`,
    since v3.16.2: a remembered pick of one of them weighs it, `ctx search eval` finds them there) with the kind of
    fold that brought each (`twin_keys`, internal: page, hash, near, link, version). `cands` are entries (one per path and heading,
    weighed by the priors: path, heading, score, flags, hits, section_id, title, …); `notes_meta` Index.notes() — the
    keys 2–5 read hash, near, size, links, version_key, confluence_id and date there, so they hold for files of the
    index (key 3a also for a note only a local index knows, by the `near` its hits carry).
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

    def fold(keep, others, mark=None, key=""):
        for o in others:
            if o is not keep and id(o) not in gone:
                gone.add(id(o))
                keep["score"] = max(keep["score"], o["score"])
                twins = keep.setdefault("twins", [])           # what it stands for: a pick of one weighs it (v3.16.2)
                keys = keep.setdefault("twin_keys", {})         # by which fold — a «не те» crosses only the same text
                inner = o.get("twin_keys") or {}
                for t, k in [(o["path"], key)] + [(t, _chain(key, inner.get(t, key))) for t in o.get("twins") or []]:
                    if t != keep["path"] and t not in twins:
                        twins.append(t)
                        keys[t] = k
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
        fold(max(g, key=lambda c: (when(c), c["score"])), g, TWIN, "page")
    for g in grouped(lambda c: meta(c).get("hash")):
        fold(g[0], g, TWIN, "hash")
    def yours(c):
        return "own" in (c.get("source") or []) or (own is not None and _in_scope(c["path"], own))

    def hubbed(c):
        return bool(meta(c).get("hub") or c.get("hub") or HUB in (c.get("flags") or []))

    for g in grouped(lambda c: meta(c).get("near") or c.get("near")):    # yours first, then the original: the older day
        fold(min(g, key=lambda c: (not yours(c), not when(c), when(c)[:10], -c["score"])), g, TWIN, "near")
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
                known = all(meta(c).get("size") is not None for c in part)       # a server's note has no size
                fold(max(part, key=lambda c: (not hubbed(c), meta(c).get("size") if known else 0, c["score"])), part, TWIN,
                     "link")
    for g in grouped(lambda c: meta(c).get("version_key")):
        fold(max(g, key=lambda c: (when(c), c["score"])), g, None, "version")
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
    or more (both sides folded by `_fold`)?"""
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


def _clean(text):
    """A snippet a source gave without its breadcrumb and link-only lines (ctx_index.link_only; a line's `…` aside)."""
    lines = (text or "").split("\n")
    return "\n".join(line for line in lines if not ci.link_only(line.strip().strip("…").strip())).strip("\n")


def _lost(snip):
    """Does a local index's snippet hold nothing once its link-only lines go (`_clean`) — its match marks «…» gone with
    them (the match lived in a breadcrumb or a link line), or no text left at all? Then the note's opening stands in
    for it (`_preview`); any other window is kept, without its link-only lines."""
    left = _clean(snip)
    return ("«" in snip and "«" not in left) or not left.strip().strip("…").strip()


def _preview(sections):
    """The text a candidate's snippet is taken from, given its best section and the ones after it ([(heading, text)]):
    their text without link-only lines — the best section's alone when that holds ctx_index.STUB_CHARS characters or
    more, else it and the next ones until FILL_CHARS (the fill of `--get`). A breadcrumb is never the snippet."""
    out, size = [], 0
    for i, (_, text) in enumerate(sections or []):
        if i and (size >= FILL_CHARS or (i == 1 and size >= ci.STUB_CHARS)):
            break
        part = ci.strip_links(text).strip("\n")
        out.append(part)
        size += len(part.strip())
    return "\n".join(p for p in out if p.strip())


def _following(idx, c):
    """The sections after an own candidate's section, from the index — only when its text is short (`_preview`)."""
    if len(ci.strip_links(c.get("text") or "").strip()) >= ci.STUB_CHARS:
        return []
    sec = idx.section(c["section_id"])
    return idx.following(sec["note_id"], sec["ord"], chars=FILL_CHARS) if sec else []


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
        snip = _cut(" ".join(N(_clean(c.get("snippet") or "")).split()), SNIPPET_W)
    return {"id": candidate_id(path, c["heading"]), "path": path, "heading": c["heading"], "title": c.get("title") or "",
            "type": c.get("type") or "", "product": c.get("product") or "", "date": c.get("date") or "",
            "source": list(c["source"]), "flags": list(c["flags"]),
            "matched": sorted({h.get("variant", 0) + 1 for h in c.get("hits") or []}), "snippet": snip,
            "score": round(c["score"], 6),
            "sections": [{"id": candidate_id(path, s["heading"]), "heading": s["heading"]} for s in c["sections"]],
            **({"twins": list(c["twins"])} if c.get("twins") else {})}


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
    """Index.refresh within `budget`: (what it did, None), or (None, why) when SQLite or the file system could not do
    it — the caller says why in one line (REFRESH_NOTE, or NO_INDEX_NOTE when there is no index to read). A refresh
    that rebuilt the index adds REBUILT_NOTE."""
    try:
        res = idx.refresh(sctx["roots"], sctx["store_rel"], sctx["blocks_rels"], budget=budget)
    except (sqlite3.Error, OSError) as e:
        return None, str(e) or e.__class__.__name__
    if res.get("rebuilt"):
        _note(notes, [REBUILT_NOTE])
    return res, None


def _saved_state(idx):
    """The own index's state as index.json keeps it, in the shape of Index.status() (a count it does not keep is 0) —
    for an index another process holds busy, which is not waited for a second time."""
    state = idx._state()
    return dict({k: state.get(k) for k in ("schema", "updated")},
                **{k: ci._count(state.get(k)) for k in STATUS_KEYS if k not in ("schema", "updated")})


def run(sctx, queries, skill=None, product=None, limit=LIMIT, which=KINDS, use_hints=True, now=None, refresh=True):
    """One search: {candidates, notes, sources, index, last}.
    - The own index is refreshed first (ctx_index.REFRESH_S, never past the command's COMMAND_S; with `refresh` False
      it is read as it is — `ctx search eval` refreshes it once, not at every search); then every query × source
      (`gather`, the sources of `which`), RRF (`fuse`), the priors (`skill`'s types, `product`, the classes' TTL and
      the repositories' snapshots), `dedup`, the best `limit` (LIMIT, 30; `ctx search eval` asks LIST_LIMIT, 50).
    - An own index that is not there to read — no database, or one a first build (or a rebuild) is still filling: no
      `updated` row in its meta (Index.built) — has not answered and is not asked: `індекс пошуку ще будується (інший
      процес) — цього разу без нього` while another process holds its lock (`index.locked`), else `індексу пошуку ще
      немає (<why>) — ctx index rebuild`, <why> the refresh's error when it failed.
    - The remembered picks (ctx_hints) of the request — the first query, not its variants — weigh the candidates
      after dedup and before the best `limit` are cut, so a pick can rise into them: a `good` note × 1.5 and
      `твій вибір від <день>`, a `bad` one `ти казав «не те»`; with `use_hints` False they are not read. A memory that
      cannot be read in OPEN_S is no hint and one line, `пам'ять пошуку не прочитано (<why>) — без підказок`.
    - A query that finds the own index damaged (Index.problem: a file SQLite cannot read, never a busy one) rebuilds
      it once and asks the own index again; REBUILT_NOTE says so. A rebuild another process's lock refuses is no
      rebuild: the building line, and the index is not asked again. An own index that stays unread — busy (BUSY_NOTE;
      never rebuilt) or still damaged — has not answered: its lists are dropped, and its line stays.
    - candidates: {id, path, heading, title, type, product, date, source [ids], flags, matched [the queries that
      found it, from 1], snippet, score, sections [{id, heading}: the candidate's own first, at most MAX_SECTIONS]};
      a source of the own index is the root's (`own` for a plugin folder, the repository's id for a core folder).
    - notes: the lines to print under the list; sources: [{id, kind, answered}] (none answered: the caller exits 5;
      none at all: there is no place to search); index: the own index's state and what the refresh did, `locked` when
      another process held it (None when `own` is not among the sources); last: what save_last keeps for `--get`.
    Writes only the index; nothing else."""
    start = time.monotonic()
    deadline = start + COMMAND_S
    queries = [q for q in queries or [] if isinstance(q, str)]
    if product:
        sctx = dict(sctx, product=product)
    srcs = sources(sctx["text"], sctx["repos"], tuple(which or KINDS))
    notes, index, done, why, unbuilt, locked = [], None, None, None, None, False
    idx = ci.Index(sctx["home"])
    own = [s for s in srcs if s["kind"] == "own"]
    asked = srcs
    if own:
        if refresh:
            done, why = _refresh(idx, sctx, max(0.0, min(ci.REFRESH_S, deadline - time.monotonic())), notes)
        locked = bool((done or {}).get("locked"))
        if idx.built() is False:            # no database, or one still being filled: there is no base to read yet
            locked = locked or idx.lock_held()
            unbuilt = BUILDING_NOTE if locked else NO_INDEX_NOTE % (
                why or (UNFINISHED_WHY if os.path.isfile(idx.db_path) else NO_DB_WHY))
            _note(notes, [unbuilt])
            asked = [s for s in srcs if s["kind"] != "own"]
        elif why:
            _note(notes, [REFRESH_NOTE % why])
    lists, more = gather(sctx, queries, asked, deadline) if asked else ({}, [])
    if own and any(n.startswith(_BROKEN) for n in more):
        again, more2, redo = None, [], {}
        try:
            redo = idx.rebuild(sctx["roots"], sctx["store_rel"], sctx["blocks_rels"],
                               budget=max(0.0, min(ci.REFRESH_S, deadline - time.monotonic())))
            if not redo.get("locked"):
                again, more2 = gather(sctx, queries, own, deadline)
        except (sqlite3.Error, OSError):
            pass
        if redo.get("locked"):              # another process holds the index: no rebuild, and it is not asked again
            locked = True
            more = more + [BUILDING_NOTE]
        elif again is not None and not any(n.startswith(_BROKEN) for n in more2):
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
    metas = idx.notes() if os.path.isfile(idx.db_path) and not busy and not unbuilt else []
    mine = [ci.rel_path(r["path"], sctx.get("vaults") or [], r) for r in sctx.get("roots") or []
            if r.get("source") == "own"]
    cands = dedup(entries, metas, own=mine)
    if hints:
        ch.apply(cands, hints, _today(now))
        cands.sort(key=_order)
    cands = cands[:max(1, int(limit))]
    for c in cands:
        if c.get("section_id") is not None and c.get("text") is not None:
            c["text"] = _preview([(c.get("heading") or "", c["text"])] + _following(idx, c))
    terms = list(dict.fromkeys(t for q in queries for t in st.query_terms(q)))
    last = {}
    for c in cands:
        last.update(_last(c))
    if own:
        state = idx.status() if not busy else _saved_state(idx)       # busy: no second wait
        index = dict(state, **{k: (done or {}).get(k, 0) for k in ("added", "changed", "removed")},
                     locked=locked, rebuilt=bool((done or {}).get("rebuilt")) or REBUILT_NOTE in notes)
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


def _file_of(sctx, path):
    """The file of an index name — a vault's file, or `@<repository>/…` under its core folder — when it is a `.md` file
    on disk inside a vault or a core folder; else None. Only stat calls: a file iCloud has not downloaded is not
    opened."""
    folders = list(sctx.get("vaults") or []) + [_folder(r) for r in sctx.get("repos") or []]
    if path.startswith("@"):
        rid, _, rest = path[1:].partition("/")
        repo = next((r for r in sctx.get("repos") or [] if r.get("id") == rid), None)
        files = [os.path.join(_folder(repo), *rest.split("/"))] if repo and _folder(repo) and rest else []
    else:
        files = [os.path.join(v, *path.split("/")) for v in sctx.get("vaults") or []]
    return next((f for f in files if f.lower().endswith(".md") and _inside(f, folders) and os.path.isfile(f)), None)


def _icloud_missing(sctx, path):
    """The line of a file iCloud has not downloaded that no local index holds: ICLOUD_MISSING (Obsidian or `ctx index
    rebuild --download`) for a note of a plugin folder — the one --download brings down —, else ICLOUD_OPEN."""
    return (ICLOUD_MISSING if _root_source(sctx, path) == "own" else ICLOUD_OPEN) % path


def _from_disk(sctx, entry):
    """(text, date, meta, said) of a note on disk, by its index name: a vault's file, or `@<repository>/…` under its
    core folder; meta is what its frontmatter says (`_marks`), said a line to print above the text (None). Only a `.md`
    file inside a vault or a core folder is read, and only through the time-budgeted reader (ctx_store.read_text): a
    file that does not arrive in time is one line, GetError 3, never a hang. A file iCloud has not downloaded
    (ctx_index.is_dataless) is never read — that would start its download: its text comes from a registered local index
    that holds it, said so (`файл не завантажено з iCloud — текст із локального індексу <id>`), else GetError 3
    (`_icloud_missing`: `файл не завантажено з iCloud: <шлях> — відкрий його в Obsidian`, and ` або ctx index rebuild
    --download` for a note of a plugin folder)."""
    path = entry["path"]
    found = _file_of(sctx, path)
    if not found:
        raise GetError(3, "the note is not on disk: %s" % path)
    if ci.is_dataless(found):
        local = _local_body(sctx, path, found)
        if local is None:
            raise GetError(3, _icloud_missing(sctx, path))
        meta = _local_meta(path, local)
        return local[1], meta.get("date") or "", meta, ICLOUD_LOCAL % local[0]
    try:
        text = cst.read_text(found)
    except (OSError, UnicodeError, cst.StoreError) as e:
        raise GetError(3, "the note cannot be read: %s (%s)" % (path, e))
    meta = ci.note_meta(path, text)
    return text, meta.get("date") or "", meta, None


def _from_local(sctx, entry):
    """(text, date, meta, said, source) of a candidate a local index named: its file (`_from_disk`) when it is on disk;
    else, since v3.16.2, the server of a registered core whose folder is not on disk (`_mcp_entry` of a vault name
    under it; `source` is that repository — never a local index's old copy of it); else, for a local index's own
    `@<id>/…` name (an index outside every vault), that index's text (the file itself is never opened); else
    GetError 3 — a vault file deleted since the search is not served from a local index's copy. `source` is None but
    for the server."""
    path = entry["path"]
    if _file_of(sctx, path):
        return _from_disk(sctx, entry) + (None,)
    alt = _mcp_entry(sctx, path)
    if alt:
        return _from_mcp(sctx, alt) + (alt["source"],)
    lid = path[1:].partition("/")[0] if path.startswith("@") else ""
    if lid and any(src["id"] == lid for src in sources(sctx["text"], sctx["repos"], ("local",))):
        local = _local_body(sctx, path, os.path.join((sctx.get("vaults") or [""])[0], *path.split("/")))
        if local:
            meta = _local_meta(path, local)
            return local[1], meta.get("date") or "", meta, None, None
    raise GetError(3, "the note is not on disk: %s" % path)


def _local_names(path, found, vaults, folder, src_id=""):
    """The spellings a local index may keep the note under: its file's absolute path; the index name and the path from
    each vault that holds it — only for an index with no root or one rooted at a vault (since v3.16.2: an index rooted
    in a subfolder keeps paths from that folder, and its `kiwi.md` is not the vault's); the path from the index's own
    root; for its own `@<src_id>/<rest>` name (an index outside every vault), `<rest>` — NFC and NFD."""
    real = os.path.realpath(found)
    names = {found, real}
    tops = [os.path.realpath(v) for v in vaults or []]
    own = os.path.realpath(folder) if folder else ""
    if not own or own in tops:
        names.add(path)
        for top in tops:
            if real.startswith(top.rstrip(os.sep) + os.sep):
                names.add(os.path.relpath(real, top).replace(os.sep, "/"))
    if own and real.startswith(own.rstrip(os.sep) + os.sep):
        names.add(os.path.relpath(real, own).replace(os.sep, "/"))
    if src_id and path.startswith("@%s/" % src_id):
        rest = path[len(src_id) + 2:]
        names.update({rest, os.path.join(folder, *rest.split("/"))} if folder else {rest})
    return sorted({f(n) for n in names for f in (N, lambda x: unicodedata.normalize("NFD", x))})


def _local_body(sctx, path, found):
    """(id, text, row) of a note in the first registered local index whose `body` holds it (either shape of
    `_local_sql`), opened read only as a search opens it (OPEN_S to open, SOURCE_S for the query); None when none does.
    `row` is what the index's `notes` says of it, {"type", "fm"} (since v3.17.0: §10 keeps the frontmatter apart from
    the body). `path` is the note's index name, `found` its file."""
    for src in sources(sctx["text"], sctx["repos"], ("local",)):
        try:
            con = sqlite3.connect("file:%s?mode=ro" % urllib.parse.quote(src["path"]), uri=True, timeout=OPEN_S)
        except sqlite3.Error:
            continue
        until = time.monotonic() + SOURCE_S
        con.set_progress_handler(lambda: time.monotonic() > until, 10000)
        try:
            fts, notes = _columns(con, "notes_fts"), _columns(con, "notes")
            names = _local_names(path, found, sctx.get("vaults"), _local_root(con), src["id"])
            marks = ",".join("?" * len(names))
            fmc = next((c for c in ("fm_json", "frontmatter_json") if c in notes), None)
            cols = [c for c in ("type", fmc) if c and c in notes] if "path" in notes else []
            more = "".join(", notes.%s" % c for c in cols)
            if "body" not in fts:
                row = None
            elif "path" in fts:
                row = con.execute("SELECT notes_fts.body%s FROM notes_fts %sWHERE notes_fts.path IN (%s)"
                                  % (more, "LEFT JOIN notes ON notes.path = notes_fts.path " if cols else "", marks),
                                  names).fetchone()
            elif "id" in notes and "path" in notes:
                row = con.execute("SELECT notes_fts.body%s FROM notes_fts JOIN notes ON notes.id = notes_fts.rowid "
                                  "WHERE notes.path IN (%s)" % (more, marks), names).fetchone()
            else:
                row = None
        except sqlite3.Error:
            row = None
        finally:
            con.close()
        if row and isinstance(row[0], str) and row[0].strip():
            got = dict(zip(cols, row[1:]))
            return src["id"], row[0], {"type": got.get("type"), "fm": _fm(got.get(fmc)) if fmc else {}}
    return None


def _local_meta(path, local, mtime=None):
    """note_meta of a local index's text of a note, with what the index's row says that the text may not (§10 keeps
    the frontmatter apart from the body): its type, its date, and whether it is sensitive (since v3.17.0)."""
    meta = ci.note_meta(path, local[1], mtime=mtime)
    row = local[2] if len(local) > 2 else {}
    fm = row.get("fm") or {}
    rtype = (_text_or_none(row.get("type")) or ci._text(fm.get("type")) or "").lower()
    meta["type"] = meta["type"] or rtype
    meta["sensitive"] = bool(meta["sensitive"] or ci.sensitive_of(fm) or rtype in ci.PEOPLE_TYPES)
    meta["date"] = _first_date(fm, ci.DATE_KEYS) or meta["date"]
    return meta


def _after(body, heading):
    """The sections of a note's text (ctx_index.split_sections) after the one named `heading`; [] for the whole note
    ("") or a heading it does not have."""
    if not heading:
        return []
    secs = ci.split_sections(body)
    i = next((i for i, (h, _) in enumerate(secs) if h == heading), None)
    return [] if i is None else secs[i + 1:]


def _fill(text, following):
    """A section shorter than ctx_index.STUB_CHARS without its breadcrumb lines (ctx_index.link_only) — an image, a
    breadcrumb, one line — goes on with the sections after it (`following`, [(heading, text)]) until the text holds
    FILL_CHARS characters or the note ends: one line `секція коротка — додано наступні: <headings>`, then each section
    under its heading (as many `#` as its heading path has parts). Anything else is given as it is."""
    size = len(ci.strip_links(text).strip())
    if size >= ci.STUB_CHARS:
        return text
    got = []
    for heading, body in following or []:
        if size >= FILL_CHARS:
            break
        got.append((heading, body))
        size += len(ci.strip_links(body).strip())
    if not got:
        return text
    parts = [text.strip("\n"), SHORT_NOTE % " · ".join(h for h, _ in got)]
    parts += [_as_markdown(h, body) for h, body in got]
    return "\n\n".join(p for p in parts if p)


def _as_markdown(heading, body):
    """A section as Markdown again: its heading (as many `#` as its heading path has parts, the last part), its text."""
    names = heading.split(" › ")
    head = "%s %s" % ("#" * min(len(names), 6), names[-1]) if heading else ""
    return "\n\n".join(p for p in (head, body.strip("\n")) if p)


def _is_id(arg):
    """Is a `--get` argument a candidate's id (ten hex digits, `candidate_id`) rather than a note's path or name?"""
    return len(arg) == 10 and all(c in "0123456789abcdefABCDEF" for c in arg)


def _parse(arg):
    """(target, heading) of a `--get` argument that is no id — a path or a name, bare, as a wiki-link or as an embed:
    `![[…]]` and `[[…]]` off, `|alias` dropped, the heading after the `#` that follows the name or the `.md`
    (`[[Name#Heading]]`, `<path>#<heading>` — all of it, `#H1#H2` and `#^block` too, for `_heading_for`; a target that
    ends in `.md` carries no heading, so `Growth/C# notes.md` is a path); NFC, `/`, the `.` and `..` segments of a path
    resolved (posixpath.normpath), no leading `./` or `../` (a link relative to the note that holds it: `_by_tail`
    finds it)."""
    s = N(arg).strip()
    s = s[1:] if s.startswith("![[") and s.endswith("]]") else s
    s = s[2:-2] if s.startswith("[[") and s.endswith("]]") else s
    s = s.split("|", 1)[0].strip()
    md = re.search(r"\.md#", s, re.I)          # on `s` itself: a lowered copy can be longer (`İ`)
    if s.lower().endswith(".md"):
        target, heading = s, ""
    elif md:
        target, heading = s[:md.start() + 3], s[md.end():]
    else:
        target, _, heading = s.partition("#")
    target = target.strip().replace("\\", "/")
    target = posixpath.normpath(target) if "/" in target else target
    while target.startswith("../"):
        target = target[3:]
    return target[2:] if target.startswith("./") else target, heading.strip()


def _root_source(sctx, path):
    """The source of the root of the index that holds `path` (the longest): `own` or a repository id — for an
    `@<repository>/…` name the repository, when it is registered; None outside."""
    if path.startswith("@"):
        rid = path[1:].partition("/")[0]
        return rid if any(r.get("id") == rid for r in sctx.get("repos") or []) else None
    best = None
    for r in sctx.get("roots") or []:
        prefix = ci.rel_path(r["path"], sctx.get("vaults") or [], r)
        if _in_scope(path, [prefix]) and (best is None or len(prefix) > len(best[0])):
            best = (prefix, r["source"])
    return best[1] if best else None


def _local_paths(sctx, match):
    """The index names of the notes of every registered local index that `match(name)` takes (a file name's key, the
    end of a path), each index opened read only as a search opens it (OPEN_S to open, SOURCE_S for the query); one that
    cannot be read or has another shape gives none."""
    out = []
    for src in sources(sctx["text"], sctx["repos"], ("local",)):
        try:
            con = sqlite3.connect("file:%s?mode=ro" % urllib.parse.quote(src["path"]), uri=True, timeout=OPEN_S)
        except sqlite3.Error:
            continue
        until = time.monotonic() + SOURCE_S
        con.set_progress_handler(lambda: time.monotonic() > until, 10000)
        try:
            fts, notes = _columns(con, "notes_fts"), _columns(con, "notes")
            table = "notes_fts" if "path" in fts else "notes" if "path" in notes else None
            rows = con.execute("SELECT path FROM %s" % table).fetchall() if table else []
            folder = _local_root(con)
        except sqlite3.Error:
            rows, folder = [], ""
        finally:
            con.close()
        root = ci.Root(src["id"], folder) if folder else None
        for (p,) in rows:
            rel = _local_name(p, sctx.get("vaults") or [], folder, root) if _usable(p) else ""
            if _usable(rel) and match(rel) and rel not in out:
                out.append(rel)
    return out


def _by_name(sctx, name):
    """The path of the note named `name` — its name key (ctx_index.name_key: no folder, no `.md`, NFC, case folded)
    among the own index's notes, else among those of every registered local index (`_local_paths`, by the file's
    name); a note the search excludes (`_keep`) does not count. Exactly one, or the one whose path is the name itself
    (`<name>.md` at a vault's root); else several → GetError 3 naming at most SEVERAL_MAX of them and `ще N` for the
    rest; none → GetError 3 (NO_CANDIDATE, or EXCLUDED_NOTE when only an excluded note has the name)."""
    key = ci.name_key(name)
    found = [p for p in ci.Index(sctx["home"]).paths() if ci.name_key(p) == key] if key else []
    if key and not found:
        found = _local_paths(sctx, lambda rel: ci.name_key(rel) == key)
    return _pick(sctx, name, found)


def _by_tail(sctx, path):
    """The path of the note a link with a folder in it means (`[[Concepts/Name]]`, as Obsidian writes one when a name
    is not unique; `../` is dropped by `_parse`), NFC, case folded: the notes whose index name ends in `/<path>` —
    the own index's and every registered local index's together, so that a note one of them misses (iCloud evicted
    it) is never swapped silently for another —, then the one that is `<plugin folder>/<path>` (the link as it reads
    from the plugin folder), else a file of the plugin folder on disk by that name (stat only: one no index holds),
    else as `_by_name` picks (`_pick`, SEVERAL_TAIL for several)."""
    tail = "/" + N(path).casefold()
    hit = lambda rel: ("/" + N(rel).casefold()).endswith(tail)  # noqa: E731
    found = sorted({N(p) for p in ci.Index(sctx["home"]).paths() if hit(p)} | {N(p) for p in _local_paths(sctx, hit)})
    vaults = sctx.get("vaults") or []
    for r in sctx.get("roots") or []:
        if r.get("source") != "own":
            continue
        pre = ci.rel_path(r["path"], vaults, r)
        meant = pre + "/" + N(path) if pre else N(path)
        same = [p for p in found if p.casefold() == meant.casefold() and _keep(sctx, p)]
        if same:
            return same[0]
        if os.path.isfile(os.path.join(r["path"], *N(path).split("/"))) and _keep(sctx, meant):
            return meant
    return _pick(sctx, path[:-3] if path.lower().endswith(".md") else path, found, missing=path, several=SEVERAL_TAIL)


def _pick(sctx, name, found, missing=None, several=None):
    """The one path of `found` a `--get` of `name` means: a note the search excludes (`_keep`) does not count; exactly
    one, or the one whose path is the name itself (`<name>.md` at a vault's root); else several → GetError 3 naming at
    most SEVERAL_MAX and `ще N`; none → GetError 3 (NO_CANDIDATE of `missing` — the name when None —, or EXCLUDED_NOTE
    when only excluded ones match)."""
    kept = sorted({N(p) for p in found if _keep(sctx, p)})
    if not kept:
        raise GetError(3, EXCLUDED_NOTE % sorted(found)[0] if found else NO_CANDIDATE % (missing or name))
    if N(name) + ".md" in kept:
        return N(name) + ".md"
    if len(kept) > 1:
        shown = kept[:SEVERAL_MAX] + (["ще %d" % (len(kept) - SEVERAL_MAX)] if len(kept) > SEVERAL_MAX else [])
        raise GetError(3, (several or SEVERAL_NOTE) % (name, " · ".join(shown)))
    return kept[0]


def _mcp_entry(sctx, path):
    """A last.json-like entry for `_from_mcp` of a name a search asks over MCP — the inverse of `_remote_name`: an
    `@<repository>/<rest>` name of a repository with an endpoint and no core folder on disk, its server path
    `endpoint.root/<rest>` (never asked again elsewhere: that could be another note); `@<repository>/:/<path>` of a
    repository whose endpoint has a root, the path as the server gave it (outside its root); since v3.16.2 also a vault's
    name under the core folder of such a repository whose folder is not on disk (it moved, or did not sync yet) —
    `endpoint.root/<the rest under the core>`. None for any other name."""
    repos = sctx.get("repos") or []
    if not path.startswith("@"):
        vaults = sctx.get("vaults") or []
        for repo in repos:
            ep, folder = repo.get("endpoint") or {}, _folder(repo)
            if not ep.get("url") or not folder or os.path.isdir(folder):
                continue
            prefix = ci.rel_path(folder, vaults)
            if prefix and not prefix.startswith("/") and path.startswith(prefix.rstrip("/") + "/"):
                rest = path[len(prefix.rstrip("/")) + 1:]
                root = N(ep.get("root") or "").replace("\\", "/").strip("/")
                return {"source": repo["id"], "path": path, "remote": root + "/" + rest if root else rest}
        return None
    rid, _, rest = path[1:].partition("/")
    repo = next((r for r in repos if r.get("id") == rid), None)
    ep, folder = (repo or {}).get("endpoint") or {}, _folder(repo) if repo else ""
    root = N(ep.get("root") or "").replace("\\", "/").strip("/")
    if rest.startswith(OUTSIDE_ROOT + "/") and ep.get("url") and root:
        return {"source": rid, "path": path, "remote": rest[len(OUTSIDE_ROOT) + 1:]}
    if not rest or not ep.get("url") or (folder and os.path.isdir(folder)):
        return None
    return {"source": rid, "path": path, "remote": root + "/" + rest if root else rest}


def _parts(heading):
    """A heading path's parts as `_heading_of` compares them: split at `›`, spaces collapsed, case folded."""
    return [" ".join(p.split()).casefold() for p in N(heading).split("›")]


def _heading_index(secs):
    """{exact, suffix}: the first section of each whole heading path and of each end of one, parts as `_parts` folds
    them — what `_heading_of` finds by scanning, in one map (`_names_past` asks it for every heading of a note)."""
    exact, suffix = {}, {}
    for h, _ in secs:
        if h:
            parts = tuple(_parts(h))
            exact.setdefault(parts, h)
            for n in range(1, len(parts) + 1):
                suffix.setdefault(parts[-n:], h)
    return {"exact": exact, "suffix": suffix}


def _heading_of(secs, want, index=None):
    """The heading path of the first section whose path ends in `want` — its last part, its last parts (`Delivery ›
    Fees`) or the whole path (spaces collapsed, case folded): how `[[Name#Heading]]` and `<path>#<heading>` name a
    section; None when the note has none. `index` (`_heading_index`) answers the same without a scan."""
    if index is not None:
        key = tuple(_parts(want))
        if len(key) > 1 and key in index["exact"]:
            return index["exact"][key]
        return index["suffix"].get(key)
    key = _parts(want)
    if len(key) > 1:                          # a whole path asked is that section before the end of a longer one
        exact = next((h for h, _ in secs if h and _parts(h) == key), None)
        if exact is not None:
            return exact
    for h, _ in secs:
        if h:
            parts = _parts(h)
            if len(key) <= len(parts) and parts[len(parts) - len(key):] == key:
                return h
    return None


def _heading_for(secs, heading, index=None):
    """The heading path a `#…` after a note names: the whole of it as one heading first (`C# tips`), then its parts
    between `#` as the end of a heading path (`#H1#H2` → `… › H1 › H2`) with a `^block` part dropped; a block alone
    (`#^a1b2c3`) is the section whose text holds that block id at the end of a line, else "" (the whole note); None
    when no section has it; since v3.16.2, when neither finds it, the parts joined back with `#` where a heading
    holds one (`#Delivery#C# tips` → `Delivery › C# tips`)."""
    hp = _heading_of(secs, heading, index)
    if hp is not None:
        return hp
    parts = [p.strip() for p in heading.split("#") if p.strip() and not p.strip().startswith("^")]
    if not parts:
        blocks = [p.strip()[1:] for p in heading.split("#") if p.strip().startswith("^") and len(p.strip()) > 1]
        if blocks:
            mark = re.compile(r"(?:^|\s)\^%s[ \t]*$" % re.escape(blocks[-1]), re.M)
            return next((h for h, t in secs if h and mark.search(t or "")), "")
        return ""
    joined = " › ".join(parts)
    hp = _heading_of(secs, joined, index) if joined != heading.strip() else None
    if hp is not None:
        return hp
    raw = heading.split("#")
    pieces = [] if any(p.strip().startswith("^") for p in raw[:-1]) else [p for p in raw if not p.strip().startswith("^")]
    if 2 < len(pieces) <= 8:                         # never across a block part in the middle                         # «C# tips» inside a nested link: join neighbours back with `#`
        for cuts in range(len(pieces) - 2, 0, -1):
            for at in itertools.combinations(range(1, len(pieces)), cuts):
                groups = ["#".join(pieces[a:b]).strip() for a, b in zip((0,) + at, at + (len(pieces),))]
                if all(groups):
                    hp = _heading_of(secs, " › ".join(groups), index)
                    if hp is not None:
                        return hp
    return None


def _index_name(sctx, abs_path):
    """The index's name of a file on disk: its vault's name, else `@<repository>/…` under the core folder of the
    registration that holds it (as the walk names it), else the absolute path — so that an exclusion is tested on
    the name, never on the folders above a core."""
    vaults = sctx.get("vaults") or []
    name = ci.rel_path(abs_path, vaults)
    if not name.startswith("/"):
        return name
    held = [r for r in sctx.get("repos") or [] if _folder(r) and r.get("id")]
    for r in sorted(held, key=lambda r: -len(os.path.realpath(_folder(r)))):    # the innermost core, as the walk does
        got = ci.rel_path(abs_path, vaults, ci.Root(r["id"], _folder(r)))
        if got.startswith("@"):
            return got
    return name


def _note_of(sctx, path):
    """(source, date, marks, said, sections, whole) of a note by its index name, read in this order: the server, for a
    name only a server holds now (`_mcp_entry`: an `@<repository>/…` name of a repository reached only over MCP, an
    `@<repository>/:/…` one outside its root, a vault name under a registered core folder gone from disk — since
    v3.16.2 first, so that neither the index's rows nor a local copy of it is served as current); the own section index
    (its sections; the whole note is their text joined under their headings); the file itself, when it is on disk and
    downloaded, through the time-budgeted reader (ctx_store.read_text); a registered local index's body (`_local_body`;
    `said` is the ICLOUD_LOCAL line when the file is one iCloud has not downloaded — never opened).
    `source` names the root the note lies under (`_root_source`: `own`, a repository id), else `vault` (a file outside
    every root) whichever source gave the text; `marks` is `_marks` of its frontmatter. None when nothing holds the
    note. GetError 3 — a file not downloaded that no local index holds (ICLOUD_MISSING), one not read in time, or a
    file that lies under an excluded folder after all (ctx_index.excluded of its real path, case-folded: a link, a
    spelling in another case); 5 — the server did not answer."""
    entry = _mcp_entry(sctx, path)       # a name only a server holds now: never the index's or a local copy (v3.16.2)
    if entry:
        body, date, meta, _ = _from_mcp(sctx, entry)
        return entry["source"], date, _marks(meta), None, ci.split_sections(body), _section_of(body, "")
    got = ci.Index(sctx["home"]).note(path)
    if got:
        meta, secs = got
        return (meta.get("source") or "own", meta.get("date"), _marks(meta), None, secs,
                "\n\n".join(p for p in (_as_markdown(h, t) for h, t in secs) if p))
    found = _file_of(sctx, path)
    if found and ci.excluded(_index_name(sctx, os.path.realpath(found)), sctx.get("store_rel"),
                             sctx.get("blocks_rels"), fold=True):
        raise GetError(3, EXCLUDED_NOTE % path)
    dataless = bool(found) and ci.is_dataless(found)
    try:
        mtime = os.stat(found).st_mtime if found else None
    except OSError:
        mtime = None
    if found and not dataless:
        try:
            body = cst.read_text(found)
        except (OSError, UnicodeError, cst.StoreError) as e:
            raise GetError(3, "the note cannot be read: %s (%s)" % (path, e))
        meta = ci.note_meta(path, body, mtime=mtime)
        return (_root_source(sctx, path) or "vault", meta.get("date"), _marks(meta), None, ci.split_sections(body),
                _section_of(body, ""))
    local = _local_body(sctx, path, found or os.path.join((sctx.get("vaults") or [""])[0], *path.split("/")))
    if local:
        meta = _local_meta(path, local, mtime=mtime)
        return (_root_source(sctx, path) or "vault", meta.get("date"), _marks(meta),
                ICLOUD_LOCAL % local[0] if dataless else None, ci.split_sections(local[1]), _section_of(local[1], ""))
    if found and dataless:
        raise GetError(3, _icloud_missing(sctx, path))
    return None


def _get_path(sctx, arg, full=False):
    """(header, text) of a note by its path (an index name, NFC or NFD; `.md` added when it has none) or its name
    (`Name`, `Name.md`, `[[Name]]`, `[[Name|alias]]`, an embed `![[…]]` — `_parse`), read as `_note_of` reads it. A
    target is a path first — a note at a vault's root is named `<name>.md`, with no `/`, as the list prints it — and a
    name only when no source holds that path (`_by_name`); a link with a folder in it is a path, else the end of one
    (`_by_tail`: the plugin folder's path first; an `@<repository>/…` name never). The whole note without its
    frontmatter under `> [<source> · <path> · <day>]` and its marks, cut by `_cap` (GET_CHARS, FULL_CHARS with
    `full`); with a heading after `#` (`[[Name#Heading]]`, `<path>#<heading>`, `#H1#H2`, `#^block` — `_heading_for`)
    that section alone under `> [<source> · <path> › <heading> · <day>]`, a short one going on with the next
    (`_fill`); GetError 3 for a heading the note lacks. A path the search excludes (ctx_index.excluded,
    case-folded: the store, a blocks file, `_System/_scratch/`) is GetError 3 EXCLUDED_NOTE. Reads only; last.json
    is not touched."""
    target, heading = _parse(arg)
    path = target if target.lower().endswith(".md") else target + ".md"
    if ci.excluded(path, sctx.get("store_rel"), sctx.get("blocks_rels"), fold=True):
        raise GetError(3, EXCLUDED_NOTE % path)
    note = _note_of(sctx, path)
    if note is None:
        if "/" not in target:
            path = _by_name(sctx, target[:-3] if target.lower().endswith(".md") else target)
        elif not path.startswith("@"):              # a repository's own name is never the end of another path
            path = _by_tail(sctx, path)
        else:
            raise GetError(3, NO_CANDIDATE % path)
        note = _note_of(sctx, path)
    if note is None:
        raise GetError(3, NO_CANDIDATE % path)
    source, date, marks, said, secs, whole = note
    hp = _heading_for(secs, heading, _heading_index(secs)) if heading else ""
    if hp is None:
        raise GetError(3, "no section %s in %s" % (heading, path))
    if hp:
        i = next(i for i, (h, _) in enumerate(secs) if h == hp)
        text = _cap(_fill(secs[i][1], secs[i + 1:]), path, full, secs, hp)
    else:
        text = _cap(whole, path, full, secs)
    return _header(source, path, hp, date, marks), (said + "\n\n" + text) if said else text


def _thousands(n):
    """20 000 — a number as the lines print it (a text such as `<усього>` as it is)."""
    return "{:,}".format(n).replace(",", " ") if isinstance(n, int) else str(n)


def long_note(path, shown, total, names, full):
    """The LONG_NOTE line under a text `--get` cut: how many of how many characters it gave, then the headings `names`
    (the one the cut falls under first; LONG_NAMES of them or LONG_NAMES_CHARS characters at most, then `· ще N`) with
    the --get of a section — or LONG_NONE — and, unless the text was asked for with --full, LONG_FULL."""
    if names:
        kept, size = [], 0
        for name in names:
            if kept and (len(kept) >= LONG_NAMES or size + len(name) > LONG_NAMES_CHARS):
                break
            kept.append(name)
            size += len(name) + 3
        listed = " · ".join(kept + (["ще %d" % (len(names) - len(kept))] if len(kept) < len(names) else []))
        tail = LONG_NEXT % (listed, path) + (" --full" if full else " або " + LONG_FULL)     # read as this one was
    else:
        tail = LONG_NONE + ("" if full else " — " + LONG_FULL)
    return LONG_NOTE % (_thousands(shown), _thousands(total), tail)


def _heading_lines(text):
    """[(offset, heading path parts, level)] of the heading lines of `text` that ctx_index.split_sections keeps as
    sections: level 1–3, none in a code fence, and — as it does — none with nothing under it (unless every one is
    empty); the path within the text, by the same stack of levels."""
    out, pos, fence, stack = [], 0, None, []
    for line in text.split("\n"):
        f = ci._FENCE.match(line)
        if fence:
            if f and f.group(1) == fence:
                fence = None
        elif f:
            fence = f.group(1)
        else:
            m = ci._HEADING.match(line)
            if m and len(m.group(1)) <= 3:
                level = len(m.group(1))
                stack = [(lv, t) for lv, t in stack if lv < level] + [(level, m.group(2).strip())]
                out.append((pos, [t for _, t in stack], level))
        pos += len(line) + 1
    ends = [p for p, _, _ in out[1:]] + [len(text)]
    filled = []
    for (p, _, _), e in zip(out, ends):
        nl = text.find("\n", p)
        filled.append(bool(text[nl if 0 <= nl < e else e:e].strip()))
    return [o for o, f in zip(out, filled) if f] if any(filled) else out


def _names_past(text, cut, path, secs, start=0):
    """The names LONG_NOTE gives for what lies past `cut` of `text` — the note's sections `secs` (ctx_index.
    split_sections) from `start` on, each matched in order to a heading line of the text (a heading the note's sections
    left out, one with nothing under it, is skipped): the section the cut falls under, then every one after it, each by
    the shortest end of its heading path (its last part, else more of it) that `--get "<path>#<name>"` — `_parse`, then
    `_heading_for` — takes back to that very section; one no name reaches (a heading another one shadows, `|` in it)
    is left out. Since v3.16.2 the heading lines with nothing under them are left out as split_sections leaves them out
    (an empty `## Notes` before the cut never takes the place of a `### Notes` after it), the names are found through
    one map of the note's headings, and the section the cut falls under is named only when --get of it shows
    LONG_GAIN characters more than the cut text does."""
    folded = [_parts(h) if h else [] for h, _ in secs]
    lines, aligned, k = _heading_lines(text), [], start
    for pos, line, _ in lines:                       # the lines and the sections leave out the same empty headings:
        key = _parts(line[-1])[-1]                   # in order, by the last part
        nxt = next((i for i in range(k, len(secs)) if folded[i] and folded[i][-1] == key), None)
        if nxt is not None:
            aligned.append((pos, nxt))
            k = nxt + 1
    before = [a for a in aligned if a[0] < cut][-1:]
    if before and min(len(secs[before[0][1]][1]), cut) - (cut - before[0][0]) < LONG_GAIN:
        before = []                                  # --get of it would show little more than the cut text does
    index, first = _heading_index(secs), {}
    for x, (h, _) in enumerate(secs):
        first.setdefault(h, x)
    out = []
    for _, i in before + [a for a in aligned if a[0] >= cut]:
        parts = secs[i][0].split(" › ")
        for n in range(1, len(parts) + 1):
            name = " › ".join(parts[-n:])
            hp = _heading_for(secs, _parse("%s#%s" % (path, name))[1], index)
            if hp and first.get(hp) == i:
                out.append(name)
                break
    return out


def _cap(text, path, full=False, secs=None, heading=""):
    """`text` as `--get` gives it: GET_CHARS characters at most (FULL_CHARS with --full), then the LONG_NOTE line with
    the names of what lies past the cut (`_names_past` over the note's sections `secs` — a list, or a function that
    reads them, called only for a text that is cut — from the section `heading` the text begins with; "" the note)."""
    limit = FULL_CHARS if full else GET_CHARS
    if len(text) <= limit:
        return text
    secs = (secs() if callable(secs) else secs) or []
    start = next((i for i, (h, _) in enumerate(secs) if h == heading), 0) if heading else 0
    return text[:limit] + "\n\n" + long_note(path, limit, len(text), _names_past(text, limit, path, secs, start), full)


def _header(source, path, heading, date, marks=""):
    """The provenance line `> [<source> · <path> › <heading> · <day>]` (no ` › ` for a whole note), then the marks."""
    return "> [%s · %s%s · %s%s]" % (source or "own", path, " › " + heading if heading else "", (date or "—")[:10],
                                     marks)


def _from_mcp(sctx, entry):
    """(text, date, meta, said) of an MCP candidate: vault_get_note on the path as the server gave it (`remote`); the
    date and meta are what the note's frontmatter says — the server's `frontmatter`, else what its `content` starts
    with; said is None."""
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
    inner = ci.note_meta(entry.get("remote") or "", content)

    def said(key):
        v = fm.get(key)
        return "" if v is None or isinstance(v, (list, dict)) else N(str(v)).strip()

    meta = {"type": said("type") or inner["type"], "status": said("status") or inner["status"],
            "sensitive": ci.sensitive_of(fm) or inner["sensitive"]}
    return content, _first_date(fm, ci.DATE_KEYS) or inner["date"] or "", meta, None


def _marks(meta):
    """What a note's frontmatter says that the list of a local index or a server could not: ` · sensitive`, ` ·
    застаріле` (its status is one of OUTDATED) and its type — the tail of a `--get` line."""
    meta = meta or {}
    status, ntype = str(meta.get("status") or "").strip().lower(), str(meta.get("type") or "").strip().lower()
    out = [SENSITIVE] if meta.get("sensitive") else []
    if status in OUTDATED:
        out.append(STALE)
    if ntype:
        out.append(ntype)
    return "".join(" · " + m for m in out)


def get(sctx, cid, full=False):
    """(header, text) of a candidate's section — or, for an argument that is no id (`_is_id`: ten hex digits) but a
    note's path or name, of the whole note or of one section of it (`_get_path`: a twin, a newer version, a note a hub
    links to — `<path>`, `Name`, `[[Name|alias]]`, `[[Name#Heading]]`, `<path>#<heading>`). For an id: the header
    `> [<source> · <path> › <heading> · <day>]` (an own section names the index's source of its note: `own`, or the
    repository of a core page), the text under the heading (a note-level candidate: the note without its
    frontmatter). The id is looked up in last.json (the last search), else among the sections of the own index — and
    one neither has is tried as a name (a note named by ten hex digits). An
    own section is read from the index (from its file when the note changed since); a note only a local index knows
    from the vault; an MCP one through vault_get_note. A file is read only through the time-budgeted reader, and
    never one iCloud has not downloaded (`_from_disk`: the text of a local index then, its line first — the whole
    note when that copy has no such section). A section shorter than 200 characters goes on with the next ones
    (`_fill`); the text is cut by `_cap` — GET_CHARS characters, FULL_CHARS with `full` (`--full`) — and the
    LONG_NOTE line names what lies past the cut. The header of a local or an MCP note goes on with what its frontmatter says (`_marks`: ` · sensitive`,
    ` · застаріле`, its type) — what the list of such a source does not carry, so its flags are complete only here.
    GetError: 3 — no such id, note or section, a file not read in time or not downloaded; 5 — the server did not
    answer. Reads only."""
    arg = str(cid or "").strip()
    if not _is_id(arg):
        return _get_path(sctx, arg, full)
    cid = arg.lower()
    idx = ci.Index(sctx["home"])
    entry = _load_last(sctx["home"]).get(cid)
    if not isinstance(entry, dict) or not entry.get("path"):
        entry = _in_index(idx, cid)
    if not entry:
        return _get_path(sctx, arg, full)       # a note named like an id; else NO_CANDIDATE, as for a name
    heading, date, text, marks = entry.get("heading") or "", entry.get("date") or "", None, ""
    said, following = None, []
    secs = lambda: (idx.note(entry["path"]) or (None, []))[1]  # noqa: E731 — the note's sections, for a cut text
    if entry.get("kind") == "own":
        sec = idx.section(entry.get("section_id")) if entry.get("section_id") is not None else None
        if sec and N(sec["path"]) == entry["path"] and (sec.get("heading") or "") == heading:
            text, date = sec.get("text") or "", sec.get("date") or date
            entry = dict(entry, source=sec.get("source") or entry.get("source"))
            following = idx.following(sec["note_id"], sec["ord"], chars=FILL_CHARS)
    if text is None:
        if entry.get("kind") == "mcp":
            body, day, meta, said = _from_mcp(sctx, entry)
        else:
            body, day, meta, said, via = _from_local(sctx, entry)
            if via:                                      # read through the server: its line and its day
                entry, date = dict(entry, source=via, kind="mcp"), ""
        text, date = _section_of(body, heading), date or day
        secs = ci.split_sections(body)
        following = _after(body, heading)
        if text is None and said:           # a local index's copy without that section: the whole note, never the file
            text, following = _section_of(body, ""), []
        if text is None:
            raise GetError(3, "no section %s in %s" % (heading, entry["path"]))
        if entry.get("kind") in ("local", "mcp"):
            marks = _marks(meta)
    text = _cap(_fill(text, following), entry["path"], full, secs, heading)
    return _header(entry.get("source"), entry["path"], heading, date, marks), (said + "\n\n" + text if said else text)


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
