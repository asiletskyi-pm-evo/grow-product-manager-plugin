<!-- Output-eval fixture (input brief) for task-creator. Feed as the user request (run it as a dry run — nothing is created in Jira); score the resulting task set against the task-creator rubric in testing/output-evals.md. Gold reference: skills/task-creator/references/examples/tasks-example-v1.md. Generic, no org data. For the evaluator only (never part of the input; moved out of the brief in v3.8.0): Expected: one task per selected discipline (BE, FE, iOS, Android, QA, Analytics), each parented to PROJ-1234, carrying the work-type label + feature code `PROJ-1234.3`, a Why / What / How / Definition of Done / Requirements body traced to the FR and AC numbers above, no engineering detail invented beyond the requirements, the dependency links, and the post-creation verification. -->

# Input brief

Create Jira tasks under Epic **PROJ-1234** from the approved requirements below (dry run).

Context the PM gives:
- Product: **Product 1** (a generic marketplace). Reporter: Person1 Surname1; team: Team 1 — both from `local-context.md`.
- Purpose: development tasks (not grooming). Not an A/B test — staged rollout behind a feature flag.
- Work types: **BE, FE (web), iOS, Android, QA, Analytics**. No Design task — the mockups are approved and linked in the requirements.
- QA is one task with label `qa`; it runs after FE, iOS and Android are done.
- Components: the page label `orders`.

## Requirements excerpt — "PROJ-1234.3 - Buyer order cancellation before shipment" (status: Approved)

- **Page:** https://confluence.example.com/wiki/spaces/SPACE/pages/100001 · **Page label:** `orders`
- **Epic:** PROJ-1234 "Buyer self-service for orders"
- **Design:** approved mockups — https://design.example.com/file/order-cancel
- **Platforms:** web (desktop and mobile web), iOS, Android
- **Goal:** today a buyer who wants to cancel an unshipped order has to contact support or the seller. Let buyers cancel it themselves.
  - Primary metric: share of buyer cancellations done in self-service.
  - Guardrail: overall order cancellation rate must not grow by more than 0.5 pp vs. the 4 weeks before release.
- **Rollout:** feature flag `buyer_order_cancel`, 10% → 50% → 100%.

**Functional requirements**
1. **FR-1** Order details show a "Cancel order" action when the order status is New or Confirmed. It is hidden for Shipped, Delivered and Cancelled.
2. **FR-2** The action opens a confirmation step with a required reason from a fixed list: Changed my mind · Found a better price · Ordered by mistake · Delivery takes too long · Other (optional comment, up to 300 characters). Confirm stays disabled until a reason is chosen.
3. **FR-3** On confirm, the order status becomes "Cancelled by buyer". The reason and comment are saved with the order and shown in the seller's order view. The seller is notified through the existing order-notification channel.
4. **FR-4** A prepaid order starts the existing refund process. The buyer sees "Refund initiated" on the order and in the confirmation message. No new refund logic.
5. **FR-5** If the order became Shipped after the screen was opened, the cancellation is rejected. The buyer sees "This order has already been shipped and can no longer be cancelled", and the screen refreshes to the current status.
6. **FR-6** With the flag `buyer_order_cancel` off, no cancel action is shown on any platform.

**Analytics events:** `order_cancel_click`, `order_cancel_confirm` (order_id, reason, is_prepaid, platform), `order_cancel_rejected` (order_id, platform, rejection_reason).

**Acceptance criteria**
| # | Given / When / Then |
|---|---------------------|
| AC-1 | GIVEN an order in status New or Confirmed, WHEN the buyer opens order details on web, iOS or Android, THEN "Cancel order" is visible. |
| AC-2 | GIVEN an order in status Shipped, Delivered or Cancelled, WHEN the buyer opens order details, THEN no cancel action is shown. |
| AC-3 | GIVEN the confirmation step, WHEN no reason is selected, THEN Confirm is disabled. |
| AC-4 | GIVEN a prepaid order in status Confirmed, WHEN the buyer confirms with a reason, THEN the status is "Cancelled by buyer", the seller sees the reason and is notified, AND the buyer sees "Refund initiated". |
| AC-5 | GIVEN the order became Shipped after the screen was opened, WHEN the buyer confirms, THEN the cancellation is rejected, the FR-5 message is shown AND the screen shows the current status. |
| AC-6 | GIVEN the flag is off, WHEN any buyer opens order details on any platform, THEN no cancel action is shown. |
| AC-7 | GIVEN a cancellation attempt, WHEN the buyer taps, confirms or is rejected, THEN the matching event fires with all listed parameters on every platform. |

**Out of scope:** cancellation after shipment (returns flow), partial cancellation of multi-item orders, changes to the refund process itself.
