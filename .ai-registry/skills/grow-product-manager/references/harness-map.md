# Harness Map — anatomy of the Grow PM plugin

> **What this is.** An agent is a *model plus a harness*: the model is one input (~10%); the harness — instructions, tools, sandboxes, orchestration, guardrails, observability — is the other ~90% and is the team's surface area, not the provider's. This file documents what plays each harness role in *this* plugin, so that when a skill misbehaves we debug the **harness first** (see `self-improvement.md` → Harness-first diagnosis). Framing follows Google/Kaggle "The New SDLC With Vibe Coding" (2026).

## 1. The six harness layers in this plugin

| Layer | What it is (paper) | Where it lives here |
|-------|--------------------|---------------------|
| **Instructions / rules** | Who the agent is, what it must/mustn't do | Skill cores (`skills/*/SKILL.md`, thin ≤400 lines — validator check 15), the judgment contract every skill reads at Step 0j (`pm-mental-model.md`, since v3.4.0) and its implementing steps (`judgment-points.md` — P2, P3 and P9 since v3.7.0; the P4 pre-mortem, the P6 build-first line and the P8 learning modes since v3.9.0), the role layer resolved at Step 0i (`role-profiles.md`, since v3.5.0), shared protocols (`planning-core.md`, `cjm-protocol.md`, `focus-*.md`), `local-context.md` (org/product rules) |
| **Tools** | Functions/MCP/APIs + prose on when to call them | `integration-strategy.md` (MCP → Registry → Browser fallback), `jira-data-protocol.md`, Tableau/Atlassian/Figma/Fireflies/GWorkspace MCPs |
| **Sandboxes / execution** | Where code runs, what it can reach | Cowork Linux sandbox (bash), `~/.grow-pm/` persistent store, `~/.grow-pm-sandbox/` (dry-run onboarding), Vault mirror |
| **Orchestration** | Sub-agent spawning, routing, hand-offs | `subagent-delegation.md`, skill-to-skill chaining (focus-advisor → executors; cjm-research → brainstorm-features), description collision groups |
| **Guardrails / hooks** | Deterministic checks at set points | **Host hooks (`hooks/hooks.json`, v2.6.0):** SessionStart context digest (`scripts/session_start.py`), PreToolUse write gate before Jira/Confluence writes (`scripts/write_gate.py`, `ask`) and, since v3.10.0, before file writes under a shared-context provider's folders (`context-provider-protocol.md` §7); tool-restricted agents (`agents/`, v2.5.0); `data-integrity-protocol.md` (6 gate checks; evidence class & frontier since v3.8.0), `artifact-style-gate.md` (Gates 1–3 and Gate 4 — 4a altitude since v3.5.0, 4c confidence since v3.7.0, 4b evidence labels since v3.8.0 — through the maker–checker lenses and the `template-protocol.md` T-5 self-checks; since v3.9.0 the non-blocking Spec readiness line, and the `judgment-points.md` §7 pre-mortem inserted at T-5 step 3b, which is not a Gate part), the `self-improvement.md` Principle 5 guard (evidence labels since v3.8.0; counter-arguments, hand-back and confidence lines and "agree more" since v3.9.0), `data-policy.md` (internal data never leaves session), Step 0 config gate, `release-manager` pre-flight gates |
| **Observability** | Logs, traces, evals, drift detection | `testing/trigger-evals.md` (trajectory/routing, live runs on Claude Code and Codex CLI), `testing/output-evals.md` (artifact quality — rubrics judged against gold exemplars and fixtures, with the judgment criteria since v3.7.0, the evidence-label criteria since v3.8.0 and `counter_argument` since v3.9.0), `validate-consistency.sh` and `testing/skill_lint.py` (CI), `testing/seeded_leak_test.py` (CI — a seeded defect proves each lint check fires), `testing/session_start_test.py` (the SessionStart digest), `testing/host-smoke.sh` (loads the tree on Claude Code and Codex CLI before a release), CHANGELOG/release verification |

**Reading:** guardrails and observability are the plugin's strongest layers. **The gaps that remain:**
- Examples are partial — the two light output-eval rubrics (product-analysis analysis report, brainstorm-features) still lack a fixture and a gold (§2; `testing/output-evals.md` → Coverage status).
- The static/dynamic context budget is not written yet (§3).
- The judgment layer has no durable runtime log: its behaviour is evidenced by test cases and output-evals, and a judgment-guard correction leaves one chat line only (`self-improvement.md`).
- The ChatGPT and Codex-cloud host profiles are derived, not measured (`testing/host-matrix.md`).

## 2. Six context types — coverage map

Context engineering means balancing which of six context types the agent holds upfront (static) vs retrieves on demand (dynamic). Coverage across the plugin's references and skills:

| Context type | Definition | Covered by | Status |
|--------------|------------|-----------|--------|
| **Instructions** | Core role, goals, boundaries | Skill cores, `pm-mental-model.md` (who the user is + ten principles) with its implementing steps in `judgment-points.md`, `role-profiles.md` (eight roles as defaults, altitude L1–L4), `planning-core.md`, `cjm-protocol.md`, `focus-*.md`, `local-context.md` | ✅ strong |
| **Knowledge** | Retrieved docs, domain data | `knowledge-library`, `local-context.md` product data, `funnel-templates.md`, Confluence/Tableau via MCP | ✅ good |
| **Memory** | Session + persistent project state | `vault-protocol.md`, `persistent-storage.md`, `~/.grow-pm/`, experiments `registry.yaml`, `focus/`, shared-context providers (`context-provider-protocol.md`, since v3.10.0) | ✅ strong |
| **Examples** | Few-shot demonstrations, reference patterns | `templates/built-in/` (structure); golden artifacts for the heavy artifact skills (list below) | ⚠️ **partial — 12 golds / 8 skills; two light rubrics without one** |
| **Tools** | Precise API/MCP definitions + usage prose | `integration-strategy.md`, `jira-data-protocol.md`, `subagent-delegation.md` | ✅ good |
| **Guardrails** | Hard constraints, validations | `data-integrity-protocol.md` (since v3.8.0 with the evidence classes and the Gate Check 6 frontier hand-back), `artifact-style-gate.md` Gate 4 (4a–4c) and its Spec readiness line (since v3.9.0), the `self-improvement.md` Principle 5 guard (in full since v3.9.0), `data-policy.md`, `test-mode.md`, Step 0 gate | ✅ strong |

### Examples — golds and the remaining gap
Templates define *structure*; they do not show a *worked, high-quality instance*. The heaviest artifact skills carry on-demand golden examples (loaded only when the task matches → cheap):

- `skills/write-concept/references/examples/` — PRD, design brief, strategy memo
- `skills/requirements-creator/references/examples/` — feature spec; AI-feature spec (since v3.9.0)
- `skills/cjm-research/references/examples/` — funnel-anomaly report
- `skills/product-analysis/references/examples/` — A/B test report (since v3.7.0)
- `skills/product-research/references/examples/` — research plan; user-research synthesis (since v3.8.0)
- `skills/meeting-processor/references/examples/` — MoM (since v3.4.0)
- `skills/task-creator/references/examples/` — task batch (since v3.4.0)
- `skills/product-reporter/references/examples/` — QBR

The role-default exemplars of v3.6.0 (design brief, strategy memo, research plan, QBR) are among them. Each gold is also the gold reference of a `testing/output-evals.md` rubric, paired with a fixture in `testing/fixtures/` (one asset, two jobs). Still without a fixture and gold: the product-analysis analysis report and brainstorm-features (light rubrics).

## 3. Static vs dynamic boundary (pointer)

The static/dynamic context boundary is a first-class, versioned architectural decision — budgeted separately in `references/context-budget.md` (planned). Rule of thumb: **static** = loaded every skill turn (Step 0 core of `local-context.md`, core guardrails); **dynamic** = loaded on task match (skill-local references, on-demand `local-context.md` sections, knowledge-library, vault context). Progressive disclosure (metadata → full instructions → deep references) is how a skill carries dozens of capabilities while paying only for the one in use.

## 4. How to use this map
- **Debugging a skill:** find the failing layer in §1, apply the routing table in `self-improvement.md`.
- **Adding a skill:** confirm it has coverage in each of the six context types (§2) that its job needs; don't ship an artifact skill with no Examples and no output-eval.
- **Architecture reviews:** this file is the canonical answer to "what is our harness, and where is it thin."
