# Integration Strategy

This document defines how every skill in the Grow Product Manager plugin connects to external products and services. Follow this three-step fallback chain **every time** a skill needs to interact with an external tool.

> **Data confidentiality**: Before gathering any data, also read and follow `data-policy.md`. Confidential data (Tableau, internal analytics, research materials, trade secrets) must NOT be passed to external LLMs or third-party services. This restriction applies regardless of which integration method is used.

---

## Fallback Chain

### Step 1: Use existing MCP connector

Check if an MCP connector for the target product is already available in the current session.

**How to check**: Look at available tools in the session. MCP tools follow the pattern `mcp__<id>__<tool_name>`. Common connectors:

| Product | Tool pattern to look for | Example tools |
|---------|-------------------------|---------------|
| Jira | `mcp__*__*Jira*` | `searchJiraIssuesUsingJql`, `createJiraIssue` |
| Confluence | `mcp__*__*Confluence*` | `getConfluencePage`, `createConfluencePage` |
| Google Drive | `mcp__*__*drive*`, `mcp__*__*gdrive*` | `list_files`, `read_file`, `search_files` |
| Figma | `mcp__*__get_screenshot`, `mcp__*__get_design_context` | `get_screenshot`, `get_metadata` |
| Notion | `mcp__*__notion-*` | `notion-search`, `notion-create-pages` |
| Google Calendar | `mcp__*__gcal_*` | `gcal_list_events`, `gcal_create_event` |
| Gmail | `mcp__*__gmail_*` | `gmail_search_messages`, `gmail_create_draft` |
| Fireflies | `mcp__*__fireflies_*` | `fireflies_get_transcripts`, `fireflies_search` |

**If found** → use the MCP tools directly. Proceed with the skill workflow.

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
