---
template_id: ops-report-builtin-sprint-review
schema_version: 1
name: "Sprint Review"
artifact_type: ops-report
subtype: ops-sprint-review
scope: built-in
products: []
default_language: uk
available_languages: [uk, en]
version: "1.0.0"
author: "grow-pm"
created: 2026-06-29
updated: 2026-06-29
tags: [ops, sprint, review, releases, flags]
description: "Результати спринту: закриті задачі, релізи, прапори ON/OFF, закрито по членах, перелік задач"
status: active
min_plugin_version: "1.14.0"
---


> **Команда:** {{team_name}} · **Спринт:** {{sprint_name}} · **Період:** {{sprint_dates}}
> Дошка: {{board_url}} · «Закрите» = статус-категорія Done (включно зі статусом **Ready** = викочено / йде A/B). Згенеровано {{date}}.

## 📊 Підсумок
| Показник | Значення |
|---|---|
| Закрито задач (Closed+Ready) | **{{closed_count}}** |
| Story Points виконано | **{{sp_done}}** |
| % від плану спринту (закрито/заплановано) | {{plan_completion}} |
| Релізів у спринті | {{releases_count}} |
| Прапорів увімкнено / A-B запущено | {{flags_on_count}} |
| Прапорів вимкнено / прибрано | {{flags_off_count}} |

## 🚀 Релізи у спринті
Згруповано по потоках, лише релізи з `releaseDate` у вікні спринту.
| Потік | Версії |
|---|---|
| App (Android/iOS) | {{releases_app}} |
| catalog-ui | {{releases_catalog}} |
| Backend / сервіси | {{releases_backend}} |

## 🚩 Прапори
| Дія | Прапор | Задача |
|---|---|---|
| ON / A-B | {{flag_name}} | {{key}} |
| OFF / прибрано | {{flag_name}} | {{key}} |

## 👥 Закрито по членах — за Assignee
| Виконавець | Закрито | SP |
|---|--:|--:|
| {{name}} | {{count}} | {{sp}} |
| **Разом** | **{{closed_count}}** | **{{sp_done}}** |

## 🧑‍💻 Закрито по членах — за Developer
| Developer | Закрито | SP |
|---|--:|--:|
| {{name}} | {{count}} | {{sp}} |
| **Разом** | **{{closed_count}}** | **{{sp_done}}** |

## 📋 Перелік закритих задач
Згруповано по фічах (Epic Link); кожен тікет — посиланням `https://evocompany.atlassian.net/browse/{{key}}`. Задачі без фічі — в окремому блоці наприкінці.

### {{feature_name}} — {{epic_link}}
| Тікет | Задача | Статус | SP | Assignee | Developer |
|---|---|---|--:|---|---|
| [{{key}}]({{url}}) | {{summary}} | {{status}} | {{sp}} | {{assignee}} | {{developer}} |

### ⬚ Поза фічами / технічне
Дрібні чори, баги, крос-проєктні (CMS-*, DT-*) — окремою таблицею того ж формату.

## 📦 Зведення по фічах/напрямках (опц.)
| Напрямок → Фіча | Закрито | SP | Релізи |
|---|--:|--:|---|

## Нотатки
- Незавершене, що перейшло далі (carry-over у наступний спринт): {{carry_over_note}}
- Спостереження / ризики: {{notes}}

<!-- template: ops-sprint-review-builtin@0.1 -->
