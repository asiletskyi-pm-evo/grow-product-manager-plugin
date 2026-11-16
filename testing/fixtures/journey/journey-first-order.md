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
    outcome: "⚠️ TBD"
health: []
tags: [zorg, cjm]
---

# Zorg: перше замовлення

## Карта

| id | етап | крок | доріжка | текст | рівень | ціль | parent | код | джерело | клас | дата |
|---|---|---|---|---|---|---|---|---|---|---|---|
| a1 | s1 | | action | Приходить із пошукової реклами на головну | | | | | walkthrough 2026-10-12, крок 1 | observed | 2026-10-12 |
| t1 | s1 | | touchpoint | Головна сторінка, мобільний веб | | | | | walkthrough 2026-10-12, крок 1 | observed | 2026-10-12 |
| m-s1-visit-search | s1 | | metric | visit -> search: 44.0% (база 45.0%, -2.2%) | transition | | | | health-check 2026-11-02, 2026-10-26..2026-11-01 | measured | 2026-11-02 |
| e1 | s2 | | experience | Багато зусиль, щоб звузити видачу | | | | | feedback-triage 2026-10-30, тема «фільтри», pain 6.0 | reported | 2026-10-30 |
| p1 | s2 | Фільтри | pain | Фільтри скидаються після повернення назад до видачі | | | o1 | | walkthrough 2026-10-12, крок 4 | observed | 2026-10-12 |
| o1 | s2 | | opportunity | Не губити вибір покупця між кроками | | | | | зі слів PM | | |
| m-s2-search-cart | s2 | | metric | search -> cart: 31.0% (база 35.0%, -11.4%) | transition | | | | health-check 2026-11-02, 2026-10-26..2026-11-01 | measured | 2026-11-02 |
| a-s2-1 | s2 | | anomaly | search -> cart: -11.4% від бази — попередження | | | | | health-check 2026-11-02, 2026-10-26..2026-11-01 | measured | 2026-11-02 |
| p2 | s3 | | pain | Не видно вартості доставки до оформлення | | | o2 | | feedback-triage 2026-10-30, тема «доставка», pain 7.5 | reported | 2026-10-30 |
| p3 | s3 | | pain | Покупці питають у підтримці про строки доставки | | | o2 | | product-research 2026-09-20, синтез інтерв'ю | reported | 2026-09-20 |
| o2 | s3 | | opportunity | Покупець знає повну ціну й строк доставки ще в кошику | | так | | | зі слів PM | | |
| h1 | s3 | | solution | Калькулятор доставки в кошику | | | o2 | | Hypotheses/hypothesis-delivery-calculator | | |
| h2 | s3 | | solution | Безкоштовна доставка від порогу, показана в кошику | | | o2 | | cjm-research hypotheses 2026-10-31, H3 | | |
| h3 | s3 | | solution | Строк доставки на картці товару | | | o2 | | Hypotheses/hypothesis-delivery-date-on-card | | |
| x1 | s3 | | experiment | A/B калькулятора доставки | | | h1 | exp-delivery-calc-20261020 | experiment-tracker registry | | |
| i1 | s3 | | initiative | Епік «Прозора доставка» | | | p2 | PROJ-1234 | roadmap-architect PROJ-1234 | | |
| m-s3-cart-checkout | s3 | | metric | cart -> checkout: 52.0% (база 50.0%, +4.0%) | transition | | | | health-check 2026-11-02, 2026-10-26..2026-11-01 | measured | 2026-11-02 |
| e2 | s4 | | experience | Тривога: чи не задорого вийде з доставкою | | | | | feedback-triage 2026-10-30, тема «доставка», pain 7.5 | reported | 2026-10-30 |
| m-s4-checkout-payment | s4 | | metric | checkout -> payment: 70.0% (база 72.0%, -2.8%) | transition | | | | health-check 2026-11-02, 2026-10-26..2026-11-01 | measured | 2026-11-02 |
| g1 | s5 | | pain | ⚠️ немає доказів | | | | | | | |

## Здоров'я

Тренду ще немає — `health` порожнє.

## Розриви

- s5 «Оплата»: немає доказів, метрика результату `⚠️ TBD`.

<!-- judgment footer -->
