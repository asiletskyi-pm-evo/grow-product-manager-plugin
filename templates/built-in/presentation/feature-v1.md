---
template_id: presentation-builtin-feature
schema_version: 1
name:
  uk: "Презентація фічі"
  en: "Feature Presentation"
artifact_type: presentation
subtype: feature
scope: built-in
products: []
default_language: uk
available_languages: [uk, en]
version: "1.0.0"
author: "grow-pm"
created: 2026-04-17
updated: 2026-04-17
tags: [presentation, feature, pitch]
description:
  uk: "Презентація фічі стейкхолдерам (10 слайдів) у форматі текстового outline"
  en: "Feature presentation to stakeholders (10 slides) as a text outline"
status: active
min_plugin_version: "1.9.0"
variables:
  - name: feature_name
    type: string
    required: true
    label:
      uk: "Назва фічі"
      en: "Feature name"
  - name: presenter
    type: string
    required: false
    label:
      uk: "Хто презентує"
      en: "Presenter"
  - name: audience
    type: string
    required: false
    label:
      uk: "Аудиторія"
      en: "Audience"
  - name: problem_statement
    type: text
    required: true
    label:
      uk: "Проблема"
      en: "Problem"
  - name: solution_summary
    type: text
    required: true
    label:
      uk: "Рішення"
      en: "Solution"
  - name: key_metrics
    type: list
    required: true
    label:
      uk: "Ключові метрики / KPI"
      en: "Key metrics / KPIs"
  - name: ask
    type: text
    required: false
    label:
      uk: "Запит до стейкхолдерів"
      en: "Ask for stakeholders"
---

<!-- lang:uk -->
# Презентація: {{feature_name}}

{{#if presenter}}**Презентує:** {{presenter}}{{/if}}
{{#if audience}}**Аудиторія:** {{audience}}{{/if}}

---

## Слайд 1. Заголовок

- {{feature_name}}
- Підзаголовок: one-liner
- Презентує, дата

## Слайд 2. Контекст

- Де ми зараз?
- Чому саме зараз?

## Слайд 3. Проблема

{{problem_statement}}

## Слайд 4. Користувачі / сегменти

- Хто страждає?
- Скільки їх?
- Що говорять?

## Слайд 5. Дані / Evidence

- Ключові цифри, що підтверджують проблему
- Дослідження / фідбек

## Слайд 6. Рішення

{{solution_summary}}

## Слайд 7. Як це виглядає (візуал)

- Скрін / мокап / flow
- Ключові зміни UX

## Слайд 8. Метрики успіху

{{#each key_metrics}}
- {{this}}
{{/each}}

## Слайд 9. План / Timeline

- Етапи, дати, команди
- Залежності, ризики

## Слайд 10. Ask

{{#if ask}}
{{ask}}
{{else}}
- Що потрібно від команди / стейкхолдерів?
{{/if}}

---

## Додаток: спікер-нотатки

Для кожного слайду — 3-5 речень, що сказати вголос.

<!-- /lang:uk -->

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
