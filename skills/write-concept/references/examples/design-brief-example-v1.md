> Gold exemplar for testing/output-evals.md (write-concept — design brief rubric). Fixture: testing/fixtures/write-concept/design-brief-v1.md.

<!-- Golden exemplar for the write-concept skill, subtype design-brief (since v3.6.0; template builtin://concept/design-brief-v1.md).
     Purpose: the ideal design brief for the fixture — the quality bar the judge scores against and a few-shot pattern for the skill.
     Generic/anonymized: Product 1, Person1…Person6, PROJ-1400, example.com. NO org-specific data; the numbers are fictional.
     Written in English as a neutral reference; a real run writes in the user's `user.language`.
     Illustrates rigor and shape, not wording: the brief frames the problem and never prescribes screens, components or a solution.
     A real run appends the template marker after the altitude line (template-protocol T-5 step 5); it is left out here. -->

# Design brief: Order status after checkout

## Problem

After checkout, buyers cannot tell where their order is or when it will arrive. They contact support or leave Product 1 to check the carrier's website.

| What we see | Source · period |
|-------------|-----------------|
| "Where is my order" is the top buyer-contact tag: **4.2 contacts per 100 orders**, **31%** of all buyer contacts | Support-desk export · 2026-07-01 – 2026-09-27 (13 weeks) |
| **4 of 5** buyers could not tell when the order would arrive; **3 of 5** copied the tracking number to the carrier's website | Moderated usability sessions P1–P5 · 2026-09-14 – 2026-09-18 |
| Buyers come back to check: median **3 visits** to the order-details page between "Shipped" and "Delivered" | Analytics dashboard · same 13 weeks |
| **2 of 5** app users did not find the order-details page from the home screen | Usability sessions P1–P3 (app) · same week |

**Current state.** The order-details page (iOS, Android, web) shows one status label (Confirmed / Shipped / Delivered) and the tracking number as plain text — no expected delivery date, no status history. Notifications go out on "Shipped" only. Guests get an e-mail link to a guest order page with the same content. Current screens: [order details in Figma](https://design.example.com/file/order-details) (referenced, not reviewed in this run).

**Evidence coverage.** 5 real buyers (qualitative), the support-desk export and analytics — three independent source types agree that buyers cannot tell when the order arrives. The "cannot find the order on the app" signal rests on 2 of 5 sessions only: a hypothesis for the usability round, not a finding.

## Jobs to be done

- When my order has shipped, I want to know the day it will arrive, so I can plan to receive it. *(4 of 5 sessions; support tags)*
- When I want to check progress, I want to see it inside Product 1, so I don't have to copy a tracking number to the carrier's website. *(3 of 5 sessions)*
- When I come back to check my order on the app, I want to reach it from where I land, so I don't have to search for it. *(2 of 5 sessions — hypothesis)*

## Users and segments

| Segment | Share of orders | Context of use and platform | Frequency | Evidence behind it |
|---------|----------------:|-----------------------------|-----------|--------------------|
| Logged-in buyers, app | 62% | iOS and Android, often right after a notification | Median 3 order-page visits between Shipped and Delivered | 3 real users (P1–P3) + analytics + tickets |
| Logged-in buyers, web | 26% | Desktop and mobile web | Same median (not split by platform) | 2 real users (P4–P5) + analytics + tickets |
| Guest buyers | 12% | Guest order page opened from an e-mail link | Unknown | **None — 0 of 5 sessions were guests.** Evidence gap, see Open question 1 |

Share of orders: analytics dashboard, 2026-07-01 – 2026-09-27. Accessibility: WCAG 2.1 AA for every segment (see Constraints). Sellers are not a target segment of this brief — seller-side order management is out of scope.

## Constraints

- Tracking statuses and an expected delivery date exist only for integrated carriers — about **70%** of orders. Sellers with custom delivery rates enter a free-text tracking number only. *(Person4, 2026-09-22)*
- The carrier integration returns no courier location. *(Person4, 2026-09-22)*
- Notifications go through the existing notification service; no new channel this quarter. *(Person4, 2026-09-22)*
- No courier personal data (name, phone) on buyer screens. *(Legal review, 2026-08)*
- Existing Design System components and tokens only; WCAG 2.1 AA. *(Product accessibility policy)*
- Platforms: iOS, Android, web, and the guest order page. *(Current state)*

## Success metric

- **Primary:** "where is my order" contacts per 100 orders — baseline **4.2** (support-desk export, 2026-07-01 – 2026-09-27) → target **3.4** (−20%, key result KR2) by 2026-12-31.
- **Guardrail:** notification opt-out rate — baseline **1.8% per month** (notification-service dashboard, 2026-07 – 2026-09) — must not rise by more than **0.5 pp**.
- **Usability round:** an exploration passes when at least **4 of 5** participants can tell the expected delivery day within **30 seconds**.

## Out of scope

- The returns and refunds flow.
- Seller-side order management.
- Adding or changing carriers.
- A live map of the courier's location. Person6 (Head of Support) asked for it; it is kept as input, not as a requirement. The carrier integration returns no courier location (Person4, 2026-09-22), and the need behind the request — knowing when the order arrives — is job 1 above.

## Open questions

| # | Question — to answer before handoff | Owner |
|---|--------------------------------------|-------|
| 1 | What does a guest buyer see and need? No guest took part in the sessions. | Person2 |
| 2 | How do we show orders from non-integrated carriers, which have no statuses (about 30% of orders)? | Person2 |
| 3 | Is a "delayed" state needed, and what triggers it? How late carrier data arrives is unknown. | Person4 |
| 4 | Is the "cannot find the order on the app" signal real? It rests on 2 of 5 sessions. | Person2 |

## Related materials

- Epic PROJ-1400 "Post-purchase self-service" — serves the Q4 2026 product OKR key result KR2.
- Usability session notes, P1–P5, 2026-09-14 – 2026-09-18 (Person2).
- Support-desk export, tag "where is my order", 2026-07-01 – 2026-09-27.
- Analytics dashboard: order-page visits and order share by segment, same period.
- Current order-details screens: https://design.example.com/file/order-details

Altitude: L1 · ↑ serves: Q4 2026 KR2 "Cut where-is-my-order contacts per 100 orders by 20%" (via PROJ-1400) · ↓ next: two explorations of the order-status states in design-bridge, then the usability round with 5 participants, including guests (Open questions 1, 2 and 4)
