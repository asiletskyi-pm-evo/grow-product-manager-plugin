---
template_id: research-builtin-insight-report
schema_version: 1
name: "Insight Report"
artifact_type: research
subtype: insight-report
scope: built-in
products: []
match: subtype
default_language: en
available_languages: [en]
version: "1.0.0"
author: "grow-pm"
created: 2026-09-29
updated: 2026-09-29
tags: [research, insight-report, synthesis, insights]
description: "Research synthesis by insight (since v3.6.0): evidence count, n of real users, method, confidence, verbatim quotes with source, human-validated flag, implications and open questions"
status: active
min_plugin_version: "3.6.0"
variables:
  - name: research_topic
    type: string
    required: true
    label: "Study topic"
  - name: research_question
    type: text
    required: false
    label: "Research question"
  - name: method
    type: enum
    required: false
    options: [interviews, usability-test, survey, diary-study, mixed]
    label: "Method"
  - name: participants_count
    type: number
    required: false
    label: "Real users (n)"
---

<!-- lang:en -->
# Insight Report: {{research_topic}}

## 1. Study

<!-- n counts real users only. Simulated or synthetic input is named on its own line and supports hypotheses, never insights. -->
- **Research question:** {{#if research_question}}{{research_question}}{{else}}TBD{{/if}}
- **Method:** {{#if method}}{{method}}{{else}}TBD{{/if}} · **Real users (n):** {{#if participants_count}}{{participants_count}}{{else}}TBD{{/if}} · **Period:** TBD
- **Simulated input:** none

## 2. Insights

<!-- Repeat the block per insight. An insight is a finding plus why it matters; a quote alone is not an insight.
Confidence: high = consistent across participants and confirmed by a second, independent source type; medium = consistent within one source type; low = few participants or mixed signals.
Quotes stay verbatim in the participant's own words and language; the source is the participant id, session date and method.
Human-validated: yes only after a researcher checked the insight against the raw sessions; model-synthesised insights start at no. -->

### Insight 1: TBD

- **Evidence count:** TBD · **Real users (n):** TBD · **Method:** TBD
- **Confidence:** TBD (high · medium · low) · **Human-validated:** no
- **Quotes (verbatim, with source):**
  > "TBD" — P1, session date, method
- **Implication:** TBD

## 3. Implications

<!-- What changes for the product, design or roadmap — each tied to the insights above. A direction, not a solution spec. -->
- TBD

## 4. Open questions

<!-- What this study could not answer; candidates for the next study. -->
- TBD

## 5. Limitations and sources

<!-- Sample and recruiting bias, method limits. Raw sessions and transcripts stay local — link them, never attach them. -->
- TBD

<!-- /lang:en -->
