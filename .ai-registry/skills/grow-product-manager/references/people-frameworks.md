# People Frameworks

Methodology reference for diagnosing and developing people in the People-contour. Consumed by `performance-review`, `one-on-one`, `delegation-coach`, `offboarding-guide`, and read by `task-creator` / `sprint-planning` (for how-depth and assignee fit). Framework terms (Hersey-Blanchard, D1–D4/S1–S4, 7 levels of Appelo, GTD-index, NVC) are the plugin's working vocabulary.

---

## 1. Situational leadership (Hersey-Blanchard) — D-types and S-styles

Diagnose each person on two axes — **wants / doesn't want** and **can / can't** — then match the leadership style. D-type is judged **per kind of work**, not per person globally: someone can be D4 on familiar work and D1 on a new area.

| Type | "wants / can" | Meaning | Style |
|------|---------------|---------|-------|
| **D1** — Enthusiastic beginner | can't, but wants | Low skill, high motivation, inexperienced. | **S1 Directing** |
| **D2** — Disillusioned | can't and doesn't want | Some competence, faded enthusiasm (often a junior thrown in without onboarding). | **S2 Coaching** |
| **D2.1** — beginner who never wanted | can't, doesn't want *in principle* | A hiring miss; no motivation at all → don't engage, part ways. | — |
| **D3** — Capable but unsure | can, but doesn't want | High skill, variable motivation (confidence dip / life circumstances). Worth helping out of the dip. | **S3 Supporting** |
| **D3.1** — capable who never wanted | can, doesn't want *in principle* | No motivation at all — a hiring miss, part ways. If they *became* this (weren't always) → treat as D3 and help. | — |
| **D4** — Self-driven pro | wants and can | High skill + high motivation, owns responsibility. | **S4 Delegating** |

**The four styles:**
- **S1 Directing** — the leader decides everything (who/what/how/why) and informs.
- **S2 Coaching** — leader still sets tasks but is receptive and "sells" ideas; high task + high people focus.
- **S3 Supporting** — team makes most decisions; leader participates as a peer; high people, low task.
- **S4 Delegating** — hands off authority + responsibility; leader focuses on strategy, sets **goals** (SMARTCBP) and reads **reports** (3T5F), not tasks.

**Style-to-type mapping used by the plugin:** S1→D1 and S4→D4 directly. For D2/D3 — try to "cure" the *doesn't-want* with manager tools (1-1s, career ladder, knowledge maps, incentives); if it doesn't take → part ways. **D2.1 / D3.1 — part ways immediately.**

### The "doesn't want" rule
- **"Wants" matters more than "can"** when you see potential.
- **"Doesn't want" is very hard to cure** — treat it as a management/hiring error more often than a personality trait. Reanimation succeeds only a minority of the time (rule of thumb ≈ 1 in 4), and the average time spent on a *failed* reanimation is far longer than on a successful one — so **don't drag it out**.
- Fire not when someone "doesn't instantly do what's needed" but when they **stop developing** (development requires "wants").

### Reanimation protocols (fed into `one-on-one` / `offboarding-guide`)
- **New hire (<6 months) who "doesn't want" (D2.1/D3.1):** at most **one** motivational 1-1 (career/professional/material horizon, helicopter view, start from their stated goals). If it doesn't land — part ways and reopen the role.
- **Experienced person who faded (D4/D1 → D2/D3):** **three 1-1s over three months** — surface challenges, restate values, build a joint development plan. No stable progress in three sessions → decision to part ways.

Everyone on staff should be growing toward D4. If a role only ever needs simple, static work, use freelance/AI rather than keeping a permanent "eternal executor".

---

## 2. Delegation — 7 levels of Appelo

Gradual transfer of authority, balancing control and autonomy against team maturity.

| Level | Name | Meaning |
|-------|------|---------|
| 1 | **Tell** | Manager decides and informs. |
| 2 | **Sell** | Decides, but explains reasons/context to win support. |
| 3 | **Consult** | Gathers the team's input, then decides alone. |
| 4 | **Agree** | Manager and team discuss and reach agreement together. |
| 5 | **Advise** | Manager advises; the team decides. |
| 6 | **Inquire** | Team decides, then informs the manager. |
| 7 | **Delegate** | Full team autonomy, full trust. |

**Real delegation begins at level 5 (Advise).** Levels 1–4 on routine work are candidates to push down.

**Audit method (the `delegation-coach` core):** list every recurring operational activity (10–20 concrete items, no "I manage the team" abstractions) → mark current level per item, target level, who it could go to, and what blocks the transfer. The blocker reason is a controlled list: *"Impossible to transfer" / "Already training someone" / "Still looking for someone"*. A low average level = the delegation skill still has room to grow.

### S1→S4 transfer plan (how a zone is handed over)
- **S1 (start):** immerse the delegate — add to all channels/threads for the area, bring them to every meeting on the topic (with a date after which they attend alone), make them the meeting secretary (ARCV notes → tasks → control → reports).
- **S2 (~1–2 months, first results):** have them answer/lead in meetings and chats, set tasks, check execution; ask their opinion often.
- **S3 (~2–3 more months):** step out of operations — stop attending the meetings; control only results and key checkpoints.
- **S4 (results "good" or better):** stop setting tasks and checking execution; set SMARTCBP goals, read 3T5F reports, pay bonuses on goal achievement.

**Internal blocks on delegating** (and counters): missing professional trust (give a chance to earn it; if repeated critical errors — part ways); perfectionism (acknowledge and delegate anyway); unwillingness to invest teaching time ("cheaper to do it myself" — false long-term); inexperience (just start); fears of losing control / becoming redundant. Before concluding "no one to delegate to", compute hiring ROI via ROAIP (`references/roi-frameworks.md` if present, else the ROAIP note in `communication-frameworks.md`).

---

## 3. GTD-index (Getting-Things-Done conversion)

A person's **GTD-index** = the conversion between what they **took on** and what they **actually delivered**. It is the universal marker of "gets things done" — weighted above certificates and methodology knowledge.

- Computed per period from delivery data (e.g. Jira: planned-vs-done across a sprint — the carryover analysis in `sprint-planning` already produces the raw numbers).
- Stored as a trend in the person profile (`gtd_index: [{period, value}]`).
- Read by `performance-review` (a core input) and `delegation-coach` (levels 5–7 only for consistently high GTD).
- Rule: **explanations are not currency; results are.** "Bad management / no time" reasons don't change the index — but a *sustained low* index is a management signal (D1 → the manager owns the fix; D4 → the person owns it).

Verbs of a high-GTD culture (nudge roadmaps/tickets toward these, away from passive process nouns): execute, ship, close, finish, deliver, reach, implement, complete, finalize.

---

## 4. Feedback — Radical Candor + NVC (facts, not traits)

Feedback in every People-skill (1-1 prep, performance-review, offboarding scripts) follows **Nonviolent Communication (NVC)** — describe **actions, not the person**:

Template: **"When [observation — a fact, no judgment], I feel [feeling], because [need] matters to me. Could you please [concrete, doable request]?"**

Four components: **Observation** (fact, not "you always…"), **Feeling**, **Need**, **Request** (a request, not a demand — be ready for "no").

- ❌ "You're terribly careless, how could you make this mistake?" → ✅ "The numbers in the report differ from the source data here and here."
- Prefer **cognitive empathy** (understand what the person feels) over **emotional empathy** (feeling it as your own) in 1-1s — emotional empathy burns the manager out.
- Separate facts from assumptions: without a 1-1, a guess ("they went quiet, they must be quitting") hardens into a "fact".

---

## 5. "Did you tell them yourself?" principle

When someone complains about a colleague, the manager's first question is: **"Did you tell them this yourself?"** Route the person to a direct conversation rather than carrying the complaint. Prevents the manager becoming a message-relay and keeps issues where they can be resolved. Applied by `one-on-one` when a session surfaces inter-colleague friction.

---

## References
- `references/people-context-protocol.md` — where D-type, delegation, GTD-index live
- `references/goal-frameworks.md` — SMARTCBP goals set at S4
- `references/reporting-3t5f.md` — 3T5F reports read at S4
- `references/communication-frameworks.md` — ARCV, task formulation by D-level, ROAIP note
