# Persistent Storage Protocol

This document defines how the Grow Product Manager plugin stores user data persistently across plugin reinstalls, updates, and deletions. **All skills that read or write user data MUST follow this protocol.**

## Design Principle

User configuration, templates, and knowledge are **the user's data**, not plugin data. They MUST survive plugin lifecycle events (uninstall, reinstall, update). The plugin stores all user-generated data in a dedicated directory in the user's home folder, separate from the plugin installation directory.

## Storage Location

All persistent user data is stored under:

```
~/.grow-pm/
```

Resolved as `$HOME/.grow-pm/` on the user's machine. In Cowork sessions, this translates to the user's home directory (e.g., `/Users/username/.grow-pm/`).

### Directory Structure

```
~/.grow-pm/
├── local-context.md              # Main plugin configuration (user profile, orgs, products, teams)
├── .schema-version               # Schema version marker (for migration compatibility)
├── template-library/
│   ├── _registry.json            # Template registry
│   └── templates/                # Template files organized by type
│       ├── requirements/
│       ├── concepts/
│       ├── presentations/
│       └── ...
├── knowledge-library/
│   ├── library.md                # Master index
│   ├── categories.md             # Category definitions
│   ├── trust-scores.yaml         # Trust scores metadata
│   ├── sources/                  # Individual source detail files
│   └── health-checks/            # CJM health-check snapshots
└── backups/                      # Auto-backups before migrations
    ├── pre-migration-1.4.0/      # Backup taken before migrating to v1.4.0
    │   ├── local-context.md
    │   ├── .schema-version
    │   └── ...
    └── ...
```

### .schema-version File

A plain-text file containing the plugin version that last wrote/migrated the data:

```
1.4.0
```

This is used by the migration protocol to determine if data needs to be migrated.

---

## File Search Priority

When any skill needs to locate `local-context.md` (or any other persistent file), search in this order:

| Priority | Location | Description |
|----------|----------|-------------|
| 1 (highest) | `~/.grow-pm/local-context.md` | **Persistent home directory** — primary location |
| 2 | Plugin root directory (`../../local-context.md` from skill folder) | Legacy location (pre-v1.4.0 installs) |
| 3 | User's workspace/outputs folder | Session workspace (Cowork outputs) |
| 4 | Session working directory | Current session directory |

**Important:** When saving files, ALWAYS write to `~/.grow-pm/`. The lower-priority locations are only checked for backward compatibility with pre-v1.4.0 data.

Similarly for `knowledge-library/` and `template-library/`:

| Priority | Location | Description |
|----------|----------|-------------|
| 1 (highest) | `~/.grow-pm/knowledge-library/` | Persistent home directory |
| 2 | `workspace/knowledge-library/` | Legacy workspace location |

---

## Directory Initialization

When the `~/.grow-pm/` directory does not exist, the Plugin Configurator creates it during Onboarding:

1. Create `~/.grow-pm/` directory
2. Create `.schema-version` file with current plugin version
3. Proceed with normal Onboarding workflow
4. Save all generated files to `~/.grow-pm/`

If the directory exists but `.schema-version` is missing — treat as legacy data and run migration (see below).

---

## Migration Protocol (on reinstall / update)

When a user installs or updates the plugin, the Plugin Configurator runs a **Persistent Data Check** before any other operation.

### Step M-0. Detect existing data

Check if `~/.grow-pm/` exists:

- **Directory does not exist** → fresh install, proceed to Onboarding
- **Directory exists** → existing user data found, proceed to Step M-1

### Step M-1. Read schema version

Read `~/.grow-pm/.schema-version`:

- **File exists** → compare with current plugin version
- **File missing** → legacy data (pre-v1.4.0), needs full migration scan

### Step M-2. Present findings to user

Always inform the user what was found and ask how to proceed:

> "I found existing plugin data from a previous installation:"
>
> | Component | Status | Details |
> |-----------|--------|---------|
> | Configuration | ✅ Found | local-context.md (last updated: [date]) |
> | Template Library | ✅ Found | [N] templates in [M] categories |
> | Knowledge Library | ✅ Found | [N] sources, avg trust: [score] |
> | Schema version | [version or "unknown"] | Current plugin: [current version] |
>
> "How would you like to proceed?"

Present options via AskUserQuestion:

- **Use existing data** — keep everything as is, validate and update schema if needed
- **Use existing data + reconfigure** — keep data but re-run configuration to update/add sections
- **Start fresh** — archive existing data to `~/.grow-pm/backups/` and run full Onboarding
- **View existing config first** — show current configuration before deciding

### Step M-3. Schema compatibility check

If user chose to keep existing data, verify compatibility:

**3a. Compare schema versions:**

| Scenario | Action |
|----------|--------|
| Same version | No migration needed, proceed normally |
| Newer plugin, minor version diff | Auto-migrate: add new optional fields with defaults |
| Newer plugin, major version diff | Guided migration: show what will change, ask for confirmation |
| Older plugin than data | Warn: "Your data was created by a newer plugin version. Some features may not work correctly." |
| No schema version | Legacy data: run full compatibility scan |

**3b. Auto-migration (minor version changes):**

1. Create backup in `~/.grow-pm/backups/pre-migration-[version]/`
2. Read current `local-context.md`
3. Add new fields introduced in the current version (with sensible defaults or empty)
4. Remove deprecated fields (if any)
5. Update `.schema-version`
6. Show migration changelog to user

**3c. Guided migration (major version changes):**

1. Create backup in `~/.grow-pm/backups/pre-migration-[version]/`
2. Read current data
3. Show a detailed comparison: "Here's what will change in the new version:"
4. For each breaking change — ask user to provide updated values
5. Apply changes
6. Update `.schema-version`
7. Show complete migration changelog
8. Run validation (Validate mode)

### Step M-4. Validate migrated data

After migration:
1. Run Plugin Configurator in Validate mode
2. Check all MCP connections still work
3. Check all referenced resources (Jira projects, Confluence spaces) are accessible
4. Report any issues

---

## Legacy Data Discovery

For users upgrading from pre-v1.4.0 (where data was stored in workspace/outputs):

### L-1. Search for legacy data

During first plugin launch, after checking `~/.grow-pm/`, also search legacy locations:
1. User's workspace/outputs folder
2. Plugin root directory
3. Session working directory

### L-2. If legacy data found

Inform the user:

> "I found plugin data from an older version in your workspace folder. Would you like to migrate it to the persistent storage (~/.grow-pm/) so it's preserved across plugin reinstalls?"

Options:
- **Yes, migrate** — copy data to `~/.grow-pm/`, run schema migration, validate
- **No, start fresh** — ignore legacy data, run Onboarding with fresh `~/.grow-pm/`
- **Let me review first** — show the found data before deciding

### L-3. Migration from legacy location

1. Copy all found files to `~/.grow-pm/` (preserving structure):
   - `local-context.md` → `~/.grow-pm/local-context.md`
   - `knowledge-library/` → `~/.grow-pm/knowledge-library/`
   - `template-library/` → `~/.grow-pm/template-library/` (if exists)
2. Create `.schema-version` with the version that best matches the data format
3. Run schema migration if needed (Step M-3)
4. Validate (Step M-4)
5. Inform user: "Data migrated successfully. Your configuration is now stored in ~/.grow-pm/ and will persist across plugin reinstalls."

---

## Backup Protocol

### Automatic backups

Backups are created automatically:
- Before any schema migration (Step M-3)
- Before major configuration changes (full Onboarding re-run)

### Backup structure

```
~/.grow-pm/backups/pre-migration-[version]/
├── local-context.md
├── .schema-version
├── knowledge-library/     (if exists)
│   ├── library.md
│   ├── trust-scores.yaml
│   └── ...
└── template-library/      (if exists)
    ├── _registry.json
    └── ...
```

### Backup cleanup

Keep the last 3 backups. When creating a new backup and there are already 3 — delete the oldest one.

---

## Symlink to Workspace (optional)

After saving data to `~/.grow-pm/`, the plugin can optionally create a **symlink** in the workspace folder for easy access:

```
workspace/.grow-pm-data → ~/.grow-pm/
```

This is offered during Onboarding:
> "Would you like a shortcut to your plugin data in the workspace folder? This makes it easy to view and edit configuration files directly."

This is purely for convenience and is not required for plugin operation.

---

## Deletion Behavior

When the plugin is uninstalled:
- **`~/.grow-pm/` is NOT deleted** — user data persists
- Only plugin code/skills are removed
- On next install, migration protocol detects and reuses existing data

If the user explicitly wants to delete all data:
> "To completely remove all Grow Product Manager data, delete the ~/.grow-pm/ directory."

**CRITICAL: Plugin uninstall / reinstall MUST NOT touch `~/.grow-pm/`.** This directory is outside the plugin installation path specifically to survive any plugin lifecycle event. No cleanup script, no pre-uninstall hook, no post-update migration should ever delete files from `~/.grow-pm/` without explicit user consent.

---

## Pre-Update Backup Protocol

**Before ANY plugin update**, the system MUST create an automatic backup of all user data. This is the primary defense against data loss during plugin updates.

### PU-1. Trigger conditions

A pre-update backup is triggered:
- Before plugin update (version change detected)
- Before plugin reinstall (existing `~/.grow-pm/` found during fresh install)
- Before any schema migration (already covered in Migration Protocol)
- Manually by user via Plugin Configurator → "Backup" action

### PU-2. Backup procedure

1. **Create timestamped backup directory:**
   ```
   ~/.grow-pm/backups/pre-update-[old-version]-to-[new-version]-[YYYY-MM-DD]/
   ```
   If no version info available:
   ```
   ~/.grow-pm/backups/pre-update-[YYYY-MM-DD-HHmmss]/
   ```

2. **Copy ALL user data files:**
   - `local-context.md`
   - `.schema-version`
   - `knowledge-library/` (entire directory recursively)
   - `template-library/` (entire directory recursively)

3. **Write backup manifest:**
   ```
   ~/.grow-pm/backups/pre-update-.../MANIFEST.md
   ```
   Contents:
   ```markdown
   # Backup Manifest
   - Date: [ISO timestamp]
   - Trigger: [update / reinstall / migration / manual]
   - Plugin version (before): [version or unknown]
   - Plugin version (after): [new version]
   - Files backed up: [count]
   - Knowledge Library sources: [count]
   - Template Library templates: [count]
   ```

4. **Keep last 5 backups** (increased from 3 to provide more safety net). Delete oldest when exceeding limit.

### PU-3. Backup verification

After creating backup:
1. Verify backup directory exists and is non-empty
2. Verify `local-context.md` was copied (compare file size)
3. If `knowledge-library/library.md` existed — verify it was copied
4. Log success or failure

### PU-4. Backup restore

If user data is lost or corrupted, recovery follows this priority:

| Priority | Source | How to restore |
|----------|--------|---------------|
| 1 (best) | `~/.grow-pm/backups/` | Copy latest backup → `~/.grow-pm/` |
| 2 | Obsidian Vault (if configured) | Reconstruct from vault mirror (see Vault Recovery Protocol) |
| 3 | Legacy locations | Search workspace/outputs, session dirs |
| 4 | Manual | User re-creates via Onboarding |

---

## Vault Mirror Protocol (Obsidian as secondary storage)

When Obsidian Vault is configured, `~/.grow-pm/` data MUST be mirrored to the vault. This provides a secondary backup that is:
- Visible and browsable by the user
- Synced via Obsidian Sync / Git / iCloud (user's choice)
- Recoverable even if `~/.grow-pm/` is deleted

### VM-1. What gets mirrored

| Source | Vault destination |
|--------|-------------------|
| `~/.grow-pm/local-context.md` | `{vault}/{plugin_folder}/_System/local-context.md` |
| `~/.grow-pm/.schema-version` | `{vault}/{plugin_folder}/_System/.schema-version` |
| `~/.grow-pm/knowledge-library/library.md` | `{vault}/{plugin_folder}/Knowledge/library.md` |
| `~/.grow-pm/knowledge-library/categories.md` | `{vault}/{plugin_folder}/Knowledge/categories.md` |
| `~/.grow-pm/knowledge-library/trust-scores.yaml` | `{vault}/{plugin_folder}/Knowledge/trust-scores.yaml` |
| `~/.grow-pm/knowledge-library/sources/*` | `{vault}/{plugin_folder}/Knowledge/sources/*` |

### VM-2. When to sync

Mirror sync happens:
- After every write to `~/.grow-pm/` (local-context.md update, knowledge-library change, etc.)
- After migration completes
- After backup restore
- On explicit user request ("sync to vault")

### VM-3. Sync direction

**Primary: `~/.grow-pm/` → Vault** (write-through)

Every write to `~/.grow-pm/` is immediately followed by a write to the vault mirror location. This is a one-way sync — the vault is a replica.

**Recovery: Vault → `~/.grow-pm/`** (restore)

If `~/.grow-pm/` data is missing but vault mirror exists, the system can restore from vault. See Vault Recovery Protocol below.

---

## Vault Recovery Protocol

When `~/.grow-pm/` is empty or missing but a configured Obsidian Vault exists with mirrored data:

### VR-1. Detection

During Step 0 (context loading), if `~/.grow-pm/local-context.md` is NOT found:
1. Check if vault paths are known (from Cowork session memory, previous conversation, or user input)
2. Search vault for `_System/local-context.md`
3. Search vault for `Knowledge/library.md`

### VR-2. Recovery prompt

If vault data is found:

> "I couldn't find your plugin data at ~/.grow-pm/, but I found a copy in your Obsidian Vault at [path]. This may have happened due to a plugin update or reinstall."
>
> | Component | Vault status | Details |
> |-----------|-------------|---------|
> | Configuration | ✅ Found | [user name], [N] products |
> | Knowledge Library | ✅ Found | [N] sources |
> | Schema version | [version] | |
>
> "Would you like to restore from the vault?"

Options:
- **Yes, restore** — copy vault data → `~/.grow-pm/`, validate, continue
- **No, start fresh** — run Onboarding
- **Let me check first** — show vault data contents

### VR-3. Restore procedure

1. Create `~/.grow-pm/` directory
2. Copy `_System/local-context.md` → `~/.grow-pm/local-context.md`
3. Copy `_System/.schema-version` → `~/.grow-pm/.schema-version`
4. Copy `Knowledge/library.md` → `~/.grow-pm/knowledge-library/library.md`
5. Copy `Knowledge/categories.md` → `~/.grow-pm/knowledge-library/categories.md`
6. Copy `Knowledge/trust-scores.yaml` → `~/.grow-pm/knowledge-library/trust-scores.yaml`
7. Copy `Knowledge/sources/*` → `~/.grow-pm/knowledge-library/sources/`
8. Run schema compatibility check (Step M-3 from Migration Protocol)
9. Validate restored data
10. Inform user: "Data restored successfully from Obsidian Vault."

---

## Security Considerations

- `local-context.md` contains organization-specific configuration (Jira URLs, project keys, team members) — it should not be shared publicly
- `~/.grow-pm/` should have user-only permissions (chmod 700 on Unix systems)
- Backups inherit the same permission model
- Skills should never log or expose the full path of `~/.grow-pm/` to external services
# Persistent Storage Protocol

This document defines how the Grow Product Manager plugin stores user data persistently across plugin reinstalls, updates, and deletions. **All skills that read or write user data MUST follow this protocol.**

## Design Principle

User configuration, templates, and knowledge are **the user's data**, not plugin data. They MUST survive plugin lifecycle events (uninstall, reinstall, update). The plugin stores all user-generated data in a dedicated directory in the user's home folder, separate from the plugin installation directory.

## Storage Location

All persistent user data is stored under:

```
~/.grow-pm/
```

Resolved as `$HOME/.grow-pm/` on the user's machine. In Cowork sessions, this translates to the user's home directory (e.g., `/Users/username/.grow-pm/`).

### Directory Structure

```
~/.grow-pm/
├── local-context.md              # Main plugin configuration (user profile, orgs, products, teams)
├── .schema-version               # Schema version marker (for migration compatibility)
├── template-library/
│   ├── _registry.json            # Template registry
│   └── templates/                # Template files organized by type
│       ├── requirements/
│       ├── concepts/
│       ├── presentations/
│       └── ...
├── knowledge-library/
│   ├── library.md                # Master index
│   ├── categories.md             # Category definitions
│   ├── trust-scores.yaml         # Trust scores metadata
│   ├── sources/                  # Individual source detail files
│   └── health-checks/            # CJM health-check snapshots
└── backups/                      # Auto-backups before migrations
    ├── pre-migration-1.4.0/      # Backup taken before migrating to v1.4.0
    │   ├── local-context.md
    │   ├── .schema-version
    │   └── ...
    └── ...
```

### .schema-version File

A plain-text file containing the plugin version that last wrote/migrated the data:

```
1.4.0
```

This is used by the migration protocol to determine if data needs to be migrated.

---

## File Search Priority

When any skill needs to locate `local-context.md` (or any other persistent file), search in this order:

| Priority | Location | Description |
|----------|----------|-------------|
| 1 (highest) | `~/.grow-pm/local-context.md` | **Persistent home directory** — primary location |
| 2 | Plugin root directory (`../../local-context.md` from skill folder) | Legacy location (pre-v1.4.0 installs) |
| 3 | User's workspace/outputs folder | Session workspace (Cowork outputs) |
| 4 | Session working directory | Current session directory |

**Important:** When saving files, ALWAYS write to `~/.grow-pm/`. The lower-priority locations are only checked for backward compatibility with pre-v1.4.0 data.

Similarly for `knowledge-library/` and `template-library/`:

| Priority | Location | Description |
|----------|----------|-------------|
| 1 (highest) | `~/.grow-pm/knowledge-library/` | Persistent home directory |
| 2 | `workspace/knowledge-library/` | Legacy workspace location |

---

## Directory Initialization

When the `~/.grow-pm/` directory does not exist, the Plugin Configurator creates it during Onboarding:

1. Create `~/.grow-pm/` directory
2. Create `.schema-version` file with current plugin version
3. Proceed with normal Onboarding workflow
4. Save all generated files to `~/.grow-pm/`

If the directory exists but `.schema-version` is missing — treat as legacy data and run migration (see below).

---

## Migration Protocol (on reinstall / update)

When a user installs or updates the plugin, the Plugin Configurator runs a **Persistent Data Check** before any other operation.

### Step M-0. Detect existing data

Check if `~/.grow-pm/` exists:

- **Directory does not exist** → fresh install, proceed to Onboarding
- **Directory exists** → existing user data found, proceed to Step M-1

### Step M-1. Read schema version

Read `~/.grow-pm/.schema-version`:

- **File exists** → compare with current plugin version
- **File missing** → legacy data (pre-v1.4.0), needs full migration scan

### Step M-2. Present findings to user

Always inform the user what was found and ask how to proceed:

> "I found existing plugin data from a previous installation:"
>
> | Component | Status | Details |
> |-----------|--------|---------|
> | Configuration | ✅ Found | local-context.md (last updated: [date]) |
> | Template Library | ✅ Found | [N] templates in [M] categories |
> | Knowledge Library | ✅ Found | [N] sources, avg trust: [score] |
> | Schema version | [version or "unknown"] | Current plugin: [current version] |
>
> "How would you like to proceed?"

Present options via AskUserQuestion:

- **Use existing data** — keep everything as is, validate and update schema if needed
- **Use existing data + reconfigure** — keep data but re-run configuration to update/add sections
- **Start fresh** — archive existing data to `~/.grow-pm/backups/` and run full Onboarding
- **View existing config first** — show current configuration before deciding

### Step M-3. Schema compatibility check

If user chose to keep existing data, verify compatibility:

**3a. Compare schema versions:**

| Scenario | Action |
|----------|--------|
| Same version | No migration needed, proceed normally |
| Newer plugin, minor version diff | Auto-migrate: add new optional fields with defaults |
| Newer plugin, major version diff | Guided migration: show what will change, ask for confirmation |
| Older plugin than data | Warn: "Your data was created by a newer plugin version. Some features may not work correctly." |
| No schema version | Legacy data: run full compatibility scan |

**3b. Auto-migration (minor version changes):**

1. Create backup in `~/.grow-pm/backups/pre-migration-[version]/`
2. Read current `local-context.md`
3. Add new fields introduced in the current version (with sensible defaults or empty)
4. Remove deprecated fields (if any)
5. Update `.schema-version`
6. Show migration changelog to user

**3c. Guided migration (major version changes):**

1. Create backup in `~/.grow-pm/backups/pre-migration-[version]/`
2. Read current data
3. Show a detailed comparison: "Here's what will change in the new version:"
4. For each breaking change — ask user to provide updated values
5. Apply changes
6. Update `.schema-version`
7. Show complete migration changelog
8. Run validation (Validate mode)

### Step M-4. Validate migrated data

After migration:
1. Run Plugin Configurator in Validate mode
2. Check all MCP connections still work
3. Check all referenced resources (Jira projects, Confluence spaces) are accessible
4. Report any issues

---

## Legacy Data Discovery

For users upgrading from pre-v1.4.0 (where data was stored in workspace/outputs):

### L-1. Search for legacy data

During first plugin launch, after checking `~/.grow-pm/`, also search legacy locations:
1. User's workspace/outputs folder
2. Plugin root directory
3. Session working directory

### L-2. If legacy data found

Inform the user:

> "I found plugin data from an older version in your workspace folder. Would you like to migrate it to the persistent storage (~/.grow-pm/) so it's preserved across plugin reinstalls?"

Options:
- **Yes, migrate** — copy data to `~/.grow-pm/`, run schema migration, validate
- **No, start fresh** — ignore legacy data, run Onboarding with fresh `~/.grow-pm/`
- **Let me review first** — show the found data before deciding

### L-3. Migration from legacy location

1. Copy all found files to `~/.grow-pm/` (preserving structure):
   - `local-context.md` → `~/.grow-pm/local-context.md`
   - `knowledge-library/` → `~/.grow-pm/knowledge-library/`
   - `template-library/` → `~/.grow-pm/template-library/` (if exists)
2. Create `.schema-version` with the version that best matches the data format
3. Run schema migration if needed (Step M-3)
4. Validate (Step M-4)
5. Inform user: "Data migrated successfully. Your configuration is now stored in ~/.grow-pm/ and will persist across plugin reinstalls."

---

## Backup Protocol

### Automatic backups

Backups are created automatically:
- Before any schema migration (Step M-3)
- Before major configuration changes (full Onboarding re-run)

### Backup structure

```
~/.grow-pm/backups/pre-migration-[version]/
├── local-context.md
├── .schema-version
├── knowledge-library/     (if exists)
│   ├── library.md
│   ├── trust-scores.yaml
│   └── ...
└── template-library/      (if exists)
    ├── _registry.json
    └── ...
```

### Backup cleanup

Keep the last 3 backups. When creating a new backup and there are already 3 — delete the oldest one.

---

## Symlink to Workspace (optional)

After saving data to `~/.grow-pm/`, the plugin can optionally create a **symlink** in the workspace folder for easy access:

```
workspace/.grow-pm-data → ~/.grow-pm/
```

This is offered during Onboarding:
> "Would you like a shortcut to your plugin data in the workspace folder? This makes it easy to view and edit configuration files directly."

This is purely for convenience and is not required for plugin operation.

---

## Deletion Behavior

When the plugin is uninstalled:
- **`~/.grow-pm/` is NOT deleted** — user data persists
- Only plugin code/skills are removed
- On next install, migration protocol detects and reuses existing data

If the user explicitly wants to delete all data:
> "To completely remove all Grow Product Manager data, delete the ~/.grow-pm/ directory."

---

## Security Considerations

- `local-context.md` contains organization-specific configuration (Jira URLs, project keys, team members) — it should not be shared publicly
- `~/.grow-pm/` should have user-only permissions (chmod 700 on Unix systems)
- Backups inherit the same permission model
- Skills should never log or expose the full path of `~/.grow-pm/` to external services
