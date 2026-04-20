---
template_id: epic-builtin-default
schema_version: 1
name: "Epic (default)"
artifact_type: epic
subtype: null
scope: built-in
products: []
default_language: en
available_languages: [en]
version: "1.0.0"
author: "grow-pm"
created: 2026-04-17
updated: 2026-04-17
tags: [epic, jira, planning]
description: "Standard Epic template for Jira / Confluence"
status: active
min_plugin_version: "1.9.0"
variables:
  - name: epic_name
    type: string
    required: true
    label: "Epic name"
  - name: goal
    type: text
    required: true
    label: "Goal"
  - name: business_value
    type: text
    required: true
    label: "Business value"
  - name: success_metrics
    type: list
    required: true
    label: "Success metrics"
  - name: child_features
    type: list
    required: false
    label: "Features under this Epic"
  - name: milestones
    type: list
    required: false
    label: "Key milestones"
  - name: stakeholders
    type: list
    required: false
    label: "Stakeholders"
---

<!-- lang:en -->
# Epic: {{epic_name}}

## 1. Goal

{{goal}}

## 2. Business Value

{{business_value}}

## 3. Success Metrics

{{#each success_metrics}}
- {{this}}
{{/each}}

## 4. Scope

### In scope
- TBD

### Out of scope
- TBD

## 5. Features in this Epic

{{#if child_features}}
{{#each child_features}}
- {{this}}
{{/each}}
{{else}}
- TBD
{{/if}}

## 6. Milestones

{{#if milestones}}
{{#each milestones}}
- {{this}}
{{/each}}
{{else}}
- TBD
{{/if}}

## 7. Stakeholders

{{#if stakeholders}}
{{#each stakeholders}}
- {{this}}
{{/each}}
{{else}}
- TBD
{{/if}}

## 8. Risks & Dependencies

- TBD

## 9. Links

- Concept: TBD
- Requirements: TBD
- Research: TBD
- Design: TBD
- Analytics: TBD

<!-- /lang:en -->
