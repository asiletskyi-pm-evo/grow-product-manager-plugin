# Grow Product Manager

The plugin acts as an AI assistant for Product Managers. The shared goal is product growth, finding improvement opportunities, solving user problems, and improving metrics. Product changes are implemented on the principle of conscious, data-backed decisions supported by benchmarks and research results.

The toolkit covers the full product lifecycle: from market and competitor research, writing concepts and requirements, decomposing features into tasks — to sprint planning and stakeholder reporting. Each skill integrates with Jira, Confluence, Figma, and other tools via a smart fallback connection chain.

## Current Skills

### CJM Research (v0.2.0)
CJM Research orchestrator — analyze Customer Journey Map funnels, detect anomalies, generate data-backed hypotheses with funnel impact modeling, and produce structured CJM reports. Supports 5 modes: anomaly detection, hypothesis generation, full CJM analysis, scheduled health-check with delta comparison, and cross-platform comparison. Orchestrates product-analysis, product-research, brainstorm-features, knowledge-library, and schedule through a 12-step pipeline with independent verification and risk assessment. Health-check mode supports automatic periodic execution with multi-channel notifications (Slack, Email, Confluence, local) and critical alert escalation.

### Product Research (v0.5.0)
Conduct competitive analysis, user research, market research, and UX benchmark research using web search, uploaded files, Knowledge Library, and Confluence pages. UX Benchmark Research mode provides benchmark matrices with gap analysis and best practice catalogs. Results are published as structured Confluence pages with actionable insights.

### Write Concept / PRD (v0.4.0)
Create structured product concept documents (PRD) with adaptive structure based on feature type. Gathers context from conversation, Confluence, web, files, and Deep Research via external LLMs. Can leverage existing Product Research results. Publishes to Confluence with proper formatting.

### Brainstorm Features and Hypotheses (v0.5.0)
Interactive brainstorming assistant: evaluate user's existing ideas, generate new feature hypotheses with ICE scoring, benchmarks, risk assessment, and validation method recommendations. Supports MVP-phased approach. CJM Hypotheses mode generates data-driven hypotheses from funnel anomalies with funnel position-weighted ICE scoring, evidence-based confidence boost, and funnel impact modeling. Saves results to Confluence or Google Drive.

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

### Knowledge Library (v0.2.0)
Manage a local library of curated knowledge sources (articles, benchmarks, research) with trust scoring, categorization, and multi-mode search (local library, Confluence, Google Drive, Baymard, internet). Service skill for CJM enrichment and UX Benchmark Research. Supports scheduled monthly trust re-evaluation with freshness decay, URL validation, and automated trust reports.

## Shared References

Shared reference files used across multiple skills:

- **cjm-protocol.md** — anomaly severity levels, health score formula, funnel impact calculations
- **funnel-templates.md** — funnel stage templates by product type (e-commerce, SaaS, marketplace, custom)
- **verification-checklist.md** — checklist for CJM Research independent verification (6 criteria, 3 status levels)
- **local-context-protocol.md** — Step 0 protocol for reading local-context.md, including optional sections handling for CJM and Knowledge Library configurations

## Supporting Skills

### Plugin Configurator (v0.6.0)
Configure the plugin for your organization: products, teams, data sources, CJM funnel configuration, and Knowledge Library onboarding. Manages `local-context.md` — the shared context file used by all skills.

### Presentation Creator (v0.5.0)
Create and update presentations (Google Slides / PowerPoint) from product context, templates, analytics data, and other plugin skills.

### Template Library (v0.2.0)
Manage and serve templates for all artifact types (concepts, requirements, research, Jira tasks, epics, presentations).
