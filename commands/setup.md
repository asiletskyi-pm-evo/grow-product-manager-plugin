---
description: Show or change the plugin's host-level toggles — currently the PreToolUse write gate (confirmation before Jira/Confluence writes) — and report whether the hooks environment is wired
argument-hint: "[--show | --write-gate on|off]"
disable-model-invocation: true
allowed-tools: Bash(python3:*)
---

# /grow-product-manager:setup

Backend: `scripts/setup.py`. One Bash call, then present the JSON as a short table.

!`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/setup.py" $ARGUMENTS`

## Present

| Setting | Value | Meaning |
|---|---|---|
| Write gate | on / off | `on` = the host asks for confirmation before `createJiraIssue` / `createConfluencePage` and content-bearing `editJiraIssue` / `updateConfluencePage` (`hooks/hooks.json` → PreToolUse). `off` = silent. |
| Config path | … | where the toggle is stored (plugin data dir; never `local-context.md`) |
| Hooks env | CLAUDE_PLUGIN_DATA / CLAUDE_ENV_FILE / GROW_PM_CONTEXT_PATH | whether the SessionStart hook ran in this session and found the context |

Then one line: what changed (or "no changes"). Nothing else — no onboarding, no context edits (those belong to `plugin-configurator`).

Turning the write gate off is the user's decision to publish without the host prompt; the artifact quality gate in the skills still runs.
