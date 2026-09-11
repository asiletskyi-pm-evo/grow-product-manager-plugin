# Test accounts by role and multi-role walkthrough legs — design spec (v3.2.0)

**Date:** 2026-09-11 · **Status:** approved in chat, pending implementation plan · **Target release:** v3.2.0 · Ukrainian mirror: `2026-09-11-test-accounts-and-legs-design.uk.md` · Builds on `2026-09-10-flow-walkthrough-design.md` (v3.1.0).

## 1. Problem and goal

A v3.1.0 walk is one role, one account, and it stops before every irreversible production action. Two things a PM actually needs are missing: (a) **riskier actions on production, safely** — most products have test accounts on production (a test buyer, test seller companies, an admin) where placing an order or publishing a review harms nobody; (b) **journeys that span roles** — a buyer orders, a seller confirms and ships, the buyer reviews. The goal: let the user declare test accounts per role once, let a walkthrough scenario consist of several **legs** played by different roles in sequence with hand-off data between them, and let the write boundary follow the account type instead of being one global rule.

Reference case (Prom): test buyer (an account from the team's test-accounts page) orders from a test company → the seller confirms and ships in the seller cabinet → the buyer leaves a review. This is the only way to walk the review flow end to end, because a review requires a purchase.

## 2. Decisions taken (with the user)

| # | Decision | Choice |
|---|---|---|
| D1 | Where test accounts live | `local-context.md`, product section `#### Test Accounts` — label, role, surfaces, where to obtain access, sandbox flag. **Never credentials or one-time codes.** |
| D2 | Scenario shape | a list of **legs** `[{role, account, surface, goal}]`, run in order, each leg a normal walk; hand-off values (order id, product, tracking number) are captured from screenshots and passed to the next leg |
| D3 | Write boundary by account type | `own` → `stop-before-irreversible` (as v3.1.0); `test` in the user's own product → `sandbox-confirm` (irreversible actions inside the test contour are allowed, **each one confirmed by the user before the tap**; real money and actions that reach real users always stop); competitor → `read-only`, no exceptions |
| D4 | Who logs in | the user, before each leg; the skill says which role and which account label; on a shared surface the previous role is logged out first |
| D5 | Setup | plugin-configurator gets an Extended add-on **Test accounts setup** and the standalone commands `add Test accounts` / `додай тестові акаунти`; Basic mode defers it |
| D6 | Report | step table gains a `Leg / Role` column; a leg summary table (leg, role, account label, steps, verdict) precedes it; the comparison matrix is unchanged |
| D7 | Sandbox confirmation style | one AskUserQuestion-free yes/no line per irreversible action: "Leg 2 / seller: confirm order #… — proceed?" — the run pauses until the user answers; the user may say "confirm all in this leg" to switch the leg to `sandbox-auto` |

Out of v3.2.0: parallel legs on two devices at once (legs are sequential; two surfaces may stay open), automatic account switching, storing any secret.

## 3. Components

### 3.1 `local-context.md` — Test Accounts section (schema)

Under each product, after `#### Locales` / `#### Primary Market`:

```markdown
#### Test Accounts
<!-- labels and roles only — never passwords, tokens or one-time codes -->
| Label | Role | Surfaces | Access | Sandbox |
|-------|------|----------|--------|---------|
| test-buyer-1 | buyer | web, iphone-on-mac | team page "Test accounts" (link) — phone login, code by e-mail | yes |
| test-seller-shop-a | seller | web | same page — company "Shop A" | yes |
| admin-staging | admin | web | internal admin URL, SSO | no |
```

Schema (`skills/plugin-configurator/references/context-schema.md`): `test_accounts[]` with `label` (unique per product), `role` (free text, suggested `buyer | seller | admin | support | courier`), `surfaces[]` (from `web | desktop | iphone-on-mac | android-adb`), `access` (where/how the user obtains access — a link or a sentence), `sandbox` (`yes` = the account's actions stay inside a test contour and may be irreversible; `no` = treat like `own`). Lint check 9/18 stays green: examples use placeholder labels and `example.com`.

### 3.2 plugin-configurator — Test accounts setup (Extended add-on)

`references/onboarding-steps.md`: new add-on after People setup. Flow: "Does this product have test accounts on production? (roles: buyer / seller / admin …)" → for each: label, role, surfaces, access description, sandbox yes/no → write the section → remind: "the plugin never stores passwords; you log in yourself before each leg". Deferred step id `test-accounts`. SKILL.md: standalone triggers `add Test accounts`, `set up test accounts`, `додай тестові акаунти`, `налаштуй тестові акаунти`. Version bump patch.

### 3.3 flow-walkthrough — legs

**Step 1 (scope)** — a scenario is one leg by default; the user's phrasing ("…as buyer, then as seller…") or a request naming two roles makes it multi-leg. For each leg: `role`, `account` (a Test Accounts label, or `own` / `anonymous`), `surface`, `goal` (one sentence), `handoff_in` (what this leg needs from the previous one) and `handoff_out` (what it must capture). The write boundary is resolved **per leg** from the account (D3) and restated: "Leg 1 buyer (test-buyer-1, sandbox-confirm): I will place a real order in the test shop and ask before paying/confirming".

**Step 2 (preflight)** — per leg: the account exists for the role (else offer Test accounts setup or `own`); the surface is ready; the user is asked to log in as that account and says "done"; on a surface shared between legs, the previous role is logged out first. `steps/00.png` per leg → `steps/L1-00.png`.

**Step 3 (walk loop)** — unchanged cycle; screenshot names `steps/L<leg>-<NN>.png`; every `steps.yaml` row carries `leg` and `role`. At each irreversible action under `sandbox-confirm` the skill stops, states the action in one line and waits for "yes"; a "no" logs the step as `blocked_reason: user declined` and ends the leg. Hand-off: after the last step of a leg the skill reads the `handoff_out` values from the screenshot (e.g. the order number), writes them to `run.yaml → legs[i].handoff`, and echoes them; the next leg starts only when every `handoff_in` value is present (else pause and ask).

**Step 6 (report)** — leg summary table + `Leg / Role` column. **Compare mode** — unchanged; a multi-leg scenario compared across surfaces aligns legs first, then step intents.

### 3.4 app-drive-protocol.md

§3 Preflight item 5 → "Account state per leg"; item 6 → the write-boundary policy table (D3) with the three values `stop-before-irreversible | sandbox-confirm | sandbox-auto | read-only`; §5 Safety adds: "sandbox never lifts the two hard stops — real money, and actions visible to real users (a message to a real seller, a public review on a real listing)". §7 pack layout: `run.yaml` gains `legs: [{n, role, account, surface, goal, write_boundary, started, finished, verdict, handoff: {…}}]` and `verdict` becomes the worst leg verdict; `steps.yaml` rows gain `leg`, `role`; screenshots `steps/L<leg>-<NN>.png`.

### 3.5 Template, fixture, docs

- `templates/built-in/research/walkthrough-v1.md` → v1.1.0: leg summary table, `Leg / Role` column; `min_plugin_version` stays 3.1.0 (the columns are optional).
- `skills/flow-walkthrough/examples/marketplace-order-to-review-flow.md`: the 3-leg reference scenario (buyer test account orders from a test shop → seller confirms and ships → buyer reviews), expected hand-offs (order id, tracking), expected confirmations, expected frictions to look for.
- README (flow-walkthrough section + "New in v3.2.0"), CHANGELOG, `.claude-plugin/plugin.json` ×3 (v3.2.0), Setup Guide and PM instruction in Confluence (Test accounts step; per-leg login; sandbox-confirm behaviour), the flow-walkthrough Confluence article ("Нове у v3.2.0").
- `testing/trigger-evals.md` Group N (multi-role phrasing routes to flow-walkthrough; "додай тестові акаунти" routes to plugin-configurator); `testing/test-cases.md` TC-flow-walkthrough-scenario-3 (3-leg run) and TC-plugin-configurator-test-accounts-1.

## 4. Testing

- Lint GREEN; validate-consistency green at v3.2.0; host-smoke on both hosts.
- Fixture dry run: `audit` on the 3-leg example produces a leg table and per-leg verdicts.
- Acceptance on Prom (manual, Claude Cowork, sandbox-confirm): buyer leg on iphone-on-mac with the test buyer, seller leg on web with a test company, buyer review leg; every irreversible action confirmed in chat; `run.yaml` has three legs with hand-off `order_id`; nothing touches a real seller or real money. The user logs in for each leg and enters any one-time code themselves.

## 5. Risks

Order flow on production may involve payment: the test contour must offer cash-on-delivery or a test payment method — if only real payment exists, the leg stops there (`blocked_reason: real money`) and the scenario is reported as partially walkable. Seller-side surfaces may be web-only; that is fine (legs may change surface).
