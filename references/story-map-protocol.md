# story-map-protocol.md

> Shared reference (since v4.6.0). The user story map: a backbone of what the user does, cards of value under it, and release slices across it — each slice with a measurable outcome and no date. The procedure of `roadmap-architect` mode `story-map` (Step 7); `project-planning` reads a map's slices as the milestones of an arc (§9).
>
> **Rule of the file:** the note in the vault is the source of truth (`native-surfaces.md` §2). The board and the progress dashboard are renders of it; what the team changes on the board comes back into the note only after a question (§8). Every publication and every new version goes through `artifact-publishing.md`, after its question. A card that goes to work becomes a feature by the `planning-core.md` convention, never a Jira issue of its own; its FE/BE tasks are `task-creator`'s, later, as today. A map has no dates.

## 1. The model

- **Backbone.** Activities — the big things the user does — from left to right in the order of the user's own story; under each activity its steps, left to right.
- **Body.** Cards under each step; the higher a card, the more important it is. A card is one value the user gets, in the user's words; a job story («Коли …, я хочу …, щоб …») is an optional wording, never required.
- **Slices.** Horizontal bands across the whole map. The first slice is the walking skeleton (the MVP): the thinnest path through every activity. Then R1, R2 … A card belongs to one slice or to none (the backlog under the last line).
- **An outcome per slice** — a metric and a target («частка замовлень у поштомат ≥ 15 % за 4 тижні після запуску»). Without one the outcome is `⚠️ TBD`, and the check says so (§3).
- **No dates.** A slice is an order of value, not a calendar. A date asked for goes to `project-planning`, which takes the slices as milestones (§9).
- **The level.** A card that goes to work becomes a feature (`planning-core.md` §1–§2) through §5; the work types inside it (FE, BE, QA …) stay below the map.

## 2. Inputs

Read in this order, each when it exists; several combine into one map:

1. **A concept note** (`write-concept`) — its sections give the activities, the steps and the first cards; source marker `концепт §<section>`.
2. **A requirements page** (`requirements-creator`) — every functional requirement traces to a card (marker `FR-<n>`, added to the card it belongs to); an FR no card carries is a gap (§4 «Розриви»).
3. **An existing epic** — its features by CQL (`planning-core.md` §2: label `feature`, name `{PROJ}-{epic}.{n} - …`) become cards with their codes in `feature` and the code as the source. A feature and a card from the concept that name the same value are one card — the build preview shows the match, the PM corrects it — never two cards for one feature.
4. **The conversation** — marker `зі слів PM`.

**Nothing is invented.** Every card carries its source marker. A step an input names with no card under it stays a gap row (`⚠️`, §4); an activity or a step no input names is not added. Card texts carry no person's name and no link.

## 3. Quality — one card, one value

Checked when the cards are built (Step 7b) and again before a slice is written (§5). The structural checks are `story_map.py check`; the semantic ones are the model's, by the text of the rule. **Every finding is a proposal — the PM decides.** Before a slice write the findings stand in the same confirmation message; they never block it.

| Finding | Who | What it is | Proposal |
|---|---|---|---|
| `two_values` | model | one card holds two values the user could get separately | split it into two cards under the same step |
| `edge_inline` | model | an edge case written inside another card | its own card under the same step, `edge_of` = the card; it may go to a later slice |
| `subitem` | script | a sub-item inside a card: a `<br>`, a `•`, or a `- ` item after `:` or `;` | the sub-item becomes its own card (with `edge_of` when it is an edge case) |
| `work_type` | script | a card named by a type of work — `FE`, `BE`, `QA`, `iOS`, `Android`, `Design`, `DevOps` before its text | the value behind it; the work is `task-creator`'s |
| `skeleton_gap` | script | an activity with no card in the first slice | the thinnest card of that activity into the first slice |
| `no_outcome` | script | a slice whose outcome is empty or `⚠️ TBD` | a metric and a target from the concept or the goal, else it stays `⚠️ TBD` |
| `no_step` | script | a card without its activity or step | place it |
| `no_source` | script | a card without a source marker | name the source, or drop the card |
| `duplicate_id` | script | two rows with one id | a new id for the later row |
| `edge_unknown` | script | `edge_of` names no card | fix the id |
| `edge_other_step` | script | an edge card under another step than its card | move it under its card's step |
| `unknown_slice` | script | a slice that `slices` does not declare | declare it, or fix the cell |
| `bad_code` | script | a feature or epic code that does not parse (`planning-core.md` §2) | fix the code |
| `empty_step` | script | a gap row: a step with no card yet | a card from the inputs, or the gap stays |

## 4. The note

`type: roadmap`, `subtype: story-map`, saved to `Roadmaps/{product}/` by the vault save (`vault-schema.md`); without a vault, a file in the workspace (`persistent-storage.md`). The file name is `story-map-<slug>`, the slug from the map's subject («parcel-locker»), and it never changes — the publication key is built from it (§7).

**Frontmatter** — the map's own fields, next to the vault's usual ones:

| Field | What |
|---|---|
| `product` | the product id from `local-context.md` |
| `epic` | the epic key the cards belong to unless their own `epic` cell says another |
| `slices` | the slices in order, a list of `slice` (a lower-case id: `mvp`, `r1` …) and `outcome` (a metric and a target, else `⚠️ TBD`); an optional `label` when the labeling convention of `local-context.md` names the slice label |
| `baseline` | written only by `story_map.py baseline`: a list of `slice`, `date` (YYYY-MM-DD) and `cards` (the ids in that slice at that moment) |
| `published` | the mirror of the publication record (`artifact-publishing.md` §5), written only by `publications.py` |

```yaml
type: roadmap
subtype: story-map
product: zorg
epic: PROJ-1234
slices:
  - slice: mvp
    outcome: "share of orders to a parcel locker >= 15% four weeks after launch"
  - slice: r1
    outcome: "⚠️ TBD"
baseline: []
```

**The cards — one markdown table** under the heading `## Мапа` (`## Map` in English), easy to edit in Obsidian and parsed by the script. The rows of a step, from top to bottom, are its order of importance; activities and steps keep the order of their first row. A header may be written in the note's language:

| Column | Ukrainian header | What |
|---|---|---|
| `id` | `id` | the card's id (`c1`, `c2` …): stable, never reused |
| `activity` | `діяльність` | the activity of the backbone |
| `step` | `крок` | the step under the activity |
| `card` | `картка` | the value in the user's words; empty or `⚠️ …` makes the row a gap — a step with no card yet |
| `slice` | `зріз` | a slice id of `slices`; empty = the backlog |
| `feature` | `фіча` | the feature code `{PROJ}-{epic}.{n}` once the card is linked (§5), else empty |
| `epic` | `епік` | the epic key when it is not the frontmatter's |
| `source` | `джерело` | `концепт §2`, `FR-4`, `PROJ-1234.3`, `зі слів PM`, `дошка команди 2026-11-12` |
| `edge_of` | `edge_of` | the id of the card this one is an edge case of |

Then two sections the skill writes and the PM may edit: **«Прогрес»** (§9) and **«Розриви»** — the gap rows, the FRs no card carries, the findings of §3 the PM kept. The judgment footer closes the note (`artifact-style-gate.md` Gate 4a) — on the note only, never on the board or the dashboard. A map renders no pre-mortem (`planning-core.md` §8).

## 5. A slice goes to work — one message, one «так»

1. **Check** — `story_map.py check` and the semantic pass (§3).
2. **Linked or new.** A card with a feature code is linked: nothing is written for it. A card without one is new.
3. **A stub for each new card** — a feature page `{PROJ}-{epic}.{n} - {card text}` (`planning-core.md` §2). `n` is the next free number under the epic by CQL (the pages labelled `feature` whose name starts with `{PROJ}-{epic}.`), then consecutive for the next stubs — never guessed: without Confluence the stubs show `n = ?` and nothing is written. Labels: `feature`, the team label, the slice label (`slice-<id>`, or the slice's `label`); a quarter label only when the PM names the quarter in this message — otherwise `audit` shows the gap later. The body: `Status: planned`, the card text, its source marker, the map note's name, the slice and its outcome.
4. **One message** names: the linked cards and the new stubs (names, labels); the findings of §3; the write checklist (`artifact-style-gate.md` → Host write gate); who reads the Confluence space (`native-surfaces.md` §3); and, for a card with no epic, the question which epic it goes to.
5. **One «так»** → `roadmap-architect` Step 4b writes the stubs, one page each, with no pre-mortem (a feature never gets one). A card still without an epic is not written. Then the new codes go into the cards' `feature` cells and `story_map.py baseline --slice <id>` records the slice's baseline (§9).
6. **A dry run** («сухий прогін») shows the same message and writes nothing to Confluence or Jira; the baseline is recorded only when the PM asks for it («зафіксуй базову лінію»).

FE/BE tasks come later from each feature's requirements through `task-creator`; the map never creates a Jira issue for a card. Progress comes from `product-reporter` `initiative-status` (§9).

## 6. Renders — one parse, two places

Both come from one `story_map.py parse` of the note; neither is edited by hand.

- **The HTML page** — `story_map.py render-html --note <note> --out <file> [--status <S.json>] [--lang uk|en]`: one self-contained page — the grid (activities and steps across, cards down), a band per slice with its outcome and progress, status colours when a status file is given, each card's source, the note's name and the status source and date at the top. No external request, no link (feature codes only, so no URL with credentials can get in), every text escaped, light theme. Always written next to the note; published as kind `dashboard` when the PM chooses it (§7).
- **The board** — kind `board`: a registry record with `board` in its `publishes` whose tools in this session create frames and stickies and update them by element id (an observed capability, never a brand; measured on Miro 2026-11-09). The model builds it from the parse — `layout` gives the columns and the cells of each band — following the connector's own authoring instructions (Miro: its composer skill, read before the first board): a row of activities, a row of steps under them, the cards as stickies under their step in their order, each slice a horizontal frame titled with its id and outcome, the backlog in a last frame. A sticky carries the card text and, once linked, its feature code on a second line — never the card id, a source, a name or a link.
- **Not a board.** A whiteboard tool that draws only diagrams — FigJam's diagram tool, Mermaid types only, measured 2026-11-09 — builds no card grid and is never a candidate; neither is a tool that cannot update an element by its id.
- **No board tool in the session** → the HTML file, and once per run the registry's one line (`tool-registry.md` §4: `tools_scan.py suggest --skill roadmap-architect --need board`).

## 7. Publication

Through `artifact-publishing.md`, never around it:

- **The key** — `roadmap-architect/<product>/story-map-<slug>`: one key, the board and the dashboard in one question. `publications.py find --key <key> --note <note>` runs first; a place found is offered as «нова версія N».
- **The order.** The map's primary kind is `board` (the team edits the map there): its candidates come first (`artifact-publishing.md` §3), then the dashboard's by audience, and «лише файл» always.
- **Who sees the board.** In the team's root folder of the board tool, a board may be visible to the team's members by that team's settings — not measured yet: the question says both («бачиш ти, а можливо — й учасники команди за її налаштуваннями») and the record keeps `audience: unknown`. In a space the PM names, its members see it: `shared`.
- **The record** after each place: `publications.py record --key <key> --note <note> --surface <registry id> --kind board --id <board id> --url <board link> [--audience unknown]`; the dashboard as `--kind dashboard` on its own surface.
- **The board's state** — after a board publication the skill reads the board back (§8) and keeps that as its last state.
- **A new version of the board** is an update of the same board by element ids, after §8 — never a new board unless the PM chooses one. **A new version of the dashboard** is the same place's next version (`artifact-publishing.md` §6).
- **Sharing** — to named people or groups only, a separate question after the publication (`artifact-publishing.md` §7).
- **The dashboard's live parts** only where the surface re-queries the connectors on open (`artifact-publishing.md` §9); anywhere else it is a snapshot with its date.
- A scheduled run never publishes, and a map has no scheduled refresh at all.

## 8. What the team changed on the board — only through a question

- **The state.** After every successful board publication the skill reads the board back — the connector's read tool over the map's area (`story_map.py board-diff --last <state>` prints that area as `scope`) — and saves it as `~/.grow-pm/story-maps/<key>.board.svg`. A create's or an update's own result is not enough: an update returns only the elements it touched (the connector's own spec). Card texts are internal data, so the state stays on this machine, like the vault.
- **Before a new version** the skill reads the board back the same way into a scratch file and runs `story_map.py board-diff --last <state> --now <read> --note <note>`: elements by their id — `changed` (text), `moved` (position or frame), `added` (on the board, not in the state), `removed`. Reading back is not a publication: the user's own connected tool, no question.
- **Nothing changed** → the version question of §7.
- **Something changed** → one question: «На дошці змінено N карток і додано M — забрати в мапу / перезаписати мої картки / нова дошка».
  - **«Забрати»** updates the note first, shown as a preview: changed texts into their cards; each added item a new card with source `дошка команди <date>`, under the step and in the slice its column and frame say; a moved card to its new step or slice; a card removed on the board marked in the preview, and dropped from the note only on the PM's word for that card. Then the board's new version is rendered from the note, and the team's items keep their ids.
  - **«Перезаписати мої картки»** gives the plugin's own cards the note's text; what the team added stays on the board untouched.
  - **«Нова дошка»** creates a new board (version 1, the old id to `replaced`); the old board stays as it is.
- **Never a deletion of what the team added.** Any deletion from the board is one item at a time, after its own «так».
- **No state** (another machine, a lost folder) → «Не можу сказати, що змінилось на дошці» → the same question with one more answer, «показати, що на дошці».

## 9. Progress and the baseline

- **The baseline** of a slice is recorded when the PM confirms its write (§5), or on «зафіксуй базову лінію»: `story_map.py baseline --note <note> --slice <id>` writes the `baseline` field alone, every other byte of the note as it was.
- **«Онови мапу».** For every epic of the map the skill runs `product-reporter` `initiative-status` with depth `feature`, normalizes each feature's status to the canons of `planning-core.md` §3 and writes them to a status file:

```json
{"source": "product-reporter initiative-status PROJ-1234, depth feature", "date": "2026-11-10",
 "features": {"PROJ-1234.1": "done", "PROJ-1234.2": "in_progress", "PROJ-1234.4": "blocked"}}
```

- `story_map.py progress --note <note> --status <S.json>` gives per slice: the spread of `done` / `in_progress` / `planned` / `blocked`, the % done, what is blocked, and against the baseline the cards added (+N, %), removed and moved between slices. A card's status is its feature's; a card without a feature is `planned`; a feature the status file does not name is `unknown` `⚠️`, never guessed.
- The note gets the section «Прогрес» with the date and the source; the HTML the same (`render-html --status`). No status data (no Jira) → no section and one line, never an invented status.
- **`project-planning`** takes a map note as its input: the slices are the milestones of the arc in their order, a slice's scope is its features (estimated as usual), and a card without a feature is «не оцінено» `⚠️` (`roadmap-artifacts.md` §3). The map gets no dates back.

## 10. The script

`scripts/story_map.py`, stdlib (Python 3.9). Every command ends with one `MAP_RESULT {json}` line; exit 0, 2 for a wrong argument or a note that does not parse, 1 when a file cannot be written.

| Command | What |
|---|---|
| `parse --note P` | the table as a parse: activities with their steps, slices, cards, gap rows, `layout` (columns, and the cells of each band) — plus the structural errors of the table |
| `check --note P` | the script's findings of §3, each with its card |
| `render-html --note P --out F [--status S.json] [--lang uk\|en]` | the HTML page of §6 |
| `progress --note P --status S.json` | per slice: spread, % done, blocked, added / removed / moved against the baseline |
| `baseline --note P --slice S [--date D]` | the slice's baseline into the `baseline` field, nothing else changed |
| `board-diff --last L [--now N] [--note P]` | elements by `data-miro-id`: changed, moved, added, removed — and the area to read (`scope`); without `--last` (or its file) the state is `unknown` |
| `schema` | the fields, columns, findings and statuses this file and `planning-core.md` §3 must agree with (`validate-consistency.sh` check 26) |

**Without SHELL** — the note only: the model builds the table, checks it by §3 itself and says in one line that the HTML page, the baseline, the progress and the board's diff need a shell. **Without FS** — the session's note, exported at the end (`host-profiles.md`); no board state and no record.

## 11. What never happens

- A change to `task-creator`, a Jira issue for a card, a date on a slice.
- A publication or a new version without the question; a scheduled refresh of a map.
- An automatic two-way sync with the board: the team's changes come back only through §8.
- A deletion from the board without its own «так» per item; a deletion of what the team added.
- Sharing beyond named people or groups.
- A map on FigJam.
