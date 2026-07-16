# cjm-hypotheses-mode.md

> Skill-local reference for `brainstorm-features` → Step 3C (CJM Hypothesis Generation). Loaded on demand when the mode activates — invoked by `cjm-research` (Situation D) or by an explicit user request for CJM-based brainstorming. Content moved verbatim from the skill core in v0.10.0 (monolith-refactor pattern); the core keeps the activation conditions and the return contract summary.

**3C-1. Generate hypotheses from anomalies:**

For each anomaly (prioritize by severity: Critical first, then Warning):

```
Name: [short descriptive name]

Data Trigger: [anomaly details — stage, metric, deviation from baseline]
Feedback Match: [correlated user feedback, support tickets, NPS verbatims — from internal enrichment]
Heuristic Match: [matching UX best practice or benchmark — from Knowledge Library with trust score]

Solution: [proposed change to address the anomaly]
Expected Impact: [estimated conversion lift % for the affected stage]
Target Metric: [stage conversion rate, expected change direction and magnitude]
Validation Method: [A/B test / feature flag / user interviews / analytics deep-dive]

ICE Score: Impact [X] × Confidence [X] × Ease [X] = [Score]
PRO/ROI: [annual % return per `references/roi-frameworks.md` — or "n/a: <why the $ effect is unknowable>"]

Funnel Stage Impact: current [X]% → projected [Y]% (+Z%)

Benchmarks: [supporting evidence with trust scores — from Knowledge Library and web]
Risks: [what could go wrong, negative side effects]
```

> Use the user's preferred language (`user.language`) for all field labels and content.

**3C-2. ICE scoring with CJM-specific weighting:**

Enhanced ICE scoring for CJM hypotheses:

**Impact** — weighted by funnel stage position (per `references/cjm-protocol.md`):
| Stage position | Multiplier | Rationale |
|---------------|-----------|-----------|
| Stage 1 (entry) | ×1.5 | Improvements at entry affect all downstream stages |
| Stage 2 | ×1.3 | High leverage — feeds middle funnel |
| Stage 3 | ×1.1 | Important but narrower audience |
| Stage 4+ | ×1.0 | Baseline — affects only late-stage users |

**Confidence** — boosted by evidence quality:
- Baymard/academic evidence supports hypothesis → +1–2 points
- Internal A/B test confirmed similar approach → +2–3 points
- Only blog/article evidence → +0 (no boost)
- Contradicting internal evidence → -2–3 points

**Ease** — based on technical complexity, team capacity, dependencies

**3C-3. Funnel impact calculation:**

For each hypothesis, calculate the per-stage conversion impact:
```
new_stage_conversion = current_stage_conversion × (1 + expected_lift_percent / 100)
```

Calculate end-to-end funnel impact if all hypotheses in a stage are implemented:
```
stage_combined_lift = 1 - product(1 - lift_i for each hypothesis_i in stage)
new_stage_conversion = current × (1 + stage_combined_lift)
```

**3C-4. Categorize hypotheses:**

| Category | Criteria | Typical timeline |
|----------|----------|-----------------|
| **Low-hanging fruit** | Ease ≥ 7, moderate Impact, can be A/B tested quickly | 1–2 sprints |
| **Structural changes** | High Impact, Ease < 5, requires significant development | 1–2 quarters |
| **Business logic changes** | Requires stakeholder alignment, pricing/policy changes | Cross-functional initiative |

**3C-5. Present results:**

Show hypotheses grouped by category, sorted by ICE score within each group.

Present ICE summary table:
| # | Name | Stage | Trigger | ICE | Stage Impact | Category |
|---|------|-------|---------|-----|-------------|----------|

**3C-6. Return results to cjm-research:**

When returning to `cjm-research`, include:
- Full hypothesis list with all fields
- ICE scores with stage multipliers applied
- Per-hypothesis funnel stage impact
- Category assignments
- Evidence references (Knowledge Library sources, web sources)
