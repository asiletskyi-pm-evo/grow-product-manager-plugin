# Observing your context in the connectors (since v3.22.0)

`ctx` calls no connector: it is a deterministic script. A skill that sets up or checks the context — `plugin-configurator` (onboarding and Validate), `focus-advisor` (the weekly recheck), `/grow-product-manager:context recheck` — reads the connectors **read-only** by the map below and writes what it saw into one **observation file**. `ctx bootstrap --observed <file>` turns it into a table of differences; `ctx validate --recheck --observed <file>` into the inbox's deltas. How sure a fact is, which facts are too thin to show and what of a meeting or a mail is never kept are decided by `ctx` (`scripts/ctx_observe.py`), never by the skill. Semantics of the commands: `context-protocol.md` §5k–§5m.

## 1. Rules for the skill

- **Read only.** Only tools that read: `atlassianUserInfo`, `getAccessibleAtlassianResources`, `getVisibleJiraProjects`, `searchJiraIssuesUsingJql`, `getConfluenceSpaces`, `searchConfluenceUsingCql`, `lookupJiraAccountId`, `list_calendars`, `list_events`, `fireflies_get_transcripts`, Tableau `list-workbooks` / `search-content`. Never a tool that creates, edits, moves, shares or deletes. Tool names differ between connector builds — detect them by pattern (`integration-strategy.md` 1b).
- **Nothing of a meeting or a letter.** From a calendar or Fireflies the skill takes only who took part and how often; from mail only the domain of your address. It does not put an event's title, description, attendees' answers, a transcript, a subject or a body into the file. `ctx` drops `ref` and `evidence` of every `calendar:*`, `fireflies:*` and `mail:*` fact anyway and words the count itself.
- **The file lives in the session's scratchpad**, never in the store or the vault, and is deleted after `ctx bootstrap --apply` or the recheck. Internal data stays in the session (`data-policy.md`).
- **Say what did not answer.** Every connector the run tried is in `connectors` with `ok`, `absent` (not connected) or `error: <why>`. A fact from a connector that is not `ok` is refused; the recheck never reads «absent» as «gone».
- **Budget.** At most one call per row of §3 per connector, a page of at most 100 results; a connector that does not answer in 20 s is `error: timeout`. A list that was cut by paging is not `complete`.

## 2. The file — `context-observed/1`

```json
{"schema": "context-observed/1", "at": "2026-10-27",
 "connectors": {"atlassian": "ok", "calendar": "ok", "mail": "absent", "fireflies": "error: timeout", "tableau": "ok",
                "provider:zorg-brain": "ok"},
 "facts": [
   {"type": "profile", "field": "Email", "value": "pm@zorg.example", "from": "atlassian:user", "ref": "atlassianUserInfo"},
   {"type": "product", "title": "Zorg App", "field": "Jira Project Key", "value": "PROJ", "from": "jira:active", "count": 14},
   {"type": "product", "title": "Zorg App", "list": "Dashboards", "value": "Zorg funnel — https://…", "from": "tableau:owned"},
   {"type": "team", "title": "Alpha (A)", "from": "provider:identity"},
   {"type": "team", "title": "Alpha (A)", "list": "Members", "value": "Cid Three", "from": "calendar:co-attendee", "count": 6}],
 "checks": {
   "jira:visible": {"complete": true, "values": [{"key": "PROJ", "name": "Zorg App"}]},
   "confluence:visible": {"complete": true, "values": ["ZAPP"]},
   "atlassian:people": {"complete": true, "active": ["Alex One"], "inactive": ["Bea Two"]}}}
```

- A **fact**: `type` (`profile`, `org`, `product`, `team`); `title` — the organisation's, product's or team's name as you would write it in the heading (`Zorg App`, not `Product: Zorg App`), none for the profile; then `field` (a `- **Field:** value` line, names as `context-fields.yaml` and Step 16 give them: `Name`, `Email`, `Role`, `Language`; `Domain`, `Jira`, `Confluence`; `Jira Project Key`, `Confluence Space`, `URL`, `Platforms`) **or** `list` (a line under `#### <list>`: `Members`, `Dashboards`) with its `value` — or neither: the record itself exists (a product you work on, the team a provider puts you in). `from`, and as needed `ref` (where — a tool, a key), `evidence` (≤ 200 characters) and `count`.
- **Never** `confidence`: a fact that brings one is refused.
- A fact that is wrong, below its threshold, from a connector that did not answer, or holds a secret or an identifier (`ctx_never`) is **dropped** with why — never its value — and the others are kept. A file of another shape is refused whole.
- `checks` — only for the recheck (§4): what the connector lists in full. `complete: true` only when the list was not cut.

## 3. Where a fact comes from, and how sure it is

The confidence is `ctx`'s, by where the fact came from:

| `from` | Call (pattern) | Gives | Confidence |
|---|---|---|---|
| `atlassian:user` | `atlassianUserInfo` | the profile's `Name`, `Email` | high |
| `atlassian:site` | `getAccessibleAtlassianResources` | the organisation's `Jira`, `Confluence` (the site's URL, nothing after the host but `/wiki`) | high |
| `mail:domain` | your address (from `atlassianUserInfo` or the mail connector's profile) | the organisation's `Domain` | high |
| `calendar:owner` | `list_calendars` — the primary calendar's id | the profile's `Email` | high |
| `provider:identity` | a registered provider's access bundle (`provider_bundle.py`: your mail → team → role) | the team (the record itself) — high; the profile's `Role` — medium | high / medium |
| `local-context` | your `local-context.md` as it is | any field it already has | high |
| `user` | your answer to a question of the configurator | any field | high |
| `jira:active` | `searchJiraIssuesUsingJql`: `(assignee = currentUser() OR reporter = currentUser() OR comment ~ currentUser()) AND updated >= -90d`, grouped by project | a product with its `Jira Project Key` | medium |
| `confluence:active` | `searchConfluenceUsingCql`: `contributor = currentUser() AND lastmodified >= now("-90d")`, grouped by space | the product's `Confluence Space` | medium |
| `jira:visible` | `getVisibleJiraProjects` without your activity | a product you can see, with its `Jira Project Key` | low |
| `confluence:visible` | `getConfluenceSpaces` without your activity | a product's `Confluence Space` you can see | low |
| `calendar:co-attendee` | `list_events` of the last 30 days — only the attendees | a name for the team's `Members` list | low |
| `fireflies:participant` | `fireflies_get_transcripts` of the last 30 days — only the participants | a name for the team's `Members` list | low |
| `tableau:owned` | Tableau `list-workbooks` / `search-content` owned by you | a line for the product's `Dashboards` list: «name — link» | low |

**A source gives only what its row says** — a fact asking more of it is dropped: a calendar never gives a product's field, Jira activity never gives your e-mail. `local-context` and `user` may give any field. And **the value must have its field's shape**, or the fact is dropped: `Email` an address, `Domain` a domain, `Jira` / `Confluence` the site's URL, `Jira Project Key` capitals and digits, `Confluence Space` a space key, a `Dashboards` line a name and a link, `Name` and a `Members` line a person's name — at most five words, each with a capital letter, no digits. A meeting's title or a letter's subject has none of these shapes. The organisation's name from `mail:domain` or `atlassian:site` is the domain's or the site's own word (`zorg.example` → `Zorg`); another name comes from your answer (`user`). A fact about the record itself (no `field`, no `list`) carries no `value`.

**Thresholds** — below them the fact is dropped («нижче порогу»):
- `jira:active` — ≥ 5 issues of yours in 90 days in the project;
- `confluence:active` — ≥ 3 pages you created or edited in 90 days in the space;
- `calendar:co-attendee` — ≥ 3 meetings together in 30 days.

**What happens to a fact** (`ctx bootstrap`, `context-protocol.md` §5k): high and medium → a row of the table you confirm; low → a delta of the inbox, after the table is saved (its record must exist by then); a fact that agrees with your context → counted, not shown.

## 4. The recheck — what is checked

| Check | Call | In `checks` |
|---|---|---|
| a product's Jira key is still there | `getVisibleJiraProjects` (all pages) | `jira:visible` — `[{key, name}]` |
| a product's Confluence space is still there | `getConfluenceSpaces` (all pages) | `confluence:visible` — `[{key, name}]` or keys |
| a team's members are still active people of the site | `lookupJiraAccountId` for each name of `Members` | `atlassian:people` — `active`; `inactive` only for an account found and **deactivated**; `unknown` for a name the lookup found no one for (another spelling, a nickname — never evidence); `complete: true` when every member was looked up |
| the role a provider gives you | the provider's access bundle | a `provider:identity` fact with `field: Role` |

A connector that is not `ok`, or a list that is not `complete`, checks nothing. `at` is required: it is the day of the look. A finding becomes a delta only when the next recheck, at least 6 days later, sees it again (`context-protocol.md` §5l).
