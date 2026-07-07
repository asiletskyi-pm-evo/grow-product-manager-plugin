<!-- Golden exemplar for the requirements-creator skill.
     Purpose: a worked, high-quality feature-spec (with an A/B variant) the skill can pattern-match against (few-shot Examples context type).
     Generic/anonymized — NO org-specific data. Also used as a fixture for testing/output-evals.md (requirements-creator rubric).
     Illustrates rigor and shape, not a rigid template — real structure comes from requirements-template.md + the chosen template.
     Continues the "Save for later" example from write-concept/references/examples/prd-example-v1.md to show concept → requirements flow. -->

# Feature Requirements: Save-for-later (Phase 1 MVP) — A/B test

## Epic
Link to the parent Epic (buyer retention / product-page engagement). *(In a real spec: clickable Confluence link.)*

## Hypotheses
| № | Hypothesis |
|---|------------|
| 1 | IF hesitant buyers can save an item without adding it to cart, THEN return-to-purchase among savers rises, WITHOUT reducing checkout conversion. |

## Approach
A/B test (feature flag on 50/50 split). Rationale: revenue-adjacent change with a real cannibalization risk → must be measured against a control, not shipped blind. See `references/approach-recommendation.md`.

## Test Groups
| Group | Description |
|-------|-------------|
| Control (A) | Current product card and cart — no save control. |
| Test (B) | "Save for later" control on product card + page, "Saved" list, one-tap move-to-cart. |

## Traffic Split
50% A / 50% B, logged-in buyers only (Phase 1 scope). Guests excluded from analysis.

## Functional Requirements
1. A "Save for later" control appears on the product card and product page for logged-in buyers (Group B).
2. Saving an item adds it to a persistent "Saved" list without adding it to the cart.
3. The control toggles: a saved item shows a "Saved" state and can be un-saved from the same control.
4. The "Saved" list is reachable from main navigation and the account menu; it lists saved items with image, title, price, and a one-tap "Move to cart".
5. "Move to cart" adds the item to the cart and removes it from the saved list.
6. Saved state persists across sessions and devices for the logged-in user.

## Non-Functional Requirements
- Save / un-save actions respond in < 300 ms (optimistic UI acceptable).
- Saved list loads in < 1 s for up to 200 items.
- No PII beyond existing account scope.

## Acceptance Criteria
| # | Given / When / Then |
|---|---------------------|
| AC-1 | GIVEN a logged-in buyer in Group B on a product page, WHEN they tap "Save for later", THEN the item appears in "Saved" and the cart count is unchanged. |
| AC-2 | GIVEN an item in "Saved", WHEN the buyer taps "Move to cart", THEN the item is in the cart AND removed from "Saved". |
| AC-3 | GIVEN a buyer saved an item on device 1, WHEN they log in on device 2, THEN the saved item is present. |
| AC-4 | GIVEN a buyer in Group A (control), WHEN they view any product page, THEN no save control is shown. |

## Success Metrics & Decision Rule
- **Primary:** return-to-purchase rate among users with ≥1 save (30-day window) vs. control. **Ship target: +3–5%**, statistically significant.
- **Guardrail:** checkout conversion and add-to-cart rate must not regress > 0.5% relative.
- **Decision rule:** promote B to 100% **only if** primary hits target AND no guardrail regression at significance; otherwise iterate or kill.

## Analytics / Events (required before launch)
`save_click`, `unsave_click`, `saved_list_open`, `move_to_cart_from_saved`, plus experiment group assignment on all product-page and checkout events.

## Out of Scope (Phase 1)
Guest persistence, price-drop alerts, seller-side saves signal, wishlist sharing.

## Open Questions
- Snapshot vs. live price/availability on the saved list?
- Cap on saved-list size?

## Sources
- Concept PRD (write-concept exemplar) · Product Analysis (period-annotated exit/return figures)
