---
template_id: research-builtin-user-research
schema_version: 1
name: "User Research"
artifact_type: research
subtype: user-research
scope: built-in
products: []
default_language: en
available_languages: [en]
version: "1.0.0"
author: "grow-pm"
created: 2026-04-17
updated: 2026-04-17
tags: [research, user-research, interviews, insights]
description: "User research report template (interviews / surveys)"
status: active
min_plugin_version: "1.9.0"
variables:
  - name: research_topic
    type: string
    required: true
    label: "Research topic"
  - name: research_question
    type: text
    required: true
    label: "Research question"
  - name: method
    type: enum
    required: true
    options: [interviews, survey, diary-study, usability-test, mixed]
    label: "Method"
  - name: participants_count
    type: number
    required: false
    label: "Number of participants"
  - name: segments
    type: list
    required: false
    label: "Participant segments"
  - name: key_findings
    type: list
    required: true
    label: "Key findings"
  - name: themes
    type: list
    required: false
    label: "Themes / patterns"
  - name: recommendations
    type: list
    required: false
    label: "Recommendations"
---

<!-- lang:en -->
# User Research: {{research_topic}}

## 1. Research Question

{{research_question}}

## 2. Methodology

- **Method:** {{method}}
- **Participants:** {{#if participants_count}}{{participants_count}}{{else}}TBD{{/if}}
{{#if segments}}
- **Segments:**
{{#each segments}}
  - {{this}}
{{/each}}
{{/if}}
- **Period:** TBD

## 3. Protocol

- Script / guide: TBD
- Tools: TBD
- Analysis: thematic coding / affinity mapping

## 4. Key Findings

{{#each key_findings}}
- {{this}}
{{/each}}

## 5. Themes & Patterns

{{#if themes}}
{{#each themes}}
### {{this}}

- Evidence: TBD
- Quotes: TBD
- Frequency: TBD

{{/each}}
{{else}}
TBD.
{{/if}}

## 6. Pains & Needs

### Pains
- TBD

### Needs
- TBD

### Jobs that are met
- TBD

## 7. Quotes

> "TBD" — Participant #X

## 8. Recommendations

{{#if recommendations}}
{{#each recommendations}}
- {{this}}
{{/each}}
{{else}}
- TBD
{{/if}}

## 9. Research Limitations

- TBD

## 10. Next Steps

- TBD

<!-- /lang:en -->
