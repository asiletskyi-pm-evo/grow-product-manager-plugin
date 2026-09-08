---
description: Typed command /grow-product-manager:setup only — never for a conversational request to change the write gate (answer by pointing to this command instead). Shows or changes the plugin's host-level toggles — currently the PreToolUse write gate — and reports whether the hooks environment is wired.
argument-hint: "[--show | --write-gate on|off]"
disable-model-invocation: true
allowed-tools: Bash(python3:*)
---

# /grow-product-manager:setup

> **Path rule.** A bare `references/<file>.md` in this file is read from the **shared** `references/` at the plugin root. Resolve the root as `${PLUGIN_ROOT}`, else `${CLAUDE_PLUGIN_ROOT}`, else the directory that contains `skills/`, found by walking up from this folder (`references/host-profiles.md` §6). Never continue without a protocol named here.

Backend: `scripts/setup.py`. One Bash call, then present the JSON as a short table.

Run exactly once:

```bash
python3 "${PLUGIN_ROOT}/scripts/setup.py"
```

`${CLAUDE_PLUGIN_ROOT}` on Claude; if neither variable expands, walk up to the directory that contains `skills/` — `references/host-profiles.md` §6.

If the user typed a toggle after the command name — `--show`, or `--write-gate on` / `--write-gate off` — append exactly that to the command above. If they typed nothing, run it bare: the script reports the current state and changes nothing.

## Present

| Setting | Value | Meaning |
|---|---|---|
| Write gate | on / off | `on` = the host asks for confirmation before `createJiraIssue` / `createConfluencePage` and content-bearing `editJiraIssue` / `updateConfluencePage` (`hooks/hooks.json` → PreToolUse). `off` = silent. |
| Config path | … | where the toggle is stored (plugin data dir; never `local-context.md`) |
| Hooks env | CLAUDE_PLUGIN_DATA / CLAUDE_ENV_FILE / GROW_PM_CONTEXT_PATH | whether the SessionStart hook ran in this session and found the context |

Then one line: what changed (or "no changes"). Nothing else — no onboarding, no context edits (those belong to `plugin-configurator`).

Turning the write gate off is the user's decision to publish without the host prompt; the artifact quality gate in the skills still runs.
