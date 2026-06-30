---
name: project-planning
version: 0.1.1
description: Plans and forecasts delivery of a project/mission/initiative beyond a single quarter — estimates the total volume of epics/features, builds a dependency graph and sequence, computes duration under a given team allocation % to the direction, and lays out a multi-quarter project roadmap with rolling-reforecast. Use when the user asks "how long will the project take", "project roadmap", "epic sequence", "feature dependencies", "when will we finish the initiative", "team % on a direction", "critical path", "replan the project". Українською: "скільки займе проєкт", "roadmap проєкту", "послідовність епіків", "залежності фіч", "коли завершимо ініціативу", "% команди на напрямок", "критичний шлях", "переплан проєкту".
---

# Project Planning

Project/mission planning orchestrator (vertical axis: one direction across time). Estimates volume, builds dependencies and the critical path, forecasts duration under a team allocation %, lays out the arc (multi-quarter roadmap), and **replans** it against actuals (rolling-reforecast). **AI is the PM's advisor.**

Part of the planning-suite: supplies arcs and allocation % to `quarterly-planning`. Integrates with `team-ops-reporter` (current state / % done ← `initiative-status`).

## Prerequisites
- `references/local-context-protocol.md` — Step 0 + Planning section.
- `references/planning-core.md` — model, labeling, goal map.
- `references/dependency-model.md` — epic/feature DAG, topo-sort, **critical path**, cycles.
- `references/capacity-model.md` — volume, auto-estimation, **allocation %**, `duration = critical_path_schedule(...)` (sec. 5, 10).
- `references/roadmap-artifacts.md` — project arc/Gantt format.
- `skills/team-ops-reporter/references/jira-data-protocol.md` — Jira plumbing (reuse).
- `references/integration-strategy.md`, `references/persistent-storage.md`, `references/template-protocol.md`.

## Step T — Template Resolution
`artifact_type: roadmap`, `subtype: project-arc`, `product_id`, `language`. Fallback → `roadmap-artifacts.md` sec. 3.

## Modes

| Mode | Output |
|------|--------|
| `forecast` | Volume + allocation % → duration and completion date |
| `sequence` | Dependency graph → sequence + critical path |
| `roadmap` | Multi-quarter project roadmap (Gantt) |
| `whatif` | Vary % / scope → date change |
| `replan` | Rolling-reforecast: actuals + quarter plan → carry the unfit volume forward + drift vs baseline |

## Pipeline

### Step 0 — Local context
Per `local-context-protocol.md` + Planning (capacity rules, sprints, goal map, Development Flow).

### Step 1 — Scope
Pick the project/mission/initiative (goal EVOCO1-XX, epic, or a set of epics).

### Step 2 — Project content
Epics + features (CQL by epic, `getJiraIssue` per-key); volume by platform; **auto-estimate missing ones** (`capacity-model` sec. 8). Current state / % done — **delegate `team-ops-reporter` `initiative-status`**.

### Step 3 — Dependency graph
Per `dependency-model.md`: derive from Jira links (Blocks/Relates) + PM input → DAG; topo-sort; **critical path**; flag cycles/breaks. **Gate** on manual dependencies.

### Step 4 — Allocation % to the direction
Ask for the **maximum available team %** for the direction (by platform). `effective_capacity = ceiling × %` (`capacity-model` sec. 5). Check that the sum of % across active directions ≤100%. **Gate.**

### Step 5 — Duration forecast
`duration ≈ critical_path_schedule(volume_by_platform, dependencies, effective_capacity)` (`capacity-model` sec. 10) → completion date + distribution across quarters/sprints.

### Step 6 — Project roadmap
Per `roadmap-artifacts.md` sec. 3: multi-quarter Gantt, critical path highlighted, forecast date, what-if by %. Workspace + library storage; save baseline for drift.

### Replan — rolling-reforecast (mode `replan`)
Trigger: quarter boundary / on-demand / scheduled.
- R1. Current state ← `team-ops-reporter` (`initiative-status` + quarter actuals); committed and **carried over** ← `quarterly-planning`.
- R2. Remainder = volume − done.
- R3. Backlog = remainder − committed_this_quarter (incl. carried over).
- R4. Re-sequence under dependencies + % for future periods.
- R5. New date + **drift vs baseline** (slip of N weeks + why; moving a critical-path item = arc shift).
- R6. Update roadmap + risks; save the new baseline.

## Integration
↔ `quarterly-planning` (down: arcs + allocation %; up: actuals + carryover → `replan`). ← `team-ops-reporter` `initiative-status` (state / % done). ← `roadmap-architect` (structure). → `diagram-prototyper` (arc presentation). ← `cjm-research`/`brainstorm-features` (new epics/features).

## Quality Standards
- Don't invent dependencies — only Jira links / Development Flow / explicit PM input; the rest = "break, please formalize".
- Recompute the critical path on every `replan`.
- Estimates/forecast — marked "pending TL/PM confirmation"; the PM decides.
- Always show drift vs baseline, not just the new state.
- Every date/number with context (allocation %, sprint count). Language — `user.language`.

## Additional Resources
`references/dependency-model.md`, `capacity-model.md`, `planning-core.md`, `roadmap-artifacts.md`, `local-context-protocol.md`, `template-protocol.md`, `persistent-storage.md`, `self-improvement.md`; `skills/team-ops-reporter/references/jira-data-protocol.md`.
