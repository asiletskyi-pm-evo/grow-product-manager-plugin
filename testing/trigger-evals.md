# Trigger evals — skill routing test set

Purpose: verify that user phrases trigger the **intended** skill, especially in the known collision groups (CJM trio, prototype pair, roadmap trio). Run after any change to a skill `description` frontmatter, and before releases that touch descriptions.

## How to run

**Manual protocol (baseline):** in a fresh Cowork session with the plugin installed, paste each phrase as a user message. Record which skill triggers (or none). Pass = expected skill; borderline pass = Claude asks a clarifying question naming the expected skill among options.

**Codex CLI (since v3.0.0):** install the branch as a local marketplace, then for each phrase run `codex exec -s read-only` with a **single-line** prompt asking for the bare skill name only (a multi-line prompt argument hangs `codex exec` 0.153 before the session starts). Score on the host's *real* configuration — Codex shares one ~15k-character budget across every listed skill, so a machine with 80 skills shows ~190 characters per description; that is the configuration the descriptions must route on. Runner and scorer: see the v3.0.0 pilot notes in the design workspace.

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
| E1 | дослідi як головний конкурент зробив Q&A на картці товару | product-research |
| E2 | порівняй наш фільтр з галузевими UX-бенчмарками | product-research |
| E3 | збережи цю статтю Baymard у бібліотеку | knowledge-library |
| E4 | які джерела маємо по темі відгуків | knowledge-library |

> E1 named a specific local competitor until v2.4.1; it now says "головний конкурент". The routing signal is unchanged (research verb + a competitor + a product surface), and the phrase no longer ties the fixture to one market.
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

### Group I — Debate mode (brainstorm-features Debate mode vs neighbors)

| # | Phrase | Expected |
|---|--------|----------|
| I1 | проведи дебати про сортування за кредитною ціною | brainstorm-features (Debate mode) |
| I2 | розбери транскрипт дискусії з команди | meeting-processor (NOT debate) |
| I3 | брейншторм фіч для сторінки Q&A | brainstorm-features (standard mode, NOT debate) |
| I4 | зафіксуй рішення після наших дебатів | decision-log |
| I5 | red team цю ідею перед стартом розробки | brainstorm-features (Debate mode) |
| I6 | stress-test our top-3 hypotheses via a role debate | brainstorm-features (Debate mode) |
| I7 | нехай агенти подискутують: чи варто ховати телефони продавців зі сторінки товару | brainstorm-features (Debate mode) |
| I8 | круглий стіл ролей щодо переходу на нову модель тарифів | brainstorm-features (Debate mode) |

### Group J — People contour + v2.1.1 guards (added 2026-07-16 per the log-status note below)

| # | Phrase | Expected |
|---|--------|----------|
| J1 | підготуй мене до 1-1 з аналітиком | one-on-one |
| J2 | розбери транскрипт 1-1 — які сигнали по вигоранню | one-on-one |
| J3 | розбери транскрипт статус-зустрічі команди | meeting-processor |
| J4 | проведи піврічне ревʼю розробника з планом розвитку | performance-review |
| J5 | скільки задач закрив розробник за квартал по Jira | product-reporter (member review) |
| J6 | опиши фічу | write-concept; borderline pass = clarifying question naming write-concept vs requirements-creator |
| J7 | опиши фічу як нумеровані вимоги для розробки | requirements-creator |
| J8 | що каже наша бібліотека джерел про guest checkout | knowledge-library |
| J9 | дослідi, як конкуренти зробили guest checkout | product-research |

### Group K — Team language + annotation (added 2026-07-29, v2.4.0)

Collisions: knowledge-library (glossary/style) vs template-library vs plugin-configurator (setup vs build) vs feedback-triage; diagram-prototyper (annotate) vs design-bridge.

| # | Phrase | Expected |
|---|--------|----------|
| K1 | збери глосарій наших термінів з Confluence і зустрічей | knowledge-library |
| K2 | додай термін «картка товару» в глосарій | knowledge-library |
| K3 | як ми називаємо блок з питаннями на картці товару? | knowledge-library |
| K4 | перевір термінологію в цьому тексті | knowledge-library |
| K5 | навчись нашого стилю письма | knowledge-library |
| K6 | build a glossary of team terms with synonyms | knowledge-library |
| K7 | додай шаблон для вимог | template-library |
| K8 | налаштуй секцію глосарія і стилю в конфігурації плагіна | plugin-configurator |
| K9 | анотуй цей скріншот стрілками | diagram-prototyper |
| K10 | додай стрілки й нумеровані маркери на скрін головної | diagram-prototyper |
| K11 | annotate this screenshot with numbered markers | diagram-prototyper |
| K12 | згенеруй hi-fi екран фічі на нашій дизайн-системі | design-bridge |
| K13 | розбери скарги покупців за липень на теми | feedback-triage |

### Group L — Commands stay out of auto-routing (added 2026-09-04, v2.5.0)

Commands in `commands/` carry `disable-model-invocation: true`; the model must never route a conversation into them. Every row here is a **negative** case: the expected target is a skill (or plain conversation), and any command in the answer is a failure. The command itself is reached only when the user types it.

| # | Phrase | Expected |
|---|--------|----------|
| L1 | який статус плагіна, чи все підключено? | plugin-configurator (Validate) — NOT `status` command |
| L2 | покажи мій конфіг | plugin-configurator (View) — NOT `config` command |
| L3 | перевір налаштування плагіна | plugin-configurator (Validate) — NOT `config` command |
| L4 | зарелізь плагін як patch | release-manager — NOT `release` command |
| L5 | випусти фічу Q&A в реліз наступного спринта | sprint-planning / product-reporter — NOT release-manager, NOT `release` command |
| L6 | перевір термінологію в цьому тексті | knowledge-library — NOT `glossary-lint` command |
| L7 | what is the plugin status | plugin-configurator (Validate) — NOT `status` command |
| L8 | /grow-product-manager:status | `status` command (explicit invocation — the only way in) |
| L9 | вимкни підтвердження перед записом у Confluence | conversation → point to `/grow-product-manager:setup --write-gate off` — NOT the `setup` command itself (added v2.6.0) |

## Results log

| Date | Runner | Group accuracies | Failures → action |
|------|--------|------------------|-------------------|
| 2026-07-03 | 2 independent agent runs (descriptions-only simulation), plugin v1.33.0 | A 100 / B 100 / C 100 / D 100 / E 100 / F 100 / G 95→100 | G8: both runs picked product-analysis over cjm-research — eval label was wrong (data-only phrase), fixed the expected column, no description change. 46/46 primary agreement between runs. Baseline recorded before the monolith refactor (v1.34.x). |
| 2026-07-04 | 2 independent agent runs, pre-release v1.36.0 | H 100 (14/14 both runs) | New lifecycle trio routes cleanly vs neighbors (H3→product-analysis, H5→requirements-creator, H11→product-research as expected). No description changes needed. |
| 2026-07-16 | 2 independent agent runs (descriptions-only simulation), pre-release v2.2.0 | A 100 / B 100 / C 100 / D 100 / E 100 / F 100 / G 100 / H 100 / I 100 / J 100 | None. 80/80 primary agreement between runs; J6 → clarifying question naming write-concept vs requirements-creator in both runs (borderline pass by the group's own definition). New Group I (Debate mode) and Group J (People contour + v2.1.1 guards) route cleanly on first run; the brainstorm-features description change (debate triggers + Do NOT use guard) did not regress Groups A/H. |
| 2026-07-29 | 2 independent agent runs (descriptions-only simulation), pre-release v2.4.0 | B 100 / E 100 / J 100 / K 100 | None. New Group K (team language + annotation) routes cleanly on first run: glossary/style → knowledge-library, setup phrasing → plugin-configurator, annotate → diagram-prototyper without stealing design-bridge hi-fi. Regression re-run limited to groups whose members' descriptions changed (B, E, J — knowledge-library + diagram-prototyper): no regressions. 36/36 phrases, full agreement between runs. |
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

> **Update (2026-07-16, v2.2.0).** Addressed: Group I (Debate mode vs meeting-processor / decision-log / standard brainstorm) and Group J (People contour + the v2.1.1 guards) added; the descriptions-only simulation run over all groups is recorded in the Results log.
