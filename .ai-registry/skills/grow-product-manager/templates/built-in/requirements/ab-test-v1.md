---
template_id: requirements-builtin-ab-test
schema_version: 1
name: "A/B Test Requirements"
artifact_type: requirements
subtype: ab-test
scope: built-in
products: []
default_language: en
available_languages: [en]
version: "1.0.0"
author: "grow-pm"
created: 2026-04-17
updated: 2026-04-17
tags: [requirements, ab-test, experiment, growth]
description: "A/B experiment requirements — hypothesis, variants, metrics, stopping criteria"
status: active
min_plugin_version: "1.9.0"
variables:
  - name: experiment_name
    type: string
    required: true
    label: "Experiment name"
  - name: hypothesis
    type: text
    required: true
    label: "Hypothesis"
    hint: "If <change>, then <metric> will change by <amount>, because <reason>"
  - name: primary_metric
    type: string
    required: true
    label: "Primary metric"
  - name: secondary_metrics
    type: list
    required: false
    label: "Secondary metrics"
  - name: guardrail_metrics
    type: list
    required: false
    label: "Guardrail metrics"
  - name: audience
    type: text
    required: true
    label: "Audience / segmentation"
  - name: control_description
    type: text
    required: true
    label: "Control description (A)"
  - name: variant_description
    type: text
    required: true
    label: "Variant description (B)"
  - name: split_ratio
    type: string
    required: false
    label: "Traffic split"
    default: "50/50"
  - name: mde
    type: string
    required: false
    label: "MDE (minimum detectable effect)"
  - name: duration_estimate
    type: string
    required: false
    label: "Estimated duration"
  - name: stopping_criteria
    type: list
    required: true
    label: "Stopping / decision criteria"
---

<!-- lang:en -->
# A/B Test: {{experiment_name}}

## 1. Hypothesis

{{hypothesis}}

## 2. Audience

{{audience}}

## 3. Variants

### Control (A)
{{control_description}}

### Variant (B)
{{variant_description}}

**Traffic split:** {{split_ratio}}

## 4. Metrics

### Primary
- **{{primary_metric}}**

### Secondary
{{#if secondary_metrics}}
{{#each secondary_metrics}}
- {{this}}
{{/each}}
{{else}}
- TBD
{{/if}}

### Guardrails
{{#if guardrail_metrics}}
{{#each guardrail_metrics}}
- {{this}}
{{/each}}
{{else}}
- TBD
{{/if}}

## 5. Experiment Parameters

- **MDE:** {{#if mde}}{{mde}}{{else}}TBD{{/if}}
- **Estimated duration:** {{#if duration_estimate}}{{duration_estimate}}{{else}}TBD{{/if}}
- **Significance level:** 95%
- **Power:** 80%

## 6. Stopping / Decision Criteria

{{#each stopping_criteria}}
- {{this}}
{{/each}}

## 7. Analytics / Tracking

- Events: TBD
- Dashboard: TBD
- Segments to analyze: TBD

## 8. Risks

- TBD

## 9. Post-experiment Plan

- If B wins: TBD
- If A wins or tie: TBD
- If guardrails are breached: TBD

<!-- /lang:en -->
