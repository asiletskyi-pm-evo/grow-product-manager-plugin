# native-surfaces.md

> Shared reference (since v4.1.0). A host can show or keep a result in more places than a file: a typed page, a live document, a visual inside the conversation, a run on a schedule, a built-in research pass. This file says how a skill recognises each of these **surfaces**, which result goes where, what it asks before anything leaves the session, and what it does when the surface is absent. Consumed by `host-profiles.md` §1–§3 (the five capabilities are marked in Step 0-host) and by the skills that route a result: `focus-advisor`, `product-analysis`, `cjm-research`, `product-research`, `product-reporter`, and every skill that sets up a recurring run.
>
> **Rule of the file:** the same as `host-profiles.md` — branch on an **observed capability**, never on a brand. This file and `host-profiles.md` are the only two places where a surface is named by its brand or tool (§6); a skill names the capability (`skill_lint.py` check 30).

## 1. The five surface capabilities

| Capability | Present when the session has… | Levels | Does not count |
|---|---|---|---|
| **ARTIFACT** | a tool that publishes a page and returns a link the user opens | `typed` — the tool has kinds (document, deck, dashboard, design); `page` — a plain hosted page or site | a file on disk, even an HTML one |
| **DOCS** | a tool that creates a document the user and the agent both edit, and returns its link | `native` — the host's own documents; `connector` — through a connector (a Docs-like service the user connected) | a generator of `.docx` / `.pptx` / `.xlsx` — that is a file |
| **WIDGET** | a tool that renders a visual (chart, diagram, small interactive view) **inside the conversation** | — | an HTML file the user has to open |
| **SCHEDULE** | a tool with which **the agent** creates a recurring run of a prompt or a skill | — | a schedule only the user can create in the host's interface: then the skill says in one line where to create it (§5) |
| **RESEARCH** | a built-in multi-source research tool or skill that runs inside the session and returns its sources | — | plain web search; an external LLM reached through a browser (that is `product-research`'s ChatGPT / Gemini path, `data-policy.md` Deep Research) |

Mark them in Step 0-host together with the other six (`host-profiles.md` §3), once per run. A skill marks only the ones its own steps use (§2 says which).

## 2. Routing — which result goes where

| Result | First choice | Next | Without any |
|---|---|---|---|
| A chart, a trend, a comparison shown while working (`product-analysis`) | WIDGET | — | a table in the report, as before v4.1.0 |
| The Focus Board (`focus-advisor` Step 7b) | WIDGET, with no question | ARTIFACT `typed` — only on the user's request or when a live board already exists, asked before **every** refresh (§3) | the static `~/.grow-pm/focus/board.html` |
| A report the user will read and edit (`product-reporter` Step 6) | offered as one of the outputs: DOCS (§3), Confluence, local files | — | Confluence / local files, as before v4.1.0 |
| A recurring run (`cjm-research` health-check, `focus-advisor` briefs, `knowledge-library` Verify, `experiment-tracker`, `feedback-triage`, `one-on-one` reminders, the configurator's scheduled briefs) | SCHEDULE — the run follows §4 | — | one line where to create it (§5) |
| An enrichment pass over public sources (`product-research` Step 1–2) | RESEARCH, first, with no question of its own — it runs in the session | the external LLMs, each asked about as before | web search and the skill's other sources |

The vault copy stays the source of truth in every row: a widget shows, a live document or a page is one more place the user reads it, never the only one.

## 3. The question before anything is published

**Rule (decided by the user, v4.1.0): always ask.** Before every publication of internal data to a hosted surface — ARTIFACT of either level, DOCS of either level, Confluence, a whiteboard, a design file — the skill asks, and it asks again before a **new version** of the same artifact. The rule is the policy's (`data-policy.md` → Hosted surfaces); this section is its wording.

One question, in the user's language, naming three things:

1. **what** goes — the kind of result and whether it holds internal data (metrics, Jira or Confluence content, research findings);
2. **where** — the surface and the account it lives in;
3. **who sees it** — the user alone until they share it.

> «Опублікувати звіт спринту (внутрішні дані: задачі й SP з Jira) як живий документ у твоєму акаунті Claude? Бачитимеш лише ти, поки не поділишся. Так / ні.»

- **An existing «where to?» question counts.** When a step already asks where the result goes (`product-reporter` Step 6) and that question names the surface and says the result holds internal data, it is this question — the skill does not ask twice.
- **Sharing is a separate question** — to whom, by name or group — asked after the publication, never folded into it.
- **A person's profile is never published** to a hosted surface, whatever the answer (`people-context-protocol.md`). People-contour skills route nothing here.
- **«Ні» is final for the run**: the result stays where the vault copy is, and the skill does not ask again in the same run.
- A WIDGET is not a publication — it stays in the conversation — and needs no question.

## 4. A scheduled run never publishes

A run started by SCHEDULE has no one to answer §3. So it:

- writes its result to the vault or a file, as the skill's save step says;
- never creates or updates an ARTIFACT, a DOCS document, a Confluence page or a Jira issue (`focus-advisor` headless: «no side-effect actions at all»);
- ends with one line for the next interactive run: «Новий результат від <дата> — опублікувати можна в наступному прогоні.»

Setting the schedule up is an interactive step: the skill says what will run, how often and where its result will go, and creates it on the user's «так».

## 5. When the surface is absent

Say it once, at the start, in one line — the `host-profiles.md` §3 rule — and take the next column of §2:

> «Тут немає віджетів у розмові — графік буде таблицею у звіті.»
> «Запланувати запуск звідси не можу — створи розклад у налаштуваннях хоста, промпт: `<skill> mode=… headless=true`.»

Never fail, never repeat the line at each step, and never ask the user which host they are on.

## 6. Brand map — the only place a surface is named

What the plugin has seen under each capability. A new tool that does the same job counts without a change here; this table only helps recognise the known ones.

| Capability | Seen as |
|---|---|
| ARTIFACT `typed` | Claude: the `Artifact` tool (kinds: document, slides, design, dashboard, design system); Cowork: `create_artifact` / `update_artifact` (the Focus Board since `focus-advisor` v0.3) |
| ARTIFACT `page` | Codex / ChatGPT: Sites (`sites_create_site`, `sites_deploy_private_site_version`, `sites_update_site_access` through Apps; a «Sites» section in the ChatGPT app) |
| DOCS `native` | Claude: the Claude Docs connector |
| DOCS `connector` | Codex / ChatGPT: Google Drive through Apps (create and update Docs, Slides, Sheets) |
| WIDGET | Claude: `show_widget`; ChatGPT app: `genui.run`; Codex app: the `visualize` skill (inline HTML, not rendered by the CLI) |
| SCHEDULE | Claude: the scheduled-tasks connector, `CronCreate`, the `schedule` skill; Codex app: `automation_update` (enabled in the app only). ChatGPT app: the «Заплановано» section — the user creates the task, the model only has `automations.peek`, so SCHEDULE is **absent** for the agent there |
| RESEARCH | Claude: the deep-research skill. Not seen on Codex CLI or the ChatGPT app — they have web search only (`web.run`) |

Not surfaces in this sense: document, presentation and spreadsheet **generators** (they write files), image generation, a browser or computer-use tool (that is APP-DRIVE, `app-drive-protocol.md`).

## 7. Measured per host

Measured 2026-10-29 (`plans/` of the «Поверхні» programme in the design workspace). ✅ present · ⚠️ partly, as noted · ❌ absent · ? not measured.

| Capability | Claude Code desktop | Codex CLI 0.153.2 | ChatGPT desktop app |
|---|---|---|---|
| ARTIFACT | ✅ `typed` | ⚠️ `page` (Sites through Apps) | ⚠️ `page` (Sites) |
| DOCS | ✅ `native` | ⚠️ `connector` (Google Drive) | ❌ — Documents / Presentations / Spreadsheets write files |
| WIDGET | ✅ | ❌ — the terminal renders none | ✅ tool present; rendering not checked |
| SCHEDULE | ✅ | ❌ | ❌ for the agent (the user creates it in the app) |
| RESEARCH | ✅ | ❌ — web search only | ❌ — web search only |

Claude Code CLI, Cowork and claude.ai web are not measured yet; ChatGPT on web and mobile neither. A cell changes only with a measurement on that host, with its date.
