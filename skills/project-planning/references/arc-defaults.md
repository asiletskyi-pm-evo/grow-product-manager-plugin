# Arc defaults — window and altitude view (since v3.6.0)

> Part of `project-planning`. Read at Step 4 and Step 6 (and when `whatif` or `replan` redraws the arc) in an interactive run. Source fields: `role_defaults.horizon` and `role_defaults.planning_view` (`references/role-profiles.md` §2, §2b, §5 step 2; `references/planning-core.md` §7). A hat never changes either field — both stay the profile's.

## 1. Default arc window (`horizon`)

The arc window is the span the project roadmap (Gantt, `references/roadmap-artifacts.md` sec. 3) is drawn over. The forecast itself — volume, dependencies, critical path, allocation %, completion date — is computed the same way for every profile; the window only decides how far the drawing reaches.

| `role_defaults.horizon` reaches | Default arc window |
|---|---|
| a quarter or less (`quarter`, `sprint–quarter`, `1–2 sprints + discovery loop`, `days–experiment cycle`, `study = 1–4 weeks`) | the current quarter through the forecast completion quarter — the pre-v3.6.0 arc |
| a year or more (`quarter–year`, `month–quarter–year`, `year–3 y`) | the same arc, drawn over at least four quarters from the current one; quarters after the completion quarter are drawn as empty columns |

- A window named in the request ("roadmap for 3 quarters", "to the end of the year") wins over the default.
- A default window never cuts the arc short: it always reaches the forecast completion quarter, so no work, critical-path item or drift is ever outside it.
- Horizons longer than a year still draw four quarters minimum — an arc of empty years says nothing a completion date does not.

## 2. Altitude view (`planning_view`)

| `role_defaults.planning_view` | Arc presentation | Capacity table (Step 4) |
|---|---|---|
| `slice` | epics and features as bars, as before | the tech-debt reserve as its own row (`references/capacity-model.md` §7) — the numbers do not change |
| `rollup` | initiatives → epics first (one bar per epic, grouped by initiative); feature bars on request | as before |

- The critical path stays highlighted in both views: in `rollup`, an epic that holds a critical-path feature is highlighted as a whole.
- Drift vs baseline (`replan`) is shown in both views, at the depth of the view.

## 3. What never changes

- Steps 1–5 and Replan R1–R6, their gates (manual dependencies, allocation %), the numbers and the "pending TL/PM confirmation" markers.
- No question is added: the window and the view are defaults, and the user can ask for any window or depth at any point.
- The saved baseline, the vault artifact and a published page carry the full arc — every epic and feature — whatever the view.
- An automated run (a scheduled `replan`, or a return payload to `quarterly-planning`) keeps the pre-v3.6.0 window, view and capacity table.
