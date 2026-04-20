---
name: requirements-creator
version: 0.7.0
description: Create structured feature requirements documents or analyze and improve existing ones, acting as an experienced Business Analyst. Use when the user asks to "write requirements", "describe a feature", "create feature spec", "write A/B test requirements", "review requirements", "analyze requirements", "improve requirements", "check my spec", or needs help turning a feature idea into a structured requirements document or improving an existing one.
---

# Feature and Hypothesis Requirements Creator

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
- `subtype: {inferred — "ab-test" when user mentions A/B test / experiment, "bugfix" when describing a bugfix spec, null otherwise}`
- `product_id: {from local-context.md active product}`
- `language: {from local-context.md → user.language or product.default_language}`

Run Steps T-1 → T-5 via the `template-library` helper routines. Render the result and append `<!-- template: {template_id} version: {version} -->` at the end.

If the user says "do not use a template" → skip Step T and use the skill's internal structure.

If no template applies → fall back to the built-in `requirements-builtin-default` (or `requirements-builtin-ab-test` if subtype matched); if both are missing, use the skill's internal structure below.

In **Analyze & Improve** mode, Step T is NOT run — the input document's structure drives the analysis.

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

**1c. Figma designs check — if modifying UI/UX of existing functionality:**

If the requirements involve changing UI/UX for any user type, ask via AskUserQuestion:

> "Are there current designs / mockups / prototypes of this functionality in Figma?"

- **If the user provides a link** — open via Figma MCP (`get_design_context`, `get_screenshot`) or browser fallback. Read and extract: current UX flows, screens, key UI patterns. Use as context for writing functional requirements and understanding current state
- **If the user believes designs should exist but cannot provide a link** — offer to search:
  > "I can search for relevant mockups in Figma from your account. Would you like me to search?"
  - If agreed — search via Figma MCP or browser (`https://www.figma.com`):
    - Try to understand the structure of the design system: look for sections like "Актуальний дизайн", "Current design", "Production", "Live", "Ready for dev", "Поточний стан"
    - Show the user the found files/frames and ask them to confirm which are relevant and up-to-date
  - If Figma MCP is unavailable — follow `references/integration-strategy.md` fallback chain
- **If no designs exist** — note this and proceed without design context
- **If relevant designs are confirmed** — use throughout the requirements: reference current state in functional requirements, describe what changes in the UI, include Figma links in the UI&UX section

**1d. Requirements template — ask via AskUserQuestion:**

> "Which template should we use for the requirements?"

- **Standard template** (default) — use the template defined in `references/requirements-template.md`. If a custom Confluence template URL is configured in `local-context.md` — reference it as the base
- **Standard with modifications** — ask the user what exactly needs to change (add/remove/modify sections)
- **Custom template** — ask the user to provide their template (as text, file, or link)

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

- If Epic is known from context (passed from another skill or mentioned by user) → read Epic from Jira using `getJiraIssue`, count existing features in the tree using `searchJiraIssuesUsingJql` (JQL: `parent = EPIC-KEY`), determine next number → propose to user for confirmation (e.g., "Наступний номер фічі: PROJ-1234.3. Підтверджуєте?")
- If Epic is unknown → ask the user for Epic key and feature number
- Always show the proposed number to the user for confirmation before using it

### Step 4 — Draft the requirements document

Generate the full requirements document following the confirmed template structure.

**Standard template structure** (from `references/requirements-template.md`):

| Section | Skill behavior |
|---------|---------------|
| — | Table of Contents | Auto-generated (Confluence ToC macro levels 1-6 / equivalent for other tools) |
| Epic | Link to Epic description in Confluence |
| Hypotheses | Numbered table: №, Hypothesis |
| Goals | Numbered table: №, Goal (can be removed if goal = metrics) |
| Metrics | Numbered table: №, Metric, Expected change |
| 5.1 | Business requirements | Text with bold highlights for key theses |
| 5.2 | Functional requirements | Numbered table: №, Block/Module/Theme, Requirements |
| 5.3 | Technical requirements | Implementation approach, platforms, locales |
| 5.4 | UI&UX requirements | **Empty section** — to be filled by Product Designer. If Figma links to current designs were found — include them as reference |
| 5.5 | Analytics coverage requirements | **Empty section** — to be filled by Product Analyst |
| Tasks | Link to Epic in Jira + Jira work items macro with JQL filter (parent = EPIC-KEY AND labels = FEATURE-CODE) |

> **Note:** Use the user's preferred language (`user.language`) for all section headings and content in the published document.

**Additional sections for A/B / A/B/C tests:**

If A/B Test or A/B/C Test approach is selected — automatically add these sections after "Hypotheses":

| Section | Content |
|---------|---------|
| Test groups | Description of each group: control (current behavior), test A (new behavior), test B (alternative — for A/B/C) |
| Traffic split | Percentage split between groups (e.g., 50/50, 33/33/34) |
| Success criteria | What metrics and thresholds determine if the test is successful |
| Expected duration | Estimated test duration and minimum sample size considerations |

**Formatting — mandatory for every document:**

1. **Headings** — H1/H2/H3 hierarchy for all sections and subsections. Headings must NOT be numbered (no "1. Epic", "2. Hypotheses" etc — just "Epic", "Hypotheses").
2. **Dividers** — horizontal rule between all major sections
3. **Bold text** — highlight key theses, important conclusions, critical data points
4. **Tables** — use for all structured data: hypotheses, goals, metrics, functional requirements, risk/mitigation pairs
5. **Clarity** — every requirement must be specific, unambiguous, and actionable
6. **Adaptivity** — requirements must contain all necessary information for BE, FE, Android, iOS, and Design teams

### Step 5 — Review with the user

**Before publishing, always present the full draft to the user for review.**

> "Here is the requirements draft. Please review it and let me know if any changes are needed."

- Walk through each section
- Collect feedback and make edits
- May require multiple iterations
- Only proceed to publishing after the user confirms "ОК"

**Self-improvement check** (after corrections are applied and confirmed):

If the user requested corrections during review, analyze whether the skill's algorithm can be improved to prevent similar issues in the future. Follow the full protocol in `references/self-improvement.md`. In short:
1. Analyze the root cause of the error — is this a pattern or a one-off?
2. If it's a pattern — propose a specific improvement to the skill's conditions
3. If the user agrees — update the SKILL.md, re-package the plugin, and provide the updated file

### Step 6 — Publishing

**6a. Ask if the user wants to save the document:**

> "Would you like to save the requirements document? If yes — which tool should I use?"

- If no — end the skill, results stay in the dialogue
- If yes — ask where:
  - **Confluence** (default)
  - **Notion**
  - **Google Doc**
  - **Other** — user specifies

**6b. Ask for location:**

- Which **space** (Confluence) / **workspace** (Notion) / **folder** (Google Drive)?
- Which **parent page/document** to nest under?
- Should the article be a **child page** of the specified location?
- Offer to search existing pages to help decide

**6c. Document title — template:**

`[Feature number] - [A/B Test type if applicable] - [Feature name]`

Rules:
- Feature number = Epic key + `.` + sequential number (e.g., PROJ-1234.3)
- If no feature number — skip this part
- Add "A/B Test" or "A/B/C Test" only if this approach was selected
- Feature name = concise description of the feature

Examples:
- `PROJ-1234.3 - A/B Test - Add wishlist button to product comparison`
- `PROJ-5678.1 - Move Buy button higher on product page`
- `PROJ-5678.1 - A/B/C Test - Promo block layout on product page`

**6d. Publishing to Confluence:**

Use Confluence-native elements:
- **Table of Contents macro** (heading levels 1-6)
- **Jira work items macro** with JQL filter: `parent = EPIC-KEY AND labels = FEATURE-CODE`, sorted by Sprint
- **Horizontal rule/divider** between sections
- **Panels** where appropriate
- **Bold**, headings H1/H2/H3, tables

Publish via Confluence MCP (`createConfluencePage`). If unavailable — follow integration fallback chain.

**6e. Publishing to Notion:**

Adapt structure to Notion elements:
- Table of Contents block
- Dividers between sections
- Toggle headings for collapsible sections where appropriate
- Tables, bold text, headings hierarchy

Publish via Notion MCP. If unavailable — follow integration fallback chain.

**6f. Publishing to Google Docs:**

Adapt structure to Google Docs:
- Table of Contents
- Horizontal lines between sections
- Tables, bold text, headings hierarchy

Follow integration fallback chain: Google Docs MCP → registry → browser.

**6g. Publishing to other destinations:**

Follow integration fallback chain for the specified tool. Adapt format to platform capabilities.

As a last resort for any destination — generate a local document and provide to the user for manual publishing.

### Step 7 — Skill chaining

After publishing (or if the user decided not to save), **always** propose transitioning to the next skill:

> "Requirements are ready. Would you like to create Jira tasks for implementing this feature? I'll pass the context (requirements link, Epic, platforms) to the Feature Task Creator skill."

If the user agrees:
- Pass the full context: requirements document link, Epic key, feature number, platforms, approach (feature flag / A/B test), locales
- The Feature Task Creator skill will use these requirements as the source for creating Jira issues

If the user declines — end the workflow gracefully.

### Step 8 — Design Bridge handoff (Optional)

> Requires: `design-bridge` skill (Grow PM v1.10.0+). If not installed — skip gracefully.

Requirements часто є вхідною точкою для developer handoff та для low-fi prototype. Через `AskUserQuestion`:

> "Requirements published. Create a design-side deliverable?"
> 1. **Developer handoff spec** — повна специфікація для фронту (tokens, components, states, breakpoints, a11y) — recommended якщо requirements включали UI changes
> 2. **Low-fi UI prototype** — для візуальної валідації перед розробкою
> 3. **Deck для dev-review** — 6-8 слайдів зі scope + UI flow + edge cases
> 4. **Skip**

IF user selects 1 → invoke `design-bridge` with:
- `intent: handoff`
- `source: requirements_page_url`
- `a11y_audit: true` (обов'язково для handoff)
- `figma_context: from requirements_page OR ask user`

IF user selects 2 → invoke `design-bridge` with:
- `intent: prototype`
- `source: requirements_page_url`
- `fidelity: lo-fi | mid-fi` (ask)

IF user selects 3 → invoke `design-bridge` with:
- `intent: deck`
- `subtype: feature-concept` (найближчий до requirements pitch)
- `audience: dev_handoff`
- `length: 6-8`

Fallback: якщо `design-bridge` не встановлений — display: "Install `grow-product-manager` v1.10.0+ to enable design-bridge handoffs." Не блокуй workflow.

---

## Mode: Analyze & Improve — Workflow

This mode is for reviewing and improving **already written requirements**. The goal is to act as an experienced Business Analyst: assess the quality, completeness, and coherence of the document, ask clarifying questions where needed, propose concrete improvements, and optionally initiate additional research to validate whether the requirement is worth implementing.

### A1 — Read existing requirements

**A1a. Determine the source of requirements:**

- **Confluence link provided** → read page via Confluence MCP (`getConfluencePage`) or browser fallback. Extract full text, tables, and structure
- **File provided** → read from uploaded file
- **Text pasted into dialogue** → use as-is
- **No source provided** → ask via AskUserQuestion:
  > "Please provide the existing requirements — paste the text, share a Confluence/Notion link, or upload a file."

**A1b. Read supporting context:**

After reading the requirements, check if additional context is available:
- If a Jira Epic is referenced — read it via Jira MCP to understand the broader goal
- If a Confluence concept/PRD is referenced — read it for background
- If Figma designs are linked — read via Figma MCP for design context

### A2 — Structural analysis

Evaluate the document against the standard requirements template (`references/requirements-template.md`) and the standard quality criteria:

**Structure completeness check — assess each section:**

| Section | Present? | Quality assessment |
|---------|----------|-------------------|
| Hypotheses | ✅ / ⚠️ Missing | Clear, measurable, falsifiable? |
| Goals | ✅ / ⚠️ Missing | Tied to a measurable outcome? Or redundant with metrics? |
| Metrics | ✅ / ⚠️ Missing | Specific metrics named? Expected changes quantified? |
| Business requirements | ✅ / ⚠️ Missing | Covers all user types? Rules clearly stated? |
| Functional requirements | ✅ / ⚠️ Missing | Decomposed by block/screen/stage? Numbered? Unambiguous? |
| Technical requirements | ✅ / ⚠️ Missing | Approach selected (flag/A/B)? Platforms? Locales? |
| UI&UX requirements | ✅ / ⚠️ Missing | Design placeholder present? Figma links included if available? |
| Analytics coverage | ✅ / ⚠️ Missing | Placeholder present? Any analytics events specified? |
| Tasks section | ✅ / ⚠️ Missing | Epic link? Jira macro or task list? |

**Content quality check:**

- Are hypotheses falsifiable and tied to a measurable outcome?
- Are functional requirements specific enough for a developer to implement without asking follow-up questions?
- Are edge cases and error states described?
- Are all user types (buyer, seller, admin, etc.) covered where relevant?
- Are there internal contradictions or ambiguities?
- Is the scope clear — what IS in scope and what is NOT?
- Are acceptance criteria or success thresholds defined?

### A3 — Present analysis results

Present findings to the user in a structured format:

```
## Requirements Analysis — [Document title]

### Overall assessment
[Brief summary: strong points and main gaps. 2-4 sentences.]

### Completeness
| Section | Status | Issue |
|---------|--------|-------|
| Hypotheses | ✅ Present | — |
| Metrics | ⚠️ Incomplete | Expected % change not specified |
| Functional requirements | ❌ Missing | No breakdown by screen/block |
| ... | ... | ... |

**Completeness score: X/9 sections fully covered**

### Content issues
1. **[Issue title]** — [description of the problem and why it matters]
2. ...

### Strong points
- [What is well written and should be preserved]
- ...
```

### A4 — Clarifying questions

Based on gaps identified in A2 and A3, ask the user targeted clarifying questions to fill in the missing context. Ask in batches — group related questions together to avoid overwhelming the user.

Prioritize questions by impact:
1. **Critical** — missing information that blocks implementation (e.g., no functional requirements for a key scenario)
2. **Important** — missing information that reduces quality (e.g., no metrics, no edge cases)
3. **Recommended** — additions that strengthen the document (e.g., competitor precedents, rollback plan)

For each clarifying question, briefly explain why this information matters:

> "The functional requirements don't cover what happens when a user has no purchase history. This is needed so the BE team knows what to return in that case. Could you describe the expected behavior?"

Continue asking until all critical and important gaps are resolved, or the user explicitly says to proceed with what's available.

### A5 — Propose improvements

Present a prioritized list of concrete improvement proposals:

```
## Proposed improvements

### Critical (required for implementation)
1. **Add functional requirements for [scenario]** — currently missing. Here is a draft based on the context provided:
   [draft requirement text]

2. **Clarify [section]** — the current wording "[quote]" is ambiguous. Proposed revision:
   [revised text]

### Important (quality improvements)
3. **Add expected metric changes** — currently the Metrics section lists metrics without target values. Based on the product context, suggest:
   [suggested values or "please provide"]

4. **Add edge cases to functional requirements** — [list of missing scenarios]

### Recommended (optional enhancements)
5. **Add a rollback plan** — for a feature of this scale, it's good practice to define rollback conditions
6. **Restructure [section]** — current structure makes it hard to read; proposed restructuring: [description]
```

Ask the user via AskUserQuestion:

> "Which of these improvements would you like to apply? You can select all, some, or none."

- **All** → apply all improvements in priority order
- **Selected** → apply only the chosen ones
- **None** → skip to next step
- **Discuss first** → explain any specific improvement in more detail before deciding

### A6 — Apply improvements

For each approved improvement:
1. Edit the relevant section of the requirements
2. Show the before/after diff for the changed section
3. Ask for confirmation before moving to the next change (or apply all at once if the user prefers)

After all improvements are applied — present the full updated document for final review.

### A7 — Feasibility research (optional)

After analysis and improvements, offer to validate the requirement from a strategic and product perspective:

> "Would you like me to assess the feasibility and advisability of implementing this requirement? I can research: competitor implementations, user behavior data, technical risk, and alignment with product goals."

If the user agrees — **invoke the Product Research skill** with the following context:
- Feature description and hypotheses from the requirements
- Product name and key metrics from `local-context.md`
- Research goal: assess whether this feature is worth building, what analogues exist in the market, what risks exist

The Product Research skill will return: competitive analysis, market evidence, risk assessment, and a recommendation. Use these results to:
- Add a "Research summary" section to the requirements (or as a linked document)
- Highlight if the research reveals reasons to reconsider the approach, pivot the hypothesis, or de-prioritize the feature
- If research is discouraging — explicitly flag this to the user and ask how they want to proceed

If the user declines the research offer — proceed to publishing.

### A8 — Publishing updated requirements

After the user confirms the improved document:

**A8a. Ask if the user wants to save:**

> "Would you like to save the updated requirements? I can update the original document or save a new version."

Options:
- **Update original** — overwrite the existing Confluence/Notion page with the improved version
- **Save as new version** — create a new page (e.g., with "[Updated]" or a version suffix in the title)
- **No** — end the skill, results stay in the dialogue

**A8b. Publishing flow:**

Follow the same publishing flow as **Create Mode — Step 6** (Confluence, Notion, Google Docs, other).

### A9 — Skill chaining

After publishing, always offer the next step:

> "Requirements are improved and saved. Would you like to create Jira tasks for implementing this feature?"

If the user agrees — invoke Feature Task Creator with full context.

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
- **`references/approach-recommendation.md`** — implementation approach recommendation logic (feature flag, A/B test, etc.)
- **`references/integration-strategy.md`** — MCP → Registry → Browser fallback chain (shared across all skills)
- **`references/data-policy.md`** — data confidentiality policy: what data can and cannot be shared externally (mandatory reading before any data gathering)
- **`references/self-improvement.md`** — self-improvement protocol: how to learn from user corrections and improve skill algorithms

