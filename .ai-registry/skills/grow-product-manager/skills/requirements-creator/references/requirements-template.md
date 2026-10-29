# Standard Requirements Template

This is the default template structure for requirements documents. If your organization has a custom Confluence template, configure its URL in `local-context.md` (see `local-context.example.md` for setup).

When publishing to non-Confluence tools (Notion, Google Docs, etc.), adapt the structure using equivalent elements of the target tool while preserving the same sections and hierarchy.

## Template Structure

### Table of Contents

- In Confluence: use the Table of Contents macro with heading levels 1 through 6
- In Notion: use the Table of Contents block
- In Google Docs: use Insert → Table of Contents

---

### Epic

Link to the Epic description in Confluence.

**Instructions:** Insert a clickable link to the Confluence page that describes the Epic this feature belongs to. This provides teams with broader context about the initiative.

---

### Hypotheses

Describe hypotheses: preconditions/problem, what we want to change, what we want to achieve.

**Format — numbered table:**

| № | Hypothesis |
|---|------------|
| 1 | If [precondition/problem], then [what we change], therefore [expected outcome] |
| 2 | ... |

**Instructions:** Each hypothesis should follow the structure: IF [precondition or problem exists] → WE DO [specific change] → THEN [expected measurable outcome]. Be specific about the problem and the expected result.

---

### A/B Test sections (only if A/B or A/B/C test is selected)

#### Test Groups

| Group | Description |
|-------|-------------|
| Control (A) | Current behavior — no changes. Description of what users see now |
| Test (B) | New behavior — description of what changes for users in this group |
| Test (C) | *(Only for A/B/C)* Alternative behavior — description of the alternative approach |

#### Traffic Split

| Group | % of traffic |
|-------|-------------|
| A (control) | X% |
| B (test) | Y% |
| C (test) | Z% *(only for A/B/C)* |

**Instructions:** Standard split is 50/50 for A/B, 33/33/34 for A/B/C. Adjust based on risk tolerance and required sample size.

#### Success Criteria

| Metric | Success threshold | Comment |
|--------|------------------|---------|
| Primary metric | +X% vs control | Minimum detectable effect |
| Secondary metric | No degradation | Guard rail metric |

**Instructions:** Define primary metric (what determines success), guard rail metrics (what must not degrade), and minimum detectable effect size.

#### Decision Rule

| Outcome | Condition | Action |
|---------|-----------|--------|
| **Ship** | Primary metric hits threshold at significance AND no guardrail regression | Promote test group to 100% |
| **Iterate** | Primary metric neutral / inconclusive, no guardrail harm | Refine and re-run, or extend for sample size |
| **Kill** | Guardrail metric regresses beyond tolerance OR primary metric negative | Roll back, keep control |

**Instructions:** State the ship / iterate / kill rule explicitly **before** launch, so the readout is a lookup, not a debate. Tie thresholds to the Success Criteria above and the significance level. Since v3.9.0 the Pre-mortem below points here for its kill criteria.

#### Expected Duration

- Estimated duration: X weeks
- Minimum sample size considerations
- Statistical significance threshold (typically 95%)

---

### Goals

Describe goals of the feature.

**Format — numbered table:**

| № | Goal |
|---|------|
| 1 | [Specific, measurable goal] |
| 2 | ... |

**Instructions:** If the goal IS the metric itself (e.g., "increase conversion by 5%"), this block can be removed and the "Metrics" block is sufficient. Goals should describe the desired outcome at a higher level than metrics.

---

### Metrics

Describe metrics and forecasts of their changes, usually in %.

**Format — numbered table:**

| № | Metric | Expected change |
|---|--------|----------------|
| 1 | [Metric name] | [Expected change, e.g., +5%, -2%, no change] |
| 2 | ... | ... |

**Instructions:** Include both primary metrics (that the feature aims to improve) and guard-rail metrics (that should not degrade). Be specific about expected direction and magnitude of change. Expected changes are targets or forecasts and carry no evidence class (since v3.8.0, `references/pm-mental-model.md` §4); a current baseline, where one is given, carries its class (e.g. `measured · <dashboard>, <period>` from Product Analysis, `reported (<who>)` when the user typed it), and an unsourced input a forecast rests on is labelled `[assumed — …]`.

---

### Requirements

#### Business Requirements

Describe general business requirements: what should change for different user types and in the product overall.

**Format — bulleted list of theses:**

- Each thesis is 1–2 sentences, key business rules and constraints in **bold**
- Group theses by affected user type when more than one is affected
- No paragraph prose — a paragraph hides individual requirements (`references/artifact-style-gate.md`, Gate 2)

**Instructions:** Focus on WHAT should change from a business perspective, not HOW it should be implemented. Describe the expected behavior for each affected user type. Only include technical facts that pass the source test (Gate 1) — no AI technical assumptions here.

#### Functional Requirements

Describe what we want to implement/change in the product, how it should work, what business logic conditions should apply, how the functionality should work in user interfaces. Decompose requirements by blocks, screens, and stages of user interaction.

**Format — numbered table:**

| № | Block / Module / Topic | Requirements |
|---|------------------------|--------------|
| 1 | [Block/screen name] | [Detailed functional requirements for this block] |
| 2 | [Another block] | [Requirements] |

**Instructions:**
- Each row should cover a distinct block, screen, or interaction stage
- Requirements must be specific enough for a developer to implement without guessing
- Include: expected behavior, edge cases, error handling, validation rules
- If the feature has multiple user flows — describe each flow separately
- Reference current Figma designs where applicable (link to specific frames)

#### AI Feature: Behaviour and Evaluation (only if the feature is AI-driven, since v3.9.0)

Added when the feature is AI-driven in explicit AI-qualified words (`references/ai-feature-section.md` §1). The skeleton is section 2 of `templates/built-in/requirements/ai-feature-v1.md` — Behaviour spec, Eval set, Acceptable error rate, Kill criteria, with the same columns; copy it, never restate it.

**Instructions:** Fill each cell from the request and the sources; a cell nothing states reads `⚠️ TBD` and is never asked — except a kill row's date and then, which are derived (`references/ai-feature-section.md` §3). Each eval case carries its origin class (`observed`, `reported` or `simulated`); expected outputs, error rates and kill thresholds carry none. Keep it apart from the optional "Технічні рекомендації (AI)" block — behaviour rules are requirements, and Gate 1 still keeps model, vendor and prompt choices out of them. Rules: `references/ai-feature-section.md` §3.

#### Technical Requirements

**Implementation approach:**
- Determine the approach: without flag, under feature flag, as A/B test, A/B/C test
- State the selected approach clearly

**Platforms:**
- List all platforms where changes are needed
- Examples: Buyer App Android, Buyer App iOS, WEB Buyer Portal, WEB Seller CMS, Seller CMS App, Admin panel, etc.
- The platform list is flexible and product-specific

**Locales:**
- Determine on which locales the functionality should work:
  - On all locales
  - Only on specific locales (list them)
  - On several (specify which)

#### Технічні рекомендації (AI) — optional

Included ONLY when the user explicitly requested technical recommendations. Placed at the end of the document. Opens with the mandatory AI callout (warning panel in Confluence) and marks each item's confidence (`general practice` / `assumption from context`). See `references/artifact-style-gate.md` (Gate 1). Never merge these items into functional or business requirements.

#### UI&UX Requirements

**This section is left empty for Product Designers to fill in.**

Product Designers add:
- Links to Figma mockups
- Description of main UI&UX implementation requirements

If Figma links to current (pre-change) designs were found during context gathering — include them here as reference with a note: "Current state (before changes):"

With a prototype source (since v3.9.0, `references/ai-feature-section.md` §6b), link its frames as the proposed design — a source, not validation.

#### Analytics Coverage Requirements

**This section is left empty for Product Analysts to fill in.**

Product Analysts add:
- Analytics event requirements per platform
- Tracking specifications

---

### Acceptance Criteria

Testable conditions the implementation must satisfy for the feature to be considered done and correct — written so QA and analytics can verify them without guessing.

**Format — Given / When / Then table:**

| # | Given / When / Then |
|---|---------------------|
| AC-1 | GIVEN [context/state], WHEN [action], THEN [observable, checkable result] |
| AC-2 | ... |

**Instructions:** Cover the main flows AND the key edge cases and error states. Each criterion must be observable and binary (pass/fail) — avoid vague wording like "works well". These criteria are the contract with the developer/AI and the checklist QA verifies against; they also seed the Analytics Coverage and Test tasks. For A/B tests, acceptance criteria verify the mechanics work; the **Decision Rule** (above) decides whether the change ships. For an AI-driven feature (since v3.9.0), add AC-eval: the eval set passes at or below the acceptable error rate.

---

### Out of scope

What this spec deliberately does not cover (since v3.9.0).

**Format — bulleted list.**

**Instructions:** Fill from the request and the source concept's Non-goals / Scope. When nothing states it, write `⚠️ TBD` — a derived section, never asked. It is one of the six elements of `references/artifact-style-gate.md` → Spec readiness.

---

### Pre-mortem (A/B test or AI-driven feature only, since v3.9.0)

Rendered from `templates/built-in/partial/pre-mortem-v1.md` (`references/judgment-points.md` §7): written as if the change already failed — 2–3 causes, each naming the input or section it rests on, with an early signal and what we do now.

**Instructions:** For an A/B test the causes are test-validity causes (power for the MDE, sample-ratio or exposure faults, novelty, events not firing, a missing guardrail), each with a pre-launch check. Kill criteria are a pointer to the **Decision Rule** (A/B) or to the AI **Kill criteria** — never a second table. Derived, never asked; a `⚠️ TBD` cell is counted, not asked. The PM edits or deletes it at review. Rules: `references/ai-feature-section.md` §4.

---

### Tasks

> **Note:** Use the user's preferred language (`user.language`) for all section headings and content when publishing the requirements document.

- Insert link to Epic in Jira
- Configure Jira work items macro block:
  - JQL filter: `parent = EPIC-KEY AND labels = FEATURE-CODE`
  - Sort by: Sprint
  - Display columns: Key, Summary, Status, Assignee, Sprint

**In Confluence:** Use the Jira Issues / Jira work items macro with the configured JQL query.

**In Notion / Google Docs:** Add a link to the Jira board filtered by Epic and feature label.

## Adaptation for Non-Confluence Tools

When publishing to Notion or Google Docs, adapt Confluence-specific elements:

| Confluence element | Notion equivalent | Google Docs equivalent |
|-------------------|-------------------|----------------------|
| Table of Contents macro | Table of Contents block | Insert → Table of Contents |
| Horizontal rule/divider | Divider block (---) | Horizontal line |
| Jira work items macro | Link to Jira board with JQL filter | Link to Jira board with JQL filter |
| Panels | Callout blocks | Colored text boxes or indented blocks |
| Headings H1/H2/H3 | Headings 1/2/3 | Headings 1/2/3 |
