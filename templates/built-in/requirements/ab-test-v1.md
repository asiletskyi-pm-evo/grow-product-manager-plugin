---
template_id: requirements-builtin-ab-test
schema_version: 1
name:
  uk: "Вимоги до A/B-тесту"
  en: "A/B Test Requirements"
artifact_type: requirements
subtype: ab-test
scope: built-in
products: []
default_language: uk
available_languages: [uk, en]
version: "1.0.0"
author: "grow-pm"
created: 2026-04-17
updated: 2026-04-17
tags: [requirements, ab-test, experiment, growth]
description:
  uk: "Вимоги до A/B-експерименту — гіпотеза, варіанти, метрики, критерії зупинки"
  en: "A/B experiment requirements — hypothesis, variants, metrics, stopping criteria"
status: active
min_plugin_version: "1.9.0"
variables:
  - name: experiment_name
    type: string
    required: true
    label:
      uk: "Назва експерименту"
      en: "Experiment name"
  - name: hypothesis
    type: text
    required: true
    label:
      uk: "Гіпотеза"
      en: "Hypothesis"
    hint:
      uk: "Якщо <зміна>, то <метрика> зміниться на <величина>, бо <причина>"
      en: "If <change>, then <metric> will change by <amount>, because <reason>"
  - name: primary_metric
    type: string
    required: true
    label:
      uk: "Первинна метрика"
      en: "Primary metric"
  - name: secondary_metrics
    type: list
    required: false
    label:
      uk: "Вторинні метрики"
      en: "Secondary metrics"
  - name: guardrail_metrics
    type: list
    required: false
    label:
      uk: "Guardrail метрики"
      en: "Guardrail metrics"
  - name: audience
    type: text
    required: true
    label:
      uk: "Аудиторія / сегментація"
      en: "Audience / segmentation"
  - name: control_description
    type: text
    required: true
    label:
      uk: "Опис контрольної групи (A)"
      en: "Control description (A)"
  - name: variant_description
    type: text
    required: true
    label:
      uk: "Опис тестової групи (B)"
      en: "Variant description (B)"
  - name: split_ratio
    type: string
    required: false
    label:
      uk: "Розподіл трафіку"
      en: "Traffic split"
    default: "50/50"
  - name: mde
    type: string
    required: false
    label:
      uk: "MDE (мінімальний ефект, що ми хочемо виявити)"
      en: "MDE (minimum detectable effect)"
  - name: duration_estimate
    type: string
    required: false
    label:
      uk: "Орієнтовна тривалість"
      en: "Estimated duration"
  - name: stopping_criteria
    type: list
    required: true
    label:
      uk: "Критерії зупинки / прийняття рішення"
      en: "Stopping / decision criteria"
---

<!-- lang:uk -->
# A/B Test: {{experiment_name}}

## 1. Гіпотеза

{{hypothesis}}

## 2. Аудиторія

{{audience}}

## 3. Варіанти

### Контроль (A)
{{control_description}}

### Варіант (B)
{{variant_description}}

**Розподіл трафіку:** {{split_ratio}}

## 4. Метрики

### Первинна
- **{{primary_metric}}**

### Вторинні
{{#if secondary_metrics}}
{{#each secondary_metrics}}
- {{this}}
{{/each}}
{{else}}
- TBD
{{/if}}

### Guardrails
{{#if guardrail_metrics}}
{{#each guardrail_metrics}}
- {{this}}
{{/each}}
{{else}}
- TBD
{{/if}}

## 5. Параметри експерименту

- **MDE:** {{#if mde}}{{mde}}{{else}}TBD{{/if}}
- **Орієнтовна тривалість:** {{#if duration_estimate}}{{duration_estimate}}{{else}}TBD{{/if}}
- **Рівень значущості:** 95%
- **Потужність:** 80%

## 6. Критерії зупинки / прийняття рішення

{{#each stopping_criteria}}
- {{this}}
{{/each}}

## 7. Аналітика / трекінг

- Події: TBD
- Дашборд: TBD
- Сегменти для аналізу: TBD

## 8. Ризики

- TBD

## 9. План пост-експерименту

- Якщо виграв B: TBD
- Якщо виграв A або нічия: TBD
- Якщо guardrails порушено: TBD

<!-- /lang:uk -->

<!-- lang:en -->
# A/B Test: {{experiment_name}}

## 1. Hypothesis

{{hypothesis}}

## 2. Audience

{{audience}}

## 3. Variants

### Control (A)
{{control_description}}

### Variant (B)
{{variant_description}}

**Traffic split:** {{split_ratio}}

## 4. Metrics

### Primary
- **{{primary_metric}}**

### Secondary
{{#if secondary_metrics}}
{{#each secondary_metrics}}
- {{this}}
{{/each}}
{{else}}
- TBD
{{/if}}

### Guardrails
{{#if guardrail_metrics}}
{{#each guardrail_metrics}}
- {{this}}
{{/each}}
{{else}}
- TBD
{{/if}}

## 5. Experiment Parameters

- **MDE:** {{#if mde}}{{mde}}{{else}}TBD{{/if}}
- **Estimated duration:** {{#if duration_estimate}}{{duration_estimate}}{{else}}TBD{{/if}}
- **Significance level:** 95%
- **Power:** 80%

## 6. Stopping / Decision Criteria

{{#each stopping_criteria}}
- {{this}}
{{/each}}

## 7. Analytics / Tracking

- Events: TBD
- Dashboard: TBD
- Segments to analyze: TBD

## 8. Risks

- TBD

## 9. Post-experiment Plan

- If B wins: TBD
- If A wins or tie: TBD
- If guardrails are breached: TBD

<!-- /lang:en -->
