---
name: product-research
version: 0.7.0
description: Conduct comprehensive product research — competitive analysis, user research, market research, or UX benchmark research. Use when the user asks to "research competitors", "analyze the market", "do competitive analysis", "synthesize user interviews", "find market trends", "compare against industry benchmarks", "search knowledge library", or needs SWOT, TAM SAM SOM, or PESTEL analysis.
---

# Product Research

Conduct structured product research and deliver results as a Confluence page.

## Integration prerequisite

Before gathering data, read and follow the integration fallback chain in `references/integration-strategy.md`. For this skill, the typical external products needed are:

- **Confluence** — for reading internal knowledge and publishing results
- **Google Drive** — for reading internal documents, research materials, reports, and any files stored in the team's Drive
- **Figma** — for pulling design context if researching UI/UX topics
- **Product Analysis skill** — for analyzing product metrics, dashboards, and data (invoked when research needs quantitative data analysis)
- **Knowledge Library** — for searching curated sources (articles, benchmarks, best practices) that enrich research with pre-vetted knowledge
- **Web** — always available via WebSearch

For each product: check for MCP connector → search MCP registry → fall back to browser.

Before gathering any data, also read and comply with `references/data-policy.md`. Confidential data (Tableau metrics, internal analytics, research materials) must NOT be passed to external LLMs or third parties.

## Local context prerequisite

**Before starting, follow `references/local-context-protocol.md` (Step 0).** Read `local-context.md`, select the active product, and load all product-specific context. If the file doesn't exist — redirect to Plugin Configurator for initial setup.

Key context used by this skill:
- `product.name`, `product.description`, `product.url` — for product context in research
- `product.competitors` — pre-fill competitor list for competitive analysis, always include user's product in comparisons
- `product.confluence_space` — default publishing destination
- `organization.domain` — for understanding company context
- `user.language` — for output language

**Knowledge Library context** (if initialized):
- `knowledge_library.status` — whether Knowledge Library is initialized (`~/.grow-pm/knowledge-library/`)
- `knowledge_library.sources_count` — number of curated sources available
- `knowledge_library.search_modes` — available search modes (semantic, keyword, hybrid)
- `knowledge_library.baymard_access` — access to Baymard UX benchmarks (if configured)
- `knowledge_library.confluence_spaces` — integrated Confluence spaces for knowledge enrichment

## Step T — Template Resolution

Before producing the research report, resolve which template to use.

Follow `references/template-protocol.md`.

Declare:
- `artifact_type: research`
- `subtype: {inferred from research type — "competitive" | "user-research" | "market" | "ux-benchmark" | null}`
- `product_id: {from local-context.md active product}`
- `language: {from local-context.md → user.language or product.default_language}`

Run Steps T-1 → T-5 via the `template-library` helper routines. Render the result and append `<!-- template: {template_id} version: {version} -->` at the end.

If the user says "do not use a template" → skip Step T and use the skill's internal structure.

If no template applies → fall back to built-in `research-builtin-competitive` (for competitive), `research-builtin-user-research` (for user research), or skill's internal structure for other subtypes.

## Workflow

### 1. Deep discovery — gather maximum context before research

This step is critical. Do NOT start research until the scope is crystal clear. Use AskUserQuestion to clarify all of the following:

**Product and feature context — clarify via AskUserQuestion if not clear from context:**

- **Which product or part of the product ecosystem** is this research for? (if not explicitly stated — ask before proceeding)
- **New or existing functionality?** — Is this research for completely new functionality we are planning to build, or for existing functionality we are developing/modifying? (if not clear — ask explicitly)

**Research scope:**
- Research type: competitive analysis, user research, market research, UX benchmark research, or a combination
- Subject: specific product, feature area, market segment, or user persona
- Depth: quick overview (1-2 pages) or deep dive (5+ pages)
- Goal: what decision will this research inform? (e.g., launch/no-launch, feature prioritization, market entry)
- Audience: who will read the result? (team, leadership, investors)

**Context gathering — ask proactively:**
- What does the user already know about the topic? Any hypotheses or assumptions to validate?
- Are there existing internal documents (Confluence pages, previous research, strategy docs) to build upon?
- Are there specific competitors, markets, or user segments to focus on or exclude?
- What time frame is relevant? (last quarter, last year, all-time)
- Any specific metrics, KPIs, or data points the user wants included?

**Sources and tools — confirm where to look:**
- Ask the user which sources and tools to use for this specific research
- Suggest relevant sources based on the research type (web, Confluence, Google Drive, Figma, Tableau, uploaded files)
- Ask whether there are relevant documents in **Google Drive** (research reports, strategy docs, meeting notes, spreadsheets) — if yes, ask the user to share links or folder names
- **Deep Research via external LLMs — ask about each LLM separately via AskUserQuestion:**
  - "Should we use **ChatGPT** in Deep Research mode for deeper analysis?" (via the user's browser)
  - "Should we use **Google Gemini** in Deep Research mode for deeper analysis?" (via the user's browser)
  - The user can enable one, both, or neither. If both are enabled — run Deep Research in both LLMs and cross-reference their findings
- If the user has preferences for specific tools or databases, capture them now

**Knowledge Library check:**

Follow `references/local-context-protocol.md` — Step 0g:
- Check if Knowledge Library is initialized (`~/.grow-pm/knowledge-library/`)
- If available and contains sources relevant to the research topic (≥3 matching sources), inform the user:
  > "Knowledge Library has [N] sources relevant to [topic]. Would you like to include them in the research?"
- If user confirms → library sources will be included in Step 2
- If not available → skip, no impact on workflow

**Figma designs check — if researching existing product or existing functionality:**

If the product or feature area already exists (i.e., not being built from scratch), ask via AskUserQuestion:

> "Are there current designs / mockups / prototypes of this functionality in Figma?"

- **If the user provides a link** — open it via Figma MCP (`get_design_context`, `get_screenshot`) or browser fallback, read and extract: current UX flows, screens, key UI patterns. Use this as context for the research (e.g., when analyzing competitor UX, reference the current state)
- **If the user believes designs should exist but cannot provide a link** — offer to search:
  > "I can search for relevant mockups in Figma from your account. Would you like me to search?"
  - If agreed — search via Figma MCP or browser (`https://www.figma.com`):
    - Try to understand the structure of the design system: look for sections like "Current design", "Production", "Live", "Ready for dev", "Latest state"
    - Show the user the found files/frames and ask them to confirm which are relevant and up-to-date
  - If Figma MCP is unavailable — follow `references/integration-strategy.md` fallback chain
- **If no designs exist** — note this and proceed without design context
- **If relevant designs are confirmed** — use them as primary context for understanding the current state. Reference design frames in the final research output

Summarize the full research brief back to the user and get confirmation before proceeding.

### 2. Gather data from all available sources

Pull information from every source agreed upon in Step 1. For each external product, follow the integration fallback chain from `references/integration-strategy.md`.

**Web search** — use WebSearch to find:
- Competitor websites, pricing pages, feature lists
- Industry reports, analyst coverage, market sizing
- Product reviews, G2/Capterra ratings, user feedback
- News, funding announcements, partnership deals

**Uploaded files** — if the user provides files (interview transcripts, survey results, reports), read them with the Read tool and extract key data points.

**Knowledge Library** (if user confirmed in Step 1):
- Call `knowledge-library` in Search mode with research topic keywords
- Include sources with trust_score >= 0.5
- For each matching source: include URL, key insights, trust score, source type
- Mark library sources in the final output's Sources section as "Source: Knowledge Library"
- If sources contain benchmark data → use in competitive analysis matrices
- Library sources complement (not replace) web search — they provide pre-vetted, curated knowledge

**Confluence** — search existing Confluence pages for internal knowledge:
- Previous research, decision logs, meeting notes
- Product specs, OKRs, strategy docs
- Use `searchConfluenceUsingCql` or `getConfluencePage` to find relevant pages
- If Confluence MCP is unavailable, follow integration-strategy.md fallback chain

**Google Drive** — search and read internal documents stored in Google Drive:
- Research reports, strategy presentations, user interview notes, competitive analyses
- Product briefs, roadmap spreadsheets, analytics exports
- Follow the integration fallback chain: Google Drive MCP → search MCP registry → open via browser (`https://drive.google.com`)
- When accessing via browser: navigate to the shared link or search within Drive, open the document, read its content using `get_page_text`
- Treat all Drive documents as potentially confidential — follow `references/data-policy.md`

**Figma** (when researching UI/UX or competitor design):
- Pull screenshots and design context via Figma MCP
- If unavailable, use browser to access Figma files shared by the user

**Product Analysis skill** (when research needs product metrics or data analysis):

When the research requires quantitative data — product metrics, dashboard analysis, funnel data, cohort analysis, or any numerical analysis — delegate to the **Product Analysis** skill:

1. Invoke Product Analysis with context: which product, what metrics are needed, what time period, what comparison baseline
2. Product Analysis will handle all data acquisition (Tableau, Google Sheets, CSV, screenshots) and computation
3. Receive structured results: key metrics, trends, anomalies, relevant hypotheses
4. Incorporate the returned data into the research output, citing "Source: Product Analysis" for data-driven findings

This delegation ensures accurate computation (via pandas/numpy) and consistent analysis methodology across all skills.

**Deep Research via ChatGPT** (if confirmed by user in Step 1):

1. Open ChatGPT via browser (`navigate` to `https://chatgpt.com`)
2. Select the strongest model available in the user's interface (e.g., GPT-4o, o3)
3. Activate **Deep Research** mode if available in the interface
4. Compose a detailed research prompt based on the agreed scope from Step 1 — include specific questions, competitors, market segments, and what data points are needed
5. Submit the prompt and wait for the full response
6. Read and extract the findings using `read_page` / `get_page_text`
7. Use the extracted data as additional context — cross-reference with other sources, note any contradictions or unique insights

**Deep Research via Google Gemini** (if confirmed by user in Step 1):

1. Open Gemini via browser (`navigate` to `https://gemini.google.com`)
2. Select the strongest model available in the user's interface (e.g., Gemini 2.5 Pro)
3. Activate **Deep Research** mode if available in the interface
4. Compose a detailed research prompt — can be the same as for ChatGPT, or adjusted based on ChatGPT's results if it was run first (to fill gaps or verify claims)
5. Submit the prompt and wait for the full response
6. Read and extract the findings using `read_page` / `get_page_text`
7. Use the extracted data as additional context — cross-reference with ChatGPT results (if both are used) and other sources

**If both ChatGPT and Gemini are used:**
- Run both Deep Research sessions
- Cross-reference findings — note where both LLMs agree (higher confidence) and where they diverge (flag for verification)
- Present a unified view in the research output, citing which LLM provided each insight

**Important guidelines for LLM-sourced data:**
- Always cross-verify claims from LLMs against web search or internal data
- Mark LLM-sourced insights in the final output (e.g., "Source: ChatGPT Deep Research" or "Source: Gemini Deep Research")
- If LLMs provide conflicting information, present both perspectives with a note
- Do NOT treat LLM output as primary source — use it to enrich and deepen the analysis

### 3. Analyze and structure findings

Apply the appropriate framework(s) based on research type. See `references/frameworks.md` for detailed templates.

**Competitive analysis** → Feature comparison matrix, SWOT, positioning map, pricing comparison, key takeaways

**Important: always include the user's product in competitive comparisons.** When building a feature comparison matrix, benchmark table, positioning map, or any other comparative analysis — always include the user's own product as one of the compared entities alongside competitors. This allows the user to immediately see where their product stands relative to the competition. Clearly mark the user's product in the table (e.g., bold name, highlight row) so it's visually distinct.

**User research** → Themes & patterns, user segments, pain points ranked by frequency/severity, quotes, insights → recommendations

**Market research** → Market sizing (TAM/SAM/SOM), trends, PESTEL factors, opportunities & threats, growth drivers

**UX Benchmark Research** → Feature/practice comparison against industry benchmarks, UX best practices matrix, gap analysis between current state and industry standards, recommendations ranked by impact

**Important for UX Benchmark Research type:**
- Primary source: Knowledge Library (if initialized with UX sources)
- Secondary source: web search for fresh benchmarks
- Output format: benchmark matrix (practice, industry standard, our current state, gap, priority)
- This type is commonly used by `cjm-research` during enrichment steps

### 4. Confirm Confluence location and publish

**Before creating the page**, if the user has not already specified where to publish, use AskUserQuestion to clarify:

- Which Confluence **space** to use?
- Which **parent page** to nest the research under? (offer to search existing pages to help the user decide)
- Suggest a logical location based on the research type (e.g., "Research" or "Competitive Analysis" section)
- Show the proposed page title for confirmation: `[Research Type] — [Subject] — [Date]`

Once confirmed, create the Confluence page using `createConfluencePage` with:

- The confirmed title and location
- Structured sections matching the framework used
- Tables for comparison data
- A summary/TL;DR section at the top
- **Glossary section** — at the end of the document (before Sources), add a "Glossary" section that explains all terms, professional jargon, abbreviations, and metrics used in the report. For each term provide a concise, clear definition accessible to a reader who may not be deeply familiar with the domain. Examples: "CAC (Customer Acquisition Cost) — cost of acquiring one customer", "Churn rate — percentage of users who stop using the product over a given period", "TAM (Total Addressable Market) — the total market volume theoretically available to the product". Use the user's preferred language (`user.language`) for the glossary content.
- Sources section at the bottom with links — clearly marking each source type (Web, Confluence, Google Drive, Knowledge Library, ChatGPT Deep Research, Gemini Deep Research, uploaded file, etc.)

**Confluence formatting requirements — use standard (non-legacy) elements:**

Use only current, non-deprecated Confluence elements. Do NOT use elements marked as "Legacy" in the Confluence editor.

1. **Table of Contents** — use the current Table of Contents macro (not the legacy TOC macro). Heading levels 1-6
2. **Headings** — H1/H2/H3 hierarchy for all sections and subsections
3. **Dividers** — horizontal rule between all major sections (use the current divider, not the legacy horizontal rule)
4. **Tables** — use the standard Confluence table element for all structured data: comparison matrices, feature lists, metric tables, SWOT grids
5. **Bold text** — highlight key theses, important conclusions, critical data points
6. **Expand/Collapse sections** — use the current Expand macro (not legacy) for long detailed sections that may clutter the page (e.g., full competitor profiles, detailed data tables)
7. **Info/Note/Warning panels** — use the current panel macros for callouts (key insights, warnings, caveats)
8. **Links** — use standard Confluence page links and external URL links
9. **Status lozenges** — use for quick visual indicators where appropriate (e.g., feature availability: ✅ Available / ❌ Missing / 🔶 Partial)

**Avoid legacy elements**: If an element is marked "Legacy" in the Confluence editor, do not use it. Always prefer the current/modern equivalent.

If Confluence MCP is unavailable, follow the integration fallback chain. As a last resort, generate the content as a local document and let the user publish manually.

### 5. Summary report and feedback

After publishing, provide a structured report of what was done:

**Report format:**
- **What was done:** brief description of the research conducted (type, scope, depth)
- **Artifacts created:** links to all created documents (Confluence page, local files, etc.)
- **Key findings:** 3-5 key takeaways from the research
- **Sources used:** list of source types used (Web, Confluence, Google Drive, Knowledge Library, Figma, ChatGPT Deep Research, Gemini Deep Research, uploaded files)
- **Recommended next steps:** suggested follow-up actions

**After presenting the report, proactively ask for feedback:**

> "Are you satisfied with the research results? Would you like to refine, add, or change anything?"

- If the user requests changes — iterate: update the research, re-publish, present updated report
- If the user confirms — proceed to the next step

**Self-improvement check** (after corrections are applied and confirmed):

If the user requested corrections during review, analyze whether the skill's algorithm can be improved to prevent similar issues in the future. Follow the full protocol in `references/self-improvement.md`. In short:
1. Analyze the root cause of the error — is this a pattern or a one-off?
2. If it's a pattern — propose a specific improvement to the skill's conditions
3. If the user agrees — update the SKILL.md, re-package the plugin, and provide the updated file

### 6. Propose next step — Write Concept / PRD / CJM Research

After sharing the research summary, **always** propose transitioning to the next step:

> "Research is complete. Would you like to create a concept (PRD) for a feature based on these results? I can pass the full research context to the Write Concept / PRD skill and we can start drafting the document right away."

If UX Benchmark Research was conducted, also offer:
> "Run **CJM Research** to analyze your funnel using these benchmarks as evidence"

If the user agrees to Write Concept:
- Pass the full research context to the Write Concept / PRD skill: Confluence page link, key findings, identified opportunities, data sources used
- The Write Concept skill will use these research results as primary input (Step 2 of its workflow)
- No need to re-gather the same data — the research is already done

If the user agrees to CJM Research:
- Invoke CJM Research skill with the benchmark data and gap analysis
- Pass the benchmark matrix and current state analysis
- CJM Research will use these findings to enrich the journey analysis with evidence-backed insights

If the user declines — end the workflow gracefully.

### Step D — Design Bridge handoff (Optional)

> Requires: `design-bridge` skill (Grow PM v1.10.0+). If not installed — skip gracefully.

Research synthesis naturally converts into a research-highlights deck for distribution among the team and stakeholders. Via `AskUserQuestion`:

> "Research published. Create a design-side deliverable?"
> 1. **Research highlights deck** — 10-slide summary with key themes, quotes, and numbers — recommended for user research or UX benchmark results
> 2. **Research-enrichment through design:research-synthesis** — pass raw interview notes through Claude Design's research-synthesis for deeper thematic analysis (if user research included raw transcripts)
> 3. **Skip**

IF user selects 1 → invoke `design-bridge` with:
- `intent: deck`
- `subtype: research-highlights`
- `source: confluence_research_page_url`
- `audience: team` (default; upgrade to `c-level` upon request)
- `length: 10`

IF user selects 2 → invoke `design-bridge` with:
- `intent: research-enrichment`
- `source: raw interviews / survey responses`
- design-bridge will return structured themes — add as appendix to research page

Fallback: if `design-bridge` is not installed — display: "Install `grow-product-manager` v1.10.0+ to enable design-bridge handoffs." Do not block the workflow.

## Quality standards

- Always cite sources with links
- Distinguish facts from opinions/interpretations
- Flag data that is older than 12 months
- If data is insufficient, explicitly state gaps and suggest how to fill them
- Use Ukrainian or English based on user's language preference

## Additional Resources

- **`references/local-context-protocol.md`** — Step 0: how to read and use local-context.md (mandatory before any skill execution)
- **`references/frameworks.md`** — detailed templates for each research framework
- **`references/integration-strategy.md`** — MCP → Registry → Browser fallback chain (shared across all skills)
- **`references/data-policy.md`** — data confidentiality policy: what data can and cannot be shared externally (mandatory reading before any data gathering)
- **`references/self-improvement.md`** — self-improvement protocol: how to learn from user corrections and improve skill algorithms
- **`references/cjm-protocol.md`** — CJM anomaly severity, funnel impact formulas (relevant when research supports CJM analysis)
