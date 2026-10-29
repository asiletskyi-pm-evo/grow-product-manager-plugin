# Type-specific blocks — Step M5b

> Part of `meeting-processor`. Loaded on demand at Step M5, once the meeting types are confirmed at Step M3 — read the blocks for every confirmed type. Since v3.9.0 the PM-first pass section at the end is read earlier, right after the M4 format choice, when SKILL.md sends you here. The common blocks (M5a) and the classifier (M3) stay in SKILL.md.

**For Grooming / Planning:**

| Block | What to extract |
|-------|----------------|
| **Task estimates** | Story points or time estimates discussed per task |
| **Priorities** | Priority assignments (P0, P1, P2) or ordering |
| **Task assignments** | Who takes which task |
| **Blockers** | Dependencies or blockers raised |
| **Sprint scope** | What was included/excluded from the sprint |

**For Discovery / Interview:**

| Block | What to extract |
|-------|----------------|
| **User insights** | Key findings about user behavior, needs, or pain points — candidate insights from this one meeting, each traced to what a participant said (`reported`); what a teammate says about users is `reported (<teammate>)`, not a user's own words |
| **Quotes** | Direct user quotes that support insights — verbatim from the transcript, never from an AI summary: `«…» — <speaker>, <hh:mm> · reported` (timestamp where the source has one); a paraphrase loses its quote marks |
| **Pain points** | Specific problems the user described |
| **Needs / Jobs-to-be-done** | What the user is trying to accomplish |
| **Opportunities** | Product opportunities identified from the discussion |

**For Demo / Retro:**

| Block | What to extract |
|-------|----------------|
| **Feature feedback** | Reactions to demonstrated features — positive and negative |
| **What went well** | (Retro) Positive outcomes and practices to continue |
| **What went wrong** | (Retro) Problems, failures, things to improve |
| **Improvement proposals** | Suggested improvements and changes |

**For Status / Agreements:**

| Block | What to extract |
|-------|----------------|
| **Progress updates** | Status per project/feature/team member |
| **Agreements** | Commitments with responsible person and deadline |
| **Risks** | Risks or concerns raised |
| **Blockers** | Current blockers and who is resolving them |
| **Deadlines** | Mentioned deadlines and their status |

**For Brainstorm:**

| Block | What to extract |
|-------|----------------|
| **Ideas** | All ideas proposed during the session |
| **Evaluation** | Pros/cons, voting results, rankings if discussed |
| **Selected ideas** | Which ideas were chosen to pursue |
| **Next steps** | What happens next with the selected ideas |

## PM-first pass (after M4, since v3.9.0)

`references/judgment-points.md` §9 at this skill's step: Process mode, a meeting confirmed at M3 as Discovery / Interview, a verbatim transcript, Structured MoM chosen at M4, an interactive run, and `judgment.learning_mode` `pm_first` or `explain`. Not for Short summary, the "just a quick summary" escape hatch, Search mode, a 1-1 kept here, or a run with no user present.

- **Excerpts (`pm_first`).** Five passages from interviewee turns — speaker turns not matched to `team.members` — verbatim from the transcript itself (`fireflies_get_transcript`, the file or the pasted text), never from `fireflies_get_summary` or another AI summary. Each is one complete statement from one turn, personal data masked (`[name]`, `[order]`), with speaker and timestamp where the source has them; spread across the meeting (one from each fifth of it where possible) and shown in transcript order. With fewer qualifying turns, show those there are. With none, or with only a summary or notes and no verbatim transcript, print one notice line in `user.language` that the pass needs a verbatim transcript, and ask nothing.
- **The question.** One free-text message in `user.language`: tag each excerpt with one Discovery block — insight / pain point / need-JTBD / opportunity / nothing — plus a few words of your own. Partial tags count; a skip word skips; «вимкни» / "turn off" writes `- **Learning mode:** off` (§9). The first such question in a session adds one line on how to skip or switch it off.
- **Extraction stays independent.** M5b extracts on the transcript's own words: an excerpt the PM tagged is extracted, or not, exactly as it would be untagged. The tags change no block, insight, quote, pain point or opportunity, and never enter the MoM.
- **Your tags vs mine.** After M6 and before the M7 review question, one chat block in `user.language`: per excerpt, the PM's tag next to the block M5b put it in (or "not extracted"); agreements; and for each difference the transcript evidence that separates them (the surrounding turns, the same point made elsewhere in the meeting), or "no evidence decides this — your call". A change the PM asks for at M7 is applied as any M7 correction, and the M7 self-improvement check treats it as `references/self-improvement.md` says, its judgment-guard rule included.
- **`explain`.** Instead of the question and the comparison, one chat block "How I got here" at the same point before M7: the inputs used (transcript source, which speakers were read as interviewees), the extraction rule applied (the Discovery / Interview blocks above), and the two closest alternatives rejected (for example a pain point read as a need, or a statement kept as a quote rather than an insight). It asks nothing and never enters the MoM.
- **Chain.** M9 → product-research passes `pm_first: done | skipped | off` for this transcript (`references/chaining.md`), so the same material is never asked about twice. The tags themselves are not passed.
