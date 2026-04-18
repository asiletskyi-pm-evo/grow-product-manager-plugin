---
template_id: cjm-builtin-funnel
schema_version: 1
name:
  uk: "CJM-звіт: аналіз воронки"
  en: "CJM Report: Funnel Analysis"
artifact_type: cjm
subtype: funnel
scope: built-in
products: []
default_language: uk
available_languages: [uk, en]
version: "1.0.0"
author: "grow-pm"
created: 2026-04-17
updated: 2026-04-17
tags: [cjm, funnel, analysis]
description:
  uk: "Шаблон звіту CJM з кроками воронки, аномаліями та гіпотезами"
  en: "CJM report template with funnel steps, anomalies, and hypotheses"
status: active
min_plugin_version: "1.9.0"
variables:
  - name: funnel_name
    type: string
    required: true
    label:
      uk: "Назва воронки"
      en: "Funnel name"
  - name: product
    type: string
    required: false
    label:
      uk: "Продукт"
      en: "Product"
  - name: platform
    type: enum
    required: false
    options: [web, ios, android, all]
    label:
      uk: "Платформа"
      en: "Platform"
  - name: period
    type: string
    required: true
    label:
      uk: "Період аналізу"
      en: "Analysis period"
  - name: funnel_steps
    type: list
    required: true
    label:
      uk: "Кроки воронки (в порядку)"
      en: "Funnel steps (in order)"
  - name: anomalies
    type: list
    required: false
    label:
      uk: "Виявлені аномалії"
      en: "Detected anomalies"
  - name: hypotheses
    type: list
    required: false
    label:
      uk: "Гіпотези покращення"
      en: "Improvement hypotheses"
---

<!-- lang:uk -->
# CJM / Воронка: {{funnel_name}}

**Період:** {{period}}
{{#if product}}**Продукт:** {{product}}{{/if}}
{{#if platform}}**Платформа:** {{platform}}{{/if}}

## 1. Контекст

Опис воронки, гіпотези, які перевіряємо, і джерела даних.

## 2. Кроки воронки

{{#each funnel_steps}}
### {{@index}}. {{this}}
- Вхід: TBD
- Конверсія до наступного кроку: TBD %
- Очікування (benchmark): TBD %
- Δ: TBD

{{/each}}

## 3. Загальна воронка

| Крок | Користувачі | Конверсія крок→крок | Загальна конверсія |
|------|-------------|---------------------|--------------------|
{{#each funnel_steps}}
| {{this}} | TBD | TBD % | TBD % |
{{/each}}

## 4. Аномалії

{{#if anomalies}}
{{#each anomalies}}
### {{this}}

- Крок: TBD
- Метрика: TBD
- Відхилення: TBD
- Потенційна причина: TBD

{{/each}}
{{else}}
TBD.
{{/if}}

## 5. Порівняння з benchmarks / джерелами знань

- TBD (з бібліотеки знань / CJM-протоколу)

## 6. Гіпотези покращення

{{#if hypotheses}}
{{#each hypotheses}}
- {{this}}
{{/each}}
{{else}}
- TBD
{{/if}}

## 7. Пріоритизація (ICE)

| Гіпотеза | Impact | Confidence | Ease | Score |
|----------|--------|------------|------|-------|
{{#if hypotheses}}
{{#each hypotheses}}
| {{this}} | TBD | TBD | TBD | TBD |
{{/each}}
{{/if}}

## 8. Рекомендації

- TBD

## 9. Наступні кроки

- TBD

<!-- /lang:uk -->

<!-- lang:en -->
# CJM / Funnel: {{funnel_name}}

**Period:** {{period}}
{{#if product}}**Product:** {{product}}{{/if}}
{{#if platform}}**Platform:** {{platform}}{{/if}}

## 1. Context

Funnel description, hypotheses being tested, and data sources.

## 2. Funnel Steps

{{#each funnel_steps}}
### {{@index}}. {{this}}
- Entry: TBD
- Conversion to next step: TBD %
- Benchmark: TBD %
- Δ: TBD

{{/each}}

## 3. Overall Funnel

| Step | Users | Step→Step conversion | Overall conversion |
|------|-------|----------------------|--------------------|
{{#each funnel_steps}}
| {{this}} | TBD | TBD % | TBD % |
{{/each}}

## 4. Anomalies

{{#if anomalies}}
{{#each anomalies}}
### {{this}}

- Step: TBD
- Metric: TBD
- Deviation: TBD
- Potential cause: TBD

{{/each}}
{{else}}
TBD.
{{/if}}

## 5. Comparison vs benchmarks / knowledge sources

- TBD (from knowledge library / CJM protocol)

## 6. Improvement Hypotheses

{{#if hypotheses}}
{{#each hypotheses}}
- {{this}}
{{/each}}
{{else}}
- TBD
{{/if}}

## 7. Prioritization (ICE)

| Hypothesis | Impact | Confidence | Ease | Score |
|------------|--------|------------|------|-------|
{{#if hypotheses}}
{{#each hypotheses}}
| {{this}} | TBD | TBD | TBD | TBD |
{{/each}}
{{/if}}

## 8. Recommendations

- TBD

## 9. Next Steps

- TBD

<!-- /lang:en -->
