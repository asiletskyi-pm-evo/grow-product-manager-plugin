---
template_id: performance-review-builtin-default
schema_version: 1
name: "Performance Review"
artifact_type: performance-review
subtype: null
scope: built-in
products: []
default_language: en
available_languages: [en]
version: "1.0.0"
author: "grow-pm"
created: 2026-07-14
updated: 2026-07-14
tags: [performance-review, people]
description: "Performance review — past-period feedback + a 6–12-month plan. Employers register their own variant via plugin-configurator."
status: active
min_plugin_version: "2.0.0"
variables:
  - name: person
    type: string
    required: true
    label: "Person"
  - name: period
    type: string
    required: true
    label: "Period (MM.YYYY)"
  - name: feedback_items
    type: list
    required: true
    label: "Past-period achievements & feedback (~6 items, NVC — facts not traits)"
  - name: plan_items
    type: list
    required: true
    label: "Plan items for the next 6–12 months (each phrased as a SMARTCBP goal)"
  - name: recommendation
    type: enum
    required: true
    options: [development, style-change, yellow-card, promotion]
    label: "Action recommendation"
---

<!-- lang:en -->
# Performance Review — {{person}} · {{period}}

> Strictly local/vault. Feedback describes the work (facts, NVC), not the person's worth.

## 1. Past-period feedback

| # | Achievement / growth area | Feedback |
|---|---------------------------|----------|
{{#each feedback_items}}
| | {{this}} | |
{{/each}}

## 2. Plan for the next 6–12 months

| # | Item (SMARTCBP goal) | Feedback on results |
|---|----------------------|---------------------|
{{#each plan_items}}
| | {{this}} | |
{{/each}}

<!-- The "Feedback on results" column is filled at the next review. -->

## Recommendation
**{{recommendation}}** — grounded in the evidence (goal attainment / Forecast QA, GTD-index trend, D-type movement).
<!-- /lang:en -->
