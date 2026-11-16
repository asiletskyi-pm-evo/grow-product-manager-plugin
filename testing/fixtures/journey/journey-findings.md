---
type: cjm-journey
product: zorg
journey: "Повторне замовлення"
owner: ""
reviewed: 2026-05-01
stages:
  - id: s1
    name: "Візит"
    outcome: "repeat visit within 30 days >= 20%"
  - id: s2
    name: "Пошук"
    outcome: "⚠️ TBD"
  - id: s3
    name: "Кошик"
    outcome: "cart -> checkout >= 55%"
  - id: s4
    name: "Оформлення"
    outcome: "checkout -> payment >= 72%"
health:
  - date: "2026-10-05"
    score: 74
    snapshot: "2026-10-05.md"
  - date: "2026-11-02"
    score: 71
    snapshot: "2026-11-02.md"
---

# Zorg: повторне замовлення — фікстура знахідок

## Карта

| id | етап | крок | доріжка | текст | рівень | ціль | parent | код | джерело | клас | дата |
|---|---|---|---|---|---|---|---|---|---|---|---|
| a1 | s1 | | action | Повертається з листа-нагадування | stage | | | | walkthrough 2026-10-12, крок 1 | observed | 2026-10-12 |
| m1 | s1 | | metric | Повторний візит 18% | funnel | | | | дашборд PM | reported | 2026-10-05 |
| p1 | s1 | | pain | Не пам'ятає, що замовляв минулого разу | | | | | feedback-triage 2026-03-01, тема «історія», pain 5.0 | reported | 2026-03-01 |
| p2 | s1 | | pain | Персона: «хочу знижку за повтор» | | | | | persona interview | simulated | 2026-10-20 |
| p3 | s1 | | pain | Довго шукати попереднє замовлення | | | | | | reported | 2026-10-21 |
| p4 | s2 | | pain | Пошук не пам'ятає попередні запити | | | | | feedback-triage 2026-10-30, тема «пошук», pain 4.0 | | 2026-10-30 |
| p5 | s2 | | pain | Підказки пошуку не враховують історію | | | | | walkthrough 2026-10-12, крок 3 | guess | 12.10.2026 |
| p5 | s2 | | pain | Немає кнопки «повторити замовлення» | | | | | walkthrough 2026-10-12, крок 5 | observed | 2026-10-12 |
| e1 | s2 | | experience | Роздратування: усе спочатку | | | | | зі слів PM | reported | 2026-10-25 |
| o1 | s3 | | opportunity | Повторити минуле замовлення в один дотик | | так | | | зі слів PM | | |
| o2 | s3 | | opportunity | Бачити, що змінилось у ціні з минулого разу | | так | | | зі слів PM | | |
| h1 | s3 | | solution | Кнопка «повторити» в історії | | | o1 | | Hypotheses/hypothesis-reorder-button | | |
| h2 | s3 | | solution | Блок «купували раніше» в кошику | | так | o1 | | cjm-research hypotheses 2026-10-31, H5 | | |
| h3 | s3 | | solution | Нагадування про повтор | | | o99 | | зі слів PM | | |
| h4 | s3 | | solution | Персональна знижка на повтор | | | o9 | | зі слів PM | | |
| x1 | s3 | | experiment | A/B блоку «купували раніше» | | | o1 | exp-reorder-block-20261101 | experiment-tracker registry | | |
| i1 | s3 | | initiative | Епік «Повторні покупки» | | | o1 | delivery epic | roadmap-architect | | |
| m2 | s3 | | metric | cart -> checkout 49% | transition | | | | health-check 2026-10-05, 2026-09-28..2026-10-04 | measured | |
| k1 | s3 | | action | Деталі на https://wiki.example.com/zorg/reorder | | | | | зі слів PM | reported | 2026-10-25 |
| g1 | s9 | | goal | Хоче замовити швидше, ніж минулого разу | | | | | зі слів PM | reported | 2026-10-25 |
| g2 | s4 | | pain | ⚠️ немає доказів | | | | | | | |
| o9 | s1 | | opportunity | Знати, коли товар знову в наявності | | | | | зі слів PM | | |
