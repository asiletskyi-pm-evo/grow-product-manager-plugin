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
                                ("не застосовуватиметься, доки ядро не змінить блок: <repo>: <blocks>"). CTX_RESULT:
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
                                Since v3.18.1 (scripts/ctx_eslots.py): one entity's `слоти:` — a person's role, team and
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
  entity same|not-same A B      your answer: A and B (a card's path or link, or a name one card alone carries) are, or are
                                not, the same — kept in the store's `.state/entities.json` (context-entity-memory/1), the
                                opposite answer replaced; `not-same` keeps them apart whatever the e-mail or a bridge
                                says. A writing command: snapshot, one journal line (op entity, action, cards), `ctx undo`
                                takes it back; one that changes nothing says "unchanged". No store («немає сховища —
                                відповідь не збережено»), a name several cards carry, two kinds, or a memory that cannot be
                                read: exit 3. CTX_RESULT: action, cards, changed, snapshot

`read` and `explain` take no lock and write nothing; `index`, `search` (but `search remember|forget`) and `entity` (but
`entity same|not-same`) take no store lock and write only the index's folder.
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
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx_blocks as cb  # noqa: E402
import ctx_common as cc  # noqa: E402
import ctx_entity as ce  # noqa: E402
import ctx_hints as ch  # noqa: E402
import ctx_index as ci  # noqa: E402
import ctx_store as cs  # noqa: E402
import ctx_ops as co  # noqa: E402
import ctx_read as cr  # noqa: E402
import ctx_repos as crp  # noqa: E402
import ctx_resolve as rv  # noqa: E402
import ctx_search as cs_  # noqa: E402
import ctx_schema as sc  # noqa: E402
import ctx_slots as sl  # noqa: E402
import ctx_synced as sy  # noqa: E402

HEADINGS = {"product": "### Product: %s", "team": "### Team: %s", "org": "## Organization: %s",
            "setting": "## %s", "custom": "## %s"}


class Usage(Exception):
    pass


WRITING = {"compile", "sync", "set", "append", "add", "snapshot", "undo", "card",
           "invalidate", "archive", "restore", "verify", "assign", "slot"}


def writes(a):
    """Does this run write to the store? Every command of WRITING does, and `provider apply`, `provider sync` and (since
    v3.16.0) `search remember|forget`, (since v3.18.0) `entity same|not-same`; `migrate` and `provider adopt` only with
    --apply. A plain search, `--get` and `search
    eval` write no store. (A `provider sync` that synced nothing saves no summary: `main`.)"""
    if a.cmd in WRITING or (a.cmd == "provider" and getattr(a, "action", None) in ("apply", "sync")):
        return True
    if a.cmd == "search" and getattr(a, "action", None) in ("remember", "forget"):
        return True
    if a.cmd == "entity" and _entity_action(a)[0] in ("same", "not-same"):
        return True
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
        if not found:
            raise cs.StoreError("no such file: %s (--context)" % a.context if a.context else
                                "no local-context.md found (GROW_PM_CONTEXT_PATH, ~/.grow-pm)")
        self.found = found                       # as found, links not followed: the digest's summary is kept beside it
        self.context = os.path.realpath(found)
        self.text = co._read(self.context)
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
    last = sorted(n for n in os.listdir(snaps) if co.SNAP_RE.match(n))[-1:] if os.path.isdir(snaps) else []
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
    """The registry `ctx read` joins team.members by (v3.18.1, plan C8), built the first time it is asked for: the index
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
        reg, _ = ce.load(sctx, idx, mem)
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


def _write_one(c, op, rid, mutate, source, reason):
    c.need_store()
    with co.lock(c.home):
        c.guard()
        pre = c.import_first()
        rec = _record(c, rid)
        body = mutate(rec["body"])
        if body == rec["body"]:
            print("unchanged — %s already says that" % rid)
            return {"command": op, "id": rid, "changed": False, "imported": pre["changed"] + pre["added"]}
        t = now()
        snap = co.snapshot(c.store, c.copies, c.home, op)
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
    return 0, _write_one(c, "set", a.id, lambda b: cs.field_set(b, a.field, a.value), a.source or "ctx-set", a.reason)


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
        c.store.write(dict(rec, read_by=value, source=source, modified=t))     # who reads it — not a content check
        c.store.journal({"ts": t, "op": "assign", "ids": [a.id], "source": source, "reason": a.reason or "",
                         "snapshot": snap})
        comp = co.compile_store(c.store, c.copies, t, c.home, snap)
    print("assign: %s read_by %s · wrote %s" % (a.id, value or "unset", ", ".join(comp["written"]) or "no copy"))
    return 0, {"command": "assign", "id": a.id, "read_by": value, "changed": True, "snapshot": snap,
               "imported": pre["changed"] + pre["added"]}


def cmd_append(a, c):
    return 0, _write_one(c, "append", a.id, lambda b: cs.append_line(b, a.text, under=a.under),
                         a.source or "ctx-append", a.reason)


def cmd_add(a, c):
    c.need_store()
    if a.type not in HEADINGS:
        raise Usage("add takes one of %s" % ", ".join(sorted(HEADINGS)))
    content = co._read(a.body_file) if a.body_file else ""
    heading = HEADINGS[a.type] % a.title
    text = heading + "\n\n" + (content.rstrip("\n") + "\n\n" if content.strip() else "")
    with co.lock(c.home):
        c.guard()
        c.import_first()
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
        c.store.journal({"ts": t, "op": "add", "ids": new, "source": a.source or "ctx-add", "reason": a.reason or "",
                         "snapshot": snap})
        comp = co.compile_store(c.store, c.copies, t, c.home, snap)
    print("added %s after %s" % (new[0], after))
    return 0, {"command": "add", "id": new[0], "after": after, "snapshot": snap, "written": comp["written"]}


def cmd_snapshot(a, c):
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
        pre = co.snapshot(c.store, c.copies, c.home, "pre-undo")
        skipped = co.restore(target, c.store, c.copies)
        for p in skipped:
            print("skipped (not a current copy): %s" % p)
        with open(os.path.join(target, "manifest.json"), encoding="utf-8") as f:
            existed = json.load(f).get("store_existed")
        reverted, kept, rejected, rejected_failed = [], [], {}, {}
        if existed:
            cs.atomic_write(jpath, journal)
            t = now()
            c.store.journal({"ts": t, "op": "undo", "ids": [], "source": "undo", "reason": target, "snapshot": pre})
            # a sync pass taken back stays taken back: the core's texts it applied are remembered as rejected in the
            # block state — after the restore, which brought that state back to what it was before the pass
            rejected, rejected_failed = remember_rejected(c.store, rejections)
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
               "rejected_failed": rejected_failed}


def cmd_validate(a, c):
    c.need_store()
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
    for e in errors:
        print("error: " + e)
    for w in warnings:
        print("warning: " + w)
    print("valid" if not errors else "%d error(s)" % len(errors))
    return (3 if errors else 0), {"command": "validate", "errors": errors, "warnings": warnings, "slot_proposals": proposals}


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
    raise Usage("repo takes list or status")


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
    return None, words


NO_STORE_ANSWER = "немає сховища — відповідь не збережено"


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
    if a.slot and action in ("same", "not-same", "pairs"):
        raise Usage("--slot asks for an entity's slots: not with %s" % action)
    if action in ("same", "not-same"):
        return _entity_answer(a, c, action, words)
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
        if len(queries) > 1:
            res = ce.run_many(sctx, queries, kind=a.kind, skill=a.skill, store=c.store, slots=a.slot)
        else:
            res = ce.run(sctx, queries[0], kind=a.kind, skill=a.skill, store=c.store, slots=a.slot)
    if not res["read"]:
        why = "; ".join(res["notes"]) or "індексу немає"
        print(ce.NOT_READ % why)
        return 5, dict(res, error="not read")
    if not a.json:
        sys.stdout.write(ce.render(res))
    return 0, res


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
        if reg.unread:                  # the index did not answer: a card it holds is no «не картка» (v3.18.1, C11)
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
    deadline = time.monotonic() + sy.BUDGET_S
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
        repos = [r for r in crp.load_repos(c.text, c.home)
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
    """The usage line for a slot the records do not know: a slot of an entity's cards (v3.18.1, plan C1a) says who
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
    sp = sub.add_parser("snapshot", parents=[common]); sp.add_argument("--label")
    sp = sub.add_parser("undo", parents=[common]); sp.add_argument("--steps", type=int, default=1)
    sub.add_parser("validate", parents=[common])
    sub.add_parser("card", parents=[common])
    rp = sub.add_parser("repo").add_subparsers(dest="action", required=True, parser_class=Parser)
    sp = rp.add_parser("list", parents=[common]); sp.add_argument("--json", action="store_true")
    sp = rp.add_parser("status", parents=[common]); sp.add_argument("id", nargs="?"); sp.add_argument("--json", action="store_true")
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
            "verify": cmd_verify, "assign": cmd_assign, "repo": cmd_repo, "provider": cmd_provider, "slot": cmd_slot,
            "index": cmd_index, "search": cmd_search, "entity": cmd_entity}


def emit(result, conflict=None):
    if conflict is not None:
        print("CTX_CONFLICT " + json.dumps(conflict, ensure_ascii=False))
    print("CTX_RESULT " + json.dumps(result, ensure_ascii=False))


def main(argv=None):
    try:
        a = build_parser().parse_args(argv)
    except Usage as e:
        print("ctx: %s — `ctx.py --help`" % e)
        emit({"ok": False, "error": str(e)})
        return 3
    try:
        c = Ctx(a)
        with cs.guard_roots(co.allowed_roots(c.home, c.text)):
            rc, res = COMMANDS[a.cmd](a, c)
            idle = a.cmd == "provider" and a.action == "sync" and not res.get("synced")    # a sync that synced nothing
            if rc == 0 and writes(a) and not idle:      # since v3.13.1: the summary the digest shows on a cold start,
                try:                                    # on the digest's budget; a miss saves nothing
                    co.summary_in_time(c.found, home=c.home)
                except Exception:  # noqa: BLE001 — a cache never changes the command's result
                    pass
        emit(dict(res, ok=rc == 0))
        return rc
    except co.Conflict as e:
        print("ctx: %s" % e)
        emit({"ok": False, "command": a.cmd, "error": str(e)}, conflict=e.payload)
        return 2
    except (co.Refused, co.Busy, cs.RegionError, cs.PathRefused) as e:
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
