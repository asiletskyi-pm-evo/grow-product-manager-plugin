# Focus Cadence — the PM ritual calendar

**Overview:** Deterministic layer of `focus-advisor`: maps "where are we in the cycle" to "which ritual is due". Works from day one with zero history — this is what makes the skill useful before any scoring or journal data exists. Consumed by `focus-advisor` (Step 3); configured by `plugin-configurator` (Focus setup).

---

## 1. Cycle position

Compute from `local-context → Planning` (sprint cadence + anchor, e.g. `Sprint 55 = 2026-06-29`, 2 weeks):

```
days_since_anchor = today - anchor_date
sprint_number     = anchor_number + floor(days_since_anchor / cadence_days)
day_of_sprint     = (days_since_anchor mod cadence_days) + 1   # 1..cadence_days
week_of_sprint    = ceil(day_of_sprint / 7)                    # 1 or 2 for 2-week sprints
quarter_position  = which sprint of the quarter this is (from quarterly roadmap sprint range, if known)
```

If Planning section is missing → ask the PM for cadence + anchor once and offer to save via `plugin-configurator`.

## 2. Default ritual table (2-week sprint)

The table answers: *given today's cycle position, what does a disciplined PM do?* Every row carries the chain target so the recommendation is actionable, not abstract.

| Cycle position | Ritual | Why | Chain |
|---|---|---|---|
| Mon, week 1 | Week kickoff: metrics glance + week goals | Start of sprint execution; catch weekend anomalies early | metrics health-check (see focus-signals §5) |
| Fri, week 1 | Backlog grooming check | Mid-sprint: next-sprint candidates need estimates/requirements before pre-planning | sprint-planning `groom` |
| **Mon, week 2** | **Sprint pre-planning** | Team needs the next sprint shaped before it starts | sprint-planning `plan` |
| Thu, week 2 | Demo / review prep | Sprint results need packaging before the demo | team-ops-reporter `sprint-review` (draft) |
| Fri, week 2 | Sprint close: review + retro notes | Close the loop; carryover feeds next sprint's risk model | team-ops-reporter `sprint-review` |
| First week of quarter | Quarter retro + plan confirmation | Plan-vs-actual while memory is fresh | quarterly-planning `retro` |
| Last month of quarter | Next-quarter roadmap draft | Capacity and scope need lead time | quarterly-planning `plan` |
| Monthly (1st business day) | Backlog hygiene + decision log | Stale ideas and undocumented decisions accumulate silently | brainstorm-features / journal |

Defaults are exactly that — defaults. The PM's real calendar (configured rituals, team meetings) always wins over this table when they conflict.

## 3. Customization

Stored in `local-context → Focus → Cadence` as overrides to the default table:

```markdown
#### Cadence Overrides
| Cycle position | Ritual | Chain |
|---|---|---|
| [e.g. Wed w1] | [team sync prep] | [meeting prep] |
```

Rows with the same cycle position replace the default; new rows extend it. An override with ritual `off` disables a default row.

## 4. Resolution algorithm (Step 3 of focus-advisor)

1. Compute cycle position (§1).
2. Collect due rituals: today's rows + rows missed in the last 2 business days that the journal shows as not done (a missed pre-planning is still the top candidate on Tuesday).
3. Emit each due ritual as a signal packet (`source: cadence`, severity: high for sprint-boundary rituals, normal otherwise) into the common ranking (see `focus-scoring.md`).
4. Never silently drop a due ritual: if outranked by urgent signals, it still appears in the brief under "також сьогодні за каденсом".
