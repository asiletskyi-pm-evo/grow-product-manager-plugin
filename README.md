# Grow Product Manager

**Version:** 1.7.0

AI assistant plugin for Product Managers. Integrates with Jira, Confluence, Figma, Tableau, and other tools to streamline product management workflows.

---

## Overview

The Grow Product Manager plugin is a comprehensive AI-powered toolkit designed to accelerate product management workflows. It provides skills for research, analysis, brainstorming, documentation, task creation, and visualization across your entire product lifecycle.

---

## Skills

### 1. CJM Research (v0.2.0) — NEW

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

### 2. Product Analysis (v0.6.0)

**Description:** Analyze product data with interactive dashboards, metrics, and reports to find trends and growth opportunities.

**Modes:**
- **Interactive Q&A** — Ask questions about your metrics
- **Full Report** — Comprehensive analysis of all available data
- **Post-Release** — Analyze metrics before and after a feature release
- **A/B Test Results** — Evaluate test outcomes and statistical significance
- **CJM Funnel Analysis** — Analyze customer behavior across funnel stages

**Trigger phrases:** "analyze metrics", "review a dashboard", "find anomalies", "post-release analysis", "analyze A/B test results", "CJM funnel analysis"

---

### 3. Product Research (v0.5.0)

**Description:** Conduct competitive analysis, user research, market research, and UX benchmarking with Knowledge Library integration for data-backed insights.

**Research Types:**
- Competitive analysis and feature comparison
- User research synthesis and insights
- Market trends and opportunity identification
- UX benchmark research against industry standards

**Trigger phrases:** "research competitors", "analyze the market", "competitive analysis", "find market trends", "UX benchmark research"

---

### 4. Brainstorm Features (v0.5.0)

**Description:** Interactive brainstorming for product features and growth opportunities with ICE scoring and CJM hypothesis generation.

**Features:**
- Feature ideation and scoring (Impact, Confidence, Ease)
- CJM Hypotheses mode with funnel impact calculation
- Growth opportunity identification
- Prioritization framework

**Trigger phrases:** "brainstorm features", "generate hypotheses", "find growth opportunities", "CJM hypotheses"

---

### 5. Write Concept (v0.4.0)

**Description:** Write detailed product concept documents (PRDs) from ideas, problem statements, or research findings.

**Outputs:** Full PRD with objectives, user stories, success metrics, and implementation notes

**Trigger phrases:** "write a concept", "create a PRD"

---

### 6. Requirements Creator (v0.5.1)

**Description:** Create structured feature requirements or analyze and improve existing requirement documents using business analyst expertise.

**Capabilities:**
- Generate detailed requirements from concepts
- Analyze and improve existing specs
- User story generation
- Acceptance criteria definition

**Trigger phrases:** "write requirements", "create feature spec", "review requirements"

---

### 7. Feature Task Creator (v0.7.0)

**Description:** Automatically create Jira tasks and issues from requirements, breaking down work into actionable engineering tasks.

**Capabilities:**
- Parse requirements and decompose into tasks
- Create Jira issues with proper fields and links
- Estimate complexity and effort
- Set up dependencies and sprint planning

**Trigger phrases:** "create tasks for a feature", "create Jira issues"

---

### 8. Diagram & Prototype Creator (v0.7.0)

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

### 9. Meeting Processor (v0.9.0)

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

### 10. Plugin Configurator (v0.9.0)

**Description:** Configure the Grow Product Manager plugin for your organization, including products, teams, data sources, and user preferences.

**Configuration Areas:**
- Organization and product settings
- Team structure and roles
- Data source connections (Jira, Confluence, Figma, etc.)
- Knowledge library settings
- Output preferences and defaults

**Trigger phrases:** "configure plugin", "set up plugin"

---

### 11. Knowledge Library (v0.3.0) — NEW

**Description:** Manage a local, curated library of knowledge sources including articles, benchmarks, research, and competitive intelligence with trust scoring and categorization.

**Features:**
- Local storage in `~/.grow-pm/knowledge-library/`
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

## Skills Summary

| Skill | Version | Description |
|-------|---------|-------------|
| CJM Research | v0.2.0 | Customer Journey Map analysis and hypothesis validation (NEW) |
| Product Analysis | v0.6.0 | Analyze metrics, dashboards, and A/B test results |
| Product Research | v0.5.0 | Competitive analysis, user research, market trends, UX benchmarking |
| Brainstorm Features | v0.5.0 | Interactive feature ideation with ICE scoring |
| Write Concept | v0.4.0 | Write product concept documents (PRDs) |
| Requirements Creator | v0.5.1 | Create and analyze feature requirements |
| Feature Task Creator | v0.7.0 | Create Jira tasks from requirements |
| Diagram & Prototype Creator | v0.7.0 | Visualize concepts with diagrams, prototypes, infographics |
| Meeting Processor | v0.9.0 | Process meetings and extract action items |
| Plugin Configurator | v0.9.0 | Configure plugin for your organization |
| Knowledge Library | v0.3.0 | Manage curated knowledge sources (NEW) |

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

All user configuration, templates, and knowledge library files are stored in `~/.grow-pm/` in the user's home directory. This data persists across plugin uninstalls, reinstalls, and updates.

**Directory Structure:**

```
~/.grow-pm/
├── config/                    # Configuration files
│   ├── plugin-settings.json   # Plugin-wide settings
│   ├── products.json          # Product configurations
│   └── teams.json             # Team and role mappings
├── knowledge-library/         # Curated knowledge sources
│   ├── sources.json           # Source registry with trust scores
│   ├── articles/              # Imported articles
│   ├── benchmarks/            # Industry benchmarks
│   └── competitive/           # Competitor intelligence
├── vault/                     # Obsidian Vault artifacts (if configured)
│   ├── dashboard/             # Dashboards and MOCs
│   ├── products/              # Product-specific artifacts
│   ├── research/              # Research and analysis
│   ├── concepts/              # Concept documents and PRDs
│   ├── requirements/          # Requirement specs
│   ├── decisions/             # Decisions and A/B test results
│   └── hypotheses/            # Hypotheses and lifecycle tracking
└── templates/                 # Custom templates and outputs
```

**Key Features:**
- Configuration files in `~/.grow-pm/config/`
- Knowledge library in `~/.grow-pm/knowledge-library/`
- Vault artifacts in `~/.grow-pm/vault/` (optional)
- Automatic backups before migrations
- Schema versioning for data compatibility
- Legacy data migration on first launch

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
- `vault-protocol.md` — Obsidian Vault integration protocol (detection, search, save, MOC updates)
- `vault-schema.md` — Vault artifact schema (frontmatter, types, tags, folder structure, templates)

See the plugin's `references/` folder for the complete list of available materials.

---

## Version History

For detailed version history, release notes, and changelog information, see [CHANGELOG.md](CHANGELOG.md).

---

## Getting Started

1. **Install the plugin** from the Claude Code plugin marketplace
2. **Configure the plugin** using the Plugin Configurator skill
3. **Connect your data sources** (Jira, Confluence, Figma, etc.)
4. **Start using skills** by typing trigger phrases in your Claude Code session

---

## Integration Points

The Grow Product Manager plugin integrates with:

- **Jira** — Task and issue management
- **Confluence** — Document collaboration and publishing
- **Figma** — Design and prototyping
- **Tableau / Looker** — Data visualization and metrics
- **Google Calendar / Microsoft Calendar** — Meeting context and scheduling
- **Fireflies.ai** — Meeting recording and transcription
- **Google Drive** — Document storage and collaboration
- **Obsidian** — Persistent knowledge graph (optional)
- **ChatGPT / Google Gemini** — Image and content generation (optional)

---

## Support & Documentation

For questions, issues, or feature requests, please refer to the plugin documentation or contact the plugin author.

**Plugin Author:** Andrii  
**Version:** 1.7.0  
**Last Updated:** April 2026
# Grow Product Manager

**Version:** 1.5.0

AI-powered plugin for Product Managers that turns Claude into your daily co-pilot — from market research and CJM analysis to writing PRDs, creating Jira tasks, and processing meetings.

---

## Why Grow Product Manager?

Product Managers juggle dozens of tools and context-switch constantly between research, analysis, writing specs, breaking tasks into stories, and keeping stakeholders aligned. Grow Product Manager solves this by combining **11 specialized skills** into a single conversational interface that connects to the tools you already use.

### Key Benefits

**End-to-End Product Workflow.** Cover your entire product lifecycle without leaving Claude: research the market, analyze funnels, brainstorm features, write a PRD, generate requirements, create Jira tasks, and summarize your meetings — all in one place.

**Data-Driven Decision Making.** Analyze Tableau dashboards, Google Sheets, and CSV exports conversationally. Detect funnel anomalies, evaluate A/B tests with statistical significance, and generate hypotheses scored by ICE framework with funnel impact multipliers.

**Smart Skill Chaining.** Skills automatically delegate to each other when it makes sense. A meeting summary can trigger task creation in Jira; CJM research enriches hypotheses with data from your Knowledge Library; a concept doc pulls in competitive research you've already done.

**Persistent Context.** Your configuration, knowledge library, and team structure live in `~/.grow-pm/` and survive plugin reinstalls and updates. The plugin remembers your products, team roles, OKRs, and data sources across sessions.

**Deep Integrations.** Works with Jira, Confluence, Figma, Tableau, Fireflies.ai, Google Calendar, Google Drive, Notion, and more — via MCP connectors or browser fallback.

**Confidentiality First.** Sensitive analytics and internal metrics stay local. Infographics with confidential data are generated using built-in Mermaid/HTML engines, never sent to external LLMs.

### What Makes It Different

Unlike generic PM assistants, Grow Product Manager is built around the **Customer Journey Map (CJM)** as a central framework. Every skill — from brainstorming to analysis — can be viewed through the lens of your funnel stages, making it easy to tie any feature idea or metric back to a specific point in your customer journey.

---

## Typical Use Cases

### Daily Workflow
- **"Summarize my meeting from yesterday"** — Meeting Processor fetches the recording from Fireflies, auto-classifies it (grooming, discovery, brainstorm…), extracts action items, and can immediately create Jira tasks from them.
- **"What happened with our conversion after the last release?"** — Product Analysis pulls your Tableau dashboard, compares pre- and post-release metrics, and highlights statistically significant changes.
- **"Research how competitors handle onboarding"** — Product Research runs a competitive analysis, checks your Knowledge Library for saved benchmarks, and produces a structured brief.

### Weekly / Sprint Cadence
- **"Analyze our CJM and find funnel anomalies"** — CJM Research loads your funnel data stage-by-stage, detects drops, classifies severity, and generates prioritized improvement hypotheses.
- **"Brainstorm features for improving checkout conversion"** — Brainstorm Features generates ideas with ICE scoring, connects them to specific CJM stages, and categorizes as low-hanging fruit vs. structural changes.
- **"Write a concept for the new referral program"** — Write Concept produces a full PRD with objectives, user stories, success metrics, and links to related research.

### Feature Development Cycle
- **"Write detailed requirements for the loyalty program"** — Requirements Creator generates structured specs with user stories, acceptance criteria, and technical requirements.
- **"Create Jira tasks from the requirements page"** — Feature Task Creator reads the requirements, decomposes them into FE/BE/Mobile/Design/Analytics tasks, estimates effort, and creates issues in Jira with proper links.
- **"Create a user flow diagram for the checkout redesign"** — Diagram Prototyper generates Mermaid flowcharts, HTML infographics, or delegates to Figma/Gemini depending on the visualization type.

### Strategic Work
- **"Run a full CJM health check across platforms"** — CJM Research performs a comprehensive analysis: anomaly detection, hypothesis generation, verification, risk assessment, and builds a prioritized backlog.
- **"What sources do we have on subscription pricing?"** — Knowledge Library searches your local curated collection, Confluence, Google Drive, and Baymard for relevant benchmarks and articles.

---

## Installation & Setup Guide

### Step 1: Install the Plugin

**First-time installation:**
1. Open the **Claude Desktop** app and go to **Settings → Plugins** (or use the plugin marketplace).
2. Search for **"Grow Product Manager"**.
3. Click **Install** and wait for the plugin to load.
4. Restart Claude Desktop if prompted.

**Updating the plugin:**
1. Go to **Settings → Plugins → Grow Product Manager**.
2. If an update is available, click **Update**.
3. Your data in `~/.grow-pm/` is preserved automatically — nothing is lost during updates.
4. After update, run `configure plugin → validate` to verify all connections still work.

**Reinstalling after removal:**
1. Install the plugin as described above.
2. On first launch, the Plugin Configurator detects existing data in `~/.grow-pm/` and offers a **Reinstall/Migration** mode.
3. Choose "Reinstall" to restore your previous configuration, or "Fresh Start" to begin from scratch.

### Step 2: Initial Configuration (Plugin Configurator)

After installation, the very first thing to do is configure the plugin. Type:

> **"configure plugin"** or **"set up plugin"**

The Plugin Configurator will guide you through **Onboarding mode** with these steps:

1. **Organization Info** — Set your company name, product names, and product descriptions.
2. **Team Structure** — Add team members with their roles (PM, Designer, Engineer, Analyst, etc.) and Jira account IDs for task assignment.
3. **Products & OKRs** — Define your products, their current objectives, and key results you're tracking.
4. **Data Sources** — Connect the tools your team uses (see Step 3 below).
5. **CJM Configuration** — Set up your funnel stages, dashboard URLs per stage, baseline conversion rates, and alert thresholds.
6. **Output Preferences** — Choose default publishing destinations (Confluence space, Notion workspace, local files).

The configuration is saved to `~/.grow-pm/local-context.md` and is automatically loaded by every skill.

### Step 3: Connect Your Tools (MCP Connectors)

To get maximum value from the plugin, connect the following integrations. Each one is set up through Claude Desktop's **Settings → Connectors** section.

#### Essential Connectors

| Connector | What It Enables | How to Connect |
|-----------|----------------|----------------|
| **Atlassian (Jira + Confluence)** | Create tasks, read requirements, publish documents | Settings → Connectors → Atlassian → Authenticate with your Atlassian account |
| **Figma** | Pull design context, screenshots, component specs | Settings → Connectors → Figma → Authenticate with your Figma account |

#### Recommended Connectors

| Connector | What It Enables | How to Connect |
|-----------|----------------|----------------|
| **Fireflies.ai** | Fetch meeting transcripts and recordings automatically | Settings → Connectors → Fireflies → Authenticate with API key |
| **Google Calendar** | Enrich meeting notes with participant lists, agendas, and attachments | Settings → Connectors → Google Calendar → Authenticate with Google |
| **Notion** | Publish documents and notes to Notion workspaces | Settings → Connectors → Notion → Authenticate with Notion |
| **Google Drive** | Access shared documents, feedback spreadsheets, research files | Settings → Connectors → Google Drive → Authenticate with Google |

#### Optional Connectors

| Connector | What It Enables |
|-----------|----------------|
| **Amplitude** | Product analytics data for deeper metric analysis |
| **Pendo** | User engagement and product usage data |
| **Linear / ClickUp / Monday** | Alternative task management (instead of Jira) |
| **Microsoft Calendar** | Meeting context (alternative to Google Calendar) |

### Step 4: Set Up Knowledge Library

The Knowledge Library is your personal curated research database. To set it up:

1. Type **"show library"** to see the current state.
2. Add your existing sources: **"add source [URL or description]"** — the library will categorize, score trust, and store it.
3. Import in bulk by pointing to a Confluence space or Google Drive folder with your research materials.
4. Configure Baymard integration if you have access (for UX benchmarking data).

The library is stored in `~/.grow-pm/knowledge-library/` and is automatically used by CJM Research, Product Research, and Brainstorm Features skills.

### Step 5: Set Up Obsidian Vault (Optional — Advanced)

For teams that use Obsidian for knowledge management, the plugin supports integration with Obsidian vaults for persistent knowledge graph storage.

1. Ensure Obsidian is installed and your vault is accessible on your local file system.
2. During Plugin Configurator setup, specify the path to your Obsidian vault.
3. The plugin will use the vault for storing and linking research notes, meeting summaries, and concept documents.
4. Vault configuration is cached in `~/.grow-pm/obsidian-vaults/`.

### Step 6: Validate Your Setup

After completing the setup, run a validation check:

> **"configure plugin → validate"** or **"validate setup"**

This will:
- Test all MCP connections (Jira, Confluence, Figma, etc.)
- Verify your configuration file is complete and well-formed
- Check that the Knowledge Library is accessible
- Report any missing or broken connections with fix suggestions

### Quick Start After Setup

Once everything is configured, try these commands to verify everything works:

1. **"show config"** — View your current configuration
2. **"analyze CJM → anomalies"** — Run a quick funnel anomaly scan
3. **"search knowledge [your topic]"** — Test the Knowledge Library
4. **"summarize meeting"** — Process a recent meeting (requires Fireflies connector)

---

## Skills

### 1. CJM Research (v0.1.0) — NEW

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

### 2. Product Analysis (v0.5.0)

**Description:** Analyze product data with interactive dashboards, metrics, and reports to find trends and growth opportunities.

**Modes:**
- **Interactive Q&A** — Ask questions about your metrics
- **Full Report** — Comprehensive analysis of all available data
- **Post-Release** — Analyze metrics before and after a feature release
- **A/B Test Results** — Evaluate test outcomes and statistical significance
- **CJM Funnel Analysis** — Analyze customer behavior across funnel stages

**Trigger phrases:** "analyze metrics", "review a dashboard", "find anomalies", "post-release analysis", "analyze A/B test results", "CJM funnel analysis"

---

### 3. Product Research (v0.5.0)

**Description:** Conduct competitive analysis, user research, market research, and UX benchmarking with Knowledge Library integration for data-backed insights.

**Research Types:**
- Competitive analysis and feature comparison
- User research synthesis and insights
- Market trends and opportunity identification
- UX benchmark research against industry standards

**Trigger phrases:** "research competitors", "analyze the market", "competitive analysis", "find market trends", "UX benchmark research"

---

### 4. Brainstorm Features (v0.5.0)

**Description:** Interactive brainstorming for product features and growth opportunities with ICE scoring and CJM hypothesis generation.

**Features:**
- Feature ideation and scoring (Impact, Confidence, Ease)
- CJM Hypotheses mode with funnel impact calculation
- Growth opportunity identification
- Prioritization framework

**Trigger phrases:** "brainstorm features", "generate hypotheses", "find growth opportunities", "CJM hypotheses"

---

### 5. Write Concept (v0.5.0)

**Description:** Write detailed product concept documents (PRDs) from ideas, problem statements, or research findings.

**Outputs:** Full PRD with objectives, user stories, success metrics, and implementation notes

**Trigger phrases:** "write a concept", "create a PRD"

---

### 6. Requirements Creator (v0.5.1)

**Description:** Create structured feature requirements or analyze and improve existing requirement documents using business analyst expertise.

**Capabilities:**
- Generate detailed requirements from concepts
- Analyze and improve existing specs
- User story generation
- Acceptance criteria definition

**Trigger phrases:** "write requirements", "create feature spec", "review requirements"

---

### 7. Feature Task Creator (v0.7.0)

**Description:** Automatically create Jira tasks and issues from requirements, breaking down work into actionable engineering tasks.

**Capabilities:**
- Parse requirements and decompose into tasks
- Create Jira issues with proper fields and links
- Estimate complexity and effort
- Set up dependencies and sprint planning

**Trigger phrases:** "create tasks for a feature", "create Jira issues"

---

### 8. Diagram & Prototype Creator (v0.7.0)

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

### 9. Meeting Processor (v0.9.0)

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

### 10. Plugin Configurator (v0.7.0)

**Description:** Configure the Grow Product Manager plugin for your organization, including products, teams, data sources, and user preferences.

**Modes:**
- **Onboarding** — Initial setup with guided step-by-step configuration
- **Reinstall/Migration** — Recover existing data or migrate from legacy locations
- **Update** — Edit specific sections (add product, update team, change URLs, add OKRs)
- **Validate** — Test all MCP connections and verify setup completeness
- **View** — Display current configuration

**Configuration Areas:**
- Organization and product settings
- Team structure and roles
- Data source connections (Jira, Confluence, Figma, etc.)
- CJM Configuration (funnel templates, stage dashboards, baselines, thresholds)
- Knowledge library settings
- Output preferences and defaults

**Trigger phrases:** "configure plugin", "set up plugin", "validate setup", "show config"

---

### 11. Knowledge Library (v0.2.0) — NEW

**Description:** Manage a local, curated library of knowledge sources including articles, benchmarks, research, and competitive intelligence with trust scoring and categorization.

**Features:**
- Local storage in `~/.grow-pm/knowledge-library/`
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

## Skills Summary

| Skill | Version | Description |
|-------|---------|-------------|
| CJM Research | v0.1.0 | Customer Journey Map analysis and hypothesis validation (NEW) |
| Product Analysis | v0.5.0 | Analyze metrics, dashboards, and A/B test results |
| Product Research | v0.5.0 | Competitive analysis, user research, market trends, UX benchmarking |
| Brainstorm Features | v0.5.0 | Interactive feature ideation with ICE scoring |
| Write Concept | v0.5.0 | Write product concept documents (PRDs) |
| Requirements Creator | v0.5.1 | Create and analyze feature requirements |
| Feature Task Creator | v0.7.0 | Create Jira tasks from requirements |
| Diagram & Prototype Creator | v0.7.0 | Visualize concepts with diagrams, prototypes, infographics |
| Meeting Processor | v0.9.0 | Process meetings and extract action items |
| Plugin Configurator | v0.7.0 | Configure plugin for your organization |
| Knowledge Library | v0.2.0 | Manage curated knowledge sources (NEW) |

---

## Persistent Data Storage

All user configuration, templates, and knowledge library files are stored in `~/.grow-pm/` in the user's home directory. This data persists across plugin uninstalls, reinstalls, and updates.

**Directory Structure:**

```
~/.grow-pm/
├── local-context.md              # Main configuration (products, teams, tools, OKRs)
├── .schema-version               # Schema version marker
├── template-library/             # User's custom templates
├── knowledge-library/            # Curated knowledge sources
│   ├── library.md                # Master source index
│   ├── categories.md             # Category definitions
│   ├── trust-scores.yaml         # Trust scoring metadata
│   ├── sources/                  # Individual source details
│   └── health-checks/            # CJM health-check snapshots
├── backups/                      # Auto-backups before migrations (keeps last 3)
└── obsidian-vaults/              # Vault configuration cache (optional)
```

**Key Features:**
- Automatic backups before migrations (keeps last 3)
- Schema versioning for data compatibility
- Legacy data migration on first launch
- Auto-detection of existing config on reinstall

---

## Integration Points

The Grow Product Manager plugin integrates with:

- **Jira** — Task and issue management
- **Confluence** — Document collaboration and publishing
- **Figma** — Design and prototyping
- **Tableau / Looker** — Data visualization and metrics
- **Google Calendar / Microsoft Calendar** — Meeting context and scheduling
- **Fireflies.ai** — Meeting recording and transcription
- **Google Drive** — Document storage and collaboration
- **Notion** — Publishing and knowledge management
- **ChatGPT / Google Gemini** — Image and content generation (optional)

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

See the plugin's `references/` folder for the complete list of available materials.

---

## Version History

For detailed version history, release notes, and changelog information, see [CHANGELOG.md](CHANGELOG.md).

---

## Support & Documentation

For questions, issues, or feature requests, please refer to the plugin documentation or contact the plugin author.

**Plugin Author:** Andrii
**GitHub:** [grow-product-manager-plugin](https://github.com/asiletskyi-pm-evo/grow-product-manager-plugin)
**Version:** 1.5.0
**Last Updated:** April 2026# Grow Product Manager

**Version:** 1.6.0

AI assistant plugin for Product Managers. Integrates with Jira, Confluence, Figma, Tableau, and other tools to streamline product management workflows.

---

## Overview

The Grow Product Manager plugin is a comprehensive AI-powered toolkit designed to accelerate product management workflows. It provides skills for research, analysis, brainstorming, documentation, task creation, and visualization across your entire product lifecycle.

---

## Skills

### 1. CJM Research (v0.1.0) — NEW

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

### 2. Product Analysis (v0.5.0)

**Description:** Analyze product data with interactive dashboards, metrics, and reports to find trends and growth opportunities.

**Modes:**
- **Interactive Q&A** — Ask questions about your metrics
- **Full Report** — Comprehensive analysis of all available data
- **Post-Release** — Analyze metrics before and after a feature release
- **A/B Test Results** — Evaluate test outcomes and statistical significance
- **CJM Funnel Analysis** — Analyze customer behavior across funnel stages

**Trigger phrases:** "analyze metrics", "review a dashboard", "find anomalies", "post-release analysis", "analyze A/B test results", "CJM funnel analysis"

---

### 3. Product Research (v0.5.0)

**Description:** Conduct competitive analysis, user research, market research, and UX benchmarking with Knowledge Library integration for data-backed insights.

**Research Types:**
- Competitive analysis and feature comparison
- User research synthesis and insights
- Market trends and opportunity identification
- UX benchmark research against industry standards

**Trigger phrases:** "research competitors", "analyze the market", "competitive analysis", "find market trends", "UX benchmark research"

---

### 4. Brainstorm Features (v0.5.0)

**Description:** Interactive brainstorming for product features and growth opportunities with ICE scoring and CJM hypothesis generation.

**Features:**
- Feature ideation and scoring (Impact, Confidence, Ease)
- CJM Hypotheses mode with funnel impact calculation
- Growth opportunity identification
- Prioritization framework

**Trigger phrases:** "brainstorm features", "generate hypotheses", "find growth opportunities", "CJM hypotheses"

---

### 5. Write Concept (v0.4.0)

**Description:** Write detailed product concept documents (PRDs) from ideas, problem statements, or research findings.

**Outputs:** Full PRD with objectives, user stories, success metrics, and implementation notes

**Trigger phrases:** "write a concept", "create a PRD"

---

### 6. Requirements Creator (v0.5.1)

**Description:** Create structured feature requirements or analyze and improve existing requirement documents using business analyst expertise.

**Capabilities:**
- Generate detailed requirements from concepts
- Analyze and improve existing specs
- User story generation
- Acceptance criteria definition

**Trigger phrases:** "write requirements", "create feature spec", "review requirements"

---

### 7. Feature Task Creator (v0.7.0)

**Description:** Automatically create Jira tasks and issues from requirements, breaking down work into actionable engineering tasks.

**Capabilities:**
- Parse requirements and decompose into tasks
- Create Jira issues with proper fields and links
- Estimate complexity and effort
- Set up dependencies and sprint planning

**Trigger phrases:** "create tasks for a feature", "create Jira issues"

---

### 8. Diagram & Prototype Creator (v0.7.0)

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

### 9. Meeting Processor (v0.9.0)

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

### 10. Plugin Configurator (v0.7.0)

**Description:** Configure the Grow Product Manager plugin for your organization, including products, teams, data sources, and user preferences.

**Configuration Areas:**
- Organization and product settings
- Team structure and roles
- Data source connections (Jira, Confluence, Figma, etc.)
- Knowledge library settings
- Output preferences and defaults

**Trigger phrases:** "configure plugin", "set up plugin"

---

### 11. Knowledge Library (v0.2.0) — NEW

**Description:** Manage a local, curated library of knowledge sources including articles, benchmarks, research, and competitive intelligence with trust scoring and categorization.

**Features:**
- Local storage in `~/.grow-pm/knowledge-library/`
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

## Skills Summary

| Skill | Version | Description |
|-------|---------|-------------|
| CJM Research | v0.1.0 | Customer Journey Map analysis and hypothesis validation (NEW) |
| Product Analysis | v0.5.0 | Analyze metrics, dashboards, and A/B test results |
| Product Research | v0.5.0 | Competitive analysis, user research, market trends, UX benchmarking |
| Brainstorm Features | v0.5.0 | Interactive feature ideation with ICE scoring |
| Write Concept | v0.4.0 | Write product concept documents (PRDs) |
| Requirements Creator | v0.5.1 | Create and analyze feature requirements |
| Feature Task Creator | v0.7.0 | Create Jira tasks from requirements |
| Diagram & Prototype Creator | v0.7.0 | Visualize concepts with diagrams, prototypes, infographics |
| Meeting Processor | v0.9.0 | Process meetings and extract action items |
| Plugin Configurator | v0.7.0 | Configure plugin for your organization |
| Knowledge Library | v0.2.0 | Manage curated knowledge sources (NEW) |

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

All user configuration, templates, and knowledge library files are stored in `~/.grow-pm/` in the user's home directory. This data persists across plugin uninstalls, reinstalls, and updates.

**Directory Structure:**

```
~/.grow-pm/
├── config/                    # Configuration files
│   ├── plugin-settings.json   # Plugin-wide settings
│   ├── products.json          # Product configurations
│   └── teams.json             # Team and role mappings
├── knowledge-library/         # Curated knowledge sources
│   ├── sources.json           # Source registry with trust scores
│   ├── articles/              # Imported articles
│   ├── benchmarks/            # Industry benchmarks
│   └── competitive/           # Competitor intelligence
├── vault/                     # Obsidian Vault artifacts (if configured)
│   ├── dashboard/             # Dashboards and MOCs
│   ├── products/              # Product-specific artifacts
│   ├── research/              # Research and analysis
│   ├── concepts/              # Concept documents and PRDs
│   ├── requirements/          # Requirement specs
│   ├── decisions/             # Decisions and A/B test results
│   └── hypotheses/            # Hypotheses and lifecycle tracking
└── templates/                 # Custom templates and outputs
```

**Key Features:**
- Configuration files in `~/.grow-pm/config/`
- Knowledge library in `~/.grow-pm/knowledge-library/`
- Vault artifacts in `~/.grow-pm/vault/` (optional)
- Automatic backups before migrations
- Schema versioning for data compatibility
- Legacy data migration on first launch

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
- `vault-protocol.md` — Obsidian Vault integration protocol (detection, search, save, MOC updates)
- `vault-schema.md` — Vault artifact schema (frontmatter, types, tags, folder structure, templates)

See the plugin's `references/` folder for the complete list of available materials.

---

## Version History

For detailed version history, release notes, and changelog information, see [CHANGELOG.md](CHANGELOG.md).

---

## Getting Started

1. **Install the plugin** from the Claude Code plugin marketplace
2. **Configure the plugin** using the Plugin Configurator skill
3. **Connect your data sources** (Jira, Confluence, Figma, etc.)
4. **Start using skills** by typing trigger phrases in your Claude Code session

---

## Integration Points

The Grow Product Manager plugin integrates with:

- **Jira** — Task and issue management
- **Confluence** — Document collaboration and publishing
- **Figma** — Design and prototyping
- **Tableau / Looker** — Data visualization and metrics
- **Google Calendar / Microsoft Calendar** — Meeting context and scheduling
- **Fireflies.ai** — Meeting recording and transcription
- **Google Drive** — Document storage and collaboration
- **Obsidian** — Persistent knowledge graph (optional)
- **ChatGPT / Google Gemini** — Image and content generation (optional)

---

## Support & Documentation

For questions, issues, or feature requests, please refer to the plugin documentation or contact the plugin author.

**Plugin Author:** Andrii  
**Version:** 1.6.0  
**Last Updated:** April 2026
