---
name: meeting-processor
version: 0.17.0
description: Turn meeting transcripts, recordings or notes into decisions, ARCV action items and MoM. Not a 1-1 (one-on-one, redirected automatically), not a role debate (brainstorm-features). UA — «підсумуй зустріч», «action items», «розбери транскрипт зустрічі», «що обговорювали». EN — "summarize meeting", "meeting notes", "what was discussed", "action items", "MoM", or any pasted/uploaded transcript. Sources — Fireflies, other meeting tools via MCP, files, pasted text. Chains to task-creator, requirements-creator, product-research, brainstorm-features and decision-log.
---

# Meeting Processor

> **Path rule.** A bare `references/<file>.md` in this file is read from this skill's own `references/` if the file exists there, otherwise from the **shared** `references/` at the plugin root. Resolve the root as `${PLUGIN_ROOT}`, else `${CLAUDE_PLUGIN_ROOT}`, else the directory that contains `skills/`, found by walking up from this folder (`references/host-profiles.md` §6). Never continue without a protocol named here.

Process meetings from any source — Fireflies, other recording tools, uploaded files, or pasted text — to extract action items, decisions, and structured meeting reports. The skill classifies the meeting type, adapts the output format, and chains to other plugin skills for follow-up actions.

## Integration prerequisite

Before starting, read and follow the integration fallback chain in `references/integration-strategy.md`. This skill can use:

- **Fireflies MCP** — for searching, reading summaries, and transcripts from Fireflies.ai
- **Other meeting tool MCPs** — if the user has connected another meeting recording tool (Otter.ai, Grain, tl;dv, Zoom, Google Meet, etc.), discover and use its MCP connector
- **Google Calendar MCP** — for finding calendar events, extracting participants, attached documents, meeting links, and agenda
- **Microsoft Calendar MCP** — alternative calendar connector (Outlook / Microsoft 365). If Google Calendar MCP is not available — search MCP registry for Microsoft Calendar
- **Confluence** — for publishing meeting notes / MoM
- **Notion** — alternative publishing destination
- **Jira** — for creating action item tasks (via task-creator chaining)

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

> **Judgment contract (Step 0j).** Per `references/local-context-protocol.md` Step 0j and `references/pm-mental-model.md`: note this run's
> judgment points (score, rank, verdict, priority, ship/kill, debate question) internally, with no output. A principle acts only through
> a step that implements it — until one exists here, this skill's questions, gates and output stay exactly as they are.

## Step T — Template Resolution (MoM report only)

Follow `references/template-protocol.md`, but with meeting-specific semantics:

- `artifact_type: meeting-notes`
- `subtype`: **exactly the class Step M3 assigns** — one subtype per classifier row, no more:
  - Grooming / Planning → `grooming-planning`
  - Discovery / Interview → `discovery`
  - Demo / Retro → `demo-retro`
  - Status / Agreements → `status`
  - Brainstorm → `brainstorm`
  - (1-1 never reaches Step T — M3 redirects it to `one-on-one`, which owns its own artifact)
- `product_id`: from local-context.md active product
- `language`: from `user.language` in local-context.md

> This map must stay row-for-row with M3's classification table. Until v2.1.1 it offered `decision` and `review` subtypes and split grooming from planning — classes M3 cannot emit — so a user who registered a `meeting-notes/decision` template could never have it selected. If you want a new subtype here, add the classifier row in M3 first.

Run **Steps T-0 → T-5 exactly as `references/template-protocol.md` names them** (do not renumber locally):

- **T-0 (Declare context):** the fields above — so Step T runs after M3, whose classification produces `subtype`, and before M6.
- **T-1 (Load registry) + T-2 (Score and rank):** via `resolve({artifact_type: "meeting-notes", subtype, product_id, language})`.
- **T-3 (Decide):** per `templates.preference`.
- **T-4 (Collect variables):** from the Step M5 extraction.
- **T-5 (Render and record):** use the selected template as the MoM structure for Step M6 (Generate output); if nothing matched, use the built-in structure described in Step M4 per meeting type. When publishing to Confluence / Notion, append `<!-- template: {template_id} version: {version} -->` to the body.

**When to run Step T:** between Step M4 (Choose output format) and Step M5 (Extract content) — once meeting type is known, resolve the template so that Step M5 can collect variables that the template expects.

**Chained invocation (delegation pattern):** when the user routes the output to another skill (Step M9 — Skill chaining: e.g., "turn action items into Jira tasks" → `task-creator`, "write a concept from this discovery" → `write-concept`, "draft requirements from this spec meeting" → `requirements-creator`, "research these hypotheses" → `product-research`, "brainstorm this further" → `brainstorm-features`), **each downstream skill runs its OWN Step T** for its own artifact type. Meeting-processor's Step T is only for the MoM/meeting-notes artifact itself. Pass the raw extracted content to the downstream skill; do NOT pre-apply templates intended for downstream artifacts.

**Escape hatch:** if the user says "just a quick summary" or "plain notes, no template", skip Step T and use a lightweight bullet-list output.

**Fallback** (when registry returns no match for any meeting subtype): use the built-in structure for that meeting type described in Step M4.

**Judgment footer (since v3.5.0).** The artifact closes with the altitude line from `templates/built-in/partial/judgment-footer-v1.md` (`references/template-protocol.md` T-5 step 3a; checked by `references/artifact-style-gate.md` Gate 4a) — a meeting classified as 1-1 carries none, even when the user keeps it here.

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

After determining the meeting source, **ask the user if they want to pull additional context from the calendar event:** "Would you like me to check the calendar for this meeting? I can get the participant list, agenda, attached documents, and any linked materials." If the user agrees — look up the matching Google / Microsoft Calendar event and merge it with the meeting data; if the user declines — skip to M2.

The full procedure — calendar connector detection (M1d-1), finding the event (M1d-2), the event-data table (M1d-3), reading attached materials (M1d-4) and merging calendar with transcript data (M1d-5) — lives in `references/calendar-enrichment.md` (skill-local). Read it when the user agrees to the calendar lookup.

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

If the source provides a pre-built summary (like Fireflies) — use it as a starting point but always cross-reference with the full transcript for completeness; since v3.8.0 it is never the source of a quote (Quality standards).

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
| **1-1** | "1-1", "one-on-one", "ван-он-ван", two participants (manager + one report) | Personal feedback, growth, motivation, career, "how are you", not tasks/status |

**1-1 detection → redirect.** If the meeting classifies as a **1-1** (two participants — a manager and a direct report — with feedback/growth/personal content rather than tasks/status), do **not** process it as a generic MoM. Offer to hand off to the dedicated skill:

> "This looks like a 1-1 meeting. The **one-on-one** skill analyzes it properly — extracting signals (motivation, burnout, career), writing an ARCV follow-up, and updating the person's profile (kept strictly local). Continue there?"

If the user accepts → invoke `one-on-one` (analyze mode), passing the transcript/notes. 1-1 content is People-data (`data-policy.md`) and must not be published to Confluence — one-on-one enforces this. If the user declines → proceed here but keep the output local.

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
- Look for language patterns: "we decided", "agreed to", "let's go with", "the decision is"
- For each decision: what was decided, context/rationale, who was responsible (if mentioned)
- Since v3.7.0, only when said in the meeting: the one accountable owner, options rejected and why, a dissent (who, what) and a revisit condition — they travel to `decision-log` as `owner`, `rejected_alternatives`, `minority_report`, `revisit_trigger` (`references/judgment-points.md` §4); never inferred, left out when not said. The MoM's Decisions table keeps its columns

**Action items (ARCV standard):**
- Extract tasks that someone committed to doing
- Look for language patterns: "I'll do", "take this", "action item", "TODO"
- Format every action item to the **ARCV** quality bar (`references/communication-frameworks.md`):
  - **A — Actions:** only items that must be *done*; each **numbered**; one item = one number.
  - **R — Responsible:** exactly **one** responsible person per action (two+ → the result may not happen).
  - **C — Clearly:** each item unambiguous — someone who wasn't in the meeting could execute it.
  - **V — Verbs:** start each with an **active perfective verb** + a deadline if relevant ("Olia will produce the doc by Apr 1", not "Doc — responsible: Olia").
- Cross-reference with Fireflies action_items if available — merge, don't duplicate
- Keep **Decisions separate from Actions** (see the Decisions block above): important agreements with no owner/action (e.g. "we stop the process if no 2 deals in 2 months") go under Decisions, not Action Items.

**Open questions:**
- Extract unresolved discussions, questions left without a clear answer
- Look for: "we need to figure out", "let's discuss later", "open question", "TBD"

**M5b. Type-specific blocks:**

Add the blocks specific to each type confirmed at M3: Grooming / Planning (estimates, priorities, assignments, blockers, sprint scope), Discovery / Interview (insights, quotes, pain points, needs / JTBD, opportunities), Demo / Retro (feature feedback, what went well / wrong, improvement proposals), Status / Agreements (progress, agreements, risks, blockers, deadlines), Brainstorm (ideas, evaluation, selected ideas, next steps).

The full per-type block tables — what to extract for each block — live in `references/meeting-type-blocks.md` (skill-local). Read it at M5 for every type the meeting was classified as.

### M6 — Generate output

**M6a. Structured MoM format:**

Generate the full MoM in `user.language`: header (date, duration, type), participants table with attendance status, topics discussed, decisions table, action-items table, the type-specific section(s) from M5b, and open questions.

The full procedure — the MoM markdown skeleton — lives in `references/mom-format.md` (skill-local). Read it whenever the Structured MoM format is chosen; a template selected at Step T takes precedence over the skeleton.

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

**Self-improvement check** (after corrections are applied and confirmed): follow `references/self-improvement.md` — analyze whether the correction is a pattern, and if so propose a SKILL.md improvement (version bump + CHANGELOG).

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
| **Grooming / Planning** | Action items with task assignments extracted | "Would you like to create Jira tasks for the discussed items? I'll pass the context to Task Creator." → invoke `task-creator` |
| **Discovery / Interview** | User insights and quotes extracted | "Would you like to synthesize these interview insights into a research report? I'll pass the context to Product Research." → invoke `product-research` |
| **Discovery / Interview** | Feature ideas or requirements discussed | "Would you like to write requirements based on the discussed feature? I'll pass the context to Requirements Creator." → invoke `requirements-creator` |
| **Brainstorm** | Ideas and hypotheses extracted | "Would you like to score and prioritize these ideas? I'll pass the context to Brainstorm Features." → invoke `brainstorm-features` |
| **Status / Agreements** | Agreements with deadlines | "Would you like to create Jira tasks for the agreed action items?" → invoke `task-creator` |
| **Demo / Retro** | Improvement proposals extracted | "Would you like to brainstorm solutions for the identified improvements?" → invoke `brainstorm-features` |
| **1-1** | Detected as a 1-1 (see M3) | "Analyze this as a 1-1 (signals + ARCV follow-up + profile update)?" → invoke `one-on-one` (analyze mode); keep output local |
| **Any type** | Complex process discussed | "Would you like to visualize the discussed process as a diagram?" → invoke `diagram-prototyper` |
| **Any type** | Decisions extracted (see M5a) | "Log these decisions so the 'why' survives?" → invoke `decision-log` (log mode) — see M10 |
| **Status / Decision** | Decisions that change quarterly scope or direction focuses | "These decisions change the quarter's focuses. Fold them into the quarterly plan?" → invoke `quarterly-planning` |

**Context to pass when invoking another skill:** every invocation carries the full participant context (name, email, role, attendance status), meeting metadata, the meeting source link, attached materials, and the extracted content the target skill needs.

The full procedure — the context-element table and the per-target-skill content table (task-creator, requirements-creator, product-research, brainstorm-features, diagram-prototyper, decision-log, quarterly-planning) — lives in `references/chaining.md` (skill-local). Read it before invoking any skill from the table above.

If no chaining is relevant or the user declines — end the workflow gracefully.

### M10 — Save to Vault (Optional)

> Requires: `references/vault-protocol.md` → Vault Save

IF vault_level > L0 AND vault sync_mode != "off":

1. `vault_save({ type: "meeting-notes", product: active_product, skill: "meeting-processor", skill_version: "0.17.0", tags: [meeting type (grooming/discovery/demo/status/brainstorm), topic keywords], content: structured notes or MoM from M6, related: [artifacts created via M9 chaining], extra_frontmatter: { meeting_date, participants, source (fireflies/upload/paste) } })`
2. Key decisions from the meeting may additionally be recorded as ADR-style records — offer, don't force: "The meeting produced N decisions. Log them in the decision log so the 'why' survives?" → invoke `decision-log` (log mode) once for the chosen decisions — one record per decision, and decision-log's own confidence question once for the whole batch (since v3.7.0) — passing per decision the decision-log row of `references/chaining.md`: what was decided, the context and options discussed, who decided, a link back to these notes, and the v3.7.0 fields only when said in the meeting, plus `evidence_classes` since v3.8.0. decision-log owns the `decision` artifact; do not hand-write `Decisions/` files here.
3. Display: "Saved to Vault: Meetings/{product}/…"

---

## Mode: Search — Workflow

Find what was discussed, decided or assigned about a topic across many meetings: parse the query — topic, time range, participants, meeting-type filter (S1); search the connected meeting tools and keep only the relevant fragments (S2); compile a chronological synthesis with all decisions and action items on the topic (S3); present it with follow-ups — Process mode for one meeting, publishing, or tasks via task-creator (S4). A query spanning many meetings delegates the per-meeting reads per `references/subagent-delegation.md`.

The full procedure — S1–S4, the search sources and filters (S2a–S2c), the synthesis template and the large-fan-out delegation rule — lives in `references/search-mode.md` (skill-local). Read it when Search mode is selected.

---

## Input Source Discovery Protocol

At the start of skill execution (before M1 or S1), if the user didn't explicitly specify a source: use an attached file if there is one; otherwise scan for connected meeting-tool MCPs and present the available sources (connected tools, file upload, pasted text), offering an MCP-registry search when no meeting tool is connected and the user expects one.

The full procedure — the discovery steps and the prompts to show — lives in `references/chaining.md` (skill-local). Read it when the user hasn't named a meeting source.

---

## Quality standards

- Always confirm the selected meeting with the user before processing
- Match speaker names against `team.members` from `local-context.md` when possible
- Distinguish facts (what was explicitly said) from inferences (what the skill interpreted). Since v3.8.0 (`references/pm-mental-model.md` §4) what was said — a figure too, even a dashboard number read out — is `reported` with its speaker: one artifact-level line `Evidence: reported — meeting <transcript | notes | recording> <date>` covers the MoM (`references/mom-format.md`; none on a 1-1), an item of another class (a linked artifact's label) keeps its own, and an inference is never presented as said — one that claims something nobody stated reads `[assumed — …]`
- Quotes are verbatim from the transcript (`fireflies_get_transcript`, the file or the pasted text), with speaker and timestamp where the source has them — never from an AI summary (`fireflies_get_summary`); a paraphrase loses its quote marks (`references/artifact-style-gate.md` Gate 4b)
- Mark uncertain extractions: if unsure whether something is a decision vs. a suggestion — mark as "Possible decision (needs confirmation)" and ask the user
- Respect `user.language` for all output content
- Treat all meeting content as confidential — do not pass to external LLMs or third parties per `references/data-policy.md`
- For Confluence content rules: respect `local-context.md` content rules (e.g., ignore pages with `noindex` label when searching for context)
- Cross-reference Fireflies summary with actual transcript — Fireflies AI summaries may miss items or misattribute actions
- **Lists over prose (opt-in gate):** topics, decisions, action items, and next steps are always lists/tables, never paragraph prose; for a MoM headed to Confluence you MAY run the full `references/artifact-style-gate.md` (maker–checker) before publishing — since v3.8.0 with both lenses, as its escalation rule requires for a publication: form (Gate 2) and groundedness (Gate 4b — verbatim quotes, `reported` labels)

## Additional Resources

- **`references/local-context-protocol.md`** — Step 0: how to read and use local-context.md (mandatory before any skill execution)
- **`references/integration-strategy.md`** — MCP → Registry → Browser fallback chain (shared across all skills)
- **`references/data-policy.md`** — data confidentiality policy: what data can and cannot be shared externally (mandatory reading before any data gathering); People-data tier for 1-1s
- **`references/communication-frameworks.md`** — ARCV follow-up standard (Actions/Responsible/Clearly/Verbs + Decisions block)
- **`references/self-improvement.md`** — self-improvement protocol: how to learn from user corrections and improve skill algorithms
- **`references/calendar-enrichment.md`** — M1d calendar enrichment: connector detection, event matching, event data, attached materials, merge rules (skill-local)
- **`references/meeting-type-blocks.md`** — M5b type-specific extraction blocks per meeting type (skill-local)
- **`references/mom-format.md`** — M6a Structured MoM skeleton (skill-local)
- **`references/chaining.md`** — M9 context to pass per target skill + Input Source Discovery Protocol (skill-local)
- **`references/search-mode.md`** — Search mode workflow S1–S4 with the fan-out delegation rule (skill-local)
- **`skills/one-on-one/SKILL.md`** — dedicated handler for 1-1 meetings (redirect target)
