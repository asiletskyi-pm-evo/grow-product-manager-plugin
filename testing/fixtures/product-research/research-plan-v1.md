<!-- Output-eval fixture (input brief) for product-research, subtype research-plan (since v3.6.0). Feed as the user request; score the resulting plan against the "product-research — research plan" rubric in testing/output-evals.md. Gold reference: skills/product-research/references/examples/research-plan-example-v1.md. Generic, no org data — the product, people and numbers are fictional. For the evaluator only (never part of the input; moved out of the brief in v3.8.0): Expected: a research plan with one decision and one primary question (the acquisition-channel question dropped with its reason); a method matched to the question, with simulated interviews allowed only to rehearse the guide and never counted in n; planned n of real sellers per group, as ids only, with what n = 8 can and cannot support; recruiting criteria, exclusions, screener, channel, incentive, timeline and owners; an expected-confidence label with its reason; `Human-validated: no`; the role's Repository entry section above the altitude line; and one closing altitude line whose `serves` is PROJ-1500 and whose `next` is a product step. -->

# Input brief

Draft a **research plan** for a study on why new sellers stop listing in their first 30 days.

Setup:
- Role: `user.role: ux_researcher` in `local-context.md` (confirmed at onboarding; no hat in the request). Step 0i resolves `role_defaults` per `references/role-profiles.md` §2 / §2b — including `extra_sections.research` = `repository-entry`, which template-protocol T-5 step 3b inserts above the altitude line. The request names the subtype, so Step T declares `research-plan` from the request.
- Product: **Product 1** — a generic marketplace (buyers, sellers, delivery through carriers). Jira project `PROJ`, Confluence space `SPACE`.
- Linked goal: the study feeds initiative **PROJ-1500 "New-seller activation"** (roadmap Next). The request links it.
- Roster: Person1 — UX Researcher (the user) · Person2 — Product Manager, seller experience · Person3 — Data Analyst · Person5 — Marketing Lead · Person7 — Research Operations.
- `user.language`: en for this fixture. The judge scores rigor, not wording — a run in another language is scored the same way.

## What the researcher gives

The decision: which new-seller problem the activation work (PROJ-1500) addresses first in 2027-H1 — listing creation, clarity of fees, or the wait for a first sale.

Evidence so far:
- Of sellers who registered 2026-04-01 – 2026-06-30 and published at least one listing, **46%** added no new listing within their first 30 days (seller analytics dashboard, cohort data through 2026-07-30).
- Support tickets from sellers in their first 30 days, 2026-07-01 – 2026-09-27 (support-desk export): top tags "fees unclear" **29%**, "listing rejected" **22%**, "payout timing" **17%**.
- The last study of new sellers is a seller survey from 2024-05 (n = 1,200).

Assumptions to test:
- A1 — sellers stop because no sale comes in the first weeks.
- A2 — sellers find out about fees too late.
- A3 — a rejected listing gives no clear reason, and sellers give up.

Method and sample the researcher wants:
- Remote semi-structured interviews, 45 minutes, plus a cut of the onboarding funnel for the same cohort by Person3 as a second source type (due 2026-10-30).
- **8 real sellers**: 5 who stopped (registered 2026-06-01 – 2026-08-31, at least one listing, no new listing within 30 days) and 3 who kept going (3 or more listings in their first 30 days) as a contrast.
- Exclusions: an open dispute or a blocked account; interviewed in the last 90 days; employees and their relatives; catalogues of more than 1,000 products imported in bulk.
- Screener of 5 questions; recruiting through a seller-support e-mail and a banner in the seller cabinet; incentive — a one-month fee credit.
- Consent through the standard consent form; sessions recorded, recordings deleted after 90 days.

Timeline and owners: recruiting 2026-10-12 – 2026-10-23 (Person7) · sessions 2026-10-26 – 2026-11-06 (Person1) · synthesis and readout 2026-11-09 – 2026-11-13 (Person1).

Two requests from colleagues, which the researcher asks the plan to handle:
- Person2 suggests adding 5 simulated seller interviews run with an LLM "to fill the sample faster".
- Person5 wants each interview to ask which acquisition channel brought the seller.

The discussion guide is not written yet.

## Pre-answered skill questions (interactive run, answers supplied)

Product — Product 1 · new or existing functionality — existing (seller onboarding) · research type — a research plan (study plan before fieldwork), not a synthesis · subject — new sellers in their first 30 days · depth — plan only · goal — the decision above · audience — the PROJ-1500 product trio and the seller-experience lead · existing knowledge and assumptions — as given above · internal documents — this brief only · time frame — as given · sources — this brief only (no Confluence, Drive or web search, no Product Analysis call) · Deep Research in ChatGPT — no · Deep Research in Gemini — no · Knowledge Library — skip · Figma — not relevant · red-team debate — no · publishing — keep in chat, no Confluence write · design-bridge handoff — skip · vault save — no.
