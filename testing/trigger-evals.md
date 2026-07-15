# Trigger evals — skill routing test set

Purpose: verify that user phrases trigger the **intended** skill, especially in the known collision groups (CJM trio, prototype pair, roadmap trio). Run after any change to a skill `description` frontmatter, and before releases that touch descriptions.

## How to run

**Manual protocol (baseline):** in a fresh Cowork session with the plugin installed, paste each phrase as a user message. Record which skill triggers (or none). Pass = expected skill; borderline pass = Claude asks a clarifying question naming the expected skill among options.

**Automated (preferred when available):** the `skill-creator` skill ships an eval harness — feed it this table as scenarios (`phrase` → `expected_skill`) and let it benchmark triggering accuracy across N runs. Record the accuracy per group below.

Scoring: each row ✓/✗; group accuracy = ✓ / total. Target: ≥ 90 % per group. Any ✗ → tighten the losing/winning skill descriptions ("Do NOT use" hints), bump PATCH, re-run.

## Test set

### Group A — CJM trio (cjm-research / product-analysis / brainstorm-features)

| # | Phrase | Expected |
|---|--------|----------|
| A1 | проаналізуй CJM-воронку продукту і знайди аномалії | cjm-research |
| A2 | зроби повне CJM-дослідження з гіпотезами | cjm-research |
| A3 | подивись дашборд конверсії за червень і поясни тренд | product-analysis |
| A4 | проаналізуй результати A/B-тесту нового чекаута | product-analysis |
| A5 | analyze CJM funnel data for the checkout stage (data only, no research) | product-analysis |
| A6 | згенеруй гіпотези для росту конверсії з ICE-оцінкою | brainstorm-features |
| A7 | brainstorm features for the reviews page | brainstorm-features |
| A8 | CJM research: anomalies → enrichment → hypothesis backlog | cjm-research |

### Group B — Prototype pair (diagram-prototyper / design-bridge)

| # | Phrase | Expected |
|---|--------|----------|
| B1 | намалюй BPMN-діаграму процесу скарги | diagram-prototyper |
| B2 | зроби швидкий вайрфрейм сторінки відгуків у Mermaid | diagram-prototyper |
| B3 | створи деку з концепту для стейкхолдерів | design-bridge |
| B4 | побудуй hi-fi прототип на нашій дизайн-системі | design-bridge |
| B5 | make a prototype (no DS/brand mentioned, quick visualization) | diagram-prototyper |
| B6 | згенеруй design handoff з a11y-аудитом | design-bridge |
| B7 | згенеруй hi-fi екран фічі через мій дизайн-тулкіт | design-bridge |
| B8 | generate a hi-fi screen using my external design toolkit | design-bridge |
| B9 | намалюй lo-fi блок-схему екрана швидко | diagram-prototyper |

### Group C — Roadmap trio + sprint (roadmap-architect / project-planning / quarterly-planning / sprint-planning)

| # | Phrase | Expected |
|---|--------|----------|
| C1 | наведи лад у структурі: звʼяжи епіки з цілями, розміть фічі | roadmap-architect |
| C2 | побудуй дерево roadmap без прив'язки до кварталів | roadmap-architect |
| C3 | скільки займе місія Brands при 40% команди | project-planning |
| C4 | критичний шлях і послідовність епіків проєкту | project-planning |
| C5 | зібери roadmap на Q3 з capacity-перевіркою | quarterly-planning |
| C6 | plan-vs-actual за минулий квартал | quarterly-planning |
| C7 | що можна взяти у Sprint 52 з беклогу | sprint-planning |
| C8 | roadmap проєкту на наступні 3 квартали | project-planning |
| C9 | розподіли задачі спринта по людях з урахуванням відпусток | sprint-planning |

### Group D — Release semantics (release-manager vs product work)

| # | Phrase | Expected |
|---|--------|----------|
| D1 | зарелізь плагін | release-manager |
| D2 | підготуй реліз v1.31.0 | release-manager |
| D3 | звіт по релізах команди за спринт | product-reporter |
| D4 | які фічі виїхали в реліз каталогу цього тижня | product-reporter |

### Group E — Research vs analysis vs knowledge

| # | Phrase | Expected |
|---|--------|----------|
| E1 | дослідi як Rozetka зробила Q&A на картці товару | product-research |
| E2 | порівняй наш фільтр з галузевими UX-бенчмарками | product-research |
| E3 | збережи цю статтю Baymard у бібліотеку | knowledge-library |
| E4 | які джерела маємо по темі відгуків | knowledge-library |
| E5 | поясни чому впала конверсія КТ минулого тижня | product-analysis |

### Group F — Documents chain (write-concept / requirements-creator / task-creator)

| # | Phrase | Expected |
|---|--------|----------|
| F1 | оформи ідею рейтингу продавця в концепт | write-concept |
| F2 | напиши вимоги до A/B-тесту бейджів | requirements-creator |
| F3 | створи Jira-задачі з цих вимог у Confluence | task-creator |
| F4 | перевір мою специфікацію на повноту | requirements-creator |

### Group G — Attention vs execution (focus-advisor vs planning/analysis skills)

| # | Phrase | Expected |
|---|--------|----------|
| G1 | на чому мені сфокусуватись сьогодні | focus-advisor |
| G2 | ранковий бриф: пошта, календар, задачі | focus-advisor |
| G3 | розбери мою пошту — чи є важливі листи без відповіді | focus-advisor |
| G4 | до яких зустрічей цього тижня треба готуватись | focus-advisor |
| G5 | сформуй фокуси спринта з квартального roadmap | sprint-planning |
| G6 | що можна взяти у Sprint 56 з беклогу | sprint-planning |
| G7 | чи все ок з моїми метриками, глянь по-швидкому | focus-advisor (chains health-check) |
| G8 | проаналізуй воронку за минулий тиждень проти baseline | product-analysis (label fixed 2026-07-03: data-only comparison; cjm-research only if hypotheses/research requested) |
| G9 | що робити з продуктом далі, де великі можливості | focus-advisor (strategy route) |
| G10 | зроби health-check воронки з гіпотезами | cjm-research |

### Group H — Lifecycle trio (experiment-tracker / decision-log / feedback-triage vs neighbors)

| # | Phrase | Expected |
|---|--------|----------|
| H1 | які A/B-тести зараз біжать і що з ними | experiment-tracker |
| H2 | зафіксуй запуск тесту бейджів: фліг BADGES_AB, 50/50 | experiment-tracker |
| H3 | проаналізуй результати A/B-тесту бейджів | product-analysis |
| H4 | нагадай, які тести завислі без рішення | experiment-tracker |
| H5 | напиши вимоги до A/B-тесту нового фільтра | requirements-creator |
| H6 | зафіксуй рішення: розкочуємо бейджі на 100% | decision-log |
| H7 | чому ми відмовились від кастомних шаблонів торік | decision-log |
| H8 | підсумуй зустріч і витягни action items | meeting-processor |
| H9 | розбери скарги продавців за червень — що болить найбільше | feedback-triage |
| H10 | кластеризуй ці support-тікети по темах | feedback-triage |
| H11 | синтезуй ці 12 інтервʼю з користувачами | product-research |
| H12 | збережи цю статтю про churn у бібліотеку | knowledge-library |
| H13 | згенеруй гіпотези з топ-болей фідбеку | brainstorm-features |
| H14 | тренд тем скарг цього кварталу проти минулого | feedback-triage |

## Results log

| Date | Runner | Group accuracies | Failures → action |
|------|--------|------------------|-------------------|
| 2026-07-03 | 2 independent agent runs (descriptions-only simulation), plugin v1.33.0 | A 100 / B 100 / C 100 / D 100 / E 100 / F 100 / G 95→100 | G8: both runs picked product-analysis over cjm-research — eval label was wrong (data-only phrase), fixed the expected column, no description change. 46/46 primary agreement between runs. Baseline recorded before the monolith refactor (v1.34.x). |
| 2026-07-04 | 2 independent agent runs, pre-release v1.36.0 | H 100 (14/14 both runs) | New lifecycle trio routes cleanly vs neighbors (H3→product-analysis, H5→requirements-creator, H11→product-research as expected). No description changes needed. |
| (fill after each run) | | | |

## Maintenance

- New collision discovered in real use → add 2–3 rows to the relevant group (or a new group), then fix descriptions.
- Keep phrases realistic (copy from actual user requests where possible), mixed UA/EN like real usage.
- This file is part of the release definition-of-done for any description-touching release.

> **Log status (2026-07-15).** The last recorded run is 2026-07-04 (pre-v1.36.0). v2.0.0 added
> 6 skills, v2.0.1 rewrote all 29 descriptions, and v2.1.1 changed the routing-relevant guards
> below — none of it is logged here, so the DoD above has been asserted rather than met. The
> next description-touching release must run the groups and add a row, and the run needs a new
> group for the People contour (one-on-one vs meeting-processor, performance-review vs
> product-reporter member-review) plus the v2.1.1 guards: write-concept vs requirements-creator
> ("describe a feature" / "описати фічу"), product-research vs knowledge-library (library lookup).
