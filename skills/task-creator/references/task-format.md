# Task format — Step 7 titles, work-type fields, A/B-test Analytics tasks, AI-driven eval-set task

> Part of `task-creator`. Loaded on demand in Step 7, before task titles and labels are drafted. The common-fields table, the description format, the style preamble and the batch quality gate stay in SKILL.md.

## Task title format:

Standard development:
```
[WorkType] FeatureName
```

If Grooming (only for FE/BE/Android/iOS tasks):
```
[WorkType] - Grooming - FeatureName
```

If A/B test:
```
[WorkType] - A/B Test - FeatureName
```

If both Grooming AND A/B test (FE/BE/Android/iOS only):
```
[WorkType] - Grooming - A/B Test - FeatureName
```

Examples:
- `[FE] User Reviews - Product page review section`
- `[BE] - Grooming - User Reviews - Product page review section`
- `[iOS] - A/B Test - Compact product specs block`
- `[Android] - Grooming - A/B Test - Compact product specs block`
- `[Design] User Reviews - Product page review section` *(Design is never affected by Grooming)*
- `[QA] Smart reply suggestions - Eval set` *(the eval-set task of an AI-driven spec; QA is never affected by Grooming)*

## Work-type specific fields:

| Work Type | Issue Type | Labels | +Grooming label |
|---|---|---|---|
| **FE** | Task | `frontend` | + `grooming` if grooming mode |
| **BE** | Task | `backend` | + `grooming` if grooming mode |
| **Android** | Task | `Android`, `app` | + `grooming` if grooming mode |
| **iOS** | Task | `iOS`, `app` | + `grooming` if grooming mode |
| **Design** | Design (if available) or Task | `design` | not affected |
| **Analytics** | Analytics (if available) or Task | `Analytics` | not affected |
| **QA** (since v3.9.0) | QA (if available) or Task | `qa`, or the QA label the Epic's existing tasks already use (Step 5) | not affected |

## Analytics special case — A/B Test:

If the feature is an A/B test, create **2** Analytics tasks:
1. `[Analytics] {FeatureName} - Analytics coverage` — for defining analytics requirements
2. `[Analytics] {FeatureName} - Test results analysis` — for analyzing test results after completion

> **Note:** Use the user's preferred language (`user.language`) for analytics task titles if required by your team's conventions.

## QA special case — AI-driven spec (since v3.9.0):

When Step 1 finds the spec AI-driven (`references/spec-readiness.md`), the Step 4 work-type multi-select offers **QA — Eval set**, pre-selected. Unticked → no task. When the work types come from the request or a caller and Step 4 is not shown, the task is not added, and the Step 11 report says it is available.

- **Title:** `[QA] {FeatureName} - Eval set` — plus the A/B Test qualifier when it applies, like every title.
- **Fields:** issue type and labels from the QA row above; Parent, Team, Components and Reporter are the batch's common fields. Nothing is asked for this task: a field that would need a Step 6b question drops it, with one notice line in the 6b summary and in the Step 11 report (`Eval-set task not created — <field> unknown`).
- **Body** (the Step 7 format, built only from the spec — Gate 1):
  - *Why* — the feature's output comes from an AI model, so it ships against an eval set and an acceptable error rate rather than a feature list;
  - *What* — the spec's eval set, cited by section and not copied; one case marked `draft` for each behaviour-spec rule that no eval case covers, made only of that rule's input and its must / must not;
  - *How* — review the `draft` cases with the PM, then run the eval set on the built feature and record the error rate per error class the spec defines;
  - *Definition of Done* — the eval criterion cited by id (`AC-eval` in `requirements/ai-feature`; else the spec's own criterion, or its Acceptable error rate section by name); every `draft` case accepted or removed; a pointer to the spec's Kill criteria section, not a copy;
  - *Requirements* — the page link.
- **Links:** every selected BE, FE, Android and iOS task blocks it (Step 10).
