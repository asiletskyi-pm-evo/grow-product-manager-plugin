---
name: design-bridge
version: 0.1.0
description: Orchestrate Claude's Design skills (user-research, research-synthesis, ux-copy, design-critique, design-system, accessibility-review, design-handoff) and Figma MCP into the Grow PM pipeline. Use when the user asks to "create a deck", "make a presentation", "build a prototype", "generate handoff", "design review", or when another Grow PM skill (write-concept, requirements-creator, brainstorm-features, product-research, cjm-research, meeting-processor) finishes and the next step involves a deck, prototype, or design artifact.
---

# Design Bridge

Оркестратор, що поєднує Grow PM pipeline з Claude Design skills + Figma MCP + Prom DS + Prom pptx template. Один скіл відповідає за чотири сценарії: **deck**, **prototype**, **handoff**, **research-enrichment**.

## Коли використовувати

**Автоматично тригериться з інших скілів** (Step D hook):

| Upstream skill | Trigger | Default intent |
|---|---|---|
| `write-concept` | після Step 7 (publish) | `deck: subtype=feature-concept` |
| `requirements-creator` | після Step 5 (publish) | `handoff: components + copy + a11y` |
| `brainstorm-features` | після ICE ranking top-3 | `prototype: lo-fi per top hypothesis` |
| `product-research` | після Step 6 (synthesis) | `deck: subtype=research-highlights` |
| `cjm-research` | після hypothesis-backlog | `deck: subtype=research-highlights` + `prototype` для quick wins |
| `meeting-processor` | якщо meeting → decisions → deck | пропонує deck або handoff за контекстом |

**Вручну** — коли користувач каже:
- "зроби/створи презентацію", "зроби deck", "make a deck", "підготуй для direction review"
- "прототип", "mockup", "wireframe" (для hypothesis / concept / requirements)
- "handoff до розробників", "передати дизайн у розробку"
- "проведи review дизайну", "перевір контраст", "a11y аудит"
- "витягни контекст із Figma", "Figma screenshot"

## Integration prerequisite

Читай і виконуй fallback chain із `references/integration-strategy.md`. Для цього скіла ключові:

- **Claude Design plugin** (`design:*` sub-skills) — `user-research`, `research-synthesis`, `ux-copy`, `design-critique`, `design-system`, `accessibility-review`, `design-handoff`
- **Figma MCP** — `whoami`, `get_libraries`, `search_design_system`, `get_variable_defs`, `get_design_context`, `get_screenshot`, `get_metadata`
- **pptx skill** (Anthropic) — для рендеру .pptx через python-pptx
- **docx / pdf** — для alternative deliverables
- **diagram-prototyper** (Grow PM) — для low-fi wireframes та flow-диаграм
- **template-library** (Grow PM) — для resolve presentation templates
- **Confluence / Jira / Google Drive** — для публікації та attachments

Перед gather data — читай `references/data-policy.md`. Figma embeds з конкурентних досліджень або приватних файлів інших команд **не** публікуємо у зовнішні deck.

## Local context prerequisite

**Перед стартом** слідуй `references/local-context-protocol.md` (Step 0). Зчитай `local-context.md`, обери active product, завантаж design-специфічний контекст:

- `product.figma.ds_file_key` — для Figma MCP викликів (якщо відсутній — graceful fallback)
- `product.design_system_spec` — path до Prom DS yaml (за замовчуванням `design-integration/02-prom-design-system-spec.yaml`)
- `product.pptx_theme` — path до theme yaml (за замовчуванням `design-integration/06-pptx-theme-prom.yaml`)
- `product.base_pptx` — path до base template (`design-integration/assets/base_prom.pptx`)
- `product.tone_of_voice` — style guide (див. Design System (Prom) секцію)
- `product.design_targets` — WCAG rules, touch targets, motion
- `user.language` — мова deliverable (default uk)

Якщо `local-context.md` відсутній → редирект до `plugin-configurator`.

## Step T — Template Resolution

Виконується тільки у `intent ∈ {deck}`. Для інших intent — пропусти.

Слідуй `references/template-protocol.md`:
- `artifact_type: presentation`
- `subtype: {feature-concept | research-highlights | ab-test-readout | release-readout}` (визначається у Step 1)
- `product_id: {active product}`
- `language: {uk|en}`

T-1..T-5 через `template-library`. Якщо жоден не знайдено → fallback: `presentation-builtin-{subtype}-v1` (built-in у `templates/built-in/presentation/`). Якщо і цей відсутній → ad-hoc outline з цього SKILL.

## Workflow

### Step 0 — Context bootstrap

1. Завантаж local-context.md → active product, user preferences.
2. Завантаж `design-integration/02-prom-design-system-spec.yaml` (Prom DS tokens).
3. Якщо intent=deck → завантаж `design-integration/06-pptx-theme-prom.yaml`.
4. Якщо Figma MCP доступний і є `ds_file_key` — cache DS через `get_variable_defs` (не обов'язково, для speedup).

### Step 1 — Intent & subtype detection

Через `AskUserQuestion`, якщо не задано upstream-скілом:

**Q1. Який deliverable потрібен?**
- deck (презентація .pptx)
- prototype (wireframe / lo-fi mockup)
- handoff (developer spec для фронту)
- research-enrichment (пропустити через design:research-synthesis та додати до upstream)

**Q2 (тільки для deck). Який тип deck?**
- feature-concept (pitch фічі — 10 slides, типовий для direction review)
- research-highlights (dump дослідження — 8-12 slides)
- ab-test-readout (результати A/B — 6 slides)
- release-readout (підсумки релізу / спринта — 6-8 slides)

**Q3 (для prototype). Рівень точності?**
- lo-fi (Mermaid flow / ASCII wireframe)
- mid-fi (HTML + Prom DS tokens)
- hi-fi (відправляємо у Figma через `use_figma` — потребує Full seat)

**Q4 (для handoff). Ціль деливарі?**
- спецсторінка Confluence (markdown + screenshots)
- inline у Jira ticket як attachment
- standalone .md у папці `deliverables/handoffs/`

### Step 2 — Audience & constraints

Через `AskUserQuestion`:
- **Audience** (за замовчуванням з upstream): direction_review / team / c-level / customer / dev_handoff
- **Length** (для deck): recommended 10; cap 20
- **Language**: uk / en (default з local-context)
- **Brand mode**: prom_default (confirmed #7B04DF + Montserrat) | custom | minimal
- **Figma embeds**: так / ні / тільки якщо user надасть посилання

### Step 3 — Source extraction

Залежно від **upstream**:

**a. Confluence page** (`write-concept`, `requirements-creator`) — парс через `getConfluencePage`; витягай:
- `title`, `problem_statement`, `solution_summary`, `key_metrics`, `scope`, `phases`, `risks`, `ask`
- будь-які embedded diagram URLs → ремапимо у Step 4c

**b. Research output** (`product-research`, `cjm-research`, `meeting-processor`) — парс markdown:
- themes, insights, recommendations
- quotes (для research decks)
- anomalies / funnel drops (для CJM decks)

**c. Brainstorm output** (`brainstorm-features`) — json/md:
- top-3 hypotheses з ICE scores
- mapped funnel steps

**d. A/B test data** (`product-analysis`, Tableau) — csv/markdown:
- metrics, control vs treatment, CI, lift

**e. User-provided** — raw text / pasted context / uploaded files.

Нормалізуй у **Deck IR** (intermediate representation):

```yaml
deck:
  subtype: <from Step 1>
  title: <string>
  subtitle: <string>
  presenter: <string>
  date: <ISO>
  audience: <string>
  language: uk|en
  slides:
    - layout: <title|section|two-col|metric|chart|quote|cta>
      title: <string>
      body: <string|list>
      media: [<image path|figma node ref|chart spec>]
      speaker_notes: <string>
```

### Step 4 — Design-skill hooks

#### 4a. User research → research-synthesis

**Тригер**: intent=deck AND subtype=research-highlights AND sources містять interview transcripts / survey data.
**Виклик**: `design:research-synthesis` із сировим матеріалом.
**Вихід**: структуровані themes, recommendations — вставляємо у slides (section, quote).

#### 4b. UX copy polish

**Тригер**: intent∈{deck, prototype, handoff}.
**Виклик**: `design:ux-copy` з:
- slide titles (max 72 chars, відповідно Prom tone)
- CTA labels (на cta-слайдах і prototype-кнопках)
- error/empty/loading states (на прототипах)

**Вихід**: поправлені headings та microcopy. Перезаписуємо відповідні поля у Deck IR / Prototype IR.

#### 4c. Design critique

**Тригер**: intent=deck AND slides_count ≥ 5.
**Виклик**: `design:design-critique` на outline + ключові візуали.
**Вихід**: список issues:
- "Slide 4 має 7 bullets — split"
- "Slide 7 (MVP scope) — додати 'Out of scope'"
- "Low-contrast combo на slide 2"

Виправ автоматично ті, що можна (split, re-order, add section); для інших — попроси user confirmation.

#### 4d. Design system check

**Тригер**: intent∈{prototype, handoff}.
**Виклик**: `design:design-system` проти Prom DS spec.
**Вихід**: список DS violations — hardcoded colors, wrong radius, missing tokens. Fix inline або додай у Open Questions.

#### 4e. Accessibility audit

**Тригер**: intent∈{prototype, handoff, deck} AND (audience=c-level OR dev_handoff OR user сам попросив).
**Виклик**: `design:accessibility-review` (WCAG 2.1 AA):
- contrast ratios
- touch targets ≥ 44×44
- keyboard nav
- screen reader labels

**Вихід**: pass/fail report. Критичні виявлення блокують release (Step 6 QA gate).

#### 4f. Developer handoff

**Тригер**: intent=handoff.
**Виклик**: `design:design-handoff`.
**Вихід**: spec sheet — layout, tokens, component props, states, breakpoints, animation. Саме це і є основний deliverable у handoff-сценарії.

#### 4g. Figma context / screenshots

**Тригер**: `embeds=yes` AND (Figma URL у source OR user надав посилання).

Workflow:
1. Parse URL → fileKey, nodeId
2. `get_design_context(nodeId, fileKey)` — TEXT контекст фрейму (назви шарів, variants)
3. `get_screenshot(nodeId, fileKey)` — зображення у temp
4. Вставити у Deck IR slide як `media: [path/to/screenshot.png]`
5. Якщо seat=View і треба edit → skip hi-fi prototype, warn у outline

**Policy** (з `references/data-policy.md`):
- Не ембедимо Figma frames з конкурентних досліджень
- Embeds з приватних файлів Prom — тільки у internal decks (not published externally)
- Permission error (403) → graceful fallback: placeholder "[Дизайн: див. Figma {{url}}]"

### Step 5 — Render deliverable

Рoutinг за `intent`:

#### 5a. intent=deck → .pptx

1. Завантаж base template: `Presentation("design-integration/assets/base_prom.pptx")`.
2. Завантаж `06-pptx-theme-prom.yaml`.
3. Для кожного slide у Deck IR:
   - resolve layout name через `implementation_hints.slide_layout_index.mapping`
   - `slide_layout = prs.slide_layouts.get_by_name(<mapping>)`
   - `new_slide = prs.slides.add_slide(slide_layout)`
   - заповни placeholders або додай shapes за rect-координатами (Part 6 → `layouts.<name>.elements`)
   - apply colors/fonts з theme.colors / theme.typography (Montserrat, `#7B04DF`, `#222223`)
4. Embed media (images, charts).
5. Save: `{vault_root}/Presentations/{product}/{date}-{slug}-{subtype}.pptx`.
6. Паралельно — markdown outline companion у тій самій папці (`.md`) для швидкого review.

Fallback: якщо pptx skill недоступний → лише outline.md + outline.html (copy-pasteable у Google Slides).

#### 5b. intent=prototype → HTML / Mermaid / Figma

- lo-fi → `diagram-prototyper` (Mermaid + ASCII)
- mid-fi → HTML з inline Prom DS tokens (Montserrat, `#7B04DF`) + Tailwind-compatible класи
- hi-fi → `use_figma(…)` (Full seat only) → створює Figma frame

Save у `{vault_root}/Prototypes/{product}/{date}-{slug}/`.

#### 5c. intent=handoff → Confluence page / .md

Spec sheet із `design:design-handoff` output + screenshots з Figma + a11y checklist.

#### 5d. intent=research-enrichment → append to upstream

Не створює окремий файл — повертає структуровані themes назад у upstream skill, який вже публікує.

### Step 6 — QA gate

Обов'язковий для intent∈{deck, prototype, handoff}:

- **Contrast** (WCAG AA): всі ключові pairs з `qa_rules.contrast.pairs_to_check` у Part 6
- **Slide count** (для deck): within `max_over_preference_ratio`
- **Bullets per slide** (для deck): ≤ 5
- **Title length**: ≤ 72 chars
- **Brand usage**: мін 2 слайди з `accent1` (#7B04DF)
- **Empty slots**: немає `{{…}}`, `TODO`, "Тут може бути твій заголовок", "Lorem ipsum"
- **Font check**: Montserrat + ExtraBold доступні (якщо ні — warning у outline footer)
- **A11y**: якщо Step 4e був запущений — всі fails = blocker; warnings = footer notice

Якщо fail → fix + rerun QA; повертайся до user у разі нефіксабельного блокера.

### Step 7 — Publish & link

Залежно від deliverable:

- **deck** → attach до:
  - Confluence page upstream (якщо є) як attachment
  - Jira ticket (якщо source = ticket) як comment із link
  - Обидва, якщо upstream обидва
- **prototype** → link у concept / requirements page (inline)
- **handoff** → новий Confluence page у design-space або attach у Jira epic
- **research-enrichment** → інлайн у upstream skill

Далі:
- Оновити Obsidian Vault MOC: `Presentations/{product}/` або `Prototypes/{product}/` або `Handoffs/{product}/` (якщо vault_level > L0)
- Додати `design_sources` у frontmatter artifact (Figma URLs, screenshot paths)
- Повернути user-friendly summary із computer:// links

## Step 8 — Vault save (optional)

Якщо `vault_level > L0` і `sync_mode != off`:

```
vault_save({
  type: "presentation" | "prototype" | "handoff",
  product: active_product,
  skill: "design-bridge",
  skill_version: "0.1.0",
  tags: [subtype, audience, language, figma_embeds?],
  content: artifact_content,
  related: [upstream_artifact_id, figma_urls],
  extra_frontmatter: {
    subtype: <from Step 1>,
    audience: <from Step 2>,
    slide_count: N,
    figma_embeds: [urls],
    a11y_status: pass|warn|fail
  }
})
```

## Additional Resources

- **`references/local-context-protocol.md`** — Step 0 протокол
- **`references/template-protocol.md`** — Step T (resolve presentation template)
- **`references/integration-strategy.md`** — MCP → Registry → Browser fallback
- **`references/data-policy.md`** — обмеження embed-ів Figma та publish
- **`references/deck-subtypes.yaml`** — слайд-аутлайни всіх 4 subtypes (layout sequence, required slots, recommended media)
- **`references/figma-playbook.md`** — як резолвити fileKey, safe patterns, known limitations (View seat)
- **`references/a11y-checklist.md`** — checklist для Step 6 QA
- **`design-integration/02-prom-design-system-spec.yaml`** — Prom DS tokens (colors, typography, components)
- **`design-integration/05-presentation-logic.md`** — повна логіка рендеру .pptx (layer model, trigger matrix)
- **`design-integration/06-pptx-theme-prom.yaml`** — mapping Prom DS → python-pptx (layouts, fonts, colors)
- **`design-integration/assets/base_prom.pptx`** — офіційний Prom brand template (11 Google Slides layouts)
- **`references/vault-protocol.md`** — Step 8 vault save

## Quality standards

- Завжди перевіряй Figma seat before hi-fi prototype
- Не публікуй зовнішньо deck із screenshots приватних Figma
- WCAG 2.1 AA — non-negotiable для handoff і dev-facing deliverables
- Montserrat / `#7B04DF` / `#222223` — brand invariant; custom mode тільки за явним запитом
- Кожен deck повинен мати cover + ask/next-steps slides, навіть якщо коротший за 6 слайдів
- Всі slides з даними повинні мати source line (caption: "Source: ..."), якщо цифри з upstream
- Bilingual support (uk/en) у всіх outputs; kz — поки не підтримується

## Failure modes & fallbacks

| Failure | Behavior |
|---|---|
| base_prom.pptx відсутній | blank Presentation() + явне позиціонування shapes за rect-координатами з Part 6 |
| Template not found | fallback до `presentation-builtin-{subtype}-v1`; якщо теж немає — ad-hoc outline |
| DS yaml не парситься | fallback на hardcoded Prom brand (purple #7B04DF, Montserrat) |
| Figma MCP 403 / seat=View | skip hi-fi; embed лише screenshots (якщо get_screenshot працює); на fail — placeholder |
| `design:*` plugin відсутній | propose install; fallback на native rewrite (ux-copy), manual critique outline |
| pptx skill недоступний | fallback: outline.md + outline.html |
| Source content < 100 слів | ask user для fill manual; не генерувати "lorem ipsum" |
| A11y fail на handoff | блокер release; deck-mode — warning у footer |
| Language не у `available_languages` | обери найближчу, позначи у outline |

## End-to-end example: concept → deck

**Тригер**: Andrii каже "зробімо презентацію для direction review на базі концепту SHOPEX-6610" (Q&A — Product Page Integration).

```
design-bridge:
  Step 0  → load local-context + DS yaml + theme yaml
  Step 1  → intent=deck (user explicit), subtype=feature-concept
  Step 2  → audience=direction_review (default), language=uk, length=10,
            brand=prom_default, embeds=ask
  Step T  → template-library.resolve(presentation, feature-concept, prom, uk)
            → selected: presentation-builtin-feature-concept-v1@1.0.0
  Step 3  → parse Confluence SHOPEX-6610 page → Deck IR populated:
              title="Q&A на Product Page", subtitle="Direction review",
              problem, solution, metrics, ask, scope, phases
  Step 4b → design:ux-copy polishes titles + CTA (max 72 char, Prom tone)
  Step 4c → design:design-critique flags:
              • Slide 4 (Evidence) has 7 bullets → split into 4a+4b
              • Slide 7 (MVP scope) → add "Out of scope" sub-section
  Step 4g → Andrii pastes Figma frame URL for Q&A block
            → get_screenshot(nodeId, ds_file_key) → image for slide 7
  Step 5a → open base_prom.pptx, apply Prom theme
            → 10 slides added via slide_layouts.get_by_name(…)
            → save: Presentations/prom/2026-04-20-qa-product-page-direction.pptx
  Step 6  → QA pass (contrast, 10 slides, no empty slots, Montserrat OK,
            accent1 used on 3 slides)
  Step 7  → attach to SHOPEX-6610 Confluence page as attachment
            → comment in Jira SHOPEX-6610 with computer:// link
            → update Obsidian Vault: Presentations/prom/2026-04-20/
  Step 8  → vault_save(type=presentation, subtype=feature-concept, …)
  → output: "[View deck](computer://…/2026-04-20-qa-product-page-direction.pptx)"
```

## Changelog

- `0.1.0` (2026-04-20) — Initial release. Supports 4 intents, 4 deck subtypes, 7 design-skill hooks, Figma MCP integration, Prom brand parity (base_prom.pptx).
