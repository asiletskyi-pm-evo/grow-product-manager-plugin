# Vault Schema

**Overview:** This document defines the schema for artifacts stored in the Obsidian Vault — frontmatter fields, artifact types, tag taxonomy, folder structure, and templates. Referenced by `vault-protocol.md`.

---

## Frontmatter Standard

All artifacts stored in the Obsidian Vault follow a consistent frontmatter schema to enable consistent parsing, filtering, and automation across the Grow Product Manager Plugin.

### Base Frontmatter (All Artifact Types)

Every artifact, regardless of type, includes these base frontmatter fields:

#### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Artifact type from Type Taxonomy (see Type Taxonomy section) |
| `product` | string | Product name from local-context, or "general" if cross-product |
| `created` | date | Creation date (YYYY-MM-DD) |
| `skill` | string | Skill name that created this artifact |
| `skill_version` | string | Version of skill that created this artifact (e.g., "1.2.3") |

#### Classification Fields (Optional but Recommended)

| Field | Type | Description |
|-------|------|-------------|
| `tags` | string[] | Hierarchical tags from Tag Taxonomy (e.g., ["funnel/checkout", "platform/web"]) |
| `category` | string | Content category for organizational purposes |
| `platform` | string[] | Platforms affected or relevant to this artifact (android, ios, web, admin, cms) |

#### Relation Fields

| Field | Type | Description |
|-------|------|-------------|
| `related` | string[] | Wikilinks to related artifacts (format: "[[path/to/artifact]]") |
| `parent` | string | Wikilink to parent artifact |
| `children` | string[] | Wikilinks to child artifacts |

#### Lifecycle Fields

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Lifecycle status: active \| archived \| superseded \| draft |
| `superseded_by` | string | Wikilink to superseding artifact (if status = superseded) |
| `confidence` | float | Confidence score (0.0-1.0) for findings or recommendations |
| `last_reviewed` | date | Last review date (YYYY-MM-DD) |

#### Context Fields

| Field | Type | Description |
|-------|------|-------------|
| `source_session` | string | Session ID where artifact was created |
| `published_to` | string | URL where artifact is published (e.g., Confluence page) |
| `confluence_page_id` | string | Confluence page ID if synced |
| `jira_epic` | string | Associated Jira epic key |

### Extended Frontmatter by Type

Each artifact type includes additional type-specific fields beyond the base schema.

#### hypothesis

Artifact type for feature hypotheses with ICE scoring.

```yaml
ice_score: float (0-100)
ice_impact: float (1-10, 10 = massive impact)
ice_confidence: float (0-1.0)
ice_ease: float (1-10, 10 = easiest to implement)
funnel_stage: string (awareness|consideration|checkout|retention|referral)
hypothesis_status: string (proposed|testing|validated|rejected)
test_result: string (description of test outcome, if status = tested)
validated_by: string (email or name of person who validated)
```

#### ab-test-results

Artifact type for A/B test results and learnings.

```yaml
test_name: string (name of the test)
test_duration_days: int (number of days test ran)
sample_size: int (total sample size across variants)
primary_metric: string (metric being measured)
primary_metric_change: float (percentage change, e.g., 5.2)
statistical_significance: float (p-value or confidence level, 0-1.0)
result: string (winner|loser|inconclusive)
tested_hypothesis: string (wikilink to hypothesis tested)
```

#### decision

Artifact type for key product, technical, or process decisions.

```yaml
decision_type: string (product|technical|process)
decided_by: string[] (email addresses or names of decision makers)
alternatives_considered: int (number of alternatives evaluated)
reversibility: string (easy|medium|hard - how easy to reverse)
deadline: date (decision deadline, YYYY-MM-DD)
```

#### cjm-health-check

Artifact type for regular Customer Journey Map health assessments.

```yaml
health_score: int (0-100, overall funnel health)
anomalies_found: int (number of anomalies detected)
critical_anomalies: int (number of critical-severity anomalies)
comparison_baseline: string (wikilink to baseline CJM for comparison)
previous_health_check: string (wikilink to previous health check)
```

#### meeting-notes

Artifact type for meeting notes and summaries.

```yaml
meeting_type: string (sprint-planning|grooming|stakeholder|1on1|other)
attendees: string[] (email addresses or names)
action_items_count: int (number of action items generated)
decisions_count: int (number of decisions made)
duration_minutes: int (meeting duration)
fireflies_id: string (Fireflies.ai transcript ID, if recorded)
```

#### metrics-review

Artifact type for periodic metrics analysis and insights.

```yaml
review_period: string (e.g., "2026-03" for March 2026)
key_metrics_analyzed: string[] (list of metrics reviewed)
anomalies_detected: int (number of anomalies identified)
trend_direction: string (up|down|stable - overall trend)
```

#### concept

Artifact type for product concepts and PRDs.

```yaml
scope: string (mvp|full - scope of concept)
phase_count: int (number of implementation phases)
estimated_effort: string (T-shirt size: xs|s|m|l|xl, or story points)
```

#### requirements

Artifact type for feature requirements documents.

```yaml
approach: string (feature-flag|ab-test|direct - how feature will be shipped)
platforms_covered: string[] (platforms included in requirements: android|ios|web|admin|cms)
requirements_count: int (number of functional/acceptance requirements)
```

#### competitive-analysis

Artifact type for competitive intelligence.

```yaml
competitors_analyzed: string[] (competitor company names)
analysis_type: string (feature|pricing|ux|market-position)
```

#### market-research

Artifact type for market research and sizing.

```yaml
methodology: string (survey|interview|desk-research|mixed)
market_size: string (e.g., "$500M TAM")
growth_rate: float (annual growth rate as percentage, e.g., 15.5)
```

#### ux-benchmark

Artifact type for UX benchmarking studies.

```yaml
benchmark_source: string (e.g., "Nielsen Norman Group")
areas_covered: string[] (UX areas benchmarked: usability|performance|accessibility|design-quality)
```

#### post-release

Artifact type for post-release analysis and impact measurement.

```yaml
feature_name: string (name of released feature)
release_date: date (launch date, YYYY-MM-DD)
metrics_impacted: string[] (list of metrics affected)
overall_impact: string (positive|negative|neutral)
```

#### knowledge-source

Artifact type for curated external knowledge sources.

```yaml
source_url: string (full URL to source)
source_type: string (article|research-report|case-study|benchmark|tool|video)
trust_score: float (0-1.0, internal trust assessment)
publication_date: date (publication date, YYYY-MM-DD)
```

#### funnel-anomaly

Artifact type for detected funnel anomalies and investigations.

```yaml
severity: string (critical|warning|info)
affected_stage: string (awareness|consideration|checkout|retention|referral)
deviation_percent: float (percentage deviation from baseline, e.g., -15.3)
affected_platforms: string[] (platforms affected)
```

#### project-overview

Artifact type for project descriptions and tracking.

```yaml
project_status: string (active|paused|completed)
team_size: int (number of people on team)
start_date: date (project start date, YYYY-MM-DD)
target_date: date (project completion target, YYYY-MM-DD)
```

---

## Type Taxonomy

The Grow Product Manager Plugin defines 16 artifact types, each with a specific purpose, source skill, and folder location.

| Type | Skill Source | Folder | Description |
|------|--------------|--------|-------------|
| competitive-analysis | product-research | Research/ | Competitive feature/pricing/UX analysis |
| market-research | product-research | Research/ | Market sizing, TAM, and research |
| ux-benchmark | product-research | Research/ | UX benchmark study or comparison |
| cjm-analysis | cjm-research | CJM/full-reports/ | Full Customer Journey Map analysis |
| cjm-health-check | cjm-research | CJM/health-checks/ | Regular funnel health assessment |
| funnel-anomaly | cjm-research | CJM/anomalies/ | Detected funnel anomaly and investigation |
| concept | write-concept | Concepts/ | Product concept or PRD |
| requirements | requirements-creator | Requirements/ | Feature requirements document |
| ab-test-results | product-analysis | Analysis/ab-tests/ | A/B test results and learnings |
| metrics-review | product-analysis | Analysis/metrics/ | Periodic metrics review and analysis |
| post-release | product-analysis | Analysis/post-release/ | Post-release feature analysis |
| hypothesis | brainstorm-features | Hypotheses/ | Feature hypothesis with ICE score |
| meeting-notes | meeting-processor | Meetings/ | Meeting notes and summaries |
| decision | (any skill) | Decisions/ | Key decision with rationale |
| knowledge-source | knowledge-library | Knowledge/sources/ | Curated external knowledge source |
| project-overview | (manual/configurator) | Projects/ | Project description and status |

### TYPE_FOLDER_MAP Reference

```json
{
  "competitive-analysis": "Research/",
  "market-research": "Research/",
  "ux-benchmark": "Research/",
  "cjm-analysis": "CJM/full-reports/",
  "cjm-health-check": "CJM/health-checks/",
  "funnel-anomaly": "CJM/anomalies/",
  "concept": "Concepts/",
  "requirements": "Requirements/",
  "ab-test-results": "Analysis/ab-tests/",
  "metrics-review": "Analysis/metrics/",
  "post-release": "Analysis/post-release/",
  "hypothesis": "Hypotheses/",
  "meeting-notes": "Meetings/",
  "decision": "Decisions/",
  "knowledge-source": "Knowledge/sources/",
  "project-overview": "Projects/"
}
```

---

## Tag Taxonomy (Hierarchical)

Tags use hierarchical naming (parent/child) to enable filtering and organization. All tags are lowercase with hyphens for multi-word tags.

### funnel/ — Customer Journey Map Stages

Tags for CJM stage classification:
- `funnel/awareness` — Awareness stage
- `funnel/consideration` — Consideration stage
- `funnel/checkout` — Checkout / conversion stage
- `funnel/retention` — Retention and engagement
- `funnel/referral` — Referral and advocacy

### platform/ — Platform Identification

Tags for platform-specific content:
- `platform/android` — Android app
- `platform/ios` — iOS app
- `platform/web` — Web platform
- `platform/admin` — Admin dashboard
- `platform/cms` — CMS or content management

### metric/ — Metric Categories

Tags for metric type classification:
- `metric/conversion` — Conversion rate metrics
- `metric/retention` — Retention and churn metrics
- `metric/revenue` — Revenue and monetization metrics
- `metric/engagement` — User engagement metrics
- `metric/acquisition` — User acquisition metrics

### status/ — Hypothesis Statuses

Tags for hypothesis lifecycle:
- `status/proposed` — Newly proposed hypothesis
- `status/testing` — Currently being tested
- `status/validated` — Validated through testing
- `status/rejected` — Rejected or disproven

### impact/ — Impact Levels

Tags for severity or impact classification:
- `impact/high` — High impact
- `impact/medium` — Medium impact
- `impact/low` — Low impact

### research/ — Research Types

Tags for research methodology:
- `research/competitive` — Competitive analysis
- `research/market` — Market research
- `research/ux` — UX research or usability testing
- `research/user` — User interviews or feedback

### phase/ — Project Phases

Tags for project lifecycle:
- `phase/discovery` — Discovery and research phase
- `phase/design` — Design and ideation phase
- `phase/development` — Development and implementation
- `phase/testing` — Testing and QA phase
- `phase/launched` — Launched to production

---

## Folder Structure

Complete folder structure for `{Vault}/{PluginFolder}/`:

```
{Vault}/
├── _MOC/                              # Maps of Content (auto-generated indexes)
│   ├── Dashboard.md
│   ├── Products/
│   │   ├── {ProductName}.md
│   │   └── {ProductName}.md
│   ├── Timeline.md
│   └── Tags.md
│
├── Research/                          # Competitive, market, and UX research
│   ├── {product}/
│   │   ├── competitive-analysis-*.md
│   │   ├── market-research-*.md
│   │   └── ux-benchmark-*.md
│   └── general/
│       ├── competitive-analysis-*.md
│       ├── market-research-*.md
│       └── ux-benchmark-*.md
│
├── CJM/                               # Customer Journey Map research
│   ├── {product}/
│   │   ├── health-checks/
│   │   │   └── cjm-health-check-*.md
│   │   ├── anomalies/
│   │   │   └── funnel-anomaly-*.md
│   │   └── full-reports/
│   │       └── cjm-analysis-*.md
│   └── cross-platform/
│       └── [shared CJM reports]
│
├── Concepts/                          # Product concepts and PRDs
│   ├── {product}/
│   │   └── concept-*.md
│   └── drafts/
│       └── concept-*.md (draft status)
│
├── Requirements/                      # Feature requirements
│   ├── {product}/
│   │   └── requirements-*.md
│
├── Analysis/                          # Product analysis and metrics
│   ├── {product}/
│   │   ├── metrics/
│   │   │   └── metrics-review-*.md
│   │   ├── ab-tests/
│   │   │   └── ab-test-results-*.md
│   │   └── post-release/
│   │       └── post-release-*.md
│   └── dashboards/
│       └── [analysis summary dashboards]
│
├── Hypotheses/                        # Feature hypotheses and ideas
│   ├── {product}/
│   │   └── hypothesis-*.md
│   ├── archive/
│   │   └── hypothesis-*.md (archived status)
│   └── backlog.md
│       (Prioritized hypothesis backlog with links to hypothesis artifacts)
│
├── Meetings/                          # Meeting notes and summaries
│   └── meeting-notes-*.md
│
├── Decisions/                         # Product and technical decisions
│   ├── {product}/
│   │   └── decision-*.md
│   └── ADR/
│       └── decision-*.md (Architecture Decision Records)
│
├── Knowledge/                         # Knowledge library and sources
│   ├── sources/
│   │   └── knowledge-source-*.md
│   ├── library-index.md
│   │   (Index of all knowledge sources)
│   ├── categories.md
│   │   (Knowledge source categories and trust scores)
│
├── Projects/                          # Project overviews and tracking
│   ├── {project-name}/
│   │   ├── project-overview.md
│   │   └── [project-specific files]
│   └── {project-name}/
│       └── project-overview.md
│
└── Templates/                         # Template files (7 templates)
    ├── research.md
    ├── concept.md
    ├── requirements.md
    ├── decision.md
    ├── meeting.md
    ├── hypothesis.md
    └── knowledge-source.md
```

---

## Naming Convention

All artifact files follow a consistent naming pattern to support automated organization and deduplication.

### File Naming Format

```
{type}-{topic-slug}-{YYYY-MM-DD}.md
```

- **type**: Artifact type from Type Taxonomy (e.g., hypothesis, ab-test-results)
- **topic-slug**: Lowercase, hyphens for spaces, max 50 characters (e.g., checkout-flow, mobile-retention)
- **YYYY-MM-DD**: Creation date (e.g., 2026-04-14)
- **Duplicate handling**: If filename exists, append -2, -3, etc. (e.g., `hypothesis-checkout-flow-2026-04-14-2.md`)

### Naming Examples by Type

| Type | Example | Description |
|------|---------|-------------|
| hypothesis | `hypothesis-guest-checkout-flow-2026-04-14.md` | Feature hypothesis with descriptive topic |
| ab-test-results | `ab-test-results-checkout-mobile-upsell-2026-04-14.md` | Test results with variant names |
| decision | `decision-postgres-vs-mongodb-2026-04-14.md` | Decision with clear topic/choice |
| cjm-health-check | `cjm-health-check-q1-2026-summary-2026-04-14.md` | Health check with period |
| meeting-notes | `meeting-notes-sprint-planning-2026-04-14.md` | Meeting type and date |
| metrics-review | `metrics-review-march-2026-mobile-app-2026-04-14.md` | Period and platform/product |
| concept | `concept-one-click-checkout-2026-04-14.md` | Feature or area being conceptualized |
| requirements | `requirements-one-click-checkout-phase-2-2026-04-14.md` | Feature and phase |
| competitive-analysis | `competitive-analysis-stripe-checkout-ux-2026-04-14.md` | Competitor and area analyzed |
| market-research | `market-research-buy-now-pay-later-market-2026-04-14.md` | Market segment or topic |
| ux-benchmark | `ux-benchmark-mobile-payment-flows-2026-04-14.md` | Area benchmarked |
| post-release | `post-release-guest-checkout-impact-2026-04-14.md` | Feature and impact focus |
| knowledge-source | `knowledge-source-stripe-api-docs-2026-04-14.md` | Source name or topic |
| funnel-anomaly | `funnel-anomaly-checkout-mobile-drop-2026-04-14.md` | Stage and anomaly description |
| project-overview | `project-overview-checkout-modernization-2026-04-14.md` | Project name/goal |
| cjm-analysis | `cjm-analysis-full-funnel-q1-2026-2026-04-14.md` | Scope and period |

---

## Frontmatter Parsing Rules

The Grow Product Manager Plugin must handle frontmatter parsing robustly to support user customization and evolution of the schema.

### Parsing Strategy

1. **Tolerant Parsing**: Missing fields → use defaults, don't error
   - If a required field is missing, use a sensible default value
   - Missing optional fields are simply left empty
   - Plugin should not fail due to schema drift

2. **Unknown Fields**: Ignore (user may add custom fields)
   - Any fields not in the standard schema are preserved but ignored by automation
   - Users can add custom metadata without breaking the plugin
   - Custom fields may be useful for future extensions

3. **Date Formats**: Accept both YYYY-MM-DD and YYYY-MM-DDTHH:MM:SS
   - ISO 8601 date format preferred: YYYY-MM-DD
   - ISO 8601 datetime format also accepted: YYYY-MM-DDTHH:MM:SS
   - Both UTC and with timezone offset accepted

4. **Wikilinks in Frontmatter**: Always quoted "[[path]]"
   - Wikilinks in YAML must be quoted to avoid YAML parsing errors
   - Format: `related: ["[[path/to/artifact1]]", "[[path/to/artifact2]]"]`
   - Format: `parent: "[[path/to/parent]]"`

5. **Tags**: Always YAML list [tag1, tag2, ...]
   - Tags must be a YAML array, never a single string
   - Format: `tags: [funnel/checkout, platform/web, impact/high]`

6. **Empty Collections**: Use []
   - Empty lists should be represented as `[]`, not null
   - Format: `related: []`
   - Format: `children: []`

7. **Null Values**: Treat as unset
   - If a field is explicitly set to null, treat it as not provided
   - Plugin should use defaults for null fields
   - Null values should not trigger errors

### Example Frontmatter with Parsing Rules Applied

```yaml
---
type: hypothesis
product: mobile-app
created: 2026-04-14
skill: brainstorm-features
skill_version: 1.2.3
tags: [funnel/checkout, platform/mobile, impact/high]
category: conversion-optimization
platform: [ios, android]
related: ["[[Analysis/metrics/metrics-review-q1-2026-2026-04-14.md]]"]
parent: "[[Projects/mobile-checkout-modernization/project-overview.md]]"
children: []
status: active
confidence: 0.75
last_reviewed: 2026-04-14
source_session: abc123def456
ice_score: 78
ice_impact: 8
ice_confidence: 0.8
ice_ease: 6
funnel_stage: checkout
hypothesis_status: testing
validated_by: sarah@company.com
custom_field: any-value
---
```

---

## Template Files

The plugin includes 7 master template files that can be used to consistently create new artifacts. Each template includes complete frontmatter with placeholder values and markdown sections with HTML comment instructions for the user.

### 1. Research Template (research.md)

**Use for:** competitive-analysis, market-research, ux-benchmark artifacts

```markdown
---
type: competitive-analysis
product: general
created: YYYY-MM-DD
skill: product-research
skill_version: 1.0.0
tags: [research/competitive]
category: competitive-intelligence
platform: []
related: []
parent: null
children: []
status: draft
confidence: 0.5
last_reviewed: null
source_session: null
published_to: null
competitors_analyzed: []
analysis_type: feature
---

# Research: [Topic]

<!-- Replace [Topic] with your research focus (e.g., "Stripe Checkout UX", "BNPL Market Sizing") -->

## Overview

<!-- Provide a 2-3 sentence summary of what this research covers and why it's relevant -->

## Methodology

<!-- Describe how you conducted this research (desk research, interviews, survey, competitive review, etc.) -->

### Data Sources

<!-- List the sources used for this research -->
- Source 1
- Source 2
- Source 3

### Limitations

<!-- Note any limitations or biases in this research -->

## Key Findings

### Finding 1
<!-- Detailed finding with supporting evidence -->

### Finding 2
<!-- Detailed finding with supporting evidence -->

### Finding 3
<!-- Detailed finding with supporting evidence -->

## Implications

<!-- How do these findings apply to your product strategy? -->

## Recommendations

<!-- What actions should be taken based on these findings? -->

## Artifacts & Follow-ups

<!-- Link to related artifacts or next steps -->
- [ ] Action item 1
- [ ] Action item 2

## References

<!-- Links to source materials -->
```

### 2. Concept Template (concept.md)

**Use for:** concept artifacts

```markdown
---
type: concept
product: general
created: YYYY-MM-DD
skill: write-concept
skill_version: 1.0.0
tags: [phase/design]
category: product-concept
platform: []
related: []
parent: null
children: []
status: draft
confidence: 0.5
last_reviewed: null
source_session: null
scope: mvp
phase_count: 1
estimated_effort: m
---

# Concept: [Feature Name]

<!-- Replace [Feature Name] with your product concept title (e.g., "One-Click Checkout Flow") -->

## Problem Statement

<!-- What user problem does this concept solve? Why does it matter? -->

## User Story

<!-- As a [user type], I want [capability] so that [benefit] -->

## Concept Description

<!-- Detailed description of how this feature works from user perspective -->

### Scope: MVP

<!-- Define what's included in MVP vs. future phases -->

### User Flows

<!-- Describe key user flows and interactions -->

## Success Metrics

<!-- How will we measure success of this feature? -->
- Metric 1
- Metric 2
- Metric 3

## Technical Approach

<!-- High-level technical approach and dependencies -->

## Platforms

<!-- Platforms impacted: web, ios, android, admin, cms -->

## Assumptions & Risks

### Assumptions
<!-- What assumptions are we making? -->

### Risks
<!-- What could go wrong? -->

## Open Questions

<!-- Questions that need answering before proceeding -->
- Question 1
- Question 2

## Next Steps

<!-- What needs to happen next? -->
- [ ] Validate with users
- [ ] Define detailed requirements
- [ ] Design UI/UX mockups

## Related Artifacts

<!-- Link to research, requirements, decisions that relate to this concept -->
```

### 3. Requirements Template (requirements.md)

**Use for:** requirements artifacts

```markdown
---
type: requirements
product: general
created: YYYY-MM-DD
skill: requirements-creator
skill_version: 1.0.0
tags: [phase/development]
category: feature-requirements
platform: [web]
related: ["[[Concepts/...]]"]
parent: null
children: []
status: draft
confidence: 0.5
last_reviewed: null
source_session: null
approach: feature-flag
platforms_covered: [web]
requirements_count: 0
---

# Requirements: [Feature Name]

<!-- Replace [Feature Name] with your feature name -->

## Overview

<!-- 2-3 sentence summary of what's being built -->

## Product Context

### Problem Being Solved
<!-- What user problem or business opportunity is this addressing? -->

### Success Metrics
<!-- How will we know this is successful? -->

## Functional Requirements

### Requirement 1
**Description:** <!-- What the feature must do -->
**Acceptance Criteria:**
- [ ] Criteria 1
- [ ] Criteria 2
- [ ] Criteria 3

### Requirement 2
**Description:** <!-- What the feature must do -->
**Acceptance Criteria:**
- [ ] Criteria 1
- [ ] Criteria 2

## Non-Functional Requirements

<!-- Performance, security, scalability, accessibility, etc. -->

### Performance
<!-- Response time, load time, throughput requirements -->

### Accessibility
<!-- WCAG 2.1 AA or similar standards -->

### Security
<!-- Data protection, authentication, authorization -->

## Edge Cases & Error Handling

<!-- How should the feature behave in error scenarios? -->

## Mobile Considerations

<!-- Responsive design, touch interactions, mobile performance -->

## Analytics & Logging

<!-- What events and data should be tracked? -->

## Dependencies & Integrations

<!-- External systems, APIs, or services this depends on -->

## Implementation Approach

### Feature Flag Strategy
<!-- How will this be gradually rolled out? -->

### Backwards Compatibility
<!-- Will this change break existing integrations or workflows? -->

## Open Questions

<!-- Clarifications needed before development starts -->
- Question 1
- Question 2

## Approval & Sign-off

<!-- Who approved this? When? -->

```

### 4. Decision Template (decision.md)

**Use for:** decision artifacts

```markdown
---
type: decision
product: general
created: YYYY-MM-DD
skill: brainstorm-features
skill_version: 1.0.0
tags: [phase/development]
category: product-decision
platform: []
related: []
parent: null
children: []
status: active
confidence: 0.8
last_reviewed: YYYY-MM-DD
source_session: null
decision_type: technical
decided_by: [name@company.com]
alternatives_considered: 2
reversibility: medium
deadline: null
---

# Decision: [Decision Title]

<!-- Replace [Decision Title] with clear decision statement (e.g., "Use PostgreSQL instead of MongoDB") -->

## The Decision

<!-- State the decision clearly in one sentence -->

**Decision:** [State the decision]
**Decided by:** [Decision maker(s)]
**Date:** YYYY-MM-DD
**Status:** [Active | Archived | Superseded]

## Context

<!-- Why is this decision being made now? What's the situation? -->

## Problem Statement

<!-- What problem or opportunity prompted this decision? -->

## Alternatives Considered

### Option 1: [Option Name]
**Pros:**
- Pro 1
- Pro 2

**Cons:**
- Con 1
- Con 2

### Option 2: [Option Name]
**Pros:**
- Pro 1
- Pro 2

**Cons:**
- Con 1
- Con 2

### Option 3: [Option Name]
**Pros:**
- Pro 1

**Cons:**
- Con 1

## Rationale

<!-- Why we chose Option X over the alternatives -->

## Consequences

### Short-term
<!-- Immediate impacts and changes -->

### Long-term
<!-- Strategic or technical implications -->

## Implementation Plan

<!-- How will this decision be implemented? -->

## Reversibility

<!-- How reversible is this decision? What would it take to change course? -->

**Reversibility Level:** [Easy | Medium | Hard]

## Related Decisions

<!-- Links to related decisions or follow-up decisions -->

## Sign-off

<!-- Who approved this decision? -->

```

### 5. Meeting Template (meeting.md)

**Use for:** meeting-notes artifacts

```markdown
---
type: meeting-notes
product: general
created: YYYY-MM-DD
skill: meeting-processor
skill_version: 1.0.0
tags: []
category: meeting
platform: []
related: []
parent: null
children: []
status: active
confidence: 0.9
last_reviewed: null
source_session: null
meeting_type: sprint-planning
attendees: []
action_items_count: 0
decisions_count: 0
duration_minutes: 60
fireflies_id: null
---

# Meeting Notes: [Meeting Title]

<!-- Replace [Meeting Title] with meeting name and date (e.g., "Sprint Planning - Apr 14") -->

**Date:** YYYY-MM-DD
**Time:** HH:MM - HH:MM
**Duration:** X minutes
**Attendees:** 
- Name (Role)
- Name (Role)

**Recording:** [Fireflies link, if available]

## Agenda

<!-- What was discussed -->
1. Agenda item 1
2. Agenda item 2
3. Agenda item 3

## Discussion Summary

### Topic 1
<!-- Summary of discussion around topic 1 -->

### Topic 2
<!-- Summary of discussion around topic 2 -->

### Topic 3
<!-- Summary of discussion around topic 3 -->

## Decisions Made

### Decision 1
<!-- What was decided and why -->

### Decision 2
<!-- What was decided and why -->

## Action Items

| Owner | Action | Due Date | Priority |
|-------|--------|----------|----------|
| Name | [ ] Action item 1 | YYYY-MM-DD | High |
| Name | [ ] Action item 2 | YYYY-MM-DD | Medium |
| Name | [ ] Action item 3 | YYYY-MM-DD | Low |

## Follow-up Required

<!-- Any outstanding questions or follow-ups needed -->

## Next Meeting

**Date:** YYYY-MM-DD
**Time:** HH:MM

```

### 6. Hypothesis Template (hypothesis.md)

**Use for:** hypothesis artifacts

```markdown
---
type: hypothesis
product: general
created: YYYY-MM-DD
skill: brainstorm-features
skill_version: 1.0.0
tags: [status/proposed]
category: hypothesis
platform: [web]
related: []
parent: null
children: []
status: draft
confidence: 0.5
last_reviewed: null
source_session: null
ice_score: 0
ice_impact: 5
ice_confidence: 0.5
ice_ease: 5
funnel_stage: awareness
hypothesis_status: proposed
test_result: null
validated_by: null
---

# Hypothesis: [Hypothesis Title]

<!-- Replace [Hypothesis Title] with your hypothesis (e.g., "Simplifying checkout reduces cart abandonment by 15%") -->

## The Hypothesis

**If** [we make this change]
**Then** [this will happen]
**Because** [this is why we think it will happen]

## Opportunity/Problem

<!-- What user problem or opportunity are we addressing? -->

## Success Metrics

<!-- How will we measure if this hypothesis is true? -->
- Primary metric: [Metric] - target change [+X% or -X%]
- Secondary metric: [Metric]
- Guardrail metric: [Metric]

## Expected Impact

<!-- What's the potential impact if this hypothesis is true? -->

## Implementation Approach

<!-- How would we test this hypothesis? -->
- Test type: [A/B test | Feature flag | Experimentation]
- Sample size needed: [X]
- Test duration: [X days/weeks]
- Audience: [Target audience]

## ICE Score

**Impact:** [1-10] - How much would success move our metrics?
**Confidence:** [0-100%] - How confident are we in this hypothesis?
**Ease:** [1-10] - How easy would this be to implement and test?

**ICE Score:** [Overall score] = Impact × Confidence × Ease

## Risks & Constraints

<!-- What could go wrong? What are the constraints? -->
- Risk 1
- Risk 2
- Constraint 1

## Related Artifacts

<!-- Links to research, concepts, or requirements -->

## Test Results (When Available)

<!-- Fill in after testing -->
**Status:** [Proposed | Testing | Validated | Rejected]
**Results:** [Summary of results]
**Confidence:** [0-1.0]

```

### 7. Knowledge Source Template (knowledge-source.md)

**Use for:** knowledge-source artifacts

```markdown
---
type: knowledge-source
product: general
created: YYYY-MM-DD
skill: knowledge-library
skill_version: 1.0.0
tags: [research/user]
category: knowledge
platform: []
related: []
parent: null
children: []
status: active
confidence: 0.8
last_reviewed: YYYY-MM-DD
source_session: null
source_url: https://
source_type: article
trust_score: 0.7
publication_date: YYYY-MM-DD
---

# Knowledge Source: [Source Title]

<!-- Replace [Source Title] with the source name -->

## Source Information

**URL:** [Full URL to source]
**Source Type:** [Article | Research Report | Case Study | Benchmark | Tool | Video]
**Author/Publisher:** [Name]
**Publication Date:** YYYY-MM-DD
**Accessed Date:** YYYY-MM-DD

## Trust Score

**Overall Trust Score:** 0.7/1.0

**Scoring Factors:**
- Author credibility: [High | Medium | Low]
- Publication credibility: [High | Medium | Low]
- Recency: [Current | Recent | Outdated]
- Data/evidence quality: [Strong | Adequate | Weak]
- Bias potential: [Low | Medium | High]

## Summary

<!-- 3-4 sentence summary of the source content -->

## Key Takeaways

### Takeaway 1
<!-- Important insight or finding from the source -->

### Takeaway 2
<!-- Important insight or finding from the source -->

### Takeaway 3
<!-- Important insight or finding from the source -->

## Relevance to Your Product

<!-- Why is this source relevant to your product strategy? -->

## Direct Quotes (If Applicable)

> "Quote from source with relevance to your work"
> — Source, Author

## How to Use This Knowledge

<!-- Suggestions for how to apply this knowledge in product development -->

## Related Sources

<!-- Links to related knowledge sources in the vault -->

## Custom Fields

<!-- Add any additional metadata or categorization as needed -->

```

---

## MOC Templates

Maps of Content (MOCs) are auto-generated index pages that help navigate the vault. Two primary MOC templates are provided.

### Dashboard.md Template

The main navigation and overview page for the vault.

```markdown
---
type: moc
product: general
created: YYYY-MM-DD
status: active
---

# Product Manager Vault — Dashboard

Welcome to your Grow Product Manager Plugin vault. This dashboard provides navigation to all artifacts across research, strategy, analysis, and decisions.

## Quick Navigation

- **[Products](#products)** — Product-specific overviews and artifacts
- **[Research](#research)** — Competitive analysis, market research, UX studies
- **[Strategy & Concepts](#strategy--concepts)** — Product concepts and PRDs
- **[Analysis](#analysis)** — Metrics, A/B tests, post-release analysis
- **[Decisions](#decisions)** — Key product and technical decisions
- **[Meetings](#meetings)** — Meeting notes and summaries
- **[Projects](#projects)** — Active projects and initiatives
- **[Knowledge Library](#knowledge-library)** — Curated external sources
- **[Hypotheses](#hypotheses)** — Feature ideas and hypotheses (prioritized backlog)

## Products

Overview of artifacts organized by product:

### [[_MOC/Products/mobile-app]]
Latest artifacts: [Recent research], [Recent concepts], [Recent analyses]

### [[_MOC/Products/web]]
Latest artifacts: [Recent research], [Recent concepts], [Recent analyses]

### [[_MOC/Products/general]]
Cross-product research and strategy

---

## Research

Latest research across competitive, market, and UX dimensions.

### Competitive Analysis
- [[Research/competitive-analysis-stripe-checkout-2026-04-14]]
- [[Research/competitive-analysis-square-checkout-2026-04-10]]

### Market Research
- [[Research/market-research-bnpl-market-2026-04-12]]

### UX Benchmarks
- [[Research/ux-benchmark-mobile-checkout-2026-04-08]]

---

## Strategy & Concepts

Product concepts and strategic initiatives.

### Active Concepts
- [[Concepts/mobile-app/concept-one-click-checkout-2026-04-14]]
- [[Concepts/web/concept-guest-checkout-2026-04-10]]

---

## Analysis

Metrics, tests, and post-release analysis.

### Recent Metrics Reviews
- [[Analysis/mobile-app/metrics/metrics-review-march-2026-2026-04-14]]

### A/B Test Results
- [[Analysis/web/ab-tests/ab-test-results-checkout-mobile-2026-04-08]]

### Post-Release Analysis
- [[Analysis/web/post-release/post-release-guest-checkout-2026-04-10]]

---

## CJM & Anomalies

Customer Journey Map health and anomaly tracking.

### Latest Health Checks
- [[CJM/mobile-app/health-checks/cjm-health-check-q1-2026-summary-2026-04-14]]
- [[CJM/web/health-checks/cjm-health-check-q1-2026-summary-2026-04-12]]

### Critical Anomalies
- [[CJM/mobile-app/anomalies/funnel-anomaly-checkout-mobile-drop-2026-04-14]]

---

## Decisions

Key product and technical decisions.

### Recent Decisions
- [[Decisions/decision-postgres-vs-mongodb-2026-04-10]]
- [[Decisions/decision-feature-flag-strategy-2026-04-08]]

---

## Meetings

Recent meeting notes and summaries.

### Latest Meetings
- [[Meetings/meeting-notes-sprint-planning-2026-04-14]]
- [[Meetings/meeting-notes-stakeholder-update-2026-04-12]]

---

## Projects

Active projects and initiatives.

### Current Projects
- [[Projects/checkout-modernization/project-overview]]
- [[Projects/mobile-app-redesign/project-overview]]

---

## Knowledge Library

Curated external knowledge sources organized by category.

- **[Research & Studies](Knowledge/categories#research--studies)**
- **[Product Strategy](Knowledge/categories#product-strategy)**
- **[UX & Design](Knowledge/categories#ux--design)**
- **[Analytics & Metrics](Knowledge/categories#analytics--metrics)**
- **[Payment Systems](Knowledge/categories#payment-systems)**

**[View All Sources →](Knowledge/library-index.md)**

---

## Hypotheses

Feature ideas and hypotheses organized by funnel stage. See full prioritized backlog: [[Hypotheses/backlog]]

### High ICE Score (Ready to Test)
- [[Hypotheses/mobile-app/hypothesis-guest-checkout-2026-04-14]] (ICE: 78)
- [[Hypotheses/web/hypothesis-simplified-shipping-2026-04-12]] (ICE: 72)

### Medium Priority
- [[Hypotheses/mobile-app/hypothesis-one-click-checkout-2026-04-10]] (ICE: 65)

### Archive
- [[Hypotheses/archive/hypothesis-saved-payment-methods-2026-03-15]]

---

## Timeline

Key milestones and upcoming events.

- **Q1 2026 Review** — [[_MOC/Timeline#q1-2026]]
- **Q2 2026 Planning** — [[_MOC/Timeline#q2-2026]]

---

## Tags

Browse all artifacts by tag.

[[_MOC/Tags]]

---

## Recent Updates

Latest artifacts created or modified:
- 2026-04-14 — [[Hypotheses/mobile-app/hypothesis-guest-checkout-2026-04-14]]
- 2026-04-14 — [[Analysis/mobile-app/metrics/metrics-review-march-2026-2026-04-14]]
- 2026-04-12 — [[CJM/web/health-checks/cjm-health-check-q1-2026-summary-2026-04-12]]

```

### Product MOC Template

A template for per-product overview and navigation.

```markdown
---
type: moc
product: {ProductName}
created: YYYY-MM-DD
status: active
---

# {ProductName} — Overview

Complete view of all artifacts for {ProductName}, including research, strategy, analysis, and decisions.

## Product Overview

**Product Name:** {ProductName}
**Status:** [Active | Paused | Beta]
**Team:** [Team names]
**Last Updated:** YYYY-MM-DD

---

## Research

Research specific to {ProductName}:

### Competitive Analysis
- [[Research/{ProductName}/competitive-analysis-...]]

### Market Research
- [[Research/{ProductName}/market-research-...]]

### UX Benchmarks
- [[Research/{ProductName}/ux-benchmark-...]]

---

## Strategy & Concepts

Product concepts and PRDs:

### Active Concepts
- [[Concepts/{ProductName}/concept-...]]

### Concept Backlog
- [[Concepts/{ProductName}/concept-... (draft status)]]

---

## Customer Journey

CJM analysis and health:

### Full CJM Analysis
- [[CJM/{ProductName}/full-reports/cjm-analysis-...]]

### Funnel Health Checks
- [[CJM/{ProductName}/health-checks/cjm-health-check-...]]

### Detected Anomalies
- [[CJM/{ProductName}/anomalies/funnel-anomaly-...]]

---

## Feature Requirements

Feature specifications ready for development:

- [[Requirements/{ProductName}/requirements-...]]

---

## Analysis & Insights

Metrics, tests, and post-launch analysis:

### Metrics Reviews
- [[Analysis/{ProductName}/metrics/metrics-review-...]]

### A/B Test Results
- [[Analysis/{ProductName}/ab-tests/ab-test-results-...]]

### Post-Release Analysis
- [[Analysis/{ProductName}/post-release/post-release-...]]

---

## Hypotheses & Ideas

Feature hypotheses organized by priority:

### High Priority (ICE > 70)
- [[Hypotheses/{ProductName}/hypothesis-... (ICE: XX)]]

### Medium Priority (ICE 50-70)
- [[Hypotheses/{ProductName}/hypothesis-... (ICE: XX)]]

### Backlog & Archive
- [[Hypotheses/{ProductName}/hypothesis-... (draft status)]]
- [[Hypotheses/archive/hypothesis-...]]

---

## Decisions

Key decisions affecting {ProductName}:

### Product Decisions
- [[Decisions/{ProductName}/decision-...]]

### Technical Decisions
- [[Decisions/ADR/decision-...]]

---

## Meetings

Meeting notes related to {ProductName}:

- [[Meetings/meeting-notes-...]]

---

## Key Metrics

Latest performance data for {ProductName}:

| Metric | Value | Trend | Target |
|--------|-------|-------|--------|
| Conversion Rate | X.X% | ↑ | X% |
| Retention Rate | X% | → | X% |
| Revenue per User | $X.XX | ↓ | $X.XX |

---

## Upcoming Initiatives

Planned work for {ProductName}:

- [[Projects/{project-name}/project-overview]]

---

## Related Products

- [[_MOC/Products/{RelatedProductName}]]

```

---

## Summary

The Vault Schema defines a consistent, extensible structure for storing and organizing product artifacts in an Obsidian Vault. It includes:

- **Frontmatter Standard** — Base and type-specific fields for classification, relations, and lifecycle management
- **Type Taxonomy** — 16 artifact types mapped to skills, folders, and purposes
- **Tag Taxonomy** — Hierarchical tags for funnel, platform, metric, status, impact, research, and phase classification
- **Folder Structure** — Complete directory organization for {Vault}/{PluginFolder}/
- **Naming Convention** — Consistent {type}-{topic-slug}-{YYYY-MM-DD}.md pattern
- **Parsing Rules** — Tolerant parsing strategy for robustness and extensibility
- **Templates** — 7 complete artifact templates + MOC navigation templates

This schema is **referenced by `vault-protocol.md`** and enables automated indexing, filtering, linking, and publication of product artifacts across teams and systems.
