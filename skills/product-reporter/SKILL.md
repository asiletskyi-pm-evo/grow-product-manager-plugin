---
name: product-reporter
version: 0.5.0
description: Create operational Jira reports AND goal reports for a team, person, or direction. Six modes — sprint plan, sprint review, quarter review, initiative status, member review, goal-report (3T5F build/audit against a goal). Use when the user asks to "build a sprint plan/review report", "quarter results", "epic/feature/mission status", "how much did <person> close this period", "team ops report", "report on releases / flags / story points", "goal report", "3T5F report", "stakeholder report for the direction", or "audit this report against the goal". Українською — "зібрати звіт по спринту (план/рев'ю)", "результати кварталу", "статус епіка/фічі/місії", "скільки <людина> закрила за період", "операційний звіт команди", "звіт по релізах / флагах / стори-поінтах", "звіт по цілі", "звіт 3T5F", "звіт для стейкхолдерів по напрямку", "перевір звіт проти цілі". Do NOT use to SET a person's goal (goal-setter), to analyze A/B or dashboard metrics (product-analysis), or to run a full performance review (performance-review).
---

# Product Reporter

Generate operational process reports for a team from Jira (optionally enriched with Confluence, Tableau, Fireflies), plus **goal reports (3T5F)** for a person or a direction. Operational modes pull issues and process them in Python (aggregations, Story Points, carried-vs-new, per-member, time dynamics); the goal-report mode builds or audits a goal-linked 3T5F report per `references/reporting-3t5f.md`. Renders from a template and offers visualizations. Supports six modes.

## Modes

| Mode | Output | Primary data |
|------|--------|--------------|
| `sprint-plan` | Plan for the open/selected sprint: directions → features → tasks, summary (total / carried / new / SP), per-Assignee and per-Developer distribution, key-focus table | Jira open/selected sprint |
| `sprint-review` | Sprint results: closed tasks, releases (fixVersions), feature flags turned ON/OFF, closed count + SP done per member | Jira closed sprint + fixVersions + FLAG |
| `quarter-review` | Quarter results: planned vs done, progress by direction, releases, epics/features fully closed | Jira quarter (sprint set or date range) |
| `initiative-status` | Implementation status of a mission/project/epic/feature: % done, child statuses, milestones, blockers | Jira tree under a key |
| `member-review` | One team member over a user-defined period: tasks/features closed, passed-to-test (dev) / tested (QA) / passed-to-review (analyst/designer), SP done, dynamics across days/weeks/sprints/months/quarters/years | Jira by assignee/developer/QA + status transitions |
| `goal-report` | Build or audit a **3T5F** report of a person's or a direction's progress against a *goal* (Target, Top Record, Top-3 Highlights, Fact, Fact/Forecast Quota Attainment, Funnel). Two paths: **build** (draft a report from data + the person's own Highlights) and **audit** (score an existing report, flag Forecast QA < 100%, return a corrected model). | The goal (from goal-setter / person profile) + Fact/Funnel data (Jira, Tableau) |

> **Boundary:** `member-review` reports **team throughput** (what the person shipped in Jira — tasks, SP, transitions). `goal-report` reports **progress against a goal** (3T5F). Setting the goal itself is `goal-setter`. `performance-review` consumes `goal-report` output as achievement evidence.

## Integration prerequisite

Follow the MCP → registry → browser fallback chain (`references/integration-strategy.md`). Typical products:
- **Jira** — primary source (issues, custom fields, sprints, transitions, fixVersions, flags). Critical for all modes.
- **Confluence** — publishing target and reading OKRs / roadmap / previous reports.
- **Tableau** — optional, for correlating ops output with product metrics (CR, GMV) in quarter-review.
- **Fireflies** — optional, retro/standup notes for qualitative context in sprint/quarter review.

Confidential data policy applies (`references/data-policy.md`): internal Jira/Tableau data must not be passed to external LLMs.

## Local context prerequisite

**Before starting, follow `references/local-context-protocol.md` (Step 0).** Read `local-context.md`, select the active product, load:
- `product.jira_project_key` (e.g. PROJ), `organization.atlassian_cloud_id` (auto-discoverable via `getAccessibleAtlassianResources` if unset)
- **Team filter** — team field id (`customfield_10001` value) for the product's team(s)
- **Custom-field map** — SP / Developer / QA / Epic Link / Sprint / FLAG ids (`references/jira-data-protocol.md` has the PROJ defaults)
- `user.language`, Confluence space/parent for publishing
If `local-context.md` is missing → redirect to Plugin Configurator.

## Step T — Template Resolution

Runs before Step 1 (every mode produces an artifact). Follow `references/template-protocol.md`:
- `artifact_type: ops-report` for operational modes; `artifact_type: report-3t5f` for `goal-report`.
- `subtype`: `sprint-plan` | `sprint-review` | `quarter-review` | `initiative-status` | `member-review` | `goal-3t5f` (the subtype is already scoped by `artifact_type: ops-report` — it carries no `ops-` prefix, which is also why the built-in filenames resolve)
- `product_id`, `language` from local-context.
- Run **T-0 → T-5 exactly as `references/template-protocol.md` names them** — T-0 declare context, T-1 load registry, T-2 score/rank, T-3 decide (per `templates.preference`: `auto`/`always_ask`/`smart`), T-4 collect variables (during Step 3), T-5 render + record. Do not renumber the steps locally: other skills cite "Step T-4" meaning the protocol's T-4.
- **Fallback**: if no custom template, the protocol's built-in ladder resolves `builtin://ops-report/{subtype}-v1.md` (e.g. `sprint-plan-v1.md`); for `goal-report` — `templates/built-in/report-3t5f/default-v1.md`.
- **Escape hatch**: "no template" / "blank slate" → skip Step T, use built-in skeleton.

## Workflow

### Step 1 — Scope

Ask via AskUserQuestion (skip what is already unambiguous from the request):
- **Mode** (which of the 6 reports — the five ops modes or `goal-report`).
- **Team** (default: active team from local-context; allow override).
- **Mode parameters**:
  - `sprint-plan` / `sprint-review`: which sprint (open / named, e.g. `Sprint 41` / last closed). Review defaults to the **last closed** sprint.
  - `quarter-review`: quarter (e.g. Q2 2026) → resolve to sprint set or date range.
  - `initiative-status`: the key (mission/epic/feature) and depth.
  - `member-review`: which member (Assignee and/or Developer/QA role), period, and **granularity** for dynamics (day/week/sprint/month/quarter/year).

### Step 2 — Jira fetch

> **Subagent delegation (large fan-out).** For member-review / quarter-review with many Jira pages (paginated, per period), delegate per `references/subagent-delegation.md`: split by page / month / member into batches, spawn subagents in parallel, each returns compact extracted rows (status, SP, transitions) per the data protocol, and the main agent aggregates (merge, dedupe). Falls back to inline if subagents are unavailable.

Follow `references/jira-data-protocol.md`. Per mode, build the JQL and fetch the fields needed:

- Common fields: `summary, status, assignee, customfield_10014 (Epic Link), customfield_10036 (SP), customfield_10041 (Developer), customfield_10037 (QA), customfield_10020 (Sprint)`.
- `sprint-review` adds: `fixVersions`, `customfield_10043 (FLAG)`, `resolutiondate`, status-category.
- `member-review` adds: `changelog` (status transitions) to date "passed to test / review / tested / closed" events and to compute period dynamics.
- `quarter-review` adds: epic-level rollup (issuetype Epic, status), `resolutiondate`, `fixVersions`.

**Extraction technique (mandatory for large teams):** markdown responses include descriptions and exceed token limits → the tool saves to a file. Run `Grep -o` with compact field patterns and parse; paginate via `nextPageToken` (~100/page). See protocol for the exact patterns.

### Step 2.5 — Data integrity gate

- **Completeness**: sprint/quarter boundaries correct; period not mid-bucket without normalization.
- **Carried vs new** (`sprint-plan`): `new` = no `closed` sprint in `customfield_10020` history; else `carried`.
- **Closed vs open** (`sprint-review`/`quarter-review`): use status-category `done` for "closed"; record `resolutiondate` inside the period.
- **Dedup**: a member can be Assignee+Developer+QA on the same issue — count per role, never double-count totals.
- **SP nulls** → treat as 0; flag features with missing estimates.

### Step 3 — Process (Python)

Compute in Python (pandas) — never estimate what can be computed:
- Totals, Story-Point sums, carried/new split (plan), closed counts + SP done (review), per-member by **Assignee, Developer, QA** separately.
- `quarter-review`: planned vs done, epics/features with 100% children done, releases list.
- `initiative-status`: % done (done-children / all-children, optionally SP-weighted), status spread, blockers (Flagged / blocked links), milestone/timeline from due dates & resolutiondate.
- `member-review`: per role, count of items **closed / passed-to-test / tested / passed-to-review** (from changelog transitions), SP done, and a dynamics series at the chosen granularity.

### Step 4 — Structure under template

Map computed data into the resolved template's sections (or the built-in skeleton). Keep the reporting conventions from `planning-core.md`: directions → features (Epic Link) → tasks; "feature" carries its Jira number; orphan tasks in a separate table.

### Step 5 — Visualizations (offer, don't force)

Per the user's preference, **propose** the visualizations that fit the mode, then build only if accepted:
- `sprint-plan`: SP by direction (bar), Assignee/Developer load (bar), carried-vs-new (donut).
- `sprint-review`: burndown / closed-vs-planned, closed SP per member, flags ON/OFF timeline.
- `quarter-review`: planned-vs-done by direction (bar), epic completion (progress), SP trend across sprints (line).
- `initiative-status`: completion gauge, status breakdown (stacked bar), timeline.
- `member-review`: dynamics line (SP done / items closed over periods), role-mix breakdown.
Build charts into xlsx and/or as images embedded in Confluence.

### Step 6 — Output (ask each time)

Ask via AskUserQuestion: **Confluence (the product's space from local-context) / local files (md + xlsx) / both**.
- **Confluence**: `contentFormat: html`; ask space + parent (page **or folder** id both work). Tables use `<th>` headers, no "№" column, panel-info for the header block, epic/board links.
- **Local**: build `<report>.md` (structured, nested tables) and `<report>.xlsx` (flat filterable sheet + "Огляд" summary sheet). Present files for the user.
- **Both**: do local first, then publish, then link the page.

## Workflow — `goal-report` mode (3T5F)

This mode does **not** use the Jira ops pipeline above. It follows `references/reporting-3t5f.md`. Two paths, chosen from the request ("build a goal report" vs "audit this report").

### G-0 — Person / direction context
After Step 0, if the report is for a **person**, run **Step P** (`references/people-context-protocol.md`) to load their `active_goal_letter`, reporting cadence, and last Forecast QA. For a **direction**, resolve the direction goal (OKR) from `planning-core` / local-context. If no goal is known → say so and offer to chain to `goal-setter` (a 3T5F report without a Target is harmful).

### G-1 — Assemble the eight elements
Pull what can be computed and leave the human parts to the person:
- **Target** — the SMARTCBP goal (verbatim from the goal letter).
- **Fact / Funnel** — pull from Jira (delivery, SP) and/or Tableau (metrics) via the integration chain; compute in Python.
- **Fact / Forecast Quota Attainment** — compute per period and cumulatively; Forecast uses the minimum model in `reporting-3t5f.md` (prior fact + last-period × remaining) unless a better model is given.
- **Top Record** — the period's best datapoint with its time-slice.
- **Top-3 Highlights** — ask the person (or the PM) for these; never fabricate. Where an improvement is quantifiable, express its $ / ROI per `references/roi-frameworks.md`.

### G-2 (build) — Draft + hand off
Render the 8 elements under the `report-3t5f` template with the formatting rules (status emoji, brevity, bold figures). Present the draft; the person fills/confirms Top-3 Highlights (preserving the "personal attention to the numbers" principle — the report is sent manually).

### G-2 (audit) — Score an existing report
Given a report + its goal, run the manager audit from `reporting-3t5f.md`: presence of all 8 elements, goal-linkage, **Forecast QA gate** (< 100% → generate corrective suggestions), ambiguity/brevity. Output a before→after and a reformatted model report.

### G-3 — Update the person's profile
If the report is for a **person**, run the Step P write (gated, per `references/people-context-protocol.md`): `reporting.last_report`, `last_report_ref`, `forecast_qa`. Persistence of the report artifact itself happens in Step 8 below — this step only writes the profile fields.

---

## Workflow — shared final steps (ALL six modes)

> These run after the mode-specific pipeline above — the five ops modes (Steps 1–6) **and** `goal-report` (G-0–G-3) alike. They were nested under the goal-report heading until v2.0.2, which read as if the ops modes ended with no feedback loop and no persistence.

### Step 7 — Feedback + self-improvement

Present a short summary + links. Ask if changes are needed; iterate. If a correction reveals a pattern, follow `references/self-improvement.md` and propose a SKILL.md improvement.

### Step 8 — Save to Vault (Optional)

> Requires: `references/vault-protocol.md` → Vault Save

IF vault_level > L0 AND vault sync_mode != "off":

1. `vault_save({ type: "ops-report" | "report-3t5f", product: active_product, skill: "product-reporter", skill_version: "0.5.0", tags: [mode (sprint-plan/sprint-review/quarter-review/initiative-status/member-review/goal-report), period], content: final report markdown, related: [previous report of same mode], extra_frontmatter: { mode, period, confluence_url (if published) } })`
   - Ops modes → `type: "ops-report"` → `Reports/ops/{product}/` → "Saved to Vault: Reports/ops/{product}/…"
   - `goal-report` → `type: "report-3t5f"` → `People/reports/{person_slug}/` → "Saved to Vault: People/reports/{person_slug}/…". **People-data locality applies** (`data-policy.md`): vault/local only, never auto-published to Confluence.

## Quality standards

- Always compute in Python; show numbers, never estimate.
- Per-member metrics: split by **Assignee / Developer / QA**; never double-count totals.
- Every Story-Point / count carries its period/scope inline (sprint name, date range, granularity).
- "Closed" = status-category `done` with `resolutiondate` in-period; "carried/new" defined via Sprint history.
- Confluence: `<th>` headers, no "№" column, links to Jira keys/epics/board (FET formatting rules).
- Language: Ukrainian by default (`user.language`).
- Mark every report with its template id; mark Jira as the source (`jira-internal`).

## Additional Resources

- `references/jira-data-protocol.md` — custom-field map, per-mode JQL, large-response grep-extraction, pagination, transitions parsing.
- `references/reporting-3t5f.md` — the 8 elements, formatting rules, and manager audit for `goal-report` mode.
- `references/people-context-protocol.md` — Step P for person goal reports (goal + cadence + Forecast QA).
- `references/roi-frameworks.md` — quantify Top-3 Highlights in $ / ROI.
- `references/goal-frameworks.md` — SMARTCBP Target; boundary with `goal-setter`.
- `templates/built-in/ops-report/` + `templates/built-in/report-3t5f/` — built-in fallback skeletons for the report subtypes.
- `references/template-protocol.md` — template-library resolution (shared).
- `references/local-context-protocol.md` — Step 0 (shared).
- `references/integration-strategy.md` — MCP → registry → browser (shared).
- `references/data-policy.md` — confidentiality (shared).
- `references/self-improvement.md` — learn from corrections (shared).

## Locked conventions (validated v1.14.0)

- **"Closed"** for review/quarter = `statusCategory = Done` (includes the `Ready` status).
- **Releases** — show **all** fixVersions streams configured in local-context (`product.release_streams`; typically app + web UI + backend + per-service), windowed by `releaseDate`.
- **Per-member** distribution — always produce **both** Assignee and Developer breakdowns (QA when relevant); never double-count totals.
- **Transitions** (member-review) — changelog-backed via `status CHANGED TO "<s>" BY "<accountId>" DURING (...)`, not raw changelog dumps.
- **Quarter-review** — fetch **per month** and sum (full-quarter JQL times out).
- **Output format** — ask each run (Confluence / local md+xlsx / both). **Visualizations** — propose, build on accept.
- See `references/jira-data-protocol.md` for the exact field map, JQL, and extraction patterns.
