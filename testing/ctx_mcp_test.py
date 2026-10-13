#!/usr/bin/env python3
"""TC-ctx-3130-mcp — scripts/ctx_mcp.py, the stdlib MCP client with an allow-list, and `ctx repo status` (since v3.13.0).

The fictional "Zorg" on a fake Streamable-HTTP MCP server (testing/mcp_fake.py: 127.0.0.1, port 0, a daemon
thread; JSON and SSE answers, a session id, recorded requests). Covers the handshake probe, calls in both
answer formats, the session id going back, the allow-list refusing before any request, errors (isError,
JSON-RPC error, HTTP status, timeout, dropped connection) and retries on network errors only, no redirects
and no secrets in messages, `headers_from_env`, and the command: reachable yes / no for an MCP repository
and for a folder, the header from the environment, the version on the source. No real server, no real data.
Semantics: references/context-provider-protocol.md. Stdlib only; run from the repo root.
"""
import json, os, socket, subprocess, sys, tempfile, threading, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "testing"))
os.environ["NO_PROXY"] = "127.0.0.1,localhost"          # the fake is local; a proxy in the environment must not see it
os.environ["no_proxy"] = "127.0.0.1,localhost"
import ctx_mcp as cm  # noqa: E402
from ctx_mcp import McpClient, McpError, McpRefused  # noqa: E402
from mcp_fake import FakeMcp  # noqa: E402

CTX = os.path.join(ROOT, "scripts", "ctx.py")
FIX = os.path.join(ROOT, "testing", "fixtures", "ctx")
BLOCKS_PATH = "Growth/_System/context-blocks.md"
fails = 0
cm.McpClient.BACKOFF = 0.0                                # no pause between retries in tests


def check(name, cond, detail=""):
    global fails
    fails += not cond
    print(("✅" if cond else "❌"), name, ("" if cond else "-> " + str(detail)[:700]))


def read(*parts):
    return open(os.path.join(*parts), encoding="utf-8", newline="").read()


def raises(fn, *exc):
    """The exception fn raises (one of exc), or None."""
    try:
        fn()
    except exc as e:
        return e
    return None


def calls(fake):
    return fake.methods().count("tools/call")


class Closer:
    """A listener that accepts every connection and closes it unanswered, counting them."""

    def __init__(self):
        self.sock = socket.socket()
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(16)
        self.url = "http://127.0.0.1:%d/mcp" % self.sock.getsockname()[1]
        self.n = 0
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        while True:
            try:
                conn, _ = self.sock.accept()
            except OSError:
                return
            self.n += 1
            conn.close()

    def wait(self, want):
        """True when exactly `want` connections were made (after a moment for the last to arrive)."""
        time.sleep(0.2)
        return self.n == want

    def close(self):
        self.sock.close()


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


# --- the module's surface
check("ALLOWED is exactly the five tools the engine may call",
      cm.ALLOWED == frozenset({"vault_get_note", "vault_list_by_folder", "vault_search", "brain_status", "brain_recent_changes"})
      and isinstance(cm.ALLOWED, frozenset), cm.ALLOWED)
check("McpRefused is an McpError, McpError an Exception", issubclass(McpRefused, McpError) and issubclass(McpError, Exception))

# --- headers_from_env
os.environ.pop("ZORG_HDR", None)
check("headers_from_env: no variable → {}", cm.headers_from_env("ZORG_HDR") == {})
os.environ["ZORG_HDR"] = "X-Token: zorg"
check("headers_from_env: 'Name: value' → {Name: value}", cm.headers_from_env("ZORG_HDR") == {"X-Token": "zorg"},
      cm.headers_from_env("ZORG_HDR"))
os.environ["ZORG_HDR"] = "Authorization: Bearer a:b=="
check("headers_from_env: the value may hold colons and spaces", cm.headers_from_env("ZORG_HDR") == {"Authorization": "Bearer a:b=="},
      cm.headers_from_env("ZORG_HDR"))
os.environ["ZORG_HDR"] = "no colon here"
check("headers_from_env: a value that is not 'Name: value' → {}", cm.headers_from_env("ZORG_HDR") == {})
os.environ["ZORG_HDR"] = "X-Token:   "
check("headers_from_env: an empty value → {}", cm.headers_from_env("ZORG_HDR") == {})
check("headers_from_env: an empty variable name → {}", cm.headers_from_env("") == {})
os.environ["ZORG_HDR"] = "X-Token: zorg"

# --- probe
check("probe false on a dead port", McpClient("http://127.0.0.1:9/mcp", probe_timeout=1).probe() is False)
with FakeMcp() as fake:
    c = McpClient(fake.url)
    check("probe true on a live server", c.probe() is True and fake.seen[0]["method"] == "initialize", fake.methods())
    check("probe is the initialize handshake and the initialized notification, nothing else",
          fake.methods() == ["initialize", "notifications/initialized"], fake.methods())
    init = fake.seen[0]["body"]
    check("initialize: JSON-RPC 2.0, protocol 2025-03-26, client info, JSON and event-stream accepted",
          init["jsonrpc"] == "2.0" and init["params"]["protocolVersion"] == "2025-03-26"
          and init["params"]["clientInfo"]["name"] and "id" in init
          and fake.seen[0]["headers"].get("Content-Type") == "application/json"
          and "application/json" in fake.seen[0]["headers"].get("Accept")
          and "text/event-stream" in fake.seen[0]["headers"].get("Accept"), fake.seen[0])
    check("the notification has no id and carries the session id",
          "id" not in fake.seen[1]["body"] and fake.seen[1]["headers"].get("Mcp-Session-Id") == "s-1", fake.seen[1])
    check("the server's name and protocol are kept", c.server_info.get("name") == "zorg-growth-mcp"
          and c.protocol_version == "2025-03-26", (c.server_info, c.protocol_version))
    check("probe twice → a fresh handshake each time", c.probe() is True and fake.methods().count("initialize") == 2,
          fake.methods())

with FakeMcp(require_headers={"X-Token": "tok-9f3a"}) as fake:
    c = McpClient(fake.url)
    check("probe false when the server answers 401, and says why", c.probe() is False and "401" in c.last_error, c.last_error)
with FakeMcp(mode="sse") as fake:
    check("probe true on an SSE server", McpClient(fake.url).probe() is True, fake.methods())

# --- calls in JSON
with FakeMcp() as fake:
    c = McpClient(fake.url)
    note = c.call("vault_get_note", {"path": BLOCKS_PATH})
    check("JSON response", note["content"].startswith("<!-- zorg-growth:begin") or "<!-- zorg-growth:begin" in note["content"], note)
    check("the note comes back as the server's JSON", note["path"] == BLOCKS_PATH and note["title"] == "context-blocks"
          and set(note) == {"path", "title", "frontmatter", "tags", "headings", "content", "outgoing_links"}, note)
    check("call without a probe handshakes first, once", fake.methods() == ["initialize", "notifications/initialized", "tools/call"],
          fake.methods())
    check("session id is sent back", fake.seen[-1]["headers"].get("Mcp-Session-Id") == "s-1", fake.seen[-1]["headers"])
    check("tools/call carries the tool name and its arguments",
          fake.seen[-1]["body"]["params"] == {"name": "vault_get_note", "arguments": {"path": BLOCKS_PATH}}, fake.seen[-1]["body"])
    c.call("vault_get_note", {"path": BLOCKS_PATH})
    check("a second call reuses the session", fake.methods().count("initialize") == 1 and calls(fake) == 2, fake.methods())
    missing = c.call("vault_get_note", {"path": "Growth/nope.md"})
    check("a path the server does not have comes back as its {error} dict, as is",
          set(missing) == {"error"} and "nope.md" in missing["error"], missing)
    fake.handlers["brain_recent_changes"] = lambda args: ({"args": args}, False)
    check("an absent arguments dict is an empty one", c.call("brain_recent_changes") == {"args": {}})

# --- calls in SSE
for noise, after in ((True, False), (False, False), (True, True)):
    with FakeMcp(mode="sse", sse_noise=noise, sse_after=after) as fake:
        c_sse = McpClient(fake.url)
        got = c_sse.call("vault_get_note", {"path": BLOCKS_PATH})
        check("SSE response (noise before=%s, a notification after=%s)" % (noise, after),
              got["path"].endswith(".md") and "zorg-growth:begin" in got["content"], got)
        check("…the session id goes back there too", fake.seen[-1]["headers"].get("Mcp-Session-Id") == "s-1")

# --- the allow-list
with FakeMcp() as fake:
    c = McpClient(fake.url)
    before = len(fake.seen)
    refused = {}
    for name in ("vault_write_note", "vault_delete_note", "vault_create_note", "brain_write", "tools/list", "",
                 "VAULT_GET_NOTE", "vault_get_note ", "vault_get_note\n", None, 7, ["vault_get_note"]):
        refused[repr(name)] = raises(lambda n=name: c.call(n, {"path": "x"}), McpError)
    check("a tool outside the allow-list is refused before any request",
          all(type(e) is McpRefused for e in refused.values()) and len(fake.seen) == before,
          {k: type(v).__name__ for k, v in refused.items()})
    check("…and the client did not even handshake", fake.methods() == [], fake.methods())
    check("every allowed tool passes the gate (an unknown one on the fake is an McpError, not McpRefused)",
          all(type(raises(lambda n=n: c.call(n, {}), McpError)) is McpError for n in ("vault_search", "vault_list_by_folder", "brain_status", "brain_recent_changes")),
          [type(raises(lambda n=n: c.call(n, {}), McpError)).__name__ for n in cm.ALLOWED])

# --- errors
with FakeMcp() as fake:
    c = McpClient(fake.url)
    fake.handlers["vault_search"] = lambda args: ("index offline", True)
    n0 = calls(fake)
    err = raises(lambda: c.call("vault_search", {"query": "x"}), McpError)
    check("isError → McpError", err is not None and type(err) is McpError and "index offline" in str(err), repr(err))
    check("…and not retried", calls(fake) - n0 == 1, calls(fake) - n0)
    fake.handlers["vault_search"] = lambda args: ("plain words, not JSON", False)
    err = raises(lambda: c.call("vault_search", {"query": "x"}), McpError)
    check("a result whose text is not JSON → McpError", err is not None and "JSON" in str(err), repr(err))
    fake.handlers["vault_search"] = lambda args: ([{"path": "a.md"}, {"path": "b.md"}], False)
    check("any JSON the tool returned is passed on (a list too)", c.call("vault_search", {}) == [{"path": "a.md"}, {"path": "b.md"}])
    fake.handlers["brain_status"] = lambda args: ("", False)
    err = raises(lambda: c.call("brain_status", {}), McpError)
    check("an empty text → McpError", err is not None, repr(err))

with FakeMcp(rpc_error="no such index") as fake:
    c = McpClient(fake.url)
    err = raises(lambda: c.call("vault_get_note", {"path": "a"}), McpError)
    check("a JSON-RPC error object → McpError with its message, not retried",
          err is not None and "no such index" in str(err) and calls(fake) == 1, (repr(err), calls(fake)))

with FakeMcp(fail_status=500) as fake:
    c = McpClient(fake.url)
    err = raises(lambda: c.call("vault_get_note", {"path": "a"}), McpError)
    check("an HTTP error status → McpError naming the status, and no retry (the server did answer)",
          err is not None and "500" in str(err) and calls(fake) == 1, (repr(err), calls(fake)))

with FakeMcp(delay=1.2) as fake:
    c = McpClient(fake.url, call_timeout=0.3, retries=0)
    t0 = time.time()
    err = raises(lambda: c.call("vault_get_note", {"path": "a"}), McpError)
    check("a call that outlasts call_timeout → McpError, and it does not wait for the server",
          err is not None and "timed out" in str(err) and time.time() - t0 < 1.0, (repr(err), time.time() - t0))

# --- retries: on a network error only
with FakeMcp(drop=1) as fake:
    c = McpClient(fake.url)
    got = c.call("vault_get_note", {"path": BLOCKS_PATH})
    check("a dropped connection is retried and the call succeeds", got["path"] == BLOCKS_PATH and calls(fake) == 2, calls(fake))
with FakeMcp(drop=-1) as fake:
    err = raises(lambda: McpClient(fake.url).call("vault_get_note", {"path": "a"}), McpError)
    check("retries=2 → three attempts, then McpError", err is not None and calls(fake) == 3, (repr(err), calls(fake)))
    n0 = calls(fake)
    err = raises(lambda: McpClient(fake.url, retries=0).call("vault_get_note", {"path": "a"}), McpError)
    check("retries=0 → one attempt", err is not None and calls(fake) - n0 == 1, calls(fake) - n0)
    n0 = calls(fake)
    err = raises(lambda: McpClient(fake.url, retries=1).call("vault_get_note", {"path": "a"}), McpError)
    check("retries=1 → two attempts", err is not None and calls(fake) - n0 == 2, calls(fake) - n0)
err = raises(lambda: McpClient("http://127.0.0.1:9/mcp", call_timeout=1, retries=1).call("vault_get_note", {"path": "a"}), McpError)
check("a dead port → McpError on a call", err is not None and type(err) is McpError, repr(err))
closer = Closer()
check("probe makes one attempt (its 3 s budget is not multiplied)",
      McpClient(closer.url, retries=2).probe() is False and closer.wait(1), closer.n)
closer.n = 0
err = raises(lambda: McpClient(closer.url, retries=2).call("vault_get_note", {"path": "a"}), McpError)
check("the handshake of a call is retried like the call", err is not None and closer.wait(3), closer.n)
closer.close()

# --- no redirects, only http(s), no secrets in messages
for code in (301, 302, 303, 307, 308):
    with FakeMcp() as elsewhere, FakeMcp(redirect_to=None, redirect_status=code) as fake:
        fake.redirect_to = elsewhere.url
        c = McpClient(fake.url, headers={"X-Token": "tok-9f3a"})
        ok = c.probe()
        err = raises(lambda: c.call("vault_get_note", {"path": "a"}), McpError)
        check("a %d is not followed: probe false, call McpError, the other server saw nothing" % code,
              ok is False and err is not None and str(code) in (c.last_error + str(err)) and elsewhere.seen == [],
              (ok, repr(err), elsewhere.seen))
for url in ("file:///etc/hosts", "ftp://127.0.0.1/x", "gopher://127.0.0.1/x", "127.0.0.1:9/mcp", "", "http://[::1/mcp"):
    c = McpClient(url)
    check("only http and https endpoints: %r" % url, c.probe() is False
          and raises(lambda: c.call("vault_get_note", {"path": "a"}), McpError) is not None, c.last_error)

with FakeMcp(drop=-1, require_headers={}) as fake:
    secret = "tok-9f3a"
    c = McpClient(fake.url, headers={"X-Token": secret}, retries=1)
    err = raises(lambda: c.call("vault_get_note", {"path": "a"}), McpError)
    check("a network failure's message does not carry a header value or the url", err is not None and secret not in str(err)
          and fake.url not in str(err), repr(err))
with FakeMcp(require_headers={"X-Token": "different"}) as fake:
    secret = "tok-9f3a"
    c = McpClient(fake.url, headers={"X-Token": secret})
    err = raises(lambda: c.call("vault_get_note", {"path": "a"}), McpError)
    c.probe()
    check("an HTTP failure's message does not carry a header value", err is not None and "401" in str(err)
          and secret not in str(err) and secret not in c.last_error, (repr(err), c.last_error))
c = McpClient("http://127.0.0.1:9/mcp", headers={"X-Token": "bad\r\nX-Evil: 1"})
err = raises(lambda: c.call("vault_get_note", {"path": "a"}), McpError)
check("a header that cannot be sent is an McpError that does not repeat it, and probe is just false",
      err is not None and "X-Evil" not in str(err) and c.probe() is False and "X-Evil" not in c.last_error, (repr(err), c.last_error))
c = McpClient("http://zorgpass9@127.0.0.1:%d/mcp?tok=zorgtok7" % free_port())
err = raises(lambda: c.call("vault_get_note", {"path": "a"}), McpError)
c.probe()
check("a url with credentials is not repeated in a message", err is not None and "zorgpass9" not in str(err)
      and "zorgtok7" not in str(err) and "zorgpass9" not in c.last_error and "zorgtok7" not in c.last_error, (repr(err), c.last_error))

# --- a response bigger than the cap
big = {"Growth/big.md": "x" * 5000}
with FakeMcp(tree=big) as fake:
    old, cm.MAX_BODY = cm.MAX_BODY, 1500
    try:
        c = McpClient(fake.url)
        small_ok = c.probe()
        err = raises(lambda: c.call("vault_get_note", {"path": "Growth/big.md"}), McpError)
    finally:
        cm.MAX_BODY = old
    check("a response over MAX_BODY → McpError (the handshake still fits)", small_ok is True and err is not None
          and "too large" in str(err), (small_ok, repr(err)))

# --- the header from the environment reaches the server
with FakeMcp(require_headers={"X-Token": "zorg"}) as fake:
    hdr = cm.headers_from_env("ZORG_HDR")
    got = McpClient(fake.url, headers=hdr).call("vault_get_note", {"path": BLOCKS_PATH})
    check("header from env", fake.seen[-1]["headers"].get("X-Token") == "zorg" and got["path"] == BLOCKS_PATH,
          fake.seen[-1]["headers"])
    check("…on every request of the session", all(s["headers"].get("X-Token") == "zorg" for s in fake.seen), len(fake.seen))
    check("…and without it the server says no", raises(lambda: McpClient(fake.url).call("vault_get_note", {"path": "a"}), McpError) is not None)


# --- ctx repo status
CORE_V1 = """schema: provider-registration/1
id: zorg-core
title: Zorg shared product core
kind: bundle
contract: vault/v1
authority: org
mode: snapshot
access: vpn
paths:
  - {core}
index: ""
synced_at: 2026-09-15
source_version: core 0.2, bundle 0.4.0
team: team-alpha
role: pm
jira_write: own
status: active
"""

MCP_V2 = """schema: provider-registration/2
id: {id}
title: Zorg Growth
kind: mcp
contract: vault/v1
authority: team
mode: live
access: open
endpoint:
  url: {url}
  root: "ZorgGrowth/"
  headers_env: ZORG_GROWTH_MCP_HEADERS
blocks_file: Growth/_System/context-blocks.md
blocks_source: mcp
team: team-alpha
role: pm
status: active
synced_at: 2026-10-01
source_version: growth 1.4
"""


class Env:
    """A temp HOME with the typical context, a temp vault `Notes` and its providers folder."""

    def __init__(self, d):
        self.home = os.path.join(d, "home")
        self.vault = os.path.join(d, "vault")
        self.core = os.path.join(d, "ZorgCore")
        self.providers = os.path.join(self.vault, "Notes", "_System", "providers")
        os.makedirs(os.path.join(self.home, ".grow-pm"))
        os.makedirs(self.providers)
        os.makedirs(self.core)
        self.text = read(FIX, "typical.md").replace("{{VAULT}}", self.vault)
        self.ctx = os.path.join(self.home, ".grow-pm", "local-context.md")
        open(self.ctx, "w", encoding="utf-8", newline="").write(self.text)

    def reg(self, name, body):
        open(os.path.join(self.providers, name + ".yaml"), "w", encoding="utf-8", newline="").write(
            body.replace("{core}", self.core))

    def run(self, *args, **env_extra):
        env = dict(os.environ)
        env.pop("GROW_PM_CONTEXT_PATH", None)
        env.pop("ZORG_GROWTH_MCP_HEADERS", None)
        env.update(env_extra)
        p = subprocess.run([sys.executable, CTX] + list(args) + ["--home", self.home, "--context", self.ctx],
                           capture_output=True, text=True, env=env, timeout=120)
        lines = [l for l in p.stdout.splitlines() if l.strip()]
        try:
            result = json.loads(lines[-1][len("CTX_RESULT "):]) if lines and lines[-1].startswith("CTX_RESULT ") else None
        except ValueError:
            result = None
        return p.returncode, p.stdout + p.stderr, result


def block(out, rid):
    """The lines of one repository in the status output: its header line and the indented ones after it."""
    lines, got = out.splitlines(), []
    for i, l in enumerate(lines):
        if l.startswith(rid):
            got = [l]
            for m in lines[i + 1:]:
                if not m.startswith(" "):
                    break
                got.append(m)
            break
    return "\n".join(got)


with tempfile.TemporaryDirectory() as d, FakeMcp(require_headers={"X-Token": "tok-9f3a"}) as fake:
    e = Env(d)
    rc, out, res = e.run("repo", "status")
    check("ctx repo status with none says so", rc == 0 and res is not None and res["repos"] == [] and "no repositories" in out, (rc, out))

    dead_url = "http://127.0.0.1:%d/mcp" % free_port()
    e.reg("zorg-core", CORE_V1)
    e.reg("zorg-growth", MCP_V2.format(id="zorg-growth", url=fake.url))
    e.reg("zorg-dead", MCP_V2.format(id="zorg-dead", url=dead_url))
    good = {"ZORG_GROWTH_MCP_HEADERS": "X-Token: tok-9f3a"}
    t0 = time.time()
    rc, out, res = e.run("repo", "status", **good)
    took = time.time() - t0
    g, dd, cc_ = block(out, "zorg-growth"), block(out, "zorg-dead"), block(out, "zorg-core")
    check("ctx repo status reports reachable and unreachable", rc == 0 and "zorg-growth" in out and "reachable yes" in g
          and "reachable no" in dd, (rc, out))
    check("a folder repository is reachable when its folder is there", "reachable yes" in cc_, cc_)
    check("the header named by headers_env is read from the environment and sent", "reachable yes" in g
          and any(s["headers"].get("X-Token") == "tok-9f3a" for s in fake.seen), g)
    check("the secret never reaches the output", "tok-9f3a" not in out and "tok-9f3a" not in json.dumps(res), out)
    check("the dead one says why, in the same line", "reachable no (" in dd and "refused" in dd.lower(), dd)
    check("version on source vs base: the registration's version, the base is a dash until blocks are kept",
          "growth 1.4" in g and "base" in g and "—" in g.splitlines()[-1] and "core 0.2" in cc_, g)
    check("each line names the kind and the endpoint without credentials", "mcp" in g.splitlines()[0] and fake.url in g.splitlines()[0]
          and "bundle" in cc_.splitlines()[0], g)
    check("CTX_RESULT is last and carries the verdicts", out.splitlines()[-1].startswith("CTX_RESULT ") and res["command"] == "repo"
          and res["action"] == "status" and res["ok"] is True
          and {r["id"]: r["reachable"] for r in res["repos"]} == {"zorg-core": True, "zorg-growth": True, "zorg-dead": False}, res)
    by_id = {r["id"]: r for r in res["repos"]}
    check("…with the reason, the registration's version and an empty base",
          all(k in by_id["zorg-growth"] for k in ("id", "kind", "status", "url", "reachable", "reason", "source_version", "base_version"))
          and by_id["zorg-dead"]["reason"] and by_id["zorg-growth"]["source_version"] == "growth 1.4"
          and by_id["zorg-growth"]["base_version"] is None and by_id["zorg-growth"]["reason"] == "", res["repos"])
    check("a dead port does not stall the command", took < 8, took)

    rc, out, res = e.run("repo", "status", "zorg-growth", "--json", **good)
    check("an id narrows it to that repository, --json is accepted and the result line stays last",
          rc == 0 and [r["id"] for r in res["repos"]] == ["zorg-growth"] and "zorg-core" not in out
          and out.splitlines()[-1].startswith("CTX_RESULT "), (rc, out))
    rc, out, res = e.run("repo", "status", "zorg-nope", **good)
    check("an unknown id is a usage error naming the way out", rc == 3 and res is not None and res["ok"] is False
          and "zorg-nope" in out and "repo list" in out, (rc, out))

    rc, out, res = e.run("repo", "status", "zorg-growth")
    gn = block(out, "zorg-growth")
    check("without the header variable the server's 401 is a reachable no that names the variable (not a value)",
          rc == 0 and "reachable no" in gn and "401" in gn and "ZORG_GROWTH_MCP_HEADERS" in gn and "is not set" in gn, gn)

    e.reg("zorg-gone", CORE_V1.replace("id: zorg-core", "id: zorg-gone").replace("{core}", os.path.join(d, "no-such-core")))
    rc, out, res = e.run("repo", "status", "zorg-gone")
    check("a folder that is not there is a reachable no", rc == 0 and "reachable no" in block(out, "zorg-gone")
          and "not found" in block(out, "zorg-gone"), out)
    os.remove(os.path.join(e.providers, "zorg-gone.yaml"))

    e.reg("zorg-creds", MCP_V2.format(id="zorg-creds", url="http://zorguser:zorgpass9@127.0.0.1:%d/mcp?tok=zorgtok7" % free_port()))
    rc, out, res = e.run("repo", "status", "zorg-creds")
    check("an endpoint with credentials in its url is shown without them (userinfo and query)",
          rc == 0 and "zorgpass9" not in out and "zorgtok7" not in out and "zorguser" not in out
          and "zorgpass9" not in json.dumps(res) and "zorgtok7" not in json.dumps(res), out)
    os.remove(os.path.join(e.providers, "zorg-creds.yaml"))

    e.reg("zorg-bare", "id: zorg-bare\nkind: mcp\n")
    rc, out, res = e.run("repo", "status", "zorg-bare")
    check("an mcp registration without an endpoint url is a reachable no that says so",
          "reachable no" in block(out, "zorg-bare") and "endpoint" in block(out, "zorg-bare"), out)
    os.remove(os.path.join(e.providers, "zorg-bare.yaml"))

    e.reg("zorg-growth", MCP_V2.format(id="zorg-growth", url=fake.url).replace("status: active", "status: paused"))
    rc, out, res = e.run("repo", "status", "zorg-growth", **good)
    check("a paused repository is named as paused", "(paused)" in block(out, "zorg-growth") and res["repos"][0]["status"] == "paused", out)

    e.reg("zorg-broken", "id: zorg-broken\nendpoint:\n  nested:\n    deeper: 1\n")
    rc, out, res = e.run("repo", "status", **good)
    check("an unreadable registration is named, as in `repo list`", rc == 0 and "zorg-broken.yaml" in out
          and res.get("unreadable") and "zorg-broken.yaml" in res["unreadable"][0]["file"], out)
    os.remove(os.path.join(e.providers, "zorg-broken.yaml"))

    check("repo status is a reading command: nothing is written", not os.path.exists(os.path.join(e.vault, "Notes", "_System", "context"))
          and not os.path.exists(os.path.join(e.home, ".grow-pm", "snapshots")) and sorted(os.listdir(os.path.join(e.home, ".grow-pm"))) == ["local-context.md"],
          os.listdir(os.path.join(e.home, ".grow-pm")))
    check("…and the engine only called what the allow-list names (the status only handshakes)",
          set(s["method"] for s in fake.seen) <= {"initialize", "notifications/initialized"}, set(s["method"] for s in fake.seen))

print("RESULT:", "GREEN ✅" if not fails else "RED ❌", "(%d failed)" % fails)
sys.exit(1 if fails else 0)
