# Task format — Step 7 titles, work-type fields, A/B-test Analytics tasks

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

## Work-type specific fields:

| Work Type | Issue Type | Labels | +Grooming label |
|---|---|---|---|
| **FE** | Task | `frontend` | + `grooming` if grooming mode |
| **BE** | Task | `backend` | + `grooming` if grooming mode |
| **Android** | Task | `Android`, `app` | + `grooming` if grooming mode |
| **iOS** | Task | `iOS`, `app` | + `grooming` if grooming mode |
| **Design** | Design (if available) or Task | `design` | not affected |
| **Analytics** | Analytics (if available) or Task | `Analytics` | not affected |

## Analytics special case — A/B Test:

If the feature is an A/B test, create **2** Analytics tasks:
1. `[Analytics] {FeatureName} - Analytics coverage` — for defining analytics requirements
2. `[Analytics] {FeatureName} - Test results analysis` — for analyzing test results after completion

> **Note:** Use the user's preferred language (`user.language`) for analytics task titles if required by your team's conventions.
