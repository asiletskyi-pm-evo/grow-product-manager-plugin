---
name: design-bridge
version: 0.5.0
description: Decks, hi-fi prototypes and design handoffs on your Design System or external design toolkit (Claude Design skills + Figma). Not quick diagrams, Mermaid or wireframes (diagram-prototyper). UA — «створи деку/презентацію», «hi-fi прототип/екран», «design handoff», «дизайн-рев'ю», «через мій дизайн-тулкіт». EN — "create a deck", "make a presentation", "build a prototype on our DS", "generate a hi-fi screen", "use my design toolkit", "generate handoff", "design review". Also UA — «передати дизайн у розробку». Orchestrates research-synthesis, ux-copy, design-critique, design-system, accessibility-review, design-handoff and Figma MCP; the next step after write-concept, requirements-creator, brainstorm-features or product-research when a deck or prototype is needed.
---

# Design Bridge

> **Path rule.** A bare `references/<file>.md` in this file is read from this skill's own `references/` if the file exists there, otherwise from the **shared** `references/` at the plugin root. Resolve the root as `${PLUGIN_ROOT}`, else `${CLAUDE_PLUGIN_ROOT}`, else the directory that contains `skills/`, found by walking up from this folder (`references/host-profiles.md` §6). Never continue without a protocol named here.

Orchestrator that connects the Grow PM pipeline with Claude Design skills, the Figma MCP, a brand Design System, and a pptx template. One skill handles four scenarios: **deck**, **prototype**, **handoff**, **research-enrichment**.

All brand-specific values (Design System spec, pptx theme, base template, brand tokens, Figma `fileKey`) are read from `local-context.md` — the plugin ships **no** hardcoded brand assets. Users configure their own brand via the `plugin-configurator` skill or by editing `local-context.md` manually.

**Routing host for external design toolkits.** This skill is also the single entry point for delegating hi-fi design / screen-generation work to an **external design toolkit** (a separate org-specific solution declared in `local-context.md` → `design_toolkits[]`). Other Grow PM skills never call a toolkit directly — they hand the design/prototype step here, and this skill applies `references/design-toolkit-protocol.md` (tier-0 provider check → delegate → ingest returns → publish/link/vault). The plugin ships **no** reference to any concrete toolkit; if `design_toolkits` is empty, behaviour is unchanged.

## When to invoke

**Auto-triggered from other skills** (Step D hook):

| Upstream skill | Trigger | Default intent |
|---|---|---|
| `write-concept` | after Step 8 (Design Bridge handoff) | `deck: subtype=feature` |
| `requirements-creator` | after Step 8 (Design Bridge handoff) | `handoff: components + copy + a11y` |
| `brainstorm-features` | after Step 8, ICE ranking top-3 | `prototype: lo-fi per top hypothesis` |
| `product-research` | after Step 8 (synthesis published) | `deck: subtype=research-highlights` |

> Only rows with a real hook in the upstream skill belong here. `cjm-research` and `meeting-processor` were listed until v2.0.2 but have no design-bridge hook — both route visualization to `diagram-prototyper` instead, which is the correct boundary (their outputs are process/funnel diagrams, not DS-themed decks).

**Manual** — when the user says:
- "make a deck", "create a presentation", "prep for direction review"
- "prototype", "mockup" (for a hypothesis / concept / requirements doc) — **when it should carry your Design System / brand**; a plain structural wireframe is `diagram-prototyper`. If the request doesn't say, ask: "branded (your DS tokens, ready to show) or plain structure (fast, to think with)?"
- "handoff to engineering", "ship the design to dev"
- "design review", "contrast check", "a11y audit"
- "pull context from Figma", "Figma screenshot"

## Integration prerequisite

Read and follow the fallback chain in `references/integration-strategy.md`. Key dependencies for this skill:

- **Claude Design plugin** (`design:*` sub-skills) — `research-synthesis` (4a), `ux-copy` (4c), `design-system` (4d), `accessibility-review` (4e), `design-critique` (4f), `design-handoff` (handoff path). Each is called by the step named beside it; this skill does not orchestrate `design:user-research` — Grow PM's own `product-research` owns primary research.
- **Figma MCP** — `whoami`, `get_libraries`, `search_design_system`, `get_variable_defs`, `get_design_context`, `get_screenshot`, `get_metadata`
- **pptx skill** (Anthropic) — for .pptx rendering via python-pptx
- **docx / pdf** — alternative deliverables
- **diagram-prototyper** (Grow PM) — for low-fi wireframes and flow diagrams
- **template-library** (Grow PM) — for resolving presentation templates
- **Confluence / Jira / Google Drive** — for publishing and attachments

Before gathering data, read `references/data-policy.md`. Figma embeds from competitive research or private files owned by other teams are **never** published to external decks.

## Local context prerequisite

**Before starting,** follow `references/local-context-protocol.md` (Step 0). Read `local-context.md`, pick the active product, and load design-specific context from its Design System section:

- `product.figma.ds_file_key` — for Figma MCP calls (if missing → graceful fallback with a placeholder)
- `product.design_system_spec` — path to your DS yaml (see `local-context.example.md` for the schema)
- `product.pptx_theme` — path to your pptx theme yaml
- `product.base_pptx` — path to your base pptx template
- `product.brand.primary`, `product.brand.dark`, `product.brand.font_primary`, `product.brand.font_display` — brand token overrides
- `product.tone_of_voice` — writing style guide (optional; used for slide titles and copy). Absent → neutral, plain product English/Ukrainian per `user.language`.
- `user.language` — deliverable language (default `en`)
- `design_toolkits[]` (product- or user-level) — declared external design toolkits for hi-fi delegation (see `references/design-toolkit-protocol.md`)

If `local-context.md` is missing → follow `local-context-protocol.md` Step 0b (launch `plugin-configurator`, let its mode selection decide).

If the **Design System** keys are absent, do **not** hard-redirect: there is no configurator step that writes them, so the redirect used to be a dead end. Instead say what is missing, point at the block in `local-context.example.md` → Design System for the user to fill, and continue on the fallbacks in "Failure modes" below — every Design System key is optional by design, and the deliverable degrades rather than blocks.

> **Judgment contract (Step 0j).** Per `references/local-context-protocol.md` Step 0j and `references/pm-mental-model.md`: note this run's
> judgment points (score, rank, verdict, priority, ship/kill, debate question) internally, with no output. A principle acts only through
> a step that implements it — until one exists here, this skill's questions, gates and output stay exactly as they are.

## Step T — Template Resolution

Runs only when `intent = deck`. For other intents, skip.

Follow `references/template-protocol.md`:
- `artifact_type: presentation`
- `subtype: {feature | research-highlights | ab-test-readout | release-readout}` (set in Step 1)
- `product_id: {active product}`
- `language: {en|uk|…}`

T-1..T-5 via `template-library`. If none found, fall back to `presentation-builtin-{subtype}` (shipped in `templates/built-in/presentation/`). If that's also missing, produce an ad-hoc outline using this SKILL.

## Workflow

### Step 0 — Context bootstrap

1. Load `local-context.md` → active product, user preferences.
2. Load the DS spec yaml at `product.design_system_spec` (path from local-context). If the path is unset or the file is missing → graceful fallback: use brand tokens from `product.brand.*`, or, as a last resort, a neutral default palette (dark text on white, 4.5:1 contrast).
3. If `intent = deck` → load `product.pptx_theme` yaml.
4. If the Figma MCP is available and `ds_file_key` is set → cache DS tokens via `get_variable_defs` (optional, for speed).
5. Load `design_toolkits[]` (product- then user-level). If none → skip Step 0.5 entirely and behave exactly as before.

### Step 0.5 — External toolkit routing (tier-0)

Follow `references/design-toolkit-protocol.md`. Runs only when a toolkit is declared AND the request needs hi-fi generation — resolved in Step 1: `intent=prototype` with `fidelity=hi-fi` (Q3), or `intent=handoff` with Q4a = "generate the screens".

> Ordering note: Steps 0.5 and T consume Step 1's answers, so despite their numbers they execute **after** Step 1 (as the end-to-end example shows). The numbering reflects the setup→routing→render grouping, not the call order.

1. Map the request to required **core-enum** capabilities (protocol §6).
2. Find `design_toolkits[]` entries whose `capabilities` cover them. None → continue to the normal built-in path (Step 5b Figma / Step 4f handoff). Two+ → `AskUserQuestion` which to use.
3. **Confirm with the user** before delegating (mandatory — never silent).
4. Build the input payload from `input_contract` (protocol §5) using upstream artifacts (concept / requirements / research / hypotheses). A conforming toolkit also works with an empty payload.
5. Invoke via `entry` (protocol §4: skill / mcp_tool / command / browser). Entry unavailable → note it, offer `setup_hint`, fall back to the built-in path (do not hard-fail).
6. Ingest `returns` (`figma_url` / `branch` / `files`) → carry into Step 7 (publish/link) and Step 8 (vault, with `design_delivery: true`).
7. **QA ownership** (protocol §7): if the toolkit declares `design-review`, do NOT re-run Step 4d/4e on its output. If it does not, Step 6 QA still applies.

Data policy (protocol §9): `data_locality: external` → `references/data-policy.md` constrains the payload; `local` → in-session, internal context allowed.

### Step 1 — Intent & subtype detection

Via `AskUserQuestion` if not passed from an upstream skill:

**Q1. What deliverable is needed?**
- deck (.pptx presentation)
- prototype (wireframe / lo-fi mockup)
- handoff (developer spec for front-end)
- research-enrichment (run sources through `design:research-synthesis` and append to the upstream artifact)

**Q2 (deck only). Which deck subtype?** Lengths are `target (max)` from `references/deck-subtypes.yaml` — that file is the source of truth; do not restate different numbers here.
- feature (feature pitch — 10 slides, max 15; typical for direction review)
- research-highlights (research dump — 10 slides, max 14)
- ab-test-readout (A/B test results — 6 slides, max 8)
- release-readout (release / sprint summary — 7 slides, max 10)

**Q3 (prototype only). Fidelity level?**
- lo-fi (Mermaid flow / ASCII wireframe)
- mid-fi (HTML with inline brand tokens from local-context)
- hi-fi (delegate to an external toolkit if one covers it — Step 0.5; else send to Figma via `use_figma`, Full seat)

**Q4a (handoff only). Does this handoff need screens generated?** This is the input Step 0.5 branches on — without it, "handoff with screen generation" is undecidable.
- **document existing designs** (default) — the screens exist (Figma link / shipped UI); the handoff specs them. No toolkit delegation.
- **generate the screens** — the handoff needs new hi-fi screens first → Step 0.5 routes to a declared toolkit (`screen-generation` capability); tier-0 fallback if none covers it.

**Q4b (handoff only). Delivery target?**
- dedicated Confluence page (markdown + screenshots)
- inline in a Jira ticket as attachment
- standalone .md in `deliverables/handoffs/`

### Step 2 — Audience & constraints

Via `AskUserQuestion`:
- **Audience** (default from upstream): direction_review / team / product_leads / stakeholders / c-level / customer / dev_handoff — the same set `deck-subtypes.yaml` uses in `typical_audience` (upstream skills pass values from it, e.g. brainstorm-features sends `product_leads`)
- **Length** (for deck): recommended 10; cap 20
- **Language**: from local-context `user.language`; user can override
- **Brand mode**: `brand_default` (uses `product.brand.*`) | `custom` | `minimal`
- **Figma embeds**: yes / no / only if the user provides a link

### Step 3 — Source extraction

Depending on **upstream**, pull the fields the deliverable needs from a Confluence page (`write-concept`, `requirements-creator`), research output (`product-research`, `cjm-research`, `meeting-processor`), brainstorm output (`brainstorm-features`), A/B test data (`product-analysis`, Tableau) or user-provided text / files. The per-source field list (a–e) — what to parse and extract from each — lives in `references/design-bridge-playbook.md` (skill-local). Read it before extracting from an upstream artifact.

Normalize into **Deck IR** (intermediate representation).

**Read `references/deck-subtypes.yaml` first** and look the subtype up by its key — it gives the slide-by-slide outline (index, layout, role, required slots, media hint) for the chosen subtype, plus `target_length` / `max_length`. Build the IR's `slides` list from that outline and fill the slots from the sources extracted above; a slot with no source becomes an Open Question, not an invented fact. If the subtype has no entry, fall back to the generic structure below.

> The yaml's header has always said "Read by design-bridge Step 3", but this step never cited it — combined with the `feature`/`feature-concept` key split (fixed in v2.0.2), the outlines were unreachable by the documented lookup.

```yaml
deck:
  subtype: <from Step 1 Q2 — must match a key in deck-subtypes.yaml>
  title: <string>
  subtitle: <string>
  presenter: <string>
  date: <ISO>
  audience: <string>
  language: <lang code>
  slides:
    - layout: <title|section|two-col|metric|chart|quote|cta>
      title: <string>
      body: <string|list>
      media: [<image path|figma node ref|chart spec>]
      speaker_notes: <string>
```

### Step 4 — Design-skill hooks

#### 4a. User research → research-synthesis

**Trigger**: `intent=deck` AND `subtype=research-highlights` AND sources include interview transcripts / survey data.
**Call**: `design:research-synthesis` with raw material.
**Output**: structured themes and recommendations — populate slides (section, quote).

#### 4b. UX copy polish

**Trigger**: `intent ∈ {deck, prototype, handoff}`.
**Call**: `design:ux-copy` with:
- slide titles (max 72 chars, matching `product.tone_of_voice`)
- CTA labels (on cta slides and prototype buttons)
- error/empty/loading states (on prototypes)

**Output**: refined headings and microcopy. Overwrite the corresponding fields in Deck IR / Prototype IR.

#### 4c. Design critique

**Trigger**: `intent=deck` AND `slides_count ≥ 5`.
**Call**: `design:design-critique` on the outline + key visuals.
**Output**: list of issues:
- "Slide 4 has 7 bullets — split"
- "Slide 7 (MVP scope) — add 'Out of scope'"
- "Low-contrast combo on slide 2"

Auto-fix what can be fixed (split, reorder, add section); for everything else, ask the user for confirmation.

#### 4d. Design system check

**Trigger**: `intent ∈ {prototype, handoff}`.
**Call**: `design:design-system` against the DS spec at `product.design_system_spec`.
**Output**: list of DS violations — hardcoded colors, wrong radius, missing tokens. Fix inline or add to Open Questions.

#### 4e. Accessibility audit

**Trigger**: `intent ∈ {deck, prototype, handoff}` — **always, regardless of audience**. Scope and blocker-severity come from `references/a11y-checklist.md` → "Pre-audit: what to run and when":

| intent | WCAG scope | blocker? |
|---|---|---|
| deck | contrast (primary text, CTA) | blocker; everything else — warning |
| prototype (lo-fi) | contrast, touch targets | warning only |
| prototype (mid-fi, hi-fi) | full WCAG 2.1 AA | blocker |
| handoff | full WCAG 2.1 AA + AAA stretches | blocker |
| research-enrichment | not run | — |

> Until v2.1.0 this step also required `audience=c-level OR dev_handoff OR user explicitly asked`, so a **handoff with `audience=team` skipped the audit entirely** — and Step 6's "A11y: if Step 4e ran" then never blocked it. That directly contradicted the checklist above, Quality Standards ("WCAG 2.1 AA — non-negotiable for handoff") and the failure-mode table ("A11y fail on handoff | release blocker"). The audience does not change whether a disabled user can use the thing.

**Call**: `design:accessibility-review` (WCAG 2.1 AA):
- contrast ratios
- touch targets ≥ 44×44
- keyboard nav
- screen reader labels

**Output**: pass/fail report. Blocker-severity findings block the Step 6 QA gate; warnings ship with a visible note in the footer/handoff.

#### 4f. Developer handoff

**Trigger**: `intent=handoff`.
**Call**: `design:design-handoff`.
**Output**: spec sheet — layout, tokens, component props, states, breakpoints, animation. This is the primary deliverable in the handoff scenario.

#### 4g. Figma context / screenshots

**Trigger**: `embeds=yes` AND (Figma URL in sources OR user provided a link).

Pulls the linked frame's design context and a screenshot into the Deck IR as slide media; a View seat skips any hi-fi edit, competitive-research frames are never embedded, private brand frames go only into internal decks, and a 403 becomes a placeholder. The full procedure — URL parsing, the `get_design_context` / `get_screenshot` calls, the View-seat rule and the embed policy from `references/data-policy.md` — lives in `references/figma-playbook.md` → "Step 4g — Figma context / screenshots" (skill-local). Read it when the trigger fires.

### Step 5 — Render deliverable

Routing by `intent`:

#### 5a. intent=deck → .pptx

Renders the Deck IR on `product.base_pptx` (blank `Presentation()` when unset) with the `product.pptx_theme` colours and fonts, saves `{vault_root}/Presentations/{product}/{date}-{slug}-{subtype}.pptx` plus a markdown outline companion; pptx skill unavailable → outline.md + outline.html. The full procedure — layout mapping, placeholder / shape filling, media embedding and save paths — lives in `references/design-bridge-playbook.md` (skill-local). Read it when rendering a deck.

#### 5b. intent=prototype → HTML / Mermaid / Figma

- lo-fi → `diagram-prototyper` (Mermaid + ASCII)
- mid-fi → HTML with inline brand tokens (from `product.brand.*`) + Tailwind-compatible classes
- hi-fi → **if Step 0.5 routed to an external toolkit** → use its `returns` (Figma URL / branch / files) as the deliverable; **else** → `use_figma(…)` (Full seat only) → creates a Figma frame

Save to `{vault_root}/Prototypes/{product}/{date}-{slug}/`.

#### 5c. intent=handoff → Confluence page / .md

Spec sheet from `design:design-handoff` output + Figma screenshots + a11y checklist.

#### 5d. intent=research-enrichment → append to upstream

Does not create a separate file — returns structured themes to the upstream skill, which then publishes.

### Step 6 — QA gate

Required for `intent ∈ {deck, prototype, handoff}`:

- **Contrast** (WCAG AA): all key pairs from `qa_rules.contrast.pairs_to_check` in your theme yaml — **if no theme yaml or no `qa_rules`, check the default pairs**: title/background, body/background, CTA text/CTA fill
- **Slide count** (deck): within the subtype's `max_length` from `references/deck-subtypes.yaml` — the one length rule. (`qa_rules.max_over_preference_ratio` overrides it when the theme yaml defines it.)
- **Bullets per slide** (deck): ≤ 5
- **Title length**: ≤ 72 chars
- **Brand usage**: at least 2 slides using `product.brand.primary`
- **Empty slots**: no `{{…}}`, `TODO`, placeholder titles, or "Lorem ipsum"
- **Font check**: `product.brand.font_primary` + display font available (if not — warning in the outline footer)
- **A11y**: Step 4e always ran for deck/prototype/handoff — blocker-severity findings (per the intent's row in `references/a11y-checklist.md`) block the deliverable; warnings go into the footer notice

If any check fails → fix + rerun QA; escalate to the user if the blocker is not auto-fixable.

### Step 7 — Publish & link

Depending on the deliverable:

- **deck** → attach to:
  - upstream Confluence page (if any) as attachment
  - Jira ticket (if source = ticket) as comment with link
  - both, if upstream has both
- **prototype** → link from the concept / requirements page (inline)
- **handoff** → new Confluence page in the design space, or attach to a Jira epic
- **research-enrichment** → inline in the upstream skill

Then:
- Update the Obsidian Vault MOC: `Presentations/{product}/` or `Prototypes/{product}/` or `Handoffs/{product}/` (if `vault_level > L0`)
- Add `design_sources` to the artifact frontmatter (Figma URLs, screenshot paths)
- Return a user-friendly summary with computer:// links

## Step 8 — Vault save (optional)

If `vault_level > L0` and `sync_mode != off`:

```
vault_save({
  type: "presentation" | "prototype" | "handoff",
  product: active_product,
  skill: "design-bridge",
  skill_version: "0.5.0",
  tags: [subtype, audience, language, figma_embeds?],
  content: artifact_content,
  related: [upstream_artifact_id, figma_urls],
  extra_frontmatter: {
    subtype: <from Step 1>,
    audience: <from Step 2>,
    slide_count: N,
    figma_embeds: [urls],
    a11y_status: pass|warn|fail,
    // when the deliverable came from an external toolkit (Step 0.5):
    design_delivery: true,
    toolkit_id: <id>,
    toolkit_returns: [figma_url?, branch?, files?]
  }
})
```

## Additional Resources

- **`references/local-context-protocol.md`** — Step 0 protocol
- **`references/design-toolkit-protocol.md`** — Step 0.5 (external toolkit routing, delegation contract, capabilities)
- **`references/template-protocol.md`** — Step T (resolve presentation template)
- **`references/integration-strategy.md`** — MCP → Registry → Browser fallback
- **`references/data-policy.md`** — Figma embed and publish restrictions
- **`references/deck-subtypes.yaml`** — slide outlines for all 4 subtypes (layout sequence, required slots, recommended media)
- **`references/figma-playbook.md`** — how to resolve a `fileKey`, safe patterns, known limitations (View seat), Step 4g procedure (frame context, screenshots, embed policy)
- **`references/a11y-checklist.md`** — checklist for Step 6 QA
- **`references/design-bridge-playbook.md`** — skill-local: Step 3 per-source extraction (a–e), Step 5a pptx rendering, the failure-mode table, the end-to-end concept → deck example, version history
- **`references/vault-protocol.md`** — Step 8 vault save
- **`local-context.example.md`** → Design System section — schema for brand configuration (DS spec path, pptx theme path, base pptx path, brand tokens, Figma file key)

## Quality standards

- Always check Figma seat before attempting a hi-fi prototype
- Never publish a deck externally with screenshots of private Figma files
- WCAG 2.1 AA — non-negotiable for handoff and dev-facing deliverables
- Brand tokens are sourced from `product.brand.*` — hardcoded brand values are forbidden in generated artifacts
- Every deck must have cover + ask/next-steps slides, even if shorter than 6 slides
- Every data-bearing slide must include a source line (`caption: "Source: …"`) when numbers come from upstream
- Multilingual support (see `product.available_languages` in local-context) across all outputs

## Failure modes & fallbacks

Every dependency degrades rather than blocks: a missing base pptx, template, theme, DS yaml or Design System keys fall back to built-in or neutral defaults; a missing `design:*` plugin or pptx skill to native / outline output; an unavailable toolkit to the built-in path; thin source content (< 100 words) → ask the user, never lorem ipsum. The Step 6 QA gate still runs on defaults, and an a11y fail on handoff is a release blocker (a footer warning in deck mode). The full failure → behaviour table lives in `references/design-bridge-playbook.md` (skill-local). Read it when any dependency is missing, unparseable or fails at runtime.

## End-to-end example: concept → deck

A worked trace of a direction-review deck built from a concept page (Step 0 → 1 → 2 → T → 3 → 4b/4c/4g → 5a → 6 → 7 → 8, with Step T running after Step 1) lives in `references/design-bridge-playbook.md` (skill-local). Read it when unsure of the call order.

## Changelog

Version history up to 0.3.0 lives in `references/design-bridge-playbook.md` → History (skill-local); later releases are recorded in `CHANGELOG.md`.
