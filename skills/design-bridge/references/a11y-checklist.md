# Accessibility Checklist — Step 6 QA gate

WCAG 2.1 AA — non-negotiable for handoff and dev-facing deliverables. For decks, warnings are acceptable with a footer note, but a critical blocker is any contrast fail on primary text or CTAs.

## Pre-audit: what to run and when

| intent | WCAG scope | blocker? |
|---|---|---|
| deck | contrast (primary text, CTA) | blocker; everything else — warning |
| prototype (lo-fi) | contrast, touch targets | warning only |
| prototype (mid-fi, hi-fi) | full WCAG 2.1 AA | blocker |
| handoff | full WCAG 2.1 AA + AAA stretches | blocker |
| research-enrichment | not run | — |

## Core checks (WCAG 2.1 AA)

### 1. Color contrast

- **Normal text (≤ 18px reg, ≤ 14px bold)**: min 4.5:1
- **Large text (> 18px reg, > 14px bold)**: min 3.0:1
- **Non-text UI (icons, borders, focus rings)**: min 3.0:1
- **Disabled states**: excluded from the requirement, but avoid < 3.0:1

Pre-compute contrast ratios for the brand's key pairs in your DS yaml (path: `product.design_system_spec`) under `contrast_pairs:` and have `design-bridge` read them during Step 6. Example structure:

```yaml
contrast_pairs:
  - { fg: "#222", bg: "#FFF", ratio: 16.1, usage: "body text on white" }
  - { fg: "#FFF", bg: "<brand.primary>", ratio: 4.9, usage: "CTA label on primary" }
  # … one entry per combination your brand actually uses
```

If a pair isn't listed, the QA gate computes it on the fly with a contrast library.

### 2. Touch target size

- Min **44×44 CSS px** (Apple HIG + WCAG 2.5.5 AAA).
- Spacing between interactive elements ≥ 8px.
- On mobile, enforce on product cards, filters, CTAs, tab switches.

### 3. Keyboard navigation

- All interactive elements reachable via Tab.
- Focus ring visible (contrast ≥ 3.0:1 against the background).
- Order is logical (top→bottom, left→right).
- Escape closes modals / dropdowns.
- Enter / Space activates buttons.

### 4. Screen reader labels

- Inputs have `<label>` (or `aria-label`).
- Icon-only buttons have `aria-label`.
- Images have `alt` with context (empty `alt=""` for decorative).
- Headings in a logical hierarchy (h1 → h2 → h3, no skip).
- Live regions (`aria-live`) for dynamic content updates.

### 5. Motion & animation

- Respect `prefers-reduced-motion`.
- Animations ≤ 5 s or have controls (pause/stop).
- Parallax / auto-play off by default.
- Flashes — no more than 3 per second.

### 6. Forms & errors

- Error messages — inline, descriptive, tell the user how to fix.
- Required fields marked (`*` + `aria-required="true"`).
- Field groups use `<fieldset>` + `<legend>`.
- Error states are conveyed by more than color alone (icon + text).

## Deck-specific checks

- Cover slide title: use the brand display font at a size that yields ≥ 4.5:1 against the cover background.
- Metric tiles: value text must pass contrast against the tile background (use brand subtle/tint colors from the DS yaml).
- CTA buttons (if embedded in a slide): label color on brand primary must clear 4.5:1.
- Charts: encode category differences with color **and** a secondary channel (pattern, label, shape).
- Footer caption: secondary-grey on white must clear 4.5:1 (it usually qualifies as large text at ≥ 10pt, so 3.0:1 is acceptable; still prefer 4.5:1).

## Handoff / prototype deep checks

- Every component has states: default, hover, focus, active, disabled, loading, error.
- Responsive: mobile (≤ 480), tablet (≤ 1024), desktop (> 1024).
- RTL support — if the brand targets Arabic/Hebrew audiences.
- i18n: allow string expansion ≤ 30% for translations (target language often longer than source).

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

If `blockers` is non-empty → Step 5 is blocked. Call it out conspicuously in the outline footer.

If only `warnings` → deliverable ships, but with a visible block in the footer / handoff:
> ⚠️ A11y audit warnings: <list>. Slide X / Component Y. Recommendation: <fix>.
