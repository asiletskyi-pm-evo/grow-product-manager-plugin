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
| H15 | перегляньмо рішення про бейджі: воно було добрим, чи нам просто пощастило з результатом? | decision-log |
| H16 | revisit the badges decision: was it a good call, or did we just get lucky with the outcome? | decision-log |

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
| L9 | вимкни підтвердження перед записом у Confluence | plugin-configurator or none (conversation) → point to `/grow-product-manager:setup --write-gate off` — NOT the `setup` command itself (added v2.6.0; plugin-configurator accepted since v3.5.0, when it learned to explain the command) |

### Group M — Flow walkthrough vs neighbours (added 2026-09-10, v3.1.0)

Collisions: flow-walkthrough vs design-bridge (Figma review) vs product-analysis (dashboards) vs cjm-research (pipeline) vs diagram-prototyper (annotate).

| # | Phrase | Expected |
|---|--------|----------|
| M1 | пройди шлях покупця у застосунку до створення відгуку | flow-walkthrough |
| M2 | перевір зручність каталогу в реальному застосунку на iPhone | flow-walkthrough |
| M3 | порівняй флоу оформлення замовлення на web і Android | flow-walkthrough |
| M4 | налаштуй adb, щоб проходити флоу на телефоні | flow-walkthrough |
| M5 | проаналізуй дашборд конверсії каталогу | product-analysis |
| M6 | зроби дизайн-рев'ю макета каталогу у Figma | design-bridge |
| M7 | анотуй цей скріншот номерами вимог | diagram-prototyper |
| M8 | CJM-дослідження воронки з гіпотезами | cjm-research |

### Group N — Multi-role legs and test accounts (added 2026-09-11, v3.2.0)

Collisions: flow-walkthrough (legs) vs plugin-configurator (test accounts setup) vs task-creator / decision-log / one-on-one / requirements-creator.

| # | Phrase | Expected |
|---|--------|----------|
| N1 | пройди як покупець, потім як продавець: замовлення → відправка → відгук | flow-walkthrough |
| N2 | прогони шлях покупця на тестовому акаунті з оформленням замовлення | flow-walkthrough |
| N3 | додай тестові акаунти для продукту | plugin-configurator |
| N4 | налаштуй тестові акаунти продавця і покупця | plugin-configurator |
| N5 | створи задачі для фічі відгуків | task-creator |
| N6 | зафіксуй рішення: тестові акаунти лише на проді | decision-log |
| N7 | підготуй мене до 1-1 з продавцем | one-on-one |
| N8 | перевір мою специфікацію фічі тестових акаунтів для продавців | requirements-creator (reworded v3.6.0 — see N9) |
| N9 | перевір мою специфікацію тестових акаунтів | plugin-configurator or requirements-creator — ambiguous: "my test-accounts specification" reads as the configured accounts; the original N8 wording, kept since v3.6.0 |

### Group O — Product landscape vs neighbours (added 2026-09-11, v3.3.0)

Collisions: product-landscape vs product-research (a single competitive report) vs knowledge-library (sources) vs flow-walkthrough (the walk) vs plugin-configurator (Landscape setup).

| # | Phrase | Expected |
|---|--------|----------|
| O1 | просканируй мої застосунки і скажи, які з них конкуренти | product-landscape |
| O2 | хто конкуренти й дотичні у сфері онлайн-покупок | product-landscape |
| O3 | додай продукт у реєстр конкурентів | product-landscape |
| O4 | досліди однакове флоу оформлення замовлення на конкурентах | product-landscape |
| O5 | досліди конкурентів для картки товару | product-research |
| O6 | які джерела маємо по Q&A | knowledge-library |
| O7 | пройди флоу відгуку в застосунку | flow-walkthrough |
| O8 | налаштуй карту конкурентів | plugin-configurator |

### Group R — Roles and hats (added 2026-09-28, v3.5.0)

Collisions: a hat or a role word must never move routing — the skill is chosen by the task, and the hat only changes that run's defaults (`references/role-profiles.md` §4; hat parsing is verified in TC-role-350-hat, not here). «змінити роль» / "set role" belongs to plugin-configurator, not to the typed `/config` or `/setup` commands. Designer-hat phrases about a live flow must not drift to design-bridge. Artifact-dependent rows R15–R20 (design brief, research plan, QBR, board update, the strategy-memo pair) joined in v3.6.0 with their templates.

| # | Phrase | Expected |
|---|--------|----------|
| R1 | подивись як CPO: чи реалістичний план на квартал | quarterly-planning (hat: cpo) |
| R2 | as an analyst, check this A/B test readout | product-analysis (hat: product_analyst) |
| R3 | очима дизайнера пройди флоу оформлення замовлення в застосунку | flow-walkthrough (hat: product_designer) |
| R4 | wear the business owner hat and review last quarter's results | product-reporter (hat: business_owner) |
| R5 | як техлід, розбий ці вимоги на задачі | task-creator (hat: eng_lead) |
| R6 | як дослідник, синтезуй ці інтерв'ю | product-research (hat: ux_researcher) |
| R7 | змінити роль | plugin-configurator |
| R8 | яка моя роль у плагіні | plugin-configurator |
| R9 | set my role to head of product | plugin-configurator |
| R10 | I'm a CPO — what should I focus on this quarter | focus-advisor |
| R11 | як head of product, постав OKR команді на квартал | goal-setter (hat: head_of_product) |
| R12 | as a designer, write the concept for saved searches | write-concept (hat: product_designer) |
| R13 | подивись на цей макет у Figma очима дизайнера | design-bridge |
| R14 | як аналітик, знайди аномалії у воронці CJM | cjm-research (hat: product_analyst) |
| R15 | дизайн-бриф для фічі збережених пошуків | write-concept (subtype design-brief, v3.6.0) |
| R16 | research plan for onboarding interviews | product-research (subtype research-plan, v3.6.0) |
| R17 | QBR за квартал | product-reporter (subtype qbr, v3.6.0) |
| R18 | board update for the quarter | product-reporter (subtype board-update, v3.6.0) |
| R19 | стратегічний меморандум по продукту на рік: ставки і що зупиняємо | write-concept (subtype strategy-memo, v3.6.0) |
| R20 | на чому фокусуватись у кварталі | focus-advisor — the attention memo, not write-concept's strategy memo |

### Group S — Build, opponent, learning (added 2026-10-06, v3.9.0)

Collisions: v3.9.0 changes three `description`s (requirements-creator names AI-feature specs; product-research and quarterly-planning gained the S14 / S15 phrases after the first pass), and its judgment steps (`references/judgment-points.md` §7–§9) bring new words into requests — pre-mortem, kill criteria, eval set, build first, `pm_first` — and none of them may move routing; the task does. A pre-mortem is a concept section (write-concept) while a role debate is brainstorm-features Debate mode; an AI-feature spec with its eval set and tracking plan is requirements-creator, not write-concept or product-analysis; the Spec readiness line comes with task breakdown (task-creator), while a spec check stays requirements-creator Analyze & Improve (F4 and N8 hold); a prototype routes by the descriptions — hi-fi or a Design System is design-bridge, a prototype with no DS named is diagram-prototyper (B5); setting `learning_mode` or `build_first` is plugin-configurator, while "let me tag first" goes to the skill that synthesises; kill criteria for a quarter, and reading them back, are quarterly-planning. An "or" row is ambiguous by the descriptions and accepts either skill.

| # | Phrase | Expected |
|---|--------|----------|
| S1 | додай у концепт збережених пошуків pre-mortem і kill criteria | write-concept |
| S2 | run a pre-mortem on the saved-searches concept | write-concept or brainstorm-features (Debate mode) — no description names a pre-mortem; write-concept renders it as a concept section, Debate mode red-teams the concept |
| S3 | проведи дебати ролей щодо концепту збережених пошуків — нехай Скептик його розіб'є | brainstorm-features (Debate mode) |
| S4 | напиши вимоги до AI-фічі підказок відповідей для продавців з eval set і допустимим рівнем помилок | requirements-creator |
| S5 | AI feature spec for the support chatbot: eval set, kill criteria, tracking plan | requirements-creator — NOT write-concept, NOT product-analysis (the tracking plan is a spec section) |
| S6 | write a concept for an AI shopping assistant — problem, value, success metrics | write-concept — AI words do not move a concept to requirements-creator |
| S7 | чи готова специфікація до розбивки на задачі? | task-creator or requirements-creator — a readiness question reads as a spec check ("check my spec") and as the start of a breakdown |
| S8 | break this spec into Jira tasks and flag what it is missing for readiness | task-creator |
| S9 | перевір мою специфікацію на повноту, перш ніж розбивати на задачі | requirements-creator (Analyze & Improve — F4 and N8 hold) |
| S10 | спершу прототип для ризикованого припущення концепту | diagram-prototyper or design-bridge — no DS named reads as diagram-prototyper (B5); design-bridge, the next step after write-concept and the build-first path, is also correct |
| S11 | build first: a hi-fi prototype on our Design System to test the riskiest assumption | design-bridge |
| S12 | увімкни режим навчання pm_first | plugin-configurator |
| S13 | вимкни build first у налаштуваннях плагіна | plugin-configurator — NOT write-concept or design-bridge |
| S14 | let me tag the first interviews myself, then synthesize them | product-research |
| S15 | set kill criteria for the quarter in our Q4 plan | quarterly-planning — NOT goal-setter |
| S16 | чи спрацювали kill criteria з плану минулого кварталу | quarterly-planning (retro) — NOT product-reporter |

### Group T — Shared-context providers (added 2026-10-08, v3.10.0)

Collisions: v3.10.0 adds two skills. Connecting to a team's shared core, refreshing its bundle or enriching the context with its blocks is context-connect — the plugin's own setup (products, connectors, Obsidian, roles) stays plugin-configurator, and adding a source to the curated library stays knowledge-library. Answering *from* the shared core — who owns what, what a team does, where a rule lives, which missions a team has — is context-navigator; "why did we decide" stays decision-log, a dashboard read stays product-analysis, and "which sources do we have" stays knowledge-library.

| # | Phrase | Expected |
|---|--------|----------|
| T1 | підключи мене до спільного вейлта команди | context-connect |
| T2 | connect me to the team vault | context-connect |
| T3 | налаштуй плагін під мій продукт | plugin-configurator — NOT context-connect |
| T4 | онови мій пакет з ядра | context-connect |
| T5 | додай у бібліотеку цю статтю про чекаут | knowledge-library — NOT context-connect |
| T6 | add a context provider for our shared core MCP | context-connect |
| T7 | збагати мій контекст блоками спільного ядра | context-connect |
| T8 | підключи Obsidian-вейлт | plugin-configurator — NOT context-connect |
| T9 | хто відповідає за модуль відгуків | context-navigator |
| T10 | чому ми вирішили відкласти фічу порівняння | decision-log — NOT context-navigator |
| T11 | подивись дашборд конверсії за вересень | product-analysis — NOT context-navigator |
| T12 | what does team Alpha own | context-navigator |
| T13 | які джерела маємо по чекауту | knowledge-library — NOT context-navigator |
| T14 | де описане правило модерації відгуків | context-navigator |

## Results log

| Date | Runner | Group accuracies | Failures → action |
|------|--------|------------------|-------------------|
| 2026-07-03 | 2 independent agent runs (descriptions-only simulation), plugin v1.33.0 | A 100 / B 100 / C 100 / D 100 / E 100 / F 100 / G 95→100 | G8: both runs picked product-analysis over cjm-research — eval label was wrong (data-only phrase), fixed the expected column, no description change. 46/46 primary agreement between runs. Baseline recorded before the monolith refactor (v1.34.x). |
| 2026-07-04 | 2 independent agent runs, pre-release v1.36.0 | H 100 (14/14 both runs) | New lifecycle trio routes cleanly vs neighbors (H3→product-analysis, H5→requirements-creator, H11→product-research as expected). No description changes needed. |
| 2026-07-16 | 2 independent agent runs (descriptions-only simulation), pre-release v2.2.0 | A 100 / B 100 / C 100 / D 100 / E 100 / F 100 / G 100 / H 100 / I 100 / J 100 | None. 80/80 primary agreement between runs; J6 → clarifying question naming write-concept vs requirements-creator in both runs (borderline pass by the group's own definition). New Group I (Debate mode) and Group J (People contour + v2.1.1 guards) route cleanly on first run; the brainstorm-features description change (debate triggers + Do NOT use guard) did not regress Groups A/H. |
| 2026-07-29 | 2 independent agent runs (descriptions-only simulation), pre-release v2.4.0 | B 100 / E 100 / J 100 / K 100 | None. New Group K (team language + annotation) routes cleanly on first run: glossary/style → knowledge-library, setup phrasing → plugin-configurator, annotate → diagram-prototyper without stealing design-bridge hi-fi. Regression re-run limited to groups whose members' descriptions changed (B, E, J — knowledge-library + diagram-prototyper): no regressions. 36/36 phrases, full agreement between runs. |
| 2026-09-08 | **Codex CLI 0.153.2, live** (`codex exec`, the author's real configuration: 80 skills listed, ~190 chars shown per description), pre-release v3.0.0 — 3 full runs of 102 phrases | run 1 (descriptions rewritten, commands unguarded): overall 91.2 — A 88 / B 100 / C 100 / D 100 / E 100 / F 100 / G 80 / H 100 / I 100 / J 100 / K 92 / **L 44**. run 2 and run 3 (after fixes): **100 / 100 on every group, 102/102 identical answers between runs** | Run-1 failures: L1/L2/L6/L7/L9 and K4 — the five migrated commands are real skills in Codex with no `disable-model-invocation`, and their descriptions captured conversational status/config/terminology/write-gate phrases → every command description now opens with "Typed command … only — never for a conversational …" naming the owning skill. A1 (explicit CJM funnel → product-analysis), G3 (mail cue lost when the lead was trimmed), G7 (quick health glance) → three leads adjusted within the 190-char cut. L8 (`/grow-product-manager:status` typed) correctly routes to the command; L9 → none. |
| 2026-09-08 | **Claude Code 2.1.126, live** (`claude -p --plugin-dir <repo> --max-turns 1`, model claude-opus-4-7, 102 phrases, 4 shards) — replaces the earlier in-context simulation | A–K 100; L 8/9 → **effectively 100**: the one miss is L8 (`/grow-product-manager:status` → `none`), which is the correct Claude answer — a typed command with `disable-model-invocation` is executed by the host, not routed by the model, so "none" is what routing should say (in Codex the migrated command is a skill and `source-command-status` was correct there). J6 → write-concept. | None. Both hosts route the whole set on the v3.0.0 descriptions. |
| 2026-09-10 | **Claude Code, live** (`claude -p --plugin-dir <repo> --max-turns 1`, one run of the 8 Group M phrases), pre-release v3.1.0 | M 100 (8/8) | None. New Group M routes cleanly on first run: M1–M4 → flow-walkthrough (walk, real app on iPhone, cross-platform compare, adb setup); neighbours held — M5 → product-analysis, M6 → design-bridge, M7 → diagram-prototyper, M8 → cjm-research. Codex not re-run this version (drive levels there are `assumed`, see host-matrix). |
| 2026-09-11 | **Claude Code, live** (`claude -p --plugin-dir <repo> --max-turns 1`, Group N, 8 phrases), pre-release v3.2.0 | N 7/8 → **8/8** after one description fix | N4 «налаштуй тестові акаунти продавця і покупця» → flow-walkthrough on run 1 (its description mentioned test accounts, the configurator's did not name them). Fix: «додай/налаштуй тестові акаунти» added to plugin-configurator's UA keywords and a guard «declaring the accounts is plugin-configurator» to flow-walkthrough; re-run N1–N4 → 4/4. Also: host-smoke now counts the skill names the model lists (self-reported counts were 29/32/27 for 30 skills). |
| 2026-09-11 | **Claude Code, live** (`claude -p --plugin-dir <repo> --max-turns 1`, Group O, 8 phrases), pre-release v3.3.0 | O 7/8 → **8/8** after one fix | O8 «налаштуй карту конкурентів» → product-landscape on run 1 (its description opened with «карта конкурентів»). Fix: guard «setup of consent and category is plugin-configurator» in the description and a hand-over line in Step 1; re-run O1–O4 + O8 → 5/5. |
| 2026-09-25 | 2 independent agent runs (descriptions-only simulation over the 31 skill + 5 command descriptions), pre-release v3.4.0 | A 100 / B 100 / C 100 / D 100 / E 100 / F 100 / G 100 / H 100 / I 100 / J 100 / K 100 / L 100 / M 100 / N 100 / O 100 (both runs) | None. v3.4.0 changes no `description` (only the `version` field of every skill), so no live pass is required by the DoD; the simulation confirms the thin-core moves and the Step 0j block left routing untouched. |
| 2026-09-28 | **Claude Code, live** (`claude -p --plugin-dir <repo> --max-turns 1`, current default model), pre-release v3.5.0 — all 140 phrases once, then Groups K, L, N, O, R three times each (majority of 3) | A 8/8 · B 9/9 · C 9/9 · D 4/4 · E 5/5 · F 4/4 · G 10/10 · H 14/14 · I 8/8 · J 9/9 · K 13/13 · L 9/9 · M 8/8 · **N 7/8** · O 8/8 · **R 13/14** | **N8** «перевір мою специфікацію тестових акаунтів» → plugin-configurator 3/3 — reproduced on v3.4.0 `main` (3/3), so pre-existing drift, not a v3.5.0 regression; a description guard in plugin-configurator did not move it and was reverted; open for a follow-up. **R4** "wear the business owner hat and review last quarter's results" → 1/3, while the same task without the idiom and the «як власник бізнесу, …» / "as a business owner, …" forms route 3/3 — the "wear the … hat" idiom disturbs routing; role-profiles §4 now recommends the "as a …" form (no hat phrases in descriptions, by design). **R1** reworded (the first draft «подивись на цей roadmap як CPO» had no task and routed to none on `main` too). **L9** label widened: plugin-configurator now explains `/grow-product-manager:setup --write-gate off`, so routing there is correct. **J6**, **L8** = scorer artefacts (J6 → write-concept; L8 → none is the accepted Claude answer since 2026-09-08). |
| 2026-09-29 | **Claude Code, live** (`claude -p --plugin-dir <repo> --max-turns 1`), pre-release v3.6.0 — all 146 phrases once (misses and rate-limited rows re-run 3×, majority), then Groups B, C, F, G, J, R again after the description fixes | A 8/8 · B 9/9 · C 9/9 · D 4/4 · E 5/5 · F 4/4 · G 10/10 · H 14/14 · I 8/8 · J 9/9 · K 13/13 · L 9/9 · M 8/8 · **N 9/9** · O 8/8 · **R 19/20** | New rows R15 «дизайн-бриф …» → design-bridge, R19 «стратегічний меморандум …» → none, R20 «на чому фокусуватись у кварталі» → quarterly-planning on the first run: write-concept's description gained «дизайн-бриф», «стратегічний меморандум», «мемо рішення», «бізнес-кейс» and the EN forms, focus-advisor's gained «фокус кварталу» / «на чому фокусуватись у кварталі», product-reporter's «QBR», «звіт для борду», "board update" → 3/3 each; neighbours held (quarterly roadmap, decks). **N8** reworded to an unambiguous spec-review phrase (3/3 requirements-creator) and the original wording kept as **N9** accepting either skill — "my test-accounts specification" reads as the configured accounts. R4 is the known weak "wear the … hat" idiom. Seven first-run rows were API rate-limit errors, re-run clean. |
| 2026-09-29 | **Claude Code, live** (`claude -p --plugin-dir <repo> --max-turns 1`), pre-release v3.7.0 — Groups A, G, H, I once (42 phrases) | A 8/8 · G 10/10 · H 16/16 · I 8/8 | None. v3.7.0 changes no description; the new H15–H16 (revisit / "good call or lucky?") route to decision-log, so the resulting check needs no new mode (D25). |
| 2026-10-06 | **Claude Code, live** (`claude -p --plugin-dir <repo> --max-turns 1`), pre-release v3.8.0 — Groups A, B, E, G, H, I, M, O once (72 phrases) | A 8/8 · B 9/9 · E 5/5 · G 10/10 · H 16/16 · I 8/8 · M 8/8 · O 8/8 | None. v3.8.0 changes no description; the regression covers the groups whose skills gained evidence-class steps (design-bridge, diagram-prototyper, flow-walkthrough, product-landscape, knowledge-library). Runner note: a phrase with an apostrophe («рев'ю») breaks an `xargs` driver — use a Python driver. |
| 2026-10-06 | **Claude Code, live** (`claude -p --plugin-dir <repo> --max-turns 1`, run from a neutral directory, Python driver), pre-release v3.9.0 — all 165 phrases once, misses re-run 3× (majority), then Groups C, E, G, H, J, S again after two description fixes | A 8/8 · B 9/9 · C 9/9 · D 4/4 · E 5/5 · F 4/4 · G 10/10 · H 16/16 · I 8/8 · J 9/9 · K 13/13 · L 8/9 · M 8/8 · N 9/9 · O 8/8 · R 20/20 · S 16/16 | S14 «tag the first interviews myself, then synthesize» → none 3/3 and S15 "kill criteria for the quarter in our Q4 plan" → goal-setter 3/3 on the first pass: product-research and quarterly-planning descriptions gained those phrases; after the fix S14 3/3, S15 3/3 and C/E/G/H/J/S unchanged. L8 is the known `status` command row (explicit invocation only). N7 2/3 by majority (pre-existing). |
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
