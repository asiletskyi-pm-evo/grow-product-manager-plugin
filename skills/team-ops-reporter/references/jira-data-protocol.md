# jira-data-protocol (team-ops-reporter)

How to fetch and parse Jira data reliably for ops reports. SHOPEX/Prom defaults shown; move org-specific ids into `local-context.md`.

## Custom-field map (SHOPEX)

| Field | ID | Notes |
|---|---|---|
| Team | `customfield_10001` | Atlassian Team object. JQL by **id**: `cf[10001] = "3eb29614-f447-45a5-8963-016f46f7dded-31"` (Feedback Ecosystem). Filtering by name does not work. |
| Story Points | `customfield_10036` | number; null → treat as 0 |
| Story point estimate | `customfield_10016` | team-managed alt; SHOPEX uses 10036 |
| Developer | `customfield_10041` | user object |
| QA | `customfield_10037` | user object |
| Epic Link | `customfield_10014` | string key (`SHOPEX-…` or cross-project `DT-…`) = the "feature" level |
| Sprint | `customfield_10020` | array of `{id,name,state,startDate,endDate,completeDate}` — full history |
| FLAG | `customfield_10043` | feature flag |
| fixVersions | `fixVersions` | releases (`name`, `releaseDate`, `released`) |
| resolutiondate | `resolutiondate` | use for "closed in period" |

Cloud ID: `4a0df834-655a-4a18-8b2a-5ec2c9dec994`. **Sprint ids are NOT hardcoded** — resolve them at runtime: use `openSprints()` / `closedSprints()` in JQL, or read `customfield_10020` (`{id,name,state,…}`) from issues, or query the board's sprints, then map name → id. (Example only, do NOT use as defaults: at one point sprint 55 ≈ `14979` active, 54 ≈ `14978`, 53 ≈ `14977` closed — these go stale every sprint.)

## Per-mode JQL

```
# sprint-plan (open or named sprint)
project = SHOPEX AND cf[10001] = "<team-id>" AND sprint in openSprints() ORDER BY cf[10014] ASC, status ASC
# or a named/closed sprint:
... AND sprint = <sprintId> ...

# sprint-review (completed work in a sprint)
project = SHOPEX AND cf[10001] = "<team-id>" AND sprint = <sprintId> AND statusCategory = Done ORDER BY resolutiondate
# all sprint scope (for % done): drop the statusCategory clause

# quarter-review (date range; pair with sprint set if needed)
project = SHOPEX AND cf[10001] = "<team-id>" AND resolutiondate >= "YYYY-MM-DD" AND resolutiondate <= "YYYY-MM-DD" AND statusCategory = Done
# epics rolled up in the quarter:
project = SHOPEX AND cf[10001] = "<team-id>" AND issuetype = Epic

# initiative-status (tree under a key)
parent = <KEY>           # direct children
"Epic Link" = <EPIC>     # tasks under an epic (or cf[10014] = "<EPIC>")

# member-review (one person over a period, any role)
project = SHOPEX AND (assignee = <accountId> OR cf[10041] = <accountId> OR cf[10037] = <accountId>)
  AND updated >= "<from>" AND updated <= "<to>"
# closed-by-them in period:
... AND statusCategory = Done AND resolutiondate >= "<from>" AND resolutiondate <= "<to>"
```

## Large-response extraction (mandatory)

`searchJiraIssuesUsingJql` with `responseContentFormat:"markdown"` still embeds full descriptions → responses routinely exceed the token cap and are **saved to a file**. Do not try to read the whole file. Instead:

1. Request only the fields you need (descriptions still come back, but smaller scopes help).
2. `Grep -o` the saved file with compact alternation patterns, then parse in document order (fields appear per node in JSON order).

Useful `-o` patterns:
```
"key":"SHOPEX-[0-9]+"
"summary":"[^"]*"
"customfield_10014":(null|"[A-Z]+-[0-9]+")
"customfield_10036":(null|[0-9.]+)
"customfield_10041":(null|\{"self":"[^"]*","accountId":"[^"]*","emailAddress":"[^"]*")
"customfield_10037":(null|\{...emailAddress...)
"assignee":(null|\{...emailAddress...)
statuses/[a-z]*\.png","name":"[^"]*"      # status name (not statusCategory)
"state":"(closed|future)"                  # count to detect carried-over (see below)
"id":[0-9]+,"name":"[^"]*","state":"[a-z]+"# sprint entries
```
Notes:
- With a **restricted** field set there is exactly one `"key":"SHOPEX-…"`/node and one of each cf line → tokens align per node.
- A user field's `emailAddress` comes right after `accountId`; map email local-part → display name via a roster in local-context.
- The "Team = name" form returns 0; always use the team **id**.

## Pagination

`maxResults` ~100/page; `pageInfo.hasNextPage` + `endCursor` → pass as `nextPageToken`. Grep the saved file for `"endCursor":"[^"]*"`. Large cross-functional teams span 3+ pages. The search endpoint can time out (~180s) on deep pages — retry, or fetch the tail by explicit `key in (...)`.

## Carried-over vs new (sprint-plan)

Issues keep their **entire** sprint history in `customfield_10020`. Definition:
- **New** (planned at this sprint's grooming) = history contains **no** `"state":"closed"` sprint (only the one active sprint).
- **Carried** = ≥1 closed sprint in history.
Detect by counting `"state":"closed"` occurrences between one node's key and the next.

## Status transitions (member-review)

Fetch `changelog` (expand) and read `items[].field == "status"` transitions with timestamps. Map to role events:
- **passed to test** (dev) — transition to `Ready for test`.
- **tested** (QA) — transition out of testing to `Documentation`/`Ready`/`Done`-side, or `In test → Ready`.
- **passed to review** (analyst/designer) — transition to `On review`.
- **closed** — transition into a `done` status-category status, with `resolutiondate`.
Aggregate counts and SP by the chosen granularity (day/week/sprint/month/quarter/year) for the dynamics series. Sprint buckets come from `customfield_10020` start/end dates.

## Confluence publishing

- `createConfluencePage`, `contentFormat:"html"`, `spaceId` (PROM = `108528587`), `parentId` = a **page or folder** id (folder works).
- Tables: `<th>` header cells, **no "№" column**, header block in `<div data-type="panel-info">`, link Jira keys/epics and the board.
- Escape `&` → `&amp;` in cell text (e.g. "Q&amp;A", "UI&amp;UX").

## Validated conventions (v1.14.0 — from test runs)

These were confirmed against real SHOPEX data during skill bring-up:

- **"Closed" = statusCategory `Done`** — and this category **includes the `Ready` status** (A/B-rolled-out tasks often sit in `Ready`, not `Closed`). Count both. Use `statusCategory = Done` in JQL, not `status = Closed`.
- **Releases** — issues carry their **entire** fixVersions history (back years). For "releases in period", filter `fixVersions.releaseDate` to the period window and group by **stream**: app (`[B2C][Android] …`, `[B2C][iOS] …`), `catalog-ui: vYYYY…`, backend (`26.NN.N`), `company-stats: …`. Show all streams.
- **Feature flags** — `customfield_10043` (FLAG) holds flag name(s), sometimes comma-separated, suffixes `_AB` / `_ENABLED`. **Enabled / A-B launched** = FLAG present on the task. **Disabled / removed** = tasks whose summary matches `Випилити прапор …` (flag cleanup after full rollout).
- **member-review transitions (changelog-backed, efficient)** — do NOT bulk-fetch raw `changelog`. Use status-history JQL:
  - passed to test (dev): `status CHANGED TO "Ready for test" BY "<accountId>" DURING ("<from>","<to>")`
  - passed to review (analyst/designer): `status CHANGED TO "On review" BY "<accountId>" DURING (...)`
  - bucket dynamics by running the `DURING` clause per period (month/sprint/quarter). Delivery metrics (closed count + SP) come from `resolutiondate` + SP without any changelog.
- **quarter-review pagination** — a full-quarter `resolved >= … AND resolved <= …` (3 months) JQL **times out (>180 s)** on this Jira. Fetch **per month** (Apr / May / Jun) and sum. "Epics fully closed in quarter": `issuetype = Epic AND status CHANGED TO Done DURING (<quarter>)`.
- **initiative-status** — `cf[10014] = "<epic>"` returns the whole child tree; `statusCategory` → % done; group by the `X.Y` sub-feature code in the summary; blockers = `customfield_10021` (Flagged) non-null + status `On hold` + `is blocked by` links.
