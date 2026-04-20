---
template_id: presentation-builtin-feature
schema_version: 1
name: "Feature Presentation"
artifact_type: presentation
subtype: feature
scope: built-in
products: []
default_language: en
available_languages: [en]
version: "1.0.0"
author: "grow-pm"
created: 2026-04-17
updated: 2026-04-17
tags: [presentation, feature, pitch]
description: "Feature presentation to stakeholders (10 slides) as a text outline"
status: active
min_plugin_version: "1.9.0"
variables:
  - name: feature_name
    type: string
    required: true
    label:
      en: "Feature name"
  - name: presenter
    type: string
    required: false
    label: "Presenter"
  - name: audience
    type: string
    required: false
    label: "Audience"
  - name: problem_statement
    type: text
    required: true
    label: "Problem"
  - name: solution_summary
    type: text
    required: true
    label: "Solution"
  - name: key_metrics
    type: list
    required: true
    label: "Key metrics / KPIs"
  - name: ask
    type: text
    required: false
    label: "Ask for stakeholders"
---

<!-- lang:en -->
# Presentation: {{feature_name}}

{{#if presenter}}**Presenter:** {{presenter}}{{/if}}
{{#if audience}}**Audience:** {{audience}}{{/if}}

---

## Slide 1. Title

- {{feature_name}}
- Subtitle: one-liner
- Presenter, date

## Slide 2. Context

- Where are we now?
- Why now?

## Slide 3. Problem

{{problem_statement}}

## Slide 4. Users / segments

- Who is affected?
- How many?
- What do they say?

## Slide 5. Data / Evidence

- Key numbers that confirm the problem
- Research / feedback

## Slide 6. Solution

{{solution_summary}}

## Slide 7. What it looks like (visual)

- Screenshot / mockup / flow
- Key UX changes

## Slide 8. Success Metrics

{{#each key_metrics}}
- {{this}}
{{/each}}

## Slide 9. Plan / Timeline

- Phases, dates, teams
- Dependencies, risks

## Slide 10. Ask

{{#if ask}}
{{ask}}
{{else}}
- What's needed from the team / stakeholders?
{{/if}}

---

## Appendix: speaker notes

For each slide — 3-5 sentences to say out loud.

<!-- /lang:en -->
