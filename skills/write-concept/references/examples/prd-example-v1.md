<!-- Golden exemplar for the write-concept skill.
     Purpose: a worked, high-quality PRD instance the skill can pattern-match against (few-shot Examples context type).
     Generic/anonymized — NO org-specific data. Also used as a fixture for testing/output-evals.md (write-concept rubric).
     This is an illustration of quality and shape, not a rigid template — the real structure comes from prd-structure.md + the chosen template. -->

# [PRD] Saved-for-later cart on a marketplace

## Summary (TL;DR)
Buyers who aren't ready to purchase have no lightweight way to keep items in view, so they lose the item and the session. This concept adds a "Save for later" action on the product card and a dedicated saved list, letting buyers park items without committing to a cart. Target outcome: **+3–5% return-to-purchase rate** among savers within 30 days, with no regression to add-to-cart rate.

## Problem Statement
Analytics show a large share of product-page sessions end without an add-to-cart, yet a meaningful fraction of those buyers return within two weeks searching for the same item. The current cart conflates "intent to buy now" with "interested later," so hesitant buyers either overload the cart (inflating abandonment) or leave with nothing saved. This raises re-discovery cost and depresses repeat visits. *(Assumption — to validate in discovery: the "return searching for same item" pattern is material; confirm against session data before build.)*

## Goals & Non-Goals
**Goals**
- Give buyers a one-tap way to save an item without adding to cart.
- Increase return-to-purchase among hesitant buyers.
- Keep the saved list accessible across sessions and devices (for logged-in users).

**Non-Goals**
- Not a wishlist-sharing or social feature (future phase).
- Not price-drop notifications (dependent, separate concept).
- No changes to the checkout flow.

## User Stories
- As a logged-in buyer, I can tap "Save for later" on a product card so the item is kept without entering my cart.
- As a returning buyer, I can open my saved list and move an item to the cart in one action.
- As a guest, I'm prompted to log in to persist saves across sessions.

## Proposed Solution
A "Save for later" control on the product card and product page, plus a "Saved" list reachable from the main navigation and account menu. Saving is instant and reversible; moving to cart is one tap. For guests, saves persist for the session and are offered a login upsell to keep them.

## What Changes for Users
| Segment | What changes | What they gain |
|---------|-------------|----------------|
| Logged-in buyers | New save control + persistent saved list | Re-find items instantly across sessions |
| Guests | Session-only saves + login prompt | Frictionless save now, persistence on login |
| Sellers | Aggregate "saves" signal on their items | Weak-intent demand signal (read-only, phase 2) |

## Scope & Phasing
- **Phase 1 (MVP):** save/unsave on product card + page; saved list; move-to-cart. Logged-in only persistence.
- **Phase 2:** guest→login save migration; seller-side saves signal.

## Success Metrics
- **Primary:** return-to-purchase rate among users with ≥1 save, 30-day window. **Target +3–5%** vs. matched non-saver baseline.
- **Guardrail:** add-to-cart rate and checkout conversion must not drop (≤0.5% relative).
- **Secondary:** save adoption (% of product-page sessions with ≥1 save); saved-list → cart move rate.

## Risks & Mitigations
| Risk | Mitigation |
|------|-----------|
| Saves cannibalize add-to-cart (buyers save instead of buy) | Guardrail metric + A/B; kill if checkout CR regresses |
| Low discoverability of the saved list | Nav entry + first-save tooltip; measure adoption |
| Guest saves lost → frustration | Clear session-only labeling + login upsell (phase 2 persistence) |

## Verification / How we'll know it worked
- Ship behind an A/B test; **decision rule:** promote only if primary metric hits target AND no guardrail regression at significance.
- Instrument save, unsave, saved-list-open, move-to-cart events before launch.

## Open Questions
- Does the "return for same item" pattern hold in session data? (blocks build-vs-defer)
- Should saved items show live price/availability, or a snapshot?

## Sources
- Product Analysis: product-page exit & return-session figures *(period-annotated)*
- Web: marketplace wishlist/save-for-later UX benchmarks
