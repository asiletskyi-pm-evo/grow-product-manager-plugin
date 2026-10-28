#!/usr/bin/env python3
"""TC-ctx-3233-overlay-cli — `ctx overlay show | plan | apply | add | rm | answer` (since v3.23.0).

Through the command line on a migrated store of the fictional "Zorg" (testing/fixtures/ctx-repos/context.md, a temp
HOME, a registration of zorg-core and the state `provider adopt` leaves): `plan` reads only and prints a code; `apply`
with another code writes nothing (exit 4) and with the shown one writes the file, the regions, one journal line, one
snapshot — `ctx undo` takes all of it back; `add`, `rm` and `answer` change the file and lay it over the regions in one
run; a held operation is named by `show`, `plan` and `ctx health` (✋); a file that cannot be read is never rewritten
by `add` (exit 3). Semantics: references/context-protocol.md §5n. Stdlib only; run from the repo root.
"""
import json, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import ctx_blocks as cb  # noqa: E402
import ctx_ops as co  # noqa: E402
import ctx_overlay as ov  # noqa: E402
import ctx_repos as crp  # noqa: E402
import ctx_store as cs  # noqa: E402

FIX = os.path.join(ROOT, "testing", "fixtures", "ctx-repos")
NOW = "2026-10-20T10:00:00+03:00"
NS = "zorg-core"
fails = 0


def check(name, cond, detail=""):
    global fails
    fails += not cond
    print(("✅" if cond else "❌"), name, ("" if cond else "-> " + str(detail)[:900]))


OWN_MEMBERS = ("- **Jira Team ID:** <team-uuid>\n",
               "- **Jira Team ID:** <team-uuid>\n\n#### Team Members\n\n| Name | Role |\n|---|---|\n| Alex One | PM |\n| Cid Three | QA |\n")
REG = """schema: provider-registration/2
id: zorg-core
title: Zorg shared core
kind: folder
paths:
  - {core}
namespace: zorg-core
blocks_file: Core/_System/context-blocks.md
products: []
writable: []
skip_blocks: []
team: team-alpha
sync: off
"""


def setup(d):
    home, vault = os.path.join(d, "home"), os.path.join(d, "vault")
    core = os.path.join(d, "core")
    os.makedirs(os.path.join(home, ".grow-pm", "providers"))
    os.makedirs(os.path.join(vault, "Notes", "_System"))
    os.makedirs(core)
    text = open(os.path.join(FIX, "context.md"), encoding="utf-8", newline="").read().replace("{{VAULT}}", vault)
    text = text.replace(*OWN_MEMBERS, 1)
    ctxp = os.path.join(home, ".grow-pm", "local-context.md")
    for p in (ctxp, os.path.join(vault, "Notes", "_System", "local-context.md")):
        open(p, "w", encoding="utf-8", newline="").write(text)
    open(os.path.join(home, ".grow-pm", "providers", "zorg-core.yaml"), "w", encoding="utf-8").write(REG.format(core=core))
    copies = co.copies_for(ctxp, text, home=home)
    store = cs.Store(co.store_root_for(text, home=home))
    co.migrate(ctxp, store.root, copies, home, apply=True, now=NOW)
    repo = crp.normalise({"id": "zorg-core", "kind": "folder", "paths": [core], "namespace": NS})
    regions = {k: v["text"] for k, v in cb.find_regions(store.load(), NS)[0].items()}
    f = {"source": "folder", "version": "0.4", "blocks": {k: v for k, v in regions.items() if k != "team"},
         "team": regions["team"], "team_source": "folder", "team_error": None, "error": None, "checked": NOW}
    with cs.guard_roots(co.allowed_roots(home, text)):
        cb.adopt(store, copies, home, repo, f, NOW, True)
    return home, ctxp, store


def ctx(home, ctxp, *args):
    env = {k: v for k, v in os.environ.items() if k not in ("GROW_PM_CONTEXT_PATH", "GROW_PM_PROVIDER_PATHS")}
    env["HOME"] = home
    r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "ctx.py")] + list(args) + ["--context", ctxp, "--home", home],
                       capture_output=True, text=True, env=env)
    out = r.stdout + r.stderr
    res = [l for l in out.splitlines() if l.startswith("CTX_RESULT ")]
    return r.returncode, out, json.loads(res[-1][len("CTX_RESULT "):]) if res else {}


def regions(store):
    return {k: v["text"] for k, v in cb.find_regions(store.load(), NS)[0].items()}


def journal(store):
    p = os.path.join(store.state_dir, "journal.jsonl")
    return [json.loads(l) for l in open(p, encoding="utf-8")] if os.path.isfile(p) else []


def tree(store):
    out = {}
    for base, _, files in os.walk(store.root):
        for f in files:
            p = os.path.join(base, f)
            out[os.path.relpath(p, store.root)] = open(p, "rb").read()
    return out


DRAFT = """schema: context-overlay/1
repo: zorg-core
ops:
  - id: members
    target: {block: team, path: "#Members"}
    op: replace
    value_ref: "team.alpha-a#Team Members"
    reason: "the core's table lists stubs"
  - id: gamma
    target: {block: teams}
    op: append
    value: "- Gamma (mine)"
    reason: "Gamma is ours too"
"""

with tempfile.TemporaryDirectory() as d:
    home, ctxp, store = setup(d)
    rc, out, res = ctx(home, ctxp, "overlay", "show")
    check("show with no overlay: says so, exit 0", rc == 0 and "оверлею немає" in out, out)

    draft = os.path.join(d, "draft.yaml")
    open(draft, "w", encoding="utf-8").write(DRAFT)
    before = tree(store)
    rc, out, res = ctx(home, ctxp, "overlay", "plan", "zorg-core", "--file", draft)
    code = res.get("code")
    check("plan --file: reads only, names each operation and the blocks it rewrites, with the lines and a code",
          rc == 0 and tree(store) == before and "members · team › #Members · replace · діє (знайдено 1)" in out
          and "gamma · teams · append · діє (знайдено 1)" in out and "teams · оверлей накладається" in out
          and "+ - Gamma (mine)" in out and code and ("код: %s" % code) in out, out)

    rc, out, res = ctx(home, ctxp, "overlay", "apply", "zorg-core", "--file", draft, "--code", "deadbeef")
    check("apply with another code: exit 4, nothing written", rc == 4 and tree(store) == before, out)
    rc, out, res = ctx(home, ctxp, "overlay", "apply", "zorg-core", "--file", draft)
    check("apply without --code: exit 3, nothing written", rc == 3 and tree(store) == before, out)

    rc, out, res = ctx(home, ctxp, "overlay", "apply", "zorg-core", "--file", draft, "--code", code)
    rg = regions(store)
    j = journal(store)[-1]
    check("apply with the code: the file in the canonical form, the regions overlaid, one journal line",
          rc == 0 and open(ov.path_of(store.root, "zorg-core"), encoding="utf-8").read() == ov.dump(ov.parse(DRAFT))
          and "> [оверлей members: замінено на team.alpha-a › Team Members" in rg["team"] and "- Gamma (mine)" in rg["teams"]
          and j["op"] == "overlay" and j["action"] == "apply" and j["overlay"] == {"team": ["members"], "teams": ["gamma"]}
          and sorted(j["ids"]) == sorted(res.get("written") or []), (out, j))
    rc, out, res = ctx(home, ctxp, "overlay", "plan", "zorg-core")
    check("…the plan after it has nothing to rewrite", rc == 0 and "оверлей накладається" not in out, out)

    n = len(journal(store))
    rc, out, res = ctx(home, ctxp, "overlay", "apply", "zorg-core", "--code", ctx(home, ctxp, "overlay", "plan", "zorg-core")[2]["code"])
    check("apply of the file as it is, with nothing to rewrite: no snapshot, no journal line", rc == 0 and "без змін" in out
          and len(journal(store)) == n, out)
    rc, out, res = ctx(home, ctxp, "undo")
    check("ctx undo: the file gone, the regions and the state as before", rc == 0 and tree(store).keys() >= before.keys()
          and {k: v for k, v in tree(store).items() if k.startswith(("records", ".state/blocks"))}
          == {k: v for k, v in before.items() if k.startswith(("records", ".state/blocks"))}
          and not os.path.exists(ov.path_of(store.root, "zorg-core")), out)

    rc, out, res = ctx(home, ctxp, "overlay", "add", "zorg-core", "--block", "scope", "--path", 'match:"Zorg App only"',
                       "--op", "ignore", "--reason", "we serve Lite too")
    doc = ov.load(store.root, "zorg-core")
    check("add: one operation in a new file, the made id, today's date, one journal line",
          rc == 0 and doc and [o["id"] for o in doc["ops"]] == ["scope-match-zorg-app-only"]
          and doc["ops"][0]["created"] == res.get("created") and journal(store)[-1]["action"] == "add", (out, doc))
    rc, out, res = ctx(home, ctxp, "overlay", "add", "zorg-core", "--block", "teams", "--op", "append", "--value", "- Gamma (mine)",
                       "--reason", "r", "--id", "gamma")
    check("add an append: the region gets the line in the same run", rc == 0 and "- Gamma (mine)" in regions(store)["teams"], out)
    rc, out, res = ctx(home, ctxp, "overlay", "add", "zorg-core", "--block", "teams", "--op", "append", "--value", "x",
                       "--id", "gamma")
    check("add an id already there: exit 3, nothing changes", rc == 3 and len(ov.load(store.root, "zorg-core")["ops"]) == 2, out)
    rc, out, res = ctx(home, ctxp, "overlay", "add", "zorg-core", "--block", "teams", "--op", "hide")
    check("add an operation of no known kind: exit 3", rc == 3, out)
    rc, out, res = ctx(home, ctxp, "overlay", "add", "zorg-core", "--block", "teams", "--op", "append", "--value",
                       "token sk-ant-api03-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
    check("add a value with a secret: refused before anything is written", rc == 4 and len(ov.load(store.root, "zorg-core")["ops"]) == 2, out)

    # the core fixes scope: the ignore is held → show, health, answer
    st = cb.load_state(store, "zorg-core")
    with cs.guard_roots([d]):
        new_base = cb.region("scope", "0.5", "### Scope of work\nThe user works on Zorg App and Lite.") \
            if hasattr(cb, "region") else "<!-- zorg-core:begin id=scope v=0.5 -->\n### Scope of work\nThe user works on Zorg App and Lite.\n<!-- zorg-core:end id=scope -->"
    rec = [r for r in store.load() if "zorg-core:begin id=scope" in r["body"]][0]
    old_region = regions(store)["scope"]
    with cs.guard_roots([d]):
        store.write(dict(rec, body=rec["body"].replace(old_region, new_base)))
        sha = cb.put_base(store, "zorg-core", new_base)
        st["blocks"]["scope"].update(base_sha=sha, bases=st["blocks"]["scope"]["bases"] + [sha], v="0.5")
        cb.save_state(store, "zorg-core", st)
    ctx(home, ctxp, "sync")
    rc, out, res = ctx(home, ctxp, "overlay", "show", "zorg-core")
    check("show: the held ignore with what was found", rc == 0 and "scope-match-zorg-app-only" in out
          and "затримано: знайдено 0, очікувалось 1" in out, out)
    rc, out, res = ctx(home, ctxp, "health")
    check("health: ✋ the held correction with the command", "✋" in out and "оверлей" in out and "/context overlay" in out, out)
    rc, out, res = ctx(home, ctxp, "overlay", "answer", "zorg-core", "scope-match-zorg-app-only", "drop")
    check("answer drop: the operation goes, one journal line", rc == 0 and [o["id"] for o in ov.load(store.root, "zorg-core")["ops"]]
          == ["gamma"] and journal(store)[-1]["action"] == "answer", out)
    rc, out, res = ctx(home, ctxp, "health")
    check("…health: no ✋ about the overlay any more, a ✅ line with what applies",
      "чекають рішення" not in out and "✅ оверлей zorg-core: поправок діє 1" in out, out)
    rc, out, res = ctx(home, ctxp, "overlay", "answer", "zorg-core", "gamma", "expects", "--expects", "1")
    check("answer expects with the same number: unchanged, exit 0", rc == 0 and "unchanged" in out, out)
    rc, out, res = ctx(home, ctxp, "overlay", "answer", "zorg-core", "gamma", "retarget", "--path", "#Teams map")
    check("answer retarget: the path changes, the region follows",
          rc == 0 and ov.load(store.root, "zorg-core")["ops"][0]["target"] == {"block": "teams", "path": "#Teams map"}
          and "- Gamma (mine)" in regions(store)["teams"], out)
    rc, out, res = ctx(home, ctxp, "overlay", "rm", "zorg-core", "gamma")
    check("rm: the operation goes and the region is the core's again", rc == 0 and ov.load(store.root, "zorg-core")["ops"] == []
          and "- Gamma (mine)" not in regions(store)["teams"], out)
    rc, out, res = ctx(home, ctxp, "overlay", "rm", "zorg-core", "nope")
    check("rm an id that is not there: exit 3", rc == 3, out)

    open(ov.path_of(store.root, "zorg-core"), "w", encoding="utf-8").write("ops: [broken\n")
    rc, out, res = ctx(home, ctxp, "overlay", "add", "zorg-core", "--block", "teams", "--op", "append", "--value", "x")
    check("add over a file that cannot be read: exit 3, the file untouched",
          rc == 3 and open(ov.path_of(store.root, "zorg-core"), encoding="utf-8").read() == "ops: [broken\n", out)
    rc, out, res = ctx(home, ctxp, "overlay", "show")
    check("show names the file that cannot be read, exit 3", rc == 3 and "zorg-core.yaml" in out, out)
    rc, out, res = ctx(home, ctxp, "health")
    check("health: ✋ the overlay that cannot be read", "✋" in out and "zorg-core.yaml" in out, out)
    rc, out, res = ctx(home, ctxp, "overlay", "show", "nope")
    check("a repository nobody registered: exit 3", rc == 3, out)

print("RESULT: GREEN ✅" if not fails else "RESULT: RED ❌")
sys.exit(1 if fails else 0)
