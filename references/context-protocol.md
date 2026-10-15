# Context store protocol (since v3.11.0; repositories and provider blocks since v3.13.0)

The user's context can live as **records** — one markdown note per section of `local-context.md` — in a **context store**. `local-context.md` then becomes the **compiled view** of the records: skills read it exactly as before, and anything written into it directly (by a skill, another plugin, or the user in Obsidian) is imported back into the records. The deterministic `ctx` command line (`scripts/ctx.py`) migrates a single-file context losslessly, snapshots before every change, keeps a journal and generates a **context card** (`INDEX.md`). A user who never migrates keeps working exactly as before.

## 1. Where things live

- **Store:** `{storage_root}/_System/context/` — `storage_root` as in `persistent-storage.md`: the first vault in `## Obsidian Vaults` whose sync mode is not `off` → `{vault_path}/{plugin_folder}`; otherwise `~/.grow-pm`.
  ```
  _System/context/
  ├── INDEX.md              # the context card, generated
  ├── records/<id>.md       # one record per section
  └── .state/
      ├── compiled.json     # hashes of the last compile: per record and per section of each compiled copy
      ├── journal.jsonl     # one line per change
      └── blocks/           # since v3.13.0: what the store remembers of each repository's blocks (§5e)
          ├── <repo>.json   #   when it was checked and, per block, its base hash, version, host record
          └── <repo>/<sha>.md   # the base texts
  ```
- **Compiled copies:** `~/.grow-pm/local-context.md` (the canonical one — the digest, the hooks and Step 0a find it) and, when `storage_root` is a vault, `{storage_root}/_System/local-context.md`. `ctx compile` writes both; with a store, `ctx` replaces the manual vault-mirror copy of `local-context.md`.
- **Snapshots** `~/.grow-pm/snapshots/` and the **lock** `~/.grow-pm/.ctx.lock` — outside any vault.
- **The digest's summary** `~/.grow-pm/.ctx-summary.json` (since v3.13.1): the store's counts as the session digest last saw them, for a session start that cannot count them in time (§7). Only beside a context file in a `.grow-pm` folder — never in a folder of the user's own; a cache, never a source of truth.
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
| `undo [--steps N]` | back to the state before the N-th last change, N from 1 (a `pre-undo` snapshot first; the journal is kept); the copies are rebuilt from the restored records, so undoing an import also undoes the imported edit in `local-context.md` (since v3.12.1; the edit stays in the `pre-undo` snapshot) — except when only a compile's own snapshot is undone, whose copies stay as restored; **a record file edited in Obsidian** (since v3.13.0): an import's snapshot holds that edit already in the record while the copies still hold the previous compile, so after the restore a record whose text is not the one the last compile saved a hash for is put back to that compile's text in the home copy (the frontmatter stays) — the edit is undone with the import, the answer lists the ids as `records_reverted` and a line says `put back to the last compiled text (the edit made in the file is undone): <ids>`; a record with no matching section in the home copy (no home copy, or the copy was edited too) is left as it is, never guessed — since v3.13.1 the answer lists such ids as `records_not_reverted` and a line says `not put back (no matching text in local-context.md): <ids> — check them: ctx get <id>`; a record created in Obsidian and imported is not removed by `undo`, and a record file deleted there is not brought back; the block state of the repositories (`.state/blocks/**`) is restored with the rest; refused while edits wait to be imported — `ctx sync` first; right after a migration it removes the store |
| `assign ID all\|none\|S1,S2` | who reads a `custom` or `setting` record in `ctx read` (§5a, since v3.12.1): `read_by` in its frontmatter — `all`, or skill names (folder names under `skills/`; an unknown name → exit 3), or `none` to clear it; another record type → exit 3. A snapshot and a journal line; the copies do not change |
| `validate` | records parse, ids match their file names, parents exist, orders are unique, the card fits, required fields (warnings), edits waiting, stray files |
| `card` | regenerates `INDEX.md` only |
| `invalidate ID --reason R` | marks a record no longer current (§5b): it stays in the copies with a status region after its heading |
| `archive ID [--reason R]` | moves a record to `{store}/archive/<year>/` (§5b); it leaves the copies, its id stays reserved |
| `restore ID` | brings a record back: an invalid one becomes current; else from the archive, else the newest in the trash, at its former place; an id a current record holds → refused |
| `verify [ID …] [--stale]` | marks records verified today (§5d); `--stale` — every stale record |
| `repo list [--json]` | the repositories — the provider registrations a product draws context blocks from (`context-provider-protocol.md` §3b): kind, products, rank, access and, from the block state, the blocks you hold a base for, their base version and the day of the last check (`—` before `provider adopt`, `!` when the state cannot be read, with one line under the table); a registration with no `namespace` earns one `warning:` line. Reads local files, no network. `--json` is accepted and changes nothing (the last line is always `CTX_RESULT`) |
| `repo status [ID] [--json]` | is each repository reachable (a server answers the handshake within 3 s; a core folder is there) and its version on the source — read from the blocks file now, `—` with the reason on a `blocks file:` line when it could not be read — against the version most of your blocks are at; exits 0 also when a repository is unreachable. The only `repo` command that goes to the network |
| `provider adopt REPO [--apply]` | the first base of each block of REPO that is already in your records (§5e); a dry run without `--apply`; with it, imports the edits waiting first, then writes the block state `.state/blocks/**` (after a snapshot) and the card's `Repos` line, never a block's text |
| `provider plan [REPO] [--product P] [--all]` | one table per repository: the sign of every block (`=` `~` `✎` `⚠` `+` `−` `✂` `?` `·`), the questions and the records an apply would rewrite; reads only. Without REPO: the repositories of product P, else all — a paused one and a search-only registration (no `blocks_file`, no core folder) left out with one line each (`призупинено: <id>`, `лише пошук: <id>`). Exits 0, or 5 when a repository is unavailable |
| `provider apply [REPO] [--product P] [--choose BLOCK=theirs\|mine\|both [BLOCK=… …]] [--add BLOCK [BLOCK …]]` | one pass per repository: what needs no answer is applied and your edits stay; a `⚠` or `?` waits for `--choose`, a `+` for `--add`. A snapshot, the records, the block state, one journal line, the compile |

**Rules every writing command follows:** take the lock (a live lock younger than 120 s → refused; an older one, or a dead process's, is taken over); refuse a store that lies inside a registered provider's folder (`context-provider-protocol.md` §7); import direct edits first; snapshot; write each file atomically (a temp file, then rename); add a journal line; compile; drop trash entries older than 30 days. **Write allow-list:** every write or delete target, after its links are resolved, lies under `~/.grow-pm/` or the storage root; anything else → exit 4 and nothing written. `undo` writes only the current copies and store — never a path from a snapshot's manifest. A compiled copy is never replaced or created without a snapshot and a journal line — a compile with nothing to import that still rewrites a copy (a mirror without a baseline, a missing mirror) takes its own. Files are read within a time budget (30 s in all, `GROW_PM_CTX_READ_TIMEOUT`): a record that does not arrive — an iCloud-evicted file still downloading — stops the run with exit 3, naming it, before anything is written. **Since v3.13.0:** `provider adopt --apply` imports first like every writing command (so `ctx undo` across an adopt never takes back an edit made before it), then writes only the block state `.state/blocks/**` (after a snapshot) and the card's `Repos` line — no record of its own; `provider plan` and `repo …` write nothing and take no lock. `provider apply` follows the rules above once per repository: every repository is read first, and one that is unavailable — unreachable, or a blocks file that is empty, cut, foreign or holds none of the blocks you have a base for (`context-provider-protocol.md` §12.2) — stops the run before the lock, with nothing written.

**Output contract.** The last stdout line is `CTX_RESULT {json}`; a conflict prints `CTX_CONFLICT {json}` (each conflicting record with the versions) right before it. **Exit codes:** 0 ok · 2 a decision is needed (`provider apply`: also when answers are awaited — the rest was applied) · 3 bad input, no store, an unreadable or missing record, a value outside its type, an unknown skill for `read`, an unknown repository or block (usage errors too) · 4 refused (managed region, provider boundary, busy lock, existing store, `undo` while edits wait, a target outside the allow-list, a `restore` onto a current id, `provider apply` with only refused blocks left) · 5 a repository is unavailable — unreachable, or its blocks file is no source — and nothing was written (`provider` commands; `repo status` reports it and exits 0). The `provider` result shapes: `context-provider-protocol.md` §12.7; the plan signs: `context-provider-protocol.md` §12.5.

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

**Your own sections (since v3.12.1).** The manifest cannot name a user's own sections, so a `custom` or `setting` record says itself who reads it: `read_by` in its frontmatter — `all`, or skill names (`ctx assign`, or the Obsidian property as a list). `ctx read` adds such a record whole for those skills. A `custom` record without `read_by` is named in one line — `Власні секції без призначення: <title> (<id>), … — ctx get <id>, якщо запит їх стосується` — and the skill reads it with `ctx get` when the request is about it. Output over 8 000 tokens ends with `⚠ ≈N токенів — більше за 8000; найбільший запис: <id> (≈M)`; trimming is the user's call. `validate` and `status` list the unassigned `custom` records; the configurator's Update item "Who reads custom sections" assigns them.

`ctx read --skill S [--product P]` prints the card, then one block per record headed `## <title> · <id> · перевірено <date>`, with `⚠ застаріле (TTL N д)` or `⚠ неактуально: <reason>` when that applies, and one closing line `Відсутнє: …` — `(обов'язкове)` marks the obligatory ones; defaults apply to the rest. Edits not imported yet, and a record missing on disk, are read from the canonical copy with a note (`ctx sync`). Archived records never appear. With several products and no `--product` (or an ambiguous one) the output is the card and the product list — the skill asks (Step 0d) and runs again. Step 0c of `local-context-protocol.md` says when a skill uses it.

**Blocks (since v3.13.0).** A field or a subsection is looked for in the record's own text first — outside the managed regions — and only then inside a repository's blocks. The text of a block is preceded by the line `> [<repo-id> · v<version> · станом на <date>]` (`context-provider-protocol.md` §12.9), so a skill states a fact from a block with its source and date. A record whose file and record disagree (a conflict waiting for `ctx sync`) is headed with `⚠ конфлікт: файл і запис різняться — ctx sync`.

## 5b. Lifecycle — invalidate, archive, trash, restore (since v3.12.0)

- **Invalidate** writes a `ctx` managed region right after the record's heading: `<!-- ctx:begin id=status -->`, `> ⚠ Неактуально з <date>: <reason>`, `<!-- ctx:end id=status -->`. The record stays in the copies, so even a skill that reads the file whole sees it; `status` in the frontmatter follows the region — remove the region and the record is current again.
- **Archive** moves the record file to `{store}/archive/<year>/<id>.md` with `status: archived`, the date, the reason and `former_after` (its predecessor). It leaves both copies; `assign_ids` treats its id as taken. The card counts the archive.
- **Trash** — `~/.grow-pm/trash/<time>-<id>.md`, outside any vault, 30 days: every record a sync removes (a section deleted from the file; a record missing on disk dropped with `--accept-removals`, its text taken from the canonical copy).
- **Restore** — an invalid record becomes current; else the archived record, else the newest trashed one comes back after `former_after`, else after its last sibling, else at the end. The body and both copies come back byte for byte.

## 5c. Typed fields (since v3.12.0)

`references/context-fields.yaml` declares the types of the fields the card and the skills read — `Role`, `Role scope`, `Level home`, `Email` in the profile; `Jira Project Key`, `Confluence Space`, `Platforms`, `Locales`, `URL` in a product; `Mode`, `Deferred steps` in onboarding; the `Judgment` switches. Types: text, enum, list, key, url, date, email, int. The text line stays the source of truth (a `list` may be the bullets under `#### Field`); `validate` warns about a mismatch, `set` refuses one, `get --json` returns the parsed value. An active record carries no `status` key; Obsidian properties a user adds to a record's frontmatter are kept.

## 5d. Freshness (since v3.12.0)

Each record has a `verified` date — set by every write of it through `ctx` (an import, `set`, `append`, `add`, `restore` — not `assign`, which changes only who reads it), by an Obsidian edit of it being picked up, and by `ctx verify`; until then the store's first v3.12 run (`freshness_since`). Default TTL: product and team 90 days; organisation, profile and settings 180; the header, onboarding and custom sections none — `ttl_days` in the frontmatter overrides (`0` = never stale). A stale record: the digest counts it (`· K stale`), the card marks its row (`⚠ <date>`), `ctx read` marks its block, `status` and `validate` list it. A skill states a fact from a stale record as "станом на <date>" and never asks about it mid-run; `ctx verify --stale` or the configurator's "Review stale records" confirms.

## 5e. Provider blocks (since v3.13.0)

A repository's context blocks (`context-provider-protocol.md` §12) are managed regions inside the records. The registrations a store draws them from are listed by `ctx repo list`; `ctx provider plan` compares each block with the repository's text and with the **base** the store remembers, and `ctx provider apply` merges them. What the store remembers lives in `.state/blocks/` (§1), is kept by snapshots, and is brought back by `ctx undo`.

- **Human edits in a block are kept.** An edit inside a block — in `local-context.md`, or in a record file in Obsidian — is imported like any direct edit (§4). Every later refresh keeps it: the plan reads the block as `✎` when the repository did not change it, and asks (`⚠`) when the repository did.
- **Agent edits are not written.** `ctx set` and `ctx append` refuse a target inside a managed region (exit 4), and a skill or the agent never writes inside one by any other path (`vault-schema.md` → Generated regions and layers) — a text typed into a block of `local-context.md` is imported as a human's edit and kept as one. The only writer of a block's text is `ctx provider apply` — for a block the user did not touch (`~`, `−`) or for the answer the user gave (`--choose`, `--add`) — and the record it writes carries the `source` `repo:<id>`.
- **A source that cannot be trusted removes nothing.** A blocks file that is empty, cut, another repository's, or holds none of the blocks you have a base for makes the repository unavailable (exit 5, nothing written) — never "every block removed"; a source behind your base (a lagging copy) is `=` and never takes a block back a version (`context-provider-protocol.md` §12.2, §12.5).
- **Nothing is written to a repository.** `ctx` reads a core folder or a server and writes only under `~/.grow-pm/` and the storage root.
- **Bases come first.** A context that already holds a repository's blocks has no bases; `ctx provider adopt` sets them (§12.4 of the provider protocol) so that the first plan does not ask about every block.

## 6. The context card

`INDEX.md`, at most 200 lines, regenerated by every compile that changed something: who the user is (name, role, language), onboarding (mode, deferred steps), products (Jira key, Confluence space, platforms), teams (member counts), vaults and providers, then one row per record — id, title, a one-line summary, the date of the last change. A longer table ends with `+N more — ctx list`. People and team-member names never appear (`people-context-protocol.md`): only counts. Since v3.13.0 one line `- **Repos:** <id>: <N> блок/блоки/блоків · v<version> · перевірено <date>; <id>: …` about the registered repositories that have blocks in the records, one entry each, joined by `; ` (the version is the one most blocks have a base at; `ctx provider apply` and `adopt --apply` refresh the line though no record changed), and a team's member count falls back to the table of the `team` block when your own team section has none. Since v3.12.0 stale rows end with `⚠ <date>`, with a line counting them and one counting the archive; `ctx read` opens with the card.

## 7. The session digest

With a store, the SessionStart digest adds one read-only line: `context: records N · card M lines · in sync` — or `· K edits to import`, or `· C conflicts (ctx sync)` (a record missing on disk counts as one) — plus `· K stale` when records are stale and `· N custom unassigned` when `custom` records have no `read_by` (since v3.12.1), and tells skills to run `ctx read --skill <name>` at Step 0c. A store used before that cannot be reached (a vault not mounted, moved or switched off) → `context: store at <path> unavailable — vault not mounted?`. It is read within a two-second budget so an iCloud download never holds the session start; no store, or any failure → no line (a count that only misses the budget shows the summary saved last — below). Since v3.13.0 the `providers:` line dates a repository by the store's last check of it when that is later than the registration's `synced_at`: the dates are read from `.state/blocks/` after the store's facts, with half a second of their own, so a block state that does not arrive (iCloud) costs the dates, never the `context:` line; the digest never goes to the network.

**On a cold start (since v3.13.1).** The live count gets two seconds; when it misses them (an iCloud download, an antivirus scan of the records), the digest shows the summary saved last instead, marked with when it was saved — `context: records N · card M lines · <tail> · cached YYYY-MM-DD HH:MM` — with its dates on the `providers:` line, and still tells skills to run `ctx read`. The summary lives in `~/.grow-pm/.ctx-summary.json` (§1): the digest writes it after every live count that came in time, and every writing `ctx` command that exits 0 writes it after its run (a failure to save never changes the exit code); reading commands never write it. A summary older than 7 days, saved for another context file, not JSON, of another schema or without the counts is not used — no line, as before; a live count that fails in time (no store, an error) gives no line, and the cache never stands in for it. The digest still never goes to the network, and reads each provider registration within a second — one that does not arrive is named on the `provider registration unreadable` line as `not available locally (still downloading?)`. `ctx` reads them within three seconds in `repo list`, `repo status`, `provider adopt|plan|apply`, `read` (the line naming a block's repository) and for the card's `Repos` line (every compile, `card`, `migrate --apply`), and a registration it could not read is never silent: `repo list`, `repo status` and `provider plan|apply` without a repository print `unreadable registration: <path> (<reason>)` (and list it under `unreadable` in `CTX_RESULT`); a repository named and not found adds `— a registration could not be read: <path> (<reason>); it may still be downloading`; the card keeps the `Repos` line it has rather than rebuild it from a partial list (after an adopt or an apply: `card not refreshed: a registration could not be read: …`). A writing command's summary is counted on the digest's budget (two seconds, then half a second for the days of the last checks): a count that misses it saves nothing and the summary saved before stands, and days that miss keep the days saved before.

## 8. Snapshots and the journal

- A snapshot holds the records, the state (its subfolders too, such as `.state/blocks/` since v3.13.0), the card and both copies, with a manifest and a content hash; an identical newest snapshot is reused. Rotation: the last 20 plus the newest of each day for 14 days. The pre-migration and pre-apply backups in `~/.grow-pm/backups/` (last 5, `persistent-storage.md`) are separate and unchanged.
- `journal.jsonl` — one JSON line per change: `ts`, `op`, `ids`, `source`, `reason`, `snapshot`. A provider pass adds `op` `provider-apply` (with `from_v`, `to_v`, `decisions`, `pending`) or `provider-adopt`, `source` `repo:<id>`.
- **One snapshot and one journal line per repository.** A `provider apply` over several repositories takes them one after another, so `ctx undo` takes back the last repository's pass only; `ctx undo --steps N` goes back N passes. A crash between the record writes and the journal line leaves the records changed and a snapshot with no journal line: `ctx undo` follows the journal and steps back to the operation before it, so run `ctx provider plan` again — it reads the records as they are.

## 9. Hosts

| Capability | Behaviour |
|---|---|
| FS + SHELL (Claude Code, Codex CLI, a Cowork sandbox with the folder mounted) | full: `ctx`, `ctx read` at Step 0c, the lifecycle, freshness, the digest line, the card, and — with the network — `repo status` and `provider …` (`host-profiles.md` §4) |
| FS without SHELL | Step 0c reads `INDEX.md` and the records the manifest names, whole; edits go to `local-context.md` as before and a later `ctx` run on a host with a shell imports them |
| No FS (`storage_mode: session`) | no store; the session protocol of `local-context-protocol.md` applies |

## 10. Not yet

The configurator as a loop, deltas proposed by skills and a `/context` command — v3.15; checking records against the connectors (`validate --recheck`) — v3.15; an index and a graph — v4.0.
