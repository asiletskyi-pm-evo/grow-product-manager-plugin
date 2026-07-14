---
template_id: goal-letter-builtin-default
schema_version: 1
name: "Goal Letter (SMARTCBP)"
artifact_type: goal-letter
subtype: null
scope: built-in
products: []
default_language: en
available_languages: [en]
version: "1.0.0"
author: "grow-pm"
created: 2026-07-14
updated: 2026-07-14
tags: [goals, smartcbp, people]
description: "SMARTCBP goal letter — for an offer or a periodic review (purpose, results, traits, culture)"
status: active
min_plugin_version: "2.0.0"
variables:
  - name: subject
    type: string
    required: true
    label: "Person or role"
  - name: period
    type: string
    required: true
    label: "Period / horizon (e.g. H2 2026, or 3/6/12 mo for an offer)"
  - name: purpose
    type: text
    required: true
    label: "Core purpose (5–6 sentences: why this role/period matters)"
  - name: goals
    type: list
    required: true
    label: "Expected results (3–5 SMARTCBP goals, one sentence each)"
  - name: traits
    type: list
    required: false
    label: "Professional traits"
  - name: culture
    type: list
    required: false
    label: "Culture points"
---

<!-- lang:en -->
# Goal Letter — {{subject}} ({{period}})

## Core purpose

{{purpose}}

## Expected results (SMARTCBP)

Each result is one sentence and passes all eight checks (S, M, A, R, T, Comparable, Brief, Public); it sits outside the performer's own process.

{{#each goals}}
1. {{this}}
{{/each}}

## Professional traits

{{#if traits}}
{{#each traits}}
- {{this}}
{{/each}}
{{else}}
- TBD
{{/if}}

## Culture

{{#if culture}}
{{#each culture}}
- {{this}}
{{/each}}
{{else}}
- TBD
{{/if}}

## Commitment (Tell and Sell)

- Committed: TBD (who committed, and how — "sold and committed" vs "just told")
<!-- /lang:en -->
