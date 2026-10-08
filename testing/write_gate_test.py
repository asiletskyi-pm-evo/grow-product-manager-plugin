#!/usr/bin/env python3
"""TC-hook-3100-boundary — scripts/write_gate.py, the PreToolUse gate.

Since v3.10.0 the gate also guards file writes under a shared-context provider's
local folders (references/context-provider-protocol.md §7): Write / Edit /
MultiEdit / NotebookEdit under a registered root and outside its `writable` globs
→ permissionDecision "ask"; anything else → no output (allow). The Jira /
Confluence branch is unchanged. Each case runs the script as a subprocess with an
isolated HOME, so the user's real configuration is never read.

Stdlib only; run from the repo root.
"""
import json, os, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GATE = os.path.join(ROOT, "scripts", "write_gate.py")

def run(env, payload):
    p = subprocess.run([sys.executable, GATE], input=json.dumps(payload), capture_output=True,
                       text=True, env=env, timeout=20)
    return p.stdout.strip()

fails = 0
def check(name, cond, detail=""):
    global fails
    fails += not cond
    print(("✅" if cond else "❌"), name, ("" if cond else "-> " + repr(detail)[:300]))

with tempfile.TemporaryDirectory() as d:
    home = os.path.join(d, "home"); os.makedirs(home)
    vault = os.path.join(d, "Vault")
    core = os.path.join(d, "ZorgCore"); os.makedirs(os.path.join(core, "Core", "Teams"))
    os.makedirs(os.path.join(d, "ZorgCore-notes"))
    regdir = os.path.join(vault, "Notes", "_System", "providers"); os.makedirs(regdir)
    reg = os.path.join(regdir, "zorg-core.yaml")
    open(reg, "w").write("schema: provider-registration/1\nid: zorg-core\nkind: bundle\npaths:\n  - %s\n"
                         "writable:\n  - Core/Now.md\n  - Core/_personal/\nstatus: active\n" % core)
    ctx = os.path.join(d, "local-context.md")
    open(ctx, "w").write("# Local Context\n\n## Obsidian Vaults (Optional)\n\n"
                         "| # | Vault Path | Folder Name | Products | Sync Mode | Last Artifact |\n|---|---|---|---|---|---|\n"
                         "| 1 | %s | Notes | all | auto | never |\n\n## Custom Sections\n" % vault)
    pdata = os.path.join(d, "plugin-data"); os.makedirs(pdata)
    env = {"HOME": home, "PATH": os.environ.get("PATH", ""), "GROW_PM_CONTEXT_PATH": ctx, "CLAUDE_PLUGIN_DATA": pdata}

    out = run(env, {"tool_name": "Write", "tool_input": {"file_path": os.path.join(core, "Core", "Teams", "x.md"), "content": "x"}})
    check("provider path asks", '"permissionDecision": "ask"' in out and "zorg-core" in out, out)
    out = run(env, {"tool_name": "Edit", "tool_input": {"file_path": os.path.join(vault, "Notes", "Meetings", "m.md")}})
    check("own path allowed", out == "", out)
    out = run(env, {"tool_name": "Write", "tool_input": {"file_path": os.path.join(d, "ZorgCore-notes", "x.md")}})
    check("sibling folder with same prefix is allowed", out == "", out)
    out = run(env, {"tool_name": "MultiEdit", "tool_input": {"file_path": os.path.join(core, "Core", "Now.md")}})
    check("writable overlay file allowed", out == "", out)
    out = run(env, {"tool_name": "Write", "tool_input": {"file_path": os.path.join(core, "Core", "_personal", "a", "b.md")}})
    check("writable overlay folder allowed", out == "", out)
    out = run(env, {"tool_name": "NotebookEdit", "tool_input": {"notebook_path": os.path.join(core, "Core", "n.ipynb")}})
    check("notebook under provider asks", '"permissionDecision": "ask"' in out, out)
    out = run(env, {"tool_name": "mcp__Atlassian_Rovo__createJiraIssue", "tool_input": {"description": "d" * 300}})
    check("jira op still asks", '"permissionDecision": "ask"' in out and "Jira issue" in out, out)
    open(os.path.join(pdata, "config.json"), "w").write('{"write_gate": "off"}')
    out = run(env, {"tool_name": "Write", "tool_input": {"file_path": os.path.join(core, "Core", "Teams", "x.md")}})
    check("gate off allows", out == "", out)
    os.unlink(os.path.join(pdata, "config.json"))
    src = open(reg).read()
    assert "status: active" in src
    open(reg, "w").write(src.replace("status: active", "status: paused"))
    out = run(env, {"tool_name": "Write", "tool_input": {"file_path": os.path.join(core, "Core", "Teams", "x.md")}})
    check("paused registration allows", out == "", out)
    out = run({"HOME": home, "PATH": os.environ.get("PATH", "")}, {"tool_name": "Write", "tool_input": {"file_path": "/tmp/x.md"}})
    check("no context file allows", out == "", out)
    # since the final review: symlinks, the hook's cwd, a hosted session's connected folder
    open(reg, "w").write(src)                          # back to active
    link = os.path.join(d, "core-link"); os.symlink(core, link)
    out = run(env, {"tool_name": "Write", "tool_input": {"file_path": os.path.join(link, "Core", "Teams", "y.md")}})
    check("write through a symlink to the root asks", '"permissionDecision": "ask"' in out, out)
    open(reg, "w").write(src.replace(core, link))       # root registered through the symlink
    out = run(env, {"tool_name": "Write", "tool_input": {"file_path": os.path.join(core, "Core", "Teams", "y.md")}})
    check("root registered via a symlink, write via the real path asks", '"permissionDecision": "ask"' in out, out)
    open(reg, "w").write(src)
    out = run(env, {"cwd": os.path.join(core, "Core"), "tool_name": "Edit", "tool_input": {"file_path": "Teams/z.md"}})
    check("relative path resolved against the hook cwd asks", '"permissionDecision": "ask"' in out, out)
    mnt = os.path.join(home, "mnt", "Vault", ".grow-pm"); os.makedirs(mnt)
    shutil.copy(ctx, os.path.join(mnt, "local-context.md"))
    out = run({"HOME": home, "PATH": os.environ.get("PATH", ""), "CLAUDE_PLUGIN_DATA": pdata},
              {"tool_name": "Write", "tool_input": {"file_path": os.path.join(core, "Core", "Teams", "w.md")}})
    check("hosted session: context in a connected folder still guards", '"permissionDecision": "ask"' in out, out)

print("RESULT:", "GREEN ✅" if not fails else "RED ❌", "(%d failed)" % fails)
sys.exit(1 if fails else 0)
