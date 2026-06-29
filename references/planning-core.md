# planning-core.md

> Спільний reference planning-suite. Канонічна модель сутностей, конвенція розмітки, нормалізація статусів, мапа цілей і Development Flow. Споживають усі чотири скіли suite. `roadmap-architect` — enforce; решта — read.

---

## 1. Канонічна ієрархія

```
Місія / Ціль (Atlas Goal, напр. EVOCO1-XX)
  └── Initiative / Напрямок (логічна група; опційно — Jira issue type Initiative, lvl вище Epic)
        └── Епік (Jira, hierarchy level 1)
              └── Фіча (Confluence-сторінка з лейбою + код у назві)
```

Задачі рівня Story/Task **поза скоупом roadmap** (вони — рівень sprint-planning, work-type усередині фічі).

---

## 2. Конвенція розмітки (єдине джерело правди для авто-збірки)

**Фіча (Confluence page):**
- Назва: `{PROJ}-{епік}.{фіча}[.{суб}] - {людська назва}` (напр. `SHOPEX-6610.5 - Q&A - YouTube у тредах`).
- Лейби: `feature`, `q{N}-{рік}` (квартал, де ведеться/планується робота; може бути кілька), командна лейба.
- Поле статусу в тілі: рядок `Статус: {значення}` з контрольованого словника (розд. 3).

**Епік (Confluence page + Jira issue):**
- Confluence-назва: `Epic - {PROJ}-{епік} - {назва}`; лейби `epic`, `q{N}-{рік}`.
- Jira: лейба `q{N}-{рік}` на епіку (для читабельності кварталу з Jira).

**Парсинг коду з назви фічі:** `^(?:Epic - )?{PROJ}-(\d+)((?:\.\d+)*)\s*-\s*(.+)$` → `epicKey`, `featureCode`, `name`.

> Якщо у сутності бракує кварталу/цілі/коду — це **розрив розмітки** (флаг від `roadmap-architect`), а не привід вигадувати звʼязок.

---

## 3. Нормалізація статусів (контрольований словник)

Тіла фіч/епіків містять різні формулювання → зводити до 4 канонів:

| Канон | Сигнали |
| --- | --- |
| `done` | Done, Готово, Закінчено, «запущено на 100%», Closed |
| `in_progress` | в розробці, Запущено (rollout/A-B), Розкатується, In dev |
| `planned` | Draft, Requirements, «не починали», готується, To Do |
| `blocked` | «чекаємо деталей», заблоковано, явні перешкоди |

Jira-статус епіка береться з `statusCategory.key`: `done`→done, `indeterminate`→in_progress, `new`→planned.

---

## 4. Мапа цілей (епік → Ціль)

Atlas Goals не запитуються через MCP → тримати мапу в local-context (Planning → goal_map). Приклад (FET):

| Ціль | Епіки |
| --- | --- |
| EVOCO1-25 (Конверсія/каталог/бренди) | 10272, 5783, 4950, 10452, 7930, 11300, 11240 |
| EVOCO1-3 (Відгуки про товари) | 3080, 11300 |
| EVOCO1-22 (Q&A) | 6610 |
| EVOCO1-23 (Порівняння товарів) | (епік порівняння) |
| EVOCO1-24 (Новий сегмент) | 4750 |
| — Feedback Ecosystem | 3930, 9534, 9557, 9294 |

---

## 5. Development Flow (флоу розробки команди)

Збирається на онбордингу (`plugin-configurator` → Planning setup), зберігається в local-context → Planning → development_flow. Структура:

```yaml
development_flow:
  work_types: [Requirements, Design, BE, Analytics, Client, QA, Release]
  sequence:                      # ребра DAG: передумова → наступник
    Design: [Requirements]
    BE: [Design]
    Analytics: [Design]
    Client: [BE, Analytics]
    QA: [Client]
    Release: [QA]
  parallel: [[BE, Analytics]]    # що йде одночасно
  ready_threshold: [on review, in test, ready for test, done, closed]
  platform_notes: "iOS/Android client залежать від BE"
  exceptions: "..."              # вільний ввід особливостей команди
```

Споживають: `sprint-planning` (готовність/порушення), `project-planning` (макро-залежності), `dependency-model.md` (апарат). `update config` оновлює — детекція підлаштовується автоматично.

---

## 6. Якість / застороги

- Тільки розмічені сутності йдуть у авто-збірку; розриви — підсвічувати, не домислювати.
- Конвенції (назви/лейби/статуси/флоу) override-яться у local-context; не хардкодити в скілах.
- Фічі у будь-якому артефакті — списком `код — назва`, не голими номерами.
- Рекомендації розмітки маркувати «на підтвердження PM».
