---
name: team-ops-reporter
version: 0.1.0
description: Create operational team reports from Jira — sprint plan, sprint review, quarter review, initiative status, and team-member review. Use when the user asks to "build a sprint plan/review report", "quarter results", "epic/feature/mission status", "how much did <person> close this period", "team ops report", or "report on releases / flags / story points". Українською: "зібрати звіт по спринту (план/рев'ю)", "результати кварталу", "статус епіка/фічі/місії", "скільки <людина> закрила за період", "операційний звіт команди", "звіт по релізах / флагах / стори-поінтах".
---

# Team Ops Reporter

Generate operational process reports for a team from Jira (optionally enriched with Confluence, Tableau, Fireflies). Pulls issues, processes them in Python (aggregations, Story Points, carried-vs-new, per-member, time dynamics), renders a report from a template, and offers visualizations. Supports five modes.

## Modes

| Mode | Output | Primary data |
|------|--------|--------------|
| `sprint-plan` | Plan for the open/selected sprint: directions → features → tasks, summary (total / carried / new / SP), per-Assignee and per-Developer distribution, key-focus table | Jira open/selected sprint |
| `sprint-review` | Sprint results: closed tasks, releases (fixVersions), feature flags turned ON/OFF, closed count + SP done per member | Jira closed sprint + fixVersions + FLAG |
| `quarter-review` | Quarter results: planned vs done, progress by direction, releases, epics/features fully closed | Jira quarter (sprint set or date range) |
| `initiative-status` | Implementation status of a mission/project/epic/feature: % done, child statuses, milestones, blockers | Jira tree under a key |
| `member-review` | One team member over a user-defined period: tasks/features closed, passed-to-test (dev) / tested (QA) / passed-to-review (analyst/designer), SP done, dynamics across days/weeks/sprints/months/quarters/years | Jira by assignee/developer/QA + status transitions |

## Integration prerequisite

Follow the MCP → registry → browser fallback chain (`references/integration-strategy.md`). Typical products:
- **Jira** — primary source (issues, custom fields, sprints, transitions, fixVersions, flags). Critical for all modes.
- **Confluence** — publishing target and reading OKRs / roadmap / previous reports.
- **Tableau** — optional, for correlating ops output with product metrics (CR, GMV) in quarter-review.
- **Fireflies** — optional, retro/standup notes for qualitative context in sprint/quarter review.

Confidential data policy applies (`references/data-policy.md`): internal Jira/Tableau data must not be passed to external LLMs.

## Local context prerequisite

**Before starting, follow `references/local-context-protocol.md` (Step 0).** Read `local-context.md`, select the active product, load:
- `product.jira_project_key` (e.g. SHOPEX), `organization.atlassian_cloud_id`
- **Team filter** — team field id (`customfield_10001` value) for the product's team(s)
- **Custom-field map** — SP / Developer / QA / Epic Link / Sprint / FLAG ids (`references/jira-data-protocol.md` has the SHOPEX defaults)
- `user.language`, Confluence space/parent for publishing
If `local-context.md` is missing → redirect to Plugin Configurator.

## Step T — Template Resolution

Runs before Step 1 (every mode produces an artifact). Follow `references/template-protocol.md`:
- `artifact_type: ops-report`
- `subtype`: `ops-sprint-plan` | `ops-sprint-review` | `ops-quarter-review` | `ops-initiative-status` | `ops-member-review`
- `product_id`, `language` from local-context.
- T-1 read `templates.preference` (`auto`/`always_ask`/`smart`); T-2 `resolve(...)` via template-library; T-3 decide; T-4 render with the template skeleton (collect required variables in Step 3); T-5 mark saved artifact with `<!-- template: {id}@{version} -->`.
- **Fallback**: if no custom template, use `references/builtin-templates/<subtype>.md`.
- **Escape hatch**: "no template" / "blank slate" → skip Step T, use built-in skeleton.

## Workflow

### Step 1 — Scope

Ask via AskUserQuestion (skip what is already unambiguous from the request):
- **Mode** (which of the 5 reports).
- **Team** (default: active team from local-context; allow override).
- **Mode parameters**:
  - `sprint-plan` / `sprint-review`: which sprint (open / named `SEX <n>` / last closed). Review defaults to the **last closed** sprint.
  - `quarter-review`: quarter (e.g. Q2 2026) → resolve to sprint set or date range.
  - `initiative-status`: the key (mission/epic/feature) and depth.
  - `member-review`: which member (Assignee and/or Developer/QA role), period, and **granularity** for dynamics (day/week/sprint/month/quarter/year).

### Step 2 — Jira fetch

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

Map computed data into the resolved template's sections (or the built-in skeleton). Keep the FET conventions from this product: directions → features (Epic Link) → tasks; "feature" carries its Jira number; orphan tasks in a separate table.

### Step 5 — Visualizations (offer, don't force)

Per the user's preference, **propose** the visualizations that fit the mode, then build only if accepted:
- `sprint-plan`: SP by direction (bar), Assignee/Developer load (bar), carried-vs-new (donut).
- `sprint-review`: burndown / closed-vs-planned, closed SP per member, flags ON/OFF timeline.
- `quarter-review`: planned-vs-done by direction (bar), epic completion (progress), SP trend across sprints (line).
- `initiative-status`: completion gauge, status breakdown (stacked bar), timeline.
- `member-review`: dynamics line (SP done / items closed over periods), role-mix breakdown.
Build charts into xlsx and/or as images embedded in Confluence.

### Step 6 — Output (ask each time)

Ask via AskUserQuestion: **Confluence (PROM) / local files (md + xlsx) / both**.
- **Confluence**: `contentFormat: html`; ask space + parent (page **or folder** id both work). Tables use `<th>` headers, no "№" column, panel-info for the header block, epic/board links.
- **Local**: build `<report>.md` (structured, nested tables) and `<report>.xlsx` (flat filterable sheet + "Огляд" summary sheet). Present files for the user.
- **Both**: do local first, then publish, then link the page.

### Step 7 — Feedback + self-improvement

Present a short summary + links. Ask if changes are needed; iterate. If a correction reveals a pattern, follow `references/self-improvement.md` and propose a SKILL.md improvement.

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
- `references/builtin-templates/` — fallback skeletons for the 5 subtypes.
- `references/template-protocol.md` — template-library resolution (shared).
- `references/local-context-protocol.md` — Step 0 (shared).
- `references/integration-strategy.md` — MCP → registry → browser (shared).
- `references/data-policy.md` — confidentiality (shared).
- `references/self-improvement.md` — learn from corrections (shared).

## Locked conventions (validated v1.14.0)

- **"Closed"** for review/quarter = `statusCategory = Done` (includes the `Ready` status).
- **Releases** — show **all** fixVersions streams (app + catalog-ui + backend + company-stats), windowed by `releaseDate`.
- **Per-member** distribution — always produce **both** Assignee and Developer breakdowns (QA when relevant); never double-count totals.
- **Transitions** (member-review) — changelog-backed via `status CHANGED TO "<s>" BY "<accountId>" DURING (...)`, not raw changelog dumps.
- **Quarter-review** — fetch **per month** and sum (full-quarter JQL times out).
- **Output format** — ask each run (Confluence / local md+xlsx / both). **Visualizations** — propose, build on accept.
- See `references/jira-data-protocol.md` for the exact field map, JQL, and extraction patterns.
