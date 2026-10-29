#!/usr/bin/env python3
"""TC-ctx-3240-copy-folder — the plugin's copy of an MCP-only core read as the repository's folder (since v3.24.0).

A temp HOME and vault (testing/ctx_testenv.py, the typical fictional context), the example kit
`examples/provider-kit/zorg-core/` (fictional "Zorg") served by the fake notes server (testing/mcp_fake.py, 127.0.0.1)
with its two `.md` wrappers, and an MCP-only registration of it (an endpoint, no folder). Before a copy, and with a copy
that has not completed a pass, the registration is as v3.23 read it (no core folder). After `ctx repo copy`:
`load_repos` gives it the copy as its `core_root` (`core_from: copy`, `copy_at`); the blocks come from the server, and
with the server down from the copy; the team block from the copy is byte for byte the one a folder registration of the
same kit builds; without wrappers, or with a broken one, the team block is unavailable with the reason; the index walks
the copy (names `@<id>/…`, the copy's service folders left out); search and `--get` answer from the copy with the server
unreachable (`· копія від <day>` on the provenance line), entities too; a write into the copy is refused; a
registration with its own folder never takes a copy; a search-only registration stays search-only.
Semantics: references/context-provider-protocol.md §12.12. Stdlib only; run from the repo root.
"""
import datetime, json, os, re, shutil, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "testing"))
os.environ["NO_PROXY"] = "127.0.0.1,localhost"
os.environ["no_proxy"] = "127.0.0.1,localhost"
import ctx_common as cc  # noqa: E402
import ctx_copy as cp  # noqa: E402
import ctx_mcp as cm  # noqa: E402
import ctx_repos as crp  # noqa: E402
import provider_bundle as pb  # noqa: E402
from ctx_testenv import Env  # noqa: E402
from mcp_fake import FakeMcp  # noqa: E402

cm.McpClient.BACKOFF = 0.0
KIT = os.path.join(ROOT, "examples", "provider-kit", "zorg-core")
fails = 0


def check(name, cond, detail=""):
    global fails
    fails += not cond
    print(("✅" if cond else "❌"), name, ("" if cond else "-> " + str(detail)[:900]))


def read(p):
    return open(p, encoding="utf-8", newline="").read()


def served(kit, skip=()):
    out = {}
    for rel in sorted(pb.walk(kit)):
        rel = rel.replace(os.sep, "/")
        if not rel.endswith(".md") or rel in skip:
            continue
        text = read(os.path.join(kit, rel))
        front, body = pb.split_fm(text)
        try:
            fm = cc.read_yaml_subset(front) if front else {}
        except ValueError:
            fm, body = {}, text
        out["Zorg/" + rel] = {"frontmatter": fm, "content": body}
    return out


REG = """schema: provider-registration/2
id: {rid}
title: Zorg core, served
kind: mcp
contract: vault/v1
authority: org
mode: live
access: vpn
endpoint:
  url: {url}
  root: Zorg/
namespace: zorg-core
blocks_file: {blocks}
team: team-alpha
role: pm
jira_write: ask
sync: daily
status: active
"""
FOLDER = """schema: provider-registration/2
id: zorg-folder
title: Zorg core, a folder
kind: folder
paths:
  - {kit}
core_root: {kit}
namespace: zorg-core
blocks_file: Core/_System/context-blocks.md
team: team-alpha
role: pm
jira_write: ask
status: active
"""
DEAD = "http://127.0.0.1:9/mcp"                      # nothing listens: the server is down (VPN off)
MAN, MODEL = "Core/_System/provider-manifest.md", "Core/_System/access-bundles.md"


def repo_of(env, rid):
    return next(r for r in crp.load_repos(env.text, env.home) if r["id"] == rid)


def set_url(path, url):
    t = read(path)
    open(path, "w", encoding="utf-8").write(re.sub(r"url: \S+", "url: " + url, t, count=1))


tmp = tempfile.mkdtemp(prefix="ctx-copy-folder-")
try:
    env = Env(tmp)
    prov = os.path.join(env.home, ".grow-pm", "providers")
    os.makedirs(prov)
    kit = os.path.join(tmp, "kit")
    shutil.copytree(KIT, kit)
    open(os.path.join(prov, "zorg-folder.yaml"), "w", encoding="utf-8").write(FOLDER.format(kit=kit))
    reg = os.path.join(prov, "zorg-core.yaml")
    rc, out, _ = env.run("migrate", "--apply")
    check("a store to plan against", rc == 0, out)
    with FakeMcp(tree=served(KIT)) as fake:
        open(reg, "w", encoding="utf-8").write(REG.format(rid="zorg-core", url=fake.url, blocks="Core/_System/context-blocks.md"))

        print("— 1. no copy, or one not complete: as v3.23")
        r0 = repo_of(env, "zorg-core")
        check("no copy: no core folder", r0["core_root"] == "" and "core_from" not in r0, r0.get("core_root"))
        rc, out, res = env.run("repo", "list", "--json")
        check("no copy: the rows of repo list carry no copy key", all("copy" not in r for r in res["repos"]), res["repos"])
        rc, out, res = env.run("repo", "status", "zorg-folder", "--json")
        check("…nor those of repo status", all("copy" not in r for r in res["repos"]) and "копія" not in out, out)
        fake.list_cap = 0
        env.run("repo", "copy", "zorg-core", "--now", "2026-10-29T08:00:00+02:00")
        fake.list_cap = None
        r1 = repo_of(env, "zorg-core")
        check("a copy with no complete pass is no folder", r1["core_root"] == "" and os.path.isdir(cp.copy_dir(env.home, "zorg-core")), r1.get("core_root"))
        f1 = crp.fetch(r1)
        check("…and the team block is as v3.23 (no core folder)", "no core folder in the registration" in (f1["team_error"] or ""), f1)

        print("— 2. after a copy")
        rc, out, res = env.run("repo", "copy", "zorg-core", "--now", "2026-10-29T09:00:00+02:00")
        check("ctx repo copy: complete", rc == 0 and res["outcome"] == "complete", out)
        copy = cp.copy_dir(env.home, "zorg-core")
        r2 = repo_of(env, "zorg-core")
        check("load_repos: core_root = the copy, core_from copy, copy_at the day", r2["core_root"] == copy
              and r2["core_from"] == "copy" and r2["copy_at"] == "2026-10-29", {k: r2.get(k) for k in ("core_root", "core_from", "copy_at")})
        check("not search-only", not crp.search_only(r2))
        folder_repo = repo_of(env, "zorg-folder")
        ff = crp.fetch(folder_repo)
        f2 = crp.fetch(r2)
        check("blocks from the server while it answers", f2["source"] == "mcp" and not f2["error"], f2)
        check("the team block from the copy, byte for byte the folder's", f2["team"] and f2["team"] == ff["team"]
              and f2["team_source"] == "folder", (f2["team_error"], (f2["team"] or "")[:200], (ff["team"] or "")[:200]))
    set_url(reg, DEAD)
    r3 = repo_of(env, "zorg-core")
    f3 = crp.fetch(r3)
    check("server down: blocks from the copy", f3["source"] == "folder" and not f3["error"] and f3["blocks"] == ff["blocks"], f3)
    check("server down: the team block still from the copy", f3["team"] == ff["team"], f3["team_error"])
    rc, out, res = env.run("provider", "plan", "zorg-core")
    check("provider plan names the copy as the source", rc == 0 and "копія від 2026-10-29" in out, out)

    print("— 3. index, search, entity from the copy, the server unreachable")
    rc, out, res = env.run("index", "rebuild")
    check("index rebuild: exit 0", rc == 0, out)
    os.makedirs(os.path.join(copy, ".removed", "2026-10-29", "Core"), exist_ok=True)
    open(os.path.join(copy, ".removed", "2026-10-29", "Core", "Ghost Zorgplan.md"), "w").write("# Ghost Zorgplan\n")
    os.makedirs(os.path.join(copy, ".backup", "20261029-090000", "Core"), exist_ok=True)
    open(os.path.join(copy, ".backup", "20261029-090000", "Core", "Ghost Zorgplan.md"), "w").write("# Ghost Zorgplan\n")
    env.run("index", "rebuild")
    rc, out, res = env.run("search", "--q", "Ghost Zorgplan", "--json")
    check("the copy's service folders are not indexed", "Ghost Zorgplan" not in json.dumps(res, ensure_ascii=False), out[-600:])
    rc, out, res = env.run("search", "--q", "Alpha reviews", "--json")
    blob = json.dumps(res, ensure_ascii=False)
    check("search answers from the copy with names @zorg-core/…", rc == 0 and "@zorg-core/Core/Teams/team-alpha.md" in blob, out[-900:])
    check("…and never asks the server for it", "zorg-core" not in [s.get("id") for s in (res or {}).get("sources", []) if s.get("kind") == "mcp"], res and res.get("sources"))
    rc, out, res = env.run("search", "--get", "@zorg-core/Core/Teams/team-alpha.md")
    check("--get: the provenance line ends with · копія від <day>", rc == 0 and re.search(r"^> \[zorg-core · @zorg-core/Core/Teams/team-alpha\.md · .* · копія від 2026-10-29\]", out, re.M), out[:600])
    rc, out, res = env.run("entity", "pat.moss@zorg.example", "--json")
    check("entity: found in the copy", rc == 0 and "@zorg-core/Core/People/pat-moss.md" in json.dumps(res, ensure_ascii=False), out[-900:])

    print("— 4. what stays as it was")
    other = cp.copy_dir(env.home, "zorg-folder")
    shutil.copytree(copy, other)
    rf = repo_of(env, "zorg-folder")
    check("a registration with its own folder never takes a copy", rf["core_root"] == kit and "core_from" not in rf, rf.get("core_root"))
    open(os.path.join(prov, "zorg-rooted.yaml"), "w", encoding="utf-8").write(
        REG.format(rid="zorg-rooted", url=DEAD, blocks="Core/_System/context-blocks.md") + "core_root: %s\n" % kit)
    shutil.copytree(copy, cp.copy_dir(env.home, "zorg-rooted"))
    rr = repo_of(env, "zorg-rooted")
    check("…nor one that names a core_root and no paths", rr["core_root"] == kit and "core_from" not in rr, rr.get("core_root"))
    open(os.path.join(prov, "zorg-search.yaml"), "w", encoding="utf-8").write(
        REG.format(rid="zorg-search", url=DEAD, blocks='""').replace("team: team-alpha\n", ""))
    shutil.copytree(copy, cp.copy_dir(env.home, "zorg-search"))
    st = cp.load_state(cp.copy_dir(env.home, "zorg-search"))
    st["repo"] = "zorg-search"
    cp.save_state(cp.copy_dir(env.home, "zorg-search"), st)
    rs = repo_of(env, "zorg-search")
    check("a search-only registration with a copy stays search-only", rs.get("core_from") == "copy" and crp.search_only(rs), rs.get("blocks_file"))

    open(os.path.join(kit, "Core", ".backup", "Ghost Folderplan.md"), "w").write("# Ghost Folderplan\n") if os.makedirs(
        os.path.join(kit, "Core", ".backup"), exist_ok=True) is None else None
    env.run("index", "rebuild")
    rc, out, res = env.run("search", "--q", "Ghost Folderplan", "--json")
    check("a `.backup/` folder of a registration's own folder is indexed as before",
          "@zorg-folder/Core/.backup/Ghost Folderplan.md" in json.dumps(res, ensure_ascii=False), out[-600:])

    print("— 5. the team block's reasons")
    with FakeMcp(tree=served(KIT, skip=(MAN, MODEL))) as fake:
        set_url(reg, fake.url)
        env.run("repo", "copy", "zorg-core", "--now", "2026-10-30T09:00:00+02:00")
        env.run("repo", "copy", "zorg-core", "--now", "2026-10-31T10:00:00+02:00")
        r5 = repo_of(env, "zorg-core")
        f5 = crp.fetch(r5)
        check("wrappers gone: the team block is unavailable with the advice for the core owner", f5["team"] is None
              and "сервер не віддає provider-manifest" in (f5["team_error"] or ""), f5["team_error"])
        inline = served(KIT, skip=(MAN, MODEL))
        blocks_note = inline["Zorg/Core/_System/context-blocks.md"]
        inline["Zorg/Core/_System/context-blocks.md"] = dict(blocks_note, content=blocks_note["content"]
                                                             + "\n<!-- zorg-core:begin id=team v=0.1 -->\n### Team\nAlpha, from the file.\n<!-- zorg-core:end id=team -->\n")
        fake.tree = inline
        env.run("repo", "copy", "zorg-core", "--now", "2026-10-31T11:00:00+02:00")
        f7 = crp.fetch(repo_of(env, "zorg-core"))
        check("no wrappers and a team region in the blocks file: as v3.23 — the file's region, no error",
              f7["team"] is None and f7["team_error"] is None and "team" in f7["blocks"], (f7["team_error"], list(f7["blocks"])))
        bad = served(KIT)
        bad["Zorg/" + MODEL] = dict(bad["Zorg/" + MODEL], content=bad["Zorg/" + MODEL]["content"] + "\n```json\n{}\n```\n")
        fake.tree = bad
        env.run("repo", "copy", "zorg-core", "--now", "2026-10-31T12:00:00+02:00")
        f6 = crp.fetch(repo_of(env, "zorg-core"))
        check("a broken wrapper: the team block is unavailable with its reason", f6["team"] is None
              and "access-bundles.json" in (f6["team_error"] or "") and "рівно один" in (f6["team_error"] or ""), f6["team_error"])
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("RESULT:", "GREEN ✅" if not fails else "RED ❌", "(%d failed)" % fails)
sys.exit(1 if fails else 0)
