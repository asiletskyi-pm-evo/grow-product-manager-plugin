# PRD Block Reference

Detailed templates for each standard block. Use these as the foundation for Confluence pages. Adapt depth per feature type.

---

## 1. Summary (TL;DR)

2-3 sentences answering: what is being built, for whom, and why.

```
**Feature**: [name]
**Goal**: [one-sentence goal]
**Target users**: [who benefits]
**Expected impact**: [key metric or outcome]
```

---

## 2. Problem Statement

```
### Problem
[Describe the problem in 2-3 paragraphs]

### Who is affected
[User segments experiencing the problem]

### Current workarounds
[How users cope today — manual processes, competitor tools, hacks]

### Evidence
[Data, quotes, support tickets, metrics proving the problem exists]
- **Metric**: [e.g., "30% of users abandon at step X"]
- **User feedback**: [quote or summary]
- **Support volume**: [e.g., "50 tickets/month about this issue"]
```

---

## 3. Goals & Non-Goals

```
### Goals
- **G1**: [Specific, measurable goal]
- **G2**: [Specific, measurable goal]

### Non-Goals
- **NG1**: [What we consciously do NOT include in scope and why]
- **NG2**: [What we consciously do NOT include in scope and why]
```

---

## 4. User Stories / Use Cases

```
### Primary scenarios
| # | As a... | I want to... | So that... |
|---|---------|-------------|------------|
| 1 | [role]  | [action]    | [benefit]  |

### Edge cases
- **Edge case 1**: [description] → expected behavior: [what should happen]
- **Edge case 2**: [description] → expected behavior: [what should happen]

### Acceptance criteria
- [ ] [Criterion 1]
- [ ] [Criterion 2]
```

---

## 5. Proposed Solution

```
### Overview
[High-level description of the solution in 2-3 paragraphs]

### Key components
| Component | Description | Owner |
|-----------|------------|-------|
| [Component 1] | [What it does] | [Team] |

### User flow
1. [Step 1]: [what happens]
2. [Step 2]: [what happens]
3. ...

### Key decisions
- **Decision 1**: [what was decided and why]
- **Decision 2**: [what was decided and why]
```

---

## 6. What Changes for Users

This block must be written separately for each affected user segment.

```
### Affected user segments
[List all user types impacted by this concept]

### Changes for [User Segment A] (e.g., Buyers)

**What they gain:**
- [New capability or improvement 1]
- [New capability or improvement 2]

**What changes in their existing flow:**
- [Current behavior] → [New behavior]
- [Current behavior] → [New behavior]

**What they may lose or find different:**
- [Removed feature / changed behavior — if any]

### Changes for [User Segment B] (e.g., Sellers)

**What they gain:**
- ...

**What changes in their existing flow:**
- [Current behavior] → [New behavior]

**What they may lose or find different:**
- ...
```

### Tips for this block
- Be specific: don't just say "improved experience" — describe exactly what changes
- If a flow changes, show before/after
- If something is removed, explain why and what replaces it
- Consider emotional impact: will users need to re-learn something?

---

## 7. Alternative Solutions (optional)

Include only if confirmed by the user in Step 1.

```
### Alternatives considered

| # | Alternative | Pros | Cons | Why not chosen |
|---|------------|------|------|----------------|
| 1 | [Option A] | [benefits] | [drawbacks] | [reason] |
| 2 | [Option B] | [benefits] | [drawbacks] | [reason] |
| 3 | [Option C] | [benefits] | [drawbacks] | [reason] |

### Recommendation
[Why the proposed solution was chosen over alternatives — summarize the key trade-off]
```

---

## 8. Scope & Phasing

```
### Phase 1 — MVP
- [Feature/capability 1]
- [Feature/capability 2]
- **Release target**: [date or sprint]

### Phase 2
- [Feature/capability 3]
- [Feature/capability 4]
- **Release target**: [date or sprint]

### Out of Scope
- [Item 1] — reason: [why excluded]
- [Item 2] — reason: [why excluded]
```

---

## 9. Design & UX (adaptive)

**Expanded** for frontend/product features. **Minimal or skipped** for backend/infrastructure.

```
### Design artifacts
- **Figma link**: [URL]
- **Prototype link**: [URL if available]

### Key UI decisions
- [Decision 1]: [rationale]
- [Decision 2]: [rationale]

### Accessibility requirements
- [Requirement 1]
- [Requirement 2]

### Responsive behavior
- **Desktop**: [description]
- **Mobile**: [description]
```

---

## 10. Technical Considerations (adaptive)

**Expanded** for backend/infrastructure features. **Minimal** for design-only changes.

```
### Architecture
[High-level architecture description or diagram reference]

### API changes
| Endpoint | Method | Change type | Description |
|----------|--------|-------------|-------------|
| [/api/...] | POST | New | [what it does] |

### Data model changes
[New tables, fields, migrations needed]

### Dependencies
| Dependency | Team | Status | Risk |
|-----------|------|--------|------|
| [Service X] | [Team Y] | [Ready/Blocked] | [High/Med/Low] |

### Performance considerations
- [Expected load / throughput]
- [Caching strategy]

### Data migrations
- [Migration 1]: [description, estimated downtime]
```

---

## 11. Success Metrics

```
### Primary metric (North Star)
- **Metric**: [name]
- **Current value**: [baseline]
- **Target**: [goal]
- **Measurement method**: [how and where]

### Secondary metrics
| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| [Metric 1] | [current] | [goal] | [method] |
| [Metric 2] | [current] | [goal] | [method] |

### Measurement timeline
- **After 1 week**: [what to check]
- **After 1 month**: [what to evaluate]
- **After 1 quarter**: [success/fail criteria]

### Guardrail metrics
[Metrics that should NOT degrade — e.g., page load time, error rate]
```

---

## 12. Risks & Mitigations

```
| # | Risk | Type | Probability | Impact | Mitigation |
|---|------|------|------------|--------|------------|
| 1 | [Risk description] | Technical / Business / Dependency | High/Med/Low | High/Med/Low | [How to mitigate] |
| 2 | ... | ... | ... | ... | ... |
```

---

## 13. Timeline & Milestones (adaptive)

**Expanded** for cross-team features with dependencies. **Minimal** for autonomous features.

```
### Timeline
| Phase | Start | End | Owner | Dependencies |
|-------|-------|-----|-------|-------------|
| Design | [date] | [date] | [team] | — |
| Development | [date] | [date] | [team] | Design complete |
| QA | [date] | [date] | [team] | Dev complete |
| Release | [date] | [date] | [team] | QA passed |

### Key milestones
- [ ] [Milestone 1] — [date]
- [ ] [Milestone 2] — [date]

### Cross-team dependencies
| Dependency | Team | Needed by | Status |
|-----------|------|-----------|--------|
| [Item] | [Team] | [date] | [On track / At risk / Blocked] |
```

---

## 14. Open Questions

```
| # | Question | Owner | Deadline | Status |
|---|---------|-------|---------|--------|
| 1 | [Question] | [Person/team] | [date] | Open / Resolved |
| 2 | [Question] | [Person/team] | [date] | Open / Resolved |
```
