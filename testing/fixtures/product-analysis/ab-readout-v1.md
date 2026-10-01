<!-- Output-eval fixture (input brief) for product-analysis (mode: A/B Test Results, standalone). Feed as the user request; score the resulting report against the product-analysis A/B rubric in testing/output-evals.md. Gold reference: skills/product-analysis/references/examples/ab-test-report-example-v1.md. Generic, no org data. The PM's own call is already in the brief, so the P2 question is not asked (references/judgment-points.md §2 step 1) and the comparison belongs in the chat, not in the report. For the evaluator only (never part of the input): expected a report whose verdict follows the pre-set criteria per platform and per guardrail (not the PM's leaning), assesses validity (one source, Android power, the week-2 fade, the pooled guardrails), recommends one of the five AB-4 actions by its definition with what to change and monitor, carries period annotations, and closes with the confidence line and the altitude line. -->

# Input brief

Analyze the A/B test **`one-page-checkout`** on a marketplace and write the A/B test report. I think it clearly won — I'd roll it out everywhere.

Test context the PM gives:
- Hypothesis: collapsing the three checkout steps into one page raises checkout completion.
- Groups: control (three-step checkout) vs test (one page), 50 / 50 split, stable for the whole run.
- Platforms: web and Android. Ran 1–14 Sep 2026 (14 days, as planned). Success criterion: checkout completion (checkout start → order) up by ≥ 2% relative with p < 0.05; guardrails: average order value and support contacts per order must not get worse.

Results the PM pastes (test window 1–14 Sep 2026, per platform):
- Web — checkout completion: control 61.8 %, test 64.1 % (+3.7 % relative), p < 0.001; sample reached 104 % of the planned power.
- Android — checkout completion: control 58.0 %, test 58.9 % (+1.6 % relative), p = 0.15; sample reached 41 % of the planned power (traffic lower than forecast).
- Average order value (both platforms): −0.4 %, not significant.
- Support contacts per order (both platforms): +6 %, p = 0.04 — mostly "where is my delivery option" questions on the test page.
- Time dynamics (web): relative lift +5.1 % in week 1, +2.4 % in week 2.
- No holidays, promotions or outages in the window; no methodology change.
