# Task breakdown: Buyer order cancellation before shipment (PROJ-1234.3)

> Gold exemplar for testing/output-evals.md (task-creator rubric). Fixture: testing/fixtures/task-creator/brief-v1.md.

<!-- Golden exemplar for the task-creator skill: a worked, high-quality run from requirements to a linked task set (few-shot Examples context type).
     Generic/anonymized — placeholders only (PROJ-1234, SPACE, example.com, Product 1, Person1 Surname1). Illustrates rigor and shape, not a rigid
     template: the real structure comes from SKILL.md Step 7 and the resolved template. Task text is written in `user.language`; this exemplar
     happens to use English. Keys PROJ-1301…PROJ-1306 stand for the keys Jira returns on creation. -->

## 1. Run parameters (Steps 1–5)

| Parameter | Value | Source |
|-----------|-------|--------|
| Requirements page | [PROJ-1234.3 - Buyer order cancellation before shipment](https://confluence.example.com/wiki/spaces/SPACE/pages/100001) — status Approved | User link (Step 1) |
| Feature name / code | Buyer order cancellation before shipment / `PROJ-1234.3` | Page title |
| Epic | PROJ-1234 "Buyer self-service for orders" — exists, status In Progress | Page "Epic" section, confirmed with `getJiraIssue` (Step 2) |
| Task purpose | Development (no `grooming` label, no "Grooming" in titles) | User answer (Step 4) |
| A/B test | No — staged rollout behind flag `buyer_order_cancel` (FR-6) → no `a/b_test` label, one Analytics task | Page "Rollout" + user answer |
| Work types | BE, Analytics, FE, iOS, Android, QA | User answer |
| Design task | Not created — mockups already approved and linked in the requirements | User answer |

## 2. Pre-creation summary (Step 6b) — confirmed by the user before creation

| Field | Value | Source / confidence |
|-------|-------|---------------------|
| Parent (Epic) | PROJ-1234 | Certain — page "Epic" section + `getJiraIssue` |
| Reporter | Person1 Surname1 (`<account-id>`) | Certain — `user.jira_account_id` in `local-context.md` |
| Team | Team 1 (`<team-uuid>-NN`) | Certain — `team.jira_team_id` in `local-context.md` |
| Components | `orders` | Inferred — page label; matches existing tasks in PROJ-1234 → confirmed by the user |
| Labels (all tasks) | `PROJ-1234.3` (feature code) + the work-type label below | Certain — page title |
| Work-type labels | BE `backend` · FE `frontend` · iOS `iOS`, `app` · Android `Android`, `app` · Analytics `Analytics` · QA `qa` | Skill table; `qa` is not in the skill's table — taken from the brief, confirmed by the user |
| Issue type | Task for all six | Certain — the project has no Analytics or QA issue type (`getJiraProjectIssueTypesMetadata`) |
| Assignee / "How" depth | Not set; moderate checklist in "How" | Assumption — no person profiles for the team, so no D-level tuning |
| Estimate (story points) | Not set — the team estimates at grooming | The requirements carry no estimates; none invented (Gate 1) |
| Template | `task-builtin-default` 1.0.0 — no product template for Product 1 | Step T (batch: resolved once) |

**Batch quality gate** (form + groundedness lenses, independent checker): 3 findings, 3 fixed, 0 disputed — a BE "How" step that named an endpoint path (absent from the requirements, removed); two "What" blocks written as prose (rewritten as lists).

## 3. Requirements coverage

Every functional requirement and acceptance criterion lands in at least one task; nothing in a task comes from outside the page.

| Requirement | BE | Analytics | FE | iOS | Android | QA |
|-------------|----|-----------|----|-----|---------|----|
| FR-1 Action shown for New / Confirmed only | ✓ | | ✓ | ✓ | ✓ | ✓ |
| FR-2 Required reason, "Other" comment ≤ 300 chars | ✓ | | ✓ | ✓ | ✓ | ✓ |
| FR-3 "Cancelled by buyer", reason to seller, seller notified | ✓ | | ✓ | ✓ | ✓ | ✓ |
| FR-4 Prepaid → existing refund, "Refund initiated" | ✓ | | ✓ | ✓ | ✓ | ✓ |
| FR-5 Already shipped → rejected, message, refresh | ✓ | | ✓ | ✓ | ✓ | ✓ |
| FR-6 Flag `buyer_order_cancel` | ✓ | | ✓ | ✓ | ✓ | ✓ |
| Analytics events (3) + metrics | | ✓ | ✓ | ✓ | ✓ | ✓ |
| AC-1 Action visible for New / Confirmed | | | DoD | DoD | DoD | DoD |
| AC-2 No action for Shipped / Delivered / Cancelled | DoD | | DoD | DoD | DoD | DoD |
| AC-3 Confirm disabled without a reason | | | DoD | DoD | DoD | DoD |
| AC-4 Prepaid cancellation end to end | DoD | | DoD | DoD | DoD | DoD |
| AC-5 Already shipped → rejected | DoD | | DoD | DoD | DoD | DoD |
| AC-6 Flag off → no action | DoD | | DoD | DoD | DoD | DoD |
| AC-7 Events fire on every platform | | DoD (spec) | DoD | DoD | DoD | DoD |

## 4. Tasks

### 4.1 PROJ-1301 — [BE] Buyer order cancellation before shipment - Support buyer cancellation with reason, seller notice and refund start

| Issue type | Parent | Labels | Components | Team | Reporter |
|------------|--------|--------|------------|------|----------|
| Task | PROJ-1234 | `backend`, `PROJ-1234.3` | `orders` | Team 1 | Person1 Surname1 |

```markdown
## Why

A buyer who wants to cancel an unshipped order has to contact support or the seller today. The backend decides whether a cancellation is allowed, so it is the source of truth for every client. Goal: raise the share of self-service cancellations while the overall cancellation rate stays within +0.5 pp.

## What

- A cancellation is accepted only for orders in status New or Confirmed; any other status is rejected (FR-1, FR-5).
- A reason from the fixed list is required; "Other" accepts an optional comment up to 300 characters (FR-2).
- A successful cancellation sets status "Cancelled by buyer", saves the reason and comment with the order, shows them in the seller's order view and notifies the seller through the existing order-notification channel (FR-3).
- A prepaid order starts the existing refund process and carries the "Refund initiated" state for clients to show (FR-4).
- A cancellation for an order that has become Shipped returns a distinct "already shipped" result, so clients can show the FR-5 message.
- Everything sits behind the flag `buyer_order_cancel` (FR-6).

## How

- Read FR-1 to FR-6 and AC-2 to AC-6 on the requirements page.
- Agree the cancellation contract (inputs, success result, "already shipped" result) with FE, iOS and Android before they start; post it as a comment on this task.
- Confirm with the owners of the refund process and seller notifications that both are reused unchanged (refund changes are out of scope).
- Cover the status matrix: New and Confirmed are allowed; Shipped, Delivered and Cancelled are rejected.

## Definition of Done

- [ ] AC-4: a prepaid Confirmed order cancelled with a reason ends in "Cancelled by buyer", the seller sees the reason and is notified, the "Refund initiated" state is set.
- [ ] AC-5: a cancellation for an order already Shipped is rejected with the "already shipped" result; the order status is unchanged.
- [ ] AC-2 (backend side): cancellation of Shipped, Delivered and Cancelled orders is rejected.
- [ ] FR-2: a cancellation without a reason is rejected.
- [ ] AC-6 (backend side): with `buyer_order_cancel` off, no cancellation is accepted.
- [ ] The contract is posted on this task and acknowledged by FE, iOS and Android.

## Requirements

[PROJ-1234.3 - Buyer order cancellation before shipment](https://confluence.example.com/wiki/spaces/SPACE/pages/100001)

<!-- template: task-builtin-default version: 1.0.0 -->
```

### 4.2 PROJ-1302 — [Analytics] Buyer order cancellation before shipment - Define cancellation event coverage and metrics

| Issue type | Parent | Labels | Components | Team | Reporter |
|------------|--------|--------|------------|------|----------|
| Task | PROJ-1234 | `Analytics`, `PROJ-1234.3` | `orders` | Team 1 | Person1 Surname1 |

```markdown
## Why

The primary metric (share of self-service cancellations) and the guardrail (overall cancellation rate, max +0.5 pp) can be read only if cancellation events are tracked on all three platforms from the first rollout step (10%).

## What

- Event spec for `order_cancel_click`, `order_cancel_confirm`, `order_cancel_rejected` with exactly the parameters listed on the requirements page.
- The spec handed to FE, iOS and Android before they start.
- Primary and guardrail metric definitions, with the baseline period "4 weeks before release".

## How

- Take event names and parameters only from the requirements' Analytics section; any new event goes back to the PM first.
- Parameters: order_id, reason, is_prepaid, platform for `order_cancel_confirm`; order_id, platform, rejection_reason for `order_cancel_rejected`.
- Take the possible `rejection_reason` values from the contract agreed in the BE task.
- Record the baseline for the guardrail before the flag reaches 10%.

## Definition of Done

- [ ] AC-7 (spec side): the spec for 3 events on web, iOS and Android is published and linked on this task.
- [ ] Primary and guardrail metric definitions are written; the 4-week baseline is captured.
- [ ] FE, iOS and Android have acknowledged the spec.

## Requirements

[PROJ-1234.3 - Buyer order cancellation before shipment](https://confluence.example.com/wiki/spaces/SPACE/pages/100001)

<!-- template: task-builtin-default version: 1.0.0 -->
```

### 4.3 PROJ-1303 — [FE] Buyer order cancellation before shipment - Build the cancel flow on web order details

| Issue type | Parent | Labels | Components | Team | Reporter |
|------------|--------|--------|------------|------|----------|
| Task | PROJ-1234 | `frontend`, `PROJ-1234.3` | `orders` | Team 1 | Person1 Surname1 |

```markdown
## Why

Web buyers get a self-service way to cancel an unshipped order instead of contacting support or the seller — the change the primary metric measures.

## What

- A "Cancel order" action on web order details (desktop and mobile web), shown for status New or Confirmed only (FR-1).
- A confirmation step with a required reason from the fixed list; "Other" with an optional comment up to 300 characters; Confirm disabled until a reason is chosen (FR-2).
- A success state: status "Cancelled by buyer"; for a prepaid order, "Refund initiated" on the order and in the confirmation message (FR-3, FR-4).
- An "already shipped" state: the exact FR-5 message, then a refresh to the current status.
- Events `order_cancel_click`, `order_cancel_confirm`, `order_cancel_rejected` per the Analytics spec.
- Nothing shown while the flag `buyer_order_cancel` is off (FR-6).

## How

- Build the screens from the approved mockups linked in the requirements.
- Use the cancellation contract agreed in the BE task and the event spec from the Analytics task.
- Cover the states: action shown / hidden by status, no reason chosen, success (prepaid and not prepaid), already shipped, flag off.

## Definition of Done

- [ ] AC-1 and AC-2 pass on desktop and mobile web.
- [ ] AC-3: Confirm is disabled until a reason is chosen.
- [ ] AC-4 (web side): the buyer sees "Cancelled by buyer" and, for a prepaid order, "Refund initiated".
- [ ] AC-5: the FR-5 message is shown and the screen shows the current status.
- [ ] AC-6: no action with the flag off.
- [ ] AC-7: all three events fire on web with every listed parameter.

## Requirements

[PROJ-1234.3 - Buyer order cancellation before shipment](https://confluence.example.com/wiki/spaces/SPACE/pages/100001)

<!-- template: task-builtin-default version: 1.0.0 -->
```

### 4.4 PROJ-1304 — [iOS] Buyer order cancellation before shipment - Build the cancel flow on the iOS order details screen

| Issue type | Parent | Labels | Components | Team | Reporter |
|------------|--------|--------|------------|------|----------|
| Task | PROJ-1234 | `iOS`, `app`, `PROJ-1234.3` | `orders` | Team 1 | Person1 Surname1 |

```markdown
## Why

iOS buyers get a self-service way to cancel an unshipped order instead of contacting support or the seller — the change the primary metric measures.

## What

- A "Cancel order" action on the native order details screen, shown for status New or Confirmed only (FR-1).
- A native confirmation step with a required reason from the fixed list; "Other" with an optional comment up to 300 characters; Confirm disabled until a reason is chosen (FR-2).
- A success state: status "Cancelled by buyer"; for a prepaid order, "Refund initiated" on the order and in the confirmation message (FR-3, FR-4).
- An "already shipped" state: the exact FR-5 message, then a refresh to the current status.
- Events `order_cancel_click`, `order_cancel_confirm`, `order_cancel_rejected` with platform = iOS.
- Nothing shown while the flag `buyer_order_cancel` is off (FR-6).
- No deeplink or push changes — the requirements have none.

## How

- Build the screen from the approved mockups linked in the requirements.
- Use the cancellation contract agreed in the BE task and the event spec from the Analytics task.
- Cover the states: action shown / hidden by status, no reason chosen, success (prepaid and not prepaid), already shipped, flag off.

## Definition of Done

- [ ] AC-1 and AC-2 pass on iOS.
- [ ] AC-3: Confirm is disabled until a reason is chosen.
- [ ] AC-4 (iOS side): the buyer sees "Cancelled by buyer" and, for a prepaid order, "Refund initiated".
- [ ] AC-5: the FR-5 message is shown and the screen shows the current status.
- [ ] AC-6: no action with the flag off.
- [ ] AC-7: all three events fire on iOS with every listed parameter.

## Requirements

[PROJ-1234.3 - Buyer order cancellation before shipment](https://confluence.example.com/wiki/spaces/SPACE/pages/100001)

<!-- template: task-builtin-default version: 1.0.0 -->
```

### 4.5 PROJ-1305 — [Android] Buyer order cancellation before shipment - Build the cancel flow on the Android order details screen

| Issue type | Parent | Labels | Components | Team | Reporter |
|------------|--------|--------|------------|------|----------|
| Task | PROJ-1234 | `Android`, `app`, `PROJ-1234.3` | `orders` | Team 1 | Person1 Surname1 |

```markdown
## Why

Android buyers get a self-service way to cancel an unshipped order instead of contacting support or the seller — the change the primary metric measures.

## What

- A "Cancel order" action on the native order details screen, shown for status New or Confirmed only (FR-1).
- A native confirmation step with a required reason from the fixed list; "Other" with an optional comment up to 300 characters; Confirm disabled until a reason is chosen (FR-2).
- A success state: status "Cancelled by buyer"; for a prepaid order, "Refund initiated" on the order and in the confirmation message (FR-3, FR-4).
- An "already shipped" state: the exact FR-5 message, then a refresh to the current status.
- Events `order_cancel_click`, `order_cancel_confirm`, `order_cancel_rejected` with platform = Android.
- Nothing shown while the flag `buyer_order_cancel` is off (FR-6).
- No deeplink or push changes — the requirements have none.

## How

- Build the screen from the approved mockups linked in the requirements.
- Use the cancellation contract agreed in the BE task and the event spec from the Analytics task.
- Cover the states: action shown / hidden by status, no reason chosen, success (prepaid and not prepaid), already shipped, flag off.

## Definition of Done

- [ ] AC-1 and AC-2 pass on Android.
- [ ] AC-3: Confirm is disabled until a reason is chosen.
- [ ] AC-4 (Android side): the buyer sees "Cancelled by buyer" and, for a prepaid order, "Refund initiated".
- [ ] AC-5: the FR-5 message is shown and the screen shows the current status.
- [ ] AC-6: no action with the flag off.
- [ ] AC-7: all three events fire on Android with every listed parameter.

## Requirements

[PROJ-1234.3 - Buyer order cancellation before shipment](https://confluence.example.com/wiki/spaces/SPACE/pages/100001)

<!-- template: task-builtin-default version: 1.0.0 -->
```

### 4.6 PROJ-1306 — [QA] Buyer order cancellation before shipment - Verify the cancel flow on web, iOS and Android

| Issue type | Parent | Labels | Components | Team | Reporter |
|------------|--------|--------|------------|------|----------|
| Task | PROJ-1234 | `qa`, `PROJ-1234.3` | `orders` | Team 1 | Person1 Surname1 |

```markdown
## Why

The change touches order status and refunds on three platforms. One pass against every acceptance criterion before the flag reaches 10% keeps a wrong cancellation or a missed refund away from real buyers.

## What

- A test run of AC-1 to AC-7 on desktop web, mobile web, iOS and Android.
- Orders in every status (New, Confirmed, Shipped, Delivered, Cancelled), prepaid and not prepaid.
- The event check (AC-7) against the Analytics spec.

## How

- Write one test case per acceptance criterion and platform, straight from the AC table.
- Prepare test orders in each status, prepaid and not prepaid.
- Reproduce FR-5: open order details, move the order to Shipped, then confirm.
- File each defect as a bug linked to the platform task it belongs to.
- Leave out-of-scope flows untested: returns after shipment, partial cancellation.

## Definition of Done

- [ ] AC-1 to AC-7 pass on desktop web, mobile web, iOS and Android; results attached to this task.
- [ ] No open defect blocks any acceptance criterion.
- [ ] A sign-off comment is posted before the flag goes to 10%.

## Requirements

[PROJ-1234.3 - Buyer order cancellation before shipment](https://confluence.example.com/wiki/spaces/SPACE/pages/100001)

<!-- template: task-builtin-default version: 1.0.0 -->
```

## 5. Links (Steps 9–10) — linking confirmed by the user

| # | Link | Rule |
|---|------|------|
| 1–3 | PROJ-1301 [BE] **blocks** PROJ-1303 [FE], PROJ-1304 [iOS], PROJ-1305 [Android] | Standard chain |
| 4–6 | PROJ-1302 [Analytics] **blocks** PROJ-1303 [FE], PROJ-1304 [iOS], PROJ-1305 [Android] | Standard chain |
| 7–9 | PROJ-1303 [FE], PROJ-1304 [iOS], PROJ-1305 [Android] **block** PROJ-1306 [QA] | From the brief — QA sits outside the standard chain |

Design links skipped (no Design task); no "Test results analysis" task (not an A/B test).

```
[BE] PROJ-1301 ---------+--> [FE] PROJ-1303 -------+
                        |                          |
[Analytics] PROJ-1302 --+--> [iOS] PROJ-1304 ------+--> [QA] PROJ-1306
                        |                          |
                        +--> [Android] PROJ-1305 --+
```

## 6. Report (Step 11)

| # | Key | Title | Issue Type | Labels | Components |
|---|-----|-------|------------|--------|------------|
| 1 | PROJ-1301 | [BE] Buyer order cancellation before shipment - Support buyer cancellation with reason, seller notice and refund start | Task | `backend`, `PROJ-1234.3` | `orders` |
| 2 | PROJ-1302 | [Analytics] Buyer order cancellation before shipment - Define cancellation event coverage and metrics | Task | `Analytics`, `PROJ-1234.3` | `orders` |
| 3 | PROJ-1303 | [FE] Buyer order cancellation before shipment - Build the cancel flow on web order details | Task | `frontend`, `PROJ-1234.3` | `orders` |
| 4 | PROJ-1304 | [iOS] Buyer order cancellation before shipment - Build the cancel flow on the iOS order details screen | Task | `iOS`, `app`, `PROJ-1234.3` | `orders` |
| 5 | PROJ-1305 | [Android] Buyer order cancellation before shipment - Build the cancel flow on the Android order details screen | Task | `Android`, `app`, `PROJ-1234.3` | `orders` |
| 6 | PROJ-1306 | [QA] Buyer order cancellation before shipment - Verify the cancel flow on web, iOS and Android | Task | `qa`, `PROJ-1234.3` | `orders` |

- **Common fields:** Parent PROJ-1234 · Team 1 · Reporter Person1 Surname1.
- **Links:** 9 "Blocks" links (section 5).
- **Issues encountered:** the Team field was not accepted on create; set with `editJiraIssue` on all six tasks (Step 8).
- **All tasks:** [`parent=PROJ-1234 AND labels=PROJ-1234.3 ORDER BY created DESC`](https://jira.example.com/issues/?jql=parent%3DPROJ-1234%20AND%20labels%3DPROJ-1234.3%20ORDER%20BY%20created%20DESC)

Altitude: L1 · ↑ serves: Epic PROJ-1234 "Buyer self-service for orders" — share of buyer cancellations done in self-service · ↓ next: estimate PROJ-1301…PROJ-1306 at grooming (story points left unset)

## 7. Post-creation verification (Step 12)

PROJ-1303 [FE] read back with `getJiraIssue` and checked by an independent checker agent against the requirements page.

| Check | Expected | Actual | Result |
|-------|----------|--------|--------|
| Title format | `[FE] FeatureName - …` — no Grooming / A/B Test parts | As expected | Pass |
| Parent | PROJ-1234 | PROJ-1234 | Pass |
| Reporter | Person1 Surname1 | Person1 Surname1 | Pass |
| Team | Team 1 | Team 1 | Pass |
| Labels | `frontend`, `PROJ-1234.3` | `frontend`, `PROJ-1234.3` | Pass |
| Components | `orders` | `orders` | Pass |
| Description | Why, What, How, Definition of Done, Requirements (with page link) | All five present | Pass |
| Issue type | Task | Task | Pass |
| Links | Blocked by PROJ-1301, PROJ-1302; blocks PROJ-1306 | As expected | Pass |
| List formatting | What / How / DoD as lists | Lists | Pass |
| No ungrounded tech content | Nothing beyond the requirements; no "AI technical recommendations" section requested | None found | Pass |

Result: all checks pass — no cross-task fixes needed.

> Was everything created correctly? Is there anything to fix, add, or change?

## Why this is the gold bar (rubric map)

| Criterion | Where it is met |
|-----------|-----------------|
| tasks_per_discipline | One task per selected discipline — BE, Analytics, FE, iOS, Android, QA; each "What" is specific to its work type |
| derived_from_requirements | Every bullet cites its FR / AC; the coverage table maps all of them; "How" holds process steps only, nothing invented |
| acceptance_in_task | Each task carries a Definition of Done built from the AC that apply to its discipline |
| correct_epic_link | Parent PROJ-1234 on all six tasks, confirmed before creation and on read-back |
| estimates_or_labels | Work-type label + feature code on every task; story points deliberately left for grooming and said so |
