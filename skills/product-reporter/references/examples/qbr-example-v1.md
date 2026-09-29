> Gold exemplar for testing/output-evals.md (product-reporter — QBR rubric). Fixture: testing/fixtures/product-reporter/qbr-v1.md.

<!-- Golden exemplar for the product-reporter skill: quarter-review mode rendered as subtype qbr (since v3.6.0; template builtin://ops-report/qbr-v1.md, money bridge from builtin://partial/money-bridge-v1.md).
     Purpose: the ideal QBR for the fixture — the quality bar the judge scores against and a few-shot pattern for the skill.
     Generic/anonymized: Product 1, Competitor A, Person1…Person6, PROJ-1234 / PROJ-1300 / PROJ-1350, DL-10…DL-12. NO org-specific data; the numbers are fictional.
     Written in English as a neutral reference; a real run writes in the user's `user.language`.
     The fixture's remark from 1-1 notes is deliberately absent: org health is aggregate only, and People-contour data stays local.
     The ⚠️ lines under the money bridge and on DL-12 come from role_defaults.gate_emphasis (money-bridge, hippo-check); they add caveats, never questions.
     A real run appends the template marker after the altitude line (template-protocol T-5 step 5); it is left out here. -->

# QBR: Product 1 marketplace direction · Q3 2026 (2026-07-01 – 2026-09-30)

## Summary

- **Against the objective (O1 "Grow GMV profitably"):** all three key results missed — KR1 GMV **112.4 M vs 120.0 M** (−6.3%), KR2 contribution margin **−2.4% vs ≥ −1.5%**, KR3 checkout conversion **3.1% vs 3.5%**.
- **Biggest win:** ad revenue **0.8 M vs 0.6 M** plan (+33%) after sponsored listings opened to all sellers a month early (DL-10).
- **Biggest miss:** electronics GMV **−11% vs plan** after Competitor A's August price campaign; the counter-campaign added 0.2 M of marketing cost.
- **Decision needed:** approve the four commitments for the next quarter below.

Sources: finance export (Person5, 2026-10-05); analytics, ads and survey dashboards; `jira-internal`. Period for every number: 2026-07-01 – 2026-09-30 unless stated.

## Financials

Money in millions of the reporting currency. Source: finance export (Person5, 2026-10-05).

| Line | Plan | Actual | Δ | Full-year forecast | Cause of deviation |
|------|-----:|-------:|--:|-------------------:|--------------------|
| GMV | 120.0 | 112.4 | −7.6 (−6.3%) | 468 vs plan 490 (−4.5%) | Electronics −11% vs plan after Competitor A's price campaign (2026-08-03 – 2026-08-31); other categories on plan |
| Commission revenue | 9.0 | 8.4 | −0.6 (−6.7%) | 35.1 vs plan 36.8 (−4.6%) | Follows GMV; the 7.5% take rate held |
| Ad revenue | 0.6 | 0.8 | +0.2 (+33%) | 2.9 vs plan 2.4 (+21%) | Sponsored listings open to all sellers from 2026-08-01, a month early (DL-10) |
| Contribution margin, % of revenue | −1.5% | −2.4% | −0.9 pp | −2.0% vs plan −1.2% | The GMV miss and the counter-campaign |
| Marketing cost | 2.0 | 2.2 | +0.2 (+10%) | 8.4 vs plan 8.0 (+5%) | 3-week electronics counter-campaign (DL-11) |

## Money bridge

| Metric | Revenue driver | Expected effect |
|--------|----------------|-----------------|
| Checkout conversion — 3.1% vs 3.5% plan (−0.4 pp) | GMV → commission revenue | ≈ −6.0 M GMV → ≈ −0.45 M commission revenue in the quarter (−0.4 pp × 1.5 M GMV per 0.1 pp, finance model 2026-07; take rate 7.5%) |
| Sellers buying ads — 1,850 vs 1,500 plan | Ad revenue | — (not estimated): ad revenue is +0.2 M vs plan (finance export), but no per-seller sensitivity is given |

- Buyer NPS fell to **41** from 44 in the previous quarter (survey dashboard). ⚠️ No revenue mapping configured for Buyer NPS — its revenue effect stays unlinked.

## Initiatives

Source: `jira-internal`, 2026-07-01 – 2026-09-30. Across the direction: **34 of 46** planned features closed (74%).

| Initiative | Objective served | Status | Planned vs delivered | Next |
|------------|------------------|--------|----------------------|------|
| PROJ-1234 — Delivery cost transparency | KR3 checkout conversion | 🟡 At risk | 5 of 8 features | A/B test launch moved from 2026-10-26 to 2026-11-16 — the tariff API needs a cache (Person4, 2026-10-09) |
| PROJ-1300 — Sponsored listings for all sellers | KR2 contribution margin | ✅ Done — live since 2026-08-01 | 6 of 6 features | Closed; ad revenue tracked in next quarter's financials |
| PROJ-1350 — Seller onboarding revamp | KR1 GMV | 🔴 Slipped | 2 of 7 features | The other 5 move to the next quarter; two engineering roles are open |

## Market

- Competitor A ran an electronics price campaign, 2026-08-03 – 2026-08-31 (its website, 2026-08). It drove the GMV miss and the counter-campaign (DL-11).
- Competitor A added free delivery above an order threshold from 2026-09-15 (its press release, 2026-09-15). It bears on the delivery-cost test (PROJ-1234), which targets the same buyer concern.

## Org health

Aggregate only. Source: HR export (2026-09-30); tech-debt share from `jira-internal`.

- Headcount **42 of 45** planned; **3** open roles (2 engineering, 1 analyst); **1** leaver in the quarter.
- Capacity used **92%** of plan; tech-debt share **18%** of closed story points.

## Risks

| Risk | Likelihood | Impact | Owner | Mitigation |
|------|------------|--------|-------|------------|
| The tariff-API cache slips again; the A/B test misses 2026-11-16 and KR3 recovery moves into 2027 | Medium | High | Person4 | Agree the cache scope by 2026-10-23; fallback — test on the two largest carriers only |
| Competitor A keeps the price pressure on electronics next quarter | High | High | Person6 | A category margin floor; no second counter-campaign without a decision record |
| The open engineering roles stay unfilled; the onboarding revamp slips again | Medium | Medium | Person1 | Prioritise the two roles; agency sourcing from 2026-10 |

## Decisions taken

| Record | Date | Decision | Evidence |
|--------|------|----------|----------|
| DL-10 | 2026-07-14 | Open sponsored listings to all sellers on 2026-08-01, a month early | Beta advertiser retention 78% after 8 weeks (ads dashboard, 2026-05-01 – 2026-06-30) |
| DL-11 | 2026-08-06 | A 3-week counter-campaign in electronics, +0.2 M marketing | Electronics GMV −14% week over week, 2026-08-03 – 2026-08-09 (analytics dashboard) |
| DL-12 | 2026-08-20 | Pause the business-buyer pilot until 2027 | None recorded |

- ⚠️ DL-12 rests on a senior opinion (the CEO's call in the leadership meeting) and its record names no evidence — the input is labelled `assumed`.

## Commitments for next quarter

| # | Commitment | Owner | Date |
|---|------------|-------|------|
| 1 | Launch the delivery-cost A/B test (PROJ-1234) | Person2 | 2026-11-16 |
| 2 | Checkout conversion back to **3.4%** | Person2 | 2026-12-31 |
| 3 | Contribution margin at or above **−2.0%** for the quarter | Person1 | 2026-12-31 |
| 4 | Fill **2 of the 3** open roles | Person1 | 2026-12-15 |

Altitude: L3 · ↑ serves: direction objective O1 "Grow GMV profitably" (2026-07-01 – 2026-09-30) · ↓ next: agree the tariff-API cache scope by 2026-10-23 (PROJ-1234), then carry the four commitments into next quarter's plan (quarterly-planning)
