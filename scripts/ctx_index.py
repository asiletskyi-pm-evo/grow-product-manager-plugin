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
- is_dataless                   a file iCloud has not downloaded: reading it would start the download, so it is skipped.
- Index                         sections.sqlite (notes, sections, the FTS5 table sections_fts, meta), index.json (the
                                state the session digest reads) and index.lock (one refresh at a time).

The refresh is incremental. It walks the roots as os.walk(followlinks=False) would, one folder at a time so that it can
stop and go on later: a file whose mtime and size did not change is not read, a changed one is read again (sha1 of its
bytes). A row goes only when its file is gone from a folder the walk listed; a file iCloud has not downloaded keeps its
row. The walk stops at its time budget (30 s) and leaves the folders and files it did not reach in a queue in
index.json, which the next run takes first. A sections.sqlite of another schema, or one SQLite cannot read, is put aside
as sections.sqlite.broken and built again. While another process holds index.lock (younger than 600 s, its process
alive) the refresh does nothing and the queries read the index as it is.

Writes only under `<home>/.grow-pm/index/` (through ctx_store.check_target, so inside `ctx` the write guard holds);
reads the vault and the core folders; no network. Stdlib only.
"""
import bisect
import collections
import datetime
import hashlib
import json
import os
import re
import sqlite3
import stat
import sys
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
DB_NAME, STATE_NAME, LOCK_NAME = "sections.sqlite", "index.json", "index.lock"
BM25 = (10.0, 6.0, 4.0, 4.0, 1.0)   # title, heading, tags, aliases, body
HUB_TYPES = frozenset(("glossary", "moc", "people", "person", "focus-brief", "daily-summary"))
HUB_TITLE = re.compile(r"style guide|глосарій|glossary|абревіатури", re.I)
TRUE = ("true", "yes", "1")
DATE_KEYS = ("updated", "modified", "date", "created")
COMMIT_EVERY = 50                   # files written between two commits of a refresh
N = cc.N

DDL = """
CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE notes(id INTEGER PRIMARY KEY, path TEXT UNIQUE, source TEXT, title TEXT, type TEXT, product TEXT,
                   status TEXT, date TEXT, confluence_id TEXT, aliases_json TEXT, tags_json TEXT, sensitive INTEGER,
                   hub INTEGER, version_key TEXT, links_json TEXT, hash TEXT, mtime REAL, size INTEGER);
CREATE TABLE sections(id INTEGER PRIMARY KEY, note_id INTEGER, heading TEXT, ord INTEGER, text TEXT);
CREATE INDEX sections_note ON sections(note_id);
CREATE VIRTUAL TABLE sections_fts USING fts5(title, heading, tags, aliases, body,
                                             tokenize='unicode61 remove_diacritics 2');
"""
NOTE_COLS = ("path", "source", "title", "type", "product", "status", "date", "confluence_id", "aliases_json",
             "tags_json", "sensitive", "hub", "version_key", "links_json", "hash", "mtime", "size")
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


def _skip_folder(rel, store_rel):
    """A folder (or a file in it) the index never enters: the store, `_System/providers/`, `.obsidian`, `.trash`,
    a name that starts with `_backup`."""
    if store_rel:
        s = _slash(N(store_rel)).rstrip("/")
        if s and (rel == s or rel.startswith(s + "/")):
            return True
    parts = rel.split("/")
    for i, part in enumerate(parts):
        if part in (".obsidian", ".trash") or part.startswith("_backup"):
            return True
        if part == "_System" and i + 1 < len(parts) and parts[i + 1] == "providers":
            return True
    return False


def excluded(rel, store_rel, blocks_rels):
    """Is the file `rel` (an index name) left out: under the store or `_System/providers/`, a blocks file of a
    registration, in a `.obsidian`, `.trash` or `_backup…` folder, not `.md`, or `local-context.md` itself."""
    rel = _slash(N(rel or ""))
    if _skip_folder(rel, store_rel) or rel in {_slash(N(b)) for b in blocks_rels or ()}:
        return True
    name = rel.rsplit("/", 1)[-1]
    return not name.lower().endswith(".md") or name == "local-context.md"


# ------------------------------------------------------------------ a note
_HEADING = re.compile(r"^(#{1,6})[ \t]+(.+?)(?:[ \t]+#+)?[ \t]*$")
_FENCE = re.compile(r"^[ \t]{0,3}(```|~~~)")
_FM_KEY = re.compile(r"^([^\s:#\-\[\]{}][^:]*?)[ \t]*:(?:[ \t]+(.*))?$")
_WIKI = re.compile(r"\[\[([^\]\n]+?)\]\]")
_CID = re.compile(r"\((\d{6,})\)\.md$", re.I)
_DATE = re.compile(r"^(\d{4}-\d{2}-\d{2})(?:[T ](\d{2}:\d{2}(?::\d{2})?))?")
_MARK = re.compile(r"\b(?:v\d+|draft|драфт(?:\s*№\s*\d+)?|rev\d+|ревізія\s*\d+)\b", re.I)
_DATES = re.compile(r"\d{4}-\d{2}-\d{2}|\d{2}\.\d{2}(?:\.\d{2,4})?")


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
    a tab in the indentation, or a line at the margin that is no `key: value`. A nested mapping is not read."""
    data, cur = {}, None
    for raw in lines:
        raw = raw.rstrip("\r")
        if not raw.strip() or raw.lstrip(" ").startswith("#"):
            continue
        lead = raw[:len(raw) - len(raw.lstrip(" \t"))]
        if "\t" in lead:
            return None
        if not lead:
            m = _FM_KEY.match(raw.rstrip())
            if not m:
                return None
            key, val = m.group(1).strip().lower(), (m.group(2) or "").strip()
            data[key] = _fm_value(val) if val else ""
            cur = None if val else key
            continue
        item = raw.strip()
        if cur is not None and (item == "-" or item.startswith("- ")):
            v = _fm_value(item[1:])
            if not isinstance(data.get(cur), list):
                data[cur] = []
            if isinstance(v, str) and v:
                data[cur].append(v)
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


def split_sections(text):
    """[(heading path "H1 › H2 › H3", body)] for the headings of level 1–3 (a deeper heading stays in the body, a `#` in
    a code fence is no heading). The frontmatter is cut; text before the first heading is a section of its own when
    it has any; a heading with nothing under it is left out unless every one is empty. No heading: [("", text)]."""
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
    (lower case), product, date (`updated` | `modified` | `date` | `created`, else `mtime`), confluence_id (frontmatter,
    else `(<6+ digits>).md`), aliases, tags, sensitive, hub, version_key and links (name_key of every wiki-link target
    and of `core_page`). A frontmatter that is never closed or cannot be read gives no metadata — the note is text."""
    t = (text or "").replace("\r\n", "\n")
    fm, body = _frontmatter(t)
    fm = fm or {}
    rel = _slash(N(rel or ""))
    name = rel.rsplit("/", 1)[-1]
    title = _text(fm.get("title")) or _first_h1(body) or (name[:-3] if name.lower().endswith(".md") else name)
    date = next((d for d in (_date(fm.get(k)) for k in DATE_KEYS) if d), None)
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
        "date": date or "", "confluence_id": cid, "aliases": _items(fm.get("aliases") or fm.get("alias")),
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


# ------------------------------------------------------------------ the index
def _now():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


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

    def _take_lock(self):
        """Take index.lock; False while another live process holds one younger than LOCK_STALE_S."""
        for attempt in (1, 2):
            try:
                fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
            except FileExistsError:
                try:
                    with open(self.lock_path, encoding="utf-8") as f:
                        held = json.load(f)
                    at, pid = float(held.get("at") or 0), held.get("pid")
                except (OSError, ValueError, TypeError, AttributeError):
                    at, pid = self._lock_mtime(), None
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
                if row and row[0] == SCHEMA:
                    return con, False
            except sqlite3.DatabaseError:
                pass
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
                walk = _Walk(con, roots, store_rel, blocks_rels, deadline, res)
                queue = walk.run(None if res["rebuilt"] else self._state().get("queue"))
                when = _now()
                con.execute("INSERT OR REPLACE INTO meta(key, value) VALUES ('updated', ?)", (when,))
                con.commit()
                files = con.execute("SELECT count(*) FROM notes").fetchone()[0]
                sections = con.execute("SELECT count(*) FROM sections").fetchone()[0]
            finally:
                con.close()
            self._save_state({"schema": SCHEMA, "updated": when, "files": files, "sections": sections,
                              "skipped_dataless": res["skipped_dataless"], "pending": res["pending"], "queue": queue})
        finally:
            self._drop_lock()
        return res

    # -------------------------------------------------- reading
    def query(self, expr, limit):
        """The sections an FTS5 expression matches, best first (bm25: title 10, heading 6, tags 4, aliases 4, body 1):
        dicts with the section's id, heading, ord and raw text, the note's metadata and `rank`. A blank expression, no
        index, or an index SQLite cannot read (the next refresh rebuilds it) answer []."""
        if not (expr or "").strip():
            return []
        try:
            con = self._ro()
            if con is None:
                return []
            try:
                rows = con.execute(QUERY_SQL, (expr, int(limit))).fetchall()
            finally:
                con.close()
        except sqlite3.DatabaseError:
            return []
        return [self._section_dict(r) for r in rows]

    @staticmethod
    def _section_dict(r):
        d = _note_dict(r)
        d.update({"id": r["id"], "note_id": r["note_id"], "heading": r["heading"], "ord": r["ord"], "text": r["text"]})
        if "rank" in r.keys():
            d["rank"] = r["rank"]
        return d

    def section(self, sid):
        """One section with its note's metadata, or None."""
        try:
            con = self._ro()
            if con is None:
                return None
            try:
                r = con.execute(ROW_SQL + " WHERE s.id = ?", (int(sid),)).fetchone()
            finally:
                con.close()
        except (sqlite3.DatabaseError, ValueError, TypeError):
            return None
        return self._section_dict(r) if r else None

    def notes(self):
        """The metadata of every note, by path (id, path, source, title, type, product, status, date, confluence_id,
        aliases, tags, sensitive, hub, version_key, links, hash, mtime, size)."""
        try:
            con = self._ro()
            if con is None:
                return []
            try:
                rows = con.execute("SELECT id, %s FROM notes ORDER BY path" % ", ".join(NOTE_COLS)).fetchall()
            finally:
                con.close()
        except sqlite3.DatabaseError:
            return []
        return [dict(_note_dict(r), id=r["id"]) for r in rows]

    def status(self):
        """{schema, updated, files, sections, pending, skipped_dataless}: the counts from the index, the rest from
        index.json; no index: schema None and zeros."""
        state = self._state()
        out = {"schema": None, "updated": state.get("updated"), "files": 0, "sections": 0,
               "pending": _count(state.get("pending")), "skipped_dataless": _count(state.get("skipped_dataless"))}
        try:
            con = self._ro()
            if con is not None:
                try:
                    row = con.execute("SELECT value FROM meta WHERE key='schema'").fetchone()
                    out["schema"] = row[0] if row else None
                    row = con.execute("SELECT value FROM meta WHERE key='updated'").fetchone()
                    out["updated"] = row[0] if row else out["updated"]
                    out["files"] = con.execute("SELECT count(*) FROM notes").fetchone()[0]
                    out["sections"] = con.execute("SELECT count(*) FROM sections").fetchone()[0]
                finally:
                    con.close()
        except sqlite3.DatabaseError:
            pass
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
        self.store_rel = _slash(N(store_rel or "")).rstrip("/")
        self.blocks = [_slash(N(b)) for b in blocks_rels or ()]
        self.rows = {}
        for nid, path, mtime, size, digest in con.execute("SELECT id, path, mtime, size, hash FROM notes"):
            self.rows[path] = {"id": nid, "mtime": mtime, "size": size, "hash": digest}
        self.children = collections.defaultdict(set)
        for path in self.rows:
            self._know(path)
        self.writes = 0

    def _know(self, path):
        parts = path.split("/")
        for i in range(1, len(parts)):
            self.children["/".join(parts[:i])].add(parts[i])

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
            lo = bisect.bisect_left(paths, rel + "/")
            hi = bisect.bisect_left(paths, rel + "/\U0010ffff")
            names.update(paths[lo:hi] or ["%s/" % rel])
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
            self._remove(rel + "/" + name if rel else name)
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
                  meta["confluence_id"], json.dumps(meta["aliases"], ensure_ascii=False),
                  json.dumps(meta["tags"], ensure_ascii=False), int(meta["sensitive"]), int(meta["hub"]),
                  meta["version_key"], json.dumps(meta["links"], ensure_ascii=False), digest, info.st_mtime, info.st_size)
        if row:
            nid = row["id"]
            self._drop_sections(nid)
            con.execute("UPDATE notes SET %s WHERE id=?" % ", ".join(c + "=?" for c in NOTE_COLS), values + (nid,))
            self.res["changed"] += 1
        else:
            nid = con.execute("INSERT INTO notes(%s) VALUES (%s)" % (", ".join(NOTE_COLS), ", ".join("?" * len(NOTE_COLS))),
                              values).lastrowid
            self.res["added"] += 1
            self._know(rel)
        self.rows[rel] = {"id": nid, "mtime": info.st_mtime, "size": info.st_size, "hash": digest}
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

    def _remove(self, prefix):
        """The rows of the file `prefix`, or of every file under the folder `prefix`. The names the index knew under it
        are forgotten (a name left behind elsewhere only costs a removal that finds nothing)."""
        for path in [p for p in self.rows if p == prefix or p.startswith(prefix + "/")]:
            nid = self.rows.pop(path)["id"]
            self._drop_sections(nid)
            self.con.execute("DELETE FROM notes WHERE id=?", (nid,))
            self.res["removed"] += 1
        parent, _, child = prefix.rpartition("/")
        self.children[parent].discard(child)
        for folder in [f for f in self.children if f == prefix or f.startswith(prefix + "/")]:
            del self.children[folder]
