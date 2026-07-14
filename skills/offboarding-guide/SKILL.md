---
name: offboarding-guide
version: 0.1.0
description: Guide a manager through parting ways with an underperforming team member — respectfully, on evidence, via a structured four-meeting algorithm. Checks that an evidence base (goals + reports) exists first, diagnoses "can't" vs "doesn't want", and drafts each conversation's ARCV follow-up plus a neutral team message. Use when the user asks to "help me let someone go", "offboarding", "PIP / probation for underperformance", "termination conversation", "how do I fire <person> fairly", "is it time to part ways". Українською: "допоможи звільнити", "офбординг", "випробувальний термін через недосягнення", "розмова про звільнення", "як коректно розлучитися зі співробітником", "чи час прощатися". Do NOT use for a routine review (performance-review), for setting corrective goals alone (goal-setter), or for hiring a replacement (hiring-designer — chain there after). This is the hardest manager conversation — the tone is deliberate and the data is strictly local.
---

# Offboarding Guide

Companies need goals achieved — a rational stance. The core message: **don't "drag" a person at the expense of your own management**. When someone "doesn't want" (Hersey-Blanchard) and every motivation tool is exhausted, parting ways is the right call. Dragging it out statistically doesn't work (roughly only 1 in 4 reanimations succeed), so the moment underperformance makes you consider it — act by the algorithm, respectfully and on evidence.

> **Tone & data:** this is the heaviest conversation a manager has. Be delicate, factual, and respectful. All materials are **strictly local/vault** (`data-policy.md`) — never Confluence/Jira, never external LLMs.

## Prerequisites
- `references/local-context-protocol.md` — Step 0. Context: `user.language`, calendar (schedule the meetings).
- `references/people-context-protocol.md` — **Step P** (read goals/reports/D-type/1-1 history; write offboarding state locally).
- `references/people-frameworks.md` — "can't" vs "doesn't want", the reanimation stats, motivation-tools checklist.
- `references/goal-frameworks.md` — the evidence base is SMARTCBP goals; chain to goal-setter if missing.
- `references/reporting-3t5f.md` — reports are the objective record of achievement.
- `references/roi-frameworks.md` — the "X dollars for Y tasks" rational check (optional).
- `references/communication-frameworks.md` — ARCV follow-ups after each meeting; NVC phrasing.
- `references/template-protocol.md` — **Step T** (`offboarding-plan`, `followup-arcv` templates).
- `references/data-policy.md` — highest-sensitivity tier (strictly local).
- `references/self-improvement.md`.

## Pipeline

### Step 0 — Local context · Step P — Person context
Load the person's profile: goals, last reports (Forecast QA), D-type, 1-1 history.

### Step T — Template resolution
Per `template-protocol.md`: `artifact_type: offboarding-plan` for the case plan, `followup-arcv` for each meeting's follow-up. Built-in templates; escape hatch uses the internal structure.

### Gate G — Evidence base
Before anything: **is there objective evidence** (set goals + reports/KPIs showing non-achievement)?
- **No** → stop and say so plainly: without goals and reports the conversation is "by feel" and won't be fair or defensible. Chain to `goal-setter` (set goals) and `product-reporter` (set up 3T5F) first, then return. This gate is mandatory.
- **Yes** → continue.

### Step 1 — Diagnosis
- **"Can't" (skill gap)** → maybe development, not offboarding — route back to `one-on-one`/`goal-setter`; reconsider.
- **"Doesn't want"** → the algorithm below (only ~25% reanimate; don't drag).
- Optional **"X dollars for Y tasks"** rational check (`roi-frameworks.md`): export the period's completed tasks, compare to the fully-loaded salary — "am I willing to keep paying X for Y delivered?"
- **Pre-screen:** run the motivation-tools checklist (SMARTCBP goals, knowledge map, career ladder, incentives, feedback, delegation, 1-1s, sabbatical…) — what has the PM *not* yet tried? Surface gaps before starting the algorithm.

### Step 2 — The four-meeting algorithm
Guide the case meeting by meeting; each ends with an **ARCV follow-up** emailed to the person.

1. **Meeting 1 — critical issues.** Make clear you're dissatisfied with the *results* (not personality); direct but constructive, ≥45 min, a dialogue. **Do not mention possible dismissal** — signal it's still fixable with effort. Follow-up on the problem areas. No material change in ~a month (or change that rolled back) → meeting 2.
2. **Meeting 2 — warning + measurable probation.** State exactly what to fix / achieve and by which date; set a clear probation term (e.g. 2 weeks / 1 month) and book the results meeting now. Ensure the person understands unambiguously: (a) results are unsatisfactory, (b) which goals by when, (c) dismissal follows if unchanged — no hints or euphemisms. If they resign themselves — that's fine, do nothing.
3. **Meeting 3 — probation results.** Passed → congratulate, and say you expect this level sustained. Not passed → dismiss, **no further chances** (not even a hint of a second chance in your voice). Responsibility sits with the person; the manager did everything possible — no guilt.
4. **Meeting 4 — sustainability check.** People often relax after probation; if problems return → dismiss without another probation (use the plain narrative script). If working well after ~3 months → congratulate — the manager's win (≈1 in 4).

### Step 3 — Immediate dismissal (no algorithm)
Theft (money/info/clients), other unlawful acts, or ethics violations → immediately. A newcomer who fails the probation-period goal letter → didn't pass (no long algorithm).

### Step 4 — The dismissal conversation & team message
Help draft (respectful, facts-only, ≥30 min):
- **Script:** thank them for their contribution; explain reasons clearly and structurally — non-achievement of goals/results with facts/KPIs, **not** personal qualities; agree the wording + team message; agree the last working day. If the reaction is emotional — don't interrupt, let them vent, stay calmly kind. Never say "lazy / hopeless / can't learn"; say "you didn't meet your goals and tasks on time / didn't show these KPIs".
- **Team message** (written by the manager, agreed with the person during/after the talk): "I let X go for these reasons" + reasons + last day + reminder to reassign the person's open tasks. Clear and official (radical candor) so it's not gossip.
- **Softening** for hard personal circumstances (optional): advance notice, a month or two of pay, outplacement help, temporary part-time.

### Step 5 — Persist & chain
- **Step P write (strictly local):** offboarding state + follow-ups in `People/offboarding/…`; mark `d_type` accordingly. Gated show-before-save. Never leaves the machine.
- Chain: ← `performance-review` (arrives here when "doesn't want" and tools are exhausted) · → `hiring-designer` (re-design the role + a hiring retro) · → `task-creator` (reassign open tasks).

### Step 6 — Feedback + self-improvement
Per `self-improvement.md`.

## Quality standards
- **Evidence gate is mandatory** — no goals/reports → set them first, don't proceed "by feel".
- Facts and results only in every conversation; never personal characterization (NVC).
- Follow the four meetings in order; each with an ARCV follow-up and a booked next date; no hinted second chances after a failed probation.
- Immediate dismissal only for theft/unlawful/ethics.
- Respectful, delicate tone throughout; try to keep good relations (re-hiring later is fine except for lies/ethics violations).
- **Strictly local** — offboarding data never goes to Confluence/Jira/external services.
- Language — `user.language`.

## Skill chaining
← `performance-review` · → `goal-setter` (evidence gate) · → `product-reporter` (evidence gate) · → `one-on-one` (if "can't" → development) · → `hiring-designer` (replacement + retro) · → `task-creator` (reassign tasks) · → `schedule` (book the sequence).

## Example dialogues
- *"Думаю звільнити аналітика, він не тягне"* → Step P shows no formal goals set → **Gate G fails** → "There's no goal/report evidence — let's set goals via goal-setter and stand up 3T5F reporting first, otherwise this is by-feel." → returns after evidence exists.
- *"Евіденс є, він 'не хоче'. Що далі?"* → runs the motivation-tools pre-screen (career ladder + sabbatical untried) → if PM still proceeds → guides Meeting 1 with an ARCV follow-up draft and a 1-month check reminder.
- *"Провалив випробувальний, готую розмову"* → Meeting-3 dismissal script (facts, no personal blame) + agreed team message with the three required elements + reassignment task list → chains to hiring-designer for the role re-design.
