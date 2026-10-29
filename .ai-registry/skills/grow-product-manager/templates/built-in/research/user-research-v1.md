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
version: "1.1.0"
author: "grow-pm"
created: 2026-04-17
updated: 2026-10-06
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
    label: "Number of participants (real users only)"
  - name: simulated_input
    type: text
    required: false
    label: "Simulated input — hypotheses only"
    hint: "Derived by product-research 1.5.g (or the rendering skill's own Gate Check 6 step; data-integrity-protocol.md 6b), never asked: what the simulated input is and how many items — persona answers, simulated interviews, model-written 'user' answers — and the study that would check it; unset when there is none, and then no line renders"
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

<!-- n counts real users only. Persona answers, simulated interviews and model-written "user" answers are `simulated` (pm-mental-model.md §4): never counted in n, never a finding, theme, pain, need or quote — they appear only on the Simulated input line, which renders only when such input exists. -->
- **Method:** {{method}}
- **Participants (n = real users only):** {{#if participants_count}}{{participants_count}}{{else}}TBD{{/if}}
{{#if segments}}
- **Segments:**
{{#each segments}}
  - {{this}}
{{/each}}
{{/if}}
- **Period:** TBD
{{#if simulated_input}}
- **Simulated input — hypotheses only** (`simulated`): {{simulated_input}}
{{/if}}

## 3. Protocol

- Script / guide: TBD
- Tools: TBD
- Analysis: thematic coding / affinity mapping

## 4. Key Findings

<!-- Findings, themes, pains, needs and quotes (§4–§7) rest on real users only. Each carries its evidence class first in its annotation (pm-mental-model.md §4); a synthesis keeps the class of what it synthesises — `reported` for interviews and surveys, `observed` for usability sessions — and one label may cover a section when every claim in it shares class and source. `assumed` appears only labelled `[assumed — …]`; `simulated` never appears here. A finding about why users act or what they need with no real-user source keeps only its supportable part plus one hand-back line (data-integrity-protocol.md Gate Check 6c). -->
{{#each key_findings}}
- {{this}}
{{/each}}

## 5. Themes & Patterns

{{#if themes}}
<!-- Per theme: Evidence = class — source (e.g. `reported — interviews P1, P3, P5`); Quotes = verbatim, ending `· reported`; Frequency = X of n real users. -->
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

<!-- Verbatim only, with who and when, ending `· reported` — masking [name], a marked […] and a marked (translated) with the original kept still count as verbatim; a paraphrase loses its quote marks; a persona or model-written answer is never a quote. -->
> "TBD" — Participant #X, session date · reported

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
