# Presentation Creation Logic — Grow PM × Design System × Templates

> **Scope:** логіка створення .pptx-презентацій у межах `design-bridge` скілу з урахуванням (а) Prom Design System і (б) template-library.
> **Owner skill:** `design-bridge` (deck-pack mode).
> **Consumers:** `write-concept`, `requirements-creator`, `product-research`, `product-analysis`, `cjm-research`, `meeting-processor`, standalone user prompt "зроби презентацію...".
> **Related files:**
> - `01-integration-plan.md` § 2.1 (Concept → Deck) і § 4 (design-bridge)
> - `02-prom-design-system-spec.yaml` (джерело токенів DS)
> - `03-figma-mcp-config.md` § 3 (Figma MCP calls)
> - `06-pptx-theme-prom.yaml` (theme map для python-pptx, частина цього пакету)

---

## 1. Ментальна модель

Презентація = **3 шари**, які збираються окремо і склеюються на етапі рендеру:

```
┌────────────────────────────────────────────────────────────┐
│ Layer 3 — Narrative (content)                              │
│   Текст слайдів, факти, цифри, висновки                   │
│   Джерело: контекст попереднього скілу + template          │
├────────────────────────────────────────────────────────────┤
│ Layer 2 — Structure (template)                             │
│   Outline: розбиття на слайди, slide-types, variables      │
│   Джерело: template-library (artifact_type=presentation)   │
├────────────────────────────────────────────────────────────┤
│ Layer 1 — Visual identity (Design System)                  │
│   Theme: кольори, типографіка, spacing, layouts, masters  │
│   Джерело: Prom DS YAML + Figma MCP (опціонально)         │
└────────────────────────────────────────────────────────────┘
```

Кожен шар можна **підміняти окремо:**
- Інший DS → lower layer
- Інший template → middle layer
- Інший контент → upper layer

---

## 2. Типи презентацій (MVP)

| # | Subtype | Коли використовуємо | Source skill | Template ID | Audience | Довжина |
|---|---------|---------------------|--------------|-------------|----------|---------|
| 1 | `feature` | Пітч концепту фічі стейкхолдерам / direction review | `write-concept` | `presentation-builtin-feature` | Product leads, engineering leads, stakeholders | 10-12 слайдів |
| 2 | `research-highlights` | Результати дослідження (конкуренти / юзери / UX-бенчмарки) | `product-research`, `meeting-processor` | `presentation-research-highlights-v1` | Cross-functional, team | 12-18 слайдів |
| 3 | `ab-test-readout` | Чітаут A/B-експерименту: hypothesis → result → decision | `product-analysis` | `presentation-ab-readout-v1` | Direction review, growth syncs | 8-12 слайдів |
| 4 | `release-readout` | Постреліз або sprint review | `product-analysis`, `feature-task-creator` (retro) | `presentation-release-readout-v1` | Team, direction PM lead | 10-15 слайдів |

> **Додаткові subtypes поза MVP:** `okr-check-in`, `epic-kickoff`, `competitor-battle-card`, `cjm-readout`. Додаються через `template-library` без зміни логіки.

---

## 3. Тригер-матриця (коли і як запускається)

### 3.1. Via chain (автоматична пропозиція)

| Source skill | Step | Умова | Пропозиція |
|---|---|---|---|
| `write-concept` | Step D (після draft) | concept approved | "Deck (feature pitch) — 10 слайдів зі стейкхолдерами?" |
| `product-research` | після synthesis | research report готовий | "Research highlights deck (12 слайдів)?" |
| `meeting-processor` | якщо `meeting_type=user-interview` | зібрано >= 3 інсайти | "Зібрати research-highlights deck?" |
| `product-analysis` | якщо `analysis_type=ab-test` | є verdict | "A/B readout deck (8-10 слайдів)?" |
| `product-analysis` | якщо `analysis_type=post-release` | > 2 тижні з релізу | "Release readout deck (10 слайдів)?" |
| `feature-task-creator` | після sprint closing | sprint closed | "Sprint review deck?" |

### 3.2. Via standalone prompt

Триггерні фрази: "зроби презентацію", "готуємо пітч", "презентація для...", "A/B readout на слайдах", "deck", "pptx".

---

## 4. Workflow — `design-bridge` в режимі `deck-pack`

### Step 0 — Local context + DS resolution

1. Follow `references/local-context-protocol.md` (Step 0).
2. Read `design-integration/02-prom-design-system-spec.yaml`.
3. IF `figma_ds_file_key` заповнений → call `get_libraries(fileKey)` + `search_design_system(...)` для freshest tokens.
4. IF offline / немає file key → fallback на YAML кеш (`status: observed/placeholder` помічається у deck footer як "DS tokens: cached 2026-04-XX").

### Step 1 — Intent & source detection

Визначаємо:
- `intent` = `deck` (вже встановлено)
- `subtype` ∈ {feature, research-highlights, ab-test-readout, release-readout}
- `source_type` ∈ {concept, research_report, ab_test_result, release_summary, standalone_brief}
- `source_location` = URL / file / inline text

AskUserQuestion якщо subtype неоднозначний:

> "Який тип презентації?" — показати 4 варіанти + приклад outline у preview.

### Step 2 — Audience profiling

Ask:
- `audience` = direction_review / team_sync / exec / cross-functional
- `language` = uk / en (default з local-context)
- `tone` = default (per tone-of-voice) / formal / casual
- `length_preference` = compact / standard / extended

**Defaults за subtype:**

| Subtype | Audience default | Length default |
|---|---|---|
| feature | direction_review | 10 |
| research-highlights | cross-functional | 14 |
| ab-test-readout | direction_review | 9 |
| release-readout | team | 12 |

### Step 3 — Template resolution (Step T from template-protocol.md)

Виклик `template-library.resolve({artifact_type: "presentation", subtype, product_id, language})`:

1. **T-1:** read `templates.preference` з `local-context.md`.
2. **T-2:** get candidates filtered by `artifact_type=presentation AND status=active`.
3. **T-3:** pick per preference (auto / ask / smart):
   - **auto**: topmost по scope priority (product > user-global > built-in) + version.
   - **ask**: показати ≤ 3 top кандидатів.
   - **smart**: якщо є product-scope match — auto; інакше ask.
4. **T-4:** зчитати `template.body` і зібрати `variables[]` зі Step 2 + Step 4a.
5. **T-5:** після рендеру — append `<!-- template: {template_id}@{version} -->` у outline.md.

**Fallback:** `presentation-builtin-feature` якщо нічого не знайшлося.

### Step 4 — Content assembly

#### Step 4a. Gather variables from source

Source-specific extractors:

| Source | Extractor | Output (фрагмент вар) |
|---|---|---|
| concept (Confluence / .md) | parse PRD → problem, solution, metrics, ask, risks | `problem_statement`, `solution_summary`, `key_metrics[]`, `ask`, `risks[]` |
| research_report | parse insights, themes, recommendations | `key_findings[]`, `themes[]`, `recommendations[]`, `quotes[]` |
| ab_test_result | parse hypothesis, MDE, result, verdict | `hypothesis`, `variants[]`, `primary_metric`, `uplift`, `verdict` |
| release_summary | parse scope, metrics pre/post, learnings | `released_features[]`, `metrics_delta{}`, `learnings[]`, `next_steps[]` |

#### Step 4b. Enrich via design-skills (опціонально)

На цьому етапі (**до** рендеру pptx) запропонувати:

| Design skill | Коли | Що робить |
|---|---|---|
| `design:ux-copy` | subtype ∈ {feature, release-readout} | Полірує headings, CTA-слова у body (per Prom tone-of-voice). Переписує "Click here" → живим голосом. |
| `design:design-critique` | після draft outline | Критикує slide-level hierarchy, читабельність, наявність 1 ідеї на слайд. |
| `design:research-synthesis` | subtype=research-highlights | Якщо є ≥ 10 insights — автоматично групує у теми для слайдів. |

**Gate:** для `audience=exec / direction_review` — `design:design-critique` запускати **примусово** перед фінальним рендером.

#### Step 4c. Visual assets

- **DS tokens** → беремо з Step 0.
- **Icons** → з Lucide (через lucide-react у HTML preview) або вставлені як .svg з шаблону.
- **Charts** → якщо subtype=ab-test-readout або release-readout, генеруємо графіки через pptx skill (вбудований chart API).
- **Figma screenshots (опціонально):** якщо у source є Figma URL, через `get_screenshot(nodeId, fileKey)` витягти прев'ю 3-5 ключових frames і вставити у слайди "Solution / Design" і "Before / After".

### Step 5 — Render pipeline

```
outline.md (Markdown per template)
    │
    ▼
 Deck IR (intermediate representation, JSON):
 {
   meta: { subtype, language, version },
   theme: <from Prom DS>,          # Layer 1
   slides: [
     { layout: "title",    data: {...} },
     { layout: "section",  data: {...} },
     { layout: "two-col",  data: {..., image: "figma://..."} },
     { layout: "metric",   data: {...} },
     { layout: "chart",    data: {chart_type, series} },
     { layout: "quote",    data: {...} },
     { layout: "cta",      data: {...} }
   ]
 }
    │
    ▼
python-pptx rendering (via anthropic-skills:pptx):
  - Apply theme (colors, fonts) from 06-pptx-theme-prom.yaml
  - Iterate slides, pick layout from master
  - Inject images / charts / text
    │
    ▼
.pptx file → /Users/asiletskiy/Documents/Claude/Projects/Grow Product Manager Plagin/
            (or active Obsidian vault: GrowPM/presentations/{product}/{YYYY-MM-DD}-{slug}.pptx)
```

### Step 6 — QA gate

Автоматичні чеки перед сохраненням:

| Check | Rule | Severity |
|---|---|---|
| Contrast | всі text-bg пари ≥ 4.5:1 (body) або 3:1 (large) | error |
| Слайдів > max | len(slides) ≤ length_preference + 20% | warning |
| 1 ідея на слайд | кожен слайд має ≤ 5 bullets або ≤ 60 слів у body | warning |
| Branding | primary color використано ≥ 2 разів (не забули брендинг) | info |
| Empty data | жоден slot з template не лишився {{unfilled}} | error |
| Tone | ux-copy gate passed (якщо run) | info |

**Поведінка:** error → блокує рендер, warning → запит "continue?", info → просто в лог.

### Step 7 — Publish & persistence

1. **File:** save as `.pptx` у workspace папку і у Obsidian Vault (`GrowPM/presentations/{product}/{date}-{subtype}-{slug}.pptx`).
2. **Companion outline.md** (для diff / редакції): зберегти поруч як `.outline.md` з frontmatter `<!-- template: ... -->`.
3. **Obsidian link:** у MOC продукту додати запис "[[YYYY-MM-DD — {title}]]".
4. **Artifact summary** (для chain-назад):
   ```yaml
   deck:
     path: ...
     subtype: ...
     slides: 10
     used_template: presentation-builtin-feature@1.0.0
     ds_version: "1.0.0-draft"
     qa_passed: true
     enrichment: [ux-copy, design-critique]
   ```
5. **Optional publish:**
   - Confluence attachment (якщо source = Confluence page)
   - Jira attachment на epic / ticket
   - Google Slides expor (через pptx → gslides конвертор, поза MVP)

---

## 5. Template outline — 4 subtypes (slide-by-slide)

### 5.1. `feature` — Feature / Concept pitch (10 слайдів)

| # | Layout | Title | Ключовий контент | Variables |
|---|--------|-------|-------------------|-----------|
| 1 | title | {{feature_name}} | Дата, presenter, audience | title, date, presenter |
| 2 | section | Context | Що відбувається в продукті / бізнес-момент | context, product |
| 3 | two-col | Проблема | Проблема + докази (цитати, метрика) | problem_statement, evidence[] |
| 4 | metric | Чому зараз | 2-3 цифри, що показують болі | pain_metrics[] |
| 5 | two-col | Рішення | Ідея + 1 scren Figma (опц.) | solution_summary, figma_preview |
| 6 | section | Як це вимірюємо | KPI + ціль | key_metrics[], target |
| 7 | two-col | MVP scope | In / Out / Future | in_scope[], out_of_scope[] |
| 8 | metric | Очікуваний impact | ICE / uplift estimate | ice_score, uplift_estimate |
| 9 | two-col | Ризики і залежності | Топ-3 ризики + mitigation | risks[] |
| 10 | cta | Ask | Що потрібно від аудиторії | ask |

### 5.2. `research-highlights` — Research highlights (14 слайдів)

| # | Layout | Title | Ключовий контент |
|---|--------|-------|-------------------|
| 1 | title | {{research_name}} | Audience, method, sample |
| 2 | section | Questions | 3-5 дослідницьких питань |
| 3 | section | Method | Сегменти, метод, тривалість |
| 4 | metric | Sample | N учасників, demographics |
| 5-8 | theme | Тема N | Name + 1 insight + 1 quote + evidence |
| 9 | two-col | Pattern map | Де болі перетинаються |
| 10 | section | Surprises | Що виявилось неочевидним |
| 11 | section | Recommendations | Конкретні дії |
| 12 | two-col | Priority matrix | Impact × effort |
| 13 | section | Next research | Що варто дослідити далі |
| 14 | cta | Ask / Discussion | Що обговорюємо |

### 5.3. `ab-test-readout` — A/B test readout (9 слайдів)

| # | Layout | Title | Контент |
|---|--------|-------|---------|
| 1 | title | {{test_name}} — Readout | Period, variant split |
| 2 | section | Hypothesis | If we [do X], then [metric] will [change], because [reason] |
| 3 | two-col | Variants | Screenshots control vs. treatment |
| 4 | section | Design of the test | Primary metric, MDE, guardrails, duration |
| 5 | chart | Primary metric | Control vs. treatment з CI |
| 6 | chart | Guardrails | Performance, cancellations, NPS-проксі |
| 7 | section | Segments | Де зайшло / не зайшло (platform, locale, seller-tier) |
| 8 | section | Verdict | Ship / Kill / Iterate + rationale |
| 9 | cta | Next steps | Follow-ups + owner |

### 5.4. `release-readout` — Release / Sprint readout (12 слайдів)

| # | Layout | Title | Контент |
|---|--------|-------|---------|
| 1 | title | Release {{version}} / Sprint {{name}} | Date range |
| 2 | section | Scope | Що ввійшло (link → Jira епіки) |
| 3 | metric | Delivery | Planned vs. delivered, velocity |
| 4 | chart | Key metrics — before / after | Primary + secondary |
| 5 | two-col | What went well | Top 3 успіхи |
| 6 | two-col | What to improve | Top 3 блокери з action |
| 7 | section | User feedback | 3 цитати + ticket counts |
| 8 | section | Bugs | Production incidents, resolved |
| 9 | metric | Business impact | GMV, orders, CR дельта |
| 10 | section | Learnings | 3 learnings + як враховуємо у next |
| 11 | section | Next sprint focus | Priorities, ownership |
| 12 | cta | Discussion | Open questions |

---

## 6. Layer 1 — DS → pptx theme mapping

Прямий mapping з YAML (Part 2) у python-pptx-parameters. Повний map — у `06-pptx-theme-prom.yaml`. Ключові рішення тут:

### Colors

| pptx slot | Source DS token | Usage |
|---|---|---|
| `theme.accent1` | `colors.brand.prom_primary` | CTA, headings highlight |
| `theme.accent2` | `colors.brand.prom_primary_subtle` | Background blocks |
| `theme.text_primary` | `colors.neutrals.text_primary` | Body text |
| `theme.text_secondary` | `colors.neutrals.text_secondary` | Meta, captions |
| `theme.background_light` | `colors.neutrals.surface_primary` | Main bg |
| `theme.background_section` | `colors.neutrals.surface_secondary` | Section dividers |
| `theme.chart.positive` | `colors.semantic.success` | Uplift bars, wins |
| `theme.chart.negative` | `colors.semantic.error` | Regression bars |
| `theme.chart.neutral` | `colors.neutrals.text_secondary` | Control |

### Typography

Підтверджено з офіційного brand template (`design-integration/assets/base_prom.pptx`, XML-аудит):
**Montserrat** (400/500/600/700) + **Montserrat ExtraBold** (800) для display-ролей.

| Role | Font | Size | Weight |
|---|---|---|---|
| Slide title (H1) | Montserrat ExtraBold | 36 | 800 |
| Section (H2) | Montserrat | 26 | 700 |
| Subtitle | Montserrat | 18 | 500 |
| Body large | Montserrat | 16 | 400 |
| Body | Montserrat | 14 | 400 |
| Caption | Montserrat | 10 | 400 |
| Metric value | Montserrat ExtraBold | 44 | 800 |

**Fallback:** Montserrat — Google Font, вільний до embed у .pptx. Якщо не знайдено на reader-машині — PowerPoint підставить system sans; renderer додає warning у outline footer.

### Layouts (master slides)

| Layout ID | Використання | Slots |
|---|---|---|
| `title` | #1 | title(H1), subtitle(body), presenter(caption), date(caption) |
| `section` | section dividers + paragraph слайди | title(H2) + body(body) або bullets |
| `two-col` | problem/solution, before/after, in/out | left(title+body), right(title+body або image) |
| `metric` | KPI-виклад | up to 3 metric blocks (label+value+delta) |
| `chart` | графіки | title + chart area + legend |
| `quote` | user quote у research | quote(H2, italic) + attribution(caption) |
| `cta` | ask / next steps | title + 1-3 actions + owner (body) |

### Spacing & layout

- Slide size: 16:9, **10.0 × 5.625 inches** (25.4 × 14.29 cm) — Google Slides default, успадковано від офіційного Prom template.
- Outer margin: **0.5 inch** (оптимально під 10"-slide; 1" з'їдав би 20% ширини).
- Gutter between columns: **0.35 inch**.
- Максимум 5 bullets на слайд; якщо більше — split.
- Base file: `design-integration/assets/base_prom.pptx` (11 layouts: TITLE, TITLE_AND_BODY, TITLE_AND_TWO_COLUMNS, BIG_NUMBER, MAIN_POINT, BLANK та ін.). Renderer відкриває цей файл як entry point і додає нові слайди через `prs.slides.add_slide(prs.slide_layouts[...])`.

---

## 7. Figma integration (опціонально, заглушена hook-поверхня)

Опціональний layer у Step 4c.

Тригер: source доза містить Figma URL **АБО** користувач явно просить "додай скріни з Figma".

```
for each figma_url у source:
  parse URL → fileKey, nodeId
  screenshot = get_screenshot(nodeId, fileKey)
  store temp file
  emit slide placeholder: { layout: "two-col", image: <screenshot path> }
```

**Policy:**
- Не embed-имо Figma frames з конкурентних досліджень (data-policy).
- Embeds з приватних файлів Prom — тільки у internal decks (pptx not shared publicly).
- Permission check — якщо `whoami` seat = View і фрейм потребує edit-токенів для контексту, fallback на low-fi placeholder.

**Fallback коли Figma недоступна:**
- Placeholder-слайд з текстом "[Дизайн: див. Figma {{url}}]"
- або ICE-стиль: slot "Insert screenshot manually" (для людини-презентера).

---

## 8. Приклад: end-to-end flow (concept → deck)

**Вхід:** Andrii має concept doc "Q&A — Product Page Integration" у Confluence, хоче deck для direction review.

```
Andrii: "зробімо презентацію для direction review на базі концепту SHOPEX-6610"

design-bridge activates:
  Step 0  → load local-context + DS yaml
  Step 1  → intent=deck, subtype=feature (inferred from "direction review")
            source_type=concept, source_location=confluence page 6610
  Step 2  → audience=direction_review (default), language=uk, length=10
  Step 3  → template-library.resolve(artifact_type=presentation, subtype=feature)
            → selected: presentation-builtin-feature@1.0.0
  Step 4a → parse Confluence page → extract:
            - feature_name = "Q&A на Product Page"
            - problem_statement = "Низький % відповідей продавців, питання лишаються у листуваннях"
            - solution_summary = "Публічний Q&A блок на КТ із нотифікаціями продавця"
            - key_metrics = ["% товарів з ≥1 QA", "Response rate продавця < 24h", "CR КТ"]
            - ask = "схвалення MVP, ресурси FE/BE для 2 sprints"
  Step 4b → ask user: "Запустити design:ux-copy + design:design-critique?"
            → user says yes
            → design:ux-copy полірує headings і CTA
            → design:design-critique flags:
              • Slide 4 має 7 bullets — split
              • Slide 7 (MVP scope) — додати "Out of scope" секцію
            → iterate, re-render outline
  Step 4c → Figma?
            → Andrii дає посилання на Figma frame нового Q&A блоку
            → get_screenshot(nodeId, DS_FILE_KEY) → 1 image attached to slide 5
  Step 5  → render via pptx skill:
            - Open base_prom.pptx, apply Prom theme (primary #7B04DF, Montserrat)
            - 10 slides instantiated from master layouts
  Step 6  → QA:
            - contrast OK
            - slides=10 (within limit)
            - no unfilled slots
            - branding: primary color used on 3 slides ✓
            → all passed
  Step 7  → save to:
            /Users/.../presentations/prom/2026-04-20-qa-product-page-direction.pptx
            + outline.md companion
            → update Obsidian MOC
            → attach link to SHOPEX-6610 as comment
```

---

## 9. Failure modes & fallbacks

| Failure | Behavior |
|---|---|
| Template not found | fallback до `presentation-builtin-feature`, warning у outline footer |
| DS yaml не парситься | fallback на hardcoded Prom brand (primary=#7B04DF, Montserrat) |
| base_prom.pptx відсутній | fallback до blank Presentation() + явне позиціонування shapes за rect-координатами з Part 6 |
| Figma MCP 403 | пропустити embeds, залишити placeholders |
| Source content надто малий (<100 слів) | ask користувача заповнити ручно ключові variables |
| Мова не співпадає з template `available_languages` | вибрати найближчу; позначити у outline |
| pptx skill недоступний | fallback на `outline.md` + `outline.html` (можна скопіювати у Google Slides) |

---

## 10. Acceptance criteria

- [ ] `design-bridge` у deck-pack режимі підтримує 4 subtypes.
- [ ] Кожен deck використовує Prom DS tokens (accent1 = prom_primary; fonts з DS).
- [ ] Template resolution проходить per template-protocol.md (Step T-0..T-5).
- [ ] `design:ux-copy` + `design:design-critique` інтегровані як Step 4b-хуки.
- [ ] Figma screenshots embed-ються опціонально (graceful fallback).
- [ ] QA gate блокує release при contrast failure або unfilled slots.
- [ ] Файл .pptx + outline.md + Obsidian link — всі три артефакти генеруються.

---

## 11. Roadmap (MVP → v2)

### MVP (v1.10.0)
- design-bridge deck-pack skeleton (Steps 0-7)
- 1 template: `presentation-builtin-feature` (існує)
- Prom DS theme YAML (Part 6)
- Chain hook у `write-concept` Step D

### v1.11.0
- Templates: research-highlights, ab-test-readout, release-readout (нові у `templates/built-in/presentation/`)
- design:design-critique gate для exec/direction decks
- Figma embed (опціонально)

### v1.12.0+
- Google Slides export
- Live metrics auto-populate (Tableau → chart slides)
- User-scope template authoring для custom decks (FET-specific)

---

## 12. Related artifacts

- **Part 6:** `06-pptx-theme-prom.yaml` — повний mapping DS → python-pptx parameters + master slide specs.
- (Post-MVP) `templates/built-in/presentation/research-highlights-v1.md`
- (Post-MVP) `templates/built-in/presentation/ab-test-readout-v1.md`
- (Post-MVP) `templates/built-in/presentation/release-readout-v1.md`
