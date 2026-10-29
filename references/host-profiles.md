# host-profiles.md

> Shared reference. The plugin runs on more than one host (Claude Code / Cowork, Codex CLI, ChatGPT, Codex Cloud). Hosts differ in what they *can do*, not in what the skills *mean*. This file defines how a skill learns which capabilities it has and what each contour does when a capability is missing. Consumed by `persistent-storage.md`, `subagent-delegation.md`, `artifact-style-gate.md`, `integration-strategy.md` and by any skill's Step 0.
>
> **Rule of the file:** never branch on a brand name. Branch on an **observed capability**. A host that grows a capability tomorrow then works without a plugin change.

## 1. The capabilities that matter

| Capability | How to observe it | If absent |
|---|---|---|
| **FS** — a filesystem the user's data survives in | a file-read/write tool is present *and* a home-like path resolves (`~/.grow-pm/`, or a connected folder) | `persistent-storage.md` → storage mode `connector` or `session` |
| **SHELL** — running commands / scripts | a bash-like tool is present | no `scripts/*.py`; every deterministic step degrades to prose the model executes |
| **SUBAGENT** — spawning an independent agent with a fresh context | an agent/task tool is present **and** the host spawns without asking the user each time | `subagent-delegation.md` → inline passes; `artifact-style-gate.md` → sequential lens passes |
| **MCP** — connector tools in the session | tools matching `mcp__<id>__<tool>` are listed | `integration-strategy.md` Step 2 → Step 3 |
| **HOOKS** — deterministic host-side gates | the SessionStart digest `GROW_PM_SESSION` is present in context | `local-context-protocol.md` Step 0a runs in full; write gate becomes an in-skill confirmation |
| ↳ **the write gate** (since v4.1.0 a separate mark) | HOOKS is present **and** the session's write tools carry the names the PreToolUse matchers of `hooks/hooks.json` list — `mcp__<server>__createJiraIssue`, `…__updateConfluencePage` and the rest in that exact form, `Write` / `Edit` for files | the skill confirms in-skill before the write step (`artifact-style-gate.md` → Host write gate). The digest alone never proves the gate: Codex 0.153.2 runs SessionStart, but names its tools `apply_patch` and `mcp__codex_apps__<app>_<tool>` in lower case, which no matcher catches; on a host where the gate is not measured, treat it as absent — a second confirmation costs one answer, a missing one writes without the user |
| **APP-DRIVE** — a tool that can observe a running product and act on it | browser tools, app-scoped screenshot/click tools, full-screen control tools, or `adb`/`simctl` through SHELL — levels in `app-drive-protocol.md` §1 | `app-drive-protocol.md` §6 → user-driven variant (the user walks and pastes screenshots) |

**Five more say where a result can go (since v4.1.0).** **ARTIFACT** (a page at a link), **DOCS** (a live document the user and the agent edit), **WIDGET** (a visual inside the conversation), **SCHEDULE** (a recurring run the agent can create), **RESEARCH** (a built-in research pass with sources). How to observe each, what goes there, the question before anything is published and what to do without them: `native-surfaces.md` §1–§5. Without them every skill writes a file, as before v4.1.0.

**Do not ask the user which host they are on.** Every row above is observable from the session itself.

## 2. Profiles

Profiles are shorthand for a capability set. They are documentation, not a switch.

| Profile | FS | SHELL | SUBAGENT | MCP | HOOKS | APP-DRIVE | Notes |
|---|---|---|---|---|---|---|---|
| `claude-cowork` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ web / desktop-background / foreground (measured 2026-09-10) | Reference host. Everything in the plugin is defined against it. |
| `codex-cli` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ SessionStart only (measured 0.153.2, 2026-10-29) | ⚠️ assumed | Codex spawns a subagent only on an explicit user request → treat SUBAGENT as absent unless the user asked for it (0.153.2 lists a `spawn_agent` tool; spawning without a request is not measured). Plugin agents (`agents/*.md`) are not loaded. Since 0.153.2 a plugin's hooks run once the user trusts them in Codex (§7): the SessionStart digest arrives. The write gate is not measured — its PreToolUse matchers name Claude's tools, and Codex names them differently (`apply_patch`, `mcp__codex_apps__atlassian_createjiraissue`) — so the write step keeps the in-skill confirmation (§1, §4). The Codex **desktop app** is the same profile, except that it matches `.mcp.json` connectors by name like Claude does (the CLI does not — §7). |
| `chatgpt` | ❌ | ❌ | ❌ | ✅ | ❌ | ⚠️ web only, assumed | ChatGPT on **web / mobile**: skills and connectors only; the storage, vault and script contours are unavailable. The ChatGPT **desktop app with a Local Project** attaches local folders read/write (vendor doc) — observe FS as present and apply the `codex-cli` row. Not yet run with the plugin: derived, not measured. |
| `codex-cloud` | ⚠️ | ✅ | ⚠️ | ? | ❌ | ❌ | Its own sandbox filesystem — **not** the user's `~/.grow-pm/`. Treat FS as present but empty: never assume prior state, always write results back through a connector or the repo. |

The **measured / assumed** marks in this file (and **vendor**, §7) say how a host fact is known. They are not the evidence classes of `pm-mental-model.md` §4 (since v3.8.0) and never label a claim in an artifact.

## 3. Step 0-host — the host check

Any skill that touches storage, subagents or scripts runs this before its first real step. It is three lines of reasoning, not a tool call:

1. Look at the tool list actually available in this session.
2. Mark the six capabilities from §1 as present / absent — and the surface capabilities your output step uses (`native-surfaces.md` §1).
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
| Context store (`ctx`, since v3.11.0) | SHELL: `scripts/ctx.py` — records, sync of direct edits, card, digest line; since v3.12.0 `ctx read` at Step 0c, lifecycle, freshness; since v3.15.0 slots and the cascade in `ctx read`, `ctx explain`, `ctx slot …` | FS without SHELL: edit `local-context.md` as before; Step 0c reads `INDEX.md` and the manifest's records whole; a later `ctx` run on a host with a shell imports the edits; since v3.15.0 the slot catalogue is read and each slot looked for under all its names, with no cascade and no `explain` (`context-protocol.md` §9) | no FS: no store (`storage_mode: session`) |
| Context repositories (`ctx repo`, `ctx provider`, since v3.13.0) | SHELL: `scripts/ctx.py`. The network use of `ctx` is in `repo status` and `provider adopt`, `plan`, `apply` and `sync` (the daily sync of v3.14.0, run from Step 0c of every skill — the hook is not involved): a handshake and one `vault_get_note` of the repository's blocks file over http(s); the core folder is read when the server does not answer — and, since v3.16.0, in `search` (row below). The SessionStart hook never goes to the network | MCP without SHELL: the blocks file can be read with the host's own `vault_get_note`; nothing merges it, the user's edits stay in `local-context.md` | no SHELL and no MCP: the blocks stay as they are (`context-provider-protocol.md` §12.10) |
| The copy of a core (`ctx repo copy`, since v3.24.0) | SHELL: `scripts/ctx.py repo copy <id>` — a pass in the foreground; the daily sync starts the same pass as a background process that outlives it (`context-provider-protocol.md` §12.12) | a host whose process does not outlive the command cuts the background pass (it resumes in an hour); a sandbox with no network → `unreachable` | no SHELL: no copy — the skills read the server in prose, as before |
| The vault — `ctx graph`, `ctx audit`, `ctx vault normalize` (since v4.0.0) | SHELL: `scripts/ctx.py` over the section index and the downloaded notes of your layer; no network | — | no SHELL: none of them — the normaliser has no prose mode (§5) |
| The local MCP — `ctx serve` (since v4.0.0) | a host that starts a local MCP server from its config (Claude Desktop, Cowork, Codex CLI `codex mcp add`): the tools of `vault/v1` over the plugin's index, for a session that has no shell | — | a host that starts no local server: none |
| Search (Step 0.5, since v3.16.0; `search-protocol.md` §12) | SHELL: `ctx search` — the section index in `<home>/.grow-pm/index/` (the plugin folder of every vault, the local core folder of every registration), a registered local index (SQLite, read only) and the server of a repository whose folder is not on disk; its only network use is `vault_search` and `vault_get_note` on such a server, 20 s a source and 60 s in all. The rating is the session model's own, so it needs no SUBAGENT. Without a context store the same search, without the memory of choices. The SessionStart hook reads only the index's `index.json` and never goes to the network | FS without SHELL: the words of the request looked for in the plugin folder and the core folders, file by file, the same rating and block of variants; a choice is not remembered. MCP without FS: `vault_search` of each reachable provider, one call per variant | no FS, no SHELL, no MCP: Step 0.5 is skipped — say so once when the request needed the base |
| Write gate | PreToolUse hook (`ask`) | in-skill confirmation before the write step | — |
| Structured questions (`AskUserQuestion`: onboarding, Step 0i role, template choice) | the host's option picker (2–4 options per question, up to 4 questions per call) | a numbered list in chat; the answer is parsed from the user's reply (a number or the text) | — (no capability mark needed: every host can ask in plain text) |
| Product drive (`flow-walkthrough`) | best level per `app-drive-protocol.md` §1 | a lower level (foreground instead of background; sequential compare) | user-driven variant — the user walks, the agent logs |

## 5. Contours that have no meaningful degraded mode

These need FS. On a host without it, the skill says so in one line and stops instead of pretending:

- `focus-advisor` → Focus Board (`~/.grow-pm/focus/`)
- `experiment-tracker` → `registry.yaml`
- the whole People contour (`one-on-one`, `performance-review`, `delegation-coach`, `offboarding-guide`, `hiring-designer`) → person profiles are strictly local by `people-context-protocol.md`
- `template-library`, `knowledge-library` → local library and glossary
- `ctx entity apply` (`context-navigator`, since v3.20.0) → writes bridges into the user's notes with a snapshot and `ctx undo`; it needs FS and SHELL — never written by hand in its place
- The inbox, `ctx show`, `ctx health`, `ctx snapshot import` (since v3.21.0, `context-protocol.md` §5i–§5j) → need FS and SHELL with a store; without them a skill asks «Знайшов нове: … Зберегти?» as before and edits `local-context.md` on «так» (`local-context-protocol.md` → Context Enrichment), and `/grow-product-manager:context` says in one line that it needs the store
- The configurator's bootstrap, `ctx validate --recheck`, `ctx consolidate` (since v3.22.0, `context-protocol.md` §5k–§5m) → the connectors are read by the skill on any host with MCP; the table, the recheck and the consolidation need FS and SHELL with a store. Without SHELL the configurator reads the same connectors by `context-observe.md`, applies the same rules in prose (what each source may give, the thresholds, low confidence never written without asking) and shows the same table, then writes Step 16c's `local-context.md` on «так» — no store, so no source per field; recheck and consolidate are offered only where `ctx` runs. Without MCP the five questions are typed answers
- The declared overlay, the core's suggestions, `ctx history`, `ctx identity`, `ctx repo kit-check | add` (since v3.23.0, `context-protocol.md` §5n–§5r) → FS and SHELL with a store: the overlay is laid by `ctx` after every apply and sync. Without SHELL a skill reads `{store}/overlays/<repo>.yaml` as text and applies its `ignore` and `replace` in its answer in prose (the core's text for that part is set aside, with the operation's reason); nothing is laid, held or asked, there is no history and no proposal from the core, and a kit is connected by `context-connect`'s flow. Codex CLI: no hooks, the same commands.

- `ctx vault normalize` (since v4.0.0, `context-protocol.md` §5s) → writes many notes of the user's layer, each with a snapshot and `ctx undo`; it needs FS and SHELL with a store in the vault — never done by hand in its place. `ctx audit` and `ctx graph` need SHELL too; a host without one reaches the graph through `ctx serve` when it can start a local MCP server.

Read-only modes of these skills still work when the user pastes the data into the session.

## 6. Path variables

`${PLUGIN_ROOT}` is the portable variable (Agent Plugins 1.0); `${CLAUDE_PLUGIN_ROOT}` is the Claude-specific one. Anything that needs the plugin root resolves in this order:

1. `${PLUGIN_ROOT}`
2. `${CLAUDE_PLUGIN_ROOT}`
3. the directory that contains `skills/`, found by walking up from the current skill's folder

Never hardcode an absolute path, and never assume either variable expanded — a literal `${...}` left in the text means the host did not define it, which is signal, not an error to hide.

## 7. Known host gaps (v3.0.0)

Each item names its source — **measured** (this plugin's pilot, Codex CLI 0.153.2, September 2026; details in `Codex-Compat-Findings.md` in the design workspace) or **vendor** (a Codex/ChatGPT document or issue). A host limitation with neither source does not belong here, in README, or in a release note.

- **Codex refreshes Git marketplaces only when it starts** — on plugin startup and on `codex plugin list` — and then refreshes the installed plugin cache; it does not check periodically while the app stays open. *Vendor:* openai/codex#17425, openai/codex#38401. After a release: restart Codex, or `codex plugin marketplace upgrade <name>` + `codex plugin add …` — `codex plugin marketplace add` on a marketplace that is already configured only reports it and does not refresh it (measured, codex-cli 0.153.2, v3.10.1). Run these commands from a folder without a project-local `.codex/config.toml`: Codex merges one from the current folder, and a repository-root copy that declares a server by `url` where the global config declares it as a command stops every command with "url is not supported for stdio". *(An earlier note here said "no auto-update" — that was an app left open across a merge.)*
- **ChatGPT on web / mobile has no filesystem; the ChatGPT desktop app's Local Projects attach local folders read/write.** *Vendor:* Projects docs. The plugin has not been run on either surface — the `chatgpt` profile is derived.

Measured on Claude Cowork (2026-09-10, this plugin's flow-walkthrough spike):

- **Background window capture fails for iPhone apps running on a Mac** (apps installed from the Mac App Store on Apple Silicon) — they are driven at the `foreground` level only (`app-drive-protocol.md` §2).
- **Transparent overlay windows of utilities block clicks** (a grammar checker's floating window did); quit them for the run.
- **An App Store build can never run in the iOS Simulator** — it is a device binary; a simulator build from the mobile team is needed.

Measured on Claude Code (2.1.292, v3.10.1):

- **Claude Code caps the skill listing at 1% of the context window** (4 characters per token; setting `skillListingBudgetFraction`, env `SLASH_COMMAND_TOOL_CHAR_BUDGET`). Over the cap it keeps the host's bundled skills whole, ranks every other skill by use (a count with a one-week half-life) and gives descriptions in that order while they fit; the rest are listed **by name only**, and the model routes on the name. On a machine with about 150 skills, 16 of the plugin's 33 skills showed names only, and they explained 8 of 10 trigger misses. Hence, since v3.10.1: each description within 400 characters and all of them within 10,000 (validator check 12), the full trigger list in each skill's `## Routing` section, and trigger evals run twice — as the host lists skills, and with every description visible. A user who sees misrouting can raise `skillListingBudgetFraction` in `~/.claude/settings.json` or disable unused plugins with `/skills`.

Measured on Codex CLI:

- **Codex shares one ~15,000-character budget across every listed skill's `description`** (measured: 80 skills → ~190 characters each; this plugin alone → ~530). The warning is literal: *"Skill descriptions were shortened to fit the skills context budget"*. Hence the description order enforced since v3.0.0: essence with the discriminating nouns and the guard against the nearest neighbour inside the first 190 characters, then Ukrainian keywords, then EN triggers, then chains. Migrated commands count against the same budget.
- **Codex does not load `agents/*.md`** from a plugin (v3.0.0 pilot). **Its hooks do run since 0.153.2** (measured 2026-10-29: the SessionStart digest `GROW_PM_SESSION` is in the session's log; until then openai/codex#17331) — **once the user trusts them**: Codex keeps a hash per plugin hook (`[hooks.state."<plugin>@<marketplace>:hooks/hooks.json:<event>:…"] trusted_hash` in `~/.codex/config.toml`), and a freshly installed copy without one did not run its SessionStart in `codex exec`. Whether a changed `hooks.json` has to be trusted again is not measured. The PreToolUse write gate is not measured: its matchers name Claude's tool names, which Codex does not use (`apply_patch` for files; `mcp__codex_apps__<app>_<tool>` in lower case for connectors), so it is treated as absent.
- **Codex skips a command whose body contains `$1` or `$ARGUMENTS`** when migrating `commands/` into skills.
- **A marketplace entry needs a string `source` with a `./` prefix** (`"./"` for a plugin at the repository root, `"./subdir"` otherwise); Codex silently ignores the object form, and Claude Code rejects a bare `"."` (`plugins.0.source: Invalid input`).
- **Codex resolves a bare `references/<file>.md` against the skill's own folder**, not the plugin root — the shared protocols are copied into the plugin cache but are not found from a skill without the resolution rule in `local-context-protocol.md`.
- **Codex CLI does not match a connector by name.** An `.mcp.json` entry with an empty `url` is opened as an HTTP transport and fails at every session start (`relative URL without a base`); in the CLI those connectors exist only through pattern detection (`integration-strategy.md` 1b). The Codex desktop app does match by name and shows them as connected.
