# Design Bridge playbook — source extraction (Step 3), Prototype IR, prototype as spec (Step 9), deck rendering (Step 5a: pptx, HTML deck, the host's deck), publishing an existing deck, failure modes, worked example, role defaults, history

> Part of `design-bridge`. Loaded on demand: Step 3 before extracting from an upstream artifact (and before Step 2 for a build-first hand-off), the Prototype IR when Step 3 builds a prototype and at 5b, Prototype as spec when Step 9 shows its line, Step 5a when rendering a deck, the failure-mode table when a dependency is missing or fails at runtime, the end-to-end example when checking the call order, Role defaults when Step 1 asks a question under a role default, History for version context. Step headings, triggers, the Deck IR schema, the copy / DS / a11y gates (4b, 4d, 4e), the Step 6 QA gate and the vault save stay in SKILL.md.

## Step 3 — Source extraction by upstream

Depending on **upstream**:

**a. Confluence page** (`write-concept`, `requirements-creator`) — parse via `getConfluencePage`; extract:
- `title`, `problem_statement`, `solution_summary`, `key_metrics`, `scope`, `phases`, `risks`, `ask`
- any embedded diagram URLs → remap in Step 4c
- `prototype_ref` (write-concept Step 8 after a build-first run, since v3.9.0): the Prototype IR is read from that prototype, and 5b edits it in place — no new prototype is drawn

**b. Research output** (`product-research`, `cjm-research`, `meeting-processor`) — parse markdown:
- themes, insights, recommendations
- quotes (for research decks) — copied verbatim from the upstream, with its speaker and date
- anomalies / funnel drops (for CJM decks), with any hand-back line the upstream attached to them

**c. Brainstorm output** (`brainstorm-features`) — json/md:
- top-3 hypotheses with ICE scores
- mapped funnel steps

**d. A/B test data** (`product-analysis`, Tableau) — csv/markdown:
- metrics, control vs treatment, CI, lift

**e. User-provided** — raw text / pasted context / uploaded files.

**f. Build-first brief** (`write-concept` Step 1, since v3.9.0; `references/judgment-points.md` §8) — the confirmed brief and its riskiest assumption, handed over with `intent: prototype`, `fidelity: lo-fi`, `source: brief` and `assumption`. Steps 1–2 ask nothing for this upstream: audience `team`, brand mode `minimal`, Figma embeds `no` (a Figma link the brief names becomes the IR's reference, not an embed), language from `user.language`. Extract:
- the problem, the target user, the proposed solution and the assumption;
- only the screens and states a real user has to meet to test the assumption (typically 2–5 screens) — the Prototype IR is scoped to the assumption, not the whole feature;
- the brief's claims keep the labels the brief gives them; the brief is not saved anew here.

**Evidence labels in the Deck IR (since v3.8.0).** The class words and grammar are `references/pm-mental-model.md` §4; the class of an input comes from `references/data-integrity-protocol.md` Gate Check 6 (6a). This step only carries labels — it runs no data gate and adds no question.
- **Carry, never upgrade.** Every number, quote and benchmark enters the IR with the label its upstream gives it, into the slot's caption or attribution. An unlabelled claim from an artifact saved before v3.8.0 takes the class of the source it cites, else `reported` (the artifact) — never `measured`, because this skill re-verifies nothing.
- **Read here, not upstream** (d., e.): this skill runs no data gate, so a figure it takes in itself — typed or pasted, an uploaded export, a dashboard read straight from Tableau — is `reported` (who, or which file or dashboard · not gate-checked). `measured` arrives only labelled by an upstream skill that ran its gate (product-analysis, cjm-research, product-reporter's Jira counts).
- **Quotes** are verbatim from the upstream's source, with who and when; a paraphrase loses its quote marks. A quote never comes from a synthesis, an AI summary or a persona.
- **Themes from 4a** (`design:research-synthesis`) keep the class of the material they synthesise (`reported` for real interviews); a theme with no traceable source item is `[assumed — …]`.
- **Synthetic input** (persona answers, synthetic users, model-written "user" quotes) is `simulated`: it never fills a theme, quote, metric or evidence slot and is never counted in "Method & sample"; it goes to one "Simulated input — hypotheses only" line.
- **Hand-back lines** the upstream attached travel with their claim: in the caption of the slide that cites it for internal audiences, only in the outline companion for an external one. A before / after change with no control reads "coincides with", never "caused by".
- **Forward-looking numbers** (targets, forecasts, expected impact) carry no class — only their forecast / illustrative marker.

## Prototype IR (since v3.9.0)

The prototype's counterpart of the Deck IR. Built at Step 3 for `intent=prototype` from the source (a–f), refined by 4b (state copy), 4d (DS components; a violation not fixed inline goes to `open_questions`) and 4e (a11y notes), and completed at 5b with each screen's rendered reference:
- lo-fi — diagram-prototyper fills it when called with `return_to: design-bridge`, which 5b passes only for the build-first hand-off: Mermaid node ids or wireframe block ids; any other lo-fi prototype is drawn without it, its IR keeps no screen references, and Step 9 shows no line;
- mid-fi — the HTML section id of each screen;
- hi-fi — the Figma frame node id (`use_figma`), or, for a toolkit's Figma URL, `get_metadata`: frames → screens, prototype connections → transitions. A toolkit return with no readable Figma file (a code branch, files only, a 403) leaves the IR without screen references, and Step 9 shows no line.

```yaml
prototype:
  fidelity: <lo-fi | mid-fi | hi-fi>
  source: <upstream artifact, the build-first brief, or user text>
  assumption: <the assumption it tests, or none>
  screens:
    - id: <S1>
      purpose: <what the user does here, one sentence>
      components: [<DS components from 4d>]
      states:                  # default, plus empty / error / loading wherever the screen loads data or takes input, no-permission / offline wherever access or the connection can fail
        - name: <default | empty | error | loading | no-permission | offline | other>
          shown: <yes | no>
          copy: <microcopy from 4b>
      a11y: [<4e findings>]
      ref: <Mermaid node id | wireframe block id | HTML section id | Figma frame node id>
  transitions:
    - from: <S1>
      to: <S2>
      trigger: <user action or system event>
  open_questions: [<states not shown, DS violations not fixed>]
```

Rules:
- A state the screen needs but the prototype does not show is recorded `shown: no` — never drawn after the fact to complete the IR.
- The IR describes the prototype; it adds no evidence of its own. The prototype is `reported` (file, frame) — intended UI, never `observed` user behaviour (`references/data-integrity-protocol.md` 6a).

## Prototype as spec — Step 9 (since v3.9.0)

**Payload to requirements-creator** (when the user takes the Step 9 line):
- `prototype_ref` — the vault path, the Figma URL or the toolkit returns;
- `prototype_ir` — the IR above;
- the upstream — the concept, the build-first brief or the user's text — and the assumption, when there is one;
- `real_user_sessions` — the product-research run on this prototype, or `none`;
- the class — the prototype is `reported` (file, frame); session results keep the class product-research gave them.

**Mapping** (applied by requirements-creator; nothing is asked to fill a gap):

| Prototype IR | Spec |
|---|---|
| a screen | one functional-requirement row — purpose → the requirement; components and a11y → its notes |
| a state with `shown: yes` | one Given / When / Then acceptance criterion — Given the screen, When the trigger or condition, Then what the state shows |
| a transition | the flow between the rows it connects |
| a state with `shown: no`, an item in `open_questions` | an Open Question — never an invented acceptance criterion |
| `prototype_ref` | the link in the spec's UI & UX section |

A claim about users made on the prototype alone ("users will understand X") stays `assumed` until real-user sessions back it.

**Payload to product-research** (the "show it to 3–5 real users" suggestion, first when the prototype tests an assumption): `prototype_ref`, the assumption, the screens in flow order from the IR, and a request for 3–5 sessions with real users of the target segment. What the sessions show comes back with its own class (`observed` / `reported`, with the session); the prototype itself is never evidence of what users do.

## Step 5a — intent=deck → .pptx, HTML deck, the host's deck

All three renders take the same Deck IR and the same tokens (`product.brand.*`, the DS spec, the deck theme). A render never adds, drops or rewrites a slide, a word, a number or a source caption; what one render cannot show (an animation, a native chart) is drawn as the closest static form, never left out.

### .pptx

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

### HTML deck (since v0.10.0)

One file, `{date}-{slug}-{subtype}.html`, beside the `.pptx`. It is what goes to a place that takes a page — Atlassian Artifacts (`text/html`), ARTIFACT `page` — and a file the user can open anywhere.

- **Structure.** `<!doctype html>`, `lang` from `user.language`, `<title>` = the deck title; `:root { color-scheme: light; }` with the tokens as CSS custom properties (primary, dark, background, text, accent; fonts). One `<section class="slide">` per IR slide, in order, with `aria-label="Slide n of N: <title>"`; 16:9 on a 1280×720 design grid, scaled to the window by a few lines of inline script — no framework.
- **Navigation.** ←/→, PageUp/PageDown, Space, Home/End; a counter «n / N»; `#n` in the address opens slide n; `n` shows the speaker notes (`<aside class="notes">`, hidden by default); print styles give one slide per page.
- **Content.** The IR's titles, bodies, tables and source captions (with their evidence class) as text, never as pictures of text; a chart as inline SVG drawn from the IR's chart spec, from its numbers only; a diagram redrawn as inline SVG in the theme's colours, its arrowheads drawn as shapes on their own slide — an `id` shared between slides (an SVG `marker` defined once and used on every slide) resolves to the first slide's copy, which is hidden, and the arrows vanish; a picture inlined as a `data:` URI with its alt text (a picture whose only alt is a file name is decorative: `alt=""`) (a Figma screenshot only under the embed rules of `references/data-policy.md`).
- **No external request.** No `<script src>`, no stylesheet or font loaded by URL, no `@import`, no `url(http…)`, no remote image, no analytics. A link the reader may click (`<a href>` to the upstream page) is not a request and stays.
- **Font.** The theme's font is embedded as a base64 `@font-face` when its file is on this machine — among the user's design assets or installed fonts — and its licence allows embedding (an OFL font does); otherwise `font-family: <font_primary>, system-ui, sans-serif`, and the outline's footer says once that the system fallback was used.

**File checks** (Step 6, on top of the deck checks): the count of `section.slide` equals the IR's slides; every slide has its title; no `{{…}}`, `TODO` or «Lorem ipsum»; no external request by the rule above — search the file for `src=`, `srcset=`, `poster=` and `href=` outside `<a>` whose value starts with `http` or `//` (either quote), `@import`, `url(` with an `http` or `//` value (quoted or not), `fetch(`, `XMLHttpRequest`, `<meta http-equiv="refresh"`; every `id` used once in the file (markers, gradients, clip paths); `lang` is the deck's language; the file's size said in the summary (a host may refuse a large one); the contrast pairs computed from the CSS custom properties. Where the session has a browser, open the file and take one screenshot each of the cover, one data slide and the last slide — clipped or overflowing text, a missing chart or a wrong colour fails the check.

### A document service's deck (DOCS `connector` or a registry record that publishes `deck`)

The `.pptx` itself, imported as the service's presentation in the user's drive (the service's own import tool); a new version replaces the same presentation's content by its id. Its sharing is the drive's: the question names who can open that folder (`native-surfaces.md` §3).

### The host's deck (ARTIFACT `typed`, kind deck, since v0.10.0)

Built at Step 7, when the user picks it, from the IR as data — per slide its title, body, table, notes, media and source caption; the host adds no content of its own.

- **Design system.** The host's design system for the product when the host lists one — its title equal to the DS spec's `ds_name` (or `<product> Design System`), never a loose match. Without one, ask once per product in a run: «Створити дизайн-систему «<product>» для дек у твоєму акаунті з токенів продукту (кольори, шрифти, лого з DS spec)? Бачиш лише ти. Так / ні.» — built from the same tokens, never from a guess. «Ні» → the host's deck is not built in this run (an off-brand deck is not offered); the other places stay.
- **Faithful to the source's paint.** A translucent fill stays translucent (its alpha as `rgba`; a near-invisible one is no fill, never a solid block), and a text box shorter than its text keeps its text's size — set the host's no-shrink option where it has one — the way the `.pptx` lets text run past its box; a host that shrinks or clips such text breaks the layout.
- **QA** on the built deck as on the other renders (Step 6), before the link is given: building it in the user's private account is the publication the user said yes to, and nobody else sees it before the check; where the session cannot open the host's page (not signed in), the user's look at it is the check, and the run says so.
- **A new version** is a publication to the same link (`references/artifact-publishing.md` §6).

## Publish an existing deck (since v0.10.0)

«Опублікуй деку <назва>» — a deck that exists in the vault. **The deck's note** is the note of `type: presentation` that names or sits beside its `.pptx` (`{date}-{slug}-{subtype}.pptx`); with both an outline companion and a vault note of one deck, it is the vault note — they are one deck, never two to choose between. The deck's key is `design-bridge/<product>/<slug>-<subtype>` (`references/artifact-publishing.md` §5).

1. **Find** the deck's note by the name the user gave (the vault path, or `ctx search` with the presentation type); two different decks match → ask which. No `.pptx` → rebuild from the note's outline alone and say so.
2. **Read** the note (frontmatter: subtype, audience, slide count, language, template; body: the outline and the speaker notes) and the `.pptx` — with python-pptx, or with the standard library where it is not installed (a `.pptx` is a zip of XML: `ppt/presentation.xml` for the order, `ppt/slides/slideN.xml` for shapes and text, `ppt/notesSlides/` for notes, `ppt/media/` for pictures): per slide the layout name, the title, the text frames with their bullet levels, tables, notes, pictures, native charts' data, and each shape's place, fill (with its transparency) and line.
3. **Rebuild the IR**: the slides in the `.pptx` order; the layout mapped back through `implementation_hints.slide_layout_index.mapping`; titles, bodies, notes and source captions verbatim, evidence labels as they are; a diagram drawn with shapes is redrawn as SVG in the theme's colours from its own shapes and words — no new box, arrow or word; pictures kept.
4. **Check** that the IR has the `.pptx`'s slide count and every title, and nothing more. The summary says «Деку з N слайдів перенесено як є». Where the note and the `.pptx` disagree, the `.pptx` wins for what the slides say, the note for the deck's metadata (audience, language, subtype).
5. **QA without rewriting.** Step 6 runs on each new render for what a render can break — contrast, fonts, overflow, the file checks, a11y of the render (alt text, `lang`, reading order; Step 4e does not run again on content already shown). A content rule the deck already broke (bullets, title length, slide count, a missing label) is reported in the summary as it is, never fixed: the deck is published as the user made it.
6. **The `.pptx` is not re-rendered** — it exists; the HTML deck and the host's deck are rendered from the IR (Step 5a), then Step 6 and Step 7. Before the Step 7 question the deck's key is looked up (`publications.py find --key <key> --note <the deck's note>`): a place the deck already went to — the key file, or before it exists the note's own `published` — is offered as its next version. **Step 8 saves nothing new**: the record goes to the key with the deck's note as its mirror.
7. **An attachment and a comment of an earlier run.** A rerun attaches the new `.pptx` to the upstream Confluence page under the same file name — Confluence keeps it as the attachment's next version — and does not add a second Jira comment: the one already there links the page.

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
| No place takes a page, and the user did not ask for an HTML deck | no HTML deck is rendered; the `.pptx` and its outline as before v0.10.0 |
| The theme's font file is absent or may not be embedded | the HTML deck uses the system fallback; one line in the outline's footer |
| No browser in the session | the HTML deck's file checks still run; the 2–3 slide look is skipped, said once in the outline's footer |
| The host shows no design system for the product and the user said «ні» to creating one | the host's deck is not built in this run; the other places stay |
| An existing deck without its `.pptx` | the IR is rebuilt from the note's outline; said in the summary |
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
            brand.primary used on 3 slides, Evidence-slide caption
            carries its upstream class)
  Step 7  → attach to PROJ-1234 Confluence page as attachment
            → comment in Jira PROJ-1234 with computer:// link
            → update Obsidian Vault: Presentations/<product>/2026-04-20/
  Step 8  → vault_save(type=presentation, subtype=feature, …)
  → output: "[View deck](computer://…/2026-04-20-qa-product-page-direction.pptx)"
```

## Role defaults — question order (since v3.6.0)

Read from SKILL.md Step 1 when `role_defaults.question_defaults` is `design` or `role_defaults.template_defaults` has a `presentation` entry (`references/role-profiles.md` §2, §2b, §6; a hat overlays both fields for its run).

Invariants for every row: a question is asked exactly when it was asked before (an upstream hand-off that passes the intent still skips it), keeps its options and their count, and the user can pick any option. Only the order, the pre-selected ("Recommended") option and the option wording change — the order and the pre-selection are this step's own (`references/role-profiles.md` §6), the labels below are this skill's design wording on top of the `design` set (`references/vocabulary-sets.md`), an approved glossary entry still wins over both, and the value an option passes on stays the same. Steps 4d (DS check), 4e (a11y audit) and 6 (QA gate) run for every profile exactly as SKILL.md states. An automated run (scheduled, headless, or a return payload to an upstream skill) asks nothing and is unchanged.

| Question | Order and wording when `question_defaults` is `design` | Pre-selected |
|---|---|---|
| Branded or plain (manual "prototype" / "mockup") | branded — DS tokens and components · plain structure | branded |
| Q1 deliverable | prototype · handoff · deck · research-enrichment | none — the request decides |
| Q3 fidelity | mid-fi · hi-fi — DS components in Figma or the declared toolkit · lo-fi — structure only | mid-fi |
| Step 4c issues that need confirmation | state, DS-token and a11y issues first, then the rest in critique order | — |

Q4a, Q4b and Step 2 are unchanged for every profile.

**Q2 deck subtype.** When `role_defaults.template_defaults` has a `presentation` entry, that subtype is listed first and pre-selected; otherwise Q2 is as before. The fallback profile has no `presentation` entry, so a user without a role sees Q2 unchanged. The subtype still has to be a key of `references/deck-subtypes.yaml`; an entry that is not one is ignored.

## History

- `0.3.0` (2026-07-10) — Became the routing host for external design toolkits. Added Step 0.5 (tier-0 provider check → delegate → ingest returns) per `references/design-toolkit-protocol.md`. hi-fi prototype now delegates to a declared toolkit when one covers the request, else falls back to the Figma path (unchanged when `design_toolkits` is empty). QA-ownership rule (no double review), vault `design_delivery` marker, new failure modes. No hardcoded toolkit reference — all org-specifics live in `local-context.md`.
- `0.2.0` (2026-04-20) — Removed hardcoded brand assets and `design-integration/` coupling. All brand specifics (DS spec, pptx theme, base pptx, brand tokens, Figma fileKey) now read from `local-context.md`. English-only copy. Added graceful fallbacks when brand config is partial or missing.
- `0.1.0` (2026-04-20) — Initial release. Supports 4 intents, 4 deck subtypes, 7 design-skill hooks, Figma MCP integration.
