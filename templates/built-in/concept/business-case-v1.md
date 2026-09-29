---
template_id: concept-builtin-business-case
schema_version: 1
name: "Business Case"
artifact_type: concept
subtype: business-case
scope: built-in
products: []
match: subtype
default_language: en
available_languages: [en]
version: "1.0.0"
author: "grow-pm"
created: 2026-09-29
updated: 2026-09-29
tags: [concept, business-case, unit-economics, investment, kill-criteria]
description: "Business case (since v3.6.0): market, traction, unit economics, projections, money bridge, risks, kill criteria"
status: active
min_plugin_version: "3.6.0"
variables:
  - { name: feature_name, type: string, required: true, label: "Initiative or bet" }
  - { name: problem_statement, type: text, required: true, label: "Opportunity or problem" }
  - { name: target_audience, type: text, required: true, label: "Target customers or segment" }
  - { name: kill_criteria, type: list, required: false, label: "Kill criteria" }
---

<!-- lang:en -->
# Business case: {{feature_name}}

## Opportunity

{{problem_statement}}

**Target customers:** {{target_audience}}

## Market

<!-- Size, growth, segment and competitors — each number with its source and date; a range rather than a single point where estimates differ. -->
- TBD

## Traction

<!-- Evidence so far — usage, pilots, pipeline, experiments — each with its period and source. -->
- TBD

## Unit economics

<!-- Per unit, current vs target. Inputs without data are labelled `assumed`. -->

| Line | Current | Target | Source |
|------|---------|--------|--------|
| CAC | TBD | TBD | TBD |
| LTV | TBD | TBD | TBD |
| Contribution margin | TBD | TBD | TBD |
| Payback period | TBD | TBD | TBD |

## Projections

<!-- Low / base / high scenarios with the drivers behind each, the investment and the payback. List the assumptions; name the base rate for comparable initiatives, or say none is known. -->
- TBD

{{> money-bridge}}

## Risks

<!-- Risk · likelihood · impact · mitigation. -->
- TBD

## Kill criteria

<!-- The signal and the date at which we stop or pivot — fixed before launch. -->
{{#each kill_criteria}}
- {{this}}
{{/each}}

## Decision requested

<!-- Invest / continue / kill — with the amount, the owner and the date of the next review. -->
- TBD
<!-- /lang:en -->
