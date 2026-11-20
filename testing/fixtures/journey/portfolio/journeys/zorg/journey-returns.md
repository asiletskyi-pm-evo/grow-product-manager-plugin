---
type: cjm-journey
created: 2026-07-01
skill: cjm-research
product: zorg
journey: "Повернення товару"
reviewed: 2026-07-01
stages:
  - id: s1
    name: "Заява"
    outcome: "request -> approved >= 80%"
  - id: s2
    name: "Відправка"
    outcome: "⚠️ TBD"
health:
  - date: "2026-11-09"
    score: 66
    snapshot: "health-check-zorg-2026-11-09.md"
tags: [zorg, cjm]
---

# Zorg: повернення товару

## Карта

| id | етап | крок | доріжка | текст | рівень | ціль | parent | код | джерело | клас | дата |
|---|---|---|---|---|---|---|---|---|---|---|---|
| p1 | s1 | | pain | Форма заяви губить фото, деталі на https://example.com/zorg/returns-form | | | | | walkthrough 2026-06-20, крок 3 | observed | 2026-06-20 |
| p2 | s1 | | pain | Покупець просить відповісти на buyer@zorg.example про статус | | | | | feedback-triage 2026-06-25, тема «статус», pain 4.0 | reported | 2026-06-25 |
| g1 | s2 | | pain | ⚠️ немає доказів | | | | | | | |

## Здоров'я

Одна точка — тренду ще немає.

## Розриви

- s2 «Відправка»: немає доказів.
