---
template_id: ops-report-builtin-initiative-status
schema_version: 1
name: "Initiative Status"
artifact_type: ops-report
subtype: ops-initiative-status
scope: built-in
products: []
default_language: uk
available_languages: [uk, en]
version: "1.0.0"
author: "grow-pm"
created: 2026-06-29
updated: 2026-06-29
tags: [ops, epic, feature, status, progress]
description: "Статус реалізації місії/проєкту/епіка/фічі: % готовності, статуси, під-фічі, блокери"
status: active
min_plugin_version: "1.14.0"
---


> **Ініціатива:** {{initiative_title}} — {{key_link}} · **Тип:** {{type}} · **Статус:** {{epic_status}}
> Власник: {{owner}} · Активна з {{start_date}} · Згенеровано {{date}}.

## 🎯 Готовність
| Показник | Значення |
|---|---|
| Дочірніх задач усього | **{{total}}** |
| Закрито (done) | {{done}} |
| **% готовності (за кількістю)** | **{{pct_done}}** |
| % готовності (SP-зважено, де є оцінки) | {{pct_done_sp}} |
| Відкрито | {{open}} |
| Блокери (Flagged / On hold / blocked-links) | {{blockers}} |

→ Графік: donut статусів (Done / Ready for test / In dev / Ready for dev / Requirements). PNG.

## 📊 Розклад по статусах
| Статус | Задач |
|---|--:|
| {{status}} | {{count}} |

## 🧩 Стан по під-фічах (X.Y)
Групування за кодом під-фічі в назві (`{{key}}.N`); показує, що зроблено / в роботі / заплановано.
| Під-фіча | Задач | Готово | Відкрито | Стан |
|---|--:|--:|--:|---|
| {{subfeature}} | {{n}} | {{done}} | {{open}} | {{state}} |

## ⛔ Блокери та ризики
- Flagged-задачі: {{flagged_list}}
- On hold: {{onhold_list}}
- Залежності (blocked by): {{blocked_links}}

## 🗓 Таймлайн
- Перша закрита: {{first_resolved}} · Остання активність: {{last_activity}}
- Найближчі віхи (due dates): {{milestones}}

## Наступні кроки
{{next_steps}}

<!-- template: ops-initiative-status-builtin@0.1 -->
