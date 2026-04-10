—————————————————————# Grow Product Manager

The plugin acts as an AI assistant for Product Managers. The shared goal is product growth, finding improvement opportunities, solving user problems, and improving metrics. Product changes are implemented on the principle of conscious, data-backed decisions supported by benchmarks and research results.

The toolkit covers the full product lifecycle: from market and competitor research, writing concepts and requirements, decomposing features into tasks — to sprint planning and stakeholder reporting. Each skill integrates with Jira, Confluence, Figma, and other tools via a smart fallback connection chain.

## Current Skills

### Product Research (v0.5.0)
Conduct competitive analysis, user research, market research, and UX benchmark research using web search, uploaded files, Knowledge Library, and Confluence pages. UX Benchmark Research mode provides benchmark matrices with gap analysis and best practice catalogs. Results are published as structured Confluence pages with actionable insights.

### Write Concept / PRD (v0.4.0)
Create structured product concept documents (PRD) with adaptive structure based on feature type. Gathers context from conversation, Confluence, web, files, and Deep Research via external LLMs. Can leverage existing Product Research results. Publishes to Confluence with proper formatting.

### Brainstorm Features and Hypotheses (v0.4.0)
Interactive brainstorming assistant: evaluate user's existing ideas, generate new feature hypotheses with ICE scoring, benchmarks, risk assessment, and validation method recommendations. Supports MVP-phased approach. Saves results to Confluence or Google Drive.

### Feature and Hypothesis Requirements Creator (v0.5.1)
Create structured feature requirements documents or analyze and improve existing ones, acting as an experienced Business Analyst. Supports two modes: Create mode and Analyze & Improve mode with customizable templates, A/B/A/B/C test sections, and implementation approach recommendations.

### Feature Task Creator (v0.4.0)
Break down a feature into structured Jira tasks by work type (FE/BE/Android/iOS/Design/Analytics) based on Confluence requirements. Supports grooming mode, A/B test flows, automatic task linking by dependency chain, and dry run mode.

### Product Analysis (v0.5.0)
Analyze product data from any source — Tableau dashboards, Google Sheets, CSV/XLSX files, screenshots, PDF reports — to find trends, anomalies, growth opportunities, and risks. Auto-generates data-backed hypotheses with ICE scoring. Includes CJM Funnel Analysis mode with stage-by-stage anomaly detection, health score calculation, and structured output for the CJM Research pipeline.

### Diagram & Prototype Creator (v0.7.0)
Create diagrams, flowcharts, BPMN 2.0 processes, mind maps, infographics, and UI prototypes to visualize product concepts and hypotheses. Supports multiple generation tools: Mermaid, HTML/CSS, Google Gemini, ChatGPT, NotebookLM, Figma, and Draw.io. Infographics with confidential data are generated locally via HTML/CSS.

### Meeting Processor (v0.9.0)
Process meetings from any source — Fireflies, other recording tools, uploaded files, or pasted text — to extract action items, decisions, and structured meeting reports. Enriches meeting data with calendar context (Google Calendar / Microsoft Calendar). Two modes: Process mode and Search mode.

### Knowledge Library (v0.1.0)
Manage a local library of curated knowledge sources (articles, benchmarks, research) with trust scoring, categorization, and multi-mode search (local library, Confluence, Google Drive, Baymard, internet). Service skill for CJM enrichment and UX Benchmark Research.

## Planned Skills

**CJM Research** — CJM analysis orchestrator with 5 modes: anomaly detection, hypothesis generation, full analysis, health-check, cross-platform comparison (Phase 3)
