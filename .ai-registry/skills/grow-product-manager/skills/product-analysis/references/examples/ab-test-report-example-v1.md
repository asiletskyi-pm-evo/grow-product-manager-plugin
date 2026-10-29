<!-- Golden exemplar for the product-analysis skill (mode: A/B Test Results, since v3.7.0).
     Purpose: a worked A/B test report the skill can pattern-match against (few-shot Examples context type), and the gold reference for the product-analysis A/B rubric in testing/output-evals.md (fixture: testing/fixtures/product-analysis/ab-readout-v1.md).
     Generic marketplace test — NO org-specific data. Numbers are illustrative.
     Demonstrates: a verdict per platform and per guardrail that follows the pre-set criteria and the AB-4 recommendation definitions rather than the PM's leaning ("roll it out everywhere"), validity limits made explicit (one source, Android power, the week-2 fade), evidence labels (since v3.8.0: the results the PM pasted are `user-text`, so `reported` and not `measured`; a randomised readout gets no hand-back line; one group label under the verdict covers the report because every value shares class and source, the quoted support theme is attributed to the PM, not to a customer, and the pooled-guardrail assumption the confidence line rests on carries its `assumed` label), and the judgment footer — the confidence line (references/judgment-points.md §3, Gate 4c) directly above the altitude line (Gate 4a). The PM's own call and the "Your estimate vs mine" comparison stay in the chat, never in the report. -->

# A/B Test Report — `one-page-checkout` (illustrative)

## 1. Executive Summary

**Verdict: lost — the success criteria are not met** (test window 1–14 Sep 2026).

Evidence: reported — results the PM pasted for 1–14 Sep 2026 (one source; see Sources).

| Criterion | Result |
|---|---|
| Checkout completion, web | met |
| Checkout completion, Android | inconclusive (41 % of planned power) |
| Support-contacts guardrail | breached (+6 %, p = 0.04, 1–14 Sep 2026, pooled) |

**Recommended action:** stop and iterate. Make the delivery option easy to find on the one-page checkout, then re-test on web and Android with Android sized to its planned power.

## 2. Test Setup

- **Hypothesis:** one checkout page instead of three raises checkout completion.
- **Groups:** control = three-step checkout; test = one page. Split 50 / 50, stable for the whole run.
- **Platforms and window:** web and Android, 1–14 Sep 2026 (14 days, as planned).
- **Success criterion:** checkout completion up by +2 % relative or more, at p < 0.05.
- **Guardrails:** average order value and support contacts per order must not get worse.

## 3. Primary Metrics Results (1–14 Sep 2026)

| Metric | Platform | Control | Test | Δ (rel.) | p | Power reached | Verdict |
|---|---|---|---|---|---|---|---|
| Checkout completion | Web | 61.8 % | 64.1 % | +3.7 % | < 0.001 | 104 % | ✅ met |
| Checkout completion | Android | 58.0 % | 58.9 % | +1.6 % | 0.15 | 41 % | ⚪ inconclusive |

## 4. Secondary Metrics Results (1–14 Sep 2026, web + Android pooled)

| Metric | Δ (rel.) | p | Verdict (must not get worse) |
|---|---|---|---|
| Average order value | −0.4 % | n.s. | ✅ met |
| Support contacts per order | +6 % | 0.04 | ❌ not met |

⚠️ Most of the extra support contacts are "where is my delivery option" questions on the test page (reported · the PM's summary of the support contacts, 1–14 Sep 2026). The guardrails arrived pooled, so the breach cannot yet be attributed to one platform.

## 5. Segment Breakdown

Web carries the primary result. Android is under-powered (41 % of the planned sample): its +1.6 % (1–14 Sep 2026) is neither a win nor a loss, and it gives no basis for a blanket rollout.

## 6. Time Dynamics (web)

| Week | Relative lift |
|---|---|
| Week 1 (1–7 Sep 2026) | +5.1 % |
| Week 2 (8–14 Sep 2026) | +2.4 % |

The lift is fading and ends only 0.4 points of relative lift above the +2 % bar (week 2, 8–14 Sep 2026). A novelty effect is not ruled out, and the steady-state lift may fall below the bar.

## 7. Test Validity Assessment

- ✅ **Duration and split:** 14 days as planned; split stable.
- ✅ **External factors:** no holidays, promotions, outages or methodology change.
- ⚠️ **Sources:** one source — the results the PM pasted; cross-validation against a second source is pending.
- ❌ **Android power:** 41 % of the planned sample, so no verdict there.
- ⚠️ **Novelty:** the web lift fades from week 1 to week 2.
- ⚠️ **Guardrails:** reported pooled, not by platform.

## 8. Conclusions

- **Checkout completion +2 % or more:** met on web; inconclusive on Android.
- **Average order value not worse:** met.
- **Support contacts per order not worse:** not met (+6 %, p = 0.04, 1–14 Sep 2026, pooled).

## 9. Recommendation

**Stop and iterate.** The test breached a pre-set guardrail and has no result on Android, so a rollout is not justified — on web or anywhere else. Keep the three-step checkout.

What to change:
- Move the delivery option above the payment block on the one-page layout.

How to re-test:
- Re-test on web and Android, with Android sized to its planned power.
- Split the guardrails by platform.

What to monitor in the re-test:
- the week-over-week web lift;
- support contacts per order, per platform.

## 10. Hypotheses for follow-up

- **H1.** The support spike comes from the delivery option being hidden below the fold on the one-page layout. Moving it above the payment block brings support contacts per order back to control levels without losing the web lift.
- **H2.** The Android effect is real but smaller than on web. Read it again at full power.

## 11. Glossary

- **Power reached:** the share of the sample size the test needed to detect the target effect.
- **Relative Δ:** (test − control) / control.
- **Guardrail:** a metric that must not get worse for the test to count as a success.

## 12. Sources

Results for `one-page-checkout` pasted by the PM (test window 1–14 Sep 2026): conversion, guardrails and weekly web lift — `user-text` → `reported` (PM). This is a single source; cross-validation is pending.

Confidence: uncertain · most sensitive to: the support-contact rise holding on web as well as Android [assumed — the +6 % for 1–14 Sep 2026 is pooled] · would change if: the web-only split of support contacts per order for 1–14 Sep 2026 shows no rise (Δ ≤ 0 %), which would move web to "roll out with caveats"
Altitude: L2 · ↑ serves: — (no linked goal) · ↓ next: move the delivery option above the payment block and re-test on web and Android at the planned power
