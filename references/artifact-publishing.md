# artifact-publishing.md

> Shared reference (since v4.3.0). How a skill turns a finished result into a link the user opens, updates and shares: which places it can go to, in which order, the one question before it leaves, the record of where it went, and a **new version of the same place** on the next run instead of a copy. The other skills that publish keep their own question of `native-surfaces.md` §3 and do not record versions yet.
>
> **Consumers:** `design-bridge` (decks), `product-reporter` (a report as a document or a dashboard), `cjm-research` (the funnel report and its dashboard), `focus-advisor` (the live board), `roadmap-architect` (the story map's board and its progress dashboard, since v4.6.0).
>
> **Rule of the file:** the same as `native-surfaces.md` — a host surface is named by its capability (ARTIFACT, DOCS), never by its brand (§6 there); Atlassian and Confluence are connectors and are named. Nothing leaves without the question of `native-surfaces.md` §3, a new version included, and a scheduled run never publishes (§4 there).

## 1. The kind of result

| Kind | What it is | Who makes it here |
|---|---|---|
| `deck` | slides to present and page through | `design-bridge` |
| `dashboard` | numbers and charts on one page, each with its source and date (§9) | `product-reporter`, `cjm-research`, `focus-advisor` (the board), `roadmap-architect` (the story map's progress) |
| `document` | text the reader reads and may edit | `product-reporter`, `cjm-research` |
| `page` | a wiki page in a space | the skills that already write to Confluence |
| `board` | a whiteboard the team edits together | `roadmap-architect` (the story map, `story-map-protocol.md`) |
| `design` | a design file | — (the registry's design tools) |

The same six words are the `publishes` values of the tools registry (`tool-registry.md` §1) and the `kind` of a publication record (§5). The skill names its kind at its own step; it never asks for it.

## 2. The candidates

Four sources, read in this order, each only when present — a missing one is not mentioned (`native-surfaces.md` §5, «No line for an addition»). One place is one candidate, whichever sources name it:

1. **The host's surfaces**, marked in Step 0-host: ARTIFACT `typed` when it has this kind (deck, dashboard, document, design); ARTIFACT `page` for a deck or a dashboard rendered as one self-contained HTML page; DOCS for a document.
2. **The tools registry**: `python3 scripts/tools_scan.py targets --kind <kind> --any-state` lists every record whose `publishes` carries the kind and that is not `deprecated` — the seed's records when the user has no registry yet — with its stored state and `access` (`tool-registry.md` §7). The skill keeps those whose tools are in its own tool list this session: the session decides, never a stored state, so a record last seen `needs-auth` and reconnected since is a candidate, and one `installed` elsewhere but not reachable here is not. Without SHELL this source is empty.
3. **Confluence**, where the skill's own step already writes there (a report, a handoff page).
4. **The file and the vault** — always where the host keeps files. They are written whatever the answer and stay the source of truth (`native-surfaces.md` §2): a hosted place is one more place to read the result, never the only one.

- **Atlassian Artifacts** arrive through source 2 (the `atlassian` record publishes `deck` and `dashboard`) and only when their operations are reachable (§8). The same record's `page` is Confluence — source 3, `surface: confluence` — never a second candidate.
- **A service reached both as a host surface and as a registry record** (a document service the host offers as DOCS `connector`) is one candidate, recorded under the host capability (`docs`).
- **A board** is a candidate only when its record carries `board` in `publishes` and its tools in this session create frames and stickies and update them by element id (`story-map-protocol.md` §6) — an observed capability, never the record's word. A whiteboard tool that draws diagrams only is not one.

## 3. The order — by audience

The audience comes from the skill's own step — `design-bridge` Step 2, a report for the team, the user's own board — and is never asked for separately. The order is advice: the question (§4) names every candidate, and the first one is marked as recommended.

| The result is for | First | Then |
|---|---|---|
| colleagues — any audience of `deck-subtypes.yaml` other than `customer`, a report for the team | registry records with `access: corporate` (the company's tenant) | the host's surfaces in the user's account |
| the user alone, or the audience is unknown | the host's surfaces in the user's account — the narrowest circle | corporate records |
| people outside the company (`customer`) | «лише файл», marked as recommended | every other candidate, in the order above |

**A primary kind** — when the skill names its result's primary kind (the story map: `board`, because the team edits the map there), that kind's candidates come first; the rest follow the table.

**Already published** — the result's record (§5–§6) names a place → «нова версія» of that place comes first, before any new place.

## 4. One question

One question in the user's language — a multi-choice one where the host can ask it; with one candidate a «так / ні» — names for each place **what** goes (the kind and the internal data it holds), **where** (the surface and the account, tenant or space) and **who can open it there** (`native-surfaces.md` §3). «Лише файл» is always one of the answers. The places chosen in it are one «так» for all of them: it is the question of `native-surfaces.md` §3 («An existing «where to?» question counts»), never asked twice.

> «Куди опублікувати деку «Zorg: нова доставка» (внутрішні дані: метрики воронки й задачі з Jira)?
> 1. Atlassian Artifacts у тенанті компанії — бачиш лише ти, поки не поділишся (рекомендую: дека для команди);
> 2. дека-артефакт у твоєму акаунті — бачиш лише ти;
> 3. лише файл.»

- **A write the host gate does not see is still a write.** Before a Jira or Confluence write and before an Atlassian Artifacts publication, the skill's write checklist (`artifact-style-gate.md` → Host write gate) is part of this one message (`native-surfaces.md` §3, last bullet).
- **A new version names its number** — the record's `version` plus one — and who will see it (§6).
- **«Ні» or «лише файл» is final for the run**: the result stays as the file and the vault copy, and the question is not repeated in the same run.
- **A person's profile is never a candidate**, whatever the answer (`people-context-protocol.md`).
- **A board in the team's root folder** of the board tool may be visible to the team's members by that team's settings — not measured yet, so the question says both («бачиш ти, а можливо — й учасники команди за її налаштуваннями») and the record keeps `unknown`; a board in a space the PM names is seen by that space's members (`shared`).

## 5. Publish and record

After the «так» the skill publishes to each chosen place, saves its note, and then records each place:

```
python3 scripts/publications.py record --key <the result's key> [--note <the note it saved>] [--carry <the note find read>] --surface <surface> --kind <kind> [--level typed|page] --id <id> --url <url> [--audience <audience>] [--remote-version <v>]
```

**One record per result, whichever run saved which note.** The record lives in the result's **key file**, `~/.grow-pm/publications/<key>.yaml`; the note the run saved gets the same list in its frontmatter field `published` (`vault-schema.md` → Context Fields) — a mirror the user sees in the vault, never the place the next run looks. A run that published nothing (an answer «ні» or «лише файл», a scheduled run) leaves the key file as it was, so the chain of versions never breaks; a run without a vault still has its record. The key names the result, never a run, and the skill builds it from what it knows **before** the question:

| Consumer | Key |
|---|---|
| `design-bridge` | `design-bridge/<product>/<deck slug>-<subtype>` — the deck's file name without its date |
| `product-reporter` | `product-reporter/<product>/<mode>-<subject>-<period>` — the board, or the epic of `initiative-status`; `member-review` and `goal-report` keep no record (they name a person) |
| `cjm-research` | `cjm-research/<product>/<mode>-<period>` for the report, `cjm-research/<product>/funnel` for the funnel dashboard — one living dashboard per product, whatever run published the snapshot |
| `focus-advisor` | none: the board keeps its record in its own state file, `~/.grow-pm/focus/board.yaml` (`--note`) |
| `roadmap-architect` | `roadmap-architect/<product>/story-map-<slug>` — one key for the map's board and its progress dashboard, both in one question; the slug is the note's (`story-map-protocol.md` §4) |

Lower-case words (any alphabet), `-` inside a part, `/` between at most four parts; a part as the run names it — a sprint `sprint-42`, a quarter `2026-q4`, a month `2026-11`. A key file the result does not have yet is created by the first `record`; before it exists, the script reads the note given with `--note` — only its entries of the same key, or entries recorded before keys existed — so a deck's own note, an older report's `confluence_url` and a key file lost with `~/.grow-pm` all go on from the vault.

- **`--audience` only for a place recorded for the first time** — a new version keeps the place's audience.
- **`--carry` once, while there is no key file**: when `find` answered from an older note (`source: note`) — the previous report, the deck's note — `record` gets that note as `--carry`, so its places start the key file; after that the key file answers.
- **The mirror goes only into a note this run saved through the vault save** (its gates passed), or into the deck's own note when it lies in the user's own vault and the vault takes writes (`vault-protocol.md`) — never into a core's or a provider's note: there the key file alone records.
- **«Забудь, що я це публікував»** → `publications.py forget --key <key> --surface <surface> --kind <kind>`: the place leaves the record and its mirror; the place itself is not touched.

Each entry of the record:

| Field | What |
|---|---|
| `surface` | `artifact` or `docs` (a host capability), `confluence`, or the id of a tools-registry record (`atlassian`, `google-drive`, `notion` …) |
| `kind` | the kind of §1 |
| `level` | an ARTIFACT's level, `typed` or `page` — on one host they are two places |
| `id`, `url` | the place's id and its link; the link carries no credentials (`publications.py` refuses one that does) |
| `version` | the plugin's own counter for that place: 1, 2, … (a place's own version number, where it has one, is `remote_version`) |
| `published` | the date and time of the latest version, UTC |
| `audience` | `private` · `shared` · `space:<KEY>` · `unknown` — so the next question can say who will see the new version; a personal space is `private` |
| `replaced` | earlier ids of this place, when it had to be created anew (§6) |
| `remote_version` | the place's own version or revision after this publication, when its tool gives one (a Confluence page version) — what §6 compares |
| `key` | the result's key; a note that mirrors two results (a report and its dashboard) keeps each entry under its own, and a lost key file is rebuilt from the note |

- **One entry per place**: a surface, a kind, the level of an ARTIFACT and the host of its link. The same kind on another host (a deck on two hosts' ARTIFACT), or as a typed artifact and as a page on one host, are two places.
- **The older fields read as a record.** A note with `confluence_page_id`, `confluence_url` or a Confluence link in `published_to` (before v4.3.0) is read as a `confluence` record of version 1; they are never rewritten or removed. A `published_to` that is not a Confluence link is not read.
- **A v4.1.0–v4.2.0 `board.yaml`** that names its live board under `artifact_id` (or `board_id`, `*_url`) is read as an `artifact` record of version 1: the old board is refreshed, never orphaned.
- **A note whose own `published` property is something else** (a date, a flag), or one that cannot be written, is never written over; the key file still records, and the result says the mirror was skipped. The Focus Board's `board.yaml` is created by its first record.
- **Copied on, checked again.** An entry or an older field whose link or id would not pass `record` is dropped when it is read to build on, never written on.
- **No FS or no SHELL → no record.** The run publishes, and the next run creates a new place; the skill says so once, at the question.
- **Never a name, never a token.** The record holds no name of anyone it was shared with, no pre-signed or signed link and no URL with a user, a password, a token or a signature in it.
- The script changes only the `published` field of the note and keeps the rest of it byte for byte; it ends with one `PUB_RESULT {json}` line.

## 6. A new version, never a copy

Before the question the skill looks the result up by its key — `publications.py find --key <key> [--note <the deck's own note>]` — and offers each place found as its next version. A result of another period or subject has another key, and its places are new.

| Place | The new version is |
|---|---|
| Atlassian Artifacts | `publishArtifact` with the id of the existing artifact — the next immutable version (§8) |
| ARTIFACT `typed` | a publication to the same link |
| Confluence | an update of the page by its id (`integration-strategy.md` 1c: a fresh `snapshotToken` on v2) |
| DOCS, another registry record's page or document | an update of the same document or page by its id |
| A board | an update of the same board by its element ids — never a new board unless the user chooses one in the question of `story-map-protocol.md` §8, which runs first because people edit the board |

> «Оновити деку «Zorg: нова доставка» в Atlassian Artifacts до версії 2 (внутрішні дані: метрики воронки й задачі з Jira)? Бачиш ти і ті, з ким ти поділився. Так / ні.»

The question names the result as the key does (the deck's title, the report's period) and says who will see the new version from the record's `audience`: `private` — «бачиш лише ти»; `shared` — «бачиш ти і ті, з ким ти поділився»; `space:<KEY>` — «усі, хто читає простір <KEY>»; `unknown` — both of the first two. A new version keeps the place's audience; `record` without `--audience` leaves it as it was.

- **A place people edit** (DOCS, Confluence, another registry record's page) is checked before it is overwritten — a board by reading it back and comparing it with its last state (`story-map-protocol.md` §8), the rest as follows: when its own version is not the record's `remote_version`, or — where it has none — it changed after the record's `published` time (both UTC), or it cannot say, the skill asks one question: «замінити / додати новим розділом / новий документ». A place whose versions are immutable (Atlassian Artifacts, ARTIFACT) loses nothing and needs no such question.
- **A place that is gone** — deleted, or the user has no access any more — is never recreated silently: «Деки в Atlassian Artifacts більше немає — створити нову?». The new place starts at version 1 and the old id goes to `replaced`.
- A surface whose new version the plugin has not measured (ARTIFACT `page`, DOCS `connector`) keeps its record; the next run offers a new version only when the tool takes that id, otherwise it offers a new place and says why, once.

## 7. Sharing — a separate question

Asked after a place that starts private is published (Atlassian Artifacts, an ARTIFACT or a DOCS document in the user's account, a board), never in the same question as the publication (`native-surfaces.md` §3). A Confluence space has no such step: its readers are named in the publication question.

- **To named people, groups or teams only.** The proposal is the user's team from `local-context.md`; the skill finds each person or team through the connector's own people and team search and never invents an id; a name that matches several people is asked about.
- **Once per place.** A place already shared is not asked about again: its next version reaches the same people, and the version question says so (§6).
- **Never everyone with the link, never the whole organisation** — the skill does not set that level, even when asked: the user does it in the place's own interface.
- **The host's own surfaces** are shared by the user in the host's interface; the skill says where in one line.
- After sharing — the share question comes after the record — `publications.py share --key <key> [--note <the same note>] --surface <surface> --kind <kind> --audience shared` sets the record's `audience`: never the names, never a new version. When the skill points the user to the host's own sharing, it sets `unknown`: it cannot know whether they shared, and the next question then says both.

## 8. Atlassian Artifacts

A connector's operations, not a host surface: the Atlassian connector v2 (`integration-strategy.md` 1c) reaches them through `discover` and calls them through `executeWrite` / `executeRead` — there are no top-level tools for them.

1. **Upload.** `createArtifactsUpload` returns a pre-signed upload link; it needs the exact byte length and the base64 SHA-256 of the file, which `python3 scripts/publications.py digest <file>` gives. The bytes go to that link with the headers its result names (`Content-Type` the same as at publishing). The link is a credential for a few minutes: it is never saved, recorded or repeated in the answer.
2. **Publish.** `publishArtifact` takes the upload's `contentId`, a content type — `text/html` (a deck or a dashboard as one self-contained page), `text/markdown` or `text/csv` — a `name` and a `description` of up to 1000 characters that the tenant's search indexes: what the result is and what it is for, nothing the result itself does not hold. With the `id` of an existing artifact it publishes that artifact's next immutable version. Its result — and `getArtifact`'s — gives the artifact's id and its `…/share` link for the record; neither shows a version number (measured 2026-11-02), so `version` is the plugin's own counter. The same result carries a signed `downloadUrl` — a credential, never recorded — and a Confluence embed fragment: putting the artifact on a page is one more place of the question, never automatic. `listArtifacts` lists the user's artifacts.
3. **Share.** `shareArtifact` / `revokeArtifactShare` take named users, groups or teams only, as identity ids (§7): a person found through `lookupJiraAccountId` or `getPeopleInfo`, a team through `searchTeams`. The call is atomic — one wrong audience and nobody is granted; the link by itself grants nothing.

- **Not a candidate without SHELL** (the upload needs `digest` and a byte transfer) or without these operations — and no line about it (§2).
- **The host write gate does not see these operations** — they run through `executeWrite`, which also carries other Jira and Confluence operations. The skill shows its write checklist in the question itself (§4); the hook is not widened.
- **A thumbnail only when the user asks for one** (`createArtifactThumbnailUpload` — it cannot be replaced once made).
- **A dashboard here is a snapshot** of the moment it was published (§9); **a CSV of internal data is a publication too.**

## 9. Dashboards

- **Every number carries its source and date** — the connector, the dashboard or the file it came from, and when — on the page next to the number or in a sources block it points to; a number without a source is not shown.
- **Local data is baked in at render time** — the journal, a snapshot, the vault note: a hosted page cannot read the user's files.
- **Live parts only where the surface re-queries the connectors when it is opened** (ARTIFACT `typed`, `native-surfaces.md` §1), and only for what the result already shows — the statuses of its own issues, its own funnel's numbers — never a new query; everywhere else the page is a snapshot and says its date at the top.
- A dashboard holds no person's profile and no data the result itself does not hold.

## 10. Decks

One deck IR, three renders — a `.pptx`, a self-contained HTML deck, an ARTIFACT `typed` deck — on the product's design system, each through the same QA gate: `design-bridge` Step 5a–6 and its playbook. Publishing an existing deck (its note and its `.pptx`) is a new render of the same content, not new work.

## 11. What never happens

- A publication or a new version without the question; a publication from a scheduled run (`native-surfaces.md` §4).
- A copy where a new version of the same place would do; a silent overwrite of a document or a page someone edited.
- Sharing without its own question, sharing with everyone who has the link or with the whole organisation, an invented person or team id.
- A name, a token, a signed link or a URL with credentials in a record.
- A person's profile on any hosted place.
- A thumbnail nobody asked for.
