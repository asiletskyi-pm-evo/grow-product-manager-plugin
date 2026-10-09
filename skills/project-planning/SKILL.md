---
name: project-planning
version: 0.6.1
description: Multi-quarter delivery forecast for a project or mission — dependencies, critical path, duration at a team-% share. Not one quarter (quarterly-planning), not structure (roadmap-architect). UA — «скільки займе проєкт/місія», «roadmap проєкту на 3 квартали», «критичний шлях». EN — "project roadmap".
---

# Project Planning

> **Path rule.** A bare `references/<file>.md` in this file is read from this skill's own `references/` if the file exists there, otherwise from the **shared** `references/` at the plugin root. Resolve the root as `${PLUGIN_ROOT}`, else `${CLAUDE_PLUGIN_ROOT}`, else the directory that contains `skills/`, found by walking up from this folder (`references/host-profiles.md` §6). Never continue without a protocol named here.

Project/mission planning orchestrator (vertical axis: one direction across time). Estimates volume, builds dependencies and the critical path, forecasts duration under a team allocation %, lays out the arc (multi-quarter roadmap), and **replans** it against actuals (rolling-reforecast). **AI is the PM's advisor.**

Part of the planning-suite: supplies arcs and allocation % to `quarterly-planning`. Integrates with `product-reporter` (current state / % done ← `initiative-status`).

## Prerequisites
- `references/local-context-protocol.md` — Step 0 + Planning section.
- `references/planning-core.md` — model, labeling, goal map.
- `references/dependency-model.md` — epic/feature DAG, topo-sort, **critical path**, cycles.
- `references/capacity-model.md` — volume, auto-estimation, **allocation %**, `duration = critical_path_schedule(...)` (sec. 5, 10).
- `references/roadmap-artifacts.md` — project arc/Gantt format.
- `references/jira-data-protocol.md` — Jira plumbing (reuse).
- `references/integration-strategy.md`, `references/persistent-storage.md`, `references/template-protocol.md`.

## Step T — Template Resolution
`artifact_type: roadmap`, `subtype: project-arc`, `product_id`, `language`. Fallback → `roadmap-artifacts.md` sec. 3.

**Judgment footer (since v3.5.0).** The artifact closes with the altitude line from `templates/built-in/partial/judgment-footer-v1.md` (`references/template-protocol.md` T-5 step 3a; checked by `references/artifact-style-gate.md` Gate 4a).

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

> **Judgment contract (Step 0j).** Per `references/local-context-protocol.md` Step 0j and `references/pm-mental-model.md`: note this run's
> judgment points (score, rank, verdict, priority, ship/kill, debate question) internally, with no output. A principle acts only through
> a step that implements it — until one exists here, this skill's questions, gates and output stay exactly as they are.

### Step 1 — Scope
Pick the project/mission/initiative (goal PROJ-XX, epic, or a set of epics).

### Step 2 — Project content
Epics + features (CQL by epic, `getJiraIssue` per-key); volume by platform; **auto-estimate missing ones** (`capacity-model` sec. 8). Current state / % done — **delegate `product-reporter` `initiative-status`**.

### Step 3 — Dependency graph
Per `dependency-model.md`: derive from Jira links (Blocks/Relates) + PM input → DAG; topo-sort; **critical path**; flag cycles/breaks. **Gate** on manual dependencies.

### Step 4 — Allocation % to the direction
Ask for the **maximum available team %** for the direction (by platform). `effective_capacity = ceiling × %` (`capacity-model` sec. 5). Check that the sum of % across active directions ≤100%. **Gate.**

### Step 5 — Duration forecast
`duration ≈ critical_path_schedule(volume_by_platform, dependencies, effective_capacity)` (`capacity-model` sec. 10) → completion date + distribution across quarters/sprints.

### Step 6 — Project roadmap
Per `roadmap-artifacts.md` sec. 3: multi-quarter Gantt, critical path highlighted, forecast date, what-if by %. Workspace + library storage; save baseline for drift.

**Role defaults (since v3.6.0, `references/planning-core.md` §7).** When the request names no window, `role_defaults.horizon` sets the default arc window; `role_defaults.planning_view` sets the arc's depth — `rollup`: initiatives → epics first, features on request; `slice`: epics and features as before, plus the tech-debt reserve row of `references/capacity-model.md` §7 in the Step 4 capacity table. Rules in `references/arc-defaults.md`. Forecast, critical path, gates, baseline and the saved arc are the same for every profile; an automated run keeps the pre-v3.6.0 presentation.

### Replan — rolling-reforecast (mode `replan`)
Trigger: quarter boundary / on-demand / scheduled.
- R1. Current state ← `product-reporter` (`initiative-status` + quarter actuals); committed and **carried over** ← `quarterly-planning`.
- R2. Remainder = volume − done.
- R3. Backlog = remainder − committed_this_quarter (incl. carried over).
- R4. Re-sequence under dependencies + % for future periods.
- R5. New date + **drift vs baseline** (slip of N weeks + why; moving a critical-path item = arc shift).
- R5a. **Kill-criteria read-back (since v3.9.0, `references/judgment-points.md` §7).** Next to the drift, each earlier kill criterion due by now — of the missions, initiatives or epics in scope (the Pre-mortem roadmap-architect Step 4b wrote on their page or epic description) or of the current quarterly plan — reads fired / not fired / not measurable, judged only on data R1–R4 already fetched (anything else is not measurable). No question; a fired one joins the Replan decisions → decision-log offer when that offer is made — never on its own. The arc itself never gets a pre-mortem.
- R6. Update roadmap + risks; save the new baseline.

### Step 7 — Save to Vault (Optional)
Per `references/vault-protocol.md` → Vault Save. IF vault_level > L0 AND sync_mode != "off": `vault_save({ type: "roadmap", product: active_product, skill: "project-planning", skill_version: "0.6.1", tags: [project/mission key, directions], content: project arc + forecast (or replan drift report), related: [[goal artifact]], [[quarterly roadmaps]], extra_frontmatter: { subtype: "project-arc", baseline_date, forecast_date } })` → "Saved to Vault: Roadmaps/{product}/…". The saved baseline is what `replan` mode compares drift against.

## Integration
↔ `quarterly-planning` (down: arcs + allocation %; up: actuals + carryover → `replan`). ← `product-reporter` `initiative-status` (state / % done). ← `roadmap-architect` (structure). → `diagram-prototyper` (arc presentation). → `decision-log` (re-sequencing and scope calls made during `replan`).

**Replan decisions → decision-log.** A `replan` that changes the critical path or drops scope is a decision with a rationale worth keeping: offer to log what changed, the drift evidence that forced it, and the alternatives rejected. Since v3.9.0 the kill criteria R5a shows as fired join this offer, all together, when it is made; they never make or open the offer on their own (`references/judgment-points.md` §7, `references/planning-core.md` §8).

## Quality Standards
- Don't invent dependencies — only Jira links / Development Flow / explicit PM input; the rest = "break, please formalize".
- Recompute the critical path on every `replan`.
- Estimates/forecast — marked "pending TL/PM confirmation"; the PM decides.
- Always show drift vs baseline, not just the new state.
- Every date/number with context (allocation %, sprint count). Language — `user.language`.

## Additional Resources
`references/dependency-model.md`, `capacity-model.md`, `planning-core.md`, `roadmap-artifacts.md`, `local-context-protocol.md`, `template-protocol.md`, `persistent-storage.md`, `self-improvement.md`, `jira-data-protocol.md`; skill-local `references/arc-defaults.md` (arc window and view defaults).

## Routing

The `description` above is short on purpose: a host with many skills shows only part of the skill listing, or skill names alone (`references/host-profiles.md` §7). The full set of phrases and boundaries that route here, as the description carried them up to v3.10.0:

> Multi-quarter delivery forecast for a project or mission — dependencies, critical path, duration at a team-% share. Not one quarter (quarterly-planning), not structure (roadmap-architect). UA — «скільки займе проєкт/місія», «roadmap проєкту на 3 квартали», «критичний шлях», «% команди на напрямок». EN — "how long will the project take", "project roadmap", "epic sequence", "feature dependencies", "when will we finish the initiative", "team % on a direction", "replan the project". Also UA — «послідовність епіків», «залежності фіч», «переплан проєкту». Rolling reforecast; horizon = beyond one quarter.
