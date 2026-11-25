# journey-protocol.md

> Shared reference (since v4.7.0). The journey map: one journey of a product, its stages from the CJM config, and on each stage the lanes of what the customer does and feels, where it hurts with evidence, what the numbers say, and what the team does about it — each row with its source and its evidence class. The procedure of `cjm-research` mode `journey` (Step J); the scheduled health-check refreshes the map's numbers locally (§10); since v4.8.0 the team edits the map on a board (§11–§12); since v4.9.0 the portfolio lists every journey map of the product and its hand CJM notes in one place (§13); since v4.10.0 a step of a map may open a child map of its own — the tree (§14); since v4.11.0 the map is edited on its page too, and what the page changed comes back through the board's take (§9, §12).
>
> **Rule of the file:** the note in the vault is the source of truth (`native-surfaces.md` §2). The dashboard and the board are renders of it, published only through `artifact-publishing.md` after its question; a scheduled run never publishes; what the team changes on the board or on the page comes back only through §12, never the health-check rows. The portfolio (§13) is one more render of the notes, computed every time — no portfolio note, no board — and a hand CJM note is only read, never changed. Nothing on the map is invented: a row without a source or a class is a finding, a stage without evidence stays a gap `⚠️`, `simulated` input never becomes a pain, and the health score is read only from a snapshot's frontmatter. A child map's rows live in its own note only: the parent shows the child's roll-up, never a copy of a row, and the nesting writes nothing to any note (§14). The map writes nothing to Jira and never names a person.

## 1. The model

- **The journey** — one funnel of the product (the CJM config's) or one named journey inside it («повторне замовлення»). One note per journey.
- **Stages** — in the order of the CJM config's funnel stages (`local-context.md` → CJM Configuration). A stage's id is `s<n>`, `n` its number in the config's stage table, so a health-check snapshot names the same stage by the same id (§10). The PM may add a stage of their own in the note (a new id: `s3a`, `home`); the script checks that every stage a row uses is declared (`undeclared_stage`, §6). A mismatch between the config's stages and a stage list kept elsewhere is the PM's to settle — in the note or in the config (`plugin-configurator`).
- **Steps** — an optional column: a smaller action inside a stage, where evidence most often attaches. Since v4.10.0 a step — or a whole stage — may open a journey map of its own, a child map with its own stages, lanes and evidence (§14).
- **No dates on the map** except the dates of the evidence and of the review.

## 2. The lanes

Ten fixed lanes, in this order on every render. A row stands in one lane on one stage.

| Lane | Ukrainian name | Evidence class |
|---|---|---|
| `action` | `дії` | `measured`, `observed`, `reported`, `external` (any real) |
| `touchpoint` | `точки контакту` | `measured`, `observed`, `reported`, `external` (any real) |
| `experience` | `досвід` | `measured`, `observed`, `reported`, `external` (any real; the effort or the emotion at the stage) |
| `pain` | `болі` | `measured`, `observed`, `reported`, `external` (never `simulated`) |
| `metric` | `метрики` | `measured` |
| `anomaly` | `аномалії` | `measured` |
| `opportunity` | `можливості` | — (the pains under it carry the evidence, §5) |
| `solution` | `рішення` | — (a hypothesis, no class) |
| `initiative` | `ініціативи` | — (a code of an existing epic or feature) |
| `experiment` | `експерименти` | — (a record of `experiment-tracker`) |

Classes are the grammar of `pm-mental-model.md` §4, checked by `data-integrity-protocol.md` Gate Check 6. No separate lanes for goals or the backstage: they are «when needed», and the need is not measured.

## 3. Inputs — nothing invented

Read in this order, each when it exists; several combine into one map. Every row carries a source marker and, in an evidence lane, its class:

1. **The newest health-check snapshot** of the product (`~/.grow-pm/knowledge-library/health-checks/`, its frontmatter, `cjm-reports.md`) → `metric` and `anomaly` rows, `measured`, source `health-check <date>, <period>` — written by `journey_map.py refresh` (§10) on the first build too, so their ids are the health-check's and the next refresh finds them.
2. **`feedback-triage`** themes (`Research/feedback/`) → `pain`, `reported`, source `feedback-triage <date>, тема «…», pain <score>`.
3. **A `flow-walkthrough` pack** → `pain`, `observed`, source `walkthrough <date>, крок N`.
4. **`product-research`** → `pain`, `external` (a benchmark, a public source) or `reported` (an interview synthesis).
5. **Hypotheses** — `Hypotheses/` notes and `cjm-research` hypotheses → `solution`, its source the hypothesis note or report.
6. **The `experiment-tracker` registry** (`~/.grow-pm/experiments/registry.yaml`) → `experiment`, its id in `код`.
7. **Epic and feature codes** (`planning-core.md` §2) → `initiative`, the code in `код` — a code only, never a URL.
8. **The conversation** → source `зі слів PM`, class `reported`.

A persona's answer or any `simulated` input is never a pain; it may inspire a `solution` only. A stage no input gives evidence for stays a gap row `⚠️` (§7) and the finding `empty_stage`. No row names a person — a customer's quote keeps its words, never their name, e-mail or phone. Row texts are internal data: they leave the note and this machine only through the publication's question (§9, `data-policy.md`).

## 4. Metrics by level

The column `рівень` of a `metric` row says where the number belongs:

| Level | Where | Example |
|---|---|---|
| `stage` | perception at the stage (CSAT, CES) — the default when the cell is empty | effort score at checkout |
| `transition` | the result of passing to the next stage | conversion cart → order |
| `journey` | the business result of the whole journey | repeat-order share, churn |

Each stage has one **outcome metric** — the metric its opportunity tree moves (§5) — declared in the note's `stages[].outcome` as a metric and a target, or `⚠️ TBD` (`no_outcome`, §6). Thresholds for anomalies are the CJM config's (warning and critical, as in `cjm-protocol.md`); the map compares with the product's own baseline, never a market average.

## 5. The opportunity tree

A view of the opportunity lane on one stage (Teresa Torres' opportunity solution tree), built from the rows' `parent` links:

- **The outcome** — the stage's `stages[].outcome`.
- **Opportunities** — `opportunity` rows on the stage; one of them may be the target (`ціль` = `так`; a second target on a stage, or `так` on a row of another lane, is `bad_target`). Pains are its evidence: a `pain` row's `parent` is the opportunity it speaks for. An opportunity with no pain of a real class under it is the model's finding `opportunity_no_story` (§6).
- **Solutions** — `solution` rows, `parent` = the opportunity. A target opportunity wants at least three to compare (`few_solutions`).
- **Tests** — `experiment` rows, `parent` = the solution.
- **Initiatives** — `initiative` rows, `parent` = the pain, the opportunity or the solution they act on.

Which parent each lane takes (anything else is `orphan`; a parent is always a row on the same stage):

| Lane | Its parent |
|---|---|
| `pain` | empty, or an `opportunity` |
| `solution` | an `opportunity` (required) |
| `experiment` | a `solution` (required) |
| `initiative` | empty, or a `pain`, an `opportunity` or a `solution` |
| every other lane | empty |

`journey_map.py tree --stage <id>` prints the stage's tree as Mermaid text; `diagram-prototyper` renders it. No Opportunity Score is entered or computed — there is no survey data behind it.

## 6. Checks — findings, never a block

Checked when the map is built (Step J2) and on every refresh. The structural checks are `journey_map.py check`; the semantic ones are the model's, by the text of the rule. **Every finding is a proposal — the PM decides.** None blocks the note, a publication or the scheduled refresh.

| Finding | Who | What it is | Proposal |
|---|---|---|---|
| `no_owner` | script | the note has no `owner` | a role or a team — never a person's name |
| `stale_review` | script | `reviewed` is empty or older than 90 days | review the map and set the date |
| `no_outcome` | script | a stage whose `outcome` is empty or `⚠️ TBD` | a metric and a target, else it stays `⚠️ TBD` |
| `empty_stage` | script | a declared stage with no row of evidence — an evidence lane, a source, a class its lane takes, a date where it needs one (a simulated pain or an unsourced number is no evidence) | evidence from the inputs (§3), or the gap stays |
| `undeclared_stage` | script | a row on a stage `stages` does not declare | declare the stage, or fix the cell |
| `unknown_lane` | script | a lane that is not one of the ten (§2) | fix the cell |
| `no_source` | script | a row without a source marker | name the source, or drop the row |
| `no_class` | script | a row of an evidence lane without its class | the class of its source |
| `wrong_class` | script | a class the lane does not take (§2), or a word that is not a class | the source's real class, or another lane |
| `simulated_pain` | script | a pain whose class is `simulated` | drop it; a persona's answer may inspire a solution only |
| `bad_level` | script | a level that is not `stage`, `transition` or `journey`, or a level on a row that is not a metric | fix the cell |
| `bad_target` | script | `ціль` on a row that is not an opportunity, or a second target on one stage | one target opportunity per stage |
| `bad_date` | script | a date that is not YYYY-MM-DD, or a pain, metric or anomaly without its date | the date of the evidence |
| `bad_code` | script | an initiative whose code is not an epic or feature code (`planning-core.md` §2) | the code of the existing epic or feature |
| `orphan` | script | a `parent` that names no row, a row of a lane §5 does not allow, or a row on another stage | fix the link |
| `pain_no_action` | script | a pain older than 182 days from whose chain of `parent` links no initiative or experiment hangs | an initiative (`roadmap-architect`) or an experiment |
| `few_solutions` | script | a target opportunity with fewer than three solutions | more solutions (`brainstorm-features`) |
| `stale_metric` | script | a health-check metric row older than the newest snapshot of the product (a metric of another source is not the snapshot's to refresh) | refresh it from the snapshot (§10) |
| `duplicate_id` | script | two rows with one id | a new id for the later row |
| `link` | script | a link in a row's cells — a row carries no link | drop it; the source marker names the page |
| `secret` | script | a row's cells hold a key, a token or an identifier the never-store filter finds (`ctx_never.py`) | remove it; such a row never goes to the page as it is |
| `contact` | script | the owner or a row holds an e-mail address or a phone number — a person's contact | a role or a team for the owner; the words without the contact in a row |
| `opportunity_no_story` | model | an opportunity whose pains do not tell a customer's story — none under it, or only the team's guesses and opinions however they are classed | a pain with evidence under it, or it becomes a hypothesis |
| `two_pains` | model | one pain row holds two different pains | split it into two rows |
| `person_name` | model | a row, a source or the owner names a person (a customer, a colleague) | the role or the segment instead of the name |

«A pain's chain»: the pain itself, the opportunity it hangs under, and every row that hangs under either of them at any depth — the opportunity's solutions and their experiments, the initiatives, the opportunity's other pains. The pain is acted on when an `initiative` or an `experiment` is in it.

## 7. The note

`type: cjm-journey`, saved to `CJM/journeys/{product}/` by the vault save (`vault-schema.md`); without a vault, a file in the workspace (`persistent-storage.md`). The file name is `journey-<slug>`, the slug from the journey's name («checkout»), and it never changes — the publication key is built from it (§9), and a child map names its parent by it (§14). A later run updates the same note in place: its table, its sections and the fields the skill owns, never the fields other writers own — `published` (`publications.py`), `health` (`journey_map.py`), `created`, `related` stay as they are (`vault-protocol.md`).

**Frontmatter** — the journey's own fields, next to the vault's usual ones:

| Field | What |
|---|---|
| `product` | the product id from `local-context.md` |
| `journey` | the journey's name |
| `owner` | a role or a team that keeps the map alive — never a person's name (`people-context-protocol.md`) |
| `reviewed` | the date of the last review, YYYY-MM-DD |
| `stages` | the stages in order, a list of `id`, `name` and `outcome` (a metric and a target, else `⚠️ TBD`) |
| `parent` | only in a child map (since v4.10.0, §14): the parent map's name, `journey-<slug>` — the link lives in the child, the parent stores nothing |
| `parent_stage` | the parent's stage id the child opens from (§14) |
| `parent_step` | the step of that stage as the parent's rows write it — optional: without it the child hangs on the stage (§14) |
| `health` | written only by `journey_map.py health` and `refresh`: a list of `date`, `score` and `snapshot` (the snapshot's file name) — joined, never erased (§8) |
| `published` | the mirror of the publication record (`artifact-publishing.md` §5), written only by `publications.py` |

```yaml
type: cjm-journey
product: zorg
journey: "First order"
owner: "Checkout team"
reviewed: 2026-11-02
stages:
  - id: s1
    name: "Visit"
    outcome: "visit -> search >= 45%"
  - id: s2
    name: "Search"
    outcome: "⚠️ TBD"
health: []
```

**The rows — one markdown table** under the heading `## Карта` (`## Map` in English), easy to edit in Obsidian and parsed by the script. A short row gets empty cells, as Markdown shows it, and the script names it. A row whose `текст` is empty or starts with `⚠️` is a gap row. A header may be written in the note's language:

| Column | Ukrainian header | What |
|---|---|---|
| `id` | `id` | the row's id: stable, never reused; `m-…` and `a-…` are the health-check's (§10) |
| `stage` | `етап` | a stage id of `stages` |
| `step` | `крок` | the step inside the stage, optional |
| `lane` | `доріжка` | one of the ten lanes (§2), by its id or its Ukrainian name |
| `text` | `текст` | what it is, in the customer's or the team's words |
| `level` | `рівень` | a metric's level (§4), else empty |
| `target` | `ціль` | `так` on the stage's target opportunity (§5), else empty |
| `parent` | `parent` | the id of the row this one hangs under (§5) |
| `code` | `код` | an initiative's epic or feature code, an experiment's registry id |
| `source` | `джерело` | `health-check 2026-11-02, 2026-10-26..2026-11-01`, `feedback-triage 2026-10-30, тема «…», pain 7.5`, `walkthrough 2026-10-12, крок 4`, `зі слів PM` |
| `class` | `клас` | the evidence class (§2) |
| `date` | `дата` | the date of the evidence, YYYY-MM-DD |

Then two sections the skill writes and the PM may edit: **«Здоров'я»** — the trend in words, with its date (§8) — and **«Розриви»** — the gap rows and the findings of §6 the PM kept. The judgment footer closes the note (`artifact-style-gate.md` Gate 4a) — on the note only, never on the dashboard.

## 8. Health over time

- `journey_map.py health --note <note> --snapshots <dir>` reads the frontmatter of every snapshot of the note's product in the folder — `type: cjm-health-check`, `product`, `date`, `health_score` (`cjm-reports.md`) — and writes the `health` field alone: the note's points joined with one per snapshot in the folder, oldest first. A point whose snapshot the folder no longer has (another machine, a cleaned folder) stays — the note is the truth. Every other byte of the note stays as it was.
- **Every file in the folder that is not a usable snapshot of the product** is named in the result with why — no frontmatter (saved before v4.7.0), another type, no product, no date, no `health_score` — and skipped; another product's snapshots are kept apart, unnamed. A score is never read from a snapshot's text.
- **The trend** — the section «Здоров'я» in the note (the skill writes it from the field, with the date of the newest point) and a sparkline on the page (§9). With no scored snapshot the trend is empty and the section says why; a snapshots folder that does not exist yet (no health-check has run) is an empty trend too — `check` and `health` go on, the result says `folder: missing`.
- Escalation stays the health-check's (`cjm-reports.md`): a drop of more than 10 points is named there; the map shows the points.

## 9. The script, the page and its publication

`scripts/journey_map.py`, stdlib (Python 3.9). Every command ends with one `JOURNEY_RESULT {json}` line; exit 0, 2 for a wrong argument or a note that does not parse, 1 when a file cannot be written. Table parsing, escaping, link removal and secret hiding are shared with `story_map.py` (`scripts/note_table.py`); the frontmatter field is written by `publications.py`'s `write_field`.

| Command | What |
|---|---|
| `parse --note P` | the stages, the rows by stage and lane, the gap rows, each stage's tree — plus the structural errors of the table |
| `check --note P [--snapshots D] [--today D]` | the script's findings of §6, each with its row or stage |
| `render-html --note P --out F [--lang uk\|en] [--map N …] [--dir D …]` | the page below — with the map's child maps when it has any (§14): the note's own folder, or the maps and folders named |
| `health --note P --snapshots D` | the `health` field from the snapshots' frontmatter (§8) |
| `refresh --note P --snapshot S [--out F] [--lang uk\|en]` | the scheduled refresh of §10 — the language of the note's headers when `--lang` is not given; the pages of the maps above a child rendered again (§14) |
| `tree --stage S --note P [--out F]` | the stage's opportunity tree as Mermaid text (also into `F`), and `few_solutions` when its target has fewer than three solutions |
| `board-layout --note P [--lang uk\|en] [--with-children] [--map N …] [--dir D …]` | the board's grid (§11): the stages with their outcome, the lanes, a cell per lane of every stage with its rows' board text and second line, the cell titles to read back, the rows the board leaves out; with `--with-children` the tree board (§14) |
| `board-state --read R… --note P --surface miro\|whiteboard [--last S] --out F [--with-children] [--map N …] [--dir D …]` | the board read back, kept as its state (§12): every element and its role; a tree board's state remembers its children (§14) |
| `board-diff --last L [--now N…] --note P [--surface miro\|whiteboard] [--out F] [--with-children] [--map N …] [--dir D …]` | what the team did on the board since the state (§12), by element id; without `--now` the ids, the rows and the area to read back; without `--last` (or its file) the state is `unknown`; a tree board as its state says (§14) |
| `board-take --note P --diff D… --take <id…> [--class <id>=<class> …] [--parent <id>=<id> …] [--drop <row id> …] [--date D] [--dry-run]` | what the PM took into the note (§12) — every other byte kept; `--dry-run` is the preview; one diff per board — the note's own and a tree board it is a child on, in one preview (§14) — and per file of edits from the page (since v4.11.0) |
| `page-diff --note P --edits F [--out D] [--lang uk\|en] [--map N …] [--dir D …]` | since v4.11.0: the edits made on the map's page — the file it saved or the text it copied — as a diff `board-take` reads (§12): the root's rows plain, a child's keyed as on a tree board (§14); a map whose rows changed since the page is `stale`, nothing of it read |
| `nest --note P [--map N …] [--dir D …] [--lang uk\|en] [--json]` | the map's subtree of child maps with each child's roll-up, and the findings of the nesting (§14) — nothing written; without `--json` the tree for the chat first |
| `schema` | the fields, columns, lanes, levels, findings and commands this file must agree with (`validate-consistency.sh` check 28) |

**The page** — `render-html`: one self-contained HTML page — the grid of stages across and lanes down, each stage with its outcome; since v4.8.0 the stage headers and the lane names stay in view while the grid scrolls in its own frame, and the grid pans with the mouse held down (one fixed inline script — no data of the note in it, no request); since v4.11.0 the map is edited on the page as well as on the boards (below, §12); each row's text with its source, class and date; the health trend as an inline SVG sparkline with each point's date, score and snapshot; the note's name, the owner, the review date and the date of the page at the top. **Only what the map may show:** a row without a source, an evidence row whose class its lane does not take (a simulated pain) or whose date is missing, and a row off the declared stages or the ten lanes are left out — the page says how many, the note's findings name them; a stage with no evidence shows its gap. No external request, no link (codes only), every text escaped, a person's e-mail or phone and a string holding a secret hidden, light theme. Always written next to the note. Since v4.11.0 every page carries the switch «Редагувати» — see «Editing on the page» below. Since v4.10.0 a map with child maps (or above one, or a reference past the depth) gets the tree page of §14; a map with none of them renders exactly as before.

**Editing on the page** (since v4.11.0, the user's decisions of 2026-11-25) — the switch «Редагувати» («Edit») on every page of the map, the published one included, so a colleague can edit it too. Off, the page is the snapshot above. On, a click on a row opens its editor, «+» in a cell adds a row; the page keeps the edits in memory and hands them over in one of two ways, **never a request**: «Зберегти правки» saves the file `journey-<slug>.page-edits.json`, «Скопіювати правки» copies the same text (a host's sandbox may block the download — the copy, and the field it is shown in, still work). The page sends nothing; an edit reaches the note only through §12's preview.

- **What the page reads** — attributes of its markup, never its script: the map's name and the digest of its rows (`table_sig`) on each grid's frame, each cell's stage, lane and title, each row's id, lane, parent, code, target and whether it is locked. Page-safe values only (§9's rules). The page's second script (`EDIT`) is fixed bytes too — no data of a note in it.
- **What it edits** — what the board does, and the links the board cannot carry:

| Op | What |
|---|---|
| `text` | a row's text |
| `move` | a row to another cell — another stage, another lane, or both |
| `add` | a new row in a cell, with its parent, code and target when its lane takes them |
| `remove` | a row gone — it leaves the note only on the PM's `--drop` (§12) |
| `parent` | the row it hangs under (§5) — a row of the same stage the lane may hang under |
| `code` | an initiative's epic or feature code, an experiment's registry id |
| `target` | the stage's target opportunity (§5) — one per stage |

- **Locked** — a health-check row (`m-…`, `a-…`) and every `metric` or `anomaly` row: no editor on the page, the cell of those lanes no «+» (R25); an edit of one that comes in a file anyway is `hc_edits` or refused `metric_lane`, never taken.
- **The file** — `{"kind": "journey-page-edits", "version": 1, "product", "root", "made", "maps": {<map>: {"digest", "edits": [...]}}}`; no author, none asked for. It is another person's input: `page-diff` reads at most 2 MB, finds the JSON object in a pasted text, checks the kind, the version, the product and the page's root, and each map's digest against its note now — a map changed since the page is `stale`, its edits not read; a map the page does not show is `unknown_map`, a row the map does not have `unknown_row`, an edit that is no op of the table `bad_edit`. Every text is made page-safe before it is kept (a link removed, a contact hidden, a secret hidden whole — refused `secret` by the take).
- **Back into the note** — `page-diff --note <the page's root> --edits <file> --out <scratch diff>`, then §12 as for a board: one preview (`board-take … --dry-run`), the class asked from the PM for every row of an evidence lane the page wrote or changed, then `board-take`. A row the page changed takes the source «сторінка команди <date>» (`team page <date>`) — the page cannot say who edited it. On a tree page a child's rows go into the child's own note (§14).

**Publication** — through `artifact-publishing.md`, never around it. The kind is `dashboard`, and since v4.8.0 a board is the second place of the same question (§11); the key `cjm-research/<product>/journey-<slug>` — one dashboard and its boards per journey, apart from the funnel's `cjm-research/<product>/funnel`. `publications.py find --key <key> --note <note>` runs first; a place found is offered as «нова версія N». The question names each candidate, what goes (internal data: the map's rows, metrics, pains) and who can open it — and, since v4.11.0, that the page carries the switch «Редагувати»: whoever opens it may edit it and send the PM a file of edits, which comes back only through §12's preview; «лише файл» is always one answer, and «ні» or «лише файл» is final for the run. After each place: `publications.py record --key <key> --note <note> --surface <surface> --kind dashboard …` (a board: §11). Sharing — to named people only, a separate question after the publication (`artifact-publishing.md` §7). The page is a snapshot with its date on every surface.

**Without SHELL** — the note only: the model builds the table, checks it by §6 itself and says in one line that the page, the health trend, the tree, `refresh` and the board need a shell. **Without FS** — the session's note, exported at the end (`host-profiles.md`); no record.

## 10. The scheduled health-check

When the product has a journey note in the vault, the automated health-check (`cjm-reports.md` → Automated Health-Check Protocol), after it saves its snapshot, runs `journey_map.py refresh --note <note> --snapshot <the new snapshot> --lang <uk when user.language is uk, else en>` (a note outside the vault, or a run without SHELL, waits for the next interactive run's J5):

- **Ids.** A metric row is `m-<stage>-<metric slug>`, an anomaly row `a-<stage>-<metric slug>` — the slug is the metric's name in lower case, every run of characters that are not letters or digits one hyphen (`search -> cart` → `search-cart`). A stage entry with `warning`, `critical` or `positive` gives an anomaly row; a stage the note does not declare and an entry without its metric are named in the result, never a row.
- **Replaced** — a `metric` or `anomaly` row with the id whose source starts with `health-check`: its text, source, class and date; every other cell the PM wrote (step, level, target, parent, code, a column of their own) stays. **Added** — a new id gets a row after its stage's last row, a metric at level `transition` (a funnel stage's metric is the conversion to the next stage). **Removed** — a health-check anomaly row `a-<stage>-…` of a stage the snapshot covers that the snapshot no longer has (it resolved).
- **Kept and named** — a row with the id but another source or lane, and an id that appears twice; every other row, and every other byte of the note, stays as it was.
- **Never backwards** — a snapshot older than the map's health-check rows is refused, the note untouched.
- **One map's snapshot** (since v4.10.0, §14) — a snapshot that names a map in its frontmatter (`map: journey-<slug>`) refreshes that map only; one without `map` is the funnel's and never refreshes a child map (a map with `parent`) — its stages are its own. Either refusal leaves the note untouched and is named.
- The `health` field gets the snapshot's point (§8), and the page is rendered again next to the note. When the map is a child (§14), the pages of the maps above it are rendered again beside their notes too — their notes never written, a page that cannot be written named (`pages_above_failed`), never a failed refresh.

It never publishes, asks nothing and never reads or updates a board (§11). After the maps it re-renders the portfolio's page locally (§13), and the health-check's one end line names both: «Новий health-check від <дата>, карти шляху й портфель оновлено локально — опублікувати можна в наступному прогоні.» The next interactive run offers the publication with its question (§9).

## 11. The board

The board is one more render of the note (since v4.8.0): the team reads and edits the map there; what it changes comes back into the note only through §12.

- **Candidates** — kind `board` (`artifact-publishing.md` §2): a registry record with `board` in its `publishes` whose tools in this session create frames and stickies, update an element by its id and read the board back (Miro: measured in the story map's acceptance, 2026-11-10), and the host's own board type — ARTIFACT `typed` with a board kind whose elements are written and updated by id and listed back (measured 2026-11-17: a board created from the type, a grid of sections with stickies in one write, a sticky updated by its id with only its changed field, the elements listed back, a person's sticky read back as their own element). An observed capability, never a brand: a tool that draws diagrams only, or cannot update an element by its id, is no candidate; FigJam is not one in this release (`story-map-protocol.md` §6).
- **The grid** — `journey_map.py board-layout --note <note> --lang <lang>`: the stages across in the order of `stages`, the lanes down in the order of §2; above each column the stage's `<id> · <name>` and its outcome (`⚠️ TBD` when it has none; a stage without evidence says its gap `⚠️`); the lane names at the left. **Every cell** is a frame (Miro) or a section (the host's board) titled `<stage id> · <lane>` — «s3 · болі», in English «s3 · pains» — and there is a cell for every lane of every stage, empty ones too, so the team has somewhere to add (5 stages make 50 cells).
- **A sticky** carries its row's `board_text` — the text with any link and any person's e-mail or phone removed, hidden whole when it holds a secret (`note_table.safe`) — and a second line: an initiative's or an experiment's code (page-safe too), or «health-check» on a health-check row (`m-…`, `a-…`), which takes another colour. The stage names, outcomes and the title are page-safe as well. Never a row id, a source, a class, a date or a name. **Only what the page shows** is on the board — the rows `render-html` would show (§9); `board-layout` names the rest (`hidden`). **No `parent` connectors**: the opportunity tree stays Mermaid (Step J3).
- **Built by the model** from `board-layout`, following the tool's own instructions — Miro's composer skill, the host board type's own instructions, read before the first board. On the host's board a cell is a section written before what it holds, the plugin's sticky is a rounded block (a person's sticky is their own element, never the plugin's), and a board is never rebuilt: a new version updates each element by its id with only its changed fields.
- **Publication** — the key does not change: `cjm-research/<product>/journey-<slug>`, the dashboard and the boards in the one question of Step J4 (§9). The map's primary kind is `dashboard`; a board is the second place, «за бажанням». The order: the dashboard's candidates by audience, then the host's own board, then a registry record's board (Miro), then «лише файл» — since v4.10.0 the host's own board first: the whole map works on the host's own tools, and no board tool's account or paid plan is ever needed (a free plan limits its editable boards).
- **Who sees it.** A Miro board in the team's root folder — «бачиш ти, а можливо — й учасники команди за її налаштуваннями», the record `unknown`. The host's board is private until it is shared — «бачиш лише ти, поки не поділишся», the record `private`; sharing is a separate question to named people only, and on the host's surface the user shares it in the host's interface (`artifact-publishing.md` §7).
- **The record** after each board: `publications.py record --key <key> --note <note> --kind board --surface miro --id <board id> --url <link> --audience unknown`, or `--kind board --surface artifact --level typed … --audience private`; the audience on the first record only — a new version keeps it.
- **The state** — after each board publication the skill reads the board back (§12) and keeps it: `journey_map.py board-state --read <reads> --note <note> --surface miro|whiteboard [--last <the previous state>] --out ~/.grow-pm/journey-maps/<product>/journey-<slug>.<surface>.board.json`, `<surface>` the record's (`miro`, `artifact`); `--last` every time there is a previous state — a new version, a take, a rebuilt state — so a sticky keeps its row by its element id. The board's texts are internal data: the state stays on this machine, like the vault.
- **A new version** of a board is an update of the same board by element ids — each row's sticky by the id its state names, a row without one as a new sticky — after §12; never a new board unless the PM chooses one there.
- **A tree board** (since v4.10.0, §14) — `board-layout --with-children`: below the map's grid, a block per child map the page shows, depth first, its cells titled `<child> · <stage id> · <lane>` and its rows keyed `<child>#<row id>`; in the parent's cell `<stage> · дії` a roll-up sticky with the child's numbers (its own colour), on Miro linked to the child's first cell (`link_to`), on the host's board naming the child — the type links only to http(s) pages, never to an element of the same board (measured 2026-11-24); past three levels a reference sticky, no grid, no link. `board-state` and `board-diff` with `--with-children` read it; its state is the root's key's, one per surface, and remembers its children.
- **No board tool in the session** → the dashboard and the file, and once per run the registry's one line (`tool-registry.md` §4: `tools_scan.py suggest --skill cjm-research --need board`). **Without SHELL** — the note only, and the one line of §9.

## 12. What the team changed on the board — only through a question

- **The state.** `board-state` keeps every element of the read and its role, and every text page-safe — a link removed, a contact hidden, a secret hidden whole: a state or a diff never keeps what the page would not show. A sticky's `origin` says whose it is: the plugin's (a row the board shows) or the team's — a team sticky, a person's own note on the host's board, and one an earlier take made a row of (its row's source is the team board; the row may not be on the page yet: no class) — which stays the team's. With `--last <the previous state>` the plugin's sticky of a row the board no longer shows stays the plugin's own (`orphan`), a row's sticky whose text the note has since changed (a refreshed metric) keeps its row by its element id, and **a re-keep never absorbs what the PM did not take**: a text edit or a move the note has not taken keeps its last text and cell, and a row's sticky gone from the board stays recorded as gone, so the next diff names each again. A last state that shares no element with the read (a new board, answer 3) is set aside (`last_ignored`) — the new board's first state. A read that holds no cell of the map is refused:

| Role | What it is |
|---|---|
| `cell` | a frame or section titled `<stage id> · <lane>` of a declared stage and a known lane |
| `row` | the plugin's sticky of a row — found by its text in its own cell first, then anywhere (it was moved) |
| `header` | a stage's `<id> · <name>`, its name or its outcome above a column |
| `lane_name` | a lane's name at the left |
| `rollup` | on a tree board (since v4.10.0, §14): the plugin's roll-up sticky of a child map, or its reference sticky past the depth — never a row, never taken; its edits named as `other` |
| `team` | a sticky the note does not hold — the team's |
| `orphan` | the plugin's own sticky of a row the board no longer shows (with `--last`) |
| `frame` | any other frame or section |
| `other` | any other element: a text, a connector, a shape |

- **Reading back** is not a publication: the user's own connected tool, no question. A Miro board is read twice into scratch files — by the state's element ids (`board-diff --last <state>` prints them as `ids`) and over the map's area (`scope`); the host's board is listed back whole — every page (a limit of 1000, then each next cursor) into a fresh folder, never one reused from an earlier read. A person's edit reaches the board's store only when the page has saved it: a read made while someone is still typing may miss it (measured 2026-11-17). A read that holds no element, or no element of the board (an error the tool returned), is refused — read again; it never reads as «everything removed». A read that lacks a cell the state holds (one page of a paged list) is no diff either: `board-diff` says `partial` and names the cells, `board-state` refuses it — the plugin never deletes a cell; read again, and if the cells are truly gone, only «нова дошка», «показати, що на дошці» or «ні» are offered. A sticky keeps its line breaks, so a code is read only from its own second line.
- **Before a new version** — `journey_map.py board-diff --last <state> --now <reads> --note <note> --out <scratch diff>`; a sticky in a section the team drew inside a cell belongs to that cell. The diff carries the note's journey, product and a digest of its rows: `board-take` refuses it on another note, or on this one once it has changed — diff again:

| Category | Counted | What |
|---|---|---|
| `changed` | yes | a row's sticky whose text the team changed (with its row), or a team sticky edited again |
| `moved` | yes | a sticky moved to another cell — another stage, another lane, or both |
| `added` | yes | a team sticky the note does not hold, with its cell — every time until it is taken, so one the PM left, or one a state rebuilt with no history recorded, is offered again |
| `removed` | yes | a row's sticky gone from the board |
| `relinked` | yes | since v4.11.0, from the page only: a row's `parent` changed (§5) |
| `recoded` | yes | since v4.11.0, from the page only: an initiative's or an experiment's code changed |
| `retargeted` | yes | since v4.11.0, from the page only: a row made the stage's target opportunity, or no longer |
| `orphaned` | yes | the plugin's own sticky of a row the board no longer shows — with its text now when the team changed it; its removal is asked one item at a time |
| `hc_edits` | yes | an edit of a health-check row's sticky — its text, its cell or its removal: named, never taken |
| `other` | no | any other element added, retitled or removed (a header, a cell's title, a loose text) — named |
| `unrecorded` | no | the map's own elements the state lacks — the next `board-state` maps them; never a team addition |

- **Every count zero** → the version question of §11.
- **Anything counted** → one question that is also the version question: everything the team did, what goes where, who sees it and the version number (`artifact-publishing.md` §4, §6); the dashboard's version line when the key holds it. Five answers:

> «На дошці Miro «Zorg: перше замовлення» команда змінила 1 рядок, перенесла 1 в інший етап, додала 3 стікери й прибрала 1; правку метрики health-check «visit -> search» названо — її не забирають, наступна версія дошки поверне текст із нотатки. Що зробити? 1) забрати в карту й оновити дошку до версії 2 і дашборд до версії 3; 2) оновити дошку до версії 2 моїми рядками — правку p2 і перенесення e2 буде скасовано, прибраний h3 повернеться, додане командою лишиться; 3) нова дошка, версія 1; 4) лише забрати в карту, дошку й дашборд не чіпати; 5) ні. Дошку бачиш ти, а можливо — й учасники команди за її налаштуваннями; дашборд — лише ти (внутрішні дані: рядки карти, метрики, болі).»

  - **«Забрати»** (answers 1 and 4) — first the preview, `journey_map.py board-take --note <note> --diff <diff> --take <ids> --dry-run`: each change with its row and cell; the **evidence class** asked once, in one list, for every added row of an evidence lane — only the classes §2 lets its lane take (`measured` for metrics and anomalies; `measured`, `observed`, `reported`, `external` for the rest), plus «без класу», `simulated` never; a parent proposed for a solution or an experiment without one, among the stage's opportunities or solutions; what the take refuses and names; and what it leaves on the board (`left` — every counted edit the PM does not take). The model's `person_name` pass (§6) runs on the taken texts. Then `board-take` with the PM's picks (`--take` the element ids the preview shows, or `row:<id>` for a row; `--class <id>=<class> …` and `--parent <id>=<row> …`, several after one flag; `--drop <row> …` for each row the PM lets go), and the state is kept again — `board-state … --last <the previous state>`. Answer 1 then renders the board's new version from the note — the team's items keep their ids, and every edit left untaken (`left`) is undone on the board, which the preview says before the take — and the dashboard's.
  - **A row the team changed** takes the team's text, the source `дошка команди <date>` and the take's date, and in an evidence lane the class the PM picks — the preview asks it as for an added row; a moved row keeps its source and class — asked again when its class does not fit the new lane, cleared (and named) in a lane that takes none, and the findings name its children. **A metric or an anomaly row never changes from the board** — its edits are named (`metric_lane`), like the health-check's.
  - **A row without a class** stays in the note with its class empty: the finding `no_class` (§6), never on the page or the board; its sticky is not touched — the team's items are never deleted.
  - **Answer 2** gives the plugin's stickies the note's text and cells — the question names each team edit it undoes; what the team added stays on the board untouched.
  - **Answer 3** creates a new board (version 1, the old id to `replaced`); the old board stays as it is.
  - **«Ні»** is final for the run: the board is not touched, and the question is not repeated.
- **What `board-take` does** — the rows the PM took into the note, every other byte of it as it was:

| Code | board-take | What |
|---|---|---|
| `health_check` | refused | a health-check row — its text, its cell, its removal — never changes from the board |
| `metric_lane` | refused | an existing metric or anomaly row's text, cell or removal — named, never taken (R25) — and a move of an existing row into those lanes (a team sticky added there is a new row like any other, its class the PM's) |
| `no_cell` | refused | a sticky in no cell of the map |
| `needs_drop` | refused | a row gone from the board taken without `--drop` — a row leaves the note only on the PM's word for it |
| `not_removed` | refused | `--drop` of a row the board still has |
| `taken` | refused | an added sticky whose row the note already holds on its cell — an earlier take |
| `secret` | refused | a sticky's text that holds a key, a token or a hidden secret — never written, the element named |
| `empty` | refused | nothing left to write once a contact and a link are removed |
| `not_takeable` | refused | an element that is no team sticky and no row's change (`orphaned`, `other`, `unrecorded`) |
| `unknown` | refused | an id the diff does not name, a row the note no longer has, or a `--drop` of a row the note does not have |
| `other_note` | refused | on a tree board (§14): another map's row or cell — taken only with `--note` of the map it lives in |
| `conflict` | refused | one row changed differently on two boards (§14) taken in both versions — the PM takes one or none |
| `contact_removed` | named | a person's e-mail or phone removed before the write |
| `link_removed` | named | a link removed before the write |
| `no_class` | named | an added row of an evidence lane with no class from the PM — the class stays empty |
| `bad_class` | named | a class its lane does not take (§2) — left empty |
| `orphan` | named | an added solution or experiment without its parent — the stage's candidates proposed |
| `bad_parent` | named | a `--parent` that is not a row of its stage the lane may hang under (§5) — not set |
| `bad_code` | named | an added initiative whose own second line is not an epic or feature code (a code is never read from the end of the text), or a code with no `код` column to go to; from the page (since v4.11.0), a code that is no epic or feature code of an initiative, no registry id of an experiment, or on another lane — not written |
| `bad_target` | named | since v4.11.0, from the page: a target on a row that is no opportunity, or a second target on one stage — not set |
| `unused` | named | a `--class` or `--parent` key that matches no taken element or new row |

  A changed text goes into its row (a second line that is the row's own code or «health-check» is not part of it; an initiative's epic or feature code, or an experiment's registry id, on its own second line goes into `код` — a second line that is no code stays in the text, never read as one); a moved row takes its new stage and lane, every other cell kept; an added sticky becomes a new row `b<n>` — numbered in the diff's order, so the preview and the take give an element the same id — after its stage's last row, its source `дошка команди <date>` (`team board <date>` in an English note), its date the board's, its class the PM's (`--class` keyed by the element's id or by the new row's id the preview shows). One element taken twice is one row.
- **Boards of one row, one preview** (since v4.10.0, §14) — a child map's row may stand on several boards: the root's tree board (`<child>#<row id>`), a middle map's tree board and the child's own (`<row id>`) — every board it stands on is diffed and passed. `board-diff` runs per board; `board-take --note <child> --diff <the root board's> <the child's own>` makes one preview for the child: each diff's entries of this note made plain, another map's entries refused `other_note` (taken only into the note they live in), an element id two diffs share prefixed with its board (`<map>@<surface>:<id>`) — the same in any order of `--diff`. A row changed differently on two boards (`text`), moved to different cells (`cell`), or gone from one and changed on another (`removed`) is listed in `conflicts` with every version: the PM takes one version by its element id, or none — two versions, `row:<id>` of such a row, or the change and the `--drop` of one row are refused `conflict`, and nothing is ever picked for the PM. The take writes the child's note alone.
- **The page's edits** (since v4.11.0, §9) — `page-diff` makes the file of edits a diff of this table's categories, each entry `via: page`, one element per row the page changed (`p<n>`), and the three links a board never carries: `relinked`, `recoded`, `retargeted`. The take checks a link as `check` would (§5, §6): a parent that is a row of the same stage — after the take's moves — the lane may hang under, else `bad_parent`, and a solution or an experiment never left without one (`orphan`, its candidates proposed); a code by its lane, else `bad_code`; one target opportunity per stage, else `bad_target`. A link never changes a row's source or class: it is the map's structure, not evidence. A text the page changed or a row it added takes the source «сторінка команди <date>» (`team page <date>`) and the class the PM picks, as a board's. The page is one more source beside the boards: its diff goes into the same one preview (`board-take --diff <each board's> <the page's>`), an id two diffs share named by its source (`<map>@page:<id>`), and a row changed differently on a board and on the page — its text, its cell, its parent, its code or its target — is a `conflict`: one version or none.
- **Health-check rows** never come back from the board: their edits are named in the question, and the board's next version gives them back the note's text — the question says so.
- **Never a deletion of what the team added.** Any deletion from the board — an orphaned sticky included — is one item at a time, after its own «так».
- **No state** (another machine, a lost folder, a read-back that failed) → the skill first reads the board back — the record's board, its cells found by their titles (the board tool's own search, or the host's board listed whole) — and rebuilds the state with `board-state`; then «Не можу сказати, що змінилось на дошці»: the question names the rows it could not find (`unmapped_rows` — they would become new stickies) and has one more answer, «показати, що на дошці». Without a read-back no new version is offered — only «нова дошка», «показати, що на дошці» or «ні».

## 13. The portfolio

Every journey map of a product and its hand CJM notes in one list (since v4.9.0, R26, R32): who keeps each map, how healthy it is and where it is going, when it was last reviewed, its pains and anomalies, its gaps and where it is published — the maps that need attention first. It is computed from the notes every time; **there is no portfolio note and no portfolio board**, and the portfolio writes nothing to a note.

**Finding the notes.** `ctx.py search --type cjm-journey --type cjm --product <product> --json` (`context-protocol.md` §3) lists the notes of both types from the context index — the index refreshed first, as a search refreshes it; another product's note is left out — one product is one key, the slug of its whole name (a name with no letters to slug, by its own letters) — and a note with no product (none, or `null` / `~`) stays, marked «продукт не вказано» on its row. Each note's file (`found[].file`) goes to the script as `--note`, except a note marked `sensitive` (named by its title only — `data-policy.md` → Search, rule 1) and one whose file is not on disk or not downloaded (an empty `file`, named by its path) — never read; ctx's line `іншого продукту — не показано: <k>` is said with the table. The script checks a note's sensitivity again itself, so a folder read never takes one either. **Nothing to search or the index not read** (exit 3 or 5) → the maps' folder `CJM/journeys/<product>/` as `--dir`, and one question for the folder of the hand CJM notes — its answer as a second `--dir`, never saved; «немає» is an answer. The note's `type` decides what it is, whichever way it came.

**The script** — `scripts/journey_portfolio.py`, stdlib (Python 3.9); `journey_map.py` is imported (the note, its findings, the health-check's labels, the sparkline and the page's pan script), never copied. Every command ends with one `PORTFOLIO_RESULT {json}` line; exit 0, 2 for a wrong argument, 1 when the page cannot be written:

| Command | What |
|---|---|
| `list --product P [--note N …] [--dir D …] [--snapshots D] [--today D] [--lang uk\|en]` | the portfolio: the table for the chat (markdown), then the result — the maps, the hand CJM notes, what was skipped and why; `--snapshots` (the health-check folder) as for `journey_map.py check` |
| `render-html --product P [--note N …] [--dir D …] [--snapshots D] [--today D] --out F [--lang uk\|en]` | the same portfolio as one self-contained page |
| `schema` | the commands, columns, attention reasons, hand-CJM fields and findings and skip reasons this section must agree with (`validate-consistency.sh` check 30) |

**A journey map's row** — read from its note by `journey_map.py`; never a row's text, a source or a name, and every value page-safe — a link removed, a contact or a secret hidden; a pain's class or a publication value that is not one of its own words, and a stage id left empty by that, shows as `?`:

| Column | Ukrainian header | What |
|---|---|---|
| `journey` | `шлях` | the note's `journey` (else its title) |
| `owner` | `власник` | the note's `owner` — a role or a team; `⚠️` when empty |
| `stages` | `етапи` | how many stages it declares |
| `health` | `здоров'я` | the last point's score of the `health` field — never read from a snapshot's text; a sparkline of every point on the page |
| `delta` | `зміна` | the last score minus the one before it |
| `health_date` | `дата точки` | the last point's date |
| `reviewed` | `рев'ю` | the review date, «застаріло» past 90 days (`stale_review`, §6) |
| `pains` | `болі` | the pain rows by their class — a word that is no class counted as `?` (a gap row is no pain) |
| `anomalies` | `аномалії` | the anomaly rows, the critical ones apart: a health-check row's status is read from its last words by the labels `refresh` writes (§10, «— критично» / «— critical»); a row the PM wrote is counted without a level |
| `gaps` | `розриви` | the stages of `empty_stage` and of `no_outcome` (§6) |
| `findings` | `знахідки` | how many findings `journey_map.py check` gives (§6) — against the snapshots of the note's own product |
| `published` | `опубліковано` | the places and versions of its `published` mirror — never a link or an id |
| `attention` | `увага` | the reasons below |

**What needs attention** — a map with any reason stands first, the maps with more reasons above, then by name; the rest by name; the hand CJM notes in a block of their own after the maps, by name. Since v4.10.0 the order is a tree (§14): the roots in that order, each followed by its child maps in the parent's stage order, indented with `↳` by level; a parent shows «діти: N · уваги потребують M» — the maps under it at any depth and how many of them have a reason of their own; a map's reasons and health are its own, never raised or lowered by its children:

| Reason | Ukrainian label | When |
|---|---|---|
| `health_drop` | `здоров'я впало` | the last health point is more than 10 points below the one before it — the scheduled health-check's own escalation (`cjm-reports.md`) |
| `stale_review` | `рев'ю застаріло` | the finding `stale_review` (§6) |
| `no_owner` | `немає власника` | the finding `no_owner` (§6) |
| `critical_anomaly` | `критична аномалія` | an anomaly row the health-check marked critical |
| `empty_stage` | `етап без доказів` | the finding `empty_stage` (§6) |

**A hand CJM note** (R32) — a CJM the team keeps by hand: `type: cjm` with a `funnel` field and at least one stage heading `## <ID> — <назва>`, the ID a short code with one to three digits (`B1`, `S2`, `s3a`) — a heading such as «## Висновки — …» or «## 2026 — …» is no stage; a heading typed with a plain hyphen («## B1 - Пошук») is none either. A `type: cjm` without them (a `cjm-research` report is `type: cjm` too) is skipped and named. It is read **partly**, and the portfolio says so on its row: «ручна CJM — частково: без джерел, класів і здоров'я». Only these are read:

| Field | What |
|---|---|
| `title` | the frontmatter's `title`, else `name`, else the file's name |
| `funnel` | the frontmatter's `funnel` |
| `stages_declared` | the frontmatter's `stages` — the number of stages it declares |
| `stages` | each stage heading `## <ID> — <назва>` in order — its id, its name (a link in it dropped) and `metrics`: the row count of the first table under it whose first header cell is «Метрика» or «Metric» — no cell of it read |
| `snapshot` | the frontmatter's `snapshot`, YYYY-MM-DD |

Never read: links, dashboards, modules, owners, teams, missions, meetings or any text of the note. The note gets no health, no pains and no gaps — it has no sources or classes to give them — and two findings of its own:

| Finding | What |
|---|---|
| `stage_count` | the declared `stages` is not the number of stage headings |
| `no_snapshot` | no `snapshot` date |

«Зібрати з неї карту шляху?» leads to J1 as usual: nothing of the hand note is carried into a map — a map's inputs stay §3, and the hand note itself is never changed.

**Skipped** — each note the portfolio does not show, with why:

| Skip | Ukrainian line | When |
|---|---|---|
| `not_cjm_map` | `не CJM-карта — немає воронки чи стадій` | a `type: cjm` note without `funnel` or without a stage heading — named |
| `other_product` | `нотатка іншого продукту` | a note of another product — counted, never named or shown |
| `wrong_type` | `не карта шляху й не CJM-нотатка` | a note given by its path whose type is neither — named; one in a folder is counted (`ignored`), never named |
| `sensitive` | `чутлива нотатка — лише для People-контуру` | a note the search marks sensitive (`sensitive: true`, a people type, a 1-1 — `data-policy.md` → Search, rule 1) — named by its file's name, nothing of it read into the portfolio |
| `unreadable` | `нотатка не читається` | a note that does not read or parse (a frontmatter never closed included), or a note given by its path that iCloud has not downloaded (never opened — opening it would start a download) — named with why; in a folder, a file with no frontmatter at all is no note of the portfolio (`ignored`) and a file iCloud has not downloaded is counted in one line, never named |

**Where it is shown.**
- **In the chat** — the table `list` prints, the maps that need attention first, then the hand CJM block, then what was skipped.
- **The page** — `render-html --out CJM/journeys/<product>/portfolio.html` beside the maps in the vault, the folder created when there is no map yet (without a vault, the working folder; an `--out` that is a note, or any `.md`, is refused): one self-contained HTML page in the journey page's style — a row per map with its health sparkline (each point's date and score), the review, the attention, the hand CJM block, the page's date and each map's note named as its source. **Numbers only**: no row text of any map, no link, no request, every text escaped, a secret or a person's contact hidden, light theme; the header row and the journey column stay in view while the table scrolls in its own frame, and it pans with the mouse — the journey page's one fixed script (§9).
- **The dashboard** — through `artifact-publishing.md`, after its question, under its own key `cjm-research/<product>/portfolio`, kind `dashboard`: `publications.py find --key <key>` first, a place found offered as «нова версія N»; the candidates the dashboard's (the host's page, HTML in Atlassian Artifacts, «лише файл» always); **no board** for the portfolio. The question says what goes — the journeys' and stages' names, scores and counts, internal data (`data-policy.md`) — and who can open it. After each place: `publications.py record --key <key> --surface <surface> --kind dashboard …` **without `--note`**: there is no portfolio note, so the record lives in the key file alone.
- **The scheduled health-check** re-renders the page locally after it refreshes the maps (§10, `cjm-reports.md`): the notes `ctx search --type` gives, or without an index the maps' folder alone (no question in a headless run); it never publishes and asks nothing.

**Without SHELL** — the model builds the chat table from the notes it can read, by the rules above, and says in one line that the page, the dashboard and the context index need a shell.

## 14. Nested maps

Since v4.10.0 (R27, R30, R31, R38): a step of a map — «Оплата» in «Перше замовлення» — opens a child map («Оплата»), and that one a grandchild («3-D Secure»). The parent shows each child's roll-up on its step; the root shows the whole tree on its page and its board; a child may also be published on its own.

**The link lives in the child.** Three fields of the child's frontmatter (§7): `parent` — the parent's file name `journey-<slug>` (also read as a wiki link `[[journey-<slug>]]`, quoted or not, or Obsidian's list property of one); `parent_stage` — the parent's stage id; `parent_step` — optional, the step as the parent's rows write it; without it the child hangs on the stage. The parent stores nothing: its children are found among the product's maps every time — the notes `ctx.py search --type cjm-journey --product <product> --json` gives, else the maps' folder. A name resolves as Obsidian and the disk resolve it: any case, either Unicode form. A hand CJM note (`type: cjm`) never nests. One product: a nesting never crosses products.

**`journey_map.py nest --note <map>`** computes the map's subtree and prints it for the chat (`--json`: the result line alone); it writes nothing. A map attaches only when every part of its link holds; anything else is a finding of the script — a proposal, never a block:

| Finding | What | Proposal |
|---|---|---|
| `orphan_child` | the map hangs on nothing: why below | fix the link — the parent's name, its stage, its step |
| `nest_cycle` | maps hang under each other in a ring — named once, each stands alone | break the ring in one `parent` |
| `too_deep` | a map below three levels — shown by a reference only, never its grid (R38) | hang it higher, or keep it a map of its own |
| `other_product_parent` | the parent is another product's map | a parent of the same product, or no parent |
| `self_parent` | the map names itself | another parent, or none |

| Why | When |
|---|---|
| `no_parent` | `parent` names no map found — renamed, deleted or not given |
| `bad_parent` | `parent` holds two parents, or a value that is no map's name |
| `no_stage` | no `parent_stage` |
| `no_stage_in_parent` | the parent declares no such stage |
| `no_step` | no row of the parent on that stage has the step |

A map whose file name is not page-safe, holds a space or any of «·», «•», «|», «—», «–», «:», «#» (what a tree board's cell titles and row keys are split by) is skipped (`unsafe_name`) — rename the file to nest it. A child whose parent was skipped (sensitive, unreadable, a duplicate, an unsafe name) is `orphan_child` naming the skip.

**Depth.** A level counts from the top root: the root 1, a child 2, a grandchild 3 — three levels at most; a map below is `too_deep` and appears only as a reference by its name and level, on the page and on the board, whatever map the command is run on.

**The roll-up (R30)** — on the parent's step, numbers and one metric, never a copy of a row: the pains the child's page shows, by class (a simulated or unsourced pain is none, a health-check row is no pain); the anomalies its page shows, the critical ones by the label `refresh` ends a row with (§10) — a row the PM wrote is counted unrated; its metric of level `journey` (§4), else `⚠️ TBD`; its last health point, else «немає знімка»; its review date. A child with children of its own adds «з дочірніми картами (N): болі X · аномалії Y (критичних Z)» over the subtree the tree shows (R27). The parent's own health score never changes from its children.

**The page (R31)** — `render-html`: on the parent's grid, a chip per child in its stage's first lane (`дії`) — after the stage's gap mark, before its rows — the step named on it; a click (or Enter) opens the child's `<details>` below the parent's grid — the child's grid with its sticky headers, its own chips and its own children, nested to three levels; past them a reference by name, never a grid. The page's rules stay §9's: only page-safe text, no link, no request; one fixed script, no data of a note in it, which pans every grid and opens a chip's child. A child's own page names the maps above it.

**The board (R31)** — §11's tree board: each child's block below the root's grid, its rows keyed `<child>#<row id>`; on the child's own board plain ids (C7). States per board and surface; `board-state` and `board-diff` name each roll-up and reference sticky by its element id (`rollups`, `references`), so a new version updates them by id — a sticky whose child left the tree stays the plugin's, never a team row. What the team changed comes back through §12's one preview per note, a row changed differently on several boards offered in every version — one or none, never two.

**A child's own publication (R31, C9).** Its key is its own: `cjm-research/<product>/journey-<slug of the child>` — its page and its boards as any map's (§9, §11). When the child is inside a root already published, the one question of Step J4 names both places — the root's new version and the child's own place — each published only when the answer names it (`artifact-publishing.md` §4). A root's tree page and tree board carry the rows of every child map they show: the question names those maps among what goes.

**The portfolio** (§13) lists the maps as a tree. **Refresh** (§10): a child map's stages are its own, so the funnel's snapshot never refreshes it — only a snapshot made for it, naming it (`map: journey-<slug>`); the scheduled health-check refreshes the maps without a `parent` and leaves the children as they are; a refreshed child renders the pages above it again, locally — nothing is ever published.

**The tree page edited (since v4.11.0, §9).** Each grid on the page carries its own map's name and digest; an edit of a child's row is that child's, keyed `<child>#<row id>` on `<child> · <stage>` as on a tree board — `board-take --note <child> --diff <the page's diff>` takes it into the child's note alone, every other map's entries `other_note`. A reference past the depth is not edited.

**Known limits.** The tree is computed from the notes every time: renaming a parent's file breaks its children's links (`orphan_child`) until their `parent` is set again. On the host's board the roll-up sticky names the child's section, with no link. No health-check writes a snapshot for one child map yet: a child's numbers change when the PM updates it (J5) or a snapshot made for it is given.

## 15. What never happens

- A request from the page — its edits leave it only as a file saved or a text copied (§9); an edit from the page written into a note without §12's preview; a health-check, metric or anomaly row changed from the page.
- A portfolio note or a portfolio board; nesting across products.
- A child's row copied into its parent — on the page, the board, the chat or a note; a note written by the nesting; a child's numbers changing its parent's health score; a grid below three levels.
- A row changed differently on two boards taken automatically, or in both versions.
- A publication or a new version without the question; a publication from a scheduled run; a board read, updated or asked about by the scheduled health-check.
- An automatic two-way sync with a board: the team's changes come back only through §12, the health-check rows never.
- A class the PM did not pick; a deletion of what the team added; a deletion from a board without its own «так» per item.
- `parent` connectors on a board; a story map on the host's board type.
- A person's name on the map or a board (the model's `person_name` pass on taken text; a board state keeps the team's texts page-safe, names not filtered, and never leaves this machine); an Opportunity Score.
- A health score read from a snapshot's text.
- A write to Jira: an initiative links an existing code; creating one is `roadmap-architect`'s.
- A change to a CJM tracker the team keeps by hand, or anything read of a hand CJM note beyond §13's fields.
