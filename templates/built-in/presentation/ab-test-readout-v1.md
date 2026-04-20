---
template_id: presentation-builtin-ab-test-readout
schema_version: 1
name: "A/B Test Readout"
artifact_type: presentation
subtype: ab-test-readout
scope: built-in
products: []
default_language: en
available_languages: [en]
version: "1.0.0"
author: "grow-pm"
created: 2026-04-20
updated: 2026-04-20
tags: [presentation, ab-test, experiment, readout]
description: "A/B test readout (6 slides): hypothesis → primary metric → guardrails → interpretation → decision"
status: active
min_plugin_version: "1.10.0"
variables:
  - name: test_name
    type: string
    required: true
    label: "Test name"
  - name: date_range
    type: string
    required: true
    label: "Test date range (start → end)"
  - name: platform
    type: string
    required: true
    label: "Platform (Web / iOS / Android / All)"
  - name: segment
    type: string
    required: false
    label: "Segment (all / new users / logged-in / geo / etc.)"
  - name: presenter
    type: string
    required: false
    label: "Presenter"
  - name: hypothesis
    type: text
    required: true
    label: "Hypothesis (If … then … because …)"
  - name: success_metric
    type: string
    required: true
    label: "Primary success metric"
  - name: traffic_split
    type: string
    required: true
    label: "Traffic split (e.g., 50/50)"
  - name: sample_size
    type: string
    required: true
    label: "Sample size (N per arm)"
  - name: primary_result
    type: text
    required: true
    label: "Primary result (control → treatment, delta, CI, p-value)"
  - name: guardrails_results
    type: list
    required: false
    label: "Guardrails / secondary metrics (one row per metric)"
  - name: interpretation
    type: text
    required: true
    label: "Interpretation (observations, segments, surprises)"
  - name: decision
    type: string
    required: true
    label: "Decision (Ship / Kill / Iterate)"
  - name: rollout_plan
    type: text
    required: false
    label: "Rollout / next-steps plan"
  - name: owner
    type: string
    required: false
    label: "Owner"
---

<!-- lang:en -->
# A/B Test: {{test_name}}

{{#if presenter}}**Presenter:** {{presenter}}{{/if}}

**Period:** {{date_range}} · **Platform:** {{platform}}{{#if segment}} · **Segment:** {{segment}}{{/if}}

---

## Slide 1. Title

- {{test_name}}
- Subtitle: {{date_range}} · {{platform}}{{#if segment}} · {{segment}}{{/if}}
- Presenter, date

## Slide 2. Hypothesis & setup

**Hypothesis:**
{{hypothesis}}

**Setup:**

- **Primary metric:** {{success_metric}}
- **Traffic split:** {{traffic_split}}
- **Sample size:** {{sample_size}} per arm
- **Duration:** {{date_range}}

## Slide 3. Primary metric: {{success_metric}}

{{primary_result}}

_(Chart: bar — control vs treatment with CI. Caption: p-value, CI.)_

## Slide 4. Secondary / guardrails

{{#if guardrails_results}}
{{#each guardrails_results}}
- {{this}}
{{/each}}
{{else}}
- Guardrail 1: control → treatment, delta
- Guardrail 2: control → treatment, delta
- Secondary 1: control → treatment, delta
{{/if}}

_(Chart: multi-bar with several metrics.)_

## Slide 5. Interpretation

{{interpretation}}

## Slide 6. Decision & rollout

**Decision:** {{decision}}

{{#if rollout_plan}}
**Plan:**
{{rollout_plan}}
{{else}}
- Next step
- Timeline
- Blockers / risks
{{/if}}

{{#if owner}}**Owner:** {{owner}}{{/if}}

---

## Appendix: speaker notes

For each slide — 3-5 sentences. For Slide 3 — always mention statistical significance AND business significance separately.

<!-- /lang:en -->
