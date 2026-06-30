# roadmap-artifacts.md

> Shared planning-suite reference. Formats of **planning** artifacts (decision/forecast). These are NOT team-ops-reporter reports (ops-report templates) — those describe fact; these capture the plan. Consumers: `quarterly-planning`, `project-planning`, `sprint-planning`, `roadmap-architect`.

---

## 1. Quarterly roadmap (Confluence page)

Sections (validated by a run of Q3 FET):
1. **Header panel** — artifact/team/period/author + method (CQL by label + Jira statuses + capacity).
2. **Quarter capacity** — table by platform: demand / ceiling / state (status-lozenges green/yellow/red); panel on platform granularity (FE slices → next quarter).
3. **Main focuses** — focus / why table.
4. **Roadmap timeline** — Gantt table by sprint (`<td colspan>` = initiative bar; status-lozenge "in progress"/"planned").
5. **Main initiatives** — Goal → Initiative → Epic → Feature tree; **features as a list of `code — name`** in the cell (`<ul><li>`), not bare numbers; status column — lozenges.
6. **Carried over to the next period** — feature table (as a list) + reason.
7. **Method** — note panel.

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

## 7. Demarcation from team-ops-reporter

| Artifact | Whose |
| --- | --- |
| ops-report (sprint/quarter/initiative/member review) | team-ops-reporter (fact) |
| quarterly roadmap, project arc, structure tree, capacity-gate, live dashboard | planning-suite (plan/forecast) |

The shared Jira-data source — `jira-data-protocol.md`. A planning artifact may contain a "fact" block, rendered by delegating to team-ops-reporter.
