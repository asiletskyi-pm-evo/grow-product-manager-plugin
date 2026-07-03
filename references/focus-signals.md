# Focus Signals — signal registry and collectors

**Overview:** Catalog of context sources `focus-advisor` scans per horizon, how each collector works, and the common signal-packet format. Collectors follow the MCP → registry → browser chain from `integration-strategy.md` and the confidentiality rules from `data-policy.md`. Consumed by `focus-advisor` (Step 2).

---

## 1. Signal packet (common format)

Every collector returns compact packets, never raw data — this keeps token cost flat regardless of how noisy the underlying source is:

```yaml
- signal: "Лист від VIP stakeholder висить без відповіді 2 дні"   # one line, human-readable
  source: mail | calendar | meetings | jira | cadence | metrics | roadmap | goals
  severity: high | normal | low
  freshness: 2026-07-03T09:00                                   # when observed
  link: <URL or file path>                                      # always present — the PM must be able to verify
  suggested_chain: <skill + mode, or "reply-draft" / "task" / "snooze">
```

## 2. Cache

`~/.grow-pm/focus/cache/{source}.yaml` — packets only (never message bodies), with `collected_at`. TTL: mail/calendar/jira — 4h; meetings — 24h; roadmap/goals — 7 days. Within TTL, reuse instead of re-collecting; `refresh` argument forces re-collection. A headless run warms the cache for the next interactive session.

## 3. Operational collectors (mode: now)

| Source | Collector | Notes |
|---|---|---|
| Cycle position | computed locally | see `focus-cadence.md` §1 |
| Calendar | Google Calendar MCP: today/tomorrow/this week | meeting-prep detector — §4 |
| | fallback: browser calendar.google.com | per `integration-strategy.md` |
| Meetings | Fireflies MCP (or vault Meetings/ if daily-import runs): last 3–7 days | extract PM's open action items |
| Jira usual suspects | per-key `getJiraIssue` + board scrape — **never bulk JQL search** (`jira-data-protocol.md`) | in-sprint: stuck In review >2 days, unassigned, blocked chains; mentions/comments addressed to the PM |
| | scope: current sprint + PM's epics from local-context | |
| Mail | Gmail MCP `search_threads`, read-only, window: **last 7 days** (default) | two-stage filter — §4 |
| Release flags | only if configured in Focus config | flags awaiting rollout decision |

### 4. Mail and calendar detectors

**Mail — "live letters" two-stage filter.** Stage 1 discards automation: `List-Unsubscribe` header, sender patterns (`noreply`, `no-reply`, `notifications@`, `newsletter`, `jira@`, `confluence@`, `calendar-notification@`), bulk-mail template subjects. These never become signals — the skill exists to surface humans waiting on the PM, not to re-render the inbox. Stage 2 ranks live letters: a real question/problem/approval addressed to the PM; sender in VIP list (`Focus → VIP senders`; if missing — collect from stakeholders on Focus setup); thread where the last message is not the PM's and has been waiting beyond the threshold (default: 24h VIP / 48h others); keywords (approve, дедлайн, блокер, погодження). Signal carries thread metadata + link only — body content stays in the mailbox (`data-policy.md`).

**Calendar — meetings needing preparation.** A meeting is prep-worthy when: participants include leadership/externals; title/type matches demo, review, planning, взаимодействие з keywords from Focus config; the PM is organizer or presenter; or the previous occurrence (Fireflies lookup by title) produced action items still open. Suggested chains: analytical slice (product-analysis on the meeting's topic), presentation (design-bridge), talking points from past transcripts, status pack (team-ops-reporter).

## 5. Metrics health-check (optional, chained — not performed inline)

When cadence says "metrics day" or the PM asks, focus-advisor **proposes** (gate) delegating to: `product-analysis` (quick pass over dashboards from `local-context → Metrics`) and/or `cjm-research` health-check (funnel vs baseline, configured thresholds). Before chaining, verify source freshness (`data-integrity-protocol.md`) — a frozen extract must be reported, not silently analyzed. Results come back as signal packets ("all green" or "stage X deviates → separate focus"). focus-advisor never interprets metrics itself — that's the analysts' height.

## 6. Tactical collectors (mode: tactics)

| Source | Collector | Signal examples |
|---|---|---|
| Roadmap plan-vs-actual | features by CQL `space=X AND label=qN-YYYY` + epic statuses per-key (`jira-data-protocol.md`); compare feature statuses vs quarter position (sprints elapsed / remaining) | "5 of 27 features done, 3 of 7 sprints gone — behind pace"; "epic X has no movement for 2 sprints" |
| Roadmap drift | committed scope vs current forecast (reuse `capacity-model.md` math where available) | "FE demand grew past ceiling after scope add → replan candidate" |
| Backlog staleness | vault `Hypotheses/` + backlog pages: age since last ICE review | "ICE backlog untouched for 6 weeks — re-score before next quarter draft" |
| Missing prerequisites | features planned for next 1–2 sprints lacking upstream work-types (work-type DAG, `dependency-model.md`) | "feature Y in SEX N+1 has no requirements page" |
| A/B decisions | A/B tracker page (from `local-context → Product → ab_test_dashboards` / tracker URL): tests past their end date without a decision recorded | "test Z ended 12 days ago — decision pending" |
| Capacity & availability | Planning config team + calendar vacations + booking/HR deadlines from Focus config | "2 of 3 Android devs on vacation in SEX N+1"; "bookings review due Sep 1" |
| Team events | calendar + Focus config: perf reviews, onboarding milestones, vacancies | "perf review cycle opens next week — drafts needed" |

Tactical signals feed `focus-scoring.md` §4 (ICE + capacity realism + goal alignment). Heavy analysis stays chained: drift → `project-planning replan`, test readout → `product-analysis`, re-scoring → `brainstorm-features`.

## 7. Strategic collectors (mode: strategy — v1.33+)

Product goals & missions (pinned source from Focus config); NPS waves and love/hate themes; CJM/funnel trends; internal research signals (knowledge-library); competitive moves (product-research); leadership-meeting mandates (Fireflies keyword scan); white spaces in the PM's zones.

## 8. Config (local-context → Focus)

```markdown
### Focus (focus-advisor)

#### Sources
- Mail: [on/off], window: [7] days, thresholds: [24]h VIP / [48]h others
- Calendar: [on/off]; prep keywords: [demo, review, планування, ...]
- Jira: [on/off]; Release flags: [off]
- Metrics health-check in scheduled runs: [off]

#### VIP senders
- [name <email>] — [role]

#### PM goals (scoring weights)
- [e.g. mission "+15% CR лістингів та КТ" — permanent high weight]

#### Cadence Overrides
(see focus-cadence.md §3)

#### Scheduled
- Daily brief: [cron + on/off], mode now, headless
- Tactical brief: [cron + on/off], mode tactics, headless
```
