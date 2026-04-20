# local-context.md — Design section patch

> **Purpose:** готовий патч для `local-context.md`, який додає Design-контекст, щоб скіли `design-bridge`, `design:*`, `diagram-prototyper` і pptx-генерація мали однакове джерело істини.
> **Apply status:** автоматично застосовано до `local-context.md` цією генерацією (секції "Design System (Figma)", "Design Targets", "Tone of Voice").

---

## 1. Що додається у файл

### 1.1. Розширена секція `#### Figma` (заміна існуючої)

```markdown
#### Figma
- **Team URL:** https://www.figma.com/files/team/1021675057377943036/all-projects
- **Team ID:** 1021675057377943036
- **User ID (fuid):** 1265194654265693083
- **MCP status:** authenticated as a.siletskyi@smartweb.com.ua (Pro, View seat)
- **Design System file key:** _(TODO — знайти через get_libraries, див. design-integration/03-figma-mcp-config.md §2)_
- **Design System library key:** _(TODO)_
- **Last DS sync:** _(TODO — YYYY-MM-DD після першого run sync через search_design_system)_
- **DS reference spec:** `design-integration/02-prom-design-system-spec.yaml`
```

### 1.2. Нова секція `### Design System (Prom)` під `Product: Prom.ua`

```markdown
### Design System (Prom)

- **Spec file:** `design-integration/02-prom-design-system-spec.yaml`
- **Source of truth:** Figma library (див. `figma.ds_file_key`) + YAML кеш (для offline).
- **Primary brand color:** `#7B04DF` (prom_primary, confirmed з офіційного brand template).
- **Dark neutral:** `#222223` (prom_dark, confirmed).
- **Typography:** Montserrat (body) + Montserrat ExtraBold (display) — confirmed з template.
- **Base deck template:** `design-integration/assets/base_prom.pptx` (10" × 5.625", 11 layouts).
- **Radius scale:** 0, 4, 8, 12, 16, pill (9999).
- **Spacing scale:** 2, 4, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80.

**Used by:**
- `design-bridge` скіл
- `design:design-system`, `design:design-handoff`, `design:accessibility-review`
- `diagram-prototyper` (Prototype type)
- pptx-генерація через template-library (презентації у Prom стилі)
```

### 1.3. Нова секція `### Design Targets`

```markdown
### Design Targets

- **Accessibility standard:** WCAG 2.1 AA (обов'язковий gate перед handoff).
- **Stretch a11y:** AAA для rating stars, price, critical CTA.
- **Mobile touch target:** ≥ 44×44 px.
- **Contrast minimums:** 4.5:1 normal text, 3:1 large text, 3:1 для non-text UI.
- **Motion:** respect `prefers-reduced-motion`.
- **Focus ring:** видимий на всіх інтерактивних елементах.
- **Localization coverage:** uk (default), ru (fallback), kz (для kz-локалі).
```

### 1.4. Нова секція `### Tone of Voice`

```markdown
### Tone of Voice

- **Primary:** доступний, практичний, без пафосу. "Ти" у b2c, "ви" — продавцям.
- **Avoid:** англіцизми без потреби ("клікніть", "чекаут"), слова-паразити ("просто", "легко"), умовний спосіб ("можливо, захочете").
- **Good:** "Додай відгук — покупцям важливо знати твою думку" / "Не знайшли те, що шукали? Уточни категорію".
- **Bad:** "Будь ласка, завершіть оформлення" / "Дякуємо за ваш цінний відгук".
- **Copy library seed:** `design-integration/02-prom-design-system-spec.yaml` → `copy_library`.
```

### 1.5. (Опціонально, v1.10+) Нова секція `### Design Hooks`

```markdown
### Design Hooks (plugin behavior)

| Skill | Hook | Trigger question |
|---|---|---|
| write-concept | Step D after draft | "Enrich з design:ux-copy / діаграма / deck?" |
| requirements-creator | Step D after sections | "Запустити design:design-critique + design:ux-copy?" |
| brainstorm-features | after ICE scoring | "Швидкий прототип обраної гіпотези через diagram-prototyper?" |
| diagram-prototyper | after type=Prototype | "Запустити design:accessibility-review?" (обов'язково пропонувати) |
| cjm-research | on anomaly | "Design:user-research plan для цього кроку?" |
| meeting-processor | after extraction | "Interview? → design:research-synthesis" |
```

---

## 2. Apply notes

- Секції 1.2, 1.3, 1.4 додаються **після** існуючого блоку `Product: Prom.ua` (перед `Product: Grow Product Manager Plugin`).
- Секція 1.5 — опціональна, додається коли буде встановлений `design-bridge` скіл (v1.10.0 ROADMAP).
- Після застосування патчу — оновити header: `Updated: 2026-04-20 (Design section added)`.
