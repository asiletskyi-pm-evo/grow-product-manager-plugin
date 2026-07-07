<!-- Golden exemplar for the cjm-research skill (mode: anomalies + one hypothesis).
     Purpose: a worked, high-quality funnel-anomaly report the skill can pattern-match against (few-shot Examples context type).
     Generic/anonymized marketplace funnel — NO org-specific data. Also a fixture for testing/output-evals.md (cjm-research rubric).
     Demonstrates the plugin's signature rigor: period annotation on EVERY metric, Data Integrity caveats, funnel-impact math.
     Numbers are illustrative. -->

# CJM Anomaly Report — Marketplace funnel (illustrative)

**Template:** marketplace (6 stages) · **Period:** full calendar month, 1–31 May 2026 (complete) · **Baseline:** prior month (Apr 2026) · **Extract date:** 2 Jun 2026 (period complete — no normalization needed) · **Thresholds:** warning 10% / critical 25% of baseline.

## Funnel snapshot (period-annotated)
| Stage | Conv. (May 2026, full month) | Baseline (Apr 2026, full month) | Δ vs. baseline | Flag |
|-------|------------------------------|----------------------------------|----------------|------|
| Visit → Search | 62.0% | 61.2% | +1.3% | ✅ |
| Search → Product view | 48.5% | 49.1% | −1.2% | ✅ |
| Product view → Add to cart | 8.1% | 10.9% | **−25.7%** | 🔴 critical |
| Add to cart → Checkout start | 71.0% | 70.4% | +0.9% | ✅ |
| Checkout start → Payment | 66.5% | 66.0% | +0.8% | ✅ |
| Payment → Order complete | 97.2% | 97.0% | +0.2% | ✅ |

## Anomaly
**A1 — Product-view → Add-to-cart dropped 25.7% MoM (critical).**
- **Data Integrity Gate:** ✅ passed. Both periods are complete calendar months (extract 2 Jun, last point 31 May). Cross-validated against a second source (events pipeline vs. dashboard) — figures agree within 1.4% (< 15% variance threshold). Not a holiday-affected window.
- **⚠️ Caveat:** none material. Single methodology change checked — none in the period.
- **Scope:** concentrated on product pages without recent price/availability updates (secondary segment cut), suggesting a stale-listing or trust driver rather than a platform-wide regression.

## Hypothesis (with funnel impact)
**H1 — Weak-intent buyers leave the product page because there is no lightweight "save" action; some who would return-and-buy are lost at the add-to-cart step.**
- **Funnel-impact estimate:** recovering the Product-view→Add-to-cart stage from 8.1% back toward baseline 10.9% (+2.8pp) on the current product-view volume would lift overall Visit→Order conversion by ≈ +0.6pp absolute (chain-multiplied through downstream stages, which are stable). *(Illustrative; recompute on live volumes.)*
- **Confidence:** medium — anomaly is verified, but causal driver (stale listings vs. missing save affordance vs. pricing) needs disambiguation before build.
- **Next step:** disambiguate via segment analysis, then feed to `brainstorm-features` (ICE) — candidate: Save-for-later (see write-concept / requirements-creator exemplars).

## Verification checklist
- [x] Every cited metric carries its period.
- [x] ≥ 2 sources cross-validated for the critical anomaly.
- [x] Holiday / methodology-change screening done.
- [x] Impact math shown and marked illustrative.

## Sources
- Funnel dashboard (marketplace workbook), period 1–31 May 2026 · Events pipeline (cross-validation) · both internal, period-annotated.
