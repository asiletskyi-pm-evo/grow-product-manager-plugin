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

**Instructions:** Include both primary metrics (that the feature aims to improve) and guard-rail metrics (that should not degrade). Be specific about expected direction and magnitude of change.

---

### Requirements

#### Business Requirements

Describe general business requirements: what should change for different user types and in the product overall.

**Instructions:** Focus on WHAT should change from a business perspective, not HOW it should be implemented. Describe the expected behavior for each affected user type. Use bold text to highlight key business rules and constraints.

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

#### UI&UX Requirements

**This section is left empty for Product Designers to fill in.**

Product Designers add:
- Links to Figma mockups
- Description of main UI&UX implementation requirements

If Figma links to current (pre-change) designs were found during context gathering — include them here as reference with a note: "Current state (before changes):"

#### Analytics Coverage Requirements

**This section is left empty for Product Analysts to fill in.**

Product Analysts add:
- Analytics event requirements per platform
- Tracking specifications

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
