---
template_id: cjm-builtin-funnel
schema_version: 1
name: "CJM Report: Funnel Analysis"
artifact_type: cjm
subtype: funnel
scope: built-in
products: []
default_language: en
available_languages: [en]
version: "1.0.0"
author: "grow-pm"
created: 2026-04-17
updated: 2026-04-17
tags: [cjm, funnel, analysis]
description: "CJM report template with funnel steps, anomalies, and hypotheses"
status: active
min_plugin_version: "1.9.0"
variables:
  - name: funnel_name
    type: string
    required: true
    label: "Funnel name"
  - name: product
    type: string
    required: false
    label: "Product"
  - name: platform
    type: enum
    required: false
    options: [web, ios, android, all]
    label: "Platform"
  - name: period
    type: string
    required: true
    label: "Analysis period"
  - name: funnel_steps
    type: list
    required: true
    label: "Funnel steps (in order)"
  - name: anomalies
    type: list
    required: false
    label: "Detected anomalies"
  - name: hypotheses
    type: list
    required: false
    label: "Improvement hypotheses"
---

<!-- lang:en -->
# CJM / Funnel: {{funnel_name}}

**Period:** {{period}}
{{#if product}}**Product:** {{product}}{{/if}}
{{#if platform}}**Platform:** {{platform}}{{/if}}

## 1. Context

Funnel description, hypotheses being tested, and data sources.

## 2. Funnel Steps

{{#each funnel_steps}}
### {{@index}}. {{this}}
- Entry: TBD
- Conversion to next step: TBD %
- Benchmark: TBD %
- Δ: TBD

{{/each}}

## 3. Overall Funnel

| Step | Users | Step→Step conversion | Overall conversion |
|------|-------|----------------------|--------------------|
{{#each funnel_steps}}
| {{this}} | TBD | TBD % | TBD % |
{{/each}}

## 4. Anomalies

{{#if anomalies}}
{{#each anomalies}}
### {{this}}

- Step: TBD
- Metric: TBD
- Deviation: TBD
- Potential cause: TBD

{{/each}}
{{else}}
TBD.
{{/if}}

## 5. Comparison vs benchmarks / knowledge sources

- TBD (from knowledge library / CJM protocol)

## 6. Improvement Hypotheses

{{#if hypotheses}}
{{#each hypotheses}}
- {{this}}
{{/each}}
{{else}}
- TBD
{{/if}}

## 7. Prioritization (ICE)

| Hypothesis | Impact | Confidence | Ease | Score |
|------------|--------|------------|------|-------|
{{#if hypotheses}}
{{#each hypotheses}}
| {{this}} | TBD | TBD | TBD | TBD |
{{/each}}
{{/if}}

## 8. Recommendations

- TBD

## 9. Next Steps

- TBD

<!-- /lang:en -->
