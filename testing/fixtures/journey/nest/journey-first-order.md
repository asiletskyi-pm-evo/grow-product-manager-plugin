---
type: cjm-journey
created: 2026-11-02
skill: cjm-research
product: zorg
journey: "Перше замовлення"
owner: "Команда оформлення Zorg"
reviewed: 2026-11-02
stages:
  - id: s1
    name: "Візит"
    outcome: "visit -> search >= 45%"
  - id: s2
    name: "Пошук"
    outcome: "search -> cart >= 35%"
  - id: s3
    name: "Кошик"
    outcome: "cart -> checkout >= 55%"
  - id: s4
    name: "Оформлення"
    outcome: "checkout -> payment >= 72%"
  - id: s5
    name: "Оплата"
    outcome: "payment -> paid >= 90%"
health:
  - date: "2026-10-05"
    score: 71
    snapshot: "2026-10-05.md"
  - date: "2026-11-02"
    score: 68
    snapshot: "2026-11-02.md"
tags: [zorg, cjm]
---

# Zorg: перше замовлення

## Карта

| id | етап | крок | доріжка | текст | рівень | ціль | parent | код | джерело | клас | дата |
|---|---|---|---|---|---|---|---|---|---|---|---|
| a1 | s1 | | action | Приходить із пошукової реклами на головну | | | | | walkthrough 2026-10-12, крок 1 | observed | 2026-10-12 |
| mj1 | s1 | | metric | Перших замовлень, оплачених з першої спроби: 81% | journey | | | | аналітика замовлень 2026-11-01 | measured | 2026-11-01 |
| p1 | s2 | Фільтри | pain | Фільтри скидаються після повернення до видачі | | | o1 | | walkthrough 2026-10-12, крок 4 | observed | 2026-10-12 |
| o1 | s2 | | opportunity | Не губити вибір покупця між кроками | | | | | зі слів PM | | |
| m-s2-search-cart | s2 | | metric | search -> cart: 31.0% (база 35.0%, -11.4%) | transition | | | | health-check 2026-11-02, 2026-10-26..2026-11-01 | measured | 2026-11-02 |
| p2 | s3 | | pain | Не видно вартості доставки до оформлення | | | | | feedback-triage 2026-10-30, тема «доставка», pain 7.5 | reported | 2026-10-30 |
| e2 | s4 | | experience | Тривога: чи не задорого вийде з доставкою | | | | | feedback-triage 2026-10-30, тема «доставка», pain 7.5 | reported | 2026-10-30 |
| a5 | s5 | Оплата карткою | action | Вводить дані картки на сторінці оплати | | | | | walkthrough 2026-10-12, крок 7 | observed | 2026-10-12 |
| p5 | s5 | Оплата карткою | pain | Оплата падає без пояснення причини | | | | | feedback-triage 2026-10-30, тема «оплата», pain 8.0 | reported | 2026-10-30 |
| m-s5-payment-paid | s5 | | metric | payment -> paid: 84.0% (база 90.0%, -6.7%) | transition | | | | health-check 2026-11-02, 2026-10-26..2026-11-01 | measured | 2026-11-02 |

## Здоров'я

Останній бал — 68 (2026-11-02).

## Розриви

- Немає.

<!-- judgment footer -->
