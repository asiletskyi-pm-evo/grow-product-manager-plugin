---
name: roadmap-architect
version: 0.1.0
description: Підтримує канонічну структуру роботи — мапить місії/цілі → ініціативи → епіки → фічі, стежить за розміткою (лейби, назви, звʼязки), знаходить розриви й генерує дерево roadmap. Use when "навести лад у структурі", "розмітити епіки/фічі", "знайти розриви розмітки", "побудувати дерево roadmap", "звʼязати епік з ціллю", "структура напрямків".
---

# Roadmap Architect

Хранитель структури (фундамент, поза часом). Мапить ієрархію Ціль→Initiative→Епік→Фіча, **enforce конвенції розмітки**, знаходить розриви й будує дерево структури. Не планує квартал/спринт і не торкається capacity — лише цілісність структури. **Рішення — за PM.**

Дає чисту структуру решті planning-suite. Інтегрується з `team-ops-reporter` (Jira-плумбінг) та `cjm-research`/`brainstorm-features` (нові кандидати).

## Prerequisites
- `references/local-context-protocol.md` — Step 0 + Planning (мапа цілей, конвенція розмітки, Development Flow).
- `references/planning-core.md` — канон-модель, конвенція назв/лейб, нормалізація, мапа цілей.
- `references/dependency-model.md` — звʼязки епік/фіча (для дерева й розривів).
- `references/roadmap-artifacts.md` — формат дерева структури + звіт розривів.
- `skills/team-ops-reporter/references/jira-data-protocol.md` — Jira-плумбінг (реюз).
- `references/integration-strategy.md`, `references/persistent-storage.md`, `references/template-protocol.md`.

## Modes

| Mode | Вихід |
|------|-------|
| `audit` | Звіт розривів розмітки (без кварталу/цілі/коду, фічі-сироти, порушення назв) |
| `map` | Звʼязати/проставити: епік→ціль, фіча→епік, лейби (з апрувом) |
| `tree` | Дерево структури Ціль→Initiative→Епік→Фіча (вся структура, без квартального скоупу) |
| `onboard` | Зареєструвати нову місію/епік/фічу з правильною розміткою |

## Pipeline

### Step 0 — Local context
Per `local-context-protocol.md` + мапа цілей + конвенція розмітки (`planning-core`).

### Step 1 — Scope
Режим + охоплення (які цілі/ініціативи/епіки).

### Step 2 — Pull структури
CQL за лейбами `epic`/`feature` + `getJiraIssue` епіки per-key + мапа цілей (`planning-core` розд. 4). Звʼязки — `dependency-model`.

### Step 3 — Валідація розмітки
Знайти: фічі/епіки без кварталу, без цілі, порушення конвенції назв (`planning-core` regex), фічі-сироти (без епіка), неоформлені залежності (розриви графа).

### Step 4 — Map (режим `map`)
Запропонувати фікси лейб/звʼязків (епік→ціль, фіча→епік, q-лейби). **Gate перед записом** у Jira/Confluence; зберігати наявні лейби.

### Step 5 — Tree (режим `tree`)
Згенерувати дерево Ціль→Initiative→Епік→Фіча (фічі `код—назва`) + звіт розривів. Per `roadmap-artifacts.md` розд. 4. Збереження workspace + бібліотека.

## Quality Standards
- Не вигадувати звʼязки — лише Jira-лінки / мапа цілей / явний ввід PM; решта = «розрив, оформи».
- Конвенції — з `planning-core`/local-context, не хардкод.
- Фічі — `код — назва` списком.
- Запис у Jira/Confluence — лише після апруву PM. Мова — `user.language`.

## Skill Chaining
→ `quarterly-planning` / `project-planning` (віддає чисту структуру) · ← `cjm-research` / `brainstorm-features` (нові епіки/фічі) · → `task-creator` (декомпозиція).

## Additional Resources
`references/planning-core.md`, `dependency-model.md`, `roadmap-artifacts.md`, `local-context-protocol.md`, `template-protocol.md`, `persistent-storage.md`, `self-improvement.md`; `skills/team-ops-reporter/references/jira-data-protocol.md`.
