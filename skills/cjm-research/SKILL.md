---
name: cjm-research
version: 0.1.0
---
name: cjm-research
version: 0.2.0
description: CJM Research orchestrator — analyze Customer Journey Map funnels, detect anomalies, generate data-backed hypotheses with funnel impact modeling, and produce structured CJM reports. Use when the user asks to "analyze CJM", "CJM research", "funnel research", "find funnel problems", "CJM health check", "schedule health checks", or "compare platforms". Orchestrates product-analysis, product-research, brainstorm-features, schedule, and knowledge-library.
---

# CJM Research

Central orchestrator for the CJM (Customer Journey Map) research pipeline. This skill does NOT perform analysis itself — it delegates to specialized skills and assembles the final report. Supports five modes: anomaly detection, hypothesis generation, full CJM analysis, scheduled health checks, and cross-platform comparison.

## Integration prerequisite

Before starting, read and follow the integration fallback chain in `references/integration-strategy.md`. For this skill, the typical external products needed are:

- **Tableau** — primary source of funnel metrics and dashboards (via product-analysis delegation)
- - **Knowledge Library** — curated UX/product knowledge sources with trust scoring (via knowledge-library skill)
  - - **Confluence** — for reading previous CJM reports, internal experiment results, post-mortems (via knowledge-library and product-research delegation)
    - - **Google Drive** — for research presentations, NPS exports, user feedback (via knowledge-library delegation)
      - - **Jira** — for creating backlog from hypotheses in `full` mode (via feature-task-creator chaining)
        - - **Figma** — for design context when analyzing UX-related funnel stages (via product-research delegation)
          - - **Web** — always available via WebSearch for benchmarks and industry context (via product-research delegation)
            -
            - For each product: check for MCP connector → search MCP registry → fall back to browser.
            -
            - Before gathering any data, also read and comply with `references/data-policy.md`. Confidential data (Tableau metrics, internal analytics, research materials) must NOT be passed to external LLMs or third parties.
            -
            - ## Local context prerequisite
            -
            - **Before starting, follow `references/local-context-protocol.md` (Step 0).** Read `local-context.md`, select the active product, and load all product-specific context. If the file doesn't exist — redirect to Plugin Configurator for initial setup.
            -
            - Key context used by this skill:
            - - `product.name`, `product.key_metrics`, `product.current_okrs` — for analysis focus and goal alignment
              - - `product.cjm_configuration` — **required** for this skill: funnel stages, dashboard URLs, baseline conversions, anomaly thresholds, default analysis settings
                - - `product.cjm_configuration.funnel_template` — funnel template type (e-commerce, SaaS, marketplace, or custom)
                  - - `product.cjm_configuration.platforms` — configured platforms for comparison mode
                    - - `product.cjm_configuration.search_modes` — default knowledge source modes per CJM research mode
                      - - `organization.tableau_base_url` — for dashboard navigation
                        - - `product.confluence_space` — for publishing reports and searching internal sources
                          - - `user.language` — for output language
                            -
                            - **CJM configuration check (mandatory):**
                            - Verify that `cjm_configuration` exists in the active product's context. If missing — redirect to Plugin Configurator (CJM Configuration section) before proceeding. The skill cannot operate without funnel stage definitions.
                            -
                            - ## Modes of operation
                            -
                            - | Mode | Description | Pipeline steps | Output |
                            - |------|-------------|---------------|--------|
                            - | `anomalies` | Anomaly detection only | 1–4 | Short report: anomalies by funnel stage |
                            - | `hypotheses` | Improvement hypotheses | 1–7, 8–9 | Hypotheses with ICE + funnel impact |
                            - | `full` | Complete CJM analysis | 1–12 | Full report + Jira backlog proposal |
                            - | `health-check` | Scheduled periodic check with delta | 1–4 (auto), 12 (delta) | Health summary + delta vs previous + escalation option |
                            - | `comparison` | Cross-platform comparison | 1–4 per platform | Anomaly comparison WEB vs APP |
                            -
                            - ## Pipeline steps
                            -
                            - ### Step 1 — Initialization
                            -
                            - - Read `local-context.md` (mandatory, per `local-context-protocol.md`)
                              - - Read CJM configuration: funnel stages, dashboard URLs, baseline metrics, anomaly thresholds
                                - - If CJM config is missing → redirect to `plugin-configurator` (CJM onboarding)
                                  - - Load funnel template from `references/funnel-templates.md` based on `cjm_configuration.funnel_template`
                                    - - Load severity classification and health score formula from `references/cjm-protocol.md`
                                      -
                                      - Communicate the active template to the user:
                                      -
                                      - > "Starting CJM Research for **[product.name]** using **[template_type]** funnel template with **[N]** stages: [stage names]. Baseline end-to-end conversion: [X%]."
                                        >
                                        > ### Step 2 — Clarify scope with user
                                        >
                                        > Ask via AskUserQuestion:
                                        >
                                        > **2a. Mode selection:**
                                        > > "Which CJM research mode should we use?"
                                        > >
                                        > > - **Anomalies** — quick anomaly scan across funnel stages. Fast, lightweight. Good for weekly monitoring
                                        > > - - **Hypotheses** — find anomalies + generate improvement hypotheses with ICE scoring and funnel impact modeling. Good for quarterly planning
                                        > >   - - **Full** — complete CJM analysis: anomalies → enrichment → hypotheses → verification → risk assessment → prioritized backlog. Good for deep dives and roadmap planning
                                        > >     - - **Health-check** — automated periodic check with delta comparison. Good for scheduled monitoring (chains to `schedule` skill)
                                        > >       - - **Comparison** — cross-platform funnel comparison (e.g., Web vs App). Good for platform-specific optimization
                                        > >         -
                                        > >         - **2b. Scope parameters:**
                                        > >         - - **Target funnel stages:** all stages or specific ones? (list stages from CJM config)
                                        > >           - - **Time period:** what date range to analyze?
                                        > >             - - **Comparison baseline:** previous period / same period last year / OKR target / custom
                                        > >               - - **Platforms:** all configured or specific (for `comparison` mode — select platforms to compare)
                                        > >                 -
                                        > >                 - **2c. Output format:**
                                        > >                 - - **Confluence page** (default) — structured report published to configured space
                                        > >                   - - **Local markdown** — saved to workspace
                                        > >                     - - **Presentation** — chains to `presentation-creator` after report generation
                                        > >                       -
                                        > >                       - **2d. Mode-specific options:**
                                        > >                       - - For `health-check`: confirm schedule → chain to `schedule` skill for recurring execution
                                        > >                         - - For `comparison`: select exactly which platforms to compare
                                        > >                           - - For `full`: confirm that creating Jira backlog is desired (default: propose at end)
                                        > >                             -
                                        > >                             - **2e. Knowledge source modes** (for `hypotheses` and `full` modes):
                                        > >                             -
                                        > >                             - Show the default source combination from CJM config and allow override:
                                        > >                             -
                                        > >                             - | Mode | Default sources |
                                        > >                             - |------|----------------|
                                        > >                             - | `anomalies` | library only (fast) |
                                        > >                             - | `hypotheses` | library + internet |
                                        > >                             - | `full` | library + internet + confluence + gdrive |
                                        > >                             - | `health-check` | library only (fast) |
                                        > >                             - | `comparison` | library + internet |
                                        > >                             -
                                        > >                             - > "Default knowledge sources for [mode]: [sources]. Would you like to adjust?"
                                        > >                               >
                                        > >                               > ### Step 3 — Load CJM data → delegates to `product-analysis` (CJM Funnel Analysis mode)
                                        > >                               >
                                        > >                               > Invoke `product-analysis` in CJM Funnel Analysis mode with the following context:
                                        > >                               >
                                        > >                               > **Pass to product-analysis:**
                                        > >                               > - Dashboard URLs from CJM configuration (per stage)
                                        > >                               > - - Target funnel stages (from Step 2)
                                        > >                               >   - - Time period and comparison baseline (from Step 2)
                                        > >                               >     - - Platforms (from Step 2, or all configured)
                                        > >                               >       - - Anomaly thresholds from CJM configuration
                                        > >                               >         -
                                        > >                               >         - **Receive from product-analysis:**
                                        > >                               >         - - Quantitative funnel data: conversion rates per stage, drop-off rates, trends
                                        > >                               >           - - Raw anomaly list with severity classification (critical / warning / info)
                                        > >                               >             - - Per-stage health scores (0–100)
                                        > >                               >               - - Overall funnel health score
                                        > >                               >                 - - Structured CJM output (both user-facing summary and machine-readable data)
                                        > >                               >                   -
                                        > >                               >                   - Validate received data:
                                        > >                               >                   - - Confirm all requested stages have data
                                        > >                               >                     - - Flag any stages with missing or incomplete data
                                        > >                               >                       - - Present funnel overview to the user with key numbers
                                        > >                               >                         -
                                        > >                               >                         - ### Step 4 — Anomaly detection → uses output from `product-analysis`
                                        > >                               >                         -
                                        > >                               >                         - Process the anomaly data received from product-analysis:
                                        > >                               >                         -
                                        > >                               >                         - **4a. Organize anomalies by funnel stage:**
                                        > >                               >                         - - Group anomalies by stage
                                        > >                               >                           - - Sort within each stage by severity (critical → warning → info)
                                        > >                               >                             - - For each anomaly: stage, metric, baseline value, actual value, deviation %, severity, trend direction
                                        > >                               >                               -
                                        > >                               >                               - **4b. Cross-stage pattern detection:**
                                        > >                               >                               - - Identify cascading anomalies (problem at stage N causing drop at stage N+1)
                                        > >                               >                                 - - Identify correlated anomalies across stages
                                        > >                               >                                   - - Flag anomalies that appear across multiple platforms (for `comparison` mode)
                                        > >                               >                                     -
                                        > >                               >                                     - **4c. Anomaly prioritization:**
                                        > >                               >                                     - - Rank by: severity × funnel position weight (earlier stages have higher weight due to cascading effect)
                                        > >                               >                                       - - Per `references/cjm-protocol.md`: use the funnel impact multiplier formula
                                        > >                               >                                         -
                                        > >                               >                                         - **For modes `anomalies` and `health-check`: skip to Step 11 (Report assembly).**
                                        > >                               >                                         -
                                        > >                               >                                         - ### Step 5 — External enrichment → delegates to `knowledge-library` + `product-research`
                                        > >                               >                                         -
                                        > >                               >                                         - For each significant anomaly (critical and warning severity), gather external context:
                                        > >                               >                                         -
                                        > >                               >                                         - **5a. Knowledge Library search** → invoke `knowledge-library` `search` operation:
                                        > >                               >                                         - - Search by: anomaly's funnel stage category + relevant UX area tags
                                        > >                               >                                           - - Example: anomaly at "Cart / Checkout" stage → search categories `cart-checkout`, `abandonment`, `forms`
                                        > >                               >                                             - - Include sources with `trust_score >= 0.5`
                                        > >                               >                                               - - Receive: matching sources with key insights, trust scores, URLs
                                        > >                               >                                                 -
                                        > >                               >                                                 - **5b. Web research** → invoke `product-research` for each anomaly cluster:
                                        > >                               >                                                 - - Search for: industry benchmarks for the affected metric, competitor approaches, UX best practices
                                        > >                               >                                                   - - If UX Benchmark Research is relevant — invoke product-research in UX Benchmark mode
                                        > >                               >                                                     - - Receive: benchmark data, competitor examples, best practice recommendations
                                        > >                               >                                                       -
                                        > >                               >                                                       - **5c. Baymard search** (if configured in CJM config):
                                        > >                               >                                                       - - Search knowledge-library for sources tagged `baymard` matching anomaly categories
                                        > >                               >                                                         - - If Baymard Premium access is configured — invoke browser-based search (notify user about login requirement)
                                        > >                               >                                                           -
                                        > >                               >                                                           - **5d. Merge external enrichment:**
                                        > >                               >                                                           - - For each anomaly: attach relevant external insights with source attribution
                                        > >                               >                                                             - - Note confidence boost: anomalies supported by Baymard/benchmark evidence get higher confidence in later ICE scoringdescription: CJM Research orchestrator — analyze Customer Journey Map funnels, detect anomalies, generate data-backed hypotheses with funnel impact modeling, and produce structured CJM reports. Use when the user asks to "analyze CJM", "CJM research", "funnel research", "find funnel problems", "CJM health check", or "compare platforms". Orchestrates product-analysis, product-research, brainstorm-features, and knowledge-library.
---

# CJM Research

Central orchestrator for the CJM (Customer Journey Map) research pipeline. This skill does NOT perform analysis itself — it delegates to specialized skills and assembles the final report. Supports five modes: anomaly detection, hypothesis generation, full CJM analysis, scheduled health checks, and cross-platform comparison.

## Integration prerequisite

Before starting, read and follow the integration fallback chain in `references/integration-strategy.md`. For this skill, the typical external products needed are:

- **Tableau** — primary source of funnel metrics and dashboards (via product-analysis delegation)
- **Knowledge Library** — curated UX/product knowledge sources with trust scoring (via knowledge-library skill)
- **Confluence** — for reading previous CJM reports, internal experiment results, post-mortems (via knowledge-library and product-research delegation)
- **Google Drive** — for research presentations, NPS exports, user feedback (via knowledge-library delegation)
- **Jira** — for creating backlog from hypotheses in `full` mode (via feature-task-creator chaining)
- **Figma** — for design context when analyzing UX-related funnel stages (via product-research delegation)
- **Web** — always available via WebSearch for benchmarks and industry context (via product-research delegation)

For each product: check for MCP connector → search MCP registry → fall back to browser.

Before gathering any data, also read and comply with `references/data-policy.md`. Confidential data (Tableau metrics, internal analytics, research materials) must NOT be passed to external LLMs or third parties.

## Local context prerequisite

**Before starting, follow `references/local-context-protocol.md` (Step 0).** Read `local-context.md`, select the active product, and load all product-specific context. If the file doesn't exist — redirect to Plugin Configurator for initial setup.

Key context used by this skill:
- `product.name`, `product.key_metrics`, `product.current_okrs` — for analysis focus and goal alignment
- `product.cjm_configuration` — **required** for this skill: funnel stages, dashboard URLs, baseline conversions, anomaly thresholds, default analysis settings
- `product.cjm_configuration.funnel_template` — funnel template type (e-commerce, SaaS, marketplace, or custom)
- `product.cjm_configuration.platforms` — configured platforms for comparison mode
- `product.cjm_configuration.search_modes` — default knowledge source modes per CJM research mode
- `organization.tableau_base_url` — for dashboard navigation
- `product.confluence_space` — for publishing reports and searching internal sources
- `user.language` — for output language

**CJM configuration check (mandatory):**
Verify that `cjm_configuration` exists in the active product's context. If missing — redirect to Plugin Configurator (CJM Configuration section) before proceeding. The skill cannot operate without funnel stage definitions.

## Modes of operation

| Mode | Description | Pipeline steps | Output |
|------|-------------|---------------|--------|
| `anomalies` | Anomaly detection only | 1–4 | Short report: anomalies by funnel stage |
| `hypotheses` | Improvement hypotheses | 1–7, 8–9 | Hypotheses with ICE + funnel impact |
| `full` | Complete CJM analysis | 1–12 | Full report + Jira backlog proposal |
| `health-check` | Weekly scheduled check | 1–4 (automatic) | Health summary with delta vs previous |
| `comparison` | Cross-platform comparison | 1–4 per platform | Anomaly comparison WEB vs APP |

## Pipeline steps

### Step 1 — Initialization

- Read `local-context.md` (mandatory, per `local-context-protocol.md`)
- Read CJM configuration: funnel stages, dashboard URLs, baseline metrics, anomaly thresholds
- If CJM config is missing → redirect to `plugin-configurator` (CJM onboarding)
- Load funnel template from `references/funnel-templates.md` based on `cjm_configuration.funnel_template`
- Load severity classification and health score formula from `references/cjm-protocol.md`

Communicate the active template to the user:

> "Starting CJM Research for **[product.name]** using **[template_type]** funnel template with **[N]** stages: [stage names]. Baseline end-to-end conversion: [X%]."

### Step 2 — Clarify scope with user

Ask via AskUserQuestion:

**2a. Mode selection:**
> "Which CJM research mode should we use?"

- **Anomalies** — quick anomaly scan across funnel stages. Fast, lightweight. Good for weekly monitoring
- **Hypotheses** — find anomalies + generate improvement hypotheses with ICE scoring and funnel impact modeling. Good for quarterly planning
- **Full** — complete CJM analysis: anomalies → enrichment → hypotheses → verification → risk assessment → prioritized backlog. Good for deep dives and roadmap planning
- **Health-check** — automated periodic check with delta comparison. Good for scheduled monitoring (chains to `schedule` skill)
- **Comparison** — cross-platform funnel comparison (e.g., Web vs App). Good for platform-specific optimization

**2b. Scope parameters:**
- **Target funnel stages:** all stages or specific ones? (list stages from CJM config)
- **Time period:** what date range to analyze?
- **Comparison baseline:** previous period / same period last year / OKR target / custom
- **Platforms:** all configured or specific (for `comparison` mode — select platforms to compare)

**2c. Output format:**
- **Confluence page** (default) — structured report published to configured space
- **Local markdown** — saved to workspace
- **Presentation** — chains to `presentation-creator` after report generation

**2d. Mode-specific options:**
- For `health-check`: confirm schedule → chain to `schedule` skill for recurring execution
- For `comparison`: select exactly which platforms to compare
- For `full`: confirm that creating Jira backlog is desired (default: propose at end)

**2e. Knowledge source modes** (for `hypotheses` and `full` modes):

Show the default source combination from CJM config and allow override:

| Mode | Default sources |
|------|----------------|
| `anomalies` | library only (fast) |
| `hypotheses` | library + internet |
| `full` | library + internet + confluence + gdrive |
| `health-check` | library only (fast) |
| `comparison` | library + internet |

> "Default knowledge sources for [mode]: [sources]. Would you like to adjust?"

### Step 3 — Load CJM data → delegates to `product-analysis` (CJM Funnel Analysis mode)

Invoke `product-analysis` in CJM Funnel Analysis mode with the following context:

**Pass to product-analysis:**
- Dashboard URLs from CJM configuration (per stage)
- Target funnel stages (from Step 2)
- Time period and comparison baseline (from Step 2)
- Platforms (from Step 2, or all configured)
- Anomaly thresholds from CJM configuration

**Receive from product-analysis:**
- Quantitative funnel data: conversion rates per stage, drop-off rates, trends
- Raw anomaly list with severity classification (critical / warning / info)
- Per-stage health scores (0–100)
- Overall funnel health score
- Structured CJM output (both user-facing summary and machine-readable data)

Validate received data:
- Confirm all requested stages have data
- Flag any stages with missing or incomplete data
- Present funnel overview to the user with key numbers

### Step 4 — Anomaly detection → uses output from `product-analysis`

Process the anomaly data received from product-analysis:

**4a. Organize anomalies by funnel stage:**
- Group anomalies by stage
- Sort within each stage by severity (critical → warning → info)
- For each anomaly: stage, metric, baseline value, actual value, deviation %, severity, trend direction

**4b. Cross-stage pattern detection:**
- Identify cascading anomalies (problem at stage N causing drop at stage N+1)
- Identify correlated anomalies across stages
- Flag anomalies that appear across multiple platforms (for `comparison` mode)

**4c. Anomaly prioritization:**
- Rank by: severity × funnel position weight (earlier stages have higher weight due to cascading effect)
- Per `references/cjm-protocol.md`: use the funnel impact multiplier formula

**For modes `anomalies` and `health-check`: skip to Step 11 (Report assembly).**

### Step 5 — External enrichment → delegates to `knowledge-library` + `product-research`

For each significant anomaly (critical and warning severity), gather external context:

**5a. Knowledge Library search** → invoke `knowledge-library` `search` operation:
- Search by: anomaly's funnel stage category + relevant UX area tags
- Example: anomaly at "Cart / Checkout" stage → search categories `cart-checkout`, `abandonment`, `forms`
- Include sources with `trust_score >= 0.5`
- Receive: matching sources with key insights, trust scores, URLs

**5b. Web research** → invoke `product-research` for each anomaly cluster:
- Search for: industry benchmarks for the affected metric, competitor approaches, UX best practices
- If UX Benchmark Research is relevant — invoke product-research in UX Benchmark mode
- Receive: benchmark data, competitor examples, best practice recommendations

**5c. Baymard search** (if configured in CJM config):
- Search knowledge-library for sources tagged `baymard` matching anomaly categories
- If Baymard Premium access is configured — invoke browser-based search (notify user about login requirement)

**5d. Merge external enrichment:**
- For each anomaly: attach relevant external insights with source attribution
- Note confidence boost: anomalies supported by Baymard/benchmark evidence get higher confidence in later ICE scoring

### Step 6 — Internal enrichment → delegates to `knowledge-library` + `product-research`

**6a. Confluence search** → invoke `knowledge-library` `search-confluence` operation:
- Search for: previous CJM reports, experiment results, post-mortems related to affected funnel stages
- Search for: feature requirements that touched affected stages recently
- Receive: internal context, historical experiment data, previous findings

**6b. Google Drive search** → invoke `knowledge-library` `search-gdrive` operation:
- Search for: research presentations, NPS data exports, user feedback analysis
- Receive: user feedback patterns, NPS trends, qualitative insights

**6c. User feedback correlation:**
- From internal sources: extract user complaints, support tickets, feedback themes related to anomaly stages
- Match feedback themes to specific anomalies

**6d. Experiment history:**
- From internal sources: find previous A/B tests and experiments related to affected stages
- Note: which hypotheses were already tested, what results were observed
- Flag anomalies where previous experiments exist — important for verification (Step 10)

**6e. Merge internal enrichment:**
- For each anomaly: attach relevant internal insights with source attribution
- Create a combined enrichment profile: external best practices + internal history + user feedback

### Step 7 — Build hypotheses → delegates to `brainstorm-features` (CJM Hypotheses mode)

Invoke `brainstorm-features` in CJM Hypotheses mode with the following context:

**Pass to brainstorm-features:**
- Anomaly list with severity and funnel stage mapping
- External enrichment data (knowledge library insights, benchmarks, best practices)
- Internal enrichment data (experiment history, user feedback, previous findings)
- Funnel baseline conversions per stage (from CJM config)
- Product context (OKRs, key metrics, constraints)

**Receive from brainstorm-features:**
- Hypotheses in CJM format: Data Trigger + Feedback Match + Heuristic Match + Solution + Expected Impact
- ICE scores with CJM-specific weighting (Impact weighted by funnel position, Confidence boosted by evidence)
- Per-hypothesis: expected conversion lift at target stage
- Categorization: Low-hanging fruit / Structural changes / Business logic changes

**For mode `hypotheses`: proceed to Steps 8–9, then skip to Step 11 (Report assembly).**

### Step 8 — Stage impact calculation → uses output from `brainstorm-features`

For each hypothesis received from brainstorm-features:

**8a. Per-stage impact:**
- Current stage conversion (from CJM config baseline)
- Expected lift % (from hypothesis)
- New stage conversion: `stage_conversion_current × (1 + expected_lift)`
- Absolute impact: `new_stage_conversion - stage_conversion_current`

**8b. Validate reasonableness:**
- Flag hypotheses with unrealistic lift expectations (> 50% lift at a single stage)
- Cross-reference with benchmark data: is the expected lift within industry-observed ranges?
- Adjust confidence score if lift expectation exceeds benchmarks

### Step 9 — End-to-end impact calculation → `cjm-research` internal logic

**9a. Aggregate stage impacts into funnel-wide impact:**
- For each hypothesis: calculate end-to-end conversion assuming all other stages remain constant
- Formula: multiply conversion rates across all stages, replacing target stage with new_stage_conversion
- Delta: `new_overall_conversion - current_overall_conversion` = absolute end-to-end impact

**9b. Combined impact scenarios:**
- If multiple hypotheses target different stages: calculate combined end-to-end impact
- Group hypotheses by stage to show total potential improvement per stage
- Calculate "best case" (all hypotheses succeed) and "conservative case" (only high-confidence hypotheses)

**9c. Ranking and categorization:**
- Rank hypotheses by end-to-end impact (descending)
- Apply categorization labels:
  - **Low-hanging fruit**: high Ease (≥7), moderate Impact — quick wins
  - **Structural changes**: high Impact, lower Ease (≤5) — requires significant development
  - **Business logic changes**: involves pricing, policies, rules — requires stakeholder alignment
- Present **prioritization matrix** combining ICE score + end-to-end impact + category

### Step 10 — Independent verification → `cjm-research` internal logic (subagent)

**This step is mandatory for `full` mode and uses a subagent for objectivity.**

The main agent generated hypotheses; the verifier challenges them.

**10a. Launch verification subagent** with context:
- Full hypothesis list with all details
- Raw anomaly data from product-analysis
- Internal enrichment data (experiment history, user feedback)
- External enrichment data (benchmarks, best practices)

**10b. Verification checklist** (per `references/verification-checklist.md`):

For each hypothesis, the subagent evaluates:

1. **Anomaly confirmation**: Does the anomaly persist after additional segmentation (by platform, user segment, traffic source)?
2. **Evidence alignment**: Do internal sources support or contradict the hypothesis?
3. **Experiment history**: Were similar hypotheses tested before? What were the results?
4. **Benchmark plausibility**: Is the expected impact within industry-observed ranges?
5. **Alternative explanations**: Could external factors (seasonality, campaigns, outages) explain the anomaly without requiring the proposed solution?
6. **Implementation risk**: Are there technical dependencies or constraints not accounted for?

**10c. Verification labels:**
- **confirmed** — strong evidence support, anomaly verified, no contradicting data
- **needs-more-data** — partial evidence, some gaps, recommend additional investigation before implementation
- **contradicted** — evidence contradicts the hypothesis, previous experiments failed, or anomaly explained by external factors

**10d. Subagent output:**
- Verification status for each hypothesis + justification + recommendations
- Updated confidence scores based on verification findings
- List of hypotheses recommended for removal or deferral

### Step 11 — Risk assessment → `cjm-research` internal logic

For each verified hypothesis (status: `confirmed` or `needs-more-data`):

**11a. Risk categories:**
- **Technical risk**: implementation complexity, dependencies, migration needs, performance impact
- **Business risk**: revenue impact if hypothesis fails, competitive implications, compliance concerns
- **UX risk**: user confusion, learning curve, accessibility regression, negative impact on other flows

**11b. Dependency analysis:**
- Map dependencies between hypotheses (hypothesis A requires hypothesis B to be implemented first)
- Identify shared dependencies (multiple hypotheses require the same backend change)

**11c. Cannibalization analysis:**
- Check if implementing hypothesis A invalidates or diminishes the impact of hypothesis B
- Flag conflicting hypotheses that cannot both be implemented

**11d. Risk-adjusted prioritization:**
- Combine ICE score + end-to-end impact + risk assessment into final priority score
- Group into implementation phases:
  - **Phase 1 (Now)**: Low-hanging fruit with confirmed status
  - **Phase 2 (Next)**: High-impact structural changes with confirmed status
  - **Phase 3 (Later)**: Needs-more-data hypotheses requiring additional validation
  - **Deferred**: Contradicted or high-risk hypotheses

### Step 12 — Report assembly → `cjm-research`

Assemble the final report in the format chosen by the user (Step 2c). Report structure depends on the mode:

**Anomaly Report** (modes: `anomalies`, `health-check`):
```
1. Summary — key findings in 3-5 bullet points
2. Funnel Overview — visualization of funnel with current conversion rates
3. Anomalies by Stage — table: stage, metric, baseline, actual, deviation, severity
4. Cross-Stage Patterns — cascading and correlated anomalies
5. Recommendations — brief next steps
6. Sources — data sources with types marked
```

**Hypothesis Report** (mode: `hypotheses`):
```
1. Summary — key findings and top hypotheses
2. Funnel Overview — visualization with anomaly markers
3. Anomalies — condensed anomaly table
4. Hypothesis Table — trigger, solution, ICE score, funnel impact, category
5. Funnel Impact Model — per-stage and end-to-end impact visualization
6. Prioritization Matrix — low-hanging / structural / business logic
7. Next Steps — recommended actions
8. Sources — all sources with types and trust scores
```

**Full CJM Report** (mode: `full`):
```
1. Executive Summary — 3-5 key findings
2. Funnel Overview — visualization with health scores per stage
3. Stage-by-Stage Analysis — for each stage: anomalies + enrichment data
4. Hypotheses with Verification Status — confirmed / needs-more-data / contradicted
5. Funnel Impact Model — per-stage and end-to-end impact
6. Risk Assessment — technical, business, UX risks per hypothesis
7. Prioritized Backlog — phased implementation plan (Phase 1 / 2 / 3 / Deferred)
8. Recommended Roadmap — timeline with dependencies
9. Glossary — explain all terms, metrics, jargon (in user.language)
10. Sources — all data sources with types, trust scores, links
```

**Health-Check Summary** (mode: `health-check`, scheduled):
```
1. Period — date range analyzed
2. Funnel Health Score — overall score (0-100)
3. Delta vs Previous Check — comparison with last saved health-check
4. New Anomalies — anomalies not present in previous check
5. Resolved Anomalies — anomalies from previous check that are no longer present
6. Top-3 Attention Items — most critical current issues
7. Link to Full Report — if critical anomalies detected, propose full CJM research
```

For `health-check` mode: save snapshot to `workspace/knowledge-library/health-checks/[date].md` for future delta comparison.

**Cross-Platform Comparison** (mode: `comparison`):
```
1. Summary — key cross-platform findings
2. Platform A Funnel — full funnel overview for platform A
3. Platform B Funnel — full funnel overview for platform B
4. Comparison Table — side-by-side metrics per stage
5. Platform-Specific Anomalies — issues unique to each platform
6. Shared Anomalies — issues present across platforms
7. Per-Platform Recommendations — targeted optimization suggestions
8. Sources — data sources per platform
```

**Publishing — ask via AskUserQuestion:**

> "Would you like to save the CJM research report? If yes — which tool should I use?"

- **Confluence** (default) → ask for space and parent page. Title: `[CJM Research] Product — Mode — Date`
- **Notion** → ask for workspace and location
- **Google Docs** → ask for folder
- **Local markdown** → save to workspace
- **No** → results stay in the dialogue

**Confluence formatting requirements:**
1. Table of Contents (levels 1-6)
2. Dividers between all major sections
3. H1/H2/H3 heading hierarchy
4. Bold key findings, critical numbers, important conclusions
5. Tables for structured data: anomalies, hypotheses, ICE scores, funnel impact
6. Color coding for severity: critical (red), warning (yellow), info (blue)
7. Sources section with links, marking source types and trust scores

Publish via appropriate MCP. If unavailable — follow integration fallback chain. As a last resort — generate a local document.

**Summary report and feedback:**

After saving (or if the user decided not to save), provide a structured report:

- **What was done:** brief description of the CJM research (mode, scope, stages analyzed, time period)
- **Artifacts created:** links to all created documents (Confluence page, local files, etc.)
- **Key findings:** 3-5 key findings
- **Hypotheses generated:** number of hypotheses, top 3 by end-to-end impact (for `hypotheses` and `full` modes)
- **Funnel health:** overall health score and stage-by-stage summary
- **Sources used:** list of knowledge sources used (Tableau, Knowledge Library, Confluence, Web, etc.)

**After presenting the report, proactively ask for feedback:**

> "Are you satisfied with the CJM research results? Would you like to dig deeper into any stage or revise hypotheses?"

- If the user requests changes — iterate: update the analysis, re-publish, present updated report
- If the user confirms — proceed to skill chaining

**Self-improvement check** (after corrections are applied and confirmed):

If the user requested corrections during review, analyze whether the skill's algorithm can be improved. Follow the full protocol in `references/self-improvement.md`. In short:
1. Analyze the root cause of the error — is this a pattern or a one-off?
2. If it's a pattern — propose a specific improvement to the skill's conditions
3. If the user agrees — update the SKILL.md, re-package the plugin, and provide the updated file

## Skill chaining

After completing the CJM research, **always** propose transitioning to the next logical skill based on the mode and findings:

> "CJM Research is complete. What's next? Based on the results, I can:"

**Propose based on mode and findings:**

| From mode | Proposal |
|-----------|----------|
| Any mode | → `presentation-creator` — create a presentation with CJM research results (auto-suggest type: "Product Review / CJM" or "Project / CJM Status") |
| `hypotheses`, `full` | → `requirements-creator` — write feature requirements for the top hypothesis |
| `full` | → `feature-task-creator` — create Jira backlog from prioritized hypotheses |
| `full` | → `diagram-prototyper` — visualize the funnel, CJM map, or hypothesis impact model |
| `health-check` | → `cjm-research` in `full` mode — if critical anomalies were detected |
| `comparison` | → `cjm-research` in `hypotheses` mode — for the platform with more anomalies |

**Context passing to next skill:**
- Pass the full research context: report link (if published), key findings, hypotheses, data sources, funnel data
- For `presentation-creator`: pass funnel data, anomalies, hypotheses, impact model, health scores
- For `requirements-creator`: pass selected hypothesis with full enrichment data, expected impact, risk assessment
- For `feature-task-creator`: pass the prioritized backlog (Phase 1/2/3) with hypothesis details
- For `diagram-prototyper`: pass funnel structure, conversion rates, anomaly markers, hypothesis impact data

If the user declines — end the workflow gracefully.

## Quality standards

- **Delegation principle**: this skill orchestrates, it does not perform analysis. All data gathering and analysis is delegated to specialized skills
- **Data integrity**: always validate data received from delegated skills before proceeding to next step
- **Transparency**: clearly communicate which skill is being invoked at each step and what data is being passed
- **Objectivity**: Step 10 verification uses a subagent specifically to challenge hypotheses from an independent perspective
- **Traceability**: every finding, hypothesis, and recommendation must be traceable to a specific data source
- **Confidentiality**: follow `references/data-policy.md` strictly — no internal data to external services
- Use Ukrainian or English based on user's language preference (`user.language`)

## Additional Resources

- **`references/local-context-protocol.md`** — Step 0: how to read and use local-context.md (mandatory before any skill execution)
- **`references/cjm-protocol.md`** — anomaly severity levels, health score formula, funnel impact calculations
- **`references/funnel-templates.md`** — funnel stage templates by product type (e-commerce, SaaS, marketplace, custom)
- **`references/verification-checklist.md`** — checklist for Step 10 independent verification
- **`references/ice-framework.md`** — ICE scoring guidelines (extended with CJM-specific weighting in brainstorm-features)
- **`references/integration-strategy.md`** — MCP → Registry → Browser fallback chain
- **`references/data-policy.md`** — data confidentiality policy
- **`references/self-improvement.md`** — self-improvement protocol
