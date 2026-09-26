# Output evals — artifact quality test set

Purpose: verify that artifact-producing skills generate **high-quality outputs**, not just that the right skill fired. This is the **output-eval** half of observability (see `references/harness-map.md`); `testing/trigger-evals.md` is the **trajectory/routing** half. The whitepaper: *"Set the bar at the eval, not the demo. An eval without a clear rubric measures nothing."* Both halves are required — a fluent artifact that skipped its checks is a more dangerous failure than an obviously broken one.

## Trajectory vs output — the split

| Eval | Question | File |
|------|----------|------|
| **Trajectory** | Did the right skill fire / did it take the right steps and tool calls? | `testing/trigger-evals.md` |
| **Output** | Is the produced artifact correct and high-quality against a rubric? | this file |

## Method

1. **Judge**: an LM-judge subagent scores the artifact against the skill's rubric. Each criterion is scored **0 / 1 / 2** (0 = absent, 1 = present but weak/partial, 2 = fully met).
2. **Gold reference**: the skill's golden exemplar (`skills/<skill>/references/examples/*-v1.md`) is given to the judge as the quality bar. Score the candidate's *rigor*, not its wording.
3. **Score**: `weighted_score = Σ(criterion_score × weight) / Σ(2 × weight)`. **Pass = weighted_score ≥ pass_threshold** (default **0.8**).
4. **Diagnose on fail**: cluster the failing criteria, route the fix via `references/self-improvement.md` (harness-first diagnosis), re-run.

## How to run

**Automated (preferred):** feed the `skill-creator` eval harness a fixture input, let the target skill produce the artifact in a subagent, then run the judge subagent with the rubric + gold reference. Record per-criterion scores and the weighted total.

**Manual (baseline):** in a fresh Cowork session, run the skill on the fixture input, paste the output and the rubric to a judge prompt, record scores.

Fixtures live in `testing/fixtures/<skill>/`. Each fixture is a short **input brief**; the matching gold reference is the skill's exemplar.

## Rubrics

### write-concept — PRD
- **Artifact:** PRD · **Gold:** `skills/write-concept/references/examples/prd-example-v1.md` · **Fixture:** `testing/fixtures/write-concept/brief-v1.md` · **pass_threshold:** 0.8

| id | Criterion | Weight |
|----|-----------|--------|
| problem_clear | Problem stated as a problem (not a pre-baked solution), with who is affected | 2 |
| success_metric | At least one **measurable** primary metric + a guardrail metric | 2 |
| verification | Verification / decision-rule present (how we'll know it worked) | 2 |
| scope_boundaries | Scope + explicit Non-Goals / Out-of-scope | 1 |
| user_segments | "What changes for users" per affected segment | 1 |
| assumptions | Assumptions/open questions flagged, not silently asserted | 1 |
| sources | Data points cited with source and period | 1 |

### requirements-creator — feature spec
- **Artifact:** requirements doc · **Gold:** `skills/requirements-creator/references/examples/feature-spec-example-v1.md` · **Fixture:** `testing/fixtures/requirements-creator/brief-v1.md` · **pass_threshold:** 0.8

| id | Criterion | Weight |
|----|-----------|--------|
| acceptance_criteria | Given/When/Then acceptance criteria, testable and binary | 2 |
| decision_rule | For A/B: explicit ship/iterate/kill rule tied to thresholds (stated before launch) | 2 |
| success_guardrail | Primary success metric + guardrail metric defined | 2 |
| functional_complete | Functional requirements specific enough to implement without guessing | 2 |
| edge_cases | Edge/error states covered | 1 |
| analytics | Analytics events listed for the change | 1 |
| out_of_scope | Out-of-scope explicit | 1 |

### cjm-research — anomaly report
- **Artifact:** funnel-anomaly report · **Gold:** `skills/cjm-research/references/examples/funnel-anomaly-report-example-v1.md` · **Fixture:** `testing/fixtures/cjm-research/brief-v1.md` · **pass_threshold:** 0.85 *(higher bar — data integrity)*

| id | Criterion | Weight |
|----|-----------|--------|
| period_annotation | **Every** cited metric carries its period (Data Integrity Gate) | 2 |
| gate_passed | Data Integrity Gate result shown (period completeness, cross-validation, holiday/method screening) | 2 |
| caveats | ⚠️ Caveats surfaced and propagated to conclusions | 2 |
| impact_math | Funnel-impact estimate shown and marked illustrative vs measured | 2 |
| anomaly_scope | Anomaly localized (segment/scope), not just a headline number | 1 |
| hypothesis | Hypothesis with confidence + next step (chain to brainstorm-features) | 1 |
| sources | ≥2 sources for critical anomalies, all period-annotated | 1 |

### meeting-processor — minutes of meeting (since v3.4.0)
- **Artifact:** Structured MoM · **Gold:** `skills/meeting-processor/references/examples/mom-example-v1.md` · **Fixture:** `testing/fixtures/meeting-processor/brief-v1.md` · **pass_threshold:** 0.8

| id | Criterion | Weight |
|----|-----------|--------|
| decisions_extracted | Every decision taken in the meeting is recorded, with its rationale; parked ideas and tentative dates are not promoted to decisions | 2 |
| action_items_with_owner | Every action item has exactly one owner, an active verb and a date | 2 |
| no_hallucinated_content | Nothing absent from the transcript (names, emails, numbers, commitments) | 2 |
| structured_summary | The Structured MoM sections are present and filled | 1 |
| chain_offer | Next-step offers to the skills that fit the meeting type | 1 |

### task-creator — Jira discipline tasks (since v3.4.0)
- **Artifact:** tasks under an epic · **Gold:** `skills/task-creator/references/examples/tasks-example-v1.md` · **Fixture:** `testing/fixtures/task-creator/brief-v1.md` · **pass_threshold:** 0.8

| id | Criterion | Weight |
|----|-----------|--------|
| tasks_per_discipline | One task per affected discipline (FE / BE / iOS / Android / QA / Analytics), none missing, none invented | 2 |
| derived_from_requirements | Every task bullet traces to a requirement or acceptance criterion; no ungrounded technical content (artifact-style-gate Gate 1) | 2 |
| acceptance_in_task | Each task carries its acceptance criteria / Definition of Done | 2 |
| correct_epic_link | Parent epic and links set as the skill prescribes | 1 |
| estimates_or_labels | Work-type labels (and estimates only when sourced) | 1 |

### Lighter rubrics (fixtures TBD — add exemplars first)

**product-analysis** (analysis report): period_annotation (2), gate_passed (2), trend_vs_baseline (2), anomaly_or_insight (2), hypothesis_backed (1), sources (1). pass 0.85.

**brainstorm-features** (hypothesis backlog): ice_scored (2), hypothesis_structure IF/THEN/measurable (2), funnel_impact_link (2), validation_method (1), prioritized (1). pass 0.8.

> **Rubric-authoring rule:** a criterion must be observable and binary-ish (0/1/2 with clear anchors). Vague criteria ("well written") are not allowed — they measure nothing.

## Integration

- **Testing-process.md stage 3b (Output eval)** — blocker for any changed artifact-producing skill. Runs after 3a (trajectory/trigger).
- **Definition of Done** — for a release touching an artifact skill, its output-eval must be ≥ pass_threshold (the same way trigger-evals gate description releases).
- **On regression** — a dropped criterion score points at the harness layer to fix (usually Instructions or Examples); see `references/self-improvement.md`.

## Results log

| Date | Release | Skill | Before (main) | After (branch) | Runner | Note |
|------|---------|-------|---------------|----------------|--------|------|
| 2026-09-25 | v3.4.0 | write-concept | 1.00 ✅ | 1.00 ✅ | maker subagent per version + one blind LM judge scoring both (order alternated per skill) | thin-core regression: no material difference |
| 2026-09-25 | v3.4.0 | requirements-creator | 0.91 ✅ | 1.00 ✅ | same | `decision_rule` 1 → 2; the judge attributes it to run variance, not to the moved publishing / handoff text |
| 2026-09-25 | v3.4.0 | cjm-research | 0.86 ✅ | 0.86 ✅ | same | identical scores after Step 3.5 became a pointer table (threshold 0.85) |
| 2026-09-25 | v3.4.0 | meeting-processor | 0.88 ✅ | 1.00 ✅ | same | first run of the new fixture + gold; `action_items_with_owner` 1 → 2, run variance |
| 2026-09-25 | v3.4.0 | task-creator | 1.00 ✅ | 1.00 ✅ | same | first run of the new fixture + gold |

## Coverage status (rubrics/fixtures as of v3.4.0)

> **Stage 3b is a blocker** (`Testing-process.md`), yet no 3b run is recorded anywhere for
> v2.0.x or v2.1.x — and those releases changed `requirements-creator`, `meeting-processor`,
> `product-analysis` and `cjm-research`, all artifact-producing. As with `trigger-evals.md`,
> the gate has been asserted rather than met. Run 3b for every changed artifact skill before
> the next release and record the result here; an unlogged pass is not a pass.

| Skill | Rubric | Fixture | Gold exemplar |
|-------|--------|---------|---------------|
| write-concept | ✅ | ✅ | ✅ |
| requirements-creator | ✅ | ✅ | ✅ |
| cjm-research | ✅ | ✅ | ✅ |
| product-analysis | ✅ light | ⬜ | ⬜ |
| brainstorm-features | ✅ light | ⬜ | ⬜ |
| meeting-processor | ✅ (v3.4.0) | ✅ | ✅ |
| task-creator | ✅ (v3.4.0) | ✅ | ✅ |

Next: add golden exemplars + fixtures for the four light-rubric skills, then promote their rubrics to full.
