---
name: cjm-research
version: 0.20.0
description: CJM funnel research — anomalies → enrichment → hypothesis backlog — and the journey map (stages × evidence lanes). Not data-only dashboards (product-analysis), not ideation alone (brainstorm-features). UA — «CJM-дослідження», «знайди аномалії у воронці», «карта шляху», «health-check воронки з гіпотезами».
---

# CJM Research

> **Path rule.** A bare `references/<file>.md` in this file is read from this skill's own `references/` if the file exists there, otherwise from the **shared** `references/` at the plugin root. Resolve the root as `${PLUGIN_ROOT}`, else `${CLAUDE_PLUGIN_ROOT}`, else the directory that contains `skills/`, found by walking up from this folder (`references/host-profiles.md` §6). Never continue without a protocol named here.

Central orchestrator for Customer Journey Map research. Manages the full CJM pipeline: loads funnel data, detects anomalies, enriches with internal and external knowledge sources, generates improvement hypotheses with funnel impact calculation, and assembles structured reports.

This skill does NOT perform analysis itself — it delegates to specialized skills and assembles the final output.

## Prerequisites

Before starting, read and follow these shared references:
- **`references/local-context-protocol.md`** — Step 0: read `local-context.md`, select active product, load product-specific context
- **`references/cjm-protocol.md`** — shared CJM standards: anomaly severity levels, funnel impact formulas, health score formula, verification checklist, Data Integrity Gate reference
- **`references/data-integrity-protocol.md`** — **MANDATORY (v0.4.0+)** — Gate Checks 1–6 for any cited metric (6, evidence class & frontier, since v3.8.0), executed at Step 3.5
- **`references/funnel-templates.md`** — standard funnel stage templates (e-commerce, SaaS, marketplace, custom)
- **`references/integration-strategy.md`** — MCP → Registry → Browser fallback chain
- **`references/data-policy.md`** — data confidentiality: internal analytics stay internal, external searches use public info only
- **`references/persistent-storage.md`** — persistent storage protocol (`~/.grow-pm/`)
- **`references/vault-protocol.md`** — vault context search, artifact storage, and lifecycle management
- **`references/vault-schema.md`** — vault artifact schema, metadata structure, and query syntax
- **`references/journey-protocol.md`** — mode `journey` (since v0.16.0): the journey map's model, lanes, inputs, findings, note, health trend, page, publication and scheduled refresh; its board (§11–§12) and the portfolio of every journey of the product (§13, since v0.18.0)

Key context used by this skill:
- `product.name`, `product.platforms`, `product.locales` — for scoping the analysis
- CJM Configuration section — funnel template, stages, dashboards, thresholds, default settings
- Knowledge Library section — search modes, Baymard access, Confluence spaces, Google Drive folders
- `user.language` — for output language

## Step T — Template Resolution

Before producing a CJM report (modes `anomalies`, `hypotheses`, `full`, `comparison`), resolve which template to use.

Follow `references/template-protocol.md`.

Declare:
- `artifact_type: cjm`
- `subtype: {inferred from mode — "funnel" | "comparison" | "health-check" | null}` — Step T does not run for `journey`: no template and no fallback, the note's format is `references/journey-protocol.md` §7
- `product_id: {from local-context.md active product}`
- `language: {from local-context.md → `user.language`; fallback `templates.default_language`}`

Run Steps T-1 → T-5 via the `template-library` helper routines. Render and append `<!-- template: {template_id} version: {version} -->` at the end of the report.

For `health-check` mode (automated), use the top-ranked template silently regardless of `templates.preference` to avoid prompting in background runs.

If no template applies → fall back to `cjm-builtin-funnel`; if that's also missing, use the skill's internal report structure.

**Judgment footer (since v3.5.0).** The artifact closes (a journey map: its note only, never its dashboard) with the altitude line from `templates/built-in/partial/judgment-footer-v1.md` (`references/template-protocol.md` T-5 step 3a; checked by `references/artifact-style-gate.md` Gate 4a); since v3.8.0 its evidence labels are confirmed by T-5 step 3c (Gate 4b), in the automated health-check too.

## Modes of Operation

| Mode | Description | Pipeline steps | Estimated time | Output |
|------|-------------|---------------|----------------|--------|
| **anomalies** | Find funnel anomalies only | 1–4 | 2–5 min | Short report: anomalies per funnel stage |
| **hypotheses** | Generate improvement hypotheses | 1–9 | 10–15 min | Hypotheses with ICE + funnel impact |
| **full** | Comprehensive CJM analysis | 1–12 | 20–30 min | Full report + optional backlog |
| **health-check** | Scheduled funnel health check | 1–4 (automated) | 2–5 min | Health summary with delta vs previous — saved as the library snapshot, **never published by the scheduled run** (`references/native-surfaces.md` §4) |
| **comparison** | Cross-platform comparison | 1–4 per platform | 10–15 min | Side-by-side anomaly comparison |
| **journey** | Journey map: stages × evidence lanes, health trend, opportunity tree (since v0.16.0), its board (since v0.17.0), the portfolio of the product's journeys (since v0.18.0), nested maps (since v0.19.0), editing on its page (since v0.20.0) | 1, 1.5, J1–J9 | 5–15 min | The journey note + its page; the dashboard and the boards only after the question |

---

## Pipeline Steps

### Step 1 — Initialize

**1a. Local context (mandatory):**

Follow `references/local-context-protocol.md` — Step 0:
- Read `local-context.md` from `~/.grow-pm/` (primary) or legacy locations
- Select active product (if multiple products configured)
- If `local-context.md` not found → chain to `plugin-configurator` in Onboarding mode

**1b. CJM configuration check (mandatory):**

Follow `references/local-context-protocol.md` — Step 0f.

**If CJM Configuration is present:** load funnel template, stages with dashboard URLs, baseline conversions, anomaly thresholds, default analysis settings; continue.

**If CJM Configuration is missing:** present three options via `AskUserQuestion`:

1. **Run Plugin Configurator → Step 11 (full CJM setup)** — ~3-5 min, saves permanently.
2. **Quick CJM setup (Recommended)** — collect ad-hoc config for this run, then offer to save it to `local-context.md` before running the analysis. See Quick CJM setup in `references/local-context-protocol.md` Step 0f.
3. **Skip CJM mode** — exit gracefully; the user can re-invoke later.

For Quick CJM setup: collect funnel template/stages, dashboard URLs (propose mapping any URL the user already pasted), thresholds (defaults Warning 10%, Critical 25%), comparison baseline, platforms. Before launching the analysis, ask:

> "I've assembled a CJM configuration for this analysis. Save it to `local-context.md` so I don't have to ask next time?"

If the user accepts → invoke the Enrichment Protocol from `references/local-context-protocol.md`, write the CJM Configuration section, and show the changelog. Proceed with the analysis regardless of save decision.

**1c. Knowledge Library availability check (optional):**

Follow `references/local-context-protocol.md` — Step 0g:
- Check if `~/.grow-pm/knowledge-library/` exists and `library.md` is initialized
- If available → note the number of sources and configured search modes
- If not available → note this; enrichment steps will use web search only

**1d. Load previous health-check (for health-check and full modes):**

If mode is `health-check` or `full`:
- Check `~/.grow-pm/knowledge-library/health-checks/` for previous snapshots
- Load the most recent one of the product (its frontmatter `product`; before v4.7.0 a `[date].md` file) for delta comparison
- If no previous check exists → this will be the baseline

**1e. Detect vault level (for all modes):**

Follow `references/vault-protocol.md` → "Vault Level Detection":
- Detect vault_level (L0, L1, L2)
- If vault_level > L0, or a repository is registered → the vault context search runs in Step 1.5
- If vault_level = L0 or vault sync_mode = "off" → vault steps will be skipped

**1f. Judgment contract (all modes):**

> **Judgment contract (Step 0j).** Per `references/local-context-protocol.md` Step 0j and `references/pm-mental-model.md`: note this run's
> judgment points (score, rank, verdict, priority, ship/kill, debate question) internally, with no output. A principle acts only through
> a step that implements it — until one exists here, this skill's questions, gates and output stay exactly as they are.

### Step 1.5: Vault Context Search (Optional)

> Requires: `references/search-protocol.md` (since v3.16.0 — the search, the rating, what is taken silently, the block of variants; it asks nothing in the middle of the run). This skill runs it here, after Step 1, rather than as Step 0.5.

Follow `references/search-protocol.md` with `--skill cjm-research`. This skill's types — a weight, not a filter: `cjm-analysis`, `cjm-health-check`, `funnel-anomaly`, `ab-test-results`, `hypothesis`, `cjm-journey`; the request is the funnel, the stage or the anomaly the user names (in `health-check` mode: the product's funnel health).

What is taken is baseline context:
- previous health scores → compared with the current ones;
- previous anomalies → still present or resolved;
- tested hypotheses → marked as already tested, with their results;
- prior CJM analyses → trends across time.

Note in the report header: "This analysis is informed by {N} previous artifacts from Vault". **`health-check` mode is an automated run** (search-protocol §11): the taken line goes into the report header, a doubt is one `Пошук:` line in the report's data notes, there is no block of variants and nothing to answer — a weekly health-check never waits on a person.

### Step 2 — Clarify scope with user

Ask via AskUserQuestion (skip for automated `health-check` — use the saved parameters; its output is the library snapshot only, never 2e's destination — `references/native-surfaces.md` §4; skip for `journey` — Step J asks what it needs):

**2a. Mode selection:**

> "Which CJM research mode should we use?"

| Mode | Best for |
|------|----------|
| **Anomalies** | Quick funnel health check — find problems fast (2–5 min) |
| **Hypotheses** | Generate improvement ideas with ICE scores and funnel impact (10–15 min) |
| **Full** | Deep analysis with verified hypotheses, impact model, and backlog (20–30 min) |
| **Health-check** | Set up recurring automated funnel monitoring |
| **Comparison** | Compare funnel performance across platforms (Web vs App, etc.) |
| **Journey** | A living journey map — stages × evidence lanes, health trend, opportunity tree (Step J) |

**2b. Target funnel stages:**

> "Which funnel stages to analyze?"

- **All stages** (default) — analyze the complete funnel
- **Specific stages** — user selects from configured stages (e.g., only Cart/Checkout and Payment)

**2c. Time period and baseline:**

> "Time period and comparison baseline?"

- Time period: last week / last month / last quarter / custom date range
- Comparison baseline: previous period (default) / previous year / target values / custom

**2d. Platforms:**

> "Which platforms?"

- **All configured** (default) — analyze all platforms together
- **Specific** — user selects from configured platforms
- For `comparison` mode: user must select 2+ platforms to compare

**2e. Output format:**

> "Where should I publish the report? It will hold internal data (funnel metrics and anomalies). Confluence — everyone who reads the space; Notion or Google Docs — whoever can open that place; a funnel dashboard — you, until you share it; or only a local file."

This is a preference, not the publication itself: the question of `references/native-surfaces.md` §3 is asked at 12a when the report is ready, naming the place chosen here. An automated health-check never uses this step.

- Confluence page (default)
- Notion page
- Google Docs
- Funnel dashboard (since v0.15.0) — every stage's numbers with their source and date, where the session has a place for it (`references/artifact-publishing.md` §2, §9)
- Local markdown file
- Presentation (chains to diagram-prototyper)

**2f. Mode-specific settings:**

- For `health-check`: confirm a recurring schedule if the user wants automation → a recurring run where the host has SCHEDULE `local`, otherwise one line on where to create it; the scheduled run (prompt `cjm-research mode=health-check headless=true` — `headless` marks it automated) writes, never publishes (`references/native-surfaces.md` §4–§5, since v0.14.0)
- For `comparison`: confirm which platforms to compare side-by-side
- For `hypotheses` and `full`: confirm enrichment search modes (library / internet / confluence / gdrive / baymard) — pre-filled from CJM config defaults

### Step 3 — Load CJM data

**Delegate to `product-analysis` in CJM Funnel Analysis mode.**

Pass context:
- Dashboard URLs from CJM Configuration (per stage)
- Target funnel stages (from Step 2b)
- Time period and comparison baseline (from Step 2c)
- Platforms (from Step 2d)
- Anomaly thresholds from CJM Configuration
- `role_defaults.gate_emphasis` tokens (since v3.6.0; none from the automated health-check)

Receive from `product-analysis`:
- Quantitative funnel data: conversion rates per stage, absolute values
- Trends: period-over-period changes per stage
- Raw data for anomaly detection

For `comparison` mode: invoke `product-analysis` separately for each platform being compared.

**Walk the stage** (`walkthrough-local`) — when a funnel stage has an anomaly and the user wants to see it as a customer, chain to **Flow Walkthrough** (`flow-walkthrough`, walk mode, scenario = the stage's goal, surface = the platform under study) and cite the pack's `findings.md` as `observed` stage evidence — `(observed · walkthrough <date>, step N)`. Screenshots stay local (`references/app-drive-protocol.md` §5); the report cites step numbers.

### Step 3.5 — Data Integrity Gate (MANDATORY, v0.4.0+)

**Internal logic (cjm-research).** Executes before Step 4 (Anomaly detection). Every metric from Step 3 goes through Gate Checks 1–6 per `references/data-integrity-protocol.md`. Without passing the gate (Gate Checks 1–5 set the status), the metric MUST NOT be used in anomaly detection or reporting.

**Why this exists:** historic incidents where uncritical citation of raw data points produced cascading errors (incomplete-period extrapolation, Week-1 holiday zriz cited as YoY trend, derived claims propagated without re-verification, missing inline-period annotation). The gate prevents these patterns systematically. See `data-integrity-protocol.md` for the full incident catalog and anti-pattern examples.

**Sub-checks.** Each sub-check runs the matching Gate Check of `references/data-integrity-protocol.md` — criteria, thresholds and actions live there; the note column is what cjm-research adds on top.

| Sub-check | Gate Check in data-integrity-protocol.md | CJM-specific note |
|---|---|---|
| **3.5.a** — Period/Context Completeness | Gate Check 1 (internal data) | Run on every timeseries metric loaded in Step 3 against the Tableau/dashboard extract date. **A blocker for PoP comparison** — do not compare an incomplete period against complete periods without normalization. |
| **3.5.b** — Seasonal/Cyclical Screening | Gate Check 2 (internal data) | Windows per `cjm-protocol.md` → Holiday Screening Windows (Ukraine default; global products also Chinese NY, Diwali, Ramadan, US Thanksgiving / BF, Boxing Day). **Automated health-check never asks:** when `product.primary_market` is unset, apply these windows as before instead of Gate Check 2's one-time question, and note it. For YoY comparison: never cite a holiday week as a year-trend; always read the full YoY table. |
| **3.5.c** — Multi-Source Cross-Validation | Gate Check 3, incl. the extreme-values special case | Every critical CR / GMV / Order / Revenue / Retention metric. Extreme-value methodology change check = DT-* / DATA-* tickets in the analysis period; reference period analysis = the full YoY/PoP table, never a single cell. |
| **3.5.d** — Period Definition Lock + Inline Annotation | Gate Check 4 | Pre-compute the inline-annotation string for every metric here, before Step 4 — e.g. `Catalog CR 0.99% (12mo rolling, 1.05.2025 → 7.05.2026)`, `Listing GMV +20% YoY (May 2025 → May 2026, weeks 18-19, non-holiday window)`, `Brand pages ~48K sessions/month (normalized to 30 days from 7-day extract, May 2026)`. |
| **3.5.e** — Source Type Marker | Gate Check 5 | Internal markers: `tableau-mcp`, `tableau-web`, `internal-live`, `ga-snapshot`, `csv-upload`, `screenshot-user`, `walkthrough-local`, `confluence-internal`, `jira-internal` — `walkthrough-local` (a Flow Walkthrough pack cited in Step 3) is this skill's addition to the protocol list. Enables the audit trail in the final Sources section. |
| **3.5.f** — Gate emphasis (since v3.6.0) | Gate emphasis — role extra checks | Each `role_defaults.gate_emphasis` token whose "Applied by" cell names CJM adds its extra check on top of 3.5.a–e (`period-completeness` and `source-type` are already met by 3.5.a and 3.5.e); a failed one adds a ⚠️ caveat line (not repeated when the Step 3 data already carries it) — never a question, a Blocked status or a halt. The automated health-check applies none, so gate emphasis leaves its output unchanged. |
| **3.5.g** — Evidence Class & Frontier (since v3.8.0) | Gate Check 6 | Runs after the status, on every cited item: Step 3 dashboard metrics `measured` (classes product-analysis returns are kept, never upgraded), configured baselines `reported (local-context.md)`, numbers the user pasted `reported (user)`, the walkthrough pack `observed`, Step 6 feedback and Confluence results `reported`, Step 5 benchmarks `external` (a knowledge-library source per its type); persona or untraceable Deep Research input is `simulated` and stays out of anomalies and findings; Step 8–9 projections take no class (an unsourced lift is `assumed`). A cause of an anomaly stated without an experiment or holdout gets one 6c line naming the human step (an A/B test or holdout, interviews at the stage, the team that owns an unrecorded change) — never a question, a status change or a halt. The automated health-check writes labels only (`[assumed — frontier: <human step>]`). |

**Output of Step 3.5:**

Every metric receives a status:
- ✅ **Verified** — passed Gate Checks 1–5; ready for Step 4 (Anomaly detection)
- ⚠️ **Caveat** — passed with limitations (normalized, holiday-affected, single-source pending cross-validation); inherit caveat into downstream steps and report
- ❌ **Blocked** — failed a critical check; either return to Step 3 to gather additional sources, or inform user that analysis cannot proceed without resolution

**If Blocked metrics > 0:**
- Halt the pipeline before Step 4 OR
- Inform user explicitly: "Cannot proceed with anomaly detection — N metrics are blocked. Need: [list of required resolutions]"

**Reference sources catalog:** Use `cjm-protocol.md` → Recommended reference sources catalog (or `local-context.md` → `data_sources_catalog` for product-specific mappings) to identify which secondary source to query for each metric.


### Steps 4–11 — Research pipeline

Anomaly detection (Step 4), WORLD enrichment (5), INTERNAL enrichment (6), hypothesis building (7), per-hypothesis impact (8), overall-conversion impact (9), independent verification (10), and risk assessment (11) live in `references/cjm-pipeline.md` (skill-local). Read it after the Step 3.5 gate passes. Mode map (which steps run per mode) — see Modes of Operation above.
**PM-first hypotheses (since v3.9.0)** (`references/judgment-points.md` §9) — `hypotheses` / `full` modes, interactive runs, `judgment.learning_mode` `pm_first` or `explain`: Step 7.0 of `references/cjm-pipeline.md`; never in `health-check`, `anomalies` or `comparison`.

> **Debate hook.** If the user asks for a debate / role discussion / red-team, or top hypotheses are contested and touch ≥ 2 interest groups — after hypothesis building (Step 7) run `references/debate-protocol.md` for the top-3 hypotheses: evidence pack = anomalies + enrichment already gathered (post-Step 3.5 gate, each item with its 3.5.g class), roles chosen with the user (Skeptic mandatory), rounds → facilitator synthesis. The verdict corrects ICE Confidence per the protocol's Step D4 (consensus +1…+2 only when the support cites an E#, never on `simulated` or `assumed` input alone; unresolved skeptic objection −1…−2), new risks feed the Step 11 risk assessment, and the «Debates» section embeds in the Step 12 report.

### Step J — Journey map (mode `journey`, since v0.16.0; its board since v0.17.0; the portfolio since v0.18.0; nested maps since v0.19.0; editing on the page since v0.20.0)

Follow `references/journey-protocol.md` — this step only points into it. Entries: «побудуй карту шляху» (J1 → J2 → J4, J3 on request), «онови карту шляху» (J5 → J2 → J4), «дерево можливостей для етапу X» (J3), «опублікуй карту шляху на дошку» (J4), «забери правки з дошки карти шляху» (J6, then J4 on its answer 1), «покажи портфель шляхів» / «які шляхи потребують уваги» (J7), «дочірня карта для кроку …» / «покажи дерево карт» (J8), «забери правки зі сторінки карти шляху» / «ось правки зі сторінки» with a file or a pasted text (J9, then J4); J6 runs before every new version of a recorded board. Steps 1 and 1.5 run as usual; Steps 2–12 do not, except 12.5, which saves the note. `<note>` is the journey's note (`CJM/journeys/<product>/journey-<slug>.md`; several → ask which journey); `--lang` is `uk` when `user.language` is `uk`, else `en`.
- **J1 Build** — a draft in the session's working folder, never in the vault (its page there too, `--out`), deleted with its page once 12.5 has saved the note: the stages from 1b (ids `s<n>`), `owner` a role or a team, never a person; the newest snapshot's rows by `python3 scripts/journey_map.py refresh --note <draft> --snapshot <newest> --lang <lang>` (their ids are the health-check's); then the other inputs of §3 in order — every row with its source marker, every evidence-lane row with its 3.5.g class (Gate Check 6), the other lanes none; `simulated` never a pain; no person's name, e-mail or phone; a stage without evidence stays a gap `⚠️`.
- **J2 Check** — `python3 scripts/journey_map.py check --note <draft or note> --snapshots ~/.grow-pm/knowledge-library/health-checks/` and the semantic pass of §6. Then the preview — stages, lanes, gaps and every finding as a proposal, never a block — and 12.5 saves the note.
- **J3 Tree** — the stage named by its name or id in `stages`; `python3 scripts/journey_map.py tree --stage <id> --note <note>` → Mermaid for `diagram-prototyper`; a target opportunity with fewer than three solutions → `brainstorm-features`; no target → its opportunities only, the PM picks one. No Opportunity Score.
- **J4 Page and publication** — `python3 scripts/journey_map.py health --note <note> --snapshots <dir>`, then `render-html --note <note> --out <the note's name>.html --lang <lang>` beside it. `python3 scripts/publications.py find --key cjm-research/<product>/journey-<slug> --note <note>`, then one question by `references/artifact-publishing.md` §3–§4 — the dashboard's places, then the boards of `references/journey-protocol.md` §11, the host's own before a registry record's (no paid board account needed), their grid from `journey_map.py board-layout --note <note> --lang <lang>` (a place found first, as «нова версія N», a board's after J6; «лише файл» always; «ні» final for the run); since v0.20.0 the question also says that the page carries the switch «Редагувати» — whoever opens it may edit it and send the PM a file of edits, which comes back only through J9's preview; on the host's own artifact the publication declares `capabilities: {db: {rules: [{path: "", read: "view", write: "admin"}]}, user: {scopes: ["profile"]}}` and says that whoever may edit the artifact edits it together, live, the edits still a draft until J9; after each place `publications.py record --key … --note <note> --kind dashboard …` or `--kind board …` (§11), and after a board its state: `journey_map.py board-state … [--last <its previous state>] --out ~/.grow-pm/journey-maps/<product>/journey-<slug>.<surface>.board.json` (the host's board listed back whole, every page).
- **J5 Update** — read the note as it is; keep its stages, outcomes, owner and rows (the PM's edits and the refresh's rows included); add only evidence whose source no row cites yet, as a draft like J1's; J2's preview shows what changed, then 12.5 saves; then `journey_map.py refresh --note <note> --snapshot <newest> --lang <lang>` (§10) and read the note again; `reviewed` set only when the PM confirms the review.
- **J6 What the team changed** — `references/journey-protocol.md` §12: the board read back into scratch files, `journey_map.py board-diff --last <state> --now <reads> --note <note> --out <diff>`, one question that is also the version question; on «забрати» the preview `board-take … --dry-run` (the class of every evidence row the team wrote or changed asked from the PM, never guessed; a parent proposed; what is refused named; what the take leaves on the board, which answer 1 undoes), then `board-take` with the PM's picks and the state kept again with `--last <the previous state>`. Health-check rows never come back from the board; no state → read the board by its cell titles first. A scheduled run never reads a board.
- **J7 Portfolio** — `references/journey-protocol.md` §13, no note of its own: the notes `python3 scripts/ctx.py search --type cjm-journey --type cjm --product <product> --json` gives (exit ≠ 0 → `--dir CJM/journeys/<product>/` and one question for the hand CJM folder, never saved), then `python3 scripts/journey_portfolio.py list --product <product> --note <each found[].file, not sensitive, not empty — the rest named> --snapshots ~/.grow-pm/knowledge-library/health-checks/ --lang <lang>` — its table in the chat (the maps that need attention first, the hand CJMs partly, the skipped named) — and `render-html … --out CJM/journeys/<product>/portfolio.html` beside the maps; the dashboard only after the question: `publications.py find --key cjm-research/<product>/portfolio`, then `record --key … --kind dashboard …` without `--note`; no board. «Зібрати з ручної CJM карту шляху?» → J1, nothing of the hand note carried over.
- **J8 Nested maps** — `references/journey-protocol.md` §14: a child map is a journey map like J1–J5's with stages of its own — the funnel's snapshot is never its input (its `refresh` refuses it; only a snapshot naming it, `map: journey-<slug>`) — its link in its own frontmatter: `parent` (the parent's `journey-<slug>`), `parent_stage`, `parent_step` for a step; ask «якого кроку якої карти?» only when the request names a parent, never guess one. After 12.5 the candidates: the files `python3 scripts/ctx.py search --type cjm-journey --product <product> --json` gives (not sensitive, not empty — the rest named; exit ≠ 0 → the maps' folder), passed as `--map` to every command alike — `python3 scripts/journey_map.py nest --note <the root> --map …` (the tree for the chat, its findings as proposals; no parent's note is ever written), `render-html` (the tree page), `board-layout --with-children` and `board-state` / `board-diff --with-children` (the tree board, each roll-up sticky updated by its id from `rollups`). J6 takes a child row's edits into the child's note from every board it stands on in one preview (`board-take --note <child> --diff <each board's diff>`): a row changed differently on two boards — one version by its element id or none, never two, never `row:`; a child's own publication is under its own key, inside a published root the one question names both places (`references/artifact-publishing.md` §4), and a tree page or board names the child maps whose rows go with it.
- **J9 The page's edits** — `references/journey-protocol.md` §9 «Editing on the page», «Shared edits» and §12: the file the page saved, the text the PM pasted (written first to a scratch file of the session, deleted after the take), or, for a page published on the host's own artifact, its shared edits — the host's database tool lists the artifact's collection `edits` into a scratch folder (`out_dir`), and that folder's `edits` is the `--edits`; after a written take the documents of the taken elements (the diff's `docs`) are deleted in one batch, each pinned to the version listed, the others left for later; `python3 scripts/journey_map.py page-diff --note <the page's root> --edits <file> --out <scratch diff> [--map …]` — a `stale` map named with the page's date («зроблено на старішій версії карти — відкрий свіжу сторінку й повтори правки»), never taken; then the one preview as J6's: `board-take --note <note> --diff <the page's diff> [<each board's diff>] --dry-run` — the class of every evidence row the page wrote or changed asked from the PM, never guessed, `simulated` never; a parent, a code or a target the take refuses named (`bad_parent`, `orphan`, `bad_code`, `bad_target`); a row the page removed dropped only on the PM's `--drop`; a row changed differently on a board and on the page — one version or none — then `board-take` with the PM's picks. A child's rows from a tree page go into the child's note (`--note <child>`). Then J4 offers the new versions. The page never sends anything; a scheduled run never reads a file of edits.
- Without SHELL — the note only (J7: the portfolio's table from the notes the model can read), plus one line that the page, the trend, the tree, the refresh, the board, the portfolio's page and the page's edits need a shell (§9, §13).

### Step 12 — Report assembly and publishing

**Internal logic (cjm-research).**

Assemble the final report based on the selected mode. Use the user's preferred language (`user.language`).

> For a worked, high-quality reference of the target shape and rigor, load `references/examples/funnel-anomaly-report-example-v1.md` on demand. It is a generic exemplar (few-shot) showing period annotation on every metric, Data Integrity caveats, evidence classes with a hand-back line, and funnel-impact math — match its rigor, not its exact wording.

---


Report formats per mode (anomalies / health-check / hypotheses / full / comparison), the Publishing procedure, and the Automated Health-Check Protocol live in `references/cjm-reports.md` (skill-local). Read only the format for the active mode.

### Step 12.5: Save to Vault (Optional)

> Requires: `references/vault-protocol.md` → Vault Save

IF vault_level > L0 AND vault sync_mode != "off":

1. Determine artifact type based on mode:
   - `anomalies` mode → type: `cjm-health-check`
   - `hypotheses` mode → type: `cjm-analysis`
   - `full` mode → type: `cjm-analysis`
   - `health-check` mode → type: `cjm-health-check`
   - `comparison` mode → type: `cjm-analysis`
   - `journey` mode → type: `cjm-journey` — addressed by name, `CJM/journeys/{product}/journey-<slug>.md`, updated in place (`journey-protocol.md` §7)

2. Build artifact:
   ```
   vault_save({
     type: determined_type,
     product: active_product,
     skill: "cjm-research",
     skill_version: "0.20.0",
     tags: [detected funnel stages, anomaly types, platforms analyzed],
     content: full_report_markdown,
     related: [previous health checks used, related hypotheses, source data references],
     extra_frontmatter: {
       health_score: calculated_score (if health-check mode; with date, period, stages — the snapshot's frontmatter, cjm-reports.md),
       anomalies_found: count,
       critical_anomalies: critical_count,
       comparison_baseline: analysis_setting,
       previous_health_check: "[[path_to_previous]]" (if found in Step 1.5)
     }
   })
   ```

3. IF mode was `health-check` and previous health check exists in Vault:
   - Update previous health check's `status` to `superseded`
   - Set `superseded_by` to link to new health check

4. Display: "Saved to Vault: {TYPE_FOLDER_MAP[type]}/{product}/…" (e.g. CJM/health-checks/{product}/…)

**Then, whatever the vault level** (since v0.15.0): for each place 12a published to, record it — `python3 scripts/publications.py record --key cjm-research/<product>/<mode>-<period> [--note <the note saved above>] …`, the funnel dashboard under `cjm-research/<product>/funnel` (`references/artifact-publishing.md` §5). An automated health-check records nothing: it publishes nothing, and its key files stay as they were.

---

## Skill Chaining (post-report)

After report assembly, offer the user next actions based on the mode:

**Always offer:**
- → **Diagram & Prototype Creator** — "Create a visual funnel diagram or infographic from this report"
- → **Flow Walkthrough** — "Walk the [stage] as a customer on [platform]" (stage evidence for the next run)
- → **Product Landscape** — "Run the same stage on the landscape products" (`product-landscape` research mode; the user picks the products)

**From `hypotheses` and `full` modes:**
- → **Requirements Creator** — "Write detailed requirements for the top hypothesis"
- → **Task Creator** — "Create Jira tasks for the prioritized backlog"

**From `full` mode additionally:**
- → **Diagram & Prototype Creator** — "Create a presentation deck from this report"

**From `health-check` mode:**
- → **CJM Research (full mode)** — "Run a full analysis" (if critical anomalies detected)

**From `comparison` mode:**
- → **CJM Research (hypotheses mode)** — "Generate hypotheses for [specific platform]"

**Mode `journey`** (`journey-protocol.md`) — pains come from ← `feedback-triage` (themes), ← `flow-walkthrough` (a pack's steps), ← `product-research`; it hands on → `brainstorm-features` (solutions for the target opportunity), → `experiment-tracker` (tests of a solution), → `diagram-prototyper` (the tree as Mermaid), → `roadmap-architect` (an initiative for a pain without action).

When chaining:
- Pass the full analysis context: report link (if published), anomalies, hypotheses, enrichment data, funnel configuration
- The receiving skill incorporates CJM results without re-analyzing

---

## Quality Standards

- Always cite data sources and values — never present estimates as facts
- Clearly distinguish: data (`measured`, from dashboards) / insights (from analysis, keeping the class of their data) / hypotheses (generated — never a key finding); projections carry no class (`pm-mental-model.md` §4)
- For every anomaly — specify: which stage, which metric, exact deviation, comparison period
- For every hypothesis — specify: which anomaly triggered it, which evidence supports it, confidence level
- Note data quality issues: missing stages, incomplete data, small sample sizes
- Use the user's preferred language (`user.language`) for all output
- Follow `data-policy.md` strictly — internal analytics never leave the session
- When comparing periods — always state which periods and the data freshness
- **(v0.4.0+) Inline period annotation MANDATORY** — every cited metric in TL;DR, Executive Summary, tables, bullets carries inline annotation per Gate Check 4 of `data-integrity-protocol.md` (`12mo rolling`, `YoY`, `snapshot`, `normalized`, etc.). Methodology section at the top is not sufficient — readers copy individual numbers into Slack and slides.
- **(v0.4.0+) Caveat propagation** — Step 3.5 ⚠️ Caveat metrics surface their qualifier in the final report (e.g., "single-source pending cross-validation", "normalized from N-day extract", "holiday-affected period")
- **(v0.4.0+) Anomaly disclosure** — for any reported anomaly: source count (≥ 2; ≥ 3 for extreme), period definition, holiday-screening status, methodology change check status
- **(v0.4.0+) Source type markers** — every cited number in Sources section tagged (`tableau-mcp` / `tableau-web` / `internal-live` / `ga-snapshot` / `confluence-internal`)
- **(v3.8.0+) Evidence classes** — every cited number and quote carries its 3.5.g class first in its annotation (one group label only when every claim it covers shares class and source); `simulated` never in a summary or key findings, `assumed` there only labelled; a hand-back line stays next to its claim

## Additional Resources

- **`references/cjm-pipeline.md`** (skill-local) — Steps 4–11: anomalies, enrichment, hypotheses, impact, verification, risk
- **`references/cjm-reports.md`** (skill-local) — per-mode report formats, the snapshot's frontmatter, publishing, automated health-check protocol
- **`references/examples/funnel-anomaly-report-example-v1.md`** (skill-local) — worked golden anomaly-report exemplar with period annotation, evidence classes + impact math (few-shot; load on demand in Step 8)
- Shared references — the Prerequisites above, plus `references/search-protocol.md` (Step 1.5) and `references/self-improvement.md`

**End of run — the inbox (since v3.21.0).** What this run learned about the user's context (a record of their store, never a person's profile or a note) goes to the inbox as deltas — urgent ones asked at once in one question, the rest one line `У скриньці +N`: `references/context-protocol.md` §5i.

## Routing

The `description` above is short on purpose: a host with many skills shows only part of the skill listing, or skill names alone (`references/host-profiles.md` §7). The full set of phrases and boundaries that route here, as the description carried them up to v3.10.0:

> CJM funnel research — analyze the CJM funnel end to end — anomalies → enrichment → hypothesis backlog. Not data-only dashboards (product-analysis), not ideation alone (brainstorm-features). UA — «CJM-дослідження», «знайди аномалії у воронці», «health-check воронки з гіпотезами», «порівняй платформи». EN — "analyze CJM", "find funnel anomalies", "CJM research", "funnel health check", "compare platforms", "CJM hypotheses". Also UA — «проаналізуй CJM», «CJM гіпотези».
>
> Since v0.16.0, the journey map (mode `journey`): UA — «побудуй карту шляху», «онови карту шляху», «карта шляху клієнта з доказами», «дерево можливостей для етапу …», «здоров'я шляху в часі». EN — "build a journey map", "update the journey map", "journey map with evidence", "opportunity solution tree for the checkout stage", "journey health over time". Not a funnel dashboard alone (product-analysis), not a story map (roadmap-architect), not a drawn CJM picture without evidence (diagram-prototyper).
>
> Since v0.17.0, the journey map's board: UA — «дошка карти шляху», «опублікуй карту шляху на дошку», «забери правки з дошки карти». EN — "publish the journey map to a board", "take the team's board edits into the journey map". Not the story map's board (roadmap-architect).
>
> Since v0.18.0, the journey portfolio: UA — «покажи портфель шляхів», «усі карти шляху продукту», «які шляхи потребують уваги», «портфель карт шляху з ручними CJM». EN — "show the journey portfolio", "all journey maps of the product", "which journeys need attention". Not a portfolio of projects or initiatives (roadmap-architect, project-planning), not the funnel dashboard (product-analysis).
>
> Since v0.20.0, editing on the journey map's page: UA — «забери правки зі сторінки карти шляху», «ось правки зі сторінки карти», «колега відредагував карту шляху на сторінці», «перенеси правки зі сторінки в карту». EN — "take the edits from the journey map's page", "here are the page edits of the journey map", "a colleague edited the journey map page". Not the board's edits alone (J6), not a story map (roadmap-architect).
>
> Since v0.19.0, nested journey maps: UA — «дочірня карта для кроку …», «розклади крок карти шляху на окрему карту», «дерево карт шляху», «вкладені карти шляху». EN — "a child journey map for a step", "nested journey maps", "the journey map tree". Not a story map's release slices (roadmap-architect), not a drawn hierarchy without evidence (diagram-prototyper).
