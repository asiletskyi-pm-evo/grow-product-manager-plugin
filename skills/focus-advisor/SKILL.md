---
name: focus-advisor
version: 0.5.0
description: PM attention dispatcher — scans the PM's context (sprint cycle, calendar, mail, meetings, Jira, roadmap drift, backlog, A/B tests awaiting decisions, capacity, goals, metrics) and recommends focuses with reasons and next steps at three horizons — daily, tactical (sprint–quarter), strategic (quarter–year) — chaining to the right skill. Use whenever the PM asks what to do or focus on — "на чому сфокусуватись", "що мені робити зараз/сьогодні", "фокус дня/тижня", "тактичний фокус", "стратегічний фокус", "куди фокусувати команду", "де великі можливості для продукту", "розбери мою пошту і календар", "до яких зустрічей готуватись", "чи все ок з метриками", "what should I focus on", "daily focus", "tactical focus", "strategic focus", "morning brief", "покажи focus board" — and for scheduled/headless briefs. Do NOT use for planning the sprint (sprint-planning), building roadmaps (quarterly-/project-planning), or deep metric analysis (product-analysis / cjm-research) — it recommends and chains, it does not execute.
---

# Focus Advisor

> **Path rule.** A bare `references/<file>.md` in this file is read from this skill's own `references/` if the file exists there, otherwise from the **shared** `references/` at the plugin root. Resolve the root as `${PLUGIN_ROOT}`, else `${CLAUDE_PLUGIN_ROOT}`, else the directory that contains `skills/`, found by walking up from this folder (`references/host-profiles.md` §6). Never continue without a protocol named here.

The 4th height of the suite — **the PM's attention** above structure/quarter/sprint. Collects context signals, ranks them, recommends 1–3 focuses, and **chains execution to the right skill. The PM decides.** This skill never plans, analyzes, or writes work artifacts itself — doing so would break the suite invariant ("stay at your height, chain the rest").

## Prerequisites
- `references/local-context-protocol.md` — Step 0 + Planning (sprint anchor/cadence) + **Focus** section (sources, VIP senders, PM goals, cadence overrides — format in `references/focus-signals.md` §8).
- `references/focus-cadence.md` — cycle position + ritual calendar (deterministic core).
- `references/focus-signals.md` — signal registry, collectors, packet format, cache, mail/calendar detectors.
- `references/focus-scoring.md` — ranking, journal dedup, honesty rules.
- `references/jira-data-protocol.md` — Jira plumbing (per-key, no bulk JQL).
- `references/people-context-protocol.md` — manager-rhythms signal source (roster + cadences, read-only).
- `references/integration-strategy.md`, `references/data-policy.md`, `references/persistent-storage.md`, `references/vault-protocol.md`.

## Step T — Template Resolution
`artifact_type: focus`, `subtype: daily-brief | tactical-brief | strategy-memo` (by mode), `product_id`, `language`.

## Modes

| Mode | Horizon | Status |
|------|---------|--------|
| `now` | today – this sprint | **v0.1** |
| `journal` | — | **v0.1** — review/close/snooze open focuses (see "Mode: journal") |
| `auto` | — | **v0.1** — detects horizon from phrasing/cycle |
| `tactics` | sprint – quarter | **v0.2** — 3–5 tactical candidates: roadmap drift, stale backlog, A/B decisions, capacity, team events |
| `strategy` | quarter – year | **v0.3 (this release)** — 2–4 strategic bets aligned to product goals/missions, with explicit "what we deliberately do NOT do" |
| `board` | — | **v0.3** — create/refresh the live "PM Focus Board" artifact (on platforms with live-artifact support; otherwise a static HTML file) |

## Headless contract (scheduled runs)

Invocation from a scheduled task prompt: `focus-advisor mode={now|tactics|strategy} headless=true` (e.g. daily morning `now`, Monday `tactics`, first week of the quarter `strategy`). Rules: (1) skip all gates — **no side-effect actions at all** (no Jira/Gmail/Confluence writes, no auto-launching chained skills); (2) metrics health-check chain only if `Focus → Scheduled → healthcheck: on`; (3) output = brief in chat **and always as a file** (Step 7) with journal status `proposed`; chains render as "next steps" with ready-to-paste phrases; (4) collector cache is kept warm for the follow-up interactive session.

## Pipeline

### Step 0 — Local context
Per `local-context-protocol.md`: product, Planning (anchor/cadence), Focus section. Focus section missing → run once with safe defaults (mail/calendar on, 7-day window, default thresholds) and offer Focus setup via `plugin-configurator` at the end.

### Step 1 — Horizon + scope. Gate (skipped in headless)
Confirm horizon (auto-detect from phrasing/cycle position: "сьогодні/зараз" → now, "квартал/команда/беклог" → tactics, "рік/можливості/напрямки" → strategy; quarter boundary nudges toward strategy) and period.

### Step 2 — Collect signals
Per `focus-signals.md`, only the sources of the confirmed horizon. **now** (§3–4): cycle position, calendar (meetings needing prep), mail (live unanswered letters — two-stage filter), recent meetings' open action items, Jira tails. **tactics** (§6): quarterly roadmap plan-vs-actual and drift, backlog staleness (ICE age), features missing prerequisites ahead of next sprints, A/B tests awaiting decision, capacity and team-event signals. **strategy** (§7): product goals/missions (pinned source), NPS waves and love/hate themes, CJM/funnel trends (freshness-guarded), knowledge-library research signals, leadership-meeting mandates, white spaces in the PM's zones. Honor cache TTL. Fan out collectors via `subagent-delegation.md` when available; inline otherwise. Each collector returns signal packets only.

**Manager-rhythms signal (People-contour, read-only).** Derived from the team's person profiles (`references/people-context-protocol.md` roster) and their cadences — surfaces People-contour rituals that are due (energy/P&L-of-attention signals):
- **weekly:** goal reports read? 1-1s held this week? meeting follow-ups sent?
- **monthly:** every direct report "touched" with a 1-1 in the last month? (feeds `one-on-one` coverage)
- **quarterly:** goals reviewed / performance reviews due?
These become candidates just like cadence rituals; chains route to `one-on-one` (coverage), `product-reporter` (unread goal reports), `performance-review` (reviews due), `goal-setter` (goals stale). Read-only — focus-advisor never writes profiles.

### Step 3 — Cadence check
Per `focus-cadence.md`: due rituals (including recently missed ones) become high-priority candidates.

### Step 4 — Score and rank
Per `focus-scoring.md`: journal dedup → **now**: urgency+impact+unblock → 1–3 focuses; **tactics**: ICE + capacity realism + goal alignment (§4) → 3–5 candidates; **strategy**: goal/mission alignment × lever size × evidence strength (§5) → 2–4 bets. The rest goes to "також на радарі". Insufficient signals → say so honestly.

**"Choose one" final filter (daily / `now`).** After ranking the daily focuses, apply a final single-pick filter: if you could do only **one** thing today, which moves the goal most? Lead the brief with that one focus (the rest stay as "також на радарі"). Cuts the overloaded-PM's analysis paralysis — the daily brief has a clear #1, not a tie.

### Step 5 — Focus brief
For each focus: what, why now (signals with links), cost of delay (one sentence), suggested next step. Subtype by mode: `daily-brief` / `tactical-brief` / `strategy-memo`. Tactical brief adds: quarter position (sprints left, capacity used vs plan) and a "decisions waiting on you" section (A/B tests, approvals). Strategy memo structure: current state (facts with sources) → 2–4 bets (each: what, why — data-backed, expected metric effect, first steps) → **"what we deliberately do NOT do"** → data-hygiene preconditions → next 2 weeks. A strategy memo without exclusions is a wish list. Footer: degraded collectors, cache ages. Language — `user.language`.

### Step 6 — PM chooses. Gate (skipped in headless)
Per focus: **(a) chain** to the executing skill with prepared arguments; (b) create a task/reminder; (c) snooze with a date. Chain map:

| Recommendation | Chain |
|---|---|
| Sprint-boundary ritual due | sprint-planning `groom`/`plan`, product-reporter `sprint-review` |
| Important letter unanswered | reply draft (Gmail `create_draft` — gate) / task |
| Meeting tomorrow needs prep | product-analysis (slice) / design-bridge (deck) / talking points from transcripts |
| Metrics day / "чи все ок з метриками" | product-analysis + cjm-research health-check (verify source freshness first — `focus-signals.md` §5) |
| Open action items from meetings | meeting-processor |
| Feature blocking next sprint lacks requirements | requirements-creator |
| Stale backlog / blurred focuses | brainstorm-features / quarterly-planning `refresh` |
| Roadmap drift beyond threshold | project-planning `replan` |
| A/B test waiting for a decision | experiment-tracker `readout` (it owns test state and chains onward to product-analysis for the readout, then decision-log) |
| Decision revisit-by date reached | decision-log (`revisit` — the decision said "re-examine by this date") |
| Team event ahead (perf review, onboarding, booking deadline) | task/reminder + product-reporter `member-review` where relevant |
| Strategic bet needs deeper evidence | product-research (competitive/market) / cjm-research / knowledge-library |
| Strategic bet accepted → needs a concept | write-concept, then quarterly-/project-planning to schedule |
| Goals/missions source stale or missing | knowledge-library (refresh pinned source) + Focus config update |
| Direct report not "touched" in > a month | one-on-one `coverage` |
| Goal reports unread / follow-ups unsent | product-reporter (goal-report) / meeting-processor |
| Performance reviews due this quarter | performance-review |
| PM overloaded with operations | delegation-coach |

### Step 7 — Save artifacts (mandatory, NOT optional)
Every artifact this skill produces is persisted to the user's local repository:
- brief → `~/.grow-pm/focus/briefs/YYYY-MM-DD-{mode}.md`;
- journal update → `~/.grow-pm/focus/focus-log.md` (proposed → chosen → done/snoozed);
- cache → `~/.grow-pm/focus/cache/` (packets only, no message bodies);
- Vault mirror after every write per `vault-protocol.md` (`type: focus-brief`), recovery pattern as in knowledge-library (if `~/.grow-pm/focus/` is empty — restore from Vault);
- artifacts produced by chained skills (slices, decks, plans) are saved by those skills' own Step V — focus-advisor links them in the brief and journal.

## Mode: journal — close the loop on what was already chosen

The brief modes (`now`/`tactics`/`strategy`) run the Step 0–7 pipeline above. `journal` does **not**: it neither collects signals nor ranks anything — it settles the focuses already in the log. (Until v2.1.0 this mode was listed with no workflow and no output, and referenced "streaks", a word that appeared nowhere else in the plugin.)

1. **Step 0** (local context), then read `~/.grow-pm/focus/focus-log.md`.
2. Show every focus **not** in a terminal state, grouped: `chosen` (in progress, with days-since), then `proposed` carryovers, then `snoozed` whose date has passed. Terminal states (`done`, and `snoozed` still in the future) are not shown — this is a working list, not a report.
3. Per focus, offer via `AskUserQuestion`: **done** (closed — optionally record the outcome in one line) · **snooze** (until a date — the 3+ snooze note from `focus-scoring.md` §2 applies) · **drop** (no longer relevant — recorded as `done` with reason "no longer relevant", not deleted) · **keep** (stays as-is).
4. **Gate**, then write the transitions to the journal (append, never rewrite history). Refresh the board if one exists (Step 7b).
5. Output: a one-line summary of what moved ("2 closed, 1 snoozed to Aug 4, 1 still open since Jul 6") plus, if a focus has been `chosen` for more than 2 cycles, the honest nudge — finish it, delegate it, or close it deliberately.

Nothing is auto-closed. A focus the PM never revisits stays open and keeps appearing — that visibility is the point.

### Step 7b — Live "PM Focus Board" (mode `board`, or offered after any brief)
A persistent one-glance panel of the PM's attention. Contract:
- **Content sections:** current focuses (from the latest brief, with status from journal), due cadence rituals, signal freshness per collector, "також на радарі" backlog, chain shortcuts (ready-to-paste phrases).
- **Platforms with live artifacts** (e.g. Cowork `create_artifact`/`update_artifact`): dynamic parts re-query connector MCP tools on open (calendar events, Jira per-key statuses); local-only data (journal, briefs) is **baked in at render time** — artifacts cannot read local files, so focus-advisor refreshes the artifact on every run (update, not recreate; keep the artifact id in `~/.grow-pm/focus/board.yaml`).
- **Fallback:** no artifact tools → render static `~/.grow-pm/focus/board.html` and link it in the brief.
- Board is a **view**, not a store: journal stays the source of truth; no actions execute from the board beyond ready-to-paste phrases.

## Quality Standards
- Recommend and chain — never execute another skill's work inline; never launch chained skills without an explicit PM "go". In headless runs — no chained launches at all, with a single exception: the metrics health-check chain when `Focus → Scheduled → healthcheck: on` (see "Invocation from a scheduled task prompt" above).
- Every focus is verifiable: signal links always present; no invented urgency; "insufficient signals" is a legitimate brief.
- Mail: read-only screening; only live letters from humans become signals; bodies never leave the mailbox or enter the cache (`data-policy.md`); any write (reply draft) — gate.
- Jira: per-key reads only (`jira-data-protocol.md`).
- Step 7 persistence is mandatory in every mode, including headless.
- Demarcation: team's sprint focuses belong to sprint-planning; this skill owns the PM's personal attention.

## Additional Resources
`references/focus-cadence.md`, `references/focus-signals.md`, `references/focus-scoring.md`, `references/jira-data-protocol.md`, `references/integration-strategy.md`, `references/data-policy.md`, `references/persistent-storage.md`, `references/vault-protocol.md`, `references/subagent-delegation.md`, `references/self-improvement.md`.
