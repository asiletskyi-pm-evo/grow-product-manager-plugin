---
name: sprint-planning
version: 0.3.2
description: Helps the PM efficiently estimate and run sprint pre-planning — derives focuses from the quarterly roadmap/missions/projects, highlights what's READY to pull right now (dependencies cleared), catches work-sequence violations (e.g. client-side work planned ahead of analytics coverage), gathers per-member capacity, analyzes carryover risk from the last sprint, suggests assignees for unowned tasks, and fills the sprint to capacity. Use when "plan the sprint", "sprint pre-planning", "what can we pull into the next sprint", "what's ready from the backlog", "check sprint dependencies", "build sprint focuses", "distribute the sprint", "who takes the tasks". Українською — "спланувати спринт", "передпланування спринта", "що можна взяти у наступний спринт", "що готове з беклогу", "перевір залежності спринта", "сформуй фокуси спринта", "розподілити спринт", "хто візьме задачі".
---

# Sprint Planning

PM advisor for sprint pre-planning (finest slice). It doesn't just fill the sprint — it **highlights readiness and work-order violations**, computes per-person capacity, accounts for carryover risk, and suggests assignees. **The PM decides.**

Part of the planning-suite: takes scope from `quarterly-planning` and direction priority from `project-planning`; tasks → `task-creator`. Integrates with `product-reporter` (last sprint ← `sprint-review`+`member-review`; approved plan → rendered as a `sprint-plan` report).

## Prerequisites
- `references/local-context-protocol.md` — Step 0 + Planning (capacity rules, sprint cadence + anchor, board, Development Flow).
- `references/planning-core.md` — model, labeling, statuses, Development Flow.
- `references/capacity-model.md` — per-member capacity (sec. 3), carryover-risk, auto-estimation, sprint ceiling (sec. 9).
- `references/dependency-model.md` — **work-type DAG + readiness rule** (sec. 4), violations.
- `references/roadmap-artifacts.md` — sprint-plan format (demarcation from ops-report).
- `references/jira-data-protocol.md` — Jira plumbing (reuse).
- `references/people-frameworks.md` — GTD-index (planned→done conversion); D-type for assignee fit.
- `references/people-context-protocol.md` — read `d_type`/`delegation`; write the `gtd_index` datapoint (read-mostly).
- `references/integration-strategy.md`, `references/persistent-storage.md`, `references/template-protocol.md`.

## Step T — Template Resolution
`artifact_type: roadmap`, `subtype: sprint-plan`, `product_id`, `language`. (The reporting sprint-plan lives in product-reporter; this is the planning one.)

## Modes

| Mode | Output |
|------|--------|
| `groom` | Pre-planning: estimate + readiness + dependency check (before commit) |
| `plan` | Fill the next sprint to capacity + goal |
| `review` | committed vs done + carryover (feeds carryover-risk) |
| `forecast` | Which sprints the quarter's remainder lands in |

## Pipeline

### Step 0 — Local context
Per `local-context-protocol.md` + Planning + Development Flow (work-type sequence, readiness threshold).

### Step 1 — Scope (3 candidate sources)
Which sprint (default: next). **Sources:** (a) backlog; (b) approved quarterly roadmap (`quarterly-planning`); (c) **future sprints** — tasks spread across upcoming sprints (Ready ones can be pulled forward / rebalanced). Jira board id.

### Step 2 — Sprint focuses
Derive from the active quarterly roadmap + project arcs (`project-planning`): which directions we pull this sprint and why. **Gate.**

### Step 3 — Per-sprint per-member capacity
Gather from the PM a forecast of **working days / capacity for each person** (time off, partial days, parallel directions) — `capacity-model` sec. 3. **Gate.**

### Step 3b — Carryover-risk + GTD-index (last sprint)
**Delegate `product-reporter` `sprint-review`+`member-review`** for committed vs done and per-person throughput. Compute carryover risk (`capacity-model` sec. 3: capacity ÷ remainder) → reduce load on at-risk members, flag chronic overload.
**GTD-index** (`references/people-frameworks.md`): from the same committed-vs-done data, compute the **planned→done conversion** per sprint and per person (the person's GTD-index for the period). If a person profile exists (`references/people-context-protocol.md`), **write the datapoint** to `gtd_index` (append, read-only elsewhere) — this feeds `performance-review`. No profile → report the number in the plan only.

### Step 4 — Readiness scan
For each candidate check the status of prerequisites along the **work-type DAG** (`dependency-model` sec. 4) → **Ready** (prerequisites cleared) / **Blocked** (by what and up to which status). Example: BE+Design+Analytics in review/testing → client-side implementation = Ready.

### Step 5 — Sequence violations
If a downstream candidate is planned while upstream is below the readiness threshold (e.g. client-side ahead of analytics within the feature scope) → **highlight the violation** with an explanation; conscious PM confirmation, not a hard block.

### Step 6 — Estimate + fill
Auto-estimate missing ones (analogy); fill to the sprint ceiling by platform/person from **Ready** candidates only; **sprint-gate** (don't exceed the platform ceiling); sprint goal. Free capacity → **pull-forward** Ready tasks from future sprints (sync the shift with `project-planning` arcs).

### Step 6b — Assignee suggestion
For unowned tasks — propose assignment, **prioritizing those with no tasks yet / free capacity**; role-platform matching; account for the per-member budget (Step 3) and risk (Step 3b). **Delegation-level fit** (`references/people-context-protocol.md` → `delegation`, `d_type`): where profiles exist, prefer routing work a person owns at a high delegation level (5–7) or that fits their D-type; a stretch assignment to a D1/D2 is flagged as needing closer support (chains to `delegation-coach` for a transfer plan). Writing assignee to Jira — **gate**; respect team convention (where assignee is left empty until work starts — the suggestion stays in the plan, not on the task).

### Step 7 — Correction loop with PM
Show what doesn't fit / is blocked → choice. Live recompute.

### Step 8 — Artifacts
Sprint plan (Confluence / assignment into the Jira sprint) — **gate before writing to Jira**. Approved plan → can be rendered as a `sprint-plan` report via product-reporter.

### Step 9 — Save to Vault (Optional)
Per `references/vault-protocol.md` → Vault Save. IF vault_level > L0 AND sync_mode != "off": `vault_save({ type: "roadmap", product: active_product, skill: "sprint-planning", skill_version: "0.3.2", tags: [sprint id, focuses], content: approved sprint plan, related: [[quarterly roadmap]], extra_frontmatter: { subtype: "sprint-plan", sprint } })` → "Saved to Vault: Roadmaps/{product}/…"

## Quality Standards
- Only Ready candidates go into the fill; Blocked — with an explanation, not silently.
- Sequence violations — always highlight; the PM decides.
- Per-member: don't double-count (Assignee/Developer/QA separate — `jira-data-protocol`).
- Estimates/assignments — marked "pending TL confirmation"; the PM decides.
- Work-type flow and readiness threshold — from the team's Development Flow, not hardcoded.
- Write to Jira only after approval. Language — `user.language`.

## Additional Resources
`references/capacity-model.md`, `dependency-model.md`, `planning-core.md`, `roadmap-artifacts.md`, `local-context-protocol.md`, `template-protocol.md`, `persistent-storage.md`, `self-improvement.md`, `jira-data-protocol.md`.
