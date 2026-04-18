---
template_id: task-builtin-default
schema_version: 1
name:
  uk: "Задача (за замовчуванням)"
  en: "Task (default)"
artifact_type: task
subtype: null
scope: built-in
products: []
default_language: uk
available_languages: [uk, en]
version: "1.0.0"
author: "grow-pm"
created: 2026-04-17
updated: 2026-04-17
tags: [task, jira]
description:
  uk: "Стандартний шаблон задачі для Jira (FE / BE / Mobile / Design / Analytics)"
  en: "Standard Jira task template (FE / BE / Mobile / Design / Analytics)"
status: active
min_plugin_version: "1.9.0"
variables:
  - name: task_title
    type: string
    required: true
    label:
      uk: "Заголовок задачі"
      en: "Task title"
  - name: task_type
    type: enum
    required: true
    options: [FE, BE, iOS, Android, Design, Analytics, QA, DevOps]
    label:
      uk: "Тип задачі"
      en: "Task type"
  - name: parent_epic
    type: reference
    required: false
    label:
      uk: "Epic"
      en: "Epic"
  - name: description
    type: text
    required: true
    label:
      uk: "Опис"
      en: "Description"
  - name: acceptance_criteria
    type: list
    required: true
    label:
      uk: "Критерії прийняття"
      en: "Acceptance criteria"
  - name: dependencies
    type: list
    required: false
    label:
      uk: "Залежності"
      en: "Dependencies"
---

<!-- lang:uk -->
# [{{task_type}}] {{task_title}}

{{#if parent_epic}}
**Epic:** {{parent_epic}}
{{/if}}

## Опис

{{description}}

## Контекст / посилання

- Концепт: TBD
- Вимоги: TBD
- Дизайн: TBD
- Аналітика (події): TBD

## Що треба зробити

- TBD

## Критерії прийняття

{{#each acceptance_criteria}}
- [ ] {{this}}
{{/each}}

## Залежності

{{#if dependencies}}
{{#each dependencies}}
- {{this}}
{{/each}}
{{else}}
- Немає
{{/if}}

## Оцінка

- SP / годин: TBD

## Definition of Done

- [ ] Код reviewed і merged
- [ ] Аналітика валідна
- [ ] QA пройдено
- [ ] Документація оновлена (якщо застосовно)

<!-- /lang:uk -->

<!-- lang:en -->
# [{{task_type}}] {{task_title}}

{{#if parent_epic}}
**Epic:** {{parent_epic}}
{{/if}}

## Description

{{description}}

## Context / Links

- Concept: TBD
- Requirements: TBD
- Design: TBD
- Analytics (events): TBD

## What to do

- TBD

## Acceptance Criteria

{{#each acceptance_criteria}}
- [ ] {{this}}
{{/each}}

## Dependencies

{{#if dependencies}}
{{#each dependencies}}
- {{this}}
{{/each}}
{{else}}
- None
{{/if}}

## Estimate

- SP / hours: TBD

## Definition of Done

- [ ] Code reviewed and merged
- [ ] Analytics validated
- [ ] QA passed
- [ ] Documentation updated (if applicable)

<!-- /lang:en -->
