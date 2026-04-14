---
name: product-analysis
version: 0.5.0
description: Analyze product data — dashboards, tables, reports, metrics — to find trends, anomalies, growth opportunities, and generate data-backed hypotheses. Use when the user asks to "analyze metrics", "review a dashboard", "find anomalies", "explain this data", "post-release analysis", "analyze A/B test results", or "CJM funnel analysis".
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

## Workflow

### Step 1 — Initialization and data acquisition

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
- Follow integration fallback chain: Tableau MCP → search MCP registry → browser fallback
- When using browser: navigate to the dashboard URL, take screenshots using `computer`, read data tables using `get_page_text`
- Extract: metric values, trends, charts, filters applied, date ranges
- **Important**: Tableau data is confidential per `data-policy.md` — do not pass to external services

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

### Step 2 — Analysis engine

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

**Self-improvement check** (after corrections are applied and confirmed):

If the user requested corrections during review, analyze whether the skill's algorithm can be improved to prevent similar issues in the future. Follow the full protocol in `references/self-improvement.md`. In short:
1. Analyze the root cause of the error — is this a pattern or a one-off?
2. If it's a pattern — propose a specific improvement to the skill's conditions
3. If the user agrees — update the SKILL.md, re-package the plugin, and provide the updated file

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

Follow `references/local-context-protocol.md` — Step 0f:
- Read CJM Configuration section from `local-context.md`
- Load: funnel template, stages with dashboard URLs, baseline conversions, anomaly thresholds
- If CJM Configuration is missing → inform user, offer to chain to `plugin-configurator`

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

For each funnel stage in scope:

1. **Navigate to the stage's dashboard URL** (from CJM config)
   - Follow `references/integration-strategy.md` fallback chain: Tableau MCP → browser
   - When using browser: navigate to URL, apply filters (time period, platforms), take screenshots, read data tables

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

**Identify affected metrics:**
- From the requirements document: extract expected metric changes (from the "Метрики" section)
- From the feature scope: identify product-level metrics and funnels that could be affected (even if not explicitly listed in requirements)
- Proactively suggest additional metrics that might be affected based on the nature of the change

**Data acquisition from Tableau / analytics:**
- Navigate to relevant Tableau dashboards via browser (follow integration fallback chain)
- Set filters for: the correct product, platforms, date ranges (before vs. after)
- Take screenshots and extract data for both periods
- Focus on:
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

**Data source — ask the user which source to use:**

**Option 1: User-provided reports**
- Read uploaded files (CSV, XLSX, PDF, screenshots) with test results
- Extract: group metrics, sample sizes, confidence intervals, significance levels

**Option 2: Tableau A/B test dashboards**
- Navigate to the appropriate A/B test dashboard via browser:
  - Use the A/B test dashboard URLs configured in `local-context.md` (see `local-context.example.md` for setup)
  - Select the appropriate dashboard based on the platform where the test was conducted
  - If `local-context.md` is not configured or dashboards are not specified — ask the user for the dashboard URL
- **Set the test name / feature flag name** as the filter parameter in the dashboard
- **Comprehensive parameter exploration** — systematically go through ALL available filters, dimensions, and views in the dashboard:
  - Try different date ranges
  - Try different metric breakdowns
  - Try different segments (platform, country, user type, new vs returning, etc.)
  - Try different views/tabs available in the workbook
  - Take screenshots of each meaningful view
  - Extract data tables where possible using `get_page_text`
- **Important**: Do not stop at the first view — explore the dashboard comprehensively to capture all relevant data dimensions

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

## Additional Resources

- **`references/analysis-frameworks.md`** — detailed description of each analysis framework with examples
- **`references/hypothesis-template.md`** — ICE scoring guidelines adapted for data-driven hypotheses
- **`references/cjm-protocol.md`** — CJM anomaly severity, funnel impact formulas, health score formula
- **`references/funnel-templates.md`** — standard funnel stage templates by product type
- **`references/local-context-protocol.md`** — Step 0: how to read and use local-context.md (mandatory before any skill execution)
- **`references/integration-strategy.md`** — MCP → Registry → Browser fallback chain (shared across all skills)
- **`references/data-policy.md`** — data confidentiality policy: what data can and cannot be shared externally (mandatory reading before any data gathering)
- **`references/self-improvement.md`** — self-improvement protocol: how to learn from user corrections and improve skill algorithms
