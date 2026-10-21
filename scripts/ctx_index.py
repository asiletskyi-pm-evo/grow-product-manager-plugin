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

The refresh is incremental. It walks the roots as os.walk(followlinks=False) would, one folder at a time so that it can
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
HUB_TITLE = re.compile(r"style guide|глосарій|glossary|абревіатури", re.I)
TRUE = ("true", "yes", "1")
DATE_KEYS = ("updated", "modified", "snapshot", "generated", "date", "created")
TTL_DATE_KEYS = ("updated", "snapshot", "generated")   # the note's own date a class TTL is counted from (provider protocol §6)
COMMIT_EVERY = 50                   # files written between two commits of a refresh
STUB_CHARS = 200                    # a section shorter than this (its breadcrumb lines aside) is short: --get and its
                                    # snippet go on with the sections after it (ctx_search)
NEAR_MIN, NEAR_CHARS = 400, 20_000  # near copies: the characters a key needs at least, and the ones it reads
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


def _spellings(path):
    """The path as given (absolute, normalised, NFC) and, when it differs, with its links resolved (/tmp on macOS)."""
    a = N(os.path.normpath(os.path.abspath(os.path.expanduser(N(path)))))
    b = N(os.path.realpath(a))
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


def _skip_folder(rel, store_rel, fold=False):
    """A folder (or a file in it) the index never enters: the store, `_System/providers/`, `_System/_scratch/` (the
    plugin's scratch files — per-person digests among them), `.obsidian`, `.trash`, a name that starts with
    `_backup`. With `fold` the names are compared case-folded (`excluded`)."""
    low = str.casefold if fold else str
    if store_rel:
        s = low(_slash(N(store_rel)).rstrip("/"))
        if s and (low(rel) == s or low(rel).startswith(s + "/")):
            return True
    parts = [low(p) for p in rel.split("/")]
    for i, part in enumerate(parts):
        if part in (".obsidian", ".trash") or part.startswith("_backup"):
            return True
        if part == low("_System") and i + 1 < len(parts) and parts[i + 1] in ("providers", "_scratch"):
            return True
    return False


def excluded(rel, store_rel, blocks_rels, fold=False):
    """Is the file `rel` (an index name) left out: under the store, `_System/providers/` or `_System/_scratch/`, a
    blocks file of a registration, in a `.obsidian`, `.trash` or `_backup…` folder, not `.md`, or `local-context.md`
    itself. Every source's hits go through it, not only the walk — exactly, as the index names them; with `fold`
    the names are compared case-folded, for a path a user typed on a case-insensitive disk (`ctx search --get`)."""
    low = str.casefold if fold else str
    rel = _slash(N(rel or ""))
    if _skip_folder(rel, store_rel, fold) or low(rel) in {low(_slash(N(b))) for b in blocks_rels or ()}:
        return True
    name = rel.rsplit("/", 1)[-1]
    return not name.lower().endswith(".md") or low(name) == "local-context.md"


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
    with no value opened (`tags:` then `- a` at the margin is how PyYAML writes a list). A nested mapping is not read."""
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


def near_key(sections):
    """The key two near copies of a note share (`Knowledge/sources/x.md` and `Research/x.md`), from its sections
    (split_sections: no frontmatter): sha1 of the first NEAR_CHARS characters of their heading paths and text, without
    the trailing «Повʼязане» / «Зв'язки» / «Related» block (sections under such a heading at the end, or a label line of
    that name in the last one and what follows it), the breadcrumb and navigation link lines (`link_only` with a label:
    `Up:: [[MOC]]` — never `Owner: [[X]]`), the lines that are only a date or the day a note was updated or made
    (`2026-10-07`, `Оновлено: 07.10.2026` — never `Deadline: …`) and the whitespace. None when fewer than NEAR_MIN
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
        body = " ".join(" ".join(line for line in lines if not (link_only(line, label=True) or _DATE_LINE.match(line)))
                        .split())
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
    """A frontmatter value as one line of text ('' for nothing or a list)."""
    return "" if v is None or isinstance(v, list) else N(str(v)).strip()


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
        "sensitive": _text(fm.get("sensitive")).lower() in TRUE,
        "hub": ntype in HUB_TYPES or _text(fm.get("search_hub")).lower() in TRUE or bool(HUB_TITLE.search(title)),
        "version_key": version_key(title, rel.rsplit("/", 1)[0] if "/" in rel else ""), "links": links,
    }


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
                        if not _skip_folder(child, store) and N(os.path.normpath(e.path)) not in every:
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
    are killed, what came down stays and is counted — a handler that sets an event, so that no KeyboardInterrupt is
    raised inside a lock. Returns {candidates, downloaded, left, timed_out, failed, interrupted}. Writes nothing."""
    fetch = fetch or _fetch
    stop = threading.Event()
    res = {"candidates": 0, "downloaded": 0, "left": 0, "timed_out": 0, "failed": 0, "interrupted": False}
    old = None
    if threading.current_thread() is threading.main_thread():
        old = signal.signal(signal.SIGINT, lambda *_: stop.set())
    try:
        files = evicted(roots, store_rel, blocks_rels)
        res["candidates"] = len(files)
        queue, done, lock = list(reversed(files)), [], threading.Lock()

        def work():
            while not stop.is_set():
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
        while not stop.is_set():
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
            stop.wait(0.1)
        if stop.is_set():
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
    d["sensitive"], d["hub"] = bool(d["sensitive"]), bool(d["hub"])
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
        con.executescript(DDL)
        con.execute("INSERT INTO meta(key, value) VALUES ('schema', ?)", (SCHEMA,))
        con.commit()
        return con

    def _ro(self):
        """A read-only connection, or None when there is no index yet."""
        if not os.path.isfile(self.db_path):
            return None
        con = sqlite3.connect("file:%s?mode=ro" % urllib.parse.quote(self.db_path), uri=True, timeout=5)
        con.row_factory = sqlite3.Row
        return con

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
            try:
                files, sections, queue, when = self._walk(con, roots, store_rel, blocks_rels, deadline, res,
                                                          None if res["rebuilt"] else self._state().get("queue"))
            except sqlite3.DatabaseError as e:      # damage the open checks did not see: put it aside, walk once more
                con.close()
                if _busy(e):
                    raise
                self._set_aside(broken=True)
                res.update({k: 0 for k in COUNTS}, rebuilt=True)
                con = self._create()
                files, sections, queue, when = self._walk(con, roots, store_rel, blocks_rels, deadline, res, None)
            finally:
                con.close()
            self._save_state({"schema": SCHEMA, "updated": when, "files": files, "sections": sections,
                              "skipped_dataless": res["skipped_dataless"], "pending": res["pending"], "queue": queue})
        finally:
            self._drop_lock()
        return res

    @staticmethod
    def _walk(con, roots, store_rel, blocks_rels, deadline, res, saved):
        """One walk into `con`, then the day and the counts: (files, sections, queue, when)."""
        queue = _Walk(con, roots, store_rel, blocks_rels, deadline, res).run(saved)
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

    def __init__(self, con, roots, store_rel, blocks_rels, deadline, res):
        self.con, self.deadline, self.res = con, deadline, res
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
        self.children = collections.defaultdict(set)
        for path in self.rows:
            self._know(path)
        self.writes = 0

    def _outside(self, path):
        """Is this index name one of a root outside every vault (`@<its source>/…`)? A vault's own `@Name.md` is not."""
        row = self.rows.get(path)
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
        """Walk: the saved queue of an unfinished walk when there is one, else a new walk from the roots. Returns the
        queue of what is left ([kind, root path, path, rel]); sets res["pending"]."""
        by_path = {r["path"]: i for i, r in enumerate(self.roots)}
        items = []
        for it in saved or []:
            if isinstance(it, list) and len(it) == 4 and it[0] in ("d", "f") and it[1] in by_path:
                items.append((it[0], by_path[it[1]], it[2], it[3]))
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
                    if _skip_folder(child, self.store_rel):
                        continue
                    present.add(name)
                    if N(os.path.normpath(e.path)) not in self.root_paths:   # another root walks it itself
                        dirs.append(("d", ri, e.path, child))
                elif e.is_file():
                    present.add(name)
                    files.append(("f", ri, e.path, child))
            except OSError:
                present.add(name)                    # cannot tell what it is: keep what the index holds of it
        for name in sorted(self.children.get(rel, set()) - present):
            self._remove(rel + "/" + name if rel else name, owner=ri)
        return files + dirs

    def _file(self, ri, path, rel):
        if excluded(rel, self.store_rel, self.blocks):
            if rel in self.rows:
                self._remove(rel)
            return
        try:
            info = os.stat(path)
        except OSError:
            return
        if not stat.S_ISREG(info.st_mode):
            return
        if is_dataless(path):
            self.res["skipped_dataless"] += 1
            return
        if info.st_size > MAX_BYTES:
            self.res["skipped_large"] += 1
            if rel in self.rows:
                self._remove(rel)
            return
        row = self.rows.get(rel)
        if row and row["mtime"] == info.st_mtime and row["size"] == info.st_size:
            return
        try:
            with open(path, "rb") as f:
                data = f.read(MAX_BYTES + 1)
        except OSError:
            return
        digest = hashlib.sha1(data).hexdigest()
        if row and row["hash"] == digest:            # touched, not changed
            self.con.execute("UPDATE notes SET mtime=?, size=? WHERE id=?", (info.st_mtime, info.st_size, row["id"]))
            row.update(mtime=info.st_mtime, size=info.st_size)
            return
        text = data.decode("utf-8", errors="replace").replace("\r\n", "\n")
        self._write(row, rel, self.roots[ri]["source"], note_meta(rel, text, mtime=info.st_mtime),
                    split_sections(text), digest, info)

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
            self.con.execute("DELETE FROM notes WHERE id=?", (nid,))
            self.res["removed"] += 1
        if any(p == prefix or p.startswith(prefix + "/") for p in self.rows):
            return                                   # another root's rows by the same name: their names stay known
        parent, _, child = prefix.rpartition("/")
        self.children[parent].discard(child)
        for folder in [f for f in self.children if f == prefix or f.startswith(prefix + "/")]:
            del self.children[folder]
