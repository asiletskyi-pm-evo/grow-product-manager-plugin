# native-surfaces.md

> Shared reference (since v4.1.0). A host can show or keep a result in more places than a file: a typed page, a live document, a visual inside the conversation, a run on a schedule, a built-in research pass. This file says how a skill recognises each of these **surfaces**, which result goes where, what it asks before anything leaves the session, and what it does when the surface is absent. Consumed by `host-profiles.md` §1–§3 (the five capabilities are marked in Step 0-host) and by every skill that shows, publishes or schedules a result.
>
> **Rule of the file:** the same as `host-profiles.md` — branch on an **observed capability**, never on a brand. This file and `host-profiles.md` are the only two places where a surface is named by its brand or tool (§6); a skill names the capability (`skill_lint.py` check 30).

## 1. The five surface capabilities

| Capability | Present when the session has… | Levels | Does not count |
|---|---|---|---|
| **ARTIFACT** | a tool that publishes a page and returns a link the user opens | `typed` — the tool has kinds (document, deck, dashboard, design), and a page may re-query the connectors when it is opened; `page` — a plain hosted page or site | a file on disk, even an HTML one |
| **DOCS** | a tool that creates a document the user and the agent both edit, and returns its link | `native` — the host's own documents; `connector` — through a connector (a Docs-like service the user connected) | a generator of `.docx` / `.pptx` / `.xlsx` — that is a file |
| **WIDGET** | **the host's own** tool that renders a visual (chart, diagram, small interactive view) **inside the conversation** | — | an HTML file the user has to open; a **third-party app or connector** that draws a visual, even one that calls itself an inline widget (a mind-map app) — the data would go to that app's service (`data-policy.md`, third-party sharing); any visual tool in a terminal session (a CLI, a non-interactive `exec` run) — a terminal shows no widget |
| **SCHEDULE** | a tool with which **the agent** creates a recurring run of a prompt or a skill | `local` — the run happens on the user's machine and reads their files, and it outlives the session; `session` — it lives only while this session runs; `remote` — a cloud run without the user's files | a schedule only the user can create in the host's interface: then the skill says in one line where to create it (§5) |
| **RESEARCH** | a built-in multi-source research tool or skill that runs inside the session and returns its sources | — | plain web search; an external LLM reached through a browser (that is `product-research`'s ChatGPT / Gemini path, `data-policy.md` Deep Research) |

Mark them in Step 0-host together with the other six (`host-profiles.md` §3), once per run. A skill marks only the ones its own steps use (§2 says which).

**The plugin's recurring runs need SCHEDULE `local`.** Every one of them reads or writes `~/.grow-pm/` or the vault (`host-profiles.md` §5), and the People-contour ones read person profiles that never leave the machine (`people-context-protocol.md`). A `session` schedule dies with the session, and a `remote` run has no access to the user's files — neither is offered for them; without `local` the skill says in one line where to create the run (§5).

## 2. Routing — which result goes where

| Result | First choice | Next | Without any |
|---|---|---|---|
| A chart, a trend, a comparison shown while working (`product-analysis`) | WIDGET | — | a table in the report, as before v4.1.0 |
| The Focus Board (`focus-advisor` Step 7b) | WIDGET, with no question | ARTIFACT `typed` — only on the user's request or when a live board already exists, asked before **every** create and refresh (§3) | the static `~/.grow-pm/focus/board.html` |
| A report the user will read and edit (`product-reporter` Step 6) | offered as one of the outputs: DOCS, Confluence, local files — each after §3 | — | Confluence / local files, as before v4.1.0 |
| Any other publication of a skill's result — Confluence, Notion, Google Docs, a whiteboard, a design file, a live dashboard | after §3, every time | — | the local file |
| A recurring run (`cjm-research` health-check, `focus-advisor` briefs, `knowledge-library` Verify, `experiment-tracker` stale-check, `feedback-triage`, `one-on-one` coverage, `project-planning` replan, the configurator's scheduled briefs) | SCHEDULE `local` — the run follows §4 | — | one line where to create it (§5) |
| An enrichment pass over public sources (`product-research` Step 1–2) | RESEARCH, first, with no question of its own — it runs in the session | the external LLMs, each asked about as before | web search and the skill's other sources |

The vault copy stays the source of truth in every row: a widget shows, a live document or a page is one more place the user reads it, never the only one.

## 3. The question before anything is published

**Rule (decided by the user, v4.1.0): always ask.** Before every publication of internal data to a hosted surface — ARTIFACT of either level, DOCS of either level, Confluence, Notion, a whiteboard, a design file — the skill asks, and it asks again before a **new version** of the same artifact (an update, a refresh, a re-publish). The rule is the policy's (`data-policy.md` → Hosted surfaces); this section is its wording.

One question, in the user's language, naming three things:

1. **what** goes — the kind of result and the internal data it holds (metrics, Jira or Confluence content, research findings, calendar events);
2. **where** — the surface and the account or space it lives in;
3. **who can open it** — said as it is for that place: a page or a document in the user's own account is theirs alone until they share it; a document in a shared drive or folder is open to everyone who can open that folder; a Confluence page is open to everyone who can read its space; an artifact already shared is open to everyone it is shared with, and a refresh reaches all of them. When the skill cannot know whether it was shared, say both: «бачиш ти і ті, з ким ти вже поділився».

> «Опублікувати звіт спринту (внутрішні дані: задачі й SP з Jira) як живий документ у твоєму акаунті? Бачитимеш лише ти, поки не поділишся. Так / ні.»
> «Опублікувати звіт у Confluence, простір ZORG (внутрішні дані: задачі й SP з Jira)? Сторінку бачитимуть усі, хто читає цей простір. Так / ні.»

- **An existing «where to?» question counts.** When a step already asks where the result goes (`product-reporter` Step 6, a skill's publishing question) and that question names the internal data and who can open each place, it is this question — the skill does not ask twice.
- **Sharing is a separate question** — to whom, by name or group — asked after the publication of a page or document that starts private. A place that is open to a team from the start (a Confluence space) has no such step: its audience is named in the question itself.
- **A person's profile is never published** to a hosted surface, whatever the answer (`people-context-protocol.md`). People-contour skills route nothing here.
- **«Ні» is final for the run**: the result stays where the vault copy is, and the skill does not ask again in the same run.
- A WIDGET is not a publication — it stays in the conversation — and needs no question.
- **Before a Jira or Confluence write** this question and the skill's write checklist (`artifact-style-gate.md` → Host write gate) are **one message**, not two; the host gate, where it fires, asks once more — a second check, never a replacement.

## 4. A scheduled run never publishes

A run started by SCHEDULE has no one to answer §3. So it:

- writes its result to the vault or a file, as the skill's save step says;
- never creates or updates an ARTIFACT, a DOCS document, a Confluence page, a Notion page or a Jira issue (`focus-advisor` headless: «no side-effect actions at all»), whatever destination its prompt or a default names;
- ends with one line for the next interactive run: «Новий результат від <дата> — опублікувати можна в наступному прогоні.»

Setting the schedule up is an interactive step: the skill says what will run, how often and where its result will go (the vault or a file, never a hosted surface), and creates it on the user's «так».

## 5. When the surface is absent

Say it once, at the start, in one line — the `host-profiles.md` §3 rule — and take the next column of §2:

> «Тут немає віджетів у розмові — графік буде таблицею у звіті.»
> «Запланувати запуск на цій машині звідси не можу — створи розклад у налаштуваннях хоста, промпт: `<skill> mode=… headless=true`.»

Never fail, never repeat the line at each step, and never ask the user which host they are on.

**No line for an addition.** A surface that only adds an option or a source — DOCS as one more place in a «where to?» question, RESEARCH as one more source — needs no line when it is absent: the option is not offered, the source is not listed, and nothing else changes.

## 6. Brand map — the only place a surface is named

What the plugin has seen under each capability, with where the fact comes from (**measured** — a tool call or the tool's own listing in a session, with the date; **tool text** — the tool's description as the host gave it in a session; **config** — the host's configuration files, not a run). A new tool that does the same job counts without a change here.

| Capability | Seen as |
|---|---|
| ARTIFACT `typed` | Claude Code (desktop and CLI): the `Artifact` tool with kinds document, slides, design, dashboard, design system (measured 2026-10-29). Cowork: `create_artifact` / `update_artifact` (used by the Focus Board since `focus-advisor` v0.3; not re-measured) |
| ARTIFACT `page` | Codex CLI: Sites through Apps — `sites_create_site`, `sites_deploy_private_site_version`, `sites_update_site_access` (measured 2026-10-29). The ChatGPT app: a «Sites» section in its sidebar (measured 2026-10-29) |
| DOCS `native` | Claude Code (desktop and CLI): the Claude Docs connector (measured 2026-10-29) |
| DOCS `connector` | Codex CLI: Google Drive through Apps — create and update Docs, Slides, Sheets (measured 2026-10-29) |
| WIDGET | Claude Code desktop: `show_widget` (measured 2026-10-29). The ChatGPT app: `genui.run` (the model listed it, 2026-10-29; rendering not checked). Codex: the `visualize` skill is installed (measured in the CLI, 2026-10-29); its own text says it renders inline HTML in the app — not measured there |
| SCHEDULE `local` | Claude Code desktop: the scheduled-tasks connector — tasks stored on the machine, run while the app is open, a missed one on the next launch (tool text, 2026-10-29) |
| SCHEDULE `session` | Claude Code: `CronCreate` — in memory only, gone when the session ends, a recurring job expires after 7 days (tool text, 2026-10-29) |
| SCHEDULE `remote` | Claude Code: the `schedule` skill and `RemoteTrigger` — cloud routines (tool text, 2026-10-29). Codex: `automation_update` of the app's tool server, disabled for the CLI (config; its level — `remote` or `local` — is assumed, not measured in the app) |
| — (SCHEDULE absent for the agent) | The ChatGPT app: a «Заплановано» section where the user creates tasks; the model has only `automations.peek` (measured 2026-10-29) |
| RESEARCH | Claude Code (desktop and CLI): the deep-research skill (measured 2026-10-29). Codex CLI: the same skill when a plugin that carries it is installed — it was on the measured machine (the model listed it, 2026-10-29); without one, web search only (`web.run`). The ChatGPT app: web search only (measured 2026-10-29) |

Not surfaces in this sense: document, presentation and spreadsheet **generators** (they write files), image generation, a browser or computer-use tool (that is APP-DRIVE, `app-drive-protocol.md`).

## 7. Measured per host

Measured 2026-10-29 (the «Поверхні» programme, design workspace). ✅ present · ⚠️ partly, as noted · ❌ absent · ? not measured.

| Capability | Claude Code desktop | Claude Code CLI 2.1.311 | Codex CLI 0.153.2 | ChatGPT desktop app |
|---|---|---|---|---|
| ARTIFACT | ✅ `typed` | ✅ `typed` | ⚠️ `page` (Sites through Apps) | ⚠️ `page` in the app's sidebar (Sites), not a tool of the chat |
| DOCS | ✅ `native` | ✅ `native` | ⚠️ `connector` (Google Drive) | ❌ — Documents / Presentations / Spreadsheets write files |
| WIDGET | ✅ | ❌ — the terminal renders none | ❌ — the terminal renders none | ✅ tool present; rendering not checked |
| SCHEDULE | ✅ `local` (+ `session`, `remote`) | ⚠️ `session` and `remote` only — no `local` | ❌ | ❌ for the agent (the user creates it in the app) |
| RESEARCH | ✅ | ✅ | ⚠️ only with a research skill installed (it was); else web search | ❌ — web search only |

Cowork and claude.ai web are not measured yet; ChatGPT on web and mobile neither. A cell changes only with a measurement on that host, with its date.
