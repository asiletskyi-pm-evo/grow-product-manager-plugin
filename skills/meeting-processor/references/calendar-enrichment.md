# Calendar enrichment — Step M1d (M1d-1 → M1d-5)

> Part of `meeting-processor`. Loaded on demand when the user agrees to pull context from the calendar event after Step M1. The offer itself, the skip-to-M2 rule and the rest of the Process workflow stay in SKILL.md.

(The offer below is asked from SKILL.md M1d; it is kept here verbatim for reference — do not ask it a second time.)

> "Would you like me to check the calendar for this meeting? I can get the participant list, agenda, attached documents, and any linked materials."

If the user agrees — proceed with calendar lookup. If the user declines — skip to M2.

**M1d-1. Detect available calendar connector:**

| Calendar | How to detect | MCP tools |
|----------|--------------|-----------|
| **Google Calendar** | A Google Calendar connector is present (its list/get event tools, e.g. `list_events` / `get_event`) | List events by date/title → read the matching event's details |
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
