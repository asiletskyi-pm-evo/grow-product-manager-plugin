# Design Bridge playbook — source extraction (Step 3), deck rendering (Step 5a), failure modes, worked example, history

> Part of `design-bridge`. Loaded on demand: Step 3 before extracting from an upstream artifact, Step 5a when rendering a deck, the failure-mode table when a dependency is missing or fails at runtime, the end-to-end example when checking the call order, History for version context. Step headings, triggers, the Deck IR schema, the copy / DS / a11y gates (4b, 4d, 4e), the Step 6 QA gate and the vault save stay in SKILL.md.

## Step 3 — Source extraction by upstream

Depending on **upstream**:

**a. Confluence page** (`write-concept`, `requirements-creator`) — parse via `getConfluencePage`; extract:
- `title`, `problem_statement`, `solution_summary`, `key_metrics`, `scope`, `phases`, `risks`, `ask`
- any embedded diagram URLs → remap in Step 4c

**b. Research output** (`product-research`, `cjm-research`, `meeting-processor`) — parse markdown:
- themes, insights, recommendations
- quotes (for research decks)
- anomalies / funnel drops (for CJM decks)

**c. Brainstorm output** (`brainstorm-features`) — json/md:
- top-3 hypotheses with ICE scores
- mapped funnel steps

**d. A/B test data** (`product-analysis`, Tableau) — csv/markdown:
- metrics, control vs treatment, CI, lift

**e. User-provided** — raw text / pasted context / uploaded files.

## Step 5a — intent=deck → .pptx

1. Load the base template from `product.base_pptx` (path in local-context): `Presentation(<base_pptx_path>)`. If unset or missing → create a blank `Presentation()` and position shapes manually.
2. Load the theme yaml from `product.pptx_theme`.
3. For each slide in Deck IR:
   - resolve the layout name via `implementation_hints.slide_layout_index.mapping`
   - `slide_layout = prs.slide_layouts.get_by_name(<mapping>)`
   - `new_slide = prs.slides.add_slide(slide_layout)`
   - fill placeholders or add shapes by rect coordinates (see your theme yaml → `layouts.<name>.elements`)
   - apply colors/fonts from `theme.colors` / `theme.typography` (values come from `product.brand.*`)
4. Embed media (images, charts).
5. Save: `{vault_root}/Presentations/{product}/{date}-{slug}-{subtype}.pptx`.
6. In parallel, produce a markdown outline companion in the same folder (`.md`) for quick review.

Fallback: if the pptx skill is unavailable → outline.md + outline.html (copy-pasteable into Google Slides).

## Failure modes & fallbacks

| Failure | Behavior |
|---|---|
| `product.base_pptx` unset or missing | blank `Presentation()` + explicit shape positioning from theme yaml rect coords |
| Template not found | fall back to `presentation-builtin-{subtype}`; if that's missing too — ad-hoc outline |
| DS yaml won't parse | fall back to brand tokens in `product.brand.*`; if those are missing — neutral defaults (dark text on white) |
| `product.pptx_theme` unset / theme yaml missing / no `qa_rules` | Step 6 QA still runs on defaults: WCAG AA on title/body/CTA pairs, slide max = the subtype's `max_length` from `deck-subtypes.yaml`. The gate never silently no-ops for want of config — it is the only blocking gate on the deck path |
| No Design System keys at all (fresh install) | proceed on neutral defaults; name the missing keys once in the outline footer, do not block or redirect |
| Figma MCP 403 / seat=View | skip hi-fi; embed only screenshots (if `get_screenshot` works); on fail — placeholder |
| `design:*` plugin missing | propose install; fall back to native rewrite (ux-copy), manual critique outline |
| pptx skill unavailable | fall back to outline.md + outline.html |
| Source content < 100 words | ask user to fill manually; do not generate "lorem ipsum" |
| A11y fail on handoff | release blocker; in deck mode — footer warning |
| Language not in `available_languages` | pick the closest and note it in the outline |
| `design_toolkits` empty / absent | skip Step 0.5; built-in hi-fi path (Figma) — unchanged behaviour |
| Declared toolkit entry unavailable at runtime | note it, offer `setup_hint`, fall back to built-in path; never hard-fail |
| Two+ toolkits match one request | `AskUserQuestion` which to use |
| Toolkit `contract_version` mismatch | warn (don't block); verify payload/return shape |

## End-to-end example: concept → deck

**Trigger**: user says "make a direction-review deck from concept PROJ-1234 (Q&A — Product Page Integration)".

```
design-bridge:
  Step 0  → load local-context + DS yaml (from product.design_system_spec)
            + theme yaml (from product.pptx_theme)
  Step 1  → intent=deck (user explicit), subtype=feature
  Step 2  → audience=direction_review (default), language=en, length=10,
            brand=brand_default, embeds=ask
  Step T  → template-library.resolve(presentation, feature, <product>, en)
            → selected: presentation-builtin-feature@1.0.0
  Step 3  → parse Confluence PROJ-1234 page → Deck IR populated:
              title="Q&A on Product Page", subtitle="Direction review",
              problem, solution, metrics, ask, scope, phases
  Step 4b → design:ux-copy polishes titles + CTAs (max 72 chars, brand tone)
  Step 4c → design:design-critique flags:
              • Slide 4 (Evidence) has 7 bullets → split into 4a+4b
              • Slide 7 (MVP scope) → add "Out of scope" sub-section
  Step 4g → user pastes a Figma frame URL for the Q&A block
            → get_screenshot(nodeId, ds_file_key) → image for slide 7
  Step 5a → open product.base_pptx, apply theme
            → 10 slides added via slide_layouts.get_by_name(…)
            → save: Presentations/<product>/2026-04-20-qa-product-page-direction.pptx
  Step 6  → QA pass (contrast, 10 slides, no empty slots, brand font OK,
            brand.primary used on 3 slides)
  Step 7  → attach to PROJ-1234 Confluence page as attachment
            → comment in Jira PROJ-1234 with computer:// link
            → update Obsidian Vault: Presentations/<product>/2026-04-20/
  Step 8  → vault_save(type=presentation, subtype=feature, …)
  → output: "[View deck](computer://…/2026-04-20-qa-product-page-direction.pptx)"
```

## History

- `0.3.0` (2026-07-10) — Became the routing host for external design toolkits. Added Step 0.5 (tier-0 provider check → delegate → ingest returns) per `references/design-toolkit-protocol.md`. hi-fi prototype now delegates to a declared toolkit when one covers the request, else falls back to the Figma path (unchanged when `design_toolkits` is empty). QA-ownership rule (no double review), vault `design_delivery` marker, new failure modes. No hardcoded toolkit reference — all org-specifics live in `local-context.md`.
- `0.2.0` (2026-04-20) — Removed hardcoded brand assets and `design-integration/` coupling. All brand specifics (DS spec, pptx theme, base pptx, brand tokens, Figma fileKey) now read from `local-context.md`. English-only copy. Added graceful fallbacks when brand config is partial or missing.
- `0.1.0` (2026-04-20) — Initial release. Supports 4 intents, 4 deck subtypes, 7 design-skill hooks, Figma MCP integration.
