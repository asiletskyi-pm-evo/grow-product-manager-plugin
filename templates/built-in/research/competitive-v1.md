---
template_id: research-builtin-competitive
schema_version: 1
name: "Competitive Analysis"
artifact_type: research
subtype: competitive
scope: built-in
products: []
default_language: en
available_languages: [en]
version: "1.0.0"
author: "grow-pm"
created: 2026-04-17
updated: 2026-04-17
tags: [research, competitive, market]
description: "Competitive analysis template: players, SWOT, positioning, takeaways"
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
  - name: competitors
    type: list
    required: true
    label: "List of competitors"
  - name: our_product
    type: string
    required: false
    label: "Our product (for comparison)"
  - name: comparison_dimensions
    type: list
    required: false
    label: "Comparison dimensions"
  - name: sources
    type: list
    required: false
    label: "Data sources"
---

<!-- lang:en -->
# Competitive Analysis: {{research_topic}}

## 1. Research Goal

{{research_question}}

## 2. Methodology

- Approach: desk research + expert judgment
- Period: TBD
{{#if sources}}
- Sources:
{{#each sources}}
  - {{this}}
{{/each}}
{{/if}}

## 3. Market Players

{{#each competitors}}
- {{this}}
{{/each}}

## 4. Comparison Table

{{#if comparison_dimensions}}
| Dimension | {{#if our_product}}{{our_product}}{{else}}Us{{/if}} | {{#each competitors}}{{this}} | {{/each}}
|-----------|------|{{#each competitors}}------|{{/each}}
{{#each comparison_dimensions}}
| {{this}} | TBD | {{#each ../competitors}}TBD | {{/each}}
{{/each}}
{{else}}
TBD — fill in comparison dimensions.
{{/if}}

## 5. SWOT (per competitor)

{{#each competitors}}
### {{this}}

- **Strengths:** TBD
- **Weaknesses:** TBD
- **Opportunities:** TBD
- **Threats:** TBD

{{/each}}

## 6. Positioning

Positioning map description (X / Y axes) with each competitor placed.

## 7. Key Takeaways

- TBD

## 8. Recommendations

### What to copy
- TBD

### What to avoid
- TBD

### Where to differentiate
- TBD

## 9. Open Questions

- TBD

<!-- /lang:en -->
