---
name: product-analysis
version: 0.11.0
description: Analyze product data — dashboards, tables, reports, metrics — to find trends, anomalies, growth opportunities, and generate data-backed hypotheses. Use when the user asks to "analyze metrics", "review a dashboard", "find anomalies", "explain this data", "post-release analysis", "analyze A/B test results", or "CJM funnel analysis". Українською: "проаналізувати метрики", "подивитись дашборд", "знайти аномалії", "пояснити ці дані", "аналіз після релізу", "аналіз результатів A/B-тесту", "аналіз CJM-воронки".
---

# Product Analysis

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

Runs before Step 1 of the workflow, but only when the user requests a deliverable artifact (Full structured report, Post-Release Analysis report, A/B Test Results report, or CJM Funnel Analysis report). **Skip Step T for Interactive Q&A mode** — no artifact is being produced, so no template is needed.

Follow `references/template-protocol.md`:

- `artifact_type: research`
- `subtype`: inferred from selected mode
  - Full structured report → `metrics-analysis`
  - Post-Release Analysis → `post-release`
  - A/B Test Results → `ab-test-results`
  - CJM Funnel Analysis → `cjm-funnel`
- `product_id`: from local-context.md active product
- `language`: from `user.language` in local-context.md

Run Steps T-1 → T-5 from `references/template-protocol.md`:

1. **T-1 (Check preference):** read `templates.preference` from local-context.md (`auto` | `always_ask` | `smart`, default `smart`).
2. **T-2 (Query registry):** call template-library helper `resolve({artifact_type, subtype, product_id, language})`; get ranked candidates.
3. **T-3 (Decide):** per preference mode, either auto-select top candidate, always ask, or ask only when multiple strong candidates exist.
4. **T-4 (Render):** if a template was selected, use it as the report skeleton; collect required variables during Step 1 data gathering; if no suitable template exists, fall back to the skill's built-in structure (see mode-specific sections below).
5. **T-5 (Mark):** when saving the final report (Confluence / Notion / vault), append:
   ```
   <!-- template: {template_id}@{version} -->
   ```

**Fallbacks** (when registry returns no match):
- `metrics-analysis` → built-in structure defined in Step 7
- `post-release` → built-in structure in Post-Release Analysis Mode section
- `ab-test-results` → built-in structure in A/B Test Results Analysis Mode section
- `cjm-funnel` → `cjm-builtin-funnel` (shared with `cjm-research`)

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
- **Post-release analysis** — analyze how a released feature affected product metrics. Based on feature requirements, Jira tasks, and release/flag activation dates. See dedicated section: **Post-Release Analysis Mode**
- **A/B test results analysis** — comprehensive analysis of A/B test outcomes. Based on user-provided reports or Tableau A/B test dashboards. See dedicated section: **A/B Test Results Analysis Mode**
- **CJM Funnel Analysis** — analyze funnel conversion rates per stage, detect anomalies, and segment by platform. Invoked by `cjm-research` or directly by the user. See dedicated section: **CJM Funnel Analysis Mode**

Interactive Q&A and Full Report modes follow the same analysis engine (Step 2) but differ in output format. Post-Release, A/B Test, and CJM Funnel modes have specialized workflows described in their dedicated sections below.

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

**1e. Data source acquisition — gather data from all available sources:**

The skill accepts data from multiple sources simultaneously. Ask the user which sources to use:

**Tableau / Analytics dashboards:**

Follow `references/integration-strategy.md` → Tableau row + the "Per-product tool guidance — Tableau" section.

**MCP-first default (recommended path):**
- If `mcp__*__query-datasource` is available → use it for tabular metrics; pass SQL against a published datasource (URL from `local-context.md` → `organization.tableau_datasource_urls` or from context).
- If `mcp__*__get-view-data` is available → when an existing view already has the right filters; pull tabular data directly.
- If `mcp__*__get-view-image` is available → for embedding a dashboard image into a report or presentation.
- If `mcp__*__search-content` is available → when the user named a dashboard but the URL/ID is unknown.
- If Tableau Pulse metric IDs are configured (`organization.tableau_pulse_metric_ids`) → `list-pulse-metrics-from-metric-ids` + `generate-pulse-insight-brief` for health checks.

**Browser fallback** — use ONLY when:
- The Tableau MCP connector is not available in the session (Step 1 of fallback chain has been exhausted), OR
- A view has a complex interactive filter that does not accept API parameters, OR
- The user provided only a URL with no parsing surface.

When using browser: navigate to the dashboard URL, take screenshots using `computer`, read data tables using `get_page_text`. Extract metric values, trends, charts, filters applied, date ranges.

**Mark the source method in the report's Sources section** as `tableau-mcp` or `tableau-web` so the user can audit which method retrieved each datapoint.

**Important**: Tableau data is confidential per `data-policy.md` — do not pass to external services regardless of the retrieval method.

**Google Sheets:**
- Follow integration fallback chain: Google Sheets MCP → registry → browser
- Read cell values, formulas, charts
- If accessing via browser: navigate to sheet URL, read using `get_page_text`

**CSV / XLSX files:**
- Read uploaded files using the Read tool
- For data computation — use Python (pandas, numpy). See Step 2

**Screenshots (PNG, JPG):**
- Read uploaded screenshots using the Read tool (visual interpretation)
- Extract: metric values, chart patterns, trend directions, annotations

**PDF reports:**
- Read uploaded PDFs using the Read tool
- Extract: tables, charts, key figures, conclusions

**Text / conversation:**
- User shares numbers, observations, or context directly in dialogue

**Confluence:**
- Search for previous Product Analysis reports on the same topic using `searchConfluenceUsingCql`
- If found — inform the user and ask: use as baseline for comparison? This enables historical trend analysis
- Also search for relevant context: OKRs, strategy docs, previous decisions

**Figma (for UX-related analysis):**
- If analyzing UX metrics (funnels, conversion, drop-offs) — optionally pull current design context via Figma MCP
- Helps correlate metric changes with UI/UX state

Summarize all gathered data sources back to the user and confirm before proceeding to analysis.

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
- ≥ 2 independent sources (two Tableau workbooks, or Tableau + Glint, or Tableau + GA, or CSV + Tableau)
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

Tag every source: `tableau-mcp`, `tableau-web`, `glint-live`, `ga-snapshot`, `csv-upload`, `screenshot-user`, `pdf-upload`, `confluence-internal`, `jira-internal`, `user-text`.

### Output of Step 1.5

Every metric receives status: ✅ Verified / ⚠️ Caveat / ❌ Blocked.

If Blocked metrics > 0:
- Return to Step 1 to gather additional sources OR
- Inform user explicitly that analysis cannot proceed without resolution

### Step 2 — Analysis engine

**Pre-condition (v0.9.0+):** Step 1.5 (Data Integrity Gate) must be completed. Skip analysis on metrics with status ❌ Blocked. For metrics with status ⚠️ Caveat — inherit the caveat into all downstream outputs (do not silently drop the qualifier).

Apply the appropriate analysis frameworks based on the data and context. See `references/analysis-frameworks.md` for detailed descriptions of each framework.

**2a. Python computation (for CSV/XLSX data):**

When analyzing tabular data from CSV or XLSX files, use Python with pandas and numpy for accurate computation:

```python
import pandas as pd
import numpy as np
```

Compute:
- Aggregations (sum, mean, median, percentiles)
- Period-over-period changes (absolute and %)
- Growth rates, CAGR
- Statistical measures (standard deviation, variance, correlation coefficients)
- Cohort calculations
- Funnel step conversion rates
- Segment comparisons

**Always show computation results** — present calculated values alongside interpretation. Never estimate what can be computed precisely.

**2b. Visual interpretation (for screenshots, charts, dashboards):**

When analyzing visual data (screenshots of dashboards, charts):
- Identify trend directions and inflection points
- Note scale and axis labels
- Identify outliers and anomalies visible in charts
- Cross-reference with any numerical data available
- Note limitations of visual-only analysis (approximate values)

**2c. Full analysis toolkit — apply relevant frameworks:**

| Framework | When to use | Output |
|-----------|------------|--------|
| **Trend analysis** | Always — baseline for any analysis | Direction, magnitude, acceleration/deceleration, inflection points |
| **Anomaly detection** | Always — surface unexpected changes | Spikes, drops, deviations from expected patterns with possible explanations |
| **Cohort analysis** | When user behavior over time matters | Retention curves, behavior differences by user cohort |
| **Funnel analysis** | When analyzing conversion flows | Step-by-step conversion rates, drop-off points, bottleneck identification |
| **Segment comparison** | When different user groups may behave differently | Performance differences by platform, country, user type, traffic source |
| **Metric decomposition** | When a high-level metric needs unpacking | Break metric into components, identify which sub-metrics drive changes |
| **Correlation analysis** | When looking for relationships between metrics | Correlation coefficients, potential causal relationships (with caveats) |
| **Benchmarking** | When external context is needed | Compare metrics against industry standards, competitor data (via WebSearch) |

**2d. Historical comparison:**

If previous Product Analysis reports were found in Confluence (Step 1e):
- Compare current metrics with previously reported values
- Identify trends spanning multiple analysis periods
- Note which previously identified issues have been resolved or persisted
- Track whether previously generated hypotheses were validated

### Step 3 — Structure findings

Organize all analysis results into structured categories:

**3a. Key Trends**
- Direction and magnitude of main metrics
- Whether trends are accelerating, stable, or decelerating
- Context: how current values relate to OKR targets, historical norms, industry benchmarks

**3b. Anomalies and Problems**
- Unexpected metric changes (spikes, drops, pattern breaks)
- For each anomaly: description, magnitude, when it started, possible root causes
- Severity assessment: critical / significant / minor
- Recommended investigation steps

**3c. Growth Opportunities**
- Segments, cohorts, or funnel steps with improvement potential
- Gap analysis: where current performance is below benchmark or target
- Quick wins identified from the data

**3d. Risks**
- Negative trends that may worsen
- Metrics approaching critical thresholds
- Dependencies and external factors

**3e. Correlations and Insights**
- Relationships discovered between metrics
- Patterns that connect multiple data points
- Insights that emerged from cross-referencing sources

### Step 4 — Generate hypotheses from findings

For each significant finding (growth opportunity, problem, anomaly), auto-generate a data-backed hypothesis:

**Hypothesis format:**

```
Name: [short name]

Finding: [what data point or pattern this hypothesis is based on]
Problem: [what problem this addresses]
Solution: [proposed action or experiment]
Expected outcome: [expected metric impact with numbers where possible]
Target metric: [which metric, expected change direction and magnitude]
Validation method: [A/B test / analysis deep-dive / user interviews / etc.]

ICE Score: Impact [X] × Confidence [X] × Ease [X] = [Score]

Supporting data: [specific data points from the analysis]
Risks: [what could go wrong]
```

> **Note:** Use the user's preferred language (`user.language`) for all field labels and content in the output document.

See `references/hypothesis-template.md` for detailed ICE scoring guidelines adapted for data-driven hypotheses.

**Grouping hypotheses:**
- **Data-confirmed** — strong data support, high confidence
- **Data-suggested** — pattern exists but needs more investigation
- **Exploratory** — based on correlations or weak signals, needs validation

Present **ICE summary table** sorted by score descending.

### Step 5 — Interactive discussion

Engage the user in discussing findings and hypotheses:

- **In Interactive Q&A mode**: this step IS the core of the skill — continue answering questions, diving deeper into specific areas, generating additional analysis on request
- **In Full Report mode**: present findings, discuss with the user, iterate on hypotheses, answer follow-up questions before finalizing the report

In both modes:
- Proactively suggest areas worth exploring deeper
- If the user questions a finding — re-examine the data, provide additional evidence or revise the conclusion
- Help prioritize: which findings need immediate action vs. monitoring
- If new data is provided during discussion — incorporate it and update analysis

### Step 6 — Report, save, and feedback

**6a. In Interactive Q&A mode:**

At the end of the session (or when the user signals they're done), provide a concise summary:
- Key findings discussed
- Hypotheses generated (if any)
- Recommended next steps
- Offer to save the summary to Confluence/Notion/Google Docs

**6b. In Full Report mode:**

Generate a comprehensive structured report:

**Report structure:**
1. **Executive Summary** — 3-5 bullet points with the most important findings
2. **Data Sources** — what was analyzed, date ranges, data quality notes
3. **Key Trends** — with charts/tables where data supports it
4. **Anomalies and Problems** — severity-sorted, with root cause analysis
5. **Growth Opportunities** — ranked by potential impact
6. **Risks** — with monitoring recommendations
7. **Correlations and Insights** — cross-metric patterns
8. **Hypotheses** — full hypothesis cards with ICE scores
9. **ICE Summary Table** — sorted by score
10. **Recommended Next Steps** — prioritized action items
11. **Glossary** — explain all terms, metrics, jargon used in the report (same format as Product Research glossary). Use the user's preferred language (`user.language`).
12. **Sources** — all data sources with types marked (Tableau, Google Sheets, CSV, Confluence, Web, screenshot, PDF)

**6c. Publishing — ask via AskUserQuestion:**

> "Would you like to save the analysis report? If yes — which tool should I use?"

- **Confluence** (default) → ask for space and parent page. Title: `[Analysis] Product/Feature — Date`
- **Notion** → ask for workspace and location
- **Google Docs** → ask for folder
- **Other** → user specifies
- **No** → results stay in the dialogue

**Confluence formatting requirements:**
1. Table of Contents (levels 1-6)
2. Dividers between all major sections
3. H1/H2/H3 heading hierarchy
4. Bold key theses, critical numbers, important conclusions
5. Tables for structured data: metrics, hypotheses, ICE scores
6. Sources section with links, marking source types

Publish via appropriate MCP. If unavailable — follow integration fallback chain. As a last resort — generate a local document.

**6d. Summary report and feedback:**

After saving (or if the user decided not to save), provide a structured report:

- **What was done:** brief description of the analysis conducted (scope, data sources, time period)
- **Artifacts created:** links to all created documents (Confluence page, local files, etc.)
- **Key findings:** 3-5 key findings
- **Hypotheses generated:** number of hypotheses generated, top 3 by ICE score
- **Sources used:** list of data sources used (Tableau, Google Sheets, CSV, Confluence, screenshots, etc.)

**After presenting the report, proactively ask for feedback:**

> "Are you satisfied with the analysis results? Would you like to dig deeper into anything or make changes?"

- If the user requests changes — iterate: update the analysis, re-publish, present updated report
- If the user confirms — proceed to the next step

**Self-improvement check** (after corrections are applied and confirmed): follow `references/self-improvement.md` — analyze whether the correction is a pattern, and if so propose a SKILL.md improvement (version bump + CHANGELOG).

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
     skill_version: "0.11.0",
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
   - Update `hypothesis_status`: winner → `validated`, loser → `rejected`, inconclusive → `inconclusive`
   - Set `test_result` and `validated_by` fields
   - If rejected: set `confidence` to 0.2
   - Update `last_reviewed` to today
   - Log: "Updated hypothesis status to {status} based on A/B test results"

4. Display: "Saved to Vault: Analysis/{product}/..."

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

## CJM Funnel Analysis Mode

Specialized mode for analyzing Customer Journey Map funnel data. Segments metrics by funnel stage, detects anomalies against baselines, and returns structured data for `cjm-research` to consume. Can also be invoked directly by the user for quick funnel checks.

### CJM-1. Read CJM configuration

Follow `references/local-context-protocol.md` — Step 0f.

**If CJM Configuration is present:** load funnel template, stages with dashboard URLs, baseline conversions, anomaly thresholds, default settings; continue to CJM-2.

**If CJM Configuration is missing:** present three options via `AskUserQuestion`:

1. **Run Plugin Configurator → Step 11 (full CJM setup)** — ~3-5 min, permanent save.
2. **Quick CJM setup (Recommended)** — collect ad-hoc config now, offer to save it before running analysis. See Quick CJM setup workflow in `references/local-context-protocol.md` Step 0f.
3. **Skip CJM mode** — return early; the user can re-invoke later.

For Quick CJM setup: collect funnel template/stages, dashboard URLs (suggest mapping any URL the user already pasted), thresholds (defaults Warning 10%, Critical 25%), comparison baseline, platforms. Before running CJM-3 onward, ask:

> "I've assembled a CJM configuration for this analysis. Save it to `local-context.md` so I don't have to ask next time?"

If the user accepts → invoke Enrichment Protocol from `references/local-context-protocol.md`, write the CJM Configuration section, and show the changelog. Proceed to CJM-2 regardless of save decision.

Read shared standards from `references/cjm-protocol.md`:
- Anomaly severity thresholds
- Funnel impact calculation formulas
- Health score formula

### CJM-2. Determine scope

**If invoked by `cjm-research`:**
- Use passed context: target stages, time period, baseline, platforms, thresholds
- Skip user questions — all parameters already specified

**If invoked directly by user:**
- Ask via AskUserQuestion:
  - Which funnel stages to analyze? (all / specific)
  - Time period? (last week / month / quarter / custom)
  - Comparison baseline? (previous period / previous year / target)
  - Platforms? (all / specific)

### CJM-3. Load funnel data from dashboards

> **Subagent delegation (large fan-out).** Loading data for many funnel stages is a natural fan-out — delegate per `references/subagent-delegation.md`: batch by stage (or stage × platform), spawn subagents in parallel, each returns a compact structured result (per stage: conversion rate, absolute users, drop-off rate, trend, segment data, source-type marker + link). The main agent aggregates and proceeds to CJM-4 anomaly calculation. `data-policy.md` applies to subagents. Falls back to inline if subagents are unavailable. When invoked by `cjm-research`, honor any batch/parallelism limits passed in context.

For each funnel stage in scope:

1. **Load data for the stage** — follow `references/integration-strategy.md` → Tableau guidance.
   - **MCP-first (default)**:
     - `get-view-data` for tabular metrics of the stage with the relevant filters (time period, platforms)
     - `get-view-image` if the visual is needed for the final report
     - `query-datasource` with SQL if the stage has a configured `datasource_url` and a single query can return conversion/absolute/dropoff in one call
   - **Browser fallback** — only if the MCP connector is not available, or the stage requires complex interactive filters that the API cannot accept. When using browser: navigate to URL, apply filters (time period, platforms), take screenshots, read data tables.
   - **Log the retrieval method** in the report's Sources section as `tableau-mcp` or `tableau-web` for transparency and reproducibility.

2. **Extract per-stage metrics:**
   - **Conversion rate** — percentage of users who complete this stage (relative to previous stage or entry)
   - **Absolute values** — number of users at this stage
   - **Drop-off rate** — percentage lost between this stage and the previous
   - **Trends** — period-over-period change in conversion rate
   - **Segment data** (if available) — breakdown by platform, locale, user type

3. **Handle missing data:**
   - If a dashboard URL is not configured for a stage → note gap, skip stage
   - If dashboard is inaccessible → try browser fallback, note if still inaccessible
   - If data is partially available → use what's available, note limitations

### CJM-4. Calculate anomalies per stage

For each stage, apply anomaly detection per `references/cjm-protocol.md`:

**4a. Deviation calculation:**

```
deviation = ((actual_conversion - baseline_conversion) / baseline_conversion) × 100
```

Where `baseline_conversion` comes from:
- Previous period (default)
- Previous year (if selected)
- Target values (from CJM config)
- Custom baseline (user-specified)

**4b. Severity classification:**

| Severity | Condition | Visual |
|----------|-----------|--------|
| **Critical** | Negative deviation > configured critical threshold (default 25%) | 🔴 |
| **Warning** | Negative deviation between configured warning (default 10%) and critical thresholds | 🟡 |
| **Info** | Negative deviation below warning threshold | ⚪ |
| **Positive** | Positive deviation > 10% (improvement) | 🟢 |

**4c. Trend analysis per stage:**

- Is the anomaly worsening, stable, or improving over the analysis period?
- When did the deviation first appear? (if possible to determine from available data)
- Are there seasonal patterns to consider?

**4d. Cross-stage impact:**

- If a significant anomaly exists in an early stage → downstream stages may be affected
- Note cascading effects: if Stage 1 drops by X%, all subsequent stages see fewer users even if their conversion rates are unchanged

### CJM-5. Compile CJM output

**If returning results to `cjm-research` (delegation):**

Return structured data:

```
Funnel Overview:
- Template: [e-commerce / saas / marketplace / custom]
- Stages analyzed: [N]
- Time period: [start] to [end]
- Comparison baseline: [type]
- Overall funnel conversion: [current] vs [baseline] ([deviation]%)

Stage Data:
| Stage | Name | Baseline Conv | Actual Conv | Deviation | Severity | Trend | Absolute Users |
|-------|------|---------------|-------------|-----------|----------|-------|---------------|

Anomalies:
| Stage | Metric | Baseline | Actual | Deviation | Severity | Since | Trend |

Data Quality Notes:
- [Any gaps, limitations, or data freshness issues]
```

**If invoked directly by user (standalone):**

Present a formatted report:

1. **Funnel Overview** — visual representation with stage conversions and health indicators
2. **Stage-by-Stage Breakdown** — for each stage: metrics, trends, comparison to baseline
3. **Anomalies Detected** — table sorted by severity
4. **Cross-Stage Impact** — cascading effects analysis
5. **Recommendations** — brief next steps for each critical/warning anomaly
6. **Glossary** — explain terms and metrics
7. **Sources** — dashboards and data sources used

Then proceed to Step 6 (Report, save, and feedback) for publishing and feedback.

**After standalone CJM analysis, offer skill chaining:**

> "Funnel analysis complete. Would you like to:"
> - "Run **CJM Research** (hypotheses mode) to generate improvement hypotheses with enrichment from knowledge sources"
> - "Run **CJM Research** (full mode) for a comprehensive analysis with verification and backlog"

---

## Post-Release Analysis Mode

Specialized mode for analyzing how a released feature affected product metrics. The goal is to determine whether the release caused significant or minor changes in product metrics, funnels, and feature-specific metrics.

### PR-1. Gather release context

**Requirements source:**
- Ask the user for the link to the **feature requirements** (Confluence page) or the **Epic key** in Jira
- Read the requirements document to understand: what was changed, which product areas are affected, which metrics were expected to change, which platforms were included

**Jira tasks analysis:**
- Read Epic and child tasks using Jira MCP (`getJiraIssue`, `searchJiraIssuesUsingJql` with JQL: `parent = EPIC-KEY`)
- For each task, determine:
  - **Release date** — when the task was deployed (look for status transitions to "Done", "Released", or deployment date fields)
  - **Feature flag activation date** — when the feature flag was enabled. Look for: FLAG field, comments mentioning flag activation, linked deployment tasks
  - **Platforms** — which platforms were affected (Android, iOS, Web, etc.)
  - **Feature flag name** — from the FLAG field in Jira tasks
- Build a **release timeline**: which changes went live on which platforms and when
- If release dates or flag activation dates are unclear — ask the user to clarify

**Determine analysis period:**
- **Before period** — a comparable period before the release (same duration, accounting for seasonality)
- **After period** — from the release/flag activation date to now (or to the user-specified end date)
- If the feature was released on different platforms at different times — analyze each platform's timeline separately
- Ask the user to confirm the analysis periods

### PR-2. Gather metrics data

> **Subagent delegation (large fan-out).** Gathering many metrics across multiple platforms and before/after periods is a natural fan-out — delegate per `references/subagent-delegation.md`: batch by metric group / platform, spawn subagents in parallel, each returns a compact structured result (per metric: before value, after value, period definition, platform, source-type marker + source link). The main agent aggregates and runs the Step 1.5 Data Integrity Gate before PR-3. `data-policy.md` applies to subagents. Falls back to inline if subagents are unavailable.

**Identify affected metrics:**
- From the requirements document: extract expected metric changes (from the "Metrics" section)
- From the feature scope: identify product-level metrics and funnels that could be affected (even if not explicitly listed in requirements)
- Proactively suggest additional metrics that might be affected based on the nature of the change

**Data acquisition from Tableau / analytics:**

Follow `references/integration-strategy.md` → Tableau guidance.

**MCP-first (default):** for each metric
- If `query-datasource` is available and a `datasource_url` is configured → one SQL query returns before/after period values with platform/date filters in a single call
- If `get-view-data` is available and the view already has the right filters → pull tabular data for both periods
- If a screenshot is needed for the report → `get-view-image` with the appropriate filter params
- If Pulse metrics are configured for affected metrics → `list-pulse-metrics-from-metric-ids` + `generate-pulse-metric-value-insight-bundle`

**Browser fallback:** if the MCP connector is unavailable or you need to drive a complex interactive filter — navigate via `navigate`/`computer`, set filters (product, platform, period), take screenshots, read tables via `get_page_text`.

**Mark each datapoint** in the report's Sources as `tableau-mcp` or `tableau-web`.

Focus on:
- **Product-level metrics**: conversion, revenue, traffic, retention, engagement
- **Feature-level metrics**: specific funnel steps, feature usage, feature-specific KPIs
- **Platform-specific metrics**: compare platforms where the feature was released vs. not yet released (natural control group)

### PR-3. Analyze impact

Compare before vs. after periods for all identified metrics:

- **Absolute change** — metric values before and after
- **Percentage change** — relative change
- **Statistical significance** — is the change within normal variance or statistically significant? Use data from screenshots/tables to assess
- **Platform comparison** — if the feature was rolled out on different platforms at different times, compare:
  - Platforms with the feature ON vs. platforms with the feature still OFF
  - This acts as a natural experiment/control group
- **Correlation with release date** — did the metric change coincide with the release/flag activation, or was the change already in progress?
- **Side effects** — check metrics NOT listed in requirements for unexpected changes (positive or negative)

**Classify each metric change:**

| Classification | Criteria |
|---------------|----------|
| **Significant positive** | Metric improved beyond expected range, likely caused by the release |
| **Minor positive** | Small improvement, possibly related to the release |
| **No change** | Metric stayed within normal variance |
| **Minor negative** | Small degradation, needs monitoring |
| **Significant negative** | Metric degraded notably — requires attention |
| **Inconclusive** | Not enough data or too much noise to determine |

### PR-4. Generate post-release report

**Report structure for post-release analysis:**
1. **Executive Summary** — overall verdict: was the release successful, neutral, or problematic?
2. **Release Context** — what was released, when, on which platforms, links to requirements and Epic
3. **Release Timeline** — table: task, platform, release date, flag activation date
4. **Metrics Impact** — for each metric: before value, after value, change %, classification, interpretation
5. **Funnel Impact** — if relevant: funnel step-by-step comparison before vs. after
6. **Platform Comparison** — if applicable: platform-by-platform analysis
7. **Side Effects** — unexpected metric changes (positive or negative)
8. **Conclusions and Recommendations** — keep flag on / roll back / needs more time / need investigation
9. **Glossary** — explain terms and metrics. Use the user's preferred language (`user.language`).
10. **Sources** — Jira tasks, Confluence requirements, Tableau dashboards used

Then proceed to Step 6 (Report, save, and feedback) for publishing and feedback.

---

## A/B Test Results Analysis Mode

Specialized mode for comprehensive analysis of A/B test outcomes. Can work with user-provided reports or directly with Tableau A/B test dashboards.

### AB-1. Gather test context

**Identify the A/B test:**
- Ask the user which A/B test to analyze
- Gather context:
  - **Test name / feature flag name** — the A/B test name usually equals the feature flag name specified in the FLAG field of the Jira development task. If not provided — search Jira for the feature tasks and read the FLAG field. If still not found — ask the user explicitly
  - **Test hypothesis** — what was being tested and why (read from requirements in Confluence if available)
  - **Test groups** — control, test A, test B (for A/B/C), their descriptions
  - **Traffic split** — percentage split between groups
  - **Success criteria** — which metrics determine success, what thresholds were defined
  - **Expected duration** — how long was the test planned to run
  - **Platforms** — on which platforms the test was running
  - **Start date** — when the test was launched

If requirements exist in Confluence — read them to extract all this context automatically.

### AB-2. Gather test results data

> **Subagent delegation (large fan-out).** The dimension iteration (platform / country / user-type / new-vs-returning) is a natural fan-out — delegate per `references/subagent-delegation.md`: batch by segment / dimension, spawn subagents in parallel, each returns a compact structured result (per segment: primary + secondary metric values per group, sample size, significance if available, source-type marker + link). The main agent aggregates, cross-validates, and runs the Step 1.5 Data Integrity Gate before AB-3. `data-policy.md` applies to subagents. Falls back to inline if subagents are unavailable.

**Data source — ask the user which source to use:**

**Option 1: User-provided reports**
- Read uploaded files (CSV, XLSX, PDF, screenshots) with test results
- Extract: group metrics, sample sizes, confidence intervals, significance levels

**Option 2: Tableau A/B test dashboards**

Follow `references/integration-strategy.md` → Tableau guidance. **MCP-first default:**

1. **Resolve the dashboard:**
   - If `local-context.md` → `product.ab_test_dashboards` has a URL for the test platform → use it.
   - If the URL is not configured → `search-content` with `terms="<feature_flag_name>"` and `filter.contentTypes=["view","workbook"]` to find the right view.
   - If a URL is configured but the view-id is unknown → `list-workbooks` filtered by `contentUrl`.
   - If neither MCP nor configured URL is available — ask the user for the dashboard URL.

2. **Extract the data:**
   - **Primary**: `get-view-data` with the `feature_flag_name` (test name) filter and the relevant date range. Returns tabular data with all metrics and segments at once.
   - **Systematically iterate dimensions**: for each value of platform / country / user-type / new-vs-returning, repeat `get-view-data` with different filters. This replaces "clicking through filters in a browser" with a series of API calls.
   - **For the report/presentation**: `get-view-image` with key filters for embedding in the final document.
   - **If Pulse metrics are tied to the test**: `list-pulse-metrics-from-metric-ids` + `generate-pulse-metric-value-insight-bundle`.

3. **Browser fallback:**
   - If the MCP connector is unavailable, OR the dashboard has a custom JS-driven filter that the API does not accept — navigate via browser as before.
   - Set the test name / feature flag name as the filter parameter.
   - Comprehensively explore all filters, dimensions, and views — try different date ranges, metric breakdowns, segments, views/tabs. Take screenshots and extract tables via `get_page_text`.
   - In the Sources section log "Browser fallback used because: [reason]".

**Mark each datapoint** in the report's Sources as `tableau-mcp` or `tableau-web`.

**Important**: Do not stop at the first view — exhaustively iterate dimensions as described above.

**Option 3: Both** — combine user reports with Tableau dashboard data for cross-validation

### AB-3. Analyze test results

**Core analysis:**
- **Primary metrics** — compare control vs. test group(s) for all success criteria metrics:
  - Absolute values per group
  - Relative difference (Δ%)
  - Statistical significance (p-value, confidence interval if available)
  - Sample size per group — is it sufficient for reliable conclusions?
- **Secondary metrics** — check for side effects on metrics not in success criteria:
  - Revenue metrics
  - Engagement metrics
  - Retention indicators
  - Funnel metrics
  - Any other metrics available in the dashboard
- **Segment analysis** — break down results by available dimensions:
  - Platform (iOS vs Android vs Web)
  - Country / locale
  - User type (new vs returning)
  - User activity level
  - Any other segments available in the dashboard
- **Time dynamics** — how did the test metrics evolve over time?
  - Was there a novelty effect that faded?
  - Did the test group metrics stabilize?
  - Was the test running long enough?

**Assess test validity:**
- Was the sample size sufficient?
- Was the test duration adequate?
- Were there any external factors (holidays, promotions, outages) during the test period?
- Was the traffic split correct and stable?
- Are there signs of selection bias or data quality issues?

### AB-4. Generate A/B test report

**Report structure for A/B test analysis:**
1. **Executive Summary** — verdict: test won / lost / inconclusive, recommended action
2. **Test Setup** — hypothesis, groups, traffic split, duration, platforms, start date
3. **Primary Metrics Results** — table: metric, control value, test value, Δ%, significance, verdict
4. **Secondary Metrics Results** — same format, flagging any significant side effects
5. **Segment Breakdown** — results by key segments (platform, country, user type)
6. **Time Dynamics** — how results evolved over the test duration
7. **Test Validity Assessment** — sample size, duration, external factors, data quality
8. **Conclusions** — for each success criterion: met / not met / inconclusive
9. **Recommendation** — one of:
   - **Roll out to 100%** — test clearly won across all key metrics and segments
   - **Roll out with caveats** — test won overall but some segments show mixed results — specify which to monitor
   - **Extend the test** — results are trending positive but not yet statistically significant — need more time/data
   - **Stop and iterate** — test did not meet success criteria, suggest what to change and re-test
   - **Stop and roll back** — test negatively impacted key metrics
10. **Hypotheses for follow-up** — based on test results, what new hypotheses emerge? (e.g., "Test won on Web but not Mobile — hypothesis: mobile UX needs adjustment")
11. **Glossary** — explain terms and metrics. Use the user's preferred language (`user.language`).
12. **Sources** — Tableau dashboards used, Jira tasks, Confluence requirements, uploaded reports

Then proceed to Step 6 (Report, save, and feedback) for publishing and feedback.

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
- **(v0.9.0+) Source type markers** — every cited number in Sources section tagged (`tableau-mcp` / `tableau-web` / `glint-live` / `ga-snapshot` / `csv-upload` / `screenshot-user` / `pdf-upload` / `confluence-internal` / `jira-internal`)
- **(v0.9.0+) Never declare A/B winner/loser without:** sample-size power check, p-value or confidence interval, holiday-screening pass, segment-level review (Mobile vs Web, country, user-type)

## Additional Resources

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
