# Maintenance modes — Reinstall/Migration, Update, Validate, View + Versioning Protocol

> Part of `plugin-configurator`. Loaded on demand when the corresponding mode starts. Mode map and entry conditions live in SKILL.md.

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
1. Run Validate mode (V-1 through V-6)
2. Report results
3. If user chose "Use existing + reconfigure" → continue to Update mode
4. If user chose "Use existing data" → complete, show summary

> "Your existing configuration has been successfully [validated / migrated and validated]. Everything is ready to use."

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
- Planning (capacity, sprints, goal map, development flow)
- Focus (sources, zones, VIP senders, PM goals, cadence, scheduled briefs)
- People (roster, cadences, HR-form field map)
- Design Toolkits (external hi-fi/screen-generation providers)
- Custom Sections
- Add new custom section

> The last four are the sections the Planning / Focus / People / Design Toolkit setup steps write and then hand off here ("offer review/update via `update config`"). They were missing from this menu until v2.1.0, so that handoff was a dead end.

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

Read `local-context.md` and scan all MCP connectors (same as Onboarding Step 3a).

### V-2. Test MCP connections

For each integration referenced in the context:

| Integration | Test | Expected result |
|-------------|------|-----------------|
| **Jira** | `getJiraIssue` with a known project key | Project accessible |
| **Confluence** | `getConfluenceSpaces` + check configured space exists | Space accessible |
| **Figma** | `whoami` | Account verified |
| **Notion** | `notion-get-teams` | Workspace accessible |
| **Tableau** | If Tableau MCP available: `search-content` (no terms, limit 1) returns metadata. Else navigate to dashboard URL via browser | Connector responds / page loads |
| **Google Sheets** | Navigate to sheet URL via browser | Sheet loads |

### V-3. Test data access

For each product in the context:
- Try to search Jira issues in the configured project: `searchJiraIssuesUsingJql` with `project = PROJECT_KEY ORDER BY created DESC` (limit 1)
- Try to access the configured Confluence space: `getConfluenceSpaces` and verify the space key exists
- If dashboard URLs are configured — try to navigate and take a screenshot to verify access
- If CJM dashboards are configured — verify each stage dashboard is accessible

### V-4. Check context completeness

First check the file-level requirements from `references/context-schema.md` → Validation Rules: the **User Profile** block (name, role, email, language) and the **Onboarding Status** block (`mode`, `deferred_steps`) must be present and well-formed. A missing User Profile is a finding no per-product score would surface.

Then score each product's context completeness:

| Category | Fields | Weight |
|----------|--------|--------|
| **Core** (required) | product name, description, platforms, jira_project_key | 30% |
| **Publishing** | confluence_space, confluence_template | 10% |
| **Analytics** | key_metrics, dashboards, ab_test_dashboards | 10% |
| **Team** | team name, members, jira_team_id | 10% |
| **Strategy** | OKRs, competitors, metric_targets | 10% |
| **CJM** | funnel template, stages, dashboards, thresholds | 5% |
| **Knowledge Library** | initialized, sources count, search modes | 5% |
| **Templates** | preference set, registry reachable at `storage_root` | 5% |
| **Planning** | jira_board_id, sprint cadence+anchor, capacity team, goal_map, development_flow | 10% |
| **Focus** | sources, zones, VIP senders, PM goals, cadence, scheduled | 5% |

Calculate a completeness percentage per product and overall.

**Sections deferred in Basic are not penalized** — report them as "deferred, add via `update config`" rather than as gaps; a Basic setup is a complete Basic setup, not a broken Extended one.

**People and Design Toolkits are validated for presence only** (configured / not configured), never scored: People data is the PM's to keep as sparse as they like, and a toolkit is optional by design.

> Planning, Focus and Templates were invisible to "validate setup" until v2.1.0 — a readiness report could read 100% while the planning suite had nothing to read.

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
