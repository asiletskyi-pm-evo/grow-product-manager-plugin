---
name: roadmap-architect
version: 0.1.1
description: Maintains the canonical structure of work — maps missions/goals → initiatives → epics → features, enforces labeling (labels, names, links), finds gaps, and generates the roadmap tree. Use when "tidy up the structure", "label epics/features", "find labeling gaps", "build the roadmap tree", "link an epic to a goal", "direction structure". Українською: "навести лад у структурі", "розмітити епіки/фічі", "знайти розриви розмітки", "побудувати дерево roadmap", "звʼязати епік з ціллю", "структура напрямків".
---

# Roadmap Architect

Keeper of the structure (foundation, outside time). Maps the Goal→Initiative→Epic→Feature hierarchy, **enforces labeling conventions**, finds gaps, and builds the structure tree. Doesn't plan the quarter/sprint and doesn't touch capacity — only structural integrity. **The PM decides.**

Supplies clean structure to the rest of the planning-suite. Integrates with `team-ops-reporter` (Jira plumbing) and `cjm-research`/`brainstorm-features` (new candidates).

## Prerequisites
- `references/local-context-protocol.md` — Step 0 + Planning (goal map, labeling convention, Development Flow).
- `references/planning-core.md` — canonical model, naming/labeling convention, normalization, goal map.
- `references/dependency-model.md` — epic/feature links (for the tree and gaps).
- `references/roadmap-artifacts.md` — structure-tree format + gap report.
- `skills/team-ops-reporter/references/jira-data-protocol.md` — Jira plumbing (reuse).
- `references/integration-strategy.md`, `references/persistent-storage.md`, `references/template-protocol.md`.

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

## Quality Standards
- Don't invent links — only Jira links / goal map / explicit PM input; the rest = "break, please formalize".
- Conventions — from `planning-core`/local-context, not hardcoded.
- Features — `code — name` as a list.
- Write to Jira/Confluence only after PM approval. Language — `user.language`.

## Skill Chaining
→ `quarterly-planning` / `project-planning` (hands off clean structure) · ← `cjm-research` / `brainstorm-features` (new epics/features) · → `task-creator` (decomposition).

## Additional Resources
`references/planning-core.md`, `dependency-model.md`, `roadmap-artifacts.md`, `local-context-protocol.md`, `template-protocol.md`, `persistent-storage.md`, `self-improvement.md`; `skills/team-ops-reporter/references/jira-data-protocol.md`.
