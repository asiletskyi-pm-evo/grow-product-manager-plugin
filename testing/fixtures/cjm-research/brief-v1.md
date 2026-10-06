<!-- Output-eval fixture (input brief) for cjm-research (mode: anomalies + one hypothesis). Feed as the user request; score the resulting report against the cjm-research rubric in testing/output-evals.md. Gold reference: skills/cjm-research/references/examples/funnel-anomaly-report-example-v1.md. Generic, no org data. For the evaluator only (never part of the input, since v3.8.0): the integrity trap is Gate Check 1 — the skill must confirm that May 2026 is complete (last data point vs extract date) before comparing, and handle a partial period (normalize / exclude / flag) rather than treat it as a real drop; until v3.7.0 the brief described a mid-month extract, which disagreed with the gold. Expected: a report where every metric carries its period, the Gate result is shown (incl. the period-completeness check), caveats propagate, and the impact math is marked illustrative. -->

# Input brief

Run a CJM anomaly analysis on a **marketplace 6-stage funnel** for last month, comparing to the prior month.

Context / data notes the PM gives:
- The funnel dashboard is read on 2 Jun 2026, a day after month end.
- One stage (Product view → Add to cart) looks materially down vs the prior month.
- Thresholds: warning 10%, critical 25%.
- Want: anomalies with the Data Integrity Gate applied, period annotation on every metric, and one hypothesis with a funnel-impact estimate.
