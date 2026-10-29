#!/usr/bin/env python3
"""Grow PM — the graph of the index (since v4.0.0): every link resolved once, `ctx graph`.

The section index keeps every wiki link of a note as written (ctx_index.links_of, v3.18.0) and the notes' Jira-key
tokens (mentions_of); since v4.0.0 the walk also keeps every file a link may land on (`names`: a note, an evicted note,
a picture), and at the end of a refresh that changed something the links are resolved here — the rules of
`ctx search --get` — into two tables of the same file:

- edges(src_id, dst, kind, field, anchor, ambiguous)   a link that lands: `dst` the name it lands on (an index name);
                                kind `wikilink` (the text), `embed`, `fm:<field>` (a frontmatter field), `same_as` (a
                                bridge, v3.20.0) or `mention` (a Jira key → every work card of that key); a name two
                                notes or more share — an edge to each, `ambiguous` 1
- unresolved(src_id, target, field, why, candidates_json)   a link that lands nowhere (why `dead`) — its candidates the
                                notes whose name is the target's (a path that is not there: the note of that name
                                elsewhere) — or on several (why `ambiguous`: its candidates those notes)

- Resolver                      a link's target as written → the note it means (moved here from ctx_entity, which keeps
                                the name): the exact path, the plugin folder's path, the end of a path, the name; several
                                → a sorted list; a file that is not `.md` by its own name (`p.png`)
- kind_of                       the kind of an edge from where its link stands
- build                         the edges and the unresolved links of an index connection: all of them (`full`), or
                                those of the notes `changed` alone; meta `graph_version`, `graph_built`

A link to itself is no edge; a link in a code block was never kept. The tables are a cache of the index: no snapshot, no
journal, rebuilt from `links`, `mentions`, `ents` and `names` whenever their rules (GRAPH_VERSION) change. Writes only
into the index connection it is given. Stdlib only.
"""
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx_common as cc  # noqa: E402
import ctx_index as ci  # noqa: E402

N = cc.N
GRAPH_VERSION = 3                  # the rules of the edges (meta `graph_version`): another value makes the tables anew
EDGE_DDL = """
CREATE TABLE edges(src_id INTEGER, dst TEXT, kind TEXT, field TEXT, anchor TEXT, ambiguous INTEGER);
CREATE INDEX edges_src ON edges(src_id);
CREATE INDEX edges_dst ON edges(dst);
CREATE TABLE unresolved(src_id INTEGER, target TEXT, field TEXT, why TEXT, candidates_json TEXT);
CREATE INDEX unresolved_src ON unresolved(src_id);
CREATE TABLE graph_src(note_id INTEGER PRIMARY KEY, hash TEXT);
"""                                # graph_src: the hash of the note each one's edges were built from (review I-2: an
                                   # older build that shares the index re-reads a note and leaves its edges as they were)
EDGE_TABLES = ("edges", "unresolved", "graph_src")
CHUNK_SQL = 400                    # the variables of one `IN (…)` (SQLite before 3.32 allows 999)


def _stem(path):
    name = path.rsplit("/", 1)[-1]
    return name[:-3] if name.lower().endswith(".md") else name


class Resolver:
    """The note a link's target means (plan C5 of v3.18.0, the rules of `ctx search --get`). `notes`: {path: title, or
    {title, source, sensitive, date}} — every note a link may land on; `plugin_prefixes`: the index names of the plugin
    folders. Since v4.0.0 a file that is not `.md` (a picture) may be among them: a link names it with its extension."""

    def __init__(self, notes, plugin_prefixes=()):
        self.meta = {}
        for p, v in (notes or {}).items():
            self.meta[N(p)] = dict(v) if isinstance(v, dict) else {"title": v}
        self.prefixes = [N(p).strip("/") for p in plugin_prefixes or () if p]
        self.exact, self.tails, self.names, self.local, self.files = {}, {}, {}, set(), {}
        for p in self.meta:
            cf = p.casefold()
            self.exact.setdefault(cf, []).append(p)
            parts = cf.split("/")
            for i in range(1, len(parts)):
                self.tails.setdefault("/".join(parts[i:]), []).append(p)
            if p.lower().endswith(".md"):
                self.names.setdefault(ci.name_key(p), []).append(p)
            else:                               # since v4.0.0: a file that is not .md answers its whole name alone
                self.files.setdefault(p.rsplit("/", 1)[-1].casefold(), []).append(p)
            if self.meta[p].get("origin") == "local":
                self.local.add(p)

    @staticmethod
    def clean(target):
        """A target as a path to look up: `[[…]]`, `|label`, `#anchor`, `\\`, `./` and `../` gone."""
        t = N(target or "").strip()
        if t.startswith("[[") and t.endswith("]]"):
            t = t[2:-2]
        t = t.split("|", 1)[0].split("#", 1)[0].replace("\\", "/").strip()
        while t.startswith(("../", "./")):
            t = t[3:] if t.startswith("../") else t[2:]
        return t.lstrip("/")

    @staticmethod
    def _one(found):
        found = sorted(set(found or ()))
        return None if not found else found[0] if len(found) == 1 else found

    def resolve(self, target):
        """The path of the one note `target` means, a sorted list when several do, None when none does."""
        t = self.clean(target)
        if not t:
            return None
        base = t[:-3] if t.lower().endswith(".md") else t
        want = (base + ".md").casefold()
        if want in self.exact:
            return self._one(self.exact[want])
        if t.casefold() in self.exact:          # since v4.0.0: a file that is not .md, named with its extension
            return self._one(self.exact[t.casefold()])
        if "/" not in base:                     # a name: the own index's notes first, as --get looks (`_by_name`)
            hits = self.names.get(ci.name_key(base)) or self.files.get(t.casefold()) or []
            return self._one([p for p in hits if p not in self.local] or hits)
        for pre in self.prefixes:               # a path: the plugin folder's, then the end of a path (`_by_tail`)
            for key in ((pre + "/" + base + ".md").casefold(), (pre + "/" + t).casefold()):
                hit = self.exact.get(key)
                if hit:
                    return self._one(hit)
        return self._one(self.tails.get(want) or self.tails.get(t.casefold()))

    def same_name(self, target):
        """The notes whose name is the target's — a dead link's candidates (a path that is not there)."""
        t = self.clean(target)
        return sorted(set(self.names.get(ci.name_key(t)) or self.files.get(t.rsplit("/", 1)[-1].casefold()) or []))

    def title(self, path):
        return (self.meta.get(path) or {}).get("title") or _stem(path)


def kind_of(field, embed):
    """The kind of an edge: `embed`, `wikilink` (the text), `same_as`, else `fm:<field>`."""
    if embed:
        return "embed"
    if not field:
        return "wikilink"
    return "same_as" if field.casefold() == "same_as" else "fm:" + field


def _meta(con, key):
    row = con.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row[0] if row else None


def stale(con):
    """Were the edges never built, or built by other rules?"""
    return _meta(con, "graph_version") != str(GRAPH_VERSION)


def _ids_in(con, sql, values):
    out = set()
    values = list(values)
    for i in range(0, len(values), CHUNK_SQL):
        part = values[i:i + CHUNK_SQL]
        out.update(r[0] for r in con.execute(sql % ",".join("?" * len(part)), part))
    return out


def _work(con):
    """{key: [paths]} of the work cards — when it changes, every mention is resolved again (review I-1)."""
    work = {}
    for path, key in con.execute("SELECT n.path, e.key FROM ents e JOIN notes n ON n.id = e.note_id "
                                 "AND e.hash = n.hash AND e.path = n.path WHERE e.kind = 'work' AND e.key != ''"):
        work.setdefault(key, set()).add(N(path))
    return {k: sorted(v) for k, v in sorted(work.items())}


def build(con, prefixes, changed=None, name_keys=(), full=False, vault_of=None):
    """The edges and the unresolved links into `con` (the index, read-write). All of them when `full`, when they were
    never built or built by other rules (the tables made anew), or when the work cards changed; else those of the notes
    `changed` (their ids), of the notes whose links name one of `name_keys` (names that came or went), and of every
    note whose hash is not the one its edges were built from. `vault_of` (an index name → its vault, None outside every
    vault): a link lands only in its own vault — Obsidian opens nothing in another (since rules 3); a note outside
    every vault (a copy of a core, `@…`) stays reachable. Returns how many rows were written."""
    tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    if stale(con) or not set(EDGE_TABLES) <= tables:
        for t in EDGE_TABLES:
            con.execute("DROP TABLE IF EXISTS %s" % t)
        con.executescript(EDGE_DDL)
        full = True
    work = _work(con)
    fp = json.dumps(work, ensure_ascii=False, sort_keys=True)
    if _meta(con, "graph_work") != fp:
        full = True
    paths = {nid: N(p) for nid, p in con.execute("SELECT id, path FROM notes")}
    if full:
        ids = None
    else:
        ids = {int(i) for i in changed or ()}
        ids |= {r[0] for r in con.execute("SELECT n.id FROM notes n LEFT JOIN graph_src g ON g.note_id = n.id "
                                          "WHERE g.hash IS NOT n.hash")}
        if name_keys:
            ids |= _ids_in(con, "SELECT DISTINCT note_id FROM links WHERE tkey IN (%s)", sorted(name_keys))
        gone = [r[0] for r in con.execute("SELECT note_id FROM graph_src WHERE note_id NOT IN (SELECT id FROM notes)")]
        for t, col in (("edges", "src_id"), ("unresolved", "src_id"), ("graph_src", "note_id")):
            for i in range(0, len(gone), CHUNK_SQL):
                part = gone[i:i + CHUNK_SQL]
                con.execute("DELETE FROM %s WHERE %s IN (%s)" % (t, col, ",".join("?" * len(part))), part)
        ids &= set(paths)
        if not ids:
            if gone:
                con.commit()
            return 0
    metas = {}
    for path, title, source in con.execute("SELECT path, title, source FROM notes"):
        metas[N(path)] = {"title": title, "source": source}
    for path, source in con.execute("SELECT path, source FROM names"):
        metas.setdefault(N(path), {"title": _stem(N(path)), "source": source})
    res = Resolver(metas, prefixes)
    by_key = {k: set(v) for k, v in work.items()}
    if ids is None:
        for t in EDGE_TABLES:
            con.execute("DELETE FROM %s" % t)
        rows = con.execute("SELECT note_id, field, target, anchor, embed FROM links").fetchall()
        mentions = con.execute("SELECT note_id, key FROM mentions").fetchall()
        done = set(paths)
    else:
        rows, mentions, order = [], [], sorted(ids)
        for i in range(0, len(order), CHUNK_SQL):
            part = order[i:i + CHUNK_SQL]
            marks = ",".join("?" * len(part))
            for t, col in (("edges", "src_id"), ("unresolved", "src_id"), ("graph_src", "note_id")):
                con.execute("DELETE FROM %s WHERE %s IN (%s)" % (t, col, marks), part)
            rows += con.execute("SELECT note_id, field, target, anchor, embed FROM links WHERE note_id IN (%s)" % marks,
                                part).fetchall()
            mentions += con.execute("SELECT note_id, key FROM mentions WHERE note_id IN (%s)" % marks, part).fetchall()
        done = ids
    edges, dead, seen = [], [], set()
    def here(dst, src):
        if vault_of is None:
            return True
        a, b = vault_of(src), vault_of(dst)
        return a is None or b is None or a == b

    for nid, field, target, anchor, embed in rows:
        src = paths.get(nid)
        if src is None:
            continue
        kind = kind_of(field or "", embed)
        hit = res.resolve(target)
        if isinstance(hit, list):
            near = [h for h in hit if here(h, src)]
            hit = near[0] if len(near) == 1 else near if near else ("elsewhere", hit)
        elif isinstance(hit, str) and not here(hit, src):
            hit = ("elsewhere", [hit])
        if isinstance(hit, tuple):               # only another vault holds it: dead here, its notes the candidates
            dead.append((nid, target, field or "", "dead", json.dumps(hit[1], ensure_ascii=False)))
            continue
        if isinstance(hit, list):
            dead.append((nid, target, field or "", "ambiguous", json.dumps(hit, ensure_ascii=False)))
            for dst in hit:
                if dst != src and (nid, dst, kind) not in seen:
                    seen.add((nid, dst, kind))
                    edges.append((nid, dst, kind, field or "", anchor or "", 1))
        elif hit is None:
            dead.append((nid, target, field or "", "dead", json.dumps(res.same_name(target), ensure_ascii=False)))
        elif hit != src and (nid, hit, kind) not in seen:
            seen.add((nid, hit, kind))
            edges.append((nid, hit, kind, field or "", anchor or "", 0))
    for nid, key in mentions:
        src = paths.get(nid)
        for dst in sorted(by_key.get(key) or ()):
            if src is not None and dst != src and (nid, dst, "mention") not in seen:
                seen.add((nid, dst, "mention"))
                edges.append((nid, dst, "mention", "", key, 0))
    con.executemany("INSERT INTO edges(src_id, dst, kind, field, anchor, ambiguous) VALUES (?, ?, ?, ?, ?, ?)", edges)
    con.executemany("INSERT INTO unresolved(src_id, target, field, why, candidates_json) VALUES (?, ?, ?, ?, ?)", dead)
    hashes = dict(con.execute("SELECT id, hash FROM notes").fetchall())
    con.executemany("INSERT OR REPLACE INTO graph_src(note_id, hash) VALUES (?, ?)",
                    [(i, hashes.get(i)) for i in sorted(done)])
    con.execute("INSERT OR REPLACE INTO meta(key, value) VALUES ('graph_version', ?)", (str(GRAPH_VERSION),))
    con.execute("INSERT OR REPLACE INTO meta(key, value) VALUES ('graph_work', ?)", (fp,))
    con.execute("INSERT OR REPLACE INTO meta(key, value) VALUES ('graph_built', ?)",
                (datetime.datetime.now().astimezone().isoformat(timespec="seconds"),))
    con.commit()
    return len(edges) + len(dead)


# ------------------------------------------------------------------ `ctx graph`
LIMIT = 200                        # the nodes one hop shows at most (by how many edges join them to the hop before)
CHUNK = 400                        # the names one SQL `IN (…)` holds
NOT_FOUND = "граф: нічого не знайдено за «%s» — шлях, назва, [[лінк]], пошта, Jira-ключ або назва сутності"
SEVERAL = "граф: «%s» — кілька збігів: %s — уточни шляхом"
NOT_READ = "граф: індекс не відповів — %s"


def _chunks(items):
    items = list(items)
    for i in range(0, len(items), CHUNK):
        yield items[i:i + CHUNK]


def kind_ok(kind, kinds):
    """Does an edge of `kind` pass `--kind` (`fm` takes every fm:<field>)?"""
    if not kinds:
        return True
    return kind in kinds or (kind.startswith("fm:") and "fm" in kinds)


def _hop(con, frontier, seen, kinds, closed=()):
    """{path: {dirs, kinds, via, ambiguous, degree}} — the names one hop away from the paths `frontier`, both ways, but
    for those in `seen`; from a path of `closed` (a sensitive one) only the notes that link to it, never what its own
    text links (review I-6 of tasks 4–6)."""
    found = {}

    def add(path, d, kind, via, amb):
        if path in seen:
            return
        n = found.setdefault(path, {"dirs": set(), "kinds": set(), "via": [], "ambiguous": False, "degree": 0})
        n["dirs"].add(d)
        n["kinds"].add(kind)
        if via not in n["via"]:
            n["via"].append(via)
        n["ambiguous"] = n["ambiguous"] or bool(amb)
        n["degree"] += 1

    ids = {}
    for part in _chunks([p for p in frontier if p not in set(closed)]):
        for nid, p in con.execute("SELECT id, path FROM notes WHERE path IN (%s)" % ",".join("?" * len(part)), part):
            ids[nid] = p
    for part in _chunks(ids):
        for src, dst, kind, amb in con.execute("SELECT src_id, dst, kind, ambiguous FROM edges WHERE src_id IN (%s)"
                                               % ",".join("?" * len(part)), part):
            if kind_ok(kind, kinds):
                add(dst, "→", kind, ids[src], amb)
    for part in _chunks(frontier):
        for src, dst, kind, amb in con.execute("SELECT n.path, e.dst, e.kind, e.ambiguous FROM edges e JOIN notes n "
                                               "ON n.id = e.src_id WHERE e.dst IN (%s)" % ",".join("?" * len(part)), part):
            if kind_ok(kind, kinds):
                add(src, "←", kind, dst, amb)
    return found


def _about(con, paths):
    """{path: {title, source, type, sensitive, dataless}} of the names given — a note's row, else its name's."""
    out = {}
    for part in _chunks(paths):
        marks = ",".join("?" * len(part))
        for p, title, source, typ, sens in con.execute(
                "SELECT path, title, source, type, sensitive FROM notes WHERE path IN (%s)" % marks, part):
            out[p] = {"title": title or _stem(p), "source": source, "type": typ or "",
                      "sensitive": bool(sens) or (typ or "").lower() in ci.PEOPLE_TYPES or ci.one_on_one(p, title),
                      "dataless": False}
        for p, source, dl in con.execute("SELECT path, source, dataless FROM names WHERE path IN (%s)" % marks, part):
            if p not in out:                     # a name alone (evicted, a picture): sensitive by its folder (review M-2)
                out[p] = {"title": _stem(p), "source": source, "type": "", "dataless": bool(dl),
                          "sensitive": _people_path(p) or ci.one_on_one(p, _stem(p))}
            elif dl:
                out[p]["dataless"] = True
    return out


def _people_path(path):
    """Is a path under a people folder (`People/` at any depth) — sensitive before it is read (search-protocol §6)?"""
    return "people" in [x.casefold() for x in path.split("/")[:-1]]


def _private(node):
    """A sensitive node as `ctx graph` may show it (data-policy, review I-4): its title and path, no type, and the kinds
    of its edges without the field a link stood in (`fm`, never `fm:<field>`)."""
    if node.get("sensitive"):
        node["type"] = ""
        node["kinds"] = sorted({("fm" if k.startswith("fm:") else k) for k in node.get("kinds") or ()})
    return node


def neighbourhood(con, start, depth=1, kinds=None, limit=LIMIT, closed=()):
    """The nodes 1..depth hops from the names `start` (hop 0), each hop at most `limit` of them — those most joined to
    the hop before first, then by path —, and {hop: how many more}. A node: {path, title, source, type, hop, dirs
    (→ the start links to it, ← it links to the start), kinds, via (the nodes of the hop before it is joined to),
    ambiguous, sensitive, dataless}. A sensitive node is shown as _private says and the walk never goes on through it:
    what it links is its text (review I-4). The next hop starts from the nodes shown (review M-3)."""
    seen, frontier, nodes, more = set(start), list(start), [], {}
    closed = set(closed) | {p for p, a in _about(con, list(start)).items() if a.get("sensitive")}
    for hop in range(1, max(1, int(depth)) + 1):
        found = _hop(con, frontier, seen, kinds, closed)
        order = sorted(found, key=lambda p: (-found[p]["degree"], p))
        shown, more[hop] = order[:limit], max(0, len(order) - limit)
        about = _about(con, shown)
        nxt = []
        for p in shown:
            f, a = found[p], about.get(p) or {"title": _stem(p), "source": "", "type": "", "sensitive": False,
                                              "dataless": False}
            nodes.append(_private(dict(a, path=p, hop=hop, dirs=sorted(f["dirs"]), kinds=sorted(f["kinds"]),
                                       via=f["via"][:3], ambiguous=f["ambiguous"])))
            if not a.get("sensitive"):
                nxt.append(p)
        seen.update(order)
        frontier = nxt
        if not frontier:
            break
    return nodes, more


def _start(reg, query, names=()):
    """(paths, how): the names a request starts from — a path, a [[link]] or a name as `--get` takes it (one note), else
    an entity (ctx_entity: an e-mail, a Jira key, a name — all its cards); several → (list of choices, "several")."""
    if ci.ISSUE_KEY.fullmatch(N(query or "").strip().upper()):   # a Jira key: its work, not a file of that name
        found, _ = reg.find(query)
        if len(found) == 1:
            return [c["path"] for c in found[0]["cards"]], "entity"
        if found:
            return [e["id"] for e in found], "several"
    hit = reg.resolver.resolve(query)
    if isinstance(hit, str):
        return [hit], "path"
    if isinstance(hit, list):
        return hit, "several"
    found, how = reg.find(query)
    if len(found) == 1:
        return [c["path"] for c in found[0]["cards"]], "entity"
    if found:
        return [e["id"] for e in found], "several"
    if names:                                   # a name alone — a picture, an evicted note (review M-9)
        hit = Resolver({p: _stem(p) for p in names}, reg.resolver.prefixes).resolve(query)
        if isinstance(hit, str):
            return [hit], "path"
        if isinstance(hit, list):
            return hit, "several"
    return [], "none"


def run(sctx, query, depth=1, kinds=None, store=None, budget=None):
    """`ctx graph <request>` (plan C2): {command, query, how, start, depth, nodes, more, elapsed_ms, notes, read,
    pending}. Refreshes the index as `ctx entity` does (that time is not the query's: `elapsed_ms` is the walk of the
    graph alone); writes nothing else."""
    import time
    import ctx_entity as ce            # it imports this module: imported here
    idx, reg, notes, read, pending = ce._prepare(sctx, store, budget)
    out = {"command": "graph", "query": query, "how": "none", "start": [], "depth": int(depth), "nodes": [],
           "more": {}, "elapsed_ms": None, "notes": list(notes), "read": read, "pending": pending}
    names = idx._read(lambda con: [r[0] for r in con.execute("SELECT path FROM names")], [])
    paths, how = _start(reg, query, names)
    out["how"] = how
    if how in ("none", "several"):
        out["choices"] = paths
        return out
    t0 = time.perf_counter()

    def walk(con):
        about = _about(con, paths)
        start = [_private(dict(about.get(p) or {"title": _stem(p), "source": "", "type": "", "sensitive": False,
                                                "dataless": False}, path=p, hop=0)) for p in paths]
        nodes, more = neighbourhood(con, paths, depth, kinds)
        return start, nodes, more

    start, nodes, more = idx._read(walk, ([], [], {}))
    out["elapsed_ms"] = round((time.perf_counter() - t0) * 1000, 1)
    if idx.problem:
        out["notes"].append(idx.problem)
    out.update(start=start, nodes=nodes, more={str(k): v for k, v in more.items() if v})
    return out


def _line(n):
    marks = "".join((" · sensitive" if n.get("sensitive") else "", " · не завантажено" if n.get("dataless") else "",
                     " · неоднозначно" if n.get("ambiguous") else ""))
    return "  %s %s  %s — %s%s\n" % ("/".join(n["dirs"]), ", ".join(n["kinds"]), n["title"], n["path"], marks)


def render(res):
    """The lines `ctx graph` prints."""
    if res["how"] == "none":
        return NOT_FOUND % res["query"] + "\n"
    if res["how"] == "several":
        return SEVERAL % (res["query"], " · ".join(res.get("choices") or [])) + "\n"
    out = []
    for s in res["start"]:
        out.append("граф: %s — %s%s\n" % (s["title"], s["path"], " · sensitive" if s.get("sensitive") else ""))
    for hop in range(1, res["depth"] + 1):
        rows = [n for n in res["nodes"] if n["hop"] == hop]
        out.append("крок %d (%d):\n" % (hop, len(rows) + int(res["more"].get(str(hop), 0))))
        if not rows:
            out.append("  —\n")
        out.extend(_line(n) for n in rows)
        if res["more"].get(str(hop)):
            out.append("  · ще %d\n" % res["more"][str(hop)])
    out.extend("  %s\n" % n for n in res["notes"])
    out.append("запит графа: %s мс\n" % res["elapsed_ms"])
    return "".join(out)
