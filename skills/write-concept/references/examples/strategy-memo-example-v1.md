> Gold exemplar for testing/output-evals.md (write-concept — strategy memo rubric). Fixture: testing/fixtures/write-concept/strategy-memo-v1.md.

<!-- Golden exemplar for the write-concept skill, subtype strategy-memo (since v3.6.0; template builtin://concept/strategy-memo-v1.md).
     Purpose: the ideal strategy memo for the fixture — the quality bar the judge scores against and a few-shot pattern for the skill.
     Generic/anonymized: Product 1, Competitor A, Person1…Person5. NO org-specific data; the numbers are fictional.
     Written in English as a neutral reference; a real run writes in the user's `user.language`.
     Illustrates rigor and shape, not wording: every bet carries its investment, return, stage, proxy metric, kill criterion and base rate.
     This is the concept-level memo of bets — not focus-advisor's quarterly attention memo, and not a decision record (decision-log).
     A real run appends the template marker after the altitude line (template-protocol T-5 step 5); it is left out here. -->

# Strategy memo: Product 1 beyond the core marketplace

**Horizon:** 2027–2028

## Context

Growth is slowing while the margin is still negative, and the board has set a break-even deadline.

| Fact | Source · date |
|------|---------------|
| GMV growth **+9% YoY** in H1 2026, down from **+24% YoY** in H1 2025 | Finance dashboard · H1 2026 closed 2026-07-10 |
| Take rate **7.5%** of GMV; contribution margin **−2.4%** of revenue | Finance dashboard · H1 2026 |
| Commissions are **88%** of revenue; ads **6%**, delivery fees **6%** | Finance dashboard · H1 2026 |
| Company objective **O1 2027**: contribution-margin break-even for Product 1 by the end of 2027 | Board approval · 2026-09-15 |

The strategic question: which bets outside the core commission business move Product 1 towards O1 2027, and what do we stop to fund them?

## Strategic intents

1. **Grow revenue that does not depend on commission growth.** Serves O1 2027 — commissions are 88% of revenue while GMV growth slows.
2. **Make delivery predictable and cheaper to serve.** Serves O1 2027 — fewer support contacts per order, no costly own-warehouse logistics.
3. **Learn whether business buyers are a segment worth serving.** No linked objective — an exploration; the pilot exists to size it.

## Bets

| Bet | Investment | Expected return | Stage | Intent served |
|-----|------------|-----------------|-------|---------------|
| 1. Self-serve seller ads | 2 teams (both freed by the stops), 2027–2028 | ≈ **+2.0 M revenue per year** at 15% of active sellers (finance model, Person5, 2026-09) | Expand | 1 |
| 2. Integrated delivery | 1 team + integration fees ≈ **0.4 M per year** | ≈ **−25%** "where is my order" contacts at 85% of orders (finance model, 2026-09); revenue effect not modelled | Expand | 2 |
| 3. Business-buyer pilot | 1 team for two quarters (2027-01 – 2027-06) | Not modelled — sizing it is the pilot's job | Explore | 3 |

**Trade-offs.**
- The ads bet takes only freed capacity: it exists because the two stops below happen.
- The pilot's team is not freed by a stop. It comes out of the other four teams for two quarters, so in 2027-H1 four of the six teams work on the bets, and three from 2027-07.
- The delivery bet adds a recurring cost (≈ 0.4 M per year) against a benefit that is modelled in support contacts, not in revenue. Its case for O1 2027 rests on cost-to-serve.

## Proxy metrics

| Bet | Leading indicator | Baseline · period | Target | Review cadence | Source |
|-----|-------------------|-------------------|--------|----------------|--------|
| 1 | Share of active sellers buying ads | **8.8%** (1,850 of 21,000) · 2026-07-01 – 2026-09-30 | 15% by 2027-12-31 | Monthly product review; quarterly with the board | Ads dashboard |
| 2 | Share of orders on integrated carriers | **≈ 70%** · 2026-07-01 – 2026-09-30 | 85% by 2027-12-31 | Monthly; quarterly with the board | Logistics dashboard |
| 3 | Company buyers with 2 or more orders | Not measured yet — first reading at pilot start, 2027-01 | 300 by 2027-06-30 | Monthly; quarterly with the board | Checkout data (company tax id) |

Context for bet 2: orders on integrated carriers already get 38% fewer "where is my order" contacts than orders on custom rates (support-desk export, 2026-07-01 – 2026-09-30).

## What we stop

| Stop | By | What it frees |
|------|----|---------------|
| Own-warehouse fulfilment pilot (one city since 2025-11, 0.8% of orders) | 2026-12-31 | 1 team → bet 1; ends a per-order cost of **2.3×** the carrier option (logistics finance review, 2026-08) |
| Social-commerce feed (in discovery since 2026-06) | 2026-12-31 | 1 team → bet 1 |

## Kill criteria

Fixed in this memo, before the first reading arrives.

| Bet | Signal | Date | Then |
|-----|--------|------|------|
| 1. Self-serve seller ads | Fewer than **12%** of active sellers buy ads | 2027-06-30 | Stop the self-serve expansion; keep managed ads only |
| 2. Integrated delivery | Integrated carriers below **78%** of orders | 2027-06-30 | Stop new integrations; renegotiate the existing ones |
| 3. Business-buyer pilot | Fewer than **100** company buyers with 2 or more orders | 2027-03-31 | Close the pilot |

## Base rates / outside view

| Bet | Reference class | Success rate | Source |
|-----|-----------------|--------------|--------|
| 1. Self-serve seller ads | New revenue lines launched by Product 1 in 2021–2025 | **2 of 6** (33%) reached their 18-month plan | Internal portfolio review, 2025-12 |
| 2. Integrated delivery | Carrier integrations of 2023–2025 | **3 of 3** reached their planned order share within 12 months | Logistics review, 2025-12 |
| 3. Business-buyer pilot | — | **None known** — no internal history, no external source | — |

- Bet 1: one in three is the outside view, so the 2027-06-30 kill date carries real weight. Competitor A launched self-serve seller ads on 2026-03-12 (its press release), but the outcome is not public, so it gives no rate.
- ⚠️ Bet 2: n = 3 is a small sample — directional, not a rate to plan on.
- ⚠️ The industry report on regional marketplace ad revenue (+30% in 2024) was published in 2025-02 — older than 12 months. Market context only, not a base rate for a launch.
- Bet 3: with no base rate, the 2027-03-31 kill date is the only guard against sunk cost.

## Related materials

- Finance dashboard — H1 2026 (closed 2026-07-10); finance model for bets 1 and 2 (Person5, 2026-09).
- Ads, logistics and support-desk data — 2026-07-01 – 2026-09-30.
- Internal portfolio review (2025-12); logistics review (2025-12); logistics finance review (2026-08).
- Board approval of O1 2027 — 2026-09-15.

Altitude: L4 · ↑ serves: O1 2027 "Reach contribution-margin break-even for Product 1 by the end of 2027" · ↓ next: record the two stops in decision-log, then carry the three bets and their kill dates into the 2027-H1 plan (quarterly-planning)
