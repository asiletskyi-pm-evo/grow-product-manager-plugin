#!/usr/bin/env python3
"""Grow PM — `ctx serve`: a local MCP server of the contract `vault/v1` over the plugin's own index (since v4.0.0).

For a host without a shell — the chat of Claude Desktop, Cowork — or any MCP client of yours: the search, the graph and
the registry of `ctx` as the tools of references/context-provider-protocol.md §2. Stdio, JSON-RPC 2.0, one message a
line; read only; no network — it answers from the section index alone (your layer, the core folders on disk, the
plugin's copies of cores), never a local index of another tool and never a core's server.

- PROTOCOLS, TOOLS            the protocol versions it speaks and the tools it lists
- Server(sctx)                handle(message) → the answer (None for a notification); the tools:
  vault_search(query, tags?, folder?, limit)   ctx search over the section index: [{path, title, snippet, score, tags,
                              sensitive}]
  vault_get_note(path)        {path, title, frontmatter, tags, headings, content, outgoing_links, trust} — for a sensitive
                              note (search-protocol §6: a people type, a 1-1, a profile's judgement) only {path, title,
                              sensitive: true, note}: a client outside the People contour gets no profile
  vault_get_links(path, direction)   {path, in, out} from the edges of the index
  vault_graph_context(entity, depth)   {nodes, edges} — ctx graph
  vault_list_by_tag(tag), vault_list_by_folder(folder)   [{path, title[, sensitive]}]
  brain_status                {last_index, age_hours, notes, edges, vault_root, schema}
  brain_find_entity(query)    {hub, related} — ctx entity
- serve(sctx, stdin, stdout)  the loop; the index is refreshed in a thread when it is an hour old (REFRESH_EVERY_S) —
                              at the start or at a call; a call that comes while it runs waits for it WAIT_S at most
- install(home, root)         `~/.grow-pm/bin/ctx-serve`, the launcher a client's config names (the plugin's folder
                              carries its version, so the config would break at the next update; `provider sync
                              --if-due` rewrites the launcher when the folder moved — relaunch_if_moved)

Writes nothing but the index (its refresh) and, on `--install`, the launcher. Stdlib only.
"""
import json
import os
import stat
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx_common as cc  # noqa: E402
import ctx_index as ci  # noqa: E402
import ctx_store as cs  # noqa: E402

N = cc.N
NAME = "grow-pm-vault"
PROTOCOLS = ("2025-06-18", "2025-03-26", "2024-11-05")
REFRESH_EVERY_S = 3600
WAIT_S = 10.0                      # a call waits this long for a refresh that runs (it holds the index while it writes)
LIMIT = 20
INSTRUCTIONS = ("Read-only search, graph and registry over your vault layer and the core folders on disk (contract "
                "vault/v1 of the Grow PM plugin). Typical chain: vault_search → vault_get_note on the hits that matter → "
                "vault_get_links / vault_graph_context when the question is about relations; brain_find_entity for a "
                "person, a team, a Jira key. A note marked sensitive is never read here: open it in a People-contour skill.")
SENSITIVE_NOTE = "sensitive — читай її скілом контуру People, не тут"


def _schema(props, required=()):
    return {"type": "object", "properties": props, "required": list(required)}


_S, _I = {"type": "string"}, {"type": "integer"}
TOOLS = [
    {"name": "vault_search", "description": "Full-text search over your layer and the cores on disk; best first.",
     "inputSchema": _schema({"query": _S, "tags": {"type": "array", "items": _S}, "folder": _S, "limit": _I}, ["query"])},
    {"name": "vault_get_note", "description": "One note: frontmatter, headings, text, its links, its trust.",
     "inputSchema": _schema({"path": _S}, ["path"])},
    {"name": "vault_get_links", "description": "The notes a note links to and that link to it.",
     "inputSchema": _schema({"path": _S, "direction": {"type": "string", "enum": ["in", "out", "both"]}}, ["path"])},
    {"name": "vault_graph_context", "description": "The notes one or two hops around a note or an entity.",
     "inputSchema": _schema({"entity": _S, "depth": {"type": "integer", "enum": [1, 2]}}, ["entity"])},
    {"name": "vault_list_by_tag", "description": "The notes that carry a tag.", "inputSchema": _schema({"tag": _S}, ["tag"])},
    {"name": "vault_list_by_folder", "description": "The notes under a folder (\"\" — all).",
     "inputSchema": _schema({"folder": _S}, ["folder"])},
    {"name": "brain_status", "description": "How fresh and how big the index is.", "inputSchema": _schema({})},
    {"name": "brain_find_entity", "description": "A person, a team, a mission, a Jira key: its card and what is related.",
     "inputSchema": _schema({"query": _S}, ["query"])},
]


class ToolError(Exception):
    pass


def _sensitive(row):
    t = (row.get("type") or "").lower()
    return bool(row.get("sensitive")) or t in ci.PEOPLE_TYPES or ci.one_on_one(row.get("path"), row.get("title"))


class Server:
    def __init__(self, sctx, version="", refresh=True):
        self.sctx = sctx
        self.version = version
        self.idx = ci.Index(sctx["home"])
        self.refreshed_at = 0.0
        self.thread = None
        self.auto = refresh
        if refresh and self._age() > REFRESH_EVERY_S:
            self.kick()
        else:
            self.refreshed_at = time.time() - self._age()

    def _age(self):
        """Seconds since the index was last brought up to date (index.json); a missing one is very old."""
        import datetime
        try:
            with open(self.idx.state_path, encoding="utf-8") as f:
                t = datetime.datetime.fromisoformat(json.load(f).get("updated"))
            return max(0.0, (datetime.datetime.now(t.tzinfo) - t).total_seconds())
        except (OSError, ValueError, TypeError, AttributeError):
            return float("inf")

    # -------------------------------------------------- the index
    def kick(self):
        """A refresh of the index in a thread, unless one runs (a call never waits for it)."""
        if self.thread is not None and self.thread.is_alive():
            return
        self.refreshed_at = time.time()

        def work():
            try:
                ci.Index(self.sctx["home"]).refresh(self.sctx["roots"], self.sctx["store_rel"], self.sctx["blocks_rels"])
            except Exception:  # noqa: BLE001 — a refresh that fails leaves the index as it is
                pass

        self.thread = threading.Thread(target=work, daemon=True)
        self.thread.start()

    def _read(self, fn, empty):
        out = self.idx._read(fn, empty)
        if self.idx.problem:
            raise ToolError(self.idx.problem)
        return out

    # -------------------------------------------------- the protocol
    def handle(self, msg):
        if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0" or not isinstance(msg.get("method"), str):
            return {"jsonrpc": "2.0", "id": msg.get("id") if isinstance(msg, dict) else None,
                    "error": {"code": -32600, "message": "invalid request"}}
        mid, method, params = msg.get("id"), msg["method"], msg.get("params") or {}
        if "id" not in msg:                       # a notification: no answer
            return None
        if method == "initialize":
            asked = str(params.get("protocolVersion") or "")
            return self._ok(mid, {"protocolVersion": asked if asked in PROTOCOLS else PROTOCOLS[0],
                                  "capabilities": {"tools": {}}, "serverInfo": {"name": NAME, "version": self.version},
                                  "instructions": INSTRUCTIONS})
        if method == "ping":
            return self._ok(mid, {})
        if method == "tools/list":
            return self._ok(mid, {"tools": TOOLS})
        if method == "tools/call":
            name, args = params.get("name"), params.get("arguments") or {}
            fn = getattr(self, "t_" + str(name), None)
            if fn is None:                        # only the t_<tool> methods answer a call
                return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32602, "message": "unknown tool: %s" % name}}
            if self.auto and time.time() - self.refreshed_at > REFRESH_EVERY_S:
                self.kick()
            if self.thread is not None and self.thread.is_alive():
                self.thread.join(WAIT_S)          # it holds the index while it writes: a read now would find it busy
            try:
                out = fn(args if isinstance(args, dict) else {})
            except ToolError as e:
                return self._ok(mid, {"content": [{"type": "text", "text": str(e)}], "isError": True})
            except Exception as e:  # noqa: BLE001 — a tool's fault is the call's answer, never the server's end
                return self._ok(mid, {"content": [{"type": "text", "text": "%s: %s" % (type(e).__name__, e)}],
                                      "isError": True})
            return self._ok(mid, {"content": [{"type": "text", "text": json.dumps(out, ensure_ascii=False)}],
                                  "structuredContent": out if isinstance(out, dict) else {"result": out},
                                  "isError": False})
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": "method not found: %s" % method}}

    @staticmethod
    def _ok(mid, result):
        return {"jsonrpc": "2.0", "id": mid, "result": result}

    # -------------------------------------------------- the tools
    def _arg(self, args, key):
        v = args.get(key)
        if not isinstance(v, str) or not v.strip():
            raise ToolError("%s is required" % key)
        return v.strip()

    def t_vault_search(self, args):
        import ctx_search as cs_
        q = self._arg(args, "query")
        try:
            limit = max(1, min(100, int(args.get("limit") or LIMIT)))
        except (TypeError, ValueError):
            limit = LIMIT
        res = cs_.run(self.sctx, [q], limit=max(limit, 30), which=("own",), use_hints=False, refresh=False)
        folder = N(str(args.get("folder") or "")).strip("/")
        tags = {str(t).lower().lstrip("#") for t in args.get("tags") or () if t}
        out = []
        for c in res.get("candidates") or []:
            if folder and not (c["path"] == folder or c["path"].startswith(folder + "/")):
                continue
            got = self.idx.note(c["path"])
            meta = got[0] if got else {}
            ctags = [str(t).lower().lstrip("#") for t in meta.get("tags") or []]
            if tags and not tags <= set(ctags):
                continue
            sens = bool(c.get("sensitive")) or "sensitive" in (c.get("flags") or []) or _sensitive(
                dict(meta, path=c["path"], title=c.get("title") or meta.get("title"), type=c.get("type") or meta.get("type")))
            hit = {"path": c["path"], "title": c.get("title") or "", "score": c.get("score"), "sensitive": sens}
            if not sens:
                hit.update(snippet=c.get("snippet") or "", tags=ctags, type=c.get("type") or "", date=c.get("date") or "")
            out.append(hit)
            if len(out) >= limit:
                break
        return {"results": out}

    def _file(self, path):
        """The note's file on disk (one of the roots holds it), or None."""
        for r in self.sctx.get("roots") or []:
            rel = ci.rel_path(r["path"], self.sctx.get("vaults") or [], r)
            if not rel or path.startswith(rel + "/"):
                inner = path[len(rel) + 1:] if rel else path
                return os.path.join(r["path"], *inner.split("/"))
        return None

    def t_vault_get_note(self, args):
        import ctx_trust as ct
        path = N(self._arg(args, "path"))
        got = self.idx.note(path)
        if self.idx.problem:
            raise ToolError(self.idx.problem)
        if not got:
            raise ToolError("note not found: %s" % path)
        meta, sections = got
        if _sensitive(meta):
            return {"path": path, "title": meta.get("title") or "", "sensitive": True, "note": SENSITIVE_NOTE}
        fm, text = {}, None
        disk = self._file(path)
        if disk and os.path.isfile(disk) and not ci.is_dataless(disk):
            try:
                with open(disk, encoding="utf-8", errors="replace") as f:
                    raw = f.read().replace("\r\n", "\n")
                fm, body = ci._frontmatter(raw)
                text = body if fm is not None else raw
            except OSError:
                text = None
        if text is None:                          # an evicted file: the text the index keeps of it
            text = "\n\n".join(((("#" * 2) + " " + h + "\n") if h else "") + t for h, t in sections)
        links = self._read(lambda con: con.execute(
            "SELECT e.dst, e.kind FROM edges e WHERE e.src_id = ? ORDER BY e.dst", (meta["id"],)).fetchall(), [])
        dead = self._read(lambda con: con.execute(
            "SELECT target FROM unresolved WHERE src_id = ? AND why = 'dead'", (meta["id"],)).fetchall(), [])
        kind = ct.kind_of(self.sctx, meta.get("source"), path, meta.get("confluence_id"))
        trust = ct.score(kind, meta.get("ttl_date") or meta.get("date"), ct.ttl_of(self.sctx, path), meta.get("status"),
                         ci._text((fm or {}).get("last_verified") or (fm or {}).get("last_reviewed")))
        return {"path": path, "title": meta.get("title") or "", "frontmatter": _plain(fm or {}),
                "tags": meta.get("tags") or [], "headings": [h for h, _ in sections if h], "content": text,
                "outgoing_links": [{"target": d, "resolved_path": d, "kind": k} for d, k in links] +
                                  [{"target": t, "resolved_path": None} for t, in dead],
                "trust": trust}

    def _rows(self, sql, args):
        return self._read(lambda con: con.execute(sql, args).fetchall(), [])

    def t_vault_get_links(self, args):
        path = N(self._arg(args, "path"))
        d = str(args.get("direction") or "both")
        if d not in ("in", "out", "both"):
            raise ToolError("direction takes in, out or both")
        out = {"path": path}
        notes = {p: (t, ty, s) for p, t, ty, s in self._rows("SELECT path, title, type, sensitive FROM notes", ())}

        def item(p, extra=None):
            t, ty, s = notes.get(p, (p.rsplit("/", 1)[-1], "", 0))
            r = dict({"path": p, "title": t or ""}, **(extra or {}))
            if _sensitive({"path": p, "title": t, "type": ty, "sensitive": s}):
                r["sensitive"] = True
            return r

        if d in ("out", "both"):
            out["out"] = [item(p, {"resolved": True, "kind": k}) for p, k in self._rows(
                "SELECT e.dst, e.kind FROM edges e JOIN notes n ON n.id = e.src_id WHERE n.path = ? ORDER BY e.dst",
                (path,))]
        if d in ("in", "both"):
            out["in"] = [item(p, {"kind": k}) for p, k in self._rows(
                "SELECT n.path, e.kind FROM edges e JOIN notes n ON n.id = e.src_id WHERE e.dst = ? ORDER BY n.path",
                (path,))]
        return out

    def _registry(self):
        import ctx_entity as ce
        reg, _ = ce.load(self.sctx, self.idx, ce.empty_memory(), hints=False)
        return reg

    def t_vault_graph_context(self, args):
        import ctx_graph as cg
        q = self._arg(args, "entity")
        try:
            depth = 2 if int(args.get("depth") or 1) == 2 else 1
        except (TypeError, ValueError):
            depth = 1
        reg = self._registry()
        names = self._read(lambda con: [r[0] for r in con.execute("SELECT path FROM names")], [])
        paths, how = cg._start(reg, q, names)
        if how == "none":
            raise ToolError("nothing found: %s" % q)
        if how == "several":
            raise ToolError("several: %s — ask by path" % " · ".join(paths[:10]))

        def walk(con):
            about = cg._about(con, paths)
            start = [cg._private(dict(about.get(p) or {"title": p, "sensitive": False}, path=p, hop=0)) for p in paths]
            return start, cg.neighbourhood(con, paths, depth)

        start, (nodes, more) = self._read(walk, ([], ([], {})))
        edges = []
        for n in nodes:
            for v in n["via"]:
                for k in n["kinds"]:
                    if "→" in n["dirs"]:
                        edges.append({"src": v, "dst": n["path"], "kind": k})
                    if "←" in n["dirs"]:
                        edges.append({"src": n["path"], "dst": v, "kind": k})
        return {"nodes": [{"path": s_["path"], "title": s_.get("title") or "", "hop": 0,
                           **({"sensitive": True} if s_.get("sensitive") else {})} for s_ in start] +
                         [{"path": n["path"], "title": n["title"], "hop": n["hop"],
                           **({"sensitive": True} if n.get("sensitive") else {})} for n in nodes],
                "edges": edges, "more": {str(k): v for k, v in more.items() if v}}

    def _list(self, where, args):
        rows = self._rows("SELECT path, title, type, sensitive FROM notes %s ORDER BY path" % where, args)
        out = []
        for p, t, ty, s in rows:
            r = {"path": p, "title": t or ""}
            if _sensitive({"path": p, "title": t, "type": ty, "sensitive": s}):
                r["sensitive"] = True
            out.append(r)
        return out

    def t_vault_list_by_tag(self, args):
        tag = self._arg(args, "tag").lstrip("#").lower()
        rows = self._list("", ())
        tags = dict(self._rows("SELECT path, tags_json FROM notes", ()))
        out = []
        for r in rows:
            try:
                have = [str(t).lower().lstrip("#") for t in json.loads(tags.get(r["path"]) or "[]")]
            except ValueError:
                have = []
            if tag in have:
                out.append(r)
        return {"results": out}

    def t_vault_list_by_folder(self, args):
        folder = N(str(args.get("folder") or "")).strip("/")
        if not folder:
            return {"results": self._list("", ())}
        return {"results": self._list("WHERE path = ? OR substr(path, 1, ?) = ?", (folder, len(folder) + 1, folder + "/"))}

    def t_brain_status(self, args):
        def read(con):
            meta = dict(con.execute("SELECT key, value FROM meta").fetchall())
            n = con.execute("SELECT count(*) FROM notes").fetchone()[0]
            tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
            e = con.execute("SELECT count(*) FROM edges").fetchone()[0] if "edges" in tables else 0
            return meta, n, e
        got = self._read(read, None)
        if got is None:
            raise ToolError("індексу ще немає — ctx index rebuild")
        meta, n, e = got
        age = None
        try:
            import datetime
            t = datetime.datetime.fromisoformat(meta.get("updated"))
            age = round((datetime.datetime.now(t.tzinfo) - t).total_seconds() / 3600.0, 1)
        except (TypeError, ValueError):
            pass
        return {"last_index": meta.get("updated"), "age_hours": age, "notes": n, "edges": e,
                "vault_root": [v for v in self.sctx.get("vaults") or []], "schema": meta.get("schema")}

    def t_brain_find_entity(self, args):
        q = self._arg(args, "query")
        reg = self._registry()
        found, how = reg.find(q)
        if not found:
            raise ToolError("nothing found: %s" % q)
        e = found[0]
        hub = next((c for c in e["cards"] if c["path"] == e["id"]), e["cards"][0])
        rel = [{"path": c["path"], "title": c.get("label") or "", "kind": c.get("kind") or e["kind"]}
               for c in e["cards"] if c["path"] != hub["path"]] + \
              [{"path": r["path"], "title": r.get("label") or "", "kind": "related"} for r in e.get("related") or []]
        return {"hub": {"path": hub["path"], "title": hub.get("label") or "", "kind": e["kind"]}, "related": rel,
                "several": len(found)}


def _plain(fm):
    """A frontmatter as JSON can hold it (a date as its text)."""
    return json.loads(json.dumps(fm, ensure_ascii=False, default=str))


def serve(sctx, stdin, stdout, version="", refresh=True):
    """The loop: one JSON-RPC message a line in, one answer a line out, until stdin ends."""
    srv = Server(sctx, version, refresh=refresh)
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            ans = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}}
        else:
            ans = srv.handle(msg)
        if ans is not None:
            stdout.write(json.dumps(ans, ensure_ascii=False) + "\n")
            stdout.flush()
    return 0


# ------------------------------------------------------------------ the launcher
LAUNCHER_MARK = "# ctx:generated — Grow PM local MCP (ctx serve); rewritten when the plugin's folder moves"


def launcher_path(home):
    return os.path.join(home or os.path.expanduser("~"), ".grow-pm", "bin", "ctx-serve")


def launcher_text(root):
    return "#!/bin/sh\n%s\nexec python3 \"%s\" serve \"$@\"\n" % (LAUNCHER_MARK, os.path.join(root, "scripts", "ctx.py"))


def install(home, root):
    """Write the launcher (only when it differs); (path, written)."""
    path = launcher_path(home)
    want = launcher_text(root)
    try:
        with open(path, encoding="utf-8") as f:
            if f.read() == want:
                return path, False
    except OSError:
        pass
    cs.check_target(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(want)
    os.chmod(tmp, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
    os.replace(tmp, path)
    return path, True


def relaunch_if_moved(home, root):
    """`provider sync --if-due`: a launcher there (ours, by its mark) that names another folder of the plugin is
    written again; none there — nothing (the launcher is made only by `ctx serve --install`). True when written."""
    path = launcher_path(home)
    try:
        with open(path, encoding="utf-8") as f:
            have = f.read()
    except OSError:
        return False
    if LAUNCHER_MARK not in have or have == launcher_text(root):
        return False
    return install(home, root)[1]


def config_lines(path):
    """What a client's config says: Claude Desktop's mcpServers entry and Codex CLI's command."""
    return ['"%s": {"command": "%s"}' % (NAME, path), "codex mcp add %s -- %s" % (NAME, path)]
