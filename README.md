# Grow Product Manager

Плагін виконує роль асистента Product Manager. Спільна ціль — розвиток продуктів, пошук точок росту, вирішення проблем користувачів та покращення метрик. Реалізація продуктових змін відбувається за принципом **свідомих зважених рішень, підкріплених даними, бенчмарками та результатами досліджень**.

Інструментарій охоплює весь продуктовий цикл: від дослідження ринку та конкурентів, написання концепцій і вимог, декомпозиції фіч на задачі — до спринт-планування та звітності для стейкхолдерів. Кожен скіл інтегрується з Jira, Confluence, Figma та іншими інструментами через розумний ланцюжок підключення.

## Current Skills

### Product Research (v0.1.0)
Conduct competitive analysis, user research, and market research using web search, uploaded files, and Confluence pages. Results are published as structured Confluence pages with actionable insights.

**Trigger phrases**: "research competitors", "analyze the market", "competitive analysis", "SWOT", "TAM SAM SOM", "user research synthesis", "аналіз конкурентів", "дослідження ринку"

### Write Concept / PRD (v0.1.0)
Create structured product concept documents (PRD) with adaptive structure based on feature type. Gathers context from conversation, Confluence, web, files, and Deep Research via external LLMs. Can leverage existing Product Research results. Publishes to Confluence with proper formatting (ToC, dividers, tables).

**Trigger phrases**: "write a concept", "create a PRD", "describe a feature", "сформувати концепцію", "написати PRD", "описати фічу", "створити концепт"

### Brainstorm Features and Hypotheses (v0.1.0)
Interactive brainstorming assistant: evaluate user's existing ideas, generate new feature hypotheses with ICE scoring, benchmarks, risk assessment, and validation method recommendations. Supports MVP-phased approach. Saves results to Confluence or Google Drive.

**Trigger phrases**: "brainstorm features", "generate hypotheses", "come up with ideas", "провести брейншторм", "згенерувати гіпотези", "які фічі можна зробити", "пошук ідей"

### Feature and Hypothesis Requirements Creator (v0.1.0)
Create structured feature requirements documents as an experienced Business Analyst. Supports standard template (customizable via `local-context.md`), custom templates, A/B/A/B/C test sections, implementation approach recommendations, and flexible publishing to Confluence, Notion, or Google Docs.

**Trigger phrases**: "write requirements", "create feature spec", "describe requirements", "A/B test requirements", "сформувати вимоги", "описати вимоги до фічі", "створити вимоги", "вимоги до A/B тесту"

### Feature Task Creator (v0.1.0)
Break down a feature into structured Jira tasks by work type (FE/BE/Android/iOS/Design/Analytics) based on Confluence requirements. Supports grooming mode, A/B test flows, automatic task linking by dependency chain, and dry run mode.

**Trigger phrases**: "create tasks for feature", "break down feature into tasks", "створи задачі для фічі", "розбий фічу на задачі", "create Jira issues from Confluence"

### Product Analysis (v0.1.0)
Analyze product data from any source — Tableau dashboards, Google Sheets, CSV/XLSX files, screenshots, PDF reports — to find trends, anomalies, growth opportunities, and risks. Auto-generates data-backed hypotheses with ICE scoring. Supports four modes: interactive Q&A, full structured report, post-release analysis (based on Jira tasks and feature flag activation dates), and A/B test results analysis (from Tableau dashboards or user reports). Uses Python (pandas/numpy) for precise computation on tabular data. Can be invoked standalone or by other skills that need data analysis.

**Trigger phrases**: "analyze metrics", "review a dashboard", "find anomalies", "explain this data", "post-release analysis", "analyze A/B test", "пострелізний аналіз", "аналіз A/B тесту", "проаналізуй метрики", "розбери дашборд", "що відбувається з метриками", "знайди аномалії"

## Planned Skills Roadmap

| Phase | Skill | Description | Status |
|-------|-------|-------------|--------|
| 1 | Product Research | Competitive, user & market research → Confluence | ✅ Done |
| 2 | Write Concept / PRD | Adaptive PRD from idea to Confluence page | ✅ Done |
| 3 | Brainstorm Features and Hypotheses | Interactive brainstorm with ICE scoring & benchmarks | ✅ Done |
| 4 | Feature and Hypothesis Requirements Creator | Structured requirements as experienced BA → Confluence/Notion/Google Docs | ✅ Done |
| 5 | Feature Task Creator | Confluence requirements → Jira tasks by team | ✅ Done |
| 6 | Product Analysis | Data analysis with hypothesis generation from any data source | ✅ Done |
| 7 | Sprint Planning | Plan sprints with capacity & priority estimation | Planned |
| 8 | Stakeholder Update | Generate status reports for different audiences | Planned |
| 9 | Design Review | Pull Figma designs for review and handoff specs | Planned |

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

Дані, отримані з Tableau та інших аналітичних платформ, внутрішні дослідження та матеріали, що підпадають під комерційну таємницю або є конфіденційними, **не можуть**:

- Використовуватись для навчання будь-яких LLM
- Передаватись третім особам у будь-якій формі

Ці дані використовуються виключно поточним користувачем в рамках свого акаунту та поставлених ним задач. Детальні правила — у `references/data-policy.md`.

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

## Author

Andrii Siletskyi
