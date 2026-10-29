# Focus role defaults — horizon proposal and source priority (since v3.6.0)

> Part of `focus-advisor`. Read at Step 1 (the horizon proposed for confirmation) and at Steps 2 and 4 (collector order, residual tie-break) in an interactive run. Source fields: `role_defaults.planning_view` and `role_defaults.sources_priority` (`references/role-profiles.md` §2, §2b, §5 step 2). A hat does not change `planning_view` (`references/role-profiles.md` §4).

## 1. Horizon proposal (Step 1)

Precedence, top to bottom — the first two are the pre-v3.6.0 rules and still win:

1. The horizon the phrasing names (the Step 1 cues: today / now → `now`; quarter, team, backlog → `tactics`; year, opportunities, directions → `strategy`).
2. The quarter-boundary nudge toward `strategy`.
3. When neither decides, `role_defaults.planning_view`: `rollup` proposes `strategy` (then `tactics`, then `now`); no `planning_view` (pm, no or unconfirmed role, automated) keeps the pre-v3.6.0 proposal exactly; `slice` keeps the pre-v3.6.0 proposal (`now`, then `tactics`).

The user confirms or changes the proposal in the same Step 1 gate — no question is added. `role_defaults.level_home` is not consulted on its own: every `rollup` profile has an L3–L4 home and every `slice` profile an L1–L2 home (`references/role-profiles.md` §2b), so it would add nothing to `planning_view`.

## 2. Source priority (Steps 2 and 4)

`sources_priority` is the ordered source list of the profile (`references/role-profiles.md` §2, "Vocabulary & sources"). It is empty for `pm` and for a user without a confirmed role — then collectors keep the `references/focus-signals.md` order and no source tie-break applies, exactly as before v3.6.0. Each entry maps to the packet `source` values of `references/focus-signals.md` §1; an entry that no focus collector reads is skipped — no collector is added for it.

| `sources_priority` entry | Packet `source` |
|---|---|
| Jira | `jira` |
| Jira plans | `roadmap` |
| analytics dashboards, dashboards, warehouse / semantic layer, experiment platform, NPS / analytics, feedback | `metrics` |
| OKR store | `goals` |
| board context | `goals`, `meetings` (the product-goals and leadership-mandate collectors) |
| transcripts | `meetings` |
| people profiles | `cadence` (the manager-rhythms signal) |
| Confluence, finance, market, pipeline, Figma, DS, session replays, usability tests, repository, CI, incidents | none — no focus collector reads them |

Rules:

1. **Collector order.** Within the confirmed horizon, collectors whose packet source is mapped run first, in `sources_priority` order; the rest follow in the `references/focus-signals.md` order. With a fan-out (`references/subagent-delegation.md`) this is the dispatch order. The set of collectors, the cache and the TTLs are the same.
2. **Residual tie-break.** After the mode's own ordering rules (`references/focus-scoring.md` §1 rule 2 for `now`; §4 and §5 for `tactics` and `strategy`), a tie that remains goes to the candidate whose packet source maps to the earlier `sources_priority` entry. Before v3.6.0 such ties were unordered, so no ranking that v3.5.0 decided changes.
3. **Ordinal only.** No points are added to urgency, impact, unblock, ICE, goal alignment, lever size or evidence strength; the caps (1–3 / 3–5 / 2–4) and the radar list are unchanged, and no signal is dropped for its source. Focuses the PM already chose stay pinned to the top (`references/focus-scoring.md` §2).

## 3. What never changes

- No question is added; the Step 1 and Step 6 gates ask what they asked before.
- A headless run (`headless=true`) and a run invoked for a return payload take the horizon from `mode=`, run collectors in the `references/focus-signals.md` order and apply no role tie-break — the v3.5.0 behaviour.
- The Focus config is applied exactly as before: the `PM goals` scoring weights, VIP senders, and every source switched off in `Sources` stays off whatever its priority.
