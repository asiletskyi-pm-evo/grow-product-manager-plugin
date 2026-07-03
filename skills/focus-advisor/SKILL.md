---
name: focus-advisor
version: 0.2.0
description: PM attention dispatcher — scans the PM's full context (sprint cycle position, calendar, unanswered important emails, recent meetings and open action items, Jira tails, quarterly roadmap drift, stale backlog, A/B tests awaiting decisions, capacity signals) and recommends 1–3 focuses with reasons and next steps, chaining execution to the right skill. Use whenever the PM asks what to do or focus on — "на чому сфокусуватись", "що мені робити зараз/сьогодні", "фокус дня/тижня", "тактичний фокус", "куди фокусувати команду в цьому кварталі", "розбери мою пошту і календар", "до яких зустрічей готуватись", "чи все ок з метриками" (proposes a health-check chain), "what should I focus on", "daily focus", "tactical focus", "morning brief" — and for scheduled/headless focus briefs. "Стратегічний фокус" triggers here too (v0.2 responds with the closest chain + roadmap note). Do NOT use for planning the sprint itself (sprint-planning), building roadmaps (quarterly-/project-planning), or deep metric analysis (product-analysis / cjm-research) — this skill recommends and chains, it does not execute.
---

# Focus Advisor

The 4th height of the suite — **the PM's attention** above structure/quarter/sprint. Collects context signals, ranks them, recommends 1–3 focuses, and **chains execution to the right skill. The PM decides.** This skill never plans, analyzes, or writes work artifacts itself — doing so would break the suite invariant ("stay at your height, chain the rest").

## Prerequisites
- `references/local-context-protocol.md` — Step 0 + Planning (sprint anchor/cadence) + **Focus** section (sources, VIP senders, PM goals, cadence overrides — format in `references/focus-signals.md` §8).
- `references/focus-cadence.md` — cycle position + ritual calendar (deterministic core).
- `references/focus-signals.md` — signal registry, collectors, packet format, cache, mail/calendar detectors.
- `references/focus-scoring.md` — ranking, journal dedup, honesty rules.
- `references/jira-data-protocol.md` — Jira plumbing (per-key, no bulk JQL).
- `references/integration-strategy.md`, `references/data-policy.md`, `references/persistent-storage.md`, `references/vault-protocol.md`.

## Step T — Template Resolution
`artifact_type: focus`, `subtype: daily-brief` (tactical-brief / strategy-memo arrive with their modes), `product_id`, `language`.

## Modes

| Mode | Horizon | Status |
|------|---------|--------|
| `now` | today – this sprint | **v0.1** |
| `journal` | — | **v0.1** — review/close/snooze focuses, streaks |
| `auto` | — | **v0.1** — detects horizon from phrasing/cycle |
| `tactics` | sprint – quarter | **v0.2 (this release)** — 3–5 tactical candidates: roadmap drift, stale backlog, A/B decisions, capacity, team events |
| `strategy` | quarter – year | planned v1.33 — until then: acknowledge + offer product-research / cjm-research / quarterly-planning |

## Headless contract (scheduled runs)

Invocation from a scheduled task prompt: `focus-advisor mode={now|tactics} headless=true` (e.g. daily morning `now`, Monday `tactics`). Rules: (1) skip all gates — **no side-effect actions at all** (no Jira/Gmail/Confluence writes, no auto-launching chained skills); (2) metrics health-check chain only if `Focus → Scheduled → healthcheck: on`; (3) output = brief in chat **and always as a file** (Step 7) with journal status `proposed`; chains render as "next steps" with ready-to-paste phrases; (4) collector cache is kept warm for the follow-up interactive session.

## Pipeline

### Step 0 — Local context
Per `local-context-protocol.md`: product, Planning (anchor/cadence), Focus section. Focus section missing → run once with safe defaults (mail/calendar on, 7-day window, default thresholds) and offer Focus setup via `plugin-configurator` at the end.

### Step 1 — Horizon + scope. Gate (skipped in headless)
Confirm horizon (auto-detect from phrasing/cycle position) and period. Non-now horizons in v0.1 → route per Modes table.

### Step 2 — Collect signals
Per `focus-signals.md`, only the sources of the confirmed horizon. **now** (§3–4): cycle position, calendar (meetings needing prep), mail (live unanswered letters — two-stage filter), recent meetings' open action items, Jira tails. **tactics** (§6): quarterly roadmap plan-vs-actual and drift, backlog staleness (ICE age), features missing prerequisites ahead of next sprints, A/B tests awaiting decision, capacity and team-event signals. Honor cache TTL. Fan out collectors via `subagent-delegation.md` when available; inline otherwise. Each collector returns signal packets only.

### Step 3 — Cadence check
Per `focus-cadence.md`: due rituals (including recently missed ones) become high-priority candidates.

### Step 4 — Score and rank
Per `focus-scoring.md`: journal dedup → **now**: urgency+impact+unblock → 1–3 focuses; **tactics**: ICE + capacity realism + goal alignment (§4) → 3–5 candidates. The rest goes to "також на радарі". Insufficient signals → say so honestly.

### Step 5 — Focus brief
For each focus: what, why now (signals with links), cost of delay (one sentence), suggested next step. Subtype by mode: `daily-brief` / `tactical-brief`. Tactical brief adds: quarter position (sprints left, capacity used vs plan) and a "decisions waiting on you" section (A/B tests, approvals). Footer: degraded collectors, cache ages. Language — `user.language`.

### Step 6 — PM chooses. Gate (skipped in headless)
Per focus: **(a) chain** to the executing skill with prepared arguments; (b) create a task/reminder; (c) snooze with a date. Chain map:

| Recommendation | Chain |
|---|---|
| Sprint-boundary ritual due | sprint-planning `groom`/`plan`, team-ops-reporter `sprint-review` |
| Important letter unanswered | reply draft (Gmail `create_draft` — gate) / task |
| Meeting tomorrow needs prep | product-analysis (slice) / design-bridge (deck) / talking points from transcripts |
| Metrics day / "чи все ок з метриками" | product-analysis + cjm-research health-check (verify source freshness first — `focus-signals.md` §5) |
| Open action items from meetings | meeting-processor |
| Feature blocking next sprint lacks requirements | requirements-creator |
| Stale backlog / blurred focuses | brainstorm-features / quarterly-planning `refresh` |
| Roadmap drift beyond threshold | project-planning `replan` |
| A/B test waiting for a decision | product-analysis (test readout) |
| Team event ahead (perf review, onboarding, booking deadline) | task/reminder + team-ops-reporter `member-review` where relevant |

### Step 7 — Save artifacts (mandatory, NOT optional)
Every artifact this skill produces is persisted to the user's local repository:
- brief → `~/.grow-pm/focus/briefs/YYYY-MM-DD-{mode}.md`;
- journal update → `~/.grow-pm/focus/focus-log.md` (proposed → chosen → done/snoozed);
- cache → `~/.grow-pm/focus/cache/` (packets only, no message bodies);
- Vault mirror after every write per `vault-protocol.md` (`type: focus-brief`), recovery pattern as in knowledge-library (if `~/.grow-pm/focus/` is empty — restore from Vault);
- artifacts produced by chained skills (slices, decks, plans) are saved by those skills' own Step V — focus-advisor links them in the brief and journal.

## Quality Standards
- Recommend and chain — never execute another skill's work inline; never launch chained skills without an explicit PM "go" (and never in headless).
- Every focus is verifiable: signal links always present; no invented urgency; "insufficient signals" is a legitimate brief.
- Mail: read-only screening; only live letters from humans become signals; bodies never leave the mailbox or enter the cache (`data-policy.md`); any write (reply draft) — gate.
- Jira: per-key reads only (`jira-data-protocol.md`).
- Step 7 persistence is mandatory in every mode, including headless.
- Demarcation: team's sprint focuses belong to sprint-planning; this skill owns the PM's personal attention.

## Additional Resources
`references/focus-cadence.md`, `references/focus-signals.md`, `references/focus-scoring.md`, `references/jira-data-protocol.md`, `references/integration-strategy.md`, `references/data-policy.md`, `references/persistent-storage.md`, `references/vault-protocol.md`, `references/subagent-delegation.md`, `references/self-improvement.md`.
