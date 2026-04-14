# Local Context Protocol

This document defines how every skill in the plugin reads and uses `local-context.md`. **All skills MUST follow this protocol at the start of execution.**

For persistent storage details, see **`references/persistent-storage.md`**.
For Vault integration details, see **`references/vault-protocol.md`**.

## Step 0 — Check and read local-context.md (MANDATORY)

Before any other action, the skill MUST:

### 0a. Search for local-context.md

Search in the following locations (in priority order):

1. **`~/.grow-pm/local-context.md`** — persistent home directory (primary, survives plugin reinstalls)
2. Plugin root directory (relative: `../../local-context.md` from skill folder) — legacy location
3. User's workspace/outputs folder (the mounted folder or outputs directory) — legacy location
4. Session working directory — fallback

**If found in a legacy location (2-4) but NOT in `~/.grow-pm/`:** the file is from a pre-v1.4.0 install. Before proceeding, offer to migrate it to `~/.grow-pm/` (see `references/persistent-storage.md` → Legacy Data Discovery). If the user agrees — migrate, then continue. If the user declines — use it in-place but warn that data may be lost on plugin reinstall.

**When saving:** ALWAYS write to `~/.grow-pm/local-context.md`. Never save to legacy locations.

### 0b. If NOT found (anywhere) → redirect to Plugin Configurator

Stop the current skill workflow and inform the user:

> "To work effectively, the plugin needs to be configured with your organization, products, and tools context. Let's run a quick setup (~5-10 min)."

Launch the **Plugin Configurator** skill in **Onboarding** mode. The Configurator will create `~/.grow-pm/` and save all data there. After Onboarding completes — return to the original skill and continue its workflow with the newly created context.

### 0c. If found → read and parse

Read `local-context.md` and extract:
- Active user profile (name, role, email, language, jira_account_id)
- List of organizations and their products
- Integration details for the current context

### 0d. Select active product

If the file contains **multiple products**:
1. If the user explicitly mentioned a product name in their request → use it
2. If only one product exists → use it automatically
3. If multiple products exist and none was mentioned → ask via AskUserQuestion:
   > "There are multiple products in the context: [list names]. Which product are we working with now?"

The selected product becomes the **active product** for the current skill session. All product-specific fields (platforms, locales, jira_project_key, Confluence space, dashboards, competitors, etc.) are read from the active product's section.

### 0e. Check for missing required fields

Each skill has specific required fields (see `references/context-schema.md` → "Which Skills Read What"). If required fields are missing for the current skill:
- Inform the user which fields are missing
- Offer two options:
  1. Run **Plugin Configurator** in Update mode to add missing data
  2. Proceed without the missing context (skill will ask for this info manually during execution)

### 0f. Check for CJM configuration (CJM skills only)

**This step applies only to:** `cjm-research`, `product-analysis` (when invoked in CJM mode), `brainstorm-features` (when invoked in CJM mode).

Check if `local-context.md` contains a **CJM Configuration** section for the active product:

**If CJM Configuration is missing:**
- Inform the user: "CJM analysis requires funnel configuration (stages, dashboards, thresholds). Would you like to set it up now?"
- If yes → launch Plugin Configurator in Update mode, specifically Step 9 (CJM Configuration)
- If no → the skill cannot proceed in CJM mode. Offer to run in a non-CJM mode if available, or end.

**If CJM Configuration is present:**
- Read funnel template type, stages, dashboards, thresholds, default settings
- Communicate the active template to the user: "Using **[template name]** template with [N] stages."

### 0g. Check Knowledge Library availability (optional)

**This step is informational — not blocking.** Skills that support Knowledge Library enrichment should check:

1. Does `~/.grow-pm/knowledge-library/` directory exist? (primary)
2. If not — does `workspace/knowledge-library/` exist? (legacy location)
3. Does `library.md` contain any sources?

If found in legacy location only — note this for potential migration prompt.
If initialized and non-empty — note availability internally (used when proposing enrichment to user).
If not initialized — no action needed, the skill continues normally without library access.

### 0h. Detect Vault level (optional)

**This step is informational — not blocking.** Detect Obsidian Vault integration level for use in Step 0.5 and vault_save operations.

Follow the detection algorithm from `references/vault-protocol.md` → "Vault Level Detection":

1. Check if `local-context.md` contains an **Obsidian Vaults** section
2. If section is missing or no vault paths configured → `vault_level = L0` (disabled, skip silently)
3. If vault path(s) configured → validate directories exist → `vault_level = L1` (file system)
4. If MCP detection is enabled → try Obsidian MCP ping → if responds `vault_level = L2` (file + MCP)

Store `vault_level` and `vault_configs` in session context for use by Step 0.5 and vault_save.

**If vault_level is L0** — no further vault-related actions in this session. All vault operations will be silently skipped.

## Step 0.5 — Vault Context Search (OPTIONAL)

**Applies to all skills.** Inserted between Step 0 and Step 1. If `vault_level == L0` — skip this step silently without any output.

Follow the full protocol from `references/vault-protocol.md` → "Step 0.5 — Vault Context Search":

1. Determine relevant artifact types for this skill (see `vault-protocol.md` → SKILL_CONTEXT_MAP)
2. Search the vault for matching artifacts (product, types, tags, status: active/draft)
3. If multi-vault: search all configured vaults, merge results
4. If results found — present to user:
   > "Found {N} related artifacts in your knowledge base: [brief list]. Use as context? [Yes / Select specific / Skip]"
5. If user accepts — read full content of selected artifacts and include as additional context
6. If user skips or no results — continue normally

**Important:** This step should be brief. Read only frontmatter + Summary section for preview. Full content is loaded only for artifacts the user selects.

## Context Enrichment

During execution, skills may discover new information that should be saved to `local-context.md`. When this happens:

1. Inform the user: "I found new information: [description]. Would you like to save it to the plugin context?"
2. If the user agrees:
   - Read the current `~/.grow-pm/local-context.md`
   - Add the new information to the appropriate section
   - Update the "Updated:" timestamp
   - Save the file back to `~/.grow-pm/local-context.md`

Examples of discoverable context:
- **Product Research** → new competitors found during research
- **Product Analysis** → current metric values from dashboards
- **Feature Task Creator** → Jira team IDs, member accountIds discovered from existing tasks
- **Requirements Creator** → Confluence template URL discovered during publishing
- **CJM Research** → updated baseline conversions read from dashboards

## Vault Save (after skill output)

**Applies to all skills that produce artifacts.** Executed after the skill delivers its main output to the user.

If `vault_level == L0` — skip silently. Otherwise, follow the full protocol from `references/vault-protocol.md` → "Vault Save":

1. Resolve target vault for the current product
2. Build file path using naming convention from `vault-schema.md`
3. Build frontmatter with appropriate type-specific fields
4. Ensure mandatory `## Summary` section (2-5 sentences)
5. Link to related artifacts (if auto-link enabled)
6. Write file to vault
7. Update MOC indexes (if auto-update enabled)
8. Inform user: "Saved to Vault: {path}"

**This step is non-blocking.** Any vault save error should be logged and reported but must NOT prevent the skill from completing its main workflow.

## Using context in skills

Once the context is loaded and active product selected, skills should:

- Use `product.name` when asking about product context (skip the "which product?" question)
- Use `product.platforms` when presenting platform options (pre-fill the list)
- Use `product.locales` as defaults for locale questions
- Use `product.jira_project_key` for Jira queries
- Use `product.confluence_space` as default publishing destination
- Use `product.competitors` when building comparison matrices (always include user's product)
- Use `product.key_metrics` when discussing metrics (pre-fill known metrics)
- Use `product.current_okrs` to align hypotheses and analysis with strategic goals
- Use `organization.tableau_base_url` and `product.ab_test_dashboards` for analytics access
- Use `user.language` for output language preference
- Use `user.jira_account_id` for setting Reporter on Jira tasks
- Use `team.jira_team_id` for setting Team field on Jira tasks
- Use `product.cjm_configuration.funnel_stages` for CJM funnel analysis
- Use `product.cjm_configuration.anomaly_thresholds` for anomaly detection
- Use `product.cjm_configuration.default_search_modes` for Knowledge Library search
- Use `knowledge_library.configured_confluence_spaces` for Confluence CJM search
- Use `knowledge_library.configured_gdrive_folders` for Google Drive CJM search
- Use vault context (from Step 0.5) to enrich analysis with historical data and prior decisions
