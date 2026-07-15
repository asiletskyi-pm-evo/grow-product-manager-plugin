---
name: decision-log
version: 0.2.2
description: Log and retrieve key product decisions as ADR-style records in the vault Decisions/ area — context, options considered, decision, rationale, consequences, links. Use when the user says "log this decision", "why did we decide X", "show decisions about Y", "supersede that decision", "decision log". Українською — "зафіксуй рішення", "чому ми вирішили…", "покажи рішення по…", "перегляньмо це рішення", "журнал рішень". Also invoked by other skills (meeting-processor, experiment-tracker, planning skills) when their outcome contains a decision worth recording. Do NOT use for meeting notes as such (meeting-processor) or experiment state (experiment-tracker) — this skill records decisions and answers "why".
---

# Decision Log

Product decisions evaporate from chats and meetings; three months later nobody remembers why the flag was rolled back or why SaaS-template won over custom. This skill gives every significant decision a permanent ADR-style record with links to the evidence — and answers "чому ми вирішили X?" from the accumulated log.

## Prerequisites
- `references/local-context-protocol.md` — Step 0.
- `references/vault-protocol.md` + `references/vault-schema.md` — the `decision` artifact type (Decisions/) already exists in the taxonomy.
- `references/persistent-storage.md` — fallback storage when no vault is configured.
- `references/roi-frameworks.md` — optional cost-of-decision (ROAIP) field.
- `references/goal-frameworks.md` — optional Tell-and-Sell commitment status.

## Storage
- **Vault configured (L1/L2):** `Decisions/{product}/decision-{topic}-{date}.md` via `vault_save({type: "decision", …})`.
- **No vault (L0):** `~/.grow-pm/decisions/` with the same file format; on later vault connection these migrate via the standard mirror protocol.

## Record format (ADR-style)

```markdown
# Decision: {title}
- **Date / Owner:** {date} / {who decided}
- **Status:** active | superseded (→ [[link]])

## Context
What was being decided and why now (1-3 sentences, links to trigger: meeting, experiment, analysis).

## Options considered
1. {option} — pros / cons
2. {option} — pros / cons   (minimum 2; "do nothing" counts)

## Decision
The chosen option, stated plainly.

## Rationale
Why this one — evidence links (readout, research, metrics with inline periods).

## Consequences & risks
What this commits us to; what we monitor; revisit-by date (optional).

## Cost & commitment (optional)
- **Cost of decision (ROAIP):** what this decision/investment costs and its expected ROI / annual return (`references/roi-frameworks.md`) — fill when the decision has a quantifiable economic weight.
- **Commitment (Tell and Sell):** who committed to the decision and how (`references/goal-frameworks.md` → Tell and Sell) — "just told" vs "sold and committed", and by whom. Distinguishes a directive from a shared commitment.

## Links
[[related artifacts]] — MoM, experiment, requirements, roadmap items, Jira epics.
```

Frontmatter per `vault-schema.md`: `type: decision`, `product`, `tags` (topic, area), `related`, plus `supersedes` / `superseded_by` when applicable, and optional `decision_cost` / `decision_roi` / `commitment` fields. **When the record names a revisit-by date, write it to the `revisit_by` frontmatter field as well** — that field is what `focus-advisor` filters to surface overdue revisits; a date left only in the body is invisible to it.

## Modes

### Mode: log (default)
1. Collect the record fields — from the invoking skill's context when chained (meeting decision block, experiment decide payload, planning outcome), or via short dialogue when standalone. Do not interrogate: infer what's already in context, ask only for gaps (especially **options considered** — the field people skip and later regret).
2. Show the draft record. **Gate: confirm/correct before saving.**
3. Save (vault or fallback), display the link. If the decision implies work → offer `task-creator`.

### Mode: search ("чому ми вирішили X")
1. Search Decisions/ by topic/tags/product (vault search per `vault-protocol.md`; L0 → grep the fallback folder).
2. Present matches: title, date, status, one-line decision. Open the full record on request — the Rationale section IS the answer to "why".
3. Nothing found → say so honestly and offer to log the decision now if the user knows it.

### Mode: revisit
1. Locate the existing record; display it.
2. Collect the new decision (same format, Context = what changed since).
3. Save the new record with `supersedes: [[old]]`; update the old one: `status: superseded`, `superseded_by: [[new]]`. **Both writes gated.**

## Quality Standards
- Never invent options or rationale — only what the user/invoking skill actually provides; gaps stay visibly empty ("options not recorded").
- One decision = one record; bundles get split.
- Superseding never edits history — old records are marked, not rewritten.
- Every record carries at least one evidence link when evidence exists.
- Language — `user.language`.

## Skill Chaining
← `meeting-processor` (M10: key decisions from MoM) · ← `experiment-tracker` (decide mode) · ← `quarterly-planning` retro / `project-planning` replan (scope decisions) · ← `feedback-triage`, `goal-setter`, `one-on-one` (decision outcomes) · ← any skill with a decision outcome · → `task-creator` (when the decision spawns work) · → `focus-advisor` (overdue `revisit_by` dates surface as tactical signals — `focus-signals.md` §6).
