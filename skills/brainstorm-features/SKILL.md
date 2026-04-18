---
name: brainstorm-features
version: 0.6.0
description: Help Product Manager brainstorm features, hypotheses, and CJM Hypotheses. Use when the user asks to "brainstorm features", "generate hypotheses", "find growth opportunities", needs CJM funnel-driven hypothesis generation, or requires ICE scoring with funnel impact analysis.
---

# Brainstorm Features and Hypotheses

Help Product Manager conduct a structured brainstorm to generate, evaluate, and prioritize feature ideas and hypotheses. Supports two main modes: standard interactive brainstorm and CJM Hypotheses mode for funnel-driven hypothesis generation. This is an interactive, dialogue-driven skill — ideas are discussed live, iterated on, and only saved when the user is ready.

## Integration prerequisite

Before gathering data, read and follow the integration fallback chain in `references/integration-strategy.md`. For this skill, the typical external products needed are:

- **Confluence** — for reading concepts/PRDs, research results, and optionally saving brainstorm output
- **Google Drive** — for reading internal documents and optionally saving brainstorm output
- **Figma** — for reading existing designs, UX flows, and prototypes of current functionality
- **Web** — always available via WebSearch for benchmarks, competitor analysis, research
- **ChatGPT / Gemini** — for Deep Research via browser when deeper analysis is needed
- **Product Analysis skill** — for data-backed hypothesis generation and metric analysis (invoked when brainstorm needs quantitative evidence)
- **Knowledge Library** — for searching curated sources (benchmarks, UX best practices) that enrich hypotheses with pre-vetted evidence
- **CJM Research skill** — provides CJM anomaly data and enrichment context for CJM Hypotheses mode

For each product: check for MCP connector → search MCP registry → fall back to browser.

Before gathering any data, also read and comply with `references/data-policy.md`. Confidential data (internal analytics, research materials) must NOT be passed to external LLMs or third parties.

## Local context prerequisite

**Before starting, follow `references/local-context-protocol.md` (Step 0).** Read `local-context.md`, select the active product, and load all product-specific context. If the file doesn't exist — redirect to Plugin Configurator for initial setup.

Key context used by this skill:
- `product.name`, `product.description` — for product context in brainstorm
- `product.key_metrics`, `product.current_okrs` — for aligning hypotheses with goals
- `product.competitors` — for competitor benchmarks
- `product.confluence_space` — default publishing destination
- `user.language` — for output language
- CJM Configuration section — funnel stages, baselines, thresholds (for CJM Hypotheses mode)
- Knowledge Library section — search modes, available sources count

## Step T — Template Resolution (when saving brainstorm output)

The brainstorm itself is interactive and dialogue-driven — no template is needed for in-chat iteration. Step T runs only when the user asks to **save** or **publish** the result as a structured artifact.

At save time, determine the artifact type the user wants:
- "Save as hypothesis list / backlog" → `artifact_type: research`, `subtype: hypothesis-list`
- "Turn top hypothesis into a concept" → `artifact_type: concept` (delegate to `write-concept` which runs its own Step T)
- "Turn top hypothesis into requirements" → `artifact_type: requirements` (delegate to `requirements-creator`)
- "Keep in chat only" → skip Step T

When staying in this skill and producing a structured document:

Follow `references/template-protocol.md`.

Declare:
- `artifact_type: research` (default for brainstorm output)
- `subtype: hypothesis-list` (or `cjm-hypotheses` for CJM Hypotheses mode)
- `product_id: {from local-context.md active product}`
- `language: {from local-context.md}`

Run Steps T-1 → T-5. Append `<!-- template: {template_id} version: {version} -->` at the end.

If the user says "do not use a template" → skip Step T and use the skill's internal structure.

## Workflow

### Step 1 — Determine context and brainstorm source

**Product and feature context — clarify via AskUserQuestion if not clear from context:**

- **Which product or part of the product ecosystem** are we brainstorming for? (if not explicitly stated — ask before proceeding)
- **New or existing functionality?** — Are we generating ideas for completely new functionality, or are we brainstorming improvements/changes to existing functionality? (if not clear — ask explicitly)

**Figma designs check — if working with existing product or existing functionality:**

If the product or feature already exists, ask via AskUserQuestion:

> "Are there current designs / mockups / prototypes of this functionality in Figma?"

- **If the user provides a link** — open it via Figma MCP (`get_design_context`, `get_screenshot`) or browser fallback, read and extract: current UX flows, screens, key UI patterns. Use this as context for brainstorming — ideas should build on or consciously change the current state
- **If the user believes designs should exist but cannot provide a link** — offer to search:
  > "I can search for relevant mockups in Figma from your account. Would you like me to search?"
  - If agreed — search via Figma MCP or browser (`https://www.figma.com`):
    - Try to understand the structure of the design system: look for sections like "Актуальний дизайн", "Current design", "Production", "Live", "Ready for dev", "Поточний стан"
    - Show the user the found files/frames and ask them to confirm which are relevant and up-to-date
  - If Figma MCP is unavailable — follow `references/integration-strategy.md` fallback chain
- **If no designs exist** — note this and proceed without design context
- **If relevant designs are confirmed** — use them throughout the brainstorm: reference the current UX state when generating ideas, describe how hypotheses change or build on the current design. Include links to relevant frames in the saved output

Identify which starting situation applies:

**Situation A — User provides an existing concept:**
- Read and analyze the provided document (Confluence link, Google Drive link, uploaded file, or text in dialogue)
- Confirm understanding with the user
- Proceed to Step 2

**Situation B — Concept was created via Write Concept / PRD skill:**
- Search Confluence for the most recent PRD related to the topic using `searchConfluenceUsingCql`
- Confirm with the user that the found document is correct
- Proceed to Step 2

**Situation C — No concept exists yet:**
- Proactively gather all available context from the user: what is the problem, which product, what goals, which user segment
- Propose conducting research first via the **Product Research** skill to build an evidence base
- After research — propose creating a concept via the **Write Concept / PRD** skill
- If the user wants to skip these steps — work with whatever context is available

**Situation D — Invoked by CJM Research (CJM Hypotheses mode):**
- Context was passed from `cjm-research`: anomaly list with severity, enrichment data from Knowledge Library and product-research
- Skip all manual context gathering — use passed data
- Proceed directly to **Step 3C — CJM Hypothesis Generation**

**Regardless of situation, additionally clarify via AskUserQuestion:**
- Which **product metrics** are we targeting? (conversion, retention, revenue, engagement, etc.)
- Are there **constraints**? (technical, resource, time)
- How many ideas to generate?
- Use the **MVP incremental approach**? (start with MVP, then expand with phases)

### Step 2 — Analyze provided materials

Deeply analyze all gathered context: concept/PRD, research, metrics, strategy, constraints. Build an internal understanding of: the core problem, goals, current product state, and opportunities for improvement.

Proactively search for additional context if gaps are detected:
- Search Confluence and Google Drive for related internal documents
- Run WebSearch for market benchmarks, competitor features, industry best practices
- If Deep Research through ChatGPT/Gemini was approved — use it for deeper analysis (only with publicly available information per data-policy.md)
- **If product metrics or data analysis is needed** — invoke the **Product Analysis** skill: pass the product context, target metrics, and time period. Product Analysis will return key trends, anomalies, and data-backed hypotheses that can directly feed into the brainstorm. This is especially valuable for generating "Growth Hypotheses" and improving ICE Confidence scores with real data

After analysis, ask the user via AskUserQuestion:

1. **Do you already have specific ideas** you want to implement within this context?
2. **Do you need help brainstorming** new ideas and hypotheses?

Both options can be selected — evaluate existing ideas AND generate new ones.

### Step 3A — Evaluate user's existing ideas (if provided)

If the user has ideas and wants evaluation:

- Ask the user to describe each idea
- Ask clarifying questions if needed to fully understand the idea
- For each idea, conduct analysis and present:

**For each idea provide:**

| Element | Description |
|---------|------------|
| **Rationale** | Why it could work — benchmarks, research, market examples |
| **Risks** | What could go wrong, potential negative effects |
| **Impact on metrics** | Which metrics will change and in which direction |
| **ICE Score** | Impact (1-10) × Confidence (1-10) × Ease (1-10) = Score |
| **Validation method** | Recommended safest way to validate (see `references/validation-methods.md`) |
| **Verdict** | Proceed / Postpone / Needs additional research |

See `references/ice-framework.md` for detailed ICE scoring guidelines.

After presenting the evaluation — propose discussing specific ideas in more depth if the user wants to explore alternatives or refine the approach.

### Step 3B — Generate new ideas and hypotheses (if requested)

If the user wants brainstorming of new ideas:

- Conduct deep analysis of all available materials
- Run WebSearch for: best practices, competitor benchmarks, industry research, trends, case studies
- Focus on **maximum result with minimum effort** — prioritize high-impact, low-effort ideas
- Generate the requested number of ideas

**Format each idea as a hypothesis:**

```
Name: [short name]

Problem: [what problem this solves]
Solution: [what we propose to do]
Expected outcome: [what changes for users and business]
Target metric: [which metric is impacted and by how much]
Validation method: [A/B test / user interviews / feature flag / fake door / etc.]

ICE Score: Impact [X] × Confidence [X] × Ease [X] = [Score]

Benchmarks: [links to research, competitor cases, market data]
Risks: [what could go wrong]
```

> **Note:** Use the user's preferred language (`user.language`) for all field labels and content in the output document.

**Grouping ideas — two layers:**

**Layer 1 — By category:**
- Quick Wins — high impact, low effort, can ship fast
- UX Improvements — user experience enhancements
- New Functionality — net-new features
- Growth Hypotheses — experiments targeting growth metrics
- Tech Debt / Infrastructure — technical improvements enabling future features

**Layer 2 — By phase (if MVP approach confirmed):**
- MVP (Phase 1) — minimal viable set to validate the core hypothesis
- Phase 2 — enhancements after MVP validation
- Phase 3 — advanced features and scaling
- Future — long-term ideas, parking lot

Present the **ICE summary table** sorted by score descending — giving the user a clear priority view.

### Step 3C — CJM Hypothesis Generation (CJM mode)

This step runs when invoked by `cjm-research` or when the user explicitly requests CJM-based brainstorming.

**Input required:**
- Anomaly list from `product-analysis` (CJM mode): stage, metric, baseline, actual, deviation, severity
- World enrichment from `knowledge-library` / `product-research`: benchmarks, best practices, competitor approaches
- Internal enrichment: Confluence experiment results, user feedback, previous research

**3C-1. Generate hypotheses from anomalies:**

For each anomaly (prioritize by severity: Critical first, then Warning):

```
Name: [short descriptive name]

Data Trigger: [anomaly details — stage, metric, deviation from baseline]
Feedback Match: [correlated user feedback, support tickets, NPS verbatims — from internal enrichment]
Heuristic Match: [matching UX best practice or benchmark — from Knowledge Library with trust score]

Solution: [proposed change to address the anomaly]
Expected Impact: [estimated conversion lift % for the affected stage]
Target Metric: [stage conversion rate, expected change direction and magnitude]
Validation Method: [A/B test / feature flag / user interviews / analytics deep-dive]

ICE Score: Impact [X] × Confidence [X] × Ease [X] = [Score]

Funnel Stage Impact: current [X]% → projected [Y]% (+Z%)

Benchmarks: [supporting evidence with trust scores — from Knowledge Library and web]
Risks: [what could go wrong, negative side effects]
```

> Use the user's preferred language (`user.language`) for all field labels and content.

**3C-2. ICE scoring with CJM-specific weighting:**

Enhanced ICE scoring for CJM hypotheses:

**Impact** — weighted by funnel stage position (per `references/cjm-protocol.md`):
| Stage position | Multiplier | Rationale |
|---------------|-----------|-----------|
| Stage 1 (entry) | ×1.5 | Improvements at entry affect all downstream stages |
| Stage 2 | ×1.3 | High leverage — feeds middle funnel |
| Stage 3 | ×1.1 | Important but narrower audience |
| Stage 4+ | ×1.0 | Baseline — affects only late-stage users |

**Confidence** — boosted by evidence quality:
- Baymard/academic evidence supports hypothesis → +1–2 points
- Internal A/B test confirmed similar approach → +2–3 points
- Only blog/article evidence → +0 (no boost)
- Contradicting internal evidence → -2–3 points

**Ease** — based on technical complexity, team capacity, dependencies

**3C-3. Funnel impact calculation:**

For each hypothesis, calculate the per-stage conversion impact:
```
new_stage_conversion = current_stage_conversion × (1 + expected_lift_percent / 100)
```

Calculate end-to-end funnel impact if all hypotheses in a stage are implemented:
```
stage_combined_lift = 1 - product(1 - lift_i for each hypothesis_i in stage)
new_stage_conversion = current × (1 + stage_combined_lift)
```

**3C-4. Categorize hypotheses:**

| Category | Criteria | Typical timeline |
|----------|----------|-----------------|
| **Low-hanging fruit** | Ease ≥ 7, moderate Impact, can be A/B tested quickly | 1–2 sprints |
| **Structural changes** | High Impact, Ease < 5, requires significant development | 1–2 quarters |
| **Business logic changes** | Requires stakeholder alignment, pricing/policy changes | Cross-functional initiative |

**3C-5. Present results:**

Show hypotheses grouped by category, sorted by ICE score within each group.

Present ICE summary table:
| # | Name | Stage | Trigger | ICE | Stage Impact | Category |
|---|------|-------|---------|-----|-------------|----------|

**3C-6. Return results to cjm-research:**

When returning to `cjm-research`, include:
- Full hypothesis list with all fields
- ICE scores with stage multipliers applied
- Per-hypothesis funnel stage impact
- Category assignments
- Evidence references (Knowledge Library sources, web sources)

### Step 4 — Interactive discussion

This skill is a live dialogue, not a one-shot generation. Actively engage the user:

- Propose discussing specific ideas in more detail to find better solutions
- If the user wants to develop an idea — help by asking the right questions, suggesting alternatives, playing devil's advocate
- Iterate: add new ideas, remove weak ones, regroup, re-score
- Can return to Step 3B or 3C to generate more ideas if needed
- Help the user make trade-off decisions between competing ideas

### Step 5 — Finalize and optionally save results

When the user confirms the final list of ideas/hypotheses, ask via AskUserQuestion:

- **Do you want to save the brainstorm results?**
  - If no — end the skill, results stay in the dialogue
  - If yes — ask where to save:
    - **Confluence page**
    - **Google Drive document**
    - **Other** — user specifies (e.g., Notion, Word file, etc.)

**When saving to Confluence:**
- Ask for space and parent page
- Title: `[Brainstorm] Concept name / topic`
- Structure:
  - Table of Contents (levels 1-6)
  - Dividers between sections
  - **Context**: links to concept/PRD/research that informed the brainstorm
  - **User's ideas** (with evaluations if conducted)
  - **Generated ideas/hypotheses** (full description, ICE, benchmarks, risks)
  - **ICE Summary Table** — sorted by score, with validation methods
  - **Phase Roadmap** (if MVP approach) — which ideas go into which phase
  - **Recommended next steps**
  - **Sources** section with links, marking each source type (Confluence, Google Drive, Web, ChatGPT Deep Research, Gemini Deep Research)
- Formatting: headings H1/H2/H3, bold key theses, tables for structured data
- Publish via Confluence MCP. If unavailable — follow integration fallback chain

**When saving to Google Drive:**
- Ask for folder or link to the target location
- Follow integration fallback chain: Google Drive MCP → registry → browser
- Same structure and formatting adapted for Google Docs
- Follow `references/data-policy.md`

**When saving to other destination:**
- Follow integration fallback chain for the specified tool
- Adapt format to platform capabilities

### Step 6 — Summary report and feedback

After saving (or if the user decided not to save), provide a structured report of what was done:

**Report format:**
- **What was done:** brief description of the brainstorm conducted (topic, number of ideas evaluated/generated, approach used)
- **Artifacts created:** links to all created documents (Confluence page, Google Drive doc, etc.) — if saved
- **Results:**
  - Number of user's ideas evaluated (if any)
  - Number of new hypotheses generated (if any)
  - Top 3 ideas by ICE score with brief descriptions
- **ICE Summary:** quick reference table of all ideas sorted by score
- **Sources used:** list of source types used (Concept/PRD, Confluence, Google Drive, Web, Figma, ChatGPT Deep Research, Gemini Deep Research)

**After presenting the report, proactively ask for feedback:**

> "Are you satisfied with the brainstorm results? Would you like to refine anything, add more ideas, or revise the scores?"

- If the user requests changes — return to Step 4 (Interactive discussion) for further iteration
- If the user confirms — proceed to the next step

**Self-improvement check** (after corrections are applied and confirmed):

If the user requested corrections during review, follow the full protocol in `references/self-improvement.md`. In short:
1. Analyze the root cause of the error — is this a pattern or a one-off?
2. If it's a pattern — propose a specific improvement to the skill's conditions
3. If the user agrees — update the SKILL.md, re-package the plugin, and provide the updated file

### Step 7 — Transition to next stage

Always propose:

- Proceed to creating detailed requirements for selected ideas via the **Feature and Hypothesis Requirements Creator** skill
- Recommend which specific ideas from the final list to take into work first — based on ICE score ranking
- If no concept exists yet — suggest creating one via **Write Concept / PRD** before moving to requirements
- If CJM Hypotheses mode was used → also offer: "Run full **CJM Research** to verify these hypotheses, assess risks, and build a prioritized backlog"

## Quality standards

- Always back ideas with evidence: benchmarks, research, competitor examples
- Clearly distinguish validated insights from assumptions
- For each hypothesis — always include a validation method and risk assessment
- Use Ukrainian or English based on user's language preference
- Be result-oriented: prioritize approaches that deliver maximum impact with minimum effort
- Proactively suggest discussing ideas to help the user find better solutions

## Additional Resources

- **`references/local-context-protocol.md`** — Step 0: how to read and use local-context.md (mandatory before any skill execution)
- **`references/ice-framework.md`** — detailed ICE scoring guidelines and examples
- **`references/validation-methods.md`** — validation methods ranked by cost and reliability
- **`references/integration-strategy.md`** — MCP → Registry → Browser fallback chain
- **`references/data-policy.md`** — data confidentiality policy
- **`references/self-improvement.md`** — self-improvement protocol: how to learn from user corrections and improve skill algorithms
- **`references/cjm-protocol.md`** — CJM anomaly severity, funnel impact formulas, stage position multipliers
- **`references/funnel-templates.md`** — standard funnel stage templates by product type
