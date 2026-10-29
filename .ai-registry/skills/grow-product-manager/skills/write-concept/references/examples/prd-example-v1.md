<!-- Golden exemplar for the write-concept skill.
     Purpose: a worked, high-quality PRD instance the skill can pattern-match against (few-shot Examples context type).
     Generic/anonymized — NO org-specific data. Also used as a fixture for testing/output-evals.md (write-concept rubric).
     This is an illustration of quality and shape, not a rigid template — the real structure comes from prd-structure.md + the chosen template.
     Pre-mortem (since v3.9.0, P4): inserted right after Risks by template-protocol T-5 step 3b, derived, never asked. Causes and kill rows carry no
     evidence class — the assumed premise keeps its label; the one threshold the PRD does not state is ⚠️ TBD, counted, not asked. -->

# [PRD] Saved-for-later cart on a marketplace

## Summary (TL;DR)
Buyers who aren't ready to purchase have no lightweight way to keep items in view, so they lose the item and the session. This concept adds a "Save for later" action on the product card and a dedicated saved list, letting buyers park items without committing to a cart. Target outcome: **+3–5% return-to-purchase rate** among savers within 30 days, with no regression to add-to-cart rate.

## Problem Statement
Analytics show a large share of product-page sessions end without an add-to-cart, yet a meaningful fraction of those buyers return within two weeks [assumed — Product Analysis to confirm product-page exits and return sessions] searching for the same item [assumed — to validate in discovery: the "return searching for same item" pattern is material; confirm against session data before build]. The current cart conflates "intent to buy now" with "interested later," so hesitant buyers either overload the cart (inflating abandonment) or leave with nothing saved [assumed — from the PM brief; no session data yet]. This raises re-discovery cost and depresses repeat visits.

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

## Pre-mortem

It is 30 days after launch and this did not work. Most likely why:

| Why it failed | Early signal | What we do now |
|---------------|--------------|----------------|
| Hesitant buyers do not come back for the same item — the Problem Statement's premise [assumed — to validate in discovery] never held | Savers' return sessions stay at the non-saver level in the first two weeks | Check the premise in session data before build (Open Questions) |
| Saves replace add-to-cart instead of adding to it (Risks: cannibalization) | Add-to-cart rate in the test arm drifts toward the 0.5% guardrail in week 1 | Read the guardrail daily; roll back at the limit |
| Buyers never find the saved list, so saves never turn into purchases (Risks: discoverability) | Save adoption rises while saved-list opens per saver stay near zero | Ship the nav entry and first-save tooltip with the MVP, not later |

### Kill criteria

| Signal | Threshold | Date | Then |
|--------|-----------|------|------|
| Checkout conversion, test vs control | drop beyond 0.5% relative (guardrail) | launch + 30 days, read daily | Roll back |
| Return-to-purchase rate among savers vs matched non-savers | below +3% (the target's lower bound) | launch + 30 days | Stop — do not promote |
| Save adoption (% of product-page sessions with ≥1 save) | ⚠️ TBD — the PRD sets no adoption target | launch + 30 days | Pivot to discoverability before more build |

- **Open (⚠️ TBD):** 1 — set them at review or before the first checkpoint.

## Verification / How we'll know it worked
- Ship behind an A/B test; **decision rule:** promote only if primary metric hits target AND no guardrail regression at significance.
- Instrument save, unsave, saved-list-open, move-to-cart events before launch.

## Open Questions
- Does the "return for same item" pattern hold in session data? (blocks build-vs-defer)
- Should saved items show live price/availability, or a snapshot?

## Sources
- Product Analysis: product-page exit & return-session figures — to be run; no figures yet, so the body marks them `[assumed — …]`
- Web: marketplace wishlist/save-for-later UX benchmarks *(external)*

Altitude: L2 · ↑ serves: — (no linked goal) · ↓ next: check the "return for same item" pattern in session data — it blocks build-vs-defer
