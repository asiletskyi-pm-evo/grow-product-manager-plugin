#!/usr/bin/env python3
"""TC-hook-3100-boundary — scripts/write_gate.py, the PreToolUse gate.

Since v3.10.0 the gate also guards file writes under a shared-context provider's
local folders (references/context-provider-protocol.md §7): Write / Edit /
MultiEdit / NotebookEdit under a registered root and outside its `writable` globs
→ permissionDecision "ask"; anything else → no output (allow). The Jira /
Confluence branch also covers the Confluence writes' Atlassian MCP v2 names
(createConfluenceContent / updateConfluenceContent). Each case runs the script as a subprocess with an
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
    # Atlassian MCP v2: the Confluence writes are createConfluenceContent / updateConfluenceContent
    v2 = "mcp__claude_ai_Atlassian_MCP__"
    out = run(env, {"tool_name": v2 + "createConfluenceContent", "tool_input": {
        "contentType": "page", "title": "T", "body": {"format": "html", "value": "p" * 300}}})
    check("v2 Confluence create asks", '"permissionDecision": "ask"' in out and "create a Confluence page" in out, out)
    out = run(env, {"tool_name": v2 + "updateConfluenceContent", "tool_input": {
        "contentId": "1", "snapshotToken": "v:7", "edits": [{"name": "replaceNode", "localId": "a", "value": "p" * 300}]}})
    check("v2 Confluence update with content asks", '"permissionDecision": "ask"' in out and "update a Confluence page" in out, out)
    out = run(env, {"tool_name": v2 + "updateConfluenceContent", "tool_input": {"contentId": "1", "title": "Renamed"}})
    check("v2 Confluence title-only update passes silently", out == "", out)
    out = run(env, {"tool_name": v2 + "executeWrite", "tool_input": {
        "name": "createConfluenceComment", "inputs": {"body": {"format": "markdown", "value": "c" * 300}}}})
    check("v2 executeWrite is not gated, as v1 comments and links were not", out == "", out)
    import re
    hooks = json.load(open(os.path.join(ROOT, "hooks", "hooks.json")))["hooks"]["PreToolUse"]
    matcher = [h["matcher"] for h in hooks if "Jira" in h["matcher"]][0]
    for op in ("createJiraIssue", "editJiraIssue", "createConfluencePage", "updateConfluencePage",
               "createConfluenceContent", "updateConfluenceContent"):
        check("hooks.json matcher covers " + op, re.search(matcher, v2 + op) is not None, matcher)
    check("hooks.json matcher skips executeWrite", re.search(matcher, v2 + "executeWrite") is None, matcher)
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
    out = run(env, {"tool_name": "Edit", "tool_input": {"file_path": note,
                    "old_string": "<!-- ctx:end id=hub-meeting-notes -->\n",
                    "new_string": "<!-- ctx:end id=hub-meeting-notes -->\nMore of mine.\n"}})
    check("v4.0.0 final review I2: an Edit that appends after a region's end marker (the note's last line) — every "
          "region as it was — passes silently", out == "", out)
    upper = note.replace(os.sep + "Vault" + os.sep, os.sep + "VAULT" + os.sep)
    out = run(env, {"tool_name": "Edit", "tool_input": {"file_path": upper, "old_string": "- [[Standup]]",
                                                        "new_string": "x"}})
    check("v4.0.0 review M-6: the same note named in another case (APFS) is still the gate's",
          not os.path.exists(upper) or '"permissionDecision": "ask"' in out, out)
    out = run(env, {"tool_name": "MultiEdit", "tool_input": {"file_path": note, "edits": [
        {"old_string": "Mine.", "new_string": "Mine. <!-- ctx:begin id=z -->"},
        {"old_string": "id=z -->", "new_string": "id=y -->"}]}})
    check("v4.0.0 review M-7: a MultiEdit whose later edit touches what an earlier one made a marker asks",
          '"permissionDecision": "ask"' in out, out)
    open(os.path.join(pdata, "config.json"), "w").write('{"write_gate": "off"}')
    out = run(env, {"tool_name": "Edit", "tool_input": {"file_path": note, "old_string": "- [[Standup]]", "new_string": "x"}})
    check("…write_gate off: no question", out == "", out)
    os.unlink(os.path.join(pdata, "config.json"))

    # the write-gate pause: `write_gate_pause_until` silences the Jira / Confluence question until a UTC time, never
    # longer than MAX_PAUSE_MINUTES; the provider-boundary and generated-region questions stay on
    from datetime import datetime, timedelta, timezone
    cfg_path = os.path.join(pdata, "config.json")
    def pause_for(value):
        open(cfg_path, "w").write(json.dumps({"write_gate_pause_until": value}))
    def read_cfg():
        try:
            return json.load(open(cfg_path))
        except (OSError, ValueError):
            return {}
    def iso(minutes):
        return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")
    jira = {"tool_name": "mcp__Atlassian_Rovo__createJiraIssue", "tool_input": {"description": "d" * 300}}
    upd = {"tool_name": v2 + "updateConfluenceContent", "tool_input": {
        "contentId": "1", "snapshotToken": "v:7", "body": {"format": "html", "value": "p" * 300}}}
    asks = lambda o: '"permissionDecision": "ask"' in o

    pause_for(iso(30))
    out = run(env, jira)
    check("pause: an active pause lets a Jira create through with no question", out == "", out)
    out = run(env, upd)
    check("pause: …and a v2 Confluence update with content", out == "", out)
    out = run(env, {"tool_name": "Write", "tool_input": {"file_path": os.path.join(core, "Core", "Teams", "x.md")}})
    check("pause: the provider-boundary question still fires during a pause", asks(out) and "zorg-core" in out, out)
    out = run(env, {"tool_name": "Edit", "tool_input": {"file_path": note, "old_string": "- [[Standup]]",
                                                        "new_string": "x"}})
    check("pause: the generated-region question still fires during a pause", asks(out) and "generated region" in out, out)
    pause_for(iso(30).replace("Z", "+00:00"))
    out = run(env, jira)
    check("pause: an explicit +00:00 offset is read like Z", out == "", out)

    pause_for(iso(-1))
    out = run(env, jira)
    check("pause: an expired pause asks again on its own, saying the pause ended",
          asks(out) and "pause" in out and "ended" in out, out)
    for bad, why in (("tomorrow", "not a time"), ("2026-13-01T00:00:00Z", "no 13th month"),
                     (iso(30)[:-1], "no zone (naive)"), (1767225600, "a number"), ("", "empty"),
                     (iso(60 * 24 * 365), "a year — over the cap, a permanent off in disguise")):
        pause_for(bad)
        out = run(env, jira)
        check("pause: a malformed value asks (fail closed) — " + why, asks(out) and "not a valid pause" in out, out)
    open(cfg_path, "w").write('{"write_gate_pause_until": ')
    out = run(env, jira)
    check("pause: a config that is not JSON leaves the gate on (asks)", asks(out), out)
    os.unlink(cfg_path)
    out = run(env, jira)
    check("pause: the ordinary question names the pause and that it covers Jira / Confluence only",
          asks(out) and "--write-gate pause" in out and "Jira/Confluence only" in out, out)

    # dry run: updateConfluenceContent with dryRun true persists nothing — no question; nothing else is a dry run
    dry = {"tool_name": v2 + "updateConfluenceContent", "tool_input": dict(upd["tool_input"], dryRun=True)}
    out = run(env, dry)
    check("dry run: updateConfluenceContent with dryRun true passes with no question", out == "", out)
    out = run(env, {"tool_name": v2 + "updateConfluenceContent", "tool_input": dict(upd["tool_input"], dryRun="true")})
    check("dry run: dryRun as the string \"true\" is not a dry run (asks)", asks(out), out)
    out = run(env, {"tool_name": v2 + "updateConfluenceContent", "tool_input": dict(upd["tool_input"], dryRun=False)})
    check("dry run: dryRun false asks", asks(out), out)
    out = run(env, {"tool_name": v2 + "createConfluenceContent", "tool_input": {
        "contentType": "page", "title": "T", "body": {"format": "html", "value": "p" * 300}, "dryRun": True}})
    check("dry run: a create has no dry run — dryRun on it still asks", asks(out), out)
    out = run(env, {"tool_name": "mcp__Atlassian_Rovo__editJiraIssue", "tool_input": {
        "issueIdOrKey": "PROJ-1234", "fields": {"description": "d" * 300}, "dryRun": True}})
    check("dry run: a Jira edit has no dry run — still asks", asks(out), out)

    # setup.py — `--write-gate pause <minutes>` writes the pause, `--write-gate on` clears it
    SETUP = os.path.join(ROOT, "scripts", "setup.py")
    def setup(*args):
        p = subprocess.run([sys.executable, SETUP] + list(args), capture_output=True, text=True, env=env, timeout=20)
        try:
            return p.returncode, json.loads(p.stdout)
        except ValueError:
            return p.returncode, {"raw": p.stdout + p.stderr}
    t0 = datetime.now(timezone.utc)
    rc, st = setup("--write-gate", "pause", "45")
    cfg = read_cfg()
    until = cfg.get("write_gate_pause_until", "")
    try:
        left = (datetime.fromisoformat(until.replace("Z", "+00:00")) - t0).total_seconds() / 60
    except ValueError:
        left = -1
    check("setup: --write-gate pause 45 writes a UTC time ~45 minutes ahead",
          rc == 0 and until.endswith("Z") and 44 <= left <= 46 and st.get("changed") is True, (rc, st, cfg))
    check("setup: …and reports the pause with its end and the minutes left",
          st.get("write_gate_pause_until") == until and st.get("write_gate_paused") is True
          and 44 <= (st.get("write_gate_pause_minutes_left") or 0) <= 45, st)
    out = run(env, jira)
    check("setup → gate: the pause setup wrote silences the Jira question", out == "", out)
    for bad in (["0"], ["241"], ["abc"], ["-5"], []):
        rc, st = setup("--write-gate", "pause", *bad)
        check("setup: pause %s is refused (1–240 minutes), nothing changed" % (bad or "with no minutes"),
              rc == 2 and "error" in st and read_cfg().get("write_gate_pause_until") == until, (rc, st))
    rc, st = setup("--write-gate", "on")
    cfg = read_cfg()
    check("setup: --write-gate on clears the pause", rc == 0 and "write_gate_pause_until" not in cfg
          and cfg.get("write_gate") == "on" and st.get("write_gate_paused") is False, (rc, st, cfg))
    out = run(env, jira)
    check("setup → gate: after --write-gate on the gate asks again", asks(out), out)
    open(cfg_path, "w").write('{"write_gate": "off"}')
    rc, st = setup("--write-gate", "pause", "10")
    cfg = read_cfg()
    check("setup: a pause on a gate that was off turns it on, so the question returns when the pause ends",
          rc == 0 and cfg.get("write_gate") == "on" and cfg.get("write_gate_pause_until"), (rc, cfg))
    rc, st = setup("--write-gate", "off")
    cfg = read_cfg()
    check("setup: --write-gate off drops a pause it makes moot", rc == 0 and cfg.get("write_gate") == "off"
          and "write_gate_pause_until" not in cfg, (rc, cfg))
    pause_for(iso(-5))
    rc, st = setup("--show")
    check("setup: --show reports an expired pause as not paused", rc == 0 and st.get("write_gate_paused") is False
          and st.get("write_gate_pause_state") == "expired", st)
    os.unlink(cfg_path)

# ---- since v4.11.1: executeDestructive always asks; a Bash approval of a provider's address asks; a pause covers neither
with tempfile.TemporaryDirectory() as d:
    home = os.path.join(d, "home"); os.makedirs(home)
    pdata = os.path.join(d, "plugin-data"); os.makedirs(pdata)
    env = {"HOME": home, "PATH": os.environ.get("PATH", ""), "GROW_PM_CONTEXT_PATH": os.path.join(d, "none.md"), "CLAUDE_PLUGIN_DATA": pdata}
    v2 = "mcp__claude_ai_Atlassian_MCP__"
    out = run(env, {"tool_name": v2 + "executeDestructive", "tool_input": {"name": "deleteConfluencePage", "cloudId": "x", "inputs": {"id": "1"}}})
    check("v4.11.1 executeDestructive asks, naming the operation", '"permissionDecision": "ask"' in out and "deleteConfluencePage" in out, out)
    out = run(env, {"tool_name": "Bash", "tool_input": {"command": 'python3 "/p/scripts/ctx.py" provider trust zorg-core --code 4f2a'}})
    check("v4.11.1 a Bash `provider trust … --code` asks", '"permissionDecision": "ask"' in out and "trust" in out, out)
    out = run(env, {"tool_name": "Bash", "tool_input": {"command": 'python3 "/p/scripts/ctx.py" provider trust zorg-core'}})
    check("…`provider trust <id>` without --code (it only reads) passes silently", out == "", out)
    out = run(env, {"tool_name": "Bash", "tool_input": {"command": "ls -la && git status"}})
    check("…any other command passes silently", out == "", out)
    until = (__import__("datetime").datetime.now(__import__("datetime").timezone.utc) + __import__("datetime").timedelta(minutes=30)).isoformat()
    open(os.path.join(pdata, "config.json"), "w").write(json.dumps({"write_gate": "on", "write_gate_pause_until": until}))
    out = run(env, {"tool_name": v2 + "executeDestructive", "tool_input": {"name": "deleteJiraIssue"}})
    out2 = run(env, {"tool_name": "Bash", "tool_input": {"command": "ctx provider trust a --code 1"}})
    check("…a write-gate pause covers neither", '"permissionDecision": "ask"' in out and '"permissionDecision": "ask"' in out2, (out, out2))
    import re as _re
    hooks = json.load(open(os.path.join(ROOT, "hooks", "hooks.json")))["hooks"]["PreToolUse"]
    ms = [h["matcher"] for h in hooks]
    check("…hooks.json wires both: a matcher for executeDestructive and one for Bash",
          any(_re.search(m, v2 + "executeDestructive") for m in ms) and any(_re.search(m, "Bash") for m in ms), ms)

# ---- the re-audit of 2026-11-25: the agent can never turn the gate off on its own; `--code` abbreviated or on a new line
with tempfile.TemporaryDirectory() as d:
    home = os.path.join(d, "home"); os.makedirs(home)
    pdata = os.path.join(d, "plugin-data"); os.makedirs(pdata)
    env = {"HOME": home, "PATH": os.environ.get("PATH", ""), "GROW_PM_CONTEXT_PATH": os.path.join(d, "none.md"), "CLAUDE_PLUGIN_DATA": pdata}
    v2 = "mcp__claude_ai_Atlassian_MCP__"
    ASK = '"permissionDecision": "ask"'
    def bash(cmd):
        return run(env, {"tool_name": "Bash", "tool_input": {"command": cmd}})
    for cmd, why in (("ctx provider trust a --cod 1", "--cod"), ("ctx provider trust a --co 1", "--co"),
                     ("ctx provider trust a --c=1", "--c="), ("ctx provider trust a \\\n  --code 1", "a new line before --code")):
        check("re-audit: `provider trust` asks with %s" % why, ASK in bash(cmd), cmd)
    check("re-audit: `--context` after `provider trust` is no --code abbreviation (passes)", bash("ctx provider trust a --context x") == "")
    for cmd in ('python3 "/p/scripts/setup.py" --write-gate off', 'python3 /p/scripts/setup.py --write-gate pause 240',
                "python3 /p/scripts/setup.py --write-g off"):
        check("re-audit: a Bash that changes the gate asks — " + cmd, ASK in bash(cmd) and "write gate" in bash(cmd), cmd)
    check("re-audit: setup.py without --write-gate passes", bash("python3 /p/scripts/setup.py --status") == "")
    for cmd, why in (('ctx provider trust a "--code" 1', "a quoted --code"),
                     ("python3 -c 'import setup; setup.main([\"--write-gate\", \"off\"])'", "setup imported"),
                     ("cd ~/.grow-pm/plugin-data && echo {} > config.json", "cd into plugin-data"),
                     ("rm -rf ~/.grow-pm/trust ~/.grow-pm/.trust-seeded", "the trust store removed"),
                     ("sed -i s/ask/allow/ /p/scripts/write_gate.py", "the gate's own script"),
                     ('cp /dev/null "$CLAUDE_PLUGIN_ROOT/hooks/hooks.json"', "hooks.json"),
                     ("ctx provider 'trust' a --code 1", "a quoted trust"),
                     ("cd ~/.grow-pm && rm -r trust .trust-seeded", "a delete under ~/.grow-pm"),
                     ("echo x > %s/config.json" % pdata, "the expanded plugin-data path")):
        check("re-audit 2: asks — " + why, ASK in bash(cmd), cmd)
    for cmd, why in (("npm run setup -- --watch", "another project's setup"), ("cat hooks/hooks.json 2>/dev/null", "a read with 2>/dev/null"),
                     ("ls ~/.grow-pm", "a listing of ~/.grow-pm")):
        check("re-audit 2: passes — " + why, bash(cmd) == "", cmd)
    for cmd in ("echo '{\"write_gate\":\"off\"}' > \"$CLAUDE_PLUGIN_DATA/config.json\"",
                "python3 -c 'open(\"%s/.grow-pm/plugin-data/config.json\",\"w\")'" % home,
                "cp x ~/.grow-pm/trust/addresses.json"):
        check("re-audit: a Bash that writes the gate's config or the trust file asks — " + cmd[:40], ASK in bash(cmd), cmd)
    check("re-audit: reading the config passes", bash("cat \"$CLAUDE_PLUGIN_DATA/config.json\"") == "")
    for path in (os.path.join(pdata, "config.json"), os.path.join(home, ".grow-pm", "plugin-data", "config.json"),
                 os.path.join(home, ".grow-pm", "trust", "addresses.json")):
        out = run(env, {"tool_name": "Write", "tool_input": {"file_path": path, "content": "{}"}})
        check("re-audit: a Write of %s asks" % os.path.relpath(path, d), ASK in out, out)
    out = run(env, {"tool_name": "Write", "tool_input": {"file_path": os.path.join(d, "notes.md"), "content": "x"}})
    check("re-audit: a Write elsewhere passes", out == "", out)
    for path, why in ((os.path.join(home, ".GROW-PM", "Trust", "x.json"), "the trust store in other case"),
                      (os.path.join(home, ".grow-pm", ".trust-seeded"), ".trust-seeded"),
                      (os.path.join(ROOT, "scripts", "write_gate.py"), "the gate's own script"),
                      (os.path.join(ROOT, "hooks", "hooks.json"), "hooks.json"),
                      (os.path.join(ROOT, "scripts", "ctx_common.py"), "any file of the plugin")):
        out = run(env, {"tool_name": "Edit", "tool_input": {"file_path": path, "old_string": "a", "new_string": "b"}})
        check("re-audit 2: an Edit asks — " + why, ASK in out, out)
    out = run(env, {"tool_name": "Write", "cwd": pdata, "tool_input": {"file_path": "config.json", "content": "{}"}})
    check("re-audit 2: a relative path is read against the hook's cwd", ASK in out, out)
    open(os.path.join(pdata, "config.json"), "w").write(json.dumps({"write_gate": "off"}))
    check("re-audit: with the gate OFF, trust still asks", ASK in bash("ctx provider trust a --code 1"))
    check("…and setup --write-gate on|off still asks", ASK in bash("python3 /p/scripts/setup.py --write-gate on"))
    out = run(env, {"tool_name": v2 + "executeDestructive", "tool_input": {"name": "deleteJiraIssue"}})
    check("…and executeDestructive still asks", ASK in out, out)
    out = run(env, {"tool_name": "Edit", "tool_input": {"file_path": os.path.join(pdata, "config.json"), "old_string": "off", "new_string": "on"}})
    check("…and an Edit of the config still asks", ASK in out, out)
    out = run(env, {"tool_name": v2 + "createJiraIssue", "tool_input": {"projectKey": "X"}})
    check("…while the ordinary Jira question is off, as configured", out == "", out)

print("RESULT:", "GREEN ✅" if not fails else "RED ❌", "(%d failed)" % fails)
sys.exit(1 if fails else 0)
