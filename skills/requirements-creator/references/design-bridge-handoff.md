# Design Bridge handoff — Step 8 (Optional)

> Part of `requirements-creator`. Loaded on demand at Step 8, after Step 7 skill chaining. The `design-bridge` requirement line and a one-paragraph summary stay in SKILL.md.

Requirements often serve as the entry point for developer handoff and low-fi prototypes. Via `AskUserQuestion`:

> "Requirements published. Create a design-side deliverable?"
> 1. **Developer handoff spec** — complete specification for front-end (tokens, components, states, breakpoints, a11y) — recommended if requirements included UI changes
> 2. **Low-fi UI prototype** — for visual validation before development
> 3. **Deck for dev-review** — 6-8 slides with scope + UI flow + edge cases
> 4. **Skip**

IF user selects 1 → invoke `design-bridge` with:
- `intent: handoff`
- `source: requirements_page_url`
- `a11y_audit: true` (mandatory for handoff)
- `figma_context: from requirements_page OR ask user`

IF user selects 2 → invoke `design-bridge` with:
- `intent: prototype`
- `source: requirements_page_url`
- `fidelity: lo-fi | mid-fi` (ask)

IF user selects 3 → invoke `design-bridge` with:
- `intent: deck`
- `subtype: feature` (closest match to requirements pitch)
- `audience: dev_handoff`
- `length: 6-8`

Fallback: if `design-bridge` is not installed — display: "Install `grow-product-manager` v1.10.0+ to enable design-bridge handoffs." Do not block the workflow.
