---
template_id: presentation-builtin-ab-test-readout
schema_version: 1
name:
  uk: "Результати A/B-тесту"
  en: "A/B Test Readout"
artifact_type: presentation
subtype: ab-test-readout
scope: built-in
products: []
default_language: uk
available_languages: [uk, en]
version: "1.0.0"
author: "grow-pm"
created: 2026-04-20
updated: 2026-04-20
tags: [presentation, ab-test, experiment, readout]
description:
  uk: "Результати A/B-тесту (6 слайдів): hypothesis → primary metric → guardrails → interpretation → decision"
  en: "A/B test readout (6 slides): hypothesis → primary metric → guardrails → interpretation → decision"
status: active
min_plugin_version: "1.10.0"
variables:
  - name: test_name
    type: string
    required: true
    label:
      uk: "Назва тесту"
      en: "Test name"
  - name: date_range
    type: string
    required: true
    label:
      uk: "Період тесту (start → end)"
      en: "Test date range (start → end)"
  - name: platform
    type: string
    required: true
    label:
      uk: "Платформа (Web / iOS / Android / All)"
      en: "Platform (Web / iOS / Android / All)"
  - name: segment
    type: string
    required: false
    label:
      uk: "Сегмент (all / new users / logged-in / geo / etc.)"
      en: "Segment (all / new users / logged-in / geo / etc.)"
  - name: presenter
    type: string
    required: false
    label:
      uk: "Хто презентує"
      en: "Presenter"
  - name: hypothesis
    type: text
    required: true
    label:
      uk: "Гіпотеза (Якщо … то … тому що …)"
      en: "Hypothesis (If … then … because …)"
  - name: success_metric
    type: string
    required: true
    label:
      uk: "Primary метрика успіху"
      en: "Primary success metric"
  - name: traffic_split
    type: string
    required: true
    label:
      uk: "Traffic split (напр. 50/50)"
      en: "Traffic split (e.g., 50/50)"
  - name: sample_size
    type: string
    required: true
    label:
      uk: "Розмір вибірки (N на варіант)"
      en: "Sample size (N per arm)"
  - name: primary_result
    type: text
    required: true
    label:
      uk: "Primary результат (control → treatment, delta, CI, p-value)"
      en: "Primary result (control → treatment, delta, CI, p-value)"
  - name: guardrails_results
    type: list
    required: false
    label:
      uk: "Guardrails / secondary метрики (по одному рядку на метрику)"
      en: "Guardrails / secondary metrics (one row per metric)"
  - name: interpretation
    type: text
    required: true
    label:
      uk: "Інтерпретація (спостереження, сегменти, сюрпризи)"
      en: "Interpretation (observations, segments, surprises)"
  - name: decision
    type: string
    required: true
    label:
      uk: "Рішення (Ship / Kill / Iterate)"
      en: "Decision (Ship / Kill / Iterate)"
  - name: rollout_plan
    type: text
    required: false
    label:
      uk: "План rollout / наступних кроків"
      en: "Rollout / next-steps plan"
  - name: owner
    type: string
    required: false
    label:
      uk: "Власник"
      en: "Owner"
---

<!-- lang:uk -->
# A/B-тест: {{test_name}}

{{#if presenter}}**Презентує:** {{presenter}}{{/if}}

**Період:** {{date_range}} · **Платформа:** {{platform}}{{#if segment}} · **Сегмент:** {{segment}}{{/if}}

---

## Слайд 1. Заголовок

- {{test_name}}
- Підзаголовок: {{date_range}} · {{platform}}{{#if segment}} · {{segment}}{{/if}}
- Презентує, дата

## Слайд 2. Гіпотеза та setup

**Гіпотеза:**
{{hypothesis}}

**Setup:**

- **Primary metric:** {{success_metric}}
- **Traffic split:** {{traffic_split}}
- **Sample size:** {{sample_size}} на варіант
- **Тривалість:** {{date_range}}

## Слайд 3. Primary метрика: {{success_metric}}

{{primary_result}}

_(Chart: bar — control vs treatment з CI. Caption: p-value, CI.)_

## Слайд 4. Secondary / guardrails

{{#if guardrails_results}}
{{#each guardrails_results}}
- {{this}}
{{/each}}
{{else}}
- Guardrail 1: control → treatment, delta
- Guardrail 2: control → treatment, delta
- Secondary 1: control → treatment, delta
{{/if}}

_(Chart: multi-bar з кількома метриками.)_

## Слайд 5. Інтерпретація

{{interpretation}}

## Слайд 6. Рішення та rollout

**Рішення:** {{decision}}

{{#if rollout_plan}}
**План:**
{{rollout_plan}}
{{else}}
- Наступний крок
- Timeline
- Blockers / ризики
{{/if}}

{{#if owner}}**Owner:** {{owner}}{{/if}}

---

## Додаток: спікер-нотатки

Для кожного слайду — 3-5 речень. Для Слайда 3 — обов'язково сказати про статистичну значущість та business significance окремо.

<!-- /lang:uk -->

<!-- lang:en -->
# A/B Test: {{test_name}}

{{#if presenter}}**Presenter:** {{presenter}}{{/if}}

**Period:** {{date_range}} · **Platform:** {{platform}}{{#if segment}} · **Segment:** {{segment}}{{/if}}

---

## Slide 1. Title

- {{test_name}}
- Subtitle: {{date_range}} · {{platform}}{{#if segment}} · {{segment}}{{/if}}
- Presenter, date

## Slide 2. Hypothesis & setup

**Hypothesis:**
{{hypothesis}}

**Setup:**

- **Primary metric:** {{success_metric}}
- **Traffic split:** {{traffic_split}}
- **Sample size:** {{sample_size}} per arm
- **Duration:** {{date_range}}

## Slide 3. Primary metric: {{success_metric}}

{{primary_result}}

_(Chart: bar — control vs treatment with CI. Caption: p-value, CI.)_

## Slide 4. Secondary / guardrails

{{#if guardrails_results}}
{{#each guardrails_results}}
- {{this}}
{{/each}}
{{else}}
- Guardrail 1: control → treatment, delta
- Guardrail 2: control → treatment, delta
- Secondary 1: control → treatment, delta
{{/if}}

_(Chart: multi-bar with several metrics.)_

## Slide 5. Interpretation

{{interpretation}}

## Slide 6. Decision & rollout

**Decision:** {{decision}}

{{#if rollout_plan}}
**Plan:**
{{rollout_plan}}
{{else}}
- Next step
- Timeline
- Blockers / risks
{{/if}}

{{#if owner}}**Owner:** {{owner}}{{/if}}

---

## Appendix: speaker notes

For each slide — 3-5 sentences. For Slide 3 — always mention statistical significance AND business significance separately.

<!-- /lang:en -->
