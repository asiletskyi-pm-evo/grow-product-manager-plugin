---
template_id: research-builtin-walkthrough
schema_version: 1
name: "Flow Walkthrough Report"
artifact_type: research
subtype: walkthrough
scope: built-in
products: []
default_language: en
available_languages: [en]
version: "1.1.0"
author: "grow-pm"
created: 2026-09-10
updated: 2026-09-11
tags: [research, walkthrough, ux, flow]
description: "Flow walkthrough report: scenario, surfaces, step table with flow strip, friction by severity, comparison matrix, recommendations"
status: active
min_plugin_version: "3.1.0"
variables:
  - name: scenario
    type: string
    required: true
    label: "Scenario (one sentence, the customer's goal)"
  - name: product
    type: string
    required: true
    label: "Product"
  - name: surfaces
    type: list
    required: true
    label: "Surfaces walked"
  - name: account_type
    type: enum
    required: true
    label: "Account used"
    options: [own, test, anonymous]
  - name: write_boundary
    type: string
    required: true
    label: "Write boundary applied"
  - name: run_ids
    type: list
    required: true
    label: "Evidence pack run ids"
  - name: sources
    type: list
    required: false
    label: "Other sources"
---

<!-- lang:en -->
# Flow Walkthrough: {{scenario}}

## 1. Scope

- Product: {{product}}
- Surfaces: {{#each surfaces}}{{this}}{{#unless @last}}, {{/unless}}{{/each}}
- Account: {{account_type}} · Write boundary: {{write_boundary}}
- Evidence packs: {{#each run_ids}}`{{this}}`{{#unless @last}}, {{/unless}}{{/each}}

## 2. Step table and flow strip

Leg summary (multi-leg runs):

| Leg | Role | Account | Surface | Steps | Verdict |
|-----|------|---------|---------|-------|---------|
| 1 | | | | | |

| # | Leg / Role | Intent | Action | Observed | Status | Friction |
|---|------------|--------|--------|----------|--------|----------|
| 1 | L1 / | | | | ok / friction / blocked | |

Flow strip: one annotated screenshot per step, marker number = step number (per `visual-annotation-protocol.md`), legend = this table.

## 3. Friction findings

### Blockers

### Major

### Minor

### Cosmetic

Each item: `step N` — what the customer expected — what happened — heuristic (Nielsen N1-N10 or CJM stage).

## 4. Comparison matrix (compare mode only)

| Step intent | {{#each surfaces}}{{this}} | {{/each}}
|---|{{#each surfaces}}---|{{/each}}

## 5. Recommendations and next steps

- Hypotheses → brainstorm-features
- As-is screens for requirements → requirements-creator
- Stage evidence → cjm-research

## 6. Sources

{{#each sources}}
- {{this}}
{{/each}}
- Evidence packs listed in §1 (local, internal data — not attached)

<!-- template: research-builtin-walkthrough version: 1.1.0 -->
