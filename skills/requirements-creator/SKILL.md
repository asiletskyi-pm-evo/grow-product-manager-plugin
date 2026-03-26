---
name: requirements-creator
description: Create structured feature requirements documents as an experienced Business Analyst. Use when the user asks to "write requirements", "describe a feature", "create feature spec", "write A/B test requirements", or needs help turning a feature idea into a structured requirements document.
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

## Workflow

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

| # | Section | Skill behavior |
|---|---------|---------------|
| — | Table of Contents | Auto-generated (Confluence ToC macro levels 1-6 / equivalent for other tools) |
| 1 | Epic | Link to Epic description in Confluence |
| 2 | Hypotheses | Numbered table: №, Hypothesis |
| 3 | Goals | Numbered table: №, Goal (can be removed if goal = metrics) |
| 4 | Metrics | Numbered table: №, Metric, Expected change |
| 5.1 | Business requirements | Text with bold highlights for key theses |
| 5.2 | Functional requirements | Numbered table: №, Block/Module/Theme, Requirements |
| 5.3 | Technical requirements | Implementation approach, platforms, locales |
| 5.4 | UI&UX requirements | **Empty section** — to be filled by Product Designer. If Figma links to current designs were found — include them as reference |
| 5.5 | Analytics coverage requirements | **Empty section** — to be filled by Product Analyst |
| 6 | Tasks | Link to Epic in Jira + Jira work items macro with JQL filter (parent = EPIC-KEY AND labels = FEATURE-CODE) |

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

1. **Headings** — H1/H2/H3 hierarchy for all sections and subsections
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
