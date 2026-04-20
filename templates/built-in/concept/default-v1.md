---
template_id: concept-builtin-default
schema_version: 1
name: "Product Concept (default)"
artifact_type: concept
subtype: null
scope: built-in
products: []
default_language: en
available_languages: [en]
version: "1.0.0"
author: "grow-pm"
created: 2026-04-17
updated: 2026-04-17
tags: [concept, prd, default]
description: "Standard concept / PRD template"
status: active
min_plugin_version: "1.9.0"
variables:
  - name: feature_name
    type: string
    required: true
    label:
      en: "Feature name"
    hint:
      en: "Short, clear name"
  - name: problem_statement
    type: text
    required: true
    label: "Problem we are solving"
  - name: target_audience
    type: text
    required: true
    label: "Target audience"
  - name: solution_summary
    type: text
    required: true
    label: "Solution summary"
  - name: success_metrics
    type: list
    required: true
    label: "Success metrics"
  - name: risks
    type: list
    required: false
    label: "Risks and assumptions"
  - name: related_research
    type: reference
    required: false
    label: "Related research"
---

<!-- lang:en -->
# {{feature_name}}

## 1. Context & Problem

{{problem_statement}}

## 2. Target Audience

{{target_audience}}

## 3. Solution

{{solution_summary}}

## 4. Success Metrics

{{#each success_metrics}}
- {{this}}
{{/each}}

## 5. Scope

### In scope
- TBD

### Out of scope
- TBD

## 6. Risks & Assumptions

{{#if risks}}
{{#each risks}}
- {{this}}
{{/each}}
{{/if}}

## 7. Dependencies

- TBD

## 8. Related Materials

{{#if related_research}}
- {{related_research}}
{{/if}}

<!-- /lang:en -->
