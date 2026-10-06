# Chaining context and input source discovery — Step M9 context tables + Input Source Discovery Protocol

> Part of `meeting-processor`. Loaded on demand: the M9 section before invoking a downstream skill, the Input Source Discovery section at the start of a run when the user hasn't named a meeting source. The M9 offer table (which skill to offer per meeting type) and both triggers stay in SKILL.md.

## M9 — Context to pass

**Context to pass when invoking another skill:**

Every skill invocation from meeting-processor must include the **full participant context** and relevant meeting data:

| Context element | What to pass | Why |
|----------------|-------------|-----|
| **Participants** | Full list: name, email, role (from `team.members` match), attendance status (spoke / invited but silent / not invited but participated) | Task-creator uses participants for task assignment; product-research uses for interview attribution; brainstorm-features uses for idea ownership |
| **Meeting metadata** | Title, date, duration, type(s), organizer, recurrence info | Context for all downstream skills |
| **Meeting source link** | Fireflies link, calendar event link, or file reference | For traceability in created documents |
| **Extracted content** | Depends on target skill (see table below) | Core input for the target skill |
| **Attached materials** | Links to agenda, pre-read docs, presentations found in calendar | Additional context for requirements, research, concepts |

**Content to pass per target skill:**

| Target skill | What to pass |
|-------------|-------------|
| **task-creator** | Action items (who, what, deadline), task estimates, priorities, Epic reference if mentioned, participants with roles for task assignment |
| **requirements-creator** | Feature discussion fragments, functional requirements mentioned, user scenarios discussed, participants as stakeholders |
| **product-research** | User insights, quotes verbatim with speaker and timestamp (`reported`, as in the MoM), pain points, needs, participants as interview subjects |
| **brainstorm-features** | Ideas, hypotheses, evaluation criteria, voting results, participants as idea owners |
| **diagram-prototyper** | Process descriptions, flow logic, architecture discussed, participants as actors in diagrams |
| **decision-log** | Per decision: what was decided, context/rationale, options discussed, who decided, link back to these notes; since v3.7.0 also the owner, rejected options with their reasons, a dissent and a revisit condition — only those said in the meeting (`references/judgment-points.md` §4); since v3.8.0 `evidence_classes`: `reported` for what was stated in the meeting (`assumed` when a decision's only basis is an opinion voiced there), plus the labels of artifacts named in it — never inferred |
| **quarterly-planning** | Decisions that shift scope or focuses, with the meeting as the source link |

## Input Source Discovery Protocol

At the start of skill execution (before M1 or S1), if the user didn't explicitly specify a source:

1. **Check for uploaded files** — if the user attached a file in the message, use it
2. **Scan for meeting tool MCPs** — check which connectors are available:
   - Fireflies MCP → note as available
   - Other meeting tool MCPs → note as available
3. **Present available options** to the user:

> "I can get meeting data from the following sources:"
> - [List connected meeting tools]
> - Upload a file (audio, video, or text transcript)
> - Paste text directly in the chat

If no meeting tool MCP is connected and the user expects one — offer to search the MCP registry:
> "No meeting recording tool is connected. Would you like me to search for available connectors?"
