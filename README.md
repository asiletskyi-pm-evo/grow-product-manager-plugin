<p align="center"><img src="assets/logo.png" alt="Grow Product Manager" width="128"></p>

# Grow Product Manager

**Version:** 3.0.1

AI assistant plugin for Product Managers. Integrates with Jira, Confluence, Figma, Tableau, and other tools to streamline product management workflows. Includes a Design Bridge that turns concepts, requirements, research, and hypotheses into brand-themed decks, prototypes, and handoffs with WCAG 2.1 AA a11y gates. All brand specifics (Design System, fonts, tokens, pptx templates) are read from your own `local-context.md` — the plugin ships no hardcoded brand assets.

---

## Overview

**New in v3.0.0** — **One plugin, three hosts: Claude Code / Cowork, Codex CLI and app, ChatGPT** (29 skills, 3 agents, 5 commands, 6 connectors, 2 hooks). Nothing was forked: Codex reads the same `.claude-plugin/` manifests, loads all 29 skills under the same `grow-product-manager:` namespace and registers the same connectors. What changed is how the skills *behave* where a host lacks something. `references/host-profiles.md` defines five observable capabilities — filesystem, shell, subagents, connectors, hooks — and every skill runs **Step 0-host** once, marks them present or absent from the session's own tool list (never from a brand name), and picks the matching mode: `storage_mode: local | connector | session`, sequential in-session checker passes instead of subagents, an in-skill confirmation instead of the write-gate hook. Measured on Codex, not assumed: Codex resolves a bare `references/<file>.md` against the skill's own folder, so every skill and command now opens with a **Path rule**; Codex shares one ≈15k-character budget across every listed skill's description (~190 characters each on a machine with 80 skills), so all 29 descriptions were rewritten with the essence and the neighbour guard inside the first 190 characters — trigger-evals 102/102 on both hosts; migrated commands are routable skills there, so each is guarded as *typed-only*. Packaging: `marketplace.json` `"source": "./"` (Codex ignores the object form; Claude rejects a bare `"."`), `AGENTS.md`, `.codex/agents/*.toml`, portable `${PLUGIN_ROOT}`. Validator checks 12–14 and `testing/host-matrix.md` keep all of it mechanical. Known Codex gaps are documented, not hidden: no plugin agents or hooks, empty-`url` connectors fail in the CLI (the app matches them by name), and updates are a two-command manual step — see **Hosts** below.

**New in v2.6.0** — **Host hooks: a context digest at session start and a human in the loop before writes** (29 skills, 3 agents, 5 commands, 6 connectors, 2 hooks). `hooks/hooks.json` registers two hooks. **SessionStart** (also after `/clear` and compaction) runs `scripts/session_start.py`: it finds `local-context.md` wherever this session can see it — including connected folders under `$HOME/mnt/*/` in hosted sessions, where the shell's home is a sandbox — and injects a `GROW_PM_SESSION` digest (path, versions, `user.language`, products, onboarding state, vault/CJM/team-language flags), so Step 0a of `local-context-protocol.md` becomes a lookup instead of a four-location search; `GROW_PM_CONTEXT_PATH` is exported for Bash. **PreToolUse** on `createJiraIssue` / `editJiraIssue` / `createConfluencePage` / `updateConfluencePage` runs `scripts/write_gate.py`, which answers `ask` for content-bearing writes — the host shows a three-point checklist (gate report in chat, explicit go-ahead, not a sandbox) and waits; metadata-only edits pass. A hook sees only the tool call, never the conversation, so this is deliberately a confirmation, not a judge; `/grow-product-manager:setup --write-gate off` turns it off. Both hooks fail open. Validator check 11 verifies the wiring (events, timeouts, scripts exist and are executable, scripts compile); component counts now include hooks. No skill changed.

**New in v2.5.0** — **Plugin components: connectors, agents, commands** (29 skills, 3 agents, 5 commands, 6 connectors, 2 hooks). Until now everything the plugin needed from the host was described in prose — "look for a tool matching `mcp__*__*Jira*`", "spawn a subagent that must not browse". v2.5.0 moves three of those contracts into the manifest, where the host enforces them. **Connectors:** `.mcp.json` declares the six connectors the skills rely on (`atlassian`, `figma`, `gmail`, `google calendar`, `google drive`, `fireflies`); they appear in the plugin's Connectors tab with a connected state, and `references/integration-strategy.md` gains a *Declared connectors* table (key → connector → observed tool namespace) that replaces the stale `gcal_*`/`gmail_*` patterns. Tableau is deliberately not declared (a local server the user runs). **Agents:** three named subagents whose `tools:` line is the guarantee the protocols only asked for — `artifact-checker` (`tools: Read`; the maker–checker half in `requirements-creator`, `write-concept`, `task-creator`), `debater` (`tools: []`; one per role in Debate Mode), `extractor` (read-only fan-out worker per `subagent-delegation.md`). Each protocol keeps its fallback chain: named agent → `general-purpose` with the same prompt (reported) → inline with the marker. **Commands** (user-only, never auto-routed): `/grow-product-manager:status` (one-screen health: version, context path, vault level, connectors present vs declared), `config validate|view`, `release patch|minor|major`, `glossary-lint`. Validator: four new consistency checks (agents/commands frontmatter, `.mcp.json` ↔ table drift, component counts in the three public descriptions); the org-leak linter and the seeded test now cover `agents/` and `commands/`. Touched: `requirements-creator` v0.13.1, `write-concept` v0.11.1, `task-creator` v0.12.1, `brainstorm-features` v0.10.1, `plugin-configurator` v2.9.2, `release-manager` v0.2.0.

**New in v2.4.1** — **The "no org data" promise, enforced.** An audit found nine shipped lines that named the maintainer's own team as the authority behind a rule (`per <Team> convention`), signed reference examples with a team and a quarter, wrote a schema example in one team's language, or hardcoded an output language where `user.language` exists — all green under every existing check, because a leak that is an ordinary word has no lexical signature, only a position. Those lines are fixed, and three positional checks now catch the class: **`org-signature`**, **`example-locale`** (fenced blocks only — bilingual triggers in prose are the routing surface by design), **`example-keys`**. New **`testing/seeded_leak_test.py`**: ten known-bad lines injected one at a time, the linter must go RED on each — **10/10**, wired into both CI workflows. `testing/Testing-process.md` gains the written rule ("Every example in the plugin is universal") and two DoD items. Touched: `product-reporter` v0.5.2, `knowledge-library` v0.7.1, `plugin-configurator` v2.9.1.

**New in v2.4.0** — **Visual requirements and team language** (stage 2 of the stakeholder-feedback release). New shared `references/visual-annotation-protocol.md`: annotated screenshots where **marker № = requirement №** (a visual index with a legend table, not an illustration) — sourced from user upload / Figma / live browser, rendered locally with Pillow, user-previewed, stored in the project repo, and attached via **Atlassian REST API** (the Rovo MCP ships no attachment tools; token env NAME in config, value never) with browser/manual fallbacks; `diagram-prototyper` v0.10.0 gains a standalone Annotate mode. `knowledge-library` v0.7.0 grows the **team-language contour**: Glossary Build/Manage/Lint + Style Build (terms with variants/avoid + officialese→living `phrases` + a style profile with few-shot fragments), wired into every artifact by **Gate 3 "Team language"** in the artifact quality gate — style preamble before generation, terminology lint after. Consumers: `requirements-creator` v0.13.0 (Step 4.2 visualization), `task-creator` v0.12.0 (Step 8.5 attachments), `write-concept` v0.11.0, `plugin-configurator` v2.9.0 (Terminology & Style + Attachments setup). Trigger-evals: new Group K 100%, B/E/J regression 100%.

**New in v2.3.0** — **Clean artifacts: a quality gate with maker–checker verification**. Stakeholder feedback surfaced two recurring defects in generated artifacts: AI-invented technical content inside business/functional requirements and tasks, and requirements written as paragraph prose instead of lists. New shared `references/artifact-style-gate.md` blocks both: **Gate 1** applies a source test to every technical statement (process parameters stay; AI technical assumptions are prohibited by default and, on explicit request, go into a separate callout-guarded "Технічні рекомендації (AI)" block), **Gate 2** enforces lists-over-prose. The gate is executed by an **independent checker subagent** — the agent that produced the artifact never checks its own work; the checker sees only the draft + sources + checklists, reports findings without rewriting, and critical artifacts (Confluence publish / Jira creation) get two checkers with distinct lenses (form / groundedness). Consumers: `requirements-creator` v0.12.0 (+ thin-core refactor: Analyze & Improve moved to skill-local `analyze-improve-mode.md`), `task-creator` v0.11.0 (batch gate before creation; Step 12 verification switches to maker–checker), `write-concept` v0.10.0, `meeting-processor` v0.13.4 (opt-in). Skill triggers unchanged.

**New in v2.2.0** — **Debate Mode: a role-based adversarial discussion engine**. One agent brainstorming alone approves its own ideas — trade-offs between interest groups go unnoticed and ICE Confidence inflates. Now any evidence-holding skill can convene 3–5 conflicting roles (10-preset card library + custom; the **Skeptic / Risk-officer is always in**) over a numbered evidence pack and debate one contested question in parallel subagent rounds: opening positions → cross-examination → facilitator synthesis (consensus points, live disagreements, position shifts, verdict + confidence, **mandatory minority report**) with ICE Confidence corrections (consensus +1…+2, unresolved skeptic objection −1…−2). New shared `references/debate-protocol.md` carries the engine and guardrails (no facts beyond the pack, no web for debaters, cost cap 4×2 = 8 / hard 12 calls, inline-simulation fallback with an explicit marker); `brainstorm-features` Step 3D is the primary entry; thin Debate hooks land in `product-research`, `cjm-research`, `write-concept`, `decision-log`; the vault gains artifact type #34 `debate` (`Debates/{product}/`); trigger-evals gain Groups I and J. The `brainstorm-features` core stays ≤ 400 lines — Step 3C's CJM workflow moved verbatim to skill-local `cjm-hypotheses-mode.md`.

**New in v2.1.0** — **Audit remediation (v2.0.1 → v2.1.0)**. A full audit of v2.0.0 found 5 critical + 14 major defects that both validators passed green. All are now fixed, and — more importantly — each defect *class* is a blocking linter check, verified by injecting the defect into a repo copy. Highlights: real organization data removed from the shipped example (and the whole repo); two protocol documents that contained themselves twice, halved; `vault-schema.md` declared the single source of truth for vault layout, with `vault-protocol.md` and the Obsidian setup guide conformed to it (they had described three incompatible layouts, and the setup smoke tests could not have passed); 28 of 29 skill frontmatters made valid YAML for external tooling; `experiment-tracker` made reachable by chaining at all; a `design-bridge` handoff can no longer skip its accessibility audit; and CJM health scores now sum to 100% for funnels of any length, not just the 4-stage default. `testing/skill_lint.py` grew from 4 checks to **13**. See the CHANGELOG for the full list.

**New in v2.0.0** — **Wave 3: the People-contour (29 skills)**. The plugin grows a whole new contour — **manager → people → goals → communication → development** — alongside the existing product/data/delivery contour. Six new skills: **`goal-setter`** (SMARTCBP for people / OKR for product, audit + cascade + commitment), **`one-on-one`** (prepare from the profile + analyze into signals & an ARCV follow-up, 1-1 coverage headless), **`performance-review`** (goals + GTD-index + situational-leadership diagnosis into the employer's review template), **`hiring-designer`** (role design — goal letter before the vacancy — + a universal vacancy profile mapped to the employer's HR form), **`offboarding-guide`** (evidence-gated four-meeting algorithm, strictly local), and **`delegation-coach`** (7-levels-of-Appelo audit + S1→S4 hand-off plan). A new **People Context Protocol (Step P)** gives every person a persistent, vault-local profile (D-type, delegation levels, goals, reporting cadence, 1-1 history, GTD-index, signals). Six methodology references distil the frameworks (SMARTCBP, 3T5F, Hersey-Blanchard, 7-levels-of-Appelo, GTD-index, ARCV, CBI, NVC, ROAIP/PRO). **Breaking:** `team-ops-reporter` is **renamed to `product-reporter`** and gains a **goal-report (3T5F)** mode. Existing skills learn the frameworks too — meeting-processor (ARCV follow-ups + 1-1 detection), task-creator (why/what/how + DoD + D-level depth), brainstorm-features (ROI/PRO **and** ICE by default), requirements-creator (ROI/ICE gate), sprint-planning (GTD-index + delegation-aware assignees), focus-advisor (manager-rhythms + "choose one"), quarterly-planning (session/board prep), feedback-triage (SH step), experiment-tracker & decision-log (cost + commitment). People data is the **highest-sensitivity tier** — vault/local only, never Confluence/Jira/external LLMs.

**New in v1.40.0** — **External design toolkit provider**. `design-bridge` becomes the single **routing host** for design/prototype work and can delegate hi-fi screen generation to an **external design toolkit** the user declares in `local-context.md` — keeping the plugin core universal for any company (zero regression when none is configured). New `references/design-toolkit-protocol.md` defines the contract: a `design_toolkits[]` config schema, capability-based routing (core enum `hi-fi-prototype` / `screen-generation` / `ds-tokens` / `figma-write` / `code-first-research` / `design-review` + custom tags), a tier-0 fallback (provider → Figma MCP → Registry → Browser), four entry types (`skill` / `mcp_tool` / `command` / `browser`), a bidirectional delegation contract, and a QA-ownership rule (no double review). `design-bridge` → v0.3.0 adds **Step 0.5** (toolkit routing); `plugin-configurator` gains a **Design Toolkit** registration step; `diagram-prototyper` documents the scope boundary (hi-fi, DS-native generation routes to design-bridge). Every toolkit is user-declared — the repository ships no concrete toolkit.

**New in v1.39.0** — **Harness engineering, wave 3: output evals** (point 1). The plugin could already check *which* skill fired (trigger-evals = trajectory); now it can check *how good the artifact is*. New `testing/output-evals.md` defines rubrics (weighted 0/1/2, pass ≥ threshold, LM-judge against the golden exemplar) for the artifact-producing skills, with runnable `testing/fixtures/` input briefs for `write-concept`, `requirements-creator`, and `cjm-research`. `Testing-process.md` splits stage 3 into **3a (trajectory)** and **3b (output eval)** — a blocker for any changed artifact skill — so quality is gated the way triggering already is. *"Set the bar at the eval, not the demo."*

**New in v1.38.0** — **Harness engineering, wave 2: artifacts carry their verification** (point 4). Specs and PRDs now bake verification in, not bolt it on. `requirements-creator` gains an **Acceptance Criteria** section (testable Given/When/Then, the contract QA and analytics verify against) and, for A/B tests, an explicit **Decision Rule** (ship / iterate / kill, stated before launch so the readout is a lookup, not a debate). `write-concept` PRDs upgrade acceptance criteria to Given/When/Then and add a **Verification & decision rule** block to Success Metrics (how each metric is verified + Definition of Done). Verification moves to the middle of the lifecycle, as the whitepaper prescribes.

**New in v1.37.0** — **Harness engineering, wave 1** (from Google/Kaggle "The New SDLC With Vibe Coding"). Self-improvement now runs a **harness-first diagnosis** — before proposing a fix, the failure is classified by harness layer (instructions / tools / context / guardrails / orchestration / observability) and the fix is routed to the right place, because most agent failures are configuration failures, not model failures. A new `references/harness-map.md` documents the plugin's own harness anatomy and a six-context-type coverage map (thin spot identified: **Examples**). To fill that spot, the three heaviest artifact skills gain on-demand **golden exemplars** (few-shot): `write-concept` (worked PRD), `requirements-creator` (feature-spec with A/B + acceptance criteria), `cjm-research` (period-annotated anomaly report) — each doubling as a future output-eval fixture.

**New in v1.36.0** — **Wave 3 kickoff: three lifecycle skills (23 total)**. `experiment-tracker` closes the loop after the A/B spec — a persistent experiment registry with lifecycle states, stale-test reminders, readouts via product-analysis, and decisions recorded via the new `decision-log` (ADR-style records in vault Decisions/ that finally answer "чому ми вирішили X?"). `feedback-triage` turns raw support-ticket/review streams into a ranked pain map (semantic clustering, frequency × severity × trend vs the previous run's baseline) chaining straight into brainstorm-features. Vault taxonomy grows to 22 types (`feedback-triage`); trigger-evals gain Group H (14 phrases, lifecycle trio vs neighbors).

**New in v1.35.0** — **Monolith refactor complete (2–4/4)**: the three remaining oversized skills slimmed to on-demand cores — `product-analysis` 968 → ~365 lines (analysis engine and the three specialized modes moved to `analysis-engine.md` / `specialized-modes.md`; the Data Integrity Gate stays in the core), `cjm-research` 788 → ~395 (research pipeline Steps 4–11 → `cjm-pipeline.md`; per-mode report formats, publishing, and the automated health-check → `cjm-reports.md`), `knowledge-library` 751 → ~250 (eight mode workflows → `library-workflows.md`; trust scoring, categories, and KL onboarding → `trust-and-categories.md`). All content preserved verbatim; every skill now loads its core plus exactly one reference per mode.

**New in v1.34.0** — **Monolith refactor 1/4: plugin-configurator** slimmed from 1345 to ~180 lines following the planning-suite pattern: the core keeps the mode map, entry conditions, and cross-skill protocols; detailed workflows moved to skill-local references (`onboarding-steps.md` — Steps 1–17 + Planning/Focus setup; `maintenance-modes.md` — RM/Update/Validate/View + Versioning Protocol) loaded on demand. All content preserved verbatim; Planning/Focus setup steps integrated into the onboarding flow (previously dangled after the resources section); a leftover editorial artifact removed. Trigger-evals baseline recorded (A–F 100%, G 95→100 after one label fix).

**New in v1.33.0** — **Focus Advisor complete: `strategy` mode + live "PM Focus Board"**: focus-advisor 0.3.0 ships the third horizon (quarter–year) — 2–4 strategic bets from product goals/missions (pinned source), NPS and funnel trends, research signals, leadership mandates and zone white-spaces, with a mandatory "what we deliberately do NOT do" section in the strategy memo. New `board` mode renders a persistent PM Focus Board (live artifact where supported, static HTML fallback). All three horizons of the original design are now live.

**New in v1.32.0** — **Focus Advisor `tactics` mode**: focus-advisor 0.2.0 adds the sprint-to-quarter horizon — 3–5 tactical focus candidates from roadmap plan-vs-actual pace and drift, backlog staleness (ICE age), features missing prerequisites ahead of next sprints, A/B tests awaiting decisions, capacity/availability and team-event signals. Tactical scoring = ICE + capacity realism + goal alignment; new chains to project-planning `replan` and test readouts; weekly headless tactical brief supported (`mode=tactics headless=true`).

**New in v1.31.0** — **Focus Advisor (20th skill)**: PM attention dispatcher above structure/quarter/sprint — collects context signals (sprint cycle position, calendar meetings needing prep, important unanswered "live" emails, open action items, Jira tails), ranks them, recommends 1–3 daily focuses, and chains execution to the right skill. Headless contract for scheduled morning briefs; mandatory persistence to `~/.grow-pm/focus/` + Vault (`focus-brief`, 21st artifact type). Plugin-configurator 2.4.0 ships a Focus setup onboarding step; trigger-evals gets Group G (attention vs execution).

**New in v1.30.0** — **Roadmap-trio disambiguation + trigger evals**: the three planning skills now carry explicit scope hints in their descriptions (roadmap-architect = structure only, no dates; project-planning = beyond one quarter; quarterly-planning = exactly one quarter), and `testing/trigger-evals.md` ships a 36-phrase routing test set across 6 collision groups with a run protocol and results log. Release-manager 0.1.1: "merging ≠ releasing" guard in Step 6.

**New in v1.29.0** — **Vault coverage complete**: a standard "Save to Vault" step added to the 11 skills that previously never wrote to the Obsidian knowledge graph (requirements-creator, meeting-processor, brainstorm-features, product-research, diagram-prototyper, task-creator, product-reporter, and the 4 Planning Suite skills). Meeting MoMs, requirements, hypotheses, research, diagrams, task breakdowns, ops reports, and roadmaps now accumulate in the vault with wikilinks. Vault schema extended with 4 new artifact types: `diagram`, `task-breakdown`, `ops-report`, `roadmap` (20 types total). Vault stays optional — L0 setups are unaffected.

**New in v1.28.0** — **Release Manager** skill: one guided pipeline to release the plugin itself — version bump across all 4 mandatory places, CHANGELOG entry, README sync, local validation, gated commit/PR/merge, GitHub Release with tag, mirror sync, and post-release verification. Ships with `skills/release-manager/references/release-pitfalls.md` — nine real failure modes (iCloud-evicted git objects, stale locks, token scopes, VPN-only mirrors, protected-branch divergence, CDN cache…) with guards and recovery recipes.

**New in v1.27.0** — **CI validation + trigger disambiguation**: every push/PR to main now runs `testing/validate-consistency.sh` via GitHub Actions (version consistency across manifests/README/CHANGELOG, SKILL.md frontmatter, broken reference paths). Skill descriptions of the CJM trio (cjm-research / product-analysis / brainstorm-features) and the prototype pair (diagram-prototyper / design-bridge) now carry explicit "Do NOT use" routing hints.

**New in v1.26.0** — **Subagent delegation** extended to all specialized modes of `product-analysis` (Post-Release, A/B Test, CJM Funnel): heavy data-acquisition fan-out runs off the main context, with data-policy guardrails and the Data Integrity Gate preserved. See CHANGELOG v1.24.0–v1.26.0 for the full subagent-delegation rollout.

**New in v1.15.0** — **Planning Suite**: four skills on top of product-reporter — `roadmap-architect` (structure: goal → initiative → epic → feature), `project-planning` (multi-quarter forecast, dependencies, critical path), `quarterly-planning` (quarter roadmap with capacity gate and retro), `sprint-planning` (sprint pre-planning: readiness, risks, assignees). Shared references: `planning-core.md`, `capacity-model.md`, `dependency-model.md`, `roadmap-artifacts.md`.

**New in v1.14.0** — **Product Reporter** skill (5 modes): sprint plan, sprint review, quarter review, initiative status, and team-member review — built directly on Jira (custom-field map, status-history throughput, per-Assignee/Developer breakdowns, charts). Output goes to Confluence and/or local md+xlsx (asked each run). Five built-in templates under `templates/built-in/ops-report/`. See `skills/product-reporter/SKILL.md` and CHANGELOG v1.14.0.

**New in v1.13.0** — **Data Integrity Gate** across `cjm-research`, `product-analysis`, and `product-research`. New universal verification gate that catches incomplete-period extrapolation, holiday windows cited as YoY trends, single-source cascading claims, and missing inline period annotation. See [`references/data-integrity-protocol.md`](references/data-integrity-protocol.md) and CHANGELOG v1.13.0.

**New in v1.12.0** — Onboarding has two modes: **Basic** (3-5 min, mandatory fields only — usable immediately for concept/requirements/research/brainstorm/spec) and **Extended** (15-25 min, full setup of CJM, Vault, Templates, Knowledge Library, Teams, full Tableau analytics). A third **Test mode (sandbox)** lets you walk through onboarding without modifying real data — say `dry-run onboarding` any time. See `skills/plugin-configurator/SKILL.md` for the full Step 1 onboarding map.

The Grow Product Manager plugin is a comprehensive AI-powered toolkit designed to accelerate product management workflows. It provides skills for research, analysis, brainstorming, documentation, task creation, and visualization across your entire product lifecycle.

---

## Skills

### 1. CJM Research (v0.7.4)

**Description:** Customer Journey Map (CJM) pipeline orchestrator with 5 specialized modes for analyzing customer experiences and identifying growth opportunities.

**Modes:**
- **Anomalies** — Detect unexpected patterns in customer funnel behavior
- **Hypotheses** — Generate and validate CJM-based growth hypotheses
- **Full** — Complete CJM analysis with all data points and insights
- **Health-Check** — Assess overall funnel health and drop-off zones
- **Comparison** — Compare customer journeys across platforms or segments

**Delegates to:** Product Analysis, Knowledge Library, Product Research, Brainstorm Features

**Outputs:** Funnel impact models, hypothesis validation, risk assessments

**Trigger phrases:** "analyze CJM", "find funnel anomalies", "CJM research", "funnel health check", "compare platforms", "CJM hypotheses"

---

### 2. Product Analysis (v0.12.3)

**Description:** Analyze product data with interactive dashboards, metrics, and reports to find trends and growth opportunities.

**Modes:**
- **Interactive Q&A** — Ask questions about your metrics
- **Full Report** — Comprehensive analysis of all available data
- **Post-Release** — Analyze metrics before and after a feature release
- **A/B Test Results** — Evaluate test outcomes and statistical significance
- **CJM Funnel Analysis** — Analyze customer behavior across funnel stages

**Trigger phrases:** "analyze metrics", "review a dashboard", "find anomalies", "post-release analysis", "analyze A/B test results", "CJM funnel analysis"

---

### 3. Product Research (v0.10.4)

**Description:** Conduct competitive analysis, user research, market research, and UX benchmarking with Knowledge Library integration for data-backed insights.

**Research Types:**
- Competitive analysis and feature comparison
- User research synthesis and insights
- Market trends and opportunity identification
- UX benchmark research against industry standards

**Trigger phrases:** "research competitors", "analyze the market", "competitive analysis", "find market trends", "UX benchmark research"

---

### 4. Brainstorm Features (v0.10.2)

**Description:** Interactive brainstorming for product features and growth opportunities with ICE scoring and CJM hypothesis generation. Hosts Debate mode — a role-based adversarial discussion over an evidence pack (`references/debate-protocol.md`).

**Features:**
- Feature ideation and scoring (Impact, Confidence, Ease)
- CJM Hypotheses mode with funnel impact calculation
- Growth opportunity identification
- Prioritization framework
- Debate mode (Step 3D): 3–5 conflicting roles, parallel rounds, verdict with a mandatory minority report, ICE Confidence correction

**Trigger phrases:** "brainstorm features", "generate hypotheses", "find growth opportunities", "CJM hypotheses", "run a debate", "red team this idea", "проведи дебати"

---

### 5. Write Concept (v0.11.2)

**Description:** Write detailed product concept documents (PRDs) from ideas, problem statements, or research findings.

**Outputs:** Full PRD with objectives, user stories, success metrics, and implementation notes

**Trigger phrases:** "write a concept", "create a PRD"

---

### 6. Requirements Creator (v0.13.2)

**Description:** Create structured feature requirements or analyze and improve existing requirement documents using business analyst expertise.

**Capabilities:**
- Generate detailed requirements from concepts
- Analyze and improve existing specs
- User story generation
- Acceptance criteria definition

**Trigger phrases:** "write requirements", "create feature spec", "review requirements"

---

### 7. Task Creator (v0.12.2)

**Description:** Automatically create Jira tasks and issues from requirements, breaking down work into actionable engineering tasks.

**Capabilities:**
- Parse requirements and decompose into tasks
- Create Jira issues with proper fields and links
- Estimate complexity and effort
- Set up dependencies and sprint planning

**Trigger phrases:** "create tasks for a feature", "create Jira issues"

---

### 8. Diagram & Prototype Creator (v0.10.1)

**Description:** Create diagrams, flowcharts, BPMN processes, mind maps, infographics, and UI prototypes to visualize product concepts.

**Supported Tools:**
- **Mermaid (built-in)** — Fast local generation of flowcharts and diagrams
- **HTML/CSS (built-in)** — Self-contained infographics with inline CSS and SVG charts
- **Google Gemini** — Image generation via browser (Nano Banana mode)
- **ChatGPT** — Image generation via browser (GPT-4o or newer)
- **NotebookLM** — Presentations and mind maps via browser
- **Figma** — Prototypes and design mockups via MCP or browser
- **Draw.io** — XML generation locally or via browser fallback

**Infographic Styles:**
- Data-driven (metrics, KPIs)
- Process/timeline (flows, roadmaps)
- Comparison (feature evaluation, competitive analysis)
- Informational/educational (product overviews)
- Statistical/report (quarterly data, surveys)

**Features:**
- Quality check loop with auto-correction (up to 3 iterations)
- Confidential data generated locally (no external data transmission)
- Skill chaining from other skills
- Publishing to Confluence, Notion, Figma, or local files
- Export as PNG or PDF

**Trigger phrases:** "create a diagram", "draw a flowchart", "BPMN diagram", "make a prototype", "create an infographic", "wireframe", "mockup", "visualize this process", "mind map"

---

### 9. Meeting Processor (v0.13.5)

**Description:** Process meetings from any source to extract action items, decisions, and structured meeting reports with calendar context.

**Meeting Sources:**
- Fireflies.ai recordings
- Other meeting tool recordings
- Uploaded audio/video files
- Transcripts (text or SRT files)
- Pasted meeting notes

**Modes:**
- **Process Mode** — Work with a single meeting:
  - Auto-classify meeting type (grooming, discovery, demo/retro, status, brainstorm)
  - Extract structured notes with type-specific blocks
  - Generate Structured Minutes of Meeting (MoM) or short summary
  
- **Search Mode** — Query across multiple meetings:
  - Chronological synthesis of related discussions
  - Extract decisions and action items across meetings
  - Example: "What did we discuss about feature X last month?"

**Calendar Integration:**
- Google Calendar / Microsoft Calendar context
- Participant list with emails and roles
- Agenda and attached documents
- Presentation materials

**Chaining:** Connects to Task Creator (action items → Jira), Product Research (interview insights), Requirements Creator, Brainstorm Features, and Diagram Prototyper

**Trigger phrases:** "summarize meeting", "meeting notes", "action items"

---

### 10. Plugin Configurator (v2.9.3)

**Description:** Configure the Grow Product Manager plugin for your organization, including products, teams, data sources, storage location, and user preferences.

**Configuration Areas:**
- Storage location selection (Obsidian Vault or custom folder)
- Organization and product settings
- Team structure and roles
- Data source connections (Jira, Confluence, Figma, etc.)
- Knowledge library settings
- CJM funnel configuration
- Obsidian Vault integration
- Output preferences and defaults

**Trigger phrases:** "configure plugin", "set up plugin"

---

### 11. Knowledge Library (v0.7.2)

**Description:** Manage a local, curated library of knowledge sources including articles, benchmarks, research, and competitive intelligence with trust scoring and categorization.

**Features:**
- User-controlled storage location (Obsidian Vault or custom folder)
- Per-product library support
- Trust scoring and source evaluation
- Multi-mode search capability
- Categorization by topic and type
- Service skill for CJM enrichment

**Search Modes:**
- Local library search
- Confluence integration
- Google Drive integration
- Baymard (UX benchmarking database)
- Internet search

**Trigger phrases:** "add source", "search knowledge", "import sources", "show library", "what sources do we have on [topic]"

---

### 12. Template Library (v0.2.4)

**Description:** Manage a multilingual library of artifact templates (concepts, requirements, research, CJM, epics, tasks, meeting notes, presentations). Templates are stored in your Obsidian vault or custom folder, scoped per-product, and consumed automatically by other skills through the Step T — Template Resolution protocol.

**Features:**
- Three-tier scope: built-in → user-global → product-specific (with inheritance)
- Single-file multilingual storage (`<!-- lang:uk --> ... <!-- /lang:uk -->` blocks)
- Registry-backed resolution with scoring (scope, subtype, language, usage_count)
- 11 actions: list, show, add, clone, update, delete, restore, import, export, validate, rebuild-registry
- Three-tier backup: per-template archive, pack backups, manual backup/restore
- Ships with 24 built-in templates in Ukrainian + English (9 original + 3 presentation templates (v1.10.0) + 5 ops-report templates (v1.14.0) + 7 People templates (v2.0.0))

**Trigger phrases:** "manage templates", "add template", "list templates", "template library", "clone template", "import templates", "restore template"

---

### 13. Design Bridge (v0.4.2) — brand-agnostic since v1.11.0

**Description:** Orchestrator skill that turns concepts, requirements, research, and hypotheses into brand-themed design deliverables (decks, prototypes, handoffs, research enrichment). Invoked either directly ("create deck from concept", "build prototype", "run design handoff") or as an optional **Step D** hook from other skills (write-concept, requirements-creator, brainstorm-features, product-research).

**Intents:**
- **deck** — render a Google Slides-compatible `.pptx` (10×5.625") from the base template you configure in `local-context.md` (`product.base_pptx`). 4 subtypes: feature (10 slides), research-highlights (10 slides), ab-test-readout (6 slides), release-readout (7 slides)
- **prototype** — lo-fi / mid-fi / hi-fi prototype brief for Figma
- **handoff** — developer-ready handoff spec (tokens, components, states, responsive breakpoints) with WCAG 2.1 AA a11y audit as blocker
- **research-enrichment** — pull UI screenshots, competitor visuals, or DS references to augment research

**Design plugin integration:** hooks 6 design skills (research-synthesis, ux-copy, design-critique, design-system, accessibility-review, design-handoff) via optional delegation, plus Figma MCP for DS sync. Your Figma DS `fileKey` lives in `local-context.md` → `product.figma.ds_file_key`.

**Brand configuration (from `local-context.md`):**
- `product.brand.primary`, `product.brand.dark`, `product.brand.font_primary`, `product.brand.font_display`
- `product.design_system_spec` — path to your DS token yaml
- `product.pptx_theme` — path to your pptx theme yaml
- `product.base_pptx` — path to your base pptx template
- Canvas defaults to 10×5.625" (Google Slides 16:9)

**A11y gates (WCAG 2.1 AA):** contrast 4.5:1 normal / 3.0:1 large, 44×44 touch targets, keyboard nav, screen-reader labels, motion controls. Handoff intent has a11y as blocker; deck intent has contrast as blocker + warnings for the rest.

**Trigger phrases:** "create deck", "design handoff", "build prototype", "research enrichment", "apply brand to deck", "run a11y audit"

---

### 14. Product Reporter (v0.5.3) — renamed from Team Ops Reporter in v2.0.0

**Description:** Operational team reports from Jira. Pulls issues, processes them in Python (aggregations, Story Points, carried-vs-new, per-Assignee/Developer, changelog-based throughput), renders from a template, and offers charts.

**Modes:**
- **sprint-plan** — directions → features → tasks, summary (total / carried / new / SP), per-Assignee and per-Developer distribution, key-focus table
- **sprint-review** — closed tasks (Done incl. `Ready`), releases by stream (your `product.release_streams` — typically app / web UI / backend / services), flags ON/OFF, task list, closed-per-member
- **quarter-review** — plan vs actual by direction, epics/features fully closed, releases (fetched per month — full-quarter JQL times out)
- **initiative-status** — mission/epic/feature % done, status breakdown, per sub-feature, blockers (Flagged / On hold / blocked-by)
- **member-review** — role-aware: closed / SP / passed-to-test (`status CHANGED TO "Ready for test" BY <member>`) / passed-to-review / tested, plus dynamics across days/weeks/sprints/months/quarters/years
- **goal-report** — 3T5F goal report for a person or direction (build or audit); People-data — vault/local only, never auto-published

**Output:** asked each run — Confluence (your space) and/or local `md` + `xlsx`. Visualizations are proposed (burndown, SP dynamics, status donut, load distribution) and built on accept. Built-in templates live in `templates/built-in/ops-report/`; custom ones via Template Library (`artifact_type: ops-report`).

**Trigger phrases:** "sprint plan/review report", "quarter results", "epic/feature/mission status", "how much did <person> close this period", "team ops report", "report on releases / flags / story points"

---

### 15. Roadmap Architect (v0.2.4) — Planning Suite

**Description:** Maintains the canonical structure of work — maps missions/goals → initiatives → epics → features, enforces labeling (labels, names, links), finds gaps, and generates the roadmap tree.

**Modes:** audit / map / tree / onboard

**Trigger phrases:** "tidy up the structure", "label epics/features", "find labeling gaps", "build the roadmap tree", "link an epic to a goal"

---

### 16. Project Planning (v0.2.4) — Planning Suite

**Description:** Plans and forecasts delivery of a project/mission/initiative beyond a single quarter — estimates the total volume of epics/features, builds a dependency graph with critical path, computes duration under a given team allocation %, and lays out a multi-quarter roadmap with rolling-reforecast.

**Modes:** forecast / sequence / roadmap / whatif / replan

**Trigger phrases:** "how long will the project take", "project roadmap", "epic sequence", "feature dependencies", "critical path", "replan the project"

---

### 17. Quarterly Planning (v0.3.4) — Planning Suite

**Description:** Builds a quarterly roadmap, reviews the previous quarter's delivery (plan-vs-actual), and stress-tests the plan against team capacity.

**Modes:** retro / plan / full / refresh

**Trigger phrases:** "build a quarterly roadmap", "quarterly planning", "plan-vs-actual for the quarter", "quarter retro", "is the quarterly plan realistic"

---

### 18. Sprint Planning (v0.3.3) — Planning Suite

**Description:** Sprint pre-planning: derives focuses from the quarterly roadmap, highlights what's READY to pull (dependencies cleared), catches work-sequence violations, gathers per-member capacity, analyzes carryover risk, suggests assignees, and fills the sprint to capacity.

**Modes:** groom / plan / review / forecast

**Trigger phrases:** "plan the sprint", "sprint pre-planning", "what can we pull into sprint N", "what's ready from the backlog", "who takes the tasks"

**Planning Suite shared references:** `planning-core.md`, `capacity-model.md`, `dependency-model.md`, `roadmap-artifacts.md`, plus the shared Jira plumbing in `references/jira-data-protocol.md` (reused from product-reporter — complements reporting, does not duplicate it).

---

### 19. Release Manager (v0.2.2) — NEW in v1.28.0

**Description:** Releases the plugin repository itself — one guided pipeline from "changes are ready" to "both remotes tagged, Release published, docs consistent". Every irreversible step (commit, push, merge, publish) is user-gated.

**Pipeline:** pre-flight guards (iCloud materialization, stale locks, clean tree) → scope & semver decision → bump in the 4 mandatory places (plugin.json, marketplace.json, README, CHANGELOG) → local `validate-consistency.sh` run → gated commit/push → PR → merge → GitHub Release with tag → mirror sync → post-release verification, optional Confluence changelog update, and vault release record.

**Built-in pitfall guide:** `skills/release-manager/references/release-pitfalls.md` — nine real failure modes with guards and recovery recipes (P1 iCloud-evicted git objects, P4 token without workflow scope, P6 diverged protected mirror, P7 stale raw CDN, and more).

**Generic by design:** works for any Claude plugin repo; org specifics (mirrors, VPN hosts, Confluence page) come from `local-context.md` → `plugin_release`.

**Trigger phrases:** "release the plugin", "prepare a release", "bump plugin version", "ship vX.Y.Z", "cut a release"

---

### 20. Focus Advisor (v0.5.1) — NEW in v1.31.0, complete in v1.33.0

**Description:** PM attention dispatcher — the 4th height of the suite, above structure/quarter/sprint. Scans the PM's context (sprint cycle position, calendar meetings needing preparation, important unanswered emails, open action items from recent meetings, Jira tails), ranks the signals, and recommends 1–3 focuses with reasons, cost of delay, and a chained next step. Recommends and chains — never executes another skill's work; the PM decides.

**Full scope (v0.3):** all three horizons — `now` (daily focus), `tactics` (sprint-to-quarter: roadmap drift, stale backlog, A/B decisions, capacity and team events), `strategy` (quarter-to-year: 2–4 bets aligned to product goals/missions with a mandatory exclusions section) — plus `journal`, `auto` routing, `board` (live PM Focus Board with static fallback), and a headless contract for scheduled briefs (daily `now`, weekly `tactics`, quarterly `strategy`).

**Key mechanics:** deterministic ritual calendar (`focus-cadence.md`: "2nd Monday of the sprint → pre-planning"), signal registry with compact packets and TTL cache (`focus-signals.md`), two-stage "live letters" mail filter (automation never becomes a signal), meeting-prep detector with analytical-slice/deck chains, optional metrics health-check chain to product-analysis / cjm-research. All briefs persist to `~/.grow-pm/focus/` + Vault mirror (mandatory Step 7).

**Trigger phrases:** "на чому сфокусуватись", "що мені робити зараз", "фокус дня", "розбери мою пошту і календар", "daily focus", "morning brief"

---

### 21. Experiment Tracker (v0.2.4) — NEW in v1.36.0

**Description:** Owns the experiment lifecycle the pipeline used to drop after the A/B spec: `proposed → specced → running → awaiting-readout → decided`, with a persistent registry (`~/.grow-pm/experiments/registry.yaml` + vault mirror) and stale-test reminders (overdue runs, pending readouts, idle high-ICE hypotheses).

**Modes:** status (board by lifecycle state) / register / start (flag, platforms, split, dates) / readout (chains product-analysis A/B mode — verdicts only come from there) / decide (chains decision-log) / stale (also the weekly headless payload).

**Trigger phrases:** "які тести зараз біжать", "зафіксуй запуск тесту", "які тести чекають рішення", "нагадай про завислі тести", "experiment status"

---

### 22. Decision Log (v0.2.5) — NEW in v1.36.0

**Description:** ADR-style records of key product decisions in the vault `Decisions/` area — context, options considered, decision, rationale, consequences, evidence links. Answers "чому ми вирішили X?" from the accumulated log; supersede-flow preserves history.

**Modes:** log (default; also invoked by meeting-processor, experiment-tracker, planning skills) / search / revisit.

**Trigger phrases:** "зафіксуй рішення", "чому ми вирішили…", "покажи рішення по…", "журнал рішень", "log this decision"

---

### 23. Feedback Triage (v0.2.3) — NEW in v1.36.0

**Description:** Turns a raw feedback stream (support tickets, complaints, reviews, Q&A, NPS verbatims) into a ranked pain map: semantic theme clustering, `frequency × severity × trend` scoring, new/growing/declining theme detection against the previous run's baseline, and hypothesis seeds for brainstorm-features. Feedback text never leaves the session; PII is masked in verbatims.

**Pipeline:** intake (files / GDrive / Confluence / pasted, subagent fan-out) → Python normalize + coverage gate → cluster → score → report (Step T template) → chains → vault save (`feedback-triage` type, 22nd — the baseline for next run's trends).

**Trigger phrases:** "розбери відгуки/скарги", "тріаж фідбеку", "що болить покупцям/продавцям", "кластеризуй support-тікети", "топ проблем за місяць"

---

## People-контур (People Contour) — NEW in v2.0.0

The second contour of the plugin: **manager → people → goals → communication → development**. These six skills share the **People Context Protocol (Step P)** — a persistent, **vault-local** profile per team member (situational-leadership D-type, 7-levels delegation, active goals, reporting cadence, 1-1 history, GTD-index trend, motivation/career signals). Person data is the **highest-sensitivity tier**: it lives in the vault `People/` area (or `~/.grow-pm/people/`) and is **never** published to Confluence/Jira or sent to external LLMs. Methodology lives in `references/goal-frameworks.md`, `people-frameworks.md`, `reporting-3t5f.md`, `communication-frameworks.md`, `roi-frameworks.md`, and `people-context-protocol.md`.

### 24. Goal Setter (v0.1.3) — NEW in v2.0.0

**Description:** Formulates and audits goals — the foundation of the People-contour. Picks the methodology (**SMARTCBP** for personal goals, **OKR** for product/direction), drafts 2–3 variants or audits a draft against the 8 SMARTCBP checks, cascades Mission→direction→team→person, drives goals to **commitment** (Tell and Sell), and records them on the person's profile. Pulls the Comparable baseline via product-reporter/Tableau.

**Modes:** formulate (default) / audit (8-check before→after table) / cascade / goal-letter.

**Trigger phrases:** "постав ціль", "проведи аудит цілі", "лист цілей", "каскад цілей", "OKR на квартал", "set a goal", "audit this goal"

### 25. One-on-One (v0.1.3) — NEW in v2.0.0

**Description:** Prepares and analyzes 1-1 meetings — *for the person, about the person* (feedback/growth/trust), not tasks/status. Prepare builds the agenda from the profile (6 stages + seven "how" questions + NVC feedback drafts); Analyze turns a Fireflies transcript/notes into signals (motivation, burnout, career) + a manager-written **ARCV** follow-up + a profile update. Headless coverage: who hasn't been "touched" in > N weeks.

**Modes:** prepare (default) / analyze / coverage (headless). meeting-processor detects a 1-1 and redirects here.

**Trigger phrases:** "підготуватись до 1-1", "розбери 1-1", "з ким давно не було 1-1", "нотатки 1-1", "prepare for a 1-1"

### 26. Performance Review (v0.1.2) — NEW in v2.0.0

**Description:** Reviews a team member on the People-contour's coordinates — goal achievement (3T5F Forecast QA), GTD-index, Hersey-Blanchard diagnosis (D-type → style + delegation level), and 1-1 signals — rendered into the employer's standard review template (past-period feedback + a 6–12-month SMARTCBP plan). Ends with one recommendation: development / style change / yellow card / promotion. Strictly local.

**Trigger phrases:** "провести перформанс-ревʼю", "оцінити співробітника", "піврічне ревʼю", "план розвитку для…", "is it time to promote"

### 27. Hiring Designer (v0.1.2) — NEW in v2.0.0

**Description:** Designs the role before the vacancy — the **goal letter** (SMARTCBP on 3/6/12 months) comes first, the offer = goals + conditions. Produces a **universal vacancy profile** (Request / Role goals / Description / Conditions / Selection process) mapped onto the employer's HR-form fields, plus killer questions (past-experience, numeric + If/Then), a candidate-documents checklist, and a **goal × experience** evaluation table. On hire, creates the new person's profile (curator, S1, probation = offer goals).

**Trigger phrases:** "відкрити вакансію", "спроєктувати посаду", "профіль вакансії", "вітальні запитання", "оцінити кандидатів", "draft an offer"

### 28. Offboarding Guide (v0.1.2) — NEW in v2.0.0

**Description:** Guides parting ways with an underperformer — respectfully, on evidence. Gates on an **evidence base** (goals + reports; if absent → set them first), diagnoses "can't" vs "doesn't want", and runs the **four-meeting algorithm** (critical issues → measurable probation → results → sustainability), each with an ARCV follow-up, plus the dismissal script and a neutral team message. Strictly local; immediate dismissal only for theft/unlawful/ethics.

**Trigger phrases:** "допоможи звільнити", "офбординг", "випробувальний термін через недосягнення", "розмова про звільнення", "PIP"

### 29. Delegation Coach (v0.1.3) — NEW in v2.0.0

**Description:** Audits the PM's operational load against the **7 levels of Appelo** (real delegation starts at level 5), builds the audit table (activity / current level / candidate / target / blocker), picks delegates from profiles (D-type, GTD-index — levels 5–7 only for consistently high GTD), and lays out the **S1→S4** transfer plan with dates. Computes hiring/delegation ROI when "no one to delegate to". Chains from focus-advisor when it sees PM overload.

**Trigger phrases:** "аудит делегування", "що можна делегувати", "я перевантажений операційкою", "рівні делегування", "план передачі"

---

## Skills Summary

| Skill | Version | Description |
|-------|---------|-------------|
| CJM Research | v0.7.4 | Customer Journey Map analysis and hypothesis validation |
| Product Analysis | v0.12.3 | Analyze metrics, dashboards, and A/B test results |
| Product Research | v0.10.4 | Competitive analysis, user research, market trends, UX benchmarking |
| Brainstorm Features | v0.10.2 | Interactive feature ideation with ICE scoring + Debate mode (role-based adversarial discussion) |
| Write Concept | v0.11.2 | Write product concept documents (PRDs) |
| Requirements Creator | v0.13.2 | Create and analyze feature requirements |
| Task Creator | v0.12.2 | Create Jira tasks from requirements |
| Diagram & Prototype Creator | v0.10.1 | Visualize concepts with diagrams, prototypes, infographics |
| Meeting Processor | v0.13.5 | Process meetings and extract action items |
| Plugin Configurator | v2.9.3 | Configure plugin for your organization |
| Knowledge Library | v0.7.2 | Manage curated knowledge sources |
| Template Library | v0.2.4 | Manage multilingual artifact templates with per-product scope |
| Design Bridge | v0.4.2 | Orchestrate brand-themed decks, prototypes, handoffs, and research enrichment (brand config in `local-context.md`) |
| Product Reporter | v0.5.3 | Operational Jira reports (sprint plan/review, quarter review, initiative status, member review) + goal-report (3T5F) mode — renamed from team-ops-reporter |
| Roadmap Architect | v0.2.4 | Canonical work structure: goal → initiative → epic → feature, labeling, gaps, roadmap tree |
| Project Planning | v0.2.4 | Multi-quarter delivery forecast: scope, dependencies, critical path, rolling-reforecast |
| Quarterly Planning | v0.3.4 | Quarterly roadmap with capacity gate and plan-vs-actual retro |
| Sprint Planning | v0.3.3 | Sprint pre-planning: readiness, sequence violations, carryover risk, assignees |
| Release Manager | v0.2.2 | Release the plugin repo: bump → validate → PR → Release → mirror sync, with pitfall guards |
| Focus Advisor | v0.5.1 | PM attention dispatcher: daily / tactical / strategic focus briefs + live Focus Board; signals from calendar, mail, meetings, Jira, roadmap, goals; chains to executing skills |
| Experiment Tracker | v0.2.4 | Experiment lifecycle registry: proposed → running → readout → decided, stale reminders, chains to product-analysis and decision-log |
| Decision Log | v0.2.5 | ADR-style product decision records in vault Decisions/: log, search ("why did we…"), supersede |
| Feedback Triage | v0.2.3 | Feedback stream → clustered themes with frequency × severity × trend scoring, pain ranking, hypothesis seeds + SH task-formulation step |
| Goal Setter | v0.1.3 | Set/audit goals — SMARTCBP (people) / OKR (product), cascade, Tell-and-Sell commitment |
| One-on-One | v0.1.3 | Prepare & analyze 1-1s — agenda from profile, signals + ARCV follow-up, coverage headless |
| Performance Review | v0.1.2 | Review a person on goals + GTD-index + D-type, into the employer's review template |
| Hiring Designer | v0.1.2 | Role design (goal letter first) + universal vacancy profile mapped to the employer HR form |
| Offboarding Guide | v0.1.2 | Evidence-gated four-meeting offboarding, strictly local |
| Delegation Coach | v0.1.3 | 7-levels-of-Appelo audit + S1→S4 hand-off plan |

---

## Obsidian Vault Integration (Optional)

The plugin can optionally integrate with [Obsidian](https://obsidian.md/) to create a persistent knowledge graph that accumulates artifacts over time and improves skill results.

### What it does
- Saves results of every skill (research, concepts, requirements, analyses, meetings, decisions) as structured .md files in your Obsidian Vault
- Links related artifacts with wikilinks (research → concept → requirements → A/B results)
- Searches your accumulated knowledge before starting new tasks to provide historical context
- Tracks hypothesis lifecycle: proposed → testing → validated/rejected
- Auto-generates Maps of Content (Dashboard, Product MOC, Timeline) for navigation

### Three-level operation
| Level | Condition | Capabilities |
|-------|-----------|-------------|
| L0 | No vault configured | Plugin works as before, no vault features |
| L1 | Vault path configured | Read/write artifacts, file-based search |
| L2 | Vault + Obsidian MCP | L1 + full-text search, graph traversal, backlinks |

### Multi-vault support
Configure one default vault for all products or separate vaults per product.

### Setup
Run Plugin Configurator → Obsidian Vault step, or say "connect Obsidian Vault".

---

## Persistent Data Storage

All user data is stored in a **user-controlled location** — either your Obsidian Vault (recommended) or a custom folder you choose during setup.

**How it works:**
- `~/.grow-pm/` contains only a pointer file (`.storage-pointer.yaml`) that tells the plugin where your actual data lives
- Two storage modes: **Vault** (Obsidian vault = primary storage) or **Custom** (user-chosen folder)
- When Obsidian is configured, the vault IS the primary storage — no separate copy needed
- Data persists across plugin uninstalls, reinstalls, and updates

**Storage structure (at your chosen location):**

```
<your-storage-location>/
├── local-context.md           # Plugin configuration
├── knowledge-library/         # Curated knowledge sources
│   ├── sources.md             # Source registry with trust scores
│   ├── articles/              # Imported articles
│   ├── benchmarks/            # Industry benchmarks
│   └── competitive/           # Competitor intelligence
└── Templates/                 # Multilingual artifact templates
    ├── _registry.json         # Template index with scoring metadata
    ├── _backups/              # Pack backups (last 5 before bulk ops)
    ├── _archive/              # Per-template version history (last 10)
    ├── built-in/              # Templates shipped with plugin
    ├── user/                  # User-global templates (all products)
    └── product/<product_id>/  # Product-scoped overrides
```

**Key Features:**
- User chooses storage location during onboarding (Step 0)
- Per-product Knowledge Library support
- Pointer-based resolution with recovery flow
- Change storage location at any time via Plugin Configurator
- Automatic backups before migrations
- Schema versioning for data compatibility

---

## Multilingual Artifact Templates

The plugin ships with a built-in template library that every skill uses to produce structured, consistent artifacts — concepts, requirements, research reports, CJM analyses, epics, tasks, meeting notes, presentation outlines, and operational team reports (sprint/quarter/initiative/member). Templates are multilingual (all languages live in a single `.md` file), scoped per product, and resolved automatically with user opt-in.

### How templates are used

When you invoke a skill that produces a deliverable (e.g., `write-concept`, `requirements-creator`, `product-research`, `cjm-research`, `task-creator`, `product-analysis` in report mode, `diagram-prototyper` for decks, `meeting-processor` for MoMs, `brainstorm-features` when saving, `product-reporter` for ops reports), the skill runs **Step T — Template Resolution** before starting the workflow. Step T:

1. Reads your `templates.preference` (`auto`, `always_ask`, or `smart` — default `smart`).
2. Queries the template registry for candidates matching the artifact type, subtype, current product, and your language.
3. Scores candidates by scope (+5 product-specific, +3 user-global, +1 built-in), subtype match, language match, and usage count.
4. Either auto-picks the top candidate, asks you to choose, or silently uses it — based on your preference.
5. Uses the template as the artifact skeleton, filling in variables as the workflow progresses.
6. Tags the saved artifact with `<!-- template: {template_id}@{version} -->` for traceability.

### Three-tier scope

| Scope | Location | Applies to |
|-------|----------|-----------|
| **built-in** | `Templates/built-in/` | All products (shipped with plugin, read-only) |
| **user-global** | `Templates/user/` | All products in your library (overrides built-in) |
| **product-specific** | `Templates/product/<product_id>/` | One product only (overrides user-global + built-in) |

### Multilingual single-file format

Every template is a single `.md` file with one YAML frontmatter block and one or more language blocks delimited by HTML comments (Obsidian-compatible):

```markdown
---
id: concept-builtin-default
version: 1.0.0
artifact_type: concept
subtype: default
scope: built-in
languages: [en]
variables: [feature_name, problem_statement, ...]
---

<!-- lang:en -->
# Concept: {{feature_name}}
## Problem
{{problem_statement}}
...
<!-- /lang:en -->

<!-- Add additional languages as needed, e.g. <!-- lang:es --> ... <!-- /lang:es --> -->
```

### Built-in templates (shipped in v1.9.0–v2.0.0)

24 seed templates; localize via additional `<!-- lang:xx -->` blocks:

- `concept/default-v1` — PRD skeleton
- `requirements/default-v1` — general feature requirements
- `requirements/ab-test-v1` — A/B test spec
- `research/competitive-v1` — competitive analysis + SWOT
- `research/user-research-v1` — user research synthesis
- `cjm/funnel-v1` — CJM funnel analysis with ICE table
- `epic/default-v1` — Jira epic description
- `task/default-v1` — Jira task with DoD and AC
- `presentation/feature-v1` — 10-slide feature deck outline
- `presentation/research-highlights-v1` — 10-slide research-highlights deck (**new in v1.10.0**)
- `presentation/ab-test-readout-v1` — 6-slide A/B-test readout deck (**new in v1.10.0**)
- `presentation/release-readout-v1` — 7-slide release / sprint readout deck (**new in v1.10.0**)
- `ops-report/sprint-plan-v1` — sprint plan report (**new in v1.14.0**)
- `ops-report/sprint-review-v1` — sprint review report (**new in v1.14.0**)
- `ops-report/quarter-review-v1` — quarter plan-vs-actual report (**new in v1.14.0**)
- `ops-report/initiative-status-v1` — mission/epic/feature status report (**new in v1.14.0**)
- `ops-report/member-review-v1` — team-member review report (**new in v1.14.0**)
- `goal-letter/default-v1` — SMARTCBP goal letter for a person (**new in v2.0.0**)
- `report-3t5f/default-v1` — 3T5F goal report (**new in v2.0.0**)
- `one-on-one-notes/default-v1` — 1-1 notes with signals (**new in v2.0.0**)
- `followup-arcv/default-v1` — ARCV follow-up after a meeting or 1-1 (**new in v2.0.0**)
- `vacancy-profile/default-v1` — universal vacancy profile (**new in v2.0.0**)
- `performance-review/default-v1` — structured performance review (**new in v2.0.0**)
- `offboarding-plan/default-v1` — four-meeting offboarding plan (**new in v2.0.0**)

### Managing your library

The **Template Library** skill provides 11 actions: `list`, `show`, `add`, `clone`, `update`, `delete`, `restore`, `import`, `export`, `validate`, `rebuild-registry`. Trigger with phrases like "add template", "list templates", "clone template", "restore template", etc.

### Backup protection

Three-tier backup system to prevent data loss:

1. **Per-template archive** — every template edit saves the previous version (last 10 versions kept per template)
2. **Pack backup** — before bulk operations (import, bulk delete, migration), the whole library is snapshotted (last 5 kept)
3. **Manual backup/restore** — trigger at any time via the Template Library skill

---

## Design Bridge — Brand Integration (v1.11.0)

The plugin ships with a first-class integration with Claude's Design plugin, fronted by the `design-bridge` skill. Four upstream skills gain an optional **Step D** hook that offers to hand off results to design-bridge:

| Upstream skill | Design Bridge offers |
|----------------|----------------------|
| `write-concept` | deck (feature) or prototype (lo-fi / mid-fi) |
| `requirements-creator` | handoff (a11y audit blocker) or prototype (hi-fi) or deck |
| `brainstorm-features` | lo-fi prototype for top-1 hypothesis, or brainstorm readout deck |
| `product-research` | research-highlights deck or research-enrichment (screenshots, DS refs) |

### Bring-your-own brand

All brand specifics live **outside this repo** in your own `local-context.md`. The plugin reads:

- `product.figma.ds_file_key` — Figma `fileKey` of your brand's Design System file
- `product.design_system_spec` — path to your DS tokens yaml (colors, typography, components, contrast pairs)
- `product.pptx_theme` — path to your pptx theme yaml (logical layouts → real layouts, scales, palette)
- `product.base_pptx` — path to your base pptx template (Google Slides–compatible 10×5.625" recommended)
- `product.brand.primary`, `product.brand.dark`, `product.brand.font_primary`, `product.brand.font_display` — fallback tokens when the DS yaml is unavailable or partial

See `local-context.example.md` → **Design System** section for the full schema. If no brand config is set, design-bridge falls back to a neutral default (dark text on white, 4.5:1 contrast).

### A11y gates

All design deliverables pass WCAG 2.1 AA QA before publish (see `skills/design-bridge/references/a11y-checklist.md`). Blocker rules by intent:

| Intent | A11y scope |
|--------|------------|
| deck | contrast on primary text + CTA is blocker; rest = warnings |
| prototype (lo-fi) | contrast + touch targets = warnings only |
| prototype (mid-fi / hi-fi) | full WCAG 2.1 AA blocker |
| handoff | full WCAG 2.1 AA + AAA stretches = blocker |
| research-enrichment | not audited |

---

## Plugin Components (since v2.5.0; hooks since v2.6.0)

Besides skills, the plugin ships four kinds of host-level components. They are declared in files the host parses, not described in prose — which is the point: the host enforces them.

**Connectors — `.mcp.json` (6).** The connectors the skills rely on: `atlassian`, `figma` (matched to your existing connection by URL), `gmail`, `google calendar`, `google drive`, `fireflies` (matched by name). Open the plugin → **Connectors** to see which are connected; a skill never searches the registry for a declared connector, it tells you which tab to connect it in. **Tableau is not declared** — it is a local MCP server you run yourself (see the Setup Guide); the skills detect it by pattern. The mapping key → connector → tool namespace lives in `references/integration-strategy.md` → *Declared connectors*.

**Agents — `agents/` (3).** Named subagents with an enforced tool set:

| Agent | Tools | Used by | Why it is an agent and not a prompt |
|---|---|---|---|
| `artifact-checker` | `Read` only | `requirements-creator`, `write-concept`, `task-creator`, `meeting-processor` (opt-in) | The checker must not see the maker's context and must not browse or write — `tools:` makes that a host rule |
| `debater` | none (`tools: []`) | `brainstorm-features` Step 3D and every skill that chains to Debate Mode | "No web, no vault, no files" is the protocol's core guardrail |
| `extractor` | `Read, Glob, Grep` | fan-out steps in 8 skills (`references/subagent-delegation.md`) | Read-only by definition — safe under `data-policy.md` |

Every protocol keeps a fallback chain (named agent → `general-purpose` with the same prompt, reported → sequential in-session passes with a role reset, reported → inline with the reduced-independence marker), so nothing breaks in a host without plugin agents. Codex does not load `agents/*.md`; `.codex/agents/*.toml` ports the three for manual use there, generated from these files (check 14 keeps them paired).

**Commands — `commands/` (5).** Service entry points that are **user-only** (`disable-model-invocation: true`) — the model never routes a conversation into them, which also keeps them out of trigger collisions. On Codex, which migrates commands into routable skills, the same guarantee comes from each description opening with *"Typed command … only"* (validator check 13, trigger-evals L):

| Command | Arguments | Does |
|---|---|---|
| `/grow-product-manager:status` | `[--verbose]` | One-screen health: plugin version, where `local-context.md` was found and its schema version, vault level, declared connectors vs tools present in this session, deferred onboarding steps |
| `/grow-product-manager:config` | `validate \| view` | Straight into `plugin-configurator`'s Validate / View mode |
| `/grow-product-manager:release` | `patch \| minor \| major` | `release-manager` with the bump class pre-answered — for the plugin repo only |
| `/grow-product-manager:glossary-lint` | `[file]` | Gate 3 team-language lint over a file or pasted text, standalone |
| `/grow-product-manager:setup` | `--show \| --write-gate on\|off` | Host-level toggles (the write gate) and whether the hooks environment is wired in this session |

**Hooks — `hooks/hooks.json` (2).** Both run in the session's own environment and **fail open** — a script error can never block a session.

| Hook | Event | Does |
|---|---|---|
| Context digest | `SessionStart` (startup, resume, clear, compact) | `scripts/session_start.py` looks for `local-context.md` where this session can see it (`~/.grow-pm/`, connected folders under `$HOME/mnt/*/`, the working directory) and hands the model a short `GROW_PM_SESSION` digest: path, configurator version, `user.language`, product names, onboarding mode and deferred steps, whether vault / CJM / team language are configured. Step 0a of every skill becomes a lookup. Re-runs after context compaction, so the location survives long sessions. In a hosted session where the shell cannot see your files it says so — skills then read the file through device tools as before. |
| Write gate | `PreToolUse` on `createJiraIssue`, `editJiraIssue`, `createConfluencePage`, `updateConfluencePage` | `scripts/write_gate.py` asks you to confirm before a content-bearing write, with the checklist the artifact quality gate expects to be done by then (gate report in chat, your go-ahead, not a sandbox). Metadata-only edits pass silently. A hook sees only the tool call, never the conversation — so this is a human-in-the-loop step, not an automatic judge. Opt-out: `/grow-product-manager:setup --write-gate off`. |


---

## Hosts (since v3.0.0)

The plugin is defined against Claude Code / Cowork and degrades by **observed capability**, never by host name — `references/host-profiles.md` is the contract, `testing/host-matrix.md` the per-skill result (derived from what each skill invokes; validator check 14 keeps it complete).

| | Claude Code / Cowork | Codex CLI · Codex app | ChatGPT | Codex Cloud |
|---|---|---|---|---|
| Skills (29) | ✅ | ✅ same namespace | ✅ (expected) | ✅ (expected) |
| Connectors | ✅ | ✅ URL-matched; name-matched ones (`gmail`, `google calendar`, `google drive`, `fireflies`) work in the **app**, fail at session start in the **CLI** | ✅ | ? |
| Filesystem `~/.grow-pm/`, vault | ✅ | ✅ | ❌ → `storage_mode: session`, artifact exported at the end | own sandbox → via connector or the repo |
| Subagents (checker, debater, extractor) | ✅ automatic | ⚠️ only on explicit request → sequential in-session passes (`.codex/agents/` for manual use) | ❌ | ⚠️ |
| Hooks (context digest, write gate) | ✅ | ❌ ([openai/codex#17331](https://github.com/openai/codex/issues/17331)) → Step 0a in full, in-skill confirmation before writes | ❌ | ❌ |
| Commands | ✅ 5, user-only | ✅ 5, migrated to typed-only skills | ❌ | ⚠️ |
| Skill descriptions | full | shortened to fit one shared ≈15k-character budget (~190 chars each on a host with 80 skills) — descriptions are ordered for that cut | ? | ? |
| Per-skill result | 29 full | 15 full / 14 degraded | 19 degraded / 10 n/a | 20 degraded / 9 n/a |

**Codex card.** `.codex-plugin/plugin.json` carries the `interface` block Codex and ChatGPT render — display name, category, brand color and the logo in `assets/` (`logo.png` 512, `composer-icon.png` 128). Claude Code has no logo field, so it reads `.claude-plugin/` only; validator check 1 keeps the two manifests' version and description identical.

**Codex — install and update.** Codex has no auto-update for marketplaces or plugins: the marketplace is a git snapshot and the plugin cache is keyed by version.

```
codex plugin marketplace add asiletskyi-pm-evo/grow-product-manager-plugin
codex plugin add grow-product-manager@grow-product-manager-plugins
```

After every release:

```
codex plugin marketplace upgrade grow-product-manager-plugins
codex plugin add grow-product-manager@grow-product-manager-plugins
```

**ChatGPT** gets roughly half of the plugin — the artifact and research skills on connectors, with the artifact delivered in the chat and exported at the end; the storage-bound contours (Focus Board, experiment registry, the whole People contour, template and knowledge libraries) say so in one line and stop. **Codex Cloud** runs in its own sandbox: never assume prior state, always write results back through a connector or the repository.

---

## Shared References

The plugin includes reference materials for product management best practices and frameworks:

**Key reference files in `references/` (34 total — see the folder for the full list):**
- `host-profiles.md` — Step 0-host: five observable capabilities, four host profiles, the degradation matrix per contour, `${PLUGIN_ROOT}` resolution, measured host gaps
- `local-context-protocol.md` — Step 0: how every skill finds and loads `local-context.md`; where a bare `references/…` lives on every host
- `integration-strategy.md` — MCP → Registry → Browser fallback chain for external tools
- `data-policy.md` — data confidentiality rules (internal data never leaves the session)
- `data-integrity-protocol.md` — verification gate against extrapolation and single-source claims
- `subagent-delegation.md` — when and how skills delegate fan-out work to subagents
- `debate-protocol.md` — role-based adversarial debate engine (roles, rounds, synthesis, ICE correction, guardrails)
- `artifact-style-gate.md` — artifact quality gate: source test for technical content, lists-over-prose, team-language Gate 3, maker–checker execution (an independent checker subagent verifies every artifact)
- `visual-annotation-protocol.md` — annotated screenshots: marker № = requirement №, local Pillow rendering, preview cycle, REST attachment chain
- `self-improvement.md` — learning from user corrections (versioning, changelog)
- `test-mode.md` — sandbox mode for dry-run onboarding and skill testing
- `persistent-storage.md` — Pointer + User-Controlled Storage protocol
- `vault-protocol.md` — Obsidian Vault integration protocol (detection, search, save, MOC updates)
- `vault-schema.md` — Vault artifact schema (frontmatter, types, tags, folder structure, templates)
- `cjm-protocol.md` — CJM shared standards (anomaly severity, funnel impact, health score)
- `funnel-templates.md` — Standard funnel stage templates by product type
- `template-protocol.md` — Multilingual template resolution protocol (Step T-0 → T-5, scoring, fallbacks, backup invariants)
- `planning-core.md` — shared planning definitions for the Planning Suite
- `capacity-model.md` — team capacity math (allocation %, velocity, focus factor)
- `dependency-model.md` — dependency graph and critical-path rules
- `roadmap-artifacts.md` — roadmap artifact formats (tree, timeline, forecast)
- `jira-data-protocol.md` — Jira plumbing: custom-field map, JQL patterns, pagination, transitions parsing (shared by product-reporter and the Planning Suite)

**Design Bridge references:**
- `skills/design-bridge/references/deck-subtypes.yaml` — slide-by-slide outlines for all 4 deck subtypes
- `skills/design-bridge/references/figma-playbook.md` — Figma MCP auth, rate limits, common patterns
- `skills/design-bridge/references/a11y-checklist.md` — WCAG 2.1 AA checklist + contrast pair schema

See the plugin's `references/` folder for the complete list of available materials.

---

## Testing & Contributing

Two validators gate every push and PR (`.github/workflows/validate.yml`), and a third — the two-host smoke test — gates every release (it needs a logged-in Claude and an installed Codex, so it runs on the release machine, not in CI):

```bash
bash testing/validate-consistency.sh   # 14 checks: versions, frontmatter, paths, components, hooks, cross-host packaging
python3 testing/skill_lint.py          # 18 named checks
bash testing/host-smoke.sh             # loads the tree on Claude Code AND Codex CLI — release blocker, run locally
```

Every check exists because the defect class it catches actually shipped, and each is verified by injecting that defect into a repo copy. `testing/trigger-evals.md` is run on **both** hosts before a description-touching release (`codex exec` and `claude -p --plugin-dir`, single-line prompts, scored on the host's real configuration); `testing/host-matrix.md` is the skill × host result. When you find a new defect class, **add a check — never a manual step** (see `testing/Testing-process.md`).

### One-time local setup: `testing/org-tokens.local`

The `org-data` check keeps your organization's identifiers out of a public repo. Its generic layer (real Atlassian hosts, real-looking email domains, literal UUIDs, registry ids, internal hostnames) always runs. But a linter cannot know that a surname, a project key, or an internal tool name is yours — those go in a local denylist:

```bash
printf 'yourcorp.example\nPROJKEY\nSurname\n' > testing/org-tokens.local
python3 testing/skill_lint.py
```

The file is **gitignored on purpose** — a denylist that ships would carry the very strings it forbids. The trade-off is that it protects nothing until you create it, so create it before your first contribution, and add any identifier you purge from the tree to it in the same commit.

---

## Version History

For detailed version history, release notes, and changelog information, see [CHANGELOG.md](CHANGELOG.md).

---

## Getting Started

1. **Add the marketplace and install the plugin** — in a Claude Code session:

   ```
   /plugin marketplace add asiletskyi-pm-evo/grow-product-manager-plugin
   /plugin install grow-product-manager@grow-product-manager-plugins
   ```

   In **Codex CLI** or the Codex app:

   ```
   codex plugin marketplace add asiletskyi-pm-evo/grow-product-manager-plugin
   codex plugin add grow-product-manager@grow-product-manager-plugins
   ```

   (Updates are manual on Codex — see **Hosts** above.)

2. **Configure the plugin** — say "налаштувати плагін" / "configure plugin" to run the Plugin Configurator. Basic setup takes ~3–5 minutes; Extended (~15–25 min) configures CJM, Vault, Templates, Planning, Focus and People. You can start Basic and add the rest later.
3. **Choose your storage location** — Obsidian Vault (recommended: templates and artifacts live together) or `~/.grow-pm/` standalone.
4. **Connect your data sources** (Jira, Confluence, Figma, Tableau, calendar, meeting tools) — the Configurator pre-checks what's available and works with whatever is connected.
5. **Start using skills** by typing trigger phrases in your Claude Code session. Not sure where to start? Say "на чому сфокусуватись" — `focus-advisor` reads your context and recommends.

> Your configuration lives in `local-context.md`, which is gitignored and never leaves your machine. Copy `local-context.example.md` if you prefer to fill it in by hand.

---

## Integration Points

The Grow Product Manager plugin integrates with:

- **Jira** — Task and issue management
- **Confluence** — Document collaboration and publishing
- **Figma** — Design and prototyping (configure your brand's DS `fileKey` in `local-context.md` → `product.figma.ds_file_key`)
- **Tableau / Looker** — Data visualization and metrics
- **Google Calendar / Microsoft Calendar** — Meeting context and scheduling
- **Fireflies.ai** — Meeting recording and transcription
- **Google Drive** — Document storage and collaboration
- **Obsidian** — Persistent knowledge graph (optional)
- **Claude Design plugin** — 6 design skills (research-synthesis, ux-copy, accessibility-review, design-system, design-critique, design-handoff) hooked via `design-bridge` (new in v1.10.0; `design:user-research` was dropped in v2.1.0 — Grow PM's own `product-research` owns primary research)
- **ChatGPT / Google Gemini** — Image and content generation (optional)

---

## Support & Documentation

For questions, issues, or feature requests, please refer to the plugin documentation or contact the plugin author.

**Plugin Author:** Andrii Siletskyi  
**Version:** 3.0.1  
**Last Updated:** September 2026
