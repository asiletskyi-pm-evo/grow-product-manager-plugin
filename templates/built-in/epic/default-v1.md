---
template_id: epic-builtin-default
schema_version: 1
name:
  uk: "Epic (за замовчуванням)"
  en: "Epic (default)"
artifact_type: epic
subtype: null
scope: built-in
products: []
default_language: uk
available_languages: [uk, en]
version: "1.0.0"
author: "grow-pm"
created: 2026-04-17
updated: 2026-04-17
tags: [epic, jira, planning]
description:
  uk: "Стандартний шаблон Epic для Jira / Confluence"
  en: "Standard Epic template for Jira / Confluence"
status: active
min_plugin_version: "1.9.0"
variables:
  - name: epic_name
    type: string
    required: true
    label:
      uk: "Назва Epic"
      en: "Epic name"
  - name: goal
    type: text
    required: true
    label:
      uk: "Ціль"
      en: "Goal"
  - name: business_value
    type: text
    required: true
    label:
      uk: "Бізнес-цінність"
      en: "Business value"
  - name: success_metrics
    type: list
    required: true
    label:
      uk: "Метрики успіху"
      en: "Success metrics"
  - name: child_features
    type: list
    required: false
    label:
      uk: "Фічі / under Epic"
      en: "Features under this Epic"
  - name: milestones
    type: list
    required: false
    label:
      uk: "Ключові етапи"
      en: "Key milestones"
  - name: stakeholders
    type: list
    required: false
    label:
      uk: "Стейкхолдери"
      en: "Stakeholders"
---

<!-- lang:uk -->
# Epic: {{epic_name}}

## 1. Ціль

{{goal}}

## 2. Бізнес-цінність

{{business_value}}

## 3. Метрики успіху

{{#each success_metrics}}
- {{this}}
{{/each}}

## 4. Scope

### У scope
- TBD

### Поза scope
- TBD

## 5. Фічі / склад Epic

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

## 7. Стейкхолдери

{{#if stakeholders}}
{{#each stakeholders}}
- {{this}}
{{/each}}
{{else}}
- TBD
{{/if}}

## 8. Ризики та залежності

- TBD

## 9. Посилання

- Концепт: TBD
- Вимоги: TBD
- Дослідження: TBD
- Дизайн: TBD
- Аналітика: TBD

<!-- /lang:uk -->

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
