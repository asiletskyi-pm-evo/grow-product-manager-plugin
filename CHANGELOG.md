# Changelog â Grow Product Manager Plugin

All notable changes to this plugin are documented here.

Version format: `MAJOR.MINOR.PATCH`
- **MAJOR** â breaking changes, full workflow restructure across multiple skills
- **MINOR** â new skill added, new step/section in existing skill, significant workflow addition
- **PATCH** â wording fix, small content addition, formatting change, bug fix in skill logic

Each skill also carries its own version in the frontmatter (`version:` field in SKILL.md).
When a skill changes, its version is bumped independently. The plugin version is bumped to reflect the highest-impact change among all updated skills.

---

## v1.8.0 (2026-04-16)

### Changed â User-Controlled Storage

**Problem:** Knowledge Library and local-context.md were stored in `~/.grow-pm/` â a hidden directory that was invisible to the user, not syncable, and often lost during plugin reinstalls. Users repeatedly lost their curated libraries.

**Solution:** Replaced hardcoded `~/.grow-pm/` storage with a pointer-based system where the user chooses where their data lives.

#### Core architecture change
- `~/.grow-pm/` now contains ONLY a pointer file (`.storage-pointer.yaml`) that tells the plugin where actual data is stored
- Two storage modes: **Vault** (Obsidian vault = primary storage, recommended) or **Custom** (user-chosen folder)
- When Obsidian is configured, the vault IS the primary storage â no separate copy, no mirror sync needed

#### Files changed

- **references/persistent-storage.md** â complete rewrite:
  - New "Pointer + User-Controlled Storage" architecture
  - Storage pointer format (.storage-pointer.yaml)
  - Per-product Knowledge Library support
  - File Resolution Protocol (R-1 through R-4)
  - Storage Selection during onboarding (S-1 through S-3)
  - Recovery flow when pointer is missing â always asks user before creating empty config
  - Change Storage Location workflow (CL-1, CL-2)

- **knowledge-library** `0.3.0 â 0.4.0`:
  - Library Storage section rewritten: vault = primary when configured, custom folder otherwise
  - New "Library Resolution at Skill Start" â 5-step resolution chain with legacy fallback
  - Removed Vault Mirror Sync (no longer needed â vault IS primary)
  - Added: "Never silently create empty library" quality standard

- **plugin-configurator** `0.9.0 â 0.10.0`:
  - New **Step 0 â Storage Selection** in Onboarding (before any data collection)
  - Rewritten **Auto-trigger Protocol** â pointer-based resolution, recovery flow asks user
  - Rewritten **Reinstall / Migration Mode** â 4 scenarios (normal, data moved, legacy, unknown)
  - RM-5: creates/updates storage pointer after migration
  - **Update mode**: added "Storage Location" option to change where data lives
  - All `~/.grow-pm/local-context.md` save references â user's storage location via pointer

---

## v1.7.0 (2026-04-15)

### What changed
Data persistence hardening: added pre-update backup protocol, Obsidian Vault mirror sync, and vault-based recovery to prevent data loss during plugin updates/reinstalls. Knowledge Library was lost during a plugin update â this release adds multiple layers of protection.

### Added
- **Pre-Update Backup Protocol** (persistent-storage.md) â automatic backup of all user data before plugin updates, with timestamped backup directories and manifests
- **Vault Mirror Protocol** (persistent-storage.md) â write-through replication of `~/.grow-pm/` to Obsidian Vault `_System/` and `Knowledge/` folders
- **Vault Recovery Protocol** (persistent-storage.md) â recovery from Obsidian Vault when `~/.grow-pm/` is lost
- **Knowledge Library vault sync** (knowledge-library SKILL.md) â automatic sync to vault after every write operation, plus recovery check at skill start
- **Plugin Configurator vault fallback** (plugin-configurator SKILL.md) â RM-0 pre-update backup, RM-1 vault recovery search, user prompt for vault path if data missing

### Changed
- **persistent-storage.md** â added Pre-Update Backup (PU-1âPU-4), Vault Mirror (VM-1âVM-3), Vault Recovery (VR-1âVR-3) protocols; strengthened deletion behavior section
- **vault-protocol.md** `1.0 â 1.1` â added Context Mirror to Vault section with sync triggers, algorithm, and recovery reference
- **plugin-configurator** `0.8.0 â 0.9.0` â added RM-0 (pre-update backup), RM-1 vault fallback search, RM-1a user vault path prompt, Step 13e vault mirror sync, U-4 vault mirror on update
- **knowledge-library** `0.2.0 â 0.3.0` â added Vault Mirror Sync section with post-write sync and recovery check at start

### Skills changed
| Skill | From | To | Change type |
|-------|------|----|-------------|
| plugin-configurator | 0.8.0 | 0.9.0 | minor â vault recovery + pre-update backup + mirror sync |
| knowledge-library | 0.2.0 | 0.3.0 | minor â vault mirror sync + recovery check |
| persistent-storage (ref) | â | â | minor â 3 new protocols (backup, mirror, recovery) |
| vault-protocol (ref) | 1.0 | 1.1 | minor â context mirror section |

---

## v1.6.0 (2026-04-14)

### Added
- **Obsidian Vault Integration (Phase 1)** â optional persistent knowledge graph for accumulating artifacts across sessions
  - New `references/vault-protocol.md` â shared protocol for vault detection, search, save, and MOC management
  - New `references/vault-schema.md` â frontmatter schema, type taxonomy (16 types), tag taxonomy, folder structure, templates
  - Multi-vault support with per-product vault binding
  - Three-level fallback: L0 (no vault), L1 (file system), L2 (file + Obsidian MCP)

### Changed
- **local-context-protocol.md** â added Step 0h (vault detection) and Step 0.5 (vault context search)
- **plugin-configurator** `0.7.0 â 0.8.0` â new Obsidian Vault section in Onboarding, Update, and Validate modes
- **cjm-research** `0.1.0 â 0.2.0` â added Step 1.5 (vault context) and Step 12.5 (vault save)
- **write-concept** `0.4.0 â 0.5.0` â added Step 0.5 (vault context) and Step 7.5 (vault save)
- **product-analysis** `0.5.0 â 0.6.0` â added Step 0.5 (vault context) and Vault Save with A/B test hypothesis lifecycle updates

---

## [1.5.0] â 2026-04-14

### What changed
- Added `cjm-research` skill (v0.1.0) â CJM pipeline orchestrator with 5 modes: anomalies (quick funnel check), hypotheses (improvement ideas with ICE + funnel impact), full (comprehensive analysis with verification, risk assessment, backlog), health-check (scheduled automated monitoring), comparison (cross-platform side-by-side analysis). Delegates to product-analysis, knowledge-library, product-research, and brainstorm-features. Assembles 5 report formats. Includes independent hypothesis verification (Step 10), risk assessment (Step 11), and post-report skill chaining.
- Updated `product-analysis` (v0.4.0 â v0.5.0) â added CJM Funnel Analysis mode: loads dashboard data per funnel stage, calculates per-stage conversion rates and deviations from baseline, detects anomalies with severity classification (Critical/Warning/Info/Positive per cjm-protocol.md), returns structured data to cjm-research. Added CJM-specific skill chaining offer.
- Updated `product-research` (v0.4.0 â v0.5.0) â added Knowledge Library as data source (search curated sources during research, include in output with trust scores). Added Knowledge Library availability check in Step 1. Added UX Benchmark Research type (benchmark matrix: practice, industry standard, current state, gap, priority). Added CJM Research chaining offer after UX benchmark research.
- Updated `brainstorm-features` (v0.4.0 â v0.5.0) â added CJM Hypotheses mode (Step 3C): generates hypotheses from CJM anomaly data with Data Trigger + Feedback Match + Heuristic Match format. Enhanced ICE scoring with stage-position multipliers (Stage 1: Ã1.5, Stage 2: Ã1.3, Stage 3: Ã1.1, Stage 4+: Ã1.0). Added funnel impact calculation per hypothesis. Added hypothesis categorization: Low-hanging fruit / Structural changes / Business logic changes. Added Situation D (invoked by CJM Research) to skip manual context gathering.

### Skills changed
| Skill | From | To | Change type |
|-------|------|----|-------------|
| cjm-research | â | 0.1.0 | new â CJM pipeline orchestrator with 5 modes and 12-step workflow |
| product-analysis | 0.4.0 | 0.5.0 | minor â added CJM Funnel Analysis mode (CJM-1 through CJM-5) |
| product-research | 0.4.0 | 0.5.0 | minor â added Knowledge Library source + UX Benchmark Research type |
| brainstorm-features | 0.4.0 | 0.5.0 | minor â added CJM Hypotheses mode (Step 3C) with funnel impact calculation |

---

## [1.4.0] â 2026-04-11

### What changed
- Persistent user data storage in `~/.grow-pm/` â all configuration, templates, and knowledge library data now stored in user's home directory, surviving plugin uninstalls, reinstalls, and updates
- Added Reinstall/Migration mode to Plugin Configurator â detects existing data, offers recovery/migration/fresh start
- Legacy data discovery and migration from workspace/session directories to `~/.grow-pm/`
- Knowledge Library storage path moved to `~/.grow-pm/knowledge-library/`
- Schema versioning with `.schema-version` file
- Auto-backups before migrations (keeps last 3)
- Updated knowledge-library (v0.1.0 â v0.2.0) â persistent storage, markdown table format, enhanced search modes
- Updated plugin-configurator (v0.6.0 â v0.7.0) â Reinstall/Migration mode, persistent storage protocol, validation report includes CJM and Knowledge Library readiness

### Skills changed
| Skill | From | To | Change type |
|-------|------|----|-------------|
| knowledge-library | 0.1.0 | 0.2.0 | minor â persistent storage in `~/.grow-pm/`, markdown format, enhanced modes |
| plugin-configurator | 0.6.0 | 0.7.0 | minor â Reinstall/Migration mode, persistent storage |

### References changed
| Reference | Change |
|-----------|--------|
| `persistent-storage.md` | new â persistent storage protocol, directory structure, migration |

---

## [1.3.0] â 2026-04-10

### What changed
- Added `knowledge-library` skill (v0.1.0) â local source management with trust scoring, multi-mode search (library, Confluence, Google Drive, Baymard, internet), and bulk import. Service skill for CJM enrichment with direct user management capabilities.
- Added `references/cjm-protocol.md` â shared CJM standards: anomaly severity levels, funnel impact calculation formula, health score formula, cross-platform comparison methodology, hypothesis verification checklist.
- Added `references/funnel-templates.md` â standard funnel stage templates for e-commerce, SaaS, marketplace, and custom product types with recommended metrics and anomaly thresholds.
- Updated `plugin-configurator` (v0.5.0 â v0.6.0) â added CJM Configuration (Step 9) with funnel template selection, stage-dashboard mapping, anomaly thresholds, and default analysis settings. Added Knowledge Library onboarding (Step 10) with source import, Baymard configuration, and search mode setup. Added CJM and Knowledge Library sections to Update, Validate, and View modes.
- Updated `references/local-context-protocol.md` â added Step 0f (CJM configuration check for CJM skills) and Step 0g (Knowledge Library availability check). Added CJM and Knowledge Library fields to context usage guidelines.

### Skills changed
| Skill | From | To | Change type |
|-------|------|----|-------------|
| knowledge-library | â | 0.1.0 | new â local knowledge source management with trust scoring and multi-mode search |
| plugin-configurator | 0.5.0 | 0.6.0 | minor â added CJM Configuration and Knowledge Library onboarding steps |

### References changed
| Reference | Change |
|-----------|--------|
| `cjm-protocol.md` | new â CJM shared standards |
| `funnel-templates.md` | new â funnel stage templates by product type |
| `local-context-protocol.md` | updated â CJM and Knowledge Library support |

---

## [1.2.1] â 2026-04-08

**Plugin summary:** Remove heading numbering from requirements-creator skill and template.

| Skill | Version | Change |
|-------|---------|--------|
| requirements-creator | 0.5.0 â 0.5.1 | Remove heading numbering |

### Details

**requirements-creator (v0.5.1)**
- Removed numbered `# | Section` column from the Step 4 template table â sections are now listed without sequential numbers
- Added formatting rule: headings must NOT be numbered (no "1. Epic", "2. Hypotheses" etc)
- Updated `references/requirements-template.md`: removed numbering from all section headings (e.g., "### 1. Epic" â "### Epic", "#### 5.1 Business Requirements" â "#### Business Requirements")
- Version bump: 0.5.0 â 0.5.1


## [1.2.0] â 2026-04-07

### Plugin
- Enhanced `diagram-prototyper` with Infographic creation support â new visualization type with 5 styles, built-in HTML/CSS generation, and data confidentiality handling

### Skills changed
| Skill | From | To | Change type |
|-------|------|----|-------------|
| diagram-prototyper | 0.6.0 | 0.7.0 | minor â added Infographic as new visualization type with full workflow support |

### Details
- **Step 1b â New visualization type:** Added **Infographic** to the type selection table alongside Diagram, Prototype, Mind Map, and Presentation. Examples: funnel metrics overview, feature comparison, onboarding steps, A/B test results summary, market research highlights
- **Step 1c â Infographic requirements gathering:** 6 targeted questions covering main message, data/metrics, target audience, intended use, key data points, and dimensions/format
- **Step 3b â Infographic style selection (new step):** 5 visual styles with context-based recommendations: Data-driven (metrics, KPIs), Process/timeline (flows, roadmaps), Comparison (feature eval, competitive), Informational/educational (product overviews), Statistical/report (quarterly data, surveys)
- **Step 4 â New tool: HTML/CSS (built-in):** Local generation of infographics as self-contained HTML files with inline CSS and SVG charts. No external LLM dependency. Added to tool recommendation table with 3 infographic-specific rows
- **Step 5 â Infographic prompt construction:** Detailed guidelines for headline, data points, visual hierarchy, section structure, chart types, icons, color scheme, dimensions, footer. Style-specific guidance for all 5 styles. Data confidentiality note: recommends HTML/CSS for infographics with sensitive metrics
- **Step 6a2 â HTML/CSS generation (new substep):** Full generation pipeline: fixed-width container, semantic sections, CSS Grid/Flexbox, inline SVG charts, CSS variables for color palette, system/Google fonts, @media print styles, HTML validation
- **Step 6g â Quality check updated:** Added "Data integrity" check row for infographics (numbers match source, charts proportional, units labeled)
- **Step 8e/8f â Publishing updated:** Added .html to local file formats. New Step 8f for additional infographic export (PNG, PDF, HTML)
- **Step 9 â Skill chaining updated:** New chaining path for infographics from product-analysis/product-research to Presentation Creator
- **Inbound chaining updated:** product-research and product-analysis now suggest infographics in their visualization offers
- **Quality standards updated:** Added HTML validity, self-containment, browser rendering, and data proportion accuracy requirements



## [0.9.0] â 2026-04-01

### Plugin
- Enhanced `meeting-processor` with calendar integration and enriched participant context

### Skills changed
| Skill | From | To | Change type |
|-------|------|----|-------------|
| meeting-processor | 0.8.0 | 0.9.0 | minor â calendar enrichment step + participant context passing |

### Details
- **Step M1d â Calendar enrichment:** After finding a meeting, optionally look up the matching calendar event (Google Calendar MCP or Microsoft Calendar MCP) to extract participants (with emails, roles, RSVP), agenda, attached documents (Google Docs, Confluence, Figma, presentations), organizer, and recurrence info. Reads attached materials for additional context
- **Enhanced M2 data merging:** Calendar data merged with transcript data using priority rules. Discrepancies marked (invited but silent, not invited but spoke)
- **Enhanced M9 skill chaining:** Full participant context (name, email, role, attendance status) now passed to all downstream skills. Per-skill content mapping ensures each target skill gets the data it needs (e.g., participants with roles for task assignment, speaker attribution for research)
- **MoM template updated:** Participants table now includes Email and Status columns

---

## [0.8.0] â 2026-04-01

### Plugin
- Added new skill **meeting-processor** â process meetings from any source to extract action items, decisions, and structured reports

### Skills changed
| Skill | From | To | Change type |
|-------|------|----|-------------|
| meeting-processor | â | 0.8.0 | new skill |

### Details
- **Two modes:** Process (single meeting â structured MoM or short summary) and Search (cross-meeting query â chronological synthesis)
- **Tool-agnostic input:** Fireflies MCP, other meeting tool MCPs, uploaded files (audio/video/text/srt), pasted text
- **Auto-classification:** 5 meeting types (Grooming, Discovery, Demo/Retro, Status, Brainstorm) with multi-type support, user confirmation
- **Type-adaptive extraction:** common blocks (participants, topics, decisions, action items, open questions) + type-specific blocks (estimates for grooming, quotes for discovery, etc.)
- **Skill chaining:** Grooming â feature-task-creator, Discovery â product-research/requirements-creator, Brainstorm â brainstorm-features, Any â diagram-prototyper
- **Publishing:** Confluence, Notion, local file

---

## [0.7.0] â 2026-03-31

### Plugin
- Enhanced `feature-task-creator` with two new workflow improvements

### Skills changed
| Skill | From | To | Change type |
|-------|------|----|-------------|
| feature-task-creator | 0.4.0 | 0.7.0 | minor â added Step 6b (field validation with user confirmation for uncertain values) and Step 12 (post-creation verification with auto-fix) |

### Details
- **Step 6b â Validate field values before creation:** Before creating tasks, the skill now categorizes each field value by confidence level (Certain / Inferred / Uncertain / Unknown), presents inferred values for confirmation, and asks the user for uncertain or unknown values with proposed options
- **Step 12 â Post-creation verification:** After creating all tasks, the skill reads back one task from Jira, runs 9 verification checks (title, parent, reporter, team, labels, components, description, issue type, links), reports discrepancies with severity, proposes fixes, and propagates fixes to all affected tasks

---

## [0.6.0] â 2026-03-30

### Plugin
- Added new skill **diagram-prototyper** â create diagrams, flowcharts, BPMN processes, mind maps, and UI prototypes
- Defined inbound skill chaining: write-concept, brainstorm-features, requirements-creator, product-research, product-analysis can now invoke diagram-prototyper

### Skills changed
| Skill | From | To | Change type |
|-------|------|----|-------------|
| diagram-prototyper | â | 0.6.0 | new skill |

---

## [0.5.0] â 2026-03-27

### Plugin
- Added **Analyze & Improve mode** to `requirements-creator` skill
- Translated `README.md` fully to English

### Skills changed
| Skill | From | To | Change type |
|-------|------|----|-------------|
| requirements-creator | 0.4.0 | 0.5.0 | minor â new Analyze & Improve mode added (A1âA9 workflow) |

---

## [0.4.0] â 2026-03-26

### Plugin
- Added versioning system for skills and plugin: `version` field in all SKILL.md frontmatter
- Added `CHANGELOG.md` (this file)
- Added versioning rules to `references/self-improvement.md`
- Added versioning protocol to `skills/plugin-configurator/SKILL.md` (step 4 â Implement improvement)

### Skills changed
| Skill | From | To | Change type |
|-------|------|----|-------------|
| brainstorm-features | 0.3.0 | 0.4.0 | minor â version field added |
| feature-task-creator | 0.3.0 | 0.4.0 | minor â version field added |
| plugin-configurator | 0.3.0 | 0.4.0 | minor â versioning protocol added |
| product-analysis | 0.3.0 | 0.4.0 | minor â version field added |
| product-research | 0.3.0 | 0.4.0 | minor â version field added |
| requirements-creator | 0.3.0 | 0.4.0 | minor â version field added |
| write-concept | 0.3.0 | 0.4.0 | minor â version field added |

---

## [0.3.0] â 2026-03-25

### Plugin
- Translated all skill instructions and reference files to English
- Output language remains controlled by `user.language` in `local-context.md`

### Skills changed
| Skill | From | To | Change type |
|-------|------|----|-------------|
| brainstorm-features | 0.2.0 | 0.3.0 | minor â full EN translation of workflow instructions |
| feature-task-creator | 0.2.0 | 0.3.0 | minor â full EN translation of workflow instructions |
| plugin-configurator | 0.2.0 | 0.3.0 | minor â full EN translation of all UI strings |
| product-analysis | 0.2.0 | 0.3.0 | minor â full EN translation of workflow instructions |
| product-research | 0.2.0 | 0.3.0 | minor â full EN translation of workflow instructions |
| requirements-creator | 0.2.0 | 0.3.0 | minor â full EN translation, requirements template translated |
| write-concept | 0.2.0 | 0.3.0 | minor â full EN translation of workflow instructions |

---

## [0.2.0] â 2026-03-25

### Plugin
- Added `plugin-configurator` skill with onboarding, update, validate, and view modes
- Added `local-context.md` support (org-specific config, gitignored)
- Added `references/local-context-protocol.md` â auto-trigger and enrichment protocol
- Added `references/self-improvement.md` â self-improvement protocol for all skills
- Added `references/context-schema.md` â full schema for `local-context.md`

### Skills changed
| Skill | From | To | Change type |
|-------|------|----|-------------|
| plugin-configurator | â | 0.2.0 | new skill |
| brainstorm-features | 0.1.0 | 0.2.0 | minor â local-context integration |
| feature-task-creator | 0.1.0 | 0.2.0 | minor â local-context integration |
| product-analysis | 0.1.0 | 0.2.0 | minor â local-context integration |
| product-research | 0.1.0 | 0.2.0 | minor â local-context integration |
| requirements-creator | 0.1.0 | 0.2.0 | minor â local-context integration |
| write-concept | 0.1.0 | 0.2.0 | minor â local-context integration |

---

## [0.1.0] â initial release

### Skills
- brainstorm-features
- feature-task-creator
- product-analysis
- product-research
- requirements-creator
- write-concept
