# pm-os-protocol.md

> Shared reference (profile `pm-os` of the app shell). The **pult** is one private app for a product manager's day: what needs them, the directions they lead, the numbers behind the goal, the freshness of their sources and the state of their context — for every product they work on, in one place. It is the profile `pm-os` of `references/app-profiles.yaml` on the app shell (`scripts/app_shell.py`); this file says which sections its modules read, what a section may hold, how a refresh run fills them, and the one standing consent under which a scheduled run may write the pult's data. Consumed by the skills that refresh the pult after their own work and by the step that sets it up.
>
> **Rule of the file:** the repository holds the profile, the section shapes and fictional fixtures only. Every value of a user — a product, a direction, an epic, a metric, a dashboard, a meeting — lives in their context store, their published page and its database, never in a file of the plugin (`testing/pm_os_test.py` checks the profile and the fixtures; `scripts/app_shell.py check` refuses a value in a profile).

## 1. What the pult is

- One app for all of the user's products. Every section document carries its product; the shell shows the product's mark on every card and row and a switch in the header. A thing with no product is shown under «Без продукту», never hidden.
- Five modules in the rail in v1, in the profile's order: `today` (home), `directions`, `metrics`, `rhythms`, `context`; the screen of one metric (`metric`) opens from the metrics module and stands under it, and the settings (`settings`) open from the rail's foot. Each is a composed module — several blocks, one under another, each reading one section (§2). The owner turns a module off, reorders the modules and adds their own from the ready blocks in `config/app` (the shell's rules; `app_shell.py check --config`).
- The page holds no data. Data arrives only through the database documents of §3, so a refresh never makes a new version of the page.
- The vault and the context store stay the source of truth. The pult is a render: nothing is ever read back from it into a note or a record without the user's own step.

## 2. Sections

A section's data has the shape of the block that shows it; `attention` is `ok`, `warn` or `crit`. The shell's blocks:

- `table` — `{columns: [{key, title, kind?, sub?, group?}], rows: [{…, product?, attention?, marks?}], note?}`. Columns that stand side by side with the same `group` get one shared head over them («Конверсія» over its two numbers). A column's `kind` is `num` (a number, set to the right), `segments` (the cell is a list of up to four parts of a whole; the column names them in `parts`, and `last: "warn"` paints the last part as the one that asks for attention) or `meter` (the cell is a number on the column's `scale`, with a mark at its `limit`); `sub` names the row's field shown as the small second line of the cell. A row's `marks` — `{<column key>: warn|crit}` — puts the mark of attention into that very cell; a table with such rows or with a drawn cell has no separate state column.
- `list` — `{items: [{title, note?, value?, product?, attention?}], note?}`; an item with a `value` is a pair row: the title at the left, the value at the right, in the colour of its `attention`, its `note` under both. `feed` — a list whose items carry `at` (a moment with its time is shown as this window's own date and time; in the rail a moment of today shows its time alone).
- `number` — `{value, unit?, label?, delta?, trend?, note?}` (a value of five digits and more is written with its thousands apart); with a `title` it is the band of a goal, and stands with its `note` even while the goal has no value yet.
- `bars` — by `kind`: `compare` `{series: [up to three names], unit?, rows: [{label, sub?, values}]}`; `delta`, a change from zero, `{unit?, ref?, refLabel?, scale?, groups: [{title?, rows: [{label, value, attention?}]}]}`; `columns`, one column per period, `{unit?, cols: [{label, value, partial?}]}`. `digits` (0–3) is the number of decimals a `compare` or a `delta` writes its values with.
- `line` — `{x: [period labels], series: [{name?, values}], unit?, partial?}`: one to four series from zero; `partial: true` says the last period is still running (one line draws it dashed with a hollow point, several lines leave it out and say so).
- `day` — `{date, start, end, items: [{from, to, title, note?, kind?}]}`: a day as a strip of time and its rows; `kind: "focus"` is time kept free of meetings; the mark «Зараз» is this window's own clock, shown only on the day of `date`, and the row that is running says how much of it is left.
- `lead` — one sentence over the module. Under the home module it reads the source `@summary`: the shell counts it from the home module itself — how many rows wait in `needs-you`, how many rows of `signals` ask for attention (the first block of the side column; the sources' freshness beside it is not counted twice), and what the calendar of `meetings` says of this very minute («Зараз час фокусу, до 15:00.», «Далі за календарем о 11:00.») — and no document holds its text. Under any other module it reads a section `{text}`: the run's own sentence about that module, one per product, shown together.

A chart takes a `headline` (what the chart shows, in a sentence), a `sub` (what is measured) and a `note` (the source and its date). Any section's document may also carry three short strings for the head of its section in the rail: `heading` — the name of what it shows («Конверсія в замовлення»), used in place of the block's general title while one document is shown; `side` — the words at the right of the head («останні 4 тижні», «3 напрямки»); `source` — the source's name, shown there with the time the section was read («календар, 13:11») when there is no `side`. A section that has nothing to show yet may say why in its own words: `{empty: "<one sentence>"}` — the shell shows that sentence in place of the block, and a `needs-you` document that only explains itself is not counted as «nothing waits». A chart block with no document takes no room at all.

| Module | Section | Block | What it holds | Read from (by role, never by brand) |
|---|---|---|---|---|
| `today` | `@summary` | lead | the state of the pult in one sentence, counted by the shell | the modules below, nothing else |
| `today` | `needs-you` | feed | what waits for the user's answer: a mention, a review request, an invitation with a question, a letter that passed their own filter | issue tracker, code host, mail, calendar |
| `today` | `meetings` | day | today's meetings and the time kept for focus, on a strip from the start to the end of the working day, each row with the state of its preparation | calendar |
| `today` | `focus` | list | one to three focuses of the day | the daily focus of `focus-advisor` |
| `today` | `signals` | list | the metric rows of `metrics` that crossed a threshold and the directions with stale work, each row naming its product; shown in the side column | the sections `metrics` and `directions` of the same run |
| `today` | `sources` | list | a pair row per source the pult reads: its name and when it was last read, a source past its age marked; under the signals in the side column | the run's own reading times, the section `rhythms` |
| `directions` | `directions-lead` | lead | the module's sentence: how many directions are in work and how many of them stalled | the section `directions` of the same run |
| `directions` | `directions` | table | a row per direction in work: its epic or release code, stage, the closed, open and stale work as parts of one bar, open work as a number | issue tracker (counts only), code host |
| `directions` | `directions-rest` | list | the directions on hold or closed, a pair row each: the name, then the code and the state | the same |
| `metrics` | `metrics-lead` | lead | the module's sentence: what the numbers below are measured against | the sections below |
| `metrics` | `goal` | number | the top goal: its name, the value now, what the value counts, the change | the user's tracker or dashboard |
| `metrics` | `metrics-change` | bars | the change of the second-level metrics to their baseline, from zero, with the attention threshold as a line | the same rows as `metrics` |
| `metrics` | `metrics-compare` | bars | the same metric side by side across platforms or segments | the same rows as `metrics` |
| `metrics` | `metrics` | table | the second level under the goal: a row per platform or stage with the value, the change to the period before and the change year over year | the user's tracker or dashboard |
| `metrics` | `metrics-pace` | number | a pace as one number — releases in 30 days — with what it counts | code host, the user's dashboard |
| `metrics` | `metrics-periods` | bars | a count per period — releases by week, orders by day — as columns | the user's dashboard, code host |
| `metric` | `metric-lead` | lead | the screen of one metric: its name as the document's `heading` (the screen's own heading), and a sentence on what it measures and where it went | the user's dashboard |
| `metric` | `metric-value` | number | the last full period as one number with what it counts; `heading` and `side` name the section it shares with the line («Замовлення за тижнями», «8 тижнів») | the same |
| `metric` | `metrics-trend` | line | the metric over time, by week or by day, beside its number | the same |
| `metric` | `metric-split` | line | the same metric by segment — a platform, a stage — up to four lines; while the source gives no split, its `empty` sentence says why | the same |
| `metric` | `metric-periods` | table | the last periods as rows: the period, the value, the change to the period before | the same |
| `rhythms` | `rhythms-lead` | lead | the module's sentence: how many sources feed the pult and how many are past their age | the section `rhythms` of the same run |
| `rhythms` | `rhythms` | table | a row per recurring source — a tracker, a board, a scheduled run — with the date of its last update and its age on a scale with the limit marked | the list of the user's published results, the schedule |
| `rhythms` | `runs-log` | feed | the last refresh runs of the pult: when, which sections of which product, what was skipped and why | the `runs` documents of §3 |
| `context` | `context-lead` | lead | the module's sentence: what of the context store is shown here | `ctx health`, `ctx inbox list` |
| `context` | `context-inbox` | list | the proposals waiting in the inbox, as questions | `ctx inbox list` |
| `context` | `context-health` | number | how many records of the context store are stale | `ctx health` |
| `settings` | `settings-lead` | lead | the settings' sentence | the record `pm-os` |
| `settings` | `@modules` | list | a switch per module of the rail, with what the module shows; the home module is always on | the profile and the owner's `config/app`, nothing else |
| `settings` | `@theme` | list | the shell's theme switch: as the system, light, dark | this window's own choice |
| `settings` | `settings-products` | list | a row per product: its name, its mark and where the mark's colour came from; beside the switches | the record `pm-os` |
| `settings` | `settings-refresh` | list | two pair rows — the standing consent of §5 with its date and limits, the schedule and whether it runs — and the phrase that takes the consent back | the record `pm-os`, the schedule |

One more section is read by no block: `refresh-note` — `{text}`, the run's own sentence on when the next data comes («Наступне оновлення на твоє прохання.»). The rail's foot shows it after the time of the data (`refresh.source` in the profile).

The pult's profile asks for the side rail (`layout: rail` in `references/app-profiles.yaml`), and in the rail a module is composed as its design draws it:

- **A section per block, the products together.** The rows of a `table`, a `list` or a `feed` from the products shown stand in one section under one head; a table merges only while its columns agree. A row shows the product it names in its own `product` field and no other: a row of one product's own section needs none, a row of a shared list (`signals`) names it.
- **A group.** The blocks of a module that share a `group` in the profile stand side by side in one section per product — the two charts of `metrics-change` and `metrics-compare` over the table of `metrics`, the number of `metrics-pace` beside the columns of `metrics-periods`. The section is named by its documents' `heading`, else by the group's first titled block, with the product and the `side` at the right. A chart whose group shows the table beside it does not fold the same numbers under itself.
- **A screen under a module.** `metric` names `under: metrics`: it has no entry in the rail, the metrics module ends with a row that opens it («Докладніше», named by the `heading` of the screen's first section), and the screen starts with the way back («Усі метрики»). A row of `signals` may name the module it speaks of in `module`; when every row asking for attention names one, the day's sentence says where the signals are («Є два сигнали: у метриках і в напрямках») in the words the modules give it (`where`).
- **A phrase for Claude.** A page cannot start a run of Claude, so a button that needs one — «Оновити зараз» in the rail's foot, «Задати базу» in the band of a goal with no value, «Відкликати згоду» under the data's updates — copies the profile's own phrase («Онови пульт») and says where to paste it; where the page may not copy, it says the phrase. The phrases are the profile's (`ask`, `refresh`), never a document's. A refresh in one click arrives with the commands of the user's machine, after v4.13.1.
- **The settings.** They open from the rail's foot and show every product whatever the product switch says. A switch writes `config/app` from the page — `{v: 1, modules: [{id, on, order?}], custom}`, the custom modules as they were read — on the owner's own click and nobody else's: the switches are closed for a viewer the platform says is not the owner, and a write the database refuses closes them with one line of why. The theme switch stands in the settings only.
- **What says nothing takes no room.** A block whose documents draw nothing and carry no `empty` sentence is left out with its head; a section moved elsewhere is overwritten with a document that draws nothing, never deleted by a run.
- **The rail itself.** The home module's entry counts the rows that wait; every other entry counts its rows asking for attention in the module's own word (`counts` in the profile: «1 застиг», «2 сигнали»); the foot says the time of the data; a row with nothing to say of its state reads «За планом». `signals` and `sources` stand beside the home module (`place: aside`), and the header carries the plugin's own mark (`icon.image: plugin`), which is the installed app's icon as well.

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
4. Build the documents: `app_shell.py snapshot --profile pm-os --product … --section … --prev-meta <the current snapshot/meta> --out <scratch dir>`. `--prev-meta` keeps the dates of the sections this run did not write, so a skipped section still shows the date of its last document; without it a partial run would drop them. A refusal (a wrong id, a weak theme) stops the run with the script's words.
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
