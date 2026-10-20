#!/usr/bin/env python3
"""Grow PM — a small MCP client for the context engine (since v3.13.0).

Reaches a repository's MCP server (a registration with `endpoint.url`, schema provider-registration/2,
references/context-provider-protocol.md §3b) over Streamable HTTP: POST JSON-RPC 2.0, the answer is
`application/json` or `text/event-stream`, the session id from the `initialize` answer goes back in
`Mcp-Session-Id`. Stdlib only (urllib), no dependency on an MCP SDK.

What it will do, and nothing more:
  * call only the tools in `ALLOWED`; any other name raises `McpRefused` before a request is made — the
    engine reads a repository, it never writes to one. Since v3.14 the transport (`_send`, which every
    message passes) checks it too, so no path around `call()` can send another tool;
  * `probe()` is the `initialize` handshake and the `notifications/initialized` notification, once — each of
    the two within `probe_timeout` of its own (since v3.14; not one shared remainder) — never an exception,
    never a retry;
  * `call()` handshakes first when no session is open (the same `probe_timeout` per step, retried like the call);
    `call_list()` (since v3.16.0) is `call()` for a tool that answers with a list of results (`vault_search`) —
    the same allow-list, handshake, retries, deadline and `isError`, only the answer is read in every shape a
    server sends it; `call()` itself stays strict: an object, never a list;
    a network error (no connection, a timeout, a dropped connection) is retried `retries` times, a server's
    answer — an HTTP status, a JSON-RPC error, `isError` — never is;
  * keep a `deadline` when given one (since v3.14; a `time.monotonic()` moment): every request gets
    min(its own timeout, what is left), no retry starts that the deadline would not leave room for, and once it
    has passed no request is made at all — `McpError("deadline reached")`. A timeout is per socket operation
    (urllib's): it bounds a server that has gone quiet, not one that trickles bytes, nor a name lookup;
  * take as the answer only the message that carries the request's id — anything else is no answer;
  * send no header whose name is not a token of RFC 7230 or is one that steers the request itself
    (`DENIED_HEADERS`: Host, Content-Length, Transfer-Encoding, Connection);
  * follow no redirect (a header meant for one host does not travel to another) and speak only http and https;
  * keep secrets out of every message it raises or keeps: no header value, no url (it may hold credentials) —
    and out of the exception chain: an error is raised outside the `except` that caught the original, so
    `__context__` is None and a traceback prints nothing of the request.

The header a server wants (`headers_env` of the registration names an environment variable that holds
`Name: value`) is read by `headers_from_env` (`header_problem` says why a variable gives none); the value is
never stored by the engine.
"""
import http.client
import json
import os
import re
import socket
import time
import urllib.error
import urllib.parse
import urllib.request

ALLOWED = frozenset({"vault_get_note", "vault_list_by_folder", "vault_search", "brain_status", "brain_recent_changes"})
PROTOCOL_VERSION = "2025-03-26"
CLIENT_INFO = {"name": "grow-pm-ctx", "version": "1"}
MAX_BODY = 32 * 1024 * 1024                            # a note is text; more than this is not one
DENIED_HEADERS = frozenset({"host", "content-length", "transfer-encoding", "connection"})   # they steer the request itself
TOKEN = re.compile(r"[!#$%&'*+\-.^_`|~0-9A-Za-z]+\Z")  # a header name: a token of RFC 7230 (§3.2.6), ASCII only
DEADLINE = "deadline reached"


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


def _name_problem(name):
    """Why a header of this name may not be sent, or "". A name that is not a token is not repeated (whatever the
    variable holds may be part of a secret); a refused one is, by its standard spelling."""
    if not isinstance(name, str) or not TOKEN.match(name):
        return "not a valid header name"
    if name.lower() in DENIED_HEADERS:
        return "the header %s is not allowed" % "-".join(w.capitalize() for w in name.split("-"))
    return ""


def _parse_env(var):
    """(name, value) of `Name: value` in the variable, or None when it is not set or not of that shape."""
    raw = os.environ.get(var) if var else None
    name, sep, value = (raw or "").partition(":")
    name, value = name.strip(), value.strip()
    return (name, value) if sep and name and value else None


def headers_from_env(var):
    """The request header an environment variable holds: `Name: value` → {Name: value}.
    No variable, an empty one, one that is not `Name: value`, and (since v3.14) one whose name is not a token of
    RFC 7230 or is in DENIED_HEADERS → {}; `header_problem` says which."""
    got = _parse_env(var)
    return {got[0]: got[1]} if got and not _name_problem(got[0]) else {}


def header_problem(var):
    """Why `headers_from_env(var)` gives no header, in words that name the variable and never the value; "" when it
    gives one. The words for a variable that is not set are those of v3.13."""
    got = _parse_env(var)
    if not got:
        return "%s is not set (or not 'Name: value')" % var
    why = _name_problem(got[0])
    return "%s: %s" % (var, why) if why else ""


def _check_message(message):
    """The allow-list at the transport: a message that is not one JSON-RPC object (a batch could carry any call) and a
    `tools/call` whose tool is not in ALLOWED → McpRefused (no request)."""
    if not isinstance(message, dict):
        raise McpRefused("only a single JSON-RPC message is sent, not %s" % type(message).__name__)
    if message.get("method") != "tools/call":
        return
    params = message.get("params")
    name = params.get("name") if isinstance(params, dict) else None
    if not isinstance(name, str) or name not in ALLOWED:
        raise McpRefused("tool %r is not on the allow-list (%s)" % (name, ", ".join(sorted(ALLOWED))))


def _same_id(value, rid):
    """Is `value` the request id `rid`? The same int, not a bool (`true == 1` in Python) — or the same number written as a
    text (`"1"`: a server that echoes ids as strings), never another spelling of it."""
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return value == rid
    return isinstance(value, str) and value == str(rid)


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


def _texts_of(result):
    """Every text item of a tools/call result, in order — none when `content` is not a list at all
    (a server may send a number there; the caller then raises its own fixed message)."""
    content = result.get("content")
    if not isinstance(content, list):
        return []
    return [item["text"] for item in content
            if isinstance(item, dict) and item.get("type") == "text" and isinstance(item.get("text"), str)]


def _text_of(result):
    """The first text item of a tools/call result, or None."""
    texts = _texts_of(result)
    return texts[0] if texts else None


def _loads(text):
    """(True, value) for a text that is JSON, else (False, None) — no exception, so that nothing of the text
    is chained to the error a caller raises for it."""
    try:
        return True, json.loads(text)
    except (ValueError, RecursionError):
        return False, None


def _objects_of(value):
    """The objects of `value` when it is a result list: a list, an empty one or one with an object in it (an element
    that is not an object is dropped). A list with no object in it is no result list — it reads as no hits at all,
    which is not what the server said — and so is anything that is not a list: None."""
    if not isinstance(value, list):
        return None
    objects = [v for v in value if isinstance(v, dict)]
    return objects if objects or not value else None


def _listed(value):
    """`value` as a result list: a list itself, or an object whose `results` is one; else None."""
    return _objects_of(value.get("results") if isinstance(value, dict) else value)


def _result_list(result):
    """The list of results in a tools/call result, in the first shape that fits, or None:
    `structuredContent` (a list, or an object with a `results` list); one text item — such a list or object as JSON,
    or a single result (a JSON object with no `results` key); several text items, each a JSON object (one result
    each). A server that found nothing sends no text at all (a `content` list with no text item in it, and no
    `structuredContent`): an empty list — it answered. A `content` that is not a list is no answer."""
    structured = result.get("structuredContent")
    found = _listed(structured)
    if found is not None:
        return found
    if not isinstance(result.get("content"), list):
        return None
    texts = _texts_of(result)
    if not texts:
        return [] if structured is None else None
    if len(texts) == 1:
        ok, value = _loads(texts[0])
        found = _listed(value) if ok else None
        if found is None and isinstance(value, dict) and "results" not in value:
            found = [value]
        return found
    objects = [value for ok, value in map(_loads, texts) if ok and isinstance(value, dict)]
    return objects or None


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

    def __init__(self, url, headers=None, probe_timeout=3.0, call_timeout=30.0, retries=2, deadline=None):
        self.url = url
        self.headers = dict(headers or {})
        self.probe_timeout = probe_timeout
        self.call_timeout = call_timeout
        self.retries = retries
        self.deadline = deadline                       # a time.monotonic() moment no request outlasts; None: none
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
        failure = None                                 # raised below, outside the `except`: nothing is chained to it
        try:
            req = urllib.request.Request(self.url, data=json.dumps(message).encode("utf-8"), headers=hdrs, method="POST")
            with _OPENER.open(req, timeout=timeout) as resp:
                body = resp.read(MAX_BODY + 1)
                headers, ctype = resp.headers, resp.headers.get("Content-Type") or ""
        except urllib.error.HTTPError as e:            # before URLError, which it extends: the server did answer
            e.close()
            hint = " (a redirect is not followed)" if 300 <= e.code < 400 else ""
            failure = McpError("HTTP %d from the server%s" % (e.code, hint))
        except http.client.InvalidURL:
            failure = McpError("the endpoint url is not valid")
        except ValueError:                             # a header or the url that cannot be put on the wire
            failure = McpError("the request could not be built (check the endpoint url and the header)")
        except (urllib.error.URLError, OSError, http.client.HTTPException) as e:
            failure = _Network("connection failed: %s" % _reason(e))
        if failure is not None:
            raise failure       # outside the handler, so __context__ is None: the original exception (it can
                                # hold a header value or the url, e.g. urllib's "Invalid header value b'...'") is dropped
        if len(body) > MAX_BODY:
            raise McpError("the response is too large (over %d bytes)" % MAX_BODY)
        return headers, ctype, body

    def _left(self):
        """Seconds left before the deadline, or None without one."""
        return None if self.deadline is None else self.deadline - time.monotonic()

    def _within(self, timeout):
        """`timeout`, cut to what the deadline leaves; nothing left → McpError("deadline reached")."""
        left = self._left()
        if left is None:
            return timeout
        if left <= 0:
            raise McpError(DEADLINE)
        return min(timeout, left)

    def _send(self, message, timeout, retries):
        """_post with the allow-list, the header names, the deadline and the retries: only a failure of the connection is
        tried again, and only when the deadline leaves room for the pause before it."""
        _check_message(message)
        refusal = next((why for why in map(_name_problem, self.headers) if why), "")
        if refusal:
            raise McpError("a request header cannot be sent: %s" % refusal)
        attempt = 0
        while True:
            failure = None
            try:
                return self._post(message, self._within(timeout))
            except _Network as e:
                failure = e
            attempt += 1
            pause = self.BACKOFF * attempt
            left = self._left()
            late = attempt <= retries and left is not None and left <= pause
            if attempt > retries or late:
                notes = (["after %d attempts" % attempt] if attempt > 1 else []) + ([DEADLINE] if late else [])
                raise McpError("%s (%s)" % (failure, "; ".join(notes)) if notes else str(failure))
            time.sleep(pause)

    def _rpc(self, method, params, timeout, retries):
        """A request → (its result object, response headers)."""
        self._ids += 1
        rid = self._ids
        headers, ctype, body = self._send({"jsonrpc": "2.0", "id": rid, "method": method, "params": params}, timeout, retries)
        text = body.decode("utf-8", "replace")
        if "text/event-stream" in ctype.lower():           # an event that is empty or not JSON (a priming event, a ping) is skipped
            msgs = [v for ok, v in (_loads(e) for e in _sse_events(text)) if ok]
        else:
            ok, parsed = _loads(text)
            if not ok:
                raise McpError("the server's answer is not JSON-RPC")
            msgs = parsed if isinstance(parsed, list) else [parsed]
        msgs = [m for m in msgs if isinstance(m, dict)]
        if not msgs:
            raise McpError("the server's answer holds no JSON-RPC message")
        mine = [m for m in msgs if _same_id(m.get("id"), rid)]     # the answer, not a notification beside it
        if not mine:                                    # nor another request's answer, nor an error that names no request
            raise McpError("no response with id %d in the server's answer" % rid)
        msg = mine[-1]
        if isinstance(msg.get("error"), dict):
            err = msg["error"]
            raise McpError("server error %s: %s" % (err.get("code"), str(err.get("message", ""))[:300]))
        if not isinstance(msg.get("result"), dict):
            raise McpError("the server's answer has no result")
        return msg["result"], headers

    def _handshake(self, retries):
        """initialize + notifications/initialized, each within probe_timeout of its own (and the deadline)."""
        self._ready, self.session_id = False, None
        result, headers = self._rpc("initialize", {"protocolVersion": PROTOCOL_VERSION, "capabilities": {},
                                                   "clientInfo": CLIENT_INFO}, self.probe_timeout, retries)
        self.session_id = headers.get("mcp-session-id") or None
        info = result.get("serverInfo")
        self.server_info = info if isinstance(info, dict) else {}
        self.protocol_version = str(result.get("protocolVersion") or "")
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized"}, self.probe_timeout, retries)
        self._ready = True

    # ------------------------------------------------------------------ interface
    def probe(self):
        """True when the server answers the handshake within probe_timeout a step (and the deadline). Never raises;
        one attempt; `last_error` says why not."""
        self.last_error = ""
        try:
            self._handshake(0)
            return True
        except McpError as e:
            self.last_error = str(e)
        except Exception as e:                         # a probe is a yes or a no, whatever went wrong
            self.last_error = "unexpected %s" % type(e).__name__
        return False

    def _tool_result(self, name, args):
        """The `result` of a tools/call of an allowed tool — what `call` and `call_list` share. A tool outside ALLOWED →
        McpRefused, before any request; the network, a timeout, a JSON-RPC error and `isError` → McpError."""
        if not isinstance(name, str) or name not in ALLOWED:
            raise McpRefused("tool %r is not on the allow-list (%s)" % (name, ", ".join(sorted(ALLOWED))))
        if not self._ready:
            self._handshake(self.retries)
        result, _ = self._rpc("tools/call", {"name": name, "arguments": {} if args is None else args}, self.call_timeout, self.retries)
        if result.get("isError"):
            raise McpError("%s failed: %s" % (name, (_text_of(result) or "no detail")[:300]))
        return result

    def call(self, name, args=None):
        """The JSON object a tool returned in its text content. A tool outside ALLOWED → McpRefused, before any
        request; the network, a timeout, a JSON-RPC error, `isError`, a text that is not JSON or JSON that is not
        an object (a list, null, a number, a string) → McpError."""
        result = self._tool_result(name, args)
        text = _text_of(result)
        if text is None:
            raise McpError("%s returned no text content" % name)
        ok, value = _loads(text)
        if not ok:
            raise McpError("%s returned text that is not JSON" % name)
        if not isinstance(value, dict):
            raise McpError("%s returned JSON that is not an object" % name)
        return value

    def call_list(self, name, args=None):
        """The list of results a tool returned (`vault_search`), as a list of objects — the same allow-list, handshake,
        retries, deadline and errors as `call`. The first of these shapes that fits: `structuredContent` (a list, or an
        object with a `results` list); one text item holding such a list or object as JSON, or one result (a JSON
        object with no `results` key); several text items, each a JSON object (one result each). An element that is
        not an object is dropped; an empty list is a list, and so is an answer with no text in it (nothing found).
        No shape fits → McpError("<name> returned no list of results"), a message that carries nothing of the answer."""
        found = _result_list(self._tool_result(name, args))
        if found is None:
            raise McpError("%s returned no list of results" % name)
        return found
