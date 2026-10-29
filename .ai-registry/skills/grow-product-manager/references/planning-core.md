# planning-core.md

> Shared planning-suite reference. Canonical entity model, marking convention, status normalization, goal map, and Development Flow. Consumed by all four skills of the suite. `roadmap-architect` — enforce; the rest — read.

---

## 1. Canonical hierarchy

```
Mission / Goal (Atlas Goal, e.g. PROJ-XX)
  └── Initiative / Direction (logical group; optionally — Jira issue type Initiative, level above Epic)
        └── Epic (Jira, hierarchy level 1)
              └── Feature (Confluence page with label + code in the name)
```

Story/Task-level issues are **out of roadmap scope** (they are the sprint-planning level, work-type inside a feature).

---

## 2. Marking convention (single source of truth for auto-assembly)

**Feature (Confluence page):**
- Name: `{PROJ}-{epic}.{feature}[.{sub}] - {human name}` (e.g. `PROJ-1234.5 - Q&A - answer threads`).
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

Atlas Goals are not queryable via MCP → keep the map in local-context (Planning → goal_map). Example (illustrative — real values live only in local-context.md):

| Goal | Epics |
| --- | --- |
| PROJ-10 (Conversion) | 101, 102, 103 |
| PROJ-11 (Reviews) | 104, 105 |
| PROJ-12 (Q&A) | 106 |
| PROJ-13 (Comparison) | (comparison epic) |
| PROJ-14 (New segment) | 107 |
| — Some initiative | 108, 109 |

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
- **Tacit organisational context (since v3.8.0, `pm-mental-model.md` P10; `data-integrity-protocol.md` 6c).** A planning input that needs context found neither in Jira nor in `local-context.md` — a goal missing from the goal map, an unrecorded dependency, unconfigured capacity, a commitment made outside Jira — keeps its existing "pending PM/TL confirmation" marker, which names whom to ask (the PM, the TL, or the owner of the goal or commitment). That marker is the planning hand-back, and the item it marks is `assumed` (`pm-mental-model.md` §4): the marker reads as its label, so no second label, no new section and no question are added. For `judgment-points.md` §3 the marked item is an `assumed` input — named in `most sensitive to`, never a frontier cap.

## 7. Altitude views — Now / Next / Later (since v3.6.0)

A view over the objects above — no new label, field or status, so marking (§2) and gap detection are unchanged.

| View | Maps to | Default depth |
|------|---------|---------------|
| **Now** | the current `q{N}-{year}` label, the sprint plan | features and epics |
| **Next** | the next `q{N}-{year}` label, the quarterly plan | epics and initiatives |
| **Later** | initiatives and goals without a quarter label, the project arc | initiatives and goals |

- `role_defaults.planning_view` (`references/role-profiles.md` §2b): `rollup` shows goals → initiatives first (Later / Next) and drills down on request; `slice` shows the delivery slice first (Now) and rolls up on request. Only the order, the depth and the tech-debt display row (`capacity-model.md` §7) change — the numbers, the capacity gate and the checks are the same.
- No `planning_view` (pm, no or unconfirmed role, automated runs): every planning skill keeps its pre-v3.6.0 order, depth and table rows.
- `role_defaults.horizon` sets project-planning's default arc window; quarterly-planning stays one quarter and sprint-planning one sprint.

## 8. Pre-mortem and kill criteria in the planning suite (since v3.9.0)

P4 of `pm-mental-model.md`, rules in `judgment-points.md` §7, formats in `roadmap-artifacts.md` §8. Derived, never asked; a `⚠️ TBD` cell is counted, not filled by a question.

- **Where it renders — two steps only:** the quarter plan at scope lock (`quarterly-planning`, plan and full modes) and a new mission, initiative or — with goal or outcome text in the request — epic at `roadmap-architect` onboard.
- **Where it never renders:** a `project-planning` arc in any mode (its replan only reads criteria back); a sprint plan; the roadmap-architect tree, gap report or `map` edits; a feature or an existing entity; the quarterly retro; a quarterly refresh, which keeps an existing section verbatim and never adds one. No role, hat or `planning_view` changes this.
- **Marked inputs.** A cause that rests on an item §6 marks keeps that marker as its label — no second label, no extra hand-back line, no question.
- **Read-back.** The quarterly retro reads the previous quarter plan's kill criteria; a project-planning replan reads those on the mission, initiative or epics in its scope and the current quarter plan's criteria for the focuses its arc touches. Each criterion whose date has passed shows as fired or not fired, with the value that decided it, or as not measurable — next to the plan-vs-actual or the drift.
  - Only data the step already fetched counts — the retro's Step 2, the replan's R1–R4. Anything else, and a `⚠️ TBD` threshold or date, reads not measurable: never a new fetch, delegation or question.
  - A plan or entity without kill criteria (before v3.9.0, or the section deleted) shows nothing.
  - Fired criteria join the step's existing decision-log offer as one batch, only when that offer is made — they never open an offer on their own.
