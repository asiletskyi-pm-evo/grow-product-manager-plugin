# Test accounts by role + multi-role legs (v3.2.0) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a walkthrough scenario run as several legs played by different roles on declared test accounts, with a write boundary that follows the account type (sandbox-confirm on test accounts, stop-before-irreversible on own, read-only on competitors).

**Architecture:** A `#### Test Accounts` table per product in `local-context.md` (labels/roles only, never secrets) written by a new configurator add-on; `flow-walkthrough` Step 1–3 and 6 become leg-aware; `app-drive-protocol.md` gets the boundary policy table and the `legs` pack layout; the report template gets a leg table; a 3-leg reference fixture.

**Tech Stack:** Markdown skills/references, YAML examples, existing Python linters, git.

**Spec:** `docs/superpowers/specs/2026-09-11-test-accounts-and-legs-design.md` (UK mirror `.uk.md`)

## Global Constraints

- Plugin version **3.1.0 → 3.2.0** (MINOR: new step in flow-walkthrough, new configurator add-on) in the six bump places (`.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.codex-plugin/plugin.json`, README header + footer, CHANGELOG top entry). Manifest tails must say `v3.2.0`; skill count stays 30.
- Skill bumps: `flow-walkthrough` 0.1.0 → 0.2.0 (inline `skill_version` too), `plugin-configurator` 2.9.3 → 2.9.4; README skill version lines follow.
- No Cyrillic inside fenced code blocks under `references/`, `skills/`, `templates/`; placeholders only (`example.com`, `Product 1`, `PROJ-1234`); no real org identifiers; **never** a password, token or one-time code in any example.
- Write-boundary vocabulary (exact strings everywhere): `stop-before-irreversible`, `sandbox-confirm`, `sandbox-auto`, `read-only`.
- Deferred step id: `test-accounts`.
- Commits end with `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`; `python3 testing/skill_lint.py` must print `RESULT: GREEN` after every task; `bash testing/validate-consistency.sh` green by Task 5.

---

### Task 1: Test Accounts in the config schema + configurator add-on

**Files:**
- Modify: `skills/plugin-configurator/references/context-schema.md` (after the `#### Competitors (per product)` table; `deferred_steps` enum table)
- Modify: `skills/plugin-configurator/references/onboarding-steps.md` (append after the People setup add-on, end of file)
- Modify: `skills/plugin-configurator/SKILL.md` (Onboarding bullet: standalone triggers; `version:` 2.9.3 → 2.9.4)
- Modify: `local-context.example.md` (after `#### Primary Market` block of the first product)
- Modify: `README.md` (`Plugin Configurator (v2.9.3)` → `(v2.9.4)`)

**Interfaces:**
- Produces: section name `#### Test Accounts`, fields `label | role | surfaces | access | sandbox`, deferred id `test-accounts`, triggers `add Test accounts`, `set up test accounts`, `додай тестові акаунти`, `налаштуй тестові акаунти`.

- [ ] **Step 1: Schema** — after the Competitors table insert:

```markdown
#### Test Accounts (per product, since v3.2.0)

Labels and roles only — the plugin never stores passwords, tokens or one-time codes; the user logs in themselves before each walkthrough leg.

| Field | Required | Used by | Description |
|-------|----------|---------|-------------|
| test_accounts[].label | yes | flow-walkthrough | Unique per product, e.g. `test-buyer-1` |
| test_accounts[].role | yes | flow-walkthrough | Free text; suggested `buyer`, `seller`, `admin`, `support`, `courier` |
| test_accounts[].surfaces | yes | flow-walkthrough | Subset of `web`, `desktop`, `iphone-on-mac`, `android-adb` |
| test_accounts[].access | yes | flow-walkthrough | Where/how the user obtains access — a link to the team's test-accounts page or one sentence; never the secret itself |
| test_accounts[].sandbox | yes | flow-walkthrough | `yes` = the account's actions stay inside a test contour (irreversible actions allowed under `sandbox-confirm`); `no` = treated like the user's own account (`stop-before-irreversible`) |

Section format in `local-context.md`:

```markdown
#### Test Accounts
| Label | Role | Surfaces | Access | Sandbox |
|-------|------|----------|--------|---------|
| test-buyer-1 | buyer | web, iphone-on-mac | team page "Test accounts" (link) — phone login, code by e-mail | yes |
| test-seller-shop-a | seller | web | same page — company "Shop A" | yes |
```
```

In the `deferred_steps` enum table add the row `| \`test-accounts\` | Test accounts setup | Test accounts per product (labels, roles, surfaces, access, sandbox) |` after the `attachments-rest` row.

- [ ] **Step 2: Onboarding add-on** — append to `onboarding-steps.md`:

```markdown

## Step — Test accounts setup (Extended, since v3.2.0)

Configures the per-product **Test Accounts** table used by `flow-walkthrough` for multi-role legs and sandbox walks (format — `references/context-schema.md` → Test Accounts). Mode-gate: Extended; in Basic — add `test-accounts` to `onboarding.deferred_steps`. Standalone triggers: "add Test accounts", "set up test accounts", "додай тестові акаунти", "налаштуй тестові акаунти".

> **Never a secret.** Collect labels, roles, surfaces and *where* access is obtained. If the user pastes a password or a one-time code, do not write it anywhere; say so and continue.

Collected via `AskUserQuestion`/dialog, per product:

1. **Does this product have test accounts on production?** (roles: buyer / seller / admin / support / courier …) — "no" → mark the step done, nothing written.
2. **For each account** — label (unique), role, surfaces it can be used on, access description (a link to the team's test-accounts page is ideal), sandbox `yes|no` (is every action of this account confined to a test contour — test shop ↔ test buyer?).
3. **Write** the `#### Test Accounts` table under the product; **existence check**: a table already there → offer review/update, never duplicate labels.
4. **Say** the rule out loud once: "before each leg you log in as the named account yourself; under `sandbox-confirm` I ask before every irreversible action; real money and actions reaching real users always stop".
```

- [ ] **Step 3: SKILL.md + example + README** — in the Onboarding bullet append: `New in v3.2.0: \`add Test accounts\` / \`set up test accounts\` / \`додай тестові акаунти\` / \`налаштуй тестові акаунти\` → **Test accounts setup** (per-product labels, roles, surfaces, access, sandbox — never secrets).` Bump `version: 2.9.4`. In `local-context.example.md` after the Primary Market block add the `#### Test Accounts` table with placeholder rows (`test-buyer-1`, `test-seller-shop-a`, access `https://example.com/wiki/test-accounts`). README: `Plugin Configurator (v2.9.4)`.

- [ ] **Step 4: Lint + commit**

Run: `python3 testing/skill_lint.py` → GREEN.
```bash
git add skills/plugin-configurator local-context.example.md README.md
git commit -m "feat(configurator): Test accounts setup — per-product labels/roles/surfaces/access/sandbox, never secrets (v2.9.4)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 2: app-drive-protocol — boundary policy, hard stops, legs in the pack

**Files:**
- Modify: `references/app-drive-protocol.md` (§3 items 5–6, §5 first two bullets, §7 run.yaml + steps.yaml examples + naming)

**Interfaces:**
- Produces: `write_boundary` enum, `legs[]` schema in `run.yaml`, `leg`/`role` fields in `steps.yaml`, screenshot naming `steps/L<leg>-<NN>.png`.

- [ ] **Step 1: §3 items 5–6** — replace item 5 with: `5. Account state **per leg**: \`own | test | anonymous\` (a \`test\` account is a label from the product's Test Accounts table); the user has logged in as that account themselves and said "done"; on a surface shared by two legs the previous role is logged out first. The agent never types passwords, one-time codes or payment data.` Replace item 6 with the policy table:

```markdown
6. **Write boundary restated per leg**, resolved from the account:

| Account | Product | `write_boundary` | Behaviour |
|---|---|---|---|
| `own` or `anonymous` | own | `stop-before-irreversible` | stop before publish / pay / send / delete / place an order |
| `test` with `sandbox: yes` | own | `sandbox-confirm` | irreversible actions inside the test contour are allowed, **each confirmed by the user in one line before the tap**; "confirm all in this leg" switches the leg to `sandbox-auto` |
| `test` with `sandbox: no` | own | `stop-before-irreversible` | as own |
| any | competitor | `read-only` | no account creation, no orders, no messages, no reviews — ever |

Two hard stops that no boundary lifts: **real money** (a payment that is not a test method) and **actions visible to real users** (a message to a real seller, a public review on a real listing). The user may lift `stop-before-irreversible` for one leg in their own product; nothing lifts the hard stops.
```

- [ ] **Step 2: §5** — replace the first two bullets with: `- Credentials, one-time codes, payment data: user-only, always.` and `- The write boundary (§3 item 6) is resolved per leg from the account; \`sandbox-confirm\` asks before every irreversible action; the two hard stops (real money, actions visible to real users) hold under every boundary; competitor products are **read-only** without exception.`

- [ ] **Step 3: §7** — in `run.yaml` example replace `write_boundary: stop-before-irreversible   # or: lifted-by-user` with `write_boundary: sandbox-confirm   # worst boundary among legs; per-leg values below` and insert before `started:`:

```yaml
legs:
  - n: 1
    role: buyer
    account: test-buyer-1          # label from Test Accounts, or own | anonymous
    surface: iphone-on-mac
    goal: "Place an order in the test shop"
    write_boundary: sandbox-confirm
    started: 2026-09-10T12:30:00+03:00
    finished: 2026-09-10T12:40:00+03:00
    verdict: completed
    handoff: {order_id: "123456", shop: "Test Shop A"}
  - n: 2
    role: seller
    account: test-seller-shop-a
    surface: web
    goal: "Confirm and ship order 123456"
    write_boundary: sandbox-confirm
    started: 2026-09-10T12:41:00+03:00
    finished: 2026-09-10T12:46:00+03:00
    verdict: completed
    handoff: {tracking: "TTN-000"}
```

Change `verdict: completed           # completed | blocked_at:N | aborted` to `verdict: completed           # worst leg verdict: completed | blocked_at:L<leg>-<N> | aborted`. In `steps.yaml` example add `leg: 1` and `role: buyer` after each `n:` line and rename screenshots to `steps/L1-01.png` etc. After the `findings.md` sentence add: `Single-leg runs use \`leg: 1\` and the same naming; a \`user declined\` confirmation is logged as \`blocked_reason: user declined\` and ends the leg.`

- [ ] **Step 4: Lint + commit** → `git commit -m "feat(refs): app-drive-protocol — write-boundary policy by account, hard stops, legs in the evidence pack"`.

---

### Task 3: flow-walkthrough — legs (v0.2.0) + 3-leg fixture

**Files:**
- Modify: `skills/flow-walkthrough/SKILL.md` (description, Step 1, Step 2, Step 3, Step 6, Step 7 skill_version, version)
- Create: `skills/flow-walkthrough/examples/marketplace-order-to-review-flow.md`
- Modify: `README.md` (`Flow Walkthrough (v0.1.0)` → `(v0.2.0)` both places)

- [ ] **Step 1: description** — insert after `report, emulator/adb setup.` the words `Multi-role legs on test accounts (buyer → seller → buyer) with sandbox-confirm.` keeping "Not Figma review" within the first 192 characters (verify with `python3 -c` as in v3.1.0; shorten the lead if needed). `version: 0.2.0`.

- [ ] **Step 2: Step 1 scope** — replace items 4–5 of the scope list with:

```markdown
4. **Legs** — one leg by default. Two roles in the request ("як покупець, потім як продавець"), or a goal that needs another role to progress, make it multi-leg. Per leg: `role`, `account` (a label from the product's `#### Test Accounts` table, or `own` / `anonymous`), `surface`, `goal` (one sentence), `handoff_in` (values this leg needs from the previous one) and `handoff_out` (values it must capture, e.g. order id). No test account for a needed role → offer `add Test accounts` (plugin-configurator) or fall back to `own`.
5. **Write boundary per leg** — resolved from the account per `references/app-drive-protocol.md` §3 item 6 (`stop-before-irreversible` / `sandbox-confirm` / `sandbox-auto` / `read-only`) and restated in one line per leg: "Leg 1 buyer (test-buyer-1, sandbox-confirm): I will place a real order in the test shop and ask before each irreversible tap".
```

- [ ] **Step 3: Step 2 preflight** — after the first paragraph add: `Per leg: the account label exists for the role; the surface is ready; ask the user to log in as that account and wait for "done"; on a surface shared with the previous leg, log the previous role out first. The first screenshot of each leg is \`steps/L<leg>-00.png\`, saved and read back.`

- [ ] **Step 4: Step 3 walk loop** — after the severity list add:

```markdown
**Legs and confirmations.** Screenshot names are `steps/L<leg>-<NN>.png`; every `steps.yaml` row carries `leg` and `role`. Under `sandbox-confirm`, before every irreversible tap (place order, confirm, ship, publish, send) the skill stops and asks in one line — "Leg 2 / seller: confirm order 123456 — proceed?" — and waits; "no" logs `blocked_reason: user declined` and ends the leg; "confirm all in this leg" switches that leg to `sandbox-auto`. The two hard stops (real money, actions visible to real users) are never asked, always stopped. **Hand-off:** after a leg's last step, read every `handoff_out` value from the screenshot (order id, tracking number), write it to `run.yaml → legs[n].handoff`, echo it to the user; the next leg starts only when all its `handoff_in` values exist — otherwise pause and ask.
```

- [ ] **Step 5: Step 6 report** — after `Render the report through Step T.` add: `Multi-leg runs put a **leg summary table** (leg, role, account label, surface, steps, verdict) before the step table, and the step table carries a \`Leg / Role\` column.` Step 7: `skill_version: "0.2.0"`.

- [ ] **Step 6: fixture** — create `examples/marketplace-order-to-review-flow.md` (English, no Cyrillic in code blocks): 3 legs — L1 buyer `test-buyer-1` on iphone-on-mac: find a test-shop product → add to cart → checkout with a test payment / cash on delivery → confirm order → capture `order_id` (sandbox-confirm at "place order"); L2 seller `test-seller-shop-a` on web: open order `order_id` → confirm → mark shipped, capture `tracking` (confirmations at "confirm", "ship"); L3 buyer: orders → order `order_id` → leave review → publish (confirmation at "publish"). Expected hand-offs, expected confirmations (4), expected frictions to watch (rating position, draft loss, order status wording), and the note that a real-payment-only checkout ends L1 with `blocked_reason: real money`.

- [ ] **Step 7: README versions + lint + commit** → `git commit -m "feat(flow-walkthrough): multi-role legs on test accounts, sandbox-confirm, hand-off (v0.2.0)"`.

---

### Task 4: Report template v1.1.0

**Files:** Modify `templates/built-in/research/walkthrough-v1.md`.

- [ ] **Step 1** — `version: "1.1.0"`, `updated: 2026-09-11`; in `## 2. Step table and flow strip` insert before the step table:

```markdown
Leg summary (multi-leg runs):

| Leg | Role | Account | Surface | Steps | Verdict |
|-----|------|---------|---------|-------|---------|
| 1 | | | | | |
```

and change the step-table header to `| # | Leg / Role | Intent | Action | Observed | Status | Friction |` with the matching separator and blank row. Update the trailing marker comment to `version: 1.1.0`.

- [ ] **Step 2: Lint + commit** → `git commit -m "feat(templates): walkthrough-v1 1.1.0 — leg summary and Leg/Role column"`.

---

### Task 5: Release chores v3.2.0

**Files:** `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.codex-plugin/plugin.json`, `README.md`, `CHANGELOG.md`, `testing/trigger-evals.md`, `testing/test-cases.md`.

- [ ] **Step 1: manifests** — version `3.2.0`; description: after `flow walkthroughs in the real product (web, desktop, iPhone app on a Mac, Android via adb)` add `, multi-role legs on test accounts`; tail `— v3.2.0 (released 2026-09-11)`.
- [ ] **Step 2: README** — header/footer `3.2.0`; "New in v3.2.0" paragraph before "New in v3.1.0" (test accounts per role, legs, boundary policy, hard stops, sandbox-confirm, configurator add-on, fixture); section 30 gains a "Legs (v3.2.0)" sentence.
- [ ] **Step 3: CHANGELOG** — `## v3.2.0 (2026-09-11)` with Added (Test accounts schema + configurator add-on; legs; policy table + hard stops; template 1.1.0; fixture; Group N), Changed (flow-walkthrough 0.2.0, plugin-configurator 2.9.4), Not in this version (parallel legs on two devices, automatic account switching), Backwards compatibility (single-leg runs unchanged; default boundary unchanged).
- [ ] **Step 4: trigger-evals Group N** — 8 phrases: N1 «пройди як покупець, потім як продавець: замовлення → відправка → відгук» → flow-walkthrough; N2 «прогони шлях покупця на тестовому акаунті з оформленням замовлення» → flow-walkthrough; N3 «додай тестові акаунти для Prom» → plugin-configurator; N4 «налаштуй тестові акаунти продавця і покупця» → plugin-configurator; N5 «створи задачі для фічі відгуків» → task-creator; N6 «зафіксуй рішення: тестові акаунти лише на проді» → decision-log; N7 «підготуй мене до 1-1 з продавцем» → one-on-one; N8 «перевір мою специфікацію тестових акаунтів» → requirements-creator. Use `Prom` only inside the phrase column (the file already carries product names in phrases? — check Group K: it uses «картка товару»; keep phrases product-neutral: replace «для Prom» with «для продукту»).
- [ ] **Step 5: test-cases** — TC-flow-walkthrough-scenario-3 (3-leg fixture: legs table, four confirmations, hand-off order_id/tracking, worst-leg verdict), TC-plugin-configurator-test-accounts-1 (add-on writes the table, refuses a pasted secret), TC-flow-walkthrough-regression-2 (single-leg run identical to v3.1.0).
- [ ] **Step 6: validate + commit** — `bash testing/validate-consistency.sh && python3 testing/skill_lint.py` green → `git commit -m "chore(release): v3.2.0 — test accounts by role, multi-role legs"`.

---

### Task 6: Acceptance

- [ ] `bash testing/host-smoke.sh` → passed both hosts.
- [ ] Group N via `claude -p` (same harness as Group M) → 8/8; log in trigger-evals Results log.
- [ ] Fixture dry run: read `examples/marketplace-order-to-review-flow.md`, produce a leg summary + expected pack skeleton (`run.yaml` with 3 legs) in the scratchpad, check the schema matches §7.
- [ ] Real 3-leg walk on the reference app (needs the user: logins for the test buyer and a test seller company, one-time codes, and a "yes" per irreversible action). Record `actual`/`status` in test-cases; if the user is unavailable, mark `blocked: needs user logins` and say so in the PR.

### Task 7: PR

- [ ] `git push -u origin feature/v3.2-test-accounts-legs`, `gh pr create` titled "v3.2.0 — test accounts by role, multi-role walkthrough legs" with the verification block; merge on the user's word → release.yml tags v3.2.0.
