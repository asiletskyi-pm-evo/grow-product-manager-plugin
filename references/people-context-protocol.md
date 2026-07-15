# People Context Protocol (Step P)

This document defines how the plugin's **People-contour** skills (`goal-setter`, `one-on-one`, `performance-review`, `hiring-designer`, `offboarding-guide`, `delegation-coach`) read and maintain a persistent profile for each member of the PM's team. It is the People-contour analogue of `local-context-protocol.md` (Step 0): where Step 0 loads *product/org* context, **Step P** loads *person* context.

Profiles accumulate knowledge about a person **between sessions** — their situational-leadership type, delegation levels, active goals, reporting cadence, 1-1 history, GTD-index trend, and career signals — so every people-skill starts from what is already known instead of re-asking.

> **Data sensitivity:** person profiles are the **highest-sensitivity** category in the plugin. They live **locally / in the vault only** and are never published to Confluence/Jira or sent to external LLM services. See `references/data-policy.md` → "People data".

---

## Storage

Person profiles are stored as one Markdown file per person:

1. **Vault area `People/<name>.md`** — primary, when a vault is configured (`vault_level ≥ L1`). Levels L0/L1/L2 behave exactly as in `references/vault-protocol.md`.
2. **`~/.grow-pm/people/<slug>.md`** — fallback when no vault is configured (`vault_level == L0`), so the People-contour works standalone.

`<slug>` is the kebab-cased name (`Firstname Lastname` → `firstname-lastname`). A team **roster index** lives at `People/_roster.md` (vault) or `~/.grow-pm/people/_roster.md` — one line per person: `- [[People/firstname-lastname]] — Analyst, D3, reports weekly`.

The `People` vault area and default cadences are configured by `plugin-configurator` → **People-setup** mode and stored in `local-context.md` → `people` section (see `skills/plugin-configurator/references/context-schema.md`).

---

## Profile schema

YAML frontmatter + free-form sections:

```yaml
---
type: people
name: "Firstname Lastname"
slug: firstname-lastname
role: "Product Analyst"
team: "Core"
manager: "<manager-name>"
joined: 2025-03-01
# Situational leadership (people-frameworks.md → Hersey-Blanchard)
d_type: D3                      # D1 | D2 | D2.1 | D3 | D3.1 | D4
d_history:                      # transitions over time
  - { date: 2025-03-01, type: D1, note: "onboarding" }
  - { date: 2025-09-01, type: D3, note: "confidence dip on new area" }
recommended_style: S3           # S1 | S2 | S3 | S4 (derived from d_type)
# Delegation (people-frameworks.md → 7 levels of Appelo), per zone
delegation:
  - { zone: "A/B readouts",      level: 6, target: 7 }
  - { zone: "funnel dashboards", level: 4, target: 6 }
# Goals
active_goal_letter: "[[People/goals/firstname-lastname/goal-letter-2026H1]]"   # link to SMARTCBP goal letter
goal_methodology: SMARTCBP      # SMARTCBP | OKR
# Reporting (reporting-3t5f.md)
reporting:
  cadence: weekly               # weekly | biweekly | monthly
  last_report: 2026-07-11
  last_report_ref: "[[People/reports/firstname-lastname/report-3t5f-2026-07-11]]"
  forecast_qa: 92               # last Forecast Quota Attainment, %
# 1-1 cadence and history
one_on_one:
  cadence: biweekly
  last: 2026-07-07
  history:
    - { date: 2026-07-07, followup_ref: "[[People/1-1/firstname-lastname/one-on-one-notes-2026-07-07]]" }
# GTD-index trend (people-frameworks.md → GTD-index)
gtd_index:
  - { period: "Sprint 41", value: 0.72 }
  - { period: "Sprint 42", value: 0.81 }
# Signals — free text, updated by one-on-one / performance-review
signals:
  motivation: "high; wants to move toward analytics lead"
  risks: "occasional overload at sprint close"
  career: "interested in mentoring juniors"
updated: 2026-07-14
---

## Summary
2–4 sentences: who this person is, current D-type and why, headline goal, latest trajectory.

## Goals
Current SMARTCBP goals (or link to the goal letter). One line each.

## 1-1 log
Reverse-chronological: date → key signals surfaced → link to the ARCV follow-up.

## Development notes
Style plan (S1→S4 evolution), delegation transfer plan, growth items.
```

Only `name`, `role`, and `updated` are strictly required. Everything else is filled incrementally as the skills gather it — a fresh profile with just those three fields is valid.

---

## Step P — Load / create person profile (MANDATORY for People-contour skills)

Runs **after Step 0** (local-context) and **before** the skill's own work, wherever a skill operates on a specific person.

### P-a. Resolve the person

1. If the user named the person → resolve to their profile file (exact slug, then fuzzy name match against the roster).
2. If the skill operates on the whole team (e.g. `one-on-one` headless "who is overdue") → load the roster and iterate.
3. If no person is named and the skill needs one → ask via `AskUserQuestion`, pre-filling names from the roster.

### P-b. If the profile exists → read and parse

Read the profile. Extract `d_type`, `recommended_style`, `delegation`, `active_goal_letter`, `reporting`, `one_on_one` history, `gtd_index` trend, and `signals`. These become inputs to the skill (e.g. `one-on-one` prep tunes tone to `d_type`; `task-creator` sets the "how" depth from `d_type`; `performance-review` reads `gtd_index` and `forecast_qa`).

### P-c. If the profile does NOT exist → offer to create

Do not hard-stop. Offer:

> "I don't have a profile for **{name}** yet. Want me to create one now (I'll fill what we learn during this session)? [Create / Skip for this session]"

- **Create** → write a minimal profile (`name`, `role`, `updated`, plus whatever the current request already reveals), add a roster line, then continue.
- **Skip** → continue in-session without persistence; warn that cross-session accumulation won't happen.

### P-d. Update at the end (MANDATORY when the profile exists)

After the skill delivers its output, write back whatever it learned — new `d_type` transition, delegation-level change, a 1-1 log entry + follow-up link, a new `gtd_index` datapoint, updated `signals`, a new `active_goal_letter`. Always bump `updated`. Append, don't overwrite history arrays.

**Every profile write is gated — show the diff, save on confirmation.** No exceptions: a profile records a judgement about a person (their D-type, their trend, their signals), and the manager owns that judgement. The one-line diff costs a second; a silently-persisted wrong `d_type` quietly steers every later 1-1, review, and delegation decision.

> Until v2.0.2 this rule read "gated for `performance-review` and `offboarding-guide`; silent-with-notice for the others", while `goal-setter`, `one-on-one` and `delegation-coach` each declared a gated write in their own SKILL.md. The skills were right; the protocol is now aligned to them.

---

## Which People-skill reads/writes what

| Skill | Reads | Writes |
|-------|-------|--------|
| `goal-setter` | d_type (goal depth), reporting cadence | `active_goal_letter`, `goal_methodology`, commitment status |
| `one-on-one` | d_type, active goals, 1-1 history, gtd trend, signals | 1-1 log entry, follow-up ref, updated signals, d_type transition |
| `performance-review` | goals, forecast_qa, gtd_index, d_type, 1-1 signals | d_type, recommended_style, delegation targets, review artifact link |
| `hiring-designer` | — (creates a new profile on hire) | new profile: curator, S1 style, probation = offer goals |
| `offboarding-guide` | goals + reports (evidence gate), d_type, 1-1 history | offboarding state (local only), d_type → "leaving" |
| `delegation-coach` | d_type, gtd_index, delegation zones | delegation levels + transfer plan |
| `product-reporter` (goal-report) | `active_goal_letter`, reporting cadence, forecast_qa history | `reporting.last_report`, `last_report_ref`, `forecast_qa` |

`product-reporter` is not a People-contour skill, but its `goal-report` mode reports **on a person against their goal**, so it runs Step P and writes the reporting fields back. Its goal-report output is People-data: `People/reports/`, vault/local only, never Confluence.

Cross-contour readers: `task-creator` reads `d_type` (how-depth); `sprint-planning` reads `d_type`/`delegation` (assignee fit) and writes a `gtd_index` datapoint from carryover; `focus-advisor` reads roster + `one_on_one`/`reporting` cadence for manager-rhythm signals. These are **read-mostly** — they never create profiles, they use them if present.

---

## Rules

- **Never fabricate** a d_type, GTD value, or signal — record only what was observed or what the PM stated. Unknown fields stay empty.
- **History is append-only**: corrections are new dated entries, never silent edits (mirrors the experiment-tracker lifecycle rule).
- **Consent to the record**: profiles describe working performance, not the person's worth. Keep language factual (see `communication-frameworks.md` → NVC).
- **Non-blocking**: any profile read/write error is reported but must not abort the skill's main workflow.
- **Locality**: profiles never leave the vault/local storage — see data-policy.

---

## References
- `references/local-context-protocol.md` — Step 0, and the `people` config section
- `references/people-frameworks.md` — D1–D4/S1–S4, 7 delegation levels, GTD-index
- `references/goal-frameworks.md` — SMARTCBP goal letters referenced by `active_goal_letter`
- `references/reporting-3t5f.md` — the reports referenced by `reporting`
- `references/vault-protocol.md` + `references/vault-schema.md` — `People/` area storage
- `references/data-policy.md` — People-data confidentiality tier
