# Search mode — Steps S1–S4

> Part of `meeting-processor`. Loaded on demand when Mode Selection picks **Search**. Mode selection, the Input Source Discovery trigger and the Process workflow stay in SKILL.md.

> **Subagent delegation (large fan-out).** When the query spans many meetings, delegate per `references/subagent-delegation.md`: split the meetings into batches, spawn subagents in parallel, each returns a compact structured result (per-meeting decisions / action items / relevant quotes + link), and the main agent aggregates (merge, dedupe, rank). Falls back to inline if subagents are unavailable.

## S1 — Understand the query

Parse the user's request to determine:
- **What** they're looking for: topic, feature name, decision, person, action item
- **Time range**: "last month", "this sprint", "since January", specific dates
- **Participants**: specific people involved (optional)
- **Meeting type filter**: "in groomings", "in status meetings" (optional)

If the query is ambiguous — ask clarifying questions via AskUserQuestion.

## S2 — Search across meetings

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

## S3 — Aggregate and synthesize

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

## S4 — Present results

Show the synthesis to the user. Offer follow-up actions:
- "Would you like to see the full transcript of any of these meetings?" → switch to Process mode for the selected meeting
- "Would you like to publish this summary?" → publish to Confluence/Notion
- "Would you like to create tasks from the action items?" → invoke task-creator
