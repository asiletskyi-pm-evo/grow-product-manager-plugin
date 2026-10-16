#!/usr/bin/env python3
"""A fake MCP server for the context engine's tests (since v3.13.0) — the fictional "Zorg" only.

Streamable HTTP as the real server speaks it (measured): POST JSON-RPC 2.0 to one URL; `initialize`
answers `serverInfo` and `protocolVersion` and hands out the session id in the `mcp-session-id`
header; later requests must send it back; a response is `application/json` or `text/event-stream`
(mode "sse"; a keep-alive comment and an event with a notification come before the answer, and with
sse_after a notification event after it too, and with sse_junk an empty `data:` event and a
`data: ping` event before all of that);
`notifications/*` get 202 and no body; `tools/call` answers `result.content` = [{"type": "text",
"text": "<JSON string>"}] and `isError`. `vault_get_note` answers the note
{"path", "title", "frontmatter", "tags", "headings", "content", "outgoing_links"}, and for a path the
server does not have {"error": "..."} with isError false.

Not a test file (no `_test` suffix), so the runner skips it; `ctx_mcp_test.py` and the tests of the
block fetch import it. `FakeMcp` runs on 127.0.0.1, port 0, in a daemon thread and records every
request in `.seen` (a dict per request: http, path, method of the JSON-RPC message or None, headers —
the message object, so `.get("Mcp-Session-Id")` is case-insensitive —, body).

Knobs: mode "json" | "sse"; tree {path: text}; handlers {tool: fn(args) -> (obj_or_text, is_error)};
require_headers {name: value} (401 otherwise); drop N (-1 = all) tools/call connections closed
without an answer; delay seconds before answering a tools/call; fail_status answers tools/call with that
HTTP status; redirect_to answers every POST with a redirect (redirect_status, 307) to that URL; rpc_error answers a tools/call with a
JSON-RPC error object; raw_result answers every tools/call with that object as the whole `result`
(for a server that sends something the protocol does not allow, such as a number for `content`);
delays {method: seconds} pauses before answering that method — `initialize` and `notifications/initialized`
too (since v3.14: a slow but healthy handshake). Stdlib only.
"""
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BLOCKS = ("# Zorg Growth blocks\n\n"
          "<!-- zorg-growth:begin id=growth-metrics v=0.1 -->\n"
          "#### Growth metrics\n- **North star:** weekly active shoppers\n"
          "<!-- zorg-growth:end id=growth-metrics -->\n")
DEFAULT_TREE = {"Growth/_System/context-blocks.md": BLOCKS}
SESSION_ID = "s-1"
PROTOCOL_VERSION = "2025-03-26"


def note_for(path, text):
    """The vault_get_note answer for a note the server has."""
    title = path.rsplit("/", 1)[-1].rsplit(".", 1)[0]
    return {"path": path, "title": title, "frontmatter": {}, "tags": [], "headings": [],
            "content": text, "outgoing_links": []}


class _Server(ThreadingHTTPServer):
    def handle_error(self, request, client_address):                # a client that gave up is not news
        pass


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _reply(self, status, body=b"", ctype="application/json", headers=None):
        self.send_response(status)
        if body:
            self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if body:
            self.wfile.write(body)

    def _rpc(self, payload, headers=None):
        fake = self.server.fake
        if fake.mode == "sse":
            noise = ""
            if fake.sse_noise:
                noise = (": keep-alive\n\n" + "event: message\ndata: "
                         + json.dumps({"jsonrpc": "2.0", "method": "notifications/message",
                                       "params": {"level": "info", "data": "working"}}) + "\n\n")
            if fake.sse_junk:                                  # a priming event with empty data, then a non-JSON ping
                noise = "id: 0\ndata:\n\n" + "event: ping\ndata: ping\n\n" + noise
            tail = ""
            if fake.sse_after:
                tail = "event: message\ndata: " + json.dumps({"jsonrpc": "2.0", "method": "notifications/done"}) + "\n\n"
            body = (noise + "event: message\ndata: " + json.dumps(payload) + "\n\n" + tail).encode("utf-8")
            self._reply(200, body, "text/event-stream", headers)
        else:
            self._reply(200, json.dumps(payload).encode("utf-8"), "application/json", headers)

    def do_POST(self):
        fake = self.server.fake
        raw = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        try:
            msg = json.loads(raw.decode("utf-8"))
        except ValueError:
            msg = None
        method = msg.get("method") if isinstance(msg, dict) else None
        fake.record({"http": "POST", "path": self.path, "method": method, "headers": self.headers, "body": msg})
        if fake.redirect_to:
            return self._reply(fake.redirect_status, b"", headers={"Location": fake.redirect_to})
        for name, value in fake.require_headers.items():
            if self.headers.get(name) != value:
                return self._reply(401, b"unauthorized", "text/plain")
        if method != "initialize" and self.headers.get("Mcp-Session-Id") != SESSION_ID:
            return self._reply(400, b"no session", "text/plain")
        rid = msg.get("id") if isinstance(msg, dict) else None
        if fake.delays.get(method):
            time.sleep(fake.delays[method])
        if method == "initialize":
            return self._rpc({"jsonrpc": "2.0", "id": rid, "result": {
                "protocolVersion": PROTOCOL_VERSION, "capabilities": {"tools": {}},
                "serverInfo": {"name": "zorg-growth-mcp", "version": "1.4"}}}, {"mcp-session-id": SESSION_ID})
        if rid is None:                                             # a notification
            return self._reply(202)
        if method != "tools/call":
            return self._rpc({"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": "no such method"}})
        if fake.delay:
            time.sleep(fake.delay)
        if fake.take_drop():
            self.close_connection = True
            return                                                   # closed without an answer
        if fake.fail_status:
            return self._reply(fake.fail_status, b"server trouble", "text/plain")
        if fake.rpc_error:
            return self._rpc({"jsonrpc": "2.0", "id": rid, "error": {"code": -32000, "message": fake.rpc_error}})
        if fake.raw_result is not None:
            return self._rpc({"jsonrpc": "2.0", "id": rid, "result": fake.raw_result})
        params = msg.get("params") or {}
        handler = fake.handlers.get(params.get("name"))
        if handler is None:
            return self._rpc({"jsonrpc": "2.0", "id": rid, "error": {"code": -32602, "message": "unknown tool"}})
        obj, is_error = handler(params.get("arguments") or {})
        text = obj if isinstance(obj, str) else json.dumps(obj)
        self._rpc({"jsonrpc": "2.0", "id": rid, "result": {"content": [{"type": "text", "text": text}],
                                                            "isError": bool(is_error)}})


class FakeMcp:
    def __init__(self, mode="json", tree=None, require_headers=None, drop=0, delay=0.0, fail_status=0,
                 redirect_to="", redirect_status=307, rpc_error="", sse_noise=True, sse_after=False, sse_junk=False,
                 raw_result=None, delays=None):
        self.mode = mode
        self.tree = dict(DEFAULT_TREE if tree is None else tree)
        self.require_headers = dict(require_headers or {})
        self.drop, self.delay, self.fail_status = drop, delay, fail_status
        self.redirect_to, self.redirect_status = redirect_to, redirect_status
        self.rpc_error, self.sse_noise, self.sse_after, self.sse_junk = rpc_error, sse_noise, sse_after, sse_junk
        self.raw_result = raw_result
        self.delays = dict(delays or {})
        self.handlers = {"vault_get_note": self._get_note}
        self.seen = []
        self._lock = threading.Lock()
        self.httpd = _Server(("127.0.0.1", 0), _Handler)
        self.httpd.daemon_threads = True
        self.httpd.fake = self
        self.url = "http://127.0.0.1:%d/mcp" % self.httpd.server_address[1]
        self._thread = threading.Thread(target=self.httpd.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True)
        self._thread.start()

    def _get_note(self, args):
        path = args.get("path", "")
        if path in self.tree:
            return note_for(path, self.tree[path]), False
        return {"error": "Note not found: %s" % path}, False

    def record(self, entry):
        with self._lock:
            self.seen.append(entry)

    def take_drop(self):
        with self._lock:
            if self.drop == 0:
                return False
            if self.drop > 0:
                self.drop -= 1
            return True

    def methods(self):
        """The JSON-RPC methods seen so far, in order."""
        return [s["method"] for s in self.seen]

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
