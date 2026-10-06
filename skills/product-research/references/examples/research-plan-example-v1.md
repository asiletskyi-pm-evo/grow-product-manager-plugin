> Gold exemplar for testing/output-evals.md (product-research — research plan rubric). Fixture: testing/fixtures/product-research/research-plan-v1.md.

<!-- Golden exemplar for the product-research skill, subtype research-plan (since v3.6.0; template builtin://research/research-plan-v1.md).
     Purpose: the ideal study plan for the fixture — the quality bar the judge scores against and a few-shot pattern for the skill.
     Generic/anonymized: Product 1, Person1…Person7, P1–P8, PROJ-1500, example.com. NO org-specific data; the numbers are fictional.
     Written in English as a neutral reference; a real run writes in the user's `user.language`.
     The Repository entry section comes from role_defaults.extra_sections.research (template-protocol T-5 step 3b): a user whose
     profile lists no extra section for research gets the same plan without it. Participants appear as ids only.
     Evidence classes (since v3.8.0): the ticket shares and the 2024-05 survey come from the researcher's brief (`user-text`), so
     they are `reported`; the plan cites nothing else. Simulated interviews only rehearse the guide — never counted, never cited.
     A real run appends the template marker after the altitude line (template-protocol T-5 step 5); it is left out here. -->

# Research Plan: Why new sellers stop listing in their first 30 days

## 1. Decision and question

- **Decision this study informs:** which new-seller problem the activation work (PROJ-1500) addresses first in 2027-H1 — listing creation, clarity of fees, or the wait for a first sale.
- **Research question:** Why do new sellers who publish a first listing add no new listing within 30 days — and which of the three problems weighs most in that choice?
- **Assumptions to test:**

| # | Assumption | Evidence so far | What would move the decision |
|---|------------|-----------------|------------------------------|
| A1 | Sellers stop because no sale comes in the first weeks | None direct ("payout timing", 17% of new-seller tickets, is related but not the same) | Stopped sellers had no sale and name the wait as the reason → first-sale support goes first |
| A2 | Sellers find out about fees too late | "Fees unclear" — **29%** of new-seller tickets | Sellers learned the fees after listing and name them → fee clarity goes first |
| A3 | A rejected listing gives no clear reason, and sellers give up | "Listing rejected" — **22%** of new-seller tickets | Rejections without a usable reason came right before stopping → listing creation goes first |

Evidence: reported — ticket shares from the support-desk export in Person1's brief (sellers in their first 30 days, 2026-07-01 – 2026-09-27).

- **Dropped from the study:** the acquisition channel of each seller (Person5's request). The answer would not change which problem goes first, and it costs interview time. It can be raised as a separate analytics question.

## 2. Method

- **Method:** mixed — remote semi-structured interviews (45 minutes) plus a cut of the onboarding funnel for the same cohort (Person3, due 2026-10-30).
- **Why this method:**
  - The question is *why* sellers stop and in what order things happened → interviews.
  - *How common* each problem is → the funnel cut and the ticket tags, not 8 interviews.
  - A usability test would show friction in listing creation only, not fees or the wait for a first sale.
- **Simulated interviews** (Person2's suggestion): they may be used to rehearse the discussion guide before fieldwork. They never count toward n and never enter the synthesis as evidence — anything they suggest is a hypothesis only.

## 3. Participants and recruiting

| Group | Inclusion criteria | n |
|-------|--------------------|--:|
| Stopped (P1–P5) | Registered 2026-06-01 – 2026-08-31, at least one listing, no new listing within the first 30 days | 5 |
| Kept going — contrast (P6–P8) | Registered in the same window, 3 or more listings within the first 30 days | 3 |

- **Recruiting criteria, exclusions, screener and channel:**
  - Exclusions: an open dispute or a blocked account; interviewed in the last 90 days; employees and their relatives; catalogues of more than 1,000 products imported in bulk.
  - Screener: 5 questions, built from the criteria and exclusions above.
  - Channel: a seller-support e-mail and a banner in the seller cabinet. Incentive: a one-month fee credit.
  - Participants appear as ids (P1–P8) in every output; names and contacts stay in the recruiting tool (Person7).
- **Planned n (real users):** **8** — 5 stopped, 3 contrast. It can show which problems exist and how they unfold. It cannot show how common each one is — that comes from the funnel cut and the ticket tags. With 3 contrast sellers, a difference between the groups is a signal, not a comparison.

## 4. Timeline and materials

| Phase | Dates | Owner |
|-------|-------|-------|
| Recruiting | 2026-10-12 – 2026-10-23 | Person7 |
| Onboarding funnel cut (second source) | by 2026-10-30 | Person3 |
| Sessions | 2026-10-26 – 2026-11-06 | Person1 |
| Synthesis and readout | 2026-11-09 – 2026-11-13 | Person1 |

- **Discussion guide:** TBD — to be drafted next (research/discussion-guide) and rehearsed before sessions start on 2026-10-26.
- **Consent and recording:** standard consent form; sessions recorded; recordings deleted 90 days after each session.

## 5. Confidence and validation

- **Expected confidence:** medium.
  - Interviews with 8 real sellers support *why* and *in what order*, not *how often*.
  - The funnel cut and the ticket tags are independent source types. A finding reaches high only where the interviews and at least one of them agree.
  - A finding from interviews alone stays medium; one that rests only on the 3 contrast sellers stays low.
- **Human-validated:** no — this plan is a model draft. It turns to yes only after a researcher has reviewed it.

## 6. Risks and limitations

| Risk | Effect | Mitigation |
|------|--------|------------|
| Sellers who stopped answer recruiting less often | Fewer than 5 in the stopped group | Invite from the whole cohort; if fewer than 5 by 2026-10-23, say so in the readout and lower the confidence of stopped-seller findings |
| Recall — reasons reconstructed weeks later | Tidy stories replace what happened | Ask for the sequence of events before asking for reasons |
| The fee-credit incentive attracts sellers still thinking about selling | Stopped group skews towards "almost stayed" | Note it in the synthesis; compare with the funnel cut |
| The seller-cabinet banner reaches only sellers who still log in | Stopped group recruited mainly by e-mail | Track the channel per participant (id only) |

- ⚠️ The 2024-05 seller survey (reported · Person1's brief, n = 1,200) is older than 12 months — context only, not evidence for this decision.

## Repository entry

| Field | Value |
|-------|-------|
| Study | Why new sellers stop listing in their first 30 days — which problem weighs most |
| Date | Fieldwork 2026-10-26 – 2026-11-06 (planned) |
| Participants | Planned: 8 real sellers — P1–P5 stopped, P6–P8 contrast; simulated: none counted (guide rehearsal only) |
| Method | Interviews + analytics (onboarding funnel cut) |
| Tags | seller onboarding · activation · first 30 days · listing creation · fees |
| Confidence | medium (expected) |
| Human-validated | no |
| Link | TBD — kept in chat, not saved |

Altitude: L2 · ↑ serves: PROJ-1500 "New-seller activation" · ↓ next: draft the discussion guide (research/discussion-guide) and rehearse it before sessions start on 2026-10-26; recruiting opens 2026-10-12
