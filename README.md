# Grow Product Manager

**Version:** 1.37.0

AI assistant plugin for Product Managers. Integrates with Jira, Confluence, Figma, Tableau, and other tools to streamline product management workflows. Includes a Design Bridge that turns concepts, requirements, research, and hypotheses into brand-themed decks, prototypes, and handoffs with WCAG 2.1 AA a11y gates. All brand specifics (Design System, fonts, tokens, pptx templates) are read from your own `local-context.md` — the plugin ships no hardcoded brand assets.

---

## Overview

**New in v1.37.0** — **Harness engineering, wave 1** (from Google/Kaggle "The New SDLC With Vibe Coding"). Self-improvement now runs a **harness-first diagnosis** — before proposing a fix, the failure is classified by harness layer (instructions / tools / context / guardrails / orchestration / observability) and the fix is routed to the right place, because most agent failures are configuration failures, not model failures. A new `references/harness-map.md` documents the plugin's own harness anatomy and a six-context-type coverage map (thin spot identified: **Examples**). To fill that spot, the three heaviest artifact skills gain on-demand **golden exemplars** (few-shot): `write-concept` (worked PRD), `requirements-creator` (feature-spec with A/B + acceptance criteria), `cjm-research` (period-annotated anomaly report) — each doubling as a future output-eval fixture.

**New in v1.36.0** — **Wave 3 kickoff: three lifecycle skills (23 total)**. `experiment-tracker` closes the loop after the A/B spec — a persistent experiment registry with lifecycle states, stale-test reminders, readouts via product-analysis, and decisions recorded via the new `decision-log` (ADR-style records in vault Decisions/ that finally answer "чому ми вирішили X?"). `feedback-triage` turns raw support-ticket/review streams into a ranked pain map (semantic clustering, frequency × severity × trend vs the previous run's baseline) chaining straight into brainstorm-features. Vault taxonomy grows to 22 types (`feedback-triage`); trigger-evals gain Group H (14 phrases, lifecycle trio vs neighbors).

**New in v1.35.0** — **Monolith refactor complete (2–4/4)**: the three remaining oversized skills slimmed to on-demand cores — `product-analysis` 968 → ~365 lines (analysis engine and the three specialized modes moved to `analysis-engine.md` / `specialized-modes.md`; the Data Integrity Gate stays in the core), `cjm-research` 788 → ~395 (research pipeline Steps 4–11 → `cjm-pipeline.md`; per-mode report formats, publishing, and the automated health-check → `cjm-reports.md`), `knowledge-library` 751 → ~250 (eight mode workflows → `library-workflows.md`; trust scoring, categories, and KL onboarding → `trust-and-categories.md`). All content preserved verbatim; every skill now loads its core plus exactly one reference per mode.

**New in v1.34.0** — **Monolith refactor 1/4: plugin-configurator** slimmed from 1345 to ~180 lines following the planning-suite pattern: the core keeps the mode map, entry conditions, and cross-skill protocols; detailed workflows moved to skill-local references (`onboarding-steps.md` — Steps 1–17 + Planning/Focus setup; `maintenance-modes.md` — RM/Update/Validate/View + Versioning Protocol) loaded on demand. All content preserved verbatim; Planning/Focus setup steps integrated into the onboarding flow (previously dangled after the resources section); a leftover editorial artifact removed. Trigger-evals baseline recorded (A–F 100%, G 95→100 after one label fix).

**New in v1.33.0** — **Focus Advisor complete: `strategy` mode + live "PM Focus Board"**: focus-advisor 0.3.0 ships the third horizon (quarter–year) — 2–4 strategic bets from product goals/missions (pinned source), NPS and funnel trends, research signals, leadership mandates and zone white-spaces, with a mandatory "what we deliberately do NOT do" section in the strategy memo. New `board` mode renders a persistent PM Focus Board (live artifact where supported, static HTML fallback). All three horizons of the original design are now live.

**New in v1.32.0** — **Focus Advisor `tactics` mode**: focus-advisor 0.2.0 adds the sprint-to-quarter horizon — 3–5 tactical focus candidates from roadmap plan-vs-actual pace and drift, backlog staleness (ICE age), features missing prerequisites ahead of next sprints, A/B tests awaiting decisions, capacity/availability and team-event signals. Tactical scoring = ICE + capacity realism + goal alignment; new chains to project-planning `replan` and test readouts; weekly headless tactical brief supported (`mode=tactics headless=true`).

**New in v1.31.0** — **Focus Advisor (20th skill)**: PM attention dispatcher above structure/quarter/sprint — collects context signals (sprint cycle position, calendar meetings needing prep, important unanswered "live" emails, open action items, Jira tails), ranks them, recommends 1–3 daily focuses, and chains execution to the right skill. Headless contract for scheduled morning briefs; mandatory persistence to `~/.grow-pm/focus/` + Vault (`focus-brief`, 21st artifact type). Plugin-configurator 2.4.0 ships a Focus setup onboarding step; trigger-evals gets Group G (attention vs execution).

**New in v1.30.0** — **Roadmap-trio disambiguation + trigger evals**: the three planning skills now carry explicit scope hints in their descriptions (roadmap-architect = structure only, no dates; project-planning = beyond one quarter; quarterly-planning = exactly one quarter), and `testing/trigger-evals.md` ships a 36-phrase routing test set across 6 collision groups with a run protocol and results log. Release-manager 0.1.1: "merging ≠ releasing" guard in Step 6.

**New in v1.29.0** — **Vault coverage complete**: a standard "Save to Vault" step added to the 11 skills that previously never wrote to the Obsidian knowledge graph (requirements-creator, meeting-processor, brainstorm-features, product-research, diagram-prototyper, task-creator, team-ops-reporter, and the 4 Planning Suite skills). Meeting MoMs, requirements, hypotheses, research, diagrams, task breakdowns, ops reports, and roadmaps now accumulate in the vault with wikilinks. Vault schema extended with 4 new artifact types: `diagram`, `task-breakdown`, `ops-report`, `roadmap` (20 types total). Vault stays optional — L0 setups are unaffected.

**New in v1.28.0** — **Release Manager** skill: one guided pipeline to release the plugin itself — version bump across all 4 mandatory places, CHANGELOG entry, README sync, local validation, gated commit/PR/merge, GitHub Release with tag, mirror sync, and post-release verification. Ships with `references/release-pitfalls.md` — nine real failure modes (iCloud-evicted git objects, stale locks, token scopes, VPN-only mirrors, protected-branch divergence, CDN cache…) with guards and recovery recipes.

**New in v1.27.0** — **CI validation + trigger disambiguation**: every push/PR to main now runs `testing/validate-consistency.sh` via GitHub Actions (version consistency across manifests/README/CHANGELOG, SKILL.md frontmatter, broken reference paths). Skill descriptions of the CJM trio (cjm-research / product-analysis / brainstorm-features) and the prototype pair (diagram-prototyper / design-bridge) now carry explicit "Do NOT use" routing hints.

**New in v1.26.0** — **Subagent delegation** extended to all specialized modes of `product-analysis` (Post-Release, A/B Test, CJM Funnel): heavy data-acquisition fan-out runs off the main context, with data-policy guardrails and the Data Integrity Gate preserved. See CHANGELOG v1.24.0–v1.26.0 for the full subagent-delegation rollout.

**New in v1.15.0** — **Planning Suite**: four skills on top of team-ops-reporter — `roadmap-architect` (structure: goal → initiative → epic → feature), `project-planning` (multi-quarter forecast, dependencies, critical path), `quarterly-planning` (quarter roadmap with capacity gate and retro), `sprint-planning` (sprint pre-planning: readiness, risks, assignees). Shared references: `planning-core.md`, `capacity-model.md`, `dependency-model.md`, `roadmap-artifacts.md`.

**New in v1.14.0** — **Team Ops Reporter** skill (5 modes): sprint plan, sprint review, quarter review, initiative status, and team-member review — built directly on Jira (custom-field map, status-history throughput, per-Assignee/Developer breakdowns, charts). Output goes to Confluence and/or local md+xlsx (asked each run). Five built-in templates under `templates/built-in/ops-report/`. See `skills/team-ops-reporter/SKILL.md` and CHANGELOG v1.14.0.

**New in v1.13.0** — **Data Integrity Gate** across `cjm-research`, `product-analysis`, and `product-research`. New universal verification gate that catches incomplete-period extrapolation, holiday windows cited as YoY trends, single-source cascading claims, and missing inline period annotation. See [`references/data-integrity-protocol.md`](references/data-integrity-protocol.md) and CHANGELOG v1.13.0.

**New in v1.12.0** — Onboarding has two modes: **Basic** (3-5 min, mandatory fields only — usable immediately for concept/requirements/research/brainstorm/spec) and **Extended** (15-25 min, full setup of CJM, Vault, Templates, Knowledge Library, Teams, full Tableau analytics). A third **Test mode (sandbox)** lets you walk through onboarding without modifying real data — say `dry-run onboarding` any time. See `skills/plugin-configurator/SKILL.md` for the full Step 1 onboarding map.

The Grow Product Manager plugin is a comprehensive AI-powered toolkit designed to accelerate product management workflows. It provides skills for research, analysis, brainstorming, documentation, task creation, and visualization across your entire product lifecycle.

---

## Skills

### 1. CJM Research (v0.6.0)

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

### 2. Product Analysis (v0.12.0)

**Description:** Analyze product data with interactive dashboards, metrics, and reports to find trends and growth opportunities.

**Modes:**
- **Interactive Q&A** — Ask questions about your metrics
- **Full Report** — Comprehensive analysis of all available data
- **Post-Release** — Analyze metrics before and after a feature release
- **A/B Test Results** — Evaluate test outcomes and statistical significance
- **CJM Funnel Analysis** — Analyze customer behavior across funnel stages

**Trigger phrases:** "analyze metrics", "review a dashboard", "find anomalies", "post-release analysis", "analyze A/B test results", "CJM funnel analysis"

---

### 3. Product Research (v0.10.0)

**Description:** Conduct competitive analysis, user research, market research, and UX benchmarking with Knowledge Library integration for data-backed insights.

**Research Types:**
- Competitive analysis and feature comparison
- User research synthesis and insights
- Market trends and opportunity identification
- UX benchmark research against industry standards

**Trigger phrases:** "research competitors", "analyze the market", "competitive analysis", "find market trends", "UX benchmark research"

---

### 4. Brainstorm Features (v0.8.0)

**Description:** Interactive brainstorming for product features and growth opportunities with ICE scoring and CJM hypothesis generation.

**Features:**
- Feature ideation and scoring (Impact, Confidence, Ease)
- CJM Hypotheses mode with funnel impact calculation
- Growth opportunity identification
- Prioritization framework

**Trigger phrases:** "brainstorm features", "generate hypotheses", "find growth opportunities", "CJM hypotheses"

---

### 5. Write Concept (v0.7.0)

**Description:** Write detailed product concept documents (PRDs) from ideas, problem statements, or research findings.

**Outputs:** Full PRD with objectives, user stories, success metrics, and implementation notes

**Trigger phrases:** "write a concept", "create a PRD"

---

### 6. Requirements Creator (v0.8.0)

**Description:** Create structured feature requirements or analyze and improve existing requirement documents using business analyst expertise.

**Capabilities:**
- Generate detailed requirements from concepts
- Analyze and improve existing specs
- User story generation
- Acceptance criteria definition

**Trigger phrases:** "write requirements", "create feature spec", "review requirements"

---

### 7. Task Creator (v0.9.0)

**Description:** Automatically create Jira tasks and issues from requirements, breaking down work into actionable engineering tasks.

**Capabilities:**
- Parse requirements and decompose into tasks
- Create Jira issues with proper fields and links
- Estimate complexity and effort
- Set up dependencies and sprint planning

**Trigger phrases:** "create tasks for a feature", "create Jira issues"

---

### 8. Diagram & Prototype Creator (v0.9.0)

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

### 9. Meeting Processor (v0.12.0)

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

### 10. Plugin Configurator (v2.5.0)

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

### 11. Knowledge Library (v0.6.0)

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

### 12. Template Library (v0.1.0)

**Description:** Manage a multilingual library of artifact templates (concepts, requirements, research, CJM, epics, tasks, meeting notes, presentations). Templates are stored in your Obsidian vault or custom folder, scoped per-product, and consumed automatically by other skills through the Step T — Template Resolution protocol.

**Features:**
- Three-tier scope: built-in → user-global → product-specific (with inheritance)
- Single-file multilingual storage (`<!-- lang:uk --> ... <!-- /lang:uk -->` blocks)
- Registry-backed resolution with scoring (scope, subtype, language, usage_count)
- 11 actions: list, show, add, clone, update, delete, restore, import, export, validate, rebuild-registry
- Three-tier backup: per-template archive, pack backups, manual backup/restore
- Ships with 17 built-in templates in Ukrainian + English (9 original + 3 presentation templates (v1.10.0) + 5 ops-report templates (v1.14.0))

**Trigger phrases:** "manage templates", "add template", "list templates", "template library", "clone template", "import templates", "restore template"

---

### 13. Design Bridge (v0.2.2) — brand-agnostic since v1.11.0

**Description:** Orchestrator skill that turns concepts, requirements, research, and hypotheses into brand-themed design deliverables (decks, prototypes, handoffs, research enrichment). Invoked either directly ("create deck from concept", "build prototype", "run design handoff") or as an optional **Step D** hook from other skills (write-concept, requirements-creator, brainstorm-features, product-research).

**Intents:**
- **deck** — render a Google Slides-compatible `.pptx` (10×5.625") from the base template you configure in `local-context.md` (`product.base_pptx`). 4 subtypes: feature-concept (10 slides), research-highlights (10 slides), ab-test-readout (6 slides), release-readout (7 slides)
- **prototype** — lo-fi / mid-fi / hi-fi prototype brief for Figma
- **handoff** — developer-ready handoff spec (tokens, components, states, responsive breakpoints) with WCAG 2.1 AA a11y audit as blocker
- **research-enrichment** — pull UI screenshots, competitor visuals, or DS references to augment research

**Design plugin integration:** hooks 7 design skills (research-synthesis, ux-copy, design-critique, design-system, accessibility-review, design-handoff) via optional delegation, plus Figma MCP for DS sync. Your Figma DS `fileKey` lives in `local-context.md` → `product.figma.ds_file_key`.

**Brand configuration (from `local-context.md`):**
- `product.brand.primary`, `product.brand.dark`, `product.brand.font_primary`, `product.brand.font_display`
- `product.design_system_spec` — path to your DS token yaml
- `product.pptx_theme` — path to your pptx theme yaml
- `product.base_pptx` — path to your base pptx template
- Canvas defaults to 10×5.625" (Google Slides 16:9)

**A11y gates (WCAG 2.1 AA):** contrast 4.5:1 normal / 3.0:1 large, 44×44 touch targets, keyboard nav, screen-reader labels, motion controls. Handoff intent has a11y as blocker; deck intent has contrast as blocker + warnings for the rest.

**Trigger phrases:** "create deck", "design handoff", "build prototype", "research enrichment", "apply brand to deck", "run a11y audit"

---

### 14. Team Ops Reporter (v0.3.0)

**Description:** Operational team reports from Jira. Pulls issues, processes them in Python (aggregations, Story Points, carried-vs-new, per-Assignee/Developer, changelog-based throughput), renders from a template, and offers charts.

**Modes:**
- **sprint-plan** — directions → features → tasks, summary (total / carried / new / SP), per-Assignee and per-Developer distribution, key-focus table
- **sprint-review** — closed tasks (Done incl. `Ready`), releases by stream (app / catalog-ui / backend / company-stats), flags ON/OFF, task list, closed-per-member
- **quarter-review** — plan vs actual by direction, epics/features fully closed, releases (fetched per month — full-quarter JQL times out)
- **initiative-status** — mission/epic/feature % done, status breakdown, per sub-feature, blockers (Flagged / On hold / blocked-by)
- **member-review** — role-aware: closed / SP / passed-to-test (`status CHANGED TO "Ready for test" BY <member>`) / passed-to-review / tested, plus dynamics across days/weeks/sprints/months/quarters/years

**Output:** asked each run — Confluence (your space) and/or local `md` + `xlsx`. Visualizations are proposed (burndown, SP dynamics, status donut, load distribution) and built on accept. Built-in templates live in `templates/built-in/ops-report/`; custom ones via Template Library (`artifact_type: ops-report`).

**Trigger phrases:** "sprint plan/review report", "quarter results", "epic/feature/mission status", "how much did <person> close this period", "team ops report", "report on releases / flags / story points"

---

### 15. Roadmap Architect (v0.2.1) — Planning Suite

**Description:** Maintains the canonical structure of work — maps missions/goals → initiatives → epics → features, enforces labeling (labels, names, links), finds gaps, and generates the roadmap tree.

**Modes:** audit / map / tree / onboard

**Trigger phrases:** "tidy up the structure", "label epics/features", "find labeling gaps", "build the roadmap tree", "link an epic to a goal"

---

### 16. Project Planning (v0.2.1) — Planning Suite

**Description:** Plans and forecasts delivery of a project/mission/initiative beyond a single quarter — estimates the total volume of epics/features, builds a dependency graph with critical path, computes duration under a given team allocation %, and lays out a multi-quarter roadmap with rolling-reforecast.

**Modes:** forecast / sequence / roadmap / whatif / replan

**Trigger phrases:** "how long will the project take", "project roadmap", "epic sequence", "feature dependencies", "critical path", "replan the project"

---

### 17. Quarterly Planning (v0.2.1) — Planning Suite

**Description:** Builds a quarterly roadmap, reviews the previous quarter's delivery (plan-vs-actual), and stress-tests the plan against team capacity.

**Modes:** retro / plan / full / refresh

**Trigger phrases:** "build a quarterly roadmap", "quarterly planning", "plan-vs-actual for the quarter", "quarter retro", "is the quarterly plan realistic"

---

### 18. Sprint Planning (v0.2.0) — Planning Suite

**Description:** Sprint pre-planning: derives focuses from the quarterly roadmap, highlights what's READY to pull (dependencies cleared), catches work-sequence violations, gathers per-member capacity, analyzes carryover risk, suggests assignees, and fills the sprint to capacity.

**Modes:** groom / plan / review / forecast

**Trigger phrases:** "plan the sprint", "sprint pre-planning", "what can we pull into sprint N", "what's ready from the backlog", "who takes the tasks"

**Planning Suite shared references:** `planning-core.md`, `capacity-model.md`, `dependency-model.md`, `roadmap-artifacts.md`, plus the shared Jira plumbing in `references/jira-data-protocol.md` (reused from team-ops-reporter — complements reporting, does not duplicate it).

---

### 19. Release Manager (v0.1.1) — NEW in v1.28.0

**Description:** Releases the plugin repository itself — one guided pipeline from "changes are ready" to "both remotes tagged, Release published, docs consistent". Every irreversible step (commit, push, merge, publish) is user-gated.

**Pipeline:** pre-flight guards (iCloud materialization, stale locks, clean tree) → scope & semver decision → bump in the 4 mandatory places (plugin.json, marketplace.json, README, CHANGELOG) → local `validate-consistency.sh` run → gated commit/push → PR → merge → GitHub Release with tag → mirror sync → post-release verification, optional Confluence changelog update, and vault release record.

**Built-in pitfall guide:** `skills/release-manager/references/release-pitfalls.md` — nine real failure modes with guards and recovery recipes (P1 iCloud-evicted git objects, P4 token without workflow scope, P6 diverged protected mirror, P7 stale raw CDN, and more).

**Generic by design:** works for any Claude plugin repo; org specifics (mirrors, VPN hosts, Confluence page) come from `local-context.md` → `plugin_release`.

**Trigger phrases:** "release the plugin", "prepare a release", "bump plugin version", "ship vX.Y.Z", "cut a release"

---

### 20. Focus Advisor (v0.3.0) — NEW in v1.31.0, complete in v1.33.0

**Description:** PM attention dispatcher — the 4th height of the suite, above structure/quarter/sprint. Scans the PM's context (sprint cycle position, calendar meetings needing preparation, important unanswered emails, open action items from recent meetings, Jira tails), ranks the signals, and recommends 1–3 focuses with reasons, cost of delay, and a chained next step. Recommends and chains — never executes another skill's work; the PM decides.

**Full scope (v0.3):** all three horizons — `now` (daily focus), `tactics` (sprint-to-quarter: roadmap drift, stale backlog, A/B decisions, capacity and team events), `strategy` (quarter-to-year: 2–4 bets aligned to product goals/missions with a mandatory exclusions section) — plus `journal`, `auto` routing, `board` (live PM Focus Board with static fallback), and a headless contract for scheduled briefs (daily `now`, weekly `tactics`, quarterly `strategy`).

**Key mechanics:** deterministic ritual calendar (`focus-cadence.md`: "2nd Monday of the sprint → pre-planning"), signal registry with compact packets and TTL cache (`focus-signals.md`), two-stage "live letters" mail filter (automation never becomes a signal), meeting-prep detector with analytical-slice/deck chains, optional metrics health-check chain to product-analysis / cjm-research. All briefs persist to `~/.grow-pm/focus/` + Vault mirror (mandatory Step 7).

**Trigger phrases:** "на чому сфокусуватись", "що мені робити зараз", "фокус дня", "розбери мою пошту і календар", "daily focus", "morning brief"

---

### 21. Experiment Tracker (v0.1.0) — NEW in v1.36.0

**Description:** Owns the experiment lifecycle the pipeline used to drop after the A/B spec: `proposed → specced → running → awaiting-readout → decided`, with a persistent registry (`~/.grow-pm/experiments/registry.yaml` + vault mirror) and stale-test reminders (overdue runs, pending readouts, idle high-ICE hypotheses).

**Modes:** status (board by lifecycle state) / register / start (flag, platforms, split, dates) / readout (chains product-analysis A/B mode — verdicts only come from there) / decide (chains decision-log) / stale (also the weekly headless payload).

**Trigger phrases:** "які тести зараз біжать", "зафіксуй запуск тесту", "які тести чекають рішення", "нагадай про завислі тести", "experiment status"

---

### 22. Decision Log (v0.1.0) — NEW in v1.36.0

**Description:** ADR-style records of key product decisions in the vault `Decisions/` area — context, options considered, decision, rationale, consequences, evidence links. Answers "чому ми вирішили X?" from the accumulated log; supersede-flow preserves history.

**Modes:** log (default; also invoked by meeting-processor, experiment-tracker, planning skills) / search / revisit.

**Trigger phrases:** "зафіксуй рішення", "чому ми вирішили…", "покажи рішення по…", "журнал рішень", "log this decision"

---

### 23. Feedback Triage (v0.1.0) — NEW in v1.36.0

**Description:** Turns a raw feedback stream (support tickets, complaints, reviews, Q&A, NPS verbatims) into a ranked pain map: semantic theme clustering, `frequency × severity × trend` scoring, new/growing/declining theme detection against the previous run's baseline, and hypothesis seeds for brainstorm-features. Feedback text never leaves the session; PII is masked in verbatims.

**Pipeline:** intake (files / GDrive / Confluence / pasted, subagent fan-out) → Python normalize + coverage gate → cluster → score → report (Step T template) → chains → vault save (`feedback-triage` type, 22nd — the baseline for next run's trends).

**Trigger phrases:** "розбери відгуки/скарги", "тріаж фідбеку", "що болить покупцям/продавцям", "кластеризуй support-тікети", "топ проблем за місяць"

---

## Skills Summary

| Skill | Version | Description |
|-------|---------|-------------|
| CJM Research | v0.6.0 | Customer Journey Map analysis and hypothesis validation |
| Product Analysis | v0.12.0 | Analyze metrics, dashboards, and A/B test results |
| Product Research | v0.10.0 | Competitive analysis, user research, market trends, UX benchmarking |
| Brainstorm Features | v0.8.0 | Interactive feature ideation with ICE scoring |
| Write Concept | v0.7.0 | Write product concept documents (PRDs) |
| Requirements Creator | v0.8.0 | Create and analyze feature requirements |
| Task Creator | v0.9.0 | Create Jira tasks from requirements |
| Diagram & Prototype Creator | v0.9.0 | Visualize concepts with diagrams, prototypes, infographics |
| Meeting Processor | v0.12.0 | Process meetings and extract action items |
| Plugin Configurator | v2.5.0 | Configure plugin for your organization |
| Knowledge Library | v0.6.0 | Manage curated knowledge sources |
| Template Library | v0.1.0 | Manage multilingual artifact templates with per-product scope |
| Design Bridge | v0.2.2 | Orchestrate brand-themed decks, prototypes, handoffs, and research enrichment (brand config in `local-context.md`) |
| Team Ops Reporter | v0.3.0 | Operational team reports from Jira: sprint plan/review, quarter review, initiative status, member review |
| Roadmap Architect | v0.2.1 | Canonical work structure: goal → initiative → epic → feature, labeling, gaps, roadmap tree |
| Project Planning | v0.2.1 | Multi-quarter delivery forecast: scope, dependencies, critical path, rolling-reforecast |
| Quarterly Planning | v0.2.1 | Quarterly roadmap with capacity gate and plan-vs-actual retro |
| Sprint Planning | v0.2.0 | Sprint pre-planning: readiness, sequence violations, carryover risk, assignees |
| Release Manager | v0.1.1 | Release the plugin repo: bump → validate → PR → Release → mirror sync, with pitfall guards |
| Focus Advisor | v0.3.0 | PM attention dispatcher: daily / tactical / strategic focus briefs + live Focus Board; signals from calendar, mail, meetings, Jira, roadmap, goals; chains to executing skills |
| Experiment Tracker | v0.1.0 | Experiment lifecycle registry: proposed → running → readout → decided, stale reminders, chains to product-analysis and decision-log |
| Decision Log | v0.1.0 | ADR-style product decision records in vault Decisions/: log, search ("why did we…"), supersede |
| Feedback Triage | v0.1.0 | Feedback stream → clustered themes with frequency × severity × trend scoring, pain ranking, hypothesis seeds |

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

When you invoke a skill that produces a deliverable (e.g., `write-concept`, `requirements-creator`, `product-research`, `cjm-research`, `task-creator`, `product-analysis` in report mode, `diagram-prototyper` for decks, `meeting-processor` for MoMs, `brainstorm-features` when saving, `team-ops-reporter` for ops reports), the skill runs **Step T — Template Resolution** before starting the workflow. Step T:

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

### Built-in templates (shipped in v1.9.0–v1.14.0)

17 seed templates; localize via additional `<!-- lang:xx -->` blocks:

- `concept/default-v1` — PRD skeleton
- `requirements/default-v1` — general feature requirements
- `requirements/ab-test-v1` — A/B test spec
- `research/competitive-v1` — competitive analysis + SWOT
- `research/user-research-v1` — user research synthesis
- `cjm/funnel-v1` — CJM funnel analysis with ICE table
- `epic/default-v1` — Jira epic description
- `task/default-v1` — Jira task with DoD and AC
- `presentation/feature-v1` — 10-slide feature-concept deck outline
- `presentation/research-highlights-v1` — 10-slide research-highlights deck (**new in v1.10.0**)
- `presentation/ab-test-readout-v1` — 6-slide A/B-test readout deck (**new in v1.10.0**)
- `presentation/release-readout-v1` — 7-slide release / sprint readout deck (**new in v1.10.0**)
- `ops-report/sprint-plan-v1` — sprint plan report (**new in v1.14.0**)
- `ops-report/sprint-review-v1` — sprint review report (**new in v1.14.0**)
- `ops-report/quarter-review-v1` — quarter plan-vs-actual report (**new in v1.14.0**)
- `ops-report/initiative-status-v1` — mission/epic/feature status report (**new in v1.14.0**)
- `ops-report/member-review-v1` — team-member review report (**new in v1.14.0**)

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
| `write-concept` | deck (feature-concept) or prototype (lo-fi / mid-fi) |
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

## Shared References

The plugin includes reference materials for product management best practices and frameworks:

**Available reference files in `references/` directory:**
- `local-context-protocol.md` — Step 0: how every skill finds and loads `local-context.md`
- `integration-strategy.md` — MCP → Registry → Browser fallback chain for external tools
- `data-policy.md` — data confidentiality rules (internal data never leaves the session)
- `data-integrity-protocol.md` — verification gate against extrapolation and single-source claims
- `subagent-delegation.md` — when and how skills delegate fan-out work to subagents
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
- `jira-data-protocol.md` — Jira plumbing: custom-field map, JQL patterns, pagination, transitions parsing (shared by team-ops-reporter and the Planning Suite)

**Design Bridge references:**
- `skills/design-bridge/references/deck-subtypes.yaml` — slide-by-slide outlines for all 4 deck subtypes
- `skills/design-bridge/references/figma-playbook.md` — Figma MCP auth, rate limits, common patterns
- `skills/design-bridge/references/a11y-checklist.md` — WCAG 2.1 AA checklist + contrast pair schema

See the plugin's `references/` folder for the complete list of available materials.

---

## Version History

For detailed version history, release notes, and changelog information, see [CHANGELOG.md](CHANGELOG.md).

---

## Getting Started

1. **Install the plugin** from the Claude Code plugin marketplace
2. **Configure the plugin** using the Plugin Configurator skill
3. **Choose your storage location** — Obsidian Vault (recommended) or custom folder
4. **Connect your data sources** (Jira, Confluence, Figma, etc.)
5. **Start using skills** by typing trigger phrases in your Claude Code session

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
- **Claude Design plugin** — 7 design skills (user-research, research-synthesis, ux-copy, accessibility-review, design-system, design-critique, design-handoff) hooked via `design-bridge` (new in v1.10.0)
- **ChatGPT / Google Gemini** — Image and content generation (optional)

---

## Support & Documentation

For questions, issues, or feature requests, please refer to the plugin documentation or contact the plugin author.

**Plugin Author:** Andrii Siletskyi  
**Version:** 1.37.0  
**Last Updated:** July 2026
