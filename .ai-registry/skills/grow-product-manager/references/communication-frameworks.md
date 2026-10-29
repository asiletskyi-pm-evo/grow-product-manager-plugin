# Communication Frameworks

Methodology reference for manager communication: meeting follow-ups (ARCV), message quality (CBI), and task formulation by performer level. Consumed by `meeting-processor` (ARCV), `one-on-one` and `offboarding-guide` (follow-ups), `task-creator` (task formulation), and read across the People-contour. Framework terms (ARCV, CBI, TL;DR, 3W1H, STAR, DoD) are the plugin's working vocabulary.

---

## ARCV — actionable follow-ups

A follow-up is the record of a meeting's outcomes that fixes **who** does **what** by **when**. Without it, each participant leaves with their own version of the agreement.

> **Fixed-agreement principle:** if a meeting happened and it was not clearly written down who does what and how (and confirmed), you will meet again on the same topic — having wasted the effort on rework, idle time, and irritation.

**Three follow-up types:** (1) *transcript* — verbatim, useful for interviews/keyword search; (2) *theses* — a summary, **not** a real follow-up (no who/what); (3) **actionable follow-up** — the real thing, structured by ARCV.

**ARCV — four criteria of a quality follow-up:**

| Letter | Criterion | Rule |
|--------|-----------|------|
| **A** — Actions | Only items that must be *done*; each numbered; one item = one number. |
| **R** — Responsible | Exactly **one** responsible person per action. Two+ → the result may not happen. |
| **C** — Clearly | Each item unambiguous — someone who wasn't in the meeting understands what to do. |
| **V** — Verbs | Each item starts with an active perfective verb + deadline if needed: "**Olia will produce** the doc by Apr 1", not "Doc — responsible: Olia". |

**Decisions block (separate from Actions):** important agreements that can't become tasks (no owner/action). E.g. "CEO launches no new projects due to load"; "if the mailing yields no 2 potential deals in 2 months — stop the process."

**Meeting rules for a good follow-up:** there is a **secretary** (owns the follow-up until an owner is assigned); the follow-up is written **during** the meeting (writing it after distorts it); it is **accepted by all participants** at the end.

**`meeting-processor` ARCV standard:** emit numbered Actions each with one Responsible and an active perfective verb + optional deadline, pass a Clearly-check (a stranger could execute it), and a separate **Decisions** block. This is the required quality bar for the skill's follow-up output.

---

## CBI — Communications that Bring Implementation

Written communication that moves a task/question/problem toward resolution. Goal: write so the recipient can act (or answer to full satisfaction) with **minimal clarification** — ideally one message is enough.

**Nine rules (condensed):**
1. No bare "hi" — greeting and the question in one message.
2. Lead with **TL;DR** — the first sentence carries the essence ("TL;DR: need budget approval of ₴15,000 for the new campaign by Jun 12").
3. Precise terms — not "conversion" but "conversion from organic traffic to leads"; Gross/Net Revenue, Gross/Net Profit, EBITDA.
4. Visual formatting — numbering, emoji, bold, paragraphs.
5. End with a clear list of actions: what the recipient must do and by when. For each attachment: (a) what you expect (review/check/FYI), (b) 2–3 keywords of what it is. *"Softness is fine. Vagueness breeds inaction."* — if no action is needed, prefix **FYI**.
6. When something only "seems" so — ask precisely to get an unambiguous answer ("Did you export the emails of **ALL** clients for **all time**?"). Question mark if it's a question; number multiple questions.
7. If three messages don't resolve it — call a 3-minute meeting instead of chat ping-pong.
8. Direct communication between people where possible — no "broken telephone".
9. Convey the essence with the necessary minimum — techniques:
   - **3W1H** (for setting/requesting): **What** to do · **When** (deadline) · **Why** (importance) · **How** (format/method).
   - **STAR** (for reporting done work): **Situation** · **Task** · **Action** · **Result** (with numbers).

**CBI test used by skills:** *would the recipient answer without asking for clarification?* If not — tighten with TL;DR + 3W1H, add the question mark and the expected action.

CBI is care for the other person's time and focus, not "dryness".

---

## Task formulation — "why + what + how" + DoD (by D-level)

Formulating a task in text is a base management skill. Depth depends on the performer's D-level (`references/people-frameworks.md`): a **D4 gets goals, not tasks**; most others need a clearly formulated task with why/what/how.

**Structure of a well-set task:**

1. **Title** — perfective verb (result-oriented): "Collect reviews…", not "Reviews collection…". Full essence in the title (readable in a filter list); length is free ("you don't pay per character"). Optional clean-time tag: `2D`, `3H`.
2. **Description = "why" + "what" + "how":**
   - **Why** — meaning and motivation (missing "why" → formal execution and demotivation); also a teaching tool. Systemic fix: a mandatory "Why" field in the tracker.
   - **What** — the result, as clear and short as possible; if it's already in the title, don't duplicate.
   - **How** — depends on the performer's level: **D4 → can omit "how"**; **D1 → detailed, ideally a checklist**. ("If you order borscht from a chef, don't explain how to chop the cabbage.")
3. **Checklist** (more important than prose description — checklist first, then description, no duplication): D4 → only non-obvious points + audit checkpoints; D1 → also the obvious steps a newcomer doesn't know yet, "how I'd do it". Useful item: "check the task's impact on the goal in X months".
4. **Definition of Done (DoD)** — acceptance criteria; don't start until DoD is agreed. Use for critical / alpha tasks, not every task.
5. **Deadline or priority** — one of the two (prefer priority; if a deadline, use "the latest I'd want it done by").

> **Plugin note:** `task-creator` applies why/what/how + DoD + how-depth-by-D-level. It does **not** enforce a single responsible per task — that requirement is intentionally **omitted** here because it conflicts with the team's process.

**Multiply estimates** from performers ("a month" → expect two; "three days" → a week) while teaching the team to build in contingencies.

---

## Typical errors (flag in linters)
- Follow-up written after the meeting; not accepted by participants; made a transcript/theses instead of actions; two+ responsibles; noun/process phrasing instead of perfective verbs.
- Bare "hi"; message without a question mark when an answer is expected; vague terms; attachment without cover text/expected action; multi-day ping-pong instead of a call.
- Task title as a process ("Market analysis" vs "Conduct market analysis"); cryptic short title; missing "why"; over-detailed "how" for a senior or none for a newcomer; duplicated description/checklist.

---

## References
- `references/people-frameworks.md` — D1–D4 levels that tune "how"-depth
- `references/goal-frameworks.md` — a D4 gets a goal instead of a task
- `references/roi-frameworks.md` — ROAIP economics for "why" / cost-of-decision
- `skills/meeting-processor/SKILL.md`, `skills/task-creator/SKILL.md` — consumers
