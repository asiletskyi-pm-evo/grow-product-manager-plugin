---
template_id: concept-builtin-default
schema_version: 1
name:
  uk: "Концепт продукту (за замовчуванням)"
  en: "Product Concept (default)"
artifact_type: concept
subtype: null
scope: built-in
products: []
default_language: uk
available_languages: [uk, en]
version: "1.0.0"
author: "grow-pm"
created: 2026-04-17
updated: 2026-04-17
tags: [concept, prd, default]
description:
  uk: "Стандартний шаблон концепту / PRD"
  en: "Standard concept / PRD template"
status: active
min_plugin_version: "1.9.0"
variables:
  - name: feature_name
    type: string
    required: true
    label:
      uk: "Назва фічі"
      en: "Feature name"
    hint:
      uk: "Коротке зрозуміле ім'я"
      en: "Short, clear name"
  - name: problem_statement
    type: text
    required: true
    label:
      uk: "Проблема, яку вирішуємо"
      en: "Problem we are solving"
  - name: target_audience
    type: text
    required: true
    label:
      uk: "Цільова аудиторія"
      en: "Target audience"
  - name: solution_summary
    type: text
    required: true
    label:
      uk: "Коротко про рішення"
      en: "Solution summary"
  - name: success_metrics
    type: list
    required: true
    label:
      uk: "Метрики успіху"
      en: "Success metrics"
  - name: risks
    type: list
    required: false
    label:
      uk: "Ризики та припущення"
      en: "Risks and assumptions"
  - name: related_research
    type: reference
    required: false
    label:
      uk: "Пов'язане дослідження"
      en: "Related research"
---

<!-- lang:uk -->
# {{feature_name}}

## 1. Контекст і проблема

{{problem_statement}}

## 2. Цільова аудиторія

{{target_audience}}

## 3. Рішення

{{solution_summary}}

## 4. Метрики успіху

{{#each success_metrics}}
- {{this}}
{{/each}}

## 5. Scope

### У scope
- TBD

### Поза scope
- TBD

## 6. Ризики та припущення

{{#if risks}}
{{#each risks}}
- {{this}}
{{/each}}
{{/if}}

## 7. Залежності

- TBD

## 8. Пов'язані матеріали

{{#if related_research}}
- {{related_research}}
{{/if}}

<!-- /lang:uk -->

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
