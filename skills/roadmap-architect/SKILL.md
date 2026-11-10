---
name: roadmap-architect
version: 0.7.0
description: Own the work structure — missions → initiatives → epics → features, labeling, roadmap tree, user story map with release slices — no dates, no capacity. Not quarter plans (quarterly-planning), not forecasts (project-planning), not a strategy memo (write-concept). UA — «наведи лад у структурі», «розміть епіки/фічі», «дерево roadmap», «мапа історій».
---

# Roadmap Architect

> **Path rule.** A bare `references/<file>.md` in this file is read from this skill's own `references/` if the file exists there, otherwise from the **shared** `references/` at the plugin root. Resolve the root as `${PLUGIN_ROOT}`, else `${CLAUDE_PLUGIN_ROOT}`, else the directory that contains `skills/`, found by walking up from this folder (`references/host-profiles.md` §6). Never continue without a protocol named here.

Keeper of the structure (foundation, outside time). Maps the Goal→Initiative→Epic→Feature hierarchy, **enforces labeling conventions**, finds gaps, builds the structure tree and the user story map (since v4.6.0). Doesn't plan the quarter/sprint and doesn't touch capacity — only structural integrity. **The PM decides.**

Supplies clean structure to the rest of the planning-suite. Integrates with `product-reporter` (Jira plumbing) and `cjm-research`/`brainstorm-features` (new candidates).

## Prerequisites
- `references/local-context-protocol.md` — Step 0 + Planning (goal map, labeling convention, Development Flow).
- `references/planning-core.md` — canonical model, naming/labeling convention, normalization, goal map.
- `references/dependency-model.md` — epic/feature links (for the tree and gaps).
- `references/roadmap-artifacts.md` — structure-tree format + gap report.
- `references/jira-data-protocol.md` — Jira plumbing (reuse).
- `references/story-map-protocol.md` — mode `story-map` (Step 7): the map's model, note, quality rule, slice → features, renders, publication, the team's board edits, progress.
- `references/artifact-publishing.md` — where the map's board and progress dashboard go, the record, a new version of the same place (Step 7d).
- `references/integration-strategy.md`, `references/persistent-storage.md`, `references/template-protocol.md`.

## Step T — Template Resolution

`artifact_type: roadmap`, `subtype: structure-tree` (`tree` mode), `gap-report` (`audit` mode) or `story-map` (`story-map` mode), `product_id`, `language`. Resolve per `references/template-protocol.md` (T-1 → T-5); the resolved template shapes the Step 5 output. `map` and `onboard` mutate Jira/Confluence rather than producing a document — they skip Step T (since v3.9.0 `onboard` renders only the pre-mortem partial itself, Step 4b).

**Fallback:** no template → use the structure-tree / gap-report formats in `references/roadmap-artifacts.md`; the story map's format is `references/story-map-protocol.md` §4.

**Judgment footer (since v3.5.0).** The artifact closes with the altitude line from `templates/built-in/partial/judgment-footer-v1.md` (`references/template-protocol.md` T-5 step 3a; checked by `references/artifact-style-gate.md` Gate 4a) — on the structure-tree, gap-report and story-map notes only (never on the map's board or dashboard); `onboard` and other Jira edits never get it.

## Modes

| Mode | Output |
|------|--------|
| `audit` | Labeling gap report (no quarter/goal/code, orphan features, naming violations) |
| `map` | Link/set: epic→goal, feature→epic, labels (with approval) |
| `tree` | Goal→Initiative→Epic→Feature structure tree (full structure, no quarter scope) |
| `onboard` | Register a new mission/epic/feature with correct labeling (+ pre-mortem for a new mission or initiative, Step 4b, since v3.9.0) |
| `story-map` | User story map: backbone → cards → release slices with an outcome, no dates; a slice into features in one «так»; board + progress dashboard (Step 7, since v4.6.0) |

## Pipeline

### Step 0 — Local context
Per `local-context-protocol.md` + goal map + labeling convention (`planning-core`).

> **Judgment contract (Step 0j).** Per `references/local-context-protocol.md` Step 0j and `references/pm-mental-model.md`: note this run's
> judgment points (score, rank, verdict, priority, ship/kill, debate question) internally, with no output. A principle acts only through
> a step that implements it — until one exists here, this skill's questions, gates and output stay exactly as they are.

### Step 1 — Scope
Mode + coverage (which goals/initiatives/epics).

### Step 2 — Pull structure
CQL by labels `epic`/`feature` + `getJiraIssue` epics per-key + goal map (`planning-core` sec. 4). Links — `dependency-model`.

### Step 3 — Labeling validation
Find: features/epics without a quarter, without a goal, naming-convention violations (`planning-core` regex), orphan features (no epic), unformalized dependencies (graph gaps).

### Step 4 — Map (mode `map`)
Propose label/link fixes (epic→goal, feature→epic, q-labels). **Gate before writing** to Jira/Confluence — a Confluence page after the publication question (`references/native-surfaces.md` §3: what it holds, where, who can open it there — and again before updating anything published earlier); preserve existing labels.

### Step 4b — Onboard (mode `onboard`)
Propose the new entity's name, labels and goal link per `planning-core` sec. 2 and 4; the same gate before writing as Step 4. **Pre-mortem (since v3.9.0, P4; `references/judgment-points.md` §7)** — only for a new mission or initiative, or a new epic when the request carries goal or outcome text; never a feature, never an existing entity. Derived, never asked:
- 2–3 causes in the §7 order: the request's stated assumptions and risks, then this run's own signals (dependencies Step 3 flags as unformalised, a goal the goal map lacks), each with an early signal; nothing beyond what the request, the Jira links or the goal map state. One kill criterion: signal, threshold and date from the request or the linked goal, else `⚠️ TBD`; then stop, pivot or descope.
- Rendered from `templates/built-in/partial/pre-mortem-v1.md` (user `_partials/pre-mortem.md` first) per `references/template-protocol.md` T-5 steps 1–3 and 3d only — no footer (3a), no 3c on a Jira body — so no hint comment or template syntax reaches the write.
- Shown in the existing approval preview, where the PM edits it (a deletion is never learned, `references/self-improvement.md`), and written with the entity: the new Confluence page body, else the epic description. When the kill criterion's threshold and date are both `⚠️ TBD`, the block stays in the preview and is written nowhere — neither the page nor Jira — unless the PM sets one of them there. `tree`, `audit` and `map` are unchanged.

### Step 5 — Tree (mode `tree`)
Generate the Goal→Initiative→Epic→Feature tree (features as `code—name`) + gap report. Per `roadmap-artifacts.md` sec. 4. Workspace + library storage.

**Tree depth (since v3.6.0, `references/planning-core.md` §7).** When `role_defaults.planning_view` is `rollup`, the tree is presented goals → initiatives first (epic and feature counts, gaps per initiative) and expands epics and features on request; `slice` presents the full tree down to epics and features, as before. The saved tree, the gap report, the labeling checks and the write gate are the same for every profile; an automated run keeps the pre-v3.6.0 presentation.

### Step 6 — Save to Vault (Optional)
Per `references/vault-protocol.md` → Vault Save. IF vault_level > L0 AND sync_mode != "off": `vault_save({ type: "roadmap", product: active_product, skill: "roadmap-architect", skill_version: "0.7.0", tags: [goals covered], content: structure tree + gap report, related: [[goal artifacts]], extra_frontmatter: { subtype: "structure-tree", gaps_count } })` → "Saved to Vault: Roadmaps/{product}/…" — a story map the same way with `subtype: "story-map"` and its own fields (`product`, `epic`, `slices`, `baseline`; Step 7a), named `story-map-<slug>`.

### Step 7 — Story map (mode `story-map`, since v4.6.0)
Read `references/story-map-protocol.md` whole first; it is the procedure. Three entries: «побудуй мапу історій» (from a concept, requirements, an epic or the conversation), «зріж реліз / запиши MVP», «онови мапу». The vault note is the source of truth; a map has no dates and never a Jira issue per card. Without SHELL — the note only, and the one line of protocol §10.
- **7a Build.** Inputs in the protocol's §2 order, every card with its source marker; nothing invented — a step without a card stays a `⚠️` gap. Write the note (§4: `type: roadmap`, `subtype: story-map`, one table of cards) through Step 6 — without a vault, a workspace file — and show the backbone, the cards, the slices with their outcomes and the gaps as one preview.
- **7b Quality.** `python3 scripts/story_map.py check --note <note>` plus the semantic pass of §3 (one card, one value; an edge case its own card). Every finding is a proposal in the preview — the PM decides, nothing blocks.
- **7c Slice and write.** The PM names a slice and its outcome (else `⚠️ TBD`). Writing it into the feature structure is §5: one message with the linked cards, the new stubs (`n` from CQL, never guessed), the slice label, the findings, the write checklist (`references/artifact-style-gate.md` → Host write gate) and who reads the space; one «так» → Step 4b writes the stubs with no pre-mortem, the codes go into the note, then `story_map.py baseline --note <note> --slice <id>`. FE/BE come later from `task-creator`.
- **7d Publish.** `story_map.py render-html --note <note> --out <file> --lang <user.language>` always writes the page next to the note. Then `references/artifact-publishing.md`: key `roadmap-architect/<product>/story-map-<slug>`; `python3 scripts/publications.py find --key <key> --note <note>` first; one question — the board first (kind `board`, the primary kind; its audience per protocol §7), the progress dashboard (kind `dashboard`), «лише файл» — naming what, where and who sees each place, «нова версія N» for a place already recorded. After the «так»: publish, read the board back as its state (§8), and `python3 scripts/publications.py record --key <key> --note <note> --surface <surface> --kind <kind> --id <id> --url <url>` per place. No board tool → the page, and once `tools_scan.py suggest --skill roadmap-architect --need board` (`references/tool-registry.md` §4). Sharing — a separate question, named people only.
- **7e Refresh.** «Онови мапу»: `product-reporter` `initiative-status` per epic, depth feature → the status file (§9) → `story_map.py progress` → «Прогрес» in the note and the page. Before a new board version: read back, `story_map.py board-diff --last <state> --now <read> --note <note>`; changes → one question «забрати в мапу / перезаписати мої картки / нова дошка» (§8); the team's items are never deleted. Then the version question of 7d. No scheduled refresh.

## Quality Standards
- Don't invent links — only Jira links / goal map / explicit PM input; the rest = "break, please formalize".
- Conventions — from `planning-core`/local-context, not hardcoded.
- Features — `code — name` as a list.
- Write to Jira/Confluence only after PM approval — for a Confluence page, the publication question (`references/native-surfaces.md` §3). Language — `user.language`.
- Story map: every card with its source, no dates, the note is the truth — the board and the dashboard are renders; the team's board edits reach the note only through the question of protocol §8.

## Skill Chaining
→ `quarterly-planning` / `project-planning` (hands off clean structure; a story map's slices become the arc's milestones) · → `task-creator` (decomposition; FE/BE for a slice's features) · → `product-reporter` `initiative-status` (the map's progress).

## Additional Resources
`references/planning-core.md`, `dependency-model.md`, `roadmap-artifacts.md`, `local-context-protocol.md`, `template-protocol.md`, `persistent-storage.md`, `self-improvement.md`, `jira-data-protocol.md`.

**End of run — the inbox (since v3.21.0).** What this run learned about the user's context (a record of their store, never a person's profile or a note) goes to the inbox as deltas — urgent ones asked at once in one question, the rest one line `У скриньці +N`: `references/context-protocol.md` §5i.

## Routing

The `description` above is short on purpose: a host with many skills shows only part of the skill listing, or skill names alone (`references/host-profiles.md` §7). The full set of phrases and boundaries that route here, as the description carried them up to v3.10.0:

> Own the work structure — missions → initiatives → epics → features, labeling, roadmap tree — no dates, no capacity. Not quarter plans (quarterly-planning), not forecasts (project-planning). UA — «наведи лад у структурі», «розміть епіки/фічі», «дерево roadmap», «звʼяжи епік з ціллю». EN — "tidy up the structure", "label epics/features", "find labeling gaps", "build the roadmap tree", "link an epic to a goal", "direction structure". Also UA — «знайди розриви розмітки», «структура напрямків».

Story map (mode `story-map`, since v4.6.0): UA — «мапа історій», «побудуй мапу історій з концепту», «user story map для епіку», «зріж реліз», «запиши MVP», «walking skeleton», «онови мапу», «прогрес по зрізах». EN — "build a user story map", "story map with release slices", "slice the MVP", "refresh the story map". Not a customer journey map (`cjm-research`), not a diagram or a board picture on its own (`diagram-prototyper`), not dates for the slices (`project-planning`), not Jira tasks for a feature (`task-creator`).
