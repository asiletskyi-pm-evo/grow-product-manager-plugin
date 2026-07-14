# Reporting — 3T5F

Methodology reference for goal-linked personal / direction reports. Consumed by `product-reporter` (goal-report mode) and read by `performance-review` (achievement evidence) and `goal-setter` (Comparable baseline). 3T5F is the plugin's working term.

> A report **without a goal is harmful** — it trains people that "process = work". Reports exist to keep focus on the **goal**, surface problems early, and let the manager react. Every report element ties back to a goal set per `references/goal-frameworks.md`.

---

## The eight elements of a 3T5F report

| # | Element | What it is |
|---|---------|-----------|
| 1 | **Target** | The goal, phrased in SMARTCBP. |
| 2 | **Top Record** | The best (record) result in the period, with the time-slice when it was hit. |
| 3 | **Top-3 Highlights** | The three things the person themself considers most important this period and that moved the goal. |
| 4 | **Fact** | Actual figures for the reporting period. |
| 5 | **Fact Quota Attainment** | % of the overall goal achieved — **separately** for the reporting period and **cumulatively** since the goal was set. |
| 6 | **Forecast** | Projection of goal achievement. Minimum model: prior-period fact + (last month × months remaining). E.g. $500k over 7 mo + $100k Aug + $100k × 4 = $1.0M/yr. |
| 7 | **Forecast Quota Attainment** | Projected % attainment at period end (forecast $1.0M vs plan $1.2M → 83%). |
| 8 | **Funnel** | The funnel leading to the goal (for sales — leads & conversions). Mandatory in some reports, optional in others. |

**Essence:** focus on the goal, light to produce, easy to spot a problem or a win, few numbers about current results.

---

## Formatting rules

1. **Clarity** — simple sentences; status emoji (✅ met / on-track, ❌ not); no ambiguity (never "currently 47%" — give the concrete date/number).
2. **Brevity** — compress every word; round to whole numbers (55%, not 54.535% — unless the goal's precision is in that digit).
3. **Structure** — numbering; bold for key words and figures.
4. **Deviation emoji convention:** −1…−5% from plan → ⚠️; worse than −5% → ❌; on/above plan → ✅.

---

## Principles (enforced in goal-report mode)

- **Cadence:** weekly for ~80% of cases; monthly for global goals. Frequency depends on the cost of collecting the data (automatic → as often as daily; manual CRM export → monthly) and on how new the work is (new work → report more often; frequency drops as professional trust grows). Seniority does not set the frequency — proximity to the goal does.
- **Manual send, even when automatable** — the person must personally notice the numbers. Compromise: manual at least once a month.
- **Text over voice** — text gives autonomy, discipline, and quiet time alone with the data; meetings only supplement (a one-minute 3T5F read replaces a long status call).
- **The manager must actually read and react** — a reporting ritual that leads to nothing is worthless. Half the job is setting reports up; the other half is engaging with them.
- **Reporting audit every 6–12 months** — cut duplicate and goal-less reports (measurable time savings).
- **Whose fault is a bad report:** if a D4 reports badly — their error; if a D1 — the manager's.

---

## Manager audit of a report (the `product-reporter` goal-report audit path)

Given a person's report + their goal:

1. **Presence check** — all 8 elements present? Flag missing ones (most commonly missing: Target, Top Record, Top-3, Forecast QA).
2. **Goal linkage** — is there a Target at all, and is each figure tied to it? A report that is a "transcript of the workday" (processes, no goal) is rejected with a rewrite.
3. **Forecast QA gate** — if **Forecast Quota Attainment < 100%**, generate corrective suggestions: what would close the gap, which funnel stage to move, whether the goal needs re-scoping.
4. **Ambiguity/brevity** — flag vague phrasings and over-detailed task dumps (collapse to Top-3 Highlights).
5. Output a **reformatted model report** as the "after".

**AI progress check:** each period, per goal, ask *"Can progress toward this goal be judged unambiguously from this report?"* and compute % attainment against the Comparable baseline.

### If the goal is falling short (manager's three questions)
1. "Why didn't we reach it?" 2. "What will you do to reach it?" 3. "What will you do / risk if you don't?" Then: temporary passenger → part ways; did everything possible → step in and help; won't learn from mistakes → part ways.

---

## Boundary vs operational Jira reports

`product-reporter` owns **both**:
- **Operational Jira reports** (sprint plan/review, quarter review, initiative status, member review) — team throughput, story points, releases.
- **Goal reports (3T5F)** — a person's or a direction's progress against a *goal*.

The line: operational reports answer "what did the team ship?"; 3T5F answers "how is this goal progressing?". **Setting** a person's goal is `goal-setter`'s job, not the reporter's.

---

## References
- `references/goal-frameworks.md` — SMARTCBP Target, Comparable baseline
- `references/people-context-protocol.md` — reporting cadence + last-report fields
- `references/people-frameworks.md` — GTD-index (delivery data feeds Fact)
- `skills/product-reporter/SKILL.md` — the reporter that renders/audits these
