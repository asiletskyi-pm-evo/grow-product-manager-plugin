# Obsidian Vault Setup — Step-by-Step Guide

> Used by:
> - **Plugin Configurator → Onboarding Mode → Step 7** (Obsidian Vault)
> - **Plugin Configurator → Update Mode → Obsidian Vault Management → Connect Vault**
>
> This guide is the canonical procedure for connecting an Obsidian Vault. Both onboarding and update flows are thin wrappers over this guide so the experience stays consistent.

This guide walks the user through connecting an Obsidian Vault, validating each prerequisite at every step. The user receives an explicit ✅/⚠️/❌ at each substep so they always know what passed, what failed, and how to recover.

---

## Pre-flight check

### P-1. Does the user have Obsidian installed?

Ask via AskUserQuestion:

- **Yes — vault folder ready** → proceed to S-1
- **Yes — but no vault yet** → proceed to P-2
- **No, I haven't installed Obsidian** → show install instructions (link to https://obsidian.md), exit step. Mark `obsidian-vault` in `onboarding.deferred_steps`. Inform: "You can connect a Vault later via `configure plugin → connect Obsidian`."
- **What is Obsidian?** → 2-sentence explanation, then re-ask:
  > "Obsidian is a local-first markdown knowledge base. The plugin can mirror your concepts, requirements, research, CJM reports, and decisions into a Vault so they accumulate over time and stay searchable across sessions."

### P-2. Create vault (user-side)

Show instructions:

> "Open Obsidian → Create new vault → choose folder location → confirm creation."

**Do not validate yet** — user will paste the path in S-1, where validation runs.

Wait for the user to confirm "done" via AskUserQuestion:
- **Done — vault created** → proceed to S-1
- **Cancel — set up later** → exit step, mark `obsidian-vault` deferred

### P-3. Pre-flight summary

> "Great. Now I'll ask for the exact path to your vault folder and we'll connect step by step. I'll validate each step and tell you what passed before moving on."

---

## Setup steps with validation

### S-1. Vault path

**Ask:**

> "Paste the absolute path to your vault folder. This is the folder that contains the `.obsidian/` subfolder."

**Validate (in order):**

1. **Path is absolute** — must start with `/` (Unix/macOS) or a drive letter (Windows). If not → ❌ "Path must be absolute. Got: `[path]`. Example: `/Users/yourname/Documents/MyVault`."
2. **Directory exists** — run `test -d "{path}"`. If false → ❌ "Folder not found at `{path}`. Check the path or create the vault in Obsidian first."
3. **`.obsidian/` subfolder exists** — run `test -d "{path}/.obsidian"`. If false → ⚠️ "This folder doesn't look like an Obsidian Vault — `.obsidian/` is missing. This is OK if you just created an empty folder for the vault, but Obsidian usually creates `.obsidian/` automatically when you open the folder as a vault. Continue anyway?"
   - If user says yes → proceed
   - If user says no → ask for a different path

**On success:** ✅ "Vault path validated: `{path}`."

**Save in session:** `session.vault.path = {path}`

### S-2. Plugin folder name

**Ask:**

> "What name should the plugin's folder use inside the vault? (default: `GrowPM`)"

**Validate:**

1. **Pattern** — regex `^[A-Za-z0-9][A-Za-z0-9_-]*$`. If invalid → ❌ "Allowed characters: letters, digits, `-` and `_`. Must start with a letter or digit. Got: `[name]`."

**On success:** ✅ "Folder name accepted: `{folder_name}`."

**Save in session:** `session.vault.folder_name = {folder_name}`

### S-3. Write/read permission test

**Goal:** Confirm that the plugin can actually create files inside the vault before promising to mirror artifacts there.

**Steps:**

1. Run `mkdir -p "{vault_path}/{folder_name}"` — create the plugin folder if missing.
2. Run `echo "test" > "{vault_path}/{folder_name}/.write-test"` — write a tiny test file.
3. Run `cat "{vault_path}/{folder_name}/.write-test"` — read it back. Verify content equals `test`.
4. Run `rm "{vault_path}/{folder_name}/.write-test"` — clean up.

**Validate:**

- If any of the above fails → ❌ "Cannot write to `{vault_path}/{folder_name}`. macOS may need to grant access to Documents/Folders — check **System Settings → Privacy & Security → Files and Folders** and allow your terminal/Claude app to access this folder."
- Show the exact error message from the failing command so the user can debug.

**On success:** ✅ "Write/read test passed. Plugin can mirror files into the vault."

### S-4. Products binding

**Decide based on `local-context.md` → number of products:**

- **1 product** → auto-bind to `all`. Inform: "Vault will store artifacts for `[product name]`."
- **Multiple products** → ask via AskUserQuestion:
  - **All products** — vault handles every product
  - **Specific products** — show multi-select with all configured products

**Save in session:** `session.vault.products = "all"` or `session.vault.products = [list of product IDs]`.

### S-5. Sync mode

**Ask via AskUserQuestion:**

- **Auto (Recommended)** — save artifacts automatically after each skill produces output
- **Manual** — ask before every save
- **Read-only** — only search the vault for context, never write

**Save in session:** `session.vault.sync_mode = {auto|manual|read-only}`.

### S-6. Optional: Obsidian MCP detection

**Goal:** Detect whether the user has the Obsidian MCP installed in Claude Desktop. If yes, the vault upgrades from L1 (filesystem-only) to L2 (filesystem + MCP) and search performance improves significantly.

**Steps:**

1. Try a tiny ping against any tool whose name matches `mcp__*__*obsidian*` or known Obsidian MCP tool patterns.
2. If the call returns successfully:
   - Mark `vault_level = L2`.
   - Inform: "✅ Obsidian MCP detected. The plugin will use it for cross-vault search."
3. If no MCP responds:
   - Mark `vault_level = L1`.
   - Inform: "ℹ️ Obsidian MCP isn't installed — that's fine. The plugin will use the filesystem for search. You can add Obsidian MCP later via `search_mcp_registry` and reconnect with no setup loss."

**This step never blocks.** L1 is fully functional.

### S-7. Folder initialization

**Trigger:** call the Vault Initialization algorithm in `references/vault-protocol.md` → "Vault Initialization" with the parameters collected above.

**Show progress with ✅/❌ per substep:**

- ✅ Created folder structure (`{plugin_folder}/_System/`, `{plugin_folder}/Templates/`, etc.)
- ✅ Created N templates (count from vault-protocol)
- ✅ Created Dashboard MOC at `{plugin_folder}/Dashboard.md`
- ✅ Copied `local-context.md` to `{plugin_folder}/_System/local-context.md`
- ✅ Migrated knowledge-library files (X files moved) — only if `~/.grow-pm/knowledge-library/` exists
- ✅ Created `.vault-schema-version` file

**On any ❌:** show the specific gap, propose recovery:
- "Retry initialization" — re-run the failing substep only
- "Skip and continue" — accept partial state; the plugin will create missing pieces lazily on first use
- "Abort vault setup" — roll back, mark `obsidian-vault` deferred

### S-8. Smoke test (read-back validation)

**Verify what was just created:**

1. `test -f "{vault_path}/{folder_name}/Dashboard.md"` → ✅ MOC present
2. `test -f "{vault_path}/{folder_name}/_System/local-context.md"` → ✅ Context mirrored
3. `test -f "{vault_path}/{folder_name}/.vault-schema-version"` → ✅ Schema version stamped
4. `test -d "{vault_path}/{folder_name}/Templates"` → ✅ Templates folder exists
5. If Templates were initialized in this onboarding (Step 8 ran) → `test -f "{vault_path}/{folder_name}/Templates/_registry.json"` → ✅ Registry present

**On all ✅:** "Vault is ready."

**On any ❌:** show which check failed, offer to re-run S-7 or skip with a warning logged.

### S-9. Save to local-context.md

1. Add or update the `## Obsidian Vaults` section in `~/.grow-pm/local-context.md` per the schema in `references/context-schema.md` and the format in `Onboarding Step 13` of `SKILL.md`.
2. If `vault.sync_mode` is `auto` or `manual` — execute the Vault Mirror Protocol (VM-1..VM-3 from `references/persistent-storage.md`) to copy `local-context.md` and `.schema-version` into `{vault_path}/{folder_name}/_System/`.
3. Update the `Updated:` timestamp at the top of `local-context.md`.
4. Show the user a summary card:
   > "Vault connected.
   > Path: `{vault_path}/{folder_name}/`
   > Sync mode: `{auto|manual|read-only}`
   > Vault level: `{L1|L2}`
   > Initialized: `{N}` folders, `{M}` templates, Dashboard MOC, schema version `{X.Y.Z}`."

---

## Common errors and recovery

| Error | What to show the user |
|-------|----------------------|
| Path doesn't exist | "Folder not found at `[path]`. Either fix the path or create a new vault in Obsidian (File → New vault)." |
| No `.obsidian/` subfolder | "Doesn't look like an Obsidian vault. If you just created the folder, open it in Obsidian once so `.obsidian/` is initialized. Or continue anyway if you're sure." |
| Permission denied on write | "macOS may be blocking access. Open System Settings → Privacy & Security → Files and Folders and grant your terminal / Claude app access to this folder. Then retry." |
| MCP ping failed | "Obsidian MCP didn't respond — that's fine, the vault works at L1 (filesystem). You can add Obsidian MCP later for faster cross-vault search." |
| Folder structure incomplete after init | "Created `{X}/{N}` expected folders. You can retry initialization, or accept the partial state — missing pieces will be created on first save. The plugin will not lose data either way." |
| Smoke test fails after retry | "Initialization keeps failing. The most common cause is permissions. Skip vault setup for now (`obsidian-vault` will be deferred) and try again later via `configure plugin → connect Obsidian`. No data has been written outside the vault folder." |

---

## Notes for Configurator authors

- This guide is shared by **Onboarding** and **Update → Vault Management → Connect Vault**. Both code paths must execute P-1..S-9 identically; the only difference is whether the result writes a new `## Obsidian Vaults` section (Onboarding) or appends/updates an existing one (Update).
- During **Test mode** (sandbox), all paths in S-3 and S-7 must point inside `~/.grow-pm-sandbox/` instead of touching the real vault. The user's real Obsidian vault is **never** modified by Test mode — Vault Mirror Protocol is fully skipped during sandbox runs.
- If `onboarding.mode == basic`, this guide is **not invoked** during onboarding. Instead, mark `obsidian-vault` in `onboarding.deferred_steps` and offer the user a Quick Win nudge after save.
