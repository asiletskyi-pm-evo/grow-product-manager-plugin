# CJM report formats, publishing, and the automated health-check protocol

> Part of `cjm-research`. Loaded on demand at Step 12 (report assembly). Pick ONLY the format for the active mode.

**Evidence labels (since v3.8.0, every format).** Each cited number and quote carries its SKILL.md 3.5.g class first in its existing annotation (`references/data-integrity-protocol.md` Gate Check 6; grammar `references/pm-mental-model.md` §4); a table or section takes one group label only when every claim it covers shares class and source. A summary, key findings or enrichment findings never hold `simulated` content — it goes to the hypotheses or to one `Simulated input — hypotheses only` line, shown only when such input exists — and hold `assumed` content only labelled. In an interactive run a cause stated without an experiment or holdout keeps its Gate Check 6c line, in `user.language`, next to the claim; the automated health-check prints no such line. Impact-model projections carry no class; an unsourced lift inside them is `assumed`.

### Report Format — Anomalies (modes: `anomalies`)

```
1. Summary (3–5 key findings)
2. Funnel Overview (visual: stages with conversion rates and health indicators)
3. Anomalies by Stage
   | Stage | Metric | Baseline | Actual | Deviation | Severity | Trend |
4. Recommendations (brief next steps for each critical/warning anomaly)
5. Glossary (explain all terms, metrics, jargon)
6. Sources (data sources used, grouped by type, each with its class. Tableau-sourced data marked as `tableau-mcp` or `tableau-web` so the user can audit the retrieval method)
```

### Report Format — Health-Check Summary (mode: `health-check`)

```
1. Period (date range analyzed) + one evidence line: `Evidence: measured — <dashboard(s)>, <period>`, followed when the configured baselines are used by a second group label `Evidence: reported — baselines, local-context.md` (one class per group label) (no gate jargon in the published body)
2. Funnel Health Score (0–100, calculated per cjm-protocol.md)
3. Delta vs Previous Check (score change, direction — values only; a previous snapshot without labels, saved before v3.8.0, is not a change)
4. New Anomalies (detected since last check)
5. Resolved Anomalies (present last time but no longer anomalous)
6. Top 3 Attention Items (highest severity, actionable; a suspected cause carries the 6c hand-back line in an interactive run and reads `[assumed — frontier: <human step>]` in the scheduled health-check)
7. Link to Full Report (offer to run full mode if critical anomalies found)
```

**Health Score calculation** per `references/cjm-protocol.md`:
- Weighted average of stage health scores (0–100 scale)
- Stage weights: Entry (15%), Middle stages (25% each), Conversion (35%)
- Penalties: Critical (-30), Warning (-15), Info (-3), Positive (+5)

**Save health-check snapshot:**
- Save to `~/.grow-pm/knowledge-library/health-checks/[date].md`
- Include: health score, all anomalies, stage data
- This enables delta comparison in future health-checks

### Report Format — Hypotheses (mode: `hypotheses`)

```
1. Summary (top 3 hypotheses, overall funnel impact potential)
2. Funnel Overview (stages with anomaly indicators)
3. Anomalies (condensed table from Step 4)
4. Hypotheses Table
   | # | Name | Trigger | Solution | ICE | Stage Impact | Category |
5. Prioritization Matrix
   - Low-hanging fruit (table)
   - Structural changes (table)
   - Business logic changes (table)
6. Funnel Impact Model
   - Per-hypothesis stage impact
   - Cumulative end-to-end impact
7. Next Steps (recommended actions for top hypotheses)
8. Glossary
9. Sources (library, web, Baymard, Confluence, GDrive — marked by type and class)
```

### Report Format — Full CJM Report (mode: `full`)

```
1. Executive Summary (key findings, overall health score, top recommendations)
2. Funnel Overview (visual with stage metrics)
3. Stage-by-Stage Analysis
   For each stage:
   - Current metrics and trends
   - Detected anomalies
   - Enrichment findings (world + internal sources, each with its class)
   - Related hypotheses
4. Hypotheses with Verification Status
   | # | Name | Data Trigger | Solution | ICE | Verification | Stage Impact |
5. Impact Model
   - Per-hypothesis: stage conversion current → new, absolute lift
   - End-to-end: current overall → projected overall, total impact
6. Risk Assessment (risk matrix per hypothesis)
7. Prioritized Backlog
   - Phase 1 (quick wins): low-hanging fruit sorted by ICE
   - Phase 2 (structural): structural changes sorted by impact
   - Phase 3 (strategic): business logic changes with stakeholder requirements
8. Recommended Roadmap (phases with timelines)
9. Glossary
10. Sources (all sources used, grouped by type, each with its class)
```

### Report Format — Cross-Platform Comparison (mode: `comparison`)

```
1. Summary (key differences between platforms)
2. Platform A Funnel (stages, conversion rates, anomalies)
3. Platform B Funnel (stages, conversion rates, anomalies)
4. Side-by-Side Comparison
   | Stage | Platform A Conv | Platform B Conv | Delta | Significance |
5. Platform-Specific Anomalies (present in one platform only)
6. Shared Anomalies (present in both platforms)
7. Recommendations per Platform
8. Glossary
9. Sources
```

---

## Publishing

**Before 12a — the PM-first comparison or `explain` (since v3.9.0).** In an interactive `hypotheses` / `full` run where `references/cjm-pipeline.md` Step 7.0 applied: "Your hypotheses vs mine" (`pm_first`, after an answer) or "How I got here" (`explain`) comes in chat once the report is assembled, before 12a — or before publishing to the Step 2e destination. It never enters the report and asks nothing; a change it prompts goes through the 12b feedback loop. The Automated Health-Check Protocol below is unchanged: no question, no block.

**12a. Ask via AskUserQuestion (if not already specified in Step 2e):**

> "Report is ready. Where should I publish it?"

- **Confluence** (default) → ask for space and parent page. Title: `[CJM] Product — Mode — Date`
- **Notion** → ask for workspace and location
- **Google Docs** → ask for folder
- **Local markdown** → save to workspace folder
- **No** → results stay in the dialogue

**Confluence formatting requirements:**
1. Table of Contents (levels 1-6)
2. Dividers between all major sections
3. H1/H2/H3 heading hierarchy
4. Bold key theses, critical numbers, important conclusions
5. Tables for all structured data: anomalies, hypotheses, ICE scores, impact model
6. Info/Note/Warning panels for critical findings
7. Sources section with links, marking source types

Publish via appropriate MCP. If unavailable — follow `references/integration-strategy.md` fallback chain. As a last resort — generate a local document.

**12b. Summary report and feedback:**

After publishing, provide a structured summary:

- **What was done:** mode used, stages analyzed, time period, platforms
- **Artifacts created:** links to published reports
- **Key findings:** top 3-5 findings as the report words them (annotations and labels kept; never `simulated`)
- **Hypotheses generated:** count, top 3 by ICE score (if applicable)
- **Health score:** current score and delta vs previous (if applicable)
- **Sources used:** list by type (Tableau [`tableau-mcp` / `tableau-web`], Knowledge Library, Web, Baymard, Confluence, GDrive)

**After presenting the report, proactively ask for feedback:**

> "Are you satisfied with the CJM analysis? Would you like to dig deeper into any stage, adjust hypotheses, or change the scope?"

- If the user requests changes — iterate: adjust analysis, re-publish, present updated report
- If the user confirms — proceed to skill chaining

**12c. Context enrichment offer:**

If the analysis discovered new data that could improve `local-context.md`:
- Updated baseline conversions from fresh dashboard data
- New competitors identified during web research
- Updated metric values

Follow the Enrichment Protocol from `plugin-configurator`:
1. Inform user what was discovered
2. Ask: "Would you like to update local-context.md?"
3. If yes — update the appropriate sections, show changelog

**Self-improvement check** (after corrections are applied and confirmed): follow `references/self-improvement.md` — analyze whether the correction is a pattern, and if so propose a SKILL.md improvement (version bump + CHANGELOG).

---

## Automated Health-Check Protocol

When `health-check` mode is configured for automation:

1. **Setup:** During Step 2, if user selects health-check mode:
   - Ask about frequency: weekly (recommended), bi-weekly, monthly
   - Ask about notification: where to publish results (Confluence page / local file)
   - Chain to `schedule` skill to create recurring task
   - Schedule task invokes `cjm-research` in `health-check` mode with saved parameters

2. **Execution (automated):**
   - Skip Step 2 (use saved parameters)
   - Run Steps 1, 3, 4 with default settings from CJM config
   - Load previous health-check for delta comparison
   - Assemble Health-Check Summary (labels only — no question, no hand-back line)
   - Save snapshot to `~/.grow-pm/knowledge-library/health-checks/[date].md`
   - Publish to configured destination

3. **Escalation:**
   - If any **Critical** anomaly detected → highlight in report, suggest full mode
   - If health score dropped by >10 points vs previous check → flag as urgent

---
