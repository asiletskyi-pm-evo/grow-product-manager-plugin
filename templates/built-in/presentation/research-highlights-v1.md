---
template_id: presentation-builtin-research-highlights
schema_version: 1
name: "Research Highlights"
artifact_type: presentation
subtype: research-highlights
scope: built-in
products: []
default_language: en
available_languages: [en]
version: "1.0.0"
author: "grow-pm"
created: 2026-04-20
updated: 2026-04-20
tags: [presentation, research, user-research, insights]
description: "User research / UX benchmark / market research dump (10 slides): themes → quotes → quantitative findings → recommendations"
status: active
min_plugin_version: "1.10.0"
variables:
  - name: research_title
    type: string
    required: true
    label: "Research title"
  - name: research_type
    type: string
    required: true
    label: "Research type (user / UX benchmark / market)"
  - name: research_period
    type: string
    required: true
    label: "Research period"
  - name: presenter
    type: string
    required: false
    label: "Presenter"
  - name: audience
    type: string
    required: false
    label: "Audience"
  - name: exec_summary
    type: text
    required: true
    label:
      uk: "Executive summary (3-5 bullets)"
      en: "Executive summary (3-5 bullets)"
  - name: method
    type: text
    required: true
    label:
      en: "Method"
  - name: sample
    type: string
    required: true
    label: "Sample (N + segments)"
  - name: sources
    type: list
    required: false
    label: "Sources"
  - name: themes
    type: list
    required: true
    label: "Themes / insights (2-3)"
  - name: quotes
    type: list
    required: false
    label: "User quotes (one per theme)"
  - name: quantitative_findings
    type: list
    required: false
    label: "Quantitative findings (2-3 numbers)"
  - name: recommendations
    type: list
    required: true
    label: "Recommendations (1-3, ranked)"
---

<!-- lang:en -->
# Research: {{research_title}}

{{#if presenter}}**Presenter:** {{presenter}}{{/if}}
{{#if audience}}**Audience:** {{audience}}{{/if}}

**Type:** {{research_type}} · **Period:** {{research_period}}

---

## Slide 1. Title

- {{research_title}}
- Subtitle: {{research_type}} · {{research_period}}
- Presenter, date

## Slide 2. Executive summary

{{exec_summary}}

## Slide 3. Method & sample

- **Method:** {{method}}
- **Sample:** {{sample}}
- **Period:** {{research_period}}
{{#if sources}}
- **Sources:**
{{#each sources}}
  - {{this}}
{{/each}}
{{/if}}

## Slide 4. Theme 1

{{#if themes.[0]}}
### {{themes.[0].title}}

{{themes.[0].insight}}
{{else}}
- Theme 1: title
- Key insight
{{/if}}

## Slide 5. User quote (theme 1)

{{#if quotes.[0]}}
> "{{quotes.[0].text}}"
>
> — {{quotes.[0].attribution}}
{{else}}
> "Direct quote from interview / survey"
>
> — Segment, role
{{/if}}

## Slide 6. Theme 2

{{#if themes.[1]}}
### {{themes.[1].title}}

{{themes.[1].insight}}
{{else}}
- Theme 2: title
- Key insight
{{/if}}

## Slide 7. User quote (theme 2)

{{#if quotes.[1]}}
> "{{quotes.[1].text}}"
>
> — {{quotes.[1].attribution}}
{{else}}
> "Direct quote from interview / survey"
>
> — Segment, role
{{/if}}

## Slide 8. Theme 3 (if applicable)

{{#if themes.[2]}}
### {{themes.[2].title}}

{{themes.[2].insight}}
{{else}}
_(optional — skip if only 2 themes)_
{{/if}}

## Slide 9. Quantitative findings

{{#if quantitative_findings}}
{{#each quantitative_findings}}
- {{this}}
{{/each}}
{{else}}
- Metric 1: value + context
- Metric 2: value + context
- Metric 3 (optional)
{{/if}}

## Slide 10. Recommendations / next steps

{{#each recommendations}}
{{@index}}. {{this}}
{{/each}}

**Owner:** _(assign)_ · **When:** _(date)_

---

## Appendix: speaker notes

For each slide — 3-5 sentences to say out loud. For quotes — context (when said, what prompted it).

<!-- /lang:en -->
