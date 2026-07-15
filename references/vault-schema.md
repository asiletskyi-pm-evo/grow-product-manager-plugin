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
revisit_by: date (when this decision should be re-examined, YYYY-MM-DD; optional)
```

> `revisit_by` is a frontmatter field, not prose: `focus-advisor` surfaces overdue revisits as a tactical signal (`focus-signals.md`), and it can only do that by filtering the field. It lived only in the decision body's "Consequences" section until v2.1.1, so that signal was a permanent false negative. `deadline` is when the decision had to be *made*; `revisit_by` is when it should be *re-examined*.

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

#### focus-brief

Artifact type for PM focus briefs produced by `focus-advisor`.

```yaml
subtype: string (daily-brief|tactical-brief|strategy-memo)
mode: string (now|tactics|strategy)
headless: boolean (true if produced by a scheduled run)
focuses_proposed: int
focuses_chosen: int (0 until the PM reacts; updated from journal)
signals_sources: string[] (mail, calendar, meetings, jira, cadence, metrics)
```


#### feedback-triage

Artifact type for clustered feedback triage runs produced by `feedback-triage`.

```yaml
period: string (e.g., "2026-06" or "2026-06-01 to 2026-06-30")
segment: string (buyers|sellers|both)
sources_count: int (number of intake sources)
items_total: int (feedback items received)
items_usable: int (after dedupe/cleaning)
top_pain_score: float (pain score of the #1 theme)
baseline_ref: string (wikilink to the previous triage of the same segment, if any)
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

The Grow Product Manager Plugin defines 33 artifact types, each with a specific purpose, source skill, and folder location.

> **This table is the single source of truth for vault layout.** `vault-protocol.md` (save/init) and `obsidian-setup-guide.md` (setup smoke tests) conform to it, not the other way round. A type that is not listed here cannot be saved — `vault_save` resolves its folder from TYPE_FOLDER_MAP below, so an unlisted type has no destination. When a skill starts producing a new artifact type, add the row **and** the map entry in the same change; `testing/skill_lint.py` → `vault-types` enforces this.

**Path composition (one rule):** `{vault}/{TYPE_FOLDER_MAP[type]}/{key_slug}/{filename}` — the map gives the area path, and the **key** is always the last folder level.

The key is whichever entity you retrieve the artifact *by*:

| Contour | Key | Example |
|---------|-----|---------|
| Product artifacts (Research, CJM, Concepts, Requirements, …) | `{product_slug}` | `Research/mobile-app/competitive-analysis-checkout-2026-04-14.md` |
| **People artifacts** (goals, reports, 1-1, reviews, …) | `{person_slug}` | `People/goals/firstname-lastname/goal-letter-2026H1.md` |

People artifacts key by person because that is the access pattern the contour is built on: Step P loads everything known about **a person**, and a person is not scoped to a product — one analyst has one goal letter per period, not one per product. Product-keying them would scatter a single person's history across every product folder and make Step P a cross-folder search. The person profile itself stays `People/<slug>.md` (addressed by name, not by date), with the roster index at `People/_roster.md`.

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
| diagram | diagram-prototyper | Diagrams/ | Diagram, prototype, or infographic (source + export link) |
| task-breakdown | task-creator | Projects/task-breakdowns/ | Feature → Jira tasks decomposition record with links |
| ops-report | product-reporter | Reports/ops/ | Sprint/quarter/initiative/member operational report |
| roadmap | planning suite (sprint-/quarterly-/project-planning, roadmap-architect) | Roadmaps/ | Sprint plan, quarterly roadmap, project arc, or structure tree (subtype in frontmatter) |
| focus-brief | focus-advisor | Focus/ | PM focus brief (daily/tactical/strategy — subtype in frontmatter) with chosen focuses and chains |
| feedback-triage | feedback-triage | Research/feedback/ | Clustered feedback themes with pain scores and trends (baseline for next run) |
| presentation | design-bridge | Presentations/ | Rendered deck (.pptx) — subtype in frontmatter |
| prototype | design-bridge | Prototypes/ | Lo-fi/mid-fi/hi-fi prototype (own or toolkit-delegated) |
| handoff | design-bridge | Handoffs/ | Design → dev handoff package |
| vacancy-profile | hiring-designer | Hiring/ | Role design + vacancy profile + offer draft |

#### People-contour types (highest-sensitivity tier)

Everything about a person lives under `People/` — one folder, one sensitivity boundary. These artifacts are **vault/local only**: never Confluence, never Jira, never external LLMs (`data-policy.md` → People data). `vacancy-profile` sits outside `People/` on purpose — a vacancy is a role, not yet a person.

| Type | Skill Source | Folder | Description |
|------|--------------|--------|-------------|
| people | People contour (Step P) | People/ | Person profile — D-type, delegation levels, goals, cadence, GTD-index, signals (`people-context-protocol.md`) |
| goal-letter | goal-setter | People/goals/ | SMARTCBP goal letter for a person |
| report-3t5f | product-reporter | People/reports/ | 3T5F goal report for a person or direction |
| one-on-one-notes | one-on-one | People/1-1/ | 1-1 notes, signals, ARCV follow-up |
| performance-review | performance-review | People/reviews/ | Structured review against goals + GTD + D-type |
| offboarding-plan | offboarding-guide | People/offboarding/ | Four-meeting offboarding plan and follow-ups |
| delegation-audit | delegation-coach | People/delegation/ | 7-levels audit + S1→S4 hand-off plan |

#### Design delivery marker (design-bridge)

When `design-bridge` delegates hi-fi work to an external design toolkit (Step 0.5, per `design-toolkit-protocol.md`), the returned artifact is saved under the `prototype` / `handoff` types above. It carries these `extra_frontmatter` keys so delegated deliverables are distinguishable:

- `design_delivery: true`
- `toolkit_id: <id>` — which declared toolkit produced it
- `toolkit_returns: [figma_url?, branch?, files?]` — what came back

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
  "project-overview": "Projects/",
  "diagram": "Diagrams/",
  "task-breakdown": "Projects/task-breakdowns/",
  "ops-report": "Reports/ops/",
  "roadmap": "Roadmaps/",
  "focus-brief": "Focus/",
  "feedback-triage": "Research/feedback/",
  "presentation": "Presentations/",
  "prototype": "Prototypes/",
  "handoff": "Handoffs/",
  "vacancy-profile": "Hiring/",

  "people": "People/",
  "goal-letter": "People/goals/",
  "report-3t5f": "People/reports/",
  "one-on-one-notes": "People/1-1/",
  "performance-review": "People/reviews/",
  "offboarding-plan": "People/offboarding/",
  "delegation-audit": "People/delegation/"
}
```

> The `people` profile itself is the one artifact addressed by name rather than by date: `People/<slug>.md` (plus the roster index `People/_roster.md`), because Step P looks it up per person. Every other People type follows `{folder}/{person_slug}/{filename}` — see "Path composition" above for why the People key is the person, not the product.

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
│   ├── health-checks/
│   │   └── {product}/
│   │       └── cjm-health-check-*.md
│   ├── anomalies/
│   │   └── {product}/
│   │       └── funnel-anomaly-*.md
│   └── full-reports/
│       └── {product}/
│           └── cjm-analysis-*.md
│
├── Concepts/                          # Product concepts and PRDs
│   └── {product}/
│       └── concept-*.md              (draft status stays in frontmatter, not a folder)
│
├── Requirements/                      # Feature requirements
│   └── {product}/
│       └── requirements-*.md
│
├── Analysis/                          # Product analysis and metrics
│   ├── metrics/
│   │   └── {product}/
│   │       └── metrics-review-*.md
│   ├── ab-tests/
│   │   └── {product}/
│   │       └── ab-test-results-*.md
│   └── post-release/
│       └── {product}/
│           └── post-release-*.md
│
├── Hypotheses/                        # Feature hypotheses and ideas
│   ├── {product}/
│   │   └── hypothesis-*.md           (archived status stays in frontmatter)
│   └── backlog.md
│       (Prioritized hypothesis backlog with links to hypothesis artifacts)
│
├── Meetings/                          # Meeting notes and summaries
│   └── {product}/
│       └── meeting-notes-*.md
│
├── Decisions/                         # Product and technical decisions
│   ├── {product}/
│   │   └── decision-*.md
│   └── ADR/
│       └── decision-*.md (Architecture Decision Records)
│
├── Knowledge/                         # Knowledge library and sources
│   ├── sources/
│   │   └── {product}/
│   │       └── knowledge-source-*.md
│   ├── library.md
│   │   (Index of all knowledge sources — created by knowledge-library)
│   └── categories.md
│       (Knowledge source categories and trust scores)
│
├── Projects/                          # Project overviews and tracking
│   ├── {product}/
│   │   └── project-overview-*.md
│   └── task-breakdowns/
│       └── {product}/
│           └── task-breakdown-*.md
│
├── Reports/                           # Operational reports
│   └── ops/
│       └── {product}/
│           └── ops-report-*.md
│
├── Roadmaps/                          # Planning suite output (subtype in frontmatter)
│   └── {product}/
│       └── roadmap-*.md
│
├── Focus/                             # focus-advisor briefs
│   └── {product}/
│       └── focus-brief-*.md
│
├── Diagrams/                          # diagram-prototyper output
│   └── {product}/
│       └── diagram-*.md
│
├── Presentations/                     # design-bridge decks
│   └── {product}/
│       └── presentation-*.md
│
├── Prototypes/                        # design-bridge prototypes
│   └── {product}/
│       └── prototype-*.md
│
├── Handoffs/                          # design-bridge dev handoffs
│   └── {product}/
│       └── handoff-*.md
│
├── Hiring/                            # hiring-designer vacancy profiles
│   └── {product}/
│       └── vacancy-profile-*.md
│
├── People/                            # HIGHEST-SENSITIVITY — local/vault only, never published
│   ├── _roster.md                     (one line per person → [[People/<slug>]])
│   ├── <slug>.md                      (person profile — type: people, Step P)
│   ├── goals/                         # keyed by PERSON, not product — see Path composition
│   │   └── {person}/
│   │       └── goal-letter-*.md
│   ├── reports/
│   │   └── {person}/
│   │       └── report-3t5f-*.md
│   ├── 1-1/
│   │   └── {person}/
│   │       └── one-on-one-notes-*.md
│   ├── reviews/
│   │   └── {person}/
│   │       └── performance-review-*.md
│   ├── offboarding/
│   │   └── {person}/
│   │       └── offboarding-plan-*.md
│   └── delegation/
│       └── {person}/
│           └── delegation-audit-*.md
│
└── Templates/                         # template-library storage (see template-protocol.md)
    ├── _registry.json                 (template registry — the resolution index)
    ├── _partials/
    ├── _System/
    ├── _archive/
    ├── user-global/
    │   └── {artifact_type}/
    └── {product}/
        └── {artifact_type}/
```

> **Folder order mirrors TYPE_FOLDER_MAP.** Where the map carries a subfolder (`CJM/full-reports/`, `Analysis/ab-tests/`, `Reports/ops/`), the product is the level **below** it — never above. Lifecycle status (`draft`, `archived`, `superseded`) lives in frontmatter and is filtered by search; it is not a folder.

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
related: ["[[Analysis/metrics/mobile-app/metrics-review-q1-2026-2026-04-14.md]]"]
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

> **Removed in v2.1.1.** This section documented seven flat master template files
> (research.md, concept.md, …) with a `[placeholder]` + HTML-comment convention —
> the pre-v2.0 template system that `references/template-protocol.md` replaced with the
> `templates/built-in/` tree, `builtin://` resolution and Handlebars variables.
> `vault-protocol.md` → `vault_init` already forbids writing those files, so this
> section described a layout the plugin must not create, in a document declared the
> single source of truth for vault layout.
>
> Templates live in `{storage_root}/Templates/` and are owned by `template-library`.
> For the artifact frontmatter each type needs, see **Frontmatter Standard** above.

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
- [[Research/mobile-app/competitive-analysis-stripe-checkout-2026-04-14]]
- [[Research/mobile-app/competitive-analysis-square-checkout-2026-04-10]]

### Market Research
- [[Research/mobile-app/market-research-bnpl-market-2026-04-12]]

### UX Benchmarks
- [[Research/mobile-app/ux-benchmark-mobile-checkout-2026-04-08]]

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
- [[Analysis/metrics/mobile-app/metrics-review-march-2026-2026-04-14]]

### A/B Test Results
- [[Analysis/ab-tests/web/ab-test-results-checkout-mobile-2026-04-08]]

### Post-Release Analysis
- [[Analysis/post-release/web/post-release-guest-checkout-2026-04-10]]

---

## CJM & Anomalies

Customer Journey Map health and anomaly tracking.

### Latest Health Checks
- [[CJM/health-checks/mobile-app/cjm-health-check-q1-2026-summary-2026-04-14]]
- [[CJM/health-checks/web/cjm-health-check-q1-2026-summary-2026-04-12]]

### Critical Anomalies
- [[CJM/anomalies/mobile-app/funnel-anomaly-checkout-mobile-drop-2026-04-14]]

---

## Decisions

Key product and technical decisions.

### Recent Decisions
- [[Decisions/mobile-app/decision-postgres-vs-mongodb-2026-04-10]]
- [[Decisions/mobile-app/decision-feature-flag-strategy-2026-04-08]]

---

## Meetings

Recent meeting notes and summaries.

### Latest Meetings
- [[Meetings/mobile-app/meeting-notes-sprint-planning-2026-04-14]]
- [[Meetings/mobile-app/meeting-notes-stakeholder-update-2026-04-12]]

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

**[View All Sources →](Knowledge/library.md)**

---

## Hypotheses

Feature ideas and hypotheses organized by funnel stage. See full prioritized backlog: [[Hypotheses/backlog]]

### High ICE Score (Ready to Test)
- [[Hypotheses/mobile-app/hypothesis-guest-checkout-2026-04-14]] (ICE: 78)
- [[Hypotheses/web/hypothesis-simplified-shipping-2026-04-12]] (ICE: 72)

### Medium Priority
- [[Hypotheses/mobile-app/hypothesis-one-click-checkout-2026-04-10]] (ICE: 65)

### Archive
- [[Hypotheses/mobile-app/hypothesis-saved-payment-methods-2026-03-15]] (status: archived)

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
- 2026-04-14 — [[Analysis/metrics/mobile-app/metrics-review-march-2026-2026-04-14]]
- 2026-04-12 — [[CJM/health-checks/web/cjm-health-check-q1-2026-summary-2026-04-12]]

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
- [[CJM/full-reports/{ProductName}/cjm-analysis-...]]

### Funnel Health Checks
- [[CJM/health-checks/{ProductName}/cjm-health-check-...]]

### Detected Anomalies
- [[CJM/anomalies/{ProductName}/funnel-anomaly-...]]

---

## Feature Requirements

Feature specifications ready for development:

- [[Requirements/{ProductName}/requirements-...]]

---

## Analysis & Insights

Metrics, tests, and post-launch analysis:

### Metrics Reviews
- [[Analysis/metrics/{ProductName}/metrics-review-...]]

### A/B Test Results
- [[Analysis/ab-tests/{ProductName}/ab-test-results-...]]

### Post-Release Analysis
- [[Analysis/post-release/{ProductName}/post-release-...]]

---

## Hypotheses & Ideas

Feature hypotheses organized by priority:

### High Priority (ICE > 70)
- [[Hypotheses/{ProductName}/hypothesis-... (ICE: XX)]]

### Medium Priority (ICE 50-70)
- [[Hypotheses/{ProductName}/hypothesis-... (ICE: XX)]]

### Backlog & Archive
- [[Hypotheses/{ProductName}/hypothesis-... (draft status)]]
- [[Hypotheses/{ProductName}/hypothesis-...]] (status: archived)

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
- **Type Taxonomy** — 33 artifact types mapped to skills, folders, and purposes
- **Tag Taxonomy** — Hierarchical tags for funnel, platform, metric, status, impact, research, and phase classification
- **Folder Structure** — Complete directory organization for {Vault}/{PluginFolder}/
- **Naming Convention** — Consistent {type}-{topic-slug}-{YYYY-MM-DD}.md pattern
- **Parsing Rules** — Tolerant parsing strategy for robustness and extensibility
- **Templates** — 7 complete artifact templates + MOC navigation templates

This schema is **referenced by `vault-protocol.md`** and enables automated indexing, filtering, linking, and publication of product artifacts across teams and systems.
