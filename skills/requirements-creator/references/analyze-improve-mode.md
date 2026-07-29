# analyze-improve-mode.md

> Skill-local reference for `requirements-creator` — the full **Analyze & Improve** mode workflow (A1–A9). Loaded on demand when the mode is active (SKILL.md → Mode Selection). Extracted verbatim from the core in v0.12.0 (thin-core rule).

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
- Are there technical claims with no identifiable source — user / document / ticket? (Gate 1 — `references/artifact-style-gate.md`)
- Are requirements or stages written as paragraph prose instead of lists/tables? (Gate 2 — same reference)
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

**Prioritization check (ROI & ICE):** as part of the analysis, verify whether the existing requirements carry computed **ROI** (PRO/ROAIP — `references/roi-frameworks.md`) and **ICE** scores (computed by `brainstorm-features`). If missing, add a proposal: "The feature isn't prioritized (no ROI/ICE) — recommend running `/grow-product-manager:brainstorm-features` to score it before finalizing, to confirm it's worth implementing."

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

Before that final review, run `references/artifact-style-gate.md` on the improved document (maker–checker; two lenses if it will be re-published). Include the one-line gate report.

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

If the user agrees — invoke Task Creator with full context.

