# Analysis engine — data acquisition (1e) + Steps 2–6 (Interactive Q&A / Full Report)

> Part of `product-analysis`. Loaded on demand for Interactive Q&A and Full Report modes. The mode map, Data Integrity Gate, Vault Save, and chaining live in SKILL.md.

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

---

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
