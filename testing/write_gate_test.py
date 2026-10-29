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
    # since v3.14: a registration iCloud has not downloaded — the boundary cannot be checked, so the gate asks
    import time
    slow = os.path.join(regdir, "zorg-slow.yaml"); os.mkfifo(slow)
    try:
        t0 = time.time()
        try:
            out = run(env, {"tool_name": "Write", "tool_input": {"file_path": os.path.join(vault, "Notes", "Meetings", "m.md")}})
        except subprocess.TimeoutExpired:
            out = "the gate still waits for the registration after 20 s"
        took = time.time() - t0
    finally:
        try:
            os.close(os.open(slow, os.O_WRONLY | os.O_NONBLOCK))
        except OSError:
            pass
        os.remove(slow)
    check("a registration that is not read in time: the gate asks (the boundary cannot be checked), within its 6 s and a margin",
          '"permissionDecision": "ask"' in out and "could not be read" in out and "zorg-slow.yaml" in out and took < 9.5,
          (round(took, 2), out))
    out = run(env, {"tool_name": "Edit", "tool_input": {"file_path": os.path.join(vault, "Notes", "Meetings", "m.md")}})
    check("…and once it is read again, an own path passes silently", out == "", out)

    # since v4.0.0: a generated region of a note in a vault — the gate asks before a Write or an Edit that changes it
    note = os.path.join(vault, "Notes", "Meetings", "hub.md")
    os.makedirs(os.path.dirname(note), exist_ok=True)
    body = ("# Hub\n\nMine.\n\n<!-- ctx:begin id=hub-meeting-notes -->\n- [[Standup]]\n"
            "<!-- ctx:end id=hub-meeting-notes -->\n")
    open(note, "w").write(body)
    out = run(env, {"tool_name": "Edit", "tool_input": {"file_path": note, "old_string": "- [[Standup]]",
                                                        "new_string": "- [[Other]]"}})
    check("v4.0.0 an Edit inside a generated region asks, naming the region and the way out",
          '"permissionDecision": "ask"' in out and "ctx id=hub-meeting-notes" in out and "re-run" in out, out)
    out = run(env, {"tool_name": "Edit", "tool_input": {"file_path": note, "old_string": "Mine.", "new_string": "Ours."}})
    check("…an Edit outside every region passes silently", out == "", out)
    out = run(env, {"tool_name": "MultiEdit", "tool_input": {"file_path": note, "edits": [
        {"old_string": "Mine.", "new_string": "Ours."}, {"old_string": "<!-- ctx:end id=hub-meeting-notes -->",
                                                          "new_string": ""}]}})
    check("…a MultiEdit with one edit on a marker asks", '"permissionDecision": "ask"' in out, out)
    out = run(env, {"tool_name": "Write", "tool_input": {"file_path": note, "content": body.replace("Mine.", "Ours.")}})
    check("…a Write that keeps every region as it is passes silently", out == "", out)
    out = run(env, {"tool_name": "Write", "tool_input": {"file_path": note, "content": "# Hub\n\nOurs.\n"}})
    check("…a Write that drops a region asks", '"permissionDecision": "ask"' in out, out)
    out = run(env, {"tool_name": "Write", "tool_input": {"file_path": os.path.join(vault, "Notes", "new.md"),
                                                         "content": body}})
    check("…a new note passes silently", out == "", out)
    store_rec = os.path.join(vault, "Notes", "_System", "context", "records", "team.alpha.md")
    os.makedirs(os.path.dirname(store_rec), exist_ok=True)
    open(store_rec, "w").write("<!-- zorg-core:begin id=team v=0.1 -->\nA\n<!-- zorg-core:end id=team -->\n")
    out = run(env, {"tool_name": "Edit", "tool_input": {"file_path": store_rec, "old_string": "A", "new_string": "B"}})
    check("…a record of the store is not the gate's: a human edit in a provider block is legal there (§12)", out == "", out)
    lc = os.path.join(vault, "Notes", "_System", "local-context.md")
    open(lc, "w").write("<!-- zorg-core:begin id=org v=0.1 -->\nA\n<!-- zorg-core:end id=org -->\n")
    out = run(env, {"tool_name": "Edit", "tool_input": {"file_path": lc, "old_string": "A", "new_string": "B"}})
    check("…nor local-context.md", out == "", out)
    outside = os.path.join(d, "elsewhere.md")
    open(outside, "w").write(body)
    out = run(env, {"tool_name": "Edit", "tool_input": {"file_path": outside, "old_string": "- [[Standup]]",
                                                        "new_string": "x"}})
    check("…a file outside every vault is not the gate's", out == "", out)
    open(os.path.join(pdata, "config.json"), "w").write('{"write_gate": "off"}')
    out = run(env, {"tool_name": "Edit", "tool_input": {"file_path": note, "old_string": "- [[Standup]]", "new_string": "x"}})
    check("…write_gate off: no question", out == "", out)
    os.unlink(os.path.join(pdata, "config.json"))

print("RESULT:", "GREEN ✅" if not fails else "RED ❌", "(%d failed)" % fails)
sys.exit(1 if fails else 0)
