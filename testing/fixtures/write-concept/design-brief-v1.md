<!-- Output-eval fixture (input brief) for write-concept, subtype design-brief (since v3.6.0). Feed as the user request; score the resulting design brief against the "write-concept — design brief" rubric in testing/output-evals.md. Gold reference: skills/write-concept/references/examples/design-brief-example-v1.md. Generic, no org data — the product, people and numbers are fictional. For the evaluator only (never part of the input; moved out of the brief in v3.8.0): Expected: a design brief that frames the problem and never prescribes a screen or a solution (the courier-map request stays input and is ruled out by its constraint); segments with their share, context and the number of real users behind the evidence, with the guest gap flagged; confirmed constraints only, each with its source; one primary metric with baseline and target, a guardrail and the usability-round bar; an explicit out-of-scope list; open questions with one owner each; and one closing altitude line whose `serves` is KR2 via PROJ-1400 and whose `next` is a product step. -->

# Input brief

Write a **design brief** for what buyers see about their order after checkout.

Setup:
- Role: `user.role: product_designer` in `local-context.md` (confirmed at onboarding; no hat in the request). Step 0i resolves `role_defaults` per `references/role-profiles.md` §2 / §2b. The request names the subtype, so Step T declares `design-brief` from the request.
- Product: **Product 1** — a generic marketplace (buyers, sellers, delivery through carriers). Jira project `PROJ`, Confluence space `SPACE`.
- Linked goal: the brief sits under epic **PROJ-1400 "Post-purchase self-service"**, which serves the Q4 2026 product OKR key result **KR2 "Cut where-is-my-order contacts per 100 orders by 20%"**. The request links both.
- Roster: Person1 — Product Manager · Person2 — Product Designer (the user) · Person3 — Data Analyst · Person4 — Backend Tech Lead · Person6 — Head of Support.
- `user.language`: en for this fixture. The judge scores rigor, not wording — a run in another language is scored the same way.

## What the designer gives

Current state (existing functionality):
- After checkout, the order-details page (iOS, Android, web) shows one status label (Confirmed / Shipped / Delivered) and the carrier's tracking number as plain text. It shows no expected delivery date and no history of statuses.
- Notifications (push and e-mail) are sent on "Shipped" only.
- Guest buyers get an e-mail link to a guest order page with the same content.
- The current screens are in Figma: https://design.example.com/file/order-details

Evidence:
- Support-desk export, 2026-07-01 – 2026-09-27 (13 weeks): tag "where is my order" = **4.2 contacts per 100 orders**, the top buyer-contact tag at **31%** of all buyer contacts.
- Usability sessions, moderated, 2026-09-14 – 2026-09-18, run by Person2 with **5 real buyers** (P1–P3 on the app, P4–P5 on desktop web; all logged in, no guests):
  - 4 of 5 could not tell when the order would arrive.
  - 3 of 5 copied the tracking number to the carrier's website.
  - 2 of 5 (both on the app) did not find the order-details page from the home screen.
- Analytics dashboard, same 13 weeks: median **3 visits** to the order-details page between "Shipped" and "Delivered"; order share by segment — logged-in app **62%**, logged-in web **26%**, guest **12%**.

Confirmed constraints:
- Tracking statuses and an expected delivery date come only from integrated carriers, about **70%** of orders; sellers with custom delivery rates enter a free-text tracking number only (Person4, 2026-09-22).
- The carrier integration returns no courier location (Person4, 2026-09-22).
- Notifications go through the existing notification service; no new channel this quarter (Person4, 2026-09-22).
- No courier personal data (name, phone) on buyer screens (legal review, 2026-08).
- Existing Design System components and tokens only; WCAG 2.1 AA (product accessibility policy).

Stakeholder input: Person6 (Head of Support) asked for "a live map with the courier's location".

Success: KR2 above. Guardrail the designer wants: notification opt-out rate, baseline **1.8% per month** (2026-07 – 2026-09, notification-service dashboard), must not rise by more than 0.5 pp. Usability-round bar: at least 4 of 5 participants can tell the expected delivery day within 30 seconds.

Not in this brief: the returns and refunds flow, seller-side order management, adding or changing carriers.

Open questions the designer already knows, with owners:
- What a guest buyer sees and needs — no guest took part in the sessions (Person2).
- How to show orders from non-integrated carriers, which have no statuses (Person2).
- Whether a "delayed" state is needed, and what triggers it — how late carrier data arrives is unknown (Person4).
- Whether the "can't find the order on the app" signal is real — 2 of 5 sessions only (Person2).

## Pre-answered skill questions (interactive run, answers supplied)

Product — Product 1 · new or existing functionality — existing (order details) · audience — the product trio (Person1, Person2, Person4) and the design review · feature type — product / design change · blocks — the design-brief template's sections, no extra blocks, no Alternative Solutions · sources — this brief only (no Confluence, Drive or web search, no Product Analysis call) · Figma designs check — current screens confirmed at the link above, used by reference only · vault context — skip · red-team debate — no · publishing — keep in chat, no Confluence write · design-bridge handoff — skip · vault save — no.
