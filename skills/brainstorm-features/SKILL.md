---
name: brainstorm-features
version: 0.10.1
description: Help Product Manager brainstorm features, hypotheses, and CJM Hypotheses. Use when the user asks to "brainstorm features", "generate hypotheses", "find growth opportunities", needs CJM funnel-driven hypothesis generation, or requires ICE scoring with funnel impact analysis. Also hosts Debate mode — "run a debate", "role debate", "red team this idea", "have agents argue / discuss from different roles", "stress-test via debate". Українською — "брейншторм фіч", "згенерувати гіпотези", "знайти точки росту", "гіпотези для CJM-воронки", "ICE-оцінка гіпотез", "проведи дебати", "нехай агенти подискутують", "розглянь з різних ролей", "red team цю ідею", "круглий стіл ролей". This is the ideation engine — for the full CJM research pipeline (anomaly detection → enrichment → hypotheses) use cjm-research, which delegates here. Do NOT use for meeting transcript discussions (meeting-processor) or for recording an already made decision (decision-log).
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
    - Try to understand the structure of the design system: look for sections like "Current design", "Production", "Live", "Ready for dev", "Latest state"
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
| **PRO / ROI** | Money-based score (`references/roi-frameworks.md`): cost-in-hours × rate → effect → **% annual return** + the task-as-credit verdict (return vs cost of capital) + Confidence % |
| **Validation method** | Recommended safest way to validate (see `references/validation-methods.md`) |
| **Verdict** | Proceed / Postpone / Needs additional research |

> **Compute BOTH scores by default.** For every idea, produce **both** the **ICE** score and the **PRO/ROI** score (`references/roi-frameworks.md`). Report only one **only if the user explicitly asks** ("just ICE" / "only ROI"). ICE ranks by impact/confidence/ease; PRO ranks by money (annual % return, task-as-credit). Where a $ effect is unknowable, say so and fall back to ICE for that idea (see the overload methods below).

See `references/ice-framework.md` for ICE scoring and `references/roi-frameworks.md` for PRO/ROAIP economics.

**Overload / no-data prioritization methods** (offer when the backlog is large or data is missing):
- **"Choose one"** — when the backlog is overloaded, force a single pick: which one idea, if you could only do one, moves the goal most? Cuts analysis paralysis.
- **"Olympic system"** — when ideas have no comparable data, rank by pairwise elimination (bracket): compare two at a time, the winner advances, until an ordering emerges — a relative ranking without absolute scores.

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
PRO / ROI: cost [hours × rate] → effect [$/yr] → [% annual return], Confidence [%] — verdict vs cost of capital

Benchmarks: [links to research, competitor cases, market data]
Risks: [what could go wrong]
```

> Both **ICE** and **PRO/ROI** are filled by default (see the scoring note in Step 3A); drop one only on explicit request.

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

This step runs when invoked by `cjm-research` (Situation D) or when the user explicitly requests CJM-based brainstorming.

**Input required:**
- Anomaly list from `product-analysis` (CJM mode): stage, metric, baseline, actual, deviation, severity
- World enrichment from `knowledge-library` / `product-research`: benchmarks, best practices, competitor approaches
- Internal enrichment: Confluence experiment results, user feedback, previous research

The full mode workflow lives in `references/cjm-hypotheses-mode.md` (skill-local) — read it when this step activates. It covers: **3C-1** the hypothesis format generated from anomalies (Data Trigger / Feedback Match / Heuristic Match), **3C-2** ICE scoring with CJM stage-position multipliers and evidence-quality Confidence boosts, **3C-3** per-stage and combined funnel-impact formulas, **3C-4** categorization (low-hanging fruit / structural / business-logic), **3C-5** result presentation, and **3C-6** the return contract to `cjm-research` (full hypothesis list, weighted ICE, per-stage impact, categories, evidence references).

### Step 3D — Debate mode (role-based adversarial discussion)

Executes `references/debate-protocol.md` — the shared engine: D0 applicability check → D1 setup (question, roles, evidence pack) → parallel debate rounds (one `grow-product-manager:debater` agent per role, fallback chain per the protocol) → facilitator synthesis → output & save. Activates in three ways:

1. **Explicit request** — the user asks for a debate / role discussion / red-team («проведи дебати», "red team this idea", «круглий стіл ролей», "stress-test via debate").
2. **Offered after 3A–3C** — when top hypotheses are contested, touch ≥ 2 interest groups, and an evidence base exists (Step 4 proposes the stress-test).
3. **Called from another skill's Debate hook** (`product-research`, `cjm-research`, `write-concept`, `decision-log`) — arrives with a ready evidence pack: skip gathering, go straight to D1 role selection.

Execution in this skill's terms:

- **Evidence pack** = what is already on the table: Step 2 analysis, `product-analysis` results, Knowledge Library sources, CJM anomalies (Situation D). Facts E1…En only from material that passed integrity checks; everything else enters as a marked assumption A1…An.
- **Debate question** = one contested hypothesis or an X-vs-Y choice between two hypotheses — never the whole backlog at once.
- **Roles** via AskUserQuestion from the protocol's presets; the Skeptic / Risk-officer is always in.
- **Results return to the standard flow:** the verdict's ICE Confidence corrections (consensus +1…+2, unresolved skeptic objection −1…−2) update the scores in the Step 3A/3B/3C tables; new risks append to the hypotheses' Risks fields; the «Debates» section embeds in the saved artifact (Step 5) and the debate is saved to the vault (Step 9).

Cost: default 4 roles × 2 rounds = 8 subagent calls, hard cap 12. Without the Agent tool — inline simulation with the mandatory "inline simulation: role independence reduced" marker (protocol → Guardrails).

### Step 4 — Interactive discussion

This skill is a live dialogue, not a one-shot generation. Actively engage the user:

- Propose discussing specific ideas in more detail to find better solutions
- If the user wants to develop an idea — help by asking the right questions, suggesting alternatives, playing devil's advocate
- Iterate: add new ideas, remove weak ones, regroup, re-score
- Can return to Step 3B or 3C to generate more ideas if needed
- Help the user make trade-off decisions between competing ideas
- For contested top hypotheses — propose: "Stress-test the top-3 hypotheses via a role debate (Step 3D)?" — the debate runs on the already-gathered evidence, and the corrected Confidence re-sorts the ICE table

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
  - **Debates** (if Step 3D ran) — verdict table open, round transcripts in collapsed expand-blocks
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

**Self-improvement check** (after corrections are applied and confirmed): follow `references/self-improvement.md` — analyze whether the correction is a pattern, and if so propose a SKILL.md improvement (version bump + CHANGELOG).

### Step 7 — Transition to next stage

Always propose:

- Proceed to creating detailed requirements for selected ideas via the **Feature and Hypothesis Requirements Creator** skill
- Recommend which specific ideas from the final list to take into work first — based on ICE score ranking
- If no concept exists yet — suggest creating one via **Write Concept / PRD** before moving to requirements
- If CJM Hypotheses mode was used → also offer: "Run full **CJM Research** to verify these hypotheses, assess risks, and build a prioritized backlog"
- For the top-ranked hypotheses → offer: "Register these in the **experiment tracker** so they're tracked from proposed → running → decided?" → invoke `experiment-tracker` (register mode), passing per hypothesis: statement, ICE/ROI score, funnel stage, primary metric, and the validation method chosen in Step 3A/3B. The tracker takes them to state `proposed`.

### Step 8 — Design Bridge handoff (Optional)

> Requires: `design-bridge` skill (Grow PM v1.10.0+). If not installed — skip gracefully.

After ICE-ranking top-3 hypotheses — often useful to quickly prototype or create an A/B readout deck. Via `AskUserQuestion`:

> "Top hypotheses ranked. Create a design-side deliverable?"
> 1. **Low-fi prototype for top hypothesis** — Mermaid flow or ASCII wireframe to visualize the idea before development investment (recommended for top-1 hypothesis)
> 2. **Brainstorm readout deck** — 8-slide summary for discussion with product leads
> 3. **Skip**

IF user selects 1 → invoke `design-bridge` with:
- `intent: prototype`
- `fidelity: lo-fi`
- `source: top-1 hypothesis (description + user goal + expected outcome)`
- `language: active user.language`

IF user selects 2 → invoke `design-bridge` with:
- `intent: deck`
- `subtype: research-highlights` (closest match — hypothesis list is also a research output)
- `source: full_brainstorm_output`
- `audience: product_leads`
- `length: 8`

Fallback: if `design-bridge` is not installed — display: "Install `grow-product-manager` v1.10.0+ to enable design-bridge handoffs." Do not block the workflow.

### Step 9 — Save to Vault (Optional)

> Requires: `references/vault-protocol.md` → Vault Save

IF vault_level > L0 AND vault sync_mode != "off":

1. For **each finalized hypothesis** (Step 5), save a separate artifact:
   `vault_save({ type: "hypothesis", product: active_product, skill: "brainstorm-features", skill_version: "0.10.1", tags: [funnel stage, platform, topic keywords], content: hypothesis with ICE + PRO/ROI scores and rationale, related: [source CJM analysis, source research, sibling hypotheses], extra_frontmatter: { ice_score, pro_roi, hypothesis_status: "proposed" } })`
2. Display: "Saved to Vault: Hypotheses/{product}/… (N hypotheses)"
3. For **debate sessions** (Step 3D), additionally save the debate itself:
   `vault_save({ type: "debate", product: active_product, skill: "brainstorm-features", skill_version: "0.10.1", tags: [debate topic, role names], content: «Debates» section (rounds + verdict + minority report), related: [affected hypotheses], extra_frontmatter: { debate_question, roles, verdict, confidence, minority_report, rounds, inline_simulation } })`
   Display: "Saved to Vault: Debates/{product}/…"

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
- **`references/roi-frameworks.md`** — PRO/ROAIP economics (money-based scoring computed alongside ICE)
- **`references/validation-methods.md`** — validation methods ranked by cost and reliability
- **`references/integration-strategy.md`** — MCP → Registry → Browser fallback chain
- **`references/data-policy.md`** — data confidentiality policy
- **`references/self-improvement.md`** — self-improvement protocol: how to learn from user corrections and improve skill algorithms
- **`references/cjm-protocol.md`** — CJM anomaly severity, funnel impact formulas, stage position multipliers
- **`references/debate-protocol.md`** — Debate mode engine (Step 3D): applicability check, role presets, rounds, facilitator synthesis, ICE Confidence correction, guardrails
- **`references/cjm-hypotheses-mode.md`** — skill-local: full Step 3C workflow (hypothesis format, CJM-weighted ICE, funnel impact, categorization, return contract)
- **`references/funnel-templates.md`** — standard funnel stage templates by product type
