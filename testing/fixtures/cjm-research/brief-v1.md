<!-- Output-eval fixture (input brief) for cjm-research (mode: anomalies + one hypothesis). Feed as the user request; score the resulting report against the cjm-research rubric in testing/output-evals.md. Gold reference: skills/cjm-research/references/examples/funnel-anomaly-report-example-v1.md. Generic, no org data. -->

# Input brief

Run a CJM anomaly analysis on a **marketplace 6-stage funnel** for last month, comparing to the prior month.

Context / data notes the PM gives (deliberately includes an integrity trap):
- Extract taken mid-month; the last month's data may be a partial period — the skill must detect and handle this (normalize / exclude / flag), not treat it as a real drop.
- One stage (Product view → Add to cart) looks materially down vs the prior month.
- Thresholds: warning 10%, critical 25%.
- Want: anomalies with the Data Integrity Gate applied, period annotation on every metric, and one hypothesis with a funnel-impact estimate.

Expected: a report where every metric carries its period, the Gate result is shown (incl. incomplete-period handling), caveats propagate, and the impact math is marked illustrative.
