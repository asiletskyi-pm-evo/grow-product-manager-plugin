---
name: flow-walkthrough
version: 0.2.0
description: Walk a customer flow in the REAL product — web, desktop, iPhone app on a Mac, Android via adb — screenshot per step, friction, evidence pack, report, emulator/adb setup. Not Figma review (design-bridge), not dashboards (product-analysis), not the CJM pipeline (cjm-research calls here). Multi-role legs on test accounts with sandbox-confirm. UA — «пройди флоу», «пройди шлях покупця в застосунку», «перевір зручність … у застосунку», «порівняй флоу на iOS і web», «налаштуй емулятор/adb для проходу». EN — "walk the flow", "walk through the app as a user", "test this journey in the real app", "compare the flow across platforms", "set up the emulator". Modes setup / walk / compare / audit; chains to brainstorm-features, requirements-creator, cjm-research, diagram-prototyper.
---

# Flow Walkthrough

> **Path rule.** A bare `references/<file>.md` in this file is read from this skill's own `references/` if the file exists there, otherwise from the **shared** `references/` at the plugin root. Resolve the root as `${PLUGIN_ROOT}`, else `${CLAUDE_PLUGIN_ROOT}`, else the directory that contains `skills/`, found by walking up from this folder (`references/host-profiles.md` §6). Never continue without a protocol named here.

Drive the real product the way a customer does and turn the walk into evidence: one screenshot per step, friction graded per step, a local evidence pack and a report other skills reuse. Everything about *how* to drive lives in `references/app-drive-protocol.md`; this file is the workflow.

## Integration prerequisite

Read `references/integration-strategy.md` for publishing (Confluence) and for browser tools on the `web` surface. Read `references/data-policy.md`: screenshots are internal data — local only, never to external LLMs. Optional enrichment: if a Lazyweb MCP is present (`mcp__lazyweb__lazyweb_search`), one quick search per major-or-worse friction for a real-app reference; never a report-generator call unless the user asks for one.

## Local context prerequisite

**Before starting, follow `references/local-context-protocol.md` (Step 0).** Then `references/host-profiles.md` §3 with the sixth capability **APP-DRIVE** (`references/app-drive-protocol.md` §1). Say the resolved level in one line — "driving via foreground control — the machine is busy for the run".

Key context used by this skill: `product.name`, `product.platforms`, `product.competitors`, `product.confluence_space`, `user.language`, `storage_root`.

## Step T — Template Resolution

Follow `references/template-protocol.md`. Declare `artifact_type: research`, `subtype: walkthrough`, `product_id` from the active product, `language` from `user.language`. Built-in fallback: `builtin://research/walkthrough-v1.md`. Skip Step T in `setup` mode (no artifact).

## Step 1 — Mode and scope

Pick the mode from the request; ask one AskUserQuestion only when two modes fit:

| Mode | Trigger shape | Output |
|---|---|---|
| `setup` | "set up …", or `walk` asked on a surface the preflight marks `missing` | readiness table → setup steps → smoke test |
| `walk` | one product, one surface, one scenario | evidence pack + report |
| `compare` | "compare … on …", two or more (product, surface) pairs | one pack per run + comparison report |
| `audit` | "audit / rate / evaluate this walkthrough", or a pack path | graded findings + recommendations |

Scope for `walk` / `compare` — collect, then restate in one block before starting:

1. **Product** — own (from local-context) or a competitor (`product.competitors`; anything else the user names is fine). Competitors are read-only, always.
2. **Surface** — `web | desktop | iphone-on-mac | android-adb` (`ios-simulator` needs a build from the mobile team — v1.1).
3. **Scenario** — one sentence, the customer's goal, e.g. "leave a review for a delivered order". Split a long journey into at most 12 steps; longer → two runs.
4. **Legs** — one leg by default. Two roles in the request ("as buyer, then as seller"), or a goal that needs another role to progress, make it multi-leg. Per leg: `role`, `account` (a label from the product's `#### Test Accounts` table in `local-context.md`, or `own` / `anonymous`), `surface`, `goal` (one sentence), `handoff_in` (values this leg needs from the previous one) and `handoff_out` (values it must capture, e.g. the order id). No test account for a needed role → offer `add Test accounts` (plugin-configurator) or fall back to `own`. The user logs in themselves; the agent never types passwords, one-time codes or payment data.
5. **Write boundary per leg** — resolved from the account per `references/app-drive-protocol.md` §3 item 6 (`stop-before-irreversible` / `sandbox-confirm` / `sandbox-auto` / `read-only`) and restated in one line per leg: "Leg 1 buyer (test-buyer-1, sandbox-confirm): I will place a real order in the test shop and ask before each irreversible tap". The two hard stops — real money, actions visible to real users — hold under every boundary.

## Step 2 — Preflight

Run `scripts/walkthrough_preflight.sh` when SHELL is present and parse the `SURFACE | STATUS | MISSING | WHO` lines; without SHELL, ask the user the same questions (macOS? Apple Silicon? adb installed? phone attached?). Then `references/app-drive-protocol.md` §3 in full: target visible, overlay utilities quit (name them), machine-busy warning for `foreground`, account and boundary restated, `steps/L<leg>-00.png` saved **and read back**.

Per leg: the account label exists for the role; the surface is ready; ask the user to log in as that account and wait for "done"; on a surface shared with the previous leg, log the previous role out first.

Create the pack folder `{storage_root}/walkthroughs/<YYYY-MM-DD>-<product-slug>-<flow-slug>/` with `steps/` inside (`references/persistent-storage.md`). No FS → keep the pack in the chat (`references/app-drive-protocol.md` §6).

## Step 3 — Walk loop

Follow `references/app-drive-protocol.md` §4 for each step: intent → action → wait → screenshot → **verify** → log. Write the `steps.yaml` row immediately (schema in the protocol §7). Friction is graded as seen:

- `blocker` — the customer cannot finish the goal
- `major` — finishes, but with an error, a wrong mental model, or a lost input
- `minor` — extra taps, hidden entry points, unclear labels
- `cosmetic` — alignment, wording, spacing

**Legs and confirmations.** Screenshot names are `steps/L<leg>-<NN>.png`; every `steps.yaml` row carries `leg` and `role`. Under `sandbox-confirm`, before every irreversible tap (place order, confirm, ship, publish, send) the skill stops and asks in one line — "Leg 2 / seller: confirm order 123456 — proceed?" — and waits; "no" logs `blocked_reason: user declined` and ends the leg; "confirm all in this leg" switches that leg to `sandbox-auto`. The two hard stops (real money, actions visible to real users) are never asked, always stopped. **Hand-off:** after a leg's last step, read every `handoff_out` value from the screenshot (order id, tracking number), write it to `run.yaml → legs[n].handoff`, echo it to the user; the next leg starts only when all its `handoff_in` values exist — otherwise pause and ask.

Each friction names a heuristic: Nielsen `N1`…`N10` (N1 visibility of status, N2 match with the real world, N3 user control, N4 consistency, N5 error prevention, N6 recognition over recall, N7 flexibility, N8 minimalism, N9 error recovery, N10 help) or a CJM stage id from `references/cjm-protocol.md`.

Stop conditions: the write boundary (log `blocked_reason: write boundary`), a `blocked` step after one retry, the user says stop, or an app takes focus (pause; resume on the user's word). Close the run: `run.yaml` with `verdict`, `findings.md` grouped by severity.

## Step 4 — Compare (compare mode)

Run Step 2–3 once per (product, surface); in parallel per `references/subagent-delegation.md` only when the surfaces do not share the screen (web tabs and adb can run alongside; two `foreground` runs cannot). Then `compare.yaml` (protocol §7): align steps by **intent**, not by index; a step present on one surface only is a finding.

## Step 5 — Audit (audit mode, or after walk/compare)

Input: a pack (path or chat). For every friction: confirm severity against the screenshot, add the heuristic if missing, and write one recommendation. Rank by severity, then by how early in the flow it hits. With Lazyweb present: one `lazyweb_search` per major-or-worse friction (2–6 word pattern, platform mobile/desktop) and cite the reference in the recommendation. Output the findings section of the report.

## Step 6 — Report and flow strip

Render the report through Step T. Multi-leg runs put a **leg summary table** (leg, role, account label, surface, steps, verdict) before the step table, and the step table carries a `Leg / Role` column. **Flow strip**: annotate `steps/NN.png` per `references/visual-annotation-protocol.md` with marker number = step number, legend = the step table; preview with the user (V-4); store per V-5; attach per V-6 when publishing. Publish like product-research (Confluence space from `product.confluence_space`, or local). The Sources section names the pack ids and the account type; screenshots of an `own` account are not attached to shared pages unless the user says so.

## Step 7 — Save to Vault (optional)

> Requires: `references/vault-protocol.md` → Vault Save

IF vault_level > L0 AND sync_mode != "off":

1. `vault_save({ type: "walkthrough", product: active_product, skill: "flow-walkthrough", skill_version: "0.2.0", tags: [scenario slug, surfaces], content: final report, related: [pack run ids], extra_frontmatter: { confluence_url (if published), account_type } })`
2. Display: "Saved to Vault: Research/walkthroughs/{product}/…"

## Setup mode

1. Preflight table (Step 2).
2. For every `partial | missing` row of the requested surface, one step at a time, each installation confirmed by the user before it runs; rows with `WHO = user` are handed over as a numbered instruction the user performs (install from the App Store, `sudo xcode-select`, enable USB debugging, log in), and the agent waits for "done".
3. Smoke test: open the target → save a screenshot → read it back → one tap → screenshot shows the change. Green → "setup complete for <surface>". Red → the failing line, and the next thing to try from the driver table (`references/app-drive-protocol.md` §2).
4. Never install anything unasked; never change system settings — say what the user must change and why.

## Skill Chaining

- → **Brainstorm Features** — "Generate hypotheses from these frictions"
- → **Requirements Creator** — "Write requirements for step N; use steps/NN.png as the as-is screen"
- → **CJM Research** — "Use this walkthrough as stage evidence for the funnel"
- → **Diagram & Prototype Creator** — "Draw the flow from steps.yaml"
- → **Decision Log** — "Log the decision on the blocker"
- ← `cjm-research` (walks a funnel stage as the enrichment source `walkthrough-local`)
- ← `product-research` (UX benchmark: compare mode on competitors)
- ← `requirements-creator` (needs an as-is screen and no screenshot source exists)

## Quality standards

- One screenshot per step, read back from disk; a step without a verified screenshot is not a step.
- A blocked step is reported as a finding with its reason, never silently skipped.
- Severity and heuristic on every friction; no friction without a step number.
- The write boundary and the account type appear in the report's Sources.
- Output language from `user.language`.

## Example

`examples/marketplace-review-flow.md` — the single-leg reference walk (leave a review in a marketplace buyer app, iPhone app on a Mac): expected step list, expected frictions, and the driver facts it taught. `examples/marketplace-order-to-review-flow.md` — the three-leg reference (test buyer orders → test seller confirms and ships → buyer reviews) with hand-offs and sandbox confirmations. Use them to dry-run `audit` and to sanity-check a new driver.
