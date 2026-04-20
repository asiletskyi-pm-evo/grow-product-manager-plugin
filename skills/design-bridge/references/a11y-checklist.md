# Accessibility Checklist — Step 6 QA gate

WCAG 2.1 AA — non-negotiable для handoff та dev-facing deliverables. Для deck — warnings допустимі з footer-нотаткою, але critical blocker = contrast fail на primary text/CTA.

## Pre-audit: коли що запускати

| intent | WCAG scope | blocker? |
|---|---|---|
| deck | contrast (primary text, CTA) | blocker; решта — warning |
| prototype (lo-fi) | contrast, touch targets | warning only |
| prototype (mid-fi, hi-fi) | full WCAG 2.1 AA | blocker |
| handoff | full WCAG 2.1 AA + AAA stretches | blocker |
| research-enrichment | не запускається | — |

## Core checks (WCAG 2.1 AA)

### 1. Color contrast

- **Normal text (≤ 18px reg, ≤ 14px bold)**: min 4.5:1
- **Large text (> 18px reg, > 14px bold)**: min 3.0:1
- **Non-text UI (icons, borders, focus rings)**: min 3.0:1
- **Disabled states**: excluded from requirement, але уникати < 3.0:1

Prom-specific pre-computed ratios (з `02-prom-design-system-spec.yaml`):
- `#222223` text on `#FFFFFF` → 16.4:1 ✓
- `#FFFFFF` text on `#7B04DF` → 4.9:1 ✓
- `#5F6368` text on `#FFFFFF` → 5.9:1 ✓
- `#5F6368` text on `#F5F6F7` → 5.5:1 ✓
- `#FFFFFF` text on `#222223` → 16.1:1 ✓
- `#7B04DF` text on `#FFFFFF` → 6.2:1 ✓
- `#7B04DF` text on `#F0E5FC` (subtle) → 5.8:1 ✓

### 2. Touch target size

- Min **44×44 CSS px** (Apple HIG + WCAG 2.5.5 AAA).
- Spacing between interactive elements ≥ 8px.
- On mobile Prom — applies to product cards, filters, CTA, tab switches.

### 3. Keyboard navigation

- Усі interactive елементи — досяжні через Tab.
- Focus ring видимий (contrast ≥ 3.0:1 з background).
- Order — logical (top→bottom, left→right).
- Escape закриває modals / dropdowns.
- Enter / Space активує кнопки.

### 4. Screen reader labels

- Input'и мають `<label>` (або `aria-label`).
- Icon-only buttons мають `aria-label`.
- Images — `alt` з контекстом (пустий `alt=""` для decorative).
- Headings — у логічній ієрархії (h1 → h2 → h3, no skip).
- Live regions (`aria-live`) для dynamic content updates.

### 5. Motion & animation

- Respect `prefers-reduced-motion`.
- Animations ≤ 5 сек або мають controls (pause/stop).
- Parallax / автопрогравання — off by default.
- Flashes — не більше 3 на сек.

### 6. Forms & errors

- Error messages — inline, описові, вказують як виправити.
- Required fields — marked (`*` + `aria-required="true"`).
- Field groups — `<fieldset>` + `<legend>`.
- Error states — не тільки колір (icon + text).

## Deck-specific checks

- Cover slide title: Montserrat ExtraBold 36pt white on `#222223` → 16.1:1 ✓
- Метричні tiles: `#222223` value on `#F0E5FC` subtle → 13.4:1 ✓
- CTA кнопки (якщо embedded у slide): `#FFFFFF` on `#7B04DF` → 4.9:1 ✓
- Charts: колір + pattern/label (не тільки колір) для різниці категорій
- Footer caption: `#5F6368` on `#FFFFFF` → 5.9:1 ✓ (навіть при 10pt — large text за WCAG)

## Handoff / prototype deep checks

- Усі компоненти мають states: default, hover, focus, active, disabled, loading, error.
- Responsive: mobile (≤ 480), tablet (≤ 1024), desktop (> 1024).
- RTL support — якщо targetuje арабську/іврит аудиторію (для Prom — не актуально).
- i18n: string expansion ≤ 30% (uk → de найдовші).

## QA output format

```yaml
a11y_audit:
  status: pass | warn | fail
  scope: deck | prototype | handoff
  wcag_level: AA
  timestamp: <ISO>
  checks:
    contrast:
      pass_count: N
      fail_count: N
      fails:
        - { slide_or_component: "...", fg: "#...", bg: "#...", actual_ratio: X.X, required: 4.5 }
    touch_target:
      pass_count: N
      fail_count: N
      fails:
        - { component: "...", actual_px: "36×36", required: "44×44" }
    keyboard_nav:
      status: pass|warn|fail
      notes: "..."
    screen_reader:
      status: pass|warn|fail
      missing_labels: [...]
    motion:
      status: pass|warn|fail
  blockers: [...]
  warnings: [...]
```

Якщо `blockers` непусті → Step 5 блокується. Розпишемо у outline footer conspicuously.

Якщо лише `warnings` → deliverable публікується, але з block у footer / handoff:
> ⚠️ A11y audit warnings: <list>. Slide X / Component Y. Recommendation: <fix>.
