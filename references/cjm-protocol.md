# CJM Protocol

This document defines shared standards for all CJM-related skills and modes. Referenced by `cjm-research`, `product-analysis` (CJM mode), and `brainstorm-features` (CJM mode).

> **Dependencies**: Also read `data-policy.md` (confidentiality) and `integration-strategy.md` (MCP fallback chain) before any CJM operation.

---

## Anomaly Severity Levels

Every anomaly detected during CJM analysis MUST be classified by severity:

| Severity | Deviation from baseline | Color | Action required |
|----------|------------------------|-------|-----------------|
| **Critical** | > 25% negative deviation | Red | Immediate investigation recommended |
| **Warning** | 10–25% negative deviation | Yellow | Monitor and investigate in next cycle |
| **Info** | < 10% deviation (positive or negative) | Gray | Note for context, no immediate action |
| **Positive** | > 10% positive deviation | Green | Investigate what caused improvement |

**Deviation formula:**
```
deviation_% = ((actual - baseline) / baseline) × 100
```

**Baseline selection** (user configures during CJM setup, defaults below):
- `previous_period` — same metric from the previous time period (default)
- `previous_year` — same metric from the same period last year (seasonality-adjusted)
- `target` — metric target from local-context.md (if set)
- `custom` — user-specified baseline value

---

## Funnel Impact Calculation

### Per-stage impact

For each hypothesis that targets a specific funnel stage:

```
new_stage_conversion = current_stage_conversion × (1 + expected_lift_%)
stage_impact_absolute = new_stage_conversion - current_stage_conversion
```

### End-to-end funnel impact

The overall conversion is the product of all stage conversions:

```
current_overall = stage_1_conv × stage_2_conv × ... × stage_N_conv
new_overall = stage_1_conv × ... × improved_stage_conv × ... × stage_N_conv
overall_impact = new_overall - current_overall
overall_impact_% = ((new_overall - current_overall) / current_overall) × 100
```

### Impact weighting by funnel position

Earlier stages affect more users, so their impact is naturally amplified through the funnel. The ICE Impact score should reflect this:

| Stage position | Impact multiplier (for ICE) |
|---------------|---------------------------|
| Stage 1 (entry) | ×1.5 — affects all users |
| Stage 2 | ×1.3 — affects most users |
| Stage 3 | ×1.1 — affects engaged users |
| Stage 4+ (end) | ×1.0 — affects converting users |

These multipliers are applied to the ICE Impact score, not to the funnel impact calculation itself.

---

## Health Score Formula

The Funnel Health Score (0–100) provides a single number for quick health assessment.

### Per-stage health

```
stage_health = 100 - (severity_penalty × weight)
```

Severity penalties per anomaly:
- Critical: -30 points
- Warning: -15 points
- Info: -3 points
- Positive: +5 points (capped at +10 per stage)

If a stage has multiple anomalies, penalties are summed (minimum 0, maximum 100 per stage).

### Overall health score

```
overall_health = weighted_average(stage_health_1, stage_health_2, ..., stage_health_N)
```

Stage weights (configurable, defaults):

| Stage position | Default weight |
|---------------|---------------|
| First stage (entry) | 15% |
| Middle stages | 25% each (split evenly) |
| Last stage (conversion) | 35% |

Last stage weighs most because it directly reflects revenue/goal completion.

### Health score interpretation

| Score | Status | Meaning |
|-------|--------|---------|
| 90–100 | Healthy | No significant anomalies, funnel performing well |
| 70–89 | Attention | Some warnings, monitor closely |
| 50–69 | Concern | Multiple warnings or critical anomaly, investigation recommended |
| 0–49 | Critical | Multiple critical anomalies, immediate action required |

---

## Cross-Platform Comparison Methodology

When comparing CJM across platforms (e.g., Web vs App):

### Step 1 — Normalize metrics

Platforms may have different absolute conversion rates. Compare:
- Relative change (% delta from each platform's own baseline)
- Trend direction (improving vs declining)
- Anomaly severity distribution

Do NOT directly compare absolute conversion rates across platforms unless the user explicitly asks.

### Step 2 — Classify anomalies

| Category | Definition |
|----------|-----------|
| **Shared anomaly** | Same metric anomaly detected on both platforms (same direction, similar severity) |
| **Platform-specific** | Anomaly detected on one platform only |
| **Divergent** | Same metric, opposite trend across platforms (e.g., improving on Web, declining on App) |

### Step 3 — Prioritize

1. **Divergent anomalies** — highest priority, investigate root cause of difference
2. **Shared critical anomalies** — systemic issue, likely backend or business logic
3. **Platform-specific critical** — platform UX or technical issue
4. **Shared warnings** — monitor, lower urgency
5. **Platform-specific warnings** — lowest priority

---

## Hypothesis Verification Checklist

Used by the verification subagent in Step 10 of `cjm-research`:

For each hypothesis, the verifier must check:

| Check | Question | If fails |
|-------|----------|----------|
| **Data validity** | Does the anomaly hold after segmenting by platform, locale, user type? | → `needs-more-data` |
| **Internal evidence** | Do internal sources (experiments, feedback, NPS) support or contradict? | → `contradicted` if strong counter-evidence |
| **Prior experiments** | Has something similar been tested before? What was the result? | → `contradicted` if prior test failed |
| **Confidence calibration** | Is the expected lift realistic given industry benchmarks? | → adjust expected lift, note in report |
| **Dependency check** | Does this hypothesis depend on or conflict with another hypothesis? | → flag dependency |
| **Data freshness** | Is the underlying data recent enough to be actionable? | → `needs-more-data` if data is stale |

Verification statuses:
- `confirmed` — all checks passed, high confidence
- `needs-more-data` — hypothesis plausible but insufficient evidence
- `contradicted` — counter-evidence found, reconsider or deprioritize

---

## Data Source Priority

When gathering CJM data, prefer sources in this order:

1. **Tableau/GA dashboards** — primary quantitative source (funnel metrics, conversion rates)
2. **Internal experiments** — A/B test results with statistical significance
3. **User feedback** — support tickets, reviews, NPS verbatims (qualitative)
4. **Knowledge Library** — curated external benchmarks and best practices
5. **Web search** — fresh industry data, competitor analysis
6. **External LLMs** — Deep Research for broad patterns (public data only per `data-policy.md`)

Always cite the source type in the final report.

---

## Report Sections — Standard Structure

All CJM reports (regardless of mode) should include these sections where applicable:

| Section | Required in modes | Content |
|---------|------------------|---------|
| Summary | all | 3-5 sentence executive summary |
| Funnel Overview | all | Visual representation of current funnel state |
| Anomalies | all | Table: stage, metric, baseline, actual, deviation, severity |
| Enrichment | hypotheses, full | What was found from external and internal sources |
| Hypotheses | hypotheses, full | Table: trigger, solution, ICE, funnel impact, category |
| Verification | full | Status per hypothesis with rationale |
| Risk Assessment | full | Technical, business, UX risks per hypothesis |
| Impact Model | hypotheses, full | Per-stage and end-to-end impact calculation |
| Prioritized Backlog | full | Categorized: low-hanging fruit / structural / business logic |
| Roadmap | full | Phased implementation recommendation |
| Sources | all | All sources with type labels |
| Glossary | full | Terms and abbreviations used in the report |
