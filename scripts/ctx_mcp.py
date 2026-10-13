#!/usr/bin/env python3
"""Grow PM — a small MCP client for the context engine (since v3.13.0).

Reaches a repository's MCP server (a registration with `endpoint.url`, schema provider-registration/2,
references/context-provider-protocol.md §3b) over Streamable HTTP: POST JSON-RPC 2.0, the answer is
`application/json` or `text/event-stream`, the session id from the `initialize` answer goes back in
`Mcp-Session-Id`. Stdlib only (urllib), no dependency on an MCP SDK.

What it will do, and nothing more:
  * call only the tools in `ALLOWED`; any other name raises `McpRefused` before a request is made — the
    engine reads a repository, it never writes to one;
  * `probe()` is the `initialize` handshake and the `notifications/initialized` notification, once, within
    `probe_timeout` — never an exception, never a retry;
  * `call()` handshakes first when no session is open; a network error (no connection, a timeout, a dropped
    connection) is retried `retries` times, a server's answer — an HTTP status, a JSON-RPC error,
    `isError` — never is;
  * follow no redirect (a header meant for one host does not travel to another) and speak only http and https;
  * keep secrets out of every message it raises or keeps: no header value, no url (it may hold credentials).

The header a server wants (`headers_env` of the registration names an environment variable that holds
`Name: value`) is read by `headers_from_env`; the value is never stored by the engine.
"""
import http.client
import json
import os
import socket
import time
import urllib.error
import urllib.parse
import urllib.request

ALLOWED = frozenset({"vault_get_note", "vault_list_by_folder", "vault_search", "brain_status", "brain_recent_changes"})
PROTOCOL_VERSION = "2025-03-26"
CLIENT_INFO = {"name": "grow-pm-ctx", "version": "1"}
MAX_BODY = 32 * 1024 * 1024                            # a note is text; more than this is not one


class McpError(Exception):
    """A call that did not come back: the network, a timeout, a server's error or `isError`."""


class McpRefused(McpError):
    """A tool that is not on the allow-list — raised before any request."""


class _Network(McpError):
    """Internal: a failure of the connection itself, the only kind that is retried."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None                                    # the 3xx surfaces as an HTTPError


_OPENER = urllib.request.build_opener(_NoRedirect)


def headers_from_env(var):
    """The request header an environment variable holds: `Name: value` → {Name: value}.
    No variable, an empty one or one that is not `Name: value` → {}."""
    raw = os.environ.get(var) if var else None
    name, sep, value = (raw or "").partition(":")
    name, value = name.strip(), value.strip()
    return {name: value} if sep and name and value else {}


def _reason(exc):
    """What went wrong on the connection, in words that carry neither the url nor a header."""
    r = getattr(exc, "reason", exc)
    if isinstance(r, socket.timeout):
        return "timed out"
    if isinstance(r, OSError):
        return r.strerror or type(r).__name__
    if isinstance(r, str):
        return r
    return type(r).__name__


def _text_of(result):
    """The first text item of a tools/call result, or None."""
    for item in result.get("content") or []:
        if isinstance(item, dict) and item.get("type") == "text" and isinstance(item.get("text"), str):
            return item["text"]
    return None


def _sse_events(text):
    """The `data:` payloads of an event stream, one per event, in order (comments and other fields skipped)."""
    events, data = [], []
    for line in text.splitlines():
        if not line.strip():
            if data:
                events.append("\n".join(data))
            data = []
        elif line.startswith("data:"):
            data.append(line[5:][1:] if line[5:6] == " " else line[5:])
    if data:
        events.append("\n".join(data))
    return events


class McpClient:
    BACKOFF = 0.3                                      # seconds before the n-th retry, times n

    def __init__(self, url, headers=None, probe_timeout=3.0, call_timeout=30.0, retries=2):
        self.url = url
        self.headers = dict(headers or {})
        self.probe_timeout = probe_timeout
        self.call_timeout = call_timeout
        self.retries = retries
        self.session_id = None
        self.server_info = {}
        self.protocol_version = ""
        self.last_error = ""                           # why the last probe failed, without secrets
        self._ready = False
        self._ids = 0

    # ------------------------------------------------------------------ transport
    def _post(self, message, timeout):
        """One POST → (response headers, content type, body bytes). A failure of the connection raises _Network,
        anything the server answered or a request that cannot be built raises McpError."""
        try:
            scheme = urllib.parse.urlsplit(self.url).scheme
        except ValueError:
            scheme = ""
        if scheme not in ("http", "https"):
            raise McpError("the endpoint is not an http or https url")
        hdrs = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
        hdrs.update(self.headers)
        if self.session_id:
            hdrs["Mcp-Session-Id"] = self.session_id
        try:
            req = urllib.request.Request(self.url, data=json.dumps(message).encode("utf-8"), headers=hdrs, method="POST")
            with _OPENER.open(req, timeout=timeout) as resp:
                body = resp.read(MAX_BODY + 1)
                headers, ctype = resp.headers, resp.headers.get("Content-Type") or ""
        except urllib.error.HTTPError as e:            # before URLError, which it extends: the server did answer
            e.close()
            hint = " (a redirect is not followed)" if 300 <= e.code < 400 else ""
            raise McpError("HTTP %d from the server%s" % (e.code, hint))
        except http.client.InvalidURL:
            raise McpError("the endpoint url is not valid")
        except ValueError:                             # a header or the url that cannot be put on the wire
            raise McpError("the request could not be built (check the endpoint url and the header)")
        except (urllib.error.URLError, OSError, http.client.HTTPException) as e:
            raise _Network("connection failed: %s" % _reason(e))
        if len(body) > MAX_BODY:
            raise McpError("the response is too large (over %d bytes)" % MAX_BODY)
        return headers, ctype, body

    def _send(self, message, timeout, retries):
        """_post with the retries: only a failure of the connection is tried again."""
        attempt = 0
        while True:
            try:
                return self._post(message, timeout)
            except _Network as e:
                if attempt >= retries:
                    raise McpError("%s (after %d attempts)" % (e, attempt + 1) if attempt else str(e))
                attempt += 1
                time.sleep(self.BACKOFF * attempt)

    def _rpc(self, method, params, timeout, retries):
        """A request → (its result object, response headers)."""
        self._ids += 1
        rid = self._ids
        headers, ctype, body = self._send({"jsonrpc": "2.0", "id": rid, "method": method, "params": params}, timeout, retries)
        text = body.decode("utf-8", "replace")
        try:
            if "text/event-stream" in ctype.lower():
                msgs = [json.loads(e) for e in _sse_events(text)]
            else:
                parsed = json.loads(text)
                msgs = parsed if isinstance(parsed, list) else [parsed]
        except (ValueError, RecursionError):
            raise McpError("the server's answer is not JSON-RPC")
        msgs = [m for m in msgs if isinstance(m, dict)]
        mine = [m for m in msgs if m.get("id") == rid] or msgs[-1:]   # the answer, not a notification beside it
        if not mine:
            raise McpError("the server's answer holds no JSON-RPC message")
        msg = mine[-1]
        if isinstance(msg.get("error"), dict):
            err = msg["error"]
            raise McpError("server error %s: %s" % (err.get("code"), str(err.get("message", ""))[:300]))
        if not isinstance(msg.get("result"), dict):
            raise McpError("the server's answer has no result")
        return msg["result"], headers

    def _handshake(self, timeout, retries):
        """initialize + notifications/initialized, within `timeout` in all."""
        deadline = time.monotonic() + timeout
        self._ready, self.session_id = False, None
        result, headers = self._rpc("initialize", {"protocolVersion": PROTOCOL_VERSION, "capabilities": {},
                                                   "clientInfo": CLIENT_INFO}, timeout, retries)
        self.session_id = headers.get("mcp-session-id") or None
        info = result.get("serverInfo")
        self.server_info = info if isinstance(info, dict) else {}
        self.protocol_version = str(result.get("protocolVersion") or "")
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized"}, max(0.1, deadline - time.monotonic()), retries)
        self._ready = True

    # ------------------------------------------------------------------ interface
    def probe(self):
        """True when the server answers the handshake within probe_timeout. Never raises; one attempt;
        `last_error` says why not."""
        self.last_error = ""
        try:
            self._handshake(self.probe_timeout, 0)
            return True
        except McpError as e:
            self.last_error = str(e)
        except Exception as e:                         # a probe is a yes or a no, whatever went wrong
            self.last_error = "unexpected %s" % type(e).__name__
        return False

    def call(self, name, args=None):
        """The JSON a tool returned in its text content (an object for every tool measured so far; whatever
        the tool sent when it is not). A tool outside ALLOWED → McpRefused, before any request; the network,
        a timeout, a JSON-RPC error, `isError` or a text that is not JSON → McpError."""
        if not isinstance(name, str) or name not in ALLOWED:
            raise McpRefused("tool %r is not on the allow-list (%s)" % (name, ", ".join(sorted(ALLOWED))))
        if not self._ready:
            self._handshake(self.call_timeout, self.retries)
        result, _ = self._rpc("tools/call", {"name": name, "arguments": {} if args is None else args}, self.call_timeout, self.retries)
        text = _text_of(result)
        if result.get("isError"):
            raise McpError("%s failed: %s" % (name, (text or "no detail")[:300]))
        if text is None:
            raise McpError("%s returned no text content" % name)
        try:
            return json.loads(text)
        except (ValueError, RecursionError):
            raise McpError("%s returned text that is not JSON" % name)
