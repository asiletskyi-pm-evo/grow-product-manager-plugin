# Goal Frameworks

Methodology reference for setting and auditing goals in the People-contour. Consumed primarily by `goal-setter`, and read by `performance-review`, `hiring-designer`, and `product-reporter` (goal-report mode). Framework terms (SMARTCBP, MBO, OKR, Tell and Sell) are the plugin's working vocabulary.

---

## SMARTCBP — eight requirements for a personal goal

SMARTCBP extends the classic SMART with three extra letters. It is the **default methodology for personal goals** (a person, a role, an offer). Each letter carries an audit question.

| # | Letter | Requirement | Audit question | Fix if it fails |
|---|--------|-------------|----------------|-----------------|
| 1 | **S** — Specific | Precise, no vagueness. Perfective verbs (attract, build, reach) + qualifiers (what exactly, which segment, from where). | "What concretely do we get?" | Replace "more clients" → "attract new HoReCa clients in Ukraine". |
| 2 | **M** — Measurable | Concrete numbers and dates, absolute or relative (%). | "How do we know the goal is met?" | Add the number + the metric + the date. |
| 3 | **A** — Achievable | Hard but real ("smart-challenge effect"). | "Realistic in this timeframe? Enough experience?" | Right-size against capacity; avoid fantasy (70% market share from 5%). |
| 4 | **R** — Relevant | Serves the wider org/strategy. | "What does the business gain? Aligned to strategy?" | Re-anchor to a business outcome, not a process. |
| 5 | **T** — Time-bound | A deadline or timeframe. | "By what date?" | Add the date. |
| 6 | **C** — Comparable | Compared to a prior-period fact, e.g. "(+20% YoY)". | "What was the result before? By how much do we improve?" | Pull the baseline from reports/analytics; if no history — benchmark the market or "+N p.p. on the measured KPI". |
| 7 | **B** — Brief | No word removable without losing meaning. | "Which words can I cut?" | Compress; one sentence. |
| 8 | **P** — Public | Open to the team/company (no sensitive figures). Anyone can trace their goal up to the company goal. | "Ready to show this to everyone?" | Remove sensitive data, then publish. |

Additional **common-sense filter**: does the goal make sense *for this specific role right now* (don't hand a brand-new hire a flagship deliverable on day one).

**A goal is one sentence. Ideally 3 goals per person, maximum 5.**

### Goals vs tasks vs KPI
- **Goal** — the end result ("where are we going?"). Must sit **outside** the performer's own process (a business outcome, not "process for the sake of process"). "Write 5 texts" is a task; "write 5 texts that yield 10 MQL" is a goal.
- **Task** — a concrete step toward the goal (also worth phrasing goal-like, just more grounded — see `communication-frameworks.md` → task formulation).
- **KPI** — an instrument panel ("what is happening?"). A KPI is not a goal, but one KPI can be chosen to build a goal on.

> Red flag: a "goal" that lives entirely within the performer's process (production counts, activity counts) is a pseudo-metric. Push it out to a business result (conversion, MQL, MRR).

---

## SMARTCBP audit output (the `goal-setter` audit mode)

Render a **before → after** table, one row per letter:

| Requirement | Status | Issue | Rewrite |
|-------------|--------|-------|---------|
| S | ❌ | "more clients" is vague | "attract 200 new HoReCa clients…" |
| … | … | … | … |

End with the single-sentence corrected goal and a note whether it now sits outside the performer's process.

**AI self-check:** feed the goal + a sample report to the model and ask *"Is this goal phrased unambiguously enough to judge progress toward it from this report?"* If not — tighten M/C.

---

## MBO vs OKR — choosing the methodology

| Dimension | MBO (→ personal goals) | OKR (→ product / direction) |
|-----------|------------------------|------------------------------|
| Ambition | Realistic; **<100% = miss** | Ambitious/"stretch"; **70–80% = success** |
| Unit | A specific **person** (personal accountability) | A **team / direction** |
| Bonuses | Compatible — bonus can attach to the goal (goal set for half-year/year) | Decoupled from bonuses |
| Cycle | Reviewed often (monthly review, weekly/biweekly reporting) | Quarterly |
| Visibility | Classically private → plugin adds **P** (public) from OKR | Public by default, vertical tree company→person |
| Structure | One-sentence goals | 1–3 Objectives × 2–5 Key Results |

**Selection rule used by `goal-setter`:**
- Goal for a **person / offer / individual accountability** → **SMARTCBP** (default).
- Goal for a **product / direction / quarter, ambitious & public** → **OKR** (Objective + 2–5 Key Results), aligned to the Mission/Goal Atlas top of `references/planning-core.md`.
- When both could apply, prefer SMARTCBP for the individual and cascade it *under* an OKR/Mission (see cascade below).

---

## Commitment — Tell and Sell vs Just Tell

- **Just Tell** — the goal is announced without the person's involvement. Read as a directive, lowers motivation.
- **Tell and Sell** — the person is involved in shaping/discussing the goal; the manager "sells" the idea; involvement → personal ownership → **commitment** ("I agree with these goals and want to achieve them").

`goal-setter` runs a **Tell-and-Sell checklist** before marking a goal committed:
1. Did the person participate in shaping (or at least argue with) the goal?
2. Can they restate the goal in their own words?
3. Do they accept the Comparable baseline as fair?
4. Have they named what they'll risk / do if it slips?
5. Explicit "yes, I commit"?

Record the commitment status (`committed: yes/no`, who committed) in the person's profile and, where relevant, in `decision-log`.

---

## Goal letter (for offers and periodic reviews)

Structure of a **goal letter** (used by `hiring-designer` for offers, by `goal-setter` mode (d), and as the `goal-letter` built-in template):

1. **Core purpose** — 5–6 sentences: why this role exists / this period matters.
2. **Expected results** — 3–5 specific outcomes, each phrased as a SMARTCBP goal (for offers: on a 3 / 6 / 12-month horizon).
3. **Professional traits** + 5–8 culture points.
4. **Collaboration/communication** + cross-check against the business plan and the goal letters of peers, reports, and managers.

---

## Cascade (goal-setter mode (c))

```
Mission / Goal (Atlas, planning-core.md)
  └── Direction goal (OKR)
        └── Team goal
              └── Person goal (SMARTCBP)  ← committed via Tell and Sell
```

Each level's goal must ladder up to its parent (SMARTCBP-P: anyone can trace the path). A missing link is a **marking gap** — surface it, do not invent the link (same rule as `planning-core.md`).

---

## First-principles goal awareness

When a goal feels inherited or unclear, decompose it: (1) break the problem into fundamental parts; (2) drop assumptions ("is that actually true?"); (3) rebuild the goal from facts, not habit. Used to escape "hire more couriers" thinking toward the real objective.

---

## Typical errors (flag these in audit)
- One goal for a whole department instead of personal goals → "collective irresponsibility".
- "This role can't be goaled" — a SMARTCBP goal can always be set (measure a KPI and improve it; for support roles, value time saved in money, or a satisfaction score).
- Setting goals and never tracking them (remembered only at the next session) — reporting + reaction are half the job.
- A goal inside the performer's process (see red flag above).
- Confusing percent with percentage points (60% + 20% = 72%; 60% + 20 p.p. = 80%).
- Nouns instead of perfective verbs ("execution" instead of "execute").
- "Conversion" without specifying from-what to-what.

---

## References
- `references/people-context-protocol.md` — where goals attach (`active_goal_letter`, commitment)
- `references/reporting-3t5f.md` — the report that tracks a goal (Comparable baseline source)
- `references/planning-core.md` — Mission/Goal Atlas at the top of the cascade
- `references/communication-frameworks.md` — task formulation for goal→task breakdown
