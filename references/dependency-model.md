# dependency-model.md

> Shared planning-suite reference. Dependency graph and sequencing at two granularity levels. Consumers: `project-planning` (epic/feature dependencies, arc critical path), `sprint-planning` (work-type inside a feature, readiness). Flow config — in local-context → Planning → Development Flow.

---

## 1. Two dependency levels

| Level | Granularity | Who uses it |
| --- | --- | --- |
| **Macro** | epic ↔ epic, feature ↔ feature | `project-planning` — sequencing and project arc critical path |
| **Micro** | work-type inside a feature (Design/BE/Analytics → Client → QA) | `sprint-planning` — readiness "what can be taken now" + order violations |

Same machinery (DAG, topo-sort), different granularity.

---

## 2. Dependency sources

1. **Jira issue-links** (primary): per FET convention — a `Blocks` chain (sequence) + `Relates` pairs (between entities of one feature). Pull via `getJiraIssue` (field `issuelinks`) per-key.
2. **Feature names/numbering** (`SHOPEX-{epic}.{feature}`) — grouping under an epic.
3. **Development Flow** from local-context — the team's typical work-type sequence (micro level).
4. **PM input** — manual dependencies not present in Jira (gate clarification).

> If a dependency exists in a mockup/concept but is not formalized as a Jira link — surface it to the PM as a "graph gap" (candidate for formalization), do not invent it.

---

## 3. Building the graph

1. Nodes = epics/features (macro) or work-type tasks of a feature (micro).
2. Edges = dependency direction (A → B = "B after A").
3. **Topological sort** → a linear sequence that respects all edges.
4. **Critical path** — the longest chain by total volume (SP); its shift = shift of the whole schedule.
5. **Cycle detection** — if A→B→…→A, surface it (the graph cannot be executed as is).
6. **Dangling/missing dependencies** — a feature with no link where a sequence is expected → flag.

---

## 4. Work-type DAG (micro) and the readiness rule

Default flow (override from the team's Development Flow):

```
Requirements → Design → {BE, Analytics} → Client (FE / iOS / Android) → QA → Release
```

**Readiness rule:** a downstream work-type is **ready to plan** when ALL of its upstream prerequisites have reached the readiness threshold.

- Threshold (default, override in Development Flow): status ∈ {on review, in test, ready for test, done, closed} — i.e., the implementation stage is passed (not necessarily "done").
- **Violation:** a downstream is planned into a sprint while an upstream is below threshold → flag "X before {prerequisite}" with an explanation; decision is the PM's (conscious confirmation), not a hard block.

Example: Design=done, BE=on review, Analytics=in test → Client = **Ready** (client implementation can be planned). If Analytics=planned → Client in the sprint = **violation**.

---

## 5. Parallelism limit

How many features/slices of an initiative the team runs simultaneously is limited by platform capacity (`capacity-model.md`). When scheduling (`critical_path_schedule`), do not place more in parallel than the platform can hold — otherwise the duration forecast will be unrealistically optimistic.

---

## 6. Outputs

- **Sequence** (topo-sort) — order of epics/features or work-types.
- **Critical path** — the chain that determines duration; mark its elements separately (their shift is the most expensive).
- **Readiness list** (micro) — Ready / Blocked (by what and up to which status) for each candidate.
- **Violation list** — attempts to plan a downstream before an upstream.
- **Graph gaps** — expected but unformalized dependencies.

---

## 7. Quality / caveats

- Do not invent dependencies — only from Jira links, Development Flow, or explicit PM input; everything else = "gap, formalize it".
- Recompute the critical path on every `replan` — carrying over one of its elements shifts the whole arc.
- The readiness threshold and the flow itself — from the team's Development Flow, not hardcoded.
- Mark sequencing recommendations "pending PM/TL confirmation".
