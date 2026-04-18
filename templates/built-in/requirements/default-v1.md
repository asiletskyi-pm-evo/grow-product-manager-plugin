---
template_id: requirements-builtin-default
schema_version: 1
name:
  uk: "Вимоги до фічі (за замовчуванням)"
  en: "Feature Requirements (default)"
artifact_type: requirements
subtype: null
scope: built-in
products: []
default_language: uk
available_languages: [uk, en]
version: "1.0.0"
author: "grow-pm"
created: 2026-04-17
updated: 2026-04-17
tags: [requirements, default]
description:
  uk: "Стандартний шаблон вимог до фічі (BA-структура)"
  en: "Standard feature requirements template (BA structure)"
status: active
min_plugin_version: "1.9.0"
variables:
  - name: feature_name
    type: string
    required: true
    label:
      uk: "Назва фічі"
      en: "Feature name"
  - name: related_concept
    type: reference
    required: false
    label:
      uk: "Пов'язаний концепт"
      en: "Related concept"
  - name: user_stories
    type: list
    required: true
    label:
      uk: "User stories"
      en: "User stories"
    hint:
      uk: "Як <роль>, я хочу <дію>, щоб <цінність>"
      en: "As a <role>, I want <action>, so that <value>"
  - name: acceptance_criteria
    type: list
    required: true
    label:
      uk: "Критерії прийняття"
      en: "Acceptance criteria"
    hint:
      uk: "Формат: Given / When / Then"
      en: "Given / When / Then format"
  - name: out_of_scope
    type: list
    required: false
    label:
      uk: "Поза scope"
      en: "Out of scope"
  - name: success_metrics
    type: list
    required: true
    label:
      uk: "Метрики успіху"
      en: "Success metrics"
  - name: platforms
    type: list
    required: false
    label:
      uk: "Платформи"
      en: "Platforms"
---

<!-- lang:uk -->
# Вимоги: {{feature_name}}

{{#if related_concept}}
**Пов'язаний концепт:** {{related_concept}}
{{/if}}

## 1. Огляд

Коротко про фічу.

## 2. User Stories

{{#each user_stories}}
- {{this}}
{{/each}}

## 3. Функціональні вимоги

### 3.1. Основний сценарій
- TBD

### 3.2. Альтернативні сценарії
- TBD

### 3.3. Edge cases
- TBD

## 4. Нефункціональні вимоги

- Продуктивність: TBD
- Безпека: TBD
- Аналітика: TBD

## 5. Критерії прийняття

{{#each acceptance_criteria}}
- {{this}}
{{/each}}

## 6. Scope

### У scope
- TBD

### Поза scope
{{#if out_of_scope}}
{{#each out_of_scope}}
- {{this}}
{{/each}}
{{/if}}

## 7. Метрики успіху

{{#each success_metrics}}
- {{this}}
{{/each}}

## 8. Платформи

{{#if platforms}}
{{#each platforms}}
- {{this}}
{{/each}}
{{else}}
- TBD
{{/if}}

## 9. Відкриті питання

- TBD

<!-- /lang:uk -->

<!-- lang:en -->
# Requirements: {{feature_name}}

{{#if related_concept}}
**Related concept:** {{related_concept}}
{{/if}}

## 1. Overview

Brief description of the feature.

## 2. User Stories

{{#each user_stories}}
- {{this}}
{{/each}}

## 3. Functional Requirements

### 3.1. Main scenario
- TBD

### 3.2. Alternative scenarios
- TBD

### 3.3. Edge cases
- TBD

## 4. Non-Functional Requirements

- Performance: TBD
- Security: TBD
- Analytics: TBD

## 5. Acceptance Criteria

{{#each acceptance_criteria}}
- {{this}}
{{/each}}

## 6. Scope

### In scope
- TBD

### Out of scope
{{#if out_of_scope}}
{{#each out_of_scope}}
- {{this}}
{{/each}}
{{/if}}

## 7. Success Metrics

{{#each success_metrics}}
- {{this}}
{{/each}}

## 8. Platforms

{{#if platforms}}
{{#each platforms}}
- {{this}}
{{/each}}
{{else}}
- TBD
{{/if}}

## 9. Open Questions

- TBD

<!-- /lang:en -->
