# Grow Product Manager

The plugin acts as an AI assistant for Product Managers. The shared goal is product growth, finding improvement opportunities, solving user problems, and improving metrics. Product changes are implemented on the principle of **conscious, data-backed decisions supported by benchmarks and research results**.

The toolkit covers the full product lifecycle: from market and competitor research, writing concepts and requirements, decomposing features into tasks — to sprint planning and stakeholder reporting. Each skill integrates with Jira, Confluence, Figma, and other tools via a smart fallback connection chain.

## Current Skills

### Product Research (v0.4.0)
Conduct competitive analysis, user research, and market research using web search, uploaded files, and Confluence pages. Results are published as structured Confluence pages with actionable insights.

**Trigger phrases**: "research competitors", "analyze the market", "competitive analysis", "SWOT", "TAM SAM SOM", "user research synthesis"

### Write Concept / PRD (v0.4.0)
Create structured product concept documents (PRD) with adaptive structure based on feature type. Gathers context from conversation, Confluence, web, files, and Deep Research via external LLMs. Can leverage existing Product Research results. Publishes to Confluence with proper formatting (ToC, dividers, tables).

**Trigger phrases**: "write a concept", "create a PRD", "describe a feature", "write a spec"

### Brainstorm Features and Hypotheses (v0.4.0)
Interactive brainstorming assistant: evaluate user's existing ideas, generate new feature hypotheses with ICE scoring, benchmarks, risk assessment, and validation method recommendations. Supports MVP-phased approach. Saves results to Confluence or Google Drive.

**Trigger phrases**: "brainstorm features", "generate hypotheses", "come up with ideas", "find growth opportunities"

### Feature and Hypothesis Requirements Creator (v0.5.0)
Create structured feature requirements documents or analyze and improve existing ones, acting as an experienced Business Analyst. Supports two modes:

- **Create mode** — write requirements from scratch or based on a concept/research. Supports standard template (customizable via `local-context.md`), custom templates, A/B/A/B/C test sections, implementation approach recommendations, and flexible publishing to Confluence, Notion, or Google Docs.
- **Analyze & Improve mode** — review existing requirements, assess structure and completeness against the standard template, ask clarifying questions, propose concrete improvements, and optionally run Product Research to evaluate whether the feature is worth implementing.

**Trigger phrases**: "write requirements", "create feature spec", "A/B test requirements", "review requirements", "analyze requirements", "improve my spec", "check requirements"

### Feature Task Creator (v0.4.0)
Break down a feature into structured Jira tasks by work type (FE/BE/Android/iOS/Design/Analytics) based on Confluence requirements. Supports grooming mode, A/B test flows, automatic task linking by dependency chain, and dry run mode.

**Trigger phrases**: "create tasks for feature", "break down feature into tasks", "create Jira issues from Confluence"

### Product Analysis (v0.4.0)
Analyze product data from any source — Tableau dashboards, Google Sheets, CSV/XLSX files, screenshots, PDF reports — to find trends, anomalies, growth opportunities, and risks. Auto-generates data-backed hypotheses with ICE scoring. Supports four modes: interactive Q&A, full structured report, post-release analysis (based on Jira tasks and feature flag activation dates), and A/B test results analysis (from Tableau dashboards or user reports). Uses Python (pandas/numpy) for precise computation on tabular data. Can be invoked standalone or by other skills that need data analysis.

**Trigger phrases**: "analyze metrics", "review a dashboard", "find anomalies", "explain this data", "post-release analysis", "analyze A/B test results"

### Plugin Configurator (v0.4.0)
Configure the plugin for your organization, products, teams, and data sources. Guided setup collects all necessary context and generates `local-context.md`. Supports multiple organizations and products simultaneously. Four modes: Onboarding (full setup), Update (edit specific sections), Validate (check integrations and context completeness), View (display and edit config inline). Auto-triggers when any skill detects missing configuration. Includes MCP auto-discovery — proactively scans available Jira projects, Confluence spaces, and team members.

**Trigger phrases**: "configure plugin", "set up plugin", "add a product", "update configuration", "validate setup", "show config"

## Planned Skills Roadmap

| Phase | Skill | Description | Status |
|-------|-------|-------------|--------|
| 1 | Product Research | Competitive, user & market research → Confluence | ✅ Done |
| 2 | Write Concept / PRD | Adaptive PRD from idea to Confluence page | ✅ Done |
| 3 | Brainstorm Features and Hypotheses | Interactive brainstorm with ICE scoring & benchmarks | ✅ Done |
| 4 | Feature and Hypothesis Requirements Creator | Structured requirements as experienced BA → Confluence/Notion/Google Docs | ✅ Done |
| 5 | Feature Task Creator | Confluence requirements → Jira tasks by team | ✅ Done |
| 6 | Product Analysis | Data analysis with hypothesis generation from any data source | ✅ Done |
| 7 | Plugin Configurator | Guided setup for organizations, products, teams, data sources | ✅ Done |
| 8 | Sprint Planning | Plan sprints with capacity & priority estimation | Planned |
| 9 | Stakeholder Update | Generate status reports for different audiences | Planned |
| 10 | Design Review | Pull Figma designs for review and handoff specs | Planned |

## Integrations

| Tool | Purpose | Status |
|------|---------|--------|
| Jira | Task management, sprint tracking | Connected via Atlassian MCP |
| Confluence | Documentation, research output | Connected via Atlassian MCP |
| Figma | Design context and screenshots | Connected via Figma MCP |
| Notion | Alternative publishing destination | Connected via Notion MCP |
| Google Docs | Alternative publishing destination | Via MCP registry / browser |
| Tableau | Product metrics and dashboards | Via Product Analysis skill (browser) |
| Google Sheets | Metrics exports and shared data | Via MCP registry / browser |
| Web Search | External research data | Built-in |

## Data Confidentiality Policy

Data retrieved from Tableau and other analytics platforms, internal research materials, and any data subject to commercial confidentiality **must not**:

- Be used to train any LLM
- Be shared with third parties in any form

This data is used exclusively by the current user within their own account and for their own tasks. Detailed rules are defined in `references/data-policy.md`.

## Smart Integration Strategy

All skills follow a three-step fallback chain when connecting to external tools:

1. **MCP connector** — if a connector for the product is already in the session, use it directly
2. **MCP registry search** — if not, search for an available MCP server and suggest installing it
3. **Browser fallback** — if no MCP option exists (or lacks needed features), use Claude in Chrome to interact with the web UI

This means the plugin works even if not all connectors are set up — it adapts to what's available.

## Setup

This plugin uses MCP connectors already available in your Cowork session (Atlassian, Figma). For products without a connector, the plugin will automatically suggest one from the registry or fall back to using the browser.

## Local Context Configuration

This plugin supports organization-specific configuration via a `local-context.md` file. This file contains internal URLs, project names, product names, and other organization-specific details that the plugin uses to adapt its behavior.

**Setup:**
1. Copy `local-context.example.md` to `local-context.md`
2. Fill in your organization's values (Jira project keys, Tableau URLs, Confluence template URLs, product names, etc.)
3. `local-context.md` is gitignored — it stays local and is never committed

Skills that use local context: Product Analysis (A/B test dashboards), Requirements Creator (template URLs, locales), Feature Task Creator (project examples).

## Versioning

Each skill carries its own version (`version:` field in SKILL.md frontmatter). The plugin version in `plugin.json` reflects the highest-impact change across all skills. All changes are documented in [CHANGELOG.md](./CHANGELOG.md).

Version bump rules:
- **PATCH** (x.x.X) — wording fix, small content addition, formatting change
- **MINOR** (x.X.0) — new step, new section, significant workflow addition, new mode
- **MAJOR** (X.0.0) — full workflow restructure, breaking change

## Author

Andrii Siletskyi
