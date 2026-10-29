---
template_id: followup-arcv-builtin-default
schema_version: 1
name: "ARCV Follow-up"
artifact_type: followup-arcv
subtype: null
scope: built-in
products: []
default_language: en
available_languages: [en]
version: "1.0.0"
author: "grow-pm"
created: 2026-07-14
updated: 2026-07-14
tags: [follow-up, arcv, meetings]
description: "Actionable follow-up (ARCV): numbered actions with one responsible each + a separate Decisions block"
status: active
min_plugin_version: "2.0.0"
variables:
  - name: meeting
    type: string
    required: true
    label: "Meeting / topic"
  - name: date
    type: date
    required: true
    label: "Date"
  - name: actions
    type: list
    required: true
    label: "Actions (verb + one responsible + deadline)"
  - name: decisions
    type: list
    required: false
    label: "Decisions (agreements with no owner/action)"
---

<!-- lang:en -->
# Follow-up — {{meeting}} · {{date}}

## Actions
<!-- ARCV: each numbered; one Responsible each; active perfective verb + deadline; Clearly (a stranger could execute it). -->
{{#each actions}}
1. {{this}}
{{/each}}

## Decisions
{{#if decisions}}
{{#each decisions}}
- {{this}}
{{/each}}
{{else}}
- None
{{/if}}
<!-- /lang:en -->
