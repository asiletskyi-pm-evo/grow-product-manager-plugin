#!/usr/bin/env python3
"""Grow PM — PreToolUse write gate (since v2.6.0).

Runs before createJiraIssue / editJiraIssue / createConfluencePage /
updateConfluencePage on any connector. It does NOT judge the artifact — a hook
sees only the tool call, never the conversation (hooks reference: prompt/command
hooks receive the hook input JSON). What it can do deterministically is put a
human in the loop before an irreversible write, with the checklist the artifact
quality gate expects to have been completed by then:

  permissionDecision: "ask" → the host shows the reason and waits for the user.

Since v3.10.0 it also runs before Write / Edit / MultiEdit / NotebookEdit: a
file under a registered shared-context provider's local folder, outside the
folder's `writable` globs, gets the same "ask" with the reason and the
alternative (references/context-provider-protocol.md §7). Everything else
passes silently.

Metadata-only edits (status, labels, title) pass silently. The gate is opt-out:
`/grow-product-manager:setup --write-gate off` writes {"write_gate": "off"} to
the plugin data dir. Fail open: any error → exit 0, no output (= allow).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

CONTENT_KEYS = ("description", "body", "content", "bodyContent", "value", "text")
FILE_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit")
MIN_CONTENT = 200  # characters — below this an edit is metadata, not an artifact


def config_paths():
    out = []
    d = os.environ.get("CLAUDE_PLUGIN_DATA")
    if d:
        out.append(os.path.join(d, "config.json"))
    out.append(os.path.join(os.path.expanduser("~"), ".grow-pm", "plugin-data", "config.json"))
    return out


def write_gate_enabled():
    for p in config_paths():
        try:
            with open(p, encoding="utf-8") as f:
                cfg = json.load(f)
            if str(cfg.get("write_gate", "on")).lower() in ("off", "false", "0"):
                return False
            return True
        except Exception:
            continue
    return True


def content_size(obj):
    """Longest content-like string anywhere in tool_input."""
    best = 0
    stack = [obj]
    while stack:
        cur = stack.pop()
        if isinstance(cur, dict):
            for k, v in cur.items():
                if isinstance(v, str) and any(c in k.lower() for c in CONTENT_KEYS):
                    best = max(best, len(v))
                elif isinstance(v, (dict, list)):
                    stack.append(v)
        elif isinstance(cur, list):
            stack.extend(cur)
    return best


def context_text(cwd=None):
    """The user's local-context.md: the digest's path, the canonical store, then every place the
    SessionStart digest searches (connected folders in hosted sessions, the working directory)."""
    cands = [os.environ.get("GROW_PM_CONTEXT_PATH"), os.path.join(os.path.expanduser("~"), ".grow-pm", "local-context.md")]
    try:
        import session_start
        cands += session_start.candidates(cwd or os.getcwd())
    except Exception:
        pass
    for p in cands:
        if p and os.path.isfile(p):
            with open(p, encoding="utf-8", errors="replace") as f:
                return f.read()
    return ""


def provider_hit(tool_input, cwd=None):
    """The provider registration whose read-only folder holds the target, or None."""
    path = str(tool_input.get("file_path") or tool_input.get("notebook_path") or "")
    if not path:
        return None, ""
    if not os.path.isabs(os.path.expanduser(path)) and cwd:
        path = os.path.join(cwd, path)           # the hook input's cwd, not this process's
    import ctx_common as cc
    text = context_text(cwd)
    regs = cc.find_registrations(cc.vault_entries(text) if text else [])
    return cc.boundary_hit(path, regs), path


def ask(reason):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "ask",
        "permissionDecisionReason": reason,
    }}))


def main():
    raw = sys.stdin.read()
    data = json.loads(raw) if raw.strip() else {}
    tool = str(data.get("tool_name", ""))
    tool_input = data.get("tool_input") or {}
    if not tool or not write_gate_enabled():
        return
    if tool in FILE_TOOLS:
        hit, path = provider_hit(tool_input, data.get("cwd"))
        if hit:
            ask("Grow PM provider boundary: %s is inside the local folder of the shared-context provider "
                "'%s', which is read-only for this plugin (references/context-provider-protocol.md §7). "
                "Write the note in your own vault layer instead, or record a correction in your overlay "
                "note for this provider; confirm only if you mean to edit the provider's copy. "
                "Disable with /grow-product-manager:setup --write-gate off." % (path, hit.get("title") or hit.get("id")))
        return
    op = tool.rsplit("__", 1)[-1]
    if op not in ("createJiraIssue", "editJiraIssue", "createConfluencePage", "updateConfluencePage"):
        return  # not a gated operation (defensive: the matcher should already exclude it)
    if op in ("editJiraIssue", "updateConfluencePage") and content_size(tool_input) < MIN_CONTENT:
        return  # metadata-only edit — no prompt
    target = "Jira issue" if "Jira" in op else "Confluence page"
    verb = "create" if op.startswith("create") else "update"
    reason = (
        "Grow PM write gate: about to %s a %s via %s. Before confirming, check the chat for: "
        "(1) the artifact quality gate report line (\"checker: …\" / maker–checker findings applied) — "
        "references/artifact-style-gate.md; (2) your explicit go-ahead to publish this artifact; "
        "(3) that this is the intended space/project, not a sandbox. "
        "Disable this prompt with /grow-product-manager:setup --write-gate off."
        % (verb, target, tool)
    )
    ask(reason)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
