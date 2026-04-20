# Grow Product Manager

**Version:** 1.11.0

AI assistant plugin for Product Managers. Integrates with Jira, Confluence, Figma, Tableau, and other tools to streamline product management workflows. Includes a Design Bridge that turns concepts, requirements, research, and hypotheses into brand-themed decks, prototypes, and handoffs with WCAG 2.1 AA a11y gates. All brand specifics (Design System, fonts, tokens, pptx templates) are read from your own `local-context.md` — the plugin ships no hardcoded brand assets.

---

## Overview

The Grow Product Manager plugin is a comprehensive AI-powered toolkit designed to accelerate product management workflows. It provides skills for research, analysis, brainstorming, documentation, task creation, and visualization across your entire product lifecycle.

---

## Skills

### 1. CJM Research (v0.3.0)

**Description:** Customer Journey Map (CJM) pipeline orchestrator with 5 specialized modes for analyzing customer experiences and identifying growth opportunities.

**Modes:**
- **Anomalies** — Detect unexpected patterns in customer funnel behavior
- **Hypotheses** — Generate and validate CJM-based growth hypotheses
- **Full** — Complete CJM analysis with all data points and insights
- **Health-Check** — Assess overall funnel health and drop-off zones
- **Comparison** — Compare customer journeys across platforms or segments

**Delegates to:** Product Analysis, Knowledge Library, Product Research, Brainstorm Features

**Outputs:** Funnel impact models, hypothesis validation, risk assessments

**Trigger phrases:** "analyze CJM", "find funnel anomalies", "CJM research", "funnel health check", "compare platforms", "CJM hypotheses"

---

### 2. Product Analysis (v0.7.0)

**Description:** Analyze product data with interactive dashboards, metrics, and reports to find trends and growth opportunities.

**Modes:**
- **Interactive Q&A** — Ask questions about your metrics
- **Full Report** — Comprehensive analysis of all available data
- **Post-Release** — Analyze metrics before and after a feature release
- **A/B Test Results** — Evaluate test outcomes and statistical significance
- **CJM Funnel Analysis** — Analyze customer behavior across funnel stages

**Trigger phrases:** "analyze metrics", "review a dashboard", "find anomalies", "post-release analysis", "analyze A/B test results", "CJM funnel analysis"

---

### 3. Product Research (v0.7.0)

**Description:** Conduct competitive analysis, user research, market research, and UX benchmarking with Knowledge Library integration for data-backed insights.

**Research Types:**
- Competitive analysis and feature comparison
- User research synthesis and insights
- Market trends and opportunity identification
- UX benchmark research against industry standards

**Trigger phrases:** "research competitors", "analyze the market", "competitive analysis", "find market trends", "UX benchmark research"

---

### 4. Brainstorm Features (v0.7.0)

**Description:** Interactive brainstorming for product features and growth opportunities with ICE scoring and CJM hypothesis generation.

**Features:**
- Feature ideation and scoring (Impact, Confidence, Ease)
- CJM Hypotheses mode with funnel impact calculation
- Growth opportunity identification
- Prioritization framework

**Trigger phrases:** "brainstorm features", "generate hypotheses", "find growth opportunities", "CJM hypotheses"

---

### 5. Write Concept (v0.7.0)

**Description:** Write detailed product concept documents (PRDs) from ideas, problem statements, or research findings.

**Outputs:** Full PRD with objectives, user stories, success metrics, and implementation notes

**Trigger phrases:** "write a concept", "create a PRD"

---

### 6. Requirements Creator (v0.7.0)

**Description:** Create structured feature requirements or analyze and improve existing requirement documents using business analyst expertise.

**Capabilities:**
- Generate detailed requirements from concepts
- Analyze and improve existing specs
- User story generation
- Acceptance criteria definition

**Trigger phrases:** "write requirements", "create feature spec", "review requirements"

---

### 7. Feature Task Creator (v0.8.0)

**Description:** Automatically create Jira tasks and issues from requirements, breaking down work into actionable engineering tasks.

**Capabilities:**
- Parse requirements and decompose into tasks
- Create Jira issues with proper fields and links
- Estimate complexity and effort
- Set up dependencies and sprint planning

**Trigger phrases:** "create tasks for a feature", "create Jira issues"

---

### 8. Diagram & Prototype Creator (v0.8.0)

**Description:** Create diagrams, flowcharts, BPMN processes, mind maps, infographics, and UI prototypes to visualize product concepts.

**Supported Tools:**
- **Mermaid (built-in)** — Fast local generation of flowcharts and diagrams
- **HTML/CSS (built-in)** — Self-contained infographics with inline CSS and SVG charts
- **Google Gemini** — Image generation via browser (Nano Banana mode)
- **ChatGPT** — Image generation via browser (GPT-4o or newer)
- **NotebookLM** — Presentations and mind maps via browser
- **Figma** — Prototypes and design mockups via MCP or browser
- **Draw.io** — XML generation locally or via browser fallback

**Infographic Styles:**
- Data-driven (metrics, KPIs)
- Process/timeline (flows, roadmaps)
- Comparison (feature evaluation, competitive analysis)
- Informational/educational (product overviews)
- Statistical/report (quarterly data, surveys)

**Features:**
- Quality check loop with auto-correction (up to 3 iterations)
- Confidential data generated locally (no external data transmission)
- Skill chaining from other skills
- Publishing to Confluence, Notion, Figma, or local files
- Export as PNG or PDF

**Trigger phrases:** "create a diagram", "draw a flowchart", "BPMN diagram", "make a prototype", "create an infographic", "wireframe", "mockup", "visualize this process", "mind map"

---

### 9. Meeting Processor (v0.10.0)

**Description:** Process meetings from any source to extract action items, decisions, and structured meeting reports with calendar context.

**Meeting Sources:**
- Fireflies.ai recordings
- Other meeting tool recordings
- Uploaded audio/video files
- Transcripts (text or SRT files)
- Pasted meeting notes

**Modes:**
- **Process Mode** — Work with a single meeting:
  - Auto-classify meeting type (grooming, discovery, demo/retro, status, brainstorm)
  - Extract structured notes with type-specific blocks
  - Generate Structured Minutes of Meeting (MoM) or short summary
  
- **Search Mode** — Query across multiple meetings:
  - Chronological synthesis of related discussions
  - Extract decisions and action items across meetings
  - Example: "What did we discuss about feature X last month?"

**Calendar Integration:**
- Google Calendar / Microsoft Calendar context
- Participant list with emails and roles
- Agenda and attached documents
- Presentation materials

**Chaining:** Connects to Feature Task Creator (action items → Jira), Product Research (interview insights), Requirements Creator, Brainstorm Features, and Diagram Prototyper

**Trigger phrases:** "summarize meeting", "meeting notes", "action items"

---

### 10. Plugin Configurator (v1.0.0)

**Description:** Configure the Grow Product Manager plugin for your organization, including products, teams, data sources, storage location, and user preferences.

**Configuration Areas:**
- Storage location selection (Obsidian Vault or custom folder)
- Organization and product settings
- Team structure and roles
- Data source connections (Jira, Confluence, Figma, etc.)
- Knowledge library settings
- CJM funnel configuration
- Obsidian Vault integration
- Output preferences and defaults

**Trigger phrases:** "configure plugin", "set up plugin"

---

### 11. Knowledge Library (v0.4.0)

**Description:** Manage a local, curated library of knowledge sources including articles, benchmarks, research, and competitive intelligence with trust scoring and categorization.

**Features:**
- User-controlled storage location (Obsidian Vault or custom folder)
- Per-product library support
- Trust scoring and source evaluation
- Multi-mode search capability
- Categorization by topic and type
- Service skill for CJM enrichment

**Search Modes:**
- Local library search
- Confluence integration
- Google Drive integration
- Baymard (UX benchmarking database)
- Internet search

**Trigger phrases:** "add source", "search knowledge", "import sources", "show library", "what sources do we have on [topic]"

---

### 12. Template Library (v0.1.0)

**Description:** Manage a multilingual library of artifact templates (concepts, requirements, research, CJM, epics, tasks, meeting notes, presentations). Templates are stored in your Obsidian vault or custom folder, scoped per-product, and consumed automatically by other skills through the Step T — Template Resolution protocol.

**Features:**
- Three-tier scope: built-in → user-global → product-specific (with inheritance)
- Single-file multilingual storage (`<!-- lang:uk --> ... <!-- /lang:uk -->` blocks)
- Registry-backed resolution with scoring (scope, subtype, language, usage_count)
- 11 actions: list, show, add, clone, update, delete, restore, import, export, validate, rebuild-registry
- Three-tier backup: per-template archive, pack backups, manual backup/restore
- Ships with 12 built-in templates in Ukrainian + English (9 original + 3 new presentation templates added in v1.10.0)

**Trigger phrases:** "manage templates", "add template", "list templates", "template library", "clone template", "import templates", "restore template"

---

### 13. Design Bridge (v0.2.0) — NEW in v1.10.0, brand-agnostic since v1.11.0

**Description:** Orchestrator skill that turns concepts, requirements, research, and hypotheses into brand-themed design deliverables (decks, prototypes, handoffs, research enrichment). Invoked either directly ("create deck from concept", "build prototype", "run design handoff") or as an optional **Step D** hook from other skills (write-concept, requirements-creator, brainstorm-features, product-research).

**Intents:**
- **deck** — render a Google Slides-compatible `.pptx` (10×5.625") from the base template you configure in `local-context.md` (`product.base_pptx`). 4 subtypes: feature-concept (10 slides), research-highlights (10 slides), ab-test-readout (6 slides), release-readout (7 slides)
- **prototype** — lo-fi / mid-fi / hi-fi prototype brief for Figma
- **handoff** — developer-ready handoff spec (tokens, components, states, responsive breakpoints) with WCAG 2.1 AA a11y audit as blocker
- **research-enrichment** — pull UI screenshots, competitor visuals, or DS references to augment research

**Design plugin integration:** hooks 7 design skills (research-synthesis, ux-copy, design-critique, design-system, accessibility-review, design-handoff) via optional delegation, plus Figma MCP for DS sync. Your Figma DS `fileKey` lives in `local-context.md` → `product.figma.ds_file_key`.

**Brand configuration (from `local-context.md`):**
- `product.brand.primary`, `product.brand.dark`, `product.brand.font_primary`, `product.brand.font_display`
- `product.design_system_spec` — path to your DS token yaml
- `product.pptx_theme` — path to your pptx theme yaml
- `product.base_pptx` — path to your base pptx template
- Canvas defaults to 10×5.625" (Google Slides 16:9)

**A11y gates (WCAG 2.1 AA):** contrast 4.5:1 normal / 3.0:1 large, 44×44 touch targets, keyboard nav, screen-reader labels, motion controls. Handoff intent has a11y as blocker; deck intent has contrast as blocker + warnings for the rest.

**Trigger phrases:** "create deck", "design handoff", "build prototype", "research enrichment", "apply brand to deck", "run a11y audit"

---

## Skills Summary

| Skill | Version | Description |
|-------|---------|-------------|
| CJM Research | v0.3.0 | Customer Journey Map analysis and hypothesis validation |
| Product Analysis | v0.7.0 | Analyze metrics, dashboards, and A/B test results |
| Product Research | v0.7.0 | Competitive analysis, user research, market trends, UX benchmarking |
| Brainstorm Features | v0.7.0 | Interactive feature ideation with ICE scoring |
| Write Concept | v0.7.0 | Write product concept documents (PRDs) |
| Requirements Creator | v0.7.0 | Create and analyze feature requirements |
| Feature Task Creator | v0.8.0 | Create Jira tasks from requirements |
| Diagram & Prototype Creator | v0.8.0 | Visualize concepts with diagrams, prototypes, infographics |
| Meeting Processor | v0.10.0 | Process meetings and extract action items |
| Plugin Configurator | v1.0.0 | Configure plugin for your organization |
| Knowledge Library | v0.4.0 | Manage curated knowledge sources |
| Template Library | v0.1.0 | Manage multilingual artifact templates with per-product scope |
| Design Bridge | v0.2.0 | Orchestrate brand-themed decks, prototypes, handoffs, and research enrichment (brand config in `local-context.md`) |

---

## Obsidian Vault Integration (Optional)

The plugin can optionally integrate with [Obsidian](https://obsidian.md/) to create a persistent knowledge graph that accumulates artifacts over time and improves skill results.

### What it does
- Saves results of every skill (research, concepts, requirements, analyses, meetings, decisions) as structured .md files in your Obsidian Vault
- Links related artifacts with wikilinks (research → concept → requirements → A/B results)
- Searches your accumulated knowledge before starting new tasks to provide historical context
- Tracks hypothesis lifecycle: proposed → testing → validated/rejected
- Auto-generates Maps of Content (Dashboard, Product MOC, Timeline) for navigation

### Three-level operation
| Level | Condition | Capabilities |
|-------|-----------|-------------|
| L0 | No vault configured | Plugin works as before, no vault features |
| L1 | Vault path configured | Read/write artifacts, file-based search |
| L2 | Vault + Obsidian MCP | L1 + full-text search, graph traversal, backlinks |

### Multi-vault support
Configure one default vault for all products or separate vaults per product.

### Setup
Run Plugin Configurator → Obsidian Vault step, or say "connect Obsidian Vault".

---

## Persistent Data Storage

All user data is stored in a **user-controlled location** — either your Obsidian Vault (recommended) or a custom folder you choose during setup.

**How it works:**
- `~/.grow-pm/` contains only a pointer file (`.storage-pointer.yaml`) that tells the plugin where your actual data lives
- Two storage modes: **Vault** (Obsidian vault = primary storage) or **Custom** (user-chosen folder)
- When Obsidian is configured, the vault IS the primary storage — no separate copy needed
- Data persists across plugin uninstalls, reinstalls, and updates

**Storage structure (at your chosen location):**

```
<your-storage-location>/
├── local-context.md           # Plugin configuration
├── knowledge-library/         # Curated knowledge sources
│   ├── sources.md             # Source registry with trust scores
│   ├── articles/              # Imported articles
│   ├── benchmarks/            # Industry benchmarks
│   └── competitive/           # Competitor intelligence
└── Templates/                 # Multilingual artifact templates
    ├── _registry.json         # Template index with scoring metadata
    ├── _backups/              # Pack backups (last 5 before bulk ops)
    ├── _archive/              # Per-template version history (last 10)
    ├── built-in/              # Templates shipped with plugin
    ├── user/                  # User-global templates (all products)
    └── product/<product_id>/  # Product-scoped overrides
```

**Key Features:**
- User chooses storage location during onboarding (Step 0)
- Per-product Knowledge Library support
- Pointer-based resolution with recovery flow
- Change storage location at any time via Plugin Configurator
- Automatic backups before migrations
- Schema versioning for data compatibility

---

## Multilingual Artifact Templates

The plugin ships with a built-in template library that every skill uses to produce structured, consistent artifacts — concepts, requirements, research reports, CJM analyses, epics, tasks, meeting notes, and presentation outlines. Templates are multilingual (all languages live in a single `.md` file), scoped per product, and resolved automatically with user opt-in.

### How templates are used

When you invoke a skill that produces a deliverable (e.g., `write-concept`, `requirements-creator`, `product-research`, `cjm-research`, `feature-task-creator`, `product-analysis` in report mode, `diagram-prototyper` for decks, `meeting-processor` for MoMs, `brainstorm-features` when saving), the skill runs **Step T — Template Resolution** before starting the workflow. Step T:

1. Reads your `templates.preference` (`auto`, `always_ask`, or `smart` — default `smart`).
2. Queries the template registry for candidates matching the artifact type, subtype, current product, and your language.
3. Scores candidates by scope (+5 product-specific, +3 user-global, +1 built-in), subtype match, language match, and usage count.
4. Either auto-picks the top candidate, asks you to choose, or silently uses it — based on your preference.
5. Uses the template as the artifact skeleton, filling in variables as the workflow progresses.
6. Tags the saved artifact with `<!-- template: {template_id}@{version} -->` for traceability.

### Three-tier scope

| Scope | Location | Applies to |
|-------|----------|-----------|
| **built-in** | `Templates/built-in/` | All products (shipped with plugin, read-only) |
| **user-global** | `Templates/user/` | All products in your library (overrides built-in) |
| **product-specific** | `Templates/product/<product_id>/` | One product only (overrides user-global + built-in) |

### Multilingual single-file format

Every template is a single `.md` file with one YAML frontmatter block and one or more language blocks delimited by HTML comments (Obsidian-compatible):

```markdown
---
id: concept-builtin-default
version: 1.0.0
artifact_type: concept
subtype: default
scope: built-in
languages: [en]
variables: [feature_name, problem_statement, ...]
---

<!-- lang:en -->
# Concept: {{feature_name}}
## Problem
{{problem_statement}}
...
<!-- /lang:en -->

<!-- Add additional languages as needed, e.g. <!-- lang:es --> ... <!-- /lang:es --> -->
```

### Built-in templates (shipped in v1.9.0 + v1.10.0 + v1.11.0)

12 seed templates, shipped in English; localize via additional `<!-- lang:xx -->` blocks:

- `concept/default-v1` — PRD skeleton
- `requirements/default-v1` — general feature requirements
- `requirements/ab-test-v1` — A/B test spec
- `research/competitive-v1` — competitive analysis + SWOT
- `research/user-research-v1` — user research synthesis
- `cjm/funnel-v1` — CJM funnel analysis with ICE table
- `epic/default-v1` — Jira epic description
- `task/default-v1` — Jira task with DoD and AC
- `presentation/feature-v1` — 10-slide feature-concept deck outline
- `presentation/research-highlights-v1` — 10-slide research-highlights deck (**new in v1.10.0**)
- `presentation/ab-test-readout-v1` — 6-slide A/B-test readout deck (**new in v1.10.0**)
- `presentation/release-readout-v1` — 7-slide release / sprint readout deck (**new in v1.10.0**)

### Managing your library

The **Template Library** skill provides 11 actions: `list`, `show`, `add`, `clone`, `update`, `delete`, `restore`, `import`, `export`, `validate`, `rebuild-registry`. Trigger with phrases like "add template", "list templates", "clone template", "restore template", etc.

### Backup protection

Three-tier backup system to prevent data loss:

1. **Per-template archive** — every template edit saves the previous version (last 10 versions kept per template)
2. **Pack backup** — before bulk operations (import, bulk delete, migration), the whole library is snapshotted (last 5 kept)
3. **Manual backup/restore** — trigger at any time via the Template Library skill

---

## Design Bridge — Brand Integration (v1.11.0)

The plugin ships with a first-class integration with Claude's Design plugin, fronted by the `design-bridge` skill. Four upstream skills gain an optional **Step D** hook that offers to hand off results to design-bridge:

| Upstream skill | Design Bridge offers |
|----------------|----------------------|
| `write-concept` | deck (feature-concept) or prototype (lo-fi / mid-fi) |
| `requirements-creator` | handoff (a11y audit blocker) or prototype (hi-fi) or deck |
| `brainstorm-features` | lo-fi prototype for top-1 hypothesis, or brainstorm readout deck |
| `product-research` | research-highlights deck or research-enrichment (screenshots, DS refs) |

### Bring-your-own brand

All brand specifics live **outside this repo** in your own `local-context.md`. The plugin reads:

- `product.figma.ds_file_key` — Figma `fileKey` of your brand's Design System file
- `product.design_system_spec` — path to your DS tokens yaml (colors, typography, components, contrast pairs)
- `product.pptx_theme` — path to your pptx theme yaml (logical layouts → real layouts, scales, palette)
- `product.base_pptx` — path to your base pptx template (Google Slides–compatible 10×5.625" recommended)
- `product.brand.primary`, `product.brand.dark`, `product.brand.font_primary`, `product.brand.font_display` — fallback tokens when the DS yaml is unavailable or partial

See `local-context.example.md` → **Design System** section for the full schema. If no brand config is set, design-bridge falls back to a neutral default (dark text on white, 4.5:1 contrast).

### A11y gates

All design deliverables pass WCAG 2.1 AA QA before publish (see `skills/design-bridge/references/a11y-checklist.md`). Blocker rules by intent:

| Intent | A11y scope |
|--------|------------|
| deck | contrast on primary text + CTA is blocker; rest = warnings |
| prototype (lo-fi) | contrast + touch targets = warnings only |
| prototype (mid-fi / hi-fi) | full WCAG 2.1 AA blocker |
| handoff | full WCAG 2.1 AA + AAA stretches = blocker |
| research-enrichment | not audited |

---

## Shared References

The plugin includes reference materials for product management best practices and frameworks:

**Available reference files in `references/` directory:**
- Product management frameworks and templates
- PRD templates and examples
- Requirement specification formats
- User research methodologies
- A/B testing frameworks
- Competitive analysis templates
- CJM mapping guides
- Meeting templates and agendas
- `persistent-storage.md` — Pointer + User-Controlled Storage protocol
- `vault-protocol.md` — Obsidian Vault integration protocol (detection, search, save, MOC updates)
- `vault-schema.md` — Vault artifact schema (frontmatter, types, tags, folder structure, templates)
- `cjm-protocol.md` — CJM shared standards (anomaly severity, funnel impact, health score)
- `funnel-templates.md` — Standard funnel stage templates by product type
- `template-protocol.md` — Multilingual template resolution protocol (Step T-0 → T-5, scoring, fallbacks, backup invariants)

**Design Bridge references:**
- `skills/design-bridge/references/deck-subtypes.yaml` — slide-by-slide outlines for all 4 deck subtypes
- `skills/design-bridge/references/figma-playbook.md` — Figma MCP auth, rate limits, common patterns
- `skills/design-bridge/references/a11y-checklist.md` — WCAG 2.1 AA checklist + contrast pair schema

See the plugin's `references/` folder for the complete list of available materials.

---

## Version History

For detailed version history, release notes, and changelog information, see [CHANGELOG.md](CHANGELOG.md).

---

## Getting Started

1. **Install the plugin** from the Claude Code plugin marketplace
2. **Configure the plugin** using the Plugin Configurator skill
3. **Choose your storage location** — Obsidian Vault (recommended) or custom folder
4. **Connect your data sources** (Jira, Confluence, Figma, etc.)
5. **Start using skills** by typing trigger phrases in your Claude Code session

---

## Integration Points

The Grow Product Manager plugin integrates with:

- **Jira** — Task and issue management
- **Confluence** — Document collaboration and publishing
- **Figma** — Design and prototyping (configure your brand's DS `fileKey` in `local-context.md` → `product.figma.ds_file_key`)
- **Tableau / Looker** — Data visualization and metrics
- **Google Calendar / Microsoft Calendar** — Meeting context and scheduling
- **Fireflies.ai** — Meeting recording and transcription
- **Google Drive** — Document storage and collaboration
- **Obsidian** — Persistent knowledge graph (optional)
- **Claude Design plugin** — 7 design skills (user-research, research-synthesis, ux-copy, accessibility-review, design-system, design-critique, design-handoff) hooked via `design-bridge` (new in v1.10.0)
- **ChatGPT / Google Gemini** — Image and content generation (optional)

---

## Support & Documentation

For questions, issues, or feature requests, please refer to the plugin documentation or contact the plugin author.

**Plugin Author:** Andrii Siletskyi  
**Version:** 1.11.0  
**Last Updated:** April 2026
