---
type: cjm-journey
created: 2026-11-02
skill: cjm-research
product: zorg
journey: "Повторне замовлення"
owner: "Команда утримання Zorg"
reviewed: 2026-11-05
stages:
  - id: s1
    name: "Повернення"
    outcome: "return -> browse >= 30%"
  - id: s2
    name: "Замовлення"
    outcome: "browse -> order >= 12%"
health:
  - date: "2026-11-02"
    score: 78
    snapshot: "health-check-zorg-2026-11-02.md"
  - date: "2026-11-09"
    score: 64
    snapshot: "health-check-zorg-2026-11-09.md"
tags: [zorg, cjm]
---

# Zorg: повторне замовлення

## Карта

| id | етап | крок | доріжка | текст | рівень | ціль | parent | код | джерело | клас | дата |
|---|---|---|---|---|---|---|---|---|---|---|---|
| p1 | s1 | | pain | Не знаходить минуле замовлення в історії | | | | | walkthrough 2026-10-14, крок 2 | observed | 2026-10-14 |
| p2 | s1 | | pain | Пише в підтримку, щоб повторити кошик | | | | | feedback-triage 2026-10-30, тема «повтор», pain 5.5 | reported | 2026-10-30 |
| p3 | s2 | | pain | Знижка постійного покупця не видна | | | | | product-research 2026-09-20, синтез інтерв'ю | reported | 2026-09-20 |
| p4 | s2 | | pain | Персона скаржиться на ціну доставки | | | | | persona run 2026-10-01 | simulated | 2026-10-01 |
| m-s1-return-browse | s1 | | metric | return -> browse: 24.0% (база 30.0%, -20.0%) | transition | | | | health-check 2026-11-09, 2026-11-02..2026-11-08 | measured | 2026-11-09 |
| a-s1-return-browse | s1 | | anomaly | return -> browse: -20.0% від бази — критично | | | | | health-check 2026-11-09, 2026-11-02..2026-11-08 | measured | 2026-11-09 |
| a-s2-browse-order | s2 | | anomaly | критично важливий browse -> order: +6.0% від бази — позитивна | | | | | health-check 2026-11-09, 2026-11-02..2026-11-08 | measured | 2026-11-09 |
| an1 | s2 | | anomaly | Повторні замовлення в жовтні — критично | | | | | зі слів PM | measured | 2026-10-31 |

## Здоров'я

64 на 2026-11-09, −14 за тиждень.

## Розриви

—
