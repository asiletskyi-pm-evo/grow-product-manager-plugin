---
name: plugin-configurator
version: 0.4.0
description: Configure the Grow Product Manager plugin for your organization, products, teams, and data sources. Use when the user asks to "configure plugin", "set up plugin", "set up context", "add a product", "update configuration", "validate setup", "show config", or when any other skill detects that local-context.md does not exist.
---

# Plugin Configurator

Configure the Grow Product Manager plugin for your organization. This skill collects all necessary context — products, teams, data sources, analytics tools, OKRs, repositories — and generates a `local-context.md` file that all other skills use as their primary context source.

Supports multiple organizations, products, and projects simultaneously.

## Four Modes

| Mode | When to use | What it does |
|------|------------|--------------|
| **Onboarding** | First launch, `local-context.md` doesn't exist | Full guided setup: user profile → organizations → products → teams → data sources → review → validation |
| **Update** | `local-context.md` exists, user wants to change something | Edit a specific section: add product, update team, change dashboard URLs, add OKRs, etc. Always shows changelog |
| **Validate** | User wants to check everything works | Test all MCP connections, verify data access, check context completeness, produce readiness report |
| **View** | User asks to see current config | Display current `local-context.md` contents in a readable format, allow inline edits via dialogue |

## Auto-trigger Protocol

**This section is for ALL other skills in the plugin.**

At the start of execution, every skill MUST check if `local-context.md` exists. Search for it in the following locations (in order):
1. Plugin root directory (relative: `../../local-context.md` from skill folder)
2. User's workspace/outputs folder
3. Session working directory

**If `local-context.md` is NOT found:**
- Stop the current skill workflow
- Inform the user: "To work effectively, the plugin needs to be configured with your organization, products, and tools context. Let's run a quick setup."
- Launch the Plugin Configurator in **Onboarding** mode
- After Onboarding completes — return to the original skill and continue its workflow with the newly created context

**If `local-context.md` IS found:**
- Read it at the start of every skill execution
- Use the context throughout the skill workflow
- If the file exists but is missing fields needed by the current skill — inform the user and offer to run Plugin Configurator in **Update** mode to add missing data, or proceed without that context

## Context File Location

The `local-context.md` file is saved to the **user's workspace folder** (outputs directory). This ensures it persists between sessions and is accessible to the user. The file is personal — it contains organization-specific configuration and should not be shared in public repositories.

## Workflow — Onboarding Mode

### Step 1 — Welcome and auto-discovery

**1a. Greeting and explanation:**

> "Welcome! I'll help you configure the Grow Product Manager plugin for your needs. We'll go through a few steps: profile, organizations, products, teams, and data sources. This will take ~5-10 minutes."

**1b. MCP auto-discovery — scan what's available:**

Before asking questions, proactively scan the session for available MCP connectors:

- Check for Jira MCP → if found, try `getVisibleJiraProjects` to list available projects
- Check for Confluence MCP → if found, try `getConfluenceSpaces` to list available spaces
- Check for Figma MCP → if found, try `whoami` to verify access
- Check for Notion MCP → if found, try `notion-get-teams` to verify access
- Check for Google Calendar MCP → if found, note availability
- Check for Gmail MCP → if found, note availability
- Check for any other MCP connectors available in the session

**1c. Present discovery results:**

Show the user what was found:

> "I scanned the available connections. Here's what I found:"

| Integration | Status | Details |
|-------------|--------|---------|
| Jira | ✅ Connected | Projects found: PROJ-1, PROJ-2, ... |
| Confluence | ✅ Connected | Spaces found: SPACE-1, SPACE-2, ... |
| Figma | ✅ Connected | Account: user@company.com |
| Notion | ❌ Not connected | — |
| Tableau | ❌ Needs URL | We'll configure this later |
| ... | ... | ... |

For missing MCP connectors — note which skills benefit from them and offer to search the MCP registry:
> "Notion MCP is not connected. It is used for publishing documents as an alternative to Confluence. Would you like to connect it?"

### Step 2 — User Profile

Ask via AskUserQuestion:

- **Name** — user's display name (pre-fill from session context if available)
- **Role** — role in the organization (Product Manager, Senior PM, Head of Product, etc.)
- **Email** — for Jira account lookup
- **Preferred language** — uk (Ukrainian) or en (English) for skill output

**Auto-discover Jira account:**
If Jira MCP is available, use `lookupJiraAccountId` with the provided email to find and store the user's Jira accountId.

### Step 3 — Organizations

**3a. Multi-org support — ask via AskUserQuestion:**

> "How many organizations/companies do you work with? The plugin supports working with multiple simultaneously."

- Single organization (most common) → proceed with one
- Multiple organizations → collect info for each, repeating Steps 3-5

**3b. For each organization, collect:**

| Field | How to collect | Auto-discovery |
|-------|---------------|----------------|
| Organization name | AskUserQuestion | — |
| Domain | AskUserQuestion | — |
| Jira instance URL | Auto from MCP, confirm with user | ✅ Extract from Jira MCP base URL |
| Confluence instance URL | Auto from MCP, confirm with user | ✅ Extract from Confluence MCP base URL |

### Step 4 — Products (per organization)

**4a. Product discovery — combine auto + manual:**

If Jira projects were discovered in Step 1:
> "I found these projects in Jira: [list]. Which of them are your products? Some projects may belong to the same product."

Help the user map Jira projects → Products (may be 1:1 or many:1).

**4b. For each product, collect via AskUserQuestion (section by section):**

**Basic info:**
- Product name
- Brief description (1-2 sentences)
- Product URL (if web product)
- Jira project key(s) — pre-filled from discovery

**Platforms:**
> "Which platforms does this product run on?"

Present common options + allow custom:
- App Android
- App iOS
- Web Portal (buyer/user-facing)
- Web CMS (seller/admin-facing)
- Admin panel
- API
- Other (specify)

**Locales/countries:**
> "In which countries/locales does this product operate?"

- All locales (single market)
- Specific locales (list them)

**Confluence configuration:**
If Confluence spaces were discovered:
> "Which Confluence space is used for this product? Found spaces: [list]"

- Default Confluence space
- Requirements template URL (optional) — "Is there a Confluence template for feature requirements?"
- Requirements template name (optional)

**Competitors:**
> "Who are the main competitors of this product? (used for comparative analysis in research)"

Collect: name, URL for each competitor. Minimum 2-3 recommended.

### Step 5 — Analytics & Data Sources (per organization)

**5a. Analytics tools:**

> "Which analytics tools does your organization use?"

For each tool mentioned, collect the base URL and any product-specific dashboard URLs:

| Tool | What to collect |
|------|----------------|
| **Tableau** | Base URL, A/B test dashboard URLs (per platform), main product dashboards |
| **Google Analytics** | Property IDs or dashboard URLs |
| **Amplitude** | Workspace URL |
| **Mixpanel** | Project URL |
| **Custom BI** | Dashboard URLs |
| **Google Sheets** | Key shared spreadsheets with metrics |

**5b. A/B test dashboards (critical for Product Analysis):**

If Tableau or another A/B testing tool is used:
> "Are there separate dashboards for A/B test analysis? If yes, please provide the URL for each platform."

Collect per platform (e.g., Dashboard 1 for Web, Dashboard 2 for Mobile).

**5c. Other data sources:**

- Google Drive folders with research/strategy docs
- Figma workspace/team URL
- Notion workspace (if used alongside Confluence)

### Step 6 — Key Metrics & OKRs (per product)

> "What are the key metrics you track for this product?"

**6a. Key metrics:**
Collect a list of primary metrics with brief descriptions:
- Metric name (e.g., "Conversion Rate", "DAU", "Revenue per User")
- What it measures
- Current approximate value (if known)

**6b. Current OKRs (optional):**
> "Are there current OKRs (quarterly objectives) for this product?"

If yes — collect objectives and key results. These help skills align hypotheses and analysis with strategic goals.

**6c. Metric targets (optional):**
> "Are there target values for the key metrics?"

Collect target values for metrics that have them (e.g., "Conversion Rate → +2% this quarter").

### Step 7 — Teams (per organization)

> "Would you like to configure team information? This will help when creating tasks in Jira."

If yes:

**7a. For each team, collect:**
- Team name
- Jira team ID (auto-discover from existing tasks if possible)
- Members: name, role (FE, BE, Android, iOS, Design, Analytics, QA, PM), Jira accountId (auto-discover via `lookupJiraAccountId`)

**7b. Auto-discovery from Jira:**
If Jira MCP is available and a product's Jira project is known:
- Search for recent tasks to discover team field values
- Extract common assignees and their roles
- Present to user for confirmation

### Step 8 — Repositories & CI/CD (per product, optional)

> "Would you like to add repository and CI/CD information? (for future skills)"

If yes:
- Repository URLs (GitHub/GitLab)
- CI/CD pipeline URLs
- Environment URLs (staging, production)

### Step 9 — Custom Sections

> "Is there any additional information you'd like to save in the plugin context? For example: strategy documents, internal guidelines, specific processes."

Allow free-form markdown sections with custom titles.

### Step 10 — Review, confirm, and save local-context.md

**10a. Compile summary for review:**

Before generating the file, present ALL collected information to the user in a structured summary for confirmation:

> "Here is the collected information. Please review and confirm everything is correct:"

**Summary format:**

```
## Collected information

### User profile
- Name: [name]
- Role: [role]
- Email: [email]
- Jira Account ID: [id or "will be auto-discovered"]
- Language: [language]

### Organization: [name]
- Domain: [domain]
- Jira: [instance URL]
- Confluence: [instance URL]

### Product: [name]
- Description: [description]
- URL: [url]
- Jira project: [key]
- Platforms: [list]
- Locales: [list]
- Confluence space: [space]
- Key metrics: [list]
- OKRs: [list or "not specified"]
- Competitors: [list]
- Analytics: [dashboards list]

### Team: [name]
- Members: [list with roles]

### Custom sections
- [if any]
```

**10b. Collect corrections:**

> "Is everything correct? If anything needs to be fixed — tell me what, and I'll make the changes."

- If the user requests corrections — apply them immediately and show the updated section
- Iterate until the user confirms: "Все ОК" / "Підтверджую"
- Only proceed to file generation after explicit confirmation

**10c. Generate the file:**

Compile all confirmed information into a structured `local-context.md` following the schema in `references/context-schema.md`.

Format:
```markdown
# Local Context — Grow Product Manager

> Generated: [date]. Updated: [date].
> Configurator version: [current plugin version from plugin.json]

## User Profile
- **Name:** ...
- **Role:** ...
...

## Organization: [Name]
...

### Product: [Name]
...

### Team: [Name]
...

## Custom Sections
...
```

**10d. Save to user's workspace:**

Save `local-context.md` to the user's outputs/workspace folder. Confirm the path to the user.

**10e. Automatic validation:**

After saving, automatically run a quick validation (see Validate Mode) to confirm everything works. Present the readiness report.

---

## Workflow — Update Mode

### U-1. Read existing context

Read the current `local-context.md`. Parse all sections.

### U-2. Ask what to update

> "What would you like to update in the plugin configuration?"

Present current sections as options via AskUserQuestion:
- User Profile
- Organization: [Name] (for each org)
- Product: [Name] (for each product)
- Add new product
- Add new organization
- Teams
- Analytics & Data Sources
- Key Metrics & OKRs
- Repositories
- Custom Sections
- Add new custom section

### U-3. Update the selected section

Follow the same collection flow as Onboarding for the selected section. Pre-fill all fields with current values so the user only needs to change what's different.

### U-4. Save updated file and show changelog

- Update the `Updated:` timestamp
- Preserve all sections that were not modified
- Preserve all custom sections
- Save to the same location

**Mandatory changelog — always present after ANY update:**

> "Changes saved. Here is the changelog:"

```
## Changelog — [date]

| Section | Was | Became |
|---------|-----|--------|
| Product: App → Platforms | Android, iOS, Web | Android, iOS, Web, **Admin Panel** |
| Organization → Tableau Base URL | https://old-url.com | https://new-url.com |
| Team: Product Team → Members | 5 members | 6 members (+Person Name, QA) |
| Product: App → OKRs | (not set) | **Added: 2 objectives, 4 key results** |
```

The changelog must include:
- **Section path** — which section was changed (hierarchical: Organization → Product → Field)
- **Was** — previous value (or "not set" if new)
- **Became** — new value (highlight additions in bold, mark deletions)
- For added items — show "+ [item]"
- For removed items — show "- [item]"
- For complex sections (lists, tables) — show count change and specific additions/removals

---

## Workflow — Validate Mode

### V-1. Read context and scan

Read `local-context.md` and scan all MCP connectors (same as Onboarding Step 1b).

### V-2. Test MCP connections

For each integration referenced in the context:

| Integration | Test | Expected result |
|-------------|------|-----------------|
| **Jira** | `getJiraIssue` with a known project key | Project accessible |
| **Confluence** | `getConfluenceSpaces` + check configured space exists | Space accessible |
| **Figma** | `whoami` | Account verified |
| **Notion** | `notion-get-teams` | Workspace accessible |
| **Tableau** | Navigate to dashboard URL via browser | Page loads |
| **Google Sheets** | Navigate to sheet URL via browser | Sheet loads |

### V-3. Test data access

For each product in the context:
- Try to search Jira issues in the configured project: `searchJiraIssuesUsingJql` with `project = PROJECT_KEY ORDER BY created DESC` (limit 1)
- Try to access the configured Confluence space: `getConfluenceSpaces` and verify the space key exists
- If dashboard URLs are configured — try to navigate and take a screenshot to verify access

### V-4. Check context completeness

Score each product's context completeness:

| Category | Fields | Weight |
|----------|--------|--------|
| **Core** (required) | product name, description, platforms, jira_project_key | 40% |
| **Publishing** | confluence_space, confluence_template | 15% |
| **Analytics** | key_metrics, dashboards, ab_test_dashboards | 20% |
| **Team** | team name, members, jira_team_id | 15% |
| **Strategy** | OKRs, competitors, metric_targets | 10% |

Calculate a completeness percentage per product and overall.

### V-5. Produce readiness report

Present a comprehensive report:

```
## Plugin Readiness Report

### MCP Connections
| Integration | Status | Test |
|-------------|--------|------|
| Jira        | ✅ OK  | Project PROJ accessible |
| Confluence  | ✅ OK  | Space SPACE accessible |
| Figma       | ⚠️ Not connected | Recommended to connect |
| Tableau     | ✅ OK  | Dashboard accessible |

### Products
| Product | Completeness | Details |
|---------|-------------|---------|
| Product 1 | 85% | Missing: OKRs, competitors |
| Product 2 | 60% | Missing: dashboards, team, OKRs |

### Recommendations
1. Connect Figma MCP for working with designs
2. Add OKRs for Product 1 (improves analysis and concept quality)
3. Add competitors for Product 2 (required for research)

### Overall readiness: 75%
```

If issues found — offer to run Update mode to fix them.

---

## Workflow — View Mode

View mode allows the user to see the current configuration and make inline changes through dialogue.

### VW-1. Read and display current context

Read `local-context.md` and present its contents in a clean, readable format — section by section:

> "Here is the current plugin configuration:"

Display each section with clear headings. For long sections (teams, metrics) — use tables. Show completeness indicators where fields are empty or missing.

### VW-2. Ask if changes are needed

> "Would you like to change anything? Just tell me what — for example: 'change email', 'add competitor X', 'remove product Y'."

### VW-3. Apply inline changes

If the user requests changes via dialogue:
1. Parse the user's request — identify which section and field to change
2. Apply the change
3. Show the changelog (same format as Update Mode U-4)
4. Ask if there are more changes needed
5. Repeat until the user says they're done

### VW-4. Save if changes were made

If any changes were applied:
- Save the updated `local-context.md`
- Show the complete changelog of all changes made during this View session
- Update the `Updated:` timestamp

If no changes were made — simply end the mode.

---

## Changelog Protocol (applies to ALL modes that modify local-context.md)

Every time `local-context.md` is modified — whether by Onboarding (Step 10), Update, View, or Enrichment from other skills — the user MUST receive a changelog report showing:

1. **What was added** (new fields, new sections, new items in lists)
2. **What was changed** (previous value → new value)
3. **What was removed** (if applicable)

Format: table with columns "Section | Was | Became"

This applies equally to:
- Plugin Configurator modes (Onboarding, Update, View)
- Context Enrichment by other skills (Product Research adding competitors, etc.)

---

## Context-aware product selection

When `local-context.md` contains **multiple products**, skills need to know which product the user is working with. The Configurator establishes the following protocol for all skills:

**At the start of any skill execution (after reading local-context.md):**

1. If the user explicitly mentioned a product name → use it
2. If only one product exists in context → use it automatically
3. If multiple products exist and none was mentioned → ask via AskUserQuestion:
   > "There are multiple products in the context: [list]. Which product are we working with now?"

This question is asked once per skill session. The selected product becomes the "active product" for the duration of the skill execution.

---

## Enrichment Protocol

Other skills can **add information** to `local-context.md` during their execution:

- **Product Research** → can add discovered competitors
- **Product Analysis** → can update current metric values
- **Feature Task Creator** → can discover and add team member Jira accountIds
- **Requirements Creator** → can discover and add Confluence template URL

When a skill discovers new context:
1. Inform the user: "I found new information that can be added to the context: [what was found]"
2. Ask: "Would you like to update local-context.md?"
3. If yes — read current file, add new data to the appropriate section, save
4. **Show changelog** (same format as Update Mode U-4): what was added, previous state → new state

---

## Versioning Protocol

This protocol applies whenever **any skill file or plugin.json is modified** — including through the Self-Improvement workflow, manual edits, or plugin structural changes.

### Skill version rules (frontmatter `version:` in SKILL.md)

| Change type | Version bump | Examples |
|-------------|-------------|---------|
| **PATCH** | x.x.X+1 | Wording fix, small content addition, formatting change, minor clarification |
| **MINOR** | x.X+1.0 | New step, new section, significant workflow addition, new condition |
| **MAJOR** | X+1.0.0 | Full workflow restructure, breaking change in logic, skill renamed |

### Plugin version rules (in `plugin.json`)

The plugin version is bumped to reflect the **highest-impact** change among all modified skills:
- Any skill PATCH → plugin PATCH
- Any skill MINOR → plugin MINOR
- Any skill MAJOR → plugin MAJOR
- New skill added → plugin MINOR

### Required steps when modifying a skill

1. **Bump skill version** — update `version:` in the modified SKILL.md frontmatter
2. **Bump plugin version** — update `"version"` in `.claude-plugin/plugin.json`
3. **Add CHANGELOG.md entry** — create a new entry at the top of `CHANGELOG.md`:

```
## [X.Y.Z] — YYYY-MM-DD

### What changed
- [brief description of what was changed and why]

### Skills changed
| Skill | From | To | Change type |
|-------|------|----|-------------|
| skill-name | old-version | new-version | patch/minor/major — what was changed |
```

4. **Re-package the plugin** — rebuild the `.plugin` archive with the new version
5. **Confirm to the user** — show the new plugin version and the skills that were bumped

### This skill's versioning

This skill (`plugin-configurator`) must bump its own version when its SKILL.md is modified, following the same rules above.

---

## Quality Standards

- Never overwrite user-provided data without confirmation
- Always show what was discovered vs. what the user needs to provide manually
- Pre-fill fields from auto-discovery, but always confirm with the user
- Preserve custom sections during updates
- Use Ukrainian or English based on user's language preference (ask in Step 2 if Onboarding, read from context if Update/Validate)

## Additional Resources

- **`references/context-schema.md`** — complete schema definition with field descriptions, required/optional status, and which skills use each field
- **`references/integration-strategy.md`** — MCP → Registry → Browser fallback chain (shared across all skills)
- **`references/self-improvement.md`** — self-improvement protocol
