---
name: quarterly-planning
version: 0.1.1
description: Builds a quarterly roadmap, reviews the previous quarter's delivery, and stress-tests the plan against team capacity. Use when the user asks to "build a quarterly roadmap", "quarterly planning", "plan-vs-actual for the quarter", "quarter retro", "plan capacity", "what the team can deliver", "is the quarterly plan realistic". Українською: "зібрати roadmap на квартал", "quarterly planning", "plan-vs-actual кварталу", "retro кварталу", "capacity плану", "що команда встигне", "оцінити реалістичність плану на квартал".
---

# Quarterly Planning

Quarterly-planning orchestrator (horizontal axis: one period across all directions). Pulls the previous quarter's actuals, computes capacity for the new quarter, drafts the plan with auto-estimates, runs it through the capacity-gate, walks the PM through scope correction, and generates artifacts. Does not analyze or compute metrics itself — it delegates. **AI is the PM's advisor:** it proposes and highlights; the user decides.

Part of the planning-suite: `roadmap-architect` (structure) → **`quarterly-planning`** (quarter) → `sprint-planning` (sprint); `project-planning` supplies arcs / allocation %. Integrates with `team-ops-reporter` (reporting — source of actuals).

## Prerequisites

Read and apply before starting:
- `references/local-context-protocol.md` — Step 0: local-context, active product, Planning section.
- `references/planning-core.md` — Goal→Initiative→Epic→Feature model, labeling convention, status normalization, goal map, Development Flow.
- `references/capacity-model.md` — ceiling formula, 4 inputs, allocation %, platform slices, auto-estimation, gate thresholds (85/100%).
- `references/dependency-model.md` — dependencies/sequencing (for carrying over unfinished work).
- `references/roadmap-artifacts.md` — roadmap page format, Gantt, live dashboard.
- `skills/team-ops-reporter/references/jira-data-protocol.md` — Jira plumbing (field map, JQL, extraction). **Reuse, don't duplicate.**
- `references/integration-strategy.md`, `references/persistent-storage.md`, `references/template-protocol.md`.

Planning section of local-context: team roster + capacity rules, sprints (cadence + anchor + board id), goal map, gate thresholds, Development Flow.

## Step T — Template Resolution
Per `references/template-protocol.md`: `artifact_type: roadmap`, `subtype: quarterly | retro`, `product_id`, `language`. Fallback → structure from `roadmap-artifacts.md`.

## Modes

| Mode | Steps | Output |
|------|-------|--------|
| `retro` | 1–2 | Plan-vs-actual for the previous quarter + lessons + calibrated baseline |
| `plan` | 1, 3–5 | Draft roadmap with a capacity traffic light |
| `full` (default) | 1–6 | Published roadmap + live dashboard |
| `refresh` | 2 + 6 | Updated statuses in existing artifacts |

## Pipeline

### Step 0 — Local context
Per `local-context-protocol.md`. If no Planning section → chain to `plugin-configurator` (Planning setup: team, sprints, baseline, goal map, thresholds, Development Flow), offer to save.

### Step 1 — Scope
`AskUserQuestion`: quarter; mode; format (Confluence + dashboard by default). Determine the previous quarter (retro) and the target quarter (plan).

### Step 2 — Actuals collection (retro)
**Delegate `team-ops-reporter` `quarter-review`** for the previous quarter's plan-vs-actual (closed epics/features, releases, by direction). On top of that:
- Feature inventory: CQL `space={space} AND label="q{N-1}-{year}" AND type=page` (name-parsing regex from `planning-core`).
- Feature status normalization (`planning-core`) → done/in_progress/planned/blocked + miss reasons.
- **Baseline calibration** of velocity against actuals (`capacity-model` sec. 4; velocity from the Jira board id).
**Gate:** show the retro, confirm/correct.

### Step 3 — Capacity (4 inputs, each gated)
Per `capacity-model.md` sec. 2–5: (3a) team + involvement % (from local-context or survey; Jira matching; save updates); (3b) sprints in the period (board id / anchor; confirm or forecast); (3c) velocity (calibrated from Step 2 + PM confirmation); (3d) time off (calendar + survey → availability, default 0.9). **Allocation % by direction** ← from `project-planning` (sum ≤100%). Output: ceiling by platform.

### Step 4 — Draft + capacity-gate
1. Plan = carried-over unfinished work (Step 2) + new (label `q{N}`).
2. **Auto-estimate by analogy** for features without an estimate (`capacity-model` sec. 8; flag "pending TL confirmation").
3. **Capacity-gate** at the platform-slice level (`capacity-model` sec. 6–7): demand vs ceiling, 85/100% traffic light.
4. Prioritization (ICE/RICE) of candidates above the ceiling.

### Step 5 — Scope correction (loop with PM)
If a platform is over the ceiling — **show the specific directions→epics→features that don't fit** (with estimates) and offer a choice (interactive capacity-gate from `roadmap-artifacts` sec. 5; feature / platform-slice toggles). Recompute after each edit. Repeat until the PM is confident. The PM decides.

### Step 6 — Artifacts + storage
Per `roadmap-artifacts.md`: (1) **Confluence roadmap** (focuses + Gantt + tree, features as `code—name`) — publish **after approval**; (2) **live dashboard**; (3) `q{N}` labels on epics (`editJiraIssue`, preserving existing); (4) workspace + library storage (draft/final kept separate).

## Integration with team-ops-reporter
- Quarter actuals ← `quarter-review` (don't rewrite the fetch).
- Approved roadmap → can be rendered as a stakeholder report via team-ops-reporter.
- Shared Jira plumbing — `jira-data-protocol.md`.

## Skill Chaining
← `project-planning` (arcs + allocation %) · ← `roadmap-architect` (clean structure) · → `task-creator` (tasks from the plan) · → `sprint-planning` (nearest sprint) · → `diagram-prototyper` (presentation) · ← `meeting-processor` (decisions into focuses).

## Quality Standards
- Human-in-the-loop: every input passes a "confirm/correct" gate.
- AI estimates/recommendations — marked "pending TL/analyst confirmation"; the PM decides.
- Overload = show the entities + offer a choice, never bare SP.
- Features — listed as `code — name`.
- Platform readiness: don't require a cross-platform launch unless critical.
- Draft ≠ final: write to Confluence/Jira only after approval.
- Every number with an inline period. Language — `user.language`.

## Additional Resources
`references/planning-core.md`, `capacity-model.md`, `dependency-model.md`, `roadmap-artifacts.md`, `local-context-protocol.md`, `template-protocol.md`, `persistent-storage.md`, `self-improvement.md`; `skills/team-ops-reporter/references/jira-data-protocol.md`.
