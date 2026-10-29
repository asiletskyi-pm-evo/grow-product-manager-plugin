# Spec readiness — Step 1 (since v3.9.0)

> Part of `task-creator`. Loaded in Step 1 when the source may be a feature spec. The six elements, the line format and the AC-by-id rule are defined once in `references/artifact-style-gate.md` → Spec readiness; this file says where task-creator finds them. The check never blocks, is never asked and never edits the spec.

## When it runs

Decided by the shape of the source, not by who called the skill:

| Source | Shown |
|---|---|
| A feature spec: a requirements page (written by `requirements-creator` or the team's own), an A/B-test spec, an AI-feature spec | `Spec readiness: n/6 — missing: …` |
| A concept or PRD (written by `write-concept`, or a page with no functional requirements) | one pointer line instead: the page is a concept, not a spec, and `requirements-creator` turns it into a numbered spec |
| Action items, decisions, experiment follow-ups, feedback quick fixes, rollout or cleanup tasks, hand-offs and reassignments, plan items | nothing |

## Where each element is found

| # | Element | Present when the spec has… |
|---|---|---|
| 1 | Outcomes | a Goal, Problem and outcome or Success metrics section with a measurable outcome, or a hypothesis whose THEN is measurable |
| 2 | Out of scope | an Out of scope, Non-goals or Scope section with at least one item that is not `⚠️ TBD` — in the spec, or in a concept the page links (read only when the spec has no such item; never searched for) |
| 3 | Constraints | technical requirements or NFR, platforms, locales, business rules, dependencies, a rollout flag or a date |
| 4 | Prior decisions | the chosen approach, an approved design (linked mockups) or a linked decision record |
| 5 | Breakdown | functional requirements split by requirement, screen, block or stage (at least two); for an AI-feature spec, the behaviour spec plus the non-model requirements |
| 6 | Verification | acceptance criteria; for an A/B-test spec, its decision rule (Stopping / Decision Criteria); for an AI-driven spec, the eval set and an acceptable error rate that is not `⚠️ TBD` |

## The line

- Format: `Spec readiness: n/6 — missing: <elements>`, or `— missing: none` at 6/6.
- An acceptance criterion with no observable outcome ("works well", a THEN with nothing to check) is named on the same line — `· not testable: AC-3`. A task still cites it by id like any other; it is never rewritten into an invented threshold (Gate 1).
- Unnumbered acceptance criteria are cited by position (`AC 3`).
- It appears with the Step 1 extraction, as a row of the Step 6b summary and in the Step 11 report — never as a question. A dry run shows it the same way.
- A missing element is not asked for and not filled in a task: a task with no criterion to cite has no AC ids in its Definition of Done.

## AI-driven spec

A spec is AI-driven when it carries the AI-feature sections (Behaviour spec, Eval set, Acceptable error rate — the `requirements/ai-feature` template or the same sections inserted into another one), or when it says explicitly that the feature's output is produced by an AI or ML model, an LLM, GPT, a chatbot or a generative system — the explicit words of `templates/built-in/requirements/ai-feature-v1.md`. The bare word "model" never counts. Then:

- element 6 needs the eval set and a set acceptable error rate;
- Step 4 offers the pre-selected QA — Eval set option (`references/task-format.md` → QA special case).
