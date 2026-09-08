---
name: product-analysis
version: 0.12.2
description: Analyze product data — dashboards, metrics, A/B results, funnel vs baseline — explain anomalies; data only. Not the CJM research pipeline (cjm-research), not focus triage (focus-advisor). UA — «проаналізуй метрики/дашборд», «результати A/B-тесту», «чому впала конверсія», «воронка проти baseline». EN — "analyze metrics", "review a dashboard", "find anomalies", "explain this data", "post-release analysis", "analyze A/B test results", "CJM funnel analysis (data only)". Also UA — «знайди аномалії», «поясни ці дані», «аналіз після релізу». Generates data-backed hypotheses; for anomalies → enrichment → backlog use cjm-research.
---

# Product Analysis

> **Path rule.** A bare `references/<file>.md` in this file is read from this skill's own `references/` if the file exists there, otherwise from the **shared** `references/` at the plugin root. Resolve the root as `${PLUGIN_ROOT}`, else `${CLAUDE_PLUGIN_ROOT}`, else the directory that contains `skills/`, found by walking up from this folder (`references/host-profiles.md` §6). Never continue without a protocol named here.

Analyze product data from any source — dashboards, tables, reports, metrics exports — to surface key trends, anomalies, growth opportunities, and risks. Generate data-backed hypotheses with ICE scoring. Supports five modes: interactive Q&A, full structured report, post-release analysis, A/B test results analysis, and CJM funnel analysis.

## Integration prerequisite

Before gathering data, read and follow the integration fallback chain in `references/integration-strategy.md`. For this skill, the typical external products needed are:

- **Tableau** — primary source of product metrics, dashboards, and A/B test results dashboards
- **Google Sheets** — for metrics exports and shared data tables
- **Confluence** — for reading previous analysis reports, feature requirements, and publishing new ones
- **Jira** — for reading feature tasks, release dates, feature flag names, and Epic context (critical for post-release and A/B test analysis)
- **Notion** — alternative publishing destination
- **Google Docs** — alternative publishing destination
- **Figma** — for design context when analyzing UX-related metrics (funnels, conversion)
- **Web** — always available via WebSearch for benchmarks and industry context

For each product: check for MCP connector → search MCP registry → fall back to browser.

Before gathering any data, also read and comply with `references/data-policy.md`. Confidential data (Tableau metrics, internal analytics, research materials) must NOT be passed to external LLMs or third parties.

## Local context prerequisite

**Before starting, follow `references/local-context-protocol.md` (Step 0).** Read `local-context.md`, select the active product, and load all product-specific context (Tableau URLs, A/B test dashboards, key metrics, OKRs). If the file doesn't exist — redirect to Plugin Configurator for initial setup.

Key context used by this skill:
- `product.name`, `product.key_metrics`, `product.current_okrs` — for analysis focus
- `organization.tableau_base_url`, `product.ab_test_dashboards` — for A/B test and dashboard analysis
- `product.jira_project_key` — for post-release analysis (reading Jira tasks)
- CJM Configuration section — funnel stages, dashboard URLs, baselines, thresholds (for CJM mode)
- `user.language` — for output language

### Vault context prerequisite

**After local context (Step 0) is loaded, read and follow the vault integration in `references/vault-protocol.md` and `references/vault-schema.md`.** If vault is configured and vault_level > L0, you will use vault context search and save throughout this workflow.

## Step T — Template Resolution (when producing a structured report)

Runs **after Step 1b (mode selection) and before data acquisition**, and only when the user requests a deliverable artifact (Full structured report, Post-Release Analysis report, A/B Test Results report, or CJM Funnel Analysis report). **Skip Step T for Interactive Q&A mode** — no artifact is being produced, so no template is needed.

> The ordering matters and used to be wrong ("runs before Step 1"): `subtype` is inferred from the selected mode, and the mode is chosen in Step 1b — so unless the user named the mode outright, Step T had no input to run on. Resolving the template before the data is gathered is still the point: T-4 tells Step 1 which variables to collect.

Follow `references/template-protocol.md`:

- `artifact_type`: `research` for the three analysis reports; **`cjm` for CJM Funnel Analysis** — that report is the same artifact `cjm-research` produces, and a `research`-typed request can never match the `cjm`-typed built-in (or any custom CJM template the user registered), which is why the declared `cjm-funnel` fallback below was unreachable until v2.1.1.
- `subtype`: inferred from selected mode
  - Full structured report → `metrics-analysis`
  - Post-Release Analysis → `post-release`
  - A/B Test Results → `ab-test-results`
  - CJM Funnel Analysis → `funnel` (with `artifact_type: cjm` — matching `cjm-research`)
- `product_id`: from local-context.md active product
- `language`: from `user.language` in local-context.md

Run **Steps T-0 → T-5 exactly as `references/template-protocol.md` names them** — do not renumber them here (this skill used to call the preference check "T-1" and rendering "T-4", so a cross-skill reference to "Step T-4" meant two different things):

- **T-0 (Declare context):** the `artifact_type` / `subtype` / `product_id` / `language` above.
- **T-1 (Load registry) + T-2 (Score and rank):** via the template-library helper `resolve({artifact_type, subtype, product_id, language})`.
- **T-3 (Decide):** per `templates.preference` from local-context.md (`auto` | `always_ask` | `smart`, default `smart`) — auto-select the top candidate, always ask, or ask only when several strong candidates exist.
- **T-4 (Collect variables):** gather the template's required variables during Step 1 data gathering.
- **T-5 (Render and record):** if no suitable template exists, fall back to the skill's built-in structure (see mode-specific sections below). When saving the final report (Confluence / Notion / vault), append the marker the protocol defines:
   ```
   <!-- template: {template_id} version: {version} -->
   ```

**Fallbacks** (when registry returns no match — the protocol's built-in ladder runs first):
- `metrics-analysis` → built-in structure defined in Step 7
- `post-release` → built-in structure in Post-Release Analysis Mode section
- `ab-test-results` → built-in structure in A/B Test Results Analysis Mode section
- `cjm` / `funnel` → `builtin://cjm/funnel-v1.md`, the same built-in `cjm-research` uses

**Escape hatch:** if the user says "don't use a template" or "blank slate", skip Step T entirely and use the built-in skeleton.

**Chained invocation:** if this skill is invoked from `cjm-research`, `cjm-research` has already resolved the CJM template; this skill receives the resolved template id in passed context and skips T-2.

## Workflow

### Step 1 — Initialization and data acquisition

> **Subagent delegation (large fan-out).** For many dashboards / funnel stages / data sources, delegate per `references/subagent-delegation.md`: split into batches (by dashboard / stage / segment), spawn subagents in parallel, each returns a compact structured result (per source: metric values, trend, period definition, source-type marker + source link), and the main agent aggregates and runs Step 1.5 validation. Falls back to inline if subagents are unavailable.


**1a. Product and feature context — clarify via AskUserQuestion if not clear from context:**

- **Which product or part of the product ecosystem** is this analysis for? (if not explicitly stated — ask before proceeding)
- **New or existing functionality?** — Are we analyzing data for existing functionality or evaluating metrics for something being planned? (if not clear — ask explicitly)

**1b. Mode selection — ask via AskUserQuestion:**

> "Which mode should we use?"

- **Interactive Q&A** — the user asks questions about the data, the skill answers and explores. Lightweight, conversational. Good for ad-hoc analysis, quick metric checks, exploratory investigation
- **Full structured report** — systematic analysis following all frameworks, with a comprehensive report at the end. Good for periodic reviews, deep dives, pre-concept research
- **Post-release analysis** — analyze how a released feature affected product metrics. Based on feature requirements, Jira tasks, and release/flag activation dates. see `references/specialized-modes.md`
- **A/B test results analysis** — comprehensive analysis of A/B test outcomes. Based on user-provided reports or Tableau A/B test dashboards. see `references/specialized-modes.md`
- **CJM Funnel Analysis** — analyze funnel conversion rates per stage, detect anomalies, and segment by platform. Invoked by `cjm-research` or directly by the user. see `references/specialized-modes.md`

Interactive Q&A and Full Report modes follow the same analysis engine (Step 2) but differ in output format. Post-Release, A/B Test, and CJM Funnel modes have specialized workflows described in `references/specialized-modes.md`.

**1c. Invocation context — determine how the skill was triggered:**

- **Transition from another skill** (Product Research / Write Concept / Brainstorm Features / Requirements Creator / **CJM Research**) → context was passed from the previous skill. Understand what specific data analysis is needed and what context is already known. Use passed context as the starting point
- **Standalone launch** → gather context from scratch

**1d. Maximum context gathering — ask via AskUserQuestion what is known:**

- **Key metrics the user cares about** — what should we focus on? (conversion, retention, revenue, engagement, funnel stages, etc.)
- **OKR context** — current quarter OKR targets, if relevant
- **Recent launches** — any features, experiments, or changes recently shipped that could explain data shifts?
- **Seasonality** — are there known seasonal patterns to account for?
- **Known issues** — any known bugs, outages, or external events affecting data?
- **Time period** — what date range should we analyze?
- **Comparison baseline** — compare with previous period, same period last year, a specific benchmark?

**1e. Data source acquisition:** the full multi-source acquisition guidance (Tableau MCP-first, Google Sheets, CSV/XLSX, screenshots, PDF, text, Confluence history, Figma) lives in `references/analysis-engine.md` → section 1e. Read it when running Interactive Q&A or Full Report mode; the specialized modes have their own acquisition steps (CJM-3 / PR-2 / AB-2).

### Step 0.5: Vault Context Search (Optional)

> Requires: `references/vault-protocol.md` → Step 0.5

IF vault_level > L0 (detected during Step 0h):

1. Search vault for relevant prior artifacts:
   - Types: `cjm-analysis`, `ab-test-results`, `metrics-review`, `post-release`, `hypothesis`
   - Product: active product
   - Tags: metric names, analysis type keywords
   - Status: `active`, `draft`
   - Sort: `created DESC`, limit: 10

2. IF results found:
   - Display: "Found {N} related analysis artifacts in your knowledge base:"
   - Show: title, type, date, key metrics or test results
   - Ask: "Use as context? [Yes / Select specific / Skip]"

3. IF user accepts:
   - Read full content of selected artifacts
   - Use as context:
     - Previous metrics reviews → compare trends, identify recurring patterns
     - Prior A/B test results → reference when analyzing related metrics
     - CJM analyses → understand funnel context for current metrics
     - Hypotheses → link metrics changes to tested/untested hypotheses
   - Note in analysis: "Comparison with previous analysis from {date}"

4. IF user skips OR no results → continue normally

### Step 1.5 — Data Integrity Gate (MANDATORY, v0.9.0+)

**Internal logic (product-analysis).** Executes before Step 2 (Analysis engine). Every data source loaded in Step 1 (Tableau, Google Sheets, CSV, screenshots, PDF, A/B reports) passes 5 universal gate checks per `references/data-integrity-protocol.md`. Without passing the gate, the metric MUST NOT be used in the analysis engine or final report.

**Why this exists:** historic incidents where uncritical citation of raw data points produced cascading errors. Specific to this skill: A/B test verdicts and post-release classifications are particularly high-stakes — a "winner" label on insufficient data leads to wrong rollout decisions. See `data-integrity-protocol.md` for the full incident catalog.

**1.5.a — Period/Context Completeness Check:**

- **Tableau:** verify extract date vs last timeseries point. Incomplete period → normalize, exclude, or wait.
- **CSV/uploaded:** verify max(date) in data vs declared analysis scope.
- **A/B test results:** verify test duration matches declared, sample size is sufficient for power.
- **Screenshots:** ask user about extract date and scope if unclear.

**This is a blocker for PoP / before-after comparisons.**

**1.5.b — Seasonal/Cyclical Screening:**

Auto-screen analyzed periods against holiday windows (per `cjm-protocol.md` → Holiday Screening Windows):
- Ukraine: Week 1 (Jan 1-7), Mar 7-8, Easter ± 1 week, May 1-3, BF, Dec 22-31
- Global products: also Chinese NY, Diwali, Ramadan, US Thanksgiving / BF, Boxing Day

If anomaly aligns with holiday window:
- ⚠️ FLAG: "Holiday-affected period"
- Search for sustained pattern in non-holiday weeks
- **For post-release / A/B test: check if test period overlapped holidays → if yes, extrapolation is risky; consider extending the test past the holiday window**

**1.5.c — Multi-Source Cross-Validation:**

For critical CR / GMV / Order / Revenue / Retention metrics:
- ≥ 2 independent sources (two Tableau workbooks, or Tableau + an internal live-metrics tool, or Tableau + GA, or CSV + Tableau)
- Variance ≤ 15% tolerated; > 15% → flag, resolve

**Special case — extreme values:**
- Drop > 25% (negative)
- Lift > 50% (positive)
- Sensational claims (10× growth, +200%)
- A/B test result with Δ% > expected by 2× — likely novelty effect or selection bias

→ Auto-promote to ≥ 3 sources, methodology change check (DT-* / DATA-* / Jira release tickets), reference period analysis (full table, not single cell).

**For A/B test specifically:**
- Sample size check vs power analysis — insufficient → inconclusive verdict, do not declare winner/loser
- Statistical significance reporting (p-value, confidence interval) — never just Δ%
- Selection bias check (traffic split balanced? opt-in vs random?)
- Novelty effect screening (week-1 lift might fade by week 4)
- Segment results (overall winner but losing on Mobile = flag, not blanket rollout)

**For post-release specifically:**
- Verify release date + flag activation date from ≥ 2 sources (Jira deployment + Confluence release note + metric inflection point)
- Before/after periods — equal duration, holiday-balanced
- Per-platform rollout → analyze each platform's timeline separately
- Side-effects check on metrics outside requirements

**1.5.d — Period Definition Lock + Inline Annotation:**

Pre-compute inline-annotation for every metric. Examples:

- `Conversion +12% YoY (May 2025 → May 2026, weeks 18-19, non-holiday window)`
- `A/B test +8.5% primary metric (pilot Q1 2026, 50/50 split, 21-day duration, p=0.03)`
- `Post-release: ATC rate 12.4% → 13.8% (before: 1.04-15.04; after: 22.04-12.05, both holiday-free)`

Methodology section at the top is **not sufficient** — readers copy individual numbers into Slack and slides.

**1.5.e — Source Type Marker:**

Tag every source: `tableau-mcp`, `tableau-web`, `internal-live`, `ga-snapshot`, `csv-upload`, `screenshot-user`, `pdf-upload`, `confluence-internal`, `jira-internal`, `user-text`.

### Output of Step 1.5

Every metric receives status: ✅ Verified / ⚠️ Caveat / ❌ Blocked.

If Blocked metrics > 0:
- Return to Step 1 to gather additional sources OR
- Inform user explicitly that analysis cannot proceed without resolution

### Steps 2–6 — Analysis engine, findings, hypotheses, report

The full engine — Python computation (2a), framework toolkit (2c), findings structure (Step 3), hypothesis generation with ICE (Step 4), interactive discussion (Step 5), report structure, publishing and feedback (Step 6) — lives in `references/analysis-engine.md` (skill-local). Read it when running **Interactive Q&A** or **Full Report** mode. Specialized modes reuse only Step 6 (report/save/feedback) from it.

### Vault Save (Optional — after output delivery)

> Requires: `references/vault-protocol.md` → Vault Save

IF vault_level > L0 AND vault sync_mode != "off":

1. Determine artifact type based on analysis mode:
   - Interactive Q&A / Full structured report → type: `metrics-review`
   - A/B Test Results Analysis → type: `ab-test-results`
   - Post-Release Analysis → type: `post-release`
   - CJM Funnel Analysis → type: `cjm-analysis` (delegated from cjm-research, usually saved by that skill)

2. Build artifact:
   ```
   vault_save({
     type: determined_type,
     product: active_product,
     skill: "product-analysis",
     skill_version: "0.12.2",
     tags: [metric names analyzed, platforms, analysis_mode],
     content: full_analysis_markdown,
     related: [source hypothesis, source requirements, previous analyses from Step 0.5],
     extra_frontmatter: {
       // For ab-test-results:
       test_name: test_name,
       test_duration_days: duration,
       sample_size: total_sample,
       primary_metric: primary_metric_name,
       primary_metric_change: "+X.X%" or "-X.X%",
       statistical_significance: significance_value,
       result: "winner" | "loser" | "inconclusive",
       tested_hypothesis: "[[Hypotheses/product/hypothesis-name]]" (if linked),
       
       // For metrics-review:
       review_period: "YYYY-MM-DD to YYYY-MM-DD",
       key_metrics_analyzed: [metric_names],
       anomalies_detected: count,
       trend_direction: "up" | "down" | "stable",
       
       // For post-release:
       feature_name: feature_name,
       release_date: release_date,
       metrics_impacted: [metric_names],
       overall_impact: "positive" | "negative" | "neutral",
       
       // Common:
       published_to: url_if_published,
       confluence_page_id: page_id_if_applicable
     }
   })
   ```

3. **Special: Hypothesis Lifecycle Update for A/B Test Results**
   
   IF type == "ab-test-results" AND a tested hypothesis is linked:
   
   Follow `references/vault-protocol.md` → "Hypothesis Lifecycle Updates":
   - Read the linked hypothesis from Vault
   - Update `hypothesis_status`: winner → `validated`, loser → `rejected`, inconclusive → stays `testing` (not a status value — the test did not decide the hypothesis)
   - Set `test_result` and `validated_by` fields
   - If rejected: set `confidence` to 0.2
   - Update `last_reviewed` to today
   - Log: "Updated hypothesis status to {status} based on A/B test results"

4. Display: "Saved to Vault: {TYPE_FOLDER_MAP[type]}/{product}/…" (e.g. Analysis/metrics/{product}/…)

### Step 7 — Skill chaining

After completing the analysis, **always** propose transitioning to the next logical skill based on the findings:

> "Analysis is complete. What's next? Based on the results, I can:"

**Propose based on findings:**

- **If growth opportunities found** → "Run **Brainstorm Features and Hypotheses** based on the identified growth opportunities"
- **If deeper research needed** → "Run **Product Research** to investigate the identified trends or problems further"
- **If a clear feature idea emerged** → "Create a **Concept (PRD)** (Write Concept) based on the found insights"
- **If hypotheses are ready for implementation** → "Create **feature requirements** (Requirements Creator) to implement the selected hypotheses"
- **If funnel anomalies detected** → "Run **CJM Research** for comprehensive funnel analysis with enrichment and hypothesis generation"

If the user chooses a skill:
- Pass the full analysis context: report link (if published), key findings, relevant hypotheses, data sources, metrics context
- The receiving skill will use analysis results as evidence base

If the user declines — end the workflow gracefully.

---

## Specialized modes

**CJM Funnel Analysis** (CJM-1..CJM-5), **Post-Release Analysis** (PR-1..PR-4), and **A/B Test Results** (AB-1..AB-4) live in `references/specialized-modes.md` (skill-local). Read the relevant mode section when entering that mode — never all three. Each mode honors the Step 1.5 gate and its subagent-delegation callout, and ends via Step 6 (report/save/feedback).

---

## Returning results to calling skills

When Product Analysis is invoked by another skill (Product Research, Write Concept, Brainstorm Features, Requirements Creator, **CJM Research**), return results in a structured format that the calling skill can incorporate:

**Return payload:**
- **Key metrics and values** — specific numbers the calling skill requested
- **Trends summary** — direction and magnitude of relevant metrics
- **Anomalies** — any unexpected findings relevant to the calling skill's context
- **Relevant hypotheses** — data-backed hypotheses that fit the calling skill's scope
- **Data quality notes** — caveats, limitations, data freshness
- **CJM-specific data** (when returning to `cjm-research`) — structured per-stage anomaly list with severity, deviation, and trend

The calling skill should incorporate these results into its workflow without re-analyzing the same data.

## Quality standards

- Always show computation results — never estimate what can be computed precisely
- Clearly distinguish facts (data) from interpretations (analysis) from assumptions (hypotheses)
- For every finding — cite the specific data source and values
- Note data quality issues: missing data, small sample sizes, potential biases
- Flag data older than the relevant analysis period
- Use Ukrainian or English based on user's language preference
- When comparing periods — always state which periods are being compared
- Statistical claims must be backed by actual computation, not intuition
- **(v0.9.0+) Inline period annotation MANDATORY** — every cited metric in TL;DR, Executive Summary, A/B verdict, post-release classification, tables, bullets carries inline annotation per Gate Check 4 of `data-integrity-protocol.md`. Methodology section at the top is not sufficient — readers copy individual numbers into Slack and slides.
- **(v0.9.0+) Caveat propagation** — Step 1.5 ⚠️ Caveat metrics surface their qualifier in the final report
- **(v0.9.0+) Anomaly/A-B disclosure** — for any reported anomaly or A/B verdict: source count (≥ 2; ≥ 3 for extreme), period definition, holiday-screening status, methodology change check status, sample-size and power adequacy
- **(v0.9.0+) Source type markers** — every cited number in Sources section tagged (`tableau-mcp` / `tableau-web` / `internal-live` / `ga-snapshot` / `csv-upload` / `screenshot-user` / `pdf-upload` / `confluence-internal` / `jira-internal`)
- **(v0.9.0+) Never declare A/B winner/loser without:** sample-size power check, p-value or confidence interval, holiday-screening pass, segment-level review (Mobile vs Web, country, user-type)

## Additional Resources

- **`references/analysis-engine.md`** (skill-local) — data acquisition (1e) + Steps 2–6: frameworks, hypotheses, report, publishing
- **`references/specialized-modes.md`** (skill-local) — CJM Funnel / Post-Release / A/B Test modes in full

- **`references/data-integrity-protocol.md`** — **MANDATORY (v0.9.0+)** — 5 universal gate checks for any cited metric (Step 1.5)
- **`references/analysis-frameworks.md`** — detailed description of each analysis framework with examples
- **`references/hypothesis-template.md`** — ICE scoring guidelines adapted for data-driven hypotheses
- **`references/cjm-protocol.md`** — CJM anomaly severity, funnel impact formulas, health score formula, holiday windows, reference sources catalog
- **`references/funnel-templates.md`** — standard funnel stage templates by product type
- **`references/local-context-protocol.md`** — Step 0: how to read and use local-context.md (mandatory before any skill execution)
- **`references/integration-strategy.md`** — MCP → Registry → Browser fallback chain (shared across all skills)
- **`references/data-policy.md`** — data confidentiality policy: what data can and cannot be shared externally (mandatory reading before any data gathering)
- **`references/self-improvement.md`** — self-improvement protocol: how to learn from user corrections and improve skill algorithms
- **`references/vault-protocol.md`** — vault integration protocol: storing, searching, and retrieving analysis artifacts
- **`references/vault-schema.md`** — vault schema definition for analysis artifact types and metadata
