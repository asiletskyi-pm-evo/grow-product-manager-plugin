#!/usr/bin/env python3
"""Grow PM — the section index of the search (since v3.16.0).

`ctx search` looks for what a question is about in an index of its own: the plugin folder of every vault and the local
core folder of every registered repository, one row per section — a heading of level 1–3 and the text under it — with
every column stemmed by ctx_stem exactly as a question is. The index is a cache in `<home>/.grow-pm/index/`, outside
the vault (iCloud never syncs it): deleting the folder is safe, `ctx index rebuild` builds it again.

- scope / rel_path / excluded   what is indexed and how a file is named: NFC, `/`, from the root of its vault with the
                                top folder (`Notes/…`, `ZorgCore/…`), or `@<repository>/…` outside every vault.
- split_sections / note_meta / version_key / name_key   a note's sections and its metadata (the frontmatter, else the
                                text); a frontmatter that cannot be read leaves the whole note as text, without metadata.
- link_only / strip_links       a breadcrumb line or a line of links alone, and a text without such lines.
- near_key                      the key two near copies of a note share (the search folds them), kept per note.
- is_dataless                   a file iCloud has not downloaded: reading it would start the download, so it is skipped.
- evicted / download            (since v3.16.1) `ctx index rebuild --download` alone: the plugin folder's files iCloud
                                evicted that the index would read, each read once in a child process (DOWNLOAD_S at
                                most, DOWNLOAD_WORKERS at once) so that macOS brings it down — never a core folder.
- Index                         sections.sqlite (notes, sections, the FTS5 table sections_fts, meta), index.json (the
                                state the session digest reads) and index.lock (one refresh at a time); `built` — has
                                a walk ever finished into it (its meta `updated` row), `lock_held` — is one going on.
- identity_of / links_of / mentions_of   (since v3.18.0) what the walk writes beside every note for `ctx entity`:
                                its identity when it is a card (only the identity fields — never a profile's judgement),
                                its wiki links as written, its Jira-key-shaped tokens — the tables ents, links and
                                mentions; Index.cards / links_to / mentions read them, a row whose hash is not its
                                note's (an older build changed the note) never.

The refresh is incremental. It walks the roots as os.walk(followlinks=False) would — and, since v3.16.2, follows no
link to a file either, and compares the excluded folder names case-folded — one folder at a time so that it can
stop and go on later: a file whose mtime and size did not change is not read, a changed one is read again (sha1 of its
bytes). A row goes only when its file is gone from a folder the walk listed; a file iCloud has not downloaded keeps its
row. The walk stops at its time budget (30 s) and leaves the folders and files it did not reach in a queue in
index.json, which the next run takes first. A sections.sqlite of another schema (or whose notes table lacks a column
of this build), or one SQLite cannot read, is put aside as sections.sqlite.broken and built again. While another
process holds index.lock (younger than 600 s, its process alive) the refresh does nothing and the queries read the
index as it is.

Writes only under `<home>/.grow-pm/index/` (through ctx_store.check_target, so inside `ctx` the write guard holds);
reads the vault and the core folders; no network of its own (`rebuild --download` has macOS bring files down from
iCloud). Stdlib only.
"""
import bisect
import collections
import datetime
import functools
import hashlib
import json
import os
import re
import signal
import sqlite3
import stat
import subprocess
import sys
import threading
import time
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx_common as cc  # noqa: E402
import ctx_stem as st  # noqa: E402
import ctx_slots as sl  # noqa: E402
import ctx_store as cs  # noqa: E402

SCHEMA = "search-index/1"
REFRESH_S = 30.0                    # the time budget of one refresh
MAX_BYTES = 2_000_000               # a file larger than this is not indexed
LOCK_STALE_S = 600.0                # a lock older than this is abandoned
SF_DATALESS = 0x40000000            # st_flags of a file whose data is not on disk (macOS, iCloud)
DOWNLOAD_S = 30.0                   # rebuild --download: one file's time to come down, then it is left
DOWNLOAD_WORKERS = 4                # rebuild --download: files read at once
_READ_ONE = ("import signal, sys; getattr(signal, 'alarm', int)(int(sys.argv[2])); open(sys.argv[1], 'rb').read(1)")
                                    # the child's read that brings a file down; it stops itself a little after its time
DB_NAME, STATE_NAME, LOCK_NAME = "sections.sqlite", "index.json", "index.lock"
BM25 = (10.0, 6.0, 4.0, 4.0, 1.0)   # title, heading, tags, aliases, body
HUB_TYPES = frozenset(("glossary", "moc", "people", "person", "focus-brief", "daily-summary"))
PEOPLE_TYPES = frozenset(("people", "person", "one-on-one-notes", "performance-review", "offboarding-plan",
                          "delegation-audit", "followup-arcv", "one-on-one"))
                                    # data-policy.md (Search, rule 1): taken only by the People contour (v3.17.0)
STEP_P_FIELDS = ("d_type", "d_history", "recommended_style", "signals", "one_on_one", "gtd_index", "forecast_qa",
                 "delegation", "active_goal_letter")   # a person profile's judgement (people-context-protocol.md)
ONE_ON_ONE = re.compile(r"(?<![^\W_])(?<![.:/-])(?:1\s?[-:]\s?1|1[-\s]?on[-\s]?1|one[-\s_]?on[-\s_]?one)s?"
                        r"(?![^\W_]|[./]|-\d|:\d)", re.I)
                                    # a 1-1 named in a title, a folder or a file name: `1-1 …`, `… 1-1`, `1:1 …`,
                                    # `1-1: …`, `1on1s/`, `1-on-1`, `One-on-ones/`, `1-1_Bea`, `1-1-Logs/`
NOT_ONE_ON_ONE = re.compile(r"(?:split|спліт|розподіл|ratio|співвідношенн\w*|пропорці\w*|крок|step|етап|пункт|"
                            r"round|раунд)\W*$", re.I)   # «Split 1:1», «Крок 1-1» — a ratio or a step
HUB_TITLE = re.compile(r"style guide|глосарій|glossary|абревіатури", re.I)
TRUE = ("true", "yes", "1")
NULLISH = ("", "~", "null", "none", "false")   # a frontmatter value that says nothing
DATE_KEYS = ("updated", "modified", "snapshot", "generated", "date", "created")
TTL_DATE_KEYS = ("updated", "snapshot", "generated")   # the note's own date a class TTL is counted from (provider protocol §6)
COMMIT_EVERY = 50                   # files written between two commits of a refresh
STUB_CHARS = 200                    # a section shorter than this (its breadcrumb lines aside) is short: --get and its
                                    # snippet go on with the sections after it (ctx_search)
NEAR_MIN, NEAR_CHARS = 400, 20_000  # near copies: the characters a key needs at least, and the ones it reads
NEAR_VERSION = 2                    # the rules of near_key (meta `near_version`): an index of other rules gets its keys
                                    # again from its own sections (v3.16.2: a list of links is content)
META_VERSION = 4                    # the rules of note_meta (meta `meta_version`): an index of other rules reads its
                                    # downloaded files once more (v3.17.0: a people type or a Step-P field is sensitive;
                                    # v3.18.0: the identity, link and mention rows of every note; v3.19.0: a card's slot
                                    # fields, no link or mention in code, Jira prefixes without JQL words, a work key's
                                    # order). The catalogue's card_names_version the fields were kept by is meta
                                    # `slot_names`: a higher one (names changed) reads the cards alone once more
ENTITY_KINDS = {"people": "person", "person": "person", "team": "team", "mission": "mission", "module": "module",
                "metric": "metric", "epic": "work", "feature": "work", "project": "work"}
                                    # a note's type → the kind of entity it is a card of (v3.18.0, plan C1)
ISSUE_KEY = re.compile(r"(?<![A-Za-z0-9])([A-Z][A-Z0-9]{1,9})-(\d{1,6})(?![A-Za-z0-9])")   # a key-shaped token
BROWSE_KEY = re.compile(r"/browse/([A-Z][A-Z0-9]{1,9}-\d{1,6})(?![0-9])")                   # a key a Jira link names
_EMAIL = re.compile(r"^[^@\s<>()\[\],;:\"]+@[^@\s<>()\[\],;:\"]+\.[^@\s<>()\[\],;:\"]+$")
_PREFIX = re.compile(r"(?<![A-Za-z0-9])[A-Z][A-Z0-9]{1,9}(?![A-Za-z0-9])")
_PROJECT = re.compile(r"\bproject\s*(?:=|\bin\b)\s*\(?([^)\n]*?)(?:\)|\s+(?:and|or|order)\b|$)", re.I | re.M)
                                    # the projects a JQL names — never those it leaves out (`!=`, `not in`)
_PREFIX_LIST = re.compile(r"\s*[A-Z][A-Z0-9]{1,9}(?:\s*[,;/ ]\s*[A-Z][A-Z0-9]{1,9})*\s*")
_LEAD_PREFIX = re.compile(r"^([A-Z][A-Z0-9]{1,9})(?=\s+[^\s=!])(?!\s+(?:in|not|is|was)\b)")
_PROJECTS_URL = re.compile(r"/projects/([A-Z][A-Z0-9]{1,9})(?![A-Za-z0-9])")
JQL_WORDS = frozenset(("AND", "OR", "NOT", "IN", "IS", "EMPTY", "NULL", "ORDER", "BY", "ASC", "DESC", "WAS", "CHANGED",
                       "DONE", "TODO", "OPEN", "CLOSED", "CURRENTUSER"))   # a JQL word is never a project (v3.19.0)
WORK_KEY_FIELDS = ("jira", "key", "issue", "jirakey", "issuekey")   # a work card's own key fields (card_norm), first
EMAIL_FIELDS = frozenset(("email", "emails", "mail", "emailaliases", "emailalias", "emailaddress", "emailaddresses"))
                                    # a card's own address fields (their names without `-` and `_`): `manager_email`
                                    # is someone else's (v3.18.0 review)
COUNTS = ("added", "changed", "removed", "pending", "skipped_dataless", "skipped_large")
BROKEN_NOTE = "індекс пошуку не читається (%s) — ctx index rebuild збудує його наново"
BUSY_NOTE = "індекс пошуку зайнятий іншим процесом — цього разу без нього"
QUERY_NOTE = "індекс пошуку не прийняв вираз (%s)"
DAMAGE_WORDS = ("corrupt", "malformed", "missing row")    # an FTS5 error that is a damaged file, not a bad expression
N = cc.N

DDL = """
CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE notes(id INTEGER PRIMARY KEY, path TEXT UNIQUE, source TEXT, title TEXT, type TEXT, product TEXT,
                   status TEXT, date TEXT, ttl_date TEXT, confluence_id TEXT, aliases_json TEXT, tags_json TEXT,
                   sensitive INTEGER, hub INTEGER, version_key TEXT, links_json TEXT, hash TEXT, near TEXT, mtime REAL,
                   size INTEGER);
CREATE TABLE sections(id INTEGER PRIMARY KEY, note_id INTEGER, heading TEXT, ord INTEGER, text TEXT);
CREATE INDEX sections_note ON sections(note_id);
CREATE VIRTUAL TABLE sections_fts USING fts5(title, heading, tags, aliases, body,
                                             tokenize='unicode61 remove_diacritics 2');
"""
ENTITY_DDL = """
CREATE TABLE IF NOT EXISTS ents(note_id INTEGER PRIMARY KEY, hash TEXT, path TEXT, kind TEXT, label TEXT, emails_json TEXT,
                                team TEXT, role TEXT, slug TEXT, aliases_json TEXT, key TEXT, bridges_json TEXT,
                                prefixes_json TEXT, fields_json TEXT);
CREATE TABLE IF NOT EXISTS links(note_id INTEGER, field TEXT, target TEXT, tkey TEXT, anchor TEXT, label TEXT,
                                 embed INTEGER);
CREATE INDEX IF NOT EXISTS links_tkey ON links(tkey);
CREATE INDEX IF NOT EXISTS links_note ON links(note_id);
CREATE TABLE IF NOT EXISTS mentions(note_id INTEGER, key TEXT, browse INTEGER);
CREATE INDEX IF NOT EXISTS mentions_key ON mentions(key);
CREATE INDEX IF NOT EXISTS mentions_note ON mentions(note_id);
"""                                 # v3.18.0: one `ents` row per note (kind "" for a note that is no card) with the
                                    # note's hash and path, so a row an older build left behind is known as stale
                                    # (plan C11) — the path too, as SQLite gives a removed note's id to the next one
ENTITY_TABLES = ("ents", "links", "mentions")
GRAPH_DDL = """
CREATE TABLE IF NOT EXISTS names(path TEXT PRIMARY KEY, source TEXT, dataless INTEGER, md INTEGER);
"""                                 # the derived tables (edges, unresolved, graph_src) are ctx_graph.EDGE_DDL: dropped
                                    # and made again whenever their rules change (ctx_graph.GRAPH_VERSION)                                 # v4.0.0: every file a link may land on (`names`, evicted ones too) and the links
                                    # resolved (ctx_graph.build) — added in place to an earlier build's file
ENTITY_COLS = ("kind", "label", "emails_json", "team", "role", "slug", "aliases_json", "key", "bridges_json",
               "prefixes_json", "fields_json")       # fields_json since v3.19.0: an earlier build's table gets it in place
NOTE_COLS = ("path", "source", "title", "type", "product", "status", "date", "ttl_date", "confluence_id",
             "aliases_json", "tags_json", "sensitive", "hub", "version_key", "links_json", "hash", "near", "mtime",
             "size")
ROW_SQL = ("SELECT s.id AS id, s.heading, s.ord, s.text, n.id AS note_id, %s FROM sections s "
           "JOIN notes n ON n.id = s.note_id" % ", ".join("n." + c for c in NOTE_COLS))
QUERY_SQL = ("SELECT s.id AS id, s.heading, s.ord, s.text, n.id AS note_id, %s, bm25(sections_fts, %s) AS rank "
             "FROM sections_fts JOIN sections s ON s.id = sections_fts.rowid JOIN notes n ON n.id = s.note_id "
             "WHERE sections_fts MATCH ? ORDER BY rank LIMIT ?"
             % (", ".join("n." + c for c in NOTE_COLS), ", ".join(str(w) for w in BM25)))


def _clock():
    """The clock of the time budget (a test turns it into a counter)."""
    return time.monotonic()


def _slash(path):
    return path.replace(os.sep, "/")


def index_dir(home):
    """`<home>/.grow-pm/index` — the index's folder."""
    return os.path.join(home or os.path.expanduser("~"), ".grow-pm", "index")


# ------------------------------------------------------------------ scope and names
def Root(source, path, vault=""):
    """One folder the index walks: `source` is "own" (the plugin folder of a vault) or a repository id; `vault` is the
    vault the folder lies in ("" outside every vault)."""
    return {"source": source, "path": path, "vault": vault}


@functools.lru_cache(maxsize=8192)
def _real_dir(d):
    """A folder's path with its links resolved — once per folder in a process (v3.19.0: a local index of thousands of
    notes asked realpath of each, a stat of every part of every path)."""
    return N(os.path.realpath(d))


def _spellings(path):
    """The path as given (absolute, normalised, NFC) and, when it differs, with its links resolved (/tmp on macOS) —
    its folder's resolved once (_real_dir), the file itself by one lstat."""
    a = N(os.path.normpath(os.path.abspath(os.path.expanduser(N(path)))))
    d, name = os.path.split(a)
    b = N(os.path.realpath(a)) if not name or os.path.islink(a) else N(os.path.join(_real_dir(d), name))
    return (a,) if a == b else (a, b)


def _within(path, root):
    root = root.rstrip("/") or "/"
    return path == root or path.startswith(root if root == "/" else root + "/")


def _vault_of(path, vaults):
    for v in vaults:
        if any(_within(p, s) for p in _spellings(path) for s in _spellings(v)):
            return v
    return ""


def scope(context_text, repos):
    """The roots of the index: `own` for `<vault>/<plugin folder>` of every vault of local-context.md, and the
    repository's id for the core folder (`core_root`, else its first path) of every registration whose folder is on
    disk. A folder named twice is walked once (the first name)."""
    entries = cc.vault_entries(context_text)
    vaults = [v for v, _ in entries]
    out, seen = [], set()

    def add(source, path, vault):
        key = os.path.normpath(path)
        if key not in seen:
            seen.add(key)
            out.append(Root(source, key, vault))

    for vault, folder in entries:
        add("own", os.path.join(vault, folder) if folder else vault, vault)
    for r in repos or []:
        path = r.get("core_root") or next(iter(r.get("paths") or []), "")
        if path and os.path.isdir(path):
            add(r.get("id") or "", path, _vault_of(path, vaults))
    return out


def rel_path(abs_path, vaults, root=None):
    """The index's name of a file: NFC, `/`, relative to the first vault that holds it, with the top folder (`Notes/…`);
    outside every vault `@<source>/<path relative to root>` when `root` (a Root) holds it, else the absolute path."""
    for p in _spellings(abs_path):
        for v in vaults or []:
            for s in _spellings(v):
                if _within(p, s):
                    rel = os.path.relpath(p, s)
                    return "" if rel == "." else _slash(rel)
    if root:
        for p in _spellings(abs_path):
            for s in _spellings(root["path"]):
                if _within(p, s):
                    rel = os.path.relpath(p, s)
                    return "@" + root["source"] + ("" if rel == "." else "/" + _slash(rel))
    return _slash(_spellings(abs_path)[0])


COPY_SERVICE = (".ctx-copy", ".backup", ".removed")        # ctx_copy: its state, backups and moved notes


def _copy_service(path):
    """Is the folder `path` a service folder of the plugin's copy of a core (since v3.24.0, ctx_copy) — one of
    COPY_SERVICE beside a `.ctx-copy/state.json`? Only a copy has one, so a folder of that name anywhere else is walked
    as before."""
    return os.path.basename(path) in COPY_SERVICE and os.path.isfile(
        os.path.join(os.path.dirname(path), ".ctx-copy", "state.json"))


def _skip_folder(rel, store_rel, fold=False):
    """A folder (or a file in it) the index never enters: the store, `_System/providers/`, `_System/_scratch/` (the
    plugin's scratch files — per-person digests among them), `.obsidian`, `.trash`, a name that starts with
    `_backup`. These names are compared case-folded (since v3.16.2, in the walk too: `_Backup 2025`, `.Trash`); the
    store only with `fold` (`excluded` for a path a user typed)."""
    if store_rel:
        low = str.casefold if fold else str
        s = low(_slash(N(store_rel)).rstrip("/"))
        if s and (low(rel) == s or low(rel).startswith(s + "/")):
            return True
    parts = [p.casefold() for p in rel.split("/")]
    for i, part in enumerate(parts):
        if part in (".obsidian", ".trash") or part.startswith("_backup"):
            return True
        if part == "_system" and i + 1 < len(parts) and parts[i + 1] in ("providers", "_scratch"):
            return True
    return False


def excluded(rel, store_rel, blocks_rels, fold=False):
    """Is the file `rel` (an index name) left out: under the store, `_System/providers/` or `_System/_scratch/`, a
    blocks file of a registration, in a `.obsidian`, `.trash` or `_backup…` folder, not `.md`, or `local-context.md`
    itself. Every source's hits go through it, not only the walk; the folder names and `local-context.md` are
    compared case-folded (`_skip_folder`), the store and the blocks files exactly as the index names them — with `fold`
    case-folded too, for a path a user typed on a case-insensitive disk (`ctx search --get`)."""
    low = str.casefold if fold else str
    rel = _slash(N(rel or ""))
    if _skip_folder(rel, store_rel, fold) or low(rel) in {low(_slash(N(b))) for b in blocks_rels or ()}:
        return True
    name = rel.rsplit("/", 1)[-1]
    return not name.lower().endswith(".md") or name.casefold() == "local-context.md"


# ------------------------------------------------------------------ a note
_HEADING = re.compile(r"^(#{1,6})[ \t]+(.+?)(?:[ \t]+#+)?[ \t]*$")
_FENCE = re.compile(r"^[ \t]{0,3}(```|~~~)")
_FM_KEY = re.compile(r"^([^\s:#\-\[\]{}][^:]*?)[ \t]*:(?:[ \t]+(.*))?$")
_WIKI = re.compile(r"\[\[([^\]\n]+?)\]\]")
_CID = re.compile(r"\((\d{6,})\)\.md$", re.I)
_DATE = re.compile(r"^(\d{4}-\d{2}-\d{2})(?:[T ](\d{2}:\d{2}(?::\d{2})?))?")
_MARK = re.compile(r"\b(?:v\d+|draft|драфт(?:\s*№\s*\d+)?|rev\d+|ревізія\s*\d+)\b", re.I)
_DATES = re.compile(r"\d{4}-\d{2}-\d{2}|\d{2}\.\d{2}(?:\.\d{2,4})?")
_LINK = re.compile(r"!?\[\[[^\]\n]*\]\]|!?\[[^\]\n]*\]\([^)\n]*\)")
_LIST_ITEM = re.compile(r"^\s*(?:>\s*)*(?:[-*+]|\d+[.)])\s+\S")    # a list item, in a callout too
_CODE = re.compile(r"`([^`\n]*)`")
_SEPARATORS = re.compile(r"^[\s·•|/\\<>‹›«»←→↑↓\-–—*_=~,;.:]*$")
_NAV = (r"(?:up|moc|parent|related|back|source|index|hub|пов[ʼ'’]?язан[еі]|зв[ʼ'’]?язки|назад|батьківська|джерело)")
_LABEL = re.compile(r"^[\s*_>\-]*%s[\s*_]*::?[\s*_]*" % _NAV, re.I)
_RELATED_WORD = r"(?:пов[ʼ'’]?язан[еі](?:\s+нотатки)?|зв[ʼ'’]?язки|related(?:\s+notes)?)"
_RELATED = re.compile(r"^%s$" % _RELATED_WORD, re.I)
_RELATED_LINE = re.compile(r"^[\s*_#>\-]*%s[\s*_]*:?[\s*_]*$" % _RELATED_WORD, re.I)
_WHEN = (r"(?:(?:last\s+)?(?:updated|modified)|created|date|generated|snapshot|оновлено|змінено|створено"
         r"|дата(?:\s+оновлення)?|станом\s+на)")
_DATE_LINE = re.compile(r"^[\s>*_\-–—•]*(?:%s[\s*_]*:{0,2}[\s*_]*)?(?:\[\[)?"
                        r"(?:\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2})?)?|\d{1,2}\.\d{1,2}\.\d{2,4})"
                        r"(?:\]\])?[\s*_.]*$" % _WHEN, re.I)


def _split_flow(s):
    """`a, "b, c", d` → items, the commas inside quotes kept."""
    items, cur, q = [], [], None
    for ch in s:
        if q:
            cur.append(ch)
            if ch == q:
                q = None
        elif ch in "\"'":
            q = ch
            cur.append(ch)
        elif ch == ",":
            items.append("".join(cur)); cur = []
        else:
            cur.append(ch)
    items.append("".join(cur))
    return [i.strip() for i in items if i.strip()]


def _fm_value(v):
    """One frontmatter value as text, or a list of texts for a flow list `[a, b]`; a wiki link `[[X]]` stays text."""
    v = v.strip()
    if v[:1] in ("'", '"'):
        q = v[0]
        if len(v) >= 2 and v.endswith(q):
            inner = v[1:-1]
            if q == "'":
                return inner.replace("''", "'")
            try:
                return json.loads(v)
            except ValueError:
                return inner
        return v.strip(q)
    v = re.sub(r"\s+#\s.*$", "", v).strip()
    if v.startswith("[[") and v.endswith("]]"):
        return v
    if v.startswith("[") and v.endswith("]"):
        return [x for x in (_fm_value(i) for i in _split_flow(v[1:-1])) if isinstance(x, str) and x]
    return v


def _read_frontmatter(lines):
    """{key (lower case): text | [texts]} of the frontmatter lines, or None when they are not YAML this reader trusts:
    a tab in the indentation, or a line at the margin that is neither `key: value` nor an item `- x` of the list a key
    with no value opened (`tags:` then `- a` at the margin is how PyYAML writes a list). Since v3.17.0 the indented
    `sub: value` lines under a key with no value are read as one map {sub: value} (a deeper level joins it; a list
    inside the map is left out) — a person profile writes `signals:` and `one_on_one:` so."""
    data, cur = {}, None
    for raw in lines:
        raw = raw.rstrip("\r")
        if not raw.strip() or raw.lstrip(" ").startswith("#"):
            continue
        lead = raw[:len(raw) - len(raw.lstrip(" \t"))]
        if "\t" in lead:
            return None
        item = raw.strip()
        if cur is not None and (item == "-" or item.startswith("- ")):
            if isinstance(data.get(cur), dict):      # a list inside the map: not read
                continue
            v = _fm_value(item[1:])
            if not isinstance(data.get(cur), list):
                data[cur] = []
            if isinstance(v, str) and v:
                data[cur].append(v)
            continue
        if not lead:
            m = _FM_KEY.match(raw.rstrip())
            if not m:
                return None
            key, val = m.group(1).strip().lower(), (m.group(2) or "").strip()
            data[key] = _fm_value(val) if val else ""
            cur = None if val else key
        elif cur is not None and not (isinstance(data.get(cur), list) and data[cur]):
            m = _FM_KEY.match(item)
            if m:
                if not isinstance(data.get(cur), dict):
                    data[cur] = {}
                sub, sval = m.group(1).strip().lower(), (m.group(2) or "").strip()
                data[cur][sub] = _fm_value(sval) if sval else ""
    return data


def _frontmatter(text):
    """(metadata, body). No frontmatter: ({}, text). One that is never closed or cannot be read: (None, text) — the
    whole note is then text."""
    t = (text or "").lstrip("﻿")
    lines = t.split("\n")
    if lines[0].rstrip("\r ") != "---":
        return {}, t
    end = next((i for i in range(1, len(lines)) if lines[i].rstrip("\r ") in ("---", "...")), None)
    if end is None:
        return None, t
    data = _read_frontmatter(lines[1:end])
    if data is None:
        return None, t
    return data, "\n".join(lines[end + 1:])


def _path_span(m):
    """A backticked span that is a path — `a/b/c.md` (a `/`, no space) or `Space / Parent / Page` — as a space; any
    other code span (`npm install zorg`) as it is."""
    inner = m.group(1)
    return " " if ("/" in inner and " " not in inner) or " / " in inner else m.group(0)


def link_only(line, label=False):
    """Is the line a breadcrumb — it starts with `↑ [[` (a Confluence mirror's way up) — or nothing but wiki links,
    embeds (`![[x.png]]`), Markdown links, backticked paths (`_path_span`) and separators (`·`, `|`, `/`, `›`, `—`,
    `---` …)? With `label`, a navigation label before the links counts too — Up, MOC, Parent, Related, Back, Source,
    Index, Hub, Повʼязане, Зв'язки, Назад, Батьківська, Джерело (`Up:: [[Zorg MOC]]`, `**MOC:** [[Research]]`); any
    other label (`Owner: [[Bea Two]]`) is text. An empty line is not one."""
    s = (line or "").strip()
    if s.startswith("↑ [["):
        return True
    if label and _LINK.search(s):
        s = _LABEL.sub("", s, count=1)
    return bool(s) and bool(_SEPARATORS.match(_CODE.sub(_path_span, _LINK.sub(" ", s))))


def strip_links(text, label=False):
    """The text without its `link_only` lines."""
    return "\n".join(line for line in (text or "").split("\n") if not link_only(line, label))


def _near_aside(line):
    """Does near_key set the line aside: a date line (a dated bullet, `- [[2026-03-01]]`, too), or a breadcrumb or a
    line of links (with a navigation label or none) that is no list item of links alone."""
    if _DATE_LINE.match(line):
        return True
    if _LIST_ITEM.match(line) and link_only(line):
        return False
    return link_only(line, label=True)


def near_key(sections):
    """The key two near copies of a note share (`Knowledge/sources/x.md` and `Research/x.md`), from its sections
    (split_sections: no frontmatter): sha1 of the first NEAR_CHARS characters of their heading paths and text, without
    the trailing «Повʼязане» / «Зв'язки» / «Related» block (sections under such a heading at the end, or a label line of
    that name in the last one and what follows it), the breadcrumb and navigation link lines (`link_only` with a label:
    `Up:: [[MOC]]` — never `Owner: [[X]]`, and never a list item of links alone, `- [[Bea Two]]`: a list of owners or
    attendees is the note's content, since v3.16.2), the lines that are only a date or the day a note was updated or
    made (`2026-10-07`, `Оновлено: 07.10.2026` — never `Deadline: …`) and the whitespace. None when fewer than NEAR_MIN
    characters of text are left (the headings do not count) — a short note never folds."""
    secs = [(h or "", b or "") for h, b in sections or []]
    while secs and any(_RELATED.match(p.strip(" *_:")) for p in secs[-1][0].split(" › ") if p):
        secs.pop()
    blocks = [b.split("\n") for _, b in secs]
    if blocks:
        cut = max((i for i, line in enumerate(blocks[-1]) if _RELATED_LINE.match(line)), default=None)
        if cut is not None:
            blocks[-1] = blocks[-1][:cut]
    kept, size = [], 0
    for (heading, _), lines in zip(secs, blocks):
        body = " ".join(" ".join(line for line in lines if not _near_aside(line)).split())
        size += len(body)
        kept += [heading, body]
    if size < NEAR_MIN:
        return None
    text = " ".join(" ".join(kept).split())
    return hashlib.sha1(text[:NEAR_CHARS].encode("utf-8")).hexdigest()


def split_sections(text):
    """[(heading path "H1 › H2 › H3", body)] for the headings of level 1–3 (a deeper heading stays in the body, a `#` in
    a code fence is no heading). The frontmatter is cut; text before the first heading is a section of its own when
    it has any — a mirror's breadcrumb too (that short row carries the note's title and ranks on it; `ctx search`
    goes on from it to the next sections, ctx_search._fill); a heading with nothing under it is left out unless every
    one is empty. No heading: [("", text)]."""
    _, body = _frontmatter((text or "").replace("\r\n", "\n"))
    out, stack, head, buf, fence, seen = [], [], "", [], None, False
    for line in body.split("\n"):
        f = _FENCE.match(line)
        if fence:
            buf.append(line)
            if f and f.group(1) == fence:
                fence = None
            continue
        if f:
            fence = f.group(1)
            buf.append(line)
            continue
        m = _HEADING.match(line)
        if m and len(m.group(1)) <= 3:
            out.append((head, "\n".join(buf).strip("\n")))
            level = len(m.group(1))
            stack = [(lv, t) for lv, t in stack if lv < level] + [(level, m.group(2).strip())]
            head, buf, seen = " › ".join(t for _, t in stack), [], True
            continue
        buf.append(line)
    out.append((head, "\n".join(buf).strip("\n")))
    if not seen:
        return [("", out[0][1])]
    pre, headed = out[0], out[1:]
    full = [s for s in headed if s[1].strip()]
    return ([pre] if pre[1].strip() else []) + (full or headed)


def _text(v):
    """A frontmatter value as one line of text ('' for nothing, a list or a map)."""
    return "" if v is None or isinstance(v, (list, dict)) else N(str(v)).strip()


def _filled(v):
    """Does a frontmatter value say something? Not None or false, not blank, `~`, `null`, `none`, `false` or a
    comment, and not a list or a map of such values only."""
    if v is None or v is False:
        return False
    if isinstance(v, (list, dict)):
        return any(_filled(x) for x in (v.values() if isinstance(v, dict) else v))
    if isinstance(v, str):
        t = N(v).strip()
        return bool(t) and t.lower() not in NULLISH and not t.startswith("#")
    return True


def sensitive_of(fm):
    """Is a note sensitive by what its frontmatter says (since v3.17.0)? `sensitive: yes`, a people type (PEOPLE_TYPES,
    any case, one of a list of types too), or a person profile's judgement field (STEP_P_FIELDS) with a value, at the
    top or one map down (`reporting: forecast_qa`) — whatever `sensitive` says then."""
    fm = fm if isinstance(fm, dict) else {}
    types = fm.get("type") if isinstance(fm.get("type"), list) else [fm.get("type")]
    if _text(fm.get("sensitive")).lower() in TRUE or any(_text(t).lower() in PEOPLE_TYPES for t in types):
        return True
    maps = [fm] + [v for v in fm.values() if isinstance(v, dict)]
    return any(_filled(m.get(k)) for m in maps for k in STEP_P_FIELDS)


def one_on_one(path, title=""):
    """Is a note a 1-1 by its title or a folder of its path (`1-1 …`, `1:1 …`, `1on1 …`, `1-1-Logs/`, one-on-one),
    whatever its type (since v3.17.0: 1-1 notes are kept as `meeting` notes too)? Never by a key, a date, a quarter,
    a ratio or a step (NOT_ONE_ON_ONE right before it). A file name is matched without its `.md`."""
    for part in [_text(title)] + N(str(path or "")).split("/"):
        part = part[:-3] if part.lower().endswith(".md") else part
        if any(not NOT_ONE_ON_ONE.search(part[:m.start()]) for m in ONE_ON_ONE.finditer(part)):
            return True
    return False


def _items(v, tags=False):
    """A list of texts: a list as it is, a scalar split on commas (tags: on spaces too, `#` dropped)."""
    raw = v if isinstance(v, list) else (_text(v).split(",") if _text(v) else [])
    out = []
    for x in raw:
        for y in (N(str(x)).split() if tags else [N(str(x))]):
            y = y.strip().lstrip("#") if tags else y.strip()
            if y and y not in out:
                out.append(y)
    return out


def _first_h1(body):
    fence = None
    for line in body.split("\n"):
        f = _FENCE.match(line)
        if fence:
            fence = None if f and f.group(1) == fence else fence
            continue
        if f:
            fence = f.group(1)
            continue
        m = _HEADING.match(line)
        if m and len(m.group(1)) == 1:
            return N(m.group(2).strip())
    return ""


def _date(v):
    m = _DATE.match(_text(v))
    if not m:
        return None
    return m.group(1) + ("T" + m.group(2) if m.group(2) else "")


def name_key(text):
    """A note's name as two notes are compared by it: the file name of a link target or a path (no folder, no `.md`,
    no `#heading`, no `|alias`), NFC, spaces collapsed, case folded."""
    s = N(text or "").strip()
    if s.startswith("[[") and s.endswith("]]"):
        s = s[2:-2]
    s = s.split("|", 1)[0].split("#", 1)[0].replace("\\", "/").rsplit("/", 1)[-1]
    if s.lower().endswith(".md"):
        s = s[:-3]
    return re.sub(r"\s+", " ", s).strip().casefold()


def version_key(title, folder):
    """The key two versions of one note share — only for a title that carries a version, draft or revision mark (`v3`,
    `draft`, `драфт №2`, `rev5`, `ревізія 5`): the title without the marks and the dates, compressed, plus the folder.
    A title without a mark is None: a series that differs only by date (weekly meetings) is no set of versions."""
    t = N(title or "")
    if not _MARK.search(t):
        return None
    t = re.sub(r"[\W_]+", " ", _DATES.sub(" ", _MARK.sub(" ", t)).casefold()).strip()
    return "%s/%s" % (_slash(N(folder or "")).strip("/"), t) if t else None


def note_meta(rel, text, mtime=None):
    """The metadata of a note: title (frontmatter `title`, else the first `# `, else the file name), type and status
    (lower case), product, date (`updated` | `modified` | `snapshot` | `generated` | `date` | `created`, else `mtime`),
    ttl_date (the note's own date a class TTL counts from: `updated` | `snapshot` | `generated`, else ""),
    confluence_id (frontmatter,
    else `(<6+ digits>).md`), aliases, tags, sensitive, hub, version_key and links (name_key of every wiki-link target
    and of `core_page`). A frontmatter that is never closed or cannot be read gives no metadata — the note is text."""
    t = (text or "").replace("\r\n", "\n")
    fm, body = _frontmatter(t)
    fm = fm or {}
    rel = _slash(N(rel or ""))
    name = rel.rsplit("/", 1)[-1]
    title = _text(fm.get("title")) or _first_h1(body) or (name[:-3] if name.lower().endswith(".md") else name)
    date = next((d for d in (_date(fm.get(k)) for k in DATE_KEYS) if d), None)
    ttl_date = next((d for d in (_date(fm.get(k)) for k in TTL_DATE_KEYS) if d), "")
    if date is None and mtime is not None:
        date = datetime.datetime.fromtimestamp(mtime).isoformat(timespec="seconds")
    cid = _text(fm.get("confluence_id"))
    if not cid:
        m = _CID.search(name)
        cid = m.group(1) if m else ""
    ntype = _text(fm.get("type")).lower()
    links = []
    for target in _WIKI.findall(t) + [_text(fm.get("core_page"))]:
        k = name_key(target)
        if k and k not in links:
            links.append(k)
    return {
        "title": title, "type": ntype, "product": _text(fm.get("product")), "status": _text(fm.get("status")).lower(),
        "date": date or "", "ttl_date": ttl_date, "confluence_id": cid, "aliases": _items(fm.get("aliases") or fm.get("alias")),
        "tags": _items(fm.get("tags") or fm.get("tag"), tags=True),
        "sensitive": sensitive_of(fm) or one_on_one(rel, title),
        "hub": ntype in HUB_TYPES or _text(fm.get("search_hub")).lower() in TRUE or bool(HUB_TITLE.search(title)),
        "version_key": version_key(title, rel.rsplit("/", 1)[0] if "/" in rel else ""), "links": links,
    }


def _strings(v):
    """The texts of a frontmatter value: a text, the texts of a list, the texts of a map's values (one level)."""
    if isinstance(v, str):
        return [v]
    if isinstance(v, list):
        return [x for x in v if isinstance(x, str)]
    if isinstance(v, dict):
        return [x for vv in v.values() for x in _strings(vv) if not isinstance(vv, dict)]
    return []


def _one_link(v):
    """The target as written of a value that is exactly one wiki link — a text, or a list of one text — else None."""
    items = v if isinstance(v, list) else [v]
    if len(items) != 1 or not isinstance(items[0], str):
        return None
    s = N(items[0]).strip()
    m = _WIKI.fullmatch(s)
    return _link_parts(m.group(1))[0] or None if m else None


def _link_parts(inner):
    """(target, anchor, label) of the inside of a wiki link `target#anchor|label` (the target NFC, stripped)."""
    left, _, label = inner.partition("|")
    target, _, anchor = left.partition("#")
    return N(target).strip().rstrip("\\").strip(), anchor.strip().rstrip("\\"), label.strip()   # `[[x\\|y]]` in a table


_CARD_NAMES = {}


def card_field_names():
    """{kind: {card_norm name: slot id}} of the plugin's catalogue (ctx_slots.card_names_by_kind), read once; a catalogue
    that cannot be read keeps no field."""
    if "names" not in _CARD_NAMES:
        try:
            cat = sl.load_catalogue()
            _CARD_NAMES.update(names=sl.card_names_by_kind(cat), version=sl.card_names_version(cat),
                               kinds={k: (sl.card_slot_info(cat, k) or {}).get("kind") for k in sl._all_slots(cat)})
        except ValueError:                      # unreadable: no field is kept (NULL, read again once it reads) and
            _CARD_NAMES.update(names=None, version=0, kinds={})          # version 0, below any real one (review M4)
    return _CARD_NAMES["names"]


def slot_names_version():
    """The catalogue's card_names_version (meta `slot_names`, v3.19.0): when it grows, the cards are read once more —
    a number, never a hash, so two builds of different catalogues on one index do not read the vault again in turn."""
    card_field_names()
    return _CARD_NAMES.get("version", 1)


def _slot_fields(kind, fm, names):
    """{slot id: value} of a card's frontmatter fields a slot of its kind is named by (v3.19.0, plan C2): a list slot's
    texts (_strings), a value slot's first text; for each slot the first field in the catalogue's order of its names.
    Never a judgement field (STEP_P_FIELDS), never a map."""
    want = names.get(kind) or {}
    if not want:
        return {}
    judgement = {sl.card_norm(x) for x in STEP_P_FIELDS}
    order = {}
    for i, n in enumerate(want):
        order.setdefault(want[n], {})[n] = i
    found = {}
    for k, v in fm.items():
        if sl.card_norm(k) in judgement or isinstance(v, dict) or not _filled(v):     # `D-Type`, `One-On-One` too
            continue
        n = sl.card_norm(k)
        slot = want.get(n)
        if slot and (slot not in found or order[slot][n] < found[slot][0]):
            found[slot] = (order[slot][n], v)
    cat_kinds = _slot_kinds()
    out = {}
    for slot, (_, v) in found.items():
        texts = [N(str(x)).strip() for x in (v if isinstance(v, list) else [v]) if not isinstance(x, (dict, list))]
        texts = [t for t in texts if t]
        if slot == "person.email":                       # an address, as the identity keeps it (lower case)
            texts = [t.lower() for t in texts if _EMAIL.match(t.lower())]
        if not texts:
            continue
        out[slot] = texts if cat_kinds.get(slot) == "list" else texts[0]
    return out


def _slot_kinds():
    card_field_names()
    return _CARD_NAMES["kinds"]


def _prefixes(fm):
    """The Jira project prefixes of a team's or a mission's `…jira…` fields (v3.19.0, v3.18.0 minor M2): a value that is
    list of prefix-shaped tokens alone (`PROJ`, `PROJ, QQ`), the prefix of a key, a `/projects/X` link, the projects of
    `project = X` / `project in (X, Y)` (never those `!=` or `not in` leave out) — never a JQL word."""
    out = set()
    for k, v in fm.items():
        if "jira" not in k.lower():
            continue
        for s_ in _strings(v):
            t = N(s_).strip()
            if _PREFIX_LIST.fullmatch(t):                # `PROJ`, `PROJ, QQ`, `PROJ QQ`
                out.update(_PREFIX.findall(t))
            lead = _LEAD_PREFIX.match(t)                 # `PROJ board`, `PROJ (payments)` — its first token
            if lead:
                out.add(lead.group(1))
            out.update(m.group(1) for m in ISSUE_KEY.finditer(t))
            out.update(_PROJECTS_URL.findall(t))         # …/projects/PROJ/board
            for m in _PROJECT.finditer(t):
                out.update(_PREFIX.findall(m.group(1)))
    return sorted(x for x in out if x not in JQL_WORDS)


def _work_key(rel, fm, title):
    """A work card's Jira key (v3.19.0, v3.18.0 minor M7): its own key field (WORK_KEY_FIELDS), else the key of its file
    name when the name holds exactly one, else — only when the name holds none — the one key of its title. A name or a
    title of two keys («GPT-4 rollout PROJ-77») gives none."""
    for k, v in fm.items():
        if sl.card_norm(k) in WORK_KEY_FIELDS:
            for s_ in _strings(v):
                m = ISSUE_KEY.search(N(s_))
                if m:
                    return m.group(0)
    name = rel.rsplit("/", 1)[-1]
    for text in (name[:-3] if name.lower().endswith(".md") else name, title or ""):
        keys = {m.group(0) for m in ISSUE_KEY.finditer(N(text))}
        if len(keys) == 1:
            return keys.pop()
        if keys:
            return ""
    return ""


def identity_of(rel, fm, title, names=None):
    """The identity of a card (v3.18.0, plan C1–C2) — {kind, label, emails, team, role, slug, aliases, key, bridges,
    prefixes, fields} — or None for a note that is no card. Only these fields: never a profile's judgement or any other field.
    `emails`: the e-mail-shaped texts of the card's own address fields (EMAIL_FIELDS), lower case; `role`: `role`, else
    `position`; `key`: a work card's Jira key (_work_key); `bridges`: {field: target} of every field that
    is exactly one wiki link, a judgement field (STEP_P_FIELDS) never; `prefixes`: the Jira project prefixes a team's or a
    mission's `…jira…` fields name (_prefixes); `fields` (since v3.19.0): {slot id: value} of the fields a slot of the
    card's kind is named by (`names`: card_field_names() by default)."""
    fm = fm if isinstance(fm, dict) else {}
    types = [x.lower() for x in _strings(fm.get("type"))]
    kind = next((ENTITY_KINDS[x.strip()] for x in types if x.strip() in ENTITY_KINDS), None)
    if kind is None:
        return None
    emails = []
    for k, v in fm.items():
        if re.sub(r"[\W_]", "", k) in EMAIL_FIELDS:
            for s in _strings(v):
                s = N(s).strip().lower()
                if _EMAIL.match(s) and s not in emails:
                    emails.append(s)
    key = _work_key(rel, fm, title) if kind == "work" else ""
    bridges = {}
    for k, v in fm.items():
        target = _one_link(v) if k not in STEP_P_FIELDS else None    # a judgement field is never identity (C9)
        if target:
            bridges[k] = target
    prefixes = _prefixes(fm) if kind in ("team", "mission") else []
    return {"kind": kind, "label": N(title or "").strip(), "emails": emails, "team": _text(fm.get("team")),
            "role": _text(fm.get("role")) or _text(fm.get("position")), "slug": _text(fm.get("slug")),
            "aliases": _items(fm.get("aliases") or fm.get("alias")), "key": key, "bridges": bridges,
            "prefixes": prefixes, "fields": None if (names is None and card_field_names() is None)
            else _slot_fields(kind, fm, card_field_names() if names is None else names)}


_EMBED_WIKI = re.compile(r"(!?)\[\[([^\]\n]+?)\]\]")
_CODE_SPAN = re.compile(r"(?<!`)(`+)(?!`)(?:(?!\n[ \t]*\n).)*?(?<!`)\1(?!`)", re.S)   # one line break inside, not two
_OPEN_FENCE = re.compile(r"^[ \t]{0,3}(`{3,}|~{3,})(.*)$")
_QUOTE = re.compile(r"^[ \t]{0,3}(?:>[ \t]?)+")


def without_code(text):
    """The text without its fenced blocks (``` or ~~~, their lines blanked) and its inline code spans — where a link or a
    key is an example, not a link or a mention (v3.19.0, v3.18.0 minor M6). Lines keep their places."""
    out, fence = [], None
    for line in (text or "").split("\n"):
        bare = _QUOTE.sub("", line)                     # a fence in a callout or a quote too
        m = _OPEN_FENCE.match(bare)
        if fence:
            if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence) and not m.group(2).strip():
                fence = None                            # closed by the same sign, as long or longer, with no info string
            out.append("")
            continue
        if m and not (m.group(1)[0] == "`" and "`" in m.group(2)):
            fence = m.group(1)
            out.append("")
            continue
        out.append(line)
    return _CODE_SPAN.sub(lambda m: " " * len(m.group(0)), "\n".join(out))


def links_of(fm, body):
    """Every wiki link of a note as written (v3.18.0): {field ("" for the text), target, tkey (its name_key), anchor,
    label, embed}, once per field and target (the first one's anchor and label), the frontmatter's fields first."""
    out, seen = [], set()

    def add(field, text):
        for m in _EMBED_WIKI.finditer(text or ""):
            target, anchor, label = _link_parts(m.group(2))
            if not target or (field, target) in seen:
                continue
            seen.add((field, target))
            out.append({"field": field, "target": target, "tkey": name_key(target), "anchor": anchor, "label": label,
                        "embed": bool(m.group(1))})

    for k, v in (fm or {}).items():
        for s in _strings(v):
            add(k, s)
    add("", without_code(body))
    return out


def mentions_of(text):
    """[(key, browse)] of every Jira-key-shaped token of a text, once each, sorted; `browse` when a `/browse/<key>`
    link names it. Which prefixes count is decided when the rows are read (plan C6)."""
    t = without_code(text or "")
    browse = set(BROWSE_KEY.findall(t))
    keys = {m.group(0) for m in ISSUE_KEY.finditer(t)} | browse
    return [(k, k in browse) for k in sorted(keys)]


def entity_rows(rel, text, title):
    """(identity or None, links, mentions) of a note's text — what the walk writes beside its row (v3.18.0)."""
    fm, body = _frontmatter((text or "").replace("\r\n", "\n"))
    return identity_of(rel, fm or {}, title), links_of(fm or {}, body if fm is not None else text), mentions_of(text)


def is_dataless(path):
    """Is the file's data not on disk (iCloud evicted it: `SF_DATALESS` in st_flags)? False where there are no flags."""
    try:
        flags = getattr(os.stat(path), "st_flags", 0)
    except OSError:
        return False
    return bool(flags & SF_DATALESS)


# ------------------------------------------------------------------ bringing evicted files down (`rebuild --download`)
_children, _children_lock = set(), threading.Lock()     # the reads running now: a stopped download kills them


def _fetch(path, timeout):
    """Read the first byte of `path` in a child process — macOS brings a file iCloud evicted down when it is read —
    within `timeout` seconds: "ok", "timeout" (the child killed: a read in this process could not be stopped) or
    "failed" (it could not be read). The child stops itself (SIGALRM) a few seconds after `timeout` should this process
    go first; while it runs it is in `_children`, so that a stopped download kills it."""
    try:
        p = subprocess.Popen([sys.executable, "-I", "-c", _READ_ONE, path, str(int(timeout) + 5)],
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        return "failed"
    with _children_lock:
        _children.add(p)
    try:
        try:
            rc = p.wait(timeout)
        except subprocess.TimeoutExpired:
            p.kill()
            p.wait()
            return "timeout"
        return "ok" if rc == 0 else "failed"
    finally:
        with _children_lock:
            _children.discard(p)


def evicted(roots, store_rel, blocks_rels):
    """The files of the plugin folders (the roots `own`) iCloud has not downloaded that the index would read: as the
    walk takes them (`_skip_folder`, `excluded`, MAX_BYTES at most) — no symbolic link followed (it could lead out of
    the plugin folder), no folder another root walks (a core inside the plugin folder, a nested plugin root: that one
    on its own turn), each file once. Only stat calls; sorted."""
    vaults = []
    for r in roots:
        if r.get("vault") and r["vault"] not in vaults:
            vaults.append(r["vault"])
    every = {N(os.path.normpath(r["path"])) for r in roots}
    store = _slash(N(store_rel or "")).rstrip("/")
    blocks = [_slash(N(b)) for b in blocks_rels or ()]
    out = set()
    for r in roots:
        if r.get("source") != "own":
            continue
        top = os.path.normpath(r["path"])
        stack = [(top, rel_path(top, vaults, r))]
        while stack:
            path, rel = stack.pop()
            try:
                with os.scandir(path) as it:
                    entries = list(it)
            except OSError:
                continue
            for e in entries:
                child = rel + "/" + N(e.name) if rel else N(e.name)
                try:
                    if e.is_dir(follow_symlinks=False):
                        if not _skip_folder(child, store) and not _copy_service(e.path) and N(os.path.normpath(e.path)) not in every:
                            stack.append((e.path, child))
                    elif (e.is_file(follow_symlinks=False) and not excluded(child, store, blocks)
                          and e.stat(follow_symlinks=False).st_size <= MAX_BYTES and is_dataless(e.path)):
                        out.add(e.path)
                except OSError:
                    continue
    return sorted(out)


def download(roots, store_rel, blocks_rels, fetch=None, workers=DOWNLOAD_WORKERS, per_file=DOWNLOAD_S, progress=None):
    """Bring down from iCloud the files `evicted` names (`ctx index rebuild --download`): each read by `fetch`
    (`_fetch`: a child process, `per_file` seconds at most), `workers` at once; a file still not on disk after its
    read is left — timed out, failed, or neither (iCloud did not give it). `progress(done, total)` after every file.
    Ctrl-C (SIGINT, from before the scan; the old handler back after) stops it: no new read begins, the running ones
    are killed, what came down stays and is counted — a handler that only marks a flag: no KeyboardInterrupt raised
    inside a lock, and no lock taken by the handler (one the main thread may hold right then). Returns {candidates,
    downloaded, left, timed_out, failed, interrupted}. Writes nothing."""
    fetch = fetch or _fetch
    stop = [False]                              # set by the handler; read by the workers and the loop
    res = {"candidates": 0, "downloaded": 0, "left": 0, "timed_out": 0, "failed": 0, "interrupted": False}
    old = None
    if threading.current_thread() is threading.main_thread():
        old = signal.signal(signal.SIGINT, lambda *_: stop.__setitem__(0, True))
    try:
        files = evicted(roots, store_rel, blocks_rels)
        res["candidates"] = len(files)
        queue, done, lock = list(reversed(files)), [], threading.Lock()

        def work():
            while not stop[0]:
                with lock:
                    if not queue:
                        return
                    path = queue.pop()
                try:
                    got = fetch(path, per_file)
                except Exception:  # noqa: BLE001 — a read that broke is one more file left
                    got = "failed"
                with lock:
                    done.append((path, got))

        threads = [threading.Thread(target=work, daemon=True) for _ in range(min(max(1, int(workers)), len(files)))]
        for t in threads:
            t.start()
        seen = 0
        while not stop[0]:
            alive = any(t.is_alive() for t in threads)
            with lock:
                batch, done[:] = list(done), []
            for path, got in batch:
                if not is_dataless(path):
                    res["downloaded"] += 1
                else:
                    res["left"] += 1
                    res["timed_out"] += got == "timeout"
                    res["failed"] += got not in ("ok", "timeout")
                seen += 1
                if progress:
                    progress(seen, len(files))
            if not alive:
                break
            time.sleep(0.1)
        if stop[0]:
            res["interrupted"] = True
            with _children_lock:
                running = list(_children)
            for p in running:
                try:
                    p.kill()
                except OSError:
                    pass
            res["downloaded"] = sum(1 for p in files if not is_dataless(p))
            res["left"] = len(files) - res["downloaded"]
    finally:
        if old is not None:
            signal.signal(signal.SIGINT, old)
    return res


# ------------------------------------------------------------------ the index
def _now():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def _busy(error):
    """Is this SQLite error a database another connection holds (locked, busy) — a live writer, never a broken file?"""
    text = str(error).lower()
    return "locked" in text or "busy" in text


def _count(v):
    return v if isinstance(v, int) and not isinstance(v, bool) and v > 0 else 0


def _note_dict(r):
    d = {c: r[c] for c in NOTE_COLS}
    for c in ("aliases", "tags", "links"):
        try:
            d[c] = json.loads(d.pop(c + "_json") or "[]")
        except ValueError:
            d[c] = []
    d["sensitive"] = bool(d["sensitive"]) or (d.get("type") or "").lower() in PEOPLE_TYPES \
        or one_on_one(d.get("path"), d.get("title"))
    d["hub"] = bool(d["hub"])
    return d


class Index:
    """The section index of `<home>/.grow-pm/index/`."""

    def __init__(self, home):
        self.home = home or os.path.expanduser("~")
        self.dir = index_dir(self.home)
        self.db_path = os.path.join(self.dir, DB_NAME)
        self.state_path = os.path.join(self.dir, STATE_NAME)
        self.lock_path = os.path.join(self.dir, LOCK_NAME)
        self.problem = None              # what the last read could not do, as a line for the caller to print
        self.busy_once = False           # v3.20.0: once a read finds the index busy, the next ones of this run give up
        self.busy = False                #   at once (`ctx entity`, apply: no wait of OPEN_S per read, ~26 s in all)

    # -------------------------------------------------- state and lock
    def _state(self):
        try:
            with open(self.state_path, encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def _save_state(self, data):
        tmp = self.state_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        os.replace(tmp, self.state_path)

    def _holder(self):
        """(at, pid) of index.lock as its holder wrote them; (the file's mtime, None) when it cannot be read."""
        try:
            with open(self.lock_path, encoding="utf-8") as f:
                held = json.load(f)
            return float(held.get("at") or 0), held.get("pid")
        except (OSError, ValueError, TypeError, AttributeError):
            return self._lock_mtime(), None

    def lock_held(self):
        """Does a live process hold index.lock, younger than LOCK_STALE_S — a refresh or a build going on now?"""
        if not os.path.exists(self.lock_path):
            return False
        at, pid = self._holder()
        return time.time() - at < LOCK_STALE_S and (pid is None or _alive(pid))

    def _take_lock(self):
        """Take index.lock; False while another live process holds one younger than LOCK_STALE_S."""
        for attempt in (1, 2):
            try:
                fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
            except FileExistsError:
                at, pid = self._holder()
                if attempt == 2 or (time.time() - at < LOCK_STALE_S and (pid is None or _alive(pid))):
                    return False
                try:
                    os.remove(self.lock_path)
                except OSError:
                    pass
                continue
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump({"pid": os.getpid(), "at": time.time()}, f)
            return True
        return False

    def _lock_mtime(self):
        try:
            return os.stat(self.lock_path).st_mtime
        except OSError:
            return 0.0

    def _drop_lock(self):
        try:
            os.remove(self.lock_path)
        except OSError:
            pass

    # -------------------------------------------------- the database
    def _set_aside(self, broken):
        """Move sections.sqlite out of the way: to sections.sqlite.broken, or away for good (a rebuild)."""
        for extra in ("-journal", "-wal", "-shm"):
            try:
                os.remove(self.db_path + extra)
            except OSError:
                pass
        if os.path.exists(self.db_path):
            if broken:
                os.replace(self.db_path, self.db_path + ".broken")
            else:
                os.remove(self.db_path)

    def _open_rw(self):
        """(connection, rebuilt): the index, or a new one after a broken or older one was put aside."""
        if os.path.exists(self.db_path):
            con = None
            try:
                con = sqlite3.connect(self.db_path, timeout=5)
                row = con.execute("SELECT value FROM meta WHERE key='schema'").fetchone()
                con.execute("SELECT count(*) FROM notes").fetchone()
                con.execute("SELECT count(*) FROM sections").fetchone()
                con.execute("SELECT rowid FROM sections_fts LIMIT 1").fetchone()
                cols = {r[1] for r in con.execute("PRAGMA table_info(notes)").fetchall()}
                if row and row[0] == SCHEMA and set(NOTE_COLS) <= cols:    # a column short (an earlier build): rebuilt
                    con.executescript(ENTITY_DDL)       # an earlier build's file gets the tables in place (v3.18.0)
                    con.executescript(GRAPH_DDL)        # and those of the graph (v4.0.0)
                    if "fields_json" not in {r[1] for r in con.execute("PRAGMA table_info(ents)").fetchall()}:
                        con.execute("ALTER TABLE ents ADD COLUMN fields_json TEXT")   # v3.19.0, in place
                        con.commit()
                    return con, False
            except sqlite3.DatabaseError as e:
                if _busy(e):
                    if con is not None:
                        con.close()
                    raise
            if con is not None:
                con.close()
            self._set_aside(broken=True)
            return self._create(), True
        return self._create(), False

    def _create(self):
        con = sqlite3.connect(self.db_path, timeout=5)
        con.executescript(DDL + ENTITY_DDL + GRAPH_DDL)
        con.execute("INSERT INTO meta(key, value) VALUES ('schema', ?)", (SCHEMA,))
        con.execute("INSERT INTO meta(key, value) VALUES ('near_version', ?)", (str(NEAR_VERSION),))
        con.execute("INSERT INTO meta(key, value) VALUES ('meta_version', ?)", (str(META_VERSION),))
        con.execute("INSERT INTO meta(key, value) VALUES ('slot_names', ?)", (str(slot_names_version()),))
        con.commit()
        return con

    @staticmethod
    def _near_again(con):
        """The near keys of an index whose `near_version` is lower than NEAR_VERSION (or none), again from its own
        sections — no file read, the schema unchanged — then the version; a later build's keys are left alone."""
        row = con.execute("SELECT value FROM meta WHERE key='near_version'").fetchone()
        try:
            stored = int(row[0]) if row else 0
        except (TypeError, ValueError):
            stored = 0
        if stored >= NEAR_VERSION:                  # this build's rules, or a later build's: left as they are
            return
        for nid, in con.execute("SELECT id FROM notes").fetchall():
            secs = con.execute("SELECT heading, text FROM sections WHERE note_id = ? ORDER BY ord", (nid,)).fetchall()
            con.execute("UPDATE notes SET near = ? WHERE id = ?", (near_key([(h or "", t or "") for h, t in secs]), nid))
        con.execute("INSERT OR REPLACE INTO meta(key, value) VALUES ('near_version', ?)", (str(NEAR_VERSION),))
        con.commit()

    @staticmethod
    def _meta_stale(con):
        """Is the index's `meta_version` lower than META_VERSION (none: 1)? Then its walk reads every downloaded file
        once more; a later build's rows are left alone."""
        row = con.execute("SELECT value FROM meta WHERE key='meta_version'").fetchone()
        try:
            stored = int(row[0]) if row else 1
        except (TypeError, ValueError):
            stored = 1
        return stored < META_VERSION

    @staticmethod
    def _names_again(con):
        """The cards of an index whose slot fields were kept by an older card_names_version (meta `slot_names`, none: 0)
        are marked unread (`fields_json` NULL) — the walk reads those files alone again — then the version; a later
        catalogue's fields are left alone, so two builds never read the cards again and again in turn (v3.19.0). The
        version is written before the walk: an older build that refreshes first fills those rows by its own names, and
        this build does not read them again until they change — a trade for never looping (review M5)."""
        row = con.execute("SELECT value FROM meta WHERE key='slot_names'").fetchone()
        try:
            stored = int(row[0]) if row else 0
        except (TypeError, ValueError):
            stored = 0
        if stored >= slot_names_version():
            return
        con.execute("UPDATE ents SET fields_json = NULL WHERE kind != ''")
        con.execute("INSERT OR REPLACE INTO meta(key, value) VALUES ('slot_names', ?)", (str(slot_names_version()),))
        con.commit()

    def _ro(self):
        """A read-only connection, or None when there is no index yet."""
        if not os.path.isfile(self.db_path):
            return None
        con = sqlite3.connect("file:%s?mode=ro" % urllib.parse.quote(self.db_path), uri=True, timeout=5)
        con.row_factory = sqlite3.Row
        return con

    def probe(self, timeout=0.5):
        """Can the index be read now — one row of its meta within `timeout` seconds (v3.20.0)? False when another
        connection holds it: `busy` and `problem` say so; True otherwise (no index, or a damaged one, is no busy one)."""
        if not os.path.isfile(self.db_path):
            return True
        try:
            con = sqlite3.connect("file:%s?mode=ro" % urllib.parse.quote(self.db_path), uri=True, timeout=timeout)
            try:
                con.execute("SELECT 1 FROM meta LIMIT 1").fetchone()
            finally:
                con.close()
        except sqlite3.DatabaseError as e:
            if _busy(e):
                self.busy, self.problem = True, BUSY_NOTE
                return False
        return True

    # -------------------------------------------------- refresh
    def refresh(self, roots, store_rel, blocks_rels, budget=REFRESH_S):
        """Bring the index up to date within `budget` seconds (None: no limit). Returns {added, changed, removed,
        pending (files not reached), skipped_dataless, skipped_large, locked, rebuilt}."""
        return self._update(roots, store_rel, blocks_rels, budget, fresh=False)

    def rebuild(self, roots, store_rel, blocks_rels, budget=None):
        """The index built again from nothing (by default with no time limit); the same result as `refresh`."""
        return self._update(roots, store_rel, blocks_rels, budget, fresh=True)

    def _update(self, roots, store_rel, blocks_rels, budget, fresh):
        res = {"added": 0, "changed": 0, "removed": 0, "pending": 0, "skipped_dataless": 0, "skipped_large": 0,
               "locked": False, "rebuilt": False}
        deadline = None if budget is None else _clock() + max(0.0, float(budget))
        for p in (self.dir, self.db_path, self.db_path + ".broken", self.state_path, self.state_path + ".tmp",
                  self.lock_path):
            cs.check_target(p)
        os.makedirs(self.dir, exist_ok=True)
        if not self._take_lock():
            res["locked"] = True
            res["pending"] = _count(self._state().get("pending"))
            return res
        try:
            if fresh:
                self._set_aside(broken=False)
            con, rebuilt = self._open_rw()
            res["rebuilt"] = rebuilt or fresh
            stale = False
            try:
                self._near_again(con)
                self._names_again(con)
                stale = self._meta_stale(con)
                state = {} if res["rebuilt"] else self._state()
                saved = state.get("queue") if not stale or state.get("reread") == META_VERSION else None
                files, sections, queue, when = self._walk(con, roots, store_rel, blocks_rels, deadline, res, saved,
                                                          reread=stale)   # an older build's queue: a new walk
            except sqlite3.DatabaseError as e:      # damage the open checks did not see: put it aside, walk once more
                con.close()
                if _busy(e):
                    raise
                self._set_aside(broken=True)
                res.update({k: 0 for k in COUNTS}, rebuilt=True)
                con = self._create()
                stale = False
                files, sections, queue, when = self._walk(con, roots, store_rel, blocks_rels, deadline, res, None)
            finally:
                con.close()
            self._save_state({"schema": SCHEMA, "updated": when, "files": files, "sections": sections,
                              "skipped_dataless": res["skipped_dataless"], "pending": res["pending"], "queue": queue,
                              "reread": META_VERSION if stale else None})
        finally:
            self._drop_lock()
        return res

    @staticmethod
    def _walk(con, roots, store_rel, blocks_rels, deadline, res, saved, reread=False):
        """One walk into `con`, then the day and the counts: (files, sections, queue, when). `reread`: every downloaded
        file is read again for its metadata (META_VERSION); the version is written once a walk ends with nothing left."""
        walk = _Walk(con, roots, store_rel, blocks_rels, deadline, res, reread=reread)
        queue = walk.run(saved)
        con.commit()
        import ctx_graph as cg                       # v4.0.0: the links resolved (imported here: it imports this one)
        try:
            cg.build(con, [r["rel"] for r in walk.roots if r["source"] == "own"], walk.touched, walk.name_keys)
        except Exception:  # noqa: BLE001 — the graph is a cache of the section index: its fault never costs the index
            con.rollback()                           # (review I-6); the next refresh builds the graph again
            try:
                con.execute("DELETE FROM meta WHERE key = 'graph_version'")
                con.commit()
            except sqlite3.DatabaseError:
                pass
        if reread and not res["pending"]:
            con.execute("INSERT OR REPLACE INTO meta(key, value) VALUES ('meta_version', ?)", (str(META_VERSION),))
        when = _now()
        con.execute("INSERT OR REPLACE INTO meta(key, value) VALUES ('updated', ?)", (when,))
        con.commit()
        files = con.execute("SELECT count(*) FROM notes").fetchone()[0]
        sections = con.execute("SELECT count(*) FROM sections").fetchone()[0]
        return files, sections, queue, when

    # -------------------------------------------------- reading
    def _read(self, fn, empty):
        """fn(read-only connection), or `empty` when there is no index yet or SQLite cannot read it — then `problem`
        says why, as a line the caller prints (a damaged file: `ctx index rebuild` — an FTS5 error that names a
        corruption, a malformed page or a missing row is one too; a busy one; an expression FTS5 did not take).
        `problem` is None after a read that worked."""
        self.problem = None
        if self.busy_once and self.busy:
            self.problem = BUSY_NOTE
            return empty
        try:
            con = self._ro()
            if con is None:
                return empty
            try:
                return fn(con)
            finally:
                con.close()
        except sqlite3.DatabaseError as e:
            if _busy(e):
                self.problem = BUSY_NOTE
                self.busy = True
            elif "fts5" in str(e).lower() and not any(w in str(e).lower() for w in DAMAGE_WORDS):
                self.problem = QUERY_NOTE % e
            else:
                self.problem = BROKEN_NOTE % e
            return empty

    def query(self, expr, limit, held=()):
        """The sections an FTS5 expression matches, best first (bm25: title 10, heading 6, tags 4, aliases 4, body 1):
        dicts with the section's id, heading, ord and raw text, the note's metadata and `rank`. `held` — FTS5
        expressions of one term each: every section then carries `held`, how many of them it matches, counted by the
        index itself in the same read (never by reading the section's text). A blank expression or no index answer [];
        so does an index SQLite cannot read, and then `problem` says so."""
        if not (expr or "").strip():
            self.problem = None
            return []
        terms = [e for e in held or () if (e or "").strip()]

        def ask(con):
            rows = con.execute(QUERY_SQL, (expr, int(limit))).fetchall()
            ids, counts = [r["id"] for r in rows], {}
            if terms and ids:
                sql = "SELECT rowid FROM sections_fts WHERE sections_fts MATCH ? AND rowid IN (%s)" % ",".join("?" * len(ids))
                for e in terms:
                    for (sid,) in con.execute(sql, [e] + ids).fetchall():
                        counts[sid] = counts.get(sid, 0) + 1
            return rows, counts

        rows, counts = self._read(ask, ([], {}))
        out = [self._section_dict(r) for r in rows]
        if held:
            for d in out:
                d["held"] = counts.get(d["id"], 0)
        return out

    @staticmethod
    def _section_dict(r):
        d = _note_dict(r)
        d.update({"id": r["id"], "note_id": r["note_id"], "heading": r["heading"], "ord": r["ord"], "text": r["text"]})
        if "rank" in r.keys():
            d["rank"] = r["rank"]
        return d

    def section(self, sid):
        """One section with its note's metadata, or None (`problem` says why when the index cannot be read)."""
        try:
            sid = int(sid)
        except (ValueError, TypeError):
            return None
        r = self._read(lambda con: con.execute(ROW_SQL + " WHERE s.id = ?", (sid,)).fetchone(), None)
        return self._section_dict(r) if r else None

    def following(self, note_id, order, chars=None):
        """(heading, text) of the sections of a note after its section `order`, in the note's order — what `ctx search`
        adds to a short section, in a candidate's snippet and in `--get`. With `chars`, the rows stop once the text they
        gathered (their link-only lines aside, as the fill counts it) holds that many characters: a long page is never
        read whole for one candidate. `problem` as for `query`."""
        try:
            note_id, order = int(note_id), int(order)
        except (ValueError, TypeError):
            return []

        def read(con):
            out, size = [], 0
            for heading, text in con.execute("SELECT heading, text FROM sections WHERE note_id = ? AND ord > ? "
                                             "ORDER BY ord", (note_id, order)):
                if chars is not None and size >= chars:
                    break
                out.append((heading or "", text or ""))
                size += len(strip_links(text).strip())
            return out

        return self._read(read, [])

    def note(self, path):
        """(metadata, sections) of the note named `path` (an index name, compared in NFC): what Index.notes() says of it
        and its sections [(heading, text)] in the note's order; None when the index holds no such note — `ctx search
        --get <path>`. `problem` as for `query`."""
        def read(con):
            row = con.execute("SELECT id, %s FROM notes WHERE path = ?" % ", ".join(NOTE_COLS),
                              (N(path or ""),)).fetchone()
            if not row:
                return None
            secs = con.execute("SELECT heading, text FROM sections WHERE note_id = ? ORDER BY ord", (row["id"],))
            return dict(_note_dict(row), id=row["id"]), [(h or "", t or "") for h, t in secs]

        return self._read(read, None)

    def paths(self):
        """The path (NFC) of every note, sorted — what `ctx search --get <name>` looks through for a note's name;
        `problem` as for `query`."""
        rows = self._read(lambda con: con.execute("SELECT path FROM notes ORDER BY path").fetchall(), [])
        return sorted(N(r[0] or "") for r in rows)

    def headings(self):
        """(section id, path, heading) of every section — how `ctx search --get` finds a section by its id when the
        last search did not list it; `problem` as for `query`."""
        rows = self._read(lambda con: con.execute("SELECT s.id, n.path, s.heading FROM sections s "
                                                  "JOIN notes n ON n.id = s.note_id").fetchall(), [])
        return [(r[0], r[1], r[2] or "") for r in rows]

    def notes(self):
        """The metadata of every note, by path (id, path, source, title, type, product, status, date, ttl_date,
        confluence_id, aliases, tags, sensitive, hub, version_key, links, hash, near — `near_key` of its sections —,
        mtime, size); `problem` as for `query`."""
        rows = self._read(lambda con: con.execute("SELECT id, %s FROM notes ORDER BY path" % ", ".join(NOTE_COLS))
                          .fetchall(), [])
        return [dict(_note_dict(r), id=r["id"]) for r in rows]

    @staticmethod
    def _has_entities(con):
        """Does the index hold the tables of v3.18.0 (an earlier build's file has none until a walk of this one)?"""
        names = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        return set(ENTITY_TABLES) <= names

    _FRESH = "JOIN ents e ON e.note_id = n.id AND e.hash = n.hash AND e.path = n.path"   # an older build's row is stale

    def cards(self):
        """Every card the index holds (v3.18.0): the identity row of a note whose kind is not "" and whose hash is the
        note's, as identity_of gives it, with the note's id, path, source, title, type, date and sensitivity (as
        Index.notes() reads it). [] before a walk of this build; `problem` as for `query`."""
        def read(con):
            if not self._has_entities(con):
                return []
            have = {r[1] for r in con.execute("PRAGMA table_info(ents)").fetchall()}   # v3.18.0's: no fields_json yet
            return con.execute("SELECT n.id, %s, %s FROM notes n %s WHERE e.kind != '' ORDER BY n.path"
                               % (", ".join("n." + c for c in NOTE_COLS),
                                  ", ".join(("e." + c) if c in have else ("NULL AS " + c) for c in ENTITY_COLS),
                                  self._FRESH)).fetchall()

        out = []
        for r in self._read(read, []):
            d = dict(_note_dict(r), id=r["id"])
            for c in ENTITY_COLS:
                v = r[c]
                if c.endswith("_json"):
                    try:
                        v = json.loads(v or "null")
                    except ValueError:
                        v = None
                    d[c[:-5]] = v if v is not None or c == "fields_json" else ({} if c == "bridges_json" else [])
                                                 # fields None: a row whose slot fields no walk of v3.19.0 read yet
                else:
                    d[c] = v or ""
            out.append(d)
        return out

    def identity_paths(self):
        """The paths of the notes whose identity row is fresh — card or not (v3.18.0): a note the index holds whose
        identity it has not read yet (iCloud evicted it before a walk of this build) is not among them, so a local
        index may give its card meanwhile. `problem` as for `query`."""
        def read(con):
            if not self._has_entities(con):
                return []
            return con.execute("SELECT n.path FROM notes n %s" % self._FRESH).fetchall()

        return {N(r[0] or "") for r in self._read(read, [])}

    def _with_note(self, sql, args):
        def read(con):
            if not self._has_entities(con):
                return []
            return con.execute(sql, args).fetchall()

        out = []
        for r in self._read(read, []):
            d = {k: r[k] for k in r.keys()}
            d["sensitive"] = bool(d["sensitive"]) or (d.get("type") or "").lower() in PEOPLE_TYPES \
                or one_on_one(d.get("path"), d.get("title"))
            out.append(d)
        return out

    def links_to(self, tkeys):
        """The links whose target's name key is one of `tkeys` (v3.18.0): {field, target, tkey, anchor, label, embed}
        with the note that holds them — its path, source, title, type, date, sensitivity. `problem` as for `query`."""
        keys = sorted({k for k in tkeys or () if k})
        if not keys:
            return []
        return self._with_note("SELECT l.field, l.target, l.tkey, l.anchor, l.label, l.embed, n.path, n.source, n.title, "
                               "n.type, n.date, n.sensitive FROM links l JOIN notes n ON n.id = l.note_id %s "
                               "WHERE l.tkey IN (%s) ORDER BY n.path" % (self._FRESH, ",".join("?" * len(keys))), keys)

    def field_links(self, field, source=None):
        """{path, target} of every link in the frontmatter field `field` (any case), of the notes of `source` only when
        given (v3.20.0: the notes of your layer that already hold `same_as`). `problem` as for `query`."""
        where, args = "WHERE lower(l.field) = ?", [str(field).lower()]
        if source is not None:
            where += " AND n.source = ?"
            args.append(source)
        rows = self._with_note("SELECT DISTINCT n.path, l.target, n.source, n.title, n.type, n.date, n.sensitive FROM links l "
                               "JOIN notes n ON n.id = l.note_id %s %s ORDER BY n.path" % (self._FRESH, where), args)
        return [{"path": N(r["path"]), "target": N(r["target"] or "")} for r in rows]

    def mentions(self, keys=None):
        """The Jira-key-shaped tokens of the notes (v3.18.0): {key, browse, path, source, title, type, date, sensitive};
        `keys` — those keys only, None — all. `problem` as for `query`."""
        if keys is not None:
            keys = sorted({k for k in keys if k})
            if not keys:
                return []
        where = "WHERE m.key IN (%s)" % ",".join("?" * len(keys)) if keys is not None else ""
        rows = self._with_note("SELECT m.key, m.browse, n.path, n.source, n.title, n.type, n.date, n.sensitive "
                               "FROM mentions m JOIN notes n ON n.id = m.note_id %s %s ORDER BY m.key, n.path"
                               % (self._FRESH, where), keys or [])
        for d in rows:
            d["browse"] = bool(d["browse"])
        return rows

    def built(self):
        """Has a walk ever finished into this index — the database there, with its meta `updated` row? False when there
        is no database yet, or while a first build (or a rebuild) is still filling one — it writes `updated` when its
        walk ends; None when SQLite cannot read it (`problem` says why: busy or damaged). Reads the meta row itself,
        never index.json."""
        done = self._read(lambda con: con.execute("SELECT 1 FROM meta WHERE key='updated'").fetchone() is not None, None)
        return False if done is None and self.problem is None else done

    def status(self):
        """{schema, updated, files, sections, pending, skipped_dataless}: schema, the day and the counts are the index's
        own (its meta and its tables; a database with no `updated` row — still being built — has no day); pending and
        skipped_dataless are the last walk's, from index.json. No index: schema and day None, zeros. Only a database
        SQLite cannot read now (`problem` says why) takes its day from index.json."""
        state = self._state()
        out = {"schema": None, "updated": None, "files": 0, "sections": 0,
               "pending": _count(state.get("pending")), "skipped_dataless": _count(state.get("skipped_dataless"))}

        def fill(con):
            row = con.execute("SELECT value FROM meta WHERE key='schema'").fetchone()
            out["schema"] = row[0] if row else None
            row = con.execute("SELECT value FROM meta WHERE key='updated'").fetchone()
            out["updated"] = row[0] if row else None
            out["files"] = con.execute("SELECT count(*) FROM notes").fetchone()[0]
            out["sections"] = con.execute("SELECT count(*) FROM sections").fetchone()[0]

        self._read(fill, None)
        if self.problem:
            out["updated"] = state.get("updated")
        return out


def _dotted(rel):
    """Does an index name lie under a dot-folder or name a dot-file (`.git/…`, `.DS_Store`)? Never a name (review I-3)."""
    return any(part.startswith(".") for part in rel.split("/"))


def _alive(pid):
    try:
        os.kill(int(pid), 0)
        return True
    except ProcessLookupError:
        return False
    except (PermissionError, OSError, ValueError, TypeError):
        return True


class _Walk:
    """One run of the refresh over the roots: folders listed one at a time, depth first, until the deadline."""

    def __init__(self, con, roots, store_rel, blocks_rels, deadline, res, reread=False):
        self.con, self.deadline, self.res, self.reread = con, deadline, res, reread
        vaults = []
        for r in roots:
            if r.get("vault") and r["vault"] not in vaults:
                vaults.append(r["vault"])
        self.roots = [dict(r, path=os.path.normpath(r["path"])) for r in roots]
        for r in self.roots:
            r["rel"] = rel_path(r["path"], vaults, r)
        self.root_paths = {N(r["path"]) for r in self.roots}
        self.by_rel = sorted(range(len(self.roots)), key=lambda i: -len(self.roots[i]["rel"]))
        self.store_rel = _slash(N(store_rel or "")).rstrip("/")
        self.blocks = [_slash(N(b)) for b in blocks_rels or ()]
        self.rows = {}
        for nid, path, mtime, size, digest, source in con.execute("SELECT id, path, mtime, size, hash, source FROM notes"):
            self.rows[path] = {"id": nid, "mtime": mtime, "size": size, "hash": digest, "source": source}
        self.names = {}                              # v4.0.0: every file a link may land on, evicted ones too
        for path, source, dataless, md in con.execute("SELECT path, source, dataless, md FROM names"):
            self.names[path] = {"source": source, "dataless": dataless, "md": md}
        self.name_keys = set()                       # the name keys of the names that came or went: the links that
        self.names_changed = False                   # name them are resolved again (ctx_graph)
        self.touched = set()                         # the notes read again: their links are resolved again
        self.children = collections.defaultdict(set)
        for path in list(self.rows) + list(self.names):
            self._know(path)
        self.writes = 0
        for tb in ENTITY_TABLES:                     # the rows of a note an older build removed (v3.18.0, plan C11)
            con.execute("DELETE FROM %s WHERE note_id NOT IN (SELECT id FROM notes)" % tb)
        self.stale_ents = {r[0] for r in con.execute(
            "SELECT n.id FROM notes n LEFT JOIN ents e ON e.note_id = n.id "
            "WHERE e.note_id IS NULL OR e.hash IS NOT n.hash OR e.path IS NOT n.path%s"
            % (" OR (e.fields_json IS NULL AND e.kind != '')" if slot_names_version() else ""))}
                                                     # a catalogue that cannot be read (version 0) keeps no field:
                                                     # its NULL is no reason to read the cards on every walk
                                                     # read again whatever their mtime: no identity row, or one an older
                                                     # build left behind when it changed the note (v3.18.0 wrote no
                                                     # slot fields: such a row is read again too, v3.19.0)

    def _outside(self, path):
        """Is this index name one of a root outside every vault (`@<its source>/…`)? A vault's own `@Name.md` is not."""
        row = self.rows.get(path) or self.names.get(path)
        return bool(row) and path.startswith("@%s/" % row["source"])

    def _know(self, path):
        """Remember every folder → name step of an index name, the vault's top level ("") too — but not for a name
        outside every vault: no vault's listing can miss it."""
        parts = path.split("/")
        for i in range(1 if self._outside(path) else 0, len(parts)):
            self.children["/".join(parts[:i])].add(parts[i])

    def _owner(self, path):
        """The root an index name belongs to: the one with the longest name that holds it (a vault walked whole holds
        every name but those outside every vault), or None."""
        for i in self.by_rel:
            rel = self.roots[i]["rel"]
            if (path == rel or path.startswith(rel + "/")) if rel else not self._outside(path):
                return i
        return None

    def _due(self):
        return self.deadline is not None and _clock() >= self.deadline

    # -------------------------------------------------- the walk
    def run(self, saved):
        """Walk: the saved queue of an unfinished walk when there is one, else a new walk from the roots — either way
        first dropping the rows no root owns now (a core folder gone from disk, a registration removed: since v3.16.2,
        never served as current). Returns the queue of what is left ([kind, root path, path, rel]); sets
        res["pending"]."""
        by_path = {r["path"]: i for i, r in enumerate(self.roots)}
        items = []
        for it in saved or []:
            if isinstance(it, list) and len(it) == 4 and it[0] in ("d", "f") and it[1] in by_path:
                items.append((it[0], by_path[it[1]], it[2], it[3]))
        self._drop_orphans()
        if not items:
            items = [("d", i, r["path"], r["rel"]) for i, r in enumerate(self.roots)]
        stack = list(reversed(items))
        while stack and not self._due():
            kind, ri, path, rel = stack.pop()
            if kind == "d":
                stack.extend(reversed(self._list(ri, path, rel)))
            else:
                self._file(ri, path, rel)
        self.con.commit()
        left = list(reversed(stack))
        self.res["pending"] = self._pending(left)
        return [[k, self.roots[ri]["path"], p, rel] for k, ri, p, rel in left]

    def _drop_orphans(self):
        """The rows no root owns, gone in one pass; then the folder → name steps the walk knows, again from the rows."""
        for path in [p for p in self.names if self._owner(p) is None]:
            self._forget(path)
        orphans = [p for p in self.rows if self._owner(p) is None]
        if not orphans:
            if self.names_changed:
                self.children = collections.defaultdict(set)
                for path in list(self.rows) + list(self.names):
                    self._know(path)
            return
        for path in orphans:
            nid = self.rows.pop(path)["id"]
            self._drop_sections(nid)
            self._drop_entities(nid)
            self.con.execute("DELETE FROM notes WHERE id=?", (nid,))
            self.res["removed"] += 1
        self.children = collections.defaultdict(set)
        for path in list(self.rows) + list(self.names):
            self._know(path)

    def _pending(self, left):
        """How many files the walk did not reach: the files left, and the files the index holds under each folder
        left (a folder it knows nothing under counts as one)."""
        paths = sorted(self.rows)
        names = set()
        for kind, _, _, rel in left:
            if kind == "f":
                names.add(rel)
                continue
            if rel:
                lo = bisect.bisect_left(paths, rel + "/")
                hi = bisect.bisect_left(paths, rel + "/\U0010ffff")
                under = paths[lo:hi]
            else:                                    # a root that is a vault itself: all its names but the outside ones
                under = [p for p in paths if not self._outside(p)]
            names.update(under or ["%s/" % rel])
        return len(names)

    def _list(self, ri, path, rel):
        """List one folder: its files, then its subfolders, in name order. The rows of names gone from it go."""
        try:
            with os.scandir(path) as it:
                entries = sorted(it, key=lambda e: N(e.name))
        except OSError:
            return []                                # a folder that cannot be listed: nothing under it goes
        files, dirs, present = [], [], set()
        for e in entries:
            name = N(e.name)
            child = rel + "/" + name if rel else name
            try:
                if e.is_dir(follow_symlinks=False):
                    if _skip_folder(child, self.store_rel) or _copy_service(e.path):
                        continue
                    present.add(name)
                    if N(os.path.normpath(e.path)) not in self.root_paths:   # another root walks it itself
                        dirs.append(("d", ri, e.path, child))
                elif e.is_file(follow_symlinks=False):      # a link to a file is not followed (v3.16.2)
                    present.add(name)
                    files.append(("f", ri, e.path, child))
            except OSError:
                present.add(name)                    # cannot tell what it is: keep what the index holds of it
        for name in sorted(self.children.get(rel, set()) - present):
            self._remove(rel + "/" + name if rel else name, owner=ri)
        return files + dirs

    def _file(self, ri, path, rel):
        try:
            info = os.stat(path, follow_symlinks=False)    # once for the note and its name (v4.0.0, review I-5)
        except OSError:
            info = None
        regular = info is not None and stat.S_ISREG(info.st_mode)
        md = rel.lower().endswith(".md")
        dataless = bool(regular and md and is_dataless(path))
        try:
            self._note(ri, path, rel, info, dataless)
        finally:
            if regular and not _skip_folder(rel, self.store_rel) and not _dotted(rel):
                self._name(ri, rel, dataless, md)
            elif rel in self.names:
                self._forget(rel)

    def _name(self, ri, rel, dataless, md):
        """The file's row in `names` (v4.0.0): a regular file — a note, evicted or not, or any other file but one under
        a dot-folder or a dot-file (`.git/…`) — is a name a link may land on; written only when it is new or its flags
        changed."""
        want = {"source": self.roots[ri]["source"], "dataless": int(dataless), "md": int(md)}
        have = self.names.get(rel)
        if have == want:
            return
        self.con.execute("INSERT OR REPLACE INTO names(path, source, dataless, md) VALUES (?, ?, ?, ?)",
                         (rel, want["source"], want["dataless"], want["md"]))
        self.names[rel] = want
        if have is None:
            self.names_changed = True
            self.name_keys.add(name_key(rel))
            self._know(rel)

    def _forget(self, rel):
        self.names.pop(rel, None)
        self.con.execute("DELETE FROM names WHERE path=?", (rel,))
        self.names_changed = True
        self.name_keys.add(name_key(rel))

    def _note(self, ri, path, rel, info, dataless):
        if excluded(rel, self.store_rel, self.blocks):
            if rel in self.rows:
                self._remove(rel)
            return
        if info is None:                                     # a link to a file is not followed, a queued one neither
            return
        if not stat.S_ISREG(info.st_mode):
            if rel in self.rows:                             # a queued link to a file: its earlier row goes
                self._remove(rel)
            return
        if dataless:
            self.res["skipped_dataless"] += 1
            row = self.rows.get(rel)
            if self.reread and row:                  # read once it comes down, its mtime as it was (v3.17.0)
                self.con.execute("UPDATE notes SET mtime=-1 WHERE id=?", (row["id"],))
                row["mtime"] = -1.0
            return
        if info.st_size > MAX_BYTES:
            self.res["skipped_large"] += 1
            if rel in self.rows:
                self._remove(rel)
            return
        row = self.rows.get(rel)
        if row and not self.reread and row["mtime"] == info.st_mtime and row["size"] == info.st_size \
                and row["id"] not in self.stale_ents:
            return
        try:
            with open(path, "rb") as f:
                data = f.read(MAX_BYTES + 1)
        except OSError:
            return
        digest = hashlib.sha1(data).hexdigest()
        if row and row["hash"] == digest:            # touched, not changed: the columns this build's rules of
            meta = note_meta(rel, data.decode("utf-8", errors="replace").replace("\r\n", "\n"), mtime=info.st_mtime)
            self.con.execute("UPDATE notes SET sensitive=?, mtime=?, size=? WHERE id=?",   # note_meta changed (v3.17.0)
                             (int(meta["sensitive"]), info.st_mtime, info.st_size, row["id"]))
            row.update(mtime=info.st_mtime, size=info.st_size)
            self._entities(row["id"], rel, data.decode("utf-8", errors="replace"), meta["title"], digest)   # v3.18.0
            return
        text = data.decode("utf-8", errors="replace").replace("\r\n", "\n")
        meta = note_meta(rel, text, mtime=info.st_mtime)
        nid = self._write(row, rel, self.roots[ri]["source"], meta, split_sections(text), digest, info)
        self._entities(nid, rel, text, meta["title"], digest)

    # -------------------------------------------------- rows
    def _write(self, row, rel, source, meta, sections, digest, info):
        con = self.con
        values = (rel, source, meta["title"], meta["type"], meta["product"], meta["status"], meta["date"],
                  meta["ttl_date"], meta["confluence_id"], json.dumps(meta["aliases"], ensure_ascii=False),
                  json.dumps(meta["tags"], ensure_ascii=False), int(meta["sensitive"]), int(meta["hub"]),
                  meta["version_key"], json.dumps(meta["links"], ensure_ascii=False), digest, near_key(sections),
                  info.st_mtime, info.st_size)
        if row:
            nid = row["id"]
            self._drop_sections(nid)
            con.execute("UPDATE notes SET %s WHERE id=?" % ", ".join(c + "=?" for c in NOTE_COLS), values + (nid,))
            self.res["changed"] += 1
        else:
            nid = con.execute("INSERT INTO notes(%s) VALUES (%s)" % (", ".join(NOTE_COLS), ", ".join("?" * len(NOTE_COLS))),
                              values).lastrowid
            self.res["added"] += 1
        self.rows[rel] = {"id": nid, "mtime": info.st_mtime, "size": info.st_size, "hash": digest, "source": source}
        self.touched.add(nid)
        if not row:
            self._know(rel)
        name = rel.rsplit("/", 1)[-1]
        name = name[:-3] if name.lower().endswith(".md") else name
        title = meta["title"] if name_key(name) == name_key(meta["title"]) else meta["title"] + " " + name
        title, tags, aliases = st.stem_text(title), st.stem_text(" ".join(meta["tags"])), st.stem_text(" ".join(meta["aliases"]))
        for order, (heading, body) in enumerate(sections):
            sid = con.execute("INSERT INTO sections(note_id, heading, ord, text) VALUES (?, ?, ?, ?)",
                              (nid, heading, order, body)).lastrowid
            con.execute("INSERT INTO sections_fts(rowid, title, heading, tags, aliases, body) VALUES (?, ?, ?, ?, ?, ?)",
                        (sid, title, st.stem_text(heading), tags, aliases, st.stem_text(body)))
        self.writes += 1
        if self.writes % COMMIT_EVERY == 0:
            con.commit()
        return nid

    def _entities(self, nid, rel, text, title, digest):
        """The identity row (kind "" for a note that is no card), the links and the mentions of a note, in place of
        what it had (v3.18.0)."""
        ident, links, mentions = entity_rows(rel, text, title)
        self._drop_entities(nid)
        ident = ident or {}
        self.con.execute("INSERT INTO ents(note_id, hash, path, %s) VALUES (?, ?, ?, %s)"
                         % (", ".join(ENTITY_COLS), ", ".join("?" * len(ENTITY_COLS))),
                         (nid, digest, rel, ident.get("kind", ""), ident.get("label", ""),
                          json.dumps(ident.get("emails", []), ensure_ascii=False), ident.get("team", ""),
                          ident.get("role", ""), ident.get("slug", ""),
                          json.dumps(ident.get("aliases", []), ensure_ascii=False), ident.get("key", ""),
                          json.dumps(ident.get("bridges", {}), ensure_ascii=False),
                          json.dumps(ident.get("prefixes", []), ensure_ascii=False),
                          None if ident and ident.get("fields") is None else json.dumps(ident.get("fields", {}), ensure_ascii=False)))
        self.con.executemany("INSERT INTO links(note_id, field, target, tkey, anchor, label, embed) VALUES (?, ?, ?, ?, ?, ?, ?)",
                             [(nid, l["field"], l["target"], l["tkey"], l["anchor"], l["label"], int(l["embed"]))
                              for l in links])
        self.con.executemany("INSERT INTO mentions(note_id, key, browse) VALUES (?, ?, ?)",
                             [(nid, k, int(b)) for k, b in mentions])
        self.stale_ents.discard(nid)
        self.touched.add(nid)

    def _drop_entities(self, nid):
        for tb in ENTITY_TABLES:
            self.con.execute("DELETE FROM %s WHERE note_id=?" % tb, (nid,))

    def _drop_sections(self, nid):
        self.con.execute("DELETE FROM sections_fts WHERE rowid IN (SELECT id FROM sections WHERE note_id=?)", (nid,))
        self.con.execute("DELETE FROM sections WHERE note_id=?", (nid,))

    def _remove(self, prefix, owner=None):
        """The rows of the file `prefix`, or of every file under the folder `prefix` — with `owner`, only those that root
        owns (a second vault walked by another root may hold the same names). The names the index knew under it are
        forgotten (a name left behind elsewhere only costs a removal that finds nothing)."""
        for path in [p for p in self.rows if (p == prefix or p.startswith(prefix + "/"))
                     and (owner is None or self._owner(p) == owner)]:
            nid = self.rows.pop(path)["id"]
            self._drop_sections(nid)
            self._drop_entities(nid)
            self.con.execute("DELETE FROM notes WHERE id=?", (nid,))
            self.res["removed"] += 1
        for path in [p for p in self.names if (p == prefix or p.startswith(prefix + "/"))
                     and (owner is None or self._owner(p) == owner)]:
            self._forget(path)
        if any(p == prefix or p.startswith(prefix + "/") for p in list(self.rows) + list(self.names)):
            return                                   # another root's rows by the same name: their names stay known
        parent, _, child = prefix.rpartition("/")
        self.children[parent].discard(child)
        for folder in [f for f in self.children if f == prefix or f.startswith(prefix + "/")]:
            del self.children[folder]
