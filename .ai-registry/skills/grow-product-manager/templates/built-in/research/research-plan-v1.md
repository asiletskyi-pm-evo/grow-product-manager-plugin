---
template_id: research-builtin-research-plan
schema_version: 1
name: "Research Plan"
artifact_type: research
subtype: research-plan
scope: built-in
products: []
match: subtype
default_language: en
available_languages: [en]
version: "1.0.0"
author: "grow-pm"
created: 2026-09-29
updated: 2026-09-29
tags: [research, research-plan, study, discovery]
description: "Study plan before fieldwork (since v3.6.0): the decision it informs, research question, method, participants and recruiting criteria, n, timeline, discussion-guide link, confidence label and human-validated flag"
status: active
min_plugin_version: "3.6.0"
variables:
  - name: research_topic
    type: string
    required: true
    label: "Study topic"
  - name: decision
    type: text
    required: true
    label: "Decision this study informs"
  - name: research_question
    type: text
    required: false
    label: "Research question"
  - name: method
    type: enum
    required: false
    options: [interviews, usability-test, survey, diary-study, mixed]
    label: "Method"
---

<!-- lang:en -->
# Research Plan: {{research_topic}}

## 1. Decision and question

<!-- One decision, one primary question. Drop any question whose answer would not change the decision. -->
- **Decision this study informs:** {{decision}}
- **Research question:** {{#if research_question}}{{research_question}}{{else}}TBD{{/if}}
- **Assumptions to test:** TBD

## 2. Method

<!-- Behaviour → usability test or diary study; motivation and jobs → interviews; prevalence → survey. Simulated participants may rehearse the guide; they never count toward n. -->
- **Method:** {{#if method}}{{method}}{{else}}TBD (interviews · usability-test · survey · diary-study · mixed){{/if}}
- **Why this method:** TBD

## 3. Participants and recruiting

<!-- Participants appear as ids (P1, P2 …) in every output; names and contacts stay in the recruiting tool. -->
- **Recruiting criteria, exclusions, screener and channel:** TBD
- **Planned n (real users):** TBD

## 4. Timeline and materials

| Phase | Dates | Owner |
|-------|-------|-------|
| Recruiting | TBD | TBD |
| Sessions | TBD | TBD |
| Synthesis and readout | TBD | TBD |

- **Discussion guide:** TBD (research/discussion-guide)
- **Consent and recording:** TBD

## 5. Confidence and validation

<!-- Expected confidence = what this method and n can support; high only when a second, independent source type (analytics, tickets, another method) is planned. Human-validated turns to yes only after a researcher has reviewed this plan. -->
- **Expected confidence:** TBD (high · medium · low)
- **Human-validated:** no

## 6. Risks and limitations

- TBD

<!-- /lang:en -->
