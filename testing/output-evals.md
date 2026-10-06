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

### Judgment criteria — every rubric (since v3.7.0; evidence criteria since v3.8.0; counter-argument since v3.9.0)

Added to each rubric below (spec FR-15). Each is scored only where its gate applies to that artifact and is `n/a` elsewhere. The evidence criteria do not double-score what a rubric already scores (the research plan's `method_fit`, the QBR's `decisions_taken`, the PRD's `assumptions`): there they check only the label, not the content. The spec's `provenance` criterion is scored as `evidence_labels` plus the rubric's own `sources` / `sources_dated` row where it has one — not as a row of its own. Since v3.9.0 a line or section the user removed at the run's review step (the altitude line, the confidence line, the pre-mortem) is `n/a`, not 0 — the skill must not restore it (`self-improvement.md`), and a restored one is a defect logged in the Results log.

| id | Criterion | Weight | `n/a` when |
|----|-----------|--------|------------|
| altitude_line | Exactly one `Altitude: L1–L4 · ↑ serves: … · ↓ next: …` line as the artifact's last content (Gate 4a): `serves` is a goal the fixture or its sources link, or `— (no linked goal)`, never a person's goal; `next` is a product or delivery step | 1 | Gate 4a is `n/a` (task bodies, A&I documents, 1-1s, prototypes, external decks, return payloads) |
| confidence_falsifier | Exactly one `Confidence: known / likely / uncertain / unknown · most sensitive to: … · would change if: …` line directly above the altitude line (Gate 4c), with: one specific assumption; an observable change condition, not "more data"; and a level no higher than the Data Integrity Gate allows (an inconclusive verdict is at most `uncertain`) | 2 | `references/judgment-points.md` §1 names no confidence line for the skill and mode. A P3-format line that appears there anyway is logged as a defect in the Results log (improvised output, `pm-mental-model.md` §5); a skill's own confidence field or label is not such a line |
| evidence_labels | Every evidence claim — a number stated as what is or was, a quote, a benchmark, a "users want X" — carries its class (`pm-mental-model.md` §4) in any visible form (inside the annotation, bracket, or a group label whose claims all share class and source), consistent with its source per Gate Check 6a: figures the user pasted are `reported`, never `measured`; quotes verbatim (masking, `[…]`, `(translated)` allowed); exemptions per Gate 4b §1 (targets, forecasts, plan totals, hypothesis statements…) carry none | 1 | Gate 4b is `n/a` (task bodies and batches, People contour, prototypes, handoffs, 1-1s, Q&A, return payloads) |
| simulated_visible | `simulated` content is never a finding, never counted in n or frequencies, never quoted — it sits on one labelled `Simulated input` line or in hypotheses; `assumed` claims in a findings section are labelled; where the skill runs Gate Check 6 (cjm-research, product-analysis, product-research, feedback-triage), a frontier claim (6c) carries its hand-back line or stays a labelled hypothesis — elsewhere such a claim needs only its label | 2 | the fixture has no `simulated` / `assumed` input and no frontier claim |
| counter_argument | A pre-mortem (`judgment-points.md` §7): 2–3 failure causes, each naming the input or section it rests on and carrying an observable early signal; plus kill criteria — rows of observable signal, threshold (from the artifact, else `⚠️ TBD`), date and then (stop / pivot / descope / roll back) — or a pointer to the artifact's existing kill / decision section instead of a second table. **2:** all of it. **1:** present but weak — a cause that names no input or section, an early signal nobody can observe, a kill row without its date or its "then", a threshold invented where the artifact states none, or a second kill table beside an existing kill section, an A/B decision rule or a concept decision rule whose kill branch has a threshold and a date (`template-protocol.md` T-5 step 3b). **0:** absent, or causes too generic to rest on anything ("the launch may not go well"). The block is never asked: a question that fills one of its `⚠️ TBD` cells is a trajectory defect logged in the Results log, not scored by this row (the AI feature spec's `no_question_for_derived` scores it there) | 2 | `judgment-points.md` §7 names no pre-mortem for the skill and mode — a pre-mortem section that appears there anyway is a defect logged in the Results log; the block was deselected at the skill's own step (write-concept Step 1, block 15) or removed by the user at the review step |

**Where `counter_argument` applies (since v3.9.0).** Scored on the write-concept PRD and strategy memo and on both requirements-creator specs (the A/B feature spec and the AI feature spec). `n/a` on the design brief, the MoM, the tasks, the cjm-research report, the A/B test report, the research plan, the user research synthesis and the QBR. No double scoring: where a rubric row already scores the kill part — `decision_rule` (feature spec), `kill_criteria` (strategy memo, AI feature spec) or a `risks` row — `counter_argument` scores only the pre-mortem part: the causes, their early signals, and a kill line that points to that section rather than repeating it. The quarter-plan and roadmap-onboard pre-mortems have no rubric yet; TC-jdg-390-pre-mortem-planning covers them.

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

Since v3.9.0 the gold carries a pre-mortem right after Risks (block 15 of the Step 1 list, pre-selected; the fixture does not touch the block list): three causes, each naming the section or the `[assumed — …]` premise it rests on, with an early signal, and its own Kill criteria table — one threshold the PRD does not state reads `⚠️ TBD`, counted, not asked. `counter_argument` (2) is scored on the whole block, causes and kill table; `verification` keeps scoring the decision rule.

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

Since v3.9.0 the gold carries the A/B pre-mortem: three test-validity causes, each naming the section it rests on, with an early signal and a pre-launch check, and `Kill criteria: see **Success Metrics & Decision Rule** above` instead of a second table. `counter_argument` (2) scores only the causes and that pointer; `decision_rule` keeps scoring the rule.

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
| spec_readiness | Since v3.9.0: one `Spec readiness: n/6 — missing: …` line in the run's existing summary and report (`artifact-style-gate.md` → Spec readiness), its count matching the spec — here `6/6 — missing: none` (platforms and the rollout flag as constraints, the approved mockups as the prior decision); never a question, never a block; no eval-set option, the spec is not AI-driven. **1:** the line is present with a wrong count. **0:** absent, asked, or the run stops on it | 1 |

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

Since v3.9.0 the gold carries a pre-mortem, placed last above the footer because the template has no Risks section: three causes resting on the Base rates and Trade-offs sections, each with an early signal, and `Kill criteria: see **Kill criteria** above` instead of a second table. `counter_argument` (2) scores only that pre-mortem part — the memo's kill table is scored by `kill_criteria`. The fixture's "no extra blocks" answers Step 1's question about additional blocks; it does not deselect block 15, so the pre-mortem is expected.

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

### requirements-creator — AI feature spec (since v3.9.0)
- **Artifact:** AI feature requirements (`requirements/ai-feature`, requested by name) · **Gold:** `skills/requirements-creator/references/examples/ai-feature-spec-example-v1.md` · **Fixture:** `testing/fixtures/requirements-creator/ai-feature-v1.md` (setup: `user.role: pm`) · **pass_threshold:** 0.8

The gold drafts listing descriptions and the fixture product titles: the judge scores the candidate's rigor against the gold's, not its content. Fixture-specific values (the rates, the masked titles, the out-of-scope items) are in the fixture's evaluator comment. For `no_question_for_derived` the judge also gets the maker's chat turns.

| id | Criterion | Weight |
|----|-----------|--------|
| not_solution_shaped | "Problem and outcome" says who has the problem and what it costs them, each evidence claim labelled, and an outcome measured by a named metric — a direction, or a target only where the input states one — with a guardrail where the input names one. It does not make the feature, the model or the mechanism the goal, and no model, vendor, prompt or architecture choice appears anywhere outside an AI recommendations block the user asked for (Gate 1). **1:** problem-shaped, but no metric in the outcome; or the brief's solution-shaped goal stays in the section and the one chat line `⚠️ not solution-shaped: …` with a problem-shaped rewording is shown (`skills/requirements-creator/references/ai-feature-section.md` §5). **0:** the feature is the goal ("add AI title suggestions") and no note is shown, or a model or vendor is prescribed | 2 |
| behaviour_spec | One row per input or situation the input names (for example the typical input, too little input, input that carries what must not be repeated, a restricted case, a timeout, the user's own text), each with must and must not, and with a fallback or refusal wherever the output is withheld or changed. The human fallback holds: the output is a suggestion or draft the user applies, edits or ignores; it never overwrites the user's text, and nothing is published without the user's action. A cell nothing states reads `⚠️ TBD`. **1:** must / must-not without fallbacks, or a situation the input names is missing. **0:** a feature list instead of behaviour rules | 2 |
| eval_set | Cases of all four types — typical, edge, adversarial, refusal — each with an expected behaviour, an origin class and a binary pass rule. The real examples the input supplies become cases, personal data masked as given, with the class their source supports: `reported` when the user pasted them, `observed` only when the skill read the production log itself. Invented cases are `simulated` and never stand in for production behaviour; expected outputs carry no class. The planned size and owner are stated or `⚠️ TBD`, and the set is re-run on every model or prompt change. **1:** a type missing, a pass rule that is not binary ("good quality"), real examples left unused, a real example labelled `observed` from pasted text, or no re-run rule. **0:** no eval set; cases without origin; a real example labelled `simulated` or an invented one labelled `reported` / `observed`; or unmasked personal data | 2 |
| error_rate | One row per error class the behaviour spec implies (for example invented content, missing content, output in a restricted case, the user discarding the output), each with an acceptable rate and how it is measured before launch (the eval set) and after (a production review or an event ratio). A rate the input states is restated exactly ("1 in 200" = 0.5 %); a rate it does not state reads `⚠️ TBD`; rates carry no evidence class. **1:** rates without a measurement, or an error class of the behaviour spec without a row. **0:** no rates, or a number the input does not state presented as the acceptable rate | 2 |
| kill_criteria | The spec's own Kill criteria (2.4) cover the launch gate — the eval set above its acceptable rate before the flag opens — and production — an error, complaint, cost or guardrail signal. Each row has an observable signal, a threshold consistent with 2.3 or the input (else `⚠️ TBD`), a date or checkpoint (from the input, else derived from the launch and the window the spec states, e.g. "4 weeks after the flag opens"), and a then — stop, pivot, descope or roll back (else the default: switch the AI behaviour off). Only the threshold may be `⚠️ TBD` (`references/judgment-points.md` §7). **1:** only the launch gate or only production, or a row without its date or its then (a `⚠️ TBD` date or then counts as without). **0:** absent, or signals nobody can observe ("if quality drops") | 2 |
| no_question_for_derived | Every value of the derived sections — the AI sections and the pre-mortem — that the input does not state reads `⚠️ TBD`: no invented threshold, case count, owner or calendar date. A kill row's relative date and default then (§7) are derived, not invented. The maker asks no Step 2, Step 3 or T-4 question about them (`skills/requirements-creator/references/ai-feature-section.md` §3); the gaps may go to Open questions. **1:** one invented value, or one such question. **0:** several, or the run stops to ask for the error rates or kill thresholds | 2 |
| tracking_plan_ai_events | The tracking plan has events that measure 2.3 and 2.4 in production: output shown, a human override (applied, edited or discarded), the fallback or refusal, and user feedback where the spec has it — each with trigger, properties, owner and verification. It says which rates and kill criteria they feed. **1:** no override or no fallback event, or no link to 2.3 / 2.4. **0:** no tracking plan, or only a generic click event | 1 |
| acceptance_eval | Given/When/Then acceptance criteria for the deterministic (non-model) parts, testable and binary, plus the AC-eval line: the eval set passes at or below the acceptable error rate. **1:** one of the two missing. **0:** neither | 1 |
| out_of_scope | An explicit Out of scope list carrying every item the input rules out, a stakeholder request deferred to a later phase included | 1 |

With the judgment criteria:
- `altitude_line` (1): L1; serves the parent epic the input links (the fixture: PROJ-2100) or `— (no linked goal)` (the gold); next a delivery step, such as running the eval set before the flag opens.
- `confidence_falsifier`: `n/a` — requirements-creator is not in `references/judgment-points.md` §1, and a P3-format line here is logged as a defect.
- `evidence_labels` (1): pasted dashboard figures read `reported (…)`, never `measured`, and an unsourced premise reads `[assumed — …]`. The eval cases' origin column is scored by `eval_set`, not twice. Behaviour rules, expected outputs, rates and kill rows carry no class (Gate 4b §1). This label check plus `eval_set`'s origin column is the spec's `provenance` here — the rubric has no `sources` row.
- `simulated_visible` (2): checks only that no `simulated` eval case is cited as evidence outside the eval set (Problem and outcome, the pre-mortem), and that the `assumed` premise keeps its label wherever it reappears. Saying how many eval cases are `simulated` — a pre-mortem cause — is not counting them as evidence.
- `counter_argument` (2): only the pre-mortem part. It needs 2–3 causes from the AI sections or the `assumed` premise — an eval set thin or mostly `simulated`, an error class at `⚠️ TBD`, a refusal left unspecified, drift after a model or prompt change. Each cause names the section it rests on and has an early signal, and the kill line points to 2.4. A second kill table scores 1; 2.4 itself is scored by `kill_criteria`.

Gold check (2026-10-06): the gold meets every row at 2 on its own content. Problem and outcome names no model, and its premise is `[assumed — …]`. The behaviour spec has six situations, a fallback or refusal on those that withhold or change the draft, and never overwrites the seller's text (FR-2, AC-4). The eval set has all four types, with origins, binary pass rules, size and owner `⚠️ TBD` and the re-run rule. 2.3 has four classes, the discard rate `⚠️ TBD`. 2.4 covers the launch gate and production. AC-1 to AC-4 and AC-eval are present. The tracking plan has the shown, applied (`draft_applied`), discarded, feedback and fallback events and what they feed. Every 2.4 row has a date and a then; only thresholds are `⚠️ TBD`. Out of scope has three items. The pre-mortem has three causes, each with "rests on", and points to 2.4. The altitude line is L1 with `— (no linked goal)`. `no_question_for_derived` is checked on its `⚠️ TBD` cells only, since a gold has no run log.

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
| 2026-10-06 | v3.9.0 | requirements-creator (AI feature spec, new — TC-jdg-390-ai-feature) | — | 0.95 ✅ | maker on the branch + blind LM judge | `requirements/ai-feature` resolved silently by `match: subtype`; the pre-mortem derived, never asked, its kill line a pointer to 2.4. One 2.4 row had `⚠️ TBD` for threshold, date and then — the rubric's `no_question_for_derived` ("no invented … date") invited it; §7, the template hint, ai-feature-section and this rubric now say the date and the then are derived and only the threshold may be `⚠️ TBD` |
| 2026-10-06 | v3.9.0 | write-concept (PRD) | — | 1.00 ✅ | same | the build-first line sits inside the Step 1 summary, not a question; pre-mortem after Risks & Assumptions with a pointer to "Verification & decision rule" — since the round-1 fixes a pointer only when that rule states a kill branch with a threshold and a date, else kill rows |
| 2026-10-06 | v3.9.0 | write-concept (strategy memo) | — | 0.88 ✅ | same | pre-mortem rendered (block 15), no build-first line (a memo); the candidate placed it before Kill criteria by a 3b clause removed in round 1 (now above the footer, as the gold). Bet 3's baseline `⚠️ TBD` without a first-reading date (as in v3.8.0) and no explicit trade-off between bets — run variance |
| 2026-10-06 | v3.9.0 | requirements-creator (A/B feature spec) | — | 1.00 ✅ | same | pre-mortem with a pointer to Stopping / Decision Criteria; no question filled a pre-mortem cell |
| 2026-10-06 | v3.9.0 | task-creator | — | 0.90 ✅ | same | no build-first line, no pre-mortem, no confidence line (correct). The dry run stopped at Step 6b, so no Step 11 report and no altitude line (run variance); the built-in task template's fixed DoD items stay on every task, "QA passed" on the QA task too — pre-existing, open |
| 2026-10-06 | v3.9.0 | meeting-processor | — | 0.85 ✅ | same | regression: no P2, pre-mortem, build-first or PM-first question (`learning_mode` off). One action item without its date although the transcript gives one; chain offers in the chat only (as in v3.8.0) |
| 2026-10-06 | v3.9.0 | write-concept (design brief) | — | 1.00 ✅ | same | no pre-mortem, no build-first line (both excluded for a brief). Step 5 re-offered the red-team debate the request had declined — pre-existing, open |
| 2026-10-06 | v3.9.0 | requirements-creator (AI feature spec, re-run after the round-1 fixes) | — | 0.95 ✅ | same | `kill_criteria` 1 → 2: every 2.4 row dated and with a then, only thresholds `⚠️ TBD`. `eval_set` 2 → 1: 2.2 had no re-run rule and no size / owner line — the template's 2.2 block did not carry one; `requirements/ai-feature` now renders "Planned size and owner: … The set is re-run on every model or prompt change." (ai-feature-section §3 too). A 200-case floor was read as sufficient (rigor, not scored) |
| 2026-10-06 | v3.9.0 | product-research (user research synthesis) | — | 1.00 ✅ | same | regression (`learning_mode` off, no PM-first question); persona interviews `simulated` from their stated origin, no question; three quotes repeated between Themes and Quotes (presentation) |
| 2026-10-06 | v3.9.0 | product-research (research plan) | — | 0.93 ✅ | same | regression; assumptions name the option they bear on but not the finding that would move the decision (as in v3.8.0) |
| 2026-10-06 | v3.9.0 | cjm-research | — | 0.90 ✅ | same | threshold 0.85; regression (Step 7.0 skipped, `learning_mode` off; no pre-mortem, no build-first line). Restated baseline figures in the hypotheses table and summary without a class; one source for the anomaly metric, disclosed as ⚠️ Caveat (the PM declared one dashboard); no segment split in the supplied totals |

## Coverage status (rubrics/fixtures as of v3.9.0)

> **Stage 3b is a blocker** (`Testing-process.md`), yet no 3b run is recorded anywhere for
> v2.0.x or v2.1.x — and those releases changed `requirements-creator`, `meeting-processor`,
> `product-analysis` and `cjm-research`, all artifact-producing. As with `trigger-evals.md`,
> the gate has been asserted rather than met. Run 3b for every changed artifact skill before
> the next release and record the result here; an unlogged pass is not a pass.

| Skill | Rubric | Fixture | Gold exemplar |
|-------|--------|---------|---------------|
| write-concept — PRD | ✅ | ✅ | ✅ |
| requirements-creator — feature spec | ✅ | ✅ | ✅ |
| requirements-creator — AI feature spec | ✅ (v3.9.0) | ✅ | ✅ |
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

**Golds per skill** (files under `skills/*/references/examples/`, counted 2026-10-06): 12 in 8 of 31 skills — write-concept 3 · requirements-creator 2 · product-research 2 · cjm-research 1 · meeting-processor 1 · product-analysis 1 · product-reporter 1 · task-creator 1; the other 23 skills have none. Each gold has one full rubric and one fixture above: 12 rubrics, 12 fixtures. Recount at each release.

Next: add golden exemplars + fixtures for the two light-rubric skills, then promote their rubrics to full.
