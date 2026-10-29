# Reference walk — order to review across three roles (marketplace, test accounts)

Three legs on production test accounts of the user's own product ("Product 1"): the test buyer orders from a test shop, the test seller confirms and ships, the buyer reviews. Boundary per leg: `sandbox-confirm` (both accounts have `sandbox: yes`). The user logs in before each leg and enters any one-time code themselves.

## Legs

| Leg | Role | Account | Surface | Goal | handoff_in | handoff_out |
|-----|------|---------|---------|------|------------|-------------|
| 1 | buyer | test-buyer-1 | iphone-on-mac | place an order in the test shop | — | order_id, shop |
| 2 | seller | test-seller-shop-a | web | confirm and ship the order | order_id | tracking |
| 3 | buyer | test-buyer-1 | iphone-on-mac | leave a review for the delivered item | order_id | review_visible |

## Expected steps

| Leg-# | Intent | Action | Observed | Confirmation |
|-------|--------|--------|----------|--------------|
| L1-1 | Find a product of the test shop | search the shop name or open the shop page | product list of the test shop | — |
| L1-2 | Open a product | tap a card | product page, price, "Buy" | — |
| L1-3 | Add to cart / buy | tap "Buy" | cart or checkout | — |
| L1-4 | Fill delivery and payment | choose a test delivery option and a test payment method or cash on delivery | order summary | — |
| L1-5 | Place the order | tap "Confirm order" | order confirmation screen with an order number | **ask: "L1 / buyer: place order in Test Shop A — proceed?"** |
| L1-6 | Capture hand-off | read the order number | `order_id` written to run.yaml | — |
| L2-1 | Open the seller cabinet | log in as the seller (user), open Orders | orders list | — |
| L2-2 | Find the order | search `order_id` | order card, status "new" | — |
| L2-3 | Confirm the order | tap "Confirm" | status "confirmed" | **ask: "L2 / seller: confirm order <order_id> — proceed?"** |
| L2-4 | Ship the order | add a tracking number, tap "Ship" | status "shipped", tracking visible | **ask: "L2 / seller: mark order <order_id> shipped — proceed?"** |
| L2-5 | Capture hand-off | read the tracking number | `tracking` written to run.yaml | — |
| L3-1 | Open the order as the buyer | Account → Orders → `order_id` | order card, status shipped/received | — |
| L3-2 | Open the review form | "Leave a review" from the order card or the reviews hub | review form | — |
| L3-3 | Fill the review | rating, title, text | text visible | — |
| L3-4 | Publish | tap "Publish" | review visible on the order / product | **ask: "L3 / buyer: publish review for order <order_id> — proceed?"** |

Four confirmations in total. If checkout offers only a real payment method, L1-5 ends with `blocked_reason: real money` and the scenario is reported as partially walkable.

## Expected frictions to watch

- where the rating sits in the review form (before or after the text) and whether it is asked only on exit
- whether a draft survives closing the form
- whether the order status wording is the same for the buyer and the seller
- how many taps from the order card to the review form
- whether the seller sees the buyer's review and can respond

## Pack skeleton

```yaml
# run.yaml (excerpt)
scenario: "Order to review across buyer and seller on test accounts"
account: test
write_boundary: sandbox-confirm
legs:
  - {n: 1, role: buyer, account: test-buyer-1, surface: iphone-on-mac, goal: "place an order in the test shop", write_boundary: sandbox-confirm, verdict: completed, handoff: {order_id: "…", shop: "Test Shop A"}}
  - {n: 2, role: seller, account: test-seller-shop-a, surface: web, goal: "confirm and ship the order", write_boundary: sandbox-confirm, verdict: completed, handoff: {tracking: "…"}}
  - {n: 3, role: buyer, account: test-buyer-1, surface: iphone-on-mac, goal: "leave a review", write_boundary: sandbox-confirm, verdict: completed, handoff: {review_visible: true}}
verdict: completed
```
