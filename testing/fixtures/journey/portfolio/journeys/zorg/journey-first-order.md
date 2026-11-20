---
type: cjm-journey
created: 2026-11-02
skill: cjm-research
product: zorg
journey: "Перше замовлення"
owner: "Команда оформлення Zorg"
reviewed: 2026-11-10
stages:
  - id: s1
    name: "Візит"
    outcome: "visit -> search >= 45%"
  - id: s2
    name: "Кошик"
    outcome: "cart -> checkout >= 55%"
health:
  - date: "2026-11-02"
    score: 71
    snapshot: "health-check-zorg-2026-11-02.md"
  - date: "2026-11-09"
    score: 74
    snapshot: "health-check-zorg-2026-11-09.md"
published:
  - surface: artifact
    kind: dashboard
    level: page
    id: "zorg-first-order-page"
    url: "https://example.com/zorg/first-order-page"
    version: 2
    published: "2026-11-10T09:00:00Z"
    audience: private
    key: cjm-research/zorg/journey-first-order
tags: [zorg, cjm]
---

# Zorg: перше замовлення

## Карта

| id | етап | крок | доріжка | текст | рівень | ціль | parent | код | джерело | клас | дата |
|---|---|---|---|---|---|---|---|---|---|---|---|
| a1 | s1 | | action | Приходить із пошукової реклами на головну | | | | | walkthrough 2026-10-12, крок 1 | observed | 2026-10-12 |
| p1 | s1 | | pain | Головна довго вантажиться на мобільному | | | | | feedback-triage 2026-10-30, тема «швидкість», pain 6.0 | reported | 2026-10-30 |
| m-s1-visit-search | s1 | | metric | visit -> search: 46.0% (база 45.0%, +2.2%) | transition | | | | health-check 2026-11-09, 2026-11-02..2026-11-08 | measured | 2026-11-09 |
| p2 | s2 | | pain | Не видно вартості доставки до оформлення | | | | | walkthrough 2026-10-12, крок 5 | observed | 2026-10-12 |
| m-s2-cart-checkout | s2 | | metric | cart -> checkout: 56.0% (база 55.0%, +1.8%) | transition | | | | health-check 2026-11-09, 2026-11-02..2026-11-08 | measured | 2026-11-09 |

## Здоров'я

74 на 2026-11-09, +3 за тиждень.

## Розриви

—
