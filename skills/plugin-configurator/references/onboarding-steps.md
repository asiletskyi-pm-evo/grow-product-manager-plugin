# Onboarding Mode — full step-by-step workflow (Steps 1–17 + Planning/Focus setup)

> Part of `plugin-configurator`. Loaded on demand when Onboarding mode starts. The mode map and entry conditions live in SKILL.md.

### Step 1 — Welcome and onboarding map

**1a. Greeting:**

> "Welcome! This configurator gets the plugin ready to work for your organization, products, and tools. Here's what we'll go through:"

**1b. Print the full onboarding map:**

| # | Step | Type | Basic | Extended | Approx. time |
|---|------|------|-------|----------|--------------|
| 1 | Welcome + map | info | — | — | 30 sec |
| 2 | Basic vs Extended | choice | ✅ | ✅ | 30 sec |
| 3 | Connector pre-check | auto | ✅ | ✅ | 30 sec |
| 4 | User Profile | required | ✅ | ✅ | 1 min |
| 5 | Organization | required | ✅ | ✅ | 1 min |
| 6 | Product (core fields) | required | ✅ | ✅ | 1-2 min |
| 6+ | Product (extended fields) | optional | — | ✅ | +2-3 min |
| 7 | Analytics & Data Sources | hybrid | base URL | full | 1-3 min |
| 8 | Key Metrics & OKRs | optional | — | ✅ | 1-2 min |
| 9 | Teams | optional | ⏭️ later | ✅ | 1-3 min |
| 10 | Repositories | optional | ⏭️ later | ✅ | 1 min |
| 11 | CJM | optional | ⏭️ later | ✅ | 3-5 min |
| 12 | Knowledge Library | optional | ⏭️ later | ✅ | 1-2 min |
| 13 | Templates | optional | ⏭️ later (built-in only) | ✅ | 1-2 min |
| 14 | Obsidian Vault | optional | ⏭️ later | ✅ | 3-5 min |
| 15 | Custom Sections | optional | ⏭️ skip | ✅ | free-form |
| 16 | Review + Save | required | ✅ | ✅ | 30 sec |
| 17 | Quick Wins | info | ✅ | ✅ | 30 sec |

**Legend:**
- ✅ — will be asked
- ⏭️ later — skipped in Basic, can be added later via `configure plugin → add [section]`
- ⏭️ skip — not asked at all in Basic
- — — no user input

> "Basic mode takes ~3-5 minutes; the plugin is immediately usable for `write-concept`, `requirements-creator`, `brainstorm-features`, and `product-research`.
> Extended mode takes ~15-25 minutes and configures every feature including CJM, Vault, and full Tableau analytics."

**1c. Tip:**

> "I'd recommend starting with Basic. Any deferred step can be added later by saying `configure plugin → upgrade to Extended`, or by adding a single section like `add CJM` or `connect Obsidian`."

### Step 2 — Choose mode

Ask via AskUserQuestion:

- **Basic (Recommended)** — required steps only. Everything else is deferred and can be added later.
- **Extended** — full setup of every feature.
- **Test mode (sandbox)** — walk through onboarding without touching real data. All writes are redirected to `~/.grow-pm-sandbox/`. See "Workflow — Test Mode" below.
- **Quit and read docs** — show README and exit.

**Save the choice in session memory** as `selected_mode`. Each subsequent step reads this and decides whether to execute or defer.

If `selected_mode == test` — switch all storage paths from `~/.grow-pm/` to `~/.grow-pm-sandbox/` for the rest of this session. Real data is never touched. See the Test Mode workflow for details.

### Step 3 — Connector pre-check

**3a. Scan available MCP connectors** in the session.

For each known connector, attempt a lightweight ping:

| Connector | Ping call | What it confirms |
|-----------|-----------|------------------|
| Jira | `getVisibleJiraProjects` | Auth + access |
| Confluence | `getConfluenceSpaces` | Auth + access |
| Figma | `whoami` | Auth |
| Notion | `notion-get-teams` | Auth + workspace access |
| Tableau | `search-content` (no terms, limit 1) | Auth + server reachable |
| Fireflies | `fireflies_get_user` | Auth |
| Google Calendar | `list_calendars` | Auth |
| Gmail | `list_labels` | Auth |
| Google Drive | `list_recent_files` | Auth |
| Slack | (any read tool) | Auth |

**3b. Score connectors against required-for-mode:**

Build the readiness table:

| Connector | Status | Required for Basic | Required for Extended | Used by skills |
|-----------|--------|--------------------|-----------------------|----------------|
| Jira | ✅/❌ | ⭐ Strongly recommended | ✅ Mandatory | `task-creator`, `requirements-creator` |
| Confluence | ✅/❌ | ⭐ Strongly recommended | ✅ Mandatory | publishing skills |
| Tableau | ✅/❌ | — | ⭐ Strongly recommended for CJM/AB | `product-analysis`, `cjm-research` |
| Figma | ✅/❌ | — | optional | `product-research`, `design-bridge` |
| Notion | ✅/❌ | optional | optional | publishing alternative |
| Fireflies | ✅/❌ | — | optional | `meeting-processor` |
| Google Drive | ✅/❌ | optional | optional | `product-research` |
| Slack | ✅/❌ | — | optional | notifications |

**3c. Action proposals:**

If a `Mandatory` connector is missing for the chosen mode → propose `search_mcp_registry` + `suggest_connectors` BEFORE proceeding. Offer:
- **Connect now** — Configurator pauses, the user makes the connection, then says "continue" → Configurator re-runs the ping for that connector and continues.
- **Continue without** — Configurator records `deferred_connectors: [...]` in session memory; surface the gap in Step 17 Quick Wins.
- **Quit and finish later** — exit; next launch enters Reinstall mode and re-asks.

If only `Strongly recommended` connectors are missing → mention them as warnings, do not block.

**3d. Persist findings:**

Save in session memory: `connector_inventory: { connected: [...], missing: [...], blocking: [...] }`. Used by Step 7 (Analytics) and Step 17 (Quick Wins).

### Step 4 — User Profile

Ask via AskUserQuestion:

- **Name** — user's display name (pre-fill from session context if available)
- **Role** — role in the organization (Product Manager, Senior PM, Head of Product, etc.)
- **Email** — for Jira account lookup
- **Preferred language** — uk (Ukrainian) or en (English) for skill output

**Auto-discover Jira account:**
If Jira MCP is available, use `lookupJiraAccountId` with the provided email to find and store the user's Jira accountId.

### Step 5 — Organizations

**5a. Multi-org support — ask via AskUserQuestion:**

> "How many organizations/companies do you work with? The plugin supports working with multiple simultaneously."

- Single organization (most common) → proceed with one
- Multiple organizations → collect info for each, repeating Steps 3-5

**5b. For each organization, collect:**

| Field | How to collect | Auto-discovery |
|-------|---------------|----------------|
| Organization name | AskUserQuestion | — |
| Domain | AskUserQuestion | — |
| Jira instance URL | Auto from MCP, confirm with user | ✅ Extract from Jira MCP base URL |
| Confluence instance URL | Auto from MCP, confirm with user | ✅ Extract from Confluence MCP base URL |

### Step 6 — Products (per organization)

> **Mode gate:** **Basic** mode collects only core product fields (name, description, platforms, Jira project key, Confluence space). Extended fields (locales, OKRs, metric_targets, competitors, custom dashboards, A/B test dashboards) are deferred. **Extended** mode collects every field.


**6a. Product discovery — combine auto + manual:**

If Jira projects were discovered in Step 3:
> "I found these projects in Jira: [list]. Which of them are your products? Some projects may belong to the same product."

Help the user map Jira projects → Products (may be 1:1 or many:1).

**6b. For each product, collect via AskUserQuestion (section by section):**

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

### Step 7 — Analytics & Data Sources (per organization)

> **Mode gate:** **Basic** mode collects only the Tableau base URL (and analytics tool names if mentioned by the user). All extended fields — datasource URLs, Pulse metric IDs, A/B test dashboards per platform, Google Sheets, Amplitude/Mixpanel/Custom BI — are deferred (`onboarding.deferred_steps += ['tableau-full', 'analytics-extended']`). **Extended** mode collects every field below.


**7a. Analytics tools:**

> "Which analytics tools does your organization use?"

For each tool mentioned, collect the base URL and any product-specific dashboard URLs:

| Tool | What to collect |
|------|----------------|
| **Tableau** | Base URL, Site Name (if non-default), A/B test dashboard URLs (per platform), main product dashboards, Datasource URLs (for `query-datasource`), Pulse metric IDs (for `list-pulse-metrics-*`) |
| **Google Analytics** | Property IDs or dashboard URLs |
| **Amplitude** | Workspace URL |
| **Mixpanel** | Project URL |
| **Custom BI** | Dashboard URLs |
| **Google Sheets** | Key shared spreadsheets with metrics |

**7a-Tableau. Tableau full setup (Extended mode only):**

If the user added Tableau in Step 7a, collect the additional fields below. **Skip in Basic mode** — they go to `onboarding.deferred_steps` as `tableau-full`.

If Tableau MCP is available:
1. Try `search-content` with no terms (limit 1) — verify the connector responds.
2. Confirm the resolved Server URL and Site Name with the user (auto-fill `tableau_base_url`, `tableau_site_name`).

For all users (regardless of MCP availability):

| Field | What to ask | local-context.md key |
|-------|-------------|----------------------|
| Site Name (optional) | "Is your Tableau site the default site, or do you use a named site?" | `organization.tableau_site_name` |
| Datasource URLs (optional) | "Do you have key published datasources with product metrics? Paste the URL for 1-3 of them with a friendly name." | `organization.tableau_datasource_urls` (map: name → URL) |
| Pulse Metric IDs (optional) | "If your Tableau Pulse is enabled — would you like to wire 2-3 key metrics for fast health checks? I can list available metrics and you pick." | `organization.tableau_pulse_metric_ids` (map: name → metric ID) |

For Pulse Metric IDs — if Tableau MCP is available and the admin has enabled Pulse, call `list-all-pulse-metric-definitions` and present the user with a multi-select to pick the most relevant metrics; save selected definition IDs.

If Tableau MCP is NOT available — skip Datasource URLs and Pulse Metric IDs (they require MCP to be useful) and note this in `onboarding.deferred_steps` as `tableau-mcp-required`.

**7b. A/B test dashboards (critical for Product Analysis):**

If Tableau or another A/B testing tool is used:
> "Are there separate dashboards for A/B test analysis? If yes, please provide the URL for each platform."

Collect per platform (e.g., Dashboard 1 for Web, Dashboard 2 for Mobile).

**7c. Other data sources:**

- Google Drive folders with research/strategy docs
- Figma workspace/team URL
- Notion workspace (if used alongside Confluence)

### Step 8 — Key Metrics & OKRs (per product)

> **Mode gate:** This step runs in **Extended** mode only. In **Basic** mode, skip this step and append `key-metrics` to `onboarding.deferred_steps`. Step 17 (Quick Wins) will surface a nudge to add it later.


> "What are the key metrics you track for this product?"

**8a. Key metrics:**
Collect a list of primary metrics with brief descriptions:
- Metric name (e.g., "Conversion Rate", "DAU", "Revenue per User")
- What it measures
- Current approximate value (if known)

**8b. Current OKRs (optional):**
> "Are there current OKRs (quarterly objectives) for this product?"

If yes — collect objectives and key results. These help skills align hypotheses and analysis with strategic goals.

**8c. Metric targets (optional):**
> "Are there target values for the key metrics?"

Collect target values for metrics that have them (e.g., "Conversion Rate → +2% this quarter").

### Step 9 — Teams (per organization)

> **Mode gate:** This step runs in **Extended** mode only. In **Basic** mode, skip this step and append `teams` to `onboarding.deferred_steps`. Step 17 (Quick Wins) will surface a nudge to add it later.


> "Would you like to configure team information? This will help when creating tasks in Jira."

If yes:

**9a. For each team, collect:**
- Team name
- Jira team ID (auto-discover from existing tasks if possible)
- Members: name, role (FE, BE, Android, iOS, Design, Analytics, QA, PM), Jira accountId (auto-discover via `lookupJiraAccountId`)

**9b. Auto-discovery from Jira:**
If Jira MCP is available and a product's Jira project is known:
- Search for recent tasks to discover team field values
- Extract common assignees and their roles
- Present to user for confirmation

### Step 10 — Repositories & CI/CD (per product, optional)

> **Mode gate:** This step runs in **Extended** mode only. In **Basic** mode, skip this step and append `repos` to `onboarding.deferred_steps`. Step 17 (Quick Wins) will surface a nudge to add it later.


> "Would you like to add repository and CI/CD information? (for future skills)"

If yes:
- Repository URLs (GitHub/GitLab)
- CI/CD pipeline URLs
- Environment URLs (staging, production)

### Step 11 — CJM Configuration (per product, optional)

> **Mode gate:** This step runs in **Extended** mode only. In **Basic** mode, skip this step and append `cjm` to `onboarding.deferred_steps`. Step 17 (Quick Wins) will surface a nudge to add it later.


> "Do you use Customer Journey Map (CJM) analysis in your product work? This enables funnel analysis, anomaly detection, and improvement hypothesis generation."

If no → skip to Step 12.

If yes:

**11a. Select funnel template:**

> "Which funnel template fits your product? Available templates:"
>
> - **E-commerce** — Start/Listing → Product Page → Cart/Checkout → Payment/Post-Purchase
> - **SaaS** — Awareness → Signup/Trial → Activation → Engagement → Conversion → Retention
> - **Marketplace** — Search/Browse → Listing Page → Contact/Booking → Transaction → Review
> - **Custom** — define your own stages

See `references/funnel-templates.md` for full template definitions.

**Communicate the selection:**
> "Using the **[template name]** template with stages: [list]. You can change this at any time."

**11b. If Custom template selected:**
1. Ask: "How many stages does your funnel have?"
2. For each stage: collect name, key metrics (at least 1)
3. Confirm the complete funnel

**11c. Map dashboards to stages:**

For each funnel stage:
> "Which dashboard shows data for **[Stage name]**?"

Collect dashboard URLs (Tableau, GA, or other). If the user already provided dashboard URLs in Step 7 — suggest mapping those first.

**11d. Set baseline conversions:**

> "Do you know the current conversion rates for each stage? (used as baseline for anomaly detection)"

- If yes → collect per-stage conversion rates
- If no → "We can read baselines from dashboards during the first CJM analysis."

**11e. Configure anomaly thresholds:**

> "Anomaly detection thresholds (you can use defaults or customize):"

| Level | Default | Your value |
|-------|---------|-----------|
| Warning | 10% deviation | [ask] |
| Critical | 25% deviation | [ask] |

**11f. Default analysis settings:**

| Setting | Default | Ask user |
|---------|---------|---------|
| Comparison baseline | Previous period | Previous period / Previous year / Target / Custom |
| Default platforms | All configured | All / Specific |
| Default search modes | Library + Internet | User selects from available modes |

### Step 12 — Knowledge Library Setup (optional)

> **Mode gate:** This step runs in **Extended** mode only. In **Basic** mode, skip this step and append `knowledge-library` to `onboarding.deferred_steps`. Step 17 (Quick Wins) will surface a nudge to add it later.


> "Would you like to set up a Knowledge Library? It stores curated sources (articles, benchmarks, UX best practices) that enrich CJM analysis and research."

If no → skip to Step 14.

If yes → delegate to `knowledge-library` skill onboarding workflow (KL-1 through KL-6). The Knowledge Library skill handles:
1. Directory structure initialization
2. Source import (if user provides URLs or files)
3. Baymard Premium configuration
4. Default search modes
5. Confluence and Google Drive search validation

After Knowledge Library setup completes, continue with Step 13.

### Step 13 — Template Library Setup (optional)

> **Mode gate:** This step runs in **Extended** mode only. In **Basic** mode, skip this step and append `templates` to `onboarding.deferred_steps`. Step 17 (Quick Wins) will surface a nudge to add it later.


> Requires: `references/template-protocol.md` (full resolution protocol) and `skills/template-library/SKILL.md` (CRUD actions)

The Template Library stores reusable templates for artifacts the plugin generates (concepts, requirements, research, CJM, epics, tasks, presentations). Templates can be **built-in** (ship with the plugin, read-only), **user-global** (apply to all products), or **product-specific** (scoped to one product).

**O-T.1. Introduce and ask:**

> "Would you like to configure the Template Library now? It stores reusable templates for concepts, requirements, research, CJM reports, epics, tasks, and presentations. You can always set it up later."

Present options via `AskUserQuestion`:
- **Use built-in templates only** (recommended default) — built-in templates ship with the plugin; nothing else to set up now.
- **Import templates from a folder** — I'll scan a folder of Markdown templates and register them.
- **Import from Confluence** — I'll pull your existing requirement/concept templates from Confluence (delegates to `template-library` import mode with Confluence scan).
- **Create one template now** — wizard: pick artifact type, base, languages, fields.
- **Skip for now** — built-in templates remain available; you can configure any time via "manage templates".

**O-T.2. Collect template preferences (always asked, even when using built-in only):**

Via `AskUserQuestion`, collect:

| Setting | Options | Default |
|---------|---------|---------|
| `templates.preference` | `auto`, `always_ask`, `smart` | `smart` |
| `templates.default_language` | from `local-context.locales` | first locale |
| `templates.auto_save_to_vault` | `true`, `false` | `true` if Vault configured |

Explain `preference` briefly:
- **auto** — always use the top-ranked template silently
- **always_ask** — always ask which template to use, even if only one matches
- **smart** (default) — ask only when multiple strong candidates exist (gap < 3 points)

**O-T.3. Storage initialization:**

Follow `references/persistent-storage.md` → "`storage_root` resolution" (the single definition — do not restate the rule here):
- Vault configured → `{vault}/{plugin_folder}/Templates/`
- Otherwise → `~/.grow-pm/Templates/`

Create (if missing):

```
{storage_root}/Templates/
├── _registry.json              # empty registry, schema_version: 1.0.0
├── _partials/                  # reusable body fragments
├── _System/
│   └── usage.log               # rendering usage log
├── _archive/                   # automatic archive of edits/deletes
├── user-global/
│   ├── concept/
│   ├── requirements/
│   ├── research/
│   ├── cjm/
│   ├── epic/
│   ├── task/
│   └── presentation/
└── products/
    └── <product_id>/           # one subfolder per configured product
        └── ...
```

**O-T.4. Run rebuild-registry:**

Invoke `template-library: rebuild-registry` to walk `Templates/` (including the plugin's `templates/built-in/`) and generate `_registry.json`. This registers the 9 built-in templates that ship with the plugin v1.9.0.

**O-T.5. Execute chosen action:**

- **Use built-in only** → no further action; registry already populated.
- **Import from folder** → delegate to `template-library` Import wizard.
- **Import from Confluence** → delegate to `template-library` Import wizard with `source=Confluence` pre-selected.
- **Create one template** → delegate to `template-library` Add wizard.

**O-T.6. Mark onboarding flag:**

In `local-context.md`, set `onboarding.templates_setup_completed: true`. If the user picked "Skip for now", set `onboarding.templates_setup_completed: false` so a later run of Plugin Configurator can re-offer this step.

**O-T.7. Write Templates section to local-context.md:**

```markdown
## Templates

templates:
  preference: smart            # auto | always_ask | smart
  default_language: uk
  favorite_templates: []       # template_id values that rise to the top
  auto_save_to_vault: true
```

**O-T.8. Confirm and continue:**

> "Template Library initialized at {storage_root}/Templates/. Registry: {N} built-in + {K} user templates. Preference: {smart|auto|always_ask}."

Then proceed to Step 14.

### Step 14 — Obsidian Vault (Optional)

> **Mode gate:** This step runs in **Extended** mode only. In **Basic** mode, skip this step and append `obsidian-vault` to `onboarding.deferred_steps`. Step 17 (Quick Wins) will surface a nudge to add it later.


> Requires: `references/obsidian-setup-guide.md`, `references/vault-protocol.md`, `references/vault-schema.md`

This step is fully delegated to the **Obsidian Setup Guide** (`references/obsidian-setup-guide.md`), which provides step-by-step instructions with explicit ✅/⚠️/❌ validation at every substep:

1. **P-1**: Pre-flight — does the user have Obsidian installed?
2. **P-2**: Create vault (if needed)
3. **P-3**: Pre-flight summary
4. **S-1**: Vault path with validation (directory exists, `.obsidian/` exists)
5. **S-2**: Plugin folder name (regex validation)
6. **S-3**: Write/read permission test (creates `.write-test`, reads back, deletes)
7. **S-4**: Products binding (single product auto-binds; multi-product asks)
8. **S-5**: Sync mode (auto / manual / read-only)
9. **S-6**: Optional Obsidian MCP detection (L1 vs L2)
10. **S-7**: Folder initialization (per `vault-protocol.md`)
11. **S-8**: Smoke test (read-back validation)
12. **S-9**: Save `## Obsidian Vaults` section to `local-context.md` and run Vault Mirror Protocol

The guide also includes a Common errors and recovery table for each likely failure mode (path missing, no `.obsidian/`, permission denied, MCP ping failed, partial init, smoke test fails).

**Multi-vault support**: after S-9 completes, ask via `AskUserQuestion`: "Add another vault?" — if yes, repeat the full P-1..S-9 cycle for the next vault.

**On completion**, show the user a single summary card listing all configured vaults, paths, sync modes, and vault levels. Then proceed to Step 15.

### Step 15 — Custom Sections

> **Mode gate:** This step runs in **Extended** mode only. In **Basic** mode, skip this step and append `custom-sections` to `onboarding.deferred_steps`. Step 17 (Quick Wins) will surface a nudge to add it later.


> "Is there any additional information you'd like to save in the plugin context? For example: strategy documents, internal guidelines, specific processes."

Allow free-form markdown sections with custom titles.

### Step 16 — Review, confirm, and save local-context.md

**16a. Compile summary for review:**

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
- CJM: [template name, stages count, thresholds or "not configured"]

### Team: [name]
- Members: [list with roles]

### Knowledge Library
- Status: [initialized / not configured]
- Sources: [count or "empty"]
- Search modes: [list or "N/A"]
- Baymard: [yes/no]

### Template Library
- Status: [initialized / using built-in only / skipped]
- Preference: [smart / auto / always_ask]
- Default language: [locale]
- User templates: [count or "none"]
- Auto-save to vault: [yes/no]

### Obsidian Vaults
- Status: [configured / not connected]
- Vaults: [list with paths or "none"]
- Products bound: [all / specific list or "N/A"]
- Sync mode: [auto / manual / read-only or "N/A"]

### Custom sections
- [if any]
```

**16b. Collect corrections:**

> "Is everything correct? If anything needs to be fixed — tell me what, and I'll make the changes."

- If the user requests corrections — apply them immediately and show the updated section
- Iterate until the user confirms: "OK" / "Confirmed"
- Only proceed to file generation after explicit confirmation

**16c. Generate the file:**

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

## Onboarding Status

<!-- This section is auto-managed by Plugin Configurator. Do not edit manually. -->

- **Mode:** [basic | extended]
- **Basic completed at:** [timestamp]
- **Extended completed at:** [timestamp or "not yet"]
- **Last test run at:** [timestamp or "never"]
- **Deferred steps:** [list of step keys deferred — e.g., obsidian-vault, cjm, templates]
- **Skip nudges:** [true | false]

## Organization: [Name]
...

### Product: [Name]
...

### CJM Configuration
...

### Team: [Name]
...

### Knowledge Library
...

### Obsidian Vaults (Optional)
...

## Custom Sections
...
```

**CJM Configuration section format in local-context.md:** See `references/context-schema.md` → CJM Configuration section format.

**Knowledge Library Configuration section format:** See `references/context-schema.md` → Knowledge Library Configuration section format.

**Obsidian Vaults Configuration section format:** See `references/context-schema.md` → Obsidian Vaults Configuration section format.

**16d. Save to persistent storage:**

1. Determine storage root:
   - **Test mode** (`selected_mode == test`) → `~/.grow-pm-sandbox/` (real `~/.grow-pm/` is NEVER touched)
   - **All other modes** → `~/.grow-pm/`
2. Create the storage root directory if it doesn't exist (with permissions 700 on Unix)
3. Save `local-context.md` to `{storage_root}/local-context.md`
4. Create `{storage_root}/.schema-version` with the current plugin version
5. **Stamp the Onboarding Status section** in `local-context.md`:
   - `mode: basic` or `mode: extended` (from `selected_mode`)
   - `basic_completed_at: {now}` if mode is basic
   - `extended_completed_at: {now}` if mode is extended (and `basic_completed_at` if not already set)
   - `last_test_run_at: {now}` if mode is test
   - `deferred_steps: [...]` from session memory
   - `skip_nudges: false` (default)
6. Confirm to the user:
   - Production: "Configuration saved to `~/.grow-pm/`. This data will persist across plugin reinstalls and updates."
   - Test mode: "TEST RUN — configuration saved to `~/.grow-pm-sandbox/`. Your real configuration was not touched. Continue to Test Mode finale for diff and Discard / Promote / Keep options."

**16e. Vault Mirror Sync:**

After saving to `~/.grow-pm/`, if Obsidian Vault is configured (Step 14 was completed):
1. Execute Vault Mirror Protocol (VM-1 through VM-3 from `references/persistent-storage.md`)
2. Copy `local-context.md` → `{vault}/{plugin_folder}/_System/local-context.md`
3. Copy `.schema-version` → `{vault}/{plugin_folder}/_System/.schema-version`
4. If Knowledge Library was initialized → copy library files to `{vault}/{plugin_folder}/Knowledge/`
5. Log: "Configuration mirrored to Obsidian Vault at [path]"

This ensures the vault always has an up-to-date copy of all user context, serving as a secondary backup.

**16f. Automatic validation:**

After saving, automatically run a quick validation (see Validate Mode) to confirm everything works. Present the readiness report.

**16g. Template Library final invitation (only if user skipped Step 13 earlier):**

If `onboarding.templates_setup_completed` is `false` (user chose "Skip for now" during Step 13), offer one more nudge after validation:

> "Plugin configured and ready! The built-in templates are available out of the box. If you want to set up custom templates now, you can: import from a folder, import from Confluence, or create a new one. Otherwise just say 'manage templates' any time later."

If the user confirms → delegate to `template-library` with the chosen action.

If Step 13 was already completed (user set up Template Library in Step 13), skip this step and go directly to the final summary.

**After template setup completes**, return confirmation:
> "Setup complete. Here's a summary of what's configured:"
> - Plugin context: ✅ local-context.md saved
> - Integrations: [validation results summary]
> - CJM: [configured / not configured]
> - Knowledge Library: [initialized with N sources / not configured]
> - Obsidian Vaults: [N vaults connected / not configured]
> - Templates: [number] templates saved / library initialized / skipped
> "You're ready to start! Try: 'brainstorm features for [product]' or 'write requirements for [feature name]'"

---

### Step 17 — Quick Wins

After successful save and validation, present 2-3 concrete next-step recommendations the user can act on immediately.

**Generate from session context:**

- If `connector_inventory.missing` includes `Tableau` → "Connect the Tableau MCP connector — it unlocks `product-analysis` and `cjm-research` with native data access."
- If at least one product has a Jira project key → "Try: `create requirements for [feature]` — I'll generate a Confluence-ready spec."
- If `onboarding.mode == basic` → "When you want full setup later, say: `configure plugin → upgrade to Extended`. Or add one section: `add CJM`, `connect Obsidian`, `set up templates`."
- If `onboarding.mode == basic` and `cjm` is in `deferred_steps` → "Want to run CJM analysis without setting it up first? Just say `analyze CJM funnel for [product]` — I'll ask for the basics and offer to save them as your CJM config at the end."
- If `vault_level == L0` (Obsidian Vault not configured) → "When you have 5 minutes, connect an Obsidian Vault — your concepts, requirements, research, and CJM reports will mirror into your knowledge base automatically."
- If `connector_inventory.missing` includes `Confluence` → "Connect Confluence MCP — it unlocks publishing of requirements and concepts."

Present each recommendation as an option in `AskUserQuestion` so the user can immediately invoke the suggested action without typing the command.

**End of Onboarding workflow.**

---

## Step — Planning setup (Extended)

Configures the planning suite (`quarterly-planning`, `project-planning`, `sprint-planning`, `roadmap-architect`). Writes the `planning` section into local-context (schema — `local-context.example.md` → Planning). Mode-gate: Extended; in Basic — add the key to `onboarding.deferred_steps`.

Collected via `AskUserQuestion`/dialog:

1. **Team and capacity** — composition by platforms/roles; **who counts** toward the ceiling (TL as a dev or not); baseline SP/sprint (default 10); tech-debt reserve (default 15%); load target (default 85%). Match members against Jira profiles.
2. **Sprints** — cadence (default 2 weeks), anchor (name+date of the nearest one, e.g. `Sprint 42 = 2026-01-05`), Jira board id.
3. **Goal map** — epic → Goal (PROJ-XX), since Atlas Goals are not queryable via MCP.
4. **Gate thresholds** — warning/critical (default 85/100%); t-shirt→SP rubric.
5. **Development Flow (survey about the development flow)** — if the section does not yet exist:
   - typical work-type sequence (default `Requirements → Design → {BE, Analytics} → Client → QA → Release`; can be reordered/added/removed);
   - what runs in parallel;
   - prerequisite dependencies (DAG edges) + platform nuances;
   - readiness threshold (from which status a prerequisite is considered passed; default on review/in test/done);
   - team logic specifics/exceptions (free input).

Offer to save everything into local-context (`planning` section). All planning skills read this; `update config` updates it.

Existence check: if `planning.development_flow` already exists → do not re-ask, only offer review/update.

## Step — Focus setup (Extended)

Configures `focus-advisor`. Writes the `Focus` section into local-context (format — `references/context-schema.md` → Focus Configuration; semantics — `references/focus-signals.md` §8). Mode-gate: Extended; in Basic — add the key to `onboarding.deferred_steps`. Requires the Planning section (sprint anchor/cadence) — if missing, run Planning setup first.

Collected via `AskUserQuestion`/dialog:

1. **Sources** — which collectors are on (mail / calendar / Jira; release flags off by default); mail window (default 7 days) and no-reply thresholds (default 24h VIP / 48h others).
2. **VIP senders** — prefill from existing stakeholders/team in local-context; if none — ask for names+emails. Explain: VIP raises mail-signal ranking, it does not filter others out.
3. **PM goals** — prefill from local-context (OKRs, mission commitments); if none — ask for 1–3 goals with wording the PM uses. These act as permanent scoring weights (`focus-scoring.md`). Also capture **Goals source** — the URL of the pinned product goals/missions document (used by strategy collectors).
4. **Cadence overrides** — show the default ritual table (`focus-cadence.md` §2), ask what differs for this PM/team.
5. **Scheduled briefs** — offer creating headless brief tasks (via the platform's scheduled-tasks/`schedule` skill): daily `now` brief (time, working days only), weekly `tactics` brief (e.g. Monday morning), and a quarterly `strategy` memo (first week of the quarter); `healthcheck: off` by default.

Existence check: if the `Focus` section already exists → do not re-ask, only offer review/update via `update config`.

## Step — Design Toolkit setup (Extended)

Registers one or more **external design toolkits** that `design-bridge` delegates hi-fi / screen-generation work to. Writes the `design_toolkits` section into local-context (format — `references/context-schema.md` → Design Toolkits section format; semantics — root `references/design-toolkit-protocol.md`). Mode-gate: Extended; in Basic — add `design-toolkits` to `onboarding.deferred_steps`. Standalone triggers: "register design toolkit", "add design toolkit", "зареєструвати дизайн-тулкіт".

> **Universality:** never hardcode a specific toolkit into the plugin. Everything collected here goes into the user's `local-context.md` only.

Collected via `AskUserQuestion`/dialog, per toolkit:

1. **Identity** — `id` (slug) and `label`.
2. **Entry** — `type` (`skill` / `mcp_tool` / `command` / `browser`) and `ref` (the invocation reference: skill name, `mcp__…` tool, shell command, or URL).
3. **Capabilities** — pick from the core enum (`hi-fi-prototype`, `screen-generation`, `ds-tokens`, `figma-write`, `code-first-research`, `design-review`); allow custom tags (opaque — won't auto-route).
4. **Input contract & returns** — confirm what the toolkit consumes (`feature_name` / `platform` / `requirements_doc` / `jira_key`) and hands back (`figma_url` / `branch` / `files`).
5. **Data locality** — `local` (co-installed skill, in-session) or `external` (third party; `data-policy.md` applies). Default `external`.
6. **Setup hint & contract version** — optional: how to (re)configure it, and the protocol semver it targets.

Pre-check the entry when cheap (skill installed? MCP tool present?) and note availability. Existence check: if a `design_toolkits` entry with the same `id` already exists → offer review/update, do not duplicate.

## Step — People setup (Extended)

Configures the **People-contour** skills (`goal-setter`, `one-on-one`, `performance-review`, `hiring-designer`, `offboarding-guide`, `delegation-coach`). Writes the `people` section into local-context (format — `references/context-schema.md` → People Configuration) and seeds the person-profile roster (`references/people-context-protocol.md`). Mode-gate: Extended; in Basic — add `people` to `onboarding.deferred_steps`. Standalone triggers: "set up People", "add team roster", "People-сетап", "налаштувати команду".

> **Data sensitivity:** person profiles are the highest-sensitivity tier (`references/data-policy.md`). They live in the vault `People/` area or `~/.grow-pm/people/` — **never** in Confluence/Jira. Collect only what the PM wants stored.

Collected via `AskUserQuestion`/dialog:

1. **Vault People area** — where profiles live: the `People/` area of a configured vault (preferred) or the `~/.grow-pm/people/` fallback if no vault. Store the resolved path.
2. **Team roster** — for each direct report: name, role, join date; optionally their current situational-leadership type (D1–D4). For each, create a minimal profile file (`People/<slug>.md`) and a roster line in `People/_roster.md`. Only `name`/`role`/`updated` are required — the rest fills in over time.
3. **Default cadences** — default 1-1 cadence (weekly / biweekly / monthly; default: monthly for newer people, quarterly for >1-year) and default goal-report cadence (weekly / monthly).
4. **Performance-review template** — register the employer's review template as a `performance-review` scope template (via `template-library: add`/`import`), or use the built-in `performance-review` structure. Store the chosen `template_id`.
5. **HR-form field map (hiring)** — the employer's vacancy-form fields and their controlled values (e.g. selects for Budget / Team / Position / Employment type / Probation length). Store under `people.hr_form` so `hiring-designer` can map the universal vacancy profile onto the employer's form field-by-field. Values are employer-specific — nothing is hardcoded in the plugin.

Existence check: if a `people` section already exists → offer review/update, do not duplicate. Never fabricate profile fields (D-type, GTD, signals) — leave unknowns empty.
