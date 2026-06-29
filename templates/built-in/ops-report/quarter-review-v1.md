---
template_id: ops-report-builtin-quarter-review
schema_version: 1
name: "Quarter Review"
artifact_type: ops-report
subtype: ops-quarter-review
scope: built-in
products: []
default_language: uk
available_languages: [uk, en]
version: "1.0.0"
author: "grow-pm"
created: 2026-06-29
updated: 2026-06-29
tags: [ops, quarter, plan-vs-actual, epics, releases]
description: "Результати кварталу: план vs факт, релізи, повністю закриті епіки/фічі, внесок по напрямках"
status: active
min_plugin_version: "1.14.0"
---


> **Команда:** {{team_name}} · **Квартал:** {{quarter}} ({{quarter_dates}}) · Спринти: {{sprint_list}}
> Згенеровано {{date}}.

## 🎯 Підсумок кварталу
| Показник | Значення |
|---|---|
| Закрито задач | **{{done_count}}** |
| Story Points виконано | **{{sp_done}}** |
| Релізів за квартал | {{releases_count}} |
| Епіків/фіч повністю закрито | {{epics_closed_count}} |
| Активних епіків (просунулись) | {{epics_active_count}} |

## 🧭 План vs Факт по напрямках
Заплановане на квартал (roadmap / OKR) проти фактично закритого; де просунулись.
| Напрямок | План (фіч/SP) | Зроблено (задач/SP) | % | Коментар |
|---|---|---|--:|---|
| {{direction}} | {{planned}} | {{done}} | {{pct}} | {{note}} |

## ✅ Епіки/фічі, повністю закриті за квартал
Епіки, де всі дочірні done (або статус епіка → Done у кварталі).
| Епік | Назва | SP | Закрито |
|---|---|--:|---|
| {{epic_link}} | {{name}} | {{sp}} | {{resolved}} |

## 🚀 Релізи кварталу
Згруповано по потоках (app / catalog-ui / backend / company-stats), `releaseDate` у вікні кварталу.
| Потік | К-сть | Ключові версії |
|---|--:|---|

## 📊 Внесок по епіках (топ)
→ Графік: bar — SP виконано по епіках/напрямках за квартал. PNG.
| Епік/Напрямок | Задач | SP |
|---|--:|--:|

## 👥 Внесок по членах (опц.)
| Виконавець | Закрито | SP |
|---|--:|--:|

## Висновки / ризики
- Що просунулось найбільше: {{highlights}}
- Що відстає / перенесено на наступний квартал: {{slips}}

<!-- template: ops-quarter-review-builtin@0.1 -->

---
### Технічна нотатка pipeline (підтверджено тестом)
Повний квартальний JQL (`resolved >= ... AND resolved <= ...`, 3 міс) **стабільно таймаутить** (>180с) на цьому Jira. Тягнути **помісячно** (квітень/травень/червень) і сумувати. «Епіки повністю закриті» — окремим запитом `issuetype = Epic AND status changed to Done DURING (quarter)` або перевіркою, що всі діти done.
