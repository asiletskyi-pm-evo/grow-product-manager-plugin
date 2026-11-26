# jira-data-protocol (shared)

How to fetch and parse Jira data reliably for ops reports and planning. Shared by `product-reporter`, the Planning Suite (`sprint-planning`, `quarterly-planning`, `project-planning`, `roadmap-architect`), and `focus-advisor` (per-key reads only). All org-specific ids live in `local-context.md` — never hardcoded here.

## Custom-field map (PROJ)

| Field | ID | Notes |
|---|---|---|
| Team | `customfield_10001` | Atlassian Team object. JQL by **id**: `cf[10001] = "<team-uuid>"` (local-context → `product.jira_team_id`). Filtering by name does not work. |
| Story Points | `customfield_10036` | number; null → treat as 0 |
| Story point estimate | `customfield_10016` | team-managed alt; PROJ uses 10036 |
| Developer | `customfield_10041` | user object |
| QA | `customfield_10037` | user object |
| Epic Link | `customfield_10014` | string key (`PROJ-…`, or a cross-project key `<OTHER>-…`) = the "feature" level |
| Sprint | `customfield_10020` | array of `{id,name,state,startDate,endDate,completeDate}` — full history |
| FLAG | `customfield_10043` | feature flag |
| fixVersions | `fixVersions` | releases (`name`, `releaseDate`, `released`) |
| resolutiondate | `resolutiondate` | use for "closed in period" |

**Cloud ID and sprint ids are NOT hardcoded.** Cloud ID: local-context → `product.atlassian_cloud_id` (resolve once via `getAccessibleAtlassianResources`). Sprint ids: resolve at runtime — use `openSprints()` / `closedSprints()` in JQL, or read `customfield_10020` (`{id,name,state,…}`) from issues, or query the board's sprints, then map name → id. Never store a sprint id as a default: they go stale every sprint.

## Per-mode JQL

```
# sprint-plan (open or named sprint)
project = PROJ AND cf[10001] = "<team-id>" AND sprint in openSprints() ORDER BY cf[10014] ASC, status ASC
# or a named/closed sprint:
... AND sprint = <sprintId> ...

# sprint-review (completed work in a sprint)
project = PROJ AND cf[10001] = "<team-id>" AND sprint = <sprintId> AND statusCategory = Done ORDER BY resolutiondate
# all sprint scope (for % done): drop the statusCategory clause

# quarter-review (date range; pair with sprint set if needed)
project = PROJ AND cf[10001] = "<team-id>" AND resolutiondate >= "YYYY-MM-DD" AND resolutiondate <= "YYYY-MM-DD" AND statusCategory = Done
# epics rolled up in the quarter:
project = PROJ AND cf[10001] = "<team-id>" AND issuetype = Epic

# initiative-status (tree under a key)
parent = <KEY>           # direct children
"Epic Link" = <EPIC>     # tasks under an epic (or cf[10014] = "<EPIC>")

# member-review (one person over a period, any role)
project = PROJ AND (assignee = <accountId> OR cf[10041] = <accountId> OR cf[10037] = <accountId>)
  AND updated >= "<from>" AND updated <= "<to>"
# closed-by-them in period:
... AND statusCategory = Done AND resolutiondate >= "<from>" AND resolutiondate <= "<to>"
```

## Large-response extraction (mandatory)

A search over a sprint or a quarter does not fit inline: the host **saves the response to a file** and shows its path (measured 2026-11-26 on Atlassian MCP v2: 100 issues with eight fields — about 380 000 characters, two fifths of them avatar links). Do not read that file whole.

1. **Ask only for the fields the mode needs** (`fields: ["summary", "status", "customfield_…"]`). With an explicit list v2 returns no description; `view: "evidence"` brings every comment of every issue, so it is not the way to custom fields in a search (`integration-strategy.md` 1c, point 4).
2. **Know the shape.** It differs between the two servers, and a reader of the wrong one finds nothing and reports every estimate as missing:

   | | v2 | v1 (until 2027-03-01) |
   |---|---|---|
   | a custom field | `fields.customFields["<display name>"] = {"id": "customfield_N", "value": …}` | `fields.customfield_N = …` |
   | a field with no value | absent | `null` |
   | a user | `accountId`, `emailAddress`, `avatarUrls`, `displayName`, … | the same, after a `self` link |

   Read a custom field by its **id**, never by its display name: the name is the site's own and changes with its language.
3. **With SHELL — the script.** `python3 scripts/jira_rows.py <saved file> [<saved file> …]` prints one JSON line per issue, the same for both shapes: `key`, the system fields that came (`summary`, `status`, `category` — the status category's key, `type`, `assignee`, `resolved`, `versions`, `labels`, `parent`), `cf` — the custom fields by id, and `closed_sprints`. A user is `{"id", "name"}` — the account id and the display name; an e-mail address, a description and a comment's text never reach a row. A custom field with no value has no key in `cf`: read it as null (Story Points → 0). The sprints printed are the ones not closed; `--sprint-history` prints the whole history with dates (member-review buckets). After a file's rows comes `{"_page": …}`: `has_next`, `next_page_token` for the next page, `shape`, and on v2 `cf_names` — the display name of each id, the quickest way to learn a site's field ids. A file that is not a Jira response is exit 2: say so, never report from nothing.
4. **No shell — `Grep -o`** the saved file with one alternation of the patterns below and parse the matches in document order. A `"key":` match opens a node; a field with no match before the next key has no value. Never align the matches by count — on v2 an empty field leaves no line.

```
"key":"PROJ-[0-9]+"
"summary":"(\\.|[^"\\])*"
"assignee":(null|\{"accountId":"[^"]*")
"id":"customfield_10014","value":"[A-Z][A-Z0-9]*-[0-9]+"
"id":"customfield_10036","value":[0-9.]+
"id":"customfield_10041","value":\{"accountId":"[^"]*"
"id":"customfield_10037","value":\{"accountId":"[^"]*"
"displayName":"[^"]*"   # the name of the user whose accountId matched just before it
statuses/[a-z]*\.png","name":"[^"]*"   # status name (not statusCategory)
"state":"closed"   # count per node to detect carried-over (see below)
"id":[0-9]+,"name":"[^"]*","state":"[a-z]+"   # sprint entries
```

On v1 the custom-field lines are `"customfield_10014":(null|"[A-Z]+-[0-9]+")`, `"customfield_10036":(null|[0-9.]+)` and `"customfield_10041":(null|\{"self":"[^"]*","accountId":"[^"]*"`; the rest is the same.

Notes:
- The "Team = name" form returns 0; always use the team **id**.
- A person is named by `displayName`; a roster in local-context is needed only to map a name to a role.

## Pagination

`maxResults` ~100/page; `pageInfo.hasNextPage` + `endCursor` → pass as `nextPageToken`. The token is `next_page_token` in the script's `_page` line (no shell: grep the saved file for `"endCursor":"[^"]*"`). Large cross-functional teams span 3+ pages. The search endpoint can time out (~180s) on deep pages — retry, or fetch the tail by explicit `key in (...)`.

## Carried-over vs new (sprint-plan)

Issues keep their **entire** sprint history in `customfield_10020`. Definition:
- **New** (planned at this sprint's grooming) = history contains **no** `"state":"closed"` sprint (only the one active sprint).
- **Carried** = ≥1 closed sprint in history.
It is `closed_sprints` in the script's row (no shell: count the `"state":"closed"` occurrences between one node's key and the next).

## Status transitions (member-review)

Prefer the status-history JQL of *Validated conventions* below. For one issue's whole history on v2 use `listJiraIssueChangelogs` (`executeRead`) — `expand: "changelog"` on `getJiraIssue` returns only the newest page there — and read `items[].field == "status"` transitions with timestamps. Map to role events:
- **passed to test** (dev) — transition to `Ready for test`.
- **tested** (QA) — transition out of testing to `Documentation`/`Ready`/`Done`-side, or `In test → Ready`.
- **passed to review** (analyst/designer) — transition to `On review`.
- **closed** — transition into a `done` status-category status, with `resolutiondate`.
Aggregate counts and SP by the chosen granularity (day/week/sprint/month/quarter/year) for the dynamics series. Sprint buckets come from `customfield_10020` start/end dates.

## Confluence publishing

- `createConfluenceContent` (`contentType: "page"`, `body: {format: "html", value}`), `parent: {spaceId}` — the numeric id of local-context → product.confluence_space (a key → `listConfluenceSpaces` with `keys`, `integration-strategy.md` 1c), and `parentContentId` = a **page or folder** id (folder works).
- Tables: `<th>` header cells, **no "№" column**, header block in `<div data-type="panel-info">`, link Jira keys/epics and the board.
- Escape `&` → `&amp;` in cell text (e.g. "Q&amp;A", "UI&amp;UX").

## Validated conventions (v1.14.0 — from test runs)

These were confirmed against real PROJ data during skill bring-up:

- **"Closed" = statusCategory `Done`** — and this category **includes the `Ready` status** (A/B-rolled-out tasks often sit in `Ready`, not `Closed`). Count both. Use `statusCategory = Done` in JQL, not `status = Closed`.
- **Releases** — issues carry their **entire** fixVersions history (back years). For "releases in period", filter `fixVersions.releaseDate` to the period window and group by **stream**. The stream set is product-specific (local-context → `product.release_streams`); a typical shape is one stream per platform plus per-service streams, each with its own version format — e.g. `[B2C][Android] …` / `[B2C][iOS] …` for apps, `<web-ui-stream>: vYYYY…`, backend `YY.NN.N`, `<service>: …`. Show all configured streams.
- **Feature flags** — `customfield_10043` (FLAG) holds flag name(s), sometimes comma-separated, suffixes `_AB` / `_ENABLED`. **Enabled / A-B launched** = FLAG present on the task. **Disabled / removed** = tasks whose summary matches the team's flag-cleanup wording (product-specific, in the team's working language — e.g. "Remove flag …"; keep the pattern in local-context → `product.flag_cleanup_pattern`).
- **member-review transitions (changelog-backed, efficient)** — do NOT bulk-fetch raw `changelog`. Use status-history JQL:
  - passed to test (dev): `status CHANGED TO "Ready for test" BY "<accountId>" DURING ("<from>","<to>")`
  - passed to review (analyst/designer): `status CHANGED TO "On review" BY "<accountId>" DURING (...)`
  - bucket dynamics by running the `DURING` clause per period (month/sprint/quarter). Delivery metrics (closed count + SP) come from `resolutiondate` + SP without any changelog.
- **quarter-review pagination** — a full-quarter `resolved >= … AND resolved <= …` (3 months) JQL **times out (>180 s)** on a large Jira instance. Fetch **per month** and sum. "Epics fully closed in quarter": `issuetype = Epic AND status CHANGED TO Done DURING (<quarter>)`.
- **initiative-status** — `cf[10014] = "<epic>"` returns the whole child tree; `statusCategory` → % done; group by the `X.Y` sub-feature code in the summary; blockers = `customfield_10021` (Flagged) non-null + status `On hold` + `is blocked by` links.
