# Specialized modes — CJM Funnel Analysis, Post-Release Analysis, A/B Test Results

> Part of `product-analysis`. Loaded on demand when entering the corresponding mode. All three modes honor the Step 1.5 Data Integrity Gate (SKILL.md) and end by returning to Step 6 (report/save/feedback) in `analysis-engine.md`.

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
