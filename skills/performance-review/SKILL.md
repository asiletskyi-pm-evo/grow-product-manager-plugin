---
name: performance-review
version: 0.1.1
description: Run a structured performance review of a team member — not Jira throughput, but achievement of goals, GTD-index, situational-leadership diagnosis, and signals — rendered into the employer's standard review template (past-period feedback + a 6–12-month plan). Diagnoses D-type → recommended style, reads 1-1 signals, and outputs an action recommendation (development / style change / yellow card / promotion) plus a profile update. Use when the user asks to "do a performance review", "review <person>", "half-year/annual review", "assess a team member", "growth plan for <person>", "is it time to promote". Українською — "провести перформанс-ревʼю", "оцінити співробітника", "піврічне/річне ревʼю", "оцінка члена команди", "план розвитку для <людини>", "чи час підвищувати". Do NOT use for Jira throughput metrics of a member (product-reporter member-review, which this skill consumes), to set new goals in isolation (goal-setter), or to run a 1-1 (one-on-one, which delivers the review). Strictly local/vault data.
---

# Performance Review

Assesses a person on the People-contour's coordinates — **goal achievement, GTD-index, situational-leadership type, and signals** — not raw Jira metrics. Renders the assessment into the employer's standard review template and outputs a clear action recommendation. The manager decides; the skill assembles the evidence and drafts the review.

> **Data:** strictly local/vault (`data-policy.md`) — a performance review is highest-sensitivity People-data. Feedback is factual/NVC, describing the work, not the person.

## Prerequisites
- `references/local-context-protocol.md` — Step 0. Context: active product, `user.language`, review-template registration.
- `references/people-context-protocol.md` — **Step P** (read goals, forecast_qa, gtd_index, d_type, 1-1 signals; write d_type, recommended_style, delegation targets, review link).
- `references/goal-frameworks.md` — goals as the primary axis; plan items phrased as SMARTCBP.
- `references/people-frameworks.md` — Hersey-Blanchard diagnosis (wants/can → D-type → style S + delegation level), GTD-index, NVC feedback.
- `references/reporting-3t5f.md` — achievement evidence (Forecast QA) via product-reporter.
- `references/communication-frameworks.md` — NVC feedback phrasing.
- `references/template-protocol.md` — **Step T** (`performance-review` built-in template).
- `references/data-policy.md` — highest-sensitivity tier (strictly local).
- `references/self-improvement.md`.

## Data sources

| Axis | Source |
|------|--------|
| Goal achievement | 3T5F reports via `product-reporter` (goal-report), `active_goal_letter`, Forecast QA |
| GTD-index | delivery data (planned→done) via `product-reporter` / `sprint-planning` carryover |
| D-type diagnosis | wants/can → D-type → recommended style S + delegation level (`people-frameworks.md`) |
| Signals | `one_on_one` history + profile `signals` |
| Rational check (optional) | "X dollars for Y tasks" / ROAIP (`roi-frameworks.md`) |

## The review artifact (the `performance-review` template)

Employer-standard structure — register in template-library as a built-in:

- **Header:** Name + period (`MM.YYYY`).
- **Section 1 — "Past-period feedback"**: a numbered **"Achievements & feedback"** table (~6 items). Each item = an achievement or growth area + concrete NVC feedback (facts, not traits). Filled from the frameworks: goal attainment (Forecast QA), GTD-index trend, D-type movement.
- **Section 2 — "Plan for the next 6–12 months"**: a numbered **"Item | Feedback on results"** table. Each plan item is phrased as a **SMARTCBP** goal; the second column stays empty (filled at the next review).

## Pipeline

### Step 0 — Local context · Step P — Person context
Load the profile: goals, `forecast_qa`, `gtd_index`, `d_type`, 1-1 `signals`.

### Step T — Template resolution
`artifact_type: performance-review`, resolve per `template-protocol.md` (employer template preferred).

### Step 1 — Gather achievement evidence
- Chain to `product-reporter` (goal-report) for Forecast QA per goal, and to `product-reporter`/`sprint-planning` for the GTD-index (planned→done). Compute, don't estimate.
- Pull the D-type inputs (wants/can) from goals+signals; derive the recommended style S and delegation level.
- Optional "X for Y" rational check.

### Step 2 — Draft Section 1 (past-period feedback)
~6 numbered items, each an achievement or growth area + **NVC feedback** (fact → feeling/need → request), referencing Forecast QA and the GTD trend. No personal characterization.

### Step 3 — Draft Section 2 (6–12-month plan)
Each item a SMARTCBP goal (chain to `goal-setter` to formulate/commit). Leave the results column empty for the next review.

### Step 4 — Recommendation
Output one clear action: **development** (grow toward D4) / **style change** (adjust S per new D-type) / **yellow card** (underperformance → the offboarding evidence path) / **promotion**. Ground it in the evidence.

### Step 5 — Persist & chain
- **Step P write (gated, strictly local):** update `d_type`, `recommended_style`, delegation targets, and the review artifact link. Save to `People/reviews/…` vault/local only — never Confluence.
- Chain: → `one-on-one` (deliver the review in person) · → `goal-setter` (new-period goals) · → `offboarding-guide` (if "doesn't want" and tools exhausted) · → `delegation-coach` (if promotion/more delegation).

### Step 6 — Feedback + self-improvement
Per `self-improvement.md`.

## Quality standards
- Assessment is goals + GTD + D-type + signals — not raw Jira throughput (that's product-reporter's member-review, consumed here).
- Numbers are computed via product-reporter, never estimated.
- Section 1 feedback is NVC (facts, not traits); Section 2 items are SMARTCBP goals.
- Always end with one grounded recommendation (development / style change / yellow card / promotion).
- Strictly local/vault; feedback describes the work, not the person's worth.
- Language — `user.language`.

## Skill chaining
← `product-reporter` (goal-report + member-review data) · ← `one-on-one` (signals) · → `one-on-one` (deliver) · → `goal-setter` (new goals) · → `offboarding-guide` (yellow card path) · → `delegation-coach` (promotion path).

## Example dialogues
- *"Проведи ревʼю аналітика Олени за півріччя"* → Step P + product-reporter (Forecast QA 92%, GTD 0.72→0.81, D3→approaching D4) → Section 1 with 6 NVC feedback items, Section 2 with 3 SMARTCBP plan goals → recommendation: **development** toward D4 + more delegation → offers to deliver via one-on-one.
- *"Готую ревʼю, він недотягує цілі й не хоче рости"* → evidence shows Forecast QA 61%, flat GTD, "doesn't want" signals → recommendation: **yellow card** → chains to offboarding-guide's evidence path (goals+reports already exist).
