# subagent-delegation.md

> Shared reference. Standard pattern for delegating heavy read / fan-out work to subagents so the main agent's context stays clean and independent reads run in parallel. Used by skills with large search/fetch steps (meeting-processor, knowledge-library, team-ops-reporter, and any future fan-out skill).

## When to delegate

Delegate to subagent(s) when a step would otherwise pull a lot into the main context, e.g.:
- Reading/scanning **many items** (rule of thumb: > ~8 documents/meetings/pages/issues).
- Running **multiple independent** searches/fetches (several sources, modes, or paginated pages).
- Any pass where the main agent only needs the **conclusion**, not the raw material.

Do NOT delegate trivial single reads, or work that needs tight back-and-forth with the user.

## How (the pattern)

1. **Split** the work into independent batches (by source, by page, by item group). Keep batches comparable in size.
2. **Spawn subagents in parallel** — one per batch — in a single dispatch when batches are independent.
3. Each subagent does its reads and returns a **compact structured result** (only the fields the next step needs) — never raw document dumps. Include source links/keys for traceability.
4. The **main agent aggregates** the structured results (merge, dedupe, rank), then proceeds.

## What a subagent must return

- A small, structured payload (table/list of {item, key fields, source link}). Not full text.
- Explicit "nothing found" when empty.
- Source markers so the final artifact can cite them.

## Rules

- **Data policy:** subagents follow `data-policy.md` — internal data stays internal; never send internal content to external LLMs.
- **Cap batch size** and total subagents (sensible limit, e.g. ≤ 6 parallel) to avoid overload; queue the rest.
- **Dedupe** across batch results in aggregation.
- **Determinism over cleverness:** subagents extract/summarize per a fixed schema; the main agent makes decisions.
- **Fallback:** if subagents are unavailable, the skill runs the fan-out inline (slower, heavier context) — behavior unchanged, just less efficient.

## Fan-out points by skill

| Skill | Fan-out step | Batch by | Subagent returns |
|---|---|---|---|
| `meeting-processor` | Search mode (query across many meetings) | meeting | per-meeting: decisions, action items, relevant quotes + link |
| `knowledge-library` | Search (multi-mode / many sources) | source group / mode | per-source: title, key insight, trust score, link |
| `team-ops-reporter` | Jira fetch for member-review / quarter-review (paginated, per period) | page / month / member | extracted rows (status, SP, transitions) per the data protocol |

> The fan-out is an efficiency layer, not a logic change: the same data is gathered, just off the main context. Each skill names its own fan-out points and keeps its existing output format.
