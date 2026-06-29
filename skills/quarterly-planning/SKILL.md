---
name: quarterly-planning
version: 0.1.0
description: Збирає квартальний roadmap, аналізує виконання попереднього кварталу й оцінює реалістичність плану під capacity команди. Use when the user asks to "зібрати roadmap на квартал", "quarterly planning", "plan-vs-actual кварталу", "retro кварталу", "capacity плану", "що команда встигне", "оцінити реалістичність плану на квартал".
---

# Quarterly Planning

Оркестратор квартального планування (горизонтальна вісь: один період через усі напрямки). Збирає факт попереднього кварталу, рахує capacity на новий, формує драфт плану з авто-оцінкою, проганяє через capacity-gate, веде PM через корекцію скоупу й генерує артефакти. Сам не аналізує й не рахує метрики — делегує. **ШІ — консультант PM:** пропонує й підсвічує, рішення за користувачем.

Частина planning-suite: `roadmap-architect` (структура) → **`quarterly-planning`** (квартал) → `sprint-planning` (спринт); `project-planning` дає арки/% allocation. Інтегрується з `team-ops-reporter` (звітність — джерело факту).

## Prerequisites

Перед стартом прочитати й виконати:
- `references/local-context-protocol.md` — Step 0: local-context, активний продукт, Planning-секція.
- `references/planning-core.md` — модель Ціль→Initiative→Епік→Фіча, конвенція розмітки, нормалізація статусів, мапа цілей, Development Flow.
- `references/capacity-model.md` — формула стелі, 4 входи, allocation %, платформні слайси, авто-оцінка, пороги gate (85/100%).
- `references/dependency-model.md` — залежності/послідовність (для перенесення незавершеного).
- `references/roadmap-artifacts.md` — формат roadmap-сторінки, Gantt, живий дашборд.
- `skills/team-ops-reporter/references/jira-data-protocol.md` — Jira-плумбінг (мапа полів, JQL, екстракція). **Реюз, не дублювати.**
- `references/integration-strategy.md`, `references/persistent-storage.md`, `references/template-protocol.md`.

Planning-секція local-context: склад команди + capacity-правила, спринти (каденс+якір+board id), мапа цілей, пороги gate, Development Flow.

## Step T — Template Resolution
Per `references/template-protocol.md`: `artifact_type: roadmap`, `subtype: quarterly | retro`, `product_id`, `language`. Fallback → структура з `roadmap-artifacts.md`.

## Modes

| Mode | Кроки | Вихід |
|------|-------|-------|
| `retro` | 1–2 | Plan-vs-actual попереднього кварталу + уроки + калібрований baseline |
| `plan` | 1, 3–5 | Драфт roadmap зі світлофором capacity |
| `full` (default) | 1–6 | Опублікований roadmap + живий дашборд |
| `refresh` | 2 + 6 | Оновлені статуси у наявних артефактах |

## Pipeline

### Step 0 — Local context
Per `local-context-protocol.md`. Якщо Planning-секції немає → chain до `plugin-configurator` (Planning setup: команда, спринти, baseline, мапа цілей, пороги, Development Flow), запропонувати зберегти.

### Step 1 — Scope
`AskUserQuestion`: квартал; режим; формат (Confluence + дашборд за замовч.). Визначити попередній квартал (retro) і цільовий (plan).

### Step 2 — Збір факту (retro)
**Делегувати `team-ops-reporter` `quarter-review`** для plan-vs-actual попереднього кварталу (закриті епіки/фічі, релізи, по напрямках). Поверх:
- Інвентар фіч: CQL `space={space} AND label="q{N-1}-{рік}" AND type=page` (`planning-core` regex розбору назв).
- Нормалізація статусів фіч (`planning-core`) → done/in_progress/planned/blocked + причини зривів.
- **Калібрування baseline** velocity по факту (`capacity-model` розд. 4; velocity з Jira-дошки board id).
**Gate:** показати retro, підтвердити/виправити.

### Step 3 — Capacity (4 входи, кожен з gate)
Per `capacity-model.md` розд. 2–5: (3a) команда + % залученості (з local-context або опит; Jira-метчинг; зберегти оновлення); (3b) спринти періоду (board id / якір; підтвердити або спрогнозувати); (3c) velocity (калібр. зі Step 2 + підтвердження PM); (3d) відпустки (календар + опит → доступність, дефолт 0.9). **% allocation по напрямках** ← з `project-planning` (сума ≤100%). Вихід: стеля по платформах.

### Step 4 — Драфт + capacity-gate
1. План = перенесене незавершене (Step 2) + нове (лейба `q{N}`).
2. **Авто-оцінка за аналогією** для фіч без оцінки (`capacity-model` розд. 8; прапор «на підтвердження TL»).
3. **Capacity-gate** на рівні платформних слайсів (`capacity-model` розд. 6–7): demand vs стеля, світлофор 85/100%.
4. Пріоритезація (ICE/RICE) кандидатів понад стелю.

### Step 5 — Корекція скоупу (цикл із PM)
Якщо платформа над стелею — **показати конкретні напрямки→епіки→фічі, що не влазять** (з оцінками) і дати вибір (інтерактивний capacity-gate з `roadmap-artifacts` розд. 5; перемикачі фіч/платформних слайсів). Перераховувати після кожної правки. Повторювати до впевненості PM. Рішення — за PM.

### Step 6 — Артефакти + збереження
Per `roadmap-artifacts.md`: (1) **Confluence-roadmap** (фокуси + Gantt + дерево, фічі `код—назва`) — публікація **після апруву**; (2) **живий дашборд**; (3) лейби `q{N}` на епіки (`editJiraIssue`, зберігаючи наявні); (4) збереження workspace + бібліотека (драфт/фінал окремо).

## Інтеграція з team-ops-reporter
- Факт кварталу ← `quarter-review` (не переписувати fetch).
- Затверджений roadmap → може рендеритись як звіт для стейкхолдерів через team-ops-reporter.
- Спільний Jira-плумбінг — `jira-data-protocol.md`.

## Skill Chaining
← `project-planning` (арки + % allocation) · ← `roadmap-architect` (чиста структура) · → `task-creator` (задачі з плану) · → `sprint-planning` (найближчий спринт) · → `diagram-prototyper` (презентація) · ← `meeting-processor` (рішення у фокуси).

## Quality Standards
- Human-in-the-loop: кожен вхід через gate «підтверди/виправ».
- AI-оцінки/рекомендації — маркер «на підтвердження TL/аналітика»; рішення за PM.
- Перевантаження = показати сутності + дати вибір, ніколи голі SP.
- Фічі — списком `код — назва`.
- Платформна готовність: не вимагати крос-платформний запуск, якщо не критично.
- Драфт ≠ фінал: запис у Confluence/Jira лише після апруву.
- Кожне число — з inline-періодом. Мова — `user.language`.

## Additional Resources
`references/planning-core.md`, `capacity-model.md`, `dependency-model.md`, `roadmap-artifacts.md`, `local-context-protocol.md`, `template-protocol.md`, `persistent-storage.md`, `self-improvement.md`; `skills/team-ops-reporter/references/jira-data-protocol.md`.
