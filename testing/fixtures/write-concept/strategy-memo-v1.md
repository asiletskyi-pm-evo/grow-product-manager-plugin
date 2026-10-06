<!-- Output-eval fixture (input brief) for write-concept, subtype strategy-memo (since v3.6.0). Feed as the user request; score the resulting memo against the "write-concept — strategy memo" rubric in testing/output-evals.md. Gold reference: skills/write-concept/references/examples/strategy-memo-example-v1.md. Generic, no org data — the product, competitor, people and numbers are fictional. For the evaluator only (never part of the input; moved out of the brief in v3.8.0): Expected: a strategy memo with 2–4 strategic intents linked to O1 2027 where they serve it; each bet with its investment, expected return (or "not modelled"), stage and intent; proxy metrics with baseline, target, cadence and source; the two stops with what they free; kill criteria per bet with a signal and a date; base rates per bet — the business-buyer pilot says "none known", the n = 3 sample is flagged, and the 2025-02 market report is flagged as older than 12 months; and one closing altitude line whose `serves` is O1 2027 and whose `next` is a product step. -->

# Input brief

Write a **strategy memo** for Product 1 for 2027–2028: which bets we make beyond the core marketplace, and what we stop.

Setup:
- Role: `user.role: cpo` in `local-context.md` (confirmed at onboarding; no hat in the request). Step 0i resolves `role_defaults` per `references/role-profiles.md` §2 / §2b. The request names the subtype, so Step T declares `strategy-memo` from the request.
- Product: **Product 1** — a generic marketplace (buyers, sellers, delivery through carriers). Six product teams.
- Linked goal: the memo answers to the company objective **O1 2027 "Reach contribution-margin break-even for Product 1 by the end of 2027"**, approved by the board on 2026-09-15. The request links it.
- Roster: Person1 — CPO (the user) · Person2 — Head of Product, marketplace · Person3 — Data Analyst · Person4 — Backend Tech Lead · Person5 — Finance Lead.
- `user.language`: en for this fixture. The judge scores rigor, not wording — a run in another language is scored the same way.

## What the CPO gives

Business facts:
- GMV growth **+9% YoY** in H1 2026, down from **+24% YoY** in H1 2025 (finance dashboard, H1 2026 closed 2026-07-10).
- Take rate **7.5%** of GMV; contribution margin **−2.4%** of revenue in H1 2026 (finance dashboard).
- Revenue mix, H1 2026: commissions **88%**, ads (sponsored listings) **6%**, delivery fees **6%** (finance dashboard).
- Sponsored listings: **1,850 of 21,000** active sellers (8.8%) bought ads in 2026-07-01 – 2026-09-30 (ads dashboard).
- Integrated carriers carry about **70%** of orders (logistics dashboard, 2026-07-01 – 2026-09-30). Orders on integrated carriers get **38% fewer** "where is my order" contacts than orders on custom delivery rates (support-desk export, same period).
- **4%** of orders come from buyers who enter a company tax id at checkout (checkout data, H1 2026). Product 1 has no features for business buyers.

Work in progress that the CPO wants to stop by 2026-12-31, with both freed teams moving to bet 1 below:
- The own-warehouse fulfilment pilot: running since 2025-11 in one city, **0.8%** of orders, cost per order **2.3×** the carrier option (logistics finance review, 2026-08). One team.
- The social-commerce feed: in discovery since 2026-06. One team.

Market:
- Competitor A launched self-serve seller ads on 2026-03-12 (its press release). Outcome not public.
- An industry report says regional marketplace ad revenue grew **30%** in 2024 (report published 2025-02).

Outside view (internal history):
- Of **6** new revenue lines launched in 2021–2025, **2** reached their 18-month plan (internal portfolio review, 2025-12).
- All **3** carrier integrations of 2023–2025 reached their planned order share within 12 months (logistics review, 2025-12).
- Nothing known — internal or external — about business-buyer pilots.

Bets the CPO wants, with investment, return, targets and kill criteria:
1. **Self-serve seller ads** — two teams (the ones the two stops free), 2027–2028. Finance model (Person5, 2026-09): ads at 15% of active sellers ≈ **+2.0 M revenue per year** at the current revenue per advertiser. Target: 15% of active sellers buy ads by 2027-12-31. Kill: fewer than 12% by 2027-06-30 → stop self-serve expansion and keep managed ads only.
2. **Integrated delivery** — one team plus integration fees of about **0.4 M per year**. Finance model: 85% of orders on integrated carriers ≈ **−25%** "where is my order" contacts (not modelled as revenue). Target: 85% of orders by 2027-12-31. Kill: below 78% by 2027-06-30 → stop new integrations and renegotiate the existing ones.
3. **Business-buyer pilot** — one team for two quarters (2027-01 – 2027-06). Return not modelled. Target: 300 company buyers with 2 or more orders by 2027-06-30. Kill: fewer than 100 by 2027-03-31 → close the pilot.

Review cadence the CPO wants for the proxy metrics: monthly in the product review, quarterly with the board.

## Pre-answered skill questions (interactive run, answers supplied)

Product — Product 1 · new or existing functionality — both (existing ads beta and carrier integration; new business-buyer pilot) · audience — the board and the product leadership team · feature type — product strategy · blocks — the strategy-memo template's sections and the pre-selected items, no extra blocks, no Alternative Solutions · sources — this brief only (no Confluence, Drive or web search, no Product Analysis call) · Figma — not relevant · vault context — skip · red-team debate — no · publishing — keep in chat, no Confluence write · design-bridge handoff — skip · vault save — no.
