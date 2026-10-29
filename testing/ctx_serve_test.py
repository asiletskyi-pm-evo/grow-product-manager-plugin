#!/usr/bin/env python3
"""TC-ctx-4000-serve — `ctx serve` (scripts/ctx_serve.py): the local MCP server of vault/v1 (since v4.0.0).

The fictional Zorg vault of testing/fixtures/graph/, its index built: `ctx serve` run as a process and spoken to over
stdio, one JSON-RPC message a line — initialize (each protocol version, an unknown one), tools/list, the eight tools on
the fixture, a sensitive note given without its text, an unknown tool and method, a bad line; nothing on stdout but the
protocol, nothing written but the index. `serve --install`: the launcher, written once; `provider sync --if-due`
rewrites it when the plugin's folder moved, never one that is not ours. Stdlib only; run from the repo root:

  env -u GROW_PM_CONTEXT_PATH -u GROW_PM_PROVIDER_PATHS python3 testing/ctx_serve_test.py
"""
import json, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "testing"))
from ctx_vaultenv import VaultEnv, read, write  # noqa: E402
sys.path.insert(0, os.path.join(ROOT, "scripts"))
try:
    import ctx_serve as csv_  # noqa: E402
except ImportError:
    csv_ = None
CTX = os.path.join(ROOT, "scripts", "ctx.py")
fails = 0


def check(name, cond, detail=""):
    global fails
    fails += not cond
    print(("✅" if cond else "❌"), name, ("" if cond else "-> " + str(detail)[:900]))


if csv_ is None:
    check("v4.0.0 scripts/ctx_serve.py exists", False, "no module ctx_serve")
    print("RESULT: RED ❌")
    sys.exit(1)


def talk(env, msgs, raw=()):
    """The answers of `ctx serve` to `msgs` (and raw lines), stdout as it came."""
    lines = [json.dumps(m) for m in msgs] + list(raw)
    e = dict(os.environ)
    e.pop("GROW_PM_CONTEXT_PATH", None)
    e.pop("GROW_PM_PROVIDER_PATHS", None)
    p = subprocess.run([sys.executable, CTX, "serve", "--home", env.home, "--context", env.ctx],
                       input="\n".join(lines) + "\n", capture_output=True, text=True, env=e, timeout=120)
    return [json.loads(l) for l in p.stdout.splitlines() if l.strip()], p


def call(i, name, **args):
    return {"jsonrpc": "2.0", "id": i, "method": "tools/call", "params": {"name": name, "arguments": args}}


def result(ans, i):
    a = next(x for x in ans if x.get("id") == i)
    return a.get("result", {}).get("structuredContent"), a


with tempfile.TemporaryDirectory() as d:
    env = VaultEnv(d, fixture="graph", evicted=())
    env.run("index", "rebuild")
    before = env.tree()
    msgs = [{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-03-26"}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            call(3, "vault_search", query="Roadmap"),
            call(4, "vault_get_note", path="Notes/Roadmap.md"),
            call(5, "vault_get_note", path="ZorgCore/People/bea.md"),
            call(6, "vault_get_links", path="Notes/Roadmap.md", direction="both"),
            call(7, "vault_graph_context", entity="Notes/Roadmap.md", depth=2),
            call(8, "vault_list_by_folder", folder="Notes/Meetings"),
            call(9, "vault_list_by_tag", tag="nothing"),
            call(10, "brain_status"),
            call(11, "brain_find_entity", query="bea@zorg.example"),
            call(12, "no_such_tool"),
            {"jsonrpc": "2.0", "id": 13, "method": "resources/list"},
            call(14, "vault_get_note", path="Notes/None.md"),
            call(15, "vault_search", query="Bea")]
    ans, p = talk(env, msgs, raw=["{not json"])
    init = next(a for a in ans if a.get("id") == 1)["result"]
    check("v4.0.0 initialize: the version asked (one it speaks), tools, serverInfo grow-pm-vault",
          init["protocolVersion"] == "2025-03-26" and init["capabilities"] == {"tools": {}}
          and init["serverInfo"]["name"] == "grow-pm-vault", init)
    check("…a notification gets no answer; stdout holds the protocol alone (no CTX_RESULT)",
          len(ans) == len(msgs) and "CTX_RESULT" not in p.stdout, (len(ans), p.stdout[-300:], p.stderr[-300:]))
    tools = {t["name"] for t in next(a for a in ans if a.get("id") == 2)["result"]["tools"]}
    check("v4.0.0 tools/list: the six vault_* tools and brain_status, brain_find_entity",
          tools == {"vault_search", "vault_get_note", "vault_get_links", "vault_graph_context", "vault_list_by_tag",
                    "vault_list_by_folder", "brain_status", "brain_find_entity"}, tools)
    s3, _ = result(ans, 3)
    check("v4.0.0 vault_search: the note first, path, title, snippet", s3 and s3["results"]
          and s3["results"][0]["path"] == "Notes/Roadmap.md" and "snippet" in s3["results"][0], s3)
    s4, _ = result(ans, 4)
    check("v4.0.0 vault_get_note: frontmatter, text without it, headings, its links resolved, its trust",
          s4 and s4["frontmatter"].get("type") == "roadmap" and s4["content"].startswith("# Roadmap")
          and "Roadmap" in s4["headings"] and {"target": "Notes/Assets/diagram.png", "resolved_path": "Notes/Assets/diagram.png",
                                               "kind": "embed"} in s4["outgoing_links"]
          and s4["trust"]["kind"] == "own", s4)
    s5, _ = result(ans, 5)
    check("v4.0.0 a sensitive note (a person card): path, title, sensitive — no text, no frontmatter",
          s5 and s5.get("sensitive") is True and "content" not in s5 and "frontmatter" not in s5, s5)
    s6, _ = result(ans, 6)
    check("v4.0.0 vault_get_links: out (the embed, the epic) and in (the evicted note links it)",
          s6 and {o["path"] for o in s6["out"]} >= {"Notes/Assets/diagram.png", "Notes/Epics/Epic — PROJ-1234.md"}
          and "Notes/Evicted note.md" in {i["path"] for i in s6["in"]}, s6)
    s7, _ = result(ans, 7)
    check("v4.0.0 vault_graph_context: nodes by hop, the edges between them",
          s7 and s7["nodes"][0]["path"] == "Notes/Roadmap.md" and any(n["hop"] == 2 for n in s7["nodes"])
          and any(e["kind"] == "embed" for e in s7["edges"]), s7)
    s8, _ = result(ans, 8)
    check("v4.0.0 vault_list_by_folder: the notes under the folder",
          s8 and {r["path"] for r in s8["results"]} == {"Notes/Meetings/Standup 2026-10-01.md",
                                                        "Notes/Meetings/Standup 2026-10-08.md",
                                                        "Notes/Meetings/Pricing review.md"}, s8)
    s9, _ = result(ans, 9)
    check("…vault_list_by_tag with no such tag: an empty list", s9 == {"results": []}, s9)
    s10, _ = result(ans, 10)
    check("v4.0.0 brain_status: the day of the index, notes, edges", s10 and s10["notes"] > 5 and s10["edges"] > 5
          and s10["last_index"], s10)
    s11, _ = result(ans, 11)
    check("v4.0.0 brain_find_entity: the person by e-mail — the core's card the hub, yours related",
          s11 and s11["hub"]["path"] == "ZorgCore/People/bea.md" and any(r["path"] == "Notes/People/bea.md"
                                                                           for r in s11["related"]), s11)
    a12 = next(a for a in ans if a.get("id") == 12)
    a13 = next(a for a in ans if a.get("id") == 13)
    check("v4.0.0 an unknown tool and an unknown method: JSON-RPC errors -32602 and -32601",
          a12.get("error", {}).get("code") == -32602 and a13.get("error", {}).get("code") == -32601, (a12, a13))
    a14 = next(a for a in ans if a.get("id") == 14)
    check("…a note it does not hold: isError with the reason", a14["result"]["isError"] is True
          and "not found" in a14["result"]["content"][0]["text"], a14)
    bad = [a for a in ans if a.get("id") is None]
    check("…a line that is not JSON: a parse error, and the server goes on", bad and bad[0]["error"]["code"] == -32700, bad)
    s15, _ = result(ans, 15)
    sens = [r for r in (s15 or {}).get("results", []) if r.get("sensitive")]
    check("v4.0.0 vault_search: a sensitive hit is its path and title alone — no snippet",
          sens and all("snippet" not in r for r in sens), s15)
    check("v4.0.0 the server writes nothing in the vault", env.tree() == before)

    ans, _ = talk(env, [{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "1999-01-01"}}])
    check("…a protocol version it does not speak: its newest", ans[0]["result"]["protocolVersion"] == csv_.PROTOCOLS[0], ans)

    rc, out, res = env.run("serve", "--install")
    launcher = os.path.join(env.home, ".grow-pm", "bin", "ctx-serve")
    check("v4.0.0 serve --install: the launcher (executable, naming this plugin's ctx.py), the config lines",
          rc == 0 and os.access(launcher, os.X_OK) and os.path.join(ROOT, "scripts", "ctx.py") in read(launcher)
          and '"grow-pm-vault": {"command": "%s"}' % launcher in out and "codex mcp add grow-pm-vault -- " in out,
          (rc, out[-400:]))
    rc, out, res = env.run("serve", "--install")
    check("…again: nothing written", rc == 0 and res["written"] is False, res)
    write(launcher, read(launcher).replace(ROOT, "/old/plugin/3.24.0"))
    check("v4.0.0 a launcher that names another folder of the plugin is written again by the daily sync's check",
          csv_.relaunch_if_moved(env.home, ROOT) and os.path.join(ROOT, "scripts", "ctx.py") in read(launcher))
    write(launcher, "#!/bin/sh\nexec my-own-thing\n")
    check("…a launcher that is not ours is never touched", not csv_.relaunch_if_moved(env.home, ROOT)
          and read(launcher) == "#!/bin/sh\nexec my-own-thing\n")
    rc, out, res = env.run("provider", "sync", "--if-due")
    check("…`provider sync --if-due` runs the check (exit 0)", rc == 0, out[-300:])

print("RESULT:", "GREEN ✅ — 0 failure(s)" if not fails else "RED ❌ — %d failure(s)" % fails)
sys.exit(1 if fails else 0)
