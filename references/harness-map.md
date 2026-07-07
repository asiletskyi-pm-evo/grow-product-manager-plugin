# Harness Map — anatomy of the Grow PM plugin

> **What this is.** An agent is a *model plus a harness*: the model is one input (~10%); the harness — instructions, tools, sandboxes, orchestration, guardrails, observability — is the other ~90% and is the team's surface area, not the provider's. This file documents what plays each harness role in *this* plugin, so that when a skill misbehaves we debug the **harness first** (see `self-improvement.md` → Harness-first diagnosis). Framing follows Google/Kaggle "The New SDLC With Vibe Coding" (2026).

## 1. The six harness layers in this plugin

| Layer | What it is (paper) | Where it lives here |
|-------|--------------------|---------------------|
| **Instructions / rules** | Who the agent is, what it must/mustn't do | Skill cores (`skills/*/SKILL.md`, thin ≤400 lines), shared protocols (`planning-core.md`, `cjm-protocol.md`, `focus-*.md`), `local-context.md` (org/product rules) |
| **Tools** | Functions/MCP/APIs + prose on when to call them | `integration-strategy.md` (MCP → Registry → Browser fallback), `jira-data-protocol.md`, Tableau/Atlassian/Figma/Fireflies/GWorkspace MCPs |
| **Sandboxes / execution** | Where code runs, what it can reach | Cowork Linux sandbox (bash), `~/.grow-pm/` persistent store, `~/.grow-pm-sandbox/` (dry-run onboarding), Vault mirror |
| **Orchestration** | Sub-agent spawning, routing, hand-offs | `subagent-delegation.md`, skill-to-skill chaining (focus-advisor → executors; cjm-research → brainstorm-features), description collision groups |
| **Guardrails / hooks** | Deterministic checks at set points | `data-integrity-protocol.md` (5-gate), `data-policy.md` (internal data never leaves session), Step 0 config gate, `release-manager` pre-flight gates |
| **Observability** | Logs, traces, evals, drift detection | `testing/trigger-evals.md` (trajectory/routing), `testing/output-evals.md` (artifact quality — planned), `validate-consistency.sh` (CI), CHANGELOG/release verification |

**Reading:** guardrails and observability are the plugin's strongest layers; **observability's output-eval half and the Examples context type are the current thin spots** (see §2 and `testing/output-evals.md`).

## 2. Six context types — coverage map

Context engineering means balancing which of six context types the agent holds upfront (static) vs retrieves on demand (dynamic). Coverage across the plugin's references and skills:

| Context type | Definition | Covered by | Status |
|--------------|------------|-----------|--------|
| **Instructions** | Core role, goals, boundaries | Skill cores, `planning-core.md`, `cjm-protocol.md`, `focus-*.md`, `local-context.md` | ✅ strong |
| **Knowledge** | Retrieved docs, domain data | `knowledge-library`, `local-context.md` product data, `funnel-templates.md`, Confluence/Tableau via MCP | ✅ good |
| **Memory** | Session + persistent project state | `vault-protocol.md`, `persistent-storage.md`, `~/.grow-pm/`, experiments `registry.yaml`, `focus/` | ✅ strong |
| **Examples** | Few-shot demonstrations, reference patterns | `templates/built-in/` (structure only); **golden artifacts largely absent** | ⚠️ **thin — fill for heavy skills** |
| **Tools** | Precise API/MCP definitions + usage prose | `integration-strategy.md`, `jira-data-protocol.md`, `subagent-delegation.md` | ✅ good |
| **Guardrails** | Hard constraints, validations | `data-integrity-protocol.md`, `data-policy.md`, `test-mode.md`, Step 0 gate | ✅ strong |

### The Examples gap
Templates define *structure*; they do not show a *worked, high-quality instance*. The heaviest artifact skills benefit most from on-demand golden examples (loaded only when the task matches → cheap):

- `skills/write-concept/references/examples/` — one exemplar PRD
- `skills/requirements-creator/references/examples/` — one exemplar feature spec (+ one A/B spec)
- `skills/cjm-research/references/examples/` — one exemplar funnel-anomaly report

These golden artifacts double as fixtures for `testing/output-evals.md` (one asset, two jobs).

## 3. Static vs dynamic boundary (pointer)

The static/dynamic context boundary is a first-class, versioned architectural decision — budgeted separately in `references/context-budget.md` (planned). Rule of thumb: **static** = loaded every skill turn (Step 0 core of `local-context.md`, core guardrails); **dynamic** = loaded on task match (skill-local references, on-demand `local-context.md` sections, knowledge-library, vault context). Progressive disclosure (metadata → full instructions → deep references) is how a skill carries dozens of capabilities while paying only for the one in use.

## 4. How to use this map
- **Debugging a skill:** find the failing layer in §1, apply the routing table in `self-improvement.md`.
- **Adding a skill:** confirm it has coverage in each of the six context types (§2) that its job needs; don't ship an artifact skill with no Examples and no output-eval.
- **Architecture reviews:** this file is the canonical answer to "what is our harness, and where is it thin."
