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


### Brainstorm Features and Hypotheses (v0.4.0
Interactive brainstorming assistant: evaluate user's existing ideas, generate new feature hypotheses with ICE scoring, benchmarks, risk assessment, and validation method recommendations. Supports MVP-phased approach. Saves results to Confluence or Google Drive.


**Trigger phrases**: "brainstorm features", "generate hypotheses", "come up with ideas", "find growth opportunities"


### Feature and Hypothesis Requirements Creator (v0.5.1)
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


### Diagram & Prototype Creator (v0.7.0)
Create diagrams, flowcharts, BPMN 2.0 processes, mind maps, infographics, and UI prototypes to visualize product concepts and hypotheses. Supports multiple generation tools:

- **Mermaid (built-in)** — fast local generation for flowcharts, BPMN, simple diagrams
- **HTML/CSS (built-in)** — local generation of infographics as self-contained HTML files with inline CSS and SVG charts
- **Google Gemini** — image generation in Nano Banana mode via browser
- **ChatGPT** — image generation via browser (GPT-4o or newer)
- **NotebookLM** — presentations and mind maps via browser
- **Figma** — prototypes and design mockups via MCP or browser
- **Draw.io** — XML generation locally or via browser fallback

**Infographic styles:** Data-driven (metrics, KPIs), Process/timeline (flows, roadmaps), Comparison (feature eval, competitive), Informational/educational (product overviews), Statistical/report (quarterly data, surveys). Infographics with confidential data are generated locally via HTML/CSS — no data sent to external LLMs.

Includes a quality check loop: auto-reviews generated images against requirements, auto-corrects up to 3 times, asks the user before continuing. Supports skill chaining from all other skills. Publishes to Confluence, Notion, Figma, or local files. Infographics can additionally be exported as PNG or PDF.

**Trigger phrases**: "create a diagram", "draw a flowchart", "BPMN diagram", "make a prototype", "create an infographic", "wireframe", "mockup", "visualize this process", "mind map"

### Meeting Processor (v0.9.0)
Process meetings from any source — Fireflies, other recording tools, uploaded files, or pasted text — to extract action items, decisions, and structured meeting reports. Enriches meeting data with calendar context (Google Calendar / Microsoft Calendar): participant list with emails and roles, agenda, attached documents and presentations. Two modes:


- **Process mode** — work with a single meeting: auto-classify type (grooming, discovery, demo/retro, status, brainstorm), extract structured notes with type-specific blocks, generate Structured MoM or Short summary
- **Search mode** — query across multiple meetings: "what did we discuss about feature X last month?" → chronological synthesis with decisions and action items


Tool-agnostic: works with Fireflies MCP, other meeting tool MCPs, uploaded files (audio/video/text/srt), or pasted text. Chains to feature-task-creator (action items → Jira), product-research (interview insights), requirements-creator, brainstorm-features, and diagram-prototyper.



### Knowledge Library (v0.1.0) — NEW
Manage a local library of curated knowledge sources (articles, benchmarks, research) with trust scoring, categorization, and multi-mode search (local library, Confluence, Google Drive, Baymard, internet). Service skill for CJM enrichment.

**Trigger phrases**: "add source", "search knowledge", "import sources", "show library", "what sources do we have on [topic]"

---

## Planned Skills

- **CJM Research** — CJM analysis orchestrator with 5 modes: anomaly detection, hypothesis generation, full analysis, health-check, cross-platform comparison (Phase 3)
