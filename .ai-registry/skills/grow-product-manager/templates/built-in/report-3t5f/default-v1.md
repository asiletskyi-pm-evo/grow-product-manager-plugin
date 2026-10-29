---
template_id: report-3t5f-builtin-default
schema_version: 1
name: "Goal Report (3T5F)"
artifact_type: report-3t5f
subtype: null
scope: built-in
products: []
default_language: en
available_languages: [en]
version: "1.0.0"
author: "grow-pm"
created: 2026-07-14
updated: 2026-07-14
tags: [reporting, 3t5f, goals]
description: "Goal-linked 3T5F report (Target, Top Record, Top-3 Highlights, Fact, Quota Attainment, Forecast, Funnel)"
status: active
min_plugin_version: "2.0.0"
variables:
  - name: subject
    type: string
    required: true
    label: "Person or direction"
  - name: period
    type: string
    required: true
    label: "Reporting period"
  - name: target
    type: string
    required: true
    label: "Target (the SMARTCBP goal)"
  - name: top_record
    type: string
    required: false
    label: "Top Record (best result + when)"
  - name: highlights
    type: list
    required: true
    label: "Top-3 Highlights (the person's own key items)"
  - name: fact
    type: string
    required: true
    label: "Fact (actuals for the period)"
  - name: fact_qa
    type: string
    required: true
    label: "Fact Quota Attainment (% period / cumulative)"
  - name: forecast
    type: string
    required: false
    label: "Forecast"
  - name: forecast_qa
    type: string
    required: false
    label: "Forecast Quota Attainment (%)"
  - name: funnel
    type: text
    required: false
    label: "Funnel (if applicable)"
---

<!-- lang:en -->
# 3T5F Report — {{subject}} · {{period}}

1. **Target:** {{target}}
2. **Top Record:** {{#if top_record}}{{top_record}}{{else}}—{{/if}}
3. **Top-3 Highlights:**
{{#each highlights}}
   - {{this}}
{{/each}}
4. **Fact:** {{fact}}
5. **Fact Quota Attainment:** {{fact_qa}}
6. **Forecast:** {{#if forecast}}{{forecast}}{{else}}—{{/if}}
7. **Forecast Quota Attainment:** {{#if forecast_qa}}{{forecast_qa}}{{else}}—{{/if}}
8. **Funnel:** {{#if funnel}}{{funnel}}{{else}}—{{/if}}

<!-- Status emoji: ✅ on/above plan · ⚠️ −1…−5% · ❌ worse than −5% -->
<!-- /lang:en -->
