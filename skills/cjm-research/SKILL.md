---
name: cjm-research
version: 0.1.0
description: Conduct CJM (Customer Journey Map) research — detect funnel anomalies, generate improvement hypotheses, and build prioritized backlogs. Use when the user asks to "analyze CJM", "find funnel anomalies", "CJM research", "funnel health check", "compare platforms", "CJM hypotheses", or needs end-to-end funnel analysis with enrichment from knowledge sources.
---

# CJM Research

Central orchestrator for Customer Journey Map research. Manages the full CJM pipeline: loads funnel data, detects anomalies, enriches with internal and external knowledge sources, generates improvement hypotheses with funnel impact calculation, and assembles structured reports.

This skill does NOT perform analysis itself — it delegates to specialized skills and assembles the final output.

## Prerequisites

Before starting, read and follow these shared references:
- **`references/local-context-protocol.md`** — Step 0: read `local-context.md`, select active product, load product-specific context
- **`references/cjm-protocol.md`** — shared CJM standards: anomaly severity levels, funnel impact formulas, health score formula, verification checklist
- **`references/funnel-templates.md`** — standard funnel stage templates (e-commerce, SaaS, marketplace, custom)
- **`references/integration-strategy.md`** — MCP → Registry → Browser fallback chain
- **`references/data-policy.md`** — data confidentiality: internal analytics stay internal, external searches use public info only
- **`references/persistent-storage.md`** — persistent storage protocol (`~/.grow-pm/`)

Key context used by this skill:
- `product.name`, `product.platforms`, `product.locales` — for scoping the analysis
- CJM Configuration section — funnel template, stages, dashboards, thresholds, default settings
- Knowledge Library section — search modes, Baymard access, Confluence spaces, Google Drive folders
- `user.language` — for output language

## Modes of Operation

| Mode | Description | Pipeline steps | Estimated time | Output |
|------|-------------|---------------|----------------|--------|
| **anomalies** | Find funnel anomalies only | 1–4 | 2–5 min | Short report: anomalies per funnel stage |
| **hypotheses** | Generate improvement hypotheses | 1–9 | 10–15 min | Hypotheses with ICE + funnel impact |
| **full** | Comprehensive CJM analysis | 1–12 | 20–30 min | Full report + optional backlog |
| **health-check** | Scheduled funnel health check | 1–4 (automated) | 2–5 min | Health summary with delta vs previous |
| **comparison** | Cross-platform comparison | 1–4 per platform | 10–15 min | Side-by-side anomaly comparison |

---

## Pipeline Steps

### Step 1 — Initialize

**1a. Local context (mandatory):**

Follow `references/local-context-protocol.md` — Step 0:
- Read `local-context.md` from `~/.grow-pm/` (primary) or legacy locations
- Select active product (if multiple products configured)
- If `local-context.md` not found → chain to `plugin-configurator` in Onboarding mode

**1b. CJM configuration check (mandatory):**

Follow `references/local-context-protocol.md` — Step 0f:
- Read CJM Configuration section from `local-context.md`
- Load: funnel template, stages with dashboard URLs, baseline conversions, anomaly thresholds, default analysis settings
- If CJM Configuration is missing → inform user and chain to `plugin-configurator` in Update mode:
  > "CJM is not configured for this product yet. Let's set it up — it takes ~2 minutes."

**1c. Knowledge Library availability check (optional):**

Follow `references/local-context-protocol.md` — Step 0g:
- Check if `~/.grow-pm/knowledge-library/` exists and `library.md` is initialized
- If available → note the number of sources and configured search modes
- If not available → note this; enrichment steps will use web search only

**1d. Load previous health-check (for health-check and full modes):**

If mode is `health-check` or `full`:
- Check `~/.grow-pm/knowledge-library/health-checks/` for previous snapshots
- Load the most recent one for delta comparison
- If no previous check exists → this will be the baseline

### Step 2 — Clarify scope with user

Ask via AskUserQuestion (skip for automated `health-check` — use defaults):

**2a. Mode selection:**

> "Which CJM research mode should we use?"

| Mode | Best for |
|------|----------|
| **Anomalies** | Quick funnel health check — find problems fast (2–5 min) |
| **Hypotheses** | Generate improvement ideas with ICE scores and funnel impact (10–15 min) |
| **Full** | Deep analysis with verified hypotheses, impact model, and backlog (20–30 min) |
| **Health-check** | Set up recurring automated funnel monitoring |
| **Comparison** | Compare funnel performance across platforms (Web vs App, etc.) |

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

> "Where should I publish the report?"

- Confluence page (default)
- Notion page
- Google Docs
- Local markdown file
- Presentation (chains to diagram-prototyper)

**2f. Mode-specific settings:**

- For `health-check`: confirm recurring schedule → chain to `schedule` skill if user wants automation
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

Receive from `product-analysis`:
- Quantitative funnel data: conversion rates per stage, absolute values
- Trends: period-over-period changes per stage
- Raw data for anomaly detection

For `comparison` mode: invoke `product-analysis` separately for each platform being compared.

### Step 4 — Anomaly detection

**Continue delegation to `product-analysis` (CJM mode).**

`product-analysis` applies anomaly detection per funnel stage:

1. **Calculate deviation** from baseline for each stage:
   ```
   deviation = ((actual - baseline) / baseline) × 100
   ```

2. **Classify severity** per `references/cjm-protocol.md`:

   | Severity | Condition | Action |
   |----------|-----------|--------|
   | **Critical** | deviation > 25% (negative) | Immediate attention required |
   | **Warning** | deviation 10–25% (negative) | Monitor and investigate |
   | **Info** | deviation < 10% (negative) | Note for context |
   | **Positive** | deviation > 10% (positive) | Highlight as improvement |

3. **Structure output:**

   For each anomaly:
   - Stage name and position in funnel
   - Metric affected (conversion rate, drop-off, absolute value)
   - Baseline value vs actual value
   - Deviation percentage
   - Severity classification
   - Trend direction (worsening / improving / stable)

**Mode branching after Step 4:**

- For `anomalies` mode → **go to Step 11** (assemble Anomalies Report)
- For `health-check` mode → **go to Step 11** (assemble Health-Check Summary)
- For `comparison` mode → **go to Step 11** (assemble Comparison Report) after running Steps 3–4 for all selected platforms
- For `hypotheses` and `full` modes → **continue to Step 5**

### Step 5 — Enrich with WORLD sources

**Delegate to `knowledge-library` (search modes: library + internet + baymard) and `product-research`.**

**5a. Knowledge Library — local search:**

Call `knowledge-library` in Search mode:
- Query: for each detected anomaly, search by funnel stage category and relevant tags
- Example: anomaly in Cart/Checkout → search categories `cart-checkout`, tags `abandonment, checkout, forms`
- Trust threshold: minimum 0.5 (configurable)
- Return: matching sources with key insights and trust scores

**5b. Web search for benchmarks:**

Delegate to `product-research` for targeted web research:
- Search for industry benchmarks related to each anomaly (e.g., "e-commerce checkout abandonment rate benchmark 2026")
- Search for competitor approaches to the affected funnel stages
- Search for UX best practices relevant to detected problems
- **Important:** Per `data-policy.md`, only use public product names and generic feature descriptions in external searches — never send internal analytics data

**5c. Baymard Premium (if configured):**

If Baymard access is configured in Knowledge Library settings:
- Call `knowledge-library` in Search Baymard mode
- Search for Baymard guidelines matching each anomaly's funnel stage
- Baymard sources get high trust scores (base 0.90)

**5d. Collate world sources:**

Merge all results into a structured enrichment dataset:
- Group sources by funnel stage
- Rank by trust score within each stage
- Note source type (library / web / baymard) for the final report's Sources section

### Step 6 — Enrich with INTERNAL sources

**Delegate to `knowledge-library` (search modes: confluence + gdrive).**

**6a. Confluence search:**

Call `knowledge-library` in Search Confluence mode:
- Search configured Confluence spaces for: previous CJM research, A/B test results, post-mortems, feature experiment outcomes related to the affected funnel stages
- Extract: experiment results, decisions, metric changes

**6b. Google Drive search:**

Call `knowledge-library` in Search Google Drive mode:
- Search configured folders for: NPS reports, user feedback exports, research presentations, strategy documents
- Extract: relevant findings, quotes, data points

**6c. Merge internal enrichment:**

Combine Confluence and Google Drive findings:
- Match to specific anomalies where possible
- Note: user feedback that correlates with a detected anomaly is strong evidence for hypothesis building
- All internal data stays internal per `data-policy.md`

### Step 7 — Build hypotheses

**Delegate to `brainstorm-features` in CJM Hypotheses mode.**

Pass context:
- Structured anomaly list (from Step 4)
- World enrichment data (from Step 5) — benchmarks, best practices, Baymard guidelines
- Internal enrichment data (from Step 6) — experiment results, user feedback, previous research
- Funnel stage configuration (from CJM config)

Receive from `brainstorm-features`:
- Hypothesis list with:
  - **Data Trigger** — the detected anomaly (stage, metric, deviation)
  - **Feedback Match** — correlated user feedback or support tickets
  - **Heuristic Match** — matching UX best practice from Knowledge Library
  - **Solution** — proposed change
  - **Expected Impact** — estimated conversion lift for the affected stage
  - **ICE Score** — Impact × Confidence × Ease (with CJM-specific weighting)
  - **Category** — Low-hanging fruit / Structural changes / Business logic changes

For `hypotheses` mode → **continue to Step 8, then go to Step 11** (skip Steps 10–11 risk assessment)

### Step 8 — Calculate impact per hypothesis

**Delegate to `brainstorm-features` (CJM mode) or calculate internally.**

For each hypothesis, calculate per-stage impact:

```
new_stage_conversion = current_stage_conversion × (1 + expected_lift_percent / 100)
```

Per `references/cjm-protocol.md`, apply stage position multipliers for ICE Impact scoring:

| Stage position | Multiplier | Rationale |
|---------------|-----------|-----------|
| Stage 1 (entry) | ×1.5 | Improvements at entry affect all downstream stages |
| Stage 2 | ×1.3 | High leverage — feeds middle funnel |
| Stage 3 | ×1.1 | Important but narrower audience |
| Stage 4+ | ×1.0 | Baseline — affects only late-stage users |

### Step 9 — Calculate impact on overall conversion

**Internal logic (cjm-research).**

Aggregate per-stage impacts into end-to-end funnel impact:

```
current_overall_conversion = stage_1_conv × stage_2_conv × ... × stage_N_conv
new_overall_conversion = new_stage_1_conv × new_stage_2_conv × ... × new_stage_N_conv
absolute_impact = new_overall_conversion - current_overall_conversion
relative_impact = (absolute_impact / current_overall_conversion) × 100
```

**Rank hypotheses by:**
1. Overall conversion impact (primary)
2. ICE score (secondary)
3. Category — Low-hanging fruit first for quick wins

**Categorize hypotheses:**

| Category | Criteria | Typical timeline |
|----------|----------|-----------------|
| **Low-hanging fruit** | High Ease (7+), moderate Impact | 1–2 sprints |
| **Structural changes** | High Impact, lower Ease, requires significant dev work | 1–2 quarters |
| **Business logic changes** | Requires stakeholder alignment, pricing/policy changes | Cross-functional initiative |

For `hypotheses` mode → **go to Step 12** (assemble report)

### Step 10 — Independent verification

**Internal logic (cjm-research) — uses subagent for objectivity.**

For each hypothesis from Step 7, run verification checks per `references/cjm-protocol.md`:

**10a. Data validity:**
- Does the anomaly still hold after segmenting by platform / locale / user type?
- Is the sample size sufficient for the detected deviation?
- Is the data fresh (collected within the analysis period)?

**10b. Internal evidence cross-check:**
- Do Confluence/GDrive sources support or contradict the hypothesis?
- Were there previous A/B tests that already tested a similar solution?
- If tested before — what were the results? (If negative — hypothesis needs strong new evidence)

**10c. Confidence calibration:**
- If Baymard/industry benchmark supports the hypothesis → Confidence +1–2 points
- If internal experiment supports → Confidence +2–3 points
- If contradicting evidence found → Confidence -2–3 points, flag for discussion

**10d. Dependency and cannibalization analysis:**
- Would implementing hypothesis A invalidate the conditions for hypothesis B?
- Are there hypotheses that must be implemented in a specific order?
- Flag dependent pairs

**10e. Assign verification status:**

| Status | Meaning |
|--------|---------|
| **Confirmed** | Multiple evidence sources support, no contradictions |
| **Needs more data** | Promising but insufficient evidence — suggest specific data to gather |
| **Contradicted** | Evidence found against the hypothesis — recommend not pursuing or re-framing |

### Step 11 — Risk assessment

**Internal logic (cjm-research).**

For each confirmed or needs-more-data hypothesis:

**11a. Technical risk:**
- Implementation complexity
- Dependencies on other systems/teams
- Performance impact potential

**11b. Business risk:**
- Revenue impact if hypothesis is wrong
- User segment affected (new vs returning, high-value vs low-value)
- Reversibility — can we roll back easily? (Feature flag vs permanent change)

**11c. UX risk:**
- Could the change negatively affect other parts of the user journey?
- Is the change consistent with the overall product design language?
- Are there accessibility implications?

**11d. Compile risk matrix:**

| Hypothesis | Technical | Business | UX | Overall | Mitigation |
|------------|-----------|----------|-----|---------|------------|
| [Name] | Low | Medium | Low | Medium | Feature flag, 10% rollout |
| ... | ... | ... | ... | ... | ... |

### Step 12 — Report assembly and publishing

**Internal logic (cjm-research).**

Assemble the final report based on the selected mode. Use the user's preferred language (`user.language`).

---

### Report Format — Anomalies (modes: `anomalies`)

```
1. Summary (3–5 key findings)
2. Funnel Overview (visual: stages with conversion rates and health indicators)
3. Anomalies by Stage
   | Stage | Metric | Baseline | Actual | Deviation | Severity | Trend |
4. Recommendations (brief next steps for each critical/warning anomaly)
5. Glossary (explain all terms, metrics, jargon)
6. Sources (data sources used: Tableau, Google Sheets, etc.)
```

### Report Format — Health-Check Summary (mode: `health-check`)

```
1. Period (date range analyzed)
2. Funnel Health Score (0–100, calculated per cjm-protocol.md)
3. Delta vs Previous Check (score change, direction)
4. New Anomalies (detected since last check)
5. Resolved Anomalies (present last time but no longer anomalous)
6. Top 3 Attention Items (highest severity, actionable)
7. Link to Full Report (offer to run full mode if critical anomalies found)
```

**Health Score calculation** per `references/cjm-protocol.md`:
- Weighted average of stage health scores (0–100 scale)
- Stage weights: Entry (15%), Middle stages (25% each), Conversion (35%)
- Penalties: Critical (-30), Warning (-15), Info (-3), Positive (+5)

**Save health-check snapshot:**
- Save to `~/.grow-pm/knowledge-library/health-checks/[date].md`
- Include: health score, all anomalies, stage data
- This enables delta comparison in future health-checks

### Report Format — Hypotheses (mode: `hypotheses`)

```
1. Summary (top 3 hypotheses, overall funnel impact potential)
2. Funnel Overview (stages with anomaly indicators)
3. Anomalies (condensed table from Step 4)
4. Hypotheses Table
   | # | Name | Trigger | Solution | ICE | Stage Impact | Category |
5. Prioritization Matrix
   - Low-hanging fruit (table)
   - Structural changes (table)
   - Business logic changes (table)
6. Funnel Impact Model
   - Per-hypothesis stage impact
   - Cumulative end-to-end impact
7. Next Steps (recommended actions for top hypotheses)
8. Glossary
9. Sources (library, web, Baymard, Confluence, GDrive — marked by type)
```

### Report Format — Full CJM Report (mode: `full`)

```
1. Executive Summary (key findings, overall health score, top recommendations)
2. Funnel Overview (visual with stage metrics)
3. Stage-by-Stage Analysis
   For each stage:
   - Current metrics and trends
   - Detected anomalies
   - Enrichment findings (world + internal sources)
   - Related hypotheses
4. Hypotheses with Verification Status
   | # | Name | Data Trigger | Solution | ICE | Verification | Stage Impact |
5. Impact Model
   - Per-hypothesis: stage conversion current → new, absolute lift
   - End-to-end: current overall → projected overall, total impact
6. Risk Assessment (risk matrix per hypothesis)
7. Prioritized Backlog
   - Phase 1 (quick wins): low-hanging fruit sorted by ICE
   - Phase 2 (structural): structural changes sorted by impact
   - Phase 3 (strategic): business logic changes with stakeholder requirements
8. Recommended Roadmap (phases with timelines)
9. Glossary
10. Sources (all sources used, grouped by type)
```

### Report Format — Cross-Platform Comparison (mode: `comparison`)

```
1. Summary (key differences between platforms)
2. Platform A Funnel (stages, conversion rates, anomalies)
3. Platform B Funnel (stages, conversion rates, anomalies)
4. Side-by-Side Comparison
   | Stage | Platform A Conv | Platform B Conv | Delta | Significance |
5. Platform-Specific Anomalies (present in one platform only)
6. Shared Anomalies (present in both platforms)
7. Recommendations per Platform
8. Glossary
9. Sources
```

---

## Publishing

**12a. Ask via AskUserQuestion (if not already specified in Step 2e):**

> "Report is ready. Where should I publish it?"

- **Confluence** (default) → ask for space and parent page. Title: `[CJM] Product — Mode — Date`
- **Notion** → ask for workspace and location
- **Google Docs** → ask for folder
- **Local markdown** → save to workspace folder
- **No** → results stay in the dialogue

**Confluence formatting requirements:**
1. Table of Contents (levels 1-6)
2. Dividers between all major sections
3. H1/H2/H3 heading hierarchy
4. Bold key theses, critical numbers, important conclusions
5. Tables for all structured data: anomalies, hypotheses, ICE scores, impact model
6. Info/Note/Warning panels for critical findings
7. Sources section with links, marking source types

Publish via appropriate MCP. If unavailable — follow `references/integration-strategy.md` fallback chain. As a last resort — generate a local document.

**12b. Summary report and feedback:**

After publishing, provide a structured summary:

- **What was done:** mode used, stages analyzed, time period, platforms
- **Artifacts created:** links to published reports
- **Key findings:** top 3-5 findings
- **Hypotheses generated:** count, top 3 by ICE score (if applicable)
- **Health score:** current score and delta vs previous (if applicable)
- **Sources used:** list by type (Tableau, Knowledge Library, Web, Baymard, Confluence, GDrive)

**After presenting the report, proactively ask for feedback:**

> "Are you satisfied with the CJM analysis? Would you like to dig deeper into any stage, adjust hypotheses, or change the scope?"

- If the user requests changes — iterate: adjust analysis, re-publish, present updated report
- If the user confirms — proceed to skill chaining

**12c. Context enrichment offer:**

If the analysis discovered new data that could improve `local-context.md`:
- Updated baseline conversions from fresh dashboard data
- New competitors identified during web research
- Updated metric values

Follow the Enrichment Protocol from `plugin-configurator`:
1. Inform user what was discovered
2. Ask: "Would you like to update local-context.md?"
3. If yes — update the appropriate sections, show changelog

**Self-improvement check** (after corrections are applied and confirmed):

If the user requested corrections during review, follow the full protocol in `references/self-improvement.md`:
1. Analyze the root cause — is this a pattern or a one-off?
2. If it's a pattern — propose a specific improvement to the skill
3. If the user agrees — update SKILL.md, bump version, update CHANGELOG.md

---

## Skill Chaining (post-report)

After report assembly, offer the user next actions based on the mode:

**Always offer:**
- → **Diagram & Prototype Creator** — "Create a visual funnel diagram or infographic from this report"

**From `hypotheses` and `full` modes:**
- → **Requirements Creator** — "Write detailed requirements for the top hypothesis"
- → **Feature Task Creator** — "Create Jira tasks for the prioritized backlog"

**From `full` mode additionally:**
- → **Diagram & Prototype Creator** — "Create a presentation deck from this report"

**From `health-check` mode:**
- → **CJM Research (full mode)** — "Run a full analysis" (if critical anomalies detected)

**From `comparison` mode:**
- → **CJM Research (hypotheses mode)** — "Generate hypotheses for [specific platform]"

When chaining:
- Pass the full analysis context: report link (if published), anomalies, hypotheses, enrichment data, funnel configuration
- The receiving skill incorporates CJM results without re-analyzing

---

## Automated Health-Check Protocol

When `health-check` mode is configured for automation:

1. **Setup:** During Step 2, if user selects health-check mode:
   - Ask about frequency: weekly (recommended), bi-weekly, monthly
   - Ask about notification: where to publish results (Confluence page / local file)
   - Chain to `schedule` skill to create recurring task
   - Schedule task invokes `cjm-research` in `health-check` mode with saved parameters

2. **Execution (automated):**
   - Skip Step 2 (use saved parameters)
   - Run Steps 1, 3, 4 with default settings from CJM config
   - Load previous health-check for delta comparison
   - Assemble Health-Check Summary
   - Save snapshot to `~/.grow-pm/knowledge-library/health-checks/[date].md`
   - Publish to configured destination

3. **Escalation:**
   - If any **Critical** anomaly detected → highlight in report, suggest full mode
   - If health score dropped by >10 points vs previous check → flag as urgent

---

## Quality Standards

- Always cite data sources and values — never present estimates as facts
- Clearly distinguish: data (from dashboards) / insights (from analysis) / hypotheses (generated)
- For every anomaly — specify: which stage, which metric, exact deviation, comparison period
- For every hypothesis — specify: which anomaly triggered it, which evidence supports it, confidence level
- Note data quality issues: missing stages, incomplete data, small sample sizes
- Use the user's preferred language (`user.language`) for all output
- Follow `data-policy.md` strictly — internal analytics never leave the session
- When comparing periods — always state which periods and the data freshness

## Additional Resources

- **`references/cjm-protocol.md`** — anomaly severity, funnel impact formulas, health score, verification checklist
- **`references/funnel-templates.md`** — standard funnel templates by product type
- **`references/persistent-storage.md`** — `~/.grow-pm/` storage protocol
- **`references/local-context-protocol.md`** — Step 0: reading and using local-context.md
- **`references/integration-strategy.md`** — MCP → Registry → Browser fallback chain
- **`references/data-policy.md`** — data confidentiality rules
- **`references/self-improvement.md`** — self-improvement protocol
