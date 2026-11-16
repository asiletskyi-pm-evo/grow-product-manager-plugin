# journey-protocol.md

> Shared reference (since v4.7.0). The journey map: one journey of a product, its stages from the CJM config, and on each stage the lanes of what the customer does and feels, where it hurts with evidence, what the numbers say, and what the team does about it — each row with its source and its evidence class. The procedure of `cjm-research` mode `journey` (Step J); the scheduled health-check refreshes the map's numbers locally (§10).
>
> **Rule of the file:** the note in the vault is the source of truth (`native-surfaces.md` §2). The dashboard is a render of it, published only through `artifact-publishing.md` after its question; a scheduled run never publishes. Nothing on the map is invented: a row without a source or a class is a finding, a stage without evidence stays a gap `⚠️`, `simulated` input never becomes a pain, and the health score is read only from a snapshot's frontmatter. The map writes nothing to Jira and never names a person.

## 1. The model

- **The journey** — one funnel of the product (the CJM config's) or one named journey inside it («повторне замовлення»). One note per journey.
- **Stages** — in the order of the CJM config's funnel stages (`local-context.md` → CJM Configuration). A stage's id is `s<n>`, `n` its number in the config's stage table, so a health-check snapshot names the same stage by the same id (§10). The PM may add a stage of their own in the note (a new id: `s3a`, `home`); the script checks that every stage a row uses is declared (`undeclared_stage`, §6). A mismatch between the config's stages and a stage list kept elsewhere is the PM's to settle — in the note or in the config (`plugin-configurator`).
- **Steps** — an optional column: a smaller action inside a stage, where evidence most often attaches. Nested journeys (a step that opens a journey of its own) are not in this release.
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

`type: cjm-journey`, saved to `CJM/journeys/{product}/` by the vault save (`vault-schema.md`); without a vault, a file in the workspace (`persistent-storage.md`). The file name is `journey-<slug>`, the slug from the journey's name («checkout»), and it never changes — the publication key is built from it (§9). A later run updates the same note in place: its table, its sections and the fields the skill owns, never the fields other writers own — `published` (`publications.py`), `health` (`journey_map.py`), `created`, `related` stay as they are (`vault-protocol.md`).

**Frontmatter** — the journey's own fields, next to the vault's usual ones:

| Field | What |
|---|---|
| `product` | the product id from `local-context.md` |
| `journey` | the journey's name |
| `owner` | a role or a team that keeps the map alive — never a person's name (`people-context-protocol.md`) |
| `reviewed` | the date of the last review, YYYY-MM-DD |
| `stages` | the stages in order, a list of `id`, `name` and `outcome` (a metric and a target, else `⚠️ TBD`) |
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
| `render-html --note P --out F [--lang uk\|en]` | the page below |
| `health --note P --snapshots D` | the `health` field from the snapshots' frontmatter (§8) |
| `refresh --note P --snapshot S [--out F] [--lang uk\|en]` | the scheduled refresh of §10 — the language of the note's headers when `--lang` is not given |
| `tree --stage S --note P [--out F]` | the stage's opportunity tree as Mermaid text (also into `F`), and `few_solutions` when its target has fewer than three solutions |
| `schema` | the fields, columns, lanes, levels, findings and commands this file must agree with (`validate-consistency.sh` check 28) |

**The page** — `render-html`: one self-contained HTML page — the grid of stages across and lanes down, each stage with its outcome; each row's text with its source, class and date; the health trend as an inline SVG sparkline with each point's date, score and snapshot; the note's name, the owner, the review date and the date of the page at the top. **Only what the map may show:** a row without a source, an evidence row whose class its lane does not take (a simulated pain) or whose date is missing, and a row off the declared stages or the ten lanes are left out — the page says how many, the note's findings name them; a stage with no evidence shows its gap. No external request, no link (codes only), every text escaped, a person's e-mail or phone and a string holding a secret hidden, light theme. Always written next to the note.

**Publication** — through `artifact-publishing.md`, never around it. The kind is `dashboard`; the key `cjm-research/<product>/journey-<slug>` — one dashboard per journey, apart from the funnel's `cjm-research/<product>/funnel`. `publications.py find --key <key> --note <note>` runs first; a place found is offered as «нова версія N». The question names each candidate, what goes (internal data: the map's rows, metrics, pains) and who can open it; «лише файл» is always one answer, and «ні» or «лише файл» is final for the run. After each place: `publications.py record --key <key> --note <note> --surface <surface> --kind dashboard …`. Sharing — to named people only, a separate question after the publication (`artifact-publishing.md` §7). The page is a snapshot with its date on every surface.

**Without SHELL** — the note only: the model builds the table, checks it by §6 itself and says in one line that the page, the health trend, the tree and `refresh` need a shell. **Without FS** — the session's note, exported at the end (`host-profiles.md`); no record.

## 10. The scheduled health-check

When the product has a journey note in the vault, the automated health-check (`cjm-reports.md` → Automated Health-Check Protocol), after it saves its snapshot, runs `journey_map.py refresh --note <note> --snapshot <the new snapshot> --lang <uk when user.language is uk, else en>` (a note outside the vault, or a run without SHELL, waits for the next interactive run's J5):

- **Ids.** A metric row is `m-<stage>-<metric slug>`, an anomaly row `a-<stage>-<metric slug>` — the slug is the metric's name in lower case, every run of characters that are not letters or digits one hyphen (`search -> cart` → `search-cart`). A stage entry with `warning`, `critical` or `positive` gives an anomaly row; a stage the note does not declare and an entry without its metric are named in the result, never a row.
- **Replaced** — a `metric` or `anomaly` row with the id whose source starts with `health-check`: its text, source, class and date; every other cell the PM wrote (step, level, target, parent, code, a column of their own) stays. **Added** — a new id gets a row after its stage's last row, a metric at level `transition` (a funnel stage's metric is the conversion to the next stage). **Removed** — a health-check anomaly row `a-<stage>-…` of a stage the snapshot covers that the snapshot no longer has (it resolved).
- **Kept and named** — a row with the id but another source or lane, and an id that appears twice; every other row, and every other byte of the note, stays as it was.
- **Never backwards** — a snapshot older than the map's health-check rows is refused, the note untouched.
- The `health` field gets the snapshot's point (§8), and the page is rendered again next to the note.

It never publishes and asks nothing. The health-check's one end line names the map too: «Новий health-check від <дата>, карту шляху оновлено локально — опублікувати можна в наступному прогоні.» The next interactive run offers the publication with its question (§9).

## 11. What never happens

- A Miro board of the map or a portfolio of journeys in this release (v4.8.0).
- A publication or a new version without the question; a publication from a scheduled run.
- A person's name on the map; an Opportunity Score.
- A health score read from a snapshot's text.
- A write to Jira: an initiative links an existing code; creating one is `roadmap-architect`'s.
- A change to a CJM tracker the team keeps by hand.
