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
3. **Score**: `weighted_score = Σ(criterion_score × weight) / Σ(2 × weight)` over every criterion of the rubric plus the judgment criteria below; a criterion scored `n/a` is left out of both sums. **Pass = weighted_score ≥ pass_threshold** (default **0.8**).
4. **Diagnose on fail**: cluster the failing criteria, route the fix via `references/self-improvement.md` (harness-first diagnosis), re-run.

## How to run

**Automated (preferred):** feed the `skill-creator` eval harness a fixture input, let the target skill produce the artifact in a subagent, then run the judge subagent with the rubric + gold reference. Record per-criterion scores and the weighted total.

**Manual (baseline):** in a fresh Cowork session, run the skill on the fixture input, paste the output and the rubric to a judge prompt, record scores.

Fixtures live in `testing/fixtures/<skill>/`. Each fixture is a short **input brief**; the matching gold reference is the skill's exemplar.

## Rubrics

### Judgment criteria — every rubric (since v3.7.0; evidence criteria since v3.8.0)

Added to each rubric below (spec FR-15). Each is scored only where its gate applies to that artifact and is `n/a` elsewhere. `counter_argument` joins in v3.9.0, with the step that implements it. The evidence criteria do not double-score what a rubric already scores (the research plan's `method_fit`, the QBR's `decisions_taken`, the PRD's `assumptions`): there they check only the label, not the content.

| id | Criterion | Weight | `n/a` when |
|----|-----------|--------|------------|
| altitude_line | Exactly one `Altitude: L1–L4 · ↑ serves: … · ↓ next: …` line as the artifact's last content (Gate 4a): `serves` is a goal the fixture or its sources link, or `— (no linked goal)`, never a person's goal; `next` is a product or delivery step | 1 | Gate 4a is `n/a` (task bodies, A&I documents, 1-1s, prototypes, external decks, return payloads) |
| confidence_falsifier | Exactly one `Confidence: known / likely / uncertain / unknown · most sensitive to: … · would change if: …` line directly above the altitude line (Gate 4c), with: one specific assumption; an observable change condition, not "more data"; and a level no higher than the Data Integrity Gate allows (an inconclusive verdict is at most `uncertain`) | 2 | `references/judgment-points.md` §1 names no confidence line for the skill and mode. A P3-format line that appears there anyway is logged as a defect in the Results log (improvised output, `pm-mental-model.md` §5); a skill's own confidence field or label is not such a line |
| evidence_labels | Every evidence claim — a number stated as what is or was, a quote, a benchmark, a "users want X" — carries its class (`pm-mental-model.md` §4) in any visible form (inside the annotation, bracket, or a group label whose claims all share class and source), consistent with its source per Gate Check 6a: figures the user pasted are `reported`, never `measured`; quotes verbatim (masking, `[…]`, `(translated)` allowed); exemptions per Gate 4b §1 (targets, forecasts, plan totals, hypothesis statements…) carry none | 1 | Gate 4b is `n/a` (task bodies and batches, People contour, prototypes, handoffs, 1-1s, Q&A, return payloads) |
| simulated_visible | `simulated` content is never a finding, never counted in n or frequencies, never quoted — it sits on one labelled `Simulated input` line or in hypotheses; `assumed` claims in a findings section are labelled; where the skill runs Gate Check 6 (cjm-research, product-analysis, product-research, feedback-triage), a frontier claim (6c) carries its hand-back line or stays a labelled hypothesis — elsewhere such a claim needs only its label | 2 | the fixture has no `simulated` / `assumed` input and no frontier claim |

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

### write-concept — design brief (since v3.6.0)
- **Artifact:** design brief (`concept/design-brief`) · **Gold:** `skills/write-concept/references/examples/design-brief-example-v1.md` · **Fixture:** `testing/fixtures/write-concept/design-brief-v1.md` (setup: `user.role: product_designer`) · **pass_threshold:** 0.8

| id | Criterion | Weight |
|----|-----------|--------|
| problem_not_solution | The problem is stated as a user problem — who hits it and what it costs them today, each claim with its source; no screen, component or solution is prescribed, and the stakeholder's live-map request stays input or goes out of scope, never a requirement | 2 |
| users_segments | Every affected segment has its share, context of use and platform; the number of real users behind the evidence is stated, and the segment with no evidence (guests, 0 of 5 sessions) is flagged as a gap | 2 |
| success_metric | One primary metric with baseline, period and target; one guardrail with baseline and limit; the usability-round bar for judging the explorations | 2 |
| constraints | Confirmed constraints only, each with its source (carrier coverage, no courier location, notification channel, legal, Design System / WCAG); no technical assumption added | 1 |
| jobs_to_be_done | Jobs in the "When … I want to … so I can …" form, each traced to evidence; a job resting on 2 of 5 sessions is marked as a hypothesis | 1 |
| out_of_scope | Explicit out-of-scope list, including the item ruled out with its reason | 1 |
| open_questions | Questions the explorations or research must answer before handoff, exactly one owner each, none invented | 1 |

### write-concept — strategy memo (since v3.6.0)
- **Artifact:** strategy memo (`concept/strategy-memo`) · **Gold:** `skills/write-concept/references/examples/strategy-memo-example-v1.md` · **Fixture:** `testing/fixtures/write-concept/strategy-memo-v1.md` (setup: `user.role: cpo`) · **pass_threshold:** 0.8

| id | Criterion | Weight |
|----|-----------|--------|
| bets_with_tradeoffs | Each bet names its investment (teams, money, time), its expected return — or says it is not modelled — its stage (explore / expand / extract) and the intent it serves; the trade-offs between bets are stated | 2 |
| proxy_metrics | Per bet, a leading indicator with baseline and period (or "not measured yet" with the first reading date), target, review cadence and source | 2 |
| what_we_stop | Named work stopped, with the date and what it frees (teams, cost) | 2 |
| kill_criteria | Per bet, a signal and a date at which we stop or pivot, fixed in the memo before the data arrives | 2 |
| base_rates | Per bet, a reference class with its success rate and source, or an explicit "none known" — never an invented rate; the small sample (n = 3) is flagged | 2 |
| intents_linked | Two to four strategic intents stated as outcomes, each linked to the objective it serves or marked as having none | 1 |
| sources_dated | Every business and market fact carries its source and date; the market report older than 12 months is flagged | 1 |

### product-research — research plan (since v3.6.0)
- **Artifact:** research plan (`research/research-plan`) · **Gold:** `skills/product-research/references/examples/research-plan-example-v1.md` · **Fixture:** `testing/fixtures/product-research/research-plan-v1.md` (setup: `user.role: ux_researcher`) · **pass_threshold:** 0.8

| id | Criterion | Weight |
|----|-----------|--------|
| decision_informed | One decision the study informs and one primary research question; each assumption says what would move the decision; a question that would not change it (the acquisition channel) is dropped with its reason | 2 |
| method_fit | The method matches the question (why → interviews; how common → funnel data and tickets) and says why; simulated interviews may rehearse the guide but never count toward n or enter the synthesis | 2 |
| participants_n | Planned n of real users per group (stopped vs contrast), participants as ids only, and what that n can and cannot support | 2 |
| recruiting | Inclusion criteria, exclusions, screener, channel and incentive; a timeline with one owner per phase | 1 |
| confidence_label | An expected-confidence label with its reason; high only where a second, independent source type is planned and agrees | 1 |
| human_validated_flag | `Human-validated: no` on the model draft, in the plan and in the repository entry — never set to yes by the model | 1 |
| repository_entry | The Repository entry section (role extra section, template-protocol T-5 step 3b) sits above the altitude line, filled from the plan, with no names or contacts | 1 |

### product-reporter — QBR (since v3.6.0)
- **Artifact:** QBR (`ops-report/qbr`, `quarter-review` mode) · **Gold:** `skills/product-reporter/references/examples/qbr-example-v1.md` · **Fixture:** `testing/fixtures/product-reporter/qbr-v1.md` (setup: `user.role: business_owner`) · **pass_threshold:** 0.8

| id | Criterion | Weight |
|----|-----------|--------|
| financials_vs_plan | Every finance line with plan, actual, Δ and full-year forecast, the period and source stated, and each deviation with its cause | 2 |
| money_bridge_or_stated_absence | Money-bridge rows only for Key Metrics that carry a Revenue driver; each expected effect cites the number behind it or says "— (not estimated)"; the metric with no mapping (Buyer NPS) carries "no revenue mapping configured"; nothing invented | 2 |
| decisions_taken | Every decision of the quarter with its decision-log record and evidence; the one resting on a senior opinion (DL-12) carries a ⚠️ line that labels its input `assumed` | 2 |
| commitments | Three to five measurable commitments for the next quarter, each with one owner and a date | 2 |
| initiatives_status | Each initiative with the objective it serves, status, planned vs delivered (Jira numbers) and next step | 1 |
| risks | Risks with likelihood, impact, owner and mitigation, as given — none invented | 1 |
| org_health_aggregate | Org health in aggregates only; nothing from 1-1 notes, person profiles or reviews (the fixture's 1-1 remark is absent) | 1 |

Since v3.7.0 the closing altitude line is scored by `altitude_line` in the judgment criteria above; before v3.7.0 it was only noted in the Results log.

### product-analysis — A/B test report (since v3.7.0)
- **Artifact:** A/B test report (`ab-test-results`, standalone) · **Gold:** `skills/product-analysis/references/examples/ab-test-report-example-v1.md` · **Fixture:** `testing/fixtures/product-analysis/ab-readout-v1.md` · **pass_threshold:** 0.85 *(higher bar — a verdict drives a rollout)*

| id | Criterion | Weight |
|----|-----------|--------|
| verdict_follows_thresholds | The overall verdict comes from the AB-4 set (won / lost / inconclusive) — here `lost`, because a pre-set guardrail is breached — and the verdict per platform and per guardrail follows the pre-set criteria: web met; Android inconclusive, because power is 41 % — never "won" or "lost"; support-contacts guardrail not met (+6 %, p = 0.04) | 2 |
| no_anchoring | The verdict and recommendation follow the data although the brief leans "roll out everywhere". The PM's call and any "your estimate vs mine" comparison are absent from the report (chat only) | 2 |
| validity | Validity names the single source (cross-validation pending), the Android power, the week-1 → week-2 fade and the pooled guardrails, and screens holidays / outages / methodology | 2 |
| recommendation_rule | The recommendation follows the AB-4 definitions: a breached guardrail means the success criteria are not met, so "Stop and iterate" with what to change and how to re-test. Any rollout that leaves the guardrail breach unresolved scores 0 | 1 |
| guardrail_cause | The "where is my delivery option" cause is carried into the change or a follow-up hypothesis | 1 |
| period_annotation | Every cited metric carries the test window | 1 |

With the judgment criteria, `confidence_falsifier` is scored here (weight 2). The gold's line reads `uncertain` — a single source with cross-validation pending, and Android inconclusive. It is most sensitive to the pooled support-contact rise holding on web, and would change if the web-only split shows no rise (Δ ≤ 0 %). A `likely` or `known` level fails `no inflation`. The altitude is L2: A/B readouts sit at L2 in `role-profiles.md` §1.

### product-research — user research synthesis (since v3.8.0)
- **Artifact:** user research report (`research/user-research`, built-in default template) · **Gold:** `skills/product-research/references/examples/user-research-synthesis-example-v1.md` · **Fixture:** `testing/fixtures/product-research/synthesis-v1.md` (setup: `user.role: pm`) · **pass_threshold:** 0.8

| id | Criterion | Weight |
|----|-----------|--------|
| real_n | n = 6 real sellers (P1–P6) stated in Methodology; the three Persona Tool 1 interviews are absent from n, from every "X of N" frequency and from the segment list | 2 |
| findings_real_only | Key Findings, Themes and Pains & Needs rest on P1–P6 only: verification rejections sellers cannot foresee or act on (4 of 6 — P1, P3, P4, P6), fees found after pricing or publishing (3 of 6 — P2, P3, P5), required listing fields that do not fit the product (3 of 6 — P1, P5, P6); the P2 import error and the P4 mobile upload stay single mentions; nothing a persona said appears there, even labelled | 2 |
| simulated_quarantined | The persona material is `simulated` from its "generated with" origin, with no question asked about it; its content appears only on one `Simulated input — hypotheses only` line (and/or as labelled hypotheses) stating what, how many and the study that would check it — a Sources row naming it `simulated` is allowed. A persona answer in quote marks, or used to support or cross-validate a theme, scores 0 | 2 |
| quotes_verbatim | Every quote is verbatim from the notes (masking, a marked […], a marked (translated) with the original allowed), with participant id and interview date, ending `· reported`; a paraphrase carries no quote marks | 1 |
| themes_supported | Each theme states its evidence (class · participant ids) and its frequency as X of 6 real users, and the frequencies match the notes (P1 knew the fee from a friend; P4 and P6 did not raise fees) | 1 |
| hand_back_or_hypothesis | Why sellers stuck at verification give up is not a finding: the supportable part (days to verify, P3 nearly gave up) is kept, Person1's "not serious" view stays a hypothesis labelled `[assumed — …]`, and one ⚠️ hand-back line next to the finding names a human step (interview sellers who stopped at verification), repeated in Research Limitations or Next Steps | 2 |
| sources | Sources list each input with its marker and class: the interview notes `reported` (P1–P6 via Person1's notes); the dashboard figures `user-text` → `reported (Person1)`, never `measured`, labelled the same where §1 cites them | 1 |

With the judgment criteria: `evidence_labels` (1) and `simulated_visible` (2) are scored, but here they check only that the labels are present and well-formed (`simulated` on the line, `[assumed — …]` on the hypothesis, a class on every claim) — placement and the hand-back are scored by `simulated_quarantined` and `hand_back_or_hypothesis`, not twice. `confidence_falsifier` is `n/a` (product-research is not in `references/judgment-points.md` §1; a P3-format line here is logged as a defect). `altitude_line`: L2, serves PROJ-1500, next a product step. A question about the persona interviews' origin is a trajectory defect (TC-jdg-380-simulated-persona), logged in the Results log, not scored here.

### Lighter rubrics (fixtures TBD — add exemplars first)

**product-analysis** (analysis report, non-A/B modes): period_annotation (2), gate_passed (2), trend_vs_baseline (2), anomaly_or_insight (2), hypothesis_backed (1), sources (1). pass 0.85.

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
| 2026-09-28 | v3.5.0 | write-concept | — | 1.00 ✅ | maker on the branch + LM judge | altitude line (Gate 4a) present and correct |
| 2026-09-28 | v3.5.0 | requirements-creator | — | 1.00 ✅ | same | altitude line present and correct |
| 2026-09-28 | v3.5.0 | cjm-research | — | 0.86 ✅ | same | threshold 0.85; altitude line present and correct |
| 2026-09-28 | v3.5.0 | meeting-processor | — | 1.00 ✅ | same | altitude line present and correct |
| 2026-09-28 | v3.5.0 | task-creator | — | 1.00 ✅ | same | altitude line on the report only, not on tasks |
| 2026-09-29 | v3.6.0 | write-concept (design brief, new) | — | 0.95 ✅ | maker on the branch + LM judge | `concept-builtin-design-brief` resolved by the product_designer role default; Gate 4a correct |
| 2026-09-29 | v3.6.0 | write-concept (strategy memo, new) | — | 1.00 ✅ | same | `concept-builtin-strategy-memo` for cpo |
| 2026-09-29 | v3.6.0 | product-research (research plan, new) | — | 1.00 ✅ | same | `research-builtin-research-plan` by the explicit request (the ux_researcher profile adds the repository entry) |
| 2026-09-29 | v3.6.0 | product-reporter (QBR, new) | — | 1.00 ✅ | same | `ops-report-builtin-qbr` for business_owner |
| 2026-09-29 | v3.6.0 | write-concept (PRD) | — | 1.00 ✅ | same | regression: `concept-builtin-default` for pm, unchanged |
| 2026-09-29 | v3.6.0 | requirements-creator | — | 1.00 ✅ | same | regression |
| 2026-09-29 | v3.6.0 | cjm-research | — | 0.91 ✅ | same | regression (threshold 0.85) |
| 2026-09-29 | v3.6.0 | meeting-processor | — | 0.88 ✅ | same | regression |
| 2026-09-29 | v3.6.0 | task-creator | — | 1.00 ✅ | same | regression |
| 2026-09-29 | v3.7.0 | product-analysis (A/B report, new) | — | 1.00 ✅ | maker on the branch + blind LM judge | threshold 0.85; verdict against the PM's leaning ("Stop and iterate"), `Confidence: uncertain` with an observable falsifier above an L2 altitude line; P2 not asked (the call was in the request), comparison in the chat only. The first gold draft was wrong (roll-out despite a breached guardrail, invented sources, L1) and was rewritten before judging |
| 2026-09-29 | v3.7.0 | write-concept (PRD) | — | 1.00 ✅ | same | regression with the judgment criteria: `confidence_falsifier` n/a, no confidence line, no P2 question |
| 2026-09-29 | v3.7.0 | meeting-processor | — | 0.83 ✅ | same | regression; decision-log payload carries only the fields said in the meeting; one undated action item (run variance) |
| 2026-10-06 | v3.8.0 | product-research (user research synthesis, new — TC-jdg-02) | — | 1.00 ✅ | maker on the branch + blind LM judge | persona interviews `simulated` from their stated origin with no question; n = 6 real sellers; one hand-back line on the "why they quit" claim |
| 2026-10-06 | v3.8.0 | requirements-creator | — | 1.00 ✅ | same | regression with evidence criteria; no evidence claims, `докази` omitted at E = 0 |
| 2026-10-06 | v3.8.0 | product-reporter (QBR) | — | 0.97 ✅ | same | the candidate labelled the pasted Jira counts `reported`, the gold `measured` — gold corrected to `reported` for this dry-run fixture |
| 2026-10-06 | v3.8.0 | product-analysis (A/B report) | — | 0.96 ✅ | same | threshold 0.85; pasted results `reported (PM)`; two hypotheses cite results without the test window |
| 2026-10-06 | v3.8.0 | write-concept (design brief) | — | 0.96 ✅ | same | one constraint-excluded request missing from Out of scope |
| 2026-10-06 | v3.8.0 | meeting-processor | — | 0.95 ✅ | same | one artifact-level `Evidence: reported` line; chain offers in the chat, not the artifact |
| 2026-10-06 | v3.8.0 | write-concept (strategy memo) | — | 0.93 ✅ | same | one proxy-metric baseline without a first-reading date |
| 2026-10-06 | v3.8.0 | product-research (research plan) | — | 0.93 ✅ | same | assumptions lack "what would move the decision" |
| 2026-10-06 | v3.8.0 | write-concept (PRD) | — | 0.93 ✅ | same | the PM-only user-need premise carries no hand-back line — `simulated_visible` now scopes 6c to skills that run Gate Check 6; the gold's unlabelled motivation sentence labelled `[assumed — …]` |
| 2026-10-06 | v3.8.0 | cjm-research | — | 0.92 ✅ | same | threshold 0.85; a template hint comment leaked into the body (T-5 step 3d now drops them). Caveat for this whole run: eight older fixtures still stated their "Expected:" line inside the input brief, so those makers saw the bar — the lines were moved into the evaluator comments afterwards; the next run is the first blind one for them |

## Coverage status (rubrics/fixtures as of v3.8.0)

> **Stage 3b is a blocker** (`Testing-process.md`), yet no 3b run is recorded anywhere for
> v2.0.x or v2.1.x — and those releases changed `requirements-creator`, `meeting-processor`,
> `product-analysis` and `cjm-research`, all artifact-producing. As with `trigger-evals.md`,
> the gate has been asserted rather than met. Run 3b for every changed artifact skill before
> the next release and record the result here; an unlogged pass is not a pass.

| Skill | Rubric | Fixture | Gold exemplar |
|-------|--------|---------|---------------|
| write-concept — PRD | ✅ | ✅ | ✅ |
| requirements-creator | ✅ | ✅ | ✅ |
| cjm-research | ✅ | ✅ | ✅ |
| product-analysis — analysis report | ✅ light | ⬜ | ⬜ |
| product-analysis — A/B test report | ✅ (v3.7.0) | ✅ | ✅ |
| product-research — user research synthesis | ✅ (v3.8.0) | ✅ | ✅ |
| brainstorm-features | ✅ light | ⬜ | ⬜ |
| meeting-processor | ✅ (v3.4.0) | ✅ | ✅ |
| task-creator | ✅ (v3.4.0) | ✅ | ✅ |
| write-concept — design brief | ✅ (v3.6.0) | ✅ | ✅ |
| write-concept — strategy memo | ✅ (v3.6.0) | ✅ | ✅ |
| product-research — research plan | ✅ (v3.6.0) | ✅ | ✅ |
| product-reporter — QBR | ✅ (v3.6.0) | ✅ | ✅ |

Next: add golden exemplars + fixtures for the two light-rubric skills, then promote their rubrics to full.
