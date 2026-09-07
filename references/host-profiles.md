# host-profiles.md

> Shared reference. The plugin runs on more than one host (Claude Code / Cowork, Codex CLI, ChatGPT, Codex Cloud). Hosts differ in what they *can do*, not in what the skills *mean*. This file defines how a skill learns which capabilities it has and what each contour does when a capability is missing. Consumed by `persistent-storage.md`, `subagent-delegation.md`, `artifact-style-gate.md`, `integration-strategy.md` and by any skill's Step 0.
>
> **Rule of the file:** never branch on a brand name. Branch on an **observed capability**. A host that grows a capability tomorrow then works without a plugin change.

## 1. The five capabilities that matter

| Capability | How to observe it | If absent |
|---|---|---|
| **FS** — a filesystem the user's data survives in | a file-read/write tool is present *and* a home-like path resolves (`~/.grow-pm/`, or a connected folder) | `persistent-storage.md` → storage mode `connector` or `session` |
| **SHELL** — running commands / scripts | a bash-like tool is present | no `scripts/*.py`; every deterministic step degrades to prose the model executes |
| **SUBAGENT** — spawning an independent agent with a fresh context | an agent/task tool is present **and** the host spawns without asking the user each time | `subagent-delegation.md` → inline passes; `artifact-style-gate.md` → sequential lens passes |
| **MCP** — connector tools in the session | tools matching `mcp__<id>__<tool>` are listed | `integration-strategy.md` Step 2 → Step 3 |
| **HOOKS** — deterministic host-side gates | the SessionStart digest `GROW_PM_SESSION` is present in context | `local-context-protocol.md` Step 0a runs in full; write gate becomes an in-skill confirmation |

**Do not ask the user which host they are on.** Every row above is observable from the session itself.

## 2. Profiles

Profiles are shorthand for a capability set. They are documentation, not a switch.

| Profile | FS | SHELL | SUBAGENT | MCP | HOOKS | Notes |
|---|---|---|---|---|---|---|
| `claude-cowork` | ✅ | ✅ | ✅ | ✅ | ✅ | Reference host. Everything in the plugin is defined against it. |
| `codex-cli` | ✅ | ✅ | ⚠️ | ✅ | ❌ | Codex spawns a subagent only on an explicit user request → treat SUBAGENT as absent unless the user asked for it. Plugin agents (`agents/*.md`) are not loaded; hooks are not loaded. |
| `chatgpt` | ❌ | ❌ | ❌ | ✅ | ❌ | Skills and connectors only. The storage, vault and script contours are unavailable. |
| `codex-cloud` | ⚠️ | ✅ | ⚠️ | ? | ❌ | Its own sandbox filesystem — **not** the user's `~/.grow-pm/`. Treat FS as present but empty: never assume prior state, always write results back through a connector or the repo. |

## 3. Step 0h — the host check

Any skill that touches storage, subagents or scripts runs this before its first real step. It is three lines of reasoning, not a tool call:

1. Look at the tool list actually available in this session.
2. Mark the five capabilities from §1 as present / absent.
3. Carry that mark for the whole run — do not re-derive it per step.

Then, and only then, resolve the contours that depend on it (storage mode, delegation mode, gate mode).

**Report once, not repeatedly.** When a capability the user's request needs is absent, say it in one line at the start — "no local storage on this host, the artifact will be delivered in the chat and not saved to the vault" — and continue. Never fail silently, and never repeat the caveat in every step.

## 4. What each contour does per capability

| Contour | Full | Degraded | Unavailable |
|---|---|---|---|
| Config (`local-context.md`) | read from `~/.grow-pm/` | read from a connected folder / an uploaded file / a connector document | ask the user for the three fields the current skill actually needs; never run full onboarding |
| Artifact storage | `~/.grow-pm/` + vault mirror | connector-backed root (Drive folder / Confluence space) | session-only + mandatory export at the end |
| Quality gate | two checker subagents, distinct lenses | sequential inline lens passes, role reset between them | single self-check, marked as reduced independence |
| Fan-out reads | parallel `extractor` subagents | sequential batches inline | fewer sources, stated explicitly |
| Deterministic scripts | `scripts/*.py` | the same logic as prose steps | — |
| Write gate | PreToolUse hook (`ask`) | in-skill confirmation before the write step | — |

## 5. Contours that have no meaningful degraded mode

These need FS. On a host without it, the skill says so in one line and stops instead of pretending:

- `focus-advisor` → Focus Board (`~/.grow-pm/focus/`)
- `experiment-tracker` → `registry.yaml`
- the whole People contour (`one-on-one`, `performance-review`, `delegation-coach`, `offboarding-guide`, `hiring-designer`) → person profiles are strictly local by `people-context-protocol.md`
- `template-library`, `knowledge-library` → local library and glossary

Read-only modes of these skills still work when the user pastes the data into the session.

## 6. Path variables

`${PLUGIN_ROOT}` is the portable variable (Agent Plugins 1.0); `${CLAUDE_PLUGIN_ROOT}` is the Claude-specific one. Anything that needs the plugin root resolves in this order:

1. `${PLUGIN_ROOT}`
2. `${CLAUDE_PLUGIN_ROOT}`
3. the directory that contains `skills/`, found by walking up from the current skill's folder

Never hardcode an absolute path, and never assume either variable expanded — a literal `${...}` left in the text means the host did not define it, which is signal, not an error to hide.

## 7. Known host gaps (v3.0.0)

Facts, measured — see `Codex-Compat-Findings.md` in the design workspace:

- **Codex truncates a skill's `description` at ~530 characters.** Anything a skill needs *for routing* — triggers, "Do NOT use" boundaries — must fit in the first 500 characters of the description; the rest belongs in the body of `SKILL.md`.
- **Codex does not load `agents/*.md` or `hooks/hooks.json`** from a plugin (hooks: openai/codex#17331).
- **Codex skips a command whose body contains `$1` or `$ARGUMENTS`** when migrating `commands/` into skills.
- **A marketplace entry needs a string `source`** (`"."` or `"./subdir"`); the object form is silently ignored.
