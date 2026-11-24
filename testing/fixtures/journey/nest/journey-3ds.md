---
type: cjm-journey
created: 2026-11-08
skill: cjm-research
product: zorg
journey: "3-D Secure"
owner: "Команда платежів Zorg"
reviewed: 2026-11-12
stages:
  - id: s1
    name: "Перенаправлення до банку"
    outcome: "redirect -> code >= 95%"
  - id: s2
    name: "Введення коду"
    outcome: "⚠️ TBD"
parent: "[[journey-payment]]"
parent_stage: s3
parent_step: "3-D Secure"
health: []
tags: [zorg, cjm]
---

# Zorg: 3-D Secure

## Карта

| id | етап | крок | доріжка | текст | рівень | ціль | parent | код | джерело | клас | дата |
|---|---|---|---|---|---|---|---|---|---|---|---|
| q1 | s1 | | pain | Сторінка банку не відкривається в застосунку | | | | | walkthrough 2026-10-22, крок 2 | observed | 2026-10-22 |
| q2 | s2 | Код | pain | Код із SMS не підходить з першого разу | | | | | feedback-triage 2026-10-28, тема «код», pain 6.0 | reported | 2026-10-28 |

<!-- judgment footer -->
