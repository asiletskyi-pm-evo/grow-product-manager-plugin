#!/usr/bin/env python3
"""ctx — the command line of the Grow PM context store (since v3.11.0).

  python3 ctx.py <command> [options] [--context PATH] [--store DIR] [--home DIR]

  status                        where the store is, records, card, edits waiting to be imported
  migrate [--apply]             split local-context.md into records (dry run unless --apply)
  compile                       import direct edits, then write both compiled copies and the card
  sync [--source S] [--reason R] [--resolve ID=file|record ...] [--accept-removals]
                                import direct edits to local-context.md into the records
  get ID [FIELD] [--json]       a record, or one `- **Field:** value`
  list [--type T] [--json]      records
  set ID FIELD VALUE            change or add a field line
  append ID --text T [--under "#### Heading"]   add a line (an identical line is not repeated)
  add TYPE TITLE [--parent ID] [--after ID] [--body-file F]   a new product, team, org, setting or custom record
  snapshot [--label L]          a snapshot of the store and both copies
  undo [--steps N]              back to the state before the N-th last change (N from 1); refused while
                                edits wait to be imported. The records it put back to the last compiled text
                                are named, and so are those it could not ("not put back …": check them).
                                Undoing a sync pass (journal op provider-sync) is final until the core changes
                                those blocks: for each block the pass took, the core's text (its hash, or "removed")
                                goes into the repository's block state as rejected — written after the restore — and
                                no sync applies it again, nor does `provider apply` unless told --choose BLOCK=theirs
                                ("не застосовуватиметься, доки ядро не змінить блок: <repo>: <blocks>"). Since v3.20.0
                                the notes `entity apply` wrote go back too («повернуто нотаток: N», «не повернуто: …»). CTX_RESULT:
                                rejected {repo: [blocks]}, rejected_failed {repo: why} (a state that could not take
                                it: the undo stands, and says the sync may apply the text again)
  read --skill S [--product P]  the card plus what the skill's manifest entry names (reads only)
  explain [SLOT …] [--skill S] [--product P] [--json]
                                where each slot came from and why it won (since v3.15.0; reads only — no lock, no network,
                                nothing written). Per slot a header (slot · kind · record) and a line for each candidate —
                                ✔ shown (yours, or a block with its repository, version and day of the last check), ✗ lost
                                (with the reason), ⚠ divergence between repositories (with `ctx slot decide`), · a block that
                                cannot be given to one team (with `ctx slot bind … --team`) — then `чому:`; a slot nobody
                                answers says what it looked for and prints `ctx slot map`; what you decided about the slot
                                is shown with `ctx slot forget`. SLOTs: only those; --skill S: the slots S asks, in the
                                manifest's order and lookup mode; neither: every slot with a candidate, then the blocks no
                                slot takes (a region of a registered repository with no binding) and the blocks of
                                `skip_blocks`. With several products and none named the slots of a product and of a team are
                                held back (needs_product). An unknown slot or skill is exit 3. CTX_RESULT: slots [{slot,
                                kind, about, record, title, winner, candidates [{source, record, block, sub, version, checked,
                                edited, rule, how, rank, outcome won|lost|shown|diverges|unplaced, reason, command}], why,
                                prefer, looked_in {names, records}, commands, decision, memory, notes}], unmapped_blocks,
                                skipped_blocks, needs_product, products, warnings
  invalidate ID --reason R      mark a record no longer current (it stays, with a status region)
  archive ID [--reason R]       move a record to the archive; restore ID brings it (or a trashed one) back
  verify [ID ...] [--stale]     mark records verified today
  validate                      records, ids, parents, card size, edits waiting; since v3.15.0 also slots (reads only): a slots
                                memory that cannot be read is an error (exit 3); warnings name each binding that does nothing
                                (`slot binding: <repo> <block>[#<sub>] → <slot> — <why>`: a slot the catalogue lacks, a
                                repository nobody registered, a block gone from the records, a block that gives its slot no
                                text, a team slot's block that cannot be given to one team), each divergence between repositories
                                (`slot <slot> diverges between <a>, <b> — ctx slot decide <slot> <repo>`) and each binding worth
                                making (`proposal: ctx slot bind <repo> <block>[#<sub>] <slot>`: an unbound block of a registered
                                repository whose heading answers a slot's names; never the plugin's `team` block). CTX_RESULT
                                adds slot_proposals [{repo, block, sub, slot}]
  bootstrap --observed F [--apply --code C [--take N,…] [--skip N,…] | [--only N,…]] [--json]
                                since v3.22.0: an observation file (references/context-observe.md) against your context —
                                one table, read only; --apply writes the rows taken (a snapshot, the records, the sources of
                                each field, the low facts as ctx-bootstrap inbox deltas); a new user's local-context.md from
                                the onboarding skeleton, moved into records (context-protocol.md §5k)
  validate --recheck --observed F
                                since v3.22.0: the records against the connectors; a finding becomes a ctx-recheck delta
                                only on a second look 6+ days later — the look's day is the file's `at` (§5l); writes the
                                inbox and .state/recheck.json
  consolidate [--now ISO]       since v3.22.0: duplicates, relative dates, passed deadlines → ctx-consolidate REPLACE deltas;
                                no record written (§5m)
  card                          regenerate INDEX.md only
  repo list [--json]            the repositories (provider registrations) a product draws context blocks
                                from: kind, products, rank, access and, from the block state, how many blocks you
                                hold a base for, their base version and the day of the last check ("—" before
                                `provider adopt`, "!" when the state cannot be read) — local files, no network
  repo status [ID] [--json]     is each repository reachable (an MCP server answers the handshake within 3 s;
                                a folder is there) and its version on the source against the base — the only
                                repo command that touches the network: the handshake, then one read of the blocks
                                file for the version ("—" and the reason on a "blocks file:" line when it could
                                not be read; the team block is not built for it). It exits 0 also when a repository
                                is unreachable. An unknown ID is exit 3 — "it may still be downloading" when a
                                registration could not be read
  provider adopt REPO [--apply] [--json]
                                a base for each block of REPO that is already in your context (dry run unless
                                --apply): the blocks the repository publishes at the version you hold are taken
                                as they are (an edit of yours counts as your edit); another version gets no base.
                                With --apply it first imports the edits waiting (as every writing command does),
                                then writes the block state and the card's Repos line — no block text, no record
  provider plan [REPO] [--product P] [--all] [--json]
                                one table per repository: what each block is in your context against what the
                                repository publishes now (= ~ ✎ ⚠ + − ✂ ?), the questions and the records an apply
                                would rewrite. Without REPO: the repositories of the product P (matched as `read`
                                matches it), else all of them. --all also lists the blocks a repository skips.
                                Reads only — no lock, nothing written; an unreachable repository — or one whose
                                blocks file is empty, cut, foreign or holds none of the blocks you have a base
                                for — exits 5 (the others still print). CTX_RESULT: with REPO the plan itself
                                (rows, questions, changes, errors …), without it {repos: [plan …], paused,
                                search_only, questions, changes}. Without REPO a paused repository is left out,
                                with one line "призупинено: <id>", and a search-only registration (no
                                blocks_file, no core folder) with "лише пошук: <id>"; naming one is exit 3
  provider apply [REPO] [--product P] [--choose BLOCK=theirs|mine|both [BLOCK=… …]] [--add BLOCK [BLOCK …]] [--json]
                                one pass per repository: = ~ ✎ − ✂ are applied (your edits stay), ⚠ and ? wait
                                for --choose, + for --add (it goes to the record holding most of the repository's
                                blocks, else a new record); a ✎ takes --choose BLOCK=theirs (the repository's
                                text, and its base; mine or both for a ✎ is "не потрібне"). A text you rejected
                                by undoing a sync pass is held ("утримано: …"), never re-applied, unless taken:
                                --choose BLOCK=theirs (any sign), --add for a +, any answer for a ⚠ or ?. The
                                snapshot, the records, the block state, one journal line (taken: the repository
                                texts written), the compile. Nothing moved: only the time of the check, "без змін".
                                Every repository is read first: one unreachable → exit 5, nothing written; an answer
                                for a block its plan does not have → exit 3, before the lock: nothing imported.
                                Exit 2 when an answer is awaited (the rest applied), 4 when only refused blocks
                                (a broken marker) are left. --choose / --add need REPO when several are in scope;
                                REPO comes first — a word with "=" in its place is exit 3, and the word after the
                                answers is read as one of them (without REPO, one that names a registered repository
                                is exit 3, in --product's scope or not). An answer for a block with a broken marker
                                is not applied ("не застосовано").
                                CTX_RESULT: the plan with applied, decisions, pending, ignored, held, written, snapshot
  provider sync [REPO] [--if-due] [--now ISO]
                                the daily sync (since v3.14.0): the repositories whose registration says `sync: daily`
                                (REPO names one of them; another is exit 3), each brought up to date with no question —
                                yours kept on a ⚠ unless the core marks the block a rule, + added, more than one − held,
                                ? left waiting, a text you rejected by undoing a pass held. --if-due first keeps only the
                                repositories due — a day after their last successful check, an hour after a failed
                                attempt — reading their block state alone (no lock, no network); none → only CTX_RESULT.
                                The lock held by another session: nothing, at once (skipped: busy; a lock that cannot be
                                taken: lock: <why>; a guard that refuses: guard: <why>); --if-due checks again under the
                                lock. The edits waiting are imported first (a conflict: import-conflict, nothing
                                written). 20 s for every repository together, the last 1 s kept for writing down the
                                results; no fetch, plan or write starts with less than 3 s left before that, and a
                                write once begun has those 3 s for its reads. Outcomes:
                                changed, no-changes, held, broken (an empty, cut or foreign blocks file — retried in a
                                day), unreachable, timeout, import-conflict, error (retried in an hour).
                                One line per repository the pass changed: «Ядро оновило N блоків у <repo>, конфліктів K
                                (лишено твоє)». Exit 0 whatever happened (3: bad usage). CTX_RESULT: synced (ids),
                                results [{repo, at, outcome, updated, added, removed, kept_yours, took_rule, awaiting, held,
                                held_behind, rejected, reason, report, snapshot}] — the same as the block state's sync_result
  slot bind REPO BLOCK[#Subsection] SLOT [--team ID]
                                what you decided about the slots of the catalogue (references/context-slots.yaml;
                                since v3.15.0), kept in the store's `.state/slots.json` — no record changes. bind: the
                                block (or its subsection) of a registered repository answers for SLOT; for a team.*
                                slot --team names the team record it is for (a record of type team)
  slot map RECORD "Heading" SLOT
                                your own subsection "Heading" in the record RECORD answers for SLOT (a record of the
                                kind the slot is looked for in)
  slot prefer SLOT mine|repo:ID|all
                                whose answer SLOT gives first (mine: yours, the default; repo:ID: one repository's)
  slot decide SLOT REPO [--product P]
                                the answer to a divergence between repositories (since v3.15.0): two or more of them tie
                                at the highest rank with different text for SLOT, and you have no text of your own for it,
                                no core rule and no preference — REPO's text wins. Kept with the hash of every side's
                                text (a value slot: the value) and the day; a new text from any side asks again. SLOT is
                                computed on the records as they are now, for the product P (a product or team slot with
                                several products needs --product; an organisation slot does not)
  slot forget SLOT              everything the memory holds about SLOT: bindings, names, preference, decision
                                All five: snapshot, one journal line (op slot, action, slot), `ctx undo` takes it back;
                                one that changes nothing (the same bind again) says "unchanged" — no snapshot, no line.
                                An unknown slot, repository, record or block id, a --team that is not a team record, a
                                record of another kind than the slot's, a preference that is none of the three, a
                                `decide` with no divergence ("no divergence for SLOT") or for a REPO that is not one of
                                the sides, and a memory that cannot be read ("slots memory not readable|not valid:
                                .state/slots.json (…)") are exit 3. CTX_RESULT: action, slot, changed, snapshot, memory (after)
  index status | index rebuild [--download]
                                the section index of the search (since v3.16.0; scripts/ctx_index.py): the plugin folder of
                                every vault and the core folder of every registration that has one on disk, in
                                `<home>/.grow-pm/index/` — no store lock, nothing written anywhere else. status: an
                                incremental refresh (30 s; a held index.lock: none, the index as it is), then the counts;
                                rebuild: the index built again from nothing, no time limit. "індекс оновлюється: N файлів ще
                                не переглянуто" when the refresh ran out of time. rebuild --download (since v3.16.1) first
                                brings down the plugin folder's files iCloud evicted that the index would read — never a
                                core folder or the rest of a vault; no limit on the run, 30 s a file, 4 at once, minutes
                                for a large vault, «iCloud: N з M…» every 100 files and at least once a minute — then
                                «iCloud: завантажено N з M[, лишилось K (не встигли за 30 с: T; не прочитано: F)]» (a
                                reason only when not zero) or «iCloud: нічого завантажувати», then the rebuild; the index
                                lock is checked first; Ctrl-C at any moment: «…, зупинено (Ctrl-C) — індекс не
                                перебудовано», exit 130, the running reads killed. Nothing else ever downloads; status
                                says «(plugin folder: K — ctx index rebuild --download)» when K evicted files lie in a
                                plugin folder. No vault and no core folder: exit 3; rebuild while another process holds
                                index.lock: exit 4. CTX_RESULT: action, schema, updated, files, sections, pending,
                                skipped_dataless, download (with it, an index error too)
  search --q TEXT [--q TEXT …] [--skill S] [--product P] [--limit N] [--sources own,local,mcp] [--no-hints] [--json]
                                (since v3.16.0; scripts/ctx_search.py) the first --q is the question, the others its
                                variants: the section index (refreshed first, 30 s), the local indexes and the MCP of a
                                repository with no folder on disk, every variant × source; RRF, the priors, one candidate per
                                note (at most two sections), the best N (30). Lines: `Пошук: <n> варіант(и) · джерела: <ids> ·
                                кандидатів <k>`, per candidate `N. <title> › <heading> · <sources> · <type> · <date>[ ·
                                <mark>…]`, its snippet, `id <id> · варіанти <i,…>`, then the notes (a source that did not
                                answer, the index's state). --json: CTX_RESULT only. CTX_RESULT: candidates, notes, sources
                                [{id, kind, answered}], index, counts. No --q (and no --get), a bad --sources/--limit/--skill,
                                or nothing to search (no vault, no repository, no source): exit 3; no source answered (the
                                own index busy or damaged counts as not answered): exit 5; 0 candidates is exit 0. No store
                                needed. The ids are merged into <home>/.grow-pm/index/last.json (a save that fails is a line,
                                never the exit code). A candidate's sources name the repository of a core page.
  search --get ID|PATH|NAME [--json]
                                one section of the last searches (or of the section index, by its id — an id neither
                                has is tried as a name); for a note's path or its name, as a hub links it (`Name`,
                                `Name.md`, `[[Name]]`, `[[Name|alias]]`, `![[Name]]`, `[[Name#H1#H2]]`, `[[Name#^block]]`;
                                a link with a folder is a path, else taken as the end of a path — the plugin folder's
                                first; a path first — a note at a vault's root is `<name>.md` — a name when no source
                                holds that path), the whole note without its frontmatter — first from the server for
                                a name only a server holds now (`@<repo>/…` of a repository with no folder on disk,
                                `@<repo>/:/…` outside its root, a path under a registered core folder gone from disk;
                                since v3.16.2), else the section index, else its file when it is on disk and
                                downloaded, else a local index's body;
                                `<path>#<heading>` or `[[Name#Heading]]` gives that section:
                                `> [<source> · <path> › <heading> · <day>]` and its text (an MCP note through vault_get_note).
                                A section under 200 characters goes on with the next ones, up to 1 500, after
                                the line `секція коротка — додано наступні: <headings>`. Any form gives 20 000
                                characters at most (since v3.16.1; --full: 60 000, for a note taken as «прямо»), then
                                `нотатка довга — показано 20 000 знаків із <усього>; далі: <headings> — --get
                                "<шлях>#<заголовок>" або --full (до 60 000)` (or `заголовків далі немає`; after --full
                                the hint is `--get "<шлях>#<заголовок>" --full`); --full
                                goes with --get alone (else exit 3). A file is read within the read
                                budget, and one iCloud has not downloaded never: the text of a registered local index,
                                after the line `файл не завантажено з iCloud — текст із локального індексу <id>`, else
                                exit 3 (`файл не завантажено з iCloud: <path> — відкрий його в Obsidian або ctx index
                                rebuild --download`; outside a plugin folder `… — відкрий його в Obsidian` alone). An
                                unknown id, note, name or section, a file not read in time, a name several notes carry
                                (`кілька нотаток із назвою «<назва>»: <шляхи> — --get один зі шляхів`; for the end of a
                                path `кілька нотаток, чий шлях закінчується на «<посилання>»: <шляхи> — --get один зі
                                шляхів`) or a path the search excludes (`шлях виключено з пошуку: <шлях>`): exit 3;
                                the server did not answer: exit 5. --json: the header and the text in CTX_RESULT only
  search remember --q REQUEST --pick ID|PATH [--not ID|PATH] [--product P]
  search forget --q REQUEST [--product P]
                                (since v3.16.0; scripts/ctx_hints.py) your choices in a search's block of options, kept in
                                the store's `.state/search.json` (context-search-memory/1): for the request (the first --q;
                                its stems — the same words in another order or form are the same request) and the product,
                                --pick is right and --not is not (an ID of the last searches is its section, `path#heading`;
                                else a note's path). A later search whose request is similar (Jaccard of the stems ≥ 0.6) and
                                whose product does not differ weighs a pick × 1.5, marked `твій вибір від <день>`, and marks a
                                --not `ти казав «не те»`; --no-hints searches without them; a memory that cannot be read is
                                one line («пам'ять пошуку не прочитано (…) — без підказок»), never the search. forget drops
                                the request's hints (of P only, when named). Writing commands: snapshot, one journal line (op
                                search, action, q), `ctx undo` takes it back; one that changes nothing says "unchanged". No
                                store («немає сховища — підказку не збережено»), an id no search gave, a request of stop words
                                only, no --pick and no --not, or a memory that cannot be read ("search memory not
                                readable|not valid: .state/search.json (…)"; the file is never rewritten): exit 3. CTX_RESULT:
                                action, q, product, good, bad, changed, hints, snapshot
  search eval [--golden PATH] [--no-hints] [--sources …] [--json]
                                the search measured on a golden set (search-golden/1): the store's `search/golden.yaml`
                                unless --golden names one (no store: --golden is needed), plus the hints of the memory as rows
                                `source: choice` (class вибір) unless --no-hints. Each row with an answer is searched with its
                                frozen variants and with its question alone (the first 50, its product and skill); an empty
                                row (class порожній) counts the candidates of its top 5. Lines: the set, recall@50 (q +
                                варіанти, лише q), MRR, a line per class, the empty rows, the rows not found. Writes nothing
                                but the index. No golden set, one that does not read, nothing to search: exit 3. CTX_RESULT:
                                n, recall50, recall50_q_only, mrr, by_class, empty_n, empty_top5_mean, rows, hints, golden
  entity <request…> [--kind K] [--skill S] [--slot SLOT …] [--json]    |    entity --q REQUEST [--q REQUEST …] …
                                (since v3.18.0; scripts/ctx_entity.py) who someone or something is: the request is an
                                e-mail, a Jira key, a card's path or link, a name or an alias, else a card alike; --kind
                                person|team|mission|module|metric|work keeps one kind; --q for a request that is a word of
                                an action (`pairs`, `same`, `not-same`). The index refreshed first (30 s), then the
                                registry: the cards of the own index and of every registered local index, joined by your
                                answers, the e-mail and a bridge by its shape — never by a name. One entity: its cards
                                with their source, its identity (e-mail, team, role — nothing else), what it is related
                                to, the cards that may be the same, who links to it and the notes that carry a work
                                entity's key (newest first, 20 at most) — a sensitive note as its title and path with
                                ` · sensitive`, its field only for a People-contour --skill; never a note's text. Several:
                                `<label> · <kind> — ctx entity "<path>"` (5 at most). A Jira key no card holds:
                                `<KEY> — картки немає, згадується в N нотатках:` when its prefix is one the cards name or
                                a /browse/ link names it; else `Не знаю такої сутності: «…»` (`Поки не знаю «…» — індекс
                                оновлюється: …` while the index has files to look at). Writes only the index. An unknown
                                --skill or --kind: exit 3; nothing to search: exit 3; no base answered: exit 5 (`Базу не
                                прочитано: …`). CTX_RESULT: query, how, entities, mention, several, notes.
                                Since v3.19.0 (scripts/ctx_eslots.py): one entity's `слоти:` — a person's role, team and
                                e-mail, a team's members, missions and parent, a mission's teams and Jira projects, an owner —
                                each with its origin (yours, a repository's, a local index's, derived) and its «також»; a
                                list one item per entity. --slot SLOT (repeatable) keeps those slots alone, no backlinks nor
                                mentions; an unknown one: exit 3. --q repeated: one refresh, a block per request
                                (CTX_RESULT requests). A local index's own entities/edges are hints: pairs `(підказка <id>)`,
                                backlink lines ` · <id>` (links and `fm:` edges only) — never a merge. CTX_RESULT adds
                                entities[].slots ({slot: value answer {value, entity?, origin, also, diverges, why} or list
                                answer {items, count, why}}), entities[].slots_asked, maybe[].hint, backlinks.items[].via;
                                `pairs`: pairs[].hint. --slot with pairs, same or not-same: exit 3. A sensitive team's,
                                mission's or metric's card gives outside the People contour its members' names and
                                sources alone
  entity pairs [--kind K] [--json]
                                every open pair «можливо той самий» (two cards of one kind from different sources whose
                                names are alike, not answered yet). Writes only the index
  entity apply [--kind K] [--json]
                                since v3.20.0: the bridges your notes lack — a card of yours an e-mail or your `same`
                                joins to a card of another source, with no bridge yet, gets `same_as: "[[<card>|<title>]]"`
                                (context-protocol §5h). A report: `запишу N мостів:`, what is skipped and why, `код звіту:
                                <8 hex>`; writes only the index. No code when your answers or notes iCloud keeps (and no
                                local index gives) cannot be read
  entity apply --apply --code C
                                writes that report alone into your plugin folder — one frontmatter line per note, in place,
                                after a snapshot of the notes; `.state/bridges.json` and one journal line (op entity-apply);
                                `ctx undo` takes it back. Another code: exit 4; --apply without --code, --code without
                                --apply, no store or no code: exit 3; the index not read: exit 5. CTX_RESULT: rows
                                (written), planned, skipped, snapshot
  entity same|not-same A B      your answer: A and B (a card's path or link, or a name one card alone carries) are, or are
                                not, the same — kept in the store's `.state/entities.json` (context-entity-memory/1), the
                                opposite answer replaced; `not-same` keeps them apart whatever the e-mail or a bridge
                                says. A writing command: snapshot, one journal line (op entity, action, cards), `ctx undo`
                                takes it back; one that changes nothing says "unchanged". No store («немає сховища —
                                відповідь не збережено»), a name several cards carry, two kinds, or a memory that cannot be
                                read: exit 3. CTX_RESULT: action, cards, changed, snapshot

`read` and `explain` take no lock and write nothing; `index`, `search` (but `search remember|forget`) and `entity` (but
`entity same|not-same` and `entity apply --apply`) take no store lock and write only the index's folder.
Every writing command takes the lock, refuses a store inside a provider's folder (and, since v3.14, a run when a
registration is not read in time — 3 s each, 6 s for all: the boundary cannot be checked, exit 4), imports direct
edits first, snapshots, writes, journals and compiles (`provider adopt --apply` imports first too, and then
writes only the block state under `.state/blocks/` and the card's Repos line; `slot` imports first too, and then
writes only `.state/slots.json` — no record, no copy, no compile). Files are read within a time budget
(GROW_PM_CTX_READ_TIMEOUT, default 30 s): a record that does not arrive (iCloud) or is missing
on disk stops the run before anything is written. A writing command that exits 0 then saves the
session digest's summary of the store beside the context (`~/.grow-pm/.ctx-summary.json`, since v3.13.1), counted
on the digest's own budget (2 s, then 0.5 s for the days of the last checks; a count that misses it saves nothing);
a summary that cannot be saved never changes the exit code. The last stdout line is `CTX_RESULT {json}`;
a conflict prints `CTX_CONFLICT {json}` before it. Exit: 0 ok · 2 conflict · 3 bad input, no store,
unreadable record · 4 refused (managed region, provider boundary, busy lock, store exists) ·
5 a repository is unreachable, or its blocks file is no source (empty, cut, foreign, or none of your based blocks)
— nothing written (provider commands); for `search` and `entity`, no source answered. `provider apply`: 2 also means answers are
awaited.
Semantics: references/context-protocol.md. Stdlib only.
"""
import argparse
import datetime
import json
import os
import re
import sqlite3
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx_backups as cbk  # noqa: E402
import ctx_blocks as cb  # noqa: E402
import ctx_bootstrap as cbt  # noqa: E402
import ctx_bridges as cbr  # noqa: E402
import ctx_common as cc  # noqa: E402
import ctx_consolidate as ccn  # noqa: E402
import ctx_copy as ccp  # noqa: E402
import ctx_entity as ce  # noqa: E402
import ctx_graph as cg  # noqa: E402
import ctx_audit as ca  # noqa: E402
import ctx_normalize as cnz  # noqa: E402
import ctx_eslots as es  # noqa: E402
import ctx_hints as ch  # noqa: E402
import ctx_history as chi  # noqa: E402
import ctx_identity as cid  # noqa: E402
import ctx_kit as ckit  # noqa: E402
import ctx_inbox as ci_  # noqa: E402
import ctx_index as ci  # noqa: E402
import ctx_never as cn  # noqa: E402
import ctx_observe as cob  # noqa: E402
import ctx_store as cs  # noqa: E402
import ctx_ops as co  # noqa: E402
import ctx_overlay as ov  # noqa: E402
import ctx_read as cr  # noqa: E402
import ctx_recheck as crk  # noqa: E402
import ctx_repos as crp  # noqa: E402
import ctx_resolve as rv  # noqa: E402
import ctx_search as cs_  # noqa: E402
import ctx_schema as sc  # noqa: E402
import ctx_show as csh  # noqa: E402
import ctx_slots as sl  # noqa: E402
import ctx_sources as csrc  # noqa: E402
import ctx_synced as sy  # noqa: E402

HEADINGS = {"product": "### Product: %s", "team": "### Team: %s", "org": "## Organization: %s",
            "setting": "## %s", "custom": "## %s"}


class Usage(Exception):
    pass


WRITING = {"compile", "sync", "set", "append", "add", "snapshot", "undo", "card",
           "invalidate", "archive", "restore", "verify", "assign", "slot"}


# The arguments of a writing command that are no free text a store keeps: paths, ids, numbers, the propose's deltas
# (each one checked on its own, so one secret does not cost the others — ctx_inbox.propose).
NOT_TEXT = {"cmd", "action", "context", "store", "home", "file", "body_file", "delta", "code", "which", "steps", "id",
            "ids", "skill", "type", "parent", "after", "repo", "product", "label", "now", "observed", "take", "skip",
            "only", "bundle", "folder", "email"}


def _free_text(a):
    out = []
    for k, v in vars(a).items():
        if k in NOT_TEXT:
            continue
        for x in (v if isinstance(v, list) else [v]):
            if isinstance(x, str):
                out.append(x)
    return out


def writes(a):
    """Does this run write to the store? Every command of WRITING does, and `provider apply`, `provider sync` and (since
    v3.16.0) `search remember|forget`, (since v3.18.0) `entity same|not-same`; `migrate`, `provider adopt` and (since
    v3.20.0) `entity apply` only with --apply. A plain search, `--get` and `search
    eval` write no store. (A `provider sync` that synced nothing saves no summary: `main`.)"""
    if a.cmd == "snapshot" and getattr(a, "action", None) == "import":
        return getattr(a, "apply", False)
    if a.cmd in WRITING or (a.cmd == "provider" and getattr(a, "action", None) in ("apply", "sync")):
        return True
    if a.cmd == "search" and getattr(a, "action", None) in ("remember", "forget"):
        return True
    if a.cmd == "propose" or (a.cmd == "inbox" and getattr(a, "action", None) in ("accept", "reject")):
        return True
    if a.cmd == "bootstrap":                            # since v3.22.0: the table only with --apply
        return getattr(a, "apply", False)
    if a.cmd == "validate":                             # since v3.22.0: --recheck writes the inbox and its memory
        return getattr(a, "recheck", False)
    if a.cmd == "consolidate":                          # since v3.22.0: the inbox only
        return True
    if a.cmd == "repo" and getattr(a, "action", None) == "add":     # since v3.23.0: only with --apply
        return getattr(a, "apply", False)
    if a.cmd == "identity":                             # since v3.23.0: check reads only
        return getattr(a, "action", None) in ("keep", "take")
    if a.cmd == "overlay":                              # since v3.23.0: show and plan read only
        return getattr(a, "action", None) in ("apply", "add", "rm", "answer")
    if a.cmd == "entity" and _entity_action(a)[0] in ("same", "not-same"):
        return True
    if a.cmd == "entity" and _entity_action(a)[0] == "apply":
        return getattr(a, "apply", False)
    if a.cmd == "vault":                                # since v4.0.0: normalize writes only with --apply
        return getattr(a, "apply", False)
    if a.cmd == "migrate" or (a.cmd == "provider" and getattr(a, "action", None) == "adopt"):
        return getattr(a, "apply", False)
    return False


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise Usage(message)


def now():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


class Ctx:
    def __init__(self, a):
        if a.store and writes(a):
            raise Usage("--store is for read commands only; writing commands use the context's own store")
        self.home = a.home or os.path.expanduser("~")
        found = cc.find_context(a.context, home=self.home)
        self.fresh = False                       # since v3.22.0: `bootstrap` of a new user — no local-context.md yet
        if not found and a.cmd == "bootstrap":
            found = os.path.expanduser(a.context or os.environ.get("GROW_PM_CONTEXT_PATH") or
                                       os.path.join(self.home, ".grow-pm", "local-context.md"))
            self.fresh = not os.path.lexists(found)
        if not found:
            raise cs.StoreError("no such file: %s (--context)" % a.context if a.context else
                                "no local-context.md found (GROW_PM_CONTEXT_PATH, ~/.grow-pm)")
        self.found = found                       # as found, links not followed: the digest's summary is kept beside it
        self.context = os.path.realpath(found)
        self.text = "" if self.fresh else co._read(self.context)
        self.store = cs.Store(a.store or co.store_root_for(self.text, self.home))
        self.copies = co.copies_for(self.context, self.text, self.home)

    def need_store(self):
        if not self.store.exists():
            raise cs.StoreError("no store at %s — `ctx migrate` shows the move" % self.store.root)

    def guard(self):
        """Before any write, under the lock: the store is not inside a provider's read-only folder, and none of the paths
        it writes is refused (cs.check_target). The registrations are read on the boundary's budget (since v3.14: 3 s each,
        6 s for all — `cc.boundary_registrations`); one not read in time may be the provider whose folder holds the store,
        so that is a refusal too (co.Refused, exit 4): "a registration could not be read: <path> — the provider boundary
        cannot be checked; try again when it has downloaded"."""
        regs, late = cc.boundary_registrations(cc.vault_entries(self.text),
                                               extra_dirs=[os.path.join(self.home, ".grow-pm", "providers")])
        hit = cc.boundary_hit(os.path.join(self.store.root, "records", "x.md"), regs)
        if hit:
            raise co.Refused("the store %s lies inside the provider %s's folder" % (self.store.root, hit.get("id")))
        if late:
            raise co.Refused("a registration could not be read: %s — the provider boundary cannot be checked; "
                             "try again when it has downloaded" % ", ".join(late))
        for p in list(self.copies) + [self.store.root, self.store.records_dir, self.store.state_dir, self.store.card_path]:
            cs.check_target(p)
        co.purge_trash(self.home)

    def import_first(self):
        return co.apply_sync(self.store, co.plan_sync(self.store, self.copies), self.copies, self.home, None, "", now())


# ------------------------------------------------------------------ commands
def cmd_status(a, c):
    if not c.store.exists():
        if os.path.isdir(c.store.records_dir):
            print(co.half_migrated(c.store.root))
            return 3, {"command": "status", "store": None, "half_migrated": True}
        print("no store at %s — local-context.md is a single file; `ctx migrate` shows the move" % c.store.root)
        return 3, {"command": "status", "store": None}
    recs = c.store.load()
    plan = co.plan_sync(c.store, c.copies)
    pending = co.pending(plan)
    card = co._read(c.store.card_path).count("\n") if os.path.isfile(c.store.card_path) else 0
    tail = c.store.journal_entries()[-3:]
    stray = c.store.stray_files()
    stale = sc.stale_ids(recs, c.store.state(), now()[:10])
    invalid = [r["id"] for r in recs if cs.has_status_region(r["body"])]
    archived = len(c.store.archived())
    snaps = os.path.join(c.home, ".grow-pm", "snapshots")
    last = sorted(n for n in os.listdir(snaps) if co.SNAP_RE.match(n) and not co.IMPORTED_RE.match(n))[-1:] \
        if os.path.isdir(snaps) else []
    print("store: %s · records %d · card %d lines" % (c.store.root, len(recs), card))
    print("freshness: %d stale · %d invalid · %d archived" % (len(stale), len(invalid), archived))
    print("last snapshot: %s" % (last[0] if last else "none"))
    print("to import: " + (", ".join("%s %d" % kv for kv in pending.items() if kv[1]) or "nothing — in sync"))
    for x in plan["conflicts"]:
        print("conflict: %s (%s)" % (x["id"], "; ".join(x["reasons"])))
    if plan["missing"]:
        print("missing on disk (not downloaded, not synced or deleted): %s — `ctx sync` says what to do"
              % ", ".join(i + ".md" for i in plan["missing"]))
    lonely = cs.unassigned_ids(recs)
    if lonely:
        print("custom without read_by: %s — ctx assign <id> all|<skills>" % ", ".join(lonely))
    for s in stray:
        print("stray file (ignored): %s" % s)
    for j in tail:
        print("journal: %s %s %s" % (j.get("ts", ""), j.get("op"), j.get("source", "")))
    return 0, {"command": "status", "store": c.store.root, "records": len(recs), "card_lines": card,
               "pending": pending, "conflicts": [x["id"] for x in plan["conflicts"]], "missing": plan["missing"],
               "stray": stray, "journal": tail, "stale": stale, "invalid": invalid, "archived": archived,
               "last_snapshot": last[0] if last else None, "unassigned": lonely}


def cmd_migrate(a, c):
    if a.apply:
        with co.lock(c.home):
            c.guard()
            rep = co.migrate(c.context, c.store.root, c.copies, c.home, True, now())
    else:
        rep = co.migrate(c.context, c.store.root, c.copies, c.home, False, now())
    print("store: %s" % rep["store"])
    print("round trip: %s" % ("identical" if rep["identical"] else "DIFFERENT — not migrating"))
    for r in rep["records"]:
        print("  %-48s %-10s %4d lines" % (r["id"], r["type"], r["lines"]))
    if rep["custom"]:
        print("not in the schema, kept as is: " + ", ".join(rep["custom"]))
    if rep["mirror_differs"]:
        print("the vault mirror differs from %s — the first compile rewrites it, after a snapshot" % c.context)
    print("migrated" if rep["applied"] else "dry run — nothing written; `ctx migrate --apply` moves it")
    return (0 if rep["identical"] else 3), dict(rep, command="migrate")


def _resolve(items):
    out = {}
    for it in items or []:
        rid, _, how = it.partition("=")
        if how not in ("file", "record") or not rid:
            raise Usage("--resolve takes ID=file or ID=record, not %r" % it)
        out[rid] = how
    return out


def cmd_sync(a, c, source=None):
    if not c.store.exists():
        if a.cmd == "sync":
            print("nothing to sync — no context store")
            return 0, {"command": "sync", "store": None}
        c.need_store()
    with co.lock(c.home):
        c.guard()
        plan = co.plan_sync(c.store, c.copies)
        res = co.apply_sync(c.store, plan, c.copies, c.home, source or getattr(a, "source", None),
                            getattr(a, "reason", None) or "", now(), resolve=_resolve(getattr(a, "resolve", None)),
                            accept_removals=getattr(a, "accept_removals", False))
    comp = res.get("compiled") or {}
    print("imported: %d changed, %d new, %d removed%s" % (len(res["changed"]), len(res["added"]), len(res["removed"]),
          " (recoverable: ctx undo)" if res["removed"] else ""))
    if res.get("moved"):
        print("order: the records follow the file (%d moved)" % len(res["moved"]))
    print("wrote: " + (", ".join(comp.get("written") or []) or "no copy needed a change"))
    return 0, dict(res, command=a.cmd)


def _record(c, rid):
    recs = {r["id"]: r for r in c.store.load()}
    if rid not in recs:
        raise cs.StoreError("no record %s — `ctx list` shows the ids" % rid)
    return recs[rid]


def _field_kind(rec):
    """The record's section of references/context-fields.yaml, or None."""
    if rec["type"] in ("profile", "product", "onboarding"):
        return rec["type"]
    return "judgment" if rec["type"] == "setting" and rec["title"].startswith("Judgment") else None


def _field_spec(rec, field):
    """The field's type from references/context-fields.yaml, or None (plain text)."""
    return (sc.load_fields().get(_field_kind(rec)) or {}).get(field)


def cmd_get(a, c):
    c.need_store()
    rec = _record(c, a.id)
    if a.section:
        name = a.section.lstrip("#").strip()
        part = cr._subsection(rec["body"], name)
        if part is None:
            raise cs.StoreError("no subsection %r in %s" % (name, a.id))
        sys.stdout.write(part)
        return 0, {"command": "get", "id": a.id, "section": name, "text": part if a.json else None}
    if a.field:
        spec = _field_spec(rec, a.field)
        raw = sc.raw_value(rec["body"], a.field, spec) if spec else cs.field_get(rec["body"], a.field)
        placeholder = cs.field_get(rec["body"], a.field) if raw is None and spec else None
        if placeholder is not None:            # the line is there with a placeholder such as _(not set)_
            print(placeholder)
            return 0, {"command": "get", "id": a.id, "field": a.field, "value": None, "not_set": True}
        if raw is None:
            raise cs.StoreError("no field %r outside managed regions in %s" % (a.field, a.id))
        print(raw)
        return 0, {"command": "get", "id": a.id, "field": a.field, "value": sc.parse_value(spec, raw) if spec else raw}
    sys.stdout.write(rec["body"] if rec["body"].endswith("\n") else rec["body"] + "\n")
    return 0, {"command": "get", "id": a.id, "body": rec["body"] if a.json else None}


def cmd_list(a, c):
    c.need_store()
    if a.archived:
        recs = [r for r in c.store.archived() if not a.type or r["type"] == a.type]
        for r in recs:
            print("%-48s %-10s archived %s  %s%s" % (r["id"], r["type"], r.get("archived") or "", r["title"],
                                                     " — " + r["archived_reason"] if r.get("archived_reason") else ""))
        return 0, {"command": "list", "archived": [{k: r.get(k) for k in ("id", "type", "title", "archived", "archived_reason")}
                                                   for r in recs]}
    if a.trash:
        items = [(p, r) for p, r in co.trash_entries(c.home) if not a.type or r["type"] == a.type]
        for p, r in items:
            print("%-48s %-10s trashed %s  %s" % (r["id"], r["type"], (r.get("trashed") or "")[:10], r["title"]))
        return 0, {"command": "list", "trash": [{"id": r["id"], "type": r["type"], "title": r["title"],
                                                 "trashed": r.get("trashed"), "file": p} for p, r in items]}
    recs = [r for r in c.store.load() if not a.type or r["type"] == a.type]
    for r in recs:
        print("%-48s %-10s %-10s %s" % (r["id"], r["type"], (r.get("modified") or "")[:10], r["title"]))
    return 0, {"command": "list", "records": [{k: r[k] for k in ("id", "type", "title", "parent", "modified")}
                                               for r in recs]}


def cmd_read(a, c):
    c.need_store()
    try:
        cr.manifest_for(cr.load_manifest(), a.skill)
    except KeyError:
        raise cs.StoreError("no manifest entry for %s — read local-context.md whole" % a.skill)
    skipped = []                    # since v3.15.0: a registration not read is one line, when it may own a block read here
    try:
        repos = crp.load_repos(c.text, c.home, skipped=skipped)
    except Exception:  # noqa: BLE001 — the line that names a block's repository is not worth a read
        repos = []
    text, res = cr.read_view(c.store, c.copies, a.skill, product=a.product, today=now()[:10], repos=repos, skipped=skipped,
                             entities=_entities_for_read(c, repos))
    sys.stdout.write(text)
    return 0, dict(res, command="read", skill=a.skill, text=text if a.json else None)


def _entities_for_read(c, repos):
    """The registry `ctx read` joins team.members by (v3.19.0, plan C8), built the first time it is asked for: the index
    as it is — never refreshed, no lock, nothing written — and your answers; ((registry, index, search context), why)."""
    got = {}

    def entities():
        if "v" not in got:
            got["v"] = _load_entities(c, repos)
        return got["v"]
    return entities


def _load_entities(c, repos):
    try:
        sctx = cs_.context_for(c.home, c.text, store_root=c.store.root, repos=repos)
        if not sctx["roots"] and not cs_.sources(sctx["text"], sctx["repos"], ("local",)):
            return None, None                    # nothing to index, nothing to join by: the list as before, no line
        idx = ci.Index(c.home)
        built = idx.built()
        if built is not True:
            return None, idx.problem or "індекс пошуку ще не збудовано — ctx index rebuild"
        mem = ce.empty_memory()
        if c.store.exists():
            try:
                mem = ce.load_memory(c.store, timeout=cs_.OPEN_S)
            except cs.StoreError:
                pass                             # without your answers, as `ctx entity` goes on
        reg, _ = ce.load(sctx, idx, mem, hints=False)    # a read joins members: no pairs to offer (final review M1)
        if reg.unread:
            return None, reg.unread
        return (reg, idx, sctx), None
    except Exception as e:  # noqa: BLE001 — a members list joined is not worth a read: it is printed as before
        return None, cc.clip(str(e), 200)


def cmd_explain(a, c):
    """`explain`: where each slot came from and why it won (ctx_resolve.explain). Reads only, as `read` does: no lock, no
    network, nothing written; the registrations are read in a try, and one that cannot be read is a line, not a failure."""
    c.need_store()
    cat = sl.load_catalogue()
    for slot in a.slots:
        if sl.slot_info(cat, slot) is None:
            raise Usage(_no_slot(slot, cat))
    if a.skill:
        try:
            cr.manifest_for(cr.load_manifest(), a.skill)
        except KeyError:
            raise cs.StoreError("no manifest entry for %s — read local-context.md whole" % a.skill)
    skipped = []
    try:
        repos = crp.load_repos(c.text, c.home, skipped=skipped)
    except Exception:  # noqa: BLE001 — what names a block's repository is not worth an explanation
        repos = []
    text, res = rv.explain(c.store, c.copies, repos, skipped, slots=a.slots or None, skill=a.skill, product=a.product,
                           today=now()[:10], catalogue=cat)
    sys.stdout.write(text)
    return 0, dict(res, command="explain", skill=a.skill, text=text if a.json else None)


def _lifecycle(c, fn, *args):
    c.need_store()
    with co.lock(c.home):
        c.guard()
        return fn(c.store, c.copies, c.home, *args)


def cmd_invalidate(a, c):
    res = _lifecycle(c, co.invalidate, a.id, a.reason, now())
    print("invalidated %s · wrote %s" % (a.id, ", ".join(res["written"]) or "no copy"))
    return 0, dict(res, command="invalidate")


def cmd_archive(a, c):
    res = _lifecycle(c, co.archive, a.id, a.reason or "", now())
    print("archived %s · wrote %s (back: ctx restore %s)" % (a.id, ", ".join(res["written"]) or "no copy", a.id))
    return 0, dict(res, command="archive")


def cmd_restore(a, c):
    res = _lifecycle(c, co.restore_record, a.id, now())
    print("restored %s · wrote %s" % (a.id, ", ".join(res["written"]) or "no copy"))
    return 0, dict(res, command="restore")


def cmd_verify(a, c):
    if not a.ids and not a.stale:
        raise Usage("verify takes record ids or --stale")
    c.need_store()
    with co.lock(c.home):
        c.guard()
        c.import_first()
        done = co.verify(c.store, c.copies, c.home, a.ids, now(), stale=a.stale)
    print("verified today: %s" % (", ".join(done) or "nothing"))
    return 0, {"command": "verify", "ids": done}


def _write_one(c, op, rid, mutate, source, reason, note=None):
    """One record changed by `mutate`; since v3.22.0 `note(sources, rec)` notes where the change came from
    (`.state/sources.json` — read before the snapshot, so a file that cannot be read stops the write first)."""
    c.need_store()
    with co.lock(c.home):
        c.guard()
        pre = c.import_first()
        srcs = csrc.load(c.store) if note else None
        rec = _record(c, rid)
        body = mutate(rec["body"])
        if body == rec["body"]:
            print("unchanged — %s already says that" % rid)
            return {"command": op, "id": rid, "changed": False, "imported": pre["changed"] + pre["added"]}
        t = now()
        snap = co.snapshot(c.store, c.copies, c.home, op)
        if note:
            csrc.adopt(srcs, rec)
            note(srcs, rec)
            csrc.save(c.store, srcs)
        c.store.write(co.touch(dict(rec, body=body, source=source, modified=t), t))
        c.store.journal({"ts": t, "op": op, "ids": [rid], "source": source, "reason": reason or "", "snapshot": snap})
        comp = co.compile_store(c.store, c.copies, t, c.home, snap)
    print("%s: %s · wrote %s" % (op, rid, ", ".join(comp["written"]) or "no copy"))
    return {"command": op, "id": rid, "changed": True, "snapshot": snap, "imported": pre["changed"] + pre["added"],
            "written": comp["written"]}


def cmd_set(a, c):
    c.need_store()
    spec = _field_spec(_record(c, a.id), a.field)
    err = sc.check_value(spec, a.value) if spec else None
    if err:
        raise ValueError("%s: %s" % (a.field, err))
    return 0, _write_one(c, "set", a.id, lambda b: cs.field_set(b, a.field, a.value), a.source or "ctx-set", a.reason,
                         note=lambda m, rec: csrc.note(m, rec["id"], csrc.field_key(a.field), a.value,
                                                       a.source or "user", at=now()))


def _readers_value(text):
    """`all`, `none` (→ None) or skill names → the stored read_by value; unknown names → Usage."""
    v = text.strip().lower()
    if v == "none":
        return None
    if v == "all":
        return "all"
    names = sorted(cr.readers({"read_by": v}) or [])
    if not names:
        raise Usage("assign takes all, none or skill names separated by commas")
    unknown = [n for n in names if n not in (cr.load_manifest().get("skills") or {})]
    if unknown:
        raise Usage("unknown skill(s): %s — the names of skills/ folders" % ", ".join(unknown))
    return ", ".join(names)


def cmd_assign(a, c):
    """Who reads a custom or setting record in `ctx read` (read_by)."""
    value = _readers_value(a.readers)
    c.need_store()
    with co.lock(c.home):
        c.guard()
        pre = c.import_first()
        rec = _record(c, a.id)
        if rec["type"] not in ("custom", "setting"):
            raise Usage("read_by is for custom and setting records, not %s (%s)" % (rec["type"], a.id))
        if rec.get("read_by") == value:
            print("unchanged — %s already has read_by %s" % (a.id, value or "unset"))
            return 0, {"command": "assign", "id": a.id, "read_by": value, "changed": False, "snapshot": None}
        t = now()
        source = a.source or "ctx-assign"
        snap = co.snapshot(c.store, c.copies, c.home, "assign")
        co.adopt_sources(c.store, rec)
        c.store.write(dict(rec, read_by=value, source=source, modified=t))     # who reads it — not a content check
        c.store.journal({"ts": t, "op": "assign", "ids": [a.id], "source": source, "reason": a.reason or "",
                         "snapshot": snap})
        comp = co.compile_store(c.store, c.copies, t, c.home, snap)
    print("assign: %s read_by %s · wrote %s" % (a.id, value or "unset", ", ".join(comp["written"]) or "no copy"))
    return 0, {"command": "assign", "id": a.id, "read_by": value, "changed": True, "snapshot": snap,
               "imported": pre["changed"] + pre["added"]}


def cmd_append(a, c):
    return 0, _write_one(c, "append", a.id, lambda b: cs.append_line(b, a.text, under=a.under),
                         a.source or "ctx-append", a.reason,
                         note=lambda m, rec: csrc.note_text(m, rec["id"], a.text, a.source or "user", at=now()))


def cmd_add(a, c):
    c.need_store()
    if a.type not in HEADINGS:
        raise Usage("add takes one of %s" % ", ".join(sorted(HEADINGS)))
    content = co._read(a.body_file) if a.body_file else ""
    cn.check(content)
    heading = HEADINGS[a.type] % a.title
    text = heading + "\n\n" + (content.rstrip("\n") + "\n\n" if content.strip() else "")
    with co.lock(c.home):
        c.guard()
        c.import_first()
        srcs = csrc.load(c.store)
        recs = c.store.load()
        ids = [r["id"] for r in recs]
        if a.after:
            if a.after not in ids:
                raise cs.StoreError("no record %s" % a.after)
            after = a.after
        elif a.type in ("product", "team"):
            orgs = [r["id"] for r in recs if r["type"] == "org"]
            parent = a.parent or (orgs[0] if len(orgs) == 1 else None)
            if parent not in orgs:
                raise Usage("--parent names the organisation record (%s)" % ", ".join(orgs))
            same = [r["id"] for r in recs if r["type"] == a.type and r["parent"] == parent]
            kids = [r["id"] for r in recs if r["parent"] == parent]
            after = (same or kids or [parent])[-1]
        else:
            after = ids[-1] if ids else None
        t = now()
        snap = co.snapshot(c.store, c.copies, c.home, "add")
        title = heading.lstrip("#").strip()
        new = co._insert(c.store, [{"text": text, "type": a.type, "title": title, "after": after}],
                         a.source or "ctx-add", t)
        csrc.note_body(srcs, new[0], text, a.source or "user", at=t)
        csrc.save(c.store, srcs)
        c.store.journal({"ts": t, "op": "add", "ids": new, "source": a.source or "ctx-add", "reason": a.reason or "",
                         "snapshot": snap})
        comp = co.compile_store(c.store, c.copies, t, c.home, snap)
    print("added %s after %s" % (new[0], after))
    return 0, {"command": "add", "id": new[0], "after": after, "snapshot": snap, "written": comp["written"]}


def cmd_snapshot_import(a, c):
    """`snapshot import [--apply --code C]` (since v3.21.0): the old backups of local-context.md as snapshots. A dry run
    lists what it would import, what a snapshot already holds and what it leaves, and `код звіту`; `--apply --code` writes
    the snapshots (`<their time>-imported`, out of the rotation), moves the originals to the trash, one journal line
    {op snapshot-import, moves, snapshots} with a snapshot of the store; `ctx undo` puts them back. No store: exit 3."""
    c.need_store()
    p = cbk.plan(c.home)
    cd = cbk.code(p)
    for r in p["import"]:
        print("імпортую: %s (%s, %s)" % (r["path"], csh.human(r["size"]), r["when"][:8]))
    for r in p["known"]:
        print("уже в знімку %s: %s — оригінал у кошик" % (r["snapshot"], r["path"]))
    for r in p["left"]:
        print("не імпортую: %s (%s) — %s" % (r["path"], csh.human(r["size"]), r["why"]))
    out = {"command": "snapshot", "action": "import", "import": p["import"], "known": p["known"], "left": p["left"],
           "code": cd}
    if not a.apply:
        print("нічого імпортувати" if not (p["import"] or p["known"]) else "код звіту: %s" % cd)
        return 0, out
    if not a.code:
        raise Usage("snapshot import --apply takes --code from the report")
    if a.code != cd:
        raise co.Refused("звіт змінився — переглянь ще раз: ctx snapshot import")
    if not (p["import"] or p["known"]):
        print("нічого імпортувати")
        return 0, out
    with co.lock(c.home):
        c.guard()
        c.import_first()
        snap = co.snapshot(c.store, c.copies, c.home, "snapshot-import")
        moves = cbk.planned_moves(p, c.home, datetime.datetime.now())
        # the journal line first, with every planned move: an apply cut short is still taken back by `ctx undo`
        c.store.journal({"ts": now(), "op": "snapshot-import", "ids": [], "source": "ctx-snapshot-import", "reason": "",
                         "snapshot": snap, "moves": moves})
        done = cbk.apply(moves, c.home, c.context)
    for path, why in done["failed"]:
        print("не імпортовано: %s — %s" % (path, why))
    made = [m["snapshot"] for m in done["done"] if m["made"]]
    print("знімків створено: %d · оригіналів у кошику: %d (30 днів; back: ctx undo)" % (len(made), len(done["done"])))
    return 0, dict(out, snapshots=made, moves=[[m["path"], m["trash"]] for m in done["done"]],
                   failed=[{"path": a, "why": b} for a, b in done["failed"]], snapshot=snap)


def cmd_snapshot(a, c):
    if a.action == "import":
        return cmd_snapshot_import(a, c)
    if re.match(r"^%s(?:-\d+)?$" % cbk.LABEL, cc.slugify(a.label or "")):
        raise Usage("the label «imported» is the old backups' — choose another")
    c.need_store()
    path = co.snapshot(c.store, c.copies, c.home, a.label or "manual")
    print(path)
    return 0, {"command": "snapshot", "snapshot": path}


def sync_rejections(marks):
    """What undoing these journal changes (`marks`, oldest first) makes the sync remember as rejected (spec v3.14 §5.4):
    {repo: {block: [sha | "removed", …]}}, the texts in the order the passes took them. Only a `provider-sync` line counts —
    a manual `provider apply` or any other change does not — and only through its `taken`; an older line has none. A line
    whose source is not `repo:<id>` of a repository id, or a block or text that is not what `taken` holds (a block id and
    a hash, or "removed"), is skipped: a hand-edited journal never stops an undo."""
    out = {}
    for m in marks:
        source, taken = m.get("source"), m.get("taken")
        if m.get("op") != sy.OP or not isinstance(source, str) or not source.startswith("repo:") or not isinstance(taken, dict):
            continue
        repo = source[len("repo:"):]
        if not cb.REPO_ID.fullmatch(repo):
            continue
        for bid, sha in taken.items():
            if isinstance(sha, str) and (sha == cb.REMOVED or cb.SHA.fullmatch(sha)):
                out.setdefault(repo, {}).setdefault(bid, []).append(sha)
    return out


def remember_rejected(store, rejections):
    """Write `rejections` ({repo: {block: [text, …]}}, from `sync_rejections`) into the repositories' block states, after the
    newest rejected texts of each block (`cb.save_state` keeps the last ten, each once). Returns ({repo: [blocks]} saved,
    {repo: why} for a state that could not be read or written — the others are saved all the same)."""
    saved, failed = {}, {}
    for repo in sorted(rejections):
        try:
            state = cb.load_state(store, repo)
            rejected = {b: list(seq) for b, seq in (state.get("rejected") or {}).items()}
            for bid, texts in rejections[repo].items():
                rejected[bid] = rejected.get(bid, []) + texts
            state["rejected"] = rejected
            cb.save_state(store, repo, state)
        except (cs.StoreError, OSError) as e:
            failed[repo] = str(e)
            continue
        saved[repo] = sorted(rejections[repo])
    return saved, failed


def cmd_undo(a, c):
    if a.steps < 1:
        raise Usage("--steps takes a whole number from 1")
    c.need_store()
    with co.lock(c.home):
        c.guard()
        plan = co.plan_sync(c.store, c.copies)
        waiting = sum(co.pending(plan).values()) + len(plan["conflicts"]) + len(plan["missing"])
        if waiting:
            raise co.Refused("%d change(s) to local-context.md or the records are not imported yet and undo would "
                             "discard them — `ctx sync` first, then `ctx undo`" % waiting)
        marks = [e for e in c.store.journal_entries() if e.get("snapshot")]
        if len(marks) < a.steps:
            raise cs.StoreError("nothing to undo — the journal has %d change(s)" % len(marks))
        target = marks[-a.steps]["snapshot"]
        if not os.path.isdir(target):
            raise cs.StoreError("the snapshot %s is gone (rotated)" % target)
        rejections = sync_rejections(marks[-a.steps:])      # the sync passes this undo takes back: what they took is not applied again
        jpath = os.path.join(c.store.state_dir, "journal.jsonl")
        journal = co._read(jpath)
        items = cbr.undo_notes(marks[-a.steps:])        # the notes `entity apply` (or an undo of it) changed (v3.20.0)
        sctx, regs, keep = None, None, []
        if items:
            sctx = cs_.context_for(c.home, c.text, store_root=c.store.root)
            regs, _ = cc.boundary_registrations(cc.vault_entries(c.text),
                                                extra_dirs=[os.path.join(c.home, ".grow-pm", "providers")])
            for rel in dict.fromkeys(rel for rel, _, _ in items):    # as they are now: `ctx undo` of this undo needs them
                path, _ = cbr.own_file(sctx, rel)
                if path and os.path.isfile(path) and not ci.is_dataless(path) \
                        and not cbr.write_refusal(sctx, regs, c.store.root, c.home, rel):
                    try:
                        cs.read_bytes(path)             # one iCloud has not downloaded: no copy, said by the revert
                    except (OSError, cs.StoreError):
                        continue
                    keep.append((rel, path))
        previous = None
        if items:
            try:
                previous = cbr.load_ledger(c.store)     # our lines before the restore: a renamed note keeps them ours
            except cs.StoreError:
                previous = None
        entries = c.store.journal_entries()
        at = max((i for i, e in enumerate(entries) if e.get("snapshot") == target), default=len(entries))
        later = {s for e in entries[at + 1:] if e.get("op") == "propose" for s in (e.get("sigs") or [])}
        inbox_before = None
        if later:                                       # since v3.21.0: what skills proposed after the change undone —
            try:                                        # in the inbox now, or in a later change's snapshot when it was
                now_box = ci_.load(c.store)             # taken or rejected inside the span undone
            except cs.StoreError as e:
                now_box = None
                print("скринька не читається: %s — пропозиції після цієї зміни лишаються лише в знімку pre-undo" % e)
            inbox_before = ci_.union([ci_.load_path(os.path.join(m["snapshot"], "state", ci_.FILE))
                                      for m in marks[-a.steps + 1:] if a.steps > 1] + [now_box])
        pre = co.snapshot(c.store, c.copies, c.home, "pre-undo", notes=keep or None)
        skipped = co.restore(target, c.store, c.copies)
        with open(os.path.join(target, "manifest.json"), encoding="utf-8") as f:
            existed = json.load(f).get("store_existed")
        if existed:
            cs.atomic_write(jpath, journal)             # the history first: nothing after the restore may lose it
        for p in skipped:
            print("skipped (not a current copy): %s" % p)
        notes_done, notes_back, notes_kept = (cbr.revert_notes(sctx, regs, c.store.root, c.home, items) if items
                                              else ([], [], []))
        if items and existed:
            cbr.keep_ours(sctx, c.store, items, now()[:10], previous=previous, reverted=notes_back)   # ours stays ours
        if notes_back:
            print("повернуто нотаток: %d" % len(notes_back))
        for m in reversed(marks[-a.steps:]):             # since v3.21.0: an import of old backups — the originals back
            if m.get("op") == "snapshot-import":
                back, kept_b = cbk.revert([x for x in (m.get("moves") or []) if isinstance(x, dict)], c.home)
                print("повернуто бекапів: %d" % len(back))
                for path, why in kept_b:
                    print("бекап не повернуто: %s — %s" % (path, why))
        for rel, why in notes_kept:
            print("не повернуто: %s — %s" % (rel, why))
        reverted, kept, rejected, rejected_failed = [], [], {}, {}
        hist = os.path.join(c.store.root, "history")
        if not existed and os.path.isdir(hist):         # since v3.23.0: the changelog is derived — no store, no notes of it
            import shutil
            shutil.rmtree(cs.check_target(hist))
        if existed:
            t = now()
            c.store.journal(dict({"ts": t, "op": "undo", "ids": [], "source": "undo", "reason": target, "snapshot": pre},
                                 **({"notes": notes_done} if notes_done else {})))
            # a sync pass taken back stays taken back: the core's texts it applied are remembered as rejected in the
            # block state — after the restore, which brought that state back to what it was before the pass
            rejected, rejected_failed = remember_rejected(c.store, rejections)
            if inbox_before is not None:                # proposals are no undo steps: the later ones stay in the inbox
                try:
                    mem = ci_.load(c.store)
                    if ci_.merge_back(mem, inbox_before, later):
                        ci_.save(c.store, mem, t[:10])
                except cs.StoreError as e:
                    print("скриньку не відновлено: %s — ctx inbox list" % e)
            # an import's snapshot holds the copies as they were on disk then — already edited; rebuild them
            # from the restored records so the edit is undone and nothing waits to be imported again. A compile's
            # own snapshot (a mirror created or rewritten) is the one case whose copies must stay as restored.
            # The same import of a record edited in its file (Obsidian) holds the edit in the records too: they
            # go back to the last compile's text first, or the rebuild would write the edit into the copies again.
            rebuilt = bool({m.get("op") for m in marks[-a.steps:]} - {"compile"})
            reverted, kept = co.consistent_records(c.store, c.copies) if rebuilt else ([], [])
            if rebuilt:
                co.compile_store(c.store, c.copies, t, c.home, pre)
            print("restored the state before the %s — %s%s"
                  % ("last change" if a.steps == 1 else "%d last changes" % a.steps, target,
                     "; the copies were rebuilt from the records" if rebuilt else ""))
            if reverted:
                print("put back to the last compiled text (the edit made in the file is undone): %s" % ", ".join(reverted))
            if kept:
                print("not put back (no matching text in local-context.md): %s — check them: ctx get <id>" % ", ".join(kept))
            for repo, blocks in rejected.items():
                print("не застосовуватиметься, доки ядро не змінить блок: %s: %s" % (repo, ", ".join(blocks)))
            for repo, why in rejected_failed.items():
                print("не вдалося запам'ятати відкинуте в %s: %s — наступний синк може застосувати це знову" % (repo, why))
        else:
            co.forget_store(c.home)
            print("store removed — local-context.md is a single file again (the store is kept in %s)" % pre)
    return 0, {"command": "undo", "restored": target, "snapshot": pre, "store_removed": not existed, "skipped": skipped,
               "records_reverted": reverted, "records_not_reverted": kept, "rejected": rejected,
               "rejected_failed": rejected_failed, "notes_reverted": notes_back,
               "notes_not_reverted": [{"path": p, "why": w} for p, w in notes_kept]}


def cmd_validate(a, c):
    c.need_store()
    if a.recheck or a.observed:
        return cmd_recheck(a, c)
    errors, warnings, proposals = _validate(c)
    for e in errors:
        print("error: " + e)
    for w in warnings:
        print("warning: " + w)
    print("valid" if not errors else "%d error(s)" % len(errors))
    return (3 if errors else 0), {"command": "validate", "errors": errors, "warnings": warnings, "slot_proposals": proposals}


CHECK_NAMES = {"jira": "Jira-ключі", "confluence": "простори Confluence", "member": "учасники команд",
               "role": "роль від провайдера"}


def cmd_recheck(a, c):
    """`validate --recheck --observed F` (since v3.22.0, plan C9; the day of the look is the file's `at`): the records against what the connectors
    say. A finding seen the first time waits in `.state/recheck.json`; seen again at least 6 days later it becomes a
    delta of the inbox (ctx-recheck) — urgent ones by the inbox's table. Writes only the inbox, the memory and, when
    something was proposed, one journal line {op propose, skill ctx-recheck}; the records it found as they should be are
    printed for `ctx verify`. A connector that did not answer checks nothing."""
    if not (a.recheck and a.observed):
        raise Usage("validate --recheck бере --observed F (файл спостережень, references/context-observe.md)")
    try:
        obs = cob.load(a.observed)
    except ValueError as e:
        raise Usage(str(e))
    if not obs.get("at"):
        raise Usage("validate --recheck needs the observation's at (the day the connectors were read)")
    today = obs["at"]
    with co.lock(c.home):
        c.guard()
        mem_rk = crk.load(c.store)
        box = ci_.load(c.store)
        c.import_first()
        recs = c.store.load()
        res = crk.run(obs, recs, mem_rk, today)
        props = ci_.propose(box, res["deltas"], "ctx-recheck", recs, today) if res["deltas"] else []
        new = [r for r in props if r["status"] == ci_.ADDED]
        if new:
            ci_.save(c.store, box, today)
            c.store.journal({"ts": now(), "op": "propose", "skill": "ctx-recheck",
                             "ids": sorted({r["record"] for r in new}),
                             "sigs": [e["sig"] for e in box["entries"] if e["n"] in {r["n"] for r in new}],
                             "source": "ctx-recheck"})
        crk.save(c.store, mem_rk)
        cd = ci_.code(box, recs)
    print("перевірено: %s" % (", ".join("%s (%d)" % (CHECK_NAMES[k], sum(k in v for v in res["checked"].values()))
                                         for k in CHECK_NAMES if k not in res["unchecked"]) or "нічого"))
    if res["unchecked"]:
        print("не перевірено: %s — конектор не відповів, список неповний чи даних немає"
              % ", ".join(CHECK_NAMES[k] for k in res["unchecked"]))
    for f in res["noticed"]:
        print("помічено: %s · %s %s — перевірю ще раз не раніше ніж через %d дн після %s" % (
            f["record"], CHECK_NAMES[f["check"]], f["item"], crk.CONFIRM_DAYS, f["first"]))
    for f in res["unresolved"]:
        print("перевір сам: %s · %s" % (f["record"], f["why"]))
    for i, r in enumerate(props, 1):
        if r["status"] in (ci_.REFUSED, ci_.SECRET, ci_.BLOCK):
            print("знахідка %d: %s" % (i, r.get("why")))
    added = [r for r in props if r["status"] == ci_.ADDED]
    urgent = sorted({r["n"] for r in new if r.get("urgent")})
    if new:
        print("у скриньці +%d (усього %d)%s — /context inbox" % (len(added), len(box["entries"]), (
            " · термінові №%s — запитай зараз, код %s" % (", ".join(map(str, urgent)), cd)) if urgent else ""))
    if res["fine"]:
        print("як і було: %s — ctx verify %s" % (", ".join(res["fine"]), " ".join(res["fine"])))
    return 0, {"command": "validate", "recheck": True, "checked": res["checked"], "unchecked": res["unchecked"],
               "noticed": res["noticed"], "confirmed": res["confirmed"], "unresolved": res["unresolved"],
               "results": props, "added": [r["n"] for r in added], "urgent": urgent, "code": cd, "fine": res["fine"]}


def _validate(c):
    """(errors, warnings, slot proposals) of the store — what `validate` prints and `health` counts. Reads only."""
    errors, warnings = [], []
    try:
        recs = c.store.load()
    except cs.StoreError as e:
        errors.append(str(e))
        recs = []
    valid, odd = c.store.record_files()
    state = c.store.state()
    for r in recs:
        for field, spec in (sc.load_fields().get(_field_kind(r)) or {}).items():
            problem = sc.check_value(spec, sc.raw_value(r["body"], field, spec))
            if problem:
                warnings.append("%s: %s — %s%s" % (r["id"], field, problem, " (Step 0i asks once)" if field == "Role" else ""))
        if r.get("verified") is not None and sc._date(r.get("verified")) is None:
            warnings.append("%s: verified %r is not a date — the store's freshness date applies" % (r["id"], r.get("verified")))
        if r.get("ttl_days") is not None and not str(r.get("ttl_days")).strip().isdigit():
            warnings.append("%s: ttl_days %r is not a whole number — the type's default applies" % (r["id"], r.get("ttl_days")))
        own = r["body"]
        for lo, hi in reversed(cc.managed_spans(own)):  # a provider's block is not yours to clean
            own = own[:lo] + own[hi:]
        kinds = cn.scan(own)
        if kinds:                                       # since v3.21.0: your own text may hold one — said, not refused
            warnings.append("%s: %s" % (r["id"], cn.warning(kinds)))
        if sc.is_stale(r, state, now()[:10]):
            warnings.append("stale: %s (verified %s, TTL %s d) — ctx verify %s" % (r["id"], sc.verified_of(r, state), sc.ttl_of(r), r["id"]))
    for name in valid:
        try:
            rid = cs.parse_record(co._read(os.path.join(c.store.records_dir, name)))["id"]
        except (OSError, ValueError, UnicodeDecodeError):
            continue
        if rid != name[:-3]:
            errors.append("%s: its frontmatter id %s differs from the file name — compile ignores it" % (name, rid))
    for name in odd:
        warnings.append("stray file, ignored by compile (a sync conflict copy?): %s" % name)
    ids = [r["id"] for r in recs]
    orders = [r["order"] for r in recs]
    if len(set(orders)) != len(orders):
        errors.append("two records share an order")
    for r in recs:
        if r["parent"] and r["parent"] not in ids:
            errors.append("%s: parent %s does not exist" % (r["id"], r["parent"]))
        if r["type"] == "product" and cs.field_get(r["body"], "Jira Project Key") is None:
            warnings.append("%s: no Jira Project Key (task-creator and requirements-creator need it)" % r["id"])
    skills = cr.load_manifest().get("skills") or {}
    for r in recs:
        unknown = sorted((cs.readers(r) or frozenset()) - {"all"} - set(skills))
        if unknown:
            warnings.append("%s: read_by names unknown skill(s): %s" % (r["id"], ", ".join(unknown)))
    lonely = cs.unassigned_ids(recs)
    if lonely:
        warnings.append("custom without read_by: %d (%s) — skills see only the card row; ctx assign <id> all|<skills>"
                        % (len(lonely), ", ".join(lonely)))
    if recs and not any(r["type"] == "profile" for r in recs):
        warnings.append("no User Profile record")
    if os.path.isfile(c.store.card_path) and co._read(c.store.card_path).count("\n") > cs.CARD_MAX:
        errors.append("INDEX.md is longer than %d lines" % cs.CARD_MAX)
    if recs or c.store.state().get("order"):
        plan = co.plan_sync(c.store, c.copies)
        for rid in plan["missing"]:
            errors.append("%s.md is missing on disk (not downloaded, not synced or deleted) — `ctx sync` says what to do" % rid)
        waiting = sum(co.pending(plan).values())
        if waiting:
            warnings.append("%d change(s) waiting — `ctx sync`" % waiting)
        for x in plan["conflicts"]:
            warnings.append("conflict: %s — `ctx sync` asks" % x["id"])
    proposals = []
    if recs:                        # since v3.15.0: the slots — bindings that do nothing, divergences, bindings to propose (reads only)
        skipped = []
        try:
            repos = crp.load_repos(c.text, c.home, skipped=skipped)
        except Exception:  # noqa: BLE001 — a registration that cannot be read is a line (unread_lines), not a failure
            repos = []
        slot_errors, slot_warnings, proposals = rv.validate_slots(c.store, c.copies, repos, skipped, now())
        errors += slot_errors
        warnings += slot_warnings
    return errors, warnings, proposals


# ---------------------------------------------------------------------- show and health (since v3.21.0)
def cmd_show(a, c):
    """`show [ID …] [--json]`: what the plugin knows about you — one line a record (who wrote it last, when, verified,
    stale or no longer current, who reads it), the repositories' blocks, your answers and the inbox; with ids, those
    records' text too. Reads only: no lock, no network, nothing written."""
    c.need_store()
    today = now()[:10]
    rows = csh.records(c.store, today)
    want = set(a.ids or [])
    try:
        srcs = csrc.load(c.store)
    except cs.StoreError as e:
        srcs = None
        print("джерела полів не читаються: %s" % e)
    unknown = sorted(want - {r["id"] for r in rows})
    if unknown:
        raise cs.StoreError("no record %s — `ctx list` shows the ids" % ", ".join(unknown))
    for r in rows:
        if want and r["id"] not in want:
            continue
        marks = [m for m, on in (("застаріле", r["stale"]), ("неактуальне", r["invalid"])) if on]
        print("%s — %s · писав %s %s · перевірено %s%s%s%s" % (
            r["id"], r["title"], r["source"], r["modified"], r["verified"], (" (TTL %s дн)" % r["ttl"]) if r["ttl"] else "",
            (" · читає: %s" % r["read_by"]) if r["read_by"] else "", (" · " + ", ".join(marks)) if marks else ""))
        if want:
            rec = _record(c, r["id"])
            print(rec["body"].rstrip("\n"))
            if srcs is not None:                        # since v3.22.0: where each field came from
                print("джерела:")
                for x in csrc.of(srcs, rec):
                    print("  %s %s" % (x["label"], csrc.describe(x)))
            print()
    repo_rows = csh.repos(c.text, c.home, c.store)
    mem = csh.memories(c.store, today)
    try:
        waiting = sum(co.pending(co.plan_sync(c.store, c.copies)).values())
    except cs.StoreError:
        waiting = 0
    if waiting:
        print("правок у local-context.md чекає імпорту: %d — тут ще без них; ctx sync" % waiting)
    if not want:
        for r in repo_rows:
            print("репозиторій %s: блоків %s · версія %s · перевірено %s" % (
                r["id"], r["blocks"] or "—", r["version"] or "—", r["checked"] or "—"))
        ib = mem.get("inbox")
        print("твої відповіді: слоти %s · same/not-same %s · пошук %s · мости %s · скринька %s" % (
            mem.get("slots"), mem.get("entities"), mem.get("search"), mem.get("bridges"),
            ib if isinstance(ib, str) else "%d (термінових %d)" % (ib["entries"], ib["urgent"])))
    cov = None
    if srcs is not None:
        own, total = csrc.coverage(srcs, c.store.load())
        cov = {"own": own, "fields": total}
        if not want:
            print("полів із власним джерелом: %d з %d (решта — за джерелом запису)" % (own, total))
    return 0, {"command": "show", "records": [r for r in rows if not want or r["id"] in want], "repos": repo_rows,
               "memories": mem, "sources": cov}


def cmd_health(a, c):
    """`health [--json]`: what wants looking after, one line each — ✅ fine · ⚠ worth a look · ✋ do something — with the
    command that fixes it. Reads only: no lock, no network, nothing written; the copies outside the snapshots by stat alone
    (a backup iCloud evicted is never brought down). Exit 0."""
    c.need_store()
    today = now()[:10]
    try:                                                # a record that does not parse is health's first error, not a crash
        errors, warnings, _ = _validate(c)
        recs = csh.records(c.store, today)
        plan = co.plan_sync(c.store, c.copies)
    except cs.StoreError as e:
        errors, warnings, recs, plan = [str(e)], [], [], {"conflicts": [], "missing": [], "unread": True}
    skipped = []
    repo_rows = csh.repos(c.text, c.home, c.store, skipped=skipped)
    lines = csh.health(recs, csh.memories(c.store, today), repo_rows,
                       sum(co.pending(plan).values()) if not plan.get("unread") else 0, len(plan["conflicts"]),
                       len(plan["missing"]),
                       len(c.store.stray_files()), warnings, errors, csh.index_state(c.home), csh.snapshots(c.home),
                       csh.backups(c.home, c.context, c.text), today, unread_regs=skipped,
                       recheck=_recheck_health(c, today), consolidate=_consolidate_health(c, today),
                       overlays=_overlay_health(c),
                       audit=ca.health(c.home, bool(cc.vault_entries(c.text)), today))
    for level, text, fix in lines:
        print("%s %s%s" % (csh.MARK[level], text, (" — " + fix) if fix else ""))
    n = {k: sum(1 for l in lines if l[0] == k) for k in (csh.OK, csh.WARN, csh.ACT)}
    return 0, {"command": "health", "lines": [{"level": l, "text": t, "fix": f} for l, t, f in lines],
               "counts": n}


def _overlay_health(c):
    """[{repo, error | held: [ids], applied: n}] — each registered repository's overlay file (none: not listed), read only."""
    out = []
    try:
        repos = crp.load_repos(c.text, c.home)
    except Exception:  # noqa: BLE001 — health never fails over a registration
        return out
    for repo in repos:
        if not ov.REPO_ID.match(str(repo.get("id"))) or not os.path.isfile(ov.path_of(c.store.root, repo["id"])):
            continue                                    # an id no overlay file can have: none to report
        try:
            doc = ov.load(c.store.root, repo["id"])
            res = cb.reoverlay(c.store, c.copies, c.home, repo, now(), doc["ops"])
        except ov.Unreadable as e:
            out.append({"repo": repo["id"], "error": cb.clip(e, cb.NOTE_CLIP)})
            continue
        except (cs.StoreError, OSError) as e:
            out.append({"repo": repo["id"], "error": cb.clip(e, cb.NOTE_CLIP)})
            continue
        results = [x for r in res["rows"] for x in r["results"]]
        live = [x for r in res["rows"] if r["state"] in ("rewrite", "same") for x in r["results"]]
        out.append({"repo": repo["id"], "held": [x["id"] for x in results if x["state"] != "applied"],
                    "applied": sum(1 for x in live if x["state"] == "applied"),
                    "edited": sorted({r["block"] for r in res["rows"] if r["state"] in ("edited", "behind")})})
    return out


def cbt_day(s):
    try:
        return datetime.date.fromisoformat(s)
    except ValueError:
        return None


def _consolidate_find(c, recs, today):
    card = c.store.card_path
    lines = None
    if os.path.isfile(card):
        try:
            lines = cs.read_text(card).count("\n")
        except (OSError, cs.StoreError):
            lines = None
    return ccn.find(recs, today, card_lines=lines)


def cmd_consolidate(a, c):
    """`consolidate [--now ISO] [--json]` (since v3.22.0, plan C13, R4): a line written twice, a relative date, a passed
    deadline → REPLACE deltas of the inbox (ctx-consolidate); nothing written to a record. One op propose journal line
    when something new was proposed. Records no longer current for 90+ days and a card over its budget are named with
    their commands — archiving is no delta."""
    c.need_store()
    today = (a.now or now())[:10]
    if not re.match(r"\d{4}-\d{2}-\d{2}$", today) or cbt_day(today) is None:
        raise Usage("--now is a date or an ISO time")
    with co.lock(c.home):
        c.guard()
        box = ci_.load(c.store)
        c.import_first()
        recs = c.store.load()
        res = _consolidate_find(c, recs, today)
        props = ci_.propose(box, res["deltas"], "ctx-consolidate", recs, today) if res["deltas"] else []
        added = [r for r in props if r["status"] == ci_.ADDED]
        if added:
            ci_.save(c.store, box, today)
            c.store.journal({"ts": now(), "op": "propose", "skill": "ctx-consolidate",
                             "ids": sorted({r["record"] for r in added}),
                             "sigs": [e["sig"] for e in box["entries"] if e["n"] in {r["n"] for r in added}],
                             "source": "ctx-consolidate"})
    print("у скриньці +%d (усього %d) — /context inbox" % (len(added), len(box["entries"])) if added else
          "нічого нового для скриньки")
    for rid, since in res["archive"]:
        print("неактуальне з %s: %s — ctx archive %s" % (since, rid, rid))
    if res["card_over"]:
        print("картка %d рядків (бюджет %d) — архівуй неактуальне або злий записи" % (res["card_over"], cs.CARD_MAX))
    return 0, {"command": "consolidate", "results": props, "added": [r["n"] for r in added],
               "archive": [rid for rid, _ in res["archive"]], "card_over": res["card_over"]}


def _consolidate_health(c, today):
    """How many new deltas consolidate would propose now — counted on a copy of the inbox, nothing written."""
    import copy
    try:
        box = copy.deepcopy(ci_.load(c.store))
        recs = c.store.load()
    except cs.StoreError as e:
        return str(e)
    res = _consolidate_find(c, recs, today)
    props = ci_.propose(box, res["deltas"], "ctx-consolidate", recs, today) if res["deltas"] else []
    return sum(1 for r in props if r["status"] == ci_.ADDED) + len(res["archive"])


def _recheck_health(c, today):
    try:
        mem = crk.load(c.store)
    except cs.StoreError as e:
        return str(e)
    return {"age": crk.age(mem, today), "noticed": crk.waiting(mem), "old": crk.OLD_DAYS}


def cmd_card(a, c):
    c.need_store()
    with co.lock(c.home):
        c.guard()
        recs = c.store.load()
        stale, archived = co.card_marks(c.store, recs, now()[:10])
        compiled = cs.compile_records(recs)
        card = co.store_card(c.store, recs, compiled, now()[:10], c.home, stale=stale, archived=archived)
        cs.atomic_write(c.store.card_path, card)
    print("INDEX.md: %d lines" % card.count("\n"))
    return 0, {"command": "card", "card_lines": card.count("\n")}


def _table(rows):
    """Rows of texts as aligned columns; the first row is the header."""
    widths = [max(len(r[i]) for r in rows) for i in range(len(rows[0]))]
    return "\n".join("  ".join(cell.ljust(w) for cell, w in zip(r, widths)).rstrip() for r in rows)


NO_REPOS = ("no repositories registered — a registration is {vault}/{plugin folder}/_System/providers/<id>.yaml "
            "(references/context-provider-protocol.md §3b)")


def _list_state(c, rid):
    """(blocks, version, checked, error) of one repository for `repo list`, read from its block state — local files,
    no lock, nothing written. No store, or no state file, gives (None, None, None, None); a state that cannot be read
    gives an error text (a list must not fail over a state file; it says so)."""
    if not c.store.exists():
        return None, None, None, None
    try:
        state = cb.load_state(c.store, rid)
    except cs.StoreError as e:
        return None, None, None, cb.clip(e, cb.NOTE_CLIP)
    checked = state.get("checked")
    return (cb.based_count(state) or None, cb.base_version(state),
            checked[:10] if isinstance(checked, str) and checked else None, None)


def cmd_repo_list(a, c):
    skipped = []
    repos = crp.load_repos(c.text, c.home, skipped=skipped)
    rows, bad = [], []
    for r in repos:
        blocks, version, checked, error = _list_state(c, r["id"])
        rows.append(dict(r, blocks=blocks, base_version=version, checked=checked))
        if error is not None:
            rows[-1]["state_error"] = error
            bad.append((r["id"], error))
    if repos:
        table = [("id", "kind", "products", "rank", "access", "blocks", "version", "checked")]
        for r in rows:
            cells = ("!", "!", "!") if r.get("state_error") else (
                str(r["blocks"]) if r["blocks"] else "—", r["base_version"] or "—", r["checked"] or "—")
            table.append((r["id"] + (" (paused)" if r["status"] == "paused" else ""), r["kind"] or "—",
                          ", ".join(r["products"]) or "all", str(r["rank"]), r["access"] or "—") + cells)
        print(_table(table))
    else:
        print(NO_REPOS)
    for r in rows:                                      # since v3.24.0: the plugin's copy of a core
        facts = csh.copy_facts(c.home, r["id"]) if r.get("core_from") == "copy" or not (r.get("paths") or r["core_root"]) else None
        if facts:
            r["copy"] = facts
            print("%s · %s" % (cb.clip(r["id"], cb.HEADER_CLIP), csh.copy_line(facts)))
    for rid, error in bad:
        print("block state unreadable: %s (%s)" % (cb.clip(rid, cb.HEADER_CLIP), error))
    for r in rows:
        warning = crp.namespace_warning(r)
        if warning:
            print("warning: %s: %s" % (cb.clip(r["id"], cb.HEADER_CLIP), warning))
        r["namespace_warning"] = warning
    for path, why in skipped:
        print("unreadable registration: %s (%s)" % (path, why))
    return 0, {"command": "repo", "action": "list", "repos": rows,
               "unreadable": [{"file": p, "reason": w} for p, w in skipped]}


def cmd_repo_status(a, c):
    skipped = []
    repos = crp.load_repos(c.text, c.home, skipped=skipped)
    if a.id:
        repos = [r for r in repos if r["id"] == a.id]
        if not repos:
            raise Usage(_not_registered(a.id, skipped))
    rows = []
    for r in repos:
        ok, why = crp.reach(r)
        why = cb.clip(why, cb.NOTE_CLIP)                # reach clips already; kept, harmless (clip is idempotent)
        # the version on the source is what its blocks carry now, and only that: when the source was not read there is
        # none (the registration's own version, a note from whoever wrote it, goes in its own key and is never shown as
        # the source's). The base is the version most of the blocks the store holds a base for are at. Only the blocks
        # file is read for it (since v3.14): the team region is never built from the core folder here.
        fetched = crp.fetch(r, team=False) if ok else None
        live = fetched["version"] if fetched and not fetched.get("error") else None
        warning = crp.namespace_warning(r, fetched["namespace"] if fetched else None)
        base, bad_state = None, None
        try:
            base = cb.base_version(cb.load_state(c.store, r["id"]))
        except cs.StoreError as e:                      # a status must not fail over a state file; it says so
            bad_state = str(e)
        rows.append({"id": r["id"], "kind": r["kind"], "status": r["status"], "url": crp.public_url(r["endpoint"]["url"]),
                     "reachable": ok, "reason": why, "source_version": live,
                     "registration_version": r["source_version"], "base_version": base, "namespace_warning": warning})
        if fetched and fetched.get("error"):             # the server answers, the blocks could not be read
            rows[-1]["fetch_error"] = cb.clip(fetched["error"], cb.NOTE_CLIP)
        if bad_state:
            rows[-1]["state_error"] = bad_state
        facts = csh.copy_facts(c.home, r["id"]) if r.get("core_from") == "copy" or not (r.get("paths") or r["core_root"]) else None
        if facts:
            rows[-1]["copy"] = facts
    if rows:
        for row in rows:
            where = row["url"] or "—"
            print("%s  %s  %s" % (row["id"] + (" (paused)" if row["status"] == "paused" else ""), row["kind"] or "—", where))
            print("  reachable %s" % ("yes" if row["reachable"] else "no (%s)" % row["reason"]))
            print("  version on source: %s · base: %s" % (row["source_version"] or "—", row["base_version"] or "—"))
            if row.get("fetch_error"):
                print("  blocks file: %s" % row["fetch_error"])
            if row.get("state_error"):
                print("  block state: %s" % row["state_error"])
            if row["namespace_warning"]:
                print("  warning: %s" % row["namespace_warning"])
            if row.get("copy"):
                print("  %s" % csh.copy_line(row["copy"]))
    else:
        print(NO_REPOS)
    for path, why in skipped:
        print("unreadable registration: %s (%s)" % (path, why))
    return 0, {"command": "repo", "action": "status", "repos": rows,
               "unreadable": [{"file": p, "reason": w} for p, w in skipped]}


def cmd_repo(a, c):
    if a.action == "list":
        return cmd_repo_list(a, c)
    if a.action == "status":
        return cmd_repo_status(a, c)
    if a.action == "kit-check":
        return cmd_repo_kit_check(a, c)
    if a.action == "add":
        return cmd_repo_add(a, c)
    if a.action == "copy":
        return cmd_repo_copy(a, c)
    raise Usage("repo takes list, status, kit-check, add or copy")


COPY_WORDS = (("new", "нових"), ("updated", "оновлено"), ("same", "без змін"), ("kept", "лишено твоє"),
              ("conflict", "конфліктів"), ("failed", "не прийшло"), ("removed", "перенесено в .removed"))


def copy_summary(rid, res):
    """The one line a pass of the copy earns (`repo copy`, and the daily sync's report part)."""
    if res["outcome"] in ("complete", "partial"):
        line = "копія %s: %s — %s · %s с" % (rid, " · ".join("%s %d" % (w, res["counts"][k]) for k, w in COPY_WORDS),
                                            res["folder"], res["elapsed_s"])
        return line + ("" if res["outcome"] == "complete" else " · неповний прохід: %s" % res["reason"])
    return "копія %s: не оновлено — %s" % (rid, res["reason"])


def _copy_repo(c, rid):
    """(the registration to copy, every registration) — or Usage (exit 3): no such repository, one with its own folder
    (it needs no copy), one with no endpoint url."""
    skipped = []
    repos = crp.load_repos(c.text, c.home, skipped=skipped)
    mine = [r for r in repos if r["id"] == rid]
    if not mine:
        raise Usage(_not_registered(rid, skipped))
    repo = mine[0]
    if repo.get("paths") or (repo["core_root"] and repo.get("core_from") != "copy"):
        raise Usage("%s: тека на диску — копія не потрібна (ядро читається з %s)"
                    % (rid, repo["core_root"] or repo["paths"][0]))
    if not repo["endpoint"]["url"]:
        raise Usage("%s: no endpoint url in the registration — nothing to copy from" % rid)
    return repo, repos


REPORT_LOCK_TRIES = 10                                  # the background pass waits this many seconds at most for the store's
                                                        # lock before it writes its part of the day's report


def copy_section(rid, res):
    """The part «Копія ядра <id>» of the day's report for a pass of the background (since v3.24.0)."""
    lines = ["## %s · копія ядра" % rid, "", copy_summary(rid, res)]
    for key, word in (("removed", "Перенесено в .removed/"), ("conflicts", "Конфлікти (твоє лишилось, серверне — у "
                                                                           "~/.grow-pm/conflicts/%s/)" % rid)):
        if res.get(key):
            lines += ["", "%s:" % word] + ["- `%s`" % cb.clip(x, cb.HEADER_CLIP) for x in res[key]]
    return "\n".join(lines) + "\n"


def _copy_reported(prev, res):
    """Does a background pass earn a part of the day's report? A change (new, updated, a conflict, a move), or a pass that
    is held or partial — but not the same held, with the same reason, as the attempt before it (safeguard 4)."""
    counts = res["counts"]
    if any(counts[k] for k in ("new", "updated", "conflict", "removed")):
        return True
    if res["outcome"] in ("held", "partial"):           # the same kind again is no news (its reason carries counts)
        return not (prev and prev.get("outcome") == res["outcome"])
    return False


def _copy_background(c, repo, repos, at):
    """`repo copy <id> --background` — the pass the daily sync starts (C7): only for a copy that exists (the background
    never makes the first one), the copy's lock only, and at the end a part of the day's report when `_copy_reported`
    says so — written under the store's lock (a short wait; busy for longer → no part, the log says so)."""
    folder, prev = ccp.copy_info(c.home, repo["id"])
    if folder is None:
        raise Usage("%s: no complete copy — the first copy is made by `ctx repo copy %s`, not in the background"
                    % (repo["id"], repo["id"]))
    try:
        res = ccp.run(c.home, repo, at, regs=repos)
    except ccp.CopyError as e:
        print("ctx: refused — %s" % e)
        return 4, {"command": "repo", "action": "copy", "id": repo["id"], "outcome": "busy" if isinstance(e, ccp.Busy)
                   else "refused", "error": str(e), "background": True}
    print(copy_summary(repo["id"], res))
    report = None
    if _copy_reported(prev, res) and c.store.exists():
        for _ in range(REPORT_LOCK_TRIES):
            try:
                with co.lock(c.home):
                    report = sy.write_report(c.store, at.date().isoformat(), copy_section(repo["id"], res), repo=repo["id"])
                break
            except co.Busy:
                time.sleep(1)
            except (cs.StoreError, OSError, ValueError) as e:   # the part is lost, the pass is not: the log says why
                print("копія %s: частину звіту не дописано — %s" % (repo["id"], cb.clip(str(e), cb.NOTE_CLIP)))
                break
        else:
            print("копія %s: частину звіту не дописано — сховище зайняте" % repo["id"])
    return (5 if res["outcome"] == "unreachable" else 0), dict(res, command="repo", action="copy", id=repo["id"],
                                                                background=True, report=report)


def start_copies(c, repos, at, home, context):
    """After the daily sync's block passes (C7): for each repository whose copy is due (`ctx_copy.background_choice`),
    `ctx repo copy <id> --background` as a process of its own that outlives the sync — started, never waited for
    (GROW_PM_COPY_FOREGROUND=1: run here, for the tests). → {id: "started" | "busy" | "not-due" | "failed"}; a repository
    with no copy is not named."""
    out = {}
    for repo in repos:
        choice = ccp.background_choice(home, repo, sy.instant(at))
        if choice is None:
            continue
        if choice != "due":
            out[repo["id"]] = choice
            continue
        args = [sys.executable, os.path.abspath(__file__), "repo", "copy", repo["id"], "--background", "--home", home,
                "--context", context]
        if os.environ.get("GROW_PM_COPY_FOREGROUND") == "1":
            args += ["--now", at]
        log = os.path.join(ccp.copy_dir(home, repo["id"]), ccp.SERVICE, "log")
        try:
            cs.check_target(log)
            if os.environ.get("GROW_PM_COPY_FOREGROUND") == "1":
                with open(log, "a", encoding="utf-8") as f:
                    subprocess.run(args, stdin=subprocess.DEVNULL, stdout=f, stderr=f, timeout=600)
            else:
                with open(log, "a", encoding="utf-8") as f:
                    subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=f, stderr=f, start_new_session=True,
                                     close_fds=True)
            out[repo["id"]] = "started"
        except (OSError, cs.PathRefused, ValueError):
            out[repo["id"]] = "failed"
    return out


def cmd_repo_copy(a, c):
    """`repo copy <id> [--restore PATH] [--now ISO]` (since v3.24.0): one pass of the plugin's own copy of an MCP-only
    repository into ~/.grow-pm/cores/<id>/ (ctx_copy, references/context-provider-protocol.md §12.12), in the foreground,
    progress on stderr. No store write (the copy is a cache of the server — no confirmation code, no journal line).
    Exit 0 complete | partial | held; 3 a usage error; 4 a folder that is not the plugin's, or busy; 5 no answer."""
    at = sy.instant(_sync_now(a.now))
    repo, repos = _copy_repo(c, a.id)
    if a.restore:
        try:
            src = ccp.restore(c.home, a.id, a.restore, at, repos)
        except (ccp.Busy, ccp.Refused) as e:
            print("ctx: refused — %s" % e)
            return 4, {"command": "repo", "action": "copy", "id": a.id, "outcome": "busy" if isinstance(e, ccp.Busy)
                       else "refused", "error": str(e)}
        except ccp.CopyError as e:
            raise Usage(str(e))
        print("копія %s: повернуто %s з %s" % (a.id, a.restore, os.path.dirname(src)))
        return 0, {"command": "repo", "action": "copy", "id": a.id, "restored": a.restore, "from": src}
    if a.background:
        return _copy_background(c, repo, repos, at)
    progress = lambda line: print(line, file=sys.stderr, flush=True)    # noqa: E731
    try:
        res = ccp.run(c.home, repo, at, regs=repos, progress=progress)
    except ccp.Busy as e:
        print("ctx: refused — %s" % e)
        return 4, {"command": "repo", "action": "copy", "id": a.id, "outcome": "busy", "error": str(e)}
    except ccp.CopyError as e:
        print("ctx: refused — %s" % e)
        return 4, {"command": "repo", "action": "copy", "id": a.id, "outcome": "refused", "error": str(e)}
    print(copy_summary(a.id, res))
    return (5 if res["outcome"] == "unreachable" else 0), dict(res, command="repo", action="copy", id=a.id)


def cmd_repo_kit_check(a, c):
    """`repo kit-check <folder>` (since v3.23.0): is the folder a sound provider kit (context-provider-protocol.md §9)?
    Reads only. Exit 0 sound (warnings said), 3 with every fault named."""
    warnings = []
    m, model, problems = ckit.check(os.path.abspath(os.path.expanduser(a.folder)), warnings)
    for p in problems:
        print("вада: %s" % p)
    for w in warnings:
        print("увага: %s" % w)
    if not problems:
        print("набір у порядку: %s · ядро %s · команд %d · блоків у файлі — див. ctx repo add" % (
            m.s("id"), (model or {}).get("version") or "?", len((model or {}).get("teams") or {})))
    return (3 if problems else 0), {"command": "repo", "action": "kit-check", "problems": problems, "warnings": warnings,
                                    "id": m.s("id") if m else None}


def _kit_add_plan(c, a):
    """(the dry run's facts, its text): the kit checked, the identity, the registration, the blocks it brings."""
    folder = os.path.abspath(os.path.expanduser(a.folder))
    warnings = []
    m, model, problems = ckit.check(folder, warnings)
    if problems:
        raise Usage("набір має вади — ctx repo kit-check %s:\n  %s" % (a.folder, "\n  ".join(problems)))
    rid = m.s("id")
    skipped = []
    if rid in [r["id"] for r in crp.load_repos(c.text, c.home, skipped=skipped)]:
        raise Usage("%s уже зареєстровано — оновлення: ctx provider plan %s" % (rid, rid))
    try:
        ident = ckit.identity(folder, m, model, a.email, team=a.team, role=a.role)
    except ValueError as e:
        raise Usage(str(e))
    text = ckit.registration(folder, m, model, ident, now()[:10])
    where = os.path.join(ckit.registrations_dir(c.store.root, c.text, c.home), "%s.yaml" % rid)
    if os.path.lexists(where):
        raise Usage("файл реєстрації вже є: %s — нічого не записано" % where)
    repo = crp.normalise(cc.read_yaml_subset(text))
    fetched = crp.fetch(repo)
    if fetched.get("error"):
        raise Usage("блоки набору не читаються: %s" % fetched["error"])
    p = cb.plan(c.store, c.copies, repo, fetched, now())
    adds = [r["block"] for r in p["rows"] if r["sign"] == "+"]
    code = cs.sha_text(json.dumps([text, adds, fetched.get("version")], ensure_ascii=False))[:8]
    lines = ["набір %s · ядро %s · %s" % (rid, model.get("version") or "?", folder),
             "команда: %s (%s) · %s" % (ident["team"], ident["team_title"], ident["team_from"]),
             "роль: %s · %s" % (ident["role"], ident["role_from"]),
             "Jira: запис — ask (context-connect спитає, чи є в тебе свій проєкт)",
             "реєстрація: %s (sync: off — щоденний синк вмикає context-connect)" % where,
             "блоки: %s → %s" % (", ".join("+ " + b for b in adds) or "жодного нового",
                                 cb._home_record(repo, {}, c.store.load(), m.s("title") or rid) or "новий запис «%s»" % (m.s("title") or rid))]
    lines += ["увага: %s" % w for w in warnings] + ["код: %s" % code]
    return {"id": rid, "ident": ident, "text": text, "where": where, "repo": repo, "fetched": fetched, "adds": adds,
            "code": code}, "\n".join(lines)


def cmd_repo_add(a, c):
    """`repo add <folder> --email E [--team T] [--role R] [--apply --code C]` (since v3.23.0): a provider kit from
    nothing in one command once shown — the kit checked, your team and role resolved, the registration written beside
    your store, every block of the kit added (`provider apply --add`, its own snapshot and journal line). Without
    --apply it reads only and prints a code; another code → exit 4, nothing written. The core folder is only read."""
    c.need_store()
    facts, text = _kit_add_plan(c, a)
    if not a.apply:
        print(text)
        return 0, {"command": "repo", "action": "add", "id": facts["id"], "code": facts["code"], "blocks": facts["adds"],
                   "registration": facts["where"], "team": facts["ident"]["team"], "role": facts["ident"]["role"]}
    if not a.code:
        raise Usage("--apply needs the code the dry run printed: ctx repo add %s --email %s" % (a.folder, a.email))
    with co.lock(c.home):
        c.guard()
        c.import_first()
        facts, text = _kit_add_plan(c, a)
        if facts["code"] != a.code:
            raise co.Refused("набір або сховище змінились — переглянь ще раз: ctx repo add %s --email %s" % (a.folder, a.email))
        res = cb.apply(c.store, c.copies, c.home, facts["repo"], facts["fetched"], {}, facts["adds"], now())
        os.makedirs(cs.check_target(os.path.dirname(facts["where"])), exist_ok=True)    # after the blocks: a failed
        cs.atomic_write(facts["where"], facts["text"])                                  # apply leaves no registration
        card = _refresh_card(c)
    print(text)
    print(cb.render_apply(res))
    print("реєстрацію записано: %s" % facts["where"])
    if card:
        print(card)
    return 0, {"command": "repo", "action": "add", "id": facts["id"], "registration": facts["where"], "written": res["written"],
               "snapshot": res["snapshot"], "blocks": facts["adds"]}


def _index_scope(c):
    """(roots, store_rel, blocks_rels) of the section index for this context — the search context of
    `ctx_search.context_for` (since v3.16.0 one function for `ctx index` and `ctx search`): the roots of `ci.scope`,
    the store's folder and the blocks file of every repository (the registration's, else, for a root, its core
    manifest's), each as the index names a file."""
    s = cs_.context_for(c.home, c.text)
    return s["roots"], s["store_rel"], s["blocks_rels"]


def _download_line(dl):
    """The line of `ctx index rebuild --download`: what came down from iCloud, what is left and why — a Ctrl-C first,
    even one in the scan, before anything was found."""
    head = "iCloud: завантажено %d з %d" % (dl["downloaded"], dl["candidates"])
    if dl["interrupted"]:
        return head + ", зупинено (Ctrl-C) — індекс не перебудовано"
    if not dl["candidates"]:
        return "iCloud: нічого завантажувати"
    if not dl["left"]:
        return head
    why = (["не встигли за %d с: %d" % (ci.DOWNLOAD_S, dl["timed_out"])] if dl["timed_out"] else []) \
        + (["не прочитано: %d" % dl["failed"]] if dl["failed"] else [])
    return head + ", лишилось %d" % dl["left"] + (" (%s)" % "; ".join(why) if why else "")


def _download_progress_printer(every=100, seconds=60.0, clock=time.monotonic):
    """The progress of `rebuild --download`: «iCloud: N з M…» every `every` files and at least once in `seconds` (an
    offline run reads a file in 30 s), never for the last file — the summary line says it."""
    last = [clock()]

    def show(done, total):
        now = clock()
        if done < total and (done % every == 0 or now - last[0] >= seconds):
            print("iCloud: %d з %d…" % (done, total), flush=True)
            last[0] = now

    return show


def cmd_index(a, c):
    roots, store_rel, blocks = _index_scope(c)
    if not roots:
        print("index: nothing to index — no vault in local-context.md and no registered repository with a folder on disk")
        return 3, {"command": "index", "action": a.action, "error": "no vault and no repository folder"}
    idx = ci.Index(c.home)
    dl = None
    if getattr(a, "download", False):
        if idx.lock_held():                     # before minutes of downloading, not after
            raise co.Busy("another process is updating the index (%s)" % idx.lock_path)
        dl = ci.download(roots, store_rel, blocks, progress=_download_progress_printer())
        print(_download_line(dl), flush=True)
        if dl["interrupted"]:
            return 130, {"command": "index", "action": a.action, "download": dl}
    try:
        if a.action == "rebuild":
            res = idx.rebuild(roots, store_rel, blocks)
            if res["locked"]:
                raise co.Busy("another process is updating the index (%s)" % idx.lock_path)
        else:
            res = idx.refresh(roots, store_rel, blocks)
    except sqlite3.Error as e:
        print("index: %s — %s" % (idx.db_path, e))
        err = {"command": "index", "action": a.action, "error": str(e)}
        return 3, dict(err, download=dl) if dl else err
    s = idx.status()
    print("index: %s" % idx.dir)
    for r in roots:
        print("  %s  %s" % (r["source"], r["path"]))
    print("  files %d · sections %d · schema %s · updated %s" % (s["files"], s["sections"], s["schema"] or "—",
                                                                (s["updated"] or "—")[:16].replace("T", " ")))
    if res["locked"]:
        print("  another process is updating it — the index as it is")
    if res["rebuilt"] and a.action != "rebuild":
        print("  the index could not be read or had another schema — built again (the old one: %s.broken)" % idx.db_path)
    if s["skipped_dataless"]:
        own = dl["left"] if dl else len(ci.evicted(roots, store_rel, blocks))   # the plugin folder's: --download's
        print("  not downloaded (iCloud), not read: %d%s" % (s["skipped_dataless"], " (plugin folder: %d — ctx index "
                                                              "rebuild --download)" % own if own else ""))
    if res["skipped_large"]:
        print("  over %d bytes, not indexed: %d" % (ci.MAX_BYTES, res["skipped_large"]))
    if s["pending"]:
        print("індекс оновлюється: %d файлів ще не переглянуто" % s["pending"])
    out = {"command": "index", "action": a.action, "schema": s["schema"], "updated": s["updated"], "files": s["files"],
           "sections": s["sections"], "pending": s["pending"], "skipped_dataless": s["skipped_dataless"]}
    return 0, dict(out, download=dl) if dl else out


def _search_kinds(value):
    """The kinds of `--sources own,local,mcp` (all three when not given); an unknown or empty one is bad usage."""
    if value is None:
        return cs_.KINDS
    kinds = [k.strip() for k in value.split(",") if k.strip()]
    bad = [k for k in kinds if k not in cs_.KINDS]
    if not kinds or bad:
        raise Usage("--sources takes %s, comma-separated%s" % (", ".join(cs_.KINDS), ": not %s" % ", ".join(bad) if bad else ""))
    return tuple(dict.fromkeys(kinds))


SEARCH_ACTIONS = ("remember", "forget", "eval")
_SEARCH_OPTS = {"q": "--q", "get": "--get", "skill": "--skill", "product": "--product", "limit": "--limit",
                "sources": "--sources", "no_hints": "--no-hints", "pick": "--pick", "not_": "--not", "golden": "--golden",
                "full": "--full"}
_SEARCH_TAKES = {None: ("q", "get", "skill", "product", "limit", "sources", "no_hints", "full"),
                 "remember": ("q", "product", "pick", "not_"), "forget": ("q", "product"),
                 "eval": ("golden", "no_hints", "sources")}


def _search_options(a):
    """Refuse an option the search's action does not take (a usage error that names it)."""
    takes = _SEARCH_TAKES[a.action]
    given = [flag for key, flag in _SEARCH_OPTS.items() if key not in takes and getattr(a, key, None) not in (None, False, [])]
    if given:
        raise Usage("search%s takes no %s" % (" " + a.action if a.action else "", ", ".join(given)))


def cmd_search(a, c):
    """`search`: the question and its variants through the section index, the local indexes and MCP
    (ctx_search.run), or `--get ID|PATH|NAME`: one section, or a whole note, with its line of provenance
    (ctx_search.get). Reads only — no store lock, no import, the store need not exist; writes only
    `<home>/.grow-pm/index/` (the index, last.json).
    `search remember|forget` (since v3.16.0) write the store's search memory (`_search_hint`); `search eval` measures
    the search on a golden set (`_search_eval`) and writes nothing but the index."""
    _search_options(a)
    if a.action in ("remember", "forget"):
        return _search_hint(a, c)
    if a.action == "eval":
        return _search_eval(a, c)
    if a.full and a.get is None:
        raise Usage("--full goes with --get")
    sctx = cs_.context_for(c.home, c.text, store_root=c.store.root)
    if a.get is not None:
        if a.q:
            raise Usage("search takes --q or --get, not both")
        try:
            header, text = cs_.get(sctx, a.get, full=a.full)
        except cs_.GetError as e:
            print("search: %s" % e)
            return e.code, {"command": "search", "action": "get", "id": a.get, "error": str(e)}
        if not a.json:
            print(header)
            print(text)
        return 0, {"command": "search", "action": "get", "id": a.get, "header": header, "text": text if a.json else None}
    if not a.q:
        raise Usage("search takes --q TEXT (once or more) or --get ID|PATH|NAME")
    which = _search_kinds(a.sources)
    limit = cs_.LIMIT if a.limit is None else a.limit
    if limit < 1:
        raise Usage("--limit takes a number from 1")
    if a.skill:
        try:
            cr.manifest_for(cr.load_manifest(), a.skill)
        except KeyError:
            raise Usage("no such skill: %s" % a.skill)
    res = cs_.run(sctx, a.q, skill=a.skill, product=a.product, limit=limit, which=which, use_hints=not a.no_hints)
    last = res.pop("last", {})
    said = sum(1 for s in res["sources"] if s["answered"])
    res = dict(res, command="search", counts={"candidates": len(res["candidates"]), "sources": said,
                                              "skipped": len(res["sources"]) - said})
    if not res["sources"]:
        print("search: nothing to search — no vault in local-context.md, no registered repository with a folder on disk, "
              "no local index or MCP%s" % (" of the kinds asked (%s)" % ",".join(which) if a.sources else ""))
        return 3, dict(res, error="nothing to search")
    why = cs_.save_last(c.home, last) if said else None     # a failed save is one line, never the exit code
    if why:
        res["notes"].append(cs_.LAST_NOTE % why)
    if not a.json:
        sys.stdout.write(cs_.render(res, a.q))
    return (0 if said else 5), res


def _entity_action(a):
    """(action, words) of `ctx entity`: `same`/`not-same` with two cards, `pairs`, else a request (None) — the words of
    the request, or --q."""
    words = list(getattr(a, "words", None) or [])
    if getattr(a, "q", None):
        return None, words
    if words and words[0] in ("same", "not-same"):
        return words[0], words[1:]
    if words == ["pairs"]:
        return "pairs", []
    if words == ["apply"]:
        return "apply", []
    return None, words


def _team_records(c, repos):
    """team.members of every store team record, by the team entity it matches (plan C8): a function of a registry that
    gives {entity id: [record candidates]} — read once, read only (ctx_resolve.slot_context, as `ctx read`); no store,
    or one that cannot be read: nothing."""
    got = {}

    def of(reg):
        if "v" not in got:
            out = {}
            try:
                if c.store.exists():
                    sc = rv.slot_context(c.store, c.copies, repos, None, now())
                    results = {a["place"]: a["result"] for a in rv.slot_answers(sc, "team.members")}
                    for rec in sc["records"]:
                        r = results.get(rec["id"])
                        if rec.get("type") == "team" and r and r["shown"]:
                            ent, _ = es.team_entity(reg, rec.get("title"))
                            if ent:
                                got_ = out.setdefault(ent["id"], {"cands": [], "exclusive": False})
                                got_["cands"].extend(es.record_candidates(r["shown"]))
                                if r["why"] == rv.WHY_RULE or str(r.get("prefer", "")).startswith("repo:"):
                                    got_["exclusive"] = True       # the list `ctx read` prints alone (final review I2)
            except Exception:  # noqa: BLE001 — the cards still answer; a record that cannot be read adds nothing
                out = {}
            got["v"] = out
        return got["v"]
    return of


NO_STORE_ANSWER = "немає сховища — відповідь не збережено"
NO_STORE_APPLY = "немає сховища — мости не пишуться: `ctx undo` живе у сховищі (ctx migrate --apply)"


def cmd_entity(a, c):
    """`entity`: who someone or something is (ctx_entity.run), `entity pairs`, `entity same|not-same A B`
    (`_entity_answer`). Reads the index, a local index and `.state/entities.json`; no store lock but for an answer."""
    action, words = _entity_action(a)
    if a.kind and a.kind not in ce.KINDS:
        raise Usage("--kind takes %s" % ", ".join(ce.KINDS))
    cat = sl.load_catalogue()
    for slot in a.slot or ():
        if not sl.card_slot_info(cat, slot):
            raise Usage("--slot takes a slot of an entity's cards: %s" % ", ".join(
                dict.fromkeys(s_ for k in sl.CARD_KINDS for s_ in sl.card_slots(cat, k))))
    if a.skill:
        try:
            cr.manifest_for(cr.load_manifest(), a.skill)
        except KeyError:
            raise Usage("no such skill: %s" % a.skill)
    if (getattr(a, "apply", False) or getattr(a, "code", None)) and action != "apply":
        raise Usage("--apply and --code belong to `entity apply`")
    if a.slot and action in ("same", "not-same", "pairs", "apply"):
        raise Usage("--slot asks for an entity's slots: not with %s" % action)
    if action in ("same", "not-same"):
        return _entity_answer(a, c, action, words)
    if action == "apply":
        return _entity_apply(a, c)
    sctx = cs_.context_for(c.home, c.text, store_root=c.store.root)
    if not sctx["roots"] and not cs_.sources(sctx["text"], sctx["repos"], ("local",)):
        print("entity: nothing to search — no vault in local-context.md, no registered repository with a folder on disk, "
              "no local index")
        return 3, {"command": "entity", "error": "nothing to search"}
    if action == "pairs":
        res = ce.pairs_result(sctx, kind=a.kind, store=c.store)
    else:
        if a.q and words:
            raise Usage("entity takes a request or --q, not both")
        queries = [q.strip() for q in a.q] if a.q else [" ".join(words).strip()]
        if not all(queries):
            raise Usage("entity takes a request: an e-mail, a Jira key, a path or a name (or pairs, same, not-same)")
        records = _team_records(c, sctx["repos"])       # the registrations context_for read, read once
        if len(queries) > 1:
            res = ce.run_many(sctx, queries, kind=a.kind, skill=a.skill, store=c.store, slots=a.slot, records=records)
        else:
            res = ce.run(sctx, queries[0], kind=a.kind, skill=a.skill, store=c.store, slots=a.slot, records=records)
    if not res["read"]:
        why = "; ".join(res["notes"]) or "індексу немає"
        print(ce.NOT_READ % why)
        return 5, dict(res, error="not read")
    if not a.json:
        sys.stdout.write(ce.render(res))
    return 0, res


def cmd_graph(a, c):
    """`graph <request> [--depth 1|2] [--kind K,…]` (since v4.0.0, ctx_graph.run): the notes around a note or an entity,
    from the edges of the index. Reads the index (refreshed as `entity` does); writes nothing else."""
    kinds = [k.strip() for k in (a.kind or "").split(",") if k.strip()]
    for k in kinds:
        if k not in GRAPH_KINDS and not k.startswith("fm:"):
            raise Usage("--kind takes %s or fm:<field>" % ", ".join(GRAPH_KINDS))
    sctx = cs_.context_for(c.home, c.text, store_root=c.store.root)
    if not sctx["roots"]:
        print("graph: nothing to walk — no vault in local-context.md, no registered repository with a folder on disk")
        return 3, {"command": "graph", "error": "nothing to walk"}
    res = cg.run(sctx, " ".join(a.words).strip(), depth=a.depth, kinds=kinds, store=c.store)
    if not res["read"]:
        print(cg.NOT_READ % ("; ".join(res["notes"]) or "індексу немає"))
        return 5, dict(res, error="not read")
    if not a.json:
        sys.stdout.write(cg.render(res))
    return (3 if res["how"] in ("none", "several") else 0), res


GRAPH_KINDS = ("wikilink", "embed", "fm", "same_as", "mention")
NO_STORE_NORMALIZE = "немає сховища — нормалізатор не пише: `ctx undo` живе у сховищі (ctx migrate --apply)"


def cmd_vault(a, c):
    """`vault normalize [--only OPS] [--skip N,…]` (since v4.0.0, ctx_normalize): what the audit finds and a machine can
    fix in your layer — a report and its code; `--apply --code <code>` writes it (a snapshot of the files changed, one
    journal line, `ctx undo`). No store: the report only (exit 3 on --apply); an index that did not answer: exit 5."""
    only = [o.strip() for o in (a.only or "").split(",") if o.strip()] or list(cnz.OPS)
    for o in only:
        if o not in cnz.OPS:
            raise Usage("--only takes %s" % ", ".join(cnz.OPS))
    try:
        skip = [int(x) for x in (a.skip or "").split(",") if x.strip()]
    except ValueError:
        raise Usage("--skip takes the numbers of the report's rows: --skip 2,5")
    if a.apply and not a.code:
        raise Usage("vault normalize --apply takes --code <the report's code>: run `ctx vault normalize` first")
    if a.code and not a.apply:
        raise Usage("--code goes with --apply: `ctx vault normalize --apply --code <code>`")
    sctx = cs_.context_for(c.home, c.text, store_root=c.store.root)
    if not ca.own_roots(sctx):
        print("vault normalize: nothing to normalize — no vault in local-context.md")
        return 3, {"command": "vault", "action": "normalize", "error": "nothing to normalize"}
    if not a.apply:
        res = cnz.plan(sctx, c.context, c.store, c.home, only, now())
        if not res["read"]:
            print("vault normalize: індекс не відповів — %s" % ("; ".join(res["notes"]) or "індексу немає"))
            return 5, dict(res, error="not read")
        if not a.json:
            sys.stdout.write(cnz.render(res))
            if not c.store.exists() and res["rows"]:
                print(NO_STORE_NORMALIZE)
        return 0, res
    if not c.store.exists():
        print(NO_STORE_NORMALIZE)
        return 3, {"command": "vault", "action": "normalize", "error": NO_STORE_NORMALIZE}
    with co.lock(c.home):
        c.guard()
        res = cnz.plan(sctx, c.context, c.store, c.home, only, now())
        if not res["read"]:
            print("vault normalize: індекс не відповів — %s" % ("; ".join(res["notes"]) or "індексу немає"))
            return 5, dict(res, error="not read", written=[])
        if res["code"] != a.code.strip().lower():
            raise co.Refused("звіт змінився — переглянь ще раз: ctx vault normalize")
        if res["rows"]:
            c.import_first()
        t = now()
        done = cnz.apply(sctx, res, skip, lambda notes: co.snapshot(c.store, c.copies, c.home, "vault-normalize",
                                                                    notes=notes), c.store.journal, t)
    merged = {k: list(v) for k, v in res["skipped"].items()}
    for k, v in done["skipped"].items():
        merged[k] = list(dict.fromkeys(merged.get(k, []) + v))
    shown = dict(res, rows=done["written"], skipped=merged)
    if not a.json:
        sys.stdout.write(cnz.render(shown, written=True))
        if done["written"]:
            print("скасувати: ctx undo")
    return 0, dict(res, rows=done["written"], planned=res["rows"], written=done["written"], skipped=merged,
                   snapshot=done["snapshot"])


def cmd_audit(a, c):
    """`audit [--all]` (since v4.0.0, ctx_audit.run): what breaks the links of your layer. Reads the index (refreshed as
    `entity` does) and the downloaded notes of your layer; writes only its last result in ~/.grow-pm/audit/. Exit 0;
    3 with nothing to audit; 5 when the index did not answer."""
    sctx = cs_.context_for(c.home, c.text, store_root=c.store.root)
    if not ca.own_roots(sctx):
        print("audit: nothing to audit — no vault in local-context.md")
        return 3, {"command": "audit", "error": "nothing to audit"}
    res = ca.run(sctx, c.context, store=c.store, all_=a.all_, now=now())
    if not res["read"]:
        print("audit: індекс не відповів — %s" % ("; ".join(res["notes"]) or "індексу немає"))
        return 5, dict(res, error="not read")
    if not a.json:
        sys.stdout.write(ca.render(res))
    return 0, res


def _entity_apply(a, c):
    """`entity apply` (v3.20.0, ctx_bridges): the bridges your layer lacks — a report and its code; `--apply --code
    <code>` writes them. No store: exit 3 (`ctx undo` lives in the store); an index that did not answer: exit 5."""
    out = {"command": "entity", "action": "apply"}
    if not c.store.exists():
        print(NO_STORE_APPLY)
        return 3, dict(out, error=NO_STORE_APPLY)
    if a.apply and not a.code:
        raise Usage("entity apply --apply takes --code <the report's code>: run `ctx entity apply` first")
    if a.code and not a.apply:
        raise Usage("--code goes with --apply: `ctx entity apply --apply --code <code>`")
    sctx = cs_.context_for(c.home, c.text, store_root=c.store.root)
    if not a.apply:
        res = cbr.plan_result(sctx, c.store, kind=a.kind)
        if not res["read"]:
            print(ce.NOT_READ % ("; ".join(res["notes"]) or "індексу немає"))
            return 5, dict(res, error="not read")
        if not a.json:
            sys.stdout.write(cbr.render(res))
        return 0, res
    with co.lock(c.home):
        c.guard()
        res = cbr.plan_result(sctx, c.store, kind=a.kind)
        if not res["read"]:            # a plan without the index is not the plan the report showed: nothing written
            print(ce.NOT_READ % ("; ".join(res["notes"]) or "індексу немає"))
            return 5, dict(res, error="not read", written=[])
        if res.get("blocked"):
            raise cs.StoreError(res["blocked"])         # your not-same unread: never a bridge it might deny
        if res["code"] != a.code.strip().lower():
            raise co.Refused(cbr.CHANGED)               # refused before anything is touched, the copies included
        if res["rows"]:
            c.import_first()            # an edit to local-context.md waiting is kept before the snapshot `ctx undo` uses
        regs, _ = cc.boundary_registrations(cc.vault_entries(c.text),
                                            extra_dirs=[os.path.join(c.home, ".grow-pm", "providers")])
        t = now()
        done = cbr.apply_plan(sctx, c.store, c.copies, c.home, res, regs, t[:10],
                              lambda notes: co.snapshot(c.store, c.copies, c.home, "entity-apply", notes=notes),
                              c.store.journal, t)
    merged = {k: list(v) for k, v in res["skipped"].items()}
    for k, v in done["skipped"].items():            # a reason of the plan and of the write: both lists kept (final M5)
        merged[k] = list(dict.fromkeys(merged.get(k, []) + v))
    shown = dict(res, rows=done["written"], skipped=merged)
    if not a.json:
        sys.stdout.write(cbr.render(shown, written=True))
        if done["written"]:
            print("скасувати: ctx undo")
    return 0, dict(res, rows=done["written"], planned=res["rows"], written=done["written"], skipped=merged,
                   snapshot=done["snapshot"])


def _entity_answer(a, c, action, words):
    """`entity same|not-same A B`: your answer in `.state/entities.json` — the lock, the guard, the memory read (one that
    cannot be read stops the run), the edits waiting imported, a snapshot, the memory written, one journal line {op
    entity, action, cards}; `ctx undo` takes it back. No store: exit 3."""
    if len(words) != 2:
        raise Usage("entity %s takes two cards: a path, a link or a name one card alone carries" % action)
    out = {"command": "entity", "action": action, "cards": [], "changed": False, "snapshot": None}
    if not c.store.exists():
        print(NO_STORE_ANSWER)
        return 3, dict(out, error=NO_STORE_ANSWER)
    sctx = cs_.context_for(c.home, c.text, store_root=c.store.root)
    _, reg, _, _, _ = ce._prepare(sctx, None, None)
    try:
        x, y = ce.card_of(reg, words[0]), ce.card_of(reg, words[1])
    except ValueError as e:
        if reg.unread:                  # the index did not answer: a card it holds is no «не картка» (v3.19.0, C11)
            line = ce.BUSY_ANSWER if reg.unread == ci.BUSY_NOTE else ce.NOT_READ % reg.unread
            print(line)
            return 5, dict(out, error=line)
        raise Usage(str(e))
    if x["path"] == y["path"]:
        raise Usage("одна й та сама картка: %s" % x["path"])
    if x["kind"] != y["kind"]:
        raise Usage("картки різних видів: %s (%s), %s (%s)" % (x["path"], x["kind"], y["path"], y["kind"]))
    cards = sorted((x["path"], y["path"]))
    out["cards"] = cards
    with co.lock(c.home):
        c.guard()
        mem = ce.load_memory(c.store)
        c.import_first()
        changed = ce.answer(mem, cards[0], cards[1], action == "same", now()[:10])
        out["changed"] = changed
        if not changed:
            print("unchanged — the memory already says so: %s %s ↔ %s" % (action, cards[0], cards[1]))
            return 0, out
        snap = co.snapshot(c.store, c.copies, c.home, "entity")
        ce.save_memory(c.store, mem)
        out["snapshot"] = snap
        c.store.journal({"ts": now(), "op": "entity", "action": action, "cards": cards, "ids": [],
                         "source": "ctx-entity", "snapshot": snap})
    print("entity %s: %s ↔ %s · snapshot %s (back: ctx undo)" % (action, cards[0], cards[1], snap))
    return 0, out


NO_STORE_HINT = "немає сховища — підказку не збережено"
NO_STORE_FORGET = "немає сховища — підказок немає"


def _search_hint(a, c):
    """`search remember --q REQUEST --pick ID|PATH [--not ID|PATH] [--product P]` and `search forget --q REQUEST
    [--product P]`: your choices, kept in the store's `.state/search.json` (ctx_hints). The request is the first --q (the
    others, its variants, are not remembered); an id is one of the last searches (last.json), a path is the note's.
    A writing command — the lock, the guard, the memory read (one that cannot be read stops the run before anything is
    imported), the edits waiting imported, a snapshot, the memory written, one journal line {op search, action, q};
    `ctx undo` takes it back. No record changes, so nothing is compiled. One that changes nothing writes nothing and
    takes no snapshot. No store: exit 3."""
    if not a.q:
        raise Usage("search %s takes --q TEXT: the request" % a.action)
    q = a.q[0]
    if not ch.terms(q):
        raise Usage("the request %r has no words to %s (only stop words)" % (q, a.action))
    good, bad = [], []
    if a.action == "remember":
        if not a.pick and not a.not_:
            raise Usage("search remember takes --pick ID|PATH (the right note), --not ID|PATH (one that is not it), or both")
        try:
            good = [ch.resolve(v, cs_.last_path(c.home)) for v in a.pick or []]
            bad = [ch.resolve(v, cs_.last_path(c.home)) for v in a.not_ or []]
        except ValueError as e:
            raise Usage(str(e))
    out = {"command": "search", "action": a.action, "q": q, "product": a.product or "", "good": good, "bad": bad}
    if not c.store.exists():
        line = NO_STORE_HINT if a.action == "remember" else NO_STORE_FORGET
        print(line)
        return 3, dict(out, error=line)
    with co.lock(c.home):
        c.guard()
        mem = ch.load(c.store)
        pre = c.import_first()
        if a.action == "remember":
            changed = ch.remember(mem, q, a.product, good, bad, now()[:10])
        else:
            changed = ch.forget(mem, q, a.product) > 0
        out.update(changed=changed, snapshot=None, hints=len(mem["hints"]), imported=pre["changed"] + pre["added"])
        if not changed:
            print("unchanged — the memory already says so: «%s»" % q if a.action == "remember" else
                  "unchanged — the memory holds no hint for «%s»" % q)
            return 0, out
        t = now()
        snap = co.snapshot(c.store, c.copies, c.home, "search")
        out["hints"] = len(ch.save(c.store, mem)["hints"])
        out["snapshot"] = snap
        c.store.journal({"ts": t, "op": "search", "action": a.action, "q": q, "product": a.product or "", "ids": [],
                         "source": "ctx-search", "snapshot": snap})
    what = " · ".join(p for p in ("так: " + ", ".join(good) if good else "", "не те: " + ", ".join(bad) if bad else "") if p)
    print("search %s: «%s»%s%s · snapshot %s (back: ctx undo)" % (a.action, q, " (%s)" % a.product if a.product else "",
                                                                  " → " + what if what else "", snap))
    return 0, out


def _share(x):
    return "—" if x is None else "%.3f" % x


def _search_eval(a, c):
    """`search eval [--golden PATH] [--no-hints] [--json]`: the level-1 numbers of the search on a golden set
    (ctx_hints.evaluate) — the store's `search/golden.yaml` unless --golden names one (no store: --golden is needed),
    plus, without --no-hints, the hints of the store's memory as rows `source: choice`. Each row with an answer is
    searched with its frozen variants (`[q] + variants`, the first 50, its product and skill) and with its question
    alone; the hints weigh both unless --no-hints. The index is refreshed once, by the first search (again only while
    it is not built — another process building it), not at each. Writes nothing but the index (no last.json, no
    store). Exit 3: no golden set, one that does not read, or nothing to search."""
    which = _search_kinds(a.sources)
    golden = a.golden
    if not golden:
        if not c.store.exists():
            print("eval: немає сховища — назви еталонний набір: --golden ШЛЯХ")
            return 3, {"command": "search", "action": "eval", "error": "no store and no --golden"}
        golden = os.path.join(c.store.root, "search", "golden.yaml")
    try:
        rows = ch.load_golden(golden)
    except (OSError, ValueError) as e:
        print("eval: the golden set %s cannot be read — %s" % (golden, getattr(e, "strerror", None) or e))
        return 3, {"command": "search", "action": "eval", "golden": golden, "error": str(e)}
    notes, extra = [], []
    for skill in sorted({r["skill"] for r in rows if r.get("skill")}):
        try:
            cr.manifest_for(cr.load_manifest(), skill)
        except KeyError:
            notes.append("еталонний набір: скіла %s немає — його рядки без ваги типів" % skill)
    if not a.no_hints and c.store.exists():
        try:
            extra = ch.hint_rows(ch.load(c.store))
        except cs.StoreError as e:
            notes.append(ch.UNREAD_NOTE % e)
    sctx = cs_.context_for(c.home, c.text, store_root=c.store.root)
    if not cs_.sources(sctx["text"], sctx["repos"], which):
        print("eval: nothing to search — no vault in local-context.md, no registered repository with a folder on disk, "
              "no local index or MCP")
        return 3, {"command": "search", "action": "eval", "golden": golden, "error": "nothing to search"}

    built = []          # the index is refreshed once per eval: until one search finds it built, never after

    def ask(queries, row):
        res = cs_.run(sctx, queries, skill=row.get("skill") or None, product=row.get("product") or None,
                      limit=cs_.LIST_LIMIT, which=which, use_hints=not a.no_hints, refresh=not built)
        if not built and (res.get("index") is None or res["index"].get("updated")):
            built.append(True)
        return res

    res = ch.evaluate(rows + extra, ask)
    for n in res.pop("notes"):
        if n not in notes:
            notes.append(n)
    out = dict(res, command="search", action="eval", golden=golden, hints=len(extra), notes=notes)
    if not a.json:
        print("eval: %s · запитів %d (+ порожніх %d) · підказок %d" % (golden, res["n"], res["empty_n"], len(extra)))
        print("recall@50 %s (q + варіанти) · %s (лише q) · MRR %s" % (_share(res["recall50"]), _share(res["recall50_q_only"]),
                                                                     _share(res["mrr"])))
        for k in sorted(res["by_class"]):
            v = res["by_class"][k]
            print("  %s: %d · recall@50 %s · лише q %s · MRR %s" % (k, v["n"], _share(v["recall50"]),
                                                                   _share(v["recall50_q_only"]), _share(v["mrr"])))
        if res["empty_n"]:
            print("порожні: %d · кандидатів у топ-5 у середньому %.1f" % (res["empty_n"], res["empty_top5_mean"]))
        missed = [r["q"] for r in res["rows"] if "rank" in r and r["rank"] is None]
        if missed:
            print("не знайдено серед 50: " + "; ".join("«%s»" % q for q in missed))
        for n in notes:
            print(n)
    return 0, out


def _unread(skipped):
    """The registrations that could not be read, as `<path> (<reason>)`, for a message."""
    return "; ".join("%s (%s)" % (p, why) for p, why in skipped)


def _not_registered(rid, skipped):
    """The usage error for a repository id no registration has: with a registration that could not be read (since
    v3.13.1; `skipped`, as load_repos fills it) the message names it — it may be that one, still downloading."""
    return "no repository %r is registered — `ctx.py repo list`" % rid + (
        " — a registration could not be read: %s; it may still be downloading" % _unread(skipped) if skipped else "")


def _repository(c, rid):
    """The registered repository named `rid`; an unknown one, or a search-only registration (it publishes no blocks),
    is a usage error (exit 3). Unknown while a registration could not be read (since v3.13.1): the message names it —
    it may be that one, still downloading."""
    skipped = []
    repos = [r for r in crp.load_repos(c.text, c.home, skipped=skipped) if r["id"] == rid]
    if not repos:
        raise Usage(_not_registered(rid, skipped))
    if crp.search_only(repos[0]):
        raise Usage("%s is a search-only registration (no blocks_file and no core folder): it publishes no blocks for "
                    "`ctx provider`" % cb.clip(rid, cb.HEADER_CLIP))
    return repos[0]


def _refresh_card(c):
    """Bring the card's line about the repositories up to date after the state moved. The state is already written by
    then, so a card that cannot be read or written (an INDEX.md that has not arrived from iCloud, say) is one line for
    the caller to print after its report — "card not refreshed: <why>" — and never a lost report or another exit
    code. A registration that could not be read leaves the card's line as it is, with the same line naming it (since
    v3.13.1). Returns that line, or None."""
    skipped = []
    try:
        co.refresh_card_repos(c.store, c.home, now()[:10], skipped=skipped)
    except Exception as e:  # noqa: BLE001 — see above
        return "card not refreshed: %s" % cb.clip(e, cb.NOTE_CLIP)
    if skipped:
        return "card not refreshed: a registration could not be read: %s" % _unread(skipped)
    return None


def cmd_provider_adopt(a, c):
    c.need_store()
    repo = _repository(c, a.repo)
    fetched = crp.fetch(repo)
    if fetched["error"]:
        print("ctx: the repository %s is unreachable — %s" % (repo["id"], fetched["error"]))
        print("nothing written")
        return 5, {"command": "provider", "action": "adopt", "repo": repo["id"], "written": False, "error": fetched["error"]}
    plan = co.plan_sync(c.store, c.copies)
    pending = sum(co.pending(plan).values()) + len(plan["conflicts"]) + len(plan["missing"])
    imported, waited = [], 0
    if a.apply:                                         # like every writing command: the edits waiting go in first, so
        with co.lock(c.home):                           # the adopt's snapshot holds them and `ctx undo` never takes them back
            c.guard()
            pre = c.import_first()
            imported, waited, pending = pre["changed"] + pre["added"], pending, 0
            res = cb.adopt(c.store, c.copies, c.home, repo, fetched, now(), True)
            card_note = _refresh_card(c) if res["written"] else None
    else:
        res = cb.adopt(c.store, c.copies, c.home, repo, fetched, now(), False)
        card_note = None
    gets = [b for b, o in res["blocks"].items() if o in ("base", "edit")]
    print("adopt %s — source %s, %d block(s) of %s in your context" % (repo["id"], fetched["source"], len(res["blocks"]),
                                                                     cb.namespace_of(repo, fetched)))
    if res["blocks"]:
        print(_table([("block", "result", "why")] + [(b, o, res["why"][b]) for b, o in res["blocks"].items()]))
    if res["new"]:
        print("offered by the repository, not in your context (the plan shows +): " + ", ".join(res["new"]))
    for x in res["problems"]:
        print("problem: block %s in %s — %s (left out)" % (x["block"] or "?", x["host"], x["why"]))
    if pending:
        print("note: %d change(s) to local-context.md or the records are not imported yet — this dry run does not see them; "
              "--apply imports them first" % pending)
    elif a.apply and waited:
        print("imported first: %d change(s) to local-context.md or the records" % waited)
    if res["written"]:
        print("adopted %d block(s) · snapshot %s (back: ctx undo)" % (len(gets), res["snapshot"]))
    elif a.apply:
        print("nothing to adopt — no base written")
    elif gets:
        print("dry run — nothing written; `ctx provider adopt %s --apply` sets the bases" % repo["id"])
    else:
        print("dry run — nothing written, and there is nothing to adopt")
    if card_note:
        print(card_note)
    return 0, dict(res, command="provider", action="adopt", pending=pending, imported=imported)


def _product_repos(c, repos, wanted):
    """The repositories that serve the product `wanted` names (picked among the product records the way `ctx read`
    picks it), and those that name no product (they serve all). An unknown or ambiguous product is a usage error."""
    records, _, _ = cr._live_view(c.store, c.copies, now())
    products = [r for r in records if r["type"] == "product"]
    prod, _ = cr._pick_product(products, wanted)
    if prod is None:
        raise Usage("no single product matches %r — products: %s" % (
            wanted, ", ".join(p["title"].split(":", 1)[-1].strip() for p in products) or "none"))
    return [r for r in repos if crp.serves_product(r, prod)]


def _in_scope(c, a, skipped, registered=None):
    """(repositories, ids of the paused ones, ids of the search-only ones) of a plan or an apply: the one named —
    paused or not; a search-only one is a usage error — else those of the product --product names (and those serving
    every product), else all; without a name the paused and the search-only registrations (no blocks_file, no core
    folder: `crp.search_only`) are left out. Prints the line for an empty scope, one line "призупинено: <id>" per paused
    repository and one line "лише пошук: <id>" per search-only registration; without a name, also one line
    "unreadable registration: <path> (<reason>)" per registration that could not be read — not there within its 3 s
    (iCloud), or broken — as `repo list` prints it, the pair appended to `skipped` (since v3.13.1). Without a name,
    `registered` (a set, since v3.14) gets the id of every registration read, in --product's scope or not."""
    if a.repo:
        return [_repository(c, a.repo)], [], []
    repos = crp.load_repos(c.text, c.home, skipped=skipped)
    if registered is not None:
        registered.update(r["id"] for r in repos)
    for path, why in skipped:
        print("unreadable registration: %s (%s)" % (path, why))
    if a.product:
        repos = _product_repos(c, repos, a.product)
    search = [r["id"] for r in repos if crp.search_only(r)]
    repos = [r for r in repos if not crp.search_only(r)]
    paused = [r["id"] for r in repos if r["status"] == "paused"]
    repos = [r for r in repos if r["status"] != "paused"]
    if not repos and not paused and not search:
        print(NO_REPOS if not a.product else "no repository serves the product %r" % a.product)
    for rid in paused:
        print("призупинено: %s" % cb.clip(rid, cb.HEADER_CLIP))
    for rid in search:
        print("лише пошук: %s" % cb.clip(rid, cb.HEADER_CLIP))
    return repos, paused, search


def cmd_provider_plan(a, c):
    c.need_store()
    skipped = []
    repos, paused, search = _in_scope(c, a, skipped)
    plans, down = [], 0
    for k, repo in enumerate(repos):
        fetched = crp.fetch(repo, include_skipped=a.all)
        if k or paused or search or skipped:
            print()
        try:
            plan = None if fetched["error"] else cb.plan(c.store, c.copies, repo, fetched, now(), all_=a.all)
        except cb.SourceLost as e:                      # a file that holds none of your based blocks: unavailable, not N "−"
            fetched = dict(fetched, error=str(e))
        if fetched["error"]:
            down += 1
            why = cb.clip(fetched["error"], cb.NOTE_CLIP)
            print("%s · недоступний: %s" % (cb.clip(repo["id"], cb.HEADER_CLIP), why))
            plans.append({"repo": repo["id"], "error": why})
            continue
        print(cb.render_plan(plan))
        plan["namespace_warning"] = crp.namespace_warning(repo, fetched["namespace"])
        if plan["namespace_warning"]:
            print("warning: %s" % plan["namespace_warning"])
        plans.append(plan)
    rc = 5 if down else 0
    if a.repo:
        return rc, dict(plans[0], command="provider", action="plan")
    return rc, {"command": "provider", "action": "plan", "repos": plans, "paused": paused, "search_only": search,
                "questions": sum(p.get("questions", 0) for p in plans), "changes": sum(p.get("changes", 0) for p in plans),
                "unreadable": [{"file": p, "reason": w} for p, w in skipped]}


def _choices(items):
    """--choose BLOCK=theirs|mine|both … → {block: answer}; anything else is a usage error."""
    out = {}
    for it in items or []:
        bid, eq, how = it.partition("=")
        if not eq or not bid or how not in cb.CHOICES:
            raise Usage("--choose takes BLOCK=theirs|mine|both, not %r" % it)
        out[bid] = how
    return out


def _applied(res):
    """The data of one apply: the plan's (rows, versions …) and what the pass did."""
    out = dict(res["plan"])
    out.update((k, v) for k, v in res.items() if k != "plan")
    return out


def cmd_provider_apply(a, c):
    """One pass per repository: every repository is read first, and one that cannot be read stops the run before
    the lock (exit 5, nothing written); so does an answer that names no block of the plan (since v3.14: a plan of the
    same fetch, made before the lock — exit 3, nothing imported) and, without REPO, an answer that names a registered
    repository, in --product's scope or not (exit 3); then, under the lock, the edits waiting are imported and each
    repository is applied (its own snapshot, journal line and compile), holding the blocks that offer a text you
    rejected unless this run takes it (`cb.held_rejected`). Exit 2 when an answer is still awaited (the rest applied),
    4 when a block was refused (a broken marker) and nothing else changed, else 0."""
    if a.repo and "=" in a.repo:
        raise Usage("%r looks like an answer, not a repository — put the repository first: "
                    "ctx provider apply <repo> --choose BLOCK=… [BLOCK=…]" % a.repo)
    choose, add = _choices(a.choose), list(a.add or [])
    c.need_store()
    skipped, registered = [], set()
    repos, paused, search = _in_scope(c, a, skipped, registered)
    if not a.repo:                                      # `--add okr zorg-core`: the repository read as one more block —
        for flag, words in (("--add BLOCK [BLOCK …]", add), ("--choose BLOCK=…", list(choose))):   # any registered one
            named = next((w for w in words if w in registered), None)
            if named is not None:
                raise Usage("%r is a repository, not a block — put the repository first: ctx provider apply <repo> %s"
                            % (named, flag))
    if (choose or add) and len(repos) > 1:
        raise Usage("--choose and --add answer one repository's plan — name it: ctx provider apply <repo> …")
    fetched = [(repo, crp.fetch(repo)) for repo in repos]
    down = []
    for repo, f in fetched:                             # unreachable, or a file that holds none of your based blocks
        why = f["error"] or cb.source_lost(c.store, c.copies, repo, f, now())
        if why:
            down.append({"repo": repo["id"], "error": cb.clip(why, cb.NOTE_CLIP)})
    if down:
        for x in down:
            print("%s · недоступний: %s" % (cb.clip(x["repo"], cb.HEADER_CLIP), x["error"]))
        print("нічого не записано")
        res = {"command": "provider", "action": "apply", "unreachable": down, "paused": paused, "search_only": search, "written": [],
               "unreadable": [{"file": p, "reason": w} for p, w in skipped]}
        if a.repo:
            res.update(repo=a.repo, error=down[0]["error"])
        return 5, res
    if choose or add:                                   # a block the plan does not have: refused here, before the lock and
        for repo, f in fetched:                         # the import (`cb.plan` reads only; `apply` asks the same again)
            unknown = cb.unknown_blocks(cb.plan(c.store, c.copies, repo, f, now()), choose, add)
            if unknown:
                raise Usage(cb.no_block(unknown, repo["id"]))
    results, card_note = [], None
    if fetched:
        with co.lock(c.home):
            c.guard()
            c.import_first()
            for repo, f in fetched:
                at = now()
                hold = cb.held_rejected(cb.plan(c.store, c.copies, repo, f, at), choose, add)   # spec v3.14 §5.4: not again
                results.append(cb.apply(c.store, c.copies, c.home, repo, f, choose, add, at, hold=hold))
            card_note = _refresh_card(c)
    for k, res in enumerate(results):
        if k or paused or search or skipped:
            print()
        print(cb.render_apply(res))
    if card_note:
        print(card_note)
    if any(r["pending"] for r in results):
        rc = 2
    elif any(r["errors"] for r in results) and not any(r["changed"] for r in results):
        rc = 4
    else:
        rc = 0
    data = [_applied(r) for r in results]
    if a.repo:
        return rc, dict(data[0], command="provider", action="apply")
    return rc, {"command": "provider", "action": "apply", "repos": data, "paused": paused, "search_only": search,
                "questions": sum(len(r["pending"]) for r in results), "changes": sum(len(r["written"]) for r in results),
                "unreadable": [{"file": p, "reason": w} for p, w in skipped]}


def _sync_now(text):
    """--now as ISO text with its offset (local time when it names none), seconds only; the present moment without it."""
    if text is None:
        return now()
    t = sy.instant(text)
    if t is None:
        raise Usage("--now takes an ISO time, such as 2026-10-16T09:00:00+03:00, not %r" % text)
    return t.isoformat(timespec="seconds")


def cmd_provider_sync(a, c):
    """The daily sync (ctx_synced): the repositories with `sync: daily` — REPO names one of them — not paused, not
    search-only; with --if-due only those due, read from their block state without the lock or the network (none →
    nothing printed, only CTX_RESULT). Then `sy.run` within BUDGET_S — with --if-due it checks again under the lock — and
    one sentence per repository whose pass changed a block or decided a conflict. A run that did nothing because of the
    lock or the guard says so in CTX_RESULT: skipped "busy" | "lock: <why>" | "guard: <why>". Exit 0 whatever the repositories did; a
    usage error (an unknown REPO, one without `sync: daily`, a paused one, a bad --now) is exit 3."""
    deadline = time.monotonic() + sy.BUDGET_S          # the whole run, the registrations' read included (as in v3.23)
    loaded = None if a.repo else crp.load_repos(c.text, c.home, deadline=deadline)   # read once: blocks and copies
    rc, out = _provider_sync_blocks(a, c, loaded, deadline)
    try:                                                # since v3.24.0: the copies, after the blocks (C7)
        rows = loaded if loaded is not None else [r for r in crp.load_repos(c.text, c.home) if r["id"] == a.repo]
        copies = start_copies(c, rows, _sync_now(a.now), c.home, c.found)
    except Exception:  # noqa: BLE001 — a copy never changes the sync's own result
        copies = {}
    if copies:
        out = dict(out, copy=copies)
    return rc, out


def _provider_sync_blocks(a, c, loaded=None, deadline=None):
    deadline = time.monotonic() + sy.BUDGET_S if deadline is None else deadline
    at = _sync_now(a.now)
    quiet = {"command": "provider", "action": "sync", "synced": []}
    if a.repo:
        repo = _repository(c, a.repo)
        rid = cb.clip(repo["id"], cb.HEADER_CLIP)
        if repo["sync"] != crp.SYNC_DAILY:
            raise Usage("%s has no `sync: daily` in its registration — the daily sync touches only the repositories it was "
                        "switched on for (context-connect asks); `ctx provider apply %s` updates it with your answers" % (rid, rid))
        if repo["status"] == "paused":
            raise Usage("%s is paused (status: paused) — the daily sync leaves it alone" % rid)
        repos = [repo]
    else:
        repos = [r for r in (loaded if loaded is not None else crp.load_repos(c.text, c.home))
                 if r["sync"] == crp.SYNC_DAILY and r["status"] != "paused" and not crp.search_only(r)]
    if not c.store.exists():
        if not a.if_due:
            print("nothing to sync — no context store")
        return 0, quiet
    if a.if_due:
        repos = sy.pick_due(c.store, repos, at)
    elif not repos:
        print("nothing to sync — no repository has `sync: daily` in its registration (context-connect turns it on)")
    if not repos:
        return 0, quiet
    skipped = []
    results = sy.run(c, repos, at, deadline, only_due=a.if_due, skipped=skipped)
    for r in results:
        if sy.news(r):
            print(sy.sentence(r))
    out = dict(quiet, synced=[r["repo"] for r in results], results=[sy.public(r) for r in results])
    if skipped:
        out["skipped"] = skipped[0]
    return 0, out


def _no_slot(slot, cat=None):
    """The usage line for a slot the records do not know: a slot of an entity's cards (v3.19.0, plan C1a) says who
    decides it, anything else is not in the catalogue."""
    try:
        card = sl.card_slot_info(cat if cat is not None else sl.load_catalogue(), slot)
    except ValueError:
        card = None
    if card:
        return ("%s is a slot of an entity's cards: the cascade of the cards decides it, not a record's binding or "
                "preference — see it with: ctx entity \"<who>\" --slot %s" % (slot, slot))
    return "no slot %r in the catalogue (references/context-slots.yaml)" % slot


def _slot_request(a, cat):
    """What the arguments of a `ctx slot` command ask for, checked as far as they can be without the store: the slot is
    in the catalogue (`forget` also takes one only the memory still knows — checked under the lock), a block id is an id,
    a subsection or a heading is not empty, a preference is mine, all or repo:<id>. Anything else is a usage error."""
    req = {"slot": a.slot, "info": sl.slot_info(cat, a.slot)}
    if req["info"] is None and a.action != "forget":
        raise Usage(_no_slot(a.slot, cat))
    if a.action == "bind":
        block, hash_, sub = a.target.partition("#")
        block = block.strip()
        if not re.fullmatch(cb.ID, block):
            raise Usage("%r is not a block id (letters, digits, '_', '.' and '-'); a subsection follows a '#': block#Subsection"
                        % block)
        if hash_ and not sub.strip():
            raise Usage("nothing follows the '#' in %r — the subsection's heading, or no '#' for the whole block" % a.target)
        req["block"], req["sub"] = block, (sub.strip() if hash_ else None)
        if a.team and not a.slot.startswith("team."):
            raise Usage("--team is for the team.* slots; %s is not one" % a.slot)
    elif a.action == "map":
        req["heading"] = a.heading.strip()
        if not req["heading"]:
            raise Usage("the heading of your subsection is empty")
    elif a.action == "prefer":
        req["who"] = a.who.strip()
        if not sl.valid_preference(req["who"]):
            raise Usage("prefer takes mine, all or repo:<id>, not %r" % a.who)
    return req


def _slot_decide(c, a, info, mem, day):
    """`slot decide`: the answer to a divergence between repositories, put into `mem` (in place). The slot is computed on the
    records as they are now (ctx_resolve.slot_context / slot_answers — what `ctx read` would give): the first place (product
    or team) where repositories tie at the highest rank with different text has the sides; `a.repo` must be one of them. What
    is kept is the winner, the hash of each side's compared text (ctx_resolve.divergence_hashes) and the day — a new text from
    any side is a new hash, and the question comes back. Returns the line that says what was decided."""
    skipped = []
    repos = crp.load_repos(c.text, c.home, skipped=skipped)
    if skipped:
        raise Usage("a registration could not be read: %s — the ranks of its blocks are not known; try again when it has "
                    "downloaded" % _unread(skipped))
    sctx = rv.slot_context(c.store, c.copies, repos, a.product, now(), mem=mem)
    if sctx["needs_product"] and info["record"] in ("product", "team"):
        names = ", ".join(sctx["products"])
        raise Usage("%s matches no single product (products: %s)" % (a.product, names) if a.product else
                    "several products (%s) — name the one whose slot it is: --product \"<name>\"" % names)
    sides = [x for x in rv.slot_answers(sctx, a.slot) if x["result"]["diverges"]]
    if not sides:
        raise Usage("no divergence for %s" % a.slot)
    first = sides[0]["result"]
    if a.repo not in first["diverges"]:
        raise Usage("%s is not one of the repositories whose texts differ for %s: %s"
                    % (a.repo, a.slot, ", ".join(first["diverges"])))
    mem["decisions"][a.slot] = {"winner": a.repo, "hashes": rv.divergence_hashes(info["kind"], first["shown"]), "at": day}
    return "%s → %s" % (a.slot, a.repo)


def cmd_slot(a, c):
    """What you decided about slots (bind, map, prefer, decide, forget): `.state/slots.json`. A writing command — the lock,
    the guard, the memory read (one that cannot be read stops the run before anything is imported), the edits waiting
    imported, a snapshot, the memory written, one journal line. No record changes, so nothing is compiled. A command that
    changes nothing writes nothing and takes no snapshot."""
    req = _slot_request(a, sl.load_catalogue())
    slot, info = req["slot"], req["info"]
    c.need_store()
    repo = None
    if a.action == "bind":
        repo = _repository(c, a.repo)["id"]
    elif a.action == "prefer" and req["who"].startswith("repo:"):
        skipped = []
        if req["who"][5:] not in [r["id"] for r in crp.load_repos(c.text, c.home, skipped=skipped)]:
            raise Usage(_not_registered(req["who"][5:], skipped))
    with co.lock(c.home):
        c.guard()
        mem = sl.load_memory(c.store)
        pre = c.import_first()
        if a.action == "bind":
            if a.team:
                team = _record(c, a.team)
                if team["type"] != "team":
                    raise Usage("--team takes the id of a team record, not %s (%s)" % (team["type"], a.team))
            changed = sl.add_binding(mem, repo, req["block"], req["sub"], slot, a.team or None)
            what = "%s %s%s → %s" % (repo, req["block"], "#" + req["sub"] if req["sub"] else "", slot)
        elif a.action == "map":
            rec = _record(c, a.record)
            if rec["type"] != info["record"]:
                raise Usage("%s is a %s record; %s is looked for in a %s record" % (a.record, rec["type"], slot, info["record"]))
            changed = sl.add_alias(mem, a.record, req["heading"], slot)
            what = "%s “%s” → %s" % (a.record, req["heading"], slot)
        elif a.action == "prefer":
            changed = sl.set_prefer(mem, slot, req["who"])
            what = "%s → %s" % (slot, req["who"])
        elif a.action == "decide":
            what = _slot_decide(c, a, info, mem, now()[:10])
            changed = True
        else:
            if info is None and not sl.in_memory(mem, slot):
                raise Usage(_no_slot(slot))
            changed = sl.drop_slot(mem, slot)
            what = slot
        out = {"command": "slot", "action": a.action, "slot": slot, "changed": changed, "snapshot": None, "memory": mem,
               "imported": pre["changed"] + pre["added"]}
        if not changed:
            print("unchanged — slot %s: %s" % (a.action, what) if a.action != "forget" else
                  "unchanged — the memory holds nothing about %s" % slot)
            return 0, out
        t = now()
        snap = co.snapshot(c.store, c.copies, c.home, "slot")
        out["memory"] = sl.save_memory(c.store, mem)
        out["snapshot"] = snap
        c.store.journal({"ts": t, "op": "slot", "action": a.action, "slot": slot, "ids": [], "source": "ctx-slot",
                         "snapshot": snap})
    print("slot %s: %s · snapshot %s (back: ctx undo)" % (a.action, what, snap))
    return 0, out


# ------------------------------------------------------------------ `ctx overlay` (since v3.23.0)
NO_OVERLAY = "оверлею немає — поправку до ядра додає ctx overlay add <repo> --block <id> --op <op> --reason <чому>"


def _overlay_repos(c, a):
    """The repositories `ctx overlay` speaks of: the one named (registered, else exit 3), else every registered one
    that has an overlay file."""
    if a.repo:
        return [_repository(c, a.repo)]
    skipped = []
    repos = crp.load_repos(c.text, c.home, skipped=skipped)
    for path, why in skipped:
        print("unreadable registration: %s (%s)" % (path, why))
    return [r for r in repos if ov.REPO_ID.match(str(r.get("id"))) and os.path.isfile(ov.path_of(c.store.root, r["id"]))]


def _overlay_doc(c, rid):
    """The overlay document of `rid` (an empty one when there is no file); a file that cannot be read → Usage (exit 3),
    the file untouched."""
    try:
        doc = ov.load(c.store.root, rid)
    except ov.Unreadable as e:
        raise Usage("оверлей не прочитано: %s — файл не змінено; виправ його або заміни: ctx overlay apply %s --file <чернетка>"
                    % (e, rid))
    return doc or {"schema": ov.SCHEMA, "repo": rid, "ops": []}


def _checked_doc(doc, rid):
    """The document as the file would hold it (parsed back from its canonical text): an operation that is not one → Usage."""
    try:
        return ov.parse(ov.dump(dict(doc, repo=rid)))
    except ov.Unreadable as e:
        raise Usage("операція не підходить: %s" % e)


def cmd_overlay(a, c):
    """Your declared corrections to a repository's blocks, `overlays/<repo>.yaml` (references/context-protocol.md §5n).
    `show` and `plan` read only; `plan` and `apply` take `--file` (a draft — the migration of a prose overlay note);
    `apply` needs the code its plan printed (another → exit 4, nothing written); `add`, `rm`, `answer` change the file and
    lay it over the regions in one run. Every write: the lock, the guard, the edits waiting imported, one snapshot, one
    journal line (`op: overlay`), `ctx undo` takes it back."""
    c.need_store()
    if a.action == "plan" and a.file and not a.repo:      # a draft names its repository
        try:
            a.repo = ov.parse(co._read(a.file))["repo"]
        except ov.Unreadable as e:
            raise Usage("чернетка %s: %s" % (a.file, e))
    if a.action in ("show", "plan"):
        repos = _overlay_repos(c, a)
        if not repos:
            print(NO_OVERLAY)
            return 0, {"command": "overlay", "action": a.action, "repos": []}
        out, rc = [], 0
        for k, repo in enumerate(repos):
            if k:
                print()
            if a.action == "plan" and a.file:
                try:
                    doc = ov.parse(co._read(a.file))
                except ov.Unreadable as e:
                    raise Usage("чернетка %s: %s" % (a.file, e))
                if doc["repo"] != repo["id"]:
                    raise Usage("чернетка %s — для %s, не для %s" % (a.file, doc["repo"], repo["id"]))
            else:
                try:
                    doc = ov.load(c.store.root, repo["id"])
                except ov.Unreadable as e:
                    print("оверлей не прочитано: %s" % cb.clip(e, cb.NOTE_CLIP))
                    out.append({"repo": repo["id"], "error": str(e)})
                    rc = 3
                    continue
                if doc is None:
                    print("%s · %s" % (cb.clip(repo["id"], cb.HEADER_CLIP), NO_OVERLAY))
                    out.append({"repo": repo["id"], "ops": []})
                    continue
            res = cb.reoverlay(c.store, c.copies, c.home, repo, now(), doc["ops"])
            print(cb.render_overlay(res, doc["ops"], show_diff=a.action == "plan"))
            kinds = cn.scan("\n".join(_overlay_texts(doc)))
            if kinds:
                print("увага: %s — apply цього не запише" % cn.message(kinds))
            out.append({"repo": repo["id"], "ops": doc["ops"], "rows": [dict((k2, v) for k2, v in r.items() if k2 not in ("before", "after"))
                                                                       for r in res["rows"]], "code": res["code"]})
        data = {"command": "overlay", "action": a.action, "repos": out}
        if a.repo and out:
            data.update(out[0])
        return rc, data
    repo = _repository(c, a.repo)
    rid = repo["id"]
    if a.action == "apply" and not a.code:
        raise Usage("apply needs the code its plan printed: ctx overlay plan %s%s" % (rid, " --file " + a.file if a.file else ""))
    t = now()
    with co.lock(c.home):
        c.guard()
        c.import_first()
        what = None
        if a.action == "apply":
            if a.file:
                try:
                    doc = ov.parse(co._read(a.file))
                except ov.Unreadable as e:
                    raise Usage("чернетка %s: %s" % (a.file, e))
                if doc["repo"] != rid:
                    raise Usage("чернетка %s — для %s, не для %s" % (a.file, doc["repo"], rid))
            else:
                doc = _overlay_doc(c, rid)
            shown = cb.reoverlay(c.store, c.copies, c.home, repo, t, doc["ops"])
            if shown["code"] != a.code:
                raise co.Refused("оверлей або записи змінились — переглянь ще раз: ctx overlay plan %s%s"
                                 % (rid, " --file " + a.file if a.file else ""))
        else:
            doc = _overlay_doc(c, rid)
            ops = [dict(o) for o in doc["ops"]]
            ids = [o["id"] for o in ops]
            if a.action == "add":
                if a.id and a.id in ids:
                    raise Usage("операція %s уже є — змінити її: ctx overlay answer %s %s …" % (a.id, rid, a.id))
                new = {"target": {"block": a.block, "path": a.path} if a.path else {"block": a.block}, "op": a.op,
                       "expects": 1 if a.expects is None else a.expects, "created": t[:10]}
                if a.id:
                    new["id"] = a.id
                if a.value:
                    new["value"] = a.value if (len(a.value) > 1 or a.op == "alias") else a.value[0]
                if a.value_ref:
                    new["value_ref"] = a.value_ref
                if a.reason:
                    new["reason"] = a.reason
                raw = {"schema": ov.SCHEMA, "repo": rid, "ops": [dict(o) for o in ops]}
                text = ov.dump(raw).rstrip("\n")
                try:                                    # the new operation as the file would hold it: parse the whole
                    doc = ov.parse(_with_op(text, new))
                except ov.Unreadable as e:
                    raise Usage("операція не підходить: %s" % e)
                what = doc["ops"][-1]["id"]
            else:
                if a.op_id not in ids:
                    raise Usage("операції %s немає в оверлеї %s (є: %s)" % (a.op_id, rid, ", ".join(ids) or "—"))
                at = ids.index(a.op_id)
                what = a.op_id
                if a.action == "rm" or a.how == "drop":
                    ops.pop(at)
                elif a.how == "retarget":
                    if not a.path:
                        raise Usage("retarget needs --path")
                    ops[at] = dict(ops[at], target={"block": ops[at]["target"]["block"], "path": a.path})
                else:
                    if a.expects is None:
                        raise Usage("expects needs --expects N")
                    if ops[at]["expects"] == a.expects:
                        print("unchanged — %s already expects %d" % (a.op_id, a.expects))
                        return 0, {"command": "overlay", "action": a.action, "repo": rid, "changed": False}
                    ops[at] = dict(ops[at], expects=a.expects)
                doc = _checked_doc(dict(doc, ops=ops), rid)
        cn.check(*_overlay_texts(doc))                  # a draft or a hand-edited file: no secret goes into the store
        res = cb.reoverlay(c.store, c.copies, c.home, repo, t, doc["ops"], doc=doc, apply=True, action=a.action, what=what)
    print(cb.render_overlay(res, doc["ops"], show_diff=True))
    if res["changed"]:
        print("записано: %s · знімок %s (назад: ctx undo)" % (", ".join(res["written"]) or "лише оверлей", res["snapshot"]))
    else:
        print("без змін")
    out = {"command": "overlay", "action": a.action, "repo": rid, "changed": res["changed"], "written": res["written"],
           "snapshot": res["snapshot"], "code": res["code"]}
    if a.action == "add":
        out.update(created=t[:10], id=what)
    return 0, out


def _overlay_texts(doc):
    """Every free text of an overlay document — what the never-store filter reads before it is written."""
    return ov.texts_of(doc)


def _with_op(text, op):
    """The canonical text of a document plus one operation in the file's own syntax (its id may be absent: parse makes it)."""
    q = lambda s: json.dumps(str(s), ensure_ascii=False)
    tgt = op["target"]
    head = text[:-len("ops: []")] + "ops:" if text.endswith("ops: []") else text    # only the empty list of an empty file
    lines = [head, "  - target: {block: %s%s}" % (q(tgt["block"]), (", path: %s" % q(tgt["path"])) if tgt.get("path") else ""),
             "    op: %s" % q(op["op"])]
    if op.get("id"):
        lines.append("    id: %s" % q(op["id"]))
    if "value" in op:
        v = op["value"]
        lines.append("    value: %s" % ("[%s]" % ", ".join(q(x) for x in v) if isinstance(v, list) else q(v)))
    if "value_ref" in op:
        lines.append("    value_ref: %s" % q(op["value_ref"]))
    lines.append("    expects: %d" % op["expects"])
    for k in ("reason", "created"):
        if op.get(k):
            lines.append("    %s: %s" % (k, q(op[k])))
    return "\n".join(lines) + "\n"


def _identity_mine(c, repo):
    """{team: (value, source), role: (value, source)} — your role in the profile with its source, the team your
    registration names."""
    prof = next((r for r in c.store.load() if r["type"] == "profile"), None)
    role = cs.field_get(prof["body"], "Role") if prof else None
    src = None
    if prof and role:
        try:
            x = next((x for x in csrc.of(csrc.load(c.store), prof) if x["label"].casefold() == "role"), None)
        except cs.StoreError:
            x = None
        src = csrc.describe(x) if x else None
    team = repo.get("team") or None
    reg = repo.get("_file") or repo.get("file") or "%s.yaml" % repo["id"]
    return {"role": (role or None, src), "team": (team, "реєстрація %s" % os.path.basename(str(reg)) if team else None)}, prof


def cmd_identity(a, c):
    """`identity check|keep|take REPO [FIELD] --bundle F` (context-protocol.md §5r): the core's team and role for your
    e-mail beside yours, both with their source; `keep` / `take` answer — a writing command (lock, snapshot, one journal
    line `op: identity`); `take role` also writes the core's role into your profile (source repo:<id>)."""
    c.need_store()
    repo = _repository(c, a.repo)
    try:
        bundle = cid.read_bundle(a.bundle)
    except ValueError as e:
        raise Usage(str(e))
    if a.action == "check":
        mem = cid.load(c.store)
        mine, _ = _identity_mine(c, repo)
        rows = cid.compare(bundle, mine, mem, repo["id"])
        print(cid.render(rows, repo["id"], a.bundle))
        return 0, {"command": "identity", "action": "check", "repo": repo["id"], "rows": rows,
                   "questions": sum(1 for r in rows if r["state"] == "ask")}
    if a.field not in cid.FIELDS:
        raise Usage("the field is team or role")
    if a.action == "take" and a.field == "team":
        raise Usage("команду змінює context-connect: перезбери пакет з --team %s (connect-steps.md §3) — тут лише keep" % bundle["team"])
    t = now()
    with co.lock(c.home):
        c.guard()
        mem = cid.load(c.store)                         # one that cannot be read stops here, before anything is written
        c.import_first()
        mine, prof = _identity_mine(c, repo)
        mval = mine[a.field][0]
        snap = co.snapshot(c.store, c.copies, c.home, "identity")
        ids = []
        if a.action == "take":
            if prof is None:
                raise Usage("no profile record to write the role into")
            value = bundle.get("role_enum") or bundle["role"]          # the plugin's value, not the role model's id
            spec = _field_spec(prof, "Role")
            err = sc.check_value(spec, value) if spec else None
            if err:
                raise Usage("Role: %s — the core's role %s is no value of the profile; set it yourself: ctx set %s Role <value>"
                            % (err, bundle["role"], prof["id"]))
            srcs = csrc.load(c.store)
            csrc.adopt(srcs, prof)
            csrc.note(srcs, prof["id"], csrc.field_key("Role"), value, "repo:%s" % repo["id"], at=t)
            csrc.save(c.store, srcs)
            c.store.write(co.touch(dict(prof, body=cs.field_set(prof["body"], "Role", value), source="repo:%s" % repo["id"],
                                        modified=t), t))
            ids = [prof["id"]]
        cid.answer(mem, repo["id"], a.field, "mine" if a.action == "keep" else "core", bundle[a.field], mval, t[:10])
        cid.save(c.store, mem)
        c.store.journal({"ts": t, "op": "identity", "action": a.action, "repo": repo["id"], "what": a.field, "ids": ids,
                         "source": "ctx-identity", "snapshot": snap})
        if ids:
            co.compile_store(c.store, c.copies, t, c.home, snap)
    print("identity %s: %s %s — ядро %s, твоє %s · знімок %s (назад: ctx undo)" % (a.action, repo["id"], a.field, bundle[a.field],
                                                                                  mval, snap))
    return 0, {"command": "identity", "action": a.action, "repo": repo["id"], "field": a.field, "snapshot": snap}


def cmd_history(a, c):
    """`history [--month YYYY-MM] [--write] [--json]`: the human changelog of the store (references/context-protocol.md
    §5p) — printed, or with --write written to `history/YYYY-MM.md` only when its text changed. No lock, no journal line:
    the note is derived from the journal and the base texts."""
    c.need_store()
    month = a.month or now()[:7]
    if not chi.MONTH.match(month):
        raise Usage("--month takes YYYY-MM, not %r" % month)
    text = chi.build(c.store, month)
    if a.write:
        path, changed = chi.write(c.store, month)
        print("%s: %s" % ("записано" if changed else "без змін", path))
        return 0, {"command": "history", "month": month, "path": path, "changed": changed}
    print(text)
    return 0, {"command": "history", "month": month, "text": text if a.json else None}


def cmd_provider(a, c):
    if a.action == "adopt":
        return cmd_provider_adopt(a, c)
    if a.action == "plan":
        return cmd_provider_plan(a, c)
    if a.action == "apply":
        return cmd_provider_apply(a, c)
    if a.action == "sync":
        return cmd_provider_sync(a, c)
    raise Usage("provider takes adopt, plan, apply or sync")


# ---------------------------------------------------------------------- the inbox (since v3.21.0)
NO_STORE_INBOX = "немає сховища — скринька живе у сховищі; скіл питає «Зберегти?», як у Context Enrichment"


def _deltas(a):
    """The deltas of `propose`: each --delta (an object or a list), then --file's (the same)."""
    out = []
    for raw in list(a.delta or []) + ([co._read(a.file)] if a.file else []):
        try:
            v = json.loads(raw)
        except ValueError as e:
            raise Usage("a delta is JSON: %s" % e)
        out.extend(v if isinstance(v, list) else [v])
    if not out:
        raise Usage("propose takes --delta JSON or --file F")
    return out


def _inbox_line(mem, recs):
    n = ci_.counts(mem, now()[:10])
    return "у скриньці %d%s — /context inbox" % (n["entries"], (" (термінових %d)" % n["urgent"]) if n["urgent"] else "")


def cmd_propose(a, c):
    """`propose --skill S (--delta JSON | --file F)`: the deltas into the inbox (`.state/inbox.json`). The lock, the
    guard, the inbox read (one that cannot be read stops the run before anything is imported), the edits waiting
    imported, the inbox written, one journal line {op propose, skill, sigs} — no snapshot (plan C4: a skill's every run
    would rotate real ones out); `ctx inbox reject` takes a proposal back, and `ctx undo` of any change keeps the
    entries proposed after it. Exit 4 when a delta held what the store never keeps, 3 when one was malformed or named
    no record — the others are kept either way. No store: exit 3."""
    raws = _deltas(a)
    try:
        a.skill = ci_.skill_name(a.skill)
    except ValueError as e:
        raise Usage(str(e))
    if a.skill in ci_.CTX_OWN:                         # since v3.22.0: ctx's own proposers come only from its commands
        raise Usage("%s — джерело самого ctx (bootstrap, validate --recheck, consolidate, provider apply), не скіл" % a.skill)
    if a.skill not in (cr.load_manifest().get("skills") or {}):     # a name the plugin does not know is no skill's
        raise Usage("--skill names one of the plugin's skills (references/context-manifest.yaml), not %s"
                    % ("that" if cn.scan(a.skill) else a.skill))
    out = {"command": "propose", "skill": a.skill, "results": [], "added": [], "urgent": [], "code": None}
    if not c.store.exists():
        print(NO_STORE_INBOX)
        return 3, dict(out, error=NO_STORE_INBOX)
    with co.lock(c.home):
        c.guard()
        mem = ci_.load(c.store)
        c.import_first()
        recs = c.store.load()
        today = now()[:10]
        res = ci_.propose(mem, raws, a.skill, recs, today)
        new = [r for r in res if r["status"] in (ci_.ADDED, ci_.MERGED)]
        if new:
            ci_.save(c.store, mem, today)
            c.store.journal({"ts": now(), "op": "propose", "skill": a.skill, "ids": sorted({r["record"] for r in new}),
                             "sigs": [e["sig"] for e in mem["entries"] if e["n"] in {r["n"] for r in new}],
                             "source": "ctx-propose"})
        out.update(results=res, added=[r["n"] for r in res if r["status"] == ci_.ADDED],
                   urgent=sorted({r["n"] for r in new if r.get("urgent")}), code=ci_.code(mem, recs),
                   noop=sum(1 for r in res if r["status"] == ci_.NOOP), inbox=ci_.counts(mem, today))
    for i, r in enumerate(res, 1):
        if r["status"] in (ci_.REFUSED, ci_.SECRET, ci_.BLOCK):
            print("дельта %d: %s" % (i, r["why"]))
    added = len(out["added"])
    if new:
        print("у скриньці +%d (усього %d)%s — /context inbox" % (
            added, out["inbox"]["entries"], (" · термінові №%s — запитай зараз, код %s" % (
                ", ".join(map(str, out["urgent"])), out["code"])) if out["urgent"] else ""))
    else:
        print("нічого нового для скриньки")
    rc = 4 if any(r["status"] in (ci_.SECRET, ci_.BLOCK) for r in res) else \
        3 if any(r["status"] == ci_.REFUSED for r in res) else 0
    return rc, out


def _inbox_code(c, mem, recs, given):
    if not given:
        raise Usage("accept і reject беруть --code з ctx inbox list")
    if given != ci_.code(mem, recs):
        raise co.Refused("скринька змінилась — переглянь ще раз: ctx inbox list")


def _note_delta(srcs, e):
    d, s = e["delta"], e["delta"]["source"]
    at = s.get("at") or now()
    if d["op"] == "UPDATE":
        csrc.note(srcs, d["record"], csrc.field_key(d["field"]), d["value"], s["kind"], ref=s.get("ref"), at=at)
    elif d["op"] in ("ADD", "REPLACE"):                 # the line it adds (a field's line as that field)
        csrc.note_text(srcs, d["record"], d["text"] if d["op"] == "ADD" else d["value"], s["kind"], ref=s.get("ref"),
                       at=at)


def cmd_inbox(a, c):
    out = {"command": "inbox", "action": a.action}
    if not c.store.exists():
        print(NO_STORE_INBOX)
        return 3, dict(out, error=NO_STORE_INBOX)
    today = now()[:10]
    if a.action == "list":
        mem, recs = ci_.load(c.store), c.store.load()
        lines = ci_.render(mem, recs, today)
        for l in lines:
            print(l)
        cd = ci_.code(mem, recs)
        print("скринька порожня" if not lines else "код: %s" % cd)
        return 0, dict(out, entries=[dict(e, moved=ci_.moved(e, recs)) for e in mem["entries"]],
                       clashes=sorted(ci_.clashes(mem)), code=cd, inbox=ci_.counts(mem, today))
    with co.lock(c.home):
        c.guard()
        mem = ci_.load(c.store)
        srcs = csrc.load(c.store) if a.action == "accept" else None
        recs = c.store.load()
        _inbox_code(c, mem, recs, a.code)        # what was shown, before anything is imported
        try:
            chosen = ci_.pick(mem, a.which)
        except ValueError as e:
            raise Usage(str(e))
        c.import_first()
        if srcs is not None:                            # the import notes its own fields: read them after it
            srcs = csrc.load(c.store)
        recs = c.store.load()
        if a.action == "reject":
            snap = co.snapshot(c.store, c.copies, c.home, "inbox-reject")
            ci_.reject(mem, chosen, today, a.reason or "")
            ci_.save(c.store, mem, today)
            c.store.journal({"ts": now(), "op": "inbox-reject", "ids": [], "sigs": [e["sig"] for e in chosen],
                             "source": "ctx-inbox", "reason": a.reason or "", "snapshot": snap})
            print("відхилено: №%s · %s (back: ctx undo)" % (", ".join(str(e["n"]) for e in chosen), _inbox_line(mem, recs)))
            return 0, dict(out, rejected=[e["n"] for e in chosen], snapshot=snap, inbox=ci_.counts(mem, today))
        by_id = {r["id"]: r for r in recs}
        plan, done, held, gone = {}, [], [], []
        pairs = {}
        for e in chosen:
            if e["delta"]["op"] == "UPDATE":
                pairs.setdefault((e["delta"]["record"], e["delta"]["field"]), []).append(e)
        twice = {e["n"] for group in pairs.values() if len({x["delta"]["value"] for x in group}) > 1 for e in group}
        for e in chosen:
            d = e["delta"]
            if e["n"] in twice:
                held.append((e, "два значення для одного поля — прийми одне номером"))
                continue
            try:
                cn.check(*ci_.texts(d))
            except cn.NeverStore as err:
                held.append((e, str(err)))
                continue
            rec = plan.get(d["record"]) or by_id.get(d["record"])
            if rec is None:
                gone.append((e, "запис зник"))
                continue
            if d["op"] == "UPDATE":
                now_v = cs.field_get(rec["body"], d["field"])
                if now_v not in (e["was"], d["value"]):
                    held.append((e, "поле змінилось: було «%s», тепер «%s»" % (e["was"] or "—", now_v or "—")))
                    continue
            try:
                body = ci_.apply_to(d, rec, today)
            except (cs.RegionError, ValueError) as err:
                held.append((e, str(err) if isinstance(err, ValueError) else "це блок ядра"))
                continue
            if body != rec["body"]:
                plan[d["record"]] = dict(rec, body=body, source="inbox:%s" % e["skills"][0], modified=now())
            done.append(e)
        snap, written = None, []
        if done or gone:
            snap = co.snapshot(c.store, c.copies, c.home, "inbox-accept")
            t = now()
            for rid in plan:                            # since v3.22.0: each field or line, where it came from
                csrc.adopt(srcs, by_id[rid])
            for e in done:
                _note_delta(srcs, e)
            csrc.save(c.store, srcs)
            for rec in plan.values():
                c.store.write(co.touch(rec, t))
            c.store.journal({"ts": t, "op": "inbox-accept", "ids": sorted(plan), "sigs": [e["sig"] for e in done],
                             "source": "ctx-inbox", "reason": "", "snapshot": snap})     # right after the records: undo finds it
            ci_.take(mem, done + [e for e, _ in gone])  # a record gone is no rejection: after a restore it may come back
            ci_.save(c.store, mem, today)
            if plan:
                written = co.compile_store(c.store, c.copies, t, c.home, snap)["written"]
    for e, why in held + gone:
        print("№%d не прийнято: %s" % (e["n"], why))
    print("прийнято: %s · %s%s" % (", ".join("№%d" % e["n"] for e in done) or "нічого", _inbox_line(mem, recs),
                                   " (back: ctx undo)" if snap else ""))
    return 0, dict(out, accepted=[e["n"] for e in done], held=[e["n"] for e, _ in held],
                   gone=[e["n"] for e, _ in gone], ids=sorted(plan), snapshot=snap, written=written,
                   inbox=ci_.counts(mem, today))


# ------------------------------------------------------------------ bootstrap (since v3.22.0)
def _bootstrap_recs(c):
    """The records the table is compared with: the store's, or — no store — the file's sections, or nothing."""
    if c.store.exists():
        return c.store.load()
    if c.fresh:
        return []
    return [dict(r, body=r["text"], source="local-context") for r in cs.assign_ids(cs.split_sections(c.text))]


def _bootstrap_result(d, obs, cd):
    return {"rows": d["rows"], "inbox": len(d["inbox"]), "later": len(d["later"]), "same": d["same"],
            "dropped": obs["dropped"],
            "connectors": obs["connectors"], "code": cd, "default": [r["n"] for r in d["rows"] if r["default"]]}


def cmd_bootstrap(a, c):
    """`bootstrap --observed F [--json]` — the table: what the connectors say against your context (plan C5); reads
    only. `--apply --code C [--take N,…] [--skip N,…] | [--only N,…]` — writes the rows taken (C6). Every check comes
    first, under the lock, before anything is written: the code against the records as they are (and again after the
    edits waiting are imported), the rows, the inbox and the sources readable. With a store: a snapshot, the records,
    `.state/sources.json`, the low facts as inbox deltas (ctx-bootstrap), one journal line {op bootstrap, sigs}, the
    compile — `ctx undo` takes it all back. Nothing taken and nothing new for the inbox → nothing written; only new
    proposals → one {op propose} line, as `ctx propose` writes. Without a store and without local-context.md (a new
    user): the file from the skeleton, moved into records at once. A local-context.md not in records yet, or a store
    with no local-context.md: the table, never the apply."""
    try:
        obs = cob.load(a.observed)
    except ValueError as e:
        raise Usage(str(e))
    today = now()[:10]
    at = obs["at"] or today
    srcs = csrc.load(c.store) if c.store.exists() else csrc.empty()
    recs = _bootstrap_recs(c)
    d = cbt.diff(obs, recs, srcs)
    cd = cbt.code(d, recs)
    out = dict(_bootstrap_result(d, obs, cd), command="bootstrap", applied=False)
    if not a.apply:
        for line in cbt.render(d, obs["connectors"], obs["dropped"]):
            print(line)
        print("код: %s" % cd if d["rows"] or d["inbox"] or d["later"] else "нічого нового — контекст уже такий")
        if not c.store.exists() and not c.fresh:
            print("local-context.md ще не в записах — щоб записати таблицю, спершу ctx migrate --apply")
        return 0, out
    if not a.code:
        raise Usage("--apply бере --code з таблиці (ctx bootstrap --observed F)")
    try:
        cbt.chosen(d, a.take, a.skip, a.only)
    except ValueError as e:
        raise Usage(str(e))
    if c.fresh:
        held = [p for p in (c.store.records_dir, co._last_store_path(c.home)) if os.path.lexists(p)]
        if held:
            raise cs.StoreError("local-context.md немає, але сховище контексту є (%s) — це відновлення, не новий "
                                "користувач: «налаштуй плагін» (RM-1)" % held[0])
    elif not c.store.exists():
        raise cs.StoreError("local-context.md ще не в записах — спершу перенеси його (ctx migrate --apply, пункт "
                            "оновлення «Move my context to records»), тоді таблиця запишеться")
    t = now()
    with co.lock(c.home):
        c.guard()
        res = _bootstrap_new(c, a, obs, at, t) if c.fresh else _bootstrap_store(c, a, obs, at, t)
    added = [r for r in res["props"] if r["status"] == ci_.ADDED]
    print("записано: %s · у скриньці +%d%s" % (", ".join(res["ids"]) or "нічого", len(added),
                                              " (back: ctx undo)" if res["snapshot"] else ""))
    for n, why in res["not_written"]:
        print("№%d не записано: %s" % (n, why))
    if c.fresh:
        print("контекст у записах: %s — ctx undo повертає один файл" % c.store.root)
    return 0, dict(out, applied=True, taken=res["taken"], ids=res["ids"], snapshot=res["snapshot"],
                   written=res["written"], proposed=[r["n"] for r in added],
                   not_written=[n for n, _ in res["not_written"]])


def _note_row(srcs, rid, field, value, r, at):
    csrc.note(srcs, rid, csrc.field_key(field) if field else csrc.line_key(value), value, cbt.kind_of(r["from"]),
              ref=r.get("ref"), at=at, confidence=r["confidence"])


def _bootstrap_check(a, obs, recs, srcs, why):
    d = cbt.diff(obs, recs, srcs)
    if cbt.code(d, recs) != a.code:
        raise co.Refused("%s — переглянь ще раз: ctx bootstrap --observed %s" % (why, a.observed))
    try:
        return d, cbt.chosen(d, a.take, a.skip, a.only)
    except ValueError as e:
        raise Usage(str(e))


def _bootstrap_propose(c, box, facts, at, t):
    recs = c.store.load()
    props = ci_.propose(box, cbt.deltas(facts, recs, at), "ctx-bootstrap", recs, t[:10]) if facts else []
    added = {r["n"] for r in props if r["status"] == ci_.ADDED}
    return props, [e["sig"] for e in box["entries"] if e["n"] in added]


def _bootstrap_store(c, a, obs, at, t):
    box = ci_.load(c.store)                             # everything that must read, before anything is written
    srcs = csrc.load(c.store)
    _bootstrap_check(a, obs, c.store.load(), srcs, "таблиця змінилась")
    pre = c.import_first()
    recs = c.store.load()
    if pre["changed"] or pre["added"] or pre.get("removed"):
        srcs = csrc.load(c.store)
    d, take = _bootstrap_check(a, obs, recs, srcs, "правки з local-context.md змінили таблицю")
    res = {"ids": [], "snapshot": None, "written": [], "taken": [], "not_written": [], "props": []}
    if not take:
        res["props"], sigs = _bootstrap_propose(c, box, d["inbox"], at, t)
        if sigs:                                        # proposals only: a line as `ctx propose` writes
            ci_.save(c.store, box, t[:10])
            c.store.journal({"ts": t, "op": "propose", "skill": "ctx-bootstrap", "ids": sorted({
                r["record"] for r in res["props"] if r["status"] == ci_.ADDED}), "sigs": sigs, "source": "ctx-bootstrap"})
        return res
    by_id = {r["id"]: r for r in recs}
    snap = co.snapshot(c.store, c.copies, c.home, "bootstrap")
    changed = {}
    for r in take:
        if r["new"]:
            continue
        rec = changed.get(r["record"]) or by_id.get(r["record"])
        if rec is None:
            res["not_written"].append((r["n"], "запису %s немає" % (r["record"] or r["type"])))
            continue
        if r["record"] not in changed:
            csrc.adopt(srcs, rec)
        if r.get("field"):
            body = cbt.put_field(rec["body"], r["field"], r["value"])
            _note_row(srcs, rec["id"], r["field"], r["value"], r, at)
        else:
            body, line = cbt.add_line(rec["body"], r["list"], r["value"])
            _note_row(srcs, rec["id"], None, line, r, at)
        changed[rec["id"]] = dict(rec, body=body, source="ctx-bootstrap", modified=t)
        res["taken"].append(r["n"])
    news = sorted([r for r in take if r["new"]], key=lambda r: cbt.TYPE_ORDER[r["type"]])
    for rec in changed.values():
        c.store.write(co.touch(rec, t))
    ids = list(changed)
    for r in news:
        cur = c.store.load()
        if r["type"] == "org":
            after = cur[-1]["id"] if cur else None
        else:
            parent = [x["id"] for x in cur if x["type"] == "org"][0]   # chosen() made sure there is one
            kids = [x["id"] for x in cur if x["parent"] == parent and x["type"] == r["type"]] or \
                [x["id"] for x in cur if x["parent"] == parent] or [parent]
            after = kids[-1]
        text = cbt.new_body(r)
        rid = co._insert(c.store, [{"text": text, "type": r["type"], "title": "%s: %s" % (cbt.PREFIX[r["type"]],
                                                                                         r["title"]), "after": after}],
                         "ctx-bootstrap", t)[0]
        for f in r["fields"]:
            _note_row(srcs, rid, f["field"], f["value"], f, at)
        for x in r["lists"]:
            _note_row(srcs, rid, None, "- " + x["value"], x, at)
        ids.append(rid)
        res["taken"].append(r["n"])
    csrc.save(c.store, srcs)
    res["props"], sigs = _bootstrap_propose(c, box, d["inbox"] + d["later"], at, t)
    c.store.journal({"ts": t, "op": "bootstrap", "ids": ids, "rows": res["taken"], "source": "ctx-bootstrap",
                     "reason": "", "sigs": sigs, "snapshot": snap})     # the proposals ride it: undo takes them too
    if sigs:
        ci_.save(c.store, box, t[:10])
    res.update(ids=ids, snapshot=snap, written=co.compile_store(c.store, c.copies, t, c.home, snap)["written"])
    return res


def _bootstrap_new(c, a, obs, at, t):
    """A new user: the file from the skeleton, then the move into records — `ctx undo` after it is one file again."""
    d, take = _bootstrap_check(a, obs, [], csrc.empty(), "таблиця змінилась")
    try:
        text = cbt.skeleton(take, t[:10], t, cbt.plugin_version())
    except ValueError as e:
        raise Usage(str(e))
    cs.check_target(c.context)
    os.makedirs(os.path.dirname(c.context), exist_ok=True)
    cs.atomic_write(c.context, text)
    rep = co.migrate(c.context, c.store.root, c.copies, c.home, True, t)
    srcs = csrc.empty()
    recs = c.store.load()
    for r in take:
        if r["new"]:
            rec = cbt.find(recs, r["type"], r["title"], fallback=False)
            for f in r["fields"]:
                _note_row(srcs, rec["id"], f["field"], f["value"], f, at)
            for x in r["lists"]:
                _note_row(srcs, rec["id"], None, "- " + x["value"], x, at)
        elif r["type"] == "profile" and r.get("field"):
            _note_row(srcs, cbt.find(recs, "profile", None)["id"], r["field"], r["value"], r, at)
    for rec in recs:                                    # the skeleton's own lines (Judgment defaults, the onboarding
        for name, value in csrc.fields(rec["body"]):    # status): written by the configurator itself
            if csrc.field_key(name) not in srcs["records"].get(rec["id"], {}):
                csrc.note(srcs, rec["id"], csrc.field_key(name), value, "ctx-bootstrap", at=t)
    csrc.save(c.store, srcs)
    box = ci_.load(c.store)
    props, sigs = _bootstrap_propose(c, box, d["inbox"] + d["later"], at, t)
    c.store.journal({"ts": t, "op": "bootstrap", "ids": [r["id"] for r in recs], "rows": [r["n"] for r in take],
                     "source": "ctx-bootstrap", "reason": ""})
    if sigs:
        ci_.save(c.store, box, t[:10])
        c.store.journal({"ts": t, "op": "propose", "skill": "ctx-bootstrap", "ids": [], "sigs": sigs,
                         "source": "ctx-bootstrap"})
    return {"ids": [r["id"] for r in recs], "snapshot": rep.get("snapshot"), "written": [c.context],
            "taken": [r["n"] for r in take], "not_written": [], "props": props}


# ---------------------------------------------------------------------- main
def build_parser():
    common = Parser(add_help=False)
    common.add_argument("--context")
    common.add_argument("--store")
    common.add_argument("--home")
    p = Parser(prog="ctx", description="The Grow PM context store (references/context-protocol.md).")
    sub = p.add_subparsers(dest="cmd", required=True, parser_class=Parser)
    sub.add_parser("status", parents=[common])
    sp = sub.add_parser("migrate", parents=[common]); sp.add_argument("--apply", action="store_true")
    sub.add_parser("compile", parents=[common])
    sp = sub.add_parser("sync", parents=[common])
    sp.add_argument("--source"); sp.add_argument("--reason")
    sp.add_argument("--resolve", action="append"); sp.add_argument("--accept-removals", action="store_true")
    sp = sub.add_parser("get", parents=[common]); sp.add_argument("id"); sp.add_argument("field", nargs="?")
    sp.add_argument("--section")
    sp.add_argument("--json", action="store_true")
    sp = sub.add_parser("list", parents=[common]); sp.add_argument("--type"); sp.add_argument("--json", action="store_true")
    g = sp.add_mutually_exclusive_group(); g.add_argument("--archived", action="store_true"); g.add_argument("--trash", action="store_true")
    sp = sub.add_parser("read", parents=[common]); sp.add_argument("--skill", required=True); sp.add_argument("--product")
    sp.add_argument("--json", action="store_true")
    sp = sub.add_parser("explain", parents=[common]); sp.add_argument("slots", nargs="*"); sp.add_argument("--skill")
    sp.add_argument("--product"); sp.add_argument("--json", action="store_true")
    sp = sub.add_parser("invalidate", parents=[common]); sp.add_argument("id"); sp.add_argument("--reason", required=True)
    sp = sub.add_parser("archive", parents=[common]); sp.add_argument("id"); sp.add_argument("--reason")
    sp = sub.add_parser("restore", parents=[common]); sp.add_argument("id")
    sp = sub.add_parser("verify", parents=[common]); sp.add_argument("ids", nargs="*"); sp.add_argument("--stale", action="store_true")
    sp = sub.add_parser("set", parents=[common]); sp.add_argument("id"); sp.add_argument("field"); sp.add_argument("value")
    sp.add_argument("--source"); sp.add_argument("--reason")
    sp = sub.add_parser("assign", parents=[common]); sp.add_argument("id"); sp.add_argument("readers")
    sp.add_argument("--source"); sp.add_argument("--reason")
    sp = sub.add_parser("append", parents=[common]); sp.add_argument("id"); sp.add_argument("--text", required=True)
    sp.add_argument("--under"); sp.add_argument("--source"); sp.add_argument("--reason")
    sp = sub.add_parser("add", parents=[common]); sp.add_argument("type"); sp.add_argument("title")
    sp.add_argument("--parent"); sp.add_argument("--after"); sp.add_argument("--body-file")
    sp.add_argument("--source"); sp.add_argument("--reason")
    sp = sub.add_parser("snapshot", parents=[common]); sp.add_argument("action", nargs="?", choices=["import"])
    sp.add_argument("--label"); sp.add_argument("--apply", action="store_true"); sp.add_argument("--code")
    sp = sub.add_parser("bootstrap", parents=[common]); sp.add_argument("--observed", required=True)
    sp.add_argument("--apply", action="store_true"); sp.add_argument("--code"); sp.add_argument("--take", action="append")
    sp.add_argument("--skip", action="append"); sp.add_argument("--only", action="append")
    sp.add_argument("--json", action="store_true")
    sp = sub.add_parser("propose", parents=[common]); sp.add_argument("--skill", required=True)
    sp.add_argument("--delta", action="append"); sp.add_argument("--file")
    xp = sub.add_parser("inbox").add_subparsers(dest="action", required=True, parser_class=Parser)
    sp = xp.add_parser("list", parents=[common]); sp.add_argument("--json", action="store_true")
    for act in ("accept", "reject"):
        sp = xp.add_parser(act, parents=[common]); sp.add_argument("which", nargs="+"); sp.add_argument("--code")
        sp.add_argument("--reason")
    sp = sub.add_parser("undo", parents=[common]); sp.add_argument("--steps", type=int, default=1)
    sp = sub.add_parser("validate", parents=[common]); sp.add_argument("--recheck", action="store_true")
    sp.add_argument("--observed")
    sp = sub.add_parser("consolidate", parents=[common]); sp.add_argument("--now"); sp.add_argument("--json", action="store_true")
    sp = sub.add_parser("show", parents=[common]); sp.add_argument("ids", nargs="*"); sp.add_argument("--json", action="store_true")
    sp = sub.add_parser("health", parents=[common]); sp.add_argument("--json", action="store_true")
    sub.add_parser("card", parents=[common])
    rp = sub.add_parser("repo").add_subparsers(dest="action", required=True, parser_class=Parser)
    sp = rp.add_parser("list", parents=[common]); sp.add_argument("--json", action="store_true")
    sp = rp.add_parser("status", parents=[common]); sp.add_argument("id", nargs="?"); sp.add_argument("--json", action="store_true")
    sp = rp.add_parser("kit-check", parents=[common]); sp.add_argument("folder")
    sp = rp.add_parser("copy", parents=[common]); sp.add_argument("id"); sp.add_argument("--restore"); sp.add_argument("--now")
    sp.add_argument("--background", action="store_true"); sp.add_argument("--json", action="store_true")
    sp = rp.add_parser("add", parents=[common]); sp.add_argument("folder"); sp.add_argument("--email", required=True)
    sp.add_argument("--team"); sp.add_argument("--role"); sp.add_argument("--apply", action="store_true"); sp.add_argument("--code")
    ip = sub.add_parser("index").add_subparsers(dest="action", required=True, parser_class=Parser)
    ip.add_parser("status", parents=[common])
    ip.add_parser("rebuild", parents=[common]).add_argument("--download", action="store_true")
    sp = sub.add_parser("search", parents=[common]); sp.add_argument("action", nargs="?", choices=SEARCH_ACTIONS)
    sp.add_argument("--q", action="append"); sp.add_argument("--get"); sp.add_argument("--full", action="store_true")
    sp.add_argument("--skill"); sp.add_argument("--product"); sp.add_argument("--limit", type=int)
    sp.add_argument("--sources"); sp.add_argument("--no-hints", action="store_true"); sp.add_argument("--json", action="store_true")
    sp.add_argument("--pick", action="append", metavar="ID|PATH")
    sp.add_argument("--not", dest="not_", action="append", metavar="ID|PATH")
    sp.add_argument("--golden", metavar="PATH")
    sp = sub.add_parser("entity", parents=[common]); sp.add_argument("words", nargs="*"); sp.add_argument("--q", action="append")
    sp.add_argument("--slot", action="append")
    sp.add_argument("--kind"); sp.add_argument("--skill"); sp.add_argument("--json", action="store_true")
    sp.add_argument("--apply", action="store_true"); sp.add_argument("--code")
    vp = sub.add_parser("vault").add_subparsers(dest="action", required=True, parser_class=Parser)
    sp = vp.add_parser("normalize", parents=[common]); sp.add_argument("--only"); sp.add_argument("--skip")
    sp.add_argument("--apply", action="store_true"); sp.add_argument("--code"); sp.add_argument("--json", action="store_true")
    sp = sub.add_parser("audit", parents=[common]); sp.add_argument("--all", dest="all_", action="store_true")
    sp.add_argument("--json", action="store_true")
    sp = sub.add_parser("graph", parents=[common]); sp.add_argument("words", nargs="+")
    sp.add_argument("--depth", type=int, choices=(1, 2), default=1); sp.add_argument("--kind")
    sp.add_argument("--json", action="store_true")
    ip_ = sub.add_parser("identity").add_subparsers(dest="action", required=True, parser_class=Parser)
    sp = ip_.add_parser("check", parents=[common]); sp.add_argument("repo"); sp.add_argument("--bundle", required=True)
    sp.add_argument("--json", action="store_true")
    for act in ("keep", "take"):
        sp = ip_.add_parser(act, parents=[common]); sp.add_argument("repo"); sp.add_argument("field"); sp.add_argument("--bundle", required=True)
    sp = sub.add_parser("history", parents=[common]); sp.add_argument("--month"); sp.add_argument("--write", action="store_true")
    sp.add_argument("--json", action="store_true")
    op_ = sub.add_parser("overlay").add_subparsers(dest="action", required=True, parser_class=Parser)
    for act in ("show", "plan"):
        sp = op_.add_parser(act, parents=[common]); sp.add_argument("repo", nargs="?"); sp.add_argument("--json", action="store_true")
        if act == "plan":
            sp.add_argument("--file")
    sp = op_.add_parser("apply", parents=[common]); sp.add_argument("repo"); sp.add_argument("--file"); sp.add_argument("--code")
    sp = op_.add_parser("add", parents=[common]); sp.add_argument("repo"); sp.add_argument("--block", required=True)
    sp.add_argument("--path"); sp.add_argument("--op", required=True); sp.add_argument("--value", action="append")
    sp.add_argument("--value-ref", dest="value_ref"); sp.add_argument("--expects", type=int); sp.add_argument("--reason")
    sp.add_argument("--id")
    sp = op_.add_parser("rm", parents=[common]); sp.add_argument("repo"); sp.add_argument("op_id")
    sp = op_.add_parser("answer", parents=[common]); sp.add_argument("repo"); sp.add_argument("op_id")
    sp.add_argument("how", choices=("drop", "retarget", "expects")); sp.add_argument("--path"); sp.add_argument("--expects", type=int)
    kp = sub.add_parser("slot").add_subparsers(dest="action", required=True, parser_class=Parser)
    sp = kp.add_parser("bind", parents=[common]); sp.add_argument("repo"); sp.add_argument("target"); sp.add_argument("slot")
    sp.add_argument("--team")
    sp = kp.add_parser("map", parents=[common]); sp.add_argument("record"); sp.add_argument("heading"); sp.add_argument("slot")
    sp = kp.add_parser("prefer", parents=[common]); sp.add_argument("slot"); sp.add_argument("who")
    sp = kp.add_parser("decide", parents=[common]); sp.add_argument("slot"); sp.add_argument("repo"); sp.add_argument("--product")
    sp = kp.add_parser("forget", parents=[common]); sp.add_argument("slot")
    pp = sub.add_parser("provider").add_subparsers(dest="action", required=True, parser_class=Parser)
    sp = pp.add_parser("adopt", parents=[common]); sp.add_argument("repo"); sp.add_argument("--apply", action="store_true")
    sp.add_argument("--json", action="store_true")
    sp = pp.add_parser("plan", parents=[common]); sp.add_argument("repo", nargs="?"); sp.add_argument("--product")
    sp.add_argument("--all", action="store_true"); sp.add_argument("--json", action="store_true")
    sp = pp.add_parser("apply", parents=[common]); sp.add_argument("repo", nargs="?"); sp.add_argument("--product")
    sp.add_argument("--choose", action="extend", nargs="+"); sp.add_argument("--add", action="extend", nargs="+")
    sp.add_argument("--json", action="store_true")
    sp = pp.add_parser("sync", parents=[common]); sp.add_argument("repo", nargs="?"); sp.add_argument("--if-due", action="store_true")
    sp.add_argument("--now"); sp.add_argument("--json", action="store_true")
    return p


COMMANDS = {"status": cmd_status, "migrate": cmd_migrate, "compile": lambda a, c: cmd_sync(a, c, source="compile"),
            "sync": cmd_sync, "get": cmd_get, "list": cmd_list, "set": cmd_set, "append": cmd_append,
            "add": cmd_add, "snapshot": cmd_snapshot, "undo": cmd_undo, "validate": cmd_validate, "card": cmd_card,
            "read": cmd_read, "explain": cmd_explain, "invalidate": cmd_invalidate, "archive": cmd_archive, "restore": cmd_restore,
            "verify": cmd_verify, "assign": cmd_assign, "repo": cmd_repo, "provider": cmd_provider, "slot": cmd_slot, "overlay": cmd_overlay, "history": cmd_history, "identity": cmd_identity,
            "index": cmd_index, "search": cmd_search, "entity": cmd_entity, "graph": cmd_graph, "audit": cmd_audit, "vault": cmd_vault, "propose": cmd_propose, "show": cmd_show, "health": cmd_health,
            "inbox": cmd_inbox, "bootstrap": cmd_bootstrap, "consolidate": cmd_consolidate}


def emit(result, conflict=None):
    if conflict is not None:
        print("CTX_CONFLICT " + json.dumps(conflict, ensure_ascii=False))
    print("CTX_RESULT " + json.dumps(result, ensure_ascii=False))


def _journal_size(c):
    """The journal's size in bytes (None: none) — a write that added no line leaves the month's changelog as it is."""
    try:
        return os.path.getsize(os.path.join(c.store.state_dir, "journal.jsonl"))
    except OSError:
        return None


def main(argv=None):
    try:
        a = build_parser().parse_args(argv)
    except Usage as e:
        print("ctx: %s — `ctx.py --help`" % e)
        emit({"ok": False, "error": str(e)})
        return 3
    try:
        if writes(a):                                   # since v3.21.0: no free text a write keeps may hold a secret
            cn.check(*_free_text(a))
            if a.cmd == "set":                          # «API key: abcd…» is a secret only read together
                cn.check("%s: %s" % (a.field, a.value))
        c = Ctx(a)
        with cs.guard_roots(co.allowed_roots(c.home, c.text)):
            before = _journal_size(c) if writes(a) else None
            rc, res = COMMANDS[a.cmd](a, c)
            idle = a.cmd == "provider" and a.action == "sync" and not res.get("synced")    # a sync that synced nothing
            if rc == 0 and writes(a) and c.store.exists() and _journal_size(c) != before:   # since v3.23.0: the changelog
                try:
                    chi.write(c.store, now()[:7])
                except Exception:  # noqa: BLE001 — a derived note never changes the command's result
                    pass
            if rc == 0 and writes(a) and not idle:      # since v3.13.1: the summary the digest shows on a cold start,
                try:                                    # on the digest's budget; a miss saves nothing
                    co.summary_in_time(c.found, home=c.home)
                except Exception:  # noqa: BLE001 — a cache never changes the command's result
                    pass
        emit(dict({k: v for k, v in res.items() if not str(k).startswith("_")}, ok=rc == 0))
        return rc
    except co.Conflict as e:
        print("ctx: %s" % e)
        emit({"ok": False, "command": a.cmd, "error": str(e)}, conflict=e.payload)
        return 2
    except (co.Refused, co.Busy, cs.RegionError, cs.PathRefused, cn.NeverStore) as e:
        print("ctx: refused — %s" % e)
        emit({"ok": False, "command": a.cmd, "error": str(e)})
        return 4
    except cb.SourceLost as e:                          # checked before the lock; here only if the state moved meanwhile
        print("ctx: the repository is unavailable — %s" % e)
        emit({"ok": False, "command": a.cmd, "error": str(e)})
        return 5
    except Usage as e:
        print("ctx: %s" % e)
        emit({"ok": False, "command": a.cmd, "error": str(e)})
        return 3
    except (cs.StoreError, ValueError, OSError) as e:
        print("ctx: %s" % e)
        emit({"ok": False, "command": a.cmd, "error": str(e)})
        return 3


if __name__ == "__main__":
    sys.exit(main())
