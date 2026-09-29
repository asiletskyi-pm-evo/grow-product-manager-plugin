---
name: requirements-creator
version: 0.16.0
description: Write or review a requirements document with numbered functional requirements, incl. A/B test specs. Not a high-level concept/PRD (write-concept), not Jira tasks (task-creator). UA — «напиши вимоги», «вимоги до A/B-тесту», «перевір мою специфікацію», «опиши фічу як вимоги». EN — "write requirements", "create feature spec", "write A/B test requirements", "review / analyze / improve requirements", "check my spec". Also UA — «створи специфікацію фічі», «переглянь вимоги», «покращ вимоги». A concept from write-concept is the input; task-creator consumes the output.
---

# Feature and Hypothesis Requirements Creator

> **Path rule.** A bare `references/<file>.md` in this file is read from this skill's own `references/` if the file exists there, otherwise from the **shared** `references/` at the plugin root. Resolve the root as `${PLUGIN_ROOT}`, else `${CLAUDE_PLUGIN_ROOT}`, else the directory that contains `skills/`, found by walking up from this folder (`references/host-profiles.md` §6). Never continue without a protocol named here.

Create structured, high-quality feature requirements documents as an experienced Business Analyst. The output is a complete requirements document ready for implementation by product teams (Back-end, Front-end, Android, iOS, Design).

## Integration prerequisite

Before gathering data, read and follow the integration fallback chain in `references/integration-strategy.md`. For this skill, the typical external products needed are:

- **Confluence** — for reading context (concepts, research, existing specs) and publishing requirements
- **Notion** — alternative publishing destination
- **Google Docs** — alternative publishing destination
- **Jira** — for reading Epic info, counting features in the tree, configuring Jira work items macro
- **Figma** — for reading current designs/mockups/prototypes of existing functionality
- **Google Drive** — for reading internal documents
- **Web** — always available via WebSearch

For each product: check for MCP connector → search MCP registry → fall back to browser.

- **Product Analysis skill** — for analyzing product metrics relevant to requirements (invoked when requirements need quantitative data for metrics, hypotheses, or success criteria)

Before gathering any data, also read and comply with `references/data-policy.md`. Confidential data (Tableau metrics, internal analytics, research materials) must NOT be passed to external LLMs or third parties.

## Local context prerequisite

**Before starting, follow `references/local-context-protocol.md` (Step 0).** Read `local-context.md`, select the active product, and load all product-specific context. If the file doesn't exist — redirect to Plugin Configurator for initial setup.

Key context used by this skill:
- `product.name`, `product.platforms`, `product.locales` — pre-fill technical requirements
- `product.jira_project_key` — for Epic numbering and Jira macros
- `product.confluence_space`, `product.confluence_template_url` — for publishing and template
- `product.key_metrics` — for metrics section
- `user.language` — for output language

> **Judgment contract (Step 0j).** Per `references/local-context-protocol.md` Step 0j and `references/pm-mental-model.md`: note this run's
> judgment points (score, rank, verdict, priority, ship/kill, debate question) internally, with no output. A principle acts only through
> a step that implements it — until one exists here, this skill's questions, gates and output stay exactly as they are.

## Mode Selection

At the start of execution, determine which mode to use — ask via AskUserQuestion if not clear from context:

| Mode | When to use | Trigger phrases |
|------|------------|----------------|
| **Create** | Writing new requirements from scratch or based on a concept/research | "write requirements", "create spec", "describe a feature", "A/B test requirements" |
| **Analyze & Improve** | Reviewing and improving existing requirements | "review requirements", "analyze spec", "improve requirements", "check my spec", user provides a link to existing requirements |

If the user provides a Confluence link, file, or pastes existing requirements text — automatically enter **Analyze & Improve** mode.

If the user describes a new feature idea with no existing document — automatically enter **Create** mode.

---

## Step T — Template Resolution (Create mode only)

In Create mode, before writing requirements, resolve which template to use.

Follow `references/template-protocol.md`.

Declare:
- `artifact_type: requirements`
- `subtype`: inferred — `ab-test` when the user mentions an A/B test / experiment, `bugfix` when describing a bugfix spec; none inferred → `role_defaults.template_defaults.requirements` (T-0, since v3.6.0; a hat overlays it; its value `default` keeps the subtype `null`), else `null`
- `product_id: {from local-context.md active product}`
- `language: {from local-context.md → `user.language`; fallback `templates.default_language`}`

Run Steps T-1 → T-5 via the `template-library` helper routines. Render the result and append `<!-- template: {template_id} version: {version} -->` at the end.

If the user says "do not use a template" → skip Step T and use the skill's internal structure.

If no template applies → fall back to the built-in `requirements-builtin-default` (or `requirements-builtin-ab-test` if subtype matched); if both are missing, use the skill's internal structure below.

In **Analyze & Improve** mode, Step T is NOT run — the input document's structure drives the analysis.

**Judgment footer (since v3.5.0).** The artifact closes with the altitude line from `templates/built-in/partial/judgment-footer-v1.md` (`references/template-protocol.md` T-5 step 3a; checked by `references/artifact-style-gate.md` Gate 4a) — Create mode only; Analyze & Improve never adds it to the user's document.

**Role extra sections (since v3.6.0).** T-5 step 3b inserts each `role_defaults.extra_sections.requirements` partial (`tracking-plan`, `nfr`) above the judgment footer when the document — template or internal structure alike — has no section with that heading; derived, never asked, Create mode only (Analyze & Improve never adds them to the user's document).

---

## Mode: Create — Workflow

### Step 1 — Initialization and context gathering

**1a. Product and feature context — clarify via AskUserQuestion if not clear from context:**

- **Which product or part of the product ecosystem** are these requirements for? (if not explicitly stated — ask before proceeding)
- **New or existing functionality?** — Are we creating requirements for completely new functionality, or modifying/developing existing functionality? (if not clear — ask explicitly)

**1b. Determine context source:**

- **Transition from another skill** (Product Research / Write Concept / Brainstorm Features) → context was passed from the previous skill. Ask the user which specific feature/hypothesis from the results they want to describe requirements for. Use all passed context as the starting point
- **Standalone launch** → gather context from scratch: what is the feature, what problem does it solve, for whom, what is the expected outcome

In both cases, proactively gather additional information from the user:
- What is the business goal?
- What user segments are affected?
- Are there constraints (technical, resource, time)?
- What is the expected behavior? Edge cases?
- Analyze provided information, propose alternatives and improvements as an experienced BA would

**1c. Figma designs check — if modifying UI/UX of existing functionality:** if the requirements involve changing UI/UX for any user type, run `references/figma-designs-check.md` with:
- *use as context for:* writing functional requirements and understanding the current state;
- *when designs are confirmed:* reference the current state in functional requirements, describe what changes in the UI, and include Figma links in the UI&UX section.

**1d. Template — already resolved in Step T; do not ask again.**

Step T resolved the template through the registry (`references/template-protocol.md`). Do **not** re-ask "which template?" here: the protocol is explicit that *skills must not reimplement template search logic*, and a second question can contradict T-3's answer with nothing defining which wins.

- **Step T selected a template** → use it. If the user wants structural changes, ask what to add/remove/modify and apply them to that skeleton for this run only.
- **Step T selected nothing** (registry empty / user said "no template") → confirm the built-in structure from `references/requirements-template.md`.
- **A custom Confluence template URL is configured** (`product.confluence_template_url`) → that is a `product`-scope template: offer to register it via `template-library` (`add-template`) so Step T can rank it from now on, and use it as the base for this run.

### Step 2 — Deep requirements gathering (BA mode)

Proactively gather detailed information from the user, asking clarifying questions like an experienced Business Analyst:

**Hypotheses:**
- What is the precondition/problem?
- What do we want to change?
- What do we want to achieve?
- Format as a numbered table: №, Hypothesis

**Goals:**
- What are the goals of this feature?
- If the goal IS the metric itself — note that the "Goals" block can be removed and metrics are sufficient
- Format as a numbered table: №, Goal

**Metrics:**
- Which metrics do we expect to change?
- What is the expected change (in %)?
- Format as a numbered table: №, Metric, Expected change
- **If the user needs help identifying relevant metrics or establishing current baselines** — invoke the **Product Analysis** skill: pass the product context, feature area, and hypothesis. Product Analysis will return current metric values, trends, and suggested target metrics. Use these results to populate the Metrics section with data-backed expected changes

**Business requirements:**
- What should change for different user types?
- How should the product behavior change overall?
- What are the general rules and constraints?

**Functional requirements:**
- What exactly do we want to implement/change in the product?
- How should it work? What are the business logic conditions?
- How should the functionality work in user interfaces?
- Decompose requirements by blocks, screens, and stages of user interaction
- Format as a numbered table: №, Block/Module/Theme, Requirements
- For each requirement — be specific, clear, and unambiguous

Throughout this step: analyze provided information, identify gaps, propose alternatives, challenge assumptions, suggest improvements.

**Source test (Gate 1):** every technical statement recorded here must pass *"Can I point to where this came from — the user, a document, a ticket?"* AI technical assumptions (technology choices, API/schema design, architecture, effort estimates) do NOT go into business or functional requirements — see `references/artifact-style-gate.md`. If the user explicitly asks for technical recommendations, collect them for the separate "Технічні рекомендації (AI)" block (Step 4).

### Step 3 — Technical parameters

**3a. Implementation approach — provide a recommendation based on context analysis:**

Analyze the feature's risk level, impact on metrics, scale of changes, and provide a reasoned recommendation. See `references/approach-recommendation.md` for detailed recommendation logic.

Present options to the user via AskUserQuestion:
- **Feature flag** — recommended for moderate risk, changes to existing functionality
- **Without feature flag** — ⚠️ warn the user: "Implementing without a feature flag carries risks of breaking the system if unexpected issues arise. We recommend using a feature flag or A/B test for safer deployment."
- **A/B Test** — recommended for risky features impacting key metrics
- **A/B/C Test** — recommended when comparing multiple alternative solutions

**3b. Platforms — flexible list:**

Ask the user which platforms need the implementation. On first run with a new product — ask for the full list of product platforms. Examples: App Android, App iOS, Web Portal, Web CMS, Admin panel, etc.

On subsequent runs — propose selecting from the known list for this product.

**3c. Locales/countries — if the product operates in multiple countries:**

Ask the user via AskUserQuestion. Default options:
- On all locales
- Only on specific locales (ask which ones)
- Default suggestions based on product context (from `local-context.md` if configured)
- Allow custom input

**3d. Epic and feature numbering — combined approach:**

- If Epic is known from context (passed from another skill or mentioned by user) → read Epic from Jira using `getJiraIssue`, count existing features in the tree using `searchJiraIssuesUsingJql` (JQL: `parent = EPIC-KEY`), determine next number → propose to user for confirmation (e.g., "Next feature number: PROJ-1234.3. Confirm?")
- If Epic is unknown → ask the user for Epic key and feature number
- Always show the proposed number to the user for confirmation before using it

### Step 3e — Prioritization check (ROI & ICE)

Before finalizing, check whether the feature has been **prioritized** — does it carry computed **ROI** (PRO/ROAIP — `references/roi-frameworks.md`) and **ICE** scores (computed by `brainstorm-features`)?

- If **both are present** (e.g. passed from `brainstorm-features` or in the source concept) → carry them into the requirements' prioritization/metrics section.
- If **missing** → offer to score before finalizing:
  > "This feature doesn't have ROI (PRO/ROAIP) and ICE scores yet. Want me to run `/grow-product-manager:brainstorm-features` to evaluate it before we finalize the requirements? Writing requirements for an unprioritized feature risks speccing something that shouldn't be built yet."

  If the user accepts → chain to `brainstorm-features` (scoring), then continue. If they decline → proceed and note "prioritization not computed" in the document.

### Step 4 — Draft the requirements document

Before writing, load the team style preamble — `references/artifact-style-gate.md` Gate 3a (style profile + reference fragments from `knowledge-library`); skip silently if no profile is configured. Then generate the full requirements document following the confirmed template structure.

> For a worked, high-quality reference of the target shape and rigor, load `references/examples/feature-spec-example-v1.md` on demand. It is a generic exemplar (few-shot) with testable Acceptance Criteria and an explicit A/B decision rule — match its rigor, not its exact wording.

**Standard template structure** (from `references/requirements-template.md`):

| Section | Skill behavior |
|---------|---------------|
| — | Table of Contents | Auto-generated (Confluence ToC macro levels 1-6 / equivalent for other tools) |
| Epic | Link to Epic description in Confluence |
| Hypotheses | Numbered table: №, Hypothesis |
| Goals | Numbered table: №, Goal (can be removed if goal = metrics) |
| Metrics | Numbered table: №, Metric, Expected change |
| 5.1 | Business requirements | Bulleted list of theses — 1–2 sentences each, key points in bold; no paragraph prose |
| 5.2 | Functional requirements | Numbered table: №, Block/Module/Theme, Requirements |
| 5.3 | Technical requirements | Implementation approach, platforms, locales |
| 5.4 | UI&UX requirements | **Empty section** — to be filled by Product Designer. If Figma links to current designs were found — include them as reference |
| 5.5 | Analytics coverage requirements | **Empty section** — to be filled by Product Analyst |
| Acceptance Criteria | Given/When/Then table (AC-N): testable, binary pass/fail conditions covering main flows + edge/error states. The contract QA and analytics verify against |
| Tasks | Link to Epic in Jira + Jira work items macro with JQL filter (parent = EPIC-KEY AND labels = FEATURE-CODE) |

> **Note:** Use the user's preferred language (`user.language`) for all section headings and content in the published document.

**Additional sections for A/B / A/B/C tests:**

If A/B Test or A/B/C Test approach is selected — automatically add these sections after "Hypotheses":

| Section | Content |
|---------|---------|
| Test groups | Description of each group: control (current behavior), test A (new behavior), test B (alternative — for A/B/C) |
| Traffic split | Percentage split between groups (e.g., 50/50, 33/33/34) |
| Success criteria | What metrics and thresholds determine if the test is successful |
| Decision rule | Explicit ship / iterate / kill table tied to the success thresholds, stated **before** launch so the readout is a lookup, not a debate |
| Expected duration | Estimated test duration and minimum sample size considerations |

**Optional block — "Технічні рекомендації (AI)" (only on explicit user request):**

If the user asked for technical recommendations, add them as a separate block at the very end of the document — never inside the functional requirements table — opened with the mandatory AI callout and per-item confidence markers. Format per `references/artifact-style-gate.md` (Gate 1).

**Formatting — mandatory for every document:**

1. **Headings** — H1/H2/H3 hierarchy for all sections and subsections. Headings must NOT be numbered (no "1. Epic", "2. Hypotheses" etc — just "Epic", "Hypotheses").
2. **Dividers** — horizontal rule between all major sections
3. **Bold text** — highlight key theses, important conclusions, critical data points
4. **Tables** — use for all structured data: hypotheses, goals, metrics, functional requirements, risk/mitigation pairs
5. **Clarity** — every requirement must be specific, unambiguous, and actionable
6. **Adaptivity** — requirements must contain all necessary information for BE, FE, Android, iOS, and Design teams
7. **Lists over prose** — any sequence (steps, stages, requirements, criteria, changes, risks) is a numbered/bulleted list or a table, never a paragraph; paragraphs only for context and motivation, ≤ 3–4 sentences (`references/artifact-style-gate.md`, Gate 2)

### Step 4.2 — Requirements visualization (annotated screenshot)

If the requirements change **existing UI**, offer an annotated screenshot per `references/visual-annotation-protocol.md`: obtain the current screen (a `flow-walkthrough` pack's `steps/NN.png` if a run exists for this flow → user upload → Figma frame from Step 1c → live product via browser; no source and the UI is reachable → offer **Flow Walkthrough** in walk mode, 3–5 steps, to capture the as-is screens), place numbered markers where **marker № = functional requirement №**, preview with the user, store in the project repo (`{feature-code}-screen-{N}.png`), and put the image + legend table into the Functional requirements / UI&UX sections. Attach to the published page via the protocol's REST chain in Step 6. Never block on this — skip gracefully if declined or no source exists.

### Step 4.5 — Artifact quality gate

Run `references/artifact-style-gate.md` on the draft. Maker–checker: the `grow-product-manager:artifact-checker` agent (one call per lens; fallback chain per the reference) receives the draft + the source list + the lens — never this conversation's reasoning. A requirements document is a critical artifact (published and then materialized in Jira) → use two checker lenses (form / groundedness). Apply fixes, keep disputed findings visible, and include the one-line gate report when presenting the draft in Step 5.

**Gate emphasis (since v3.6.0).** For each of `spec-readiness` and `nfr-present` in `role_defaults.gate_emphasis`, run that extra check (`references/data-integrity-protocol.md` → Gate emphasis) alongside this gate; a failed one adds a ⚠️ caveat line naming the gap to the draft and to the gate report — never a question, never a blocked draft. Create mode only.

### Step 5 — Review with the user

**Before publishing, always present the full draft to the user for review.**

> "Here is the requirements draft. Please review it and let me know if any changes are needed."

- Walk through each section
- Collect feedback and make edits
- May require multiple iterations
- Only proceed to publishing after the user confirms "OK"

**Self-improvement check** (after corrections are applied and confirmed): follow `references/self-improvement.md` — analyze whether the correction is a pattern, and if so propose a SKILL.md improvement (version bump + CHANGELOG).

### Step 6 — Publishing

Ask whether to save the document — if not, the results stay in the dialogue; if yes, ask where (Confluence by default, Notion, Google Doc, other) and under which space / parent page. Title the page `[Feature number] - [A/B Test type if applicable] - [Feature name]` and publish with the destination's native elements (Confluence: `createConfluencePage` with the ToC and Jira work items macros), following the integration fallback chain; a local document is the last resort.

The full procedure — 6a–6g: the save prompt, location questions, title rules with examples, and the Confluence / Notion / Google Docs / other-destination adaptations — lives in `references/publishing-destinations.md` (skill-local). Read it when the user has confirmed the draft in Step 5 (or at A8 in Analyze & Improve mode).

### Step 7 — Skill chaining

After publishing (or if the user decided not to save), **always** propose transitioning to the next skill:

> "Requirements are ready. Would you like to create Jira tasks for implementing this feature? I'll pass the context (requirements link, Epic, platforms) to the Task Creator skill."

If the user agrees:
- Pass the full context: requirements document link, Epic key, feature number, platforms, approach (feature flag / A/B test), locales
- The Task Creator skill will use these requirements as the source for creating Jira issues

If the user declines — end the workflow gracefully.

**If the approach is `ab-test` — also register the experiment.** An A/B spec that nobody tracks is how a test ends up running for six weeks with no readout. Offer:

> "This is an A/B spec. Register it in the experiment tracker so it doesn't get lost between launch and readout?"

If the user agrees → invoke `experiment-tracker` (register mode) with: hypothesis statement, the Decision Rule (ship/iterate/kill, from the spec), primary metric, requirements-document link, planned start and expected readout date. The tracker takes it to state `specced`.

### Step 8 — Design Bridge handoff (Optional)

> Requires: `design-bridge` skill (Grow PM v1.10.0+). If not installed — skip gracefully.

Offer a design-side deliverable via `AskUserQuestion` — developer handoff spec (recommended if the requirements included UI changes), low-fi UI prototype, deck for dev-review, or skip — and invoke `design-bridge` with `intent: handoff` / `prototype` / `deck` and `source: requirements_page_url`. Never block the workflow.

The full procedure — the offer wording, the exact `design-bridge` parameters per option and the not-installed fallback message — lives in `references/design-bridge-handoff.md` (skill-local). Read it when you reach this step after Step 7.

### Step 9 — Save to Vault (Optional)

> Requires: `references/vault-protocol.md` → Vault Save

IF vault_level > L0 AND vault sync_mode != "off":

1. `vault_save({ type: "requirements", product: active_product, skill: "requirements-creator", skill_version: "0.16.0", tags: [feature area, platforms, subtype (default/ab-test)], content: final requirements document, related: [[source concept]], extra_frontmatter: { confluence_url (if published), subtype } })`
2. IF the source concept came from Vault — update it: add this artifact as `children` link.
3. Display: "Saved to Vault: Requirements/{product}/…"

(Analyze & Improve mode: after A8 publishing, save the improved document the same way — `extra_frontmatter.superseded` links the previous version if it lives in the vault.)

---

## Mode: Analyze & Improve — Workflow

Review and improve **already written requirements** as an experienced BA: read the document and its context (A1), run structural + content analysis against the template and gate checklists (A2–A3), ask prioritized clarifying questions (A4), propose and apply improvements (A5–A6, gate-checked), optionally validate feasibility via Product Research (A7), publish and chain to Task Creator (A8–A9).

The full A1–A9 workflow lives in the skill-local `references/analyze-improve-mode.md` — read it ONLY when this mode is active.

---

## Quality standards

- Write requirements as an experienced Business Analyst — specific, clear, unambiguous
- Every functional requirement must be actionable by a developer
- Distinguish facts from assumptions — mark assumptions explicitly
- If information is insufficient for a section — state gaps and ask the user to fill them
- Requirements must be adaptive: contain information for BE, FE, Android, iOS, and Design
- Use Ukrainian or English based on user's language preference
- Maintain consistent formatting: headings, bold highlights, tables, dividers
- Proactively suggest improvements, alternatives, and identify edge cases

## Additional Resources

- **`references/local-context-protocol.md`** — Step 0: how to read and use local-context.md (mandatory before any skill execution)
- **`references/requirements-template.md`** — detailed standard template with section descriptions and instructions
- **`references/analyze-improve-mode.md`** — skill-local: the full Analyze & Improve workflow (A1–A9); load only in that mode
- **`references/publishing-destinations.md`** — skill-local: Step 6 publishing (6a–6g) — save prompt, location, title template, Confluence / Notion / Google Docs / other adaptations; load at Step 6 (and A8)
- **`references/design-bridge-handoff.md`** — skill-local: Step 8 Design Bridge handoff — offer wording and `design-bridge` parameters per option; load at Step 8
- **`references/artifact-style-gate.md`** — artifact quality gate: Gate 1 (ungrounded technical content), Gate 2 (lists over prose), maker–checker execution model (Step 4.5 / A6)
- **`references/examples/feature-spec-example-v1.md`** — worked golden feature-spec exemplar with A/B + acceptance criteria (few-shot; load on demand in Step 4)
- **`references/approach-recommendation.md`** — implementation approach recommendation logic (feature flag, A/B test, etc.)
- **`references/roi-frameworks.md`** — the ROI (PRO/ROAIP) side of the prioritization gate (Step 3e / A5); ICE scoring is computed by `brainstorm-features`
- **`references/integration-strategy.md`** — MCP → Registry → Browser fallback chain (shared across all skills)
- **`references/data-policy.md`** — data confidentiality policy: what data can and cannot be shared externally (mandatory reading before any data gathering)
- **`references/self-improvement.md`** — self-improvement protocol: how to learn from user corrections and improve skill algorithms

