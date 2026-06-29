---
template_id: ops-report-builtin-sprint-plan
schema_version: 1
name: "Sprint Plan"
artifact_type: ops-report
subtype: ops-sprint-plan
scope: built-in
products: []
default_language: uk
available_languages: [uk, en]
version: "1.0.0"
author: "grow-pm"
created: 2026-06-29
updated: 2026-06-29
tags: [ops, sprint, plan, jira]
description: "План на спринт: напрямки → фічі → задачі, зведення (план/carried/new/SP), розподіл по Assignee та Developer, ключові фокуси"
status: active
min_plugin_version: "1.14.0"
variables:
  - { name: team_name, type: string, required: true, label: "Команда" }
  - { name: sprint_name, type: string, required: true, label: "Спринт" }
  - { name: sprint_dates, type: string, required: true, label: "Період" }
  - { name: board_url, type: string, required: false, label: "Дошка" }
---

> **Команда:** {{team_name}} · **Спринт:** {{sprint_name}} · **Період:** {{sprint_dates}} · Дошка: {{board_url}}
> «Нова» = немає попередніх спринтів в історії; «Перенесена» = була в попередніх. Платформа — з префікса назви.

## 📊 Зведення спринту
| Показник | Значення |
|---|---|
| Усього задач заплановано | **{{total}}** |
| Перенесено з попереднього спринту | {{carried}} |
| Нових задач заплановано | {{new}} |
| Story Points усього | **{{sp_total}}** |
| SP у перенесених | {{sp_carried}} |
| SP у нових (сформовано при плануванні) | {{sp_new}} |

## 👥 Розподіл за Assignee
| Виконавець | Задач | Перенесено | Нових | SP усього | SP нових |
|---|--:|--:|--:|--:|--:|

## 🧑‍💻 Розподіл за Developer
| Developer | Задач | Перенесено | Нових | SP усього | SP нових |
|---|--:|--:|--:|--:|--:|

## 🎯 Ключові фокуси
| Напрямок | Задач | SP | Що робимо у спринті |
|---|--:|--:|---|

## Деталізація: напрямки → фічі → задачі
### {{direction}} · {{count}} задач
#### {{feature_name}} — {{epic_link}}
| Тікет | Задача | Платформа | Статус | Походження | SP | Assignee | Developer | QA |
|---|---|---|---|---|--:|---|---|---|

### ⬚ Задачі без фічі
Окрема таблиця того ж формату.

<!-- template: ops-report-builtin-sprint-plan@1.0.0 -->
