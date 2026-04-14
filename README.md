# Grow Product Manager

**Version:** 1.5.0

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
└── templates/                 # Custom templates and outputs
```

**Key Features:**
- Configuration files in `~/.grow-pm/config/`
- Knowledge library in `~/.grow-pm/knowledge-library/`
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
- **ChatGPT / Google Gemini** — Image and content generation (optional)

---

## Support & Documentation

For questions, issues, or feature requests, please refer to the plugin documentation or contact the plugin author.

**Plugin Author:** Andrii  
**Version:** 1.5.0  
**Last Updated:** April 2026
