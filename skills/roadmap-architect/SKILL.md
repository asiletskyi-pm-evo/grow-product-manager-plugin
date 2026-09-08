---
name: roadmap-architect
version: 0.2.3
description: Own the work structure — missions → initiatives → epics → features, labeling, roadmap tree — no dates, no capacity. Not quarter plans (quarterly-planning), not forecasts (project-planning). UA — «наведи лад у структурі», «розміть епіки/фічі», «дерево roadmap», «звʼяжи епік з ціллю». EN — "tidy up the structure", "label epics/features", "find labeling gaps", "build the roadmap tree", "link an epic to a goal", "direction structure". Also UA — «знайди розриви розмітки», «структура напрямків».
---

# Roadmap Architect

> **Path rule.** A bare `references/<file>.md` in this file is read from this skill's own `references/` if the file exists there, otherwise from the **shared** `references/` at the plugin root. Resolve the root as `${PLUGIN_ROOT}`, else `${CLAUDE_PLUGIN_ROOT}`, else the directory that contains `skills/`, found by walking up from this folder (`references/host-profiles.md` §6). Never continue without a protocol named here.

Keeper of the structure (foundation, outside time). Maps the Goal→Initiative→Epic→Feature hierarchy, **enforces labeling conventions**, finds gaps, and builds the structure tree. Doesn't plan the quarter/sprint and doesn't touch capacity — only structural integrity. **The PM decides.**

Supplies clean structure to the rest of the planning-suite. Integrates with `product-reporter` (Jira plumbing) and `cjm-research`/`brainstorm-features` (new candidates).

## Prerequisites
- `references/local-context-protocol.md` — Step 0 + Planning (goal map, labeling convention, Development Flow).
- `references/planning-core.md` — canonical model, naming/labeling convention, normalization, goal map.
- `references/dependency-model.md` — epic/feature links (for the tree and gaps).
- `references/roadmap-artifacts.md` — structure-tree format + gap report.
- `references/jira-data-protocol.md` — Jira plumbing (reuse).
- `references/integration-strategy.md`, `references/persistent-storage.md`, `references/template-protocol.md`.

## Step T — Template Resolution

`artifact_type: roadmap`, `subtype: structure-tree` (`tree` mode) or `gap-report` (`audit` mode), `product_id`, `language`. Resolve per `references/template-protocol.md` (T-1 → T-5); the resolved template shapes the Step 5 output. `map` and `onboard` mutate Jira/Confluence rather than producing a document — they skip Step T.

**Fallback:** no template → use the structure-tree / gap-report formats in `references/roadmap-artifacts.md`.

## Modes

| Mode | Output |
|------|--------|
| `audit` | Labeling gap report (no quarter/goal/code, orphan features, naming violations) |
| `map` | Link/set: epic→goal, feature→epic, labels (with approval) |
| `tree` | Goal→Initiative→Epic→Feature structure tree (full structure, no quarter scope) |
| `onboard` | Register a new mission/epic/feature with correct labeling |

## Pipeline

### Step 0 — Local context
Per `local-context-protocol.md` + goal map + labeling convention (`planning-core`).

### Step 1 — Scope
Mode + coverage (which goals/initiatives/epics).

### Step 2 — Pull structure
CQL by labels `epic`/`feature` + `getJiraIssue` epics per-key + goal map (`planning-core` sec. 4). Links — `dependency-model`.

### Step 3 — Labeling validation
Find: features/epics without a quarter, without a goal, naming-convention violations (`planning-core` regex), orphan features (no epic), unformalized dependencies (graph gaps).

### Step 4 — Map (mode `map`)
Propose label/link fixes (epic→goal, feature→epic, q-labels). **Gate before writing** to Jira/Confluence; preserve existing labels.

### Step 5 — Tree (mode `tree`)
Generate the Goal→Initiative→Epic→Feature tree (features as `code—name`) + gap report. Per `roadmap-artifacts.md` sec. 4. Workspace + library storage.

### Step 6 — Save to Vault (Optional)
Per `references/vault-protocol.md` → Vault Save. IF vault_level > L0 AND sync_mode != "off": `vault_save({ type: "roadmap", product: active_product, skill: "roadmap-architect", skill_version: "0.2.3", tags: [goals covered], content: structure tree + gap report, related: [[goal artifacts]], extra_frontmatter: { subtype: "structure-tree", gaps_count } })` → "Saved to Vault: Roadmaps/{product}/…"

## Quality Standards
- Don't invent links — only Jira links / goal map / explicit PM input; the rest = "break, please formalize".
- Conventions — from `planning-core`/local-context, not hardcoded.
- Features — `code — name` as a list.
- Write to Jira/Confluence only after PM approval. Language — `user.language`.

## Skill Chaining
→ `quarterly-planning` / `project-planning` (hands off clean structure) · → `task-creator` (decomposition).

## Additional Resources
`references/planning-core.md`, `dependency-model.md`, `roadmap-artifacts.md`, `local-context-protocol.md`, `template-protocol.md`, `persistent-storage.md`, `self-improvement.md`, `jira-data-protocol.md`.
