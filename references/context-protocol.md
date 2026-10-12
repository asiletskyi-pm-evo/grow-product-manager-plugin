# Context store protocol (since v3.11.0)

The user's context can live as **records** — one markdown note per section of `local-context.md` — in a **context store**. `local-context.md` then becomes the **compiled view** of the records: skills read it exactly as before, and anything written into it directly (by a skill, another plugin, or the user in Obsidian) is imported back into the records. The deterministic `ctx` command line (`scripts/ctx.py`) migrates a single-file context losslessly, snapshots before every change, keeps a journal and generates a **context card** (`INDEX.md`). A user who never migrates keeps working exactly as before.

## 1. Where things live

- **Store:** `{storage_root}/_System/context/` — `storage_root` as in `persistent-storage.md`: the first vault in `## Obsidian Vaults` whose sync mode is not `off` → `{vault_path}/{plugin_folder}`; otherwise `~/.grow-pm`.
  ```
  _System/context/
  ├── INDEX.md              # the context card, generated
  ├── records/<id>.md       # one record per section
  └── .state/
      ├── compiled.json     # hashes of the last compile: per record and per section of each compiled copy
      └── journal.jsonl     # one line per change
  ```
- **Compiled copies:** `~/.grow-pm/local-context.md` (the canonical one — the digest, the hooks and Step 0a find it) and, when `storage_root` is a vault, `{storage_root}/_System/local-context.md`. `ctx compile` writes both; with a store, `ctx` replaces the manual vault-mirror copy of `local-context.md`.
- **Snapshots** `~/.grow-pm/snapshots/` and the **lock** `~/.grow-pm/.ctx.lock` — outside any vault.
- There is no pointer file: `ctx` finds `local-context.md` like the digest does (`GROW_PM_CONTEXT_PATH`, then `~/.grow-pm/local-context.md`), derives `storage_root` from it and checks for `{storage_root}/_System/context/.state/`.

## 2. Records

**Split rules.** The file is cut into consecutive fragments that cover every byte exactly once, so the compile gives the file back byte for byte:

1. Everything before the first `## ` heading → the `header` record (the `#` title, `> Generated … Updated …`, `> Configurator version`).
2. Every `## ` heading starts a top-level record that runs to the next `## `.
3. Inside `## Organization: …`, every `### Product: …` and `### Team: …` starts its own record, running to the next `### Product:`, `### Team:` or `## `. Other `###` and deeper headings stay in the fragment they are in.
4. Headings inside fenced code and inside managed regions (`<!-- ns:begin … -->` … `<!-- ns:end … -->`) never split; a region stays in its record's body. **Except:** a region whose begin marker is followed, after blank lines only, by a `## ` heading starts a new fragment at its marker — the section the region wraps becomes its own record, titled by that heading.
5. `### Product:` outside `## Organization:` (for example under `## Landscape`) does not start a record.

**Types.** `User Profile` → `profile`; `Onboarding Status` → `onboarding`; `Organization: X` → `org`; `Product: X` → `product`; `Team: X` → `team`; a heading that starts with `Judgment`, `CJM Configuration`, `Knowledge Library`, `Templates`, `Obsidian Vaults`, `People`, `Planning`, `Focus`, `Release`, `Terminology & Style`, `Landscape`, `Experiments`, `Feedback` or `Custom Sections` → `setting`; any other `##` → `custom` (kept as is — for example a section another plugin writes).

**The record file** `records/<id>.md`:
```markdown
---
ctx: 1
id: "product.zorg-app"
type: "product"
title: "Product: Zorg App"
parent: "org.zorg"
order: 50
owner: "user"
source: "migrated"
modified: "2026-10-20T10:00:00+03:00"
sha: "<sha256 of the body>"
---
### Product: Zorg App
- **Jira Project Key:** PROJ
```
- The body is the section's exact text, blank lines included; the frontmatter is closed by the first `---` line.
- `id` = `type.slug` (`header`, `profile`, `onboarding` have no slug); the slug comes from the heading (Cyrillic transliterated), a repeat gets `-2`. An id never changes, even when the heading is renamed; the file name is the id.
- `order` steps by 10; the compile sorts by it. `parent` links products and teams to their organisation.
- `owner` is `user` or `plugin:<name>` — informational in v3.11.0: migration sets `user`, the user marks another plugin's section in the record's frontmatter.
- `source` is the kind of the last change: `migrated`, `import:home` / `import:mirror`, the command that made it (`ctx-set`, `ctx-append`, `ctx-add`), or the name the writer passed with `--source`.

## 3. The `ctx` command line

`python3 "<plugin root>/scripts/ctx.py" <command> [options] [--context PATH] [--store DIR] [--home DIR]` (the three path options go after the command; `--store` only for reading commands).

| Command | What it does |
|---|---|
| `status` | where the store is, records, card lines, freshness (stale · invalid · archived), the last snapshot, edits waiting to be imported per kind, conflicts, stray files, the last journal lines; no store → exit 3 (a half-migrated one says which folder to remove) |
| `read --skill S [--product P] [--json]` | what skill S reads at Step 0c (§5a): the card plus the records, fields and subsections its entry in `references/context-manifest.yaml` names; reads only — no lock, no writes; an unknown skill → exit 3 |
| `migrate [--apply]` | cuts `local-context.md` into records and proves the compile gives it back byte for byte; lists the records and the `custom` ones. `--apply`: a `pre-migrate` snapshot, then records, state, card and a journal line; the compiled copies are not touched. An existing store → refused |
| `compile` | imports direct edits, then writes both copies (only the ones that differ; a missing vault copy is created), the card and the state; nothing changed → nothing written |
| `sync [--source S] [--reason R] [--resolve ID=file\|record …] [--accept-removals]` | imports direct edits (§4); no store → exit 0 and "nothing to sync"; a record file missing on disk → exit 3, nothing compiled (`--accept-removals` drops it) |
| `get ID [FIELD] [--json]` | a record's body, or the value of its first `- **Field:** value` line outside managed regions; a typed field (§5c) — the parsed value in `CTX_RESULT` (a list for `Platforms`) |
| `list [--type T] [--archived \| --trash] [--json]` | id, type, modified date, title; `--archived` the archive, `--trash` the trash |
| `set ID FIELD VALUE` | changes the field's line; an absent field goes after the last line of the record's first bullet list; a field that lives only inside a managed region → refused; a value outside its type (§5c) → exit 3 with the allowed values |
| `append ID --text T [--under "#### Heading"]` | adds a line after the last non-empty line of the record or of the named subsection; an identical line is not repeated |
| `add TYPE TITLE [--parent ID] [--after ID] [--body-file F]` | a new `product`, `team`, `org`, `setting` or `custom` record with the right heading, after its last sibling |
| `snapshot [--label L]` | a snapshot of the store and both copies |
| `undo [--steps N]` | back to the state before the N-th last change, N from 1 (a `pre-undo` snapshot first; the journal is kept); refused while edits wait to be imported — `ctx sync` first; right after a migration it removes the store |
| `validate` | records parse, ids match their file names, parents exist, orders are unique, the card fits, required fields (warnings), edits waiting, stray files |
| `card` | regenerates `INDEX.md` only |
| `invalidate ID --reason R` | marks a record no longer current (§5b): it stays in the copies with a status region after its heading |
| `archive ID [--reason R]` | moves a record to `{store}/archive/<year>/` (§5b); it leaves the copies, its id stays reserved |
| `restore ID` | brings a record back: an invalid one becomes current; else from the archive, else the newest in the trash, at its former place; an id a current record holds → refused |
| `verify [ID …] [--stale]` | marks records verified today (§5d); `--stale` — every stale record |

**Rules every writing command follows:** take the lock (a live lock younger than 120 s → refused; an older one, or a dead process's, is taken over); refuse a store that lies inside a registered provider's folder (`context-provider-protocol.md` §7); import direct edits first; snapshot; write each file atomically (a temp file, then rename); add a journal line; compile; drop trash entries older than 30 days. **Write allow-list:** every write or delete target, after its links are resolved, lies under `~/.grow-pm/` or the storage root; anything else → exit 4 and nothing written. `undo` writes only the current copies and store — never a path from a snapshot's manifest. A compiled copy is never replaced or created without a snapshot and a journal line — a compile with nothing to import that still rewrites a copy (a mirror without a baseline, a missing mirror) takes its own. Files are read within a time budget (30 s in all, `GROW_PM_CTX_READ_TIMEOUT`): a record that does not arrive — an iCloud-evicted file still downloading — stops the run with exit 3, naming it, before anything is written.

**Output contract.** The last stdout line is `CTX_RESULT {json}`; a conflict prints `CTX_CONFLICT {json}` (each conflicting record with the versions) right before it. **Exit codes:** 0 ok · 2 a decision is needed · 3 bad input, no store, an unreadable or missing record, a value outside its type, an unknown skill for `read` (usage errors too) · 4 refused (managed region, provider boundary, busy lock, existing store, `undo` while edits wait, a target outside the allow-list, a `restore` onto a current id).

## 4. Direct edits — `sync`

Each compiled copy is cut with the same rules and compared, section by section, with the hashes of the last compile:

- **Changed section**, record unchanged since the last compile → the record takes the section's text.
- **New section** → a new record, placed after the record that precedes it in the file.
- **Renamed section** — a heading disappeared and, after the same preceding record, a new one appeared whose text holds at least half of the old record's non-empty lines → the same record, new `title`, same `id`. Otherwise: a removal plus a new section.
- **Reordered sections** → the records take the file's order (the canonical copy's, when both copies moved sections).
- **Removed section** → the record goes into the snapshot and leaves the store (`ctx undo` brings it back); it is always reported. **Three or more removals in one run** are a conflict until `--accept-removals`.
- **A record file missing on disk** (not downloaded yet, not synced yet, or deleted in Obsidian) → nothing is compiled and both copies stay as they are; `ctx` exits 3 naming the files and the way back (let them download; restore them from Obsidian's trash or a snapshot). `--accept-removals` drops them for good.
- **Conflict** — the only case that asks: the same section changed in a copy and in the record (edited in Obsidian), or differently in the two copies. `ctx` exits 2 with both versions; the caller shows them, asks which to keep and re-runs with `--resolve <id>=file` or `--resolve <id>=record`. `file` is the canonical copy, `~/.grow-pm/local-context.md`: to keep the vault mirror's version, or a merge of the two, put that text into the canonical copy first.
- A record edited directly in Obsidian, with no change in the copies, is simply compiled out.
- A copy with no baseline in the state (a mirror that differed at migration) is never a source of edits; the next compile rewrites it, after a snapshot and with a journal line.

## 5. Who writes

`local-context.md` stays the surface for edits; no skill has to learn record files.

- **Context Enrichment** (`local-context-protocol.md`), the **configurator** and **context-connect**: after saving `local-context.md`, when the session digest shows a `context: records …` line — on a host without the digest (Codex CLI): when `{storage_root}/_System/context/.state/` exists — and SHELL is available, run `python3 "<plugin root>/scripts/ctx.py" sync --source <writer> --reason "<what was saved>"`; exit 2 → show the two versions, ask, re-run with `--resolve`; no store or no shell → nothing more.
- **Other plugins** that write their own section — unchanged; the next `ctx` run imports their edits.
- **Hosts without SHELL** edit `local-context.md` as before; the next `ctx` run on a host with a shell imports the edits.
- **Moving in** is offered by the configurator — the Update item "Move my context to records" and one question at the end of onboarding — with one confirmation; `ctx undo` right after it moves back.

## 5a. What a skill reads — `ctx read` (since v3.12.0)

`references/context-manifest.yaml` says, for each skill, what Step 0c needs: from the active product and its teams, fields (a `- **Field:**` line, or the `#### Field` subsection when there is no such line) and `####` subsections; settings by the start of their title, read whole; `required` and `required_settings` mark the obligatory ones. Every skill also gets the User Profile and `Judgment`. The configurator and context-connect are `full: true` — they edit `local-context.md` and read it whole. Validator check 16 keeps the manifest in step with the skills and with "Which Skills Read What".

`ctx read --skill S [--product P]` prints the card, then one block per record headed `## <title> · <id> · перевірено <date>`, with `⚠ застаріле (TTL N д)` or `⚠ неактуально: <reason>` when that applies, and one closing line `Відсутнє: …` — `(обов'язкове)` marks the obligatory ones; defaults apply to the rest. Edits not imported yet, and a record missing on disk, are read from the canonical copy with a note (`ctx sync`). Archived records never appear. With several products and no `--product` (or an ambiguous one) the output is the card and the product list — the skill asks (Step 0d) and runs again. Step 0c of `local-context-protocol.md` says when a skill uses it.

## 5b. Lifecycle — invalidate, archive, trash, restore (since v3.12.0)

- **Invalidate** writes a `ctx` managed region right after the record's heading: `<!-- ctx:begin id=status -->`, `> ⚠ Неактуально з <date>: <reason>`, `<!-- ctx:end id=status -->`. The record stays in the copies, so even a skill that reads the file whole sees it; `status` in the frontmatter follows the region — remove the region and the record is current again.
- **Archive** moves the record file to `{store}/archive/<year>/<id>.md` with `status: archived`, the date, the reason and `former_after` (its predecessor). It leaves both copies; `assign_ids` treats its id as taken. The card counts the archive.
- **Trash** — `~/.grow-pm/trash/<time>-<id>.md`, outside any vault, 30 days: every record a sync removes (a section deleted from the file; a record missing on disk dropped with `--accept-removals`, its text taken from the canonical copy).
- **Restore** — an invalid record becomes current; else the archived record, else the newest trashed one comes back after `former_after`, else after its last sibling, else at the end. The body and both copies come back byte for byte.

## 5c. Typed fields (since v3.12.0)

`references/context-fields.yaml` declares the types of the fields the card and the skills read — `Role`, `Role scope`, `Level home`, `Email` in the profile; `Jira Project Key`, `Confluence Space`, `Platforms`, `Locales`, `URL` in a product; `Mode`, `Deferred steps` in onboarding; the `Judgment` switches. Types: text, enum, list, key, url, date, email, int. The text line stays the source of truth (a `list` may be the bullets under `#### Field`); `validate` warns about a mismatch, `set` refuses one, `get --json` returns the parsed value. An active record carries no `status` key; Obsidian properties a user adds to a record's frontmatter are kept.

## 5d. Freshness (since v3.12.0)

Each record has a `verified` date — set by every write of it through `ctx` (an import, `set`, `append`, `add`, `restore`), by an Obsidian edit of it being picked up, and by `ctx verify`; until then the store's first v3.12 run (`freshness_since`). Default TTL: product and team 90 days; organisation, profile and settings 180; the header, onboarding and custom sections none — `ttl_days` in the frontmatter overrides (`0` = never stale). A stale record: the digest counts it (`· K stale`), the card marks its row (`⚠ <date>`), `ctx read` marks its block, `status` and `validate` list it. A skill states a fact from a stale record as "станом на <date>" and never asks about it mid-run; `ctx verify --stale` or the configurator's "Review stale records" confirms.

## 6. The context card

`INDEX.md`, at most 200 lines, regenerated by every compile that changed something: who the user is (name, role, language), onboarding (mode, deferred steps), products (Jira key, Confluence space, platforms), teams (member counts), vaults and providers, then one row per record — id, title, a one-line summary, the date of the last change. A longer table ends with `+N more — ctx list`. People and team-member names never appear (`people-context-protocol.md`): only counts. Since v3.12.0 stale rows end with `⚠ <date>`, with a line counting them and one counting the archive; `ctx read` opens with the card.

## 7. The session digest

With a store, the SessionStart digest adds one read-only line: `context: records N · card M lines · in sync` — or `· K edits to import`, or `· C conflicts (ctx sync)` (a record missing on disk counts as one) — plus `· K stale` when records are stale, and tells skills to run `ctx read --skill <name>` at Step 0c. A store used before that cannot be reached (a vault not mounted, moved or switched off) → `context: store at <path> unavailable — vault not mounted?`. It is read within a two-second budget so an iCloud download never holds the session start; no store, or any failure → no line.

## 8. Snapshots and the journal

- A snapshot holds the records, the state, the card and both copies, with a manifest and a content hash; an identical newest snapshot is reused. Rotation: the last 20 plus the newest of each day for 14 days. The pre-migration and pre-apply backups in `~/.grow-pm/backups/` (last 5, `persistent-storage.md`) are separate and unchanged.
- `journal.jsonl` — one JSON line per change: `ts`, `op`, `ids`, `source`, `reason`, `snapshot`.

## 9. Hosts

| Capability | Behaviour |
|---|---|
| FS + SHELL (Claude Code, Codex CLI, a Cowork sandbox with the folder mounted) | full: `ctx`, `ctx read` at Step 0c, the lifecycle, freshness, the digest line, the card |
| FS without SHELL | Step 0c reads `INDEX.md` and the records the manifest names, whole; edits go to `local-context.md` as before and a later `ctx` run on a host with a shell imports them |
| No FS (`storage_mode: session`) | no store; the session protocol of `local-context-protocol.md` applies |

## 10. Not yet

Provider blocks as records with a three-way merge — v3.13; the configurator as a loop, deltas proposed by skills and a `/context` command — v3.15; checking records against the connectors (`validate --recheck`) — v3.15; an index and a graph — v4.0.
