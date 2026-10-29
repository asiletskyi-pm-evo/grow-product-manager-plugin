# Changelog — Grow Product Manager Plugin

All notable changes to this plugin are documented here.

Version format: `MAJOR.MINOR.PATCH`
- **MAJOR** — breaking changes, full workflow restructure across multiple skills
- **MINOR** — new skill added, new step/section in existing skill, significant workflow addition
- **PATCH** — wording fix, small content addition, formatting change, bug fix in skill logic

Each skill also carries its own version in the frontmatter (`version:` field in SKILL.md).
When a skill changes, its version is bumped independently. The plugin version is bumped to reflect the highest-impact change among all updated skills.

---

## v4.0.0 (2026-10-29)

**«Вейлт: аудит і граф»: the links of your vault, seen and tidied.** The index now knows every file a link may land on and resolves every link once: `ctx graph` shows what is around a note or an entity, `ctx audit` names what breaks the links of your layer, and `ctx vault normalize` fixes what a machine can — with a report, your code, a snapshot and `ctx undo`. A card's numbers become facts with their period and day, every answer from a note can show the trust of its source, and `ctx serve` gives all of it to a host without a shell as a local MCP server. The last release of the programme «Петля контексту».

MAJOR, by the programme's promise (concept §6 «Ціль v4.0»). **Breaking:** the write gate now asks before a Write, Edit or MultiEdit that changes a generated region of a note in a vault (`<!-- <ns>:begin … -->`) — a flow that edited such a region by hand gets a question; `/grow-product-manager:setup --write-gate off` turns every question of the gate off. Everything else is added: the index gains tables in place (no rebuild), the existing commands answer as in v3.24.

### Added

- **The graph of the index** (`scripts/ctx_graph.py`, `context-provider-protocol.md` §10):
  - `names` — every file a link may land on, an evicted note and a picture too (never a dot-folder), so a link to a note iCloud evicted is no dead link;
  - `edges` (wikilink · embed · fm:<field> · same_as · mention of a Jira key → its work cards) and `unresolved` (dead with the notes of its name as candidates · ambiguous with every note of the name), resolved by the rules of `ctx search --get`; a link lands only in its own vault;
  - built at the end of a refresh that changed something: a changed note's links, the links that name a name that came or went, every note whose hash moved since (an older build sharing the index); everything only when the rules or the work cards change; a fault of the build costs the graph, never the index.
- **`ctx graph <request> [--depth 1|2] [--kind …]`** — hops with `→` / `←` and the kind of each edge, 200 a hop at most; a sensitive note by title and path only and never walked through; the query alone under 300 ms on 6 500 notes.
- **`ctx audit [--all]`** (`scripts/ctx_audit.py`) — orphans, dead and ambiguous links, broken generated regions, missing `type` / `created`, vault backups, cards that disagree on a fact — each fixable or not by the normaliser's own rules; `не перевірено (iCloud): N`; the last result in `~/.grow-pm/audit/last.json`, «нових від минулого аудиту»; `ctx health` lines → the morning brief.
- **`ctx vault normalize [--only …]` · `--apply --code C [--skip N,…]`** (`scripts/ctx_normalize.py`) — in your layer, in downloaded notes only:
  - `frontmatter` — a missing `type` (TYPE_FOLDER_MAP) and `created` (`date`, `created_at`, a date in the file name); an empty key filled in place; never a value changed or a key removed;
  - `links` — an ambiguous name → your layer's note; a moved note → the one note of its name; the text a reader sees stays (`|as written`, `|Note > Heading`, `\|` in a table);
  - `hubs` — an orphan listed in `ctx:hub-<type>` of the hub of its type (or a new `_MOC/<type> — хаб.md`); a People note never;
  - `related` — «Пов'язане» from the Jira keys a note mentions and participants the registry knows by an e-mail, an alias or a link; not where your own scripts keep `related`;
  - `agents` — the region `ctx:agents` of `_System/AGENTS.md`; `bases` — Obsidian Bases tables of the type folders with 5 notes or more, never a People folder;
  - never a core, a copy, the store, an evicted note, a note that is not UTF-8, a code block, another script's region, a note with broken regions or an open code block at its end, a link into another vault; a relative link only to the note it names from its folder; a sensitive note's links are counted, never named; one snapshot, one journal line; `ctx undo` byte for byte, files it created removed, and the audit run again.
- **The registry of generated regions** (`scripts/ctx_regions.py`, `vault-schema.md` → Registry; validate-consistency check 21) and the write gate on regions.
- **Facts and trust** (`scripts/ctx_facts.py`, `ctx_trust.py`, `search-protocol.md` §14) — `actual`, `target`, `value`, `baseline`, `current` of a card (never a person's or a sensitive card) with their period and day; `ctx entity` «факти:» with ⚠ where two cards disagree; trust = source × freshness × state under the provenance line of `ctx search --get` and in its `CTX_RESULT` — shown, never ranked.
- **`ctx serve [--install]`** (`scripts/ctx_serve.py`, `context-provider-protocol.md` §2) — a local stdio MCP server of `vault/v1` over the section index alone (never another tool's local index): the six `vault_*` tools, `brain_status`, `brain_find_entity`; read only, no network; batches; a sensitive note — by its index row or by its file as it is now — without its text or the links its text holds; `--install` writes `~/.grow-pm/bin/ctx-serve`, which `provider sync --if-due` keeps pointing at the plugin's current folder.
- `testing/vault-evals.md`; tests `ctx_graph_test`, `ctx_regions_test`, `ctx_audit_test`, `ctx_normalize_test`, `ctx_facts_test`, `ctx_serve_test` (+ `ctx_vaultenv.py`), cases in `write_gate_test`.

### Changed

- **plugin-configurator 2.17.0** — mode «Vault upkeep» (`maintenance-modes.md` → VU): audit → report → one question → write with the code → `ctx undo`. **context-navigator 0.5.0** — «що пов'язано з X» from `ctx graph`; a card's facts with trust. **context-connect 0.8.0** — §10, the local MCP of your vault. **focus-advisor 0.9.7** — the audit's health line in the brief.
- `/grow-product-manager:context audit`.
- `references/context-protocol.md` §3, §5q, §5s, §9, §10; `context-provider-protocol.md` §2, §10; `search-protocol.md` §14; `vault-schema.md`; `data-policy.md`; `host-profiles.md`; `persistent-storage.md`.

### Acceptance

On a full scratch copy of the author's vault (`Context-Loop-Acceptance.md` §5; 7 309 notes; the real state fingerprinted before and after — no change from the acceptance's calls): index 33 s; `ctx audit` 3 s; `ctx vault normalize` — 219 rows, written in 14 s (178 files, no line removed but rewritten links, the core untouched), then 0 orphans and 0 fixable findings, a second run 0 rows, `ctx undo` — 8 100 files byte for byte; `ctx graph` two hops 9–19 ms; `ctx serve` — 8 tools, a 1-1 note without its text; a real metric card's facts with trust, and ⚠ on a staged disagreement. Found there and fixed: a relative link's choice, a note that is not UTF-8, Bases for People folders, `brain_find_entity` reading another tool's index. Four independent reviews (tasks 1–3, 4–6, 7–9 and the whole branch) found 4 blockers and 22 important defects; each was reproduced, fixed with a test and its mutants killed.

### Known limits

- A note iCloud evicted is neither audited nor fixed: «не перевірено N» (`ctx index rebuild --download`, or «Keep downloaded» in Finder).
- A dead link with no candidate or several stays in the report; the normaliser never guesses, never renames a file, never changes a value (your own types outside the taxonomy are information).
- «Пов'язане» only from strong keys; a note with your own `related` region is left alone.
- Facts only from a card's frontmatter; the trust weights are a heuristic, shown and never ranked.
- `ctx serve` asks neither a core's server nor another tool's local index; a sensitive note comes without its text.
- Bases need Obsidian 1.9+.
- `ctx undo --steps 2` and then `undo` of that undo cannot bring back a hub that was created by one normalisation and grown by the next; an older plugin's `ctx undo` of a normalisation is partial (and says so).
- The `ctx serve` launcher keeps naming an older copy of the plugin while that copy is still on disk.
- The plugin's reader of local indexes calls one shape of a user's own index «unknown» (seen on the author's; v3.24 the same) — a separate task.
- No SHELL — no graph, audit or normaliser; `ctx serve` serves a host that starts a local MCP server.

## v3.24.0 (2026-10-29)

**«Власна копія ядра для MCP»: a core that lives only on a server becomes a folder on your machine.** A registration with an endpoint and no folder of its own can now keep the plugin's own copy of the core in `~/.grow-pm/cores/<id>/` — made in one command, refreshed daily in the background, never deleting a note — and from its first complete pass the plugin reads the repository as a folder: blocks, the team block, search, entities and the bridges' boundary, with no VPN for search and entities.

MINOR: a new folder `~/.grow-pm/cores/` (and `~/.grow-pm/conflicts/`), a new command `ctx repo copy`, lines in `repo status`, `repo list`, `health` and the sync report, two `.md` wrappers in the provider kit; nothing incompatible.

### Added

- **The copy of a core** (`scripts/ctx_copy.py`, `context-provider-protocol.md` §12.12, state `context-copy/1`) — the pattern of a team's own daily sync script, generalised:
  - one `vault_list_by_folder` and every note fetched by twelve clients (a note dropped under them tried once more alone, by the path verbatim as the server listed it); a semantic hash `sha1(canon_json(frontmatter) + "\n␞\n" + NFC(text).rstrip())`, so the YAML the copy writes is never a change; the frontmatter written without PyYAML, one key a line;
  - per note: same (nothing written) · new · updated (the old file into `.backup/<stamp>/`, 30 days) · kept (yours) · conflict (yours stays, the server's into `~/.grow-pm/conflicts/<id>/<day>/`) · failed;
  - **the guard against an incomplete index**: a listing empty or under half of the last complete one is `held` — 0 notes written, 0 moved; a pass with more than max(5, 1 %) failed is `partial` — nothing moved;
  - **never deleted**: a note gone from two complete listings in a row, 20 h apart, moves into `.removed/<day>/`; `--restore` brings it back for good; a case-only rename moves nothing;
  - the target guard: only `~/.grow-pm/cores/<id>/`, `~/.grow-pm/conflicts/<id>/` and the day's report part — someone else's folder, a symbolic link and a registration's folder are refused (exit 4).
- **`ctx repo copy <id> [--now ISO] [--restore PATH]`** — the copy in one command, progress on stderr, one summary line; exit 0 complete / partial / held, 3, 4, 5.
- **The copy as the core folder** — `load_repos` gives an MCP-only registration its complete copy as `core_root` (`core_from: copy`, `copy_at`); `provider plan` says `джерело: копія від <day>`, `ctx search --get` ends its line `· копія від <day>`; the index walks the copy and skips its service folders.
- **The daily pass in the background** — `provider sync` (and `--if-due`), after its passes over the blocks, starts `ctx repo copy <id> --background` for a due copy and never waits; today's sync reads yesterday's complete copy; a change, a move, a held or a partial pass is a part «копія ядра» of the day's report; `copy` in the result.
- **`.md` wrappers of the manifest and the role model** (`scripts/ctx_wrappers.py`, `context-provider-protocol.md` §9) — `kind: provider-file`, `file: <name>`, one fenced block; unpacked in the copy only; `ctx repo kit-check` checks that a wrapper and the file beside it agree; the example kit ships both.
- `ctx health`: ⚠ a copy of a `sync: daily` repository older than 3 days, ⚠ conflicts waiting, ✋ held twice in a row. `testing/copy-evals.md`.

### Changed

- **context-connect 0.7.0** — after registering an MCP-only provider with a blocks file it offers the copy once (a «ні» kept in `.state/copy-offers.json` for 30 days, never in the registration) and gives the request for the core's owner, ready to send (`connect-steps.md` §7). **context-navigator 0.4.4** — an answer from the copy cites «копія від <day>».
- `ctx_store.atomic_write` gives a file whose name is near the file system's limit a short temp name.
- `references/context-provider-protocol.md` §3b, §6, §9, §12.2, §12.8, §12.11, §12.12; `context-protocol.md` §1, §3, §5j, §5q; `host-profiles.md`, `data-policy.md`, `persistent-storage.md`.

### Files

| File | Change |
|---|---|
| `scripts/ctx_copy.py`, `ctx_wrappers.py` | new |
| `scripts/ctx.py` | `repo copy`, the background pass after the sync, the copy's lines in `repo status` / `list` |
| `scripts/ctx_repos.py` | the copy as `core_root`, the team block's reasons for a copy, `search_only` asks the registration |
| `scripts/ctx_index.py`, `ctx_search.py`, `ctx_blocks.py`, `ctx_show.py`, `ctx_kit.py`, `ctx_store.py` | the copy's service folders, «копія від», health, wrappers in kit-check, a short temp name |
| `examples/provider-kit/zorg-core/Core/_System/provider-manifest.md`, `access-bundles.md` | new — the wrappers |
| `references/context-provider-protocol.md`, `context-protocol.md`, `host-profiles.md`, `data-policy.md`, `persistent-storage.md` | §12.12 and the rows |
| `skills/context-connect/` | 0.6.0 → 0.7.0 |
| `skills/context-navigator/SKILL.md` | 0.4.3 → 0.4.4 |
| `testing/ctx_copy_test.py`, `ctx_copy_pass_test.py`, `ctx_copy_wrap_test.py`, `ctx_copy_folder_test.py`, `ctx_copy_sync_test.py`, `provider_kit_test.py`, `mcp_fake.py`, `copy-evals.md`, fixture `copy/` | new and extended |

### Acceptance (the author's real core, read only)

- **One command:** 4 877 notes listed, 4 865 copied in 102 s; the 5 that never arrive are the server's own broken notes (the author's sync script fails on the same).
- **A rerun:** 0 notes written (mtime and size as they were), nothing in the store, no report.
- **Against the author's sync script:** 4 863 notes in both, the semantic hashes equal for **100 %**; what the copy lacks is the personal layer, the bundle's files and the broken notes.
- **The team block:** through the real server `·` with the advice for the core's owner; through a server with the two wrappers, byte for byte the block the folder builds.
- **Search:** recall@50 of the golden set equal with the copy and with the folder (0.863); with the server unreachable, search and entities answer from the copy.
- **Safeguards:** a 40 % listing held with 0 writes; 3 vanished notes moved into `.removed/` after two complete passes and one restored; the background pass started from `sync --if-due` in 1.6 s.
- The real vault, `~/.grow-pm`, the author's sync script's state and folders: 17 609 entries, 0 changes. Found and fixed on the way: a path with an emoji the server keeps in NFD, notes dropped under twelve clients.

### Known limits

- A server with no change dates: every daily pass fetches every note — in the background, 80–120 s for about 4 900 notes on the author's server.
- The team block through the copy needs the two `.md` wrappers from the core's owner; until then it is `·` with the reason.
- The copy is not in `ctx undo`: backups for 30 days, `.removed/`, conflicts. What reaches your records from it goes through `provider apply|sync` with `undo` as ever.
- Obsidian does not see the copy; links from the vault to the core's notes are opened by the plugin.
- The background pass needs a host whose process outlives the command; a pass that is cut resumes in an hour.
- `.removed/` is not emptied by itself; to drop a copy, move its folder to the trash by hand.
- A `~/.grow-pm` that is itself a symbolic link gets no copy (the target guard refuses every write through a link).
- Without a shell there is no copy. A registration with its own folder keeps it: moving from your own sync script to the plugin's copy is a decision for later.
- A server key holding `:` is written quoted and makes the plugin's index read that note without metadata.
- `ctx audit` and the graph over the copy — v4.0.0.

### Backwards compatibility

A registration with its own folder, and one with no copy, behave as v3.23.0 (the whole suite, unchanged, on a frozen copy). New keys only: `copy` in the result of `provider sync` and on a row of `repo list` / `repo status` / `health` with a copy; `core_from` and `copy_at` on a repository that reads its copy.

---

## v3.23.0 (2026-10-28)

**«Оверлей і журнал»: your corrections to a core are declared, and you can read what changed.** A correction you keep to a team's shared core is no longer a prose note to remember: it is an operation in `overlays/<repo>.yaml` beside your store — replace, remove, append, ignore or alias, with the reason in your words — and `ctx` lays it again after every refresh and daily sync. When the core fixes what you corrected, the operation no longer finds its text and you get one question, «прибрати поправку?». A value the core changed that you copied into your own sections arrives in the inbox as a proposal. `ctx history` writes a note a month — Keep a Changelog, «Було | Стало» — of the core's releases and your own changes. The core's team and role for your e-mail are put beside yours with the source of each. And a team that wants to share its context copies the example kit «Zorg» and is connected with one command.

MINOR: new store files (`overlays/`, `history/`, `.state/identity.json`), new `ctx` commands (`overlay`, `history`, `identity`, `repo kit-check | add`), two new actions of `/grow-product-manager:context`; nothing incompatible.

### Added

- **The declared overlay** (`scripts/ctx_overlay.py`, `context-protocol.md` §5n, schema `context-overlay/1`) — `target {block, path}` with four path forms (the whole block, `#Subsection`, `field:Label`, `match:"text"`), `expects`, `reason`:
  - laid into the block's region after every `provider apply`, daily sync and `ctx overlay …`; the base stays the core's text and the block state remembers what the overlay wrote, so a core release over a region you did not edit is `~` with **no question**;
  - `replace` by `value_ref` writes one pointer line to your own subsection — your text is never copied into a block; `ignore` takes the core's text out of the slot (no «також», no divergence; `ctx explain` says why); `alias` adds names to the core's entity card;
  - `expects` ≠ what is found → the operation is **held**: one question interactively, ✋ in `ctx health`, a part of the sync report and a line in the morning brief when nobody is at the keyboard;
  - a region you edited by hand — taking the overlay out too — is yours: never overlaid; a core rule (`policy=rule`) is annotated only (`append`, `alias`); a file that cannot be read, or holds a secret, holds every block that carries an overlay; snapshots keep `overlays/`, `ctx undo` takes a change back.
- **`ctx overlay show | plan [--file] | apply --code | add | rm | answer`** — a draft (`--file`) is how `context-connect` moves a prose note of corrections (`connect-steps.md` §8: the operations, then what did not become one, then one «так»).
- **The core's changes into your sections** (§5o) — a field paired by its place in the diff, or a whole line of 12+ characters, that your own text still holds becomes a `REPLACE` proposal from `ctx-provider`; never a line in a region, under your overlay, rejected before, or a single plain word.
- **The journal with values and `ctx history`** (`scripts/ctx_history.py`, §5p) — every write's journal line carries `changes` (was / became, 300 characters, a secret hidden by kind); a provider pass carries `was`; `history/YYYY-MM.md` is refreshed after every write that added a line.
- **`ctx identity check | keep | take`** (`scripts/ctx_identity.py`, §5r, `.state/identity.json`) — the bundle builder says where the team and the role came from (`team_from`, `role_from`, `role_enum`); a disagreement is two lines with their sources, your answer is kept until the core says something else; `take role` writes the plugin's value into your profile.
- **The example provider kit** `examples/provider-kit/zorg-core/` (manifest, role model, blocks with `slot=` and `policy=rule`, cards, playbook, an overlay example, a README); **`ctx repo kit-check`** names every fault; **`ctx repo add <kit> --email E`** shows team, role, registration and blocks with a code and, with `--apply --code`, connects the kit (`jira_write: ask`, `sync: off` — both are `context-connect`'s questions).
- `testing/overlay-evals.md`; validator check 20 — the example kit stays sound.

### Changed

- **context-connect 0.6.0** — modes «Overlay» and «A kit in one command», identity on a refresh (`connect-steps.md` §1, §8, §9). **focus-advisor 0.9.6** — a held correction in the brief. **context-navigator 0.4.3** — routing to `/context history | overlay`.
- `/grow-product-manager:context` gains `overlay` and `history`; what each action runs moved to `context-protocol.md` §5q (the command is 2.7 KiB).
- `ctx read` / `ctx explain` mark a block the overlay wrote «з твоїм оверлеєм»; `references/context-provider-protocol.md` §7, §9, §12.6, §12.11; `data-policy.md`, `host-profiles.md`.

### Files

| File | Change |
|---|---|
| `scripts/ctx_overlay.py`, `ctx_history.py`, `ctx_identity.py`, `ctx_kit.py` | new |
| `scripts/ctx_blocks.py` | the overlay in plan / apply / sync, `reoverlay`, `core_suggestions`, `was` |
| `scripts/ctx.py` | `overlay`, `history`, `identity`, `repo kit-check | add`, health lines, the changelog after a write |
| `scripts/ctx_resolve.py`, `ctx_entity.py` | `ignore`, `alias`, the `overlaid` mark |
| `scripts/ctx_store.py`, `ctx_ops.py`, `ctx_synced.py`, `ctx_show.py`, `ctx_inbox.py`, `provider_bundle.py` | journal `changes`, `overlays/` in snapshots, the report's part, health, `ctx-provider`, `team_from` / `role_from` / `role_enum` |
| `examples/provider-kit/zorg-core/` | new — the example kit |
| `references/context-protocol.md`, `context-provider-protocol.md`, `data-policy.md`, `host-profiles.md` | §5n–§5r and rows; §7, §9, §12; the store's new files; the prose path |
| `skills/context-connect/` | 0.5.0 → 0.6.0 |
| `skills/focus-advisor/SKILL.md` | 0.9.5 → 0.9.6 |
| `skills/context-navigator/SKILL.md` | 0.4.2 → 0.4.3 |
| `commands/context.md` | `overlay`, `history`; detail to §5q |
| `testing/ctx_overlay_test.py`, `ctx_overlay_merge_test.py`, `ctx_overlay_read_test.py`, `ctx_overlay_cli_test.py`, `ctx_core_suggest_test.py`, `ctx_history_test.py`, `ctx_identity_test.py`, `provider_kit_test.py`, `overlay-evals.md`, fixture `provider-kit-bad/` (new); `validate-consistency.sh` check 20; pins in `ctx_cli_test.py`, `ctx_resolve_test.py`, `ctx_search_test.py`, `provider_bundle_test.py` | |

### Acceptance (a copy of the author's store and core; real data only read)

- **Moving the author's prose note of corrections:** 3 operations (the team's members by the author's own table, a disputed OKR ignored until the core changes it, the team's name as an alias); 5 items of the note did not become operations, each with why. `ctx undo` — records, state and `local-context.md` byte for byte.
- **A core release v0.4 → v0.5:** 8 blocks updated, **0 questions, 1 confirmation**, no block or overlay lost; the core's fixed OKR made exactly one correction held — ✋, then «прибрати». The same release through the daily sync: 0 questions, the report's part, ✋.
- **The core's suggestions:** 0 on the author's data (no value copied from the core), 1 on a constructed copy line. **Identity:** team and role agree on the author's data. **Zorg** from an empty store in one command.
- The real vault, `~/.grow-pm` and the author's local index: 16 862 files, 0 changes. Findings fixed on the way: an overlaid block marked as the author's edit, a noisy changelog, two false identity disagreements.

### Known limits

- A prose note is not parsed by the plugin: `context-connect` drafts the operations, you confirm the report.
- «Було | Стало» exists for changes from v3.23.0 and for the core's releases whose bases are still kept; an edit made in a record file (Obsidian) and imported has no values; earlier lines say only what changed.
- Decisions on conflicts are not written to the decision log; «Playbook — адаптації» is not moved into the overlay (it acts on blocks in your records only).
- Without a shell the overlay is only read by skills in prose; there is no history and no proposal from the core.
- `alias` acts in the plugin's reading only; the core's cards are not changed. `ctx undo` of `repo add` takes the blocks back and leaves the registration.
- A proposal of the core waits until answered, even if the core changes the same value again.
- The repository's own copy of a core served by MCP only — v3.24.0; `ctx audit` — v4.0.0.

### Backwards compatibility

Without an overlay file the plugin behaves as v3.22.0 byte for byte (measured against the v3.22 scripts on a copy). New keys only: journal lines (`changes`, `was`, `overlay`, `overlay_held`, `proposed`), the block state (`overlay_sha`, `overlay_of`), the snapshot manifest (`overlays_known`; a v3.22 snapshot leaves `overlays/` alone). v3.22 code on a v3.23 store loses nothing: an overlaid region reads as your edit. The inbox stays `context-inbox/1`; the index stays `search-index/1`.

## v3.22.0 (2026-10-28)

**«Конфігуратор-петля»: the configurator reads first and asks at most five questions.** Setting up the plugin no longer starts with an interview of seventeen steps. The configurator reads your connectors read-only and `ctx bootstrap` shows what they say as one table, with the source and the confidence of every field; Basic is at most five decisions, and saving creates the context store with the source of every field. Once a week your records are checked against the connectors, and `consolidate` tidies them — both only as proposals of the inbox. The second release of the programme «Петля контексту».

MINOR: new `ctx` commands (`bootstrap`, `validate --recheck`, `consolidate`), a new delta (`REPLACE`), a new onboarding order, two new actions of `/grow-product-manager:context`.

### Added

- **The observation file** (`scripts/ctx_observe.py`, `references/context-observe.md`, schema `context-observed/1`): what a skill saw in the connectors, read-only — `ctx` itself calls no connector.
  - **Confidence is decided by `ctx`, not by the skill**, from where a fact came: high — who you are by Atlassian, the site, your mail's domain, your file, your answers; medium — your activity in Jira (≥ 5 issues in 90 days) and Confluence (≥ 3 pages), the role a provider infers; low — co-attendees (≥ 3 meetings in 30 days), Fireflies participants, Tableau.
  - **Each source gives only its own** (a table held equal to the document by a test), and a value must have its field's shape — a meeting's title or a letter's subject has none. Of a calendar, Fireflies or mail fact only a count is kept.
- **`ctx bootstrap --observed F`** (`scripts/ctx_bootstrap.py`, `context-protocol.md` §5k) — one table, read-only:
  - `+` absent, `~` another value, a new organisation, product or team with its fields; what agrees is only counted;
  - never taken by default: `✋ твоє` (another value against one you gave), `⚠` (two values for one field), `≠ назва` (an organisation named otherwise), `немає організації`;
  - your answer outranks every connector; a product is known by its Jira key or Confluence space before its name; a field and its older names agree (`Jira` / `Jira instance`, `Email` / `Work Email`).
- **`ctx bootstrap --apply --code C [--take|--skip|--only]`** — every check under the lock first (the code before and after the edits waiting are imported); one snapshot, the records, the sources, the low facts as `ctx-bootstrap` inbox deltas, one journal line, the compile; `ctx undo` byte for byte. Nothing new → nothing written. **A new user** gets `local-context.md` from the onboarding skeleton, moved into records at once.
- **The source of every field** (`scripts/ctx_sources.py`, `.state/sources.json`, `context-sources/1`): what wrote it, where, when, how sure, with a hash of the value; every rewrite keeps the fields it did not touch; an import makes the fields it changed the editor's; `ctx show <id>` prints it beside each field.
- **Basic in ≤ 5 questions** (`onboarding-steps.md` «Basic — derive first»): the scan, then «це ти?», role, products, team, the table — each with its progress and the skills it feeds, skipped when the table already knows; the mode question is gone (the full setup and the sandbox on request).
- **`ctx validate --recheck --observed F`** (`scripts/ctx_recheck.py`, §5l, `.state/recheck.json`) — a product's key and space, a team's members, the role a provider gives:
  - a finding becomes a `ctx-recheck` delta only on a second look at least 6 days later (the day of a look is the file's `at`); a connector that did not answer or a list that was cut checks nothing;
  - a product is closed only when every anchor is gone and no project of its name appears under another key (then it is an UPDATE to that key); a key is compared without case and through a link; a member is removed only when the site shows the account deactivated, never when a lookup finds no one;
  - weekly in the focus-advisor morning brief, on request through `/context recheck` and the configurator's Validate.
- **`ctx consolidate`** (`scripts/ctx_consolidate.py`, §5m) — a line written twice in one section, a relative date made absolute (never a standing rule like «data up to yesterday»), a deadline passed after «до» / "by" / "until" — `ctx-consolidate` REPLACE deltas, never a write; `ctx health` says how many it would find.
- **`REPLACE`** — a delta that changes one line or removes it, within its section when it names one; urgent as an UPDATE of its field would be; ctx's own proposers (`ctx-bootstrap`, `ctx-recheck`, `ctx-consolidate`) are refused to `ctx propose --skill`.
- `testing/bootstrap-evals.md` — Basic's scenarios; `skill_lint` checks 28 `[bootstrap-template]` (the skeleton equals Step 16c) and 29 `[command-size]` (a command over 4 KiB is not migrated by Codex CLI).

### Changed

- **plugin-configurator 2.16.0** — Basic derives first; Step 2 on request; Validate V-5b rechecks. **focus-advisor 0.9.5** — the weekly recheck in the brief. **context-navigator 0.4.2** — «перевір мій контекст», «прибери дублі в контексті».
- `ctx append` puts a table row inside its table; `ctx set` / `append` / `add` / `inbox accept` note sources; `ctx health` names the last recheck and what consolidate would find.
- `references/context-protocol.md` §5k–§5m, the command rows, the store's tree, §10; `data-policy.md` — what the connectors read is kept to a field's need; `host-profiles.md` — the prose path without a shell.

### Files

| File | Change |
|---|---|
| `scripts/ctx_observe.py`, `ctx_bootstrap.py`, `ctx_sources.py`, `ctx_recheck.py`, `ctx_consolidate.py` | new |
| `scripts/ctx.py` | `bootstrap`, `validate --recheck`, `consolidate`, sources in `set` / `append` / `add` / `inbox accept` / `show`, `health` lines |
| `scripts/ctx_inbox.py` | `REPLACE`, ctx's own proposers, every line break refused |
| `scripts/ctx_ops.py`, `ctx_store.py`, `ctx_show.py` | sources on import, invalidate, restore; a table row inside its table; health lines |
| `references/context-observe.md` | new — the read-only call map |
| `references/context-protocol.md`, `data-policy.md`, `host-profiles.md` | §5k–§5m, rows, §10; the connectors' reach; the prose path |
| `skills/plugin-configurator/` | 2.15.3 → 2.16.0 — Basic derives first, V-5b |
| `skills/focus-advisor/SKILL.md` | 0.9.4 → 0.9.5 — the weekly recheck |
| `skills/context-navigator/SKILL.md` | 0.4.1 → 0.4.2 — recheck and consolidate in words |
| `commands/context.md` | `recheck`, `consolidate`; under 4 KiB |
| `testing/ctx_observe_test.py`, `ctx_sources_test.py`, `ctx_bootstrap_test.py`, `ctx_replace_test.py`, `ctx_recheck_test.py`, `ctx_consolidate_test.py`, `bootstrap-evals.md`, fixture `bootstrap/observed-zorg.json` (new); `skill_lint.py`, `ctx_cli_test.py`, `ctx_search_test.py` | the tests and pins |

### Acceptance (a copy of the author's store; the author's real connectors read-only)

- Atlassian read-only (user, site, 90 days of Jira and Confluence activity, every visible project and space, the team's five members). The table on the author's context: 6 facts agree, 1 row (another mail domain) held as `✋ твоє` + `≠ назва`; an apply with nothing taken wrote nothing; `--take 1` then `ctx undo` byte for byte.
- `validate --recheck`, two looks a week apart: **0 findings, 0 false INVALIDATE, 0 false REPLACE**. `consolidate`: 0 proposals on 19 records.
- A new user from an empty HOME with the author answering: **4 decisions, 2 min 43 s** from the start to the first artifact (≈ 6 min with the scan); 21 of 21 fields with their own source.
- The real vault, `~/.grow-pm` and the author's local index: 17 563 files, 0 changes. `host-smoke`: Claude 33 skills + digest, Codex 40 (33 + 7).

### Known limits

- Fireflies gives participants only — no meeting titles or topics are kept (a deviation from the concept).
- Without a shell the sources of fields are not kept — the table shows them only while setting up.
- A recheck closes a product only after two weekly looks and only when every anchor is gone; a member is never removed on «not found»; the role check reminds you each week when you chose another role than the provider's.
- `consolidate` archives nothing itself (it names `ctx archive`); a relative date's proposal follows the record's last change, so a rejected one may come back after the record changes.
- Several organisations: new products and teams go under the first. The extended setup stays a dialogue, section by section.
- The core's suggestions into your sections — v3.23.0; `ctx audit` — v4.0.0.

### Backwards compatibility

The index schema stays `search-index/1`; the inbox stays `context-inbox/1` with one more action (`REPLACE` — an older `ctx` refuses an inbox that holds one). Nothing new is written unless you apply a table with its code, a recheck or consolidate proposes, or you accept. A host without a store or a shell keeps the onboarding of v3.21.0, with the same reads shown in prose.

## v3.21.0 (2026-10-27)

**«Скринька»: what skills learn about your context waits for your «так».** A skill that learned something about your context — a dashboard the product record lacks, a Jira key that moved, a product that closed — wrote it in silence or asked «зберегти?» at the end of a run. Now it proposes a delta, and the inbox keeps it: the urgent ones are asked at once in one question, the rest wait for one answer in the morning brief or `/grow-product-manager:context inbox`. A secret or a state or financial identifier never reaches the store. The first release of the programme «Петля контексту» (the configurator as a loop, the declared overlay, a core's own copy for MCP-only repositories, the vault's audit and graph follow).

MINOR: new `ctx` commands (`propose`, `inbox`, `show`, `health`, `snapshot import`), a new typed command, a new end-of-run step in every skill.

### Added

- **The inbox** (`scripts/ctx_inbox.py`, `context-protocol.md` §5i, `.state/inbox.json` schema `context-inbox/1`):
  - `ctx propose --skill S --delta JSON` — ADD a line, UPDATE a field (typed fields checked), INVALIDATE a record, NOOP «checked, still so»; the same change from two skills is one entry with the newest evidence; two values for one field are both kept and marked `⚠`; a rejected delta is remembered 180 days; a delta to a provider's block, a missing record, a heading or a region marker as a line, a skill the plugin does not have, a People-contour skill → refused;
  - **urgent by a table, not by the skill**: any INVALIDATE, the profile's identity (`Name`, `Role`, `Role label`, `Role scope`, `Level home`, `Email`, `Work Email`, `Language`), an organisation's `Domain`, `Jira`, `Confluence`, `Jira instance`, `Confluence instance`, a product's `Jira Project Key`, `Confluence Space`, `URL`, any change to a team;
  - `ctx inbox list` (numbered, `терміново` · `⚠` · `!` the record changed since, a code) and `ctx inbox accept|reject <N…|all> --code` — another code means the inbox changed since it was shown (exit 4); accept re-checks each delta (already so → taken quietly; the record gone → out; a field you changed since, a heading gone, both values of one field, a secret → held and said); one snapshot, one journal line, `ctx undo`;
  - a proposal takes no snapshot (a run of every skill would rotate real ones out) and is no undo step; `ctx undo` of any change, `--steps N` too, keeps what was proposed after it.
- **The end of a run in every skill** — one line before each `## Routing`: what the run learned goes to the inbox (`context-protocol.md` §5i); the People contour proposes nothing («no deltas»). `skill_lint` check 27 `[inbox-step]`. Without a store or a shell a skill asks «Зберегти?» as before (Context Enrichment).
- **What the store never keeps** (`scripts/ctx_never.py`, `data-policy.md`): a card number (a network's range and length, Luhn), an IBAN (mod 97), a РНОКПП (its checksum and word), a passport number (beside its word), keys and tokens by form (`sk-…`, `gh?_…`, `glpat-…`, `xox?-…`, `AKIA…`, `AIza…`, `ya29.…`, a bot token, a JWT, a private key, `Bearer …`, a password in a URL or `key=` in a query, a labelled password) — refused by every writing command and every delta with exit 4, naming the kind, never the value; your own edit is imported and `validate` / `health` name the record and the kind. Health, religion, politics, family matters — a rule for skills.
- **`ctx show`** — what the plugin knows about you: a line a record (who wrote it last, when, verified, `застаріле` / `неактуальне`, who reads it), the repositories' blocks, your answers, the inbox, edits waiting.
- **`ctx health`** — ✅ / ⚠ / ✋ a line, each with the command that fixes it: stale and invalid records, store errors, edits waiting and conflicts, a secret in your text, the inbox, each repository's last sync, an unreadable registration or memory, the search index's age and the files iCloud has not downloaded, the snapshots, and the copies outside them (a line per kind; sizes by stat alone).
- **`/grow-product-manager:context show | health | inbox`** — the seventh typed command; context-navigator 0.4.1 answers the same words in conversation («що ти про мене знаєш», «що в скриньці»).
- **`ctx snapshot import [--apply --code]`** (`scripts/ctx_backups.py`) — the old backups of `local-context.md` under `~/.grow-pm` become `<their time>-imported` snapshots (never rotated, named for the time the backup's name carries), the originals go to the trash; a zip, a section, a yaml, a file holding a secret are left and said; the journal line is written before anything moves, so `ctx undo` takes back whatever part was done, and a snapshot is removed only when its original's text is back in its place.
- **focus-advisor 0.9.4** shows the inbox in the morning brief (one question; headless: the lines only).
- `testing/inbox-evals.md` — the expected deltas of ten skills.

### Changed

- `references/local-context-protocol.md` «Context Enrichment» points to the inbox; its old way stays for a host without a store or a shell and for «запам'ятай X».
- `ctx undo` also puts back the old backups an import moved, and keeps the inbox's later proposals.
- `skill_lint`'s taxonomy check reads a folder that starts with `_` (the `moc` row was there all along); `validate-consistency.sh` counts the host matrix's summary line and README's «Per-skill result» row from the matrix (README said 31 · 15/16 · 21/10 · 22/9), and checks README's Commands row.
- `references/context-protocol.md` §10 — the programme's next releases.

### Files

| File | Change |
|---|---|
| `scripts/ctx_inbox.py`, `ctx_never.py`, `ctx_show.py`, `ctx_backups.py` | new |
| `scripts/ctx.py` | `propose`, `inbox`, `show`, `health`, `snapshot import`, the guard over every writing command, `ctx undo` (inbox, backups) |
| `scripts/ctx_ops.py` | `rotate` and `restore` leave imported snapshots alone |
| `commands/context.md` | new — `/grow-product-manager:context` |
| `skills/*/SKILL.md` (33) | the end-of-run line |
| `skills/context-navigator/SKILL.md` | 0.4.0 → 0.4.1 — show, health, inbox |
| `skills/focus-advisor/SKILL.md` | 0.9.3 → 0.9.4 — the inbox in the brief |
| `references/context-protocol.md`, `local-context-protocol.md`, `data-policy.md`, `host-profiles.md`, `persistent-storage.md` | §5i, §5j, the command rows, exit 4, §8, §10; Context Enrichment; what the store never keeps; hosts; the recovery ladder |
| `testing/ctx_inbox_test.py`, `ctx_never_test.py`, `ctx_show_test.py`, `ctx_snapshot_import_test.py`, `ctx_testenv.py` (new), `skill_lint.py`, `validate-consistency.sh`, `inbox-evals.md` (new), `trigger-evals.md`, `ctx_cli_test.py` | tests, check 27, the host-matrix check |

### Acceptance (a copy of the author's store, `~/.grow-pm` and backups)

- Ten skills' end-of-run step on the author's records: 10 entries, 5 urgent by the table, a core's block refused; `accept all` changed exactly 10 lines; `ctx undo` byte for byte.
- The filter: 0 hits on the author's records; in 4 990 downloaded vault notes 0 in their own layer and 216 lines of a shared core — real tokens (JWT, `Bearer`, `?token=`) in pages taken from a wiki.
- `show` 0.3 s, `health` 0.4 s, nothing changed; `snapshot import`: 17 snapshots byte for byte, 17 originals to the trash, `ctx undo` byte for byte.
- The real vault, `~/.grow-pm` and the local index: 0 changes from the acceptance.

### Known limits

- A delta creates no record (a new product or team comes from the configurator, v3.22.0); INVALIDATE closes a whole record, not a line.
- The core's suggestions into your sections (v3.23.0), `validate --recheck` (v3.22.0) and `ctx audit` (v4.0.0) do not propose deltas yet.
- The ten skills' deltas are checked by `testing/inbox-evals.md` by hand, not by a script.
- A conflict while importing your edits stops `propose` (exit 2) — the skill says so; the deltas are proposed again on the next run.

### Backwards compatibility

The index schema stays `search-index/1`. Nothing new is written unless a skill proposes (the inbox only) or you accept, reject or import with a code. A host without a store or a shell keeps «Зберегти?» as before.

## v3.20.0 (2026-10-26)

**«Мости в нотатках»: the bridges your notes lack, written on your «так».** Since v3.18.0 `ctx entity` knows that your person note and a core's card are one person when an e-mail or your `same` answer joins them — but nothing in your note said so, and Obsidian, your scripts and other tools did not see the join. `ctx entity apply` reports the bridges your layer lacks and, only on your «так» to that report, writes them: one frontmatter line per note, a snapshot first, `ctx undo` to take it back. It is the only command of the plugin that writes into your notes, so it is the last release of the Context Core programme. Also: the plugin's card in Claude shows one sentence instead of 5 089 characters of history.

MINOR: a new command (`ctx entity apply`) that writes into your notes, and a new behaviour of `ctx undo`. (Planned as v3.18.2, then v3.19.1 — the version follows the change.)

### Added

- **`ctx entity apply`** (`scripts/ctx_bridges.py`, `context-protocol.md` §5h):
  - **a dry run** lists, for a card of yours that an e-mail or your `same` joins *directly* to a card of another source and that has no bridge to its entity yet, the line `same_as: "[[<card>|<title>]]"` — one link, the shape the registry itself reads as a bridge — to the strongest such card (a core's by rank, then a local index's) in the same vault. A name or a «maybe the same» pair never makes one; a `not-same` pair never gets one;
  - **what it skips, and why**: `уже мають міст` (any field, your scripts' too), `уже має same_as, але його ціль не знайдено`, `межа запису: …` (a note `--apply` would refuse), `картка поза вейлтом`, `нотатку не прочитано` / `не завантажено з iCloud — завантаж: ctx index rebuild --download`; then `код звіту: <8 hex>`;
  - **someone else's field**: a `same_as` in your layer the plugin did not write (`.state/bridges.json`, schema `context-bridges/1`) — in a note on disk, or one iCloud keeps that your local index gives — means your own scripts keep it: no bridge at all, said once;
  - **`--apply --code <code>`** writes that report alone (another code: exit 4, nothing touched): into your plugin folder and the storage root, never a core — a registered one, one inside your plugin folder in any letter case, one a registration file names even when it does not parse, a folder with a core's manifest or `.git` —, never `_System/`, the store or through a symlink; a note changed meanwhile is skipped; the line goes last in the frontmatter the index reads (`---` or `...`), in the note's own line ending, the note written in place — its mode, extended attributes and inode kept; one journal line `op entity-apply` with each note's hashes, a snapshot of the notes (0600);
  - **context-navigator 0.4.0** writes bridges only when asked («запиши мости в нотатки», «зв'яжи мої нотатки з ядром»): the report, one question, `--apply --code` on your «так», then `Скасувати: ctx undo`.

### Changed

- **`ctx undo`** puts back the notes `entity apply` wrote: byte for byte from the snapshot when untouched, else our line alone (your edits stay), else `не повернуто: <path> — …`; the journal's history is written back before any note; `ctx undo` of the undo writes the bridges back; a note renamed since keeps our line ours.
- **The plugin's description** (`plugin.json`, the marketplace entry, the Codex manifest) is one sentence of 182 characters; the component counts live in README alone. `validate-consistency.sh` check 1 keeps it one sentence ≤ 200 characters with no count, no version, no `**`; release-manager 0.4.2 no longer writes a version tail.
- **The deferred minors of v3.19.0:** a row `«Ім'я, Ім'я — роль»` of a team card's people — in a table, as `**Lead:** A, B` or as the cores' own `**A, B** — роль` — gives one item per person when every name is exactly one person, and `ctx read` prints each as `<person> — з рядка «…»`; a repository card whose registration gives no rank is the last of the repositories in the cascade; `ctx entity` and `entity apply` on an index another process holds answer in about 6 s instead of 26–32 s.

### Files

| File | Change |
|---|---|
| `scripts/ctx_bridges.py` | new: the plan, the ledger, the write, the undo of notes |
| `scripts/ctx.py` | `entity apply`, `ctx undo` of notes, usage text |
| `scripts/ctx_ops.py` | `snapshot(notes=)` |
| `scripts/ctx_index.py` | `Index.field_links`, `busy_once` + `probe` |
| `scripts/ctx_entity.py` | the registry's own answers for the plan; busy once |
| `scripts/ctx_eslots.py` | rows of several people; unranked registrations |
| `skills/context-navigator/SKILL.md` | 0.3.2 → 0.4.0 — «Bridges in your notes» |
| `skills/release-manager/SKILL.md` | 0.4.1 → 0.4.2 — no description tail |
| `references/context-protocol.md`, `data-policy.md`, `host-profiles.md` | §5h, the journal, the commands table; bridges carry identity alone; needs FS + SHELL |
| `.claude-plugin/*.json`, `.codex-plugin/plugin.json` | one-sentence description |
| `testing/ctx_bridges_test.py` (new), `ctx_eslots_test.py`, `validate-consistency.sh`, `test-cases.md` | tests, the description check |

### Acceptance (a copy of the author's vault, local index and store)

- **The author's data as it is:** 0 bridges to write — 178 notes «уже мають міст» (the bridges their own normaliser keeps); 646 person cards → 465 people, 0 doubles.
- **Without the normaliser** (its field taken out of the copy): 178 bridges, all by e-mail, all to the core; `--apply`: exactly 178 notes changed, one line each, the core's folder 0 changes; the next report 0; `ctx undo`: every note byte for byte.
- One hand-written `same_as`: 0 bridges, said. An edited note: undo takes our line alone.
- A busy index: 7.2 s / 6.3 s (exit 5, nothing written). Members of 39 core teams: 0 lost, +1; `ctx read` identical.
- The real vault, `~/.grow-pm` and the local index: 0 changes from the acceptance.
- Findings fixed during the acceptance: the author's notes iCloud keeps were taken for another source (never a bridge's target now, and said with `ctx index rebuild --download`); the cores' `**A, B** — роль` was taken for a label.

### Known limits

- A `same_as` written as text (no link) in a note that is no row of the report is not seen.
- A process killed in the middle of the writes leaves the notes written so far with no journal line; the snapshot holds them.
- On a vault iCloud mostly keeps, notes of yours that only a local index gives are checked by their frontmatter but get no bridge until downloaded (`ctx index rebuild --download`).

### Backwards compatibility

The index schema stays `search-index/1`, `meta_version` 4 — no re-read. Nothing writes into a note unless you run `entity apply --apply` with its report's code. `ctx undo` of anything else works as before. A CTX_RESULT of `ctx undo` gains `notes_reverted` and `notes_not_reverted`.

## v3.19.0 (2026-10-26)

**«Слоти з однієї сутності»: a person's role, a team's members — one answer from every card.** A person has a note of yours, a core's registry card and maybe another team's card; a team has its core card, your team record and every person whose `team:` names it. Until now a skill read one of them, or read them all and saw one person twice. Now an entity's slots — `person.role`, `person.team`, `person.email`, `team.members`, `team.missions`, `team.parent`, `mission.teams`, `mission.jira_projects`, `*.owner` — are put together from all of its cards by the cascade of the records (yours, then the cores by rank, then a local index's card, then what other cards say), each piece with where it comes from and its date, and a list is one line per person. `ctx read`'s `team.members` is joined the same way, and the 14 skills that work with people find a person through `ctx entity`, never by a file name.

MINOR: new slot ids, new `ctx entity` flags (`--slot`, repeated `--q`), new behaviour in 14 skills. (Planned as v3.18.1 — the version follows the change.)

### Added

- **Slots of one entity** (`scripts/ctx_eslots.py`, `context-protocol.md` §5h, catalogue `context-slots.yaml` with `answered_on: cards`):
  - a card answers a slot by a frontmatter field of the slot's names, else — never on a person's card, never on a sensitive note — by a section of those names (`Склад команди`, `Місії (матриця …)`, its sub-headings too);
  - a list keeps the items that name an entity — a link, an e-mail, a name exactly one card carries — so a table of roles under `## Люди` is no member;
  - **derived:** a person whose *winning* `person.team` names a team is one of its members; a team's missions and a mission's teams answer each other;
  - **cascade:** a value is the first, the others `також: <value> (<whose> · <path> · <day>)`; a list is one item per entity with every origin, `лише виведене` when only the derivation names it;
  - `ctx slot prefer|decide|bind|map` do not reach a card's slot; outside the People contour a person's slots are their identity alone, and a sensitive team's card gives names and sources only.
- **`ctx entity`:** one entity's `слоти:`; `--slot <id>` (repeatable) for the slots alone (no backlinks, no mentions; an unanswered one `—`); `--q` repeated — several requests, one refresh of the index.
- **Hints of a local index** that keeps its own `entities`/`edges`: a pair `можливо той самий: … (підказка <id>)` closed by your `same`/`not-same`; a backlink line ` · <id>` from a note the plugin's index does not hold. Never a merge, never a slot.
- **`people-context-protocol.md` → «Find a person — `ctx entity`»:** e-mail first; several → ask, never pick; a near match is no match; only a core's card → a profile seeded with the identity and a one-link field (shown as a diff first); a team's people by `--slot team.members`; without SHELL — as before.

### Changed

- **`ctx read` — `team.members` one line per person:** the record's items, its team card's members and the members derived from the cards joined by entity (a name in another spelling of a person the list's other sources name: `схоже ім'я`); a section's prose and sub-headings follow, nothing lost; a team with no members of its own gets its card's. A core rule or `prefer repo:` prints as before with `з карток ще N`; a busy or absent index prints as before. `ctx entity <team> --slot team.members` gives the same composition.
- **14 skills find people through `ctx entity`** (patch versions): `one-on-one` 0.2.2, `performance-review` 0.2.2, `goal-setter` 0.2.2, `hiring-designer` 0.2.2, `offboarding-guide` 0.2.2, `delegation-coach` 0.2.2, `meeting-processor` 0.18.2 (participants and action items, one call), `context-navigator` 0.3.2 (slots), `product-reporter` 0.10.2, `sprint-planning` 0.6.2, `task-creator` 0.15.2, `focus-advisor` 0.9.3, `decision-log` 0.5.2, `plugin-configurator` 2.15.3 (the team step proposes members from the cards, written only once you confirm). No description changed.
- **Search index** (`context-provider-protocol.md` §10): a card's slot fields (`fields_json`, never a judgement field); `meta_version` 4 reads the files once in place; the catalogue's `card_names_version` re-reads the cards alone when the names change. A link or a Jira key inside code is neither a link nor a mention; Jira prefixes never come from JQL words; a work card's key comes from its own field first.
- **`data-policy.md` Search rule 1:** a person's identity (name, e-mail, team, role, card path) as `ctx entity` and `ctx read`'s team members give it may be used by any skill — never a profile's body or a judgement field; a sensitive team's, mission's or metric's card gives its members' names and its path only. Under a core rule or `prefer repo:` `ctx entity --slot team.members` is the rule's list with `from_cards: N`, as `ctx read` prints it.
- v3.18.0 minors: `field` in the text of `ctx entity`; `same` on a busy index exits 5; local cards dedupe without case; a folder's path is resolved once (a local index of thousands of notes).

### Acceptance (a copy of the author's index, local index and store)

- **Migration** of a copy of the real index: one 28 s walk, in place, `meta_version` 1 → 4.
- **Regression of v3.18.0:** 646 person cards → 465 people, 0 doubles, 0 merges across different e-mails.
- **Members:** 38 of 39 core teams, 530 items, 0 without an entity, 0 twice in a team; members only from the winning team (0 violations); missions ↔ teams symmetric (0).
- **`ctx read` of the author's team:** 46 rows of two tables → 29 people, one line each, no row lost.
- **Privacy:** 0 judgement values in the slots of 20 people with Step-P fields; real store and `~/.grow-pm` unchanged.
- **Time:** `ctx entity <team>` 1.8–2.0 s, `--q` × 8 1.4 s, `ctx read` with team members +0.7 s, other reads unchanged.
- Five findings fixed during the acceptance (path resolution 21.7 s → 1.8 s; your evicted notes counted as yours; a team record matched over another team's card; another spelling of a name; one composition in `ctx entity` and `ctx read`).

### Known limits

- A row «Ім'я, Ім'я — роль» in a core team card's people section joins the first name only (the second person still comes from their own `team:`); an inline `**Lead:** A, B` line stays one item.
- A card of a repository whose registration gives no rank is shown after the cascade.
- `ctx entity` on a busy index waits for each of its reads before exit 5 (as in v3.18.0).

### Backwards compatibility

The schema name stays `search-index/1`; an older build reading a newer index leaves it as it is (`meta_version` above its own). `ctx read` output changes only for `team.members`. A card's slot is unknown to `ctx slot …` and `ctx explain` (they say so).

## v3.18.0 (2026-10-22)

**«Хто є хто»: one person, team or epic across your notes and the cores.** Your person note, a core's registry card and another team's card in your local index often describe one person — and until now each skill saw them apart. `ctx entity` joins them into one entity and answers «хто такий X», «що за команда X», «що таке PROJ-1234», «хто посилається на X»: who it is, where its cards are, who links to it, and — for a Jira key with no card — where it is mentioned. It writes nothing into your notes.

MINOR: a new command line (`ctx entity`), three new tables in the search index (filled in place, the schema name unchanged), `context-navigator` 0.3.1.

### Added

- **`ctx entity <запит> [--kind K] [--skill S] [--json]`** (`scripts/ctx_entity.py`, `context-protocol.md` §5h):
  - the request is an e-mail, a Jira key, a card's path or link, a name or an alias; a near match says `схоже на «…» — не точний збіг:`;
  - one entity → its cards with their source, its identity (e-mail, team, role — nothing else), `пов'язана з: …`, `можливо той самий: … — ctx entity same|not-same …`, who links to it and the notes that carry a work entity's key (newest first, 20 at most);
  - several → `<мітка> · <вид> — ctx entity "<шлях>"`;
  - a Jira key with no card → `<KEY> — картки немає, згадується в N нотатках:`, only for a key whose project prefix a card names or a `/browse/` link names (`GPT-4` is no key);
  - a sensitive note outside the People contour → its title, path and day with ` · sensitive`; its field only for a People skill, its text never.
- **How cards join** — the strongest key first:
  - your answer `ctx entity same`;
  - an equal e-mail of a card's own address fields (`manager_email` is someone else's);
  - a bridge recognised by its shape — a field of exactly one link, whatever its name, to a card of the same kind in another source, with nothing against it.

  A name never merges. `ctx entity not-same` keeps two cards apart whatever the keys say. A team linked under another name is `пов'язана з` it. An epic's core page with the same key is its second home.
- **`ctx entity pairs`** lists every open «можливо той самий» pair: two cards of one kind from different sources whose names are alike, never two people with different e-mails. **`ctx entity same|not-same A B`** keeps your answer in `.state/entities.json`, with a snapshot and a journal line; `ctx undo` takes it back.
- **Cards from your local index (Q7):** another team's cards that only your local index holds join by their frontmatter alone.
- **The search index keeps who is who** (`context-provider-protocol.md` §10), three tables in the same file:
  - an identity row per note — a card's identity fields alone, never a judgement field;
  - every wiki link as written;
  - every Jira-key-shaped token.

  An index of v3.17 gets them in place: its downloaded files are read once (`meta_version` 3) and nothing is rebuilt. A row an older build left behind (another hash or path) is never read, and its file is read again.

### Changed

- **`context-navigator` 0.3.1** and `search-protocol.md` §13 — «Who or what it is»: a question about a person, a team, a mission, a module, a metric, a work item or a Jira key asks `ctx entity` first, and its lines are the answer with their paths. A person's identity comes from it.
- Protocols:
  - `data-policy.md` Search rule 1 — `ctx entity` follows it;
  - `people-context-protocol.md`;
  - `context-protocol.md` §1, §3, §5h, §8.

  Also: trigger evals U11–U12.

### Acceptance (a copy of the author's index and local index)

- **Migration:** a copy of the real index migrated in one 18 s walk — 7 243 notes, 898 cards, 49 319 links.
- **Links:** 99.74 % of the links with a folder from your layer resolve to one note.
- **People:** 646 cards → 465 people, with 0 doubles by e-mail and 0 false merges.
- **Who links to them:**
  - missions 27/30, people 178/447;
  - teams 4/39: the other teams are linked only from `_System/` notes, which the index leaves out by design.
- **Judgement fields:** none of their values reached the output for 20 people.
- **Jira:** 1 473 of 1 524 keys have a known prefix; 34 epics have a second home.
- **Pairs:** 74 open pairs of people. 605 more joined people with different e-mails and were dropped by a fix.
- **Speed:** the registry builds in ~1 s; a request takes ~0.7 s.
- **Found by the acceptance and fixed:**
  - a link that two notes of one name answer broke the command;
  - pairs of people with different e-mails.
- **Trigger evals:**
  - Claude (visible and real): U 11/11, T 14/14, L 8/9 (L9 → the host's own `update-config`, as before);
  - Codex: 29/36. U11 and U12 are right; the misses are the earlier ones, plus noise on L5 and T8 — the branch changes no description.
- `host-smoke` passed (Claude + Codex).

## v3.17.0 (2026-10-22)

**«Пошук по контексту»: ask your context directly.** Until now the search ran only inside the skills, before their work (Step 0.5). Now you ask it yourself — «знайди в моєму контексті…», «що в мене є про…», or the typed `/grow-product-manager:find` — and `context-navigator` searches every connected context: the plugin folder of each vault (the rest of a vault through a local index of it), every registered core, your local indexes, a `vault/v1` provider of the session, and the live sources when you ask or when the base has nothing direct. It answers with a source and a date for every statement, or lists the notes, and ends with the line `Де шукав: …`. People notes — 1-1s among them — are marked `sensitive` by the engine and stay with the People contour.

MINOR: a new command (`/find`), a new protocol section (search-protocol §13), `context-navigator` 0.3.0; the index schema unchanged.

### Added

- **`search-protocol.md` §13 — the search the user asks for:**
  - Step 0.5 as the task itself: level 1 over every connected context — `ctx search`, plus a `vault/v1` provider no registration covers, joined by RRF;
  - an **answer** takes at most five sections, base and live together; every statement carries its source and date, and nothing unsupported is said;
  - a **list** gives at most ten notes and calls no `--get`:
    - a server's line whose mark is not known yet shows its title only;
    - a line is read before it is remembered;
    - its doubts are unnumbered lines, never a second numbering;
  - **level 2**:
    - starts at once on `--all`, or on a named source (that source only);
    - otherwise starts only when the base has nothing direct;
    - a VPN or a login, mail, person profiles and private channels are still asked about first;
  - **the closing lines:**
    - `Де шукав: …` names every source, and the one that did not answer or was skipped;
    - `Немає де шукати: …` when there is nothing to search;
    - `Поки нічого прямо про це — індекс оновлюється: …` while the index refreshes.
- **`/grow-product-manager:find <запит> [--list] [--all]`** — the same search, typed. It is user-only like every command, and there are six now.

### Changed

- **`context-navigator` 0.3.0:**
  - answers and searches from your whole context, with or without a shared core — with no core, one line and then your base;
  - recording or revisiting a decision → decision-log; what was decided → §13, which reads the decision records and the meeting notes alike;
  - a person by identity only: name, e-mail, team and role from the card's frontmatter, and its path;
  - the description is re-cut so that the guards against decision-log, product-analysis and the source library fit the 190 characters Codex shows.
- **`knowledge-library` 0.9.2:** its description now leads with «які джерела маємо» and «додай у бібліотеку». Before, these sat past the 190 characters Codex shows, so «які джерела маємо по чекауту» (T13) went to the navigator there.
- **The engine marks `sensitive` itself (Q2).** A note is sensitive when it has:
  - `sensitive: true`;
  - a people type: `people`, `person`, `one-on-one-notes`, `one-on-one`, `performance-review`, `offboarding-plan`, `delegation-audit`, `followup-arcv`;
  - a person profile's judgement field (`d_type`, `signals`, `one_on_one`, … — one map down too);
  - a 1-1 in its title, folder or file name (`1-1 …`, `… 1-1.md`, `1:1 …`, `1on1s/`, `1-on-1`, `One-on-ones/`, `1-1-Logs/` — never «Split 1:1»).

  Own rows, local-index and server hits, and `--get` from every source carry the mark. An old row of a people type or a 1-1 reads as sensitive at once.
- Protocols:
  - `data-policy.md` Search rule 1 — the list, and the one identity exception;
  - `search-protocol.md` §1, §4, §6;
  - `people-context-protocol.md`;
  - `context-provider-protocol.md` §2, §10.

  Also: README, the plugin-configurator context schema, trigger evals Group U (U1–U10) and L10.

### Fixed

- The frontmatter reader keeps one level of a map (a profile's `signals:`, `one_on_one:`), and a mapped value never becomes a title.
- `--get` of an evicted note that a local index serves takes its type, date and mark from the index's row, in both shapes.
- A server's hit keeps the date its class TTL counts from.

### Acceptance (a copy of the author's vault, the same state for both versions)

- `ctx search eval`: v3.16.2 and v3.17.0 agree row for row — recall in the first 50 is 100 %, MRR 0.594.
- `sensitive` went from 54 to 734 notes. None of them is marked by a judgement field alone on a non-people type.
- Twelve requests walked by the model at the level of §13:
  - every answer cites path and date;
  - the lists call no `--get`;
  - a person is identity only;
  - with no core the search uses the vault alone.
- The walk found 1-1 notes kept as `meeting` or `one-on-one`: they were unmarked and their snippets reached the list. This is fixed — see the 1-1 rule above.
- Trigger evals, Claude (visible and real): E 5/5, H 16/16, J 9/9, K 13/13, O 8/8, T 14/14, U 9/9 (6/8 on v3.16.2), L 8/9 (L9 → the host's own `update-config`, as on v3.16.2).
- Trigger evals, Codex: T13 had gone to the navigator; with `knowledge-library` 0.9.2 it is 2/3 to the library, and green in the U+T run. Groups U and T are 22/24 (U8 → the user's own `lazyweb-quick-search`; U9 is the `find` command under Codex's name).
- Pre-existing on Codex, on v3.16.2 as well: L6, L7, U8, and Group K's glossary and style phrases.
- Tests: `ctx_index_test.py`, `ctx_search_test.py` (with pins of §13, the navigator and `/find`) — each new check failed before its code. An independent review followed every task and the whole branch, each with fixes.

### Backwards compatibility

- The index schema is unchanged (`search-index/1`). An index of an earlier build reads its downloaded files once more on the next refresh (meta `meta_version` 2), which takes about as long as one rebuild. Until then, people types and 1-1s are marked as they are read.
- Notes that skills outside People could take before — `person` notes, 1-1 notes kept as `meeting` — are now named there by title only.
- `context-navigator` no longer stops when no shared core is connected.

---

## v3.16.2 (2026-10-22)

**«Пошук», другий патч: nothing swaps in another note silently.** What v3.16.1 deferred, done in one night with the user's consent to merge: two cards that differ only by a list of owners no longer fold into one; a remembered pick is no longer lost — nor a «не те» spread to the wrong note — when its note is folded; the excluded folders are the same in the index, the search and `--get`; every name a search lists reads back from the source that holds it; the «нотатка довга» line names exactly the sections `--get` takes back, and fast. Measured on a copy of the user's real vault (95 reviewed requests, old = v3.16.1 and new on the same vault state): the search ranks every request alike (a sample's top 15 identical); `ctx search eval` now counts a golden note folded as a twin at its survivor's place — top-1 good 49 → 51, MRR 0,629 → 0,649, each change through such a fold (a project note and the Confluence page it links, a library copy and its original); near-copy groups 51 = 51.

PATCH: fixes of the search and its index; no new command, no skill changed.

### Fixed

- **Near copies:** a list item of links alone (`- [[Bea Two]]`, in a callout too) is the note's content, so two cards that differ only in their owners or attendees no longer fold; a dated bullet (`- [[2026-03-01]]`) is still set aside. An index of the earlier rules gets its keys again from its own sections at the next refresh — no file read, the schema unchanged (meta `near_version`; a later build's keys are left alone).
- **Folds remember what they stand for:** every fold (the same page, content, near copy, title and link, version) records on the survivor the paths it stands for (`twins` in the candidate). A remembered pick of a twin weighs its survivor and marks it «твій вибір від <день>»; a «не те» is carried only across a fold of the same text — never from an older version to the newer one —, and a verdict on the candidate itself outranks a carried one. `ctx search eval` finds a golden note folded as a twin at its survivor's place; its rows say `via_twin` / `good_via_twin`.
- **Exclusions alike everywhere:** `.obsidian`, `.trash`, `_backup…`, `_System/providers|_scratch` are compared case-folded in the walk too (`_Backup 2025`, `.Trash`), so a stale backup no longer competes with — or replaces — the original; a symbolic link to a file is not followed; the real-path re-check of `--get` names a file by the innermost core folder that holds it.
- **Names read back from their source:** a server's hit outside `endpoint.root` is `@<repo>/:/<path as given>` (no Obsidian name holds a `:`) — no longer the name of the note under the root, which made one of them vanish from the list and a path read return the other; a path under a registered core folder gone from disk is read through its server — by id under the server's line and day — and the index drops the rows no root owns at every walk (a resumed one too), so neither the index's nor a local index's old copy is served as current; a local index rooted in a subfolder is asked only by its own relative paths; a local index outside every vault reads its `@<id>/…` notes back from its own text. By id, a vault file deleted since the search is «not on disk», not a local copy.
- **The «нотатка довга» line:** the heading lines with nothing under them are left out as the sections leave them out, so a file read and the own index's render name the same headings and each reads back; the names are found through one map of the note's headings (4 000 headings: 4,7 s → 0,03 s); the section the cut falls under is named only when `--get` of it shows 2 000 characters more; after `--full` the hint carries `--full`. `[[Name#Delivery#C# tips]]` joins the parts back with `#`.
- After `rebuild --download` the status line's plugin-folder count comes from the download.
- Protocols: `search-protocol.md` §3 (`twins` serve picks and eval — read what a mark names), §4 (the read order, `@<repo>/:/…`, the link forms, the line); `context-protocol.md`, `context-provider-protocol.md` §5 (key 3a), §10 (not indexed).
- Tests: `ctx_index_test.py`, `ctx_search_test.py`, `ctx_hints_test.py` — each new check failed before its code (some pin a behaviour an earlier task already gave).

### Backwards compatibility

- The index schema is unchanged (`search-index/1`); the near keys are redone once, from the index itself.
- A server's note outside its root has a new name, `@<repo>/:/…`: a v3.16.1 path string or a remembered pick of such a note no longer matches it (an honest «no note»); every other name is as before.
- `ctx search --json` candidates may carry `twins`; `ctx search eval` rows carry `via_twin` and `good_via_twin`.
- No skill renamed, no description changed: routing is as in v3.16.1.

---

## v3.16.1 (2026-10-21)

**«Пошук», патч: your whole plugin folder reaches the search, and `--get` gives a long note in measured parts.** On a Mac that offloads iCloud files, 1 821 notes of the user's own layer were not on disk: the section index skipped them (reading one would start its download), so they reached Step 0.5 only through a local index, as whole notes. `ctx index rebuild --download` now brings them down — only the plugin folder, only what the index would read — and indexes them. Measured on a copy of the user's real vault with the reviewed set of 95 requests: 1 820 of 1 821 notes came down in 13 minutes; the right note among the first 50 rose from 98,9 % to 100 % (the one miss of the v3.16.0 acceptance, a real request about a CJM status meeting, is now 7th), among the first 5 from 83 to 85, MRR from 0,623 to 0,629; the old and the new code rank every request alike on the same vault state. `--get` no longer hands a skill a 45 000-character note whole — 228 notes of that local index were over 20 000 — and now reads a link the way a hub writes it: of 300 folder links sampled from the user's notes it read 207 before, 298 now.

PATCH: one option of an existing command (`ctx index rebuild --download`), one of `ctx search --get` (`--full`), `--get` fixes; no skill changed, no description changed.

### Added

- **`ctx index rebuild --download`** — brings down the files iCloud evicted from the plugin folder of every vault, only those the index would read (never a core folder, the rest of a vault, the store, `_System/_scratch|providers`, `.trash`, `_backup…`, `.obsidian`, a file over 2 MB or not `.md`, a symbolic link), each read once in a child process (30 s a file, 4 at once, no limit on the run; the child stops itself shortly after its time), then rebuilds the index. Lines: `iCloud: N з M…` every 100 files and at least once a minute, then `iCloud: завантажено N з M` (`, лишилось K (не встигли за 30 с: T; не прочитано: F)` — a reason only when it is not zero) or `iCloud: нічого завантажувати`. The index lock is checked first (exit 4 before any download); Ctrl-C at any moment stops it (`…, зупинено (Ctrl-C) — індекс не перебудовано`, exit 130): the running reads are killed, what came down stays. Nothing else ever downloads — no search, no `--get`, no `ctx index status` (decided with the user: opt-in, no limit on the run).
- **`ctx search --get … --full`** — for a candidate the model rated «прямо» whose part lies past the cut, or a skill that works on that whole document: the cut is 60 000 characters instead of 20 000 (decided with the user: the model, which has already rated the candidate, decides). `search-protocol.md` §4 says when; never for a hub, a twin's check or a candidate not rated «прямо». Bad usage without `--get`.

### Changed

- **Every form of `--get` is cut at 20 000 characters** — an id too (a local-index or MCP note came whole before), a section after `#` too (it was never cut; a section of 276 000 characters exists in a real vault). The line after a cut says how much of how many and names the headings past it — `нотатка довга — показано 20 000 знаків із 45 491; далі: Part 9 · Part 10 · … — --get "<шлях>#<заголовок>" або --full (до 60 000)` — each by the shortest end of its heading path that `--get` takes back to that very section (a heading the note's sections leave out, or one another heading shadows, is not named); `заголовків далі немає` when none follows.
- **`ctx index status`** names `--download` only for the plugin folder's evicted files: `not downloaded (iCloud), not read: N (plugin folder: K — ctx index rebuild --download)`. A `--get` of an evicted note no local index holds says `… — відкрий його в Obsidian або ctx index rebuild --download` for a plugin-folder note, `… — відкрий його в Obsidian` for any other.

### Fixed

- **`--get` reads a link as a hub writes it:** an embed `![[Name]]` / `![[Name#H]]`; nested headings `[[Name#H1#H2]]` and `Name#H1 › H2` (the section whose heading path ends in them — a bare `#H` is still the first one; a whole heading path asked is that section before the end of a longer one); a block reference `#^id` (the section that holds the block, else the whole note); a heading with `#` in it tried whole first; `İ` before `.md#` no longer shifts the heading.
- **A link with a folder** (`[[People/zorg-one|Zorg One]]`, `[[Concepts/Name]]`, `[[../Concepts/Name]]`) that no source holds as a path is the note whose path ends in it: the own and the local indexes asked together, `<plugin folder>/<link>` first, else a plugin-folder file on disk by that name — an evicted note is never swapped silently for another with the same tail; several are `кілька нотаток, чий шлях закінчується на «<посилання>»: … — --get один зі шляхів`. The exact path still wins; an `@<repo>/…` name is never the end of another path.
- Protocols: `search-protocol.md` §4 (the cut and `--full`, the link forms, the lines), `context-protocol.md` (`index`, `search --get`); the usage of `ctx`.
- Tests: `ctx_index_test.py` 166 checks (+28: the download's scope and counts, `_fetch`'s time bound on a FIFO, Ctrl-C at random moments in 30 runs and a handler that takes no lock, the lock first, the hint), `ctx_search_test.py` 321 (+46: the cut of every form, the names past it read back, `--full`, the link forms, the tail lookup's never-silent rule, nothing ever downloading), `ctx_cli_test.py` 719 (+4). Each new check failed before its code. Deferred to v3.17: copies that differ only by a bare `- [[…]]` or date line still fold as near copies (re-measured after the download: 0 such groups in the user's vault), a remembered pick of a note folded as a twin, and the minors of the final review.

### Backwards compatibility

- The index schema is unchanged (`search-index/1`); nothing is downloaded unless you run `ctx index rebuild --download`. A `--get` text longer than 20 000 characters is now cut with a line — a skill reads the section it names, or adds `--full`.
- No skill renamed, no description changed: routing is as in v3.16.0.

---

## v3.16.0 (2026-10-21)

**«Пошук»: Step 0.5 finds what your base already holds about the request.** Until now Step 0.5 of a skill matched every word of the request at once (AND), in the language it was typed in, gave the newest notes of the skill's types, and asked «Use as context?» in the middle of the run. Measured on a copy of a real vault with a reviewed set of 105 requests: a user's own local index as it was put the right note among the first five for 44 % of the requests with an answer, and for 2 of 24 requests taken from real work; the type-and-date list, for 2 of 17. The anti-goal of this release is the opposite failure — a wrong note taken silently, which becomes the source of wrong conclusions — so what is taken is rated, marked and cited.

MINOR: a new protocol, two new commands of `ctx` (`search`, `index`), a new memory file in the store, a new index outside it; Step 0.5 of four skills rewritten. No skill renamed, no description changed.

### Added

- **`references/search-protocol.md`** — Step 0.5 of every skill: the model writes 3–4 variants of the request (Ukrainian, Russian, English, a synonym or the team's term), runs `ctx search`, rates each candidate «прямо» / «частково» / «ні», takes silently at most three that are directly about the request — with their source and date in one line «Взяв із бази: …» — and asks nothing in the middle of the run. A doubt (only partial matches, an outdated or older note, a hub, a glossary-only hit, a snapshot) or a conflict between taken notes goes into a numbered **block of variants after the work**; nothing found is «У базі нічого прямо про це». When what was taken lacks a fact the work needs, or nothing was found, level 2 may ask a live source (Confluence, Jira) — never in the middle of the run without the user's OK. `sensitive` notes and people types stay out of product skills (in the block by title only). An automated run (`health-check`) writes its doubt as one `Пошук:` line in the report.
- **`ctx search --q TEXT [--q TEXT …] [--skill S] [--product P] [--limit N] [--sources own,local,mcp] [--no-hints] [--json]`** — read only, no store lock. Every variant goes to every source at once, each its own ranked list:
  - **its own section index** of the plugin folder of each vault and the core folder of each registration — `<home>/.grow-pm/index/sections.sqlite` (schema `search-index/1`), one row per section (headings 1–3), FTS5 with bm25 weights title 10 · heading 6 · tags 4 · aliases 4 · body 1; refreshed incrementally on each search within 30 s (a queue carries over, a lock, a broken or older index is rebuilt and says so in one line); files over 2 MB, not Markdown, under `.obsidian`/`.trash`/`_backup*`, the store and `_System/_scratch/` are not indexed; **a file iCloud has not downloaded is never read** (it would start a download) — it is counted in `ctx index status`;
  - **a local compatible index** of yours (sqlite read with `mode=ro`, both shapes of `context-provider-protocol.md` §10), within 5 s to open;
  - **a repository's MCP server** only when the repository has no folder on disk (`McpClient.call_list` reads `vault_search` in every shape a server sends, including `structuredContent: {"result": [...]}`).
  
  A light Ukrainian/Russian stemmer and OR semantics; the team glossary's approved other names of a word as a list of weight 0.5 (`лише глосарій` when that is all that matched); reciprocal rank fusion (k = 60); priors — the skill's types × 1.2 (a weight, not a filter, from `search_types` in `references/context-manifest.yaml`), the same product × 1.1, another × 0.7, a hub × 0.5, outdated × 0.5, your earlier pick × 1.5. Limits: 20 s a source, 60 s the command; a source that does not answer is one line `<id> не відповів — без нього`, and a base that was not read is never «nothing found» (exit 5, «Базу не прочитано»).
- **Folding and marks.** One candidate per note with at most two of its sections; the same note found twice (the same path in NFC, the same Confluence id — the newer stays, the same content hash, a near copy — the same text but for a back-link, a navigation line, a date stamp or a «Повʼязане» block: your layer's copy stays, then the original (the older), the same title and link) is folded into one with `двійник <шлях>`; versions (`v2`, `draft`, `№2.1`) fold into the newest with `старіша версія <шлях>` / `є старіші версії: N`. Marks: `застаріле` (status outdated, archived, deprecated, former, superseded), `станом на <день>` (a card older than its class's `ttl_days` — taken, cited with that day), `знімок від <день>`, `sensitive` (also from a folded copy), `хаб`, `лише глосарій`, `одне слово`, `твій вибір від <день>`, `ти казав «не те»`. Every candidate carries its source, path and date (a local index's file day when the note has none).
- **`ctx search --get ID|PATH|NAME`** — a section with its provenance line `> [<джерело> · <шлях> › <заголовок> · <дата>]`; a section shorter than 200 characters goes on with the next ones up to 1 500 (`секція коротка — додано наступні: …`), so a Confluence navigation line is never all you get; a note by its path (`Notes/x.md`, `@repo/x.md`) or by its name (`Назва`, `[[Назва]]`, `[[Назва#Розділ]]`) — to read a twin, a newer version or a hub's link; a note iCloud has not downloaded is read from a local index (`файл не завантажено з iCloud — текст із локального індексу <id>`) or not at all; at most 20 000 characters of a whole note.
- **`ctx search remember|forget`** — your picks from the block of variants (`<store>/.state/search.json`, schema `context-search-memory/1`): a writing command (lock, snapshot `search`, journal `op: search`, `ctx undo`); a similar request (Jaccard ≥ 0.6) weighs the pick × 1.5 or marks a rejected note.
- **`ctx search eval --golden <file>`** — the golden set `<store>/search/golden.yaml` (schema `search-golden/1`, frozen variants): the right answer among the first 50, by class, the same by the request alone, MRR, and the empty requests; `testing/search_agent_eval.py prepare|score` measures the model level (precision of what is taken, empty requests clean, the right answer taken or offered).
- **`ctx index status|rebuild`**; the SessionStart digest line `index: секцій N · оновлено <день>` (read from `index.json` alone, no sqlite at session start).
- Validator check 19: every skill's `search_types` in the manifest equals the types its `SKILL_CONTEXT_MAP` row names.

### Changed

- **Step 0.5 of `write-concept` 0.16.0, `product-analysis` 0.18.0, `cjm-research` 0.13.0 (its Step 1.5)** follows `search-protocol.md`: no «Use as context?» question; what is taken feeds the work as before (the concept's "Informed by", a previous value with its source and date, the CJM baseline).
- **`context-navigator` 0.2.0** — its "anything else" route uses `ctx search` → `--get` with SHELL; a card or note one of its own routes reads directly is neither taken by Step 0.5 nor counted as a doubt.
- Protocols: `vault-protocol.md` (L1/L2 point to `search-protocol.md`), `local-context-protocol.md`, `context-protocol.md` §3 and §5g, `context-provider-protocol.md` §2, §5, §6 (a class's age gives «станом на», only a status gives `застаріле`), §10, §12.8, `host-profiles.md`, `data-policy.md` (the index stays on the machine; a search goes to a server only for a repository with no folder).

### Acceptance

On a copy of a real vault, read only (the index and every write target in a scratch folder, a guard before every call), on the reviewed set of 105 requests (71 simulated in ten classes, 24 from real work, 10 the base has nothing on) — `Context-Core-v3.16-Acceptance` in the programme folder:
- `ctx search eval`: the right note among the first 50 for **98.9 %** (criterion ≥ 85 %), first for 49 of 95, MRR 0.621; the right note among the 30 a skill reads — 94 of 95.
- The model level (agents following the protocol, an independent judge on what was taken outside the set): **95.8 %** of what was taken silently was right, no wrong note taken silently, nothing taken on **10 of 10** empty requests, the right note taken or offered for **96.8 %**.
- No note twice in a list; every candidate has a source, a path and a date.
- The first fix wave after the acceptance lowered the top place (the right note first for 39 instead of 48 requests) — found by measuring the old and the new code on the same state of the vault, fixed before release (a navigation line stays a section of its own; of two near copies the original stays).

### Tests

`ctx_stem_test.py` 67, `ctx_index_test.py` 138, `ctx_glossary_test.py` 48, `ctx_search_test.py` 275, `ctx_hints_test.py` 80 (all new), `ctx_mcp_test.py` 244, `ctx_cli_test.py` 715, `session_start_test.py` 130; the golden read test still matches all 99 read views; a fictional fixture vault (`testing/fixtures/search/`) with a core folder, a local index built by the tests, a broken frontmatter, NFD names and a pinned eval. Every new check failed before its code.

| File | Change |
|---|---|
| `references/search-protocol.md` | new — Step 0.5 |
| `scripts/ctx_stem.py`, `ctx_index.py`, `ctx_glossary.py`, `ctx_search.py`, `ctx_hints.py` | new |
| `scripts/ctx.py`, `ctx_mcp.py`, `ctx_common.py`, `ctx_read.py`, `ctx_resolve.py`, `session_start.py` | `search`, `index`; `call_list`; the digest line |
| `references/context-manifest.yaml` | `search_types` per skill |
| `skills/write-concept` 0.15.1 → 0.16.0, `product-analysis` 0.17.1 → 0.18.0, `cjm-research` 0.12.1 → 0.13.0, `context-navigator` 0.1.1 → 0.2.0 | Step 0.5 by the protocol |
| `testing/validate-consistency.sh` | check 19 |

### Backwards compatibility

- Your context, the records, the manifest's reading and the registrations are unchanged; `ctx read` gives what it gave in v3.15.2. The index lives in `~/.grow-pm/index/` and is built on the first search (or `ctx index rebuild`); deleting it loses nothing.
- Without SHELL (no `ctx`), Step 0.5 works as before through the vault server's search, with the protocol's rating and block of variants.
- A note iCloud has evicted is not in the own index until it is downloaded; until then it reaches the search through a local index of yours, if you have one. An option to download such notes is planned for v3.16.1.

---

## v3.15.2 (2026-10-20)

**A binding to a slot the catalogue lacks sets no other binding aside.** v3.15.1 stopped such a binding from hiding a block from the by-name answer; it still decided which source binds the block. Per block the first source counts — yours, then the publisher's `slot=`, then the plugin's `team#Members` — and a binding to an unknown slot still took that place. So a core ahead of the plugin that marks its `team` block `slot=<a slot this plugin does not know>` set the plugin's `team#Members` aside, and a skill that reads a team's members, with your own `Team Members` table, lost the core's half; a binding of yours to a slot the catalogue no longer has set the publisher's `slot=` aside in the same way. Decided with the user: such a binding does nothing, and the next source binds the block.

PATCH: a resolver fix; no new command, no skill changed.

### Fixed

- **A binding to a slot the catalogue lacks is no binding.** `ctx_slots.bindings_of` counts a source only with a slot of the catalogue: yours with only unknown slots leaves the publisher's `slot=` (then the plugin's binding) in force; the publisher's `slot=` with only unknown slots leaves the plugin's `team#Members` in force; a source with known and unknown slots binds the known ones. `ctx read`, `ctx explain` and `ctx validate` follow from it: with your own `Team Members` table and the core's team block marked with a slot this plugin does not know, `team.members` again shows both halves.
- **`ctx validate` and `ctx explain` still name every such binding** as `unknown`. A publisher's `slot=` is now named «ignored» only when your binding of the block names a slot of the catalogue.
- **Unchanged:** like any block with a binding, a block bound only to an unknown slot is not proposed again and not listed among the blocks no slot takes; the `unknown` line says what is wrong with it.
- Protocols: `context-protocol.md` §5f (a binding to an unknown slot is no binding; candidate 3 reads «any slot of the catalogue») and `context-provider-protocol.md` §12.2 (neither the attribute nor your binding to such a slot sets the next source aside).
- Tests: `ctx_resolve_test.py` 223 checks — 12 new. 9 failed before the fix: the order of the sources, the list of bindings set aside, the team-members case. 3 hold v3.15.0 rules this patch keeps: validate names the publisher's unknown slots; such a block is not proposed and not listed as no slot's. The golden test still matches all 99 read views of v3.14.1.

### Backwards compatibility

- Your context, the records, the manifest, the catalogue and `.state/slots.json` are unchanged; nothing new is written. A read differs from v3.15.1 only for a block whose binding names a slot the catalogue lacks: the next source binds it.
- No skill renamed, no description changed: routing is as in v3.15.1.

---

## v3.15.1 (2026-10-19)

**A binding to a slot the catalogue lacks no longer hides a block.** Left over from the v3.15.0 final review: the resolver kept a block out of every by-name answer as soon as you or its publisher bound it to any slot — including a slot `references/context-slots.yaml` does not have (a publisher's `slot=org.nowhere`, or a binding of yours to a slot a later catalogue removed). The protocol says such a binding does nothing (`context-provider-protocol.md` §12.2, and `ctx validate` names it `unknown`), so the block should still answer by its heading, as in v3.14.1. No real core publishes `slot=` yet, so nothing changed for anyone today.

PATCH: a resolver fix; no new command, no skill changed, no protocol text changed.

### Fixed

- **`ctx read` and `ctx explain`: only a binding to a slot of the catalogue says what a block is.** A block of a product, team or profile record that you or its publisher bound to an unknown slot answers by name again (`за назвою, без прив'язки`), where your text has nothing for the slot; `ctx validate` still warns about the binding as `unknown`. A binding to a slot the catalogue has keeps the block out of every by-name answer, as before (`context-protocol.md` §5f, candidate 3).
- Tests: `ctx_resolve_test.py` 211 checks — 4 new (the publisher's `slot=org.nowhere`, your binding to a removed slot, and `validate` naming both), the two by-name checks failed before the fix; the golden test still matches all 99 read views of v3.14.1.

### Backwards compatibility

- Your context, the records, the manifest, the catalogue and `.state/slots.json` are unchanged; nothing new is written. A read differs from v3.15.0 only for a block bound solely to a slot the catalogue lacks: it is found by name again.
- No skill renamed, no description changed: routing is as in v3.15.0.

---

## v3.15.0 (2026-10-19)

**A skill gets its slot, says what it lacks, and `ctx explain` says where each piece came from.** Until now `ctx read` found a field or a subsection by the exact start of its heading, in the record the manifest named, and mixed a repository's block into a skill's context with nothing to say which text won or why. A read-only look at a real store showed what that hides: a skill that silently got no team members because the heading had another name, two `Key Metrics` sections that meant different things, and the two halves of one team list in two records. v3.15.0 is the resolver: every name a skill asks for is a **slot**, every candidate text for it is found wherever it sits, and one cascade decides what the skill gets — and says so.

MINOR: two new commands, a new memory file in the store, a new marker attribute, a changed `ctx read` output. No skill renamed, no description changed.

### Added

- **A catalogue of slots** — `references/context-slots.yaml` (schema `context-slots/1`), 22 slots, each with a kind (`value` | `text` | `list`), the record kind it lives in, the names it goes by (English and Ukrainian: `team.members` answers `Members`, `Team Members`, `Склад команди`, `Учасники`) and a one-line `about`. The manifest is unchanged: each name it asks for is translated to its slot. Validator check 16 now also requires a slot for every manifest name and a clean catalogue.
- **Bindings** — a repository's block (or one of its subsections) answers a slot only when it is bound: by you (`ctx slot bind <repo> <block>[#<Підсекція>] <slot> [--team <запис>]`), by its publisher (`slot=<slot>[,<slot>]` in the begin marker, read from the block's base, never from your region), or — for the team block the plugin builds — by the plugin itself (`team#Members` → `team.members`). A heading never binds a block by guesswork; `ctx validate` proposes bindings and `context-connect` offers them in one message.
- **The cascade** — for each slot and place: a core rule (`policy=rule`) first, with your text under it as a note; then your text; then the repositories by rank (a higher `rank` wins); equal ranks with different texts are a **divergence**, never decided mid-run. Value slots compare values, not lines. A per-slot preference (`ctx slot prefer <slot> mine|repo:<id>|all`) and a remembered answer to a divergence (`ctx slot decide <slot> <repo>`, kept with the hashes of both sides — a new text asks again).
- **The memory of decisions** — `<store>/.state/slots.json` (schema `context-slots-memory/1`): your bindings, your headings mapped to a slot (`ctx slot map <запис> "<Назва>" <slot>`), preferences and decisions; `ctx slot forget <slot>` drops them. Every `ctx slot …` is a writing command — lock, snapshot `slot`, one journal line `op: slot`, `ctx undo`.
- **`ctx explain [<slot> …] [--skill S] [--product P]`** — read only (no lock, no network): for each slot the winner with its source, record, block, version and day of check, every other candidate and why it lost, a divergence, an unplaced block with the command that places it, where it looked when nothing was found, and the decisions in force. Without arguments it also lists the unbound blocks and the blocks you switched off.
- **`ctx validate`** names bindings that do nothing (an unknown slot, an unregistered repository, a block no longer in the records, several slots without their subsections, a team slot with no team to place it), every divergence with its `ctx slot decide` command, and proposes `ctx slot bind …` for unbound blocks whose headings match a slot (`slot_proposals` in `CTX_RESULT`). An unreadable memory is an error.

### Changed

- **`ctx read`** answers every manifest name through its slot. A list shows every candidate in full, each with its source (`> [твоє · <запис>]`, `> [<repo> · v<v> · станом на <date> · слот <slot> — <about>]`); a value or a text shows the winner and one line for the rest — `також: <джерело> каже інакше — ctx explain <slot>`; a divergence shows both and how to decide. A bound block shown in a slot is not repeated in a record read whole — exactly what the slot used is replaced by `> [блок <block> — у слоті <slot> вище]` or `> [блок <block> › <Підсекція> — у слоті <slot> вище]`. The `Відсутнє` line says where it looked (`Members (шукав: Members, Team Members, Склад команди, Учасники у Team: …; блоків із цим слотом немає)`). An unread registration, memory or block state is one line, and the read goes on. The whole read runs on one read budget.
- **Without any binding nothing changes**: a golden test hashes the 99 read views (33 skills × three fixtures) of v3.14.1 and the new code must give the same, but for the `Відсутнє` line and the two provenance marks.
- **`context-connect` 0.5.0** — at a refresh, one message with the binding proposals, one with any divergence (both texts, their sources and days, no recommended side), and an offer to return the blocks you switched off that now have a slot (a no is offered again at the next refresh). The registration gains a second exception to "a refresh changes no key": `context-connect` may remove an id from `skip_blocks`, only on your yes for that block.
- **`plugin-configurator` 2.15.2** — Validate shows the same package: divergences and binding proposals.
- Protocols: `context-protocol.md` §3, §5a, new §5f (slots, the cascade, explain), §8, §9, §10; `context-provider-protocol.md` §3b, §12.2 (`slot=`, the plugin's binding), §12.8, §12.9; Step 0c of `local-context-protocol.md` (how to read `також`, a divergence and a rule's note).
- Tests: `ctx_slots_test.py` (new) 70, `ctx_resolve_test.py` (new) 208, `ctx_read_test.py` 101 incl. the golden test, `ctx_cli_test.py` 613 checks — each new check failed before its code. A whole-branch review found two more defects (a plugin-bound team block with a `Team Members` heading lost its text and the read claimed no block; a blank line after a begin marker left a duplicate section) — fixed with checks that failed first.

### Backwards compatibility

- Your context, your records, the manifest and the registrations are unchanged; nothing is written by `ctx read`, `explain` or `validate`. With no binding and no memory, every skill reads what it read in v3.14.1 except: the `Відсутнє` entries carry where they looked; a block found by its heading is marked `за назвою, без прив'язки`; and the team block, which the plugin binds, carries its slot tag — so a skill that asks for a team's members now gets both your table and the core's `Members`.
- `.state/slots.json` is new and only `ctx slot …` writes it; a plugin before v3.15.0 never reads it, and a snapshot and `ctx undo` carry it like the rest of `.state/`. The memory refuses keys it does not know: a later version that adds one will bump the schema.
- Searching several repositories at Step 0.5, once planned for this version, moved to a separate «Пошук» version; the daily sync, `adopt` and `apply` are as in v3.14.1.

---

## v3.14.1 (2026-10-18)

**A skill sees the subsections it lacks; `Team Members` answers `Members`.** Found on a real store, read only, while the v3.15 resolver was being designed: task-creator asks for a team's `Members` subsection, the user's own heading was `Team Members`, and `ctx read` matches a heading by its start — so the skill got neither the members nor their Jira account ids, and said nothing, because a missing subsection never reached the `Відсутнє` line (only a missing field did).

PATCH: a reading fix; no new command, no skill changed.

### Fixed

- **`ctx read` lists the subsections it did not find.** A subsection the manifest names and nobody has goes to the closing `Відсутнє: …` line, never as obligatory, and to `missing` in `CTX_RESULT`. When a skill reads several teams, what one of them lacks is named with it — `Members (Team: Beta)` — so the line never seems to contradict a team that has it.
- **`Team Members` answers `Members`.** A subsection is also found under the other headings the engine knows for it (`ctx_store.SECTION_ALIASES`; one today). Your own text is still read before any repository block, under either heading; a block's `Members` is read as before when you have neither.
- **The card counts a team's members under either heading** — it showed `—` for a team whose table sat under `Team Members`.
- Tests: `ctx_read_test.py` 48, `ctx_store_test.py` 72 checks — each new check failed before its code.

### Backwards compatibility

- `ctx read` output and `missing` gain entries for subsections nobody has; with several teams a team field or subsection that one team lacks is now named with the team (`Jira Team ID (Team: Beta)`) instead of the bare name. Nothing is removed.
- No skill renamed, no description changed: routing is as in v3.14.0.

---

## v3.14.0 (2026-10-16)

**The core reaches your context by itself, once a day.** Until now a change in a team's or an organisation's core reached `local-context.md` only when someone ran «онови мій пакет з ядра». Now a repository can be synced daily: the first skill of the day runs `ctx provider sync --if-due` at step 0c, and the sync decides every block by the cascade agreed in phase 3 — yours wins unless the core marks the block as a rule — writes through the same snapshot-and-journal path as `provider apply`, and explains every decision in a report. It is opt-in per repository (D6: the write boundary is asked once).

MINOR: a new command, a new registration key, a step 0c change, context-connect 0.4.0.

### Added

- **`ctx provider sync [REPO] [--if-due] [--now ISO]`** — one unattended pass per repository with `sync: daily` (a registration without the key, or paused, is never synced). Due 24 h after the last successful check; an hour after a failed attempt (unreachable, out of time). A 20 s budget for the whole run, each fetch in a helper thread (a hanging DNS lookup on a VPN-off day costs the budget, never the skill); no fetch, plan or write begins with less than 3 s left; a busy lock, or a registration still downloading, skips the run with nothing written. The edits waiting in `local-context.md` are imported first. Outcomes: `changed`, `no-changes`, `unreachable`, `broken`, `held`, `import-conflict`, `timeout`, `error`; `CTX_RESULT` carries `synced`, `results` and, when nothing ran, `skipped`. A pass that changed something prints one sentence for the skill to repeat: «Ядро оновило N блоків у <repo>, конфліктів K (лишено твоє) — звіт: …».
- **The cascade, unattended** (`ctx_synced.decide`): a block only the core changed is updated; one you changed stays yours; one you both changed keeps your text and moves the base, unless the core's text carries `policy=rule`; a block with no base waits (unless a rule); a new block is added; one removal is applied, more than one at once are held; a text you undid is never applied; a copy of the core that lags behind (positive evidence: a block older than your base of it, none newer) takes nothing.
- **The sync report** `{storage_root}/_System/context/sync/YYYY-MM-DD.md` — written only when a pass changed something, decided a conflict, met a new waiting block, a lagging source or a safeguard; per repository a table of blocks with the sign, the decision and why, both texts of every conflict (40 lines and 500 characters a line per side), the command to take the core's text instead, and how to take the pass back. A repeated safeguard writes nothing new; reports older than 90 days go to the plugin's trash.
- **"Не повторювати"** — `ctx undo` of a sync pass remembers the core texts it had taken (the journal's `taken`) and the sync never applies them again until the core publishes something new in that block; `ctx provider apply --choose <block>=theirs` takes one block (also on a `✎` row and on a rejected row).
- **The digest's `repos:` line** — `synced <date>` with updates, conflicts kept yours and the report; `no changes`; `unreachable since <date> (VPN?)`; `⚠ N removals held`; `⚠ source behind — nothing taken`; `N block(s) awaits a decision`; `sync timed out`, `⚠ source broken`, `⚠ edits to import first`, `⚠ sync error` — from the state only, within the hook's budget, and in the v3.13.1 summary cache. The `Skills:` line names `provider sync --if-due` before `ctx read`.
- **context-connect 0.4.0** — after connecting or refreshing a repository it asks once whether to turn the daily sync on (`sync: daily` / `sync: off`), after settling every block without a base; a refresh never changes the `sync` key on its own.

### Changed

- **Step 0c** (`references/local-context-protocol.md`) runs `ctx provider sync --if-due` before `ctx read` on every host with a shell — Codex included, which loads no hooks.
- **Registrations are read on a shared deadline everywhere**: 3 s a file and 6 s for all in `ctx` (a writing command refuses, exit 4, while one has not downloaded, since the provider boundary cannot be checked; the write gate asks), 1 s and 2 s in the hook; `--choose`/`--add` that name no block of the plan are refused before the lock; `repo status` reads only the blocks file's version.
- **The MCP client** keeps a deadline, checks the allow-list at the transport (a batch is refused), takes a reply by its id and refuses unsafe header names.
- **The team block is never built from missing inputs** — a missing or unreadable team card, People folder or person card makes it unavailable (`·`, "not downloaded yet" for an iCloud timeout) instead of a silently thinner block; the bundle builder's global reader is gone.
- **State hygiene** — repository ids up to 64 characters, stale `.tmp` files cleaned (also in `sync/`), diffs capped at 2000 lines, `undo` falls back to the mirror when the home copy was edited.
- Tests: `ctx_cli_test.py` 471, `ctx_blocks_test.py` 341, `ctx_repos_test.py` 222, `ctx_mcp_test.py` 180, `ctx_synced_test.py` 177 (new), `ctx_ops_test.py` 169, `session_start_test.py` 126 checks — each new check failed before its code. Every task had its own review, and a whole-branch review found three more defects (the write could start with no budget left; a lasting lag read as "no changes"; the card's registration reads ran outside the sync's deadline) — each fixed with a check that failed first. Acceptance on a scratch copy of the author's real context and core: update, kept edit, conflict kept yours, report, undo byte for byte, the undone text held the next day.

### Backwards compatibility

- Nothing syncs until a registration says `sync: daily`; a v3.13 store, state and summary cache load as they are.
- `CTX_RESULT` changes only add keys (`held`, `taken` in the journal, `rejected`, `records_not_reverted` stays). `--choose X=theirs` on a `✎` row used to be "не потрібне" and now takes the core's text.
- A writing command now refuses (exit 4) while a provider registration has not downloaded from iCloud — before, it could hang on it.
- No skill renamed; context-connect's description gains the daily-sync phrases.

---

## v3.13.1 (2026-10-15)

**`ctx repo list` tells the truth; the digest keeps its context line on a cold start.** Two findings after v3.13.0 went live on a real store: `ctx repo list` showed `—` in its "blocks" and "checked" columns and the registration's own version in "version"; and on a cold session start (iCloud downloads, an antivirus scan) the store's summary took about 17 s against the digest's 2 s, so the `context:` line — and with it the instruction to read through `ctx read` — disappeared and skills fell back to reading the whole `local-context.md`. With them, the deferred v3.13 minors a user meets.

PATCH: fixes and messages; no new command, no skill changed.

### Fixed

- **`ctx repo list`** — "blocks" (the blocks you hold a base for), "version" (the version of your bases) and "checked" (the last check) come from the block state; `—` without a store or a base; a state file that cannot be read shows `!` and one line `block state unreadable: <id> (<reason>)`, exit 0. `CTX_RESULT` rows add `blocks`, `base_version`, `checked` and, on a bad state, `state_error`.
- **`ctx repo status`** — `source_version` is only what the source gives now (otherwise `—`); the registration's own is `registration_version`, and a reachable source whose blocks file could not be read adds `fetch_error` and the line `  blocks file: <reason>`. An unreachable reason is cleaned and clipped to one line.
- **The digest on a cold start** — the store's summary is saved to `~/.grow-pm/.ctx-summary.json` by every live count that comes in time and by every writing `ctx` command that exits 0 (counted on the digest's own budget, so a slow store holds a command's result for at most two and a half seconds and saves nothing). When the live count misses its two seconds, the digest shows the saved summary marked `· cached YYYY-MM-DD HH:MM` and still tells skills to run `ctx read`. A summary older than 7 days, saved for another context file, or not readable is never used; nothing is written for a context outside `~/.grow-pm`; a live count that fails in time is never replaced by the cache; days of the last checks that miss their half second keep the days saved before.
- **Registrations within a time budget** — each is read within 1 s in the hook and 3 s in `ctx`. One still downloading (iCloud) is named: `unreadable registration: <path> (<reason>)` in `repo list`, `repo status` and `provider plan|apply` without a repository; "— a registration could not be read …; it may still be downloading" when `provider adopt|plan|apply` cannot find the repository it names; and the card keeps its `Repos` line rather than rebuild it from a partial list.
- **`ctx provider apply`** — `--choose a=mine b=theirs` and `--add x y` take several answers; an answer given in the repository's place, or a repository given as a block, is exit 3 before anything is fetched or written; an answer for a block whose markers are broken is reported (`не застосовано: --choose/--add <id> — у блоку зламані маркери …`, `ignored` value `"!"`) instead of being dropped.
- **`ctx undo`** names the records it could not put back to the last compiled text (`records_not_reverted`).
- **Messages** — an unavailable source lists only the blocks you still hold and says how to retire them by hand (`context-provider-protocol.md` §12.2); the usage text names both readings of exit 5; bidi overrides and the byte-order mark are stripped from server text like other control characters; a `rank` longer than nine digits, quoted or not, falls back to the authority's.
- Tests: `ctx_cli_test.py` 299, `ctx_blocks_test.py` 261, `ctx_repos_test.py` 171, `ctx_mcp_test.py` 135, `ctx_ops_test.py` 134, `session_start_test.py` 49, `ctx_common_test.py` 17 checks — each new check failed before its code. A whole-branch review found five more defects (the summary after a write read every block state on the 30 s budget; a skipped registration was silent in provider scope and the card; a repository given as `--add` reached the lock; an unquoted rank bypassed the cap; a linked `~/.grow-pm/local-context.md` never refreshed the summary) — each fixed with a check that failed first.

### Backwards compatibility

- `repo status`'s `source_version` no longer falls back to the registration's version — that value is now `registration_version`. Every other `CTX_RESULT` change adds keys.
- `--choose a=x --choose b=y` works as before. `ctx provider apply --add BLOCK REPO` (the repository last) used to work and is now refused with a hint — put the repository first.
- A new file, `~/.grow-pm/.ctx-summary.json` (counts only, no context text), rebuilt on its own; deleting it is safe.
- No skill renamed, no description changed: routing is as in v3.13.0.

---

## v3.13.0 (2026-10-14)

**Repositories and block merge** (Context Core, phase 3 — first release). A product can now take context blocks from any number of repositories — a team's or an organisation's shared core, reached through its MCP server or its folder — and a refresh is one pass instead of a regenerated file: `ctx provider plan` shows what changed, `ctx provider apply` writes it, and a question comes only where both the repository and you changed the same block. Verified on a copy of a real context against a real core over MCP and from its folder: every block matched byte for byte and both sources gave the same plan.

MINOR: new `ctx` commands, three new modules, registration v2, context-connect 0.3.0.

### Added

- **Registration v2** (`references/context-provider-protocol.md` §3b): `products`, `rank`, `core_root`, `namespace`, `blocks_file`, `blocks_source` (`auto` | `mcp` | `paths`), `endpoint` (`url`, `root`, `headers_env` — the name of an environment variable, never its value), `home_record`. v1 registrations read as before; one without `namespace` takes the core manifest's, with a warning to add it. `ctx repo list | status`.
- **A stdlib MCP client** (`scripts/ctx_mcp.py`): Streamable HTTP, JSON or SSE, session id, 3 s probe, 30 s call, 2 retries; calls only `vault_get_note`, `vault_list_by_folder`, `vault_search`, `brain_status`, `brain_recent_changes`; no redirects, 32 MB cap; a header value or URL secret never reaches an error. Validator check 17 keeps the allow-list inside the contract.
- **Block state and merge** (`scripts/ctx_blocks.py`, §12): blocks stay regions in your records; the store keeps, per repository, what each block was when the repository last gave it (the base, with the last 10). `ctx provider adopt` records the bases for blocks already in your context; `ctx provider plan` shows `=` `~` `✎` `⚠` `+` `−` `✂` `?`; `ctx provider apply` writes one pass (snapshot, records, state, journal, compile) — `--choose B=theirs|mine|both`, `--add B`. Exit codes 0 / 2 decisions waiting / 3 / 4 / 5 a repository unavailable, nothing written.
- **Your edits are kept**: a block you edited is never overwritten; a block the repository removed while you had edited it is a question (`mine` keeps its text as yours); `both` keeps the two texts in one region.
- **Never a silent change from a bad source**: an empty, cut or foreign blocks file, an empty server answer, a source that offers none of your blocks, or a team block whose core folder, manifest or cards are missing or still downloading from iCloud → "unavailable", nothing written; a source behind your base is not taken back.
- `ctx read` marks each repository block with its source and the day it was checked, and a field or subsection missing from your own text is taken from a block with that mark; the card has a Repos line; the session digest dates a provider by its last check. Validator check 18 keeps the fixtures' regions well-formed.

### Changed

- **context-connect 0.3.0**: with a context store, Refresh is `ctx provider plan` → one message about ⚠ / + / ? only → `ctx provider apply`; Connect inserts the chosen blocks and adopts them. A Refresh keeps a registration you completed (only the sync dates move) and never stamps `Updated:`, appends changelog tables or rewrites the Vault Search line. Without a store the proposal path is unchanged. The bundle builder (1.1.0) proposes registration v2.
- `references/context-protocol.md`, `context-provider-protocol.md` (§12 new), `vault-schema.md`, `host-profiles.md`, `connect-steps.md`; snapshots now include `.state/` subfolders.

### Fixed

- `ctx undo` after an Obsidian edit of a record that a sync imported now reverts that edit too (found in the v3.11 acceptance run).

### Not in this version

- Automatic refresh, the plugin's own copy of an MCP-only core, the cascade between repositories and `ctx explain` (v3.14.0); entities and cross-store links (v3.15.0); a declared overlay, identity and the provider kit (v3.16.0).

### Backwards compatibility

- Without a registration that offers blocks, nothing changes. A v3.12 store keeps working; the first provider command adds `.state/blocks/`.
- Managed regions: an agent or skill still never writes inside one; a person's edit inside a provider block is now kept (and merged) when a context store exists.
- No skill renamed, no description changed: routing is as in v3.12.1.

---

## v3.12.1 (2026-10-12)

**Your own sections reach the skills again; `ctx undo` after an import is whole.** Found in the v3.11 acceptance run on a real store: since v3.12.0 a skill reads only what `references/context-manifest.yaml` names, and the manifest — shipped with the plugin — cannot name a user's own `##` sections, so none of them reached any skill (before v3.12 skills read the whole file and saw them). And `ctx undo` after a sync that imported a direct edit or removal restored the records but left `local-context.md` as edited, so the next sync applied the edit again.

PATCH by the owner's decision: it repairs a v3.12.0 regression and an undo defect; the one new command exists only to make the repair usable (plugin-configurator 2.15.1).

### Added

- **`read_by`** — an optional key of a `custom` or `setting` record: `all`, or skill names. `ctx read --skill S` adds the record whole for those skills; a `custom` record without it is named in one line — `Власні секції без призначення: <title> (<id>), … — ctx get <id>, якщо запит їх стосується` — and the skill reads it when the request is about it. The Obsidian property works too, as a list, a comma string or a hand-typed `[a, b]` (which used to make the record unreadable).
- **`ctx assign ID all|none|S1,S2`** — sets or clears `read_by` (an unknown skill or another record type → exit 3); a snapshot and a journal line, the copies do not change, the record's verified date stays.
- `ctx validate` and `ctx status` list the `custom` records without `read_by` and warn about unknown names; the session digest adds `· N custom unassigned`; `ctx read` output over 8,000 tokens ends with a warning naming the largest record.
- **plugin-configurator 2.15.1** — the Update item "Who reads custom sections" proposes an assignment per section (`all` for rules that apply to any work, otherwise the skills its content serves) and applies it with one confirmation; Validate lists the unassigned ones.
- Tests: `ctx_read_test.py` 27, `ctx_store_test.py` 50, `ctx_cli_test.py` 80, `session_start_test.py` 25 checks — each new check failed before its code. A whole-branch review found two more defects (an undo of a compile snapshot became a no-op; `assign` marked the record verified); each was fixed with a check that failed first.

### Fixed

- **`ctx undo` after an import** — the copies are rebuilt from the restored records, so undoing a sync that imported an edit or a removal undoes it in both copies and leaves the store in sync; the edit stays in the `pre-undo` snapshot. Undoing only a compile's own snapshot (a mirror created or rewritten) keeps the restored copies.
- v3.12.0 minors: `ctx card` keeps the stale and archive marks; `ctx read --product X` on a context without products says the product is missing instead of listing none; a typed `ctx get` of a placeholder (`_(not set)_`) prints it with `not_set` instead of "no field"; an internal error in `ctx read` is no longer reported as "no manifest entry"; the card's platforms match a heading with a qualifier ("Platforms (mobile first)"), as `ctx read` does.

### Backwards compatibility

- Nothing changes until a record gets `read_by`: unassigned sections behave as in v3.12.0, plus the one line naming them. A v3.12.0 engine keeps a `read_by` key it does not know.
- `ctx undo` now also rewrites `local-context.md` and its vault mirror when the undone change was an import — that is the documented behaviour ("`ctx undo` brings it back") the engine did not deliver.
- No skill renamed, no description changed: routing is as in v3.12.0.

---

## v3.12.0 (2026-10-12)

**Lean reading, record lifecycle, freshness and typed fields** (Context Core, phase 2 — second half). With a context store, a skill no longer reads the whole `local-context.md` at Step 0: `ctx read --skill <name>` gives it the context card plus only the fields and subsections its entry in `references/context-manifest.yaml` names. On a real 926-line context about 25,600 tokens became 900–3,000 per skill (measured with this release's engine on the release machine, all 33 skills). Records get a lifecycle (invalidate → archive → trash, `restore`), a verified date with a time to live (a stale fact is stated "as of" its date), and typed fields; `ctx` writes only under `~/.grow-pm` and the storage root. Without a store nothing changes.

MINOR: new `ctx` commands, two new shared files (`references/context-manifest.yaml`, `references/context-fields.yaml`), validator check 16, and the configurator's "Review stale records" (plugin-configurator 2.15.0).

### Added

- **`ctx read --skill S [--product P]`** — reads only: the card, then one block per record the skill needs (`## <title> · <id> · перевірено <date>`, with `⚠ застаріле` or `⚠ неактуально` when that applies) and one closing `Відсутнє:` line. Edits not imported yet, new sections and records missing on disk are read from the canonical copy with a note; archived records never appear; several products and no `--product` → the list and the exact command to run again; exit 3 (a record still downloading, an unknown skill) → the skill reads the file whole. `ctx get <id> --section "…"` gives any other subsection.
- **`references/context-manifest.yaml`** — what each of the 33 skills reads (fields, `####` subsections matched by the start of their heading, settings by the start of their title, obligatory ones marked); validator check 16 keeps it in step with the skills and with "Which Skills Read What".
- **Lifecycle** — `ctx invalidate ID --reason R` (a status region after the heading; the record stays in the file), `ctx archive ID` (to `{store}/archive/<year>/`, its id reserved), a trash for every record a sync removes (`~/.grow-pm/trash/`, 30 days), `ctx restore ID` (the body and both copies come back byte for byte, inside its organisation), `ctx list --archived | --trash`; the archive is part of every snapshot.
- **Freshness** — `verified` per record (every write, an Obsidian edit picked up, `ctx verify ID… | --stale`); default TTL 90 days for products and teams, 180 for organisations, the profile and settings, none for custom sections (`ttl_days` overrides, `0` = never); stale records counted in the digest (`· K stale`), marked on the card and in `ctx read`, listed by `status` and `validate`.
- **Typed fields** — `references/context-fields.yaml` (role, role scope, level home, email; Jira key, Confluence space, platforms, locales, URL; onboarding mode and deferred steps; the Judgment switches): `validate` warns about a mismatch, `set` refuses one with the allowed values, `get --json` returns the parsed value. The text line stays the source of truth; Obsidian properties added to a record are kept.
- Tests: `ctx_read_test.py` (new, 18 checks); `ctx_store_test.py` 47, `ctx_ops_test.py` 64, `ctx_cli_test.py` 56, `ctx_common_test.py` 16, `session_start_test.py` 24 — each new check failed before its code. A whole-branch review before the release found eight more defects (two of them a restore that could break the file on the next sync); each was fixed with a check that failed first.

### Changed

- **Step 0c** (`references/local-context-protocol.md`): with a store and a shell — `ctx read`; with a filesystem only — the card and the manifest's records, whole; without a store — the whole file, as before. The session digest tells skills that `ctx read` replaces reading `local-context.md`, with the product the request names — an isolated scenario run showed skills follow the digest and their own "read local-context.md" line, not the protocol.
- **plugin-configurator 2.15.0** — Validate counts stale, invalid and archived records; the Update item "Review stale records" confirms, edits, invalidates or archives each.
- `references/context-protocol.md` (§5a–§5d), `context-schema.md`, `persistent-storage.md`, `host-profiles.md`, `testing/host-matrix.md`; `.gitignore` ignores a project-local `.codex/config.toml`.

### Fixed

- **Write allow-list** (an internal audit of the v3.11 engine): every write or delete target, after its links are resolved, lies under `~/.grow-pm/` or the storage root — anything else is refused (exit 4) before a byte is written; `undo` writes only the current copies and store, never a path from a snapshot's manifest; `--store` only for reading commands; `migrate --apply` never creates a missing vault folder. Not a privilege escalation — `ctx` runs as the user, without network or code execution — but two gaps were real and are closed.
- From the v3.11 review: a renamed section takes the type of its new heading; products and teams follow the organisation above them; an Obsidian edit of a record is journalled with its id; records imported by `compile` keep `import:home` / `import:mirror`; a half-migrated store says which folder to remove; a vault that is not mounted is reported as "store unavailable"; a migrate dry run that does not give the file back exits 3; `status` shows the last snapshot, `list` the modified date; CRLF in a record's frontmatter is read.

### Not in this version

- Provider blocks as records with a three-way merge (v3.13.0); the configurator as a loop, deltas proposed by skills, a `/context` command and checking records against the connectors (v3.15.0); an index and a graph (v4.0.0).

### Backwards compatibility

- Without a store nothing changes: no new digest line, the v3.11 hint, Step 0 reads the file as before.
- A v3.11 store keeps working: its records render byte-identically until something writes them; the first v3.12 compile adds `freshness_since` to the state (one write) and the freshness clock starts there.
- `ctx set` now refuses a value outside its type (a role outside the list, a one-letter Jira key) with exit 3; a context file outside `~/.grow-pm` and the storage root makes writing `ctx` commands refuse (exit 4).
- No skill renamed, no description changed: routing is as in v3.11.

---

## v3.11.0 (2026-10-09)

**The context store: your context as records, `local-context.md` as their compiled view** (Context Core, phase 2). The context can now live as records — one markdown note per section of `local-context.md` — in the vault (`{storage_root}/_System/context/records/`). `local-context.md` becomes the compiled view: every skill reads it exactly as before, and anything written into it directly — by a skill, another plugin or the user in Obsidian — is imported back into the records. A deterministic engine, `ctx`, moves a single-file context in losslessly (it proves the compile gives the file back byte for byte before it writes anything), snapshots before every change, keeps a journal, undoes and generates a context card (`INDEX.md`). The sixth contour, **Context** — `context-connect`, `context-navigator` and the store — is declared in the README, the three manifests and `AGENTS.md`. Without the move nothing changes.

MINOR: a new engine (`scripts/ctx.py`, `ctx_store.py`, `ctx_ops.py`), a new shared protocol (`references/context-protocol.md`), a digest line, and the sync step in the three writers (plugin-configurator 2.14.0, context-connect 0.2.0).

### Added

- **`ctx`** (`scripts/ctx.py` over `ctx_store.py` — split rules, record format, compile, card — and `ctx_ops.py` — lock, snapshots, migrate, sync): `status`, `migrate [--apply]`, `compile`, `sync`, `get`, `list`, `set`, `append`, `add`, `snapshot`, `undo`, `validate`, `card`. The last stdout line is `CTX_RESULT {json}`, a conflict prints `CTX_CONFLICT {json}` before it; exit 0 ok · 2 a decision is needed · 3 bad input, no store, an unreadable or missing record · 4 refused (managed region, provider boundary, busy lock, existing store, `undo` while edits wait). Standard library only.
- **Split rules** — every `##` section is a record; inside `## Organization:`, so is every `### Product:` and `### Team:`; fenced code and managed regions never split (a region that wraps a `##` section starts its own record). The records cover every byte once, so the compile is byte-identical by construction. Ids are `type.slug` and survive a renamed heading.
- **Direct edits** (`ctx sync`) — both compiled copies (`~/.grow-pm/local-context.md` and the vault mirror) are cut by the same rules and compared with the last compile: changed, new, renamed, removed and reordered sections reach the records; a record edited in Obsidian is compiled out. Three or more removals at once, the same section changed in the file and in its record, or changed differently in the two copies, are a question: exit 2 with both versions, then `--resolve <id>=file|record` or `--accept-removals`.
- **Safety** — a snapshot before every change (`~/.grow-pm/snapshots/`: the last 20 and one a day for 14 days, identical ones reused) and a journal line after it, atomic writes, one writer at a time (`~/.grow-pm/.ctx.lock`, stale after 120 s), direct edits imported before every write, never a write into a provider's folder or managed region. Records are read within a time budget (30 s, `GROW_PM_CTX_READ_TIMEOUT`): a record that is missing on disk or still downloading from iCloud stops the run before anything is written, with the way back.
- **Context card** `INDEX.md` — at most 200 lines: who you are, onboarding, products, teams (member counts, never names), vaults and providers, one line per record.
- **Session digest** — with a store, one read-only line, `context: records N · card M lines · in sync` (or the edits waiting, or the conflicts), read within a two-second budget.
- `references/context-protocol.md` — the store, the split rules, the record format, the commands and their output contract, the sync, snapshots and the journal, hosts.
- Tests: `ctx_store_test.py` (34 checks), `ctx_ops_test.py` (35), `ctx_cli_test.py` (33), `ctx_common_test.py` 8 → 12, `session_start_test.py` +3 (the context line); fictional fixtures in `testing/fixtures/ctx/` (minimal; typical; rich — provider regions, a fenced block with `## ` lines, Cyrillic headings, another plugin's section) and a golden card. A whole-branch review before the release found a compile that could rewrite a copy without a snapshot; it was fixed with 16 more checks, each of which failed first.

### Changed

- **Context Enrichment** (`references/local-context-protocol.md`), **plugin-configurator** 2.14.0 and **context-connect** 0.2.0 run `ctx sync --source <writer>` after saving `local-context.md` when a store exists — the digest shows its line, or, on a host without the digest (Codex CLI), the store's `.state/` folder exists; a conflict is shown and asked.
- **plugin-configurator** offers the move once at the end of onboarding and as the Update item "Move my context to records"; Validate reports `ctx status`.
- **Six contours** in the README, the three manifests and `AGENTS.md`; `context-schema.md`, `persistent-storage.md`, `host-profiles.md` and `testing/host-matrix.md` describe the store and what `ctx` needs (FS and SHELL).
- README and `host-profiles.md` §7: after a release, `codex plugin marketplace upgrade` refreshes the marketplace (`marketplace add` does not), and `codex` commands run from a folder without a project-local `.codex/config.toml` (measured, codex-cli 0.153.2).

### Not in this version

- Skills reading the card and only their own records, archive and trash, freshness (TTL) and typed fields (v3.12.0). Until then, a property added to a record note in Obsidian is not kept by the next `ctx` write of that record (the snapshot keeps it).
- Provider blocks as records with a three-way merge (v3.13.0); the configurator as a loop and a `/context` command (v3.15.0); an index and a graph (v4.0.0).

### Backwards compatibility

- Without the move nothing changes: no store → no digest line, `ctx sync` is a no-op, every skill reads `local-context.md` as before.
- The move is lossless and reversible: `ctx migrate` shows the records and the round-trip proof first, `--apply` does not touch the compiled copies, and `ctx undo` right after it removes the store.
- Hosts without a shell edit `local-context.md` as before; the next `ctx` run on a host with a shell imports the edits.
- No skill renamed and no description changed: routing is as in v3.10.1.

---

## v3.10.1 (2026-10-09)

**Routing that survives a crowded host, and the phase-1 fixes.** Claude Code caps the skill listing at 1% of the context window and, over the cap, lists the least-used skills by name alone (measured in Claude Code 2.1.292, `references/host-profiles.md` §7). On a machine with about 150 skills, 16 of the plugin's 33 skills showed no description, and the model routed on names: that explained 8 of the 10 trigger misses left open in v3.10.0, and why the guards tried then changed nothing — they sat in descriptions the model never saw. Every description now keeps its lead and nearest-neighbour guard and drops the long trigger tail (21,217 → 9,787 characters for all 33), so the plugin fits the room it already had; the full trigger lists move into each skill's `## Routing` section. Trigger evals on the same machine and harness: 169/178 → 178/178 as the host lists skills (a row that missed was re-run three times and scored by majority; the nine rows that also fail on v3.9.0 now pass), 177/178 → 178/178 with every description visible.

PATCH: the 33 descriptions (each skill +0.0.1), fixes in the bundle builder, the session digest and the branch scan, a validator cap, the eval method and its runners.

### Changed

- **All 33 skill descriptions** (each skill +0.0.1) — within 400 characters each and 9,787 together (were 21,217): the lead and the nearest-neighbour guard as before — what Codex shows — and the strongest Ukrainian and English triggers. Where a miss showed a gap: product-research names research plans and «як конкурент зробив…»; product-reporter is "not a plan-vs-actual retro (quarterly-planning)"; roadmap-architect is "not a strategy memo (write-concept)"; product-landscape is "not its setup (plugin-configurator)"; design-bridge keeps «через мій дизайн-тулкіт», since with the listing freed a design toolkit's own skill competes for that phrase. The v3.10.0 description of each skill is kept word for word in its new `## Routing` section, so no trigger or boundary is lost.
- **`context-connect`** opens with "Shared team core — connect, refresh bundle, add MCP provider", so a refresh request reaches it on a host that shows about 53 characters of each description (Codex with 118 skills sent «онови мій пакет з ядра» to the configurator). «підключи Obsidian-вейлт» stays with the configurator. Group T on that Codex configuration: 25/28 → 28/28 over two runs.
- **Validator check 12** — each description within 400 characters and all of them within 10,000, so the listing does not grow back.
- **Trigger evals** run twice — as the host lists skills, and with every description visible (`SLASH_COMMAND_TOOL_CHAR_BUDGET` raised for the test processes only). A miss in the first mode only is a visibility problem, in both a description problem. Two runners now live in the repository: `testing/trigger_claude.py` (a staged copy whose digest reads a fictional context, never the user's `~/.grow-pm`; no MCP servers; no write tools) and `testing/trigger_codex.py` (the working tree as a temporary marketplace; the installed copies disabled for these processes only; usage-limit replies counted as errors, not misses). L8 (a typed command) is scored on Codex only, since Claude Code runs a typed command before any routing; E2 and R13 accept a Lazyweb skill when the user's own global instructions send UI work there.
- `references/host-profiles.md` §7 records the measured listing budget and what a user can do about it; the README hosts table and AGENTS.md known gap 1 follow.

### Fixed

- **Bundle builder** (`scripts/provider_bundle.py`): a refresh keeps the user's own note on the `Updated:` line (the line was rewritten whole); registration paths and `writable` globs are written in quotes (a folder with ` #` in its name was cut on read-back); a begin marker without its end in the proposal stops with exit 4 (only nesting was checked); a provider title with `,` or `;` is quoted in the `### Vault Search MCP` bullet, and the bullet parser respects quotes; `--dry-run` is now `--propose-only`, since it writes the proposal files — the old name still works and says so.
- **Session digest**: the index date is read from a `meta` table with `k`/`v` columns too — a legacy spelling met in a real index; `key`/`value` stays the contract (protocol §10); the index path is URI-escaped (a path with `?` or `%` read as "no index"); a `_none_` placeholder is not a deferred onboarding step; a registration that does not parse is named in one digest line instead of disappearing.
- **Branch scan**: a base branch missing from the clone (a shallow clone) is one line and exit 2, never a traceback or a pass.
- Tests: `provider_bundle_test.py` 41 → 49 checks, `session_start_test.py` 12 → 16, `branch_leak_scan_test.py` 4 → 5 — each new check failed before its fix.

### Backwards compatibility

- No skill renamed, no step added or removed: only descriptions, two builder flags, digest lines and the scan's exit code. Registrations written by v3.10.0 read as before; `--dry-run` keeps working.
- On Claude Code with many plugins, a user who still sees misrouting can raise `skillListingBudgetFraction` in `~/.claude/settings.json` or disable unused plugins with `/skills` (`references/host-profiles.md` §7).

### Not in this version

- K8 («налаштуй секцію глосарія і стилю в конфігурації плагіна») passes 2 of 3 on Claude Code, 3 of 3 on v3.9.0 — to watch, not tuned: a change for one row moved others in v3.10.0.
- Context records instead of the single `local-context.md`, the `ctx` command line and a generated context card (v3.11.0).

---

## v3.10.0 (2026-10-08)

**Shared-context providers: connect your context to a team's core.** First phase of the Context Core programme. A team or an organisation can share its core knowledge — team cards, a people registry, missions, metrics, rules, exported pages — with every colleague's plugin, and the plugin now treats such a core as a *provider*: one tool contract, one manifest, one registration per user, one write boundary. What a separate companion plugin used to do for one organisation — e-mail → team → role, a role-filtered bundle, context blocks merged into the user's context, rules for the agent, a session digest — is now part of this plugin and works for any provider that ships a manifest.

MINOR: two new skills (33), a new shared reference, a new script and its templates, a third hook, lint check 26, a branch scan in the release pre-flight.

### Added

- **`references/context-provider-protocol.md`** — the contract `vault/v1` (`vault_search`, `vault_get_note`, `vault_get_links`, `vault_graph_context`, `vault_list_by_tag`, `vault_list_by_folder`; optional `brain_status`, `brain_find_entity`, `brain_recent_changes`; recommended `search` / `fetch` aliases), the provider manifest (`_System/provider-manifest.yaml`, every path relative to the core root), the user-side registration (`_System/providers/<id>.yaml`: read-only `paths`, `writable` overlay globs, freshness), the interim `### Vault Search MCP` declaration in `local-context.md`, detection and the L2 binding, routing across providers (own vault → local index → snapshot → live; dedupe by provider + path; reciprocal-rank fusion), freshness and offline behaviour (index older than 36 hours, snapshot older than `stale_after_days`, one line per session), the write boundary, generated regions, the provider kit a team ships, and the index schema v1 for any local index.
- **`context-connect` (v0.1.0)** — connect, refresh or enrich: dry run with "I see you as <role> in team <title>", the Jira write-scope question (never where the bundle goes: an unpacked core is refreshed in place), the bundle, the proposal (`local-context.proposed.md`, `context-merge-report.md`, `team-context.md`, `provider-registration.proposed.yaml`), one question per discrepancy, backup and apply, a five-question focus interview, the registration. MCP-only providers are registered without a bundle; the host configuration entry is shown, never written.
- **`context-navigator` (v0.1.0)** — answers from the shared core through the provider's `playbook` and `routing_hints` and the graph, with the note path, the period and source of a number and the snapshot date; a reference value is never the current one; meeting participants resolve through the provider's `people_resolver`; never writes into the provider's folders.
- **`scripts/provider_bundle.py`** (with `scripts/provider_templates/`) — the bundle builder: role-filtered copy, registry cards with registry fields only, personal-layer links turned into text, the entry note pruned, the team block and the context blocks proposed, the provider entry and the registration proposed; blocks the user declined (`--skip-blocks`, kept in the registration's `skip_blocks`) are never proposed again, so a refresh is one confirmation; blocks whose content did not change are left byte for byte, and a refresh with nothing new returns the user's file unchanged. A block id never matches a longer one (`team` vs `teams`): the merge this builder generalises let the `team` block swallow every block between `teams` and itself and re-add them elsewhere — a likely source of the duplicated sections users saw. Every folder, label, marker namespace, exclusion, deny pattern and note template comes from the manifest; the plugin ships English defaults. Team membership is matched as a whole slug (`team-alpha` never takes in `team-alpha-two`). A role inferred from the registry that the role model lacks falls back to `pm` (else the first profile) with a notice; an explicit `--role` it lacks stops. The proposal holds the user's whole context, so `--proposal-dir` writes it, the report and the registration into a private folder when the core syncs back to others, and a context copy placed there is picked up without a flag. Exit codes 0 / 2 `UNKNOWN_TEAM` / 3 a missing or unreadable core, manifest or role model, a pattern that does not compile, or an explicit role the model lacks — one line naming the file, the line or the key / 4 a provider block that matches a deny pattern (the line names the block; the user's own text is never checked) or nested markers — nothing written.
- **`scripts/ctx_common.py`** — a YAML-subset reader (no third-party parser, so a manifest parses the same on every host), managed-region stripping, the `## Obsidian Vaults` and `### Vault Search MCP` parsers, registrations and the component-wise boundary test.
- **Third hook — provider boundary.** `PreToolUse` on `Write`, `Edit`, `MultiEdit`, `NotebookEdit`: a file inside a registered provider's folder and outside its `writable` paths asks for confirmation with the reason and the alternative. Same opt-out as the write gate. Paths are compared after resolving symlinks (synced vaults are often symlinked), a relative path resolves against the session's working directory, and the context is found the way the digest finds it, so a hosted session with the context in a connected folder is guarded too.
- **Tests:** `testing/ctx_common_test.py` (8), `testing/write_gate_test.py` (14), `testing/provider_bundle_test.py` (41 checks on the fictional fixture core `testing/fixtures/context-connect/zorg-core/`), `testing/session_start_test.py` (4 → 12), lint check 26 `provider-contract` with a seed (27/27), `testing/branch_leak_scan.py` with its test (4), trigger-evals Group T (14 phrases; live on Claude Code 28/28 after one description fix, on Codex CLI see the results log), test-case section v3.10.0.

### Changed

- **Vault level L2** (`vault-protocol.md`, `local-context-protocol.md` Step 0h / 0.5): L2 is "a provider answers `vault/v1`". The algorithm named `test_mcp_connection`, `mcp_full_text_search` and `mcp_get_backlinks` — tools no server had — since v1.6.0. Step 0.5 searches every reachable provider, labels each result with its source and snapshot date, and says once when a provider is stale or unreachable. `vault_save` honours `sync_mode: read-only` (it was offered by setup but written to as `auto`) and never saves into a provider's folder.
- **Session digest** (`scripts/session_start.py`): products are counted in `## Organization` sections only and deduplicated (the Landscape section's per-product headings were counted as products); teams outside managed regions; a vault declared as a table now counts as configured; new `providers:` and `bundle:` lines; `GROW_PM_PROVIDER_PATHS` exported for Bash; both exported paths are shell-quoted, so a folder name with spaces or non-ASCII letters reads back intact (the JSON quoting before left `\uXXXX` escapes that bash keeps literally).
- **`vault-schema.md`:** optional `id`, `aliases`, `modified`, `last_verified`, `archived_at`; a "Generated regions and layers" section (one marker grammar, written only by scripts; the user's layer vs a provider's read-only folders); the `moc` type (37 types).
- **`persistent-storage.md` and README:** one storage story — `~/.grow-pm/` for the context file, service data and backups; the vault as `storage_root` with a write-through mirror — replacing the pointer-file description of an early design that never shipped; one backup rotation (last 5) instead of 3 in one place and 5 in another; the mirror map lists the glossary, style profile and experiment registry, which skills already mirrored but recovery did not restore.
- **Configurator** (v2.13.0, text only): the shared-context entry point hands off to `context-connect`; S-6 detects a search provider by the contract, not by an `obsidian` tool name; the Update menu has "Shared context providers"; Validate V-5 shows one row per provider (reachable, index or snapshot date, stale); `context-schema.md` defines the `### Vault Search MCP` subsection; its description now names the Obsidian vault in its first words, so «підключи Obsidian-вейлт» reaches the configurator on a host that shows only the start of each description.
- **`release-manager` (v0.4.0):** Step 1 runs the branch scan for organisation identifiers before anything is pushed; a hit in an unpushed commit is rewritten, not fixed by a later commit.
- `integration-strategy.md` (providers are detected by the contract and declared by their manifests, never in `.mcp.json`), `harness-map.md` (Guardrails and Memory rows), `commands/status.md` (vault level by contract).

### Not in this version

- Context records instead of the single `local-context.md`, the `ctx` command line and a generated context card (v3.11.0).
- Three-way merge of provider blocks with stored bases, declared overlays for corrections to a provider, precedence rules and remembered resolutions (v3.13.0).
- The configurator as a loop: bootstrap from connectors and providers, proposals from skill runs, validation and consolidation (v3.15.0).
- A local index and graph built by the plugin itself (v4.0.0); until then any index that follows the schema v1 answers `vault/v1`.
- Routing drift on the current default model (next PATCH). The live run found ten trigger-eval misses that fail the same way on v3.9.0 in the same environment, so they predate this release: C6, J6, L8, O4, O8 and R19 route to a neighbour inside the plugin, and E2, R13, R15 and R16 are answered by other plugins installed on the test machine. A retune of six descriptions was tried and reverted: it fixed O4 but moved J9 to another skill and left the rest unchanged, so the next attempt needs a different approach than more guards.
- Codex in a crowded configuration. With 118 listed skills Codex shows about 55 characters of each description, so routing there rests on skill names, and «підключи Obsidian-вейлт» went to `context-connect`. The configurator's description now starts with the Obsidian vault (no regression on Claude Code across groups K, L, N, O and T); the Codex re-check of Group T waits for the account's usage limit to reset.

### Backwards compatibility

- A `local-context.md` without `### Vault Search MCP` and without registrations works exactly as in v3.9.0: no provider, Step 0.5 at L1 (or L2 through a server that speaks the contract), no new question in any existing skill.
- Provider blocks already merged into a context (between `<!-- <namespace>:begin id=… -->` markers) keep working: the bundle builder updates them in place; the digest stops counting their headings.
- A generic Obsidian MCP server without `vault_search` and `vault_get_note` now counts as L1. v3.9.0 marked any tool with `obsidian` in its name as L2, while the search tools its algorithm named existed on no server; S-6 and Step 0h now detect a provider by the contract `vault/v1`, and S-6 asks nothing new.
- The new hook asks only for paths under a registered provider root outside its `writable` globs; with no registration it never fires. `/grow-product-manager:setup --write-gate off` disables both gates.
- Users of a separate companion plugin for a team's core: keep the core folder, uninstall the companion, ask the provider's owner for the manifest (or add one, protocol §3a), and say "connect me to the team vault" — the existing bundle is refreshed in place and the registration replaces the companion's session digest.

---

## v3.9.0 (2026-10-06)

**Build first, a built-in opponent, learning modes — and the Judgment Core + Role Layer programme is complete.** Sixth and last release of the programme (v3.4.0 → v3.9.0).

The plugin now offers the cheapest way to settle a risky assumption before a long document. It gives consequential artifacts a pre-mortem and pre-committed kill criteria, and specs AI features as a behaviour spec, an eval set and an acceptable error rate. It checks a spec is ready before it becomes tasks, lets the PM do the first pass of a synthesis themselves, and never learns to drop a counter-argument.

The only new question in a skill run is opt-in: the PM-first pass under `learning_mode: pm_first` (two configuration exceptions under Backwards compatibility). MINOR: two new built-in templates, new steps in 15 skills, two new `## Judgment` behaviours.

### Added

- **`judgment-points.md` §7 — P4 pre-mortem and kill criteria.**
  - **What it is:** a new partial, `partial/pre-mortem-v1`, inserted by `template-protocol.md` T-5 step 3b ("Inserted sections"). It lists 2–3 failure causes, each tied to the input or section it rests on and with an early signal, followed by kill criteria (signal, threshold, date, then).
  - **Where it appears:**
    - every write-concept concept except the design brief and a release-notes draft — a pre-selected item in the Step 1 block list;
    - A/B specs, where kill criteria are a pointer to the decision rule;
    - AI-feature specs;
    - the quarter plan at scope lock;
    - new missions and initiatives in roadmap-architect `onboard`, and a new epic whose request carries goal or outcome text.
  - **How it behaves:** unknown thresholds read `⚠️ TBD` and are never asked for. Refresh keeps an existing pre-mortem verbatim. A user's own template gets it only through `{{> pre-mortem}}`.
  - **Read-back:** the quarterly-planning retro and the project-planning replan read earlier criteria back as fired, not fired or not measurable, using data they already fetched.
- **§8 — the P6 build-first offer.** New switch `judgment.build_first`, default `on`.
  - write-concept Step 1 names the riskiest assumption. When no evidence covers it, one line in the brief summary offers the cheapest path: a lo-fi prototype for 3–5 real users, a walk of the as-is flow, or an eval set.
  - design-bridge Step 9 offers a build-first prototype, or a standalone mid-fi or hi-fi one, as the spec for requirements-creator (a Prototype IR: screens, states, transitions). diagram-prototyper returns a lo-fi prototype on `return_to: design-bridge`, passed only for the build-first hand-off.
  - It is a line, not a question; never in automated runs; «вимкни» / "turn off" switches it off.
- **§9 — P8 learning modes.** `judgment.learning_mode` now acts. `pm_first` asks the PM to tag a few real items first, or to write their own CJM hypotheses, at four steps:
  - feedback-triage Step 2;
  - meeting-processor Discovery / Interview (Structured MoM);
  - product-research interview synthesis;
  - cjm-research before Step 7.

  It then shows "Your tags vs mine" in the chat. The tags never change the artifact or set `human-validated`. `explain` shows a chat-only "How I got here" block. The default is `off`.
- **`requirements/ai-feature-v1`.** It holds the behaviour spec, eval set (with origin classes), acceptable error rate, kill criteria and tracking plan, and is reached only by explicit AI words (AI / ШІ, LLM, ML model, GPT, chatbot, generative).
  - AI-driven specs on other templates get the same sections, with `⚠️ TBD` cells that are never asked for.
  - A one-line "not solution-shaped" note appears when the problem or outcome prescribes the solution.
- **Spec readiness** (`artifact-style-gate.md`): six elements — outcomes, out of scope, constraints, prior decisions, breakdown, verification. task-creator reports `Spec readiness: n/6 — missing: …` and never blocks or asks.
  - Tasks with a Definition of Done cite `AC-N`.
  - An AI-driven spec gets a pre-selected "QA — Eval set" task option.
- **Self-improvement guard, in full** (`self-improvement.md`, P5). A correction that only removes or softens one of the following is applied to this artifact only, noted in one chat line, and never proposed as a skill change:
  - a pre-mortem, kill criteria, a minority report or a Skeptic objection;
  - a hand-back line, a confidence line or an evidence label;
  - a score, rank, verdict, theme or hypothesis moved to the PM's without new evidence ("agree more").

  A footer or confidence line the user removed at review is not silently re-added. Not in the People contour; a mixed correction is split (its guarded part one-off, the rest the normal flow); a removed `assumed` / `simulated` label stays or its item is dropped (Gate 4b §6).
- **Tests:**
  - lint check 25 `judgment-binds` (Binds coverage plus stale forward markers) with two seeds, and check 23 tightened to a §1 / §2 citation with one more (26/26);
  - output-evals `counter_argument` for every rubric and a full AI-feature rubric with fixture and gold; 10 rubrics of the changed skills run (11 runs, 0.85–1.00, all pass — Results log);
  - test cases TC-jdg-390-* (TC-jdg-05 self-improvement included) and trigger-evals Group S;
  - `host-smoke.sh` runs its Codex leg from a neutral directory, so a project-local `.codex/config.toml` cannot break it.

### Changed

- `pm-mental-model.md`:
  - P4, P5, P6 and P8 act since v3.9.0.
  - Their rule sentences now apply at the steps their *Binds* list, so Step 0j no longer reads them as instructions for every skill.
  - P8 states the opt-in default.
  - §5 lists the new outputs and the creation-step exceptions.
- `local-context-protocol.md`: the `build_first` key (default `on`); bracket notes are ignored when switch values are read; Step 0j item 5.
- `template-protocol.md`: step 3b is "Inserted sections" (role extras plus the pre-mortem, also without a template); step 3a never re-adds a footer the user removed.
- `artifact-style-gate.md`: the Spec readiness section; Gate 4b exempts pre-mortem causes, kill rows, behaviour rules and eval-set expected outputs (hypothetical by nature).
- `data-integrity-protocol.md`: the `spec-readiness` token points to the six elements; `human-validated` is never set by a PM-first tag.
- Other shared references:
  - `debate-protocol.md` — unresolved objections feed the pre-mortem; the minority report is guarded;
  - `roadmap-artifacts.md` §1 and §8 — the quarter-plan section and onboard rules;
  - `planning-core.md` §8 — the read-back and the places that never get a pre-mortem;
  - `harness-map.md`;
  - `vault-protocol.md` — SKILL_CONTEXT_MAP rows.
- Configurator:
  - `## Judgment` gains `Build first`; `Learning mode` acts.
  - Basic records four defaults. Extended asks nothing new and shows both in its "Also set" line.
  - `update config → Judgment` asks all four switches in one call.
- Descriptions (routing): `requirements-creator` names "A/B test and AI-feature specs"; `quarterly-planning` gains "kill criteria / pre-mortem for the quarter plan" / «kill criteria для плану кварталу»; `product-research` gains "let me tag the first interviews myself, then synthesize". Live trigger evals on Claude Code: 16 of 17 groups ≥ 90 % (165 phrases), Group S 16/16; Group L 8/9 — the known L8 status-command row (explicit invocation only). Codex CLI not re-run this version (as since v3.1.0).
- Skill versions:

  | Skill | Version |
  |---|---|
  | `cjm-research` | 0.11.0 → 0.12.0 |
  | `design-bridge` | 0.8.0 → 0.9.0 |
  | `diagram-prototyper` | 0.14.0 → 0.15.0 |
  | `feedback-triage` | 0.6.0 → 0.7.0 |
  | `flow-walkthrough` | 0.6.0 → 0.6.1 |
  | `meeting-processor` | 0.17.0 → 0.18.0 |
  | `plugin-configurator` | 2.12.0 → 2.13.0 |
  | `product-research` | 0.14.0 → 0.15.0 |
  | `project-planning` | 0.5.0 → 0.6.0 |
  | `quarterly-planning` | 0.7.0 → 0.8.0 |
  | `release-manager` | 0.3.0 → 0.3.1 (patch: host-smoke wording — the Codex leg installs HEAD) |
  | `requirements-creator` | 0.16.1 → 0.17.0 |
  | `roadmap-architect` | 0.5.0 → 0.6.0 |
  | `task-creator` | 0.14.1 → 0.15.0 |
  | `template-library` | 0.3.2 → 0.3.3 |
  | `write-concept` | 0.14.1 → 0.15.0 |

  Templates: `partial/tracking-plan` 1.0.0 → 1.1.0.

### Adaptations to the specification

- `judgment.build_first` is a new switch with default `on`, added under P6. The specification's NFR-2 default set gains it.
- The pre-mortem is a partial inserted at named steps, not a section of every template. Gate 4 gets no new part: its presence is checked at T-5 step 3b, by the output-eval criterion and by lint check 25.
- P8 binds four skills. "Strategy framing" in P8's text has no implementing step yet.
- `learning_mode: explain` is a chat-only block, not a reserved value.
- Kill criteria are read back in the retro and replan (not in the specification) so they cannot become theatre.
- No new shared reference. The P4 / P6 / P8 rules live in `judgment-points.md` §7–§9.
- The specification's "provenance" output-eval criterion is `evidence_labels` plus `sources`.
- Round-1 verification fixes: Step 0.5's new types (`walkthrough`, `ab-test-results`, `prototype`) never raise the context question on their own; a fired kill criterion never opens a decision-log offer on its own; one pre-mortem placement everywhere (no "before Kill criteria" clause); PRD kill rows render unless the decision rule has a kill branch with a threshold and a date; the build-first suppression cases spelled out; design-bridge Step 9 only after a build-first upstream or a standalone mid-fi / hi-fi prototype, and `return_to` only for the build-first hand-off; the judgment guard's scope (People contour excluded, a mixed correction split, `assumed` / `simulated` labels per Gate 4b); lint check 23 tightened, check 25's legacy-line skip removed, a new seed (26/26).

### Programme complete — open items

These stay outside the programme. Each would be a later MINOR or PATCH on request.
- P8 for strategy framing.
- Golds and fixtures for the two light rubrics (product-analysis analysis report, brainstorm-features) and for the quarter-plan pre-mortem.
- A durable judgment log; today the guard line lives in the chat only.
- `references/context-budget.md`, still planned.
- Measured, not derived, ChatGPT and Codex-cloud host profiles.
- A live Codex CLI trigger run (last run v3.0.0) — the three descriptions this release changed are routed on Claude Code only.
- Two pre-existing output-eval notes: the built-in task template keeps its fixed Definition-of-Done items on every discipline task ("QA passed" on the QA task too), and write-concept Step 5 re-offers a red-team debate the request already declined.

### Backwards compatibility

- **With `build_first: off` and `learning_mode: off`** (the latter is the default), every skill asks exactly the v3.8.0 questions, except that `update config → Judgment` now asks all four switches in one call, and an AI-feature spec requested by name meets the usual template choice when a user-global requirements template exists. The build-first line is not a question either way. A judgment-guard correction is no longer offered as a skill improvement — one chat line instead (`self-improvement.md` Step 2).
- **New for everyone:**
  - a pre-mortem section in concepts (deselectable in the Step 1 block list), A/B and AI specs, quarter plans, and new mission and initiative pages or descriptions;
  - kill-criteria read-backs in retros and replans;
  - the spec-readiness line;
  - `AC-N` ids in Definitions of Done instead of copied criterion text;
  - a pre-selected eval-set QA task for AI-driven specs (drop it in the answer to skip; a QA row in task-format);
  - AI-driven specs get the AI sections, AC-eval and the auto-selected `requirements/ai-feature` template; template-free specs get an Out of scope section; every spec gets the not-solution-shaped chat line and the matching Analyze & Improve advisory;
  - the one-line guard notice on such corrections.
- **Jira writes:** an `onboard` epic description that carries a pre-mortem is longer, so it may now meet the host write-gate prompt. Epics that task-creator creates get no pre-mortem.
- **Unchanged:** automated runs never get the build-first line, the PM-first question or `explain`. Older `local-context.md` files without the new keys read the defaults, and any bracket note on a value is ignored.

---

## v3.8.0 (2026-10-06)

**Evidence classes.** Fifth release of the Judgment Core + Role Layer programme.

Every number, quote, benchmark or "users want X" in a product artifact now says how it is known: `observed`, `measured`, `reported`, `external`, `simulated` or `assumed`. Synthetic users stay rehearsal, for every role. A claim the data cannot support is handed back with the human step that would settle it.

The release adds no question, no switch and no role-dependent behaviour. MINOR: a new gate check, a new gate part, new steps in 18 skills and 16 templates.

### Added

- **Gate Check 6 — Evidence Class & Frontier** (`data-integrity-protocol.md`, implementing P1, P7 and P10).
  - **6a: class assignment.** The Gate Check 5 marker decides the class.
    - `measured` covers only data the skill read itself after its gate, or counted itself from a system of record.
    - Figures the user pastes are `reported (<who>)`.
    - A synthesis keeps the class of what it summarises: an AI summary of a real ticket stays `reported`.
    - A prepared report the user hands over (a PDF, a dashboard or report screenshot) is `reported (<who>)` like pasted text; a figure given from memory is `[assumed — <who>, from memory]`; a design file or prototype is `reported` — a claim about users made on it alone is `assumed`.
    - An upload or pasted input is `simulated` only on an explicit marker, never after a question; the notice line appears only when it is.
  - **6b: synthetic input.** `simulated` content is never a finding, a count or a quote.
  - **6c: frontier hand-back.** One line in `user.language`, placed at the claim, naming the human step. It covers:
    - a causal claim on observational data;
    - a "why users…" claim with no real-user source;
    - a claim that needs tacit organisational context.

    A randomised A/B readout is exempt. The line never changes a status, never blocks and never asks.
  - **6d: output by run kind.** Interactive runs get labels and hand-back lines. Return payloads carry classes and flags in their data-quality notes. Scheduled and headless runs get labels and the 6b handling of synthetic input, with a frontier claim marked `[assumed — frontier: <human step>]` and no new line.
  - **Gate Check 3 and examples.** Gate Check 3 no longer accepts synthetic input as a second source. Anti-patterns 5–6 and correct patterns 5–6 are added.
  - **Sub-steps:** cjm-research 3.5.g, product-analysis 1.5.g, product-research 1.5.g, feedback-triage Step 4. product-reporter Step 2.5 applies the causal rule to a cause of deviation.
- **Gate 4b — Evidence labels** (`artifact-style-gate.md`):
  - scope and exemptions (targets, forecasts, plan totals, hypothesis statements…);
  - a compact marker → class table for the checker;
  - rules: quotes verbatim (masking, `[…]` and `(translated)` allowed), no upgrades, labels from upstream kept;
  - severity, the `n/a` list (with Analyze & Improve advisory and external decks as partial cases), and fixes only toward a weaker class.

  The gate report line gains `докази: E`. The checker output gains `gate: 4a | 4b` and a `not_applicable` line. Sources may carry their Gate Check 5 markers.
- **`template-protocol.md` T-5 step 3c** gives P1 to every Product-contour artifact without growing `SKILL.md` files.
  - It runs whether or not a template applied, independently of `review_mode`, and in automated runs (labels and the 6b handling, no hand-back line).
  - It keeps step 3a's exclusions.
- **Label grammar** (`pm-mental-model.md` §4):
  - the class goes first inside the claim's existing annotation;
  - one group label is allowed when every claim it covers shares class and source;
  - `simulated` / `assumed` are always labelled on the item;
  - forward-looking numbers carry no class.

  The §4 definitions of `measured`, `simulated` and `assumed` are patched accordingly.
- **Vault Judgment Fields** (`vault-schema.md`, `vault-protocol.md` Vault Save step 5): optional `evidence_classes` and `altitude`, derived for every caller and never asked or backfilled. The `## Summary` keeps `simulated` / `assumed` labels, so synthetic input cannot re-enter later runs through Step 0.5.
- **Skills:**

  | Skill | Change |
  |---|---|
  | product-research | 1.5.g; `simulated_input` for the user-research template |
  | feedback-triage | Step 4 Gate Check 6; `origin` of items; generated items excluded from counts |
  | cjm-research | 3.5.g; walkthrough evidence `observed`; accurate group labels on the health-check (one class per label) |
  | brainstorm-features | claims inside idea cards labelled; Deep Research claims per 6a |
  | product-analysis | 1.5.g; post-release "coincides with the release" plus a hand-back without a control; Q&A causal claims |
  | experiment-tracker, decision-log | readout and record classes; `evidence_classes` filled from evidence, never asked |
  | flow-walkthrough | steps `observed` |
  | knowledge-library | class derived from the source type, trust score never changes it; shown inside the existing confirmation, never a picker |
  | product-landscape | facts carry their source's class; scan provenance never cited |
  | design-bridge | source captions carry the class; internal source names only for internal audiences; no hand-back line on external slides |
  | diagram-prototyper | infographic footers carry the class |
  | meeting-processor | one `Evidence: reported` line; verbatim quotes only |
  | product-reporter | actuals `measured` when computed from Jira; an inferred cause `assumed` plus a hand-back |
  | write-concept, requirements-creator, task-creator | in place: source markers and `artifact_type` passed to the checker; write-concept's examples teach `reported · … · not gate-checked`; requirements-creator Analyze & Improve shows 4b findings as advisory, accepted in the existing final review (never a new question or round) |
  | focus-advisor | in place: brief labels through T-5 step 3c (headless: labels and the 6b handling) |
- **Templates:**
  - `user-research`: conditional `Simulated input` line, n = real users;
  - `insight-report`: conditional `Simulated input` line;
  - `decision-memo`, `business-case`, `strategy-memo`, `qbr`, `board-update`: class per claim, forecasts unlabelled;
  - `walkthrough`, `landscape`: source classes;
  - `competitive`, `funnel` and four presentation templates: hints;
  - `judgment-footer` 1.2.0.
- **Shared protocols:**
  - `debate-protocol.md`: E# keep their class; A# keep their label (`assumed` or `simulated`); a role card's claim outside the pack is `simulated`; the consensus ICE boost needs a cited E#.
  - `planning-core.md` §6: the "pending TL / PM confirmation" marker is the planning hand-back and reads as `assumed`.
  - `subagent-delegation.md`: fan-out rows carry `origin` and verbatim-quote fields; the main agent classifies.
  - `self-improvement.md` (pulled forward from v3.9.0): a correction that removes an evidence label is never proposed as a skill change.
  - `cjm-protocol.md`: 6 mandatory checks.
  - `figma-designs-check.md`: a design is `reported`, never `observed`.
- **Tests:**
  - lint check 24 `evidence-classes` with four seeds (23/23);
  - validate check 14 now compares each agent with its Codex port;
  - output-evals criteria `evidence_labels` and `simulated_visible` for every rubric;
  - a product-research synthesis fixture and gold for spec TC-jdg-02;
  - relabelled golds;
  - test cases TC-jdg-380-*.

### Changed

- `pm-mental-model.md`: P1, P7, P9 (`evidence_classes`) and P10 act since v3.8.0. P10 now reads "instead of presenting a plausible guess as a finding — a guess it keeps is labelled `assumed`". P5's evidence-label clause is active.
- `judgment-points.md` §3: a lead recommendation resting on a frontier claim or a `simulated` input is at most `uncertain`; a decision record keeps the owner's level. §4: how `evidence_classes` is taken.
- `local-context-protocol.md`:
  - Step 0i step 3: automated runs keep the evidence labels, with no hand-back line;
  - Step 0i step 5: the altitude is also the vault `altitude:` key;
  - Step 0j step 4 lists the implementing steps; no label anywhere else.
- `artifact-checker` agent and its Codex port: the groundedness lens adds Gate 4b.
- Skill versions:

  | Skill | Version |
  |---|---|
  | `brainstorm-features` | 0.14.0 → 0.15.0 |
  | `cjm-research` | 0.10.0 → 0.11.0 |
  | `decision-log` | 0.4.0 → 0.5.0 |
  | `design-bridge` | 0.7.0 → 0.8.0 |
  | `diagram-prototyper` | 0.13.0 → 0.14.0 |
  | `experiment-tracker` | 0.5.0 → 0.6.0 |
  | `feedback-triage` | 0.5.0 → 0.6.0 |
  | `flow-walkthrough` | 0.5.0 → 0.6.0 |
  | `focus-advisor` | 0.9.0 → 0.9.1 |
  | `knowledge-library` | 0.8.1 → 0.9.0 |
  | `meeting-processor` | 0.16.0 → 0.17.0 |
  | `product-analysis` | 0.16.0 → 0.17.0 |
  | `product-landscape` | 0.4.0 → 0.5.0 |
  | `product-reporter` | 0.9.0 → 0.10.0 |
  | `product-research` | 0.13.0 → 0.14.0 |
  | `requirements-creator` | 0.16.0 → 0.16.1 |
  | `task-creator` | 0.14.0 → 0.14.1 |
  | `write-concept` | 0.14.0 → 0.14.1 |
- **ICE Confidence:** `simulated` support counts as no evidence. On its own it keeps Confidence in the 1–2 band, a debate consensus resting only on `simulated` / `assumed` support adds +0, and "underscoring" by benchmarks needs a real (`external` or stronger) one.
- The `data-integrity-protocol.md` cross-skill row "brainstorm-features (optional) ICE Confidence adjustment from status" — never implemented in the skill — now describes what brainstorm-features actually does (the debate pack's classes).
- meeting-processor's opt-in quality gate runs both lenses for a MoM bound for Confluence, so verbatim quotes and the `reported` label are checked; task-creator passes `artifact_type: task batch` in both of its checker calls (the batch gate and Step 12), so the checker reports Gate 4a / 4b `n/a`.
- Gate 3's terminology lint never touches text inside quote marks.
- `template-protocol.md` T-5 step 3d: authoring hint comments of a template and its partials are dropped from the rendered artifact after the language blocks are resolved (one leaked into a delivered report in the eval run).
- Output-eval fixture `cjm-research/brief-v1.md`: the integrity trap is now a period-completeness check on a complete month, matching its gold (it described a mid-month extract the gold contradicted). In all nine older fixtures the "Expected:" line moved out of the input brief into the evaluator-only comment, so makers no longer see the rubric's bar.
- v3.7.0's date corrected to 2026-10-01, the day its tag was created.

### Adaptations to the specification

- **Vault key.** The specification names it `evidence:`. It is `evidence_classes` on every type, the key decision records already had: one Obsidian property, no migration, and no confusion with a field for evidence links. The altitude key is `altitude:`, never `level:` (the vault level).
- **Naming.** "Gate 6" is `Gate Check 6`; `artifact-style-gate.md` has its own Gate 1–4.
- **Roles.** Gate Check 6 is baseline for every role, not a `gate_emphasis` token. `triangulation` no longer repeats the synthetic-input rule.
- **No persona simulation.** P7 is labelling at intake plus exclusion from findings, counts and quotes.
- **brainstorm-features.** The claims inside an idea card carry classes; the idea itself does not.
- **Wider P1 coverage.** The specification lists four skills for P7. P1 reaches every Product-contour artifact through T-5 step 3c, and 14 more skills received named steps.
- **Forward-looking numbers carry no class** (otherwise every forecast would read `simulated`). An unsourced input inside them is `assumed`.

### Not in this version (next)

v3.9.0:
- the prototype path and "build before you argue";
- the pre-mortem and kill criteria in concepts, roadmaps and A/B specs;
- the AI-feature section and spec-readiness gate;
- `learning_mode: pm_first`;
- the rest of the self-improvement guard;
- consolidation of the observability work.

### Backwards compatibility

- **No new question, switch or role branch.** `local-context.md` and onboarding are unchanged.
- **Visible for everyone:**
  - evidence labels on product artifacts;
  - hand-back lines in interactive runs;
  - a `Simulated input` line where such input exists;
  - "coincides with" instead of "caused by" on post-release reports without a control;
  - `докази: E` in the gate report;
  - the vault keys on new notes;
  - a lower confidence level where a lead recommendation rests on a handed-back or `simulated` input.
- **Automated runs:**
  - labels and the 6b handling of synthetic input (set aside, one `Simulated input` line where it exists);
  - the confidence cap and the "coincides with" wording, as in any run;
  - the vault keys;
  - never a question, a hand-back line or another new line. A scheduled feedback-triage adds no comparability line; its Intake shows how many `generated` items were set aside (the usable share changes accordingly); and it publishes where its schedule prompt names a destination, else locally, without asking — a Confluence write still meets the host write gate.
- **Older material stays valid:** vault notes and decision records written before v3.8.0 are valid as they are, and no note is backfilled.

---

## v3.7.0 (2026-10-01)

**Judgment points.** Fourth release of the Judgment Core + Role Layer programme. The plugin now slows down exactly where a judgment is made: at six scoring, readout, verdict, prioritisation and decision points it asks for **your estimate before showing its own** and then compares the two; the lead recommendation or verdict states its **confidence, the assumption it is most sensitive to and what would change it**; and a decision record names its owner, rejected alternatives, base rate, revisit trigger and minority report, with decision quality judged apart from its outcome at review. It is the first release that adds a question at a judgment point — one, switchable, skippable with one word, never asked in an automated run. MINOR: new shared reference, new steps in 8 skills, a new onboarding question in Extended mode.

### Added

- **`references/judgment-points.md`** — the implementing protocol for P2, P3 and P9 of `pm-mental-model.md`. §1 is the complete list of judgment points: brainstorm-features (top-N before ICE / PRO), experiment-tracker (prediction before the readout), product-analysis (your call before the A/B verdict), quarterly-planning (Step 4.4 priorities before ICE / RICE), focus-advisor (your prior in the Step 1 gate), decision-log (the owner's confidence and revisit trigger, in log mode and for the new decision in revisit). §2 the P2 question, §3 the confidence line and its scale, §4 the decision-record fields, §5 the resulting check, §6 where Gate 4c is checked.
- **"Your estimate first" (P2)** — one question at each listed point, asked before the skill shows its own score, rank, verdict or priority, then a short "Your estimate vs mine" block in the chat: where they agree, where they differ and the evidence that separates them. The skill never moves its own result toward yours. Switch: `judgment.hypothesis_first` (default `on`). «пропусти» / "skip" skips once; «вимкни» / "turn off" writes `Hypothesis first: off` (only when `local-context.md` can be written). The first P2 question of a session says why and how to switch it off. Never asked in a scheduled, headless or return-payload run (a chained skill that shows its own gate or report counts as interactive), or when your estimate is already known — even partly — in the request, in the registry's `prediction`, or passed by the calling skill as `pm_estimate`; it is never asked for the missing part. Choices that do not fit the host's 2–4-option picker are asked as a numbered list.
- **Confidence line (P3, Gate 4c active)** — `Confidence: known / likely / uncertain / unknown · most sensitive to: … · would change if: …`, rendered by the judgment-footer partial (1.1.0) directly above the altitude line on the A/B test report, the brainstorm result, a quarterly plan with a Step 4.4 prioritisation and the focus brief (headless too); under the Decision section of a decision record. Scale ↔ numbers: known ≈ ≥ 0.8 (high), likely ≈ 0.6 to < 0.8 (medium), uncertain ≈ < 0.6 (low), unknown = no number; frontmatter `confidence` fields keep their types, and the line never reads above the no-inflation cap: an inconclusive verdict, a ❌ Blocked or not cross-validated metric (a single source included) or an estimate by analogy is at most `uncertain`. "More data" is not a falsifier. A confidence line where §1 names none is removed by the self-check.
- **Decision hygiene (P9)** — decision-log records gain `owner` (one accountable person; `decided_by` stays the list), `rejected_alternatives` (`alternatives_considered` stays the count), `base_rate`, `revisit_trigger` (`revisit_by` stays the date), `minority_report` (debates now pass it into this field and a Minority report section) and `evidence_classes` (filled from v3.8.0). Nothing is inferred: an unstated field reads `not recorded` / `none found`. experiment-tracker's decide passes the registry's win rate as the base rate (n ≥ 5); meeting-processor's Decisions block carries the owner, rejected options, dissent and revisit condition only when said in the meeting, and hands all chosen decisions to decision-log at once (one confidence question for the batch); quarterly-planning's scope cuts arrive as rejected alternatives.
- **Resulting check** — decision-log revisit, new step 1b: decision quality judged on what was known then (`sound` / `mixed` / `flawed`), the outcome (`good` / `bad` / `too early`), and a "resulting" line naming luck or variance when quality and outcome disagree. Step 1b adds no question and no new mode (D25 = a step of revisit); revisit step 2 asks the P2 question once for the new decision.
- **"No decision = status theater"** — product-reporter's quarter review (QBR and board update included) and initiative status print one ⚠️ chat line when the report records no decision taken this period and asks for none. A note, not a question; the report is unchanged; not printed when another skill asks for the report only for its data.
- experiment-tracker registry: optional `prediction: {by, date, text}`.
- plugin-configurator: Extended onboarding Step 4b asks `hypothesis_first` next to `hats_allowed` (Basic still asks nothing); `update config → Judgment` no longer says the switch acts later.
- Tests: lint check 23 `judgment-points` (a §1 skill that never cites the protocol, or a P2 question or P3 confidence line outside §1; a negated mention such as "never asks the P2 question" passes) with three seeds (19/19); output-evals judgment criteria `altitude_line` and `confidence_falsifier` for every rubric, plus a full product-analysis A/B rubric with fixture and gold exemplar; test cases TC-jdg-370-*; trigger-evals H15–H16 (revisit / resulting phrases → decision-log).

### Changed

- `pm-mental-model.md`: the Binds of P2, P3, P4 (minority-report field) and P9 are active since v3.7.0; the core names the owner in the decision record (the judgment footer names none). `local-context-protocol.md` Step 0j step 3 states the P2 rule in the present tense.
- `artifact-style-gate.md` Gate 4c: checked by the T-5 self-check and decision-log's save gate only where `judgment-points.md` §1 names a line; the artifact-checker gets no 4c lens (none of its four skills renders the line).
- `template-protocol.md` T-5 step 3a: the confidence line joins the footer; a user override without its placeholders gets the built-in line above it.
- Skill versions: `brainstorm-features` 0.13.0 → 0.14.0 · `decision-log` 0.3.0 → 0.4.0 · `experiment-tracker` 0.4.0 → 0.5.0 · `focus-advisor` 0.8.0 → 0.9.0 · `meeting-processor` 0.15.0 → 0.16.0 · `plugin-configurator` 2.11.1 → 2.12.0 · `product-analysis` 0.15.0 → 0.16.0 · `product-reporter` 0.8.0 → 0.9.0 · `quarterly-planning` 0.6.0 → 0.7.0.

### Adaptations to the specification

- P2 and P3 bind six skills, not seven: roadmap-architect has no scoring or verdict step, so the planning suite's P2 point is quarterly-planning Step 4.4 (D27); its pre-mortem and kill criteria arrive with P4 in v3.9.0.
- product-analysis implements P2 / P3 in A/B mode only — the verdict the specification names; its other modes are unchanged.
- The spec asks for the confidence line in every artifact rubric's gold. It is added only where a skill renders it: the new A/B gold. The nine existing golds belong to skills that render none, so their `confidence_falsifier` criterion is `n/a`, and a line appearing there counts as a defect.

### Not in this version (next)

v3.8.0 — evidence classes: Gate Check 6, `simulated` / `assumed` labels, vault `evidence:` / `altitude:` frontmatter, `evidence_classes` in decision records, Gate 4b.

### Backwards compatibility

- **With `hypothesis_first: off`, or in any automated run**, every skill asks exactly the v3.6.0 questions. The one exception is the configurator's Extended onboarding and `update config → Judgment`: they now offer `hypothesis_first` in the same message as `hats_allowed`. Basic onboarding still asks nothing.
- **With the default `on`**, the only new question in a skill run is the P2 question at the six points above. One word skips it, and one word switches it off. brainstorm-features' "Choose one" starts from that answer instead of asking again.
- **Visible for everyone:**
  - one confidence line on the A/B report, the brainstorm result, a quarterly plan with a Step 4.4 prioritisation and the focus brief;
  - the resulting lines in a decision revisit;
  - the status-theater note on stakeholder reports without a decision;
  - the new record fields — the MoM's Decisions table keeps its columns; meeting-processor extracts the fields for decision-log.
- **Unchanged:** decision records written before v3.7.0 remain valid without the new keys, and no route or description changed.

---

## v3.6.0 (2026-09-29)

**Role defaults and templates.** Third release of the Judgment Core + Role Layer programme. The role now changes where a run starts — the template ranked first, extra sections, extra evidence checks, the planning view and the wording of questions — while every gate, question and route stays the same, and a user without a role (or with `pm`) sees exactly v3.5.0. MINOR: 14 new built-in templates, new steps in 18 skills, new shared reference.

### Added

- **14 built-in templates** (41 in total): `concept/design-brief`, `concept/strategy-memo`, `concept/decision-memo`, `concept/business-case`, `research/research-plan`, `research/discussion-guide`, `research/insight-report`, `research/insight-memo`, `ops-report/qbr`, `ops-report/board-update`, and partials `tracking-plan`, `nfr`, `repository-entry`, `money-bridge`. The ten non-partials carry the new frontmatter key **`match: subtype`** — a candidate only when the request subtype equals theirs (a role default or the user's own words), so no request resolves differently or asks a new "which template?" question because they exist.
- **Template ranking by role** (`template-protocol.md` T-0 / T-1 / T-3): in write-concept, requirements-creator and product-reporter's quarter mode, a request without a declared subtype takes `role_defaults.template_defaults`; elsewhere (product-research included) the new subtypes are reached by the user's words. An exact `match: subtype` hit is used silently under `smart` / `auto` when the user has no template of that type (`always_ask` still asks); built-ins are always read from the plugin folder, so an upgraded registry cannot hide them.
- **Role extra sections** (T-5 step 3b): `nfr` for engineering leads and `tracking-plan` for analysts on requirements, `repository-entry` for researchers on research — only when the artifact has no section with that meaning, only in requirements-creator, product-research and feedback-triage.
- **Gate emphasis** (`data-integrity-protocol.md`): 15 tokens, each one extra check that adds a ⚠️ caveat line and never relaxes a gate — e.g. SRM / exposure / peeking and confidence intervals for analysts, comparability and trend-vs-objective for leaders, triangulation and human-validated flags for researchers, base rates and the HiPPO check for executives, the money bridge for business owners.
- **Altitude views** (`planning-core.md` §7): Now / Next / Later as a view over existing labels; `planning_view: rollup` (leaders) or `slice` (delivery roles, with the tech-debt reserve as its own row — `capacity-model.md` §7); `horizon` sets project-planning's arc window.
- **`references/vocabulary-sets.md`** — read-only role wording for headings and option labels, below the team glossary; **`question_defaults`** — designers see states / DS / a11y options first in design-bridge, diagram-prototyper and flow-walkthrough.
- **Money bridge** — optional `Revenue driver` column in Key Metrics; QBR, board update and business case show a metric → revenue-driver table or one "No revenue mapping configured" line.
- `experiment-tracker` records an optional `readout_signoff: {by, date}`; quarterly-planning hands the board readout to product-reporter (`ops-report/board-update`).
- Output evals: fixtures, gold exemplars and rubrics for design brief, strategy memo, research plan and QBR; trigger-evals R15–R20 and N9.

### Changed

- `role-profiles.md` activates the v3.6.0 fields, adds `extra_sections` and `question_defaults`, and makes the `pm` row override nothing; `template_defaults` is the first subtype §2 lists per Product-contour type.
- Descriptions: write-concept gains «дизайн-бриф», «стратегічний меморандум», «мемо рішення», «бізнес-кейс» and the EN forms; focus-advisor «фокус кварталу»; product-reporter «QBR», «звіт для борду», "board update".
- Trigger-evals N8 reworded to an unambiguous spec-review phrase; the original wording is kept as N9, which accepts either skill.
- Skill versions: `brainstorm-features` 0.12.0 → 0.13.0 · `cjm-research` 0.9.0 → 0.10.0 · `design-bridge` 0.6.0 → 0.7.0 · `diagram-prototyper` 0.12.0 → 0.13.0 · `experiment-tracker` 0.3.0 → 0.4.0 · `feedback-triage` 0.4.0 → 0.5.0 · `flow-walkthrough` 0.4.0 → 0.5.0 · `focus-advisor` 0.7.0 → 0.8.0 · `product-analysis` 0.14.0 → 0.15.0 · `product-landscape` 0.3.0 → 0.4.0 · `product-reporter` 0.7.0 → 0.8.0 · `product-research` 0.12.0 → 0.13.0 · `project-planning` 0.4.0 → 0.5.0 · `quarterly-planning` 0.5.0 → 0.6.0 · `requirements-creator` 0.15.0 → 0.16.0 · `roadmap-architect` 0.4.0 → 0.5.0 · `sprint-planning` 0.5.0 → 0.6.0 · `write-concept` 0.13.0 → 0.14.0 · `plugin-configurator` 2.11.0 → 2.11.1 · `template-library` 0.3.1 → 0.3.2 · `knowledge-library` 0.8.0 → 0.8.1.

### Not in this version (next)

v3.7.0 — judgment points: the user's estimate before the plugin's at scoring, readout, verdict and prioritisation (`hypothesis_first`), the confidence-and-falsifier footer (Gate 4c), decision-record fields and the quality-vs-outcome review. `requirements/ai-feature` and `partial/pre-mortem` ship in v3.9.0 with the steps that use them.

### Backwards compatibility

A user whose role is `pm`, missing or not yet confirmed, and every automated run (scheduled, headless, a return payload) get exactly the v3.5.0 templates, sections, checks, order and questions. A skill invoked only for a return payload applies just the gate-emphasis tokens its interactive caller passes. Visible for everyone: `template-library list` and the clone wizard show the 10 new non-partial built-ins (the 4 partials are protocol-inserted and never listed); an explicit request for one of the new artifact types (design brief, strategy memo, decision memo, business case, research plan, interview guide, insight report or memo, QBR, board update) renders that template; a **hat** («як CPO, …», "as an analyst, …") now applies that role's template, extra sections, gate-emphasis caveats, wording and question defaults for its one run — for a `pm` or role-less user too; «на чому фокусуватись у кварталі» / «фокус кварталу» now route to focus-advisor (they reached quarterly-planning before); the board readout of quarterly-planning is rendered by product-reporter as a chat draft that asks nothing and publishes nothing until the user says so. The new built-ins are English-only (`available_languages: [en]`), like most built-ins; the artifact is still written in `user.language`.

---

## v3.5.0 (2026-09-28)

**Role layer: eight roles that change defaults, never capabilities.** Second release of the Judgment Core + Role Layer programme. The plugin asks once who the user is — Product Manager, Head of Product, CPO, Product Designer, Product Analyst, UX Researcher, Engineering Lead or Business Owner — and keeps the core identical for everyone: the same skills, gates, routing and ten principles. In v3.5.0 a role sets the home altitude, the quick wins and the one-run hats; every Product-contour artifact now closes with an altitude line. Role-specific templates, gate emphasis and planning defaults arrive in v3.6.0. MINOR: new shared reference, new step in every skill, new onboarding step, new built-in partial, four lint checks.

### Added

- **`references/role-profiles.md`** — the altitude model (L1 delivery → L4 portfolio; not the vault level L0–L2), eight role profiles as defaults (home altitude and reach, horizon, default artifacts, evidence emphasis from a closed token list, vocabulary and sources), session defaults per role (`level_home`, `reach`, `quick_wins`, `planning_view`, `vocabulary_set`), what a role never changes, hats and "hats vs debate", the Step 0i resolution protocol with a single EN/UA keyword table for free-text roles. Every field carries the version from which it acts.
- **Step 0i — Role resolution** in `references/local-context-protocol.md`: read the role; ask once in an interactive run when it is missing (group and role; scope is left to onboarding and `set role`) or free text (one confirmation of the keyword-mapped role); never ask in automated runs — scheduled, headless, or a skill invoked only for a return payload (`pm` for that run, nothing written); write into the file Step 0a resolved; resolve `role_defaults`; hat override for one run with a `Hat: … (profile: …)` header; altitude inferred from the request; one line on hosts without the SessionStart hook.
- **`templates/built-in/partial/judgment-footer-v1.md`** — the altitude line `Altitude: L1–L4 · ↑ serves: … · ↓ next: …`, appended by `template-protocol.md` T-5 step 3a to every Product-contour artifact (last content before the template marker; closing slide for decks; epic and Step 11 report for task-creator; none for People-contour artifacts). Its variables are derived by the skill and never asked; `serves` is never invented — `— (no linked goal)` when none is known. 27 built-in templates.
- **Gate 4 — Judgment footer** in `references/artifact-style-gate.md`: 4a altitude line (v3.5.0); 4c confidence and falsifier (v3.7.0) and 4b evidence labels (v3.8.0) are declared with their versions. Self-check at T-5 in every Product-contour skill; the checker's **form** lens adds 4a where maker–checker runs (`agents/artifact-checker.md` and its Codex port).
- **plugin-configurator** 2.11.0 — Step 4a role and scope (both modes; a two-level picker because a structured question takes 2–4 options), Step 4b Judgment settings (Basic writes the defaults and defers `judgment`; Extended asks only `hats_allowed`, the only switch live in v3.5.0), role-first quick wins at Step 17, `set role` / `change my role` / «змінити роль» at any time, RM-4d migration of a free-text role (keyword map, one confirmation), `## Judgment` section in `context-schema.md` and `local-context.example.md`; a non-enum role is a Validate recommendation, never a failure. The description gains the role phrases; the configurator explains the typed `/grow-product-manager:setup --write-gate off|on` instead of being mistaken for it.
- **Session digest** (`scripts/session_start.py`): `user.role: <enum | legacy | absent> | level_home: <Lx | derived at Step 0i>` — never the free-text label; `testing/session_start_test.py` covers the four cases.
- **Lint checks 19–22** (`testing/skill_lint.py`, preventive): `role-branching` (no skill branches on a role name; `role_defaults.<field>` must exist in role-profiles §5), `persona-prompt` (no "You are a CPO"-style identity in skills, references, agents or Codex agent ports; the debate `{role}` card is exempt), `judgment-footer` (every Product-contour skill references the footer), `role-enum` (the enum in context-schema equals role-profiles). `testing/seeded_leak_test.py` gains `remove` and `replace` seed modes and four seeds (16/16).
- Trigger-evals **Group R** — hats and role-neutral routing (14 phrases); README **Roles** section; `host-profiles.md` §4 row for structured questions; `debate-protocol.md` note on hats vs debate; `harness-map.md` rows.

### Changed

- 19 Product-contour skills carry the judgment-footer step (MINOR each): `brainstorm-features` 0.11.0 → 0.12.0 · `cjm-research` 0.8.0 → 0.9.0 · `design-bridge` 0.5.0 → 0.6.0 · `diagram-prototyper` 0.11.0 → 0.12.0 · `feedback-triage` 0.3.0 → 0.4.0 · `flow-walkthrough` 0.3.0 → 0.4.0 · `focus-advisor` 0.6.0 → 0.7.0 · `meeting-processor` 0.14.0 → 0.15.0 · `product-analysis` 0.13.0 → 0.14.0 · `product-landscape` 0.2.0 → 0.3.0 · `product-reporter` 0.6.0 → 0.7.0 · `product-research` 0.11.0 → 0.12.0 · `project-planning` 0.3.0 → 0.4.0 · `quarterly-planning` 0.4.0 → 0.5.0 · `requirements-creator` 0.14.0 → 0.15.0 · `roadmap-architect` 0.3.0 → 0.4.0 · `sprint-planning` 0.4.0 → 0.5.0 · `task-creator` 0.13.0 → 0.14.0 · `write-concept` 0.12.0 → 0.13.0.
- Gold exemplars of write-concept, requirements-creator, cjm-research, meeting-processor and task-creator end with the altitude line.
- `AGENTS.md` names all six host capabilities (APP-DRIVE was missing).
- `template-library` 0.3.1 — built-in partials (`templates/built-in/partial/`) are protocol-inserted and never listed, offered or cloned.

### Not in this version (next)

v3.6.0 — role defaults and templates: Step T ranks the role's template first within its scope, 16 new built-ins (design brief, strategy / decision memo, business case, research plan, discussion guide, insight report / memo, QBR, board update, AI feature, tracking-plan / NFR / money-bridge / pre-mortem / repository-entry partials), gate emphasis by role, planning horizon and roll-up vs slice, `revenue_driver` on key metrics. Then v3.7.0 (hypothesis-first, confidence and falsifier, decision-record fields), v3.8.0 (evidence classes), v3.9.0 (prototype path, pre-mortem, learning-preserving modes).

### Backwards compatibility

Every existing question, gate and write is unchanged except as listed here, and an existing `local-context.md` keeps working. New visible behaviour, in full:

- **Role question** — once in the first interactive run of any skill when Role is missing (group + role) or free text (one confirmation), with a one-row changelog; again in the next session only if the user skipped it. When the file cannot be written (read-only upload, connector document, sandbox) there is no question — the keyword-mapped role or `pm` is used and one notice line offers the role lines to paste. Never in automated runs; never in plugin-configurator's own Step 0i. The configurator's RM-4 migration asks the same single confirmation when it runs on an existing file and adds `## Judgment` defaults.
- **Altitude line** on the artifact a Product-contour skill delivers, wherever it is kept — not on Jira tasks, 1-1s, prototypes, handoffs, Analyze & Improve documents, Q&A or search answers, quick summaries, or return payloads; on external-audience decks only in the outline companion. The epic task-creator creates now carries the line (a changed Jira write); an existing epic is never edited for it, and roadmap-architect `onboard` never writes it.
- **Hats** — `Hat: … (profile: …)` at the top of the draft in the chat; one line when `hats_allowed` excludes the role. The "wear the … hat" idiom routes less reliably than "as a …" (trigger-evals R4).
- **Hosts without the SessionStart hook** — one `Role: … · Altitude home: …` line per interactive session.
- **Session digest** — a `user.role | level_home` line; deferred steps are now also read from the inline list the onboarding skeleton writes, so existing users see them; Basic users see `judgment` there and in `/status`.
- **Quality gate** — `футер: F` in an existing gate report line only when F > 0; task-creator's Step 12 check table gains a "no altitude line on a task" row (reported; removed only after the user confirms).
- **plugin-configurator** — Step 4a/4b; `set role` / «змінити роль» and «яка моя роль у плагіні» (these, and the new write-gate explanation, go straight to their step, after RM-0/RM-4 when the schema version differs); a Judgment item and a relabelled "User Profile (incl. role and scope)" item in the Update menu; "change role" among the View examples; a Validate recommendation for a free-text role (a missing role stays a finding); role-first quick wins with "add <section>, then …" pairs; a shorter closing line of the review.
- **Routing** — trigger-evals L9 («вимкни підтвердження перед записом») now accepts plugin-configurator, which explains `/grow-product-manager:setup --write-gate off`.
- **template-library** — `list` and clone never show the built-in judgment-footer partial.

---

## v3.4.0 (2026-09-25)

**Judgment contract and a thinner core.** First release of the Judgment Core + Role Layer programme (v3.4.0 → v3.9.0). The plugin gets an explicit model of its user as a Product Manager in the AI era and a ten-principle behaviour contract, and every skill now names its judgment points at a new Step 0j. This version publishes the contract and changes no question and no output; the mechanisms behind principles 2–10 arrive in v3.5.0–v3.9.0. The skill cores were slimmed so that every `SKILL.md` is ≤ 400 lines, and a validator check keeps them there. MINOR: new shared reference, new step in every skill, new validator check.

### Added

- **`references/pm-mental-model.md`** — who the user is (the PM owns outcomes; six pillars and one cross-cutting discipline), the north star (decision quality and speed to evidence, not artifact count), **ten principles** (provenance by default, human hypothesis first, calibrated confidence with a falsifier, built-in opponent, no sycophancy, build before you argue, synthetic users are rehearsal, learning-preserving modes, decision ownership, hand back at the frontier), the anti-patterns they prevent, and six **evidence classes** (`observed`, `measured`, `reported`, `external`, `simulated`, `assumed`).
- **Step 0j — Judgment contract** in `references/local-context-protocol.md`, and a three-line block in all 31 skills whose first line is always `> **Judgment contract (Step 0j).**`: note the run's judgment points (score, rank, verdict, priority, ship/kill, debate question) internally, with no output; **a principle acts only through a step that implements it**, so until the version that implements a step, every question, gate and output of the skill stays exactly as it is. Each principle's *Binds* list in `pm-mental-model.md` carries the version that implements it. (The specification called it "Step 0.5-J"; Step 0.5 is already the Vault Context Search.)
- **`references/figma-designs-check.md`** — the Figma designs check that write-concept, requirements-creator, brainstorm-features and product-research each carried in full; each skill keeps its own trigger, "use as context for" and "when designs are confirmed" lines next to the pointer.
- **Validator check 15 `thin core`** — every `SKILL.md` ≤ 400 lines (`testing/validate-consistency.sh`, row in `testing/Testing-process.md`).
- README **Principles** section (ten one-line principles); `harness-map.md` names the contract in the Instructions layer.
- Output evals: full rubrics, fixtures and gold exemplars for **meeting-processor** (`testing/fixtures/meeting-processor/brief-v1.md`, `skills/meeting-processor/references/examples/mom-example-v1.md`) and **task-creator** (`testing/fixtures/task-creator/brief-v1.md`, `skills/task-creator/references/examples/tasks-example-v1.md`) — the two skills with the largest moves, evaluated before and after the slimming.

### Changed

- **Thin core** — long procedures moved verbatim into new skill-local references; each `SKILL.md` keeps the step heading, a short summary and a pointer:

| Skill | New skill-local references (what moved) |
|---|---|
| `meeting-processor` | `calendar-enrichment.md`, `meeting-type-blocks.md`, `mom-format.md`, `search-mode.md`, `chaining.md` (M1d, M5b, M6a skeleton, Search mode S1–S4, M9 context tables + input-source discovery) |
| `diagram-prototyper` | `prompt-construction.md`, `tool-procedures.md` (Step 5; Steps 3b, 6a2–6f, 8b–8f) |
| `product-research` | `source-validation-gate.md`, `deep-research-llm.md` (Step 1.5 sub-checks; Deep Research procedures) |
| `task-creator` | `post-creation-verification.md`, `task-format.md` (Step 12; Step 7 format tables) |
| `design-bridge` | `design-bridge-playbook.md` (end-to-end example, failure modes, per-source extraction, pptx render, in-file history) + Step 4g appended to `figma-playbook.md` |
| `requirements-creator` | `publishing-destinations.md`, `design-bridge-handoff.md` (Step 6; Step 8) |

  `cjm-research` Step 3.5 sub-checks 3.5.a–e, which restated `data-integrity-protocol.md` Gate Checks 1–5, became a pointer table that keeps every CJM-specific instruction; where the old restatement and the shared protocol differed (the extreme-value verification list), the shared protocol governs. Longest `SKILL.md` after the change: 380 lines (was 617).
- All 31 skills bumped MINOR (new Step 0j):

| Skill | Version |
|---|---|
| `brainstorm-features` | 0.10.3 → 0.11.0 |
| `cjm-research` | 0.7.6 → 0.8.0 |
| `decision-log` | 0.2.5 → 0.3.0 |
| `delegation-coach` | 0.1.3 → 0.2.0 |
| `design-bridge` | 0.4.2 → 0.5.0 |
| `diagram-prototyper` | 0.10.2 → 0.11.0 |
| `experiment-tracker` | 0.2.4 → 0.3.0 |
| `feedback-triage` | 0.2.3 → 0.3.0 |
| `flow-walkthrough` | 0.2.1 → 0.3.0 |
| `focus-advisor` | 0.5.1 → 0.6.0 |
| `goal-setter` | 0.1.3 → 0.2.0 |
| `hiring-designer` | 0.1.2 → 0.2.0 |
| `knowledge-library` | 0.7.2 → 0.8.0 |
| `meeting-processor` | 0.13.5 → 0.14.0 |
| `offboarding-guide` | 0.1.2 → 0.2.0 |
| `one-on-one` | 0.1.3 → 0.2.0 |
| `performance-review` | 0.1.2 → 0.2.0 |
| `plugin-configurator` | 2.9.5 → 2.10.0 |
| `product-analysis` | 0.12.3 → 0.13.0 |
| `product-landscape` | 0.1.0 → 0.2.0 |
| `product-reporter` | 0.5.3 → 0.6.0 |
| `product-research` | 0.10.6 → 0.11.0 |
| `project-planning` | 0.2.4 → 0.3.0 |
| `quarterly-planning` | 0.3.4 → 0.4.0 |
| `release-manager` | 0.2.3 → 0.3.0 |
| `requirements-creator` | 0.13.3 → 0.14.0 |
| `roadmap-architect` | 0.2.4 → 0.3.0 |
| `sprint-planning` | 0.3.3 → 0.4.0 |
| `task-creator` | 0.12.3 → 0.13.0 |
| `template-library` | 0.2.4 → 0.3.0 |
| `write-concept` | 0.11.3 → 0.12.0 |

- README: stale counts fixed (37 shared references, 26 built-in templates, 31 skills in the Hosts table, six host capabilities); `testing/host-matrix.md` per-host tallies recomputed from its 31 rows (codex-cli 15 full / 16 degraded, chatgpt 21 degraded / 10 n/a, codex-cloud 22 degraded / 9 n/a).

### Not in this version (next)

v3.5.0 — role layer: `user.role` and eight role profiles that change defaults only (altitude, horizon, template, evidence emphasis, vocabulary), Step 0i role resolution, `## Judgment` switches, the altitude line (`Altitude: L2 · ↑ serves · ↓ next`) and Gate 4 of the artifact quality gate, lint checks 19–22. Then role defaults and templates (v3.6.0); hypothesis-first questions, the confidence-and-falsifier footer and the new decision-record fields (v3.7.0); evidence classes as Data Integrity Gate Check 6 and `simulated` labels (v3.8.0); prototype path, pre-mortem and kill criteria, learning-preserving modes and the self-improvement guard (v3.9.0).

### Backwards compatibility

Full. No new question, no removed question or gate, no changed output and no new `local-context.md` field; an existing `local-context.md` works exactly as in v3.3.0. The moved procedures are loaded from the skill-local references at the same step, with the same content. One governance nuance: cjm-research Step 3.5.c now defers to `data-integrity-protocol.md` Gate Check 3, whose extreme-value list is slightly longer than the old inline restatement (a methodology-change-suspicion trigger, an original-source check and a publication-date check); the automated health-check still never asks — with `product.primary_market` unset it applies the holiday windows exactly as before.

---

## v3.3.0 (2026-09-11)

**Product landscape — a registry of competitors, adjacent players and benchmarks, and six optional research connectors.** New skill `product-landscape` scans the user's machine, discovers products by category and market, categorises and characterises them with sources, maps the category, and starts the same-flow research across any number of products the user picks. MINOR: new skill, new storage folder, new vault type, new optional connectors.

### Added

- **`skills/product-landscape`** v0.1.0 — modes `scan` / `discover` / `add` / `update` / `characterize` / `map` / `research`; shared registry `~/.grow-pm/landscape/` (`registry.yaml`, `products/<slug>.md` with kind, category, markets, platforms, walkable surfaces, size signals, characterization, per-product role links, sources, status, `last_researched`, `walkthroughs[]`); candidates confirmed in batches of 10–15; research proposals ranked with **no cap**; any product the plugin touches is registered as `status: auto`; example `examples/shopping-category-scan.md`.
- **`scripts/landscape_scan.sh`** — one JSON line per candidate: Mac apps, iPhone apps installed from the Mac App Store (`/Applications/*.app/Wrapper`), adb packages; Chrome/Safari bookmark domains only with `--bookmarks` (after a per-scan yes); never browser history.
- **Six optional connectors** in `.mcp.json` — `lazyweb`, `similarweb`, `mobbin`, `semrush`, `tavily`, `apify` (URL-matched; the user's own accounts; no skill requires them); rows in `integration-strategy.md` 1a and a paragraph on when each matters (`tavily` for hosts without web search, `apify` for Google Play data).
- `templates/built-in/research/landscape-v1.md` (26 seed templates); vault type `landscape` → `Research/landscape/` (36 types); storage folder `landscape/`.
- plugin-configurator **Landscape setup** (Extended add-on, deferred id `landscape`): bookmarks consent, product category, import of `product.competitors` into the registry; schema section `## Landscape`.
- Trigger-evals Group O; test cases for scan, discover, map, research and the no-registry regression; lint vocabulary for roles and source types.

### Changed

- `product-research` 0.10.6 — competitor list from the registry when it exists, new competitors registered as `auto`, post-study offer; `flow-walkthrough` 0.2.1 — compare candidates from the registry, walked products registered, acted-on references registered as `inspiration`; `cjm-research` 0.7.6 and `brainstorm-features` 0.10.3 — landscape offers, `landscape:<slug>` evidence; `plugin-configurator` 2.9.5; `local-context-protocol.md` documents `product.competitors` as the registry seed.

### Not in this version (next)

Periodic re-scans and change alerts, price monitoring, review-sentiment mining across stores, automatic app installs; competitor account creation — never.

### Backwards compatibility

Full. Without a registry every skill behaves as before (`product.competitors`); the six connectors are optional and unconnected by default.

---

## v3.2.0 (2026-09-11)

**Test accounts by role and multi-role walkthrough legs.** A product's production test accounts (test buyer, test seller companies, admin) are declared once — labels, roles, surfaces, where access is obtained, sandbox flag; never a secret — and a `flow-walkthrough` scenario can run as several **legs** played by different roles in sequence with hand-off values between them. The write boundary now follows the account instead of being one global rule. MINOR: new step in flow-walkthrough, new configurator add-on.

### Added

- **`#### Test Accounts`** per product in `local-context.md` (`skills/plugin-configurator/references/context-schema.md`), deferred step id `test-accounts`, and the Extended add-on **Test accounts setup** in `onboarding-steps.md` with standalone triggers `add Test accounts` / `додай тестові акаунти`; the add-on refuses to write a pasted password or one-time code.
- **Legs** in `flow-walkthrough` v0.2.0 — Step 1 collects `role`, `account`, `surface`, `goal`, `handoff_in/out` per leg; Step 2 asks the user to log in before each leg; Step 3 confirms every irreversible tap under `sandbox-confirm`, captures hand-off values from screenshots, and starts the next leg only when its inputs exist; Step 6 adds a leg summary table.
- **Write-boundary policy** in `references/app-drive-protocol.md` §3 item 6: `stop-before-irreversible` (own), `sandbox-confirm` / `sandbox-auto` (sandbox test accounts in the user's own product), `read-only` (competitors); two hard stops under every boundary — real money, actions visible to real users. §7 pack layout: `legs[]` in `run.yaml`, `leg`/`role` on every step, `steps/L<leg>-<NN>.png`, `blocked_reason: user declined`.
- `templates/built-in/research/walkthrough-v1.md` 1.1.0 — leg summary table and a `Leg / Role` column.
- `skills/flow-walkthrough/examples/marketplace-order-to-review-flow.md` — the three-leg reference (test buyer orders → test seller confirms and ships → buyer reviews; four confirmations; real-payment-only checkout ends leg 1 with `blocked_reason: real money`).
- Lint vocabulary: `test-accounts` and the four boundary values; trigger-evals Group N; test-cases for the 3-leg scenario, the configurator add-on and the single-leg regression.

### Changed

- `flow-walkthrough` 0.1.0 → 0.2.0, `plugin-configurator` 2.9.3 → 2.9.4; `local-context.example.md` shows the Test Accounts table with placeholder labels.

### Not in this version (next)

Parallel legs on two devices at once (legs are sequential; two surfaces may stay open), automatic account switching, storing any secret (never).

### Backwards compatibility

Full. A single-leg run is byte-for-byte the v3.1.0 behaviour (`leg: 1`, `stop-before-irreversible` on an own account); products without a Test Accounts table simply have no sandbox option.

---

## v3.1.0 (2026-09-10)

**Walk the flow in the real product.** New skill `flow-walkthrough` drives the product the way a customer does — a web app in a browser, a desktop app, an iPhone app installed from the Mac App Store on Apple Silicon, an Android phone or emulator over adb — one step at a time with a screenshot per step, friction graded per step, a local evidence pack (`~/.grow-pm/walkthroughs/`) and a `research/walkthrough` report. Four modes: `setup` (agent-guided readiness + install, user-only actions marked, smoke test), `walk`, `compare` (one scenario across surfaces or against competitors — read-only there), `audit`. MINOR: new skill, new shared protocol, new observed capability. Built on a measured spike (2026-09-10, Claude Cowork): a marketplace buyer app from the Mac App Store was walked end-to-end up to the publish step.

### Added

- **`references/app-drive-protocol.md`** — capability **APP-DRIVE** (levels `web` / `desktop-background` / `foreground` / `device` / `none`, measured vs assumed per host), driver table, preflight, step cycle (act → wait → screenshot → verify → log), safety (credentials user-only, write boundary, competitors read-only, screenshots local), degradation (user-driven variant), evidence-pack layout (`run.yaml`, `steps.yaml`, `steps/NN.png`, `findings.md`, `compare.yaml`).
- **`skills/flow-walkthrough`** v0.1.0 with the reference example `examples/marketplace-review-flow.md` (12 expected steps, 6 expected frictions, driver facts).
- **`scripts/walkthrough_preflight.sh`** — per-surface readiness table `SURFACE | STATUS | MISSING | WHO`, fail-open.
- **`templates/built-in/research/walkthrough-v1.md`** (25 seed templates); vault type `walkthrough` → `Research/walkthroughs/` (35 types); storage folder `~/.grow-pm/walkthroughs/`.
- `host-profiles.md`: sixth capability in §1 and the profile table, "Product drive" row in §4, three measured facts in §7 (background capture fails for iPhone apps on a Mac; overlay utilities block clicks; App Store builds never run in the Simulator). `integration-strategy.md` Step 3 points to the protocol. `template-protocol.md` shows the `research/walkthrough` built-in on the ladder.
- Lint: `walkthrough-local`, `iphone-on-mac`, `android-adb`, `ios-simulator`, `desktop-background` join the non-skill vocabulary. Trigger-evals Group M; test-cases for the new skill.

### Changed

- `cjm-research` v0.7.5 — Step 3 "Walk the stage" via `flow-walkthrough`; source marker `walkthrough-local` in Step 3.5.e; chaining offer. `references/cjm-protocol.md` documents the marker as qualitative stage evidence.
- `product-research` v0.10.5 — hands-on UX benchmark through `flow-walkthrough` compare mode (competitors read-only); post-research offer.
- `requirements-creator` v0.13.3, `task-creator` v0.12.3, `write-concept` v0.11.3 — a walkthrough pack's `steps/NN.png` is screenshot source 0 (`visual-annotation-protocol.md` V-1); requirements-creator offers a short walk when no source exists.
- `diagram-prototyper` v0.10.2 — `steps.yaml` is a valid flowchart input (node per step intent, friction as a red note, blocked step as a terminal node).
- `vault-protocol.md` skill→types table gains `flow-walkthrough`; `requirements-creator` may read `walkthrough`.

### Not in this version (next)

iOS Simulator builds from the mobile team, iPhone Mirroring, installing an Android emulator with system images, video recording, automated accessibility audit; Codex and ChatGPT drive levels stay `assumed` until measured.

### Backwards compatibility

Full. No existing skill changes behaviour unless a walkthrough pack exists or the user asks for a walk; the write boundary defaults to "stop before any irreversible action".

---

## v3.0.1 (2026-09-09)

**Plugin logo and the Codex card.** The plugin now has its own mark — a white "G" with a compass arrow on the Prom violet — and a `.codex-plugin/plugin.json` that Codex and ChatGPT render as the plugin card. Packaging only: no skill, protocol or command changed.

### Added

- **`assets/logo.png`** (512×512) and **`assets/composer-icon.png`** (128×128) — the chosen "G-compass" mark; the card rounds the tile itself, as with the bundled OpenAI plugins.
- **`.codex-plugin/plugin.json`** — mirrors `.claude-plugin/plugin.json` (name, version, description, author) and adds `skills: "./skills/"` plus the `interface` block: `displayName`, `shortDescription`, `longDescription`, `developerName`, `category: Productivity`, `websiteURL`, `brandColor: #7B04DF`, `logo`, `composerIcon`. Verified on a fixture and on the pilot stand that the manifest keeps the 29 skills loading and the 5 commands migrating (34 entries, no duplicates).
- README shows the logo and documents the card.

### Changed

- **`testing/validate-consistency.sh`** — check 1 keeps the two manifests' version and description identical and requires the logo files; check 10 counts components in the Codex manifest as well.
- **`release-manager`** Step 3 — six mandatory bump places (the Codex manifest is 2a). `AGENTS.md` names the five version-bearing files.

### Backwards compatibility

Full. Claude Code has no logo field and ignores `.codex-plugin/` and `assets/` (headless load test on the branch: skills, commands and the SessionStart hook unchanged; `claude plugin validate` passes). On Codex the logo appears after the two-step manual update (`codex plugin marketplace upgrade …`, then `codex plugin add …`) because the plugin cache is keyed by version — the reason this is a release and not a silent change on `main`.

---

## v3.0.0 (2026-09-08)

**One plugin, three hosts — Claude Code / Cowork, Codex CLI and app, ChatGPT.** Codex reads the same `.claude-plugin/` manifests, loads all 29 skills under the same `grow-product-manager:` namespace and registers the same connectors, so nothing was forked. What changed is how the skills behave where a host lacks something: every skill now branches on **observed capabilities**, never on a host name. MAJOR because the marketplace `source` format changes, every `SKILL.md` and every command description changes, and the plugin now promises a defined behaviour on hosts it previously ignored. Measured on Codex CLI 0.153.2 and Claude Code 2.1.126 throughout (`Codex-Compat-Findings.md`, stages 0–5, in the design workspace).

### Added

- **`references/host-profiles.md`** — the cross-host contract: five observable capabilities (FS, SHELL, SUBAGENT, MCP, HOOKS), four profiles (`claude-cowork`, `codex-cli` incl. the Codex app, `chatgpt`, `codex-cloud`), **Step 0-host** run once per skill, the degradation matrix per contour, the contours with no meaningful degraded mode, `${PLUGIN_ROOT}` → `${CLAUDE_PLUGIN_ROOT}` → walk-up resolution, and the measured host gaps.
- **Path rule** paragraph at the top of every `SKILL.md` and of every command that names a reference — Codex resolves a bare `references/<file>.md` against the skill's own folder and does not walk up (3 of 4 shared protocols were unreachable from `write-concept`); the rule sends the read to the plugin root. Verified 7/7 in Codex, incl. a natural activation.
- **`AGENTS.md`** (5 KB) — standing brief for hosts that read it: where things live, Step 0-host, the data-policy requirement, the measured Codex gaps.
- **`.codex/agents/*.toml`** — manual Codex ports of `artifact-checker`, `debater`, `extractor` (Codex does not load `agents/*.md` and spawns a subagent only on request), generated from the markdown sources, with a README on their weaker independence.
- **`testing/host-matrix.md`** — 29 skills × 4 hosts × full / degraded / n-a, derived from what each skill invokes: codex-cli 15 full / 14 degraded, chatgpt 19 degraded / 10 n/a, codex-cloud 20 degraded / 9 n/a.
- **Validator checks 12–14** — description routing order (guard inside the first 192 characters, neighbour is a real skill, Ukrainian keywords present); commands typed-only (no `$1` / `$ARGUMENTS`, description opens with `Typed command … only`); host packaging (Path rule everywhere, a Codex port per agent, every skill in the host matrix). Each negative-tested on the defect it targets. `testing/Testing-process.md` documents them.
- **README → Hosts** — capability table per host, per-skill result, Codex install and the two-command manual update.

### Changed

- **All 29 skill descriptions** rewritten under a priority-order rule, because Codex shares one ≈15,000-character budget across every listed skill (~530 characters each with this plugin alone, ~190 on a host listing 80 skills): essence with the discriminating nouns + the guard against the nearest neighbour inside the first 190 characters, then Ukrainian keywords, then EN triggers, then chains. No `: ` in any description (strict YAML). **Trigger-evals, 102 phrases:** Codex CLI on the author's real configuration 91.2 % → **100 % in two consecutive runs**, identical answers; Claude Code headless **101/102** where the one miss (`/grow-product-manager:status` → `none`) is the correct Claude answer for a host-executed command.
- **All 5 command descriptions** open with `Typed command /grow-product-manager:<name> only — never for a conversational «…» (that is <skill>)` — Codex migrates commands into routable skills without `disable-model-invocation`, and they captured conversational status/config/terminology/write-gate phrases (Group L 4/9 before, 9/9 after). Command bodies describe their argument in prose instead of `$1` / `$ARGUMENTS` (Codex skipped 4 of 5); `setup.md` no longer pre-executes its script.
- **`.claude-plugin/marketplace.json`** — `"source": "./"` instead of the `git-subdir` object. Codex silently ignores the object form (marketplace added, zero plugins); Claude Code rejects a bare `"."` (`plugins.0.source: Invalid input`) and accepts `"./"`. Relative sources resolve against the local marketplace copy, so `owner/repo` installs keep working; only a marketplace added by direct URL to `marketplace.json` would not.
- **`references/persistent-storage.md`** — step 0 of `storage_root` resolution: `storage_mode: local | connector | session` from Step 0-host (`local` = current behaviour; `connector` = a Drive folder or Confluence space from `storage.connector_root`; `session` = artifact stays in the chat and is exported at the end). Named `storage_mode`, not a letter — L0/L1/L2 already mean vault levels.
- **`references/subagent-delegation.md`** — the one-line fallback is a three-level chain: parallel `extractor` subagents → sequential inline passes with a role reset (the Codex default) → a single pass over fewer sources, stated. Level fixed once at Step 0-host.
- **`references/artifact-style-gate.md`** — on a host without SUBAGENT the checker lands on level 2 (sequential in-session lens passes, `checker: sequential in-session`), the reduced-independence marker stays reserved for level 3; on a host without HOOKS the skill asks for the write confirmation itself with the same three-point checklist.
- **`references/integration-strategy.md`** — host-capabilities preamble; §1a namespaces are host-dependent (1b pattern detection is the source of truth) with a Codex column: name-matched empty-`url` connectors work in the Codex **app** but fail at session start in the **CLI** (`relative URL without a base`) — kept on purpose as Claude's convention, documented in `.mcp.json` and `AGENTS.md`.
- **`references/local-context-protocol.md`** — where a bare `references/…` lives (skill-local if the file exists there, otherwise the shared folder at the plugin root, resolution per host-profiles §6).
- **Portable `${PLUGIN_ROOT}`** ahead of `${CLAUDE_PLUGIN_ROOT}` in `agents/*.md`, `commands/status.md`, the validator; `hooks/hooks.json` keeps the Claude variable (hooks load only there).
- **`testing/trigger-evals.md`** — Codex run protocol (single-line prompts — a multi-line prompt argument hangs `codex exec` 0.153 before the session starts; score on the host's real configuration) and the two-host results rows.

### Known host gaps (documented, not hidden)

Codex does not load `agents/*.md` or `hooks/hooks.json` (openai/codex#17331); Codex CLI fails empty-`url` connectors at session start (the app matches them by name); Codex refreshes Git marketplaces only at startup (openai/codex#17425, #38401) — restart Codex after a release, or `codex plugin marketplace upgrade <name>` then `codex plugin add …`; ChatGPT on web / mobile has no filesystem, shell or subagents — the storage-bound contours say so and stop (the desktop app with a *Local Project* has a filesystem and behaves like Codex). *Corrected 2026-09-09: the original entry said "no auto-update" and "no filesystem" without qualification — both were assumptions, not measurements.*

### Files

| File | Version | Change |
|------|---------|--------|
| `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` | 2.6.0 → 3.0.0 | version, description tails, string `source` |
| `skills/brainstorm-features/SKILL.md` | 0.10.1 → 0.10.2 | Path rule paragraph; description rewritten under the routing-order rule |
| `skills/cjm-research/SKILL.md` | 0.7.3 → 0.7.4 | Path rule paragraph; description rewritten under the routing-order rule |
| `skills/decision-log/SKILL.md` | 0.2.4 → 0.2.5 | Path rule paragraph; description rewritten under the routing-order rule |
| `skills/delegation-coach/SKILL.md` | 0.1.2 → 0.1.3 | Path rule paragraph; description rewritten under the routing-order rule |
| `skills/design-bridge/SKILL.md` | 0.4.1 → 0.4.2 | Path rule paragraph; description rewritten under the routing-order rule |
| `skills/diagram-prototyper/SKILL.md` | 0.10.0 → 0.10.1 | Path rule paragraph; description rewritten under the routing-order rule |
| `skills/experiment-tracker/SKILL.md` | 0.2.3 → 0.2.4 | Path rule paragraph; description rewritten under the routing-order rule |
| `skills/feedback-triage/SKILL.md` | 0.2.2 → 0.2.3 | Path rule paragraph; description rewritten under the routing-order rule |
| `skills/focus-advisor/SKILL.md` | 0.5.0 → 0.5.1 | Path rule paragraph; description rewritten under the routing-order rule |
| `skills/goal-setter/SKILL.md` | 0.1.2 → 0.1.3 | Path rule paragraph; description rewritten under the routing-order rule |
| `skills/hiring-designer/SKILL.md` | 0.1.1 → 0.1.2 | Path rule paragraph; description rewritten under the routing-order rule |
| `skills/knowledge-library/SKILL.md` | 0.7.1 → 0.7.2 | Path rule paragraph; description rewritten under the routing-order rule |
| `skills/meeting-processor/SKILL.md` | 0.13.4 → 0.13.5 | Path rule paragraph; description rewritten under the routing-order rule |
| `skills/offboarding-guide/SKILL.md` | 0.1.1 → 0.1.2 | Path rule paragraph; description rewritten under the routing-order rule |
| `skills/one-on-one/SKILL.md` | 0.1.2 → 0.1.3 | Path rule paragraph; description rewritten under the routing-order rule |
| `skills/performance-review/SKILL.md` | 0.1.1 → 0.1.2 | Path rule paragraph; description rewritten under the routing-order rule |
| `skills/plugin-configurator/SKILL.md` | 2.9.2 → 2.9.3 | Path rule paragraph; description rewritten under the routing-order rule |
| `skills/product-analysis/SKILL.md` | 0.12.2 → 0.12.3 | Path rule paragraph; description rewritten under the routing-order rule |
| `skills/product-reporter/SKILL.md` | 0.5.2 → 0.5.3 | Path rule paragraph; description rewritten under the routing-order rule |
| `skills/product-research/SKILL.md` | 0.10.3 → 0.10.4 | Path rule paragraph; description rewritten under the routing-order rule |
| `skills/project-planning/SKILL.md` | 0.2.3 → 0.2.4 | Path rule paragraph; description rewritten under the routing-order rule |
| `skills/quarterly-planning/SKILL.md` | 0.3.3 → 0.3.4 | Path rule paragraph; description rewritten under the routing-order rule |
| `skills/release-manager/SKILL.md` | 0.2.0 → 0.2.1 | Path rule paragraph; description rewritten under the routing-order rule |
| `skills/requirements-creator/SKILL.md` | 0.13.1 → 0.13.2 | Path rule paragraph; description rewritten under the routing-order rule |
| `skills/roadmap-architect/SKILL.md` | 0.2.3 → 0.2.4 | Path rule paragraph; description rewritten under the routing-order rule |
| `skills/sprint-planning/SKILL.md` | 0.3.2 → 0.3.3 | Path rule paragraph; description rewritten under the routing-order rule |
| `skills/task-creator/SKILL.md` | 0.12.1 → 0.12.2 | Path rule paragraph; description rewritten under the routing-order rule |
| `skills/template-library/SKILL.md` | 0.2.3 → 0.2.4 | Path rule paragraph; description rewritten under the routing-order rule |
| `skills/write-concept/SKILL.md` | 0.11.1 → 0.11.2 | Path rule paragraph; description rewritten under the routing-order rule |
| `commands/*.md` (5) | — | typed-only guard, prose arguments, Path rule |
| `agents/*.md` (3) | — | `${PLUGIN_ROOT}` first |
| `references/host-profiles.md`, `AGENTS.md`, `.codex/agents/*` , `testing/host-matrix.md` | new | see Added |
| `references/persistent-storage.md`, `subagent-delegation.md`, `artifact-style-gate.md`, `integration-strategy.md`, `local-context-protocol.md` | — | see Changed |
| `testing/validate-consistency.sh` (checks 12–14), `testing/skill_lint.py` (unchanged), `testing/trigger-evals.md`, `testing/Testing-process.md` | — | see Added / Changed |

### Backwards compatibility

Claude Code / Cowork behaviour is unchanged: every degraded mode is gated on an absent capability that Claude has, the Path rule is a no-op where `references/` already resolves from the plugin root, and commands keep `disable-model-invocation: true`. Existing installs from `owner/repo` keep working with the string `source`. Skill folder names, chain contracts, vault types and `local-context.md` keys are unchanged; `storage.connector_root` is a new optional key read only in `storage_mode: connector`.

---

## v2.6.0 (2026-09-04)

**Host hooks: the session knows where its context is, and a human confirms before a write.** v2.5.0 moved connectors, agents and commands into the manifest. This release adds the fourth component, hooks — two of them, chosen by a rule: a hook must be *deterministic*, *fail-open*, and do something a skill cannot do reliably from prose. A hook runs in the session's own environment (a local VM or a hosted container) and sees only its event's JSON, never the conversation — both hooks are designed around that.

### Added — `hooks/hooks.json` (2) + `scripts/`

- **SessionStart → context digest** (`scripts/session-start.sh` → `session_start.py`; matcher `startup|resume|clear|compact`, timeout 10 s). Searches for `local-context.md` in the order a session can actually see it: `~/.grow-pm/` → connected folders `$HOME/mnt/*/`, `$HOME/mnt/*/.grow-pm/`, `$HOME/mnt/*/grow-pm/` → staged uploads → the working directory. Found → injects a `GROW_PM_SESSION` digest (path, configurator version, onboarding mode, `user.language`, product and team names, vault / CJM / team-language flags, deferred onboarding steps; header facts only — never URLs, ids or emails) and appends `export GROW_PM_CONTEXT_PATH=…` to `$CLAUDE_ENV_FILE` for later Bash calls. Not found → a three-line `NOT VISIBLE` note that tells skills to run Step 0 unchanged and **not** to start onboarding on that signal. Re-runs after `/clear` and after compaction, so the location survives long sessions. Without python3 the wrapper emits a static note; any error → exit 0, no output.
- **PreToolUse → write gate** (`scripts/write-gate.sh` → `write_gate.py`; matcher `mcp__.*__(createJiraIssue|editJiraIssue|createConfluencePage|updateConfluencePage)$`, timeout 10 s). Returns `permissionDecision: "ask"` for every create and for content-bearing updates (a description/body ≥ 200 chars); the reason the host shows is the checklist the artifact quality gate expects to be done by then — gate report in chat, the user's explicit go-ahead, not a sandbox. Metadata-only edits (status, labels, title) pass silently. Opt-out via `{"write_gate": "off"}` in the plugin data dir. Any error → allow.
- **`/grow-product-manager:setup [--show | --write-gate on|off]`** (`commands/setup.md` → `scripts/setup.py`) — the toggle above, plus a report of the hooks environment (`CLAUDE_PLUGIN_DATA`, `CLAUDE_ENV_FILE`, `GROW_PM_CONTEXT_PATH`). Never touches `local-context.md`.

### Changed — protocols and validation

- **`references/local-context-protocol.md`** Step 0a — the digest is a shortcut: take the path from `GROW_PM_SESSION` / `GROW_PM_CONTEXT_PATH` and skip the location search; still parse the file for 0c–0h. `NOT VISIBLE` means "the hook could not see it", not "not configured". No skill file changed.
- **`references/artifact-style-gate.md`** — new section *Host write gate*: skills must present the gate report and get the go-ahead **before** the write step, because the host prompt will ask for exactly that.
- **`references/harness-map.md`** — hooks and agents named in the Guardrails layer.
- **`testing/validate-consistency.sh`** — check 11: `hooks.json` valid, events from the official list, every hook has a `timeout`, every command points at an existing **executable** script, `scripts/*.py` compile; check 10 counts hooks. **`testing/skill_lint.py`** scans `scripts/`. Trigger-evals L9; `testing/test-cases.md` v2.6.0 block with fixture results (8/8 pass) and the host stage split by environment (local / hosted / CLI / after compaction).

| File | From | To | Change |
|------|------|----|--------|
| `hooks/hooks.json` | — | new | SessionStart + PreToolUse |
| `scripts/session-start.sh`, `session_start.py` | — | new | context digest |
| `scripts/write-gate.sh`, `write_gate.py` | — | new | write gate (`ask`) |
| `scripts/setup.py`, `commands/setup.md` | — | new | toggles + env report |
| `references/local-context-protocol.md`, `artifact-style-gate.md`, `harness-map.md` | — | — | digest shortcut, host write gate, harness layer |
| `testing/validate-consistency.sh`, `skill_lint.py`, `trigger-evals.md`, `test-cases.md` | — | — | check 11, scope, L9, v2.6.0 cases |
| `.claude-plugin/plugin.json`, `marketplace.json`, `README.md` | 2.5.0 | 2.6.0 | version, counts, hooks section |

### Backwards compatibility

Fully backwards compatible. No skill file changed. Hosts without hook support ignore `hooks/`; skills behave exactly as in v2.5.0. The write gate adds one confirmation prompt per artifact write — the only visible change — and can be turned off per install.

---

## v2.5.0 (2026-09-04)

**Plugin components: what the host can enforce, the host now enforces.** Until this release everything the plugin needed from its host lived in prose — "look at the tools in the session for something matching `mcp__*__*Jira*`", "spawn a subagent that must not browse the web", "the checker must not see the maker's context". The model followed those instructions most of the time. This release moves three of the contracts into files the host parses — `.mcp.json`, `agents/`, `commands/` — so a connector shows its real state in the plugin card, a checker physically cannot browse, and a service command is never reached by accident. Hooks (a SessionStart context digest, a pre-write gate on Jira/Confluence tools) are designed and deferred to the next release pending environment tests — see `testing/test-cases.md` → v2.5.0 Stage 3.

### Added — connectors (`.mcp.json`, 6)

- **`.mcp.json`** declares the six connectors the skills rely on: `atlassian` and `figma` by URL (matched to the user's existing connection — no second entry is created), `gmail`, `google calendar`, `google drive`, `fireflies` by name (first-party connectors with a dynamic endpoint). They appear in the plugin's **Connectors** tab with a connected / not-connected state. **Tableau is deliberately not declared** — it is a local MCP server the user runs, and declaring a bundled one would duplicate it.
- **`references/integration-strategy.md`** — Step 1 splits into **1a Declared connectors** (a table: `.mcp.json` key → connector name → tool namespace observed in real sessions → ping call) and **1b Pattern detection** (the old wildcard table, kept for undeclared products). A declared-but-unconnected connector is reported as "enable it in the Connectors tab", never searched for in the registry. The stale `gcal_*` / `gmail_*` patterns — which matched no real tool — are replaced with the actual names. New provenance rule: name the answering server, not the product.
- **`skills/plugin-configurator/references/onboarding-steps.md`** Step 3a — reads declared connectors first, pings by pattern only for Tableau / Notion / Slack / Obsidian.

### Added — agents (`agents/`, 3)

Three named subagents. Each is the executable form of a protocol that already existed; what is new is the `tools:` line, which the host enforces.

- **`artifact-checker`** (`tools: Read`; no Write/Edit/Bash/web/Agent) — the checker half of maker–checker in `references/artifact-style-gate.md`. Receives the draft + source list + `lens` (form | groundedness) + optional Gate-3 lint findings; reads the gate reference itself (checklists are never copied into the call); returns per-section findings in a fixed schema; an empty report without per-section commentary is invalid.
- **`debater`** (`tools: []`) — one role in Debate Mode (`references/debate-protocol.md`). "No web, no vault, no files" was the protocol's core guardrail on the honor system; now it is a host rule. Fixed Round-1 / Round-2+ response structures; every argument cites `E#`/`A#`.
- **`extractor`** (`tools: Read, Glob, Grep`) — the fan-out worker in `references/subagent-delegation.md`: `batch` + `schema` + optional `filters` / `read_via` in, structured rows with source markers out; `nothing_found: true` instead of silence; `unreadable` instead of improvising when a named tool is missing.
- Each protocol gains an explicit **fallback chain**: named agent → `general-purpose` with the same prompt (the report says "checker: general-purpose" / "debater: general-purpose" so the user knows the restriction was not enforced) → inline with the existing reduced-independence marker. Nothing breaks in a host without plugin agents.

### Added — commands (`commands/`, 4; all user-only)

Every command carries `disable-model-invocation: true` — the model never routes a conversation into one, which also keeps them out of trigger collisions (new trigger-evals **Group L**, eight negative rows).

- **`/grow-product-manager:status [--verbose]`** — one-screen health: plugin version, where `local-context.md` was found (including connected folders in hosted sessions) and its schema version, vault level, declared connectors vs tools present in this session, deferred onboarding steps; one suggested next action. Read-only, never launches the configurator.
- **`/grow-product-manager:config validate|view`** — straight into `plugin-configurator`'s Validate / View mode; never starts Onboarding.
- **`/grow-product-manager:release patch|minor|major`** — `release-manager` with Step 2's classification pre-answered; for the plugin repo only.
- **`/grow-product-manager:glossary-lint [file]`** — Gate 3 team-language lint over a file or pasted text, standalone; findings only, nothing written.

### Changed — validation follows the new surface

- **`testing/validate-consistency.sh`** — four new checks: **7** agents frontmatter (name == file, description, `tools`/`disallowedTools`, `model` ∈ enum), **8** commands frontmatter (description, argument-hint, `disable-model-invocation: true`), **9** `.mcp.json` keys == the *Declared connectors* table (both directions; valid JSON), **10** the phrase `N skills, N agents, N commands, N connectors` in plugin.json, marketplace.json and README equals what is on disk.
- **`testing/skill_lint.py`** — `agents/*.md` and `commands/*.md` join the org-data, org-signature, example-locale and stale-name scans (`component_files`). **`testing/seeded_leak_test.py`** — two new seeds prove it (an Atlassian host inside an agent prompt; an authority citation inside a command): 12/12.
- **`skills/release-manager` → v0.2.0** — Step 3 has a fifth mandatory place (component counts); adding an agent / command / connector is a MINOR bump; the `/release` command is documented.
- **`skills/requirements-creator` → v0.13.1**, **`skills/write-concept` → v0.11.1**, **`skills/task-creator` → v0.12.1** — the gate step names `grow-product-manager:artifact-checker` (one call per lens) instead of "an independent checker subagent". **`skills/brainstorm-features` → v0.10.1** — Step 3D names `grow-product-manager:debater`. **`skills/plugin-configurator` → v2.9.2** — onboarding Step 3a.
- **README** — new section *Plugin Components*; **`testing/test-cases.md`** — v2.5.0 block with the host-behavior stage (tabs, no duplicate connectors, namespace, `tools: []` enforcement, hidden commands).

| File | From | To | Change |
|------|------|----|--------|
| `.mcp.json` | — | new | 6 declared connectors |
| `agents/artifact-checker.md`, `agents/debater.md`, `agents/extractor.md` | — | new | tool-restricted subagents |
| `commands/status.md`, `config.md`, `release.md`, `glossary-lint.md` | — | new | user-only service commands |
| `references/integration-strategy.md` | — | — | Step 1a/1b, provenance rule, fixed patterns |
| `references/artifact-style-gate.md`, `debate-protocol.md`, `subagent-delegation.md` | — | — | named agents + fallback chains |
| `skills/requirements-creator/SKILL.md` | 0.13.0 | 0.13.1 | Step 4.5 names the agent |
| `skills/write-concept/SKILL.md` | 0.11.0 | 0.11.1 | Step 4.5 names the agent |
| `skills/task-creator/SKILL.md` | 0.12.0 | 0.12.1 | batch gate + Step 12 name the agent |
| `skills/brainstorm-features/SKILL.md` | 0.10.0 | 0.10.1 | Step 3D names the agent |
| `skills/plugin-configurator/SKILL.md` (+ `references/onboarding-steps.md`) | 2.9.1 | 2.9.2 | Step 3a declared-first |
| `skills/release-manager/SKILL.md` | 0.1.3 | 0.2.0 | fifth mandatory place, `/release` |
| `testing/validate-consistency.sh`, `skill_lint.py`, `seeded_leak_test.py`, `trigger-evals.md`, `test-cases.md` | — | — | checks 7–10, component scope, seeds, Group L, v2.5.0 cases |
| `.claude-plugin/plugin.json`, `marketplace.json`, `README.md` | 2.4.1 | 2.5.0 | version, counts, Plugin Components section |

### Backwards compatibility

Fully backwards compatible. Skills that never used the gate, Debate Mode or fan-out are untouched; the three protocols keep their inline behavior as the last fallback; `.mcp.json` only *declares* connectors the skills already looked for by pattern. The one visible change for an existing install is the plugin card gaining Connectors / Agents / Commands tabs. No `local-context.md` schema change.

---

## v2.4.1 (2026-07-31)

**The plugin's own promise, enforced.** Both manifests state that the plugin "ships no hardcoded brand or organization data". An audit of the tree found nine lines where that was not true — not hosts or ids (those were already checked) but ordinary words: the maintainer's team cited as the authority behind a rule, examples signed with a team and a quarter, a schema example written in one team's language, and an output language hardcoded where `user.language` exists. Every check in the linter passed green over them, because a leak that is an ordinary word has no lexical signature — only a position. This release fixes the lines and adds the checks that make the class visible.

### Fixed — examples and rules are now universal

- **`references/dependency-model.md`** — the Jira link convention was attributed to one team. It now reads from `local-context.md` (`planning.link_convention`), with the previous behavior as the documented default when unset.
- **`skills/product-reporter` → v0.5.2** — report formatting was attributed to one team (now: the team's report conventions from `local-context.md`), and the output language was hardcoded (now: `user.language`).
- **`references/capacity-model.md`, `references/roadmap-artifacts.md`** — two reference examples were signed with a team and a quarter; now anonymized. A signed example reads as the plugin's rule inside that team and as an unverifiable claim outside it.
- **`skills/knowledge-library` → v0.7.1** — the glossary schema example shipped its sample terms, synonyms, `avoid` list and definitions in one team's language, so every other user read a format spec they could not use as a model. Now English throughout, with the style-profile schema's language-specific notes generalized.
- **`skills/plugin-configurator` → v2.9.1**, **`references/focus-signals.md`** — localized sample values inside config code blocks.
- **`references/visual-annotation-protocol.md`** — the legend example described one marketplace's product page; now generic UI.
- **`references/data-integrity-protocol.md`** — Gate Check 2 shipped one country's benchmark roster under the heading "Geography fit for <Country> market", so every user of the plugin screened external data against one market's competitors. It is now a **tier table** (domestic / regional comparable / global platform / mature Western / heavily local elsewhere) resolved from `product.primary_market` and `product.competitors`, with the out-of-tier caveat travelling into the artifact. The seasonal-window table is relabelled as the worked example it is, with the generic instruction above it.
- **`skills/plugin-configurator/references/context-schema.md`, `local-context.example.md`** — both geography gates referenced `product.primary_market`, a key that existed in no schema. It is now a documented optional field; unset, the gates ask once instead of assuming.
- **`testing/trigger-evals.md`** — fixture phrase E1 named a specific local competitor; now "головний конкурент". Same routing signal, no tie to one market.

### Fixed — the denylist layer is usable

- **Word-boundary matching in `org-tokens.local`.** Tokens were matched as bare substrings, so a three-letter team acronym fired on "offset", "fetch" and "feature": a first run against a real token list produced 46 hits, 42 of them noise. Boundaries are now added where the token's own edge is a word character, which leaves host-style tokens (`example.com`) matching mid-string. The same run after the fix: 4 hits, 2 of them real (both fixed above) and 2 correct-by-design (the author line and the marketplace install path name the repository owner).

### Added — three checks that catch the class, and a test that proves they do

- **`org-signature`** — a team/org name cited as the authority behind a rule (`per <Team> convention`, `(<Team> formatting rules)`), or an example signed with a team and a quarter. Positional, not lexical: in a shipped file the authority behind a convention is the plugin, a config key, or a named vendor — never a proper noun the reader cannot look up.
- **`example-locale`** — a localized sample value inside a fenced block (scope is deliberately code blocks only: bilingual trigger phrases in prose are the plugin's routing surface by design), and any output language hardcoded where `user.language` exists.
- **`example-keys`** — an example issue or Confluence space key outside the placeholder vocabulary (`PROJ-1234`, `SPACE`). A real key is both an org leak and an example the reader cannot run.
- **`testing/seeded_leak_test.py` (stage 1b)** — the checks above are the only ones whose failure mode is silence, so they get a test of their own: the tree is copied, one known-bad line is injected at a time, and the linter must go RED with the expected tag. Ten seeds, one per shipped defect class, written with a fictional org so no real identifier enters the repo. **10/10 caught.** Wired into both CI workflows; the gate-parity check now covers it too.
- **`testing/org-tokens.local.example`** — the optional denylist layer never protected anything because nobody noticed the file was absent (two release cycles, two audits). Its absence is now a WARN on every run, and the example file makes creating it a copy.

### Changed — the rule is written down

- **`testing/Testing-process.md`** — a new section, "Every example in the plugin is universal": placeholders instead of real values, a nameable authority behind every rule, no team signature on examples, language-neutral code blocks, no hardcoded output language, generic domain detail. Two rules added to the Definition of Done, and one honest limit stated: the checks catch shapes, not judgment — whether a plausible-sounding example is domain-specific stays a review question and belongs in the checker's brief.

## v2.4.0 (2026-07-29)

**Visual requirements and team language — stage 2 of the stakeholder-feedback release.** v2.3.0 cleaned artifacts of ungrounded technical content and prose; v2.4.0 closes the remaining two feedback items: requirements lacked "a screenshot with an arrow" showing where changes land, and AI text used terms and tone foreign to the team.

### Added — annotated screenshots (visual index of requirements)

- **New shared `references/visual-annotation-protocol.md`** — the core idea: marker № on the screenshot = requirement № in the table; the screenshot is a visual index, not an illustration, and always ships with a legend table. Source priority: user upload → Figma `get_screenshot` → live product via browser. Rendering: Python + Pillow, fully local (product screenshots never leave the session): numbered marker circles, arrows, no-fill boxes, defined style spec. Mandatory user preview cycle before attaching. Local storage in the **project repository** (`{feature-code}-screen-{N}.png`). Attachment chain — verified 2026-07-29 that the Atlassian (Rovo) MCP has NO attachment-upload tools — so: **Atlassian REST API via curl** (Confluence `child/attachment`, Jira `attachments`; token via env variable whose NAME lives in local-context — the value never does) → browser upload → manual placeholder.
- **`diagram-prototyper` → v0.10.0** — standalone **Annotate mode** ("анотуй скріншот", "додай стрілки на скрін", "annotate this screenshot") + description triggers.

### Added — team glossary + style profile (knowledge-library)

- **`knowledge-library` → v0.7.0** — the team-language contour, in the existing service-skill pattern: **Glossary Build** (mine term candidates from Confluence / Jira / Fireflies / documents — Atlassian read strictly sequential — rank, batch-confirm 10–15 at a time), **Style Build** (profile from 3–10 human-written reference texts: tone, syntax, do/don't, few-shot fragments, AI anti-patterns), **Glossary Manage** (CRUD, "how do we call X"), **Glossary Lint** (service: draft in → replacements / style findings / candidates out). Two-level glossary schema: `terms` (canonical + variants + avoid + en) and `phrases` (officialese → living replacements). Storage `~/.grow-pm/knowledge-library/glossary/ + style/` with vault mirror; routing becomes the triple sources / templates / **terms**; one-time sync of phrases + style with the user's project-instruction style guide. Full workflows in skill-local `references/glossary-workflows.md`.
- **`references/artifact-style-gate.md` v2 — Gate 3 "Team language"**, two touches: **3a style preamble BEFORE generation** (lively text must be born lively) and **3b terminology + style lint AFTER** (merged into the groundedness/language checker lens; `lint_mode: suggest | auto | off`). No glossary configured → Gate 3 silently skips.

### Changed — consuming skills and configuration

- **`requirements-creator` → v0.13.0** — new **Step 4.2 Requirements visualization** (annotated screenshot for existing-UI changes, marker = FR row) + style preamble in Step 4.
- **`task-creator` → v0.12.0** — style preamble before drafting descriptions; new **Step 8.5** attaches annotated screenshots to Design/FE tasks with the legend in the description.
- **`write-concept` → v0.11.0** — annotated current-state screenshot in "What Changes for Users" + style preamble.
- **`plugin-configurator` → v2.9.0** — **Terminology & Style setup** and **Attachments (REST) setup** (site + email + token env NAME, never the value; verified by a live GET) as standalone entry points; `references/context-schema.md` gains both section formats + two `deferred_steps` keys; `local-context.example.md` updated.

### Verification

- **Trigger-evals:** new **Group K** (team language + annotation, 13 phrases) — 100% in 2 independent description-only simulation runs; regression re-run of the groups whose members' descriptions changed (B, E, J) — 100%, 36/36 with full agreement between runs. Logged in `testing/trigger-evals.md`.
- **Smoke tests:** end-to-end Pillow annotation per the protocol (marker + arrow + box on a synthetic product-card screenshot) rendered and visually verified; Glossary Lint on a seeded draft caught **5/5** planted violations including inflected forms ("на продуктовій картці" → "на картці товару").
- Remaining live checks for the first real run: REST attachment against the live Confluence/Jira (needs the user's token env), Glossary Build on a real space, Style Build on real reference texts.

## v2.3.0 (2026-07-29)

**Clean artifacts — quality gate with maker–checker verification.** Stakeholder and team feedback on generated artifacts surfaced two recurring defects: AI-invented technical content sneaks into business/functional requirements and task bodies (the team burns time analyzing recommendations nobody asked for), and requirements/stages drift into paragraph prose instead of scannable lists. Both are now blocked by a shared quality gate — and, critically, the gate is executed by an **independent checker subagent, not by the agent that produced the artifact** ("the maker does not check its own work").

### Added — artifact quality gate

- **New shared `references/artifact-style-gate.md`** — two checklists plus an execution model:
  - **Gate 1 — Ungrounded technical content:** a source test for every technical statement ("can I point to where this came from — the user, a document, a ticket?"). Process parameters (feature flag / A/B, platforms, locales) stay; sourced technical facts stay with their source; AI technical assumptions (technology choices, API/schema design, architecture, effort estimates) are prohibited by default. On explicit user request they land in a separate **"Технічні рекомендації (AI)"** block at the end of the document, opened with a mandatory AI-generated warning callout and per-item confidence markers — never inside functional requirements or a task's "How".
  - **Gate 2 — Lists over prose:** any sequence (steps, stages, requirements, criteria, changes, risks) is a list or a table, never a paragraph; paragraphs only for context/motivation (≤ 3–4 sentences); named prose-enumeration markers for the self-check.
  - **Maker–checker execution model:** the checker is a fresh-context subagent that receives ONLY the draft + sources + checklists (never the maker's reasoning), reports structured findings without rewriting, and must walk every section explicitly (anti-rubber-stamping — an empty no-comment report is invalid). One fix cycle + one re-check of fixed locations; disputed findings are surfaced to the user, never silently dropped. Critical artifacts (Confluence publish, Jira creation) get **two checkers with distinct lenses** (form / groundedness). Limits: ≤ 2 checkers, sequential when reading Atlassian MCP; inline fallback carries the explicit marker "незалежність перевірки знижена (inline)". Optional config: `Artifact Quality Gate → review_mode: subagent | inline | off`. Gate 3 (Team language) is reserved for v2.4.0.

### Changed — consuming skills

- **`requirements-creator` → v0.12.0** — Step 2 applies the Gate 1 source test while gathering requirements; Step 4's Business requirements section becomes a **bulleted list of theses** (1–2 sentences each) instead of prose with bold; an optional "Технічні рекомендації (AI)" block (request-only, callout-guarded); new **Step 4.5 — Artifact quality gate** (two lenses) before user review; formatting rule 7 "lists over prose". **Thin-core refactor:** the entire Analyze & Improve mode (A1–A9) moved verbatim to skill-local `references/analyze-improve-mode.md` (core 597 → ~435 lines); inside the mode, A2 gains two content checks (ungrounded technical claims, prose-formatted requirements) and A6 gate-checks the improved document. `references/requirements-template.md` updated to match (theses format + optional AI block).
- **`task-creator` → v0.11.0** — "How" is built ONLY from the requirements and confirmed context (no invented engineering steps; D1 checklists stay process-level); optional "Технічні рекомендації (AI)" section at the end of a description; **batch quality gate** over all drafted descriptions before any Jira issue is created; **Step 12 post-creation verification switches to maker–checker** — the maker fetches the created task, an independent checker evaluates it (previously the same agent that created the tasks verified them); Step 12c adds two checks (list formatting, no ungrounded tech content outside the AI section).
- **`write-concept` → v0.10.0** — Technical Considerations carries only confirmed constraints and dependencies (source test); AI assumptions request-only in the callout-guarded block; new **Step 4.5 — Artifact quality gate** before user review.
- **`meeting-processor` → v0.13.4** (patch) — quality standard pinned: topics / decisions / action items / next steps are always lists or tables; optional full gate run for Confluence-bound MoMs.

### Notes

- Skill descriptions (triggers) are unchanged — no trigger-evals impact.
- Design doc: `Release-Design-v2.3.0-v2.4.0-Artifact-Quality.md` (workspace). v2.4.0 will add annotated screenshots (visual-annotation protocol + REST attachments), the team glossary + style profile in `knowledge-library`, and Gate 3 "Team language".

## v2.2.0 (2026-07-17)

**Debate Mode — role-based adversarial discussion engine.** A single brainstorming agent both generates ideas and approves them: trade-offs between interest groups (buyer / seller / business / risk) go unnoticed and ICE Confidence inflates. The mechanic proved itself ad-hoc in a live research session — four conflicting roles argued a prioritization decision and flipped it — and this release turns it into a reproducible, guarded protocol instead of a lucky prompt.

### Added — Debate Mode

- **`references/debate-protocol.md`** — shared debate engine any skill executes directly (the `subagent-delegation.md` pattern; no new skill): **D0** applicability check (contested decision + ≥ 2 affected interest groups + an existing evidence base — otherwise route to research/ranking instead); **D1** setup (exactly one binary/limited-choice debate question; 3–5 roles via AskUserQuestion from a 10-card preset library plus custom roles, the **Skeptic / Risk-officer always mandatory**; evidence pack `E1…En` strictly from data that passed integrity gates, assumptions explicitly marked `A1…An`); **D2** parallel opening positions (one subagent per role: position / top-3 arguments with E# references / main risk / what would change my mind); **D3** cross-examination (attack the opponents' strongest argument, defend the own weakest, record position shifts; Round 3 only if ≥ 2 roles shifted — and asks the user first; hard max 3 rounds); **D4** facilitator synthesis (consensus points, live disagreements, position shifts, verdict + confidence, **mandatory minority report**, ICE Confidence correction: full consensus +1…+2, unresolved skeptic objection −1…−2, new risks → the hypothesis Risks field); **D5** output & save (a «Debates» section in the parent artifact — round transcripts in collapsed expand-blocks, verdict table open; chains onward to `decision-log` and `experiment-tracker`). Guardrails: anti-sycophancy (convergence forbidden before Round 2; a role that attacked nothing gets its round re-run once), no new facts (debaters get no web/vault/file access), data policy (debaters are local subagents — internal data never leaves the session), cost cap (default 4 roles × 2 rounds = 8 subagent calls, hard cap 12), at most **one** facilitator-added role mid-debate (user-confirmed, within the cap), and an inline-simulation fallback without the Agent tool that must carry the visible marker "inline simulation: role independence reduced".
- **`brainstorm-features` v0.10.0 — Debate mode (Step 3D)**, the primary human entry point. Activates on explicit request, as an offer after Steps 3A–3C, or when called from another skill's Debate hook with a ready evidence pack. Verdict corrections re-sort the ICE tables, new risks append to the hypotheses, the «Debates» section embeds in the saved artifact (Step 5 structure), and Step 9 additionally saves the debate to the vault (`type: "debate"`). Step 4 now proposes "stress-test the top-3 hypotheses via a role debate". The description gains EN+UA debate triggers plus a "Do NOT use" guard (meeting transcript discussions → `meeting-processor`; recording an already made decision → `decision-log`).
- **Debate hooks in 4 skills** (thin, ≤ 8 lines each): `product-research` v0.10.3 (Step 3 — debate over gate-validated findings; the live precedent happened exactly here), `cjm-research` v0.7.3 (top-3 hypotheses after pipeline Step 7; corrections feed the Step 11 risk assessment and the Step 12 report), `write-concept` v0.9.3 (red-team before publishing; unresolved objections land in Risks / Open Questions), `decision-log` v0.2.4 (debate before the save gate; verdict + minority report enter the ADR).
- **Vault artifact type #34 — `debate`** → `Debates/{product}/`: taxonomy row, TYPE_FOLDER_MAP entry, folder-structure block, naming example, and extended frontmatter (`debate_question`, `roles`, `verdict`, `confidence`, `minority_report`, `rounds`, `inline_simulation`). SKILL_CONTEXT_MAP surfaces past debates as context to `brainstorm-features` and `decision-log`.
- **Trigger-evals: Group I** (8 EN+UA phrases — Debate mode vs `meeting-processor` vs `decision-log` vs standard brainstorm) and **Group J** (People contour + the v2.1.1 guards the log-status note demanded: one-on-one vs meeting-processor, performance-review vs product-reporter member-review, write-concept vs requirements-creator on "describe a feature", product-research vs knowledge-library). Fresh descriptions-only simulation run recorded in the Results log.

### Changed

- **`brainstorm-features` core slimmed 443 → 385 lines** (release gate: ≤ 400 after changes): the full Step 3C CJM-hypothesis workflow (3C-1…3C-6 — hypothesis format, CJM-weighted ICE, funnel-impact formulas, categorization, the return contract to `cjm-research`) moved **verbatim** to skill-local `references/cjm-hypotheses-mode.md`, following the v1.34–v1.35 monolith-refactor pattern; the core keeps the activation conditions, the input contract, and a one-paragraph map of the reference.

**Deliberately out of scope (v1):** web search for debaters (evidence pack only — otherwise fact quality is uncontrolled), a separate debate-panel skill, a dedicated debate report template subtype, scheduled headless debates.

---

## v2.1.1 (2026-07-15)

**Re-audit remediation — audit #2 of v2.1.0.** The v2.0.0 audit's fixes verifiably held where they were aimed; a second, independent audit of the result found what they did not reach. Two themes: **live organization data the genericized lint check cannot see**, and **a rule fixed in one place while its copies drifted on** — 7 of the findings are "two sources of one truth" failures. Both validators were green throughout, which is the point: three new checks now cover the classes they missed.

### Fixed — P0, organization data in shipped files

- **`jira-data-protocol.md` contradicted its own first line** ("All org-specific ids live in local-context.md — never hardcoded here"): a real Jira Team UUID **with the team's name**, the org's real Atlassian Cloud ID, and live sprint ids labelled "example only". The team UUID was duplicated in `task-creator`. All now placeholders resolved from `local-context`.
- **`data-integrity-protocol.md` shipped what `data-policy.md` itself classifies as confidential** — real GMV/CR figures and a source catalog naming internal workbooks, an internal live-metrics tool and a tracker key. The anti-patterns and correct-patterns are rewritten on a fictional two-stream product; **the arithmetic, which is the actual lesson, is preserved verbatim**. The catalog moves to `local-context` → `data_sources_catalog`.
- **The `SEX` sprint prefix survived both the v2.0.1 fix and the history purge** — 8 occurrences across 4 files, including a routing trigger shipped to every install. It was the only token from the purge list still present.
- Org vocabulary made universal: the internal live-metrics tool (now the `internal-live` source marker), "Prom-context" geo defaults (now keyed on `product.primary_market`, with the UA ladder as a worked example), release-stream names, feedback segments, and the worked-example persona across 5 files.

### Fixed — P1, validators that passed the leak

Re-injecting the **original v2.0.0 leak** (board id + epic keys + VIP name) into the example file **passed GREEN**. Root cause: after v2.1.0 made the denylist user-supplied, `testing/org-tokens.local` existed in **no environment** — not in CI (gitignored by design) and not on the author's machine — and the mechanism was documented nowhere. A check nobody knows to enable is not a check.

- **Documented** in README (Testing & Contributing) and `Testing-process.md`, with the standing rule: purge an identifier → add it to the denylist **in the same commit**.
- **The layer that must work without it** now fails by shape on literal UUIDs, registry ids (ЄДРПОУ/EDRPOU), internal hostnames (`*.corp`/`internal`/`lan`/`intra`) and service hosts (`gitlab.`/`jira.`/…), and scans **README and `testing/**`** — both previously unscanned, and a real `catalog-ui` stream name in README was found by exactly this change. Placeholder hosts now match whole labels: `mycompany.io` no longer passes because "company" is a substring of it.
- `ghost-skill` fired only when a real skill shared the line, so a chain line naming just its ghost was invisible. `vault-types` missed prose-wrapped and single-quoted `vault_save` types — three real types in `product-research` were unvalidated. `artifact_type`'s enum slurped its section's prose, making `template-library` and `focus-advisor` legal artifact types. `skill_version: v0.9.0` made the sync check invisible rather than failing. `stale-names` was case-blind and skipped README. `duplicate-h1` skipped SKILL.md. TYPE_FOLDER_MAP duplicate keys were last-wins.
- **CI**: `permissions: contents: read`; PyYAML installed with `GROW_LINT_REQUIRE_YAML=1` so the strict frontmatter parse can no longer degrade to a warning that gates nothing; `grep -F` in the shell script (dots in a version were regex wildcards, so `v2x1x0` satisfied a `v2.1.0` check).

### Fixed — P2, the release that skipped two releases

`release.yml` only ever read `plugin.json` at push HEAD, so when v2.0.1, v2.0.2 and v2.1.0 landed in one push, **only v2.1.0 was tagged** — and on the wrong commit (`ea64e32`, a change described in no CHANGELOG entry). v2.0.1 and v2.0.2 are documented releases that cannot be pinned or diffed. A guard now fails the release when the CHANGELOG documents versions between the newest tag and the one being cut (verified against the historical scenario).

### Fixed — P2, vault: schema vs the algorithms that serve it

- **People artifacts key by person, not product** — the schema mandated `{folder}/{product}/` for every People type, scattering one person's goal letters across every product folder while Step P's whole job is "load everything known about a person". The schema was wrong; the protocol and skills were right.
- `vault_init` and `vault_structure_check` **took `plugin_folder_name` and then wrote to the vault root** — one level above the plugin's own folder, into the user's vault. `vault_init` also copied local-context to `REFERENCE-local-context.md`, a filename the Context Mirror, the setup guide and its own smoke test (S-8.2) do not expect — that test could not have passed. Plus a top-level `archive/` and a `dashboard/` folder that exist in no schema.
- `vault_save` built `last_updated`/`linked_hypothesis` (schema: `last_reviewed`/`tested_hypothesis`) and **omitted the required `skill`/`skill_version`**. The Hypothesis Lifecycle branched on `winner_id`/`loser_id`/`hypothesis.id` — fields that exist nowhere — and wrote a status outside the enum; it now branches on `ab-test-results.result`, and an inconclusive test leaves the hypothesis in `testing` (it did not decide it).
- **New check `vault-paths`**: the schema's own MOC templates put the product above the area subfolder and linked an `archive/` folder the same file forbids. Those examples are what the model imitates at save time. 23 example paths corrected; every wikilink in the three vault docs is now checked against TYPE_FOLDER_MAP.
- The 650-line "Template Files" section — the pre-v2.0 flat template system that `template-protocol.md` replaced and `vault_init` forbids writing — is cut to a pointer.

### Fixed — P2, templates: a ladder that reached nothing

- **All five `ops-report` built-ins were unreachable** through the protocol's built-in ladder: it resolves by filename (`builtin://{type}/{subtype}-v1.md`) while they declared `subtype: ops-sprint-plan…` against files named `sprint-plan-v1.md`. Their own `template_id` already implied the unprefixed form. Fixed, and **new check `builtin-subtypes`** enforces it.
- **One CJM report under two `artifact_type`s**: `product-analysis` declared `research`/`cjm-funnel` for the report `cjm-research` saves as `cjm`, then declared a fallback to the shared built-in that a `research`-typed request can never match.
- **Step T meant different things in different files** — four skills had renumbered the shared protocol locally, so "Step T-4" was ambiguous; and **four marker formats** were in use, with 4 of 5 built-ins citing template ids that were not their own.
- `meeting-processor`'s Step T offered `decision` and `review` subtypes its M3 classifier cannot emit.

### Fixed — P2/P3, config, gates and chains

- **One canonical Templates key set** (context-schema): the write side and the schema side had disagreed, so half the config was read-but-undefined and half defined-but-unwritten. Dead key `auto_save_to_vault` removed — written, offered in Update mode, read by nothing.
- **Four sections added that skills already read**: `experiments.stale.*`, `feedback.*`, `plugin_release.*`, `data_sources_catalog`. Key names that pointed at nothing fixed (`product.cjm_configuration.*`, `configured_confluence_spaces`, `knowledge_library.search_modes` with an enum that exists nowhere, `product.default_language`).
- **Callers still forced the mode v2.1.0 removed** — Step 0b and the auto-trigger sent every skill to Onboarding unconditionally, bypassing the backup and vault-recovery branch that exist for a partial wipe.
- **Gates that could not do their job**: `task-creator`'s mandatory check required a description section its own format never writes (every correct task failed it); `cjm-research`'s scheduled health-check still hit an interactive question; `design-bridge`'s only blocking gate read `qa_rules` with no missing-file branch, and its Design System redirect pointed at a configurator step that does not exist.
- **Chains and triggers**: `diagram-prototyper` chained to a skill that does not exist; `design-bridge`'s description advertised two hooks its body removed in v2.0.2; `write-concept`'s next step was labelled, described and executed as three different things; `write-concept`/`requirements-creator` both claimed "describe a feature" with no guard; `focus-advisor` filtered a `revisit_by` field `decision-log` never wrote (a permanent false negative); two connector tool names did not exist.
- `quarterly-planning`'s `plan` mode consumed a step it skipped; `experiment-tracker`'s `awaiting-readout` meant two things, so the stale detector nagged about readouts that existed.

### Fixed — P4, docs that contradict the code

README claimed 7 design skills over a list of 6 (and still named the one v2.1.0 dropped), listed 5 of product-reporter's 6 modes, and enumerated 17 of "24 seed templates" — v2.0.1 fixed the count and not the list. The manifest description was 1259 chars in one sentence, omitted three skills, and had drifted between its two copies (now one canonical 844-char text). `vault-schema` claimed 32 types (33). The CHANGELOG's version-format block sat between two entries, so the release workflow would have appended it to v2.0.1's notes.

**Testing docs stop asserting gates that did not run**: `test-cases.md` promised "Updated EVERY release" over a registry that skips v1.16.0–v1.40.0 and v2.0.0; `trigger-evals.md` calls itself part of the DoD but its last logged run predates the releases that rewrote all 29 descriptions; `output-evals.md` is a blocker with no 3b run recorded for v2.0.x/v2.1.x. Each now states the gap and what the next run must cover. **New check — CI gate parity**: `validate.yml`'s comment promised its gate matches `release.yml`'s "exactly"; a comment cannot enforce that, and drift means a PR goes green, merges, then fails the release with no earlier signal.

### Enforcement

`testing/skill_lint.py`: **13 → 15 checks** (`vault-paths`, `builtin-subtypes`), plus hardened `org-data`, `ghost-skill`, `vault-types`, `artifact-types`, `stale-names`, `duplicate-h1`, `readme-versions`, `skill-version-sync`. `validate-consistency.sh` gains CI gate parity and `grep -F`. Every check verified by injecting its defect into a repo copy — including re-injecting the exact v2.0.0 leak and the exact `ops-` prefix bug.

### Known — still open (needs the repository owner)

- **GitHub still serves the full pre-purge history** via `refs/pull/1..35` — all 35 head SHAs are pre-purge commits. Force-push cannot fix this; it needs a GitHub Support request ("purge unreachable objects / stale PR refs after history rewrite") or repo delete/recreate.
- **The GitLab mirror's `main` is still pre-purge history** and its tags stop at v2.0.0 (branch protection rejected the force-push). Needs unprotect → `git push --force mirror main` → `git push mirror --tags`.
- **The `SEX` prefix remains in git history** (from commit `7fe89fb`); the tree is clean. Worth purging together with whatever resolves the PR-refs question, since a second rewrite would hit the same wall.
- `~/grow-pm-backup-20260714-223144.bundle` (17 MB) still holds the original history — delete once the above is settled.

---

## v2.1.0 (2026-07-14)

**Audit remediation, P3 + P4 — the last of the 2026-07-14 audit.** Closes the behavioural defects: a safety gate that could be skipped, a mode with no workflow, a config field nothing defined, and a health score that only summed correctly for one funnel shape. With this release every finding from the audit is either fixed or deliberately deferred with a reason.

### Fixed — gates and safety

- **`design-bridge` could ship a handoff with no accessibility audit.** Step 4e required `audience ∈ {c-level, dev_handoff}` on top of the intent, so a **handoff with `audience=team` skipped the audit entirely** — and Step 6's "A11y: if Step 4e ran" then never blocked it. This contradicted three other statements of the same rule in the same skill (the checklist's "handoff → full WCAG 2.1 AA, blocker", Quality Standards' "non-negotiable for handoff", and the failure-mode table). The audit now always runs for deck/prototype/handoff; scope and blocker-severity come from `a11y-checklist.md`, which is the one place that decides. The audience does not change whether a disabled user can use the thing.
- **`plugin-configurator` could start a fresh onboarding over live data.** Two mode-selection rules both matched "`local-context.md` is gone but `~/.grow-pm/` or a vault mirror still has data", and textual order sent it to Onboarding — bypassing RM-0's backup and the RM-1 vault-recovery branch that exists for exactly that state. Rules are now ordered, data-presence first.
- **Step P profile writes are uniformly gated.** The protocol gated 2 skills and made the rest "silent-with-notice", while 3 of those declared gated writes anyway. A profile records a judgement about a person; the manager owns it.

### Fixed — dead ends and undecidable routes

- **`focus-advisor`'s `journal` mode had no workflow, no output, and referenced "streaks"** — a word that appeared nowhere else in the plugin. It now has a defined flow: show non-terminal focuses, offer done/snooze/drop/keep per item, gate, write transitions, summarize. Nothing is auto-closed.
- **The `chosen` journal status was unhandled by dedup.** `focus-scoring.md` handled `done`, `snoozed` and `proposed`, so a focus the PM had *already picked* fell through and got re-ranked against fresh signals every morning — the quiet way a chosen focus slips off the brief. It now pins to the top without re-scoring, with an honest nudge after 2 cycles.
- **`design-bridge`'s "handoff with screen generation" route had no deciding input.** Step 0.5 and the toolkit protocol both branched on it; no question collected it. Added Q4a (document existing designs vs generate the screens).
- **Two core-enum capabilities were unreachable:** `figma-write` and `code-first-research` were declared in the toolkit protocol §3 but absent from §6's request→capability mapping, and §3's "user may reference explicitly" escape covers only *custom* capabilities. Both now have routes; every core-enum member appears in the mapping.
- **`deck-subtypes.yaml` was wired to a step that never cited it.** Its header says "Read by design-bridge Step 3"; Step 3 never mentioned it. Combined with the `feature`/`feature-concept` key split (v2.0.2), the slide outlines were unreachable by the documented lookup.

### Fixed — config fields that nothing defined

- **`Focus → Zones`** was read by three strategic collectors (white spaces, NPS themes, knowledge scoping) but defined in no schema — the collectors had nothing to read. Now in the schema, the example, and with a documented fallback.
- **`healthcheck`** lived under `Sources` in both schema files while `focus-advisor` reads `Focus → Scheduled → healthcheck` and the example already had it under `scheduled:` — the lookup found nothing in a schema-conformant file. Moved to Scheduled; subsection order aligned between the write side (`context-schema.md`) and the read side (`focus-signals.md` §8).
- **`Templates` and `Planning` sections** were written by onboarding and read by skills but defined in no schema — `context-schema.md` calls itself "the complete schema definition", and Planning's format was delegated to the example file, which is illustrative, not normative. Both now defined.
- **`deferred_steps` keys**: onboarding wrote 6 keys the enum didn't list (`key-metrics`, `analytics-extended`, `tableau-mcp-required`, `planning`, `focus`, `people`) while the enum listed 2 nobody writes (`okrs`, `competitors`) — for five sections "is it deferred?" was unanswerable. Enum now maps key → writing step.
- **`organization.atlassian_cloud_id`** was required by product-reporter and defined nowhere. Now schema'd, and documented as auto-discoverable.

### Fixed — arithmetic and coverage

- **CJM health-score weights only summed to 100% for a 4-stage funnel.** "First 15% / Middle 25% **each** / Last 35%" is correct for the E-commerce default, but the 5-stage Marketplace funnel scored out of 125 and the 6-stage SaaS funnel out of 150 — silently deflating every health score computed on them. Weights are now shares (first 15% · all middles 50% split evenly · last 35%), with worked examples per shipped template and a two-stage rule.
- **Validate mode couldn't see half the config.** Planning, Focus and Templates were absent from V-4's scoring and from the Update menu the setup steps hand off to — a readiness report could read 100% while the planning suite had nothing to read. Deferred sections are now reported as deferred, not scored as gaps; People and Design Toolkits are presence-only, never scored.
- **Declining the Knowledge Library skipped the Template Library** (Step 12 jumped to Step 14), leaving `templates_setup_completed` unset and Step 16g nudging someone who was never asked — against O-T.2's "always asked, even when using built-in only".
- **CJM health-check notifications** were defined in the schema and editable via Update mode, but no onboarding step collected them. Added 11g.
- The Step 16c skeleton lacked placeholders for the Templates/Planning/Focus/Design-Toolkits/People sections that later steps write into it; the write-ordering (steps 13–15 buffer, 16c writes once) is now explicit.

### Changed

- `local-context.example.md` gains the CJM, Knowledge Library, Templates, Obsidian Vaults and People sections (all schema-defined, none previously exemplified) plus `Focus → zones`.
- README Getting Started now carries the actual install commands and the marketplace/repo names.
- `design:user-research` removed from design-bridge's promises — no step ever called it; `product-research` owns primary research.
- Slide-count guidance in design-bridge now cites `deck-subtypes.yaml` instead of restating different numbers (8–12 vs the yaml's 10/14; 6–8 vs 7/10).
- The `wireframe` boundary is now symmetric and decidable: branded/DS → design-bridge, plain structure → diagram-prototyper, ask when the request doesn't say.

### Files

- Changed: 4 `skills/*/SKILL.md` (minor bump — behavioural), `skills/design-bridge/references/a11y-checklist.md`, `skills/plugin-configurator/references/` (context-schema, onboarding-steps, maintenance-modes), `references/` (cjm-protocol, focus-signals, focus-scoring, people-context-protocol, design-toolkit-protocol, data-integrity-protocol, jira-data-protocol), `local-context.example.md`, `README.md`, `CHANGELOG.md`, `testing/`, both manifests.

---

## v2.0.2 (2026-07-14)

**Audit remediation, P2 — structural drift.** v2.0.1 fixed the defects that were mechanically wrong (leaked data, duplicated docs, phantom paths). This release fixes the ones that were *architecturally* wrong: three documents each claiming to define the vault layout, chain edges that existed only on paper, and a template system whose fallback could not be satisfied. Three new linter checks make each class blocking.

### Fixed — vault layer: one source of truth

- **`vault-schema.md` is now declared the single source of truth for vault layout**, and `vault-protocol.md` (save/init/search) and `obsidian-setup-guide.md` (setup smoke tests) conform to it. Previously all three described *different* layouts: the protocol saved to `{vault}/artifacts/{type}/{product}/` with the MOC at `dashboard/MOC-Dashboard.md`, the schema documented an area-first tree with `_MOC/Dashboard.md`, and the setup guide's four smoke tests checked a third layout — against the very algorithm it delegates to, so they could not have passed.
- **One path rule, no exceptions:** `{vault}/{TYPE_FOLDER_MAP[type]}/{product_slug}/{filename}`. The schema's own tree contradicted its map on nesting order (`CJM/{product}/full-reports/` vs `CJM/full-reports/`); the tree now follows the map. Lifecycle status lives in frontmatter, not in folders.
- **10 artifact types that skills were already saving had no home in the schema** — `feedback-triage` (in the taxonomy but absent from TYPE_FOLDER_MAP, so it had no resolvable folder at all), `report-3t5f`, `presentation`, `prototype`, `handoff` (the schema even called the latter two "existing" while defining neither), `vacancy-profile`, and the People contour. Taxonomy grows 22 → 33 types, all mapped.
- **The People contour gets a defined home:** everything about a person under `People/` — one folder, one sensitivity boundary (`People/goals/`, `/reports/`, `/1-1/`, `/reviews/`, `/offboarding/`, `/delegation/`). The protocol's own wikilink examples pointed at top-level `Goals/`, `Reports/`, `1-1/` while the skills wrote to `People/…` — three homes for the same artifact. `vacancy-profile` sits outside `People/` deliberately: a vacancy is a role, not yet a person.
- **`vault_init` now derives its folders from TYPE_FOLDER_MAP** instead of restating them — the hardcoded list had fallen 7 types behind. Same for the search glob and the MOC paths.
- **`REVERSE_CONTEXT_MAP`** — used by `vault_save` step 7, defined nowhere — is now derived from SKILL_CONTEXT_MAP rather than being a second map to keep in sync. **SKILL_CONTEXT_MAP** grew from 8 to all 29 skills (`local-context-protocol.md` sends every skill to Step 0.5, so the 21 missing rows meant silent skips), with People types restricted to People-contour readers.

### Fixed — chain contracts that existed only on paper

- **`experiment-tracker` was unreachable by chaining.** It claimed inbound edges from `brainstorm-features` and `requirements-creator` — neither mentioned it — while `focus-advisor` routed "A/B test waiting for a decision" straight past it to `product-analysis`. All three edges are now real: brainstorm-features offers registration after ICE ranking, requirements-creator registers A/B specs with their Decision Rule, and focus-advisor routes test-readout and decision-revisit signals through the skills that own that state.
- **`decision-log` named three callers that never called it** (meeting-processor, quarterly-planning, project-planning) plus a focus-advisor signal feed that did not exist. meeting-processor now chains decisions to it (instead of hand-writing `Decisions/` files); the planning skills offer to log scope cuts and replan calls; `revisit_by` dates are a real tactical signal in `focus-signals.md`.
- **`diagram-prototyper`'s inbound table listed 5 callers, none of which still call it** — all moved to design-bridge when it arrived in v1.10.0. Table now lists the actual callers and states the boundary (lo-fi/DS-free visuals here, brand-themed decks there).
- **`design-bridge` claimed auto-triggers from `cjm-research` and `meeting-processor`** that have no hook on the upstream side; both correctly route to diagram-prototyper instead. Rows removed, stale step numbers on the remaining four corrected (Step 7/5 → Step 8).
- Unsubstantiated inbound claims dropped from `roadmap-architect` and `project-planning`. The chain graph describes what exists.

### Fixed — templates and Step P

- **The zero-candidate fallback was unsatisfiable for 4 of 9 types.** `builtin://{artifact_type}/default-v1.md` does not exist for `cjm`, `research`, `presentation` or `ops-report` — those ship only subtype files, deliberately (a generic "default ops report" is not a document anyone wants). The rule is now a ladder: requested subtype → `default-v1` → the type's only built-in → warn.
- **`storage_root` was defined nowhere.** `template-protocol.md` deferred to `persistent-storage.md`, which never mentioned the term; the only concrete rule lived in an onboarding step and named a path the protocol simultaneously called *legacy*. `persistent-storage.md` now defines the resolution (vault → `{vault}/{plugin_folder}`, else `~/.grow-pm`), and its directory tree matches what skills actually create (`Templates/` per the protocol, plus `people/`, `experiments/`, `decisions/`, `focus/`).
- **4 artifact types were declared by skills but absent from the enum** (`roadmap`, `meeting-notes`, `focus`, `delegation-audit`) — users could not create templates for them. The enum is now an explicit, machine-checkable block; template-library's wizard list matches it.
- **`roadmap-architect` had no Step T** — the only artifact-producing planning skill without one, against the protocol's own "MUST".
- **Step P write-gating contradicted itself**: the protocol gated writes for 2 skills and made the rest silent, while 3 of those "rest" declared gated writes anyway. Now uniformly gated — a profile records a judgement about a person, and the manager owns it. `product-reporter` (which writes profile fields from `goal-report`) is documented in the reads/writes table it was missing from.
- **product-reporter's Steps 7–8 were nested inside the `goal-report` section** though their content covers all six modes — read structurally, the five ops modes ended with no feedback loop and no vault save. Promoted to shared final steps; the duplicate goal-report persistence (two destinations, two optionality rules) is resolved.

### Added — validators

Three new checks (13 total): **`vault-types`** (every `vault_save` type is in the taxonomy *and* TYPE_FOLDER_MAP — an unmapped type has no destination), **`artifact-types`** (every Step T `artifact_type` is in the protocol enum), **`chain-contracts`** (a claimed `← X` edge exists on X's side, or X is one this skill calls — the notation carries both meanings). `chain-contracts` found 3 further one-sided claims beyond the audit's list on its first run.

### Files

- Changed: 13 `skills/*/SKILL.md` (patch bump), `references/` (vault-schema, vault-protocol, people-context-protocol, persistent-storage, template-protocol, focus-signals), `skills/plugin-configurator/references/` (obsidian-setup-guide, onboarding-steps, maintenance-modes), `testing/skill_lint.py`, `README.md`, `CHANGELOG.md`, both manifests.

---

## v2.0.1 (2026-07-14)

**Audit remediation (P0 + P1) + the validators that make these defect classes non-recurring.** A full audit of v2.0.0 (29 skills, 30 references, 24 templates, manifests, CI) found 5 critical and 14 major defects that both validators passed green. This release fixes the P0/P1 set and rebuilds `skill_lint.py` so each defect class is now a named, blocking check.

### Security — P0

- **Real organization data removed from shipped files.** `local-context.example.md` carried a genuine team roster (surnames per platform), Jira board id, epic keys with a goal map, sprint anchor, a named VIP stakeholder with email, and an internal mission commit — in a public repo, contradicting the file's own "should NOT be committed" warning. All replaced with placeholders. The same class of leak was cleaned from `planning-core.md` (goal map + feature-naming example), `focus-signals.md` (VIP name), `jira-data-protocol.md` (hardcoded space id), `people-context-protocol.md` (team name), `capacity-model.md`/`roadmap-artifacts.md`/`dependency-model.md` (org labels), `focus-cadence.md` + `trigger-evals.md` (sprint names), `project-planning`/`onboarding-steps` (goal keys), `release-pitfalls.md` (internal GitLab host), the `sprint-review` template (Atlassian host), and one CHANGELOG line with live page ids.
  > Note: this data remains in git history. Remediating history is a separate, deliberate decision.

### Fixed — P1

- **Two protocol documents contained themselves twice.** `references/vault-protocol.md` (1435 → 751 lines) and `references/persistent-storage.md` (699 → 426) each had a stale copy appended below the current one — new versions had been *prepended* instead of replacing (commits `07d0936`, `c152ee0`). The stale halves carried conflicting footers (v1.0 vs v1.1) and lacked the Context Mirror / Pre-Update Backup / Vault Recovery sections, so a reader could land on contradicting guidance. Removed; every load of these protocols is now half the context.
- **Phantom references and ghost skill names.** `product-reporter` pointed its template fallback at `references/builtin-templates/<subtype>.md` — a directory that never existed (real path: `templates/built-in/ops-report/`). `hiring-designer` chained to `people-context` and `onboarding-steps.md` twice cited `write-spec` — neither is a skill. `meeting-processor` still said `Feature-task-creator` (renamed to `task-creator` back in v1.24). `local-context-protocol.md` and `people-context-protocol.md` pointed at `references/context-schema.md`, which exists only skill-locally. `self-improvement.md` cited the unwritten `context-budget.md`.
- **`feature` vs `feature-concept` deck-subtype mismatch.** `deck-subtypes.yaml` keyed the outline as `feature-concept` while design-bridge, the built-in template's frontmatter, and the fallback id all use `feature` — and both callers (`write-concept`, `requirements-creator`) passed `feature-concept`. Exact-key lookup missed in one direction or the other for the most common deck. Canonicalized to `feature`.
- **focus-advisor headless contract contradicted itself** — the headless rules permit the metrics health-check chain when configured, while Quality Standards said "never in headless". The exception is now stated in both places.
- **28 of 29 SKILL.md frontmatters were not valid YAML.** An unquoted `Українською: "…"` inside the plain-scalar `description` terminates the scalar: Claude Code's lenient parser accepted it, but PyYAML/js-yaml/gray-matter — i.e. any external tooling, CI step, or other agent — failed to parse. Rephrased to `Українською — …` (plus three skills with a second `: ` hazard). All 29 now parse strictly.
- **Four descriptions exceeded the 1024-char spec limit** for the field the model routes on: `product-reporter` (1289), `focus-advisor` (1210), `hiring-designer` (1121), `performance-review` (1077). Trimmed with every trigger phrase and boundary preserved. product-reporter's parenthetical also listed 6 of the 8 3T5F elements — dropped rather than corrected, since `reporting-3t5f.md` is the source of truth.
- **README resynced with reality** — 16 skills' versions were stale against their frontmatter (Plugin Configurator claimed v2.5.0 at actual v2.7.0), the Feedback Triage section contradicted the summary table in the same file, "17 built-in templates" understated the shipped 24 (the 7 People templates were undocumented), "Five methodology references" listed six, and `release-pitfalls.md` was cited at a non-existent root path.

### Added — validators (so these classes cannot come back)

- **`testing/skill_lint.py` rebuilt** — 10 named checks, one per defect class the audit found: `frontmatter-yaml` (strict parse + plain-scalar hazard scan, stdlib-only), `frontmatter-fields` (name==folder, semver, description ≤1024), `skill-version-sync`, `ref-paths` (multi-segment paths, `.yaml`, placeholder dirs, skill-local resolution, recursive — the old glob was one level deep and blind to `references/examples/**`), `ghost-skill` (a kebab token on a line citing a real skill, checked against the repo's own auto-derived template vocabulary), `stale-names` (renames incomplete outside CHANGELOG history), `duplicate-h1` (a doc containing itself), `readme-versions` (README ↔ frontmatter), `org-data` (internal identifiers, real Atlassian hosts, non-placeholder emails in shipped files), `deck-subtypes` (yaml keys ↔ template subtypes).
- **`.github/workflows/validate.yml` now runs `skill_lint.py`** alongside the consistency script — previously only the release gate ran it, so a PR could pass CI, merge, and fail the auto-release on main with no earlier signal.
- **`.github/workflows/release.yml`** gains a `concurrency` group (two rapid pushes to main raced the tag check, failing the loser red instead of skipping) and its CHANGELOG-extraction awk now also stops at legacy `## [x.y.z]` headings.

### Files

- Changed: all 29 `skills/*/SKILL.md` (patch bump), `references/` (12 files), `templates/built-in/ops-report/sprint-review-v1.md`, `local-context.example.md`, `README.md`, `CHANGELOG.md`, both manifests, `testing/skill_lint.py`, `testing/trigger-evals.md`, `testing/Testing-process.md`, `testing/test-cases.md`, both workflows.


## v2.0.0 (2026-07-14)

**Wave 3 — the People-contour.** The plugin grows a second contour alongside product/data/delivery: **manager → people → goals → communication → development**. Six new skills, a new person-profile protocol (Step P), five methodology references, one **breaking rename**, and framework upgrades to nine existing skills. Person data is the highest-sensitivity tier — vault/local only, never Confluence/Jira/external LLMs.

### Breaking

- **`team-ops-reporter` renamed to `product-reporter`.** All live references updated across skills, references, manifests, README, and testing (historical CHANGELOG entries keep the old name as an accurate record). The skill gains a new **goal-report (3T5F)** mode (build/audit a person's or a direction's report against a goal). This rename is why the plugin goes to **v2.0.0**.

### Added — foundation (references + protocol)

- **`references/people-context-protocol.md`** — **Step P**: a persistent, vault-local profile per team member (D-type, delegation levels, active goals, reporting cadence, 1-1 history, GTD-index, signals). Storage in the vault `People/` area or `~/.grow-pm/people/`.
- **`references/goal-frameworks.md`** — SMARTCBP (8 checks), MBO-vs-OKR selection, Tell-and-Sell commitment, goal letter, cascade.
- **`references/people-frameworks.md`** — Hersey-Blanchard (D1–D4/S1–S4), 7 levels of Appelo, GTD-index, NVC feedback, "Did you tell them yourself?".
- **`references/reporting-3t5f.md`** — the 8 elements, formatting rules, and manager audit (Forecast QA gate).
- **`references/communication-frameworks.md`** — ARCV follow-ups, CBI, task formulation (why/what/how + DoD by D-level).
- **`references/roi-frameworks.md`** — ROAIP / PRO economics (money-based scoring, task-as-credit, Confidence).
- **`references/session-board.md`** — tactical-session structure + quarterly board-prep checklist.
- **`references/data-policy.md`** — new highest-sensitivity **People-data** tier (strictly local).

### Added — six People-contour skills

- **`goal-setter` (0.1.0)** — SMARTCBP/OKR formulation, 8-check audit, cascade, Tell-and-Sell commitment; writes goals to the profile.
- **`one-on-one` (0.1.0)** — prepare (agenda from profile + seven "how" questions + NVC drafts) / analyze (signals + ARCV follow-up + profile update) / coverage (headless). meeting-processor redirects 1-1s here.
- **`performance-review` (0.1.0)** — goals + GTD-index + Hersey-Blanchard diagnosis into the employer's review template; recommendation (development / style change / yellow card / promotion).
- **`hiring-designer` (0.1.0)** — role design (goal letter first) + universal vacancy profile mapped to the employer HR form + killer questions + goal×experience evaluation.
- **`offboarding-guide` (0.1.0)** — evidence-gated four-meeting algorithm, dismissal script + team message, strictly local.
- **`delegation-coach` (0.1.0)** — 7-levels-of-Appelo audit + S1→S4 hand-off plan + hiring/delegation ROI.

### Added — built-in templates

`goal-letter`, `report-3t5f`, `one-on-one-notes`, `followup-arcv`, `vacancy-profile`, `performance-review`, `offboarding-plan` under `templates/built-in/`.

### Changed — existing skills learn the frameworks

- **`meeting-processor` → 0.13.0** — ARCV follow-up standard (numbered actions, one responsible, verbs, separate Decisions block) + 1-1 detection → redirect to one-on-one.
- **`task-creator` → 0.10.0** — task-formulation gate (why/what/how + DoD + "how"-depth by D-level from the profile). Single-responsible rule intentionally NOT added (team-process conflict).
- **`brainstorm-features` → 0.9.0** — computes **ROI/PRO and ICE by default** (one only on explicit request) + "choose one" / "olympic" overload methods.
- **`requirements-creator` → 0.11.0** — ROI/ICE prioritization gate (Create Step 3e + Analyze A5) → offers brainstorm-features before finalizing.
- **`sprint-planning` → 0.3.0** — GTD-index (planned→done, written to the profile) + delegation-aware assignee fit.
- **`focus-advisor` → 0.4.0** — manager-rhythms signal from person profiles + "choose one" final daily filter + People-contour chains.
- **`quarterly-planning` → 0.3.0** — tactical-session structure + quarterly board-prep package (`references/session-board.md`).
- **`feedback-triage` → 0.2.0** — SH step: each priority pain → a well-formulated task (task-creator standard).
- **`experiment-tracker` → 0.2.0** and **`decision-log` → 0.2.0** — optional cost/ROI (ROAIP) + Tell-and-Sell commitment fields.
- **`plugin-configurator` → 2.7.0** — People setup add-on (roster, cadences, review template, HR-form field map, vault People area) + `people` context-schema section.
- **`template-library` → 0.2.0** — recognizes the seven People-contour artifact types.

### Files

| File | From | To | Change |
|------|------|----|--------|
| skills/team-ops-reporter/ → skills/product-reporter/ | 0.3.0 | 0.4.0 | **rename** + goal-report (3T5F) mode |
| skills/goal-setter/SKILL.md | — | 0.1.0 | new |
| skills/one-on-one/SKILL.md | — | 0.1.0 | new |
| skills/performance-review/SKILL.md | — | 0.1.0 | new |
| skills/hiring-designer/SKILL.md | — | 0.1.0 | new |
| skills/offboarding-guide/SKILL.md | — | 0.1.0 | new |
| skills/delegation-coach/SKILL.md | — | 0.1.0 | new |
| references/{people-context-protocol,goal-frameworks,people-frameworks,reporting-3t5f,communication-frameworks,roi-frameworks,session-board}.md | — | new | People-contour methodology |
| references/data-policy.md | — | — | People-data highest-sensitivity tier |
| skills/meeting-processor/SKILL.md | 0.12.0 | 0.13.0 | ARCV + 1-1 detection |
| skills/task-creator/SKILL.md | 0.9.0 | 0.10.0 | why/what/how + DoD + D-level depth |
| skills/brainstorm-features/SKILL.md | 0.8.0 | 0.9.0 | ROI/PRO + ICE by default |
| skills/requirements-creator/SKILL.md | 0.10.0 | 0.11.0 | ROI/ICE gate |
| skills/sprint-planning/SKILL.md | 0.2.0 | 0.3.0 | GTD-index + delegation-aware assignee |
| skills/focus-advisor/SKILL.md | 0.3.0 | 0.4.0 | manager-rhythms + choose-one |
| skills/quarterly-planning/SKILL.md | 0.2.1 | 0.3.0 | session/board prep |
| skills/feedback-triage/SKILL.md | 0.1.0 | 0.2.0 | SH step |
| skills/experiment-tracker/SKILL.md | 0.1.0 | 0.2.0 | cost/ROI + commitment |
| skills/decision-log/SKILL.md | 0.1.0 | 0.2.0 | cost/ROI + commitment |
| skills/plugin-configurator/{SKILL,references/onboarding-steps,references/context-schema}.md | 2.6.0 | 2.7.0 | People setup + people schema |
| skills/template-library/SKILL.md | 0.1.0 | 0.2.0 | People artifact types |
| templates/built-in/{goal-letter,report-3t5f,one-on-one-notes,followup-arcv,vacancy-profile,performance-review,offboarding-plan}/default-v1.md | — | new | People-contour templates |

### Backwards compatibility

The **only** breaking change is the `team-ops-reporter` → `product-reporter` rename (skill name + directory); update any external references to the old name. The People-contour is fully additive and inert until a `people` section / roster is configured. All existing skills keep their prior behavior; the new framework logic is additive.

---

## v1.40.0 (2026-07-10)

### Added — external design toolkit provider (integration + reference)

`design-bridge` becomes the single routing host for design/prototype work and can delegate hi-fi screen generation to an **external design toolkit** the user declares in `local-context.md` — keeping the plugin core universal for any company. Base logic stays the same when no toolkit is configured (zero regression); org-specifics live only in `local-context.md`.

- **New `references/design-toolkit-protocol.md`** — the contract: `design_toolkits[]` config schema, capability-based routing (core enum `hi-fi-prototype` / `screen-generation` / `ds-tokens` / `figma-write` / `code-first-research` / `design-review` + custom tags), a tier-0 fallback (provider → Figma MCP → Registry → Browser), four entry types (`skill` / `mcp_tool` / `command` / `browser`), a bidirectional delegation contract (feature/platform/requirements/jira → figma_url/branch/files), QA-ownership rule (no double review), data-locality policy, and protocol semver.
- **`design-bridge` → v0.3.0** — new **Step 0.5** (external toolkit routing): capability match → user-confirmed delegation → ingest returns → publish/link/vault. hi-fi prototype delegates to a covering toolkit, else falls back to the built-in Figma path. Added routing-host framing (other skills delegate design/prototype here), QA-ownership rule, vault `design_delivery` marker, description triggers (EN+UA), and new failure modes.
- **`plugin-configurator` → v2.6.0** — new **Design Toolkit setup** step (Extended add-on; standalone "register design toolkit" / "зареєструвати дизайн-тулкіт"). `references/context-schema.md` gains the `design_toolkits` schema + section format and a `design-toolkits` deferred-step key.
- **`references/integration-strategy.md`** — documents tier-0 (provider registry) ahead of the MCP→Registry→Browser chain, for design work only.
- **`references/vault-schema.md`** — `design_delivery` / `toolkit_id` / `toolkit_returns` markers on existing `prototype` / `handoff` types (no new artifact type).
- **`diagram-prototyper` → v0.9.1** — boundary note: hi-fi, design-system-native screen generation routes to `design-bridge`, not here.
- **`local-context.example.md`** — generic `design_toolkits` example (no concrete toolkit shipped).
- **Universality guard** — the plugin repository contains no reference to any concrete toolkit; every toolkit is user-declared in `local-context.md`.

### Files

| File | From | To | Change |
|------|------|----|--------|
| references/design-toolkit-protocol.md | — | new | provider contract: schema, capability routing, tier-0 fallback, entry types, delegation |
| skills/design-bridge/SKILL.md | 0.2.2 | 0.3.0 | minor — Step 0.5 routing host, returns, QA-ownership, triggers, failure modes |
| skills/plugin-configurator/SKILL.md + context-schema.md + onboarding-steps.md | 2.5.0 | 2.6.0 | minor — Design Toolkit registration step + schema + deferred-step key |
| references/integration-strategy.md | — | — | tier-0 provider registry (design only) |
| references/vault-schema.md | — | — | design_delivery / toolkit markers on prototype/handoff |
| skills/diagram-prototyper/SKILL.md | 0.9.0 | 0.9.1 | patch — scope-boundary note (hi-fi routes to design-bridge) |
| local-context.example.md | — | — | generic design_toolkits example |
| testing/trigger-evals.md | — | — | +B7/B8/B9 (design routing) |

### Backwards compatibility

Fully backwards compatible. The provider abstraction is inert when no `design_toolkits[]` is declared in `local-context.md` — design-bridge's built-in Figma path is unchanged. No breaking changes.

---

## v1.39.0 (2026-07-07)

### Added — harness engineering, wave 3: output evals (point 1)

The plugin could already verify *which* skill fires (`trigger-evals` = trajectory); it now verifies *how good the produced artifact is* (output eval). Following the whitepaper's split of output vs trajectory evaluation and "set the bar at the eval, not the demo."

- **`testing/output-evals.md`** (new) — artifact-quality test set: the trajectory/output split, an LM-judge method (weighted 0/1/2 per criterion, pass ≥ threshold, scored against the skill's golden exemplar), how-to-run, and rubrics. Full rubrics for `write-concept`, `requirements-creator`, `cjm-research` (data-integrity bar 0.85); lighter rubrics for `product-analysis`, `brainstorm-features`, `meeting-processor`, `task-creator`.
- **`testing/fixtures/`** (new) — runnable input briefs for the three exemplar skills (`write-concept`, `requirements-creator`, `cjm-research`), paired with the v1.37 golden exemplars as gold references. One shared "recently viewed / save-for-later" thread; the cjm-research fixture embeds an incomplete-period integrity trap.

### Changed

- **`testing/Testing-process.md`** — stage 3 split into **3a Trajectory / scenario walk** and **3b Output eval** (blocker for any changed artifact-producing skill); intro test definition updated. Output-eval ≥ threshold is now part of the DoD for releases touching artifact skills, the way trigger-evals gate description releases.

### Files

| File | Change |
|------|--------|
| testing/output-evals.md | new — rubrics + method + coverage map |
| testing/fixtures/{write-concept,requirements-creator,cjm-research}/brief-v1.md | new — output-eval input briefs |
| testing/Testing-process.md | stage 3a/3b split + DoD |

### Backwards compatibility

Fully backwards compatible. Testing infrastructure only — no runtime skill behaviour changes. No breaking changes.

---

## v1.38.0 (2026-07-07)

### Added — harness engineering, wave 2: artifacts carry their verification (point 4)

Verification is now baked into the spec/PRD, not bolted on afterward — following the whitepaper's "verification moves to the middle of the lifecycle" and "write the tests and evals before generating the code."

- **`requirements-creator` — Acceptance Criteria section** (`references/requirements-template.md`): a Given/When/Then table (AC-N) of testable, binary pass/fail conditions covering main flows + edge/error states — the contract QA and analytics verify against; also seeds Analytics Coverage and Test tasks.
- **`requirements-creator` — Decision Rule** for A/B tests: explicit ship / iterate / kill table tied to the success thresholds, stated before launch so the readout is a lookup, not a debate.
- **`write-concept` — Verification & decision rule** block added to Success Metrics (`references/prd-structure.md`): how each metric is verified (eval/dashboard/test), a Definition of Done checklist, and an experiment decision rule. Acceptance criteria in User Stories upgraded from a flat checklist to a Given/When/Then table.

### Changed

- `requirements-creator` SKILL.md — Step 4 section tables gain the Acceptance Criteria and Decision rule rows (kept in sync with the template).

### Files

| File | From | To | Change |
|------|------|----|--------|
| skills/requirements-creator/SKILL.md + requirements-template.md | 0.9.0 | 0.10.0 | minor — Acceptance Criteria section + A/B Decision Rule |
| skills/write-concept/SKILL.md + prd-structure.md | 0.8.0 | 0.9.0 | minor — Verification & decision rule block + Given/When/Then acceptance |

### Backwards compatibility

Fully backwards compatible. New/enhanced template sections are additive; existing documents and workflows are unaffected. No breaking changes.

---

## v1.37.0 (2026-07-07)

### Added — harness engineering, wave 1 (from Google/Kaggle "The New SDLC With Vibe Coding")

- **`references/harness-map.md`** (new) — anatomy of the plugin's harness across the paper's six layers (instructions / tools / sandboxes / orchestration / guardrails / observability) plus a six-context-type coverage map (instructions / knowledge / memory / examples / tools / guardrails). Names the current thin spots: **Examples** and the output-eval half of Observability. Canonical answer to "what is our harness, and where is it thin."
- **Golden exemplars (few-shot Examples context type)** for the three heaviest artifact skills, loaded on demand and doubling as fixtures for the planned `testing/output-evals.md`:
  - `skills/write-concept/references/examples/prd-example-v1.md` — worked PRD with measurable Success Metrics + a Verification/decision-rule block.
  - `skills/requirements-creator/references/examples/feature-spec-example-v1.md` — feature-spec with an A/B variant, testable Acceptance Criteria, and an explicit ship/kill decision rule.
  - `skills/cjm-research/references/examples/funnel-anomaly-report-example-v1.md` — anomaly report demonstrating period annotation on every metric, Data Integrity caveats, and funnel-impact math.
  - All exemplars are generic/anonymized (no org-specific data); a single "save-for-later" thread runs across them to show the concept → requirements → CJM pipeline.

### Changed

- **`references/self-improvement.md`** — Step 2 (root-cause analysis) gains a **harness-first diagnosis** sub-step: classify the failure by harness layer and route the fix (SKILL wording / integration-strategy / local-context / a gate / delegation / an output-eval) before proposing a change. Links to `harness-map.md`.
- `write-concept`, `requirements-creator`, `cjm-research` SKILL.md — on-demand pointer to their golden exemplar in the drafting/report-assembly step + Additional Resources.

### Files

| File | From | To | Change |
|------|------|----|--------|
| references/harness-map.md | — | new | harness anatomy + 6-context-type coverage map |
| references/self-improvement.md | — | — | harness-first diagnosis sub-step (reference, unversioned) |
| skills/write-concept/SKILL.md | 0.7.0 | 0.8.0 | minor — on-demand golden PRD exemplar |
| skills/requirements-creator/SKILL.md | 0.8.0 | 0.9.0 | minor — on-demand golden feature-spec exemplar |
| skills/cjm-research/SKILL.md | 0.6.0 | 0.7.0 | minor — on-demand golden anomaly-report exemplar |

### Backwards compatibility

Fully backwards compatible. All additions are on-demand references (progressive disclosure) — no change to existing workflows, gates, or outputs. No breaking changes.

---

## v1.36.0 (2026-07-04)

### Added — wave 3 kickoff: three lifecycle skills (21 → 23 skills)

All three ship thin-core from day one (planning-suite pattern, 110–170 lines each, no skill-local references needed yet).

**`experiment-tracker` 0.1.0** — closes the audit's "pipeline drops after the A/B spec" gap. Persistent registry `~/.grow-pm/experiments/registry.yaml` (+ vault mirror `_System/experiments-registry.yaml`) with lifecycle `proposed → specced → running → awaiting-readout → decided`; 6 modes (status board / register / start / readout / decide / stale); stale detection (overdue runs, pending readouts > 3d, idle high-ICE hypotheses > 30d, unscheduled extensions); weekly headless stale-check via `schedule`. Guardrails: verdicts only via product-analysis A/B mode (Data Integrity Gate included); decisions recorded via decision-log; every transition dated and gated.

**`decision-log` 0.1.0** — ADR-style records in vault `Decisions/` (existing `decision` type; L0 fallback `~/.grow-pm/decisions/`): context, ≥2 options considered, decision, rationale with evidence links, consequences. Modes: log (default, also chained from meeting-processor M10 / experiment-tracker decide / planning retro-replan), search ("чому ми вирішили X" — Rationale is the answer), revisit (supersede-flow: history marked, never rewritten).

**`feedback-triage` 0.1.0** — feedback stream → ranked pain map: multi-source intake (files / GDrive / Confluence / pasted, subagent fan-out returning normalized rows), Python normalize with coverage gate (data-integrity applies to trend claims), semantic clustering (language-agnostic, `other` bucket < 15%), `pain_score = frequency × severity × trend`, new/growing/declining themes vs the previous run's vault baseline, hypothesis seeds → brainstorm-features. PII masked; feedback text never leaves the session.

### Changed

- `references/vault-schema.md`: Type Taxonomy 21 → 22 (`feedback-triage` → Research/feedback/) + extended frontmatter block.
- `testing/trigger-evals.md`: Group H (14 phrases — lifecycle trio vs product-analysis / requirements-creator / meeting-processor / product-research / knowledge-library / brainstorm-features).
- README: sections 21–23, Skills Summary 23 rows, "New in v1.36.0"; both manifests → 1.36.0.

### Backwards compatibility
Additive only — three new skills, no changes to existing skill logic. Safe for Claude.

---

## v1.35.0 (2026-07-03)

### Changed — monolith refactor complete (2–4/4): product-analysis, cjm-research, knowledge-library

Closes audit section 3.1. Same recipe as v1.34.0: full read → sed extraction by line ranges (zero loss) → anchor verification → thin core. **No logic change** — all content relocated verbatim; cross-mode guards (Data Integrity Gate, Vault Mirror Sync, service contracts) stay in the cores.

| Skill | Core | New skill-local references | Version |
|---|---|---|---|
| product-analysis | 968 → 364 | `analysis-engine.md` (261: data acquisition 1e + Steps 2–6), `specialized-modes.md` (361: CJM / Post-Release / A/B modes) | 0.11.1 → 0.12.0 |
| cjm-research | 788 → 393 | `cjm-pipeline.md` (234: Steps 4–11), `cjm-reports.md` (181: per-mode formats + publishing + automated health-check) | 0.5.1 → 0.6.0 |
| knowledge-library | 751 → 252 | `library-workflows.md` (354: eight mode workflows), `trust-and-categories.md` (162: trust formula + taxonomy + KL onboarding) | 0.5.0 → 0.6.0 |

Kept in cores by design: product-analysis Step 1.5 Data Integrity Gate + Vault Save + return-payload contract; cjm-research Steps 1–3.5 (init, scope, data load, gate) + Step 12 + chaining; knowledge-library storage model + mode map + cross-skill service contract + Vault Mirror Sync.

Audit KPI closed: the top-4 monoliths were 3 838 lines (47 % of the plugin); cores now total ~1 188 — **-69 %** in always-loaded context, with per-mode references loaded on demand.

### Files

3 × SKILL.md (versions above), 6 new skill-local reference files, both manifests → 1.35.0, README (headers, Skills Summary, "New in v1.35.0").

### Backwards compatibility
Content relocation only; every mode reads the same instructions from a new location. Trigger descriptions untouched — the v1.34.0 evals baseline holds. Safe for Claude.

---

## v1.34.0 (2026-07-03)

### Changed — plugin-configurator refactor (monolith 1/4): 1345 → ~180-line core

First of four monolith refactors from the 2026-07-02 audit (section 3.1), following the planning-suite pattern: thin SKILL.md + on-demand skill-local references. **All content preserved verbatim** (extracted by line ranges, anchors verified); no logic change.

| File | Contents | Lines |
|---|---|---|
| `skills/plugin-configurator/SKILL.md` | mode map, entry conditions, Auto-trigger / Changelog / Product-selection / Enrichment protocols (read by other skills — kept in core), quality standards | ~180 |
| `skills/plugin-configurator/references/onboarding-steps.md` (new) | Onboarding Steps 1–17 in full + Planning setup + Focus setup (Extended add-ons) | ~740 |
| `skills/plugin-configurator/references/maintenance-modes.md` (new) | Reinstall/Migration RM-0..RM-6, Update U-1..U-4, Validate V-1..V-6, View VW-1..VW-4, Versioning Protocol | ~455 |

Also fixed en route: Planning/Focus setup steps were dangling after Additional Resources (outside the workflow) — now integrated into the onboarding reference; removed a leftover `<!-- Додай як новий крок… -->` editorial artifact (pitfall P3); README section 10 version was stale (v2.3.1 while frontmatter was 2.4.2) — synced.

Context economy: entering any single mode now loads ~180 + one reference instead of 1345 lines (~-55% for the largest mode, ~-85% for View/Validate).

- `skills/plugin-configurator/SKILL.md`: **2.4.2 → 2.5.0** (MINOR — structural reorganization, no behavior change).

### Added — trigger-evals baseline (first run)

Two independent description-only routing simulations on v1.33.0, 46 phrases: groups A–F **100%**, G 95% → one eval-label fix (G8 was mislabeled cjm-research for a data-only phrase; expected column corrected to product-analysis). 46/46 primary agreement between runs. Results log filled — baseline recorded before the remaining monolith refactors.

### Backwards compatibility
Content relocation + docs sync only. Every mode reads the same instructions from a new location. Safe for Claude.

---

## v1.33.0 (2026-07-03)

### Added — focus-advisor 0.2.0 → 0.3.0: `strategy` mode + live "PM Focus Board"

Third and final horizon of the attention dispatcher (quarter – year) + a persistent attention panel; completes the focus-advisor design file (phase 3).

- **Strategic collectors** (`references/focus-signals.md` §7, registry table): product goals/missions from a pinned source (`Focus → Goals source`), NPS waves + love/hate themes in the PM's zones, CJM/funnel trends (freshness-guarded), knowledge-library research signals (trust-weighted), leadership-meeting mandates (Fireflies scan), competitive moves (chained product-research), white spaces (zones without active investment).
- **Strategic scoring** (`focus-scoring.md` §5) — goal/mission alignment × lever size × evidence strength → 2–4 bets.
- **Strategy memo** — subtype `strategy-memo`: current state (facts with sources) → bets (what/why/expected effect/first steps) → mandatory **"what we deliberately do NOT do"** → data-hygiene preconditions → next 2 weeks.
- **New chains:** bet needs evidence → product-research / cjm-research / knowledge-library; bet accepted → write-concept → quarterly-/project-planning; goals source stale → knowledge-library refresh + config update.
- **Mode `board` — live "PM Focus Board"** (Step 7b): one-glance panel — current focuses with journal status, due rituals, signal freshness, radar backlog, chain shortcuts. On platforms with live artifacts: dynamic parts re-query connector MCPs on open, local data baked at render, artifact id kept in `~/.grow-pm/focus/board.yaml` (update, not recreate). Fallback: static `~/.grow-pm/focus/board.html`. Board is a view — journal remains the source of truth.
- **Headless** extended to `mode=strategy` (quarterly memo); `auto` now routes all three horizons by phrasing + quarter-boundary nudge.

### Changed

| File | Change | Version |
|---|---|---|
| `skills/focus-advisor/SKILL.md` | strategy + board modes: description, Modes, Steps 1/2/4/5, Step 7b, chain map, headless | 0.2.0 → 0.3.0 |
| `references/focus-signals.md` | §7 strategic collectors registry table; Focus config: Goals source + quarterly strategy memo | n/a |
| `references/focus-scoring.md` | §4/§5 version markers dropped (both live) | n/a |
| `skills/plugin-configurator/SKILL.md` | Focus setup: Goals source capture (Step 3), quarterly strategy memo (Step 5) | 2.4.1 → 2.4.2 |
| `skills/plugin-configurator/references/context-schema.md`, `local-context.example.md` | Focus: goals_source + strategy_memo scheduled entry | n/a |
| both manifests, `README.md` | version sync, New in v1.33.0 | 1.33.0 |

Backwards compatible: `now`/`tactics`/`journal`/headless behavior unchanged. The focus-advisor concept (design file) is now fully shipped: all three horizons + board.

---

## v1.32.0 (2026-07-03)

### Added — focus-advisor 0.1.0 → 0.2.0: `tactics` mode

Second horizon of the attention dispatcher (sprint – quarter), per the focus-advisor design file (phase 2):

- **Tactical collectors** (`references/focus-signals.md` §6, now a full registry table): roadmap plan-vs-actual pace + per-epic stagnation (CQL by quarter label + per-key statuses), roadmap drift vs capacity ceiling, backlog staleness (ICE age from vault Hypotheses/), features missing prerequisites ahead of next 1–2 sprints (work-type DAG), A/B tests past end date without a recorded decision, capacity/availability (vacations, booking deadlines), team events (perf reviews, vacancies, onboarding).
- **Tactical scoring** — ICE (reused from brainstorm-features) + capacity realism + goal alignment (`focus-scoring.md` §4); 3–5 candidates per brief.
- **Tactical brief** — subtype `tactical-brief`: adds quarter position (sprints left, capacity vs plan) and a "decisions waiting on you" section.
- **New chains:** roadmap drift → project-planning `replan`; A/B decision → product-analysis (test readout); team event → task/reminder + team-ops-reporter `member-review`.
- **Headless** extended to `mode=tactics` (weekly tactical brief); `tactical_brief` added to the Focus scheduled config (example, schema, configurator Step 5).

### Changed

| File | Change | Version |
|---|---|---|
| `skills/focus-advisor/SKILL.md` | tactics mode: description, Modes, Steps 2/4/5, chain map, headless | 0.1.0 → 0.2.0 |
| `references/focus-signals.md` | §6 tactical collectors registry table + scheduled config | n/a |
| `skills/plugin-configurator/SKILL.md` | Focus setup Step 5: daily + weekly tactical scheduled briefs | 2.4.0 → 2.4.1 |
| `skills/plugin-configurator/references/context-schema.md`, `local-context.example.md` | Focus → Scheduled: tactical brief entry | n/a |
| both manifests, `README.md` | version sync, New in v1.32.0 | 1.32.0 |

Backwards compatible: `now`/`journal`/headless behavior unchanged; `strategy` still routes to the closest chain (v1.33).

---

## v1.31.0 (2026-07-03)

### Added — new skill: focus-advisor 0.1.0 (20th skill)

PM attention dispatcher — the 4th height of the suite, above structure/quarter/sprint. Collects context signals, ranks them, recommends 1–3 focuses, and chains execution to the right skill; the PM decides. Design file: workspace `skill-design — focus-advisor.md` (decisions fixed 2026-07-03).

**v0.1 scope (MVP):** mode `now` (daily/weekly focus) + `journal` + `auto`, headless contract for scheduled morning briefs (no side-effect actions, mandatory file output). Modes `tactics`/`strategy` — declared, respond with the closest chain until v1.32/v1.33.

**Mechanics:** deterministic ritual cadence ("2nd Monday of the sprint → pre-planning"), mail collector with two-stage "live letters" filter (7-day window, automation never becomes a signal, 24h/48h thresholds, VIP list), meeting-prep detector (analytical slice / deck / talking-points chains), optional metrics health-check chain to product-analysis / cjm-research with source-freshness guard, journal dedup with snooze, mandatory persistence to `~/.grow-pm/focus/` + Vault mirror.

### Added — shared references (root)

| File | Purpose |
|---|---|
| `references/focus-cadence.md` | Cycle position math + default ritual table + overrides + resolution |
| `references/focus-signals.md` | Signal registry per horizon, packet format, cache TTL, mail/calendar detectors, Focus config format |
| `references/focus-scoring.md` | Ranking (urgency+impact+unblock), journal dedup, honesty rules; tactics/strategy scoring stubs |

### Changed — integrations

| File | Change | Version |
|---|---|---|
| `references/vault-schema.md` | +`focus-brief` type (21st): taxonomy row, extended frontmatter, folder `Focus/`; TYPE_FOLDER_MAP backfilled with v1.29 types (diagram, task-breakdown, ops-report, roadmap); stale counts fixed (16/20 → 21) | n/a |
| `skills/plugin-configurator/SKILL.md` | new Step — Focus setup (Extended): sources, VIP senders (prefill from stakeholders), PM goals (prefill from OKRs/missions), cadence overrides, scheduled brief | 2.3.1 → 2.4.0 |
| `skills/plugin-configurator/references/context-schema.md` | Focus Configuration section format + Focus Advisor row in "Which Skills Read What" | n/a |
| `testing/trigger-evals.md` | Group G — attention vs execution (10 phrases: focus-advisor vs sprint-planning vs cjm-research) | n/a |
| both manifests, `README.md` | version sync, skill #20 section + summary row | 1.31.0 |

---

## v1.30.0 (2026-07-03)

### Changed — roadmap-trio disambiguation (audit 3.4, remaining group)

Scope hints added to the last known trigger-collision group:

| Skill | Hint | Version |
|---|---|---|
| roadmap-architect | structure/labeling only, no dates/capacity → quarterly-planning / project-planning | 0.2.0 → 0.2.1 |
| project-planning | horizon beyond one quarter → quarterly-planning for a single quarter, roadmap-architect for structure | 0.2.0 → 0.2.1 |
| quarterly-planning | scope = exactly one quarter → project-planning / roadmap-architect / sprint-planning | 0.2.0 → 0.2.1 |

### Added — testing/trigger-evals.md

36-phrase routing test set across 6 collision groups (CJM trio, prototype pair, roadmap trio + sprint, release semantics, research vs analysis vs knowledge, documents chain), with a manual run protocol, a skill-creator eval-harness option, ≥90 % per-group target, results log, and maintenance rules. Part of the definition-of-done for any description-touching release.

### Fixed — release-manager 0.1.0 → 0.1.1 (self-improvement)

Step 6 now carries an explicit "merging ≠ releasing" guard: a merged PR does not create the tag/Release — verify `releases/latest` after merge. Sourced from two live observations during v1.28.0–v1.29.0.

### Files

| File | Type | Version |
|---|---|---|
| `skills/roadmap-architect/SKILL.md` | description hint | 0.2.1 |
| `skills/project-planning/SKILL.md` | description hint | 0.2.1 |
| `skills/quarterly-planning/SKILL.md` | description hint | 0.2.1 |
| `skills/release-manager/SKILL.md` | Step 6 guard | 0.1.1 |
| `testing/trigger-evals.md` | new test set | n/a |
| both manifests, `README.md` | version sync | 1.30.0 |

### Backwards compatibility
Description wording + new testing asset + one guard note. No workflow change. Safe for Claude.

---

## v1.29.0 (2026-07-03)

### Added — Step V (Save to Vault) in the 11 skills that never wrote to the vault

Closes the biggest gap from the 2026-07-02 audit (section 3.2): only 7 of 18 skills honored architecture principle #5 (vault mirror). Meeting MoMs, requirements, hypotheses, research, diagrams, task breakdowns, ops reports, and roadmaps now accumulate in the Obsidian knowledge graph with wikilinks. Vault remains optional — at L0 every new step skips silently (`IF vault_level > L0 AND sync_mode != "off"`), exactly per `references/vault-protocol.md` → Vault Save.

| Skill | New step | Vault type → folder | Version |
|---|---|---|---|
| requirements-creator | Step 9 (+ A-mode note) | `requirements` → Requirements/ | 0.7.0 → 0.8.0 |
| meeting-processor | M10 | `meeting-notes` → Meetings/ (+ optional `decision`) | 0.11.0 → 0.12.0 |
| brainstorm-features | Step 9 | `hypothesis` → Hypotheses/ (one per finalized hypothesis) | 0.7.1 → 0.8.0 |
| product-research | Step 7 | `competitive-analysis` / `market-research` / `ux-benchmark` → Research/ | 0.9.0 → 0.10.0 |
| diagram-prototyper | Step 10 | `diagram` → Diagrams/ **(new type)** | 0.8.1 → 0.9.0 |
| task-creator | Step 14 | `task-breakdown` → Projects/task-breakdowns/ **(new type)** | 0.8.0 → 0.9.0 |
| team-ops-reporter | Step 8 | `ops-report` → Reports/ops/ **(new type)** | 0.2.1 → 0.3.0 |
| sprint-planning | Step 9 | `roadmap` (subtype sprint-plan) → Roadmaps/ **(new type)** | 0.1.2 → 0.2.0 |
| quarterly-planning | Step 7 | `roadmap` (subtype quarterly/retro) → Roadmaps/ | 0.1.2 → 0.2.0 |
| project-planning | Step 7 | `roadmap` (subtype project-arc; baseline for `replan` drift) → Roadmaps/ | 0.1.2 → 0.2.0 |
| roadmap-architect | Step 6 | `roadmap` (subtype structure-tree) → Roadmaps/ | 0.1.2 → 0.2.0 |

### Changed — vault-schema.md: Type Taxonomy 16 → 20 types

New rows: `diagram` (Diagrams/), `task-breakdown` (Projects/task-breakdowns/), `ops-report` (Reports/ops/), `roadmap` (Roadmaps/, subtype in frontmatter).

### Files

11 × `skills/*/SKILL.md` (versions above), `references/vault-schema.md`, both manifests → 1.29.0, `README.md` (headers, Skills Summary, "New in v1.29.0").

### Backwards compatibility
New optional steps only; every one is a no-op at vault L0. No workflow change for users without a vault. Safe for Claude.

---

## v1.28.0 (2026-07-03)

### Added — release-manager skill (v0.1.0)

New skill: releases the plugin repository itself — one guided pipeline from "changes are ready" to "both remotes tagged, Release published, docs consistent". Every irreversible step (commit, push, merge, publish) is user-gated; Claude prepares, the user's terminal/browser session executes.

**Pipeline (8 steps):** Step 0 local-context (`plugin_release` config: repo path, canonical + mirror remotes, VPN hosts, protected branches, optional Confluence changelog page) → pre-flight guards → scope & semver decision (gate) → bump in the 4 mandatory places → local `validate-consistency.sh` run → gated commit/push terminal block → PR → merge → GitHub Release with tag (canonical remote only) → mirror sync → post-release verification + optional Confluence update + vault release record (Step V).

**`skills/release-manager/references/release-pitfalls.md`** — nine documented failure modes with guards and recovery recipes, all encountered for real during v1.26.1–v1.27.0:

| # | Pitfall |
|---|---|
| P1 | iCloud-evicted files break git (EDEADLK, packfile timeout) → `brctl download` + materialization sweep |
| P2 | Stale git lock files → delete only if >60 min old |
| P3 | Editorial placeholders shipped in CHANGELOG → write final text; validator guards `^<!-- Препенди` |
| P4 | GitHub token without `workflow` scope → fine-grained PAT with Contents + Workflows |
| P5 | Mirror host requires VPN → `vpn_required_hosts` reminder; push retryable |
| P6 | Mirror main diverged / protected → merge on canonical only; reconciliation-merge recipe, never force |
| P7 | Stale raw.githubusercontent CDN → verify via releases/latest, not raw URLs |
| P8 | GitHub editor auto-continues lists → set textarea value directly when automating |
| P9 | Fresh terminal ≠ repo dir → every terminal block starts with `cd <repo>` |

Design notes: generic for any Claude plugin repo (no hardcoded org specifics); version read/written only via structured `"version"` fields; explicit `git add` lists, never `-A`; trigger description carries a "Do NOT use" hint (Jira feature releases → team-ops-reporter / sprint-planning).

### Files

| File | Type | Version |
|---|---|---|
| `skills/release-manager/SKILL.md` | new skill | 0.1.0 |
| `skills/release-manager/references/release-pitfalls.md` | new reference | n/a |
| `.claude-plugin/plugin.json` | version + description | 1.28.0 |
| `.claude-plugin/marketplace.json` | version + descriptions | 1.28.0 |
| `README.md` | section 19, Skills Summary row, "New in v1.28.0" | n/a |

### Backwards compatibility
Additive only — new skill, no changes to existing skills. Safe for Claude.

---

## v1.27.0 (2026-07-02)

### Added — CI validation (GitHub Actions)

- **`.github/workflows/validate.yml`** — runs on every push/PR to main.
- **`testing/validate-consistency.sh`** (also runnable locally) checks:
  1. plugin version identical in `plugin.json` = `marketplace.json` = README header/footer = top CHANGELOG entry, and mentioned in both manifest description tails;
  2. every `skills/*/SKILL.md` has `name` / semver `version` / `description` frontmatter;
  3. no leftover editorial artifacts in CHANGELOG;
  4. every `references/*.md` path mentioned in skills exists;
  5. the pre-v1.26.1 location of jira-data-protocol.md does not reappear.

This makes the v1.26.1 hygiene guarantees permanent — the class of drift documented in the 2026-07-02 audit can no longer land on main unnoticed.

### Changed — trigger disambiguation in skill descriptions

Explicit "Do NOT use / use X instead" routing hints added to the descriptions of the two known trigger-collision groups (audit 2026-07-02, section 3.4):

| Group | Skill | Routing hint added | Version |
|---|---|---|---|
| CJM trio | `cjm-research` | not for standalone dashboard analysis (→ product-analysis) or pure ideation (→ brainstorm-features) | 0.5.0 → 0.5.1 |
| CJM trio | `product-analysis` | data analysis only; end-to-end CJM pipeline → cjm-research | 0.11.0 → 0.11.1 |
| CJM trio | `brainstorm-features` | ideation engine; full CJM pipeline → cjm-research | 0.7.0 → 0.7.1 |
| Prototype pair | `diagram-prototyper` | not for brand-themed DS deliverables → design-bridge | 0.8.0 → 0.8.1 |
| Prototype pair | `design-bridge` | not for quick local diagrams/Mermaid → diagram-prototyper | 0.2.1 → 0.2.2 |

README section headers and Skills Summary synced to the new versions; added "New in v1.27.0" overview paragraph.

### Backwards compatibility
Description wording + new CI infrastructure only; no workflow change inside any skill. Safe for Claude.

---

## v1.26.1 (2026-07-02)

### Fixed — release hygiene: machine-readable version, README catch-up, shared jira-data-protocol

Documentation and manifest release; **no skill-logic change**.

**Manifests — structured `version` field (root cause of the marketplace version-sync issue):**
- `.claude-plugin/plugin.json`: added `"version": "1.26.1"` — previously the version existed only as free text inside `description`, so tooling (and the release process itself) could not read it mechanically. Description tail updated; planning suite mentioned.
- `.claude-plugin/marketplace.json`: added `"version": "1.26.1"` to the plugin entry; descriptions updated.

**README.md regenerated to match the actual plugin state:**
- Version header/footer: 1.25.1 → 1.26.1 (footer previously drifted).
- Added skill sections 15–18 for the Planning Suite (roadmap-architect, project-planning, quarterly-planning, sprint-planning) — previously a dangling Ukrainian block after the footer; removed that block.
- Skills Summary table: now 18 rows with actual frontmatter versions (was 14 rows with stale versions, e.g. Plugin Configurator v1.0.0 → v2.3.1).
- Section headers synced to frontmatter versions (CJM Research 0.5.0, Product Analysis 0.11.0, Product Research 0.9.0, Meeting Processor 0.11.0, Knowledge Library 0.5.0, Design Bridge 0.2.1, Team Ops Reporter 0.2.1).
- Built-in templates: 12 → 17 (added the 5 `ops-report/` templates from v1.14.0).
- Shared References: full actual list of 18 root reference files (was a partial mix of real and placeholder bullets).
- Added "New in v1.26.0" and "New in v1.15.0" overview paragraphs.

**CHANGELOG.md:** removed 3 leftover editorial prepend-instructions (`<!-- Препенди… -->`) that shipped by mistake.

**Moved — `jira-data-protocol.md` to root `references/`:**
- `skills/team-ops-reporter/references/jira-data-protocol.md` → `references/jira-data-protocol.md`. It is shared by 5 skills (team-ops-reporter + the 4 Planning Suite skills), so it belongs with the other cross-skill protocols. Title updated to "(shared)".
- Path references updated in: `sprint-planning`, `quarterly-planning`, `project-planning`, `roadmap-architect` (each **0.1.1 → 0.1.2**). `team-ops-reporter` **0.2.0 → 0.2.1** (its `references/jira-data-protocol.md` mentions now resolve to the root file; no text change needed).

### Files

| File | Type | Version |
|---|---|---|
| `.claude-plugin/plugin.json` | modified (added `version` field) | 1.26.1 |
| `.claude-plugin/marketplace.json` | modified (added `version` field) | 1.26.1 |
| `README.md` | regenerated | n/a |
| `CHANGELOG.md` | cleanup (3 leftover comments) | n/a |
| `references/jira-data-protocol.md` | moved from `skills/team-ops-reporter/references/` | n/a |
| `skills/sprint-planning/SKILL.md` | modified (paths) | 0.1.1 → 0.1.2 |
| `skills/quarterly-planning/SKILL.md` | modified (paths) | 0.1.1 → 0.1.2 |
| `skills/project-planning/SKILL.md` | modified (paths) | 0.1.1 → 0.1.2 |
| `skills/roadmap-architect/SKILL.md` | modified (paths) | 0.1.1 → 0.1.2 |
| `skills/team-ops-reporter/SKILL.md` | modified (version only) | 0.2.0 → 0.2.1 |

### Backwards compatibility
Docs + manifest metadata + file relocation with all in-repo paths updated. No workflow change. Safe for Claude.

---

## v1.26.0 (2026-07-01)

### Added — product-analysis: subagent delegation in Post-Release, A/B, and CJM modes

`product-analysis` already delegated the main data-acquisition fan-out (Step 1) to subagents per `references/subagent-delegation.md`. The three specialized modes did comparable fan-out work but had no explicit delegation callout. This release closes that gap.

Added a subagent-delegation callout to:

| Mode | Step | Batch by | Subagent returns |
|---|---|---|---|
| Post-Release Analysis | PR-2 (Gather metrics data) | metric group / platform | per metric: before value, after value, period, platform, source-type marker + link |
| A/B Test Results | AB-2 (Gather test results data) | segment / dimension | per segment: primary + secondary metric values per group, sample size, significance, source-type marker + link |
| CJM Funnel Analysis | CJM-3 (Load funnel data) | stage (or stage × platform) | per stage: conversion, absolute users, drop-off, trend, segment data, source-type marker + link |

Guardrails preserved in every callout: `data-policy.md` applies to subagents (internal data stays internal), the main agent aggregates and still runs the **Step 1.5 Data Integrity Gate** before analysis, and each mode falls back to inline execution when subagents are unavailable. CJM-3 additionally honors any batch/parallelism limits passed by `cjm-research`.

**No logic change** — the same data is gathered, just off the main context for efficiency. Output formats of all modes are unchanged.

- `skills/product-analysis/SKILL.md`: **0.10.0 → 0.11.0** (frontmatter + Vault Save `skill_version`).

---

## v1.25.1 (2026-06-30)

### Fixed — plugin-configurator refactor (pass 3): substep-numbering cleanup

Closes the item deferred from v1.25.0. Documentation-only; **no behavior change** (substep labels are navigation aids, not logic).

Substep prefixes in `skills/plugin-configurator/SKILL.md` now match their parent Step:

| Step | Was | Now |
|---|---|---|
| Step 5 — Organizations | 3a, 3b | 5a, 5b |
| Step 6 — Products | 4a, 4b | 6a, 6b |
| Step 7 — Analytics & Data Sources | 5a, 5a-Tableau, 5b, 5c | 7a, 7a-Tableau, 7b, 7c |
| Step 8 — Key Metrics & OKRs | 6a, 6b, 6c | 8a, 8b, 8c |
| Step 9 — Teams | 7a, 7b | 9a, 9b |
| Step 11 — CJM Configuration | 9a–9f | 11a–11f |
| Step 16 — Review & save | 13a–13g | 16a–16g |

- Cross-reference "added Tableau in Step 5a" updated to "Step 7a".
- Left unchanged on purpose: the RM-4 (Resume Mode) `4a–4e` block (correctly scoped to RM-4); the "Onboarding Step 3a" reference (Step 3 connector pre-check, still 3a); the "Step 13" mention inside 16g (refers to the Template Library step, still Step 13).
- `plugin-configurator` `2.3.0 → 2.3.1` (PATCH).

This eliminated the ambiguity that blocked an automated pass earlier (`3a` existed in both Step 3 and Step 5; `4a` in both RM-4 and Step 6) — resolved with section-scoped, full-line literal replacements.

### Files

| File | Type | Version |
|---|---|---|
| `skills/plugin-configurator/SKILL.md` | modified (substep prefixes + 1 cross-ref) | 2.3.0 → 2.3.1 |
| `README.md` | version bump 1.25.1 | n/a |

### Backwards compatibility
Cosmetic relabeling only — no behavior change. Safe for Claude.

## v1.25.0 (2026-06-30)

### Changed — plugin-configurator refactor (pass 2)

Second slimming pass on the configurator. Behavior unchanged.

- Extracted 3 self-contained `local-context.md` format/schema blocks — **CJM Configuration**, **Knowledge Library Configuration**, **Obsidian Vaults Configuration** — from `skills/plugin-configurator/SKILL.md` into `skills/plugin-configurator/references/context-schema.md` (verbatim, under a new "local-context.md Section Formats" heading). The skill now points to them (bold lead-in preserved for discoverability).
- `plugin-configurator` `2.2.0 → 2.3.0` (MINOR). SKILL.md ≈ −69 lines (≈ −150 across passes 1+2).

**Deferred to pass 3:** substep-numbering cleanup (Step 5/6/7/8/9/11/16 carry mislabeled `3a/4a/…` substeps). Not done here because of ambiguous duplicate labels (`3a` exists in both Step 3 and Step 5) and live cross-references to the old labels — unsafe for literal replacement; needs a dedicated coordinated pass.

### Files

| File | Type | Version |
|---|---|---|
| `skills/plugin-configurator/references/context-schema.md` | modified (+3 format blocks) | n/a |
| `skills/plugin-configurator/SKILL.md` | modified (3 blocks → pointers) | 2.2.0 → 2.3.0 |
| `README.md` | version bump 1.25.0 | n/a |

### Backwards compatibility
Refactor only — no behavior change (formats reachable via context-schema.md). Safe for Claude.

## v1.24.0 (2026-06-30)

### Changed — plugin-configurator refactor (pass 1)

First conservative slimming pass on the plugin's largest skill (≈1459 lines), following the team-ops-reporter "thin skill + thick reference" pattern. Behavior unchanged.

- Extracted the **Test Mode (sandbox)** workflow (≈83 lines: TM-0..TM-5, sandbox isolation rules, finale diff, Discard/Promote/Keep menu, verification matrix) from `skills/plugin-configurator/SKILL.md` into **`references/test-mode.md`** (NEW); the skill now keeps the section heading + triggers and points to the reference. Content moved verbatim — every TM step/rule/table preserved.
- Removed a **duplicate "Test (sandbox)" row** from the modes table (kept the `Onboarding (Test sandbox)` row, which is grouped with the other onboarding variants and referenced by Onboarding Step 2).
- `plugin-configurator` `2.1.0 → 2.2.0` (MINOR). SKILL.md ≈ −81 lines.

Deferred to later passes: extracting format/schema blocks into `context-schema.md`, and the broader substep-numbering cleanup (kept out of this pass to stay safe).

### Changed — release convention
- The plugin **Description** (`.claude-plugin/plugin.json` + `marketplace.json`) is now stamped with the version and release date on every release — suffix ` — v{version} (released {date})` (idempotent: the previous stamp is replaced).

### Files

| File | Type | Version |
|---|---|---|
| `.claude-plugin/plugin.json` + `marketplace.json` | description stamped (v1.24.0 + date) | n/a |
| `references/test-mode.md` | NEW (extracted) | n/a |
| `skills/plugin-configurator/SKILL.md` | modified (Test Mode → pointer, dup row removed) | 2.1.0 → 2.2.0 |
| `README.md` | version bump 1.24.0 | n/a |

### Backwards compatibility
Refactor only — no behavior change (Test Mode triggers and full procedure remain reachable via the reference). Safe for Claude.

## v1.23.0 (2026-06-30)

### Added — subagent delegation for research / analytics skills

Extends v1.22's fan-out delegation to the heaviest research/analytics passes. Same shared pattern (`references/subagent-delegation.md`), now applied where many sources / competitors / dashboards are read in parallel.

- **`skills/product-research/SKILL.md`** `0.8.0 → 0.9.0` — "Gather data" step: delegate per-competitor / per-source-group reads, aggregate, then run the validation gate.
- **`skills/cjm-research/SKILL.md`** `0.4.0 → 0.5.0` — enrichment fan-out (Step 5 world sources; pattern carries to Step 6 internal): delegate per anomaly / stage / search mode.
- **`skills/product-analysis/SKILL.md`** `0.9.x → 0.10.0` — data acquisition: delegate per dashboard / funnel stage / segment, aggregate, then run the validation gate.
- **`references/subagent-delegation.md`** — fan-out table extended with these three skills.

Additive only — optional guidance with an inline fallback; existing workflows and output formats unchanged.

### Files

| File | Type | Version |
|---|---|---|
| `references/subagent-delegation.md` | modified (fan-out table +3 rows) | n/a |
| `skills/product-research/SKILL.md` | modified (delegation note) | 0.8.0 → 0.9.0 |
| `skills/cjm-research/SKILL.md` | modified (delegation note) | 0.4.0 → 0.5.0 |
| `skills/product-analysis/SKILL.md` | modified (delegation note) | → 0.10.0 |
| `README.md` | version bump 1.23.0 | n/a |

### Backwards compatibility
Additive — inline fallback preserves prior behavior. Safe for Claude.

## v1.22.0 (2026-06-30)

### Added — subagent delegation for fan-out skills

Heavy read / fan-out steps can now delegate to parallel subagents, keeping the main agent's context clean and running independent reads concurrently.

- **`references/subagent-delegation.md`** (NEW) — shared pattern: when to delegate (many items / independent searches), how (split into batches → spawn subagents in parallel → each returns a compact structured result → main agent aggregates), what subagents return, data-policy compliance, batch caps, and inline fallback. Includes a per-skill fan-out table.
- **`skills/meeting-processor/SKILL.md`** `0.10.0 → 0.11.0` — Search mode: delegate per-meeting reads across many meetings.
- **`skills/knowledge-library/SKILL.md`** `0.4.0 → 0.5.0` — Search: delegate per-source / per-mode reads.
- **`skills/team-ops-reporter/SKILL.md`** `0.1.0 → 0.2.0` — Jira fetch (member/quarter-review): delegate paginated/per-period fetches.

Each skill gained a short "Subagent delegation (large fan-out)" note in its Search/fetch step pointing to the shared reference. **Additive only** — the note is optional guidance and an inline fallback preserves prior behavior; output formats unchanged.

### Files

| File | Type | Version |
|---|---|---|
| `references/subagent-delegation.md` | NEW | n/a |
| `skills/meeting-processor/SKILL.md` | modified (delegation note) | 0.10.0 → 0.11.0 |
| `skills/knowledge-library/SKILL.md` | modified (delegation note) | 0.4.0 → 0.5.0 |
| `skills/team-ops-reporter/SKILL.md` | modified (delegation note) | 0.1.0 → 0.2.0 |
| `README.md` | version bump 1.22.0 | n/a |

### Backwards compatibility
Additive — no behavior removed; inline fallback if subagents are unavailable. Safe for Claude.

## v1.21.0 (2026-06-30)

### Changed — dedup wave (2): Self-improvement normalization

Normalized the remaining divergent inline "Self-improvement check" blocks to the same pointer to `references/self-improvement.md` introduced in v1.20, so all skills now share one consistent self-improvement instruction. Behavior unchanged — each block already directed to the same reference.

**Normalized (3):** `brainstorm-features`, `cjm-research`, `meeting-processor`.

**Skipped (1):** `team-ops-reporter` — its Step 7 already states the self-improvement step as a one-line pointer to the reference; replacing it would clobber the unrelated "summary + iterate" instructions in the same sentence. Left as-is.

After v1.20 + v1.21 the Self-improvement check is consolidated to the reference across every skill that had a full inline block (8 skills); no per-skill version bumps (consistency cleanup, no behavior change).

### Files

| File | Type |
|---|---|
| `skills/brainstorm-features/SKILL.md` | modified (block → pointer) |
| `skills/cjm-research/SKILL.md` | modified (block → pointer) |
| `skills/meeting-processor/SKILL.md` | modified (block → pointer) |
| `README.md` | version bump 1.21.0 |

### Backwards compatibility
Housekeeping only — no behavior change. Safe for Claude.

## v1.20.0 (2026-06-30)

### Changed — dedup wave (1): Self-improvement check → reference pointer

Removed a verbatim-duplicated inline "Self-improvement check" block (≈540 chars, identical byte-for-byte) from 5 skills and replaced it with a single pointer to `references/self-improvement.md`, which already holds the full protocol (trigger conditions, 4 steps, improvement types, constraints). No behavior change — the trigger condition and the version-bump/CHANGELOG outcome are preserved via the reference.

**Deduped (5):** `write-concept`, `requirements-creator`, `product-analysis`, `product-research`, `task-creator`.

**Skipped (conservative — wording differs, left intact):** `brainstorm-features`, `cjm-research`, `meeting-processor`, `team-ops-reporter` — these carry slightly divergent inline blocks; a wording-normalization pass for them is deliberately out of scope (separate future change).

**No per-skill version bumps** — additive cleanup, skills already cited `self-improvement.md`; behavior unchanged.

### Files

| File | Type |
|---|---|
| `skills/write-concept/SKILL.md` | modified (block → pointer) |
| `skills/requirements-creator/SKILL.md` | modified (block → pointer) |
| `skills/product-analysis/SKILL.md` | modified (block → pointer) |
| `skills/product-research/SKILL.md` | modified (block → pointer) |
| `skills/task-creator/SKILL.md` | modified (block → pointer) |
| `README.md` | version bump 1.20.0 |

### Backwards compatibility
Housekeeping only — no behavior change. Safe for Claude.

## v1.19.0 (2026-06-29)

### Fixed — product-analysis step order
- **`skills/product-analysis/SKILL.md`** `0.9.0 → 0.9.1` (PATCH) — moved the `Step 0.5: Vault Context Search` block to sit **before** `Step 1.5 — Data Integrity Gate` (it was physically placed below 1.5). Cosmetic ordering fix; no logic change. Closes the last concrete audit item.

### Assessed — dedup pilot
- **Figma-context-check** dedup (write-concept ↔ requirements-creator) was assessed and **skipped**: the two blocks are not cleanly identical (only a 3-bullet middle fragment is verbatim; extracting it would split one logical block across an inline section and a reference). Conservative call — not worth the fragility.
- **Identified clean dedup target for v1.20:** the "Self-improvement check" paragraph is identical across `write-concept`, `requirements-creator`, and `product-analysis` and is already backed by `references/self-improvement.md` — replacing the inline paragraphs with a pointer is the safe, high-payoff dedup.

### Files

| File | Type |
|---|---|
| `skills/product-analysis/SKILL.md` | modified (Step 0.5 reorder + 0.9.1) |
| `README.md` | version bump 1.19.0 |

### Backwards compatibility
Cosmetic reorder only — no behavior change. Safe for Claude.

## v1.18.0 (2026-06-29)

### Changed — i18n: planning suite + tooling translated to English

The plugin is a public English-language repo. The planning-suite additions (v1.15.0–v1.17.0) and the testing tooling had shipped in Ukrainian. This release translates all of that content to English so the whole repo is consistent. Going forward, planning artifacts are drafted in the team's working language and the **English version is what lands in Git**.

**Translated to English:**
- `references/capacity-model.md`, `references/dependency-model.md`, `references/planning-core.md`, `references/roadmap-artifacts.md`
- `skills/quarterly-planning/SKILL.md`, `skills/project-planning/SKILL.md`, `skills/sprint-planning/SKILL.md`, `skills/roadmap-architect/SKILL.md` — including frontmatter `description` (skill triggering is now English)
- `testing/Testing-process.md`, `testing/test-cases.md`, `testing/skill_lint.py` (comments + output strings)
- The Planning setup step in `skills/plugin-configurator/SKILL.md` and the Planning section in `local-context.example.md`
- CHANGELOG entries v1.15.0 / v1.16.0 / v1.17.0 re-written in English

**Skill version bumps (PATCH — English description):** quarterly-planning, project-planning, sprint-planning, roadmap-architect `0.1.0 → 0.1.1`.

### Added — bilingual trigger phrases (all 18 skills)
Every skill's frontmatter `description` now carries trigger phrases in **both English and Ukrainian** (`… Українською: "…", "…"`), so skills trigger regardless of the language the user types. Skill bodies stay English; only the trigger phrase list is bilingual. Additive — no behavior change, existing English triggers preserved (existing skills not version-bumped for this additive change).

**Note:** in `planning-core.md` the status-normalization "Signals" column keeps literal Ukrainian tokens (e.g. `Готово`, `Закінчено`) — those are the actual values matched in the team's Confluence/Jira bodies; translating them would break status detection. They are data, not prose.

### Backwards compatibility
Translation only — no logic or behavior change. Trigger phrases preserved (now in English). Safe for Claude.

## v1.17.0 (2026-06-29)

### Fixed — audit quick-fixes (batch 2)

- **`skills/team-ops-reporter/references/jira-data-protocol.md`** — removed the hardcoded sprint-ids (`55=14979` etc.) that go stale every sprint. Replaced with dynamic resolution at runtime (`openSprints()`/`closedSprints()` in JQL, or `customfield_10020`, or the board's sprints → map name→id). Numbers kept only as a marked "example, not a default".
- **`skills/template-library/SKILL.md`** — fixed the count: "one of **11** actions" → "**12** actions" (the Actions table actually has 12 rows, including `backup` / `restore --from`).

### Changed — lint denoise

- **`testing/skill_lint.py`** — in the dangling-refs check on reference file bodies, **dated example names are now ignored** (`YYYY-MM-DD`, e.g. vault artifacts in `vault-schema.md`/`vault-protocol.md`). Removed 18 false WARNs; the gate stays high-signal.

### Verified — not a bug
- `product-analysis` cross-ref "Step 0h" — **correct** (Step 0h = vault detection actually exists in `references/local-context-protocol.md`, a sub-step of Step 0). Audit flag cleared.

### Deferred → v1.18
- `product-analysis` cosmetic Step 0.5/Step 1.5 ordering (block move) — together with the `plugin-configurator` refactor (careful inspection of large files).

### Files

| File | Type |
|---|---|
| `skills/team-ops-reporter/references/jira-data-protocol.md` | modified (sprint-id → dynamic) |
| `skills/template-library/SKILL.md` | modified (11 → 12 actions) |
| `testing/skill_lint.py` | modified (denoise dated examples) |
| `README.md` | version bump 1.17.0 |

### Backwards compatibility
Additive + doc/tooling fixes. Safe for Claude; trigger phrases and behavior unchanged.

## v1.16.0 (2026-06-29)

### Fixed — audit quick-fixes (batch 1)

- **`skills/design-bridge/SKILL.md`** `0.2.0 → 0.2.1` (PATCH) — fixed the subtype/template_id mismatch that **broke Step T** (template resolution always missed → ad-hoc): `subtype=feature-concept` → `feature`; fallback id `presentation-builtin-feature-concept-v1` / `presentation-builtin-{subtype}-v1` → `presentation-builtin-feature` / `presentation-builtin-{subtype}` (aligned with the real `template_id: presentation-builtin-feature`, `subtype: feature`).
- **`references/capacity-model.md`** — fixed the dangling reference `data-pipeline.md` → `jira-data-protocol.md` (data-pipeline was intentionally never created; the team-ops-reporter protocol is reused).

### Added — testing infrastructure in the repo

- **`testing/Testing-process.md`** — the plugin testing process: 6 stages (backup → static lint → trigger eval → scenario walk → integration → regression → sign-off), test case format, backup protocol, release loop, subagent orchestration, Definition of Done.
- **`testing/skill_lint.py`** — automated Stage 1: frontmatter, `name`==folder, semver, resolution of `references/*`, **skill_version in body == frontmatter**, and (v1.16) **dangling refs in the bodies of reference files** (backticked `*.md`).
- **`testing/test-cases.md`** — the test case registry by stages, updated every release.

### Files

| File | Type | Version |
|---|---|---|
| `skills/design-bridge/SKILL.md` | modified (subtype/template_id fix) | 0.2.0 → 0.2.1 |
| `references/capacity-model.md` | modified (ref fix) | n/a |
| `testing/Testing-process.md` | NEW | n/a |
| `testing/skill_lint.py` | NEW | n/a |
| `testing/test-cases.md` | NEW | n/a |
| `README.md` | version bump 1.16.0 | n/a |

### Deferred
- `product-analysis` phantom Step 0h + step order → v1.17 (needs careful inspection of the file).
- Remaining audit fixes (team-ops-reporter sprint-id, template-library count, plugin-configurator duplicates/numbering) → v1.17/v1.18.

### Backwards compatibility
Additive + bugfix. Safe for Claude; trigger phrases preserved.

## v1.15.0 (2026-06-29)

### Added — Planning Suite (4 skills) + planning core references

A new planning/forecasting layer on top of the existing `team-ops-reporter` reporting. Four skills along the roadmap abstraction levels + four shared references. **Complements** team-ops-reporter (which is descriptive — "what is / was"; planning is "what should be"), does not duplicate it: shared Jira plumbing is reused from `team-ops-reporter/references/jira-data-protocol.md`.

**Two planning axes on a shared foundation:**
- Foundation — `roadmap-architect` (structure, outside of time).
- Vertical — `project-planning` (a single direction across time).
- Horizontal — `quarterly-planning` + `sprint-planning` (a period across all directions).
- The axes link through a shared `% allocation to a direction` and `capacity-model`.

**New skills:**
- **`quarterly-planning` (v0.1.0)** — quarterly roadmap: retro of the previous quarter (delegates `team-ops-reporter` `quarter-review`) → capacity (4 inputs with a gate) → draft + capacity-gate on platform slices → scope correction → artifacts (Confluence + live dashboard + q{N} labels). Modes: retro/plan/full/refresh.
- **`project-planning` (v0.1.0)** — project arc outside of quarters: scope + dependency graph/critical path + duration forecast under % allocation + multi-quarter roadmap + **rolling-reforecast** (`replan`: actuals+carryover → shift to the future + drift vs baseline). Modes: forecast/sequence/roadmap/whatif/replan.
- **`sprint-planning` (v0.1.0)** — sprint pre-planning: focuses from the roadmap → per-member capacity → carryover-risk (delegates `sprint-review`+`member-review`) → readiness scan (work-type DAG) → sequence violation detection → fill + pull-forward → assignee proposals. Modes: groom/plan/review/forecast.
- **`roadmap-architect` (v0.1.0)** — structural hygiene: mapping Goal→Initiative→Epic→Feature, enforcing layout, tree, gap report. Modes: audit/map/tree/onboard.

**New references (shared core):**
- `references/capacity-model.md` — ceiling formula, per-member, baseline+calibration, availability, tech debt, **allocation %**, platform slices, auto-estimate by analogy, gate thresholds (85/100%), quarter↔sprint scaling, duration forecast hook.
- `references/dependency-model.md` — two-level DAG (epic/feature + work-type), topological sort, critical path, cycles, **readiness rule** (threshold on review/in test/done), sources from Jira links.
- `references/planning-core.md` — canonical hierarchy, layout convention (names/labels), status normalization, goal map, **Development Flow** (the team's development flow from onboarding).
- `references/roadmap-artifacts.md` — formats of planning artifacts (quarterly roadmap, project arc, structure tree, capacity-gate, live dashboard) + demarcation from the ops report.

**Changed:**
- `skills/plugin-configurator/SKILL.md` `2.0.0 → 2.1.0` (MINOR) — new **Planning setup** + **Development Flow** survey (typical work sequence, parallelism, dependencies, readiness threshold) in Extended onboarding; writes the Planning section to local-context.
- `local-context.example.md` — new **Planning** section (team composition+capacity rules, sprint cadence+anchor+board, baseline, goal map, gate thresholds, development_flow).
- `README.md` — version 1.15.0, skills #14–17, new references.

### Changed — rename Feature Task Creator → Task Creator
- `skills/feature-task-creator/` → `skills/task-creator/`; `name: feature-task-creator → task-creator`, title "Feature Task Creator" → "Task Creator", description generalized (not just "feature"). All internal references in the plugin updated via find/replace (CHANGELOG history preserved). **Trigger phrases preserved** — phrase-based invocation in Claude does not break.

**Validated** via an end-to-end run on live PROJ/Prom data (Q2 actuals → capacity Q3 → draft → 2 correction iterations + platform slices → published roadmap + live dashboard).

### Files

| File | Type | Version |
|---|---|---|
| `references/capacity-model.md` | NEW | n/a |
| `references/dependency-model.md` | NEW | n/a |
| `references/planning-core.md` | NEW | n/a |
| `references/roadmap-artifacts.md` | NEW | n/a |
| `skills/quarterly-planning/SKILL.md` | NEW | v0.1.0 |
| `skills/project-planning/SKILL.md` | NEW | v0.1.0 |
| `skills/sprint-planning/SKILL.md` | NEW | v0.1.0 |
| `skills/roadmap-architect/SKILL.md` | NEW | v0.1.0 |
| `skills/plugin-configurator/SKILL.md` | modified (Planning setup + Development Flow) | 2.0.0 → 2.1.0 |
| `local-context.example.md` | modified (Planning section) | n/a |
| `README.md` | version + 4 skills + references | n/a |

### Fixed — skill_version sync (audit quick-fix)
Synced `skill_version` in the body (vault_save) with frontmatter: cjm-research 0.2.0→0.4.0, product-analysis 0.6.0→0.9.0, write-concept 0.5.0→0.7.0. Caught by the lint gate during the release. No behavior change.

### Backwards compatibility
Additive only. Existing skills and `local-context.md` are untouched. Planning skills require the Jira MCP (already a prerequisite) and optionally Confluence/calendar; they delegate facts to team-ops-reporter without duplicating the fetch.

## v1.14.0 (2026-06-29)

### Added — Team Ops Reporter skill

New skill `team-ops-reporter` (v0.1.0) — operational team reports built directly on Jira, with five modes: **sprint-plan**, **sprint-review**, **quarter-review**, **initiative-status**, **member-review**. Designed and validated against live PROJ/Prom data during bring-up.

**What it does:**
- Pulls issues via JQL, processes in Python (aggregations, Story Points, carried-vs-new, per-Assignee/Developer), renders from a template, and offers charts.
- Output destination is asked each run: Confluence and/or local `md` + `xlsx`. Visualizations are proposed (burndown, SP dynamics over periods, status donut, load distribution) and built on accept.
- Built-in templates ship under `templates/built-in/ops-report/` (5 subtypes); custom templates via Template Library (`artifact_type: ops-report`, Step T resolution).

**Modes & validated mechanics:**
- **sprint-plan** — directions -> features -> tasks; total / carried / new + SP; per-Assignee and per-Developer breakdowns; key-focus table with per-direction summaries.
- **sprint-review** — closed work (`statusCategory = Done`, **includes the `Ready` status**); releases grouped by stream (app / catalog-ui / backend / company-stats), windowed by `releaseDate`; feature flags ON/OFF (FLAG field + "Випилити прапор" cleanup tasks); closed-per-member; full task list with links.
- **member-review** — role-aware throughput via changelog-backed JQL (`status CHANGED TO "Ready for test" BY "<accountId>" DURING (...)`); delivery metrics from `resolutiondate` + SP; dynamics at any granularity (day/week/sprint/month/quarter/year); matplotlib chart.
- **initiative-status** — % done from `statusCategory` over the epic's `cf[10014]` child tree; status donut; per sub-feature (`X.Y` code in summary); blockers (Flagged `customfield_10021` / `On hold` / blocked-by links).
- **quarter-review** — plan-vs-actual by direction, epics/features fully closed, releases; **fetched per month** because the full-quarter `resolved` JQL times out (>180 s) on this Jira.

**Files:**

| File | Type | Version |
|---|---|---|
| `skills/team-ops-reporter/SKILL.md` | new skill | v0.1.0 |
| `skills/team-ops-reporter/references/jira-data-protocol.md` | new reference | n/a |
| `templates/built-in/ops-report/sprint-plan-v1.md` | new template | v1.0.0 |
| `templates/built-in/ops-report/sprint-review-v1.md` | new template | v1.0.0 |
| `templates/built-in/ops-report/member-review-v1.md` | new template | v1.0.0 |
| `templates/built-in/ops-report/initiative-status-v1.md` | new template | v1.0.0 |
| `templates/built-in/ops-report/quarter-review-v1.md` | new template | v1.0.0 |
| `README.md` | version bump 1.14.0 + skill #14 + templates list | n/a |

### Jira data protocol (PROJ defaults, in `jira-data-protocol.md`)
Custom-field map: Team `customfield_10001`, Story Points `customfield_10036`, Developer `customfield_10041`, QA `customfield_10037`, Epic Link `customfield_10014`, Sprint `customfield_10020`, FLAG `customfield_10043`. Large markdown JQL responses (descriptions inflate them past the token cap) are parsed via `grep -o` compact patterns; pagination via `nextPageToken`. Confluence publishing via `createConfluencePage` (HTML; `parentId` may be a folder id).

### Backwards compatibility
Additive only. Existing skills and `local-context.md` files are unaffected. The new skill requires the Jira MCP (already a plugin prerequisite) and optionally Confluence for publishing.

---

## v1.13.0 (2026-05-11)

### Added — Data Integrity Gate across analytical skills

Universal verification gate for all skills that cite metrics, benchmarks, or claims. Born from a real incident (May 2026 Prom.ua Catalog research project) where 4 progressive errors propagated into 5+ artifacts before user-side detection. Root cause: uncritical citation of raw data points without period verification, multi-source cross-validation, or context annotation.

**Failure patterns this release prevents:**

1. **Incomplete-period extrapolation** — Tableau monthly view extracted mid-month, last cell treated as full month, "-77% PoP" reported as real anomaly (was 7-day partial period)
2. **Week-1 holiday zriz cited as YoY trend** — single weekly comparison from Jan 1-7 propagated as full-year YoY decline ("Listings GMV -29% YoY, Portal -8.6% YoY"); reality across 18 of 19 weeks was both growing +20%/+42%
3. **Cascading derived claims** — "3.4× faster degradation" derived from #2 propagated into 5+ artifacts without re-verification
4. **Missing inline period annotation** — metrics like "CR 0.99%" cited without period context, losing meaning when copied to Slack/slides

**What changed:**

- **`references/data-integrity-protocol.md`** **(NEW)** — universal protocol with 5 gate checks: Period/Context Completeness, Seasonal/Cultural Screening, Multi-Source Cross-Validation (≥2 sources, ≥3 for extreme values), Period Definition Lock + Inline Annotation, Source Type Marker. Defines output statuses (✅ Verified / ⚠️ Caveat / ❌ Blocked) and anti-pattern catalog from real incidents.

- **`references/cjm-protocol.md`** — extended with three new sections: Data Integrity Gate quick reference, Holiday Screening Windows (Ukraine + Global), Anomaly Verification Checklist (mandatory checks for drop > 25% / lift > 50%), recommended reference sources catalog structure.

- **`skills/cjm-research/SKILL.md`** `0.3.1 → 0.4.0` (MINOR) — new **Step 3.5 — Data Integrity Gate (MANDATORY)** between Step 3 (Load CJM data) and Step 4 (Anomaly detection). Step 4 inherits gate status (skip Blocked, propagate Caveat). Quality Standards extended with inline-annotation requirement, caveat propagation, anomaly disclosure, source type markers.

- **`skills/product-analysis/SKILL.md`** `0.8.0 → 0.9.0` (MINOR) — new **Step 1.5 — Data Integrity Gate (MANDATORY)** between Step 1 (Initialization and data acquisition) and Step 2 (Analysis engine). Mode-specific extra checks for Post-Release Analysis (release date + flag activation verification, before/after period balance) and A/B Test Results (sample-size power check, statistical significance reporting, selection bias check, novelty-effect screening). Quality Standards extended; explicit rule: never declare A/B winner/loser without sample-size power check + p-value + holiday-screening + segment-level review.

- **`skills/product-research/SKILL.md`** `0.7.0 → 0.8.0` (MINOR) — new **Step 1.5 — Source Validation Gate (MANDATORY)** between Step 1 (Deep discovery) and Step 2 (Gather data). External-source specific checks: recency thresholds per data type, geographic/cultural context (Ukraine default catalog of direct-fit vs adaptation-required competitors), sensational-claim verification (≥3 sources), bias screening (vendor reports, single competitor PR, social-media). Quality Standards extended with caveat propagation and extreme-claims disclosure.

### Files changed

| File | Type | Skill version |
|------|------|---------------|
| `references/data-integrity-protocol.md` | **NEW** | n/a |
| `references/cjm-protocol.md` | modified (3 new sections appended) | n/a |
| `skills/cjm-research/SKILL.md` | modified (Step 3.5 added, Step 4 + Quality Standards updated) | 0.3.1 → 0.4.0 (MINOR) |
| `skills/product-analysis/SKILL.md` | modified (Step 1.5 added, Step 2 + Quality Standards updated) | 0.8.0 → 0.9.0 (MINOR) |
| `skills/product-research/SKILL.md` | modified (Step 1.5 added, Step 2 + Quality Standards updated) | 0.7.0 → 0.8.0 (MINOR) |

### Migration

No breaking changes. Existing `local-context.md` files remain fully functional. The gate operates with built-in defaults if no `data_sources_catalog` is configured.

**Optional new `local-context.md` field** (recommended for full benefit of Gate Check 3):

```yaml
data_sources_catalog:
  - metric: "Listing GMV YoY"
    primary: "Tableau workbook 285 YtoY view"
    cross_validation: "Orders Dashboard v2 Portal vs Sites"
    methodology_doc: "DT-1773 attribution"
  - metric: "Catalog CR"
    primary: "Listing metrics workbook 285 Overview"
    cross_validation: "Master CJM workbook 125 + Glint live"
  # ... more entries
```

This catalog enables Gate Check 3 (Multi-Source Cross-Validation) to operate automatically — the skill knows which secondary source to query for each metric without user prompting.

### Compatibility

- All three modified skills remain backwards compatible with existing invocation patterns.
- The new gate steps run automatically; users do not need to invoke them explicitly.
- For ⚠️ Caveat metrics, the skill will surface the qualifier in the final report instead of blocking the workflow.
- For ❌ Blocked metrics, the skill will halt with a clear explanation rather than silently producing potentially-wrong output.

### Validation

Each skill version has been validated against the 4 root-cause patterns from the May 2026 incident:

1. ✅ Incomplete-period extrapolation — Gate Check 1 catches this at the source
2. ✅ Week-1 holiday zriz — Gate Check 2 flags holiday windows, forces full-table review
3. ✅ Cascading derived claims — Caveat propagation surfaces qualifiers throughout the report
4. ✅ Missing inline annotation — Gate Check 4 + Quality Standards make annotation mandatory

---
## v1.12.0 (2026-04-29)

### Added — Tableau MCP-First Integration

The plugin now uses the Tableau MCP connector as the **default** path for all Tableau interactions, with browser as a true fallback. Concrete tools (`get-view-data`, `query-datasource`, `get-view-image`, `search-content`, `list-pulse-metrics-*`, `generate-pulse-insight-*`) replaced generic "Tableau MCP → browser" prose in three skills.

**What changed:**
- **`references/integration-strategy.md`** — added a Tableau row to the connector table with explicit MCP tool patterns; new "Per-product tool guidance — Tableau" subsection mapping every common task to the right tool. Added a `tableau-mcp` / `tableau-web` source-marker convention.
- **`skills/product-analysis/SKILL.md`** `0.7.0 → 0.8.0` — rewrote 4 sections (Step 1e Tableau/Analytics, CJM-3 Load funnel data, PR-2 Post-Release Data acquisition, AB-2 A/B Test Tableau dashboards) to make MCP the default and browser the fallback. Each section now logs its source as `tableau-mcp` or `tableau-web` for auditability.
- **`skills/cjm-research/SKILL.md`** `0.3.0 → 0.3.1` — Sources sections now mark Tableau-derived data with `tableau-mcp` / `tableau-web` so users can audit the retrieval method per datapoint.

**New optional `local-context.md` fields** (Tableau section):
- `organization.tableau_site_name` — for non-default Tableau sites
- `organization.tableau_datasource_urls` — map name → URL, used by `query-datasource`
- `organization.tableau_pulse_metric_ids` — map name → metric ID, used by Pulse tools

### Added — Onboarding 2.0 (Basic / Extended / Test modes)

Onboarding redesign addressing first-user feedback that setup felt long and uncertain.

**What changed in `skills/plugin-configurator/SKILL.md`** `1.0.0 → 2.0.0` (MAJOR):
- **New Step 1 — Welcome and onboarding map** showing all 17 steps with type, mode applicability, and time estimates so the user always sees where they are.
- **New Step 2 — Choose mode** with three options: Basic (~3-5 min), Extended (~15-25 min), Test mode (sandbox).
- **New Step 3 — Connector pre-check** — proactive ping of Jira / Confluence / Figma / Notion / Tableau / Fireflies / Calendar / Gmail / GDrive / Slack with a readiness table mapping connectors to skills they unlock. Mandatory connectors block; recommended only warn.
- **Reordered subsequent steps** so Vault precedes Templates and Knowledge Library — Templates and Knowledge can now use the Vault as their storage root from day one.
- **Mode gates** added to every Extended-only step (Step 8 Metrics & OKRs, Step 9 Teams, Step 10 Repos, Step 11 CJM, Step 12 Knowledge, Step 13 Templates, Step 14 Vault, Step 15 Custom). Basic mode silently appends each skipped key to `onboarding.deferred_steps`.
- **New Step 17 — Quick Wins** showing 2-3 actionable next-step recommendations driven from session context (missing Tableau → "connect Tableau MCP", deferred CJM → "run CJM via Quick setup", etc.).
- **New Test Mode workflow** (`Workflow — Test Mode (sandbox)`) — full 5-step procedure (TM-0..TM-5) with sandbox isolation rules, finale diff, Discard / Promote / Keep menu, and a verification matrix for maintainers. Triggers: "dry-run onboarding", "test mode", "тестовий режим", or Step 2 selection.
- **Test Mode redirects all writes** to `~/.grow-pm-sandbox/` (peer of `~/.grow-pm/`). Real config is never read or written. Vault Mirror is fully skipped during sandbox runs.
- **Modes table at the top** updated from "Five Modes" to "Six Modes" — Onboarding (Basic), Onboarding (Extended), Onboarding (Test sandbox), Reinstall / Migration, Update, Validate, View, plus the standalone Test mode entry.

### Added — Obsidian Setup Guide reference (new file)

**`skills/plugin-configurator/references/obsidian-setup-guide.md`** — canonical step-by-step procedure shared by Step 14 (Onboarding) and Update → Vault Management → Connect Vault. Pre-flight checks (Obsidian installed?), 9 setup steps with explicit ✅/⚠️/❌ validation per substep (path validation, `.obsidian/` check, write/read permission test, products binding, sync mode, Obsidian MCP detection, folder init, smoke test, save-to-context), plus a Common errors and recovery table.

### Added — CJM save-offer for ad-hoc invocation

**`references/local-context-protocol.md` Step 0f rewritten** — when a CJM skill (`cjm-research`, `product-analysis` CJM mode, `brainstorm-features` CJM mode) starts without CJM Configuration in `local-context.md`, the user is now offered three options instead of two:

1. Run Plugin Configurator → Step 11 (full setup)
2. **Quick CJM setup (Recommended)** — collect ad-hoc config, then offer to save it before running analysis
3. Skip CJM mode

The Quick CJM setup workflow collects only what the analysis needs (template/stages, dashboards, thresholds, baseline, platforms) and explicitly asks "Save this to `local-context.md`?" before running. If accepted, this becomes equivalent to a full Configurator setup. Hooks added to `cjm-research/SKILL.md` and `product-analysis/SKILL.md` CJM-1.

### Schema additions (`context-schema.md`)

- New **Onboarding Status** section in `local-context.md` (auto-managed by Configurator): `mode`, `basic_completed_at`, `extended_completed_at`, `last_test_run_at`, `deferred_steps`, `skip_nudges`. Backward compatible — old `local-context.md` files get auto-fill on next save.
- 3 new optional Tableau fields under organization (see above).

### Files changed

| File | Type | Skill version |
|------|------|---------------|
| `references/integration-strategy.md` | modified | n/a |
| `references/local-context-protocol.md` | modified (Step 0f) | n/a |
| `skills/product-analysis/SKILL.md` | modified (5 sections) | 0.7.0 → 0.8.0 (MINOR) |
| `skills/cjm-research/SKILL.md` | modified (Sources marker, CJM-1 hook) | 0.3.0 → 0.3.1 (PATCH) |
| `skills/plugin-configurator/SKILL.md` | major restructure | 1.0.0 → 2.0.0 (MAJOR) |
| `skills/plugin-configurator/references/context-schema.md` | modified (Onboarding Status, 3 Tableau fields) | n/a |
| `skills/plugin-configurator/references/obsidian-setup-guide.md` | **NEW** | n/a |
| `local-context.example.md` | modified (Tableau extended fields, Onboarding Status example) | n/a |
| `README.md` | version bump + onboarding modes mention | n/a |

### Migration

`local-context.md` files generated by previous versions remain fully functional. On next save (any Configurator mode), the missing **Onboarding Status** section is added with sensible defaults (`mode: extended`, `extended_completed_at: <now>`, empty `deferred_steps`).

No breaking changes to skill outputs. Tableau-using skills continue to work even if the new MCP-specific fields are not set — they fall back to browser as before.

---

## v1.11.0 (2026-04-20)

### Changed — Brand-Agnostic Refactor (public-repo hygiene)

**Problem:** The public plugin repo accidentally shipped hardcoded brand data for a specific organization (brand hex, brand fonts, DS file key, organization name, paths to a themed pptx template, Jira/Confluence keys) inside `design-integration/` and the `design-bridge` skill. Third-party users installing the plugin would inherit another organization's brand. Ukrainian-language template bodies also shipped publicly even though the repo README is in English.

**Solution:** Pulled all brand-specific and organization-specific values out of the plugin and moved them behind the existing `local-context.md` contract (gitignored, user-owned). Design-bridge now reads brand tokens, DS spec path, pptx theme path, base pptx path, and Figma file key from `product.*` fields in local-context, with neutral placeholder defaults when the user has not configured a DS. Every built-in template and reference has been translated to English; localize via `<!-- lang:xx -->` blocks.

#### Files removed

- **`design-integration/`** (entire folder, 6 files + an org-specific base pptx) — contained organization-specific DS spec, pptx theme, and a base pptx template. Per-organization equivalents now live in the user's workspace folder and are referenced from `local-context.md` under the new Design System section.

#### Files changed — `skills/design-bridge/`

- **SKILL.md** `0.1.0 → 0.2.0` — minor. Removed all hardcoded references to the organization's brand. Now reads `product.design_system_spec`, `product.pptx_theme`, `product.base_pptx`, `product.brand.primary`, `product.brand.dark`, `product.brand.font_primary`, `product.brand.font_display`, and `product.figma.ds_file_key` from local-context. End-to-end example genericized.
- **references/deck-subtypes.yaml** — removed `uk` language keys (kept `en` only); `referenced_theme` now points to `<product.pptx_theme from local-context.md>`.
- **references/figma-playbook.md** — removed organization name and hardcoded file key references; documents the generic brand DS configuration schema.
- **references/a11y-checklist.md** — replaced organization-specific contrast pairs with a schema and instruction to pre-compute pairs under `contrast_pairs:` in the user's DS yaml.

#### Files changed — templates and other skills

- **`templates/built-in/`** — 12 seed templates translated to English. Multilingual format preserved via `<!-- lang:xx -->` blocks; users can add additional language blocks in their own copies via Template Library.
- **Skill files and references** — all workflow instructions and inline examples translated to English; user-facing output language is still controlled by `user.language` in local-context.

#### Files changed — marketplace & plugin metadata

- **`.claude-plugin/plugin.json`** — description reworded from the old brand-specific phrasing to "brand-themed decks… (bring your own Design System via local-context.md)".
- **`.claude-plugin/marketplace.json`** — same description change.
- **`local-context.example.md`** — new **Design System** section per product with placeholder schema for brand tokens, DS spec path (yaml), pptx theme path (yaml), base pptx path, Figma file key, and an optional `contrast_pairs` block. `Language:` default flipped to `en`.

#### Skills changed

| Skill | From | To | Change type |
|-------|------|----|-------------|
| design-bridge | 0.1.0 | 0.2.0 | minor — brand-agnostic refactor; reads all brand fields from local-context |

#### Migration notes

Existing users upgrading from v1.10.0:
1. Run `plugin-configurator` to populate the new Design System fields in your `local-context.md` (see `local-context.example.md`).
2. If you relied on a shipped base pptx / DS spec / pptx theme, move those assets into your own workspace folder (e.g., `design-assets/`) and point `product.base_pptx` / `product.design_system_spec` / `product.pptx_theme` at them.
3. If any of your product-specific templates used `<!-- lang:uk -->` blocks, they remain valid in your local Template Library; only the built-in seed templates were translated to English.

---

## v1.10.0 (2026-04-20)

### Added — Design Bridge Integration

> Note (superseded by v1.11.0): organization-specific values originally captured here were moved out of the repo. The description below has been sanitized accordingly.

**Problem:** Claude's Design plugin ships 7 strong skills (user-research, research-synthesis, ux-copy, accessibility-review, design-system, design-critique, design-handoff) but they don't automatically know the brand tokens of the team using them, don't hook into the PM pipeline (concept → requirements → research → brainstorm), and don't produce brand-themed presentations. PMs had to hand-assemble decks in Google Slides and manually copy brand colors/fonts.

**Solution:** Introduced `design-bridge` — an orchestrator skill that acts as the single entry point for design deliverables (deck, prototype, handoff, research-enrichment), owns the active brand's Design System (DS) theme via local-context, and is invoked as an **optional Step D hook** from four upstream skills. Presentations render from a base pptx template (16:9, layouts pulled from the theme yaml) so output matches what stakeholders expect in their shared drive.

#### Core architecture — 3 layers

1. **Narrative** (from upstream skill: concept body, requirements, research themes, hypotheses)
2. **Template** (from Template Library: deck outline with Handlebars variables, multilingual)
3. **DS theme** (from the user-provided pptx theme yaml: colors, fonts, layouts, chart palette) — applied to the user-provided base pptx via `slide_layouts.get_by_name`

Each layer is independently versioned and swappable. Narrative changes don't invalidate the DS; DS updates don't rewrite templates.

#### Files added — skills/design-bridge/

- **SKILL.md** (`v0.1.0`) — orchestrator with 4 intents (deck, prototype, handoff, research-enrichment), Integration prerequisite, Local context prerequisite, Step T, 9-step workflow with 7 design-skill hooks (research-synthesis, ux-copy, design-critique, design-system, accessibility-review, design-handoff, Figma), pptx rendering via the user's base pptx + `slide_layouts.get_by_name`, WCAG 2.1 AA QA gate, publish, vault save, end-to-end example
- **references/deck-subtypes.yaml** — 4 deck subtypes with slide-by-slide outlines: feature-concept (10), research-highlights (10), ab-test-readout (6), release-readout (7)
- **references/figma-playbook.md** — Auth/permissions (View vs Full seat, rate limits), how to find fileKey + nodeId, common patterns (sync tokens, embed screenshot, concept→prototype, handoff), policy, brand DS configuration schema
- **references/a11y-checklist.md** — WCAG 2.1 AA checklist with schema for pre-computed contrast pairs, touch targets (44×44), keyboard nav, screen reader, motion, forms, deck-specific checks, QA output YAML schema

#### Templates added — templates/built-in/presentation/

- **research-highlights-v1.md** — 10 slides (cover / exec summary / method & sample / theme 1 / quote 1 / theme 2 / quote 2 / theme 3 / quantitative findings / recommendations). English; localize via `<!-- lang:xx -->` blocks.
- **ab-test-readout-v1.md** — 6 slides (cover / hypothesis & setup / primary metric / guardrails / interpretation / decision). English.
- **release-readout-v1.md** — 7 slides (cover / scope / key metrics / wins & learnings / incidents / what's next / ask). English.

#### Skill integrations — Step D hook

Four upstream skills gained an optional `## Step D — Design Bridge handoff (Optional)` step that offers to hand results to design-bridge:

| Skill | From | To | Offers (intent / subtype) |
|-------|------|----|---------------------------|
| write-concept | 0.6.0 | 0.7.0 | deck / feature-concept OR prototype (lo-fi / mid-fi) |
| requirements-creator | 0.6.0 | 0.7.0 | handoff (a11y_audit=true) OR prototype (hi-fi) OR deck |
| brainstorm-features | 0.6.0 | 0.7.0 | prototype (lo-fi) for top-1 hypothesis OR deck (8-slide brainstorm readout) |
| product-research | 0.6.0 | 0.7.0 | deck / research-highlights OR research-enrichment (Figma screenshots, competitor UI) |

Step D is always skippable — user can say "no thanks" and the skill finishes as before.

### Skills changed

| Skill | From | To | Change type |
|-------|------|----|-------------|
| design-bridge (new) | — | 0.1.0 | new — orchestrator for 4 design intents with 7 design-skill hooks |
| write-concept | 0.6.0 | 0.7.0 | minor — Step D hook after vault save |
| requirements-creator | 0.6.0 | 0.7.0 | minor — Step D hook (offers a11y handoff for Create mode) |
| brainstorm-features | 0.6.0 | 0.7.0 | minor — Step D hook (top-1 hypothesis prototype or brainstorm readout deck) |
| product-research | 0.6.0 | 0.7.0 | minor — Step D hook (research-highlights deck or research-enrichment) |

### Documentation

- README.md — version bumped to 1.10.0; new Design Bridge section added; 3 new templates listed under built-in; Figma and base-pptx workflow mentioned under Integration Points.
- CHANGELOG.md — this entry.
- plugin.json + marketplace.json descriptions updated to mention design-bridge capability.

### Backup

Before v1.10.0 writes, backups were taken of the plugin, local-context, and template library (preserved in session backup directory).

---

## v1.9.0 (2026-04-17)

### Added — Multilingual Artifact Template System

**Problem:** Every concept, spec, research report, and MoM was starting from a blank page. No reuse of proven document structures across products. Users in different language markets needed the same artifact in multiple languages without duplicating files.

**Solution:** Introduced a first-class template library with three-tier scope (built-in → user-global → product-specific), single-file multilingual storage (language blocks inside one template via `<!-- lang:xx -->` HTML comments), registry-backed resolution with scoring, skill-driven resolution with user opt-in, and three-tier backup protection.

#### Core architecture

- **Scope tiers:** built-in (ships with plugin) → user-global (shared across all products) → product-specific (per-product override), with inheritance and subtype matching.
- **Multilingual format:** single `.md` file contains all language variants as `<!-- lang:xx --> … <!-- /lang:xx -->` blocks. Obsidian-friendly, preserves link integrity, easy to diff.
- **Storage location:** `{storage_root}/Templates/` — lives in the Obsidian vault if configured (primary), or in the user's chosen custom folder. Survives plugin reinstalls.
- **Registry:** `Templates/_registry.json` indexes all templates with metadata (id, version, scope, artifact_type, subtype, languages, usage_count, checksum).
- **Resolution protocol (T-0 → T-5):** scoring by scope (+5/+3/+1), subtype match (+3/+1), language match (+2/+1), usage_count; tie-breakers by recency.
- **User preference:** `templates.preference` in local-context.md — `auto` (silent use of top match), `always_ask` (list candidates every time), `smart` (ask only when multiple strong candidates exist; default).
- **Three-tier backup:** per-template archive (last 10 versions per template), full pack backups (last 5 before bulk ops), and manual user-triggered backup/restore.

#### Files added

- **references/template-protocol.md** — resolution protocol (T-0 → T-5 with scoring), frontmatter schema, skill integration pattern, edge cases, registry schema, backup invariants.
- **skills/template-library/SKILL.md** (`v0.1.0`) — 11 actions (list / show / add / clone / update / delete / restore / import / export / validate / rebuild-registry), plus backup/restore; wizards for add, add-language, import, update; helper routines `resolve()` and `render()`.
- **templates/built-in/** — 9 seed templates shipped with the plugin:
  - `concept/default-v1.md` — concept (PRD) skeleton
  - `requirements/default-v1.md` — general feature requirements
  - `requirements/ab-test-v1.md` — A/B test spec
  - `research/competitive-v1.md` — competitive analysis + SWOT
  - `research/user-research-v1.md` — user research synthesis
  - `cjm/funnel-v1.md` — CJM funnel analysis with ICE table
  - `epic/default-v1.md` — Jira epic description
  - `task/default-v1.md` — Jira task with DoD and AC
  - `presentation/feature-v1.md` — 10-slide feature deck outline

#### Skill integrations

All consumer skills now include a `## Step T — Template Resolution` section that runs before the first workflow step. Each skill declares its `artifact_type` and subtype inference rules, honors the user's `templates.preference`, and falls back to a built-in structure if no template matches.

| Skill | From | To | Step T artifact_type / subtype |
|-------|------|----|------------------------------|
| write-concept | 0.5.0 | 0.6.0 | `concept` / `default` |
| requirements-creator | 0.5.1 | 0.6.0 | `requirements` / `default` \| `ab-test` \| `bugfix` (Create mode only) |
| product-research | 0.5.0 | 0.6.0 | `research` / `competitive` \| `user-research` \| `market` \| `ux-benchmark` |
| cjm-research | 0.2.0 | 0.3.0 | `cjm` / `funnel` (health-check uses silent auto) |
| feature-task-creator | 0.7.0 | 0.8.0 | `task` + `epic` (resolved once per subtype in batch mode) |
| brainstorm-features | 0.5.0 | 0.6.0 | `research` / `hypothesis-list` \| `cjm-hypotheses` (on save) |
| product-analysis | 0.6.0 | 0.7.0 | `research` / `metrics-analysis` \| `post-release` \| `ab-test-results` \| `cjm-funnel` (non-interactive modes) |
| diagram-prototyper | 0.7.0 | 0.8.0 | `presentation` / `feature` \| `research-highlights` \| `ab-test-readout` \| `release-readout` (decks only) |
| meeting-processor | 0.9.0 | 0.10.0 | `meeting-notes` / `grooming` \| `planning` \| `retro` \| `discovery` \| `status` \| `decision` \| `brainstorm` \| `review` (delegates to downstream skill's Step T when chaining) |

#### Onboarding

- **plugin-configurator** `0.10.0 → 1.0.0` — added **Step O-T — Template Library Setup** between Knowledge Library (Step 10) and Obsidian Vault (Step 11). O-T walks the user through: storage location (reuses Knowledge Library decision), copying built-in templates to their library, setting `templates.preference`, and scheduling a first-use template walkthrough.
- **knowledge-library** `0.3.0 → 0.4.0` — added routing section at top explaining when to use `knowledge-library` (external sources: articles, benchmarks) vs `template-library` (artifact skeletons). Added `template-library` to sibling-skill list.

#### Backup

Before the v1.9.0 changes were written to `v1.9.0-staging/`, full backups were taken of the plugin, local-context, and knowledge library (preserved in session backup directory).

### Skills changed

| Skill | From | To | Change type |
|-------|------|----|-------------|
| template-library (new) | — | 0.1.0 | new — CRUD + resolve + render + backup/restore |
| plugin-configurator | 0.10.0 | 1.0.0 | minor — Step O-T onboarding + template library update mode |
| knowledge-library | 0.3.0 | 0.4.0 | minor — routing to template-library, sibling skill section |
| write-concept | 0.5.0 | 0.6.0 | minor — Step T |
| requirements-creator | 0.5.1 | 0.6.0 | minor — Step T (Create mode) |
| product-research | 0.5.0 | 0.6.0 | minor — Step T |
| cjm-research | 0.2.0 | 0.3.0 | minor — Step T |
| feature-task-creator | 0.7.0 | 0.8.0 | minor — Step T (task + epic) |
| brainstorm-features | 0.5.0 | 0.6.0 | minor — Step T (on save) |
| product-analysis | 0.6.0 | 0.7.0 | minor — Step T (structured reports) |
| diagram-prototyper | 0.7.0 | 0.8.0 | minor — Step T (presentations) |
| meeting-processor | 0.9.0 | 0.10.0 | minor — Step T (MoM) + delegation pattern |

---

## v1.8.0 (2026-04-16)

### Changed — User-Controlled Storage

**Problem:** Knowledge Library and local-context.md were stored in `~/.grow-pm/` — a hidden directory that was invisible to the user, not syncable, and often lost during plugin reinstalls. Users repeatedly lost their curated libraries.

**Solution:** Replaced hardcoded `~/.grow-pm/` storage with a pointer-based system where the user chooses where their data lives.

#### Core architecture change
- `~/.grow-pm/` now contains ONLY a pointer file (`.storage-pointer.yaml`) that tells the plugin where actual data is stored
- Two storage modes: **Vault** (Obsidian vault = primary storage, recommended) or **Custom** (user-chosen folder)
- When Obsidian is configured, the vault IS the primary storage — no separate copy, no mirror sync needed

#### Files changed

- **references/persistent-storage.md** — complete rewrite:
  - New "Pointer + User-Controlled Storage" architecture
  - Storage pointer format (.storage-pointer.yaml)
  - Per-product Knowledge Library support
  - File Resolution Protocol (R-1 through R-4)
  - Storage Selection during onboarding (S-1 through S-3)
  - Recovery flow when pointer is missing — always asks user before creating empty config
  - Change Storage Location workflow (CL-1, CL-2)

- **knowledge-library** `0.3.0 → 0.4.0`:
  - Library Storage section rewritten: vault = primary when configured, custom folder otherwise
  - New "Library Resolution at Skill Start" — 5-step resolution chain with legacy fallback
  - Removed Vault Mirror Sync (no longer needed — vault IS primary)
  - Added: "Never silently create empty library" quality standard

- **plugin-configurator** `0.9.0 → 0.10.0`:
  - New **Step 0 — Storage Selection** in Onboarding (before any data collection)
  - Rewritten **Auto-trigger Protocol** — pointer-based resolution, recovery flow asks user
  - Rewritten **Reinstall / Migration Mode** — 4 scenarios (normal, data moved, legacy, unknown)
  - RM-5: creates/updates storage pointer after migration
  - **Update mode**: added "Storage Location" option to change where data lives
  - All `~/.grow-pm/local-context.md` save references — user's storage location via pointer

---

## v1.7.0 (2026-04-15)

### What changed
Data persistence hardening: added pre-update backup protocol, Obsidian Vault mirror sync, and vault-based recovery to prevent data loss during plugin updates/reinstalls. Knowledge Library was lost during a plugin update — this release adds multiple layers of protection.

### Added
- **Pre-Update Backup Protocol** (persistent-storage.md) — automatic backup of all user data before plugin updates, with timestamped backup directories and manifests
- **Vault Mirror Protocol** (persistent-storage.md) — write-through replication of `~/.grow-pm/` to Obsidian Vault `_System/` and `Knowledge/` folders
- **Vault Recovery Protocol** (persistent-storage.md) — recovery from Obsidian Vault when `~/.grow-pm/` is lost
- **Knowledge Library vault sync** (knowledge-library SKILL.md) — automatic sync to vault after every write operation, plus recovery check at skill start
- **Plugin Configurator vault fallback** (plugin-configurator SKILL.md) — RM-0 pre-update backup, RM-1 vault recovery search, user prompt for vault path if data missing

### Changed
- **persistent-storage.md** — added Pre-Update Backup (PU-1—PU-4), Vault Mirror (VM-1—VM-3), Vault Recovery (VR-1—VR-3) protocols; strengthened deletion behavior section
- **vault-protocol.md** `1.0 → 1.1` — added Context Mirror to Vault section with sync triggers, algorithm, and recovery reference
- **plugin-configurator** `0.8.0 → 0.9.0` — added RM-0 (pre-update backup), RM-1 vault fallback search, RM-1a user vault path prompt, Step 13e vault mirror sync, U-4 vault mirror on update
- **knowledge-library** `0.2.0 → 0.3.0` — added Vault Mirror Sync section with post-write sync and recovery check at start

### Skills changed
| Skill | From | To | Change type |
|-------|------|----|-------------|
| plugin-configurator | 0.8.0 | 0.9.0 | minor — vault recovery + pre-update backup + mirror sync |
| knowledge-library | 0.2.0 | 0.3.0 | minor — vault mirror sync + recovery check |
| persistent-storage (ref) | — | — | minor — 3 new protocols (backup, mirror, recovery) |
| vault-protocol (ref) | 1.0 | 1.1 | minor — context mirror section |

---

## v1.6.0 (2026-04-14)

### Added
- **Obsidian Vault Integration (Phase 1)** — optional persistent knowledge graph for accumulating artifacts across sessions
  - New `references/vault-protocol.md` — shared protocol for vault detection, search, save, and MOC management
  - New `references/vault-schema.md` — frontmatter schema, type taxonomy (16 types), tag taxonomy, folder structure, templates
  - Multi-vault support with per-product vault binding
  - Three-level fallback: L0 (no vault), L1 (file system), L2 (file + Obsidian MCP)

### Changed
- **local-context-protocol.md** — added Step 0h (vault detection) and Step 0.5 (vault context search)
- **plugin-configurator** `0.7.0 → 0.8.0` — new Obsidian Vault section in Onboarding, Update, and Validate modes
- **cjm-research** `0.1.0 → 0.2.0` — added Step 1.5 (vault context) and Step 12.5 (vault save)
- **write-concept** `0.4.0 → 0.5.0` — added Step 0.5 (vault context) and Step 7.5 (vault save)
- **product-analysis** `0.5.0 → 0.6.0` — added Step 0.5 (vault context) and Vault Save with A/B test hypothesis lifecycle updates

---

## [1.5.0] — 2026-04-14

### What changed
- Added `cjm-research` skill (v0.1.0) — CJM pipeline orchestrator with 5 modes: anomalies (quick funnel check), hypotheses (improvement ideas with ICE + funnel impact), full (comprehensive analysis with verification, risk assessment, backlog), health-check (scheduled automated monitoring), comparison (cross-platform side-by-side analysis). Delegates to product-analysis, knowledge-library, product-research, and brainstorm-features. Assembles 5 report formats. Includes independent hypothesis verification (Step 10), risk assessment (Step 11), and post-report skill chaining.
- Updated `product-analysis` (v0.4.0 → v0.5.0) — added CJM Funnel Analysis mode: loads dashboard data per funnel stage, calculates per-stage conversion rates and deviations from baseline, detects anomalies with severity classification (Critical/Warning/Info/Positive per cjm-protocol.md), returns structured data to cjm-research. Added CJM-specific skill chaining offer.
- Updated `product-research` (v0.4.0 → v0.5.0) — added Knowledge Library as data source (search curated sources during research, include in output with trust scores). Added Knowledge Library availability check in Step 1. Added UX Benchmark Research type (benchmark matrix: practice, industry standard, current state, gap, priority). Added CJM Research chaining offer after UX benchmark research.
- Updated `brainstorm-features` (v0.4.0 → v0.5.0) — added CJM Hypotheses mode (Step 3C): generates hypotheses from CJM anomaly data with Data Trigger + Feedback Match + Heuristic Match format. Enhanced ICE scoring with stage-position multipliers (Stage 1: ×1.5, Stage 2: ×1.3, Stage 3: ×1.1, Stage 4+: ×1.0). Added funnel impact calculation per hypothesis. Added hypothesis categorization: Low-hanging fruit / Structural changes / Business logic changes. Added Situation D (invoked by CJM Research) to skip manual context gathering.

### Skills changed
| Skill | From | To | Change type |
|-------|------|----|-------------|
| cjm-research | — | 0.1.0 | new — CJM pipeline orchestrator with 5 modes and 12-step workflow |
| product-analysis | 0.4.0 | 0.5.0 | minor — added CJM Funnel Analysis mode (CJM-1 through CJM-5) |
| product-research | 0.4.0 | 0.5.0 | minor — added Knowledge Library source + UX Benchmark Research type |
| brainstorm-features | 0.4.0 | 0.5.0 | minor — added CJM Hypotheses mode (Step 3C) with funnel impact calculation |

---

## [1.4.0] — 2026-04-11

### What changed
- Persistent user data storage in `~/.grow-pm/` — all configuration, templates, and knowledge library data now stored in user's home directory, surviving plugin uninstalls, reinstalls, and updates
- Added Reinstall/Migration mode to Plugin Configurator — detects existing data, offers recovery/migration/fresh start
- Legacy data discovery and migration from workspace/session directories to `~/.grow-pm/`
- Knowledge Library storage path moved to `~/.grow-pm/knowledge-library/`
- Schema versioning with `.schema-version` file
- Auto-backups before migrations (keeps last 3)
- Updated knowledge-library (v0.1.0 → v0.2.0) — persistent storage, markdown table format, enhanced search modes
- Updated plugin-configurator (v0.6.0 → v0.7.0) — Reinstall/Migration mode, persistent storage protocol, validation report includes CJM and Knowledge Library readiness

### Skills changed
| Skill | From | To | Change type |
|-------|------|----|-------------|
| knowledge-library | 0.1.0 | 0.2.0 | minor — persistent storage in `~/.grow-pm/`, markdown format, enhanced modes |
| plugin-configurator | 0.6.0 | 0.7.0 | minor — Reinstall/Migration mode, persistent storage |

### References changed
| Reference | Change |
|-----------|--------|
| `persistent-storage.md` | new — persistent storage protocol, directory structure, migration |

---

## [1.3.0] — 2026-04-10

### What changed
- Added `knowledge-library` skill (v0.1.0) — local source management with trust scoring, multi-mode search (library, Confluence, Google Drive, Baymard, internet), and bulk import. Service skill for CJM enrichment with direct user management capabilities.
- Added `references/cjm-protocol.md` — shared CJM standards: anomaly severity levels, funnel impact calculation formula, health score formula, cross-platform comparison methodology, hypothesis verification checklist.
- Added `references/funnel-templates.md` — standard funnel stage templates for e-commerce, SaaS, marketplace, and custom product types with recommended metrics and anomaly thresholds.
- Updated `plugin-configurator` (v0.5.0 → v0.6.0) — added CJM Configuration (Step 9) with funnel template selection, stage-dashboard mapping, anomaly thresholds, and default analysis settings. Added Knowledge Library onboarding (Step 10) with source import, Baymard configuration, and search mode setup. Added CJM and Knowledge Library sections to Update, Validate, and View modes.
- Updated `references/local-context-protocol.md` — added Step 0f (CJM configuration check for CJM skills) and Step 0g (Knowledge Library availability check). Added CJM and Knowledge Library fields to context usage guidelines.

### Skills changed
| Skill | From | To | Change type |
|-------|------|----|-------------|
| knowledge-library | — | 0.1.0 | new — local knowledge source management with trust scoring and multi-mode search |
| plugin-configurator | 0.5.0 | 0.6.0 | minor — added CJM Configuration and Knowledge Library onboarding steps |

### References changed
| Reference | Change |
|-----------|--------|
| `cjm-protocol.md` | new — CJM shared standards |
| `funnel-templates.md` | new — funnel stage templates by product type |
| `local-context-protocol.md` | updated — CJM and Knowledge Library support |

---

## [1.2.1] — 2026-04-08

**Plugin summary:** Remove heading numbering from requirements-creator skill and template.

| Skill | Version | Change |
|-------|---------|--------|
| requirements-creator | 0.5.0 → 0.5.1 | Remove heading numbering |

### Details

**requirements-creator (v0.5.1)**
- Removed numbered `# | Section` column from the Step 4 template table — sections are now listed without sequential numbers
- Added formatting rule: headings must NOT be numbered (no "1. Epic", "2. Hypotheses" etc)
- Updated `references/requirements-template.md`: removed numbering from all section headings (e.g., "### 1. Epic" → "### Epic", "#### 5.1 Business Requirements" → "#### Business Requirements")
- Version bump: 0.5.0 → 0.5.1


## [1.2.0] — 2026-04-07

### Plugin
- Enhanced `diagram-prototyper` with Infographic creation support — new visualization type with 5 styles, built-in HTML/CSS generation, and data confidentiality handling

### Skills changed
| Skill | From | To | Change type |
|-------|------|----|-------------|
| diagram-prototyper | 0.6.0 | 0.7.0 | minor — added Infographic as new visualization type with full workflow support |

### Details
- **Step 1b — New visualization type:** Added **Infographic** to the type selection table alongside Diagram, Prototype, Mind Map, and Presentation. Examples: funnel metrics overview, feature comparison, onboarding steps, A/B test results summary, market research highlights
- **Step 1c — Infographic requirements gathering:** 6 targeted questions covering main message, data/metrics, target audience, intended use, key data points, and dimensions/format
- **Step 3b — Infographic style selection (new step):** 5 visual styles with context-based recommendations: Data-driven (metrics, KPIs), Process/timeline (flows, roadmaps), Comparison (feature eval, competitive), Informational/educational (product overviews), Statistical/report (quarterly data, surveys)
- **Step 4 — New tool: HTML/CSS (built-in):** Local generation of infographics as self-contained HTML files with inline CSS and SVG charts. No external LLM dependency. Added to tool recommendation table with 3 infographic-specific rows
- **Step 5 — Infographic prompt construction:** Detailed guidelines for headline, data points, visual hierarchy, section structure, chart types, icons, color scheme, dimensions, footer. Style-specific guidance for all 5 styles. Data confidentiality note: recommends HTML/CSS for infographics with sensitive metrics
- **Step 6a2 — HTML/CSS generation (new substep):** Full generation pipeline: fixed-width container, semantic sections, CSS Grid/Flexbox, inline SVG charts, CSS variables for color palette, system/Google fonts, @media print styles, HTML validation
- **Step 6g — Quality check updated:** Added "Data integrity" check row for infographics (numbers match source, charts proportional, units labeled)
- **Step 8e/8f — Publishing updated:** Added .html to local file formats. New Step 8f for additional infographic export (PNG, PDF, HTML)
- **Step 9 — Skill chaining updated:** New chaining path for infographics from product-analysis/product-research to Presentation Creator
- **Inbound chaining updated:** product-research and product-analysis now suggest infographics in their visualization offers
- **Quality standards updated:** Added HTML validity, self-containment, browser rendering, and data proportion accuracy requirements



## [0.9.0] — 2026-04-01

### Plugin
- Enhanced `meeting-processor` with calendar integration and enriched participant context

### Skills changed
| Skill | From | To | Change type |
|-------|------|----|-------------|
| meeting-processor | 0.8.0 | 0.9.0 | minor — calendar enrichment step + participant context passing |

### Details
- **Step M1d — Calendar enrichment:** After finding a meeting, optionally look up the matching calendar event (Google Calendar MCP or Microsoft Calendar MCP) to extract participants (with emails, roles, RSVP), agenda, attached documents (Google Docs, Confluence, Figma, presentations), organizer, and recurrence info. Reads attached materials for additional context
- **Enhanced M2 data merging:** Calendar data merged with transcript data using priority rules. Discrepancies marked (invited but silent, not invited but spoke)
- **Enhanced M9 skill chaining:** Full participant context (name, email, role, attendance status) now passed to all downstream skills. Per-skill content mapping ensures each target skill gets the data it needs (e.g., participants with roles for task assignment, speaker attribution for research)
- **MoM template updated:** Participants table now includes Email and Status columns

---

## [0.8.0] — 2026-04-01

### Plugin
- Added new skill **meeting-processor** — process meetings from any source to extract action items, decisions, and structured reports

### Skills changed
| Skill | From | To | Change type |
|-------|------|----|-------------|
| meeting-processor | — | 0.8.0 | new skill |

### Details
- **Two modes:** Process (single meeting → structured MoM or short summary) and Search (cross-meeting query → chronological synthesis)
- **Tool-agnostic input:** Fireflies MCP, other meeting tool MCPs, uploaded files (audio/video/text/srt), pasted text
- **Auto-classification:** 5 meeting types (Grooming, Discovery, Demo/Retro, Status, Brainstorm) with multi-type support, user confirmation
- **Type-adaptive extraction:** common blocks (participants, topics, decisions, action items, open questions) + type-specific blocks (estimates for grooming, quotes for discovery, etc.)
- **Skill chaining:** Grooming → feature-task-creator, Discovery → product-research/requirements-creator, Brainstorm → brainstorm-features, Any → diagram-prototyper
- **Publishing:** Confluence, Notion, local file

---

## [0.7.0] — 2026-03-31

### Plugin
- Enhanced `feature-task-creator` with two new workflow improvements

### Skills changed
| Skill | From | To | Change type |
|-------|------|----|-------------|
| feature-task-creator | 0.4.0 | 0.7.0 | minor — added Step 6b (field validation with user confirmation for uncertain values) and Step 12 (post-creation verification with auto-fix) |

### Details
- **Step 6b — Validate field values before creation:** Before creating tasks, the skill now categorizes each field value by confidence level (Certain / Inferred / Uncertain / Unknown), presents inferred values for confirmation, and asks the user for uncertain or unknown values with proposed options
- **Step 12 — Post-creation verification:** After creating all tasks, the skill reads back one task from Jira, runs 9 verification checks (title, parent, reporter, team, labels, components, description, issue type, links), reports discrepancies with severity, proposes fixes, and propagates fixes to all affected tasks

---

## [0.6.0] — 2026-03-30

### Plugin
- Added new skill **diagram-prototyper** — create diagrams, flowcharts, BPMN processes, mind maps, and UI prototypes
- Defined inbound skill chaining: write-concept, brainstorm-features, requirements-creator, product-research, product-analysis can now invoke diagram-prototyper

### Skills changed
| Skill | From | To | Change type |
|-------|------|----|-------------|
| diagram-prototyper | — | 0.6.0 | new skill |

---

## [0.5.0] — 2026-03-27

### Plugin
- Added **Analyze & Improve mode** to `requirements-creator` skill
- Translated `README.md` fully to English

### Skills changed
| Skill | From | To | Change type |
|-------|------|----|-------------|
| requirements-creator | 0.4.0 | 0.5.0 | minor — new Analyze & Improve mode added (A1—A9 workflow) |

---

## [0.4.0] — 2026-03-26

### Plugin
- Added versioning system for skills and plugin: `version` field in all SKILL.md frontmatter
- Added `CHANGELOG.md` (this file)
- Added versioning rules to `references/self-improvement.md`
- Added versioning protocol to `skills/plugin-configurator/SKILL.md` (step 4 — Implement improvement)

### Skills changed
| Skill | From | To | Change type |
|-------|------|----|-------------|
| brainstorm-features | 0.3.0 | 0.4.0 | minor — version field added |
| feature-task-creator | 0.3.0 | 0.4.0 | minor — version field added |
| plugin-configurator | 0.3.0 | 0.4.0 | minor — versioning protocol added |
| product-analysis | 0.3.0 | 0.4.0 | minor — version field added |
| product-research | 0.3.0 | 0.4.0 | minor — version field added |
| requirements-creator | 0.3.0 | 0.4.0 | minor — version field added |
| write-concept | 0.3.0 | 0.4.0 | minor — version field added |

---

## [0.3.0] — 2026-03-25

### Plugin
- Translated all skill instructions and reference files to English
- Output language remains controlled by `user.language` in `local-context.md`

### Skills changed
| Skill | From | To | Change type |
|-------|------|----|-------------|
| brainstorm-features | 0.2.0 | 0.3.0 | minor — full EN translation of workflow instructions |
| feature-task-creator | 0.2.0 | 0.3.0 | minor — full EN translation of workflow instructions |
| plugin-configurator | 0.2.0 | 0.3.0 | minor — full EN translation of all UI strings |
| product-analysis | 0.2.0 | 0.3.0 | minor — full EN translation of workflow instructions |
| product-research | 0.2.0 | 0.3.0 | minor — full EN translation of workflow instructions |
| requirements-creator | 0.2.0 | 0.3.0 | minor — full EN translation, requirements template translated |
| write-concept | 0.2.0 | 0.3.0 | minor — full EN translation of workflow instructions |

---

## [0.2.0] — 2026-03-25

### Plugin
- Added `plugin-configurator` skill with onboarding, update, validate, and view modes
- Added `local-context.md` support (org-specific config, gitignored)
- Added `references/local-context-protocol.md` — auto-trigger and enrichment protocol
- Added `references/self-improvement.md` — self-improvement protocol for all skills
- Added `references/context-schema.md` — full schema for `local-context.md`

### Skills changed
| Skill | From | To | Change type |
|-------|------|----|-------------|
| plugin-configurator | — | 0.2.0 | new skill |
| brainstorm-features | 0.1.0 | 0.2.0 | minor — local-context integration |
| feature-task-creator | 0.1.0 | 0.2.0 | minor — local-context integration |
| product-analysis | 0.1.0 | 0.2.0 | minor — local-context integration |
| product-research | 0.1.0 | 0.2.0 | minor — local-context integration |
| requirements-creator | 0.1.0 | 0.2.0 | minor — local-context integration |
| write-concept | 0.1.0 | 0.2.0 | minor — local-context integration |

---

## [0.1.0] — initial release

### Skills
- brainstorm-features
- feature-task-creator
- product-analysis
- product-research
- requirements-creator
- write-concept
