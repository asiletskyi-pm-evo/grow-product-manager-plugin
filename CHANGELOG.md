# Changelog — Grow Product Manager Plugin

All notable changes to this plugin are documented here.

Version format: `MAJOR.MINOR.PATCH`
- **MAJOR** — breaking changes, full workflow restructure across multiple skills
- **MINOR** — new skill added, new step/section in existing skill, significant workflow addition
- **PATCH** — wording fix, small content addition, formatting change, bug fix in skill logic

Each skill also carries its own version in the frontmatter (`version:` field in SKILL.md).
When a skill changes, its version is bumped independently. The plugin version is bumped to reflect the highest-impact change among all updated skills.

---

## v3.2.0 (2026-09-11)

**Test accounts by role and multi-role walkthrough legs.** A product's production test accounts (test buyer, test seller companies, admin) are declared once — labels, roles, surfaces, where access is obtained, sandbox flag; never a secret — and a `flow-walkthrough` scenario can run as several **legs** played by different roles in sequence with hand-off values between them. The write boundary now follows the account instead of being one global rule. MINOR: new step in flow-walkthrough, new configurator add-on.

### Added

- **`#### Test Accounts`** per product in `local-context.md` (`skills/plugin-configurator/references/context-schema.md`), deferred step id `test-accounts`, and the Extended add-on **Test accounts setup** in `onboarding-steps.md` with standalone triggers `add Test accounts` / `додай тестові акаунти`; the add-on refuses to write a pasted password or one-time code.
- **Legs** in `flow-walkthrough` v0.2.0 — Step 1 collects `role`, `account`, `surface`, `goal`, `handoff_in/out` per leg; Step 2 asks the user to log in before each leg; Step 3 confirms every irreversible tap under `sandbox-confirm`, captures hand-off values from screenshots, and starts the next leg only when its inputs exist; Step 6 adds a leg summary table.
- **Write-boundary policy** in `references/app-drive-protocol.md` §3 item 6: `stop-before-irreversible` (own), `sandbox-confirm` / `sandbox-auto` (sandbox test accounts in the user's own product), `read-only` (competitors); two hard stops under every boundary — real money, actions visible to real users. §7 pack layout: `legs[]` in `run.yaml`, `leg`/`role` on every step, `steps/L<leg>-<NN>.png`, `blocked_reason: user declined`.
- `templates/built-in/research/walkthrough-v1.md` 1.1.0 — leg summary table and a `Leg / Role` column.
- `skills/flow-walkthrough/examples/marketplace-order-to-review-flow.md` — the three-leg reference (test buyer orders → test seller confirms and ships → buyer reviews; four confirmations; real-payment-only checkout ends leg 1 with `blocked_reason: real money`).
- Lint vocabulary: `test-accounts` and the four boundary values; trigger-evals Group N; test-cases for the 3-leg scenario, the configurator add-on and the single-leg regression.

### Changed

- `flow-walkthrough` 0.1.0 → 0.2.0, `plugin-configurator` 2.9.3 → 2.9.4; `local-context.example.md` shows the Test Accounts table with placeholder labels.

### Not in this version (next)

Parallel legs on two devices at once (legs are sequential; two surfaces may stay open), automatic account switching, storing any secret (never).

### Backwards compatibility

Full. A single-leg run is byte-for-byte the v3.1.0 behaviour (`leg: 1`, `stop-before-irreversible` on an own account); products without a Test Accounts table simply have no sandbox option.

---

## v3.1.0 (2026-09-10)

**Walk the flow in the real product.** New skill `flow-walkthrough` drives the product the way a customer does — a web app in a browser, a desktop app, an iPhone app installed from the Mac App Store on Apple Silicon, an Android phone or emulator over adb — one step at a time with a screenshot per step, friction graded per step, a local evidence pack (`~/.grow-pm/walkthroughs/`) and a `research/walkthrough` report. Four modes: `setup` (agent-guided readiness + install, user-only actions marked, smoke test), `walk`, `compare` (one scenario across surfaces or against competitors — read-only there), `audit`. MINOR: new skill, new shared protocol, new observed capability. Built on a measured spike (2026-09-10, Claude Cowork): a marketplace buyer app from the Mac App Store was walked end-to-end up to the publish step.

### Added

- **`references/app-drive-protocol.md`** — capability **APP-DRIVE** (levels `web` / `desktop-background` / `foreground` / `device` / `none`, measured vs assumed per host), driver table, preflight, step cycle (act → wait → screenshot → verify → log), safety (credentials user-only, write boundary, competitors read-only, screenshots local), degradation (user-driven variant), evidence-pack layout (`run.yaml`, `steps.yaml`, `steps/NN.png`, `findings.md`, `compare.yaml`).
- **`skills/flow-walkthrough`** v0.1.0 with the reference example `examples/marketplace-review-flow.md` (12 expected steps, 6 expected frictions, driver facts).
- **`scripts/walkthrough_preflight.sh`** — per-surface readiness table `SURFACE | STATUS | MISSING | WHO`, fail-open.
- **`templates/built-in/research/walkthrough-v1.md`** (25 seed templates); vault type `walkthrough` → `Research/walkthroughs/` (35 types); storage folder `~/.grow-pm/walkthroughs/`.
- `host-profiles.md`: sixth capability in §1 and the profile table, "Product drive" row in §4, three measured facts in §7 (background capture fails for iPhone apps on a Mac; overlay utilities block clicks; App Store builds never run in the Simulator). `integration-strategy.md` Step 3 points to the protocol. `template-protocol.md` shows the `research/walkthrough` built-in on the ladder.
- Lint: `walkthrough-local`, `iphone-on-mac`, `android-adb`, `ios-simulator`, `desktop-background` join the non-skill vocabulary. Trigger-evals Group M; test-cases for the new skill.

### Changed

- `cjm-research` v0.7.5 — Step 3 "Walk the stage" via `flow-walkthrough`; source marker `walkthrough-local` in Step 3.5.e; chaining offer. `references/cjm-protocol.md` documents the marker as qualitative stage evidence.
- `product-research` v0.10.5 — hands-on UX benchmark through `flow-walkthrough` compare mode (competitors read-only); post-research offer.
- `requirements-creator` v0.13.3, `task-creator` v0.12.3, `write-concept` v0.11.3 — a walkthrough pack's `steps/NN.png` is screenshot source 0 (`visual-annotation-protocol.md` V-1); requirements-creator offers a short walk when no source exists.
- `diagram-prototyper` v0.10.2 — `steps.yaml` is a valid flowchart input (node per step intent, friction as a red note, blocked step as a terminal node).
- `vault-protocol.md` skill→types table gains `flow-walkthrough`; `requirements-creator` may read `walkthrough`.

### Not in this version (next)

iOS Simulator builds from the mobile team, iPhone Mirroring, installing an Android emulator with system images, video recording, automated accessibility audit; Codex and ChatGPT drive levels stay `assumed` until measured.

### Backwards compatibility

Full. No existing skill changes behaviour unless a walkthrough pack exists or the user asks for a walk; the write boundary defaults to "stop before any irreversible action".

---

## v3.0.1 (2026-09-09)

**Plugin logo and the Codex card.** The plugin now has its own mark — a white "G" with a compass arrow on the Prom violet — and a `.codex-plugin/plugin.json` that Codex and ChatGPT render as the plugin card. Packaging only: no skill, protocol or command changed.

### Added

- **`assets/logo.png`** (512×512) and **`assets/composer-icon.png`** (128×128) — the chosen "G-compass" mark; the card rounds the tile itself, as with the bundled OpenAI plugins.
- **`.codex-plugin/plugin.json`** — mirrors `.claude-plugin/plugin.json` (name, version, description, author) and adds `skills: "./skills/"` plus the `interface` block: `displayName`, `shortDescription`, `longDescription`, `developerName`, `category: Productivity`, `websiteURL`, `brandColor: #7B04DF`, `logo`, `composerIcon`. Verified on a fixture and on the pilot stand that the manifest keeps the 29 skills loading and the 5 commands migrating (34 entries, no duplicates).
- README shows the logo and documents the card.

### Changed

- **`testing/validate-consistency.sh`** — check 1 keeps the two manifests' version and description identical and requires the logo files; check 10 counts components in the Codex manifest as well.
- **`release-manager`** Step 3 — six mandatory bump places (the Codex manifest is 2a). `AGENTS.md` names the five version-bearing files.

### Backwards compatibility

Full. Claude Code has no logo field and ignores `.codex-plugin/` and `assets/` (headless load test on the branch: skills, commands and the SessionStart hook unchanged; `claude plugin validate` passes). On Codex the logo appears after the two-step manual update (`codex plugin marketplace upgrade …`, then `codex plugin add …`) because the plugin cache is keyed by version — the reason this is a release and not a silent change on `main`.

---

## v3.0.0 (2026-09-08)

**One plugin, three hosts — Claude Code / Cowork, Codex CLI and app, ChatGPT.** Codex reads the same `.claude-plugin/` manifests, loads all 29 skills under the same `grow-product-manager:` namespace and registers the same connectors, so nothing was forked. What changed is how the skills behave where a host lacks something: every skill now branches on **observed capabilities**, never on a host name. MAJOR because the marketplace `source` format changes, every `SKILL.md` and every command description changes, and the plugin now promises a defined behaviour on hosts it previously ignored. Measured on Codex CLI 0.153.2 and Claude Code 2.1.126 throughout (`Codex-Compat-Findings.md`, stages 0–5, in the design workspace).

### Added

- **`references/host-profiles.md`** — the cross-host contract: five observable capabilities (FS, SHELL, SUBAGENT, MCP, HOOKS), four profiles (`claude-cowork`, `codex-cli` incl. the Codex app, `chatgpt`, `codex-cloud`), **Step 0-host** run once per skill, the degradation matrix per contour, the contours with no meaningful degraded mode, `${PLUGIN_ROOT}` → `${CLAUDE_PLUGIN_ROOT}` → walk-up resolution, and the measured host gaps.
- **Path rule** paragraph at the top of every `SKILL.md` and of every command that names a reference — Codex resolves a bare `references/<file>.md` against the skill's own folder and does not walk up (3 of 4 shared protocols were unreachable from `write-concept`); the rule sends the read to the plugin root. Verified 7/7 in Codex, incl. a natural activation.
- **`AGENTS.md`** (5 KB) — standing brief for hosts that read it: where things live, Step 0-host, the data-policy requirement, the measured Codex gaps.
- **`.codex/agents/*.toml`** — manual Codex ports of `artifact-checker`, `debater`, `extractor` (Codex does not load `agents/*.md` and spawns a subagent only on request), generated from the markdown sources, with a README on their weaker independence.
- **`testing/host-matrix.md`** — 29 skills × 4 hosts × full / degraded / n-a, derived from what each skill invokes: codex-cli 15 full / 14 degraded, chatgpt 19 degraded / 10 n/a, codex-cloud 20 degraded / 9 n/a.
- **Validator checks 12–14** — description routing order (guard inside the first 192 characters, neighbour is a real skill, Ukrainian keywords present); commands typed-only (no `$1` / `$ARGUMENTS`, description opens with `Typed command … only`); host packaging (Path rule everywhere, a Codex port per agent, every skill in the host matrix). Each negative-tested on the defect it targets. `testing/Testing-process.md` documents them.
- **README → Hosts** — capability table per host, per-skill result, Codex install and the two-command manual update.

### Changed

- **All 29 skill descriptions** rewritten under a priority-order rule, because Codex shares one ≈15,000-character budget across every listed skill (~530 characters each with this plugin alone, ~190 on a host listing 80 skills): essence with the discriminating nouns + the guard against the nearest neighbour inside the first 190 characters, then Ukrainian keywords, then EN triggers, then chains. No `: ` in any description (strict YAML). **Trigger-evals, 102 phrases:** Codex CLI on the author's real configuration 91.2 % → **100 % in two consecutive runs**, identical answers; Claude Code headless **101/102** where the one miss (`/grow-product-manager:status` → `none`) is the correct Claude answer for a host-executed command.
- **All 5 command descriptions** open with `Typed command /grow-product-manager:<name> only — never for a conversational «…» (that is <skill>)` — Codex migrates commands into routable skills without `disable-model-invocation`, and they captured conversational status/config/terminology/write-gate phrases (Group L 4/9 before, 9/9 after). Command bodies describe their argument in prose instead of `$1` / `$ARGUMENTS` (Codex skipped 4 of 5); `setup.md` no longer pre-executes its script.
- **`.claude-plugin/marketplace.json`** — `"source": "./"` instead of the `git-subdir` object. Codex silently ignores the object form (marketplace added, zero plugins); Claude Code rejects a bare `"."` (`plugins.0.source: Invalid input`) and accepts `"./"`. Relative sources resolve against the local marketplace copy, so `owner/repo` installs keep working; only a marketplace added by direct URL to `marketplace.json` would not.
- **`references/persistent-storage.md`** — step 0 of `storage_root` resolution: `storage_mode: local | connector | session` from Step 0-host (`local` = current behaviour; `connector` = a Drive folder or Confluence space from `storage.connector_root`; `session` = artifact stays in the chat and is exported at the end). Named `storage_mode`, not a letter — L0/L1/L2 already mean vault levels.
- **`references/subagent-delegation.md`** — the one-line fallback is a three-level chain: parallel `extractor` subagents → sequential inline passes with a role reset (the Codex default) → a single pass over fewer sources, stated. Level fixed once at Step 0-host.
- **`references/artifact-style-gate.md`** — on a host without SUBAGENT the checker lands on level 2 (sequential in-session lens passes, `checker: sequential in-session`), the reduced-independence marker stays reserved for level 3; on a host without HOOKS the skill asks for the write confirmation itself with the same three-point checklist.
- **`references/integration-strategy.md`** — host-capabilities preamble; §1a namespaces are host-dependent (1b pattern detection is the source of truth) with a Codex column: name-matched empty-`url` connectors work in the Codex **app** but fail at session start in the **CLI** (`relative URL without a base`) — kept on purpose as Claude's convention, documented in `.mcp.json` and `AGENTS.md`.
- **`references/local-context-protocol.md`** — where a bare `references/…` lives (skill-local if the file exists there, otherwise the shared folder at the plugin root, resolution per host-profiles §6).
- **Portable `${PLUGIN_ROOT}`** ahead of `${CLAUDE_PLUGIN_ROOT}` in `agents/*.md`, `commands/status.md`, the validator; `hooks/hooks.json` keeps the Claude variable (hooks load only there).
- **`testing/trigger-evals.md`** — Codex run protocol (single-line prompts — a multi-line prompt argument hangs `codex exec` 0.153 before the session starts; score on the host's real configuration) and the two-host results rows.

### Known host gaps (documented, not hidden)

Codex does not load `agents/*.md` or `hooks/hooks.json` (openai/codex#17331); Codex CLI fails empty-`url` connectors at session start (the app matches them by name); Codex refreshes Git marketplaces only at startup (openai/codex#17425, #38401) — restart Codex after a release, or `codex plugin marketplace upgrade <name>` then `codex plugin add …`; ChatGPT on web / mobile has no filesystem, shell or subagents — the storage-bound contours say so and stop (the desktop app with a *Local Project* has a filesystem and behaves like Codex). *Corrected 2026-09-09: the original entry said "no auto-update" and "no filesystem" without qualification — both were assumptions, not measurements.*

### Files

| File | Version | Change |
|------|---------|--------|
| `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` | 2.6.0 → 3.0.0 | version, description tails, string `source` |
| `skills/brainstorm-features/SKILL.md` | 0.10.1 → 0.10.2 | Path rule paragraph; description rewritten under the routing-order rule |
| `skills/cjm-research/SKILL.md` | 0.7.3 → 0.7.4 | Path rule paragraph; description rewritten under the routing-order rule |
| `skills/decision-log/SKILL.md` | 0.2.4 → 0.2.5 | Path rule paragraph; description rewritten under the routing-order rule |
| `skills/delegation-coach/SKILL.md` | 0.1.2 → 0.1.3 | Path rule paragraph; description rewritten under the routing-order rule |
| `skills/design-bridge/SKILL.md` | 0.4.1 → 0.4.2 | Path rule paragraph; description rewritten under the routing-order rule |
| `skills/diagram-prototyper/SKILL.md` | 0.10.0 → 0.10.1 | Path rule paragraph; description rewritten under the routing-order rule |
| `skills/experiment-tracker/SKILL.md` | 0.2.3 → 0.2.4 | Path rule paragraph; description rewritten under the routing-order rule |
| `skills/feedback-triage/SKILL.md` | 0.2.2 → 0.2.3 | Path rule paragraph; description rewritten under the routing-order rule |
| `skills/focus-advisor/SKILL.md` | 0.5.0 → 0.5.1 | Path rule paragraph; description rewritten under the routing-order rule |
| `skills/goal-setter/SKILL.md` | 0.1.2 → 0.1.3 | Path rule paragraph; description rewritten under the routing-order rule |
| `skills/hiring-designer/SKILL.md` | 0.1.1 → 0.1.2 | Path rule paragraph; description rewritten under the routing-order rule |
| `skills/knowledge-library/SKILL.md` | 0.7.1 → 0.7.2 | Path rule paragraph; description rewritten under the routing-order rule |
| `skills/meeting-processor/SKILL.md` | 0.13.4 → 0.13.5 | Path rule paragraph; description rewritten under the routing-order rule |
| `skills/offboarding-guide/SKILL.md` | 0.1.1 → 0.1.2 | Path rule paragraph; description rewritten under the routing-order rule |
| `skills/one-on-one/SKILL.md` | 0.1.2 → 0.1.3 | Path rule paragraph; description rewritten under the routing-order rule |
| `skills/performance-review/SKILL.md` | 0.1.1 → 0.1.2 | Path rule paragraph; description rewritten under the routing-order rule |
| `skills/plugin-configurator/SKILL.md` | 2.9.2 → 2.9.3 | Path rule paragraph; description rewritten under the routing-order rule |
| `skills/product-analysis/SKILL.md` | 0.12.2 → 0.12.3 | Path rule paragraph; description rewritten under the routing-order rule |
| `skills/product-reporter/SKILL.md` | 0.5.2 → 0.5.3 | Path rule paragraph; description rewritten under the routing-order rule |
| `skills/product-research/SKILL.md` | 0.10.3 → 0.10.4 | Path rule paragraph; description rewritten under the routing-order rule |
| `skills/project-planning/SKILL.md` | 0.2.3 → 0.2.4 | Path rule paragraph; description rewritten under the routing-order rule |
| `skills/quarterly-planning/SKILL.md` | 0.3.3 → 0.3.4 | Path rule paragraph; description rewritten under the routing-order rule |
| `skills/release-manager/SKILL.md` | 0.2.0 → 0.2.1 | Path rule paragraph; description rewritten under the routing-order rule |
| `skills/requirements-creator/SKILL.md` | 0.13.1 → 0.13.2 | Path rule paragraph; description rewritten under the routing-order rule |
| `skills/roadmap-architect/SKILL.md` | 0.2.3 → 0.2.4 | Path rule paragraph; description rewritten under the routing-order rule |
| `skills/sprint-planning/SKILL.md` | 0.3.2 → 0.3.3 | Path rule paragraph; description rewritten under the routing-order rule |
| `skills/task-creator/SKILL.md` | 0.12.1 → 0.12.2 | Path rule paragraph; description rewritten under the routing-order rule |
| `skills/template-library/SKILL.md` | 0.2.3 → 0.2.4 | Path rule paragraph; description rewritten under the routing-order rule |
| `skills/write-concept/SKILL.md` | 0.11.1 → 0.11.2 | Path rule paragraph; description rewritten under the routing-order rule |
| `commands/*.md` (5) | — | typed-only guard, prose arguments, Path rule |
| `agents/*.md` (3) | — | `${PLUGIN_ROOT}` first |
| `references/host-profiles.md`, `AGENTS.md`, `.codex/agents/*` , `testing/host-matrix.md` | new | see Added |
| `references/persistent-storage.md`, `subagent-delegation.md`, `artifact-style-gate.md`, `integration-strategy.md`, `local-context-protocol.md` | — | see Changed |
| `testing/validate-consistency.sh` (checks 12–14), `testing/skill_lint.py` (unchanged), `testing/trigger-evals.md`, `testing/Testing-process.md` | — | see Added / Changed |

### Backwards compatibility

Claude Code / Cowork behaviour is unchanged: every degraded mode is gated on an absent capability that Claude has, the Path rule is a no-op where `references/` already resolves from the plugin root, and commands keep `disable-model-invocation: true`. Existing installs from `owner/repo` keep working with the string `source`. Skill folder names, chain contracts, vault types and `local-context.md` keys are unchanged; `storage.connector_root` is a new optional key read only in `storage_mode: connector`.

---

## v2.6.0 (2026-09-04)

**Host hooks: the session knows where its context is, and a human confirms before a write.** v2.5.0 moved connectors, agents and commands into the manifest. This release adds the fourth component, hooks — two of them, chosen by a rule: a hook must be *deterministic*, *fail-open*, and do something a skill cannot do reliably from prose. A hook runs in the session's own environment (a local VM or a hosted container) and sees only its event's JSON, never the conversation — both hooks are designed around that.

### Added — `hooks/hooks.json` (2) + `scripts/`

- **SessionStart → context digest** (`scripts/session-start.sh` → `session_start.py`; matcher `startup|resume|clear|compact`, timeout 10 s). Searches for `local-context.md` in the order a session can actually see it: `~/.grow-pm/` → connected folders `$HOME/mnt/*/`, `$HOME/mnt/*/.grow-pm/`, `$HOME/mnt/*/grow-pm/` → staged uploads → the working directory. Found → injects a `GROW_PM_SESSION` digest (path, configurator version, onboarding mode, `user.language`, product and team names, vault / CJM / team-language flags, deferred onboarding steps; header facts only — never URLs, ids or emails) and appends `export GROW_PM_CONTEXT_PATH=…` to `$CLAUDE_ENV_FILE` for later Bash calls. Not found → a three-line `NOT VISIBLE` note that tells skills to run Step 0 unchanged and **not** to start onboarding on that signal. Re-runs after `/clear` and after compaction, so the location survives long sessions. Without python3 the wrapper emits a static note; any error → exit 0, no output.
- **PreToolUse → write gate** (`scripts/write-gate.sh` → `write_gate.py`; matcher `mcp__.*__(createJiraIssue|editJiraIssue|createConfluencePage|updateConfluencePage)$`, timeout 10 s). Returns `permissionDecision: "ask"` for every create and for content-bearing updates (a description/body ≥ 200 chars); the reason the host shows is the checklist the artifact quality gate expects to be done by then — gate report in chat, the user's explicit go-ahead, not a sandbox. Metadata-only edits (status, labels, title) pass silently. Opt-out via `{"write_gate": "off"}` in the plugin data dir. Any error → allow.
- **`/grow-product-manager:setup [--show | --write-gate on|off]`** (`commands/setup.md` → `scripts/setup.py`) — the toggle above, plus a report of the hooks environment (`CLAUDE_PLUGIN_DATA`, `CLAUDE_ENV_FILE`, `GROW_PM_CONTEXT_PATH`). Never touches `local-context.md`.

### Changed — protocols and validation

- **`references/local-context-protocol.md`** Step 0a — the digest is a shortcut: take the path from `GROW_PM_SESSION` / `GROW_PM_CONTEXT_PATH` and skip the location search; still parse the file for 0c–0h. `NOT VISIBLE` means "the hook could not see it", not "not configured". No skill file changed.
- **`references/artifact-style-gate.md`** — new section *Host write gate*: skills must present the gate report and get the go-ahead **before** the write step, because the host prompt will ask for exactly that.
- **`references/harness-map.md`** — hooks and agents named in the Guardrails layer.
- **`testing/validate-consistency.sh`** — check 11: `hooks.json` valid, events from the official list, every hook has a `timeout`, every command points at an existing **executable** script, `scripts/*.py` compile; check 10 counts hooks. **`testing/skill_lint.py`** scans `scripts/`. Trigger-evals L9; `testing/test-cases.md` v2.6.0 block with fixture results (8/8 pass) and the host stage split by environment (local / hosted / CLI / after compaction).

| File | From | To | Change |
|------|------|----|--------|
| `hooks/hooks.json` | — | new | SessionStart + PreToolUse |
| `scripts/session-start.sh`, `session_start.py` | — | new | context digest |
| `scripts/write-gate.sh`, `write_gate.py` | — | new | write gate (`ask`) |
| `scripts/setup.py`, `commands/setup.md` | — | new | toggles + env report |
| `references/local-context-protocol.md`, `artifact-style-gate.md`, `harness-map.md` | — | — | digest shortcut, host write gate, harness layer |
| `testing/validate-consistency.sh`, `skill_lint.py`, `trigger-evals.md`, `test-cases.md` | — | — | check 11, scope, L9, v2.6.0 cases |
| `.claude-plugin/plugin.json`, `marketplace.json`, `README.md` | 2.5.0 | 2.6.0 | version, counts, hooks section |

### Backwards compatibility

Fully backwards compatible. No skill file changed. Hosts without hook support ignore `hooks/`; skills behave exactly as in v2.5.0. The write gate adds one confirmation prompt per artifact write — the only visible change — and can be turned off per install.

---

## v2.5.0 (2026-09-04)

**Plugin components: what the host can enforce, the host now enforces.** Until this release everything the plugin needed from its host lived in prose — "look at the tools in the session for something matching `mcp__*__*Jira*`", "spawn a subagent that must not browse the web", "the checker must not see the maker's context". The model followed those instructions most of the time. This release moves three of the contracts into files the host parses — `.mcp.json`, `agents/`, `commands/` — so a connector shows its real state in the plugin card, a checker physically cannot browse, and a service command is never reached by accident. Hooks (a SessionStart context digest, a pre-write gate on Jira/Confluence tools) are designed and deferred to the next release pending environment tests — see `testing/test-cases.md` → v2.5.0 Stage 3.

### Added — connectors (`.mcp.json`, 6)

- **`.mcp.json`** declares the six connectors the skills rely on: `atlassian` and `figma` by URL (matched to the user's existing connection — no second entry is created), `gmail`, `google calendar`, `google drive`, `fireflies` by name (first-party connectors with a dynamic endpoint). They appear in the plugin's **Connectors** tab with a connected / not-connected state. **Tableau is deliberately not declared** — it is a local MCP server the user runs, and declaring a bundled one would duplicate it.
- **`references/integration-strategy.md`** — Step 1 splits into **1a Declared connectors** (a table: `.mcp.json` key → connector name → tool namespace observed in real sessions → ping call) and **1b Pattern detection** (the old wildcard table, kept for undeclared products). A declared-but-unconnected connector is reported as "enable it in the Connectors tab", never searched for in the registry. The stale `gcal_*` / `gmail_*` patterns — which matched no real tool — are replaced with the actual names. New provenance rule: name the answering server, not the product.
- **`skills/plugin-configurator/references/onboarding-steps.md`** Step 3a — reads declared connectors first, pings by pattern only for Tableau / Notion / Slack / Obsidian.

### Added — agents (`agents/`, 3)

Three named subagents. Each is the executable form of a protocol that already existed; what is new is the `tools:` line, which the host enforces.

- **`artifact-checker`** (`tools: Read`; no Write/Edit/Bash/web/Agent) — the checker half of maker–checker in `references/artifact-style-gate.md`. Receives the draft + source list + `lens` (form | groundedness) + optional Gate-3 lint findings; reads the gate reference itself (checklists are never copied into the call); returns per-section findings in a fixed schema; an empty report without per-section commentary is invalid.
- **`debater`** (`tools: []`) — one role in Debate Mode (`references/debate-protocol.md`). "No web, no vault, no files" was the protocol's core guardrail on the honor system; now it is a host rule. Fixed Round-1 / Round-2+ response structures; every argument cites `E#`/`A#`.
- **`extractor`** (`tools: Read, Glob, Grep`) — the fan-out worker in `references/subagent-delegation.md`: `batch` + `schema` + optional `filters` / `read_via` in, structured rows with source markers out; `nothing_found: true` instead of silence; `unreadable` instead of improvising when a named tool is missing.
- Each protocol gains an explicit **fallback chain**: named agent → `general-purpose` with the same prompt (the report says "checker: general-purpose" / "debater: general-purpose" so the user knows the restriction was not enforced) → inline with the existing reduced-independence marker. Nothing breaks in a host without plugin agents.

### Added — commands (`commands/`, 4; all user-only)

Every command carries `disable-model-invocation: true` — the model never routes a conversation into one, which also keeps them out of trigger collisions (new trigger-evals **Group L**, eight negative rows).

- **`/grow-product-manager:status [--verbose]`** — one-screen health: plugin version, where `local-context.md` was found (including connected folders in hosted sessions) and its schema version, vault level, declared connectors vs tools present in this session, deferred onboarding steps; one suggested next action. Read-only, never launches the configurator.
- **`/grow-product-manager:config validate|view`** — straight into `plugin-configurator`'s Validate / View mode; never starts Onboarding.
- **`/grow-product-manager:release patch|minor|major`** — `release-manager` with Step 2's classification pre-answered; for the plugin repo only.
- **`/grow-product-manager:glossary-lint [file]`** — Gate 3 team-language lint over a file or pasted text, standalone; findings only, nothing written.

### Changed — validation follows the new surface

- **`testing/validate-consistency.sh`** — four new checks: **7** agents frontmatter (name == file, description, `tools`/`disallowedTools`, `model` ∈ enum), **8** commands frontmatter (description, argument-hint, `disable-model-invocation: true`), **9** `.mcp.json` keys == the *Declared connectors* table (both directions; valid JSON), **10** the phrase `N skills, N agents, N commands, N connectors` in plugin.json, marketplace.json and README equals what is on disk.
- **`testing/skill_lint.py`** — `agents/*.md` and `commands/*.md` join the org-data, org-signature, example-locale and stale-name scans (`component_files`). **`testing/seeded_leak_test.py`** — two new seeds prove it (an Atlassian host inside an agent prompt; an authority citation inside a command): 12/12.
- **`skills/release-manager` → v0.2.0** — Step 3 has a fifth mandatory place (component counts); adding an agent / command / connector is a MINOR bump; the `/release` command is documented.
- **`skills/requirements-creator` → v0.13.1**, **`skills/write-concept` → v0.11.1**, **`skills/task-creator` → v0.12.1** — the gate step names `grow-product-manager:artifact-checker` (one call per lens) instead of "an independent checker subagent". **`skills/brainstorm-features` → v0.10.1** — Step 3D names `grow-product-manager:debater`. **`skills/plugin-configurator` → v2.9.2** — onboarding Step 3a.
- **README** — new section *Plugin Components*; **`testing/test-cases.md`** — v2.5.0 block with the host-behavior stage (tabs, no duplicate connectors, namespace, `tools: []` enforcement, hidden commands).

| File | From | To | Change |
|------|------|----|--------|
| `.mcp.json` | — | new | 6 declared connectors |
| `agents/artifact-checker.md`, `agents/debater.md`, `agents/extractor.md` | — | new | tool-restricted subagents |
| `commands/status.md`, `config.md`, `release.md`, `glossary-lint.md` | — | new | user-only service commands |
| `references/integration-strategy.md` | — | — | Step 1a/1b, provenance rule, fixed patterns |
| `references/artifact-style-gate.md`, `debate-protocol.md`, `subagent-delegation.md` | — | — | named agents + fallback chains |
| `skills/requirements-creator/SKILL.md` | 0.13.0 | 0.13.1 | Step 4.5 names the agent |
| `skills/write-concept/SKILL.md` | 0.11.0 | 0.11.1 | Step 4.5 names the agent |
| `skills/task-creator/SKILL.md` | 0.12.0 | 0.12.1 | batch gate + Step 12 name the agent |
| `skills/brainstorm-features/SKILL.md` | 0.10.0 | 0.10.1 | Step 3D names the agent |
| `skills/plugin-configurator/SKILL.md` (+ `references/onboarding-steps.md`) | 2.9.1 | 2.9.2 | Step 3a declared-first |
| `skills/release-manager/SKILL.md` | 0.1.3 | 0.2.0 | fifth mandatory place, `/release` |
| `testing/validate-consistency.sh`, `skill_lint.py`, `seeded_leak_test.py`, `trigger-evals.md`, `test-cases.md` | — | — | checks 7–10, component scope, seeds, Group L, v2.5.0 cases |
| `.claude-plugin/plugin.json`, `marketplace.json`, `README.md` | 2.4.1 | 2.5.0 | version, counts, Plugin Components section |

### Backwards compatibility

Fully backwards compatible. Skills that never used the gate, Debate Mode or fan-out are untouched; the three protocols keep their inline behavior as the last fallback; `.mcp.json` only *declares* connectors the skills already looked for by pattern. The one visible change for an existing install is the plugin card gaining Connectors / Agents / Commands tabs. No `local-context.md` schema change.

---

## v2.4.1 (2026-07-31)

**The plugin's own promise, enforced.** Both manifests state that the plugin "ships no hardcoded brand or organization data". An audit of the tree found nine lines where that was not true — not hosts or ids (those were already checked) but ordinary words: the maintainer's team cited as the authority behind a rule, examples signed with a team and a quarter, a schema example written in one team's language, and an output language hardcoded where `user.language` exists. Every check in the linter passed green over them, because a leak that is an ordinary word has no lexical signature — only a position. This release fixes the lines and adds the checks that make the class visible.

### Fixed — examples and rules are now universal

- **`references/dependency-model.md`** — the Jira link convention was attributed to one team. It now reads from `local-context.md` (`planning.link_convention`), with the previous behavior as the documented default when unset.
- **`skills/product-reporter` → v0.5.2** — report formatting was attributed to one team (now: the team's report conventions from `local-context.md`), and the output language was hardcoded (now: `user.language`).
- **`references/capacity-model.md`, `references/roadmap-artifacts.md`** — two reference examples were signed with a team and a quarter; now anonymized. A signed example reads as the plugin's rule inside that team and as an unverifiable claim outside it.
- **`skills/knowledge-library` → v0.7.1** — the glossary schema example shipped its sample terms, synonyms, `avoid` list and definitions in one team's language, so every other user read a format spec they could not use as a model. Now English throughout, with the style-profile schema's language-specific notes generalized.
- **`skills/plugin-configurator` → v2.9.1**, **`references/focus-signals.md`** — localized sample values inside config code blocks.
- **`references/visual-annotation-protocol.md`** — the legend example described one marketplace's product page; now generic UI.
- **`references/data-integrity-protocol.md`** — Gate Check 2 shipped one country's benchmark roster under the heading "Geography fit for <Country> market", so every user of the plugin screened external data against one market's competitors. It is now a **tier table** (domestic / regional comparable / global platform / mature Western / heavily local elsewhere) resolved from `product.primary_market` and `product.competitors`, with the out-of-tier caveat travelling into the artifact. The seasonal-window table is relabelled as the worked example it is, with the generic instruction above it.
- **`skills/plugin-configurator/references/context-schema.md`, `local-context.example.md`** — both geography gates referenced `product.primary_market`, a key that existed in no schema. It is now a documented optional field; unset, the gates ask once instead of assuming.
- **`testing/trigger-evals.md`** — fixture phrase E1 named a specific local competitor; now "головний конкурент". Same routing signal, no tie to one market.

### Fixed — the denylist layer is usable

- **Word-boundary matching in `org-tokens.local`.** Tokens were matched as bare substrings, so a three-letter team acronym fired on "offset", "fetch" and "feature": a first run against a real token list produced 46 hits, 42 of them noise. Boundaries are now added where the token's own edge is a word character, which leaves host-style tokens (`example.com`) matching mid-string. The same run after the fix: 4 hits, 2 of them real (both fixed above) and 2 correct-by-design (the author line and the marketplace install path name the repository owner).

### Added — three checks that catch the class, and a test that proves they do

- **`org-signature`** — a team/org name cited as the authority behind a rule (`per <Team> convention`, `(<Team> formatting rules)`), or an example signed with a team and a quarter. Positional, not lexical: in a shipped file the authority behind a convention is the plugin, a config key, or a named vendor — never a proper noun the reader cannot look up.
- **`example-locale`** — a localized sample value inside a fenced block (scope is deliberately code blocks only: bilingual trigger phrases in prose are the plugin's routing surface by design), and any output language hardcoded where `user.language` exists.
- **`example-keys`** — an example issue or Confluence space key outside the placeholder vocabulary (`PROJ-1234`, `SPACE`). A real key is both an org leak and an example the reader cannot run.
- **`testing/seeded_leak_test.py` (stage 1b)** — the checks above are the only ones whose failure mode is silence, so they get a test of their own: the tree is copied, one known-bad line is injected at a time, and the linter must go RED with the expected tag. Ten seeds, one per shipped defect class, written with a fictional org so no real identifier enters the repo. **10/10 caught.** Wired into both CI workflows; the gate-parity check now covers it too.
- **`testing/org-tokens.local.example`** — the optional denylist layer never protected anything because nobody noticed the file was absent (two release cycles, two audits). Its absence is now a WARN on every run, and the example file makes creating it a copy.

### Changed — the rule is written down

- **`testing/Testing-process.md`** — a new section, "Every example in the plugin is universal": placeholders instead of real values, a nameable authority behind every rule, no team signature on examples, language-neutral code blocks, no hardcoded output language, generic domain detail. Two rules added to the Definition of Done, and one honest limit stated: the checks catch shapes, not judgment — whether a plausible-sounding example is domain-specific stays a review question and belongs in the checker's brief.

## v2.4.0 (2026-07-29)

**Visual requirements and team language — stage 2 of the stakeholder-feedback release.** v2.3.0 cleaned artifacts of ungrounded technical content and prose; v2.4.0 closes the remaining two feedback items: requirements lacked "a screenshot with an arrow" showing where changes land, and AI text used terms and tone foreign to the team.

### Added — annotated screenshots (visual index of requirements)

- **New shared `references/visual-annotation-protocol.md`** — the core idea: marker № on the screenshot = requirement № in the table; the screenshot is a visual index, not an illustration, and always ships with a legend table. Source priority: user upload → Figma `get_screenshot` → live product via browser. Rendering: Python + Pillow, fully local (product screenshots never leave the session): numbered marker circles, arrows, no-fill boxes, defined style spec. Mandatory user preview cycle before attaching. Local storage in the **project repository** (`{feature-code}-screen-{N}.png`). Attachment chain — verified 2026-07-29 that the Atlassian (Rovo) MCP has NO attachment-upload tools — so: **Atlassian REST API via curl** (Confluence `child/attachment`, Jira `attachments`; token via env variable whose NAME lives in local-context — the value never does) → browser upload → manual placeholder.
- **`diagram-prototyper` → v0.10.0** — standalone **Annotate mode** ("анотуй скріншот", "додай стрілки на скрін", "annotate this screenshot") + description triggers.

### Added — team glossary + style profile (knowledge-library)

- **`knowledge-library` → v0.7.0** — the team-language contour, in the existing service-skill pattern: **Glossary Build** (mine term candidates from Confluence / Jira / Fireflies / documents — Atlassian read strictly sequential — rank, batch-confirm 10–15 at a time), **Style Build** (profile from 3–10 human-written reference texts: tone, syntax, do/don't, few-shot fragments, AI anti-patterns), **Glossary Manage** (CRUD, "how do we call X"), **Glossary Lint** (service: draft in → replacements / style findings / candidates out). Two-level glossary schema: `terms` (canonical + variants + avoid + en) and `phrases` (officialese → living replacements). Storage `~/.grow-pm/knowledge-library/glossary/ + style/` with vault mirror; routing becomes the triple sources / templates / **terms**; one-time sync of phrases + style with the user's project-instruction style guide. Full workflows in skill-local `references/glossary-workflows.md`.
- **`references/artifact-style-gate.md` v2 — Gate 3 "Team language"**, two touches: **3a style preamble BEFORE generation** (lively text must be born lively) and **3b terminology + style lint AFTER** (merged into the groundedness/language checker lens; `lint_mode: suggest | auto | off`). No glossary configured → Gate 3 silently skips.

### Changed — consuming skills and configuration

- **`requirements-creator` → v0.13.0** — new **Step 4.2 Requirements visualization** (annotated screenshot for existing-UI changes, marker = FR row) + style preamble in Step 4.
- **`task-creator` → v0.12.0** — style preamble before drafting descriptions; new **Step 8.5** attaches annotated screenshots to Design/FE tasks with the legend in the description.
- **`write-concept` → v0.11.0** — annotated current-state screenshot in "What Changes for Users" + style preamble.
- **`plugin-configurator` → v2.9.0** — **Terminology & Style setup** and **Attachments (REST) setup** (site + email + token env NAME, never the value; verified by a live GET) as standalone entry points; `references/context-schema.md` gains both section formats + two `deferred_steps` keys; `local-context.example.md` updated.

### Verification

- **Trigger-evals:** new **Group K** (team language + annotation, 13 phrases) — 100% in 2 independent description-only simulation runs; regression re-run of the groups whose members' descriptions changed (B, E, J) — 100%, 36/36 with full agreement between runs. Logged in `testing/trigger-evals.md`.
- **Smoke tests:** end-to-end Pillow annotation per the protocol (marker + arrow + box on a synthetic product-card screenshot) rendered and visually verified; Glossary Lint on a seeded draft caught **5/5** planted violations including inflected forms ("на продуктовій картці" → "на картці товару").
- Remaining live checks for the first real run: REST attachment against the live Confluence/Jira (needs the user's token env), Glossary Build on a real space, Style Build on real reference texts.

## v2.3.0 (2026-07-29)

**Clean artifacts — quality gate with maker–checker verification.** Stakeholder and team feedback on generated artifacts surfaced two recurring defects: AI-invented technical content sneaks into business/functional requirements and task bodies (the team burns time analyzing recommendations nobody asked for), and requirements/stages drift into paragraph prose instead of scannable lists. Both are now blocked by a shared quality gate — and, critically, the gate is executed by an **independent checker subagent, not by the agent that produced the artifact** ("the maker does not check its own work").

### Added — artifact quality gate

- **New shared `references/artifact-style-gate.md`** — two checklists plus an execution model:
  - **Gate 1 — Ungrounded technical content:** a source test for every technical statement ("can I point to where this came from — the user, a document, a ticket?"). Process parameters (feature flag / A/B, platforms, locales) stay; sourced technical facts stay with their source; AI technical assumptions (technology choices, API/schema design, architecture, effort estimates) are prohibited by default. On explicit user request they land in a separate **"Технічні рекомендації (AI)"** block at the end of the document, opened with a mandatory AI-generated warning callout and per-item confidence markers — never inside functional requirements or a task's "How".
  - **Gate 2 — Lists over prose:** any sequence (steps, stages, requirements, criteria, changes, risks) is a list or a table, never a paragraph; paragraphs only for context/motivation (≤ 3–4 sentences); named prose-enumeration markers for the self-check.
  - **Maker–checker execution model:** the checker is a fresh-context subagent that receives ONLY the draft + sources + checklists (never the maker's reasoning), reports structured findings without rewriting, and must walk every section explicitly (anti-rubber-stamping — an empty no-comment report is invalid). One fix cycle + one re-check of fixed locations; disputed findings are surfaced to the user, never silently dropped. Critical artifacts (Confluence publish, Jira creation) get **two checkers with distinct lenses** (form / groundedness). Limits: ≤ 2 checkers, sequential when reading Atlassian MCP; inline fallback carries the explicit marker "незалежність перевірки знижена (inline)". Optional config: `Artifact Quality Gate → review_mode: subagent | inline | off`. Gate 3 (Team language) is reserved for v2.4.0.

### Changed — consuming skills

- **`requirements-creator` → v0.12.0** — Step 2 applies the Gate 1 source test while gathering requirements; Step 4's Business requirements section becomes a **bulleted list of theses** (1–2 sentences each) instead of prose with bold; an optional "Технічні рекомендації (AI)" block (request-only, callout-guarded); new **Step 4.5 — Artifact quality gate** (two lenses) before user review; formatting rule 7 "lists over prose". **Thin-core refactor:** the entire Analyze & Improve mode (A1–A9) moved verbatim to skill-local `references/analyze-improve-mode.md` (core 597 → ~435 lines); inside the mode, A2 gains two content checks (ungrounded technical claims, prose-formatted requirements) and A6 gate-checks the improved document. `references/requirements-template.md` updated to match (theses format + optional AI block).
- **`task-creator` → v0.11.0** — "How" is built ONLY from the requirements and confirmed context (no invented engineering steps; D1 checklists stay process-level); optional "Технічні рекомендації (AI)" section at the end of a description; **batch quality gate** over all drafted descriptions before any Jira issue is created; **Step 12 post-creation verification switches to maker–checker** — the maker fetches the created task, an independent checker evaluates it (previously the same agent that created the tasks verified them); Step 12c adds two checks (list formatting, no ungrounded tech content outside the AI section).
- **`write-concept` → v0.10.0** — Technical Considerations carries only confirmed constraints and dependencies (source test); AI assumptions request-only in the callout-guarded block; new **Step 4.5 — Artifact quality gate** before user review.
- **`meeting-processor` → v0.13.4** (patch) — quality standard pinned: topics / decisions / action items / next steps are always lists or tables; optional full gate run for Confluence-bound MoMs.

### Notes

- Skill descriptions (triggers) are unchanged — no trigger-evals impact.
- Design doc: `Release-Design-v2.3.0-v2.4.0-Artifact-Quality.md` (workspace). v2.4.0 will add annotated screenshots (visual-annotation protocol + REST attachments), the team glossary + style profile in `knowledge-library`, and Gate 3 "Team language".

## v2.2.0 (2026-07-17)

**Debate Mode — role-based adversarial discussion engine.** A single brainstorming agent both generates ideas and approves them: trade-offs between interest groups (buyer / seller / business / risk) go unnoticed and ICE Confidence inflates. The mechanic proved itself ad-hoc in a live research session — four conflicting roles argued a prioritization decision and flipped it — and this release turns it into a reproducible, guarded protocol instead of a lucky prompt.

### Added — Debate Mode

- **`references/debate-protocol.md`** — shared debate engine any skill executes directly (the `subagent-delegation.md` pattern; no new skill): **D0** applicability check (contested decision + ≥ 2 affected interest groups + an existing evidence base — otherwise route to research/ranking instead); **D1** setup (exactly one binary/limited-choice debate question; 3–5 roles via AskUserQuestion from a 10-card preset library plus custom roles, the **Skeptic / Risk-officer always mandatory**; evidence pack `E1…En` strictly from data that passed integrity gates, assumptions explicitly marked `A1…An`); **D2** parallel opening positions (one subagent per role: position / top-3 arguments with E# references / main risk / what would change my mind); **D3** cross-examination (attack the opponents' strongest argument, defend the own weakest, record position shifts; Round 3 only if ≥ 2 roles shifted — and asks the user first; hard max 3 rounds); **D4** facilitator synthesis (consensus points, live disagreements, position shifts, verdict + confidence, **mandatory minority report**, ICE Confidence correction: full consensus +1…+2, unresolved skeptic objection −1…−2, new risks → the hypothesis Risks field); **D5** output & save (a «Debates» section in the parent artifact — round transcripts in collapsed expand-blocks, verdict table open; chains onward to `decision-log` and `experiment-tracker`). Guardrails: anti-sycophancy (convergence forbidden before Round 2; a role that attacked nothing gets its round re-run once), no new facts (debaters get no web/vault/file access), data policy (debaters are local subagents — internal data never leaves the session), cost cap (default 4 roles × 2 rounds = 8 subagent calls, hard cap 12), at most **one** facilitator-added role mid-debate (user-confirmed, within the cap), and an inline-simulation fallback without the Agent tool that must carry the visible marker "inline simulation: role independence reduced".
- **`brainstorm-features` v0.10.0 — Debate mode (Step 3D)**, the primary human entry point. Activates on explicit request, as an offer after Steps 3A–3C, or when called from another skill's Debate hook with a ready evidence pack. Verdict corrections re-sort the ICE tables, new risks append to the hypotheses, the «Debates» section embeds in the saved artifact (Step 5 structure), and Step 9 additionally saves the debate to the vault (`type: "debate"`). Step 4 now proposes "stress-test the top-3 hypotheses via a role debate". The description gains EN+UA debate triggers plus a "Do NOT use" guard (meeting transcript discussions → `meeting-processor`; recording an already made decision → `decision-log`).
- **Debate hooks in 4 skills** (thin, ≤ 8 lines each): `product-research` v0.10.3 (Step 3 — debate over gate-validated findings; the live precedent happened exactly here), `cjm-research` v0.7.3 (top-3 hypotheses after pipeline Step 7; corrections feed the Step 11 risk assessment and the Step 12 report), `write-concept` v0.9.3 (red-team before publishing; unresolved objections land in Risks / Open Questions), `decision-log` v0.2.4 (debate before the save gate; verdict + minority report enter the ADR).
- **Vault artifact type #34 — `debate`** → `Debates/{product}/`: taxonomy row, TYPE_FOLDER_MAP entry, folder-structure block, naming example, and extended frontmatter (`debate_question`, `roles`, `verdict`, `confidence`, `minority_report`, `rounds`, `inline_simulation`). SKILL_CONTEXT_MAP surfaces past debates as context to `brainstorm-features` and `decision-log`.
- **Trigger-evals: Group I** (8 EN+UA phrases — Debate mode vs `meeting-processor` vs `decision-log` vs standard brainstorm) and **Group J** (People contour + the v2.1.1 guards the log-status note demanded: one-on-one vs meeting-processor, performance-review vs product-reporter member-review, write-concept vs requirements-creator on "describe a feature", product-research vs knowledge-library). Fresh descriptions-only simulation run recorded in the Results log.

### Changed

- **`brainstorm-features` core slimmed 443 → 385 lines** (release gate: ≤ 400 after changes): the full Step 3C CJM-hypothesis workflow (3C-1…3C-6 — hypothesis format, CJM-weighted ICE, funnel-impact formulas, categorization, the return contract to `cjm-research`) moved **verbatim** to skill-local `references/cjm-hypotheses-mode.md`, following the v1.34–v1.35 monolith-refactor pattern; the core keeps the activation conditions, the input contract, and a one-paragraph map of the reference.

**Deliberately out of scope (v1):** web search for debaters (evidence pack only — otherwise fact quality is uncontrolled), a separate debate-panel skill, a dedicated debate report template subtype, scheduled headless debates.

---

## v2.1.1 (2026-07-15)

**Re-audit remediation — audit #2 of v2.1.0.** The v2.0.0 audit's fixes verifiably held where they were aimed; a second, independent audit of the result found what they did not reach. Two themes: **live organization data the genericized lint check cannot see**, and **a rule fixed in one place while its copies drifted on** — 7 of the findings are "two sources of one truth" failures. Both validators were green throughout, which is the point: three new checks now cover the classes they missed.

### Fixed — P0, organization data in shipped files

- **`jira-data-protocol.md` contradicted its own first line** ("All org-specific ids live in local-context.md — never hardcoded here"): a real Jira Team UUID **with the team's name**, the org's real Atlassian Cloud ID, and live sprint ids labelled "example only". The team UUID was duplicated in `task-creator`. All now placeholders resolved from `local-context`.
- **`data-integrity-protocol.md` shipped what `data-policy.md` itself classifies as confidential** — real GMV/CR figures and a source catalog naming internal workbooks, an internal live-metrics tool and a tracker key. The anti-patterns and correct-patterns are rewritten on a fictional two-stream product; **the arithmetic, which is the actual lesson, is preserved verbatim**. The catalog moves to `local-context` → `data_sources_catalog`.
- **The `SEX` sprint prefix survived both the v2.0.1 fix and the history purge** — 8 occurrences across 4 files, including a routing trigger shipped to every install. It was the only token from the purge list still present.
- Org vocabulary made universal: the internal live-metrics tool (now the `internal-live` source marker), "Prom-context" geo defaults (now keyed on `product.primary_market`, with the UA ladder as a worked example), release-stream names, feedback segments, and the worked-example persona across 5 files.

### Fixed — P1, validators that passed the leak

Re-injecting the **original v2.0.0 leak** (board id + epic keys + VIP name) into the example file **passed GREEN**. Root cause: after v2.1.0 made the denylist user-supplied, `testing/org-tokens.local` existed in **no environment** — not in CI (gitignored by design) and not on the author's machine — and the mechanism was documented nowhere. A check nobody knows to enable is not a check.

- **Documented** in README (Testing & Contributing) and `Testing-process.md`, with the standing rule: purge an identifier → add it to the denylist **in the same commit**.
- **The layer that must work without it** now fails by shape on literal UUIDs, registry ids (ЄДРПОУ/EDRPOU), internal hostnames (`*.corp`/`internal`/`lan`/`intra`) and service hosts (`gitlab.`/`jira.`/…), and scans **README and `testing/**`** — both previously unscanned, and a real `catalog-ui` stream name in README was found by exactly this change. Placeholder hosts now match whole labels: `mycompany.io` no longer passes because "company" is a substring of it.
- `ghost-skill` fired only when a real skill shared the line, so a chain line naming just its ghost was invisible. `vault-types` missed prose-wrapped and single-quoted `vault_save` types — three real types in `product-research` were unvalidated. `artifact_type`'s enum slurped its section's prose, making `template-library` and `focus-advisor` legal artifact types. `skill_version: v0.9.0` made the sync check invisible rather than failing. `stale-names` was case-blind and skipped README. `duplicate-h1` skipped SKILL.md. TYPE_FOLDER_MAP duplicate keys were last-wins.
- **CI**: `permissions: contents: read`; PyYAML installed with `GROW_LINT_REQUIRE_YAML=1` so the strict frontmatter parse can no longer degrade to a warning that gates nothing; `grep -F` in the shell script (dots in a version were regex wildcards, so `v2x1x0` satisfied a `v2.1.0` check).

### Fixed — P2, the release that skipped two releases

`release.yml` only ever read `plugin.json` at push HEAD, so when v2.0.1, v2.0.2 and v2.1.0 landed in one push, **only v2.1.0 was tagged** — and on the wrong commit (`ea64e32`, a change described in no CHANGELOG entry). v2.0.1 and v2.0.2 are documented releases that cannot be pinned or diffed. A guard now fails the release when the CHANGELOG documents versions between the newest tag and the one being cut (verified against the historical scenario).

### Fixed — P2, vault: schema vs the algorithms that serve it

- **People artifacts key by person, not product** — the schema mandated `{folder}/{product}/` for every People type, scattering one person's goal letters across every product folder while Step P's whole job is "load everything known about a person". The schema was wrong; the protocol and skills were right.
- `vault_init` and `vault_structure_check` **took `plugin_folder_name` and then wrote to the vault root** — one level above the plugin's own folder, into the user's vault. `vault_init` also copied local-context to `REFERENCE-local-context.md`, a filename the Context Mirror, the setup guide and its own smoke test (S-8.2) do not expect — that test could not have passed. Plus a top-level `archive/` and a `dashboard/` folder that exist in no schema.
- `vault_save` built `last_updated`/`linked_hypothesis` (schema: `last_reviewed`/`tested_hypothesis`) and **omitted the required `skill`/`skill_version`**. The Hypothesis Lifecycle branched on `winner_id`/`loser_id`/`hypothesis.id` — fields that exist nowhere — and wrote a status outside the enum; it now branches on `ab-test-results.result`, and an inconclusive test leaves the hypothesis in `testing` (it did not decide it).
- **New check `vault-paths`**: the schema's own MOC templates put the product above the area subfolder and linked an `archive/` folder the same file forbids. Those examples are what the model imitates at save time. 23 example paths corrected; every wikilink in the three vault docs is now checked against TYPE_FOLDER_MAP.
- The 650-line "Template Files" section — the pre-v2.0 flat template system that `template-protocol.md` replaced and `vault_init` forbids writing — is cut to a pointer.

### Fixed — P2, templates: a ladder that reached nothing

- **All five `ops-report` built-ins were unreachable** through the protocol's built-in ladder: it resolves by filename (`builtin://{type}/{subtype}-v1.md`) while they declared `subtype: ops-sprint-plan…` against files named `sprint-plan-v1.md`. Their own `template_id` already implied the unprefixed form. Fixed, and **new check `builtin-subtypes`** enforces it.
- **One CJM report under two `artifact_type`s**: `product-analysis` declared `research`/`cjm-funnel` for the report `cjm-research` saves as `cjm`, then declared a fallback to the shared built-in that a `research`-typed request can never match.
- **Step T meant different things in different files** — four skills had renumbered the shared protocol locally, so "Step T-4" was ambiguous; and **four marker formats** were in use, with 4 of 5 built-ins citing template ids that were not their own.
- `meeting-processor`'s Step T offered `decision` and `review` subtypes its M3 classifier cannot emit.

### Fixed — P2/P3, config, gates and chains

- **One canonical Templates key set** (context-schema): the write side and the schema side had disagreed, so half the config was read-but-undefined and half defined-but-unwritten. Dead key `auto_save_to_vault` removed — written, offered in Update mode, read by nothing.
- **Four sections added that skills already read**: `experiments.stale.*`, `feedback.*`, `plugin_release.*`, `data_sources_catalog`. Key names that pointed at nothing fixed (`product.cjm_configuration.*`, `configured_confluence_spaces`, `knowledge_library.search_modes` with an enum that exists nowhere, `product.default_language`).
- **Callers still forced the mode v2.1.0 removed** — Step 0b and the auto-trigger sent every skill to Onboarding unconditionally, bypassing the backup and vault-recovery branch that exist for a partial wipe.
- **Gates that could not do their job**: `task-creator`'s mandatory check required a description section its own format never writes (every correct task failed it); `cjm-research`'s scheduled health-check still hit an interactive question; `design-bridge`'s only blocking gate read `qa_rules` with no missing-file branch, and its Design System redirect pointed at a configurator step that does not exist.
- **Chains and triggers**: `diagram-prototyper` chained to a skill that does not exist; `design-bridge`'s description advertised two hooks its body removed in v2.0.2; `write-concept`'s next step was labelled, described and executed as three different things; `write-concept`/`requirements-creator` both claimed "describe a feature" with no guard; `focus-advisor` filtered a `revisit_by` field `decision-log` never wrote (a permanent false negative); two connector tool names did not exist.
- `quarterly-planning`'s `plan` mode consumed a step it skipped; `experiment-tracker`'s `awaiting-readout` meant two things, so the stale detector nagged about readouts that existed.

### Fixed — P4, docs that contradict the code

README claimed 7 design skills over a list of 6 (and still named the one v2.1.0 dropped), listed 5 of product-reporter's 6 modes, and enumerated 17 of "24 seed templates" — v2.0.1 fixed the count and not the list. The manifest description was 1259 chars in one sentence, omitted three skills, and had drifted between its two copies (now one canonical 844-char text). `vault-schema` claimed 32 types (33). The CHANGELOG's version-format block sat between two entries, so the release workflow would have appended it to v2.0.1's notes.

**Testing docs stop asserting gates that did not run**: `test-cases.md` promised "Updated EVERY release" over a registry that skips v1.16.0–v1.40.0 and v2.0.0; `trigger-evals.md` calls itself part of the DoD but its last logged run predates the releases that rewrote all 29 descriptions; `output-evals.md` is a blocker with no 3b run recorded for v2.0.x/v2.1.x. Each now states the gap and what the next run must cover. **New check — CI gate parity**: `validate.yml`'s comment promised its gate matches `release.yml`'s "exactly"; a comment cannot enforce that, and drift means a PR goes green, merges, then fails the release with no earlier signal.

### Enforcement

`testing/skill_lint.py`: **13 → 15 checks** (`vault-paths`, `builtin-subtypes`), plus hardened `org-data`, `ghost-skill`, `vault-types`, `artifact-types`, `stale-names`, `duplicate-h1`, `readme-versions`, `skill-version-sync`. `validate-consistency.sh` gains CI gate parity and `grep -F`. Every check verified by injecting its defect into a repo copy — including re-injecting the exact v2.0.0 leak and the exact `ops-` prefix bug.

### Known — still open (needs the repository owner)

- **GitHub still serves the full pre-purge history** via `refs/pull/1..35` — all 35 head SHAs are pre-purge commits. Force-push cannot fix this; it needs a GitHub Support request ("purge unreachable objects / stale PR refs after history rewrite") or repo delete/recreate.
- **The GitLab mirror's `main` is still pre-purge history** and its tags stop at v2.0.0 (branch protection rejected the force-push). Needs unprotect → `git push --force mirror main` → `git push mirror --tags`.
- **The `SEX` prefix remains in git history** (from commit `7fe89fb`); the tree is clean. Worth purging together with whatever resolves the PR-refs question, since a second rewrite would hit the same wall.
- `~/grow-pm-backup-20260714-223144.bundle` (17 MB) still holds the original history — delete once the above is settled.

---

## v2.1.0 (2026-07-14)

**Audit remediation, P3 + P4 — the last of the 2026-07-14 audit.** Closes the behavioural defects: a safety gate that could be skipped, a mode with no workflow, a config field nothing defined, and a health score that only summed correctly for one funnel shape. With this release every finding from the audit is either fixed or deliberately deferred with a reason.

### Fixed — gates and safety

- **`design-bridge` could ship a handoff with no accessibility audit.** Step 4e required `audience ∈ {c-level, dev_handoff}` on top of the intent, so a **handoff with `audience=team` skipped the audit entirely** — and Step 6's "A11y: if Step 4e ran" then never blocked it. This contradicted three other statements of the same rule in the same skill (the checklist's "handoff → full WCAG 2.1 AA, blocker", Quality Standards' "non-negotiable for handoff", and the failure-mode table). The audit now always runs for deck/prototype/handoff; scope and blocker-severity come from `a11y-checklist.md`, which is the one place that decides. The audience does not change whether a disabled user can use the thing.
- **`plugin-configurator` could start a fresh onboarding over live data.** Two mode-selection rules both matched "`local-context.md` is gone but `~/.grow-pm/` or a vault mirror still has data", and textual order sent it to Onboarding — bypassing RM-0's backup and the RM-1 vault-recovery branch that exists for exactly that state. Rules are now ordered, data-presence first.
- **Step P profile writes are uniformly gated.** The protocol gated 2 skills and made the rest "silent-with-notice", while 3 of those declared gated writes anyway. A profile records a judgement about a person; the manager owns it.

### Fixed — dead ends and undecidable routes

- **`focus-advisor`'s `journal` mode had no workflow, no output, and referenced "streaks"** — a word that appeared nowhere else in the plugin. It now has a defined flow: show non-terminal focuses, offer done/snooze/drop/keep per item, gate, write transitions, summarize. Nothing is auto-closed.
- **The `chosen` journal status was unhandled by dedup.** `focus-scoring.md` handled `done`, `snoozed` and `proposed`, so a focus the PM had *already picked* fell through and got re-ranked against fresh signals every morning — the quiet way a chosen focus slips off the brief. It now pins to the top without re-scoring, with an honest nudge after 2 cycles.
- **`design-bridge`'s "handoff with screen generation" route had no deciding input.** Step 0.5 and the toolkit protocol both branched on it; no question collected it. Added Q4a (document existing designs vs generate the screens).
- **Two core-enum capabilities were unreachable:** `figma-write` and `code-first-research` were declared in the toolkit protocol §3 but absent from §6's request→capability mapping, and §3's "user may reference explicitly" escape covers only *custom* capabilities. Both now have routes; every core-enum member appears in the mapping.
- **`deck-subtypes.yaml` was wired to a step that never cited it.** Its header says "Read by design-bridge Step 3"; Step 3 never mentioned it. Combined with the `feature`/`feature-concept` key split (v2.0.2), the slide outlines were unreachable by the documented lookup.

### Fixed — config fields that nothing defined

- **`Focus → Zones`** was read by three strategic collectors (white spaces, NPS themes, knowledge scoping) but defined in no schema — the collectors had nothing to read. Now in the schema, the example, and with a documented fallback.
- **`healthcheck`** lived under `Sources` in both schema files while `focus-advisor` reads `Focus → Scheduled → healthcheck` and the example already had it under `scheduled:` — the lookup found nothing in a schema-conformant file. Moved to Scheduled; subsection order aligned between the write side (`context-schema.md`) and the read side (`focus-signals.md` §8).
- **`Templates` and `Planning` sections** were written by onboarding and read by skills but defined in no schema — `context-schema.md` calls itself "the complete schema definition", and Planning's format was delegated to the example file, which is illustrative, not normative. Both now defined.
- **`deferred_steps` keys**: onboarding wrote 6 keys the enum didn't list (`key-metrics`, `analytics-extended`, `tableau-mcp-required`, `planning`, `focus`, `people`) while the enum listed 2 nobody writes (`okrs`, `competitors`) — for five sections "is it deferred?" was unanswerable. Enum now maps key → writing step.
- **`organization.atlassian_cloud_id`** was required by product-reporter and defined nowhere. Now schema'd, and documented as auto-discoverable.

### Fixed — arithmetic and coverage

- **CJM health-score weights only summed to 100% for a 4-stage funnel.** "First 15% / Middle 25% **each** / Last 35%" is correct for the E-commerce default, but the 5-stage Marketplace funnel scored out of 125 and the 6-stage SaaS funnel out of 150 — silently deflating every health score computed on them. Weights are now shares (first 15% · all middles 50% split evenly · last 35%), with worked examples per shipped template and a two-stage rule.
- **Validate mode couldn't see half the config.** Planning, Focus and Templates were absent from V-4's scoring and from the Update menu the setup steps hand off to — a readiness report could read 100% while the planning suite had nothing to read. Deferred sections are now reported as deferred, not scored as gaps; People and Design Toolkits are presence-only, never scored.
- **Declining the Knowledge Library skipped the Template Library** (Step 12 jumped to Step 14), leaving `templates_setup_completed` unset and Step 16g nudging someone who was never asked — against O-T.2's "always asked, even when using built-in only".
- **CJM health-check notifications** were defined in the schema and editable via Update mode, but no onboarding step collected them. Added 11g.
- The Step 16c skeleton lacked placeholders for the Templates/Planning/Focus/Design-Toolkits/People sections that later steps write into it; the write-ordering (steps 13–15 buffer, 16c writes once) is now explicit.

### Changed

- `local-context.example.md` gains the CJM, Knowledge Library, Templates, Obsidian Vaults and People sections (all schema-defined, none previously exemplified) plus `Focus → zones`.
- README Getting Started now carries the actual install commands and the marketplace/repo names.
- `design:user-research` removed from design-bridge's promises — no step ever called it; `product-research` owns primary research.
- Slide-count guidance in design-bridge now cites `deck-subtypes.yaml` instead of restating different numbers (8–12 vs the yaml's 10/14; 6–8 vs 7/10).
- The `wireframe` boundary is now symmetric and decidable: branded/DS → design-bridge, plain structure → diagram-prototyper, ask when the request doesn't say.

### Files

- Changed: 4 `skills/*/SKILL.md` (minor bump — behavioural), `skills/design-bridge/references/a11y-checklist.md`, `skills/plugin-configurator/references/` (context-schema, onboarding-steps, maintenance-modes), `references/` (cjm-protocol, focus-signals, focus-scoring, people-context-protocol, design-toolkit-protocol, data-integrity-protocol, jira-data-protocol), `local-context.example.md`, `README.md`, `CHANGELOG.md`, `testing/`, both manifests.

---

## v2.0.2 (2026-07-14)

**Audit remediation, P2 — structural drift.** v2.0.1 fixed the defects that were mechanically wrong (leaked data, duplicated docs, phantom paths). This release fixes the ones that were *architecturally* wrong: three documents each claiming to define the vault layout, chain edges that existed only on paper, and a template system whose fallback could not be satisfied. Three new linter checks make each class blocking.

### Fixed — vault layer: one source of truth

- **`vault-schema.md` is now declared the single source of truth for vault layout**, and `vault-protocol.md` (save/init/search) and `obsidian-setup-guide.md` (setup smoke tests) conform to it. Previously all three described *different* layouts: the protocol saved to `{vault}/artifacts/{type}/{product}/` with the MOC at `dashboard/MOC-Dashboard.md`, the schema documented an area-first tree with `_MOC/Dashboard.md`, and the setup guide's four smoke tests checked a third layout — against the very algorithm it delegates to, so they could not have passed.
- **One path rule, no exceptions:** `{vault}/{TYPE_FOLDER_MAP[type]}/{product_slug}/{filename}`. The schema's own tree contradicted its map on nesting order (`CJM/{product}/full-reports/` vs `CJM/full-reports/`); the tree now follows the map. Lifecycle status lives in frontmatter, not in folders.
- **10 artifact types that skills were already saving had no home in the schema** — `feedback-triage` (in the taxonomy but absent from TYPE_FOLDER_MAP, so it had no resolvable folder at all), `report-3t5f`, `presentation`, `prototype`, `handoff` (the schema even called the latter two "existing" while defining neither), `vacancy-profile`, and the People contour. Taxonomy grows 22 → 33 types, all mapped.
- **The People contour gets a defined home:** everything about a person under `People/` — one folder, one sensitivity boundary (`People/goals/`, `/reports/`, `/1-1/`, `/reviews/`, `/offboarding/`, `/delegation/`). The protocol's own wikilink examples pointed at top-level `Goals/`, `Reports/`, `1-1/` while the skills wrote to `People/…` — three homes for the same artifact. `vacancy-profile` sits outside `People/` deliberately: a vacancy is a role, not yet a person.
- **`vault_init` now derives its folders from TYPE_FOLDER_MAP** instead of restating them — the hardcoded list had fallen 7 types behind. Same for the search glob and the MOC paths.
- **`REVERSE_CONTEXT_MAP`** — used by `vault_save` step 7, defined nowhere — is now derived from SKILL_CONTEXT_MAP rather than being a second map to keep in sync. **SKILL_CONTEXT_MAP** grew from 8 to all 29 skills (`local-context-protocol.md` sends every skill to Step 0.5, so the 21 missing rows meant silent skips), with People types restricted to People-contour readers.

### Fixed — chain contracts that existed only on paper

- **`experiment-tracker` was unreachable by chaining.** It claimed inbound edges from `brainstorm-features` and `requirements-creator` — neither mentioned it — while `focus-advisor` routed "A/B test waiting for a decision" straight past it to `product-analysis`. All three edges are now real: brainstorm-features offers registration after ICE ranking, requirements-creator registers A/B specs with their Decision Rule, and focus-advisor routes test-readout and decision-revisit signals through the skills that own that state.
- **`decision-log` named three callers that never called it** (meeting-processor, quarterly-planning, project-planning) plus a focus-advisor signal feed that did not exist. meeting-processor now chains decisions to it (instead of hand-writing `Decisions/` files); the planning skills offer to log scope cuts and replan calls; `revisit_by` dates are a real tactical signal in `focus-signals.md`.
- **`diagram-prototyper`'s inbound table listed 5 callers, none of which still call it** — all moved to design-bridge when it arrived in v1.10.0. Table now lists the actual callers and states the boundary (lo-fi/DS-free visuals here, brand-themed decks there).
- **`design-bridge` claimed auto-triggers from `cjm-research` and `meeting-processor`** that have no hook on the upstream side; both correctly route to diagram-prototyper instead. Rows removed, stale step numbers on the remaining four corrected (Step 7/5 → Step 8).
- Unsubstantiated inbound claims dropped from `roadmap-architect` and `project-planning`. The chain graph describes what exists.

### Fixed — templates and Step P

- **The zero-candidate fallback was unsatisfiable for 4 of 9 types.** `builtin://{artifact_type}/default-v1.md` does not exist for `cjm`, `research`, `presentation` or `ops-report` — those ship only subtype files, deliberately (a generic "default ops report" is not a document anyone wants). The rule is now a ladder: requested subtype → `default-v1` → the type's only built-in → warn.
- **`storage_root` was defined nowhere.** `template-protocol.md` deferred to `persistent-storage.md`, which never mentioned the term; the only concrete rule lived in an onboarding step and named a path the protocol simultaneously called *legacy*. `persistent-storage.md` now defines the resolution (vault → `{vault}/{plugin_folder}`, else `~/.grow-pm`), and its directory tree matches what skills actually create (`Templates/` per the protocol, plus `people/`, `experiments/`, `decisions/`, `focus/`).
- **4 artifact types were declared by skills but absent from the enum** (`roadmap`, `meeting-notes`, `focus`, `delegation-audit`) — users could not create templates for them. The enum is now an explicit, machine-checkable block; template-library's wizard list matches it.
- **`roadmap-architect` had no Step T** — the only artifact-producing planning skill without one, against the protocol's own "MUST".
- **Step P write-gating contradicted itself**: the protocol gated writes for 2 skills and made the rest silent, while 3 of those "rest" declared gated writes anyway. Now uniformly gated — a profile records a judgement about a person, and the manager owns it. `product-reporter` (which writes profile fields from `goal-report`) is documented in the reads/writes table it was missing from.
- **product-reporter's Steps 7–8 were nested inside the `goal-report` section** though their content covers all six modes — read structurally, the five ops modes ended with no feedback loop and no vault save. Promoted to shared final steps; the duplicate goal-report persistence (two destinations, two optionality rules) is resolved.

### Added — validators

Three new checks (13 total): **`vault-types`** (every `vault_save` type is in the taxonomy *and* TYPE_FOLDER_MAP — an unmapped type has no destination), **`artifact-types`** (every Step T `artifact_type` is in the protocol enum), **`chain-contracts`** (a claimed `← X` edge exists on X's side, or X is one this skill calls — the notation carries both meanings). `chain-contracts` found 3 further one-sided claims beyond the audit's list on its first run.

### Files

- Changed: 13 `skills/*/SKILL.md` (patch bump), `references/` (vault-schema, vault-protocol, people-context-protocol, persistent-storage, template-protocol, focus-signals), `skills/plugin-configurator/references/` (obsidian-setup-guide, onboarding-steps, maintenance-modes), `testing/skill_lint.py`, `README.md`, `CHANGELOG.md`, both manifests.

---

## v2.0.1 (2026-07-14)

**Audit remediation (P0 + P1) + the validators that make these defect classes non-recurring.** A full audit of v2.0.0 (29 skills, 30 references, 24 templates, manifests, CI) found 5 critical and 14 major defects that both validators passed green. This release fixes the P0/P1 set and rebuilds `skill_lint.py` so each defect class is now a named, blocking check.

### Security — P0

- **Real organization data removed from shipped files.** `local-context.example.md` carried a genuine team roster (surnames per platform), Jira board id, epic keys with a goal map, sprint anchor, a named VIP stakeholder with email, and an internal mission commit — in a public repo, contradicting the file's own "should NOT be committed" warning. All replaced with placeholders. The same class of leak was cleaned from `planning-core.md` (goal map + feature-naming example), `focus-signals.md` (VIP name), `jira-data-protocol.md` (hardcoded space id), `people-context-protocol.md` (team name), `capacity-model.md`/`roadmap-artifacts.md`/`dependency-model.md` (org labels), `focus-cadence.md` + `trigger-evals.md` (sprint names), `project-planning`/`onboarding-steps` (goal keys), `release-pitfalls.md` (internal GitLab host), the `sprint-review` template (Atlassian host), and one CHANGELOG line with live page ids.
  > Note: this data remains in git history. Remediating history is a separate, deliberate decision.

### Fixed — P1

- **Two protocol documents contained themselves twice.** `references/vault-protocol.md` (1435 → 751 lines) and `references/persistent-storage.md` (699 → 426) each had a stale copy appended below the current one — new versions had been *prepended* instead of replacing (commits `07d0936`, `c152ee0`). The stale halves carried conflicting footers (v1.0 vs v1.1) and lacked the Context Mirror / Pre-Update Backup / Vault Recovery sections, so a reader could land on contradicting guidance. Removed; every load of these protocols is now half the context.
- **Phantom references and ghost skill names.** `product-reporter` pointed its template fallback at `references/builtin-templates/<subtype>.md` — a directory that never existed (real path: `templates/built-in/ops-report/`). `hiring-designer` chained to `people-context` and `onboarding-steps.md` twice cited `write-spec` — neither is a skill. `meeting-processor` still said `Feature-task-creator` (renamed to `task-creator` back in v1.24). `local-context-protocol.md` and `people-context-protocol.md` pointed at `references/context-schema.md`, which exists only skill-locally. `self-improvement.md` cited the unwritten `context-budget.md`.
- **`feature` vs `feature-concept` deck-subtype mismatch.** `deck-subtypes.yaml` keyed the outline as `feature-concept` while design-bridge, the built-in template's frontmatter, and the fallback id all use `feature` — and both callers (`write-concept`, `requirements-creator`) passed `feature-concept`. Exact-key lookup missed in one direction or the other for the most common deck. Canonicalized to `feature`.
- **focus-advisor headless contract contradicted itself** — the headless rules permit the metrics health-check chain when configured, while Quality Standards said "never in headless". The exception is now stated in both places.
- **28 of 29 SKILL.md frontmatters were not valid YAML.** An unquoted `Українською: "…"` inside the plain-scalar `description` terminates the scalar: Claude Code's lenient parser accepted it, but PyYAML/js-yaml/gray-matter — i.e. any external tooling, CI step, or other agent — failed to parse. Rephrased to `Українською — …` (plus three skills with a second `: ` hazard). All 29 now parse strictly.
- **Four descriptions exceeded the 1024-char spec limit** for the field the model routes on: `product-reporter` (1289), `focus-advisor` (1210), `hiring-designer` (1121), `performance-review` (1077). Trimmed with every trigger phrase and boundary preserved. product-reporter's parenthetical also listed 6 of the 8 3T5F elements — dropped rather than corrected, since `reporting-3t5f.md` is the source of truth.
- **README resynced with reality** — 16 skills' versions were stale against their frontmatter (Plugin Configurator claimed v2.5.0 at actual v2.7.0), the Feedback Triage section contradicted the summary table in the same file, "17 built-in templates" understated the shipped 24 (the 7 People templates were undocumented), "Five methodology references" listed six, and `release-pitfalls.md` was cited at a non-existent root path.

### Added — validators (so these classes cannot come back)

- **`testing/skill_lint.py` rebuilt** — 10 named checks, one per defect class the audit found: `frontmatter-yaml` (strict parse + plain-scalar hazard scan, stdlib-only), `frontmatter-fields` (name==folder, semver, description ≤1024), `skill-version-sync`, `ref-paths` (multi-segment paths, `.yaml`, placeholder dirs, skill-local resolution, recursive — the old glob was one level deep and blind to `references/examples/**`), `ghost-skill` (a kebab token on a line citing a real skill, checked against the repo's own auto-derived template vocabulary), `stale-names` (renames incomplete outside CHANGELOG history), `duplicate-h1` (a doc containing itself), `readme-versions` (README ↔ frontmatter), `org-data` (internal identifiers, real Atlassian hosts, non-placeholder emails in shipped files), `deck-subtypes` (yaml keys ↔ template subtypes).
- **`.github/workflows/validate.yml` now runs `skill_lint.py`** alongside the consistency script — previously only the release gate ran it, so a PR could pass CI, merge, and fail the auto-release on main with no earlier signal.
- **`.github/workflows/release.yml`** gains a `concurrency` group (two rapid pushes to main raced the tag check, failing the loser red instead of skipping) and its CHANGELOG-extraction awk now also stops at legacy `## [x.y.z]` headings.

### Files

- Changed: all 29 `skills/*/SKILL.md` (patch bump), `references/` (12 files), `templates/built-in/ops-report/sprint-review-v1.md`, `local-context.example.md`, `README.md`, `CHANGELOG.md`, both manifests, `testing/skill_lint.py`, `testing/trigger-evals.md`, `testing/Testing-process.md`, `testing/test-cases.md`, both workflows.


## v2.0.0 (2026-07-14)

**Wave 3 — the People-contour.** The plugin grows a second contour alongside product/data/delivery: **manager → people → goals → communication → development**. Six new skills, a new person-profile protocol (Step P), five methodology references, one **breaking rename**, and framework upgrades to nine existing skills. Person data is the highest-sensitivity tier — vault/local only, never Confluence/Jira/external LLMs.

### Breaking

- **`team-ops-reporter` renamed to `product-reporter`.** All live references updated across skills, references, manifests, README, and testing (historical CHANGELOG entries keep the old name as an accurate record). The skill gains a new **goal-report (3T5F)** mode (build/audit a person's or a direction's report against a goal). This rename is why the plugin goes to **v2.0.0**.

### Added — foundation (references + protocol)

- **`references/people-context-protocol.md`** — **Step P**: a persistent, vault-local profile per team member (D-type, delegation levels, active goals, reporting cadence, 1-1 history, GTD-index, signals). Storage in the vault `People/` area or `~/.grow-pm/people/`.
- **`references/goal-frameworks.md`** — SMARTCBP (8 checks), MBO-vs-OKR selection, Tell-and-Sell commitment, goal letter, cascade.
- **`references/people-frameworks.md`** — Hersey-Blanchard (D1–D4/S1–S4), 7 levels of Appelo, GTD-index, NVC feedback, "Did you tell them yourself?".
- **`references/reporting-3t5f.md`** — the 8 elements, formatting rules, and manager audit (Forecast QA gate).
- **`references/communication-frameworks.md`** — ARCV follow-ups, CBI, task formulation (why/what/how + DoD by D-level).
- **`references/roi-frameworks.md`** — ROAIP / PRO economics (money-based scoring, task-as-credit, Confidence).
- **`references/session-board.md`** — tactical-session structure + quarterly board-prep checklist.
- **`references/data-policy.md`** — new highest-sensitivity **People-data** tier (strictly local).

### Added — six People-contour skills

- **`goal-setter` (0.1.0)** — SMARTCBP/OKR formulation, 8-check audit, cascade, Tell-and-Sell commitment; writes goals to the profile.
- **`one-on-one` (0.1.0)** — prepare (agenda from profile + seven "how" questions + NVC drafts) / analyze (signals + ARCV follow-up + profile update) / coverage (headless). meeting-processor redirects 1-1s here.
- **`performance-review` (0.1.0)** — goals + GTD-index + Hersey-Blanchard diagnosis into the employer's review template; recommendation (development / style change / yellow card / promotion).
- **`hiring-designer` (0.1.0)** — role design (goal letter first) + universal vacancy profile mapped to the employer HR form + killer questions + goal×experience evaluation.
- **`offboarding-guide` (0.1.0)** — evidence-gated four-meeting algorithm, dismissal script + team message, strictly local.
- **`delegation-coach` (0.1.0)** — 7-levels-of-Appelo audit + S1→S4 hand-off plan + hiring/delegation ROI.

### Added — built-in templates

`goal-letter`, `report-3t5f`, `one-on-one-notes`, `followup-arcv`, `vacancy-profile`, `performance-review`, `offboarding-plan` under `templates/built-in/`.

### Changed — existing skills learn the frameworks

- **`meeting-processor` → 0.13.0** — ARCV follow-up standard (numbered actions, one responsible, verbs, separate Decisions block) + 1-1 detection → redirect to one-on-one.
- **`task-creator` → 0.10.0** — task-formulation gate (why/what/how + DoD + "how"-depth by D-level from the profile). Single-responsible rule intentionally NOT added (team-process conflict).
- **`brainstorm-features` → 0.9.0** — computes **ROI/PRO and ICE by default** (one only on explicit request) + "choose one" / "olympic" overload methods.
- **`requirements-creator` → 0.11.0** — ROI/ICE prioritization gate (Create Step 3e + Analyze A5) → offers brainstorm-features before finalizing.
- **`sprint-planning` → 0.3.0** — GTD-index (planned→done, written to the profile) + delegation-aware assignee fit.
- **`focus-advisor` → 0.4.0** — manager-rhythms signal from person profiles + "choose one" final daily filter + People-contour chains.
- **`quarterly-planning` → 0.3.0** — tactical-session structure + quarterly board-prep package (`references/session-board.md`).
- **`feedback-triage` → 0.2.0** — SH step: each priority pain → a well-formulated task (task-creator standard).
- **`experiment-tracker` → 0.2.0** and **`decision-log` → 0.2.0** — optional cost/ROI (ROAIP) + Tell-and-Sell commitment fields.
- **`plugin-configurator` → 2.7.0** — People setup add-on (roster, cadences, review template, HR-form field map, vault People area) + `people` context-schema section.
- **`template-library` → 0.2.0** — recognizes the seven People-contour artifact types.

### Files

| File | From | To | Change |
|------|------|----|--------|
| skills/team-ops-reporter/ → skills/product-reporter/ | 0.3.0 | 0.4.0 | **rename** + goal-report (3T5F) mode |
| skills/goal-setter/SKILL.md | — | 0.1.0 | new |
| skills/one-on-one/SKILL.md | — | 0.1.0 | new |
| skills/performance-review/SKILL.md | — | 0.1.0 | new |
| skills/hiring-designer/SKILL.md | — | 0.1.0 | new |
| skills/offboarding-guide/SKILL.md | — | 0.1.0 | new |
| skills/delegation-coach/SKILL.md | — | 0.1.0 | new |
| references/{people-context-protocol,goal-frameworks,people-frameworks,reporting-3t5f,communication-frameworks,roi-frameworks,session-board}.md | — | new | People-contour methodology |
| references/data-policy.md | — | — | People-data highest-sensitivity tier |
| skills/meeting-processor/SKILL.md | 0.12.0 | 0.13.0 | ARCV + 1-1 detection |
| skills/task-creator/SKILL.md | 0.9.0 | 0.10.0 | why/what/how + DoD + D-level depth |
| skills/brainstorm-features/SKILL.md | 0.8.0 | 0.9.0 | ROI/PRO + ICE by default |
| skills/requirements-creator/SKILL.md | 0.10.0 | 0.11.0 | ROI/ICE gate |
| skills/sprint-planning/SKILL.md | 0.2.0 | 0.3.0 | GTD-index + delegation-aware assignee |
| skills/focus-advisor/SKILL.md | 0.3.0 | 0.4.0 | manager-rhythms + choose-one |
| skills/quarterly-planning/SKILL.md | 0.2.1 | 0.3.0 | session/board prep |
| skills/feedback-triage/SKILL.md | 0.1.0 | 0.2.0 | SH step |
| skills/experiment-tracker/SKILL.md | 0.1.0 | 0.2.0 | cost/ROI + commitment |
| skills/decision-log/SKILL.md | 0.1.0 | 0.2.0 | cost/ROI + commitment |
| skills/plugin-configurator/{SKILL,references/onboarding-steps,references/context-schema}.md | 2.6.0 | 2.7.0 | People setup + people schema |
| skills/template-library/SKILL.md | 0.1.0 | 0.2.0 | People artifact types |
| templates/built-in/{goal-letter,report-3t5f,one-on-one-notes,followup-arcv,vacancy-profile,performance-review,offboarding-plan}/default-v1.md | — | new | People-contour templates |

### Backwards compatibility

The **only** breaking change is the `team-ops-reporter` → `product-reporter` rename (skill name + directory); update any external references to the old name. The People-contour is fully additive and inert until a `people` section / roster is configured. All existing skills keep their prior behavior; the new framework logic is additive.

---

## v1.40.0 (2026-07-10)

### Added — external design toolkit provider (integration + reference)

`design-bridge` becomes the single routing host for design/prototype work and can delegate hi-fi screen generation to an **external design toolkit** the user declares in `local-context.md` — keeping the plugin core universal for any company. Base logic stays the same when no toolkit is configured (zero regression); org-specifics live only in `local-context.md`.

- **New `references/design-toolkit-protocol.md`** — the contract: `design_toolkits[]` config schema, capability-based routing (core enum `hi-fi-prototype` / `screen-generation` / `ds-tokens` / `figma-write` / `code-first-research` / `design-review` + custom tags), a tier-0 fallback (provider → Figma MCP → Registry → Browser), four entry types (`skill` / `mcp_tool` / `command` / `browser`), a bidirectional delegation contract (feature/platform/requirements/jira → figma_url/branch/files), QA-ownership rule (no double review), data-locality policy, and protocol semver.
- **`design-bridge` → v0.3.0** — new **Step 0.5** (external toolkit routing): capability match → user-confirmed delegation → ingest returns → publish/link/vault. hi-fi prototype delegates to a covering toolkit, else falls back to the built-in Figma path. Added routing-host framing (other skills delegate design/prototype here), QA-ownership rule, vault `design_delivery` marker, description triggers (EN+UA), and new failure modes.
- **`plugin-configurator` → v2.6.0** — new **Design Toolkit setup** step (Extended add-on; standalone "register design toolkit" / "зареєструвати дизайн-тулкіт"). `references/context-schema.md` gains the `design_toolkits` schema + section format and a `design-toolkits` deferred-step key.
- **`references/integration-strategy.md`** — documents tier-0 (provider registry) ahead of the MCP→Registry→Browser chain, for design work only.
- **`references/vault-schema.md`** — `design_delivery` / `toolkit_id` / `toolkit_returns` markers on existing `prototype` / `handoff` types (no new artifact type).
- **`diagram-prototyper` → v0.9.1** — boundary note: hi-fi, design-system-native screen generation routes to `design-bridge`, not here.
- **`local-context.example.md`** — generic `design_toolkits` example (no concrete toolkit shipped).
- **Universality guard** — the plugin repository contains no reference to any concrete toolkit; every toolkit is user-declared in `local-context.md`.

### Files

| File | From | To | Change |
|------|------|----|--------|
| references/design-toolkit-protocol.md | — | new | provider contract: schema, capability routing, tier-0 fallback, entry types, delegation |
| skills/design-bridge/SKILL.md | 0.2.2 | 0.3.0 | minor — Step 0.5 routing host, returns, QA-ownership, triggers, failure modes |
| skills/plugin-configurator/SKILL.md + context-schema.md + onboarding-steps.md | 2.5.0 | 2.6.0 | minor — Design Toolkit registration step + schema + deferred-step key |
| references/integration-strategy.md | — | — | tier-0 provider registry (design only) |
| references/vault-schema.md | — | — | design_delivery / toolkit markers on prototype/handoff |
| skills/diagram-prototyper/SKILL.md | 0.9.0 | 0.9.1 | patch — scope-boundary note (hi-fi routes to design-bridge) |
| local-context.example.md | — | — | generic design_toolkits example |
| testing/trigger-evals.md | — | — | +B7/B8/B9 (design routing) |

### Backwards compatibility

Fully backwards compatible. The provider abstraction is inert when no `design_toolkits[]` is declared in `local-context.md` — design-bridge's built-in Figma path is unchanged. No breaking changes.

---

## v1.39.0 (2026-07-07)

### Added — harness engineering, wave 3: output evals (point 1)

The plugin could already verify *which* skill fires (`trigger-evals` = trajectory); it now verifies *how good the produced artifact is* (output eval). Following the whitepaper's split of output vs trajectory evaluation and "set the bar at the eval, not the demo."

- **`testing/output-evals.md`** (new) — artifact-quality test set: the trajectory/output split, an LM-judge method (weighted 0/1/2 per criterion, pass ≥ threshold, scored against the skill's golden exemplar), how-to-run, and rubrics. Full rubrics for `write-concept`, `requirements-creator`, `cjm-research` (data-integrity bar 0.85); lighter rubrics for `product-analysis`, `brainstorm-features`, `meeting-processor`, `task-creator`.
- **`testing/fixtures/`** (new) — runnable input briefs for the three exemplar skills (`write-concept`, `requirements-creator`, `cjm-research`), paired with the v1.37 golden exemplars as gold references. One shared "recently viewed / save-for-later" thread; the cjm-research fixture embeds an incomplete-period integrity trap.

### Changed

- **`testing/Testing-process.md`** — stage 3 split into **3a Trajectory / scenario walk** and **3b Output eval** (blocker for any changed artifact-producing skill); intro test definition updated. Output-eval ≥ threshold is now part of the DoD for releases touching artifact skills, the way trigger-evals gate description releases.

### Files

| File | Change |
|------|--------|
| testing/output-evals.md | new — rubrics + method + coverage map |
| testing/fixtures/{write-concept,requirements-creator,cjm-research}/brief-v1.md | new — output-eval input briefs |
| testing/Testing-process.md | stage 3a/3b split + DoD |

### Backwards compatibility

Fully backwards compatible. Testing infrastructure only — no runtime skill behaviour changes. No breaking changes.

---

## v1.38.0 (2026-07-07)

### Added — harness engineering, wave 2: artifacts carry their verification (point 4)

Verification is now baked into the spec/PRD, not bolted on afterward — following the whitepaper's "verification moves to the middle of the lifecycle" and "write the tests and evals before generating the code."

- **`requirements-creator` — Acceptance Criteria section** (`references/requirements-template.md`): a Given/When/Then table (AC-N) of testable, binary pass/fail conditions covering main flows + edge/error states — the contract QA and analytics verify against; also seeds Analytics Coverage and Test tasks.
- **`requirements-creator` — Decision Rule** for A/B tests: explicit ship / iterate / kill table tied to the success thresholds, stated before launch so the readout is a lookup, not a debate.
- **`write-concept` — Verification & decision rule** block added to Success Metrics (`references/prd-structure.md`): how each metric is verified (eval/dashboard/test), a Definition of Done checklist, and an experiment decision rule. Acceptance criteria in User Stories upgraded from a flat checklist to a Given/When/Then table.

### Changed

- `requirements-creator` SKILL.md — Step 4 section tables gain the Acceptance Criteria and Decision rule rows (kept in sync with the template).

### Files

| File | From | To | Change |
|------|------|----|--------|
| skills/requirements-creator/SKILL.md + requirements-template.md | 0.9.0 | 0.10.0 | minor — Acceptance Criteria section + A/B Decision Rule |
| skills/write-concept/SKILL.md + prd-structure.md | 0.8.0 | 0.9.0 | minor — Verification & decision rule block + Given/When/Then acceptance |

### Backwards compatibility

Fully backwards compatible. New/enhanced template sections are additive; existing documents and workflows are unaffected. No breaking changes.

---

## v1.37.0 (2026-07-07)

### Added — harness engineering, wave 1 (from Google/Kaggle "The New SDLC With Vibe Coding")

- **`references/harness-map.md`** (new) — anatomy of the plugin's harness across the paper's six layers (instructions / tools / sandboxes / orchestration / guardrails / observability) plus a six-context-type coverage map (instructions / knowledge / memory / examples / tools / guardrails). Names the current thin spots: **Examples** and the output-eval half of Observability. Canonical answer to "what is our harness, and where is it thin."
- **Golden exemplars (few-shot Examples context type)** for the three heaviest artifact skills, loaded on demand and doubling as fixtures for the planned `testing/output-evals.md`:
  - `skills/write-concept/references/examples/prd-example-v1.md` — worked PRD with measurable Success Metrics + a Verification/decision-rule block.
  - `skills/requirements-creator/references/examples/feature-spec-example-v1.md` — feature-spec with an A/B variant, testable Acceptance Criteria, and an explicit ship/kill decision rule.
  - `skills/cjm-research/references/examples/funnel-anomaly-report-example-v1.md` — anomaly report demonstrating period annotation on every metric, Data Integrity caveats, and funnel-impact math.
  - All exemplars are generic/anonymized (no org-specific data); a single "save-for-later" thread runs across them to show the concept → requirements → CJM pipeline.

### Changed

- **`references/self-improvement.md`** — Step 2 (root-cause analysis) gains a **harness-first diagnosis** sub-step: classify the failure by harness layer and route the fix (SKILL wording / integration-strategy / local-context / a gate / delegation / an output-eval) before proposing a change. Links to `harness-map.md`.
- `write-concept`, `requirements-creator`, `cjm-research` SKILL.md — on-demand pointer to their golden exemplar in the drafting/report-assembly step + Additional Resources.

### Files

| File | From | To | Change |
|------|------|----|--------|
| references/harness-map.md | — | new | harness anatomy + 6-context-type coverage map |
| references/self-improvement.md | — | — | harness-first diagnosis sub-step (reference, unversioned) |
| skills/write-concept/SKILL.md | 0.7.0 | 0.8.0 | minor — on-demand golden PRD exemplar |
| skills/requirements-creator/SKILL.md | 0.8.0 | 0.9.0 | minor — on-demand golden feature-spec exemplar |
| skills/cjm-research/SKILL.md | 0.6.0 | 0.7.0 | minor — on-demand golden anomaly-report exemplar |

### Backwards compatibility

Fully backwards compatible. All additions are on-demand references (progressive disclosure) — no change to existing workflows, gates, or outputs. No breaking changes.

---

## v1.36.0 (2026-07-04)

### Added — wave 3 kickoff: three lifecycle skills (21 → 23 skills)

All three ship thin-core from day one (planning-suite pattern, 110–170 lines each, no skill-local references needed yet).

**`experiment-tracker` 0.1.0** — closes the audit's "pipeline drops after the A/B spec" gap. Persistent registry `~/.grow-pm/experiments/registry.yaml` (+ vault mirror `_System/experiments-registry.yaml`) with lifecycle `proposed → specced → running → awaiting-readout → decided`; 6 modes (status board / register / start / readout / decide / stale); stale detection (overdue runs, pending readouts > 3d, idle high-ICE hypotheses > 30d, unscheduled extensions); weekly headless stale-check via `schedule`. Guardrails: verdicts only via product-analysis A/B mode (Data Integrity Gate included); decisions recorded via decision-log; every transition dated and gated.

**`decision-log` 0.1.0** — ADR-style records in vault `Decisions/` (existing `decision` type; L0 fallback `~/.grow-pm/decisions/`): context, ≥2 options considered, decision, rationale with evidence links, consequences. Modes: log (default, also chained from meeting-processor M10 / experiment-tracker decide / planning retro-replan), search ("чому ми вирішили X" — Rationale is the answer), revisit (supersede-flow: history marked, never rewritten).

**`feedback-triage` 0.1.0** — feedback stream → ranked pain map: multi-source intake (files / GDrive / Confluence / pasted, subagent fan-out returning normalized rows), Python normalize with coverage gate (data-integrity applies to trend claims), semantic clustering (language-agnostic, `other` bucket < 15%), `pain_score = frequency × severity × trend`, new/growing/declining themes vs the previous run's vault baseline, hypothesis seeds → brainstorm-features. PII masked; feedback text never leaves the session.

### Changed

- `references/vault-schema.md`: Type Taxonomy 21 → 22 (`feedback-triage` → Research/feedback/) + extended frontmatter block.
- `testing/trigger-evals.md`: Group H (14 phrases — lifecycle trio vs product-analysis / requirements-creator / meeting-processor / product-research / knowledge-library / brainstorm-features).
- README: sections 21–23, Skills Summary 23 rows, "New in v1.36.0"; both manifests → 1.36.0.

### Backwards compatibility
Additive only — three new skills, no changes to existing skill logic. Safe for Claude.

---

## v1.35.0 (2026-07-03)

### Changed — monolith refactor complete (2–4/4): product-analysis, cjm-research, knowledge-library

Closes audit section 3.1. Same recipe as v1.34.0: full read → sed extraction by line ranges (zero loss) → anchor verification → thin core. **No logic change** — all content relocated verbatim; cross-mode guards (Data Integrity Gate, Vault Mirror Sync, service contracts) stay in the cores.

| Skill | Core | New skill-local references | Version |
|---|---|---|---|
| product-analysis | 968 → 364 | `analysis-engine.md` (261: data acquisition 1e + Steps 2–6), `specialized-modes.md` (361: CJM / Post-Release / A/B modes) | 0.11.1 → 0.12.0 |
| cjm-research | 788 → 393 | `cjm-pipeline.md` (234: Steps 4–11), `cjm-reports.md` (181: per-mode formats + publishing + automated health-check) | 0.5.1 → 0.6.0 |
| knowledge-library | 751 → 252 | `library-workflows.md` (354: eight mode workflows), `trust-and-categories.md` (162: trust formula + taxonomy + KL onboarding) | 0.5.0 → 0.6.0 |

Kept in cores by design: product-analysis Step 1.5 Data Integrity Gate + Vault Save + return-payload contract; cjm-research Steps 1–3.5 (init, scope, data load, gate) + Step 12 + chaining; knowledge-library storage model + mode map + cross-skill service contract + Vault Mirror Sync.

Audit KPI closed: the top-4 monoliths were 3 838 lines (47 % of the plugin); cores now total ~1 188 — **-69 %** in always-loaded context, with per-mode references loaded on demand.

### Files

3 × SKILL.md (versions above), 6 new skill-local reference files, both manifests → 1.35.0, README (headers, Skills Summary, "New in v1.35.0").

### Backwards compatibility
Content relocation only; every mode reads the same instructions from a new location. Trigger descriptions untouched — the v1.34.0 evals baseline holds. Safe for Claude.

---

## v1.34.0 (2026-07-03)

### Changed — plugin-configurator refactor (monolith 1/4): 1345 → ~180-line core

First of four monolith refactors from the 2026-07-02 audit (section 3.1), following the planning-suite pattern: thin SKILL.md + on-demand skill-local references. **All content preserved verbatim** (extracted by line ranges, anchors verified); no logic change.

| File | Contents | Lines |
|---|---|---|
| `skills/plugin-configurator/SKILL.md` | mode map, entry conditions, Auto-trigger / Changelog / Product-selection / Enrichment protocols (read by other skills — kept in core), quality standards | ~180 |
| `skills/plugin-configurator/references/onboarding-steps.md` (new) | Onboarding Steps 1–17 in full + Planning setup + Focus setup (Extended add-ons) | ~740 |
| `skills/plugin-configurator/references/maintenance-modes.md` (new) | Reinstall/Migration RM-0..RM-6, Update U-1..U-4, Validate V-1..V-6, View VW-1..VW-4, Versioning Protocol | ~455 |

Also fixed en route: Planning/Focus setup steps were dangling after Additional Resources (outside the workflow) — now integrated into the onboarding reference; removed a leftover `<!-- Додай як новий крок… -->` editorial artifact (pitfall P3); README section 10 version was stale (v2.3.1 while frontmatter was 2.4.2) — synced.

Context economy: entering any single mode now loads ~180 + one reference instead of 1345 lines (~-55% for the largest mode, ~-85% for View/Validate).

- `skills/plugin-configurator/SKILL.md`: **2.4.2 → 2.5.0** (MINOR — structural reorganization, no behavior change).

### Added — trigger-evals baseline (first run)

Two independent description-only routing simulations on v1.33.0, 46 phrases: groups A–F **100%**, G 95% → one eval-label fix (G8 was mislabeled cjm-research for a data-only phrase; expected column corrected to product-analysis). 46/46 primary agreement between runs. Results log filled — baseline recorded before the remaining monolith refactors.

### Backwards compatibility
Content relocation + docs sync only. Every mode reads the same instructions from a new location. Safe for Claude.

---

## v1.33.0 (2026-07-03)

### Added — focus-advisor 0.2.0 → 0.3.0: `strategy` mode + live "PM Focus Board"

Third and final horizon of the attention dispatcher (quarter – year) + a persistent attention panel; completes the focus-advisor design file (phase 3).

- **Strategic collectors** (`references/focus-signals.md` §7, registry table): product goals/missions from a pinned source (`Focus → Goals source`), NPS waves + love/hate themes in the PM's zones, CJM/funnel trends (freshness-guarded), knowledge-library research signals (trust-weighted), leadership-meeting mandates (Fireflies scan), competitive moves (chained product-research), white spaces (zones without active investment).
- **Strategic scoring** (`focus-scoring.md` §5) — goal/mission alignment × lever size × evidence strength → 2–4 bets.
- **Strategy memo** — subtype `strategy-memo`: current state (facts with sources) → bets (what/why/expected effect/first steps) → mandatory **"what we deliberately do NOT do"** → data-hygiene preconditions → next 2 weeks.
- **New chains:** bet needs evidence → product-research / cjm-research / knowledge-library; bet accepted → write-concept → quarterly-/project-planning; goals source stale → knowledge-library refresh + config update.
- **Mode `board` — live "PM Focus Board"** (Step 7b): one-glance panel — current focuses with journal status, due rituals, signal freshness, radar backlog, chain shortcuts. On platforms with live artifacts: dynamic parts re-query connector MCPs on open, local data baked at render, artifact id kept in `~/.grow-pm/focus/board.yaml` (update, not recreate). Fallback: static `~/.grow-pm/focus/board.html`. Board is a view — journal remains the source of truth.
- **Headless** extended to `mode=strategy` (quarterly memo); `auto` now routes all three horizons by phrasing + quarter-boundary nudge.

### Changed

| File | Change | Version |
|---|---|---|
| `skills/focus-advisor/SKILL.md` | strategy + board modes: description, Modes, Steps 1/2/4/5, Step 7b, chain map, headless | 0.2.0 → 0.3.0 |
| `references/focus-signals.md` | §7 strategic collectors registry table; Focus config: Goals source + quarterly strategy memo | n/a |
| `references/focus-scoring.md` | §4/§5 version markers dropped (both live) | n/a |
| `skills/plugin-configurator/SKILL.md` | Focus setup: Goals source capture (Step 3), quarterly strategy memo (Step 5) | 2.4.1 → 2.4.2 |
| `skills/plugin-configurator/references/context-schema.md`, `local-context.example.md` | Focus: goals_source + strategy_memo scheduled entry | n/a |
| both manifests, `README.md` | version sync, New in v1.33.0 | 1.33.0 |

Backwards compatible: `now`/`tactics`/`journal`/headless behavior unchanged. The focus-advisor concept (design file) is now fully shipped: all three horizons + board.

---

## v1.32.0 (2026-07-03)

### Added — focus-advisor 0.1.0 → 0.2.0: `tactics` mode

Second horizon of the attention dispatcher (sprint – quarter), per the focus-advisor design file (phase 2):

- **Tactical collectors** (`references/focus-signals.md` §6, now a full registry table): roadmap plan-vs-actual pace + per-epic stagnation (CQL by quarter label + per-key statuses), roadmap drift vs capacity ceiling, backlog staleness (ICE age from vault Hypotheses/), features missing prerequisites ahead of next 1–2 sprints (work-type DAG), A/B tests past end date without a recorded decision, capacity/availability (vacations, booking deadlines), team events (perf reviews, vacancies, onboarding).
- **Tactical scoring** — ICE (reused from brainstorm-features) + capacity realism + goal alignment (`focus-scoring.md` §4); 3–5 candidates per brief.
- **Tactical brief** — subtype `tactical-brief`: adds quarter position (sprints left, capacity vs plan) and a "decisions waiting on you" section.
- **New chains:** roadmap drift → project-planning `replan`; A/B decision → product-analysis (test readout); team event → task/reminder + team-ops-reporter `member-review`.
- **Headless** extended to `mode=tactics` (weekly tactical brief); `tactical_brief` added to the Focus scheduled config (example, schema, configurator Step 5).

### Changed

| File | Change | Version |
|---|---|---|
| `skills/focus-advisor/SKILL.md` | tactics mode: description, Modes, Steps 2/4/5, chain map, headless | 0.1.0 → 0.2.0 |
| `references/focus-signals.md` | §6 tactical collectors registry table + scheduled config | n/a |
| `skills/plugin-configurator/SKILL.md` | Focus setup Step 5: daily + weekly tactical scheduled briefs | 2.4.0 → 2.4.1 |
| `skills/plugin-configurator/references/context-schema.md`, `local-context.example.md` | Focus → Scheduled: tactical brief entry | n/a |
| both manifests, `README.md` | version sync, New in v1.32.0 | 1.32.0 |

Backwards compatible: `now`/`journal`/headless behavior unchanged; `strategy` still routes to the closest chain (v1.33).

---

## v1.31.0 (2026-07-03)

### Added — new skill: focus-advisor 0.1.0 (20th skill)

PM attention dispatcher — the 4th height of the suite, above structure/quarter/sprint. Collects context signals, ranks them, recommends 1–3 focuses, and chains execution to the right skill; the PM decides. Design file: workspace `skill-design — focus-advisor.md` (decisions fixed 2026-07-03).

**v0.1 scope (MVP):** mode `now` (daily/weekly focus) + `journal` + `auto`, headless contract for scheduled morning briefs (no side-effect actions, mandatory file output). Modes `tactics`/`strategy` — declared, respond with the closest chain until v1.32/v1.33.

**Mechanics:** deterministic ritual cadence ("2nd Monday of the sprint → pre-planning"), mail collector with two-stage "live letters" filter (7-day window, automation never becomes a signal, 24h/48h thresholds, VIP list), meeting-prep detector (analytical slice / deck / talking-points chains), optional metrics health-check chain to product-analysis / cjm-research with source-freshness guard, journal dedup with snooze, mandatory persistence to `~/.grow-pm/focus/` + Vault mirror.

### Added — shared references (root)

| File | Purpose |
|---|---|
| `references/focus-cadence.md` | Cycle position math + default ritual table + overrides + resolution |
| `references/focus-signals.md` | Signal registry per horizon, packet format, cache TTL, mail/calendar detectors, Focus config format |
| `references/focus-scoring.md` | Ranking (urgency+impact+unblock), journal dedup, honesty rules; tactics/strategy scoring stubs |

### Changed — integrations

| File | Change | Version |
|---|---|---|
| `references/vault-schema.md` | +`focus-brief` type (21st): taxonomy row, extended frontmatter, folder `Focus/`; TYPE_FOLDER_MAP backfilled with v1.29 types (diagram, task-breakdown, ops-report, roadmap); stale counts fixed (16/20 → 21) | n/a |
| `skills/plugin-configurator/SKILL.md` | new Step — Focus setup (Extended): sources, VIP senders (prefill from stakeholders), PM goals (prefill from OKRs/missions), cadence overrides, scheduled brief | 2.3.1 → 2.4.0 |
| `skills/plugin-configurator/references/context-schema.md` | Focus Configuration section format + Focus Advisor row in "Which Skills Read What" | n/a |
| `testing/trigger-evals.md` | Group G — attention vs execution (10 phrases: focus-advisor vs sprint-planning vs cjm-research) | n/a |
| both manifests, `README.md` | version sync, skill #20 section + summary row | 1.31.0 |

---

## v1.30.0 (2026-07-03)

### Changed — roadmap-trio disambiguation (audit 3.4, remaining group)

Scope hints added to the last known trigger-collision group:

| Skill | Hint | Version |
|---|---|---|
| roadmap-architect | structure/labeling only, no dates/capacity → quarterly-planning / project-planning | 0.2.0 → 0.2.1 |
| project-planning | horizon beyond one quarter → quarterly-planning for a single quarter, roadmap-architect for structure | 0.2.0 → 0.2.1 |
| quarterly-planning | scope = exactly one quarter → project-planning / roadmap-architect / sprint-planning | 0.2.0 → 0.2.1 |

### Added — testing/trigger-evals.md

36-phrase routing test set across 6 collision groups (CJM trio, prototype pair, roadmap trio + sprint, release semantics, research vs analysis vs knowledge, documents chain), with a manual run protocol, a skill-creator eval-harness option, ≥90 % per-group target, results log, and maintenance rules. Part of the definition-of-done for any description-touching release.

### Fixed — release-manager 0.1.0 → 0.1.1 (self-improvement)

Step 6 now carries an explicit "merging ≠ releasing" guard: a merged PR does not create the tag/Release — verify `releases/latest` after merge. Sourced from two live observations during v1.28.0–v1.29.0.

### Files

| File | Type | Version |
|---|---|---|
| `skills/roadmap-architect/SKILL.md` | description hint | 0.2.1 |
| `skills/project-planning/SKILL.md` | description hint | 0.2.1 |
| `skills/quarterly-planning/SKILL.md` | description hint | 0.2.1 |
| `skills/release-manager/SKILL.md` | Step 6 guard | 0.1.1 |
| `testing/trigger-evals.md` | new test set | n/a |
| both manifests, `README.md` | version sync | 1.30.0 |

### Backwards compatibility
Description wording + new testing asset + one guard note. No workflow change. Safe for Claude.

---

## v1.29.0 (2026-07-03)

### Added — Step V (Save to Vault) in the 11 skills that never wrote to the vault

Closes the biggest gap from the 2026-07-02 audit (section 3.2): only 7 of 18 skills honored architecture principle #5 (vault mirror). Meeting MoMs, requirements, hypotheses, research, diagrams, task breakdowns, ops reports, and roadmaps now accumulate in the Obsidian knowledge graph with wikilinks. Vault remains optional — at L0 every new step skips silently (`IF vault_level > L0 AND sync_mode != "off"`), exactly per `references/vault-protocol.md` → Vault Save.

| Skill | New step | Vault type → folder | Version |
|---|---|---|---|
| requirements-creator | Step 9 (+ A-mode note) | `requirements` → Requirements/ | 0.7.0 → 0.8.0 |
| meeting-processor | M10 | `meeting-notes` → Meetings/ (+ optional `decision`) | 0.11.0 → 0.12.0 |
| brainstorm-features | Step 9 | `hypothesis` → Hypotheses/ (one per finalized hypothesis) | 0.7.1 → 0.8.0 |
| product-research | Step 7 | `competitive-analysis` / `market-research` / `ux-benchmark` → Research/ | 0.9.0 → 0.10.0 |
| diagram-prototyper | Step 10 | `diagram` → Diagrams/ **(new type)** | 0.8.1 → 0.9.0 |
| task-creator | Step 14 | `task-breakdown` → Projects/task-breakdowns/ **(new type)** | 0.8.0 → 0.9.0 |
| team-ops-reporter | Step 8 | `ops-report` → Reports/ops/ **(new type)** | 0.2.1 → 0.3.0 |
| sprint-planning | Step 9 | `roadmap` (subtype sprint-plan) → Roadmaps/ **(new type)** | 0.1.2 → 0.2.0 |
| quarterly-planning | Step 7 | `roadmap` (subtype quarterly/retro) → Roadmaps/ | 0.1.2 → 0.2.0 |
| project-planning | Step 7 | `roadmap` (subtype project-arc; baseline for `replan` drift) → Roadmaps/ | 0.1.2 → 0.2.0 |
| roadmap-architect | Step 6 | `roadmap` (subtype structure-tree) → Roadmaps/ | 0.1.2 → 0.2.0 |

### Changed — vault-schema.md: Type Taxonomy 16 → 20 types

New rows: `diagram` (Diagrams/), `task-breakdown` (Projects/task-breakdowns/), `ops-report` (Reports/ops/), `roadmap` (Roadmaps/, subtype in frontmatter).

### Files

11 × `skills/*/SKILL.md` (versions above), `references/vault-schema.md`, both manifests → 1.29.0, `README.md` (headers, Skills Summary, "New in v1.29.0").

### Backwards compatibility
New optional steps only; every one is a no-op at vault L0. No workflow change for users without a vault. Safe for Claude.

---

## v1.28.0 (2026-07-03)

### Added — release-manager skill (v0.1.0)

New skill: releases the plugin repository itself — one guided pipeline from "changes are ready" to "both remotes tagged, Release published, docs consistent". Every irreversible step (commit, push, merge, publish) is user-gated; Claude prepares, the user's terminal/browser session executes.

**Pipeline (8 steps):** Step 0 local-context (`plugin_release` config: repo path, canonical + mirror remotes, VPN hosts, protected branches, optional Confluence changelog page) → pre-flight guards → scope & semver decision (gate) → bump in the 4 mandatory places → local `validate-consistency.sh` run → gated commit/push terminal block → PR → merge → GitHub Release with tag (canonical remote only) → mirror sync → post-release verification + optional Confluence update + vault release record (Step V).

**`skills/release-manager/references/release-pitfalls.md`** — nine documented failure modes with guards and recovery recipes, all encountered for real during v1.26.1–v1.27.0:

| # | Pitfall |
|---|---|
| P1 | iCloud-evicted files break git (EDEADLK, packfile timeout) → `brctl download` + materialization sweep |
| P2 | Stale git lock files → delete only if >60 min old |
| P3 | Editorial placeholders shipped in CHANGELOG → write final text; validator guards `^<!-- Препенди` |
| P4 | GitHub token without `workflow` scope → fine-grained PAT with Contents + Workflows |
| P5 | Mirror host requires VPN → `vpn_required_hosts` reminder; push retryable |
| P6 | Mirror main diverged / protected → merge on canonical only; reconciliation-merge recipe, never force |
| P7 | Stale raw.githubusercontent CDN → verify via releases/latest, not raw URLs |
| P8 | GitHub editor auto-continues lists → set textarea value directly when automating |
| P9 | Fresh terminal ≠ repo dir → every terminal block starts with `cd <repo>` |

Design notes: generic for any Claude plugin repo (no hardcoded org specifics); version read/written only via structured `"version"` fields; explicit `git add` lists, never `-A`; trigger description carries a "Do NOT use" hint (Jira feature releases → team-ops-reporter / sprint-planning).

### Files

| File | Type | Version |
|---|---|---|
| `skills/release-manager/SKILL.md` | new skill | 0.1.0 |
| `skills/release-manager/references/release-pitfalls.md` | new reference | n/a |
| `.claude-plugin/plugin.json` | version + description | 1.28.0 |
| `.claude-plugin/marketplace.json` | version + descriptions | 1.28.0 |
| `README.md` | section 19, Skills Summary row, "New in v1.28.0" | n/a |

### Backwards compatibility
Additive only — new skill, no changes to existing skills. Safe for Claude.

---

## v1.27.0 (2026-07-02)

### Added — CI validation (GitHub Actions)

- **`.github/workflows/validate.yml`** — runs on every push/PR to main.
- **`testing/validate-consistency.sh`** (also runnable locally) checks:
  1. plugin version identical in `plugin.json` = `marketplace.json` = README header/footer = top CHANGELOG entry, and mentioned in both manifest description tails;
  2. every `skills/*/SKILL.md` has `name` / semver `version` / `description` frontmatter;
  3. no leftover editorial artifacts in CHANGELOG;
  4. every `references/*.md` path mentioned in skills exists;
  5. the pre-v1.26.1 location of jira-data-protocol.md does not reappear.

This makes the v1.26.1 hygiene guarantees permanent — the class of drift documented in the 2026-07-02 audit can no longer land on main unnoticed.

### Changed — trigger disambiguation in skill descriptions

Explicit "Do NOT use / use X instead" routing hints added to the descriptions of the two known trigger-collision groups (audit 2026-07-02, section 3.4):

| Group | Skill | Routing hint added | Version |
|---|---|---|---|
| CJM trio | `cjm-research` | not for standalone dashboard analysis (→ product-analysis) or pure ideation (→ brainstorm-features) | 0.5.0 → 0.5.1 |
| CJM trio | `product-analysis` | data analysis only; end-to-end CJM pipeline → cjm-research | 0.11.0 → 0.11.1 |
| CJM trio | `brainstorm-features` | ideation engine; full CJM pipeline → cjm-research | 0.7.0 → 0.7.1 |
| Prototype pair | `diagram-prototyper` | not for brand-themed DS deliverables → design-bridge | 0.8.0 → 0.8.1 |
| Prototype pair | `design-bridge` | not for quick local diagrams/Mermaid → diagram-prototyper | 0.2.1 → 0.2.2 |

README section headers and Skills Summary synced to the new versions; added "New in v1.27.0" overview paragraph.

### Backwards compatibility
Description wording + new CI infrastructure only; no workflow change inside any skill. Safe for Claude.

---

## v1.26.1 (2026-07-02)

### Fixed — release hygiene: machine-readable version, README catch-up, shared jira-data-protocol

Documentation and manifest release; **no skill-logic change**.

**Manifests — structured `version` field (root cause of the marketplace version-sync issue):**
- `.claude-plugin/plugin.json`: added `"version": "1.26.1"` — previously the version existed only as free text inside `description`, so tooling (and the release process itself) could not read it mechanically. Description tail updated; planning suite mentioned.
- `.claude-plugin/marketplace.json`: added `"version": "1.26.1"` to the plugin entry; descriptions updated.

**README.md regenerated to match the actual plugin state:**
- Version header/footer: 1.25.1 → 1.26.1 (footer previously drifted).
- Added skill sections 15–18 for the Planning Suite (roadmap-architect, project-planning, quarterly-planning, sprint-planning) — previously a dangling Ukrainian block after the footer; removed that block.
- Skills Summary table: now 18 rows with actual frontmatter versions (was 14 rows with stale versions, e.g. Plugin Configurator v1.0.0 → v2.3.1).
- Section headers synced to frontmatter versions (CJM Research 0.5.0, Product Analysis 0.11.0, Product Research 0.9.0, Meeting Processor 0.11.0, Knowledge Library 0.5.0, Design Bridge 0.2.1, Team Ops Reporter 0.2.1).
- Built-in templates: 12 → 17 (added the 5 `ops-report/` templates from v1.14.0).
- Shared References: full actual list of 18 root reference files (was a partial mix of real and placeholder bullets).
- Added "New in v1.26.0" and "New in v1.15.0" overview paragraphs.

**CHANGELOG.md:** removed 3 leftover editorial prepend-instructions (`<!-- Препенди… -->`) that shipped by mistake.

**Moved — `jira-data-protocol.md` to root `references/`:**
- `skills/team-ops-reporter/references/jira-data-protocol.md` → `references/jira-data-protocol.md`. It is shared by 5 skills (team-ops-reporter + the 4 Planning Suite skills), so it belongs with the other cross-skill protocols. Title updated to "(shared)".
- Path references updated in: `sprint-planning`, `quarterly-planning`, `project-planning`, `roadmap-architect` (each **0.1.1 → 0.1.2**). `team-ops-reporter` **0.2.0 → 0.2.1** (its `references/jira-data-protocol.md` mentions now resolve to the root file; no text change needed).

### Files

| File | Type | Version |
|---|---|---|
| `.claude-plugin/plugin.json` | modified (added `version` field) | 1.26.1 |
| `.claude-plugin/marketplace.json` | modified (added `version` field) | 1.26.1 |
| `README.md` | regenerated | n/a |
| `CHANGELOG.md` | cleanup (3 leftover comments) | n/a |
| `references/jira-data-protocol.md` | moved from `skills/team-ops-reporter/references/` | n/a |
| `skills/sprint-planning/SKILL.md` | modified (paths) | 0.1.1 → 0.1.2 |
| `skills/quarterly-planning/SKILL.md` | modified (paths) | 0.1.1 → 0.1.2 |
| `skills/project-planning/SKILL.md` | modified (paths) | 0.1.1 → 0.1.2 |
| `skills/roadmap-architect/SKILL.md` | modified (paths) | 0.1.1 → 0.1.2 |
| `skills/team-ops-reporter/SKILL.md` | modified (version only) | 0.2.0 → 0.2.1 |

### Backwards compatibility
Docs + manifest metadata + file relocation with all in-repo paths updated. No workflow change. Safe for Claude.

---

## v1.26.0 (2026-07-01)

### Added — product-analysis: subagent delegation in Post-Release, A/B, and CJM modes

`product-analysis` already delegated the main data-acquisition fan-out (Step 1) to subagents per `references/subagent-delegation.md`. The three specialized modes did comparable fan-out work but had no explicit delegation callout. This release closes that gap.

Added a subagent-delegation callout to:

| Mode | Step | Batch by | Subagent returns |
|---|---|---|---|
| Post-Release Analysis | PR-2 (Gather metrics data) | metric group / platform | per metric: before value, after value, period, platform, source-type marker + link |
| A/B Test Results | AB-2 (Gather test results data) | segment / dimension | per segment: primary + secondary metric values per group, sample size, significance, source-type marker + link |
| CJM Funnel Analysis | CJM-3 (Load funnel data) | stage (or stage × platform) | per stage: conversion, absolute users, drop-off, trend, segment data, source-type marker + link |

Guardrails preserved in every callout: `data-policy.md` applies to subagents (internal data stays internal), the main agent aggregates and still runs the **Step 1.5 Data Integrity Gate** before analysis, and each mode falls back to inline execution when subagents are unavailable. CJM-3 additionally honors any batch/parallelism limits passed by `cjm-research`.

**No logic change** — the same data is gathered, just off the main context for efficiency. Output formats of all modes are unchanged.

- `skills/product-analysis/SKILL.md`: **0.10.0 → 0.11.0** (frontmatter + Vault Save `skill_version`).

---

## v1.25.1 (2026-06-30)

### Fixed — plugin-configurator refactor (pass 3): substep-numbering cleanup

Closes the item deferred from v1.25.0. Documentation-only; **no behavior change** (substep labels are navigation aids, not logic).

Substep prefixes in `skills/plugin-configurator/SKILL.md` now match their parent Step:

| Step | Was | Now |
|---|---|---|
| Step 5 — Organizations | 3a, 3b | 5a, 5b |
| Step 6 — Products | 4a, 4b | 6a, 6b |
| Step 7 — Analytics & Data Sources | 5a, 5a-Tableau, 5b, 5c | 7a, 7a-Tableau, 7b, 7c |
| Step 8 — Key Metrics & OKRs | 6a, 6b, 6c | 8a, 8b, 8c |
| Step 9 — Teams | 7a, 7b | 9a, 9b |
| Step 11 — CJM Configuration | 9a–9f | 11a–11f |
| Step 16 — Review & save | 13a–13g | 16a–16g |

- Cross-reference "added Tableau in Step 5a" updated to "Step 7a".
- Left unchanged on purpose: the RM-4 (Resume Mode) `4a–4e` block (correctly scoped to RM-4); the "Onboarding Step 3a" reference (Step 3 connector pre-check, still 3a); the "Step 13" mention inside 16g (refers to the Template Library step, still Step 13).
- `plugin-configurator` `2.3.0 → 2.3.1` (PATCH).

This eliminated the ambiguity that blocked an automated pass earlier (`3a` existed in both Step 3 and Step 5; `4a` in both RM-4 and Step 6) — resolved with section-scoped, full-line literal replacements.

### Files

| File | Type | Version |
|---|---|---|
| `skills/plugin-configurator/SKILL.md` | modified (substep prefixes + 1 cross-ref) | 2.3.0 → 2.3.1 |
| `README.md` | version bump 1.25.1 | n/a |

### Backwards compatibility
Cosmetic relabeling only — no behavior change. Safe for Claude.

## v1.25.0 (2026-06-30)

### Changed — plugin-configurator refactor (pass 2)

Second slimming pass on the configurator. Behavior unchanged.

- Extracted 3 self-contained `local-context.md` format/schema blocks — **CJM Configuration**, **Knowledge Library Configuration**, **Obsidian Vaults Configuration** — from `skills/plugin-configurator/SKILL.md` into `skills/plugin-configurator/references/context-schema.md` (verbatim, under a new "local-context.md Section Formats" heading). The skill now points to them (bold lead-in preserved for discoverability).
- `plugin-configurator` `2.2.0 → 2.3.0` (MINOR). SKILL.md ≈ −69 lines (≈ −150 across passes 1+2).

**Deferred to pass 3:** substep-numbering cleanup (Step 5/6/7/8/9/11/16 carry mislabeled `3a/4a/…` substeps). Not done here because of ambiguous duplicate labels (`3a` exists in both Step 3 and Step 5) and live cross-references to the old labels — unsafe for literal replacement; needs a dedicated coordinated pass.

### Files

| File | Type | Version |
|---|---|---|
| `skills/plugin-configurator/references/context-schema.md` | modified (+3 format blocks) | n/a |
| `skills/plugin-configurator/SKILL.md` | modified (3 blocks → pointers) | 2.2.0 → 2.3.0 |
| `README.md` | version bump 1.25.0 | n/a |

### Backwards compatibility
Refactor only — no behavior change (formats reachable via context-schema.md). Safe for Claude.

## v1.24.0 (2026-06-30)

### Changed — plugin-configurator refactor (pass 1)

First conservative slimming pass on the plugin's largest skill (≈1459 lines), following the team-ops-reporter "thin skill + thick reference" pattern. Behavior unchanged.

- Extracted the **Test Mode (sandbox)** workflow (≈83 lines: TM-0..TM-5, sandbox isolation rules, finale diff, Discard/Promote/Keep menu, verification matrix) from `skills/plugin-configurator/SKILL.md` into **`references/test-mode.md`** (NEW); the skill now keeps the section heading + triggers and points to the reference. Content moved verbatim — every TM step/rule/table preserved.
- Removed a **duplicate "Test (sandbox)" row** from the modes table (kept the `Onboarding (Test sandbox)` row, which is grouped with the other onboarding variants and referenced by Onboarding Step 2).
- `plugin-configurator` `2.1.0 → 2.2.0` (MINOR). SKILL.md ≈ −81 lines.

Deferred to later passes: extracting format/schema blocks into `context-schema.md`, and the broader substep-numbering cleanup (kept out of this pass to stay safe).

### Changed — release convention
- The plugin **Description** (`.claude-plugin/plugin.json` + `marketplace.json`) is now stamped with the version and release date on every release — suffix ` — v{version} (released {date})` (idempotent: the previous stamp is replaced).

### Files

| File | Type | Version |
|---|---|---|
| `.claude-plugin/plugin.json` + `marketplace.json` | description stamped (v1.24.0 + date) | n/a |
| `references/test-mode.md` | NEW (extracted) | n/a |
| `skills/plugin-configurator/SKILL.md` | modified (Test Mode → pointer, dup row removed) | 2.1.0 → 2.2.0 |
| `README.md` | version bump 1.24.0 | n/a |

### Backwards compatibility
Refactor only — no behavior change (Test Mode triggers and full procedure remain reachable via the reference). Safe for Claude.

## v1.23.0 (2026-06-30)

### Added — subagent delegation for research / analytics skills

Extends v1.22's fan-out delegation to the heaviest research/analytics passes. Same shared pattern (`references/subagent-delegation.md`), now applied where many sources / competitors / dashboards are read in parallel.

- **`skills/product-research/SKILL.md`** `0.8.0 → 0.9.0` — "Gather data" step: delegate per-competitor / per-source-group reads, aggregate, then run the validation gate.
- **`skills/cjm-research/SKILL.md`** `0.4.0 → 0.5.0` — enrichment fan-out (Step 5 world sources; pattern carries to Step 6 internal): delegate per anomaly / stage / search mode.
- **`skills/product-analysis/SKILL.md`** `0.9.x → 0.10.0` — data acquisition: delegate per dashboard / funnel stage / segment, aggregate, then run the validation gate.
- **`references/subagent-delegation.md`** — fan-out table extended with these three skills.

Additive only — optional guidance with an inline fallback; existing workflows and output formats unchanged.

### Files

| File | Type | Version |
|---|---|---|
| `references/subagent-delegation.md` | modified (fan-out table +3 rows) | n/a |
| `skills/product-research/SKILL.md` | modified (delegation note) | 0.8.0 → 0.9.0 |
| `skills/cjm-research/SKILL.md` | modified (delegation note) | 0.4.0 → 0.5.0 |
| `skills/product-analysis/SKILL.md` | modified (delegation note) | → 0.10.0 |
| `README.md` | version bump 1.23.0 | n/a |

### Backwards compatibility
Additive — inline fallback preserves prior behavior. Safe for Claude.

## v1.22.0 (2026-06-30)

### Added — subagent delegation for fan-out skills

Heavy read / fan-out steps can now delegate to parallel subagents, keeping the main agent's context clean and running independent reads concurrently.

- **`references/subagent-delegation.md`** (NEW) — shared pattern: when to delegate (many items / independent searches), how (split into batches → spawn subagents in parallel → each returns a compact structured result → main agent aggregates), what subagents return, data-policy compliance, batch caps, and inline fallback. Includes a per-skill fan-out table.
- **`skills/meeting-processor/SKILL.md`** `0.10.0 → 0.11.0` — Search mode: delegate per-meeting reads across many meetings.
- **`skills/knowledge-library/SKILL.md`** `0.4.0 → 0.5.0` — Search: delegate per-source / per-mode reads.
- **`skills/team-ops-reporter/SKILL.md`** `0.1.0 → 0.2.0` — Jira fetch (member/quarter-review): delegate paginated/per-period fetches.

Each skill gained a short "Subagent delegation (large fan-out)" note in its Search/fetch step pointing to the shared reference. **Additive only** — the note is optional guidance and an inline fallback preserves prior behavior; output formats unchanged.

### Files

| File | Type | Version |
|---|---|---|
| `references/subagent-delegation.md` | NEW | n/a |
| `skills/meeting-processor/SKILL.md` | modified (delegation note) | 0.10.0 → 0.11.0 |
| `skills/knowledge-library/SKILL.md` | modified (delegation note) | 0.4.0 → 0.5.0 |
| `skills/team-ops-reporter/SKILL.md` | modified (delegation note) | 0.1.0 → 0.2.0 |
| `README.md` | version bump 1.22.0 | n/a |

### Backwards compatibility
Additive — no behavior removed; inline fallback if subagents are unavailable. Safe for Claude.

## v1.21.0 (2026-06-30)

### Changed — dedup wave (2): Self-improvement normalization

Normalized the remaining divergent inline "Self-improvement check" blocks to the same pointer to `references/self-improvement.md` introduced in v1.20, so all skills now share one consistent self-improvement instruction. Behavior unchanged — each block already directed to the same reference.

**Normalized (3):** `brainstorm-features`, `cjm-research`, `meeting-processor`.

**Skipped (1):** `team-ops-reporter` — its Step 7 already states the self-improvement step as a one-line pointer to the reference; replacing it would clobber the unrelated "summary + iterate" instructions in the same sentence. Left as-is.

After v1.20 + v1.21 the Self-improvement check is consolidated to the reference across every skill that had a full inline block (8 skills); no per-skill version bumps (consistency cleanup, no behavior change).

### Files

| File | Type |
|---|---|
| `skills/brainstorm-features/SKILL.md` | modified (block → pointer) |
| `skills/cjm-research/SKILL.md` | modified (block → pointer) |
| `skills/meeting-processor/SKILL.md` | modified (block → pointer) |
| `README.md` | version bump 1.21.0 |

### Backwards compatibility
Housekeeping only — no behavior change. Safe for Claude.

## v1.20.0 (2026-06-30)

### Changed — dedup wave (1): Self-improvement check → reference pointer

Removed a verbatim-duplicated inline "Self-improvement check" block (≈540 chars, identical byte-for-byte) from 5 skills and replaced it with a single pointer to `references/self-improvement.md`, which already holds the full protocol (trigger conditions, 4 steps, improvement types, constraints). No behavior change — the trigger condition and the version-bump/CHANGELOG outcome are preserved via the reference.

**Deduped (5):** `write-concept`, `requirements-creator`, `product-analysis`, `product-research`, `task-creator`.

**Skipped (conservative — wording differs, left intact):** `brainstorm-features`, `cjm-research`, `meeting-processor`, `team-ops-reporter` — these carry slightly divergent inline blocks; a wording-normalization pass for them is deliberately out of scope (separate future change).

**No per-skill version bumps** — additive cleanup, skills already cited `self-improvement.md`; behavior unchanged.

### Files

| File | Type |
|---|---|
| `skills/write-concept/SKILL.md` | modified (block → pointer) |
| `skills/requirements-creator/SKILL.md` | modified (block → pointer) |
| `skills/product-analysis/SKILL.md` | modified (block → pointer) |
| `skills/product-research/SKILL.md` | modified (block → pointer) |
| `skills/task-creator/SKILL.md` | modified (block → pointer) |
| `README.md` | version bump 1.20.0 |

### Backwards compatibility
Housekeeping only — no behavior change. Safe for Claude.

## v1.19.0 (2026-06-29)

### Fixed — product-analysis step order
- **`skills/product-analysis/SKILL.md`** `0.9.0 → 0.9.1` (PATCH) — moved the `Step 0.5: Vault Context Search` block to sit **before** `Step 1.5 — Data Integrity Gate` (it was physically placed below 1.5). Cosmetic ordering fix; no logic change. Closes the last concrete audit item.

### Assessed — dedup pilot
- **Figma-context-check** dedup (write-concept ↔ requirements-creator) was assessed and **skipped**: the two blocks are not cleanly identical (only a 3-bullet middle fragment is verbatim; extracting it would split one logical block across an inline section and a reference). Conservative call — not worth the fragility.
- **Identified clean dedup target for v1.20:** the "Self-improvement check" paragraph is identical across `write-concept`, `requirements-creator`, and `product-analysis` and is already backed by `references/self-improvement.md` — replacing the inline paragraphs with a pointer is the safe, high-payoff dedup.

### Files

| File | Type |
|---|---|
| `skills/product-analysis/SKILL.md` | modified (Step 0.5 reorder + 0.9.1) |
| `README.md` | version bump 1.19.0 |

### Backwards compatibility
Cosmetic reorder only — no behavior change. Safe for Claude.

## v1.18.0 (2026-06-29)

### Changed — i18n: planning suite + tooling translated to English

The plugin is a public English-language repo. The planning-suite additions (v1.15.0–v1.17.0) and the testing tooling had shipped in Ukrainian. This release translates all of that content to English so the whole repo is consistent. Going forward, planning artifacts are drafted in the team's working language and the **English version is what lands in Git**.

**Translated to English:**
- `references/capacity-model.md`, `references/dependency-model.md`, `references/planning-core.md`, `references/roadmap-artifacts.md`
- `skills/quarterly-planning/SKILL.md`, `skills/project-planning/SKILL.md`, `skills/sprint-planning/SKILL.md`, `skills/roadmap-architect/SKILL.md` — including frontmatter `description` (skill triggering is now English)
- `testing/Testing-process.md`, `testing/test-cases.md`, `testing/skill_lint.py` (comments + output strings)
- The Planning setup step in `skills/plugin-configurator/SKILL.md` and the Planning section in `local-context.example.md`
- CHANGELOG entries v1.15.0 / v1.16.0 / v1.17.0 re-written in English

**Skill version bumps (PATCH — English description):** quarterly-planning, project-planning, sprint-planning, roadmap-architect `0.1.0 → 0.1.1`.

### Added — bilingual trigger phrases (all 18 skills)
Every skill's frontmatter `description` now carries trigger phrases in **both English and Ukrainian** (`… Українською: "…", "…"`), so skills trigger regardless of the language the user types. Skill bodies stay English; only the trigger phrase list is bilingual. Additive — no behavior change, existing English triggers preserved (existing skills not version-bumped for this additive change).

**Note:** in `planning-core.md` the status-normalization "Signals" column keeps literal Ukrainian tokens (e.g. `Готово`, `Закінчено`) — those are the actual values matched in the team's Confluence/Jira bodies; translating them would break status detection. They are data, not prose.

### Backwards compatibility
Translation only — no logic or behavior change. Trigger phrases preserved (now in English). Safe for Claude.

## v1.17.0 (2026-06-29)

### Fixed — audit quick-fixes (batch 2)

- **`skills/team-ops-reporter/references/jira-data-protocol.md`** — removed the hardcoded sprint-ids (`55=14979` etc.) that go stale every sprint. Replaced with dynamic resolution at runtime (`openSprints()`/`closedSprints()` in JQL, or `customfield_10020`, or the board's sprints → map name→id). Numbers kept only as a marked "example, not a default".
- **`skills/template-library/SKILL.md`** — fixed the count: "one of **11** actions" → "**12** actions" (the Actions table actually has 12 rows, including `backup` / `restore --from`).

### Changed — lint denoise

- **`testing/skill_lint.py`** — in the dangling-refs check on reference file bodies, **dated example names are now ignored** (`YYYY-MM-DD`, e.g. vault artifacts in `vault-schema.md`/`vault-protocol.md`). Removed 18 false WARNs; the gate stays high-signal.

### Verified — not a bug
- `product-analysis` cross-ref "Step 0h" — **correct** (Step 0h = vault detection actually exists in `references/local-context-protocol.md`, a sub-step of Step 0). Audit flag cleared.

### Deferred → v1.18
- `product-analysis` cosmetic Step 0.5/Step 1.5 ordering (block move) — together with the `plugin-configurator` refactor (careful inspection of large files).

### Files

| File | Type |
|---|---|
| `skills/team-ops-reporter/references/jira-data-protocol.md` | modified (sprint-id → dynamic) |
| `skills/template-library/SKILL.md` | modified (11 → 12 actions) |
| `testing/skill_lint.py` | modified (denoise dated examples) |
| `README.md` | version bump 1.17.0 |

### Backwards compatibility
Additive + doc/tooling fixes. Safe for Claude; trigger phrases and behavior unchanged.

## v1.16.0 (2026-06-29)

### Fixed — audit quick-fixes (batch 1)

- **`skills/design-bridge/SKILL.md`** `0.2.0 → 0.2.1` (PATCH) — fixed the subtype/template_id mismatch that **broke Step T** (template resolution always missed → ad-hoc): `subtype=feature-concept` → `feature`; fallback id `presentation-builtin-feature-concept-v1` / `presentation-builtin-{subtype}-v1` → `presentation-builtin-feature` / `presentation-builtin-{subtype}` (aligned with the real `template_id: presentation-builtin-feature`, `subtype: feature`).
- **`references/capacity-model.md`** — fixed the dangling reference `data-pipeline.md` → `jira-data-protocol.md` (data-pipeline was intentionally never created; the team-ops-reporter protocol is reused).

### Added — testing infrastructure in the repo

- **`testing/Testing-process.md`** — the plugin testing process: 6 stages (backup → static lint → trigger eval → scenario walk → integration → regression → sign-off), test case format, backup protocol, release loop, subagent orchestration, Definition of Done.
- **`testing/skill_lint.py`** — automated Stage 1: frontmatter, `name`==folder, semver, resolution of `references/*`, **skill_version in body == frontmatter**, and (v1.16) **dangling refs in the bodies of reference files** (backticked `*.md`).
- **`testing/test-cases.md`** — the test case registry by stages, updated every release.

### Files

| File | Type | Version |
|---|---|---|
| `skills/design-bridge/SKILL.md` | modified (subtype/template_id fix) | 0.2.0 → 0.2.1 |
| `references/capacity-model.md` | modified (ref fix) | n/a |
| `testing/Testing-process.md` | NEW | n/a |
| `testing/skill_lint.py` | NEW | n/a |
| `testing/test-cases.md` | NEW | n/a |
| `README.md` | version bump 1.16.0 | n/a |

### Deferred
- `product-analysis` phantom Step 0h + step order → v1.17 (needs careful inspection of the file).
- Remaining audit fixes (team-ops-reporter sprint-id, template-library count, plugin-configurator duplicates/numbering) → v1.17/v1.18.

### Backwards compatibility
Additive + bugfix. Safe for Claude; trigger phrases preserved.

## v1.15.0 (2026-06-29)

### Added — Planning Suite (4 skills) + planning core references

A new planning/forecasting layer on top of the existing `team-ops-reporter` reporting. Four skills along the roadmap abstraction levels + four shared references. **Complements** team-ops-reporter (which is descriptive — "what is / was"; planning is "what should be"), does not duplicate it: shared Jira plumbing is reused from `team-ops-reporter/references/jira-data-protocol.md`.

**Two planning axes on a shared foundation:**
- Foundation — `roadmap-architect` (structure, outside of time).
- Vertical — `project-planning` (a single direction across time).
- Horizontal — `quarterly-planning` + `sprint-planning` (a period across all directions).
- The axes link through a shared `% allocation to a direction` and `capacity-model`.

**New skills:**
- **`quarterly-planning` (v0.1.0)** — quarterly roadmap: retro of the previous quarter (delegates `team-ops-reporter` `quarter-review`) → capacity (4 inputs with a gate) → draft + capacity-gate on platform slices → scope correction → artifacts (Confluence + live dashboard + q{N} labels). Modes: retro/plan/full/refresh.
- **`project-planning` (v0.1.0)** — project arc outside of quarters: scope + dependency graph/critical path + duration forecast under % allocation + multi-quarter roadmap + **rolling-reforecast** (`replan`: actuals+carryover → shift to the future + drift vs baseline). Modes: forecast/sequence/roadmap/whatif/replan.
- **`sprint-planning` (v0.1.0)** — sprint pre-planning: focuses from the roadmap → per-member capacity → carryover-risk (delegates `sprint-review`+`member-review`) → readiness scan (work-type DAG) → sequence violation detection → fill + pull-forward → assignee proposals. Modes: groom/plan/review/forecast.
- **`roadmap-architect` (v0.1.0)** — structural hygiene: mapping Goal→Initiative→Epic→Feature, enforcing layout, tree, gap report. Modes: audit/map/tree/onboard.

**New references (shared core):**
- `references/capacity-model.md` — ceiling formula, per-member, baseline+calibration, availability, tech debt, **allocation %**, platform slices, auto-estimate by analogy, gate thresholds (85/100%), quarter↔sprint scaling, duration forecast hook.
- `references/dependency-model.md` — two-level DAG (epic/feature + work-type), topological sort, critical path, cycles, **readiness rule** (threshold on review/in test/done), sources from Jira links.
- `references/planning-core.md` — canonical hierarchy, layout convention (names/labels), status normalization, goal map, **Development Flow** (the team's development flow from onboarding).
- `references/roadmap-artifacts.md` — formats of planning artifacts (quarterly roadmap, project arc, structure tree, capacity-gate, live dashboard) + demarcation from the ops report.

**Changed:**
- `skills/plugin-configurator/SKILL.md` `2.0.0 → 2.1.0` (MINOR) — new **Planning setup** + **Development Flow** survey (typical work sequence, parallelism, dependencies, readiness threshold) in Extended onboarding; writes the Planning section to local-context.
- `local-context.example.md` — new **Planning** section (team composition+capacity rules, sprint cadence+anchor+board, baseline, goal map, gate thresholds, development_flow).
- `README.md` — version 1.15.0, skills #14–17, new references.

### Changed — rename Feature Task Creator → Task Creator
- `skills/feature-task-creator/` → `skills/task-creator/`; `name: feature-task-creator → task-creator`, title "Feature Task Creator" → "Task Creator", description generalized (not just "feature"). All internal references in the plugin updated via find/replace (CHANGELOG history preserved). **Trigger phrases preserved** — phrase-based invocation in Claude does not break.

**Validated** via an end-to-end run on live PROJ/Prom data (Q2 actuals → capacity Q3 → draft → 2 correction iterations + platform slices → published roadmap + live dashboard).

### Files

| File | Type | Version |
|---|---|---|
| `references/capacity-model.md` | NEW | n/a |
| `references/dependency-model.md` | NEW | n/a |
| `references/planning-core.md` | NEW | n/a |
| `references/roadmap-artifacts.md` | NEW | n/a |
| `skills/quarterly-planning/SKILL.md` | NEW | v0.1.0 |
| `skills/project-planning/SKILL.md` | NEW | v0.1.0 |
| `skills/sprint-planning/SKILL.md` | NEW | v0.1.0 |
| `skills/roadmap-architect/SKILL.md` | NEW | v0.1.0 |
| `skills/plugin-configurator/SKILL.md` | modified (Planning setup + Development Flow) | 2.0.0 → 2.1.0 |
| `local-context.example.md` | modified (Planning section) | n/a |
| `README.md` | version + 4 skills + references | n/a |

### Fixed — skill_version sync (audit quick-fix)
Synced `skill_version` in the body (vault_save) with frontmatter: cjm-research 0.2.0→0.4.0, product-analysis 0.6.0→0.9.0, write-concept 0.5.0→0.7.0. Caught by the lint gate during the release. No behavior change.

### Backwards compatibility
Additive only. Existing skills and `local-context.md` are untouched. Planning skills require the Jira MCP (already a prerequisite) and optionally Confluence/calendar; they delegate facts to team-ops-reporter without duplicating the fetch.

## v1.14.0 (2026-06-29)

### Added — Team Ops Reporter skill

New skill `team-ops-reporter` (v0.1.0) — operational team reports built directly on Jira, with five modes: **sprint-plan**, **sprint-review**, **quarter-review**, **initiative-status**, **member-review**. Designed and validated against live PROJ/Prom data during bring-up.

**What it does:**
- Pulls issues via JQL, processes in Python (aggregations, Story Points, carried-vs-new, per-Assignee/Developer), renders from a template, and offers charts.
- Output destination is asked each run: Confluence and/or local `md` + `xlsx`. Visualizations are proposed (burndown, SP dynamics over periods, status donut, load distribution) and built on accept.
- Built-in templates ship under `templates/built-in/ops-report/` (5 subtypes); custom templates via Template Library (`artifact_type: ops-report`, Step T resolution).

**Modes & validated mechanics:**
- **sprint-plan** — directions -> features -> tasks; total / carried / new + SP; per-Assignee and per-Developer breakdowns; key-focus table with per-direction summaries.
- **sprint-review** — closed work (`statusCategory = Done`, **includes the `Ready` status**); releases grouped by stream (app / catalog-ui / backend / company-stats), windowed by `releaseDate`; feature flags ON/OFF (FLAG field + "Випилити прапор" cleanup tasks); closed-per-member; full task list with links.
- **member-review** — role-aware throughput via changelog-backed JQL (`status CHANGED TO "Ready for test" BY "<accountId>" DURING (...)`); delivery metrics from `resolutiondate` + SP; dynamics at any granularity (day/week/sprint/month/quarter/year); matplotlib chart.
- **initiative-status** — % done from `statusCategory` over the epic's `cf[10014]` child tree; status donut; per sub-feature (`X.Y` code in summary); blockers (Flagged `customfield_10021` / `On hold` / blocked-by links).
- **quarter-review** — plan-vs-actual by direction, epics/features fully closed, releases; **fetched per month** because the full-quarter `resolved` JQL times out (>180 s) on this Jira.

**Files:**

| File | Type | Version |
|---|---|---|
| `skills/team-ops-reporter/SKILL.md` | new skill | v0.1.0 |
| `skills/team-ops-reporter/references/jira-data-protocol.md` | new reference | n/a |
| `templates/built-in/ops-report/sprint-plan-v1.md` | new template | v1.0.0 |
| `templates/built-in/ops-report/sprint-review-v1.md` | new template | v1.0.0 |
| `templates/built-in/ops-report/member-review-v1.md` | new template | v1.0.0 |
| `templates/built-in/ops-report/initiative-status-v1.md` | new template | v1.0.0 |
| `templates/built-in/ops-report/quarter-review-v1.md` | new template | v1.0.0 |
| `README.md` | version bump 1.14.0 + skill #14 + templates list | n/a |

### Jira data protocol (PROJ defaults, in `jira-data-protocol.md`)
Custom-field map: Team `customfield_10001`, Story Points `customfield_10036`, Developer `customfield_10041`, QA `customfield_10037`, Epic Link `customfield_10014`, Sprint `customfield_10020`, FLAG `customfield_10043`. Large markdown JQL responses (descriptions inflate them past the token cap) are parsed via `grep -o` compact patterns; pagination via `nextPageToken`. Confluence publishing via `createConfluencePage` (HTML; `parentId` may be a folder id).

### Backwards compatibility
Additive only. Existing skills and `local-context.md` files are unaffected. The new skill requires the Jira MCP (already a plugin prerequisite) and optionally Confluence for publishing.

---

## v1.13.0 (2026-05-11)

### Added — Data Integrity Gate across analytical skills

Universal verification gate for all skills that cite metrics, benchmarks, or claims. Born from a real incident (May 2026 Prom.ua Catalog research project) where 4 progressive errors propagated into 5+ artifacts before user-side detection. Root cause: uncritical citation of raw data points without period verification, multi-source cross-validation, or context annotation.

**Failure patterns this release prevents:**

1. **Incomplete-period extrapolation** — Tableau monthly view extracted mid-month, last cell treated as full month, "-77% PoP" reported as real anomaly (was 7-day partial period)
2. **Week-1 holiday zriz cited as YoY trend** — single weekly comparison from Jan 1-7 propagated as full-year YoY decline ("Listings GMV -29% YoY, Portal -8.6% YoY"); reality across 18 of 19 weeks was both growing +20%/+42%
3. **Cascading derived claims** — "3.4× faster degradation" derived from #2 propagated into 5+ artifacts without re-verification
4. **Missing inline period annotation** — metrics like "CR 0.99%" cited without period context, losing meaning when copied to Slack/slides

**What changed:**

- **`references/data-integrity-protocol.md`** **(NEW)** — universal protocol with 5 gate checks: Period/Context Completeness, Seasonal/Cultural Screening, Multi-Source Cross-Validation (≥2 sources, ≥3 for extreme values), Period Definition Lock + Inline Annotation, Source Type Marker. Defines output statuses (✅ Verified / ⚠️ Caveat / ❌ Blocked) and anti-pattern catalog from real incidents.

- **`references/cjm-protocol.md`** — extended with three new sections: Data Integrity Gate quick reference, Holiday Screening Windows (Ukraine + Global), Anomaly Verification Checklist (mandatory checks for drop > 25% / lift > 50%), recommended reference sources catalog structure.

- **`skills/cjm-research/SKILL.md`** `0.3.1 → 0.4.0` (MINOR) — new **Step 3.5 — Data Integrity Gate (MANDATORY)** between Step 3 (Load CJM data) and Step 4 (Anomaly detection). Step 4 inherits gate status (skip Blocked, propagate Caveat). Quality Standards extended with inline-annotation requirement, caveat propagation, anomaly disclosure, source type markers.

- **`skills/product-analysis/SKILL.md`** `0.8.0 → 0.9.0` (MINOR) — new **Step 1.5 — Data Integrity Gate (MANDATORY)** between Step 1 (Initialization and data acquisition) and Step 2 (Analysis engine). Mode-specific extra checks for Post-Release Analysis (release date + flag activation verification, before/after period balance) and A/B Test Results (sample-size power check, statistical significance reporting, selection bias check, novelty-effect screening). Quality Standards extended; explicit rule: never declare A/B winner/loser without sample-size power check + p-value + holiday-screening + segment-level review.

- **`skills/product-research/SKILL.md`** `0.7.0 → 0.8.0` (MINOR) — new **Step 1.5 — Source Validation Gate (MANDATORY)** between Step 1 (Deep discovery) and Step 2 (Gather data). External-source specific checks: recency thresholds per data type, geographic/cultural context (Ukraine default catalog of direct-fit vs adaptation-required competitors), sensational-claim verification (≥3 sources), bias screening (vendor reports, single competitor PR, social-media). Quality Standards extended with caveat propagation and extreme-claims disclosure.

### Files changed

| File | Type | Skill version |
|------|------|---------------|
| `references/data-integrity-protocol.md` | **NEW** | n/a |
| `references/cjm-protocol.md` | modified (3 new sections appended) | n/a |
| `skills/cjm-research/SKILL.md` | modified (Step 3.5 added, Step 4 + Quality Standards updated) | 0.3.1 → 0.4.0 (MINOR) |
| `skills/product-analysis/SKILL.md` | modified (Step 1.5 added, Step 2 + Quality Standards updated) | 0.8.0 → 0.9.0 (MINOR) |
| `skills/product-research/SKILL.md` | modified (Step 1.5 added, Step 2 + Quality Standards updated) | 0.7.0 → 0.8.0 (MINOR) |

### Migration

No breaking changes. Existing `local-context.md` files remain fully functional. The gate operates with built-in defaults if no `data_sources_catalog` is configured.

**Optional new `local-context.md` field** (recommended for full benefit of Gate Check 3):

```yaml
data_sources_catalog:
  - metric: "Listing GMV YoY"
    primary: "Tableau workbook 285 YtoY view"
    cross_validation: "Orders Dashboard v2 Portal vs Sites"
    methodology_doc: "DT-1773 attribution"
  - metric: "Catalog CR"
    primary: "Listing metrics workbook 285 Overview"
    cross_validation: "Master CJM workbook 125 + Glint live"
  # ... more entries
```

This catalog enables Gate Check 3 (Multi-Source Cross-Validation) to operate automatically — the skill knows which secondary source to query for each metric without user prompting.

### Compatibility

- All three modified skills remain backwards compatible with existing invocation patterns.
- The new gate steps run automatically; users do not need to invoke them explicitly.
- For ⚠️ Caveat metrics, the skill will surface the qualifier in the final report instead of blocking the workflow.
- For ❌ Blocked metrics, the skill will halt with a clear explanation rather than silently producing potentially-wrong output.

### Validation

Each skill version has been validated against the 4 root-cause patterns from the May 2026 incident:

1. ✅ Incomplete-period extrapolation — Gate Check 1 catches this at the source
2. ✅ Week-1 holiday zriz — Gate Check 2 flags holiday windows, forces full-table review
3. ✅ Cascading derived claims — Caveat propagation surfaces qualifiers throughout the report
4. ✅ Missing inline annotation — Gate Check 4 + Quality Standards make annotation mandatory

---
## v1.12.0 (2026-04-29)

### Added — Tableau MCP-First Integration

The plugin now uses the Tableau MCP connector as the **default** path for all Tableau interactions, with browser as a true fallback. Concrete tools (`get-view-data`, `query-datasource`, `get-view-image`, `search-content`, `list-pulse-metrics-*`, `generate-pulse-insight-*`) replaced generic "Tableau MCP → browser" prose in three skills.

**What changed:**
- **`references/integration-strategy.md`** — added a Tableau row to the connector table with explicit MCP tool patterns; new "Per-product tool guidance — Tableau" subsection mapping every common task to the right tool. Added a `tableau-mcp` / `tableau-web` source-marker convention.
- **`skills/product-analysis/SKILL.md`** `0.7.0 → 0.8.0` — rewrote 4 sections (Step 1e Tableau/Analytics, CJM-3 Load funnel data, PR-2 Post-Release Data acquisition, AB-2 A/B Test Tableau dashboards) to make MCP the default and browser the fallback. Each section now logs its source as `tableau-mcp` or `tableau-web` for auditability.
- **`skills/cjm-research/SKILL.md`** `0.3.0 → 0.3.1` — Sources sections now mark Tableau-derived data with `tableau-mcp` / `tableau-web` so users can audit the retrieval method per datapoint.

**New optional `local-context.md` fields** (Tableau section):
- `organization.tableau_site_name` — for non-default Tableau sites
- `organization.tableau_datasource_urls` — map name → URL, used by `query-datasource`
- `organization.tableau_pulse_metric_ids` — map name → metric ID, used by Pulse tools

### Added — Onboarding 2.0 (Basic / Extended / Test modes)

Onboarding redesign addressing first-user feedback that setup felt long and uncertain.

**What changed in `skills/plugin-configurator/SKILL.md`** `1.0.0 → 2.0.0` (MAJOR):
- **New Step 1 — Welcome and onboarding map** showing all 17 steps with type, mode applicability, and time estimates so the user always sees where they are.
- **New Step 2 — Choose mode** with three options: Basic (~3-5 min), Extended (~15-25 min), Test mode (sandbox).
- **New Step 3 — Connector pre-check** — proactive ping of Jira / Confluence / Figma / Notion / Tableau / Fireflies / Calendar / Gmail / GDrive / Slack with a readiness table mapping connectors to skills they unlock. Mandatory connectors block; recommended only warn.
- **Reordered subsequent steps** so Vault precedes Templates and Knowledge Library — Templates and Knowledge can now use the Vault as their storage root from day one.
- **Mode gates** added to every Extended-only step (Step 8 Metrics & OKRs, Step 9 Teams, Step 10 Repos, Step 11 CJM, Step 12 Knowledge, Step 13 Templates, Step 14 Vault, Step 15 Custom). Basic mode silently appends each skipped key to `onboarding.deferred_steps`.
- **New Step 17 — Quick Wins** showing 2-3 actionable next-step recommendations driven from session context (missing Tableau → "connect Tableau MCP", deferred CJM → "run CJM via Quick setup", etc.).
- **New Test Mode workflow** (`Workflow — Test Mode (sandbox)`) — full 5-step procedure (TM-0..TM-5) with sandbox isolation rules, finale diff, Discard / Promote / Keep menu, and a verification matrix for maintainers. Triggers: "dry-run onboarding", "test mode", "тестовий режим", or Step 2 selection.
- **Test Mode redirects all writes** to `~/.grow-pm-sandbox/` (peer of `~/.grow-pm/`). Real config is never read or written. Vault Mirror is fully skipped during sandbox runs.
- **Modes table at the top** updated from "Five Modes" to "Six Modes" — Onboarding (Basic), Onboarding (Extended), Onboarding (Test sandbox), Reinstall / Migration, Update, Validate, View, plus the standalone Test mode entry.

### Added — Obsidian Setup Guide reference (new file)

**`skills/plugin-configurator/references/obsidian-setup-guide.md`** — canonical step-by-step procedure shared by Step 14 (Onboarding) and Update → Vault Management → Connect Vault. Pre-flight checks (Obsidian installed?), 9 setup steps with explicit ✅/⚠️/❌ validation per substep (path validation, `.obsidian/` check, write/read permission test, products binding, sync mode, Obsidian MCP detection, folder init, smoke test, save-to-context), plus a Common errors and recovery table.

### Added — CJM save-offer for ad-hoc invocation

**`references/local-context-protocol.md` Step 0f rewritten** — when a CJM skill (`cjm-research`, `product-analysis` CJM mode, `brainstorm-features` CJM mode) starts without CJM Configuration in `local-context.md`, the user is now offered three options instead of two:

1. Run Plugin Configurator → Step 11 (full setup)
2. **Quick CJM setup (Recommended)** — collect ad-hoc config, then offer to save it before running analysis
3. Skip CJM mode

The Quick CJM setup workflow collects only what the analysis needs (template/stages, dashboards, thresholds, baseline, platforms) and explicitly asks "Save this to `local-context.md`?" before running. If accepted, this becomes equivalent to a full Configurator setup. Hooks added to `cjm-research/SKILL.md` and `product-analysis/SKILL.md` CJM-1.

### Schema additions (`context-schema.md`)

- New **Onboarding Status** section in `local-context.md` (auto-managed by Configurator): `mode`, `basic_completed_at`, `extended_completed_at`, `last_test_run_at`, `deferred_steps`, `skip_nudges`. Backward compatible — old `local-context.md` files get auto-fill on next save.
- 3 new optional Tableau fields under organization (see above).

### Files changed

| File | Type | Skill version |
|------|------|---------------|
| `references/integration-strategy.md` | modified | n/a |
| `references/local-context-protocol.md` | modified (Step 0f) | n/a |
| `skills/product-analysis/SKILL.md` | modified (5 sections) | 0.7.0 → 0.8.0 (MINOR) |
| `skills/cjm-research/SKILL.md` | modified (Sources marker, CJM-1 hook) | 0.3.0 → 0.3.1 (PATCH) |
| `skills/plugin-configurator/SKILL.md` | major restructure | 1.0.0 → 2.0.0 (MAJOR) |
| `skills/plugin-configurator/references/context-schema.md` | modified (Onboarding Status, 3 Tableau fields) | n/a |
| `skills/plugin-configurator/references/obsidian-setup-guide.md` | **NEW** | n/a |
| `local-context.example.md` | modified (Tableau extended fields, Onboarding Status example) | n/a |
| `README.md` | version bump + onboarding modes mention | n/a |

### Migration

`local-context.md` files generated by previous versions remain fully functional. On next save (any Configurator mode), the missing **Onboarding Status** section is added with sensible defaults (`mode: extended`, `extended_completed_at: <now>`, empty `deferred_steps`).

No breaking changes to skill outputs. Tableau-using skills continue to work even if the new MCP-specific fields are not set — they fall back to browser as before.

---

## v1.11.0 (2026-04-20)

### Changed — Brand-Agnostic Refactor (public-repo hygiene)

**Problem:** The public plugin repo accidentally shipped hardcoded brand data for a specific organization (brand hex, brand fonts, DS file key, organization name, paths to a themed pptx template, Jira/Confluence keys) inside `design-integration/` and the `design-bridge` skill. Third-party users installing the plugin would inherit another organization's brand. Ukrainian-language template bodies also shipped publicly even though the repo README is in English.

**Solution:** Pulled all brand-specific and organization-specific values out of the plugin and moved them behind the existing `local-context.md` contract (gitignored, user-owned). Design-bridge now reads brand tokens, DS spec path, pptx theme path, base pptx path, and Figma file key from `product.*` fields in local-context, with neutral placeholder defaults when the user has not configured a DS. Every built-in template and reference has been translated to English; localize via `<!-- lang:xx -->` blocks.

#### Files removed

- **`design-integration/`** (entire folder, 6 files + an org-specific base pptx) — contained organization-specific DS spec, pptx theme, and a base pptx template. Per-organization equivalents now live in the user's workspace folder and are referenced from `local-context.md` under the new Design System section.

#### Files changed — `skills/design-bridge/`

- **SKILL.md** `0.1.0 → 0.2.0` — minor. Removed all hardcoded references to the organization's brand. Now reads `product.design_system_spec`, `product.pptx_theme`, `product.base_pptx`, `product.brand.primary`, `product.brand.dark`, `product.brand.font_primary`, `product.brand.font_display`, and `product.figma.ds_file_key` from local-context. End-to-end example genericized.
- **references/deck-subtypes.yaml** — removed `uk` language keys (kept `en` only); `referenced_theme` now points to `<product.pptx_theme from local-context.md>`.
- **references/figma-playbook.md** — removed organization name and hardcoded file key references; documents the generic brand DS configuration schema.
- **references/a11y-checklist.md** — replaced organization-specific contrast pairs with a schema and instruction to pre-compute pairs under `contrast_pairs:` in the user's DS yaml.

#### Files changed — templates and other skills

- **`templates/built-in/`** — 12 seed templates translated to English. Multilingual format preserved via `<!-- lang:xx -->` blocks; users can add additional language blocks in their own copies via Template Library.
- **Skill files and references** — all workflow instructions and inline examples translated to English; user-facing output language is still controlled by `user.language` in local-context.

#### Files changed — marketplace & plugin metadata

- **`.claude-plugin/plugin.json`** — description reworded from the old brand-specific phrasing to "brand-themed decks… (bring your own Design System via local-context.md)".
- **`.claude-plugin/marketplace.json`** — same description change.
- **`local-context.example.md`** — new **Design System** section per product with placeholder schema for brand tokens, DS spec path (yaml), pptx theme path (yaml), base pptx path, Figma file key, and an optional `contrast_pairs` block. `Language:` default flipped to `en`.

#### Skills changed

| Skill | From | To | Change type |
|-------|------|----|-------------|
| design-bridge | 0.1.0 | 0.2.0 | minor — brand-agnostic refactor; reads all brand fields from local-context |

#### Migration notes

Existing users upgrading from v1.10.0:
1. Run `plugin-configurator` to populate the new Design System fields in your `local-context.md` (see `local-context.example.md`).
2. If you relied on a shipped base pptx / DS spec / pptx theme, move those assets into your own workspace folder (e.g., `design-assets/`) and point `product.base_pptx` / `product.design_system_spec` / `product.pptx_theme` at them.
3. If any of your product-specific templates used `<!-- lang:uk -->` blocks, they remain valid in your local Template Library; only the built-in seed templates were translated to English.

---

## v1.10.0 (2026-04-20)

### Added — Design Bridge Integration

> Note (superseded by v1.11.0): organization-specific values originally captured here were moved out of the repo. The description below has been sanitized accordingly.

**Problem:** Claude's Design plugin ships 7 strong skills (user-research, research-synthesis, ux-copy, accessibility-review, design-system, design-critique, design-handoff) but they don't automatically know the brand tokens of the team using them, don't hook into the PM pipeline (concept → requirements → research → brainstorm), and don't produce brand-themed presentations. PMs had to hand-assemble decks in Google Slides and manually copy brand colors/fonts.

**Solution:** Introduced `design-bridge` — an orchestrator skill that acts as the single entry point for design deliverables (deck, prototype, handoff, research-enrichment), owns the active brand's Design System (DS) theme via local-context, and is invoked as an **optional Step D hook** from four upstream skills. Presentations render from a base pptx template (16:9, layouts pulled from the theme yaml) so output matches what stakeholders expect in their shared drive.

#### Core architecture — 3 layers

1. **Narrative** (from upstream skill: concept body, requirements, research themes, hypotheses)
2. **Template** (from Template Library: deck outline with Handlebars variables, multilingual)
3. **DS theme** (from the user-provided pptx theme yaml: colors, fonts, layouts, chart palette) — applied to the user-provided base pptx via `slide_layouts.get_by_name`

Each layer is independently versioned and swappable. Narrative changes don't invalidate the DS; DS updates don't rewrite templates.

#### Files added — skills/design-bridge/

- **SKILL.md** (`v0.1.0`) — orchestrator with 4 intents (deck, prototype, handoff, research-enrichment), Integration prerequisite, Local context prerequisite, Step T, 9-step workflow with 7 design-skill hooks (research-synthesis, ux-copy, design-critique, design-system, accessibility-review, design-handoff, Figma), pptx rendering via the user's base pptx + `slide_layouts.get_by_name`, WCAG 2.1 AA QA gate, publish, vault save, end-to-end example
- **references/deck-subtypes.yaml** — 4 deck subtypes with slide-by-slide outlines: feature-concept (10), research-highlights (10), ab-test-readout (6), release-readout (7)
- **references/figma-playbook.md** — Auth/permissions (View vs Full seat, rate limits), how to find fileKey + nodeId, common patterns (sync tokens, embed screenshot, concept→prototype, handoff), policy, brand DS configuration schema
- **references/a11y-checklist.md** — WCAG 2.1 AA checklist with schema for pre-computed contrast pairs, touch targets (44×44), keyboard nav, screen reader, motion, forms, deck-specific checks, QA output YAML schema

#### Templates added — templates/built-in/presentation/

- **research-highlights-v1.md** — 10 slides (cover / exec summary / method & sample / theme 1 / quote 1 / theme 2 / quote 2 / theme 3 / quantitative findings / recommendations). English; localize via `<!-- lang:xx -->` blocks.
- **ab-test-readout-v1.md** — 6 slides (cover / hypothesis & setup / primary metric / guardrails / interpretation / decision). English.
- **release-readout-v1.md** — 7 slides (cover / scope / key metrics / wins & learnings / incidents / what's next / ask). English.

#### Skill integrations — Step D hook

Four upstream skills gained an optional `## Step D — Design Bridge handoff (Optional)` step that offers to hand results to design-bridge:

| Skill | From | To | Offers (intent / subtype) |
|-------|------|----|---------------------------|
| write-concept | 0.6.0 | 0.7.0 | deck / feature-concept OR prototype (lo-fi / mid-fi) |
| requirements-creator | 0.6.0 | 0.7.0 | handoff (a11y_audit=true) OR prototype (hi-fi) OR deck |
| brainstorm-features | 0.6.0 | 0.7.0 | prototype (lo-fi) for top-1 hypothesis OR deck (8-slide brainstorm readout) |
| product-research | 0.6.0 | 0.7.0 | deck / research-highlights OR research-enrichment (Figma screenshots, competitor UI) |

Step D is always skippable — user can say "no thanks" and the skill finishes as before.

### Skills changed

| Skill | From | To | Change type |
|-------|------|----|-------------|
| design-bridge (new) | — | 0.1.0 | new — orchestrator for 4 design intents with 7 design-skill hooks |
| write-concept | 0.6.0 | 0.7.0 | minor — Step D hook after vault save |
| requirements-creator | 0.6.0 | 0.7.0 | minor — Step D hook (offers a11y handoff for Create mode) |
| brainstorm-features | 0.6.0 | 0.7.0 | minor — Step D hook (top-1 hypothesis prototype or brainstorm readout deck) |
| product-research | 0.6.0 | 0.7.0 | minor — Step D hook (research-highlights deck or research-enrichment) |

### Documentation

- README.md — version bumped to 1.10.0; new Design Bridge section added; 3 new templates listed under built-in; Figma and base-pptx workflow mentioned under Integration Points.
- CHANGELOG.md — this entry.
- plugin.json + marketplace.json descriptions updated to mention design-bridge capability.

### Backup

Before v1.10.0 writes, backups were taken of the plugin, local-context, and template library (preserved in session backup directory).

---

## v1.9.0 (2026-04-17)

### Added — Multilingual Artifact Template System

**Problem:** Every concept, spec, research report, and MoM was starting from a blank page. No reuse of proven document structures across products. Users in different language markets needed the same artifact in multiple languages without duplicating files.

**Solution:** Introduced a first-class template library with three-tier scope (built-in → user-global → product-specific), single-file multilingual storage (language blocks inside one template via `<!-- lang:xx -->` HTML comments), registry-backed resolution with scoring, skill-driven resolution with user opt-in, and three-tier backup protection.

#### Core architecture

- **Scope tiers:** built-in (ships with plugin) → user-global (shared across all products) → product-specific (per-product override), with inheritance and subtype matching.
- **Multilingual format:** single `.md` file contains all language variants as `<!-- lang:xx --> … <!-- /lang:xx -->` blocks. Obsidian-friendly, preserves link integrity, easy to diff.
- **Storage location:** `{storage_root}/Templates/` — lives in the Obsidian vault if configured (primary), or in the user's chosen custom folder. Survives plugin reinstalls.
- **Registry:** `Templates/_registry.json` indexes all templates with metadata (id, version, scope, artifact_type, subtype, languages, usage_count, checksum).
- **Resolution protocol (T-0 → T-5):** scoring by scope (+5/+3/+1), subtype match (+3/+1), language match (+2/+1), usage_count; tie-breakers by recency.
- **User preference:** `templates.preference` in local-context.md — `auto` (silent use of top match), `always_ask` (list candidates every time), `smart` (ask only when multiple strong candidates exist; default).
- **Three-tier backup:** per-template archive (last 10 versions per template), full pack backups (last 5 before bulk ops), and manual user-triggered backup/restore.

#### Files added

- **references/template-protocol.md** — resolution protocol (T-0 → T-5 with scoring), frontmatter schema, skill integration pattern, edge cases, registry schema, backup invariants.
- **skills/template-library/SKILL.md** (`v0.1.0`) — 11 actions (list / show / add / clone / update / delete / restore / import / export / validate / rebuild-registry), plus backup/restore; wizards for add, add-language, import, update; helper routines `resolve()` and `render()`.
- **templates/built-in/** — 9 seed templates shipped with the plugin:
  - `concept/default-v1.md` — concept (PRD) skeleton
  - `requirements/default-v1.md` — general feature requirements
  - `requirements/ab-test-v1.md` — A/B test spec
  - `research/competitive-v1.md` — competitive analysis + SWOT
  - `research/user-research-v1.md` — user research synthesis
  - `cjm/funnel-v1.md` — CJM funnel analysis with ICE table
  - `epic/default-v1.md` — Jira epic description
  - `task/default-v1.md` — Jira task with DoD and AC
  - `presentation/feature-v1.md` — 10-slide feature deck outline

#### Skill integrations

All consumer skills now include a `## Step T — Template Resolution` section that runs before the first workflow step. Each skill declares its `artifact_type` and subtype inference rules, honors the user's `templates.preference`, and falls back to a built-in structure if no template matches.

| Skill | From | To | Step T artifact_type / subtype |
|-------|------|----|------------------------------|
| write-concept | 0.5.0 | 0.6.0 | `concept` / `default` |
| requirements-creator | 0.5.1 | 0.6.0 | `requirements` / `default` \| `ab-test` \| `bugfix` (Create mode only) |
| product-research | 0.5.0 | 0.6.0 | `research` / `competitive` \| `user-research` \| `market` \| `ux-benchmark` |
| cjm-research | 0.2.0 | 0.3.0 | `cjm` / `funnel` (health-check uses silent auto) |
| feature-task-creator | 0.7.0 | 0.8.0 | `task` + `epic` (resolved once per subtype in batch mode) |
| brainstorm-features | 0.5.0 | 0.6.0 | `research` / `hypothesis-list` \| `cjm-hypotheses` (on save) |
| product-analysis | 0.6.0 | 0.7.0 | `research` / `metrics-analysis` \| `post-release` \| `ab-test-results` \| `cjm-funnel` (non-interactive modes) |
| diagram-prototyper | 0.7.0 | 0.8.0 | `presentation` / `feature` \| `research-highlights` \| `ab-test-readout` \| `release-readout` (decks only) |
| meeting-processor | 0.9.0 | 0.10.0 | `meeting-notes` / `grooming` \| `planning` \| `retro` \| `discovery` \| `status` \| `decision` \| `brainstorm` \| `review` (delegates to downstream skill's Step T when chaining) |

#### Onboarding

- **plugin-configurator** `0.10.0 → 1.0.0` — added **Step O-T — Template Library Setup** between Knowledge Library (Step 10) and Obsidian Vault (Step 11). O-T walks the user through: storage location (reuses Knowledge Library decision), copying built-in templates to their library, setting `templates.preference`, and scheduling a first-use template walkthrough.
- **knowledge-library** `0.3.0 → 0.4.0` — added routing section at top explaining when to use `knowledge-library` (external sources: articles, benchmarks) vs `template-library` (artifact skeletons). Added `template-library` to sibling-skill list.

#### Backup

Before the v1.9.0 changes were written to `v1.9.0-staging/`, full backups were taken of the plugin, local-context, and knowledge library (preserved in session backup directory).

### Skills changed

| Skill | From | To | Change type |
|-------|------|----|-------------|
| template-library (new) | — | 0.1.0 | new — CRUD + resolve + render + backup/restore |
| plugin-configurator | 0.10.0 | 1.0.0 | minor — Step O-T onboarding + template library update mode |
| knowledge-library | 0.3.0 | 0.4.0 | minor — routing to template-library, sibling skill section |
| write-concept | 0.5.0 | 0.6.0 | minor — Step T |
| requirements-creator | 0.5.1 | 0.6.0 | minor — Step T (Create mode) |
| product-research | 0.5.0 | 0.6.0 | minor — Step T |
| cjm-research | 0.2.0 | 0.3.0 | minor — Step T |
| feature-task-creator | 0.7.0 | 0.8.0 | minor — Step T (task + epic) |
| brainstorm-features | 0.5.0 | 0.6.0 | minor — Step T (on save) |
| product-analysis | 0.6.0 | 0.7.0 | minor — Step T (structured reports) |
| diagram-prototyper | 0.7.0 | 0.8.0 | minor — Step T (presentations) |
| meeting-processor | 0.9.0 | 0.10.0 | minor — Step T (MoM) + delegation pattern |

---

## v1.8.0 (2026-04-16)

### Changed — User-Controlled Storage

**Problem:** Knowledge Library and local-context.md were stored in `~/.grow-pm/` — a hidden directory that was invisible to the user, not syncable, and often lost during plugin reinstalls. Users repeatedly lost their curated libraries.

**Solution:** Replaced hardcoded `~/.grow-pm/` storage with a pointer-based system where the user chooses where their data lives.

#### Core architecture change
- `~/.grow-pm/` now contains ONLY a pointer file (`.storage-pointer.yaml`) that tells the plugin where actual data is stored
- Two storage modes: **Vault** (Obsidian vault = primary storage, recommended) or **Custom** (user-chosen folder)
- When Obsidian is configured, the vault IS the primary storage — no separate copy, no mirror sync needed

#### Files changed

- **references/persistent-storage.md** — complete rewrite:
  - New "Pointer + User-Controlled Storage" architecture
  - Storage pointer format (.storage-pointer.yaml)
  - Per-product Knowledge Library support
  - File Resolution Protocol (R-1 through R-4)
  - Storage Selection during onboarding (S-1 through S-3)
  - Recovery flow when pointer is missing — always asks user before creating empty config
  - Change Storage Location workflow (CL-1, CL-2)

- **knowledge-library** `0.3.0 → 0.4.0`:
  - Library Storage section rewritten: vault = primary when configured, custom folder otherwise
  - New "Library Resolution at Skill Start" — 5-step resolution chain with legacy fallback
  - Removed Vault Mirror Sync (no longer needed — vault IS primary)
  - Added: "Never silently create empty library" quality standard

- **plugin-configurator** `0.9.0 → 0.10.0`:
  - New **Step 0 — Storage Selection** in Onboarding (before any data collection)
  - Rewritten **Auto-trigger Protocol** — pointer-based resolution, recovery flow asks user
  - Rewritten **Reinstall / Migration Mode** — 4 scenarios (normal, data moved, legacy, unknown)
  - RM-5: creates/updates storage pointer after migration
  - **Update mode**: added "Storage Location" option to change where data lives
  - All `~/.grow-pm/local-context.md` save references — user's storage location via pointer

---

## v1.7.0 (2026-04-15)

### What changed
Data persistence hardening: added pre-update backup protocol, Obsidian Vault mirror sync, and vault-based recovery to prevent data loss during plugin updates/reinstalls. Knowledge Library was lost during a plugin update — this release adds multiple layers of protection.

### Added
- **Pre-Update Backup Protocol** (persistent-storage.md) — automatic backup of all user data before plugin updates, with timestamped backup directories and manifests
- **Vault Mirror Protocol** (persistent-storage.md) — write-through replication of `~/.grow-pm/` to Obsidian Vault `_System/` and `Knowledge/` folders
- **Vault Recovery Protocol** (persistent-storage.md) — recovery from Obsidian Vault when `~/.grow-pm/` is lost
- **Knowledge Library vault sync** (knowledge-library SKILL.md) — automatic sync to vault after every write operation, plus recovery check at skill start
- **Plugin Configurator vault fallback** (plugin-configurator SKILL.md) — RM-0 pre-update backup, RM-1 vault recovery search, user prompt for vault path if data missing

### Changed
- **persistent-storage.md** — added Pre-Update Backup (PU-1—PU-4), Vault Mirror (VM-1—VM-3), Vault Recovery (VR-1—VR-3) protocols; strengthened deletion behavior section
- **vault-protocol.md** `1.0 → 1.1` — added Context Mirror to Vault section with sync triggers, algorithm, and recovery reference
- **plugin-configurator** `0.8.0 → 0.9.0` — added RM-0 (pre-update backup), RM-1 vault fallback search, RM-1a user vault path prompt, Step 13e vault mirror sync, U-4 vault mirror on update
- **knowledge-library** `0.2.0 → 0.3.0` — added Vault Mirror Sync section with post-write sync and recovery check at start

### Skills changed
| Skill | From | To | Change type |
|-------|------|----|-------------|
| plugin-configurator | 0.8.0 | 0.9.0 | minor — vault recovery + pre-update backup + mirror sync |
| knowledge-library | 0.2.0 | 0.3.0 | minor — vault mirror sync + recovery check |
| persistent-storage (ref) | — | — | minor — 3 new protocols (backup, mirror, recovery) |
| vault-protocol (ref) | 1.0 | 1.1 | minor — context mirror section |

---

## v1.6.0 (2026-04-14)

### Added
- **Obsidian Vault Integration (Phase 1)** — optional persistent knowledge graph for accumulating artifacts across sessions
  - New `references/vault-protocol.md` — shared protocol for vault detection, search, save, and MOC management
  - New `references/vault-schema.md` — frontmatter schema, type taxonomy (16 types), tag taxonomy, folder structure, templates
  - Multi-vault support with per-product vault binding
  - Three-level fallback: L0 (no vault), L1 (file system), L2 (file + Obsidian MCP)

### Changed
- **local-context-protocol.md** — added Step 0h (vault detection) and Step 0.5 (vault context search)
- **plugin-configurator** `0.7.0 → 0.8.0` — new Obsidian Vault section in Onboarding, Update, and Validate modes
- **cjm-research** `0.1.0 → 0.2.0` — added Step 1.5 (vault context) and Step 12.5 (vault save)
- **write-concept** `0.4.0 → 0.5.0` — added Step 0.5 (vault context) and Step 7.5 (vault save)
- **product-analysis** `0.5.0 → 0.6.0` — added Step 0.5 (vault context) and Vault Save with A/B test hypothesis lifecycle updates

---

## [1.5.0] — 2026-04-14

### What changed
- Added `cjm-research` skill (v0.1.0) — CJM pipeline orchestrator with 5 modes: anomalies (quick funnel check), hypotheses (improvement ideas with ICE + funnel impact), full (comprehensive analysis with verification, risk assessment, backlog), health-check (scheduled automated monitoring), comparison (cross-platform side-by-side analysis). Delegates to product-analysis, knowledge-library, product-research, and brainstorm-features. Assembles 5 report formats. Includes independent hypothesis verification (Step 10), risk assessment (Step 11), and post-report skill chaining.
- Updated `product-analysis` (v0.4.0 → v0.5.0) — added CJM Funnel Analysis mode: loads dashboard data per funnel stage, calculates per-stage conversion rates and deviations from baseline, detects anomalies with severity classification (Critical/Warning/Info/Positive per cjm-protocol.md), returns structured data to cjm-research. Added CJM-specific skill chaining offer.
- Updated `product-research` (v0.4.0 → v0.5.0) — added Knowledge Library as data source (search curated sources during research, include in output with trust scores). Added Knowledge Library availability check in Step 1. Added UX Benchmark Research type (benchmark matrix: practice, industry standard, current state, gap, priority). Added CJM Research chaining offer after UX benchmark research.
- Updated `brainstorm-features` (v0.4.0 → v0.5.0) — added CJM Hypotheses mode (Step 3C): generates hypotheses from CJM anomaly data with Data Trigger + Feedback Match + Heuristic Match format. Enhanced ICE scoring with stage-position multipliers (Stage 1: ×1.5, Stage 2: ×1.3, Stage 3: ×1.1, Stage 4+: ×1.0). Added funnel impact calculation per hypothesis. Added hypothesis categorization: Low-hanging fruit / Structural changes / Business logic changes. Added Situation D (invoked by CJM Research) to skip manual context gathering.

### Skills changed
| Skill | From | To | Change type |
|-------|------|----|-------------|
| cjm-research | — | 0.1.0 | new — CJM pipeline orchestrator with 5 modes and 12-step workflow |
| product-analysis | 0.4.0 | 0.5.0 | minor — added CJM Funnel Analysis mode (CJM-1 through CJM-5) |
| product-research | 0.4.0 | 0.5.0 | minor — added Knowledge Library source + UX Benchmark Research type |
| brainstorm-features | 0.4.0 | 0.5.0 | minor — added CJM Hypotheses mode (Step 3C) with funnel impact calculation |

---

## [1.4.0] — 2026-04-11

### What changed
- Persistent user data storage in `~/.grow-pm/` — all configuration, templates, and knowledge library data now stored in user's home directory, surviving plugin uninstalls, reinstalls, and updates
- Added Reinstall/Migration mode to Plugin Configurator — detects existing data, offers recovery/migration/fresh start
- Legacy data discovery and migration from workspace/session directories to `~/.grow-pm/`
- Knowledge Library storage path moved to `~/.grow-pm/knowledge-library/`
- Schema versioning with `.schema-version` file
- Auto-backups before migrations (keeps last 3)
- Updated knowledge-library (v0.1.0 → v0.2.0) — persistent storage, markdown table format, enhanced search modes
- Updated plugin-configurator (v0.6.0 → v0.7.0) — Reinstall/Migration mode, persistent storage protocol, validation report includes CJM and Knowledge Library readiness

### Skills changed
| Skill | From | To | Change type |
|-------|------|----|-------------|
| knowledge-library | 0.1.0 | 0.2.0 | minor — persistent storage in `~/.grow-pm/`, markdown format, enhanced modes |
| plugin-configurator | 0.6.0 | 0.7.0 | minor — Reinstall/Migration mode, persistent storage |

### References changed
| Reference | Change |
|-----------|--------|
| `persistent-storage.md` | new — persistent storage protocol, directory structure, migration |

---

## [1.3.0] — 2026-04-10

### What changed
- Added `knowledge-library` skill (v0.1.0) — local source management with trust scoring, multi-mode search (library, Confluence, Google Drive, Baymard, internet), and bulk import. Service skill for CJM enrichment with direct user management capabilities.
- Added `references/cjm-protocol.md` — shared CJM standards: anomaly severity levels, funnel impact calculation formula, health score formula, cross-platform comparison methodology, hypothesis verification checklist.
- Added `references/funnel-templates.md` — standard funnel stage templates for e-commerce, SaaS, marketplace, and custom product types with recommended metrics and anomaly thresholds.
- Updated `plugin-configurator` (v0.5.0 → v0.6.0) — added CJM Configuration (Step 9) with funnel template selection, stage-dashboard mapping, anomaly thresholds, and default analysis settings. Added Knowledge Library onboarding (Step 10) with source import, Baymard configuration, and search mode setup. Added CJM and Knowledge Library sections to Update, Validate, and View modes.
- Updated `references/local-context-protocol.md` — added Step 0f (CJM configuration check for CJM skills) and Step 0g (Knowledge Library availability check). Added CJM and Knowledge Library fields to context usage guidelines.

### Skills changed
| Skill | From | To | Change type |
|-------|------|----|-------------|
| knowledge-library | — | 0.1.0 | new — local knowledge source management with trust scoring and multi-mode search |
| plugin-configurator | 0.5.0 | 0.6.0 | minor — added CJM Configuration and Knowledge Library onboarding steps |

### References changed
| Reference | Change |
|-----------|--------|
| `cjm-protocol.md` | new — CJM shared standards |
| `funnel-templates.md` | new — funnel stage templates by product type |
| `local-context-protocol.md` | updated — CJM and Knowledge Library support |

---

## [1.2.1] — 2026-04-08

**Plugin summary:** Remove heading numbering from requirements-creator skill and template.

| Skill | Version | Change |
|-------|---------|--------|
| requirements-creator | 0.5.0 → 0.5.1 | Remove heading numbering |

### Details

**requirements-creator (v0.5.1)**
- Removed numbered `# | Section` column from the Step 4 template table — sections are now listed without sequential numbers
- Added formatting rule: headings must NOT be numbered (no "1. Epic", "2. Hypotheses" etc)
- Updated `references/requirements-template.md`: removed numbering from all section headings (e.g., "### 1. Epic" → "### Epic", "#### 5.1 Business Requirements" → "#### Business Requirements")
- Version bump: 0.5.0 → 0.5.1


## [1.2.0] — 2026-04-07

### Plugin
- Enhanced `diagram-prototyper` with Infographic creation support — new visualization type with 5 styles, built-in HTML/CSS generation, and data confidentiality handling

### Skills changed
| Skill | From | To | Change type |
|-------|------|----|-------------|
| diagram-prototyper | 0.6.0 | 0.7.0 | minor — added Infographic as new visualization type with full workflow support |

### Details
- **Step 1b — New visualization type:** Added **Infographic** to the type selection table alongside Diagram, Prototype, Mind Map, and Presentation. Examples: funnel metrics overview, feature comparison, onboarding steps, A/B test results summary, market research highlights
- **Step 1c — Infographic requirements gathering:** 6 targeted questions covering main message, data/metrics, target audience, intended use, key data points, and dimensions/format
- **Step 3b — Infographic style selection (new step):** 5 visual styles with context-based recommendations: Data-driven (metrics, KPIs), Process/timeline (flows, roadmaps), Comparison (feature eval, competitive), Informational/educational (product overviews), Statistical/report (quarterly data, surveys)
- **Step 4 — New tool: HTML/CSS (built-in):** Local generation of infographics as self-contained HTML files with inline CSS and SVG charts. No external LLM dependency. Added to tool recommendation table with 3 infographic-specific rows
- **Step 5 — Infographic prompt construction:** Detailed guidelines for headline, data points, visual hierarchy, section structure, chart types, icons, color scheme, dimensions, footer. Style-specific guidance for all 5 styles. Data confidentiality note: recommends HTML/CSS for infographics with sensitive metrics
- **Step 6a2 — HTML/CSS generation (new substep):** Full generation pipeline: fixed-width container, semantic sections, CSS Grid/Flexbox, inline SVG charts, CSS variables for color palette, system/Google fonts, @media print styles, HTML validation
- **Step 6g — Quality check updated:** Added "Data integrity" check row for infographics (numbers match source, charts proportional, units labeled)
- **Step 8e/8f — Publishing updated:** Added .html to local file formats. New Step 8f for additional infographic export (PNG, PDF, HTML)
- **Step 9 — Skill chaining updated:** New chaining path for infographics from product-analysis/product-research to Presentation Creator
- **Inbound chaining updated:** product-research and product-analysis now suggest infographics in their visualization offers
- **Quality standards updated:** Added HTML validity, self-containment, browser rendering, and data proportion accuracy requirements



## [0.9.0] — 2026-04-01

### Plugin
- Enhanced `meeting-processor` with calendar integration and enriched participant context

### Skills changed
| Skill | From | To | Change type |
|-------|------|----|-------------|
| meeting-processor | 0.8.0 | 0.9.0 | minor — calendar enrichment step + participant context passing |

### Details
- **Step M1d — Calendar enrichment:** After finding a meeting, optionally look up the matching calendar event (Google Calendar MCP or Microsoft Calendar MCP) to extract participants (with emails, roles, RSVP), agenda, attached documents (Google Docs, Confluence, Figma, presentations), organizer, and recurrence info. Reads attached materials for additional context
- **Enhanced M2 data merging:** Calendar data merged with transcript data using priority rules. Discrepancies marked (invited but silent, not invited but spoke)
- **Enhanced M9 skill chaining:** Full participant context (name, email, role, attendance status) now passed to all downstream skills. Per-skill content mapping ensures each target skill gets the data it needs (e.g., participants with roles for task assignment, speaker attribution for research)
- **MoM template updated:** Participants table now includes Email and Status columns

---

## [0.8.0] — 2026-04-01

### Plugin
- Added new skill **meeting-processor** — process meetings from any source to extract action items, decisions, and structured reports

### Skills changed
| Skill | From | To | Change type |
|-------|------|----|-------------|
| meeting-processor | — | 0.8.0 | new skill |

### Details
- **Two modes:** Process (single meeting → structured MoM or short summary) and Search (cross-meeting query → chronological synthesis)
- **Tool-agnostic input:** Fireflies MCP, other meeting tool MCPs, uploaded files (audio/video/text/srt), pasted text
- **Auto-classification:** 5 meeting types (Grooming, Discovery, Demo/Retro, Status, Brainstorm) with multi-type support, user confirmation
- **Type-adaptive extraction:** common blocks (participants, topics, decisions, action items, open questions) + type-specific blocks (estimates for grooming, quotes for discovery, etc.)
- **Skill chaining:** Grooming → feature-task-creator, Discovery → product-research/requirements-creator, Brainstorm → brainstorm-features, Any → diagram-prototyper
- **Publishing:** Confluence, Notion, local file

---

## [0.7.0] — 2026-03-31

### Plugin
- Enhanced `feature-task-creator` with two new workflow improvements

### Skills changed
| Skill | From | To | Change type |
|-------|------|----|-------------|
| feature-task-creator | 0.4.0 | 0.7.0 | minor — added Step 6b (field validation with user confirmation for uncertain values) and Step 12 (post-creation verification with auto-fix) |

### Details
- **Step 6b — Validate field values before creation:** Before creating tasks, the skill now categorizes each field value by confidence level (Certain / Inferred / Uncertain / Unknown), presents inferred values for confirmation, and asks the user for uncertain or unknown values with proposed options
- **Step 12 — Post-creation verification:** After creating all tasks, the skill reads back one task from Jira, runs 9 verification checks (title, parent, reporter, team, labels, components, description, issue type, links), reports discrepancies with severity, proposes fixes, and propagates fixes to all affected tasks

---

## [0.6.0] — 2026-03-30

### Plugin
- Added new skill **diagram-prototyper** — create diagrams, flowcharts, BPMN processes, mind maps, and UI prototypes
- Defined inbound skill chaining: write-concept, brainstorm-features, requirements-creator, product-research, product-analysis can now invoke diagram-prototyper

### Skills changed
| Skill | From | To | Change type |
|-------|------|----|-------------|
| diagram-prototyper | — | 0.6.0 | new skill |

---

## [0.5.0] — 2026-03-27

### Plugin
- Added **Analyze & Improve mode** to `requirements-creator` skill
- Translated `README.md` fully to English

### Skills changed
| Skill | From | To | Change type |
|-------|------|----|-------------|
| requirements-creator | 0.4.0 | 0.5.0 | minor — new Analyze & Improve mode added (A1—A9 workflow) |

---

## [0.4.0] — 2026-03-26

### Plugin
- Added versioning system for skills and plugin: `version` field in all SKILL.md frontmatter
- Added `CHANGELOG.md` (this file)
- Added versioning rules to `references/self-improvement.md`
- Added versioning protocol to `skills/plugin-configurator/SKILL.md` (step 4 — Implement improvement)

### Skills changed
| Skill | From | To | Change type |
|-------|------|----|-------------|
| brainstorm-features | 0.3.0 | 0.4.0 | minor — version field added |
| feature-task-creator | 0.3.0 | 0.4.0 | minor — version field added |
| plugin-configurator | 0.3.0 | 0.4.0 | minor — versioning protocol added |
| product-analysis | 0.3.0 | 0.4.0 | minor — version field added |
| product-research | 0.3.0 | 0.4.0 | minor — version field added |
| requirements-creator | 0.3.0 | 0.4.0 | minor — version field added |
| write-concept | 0.3.0 | 0.4.0 | minor — version field added |

---

## [0.3.0] — 2026-03-25

### Plugin
- Translated all skill instructions and reference files to English
- Output language remains controlled by `user.language` in `local-context.md`

### Skills changed
| Skill | From | To | Change type |
|-------|------|----|-------------|
| brainstorm-features | 0.2.0 | 0.3.0 | minor — full EN translation of workflow instructions |
| feature-task-creator | 0.2.0 | 0.3.0 | minor — full EN translation of workflow instructions |
| plugin-configurator | 0.2.0 | 0.3.0 | minor — full EN translation of all UI strings |
| product-analysis | 0.2.0 | 0.3.0 | minor — full EN translation of workflow instructions |
| product-research | 0.2.0 | 0.3.0 | minor — full EN translation of workflow instructions |
| requirements-creator | 0.2.0 | 0.3.0 | minor — full EN translation, requirements template translated |
| write-concept | 0.2.0 | 0.3.0 | minor — full EN translation of workflow instructions |

---

## [0.2.0] — 2026-03-25

### Plugin
- Added `plugin-configurator` skill with onboarding, update, validate, and view modes
- Added `local-context.md` support (org-specific config, gitignored)
- Added `references/local-context-protocol.md` — auto-trigger and enrichment protocol
- Added `references/self-improvement.md` — self-improvement protocol for all skills
- Added `references/context-schema.md` — full schema for `local-context.md`

### Skills changed
| Skill | From | To | Change type |
|-------|------|----|-------------|
| plugin-configurator | — | 0.2.0 | new skill |
| brainstorm-features | 0.1.0 | 0.2.0 | minor — local-context integration |
| feature-task-creator | 0.1.0 | 0.2.0 | minor — local-context integration |
| product-analysis | 0.1.0 | 0.2.0 | minor — local-context integration |
| product-research | 0.1.0 | 0.2.0 | minor — local-context integration |
| requirements-creator | 0.1.0 | 0.2.0 | minor — local-context integration |
| write-concept | 0.1.0 | 0.2.0 | minor — local-context integration |

---

## [0.1.0] — initial release

### Skills
- brainstorm-features
- feature-task-creator
- product-analysis
- product-research
- requirements-creator
- write-concept
