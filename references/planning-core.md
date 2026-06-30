# planning-core.md

> Shared planning-suite reference. Canonical entity model, marking convention, status normalization, goal map, and Development Flow. Consumed by all four skills of the suite. `roadmap-architect` — enforce; the rest — read.

---

## 1. Canonical hierarchy

```
Mission / Goal (Atlas Goal, e.g. EVOCO1-XX)
  └── Initiative / Direction (logical group; optionally — Jira issue type Initiative, level above Epic)
        └── Epic (Jira, hierarchy level 1)
              └── Feature (Confluence page with label + code in the name)
```

Story/Task-level issues are **out of roadmap scope** (they are the sprint-planning level, work-type inside a feature).

---

## 2. Marking convention (single source of truth for auto-assembly)

**Feature (Confluence page):**
- Name: `{PROJ}-{epic}.{feature}[.{sub}] - {human name}` (e.g. `SHOPEX-6610.5 - Q&A - YouTube in threads`).
- Labels: `feature`, `q{N}-{year}` (quarter where the work is run/planned; may be several), team label.
- Status field in the body: line `Status: {value}` from a controlled vocabulary (section 3).

**Epic (Confluence page + Jira issue):**
- Confluence name: `Epic - {PROJ}-{epic} - {name}`; labels `epic`, `q{N}-{year}`.
- Jira: label `q{N}-{year}` on the epic (for quarter readability from Jira).

**Parsing the code from the feature name:** `^(?:Epic - )?{PROJ}-(\d+)((?:\.\d+)*)\s*-\s*(.+)$` → `epicKey`, `featureCode`, `name`.

> If an entity is missing the quarter/goal/code — this is a **marking gap** (flag from `roadmap-architect`), not a reason to invent a link.

---

## 3. Status normalization (controlled vocabulary)

Feature/epic bodies contain various phrasings → reduce to 4 canons:

| Canon | Signals |
| --- | --- |
| `done` | Done, Готово, Закінчено, "launched at 100%", Closed |
| `in_progress` | in dev, Launched (rollout/A-B), rolling out, In dev |
| `planned` | Draft, Requirements, "not started", in preparation, To Do |
| `blocked` | "waiting for details", blocked, explicit obstacles |

The epic's Jira status is taken from `statusCategory.key`: `done`→done, `indeterminate`→in_progress, `new`→planned.

---

## 4. Goal map (epic → Goal)

Atlas Goals are not queryable via MCP → keep the map in local-context (Planning → goal_map). Example (FET):

| Goal | Epics |
| --- | --- |
| EVOCO1-25 (Conversion/catalog/brands) | 10272, 5783, 4950, 10452, 7930, 11300, 11240 |
| EVOCO1-3 (Product reviews) | 3080, 11300 |
| EVOCO1-22 (Q&A) | 6610 |
| EVOCO1-23 (Product comparison) | (comparison epic) |
| EVOCO1-24 (New segment) | 4750 |
| — Feedback Ecosystem | 3930, 9534, 9557, 9294 |

---

## 5. Development Flow (the team's development flow)

Collected at onboarding (`plugin-configurator` → Planning setup), stored in local-context → Planning → development_flow. Structure:

```yaml
development_flow:
  work_types: [Requirements, Design, BE, Analytics, Client, QA, Release]
  sequence:                      # DAG edges: prerequisite → successor
    Design: [Requirements]
    BE: [Design]
    Analytics: [Design]
    Client: [BE, Analytics]
    QA: [Client]
    Release: [QA]
  parallel: [[BE, Analytics]]    # what runs simultaneously
  ready_threshold: [on review, in test, ready for test, done, closed]
  platform_notes: "iOS/Android client depend on BE"
  exceptions: "..."              # free-form input of team specifics
```

Consumers: `sprint-planning` (readiness/violations), `project-planning` (macro dependencies), `dependency-model.md` (machinery). `update config` updates it — detection adjusts automatically.

---

## 6. Quality / caveats

- Only marked entities go into auto-assembly; gaps — surface, do not infer.
- Conventions (names/labels/statuses/flow) are overridden in local-context; do not hardcode in skills.
- Features in any artifact — as a list of `code — name`, not bare numbers.
- Mark marking recommendations "pending PM confirmation".
