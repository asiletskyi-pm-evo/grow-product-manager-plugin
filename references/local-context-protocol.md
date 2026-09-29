# Local Context Protocol

This document defines how every skill in the plugin reads and uses `local-context.md`. **All skills MUST follow this protocol at the start of execution.**

For persistent storage details, see **`references/persistent-storage.md`**.
For Vault integration details, see **`references/vault-protocol.md`**.

> **Where `references/…` lives.** A bare `references/<file>.md` in a skill is skill-local if the file exists in the skill's own `references/`, and otherwise means the **shared** folder at the plugin root (the two never share a file name — `testing/skill_lint.py` checks). Hosts that hand the skill only its own directory (Codex CLI does: it resolves the bare path against `skills/<name>/`, measured in the v3.0.0 pilot) will not find it there. Resolve the plugin root in the order `${PLUGIN_ROOT}` → `${CLAUDE_PLUGIN_ROOT}` → walk up from the skill folder to the directory that contains `skills/` (`references/host-profiles.md` §6), and read the protocol from `<plugin root>/references/`. Never continue without a protocol the skill named.

## Step 0 — Check and read local-context.md (MANDATORY)

Before any other action, the skill MUST:

### 0a. Search for local-context.md

**Shortcut (since v2.6.0):** if the session context contains a `GROW_PM_SESSION` digest (emitted by the plugin's SessionStart hook, `hooks/hooks.json`) that says `local-context.md: FOUND at <path>` — or the env variable `GROW_PM_CONTEXT_PATH` is set — take that path and skip the search below. The digest is a locator, not a substitute: still read the file and run 0c–0j. If the digest says `NOT VISIBLE`, it only means the hook's environment could not see the file (hosted sessions see the user's files through device tools, not the shell) — run the search below as usual and do **not** treat it as "not configured".

Search in the following locations (in priority order):

1. **`~/.grow-pm/local-context.md`** — persistent home directory (primary, survives plugin reinstalls)
2. Plugin root directory (relative: `../../local-context.md` from skill folder) — legacy location
3. User's workspace/outputs folder (the mounted folder or outputs directory) — legacy location
4. Session working directory — fallback

**If found in a legacy location (2-4) but NOT in `~/.grow-pm/`:** the file is from a pre-v1.4.0 install. Before proceeding, offer to migrate it to `~/.grow-pm/` (see `references/persistent-storage.md` → Legacy Data Discovery). If the user agrees — migrate, then continue. If the user declines — use it in-place but warn that data may be lost on plugin reinstall.

**When saving:** ALWAYS write to `~/.grow-pm/local-context.md`. Never save to legacy locations. (Exception: Step 0i writes the role lines into the file this step resolved, including a legacy location the user chose to keep.)

### 0b. If NOT found (anywhere) → redirect to Plugin Configurator

Stop the current skill workflow and inform the user:

> "To work effectively, the plugin needs to be configured with your organization, products, and tools context. Let's run a quick setup (~5-10 min)."

Launch the **Plugin Configurator** and let **its own mode selection on launch** decide what to do — do **not** name a mode from here. A missing `local-context.md` does not mean "nothing is configured": the knowledge library, person profiles, experiment registry or a vault mirror may all still be there, and the Configurator's rule 1 restores from them after taking an RM-0 backup. Forcing Onboarding from the caller starts fresh over live data — the exact destruction its rule ordering exists to prevent.

After the Configurator finishes — return to the original skill and continue its workflow with the resulting context.

### 0c. If found → read and parse

Read `local-context.md` and extract:
- Active user profile (name, role, role label, role scope, level home, email, language, jira_account_id) and the `## Judgment` section (`hypothesis_first`, `learning_mode`, `hats_allowed`; defaults `on` / `off` / `all` when the section is absent)
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

Each skill has specific required fields (see `skills/plugin-configurator/references/context-schema.md` → "Which Skills Read What"). If required fields are missing for the current skill:
- Inform the user which fields are missing
- Offer two options:
  1. Run **Plugin Configurator** in Update mode to add missing data
  2. Proceed without the missing context (skill will ask for this info manually during execution)

### 0f. Check for CJM configuration (CJM skills only)

**This step applies only to:** `cjm-research`, `product-analysis` (when invoked in CJM mode), `brainstorm-features` (when invoked in CJM mode).

Check if `local-context.md` contains a **CJM Configuration** section for the active product.

**If CJM Configuration is present:**
- Read funnel template type, stages, dashboards, thresholds, default settings
- Communicate the active template to the user: "Using **[template name]** template with [N] stages."
- Continue with the skill workflow.

**If CJM Configuration is missing**, present three options via `AskUserQuestion`:

1. **Run Plugin Configurator → Step 11 (CJM Configuration)** — full guided setup (~3-5 min). Saves a complete CJM config to `local-context.md` for permanent reuse.
2. **Quick CJM setup (Recommended)** — collect ad-hoc configuration for this analysis only, then offer to save it to `local-context.md` at the end before running the analysis. If the user accepts the save, this becomes equivalent to a full Configurator setup.
3. **Skip CJM mode** — run the skill in a non-CJM mode if one is available, or end gracefully.

**Quick CJM setup workflow:**

Collect only what's needed for the current analysis:

| Field | Notes |
|-------|-------|
| Funnel template (or custom stages) | Use the standard templates from `references/funnel-templates.md`, or let the user define custom stages inline |
| Dashboard URLs for stages | If the user pasted URLs in the original request, propose mapping them to stages |
| Baselines (optional) | If unknown — note "to be read from dashboards on first run" |
| Thresholds | Default to Warning 10%, Critical 25%; ask only if the user wants to customize |
| Comparison baseline | Previous period (default) / previous year / target / custom |
| Platforms | All configured (default) / specific |

**Before launching the analysis** — present the collected config and ask:

> "I've assembled a CJM configuration for this analysis. Save it to `local-context.md` so I don't have to ask next time?"

Options via `AskUserQuestion`:
- **Yes, save** — invoke Enrichment (see "Context Enrichment" below) and write a full CJM Configuration section to `local-context.md`. Show a changelog of what was added.
- **No, just for this session** — keep the config in session memory only; do not persist.
- **Save partially** — let the user pick which fields to keep (e.g., dashboards yes, thresholds session-only).

After the save decision, proceed with the analysis using the collected config (regardless of whether it was persisted).

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

### 0i. Role resolution (every skill, since v3.5.0)

The role layer is `references/role-profiles.md`: a role changes **defaults, never capabilities**, and a role field acts only through a step that implements it (the version in brackets in role-profiles §5).

1. **Read** `- **Role:**` (and `Role label`, `Role scope`, `Level home`) from the User Profile.
2. **Missing or not in the enum** — in an **interactive** run (the user is present in the chat), ask once:
   - a free-text role (legacy file): ONE question — the keyword-mapped role from role-profiles §5 (Recommended) · `other` (keep my wording, `pm` defaults); Role scope stays unset;
   - no role at all: the group and the role of the two-level picker (role-profiles §5 step 1; a group with a single role skips the role question) — scope is not asked here and stays unset (`set role` adds it) — or a numbered list on a host without structured questions (`host-profiles.md` §4).
   Ask only when the file can be written. Write the answer into the `local-context.md` that Step 0a resolved — the digest path, `GROW_PM_CONTEXT_PATH`, or a legacy location the user chose to keep (this overrides 0a's "always write to `~/.grow-pm/`" rule; never create a new file for the role) — with a one-row changelog (`Role | was | became`); never ask again. When the file cannot be written (a read-only upload, a connector document, a sandbox), do not ask: use the keyword-mapped role (free text) or `pm` for the session and print one notice line with the role lines to paste. If the user skips the question, use `pm` for this session, write nothing, and ask again in the next interactive session.
   Never ask in an **automated** run — a scheduled or headless run (`headless=true`, a scheduled-task prompt) or a skill invoked by another skill only for a return payload: use `pm` for that run and write nothing.
   **`plugin-configurator` never asks here:** its own Step 4a, `set role` and RM-4d migration own the role question; Validate only reports a missing or free-text Role as a recommendation and never asks.
3. **Resolve** `role_defaults` from role-profiles §2 and §2b. Active in v3.5.0: `level_home`, `reach`, `quick_wins`, and `hat` for the header; the other fields are carried for the steps that start using them in v3.6.0. Branch only on active fields, never on `role_defaults.role` or `hat` values.
4. **Hat** — when the user asks for their own output to be viewed as another role ("as a CPO, …", «як аналітик, …»; "wear the … hat" also works, less reliably for routing) and `hats_allowed` accepts that role: state `Hat: <role> (profile: <role>)` at the top of the draft as presented in the chat — never inside slides, Jira fields or a published page body; in v3.5.0 that header is the hat's only effect (`level_home`, `reach`, `quick_wins` stay the profile's) (template and emphasis follow from v3.6.0). The profile is not rewritten. A role word describing another person (a People-contour request such as "goals for Person1 as an analyst") is never a hat, nor is a persona or test-account role walked in the product («пройди флоу як власник магазину», "as a seller / buyer / new user"). If `hats_allowed` excludes the role, say so in one line and continue without it.
5. **Altitude** — infer the altitude of this run's artifact (L1–L4) from the request and the artifact, not from the role; `level_home` is only the fallback when the request implies none. The altitude line shows that value and nothing more — a jump outside the reach needs no extra notation.
6. **One line, once per session, in an interactive run**, only when no `GROW_PM_SESSION` digest is in context at all (hosts without the SessionStart hook): `Role: <role>[ (hat: <hat>)] · Altitude home: <Lx>`. Not in automated runs, not in a skill invoked only for a return payload. No other output.

### 0j. Judgment contract (every skill)

Every skill carries a three-line block that points here; its first line is always `> **Judgment contract (Step 0j).**`. The contract itself is `references/pm-mental-model.md`: the plugin **creates freely and decides carefully**.

1. Before the first real step, read `pm-mental-model.md` §0 and §2 and note — internally, with no output — this run's **judgment points**: where the run scores, ranks, gives a verdict, sets a priority, recommends ship/kill or frames a debate question. Drafting, searching, clustering and prototyping are creation steps: they get no added friction, and their existing questions stay.
2. **A principle acts only through a step that implements it.** At a judgment point, use only what the skill's own steps, and the shared protocols those steps already call, contain (for example, where a skill already has them: sources and period annotations, the Data Integrity Gate, the decision rule, a Skeptic in debates). Do not improvise anything those steps do not contain — a question, a section, a check, a footer, a confidence line, an evidence label, a record field, a hand-back proposal or any other output. Each principle's *Binds* list in `pm-mental-model.md` is the map of where it is or will be implemented, with the version in brackets; it is not an instruction. Until an implementing step exists, every question, gate and output of the skill stays exactly as it is, in every kind of run.
3. **Questions that later versions add at judgment points** (the Principle 2 "your estimate first" question, from v3.7.0) will be switchable in the `## Judgment` section of `local-context.md` and never asked in a run with no user present — a scheduled health-check, a headless brief, a skill invoked only for a return payload. This rule does not touch any question a skill already asks.

> Why a sub-step of Step 0 and not "Step 0.5": Step 0.5 is the Vault Context Search below. The specification that introduced the contract called it "Step 0.5-J".

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
- **Task Creator** → Jira team IDs, member accountIds discovered from existing tasks
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
- Use `product.competitors` when building comparison matrices (always include user's product); since v3.3.0 prefer the landscape registry links (`{storage_root}/landscape/registry.yaml`, roles direct-competitor / benchmark) when the registry exists — `product.competitors` is the seed it imported
- Use `product.key_metrics` when discussing metrics (pre-fill known metrics)
- Use `product.current_okrs` to align hypotheses and analysis with strategic goals
- Use `organization.tableau_base_url` and `product.ab_test_dashboards` for analytics access
- Use `user.language` for output language preference
- Use `user.jira_account_id` for setting Reporter on Jira tasks
- Use `role_defaults` (Step 0i) — never the role name — for defaults: the altitude inferred at Step 0i step 5 for the altitude line (`level_home` only as its fallback) and `quick_wins` in onboarding (v3.5.0); `template_defaults`, `gate_emphasis`, `planning_view`, `horizon`, `vocabulary_set` from v3.6.0 (`references/role-profiles.md` §5–§6)
- Use `judgment.hypothesis_first`, `judgment.learning_mode`, `judgment.hats_allowed` only through the steps that implement them (hats from v3.5.0; the others from v3.7.0 / v3.9.0)
- Use `team.jira_team_id` for setting Team field on Jira tasks
- Use `cjm.stages` for CJM funnel analysis (name + dashboard + `baseline_cr` per stage)
- Use `cjm.thresholds` for anomaly detection (`warning` / `critical`, % deviation from baseline)
- Use `cjm.analysis_defaults.search_modes` for Knowledge Library search during CJM enrichment
- Use `knowledge_library.confluence_spaces` for Confluence CJM search
- Use `knowledge_library.gdrive_folders` for Google Drive CJM search

> Key names are the ones in `local-context.example.md` (the canonical spelling). Until v2.1.1 this list read `product.cjm_configuration.funnel_stages`, `.anomaly_thresholds`, `configured_confluence_spaces` and `configured_gdrive_folders` — a per-product path and four key names that exist in no example and no schema, so every skill following this list read nothing.
- Use vault context (from Step 0.5) to enrich analysis with historical data and prior decisions
