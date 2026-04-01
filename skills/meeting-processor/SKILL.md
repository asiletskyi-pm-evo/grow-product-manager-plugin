---
name: meeting-processor
version: 0.9.0
description: Process meeting recordings, transcripts, and notes to extract action items, decisions, and structured reports. Use when the user asks to "summarize meeting", "meeting notes", "what was discussed", "action items", "MoM", or provides a meeting transcript/recording. Supports Fireflies, other meeting tools via MCP, uploaded files, and pasted text. Chains to feature-task-creator, requirements-creator, product-research, and brainstorm-features.
---

# Meeting Processor

Process meetings from any source — Fireflies, other recording tools, uploaded files, or pasted text — to extract action items, decisions, and structured meeting reports. The skill classifies the meeting type, adapts the output format, and chains to other plugin skills for follow-up actions.

## Integration prerequisite

Before starting, read and follow the integration fallback chain in `references/integration-strategy.md`. This skill can use:

- **Fireflies MCP** — for searching, reading summaries, and transcripts from Fireflies.ai
- **Other meeting tool MCPs** — if the user has connected another meeting recording tool (Otter.ai, Grain, tl;dv, Zoom, Google Meet, etc.), discover and use its MCP connector
- **Google Calendar MCP** — for finding calendar events, extracting participants, attached documents, meeting links, and agenda
- **Microsoft Calendar MCP** — alternative calendar connector (Outlook / Microsoft 365). If Google Calendar MCP is not available — search MCP registry for Microsoft Calendar
- **Confluence** — for publishing meeting notes / MoM
- **Notion** — alternative publishing destination
- **Jira** — for creating action item tasks (via feature-task-creator chaining)

For each product: check for MCP connector → search MCP registry → fall back to browser.

Before gathering any data, also read and comply with `references/data-policy.md`. Meeting transcripts may contain confidential discussions — treat all meeting content as internal data. Do NOT pass raw transcript content to external LLMs or third parties.

## Local context prerequisite

**Before starting, follow `references/local-context-protocol.md` (Step 0).** Read `local-context.md`, select the active product, and load all product-specific context. If the file doesn't exist — redirect to Plugin Configurator for initial setup.

Key context used by this skill:
- `team.members` — for matching speaker names to team roles
- `product.name`, `product.jira_project_key` — for linking action items to the product context
- `product.confluence_space` — for publishing meeting notes
- `user.language` — for output language

---

## Mode Selection

At the start of execution, determine which mode to use based on the user's request:

| Mode | When to use | Trigger phrases |
|------|------------|----------------|
| **Process** | Working with a single meeting — extract notes, action items, decisions | "summarize meeting", "meeting notes", "MoM", "action items from meeting", user provides a transcript/recording |
| **Search** | Finding information across multiple meetings | "what was discussed about X", "find decisions about Y", "search meetings for Z", "what did we agree on about X last month" |

If the user provides a meeting link, file, or transcript — automatically enter **Process** mode.
If the user asks a question about past meetings — automatically enter **Search** mode.

---

## Mode: Process — Workflow

### M1 — Determine input source

The skill is **tool-agnostic** — it accepts meetings from any source. Determine the input type:

| Input source | How to detect | How to read |
|-------------|--------------|-------------|
| **Fireflies meeting** | User mentions Fireflies, provides a Fireflies link, or asks to find a recent meeting with Fireflies connected | Use Fireflies MCP: `fireflies_search` to find → `fireflies_get_summary` + `fireflies_get_transcript` to read |
| **Other meeting tool MCP** | Another meeting tool MCP is connected in the session (detected during MCP scan) | Use the available MCP tools to search and fetch the meeting |
| **Uploaded file** | User uploads a file: audio (.mp3, .wav, .m4a, .ogg), video (.mp4, .webm), text transcript (.txt, .docx, .srt, .vtt), or PDF | Read the file content. For audio/video — note that transcription may require an external service; offer to use the browser to upload to a transcription tool if needed |
| **Pasted text** | User pastes meeting notes or transcript directly in the chat | Use the pasted text as-is |
| **No source provided** | User asks for meeting processing but doesn't specify a source | Ask via AskUserQuestion: "Where should I get the meeting from?" — list available options based on connected MCPs and offer file upload / text paste |

**M1a. For Fireflies (or similar MCP-based tool):**

1. Ask what meeting to process — the user may provide:
   - A meeting title or partial title
   - A date ("yesterday's grooming", "Monday's sync")
   - A participant name ("meeting with [name]")
2. Search using the meeting tool's API (e.g., `fireflies_search` with keyword, date, participants)
3. If multiple results found — present a list and ask the user to choose
4. If one result — confirm with the user before proceeding

**M1b. For uploaded files:**

1. Read the file content
2. For text files (.txt, .docx, .srt, .vtt) — extract the text directly
3. For audio/video files — inform the user: "I can see the file, but I need to transcribe it first. Would you like me to use [available transcription service] via browser?" Follow the integration fallback chain for transcription tools
4. For .srt/.vtt subtitle files — parse timestamps and speaker labels

**M1c. For pasted text:**

1. Accept the text directly
2. Attempt to identify speaker labels (e.g., "John:", "Speaker 1:", timestamps)
3. If no speaker labels — proceed with unstructured text analysis

### M1d — Calendar enrichment (optional)

After determining the meeting source, **ask the user if they want to pull additional context from the calendar event:**

> "Would you like me to check the calendar for this meeting? I can get the participant list, agenda, attached documents, and any linked materials."

If the user agrees — proceed with calendar lookup. If the user declines — skip to M2.

**M1d-1. Detect available calendar connector:**

| Calendar | How to detect | MCP tools |
|----------|--------------|-----------|
| **Google Calendar** | Google Calendar MCP is connected (`gcal_list_events`, `gcal_get_event`) | Use `gcal_list_events` to search by date/title → `gcal_get_event` to read details |
| **Microsoft Calendar** | Microsoft Calendar / Outlook MCP is connected | Use the available MCP tools to search and fetch events |
| **No calendar** | No calendar MCP detected | Offer to search the MCP registry: "No calendar tool is connected. Would you like me to search for available calendar connectors?" |

**M1d-2. Find the matching calendar event:**

Search for the event using available data:
- Meeting title (from Fireflies, file name, or user input)
- Meeting date
- Participant names or emails

If multiple events match — present a list and ask the user to choose.

**M1d-3. Extract calendar event data:**

From the calendar event, extract:

| Data point | Where to find | How to use |
|-----------|--------------|-----------|
| **Participants** | Attendee list (names + emails + RSVP status) | Enrich the participant list with full names, emails, and attendance status. Match against `team.members` from `local-context.md` to add roles |
| **Agenda / description** | Event description / body | Use as context for understanding meeting goals and structure |
| **Attached documents** | Event attachments or links in description (Google Docs, Confluence pages, presentations, PDFs) | Read attached materials to enrich meeting context. These may contain the agenda, pre-read materials, or relevant specs |
| **Meeting link** | Conference URL (Google Meet, Zoom, Teams) | Use to cross-reference with Fireflies/other meeting tools if needed |
| **Organizer** | Event organizer field | Identify the meeting owner |
| **Recurrence** | Recurring event info | Note if this is a recurring meeting (useful for context: "weekly grooming", "bi-weekly sync") |

**M1d-4. Read attached materials:**

If the calendar event contains links to documents:
- **Google Docs / Slides / Sheets** — read via Google Drive MCP or browser
- **Confluence pages** — read via Confluence MCP (respect `noindex` label rule from `local-context.md`)
- **Figma links** — read via Figma MCP
- **PDF / PPTX / other files** — download and read content
- **Other URLs** — note them as reference materials

Present discovered materials to the user:

> "I found the following materials attached to the calendar event:
> 1. [Document title] — [type: Google Doc / Confluence page / etc.]
> 2. [Document title] — [type]
>
> Would you like me to read them for additional context?"

If the user confirms — read the materials and use their content to enrich the meeting analysis (better understanding of topics, decisions, and action items).

**M1d-5. Merge calendar data with meeting data:**

Combine the calendar event data with the transcript/recording data:
- **Participants:** merge attendee list from calendar with speakers from transcript. Calendar provides full names + emails + roles; transcript provides who actually spoke
- **Context:** use agenda/description and attached materials to better classify meeting topics and understand decisions
- **Mark absent participants:** if someone was on the calendar invite but not in the transcript — note as "invited but did not attend" (useful for status meetings)

### M2 — Read meeting data

Based on the input source, extract as much structured data as possible:

| Data point | From Fireflies MCP | From transcript file/text | From calendar (M1d) |
|------------|-------------------|--------------------------|---------------------|
| **Title** | From meeting metadata | From filename or first line, or ask user | From event title |
| **Date** | From meeting metadata | From file metadata or ask user | From event start time |
| **Duration** | From meeting metadata | Estimate from timestamps if available | From event start/end time |
| **Participants** | From speaker tags in transcript | Parse speaker labels or ask user | From attendee list (names + emails + roles + RSVP) |
| **Agenda** | — | — | From event description |
| **Attached materials** | — | — | From event attachments and links |
| **Summary** | From `fireflies_get_summary` (overview) | Generate from transcript analysis | — |
| **Action items** | From `fireflies_get_summary` (action_items) | Extract from transcript content | — |
| **Keywords** | From `fireflies_get_summary` (keywords) | Extract from transcript analysis | — |
| **Full transcript** | From `fireflies_get_transcript` (sentences with speakers) | From file content | — |
| **Organizer** | — | — | From event organizer field |
| **Recurrence** | — | — | From recurring event info |

If the source provides a pre-built summary (like Fireflies) — use it as a starting point but always cross-reference with the full transcript for completeness.

**Data merging priority:** When the same data point is available from multiple sources, use this priority:
1. **Calendar** — for participants (most complete: names, emails, roles, attendance)
2. **Meeting tool** (Fireflies etc.) — for transcript content, summary, action items
3. **File/text** — as fallback for content

Mark discrepancies: if a participant is on the calendar but not in the transcript → "invited, did not speak". If a speaker is in the transcript but not on the calendar → "not on invite, but participated".

### M3 — Classify meeting type

Analyze the meeting title, keywords, and content to determine the meeting type(s). **A meeting can have multiple types.**

**Auto-classification rules:**

| Type | Title signals | Content signals |
|------|--------------|----------------|
| **Grooming / Planning** | "grooming", "refinement", "planning", "sprint", "estimation", "backlog" | Story points, estimates, task decomposition, acceptance criteria, priorities |
| **Discovery / Interview** | "discovery", "interview", "user research", "UX research", "customer call" | User pain points, needs, quotes, insights, personas, use cases |
| **Demo / Retro** | "demo", "review", "retro", "retrospective", "showcase" | Feature demonstrations, feedback, what went well/badly, improvements |
| **Status / Agreements** | "status", "sync", "standup", "weekly", "check-in", "alignment" | Progress updates, blockers, deadlines, agreements, commitments, responsibilities |
| **Brainstorm** | "brainstorm", "ideation", "workshop", "design thinking" | Ideas, proposals, voting, pros/cons, concept exploration |

**After auto-classification, confirm with the user:**

> "Based on the title and content, this appears to be a **[type(s)]** meeting. Is that correct? Or would you like to adjust?"

Present the detected types and allow the user to:
- Confirm
- Add additional types
- Remove incorrect types
- Choose a completely different type

### M4 — Choose output format

Ask the user via AskUserQuestion:

> "What format should the meeting report have?"

| Format | Description | When to recommend |
|--------|------------|------------------|
| **Structured MoM** | Full meeting minutes: participants, topics, decisions, action items, open questions, type-specific sections → publishable to Confluence/Notion | Default for grooming, status, demo meetings |
| **Short summary** | 3-5 sentences: what was discussed, key decisions, next steps | Quick recaps, brainstorms, casual syncs |

Recommend a format based on the meeting type, but let the user choose.

### M5 — Extract and structure content

Analyze the transcript (or summary + transcript) to extract structured information.

**M5a. Common blocks — extracted for ALL meeting types:**

**Participants:**
- Extract from speaker tags in the transcript
- Match against `team.members` from `local-context.md` to add roles
- List as: Name — Role (if known)

**Topics discussed:**
- Identify distinct topics/themes from the conversation
- For each topic: brief summary (2-3 sentences)
- Order chronologically as discussed

**Decisions:**
- Extract explicit decisions: statements where participants agreed on something
- Look for language patterns: "we decided", "agreed to", "let's go with", "the decision is", "вирішили", "домовились", "обрали варіант"
- For each decision: what was decided, context/rationale, who was responsible (if mentioned)

**Action items:**
- Extract tasks that someone committed to doing
- Look for language patterns: "I'll do", "take this", "action item", "TODO", "зроблю", "візьму", "треба зробити"
- For each action item: what needs to be done, who owns it, deadline (if mentioned)
- Cross-reference with Fireflies action_items if available — merge, don't duplicate

**Open questions:**
- Extract unresolved discussions, questions left without a clear answer
- Look for: "we need to figure out", "let's discuss later", "open question", "TBD", "треба з'ясувати", "повернемось до цього"

**M5b. Type-specific blocks:**

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
| **User insights** | Key findings about user behavior, needs, or pain points |
| **Quotes** | Direct user quotes that support insights (with speaker attribution) |
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

### M6 — Generate output

**M6a. Structured MoM format:**

Generate the meeting report using the user's preferred language (`user.language`):

```markdown
## Meeting Notes — [Title]

**Date:** [date] | **Duration:** [duration] | **Type:** [grooming, discovery, ...]

---

### Participants
| Name | Role | Email | Status |
|------|------|-------|--------|
| [name] | [role or "—"] | [email] | Attended / Invited, did not speak / Not on invite |

---

### Topics Discussed
1. **[Topic title]** — [2-3 sentence summary]
2. **[Topic title]** — [2-3 sentence summary]

---

### Decisions
| # | Decision | Context | Owner |
|---|----------|---------|-------|
| 1 | [what was decided] | [why / context] | [who] |

---

### Action Items
| # | Action | Owner | Deadline | Status |
|---|--------|-------|----------|--------|
| 1 | [what needs to be done] | [who] | [when, if mentioned] | Open |

---

### [Type-specific section(s)]
[Content based on meeting type — see M5b]

---

### Open Questions
- [unresolved item 1]
- [unresolved item 2]
```

**M6b. Short summary format:**

Generate a concise summary (3-5 sentences) covering:
1. What was the meeting about (1 sentence)
2. Key decisions made (1-2 sentences)
3. Main action items and next steps (1-2 sentences)

### M7 — Review with user

> "Here are the meeting notes. Please review — are there any corrections or additions?"

- If the user requests changes — apply corrections and re-present
- If the user adds context the transcript missed — incorporate it
- If the user confirms "OK" — proceed to publishing

**Self-improvement check** (after corrections are applied and confirmed):

If the user requested corrections during review, analyze whether the skill's algorithm can be improved to prevent similar issues in the future. Follow the full protocol in `references/self-improvement.md`.

### M8 — Publishing

**M8a. Ask if the user wants to save:**

> "Would you like to publish these meeting notes?"

Options via AskUserQuestion:
- **Confluence** — create or update a page in the configured space
- **Notion** — create a page in Notion workspace
- **Local file** — save as .md file in the user's workspace
- **No** — keep in chat only

**M8b. Confluence publishing:**

- Ask which space and parent page (suggest from `local-context.md` if configured)
- Title format: `[Meeting type] — [Meeting title] — [Date]`
- Use Confluence formatting: ToC macro, tables, dividers, panels
- Publish via Confluence MCP (`createConfluencePage`)

**M8c. Notion publishing:**

- Ask which page or database
- Adapt to Notion formatting
- Publish via Notion MCP

### M9 — Skill chaining

After publishing (or if the user decided not to save), offer the next step **based on meeting type(s) and extracted content:**

| Meeting type | Condition | Offer |
|-------------|-----------|-------|
| **Grooming / Planning** | Action items with task assignments extracted | "Would you like to create Jira tasks for the discussed items? I'll pass the context to Feature Task Creator." → invoke `feature-task-creator` |
| **Discovery / Interview** | User insights and quotes extracted | "Would you like to synthesize these interview insights into a research report? I'll pass the context to Product Research." → invoke `product-research` |
| **Discovery / Interview** | Feature ideas or requirements discussed | "Would you like to write requirements based on the discussed feature? I'll pass the context to Requirements Creator." → invoke `requirements-creator` |
| **Brainstorm** | Ideas and hypotheses extracted | "Would you like to score and prioritize these ideas? I'll pass the context to Brainstorm Features." → invoke `brainstorm-features` |
| **Status / Agreements** | Agreements with deadlines | "Would you like to create Jira tasks for the agreed action items?" → invoke `feature-task-creator` |
| **Demo / Retro** | Improvement proposals extracted | "Would you like to brainstorm solutions for the identified improvements?" → invoke `brainstorm-features` |
| **Any type** | Complex process discussed | "Would you like to visualize the discussed process as a diagram?" → invoke `diagram-prototyper` |

**Context to pass when invoking another skill:**

Every skill invocation from meeting-processor must include the **full participant context** and relevant meeting data:

| Context element | What to pass | Why |
|----------------|-------------|-----|
| **Participants** | Full list: name, email, role (from `team.members` match), attendance status (spoke / invited but silent / not invited but participated) | Feature-task-creator uses participants for task assignment; product-research uses for interview attribution; brainstorm-features uses for idea ownership |
| **Meeting metadata** | Title, date, duration, type(s), organizer, recurrence info | Context for all downstream skills |
| **Meeting source link** | Fireflies link, calendar event link, or file reference | For traceability in created documents |
| **Extracted content** | Depends on target skill (see table below) | Core input for the target skill |
| **Attached materials** | Links to agenda, pre-read docs, presentations found in calendar | Additional context for requirements, research, concepts |

**Content to pass per target skill:**

| Target skill | What to pass |
|-------------|-------------|
| **feature-task-creator** | Action items (who, what, deadline), task estimates, priorities, Epic reference if mentioned, participants with roles for task assignment |
| **requirements-creator** | Feature discussion fragments, functional requirements mentioned, user scenarios discussed, participants as stakeholders |
| **product-research** | User insights, quotes with speaker attribution, pain points, needs, participants as interview subjects |
| **brainstorm-features** | Ideas, hypotheses, evaluation criteria, voting results, participants as idea owners |
| **diagram-prototyper** | Process descriptions, flow logic, architecture discussed, participants as actors in diagrams |

If no chaining is relevant or the user declines — end the workflow gracefully.

---

## Mode: Search — Workflow

### S1 — Understand the query

Parse the user's request to determine:
- **What** they're looking for: topic, feature name, decision, person, action item
- **Time range**: "last month", "this sprint", "since January", specific dates
- **Participants**: specific people involved (optional)
- **Meeting type filter**: "in groomings", "in status meetings" (optional)

If the query is ambiguous — ask clarifying questions via AskUserQuestion.

### S2 — Search across meetings

**S2a. Determine available search sources:**

Check which meeting tool MCPs are connected:
- Fireflies MCP → use `fireflies_search` with keyword, date range, participants
- Other meeting MCPs → use their search APIs
- If no MCP connected → inform the user: "No meeting tool is connected. Would you like me to search the MCP registry for available meeting connectors?" Follow integration fallback chain

**S2b. Execute the search:**

- Use keyword search with the extracted topic/feature name
- Apply date range filters
- Apply participant filters if specified
- Limit to 10-20 most relevant results

**S2c. For each relevant meeting found:**

1. Read the summary via `fireflies_get_summary` (or equivalent)
2. Check if the meeting content matches the query — filter out false positives
3. Extract only the relevant fragments (not the entire transcript)

### S3 — Aggregate and synthesize

Compile results into a chronological synthesis:

```markdown
## Search Results — "[query]"

**Period:** [date range] | **Meetings found:** [N]

---

### Timeline

#### [Date] — [Meeting title]
**Participants:** [list]
**Relevant discussion:**
[Summary of what was discussed about the searched topic in this meeting]
**Decisions:** [if any decisions were made]
**Action items:** [if any action items related to the query]

#### [Date] — [Meeting title]
...

---

### Summary
[2-3 sentences synthesizing the overall trajectory: how the discussion evolved, what was decided over time, current status]

### All decisions on this topic
| # | Date | Decision | Meeting | Owner |
|---|------|----------|---------|-------|

### All action items on this topic
| # | Date | Action | Meeting | Owner | Status |
|---|------|--------|---------|-------|--------|
```

### S4 — Present results

Show the synthesis to the user. Offer follow-up actions:
- "Would you like to see the full transcript of any of these meetings?" → switch to Process mode for the selected meeting
- "Would you like to publish this summary?" → publish to Confluence/Notion
- "Would you like to create tasks from the action items?" → invoke feature-task-creator

---

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

---

## Quality standards

- Always confirm the selected meeting with the user before processing
- Match speaker names against `team.members` from `local-context.md` when possible
- Distinguish facts (what was explicitly said) from inferences (what the skill interpreted)
- Mark uncertain extractions: if unsure whether something is a decision vs. a suggestion — mark as "Possible decision (needs confirmation)" and ask the user
- Respect `user.language` for all output content
- Treat all meeting content as confidential — do not pass to external LLMs or third parties per `references/data-policy.md`
- For Confluence content rules: respect `local-context.md` content rules (e.g., ignore pages with `noindex` label when searching for context)
- Cross-reference Fireflies summary with actual transcript — Fireflies AI summaries may miss items or misattribute actions

## Additional Resources

- **`references/local-context-protocol.md`** — Step 0: how to read and use local-context.md (mandatory before any skill execution)
- **`references/integration-strategy.md`** — MCP → Registry → Browser fallback chain (shared across all skills)
- **`references/data-policy.md`** — data confidentiality policy: what data can and cannot be shared externally (mandatory reading before any data gathering)
- **`references/self-improvement.md`** — self-improvement protocol: how to learn from user corrections and improve skill algorithms
