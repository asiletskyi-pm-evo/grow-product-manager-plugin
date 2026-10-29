# vocabulary-sets.md

> Shared reference (since v3.6.0) — the read-only **vocabulary sets** that `role_defaults.vocabulary_set` selects (`references/role-profiles.md` §2b maps each profile to one set; the `pm` fallback maps to `core`): how a skill words the headings and option labels it writes itself. Lowest precedence — the user's glossary always wins, and a set never rewrites user text.

## Rules

1. **Scope.** A set words only text the skill writes itself: question headings, option labels and the section headings of the skill's own structure. It never touches user text, quoted sources, the headings of a template, metric or event names, Jira / Confluence fields, or the field names of a return payload.
2. **Precedence.** Product glossary (`glossary/{product_id}.yaml`) > org glossary (`glossary/_org.yaml`) > vocabulary set > the skill's generic wording. Only `approved` glossary entries count; a set wording that a glossary entry lists under `avoid` is dropped for the generic term.
3. **Wording only — synonyms, never a narrower or different meaning.** A set never adds, removes or reorders a question or an option (a skill may reorder options in its own step — e.g. design-bridge's design defaults, `role-profiles.md` §6 — but that is the skill, never the set), never changes what an option does, and never touches a score, a check or a verdict. The value an option passes on stays the generic term — only the label changes.
4. **Language.** The sets are written in English. Render the preferred wording in `user.language`; where it has no natural equivalent, keep the generic term. A set never chooses the output language.
5. **Missing term.** A term the active set does not list keeps its generic wording — sets never fall through to one another, and an unknown set name counts as `core`.
6. **Read-only.** Sets ship with the plugin. A team changes its wording through the glossary (Glossary Manage), never by editing a set; a set word never becomes a glossary entry or a Glossary Lint replacement. A hat (`role-profiles.md` §4) swaps the set for one run only.
7. **No-user runs.** A scheduled or headless run words everything with `core`, exactly as before v3.6.0; a skill invoked only for a return payload keeps its payload generic — the caller words what the user sees.

## `core` — the identity set

Every generic term keeps its own wording, the wording used before v3.6.0. A user without a role sees no change.

## `leader`

| Generic term | Preferred wording |
|---|---|
| features | bets / objectives |
| ideas | bets |
| metric | metric (key result) |
| result | outcome against the objective |
| quick wins | low-cost bets |

## `design`

| Generic term | Preferred wording |
|---|---|
| screen | screen / flow step |
| features | flows |
| ideas | explorations |
| problem | user task / pain point |
| result | usability finding |

## `data`

| Generic term | Preferred wording |
|---|---|
| result | effect with confidence interval |
| metric | metric as defined in the metric dictionary |
| users | cohort / segment |
| ideas | testable hypotheses |
| risks | risks (incl. guardrail metrics) |

## `research`

| Generic term | Preferred wording |
|---|---|
| research | study |
| users | participants |
| ideas | opportunities |
| problem | user need |
| result | finding with its confidence |

## `engineering`

| Generic term | Preferred wording |
|---|---|
| features | epics / deliverables |
| ideas | candidate work items |
| effort | estimate against capacity |
| risks | risks (incl. technical risks) |
| quick wins | low-effort items |

## `business`

| Generic term | Preferred wording |
|---|---|
| features | investments |
| ideas | bets with a business case |
| metric | metric (business target) |
| result | business outcome (revenue / margin) |
| effort | investment (cost) |
