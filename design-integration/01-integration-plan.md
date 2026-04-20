# Grow PM × Claude Design — Integration Plan

> **Версія:** 0.1 (draft)
> **Дата:** 2026-04-20
> **Автор:** Andrii Siletskyi
> **Ціль:** інтегрувати 7 skills з плагіну `design` Claude у пайплайн `grow-product-manager` так, щоб PM міг (а) готувати презентації та (б) створювати прототипи в рамках концептів, вимог та гіпотез — з контекстом Prom Design System через Figma MCP.

---

## 1. TL;DR

- **Підхід:** гібридний. Залишаємо `design` плагін встановленим окремо (щоб не дублювати код), але додаємо у Grow PM **bridge-скіл** `design-bridge` + **chain-хуки** у `write-concept`, `requirements-creator`, `brainstorm-features`, `diagram-prototyper`.
- **Вхід:** ідея / проблема / гіпотеза / CJM-аномалія / existing Figma frame URL.
- **Вихід:** презентація (.pptx) **та/або** UI-прототип (Figma frame, HTML-mock, або diagram-prototyper artifact) **+** handoff spec **+** a11y-звіт **+** ux-copy для порожніх станів і CTA.
- **Джерело DS:** Figma MCP, авторизований на акаунті Prom (UAPROM LLC + Prom+). Використовуємо `get_libraries`, `search_design_system`, `get_variable_defs`, `get_design_context`, `get_screenshot`, `get_metadata`.
- **Новий артефакт:** `design-package` — папка з PRD, прототипом, handoff, a11y-чеклістом і deck.

---

## 2. Головні сценарії

### 2.1. "Концепт → Презентація"

```
write-concept (Grow PM)
  └─► design:ux-copy               (CTA, empty-states, error-messages для концепту)
      └─► design-bridge:deck-pack  (збирає концепт у .pptx з Prom DS кольорами)
          └─► pptx skill           (рендер презентації)
```

### 2.2. "Концепт → Прототип"

```
write-concept (Grow PM)
  └─► diagram-prototyper (type=Prototype)
      └─► Figma MCP: get_libraries → search_design_system (Prom)
          └─► design:design-system     (перевірка, що всі компоненти — з Prom DS)
              └─► design:accessibility-review (WCAG 2.1 AA для макета)
                  └─► design:design-handoff    (spec для розробки, токени, стейти)
```

### 2.3. "Вимоги → Handoff"

```
requirements-creator (Grow PM)
  └─► design:ux-copy              (микрокопі для всіх станів фічі)
      └─► design:design-critique  (ранній критик вимог з UX-точки зору)
          └─► design:design-handoff (формалізований spec для FE/iOS/Android)
```

### 2.4. "Гіпотеза → Швидкий прототип для A/B"

```
brainstorm-features (Grow PM) → обрана ICE-hypothesis
  └─► diagram-prototyper (Prototype, low-fi)
      └─► design:design-critique  (sanity-check перед A/B)
          └─► design:ux-copy      (копірайтинг варіантів)
```

### 2.5. "CJM-аномалія → Дизайн-дослідження"

```
cjm-research (Grow PM) → аномалія на кроці воронки
  └─► design:research-synthesis (якщо є interview/survey на цьому кроці)
      └─► design:user-research    (план нового дослідження, якщо даних мало)
          └─► write-concept       (концепт рішення)
              └─► diagram-prototyper (прототип)
```

---

## 3. Mapping: 7 design-skills → Grow PM pipeline

| Design skill | Де викликається з Grow PM | Тригер | Вхід | Вихід |
|---|---|---|---|---|
| `design:user-research` | `cjm-research`, `product-research` | "замало даних про крок X", "потрібні інтерв'ю" | voronka step, problem statement | research plan + interview guide |
| `design:research-synthesis` | `meeting-processor`, `product-research` | завантажено купу транскриптів / фідбеку | папка з нотатками, fireflies transcripts | themes + insights + recommendations |
| `design:ux-copy` | `write-concept`, `requirements-creator`, `brainstorm-features` | "готуємо вимоги", "концепт майже готовий" | фіча-спец, tone of voice Prom | мікрокопі: CTA, empty-states, errors, onboarding |
| `design:accessibility-review` | `diagram-prototyper`, `requirements-creator` | після створення прототипу або handoff | Figma frame URL або HTML mock | WCAG 2.1 AA чек-ліст + fix-list |
| `design:design-system` | `diagram-prototyper`, `design-bridge` | створення прототипу, аудит макета | Figma file key Prom DS | consistency report + missing tokens |
| `design:design-critique` | `brainstorm-features`, `write-concept`, `diagram-prototyper` | готовий чернетковий макет / wireframe | Figma link, screenshot | critique по usability/hierarchy/consistency |
| `design:design-handoff` | `requirements-creator`, кінець `diagram-prototyper` | "готуємо до розробки" | фінальний макет Figma | spec: layout, tokens, states, props, анімації |

---

## 4. Новий скіл у Grow PM: `design-bridge`

**Призначення:** єдина точка входу, яка приймає контекст від будь-якого Grow PM скілу і оркеструє потрібну комбінацію design-skills + Figma MCP + pptx.

**Структура:**

```
skills/design-bridge/
├── SKILL.md
├── references/
│   ├── figma-mcp-protocol.md       # як викликати Figma MCP tools
│   ├── prom-ds-tokens.yaml         # кеш токенів Prom DS (оновлюється щотижня)
│   └── handoff-template.md         # шаблон handoff-пакету
└── assets/
    └── prom-ds-screenshots/        # еталонні скріни компонентів Prom
```

**SKILL.md description (draft):**

> Bridge between Grow PM artifacts (concepts, requirements, hypotheses) and Claude Design skills (critique, handoff, a11y, ux-copy, design-system). Use when you need to convert a PM artifact into a presentation, prototype, or dev-handoff with Prom Design System tokens from Figma.
>
> **Triggers:** "create a deck from this concept", "prototype this hypothesis", "prepare handoff for SHOPEX-XXXX", "аудит макета на Prom DS", "презентація фічі", "прототип гіпотези".

**Workflow:**

1. **Step 0** — Local context prerequisite (per `references/local-context-protocol.md`).
2. **Step 1** — Intent classification: deck / prototype / handoff / audit?
3. **Step 2** — Source detection:
   - Figma URL → `get_metadata`, `get_design_context`, `get_screenshot`
   - Confluence concept → `getConfluencePage` → `write-concept`-style parse
   - raw text → build concept first via `write-concept`
4. **Step 3** — DS resolution: `get_libraries(fileKey)` → cache Prom DS library key → `search_design_system(query, includeLibraryKeys)`.
5. **Step 4** — Artifact generation (one or many):
   - **Deck** → template-library (`artifact_type=presentation`) → pptx skill
   - **Prototype** → diagram-prototyper (type=Prototype) з інжекцією Prom tokens
   - **Handoff** → design:design-handoff з Prom tokens
   - **Audit** → design:design-system + design:accessibility-review + design:design-critique
5. **Step 5** — QA gate: мінімум один із `design-critique` або `accessibility-review` **обов'язково** перед публікацією.
6. **Step 6** — Publish: Confluence page, Figma comment, Jira attachment.
7. **Step 7** — Vault save: артефакт у Obsidian `GrowPM/design/{product}/{artifact_type}/...`.

---

## 5. Hook-points у існуючих скілах

Щоб не переписувати скіли, додаємо **опціональний Step D** (Design) наприкінці, ДО Publish-step:

| Skill | Де додати | Що додати |
|---|---|---|
| `write-concept` | після Step 5 (draft), до Step 6 (review) | "Want to generate microcopy / critique from design-bridge?" |
| `requirements-creator` | після Step 4 (sections), до Step 5 (review) | "Run design:design-critique + design:ux-copy over the requirements?" |
| `brainstorm-features` | після ICE-scoring, на обраній гіпотезі | "Quick prototype via diagram-prototyper + design-critique?" |
| `diagram-prototyper` | після генерації макета | **Обов'язково** пропонувати `design:accessibility-review` для type=Prototype |
| `cjm-research` | на ідентифікованій аномалії | "Need design:user-research plan to investigate this step?" |
| `meeting-processor` | після extraction transcript | "Run design:research-synthesis if meeting was user-interview?" |
| `product-analysis` | post-release readout | "Convert readout into presentation via design-bridge?" |
| `feature-task-creator` | перед створенням Jira issues | "Generate design-handoff doc as Design subtask attachment?" |

**Реалізація хуку (приклад для write-concept):**

```markdown
### Step D (optional) — Design enrichment

After the draft is approved by the user, offer:

> Would you like to enrich this concept with design artifacts?
>   [1] UX copy (CTA, empty states, errors) — via design:ux-copy
>   [2] Visual prototype — via diagram-prototyper (type=Prototype)
>   [3] Deck for stakeholders — via design-bridge (deck-pack)
>   [4] Skip

If [1]: pass concept summary + tone-of-voice from local-context → invoke `design:ux-copy`.
If [2]: pass concept + user flow → invoke `diagram-prototyper` with Prom DS file key.
If [3]: pass concept + audience profile → invoke `design-bridge` with intent=deck.
```

---

## 6. Data flow: Figma MCP → design skills

```
┌─────────────────────┐
│ User / Grow PM skill │
└──────────┬──────────┘
           │ figma_url / fileKey / query
           ▼
┌──────────────────────────────┐
│  design-bridge:SKILL.md       │
│  Step 3: DS resolution        │
└──────────┬────────────────────┘
           │
    ┌──────┴───────────────────────────────────────┐
    ▼                                               ▼
┌────────────────────────┐           ┌──────────────────────────┐
│ Figma MCP              │           │ references/              │
│  • whoami              │           │  prom-ds-tokens.yaml     │
│  • get_libraries       │◄──cache──►│  (fallback, оффлайн)     │
│  • search_design_system│           └──────────────────────────┘
│  • get_variable_defs   │
│  • get_design_context  │
│  • get_screenshot      │
│  • get_metadata        │
└──────────┬─────────────┘
           │ tokens, components, screenshots
           ▼
┌──────────────────────────┐
│ design:* skills          │
│  accessibility-review    │
│  design-system           │
│  design-handoff          │
│  design-critique         │
│  ux-copy                 │
└──────────┬───────────────┘
           ▼
       Artifact
    (.pptx / .md / Figma comment / Jira)
```

---

## 7. Roadmap (6 кроків)

| # | Крок | Delivery | Effort | Owner | Статус |
|---|------|----------|--------|-------|--------|
| 1 | Prom DS tokens cache (YAML) через `get_libraries` + `search_design_system` | `references/prom-ds-tokens.yaml` | M | PM + Designer | 🔜 Part 2 цього пакета |
| 2 | `design-bridge` SKILL.md + `figma-mcp-protocol.md` | новий скіл у v1.10.0 | M | PM | 🔜 |
| 3 | Step D hooks у 4 скілах (concept, requirements, brainstorm, diagram) | patch existing SKILL.md | S | PM | 🔜 |
| 4 | `local-context.md` оновлення — Design секція | `local-context.md` | S | PM | 🔜 Part 4 |
| 5 | Приклад end-to-end: Q&A Epic → прототип → handoff → deck | `examples/qa-epic-design-flow.md` | M | PM | Post-MVP |
| 6 | Auto-save design artifacts у Obsidian Vault | update `vault-protocol.md` | S | PM | Post-MVP |

---

## 8. Acceptance criteria

- [ ] При `write-concept` з'являється опція "Design enrichment" і викликає design-skills.
- [ ] `diagram-prototyper type=Prototype` автоматично підтягує токени Prom DS з Figma MCP.
- [ ] Handoff документ містить Prom token names (не hex-коди).
- [ ] A11y-звіт має WCAG 2.1 AA критерії і посилання на Figma frame.
- [ ] Deck використовує Prom brand colors (з токенів DS).
- [ ] Всі артефакти зберігаються у Obsidian Vault `GrowPM/design/`.
- [ ] `design-bridge` працює у двох режимах: online (Figma MCP) і offline (YAML-кеш).

---

## 9. Risks & open questions

1. **Figma MCP seat.** Акаунт має `View` seat для UAPROM LLC і Prom+. Для `get_variable_defs` може бути потрібен Full seat — треба перевірити на живому файлі.
2. **File key Prom DS.** Наразі не зафіксовано `prom_ds_file_key` у local-context — треба знайти і додати (див. Part 3, розділ "Як знайти file key").
3. **design плагін встановлений окремо.** Якщо користувач не встановить `design` плагін, треба graceful fallback — скіли в Grow PM мусять перевіряти наявність через `search_plugins`.
4. **Prom DS не задокументована в одному файлі.** Можливо, компоненти розкидані по кільком Figma-файлам. Part 2 (DS spec YAML) треба наповнювати ітеративно.
5. **Tone of voice Prom** — потрібна коротка гайдлайн-секція у local-context (наразі відсутня). Part 4 додає placeholder.

---

## 10. Related files у цьому пакеті

- **Part 2:** `02-prom-design-system-spec.yaml` — специфікація Prom DS (токени + компоненти + патерни + a11y + copy).
- **Part 3:** `03-figma-mcp-config.md` — мапа Figma MCP інструментів на design-skills + готові промпти.
- **Part 4:** `04-local-context-design-section.md` — готовий патч для `local-context.md` з Design-секцією.
- **Part 5:** `05-presentation-logic.md` — логіка створення презентацій (4 subtypes × DS theme × template-library) у режимі `design-bridge:deck-pack`. Включає workflow, тригер-матрицю, slide-by-slide outlines, приклад end-to-end flow.
- **Part 6:** `06-pptx-theme-prom.yaml` — map Prom DS токенів (Part 2) на python-pptx theme: colors, typography, 7 master layouts (title / section / two-col / metric / chart / quote / cta), chart palette, QA rules.
