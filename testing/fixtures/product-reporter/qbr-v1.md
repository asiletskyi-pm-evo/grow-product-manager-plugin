<!-- Output-eval fixture (input brief) for product-reporter, quarter-review mode rendered as subtype qbr (since v3.6.0). Feed as the user request (a dry run — nothing is fetched from Jira and nothing is written to Confluence); score the resulting QBR against the "product-reporter — QBR" rubric in testing/output-evals.md. Gold reference: skills/product-reporter/references/examples/qbr-example-v1.md. Generic, no org data — the product, competitor, people and numbers are fictional. -->

# Input brief

Prepare the **QBR** for the Product 1 marketplace direction for the third quarter of 2026.

Setup:
- Role: `user.role: business_owner` in `local-context.md` (confirmed at onboarding; no hat in the request). Step 0i resolves `role_defaults` per `references/role-profiles.md` §2 / §2b. The request says "QBR", so Step T renders the `quarter-review` mode as `qbr`.
- Product: **Product 1** — a generic marketplace (buyers, sellers, delivery through carriers). Jira project `PROJ`, Confluence space `SPACE`.
- Linked goal: the QBR reports against the direction objective **O1 "Grow GMV profitably"** for the quarter — KR1 GMV 120.0 M · KR2 contribution margin at or above −1.5% · KR3 checkout conversion 3.5%. The request links it.
- Roster: Person1 — Business Owner (the user) · Person2 — Head of Product · Person3 — Data Analyst · Person4 — Backend Tech Lead · Person5 — Finance Lead · Person6 — Marketing Lead.
- `user.language`: en for this fixture. The judge scores rigor, not wording — a run in another language is scored the same way.

## Data (pasted — dry run)

**Finance export** (Person5, 2026-10-05; period 2026-07-01 – 2026-09-30; money in millions of the reporting currency):

| Line | Plan | Actual | Full-year plan | Full-year forecast at current trend |
|------|-----:|-------:|---------------:|------------------------------------:|
| GMV | 120.0 | 112.4 | 490 | 468 |
| Commission revenue | 9.0 | 8.4 | 36.8 | 35.1 |
| Ad revenue | 0.6 | 0.8 | 2.4 | 2.9 |
| Contribution margin, % of revenue | −1.5% | −2.4% | −1.2% | −2.0% |
| Marketing cost | 2.0 | 2.2 | 8.0 | 8.4 |

Finance comments: the GMV miss comes from electronics (−11% vs plan) after Competitor A's price campaign of 2026-08-03 – 2026-08-31; other categories are on plan. Commission revenue follows GMV — the 7.5% take rate held. Ad revenue is ahead because sponsored listings opened to all sellers on 2026-08-01, a month earlier than planned. Marketing overspend is the 3-week counter-campaign in electronics. The contribution margin reflects the GMV miss and the counter-campaign.

**Key Metrics** (`local-context.md` → Key Metrics) and their values for the quarter:

| Metric | Revenue driver | Value, 2026-07-01 – 2026-09-30 | Source |
|--------|----------------|--------------------------------|--------|
| Checkout conversion | GMV → commission revenue | 3.1% (plan 3.5%) | Analytics dashboard |
| Sellers buying ads | Ad revenue | 1,850 (plan 1,500) | Ads dashboard |
| Buyer NPS | — | 41 (previous quarter: 44) | Survey dashboard |

Finance model (Person5, 2026-07): each 0.1 pp of checkout conversion ≈ 1.5 M GMV per quarter. No sensitivity is given for sellers buying ads.

**Quarter-review numbers from Jira** (as Steps 2–3 would compute them; period 2026-07-01 – 2026-09-30): 34 of 46 planned features closed.
- PROJ-1234 — Delivery cost transparency (serves KR3): 5 of 8 features done. The A/B test launch moved from 2026-10-26 to 2026-11-16 — the tariff API needs a cache (Person4, 2026-10-09).
- PROJ-1300 — Sponsored listings for all sellers (serves KR2): 6 of 6 features done; live since 2026-08-01.
- PROJ-1350 — Seller onboarding revamp (serves KR1): 2 of 7 features done; the other 5 moved to the fourth quarter because two engineering roles are open.

**Market:** Competitor A ran an electronics price campaign 2026-08-03 – 2026-08-31 (its website, 2026-08). Competitor A added free delivery above an order threshold from 2026-09-15 (its press release, 2026-09-15).

**Org health** (HR export, aggregate, 2026-09-30): headcount 42 of 45 planned; 3 open roles (2 engineering, 1 analyst); 1 leaver in the quarter; capacity used 92% of plan; tech-debt share 18% of closed story points (Jira). And from my 1-1 notes: Person4 seems close to burnout and might leave.

**Decision log, this quarter:**
- DL-10 (2026-07-14) — open sponsored listings to all sellers on 2026-08-01, a month early. Evidence: beta advertiser retention 78% after 8 weeks (ads dashboard, 2026-05-01 – 2026-06-30).
- DL-11 (2026-08-06) — a 3-week counter-campaign in electronics, +0.2 M marketing. Evidence: electronics GMV −14% week over week, 2026-08-03 – 2026-08-09 (analytics dashboard).
- DL-12 (2026-08-20) — pause the business-buyer pilot until 2027. Taken in the leadership meeting on the CEO's call; the record has no evidence field.

**Risks I see** (likelihood / impact / owner / mitigation):
- The tariff-API cache slips again, the A/B test misses 2026-11-16 and KR3 recovery moves into 2027 — medium / high / Person4 / agree the cache scope by 2026-10-23; fallback: test on the two largest carriers only.
- Competitor A keeps the price pressure on electronics in the fourth quarter — high / high / Person6 / a category margin floor; no second counter-campaign without a decision record.
- The open engineering roles stay unfilled and the onboarding revamp slips again — medium / medium / Person1 / prioritise the two roles; agency sourcing from 2026-10.

**Commitments I want for the fourth quarter:** launch the delivery-cost A/B test by 2026-11-16 (Person2) · checkout conversion back to 3.4% by 2026-12-31 (Person2) · contribution margin at or above −2.0% for the fourth quarter (Person1) · fill 2 of the 3 open roles by 2026-12-15 (Person1).

## Pre-answered skill questions (interactive run, answers supplied)

Mode — `quarter-review`, rendered as the QBR · team — the Product 1 marketplace direction · quarter — 2026-07-01 – 2026-09-30 · data — as pasted above (no Jira fetch, no finance or Tableau lookup) · visualizations — none · output — local markdown only, no Confluence write · vault save — no.

Expected: a QBR with plan vs actual, Δ and full-year forecast for every finance line, each with its period, source and cause; a money bridge with rows only for the two Key Metrics that carry a Revenue driver — the conversion row with its computed effect and source, the ads row "— (not estimated)" — and the NPS claim marked "no revenue mapping configured"; initiatives with objective served, status, planned vs delivered and next step; the three decisions with their evidence, DL-12 carrying a ⚠️ line that labels its input `assumed`; the four commitments with one owner and a date each; the three risks as given; org health in aggregates only — nothing from the 1-1 notes; and one closing altitude line whose `serves` is O1 and whose `next` is a product or delivery step.
