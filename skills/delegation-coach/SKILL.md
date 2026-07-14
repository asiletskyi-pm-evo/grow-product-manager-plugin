---
name: delegation-coach
version: 0.1.0
description: Audit a manager's operational load against the 7 levels of delegation and build a hand-off plan. Lists the PM's recurring activities, marks each on the 1-7 Appelo scale (current → target), picks delegation candidates from team profiles (D-type, GTD-index), and lays out the S1→S4 transfer of a direction. Use when the user asks to "audit my delegation", "what can I delegate", "I'm overloaded with ops", "delegation levels", "hand-off plan", "who can I give this to", "stop doing operations myself". Українською: "аудит делегування", "що можна делегувати", "я перевантажений операційкою", "рівні делегування", "план передачі", "кому це віддати", "вийти з операційки". Do NOT use to create the resulting tasks (task-creator), to set the delegate's goals (goal-setter), or to decide daily focus (focus-advisor — which chains here when it sees PM overload). This skill diagnoses delegation and plans the transfer; other skills execute it.
---

# Delegation Coach

Delegation is transferring tasks **and responsibility** for them to the team — the base skill a manager can't grow without. The best managers "do nothing" — they conduct, because they delegated almost everything. The main block on delegating lives in the manager's head, and it's the manager who must break the loop "I'm overloaded doing it all → the team gets no experience". This skill turns that into an audit + a concrete hand-off plan.

## Prerequisites
- `references/local-context-protocol.md` — Step 0. Context: `user.language`, calendar/Jira for the real activity list.
- `references/people-context-protocol.md` — **Step P** (read candidates' `d_type` + `gtd_index`; write delegation levels + transfer plan).
- `references/people-frameworks.md` — 7 levels of Appelo, S1→S4 evolution, internal blocks + counters.
- `references/roi-frameworks.md` — hiring/delegation ROI when "no one to delegate to".
- `references/goal-frameworks.md` — the S4 endpoint (set SMARTCBP goals, read 3T5F).
- `references/template-protocol.md` — **Step T** (delegation-audit artifact; internal structure if no template).
- `references/self-improvement.md`.

## The model (from people-frameworks)

**7 levels of Appelo:** 1 Tell · 2 Sell · 3 Consult · 4 Agree · 5 Advise · 6 Inquire · 7 Delegate. **Real delegation starts at level 5.** Levels 1–4 on routine work are candidates to push down.

**S1→S4 transfer of a direction:** immerse (S1) → mentor (S2) → step out of operations (S3) → goals + reports only (S4).

## Pipeline

### Step 0 — Local context
Per `local-context-protocol.md`.

### Step T — Template resolution
Per `template-protocol.md`: `artifact_type: delegation-audit`. No dedicated built-in template ships — resolve if a user template exists, otherwise render the audit-table + transfer-plan internal structure below.

### Step 1 — Build the activity list
List the PM's **recurring operational activities** — concrete task types (10–20), no abstractions like "manage the team". Gather from the user, and offer to mine the real list from the calendar and Jira (recurring meetings, report prep, triage). 

### Step 2 — Delegation audit table
One row per activity:

| Activity | Current level (1–7) | Candidate | Target level | Blocker |
|----------|--------------------|-----------|--------------|---------|
| A/B readout prep | 3 Consult | Olena (D3, GTD 0.81) | 6 Inquire | "still training" |

- **Blocker** is a controlled value: *"Impossible to transfer" / "Already training someone" / "Still looking for someone"*.
- Show the **level distribution** (% of activities at each level) — a low average = the skill has room to grow. Flag every level 1–4 routine item as a push-down candidate.

### Step 3 — Pick candidates (Step P)
For each push-down candidate, propose a delegate from team profiles:
- Read `d_type` and `gtd_index`. **Levels 5–7 only for consistently high GTD.** A D4 can take a full hand-off; a D1/D2 needs the S1→S2 immersion first.
- If **no one to delegate to** → compute hiring/outsourcing ROI (`roi-frameworks.md`) and surface the argument ("not hiring" isn't a saving if it blocks bigger work).

### Step 4 — Transfer plan (S1→S4)
For the chosen direction(s), lay out the S1→S4 timeline with dates and checkpoints: which channels/threads to add the delegate to, which meetings to attend (and the date they go alone), when to make them the meeting secretary (ARCV notes → tasks → control → reports), when to step out, and the S4 endpoint (SMARTCBP goals + 3T5F reports + bonuses).

### Step 5 — Work the internal block
If the PM resists ("faster myself", "they'll do it worse", "I'll become redundant"), surface the specific block and its counter from `people-frameworks.md` (professional trust, perfectionism, teaching-time, fears). Delegating badly (so the PM still does the work) is the failure mode to avoid.

### Step 6 — Persist & chain
- **Step P write:** save each candidate's delegation zones + levels + the transfer plan to their profile (gated).
- Chain: → `goal-setter` (set the delegate's S4 goals) · → `task-creator` (create the immersion/hand-off tasks) · ← `focus-advisor` (arrives here when it detects PM overload).

### Step 7 — Feedback + self-improvement
Per `self-improvement.md`.

## Quality standards
- Activities are concrete task types (10–20), never abstractions.
- Every activity has a current level, target level, and a controlled blocker value.
- Levels 5–7 require consistently high GTD; candidates are drawn from real profiles, not assumed.
- "No one to delegate to" triggers a hiring/delegation ROI computation, not a dead end.
- The transfer plan is dated S1→S4 with checkpoints; the endpoint is goals + reports.
- Language — `user.language`.

## Skill chaining
← `focus-advisor` (PM overload) · → `goal-setter` (delegate's goals) · → `task-creator` (hand-off tasks) · → `product-reporter` (the 3T5F reporting the delegate takes over) · → `one-on-one` (mentor the delegate through S1→S2).

## Example dialogues
- *"Я потонув в операційці, що делегувати?"* → mines calendar+Jira → audit table of 14 activities, 9 at levels 1–4 → flags "A/B readout prep" and "stakeholder status prep" as top push-downs → proposes Olena (D3, GTD 0.81) at target level 6 with an S1→S4 plan.
- *"Немає кому делегувати розбір багрепортів"* → computes ROI of a junior analyst hire vs the PM's hours → positive payback → drafts the argument for the manager + a role hand-off plan (chains to hiring-designer).
