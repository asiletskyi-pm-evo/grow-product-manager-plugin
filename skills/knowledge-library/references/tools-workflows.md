# Tools workflows — Scan, Add, Search, Manage, Export, Team

> Part of `knowledge-library` (since v0.10.0). Loaded on demand when entering a tools mode — read ONLY the workflow for the active mode. The record, what the scan may read, the suggestion other skills make and the team's list are the shared protocol `references/tool-registry.md`; the confidentiality rules are `references/data-policy.md` → Tools registry. Every command below is `python3 "<plugin root>/scripts/tools_scan.py" …` and ends with a `TOOLS_RESULT` line.

Step 0-host decides the path once: **SHELL** runs the script; without it the skill reads and writes `tools.md` by hand with the same fields and the same filters, and says so in one line. **FS** absent → the registry lives in the chat for the session (`references/tool-registry.md` §2).

## Tools Scan — «які інструменти в мене є», «просканируй мої інструменти»

**TS-1. Say what is read, in one line, and ask nothing** (the user decided: what is installed is a fact, v4.2.0):
> «Сканую лише назви: плагіни, скіли й MCP-сервери з файлів хостів на цій машині, цієї сесії та акаунта, плюс відомі застосунки. Значень із конфігів не читаю.»

**TS-2. The machine.** `scan > <scratch>/tools-scan.jsonl` (the session's scratch folder, never the store or the vault).

**TS-3. The session and the account** — what the script cannot see. Write one JSON line per name into `<scratch>/tools-observed.jsonl`:
- every MCP server whose tools are in this session's tool list — the `<server>` of `mcp__<server>__<tool>` — as `{"name": "<server>", "kind": "mcp", "state": "connected"}`; a server the host lists as waiting for authorisation → `"state": "needs-auth"`;
- every plugin and skill the session lists (a plugin from the `plugin:skill` prefix) → `"kind": "plugin"` / `"skill"`, `"state": "installed"`;
- the account's plugins and skills, when the session has a tool that lists them → `"source": "scan-account"`.

Names only — never a tool's arguments, results or descriptions beyond a short line.

**TS-4. Merge.** `merge --scan <scratch>/tools-scan.jsonl --observed <scratch>/tools-observed.jsonl`. The result names `records`, `created`, `state_changed` and the store.

**TS-5. Report in one message**: how many records by state (connected · needs-auth · installed · not-installed · not-seen), the new ones (name, kind, where seen), and what went `not-seen`. Then one line of next steps — mark what you recommend, share with the team (Tools Manage), find a tool for a job (Tools Search). No question.

**TS-6. Vault mirror** — the post-write sync of SKILL.md, the `tools/` lines.

## Tools Add — «додай інструмент», a site, a portal, a course, a colleague's tip

1. Ask, in one message, what the user did not already say: name, kind (`site`, `portal`, `course`, `cli`, `app`, `plugin`, `skill`, `mcp`), the job, how to connect, access, and who recommended it (`я` or a name).
2. `add --name "<name>" --kind <kind> job=… connect=… access=… skills=… recommended_by=…`. A refusal by the never-store filter names the field and the kind — ask for the line without the key; never repeat the value.
3. Mirror (TS-6).

## Tools Search — «знайди інструмент для …» (on request only)

1. Turn the request into 2–4 **public** keywords (`data-policy.md`: the search leaves the session) — the job, not the user's product, team or data.
2. Search the MCP registry (`references/integration-strategy.md` Step 2) and, when the session has a tool for it, the organisation's plugin catalogue. Show one list: name, what it does, connected or not.
3. The user picks → `add --name … --kind mcp|plugin --source registry-search|catalog job=…`. Nothing they did not pick is kept.
4. Connecting is the user's: offer the host's own connection card when it has one; never configure a server or a plugin yourself.

## Tools Manage — «покажи інструменти», «познач X як рекомендований», «знову пропонуй X»

- **Show:** `tools.md` — the user's records, then «Від команди».
- **Set:** `set --id <id> verdict=recommended|tried|deprecated`, `shared=true`, `recommended_by=…`, `job=…`, `connect=…`, `skills=a,b`, `notes=…`. An empty value removes the field. The scan never touches these.
- **A «ні» taken back:** `decline --skill <skill> --id <id> --undo`.
- Never delete a record; `deprecated` is how a tool leaves the suggestions.

## Tools Export — «поділитися інструментами з командою»

1. Only records with `shared: true` go out; if none, say so and offer Tools Manage.
2. `export` → the file in `export/`. Say in two lines what went out (names) and what never does (state, hosts, sources, declines, notes).
3. One line: «Передай файл власнику ядра (<owner_label>) — він кладе його в ядро і називає шлях у маніфесті ключем `tools_file`.» The plugin never writes into a core.

## Tools Team — «що використовує команда»

1. `team` — reads the `tools_file` of every core the user has registered, through the registrations `ctx` knows; a core without the key is skipped silently, one whose file is outside the core or unreadable is named in one line.
2. Show the «Від команди» records: name, job, who recommends. They are read-only.
3. «Взяти собі» → `add --from-team "<name>"` copies one into the user's registry.
