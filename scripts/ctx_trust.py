#!/usr/bin/env python3
"""Grow PM — the trust of an answer's source, shown beside it (since v4.0.0). It never changes a ranking.

    trust = source × freshness × state

- source      where the text lives: your note 0.9 · a core's block or card (its folder, or
              the plugin's copy of it) 0.85 · a note of a local index 0.8 · a note a server gave 0.75 · a Confluence page
              mirrored into a core (`confluence_id`, a page id in its name) 0.7
- freshness   1 within the TTL of its class (context-provider-protocol.md §6; a core's `ttl_days`, else a year), then
              down in a straight line to 0.5 at three TTLs, never below 0.5; no date 0.6 — counted from the later of
              the note's day and its `last_verified` / `last_reviewed`
- state       `superseded`, `archived`, `outdated` (the search's «застаріле») 0.3 · `draft` 0.8 · else 1

- SOURCE, STATE, …           the weights — the table of references/search-protocol.md says the same
- score(kind, day, ttl, status, verified, today)   {score, parts: {source, freshness, state}, kind}
- line(t)                     «довіра 0,72 (джерело 0,9 · свіжість 0,8 · стан 1)»
- kind_of(sctx, source, path, confluence_id)   the source kind of a note
- for_note(sctx, meta, fm, today)   the trust of a note of the index (its row) and its frontmatter
- for_path(sctx, path, today)  the same for an index name: its row, its frontmatter read from disk when downloaded —
                              what `ctx search --get` and `ctx serve` both give (review I8 of tasks 7–9)
- for_header(sctx, header, today)   a `--get` provenance line, for a note the index does not hold

Reads nothing (kind_of: the search context's registrations and the classes' TTL). Stdlib only.
"""
import datetime
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

SOURCE = {"own": 0.9, "core": 0.85, "local": 0.8, "mcp": 0.75, "confluence": 0.7}
STATE = {"superseded": 0.3, "archived": 0.3, "outdated": 0.3, "застаріле": 0.3, "draft": 0.8}
DEFAULT_TTL = 365                  # days: the TTL of a note whose class names none
FLOOR, UNDATED = 0.5, 0.6
_CID = re.compile(r"\((\d{6,})\)\.md$", re.I)


def _day(v):
    try:
        return datetime.date.fromisoformat(str(v or "").strip()[:10])
    except ValueError:
        return None


def freshness(day, ttl, today):
    """1 within `ttl` days of `day`, a straight line down to FLOOR at 3 × ttl, FLOOR after; UNDATED without a day."""
    d, t = _day(day), _day(today) or datetime.date.today()
    if d is None:
        return UNDATED
    ttl = ttl if isinstance(ttl, int) and ttl > 0 else DEFAULT_TTL
    age = (t - d).days
    if age <= ttl:
        return 1.0
    if age >= 3 * ttl:
        return FLOOR
    return round(1.0 - (1.0 - FLOOR) * (age - ttl) / (2.0 * ttl), 2)


def state(status):
    s = str(status or "").strip().lower()
    if s in STATE:
        return STATE[s]
    return 1.0


def score(kind, day, ttl=None, status="", verified="", today=None):
    """{score, parts, kind} of a source (see the module's doc); `verified` (a `last_verified`/`last_reviewed` day) dates
    the freshness when it is later than `day`."""
    today = today or datetime.date.today().isoformat()
    when = day
    if _day(verified) and (not _day(day) or _day(verified) > _day(day)):
        when = verified
    parts = {"source": SOURCE.get(kind, SOURCE["local"]), "freshness": freshness(when, ttl, today),
             "state": state(status)}
    return {"score": round(parts["source"] * parts["freshness"] * parts["state"], 2), "parts": parts, "kind": kind}


def _num(x):
    return ("%g" % x).replace(".", ",")


def line(t):
    p = t["parts"]
    return "довіра %s (джерело %s · свіжість %s · стан %s)" % (_num(t["score"]), _num(p["source"]),
                                                              _num(p["freshness"]), _num(p["state"]))


def kind_of(sctx, source, path, confluence_id=None):
    """The source kind of a note: own (your layer, or a file outside every root), core (a registered repository whose
    folder is on disk — or the plugin's copy of it), confluence (such a note that mirrors a page), mcp (a repository
    reached through its server alone), local (any other source: a local index)."""
    if source in (None, "", "own", "vault"):
        return "own"
    repo = next((r for r in (sctx or {}).get("repos") or () if r.get("id") == source), None)
    if repo is None:
        return "local"
    folder = repo.get("core_root") or next(iter(repo.get("paths") or []), "")
    if not folder or not os.path.isdir(folder):
        return "mcp"
    if confluence_id or _CID.search(path or ""):
        return "confluence"
    return "core"


def ttl_of(sctx, path):
    """The TTL in days of the class a note lies in (a core's `ttl_days`), else None."""
    import ctx_search as cs_
    best, days = "", None
    for prefix, d in cs_.class_ttl((sctx or {}).get("repos") or [], (sctx or {}).get("vaults") or []).items():
        if (path == prefix or path.startswith(prefix + "/")) and len(prefix) > len(best):
            best, days = prefix, d
    return days


def for_note(sctx, meta, fm=None, today=None):
    import ctx_index as ci
    fm = fm or {}
    verified = ci._text(fm.get("last_verified") or fm.get("last_reviewed"))
    status = meta.get("status") or ci._text(fm.get("status"))
    path = meta.get("path") or ""
    return score(kind_of(sctx, meta.get("source"), path, meta.get("confluence_id")), meta.get("ttl_date") or
                 meta.get("date"), ttl_of(sctx, path), status, verified, today)


def disk_file(sctx, path):
    """The file on disk of an index name (one of the roots holds it), or None."""
    import ctx_index as ci
    for r in (sctx or {}).get("roots") or []:
        rel = ci.rel_path(r["path"], sctx.get("vaults") or [], r)
        if not rel or path.startswith(rel + "/"):
            inner = path[len(rel) + 1:] if rel else path
            return os.path.join(r["path"], *inner.split("/"))
    return None


def frontmatter_on_disk(sctx, path):
    """The note's frontmatter read from its file — None when it is not on disk, evicted or unreadable."""
    import ctx_index as ci
    f = disk_file(sctx, path)
    try:
        if not f or not os.path.isfile(f) or ci.is_dataless(f) or os.path.getsize(f) > ci.MAX_BYTES:
            return None
        with open(f, encoding="utf-8", errors="replace") as fh:
            fm, _ = ci._frontmatter(fh.read().replace("\r\n", "\n"))
        return fm if fm is not None else {}
    except OSError:
        return None


def for_path(sctx, path, today=None):
    import ctx_index as ci
    got = ci.Index((sctx or {}).get("home")).note(path)
    if not got:
        return None
    return for_note(sctx, got[0], frontmatter_on_disk(sctx, path), today)


def for_header(sctx, header, today=None):
    """The trust of a `ctx search --get` provenance line `> [<source> · <path>[ › <heading>] · <day>[ · marks]]`, or
    None when the line is not one."""
    h = (header or "").strip()
    if not (h.startswith("> [") and h.endswith("]")):
        return None
    parts = h[3:-1].split(" · ")
    if len(parts) < 3:
        return None
    source, path, day = parts[0], parts[1].split(" › ", 1)[0], parts[2]
    marks = parts[3:]
    status = "застаріле" if "застаріле" in marks else ""
    return score(kind_of(sctx, source, path), day if day != "—" else None, ttl_of(sctx, path), status, "", today)
