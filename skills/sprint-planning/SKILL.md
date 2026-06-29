---
name: sprint-planning
version: 0.1.0
description: Допомагає PM ефективно оцінити й провести попереднє планування спринта — формує фокуси з квартального roadmap/місій/проєктів, підсвічує що ГОТОВЕ взяти вже зараз (залежності пройдені), ловить порушення послідовності робіт (напр. клієнтську розробку планують раніше за аналітичне покриття), збирає per-member capacity, аналізує ризик недоробки з минулого спринта, пропонує виконавців для незакріплених задач і наповнює спринт під capacity. Use when "спланувати спринт", "передпланування спринта", "що можна взяти у SEX N", "що готове з беклогу", "перевір залежності спринта", "сформуй фокуси спринта", "розподілити спринт", "хто візьме задачі".
---

# Sprint Planning

Консультант PM на передплануванні спринта (найтонший зріз). Не просто наповнює спринт — **підсвічує готовність і порушення порядку робіт**, рахує capacity по людях, враховує ризик недоробки й пропонує виконавців. **Рішення — за PM.**

Частина planning-suite: бере скоуп із `quarterly-planning` і пріоритет напрямків із `project-planning`; задачі → `task-creator`. Інтегрується з `team-ops-reporter` (минулий спринт ← `sprint-review`+`member-review`; затверджений план → рендериться як `sprint-plan` звіт).

## Prerequisites
- `references/local-context-protocol.md` — Step 0 + Planning (capacity-правила, каденс+якір спринтів, board, Development Flow).
- `references/planning-core.md` — модель, розмітка, статуси, Development Flow.
- `references/capacity-model.md` — per-member capacity (розд. 3), carryover-risk, авто-оцінка, спринтова стеля (розд. 9).
- `references/dependency-model.md` — **work-type DAG + правило готовності** (розд. 4), порушення.
- `references/roadmap-artifacts.md` — формат sprint-плану (демаркація з ops-report).
- `skills/team-ops-reporter/references/jira-data-protocol.md` — Jira-плумбінг (реюз).
- `references/integration-strategy.md`, `references/persistent-storage.md`, `references/template-protocol.md`.

## Step T — Template Resolution
`artifact_type: roadmap`, `subtype: sprint-plan`, `product_id`, `language`. (Звітний sprint-plan — у team-ops-reporter; тут — планувальний.)

## Modes

| Mode | Вихід |
|------|-------|
| `groom` | Передпланування: оцінка + готовність + перевірка залежностей (до коміту) |
| `plan` | Наповнити наступний спринт під capacity + ціль |
| `review` | committed vs done + перенесення (живить carryover-risk) |
| `forecast` | У які спринти ляже залишок кварталу |

## Pipeline

### Step 0 — Local context
Per `local-context-protocol.md` + Planning + Development Flow (work-type послідовність, поріг готовності).

### Step 1 — Scope (3 джерела кандидатів)
Який спринт (дефолт наступний). **Джерела:** (а) беклог; (б) затверджений roadmap кварталу (`quarterly-planning`); (в) **майбутні спринти** — задачі, розкидані по наступних SEX (Ready можна підтягнути раніше / перебалансувати). Jira board id.

### Step 2 — Фокуси спринта
Вивести з активного квартального roadmap + арок проєктів (`project-planning`): які напрямки тягнемо цей спринт і чому. **Gate.**

### Step 3 — Per-sprint capacity по людях
Зібрати у PM прогноз **робочих днів / capacity кожного** (відпустки, частковий день, паралельні напрямки) — `capacity-model` розд. 3. **Gate.**

### Step 3b — Carryover-risk (минулий спринт)
**Делегувати `team-ops-reporter` `sprint-review`+`member-review`** для committed vs done і throughput по людях. Порахувати ризик недоробки (`capacity-model` розд. 3: capacity ÷ залишок) → знизити завантаження ризикових, підсвітити хронічні перевантаження.

### Step 4 — Сканування готовності
Для кожного кандидата перевірити статус передумов по **work-type DAG** (`dependency-model` розд. 4) → **Ready** (передумови пройдені) / **Blocked** (чим і до якого статусу). Приклад: BE+Design+Analytics на ревʼю/в тесті → клієнтська реалізація = Ready.

### Step 5 — Порушення послідовності
Якщо downstream-кандидат планується, а upstream нижче порогу готовності (напр. клієнт раніше за аналітику зі скоупу фічі) → **підсвітити порушення** з поясненням; свідоме підтвердження PM, не жорстке блокування.

### Step 6 — Оцінка + наповнення
Авто-оцінка відсутніх (аналогія); наповнення до спринтової стелі по платформах/людях лише з **Ready**-кандидатів; **sprint-gate** (не перевищувати стелю платформи); ціль спринту. Вільна capacity → **pull-forward** Ready-задач з майбутніх спринтів (зсув синхронізувати з `project-planning` арками).

### Step 6b — Пропозиція виконавців
Для задач без виконавця — запропонувати призначення, **пріоритет тим, у кого ще нема задач / є вільна capacity**; матчинг ролі-платформи; урахування per-member бюджету (Step 3) і ризику (Step 3b). Запис assignee у Jira — **gate**; поважає конвенцію команди (де assignee лишають пустим до взяття в роботу — пропозиція в плані, не в задачі).

### Step 7 — Цикл корекції з PM
Показати, що не влазить / заблоковано → вибір. Перерахунок наживо.

### Step 8 — Артефакти
Sprint-план (Confluence / призначення у Jira-спринт) — **gate перед записом у Jira**. Затверджений план → може рендеритись як `sprint-plan` звіт через team-ops-reporter.

## Quality Standards
- Тільки Ready-кандидати у наповнення; Blocked — з поясненням, не тихо.
- Порушення послідовності — завжди підсвічувати, рішення за PM.
- Per-member: не подвоювати (Assignee/Developer/QA окремо — `jira-data-protocol`).
- Оцінки/призначення — маркер «на підтвердження TL»; рішення за PM.
- Work-type флоу й поріг готовності — з Development Flow команди, не хардкод.
- Запис у Jira — лише після апруву. Мова — `user.language`.

## Additional Resources
`references/capacity-model.md`, `dependency-model.md`, `planning-core.md`, `roadmap-artifacts.md`, `local-context-protocol.md`, `template-protocol.md`, `persistent-storage.md`, `self-improvement.md`; `skills/team-ops-reporter/references/jira-data-protocol.md`.
