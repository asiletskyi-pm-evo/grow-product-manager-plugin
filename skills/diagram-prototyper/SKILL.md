---
name: diagram-prototyper
version: 0.15.1
description: Quick diagrams, flowcharts, BPMN, wireframes, infographics, and screenshot annotation with numbered markers. Not brand decks or hi-fi on a Design System (design-bridge). UA — «намалюй діаграму/блок-схему», «вайрфрейм», «анотуй скріншот», «зроби прототип». EN — "annotate this screenshot".
---

# Diagram & Prototype Creator

> **Path rule.** A bare `references/<file>.md` in this file is read from this skill's own `references/` if the file exists there, otherwise from the **shared** `references/` at the plugin root. Resolve the root as `${PLUGIN_ROOT}`, else `${CLAUDE_PLUGIN_ROOT}`, else the directory that contains `skills/`, found by walking up from this folder (`references/host-profiles.md` §6). Never continue without a protocol named here.

Create diagrams, flowcharts, BPMN processes, mind maps, infographics, and UI prototypes to improve understanding of product concepts and hypotheses. The skill acts as a visual communication assistant — it gathers context, selects the right tool, generates the visual artifact, validates quality, and publishes the result.

## Integration prerequisite

Before starting, read and follow the integration fallback chain in `references/integration-strategy.md`. For this skill, the typical external products needed are:

- **Figma** — for creating and publishing design prototypes and diagrams
- **Confluence** — for publishing diagrams as images on documentation pages
- **Notion** — alternative publishing destination
- **Claude in Chrome** — for interacting with external LLMs (Gemini, ChatGPT, NotebookLM) and Draw.io via browser
- **Web** — always available via WebSearch

Before gathering any data, also read and comply with `references/data-policy.md`. Confidential data must NOT be passed to external LLMs in a way that violates the policy. When constructing prompts for external LLMs, **exclude** any confidential metrics, internal URLs, or sensitive business data — describe the concept in general terms.

## Local context prerequisite

**Before starting, follow `references/local-context-protocol.md` (Step 0).** Read `local-context.md`, select the active product, and load all product-specific context. If the file doesn't exist — redirect to Plugin Configurator for initial setup.

Key context used by this skill:
- `product.name`, `product.platforms` — understand the product scope for prototypes
- `product.confluence_space` — for publishing diagrams to Confluence
- `user.language` — for text localization on diagrams and prototypes

---

> **Judgment contract (Step 0j).** Per `references/local-context-protocol.md` Step 0j and `references/pm-mental-model.md`: note this run's
> judgment points (score, rank, verdict, priority, ship/kill, debate question) internally, with no output. A principle acts only through
> a step that implements it — until one exists here, this skill's questions, gates and output stay exactly as they are.

## Step T — Template Resolution (presentations only)

This skill is primarily **visual-artifact-oriented** — diagrams, flowcharts, prototypes, and mind maps don't use markdown document templates. **Skip Step T** for those types.

However, when the visualization type (resolved in Step 1b) is **Presentation**, the slide outline itself IS a document artifact and benefits from a template. In that case, follow `references/template-protocol.md`:

- `artifact_type: presentation`
- `subtype`: inferred from the source context
  - Concept pitch → `feature` (fallback `presentation-builtin-feature`)
  - Research highlights → `research-highlights`
  - A/B test results → `ab-test-readout`
  - Post-release readout → `release-readout`
- `product_id`: from local-context.md active product
- `language`: from `user.language` in local-context.md

Run **Steps T-0 → T-5 exactly as `references/template-protocol.md` names them** (do not renumber locally — "Step T-4" must mean the same thing in every skill):

- **T-0 (Declare context):** the fields above.
- **T-1 (Load registry) + T-2 (Score and rank):** via the template-library helper `resolve({artifact_type, subtype, product_id, language})`.
- **T-3 (Decide):** auto / ask / smart per `templates.preference`.
- **T-4 (Collect variables):** from the passed context; ask only for required variables still missing.
- **T-5 (Render and record):** use the selected template's slide outline as the structure for Step 3 (generation); if the ladder finds nothing, fall back to `presentation-builtin-feature`. When publishing the deck/outline, append the protocol's marker `<!-- template: {template_id} version: {version} -->` to the outline markdown (not to the rendered .pptx).

**Escape hatch:** if the user says "don't use a template" or "free-form deck", skip Step T and use a blank outline.

**Chained invocation:** if invoked from `write-concept`, the concept template is already resolved; request a presentation-specific template separately here (Step T is about the deck artifact, not the source concept).

**Judgment footer (since v3.5.0).** The artifact closes with the altitude line from `templates/built-in/partial/judgment-footer-v1.md` (`references/template-protocol.md` T-5 step 3a; checked by `references/artifact-style-gate.md` Gate 4a) — only on a deck: on the closing slide (or the last slide's speaker notes), and for an external audience (customer, external users, social media) only in the outline markdown, never in the deck; diagrams, prototypes and mockups, wireframes, mind maps, infographics and annotated screenshots carry none.

---

## Workflow

### Step 1 — Context gathering

**1a. Determine the context source:**

- **Transition from another skill** (write-concept, brainstorm-features, requirements-creator, product-research, product-analysis) → context was passed from the previous skill. Summarize the passed context and confirm with the user what exactly needs to be visualized. Since v3.9.0, a call from design-bridge with `return_to: design-bridge` (passed only for its build-first hand-off) is the exception: the values it passes (type, fidelity, tool, locale, platform, the Prototype IR as the element to draw) answer Steps 1–4 without asking, and Steps 8–10 do not run (Skill Chaining — Inbound)
- **Standalone launch** → gather context from scratch

**1b. Clarify the visualization goal — ask via AskUserQuestion:**

> "What would you like to visualize?"

| Type | When to use | Examples |
|------|------------|---------|
| **Diagram** | Processes, logic, flows, architecture | User flow, order lifecycle, system interaction, decision tree |
| **Prototype** | UI screens, interface layouts, components | Product page layout, new feature mockup, checkout flow screens |
| **Mind Map** | Concept exploration, idea mapping, brainstorming results | Feature decomposition, stakeholder map, competitive landscape |
| **Infographic** | Data visualization, metric storytelling, comparisons, step-by-step guides | Funnel metrics overview, feature comparison, onboarding steps, A/B test results summary, market research highlights |
| **Presentation** | Visual summary of a concept or research | Concept pitch slides, research highlights |

**1c. Gather detailed requirements:**

Based on the visualization type, ask targeted questions:

**For diagrams:**
- What process or flow needs to be visualized?
- Who are the actors (users, systems, services)?
- What are the start and end conditions?
- Are there decision points or branches?
- What level of detail is needed?

**For prototypes:**
- Which screen(s) or feature area?
- Which platform? (Web, iOS, Android — from `product.platforms`)
- What elements should be present? (buttons, forms, lists, navigation, etc.)
- Are there existing designs in Figma to reference?

**Design vocabulary (since v3.6.0).** When `role_defaults.question_defaults` is `design`, the same questions are worded and ordered for design work: the elements question above lists states (empty / error / loading), DS components and a11y notes first; Step 3 pre-selects Mid-fi when the context names no phase; Step 4 marks Figma as Recommended where its table offers Figma (mid-fi mockup). No question is added or dropped, Step 6g is unchanged, and every other profile — and an automated run — sees these steps as before.

**For mind maps:**
- What is the central topic?
- What are the main branches?
- What level of depth is needed?

**For infographics:**
- What is the main story or message the infographic should convey?
- What data or metrics should be included? (numbers, percentages, comparisons)
- Who is the target audience? (internal team, stakeholders, external users, social media)
- What is the intended use? (presentation insert, standalone document, Confluence page, social sharing)
- Are there specific data points, KPIs, or comparisons to highlight?
- What approximate dimensions? (vertical scroll, A4 page, slide-sized, social media format)

**For presentations:**
- What concept or research to visualize?
- How many slides approximately?
- What is the target audience?

**1d. Ask about text localization:**

> "What language should be used for text labels on the diagram/prototype?"

- Use `user.language` from `local-context.md` as default suggestion
- Allow any language the user specifies
- Store the chosen locale for prompt construction

### Step 2 — Diagram type selection (for diagrams only)

If the user chose "Diagram" in Step 1, ask for the notation type via AskUserQuestion:

> "Which diagram notation would you like to use?"

| Notation | When to recommend | Description |
|----------|------------------|-------------|
| **Flowchart** | General processes, user flows, decision trees | Standard boxes, diamonds, arrows. Simplest and most universal |
| **BPMN 2.0** | Business processes with lanes, events, gateways | Professional process notation with pools, lanes, events, gateways. Best for cross-team processes |
| **Simple schema** | Architecture, data flow, system interaction | Free-form boxes and arrows, no strict notation rules. Best for technical overviews |

Provide a recommendation based on context:
- User flow or decision logic → recommend Flowchart
- A `flow-walkthrough` evidence pack (`steps.yaml`) is a valid input → Flowchart: one node per step intent, edges in step order, each friction as a red note on its node, blocked steps as a terminal node with the reason; since v3.8.0 the legend marks the walked steps `observed` (walkthrough, date)
- Cross-team or cross-system process → recommend BPMN 2.0
- Architecture or data overview → recommend Simple schema

### Step 3 — Fidelity selection (for prototypes only)

If the user chose "Prototype" in Step 1, ask for the fidelity level via AskUserQuestion:

> "What level of detail should the prototype have?"

| Fidelity | When to recommend | Description |
|----------|------------------|-------------|
| **Lo-fi wireframe** | Early concept validation, quick iteration | Simple block layouts, placeholder text, no styling. Focus on structure and flow |
| **Mid-fi mockup** | Stakeholder presentations, concept approval | Schematic screens with real text, buttons, and basic UI patterns. Not pixel-perfect, but recognizable |

Provide a recommendation based on context:
- Concept phase, brainstorming → recommend Lo-fi
- Requirements phase, stakeholder review → recommend Mid-fi

> **Boundary — hi-fi is out of scope here.** This skill covers lo-fi and mid-fi only. For hi-fi, design-system-native screen generation, route to `design-bridge`, which delegates to an external design toolkit when one is declared in `local-context.md` (`design_toolkits[]`, see `references/design-toolkit-protocol.md`) or falls back to the Figma path.

### Step 3b — Infographic style selection (for infographics only)

If the user chose "Infographic" in Step 1, ask for the visual style via AskUserQuestion — Data-driven, Process / timeline, Comparison, Informational / educational or Statistical / report — and mark the one that fits the context as recommended.

The full procedure — the style table and the recommendation rules — lives in `references/tool-procedures.md` (skill-local). Read it when the visualization type is Infographic.

### Step 4 — Tool selection

Ask the user which tool to use via AskUserQuestion:

> "Which tool should I use to create this?"

Present options based on the visualization type. Not all tools are suitable for all types:

| Tool | Best for | How it works |
|------|----------|-------------|
| **Mermaid (built-in)** | Flowcharts, BPMN, simple diagrams | Generated locally by the skill as Mermaid code → rendered as SVG/image. No external LLM needed. Fastest option |
| **HTML/CSS (built-in)** | Infographics, data visualizations | Generated locally as a single HTML file with inline CSS and SVG. No external LLM needed. Full control over layout and styling |
| **Google Gemini** | Prototypes, complex diagrams, mind maps, infographics | Browser → gemini.google.com (Nano Banana mode for image generation). Uses the strongest available model |
| **ChatGPT** | Prototypes, diagrams, mind maps, infographics | Browser → chatgpt.com. Uses the strongest available model (GPT-4o or newer) |
| **NotebookLM** | Mind maps, presentations | Browser → notebooklm.google.com. Uses Presentations and Mind Map features |
| **Figma** | Prototypes, design mockups | Via Figma MCP or browser → figma.com. Best for high-fidelity prototypes |
| **Draw.io** | Flowcharts, BPMN, architecture diagrams | Priority: generate .drawio XML file locally. Fallback: browser → app.diagrams.net |

**Tool recommendation logic:**

| Visualization type | Recommended tool | Reason |
|-------------------|-----------------|--------|
| Flowchart / BPMN / simple diagram (standard) | Mermaid (built-in) | Fastest, no external dependencies |
| Complex or large diagram | Draw.io | Better control over layout and export |
| Lo-fi wireframe | Gemini or ChatGPT | Image generation with structure |
| Mid-fi mockup | Figma or Gemini | Higher fidelity capability |
| Mind map | NotebookLM or Gemini | Built-in mind map features |
| Infographic (data-driven, statistical) | HTML/CSS (built-in) | Full control over charts, numbers, layout. Renders as a standalone file |
| Infographic (process, comparison, informational) | HTML/CSS (built-in) or Gemini | HTML for structured layouts; Gemini for more illustrative style |
| Infographic (highly visual / illustrative) | Gemini or ChatGPT | Image generation for icon-heavy or artistic infographics |
| Presentation | NotebookLM | Built-in presentation generation |

Mark the recommended option with "(Recommended)" in the AskUserQuestion options.

### Step 5 — Prompt construction

Based on all gathered context, construct a detailed prompt for the selected tool: the core elements every prompt carries (5a), the type-specific additions (5b), the quality instructions (5c), and data confidentiality (5d) — no internal URLs, metric values, employee names, Jira keys or Confluence IDs reach an external LLM; confidential infographic data steers the user to HTML/CSS (built-in) or to placeholder values.

The full procedure — the element checklists, per-type additions, quality phrases and confidentiality rules — lives in `references/prompt-construction.md` (skill-local). Read it every time Step 5 runs, for any tool.

### Step 6 — Generation

Execute the generation based on the selected tool:

**6a. Mermaid (built-in):**

1. Generate Mermaid code based on the constructed prompt
2. Validate the Mermaid syntax (test by rendering)
3. Render as `.mermaid` file and/or `.svg` image
4. Present the result to the user in the chat
5. Skip to Step 7 (no LLM quality loop needed)

For BPMN 2.0 in Mermaid — use `flowchart` with subgraphs for lanes and styled nodes for events/gateways.

**6a2. HTML/CSS (built-in) — for infographics:** one self-contained HTML file (inline CSS, inline SVG charts, a CSS-variable palette, print styles, a footer that gives each number's source and evidence class as 6g's *Data integrity* row requires), validated and saved as `.html`; skip to Step 7.

**6b–6f. External tools:** Google Gemini (6b), ChatGPT (6c), NotebookLM (6d), Figma via MCP or browser (6e), Draw.io — local `.drawio` XML first, browser as fallback (6f). Every browser-driven result proceeds to Step 6g (Quality check).

The full procedure — HTML structure, color and typography rules for 6a2 and the step-by-step browser/MCP runs for 6b–6f — lives in `references/tool-procedures.md` (skill-local). Read it when the selected tool is anything other than Mermaid.

**6g. Quality check (for LLM-generated results):**

After receiving the result from any external tool (Gemini, ChatGPT, NotebookLM, Figma, Draw.io browser):

1. **Review the generated image** — take a screenshot and analyze it
2. **Check against requirements:**

| Check | What to verify |
|-------|---------------|
| **Content accuracy** | All required elements present? Process steps match? UI elements correct? Data points accurate? |
| **Text correctness** | All labels in the correct locale? No truncated or garbled text? |
| **Visual quality** | Clean layout? No overlapping elements? Readable text? Consistent styling? |
| **Notation compliance** | (For BPMN/flowcharts) Correct symbols used? Proper flow direction? |
| **Data integrity** | (For infographics) Numbers match source data? Charts proportional? Units labeled? Since v3.8.0 (`references/artifact-style-gate.md` Gate 4b): each number keeps its source's evidence class in the footer attribution — never upgraded, `simulated` / `assumed` visible; internal source names only for an internal audience, the class for every audience; when an external tool cannot render the class, it goes in the Step 7 caption and does not count as a failed iteration |
| **Completeness** | No missing branches, screens, nodes, or data sections? Start/end conditions present? |

3. **If issues found — auto-correct:**
   - Construct a follow-up prompt describing exactly what needs to be fixed
   - Send the correction to the LLM / tool
   - Re-check the result

4. **Iteration limit:**
   - Maximum **3 auto-correction iterations**
   - After iteration 3, if the result still doesn't pass quality check:

   > "I've tried to improve the result 3 times, but there are still issues: [list issues]. Would you like to: (a) Accept the current result as-is, (b) Continue iterating, (c) Switch to a different tool?"

   Ask via AskUserQuestion and proceed based on the user's choice.

### Step 7 — Present result to user

**7a. Show the result in the chat:**

- Display the generated image/diagram/prototype/infographic
- Provide a brief description of what was created
- Highlight key elements

**7b. Ask for feedback:**

> "Here is the result. Does it match your expectations? Would you like any changes?"

- If the user requests changes — apply corrections (re-enter Step 6 with updated prompt)
- If the user confirms "OK" — proceed to Step 8

### Step 8 — Publishing

**8a. Ask if the user wants to save/publish** (with `return_to: design-bridge`, Steps 8–10 are skipped — the result goes back to design-bridge):

> "Would you like to publish or save this? You can publish to Confluence, Notion, or Figma, or save as a local file."

Present options via AskUserQuestion:

| Destination | What happens |
|-------------|-------------|
| **Confluence** | Upload image to a Confluence page (existing or new). Add caption and context |
| **Notion** | Upload image to a Notion page (existing or new) |
| **Figma** | Upload to Figma workspace (if not already created there) |
| **Local file** | Save as PNG/SVG/drawio/mermaid/html in the user's workspace folder |
| **No** | End the skill, result stays in the chat |

**8b–8f. Destinations and export:** Confluence (8b — existing or new page, image attachment with caption), Notion (8c), Figma (8d), local file (8e — PNG / SVG / .drawio / .mermaid / .html), plus an extra PNG / PDF / HTML export for infographics (8f). The full procedure for each destination lives in `references/tool-procedures.md` (skill-local). Read it when the user picks any destination other than "No".

### Step 9 — Skill chaining

After publishing (or if the user decided not to save), offer the next step based on context:

**If the visualization was for a concept:**
> "Would you like to continue writing requirements for this concept? I'll pass the context to the Requirements Creator skill."

**If the visualization was for requirements:**
> "Would you like to create Jira tasks for this feature? I'll pass the context to the Task Creator skill."

**If the infographic was for product analysis or research:**
> "Would you like a deck that includes this infographic? I'll pass the context to **design-bridge**, which builds brand-themed decks."

**If standalone:**
> "Would you like to create another diagram, prototype, or infographic? Or continue with a different task?"

---

### Step 10 — Save to Vault (Optional)

> Requires: `references/vault-protocol.md` → Vault Save

IF vault_level > L0 AND vault sync_mode != "off":

1. `vault_save({ type: "diagram", product: active_product, skill: "diagram-prototyper", skill_version: "0.15.1", tags: [diagram/prototype/infographic, topic keywords], content: source (Mermaid/HTML/XML) or brief + link to exported file and publish location, related: [source concept/requirements/hypothesis if chained] })`
2. Display: "Saved to Vault: Diagrams/{product}/…"

## Mode: Annotate (standalone screenshot annotation)

Triggers: "анотуй скріншот", "додай стрілки на скрін", "познач на скріншоті", "annotate this screenshot" — WITHOUT a full requirements/concept cycle.

Follow `references/visual-annotation-protocol.md`: obtain the image (V-1: user upload → Figma → browser), agree the marker list with the user (V-2 — here markers number the user's points, not requirement rows, unless they say otherwise), render locally with Pillow (V-3), run the mandatory preview cycle (V-4), store per V-5 and deliver the PNG + legend table. Offer the REST/browser attachment chain (V-6) only if the user names a Confluence page or Jira issue. This mode never invokes templates (Step T does not apply).

## Skill Chaining — Inbound (for other skills)

**This section defines how other skills should invoke this skill.** It lists the skills that actually chain here today — if you add a caller, add its row.

Since `design-bridge` (v1.10.0) became the routing host for brand-themed decks, prototypes and handoffs, the artifact skills (`write-concept`, `requirements-creator`, `brainstorm-features`, `product-research`, `product-analysis`) hand **design** work to design-bridge instead. This skill keeps the lo-fi, DS-free visualization work: process diagrams, flowcharts, BPMN, mind maps, infographics.

| Source skill | When to offer | Suggested visualization |
|-------------|--------------|----------------------|
| **meeting-processor** | Complex process discussed (M9) | Flowchart/BPMN of the discussed process |
| **cjm-research** | After the report is ready | Funnel diagram, journey map, deck of the findings |
| **quarterly-planning** | After the roadmap is approved | Roadmap/timeline visualization |
| **project-planning** | After the arc is built | Dependency graph, critical-path diagram |
| **design-bridge** | Lo-fi/DS-free visual needed inside a design flow | Mermaid flow, plain wireframe. With `return_to: design-bridge` (since v3.9.0, only for design-bridge's build-first hand-off): nothing passed is asked (the platform included, so Step 1c does not ask it), Steps 8–10 do not run (design-bridge publishes and saves), and the result returns with the Prototype IR it passed filled in — screens, shown and missing states, transitions, node ids; without the parameter, unchanged |

**Transition prompt template:**
> "Would you like to create a visual diagram, prototype, or infographic for [brief description]? This can help communicate the concept more effectively."

When invoking this skill from another skill, pass:
- Full context from the parent skill (concept, requirements, research results, hypotheses)
- Suggested visualization type (diagram / prototype / mind map / infographic)
- The specific element to visualize

---

## Quality standards

- Every generated visual must be reviewed for accuracy, completeness, and readability
- Text on diagrams/prototypes/infographics must match the user's chosen locale
- Prompts for external LLMs must comply with `references/data-policy.md` — no confidential data in prompts
- Mermaid code must be syntactically valid before presenting to the user
- Draw.io XML must be structurally valid and openable in Draw.io
- HTML infographics must be valid, self-contained, and render correctly in modern browsers
- BPMN 2.0 diagrams must use correct notation (events, gateways, lanes)
- Prototype fidelity must match the selected level (lo-fi or mid-fi)
- Infographic data visualizations must be accurately proportioned and labeled
- Placeholder values (5d) are marked `illustrative placeholder — not data` and carry no evidence class; a prototype, mockup or wireframe is never cited as evidence of user behaviour — where a claim about users rests on it alone, the claim is `assumed` (`references/pm-mental-model.md` §3, Prototype-as-validation; `references/data-integrity-protocol.md` 6a)
- Maximum 3 auto-correction iterations before asking the user
- Always present the result to the user before publishing

## Additional Resources

- **`references/visual-annotation-protocol.md`** — screenshot annotation: sources, Pillow rendering, marker=requirement binding, preview cycle, attachment chain
- **`references/prompt-construction.md`** (skill-local) — Step 5: core, per-type and quality prompt elements; data confidentiality in prompts
- **`references/tool-procedures.md`** (skill-local) — Step 3b infographic styles, Steps 6a2–6f per-tool generation, Steps 8b–8f publishing and export

- **`references/local-context-protocol.md`** — Step 0: how to read and use local-context.md (mandatory before any skill execution)
- **`references/integration-strategy.md`** — MCP → Registry → Browser fallback chain (shared across all skills)
- **`references/data-policy.md`** — data confidentiality policy: what data can and cannot be shared externally (mandatory reading before any data gathering)
- **`references/self-improvement.md`** — self-improvement protocol: how to learn from user corrections and improve skill algorithms

## Routing

The `description` above is short on purpose: a host with many skills shows only part of the skill listing, or skill names alone (`references/host-profiles.md` §7). The full set of phrases and boundaries that route here, as the description carried them up to v3.10.0:

> Quick diagrams, flowcharts, BPMN, wireframes, infographics, and screenshot annotation with numbered markers. Not brand decks or hi-fi on a Design System (design-bridge). UA — «намалюй діаграму/блок-схему», «вайрфрейм», «анотуй скріншот», «додай стрілки на скрін». EN — "create a diagram", "draw a flowchart", "visualize this process", "make a prototype" (no DS mentioned), "mockup", "annotate this screenshot". Also UA — «візуалізуй процес», «зроби прототип», «інфографіка», «познач на скріншоті». Generation via Mermaid/HTML, Gemini, ChatGPT, NotebookLM, Figma, Draw.io; annotation runs locally.
