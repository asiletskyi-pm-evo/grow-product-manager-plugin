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

`python3 "<plugin root>/scripts/ctx.py" <command> [options] [--context PATH] [--store DIR] [--home DIR]` (the three path options go after the command).

| Command | What it does |
|---|---|
| `status` | where the store is, records, card lines, edits waiting to be imported per kind, conflicts, stray files, the last journal lines; no store → exit 3 |
| `migrate [--apply]` | cuts `local-context.md` into records and proves the compile gives it back byte for byte; lists the records and the `custom` ones. `--apply`: a `pre-migrate` snapshot, then records, state, card and a journal line; the compiled copies are not touched. An existing store → refused |
| `compile` | imports direct edits, then writes both copies (only the ones that differ; a missing vault copy is created), the card and the state; nothing changed → nothing written |
| `sync [--source S] [--reason R] [--resolve ID=file\|record …] [--accept-removals]` | imports direct edits (§4); no store → exit 0 and "nothing to sync" |
| `get ID [FIELD] [--json]` | a record's body, or the value of its first `- **Field:** value` line outside managed regions |
| `list [--type T] [--json]` | id, type, title |
| `set ID FIELD VALUE` | changes the field's line; an absent field goes after the last line of the record's first bullet list; a field that lives only inside a managed region → refused |
| `append ID --text T [--under "#### Heading"]` | adds a line after the last non-empty line of the record or of the named subsection; an identical line is not repeated |
| `add TYPE TITLE [--parent ID] [--after ID] [--body-file F]` | a new `product`, `team`, `org`, `setting` or `custom` record with the right heading, after its last sibling |
| `snapshot [--label L]` | a snapshot of the store and both copies |
| `undo [--steps N]` | back to the state before the N-th last change (a `pre-undo` snapshot first; the journal is kept); right after a migration it removes the store |
| `validate` | records parse, ids match their file names, parents exist, orders are unique, the card fits, required fields (warnings), edits waiting, stray files |
| `card` | regenerates `INDEX.md` only |

**Rules every writing command follows:** take the lock (a live lock younger than 120 s → refused; an older one, or a dead process's, is taken over); refuse a store that lies inside a registered provider's folder (`context-provider-protocol.md` §7); import direct edits first; snapshot; write each file atomically (a temp file, then rename); add a journal line; compile.

**Output contract.** The last stdout line is `CTX_RESULT {json}`; a conflict prints `CTX_CONFLICT {json}` (each conflicting record with the versions) right before it. **Exit codes:** 0 ok · 2 a decision is needed · 3 bad input, no store or an unreadable record (usage errors too) · 4 refused (managed region, provider boundary, busy lock, existing store).

## 4. Direct edits — `sync`

Each compiled copy is cut with the same rules and compared, section by section, with the hashes of the last compile:

- **Changed section**, record unchanged since the last compile → the record takes the section's text.
- **New section** → a new record, placed after the record that precedes it in the file.
- **Renamed section** — a heading disappeared and, after the same preceding record, a new one appeared whose text holds at least half of the old record's non-empty lines → the same record, new `title`, same `id`. Otherwise: a removal plus a new section.
- **Removed section** → the record goes into the snapshot and leaves the store (`ctx undo` brings it back); it is always reported. **Three or more removals in one run** are a conflict until `--accept-removals`.
- **Conflict** — the only case that asks: the same section changed in a copy and in the record (edited in Obsidian), or differently in the two copies. `ctx` exits 2 with both versions; the caller shows them, asks which to keep and re-runs with `--resolve <id>=file` or `--resolve <id>=record`.
- A record edited directly in Obsidian, with no change in the copies, is simply compiled out.
- A copy with no baseline in the state (a mirror that differed at migration) is never a source of edits; the next compile rewrites it, after a snapshot.

## 5. Who writes

`local-context.md` stays the surface for edits; no skill has to learn record files.

- **Context Enrichment** (`local-context-protocol.md`), the **configurator** and **context-connect**: after saving `local-context.md`, when the session digest shows a `context: records …` line and SHELL is available, run `python3 "<plugin root>/scripts/ctx.py" sync --source <writer> --reason "<what was saved>"`; exit 2 → show the two versions, ask, re-run with `--resolve`; no store or no shell → nothing more.
- **Other plugins** that write their own section — unchanged; the next `ctx` run imports their edits.
- **Hosts without SHELL** edit `local-context.md` as before; the next `ctx` run on a host with a shell imports the edits.
- **Moving in** is offered by the configurator — the Update item "Move my context to records" and one question at the end of onboarding — with one confirmation; `ctx undo` right after it moves back.

## 6. The context card

`INDEX.md`, at most 200 lines, regenerated by every compile that changed something: who the user is (name, role, language), onboarding (mode, deferred steps), products (Jira key, Confluence space, platforms), teams (member counts), vaults and providers, then one row per record — id, title, a one-line summary, the date of the last change. A longer table ends with `+N more — ctx list`. People and team-member names never appear (`people-context-protocol.md`): only counts. In v3.11.0 the card is the user's overview; skills start reading it in v3.12.

## 7. The session digest

With a store, the SessionStart digest adds one read-only line: `context: records N · card M lines · in sync` — or `· K edits to import`, or `· C conflicts (ctx sync)`. It is read within a two-second budget so an iCloud download never holds the session start; no store, or any failure → no line.

## 8. Snapshots and the journal

- A snapshot holds the records, the state, the card and both copies, with a manifest and a content hash; an identical newest snapshot is reused. Rotation: the last 20 plus the newest of each day for 14 days. The pre-migration and pre-apply backups in `~/.grow-pm/backups/` (last 5, `persistent-storage.md`) are separate and unchanged.
- `journal.jsonl` — one JSON line per change: `ts`, `op`, `ids`, `source`, `reason`, `snapshot`.

## 9. Hosts

| Capability | Behaviour |
|---|---|
| FS + SHELL (Claude Code, Codex CLI, a Cowork sandbox with the folder mounted) | full: `ctx`, the digest line, the card |
| FS without SHELL | edit `local-context.md` as before; a later `ctx` run on a host with a shell imports the edits |
| No FS (`storage_mode: session`) | no store; the session protocol of `local-context-protocol.md` applies |

## 10. Not yet

Skills reading the card and only their own records, archive and trash, freshness (TTL) and typed fields — v3.12; provider blocks as records with a three-way merge — v3.13; the configurator as a loop and a `/context` command — v3.15; an index and a graph — v4.0.
