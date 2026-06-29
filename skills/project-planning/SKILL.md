---
name: project-planning
version: 0.1.0
description: Планує і прогнозує реалізацію проєкту/місії/ініціативи поза межами кварталу — оцінює сукупний обсяг епіків/фіч, будує граф залежностей і послідовність, рахує тривалість під заданий % зайнятості команди напрямком і вибудовує мульти-квартальний roadmap проєкту з rolling-reforecast. Use when the user asks "скільки займе проєкт", "roadmap проєкту", "послідовність епіків", "залежності фіч", "коли завершимо ініціативу", "% команди на напрямок", "критичний шлях", "переплан проєкту".
---

# Project Planning

Оркестратор планування проєкту/місії (вертикальна вісь: один напрямок крізь час). Оцінює обсяг, будує залежності й критичний шлях, прогнозує тривалість під % зайнятості команди, вибудовує арку (мульти-квартальний roadmap) і **переплановує** її на основі факту (rolling-reforecast). **ШІ — консультант PM.**

Частина planning-suite: дає арки й % allocation у `quarterly-planning`. Інтегрується з `team-ops-reporter` (поточний стан/% done ← `initiative-status`).

## Prerequisites
- `references/local-context-protocol.md` — Step 0 + Planning-секція.
- `references/planning-core.md` — модель, розмітка, мапа цілей.
- `references/dependency-model.md` — DAG епік/фіча, топосорт, **критичний шлях**, цикли.
- `references/capacity-model.md` — обсяг, авто-оцінка, **allocation %**, `тривалість = critical_path_schedule(...)` (розд. 5, 10).
- `references/roadmap-artifacts.md` — формат арки/Gantt проєкту.
- `skills/team-ops-reporter/references/jira-data-protocol.md` — Jira-плумбінг (реюз).
- `references/integration-strategy.md`, `references/persistent-storage.md`, `references/template-protocol.md`.

## Step T — Template Resolution
`artifact_type: roadmap`, `subtype: project-arc`, `product_id`, `language`. Fallback → `roadmap-artifacts.md` розд. 3.

## Modes

| Mode | Вихід |
|------|-------|
| `forecast` | Обсяг + % зайнятості → тривалість і дата завершення |
| `sequence` | Граф залежностей → послідовність + критичний шлях |
| `roadmap` | Мульти-квартальний roadmap проєкту (Gantt) |
| `whatif` | Варіювати % / скоуп → зміна дати |
| `replan` | Rolling-reforecast: факт + план кварталу → перенос невміщеного на майбутнє + дрейф vs baseline |

## Pipeline

### Step 0 — Local context
Per `local-context-protocol.md` + Planning (capacity-правила, спринти, мапа цілей, Development Flow).

### Step 1 — Scope
Вибрати проєкт/місію/ініціативу (ціль EVOCO1-XX, епік або набір епіків).

### Step 2 — Зміст проєкту
Епіки + фічі (CQL за епіком, `getJiraIssue` per-key); обсяг по платформах; **авто-оцінка відсутніх** (`capacity-model` розд. 8). Поточний стан/% done — **делегувати `team-ops-reporter` `initiative-status`**.

### Step 3 — Граф залежностей
Per `dependency-model.md`: вивести з Jira-лінків (Blocks/Relates) + ввід PM → DAG; топосорт; **критичний шлях**; підсвітити цикли/розриви. **Gate** на ручні залежності.

### Step 4 — % зайнятості напрямком
Спитати **максимальний доступний % команди** на напрямок (по платформах). `ефективна_capacity = стеля × %` (`capacity-model` розд. 5). Перевірити, що сума % по активних напрямках ≤100%. **Gate.**

### Step 5 — Прогноз тривалості
`тривалість ≈ critical_path_schedule(обсяг_по_платформах, залежності, ефективна_capacity)` (`capacity-model` розд. 10) → дата завершення + розподіл по кварталах/спринтах.

### Step 6 — Roadmap проєкту
Per `roadmap-artifacts.md` розд. 3: мульти-квартальний Gantt, критичний шлях виділено, прогнозна дата, what-if по %. Збереження workspace + бібліотека; baseline зберегти для дрейфу.

### Replan — rolling-reforecast (режим `replan`)
Тригер: межа кварталу / on-demand / scheduled.
- R1. Поточний стан ← `team-ops-reporter` (`initiative-status` + факт кварталу); committed і **перенесене** ← `quarterly-planning`.
- R2. Лишок = обсяг − done.
- R3. Backlog = лишок − committed_цього_кварталу (вкл. перенесене).
- R4. Ре-секвенс під залежності + % на майбутні періоди.
- R5. Нова дата + **дрейф vs baseline** (slip на N тижнів + чому; перенос елемента критичного шляху = зсув арки).
- R6. Оновити roadmap + ризики; зберегти новий baseline.

## Інтеграція
↔ `quarterly-planning` (вниз: арки + % allocation; вгору: факт+перенесене → `replan`). ← `team-ops-reporter` `initiative-status` (стан/% done). ← `roadmap-architect` (структура). → `diagram-prototyper` (презентація арки). ← `cjm-research`/`brainstorm-features` (нові епіки/фічі).

## Quality Standards
- Не вигадувати залежності — лише Jira-лінки / Development Flow / явний ввід PM; решта = «розрив, оформи».
- Критичний шлях перераховувати при кожному `replan`.
- Оцінки/прогноз — маркер «на підтвердження TL/PM»; рішення за PM.
- Дрейф завжди показувати vs baseline, не лише новий стан.
- Кожна дата/число — з контекстом (% allocation, к-сть спринтів). Мова — `user.language`.

## Additional Resources
`references/dependency-model.md`, `capacity-model.md`, `planning-core.md`, `roadmap-artifacts.md`, `local-context-protocol.md`, `template-protocol.md`, `persistent-storage.md`, `self-improvement.md`; `skills/team-ops-reporter/references/jira-data-protocol.md`.
