# Integration Strategy

This document defines how every skill in the Grow Product Manager plugin connects to external products and services. Follow this three-step fallback chain **every time** a skill needs to interact with an external tool.

> **Host capabilities**: which of the three steps below exist at all depends on the host — see `host-profiles.md` (capability **MCP**, and Step 0-host for how to observe it). Tool namespaces in particular are host-specific: a namespace named here is an observation from one host, never a contract.
>
> **Data confidentiality**: Before gathering any data, also read and follow `data-policy.md`. Confidential data (Tableau, internal analytics, research materials, trade secrets) must NOT be passed to external LLMs or third-party services. This restriction applies regardless of which integration method is used.

---

## Fallback Chain

> **Tier-0 (design work only):** for hi-fi design / screen-generation, `design-bridge` first checks the user's declared external design toolkits (`design_toolkits[]` in `local-context.md`) per `design-toolkit-protocol.md`. A matching toolkit is used before the MCP→Registry→Browser chain below. If none matches, continue with Step 1. This tier applies only to design delegation, not to general product integrations.

### Step 1: Use existing MCP connector

Check if an MCP connector for the target product is already available in the current session. Two sources, in this order:

**1a. Declared connectors (`.mcp.json`).** The plugin declares the connectors it relies on. The host matches each entry to the user's connections — by URL for remote servers, by name for entries with an empty `url` (first-party connectors whose endpoint is dynamic) — and lists them in the plugin's **Connectors** tab with a connected / not-connected state. Their tools appear in the session under the *connector's* namespace, not the plugin's:

The namespace is **host-dependent**: the same declared server gets a different prefix on a different host, so the namespace columns are one observation per host, not a contract — the source of truth is **1b (pattern detection)**, which matches on the tool name. Codex column from the v3.0.0 pilot: the **CLI** does not match a connector by name — an entry with an empty `url` is opened as an HTTP transport and fails with `relative URL without a base` at every session start, so those four are dead in the CLI and only pattern detection (1b) can find an equivalent; the Codex **desktop app** matches by name and shows them as connected. The four empty-`url` entries are **kept on purpose**: name matching is how Claude's Connectors tab links first-party connectors, and dropping them would remove that; if Codex adopts the same convention they start working there without a plugin change. The remote entries stay TBD until a Codex session with an authorized connector is measured.

| `.mcp.json` key | Connector (host directory name) | Namespace — Claude / Cowork | Namespace — Codex CLI | Ping (auth + access) |
|---|---|---|---|---|
| `atlassian` | Atlassian Rovo | `mcp__Atlassian_Rovo__*` | TBD — verify in stage 3 | `getAccessibleAtlassianResources` (v1 and v2 — 1c) |
| `figma` | Figma | `mcp__Figma__*` | TBD — verify in stage 3 | `whoami` |
| `gmail` | Gmail | `mcp__Gmail__*` | CLI: not usable, empty `url` fails at session start; app: connected by name (pilot, v3.0.0) | `list_labels` |
| `google calendar` | Google Calendar | `mcp__Google_Calendar__*` | CLI: not usable, empty `url` fails at session start; app: connected by name (pilot, v3.0.0) | `list_calendars` |
| `google drive` | Google Drive | `mcp__Google_Drive__*` | CLI: not usable, empty `url` fails at session start; app: connected by name (pilot, v3.0.0) | `list_recent_files` |
| `fireflies` | Fireflies | `mcp__Fireflies__*` | CLI: not usable, empty `url` fails at session start; app: connected by name (pilot, v3.0.0) | `fireflies_get_user` |
| `lazyweb` | Lazyweb | `mcp__lazyweb__*` (measured, Cowork 2026-09-10) | TBD | `lazyweb_health` |
| `similarweb` | Similarweb | TBD | TBD | `get-websites-website-rank` |
| `mobbin` | Mobbin | TBD | TBD | `search_screens` |
| `semrush` | Semrush | TBD | TBD | `domain_overview` |
| `tavily` | Tavily | TBD | TBD | `tavily_search` |
| `apify` | Apify | TBD | TBD | `search-actors` |

Namespaces are what the host showed in real sessions; a differently-named connection (an org's custom Atlassian server, a self-hosted Figma proxy) may expose a different prefix — that is what 1b is for. A declared connector that is **not connected** is the user's decision: say which tab to connect it in, do not search the registry for it (Step 2 is for products the plugin does not declare).

**Not declared on purpose:** Tableau (a local MCP server the user runs; in hosted sessions it appears as `mcp__remote-devices__Tableau__*`), Notion, Slack, Obsidian, and an organisation's own code-search server (a GitLab indexer reachable only over a VPN, bridged locally like Tableau — the user describes it in `local-context.md` under Integrations & Data Sources) — detected by pattern only.

**Shared-context providers (since v3.10.0).** A team's or an organisation's core knowledge served by an MCP server — often reachable only over a VPN and bridged locally — is not declared here either: each provider is described by its own manifest and registered per user (`context-provider-protocol.md` §3). Detect it by the contract, not by a name: a server exposing `vault_search` and `vault_get_note` speaks `vault/v1`. Its local folders are behind the plugin's write boundary (§7 there).

**Optional research connectors (v3.3.0).** `lazyweb`, `similarweb`, `mobbin`, `semrush`, `tavily`, `apify` are declared so the Connectors tab shows them, but no skill requires them: `product-landscape` and `flow-walkthrough` say in one line which optional sources are present and continue without the rest. Each is a paid or account service the user registers for; keys live in the host's connector configuration, never in the plugin. `tavily` matters on hosts without a built-in web search (Codex, ChatGPT); `apify` is the only route to Google Play charts and reviews.

**1b. Pattern detection.** For anything not covered by 1a — or when the declared namespace is absent but the product might still be connected under another name — look at the available tools. MCP tools follow the pattern `mcp__<id>__<tool_name>`. Common connectors:

| Product | Tool pattern to look for | Example tools |
|---------|-------------------------|---------------|
| Jira | `mcp__*__*Jira*` | `searchJiraIssuesUsingJql`, `createJiraIssue` |
| Confluence | `mcp__*__*Confluence*` | `getConfluencePage`, `createConfluencePage` (v1); `getConfluenceContent`, `createConfluenceContent` (v2 — 1c) |
| Google Drive | `mcp__*__*drive*`, `mcp__*__*gdrive*` | `list_files`, `read_file`, `search_files` |
| Figma | `mcp__*__get_screenshot`, `mcp__*__get_design_context` | `get_screenshot`, `get_metadata` |
| Notion | `mcp__*__notion-*` | `notion-search`, `notion-create-pages` |
| Tableau | `mcp__*__list-workbooks`, `mcp__*__query-datasource`, `mcp__*__get-view-data`, `mcp__*__get-view-image` | `list-workbooks`, `query-datasource`, `get-view-data`, `get-view-image`, `search-content`, `list-pulse-metric-definitions-from-definition-ids`, `list-pulse-metrics-from-metric-ids`, `generate-pulse-insight-brief`, `generate-pulse-metric-value-insight-bundle` |
| Google Calendar | `mcp__*__list_events`, `mcp__*__list_calendars` | `list_events`, `get_event`, `create_event` |
| Gmail | `mcp__*__search_threads`, `mcp__*__list_labels` | `search_threads`, `get_thread`, `create_draft` |
| Fireflies | `mcp__*__fireflies_*`, `mcp__*__get_transcripts` | `fireflies_get_transcripts`, `fireflies_search` |
| Code search over the organisation's repositories (a GitLab indexer such as `gin`) | `mcp__*__search_code`, `mcp__*__find_definition`, `mcp__*__get_file` | `search_code`, `find_definition`, `get_file` |

**If found** → use the MCP tools directly. Proceed with the skill workflow.

> **Provenance:** when a datapoint could have come from either a declared connector or a pattern-detected one, name the actual server in the artifact's source marker (e.g. `Atlassian_Rovo`), not the product — the user can then audit which connection answered.

**1c. Atlassian MCP v1 and v2.** Two Atlassian servers are in use: v1 (`https://mcp.atlassian.com/v1/mcp`, «Atlassian Rovo», the URL `.mcp.json` declares) and v2 (`https://mcp.atlassian.com/v2/mcp`), which another plugin's setup script may register under the same name `atlassian`, replacing the user's v1 registration. Tell them apart by an observed tool, not by the server's name: `getConfluencePage` → v1; `getConfluenceContent`, `discover` or `executeRead` → v2. Both can be connected at once; either works. Skills name the v1 tools; on v2 use the table below. On v2 a tool that is not primary runs through `executeRead` / `executeWrite` with `name` and a flat `inputs` object, and `discover` returns its inputs. Three differences change the outcome without an error, so they are mandatory:

1. **Read a page with `detail: "full"`.** `getConfluenceContent` defaults to `detail: "summary"` — an excerpt of a few hundred characters (measured 2026-10-29: a 3136-word page came back as a ~300-character excerpt). A skill that reads requirements, a concept or a library page without it works on the excerpt.
2. **Update with a fresh `snapshotToken`.** `updateConfluenceContent` takes the token from `getConfluenceContent(draft: true, detail: "full")`; a stale token means re-read and re-apply the change, never resend the same payload.
3. **Ping with `getAccessibleAtlassianResources`.** `getVisibleJiraProjects` and `getConfluenceSpaces` are not primary tools on v2; their absence is not a missing connector.

| v1 | v2 | v2 call | What changes |
|---|---|---|---|
| `getConfluencePage` | `getConfluenceContent` | primary | `detail: "full"` for the body; returns `snapshotToken` |
| `createConfluencePage` | `createConfluenceContent` | primary | `contentType: "page"`; `parent: {spaceId}` takes the numeric id — resolve a key with `listConfluenceSpaces` (`keys`); `body: {format, value}`; read the space instructions with `getConfluenceSpace` (`executeRead`) before writing |
| `updateConfluencePage` | `updateConfluenceContent` | primary | `snapshotToken` required; `edits[]` for a granular change instead of a full `body` |
| `searchConfluenceUsingCql` | `searchConfluence` | primary | same CQL; `cursor` for the next page |
| `getConfluenceSpaces` | `listConfluenceSpaces` / `getConfluenceSpace` | `executeRead` | |
| `createJiraIssue` | `createJiraIssue` | primary | `issueType` (not `issueTypeName`), `assignee` (not `assignee_account_id`), `priority` and `labels` are top-level; `contentFormat` is `markdown` or `html` |
| `editJiraIssue` | `editJiraIssue` | primary | multi-value fields (labels, components) are replaced, not appended — send the whole list |
| `getJiraIssue`, `searchJiraIssuesUsingJql` | same names | primary | the default `compact` view has no custom fields — `view: "evidence"` or `fields: ["customfield_…"]` (the Team field) |
| `lookupJiraAccountId`, `getJiraIssueTypeMetaWithFields` | same names | `executeRead` | an assignee: `listJiraIssueAssignableUsers` |
| `getVisibleJiraProjects` | `listJiraProjects` | `executeRead` | |
| `getJiraProjectIssueTypesMetadata` | `listJiraProjectIssueTypesMetadata` | `executeRead` | |
| `createIssueLink`, `getIssueLinkTypes` | `createJiraIssueLink`, `listJiraIssueLinkTypes` | `executeWrite` / `executeRead` | |
| `getAccessibleAtlassianResources`, `atlassianUserInfo` | same names | primary | pass the `cloudId` explicitly on every call |

The write gate covers `createConfluenceContent` and `updateConfluenceContent` as it covers their v1 names (`hooks/hooks.json`, `artifact-style-gate.md` → Host write gate); `executeWrite` is not gated on either version, as v1 comments and links were not.

### Step 2: Search for an MCP server

If no connector is available for the needed product, search the MCP registry.

**Action**: Call `search_mcp_registry` with relevant keywords for the product:

```
search_mcp_registry(["product-name", "category-keyword"])
```

Examples:
- Google Drive → `["google-drive", "gdrive", "google docs"]`
- Tableau → `["tableau", "analytics", "dashboard"]`
- GPT/OpenAI → `["openai", "gpt", "ai"]`
- Gemini → `["gemini", "google-ai"]`
- Slack → `["slack", "messaging"]`
- GitHub → `["github", "git", "repository"]`

**If found** → call `suggest_connectors` to recommend the user installs it. Explain what it does and why the skill needs it. Wait for the user to connect before proceeding.

**If the MCP server exists but lacks the specific functionality needed** → proceed to Step 3.

### Step 3: Fall back to browser

If no MCP connector or server covers the needed functionality, use Claude in Chrome to interact with the product's web interface directly.

**Action**: Use browser tools in this order:

1. `navigate` — open the product's web URL
2. `read_page` / `get_page_text` — read the current page content
3. `form_input` — fill in forms, search fields
4. `computer` — click buttons, interact with UI elements
5. `find` — locate specific elements on the page
6. `javascript_tool` — execute JS for advanced interactions

**Guidelines for browser fallback**:
- Always navigate to the product first before attempting interactions
- Use `read_page` to understand page structure before clicking
- Prefer direct URLs when possible (e.g., `https://your-domain.atlassian.net/wiki/spaces/SPACE/pages/PAGE_ID`, `https://drive.google.com/file/d/FILE_ID`)
- If the user needs to log in, ask them to do so first and then retry
- Be mindful of rate limits on web applications

**Driving the product itself** (walking a customer journey step by step, on web, desktop or a phone) is not an integration fallback — it is its own protocol: `references/app-drive-protocol.md`, owned by `flow-walkthrough`.

---

## Decision Flow Summary

```
Need to interact with [Product X]
    │
    ├─ Is there an MCP connector in session?
    │   ├─ YES → Use MCP tools ✅
    │   └─ NO ↓
    │
    ├─ Search MCP registry for [Product X]
    │   ├─ FOUND → suggest_connectors, wait for install ✅
    │   └─ NOT FOUND (or missing features) ↓
    │
    └─ Use Claude in Chrome browser tools 🌐
```

## Per-product tool guidance — Tableau

If the Tableau MCP connector is available, choose the tool by task:

| Task | Tool | When to use |
|------|------|-------------|
| Find a workbook/dashboard by name | `search-content` (filter `contentTypes=workbook,view`) | User named the dashboard in words, ID unknown |
| List workbooks in a project | `list-workbooks` (filter `projectName`) | Inventory, validating URLs from `local-context.md` |
| Pull tabular data from a view | `get-view-data` | A/B test results, funnel metrics, exact numbers |
| Pull a dashboard image | `get-view-image` | Export into a report/handoff/presentation |
| Run an SQL query against a published datasource | `query-datasource` | Custom slice not exposed in any view |
| List Pulse metrics for the product | `list-pulse-metric-definitions-from-definition-ids` + `list-pulse-metrics-from-metric-ids` | Health check, monitoring of key metrics |
| Insights for a Pulse metric | `generate-pulse-insight-brief` / `generate-pulse-metric-value-insight-bundle` | "What's interesting about [metric] right now?" |

**Browser fallback** is still used for interactive dashboards with complex filters that cannot be set through Tableau API parameters, and when the user provided only a URL with no parsing surface.

When logging the data source in any report's Sources section, mark Tableau-sourced data as `tableau-mcp` (used MCP) or `tableau-web` (used browser fallback) so the user can audit which method retrieved each datapoint.

---

## Applying This Strategy

Every skill MUST follow this chain before interacting with any external product. In practice:

1. At the **start of a skill execution**, inventory which external products are needed
2. For each product, run through the fallback chain
3. If multiple products need browser fallback, handle them one at a time
4. Log which integration method was used so the user knows how data was retrieved

**Informing the user**: When falling back to browser, briefly let the user know:
> "I don't have a direct connector for [Product], so I'll use the browser to access it."

This keeps things transparent without overloading the user with technical details.
