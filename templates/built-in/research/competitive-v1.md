---
template_id: research-builtin-competitive
schema_version: 1
name:
  uk: "Конкурентний аналіз"
  en: "Competitive Analysis"
artifact_type: research
subtype: competitive
scope: built-in
products: []
default_language: uk
available_languages: [uk, en]
version: "1.0.0"
author: "grow-pm"
created: 2026-04-17
updated: 2026-04-17
tags: [research, competitive, market]
description:
  uk: "Шаблон конкурентного аналізу: учасники ринку, SWOT, позиціонування, висновки"
  en: "Competitive analysis template: players, SWOT, positioning, takeaways"
status: active
min_plugin_version: "1.9.0"
variables:
  - name: research_topic
    type: string
    required: true
    label:
      uk: "Тема дослідження"
      en: "Research topic"
  - name: research_question
    type: text
    required: true
    label:
      uk: "Дослідницьке питання"
      en: "Research question"
  - name: competitors
    type: list
    required: true
    label:
      uk: "Список конкурентів"
      en: "List of competitors"
  - name: our_product
    type: string
    required: false
    label:
      uk: "Наш продукт (для порівняння)"
      en: "Our product (for comparison)"
  - name: comparison_dimensions
    type: list
    required: false
    label:
      uk: "Виміри порівняння"
      en: "Comparison dimensions"
  - name: sources
    type: list
    required: false
    label:
      uk: "Джерела даних"
      en: "Data sources"
---

<!-- lang:uk -->
# Конкурентний аналіз: {{research_topic}}

## 1. Мета дослідження

{{research_question}}

## 2. Методологія

- Підхід: desk research + експертні оцінки
- Період: TBD
{{#if sources}}
- Джерела:
{{#each sources}}
  - {{this}}
{{/each}}
{{/if}}

## 3. Учасники ринку

{{#each competitors}}
- {{this}}
{{/each}}

## 4. Порівняльна таблиця

{{#if comparison_dimensions}}
| Вимір | {{#if our_product}}{{our_product}}{{else}}Ми{{/if}} | {{#each competitors}}{{this}} | {{/each}}
|-------|------|{{#each competitors}}------|{{/each}}
{{#each comparison_dimensions}}
| {{this}} | TBD | {{#each ../competitors}}TBD | {{/each}}
{{/each}}
{{else}}
TBD — заповнити виміри порівняння.
{{/if}}

## 5. SWOT (для кожного конкурента)

{{#each competitors}}
### {{this}}

- **Strengths:** TBD
- **Weaknesses:** TBD
- **Opportunities:** TBD
- **Threats:** TBD

{{/each}}

## 6. Позиціонування

Опис карти позиціонування (X / Y осі), де кожен конкурент розміщений.

## 7. Ключові висновки

- TBD

## 8. Рекомендації

### Що наслідувати
- TBD

### Чого уникати
- TBD

### Де диференціюватися
- TBD

## 9. Відкриті питання

- TBD

<!-- /lang:uk -->

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
