# flow-walkthrough — design spec

**Date:** 2026-09-10 · **Status:** approved in chat, pending implementation plan · **Target release:** v3.1.0

## 1. Problem and goal

Product managers using Grow PM research a flow today from Figma mockups, dashboards and interviews. They cannot walk the flow in the *real* product the way a customer does — on the phone, in the browser, in the desktop app — and turn that walk into evidence. The goal is a capability that lets any plugin user drive their real product (usually the production build, with no DB or API access) on any surface, record every step with a screenshot, rate the friction, compare surfaces or competitors, and hand the evidence to the skills that already exist (CJM research, requirements, concepts, tasks).

Reference case: Prom buyer app, scenario «створити відгук про товар». A spike on 2026-09-10 proved the mechanics on Claude Cowork: the App Store build of Prom installed from the **Mac App Store** on Apple Silicon and was driven end-to-end with computer-use up to (not including) «Опублікувати».

## 2. Decisions taken (with the user)

| # | Decision | Choice |
|---|---|---|
| D1 | Where it lives | New skill `flow-walkthrough` + shared protocol `references/app-drive-protocol.md` |
| D2 | Surfaces in v1 | Web (browser), desktop apps (computer-use background), iPhone apps on Apple Silicon Mac (computer-use foreground), Android via adb (real phone or an already-running emulator) |
| D3 | Output | Human report **and** machine evidence pack |
| D4 | Competitors | Allowed — same walk on any product; never write or buy in someone else's product |
| D5 | Setup help | Agent-guided `setup` mode with a preflight script, plus the same steps as written docs |
| D6 | Cross-platform | `compare` mode: one scenario × N surfaces or N products → matrix |
| D7 | Screenshots reuse | Every step screenshot is a candidate for `visual-annotation-protocol.md` (marker = step number) in requirements, concepts, tasks |

Out of v1 (listed in CHANGELOG as next): iOS Simulator builds from the mobile team, iPhone Mirroring, installing an Android emulator + system images, video recording, automated accessibility audit.

## 3. Components

### 3.1 Skill `skills/flow-walkthrough/SKILL.md`

Frontmatter description (trigger phrases): UA — «пройди флоу», «пройди шлях покупця в застосунку», «перевір зручність … у застосунку», «порівняй флоу на iOS і web», «налаштуй емулятор/adb для проходу». EN — "walk the flow", "walk through the app as a user", "test this journey in the real app", "compare the flow across platforms", "set up the emulator". Not Figma review (design-bridge), not dashboard analysis (product-analysis), not the CJM pipeline itself (cjm-research — it calls here).

Modes (chosen from the request, confirmed with one AskUserQuestion when ambiguous):

| Mode | Input | Output |
|---|---|---|
| `setup` | target surface(s) | machine readiness table, the missing pieces installed with per-step confirmation, user-only actions listed, smoke test passed |
| `walk` | product, surface, scenario, account, write-boundary | evidence pack + report |
| `compare` | scenario + list of (product, surface) | one evidence pack per run + comparison report |
| `audit` | an existing evidence pack (or runs `walk` first) | friction findings graded against a checklist, recommendations, chaining |

Skill steps:

0. **Step 0 / 0-host** — `local-context-protocol.md`, `host-profiles.md` §3 extended with APP-DRIVE (see 3.2). Report the resolved drive level in one line.
1. **Scope** — product (own or competitor from `product.competitors`), surface, scenario as a numbered goal («залишити відгук на товар із замовлення»), account (test account preferred; the user logs in, the agent never types passwords or OTP), **write boundary** (default: stop before any irreversible production action — publish, pay, send, delete; the user may lift it per run).
2. **Preflight** — per `app-drive-protocol.md` §4: readiness of the driver, overlay utilities to quit, "the Mac will be busy" warning for foreground mode, target app opened and visible, screenshot capture verified by saving one file.
3. **Walk loop** — for each step: intent → action → wait → screenshot → verify the screenshot shows the expected state → log. Silent failures (typing into an unfocused field) are caught by the verify step. Focus stolen by another app → pause and tell the user, never fight for focus. A step that cannot be completed (paywall, purchase needed, network) is logged as a `blocked` step with the reason — it is a finding, not an error.
4. **Findings** — friction per step: `severity` (blocker / major / minor / cosmetic), `heuristic` (Nielsen 1–10 or CJM stage from `cjm-protocol.md`), evidence (step number). Optional enrichment when the Lazyweb MCP is present: one `lazyweb_search` per major+ friction for a real-app reference. Never a report generator call unless the user asks.
5. **Artifacts** — evidence pack (3.3) then report (3.4) through Step T.
6. **Chaining** — offer: brainstorm-features (hypotheses from frictions), requirements-creator (as-is flow strip), cjm-research (stage evidence), decision-log, diagram-prototyper (flow diagram from `steps.yaml`).

### 3.2 Protocol `references/app-drive-protocol.md`

Shared reference consumed by flow-walkthrough, cjm-research, product-research, requirements-creator, task-creator, write-concept, diagram-prototyper.

1. **Capability APP-DRIVE** — added to `host-profiles.md` §1 as the sixth capability: "a tool that can observe and act on a running product". Observed, never asked. Sub-levels, best available wins:
   - `web` — browser tools in the session (per `integration-strategy.md` Step 3 order: dedicated browser MCP → in-app browser → Playwright MCP).
   - `desktop-background` — app-scoped screenshot + click tools that do not take the screen (Cowork `app_*`).
   - `foreground` — full-screen screenshot + click with user consent; the machine is busy for the run.
   - `device` — shell-driven device control: `adb` (Android), `simctl`/simulator tool (iOS builds, v1.1).
   Every level records `measured` vs `assumed` per host in a table inside the protocol; assumed rows say so in the run's `run.yaml`.
2. **Driver table** — surface → driver → how to capture a screenshot to disk → how to tap/type/scroll/back → known limits. Measured on 2026-09-10 for Cowork: iPhone apps on Mac are foreground-only (background window capture fails); transparent overlay windows (e.g. LanguageTool) block clicks — quit them for the run; wheel scroll and drag-swipe both work; typing without real focus is lost silently.
3. **Preflight checklist** — driver ready, overlays quit, account state, write boundary restated, first screenshot saved and re-read from disk.
4. **Step cycle** — the loop of 3.1 step 3 with the verify rule and the pause rule.
5. **Safety** — credentials/OTP are user-only; write boundary; competitor products are read-only; screenshots are internal data (`data-policy.md`): local only, never to external LLMs; prefer test accounts so no personal data lands in screenshots.
6. **Degradation** — no APP-DRIVE: the skill says so in one line and offers the user-driven variant (the user walks, pastes screenshots, the agent logs and audits). No FS: evidence pack delivered in chat + mandatory export. No SHELL: `setup` becomes written instructions with the same checks phrased for the user.

### 3.3 Evidence pack — `~/.grow-pm/walkthroughs/<YYYY-MM-DD>-<product>-<flow-slug>/`

New folder in `persistent-storage.md`. Contents:

- `run.yaml` — product, surface, driver level (+ measured/assumed), host profile, scenario, account type (`own` / `test` / `anonymous`), write boundary, started/finished, verdict (`completed` / `blocked_at:N` / `aborted`), plugin version.
- `steps.yaml` — list of `{n, intent, action, observed, screenshot, friction: [{severity, heuristic, note}], blocked_reason?, elapsed_s}`.
- `steps/NN.png` — one screenshot per step, saved by the driver's own capture method (`screencapture` via SHELL for foreground, tool-native save for browser/app tools); the path is re-read to prove it exists. `save_to_disk` of the Cowork batch tool is not relied on (its paths are not surfaced).
- `findings.md` — the friction list in prose, ready to paste.
- `compare` mode: one folder per run + `compare.yaml` in the first run's folder listing the run ids and the matrix.

### 3.4 Report

`artifact_type: research`, `subtype: walkthrough`, new built-in `builtin://research/walkthrough-v1.md` (the `artifact_type` enum is unchanged; `template-protocol.md` gains the subtype). Sections: scenario and surfaces; step table with the **flow strip** — screenshots with numbered markers per `visual-annotation-protocol.md` (marker = step number, legend = step table); friction findings by severity; comparison matrix (compare mode); recommendations and chaining. Published like product-research output (Confluence space from `product.confluence_space`, or local).

### 3.5 Setup mode and preflight script

`scripts/walkthrough_preflight.sh` (SHELL hosts) prints a table `surface → status → missing → who does it`. Checks: CPU arch (Apple Silicon → iPhone apps on Mac available), Xcode present + `xcode-select` target + simulator runtimes and devices, `adb` present + `adb devices`, `brew` present, browser tool availability is reported from the tool list (not the script). Setup steps per surface, each installation confirmed by the user, user-only items marked: install from App Store, `sudo xcode-select`, enable USB debugging, log in. Ends with the smoke test: open target → save a screenshot → one tap → screenshot shows the change.

### 3.6 Touch points in the repo

`references/host-profiles.md` (§1 row, §4 contour row "Product drive"), `references/integration-strategy.md` (pointer from Step 3), `references/persistent-storage.md` (folder), `references/template-protocol.md` (subtype + built-in), `references/cjm-protocol.md` (enrichment source `walkthrough-local`), `skills/cjm-research`, `skills/product-research`, `skills/requirements-creator`, `skills/task-creator`, `skills/write-concept`, `skills/diagram-prototyper` (one paragraph each: when to call and what to read), `agents/` unchanged, `.claude-plugin/plugin.json` (skill count, description), `README.md`, `CHANGELOG.md`, `AGENTS.md` skill index, `testing/skill_lint.py` (subtype list, new skill), `testing/test-mode.md` checklist, Confluence docs per the existing sync flow after release.

## 4. Testing

- `testing/skill_lint.py` green; host-smoke on Claude Code and Codex CLI.
- Fixture `skills/flow-walkthrough/examples/prom-review-flow.md`: the spike scenario with its expected step list and findings; used to dry-run `walk` (agent reads it, produces a pack from pasted screenshots) and `audit`.
- Preflight script unit-run on this machine: expected rows — Apple Silicon yes, Xcode 26.6 with 0 devices, xcode-select → CLT, adb missing.
- Manual acceptance: one real `walk` on Prom (Mac App Store build) reproducing the spike to the publish step; one `compare` Prom web vs Prom iPhone-on-Mac on the same scenario.

## 5. Spike findings kept as the reference example (Prom, review flow)

Entry to a review exists only from Кабінет (reviews hub with filter «Очікують на оцінку», or the order card «…» menu); the product card and the all-reviews screen have no write CTA. The review form has no star rating — stars appear only in the exit modal «Оціниш товар?», whose «Опублікувати» auto-publishes typed text; the modal shows even for an empty form; a draft is lost silently on close. The orders filter «Очікує на відгук» shows the empty state «Твоя історія замовлень поки що порожня» while the reviews hub lists two items awaiting review. The «Кабінет» tab is hidden behind the top-bar arrow.
