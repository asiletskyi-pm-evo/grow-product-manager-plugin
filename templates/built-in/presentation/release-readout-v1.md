---
template_id: presentation-builtin-release-readout
schema_version: 1
name: "Release / Sprint Readout"
artifact_type: presentation
subtype: release-readout
scope: built-in
products: []
default_language: en
available_languages: [en]
version: "1.0.0"
author: "grow-pm"
created: 2026-04-20
updated: 2026-04-20
tags: [presentation, release, sprint, readout]
description: "Release or sprint readout (7 slides): scope → metrics → wins/learnings → incidents → what's next → ask"
status: active
min_plugin_version: "1.10.0"
variables:
  - name: release_name
    type: string
    required: true
    label: "Release / sprint name (e.g., v4.2 or Sprint 23)"
  - name: date_range
    type: string
    required: true
    label: "Date range (start → end)"
  - name: presenter
    type: string
    required: false
    label: "Presenter"
  - name: audience
    type: string
    required: false
    label: "Audience"
  - name: scope_shipped
    type: list
    required: true
    label: "What shipped (features / tickets)"
  - name: key_metrics
    type: list
    required: true
    label: "Key metrics (3: baseline → current → delta)"
  - name: wins
    type: list
    required: true
    label: "Wins"
  - name: learnings
    type: list
    required: true
    label: "Learnings"
  - name: incidents
    type: list
    required: false
    label: "Incidents / issues + resolution"
  - name: whats_next
    type: list
    required: true
    label: "What's next (next sprint)"
  - name: ask
    type: text
    required: false
    label: "Ask / risks"
  - name: owner
    type: string
    required: false
    label: "Owner"
---

<!-- lang:en -->
# Release: {{release_name}}

{{#if presenter}}**Presenter:** {{presenter}}{{/if}}
{{#if audience}}**Audience:** {{audience}}{{/if}}

**Period:** {{date_range}}

---

## Slide 1. Title

- {{release_name}}
- Subtitle: {{date_range}}
- Presenter, date

## Slide 2. Scope shipped

{{#each scope_shipped}}
- {{this}}
{{/each}}

_(Optional media: thumbs grid with screenshots of shipped features.)_

## Slide 3. Key metrics impact

{{#each key_metrics}}
- {{this}}
{{/each}}

_(3 tile cards: baseline → current → delta. Caption: source dashboard.)_

## Slide 4. Wins & Learnings

**Wins:**

{{#each wins}}
- {{this}}
{{/each}}

**Learnings:**

{{#each learnings}}
- {{this}}
{{/each}}

## Slide 5. Incidents / issues

{{#if incidents}}
{{#each incidents}}
- {{this}}
{{/each}}
{{else}}
_No incidents this period._
{{/if}}

## Slide 6. What's next

{{#each whats_next}}
- {{this}}
{{/each}}

## Slide 7. Ask / risks

{{#if ask}}
{{ask}}
{{else}}
- What's needed from the team / stakeholders?
- Next sprint risks
{{/if}}

{{#if owner}}**Owner:** {{owner}}{{/if}}

---

## Appendix: speaker notes

For each slide — 3-5 sentences. For Slide 3 — always show source dashboard. For Slide 5 — be honest (don't hide incidents).

<!-- /lang:en -->
