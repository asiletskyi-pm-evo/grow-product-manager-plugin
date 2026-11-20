#!/usr/bin/env python3
"""TC-ctx-491-endpoints — scripts/ctx_endpoints.py: the engine reaches only the provider addresses you approved (since v4.9.1).

The finding of the 2026-11-20 audit: a provider registration (`{vault}/{plugin_folder}/_System/providers/<id>.yaml`)
named `endpoint.url` and `endpoint.headers_env`, and the engine sent the header the variable holds — and every search
query — to that url without a check. Covered here, on temp homes and the fictional "Zorg" only:

1. the address as the engine reads it: scheme, host, port and path; no credentials, no query, no fragment kept; one
   that is not plainly an address is none;
2. the transport (`ctx_mcp.transport_problem`, checked at the client's transport too): https, and http only to this
   computer (127.0.0.1, ::1, localhost) — a remote http address gets no request at all, header or not;
3. the trust file `~/.grow-pm/trust/providers.json`: 0600 in a 0700 folder, never a header value, never credentials;
   one that cannot be read refuses everything and is never rewritten by a first run;
4. the first run after the update (R37): every registration with an address already there is trusted, once, one line
   each — a remote http one is not, and is named; the file holds `seeded_at`; an empty list is a file; a registration
   still downloading puts the first run off;
5. the verdict: the pair «address + variable name» you approved, matched with the id; anything else — a new id, another
   address, another variable — gets nothing (R36: an address with no variable needs approval as well);
6. `client_for`, the one way to a client: the approved address and the header from the environment, or `Untrusted`
   before the factory is called; a home a registration file could plant is no home;
7. `approve` / `revoke` (`ctx provider trust|untrust`): the id must be kebab-case, the variable a plain name;
8. a private registration is read before a vault's: a vault file never shadows yours, and two files of one id with
   different addresses are named.

Stdlib only; run from the repo root.
"""
import json, os, stat, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "testing"))
os.environ["NO_PROXY"] = "127.0.0.1,localhost"
os.environ["no_proxy"] = "127.0.0.1,localhost"
import ctx_common as cc  # noqa: E402
import ctx_mcp as cm  # noqa: E402
import ctx_repos as crp  # noqa: E402
import ctx_endpoints as ce  # noqa: E402
from mcp_fake import FakeMcp  # noqa: E402

cm.McpClient.BACKOFF = 0.0
fails = 0
NOW = "2026-11-20T09:00:00+02:00"
SECRET = "tok-zorg-9f3a51"
os.environ["ZORG_MCP_HEADERS"] = "X-Token: " + SECRET
os.environ["ZORG_OTHER_HEADERS"] = "X-Token: other-77"


def check(name, cond, detail=""):
    global fails
    fails += not cond
    print(("✅" if cond else "❌"), name, ("" if cond else "-> " + str(detail)[:700]))


def repo(rid, url, var="", home=None, **kw):
    reg = {"id": rid, "kind": "mcp", "endpoint": {"url": url, "root": "", "headers_env": var}}
    reg.update(kw)
    r = crp.normalise(reg)
    if home is not None:
        r["_trust_home"] = ce.Home(home)
    return r


def new_home(d, name="home"):
    h = os.path.join(d, name)
    os.makedirs(os.path.join(h, ".grow-pm"))
    return h


def raw(home):
    return open(ce.trust_file(home), "rb").read().decode("utf-8")


class Factory:
    """A client factory that records its calls and never touches the network."""

    def __init__(self):
        self.calls = []

    def __call__(self, url, headers=None, **kw):
        self.calls.append((url, dict(headers or {}), kw))
        return object()


# 1. the address -------------------------------------------------------------------------------------------------
p = ce.parse("HTTPS://User:Pa55@Context.Zorg.EXAMPLE:443/mcp?key=abc#frag")
check("1.1 an address: scheme and host lower-cased, the default port dropped, the path kept",
      p is not None and p.normal == "https://context.zorg.example/mcp" and p.origin == "https://context.zorg.example", p)
check("1.2 …no credentials, query or fragment in what is kept or shown",
      p is not None and not any(s in p.normal + p.origin for s in ("User", "Pa55", "key=abc", "frag")), p)
check("1.3 …the request goes to the same address with its query, never with the credentials",
      p is not None and p.request_url == "https://context.zorg.example/mcp?key=abc", p and p.request_url)
check("1.4 an empty path is «/», a port that is not the default stays",
      ce.parse("https://zorg.example:8443").normal == "https://zorg.example:8443/")
check("1.5 IPv6 loopback keeps its brackets", ce.parse("http://[::1]:9000/mcp").normal == "http://[::1]:9000/mcp")
BAD = ["", " https://zorg.example/", "https://zorg.example/\n", "https://zorg.example\\@evil.example/",
       "https://zorg .example/", "https://зорг.example/", "https://zorg.example:99999/", "https://zorg.example:x/",
       "https:///mcp", "ftp://zorg.example/", "zorg.example/mcp", "https://zorg%2eexample/", "https://-zorg.example/",
       None, 42]
check("1.6 what is not plainly an address is none (spaces, controls, a backslash, non-ASCII, a bad port, no host, "
      "another scheme, percent-encoding)", all(ce.parse(u) is None for u in BAD), [u for u in BAD if ce.parse(u)])

# 2. the transport -----------------------------------------------------------------------------------------------
OK = ["https://context.zorg.example/mcp", "http://127.0.0.1:9/mcp", "http://localhost:8080/mcp", "http://[::1]/mcp",
      "HTTP://LOCALHOST/mcp"]
NO = ["http://context.zorg.example/mcp", "http://127.0.0.1.evil.example/mcp", "http://localhost.evil.example/",
      "http://10.0.0.1/mcp", "http://127.0.0.2/mcp", "ftp://127.0.0.1/", "https://zorg.example\\@x/"]
check("2.1 https anywhere, http only to this computer", all(not cm.transport_problem(u) for u in OK),
      [(u, cm.transport_problem(u)) for u in OK if cm.transport_problem(u)])
check("2.2 remote http, a lookalike of loopback, another scheme, a bad address: refused",
      all(cm.transport_problem(u) for u in NO), [u for u in NO if not cm.transport_problem(u)])
opened = []
real_open = cm._OPENER.open
cm._OPENER.open = lambda *a, **k: opened.append(a) or (_ for _ in ()).throw(AssertionError("no request expected"))
try:
    cl = cm.McpClient("http://context.zorg.example/mcp", headers={"X-Token": SECRET})
    probed = cl.probe()
    try:
        cl.call("vault_search", {"query": "zorg"})
        called = "no error"
    except Exception as e:  # noqa: BLE001 — whatever it raised, it must say https and must have sent nothing
        called = "%s: %s" % (type(e).__name__, e)
finally:
    cm._OPENER.open = real_open
check("2.3 the client's transport refuses remote http before any request (probe and call)",
      probed is False and not opened and "https" in cl.last_error and "https" in called, (cl.last_error, called, opened))
check("2.4 …and the refusal names neither the url nor the header", "zorg.example" not in cl.last_error + called
      and SECRET not in cl.last_error + called, (cl.last_error, called))
with FakeMcp() as fake:
    ok = cm.McpClient(fake.url).probe()
check("2.5 loopback http still speaks (the tests' fake server)", ok)

with tempfile.TemporaryDirectory() as d:
    # 3–4. the first run ---------------------------------------------------------------------------------------
    home = new_home(d)
    regs = [repo("zorg-core", "https://context.zorg.example/mcp", "ZORG_MCP_HEADERS", home),
            repo("zorg-brain", "http://127.0.0.1:9/mcp", "", home),
            repo("zorg-old", "http://brain.zorg.example/mcp", "", home),
            crp.normalise({"id": "zorg-folder", "kind": "bundle", "paths": [d]})]
    check("3.0 no trust file before the first run", not os.path.lexists(ce.trust_file(home)))
    lines = ce.seed(home, regs, now=NOW)
    check("4.1 the first run trusts the registrations with an address already there — one line each, by the protocol's "
          "words", lines[:2] == ["Довірено наявну реєстрацію zorg-core: https://context.zorg.example (змінна ZORG_MCP_HEADERS)",
                                 "Довірено наявну реєстрацію zorg-brain: http://127.0.0.1:9 (без змінної)"], lines)
    check("4.2 …a remote http address is not trusted, and is named", len(lines) == 3 and lines[2].startswith("Не довірено zorg-old:")
          and "https" in lines[2], lines)
    data = json.loads(raw(home))
    check("4.3 the file: schema, seeded_at, one entry per trusted registration, «seeded»",
          data.get("schema") == "provider-trust/1" and data.get("seeded_at") == NOW
          and [(e["id"], e["url"], e["headers_env"], e["how"]) for e in data["entries"]]
          == [("zorg-core", "https://context.zorg.example/mcp", "ZORG_MCP_HEADERS", "seeded"),
              ("zorg-brain", "http://127.0.0.1:9/mcp", None, "seeded")], data)
    mode = stat.S_IMODE(os.stat(ce.trust_file(home)).st_mode)
    dmode = stat.S_IMODE(os.stat(os.path.dirname(ce.trust_file(home))).st_mode)
    check("3.1 the trust file is 0600, its folder 0700", mode == 0o600 and dmode == 0o700, (oct(mode), oct(dmode)))
    check("3.2 the trust file holds no header value (mutation: the value written)", SECRET not in raw(home), raw(home))
    check("3.3 the trust file lives under ~/.grow-pm/trust, not the registrations' folder",
          ce.trust_file(home) == os.path.join(home, ".grow-pm", "trust", "providers.json"))
    before = raw(home)
    regs2 = regs + [repo("zorg-new", "https://new.zorg.example/mcp", "", home)]
    again = ce.seed(home, regs2, now="2026-11-21T09:00:00+02:00")
    check("4.4 the first run happens once: the file there → no line, nothing changed, a new registration not trusted "
          "(mutation: the seed repeats)", again == [] and raw(home) == before, (again, raw(home)))

    empty = new_home(d, "empty")
    check("4.5 no registration at all: no line, and the file is written all the same",
          ce.seed(empty, [], now=NOW) == [] and json.loads(raw(empty))["entries"] == [] and json.loads(raw(empty))["seeded_at"] == NOW)
    check("4.6 …so a registration added after it is new, never seeded", ce.seed(empty, regs, now=NOW) == []
          and json.loads(raw(empty))["entries"] == [])
    late = new_home(d, "late")
    put = ce.seed(late, regs, late=["/vault/Notes/_System/providers/zorg-x.yaml"], now=NOW)
    check("4.7 a registration still downloading puts the first run off: one line, no file",
          len(put) == 1 and "завантаж" in put[0] and not os.path.lexists(ce.trust_file(late)), put)
    ro = new_home(d, "ro")
    os.chmod(os.path.join(ro, ".grow-pm"), 0o500)
    try:
        said = ce.seed(ro, regs, now=NOW)
    finally:
        os.chmod(os.path.join(ro, ".grow-pm"), 0o700)
    check("4.8 a home that cannot be written (Codex read-only): one line, no file, nothing trusted",
          len(said) == 1 and "не створено" in said[0] and not os.path.lexists(ce.trust_file(ro))
          and ce.verdict(repo("zorg-core", "https://context.zorg.example/mcp", "ZORG_MCP_HEADERS", ro)) is not None, said)

    # 5. the verdict -------------------------------------------------------------------------------------------
    core = repo("zorg-core", "https://context.zorg.example/mcp", "ZORG_MCP_HEADERS", home)
    check("5.1 the approved pair passes", ce.verdict(core) is None, ce.verdict(core))
    check("5.2 the same address written otherwise passes (case, default port, credentials, query)",
          ce.verdict(repo("zorg-core", "HTTPS://u:p@CONTEXT.zorg.example:443/mcp?x=1", "ZORG_MCP_HEADERS", home)) is None)
    moved = ce.verdict(repo("zorg-core", "https://evil.example/mcp", "ZORG_MCP_HEADERS", home))
    check("5.3 another address gets nothing — the line names the old and the new host (mutation: a changed url passes)",
          moved is not None and moved.why == "changed" and moved.line == "zorg-core: адресу не схвалено (змінилась: "
          "https://context.zorg.example → https://evil.example) — нічого не надіслано. Схвалити: ctx provider trust zorg-core",
          moved and moved.line)
    path = ce.verdict(repo("zorg-core", "https://context.zorg.example/other", "ZORG_MCP_HEADERS", home))
    check("5.4 another path on the same host is a change too", path is not None and path.why == "changed"
          and "https://context.zorg.example/mcp → https://context.zorg.example/other" in path.line, path and path.line)
    var = ce.verdict(repo("zorg-core", "https://context.zorg.example/mcp", "ZORG_OTHER_HEADERS", home))
    check("5.5 another variable gets nothing (mutation: a changed variable passes)", var is not None and var.why == "changed"
          and "змінна ZORG_MCP_HEADERS → змінна ZORG_OTHER_HEADERS" in var.line, var and var.line)
    novar = ce.verdict(repo("zorg-core", "https://context.zorg.example/mcp", "", home))
    check("5.6 dropping the variable is a change as well", novar is not None and "без змінної" in novar.line, novar and novar.line)
    new = ce.verdict(repo("zorg-new", "https://new.zorg.example/mcp", "", home))
    check("5.7 a new id with no variable needs approval as well (R36: the address gets the queries)",
          new is not None and new.why == "new" and new.line == "zorg-new: адресу не схвалено (нова) — нічого не надіслано. "
          "Схвалити: ctx provider trust zorg-new", new and new.line)
    remote = ce.verdict(repo("zorg-brain", "http://brain.zorg.example/mcp", "", home))
    check("5.8 remote http is refused whatever the file says — and no trust hint is given (trust would refuse it)",
          remote is not None and remote.why == "transport" and "ctx provider trust" not in remote.line, remote and remote.line)
    noaddr = ce.verdict(repo("zorg-x", "https://zorg.example\\@evil.example/", "", home))
    check("5.9 an address that is not plainly one is refused", noaddr is not None and noaddr.why == "transport")
    shell = ce.verdict(repo("zorg$(touch x)", "https://context.zorg.example/mcp", "", home))
    check("5.10 an id that is not kebab-case gets no command to paste (a shell would run it)",
          shell is not None and "ctx provider trust" not in shell.line and "$(" not in shell.line, shell and shell.line)
    badvar = ce.verdict(repo("zorg-core", "https://context.zorg.example/mcp", "ZORG MCP;x", home))
    check("5.11 a variable whose name is not plain is refused and not repeated", badvar is not None
          and "ZORG MCP;x" not in badvar.line, badvar and badvar.line)
    nohome = repo("zorg-core", "https://context.zorg.example/mcp", "ZORG_MCP_HEADERS")
    check("5.12 no trust home → new, nothing sent", ce.verdict(nohome) is not None and ce.verdict(nohome).why == "new")
    planted = crp.normalise({"id": "zorg-core", "kind": "mcp", "_trust_home": home,
                             "endpoint": {"url": "https://context.zorg.example/mcp", "headers_env": "ZORG_MCP_HEADERS"}})
    check("5.13 a `_trust_home` a registration file names is dropped, and a plain text is no trust home",
          "_trust_home" not in planted and ce.verdict(dict(planted, _trust_home=home)) is not None)

    broken = new_home(d, "broken")
    os.makedirs(os.path.dirname(ce.trust_file(broken)))
    open(ce.trust_file(broken), "w").write("{not json")
    bv = ce.verdict(repo("zorg-core", "https://context.zorg.example/mcp", "", broken))
    check("3.4 a trust file that cannot be read refuses everything, saying so", bv is not None and bv.why == "unreadable", bv and bv.line)
    check("3.5 …and a first run never rewrites it", ce.seed(broken, regs, now=NOW) == [] and open(ce.trust_file(broken)).read() == "{not json")
    linked = new_home(d, "linked")
    os.makedirs(os.path.join(linked, ".grow-pm", "trust"))
    os.symlink(ce.trust_file(home), ce.trust_file(linked))
    lv = ce.verdict(repo("zorg-core", "https://context.zorg.example/mcp", "ZORG_MCP_HEADERS", linked))
    check("3.6 a trust file that is a link (into a vault, say) is not read", lv is not None and lv.why == "unreadable", lv and lv.line)
    other = new_home(d, "other-schema")
    os.makedirs(os.path.dirname(ce.trust_file(other)))
    open(ce.trust_file(other), "w").write(json.dumps({"schema": "provider-trust/9", "entries": []}))
    check("3.7 a trust file of another schema is not read", ce.verdict(repo("zorg-core", "https://a.example/", "", other)).why == "unreadable")

    # 6. client_for --------------------------------------------------------------------------------------------
    f = Factory()
    ce.client_for(core, factory=f, deadline=None)
    check("6.1 an approved pair: the factory gets the address and the header from the environment",
          f.calls == [("https://context.zorg.example/mcp", {"X-Token": SECRET}, {"deadline": None})], f.calls)
    f = Factory()
    raised = None
    for r in (repo("zorg-core", "https://evil.example/mcp", "ZORG_MCP_HEADERS", home),
              repo("zorg-core", "https://context.zorg.example/mcp", "ZORG_OTHER_HEADERS", home),
              repo("zorg-new", "https://new.zorg.example/mcp", "", home),
              repo("zorg-brain", "http://brain.zorg.example/mcp", "ZORG_MCP_HEADERS", home), nohome):
        try:
            ce.client_for(r, factory=f)
        except ce.Untrusted as e:
            raised = (raised or 0) + 1
            check("6.2 …the refusal carries no secret: %s" % r["id"], SECRET not in str(e) and SECRET not in e.line, e.line)
    check("6.3 anything else raises Untrusted before the factory is called (mutation: remote http gets the header)",
          raised == 5 and f.calls == [], (raised, f.calls))
    with FakeMcp(require_headers={"X-Token": SECRET}) as fake:
        h2 = new_home(d, "live")
        live = repo("zorg-live", fake.url, "ZORG_MCP_HEADERS", h2)
        ce.seed(h2, [], now=NOW)
        try:
            ce.client_for(live).probe()
        except ce.Untrusted:
            pass
        unseen = list(fake.seen)
        ce.approve(h2, live, now=NOW)
        reached = ce.client_for(live).probe()
    check("6.4 a real client: nothing reaches the server before approval, the header does after it",
          unseen == [] and reached and fake.seen and fake.seen[0]["headers"].get("X-Token") == SECRET, (unseen, reached))
    f = Factory()
    ce.client_for(dict(core, _trust_home=None), home=home, factory=f)
    check("6.5 an explicit home (the search's, the copy's) is a trust home", len(f.calls) == 1)

    # 7. approve / revoke ------------------------------------------------------------------------------------
    h3 = new_home(d, "approve")
    ce.seed(h3, [], now=NOW)
    entry = ce.approve(h3, repo("zorg-core", "https://u:pw@context.zorg.example/mcp?k=1", "ZORG_MCP_HEADERS"), now=NOW)
    data = json.loads(raw(h3))
    check("7.1 approve writes the pair as «approved», the address normalised", data["entries"] == [
        {"id": "zorg-core", "url": "https://context.zorg.example/mcp", "headers_env": "ZORG_MCP_HEADERS", "at": "2026-11-20",
         "how": "approved"}] and entry["how"] == "approved", data)
    check("7.2 …never a value or a password", SECRET not in raw(h3) and "pw" not in raw(h3).replace("approved", ""), raw(h3))
    ce.approve(h3, repo("zorg-core", "https://context2.zorg.example/mcp", ""), now=NOW)
    check("7.3 approving again replaces the id's entry", [e["url"] for e in json.loads(raw(h3))["entries"]]
          == ["https://context2.zorg.example/mcp"])
    for bad, why in ((repo("zorg-x", "http://remote.zorg.example/mcp"), "remote http"),
                     (repo("Zorg X", "https://context.zorg.example/mcp"), "an id that is not kebab-case"),
                     (repo("zorg-x", "https://context.zorg.example/mcp", "A;B"), "a variable that is no plain name"),
                     (repo("zorg-x", ""), "no address")):
        try:
            ce.approve(h3, bad, now=NOW)
            check("7.4 approve refuses %s" % why, False)
        except ce.TrustError as e:
            check("7.4 approve refuses %s" % why, "A;B" not in str(e), str(e))
    check("7.5 revoke removes the id's entry and says how many", ce.revoke(h3, "zorg-core") == 1
          and json.loads(raw(h3))["entries"] == [] and ce.revoke(h3, "zorg-core") == 0)
    try:
        ce.approve(new_home(d, "nofile"), repo("zorg-core", "https://context.zorg.example/mcp"), now=NOW)
        check("7.6 approve before the first run refuses (it would shut the seed out)", False)
    except ce.TrustError:
        check("7.6 approve before the first run refuses (it would shut the seed out)", True)

    # 8. a private registration before a vault's -------------------------------------------------------------
    vault = os.path.join(d, "vault")
    vdir = os.path.join(vault, "Notes", "_System", "providers")
    pdir = os.path.join(d, "private")
    os.makedirs(vdir)
    os.makedirs(pdir)
    open(os.path.join(vdir, "zorg-core.yaml"), "w").write(
        "id: zorg-core\nkind: mcp\nendpoint:\n  url: https://evil.example/mcp\n  headers_env: ZORG_MCP_HEADERS\n")
    open(os.path.join(pdir, "zorg-core.yaml"), "w").write(
        "id: zorg-core\nkind: mcp\nendpoint:\n  url: https://context.zorg.example/mcp\n  headers_env: ZORG_MCP_HEADERS\n")
    open(os.path.join(vdir, "zorg-same.yaml"), "w").write("id: zorg-same\nkind: mcp\nendpoint:\n  url: https://a.zorg.example/\n")
    open(os.path.join(pdir, "zorg-same.yaml"), "w").write("id: zorg-same\nkind: mcp\nendpoint:\n  url: https://a.zorg.example/\n")
    shadowed = []
    got = cc.find_registrations([(vault, "Notes")], extra_dirs=[pdir], shadowed=shadowed)
    mine = [r for r in got if r["id"] == "zorg-core"]
    check("8.1 the private registration wins over a vault's of the same id (mutation: the vault shadows it)",
          len(mine) == 1 and mine[0]["endpoint"]["url"] == "https://context.zorg.example/mcp"
          and mine[0]["_file"].startswith(pdir), mine)
    check("8.2 two files of one id with different addresses are named; the same address is not",
          shadowed == ["реєстрація zorg-core: два файли не збігаються, взято приватний"], shadowed)
    notes = []
    loaded = crp.load_repos("", home, extra_dirs=[pdir], notes=notes)
    check("8.3 load_repos marks every registration with its trust home, which no file can plant",
          loaded and all(isinstance(r.get("_trust_home"), ce.Home) for r in loaded), loaded)

# 9. every place that builds a client refuses a registration you did not approve — the fake server sees nothing --------
import ctx as ctxmain  # noqa: E402
import ctx_copy as ccp  # noqa: E402
from ctx_testenv import Env  # noqa: E402
from mcp_fake import BLOCKS  # noqa: E402

REG = """schema: provider-registration/2
id: {id}
title: Zorg Growth
kind: mcp
authority: team
endpoint:
  url: {url}
  root: Growth/
{var}blocks_file: _System/context-blocks.md
blocks_source: mcp
sync: daily
"""
TREE = {"Growth/_System/context-blocks.md": BLOCKS, "Growth/Notes/Zorg plan.md": "# Zorg plan\nweekly active shoppers\n"}
AT = "2026-11-20T10:00:00+02:00"


def reg_text(rid, url, var=""):
    return REG.format(id=rid, url=url, var="  headers_env: %s\n" % var if var else "")


def reqs(fake):
    return len(fake.seen)


with tempfile.TemporaryDirectory() as d:
    env = Env(d)
    rc, out, _ = env.run("migrate", "--apply")
    check("9.0 a store", rc == 0, out)
    prov = os.path.join(env.home, ".grow-pm", "providers")
    os.makedirs(prov)
    rc, out, res = env.run("repo", "status")
    check("9.0 the first run with no registration: the trust file, empty, no line",
          rc == 0 and json.loads(raw(env.home))["entries"] == [] and "Довірено" not in out, out)
    reg = os.path.join(prov, "zorg-growth.yaml")
    with FakeMcp(tree=TREE, require_headers={"X-Token": SECRET}) as fake:
        open(reg, "w", encoding="utf-8").write(reg_text("zorg-growth", fake.url, "ZORG_MCP_HEADERS"))
        line = ("zorg-growth: адресу не схвалено (нова) — нічого не надіслано. Схвалити: ctx provider trust zorg-growth")
        rc, out, res = env.run("repo", "status")
        row = (res or {}).get("repos", [{}])[0]
        check("9.1 repo status: not probed, «не схвалено» with the line, trusted false in CTX_RESULT",
              rc == 0 and reqs(fake) == 0 and "не схвалено — " + line in out and row.get("trusted") is False
              and row.get("reachable") is False, (rc, out, row, fake.seen))
        rc, out, res = env.run("provider", "plan", "zorg-growth")
        check("9.2 provider plan (the fetch): exit 5, the line, no request", rc == 5 and line in out and reqs(fake) == 0, (rc, out))
        rc, out, res = env.run("provider", "adopt", "zorg-growth")
        check("9.3 provider adopt: exit 5, nothing written, no request", rc == 5 and line in out and reqs(fake) == 0, (rc, out))
        rc, out, res = env.run("provider", "sync", "zorg-growth", "--now", AT)
        r0 = ((res or {}).get("results") or [{}])[0]
        check("9.4 the daily sync: the line printed, no request, «unreachable» with the line — and exit 0 (it never stops a skill)",
              rc == 0 and line in out.splitlines() and reqs(fake) == 0 and r0.get("outcome") == "unreachable"
              and line in (r0.get("reason") or ""), (rc, out, r0))
        rc, out, res = env.run("search", "--q", "Zorg plan", "--sources", "mcp", "--json")
        check("9.5 search: the line instead of «не відповів», no query sent",
              line in (res or {}).get("notes", []) and reqs(fake) == 0, (rc, (res or {}).get("notes"), fake.seen))
        rc, out, res = env.run("search", "--get", "@zorg-growth/Notes/Zorg plan.md")
        check("9.6 search --get: exit 5, the line, no request", rc == 5 and line in out and reqs(fake) == 0, (rc, out))
        rc, out, res = env.run("repo", "copy", "zorg-growth", "--now", AT)
        check("9.7 repo copy: refused (exit 4) with the line, no request, no copy folder",
              rc == 4 and line in out and reqs(fake) == 0 and not os.path.exists(ccp.copy_dir(env.home, "zorg-growth")),
              (rc, out))
        loaded = [r for r in crp.load_repos(env.text, env.home) if r["id"] == "zorg-growth"]
        f_ = crp.fetch(loaded[0])
        ok_, why_ = crp.reach(loaded[0])
        try:
            ccp.run(env.home, loaded[0], ce.datetime.datetime.now().astimezone())
            passed = "ran"
        except ccp.Untrusted as e:
            passed = str(e)
        check("9.8 in process: fetch, reach and a copy pass refuse with the line, no request",
              f_["error"] == line and not ok_ and why_ == line and passed == line and reqs(fake) == 0, (f_["error"], why_, passed))
        check("9.9 nothing of the header reached any output", SECRET not in out, out)

        rc, out, res = env.run("provider", "trust", "zorg-growth")
        shown = out.splitlines()
        check("9.10 provider trust: the id, the address, the variable and the file first, then «схвалено»",
              rc == 0 and shown[:4] == ["схвалення адреси реєстрації zorg-growth", "  адреса: %s" % fake.url,
                                        "  змінна ZORG_MCP_HEADERS", "  файл реєстрації: %s" % reg]
              and shown[4].startswith("схвалено: zorg-growth → http://127.0.0.1:") and res["changed"] is True
              and reqs(fake) == 0, out)
        check("9.11 …the entry is «approved», no value in the file", [(e["id"], e["how"]) for e in json.loads(raw(env.home))["entries"]]
              == [("zorg-growth", "approved")] and SECRET not in raw(env.home), raw(env.home))
        rc, out, res = env.run("provider", "trust", "zorg-growth")
        check("9.12 approving again: «вже схвалено», nothing written", rc == 0 and "вже схвалено" in out and res["changed"] is False, out)
        rc, out, res = env.run("repo", "status")
        check("9.13 approved: probed with the header, reachable", rc == 0 and "reachable yes" in out and reqs(fake) > 0
              and fake.seen[0]["headers"].get("X-Token") == SECRET and res["repos"][0]["trusted"] is True, out)
        before = raw(env.home)
        rc, out, res = env.run("provider", "trust", "--list")
        check("9.14 trust --list: the pair, «діє», nothing written", rc == 0 and "zorg-growth" in out and "діє" in out
              and raw(env.home) == before and res["entries"][0]["state"] == "діє" and res["untrusted"] == [], out)
        n = reqs(fake)
        rc, out, res = env.run("provider", "untrust", "zorg-growth")
        check("9.15 untrust removes the pair", rc == 0 and res["removed"] == 1 and json.loads(raw(env.home))["entries"] == [], out)
        rc, out, res = env.run("repo", "status")
        check("9.16 …and its server gets nothing again", "не схвалено" in out and reqs(fake) == n, out)
        rc, out, res = env.run("provider", "trust", "zorg-nope")
        check("9.17 trust of an unknown id is exit 3", rc == 3, out)

        open(reg, "w", encoding="utf-8").write(reg_text("zorg-growth", "http://brain.zorg.example/mcp", ""))
        rc, out, res = env.run("provider", "trust", "zorg-growth")
        check("9.18 trust refuses remote http (exit 4), writes nothing", rc == 4 and "refused" in out
              and json.loads(raw(env.home))["entries"] == [], out)

    # a vault registration of the same id never wins; the line names the two files
    vprov = os.path.join(env.vault, "Notes", "_System", "providers")
    os.makedirs(vprov, exist_ok=True)
    with FakeMcp(tree=TREE) as good, FakeMcp(tree=TREE) as evil:
        open(reg, "w", encoding="utf-8").write(reg_text("zorg-growth", good.url, ""))
        env.run("provider", "trust", "zorg-growth")
        open(os.path.join(vprov, "zorg-growth.yaml"), "w", encoding="utf-8").write(
            reg_text("zorg-growth", evil.url, "ZORG_MCP_HEADERS"))
        rc, out, res = env.run("repo", "status")
        check("9.19 a vault file of the same id: the private one is used, the line names the two, the vault's address "
              "gets nothing", rc == 0 and "реєстрація zorg-growth: два файли не збігаються, взято приватний" in out
              and reqs(evil) == 0 and reqs(good) > 0, (out, reqs(evil), reqs(good)))

    for args, writing in ((["provider", "trust", "zorg-growth"], True), (["provider", "untrust", "zorg-growth"], True),
                          (["provider", "trust", "--list"], False)):
        check("9.20 writes(%s) is %s" % (" ".join(args), writing), ctxmain.writes(ctxmain.build_parser().parse_args(args)) is writing)

# 10. the first run through the command line (R37) ------------------------------------------------------------------
with tempfile.TemporaryDirectory() as d, FakeMcp(tree=TREE, require_headers={"X-Token": SECRET}) as fake:
    env = Env(d)
    prov = os.path.join(env.home, ".grow-pm", "providers")
    os.makedirs(prov)
    open(os.path.join(prov, "zorg-growth.yaml"), "w").write(reg_text("zorg-growth", fake.url, "ZORG_MCP_HEADERS"))
    open(os.path.join(prov, "zorg-brain.yaml"), "w").write(reg_text("zorg-brain", fake.url, ""))
    rc, out, res = env.run("repo", "status")
    seeded = [l for l in out.splitlines() if l.startswith("Довірено")]
    check("10.1 the first repo status after the update trusts both, one line each, and the requests go",
          rc == 0 and seeded == ["Довірено наявну реєстрацію zorg-brain: %s (без змінної)" % fake.url.rsplit("/", 1)[0],
                                 "Довірено наявну реєстрацію zorg-growth: %s (змінна ZORG_MCP_HEADERS)" % fake.url.rsplit("/", 1)[0]]
          and reqs(fake) > 0 and all(r["trusted"] for r in res["repos"]), (out, seeded))
    rc, out, res = env.run("repo", "status")
    check("10.2 the second run: no line", rc == 0 and "Довірено" not in out, out)

print("\nRESULT: %s (%d failed)" % ("GREEN ✅" if not fails else "RED ❌", fails))
sys.exit(1 if fails else 0)
