# Focus Scoring — ranking signals into a focus

**Overview:** How `focus-advisor` turns a pile of signal packets into 1–3 recommended focuses. The goal is not mathematical precision — it is a defensible, explainable ordering the PM can challenge. Every recommendation must carry its "why now" and its cost of delay in plain words. Consumed by `focus-advisor` (Step 4).

---

## 1. Operational scoring (mode: now)

Each candidate (signal packet or due ritual) gets three 1–3 marks:

| Dimension | 3 | 2 | 1 |
|---|---|---|---|
| **Urgency** | deadline/meeting today-tomorrow; sprint-boundary ritual; VIP waiting past threshold | this week | can wait past this week |
| **Impact** | touches PM's goals (Focus → PM goals), sprint goal, or many people blocked | one workstream | single task / courtesy |
| **Unblock** | others cannot proceed until the PM acts (review, approval, answer) | partially blocking | nobody waiting |

`score = urgency + impact + unblock` (3–9). Ordering rules:

1. Due cadence rituals with severity high (sprint boundary) rank above everything except same-day hard deadlines — process debt compounds quietly.
2. Ties break by **unblock** first (people waiting beat solo work), then by signal freshness.
3. Cap the brief at 1–3 focuses. A brief with ten priorities is a to-do list, not a focus. Everything else goes to a collapsed "також на радарі" list.

## 2. Journal dedup (before ranking)

Check `~/.grow-pm/focus/focus-log.md`:
- status `done` → drop the signal;
- status `snoozed` and snooze date not reached → drop, but count occurrences: a signal snoozed 3+ times gets a note in the brief ("це відкладається втретє — можливо, делегувати або закрити свідомо?");
- status `proposed` from a previous brief, still unresolved → keep and mark as carryover (carryover raises urgency by 1, once).

## 3. Honesty rules

- **Insufficient signals is a legitimate answer.** If collectors return little (quiet day), say so and fall back to the cadence ritual or the PM's standing goals. Never pad the brief with invented urgency.
- Every focus carries: the signal links (the PM must be able to verify in one click), the cost of delay in one sentence, and the suggested next step (chain).
- Degraded collectors (MCP down, stale cache) are reported in the brief footer — a recommendation built on partial context must look partial.

## 4. Tactical scoring (mode: tactics)

Reuse ICE from `skills/brainstorm-features/references/ice-framework.md` for backlog-type candidates, plus two modifiers: **capacity realism** (does the team have a slot this quarter — from `capacity-model.md`) and **goal alignment** (weight from Focus → PM goals). Roadmap-drift and blocked-feature signals rank by how many sprints of delay they imply.

## 5. Strategic scoring (mode: strategy)

Rank by: alignment with product goals/missions (pinned source) × size of the lever (order-of-magnitude, not precision) × evidence strength (data-backed > anecdotal; reuse trust scores from knowledge-library where applicable). Strategy briefs recommend 2–4 bets with explicit "what we deliberately do NOT do" — a strategy without exclusions is a wish list.
