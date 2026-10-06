---
name: quarterly-planning
version: 0.8.0
description: One-quarter roadmap, capacity stress-test and plan-vs-actual retro. Not multi-quarter (project-planning), not structure/labels (roadmap-architect), not a sprint (sprint-planning). UA — «зібери roadmap на квартал», «plan-vs-actual», «чи реалістичний план на Q3», «що команда встигне». EN — "build a quarterly roadmap", "quarterly planning", "plan-vs-actual for the quarter", "quarter retro", "plan capacity", "what the team can deliver", "kill criteria / pre-mortem for the quarter plan". Also UA — «retro кварталу», «capacity плану», «kill criteria для плану кварталу». Scope = exactly one quarter.
---

# Quarterly Planning

> **Path rule.** A bare `references/<file>.md` in this file is read from this skill's own `references/` if the file exists there, otherwise from the **shared** `references/` at the plugin root. Resolve the root as `${PLUGIN_ROOT}`, else `${CLAUDE_PLUGIN_ROOT}`, else the directory that contains `skills/`, found by walking up from this folder (`references/host-profiles.md` §6). Never continue without a protocol named here.

Quarterly-planning orchestrator (horizontal axis: one period across all directions). Pulls the previous quarter's actuals, computes capacity for the new quarter, drafts the plan with auto-estimates, runs it through the capacity-gate, walks the PM through scope correction, and generates artifacts. Does not analyze or compute metrics itself — it delegates. **AI is the PM's advisor:** it proposes and highlights; the user decides.

Part of the planning-suite: `roadmap-architect` (structure) → **`quarterly-planning`** (quarter) → `sprint-planning` (sprint); `project-planning` supplies arcs / allocation %. Integrates with `product-reporter` (reporting — source of actuals).

## Prerequisites

Read and apply before starting:
- `references/local-context-protocol.md` — Step 0: local-context, active product, Planning section.
- `references/planning-core.md` — Goal→Initiative→Epic→Feature model, labeling convention, status normalization, goal map, Development Flow.
- `references/capacity-model.md` — ceiling formula, 4 inputs, allocation %, platform slices, auto-estimation, gate thresholds (85/100%).
- `references/dependency-model.md` — dependencies/sequencing (for carrying over unfinished work).
- `references/roadmap-artifacts.md` — roadmap page format, Gantt, live dashboard.
- `references/session-board.md` — tactical-session structure + quarterly board-prep checklist (for the retro/readout framing).
- `references/jira-data-protocol.md` — Jira plumbing (field map, JQL, extraction). **Reuse, don't duplicate.**
- `references/integration-strategy.md`, `references/persistent-storage.md`, `references/template-protocol.md`.

Planning section of local-context: team roster + capacity rules, sprints (cadence + anchor + board id), goal map, gate thresholds, Development Flow.

## Step T — Template Resolution
Per `references/template-protocol.md`: `artifact_type: roadmap`, `subtype: quarterly | retro`, `product_id`, `language`. Fallback → structure from `roadmap-artifacts.md`.

**Judgment footer (since v3.5.0).** The artifact closes with the altitude line from `templates/built-in/partial/judgment-footer-v1.md` (`references/template-protocol.md` T-5 step 3a; checked by `references/artifact-style-gate.md` Gate 4a). Since v3.7.0 a plan with a Step 4.4 prioritisation also carries the confidence line for that prioritised list above it (`references/judgment-points.md` §3; Gate 4c).

## Modes

| Mode | Steps | Output |
|------|-------|--------|
| `retro` | 1–2 | Plan-vs-actual for the previous quarter + lessons + calibrated baseline |
| `plan` | 1, 2-lite, 3–5 | Draft roadmap with a capacity traffic light |
| `full` (default) | 1–6 | Published roadmap + live dashboard |
| `refresh` | 2 + 6 | Updated statuses in existing artifacts |

## Pipeline

### Step 0 — Local context
Per `local-context-protocol.md`. If no Planning section → chain to `plugin-configurator` (Planning setup: team, sprints, baseline, goal map, thresholds, Development Flow), offer to save.

> **Judgment contract (Step 0j).** Per `references/local-context-protocol.md` Step 0j and `references/pm-mental-model.md`: note this run's
> judgment points (score, rank, verdict, priority, ship/kill, debate question) internally, with no output. A principle acts only through
> a step that implements it — until one exists here, this skill's questions, gates and output stay exactly as they are.

### Step 1 — Scope
`AskUserQuestion`: quarter; mode; format (Confluence + dashboard by default). Determine the previous quarter (retro) and the target quarter (plan).

### Step 2 — Actuals collection (retro)
**Delegate `product-reporter` `quarter-review`** for the previous quarter's plan-vs-actual (closed epics/features, releases, by direction). On top of that:
- Feature inventory: CQL `space={space} AND label="q{N-1}-{year}" AND type=page` (name-parsing regex from `planning-core`).
- Feature status normalization (`planning-core`) → done/in_progress/planned/blocked + miss reasons.
- **Baseline calibration** of velocity against actuals (`capacity-model` sec. 4; velocity from the Jira board id).
- **Kill-criteria read-back (since v3.9.0, `references/judgment-points.md` §7; `retro` and `full` only).** When the previous quarter's plan carries a Pre-mortem (its vault roadmap from Step 0.5, or its roadmap page), the retro shows each of its kill criteria as fired / not fired / not measurable, judged only on data this step already fetched (the `quarter-review` actuals, the feature inventory, the calibrated baseline) — anything else is not measurable. Reading the earlier plan is allowed; judging needs no other fetch, and nothing is asked; a plan without kill criteria gets no line. Fired ones join the existing Scope decisions → decision-log offer when that offer is made — never an offer of their own.

> **Step 2-lite (`plan` mode).** Steps 3c and 4.1 consume this step's outputs — calibrated velocity and carried-over work — so `plan` cannot skip it entirely; it used to, leaving both undefined. In `plan` mode run only the two data pulls, with no retro narrative: (a) unfinished features from the previous quarter's label → the carryover list; (b) velocity from the board's last 3–5 sprints → the baseline. If the board is unreachable, fall back to `planning.capacity.baseline_sp_per_sprint` from local-context and say which source was used. Skip miss-reason analysis and lessons — those belong to `retro`.
**Gate:** show the retro, confirm/correct.

### Step 3 — Capacity (4 inputs, each gated)
Per `capacity-model.md` sec. 2–5: (3a) team + involvement % (from local-context or survey; Jira matching; save updates); (3b) sprints in the period (board id / anchor; confirm or forecast); (3c) velocity (calibrated from Step 2 + PM confirmation); (3d) time off (calendar + survey → availability, default 0.9). **Allocation % by direction** ← from `project-planning` (sum ≤100%). Output: ceiling by platform.

### Step 4 — Draft + capacity-gate
1. Plan = carried-over unfinished work (Step 2) + new (label `q{N}`).
2. **Auto-estimate by analogy** for features without an estimate (`capacity-model` sec. 8; flag "pending TL confirmation").
3. **Capacity-gate** at the platform-slice level (`capacity-model` sec. 6–7): demand vs ceiling, 85/100% traffic light.
4. Prioritization (ICE/RICE) of candidates above the ceiling. **Since v3.7.0 (P2):** before the scores, ask the P2 question of `references/judgment-points.md` §1–§2 — which candidates the PM would keep first; all its §2 rules apply (switch, known estimate, automated run, skip). After the scores, show the "Your estimate vs mine" comparison. The scores and the capacity gate do not change with the answer. Asked once per run: a Step 5 recompute neither asks again nor repeats the comparison.

### Step 5 — Scope correction (loop with PM)
If a platform is over the ceiling — **show the specific directions→epics→features that don't fit** (with estimates) and offer a choice (interactive capacity-gate from `roadmap-artifacts` sec. 5; feature / platform-slice toggles). Recompute after each edit. Repeat until the PM is confident. The PM decides.

### Step 6 — Artifacts + storage
Per `roadmap-artifacts.md`: (1) **Confluence roadmap** (focuses + Gantt + tree, features as `code—name`) — publish **after approval**; (2) **live dashboard**; (3) `q{N}` labels on epics (`editJiraIssue`, preserving existing); (4) workspace + library storage (draft/final kept separate).

**Pre-mortem at scope lock (since v3.9.0, P4; `references/judgment-points.md` §7).** Once the PM locks the scope at the end of Step 5 — rendered once per run, at the first scope lock; a later Step 5 edit or re-lock does not re-render it (the PM edits it at approval) — the plan carries `templates/built-in/partial/pre-mortem-v1.md`, inserted per `references/template-protocol.md` T-5 step 3b (its placement; a user or product template only through `{{> pre-mortem}}`); in `plan` mode it goes on the draft roadmap Step 5 delivers. Derived, never asked:
- `judged_on` = the quarter end. 2–3 causes in the §7 order, from this run's signals only: analogy estimates still "pending TL confirmation" and other `assumed` inputs (`references/planning-core.md` §6), platforms amber or red at the capacity gate, critical-path and cross-team dependencies, carry-over and last quarter's miss reasons.
- One kill criterion per main focus: an observable signal; the threshold from the plan or its linked goal, else `⚠️ TBD`; a date no later than the quarter end; then descope (move to the next quarter) or stop. The confidence line's `would change if` never contradicts the first kill signal.
- The PM edits it at the existing approval; a deletion holds for this plan and is never learned (`references/self-improvement.md`). Not in `retro`; `refresh` keeps an existing Pre-mortem verbatim and never adds one. Step 4.4, the capacity gate and the approvals are unchanged; the block is the same for `rollup`, `slice` and every role.

**Presentation order (since v3.6.0, `references/planning-core.md` §7).** When `role_defaults.planning_view` is `rollup`, the roadmap page, dashboard and chat summary open with the main focuses and the goal → initiative tree, then the Gantt and the capacity table; `slice` keeps the pre-v3.6.0 order (capacity → focuses → Gantt → tree) with the tech-debt reserve as its own capacity row (`references/capacity-model.md` §7). The sections, numbers, capacity gate and approvals are the same for every profile; an automated run keeps the pre-v3.6.0 order.

**Optional — quarterly board / stakeholder readout (since v3.6.0: one template, one owner).** When the quarter is being reported up (not just planned), offer the readout as a hand-off to **product-reporter**, which renders it as `ops-report/board-update` from this run's retro (Step 2) and approved plan — no new fetch. This skill passes the data with `destination: chat draft` and `visuals: none` (product-reporter then asks nothing and publishes nothing until the user says so) and renders no readout of its own; the board-prep checklist behind the template is `references/session-board.md`.

### Step 7 — Save to Vault (Optional)
Per `references/vault-protocol.md` → Vault Save. IF vault_level > L0 AND sync_mode != "off": `vault_save({ type: "roadmap", product: active_product, skill: "quarterly-planning", skill_version: "0.8.0", tags: [quarter, directions], content: published roadmap (or retro), related: [[project arcs]], [[previous quarter roadmap]], extra_frontmatter: { subtype: "quarterly" | "retro", quarter, confluence_url } })` → "Saved to Vault: Roadmaps/{product}/…"

## Integration with product-reporter
- Quarter actuals ← `quarter-review` (don't rewrite the fetch).
- Approved roadmap → can be rendered as a stakeholder report via product-reporter; the board / stakeholder readout is its `ops-report/board-update` (Step 6).
- Shared Jira plumbing — `jira-data-protocol.md`.

## Skill Chaining
← `project-planning` (arcs + allocation %) · ← `roadmap-architect` (clean structure) · → `task-creator` (tasks from the plan) · → `sprint-planning` (nearest sprint) · → `diagram-prototyper` (presentation) · → `decision-log` (scope calls made in planning/retro — what got cut and why) · ← `meeting-processor` (decisions into focuses).

**Scope decisions → decision-log.** When the capacity gate forces something out of the quarter, or the retro concludes a direction was mis-bet, offer to log it: "This cut is a decision someone will ask about next quarter. Log it?" → invoke `decision-log` (log mode) with the options considered, the capacity evidence, and what was cut (since v3.7.0 the PM as `owner` and the cut items with their reasons as `rejected_alternatives` — `references/judgment-points.md` §4). Since v3.9.0 the kill criteria the Step 2 read-back shows as fired join this offer, all together, when it is made; they never make or open the offer on their own (§7, `references/planning-core.md` §8).

## Quality Standards
- Human-in-the-loop: every input passes a "confirm/correct" gate.
- AI estimates/recommendations — marked "pending TL/analyst confirmation"; the PM decides.
- Overload = show the entities + offer a choice, never bare SP.
- Features — listed as `code — name`.
- Platform readiness: don't require a cross-platform launch unless critical.
- Draft ≠ final: write to Confluence/Jira only after approval.
- Every number with an inline period. Language — `user.language`.

## Additional Resources
`references/planning-core.md`, `capacity-model.md`, `dependency-model.md`, `roadmap-artifacts.md`, `local-context-protocol.md`, `template-protocol.md`, `persistent-storage.md`, `self-improvement.md`, `jira-data-protocol.md`.
