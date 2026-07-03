---
name: plugin-configurator
version: 2.5.0
description: Configure the Grow Product Manager plugin for your organization, products, teams, and data sources. Use when the user asks to "configure plugin", "set up plugin", "set up context", "add a product", "update configuration", "validate setup", "show config", or when any other skill detects that local-context.md does not exist. Українською: "налаштувати плагін", "сетап плагіна", "налаштувати контекст", "додати продукт", "оновити конфігурацію", "перевірити налаштування", "показати конфіг".
---

# Plugin Configurator

Configure the Grow Product Manager plugin for your organization. This skill collects all necessary context — products, teams, data sources, analytics tools, OKRs, repositories — and generates a `local-context.md` file that all other skills use as their primary context source.

Supports multiple organizations, products, and projects simultaneously.

**Structure of this skill:** this file holds the mode map, entry conditions, and cross-skill protocols. The detailed step-by-step workflows live in skill-local references and are loaded on demand:

| Reference | Contains |
|-----------|----------|
| `references/onboarding-steps.md` (skill-local) | Onboarding Steps 1–17 in full detail + Planning setup + Focus setup (Extended add-ons) |
| `references/maintenance-modes.md` (skill-local) | Reinstall/Migration (RM-0..RM-6), Update (U-1..U-4), Validate (V-1..V-6), View (VW-1..VW-4), Versioning Protocol |
| `references/test-mode.md` (root) | Test sandbox procedure (TM-0..TM-5) |

**Load only the reference for the mode you are entering** — never all at once.

## Six Modes

| Mode | When to use | What it does | Workflow |
|------|------------|--------------|----------|
| **Onboarding (Basic)** | First launch, `local-context.md` doesn't exist anywhere; user picks Basic in Step 2 | Minimal guided setup: user profile → organizations → core product fields → connector pre-check → review → save. Other sections (CJM, Vault, Knowledge Library, Templates, Teams, etc.) are deferred — saved in `onboarding.deferred_steps` and can be added later. ~3-5 min. | `references/onboarding-steps.md` |
| **Onboarding (Extended)** | First launch, user picks Extended in Step 2 | Full guided setup: every section configured (CJM, Knowledge Library, Templates, Obsidian Vault, Teams, Repos, full Tableau analytics, Planning suite, Focus). ~15-25 min. | `references/onboarding-steps.md` |
| **Onboarding (Test sandbox)** | User invokes `dry-run onboarding` / picks Test in Step 2 | Walks the user through onboarding with all writes redirected to `~/.grow-pm-sandbox/`. Real data is untouched. Ends with a diff vs. real config and Discard / Promote / Keep menu. | root `references/test-mode.md` |
| **Reinstall / Migration** | Plugin reinstalled, `~/.grow-pm/` contains existing data | Detect existing data, show to user, ask: use as-is / reconfigure / start fresh. Migrate schema if needed. Includes Vault Recovery fallback | `references/maintenance-modes.md` → RM |
| **Update** | `local-context.md` exists, user wants to change something | Edit a specific section: add product, update team, change dashboard URLs, add OKRs, manage Obsidian Vaults, Planning/Focus sections, etc. Always shows changelog | `references/maintenance-modes.md` → U |
| **Validate** | User wants to check everything works | Test all MCP connections, verify data access, check context completeness, validate Obsidian Vault connectivity, produce readiness report | `references/maintenance-modes.md` → V |
| **View** | User asks to see current config | Display current `local-context.md` contents in a readable format, allow inline edits via dialogue | `references/maintenance-modes.md` → VW |

**Mode selection on launch:** if `local-context.md` does not exist anywhere → Onboarding. If `~/.grow-pm/` has data but the launch looks like a fresh install → Reinstall/Migration (run RM-0 backup FIRST). Otherwise route by the user's request: change something → Update; check → Validate; show → View; "dry-run onboarding" → Test.

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

## Workflow entry points

- **Test Mode (sandbox):** follow root `references/test-mode.md` — full sandbox procedure (TM-0..TM-5, isolation, finale diff, Discard/Promote/Keep, verification matrix). Triggers: "dry-run onboarding", "test mode", "тестовий режим".
- **Onboarding:** read `references/onboarding-steps.md` (skill-local) and execute Steps 1–17 in order, respecting the Basic/Extended mode gates on every step. Extended add-ons: Planning setup and Focus setup (same file, after Step 14). Single sections can be run standalone: `add CJM` → Step 11, `connect Obsidian` → Step 14, `set up templates` → Step 13, `add Planning` / `add Focus` → the corresponding add-on step.
- **Reinstall / Migration:** read `references/maintenance-modes.md` → RM-0..RM-6. **RM-0 (pre-update backup) runs before ANY other operation.**
- **Update:** read `references/maintenance-modes.md` → U-1..U-4. Mandatory changelog after every save.
- **Validate:** read `references/maintenance-modes.md` → V-1..V-6. Produces the readiness report.
- **View:** read `references/maintenance-modes.md` → VW-1..VW-4.

---

## Changelog Protocol (applies to ALL modes that modify local-context.md)

Every time `local-context.md` is modified — whether by Onboarding (Step 16), Update, View, or Enrichment from other skills — the user MUST receive a changelog report showing:

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
- **Task Creator** → can discover and add team member Jira accountIds
- **Requirements Creator** → can discover and add Confluence template URL
- **CJM Research** → can update baseline conversions from dashboard data

When a skill discovers new context:
1. Inform the user: "I found new information that can be added to the context: [what was found]"
2. Ask: "Would you like to update local-context.md?"
3. If yes — read current file, add new data to the appropriate section, save
4. **Show changelog** (same format as Update Mode U-4): what was added, previous state → new state

---

## Versioning Protocol

Full protocol (skill/plugin version rules, required steps when modifying a skill): `references/maintenance-modes.md` → Versioning Protocol. Summary: PATCH = wording, MINOR = new step/section, MAJOR = restructure/breaking; plugin version reflects the highest-impact skill change; every modification requires frontmatter bump + plugin.json bump + CHANGELOG entry + re-package.

---

## Quality Standards

- Never overwrite user-provided data without confirmation
- Always show what was discovered vs. what the user needs to provide manually
- Pre-fill fields from auto-discovery, but always confirm with the user
- Preserve custom sections during updates
- Use Ukrainian or English based on user's language preference (ask in Step 4 if Onboarding, read from context if Update/Validate)
- When communicating CJM template selection — always name the template and list the stages
- Load mode references on demand only — this file plus one mode reference is the working set

## Additional Resources

**Skill-local (this skill's `references/`):**
- **`onboarding-steps.md`** — Onboarding Steps 1–17 + Planning/Focus setup (Extended add-ons)
- **`maintenance-modes.md`** — RM / Update / Validate / View workflows + Versioning Protocol
- **`context-schema.md`** — complete schema definition with field descriptions, required/optional status, and which skills use each field
- **`obsidian-setup-guide.md`** — step-by-step Vault setup with per-substep validation (P-1..S-9)

**Root `references/`:**
- **`persistent-storage.md`** — persistent storage protocol (`~/.grow-pm/`), migration, backup, legacy data handling
- **`local-context-protocol.md`** — how all skills read and use `local-context.md`
- **`integration-strategy.md`** — MCP → Registry → Browser fallback chain (shared across all skills)
- **`self-improvement.md`** — self-improvement protocol
- **`cjm-protocol.md`** — CJM anomaly severity, funnel impact formulas, health score
- **`funnel-templates.md`** — standard funnel stage templates by product type
- **`vault-protocol.md`** — Obsidian Vault initialization, folder structure, artifact management
- **`vault-schema.md`** — Vault schema definition, template formats, metadata storage
- **`template-protocol.md`** — template resolution protocol used by Step 13 and consumer skills
- **`test-mode.md`** — sandbox onboarding procedure

**Other skills:**
- **`skills/template-library/SKILL.md`** — CRUD actions and wizards for the Template Library
