# Grow Product Manager Plugin v1.3.0

AI assistant for Product Managers: research, concepts, requirements, brainstorming, task creation, data analysis, meeting processing, and knowledge management — integrated with Jira, Confluence, Figma, Notion, Google Calendar, Gmail, Fireflies, and more.

## Mandatory Protocols

Before executing ANY skill, follow these protocols in order:

1. **Local Context Protocol** — read and follow `references/local-context-protocol.md` (Step 0: search for `local-context.md` in priority order: `~/.grow-pm/local-context.md` → plugin root → workspace → session dir). If not found anywhere, launch Plugin Configurator in Onboarding mode before proceeding.
2. **Integration Strategy** — read and follow `references/integration-strategy.md` (3-step fallback: MCP connector → search MCP registry → browser fallback).
3. **Data Confidentiality Policy** — read and follow `references/data-policy.md`. Never send confidential data (Tableau metrics, internal analytics, research, PII) to external LLMs or third parties.
4. **Self-Improvement Protocol** — at the end of each skill execution, follow `references/self-improvement.md` if the user provides corrections.

## Persistent Storage

All user data is stored in `~/.grow-pm/` (survives plugin reinstalls):
- `~/.grow-pm/local-context.md` — main configuration
- `~/.grow-pm/config/` — configuration files
- `~/.grow-pm/template-library/` — user templates
- `~/.grow-pm/knowledge-library/` — curated knowledge sources
- `~/.grow-pm/backups/` — auto-backups before migrations

## Available Skills

### Plugin Configurator (v0.7.0)
- **Skill file:** `skills/plugin-configurator/SKILL.md`
- **Trigger phrases:** "configure plugin", "set up plugin", "set up context", "add a product", "update configuration", "validate setup", "show config"
- **Auto-trigger:** when any other skill detects that `local-context.md` does not exist

### Brainstorm Features (v0.4.0)
- **Skill file:** `skills/brainstorm-features/SKILL.md`
- **Trigger phrases:** "brainstorm features", "generate hypotheses", "find growth opportunities", ICE scoring, benchmarks, validation methods

### Write Concept / PRD (v0.4.0)
- **Skill file:** `skills/write-concept/SKILL.md`
- **Trigger phrases:** "write a concept", "create a PRD", "describe a feature", "write a spec"

### Requirements Creator (v0.5.1)
- **Skill file:** `skills/requirements-creator/SKILL.md`
- **Trigger phrases:** "write requirements", "describe a feature", "create feature spec", "write A/B test requirements", "review requirements", "analyze requirements", "improve requirements", "check my spec"

### Feature Task Creator (v0.7.0)
- **Skill file:** `skills/feature-task-creator/SKILL.md`
- **Trigger phrases:** "create tasks for a feature", "create Jira issues from Confluence", "break down a feature into tasks", "create tasks from requirements", or when user shares a Confluence link and asks to create Jira tasks

### Product Research (v0.4.0)
- **Skill file:** `skills/product-research/SKILL.md`
- **Trigger phrases:** "research competitors", "analyze the market", "competitive analysis", "synthesize user interviews", "find market trends", SWOT, TAM SAM SOM, PESTEL analysis

### Product Analysis (v0.4.0)
- **Skill file:** `skills/product-analysis/SKILL.md`
- **Trigger phrases:** "analyze metrics", "review a dashboard", "find anomalies", "explain this data", "post-release analysis", "analyze A/B test results"

### Diagram & Prototype Creator (v0.7.0)
- **Skill file:** `skills/diagram-prototyper/SKILL.md`
- **Trigger phrases:** "create a diagram", "draw a flowchart", "visualize this process", "make a prototype", "create an infographic", "BPMN diagram", "wireframe", "mockup"

### Meeting Processor (v0.9.0)
- **Skill file:** `skills/meeting-processor/SKILL.md`
- **Trigger phrases:** "summarize meeting", "meeting notes", "what was discussed", "action items", "MoM", or when user provides a meeting transcript/recording

### Knowledge Library (v0.2.0)
- **Skill file:** `skills/knowledge-library/SKILL.md`
- **Trigger phrases:** "add source", "search knowledge", "import sources", "show library", "what sources do we have on [topic]", "add this article", "save this source"

## Skill Execution Protocol

When the user's request matches a skill trigger phrase:

1. Read the corresponding `SKILL.md` file completely
2. Read all referenced files from the skill's `references/` subdirectory (if any) and from the shared `references/` directory as needed
3. Follow the Local Context Protocol (Step 0) — load `local-context.md`
4. Follow the Integration Strategy for any external tool access
5. Execute the skill workflow as described in the SKILL.md
6. At the end, follow the Self-Improvement Protocol if the user provides corrections

## Reference Files

| File | Purpose |
|------|---------|
| `references/local-context-protocol.md` | How to find and use local-context.md |
| `references/integration-strategy.md` | MCP → registry → browser fallback chain |
| `references/data-policy.md` | Data confidentiality rules |
| `references/self-improvement.md` | Learning from user corrections |
| `references/persistent-storage.md` | ~/.grow-pm/ directory structure and migration |
| `references/cjm-protocol.md` | Customer Journey Map protocol |
| `references/funnel-templates.md` | Funnel analysis templates |
| `local-context.example.md` | Template for manual local-context.md creation |

## Language

The plugin supports Ukrainian (uk) and English (en). The preferred language is set in `local-context.md` under `User Profile → Language`. Default to the language the user is speaking in.
