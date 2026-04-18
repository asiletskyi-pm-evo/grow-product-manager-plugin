---
name: write-concept
version: 0.6.0
description: Write a product concept (PRD) document from a feature idea, problem statement, or existing research. Use when the user asks to "write a concept", "create a PRD", "describe a feature", "write a spec", or needs help turning a vague idea into a structured product document.
---

# Write Concept (PRD)

Turn a feature idea or problem statement into a structured product concept document and publish it as a Confluence page.

## Integration prerequisite

Before gathering data, read and follow the integration fallback chain in `references/integration-strategy.md`. For this skill, the typical external products needed are:

- **Confluence** — for reading internal knowledge, existing research, and publishing the final PRD
- **Google Drive** — for reading internal documents, research materials, briefs, and specs stored in the team's Drive
- **Figma** — for pulling design context when the concept involves UI/UX
- **Product Analysis skill** — for analyzing product metrics and data relevant to the concept (invoked when concept needs quantitative data)
- **Web** — always available via WebSearch
- **ChatGPT / Gemini** — for Deep Research via browser when deeper analysis is needed

For each product: check for MCP connector → search MCP registry → fall back to browser.

Before gathering any data, also read and comply with `references/data-policy.md`. Confidential data (Tableau metrics, internal analytics, research materials) must NOT be passed to external LLMs or third parties.

## Local context prerequisite

**Before starting, follow `references/local-context-protocol.md` (Step 0).** Read `local-context.md`, select the active product, and load all product-specific context. If the file doesn't exist — redirect to Plugin Configurator for initial setup.

Key context used by this skill:
- `product.name`, `product.description` — for product context in PRD
- `product.confluence_space` — default publishing destination
- `product.key_metrics`, `product.current_okrs` — for Success Metrics and Goals sections
- `user.language` — for output language

### Step 0.5: Vault Context Search (Optional)

> Requires: `references/vault-protocol.md` → Step 0.5

IF vault_level > L0 (detected during Step 0h):

1. Search vault for relevant prior artifacts:
   - Types: `competitive-analysis`, `market-research`, `ux-benchmark`, `hypothesis`, `decision`, `requirements`
   - Product: active product
   - Tags: keywords from user's feature idea or problem statement
   - Status: `active`, `draft`
   - Sort: `created DESC`, limit: 10

2. IF results found:
   - Display: "Found {N} related artifacts in your knowledge base that may inform this concept:"
   - Show: title, type, date, brief summary
   - Ask: "Use as context? [Yes / Select specific / Skip]"

3. IF user accepts:
   - Read full content of selected artifacts
   - Use as input for the concept:
     - Research findings → feed into Problem Statement and Proposed Solution
     - Prior hypotheses → reference as basis for the concept
     - Decisions → respect previous decisions, reference in rationale
     - Existing requirements → avoid duplication, reference as related work
   - Include "Informed by" section in concept metadata

4. IF user skips OR no results → continue normally

## Step T — Template Resolution

Before writing the concept, resolve which template to use.

Follow `references/template-protocol.md`.

Declare:
- `artifact_type: concept`
- `subtype: {null | inferred from user input, e.g. "lightweight", "technical-spec"}`
- `product_id: {from local-context.md active product}`
- `language: {from local-context.md → user.language or product.default_language}`

Run Steps T-1 → T-5 via the `template-library` helper routines:
- T-1 Load registry from `{storage_root}/Templates/_registry.json`
- T-2 Score candidates (product > user-global > built-in; subtype match; language match)
- T-3 Decide based on `templates.preference` (`auto` / `always_ask` / `smart`)
- T-4 Collect variables via `AskUserQuestion`
- T-5 Render and append `<!-- template: {template_id} version: {version} -->` to the output

If the user explicitly says "do not use a template" → skip Step T and use the skill's internal structure (the workflow below).

If no template applies → fall back to the built-in `concept-builtin-default` template; if that's also missing, use the skill's internal structure.

The resolved template may reshape the sections and questions of the workflow below. Variables from the template take precedence over the generic discovery questions for overlapping fields.

## Workflow

### 1. Deep discovery — gather maximum context

This step is critical. Do NOT start writing until the scope is crystal clear. Use AskUserQuestion to clarify all of the following:

**Product and feature context — clarify via AskUserQuestion if not clear from context:**

- **Which product or part of the product ecosystem** is this concept for? (if not explicitly stated — ask before proceeding)
- **New or existing functionality?** — Are we creating a concept for completely new functionality within the product/ecosystem, or are we developing/modifying existing functionality? (if not clear — ask explicitly)

**About the concept:**
- What is the feature/idea? What problem does it solve and for whom?
- For which product/project is this being created?
- Who is the audience for this document — team, leadership, stakeholders?
- What type of feature is this — frontend, backend, infrastructure, product, design change? (this determines which sections to expand or minimize)

**Adapting the PRD structure:**

Present the full standard block list and ask the user to confirm which blocks are needed for this specific concept:

1. Summary (TL;DR)
2. Problem Statement
3. Goals & Non-Goals
4. User Stories / Use Cases
5. Proposed Solution
6. What Changes for Users
7. Alternative Solutions *(ask if needed)*
8. Scope & Phasing
9. Design & UX *(adaptive)*
10. Technical Considerations *(adaptive)*
11. Success Metrics
12. Risks & Mitigations
13. Timeline & Milestones *(adaptive)*
14. Open Questions

Ask the user:
- Which of these blocks are needed for this concept?
- Are there any **additional specific blocks** not in the standard list? If yes — clarify what exactly should be in each custom block
- Are **alternative solutions** needed in this PRD?

**Context sources:**
- Are there existing materials — Confluence pages, Google Drive documents, research, notes, uploaded files?
- Are there relevant documents in **Google Drive** (briefs, specs, research reports, OKR files, strategy decks)? If yes — ask the user to share links or folder names
- Where to gather context: conversation, Confluence, Google Drive, web, uploaded files, Deep Research via LLM?
- The user chooses the sources or provides data directly

**Figma designs check — if working with existing product or existing functionality:**

If the product or feature already exists (i.e., not being built from scratch), ask via AskUserQuestion:

> "Are there current designs / mockups / prototypes of this functionality in Figma?"

- **If the user provides a link** — open it via Figma MCP (`get_design_context`, `get_screenshot`) or browser fallback, read and extract: current UX flows, screens, key UI patterns. Use this as context when drafting the concept (especially for "What Changes for Users", "Proposed Solution", and "Design & UX" blocks)
- **If the user believes designs should exist but cannot provide a link** — offer to search:
  > "I can search for relevant mockups in Figma from your account. Would you like me to search?"
  - If agreed — search via Figma MCP or browser (`https://www.figma.com`):
    - Try to understand the structure of the design system: look for sections like "Актуальний дизайн", "Current design", "Production", "Live", "Ready for dev", "Поточний стан"
    - Show the user the found files/frames and ask them to confirm which are relevant and up-to-date
  - If Figma MCP is unavailable — follow `references/integration-strategy.md` fallback chain
- **If no designs exist** — note this and proceed without design context
- **If relevant designs are confirmed** — use them throughout the PRD: reference current UX state in the Problem Statement, describe what changes vs. current design in "What Changes for Users", include links to relevant frames in the Sources section

Summarize the full brief back to the user and get confirmation before proceeding.

### 2. Gather data from sources

**First — check for existing Product Research results:**

Search Confluence for pages that match the concept topic (previous research, competitive analysis, market research created by the Product Research skill or manually).

- If Product Research results are found — inform the user and ask: is the existing research sufficient, or should additional research be conducted via the Product Research skill?
  - If sufficient — use the found materials as primary context and proceed to Step 3
  - If additional research is needed — trigger the Product Research skill, wait for results, then add them to the context
- If no Product Research results exist — gather data from all sources agreed upon in Step 1

**Data gathering from agreed sources:**

- **Conversation** — extract requirements and context from the dialogue with the user
- **Confluence** — search existing pages: strategy docs, OKRs, previous specs, decision logs. Use `searchConfluenceUsingCql` or `getConfluencePage`. If Confluence MCP is unavailable — follow integration fallback chain
- **Google Drive** — read internal documents shared by the user or accessible via Drive: research reports, product briefs, strategy presentations, analytics exports, OKR files. Follow the integration fallback chain: Google Drive MCP → search MCP registry → open via browser (`https://drive.google.com`). When accessing via browser: navigate to the shared link or search within Drive, open the document, read content using `get_page_text`. Treat all Drive content as potentially confidential per `references/data-policy.md`
- **Uploaded files** — read with the Read tool, extract key data points
- **Web search** — use WebSearch for external context: best practices, competitor approaches, industry standards
- **Figma** — pull design context via Figma MCP when the concept involves UI/UX. If unavailable — use browser
- **Product Analysis skill** — when the concept needs product metrics, data analysis, or quantitative evidence, invoke the **Product Analysis** skill. Pass context: which product, what metrics are relevant to the concept, what time period. Receive structured results (key metrics, trends, anomalies) and incorporate into the PRD — especially in Success Metrics, Problem Statement, and Goals sections. Cite as "Source: Product Analysis"
- **Deep Research via ChatGPT / Gemini** — when confirmed by the user, open the LLM web interface via browser, select the strongest available model, activate Deep Research mode, submit a detailed prompt based on the concept scope, extract findings and use as additional context

For each tool: MCP → registry → browser (per `references/integration-strategy.md`).

### 3. Clarify "What Changes for Users" block

If the context does not make it clear which users are affected — ask separately using AskUserQuestion:

- Which user types does this concept affect? (e.g., buyers only / sellers only / buyers and sellers / admins / all users)
- For each identified user segment, define:
  - What exactly changes in their experience
  - What they gain from this feature
  - What they lose or what changes in their existing flow

### 4. Draft the PRD

Build the concept document following the confirmed structure from Step 1:

**Adaptive sections** — adjust depth based on feature type:
- **Frontend/product feature** → expand Design & UX, minimize Technical Considerations
- **Backend/infrastructure** → expand Technical Considerations, minimize or skip Design & UX
- **Cross-team feature** → expand Timeline & Milestones with dependencies
- **Autonomous small feature** → minimize Timeline & Milestones

**Content guidelines:**
- Include only the blocks confirmed in Step 1
- Add Alternative Solutions block if confirmed
- Include any custom blocks the user requested
- Cross-reference data from multiple sources
- Mark data sources throughout the document

### 5. Review with the user

Present the full draft to the user before publishing. Iterate until confirmed:
- Walk through each section
- Collect feedback and make edits
- May require multiple iterations

### 6. Confirm Confluence location and publish

If the user has not already specified where to publish — use AskUserQuestion:

- Which Confluence **space** to use?
- Which **parent page** to nest the PRD under? (offer to search existing pages to help decide)
- Suggest a logical location based on the project structure

Page title format: `[PRD] Feature Name`

**Confluence formatting requirements — mandatory for every PRD page:**

1. **Table of Contents** at the very top of the document — use the Confluence Table of Contents macro with heading levels 1 through 6 (standard)
2. **Dividers** between all key blocks — use the Confluence horizontal rule/divider element to visually separate sections
3. **Headings** — use proper H1/H2/H3 hierarchy for all sections and subsections
4. **Bold text** — highlight key theses, important conclusions, and critical data points in bold
5. **Tables** — use tables wherever structured data needs to be communicated: comparisons of alternatives, metrics, feature matrices, user impact summaries, risk/mitigation pairs
6. **Sources** section at the bottom with links, marking each source type (Confluence, Google Drive, Web, ChatGPT Deep Research, Gemini Deep Research, uploaded file, Product Research)

Publish via Confluence MCP (`createConfluencePage`). If unavailable — follow integration fallback chain. As a last resort, generate a local document for manual publishing.

After publishing, provide a structured report of what was done:

**Report format:**
- **What was done:** brief description of the concept created (feature name, type, scope)
- **Artifacts created:** links to all created documents (Confluence page, local files, etc.)
- **Key concept points:** 3-5 key points summarizing the PRD
- **Document structure:** list of blocks included in the PRD
- **Sources used:** list of source types used (Confluence, Google Drive, Product Research, Web, Figma, uploaded files)

**After presenting the report, proactively ask for feedback:**

> "Are you satisfied with the concept? Would you like to refine, add, or change anything?"

- If the user requests changes — iterate: update the PRD, re-publish, present updated report
- If the user confirms — proceed to the next step

**Self-improvement check** (after corrections are applied and confirmed):

If the user requested corrections during review, analyze whether the skill's algorithm can be improved to prevent similar issues in the future. Follow the full protocol in `references/self-improvement.md`. In short:
1. Analyze the root cause of the error — is this a pattern or a one-off?
2. If it's a pattern — propose a specific improvement to the skill's conditions
3. If the user agrees — update the SKILL.md, re-package the plugin, and provide the updated file

### 7. Propose next step — Brainstorm Features or Feature Task Creator

After sharing the concept summary, **always** propose transitioning to the next skill in the workflow:

> "Concept is ready. What's next? I can pass the context and transition to one of the following steps:
> 1. **Brainstorm Features and Hypotheses** — generate hypotheses and feature ideas based on this concept, evaluate them with ICE scoring and suggest validation methods
> 2. **Feature and Hypothesis Requirements Creator** — immediately create Jira tasks for feature implementation based on this concept"

If the user chooses **Brainstorm Features and Hypotheses**:
- Pass the full concept context: Confluence page link, problem statement, goals, proposed solution, user stories, success metrics
- The Brainstorm skill will use this concept as the starting point (Situation 1 of its workflow — concept/PRD exists)

If the user chooses **Feature and Hypothesis Requirements Creator**:
- Pass the full concept context: Confluence page link, scope, phasing, technical considerations
- The Feature Task Creator skill will use this concept as the requirements source

If the user declines — end the workflow gracefully.

### 7.5: Save to Vault (Optional)

> Requires: `references/vault-protocol.md` → Vault Save

IF vault_level > L0 AND vault sync_mode != "off":

1. Build artifact:
   ```
   vault_save({
     type: "concept",
     product: active_product,
     skill: "write-concept",
     skill_version: "0.5.0",
     tags: [feature area keywords, affected platforms, goal keywords],
     content: full_prd_markdown,
     related: [source research from Step 0.5, source hypotheses, related decisions],
     extra_frontmatter: {
       scope: "mvp" or "full" (based on phasing decision),
       phase_count: number_of_phases,
       estimated_effort: effort_estimate_if_discussed,
       published_to: confluence_or_notion_url (if published),
       confluence_page_id: page_id (if published to Confluence)
     }
   })
   ```

2. IF concept was informed by hypotheses from Vault (Step 0.5):
   - Update those hypotheses: add this concept as `children` link

3. Display: "Saved to Vault: Concepts/{product}/..."

## Additional Resources

- **`references/local-context-protocol.md`** — Step 0: how to read and use local-context.md (mandatory before any skill execution)
- **`references/vault-protocol.md`** — vault context search and save protocols
- **`references/vault-schema.md`** — vault artifact schema and metadata structure
- **`references/prd-structure.md`** — detailed templates for each PRD block
- **`references/integration-strategy.md`** — MCP → Registry → Browser fallback chain (shared across all skills)
- **`references/data-policy.md`** — data confidentiality policy: what data can and cannot be shared externally (mandatory reading before any data gathering)
- **`references/self-improvement.md`** — self-improvement protocol: how to learn from user corrections and improve skill algorithms

## PRD Block Reference

Detailed templates for each standard block are in `references/prd-structure.md`.

## Quality standards

- Always cite data sources
- Distinguish facts from assumptions — mark assumptions explicitly
- Flag data older than 12 months
- If information is insufficient for a block, state gaps and suggest how to fill them
- Use Ukrainian or English based on user's language preference
- Maintain consistent formatting: headings, bold highlights, tables, dividers
