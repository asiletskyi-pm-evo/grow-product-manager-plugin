# roadmap-artifacts.md

> Shared planning-suite reference. Formats of **planning** artifacts (decision/forecast). These are NOT product-reporter reports (ops-report templates) — those describe fact; these capture the plan. Consumers: `quarterly-planning`, `project-planning`, `sprint-planning`, `roadmap-architect`.

---

## 1. Quarterly roadmap (Confluence page)

Sections (validated by a real quarterly run):
1. **Header panel** — artifact/team/period/author + method (CQL by label + Jira statuses + capacity).
2. **Quarter capacity** — table by platform: demand / ceiling / state (status-lozenges green/yellow/red); panel on platform granularity (FE slices → next quarter).
3. **Main focuses** — focus / why table.
4. **Roadmap timeline** — Gantt table by sprint (`<td colspan>` = initiative bar; status-lozenge "in progress"/"planned").
5. **Main initiatives** — Goal → Initiative → Epic → Feature tree; **features as a list of `code — name`** in the cell (`<ul><li>`), not bare numbers; status column — lozenges.
6. **Carried over to the next period** — feature table (as a list) + reason.
7. **Pre-mortem & kill criteria** (since v3.9.0, §8) — the failure-causes table in a note panel, the kill-criteria table under it. After Carried over in both the `rollup` and the `slice` order (`planning-core.md` §7 moves only sections 2–5).
8. **Method** — note panel.

HTML via `updateConfluencePage`/`createConfluencePage` (`contentFormat: html`): status — `<span data-type="status" data-color="...">`, panels — `<div data-type="panel-info|success|note">`, `colspan` in tables works.

## 2. Live dashboard (cowork artifact)

Self-contained HTML (light mode, `:root{color-scheme:light}`). Static: capacity bars (target 85% / ceiling 100% markers), Gantt timeline. Live (on open): epic statuses ← `getJiraIssue` per-key; feature inventory ← CQL by quarter label. Registered via `create_artifact` with `mcp_tools`; the refresh button — in the panel header (do not duplicate).

## 3. Project roadmap (arc, project-planning)

Multi-quarter Gantt of a single initiative: epics/features as bars across quarters, **critical path** highlighted, forecast completion date, **drift vs baseline** (for `replan`), what-if by allocation %. Format — HTML dashboard or Confluence table.

## 4. Structure tree (roadmap-architect)

Goal → Initiative → Epic → Feature (the whole structure, without quarter scope). Plus a **marking-gaps report** (features/epics without quarter/goal/code). Format — Confluence page or markdown.

## 5. Interactive capacity-gate (corrections)

A screen with per-platform load bars + feature/platform-slice toggles into the next period; live recompute; "lock scope" button (via `sendPrompt`). For the scope-correction phase.

## 6. Conventions (all artifacts)

- Features — always `code — name` as a list, not bare numbers/ranges.
- Every number — with an inline period (quarter/sprint, number of sprints, normalized/not).
- AI estimates — "pending TL confirmation" marker; the decision is the PM's.
- **Draft ≠ final:** writing to Confluence/Jira — only after explicit PM approval; draft and final — separate files.
- Storage: workspace + library (`persistent-storage.md`).
- Language — `user.language`.

## 7. Demarcation from product-reporter

| Artifact | Whose |
| --- | --- |
| ops-report (sprint/quarter/initiative/member review) | product-reporter (fact) |
| quarterly roadmap, project arc, structure tree, capacity-gate, live dashboard | planning-suite (plan/forecast) |

The shared Jira-data source — `jira-data-protocol.md`. A planning artifact may contain a "fact" block, rendered by delegating to product-reporter.

## 8. Pre-mortem and kill criteria — quarter plan and onboard (since v3.9.0)

P4 of `pm-mental-model.md`. The rules — the order of causes, the kill-criteria row, never asked, a deletion respected — are `judgment-points.md` §7; the block is `templates/built-in/partial/pre-mortem-v1.md` (a user `_partials/pre-mortem.md` first). This section adds only each step's inputs and where the block goes. Which planning steps render one, and the read-back, are `planning-core.md` §8: nothing else in this file carries one — not the live dashboard (§2), the project arc (§3), the structure tree or gap report (§4), the capacity-gate screen (§5) or a sprint plan.

**Quarter plan** (`quarterly-planning`, plan and full modes):
- **When** — rendered once per run, at the first scope lock; a later Step 5 edit, recompute or re-lock does not re-render it (the PM edits it at approval). It goes into the draft and is published with the page.
- **Placement** — on the §1 structure (no roadmap template applies) it is section 7, rendered there from the partial, so `template-protocol.md` T-5 step 3b finds it and adds no second one. A user's or product's own roadmap template gets it only through `{{> pre-mortem}}`, where that template puts it.
- **Causes** (2–3, in the §7 order) from this run's own signals:
  - a debate on the plan in this session, when one ran;
  - `assumed` inputs — analogy estimates still "pending TL confirmation" (`capacity-model.md` §8), a goal missing from the goal map, unconfigured capacity; the marker stays their label (`planning-core.md` §6);
  - last quarter's plan-vs-actual as the base rate, and its carry-over and miss reasons (Step 2 or 2-lite);
  - 🟡 / 🔴 platforms at the capacity gate (`capacity-model.md` §7), and the dependencies and graph gaps the run found (`dependency-model.md` §6).
- **Kill criteria** — one per main focus:
  - the signal is the focus's outcome metric or delivery milestone;
  - the threshold comes from the focus's goal or the plan, else `⚠️ TBD`;
  - the date is no later than the quarter end — a sprint checkpoint where the plan names one;
  - then: descope, move to the next quarter, or stop.
- **Refresh** keeps an existing section verbatim and never adds one, so a page published before v3.9.0 stays without it. The retro renders none — it reads the previous plan's criteria back (`planning-core.md` §8).

**Onboard** (`roadmap-architect` Step 4b):
- **Entities** — a new mission or initiative; an epic only when the request carries goal or outcome text; never a feature or an existing entity.
- **Causes** come from the request text, a goal link missing from the goal map (named as the gap, never an invented link) and the unformalised dependencies around the entity that the run found (`dependency-model.md` §6 graph gaps).
- **Kill criterion** — one per entity: the outcome signal of the linked goal or the request; threshold and date from the request or the linked goal, else `⚠️ TBD`; then: stop, pivot or descope.
- **Render** — `template-protocol.md` T-5 steps 1, 2, 3 and 3d only (variables, language, blocks; hint comments dropped). `onboard` skips Step T, so there is no footer (3a), no label pass (3c) and no template marker; a cited input keeps the label it carries. Shown in the existing approval preview, then written with the entity: the new page body of a mission or initiative, or the Jira epic description when no page is created.
- **All-TBD** — when the kill criterion has neither threshold nor date (both `⚠️ TBD`), the block stays in the preview and is written nowhere — neither the page nor Jira — unless the PM sets a threshold or a date there.
