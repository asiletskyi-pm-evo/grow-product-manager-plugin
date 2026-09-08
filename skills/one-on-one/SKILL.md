---
name: one-on-one
version: 0.1.2
description: Prepare for and analyze 1-1 meetings with a team member — a meeting FOR the person and ABOUT the person (feedback, growth, trust), not a status/task sync. Prepare mode builds an agenda from the person's profile (D-type, goals, past follow-ups, GTD trend) with the seven "how" questions and NVC-framed feedback drafts. Analyze mode turns a transcript or notes into signals (motivation, burnout, conflict, career) plus an ARCV follow-up and a profile update. Use when the user asks to "prepare for a 1-1", "1-1 with <person>", "analyze this 1-1", "who haven't I had a 1-1 with", "one-on-one prep/notes", "questions for a 1-1". Українською — "підготуватись до 1-1", "1-1 з <людиною>", "розбери 1-1", "з ким давно не було 1-1", "нотатки 1-1", "питання для 1-1". Do NOT use for status/task meetings or general meeting notes (meeting-processor), for setting goals (goal-setter), or for a formal performance review (performance-review). meeting-processor detects a 1-1 and redirects here.
---

# One-on-One

> **Path rule.** A bare `references/<file>.md` in this file is read from this skill's own `references/` if the file exists there, otherwise from the **shared** `references/` at the plugin root. Resolve the root as `${PLUGIN_ROOT}`, else `${CLAUDE_PLUGIN_ROOT}`, else the directory that contains `skills/`, found by walking up from this folder (`references/host-profiles.md` §6). Never continue without a protocol named here.

A 1-1 is a regular manager↔person meeting for **feedback, the person's problems, and trust** — a meeting *for the person and about the person*, shifting from the "manager-subordinate" vertical to a "human-human" horizontal. The most common mistake is treating it as a task/status meeting (that's a separate sync). **The manager prepares** and **the manager writes the follow-up** (a sign of care — the person shouldn't have to).

## Prerequisites
- `references/local-context-protocol.md` — Step 0. Context: `user.language`, calendar integration.
- `references/people-context-protocol.md` — **Step P** (load/create profile; write 1-1 log, signals, D-type transitions).
- `references/people-frameworks.md` — D1–D4 (tone), NVC feedback, "Did you tell them yourself?", cognitive vs emotional empathy.
- `references/communication-frameworks.md` — ARCV follow-up standard.
- `references/goal-frameworks.md` — align personal goals; chain to goal-setter.
- `references/integration-strategy.md` — Fireflies (transcripts), Calendar (cadence/scheduling).
- `references/template-protocol.md` — **Step T** (`one-on-one-notes`, `followup-arcv` templates).
- `references/data-policy.md` — 1-1 notes are People-data (local/vault only).
- `references/self-improvement.md`.

## Modes

| Mode | Trigger | What it does |
|------|---------|--------------|
| `prepare` (default) | "підготуватись до 1-1", "1-1 with <person>" | Build the agenda from the profile + the 6-stage structure + tailored questions + NVC feedback drafts. |
| `analyze` | "розбери 1-1", transcript/notes provided | Extract signals, write the ARCV follow-up, update the profile, chain if needed. |
| `coverage` | "з ким давно не було 1-1" | Who among direct reports is overdue (also the headless payload). |

## The 1-1 is NOT
A task/status meeting, a goals-planning meeting, or a hybrid of all three in one hour; a meeting with a third person present (unannounced); a rushed <30-min session. Each meeting type has its own purpose — keep the 1-1 for the person.

## Pipeline

### Step 0 — Local context
Per `local-context-protocol.md`.

### Step P — Person context
Per `people-context-protocol.md`. Load the profile: `d_type`, active goals, `one_on_one` history + last follow-up, `gtd_index` trend, `signals`. If no profile — offer to create one.

### Step T — Template resolution
Per `template-protocol.md`: `artifact_type: one-on-one-notes` for prepare/analyze notes, `followup-arcv` for the actionable follow-up. Resolve the built-in templates; escape hatch "no template" uses the internal structure.

### Mode: prepare
Build an agenda around the **six stages**:
1. **Intro** — start from the last follow-up's action items. For guarded people use the **seven "how" questions**: (1) How are you? (2) How was this month? (3) How do you rate your own results (a 10-scale is easiest)? (4) …the team's results? (5) …your development here? (6) How would you *like* to develop? (7) How is it working with me? For quiet people, the manager shares about themself first to lower the distance.
2. **The person's questions** — the person is the main character; they raise what's uncomfortable to say publicly. "Too much about the person, too little about the work" is correct here.
3. **The manager's questions** — genuine interest in how they're doing + work effectiveness (positive feedback and constructive critique), align personal goals with company goals. **Not** specific tasks.
4. **Follow-up** — the manager writes it (see analyze).
5. **Schedule the next** — weekly / biweekly / at least monthly; Friday is recommended. Reschedule, never cancel.
6. **Thanks** — build a culture of gratitude.

Draft 3–5 **personalized questions** from the profile (recent wins, open action items, D-type, career signals) and, where a difficult topic exists, an **NVC feedback draft** ("When [fact], I feel [feeling], because [need]; could you [request]?"). Tune depth to `d_type`. Present the agenda as talking-points (not a rigid script). Remind the PM to block time *after* the meeting to process it.

### Mode: analyze
Input: a Fireflies transcript (via `integration-strategy.md`) or notes.
1. **Signals** — motivation, burnout/overload, conflict, career expectations, life stressors. Separate **facts from assumptions** (a guess is not a fact). If the person complained about a colleague → apply "**Did you tell them yourself?**" (route to a direct conversation, don't relay).
2. **Two note types:** an **ARCV Actionable Follow-up** (numbered actions, one responsible each, active verbs, Clearly-check; the manager writes it) and **plain notes** (observations/facts about the person).
3. **Profile update (Step P):** append the 1-1 log entry + follow-up ref, update `signals`, record any `d_type` transition. Gated show-before-save; **stays local/vault**.
4. **Chain if warranted:** → `decision-log` (if an important agreement was reached) · → `goal-setter` (revise goals) · → `performance-review` (if a review is due) · → `task-creator` (only genuine action items, and only if the person owns them — a 1-1 is not a task meeting).

### Mode: coverage / Headless
Contract (analogous to experiment-tracker stale-check): `mode=coverage headless=true` → no questions → list direct reports **not "touched" in > N weeks** (default: monthly for newer people, quarterly for >1-year trusted; overridable per profile), with a suggested Friday slot, or "everyone covered". Offer to create a weekly schedule via the platform's `schedule` skill.

### Step V — Vault Save
1-1 notes and follow-ups save to `People/1-1/…` **locally/vault only** — never Confluence (data-policy).

## Quality standards
- A 1-1 is about the person, not tasks; if it drifts to task-tracking, name it and redirect.
- The manager prepares and writes the follow-up; the follow-up is ARCV-compliant.
- Signals are separated into facts vs assumptions; colleague complaints route via "Did you tell them yourself?".
- Feedback is NVC (facts, not personal traits); prefer cognitive empathy to avoid burnout.
- Cadence: touch every direct report within a month; reschedule, never cancel.
- People-data locality: notes never leave the vault/local.
- Language — `user.language`.

## Skill chaining
← `meeting-processor` (detects a 1-1 → redirects here) · → `decision-log` · → `goal-setter` · → `performance-review` · → `task-creator` (owned action items) · → `schedule` (weekly coverage check).

## Example dialogues
- *"Підготуй мене до 1-1 з Олексієм"* → Step P (D2, GTD dipped last sprint, overload signal) → agenda with the seven "how" questions, a burnout-check block, and an NVC draft about two missed deadlines → reminder to book post-meeting processing time.
- *"Ось транскрипт 1-1, розбери"* → signals (wants mentoring role; friction with a QA colleague) → applies "Did you tell them yourself?" on the QA friction → ARCV follow-up (manager-owned) → updates profile signals, offers to chain to goal-setter.
- *"З ким я давно не бачився один-на-один?"* → coverage list: "Maria — 6 weeks (overdue), Ivan — 3 weeks" → offers Friday slots.
