---
template_id: partial-builtin-pre-mortem
schema_version: 1
name: "Pre-mortem"
artifact_type: partial
subtype: pre-mortem
scope: built-in
products: []
default_language: en
available_languages: [en]
version: "1.0.0"
author: "grow-pm"
created: 2026-10-06
updated: 2026-10-06
tags: [partial, pre-mortem, kill-criteria, opponent, judgment]
description: "Pre-mortem and kill criteria (since v3.9.0, P4 — built-in opponent), inserted by template-protocol.md T-5 step 3b at the steps references/judgment-points.md §7 lists: why this most likely failed, the early signal, and the pre-committed conditions to stop"
status: active
min_plugin_version: "3.9.0"
variables:
  - name: judged_on
    type: string
    required: false
    label: "Judged on"
    hint: "Derived by the skill, never asked: the date or milestone at which success is judged (the artifact's own target date, review date or the end of the quarter); '⚠️ TBD' when the artifact states none"
  - name: failure_causes
    type: list
    required: false
    label: "Failure causes"
    hint: "Derived by the skill, never asked: 2–3 items written '<why it failed> | <early signal> | <what we do now>', in the order of references/judgment-points.md §7 (unresolved Skeptic objections and the minority report; assumed or simulated inputs and the riskiest assumption; the artifact's risks, guardrails and base rate; the skill's own signals). Each names the specific input or section it rests on; an assumed or simulated input keeps its label; causes carry no evidence class, a cited baseline keeps its own; nothing unstated is invented"
  - name: kill_criteria
    type: list
    required: false
    label: "Kill criteria"
    hint: "Derived by the skill, never asked: items written '<observable signal> | <threshold> | <date> | <then: stop / pivot / descope / roll back>'; a threshold the artifact does not state is '⚠️ TBD'; a missing date is derived (launch or decision date plus the stated window, a plan's end) and a missing then takes the default for the kind (references/judgment-points.md §7) — only the threshold may be '⚠️ TBD'"
  - name: kill_criteria_at
    type: string
    required: false
    label: "Kill criteria already in the body"
    hint: "Derived by the skill, never asked: the heading of a section the body already has for kill criteria or a decision rule ('Kill criteria', a heading containing 'Decision rule', 'Stopping / Decision Criteria', 'Revisit trigger'); when set, only a pointer renders instead of a second table"
  - name: tbd_count
    type: string
    required: false
    label: "Open thresholds"
    hint: "Derived by the skill, never asked: how many cells of the tables in this section read '⚠️ TBD' (a pointer counts none); unset when none"
---

## Pre-mortem

<!-- P4 (references/pm-mental-model.md): the strongest case against this artifact, written as if it already failed. Derived from the artifact and its inputs — never a question, never a P2 estimate. The PM edits it at the existing review; a deletion is respected for this artifact and never learned (self-improvement.md). -->

It is {{judged_on}} and this did not work. Most likely why:

| Why it failed | Early signal | What we do now |
|---------------|--------------|----------------|
{{#each failure_causes}}
| {{this}} |
{{/each}}

{{#if kill_criteria_at}}
Kill criteria: see **{{kill_criteria_at}}**.
{{else}}
### Kill criteria

| Signal | Threshold | Date | Then |
|--------|-----------|------|------|
{{#each kill_criteria}}
| {{this}} |
{{/each}}
{{/if}}
{{#if tbd_count}}
- **Open (⚠️ TBD):** {{tbd_count}} — set them at review or before the first checkpoint.
{{/if}}
