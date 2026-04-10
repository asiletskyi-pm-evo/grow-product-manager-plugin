---
name: brainstorm-features
version: 0.5.0
description: Help Product Manager brainstorm features and hypotheses. Use when the user asks to "brainstorm features", "generate hypotheses", "find growth opportunities", "CJM hypotheses", or needs ICE scoring, benchmarks, funnel impact modeling, and validation methods.
---

# Brainstorm Features and Hypotheses

Help Product Manager conduct a structured brainstorm to generate, evaluate, and prioritize feature ideas and hypotheses. Supports two modes: general brainstorming (interactive dialogue-driven) and CJM Hypotheses (data-driven hypothesis generation from CJM anomalies with funnel impact modeling). Ideas are discussed live, iterated on, and only saved when the user is ready.

## Integration prerequisite

Before gathering data, read and follow the integration fallback chain in `references/integration-strategy.md`. For this skill, the typical external products needed are:

- **Confluence** — for reading concepts/PRDs, research results, and optionally saving brainstorm output
- **Google Drive** — for reading internal documents and optionally saving brainstorm output
- **Figma** — for reading existing designs, UX flows, and prototypes of current functionality
- **Web** — always available via WebSearch for benchmarks, competitor analysis, research
- **ChatGPT / Gemini** — for Deep Research via browser when deeper analysis is needed
- **Product Analysis skill** — for data-backed hypothesis generation and metric analysis (invoked when brainstorm needs quantitative evidence)
- **Knowledge Library** — for curated UX/product knowledge sources with trust scoring (used in CJM Hypotheses mode)

For each product: check for MCP connector → search MCP registry → fall back to browser.

Before gathering any data, also read and comply with `references/data-policy.md`. Confidential data (internal analytics, research materials) must NOT be passed to external LLMs or third parties.

## Local context prerequisite

**Before starting, follow `references/local-context-protocol.md` (Step 0).** Read `local-context.md`, select the active product, and load all product-specific context. If the file doesn't exist — redirect to Plugin Configurator for initial setup.

Key context used by this skill:
- `product.name`, `product.description` — for product context in brainstorm
- `product.key_metrics`, `product.current_okrs` — for aligning hypotheses with goals
- `product.competitors` — for competitor benchmarks
- `product.confluence_space` — default publishing destination
- `product.cjm_configuration` — for CJM Hypotheses mode: funnel stages, baseline conversions, anomaly thresholds
- `user.language` — for output language

## Workflow

### Step 1 — Determine context, mode, and brainstorm source

**1a. Mode selection — ask via AskUserQuestion:**

> "Which brainstorming mode should we use?"

- **General Brainstorm** — interactive brainstorming of features and hypotheses. Dialogue-driven, iterative. Good for exploring ideas, evaluating concepts, generating growth hypotheses
- **CJM Hypotheses** — data-driven hypothesis generation from CJM funnel anomalies. Structured, evidence-based. Uses anomaly data + external/internal enrichment to generate hypotheses with funnel impact modeling. Typically invoked by `cjm-research` orchestrator, but can also be used standalone

If invoked by `cjm-research` → automatically select CJM Hypotheses mode. Skip to **Step 2-CJM**.

**1b. Product and feature context — clarify via AskUserQuestion if not clear from context:**

- **Which product or part of the product ecosystem** are we brainstorming for? (if not explicitly stated — ask before proceeding)
- **New or existing functionality?** — Are we generating ideas for completely new functionality, or are we brainstorming improvements/changes to existing functionality? (if not clear — ask explicitly)

**1c. Figma designs check — if working with existing product or existing functionality:**

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

**1d. Identify starting situation (General Brainstorm mode only):**

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

**1e. Additional clarification (General Brainstorm mode) — ask via AskUserQuestion:**
- Which **product metrics** are we targeting? (conversion, retention, revenue, engagement, etc.)
- Are there **constraints**? (technical, resource, time)
- How many ideas to generate?
- Use the **MVP incremental approach**? (start with MVP, then expand with phases)

### Step 2 — Analyze provided materials (General Brainstorm mode)

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

### Step 2-CJM — Process CJM input data (CJM Hypotheses mode)

**This step replaces Step 2 when in CJM Hypotheses mode.**

**2-CJM-a. Receive and validate input data:**

When invoked by `cjm-research` orchestrator, receive:
- Anomaly list with severity classification and funnel stage mapping
- External enrichment: knowledge library insights, benchmark data, UX best practices (with trust scores)
- Internal enrichment: experiment history, user feedback patterns, previous CJM findings
- Funnel baseline conversions per stage (from CJM config)
- Product context: OKRs, key metrics, constraints

When invoked standalone:
- Ask user for data source: product-analysis CJM output, uploaded file, or manual input
- If no CJM data available — suggest running `product-analysis` in CJM Funnel Analysis mode first
- Validate that `cjm_configuration` exists in local-context.md (required for funnel impact calculations)

**2-CJM-b. Analyze enrichment data quality:**
- Count anomalies by severity: critical / warning / info
- Count enrichment matches: how many anomalies have external evidence, internal evidence, user feedback
- Flag anomalies with no enrichment — these will have lower confidence scores
- Present overview to user:
  > "Received [N] anomalies ([X] critical, [Y] warning, [Z] info) across [M] funnel stages. External evidence available for [P]%, internal evidence for [Q]%."

### Step 3A — Evaluate user's existing ideas (General Brainstorm mode, if provided)

If the user has ideas and wants evaluation:

- Ask the user to describe each idea
- Ask clarifying questions if needed to fully understand the idea
- For each idea, conduct analysis and present:

**For each idea provide:**

| Element | Description |
|---------|------------| || **Rationale** | Why it could work — benchmarks, research, market examples |
| **Risks** | What could go wrong, potential negative effects |
| **Impact on metrics** | Which metrics will change and in which direction |
| **ICE Score** | Impact (1-10) × Confidence (1-10) × Ease (1-10) = Score |
| **Validation method** | Recommended safest way to validate (see `references/validation-methods.md`) |
| **Verdict** | Proceed / Postpone / Needs additional research |

See `references/ice-framework.md` for detailed ICE scoring guidelines.

After presenting the evaluation — propose discussing specific ideas in more depth if the user wants to explore alternatives or refine the approach.

### Step 3B — Generate new ideas and hypotheses (General Brainstorm mode, if requested)

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

### Step 3-CJM — Generate CJM hypotheses (CJM Hypotheses mode)

**This step replaces Steps 3A/3B when in CJM Hypotheses mode.**

For each anomaly (starting with critical severity, then warning):

**3-CJM-a. Build hypothesis card:**

```
Name: [short descriptive name]

Data Trigger: [the anomaly — metric, deviation from baseline, funnel stage, severity]
Feedback Match: [correlated user feedback, support tickets, NPS themes — from internal enrichment]
Heuristic Match: [relevant UX best practice or benchmark — from external enrichment, with source and trust score]
Solution: [proposed change — specific, actionable]
Expected Impact: [estimated conversion lift % at target stage, with reasoning]

ICE Score:
  Impact: [1-10, weighted by funnel position — see CJM ICE rules below]
  Confidence: [1-10, with evidence boost — see CJM ICE rules below]
  Ease: [1-10, based on technical complexity assessment]
  Total: [Impact × Confidence × Ease]

Funnel Impact:
  Target stage: [stage name]
  Current conversion: [X%]
  Expected lift: [+Y%]
  New stage conversion: [Z%]
  End-to-end impact: [calculated by cjm-research in Step 9]

Category: [Low-hanging fruit / Structural change / Business logic change]

Evidence:
  External sources: [list with trust scores]
  Internal sources: [list with links]
  User feedback: [summary of matching feedback]
```

> **Note:** Use the user's preferred language (`user.language`) for all field labels and content.

**3-CJM-b. CJM-specific ICE scoring rules:**

**Impact weighting by funnel position:**
- Funnel stages are weighted by their position: earlier stages have a higher impact multiplier because improvements cascade through the entire funnel
- Multiplier formula: `impact_multiplier = 1.0 + (0.2 × (total_stages - stage_position))` where stage_position is 1-based
- Example for 4-stage funnel: Stage 1 = 1.6×, Stage 2 = 1.4×, Stage 3 = 1.2×, Stage 4 = 1.0×
- Apply multiplier: `adjusted_impact = base_impact × impact_multiplier` (cap at 10)

**Confidence boost from evidence:**
- Base confidence: assessed from data strength (anomaly severity, trend consistency)
- Baymard evidence: +2 points (Baymard is gold-standard for e-commerce UX)
- Industry benchmark alignment: +1 point (if expected lift matches benchmark ranges)
- Internal experiment support: +2 points (if previous experiment showed similar direction)
- Internal experiment contradiction: -2 points (if previous experiment failed with similar approach)
- User feedback correlation: +1 point (if user complaints match the anomaly)
- Cap confidence at 10

**Ease assessment:**
- Evaluate based on: scope of code changes, number of teams involved, design effort, testing complexity
- If the hypothesis touches business logic (pricing, policies): automatic Ease ≤ 5
- If the hypothesis requires backend + frontend + design: automatic Ease ≤ 6

**3-CJM-c. Categorization rules:**

- **Low-hanging fruit**: Ease ≥ 7, Impact moderate (4-7). Quick wins that can be implemented within 1-2 sprints. Typically UI/UX tweaks, copy changes, layout adjustments
- **Structural changes**: Impact ≥ 7, Ease ≤ 5. Significant development effort required: new flows, major UX overhauls, architectural changes. Typically requires 1+ months
- **Business logic changes**: Solution involves pricing, payment rules, policies, promotions, or stakeholder-dependent decisions. Requires alignment with business stakeholders, legal review, or finance approval

**3-CJM-d. Group anomalies into hypothesis clusters:**

- If multiple anomalies at the same stage point to the same root cause → create a single combined hypothesis
- If anomalies at adjacent stages are correlated (cascading effect) → note the relationship, create linked hypotheses
- Present hypotheses grouped by funnel stage, then by category within each stage

**3-CJM-e. Present results:**

1. **Hypothesis table** — all hypotheses sorted by ICE score (descending):

| # | Name | Stage | Trigger | Solution | ICE | Lift % | Category |
|---|------|-------|---------|----------|-----|--------|----------|
| 1 | ... | ... | ... | ... | ... | ... | ... |

2. **Funnel impact summary** — per-stage aggregation:

| Stage | Current Conv. | Potential Lift | New Conv. | # Hypotheses |
|-------|--------------|----------------|-----------|-------------|
| ... | ... | ... | ... | ... |

3. **Category distribution:**
- Low-hanging fruit: [N] hypotheses, combined potential: [X%] funnel improvement
- Structural changes: [N] hypotheses, combined potential: [X%] funnel improvement
- Business logic: [N] hypotheses, combined potential: [X%] funnel improvement

### Step 4 — Interactive discussion

This skill is a live dialogue, not a one-shot generation. Actively engage the user:

**In General Brainstorm mode:**
- Propose discussing specific ideas in more detail to find better solutions
- If the user wants to develop an idea — help by asking the right questions, suggesting alternatives, playing devil's advocate
- Iterate: add new ideas, remove weak ones, regroup, re-score
- Can return to Step 3B to generate more ideas if needed
- Help the user make trade-off decisions between competing ideas

**In CJM Hypotheses mode:**
- Walk through hypotheses with the user, discuss each one
- Challenge assumptions: "Is this lift realistic given your product context?"
- Help reprioritize based on user's knowledge of technical constraints and team capacity
- Allow merging, splitting, or removing hypotheses
- If user provides additional context — recalculate ICE scores and funnel impact
- Can generate additional hypotheses for specific stages if the user identifies gaps

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
- Title format:
  - General Brainstorm: `[Brainstorm] Concept name / topic`
  - CJM Hypotheses: `[CJM Hypotheses] Product — Date`
- Structure:
  - Table of Contents (levels 1-6)
  - Dividers between sections
  - **Context**: links to concept/PRD/research that informed the brainstorm (General) or CJM research context (CJM)
  - **User's ideas** (with evaluations if conducted) — General mode only
  - **Generated ideas/hypotheses** (full description, ICE, benchmarks, risks)
  - **ICE Summary Table** — sorted by score, with validation methods
  - **Phase Roadmap** (if MVP approach) — which ideas go into which phase — General mode only
  - **Funnel Impact Model** — per-stage and end-to-end impact summary — CJM mode only
  - **Prioritization Matrix** — by category (low-hanging / structural / business logic) — CJM mode only
  - **Recommended next steps**
  - **Sources** section with links, marking each source type (Confluence, Google Drive, Web, Knowledge Library, ChatGPT Deep Research, Gemini Deep Research)
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
- **What was done:** brief description of the brainstorm conducted (topic/mode, number of ideas evaluated/generated, approach used)
- **Artifacts created:** links to all created documents (Confluence page, Google Drive doc, etc.) — if saved
- **Results:**
  - Number of user's ideas evaluated (if any) — General mode
  - Number of hypotheses generated
  - Top 3 ideas by ICE score with brief descriptions
  - Funnel impact summary (total potential lift) — CJM mode
- **ICE Summary:** quick reference table of all ideas sorted by score
- **Sources used:** list of source types used (Concept/PRD, Confluence, Google Drive, Web, Knowledge Library, Figma, ChatGPT Deep Research, Gemini Deep Research)

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

**In General Brainstorm mode:**

Always propose:
- Proceed to creating detailed requirements for selected ideas via the **Feature and Hypothesis Requirements Creator** skill
- Recommend which specific ideas from the final list to take into work first — based on ICE score ranking
- If no concept exists yet — suggest creating one via **Write Concept / PRD** before moving to requirements
- Create a **Presentation** with brainstorm results via **Presentation Creator** — especially useful for presenting hypotheses and prioritization to stakeholders

**In CJM Hypotheses mode:**

**If invoked by cjm-research orchestrator:**
- Return structured results to the orchestrator for Steps 8-12 (impact calculation, verification, risk assessment, report)
- Return payload includes: hypothesis list with ICE scores, per-stage lift estimates, categorization, evidence links

**If invoked standalone:**
- Propose the same options as General mode, plus:
- → Run **CJM Research** in `full` mode to get independent verification, risk assessment, and end-to-end impact calculation
- → **Product Analysis** — if additional data analysis is needed to support hypotheses

**Structured return payload (when invoked by another skill):**

```
{
  hypotheses: [
    {
      name: string,
      data_trigger: { stage, metric, deviation, severity },
      feedback_match: string | null,
      heuristic_match: { source, insight, trust_score } | null,
      solution: string,
      expected_impact: { stage, current_conversion, expected_lift, new_conversion },
      ice: { impact, confidence, ease, total },
      category: "low-hanging" | "structural" | "business-logic",
      evidence: { external: [], internal: [], feedback: [] }
    }
  ],
  summary: {
    total_hypotheses: number,
    by_category: { low_hanging: number, structural: number, business_logic: number },
    by_stage: { [stage_name]: number },
    top_3_by_ice: [hypothesis_names]
  }
}
```

## Quality standards

- Always back ideas with evidence: benchmarks, research, competitor examples
- Clearly distinguish validated insights from assumptions
- For each hypothesis — always include a validation method and risk assessment
- **CJM mode**: every hypothesis must trace back to a specific anomaly (Data Trigger) and include at least one evidence source
- **CJM mode**: funnel impact calculations must use baseline conversions from CJM config, not estimates
- **CJM mode**: ICE scoring must apply funnel position weighting and evidence boost consistently
- Use Ukrainian or English based on user's language preference
- Be result-oriented: prioritize approaches that deliver maximum impact with minimum effort
- Proactively suggest discussing ideas to help the user find better solutions

## Additional Resources

- **`references/local-context-protocol.md`** — Step 0: how to read and use local-context.md (mandatory before any skill execution)
- **`references/ice-framework.md`** — detailed ICE scoring guidelines and examples
- **`references/validation-methods.md`** — validation methods ranked by cost and reliability
- **`references/cjm-protocol.md`** — anomaly severity levels, health score formula, funnel impact calculations (CJM mode)
- **`references/funnel-templates.md`** — funnel stage templates by product type (CJM mode)
- **`references/integration-strategy.md`** — MCP → Registry → Browser fallback chain
- **`references/data-policy.md`** — data confidentiality policy
- **`references/self-improvement.md`** — self-improvement protocol: how to learn from user corrections and improve skill algorithms
