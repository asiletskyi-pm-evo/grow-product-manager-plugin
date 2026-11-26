# pm-os-protocol.md

> Shared reference (profile `pm-os` of the app shell). The **pult** is one private app for a product manager's day: what needs them, the directions they lead, the numbers behind the goal, the freshness of their sources and the state of their context — for every product they work on, in one place. It is the profile `pm-os` of `references/app-profiles.yaml` on the app shell (`scripts/app_shell.py`); this file says which sections its modules read, what a section may hold, how a refresh run fills them, and the one standing consent under which a scheduled run may write the pult's data. Consumed by the skills that refresh the pult after their own work and by the step that sets it up.
>
> **Rule of the file:** the repository holds the profile, the section shapes and fictional fixtures only. Every value of a user — a product, a direction, an epic, a metric, a dashboard, a meeting — lives in their context store, their published page and its database, never in a file of the plugin (`testing/pm_os_test.py` checks the profile and the fixtures; `scripts/app_shell.py check` refuses a value in a profile).

## 1. What the pult is

- One app for all of the user's products. Every section document carries its product; the shell shows the product's mark on every card and row and a switch in the header. A thing with no product is shown under «Без продукту», never hidden.
- Five modules in v1, in the profile's order: `today` (home), `directions`, `metrics`, `rhythms`, `context`. Each is a composed module — several blocks, one under another, each reading one section (§2). The owner turns a module off, reorders the modules and adds their own from the ready blocks in `config/app` (the shell's rules; `app_shell.py check --config`).
- The page holds no data. Data arrives only through the database documents of §3, so a refresh never makes a new version of the page.
- The vault and the context store stay the source of truth. The pult is a render: nothing is ever read back from it into a note or a record without the user's own step.

## 2. Sections

A section's data has the shape of the block that shows it (the shell's blocks: `table` — `{columns: [{key, title}], rows: [{…, product?, attention?}]}`; `list` — `{items: [{title, note?, product?, attention?}]}`; `feed` — a list whose items carry `at`; `number` — `{value, unit?, delta?, trend?}`). `attention` is `ok`, `warn` or `crit`.

| Module | Section | Block | What it holds | Read from (by role, never by brand) |
|---|---|---|---|---|
| `today` | `needs-you` | feed | what waits for the user's answer: a mention, a review request, an invitation with a question, a letter that passed their own filter | issue tracker, code host, mail, calendar |
| `today` | `focus` | list | one to three focuses of the day | the daily focus of `focus-advisor` |
| `today` | `meetings` | list | today's meetings, in time order, each with the state of its preparation | calendar |
| `today` | `signals` | list | the metric rows of `metrics` that crossed a threshold, and the directions with stale work | the sections `metrics` and `directions` of the same run |
| `directions` | `directions` | table | a row per direction in work: its epic or release code, stage, share of closed work, open work, work with no movement for over 14 days | issue tracker (counts only), code host |
| `directions` | `directions-rest` | list | the directions on hold or closed, one line each | the same |
| `metrics` | `goal` | number | the top goal: the value now, its unit, the change | the user's tracker or dashboard |
| `metrics` | `metrics` | table | the second level under the goal: a row per stage and platform with the value, the change to the period before and the change year over year | the user's tracker or dashboard |
| `rhythms` | `rhythms` | table | a row per recurring source — a tracker, a board, a scheduled run — with the date of its last update and its age | the list of the user's published results, the schedule |
| `rhythms` | `runs-log` | feed | the last refresh runs of the pult: when, how many sections, what was skipped and why | the `runs` documents of §3 |
| `context` | `context-health` | number | how many records of the context store are stale | `ctx health` |
| `context` | `context-inbox` | list | the proposals waiting in the inbox, as questions | `ctx inbox list` |

Rules for every section:

1. **A source and a date.** A number carries where it came from and the date of that source in its `note` or its own column; a section whose source did not answer is not written in that run and keeps its last document, so the shell shows the older date.
2. **Thresholds are the user's.** `attention` for a metric row is `warn` at 10% and `crit` at 25% away from the baseline in the wrong direction unless the user's CJM configuration says otherwise; a direction is `warn` when it has work with no movement for over 14 days.
3. **No person.** A section never holds a person's name, e-mail or profile, an assignee, an author, or a count per person; `app_shell.py snapshot` drops the keys `email`, `e-mail`, `author`, `assignee`, `person`, `owner`, `reporter` at any depth, and the run does not put a name into a title or a note either. The People contour routes nothing here (`people-context-protocol.md`): in v1 the pult has no People module.
4. **A letter or a meeting is named without its people.** `needs-you` and `meetings` show a subject or a title only when it holds no person's name; otherwise the kind and the time («Лист, 09:40», «Зустріч, 11:00»).
5. **Counts, not content.** From the issue tracker a section takes counts and codes, never a description or a comment; from mail never a body.
6. **Text only.** No link, HTML or markup goes into a document: the shell shows every string as text, and a code (`PROJ-1234`) is enough for the shell's live status.

## 3. Where the data lives

- **Settings** — the record `pm-os` (type `setting`) in the context store: the products shown with their short labels and mark colours, the directions and their codes, the sources of the goal and of the second level, the refresh times, the modules turned on, and the standing consent of §5. It is written through `ctx`, with the store's own confirmation, and compiled into `local-context.md` like every record.
- **The page** — published once, at set-up, by the shell: `app_shell.py wrap --profile pm-os`. It starts private.
- **The data** — the database of that page, written by `app_shell.py snapshot --profile pm-os` as files and then sent as one batch: `snapshot/meta`, `snapshot/<section>--<product>`, `runs/<made>`. A section over the size limit is left out and named in the run's line.
- **The owner's layout** — `config/app` in the same database, written by the page itself when the owner changes it. A refresh run never writes it.

## 4. A refresh run

1. Read the record `pm-os`. Without it there is nothing to refresh: say so in one line and stop.
2. Check the consent of §5 when the run is scheduled. Without a valid consent the run follows `native-surfaces.md` §4: it builds the snapshot files, writes nothing to the database, and ends with the one line for the next interactive run.
3. For each section, read its source by role (`integration-strategy.md`), in the read-only way, and shape the data as §2 says. A source that does not answer: skip the section, note it for `runs-log`.
4. Build the documents: `app_shell.py snapshot --profile pm-os --product … --section … --out <scratch dir>`. A refusal (a wrong id, a weak theme) stops the run with the script's words.
5. Write the batch to the page's database. Interactive run — after the question of `native-surfaces.md` §3, as for every publication; scheduled run under §5 — without it.
6. One line at the end: how many sections were written, which were skipped and why.

A skill that already ran for its own reason (the daily focus, a CJM health-check) hands its result to step 3 instead of reading the source again.

## 5. The standing consent

The rule everywhere else is `data-policy.md` → Hosted surfaces: ask before every publication and every new version (rule 1), and a scheduled run never publishes (rule 3). For the pult alone the user may give one **standing consent**, because a board refreshed many times a day cannot ask each time. It is narrow on purpose:

1. **Asked once, at set-up, as its own question** — never folded into another, never assumed from a default. The question names what the runs will write (the sections of §2, by name), where (the pult's database), who can open it (the user alone), how often, and how to take the consent back.
2. **Only while the pult is private.** Before every write under the consent the run reads the page's audience from its publication record (`artifact-publishing.md` §5). Anything but `private` — `shared`, `unknown`, no record — and the consent does not apply: the run writes nothing and says why in its line. Sharing the pult ends the consent; a new one is not offered for a shared pult.
3. **Only the data documents** — `snapshot/*` and `runs/*` of the pult's own database. Never a new version of the page, never `config/app`, never another artifact, document, Jira or Confluence — those keep their question.
4. **Only a run on the user's machine** (SCHEDULE `local`, `native-surfaces.md` §1), as every recurring run of the plugin.
5. **Every write is in the journal.** Each run writes its `runs/<made>` document; the module `rhythms` shows the last ones, so the user sees what was written and when.
6. **Taken back in one step.** «Відклич згоду на пульт» — or the same from the pult — clears it in the record `pm-os`; from the next run on §4 step 2 applies. Nothing already written is removed without the user's own word.
7. **Recorded with its date** in the record `pm-os` (`consent: {given: <date>, scope: snapshot}`), and void after any change of the profile's sections that adds a kind of data the question did not name: the set-up step asks again.

## 6. When something is absent

| Absent | The pult |
|---|---|
| ARTIFACT `typed` with a database | not offered; the run's result is the snapshot files and a table in the chat |
| SCHEDULE `local` | refreshed only by an interactive run; one line says where to create the schedule (`native-surfaces.md` §5) |
| a source of a section | the section keeps its last document and its date; `runs-log` names the source |
| the context store | set-up stops: the pult's settings are a record of the store |
| the desktop app of the host | the page works in a browser, without the window, the tray and the notifications |
