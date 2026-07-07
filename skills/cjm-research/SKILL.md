---
name: cjm-research
version: 0.7.0
description: Conduct CJM (Customer Journey Map) research — detect funnel anomalies, generate improvement hypotheses, and build prioritized backlogs. Use when the user asks to "analyze CJM", "find funnel anomalies", "CJM research", "funnel health check", "compare platforms", "CJM hypotheses", or needs end-to-end funnel analysis with enrichment from knowledge sources. Українською: "проаналізувати CJM", "знайти аномалії у воронці", "CJM дослідження", "health-check воронки", "порівняти платформи", "CJM гіпотези". Do NOT use for standalone dashboard/metric analysis without the research pipeline (use product-analysis) or for pure idea generation without funnel research (use brainstorm-features).
---

# CJM Research

Central orchestrator for Customer Journey Map research. Manages the full CJM pipeline: loads funnel data, detects anomalies, enriches with internal and external knowledge sources, generates improvement hypotheses with funnel impact calculation, and assembles structured reports.

This skill does NOT perform analysis itself — it delegates to specialized skills and assembles the final output.

## Prerequisites

Before starting, read and follow these shared references:
- **`references/local-context-protocol.md`** — Step 0: read `local-context.md`, select active product, load product-specific context
- **`references/cjm-protocol.md`** — shared CJM standards: anomaly severity levels, funnel impact formulas, health score formula, verification checklist, Data Integrity Gate reference
- **`references/data-integrity-protocol.md`** — **MANDATORY (v0.4.0+)** — 5 universal gate checks for any cited metric, executed at Step 3.5
- **`references/funnel-templates.md`** — standard funnel stage templates (e-commerce, SaaS, marketplace, custom)
- **`references/integration-strategy.md`** — MCP → Registry → Browser fallback chain
- **`references/data-policy.md`** — data confidentiality: internal analytics stay internal, external searches use public info only
- **`references/persistent-storage.md`** — persistent storage protocol (`~/.grow-pm/`)
- **`references/vault-protocol.md`** — vault context search, artifact storage, and lifecycle management
- **`references/vault-schema.md`** — vault artifact schema, metadata structure, and query syntax

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
- `subtype: {inferred from mode — "funnel" | "comparison" | "health-check" | null}`
- `product_id: {from local-context.md active product}`
- `language: {from local-context.md → user.language or product.default_language}`

Run Steps T-1 → T-5 via the `template-library` helper routines. Render and append `<!-- template: {template_id} version: {version} -->` at the end of the report.

For `health-check` mode (automated), use the top-ranked template silently regardless of `templates.preference` to avoid prompting in background runs.

If no template applies → fall back to `cjm-builtin-funnel`; if that's also missing, use the skill's internal report structure.

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
- Load the most recent one for delta comparison
- If no previous check exists → this will be the baseline

**1e. Detect vault level (for all modes):**

Follow `references/vault-protocol.md` — Step 0.5:
- Detect vault_level from `local-context.md` (L0, L1, L2, L3)
- If vault_level > L0 → note that vault context search will be available in Step 1.5
- If vault_level = L0 or vault sync_mode = "off" → vault steps will be skipped

### Step 1.5: Vault Context Search (Optional)

> Requires: `references/vault-protocol.md` → Step 0.5

IF vault_level > L0 (detected during Step 1e):

1. Search vault for relevant prior artifacts:
   - Types: `cjm-analysis`, `cjm-health-check`, `funnel-anomaly`, `ab-test-results`, `hypothesis`
   - Product: active product
   - Tags: CJM-related tags from user's request
   - Status: `active`, `draft`
   - Sort: `created DESC`, limit: 10

2. IF results found:
   - Display: "Found {N} related CJM artifacts in your knowledge base:"
   - Show: title, type, date, health_score (if health-check), key tags
   - Ask: "Use as context for this analysis? [Yes / Select specific / Skip]"

3. IF user accepts:
   - Read full content of selected artifacts
   - Use as baseline context:
     - Previous health scores → compare with current
     - Previous anomalies → check if still present or resolved
     - Tested hypotheses → mark as already tested, show results
     - Prior CJM analyses → identify trends across time
   - Note in report header: "This analysis is informed by {N} previous artifacts from Vault"

4. IF user skips OR no results → continue normally

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

### Step 3.5 — Data Integrity Gate (MANDATORY, v0.4.0+)

**Internal logic (cjm-research).** Executes before Step 4 (Anomaly detection). Every metric from Step 3 passes 5 universal gate checks per `references/data-integrity-protocol.md`. Without passing the gate, the metric MUST NOT be used in anomaly detection or reporting.

**Why this exists:** historic incidents where uncritical citation of raw data points produced cascading errors (incomplete-period extrapolation, Week-1 holiday zriz cited as YoY trend, derived claims propagated without re-verification, missing inline-period annotation). The gate prevents these patterns systematically. See `data-integrity-protocol.md` for the full incident catalog and anti-pattern examples.

**3.5.a — Period/Context Completeness Check:**

For each timeseries metric loaded in Step 3:
- Verify Tableau/dashboard extract date against the last data point in the series
- If `last_point_date + period_length > extract_date` → the last point is INCOMPLETE
- Action: normalize on full period (raw × full_days / actual_days), OR exclude the partial point from analysis, OR wait for end-of-period
- **This is a blocker for PoP comparison.** Do not compare an incomplete period against complete periods without normalization.

**3.5.b — Seasonal/Cyclical Screening:**

Detect overlap of analysis period with known holiday/seasonal windows (per `cjm-protocol.md` → Holiday Screening Windows):

- Ukraine default: Week 1 (Jan 1-7), Mar 7-8, Easter ± 1 week, May 1-3, BF week, Dec 22-31
- Global products: also Chinese NY, Diwali, Ramadan, US Thanksgiving / BF, Boxing Day

If an anomaly week aligns with a holiday window:
- ⚠️ FLAG: "Holiday-affected period — interpretation is week-specific, not a trend"
- Search for sustained pattern in non-holiday weeks
- For YoY comparison: never cite a holiday week as a year-trend; always read the full YoY table

**3.5.c — Multi-Source Cross-Validation:**

For every critical CR / GMV / Order / Revenue / Retention metric:
- Require ≥ 2 independent sources (two different Tableau workbooks, or Tableau + Glint, or Tableau + GA, etc.)
- Variance tolerance ≤ 15% between sources
- Variance > 15% → ⚠️ FLAG, resolve before reporting

**Special case — extreme values (drop > 25% or lift > 50% or sensational claim):**
- Auto-promote to ≥ 3 sources (not 2)
- Methodology change check (read DT-* / DATA-* tickets in the analysis period)
- Reference period analysis (full YoY/PoP table, never single cell)

**3.5.d — Period Definition Lock + Inline Annotation:**

Pre-compute inline-annotation strings for every metric per Gate Check 4 of `data-integrity-protocol.md`. Examples:

- `Catalog CR 0.99% (12mo rolling, 1.05.2025 → 7.05.2026)`
- `Listing GMV +20% YoY (May 2025 → May 2026, weeks 18-19, non-holiday window)`
- `Brand pages ~48K sessions/month (normalized to 30 days from 7-day extract, May 2026)`

Methodology section at the top of the report is **not sufficient** — readers copy individual numbers into Slack, slides, follow-up docs without surrounding context.

**3.5.e — Source Type Marker:**

Tag every source with type per Gate Check 5 of `data-integrity-protocol.md`:

- Internal: `tableau-mcp`, `tableau-web`, `glint-live`, `ga-snapshot`, `csv-upload`, `screenshot-user`, `confluence-internal`, `jira-internal`
- This enables audit trail in the final Sources section

**Output of Step 3.5:**

Every metric receives a status:
- ✅ **Verified** — passed all 5 checks; ready for Step 4 (Anomaly detection)
- ⚠️ **Caveat** — passed with limitations (normalized, holiday-affected, single-source pending cross-validation); inherit caveat into downstream steps and report
- ❌ **Blocked** — failed a critical check; either return to Step 3 to gather additional sources, or inform user that analysis cannot proceed without resolution

**If Blocked metrics > 0:**
- Halt the pipeline before Step 4 OR
- Inform user explicitly: "Cannot proceed with anomaly detection — N metrics are blocked. Need: [list of required resolutions]"

**Reference sources catalog:** Use `cjm-protocol.md` → Recommended reference sources catalog (or `local-context.md` → `data_sources_catalog` for product-specific mappings) to identify which secondary source to query for each metric.


### Steps 4–11 — Research pipeline

Anomaly detection (Step 4), WORLD enrichment (5), INTERNAL enrichment (6), hypothesis building (7), per-hypothesis impact (8), overall-conversion impact (9), independent verification (10), and risk assessment (11) live in `references/cjm-pipeline.md` (skill-local). Read it after the Step 3.5 gate passes. Mode map (which steps run per mode) — see Modes of Operation above.

### Step 12 — Report assembly and publishing

**Internal logic (cjm-research).**

Assemble the final report based on the selected mode. Use the user's preferred language (`user.language`).

> For a worked, high-quality reference of the target shape and rigor, load `references/examples/funnel-anomaly-report-example-v1.md` on demand. It is a generic exemplar (few-shot) showing period annotation on every metric, Data Integrity caveats, and funnel-impact math — match its rigor, not its exact wording.

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

2. Build artifact:
   ```
   vault_save({
     type: determined_type,
     product: active_product,
     skill: "cjm-research",
     skill_version: "0.7.0",
     tags: [detected funnel stages, anomaly types, platforms analyzed],
     content: full_report_markdown,
     related: [previous health checks used, related hypotheses, source data references],
     extra_frontmatter: {
       health_score: calculated_score (if health-check mode),
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

4. Display: "Saved to Vault: CJM/{product}/..."

---

## Skill Chaining (post-report)

After report assembly, offer the user next actions based on the mode:

**Always offer:**
- → **Diagram & Prototype Creator** — "Create a visual funnel diagram or infographic from this report"

**From `hypotheses` and `full` modes:**
- → **Requirements Creator** — "Write detailed requirements for the top hypothesis"
- → **Task Creator** — "Create Jira tasks for the prioritized backlog"

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

## Quality Standards

- Always cite data sources and values — never present estimates as facts
- Clearly distinguish: data (from dashboards) / insights (from analysis) / hypotheses (generated)
- For every anomaly — specify: which stage, which metric, exact deviation, comparison period
- For every hypothesis — specify: which anomaly triggered it, which evidence supports it, confidence level
- Note data quality issues: missing stages, incomplete data, small sample sizes
- Use the user's preferred language (`user.language`) for all output
- Follow `data-policy.md` strictly — internal analytics never leave the session
- When comparing periods — always state which periods and the data freshness
- **(v0.4.0+) Inline period annotation MANDATORY** — every cited metric in TL;DR, Executive Summary, tables, bullets carries inline annotation per Gate Check 4 of `data-integrity-protocol.md` (`12mo rolling`, `YoY`, `snapshot`, `normalized`, etc.). Methodology section at the top is not sufficient — readers copy individual numbers into Slack and slides.
- **(v0.4.0+) Caveat propagation** — Step 3.5 ⚠️ Caveat metrics surface their qualifier in the final report (e.g., "single-source pending cross-validation", "normalized from N-day extract", "holiday-affected period")
- **(v0.4.0+) Anomaly disclosure** — for any reported anomaly: source count (≥ 2; ≥ 3 for extreme), period definition, holiday-screening status, methodology change check status
- **(v0.4.0+) Source type markers** — every cited number in Sources section tagged (`tableau-mcp` / `tableau-web` / `glint-live` / `ga-snapshot` / `confluence-internal`)

## Additional Resources

- **`references/cjm-pipeline.md`** (skill-local) — Steps 4–11: anomalies, enrichment, hypotheses, impact, verification, risk
- **`references/cjm-reports.md`** (skill-local) — per-mode report formats, publishing, automated health-check protocol
- **`references/examples/funnel-anomaly-report-example-v1.md`** (skill-local) — worked golden anomaly-report exemplar with period annotation + impact math (few-shot; load on demand in Step 8)

- **`references/data-integrity-protocol.md`** — **MANDATORY (v0.4.0+)** — 5 universal gate checks for any cited metric
- **`references/cjm-protocol.md`** — anomaly severity, funnel impact formulas, health score, verification checklist, holiday windows, anomaly verification checklist, reference sources catalog
- **`references/funnel-templates.md`** — standard funnel templates by product type
- **`references/persistent-storage.md`** — `~/.grow-pm/` storage protocol
- **`references/local-context-protocol.md`** — Step 0: reading and using local-context.md
- **`references/integration-strategy.md`** — MCP → Registry → Browser fallback chain
- **`references/data-policy.md`** — data confidentiality rules
- **`references/self-improvement.md`** — self-improvement protocol
- **`references/vault-protocol.md`** — vault context search, artifact storage, and lifecycle management
- **`references/vault-schema.md`** — vault artifact schema, metadata structure, and query syntax
