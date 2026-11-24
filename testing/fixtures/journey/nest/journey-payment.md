---
type: cjm-journey
created: 2026-11-05
skill: cjm-research
product: zorg
journey: "Оплата"
owner: "Команда платежів Zorg"
reviewed: 2026-11-10
stages:
  - id: s1
    name: "Вибір способу"
    outcome: "method -> card >= 80%"
  - id: s2
    name: "Дані картки"
    outcome: "card -> confirm >= 66%"
  - id: s3
    name: "Підтвердження"
    outcome: "confirm -> paid >= 92%"
parent: journey-first-order
parent_stage: s5
parent_step: "Оплата карткою"
health:
  - date: "2026-10-05"
    score: 70
    snapshot: "2026-10-05.md"
  - date: "2026-11-02"
    score: 64
    snapshot: "2026-11-02.md"
tags: [zorg, cjm]
---

# Zorg: оплата

## Карта

| id | етап | крок | доріжка | текст | рівень | ціль | parent | код | джерело | клас | дата |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ac1 | s1 | | action | Обирає оплату карткою на сторінці оплати | | | | | walkthrough 2026-10-20, крок 1 | observed | 2026-10-20 |
| mj1 | s1 | | metric | Оплачено з першої спроби: 78% замовлень | journey | | | | аналітика платежів 2026-11-01 | measured | 2026-11-01 |
| pc4 | s1 | | pain | Покупець хотів би оплату частинами | | | | | персона «ощадливий покупець» | simulated | 2026-11-01 |
| pc5 | s1 | | pain | Мало способів оплати | | | | | | | 2026-11-01 |
| an1 | s1 | | anomaly | Сплеск відмов після релізу — критично важливо перевірити | | | | | зі слів PM | measured | 2026-11-03 |
| pc1 | s2 | Дані картки | pain | Форма картки скидає введені дані після помилки CVV | | | o1 | | walkthrough 2026-10-20, крок 3 | observed | 2026-10-20 |
| pc2 | s2 | | pain | Незрозуміло, чому картку відхилено | | | | | feedback-triage 2026-10-28, тема «відмова», pain 7.0 | reported | 2026-10-28 |
| o1 | s2 | | opportunity | Не губити дані картки після помилки | | | | | зі слів PM | | |
| m-s2-card-confirm | s2 | | metric | card -> confirm: 58.0% (база 66.0%, -12.1%) | transition | | | | health-check 2026-11-02, 2026-10-26..2026-11-01 | measured | 2026-11-02 |
| a-s2-card-confirm | s2 | | anomaly | card -> confirm: -12.1% від бази — критично | | | | | health-check 2026-11-02, 2026-10-26..2026-11-01 | measured | 2026-11-02 |
| pc3 | s3 | 3-D Secure | pain | Код підтвердження приходить із запізненням | | | | | feedback-triage 2026-10-28, тема «код», pain 6.5 | reported | 2026-10-28 |
| m-s3-confirm-paid | s3 | | metric | confirm -> paid: 86.5% (база 92.0%, -6.0%) | transition | | | | health-check 2026-11-02, 2026-10-26..2026-11-01 | measured | 2026-11-02 |
| a-s3-confirm-paid | s3 | | anomaly | confirm -> paid: -6.0% від бази — попередження | | | | | health-check 2026-11-02, 2026-10-26..2026-11-01 | measured | 2026-11-02 |

## Здоров'я

Останній бал — 64 (2026-11-02).

<!-- judgment footer -->
