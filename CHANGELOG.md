# Changelog — Grow Product Manager Plugin

All notable changes to this plugin are documented here.

Version format: `MAJOR.MINOR.PATCH`
- **MAJOR** — breaking changes, full workflow restructure across multiple skills
- **MINOR** — new skill added, new step/section in existing skill, significant workflow addition
- **PATCH** — wording fix, small content addition, formatting change, bug fix in skill logic

Each skill also carries its own version in the frontmatter (`version:` field in SKILL.md).
When a skill changes, its version is bumped independently. The plugin version is bumped to reflect the highest-impact change among all updated skills.

---

## v1.11.0 (2026-04-20)

### Changed — Brand-Agnostic Refactor (public-repo hygiene)

**Problem:** The public plugin repo accidentally shipped hardcoded brand data for a specific organization (brand hex, brand fonts, DS file key, organization name, paths to a themed pptx template, Jira/Confluence keys) inside `design-integration/` and the `design-bridge` skill. Third-party users installing the plugin would inherit another organization's brand. Ukrainian-language template bodies also shipped publicly even though the repo README is in English.

**Solution:** Pulled all brand-specific and organization-specific values out of the plugin and moved them behind the existing `local-context.md` contract (gitignored, user-owned). Design-bridge now reads brand tokens, DS spec path, pptx theme path, base pptx path, and Figma file key from `product.*` fields in local-context, with neutral placeholder defaults when the user has not configured a DS. Every built-in template and reference has been translated to English; localize via `<!-- lang:xx -->` blocks.

#### Files removed

- **`design-integration/`** (entire folder, 6 files + an org-specific base pptx) — contained organization-specific DS spec, pptx theme, and a base pptx template. Per-organization equivalents now live in the user's workspace folder and are referenced from `local-context.md` under the new Design System section.

#### Files changed — `skills/design-bridge/`

- **SKILL.md** `0.1.0 → 0.2.0` — minor. Removed all hardcoded references to the organization's brand. Now reads `product.design_system_spec`, `product.pptx_theme`, `product.base_pptx`, `product.brand.primary`, `product.brand.dark`, `product.brand.font_primary`, `product.brand.font_display`, and `product.figma.ds_file_key` from local-context. End-to-end example genericized.
- **references/deck-subtypes.yaml** — removed `uk` language keys (kept `en` only); `referenced_theme` now points to `<product.pptx_theme from local-context.md>`.
- **references/figma-playbook.md** — removed organization name and hardcoded file key references; documents the generic brand DS configuration schema.
- **references/a11y-checklist.md** — replaced organization-specific contrast pairs with a schema and instruction to pre-compute pairs under `contrast_pairs:` in the user's DS yaml.

#### Files changed — templates and other skills

- **`templates/built-in/`** — 12 seed templates translated to English. Multilingual format preserved via `<!-- lang:xx -->` blocks; users can add additional language blocks in their own copies via Template Library.
- **Skill files and references** — all workflow instructions and inline examples translated to English; user-facing output language is still controlled by `user.language` in local-context.

#### Files changed — marketplace & plugin metadata

- **`.claude-plugin/plugin.json`** — description reworded from the old brand-specific phrasing to "brand-themed decks… (bring your own Design System via local-context.md)".
- **`.claude-plugin/marketplace.json`** — same description change.
- **`local-context.example.md`** — new **Design System** section per product with placeholder schema for brand tokens, DS spec path (yaml), pptx theme path (yaml), base pptx path, Figma file key, and an optional `contrast_pairs` block. `Language:` default flipped to `en`.

#### Skills changed

| Skill | From | To | Change type |
|-------|------|----|-------------|
| design-bridge | 0.1.0 | 0.2.0 | minor — brand-agnostic refactor; reads all brand fields from local-context |

#### Migration notes

Existing users upgrading from v1.10.0:
1. Run `plugin-configurator` to populate the new Design System fields in your `local-context.md` (see `local-context.example.md`).
2. If you relied on a shipped base pptx / DS spec / pptx theme, move those assets into your own workspace folder (e.g., `design-assets/`) and point `product.base_pptx` / `product.design_system_spec` / `product.pptx_theme` at them.
3. If any of your product-specific templates used `<!-- lang:uk -->` blocks, they remain valid in your local Template Library; only the built-in seed templates were translated to English.

---

## v1.10.0 (2026-04-20)

### Added — Design Bridge Integration

> Note (superseded by v1.11.0): organization-specific values originally captured here were moved out of the repo. The description below has been sanitized accordingly.

**Problem:** Claude's Design plugin ships 7 strong skills (user-research, research-synthesis, ux-copy, accessibility-review, design-system, design-critique, design-handoff) but they don't automatically know the brand tokens of the team using them, don't hook into the PM pipeline (concept → requirements → research → brainstorm), and don't produce brand-themed presentations. PMs had to hand-assemble decks in Google Slides and manually copy brand colors/fonts.

**Solution:** Introduced `design-bridge` — an orchestrator skill that acts as the single entry point for design deliverables (deck, prototype, handoff, research-enrichment), owns the active brand's Design System (DS) theme via local-context, and is invoked as an **optional Step D hook** from four upstream skills. Presentations render from a base pptx template (16:9, layouts pulled from the theme yaml) so output matches what stakeholders expect in their shared drive.

#### Core architecture — 3 layers

1. **Narrative** (from upstream skill: concept body, requirements, research themes, hypotheses)
2. **Template** (from Template Library: deck outline with Handlebars variables, multilingual)
3. **DS theme** (from the user-provided pptx theme yaml: colors, fonts, layouts, chart palette) — applied to the user-provided base pptx via `slide_layouts.get_by_name`

Each layer is independently versioned and swappable. Narrative changes don't invalidate the DS; DS updates don't rewrite templates.

#### Files added — skills/design-bridge/

- **SKILL.md** (`v0.1.0`) — orchestrator with 4 intents (deck, prototype, handoff, research-enrichment), Integration prerequisite, Local context prerequisite, Step T, 9-step workflow with 7 design-skill hooks (research-synthesis, ux-copy, design-critique, design-system, accessibility-review, design-handoff, Figma), pptx rendering via the user's base pptx + `slide_layouts.get_by_name`, WCAG 2.1 AA QA gate, publish, vault save, end-to-end example
- **references/deck-subtypes.yaml** — 4 deck subtypes with slide-by-slide outlines: feature-concept (10), research-highlights (10), ab-test-readout (6), release-readout (7)
- **references/figma-playbook.md** — Auth/permissions (View vs Full seat, rate limits), how to find fileKey + nodeId, common patterns (sync tokens, embed screenshot, concept→prototype, handoff), policy, brand DS configuration schema
- **references/a11y-checklist.md** — WCAG 2.1 AA checklist with schema for pre-computed contrast pairs, touch targets (44×44), keyboard nav, screen reader, motion, forms, deck-specific checks, QA output YAML schema

#### Templates added — templates/built-in/presentation/

- **research-highlights-v1.md** — 10 slides (cover / exec summary / method & sample / theme 1 / quote 1 / theme 2 / quote 2 / theme 3 / quantitative findings / recommendations). English; localize via `<!-- lang:xx -->` blocks.
- **ab-test-readout-v1.md** — 6 slides (cover / hypothesis & setup / primary metric / guardrails / interpretation / decision). English.
- **release-readout-v1.md** — 7 slides (cover / scope / key metrics / wins & learnings / incidents / what's next / ask). English.

#### Skill integrations — Step D hook

Four upstream skills gained an optional `## Step D — Design Bridge handoff (Optional)` step that offers to hand results to design-bridge:

| Skill | From | To | Offers (intent / subtype) |
|-------|------|----|---------------------------|
| write-concept | 0.6.0 | 0.7.0 | deck / feature-concept OR prototype (lo-fi / mid-fi) |
| requirements-creator | 0.6.0 | 0.7.0 | handoff (a11y_audit=true) OR prototype (hi-fi) OR deck |
| brainstorm-features | 0.6.0 | 0.7.0 | prototype (lo-fi) for top-1 hypothesis OR deck (8-slide brainstorm readout) |
| product-research | 0.6.0 | 0.7.0 | deck / research-highlights OR research-enrichment (Figma screenshots, competitor UI) |

Step D is always skippable — user can say "no thanks" and the skill finishes as before.

### Skills changed

| Skill | From | To | Change type |
|-------|------|----|-------------|
| design-bridge (new) | — | 0.1.0 | new — orchestrator for 4 design intents with 7 design-skill hooks |
| write-concept | 0.6.0 | 0.7.0 | minor — Step D hook after vault save |
| requirements-creator | 0.6.0 | 0.7.0 | minor — Step D hook (offers a11y handoff for Create mode) |
| brainstorm-features | 0.6.0 | 0.7.0 | minor — Step D hook (top-1 hypothesis prototype or brainstorm readout deck) |
| product-research | 0.6.0 | 0.7.0 | minor — Step D hook (research-highlights deck or research-enrichment) |

### Documentation

- README.md — version bumped to 1.10.0; new Design Bridge section added; 3 new templates listed under built-in; Figma and base-pptx workflow mentioned under Integration Points.
- CHANGELOG.md — this entry.
- plugin.json + marketplace.json descriptions updated to mention design-bridge capability.

### Backup

Before v1.10.0 writes, backups were taken of the plugin, local-context, and template library (preserved in session backup directory).

---

## v1.9.0 (2026-04-17)

### Added — Multilingual Artifact Template System

**Problem:** Every concept, spec, research report, and MoM was starting from a blank page. No reuse of proven document structures across products. Users in different language markets needed the same artifact in multiple languages without duplicating files.

**Solution:** Introduced a first-class template library with three-tier scope (built-in → user-global → product-specific), single-file multilingual storage (language blocks inside one template via `<!-- lang:xx -->` HTML comments), registry-backed resolution with scoring, skill-driven resolution with user opt-in, and three-tier backup protection.

#### Core architecture

- **Scope tiers:** built-in (ships with plugin) → user-global (shared across all products) → product-specific (per-product override), with inheritance and subtype matching.
- **Multilingual format:** single `.md` file contains all language variants as `<!-- lang:xx --> … <!-- /lang:xx -->` blocks. Obsidian-friendly, preserves link integrity, easy to diff.
- **Storage location:** `{storage_root}/Templates/` — lives in the Obsidian vault if configured (primary), or in the user's chosen custom folder. Survives plugin reinstalls.
- **Registry:** `Templates/_registry.json` indexes all templates with metadata (id, version, scope, artifact_type, subtype, languages, usage_count, checksum).
- **Resolution protocol (T-0 → T-5):** scoring by scope (+5/+3/+1), subtype match (+3/+1), language match (+2/+1), usage_count; tie-breakers by recency.
- **User preference:** `templates.preference` in local-context.md — `auto` (silent use of top match), `always_ask` (list candidates every time), `smart` (ask only when multiple strong candidates exist; default).
- **Three-tier backup:** per-template archive (last 10 versions per template), full pack backups (last 5 before bulk ops), and manual user-triggered backup/restore.

#### Files added

- **references/template-protocol.md** — resolution protocol (T-0 → T-5 with scoring), frontmatter schema, skill integration pattern, edge cases, registry schema, backup invariants.
- **skills/template-library/SKILL.md** (`v0.1.0`) — 11 actions (list / show / add / clone / update / delete / restore / import / export / validate / rebuild-registry), plus backup/restore; wizards for add, add-language, import, update; helper routines `resolve()` and `render()`.
- **templates/built-in/** — 9 seed templates shipped with the plugin:
  - `concept/default-v1.md` — concept (PRD) skeleton
  - `requirements/default-v1.md` — general feature requirements
  - `requirements/ab-test-v1.md` — A/B test spec
  - `research/competitive-v1.md` — competitive analysis + SWOT
  - `research/user-research-v1.md` — user research synthesis
  - `cjm/funnel-v1.md` — CJM funnel analysis with ICE table
  - `epic/default-v1.md` — Jira epic description
  - `task/default-v1.md` — Jira task with DoD and AC
  - `presentation/feature-v1.md` — 10-slide feature deck outline

#### Skill integrations

All consumer skills now include a `## Step T — Template Resolution` section that runs before the first workflow step. Each skill declares its `artifact_type` and subtype inference rules, honors the user's `templates.preference`, and falls back to a built-in structure if no template matches.

| Skill | From | To | Step T artifact_type / subtype |
|-------|------|----|------------------------------|
| write-concept | 0.5.0 | 0.6.0 | `concept` / `default` |
| requirements-creator | 0.5.1 | 0.6.0 | `requirements` / `default` \| `ab-test` \| `bugfix` (Create mode only) |
| product-research | 0.5.0 | 0.6.0 | `research` / `competitive` \| `user-research` \| `market` \| `ux-benchmark` |
| cjm-research | 0.2.0 | 0.3.0 | `cjm` / `funnel` (health-check uses silent auto) |
| feature-task-creator | 0.7.0 | 0.8.0 | `task` + `epic` (resolved once per subtype in batch mode) |
| brainstorm-features | 0.5.0 | 0.6.0 | `research` / `hypothesis-list` \| `cjm-hypotheses` (on save) |
| product-analysis | 0.6.0 | 0.7.0 | `research` / `metrics-analysis` \| `post-release` \| `ab-test-results` \| `cjm-funnel` (non-interactive modes) |
| diagram-prototyper | 0.7.0 | 0.8.0 | `presentation` / `feature` \| `research-highlights` \| `ab-test-readout` \| `release-readout` (decks only) |
| meeting-processor | 0.9.0 | 0.10.0 | `meeting-notes` / `grooming` \| `planning` \| `retro` \| `discovery` \| `status` \| `decision` \| `brainstorm` \| `review` (delegates to downstream skill's Step T when chaining) |

#### Onboarding

- **plugin-configurator** `0.10.0 → 1.0.0` — added **Step O-T — Template Library Setup** between Knowledge Library (Step 10) and Obsidian Vault (Step 11). O-T walks the user through: storage location (reuses Knowledge Library decision), copying built-in templates to their library, setting `templates.preference`, and scheduling a first-use template walkthrough.
- **knowledge-library** `0.3.0 → 0.4.0` — added routing section at top explaining when to use `knowledge-library` (external sources: articles, benchmarks) vs `template-library` (artifact skeletons). Added `template-library` to sibling-skill list.

#### Backup

Before the v1.9.0 changes were written to `v1.9.0-staging/`, full backups were taken of the plugin, local-context, and knowledge library (preserved in session backup directory).

### Skills changed

| Skill | From | To | Change type |
|-------|------|----|-------------|
| template-library (new) | — | 0.1.0 | new — CRUD + resolve + render + backup/restore |
| plugin-configurator | 0.10.0 | 1.0.0 | minor — Step O-T onboarding + template library update mode |
| knowledge-library | 0.3.0 | 0.4.0 | minor — routing to template-library, sibling skill section |
| write-concept | 0.5.0 | 0.6.0 | minor — Step T |
| requirements-creator | 0.5.1 | 0.6.0 | minor — Step T (Create mode) |
| product-research | 0.5.0 | 0.6.0 | minor — Step T |
| cjm-research | 0.2.0 | 0.3.0 | minor — Step T |
| feature-task-creator | 0.7.0 | 0.8.0 | minor — Step T (task + epic) |
| brainstorm-features | 0.5.0 | 0.6.0 | minor — Step T (on save) |
| product-analysis | 0.6.0 | 0.7.0 | minor — Step T (structured reports) |
| diagram-prototyper | 0.7.0 | 0.8.0 | minor — Step T (presentations) |
| meeting-processor | 0.9.0 | 0.10.0 | minor — Step T (MoM) + delegation pattern |

---

## v1.8.0 (2026-04-16)

### Changed — User-Controlled Storage

**Problem:** Knowledge Library and local-context.md were stored in `~/.grow-pm/` — a hidden directory that was invisible to the user, not syncable, and often lost during plugin reinstalls. Users repeatedly lost their curated libraries.

**Solution:** Replaced hardcoded `~/.grow-pm/` storage with a pointer-based system where the user chooses where their data lives.

#### Core architecture change
- `~/.grow-pm/` now contains ONLY a pointer file (`.storage-pointer.yaml`) that tells the plugin where actual data is stored
- Two storage modes: **Vault** (Obsidian vault = primary storage, recommended) or **Custom** (user-chosen folder)
- When Obsidian is configured, the vault IS the primary storage — no separate copy, no mirror sync needed

#### Files changed

- **references/persistent-storage.md** — complete rewrite:
  - New "Pointer + User-Controlled Storage" architecture
  - Storage pointer format (.storage-pointer.yaml)
  - Per-product Knowledge Library support
  - File Resolution Protocol (R-1 through R-4)
  - Storage Selection during onboarding (S-1 through S-3)
  - Recovery flow when pointer is missing — always asks user before creating empty config
  - Change Storage Location workflow (CL-1, CL-2)

- **knowledge-library** `0.3.0 → 0.4.0`:
  - Library Storage section rewritten: vault = primary when configured, custom folder otherwise
  - New "Library Resolution at Skill Start" — 5-step resolution chain with legacy fallback
  - Removed Vault Mirror Sync (no longer needed — vault IS primary)
  - Added: "Never silently create empty library" quality standard

- **plugin-configurator** `0.9.0 → 0.10.0`:
  - New **Step 0 — Storage Selection** in Onboarding (before any data collection)
  - Rewritten **Auto-trigger Protocol** — pointer-based resolution, recovery flow asks user
  - Rewritten **Reinstall / Migration Mode** — 4 scenarios (normal, data moved, legacy, unknown)
  - RM-5: creates/updates storage pointer after migration
  - **Update mode**: added "Storage Location" option to change where data lives
  - All `~/.grow-pm/local-context.md` save references — user's storage location via pointer

---

## v1.7.0 (2026-04-15)

### What changed
Data persistence hardening: added pre-update backup protocol, Obsidian Vault mirror sync, and vault-based recovery to prevent data loss during plugin updates/reinstalls. Knowledge Library was lost during a plugin update — this release adds multiple layers of protection.

### Added
- **Pre-Update Backup Protocol** (persistent-storage.md) — automatic backup of all user data before plugin updates, with timestamped backup directories and manifests
- **Vault Mirror Protocol** (persistent-storage.md) — write-through replication of `~/.grow-pm/` to Obsidian Vault `_System/` and `Knowledge/` folders
- **Vault Recovery Protocol** (persistent-storage.md) — recovery from Obsidian Vault when `~/.grow-pm/` is lost
- **Knowledge Library vault sync** (knowledge-library SKILL.md) — automatic sync to vault after every write operation, plus recovery check at skill start
- **Plugin Configurator vault fallback** (plugin-configurator SKILL.md) — RM-0 pre-update backup, RM-1 vault recovery search, user prompt for vault path if data missing

### Changed
- **persistent-storage.md** — added Pre-Update Backup (PU-1—PU-4), Vault Mirror (VM-1—VM-3), Vault Recovery (VR-1—VR-3) protocols; strengthened deletion behavior section
- **vault-protocol.md** `1.0 → 1.1` — added Context Mirror to Vault section with sync triggers, algorithm, and recovery reference
- **plugin-configurator** `0.8.0 → 0.9.0` — added RM-0 (pre-update backup), RM-1 vault fallback search, RM-1a user vault path prompt, Step 13e vault mirror sync, U-4 vault mirror on update
- **knowledge-library** `0.2.0 → 0.3.0` — added Vault Mirror Sync section with post-write sync and recovery check at start

### Skills changed
| Skill | From | To | Change type |
|-------|------|----|-------------|
| plugin-configurator | 0.8.0 | 0.9.0 | minor — vault recovery + pre-update backup + mirror sync |
| knowledge-library | 0.2.0 | 0.3.0 | minor — vault mirror sync + recovery check |
| persistent-storage (ref) | — | — | minor — 3 new protocols (backup, mirror, recovery) |
| vault-protocol (ref) | 1.0 | 1.1 | minor — context mirror section |

---

## v1.6.0 (2026-04-14)

### Added
- **Obsidian Vault Integration (Phase 1)** — optional persistent knowledge graph for accumulating artifacts across sessions
  - New `references/vault-protocol.md` — shared protocol for vault detection, search, save, and MOC management
  - New `references/vault-schema.md` — frontmatter schema, type taxonomy (16 types), tag taxonomy, folder structure, templates
  - Multi-vault support with per-product vault binding
  - Three-level fallback: L0 (no vault), L1 (file system), L2 (file + Obsidian MCP)

### Changed
- **local-context-protocol.md** — added Step 0h (vault detection) and Step 0.5 (vault context search)
- **plugin-configurator** `0.7.0 → 0.8.0` — new Obsidian Vault section in Onboarding, Update, and Validate modes
- **cjm-research** `0.1.0 → 0.2.0` — added Step 1.5 (vault context) and Step 12.5 (vault save)
- **write-concept** `0.4.0 → 0.5.0` — added Step 0.5 (vault context) and Step 7.5 (vault save)
- **product-analysis** `0.5.0 → 0.6.0` — added Step 0.5 (vault context) and Vault Save with A/B test hypothesis lifecycle updates

---

## [1.5.0] — 2026-04-14

### What changed
- Added `cjm-research` skill (v0.1.0) — CJM pipeline orchestrator with 5 modes: anomalies (quick funnel check), hypotheses (improvement ideas with ICE + funnel impact), full (comprehensive analysis with verification, risk assessment, backlog), health-check (scheduled automated monitoring), comparison (cross-platform side-by-side analysis). Delegates to product-analysis, knowledge-library, product-research, and brainstorm-features. Assembles 5 report formats. Includes independent hypothesis verification (Step 10), risk assessment (Step 11), and post-report skill chaining.
- Updated `product-analysis` (v0.4.0 → v0.5.0) — added CJM Funnel Analysis mode: loads dashboard data per funnel stage, calculates per-stage conversion rates and deviations from baseline, detects anomalies with severity classification (Critical/Warning/Info/Positive per cjm-protocol.md), returns structured data to cjm-research. Added CJM-specific skill chaining offer.
- Updated `product-research` (v0.4.0 → v0.5.0) — added Knowledge Library as data source (search curated sources during research, include in output with trust scores). Added Knowledge Library availability check in Step 1. Added UX Benchmark Research type (benchmark matrix: practice, industry standard, current state, gap, priority). Added CJM Research chaining offer after UX benchmark research.
- Updated `brainstorm-features` (v0.4.0 → v0.5.0) — added CJM Hypotheses mode (Step 3C): generates hypotheses from CJM anomaly data with Data Trigger + Feedback Match + Heuristic Match format. Enhanced ICE scoring with stage-position multipliers (Stage 1: ×1.5, Stage 2: ×1.3, Stage 3: ×1.1, Stage 4+: ×1.0). Added funnel impact calculation per hypothesis. Added hypothesis categorization: Low-hanging fruit / Structural changes / Business logic changes. Added Situation D (invoked by CJM Research) to skip manual context gathering.

### Skills changed
| Skill | From | To | Change type |
|-------|------|----|-------------|
| cjm-research | — | 0.1.0 | new — CJM pipeline orchestrator with 5 modes and 12-step workflow |
| product-analysis | 0.4.0 | 0.5.0 | minor — added CJM Funnel Analysis mode (CJM-1 through CJM-5) |
| product-research | 0.4.0 | 0.5.0 | minor — added Knowledge Library source + UX Benchmark Research type |
| brainstorm-features | 0.4.0 | 0.5.0 | minor — added CJM Hypotheses mode (Step 3C) with funnel impact calculation |

---

## [1.4.0] — 2026-04-11

### What changed
- Persistent user data storage in `~/.grow-pm/` — all configuration, templates, and knowledge library data now stored in user's home directory, surviving plugin uninstalls, reinstalls, and updates
- Added Reinstall/Migration mode to Plugin Configurator — detects existing data, offers recovery/migration/fresh start
- Legacy data discovery and migration from workspace/session directories to `~/.grow-pm/`
- Knowledge Library storage path moved to `~/.grow-pm/knowledge-library/`
- Schema versioning with `.schema-version` file
- Auto-backups before migrations (keeps last 3)
- Updated knowledge-library (v0.1.0 → v0.2.0) — persistent storage, markdown table format, enhanced search modes
- Updated plugin-configurator (v0.6.0 → v0.7.0) — Reinstall/Migration mode, persistent storage protocol, validation report includes CJM and Knowledge Library readiness

### Skills changed
| Skill | From | To | Change type |
|-------|------|----|-------------|
| knowledge-library | 0.1.0 | 0.2.0 | minor — persistent storage in `~/.grow-pm/`, markdown format, enhanced modes |
| plugin-configurator | 0.6.0 | 0.7.0 | minor — Reinstall/Migration mode, persistent storage |

### References changed
| Reference | Change |
|-----------|--------|
| `persistent-storage.md` | new — persistent storage protocol, directory structure, migration |

---

## [1.3.0] — 2026-04-10

### What changed
- Added `knowledge-library` skill (v0.1.0) — local source management with trust scoring, multi-mode search (library, Confluence, Google Drive, Baymard, internet), and bulk import. Service skill for CJM enrichment with direct user management capabilities.
- Added `references/cjm-protocol.md` — shared CJM standards: anomaly severity levels, funnel impact calculation formula, health score formula, cross-platform comparison methodology, hypothesis verification checklist.
- Added `references/funnel-templates.md` — standard funnel stage templates for e-commerce, SaaS, marketplace, and custom product types with recommended metrics and anomaly thresholds.
- Updated `plugin-configurator` (v0.5.0 → v0.6.0) — added CJM Configuration (Step 9) with funnel template selection, stage-dashboard mapping, anomaly thresholds, and default analysis settings. Added Knowledge Library onboarding (Step 10) with source import, Baymard configuration, and search mode setup. Added CJM and Knowledge Library sections to Update, Validate, and View modes.
- Updated `references/local-context-protocol.md` — added Step 0f (CJM configuration check for CJM skills) and Step 0g (Knowledge Library availability check). Added CJM and Knowledge Library fields to context usage guidelines.

### Skills changed
| Skill | From | To | Change type |
|-------|------|----|-------------|
| knowledge-library | — | 0.1.0 | new — local knowledge source management with trust scoring and multi-mode search |
| plugin-configurator | 0.5.0 | 0.6.0 | minor — added CJM Configuration and Knowledge Library onboarding steps |

### References changed
| Reference | Change |
|-----------|--------|
| `cjm-protocol.md` | new — CJM shared standards |
| `funnel-templates.md` | new — funnel stage templates by product type |
| `local-context-protocol.md` | updated — CJM and Knowledge Library support |

---

## [1.2.1] — 2026-04-08

**Plugin summary:** Remove heading numbering from requirements-creator skill and template.

| Skill | Version | Change |
|-------|---------|--------|
| requirements-creator | 0.5.0 → 0.5.1 | Remove heading numbering |

### Details

**requirements-creator (v0.5.1)**
- Removed numbered `# | Section` column from the Step 4 template table — sections are now listed without sequential numbers
- Added formatting rule: headings must NOT be numbered (no "1. Epic", "2. Hypotheses" etc)
- Updated `references/requirements-template.md`: removed numbering from all section headings (e.g., "### 1. Epic" → "### Epic", "#### 5.1 Business Requirements" → "#### Business Requirements")
- Version bump: 0.5.0 → 0.5.1


## [1.2.0] — 2026-04-07

### Plugin
- Enhanced `diagram-prototyper` with Infographic creation support — new visualization type with 5 styles, built-in HTML/CSS generation, and data confidentiality handling

### Skills changed
| Skill | From | To | Change type |
|-------|------|----|-------------|
| diagram-prototyper | 0.6.0 | 0.7.0 | minor — added Infographic as new visualization type with full workflow support |

### Details
- **Step 1b — New visualization type:** Added **Infographic** to the type selection table alongside Diagram, Prototype, Mind Map, and Presentation. Examples: funnel metrics overview, feature comparison, onboarding steps, A/B test results summary, market research highlights
- **Step 1c — Infographic requirements gathering:** 6 targeted questions covering main message, data/metrics, target audience, intended use, key data points, and dimensions/format
- **Step 3b — Infographic style selection (new step):** 5 visual styles with context-based recommendations: Data-driven (metrics, KPIs), Process/timeline (flows, roadmaps), Comparison (feature eval, competitive), Informational/educational (product overviews), Statistical/report (quarterly data, surveys)
- **Step 4 — New tool: HTML/CSS (built-in):** Local generation of infographics as self-contained HTML files with inline CSS and SVG charts. No external LLM dependency. Added to tool recommendation table with 3 infographic-specific rows
- **Step 5 — Infographic prompt construction:** Detailed guidelines for headline, data points, visual hierarchy, section structure, chart types, icons, color scheme, dimensions, footer. Style-specific guidance for all 5 styles. Data confidentiality note: recommends HTML/CSS for infographics with sensitive metrics
- **Step 6a2 — HTML/CSS generation (new substep):** Full generation pipeline: fixed-width container, semantic sections, CSS Grid/Flexbox, inline SVG charts, CSS variables for color palette, system/Google fonts, @media print styles, HTML validation
- **Step 6g — Quality check updated:** Added "Data integrity" check row for infographics (numbers match source, charts proportional, units labeled)
- **Step 8e/8f — Publishing updated:** Added .html to local file formats. New Step 8f for additional infographic export (PNG, PDF, HTML)
- **Step 9 — Skill chaining updated:** New chaining path for infographics from product-analysis/product-research to Presentation Creator
- **Inbound chaining updated:** product-research and product-analysis now suggest infographics in their visualization offers
- **Quality standards updated:** Added HTML validity, self-containment, browser rendering, and data proportion accuracy requirements



## [0.9.0] — 2026-04-01

### Plugin
- Enhanced `meeting-processor` with calendar integration and enriched participant context

### Skills changed
| Skill | From | To | Change type |
|-------|------|----|-------------|
| meeting-processor | 0.8.0 | 0.9.0 | minor — calendar enrichment step + participant context passing |

### Details
- **Step M1d — Calendar enrichment:** After finding a meeting, optionally look up the matching calendar event (Google Calendar MCP or Microsoft Calendar MCP) to extract participants (with emails, roles, RSVP), agenda, attached documents (Google Docs, Confluence, Figma, presentations), organizer, and recurrence info. Reads attached materials for additional context
- **Enhanced M2 data merging:** Calendar data merged with transcript data using priority rules. Discrepancies marked (invited but silent, not invited but spoke)
- **Enhanced M9 skill chaining:** Full participant context (name, email, role, attendance status) now passed to all downstream skills. Per-skill content mapping ensures each target skill gets the data it needs (e.g., participants with roles for task assignment, speaker attribution for research)
- **MoM template updated:** Participants table now includes Email and Status columns

---

## [0.8.0] — 2026-04-01

### Plugin
- Added new skill **meeting-processor** — process meetings from any source to extract action items, decisions, and structured reports

### Skills changed
| Skill | From | To | Change type |
|-------|------|----|-------------|
| meeting-processor | — | 0.8.0 | new skill |

### Details
- **Two modes:** Process (single meeting → structured MoM or short summary) and Search (cross-meeting query → chronological synthesis)
- **Tool-agnostic input:** Fireflies MCP, other meeting tool MCPs, uploaded files (audio/video/text/srt), pasted text
- **Auto-classification:** 5 meeting types (Grooming, Discovery, Demo/Retro, Status, Brainstorm) with multi-type support, user confirmation
- **Type-adaptive extraction:** common blocks (participants, topics, decisions, action items, open questions) + type-specific blocks (estimates for grooming, quotes for discovery, etc.)
- **Skill chaining:** Grooming → feature-task-creator, Discovery → product-research/requirements-creator, Brainstorm → brainstorm-features, Any → diagram-prototyper
- **Publishing:** Confluence, Notion, local file

---

## [0.7.0] — 2026-03-31

### Plugin
- Enhanced `feature-task-creator` with two new workflow improvements

### Skills changed
| Skill | From | To | Change type |
|-------|------|----|-------------|
| feature-task-creator | 0.4.0 | 0.7.0 | minor — added Step 6b (field validation with user confirmation for uncertain values) and Step 12 (post-creation verification with auto-fix) |

### Details
- **Step 6b — Validate field values before creation:** Before creating tasks, the skill now categorizes each field value by confidence level (Certain / Inferred / Uncertain / Unknown), presents inferred values for confirmation, and asks the user for uncertain or unknown values with proposed options
- **Step 12 — Post-creation verification:** After creating all tasks, the skill reads back one task from Jira, runs 9 verification checks (title, parent, reporter, team, labels, components, description, issue type, links), reports discrepancies with severity, proposes fixes, and propagates fixes to all affected tasks

---

## [0.6.0] — 2026-03-30

### Plugin
- Added new skill **diagram-prototyper** — create diagrams, flowcharts, BPMN processes, mind maps, and UI prototypes
- Defined inbound skill chaining: write-concept, brainstorm-features, requirements-creator, product-research, product-analysis can now invoke diagram-prototyper

### Skills changed
| Skill | From | To | Change type |
|-------|------|----|-------------|
| diagram-prototyper | — | 0.6.0 | new skill |

---

## [0.5.0] — 2026-03-27

### Plugin
- Added **Analyze & Improve mode** to `requirements-creator` skill
- Translated `README.md` fully to English

### Skills changed
| Skill | From | To | Change type |
|-------|------|----|-------------|
| requirements-creator | 0.4.0 | 0.5.0 | minor — new Analyze & Improve mode added (A1—A9 workflow) |

---

## [0.4.0] — 2026-03-26

### Plugin
- Added versioning system for skills and plugin: `version` field in all SKILL.md frontmatter
- Added `CHANGELOG.md` (this file)
- Added versioning rules to `references/self-improvement.md`
- Added versioning protocol to `skills/plugin-configurator/SKILL.md` (step 4 — Implement improvement)

### Skills changed
| Skill | From | To | Change type |
|-------|------|----|-------------|
| brainstorm-features | 0.3.0 | 0.4.0 | minor — version field added |
| feature-task-creator | 0.3.0 | 0.4.0 | minor — version field added |
| plugin-configurator | 0.3.0 | 0.4.0 | minor — versioning protocol added |
| product-analysis | 0.3.0 | 0.4.0 | minor — version field added |
| product-research | 0.3.0 | 0.4.0 | minor — version field added |
| requirements-creator | 0.3.0 | 0.4.0 | minor — version field added |
| write-concept | 0.3.0 | 0.4.0 | minor — version field added |

---

## [0.3.0] — 2026-03-25

### Plugin
- Translated all skill instructions and reference files to English
- Output language remains controlled by `user.language` in `local-context.md`

### Skills changed
| Skill | From | To | Change type |
|-------|------|----|-------------|
| brainstorm-features | 0.2.0 | 0.3.0 | minor — full EN translation of workflow instructions |
| feature-task-creator | 0.2.0 | 0.3.0 | minor — full EN translation of workflow instructions |
| plugin-configurator | 0.2.0 | 0.3.0 | minor — full EN translation of all UI strings |
| product-analysis | 0.2.0 | 0.3.0 | minor — full EN translation of workflow instructions |
| product-research | 0.2.0 | 0.3.0 | minor — full EN translation of workflow instructions |
| requirements-creator | 0.2.0 | 0.3.0 | minor — full EN translation, requirements template translated |
| write-concept | 0.2.0 | 0.3.0 | minor — full EN translation of workflow instructions |

---

## [0.2.0] — 2026-03-25

### Plugin
- Added `plugin-configurator` skill with onboarding, update, validate, and view modes
- Added `local-context.md` support (org-specific config, gitignored)
- Added `references/local-context-protocol.md` — auto-trigger and enrichment protocol
- Added `references/self-improvement.md` — self-improvement protocol for all skills
- Added `references/context-schema.md` — full schema for `local-context.md`

### Skills changed
| Skill | From | To | Change type |
|-------|------|----|-------------|
| plugin-configurator | — | 0.2.0 | new skill |
| brainstorm-features | 0.1.0 | 0.2.0 | minor — local-context integration |
| feature-task-creator | 0.1.0 | 0.2.0 | minor — local-context integration |
| product-analysis | 0.1.0 | 0.2.0 | minor — local-context integration |
| product-research | 0.1.0 | 0.2.0 | minor — local-context integration |
| requirements-creator | 0.1.0 | 0.2.0 | minor — local-context integration |
| write-concept | 0.1.0 | 0.2.0 | minor — local-context integration |

---

## [0.1.0] — initial release

### Skills
- brainstorm-features
- feature-task-creator
- product-analysis
- product-research
- requirements-creator
- write-concept
