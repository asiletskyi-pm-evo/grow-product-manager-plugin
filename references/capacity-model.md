# capacity-model.md

> Shared planning-suite reference. Single source of truth for capacity calculation, feature estimation, and realism checks. Consumers: `project-planning` (initiative ceiling + duration forecast), `quarterly-planning` (quarter ceiling), `sprint-planning` (sprint ceiling + per-member). `roadmap-architect` does not use capacity.

This module describes **one engine** with three multipliers (quarter / sprint / initiative). All skills take the formula from here — they do not duplicate it.

---

## 1. Concepts

| Term | What it is |
| --- | --- |
| **baseline_SP** | rough productivity of one engineer per sprint (default 10 SP; calibrated against actuals) |
| **availability** | share of sprint work time available for team tasks (1 − vacations/sick leave) |
| **involvement** | share of a person's time on this initiative's team tasks (the rest — other initiatives, mentoring, hiring) |
| **tech-debt reserve** | fixed % of capacity for TechDep/support (does not go into new features) |
| **risk buffer** | reserve for the unexpected; implemented as a load target ≤ 85% of the ceiling (not a multiplier) |
| **allocation %** | maximum share of the team's ceiling given to one initiative (for project/quarterly) |
| **ceiling** | how much the team realistically handles per period (SP), after all deductions |

---

## 2. Base formula (period ceiling by platform/role)

```
raw(platform)     = Σ_people[platform]  baseline_SP(person) × N_sprints × availability(person) × involvement(person)
ceiling(platform) = raw(platform) × (1 − tech_debt_reserve)
target(platform)  = ceiling(platform) × 0.85          # risk buffer (capacity-gate target)
```

- `N_sprints` = number of sprints in the period (quarter ≈ 6–7; sprint = 1).
- Compute **per platform separately** (BE / FE / iOS / Android) and per support role (Design / Analytics / QA) — because the bottleneck is always on a specific platform, not "on average".
- A TL counts as an engineer only if confirmed in the team composition (see Development Team in local-context).

**Defaults** (override in local-context): `baseline_SP = 10`, `availability = 0.9` (10% reserve), `tech_debt_reserve = 0.15`, `gate target = 0.85`.

---

## 3. Per-member capacity (for sprint-planning)

For a sprint the ceiling is broken down **to the person** — because the plan is executed by specific people, not by "a platform".

```
capacity(person, sprint) = work_days(person, sprint) / days_in_sprint × baseline_SP(person) × involvement(person)
```

- `work_days` are collected by a PM survey for each sprint (vacations, sick leave, partial days, parallel initiatives) — this is a **gate**, not auto.
- **Carryover-risk:** if in the previous sprint `done / committed < threshold` OR remaining_work / daily_throughput > days_left → the person is in the risk zone; lower their proposed load in the next sprint and surface chronic overloads to the PM.

---

## 4. Baseline velocity and calibration

1. Start — default 10 SP/sprint/engineer.
2. **Calibrate against actuals** of the previous period: real closed SP / (engineers × sprints) → actual velocity per person/role.
3. Source of actuals — the Jira board velocity report (via browser, because MCP-search fails; see `jira-data-protocol.md`).
4. **The PM confirms the final number** (they know the context: onboarding, anomalies, substitutions).

---

## 5. Allocation — the initiative dimension (for project / quarterly)

One initiative does not take the whole team. Each initiative is assigned a **maximum % of involvement**:

```
effective_initiative_capacity(platform) = ceiling(platform) × allocation%(initiative)
Σ allocation%(all active initiatives) ≤ 100%        # horizontal team budget
```

- For `project-planning`: allocation% sets the **arc speed** of the initiative → affects duration.
- For `quarterly-planning`: allocation% = share of the quarter ceiling that goes to the initiative → how much of its scope fits.
- This is a **shared concept** linking the two axes (see the two-axis design). If the sum > 100% — surface the allocation conflict to the PM.

---

## 6. Platform granularity (capacity-gate at the slice level)

Most features roll out by platform readiness and **need not ship on all platforms in one period**. So the gate works on **platform slices**, not whole features:

- demand and ceiling are computed **per platform separately**.
- An overloaded platform can be relieved by **carrying over the slice of exactly that platform** to the next period, leaving the feature alive on the platforms with slack.
- Exception — features with a critical cross-platform launch (synchronous A/B web+mobile): cannot be sliced, mark separately.

---

## 7. Capacity-gate (thresholds and presentation)

```
load(platform) = demand(platform) / ceiling(platform)
```

| Zone | Load vs target(85%) / ceiling(100%) | Signal |
| --- | --- | --- |
| 🟢 OK | ≤ 85% of ceiling | realistic, has buffer |
| 🟡 Warning | 85–100% | tight; at risk on any disruption |
| 🔴 Critical | > 100% | overloaded — cut / carry over / slice |

**Presentation rule (mandatory):** when a platform is over the ceiling — do NOT operate with abstract SP. Show the **concrete list of initiatives → epics → features (with estimates) that do not fit**, and give the PM a choice (preferably interactively: load bars + feature/slice toggles). The decision is the PM's.

Additional checks: concentration on one platform (bottleneck), share of unfinished work from the previous period, count of "waiting for details".

---

## 8. Auto-estimating features by analogy (demand-side)

When a feature has no estimate — do not leave a gap, estimate by analogy:

1. Find similar **closed** features (same type: A/B on the product card / Q&A feature / catalog landing / admin tool; similar requirements; same platforms).
2. Take their actual volume/touched platforms → produce a **range** (t-shirt or SP spread), not pseudo-precision.
3. T-shirt → SP rubric (per platform, default; calibrated): `S=3 · M=5 · L=8 · XL=13`.
4. Mark `AI-estimate (analogy to {keys}), pending TL confirmation` — final by TL/analyst (competence boundary).
5. Collect all auto-estimates into a separate list for quick PM/TL review.

---

## 9. Scaling to the period

| Skill | N_sprints | Initiative multiplier | demand granularity |
| --- | --- | --- | --- |
| `project-planning` | all sprints of the arc | initiative allocation% | epic/feature by platform |
| `quarterly-planning` | sprints of the quarter (≈6–7) | allocation% across all initiatives | feature by platform (slices) |
| `sprint-planning` | 1 | — (whole sprint) | task by person, Ready-only |

Same engine (section 2), different `N_sprints` and multiplier.

---

## 10. Duration forecast (hook for project-planning)

Initiative duration is not simply `volume / capacity`, but a schedule that accounts for dependencies:

```
duration ≈ critical_path_schedule(volume_by_platform, dependencies, effective_initiative_capacity)
```

- `volume_by_platform` — sum of estimates (incl. auto-estimates).
- `dependencies` and the critical path — from `dependency-model.md`.
- `effective_initiative_capacity` — section 5.
- Output: completion date + distribution across quarters/sprints; for `replan` — delta vs baseline.

---

## 11. Reference example (FET Q3 2026, verified by a run)

Composition: BE 2 dev, FE 2 dev, iOS 3, Android 3. N_sprints = 7. baseline 10, availability 0.9, tech-debt 0.15.

```
raw(BE)   = 2 × 10 × 7 × 0.9 = 126 ;  ceiling = 126 × 0.85 ≈ 107
raw(iOS)  = 3 × 10 × 7 × 0.9 = 189 ;  ceiling = 189 × 0.85 ≈ 161
```

Ceiling: BE/FE ≈ 107, iOS/Android ≈ 161, total ≈ 536 SP. Target ≤85%: BE/FE ≈ 91. **Bottleneck: BE/FE at 2 dev each** — almost every initiative goes through them. The FE overload was cleared by carrying over the FE slices of some product-card A/B tests to the next quarter (platform granularity, section 6).

---

## 12. Quality / caveats

- Compute per platform separately — a "team average" hides the bottleneck.
- Every AI estimate/ceiling carries a "pending TL/PM confirmation" marker; the decision is the role's.
- Overload = show the entities + give a choice, never bare SP.
- Every number — with an inline period (which quarter/sprint, how many sprints, normalized or not).
- Defaults (baseline/availability/tech-debt/thresholds/rubric) are overridden in local-context → Planning; do not hardcode in skills.
