---
template_id: ops-report-builtin-board-update
schema_version: 1
name: "Board Update"
artifact_type: ops-report
subtype: board-update
scope: built-in
products: []
match: subtype
default_language: en
available_languages: [en]
version: "1.1.0"
author: "grow-pm"
created: 2026-09-29
updated: 2026-10-06
tags: [ops, board, quarter, readout, business]
description: "Quarterly board update (since v3.6.0): the board-prep checklist of references/session-board.md rendered as a document, plus the money bridge"
status: active
min_plugin_version: "3.6.0"
variables:
  - { name: team_name, type: string, required: true, label: "Team or direction" }
  - { name: quarter, type: string, required: true, label: "Quarter reported" }
---

<!-- lang:en -->
# Board update: {{team_name}} · {{quarter}}

<!-- Rendered from references/session-board.md → "Quarterly board / readout — preparation checklist". Bring worked-through questions only: each with the owner's proposal and argument. -->

## Follow-up statuses from the previous board

<!-- Every decision of the previous board with its status. GTD coefficient = decisions done / decisions taken on, for this list as a whole (target ≥ 80%) — never a person's GTD-index. -->

| Decision | Owner | Due | Status |
|----------|-------|-----|--------|
| TBD | | | |

GTD coefficient: TBD

## Planned vs actual, previous period

<!-- Plan vs fact for the period, full-year forecast at the current trend, deviations with causes. Every actual carries its period, source marker and evidence class (pm-mental-model.md §4): `measured` only when the skill read or counted it itself through its data gate, a pasted or typed figure `reported (<who>)` — one label per table when every figure shares class and source. Plan and forecast carry no class, only their basis; an unsourced input inside them reads `[assumed — …]`. If the revenue or goal plan is missed — the catch-up options already worked out. -->

| Line | Plan | Actual | Δ | Full-year forecast | Cause |
|------|-----:|-------:|--:|-------------------:|-------|
| TBD | | | | | |

{{> money-bridge}}

## Strategic and operational goals

<!-- Per goal: status and year-end forecast; if deviating — why and how it is being solved; a changed goal — the reason; new goals with the resources they need. Direction and product goals only (OKR or direction-level targets) — never a person's goal, a 3T5F person report or a profile; headline goals as SMARTCBP (references/goal-frameworks.md), progress as 3T5F (references/reporting-3t5f.md). -->
- TBD

## AI and innovation for cost reduction

<!-- In money, in a table; idea profitability via ROAIP (references/roi-frameworks.md). -->

| Initiative | Hours saved | Money value | What it enabled (not hired / freed / same team does more) |
|------------|------------:|------------:|-----------------------------------------------------------|
| TBD | | | |

## Product and health metrics

<!-- B2B: the LAC table — CSAT or analogue, adoption rate, LTV, ideally expansion / downgrade / churn. A product direction: its funnel and NPS themes. Each metric with its period and evidence class. -->
- TBD

## Acquisition-channel hypotheses

<!-- A channel counts as found when the ICP, the reach, the interest (AIDA) and the path to payment are known; show statistics (each with its evidence class and source), required investment and forecast (no class — its basis named; an unsourced input reads `[assumed — …]`). Un-costed organic is not a channel. -->

| Channel | ICP | Reach | Interest (AIDA) | Path to payment | Investment | Forecast |
|---------|-----|-------|-----------------|-----------------|-----------:|---------:|
| TBD | | | | | | |

## Questions for approval

<!-- Worked through: each with the proposal, the argument and the recommended option. -->
- TBD
<!-- /lang:en -->
