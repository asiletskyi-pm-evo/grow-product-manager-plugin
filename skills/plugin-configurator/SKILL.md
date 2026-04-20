---
name: plugin-configurator
version: 1.0.0
description: Configure the Grow Product Manager plugin for your organization, products, teams, and data sources. Use when the user asks to "configure plugin", "set up plugin", "set up context", "add a product", "update configuration", "validate setup", "show config", or when any other skill detects that local-context.md does not exist.
---

# Plugin Configurator

Configure the Grow Product Manager plugin for your organization. This skill collects all necessary context — products, teams, data sources, analytics tools, OKRs, repositories — and generates a `local-context.md` file that all other skills use as their primary context source.

Supports multiple organizations, products, and projects simultaneously.

## Five Modes

| Mode | When to use | What it does |
|------|------------|--------------|
| **Onboarding** | First launch, `local-context.md` doesn't exist anywhere | Full guided setup: user profile → organizations → products → teams → data sources → CJM → Knowledge Library → Obsidian Vault (optional) → review → validation. Saves all data to `~/.grow-pm/` |
| **Reinstall / Migration** | Plugin reinstalled, `~/.grow-pm/` contains existing data | Detect existing data, show to user, ask: use as-is / reconfigure / start fresh. Migrate schema if needed |
| **Update** | `local-context.md` exists, user wants to change something | Edit a specific section: add product, update team, change dashboard URLs, add OKRs, manage Obsidian Vaults, etc. Always shows changelog |
| **Validate** | User wants to check everything works | Test all MCP connections, verify data access, check context completeness, validate Obsidian Vault connectivity, produce readiness report |
| **View** | User asks to see current config | Display current `local-context.md` contents in a readable format, allow inline edits via dialogue |

## Persistent Storage

All user data is stored in **`~/.grow-pm/`** (user's home directory). This location is independent of the plugin installation and survives plugin uninstalls, reinstalls, and updates.

See **`references/persistent-storage.md`** for the complete protocol, directory structure, backup and migration details.

### Directory structure

```
~/.grow-pm/
├── local-context.md              # Main configuration
├── .schema-version               # Schema version marker
├── template-library/             # User's templates
├── knowledge-library/            # Curated sources
├── backups/                      # Auto-backups before migrations
└── obsidian-vaults/              # Vault configuration cache (optional)
```

## Auto-trigger Protocol

**This section is for ALL other skills in the plugin.**

At the start of execution, every skill MUST follow `references/local-context-protocol.md` — Step 0. Search for `local-context.md` in priority order:

1. **`~/.grow-pm/local-context.md`** — persistent home directory (primary)
2. Plugin root directory (relative: `../../local-context.md` from skill folder) — legacy
3. User's workspace/outputs folder — legacy
4. Session working directory — fallback

**If `local-context.md` is NOT found anywhere:**
- Stop the current skill workflow
- Inform the user: "To work effectively, the plugin needs to be configured with your organization, products, and tools context. Let's run a quick setup."
- Launch the Plugin Configurator in **Onboarding** mode
- After Onboarding completes — return to the original skill and continue its workflow with the newly created context

**If found in `~/.grow-pm/`:**
- Read it at the start of every skill execution
- Use the context throughout the skill workflow
- If missing fields for the current skill — offer Update mode or proceed without

**If found in a legacy location (2-4) but NOT in `~/.grow-pm/`:**
- This is pre-v1.4.0 data → offer migration to `~/.grow-pm/` (see Reinstall / Migration mode)
- If user agrees → migrate, then continue
- If user declines → use in-place, warn about persistence risk

## Workflow — Reinstall / Migration Mode

This mode runs automatically when the Plugin Configurator detects existing user data in `~/.grow-pm/` but is launched as if it were a fresh install (e.g., after plugin reinstall or update). It also handles legacy data migration from pre-v1.4.0 locations and **recovery from Obsidian Vault** when primary storage is lost.

### RM-0. Pre-update backup (if existing data detected)

**Before ANY other operation**, if `~/.grow-pm/` exists and contains data:
1. Execute Pre-Update Backup Protocol (PU-1 through PU-3 from `references/persistent-storage.md`)
2. This ensures a safety copy exists even if subsequent migration steps fail
3. Log: "Created safety backup at ~/.grow-pm/backups/pre-update-..."

### RM-1. Detect existing data (with Vault fallback)

Search for user data in this priority order:

```
1. Check ~/.grow-pm/ exists and contains local-context.md
   → YES: proceed to RM-2 (reinstall recovery)
   → NO: continue to step 2

2. Check Obsidian Vault mirror (Vault Recovery Protocol)
   a. Check known vault paths from:
      - Cowork session memory (auto memory)
      - Previous conversation context
      - Common locations: ~/Documents/Projects/*/GrowPM/_System/
   b. Search for _System/local-context.md in discovered vaults
   c. Search for Knowledge/library.md in discovered vaults
   → FOUND: inform user, offer restore (see VR-2 in persistent-storage.md)
     - If user accepts → restore from vault, proceed to RM-2
     - If user declines → continue to step 3
   → NOT FOUND: continue to step 3

3. Check legacy locations (plugin root, workspace, session dir)
   → Legacy data found → proceed to RM-2 (legacy migration)
   → No data anywhere → proceed to Onboarding mode
```

**IMPORTANT:** The vault fallback (step 2) is the key defense against data loss during plugin updates. If `~/.grow-pm/` was accidentally cleared but the user had Obsidian configured, data can be fully recovered.

### RM-1a. Detect existing data — ask user for vault path

If no vault is found automatically in step 2, but the session context or auto-memory suggests the user previously had a vault configured, **proactively ask:**

> "I notice you may have previously had an Obsidian Vault connected. If so, I can try to recover your plugin data from it. Do you have an Obsidian Vault with Grow PM data?"

Options:
- **Yes, here's the path** → user provides path, search for `_System/local-context.md`
- **No / Skip** → proceed to legacy locations / Onboarding

### RM-1b. Existing data found — proceed to RM-2 (reinstall recovery)

### RM-2. Inventory existing data

Scan `~/.grow-pm/` (or legacy location) and build an inventory:

| Component | Check | Details to show |
|-----------|-------|-----------------|
| `local-context.md` | Exists? Read "Updated:" timestamp | Last updated date, user name, product count |
| `.schema-version` | Exists? Read version | Version string |
| `template-library/` | Exists? Count templates in `_registry.json` | N templates in M categories |
| `knowledge-library/` | Exists? Read `library.md` header stats | N sources, avg trust score |
| `backups/` | Exists? Count backup folders | N previous backups |

### RM-3. Present findings and ask user

Show the inventory:

> "I found existing Grow Product Manager data from a previous installation:"
>
> | Component | Status | Details |
> |-----------|--------|---------|
> | Configuration | ✅ Found | [user name], [N] products (updated: [date]) |
> | Template Library | ✅ Found | [N] templates |
> | Knowledge Library | ✅ Found | [N] sources, avg trust: [score] |
> | Schema version | [version] | Current plugin version: [current] |

Present options via AskUserQuestion:

- **Use existing data** — validate compatibility, migrate schema if needed, start using immediately
- **Use existing + reconfigure** — keep data but re-run configuration to review and update all sections
- **Start fresh** — archive current data to `~/.grow-pm/backups/` and run full Onboarding
- **View config first** — show current configuration in detail before deciding

### RM-4. Schema compatibility check

If user chose "Use existing data" or "Use existing + reconfigure":

**4a. Read `.schema-version`** (or "unknown" if missing)

**4b. Compare with current plugin version:**

| Scenario | Action |
|----------|--------|
| Same version | No migration needed → proceed to RM-5 |
| Minor version difference (e.g., 1.3.0 → 1.4.0) | Auto-migrate: add new fields with defaults, update `.schema-version` |
| Major version difference (e.g., 1.x → 2.x) | Guided migration: show breaking changes, ask for input on each |
| Data newer than plugin | Warn: data from newer version, some features may not be available |
| No `.schema-version` | Legacy data: run full compatibility scan, create `.schema-version` |

**4c. Before any migration — create backup:**

```
~/.grow-pm/backups/pre-migration-[current-plugin-version]-[date]/
```

Copy all current files to backup. Keep last 3 backups (delete oldest if exceeds).

**4d. Auto-migration (minor changes):**

1. Read current `local-context.md`
2. Identify fields present in current schema but missing from file → add with sensible defaults
3. Identify deprecated fields → remove or rename
4. Update `> Configurator version:` line
5. Update `.schema-version`
6. Show migration changelog to user:

> "Schema migrated from [old] to [new]. Changes:"
>
> | Change | Details |
> |--------|---------|
> | Added field | `product.new_field` — default: [value] |
> | Removed field | `product.old_field` — no longer used |

**4e. Guided migration (major changes):**

1. Show complete list of breaking changes
2. For each change requiring user input — ask via AskUserQuestion
3. Apply changes
4. Show complete changelog
5. Run validation

### RM-5. Legacy location migration

If data was found in a legacy location (not `~/.grow-pm/`):

1. Inform user: "Your plugin data is stored in [location]. Starting with v1.4.0, the plugin stores data in ~/.grow-pm/ to preserve it across reinstalls. Would you like to migrate?"
2. If yes:
   - Create `~/.grow-pm/` directory
   - Copy `local-context.md` → `~/.grow-pm/local-context.md`
   - Copy `knowledge-library/` → `~/.grow-pm/knowledge-library/` (if exists)
   - Copy `template-library/` → `~/.grow-pm/template-library/` (if exists)
   - Create `.schema-version` with best-match version
   - Run schema migration if needed (RM-4)
3. If no:
   - Continue using legacy location for this session
   - Warn: "Data in the workspace folder may be lost if the plugin is reinstalled. You can migrate later by running 'configure plugin'."

### RM-6. Post-migration validation

After migration completes:
1. Run Validate mode (V-1 through V-5)
2. Report results
3. If user chose "Use existing + reconfigure" → continue to Update mode
4. If user chose "Use existing data" → complete, show summary

> "Your existing configuration has been successfully [validated / migrated and validated]. Everything is ready to use."

---

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

### Step 9 — CJM Configuration (per product, optional)

> "Do you use Customer Journey Map (CJM) analysis in your product work? This enables funnel analysis, anomaly detection, and improvement hypothesis generation."

If no → skip to Step 10.

If yes:

**9a. Select funnel template:**

> "Which funnel template fits your product? Available templates:"
>
> - **E-commerce** — Start/Listing → Product Page → Cart/Checkout → Payment/Post-Purchase
> - **SaaS** — Awareness → Signup/Trial → Activation → Engagement → Conversion → Retention
> - **Marketplace** — Search/Browse → Listing Page → Contact/Booking → Transaction → Review
> - **Custom** — define your own stages

See `references/funnel-templates.md` for full template definitions.

**Communicate the selection:**
> "Using the **[template name]** template with stages: [list]. You can change this at any time."

**9b. If Custom template selected:**
1. Ask: "How many stages does your funnel have?"
2. For each stage: collect name, key metrics (at least 1)
3. Confirm the complete funnel

**9c. Map dashboards to stages:**

For each funnel stage:
> "Which dashboard shows data for **[Stage name]**?"

Collect dashboard URLs (Tableau, GA, or other). If the user already provided dashboard URLs in Step 5 — suggest mapping those first.

**9d. Set baseline conversions:**

> "Do you know the current conversion rates for each stage? (used as baseline for anomaly detection)"

- If yes → collect per-stage conversion rates
- If no → "We can read baselines from dashboards during the first CJM analysis."

**9e. Configure anomaly thresholds:**

> "Anomaly detection thresholds (you can use defaults or customize):"

| Level | Default | Your value |
|-------|---------|-----------|
| Warning | 10% deviation | [ask] |
| Critical | 25% deviation | [ask] |

**9f. Default analysis settings:**

| Setting | Default | Ask user |
|---------|---------|---------|
| Comparison baseline | Previous period | Previous period / Previous year / Target / Custom |
| Default platforms | All configured | All / Specific |
| Default search modes | Library + Internet | User selects from available modes |

### Step 10 — Knowledge Library Setup (optional)

> "Would you like to set up a Knowledge Library? It stores curated sources (articles, benchmarks, UX best practices) that enrich CJM analysis and research."

If no → skip to Step 11.

If yes → delegate to `knowledge-library` skill onboarding workflow (KL-1 through KL-6). The Knowledge Library skill handles:
1. Directory structure initialization
2. Source import (if user provides URLs or files)
3. Baymard Premium configuration
4. Default search modes
5. Confluence and Google Drive search validation

After Knowledge Library setup completes, continue with Step O-T.

### Step O-T — Template Library Setup (optional)

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

Follow `references/persistent-storage.md` to locate `storage_root`:
- If Obsidian Vault is configured → `{vault}/{plugin_folder}/Templates/`
- Otherwise → `~/.grow-pm/template-library/`

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

Then proceed to Step 11.

### Step 11 — Obsidian Vault (Optional)

> Requires: `references/vault-protocol.md`, `references/vault-schema.md`

Present the Vault option to the user:

> "Would you like to connect an Obsidian Vault to accumulate knowledge over time? This is optional — the plugin works fully without it."

Options via AskUserQuestion:
- **Yes, connect Vault** → proceed with vault setup
- **Skip for now** → complete onboarding without Vault section
- **What is this?** → brief explanation, then re-ask

**IF user chooses to connect:**

1. **Ask for Vault path:**
   > "What is the absolute path to your Obsidian Vault folder? This is the root folder that contains the `.obsidian/` subfolder."
   - Validate: directory exists
   - Validate: `.obsidian/` subdirectory exists (warning if not — may not be an Obsidian vault)

2. **Ask for Plugin folder name** (default: `GrowPM`):
   - Validate: no special characters except `-` and `_`

3. **Ask for Products binding:**
   - If single product → auto-bind to `all`
   - If multiple products → ask: "Should this vault store artifacts for all products, or specific ones?"
     - `all` → this vault handles everything
     - Specific → select which products

4. **Ask for Sync mode** via AskUserQuestion:
   - **Auto (recommended)** — save artifacts automatically after each skill
   - **Manual** — ask before each save
   - **Read-only** — only search vault for context, don't write

5. **Ask about additional vaults:**
   > "Do you want to add another Vault? (e.g., a separate vault for a specific product)"
   - If yes → repeat steps 1-4 for next vault
   - If no → proceed

6. **Execute vault initialization** (per `references/vault-protocol.md` → Vault Initialization):
   - Create folder structure in each configured vault
   - Create product subfolders for bound products
   - Write template files
   - Create initial Dashboard MOC
   - Copy local-context.md as reference
   - Migrate existing knowledge-library files (if found in `~/.grow-pm/knowledge-library/`)
   - Create `.vault-schema-version` file

7. **Save to local-context.md** — add the `## Obsidian Vaults (Optional)` section with all configured vaults

8. **Display summary:**
   > "Vault connected! Created {N} folders and {M} templates at {path}/{folder}/. Your artifacts will now be automatically saved to this vault."

### Step 12 — Custom Sections

> "Is there any additional information you'd like to save in the plugin context? For example: strategy documents, internal guidelines, specific processes."

Allow free-form markdown sections with custom titles.

### Step 13 — Review, confirm, and save local-context.md

**13a. Compile summary for review:**

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

**13b. Collect corrections:**

> "Is everything correct? If anything needs to be fixed — tell me what, and I'll make the changes."

- If the user requests corrections — apply them immediately and show the updated section
- Iterate until the user confirms: "OK" / "Confirmed"
- Only proceed to file generation after explicit confirmation

**13c. Generate the file:**

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

**CJM Configuration section format in local-context.md:**

```markdown
### CJM Configuration

#### Funnel Template
- Template: [e-commerce / saas / marketplace / custom]
- Custom template name: [if custom, user-provided name]

#### Funnel Stages
| Stage | Name | Dashboard URL | Baseline Conversion |
|-------|------|---------------|-------------------|
| 1 | [name] | [URL] | [%] |
| 2 | [name] | [URL] | [%] |
| ... | ... | ... | ... |

#### Anomaly Thresholds
- Warning: [X]% deviation from baseline
- Critical: [Y]% deviation from baseline

#### Default Analysis Settings
- Comparison baseline: [previous period / previous year / target]
- Default platforms: [all / specific list]
- Default search modes: [library, internet, confluence, gdrive]

#### Health-Check Notifications
- Channels: [slack / email / local / confluence]
- Frequency: [weekly / custom]
```

**Knowledge Library Configuration section format:**

```markdown
### Knowledge Library

#### Settings
- Library path: [~/.grow-pm/knowledge-library/]
- Default search modes: [library, internet]
- Trust re-evaluation schedule: monthly
- Minimum trust threshold: 0.5

#### Baymard Premium
- Access: [yes/no]
- URL: [if yes]

#### Configured Confluence Spaces (for CJM search)
- [Space key]: [description]

#### Configured Google Drive Folders (for CJM search)
- [Folder ID]: [description]
```

**Obsidian Vaults Configuration section format:**

```markdown
### Obsidian Vaults (Optional)

#### Status
- Connected: [yes/no]
- Total vaults: [N]

#### Vaults
| # | Vault Path | Folder Name | Products | Sync Mode | Last Artifact |
|---|------------|------------|----------|-----------|--------------|
| 1 | [path] | [folder] | [all/specific] | [auto/manual/read-only] | [date or never] |
| 2 | [path] | [folder] | [all/specific] | [auto/manual/read-only] | [date or never] |

#### Vault Initialization
- Status: [initialized / pending / error]
- Templates created: [N]
- MOC created: [yes/no]
- Knowledge library migrated: [yes/no]
- Schema version: [X.Y.Z]
```

**13d. Save to persistent storage:**

1. Create `~/.grow-pm/` directory if it doesn't exist (with permissions 700 on Unix)
2. Save `local-context.md` to `~/.grow-pm/local-context.md`
3. Create `~/.grow-pm/.schema-version` with the current plugin version
4. Confirm to the user: "Configuration saved to ~/.grow-pm/. This data will persist across plugin reinstalls and updates."

**13e. Vault Mirror Sync:**

After saving to `~/.grow-pm/`, if Obsidian Vault is configured (Step 11 was completed):
1. Execute Vault Mirror Protocol (VM-1 through VM-3 from `references/persistent-storage.md`)
2. Copy `local-context.md` → `{vault}/{plugin_folder}/_System/local-context.md`
3. Copy `.schema-version` → `{vault}/{plugin_folder}/_System/.schema-version`
4. If Knowledge Library was initialized → copy library files to `{vault}/{plugin_folder}/Knowledge/`
5. Log: "Configuration mirrored to Obsidian Vault at [path]"

This ensures the vault always has an up-to-date copy of all user context, serving as a secondary backup.

**13f. Automatic validation:**

After saving, automatically run a quick validation (see Validate Mode) to confirm everything works. Present the readiness report.

**13g. Template Library final invitation (only if user skipped Step O-T earlier):**

If `onboarding.templates_setup_completed` is `false` (user chose "Skip for now" during Step O-T), offer one more nudge after validation:

> "Plugin configured and ready! The built-in templates are available out of the box. If you want to set up custom templates now, you can: import from a folder, import from Confluence, or create a new one. Otherwise just say 'manage templates' any time later."

If the user confirms → delegate to `template-library` with the chosen action.

If Step O-T was already completed (user set up Template Library in Step O-T), skip this step and go directly to the final summary.

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
- CJM Configuration
- Knowledge Library Settings
- Template Library Settings
- Obsidian Vault Management
- Repositories
- Custom Sections
- Add new custom section

### U-3. Update the selected section

Follow the same collection flow as Onboarding for the selected section. Pre-fill all fields with current values so the user only needs to change what's different.

**For CJM Configuration updates:**
- Allow changing funnel template (with remapping prompt)
- Allow adding/removing/editing stages
- Allow changing thresholds and default settings
- Allow changing notification channels

**For Knowledge Library updates:**
- Allow changing default search modes
- Allow changing Baymard configuration
- Allow adding/removing Confluence spaces and Google Drive folders
- For source management → redirect to `knowledge-library` skill in Manage mode

**For Template Library Settings updates:**
- Allow changing `templates.preference` (auto / always_ask / smart)
- Allow changing `templates.default_language`
- Allow changing `templates.auto_save_to_vault`
- Allow editing `templates.favorite_templates` (reorder / add / remove)
- For template CRUD (add / edit / delete / import / rebuild-registry) → redirect to `template-library` skill with the requested action

**For Obsidian Vault Management:**

When user wants to manage Vault settings, offer these options via AskUserQuestion:

- **Connect Vault** — if no Vault section exists, run the onboarding Vault step
- **Add another Vault** — add additional vault to the list
- **Change Vault path** — update path for existing vault (check if artifacts exist at old path → offer to move them)
- **Change sync mode** — update sync mode for a vault
- **Change product binding** — update which products a vault handles
- **Re-initialize** — recreate folder structure + templates without losing existing artifact files
- **Disconnect Vault** — remove vault from config (files remain on disk, inform user)
- **Vault health check** — verify folder structure integrity, count artifacts by type, find orphaned files, check for broken wikilinks
- **Backup Vault** — create .zip archive of vault plugin folder to `~/.grow-pm/backups/vault-{date}.zip`

### U-4. Save updated file, mirror to vault, and show changelog

- Update the `Updated:` timestamp
- Preserve all sections that were not modified
- Preserve all custom sections
- Save to `~/.grow-pm/local-context.md` (always use persistent storage)
- **Mirror to Obsidian Vault** (if configured): execute Vault Mirror Protocol (VM-1 through VM-3 from `references/persistent-storage.md`) — sync changed files to `{vault}/{plugin_folder}/_System/`

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
| CJM → Funnel Template | e-commerce | **saas** |
| CJM → Anomaly Thresholds | Warning: 10%, Critical: 25% | Warning: **8%**, Critical: **20%** |
| Knowledge Library → Search modes | library, internet | library, internet, **confluence** |
| Obsidian Vaults → Added | (not configured) | **1 vault connected: /path/to/vault, sync: auto** |
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
- If CJM dashboards are configured — verify each stage dashboard is accessible

### V-4. Check context completeness

Score each product's context completeness:

| Category | Fields | Weight |
|----------|--------|--------|
| **Core** (required) | product name, description, platforms, jira_project_key | 35% |
| **Publishing** | confluence_space, confluence_template | 15% |
| **Analytics** | key_metrics, dashboards, ab_test_dashboards | 15% |
| **Team** | team name, members, jira_team_id | 15% |
| **Strategy** | OKRs, competitors, metric_targets | 10% |
| **CJM** | funnel template, stages, dashboards, thresholds | 5% |
| **Knowledge Library** | initialized, sources count, search modes | 5% |

Calculate a completeness percentage per product and overall.

### V-5. Validate Vault connectivity

IF `local-context.md` contains Obsidian Vaults section:

For each configured vault:
1. Check vault path exists → ✅ or ❌
2. Check plugin folder exists → ✅ or ❌
3. Check folder structure completeness → ✅ or "Missing: [list]"
4. Count artifacts by type → display summary table
5. Check .vault-schema-version → compatible or needs migration
6. Check MCP availability (if not disabled) → ✅ L2 available or ℹ️ L1 only
7. Verify last save timestamp → "Last artifact saved: [date]"

Add to the validation report output.

### V-6. Produce readiness report

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

### CJM Readiness
| Product | Template | Stages | Dashboards mapped | Status |
|---------|----------|--------|-------------------|--------|
| Product 1 | e-commerce | 4/4 | 3/4 | ⚠️ Stage 4 dashboard missing |
| Product 2 | — | — | — | ❌ Not configured |

### Knowledge Library
| Metric | Value |
|--------|-------|
| Status | ✅ Initialized |
| Sources | 37 |
| Avg trust | 0.78 |
| Search modes | library, internet, confluence |

### Obsidian Vaults
| Vault | Path | Status | Artifacts | Last Save |
|-------|------|--------|-----------|-----------|
| Primary | /Users/name/Vault | ✅ Connected | 23 files | 2026-04-14 |
| Product A | /Users/name/VaultA | ✅ Connected | 8 files | 2026-04-12 |

### Recommendations
1. Connect Figma MCP for working with designs
2. Add OKRs for Product 1 (improves analysis and concept quality)
3. Add competitors for Product 2 (required for research)
4. Map Stage 4 dashboard for Product 1 CJM analysis

### Overall readiness: 75%
```

If issues found — offer to run Update mode to fix them.

---

## Workflow — View Mode

View mode allows the user to see the current configuration and make inline changes through dialogue.

### VW-1. Read and display current context

Read `local-context.md` and present its contents in a clean, readable format — section by section:

> "Here is the current plugin configuration:"

Display each section with clear headings. For long sections (teams, metrics) — use tables. Show completeness indicators where fields are empty or missing. Include CJM Configuration, Knowledge Library, and Obsidian Vaults sections.

### VW-2. Ask if changes are needed

> "Would you like to change anything? Just tell me what — for example: 'change email', 'add competitor X', 'remove product Y', 'switch CJM template to SaaS', 'connect a vault'."

### VW-3. Apply inline changes

If the user requests changes via dialogue:
1. Parse the user's request — identify which section and field to change
2. Apply the change
3. Show the changelog (same format as Update Mode U-4)
4. Ask if there are more changes needed
5. Repeat until the user says they're done

### VW-4. Save if changes were made

If any changes were applied:
- Save the updated `local-context.md` to `~/.grow-pm/local-context.md`
- Show the complete changelog of all changes made during this View session
- Update the `Updated:` timestamp

If no changes were made — simply end the mode.

---

## Changelog Protocol (applies to ALL modes that modify local-context.md)

Every time `local-context.md` is modified — whether by Onboarding (Step 13), Update, View, or Enrichment from other skills — the user MUST receive a changelog report showing:

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
- **CJM Research** → can update baseline conversions from dashboard data

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
- When communicating CJM template selection — always name the template and list the stages

## Additional Resources

- **`references/persistent-storage.md`** — persistent storage protocol (`~/.grow-pm/`), migration, backup, legacy data handling
- **`references/context-schema.md`** — complete schema definition with field descriptions, required/optional status, and which skills use each field
- **`references/local-context-protocol.md`** — how all skills read and use `local-context.md`
- **`references/integration-strategy.md`** — MCP → Registry → Browser fallback chain (shared across all skills)
- **`references/self-improvement.md`** — self-improvement protocol
- **`references/cjm-protocol.md`** — CJM anomaly severity, funnel impact formulas, health score
- **`references/funnel-templates.md`** — standard funnel stage templates by product type
- **`references/vault-protocol.md`** — Obsidian Vault initialization, folder structure, artifact management
- **`references/vault-schema.md`** — Vault schema definition, template formats, metadata storage
- **`references/template-protocol.md`** — template resolution protocol used by Step O-T and consumer skills
- **`skills/template-library/SKILL.md`** — CRUD actions and wizards for the Template Library
