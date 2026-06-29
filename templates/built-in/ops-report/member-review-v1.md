---
template_id: ops-report-builtin-member-review
schema_version: 1
name: "Team Member Review"
artifact_type: ops-report
subtype: ops-member-review
scope: built-in
products: []
default_language: uk
available_languages: [uk, en]
version: "1.0.0"
author: "grow-pm"
created: 2026-06-29
updated: 2026-06-29
tags: [ops, member, throughput, changelog, dynamics]
description: "Результати члена команди за період: закрито/SP/передано на тест(ревʼю)/протестовано + динаміка (role-aware)"
status: active
min_plugin_version: "1.14.0"
---


> **Член команди:** {{member_name}} ({{role}}) · **Період:** {{period}} · Гранулярність динаміки: {{granularity}}
> Команда: {{team_name}} · Згенеровано {{date}}.

## 🎯 KPI періоду
Набір метрик залежить від ролі (role-aware):
- **Developer** — розроблено й закрито, **передано на тест** (`status CHANGED TO "Ready for test" BY member`), SP виконано.
- **QA** — протестовано (`customfield_10037 = member` + перехід з тестового статусу), знайдено/повернуто.
- **Analyst / Designer** — передано на ревʼю (`status CHANGED TO "On review" BY member`), закрито.

| Показник | Значення |
|---|---|
| Розроблено й закрито (Developer/Assignee) | **{{closed_count}}** |
| Story Points виконано | **{{sp_done}}** |
| Передано на тест (`Ready for test`) | {{passed_to_test}} |
| Передано на ревʼю (`On review`) | {{passed_to_review}} |
| Протестовано (QA-роль) | {{tested}} |

## 📈 Динаміка (за {{granularity}})
Delivery-метрики беруться з `resolutiondate` + SP (без важкого changelog). Метрики переходів — з `status CHANGED ... BY member DURING <bucket>` (changelog-backed JQL).

| Період | Закрито | SP | Передано на тест |
|---|--:|--:|--:|
| {{bucket}} | {{count}} | {{sp}} | {{transitions}} |

→ Графік: бари = SP, лінія = кількість задач (PNG, вбудовується в Confluence / долучається). Опційно — лінія «передано на тест».

## 🧩 Внесок по фічах
| Фіча | Закрито | SP |
|---|--:|--:|
| {{feature}} — {{epic_link}} | {{count}} | {{sp}} |

## 📋 Перелік задач (опц., згорнуто)
| Тікет | Задача | Закрито | SP | Фіча |
|---|---|---|--:|---|
| [{{key}}]({{url}}) | {{summary}} | {{resolutiondate}} | {{sp}} | {{epic}} |

## Нотатки / спостереження
- Сезонність (відпустки, провали): {{notes}}
- Цикл «розробив → на тест → закрито» (cycle time) — опц., з changelog timestamps.

<!-- template: ops-member-review-builtin@0.1 -->
