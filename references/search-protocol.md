# Search protocol — Step 0.5 (since v3.16.0)

What a skill does between Step 0 and Step 1 to bring in what the user's base already knows about the request: the user's own vault, the cores of the registered repositories, a local index the user registered and, when the base is not enough, the live sources of the session. This file is the single home of these rules: `vault-protocol.md` (Step 0.5), `local-context-protocol.md` (Step 0.5) and the skills that once carried their own step point here. The engine is `ctx search`: what it reads and how it merges is `context-provider-protocol.md` §5 and §10; the command, what it writes, the memory of choices and the golden set are `context-protocol.md` §3, §1 and §5g.

**The goal.** What the skill takes into its work is exactly what the base holds **directly** about the request, each piece with its source and its date. **The anti-goal** is the one this protocol exists to prevent: wrong context taken silently and becoming the source of wrong conclusions. Everything below serves one rule: when the search is not sure, or two sources disagree, nothing is taken silently — the skill does its work, then shows what it was unsure about and how to improve the search, and the user's choice is remembered for next time.

Step 0.5 asks nothing in the middle of a run; its only question is the level-2 one in §8, and only in the cases named there.

`<plugin root>` is resolved as in `local-context-protocol.md` (`${PLUGIN_ROOT}` → `${CLAUDE_PLUGIN_ROOT}` → the directory that contains `skills/`).

## 1. When Step 0.5 does not run

- **The skill's row in `SKILL_CONTEXT_MAP` is empty** (`vault-protocol.md`): `template-library`, `plugin-configurator`, `context-connect`.
- **The request has no topic** — nothing the artifact or the answer is *about*: a feature, a problem, a metric, a decision, a meeting, a person (People contour). «покажи мій конфіг», «статус плагіна», «зарелізь плагін» name an action on the plugin, not a topic. A routine request whose only subject is a period or the product as a whole — «сплануй спринт», «на чому сфокусуватись сьогодні», «звіт по кварталу» — has a topic only when it names something within it («спринт: графік роботи продавця»), or when the skill's own step names the request for that mode (cjm-research's health-check). A skill whose own steps read its previous artifacts (cjm-research's previous health-check, focus-advisor's board) keeps reading them there; Step 0.5 does not replace those steps.
- **A note the skill's own step reads directly** — context-navigator's route to a card, a People skill's profile (Step P, `people-context-protocol.md`), focus-advisor's own briefs — is neither taken by Step 0.5 nor counted as a doubt: it comes in through that step. context-navigator runs Step 0.5 only for its "anything else" route.
- **Nothing to search** — no vault in `## Obsidian Vaults`, no registered repository with a folder on disk, no local index and no MCP repository (`ctx search` exit 3 `nothing to search`; on a host without SHELL: vault level L0 and no provider). Skip silently, as L0 always did.

Step 0.5 runs once per skill run — and once more only when the skill's own questions, asked before the work starts, change or narrow the topic: then what was taken for the old topic is dropped and Step 0.5 runs again with the new request, before the work, and only its result counts. A skill invoked by another skill runs its own Step 0.5 for its own types (an automated run when it only returns a payload, §11).

## 2. The request and its variants

**The request** is the topic in the user's own words, without the instruction and without the artifact name the skill already implies: «напиши вимоги до кошика» → `кошик`; «що ми вирішили про накручені відгуки» → `накручені відгуки`; "analyze the drop in checkout conversion" → `checkout conversion drop`. Keep issue keys (`PROJ-1234`), names and numbers exactly as written. The skill's artifact types are not words of the request: `--skill` weighs them (§3). The request is the first `--q`; it is also what a choice is remembered under (§10).

**The variants** — 3 or 4, written by the model **before it sees any result** (it does not see the base when it writes them):
- Ukrainian — in the product's working words;
- Russian;
- English;
- a synonym, a piece of team jargon, or the request phrased as a note title would be.

Keys and names stay as they are; a person's or a product's name gets its spelling in the other alphabet as well. A variant that would repeat the request or another variant is left out — the request is already searched, so a Ukrainian request whose working words are its own words needs no Ukrainian variant. Keep a variant about as long as the request: a one-word request gets one-word variants where the language allows. Do not add a word the request does not imply — a variant that guesses the answer finds the guess.

## 3. The search — level 1

With SHELL:

`python3 "<plugin root>/scripts/ctx.py" search --q "<request>" --q "<variant 1>" … --skill <this skill> --product "<active product>" --json`

- `--product` is the active product of Step 0d; leave it out when there is none. `--skill` is the skill's own name — `ctx search` weighs the types of its `search_types` (`references/context-manifest.yaml`, the same list as its `SKILL_CONTEXT_MAP` row) × 1.2; a type is a weight, never a filter, so a note without a type is found too. Do not pass `--limit` or `--sources`: the pool of 50 and every kind of source are the design.
- **`--json` prints only the `CTX_RESULT` line** — unlike `ctx read` and `ctx explain`, whose `--json` adds to the human output. `CTX_RESULT` holds `candidates`, `notes`, `sources` (`[{id, kind, answered}]`), `index` (the section index's state; `index.locked` is true while another process holds it — building or refreshing it) and `counts`.
- A candidate is **one note**: `id` (its best section), `path`, `heading`, `title`, `type`, `product`, `date`, `source` (the ids that hold it: `own` for your plugin folder, a repository id for a core page), `flags` (§5), `matched` (which `--q` found it, from 1), `snippet` (≤ 300 characters, the matches in «»), `score`, and `sections` — at most two sections of that note, each with its own `id`.
- **`notes`** are lines to the user: `<id> не відповів — без нього`, `індекс <id> має незнайому схему — без нього`, `індекс оновлюється: N файлів ще не переглянуто`, `пам'ять пошуку не прочитано (…) — без підказок` and the index's own lines — among them `індекс пошуку ще будується (інший процес) — цього разу без нього` (no index yet, or one another process is still filling, `index.locked`) and `індексу пошуку ще немає (…) — ctx index rebuild` (no index, and nobody building it): either way the section index (`own`) has not answered. Say each once per session, unchanged, right before the taken line (§6).

**What the exit code means — one action each:**

| Exit | Meaning | Action |
|---|---|---|
| 0, candidates | the search answered | rate them (§4) |
| 0, no candidates | the sources answered and hold nothing on the request | nothing to take: §6 «nothing directly» |
| 3, `nothing to search` | no vault, no repository, no index | skip Step 0.5 silently (§1) |
| 3, `no such skill: <name>` | the skill has no manifest entry | run the same search again without `--skill` |
| 3, anything else | a usage error | one line `Пошук не виконано: <помилка>`, then continue without context — never «У базі нічого прямо про це» |
| 5 | **no source answered** — an own index that is busy, not built yet or being built by another process, or still damaged after one rebuild, counts as not answered | the base was **not read**: nothing is taken, the line `Базу не прочитано: <нотатки ctx через «; »>`, and a doubt (§7) — never «У базі нічого прямо про це» |
| the command cannot run (no python, the plugin root not found) | — | follow the host without SHELL (§12) |

**A source that did not answer** (`sources[].answered` is `false`) while others did: the search is still exit 0, but that part of the base was not read. When it is the section index (`own`) or a repository reached only through MCP (`mcp` — asked only when its folder is not on disk) it is a doubt (§7); a local index (`local`) that does not answer is only its line.

## 4. Rating the candidates

Read every candidate's line — title › heading, type, date, flags, snippet — and rate it by its meaning, not by its place in the list:
- **прямо** — the note is about exactly what the request is about: it answers it, or it is the very artifact the work builds on (the concept a requirements run derives from, the decision the question asks about);
- **частково** — it touches the topic, but the answer is not there (a neighbouring feature, a general overview, one mention in a meeting);
- **ні** — anything else; a candidate you do not rate is «ні».

Read each candidate you would rate «прямо» with `python3 "<plugin root>/scripts/ctx.py" search --get <id> --json` — the `id` of the candidate, or of the one of its `sections` that answers. `CTX_RESULT` then holds `header` — the provenance line `> [<джерело> · <шлях> › <заголовок> · <дата>]` — and `text`, the section alone. For a note a local index or a server gave (its source is a `local` or an `mcp` one), the header goes on with what the note's frontmatter says and the list could not: ` · sensitive`, ` · застаріле` (its status) and its type — `> [zorg-growth · @zorg-growth/Old sync.md · 2026-06-01 · sensitive · застаріле · meeting]`. Such a candidate's flags are complete only after `--get`: a header that carries ` · sensitive` or ` · застаріле` counts as that flag (§6) — the section is not used and its content is not repeated, and a people type there counts as `sensitive` outside the People contour. A section shorter than 200 characters — an image, a breadcrumb, one line — goes on in `text` with the sections after it, up to 1 500 characters, after the line `секція коротка — додано наступні: <заголовки>`: read them as the same note. A note whose file iCloud has not downloaded is never opened: its `text` starts with `файл не завантажено з iCloud — текст із локального індексу <id>` (the copy a registered local index holds), or `--get` exits 3 with `файл не завантажено з iCloud: <шлях> — відкрий його в Obsidian або ctx index rebuild пізніше`. Reading may change the rating: a section that turns out not to answer is «частково». Read only those; the snippet is enough for the rest. `--get` exit 3 (an unknown id — the ids of the last searches were lost) → read the note's file by its `path`; exit 3 with `файл не завантажено з iCloud: …` or a file not read in time, and exit 5 (an MCP note whose server did not answer) → the note was not read: say its line, it is not taken, and it is a doubt.

The marks (`flags`) say what the search knows about a candidate:

| Mark | What it means | What it does here |
|---|---|---|
| `застаріле` | `status` outdated, archived, deprecated, former or superseded, or older than the `ttl_days` of its class | never taken silently (§6); if all you found is this — a doubt |
| `старіша версія <шлях>` | a newer version of the same document exists at `<шлях>` | never taken; read the newer one from its path and rate that |
| `є старіші версії: N` | the newest of its versions; the older ones were folded into it | may be taken |
| `двійник <шлях>` | the same thing in another place (the same file, the same Confluence page twice, the same text, a near copy — the same text but for a back-link, a date line, a «Повʼязане» block, the frontmatter —, a hub of your layer and the core page) was folded into it | may be taken; when the fact you take is a number, a decision or an owner, read the twin too — if they say different things, it is a conflict (§7) |
| `знімок від <день>` | it comes from a repository whose snapshot is older than its `stale_after_days` | may be taken, with that day in the taken line (§6); taking it is a doubt |
| `sensitive` | `sensitive: true` in its frontmatter, or in a copy folded into it | outside the People contour: never taken, never read with `--get`, in the block by its title only (§6, §9) |
| `хаб` | a glossary, a map of contents, a people list, a focus brief, a daily summary, a style guide | never taken silently; it may point the way — a note it links to is read from its path and rated like a candidate |
| `лише глосарій` | found only through the glossary's other names for a word of the request | if it is the best you have — a doubt |
| `одне слово` | matched at best one word of a variant of several | if it is the best you have — a doubt; when the request itself is one word the mark says nothing, and is ignored |
| `твій вибір від <день>` | the user picked it for a similar request (§10); it weighs × 1.5 | rate it as any other — the mark is evidence, not a pass |
| `ти казав «не те»` | the user said it was not it for a similar request | never taken silently; in the block it keeps the mark |

A version number in a title makes a version key just as a draft mark does — a product's (`API v2`, `API v3`) as much as a document's (`v3`, `draft`): of two notes in one folder whose titles differ only by it, the older is marked `старіша версія <шлях>` (or folded into the newer) and is never taken.

A note you reached from a hub, a twin or a newer version is rated like a candidate and may be taken; its provenance is its path and its own date.

## 5. What a candidate's source and date are

- **Source** — the first id of the candidate's `source`: `own` (your plugin folder) or the repository's id (a core page, `zorg-core`). A local index or an MCP server names itself the same way.
- **Date** — the day of the candidate's `date` (the first ten characters); a note only a local index knows, with no date in its frontmatter, is dated by that index's file time. A candidate marked `знімок від <день>` carries both: `(<джерело>, <дата>, знімок від <день>)`. A piece found in a live source (§8) carries `живе · <день>` — the day it was read — in place of the date.

## 6. What is taken, and what never is

**Taken silently** — at most **three sections** rated «прямо» and not excluded below. More than three «прямо» is no doubt: take the three the work needs most (the one that answers the request most fully first, then the newer). The skill says so in **one line**, after Step 0.5 (and level 2, §8) and before the work:

`Взяв із бази: <назва › секція> (<джерело>, <дата>) · <назва › секція> (<джерело>, <дата>)`

`<назва>` is the candidate's title, `<секція>` the last part of the section's heading (a note with no heading: the title alone). In the work, every fact from a taken piece is stated with its source and date (`data-integrity-protocol.md`), and the vault save lists the taken notes in `related`.

**Nothing taken** — one line, whichever holds:
- no candidate rated «прямо» → `У базі нічого прямо про це`, when every source of kind `own` and `mcp` answered; when one of them did not, `У базі нічого прямо про це (не відповів: <id>)`;
- «прямо» there was, but every one is excluded below → `З бази нічого не взяв: <чому — застаріле | sensitive | суперечність | …> — варіанти наприкінці`. The base does hold something on the request, so «У базі нічого…» would be false;
- no source answered (exit 5) → `Базу не прочитано: …` (§3) — the base cannot be said to hold nothing when it was not read.

Each of them is a doubt (§7); level 2 may start (§8).

**Never taken silently:**
- a candidate rated «частково» or «ні», and one whose rating you are not sure of;
- one marked `застаріле` or `старіша версія <шлях>`; at level 2, a copy behind its live page (§8). `знімок від <день>` alone does not forbid it;
- **outside the People contour** (`goal-setter`, `one-on-one`, `performance-review`, `hiring-designer`, `offboarding-guide`, `delegation-coach`): a candidate marked `sensitive`, and one of the people types (`data-policy.md` → Search, rule 1). It is not read, its content is not repeated anywhere, and it can never be picked: in the block it may appear only as an unnumbered line with its title (§9). A candidate a server gave (its source is an `mcp` one in `sources`) carries no `sensitive` mark in the list — the server's search does not say; its `--get` header does (§4) — so outside the People contour treat one whose path lies under a people folder (`People/`, the core's `people_dir`) as sensitive even before reading it;
- a hub;
- a candidate marked `ти казав «не те»`;
- what contradicts another piece rated «прямо»: then **both** go to the block, the conflict named (§7), and the work goes on with the rest.

## 7. Doubt and conflict

**A doubt** is any of:
- nothing rated «прямо» was taken — there was none, or every one was excluded (§6);
- the base was not read, or a source of kind `own` or `mcp` did not answer (§3) — the section index not built yet (`індексу пошуку ще немає (…) — ctx index rebuild`) or being built by another process (`index.locked`, `індекс пошуку ще будується (інший процес) — цього разу без нього`) is one: the base was not read, never «У базі нічого прямо про це»;
- nothing was taken while the index said `індекс оновлюється: N файлів ще не переглянуто` — the files it has not seen yet may hold the answer; its block line is `повторити пошук: за хвилину`;
- all that was found is marked `застаріле`;
- something marked `знімок від <день>` was taken;
- the best candidate is marked `лише глосарій` or `одне слово`;
- a `--get` of a «прямо» failed (§4);
- the model itself is not sure of a rating — say of what.

**A conflict**: two pieces found say different things about one fact — a number, a decision, an owner, a date — or a copy lags behind its live page (§8). Two «прямо» from different documents that disagree are both a conflict and a doubt.

A doubt or a conflict ends the answer with the block of variants (§9) and may start level 2 (§8, which names every case that may). Neither stops the work or asks in the middle of it. A doubt that level 2 settled — a live piece rated «прямо» was taken for what the base lacked — raises no block; a conflict always does.

## 8. Live sources — level 2

- **When.** The skill decides. Level 2 may start on a doubt, on a conflict, when what was taken lacks a fact the work needs — a number, a decision, an owner, a status, a page's current content — or when nothing was found; and only when a live source in the session can hold what is missing. Otherwise it does not start: it is not part of every run.
- **Where.** What the session has (`integration-strategy.md`, pattern detection): Confluence (CQL `text ~ "<variant>"` for each variant), Jira (JQL `text ~ "<variant>"`), Fireflies, Drive, mail. The routing of `context-provider-protocol.md` §5 still applies: an organisation question starts at the provider whose `playbook` covers it.
- **When to ask the user first** — one question in `user.language`, naming the source and the reason, in an interactive run only:
  - the source needs a VPN or a login the session does not have now;
  - the request is broad and would take many calls;
  - the data is sensitive: person profiles, private channels, mail.

  Otherwise go, and say so in one line before the taken line: `Живі джерела: <Confluence, Jira, …> — <чому, одним рядком>`.
- **The mark.** A piece found live carries `живе · <день>` (§5) and is rated like a candidate; at most three pieces are taken in all, base and live together.
- **A copy against its live page.** A core page and its live Confluence page are matched by the page id — `confluence_id` in the copy's frontmatter, else the number of six or more digits in brackets before `.md` in its path. Compare the copy's `modified` (or its date) with the live page's `lastModified` / `version` — never the bytes. When the live page is newer, take the live one; the copy is marked `копія відстала` and the line `копія відстала: <шлях>` is said once; it is never taken silently again in this run, and it is a conflict (§7).
- **Nothing is written.** What level 2 finds goes into no index, no record and no store: it lives in this session.
- **Data boundaries.** Everything stays in the session and in the user's own connectors (`data-policy.md`).

## 9. The block of variants

At the very end of the answer that delivers the skill's work — after the artifact or the reply, the save line and any closing lines; once per run — **only** when there was a doubt or a conflict:

- `Пошук: <чому — одним рядком>`
- `1) <назва › секція> — <джерело, дата> — <чим відрізняється / чому не взяв>`
- `2) …`
- `3) уточнити запит: «…»`
- `4) живе джерело: <Confluence | Jira | …> — <що там шукати>`
- `Цифра — повторю роботу з вибраним; «не те» — запам'ятаю.`

Rules:
- **Two to four numbered lines**, numbered from 1 in the order they are filled — the lines above show the kinds, not fixed places. There is no empty block: fill it in this order — the candidates worth choosing (each «прямо» not taken — but a sensitive one or a people type only as the unnumbered line below — then the best «частково», each with why it was not taken: `частково: …`, `застаріле`, `суперечить 2): …`, `ти казав «не те»`); `уточнити запит: «…»` — a narrower or a wider wording of the request (two different wordings may fill two lines); `живе джерело: …` for a source the session has that level 2 did not already search. When the base was not read (exit 5), or nothing was taken while the index had files not yet seen (§7), one line may be `повторити пошук: <коли або як — за хвилину | ctx index rebuild>`.
- **The `Пошук:` line** says the reason in the user's language: no «прямо» about «…»; the base was not read and why; two documents say different things about <the fact>; only outdated notes; the snapshot of <repo> is from <day>; <id> did not answer; the best match came only through the glossary; not sure that «…» is it.
- **A sensitive candidate or a people type** outside the People contour: one **unnumbered** line, `· <назва> — <джерело, дата> — sensitive, зміст не показую` — no section, no snippet, and no number, so it cannot be picked; it does not count among the two to four numbered lines.
- The fixed words of the block are printed exactly as written here; titles, sections and reasons are filled in.

## 10. The user's choice

The user answers with a number, with «не те», or both («2, а 1 — не те»):
- **A candidate's number** → `python3 "<plugin root>/scripts/ctx.py" search remember --q "<request>" --pick <id> [--product "<product>"]` — the request exactly as the first `--q` of the search, the same product. Then the skill does its work again with that piece taken (read with `--get`) and says in one line what changed.
- **A live piece's number** (found at level 2, §8) → the work again with it taken; it has no id, so nothing is remembered — unless a local copy of that page exists (the same page id, §8): then `search remember --q "<request>" --pick "<the copy's path>"`.
- **«не те»** (about a numbered line, or about a piece that was taken) → `search remember --q "<request>" --not <id>`, and the work is done again without it. «не те» with no number means what was taken: one piece — that one; several — ask which, in one short question. Both in one answer → one call with `--pick` and `--not`.
- **`уточнити запит`** → Step 0.5 again with the new wording as the request; nothing is remembered.
- **`живе джерело`** → level 2 (§8) on that source, then the work again.
- **`повторити пошук`** → `ctx index rebuild` when the note asked for it, then Step 0.5 again.

A remembered choice is a hint for every later request whose stems are similar (Jaccard ≥ 0.6) and whose product does not differ: a pick weighs × 1.5 and is marked `твій вибір від <день>`, a «не те» is marked `ти казав «не те»`. `remember` is a writing command — a snapshot, one journal line, and `ctx undo` takes it back; say in one line that the choice is remembered and that `ctx undo` takes it back. Exit 3 with `немає сховища — підказку не збережено` → say that line; the work is redone all the same. Exit 3 for an id no search gave (the ids of the last searches keep the newest thousand) → pass the note's `path` instead of the id. "Forget what I chose for …" → `ctx search forget --q "<request>" [--product "<product>"]`.

## 11. «Відсутнє», automated runs, write-concept's build-first types

**«Відсутнє» → search** (`context-protocol.md` §5a). A slot that `ctx read` named in `Відсутнє:` at Step 0c may be looked for here: one more `ctx search` whose request is the missing item's name and whose variants are its other names. What it finds is never taken silently and never stated as the slot's value — it may only appear in the block of variants, as a candidate that may hold the missing item. Slots are filled by the cascade alone (`context-protocol.md` §5f).

**Automated runs** — a scheduled or headless run, or a skill invoked only for a return payload: Step 0.5 runs as above (variants, search, rating, taking), but nobody is there to answer. The taken line goes into the report header or the payload's data notes; a doubt or a conflict is one line `Пошук: <чому>` in those notes — no block, nothing remembered; level 2 goes only to a source that needs no question, and one that would need one is named in the same line.

**write-concept, while `judgment.build_first` is `on`.** Candidates of type `walkthrough`, `ab-test-results` and `prototype` do what `references/judgment-points.md` §8 and `skills/write-concept/references/judgment-blocks.md` §2 say: one that addresses the riskiest assumption suppresses the build-first line, whether it was taken or not, and a prototype found is linked on resume. They are not in the skill's `search_types`, so they carry no weight; they are found by their words. On their own they never raise the block of variants: a doubt or a conflict that only they would raise raises none, and they join a block only when other candidates raise it. While `build_first` is `off` they are ignored.

## 12. Hosts

| Host (`host-profiles.md`) | What there is |
|---|---|
| FS + SHELL (Claude Code, the desktop app, Codex CLI) | all of the above. The rating is done by the session's model itself — no subagent is needed, so a host without SUBAGENT loses nothing |
| a Cowork VM | the same, when it has SHELL |
| SHELL without a context store | `ctx search` over the vaults of `local-context.md` and the registrations; the block of variants is shown, but a choice is not remembered (`remember` says `немає сховища — підказку не збережено`) |
| FS without SHELL | this protocol in prose, below |
| MCP only (ChatGPT, cloud hosts) | `vault_search` of the providers, below; no section index |

**FS without SHELL.** No index and no `ctx`: for each variant, look through the plugin folder of each vault and the core folder of each registration (`core_root`, else its `paths`) for notes whose title, headings or text hold its words — the words of the request, never "the 10 newest of a type". Leave out what `ctx` would: `_System/context/`, the blocks file, `_System/providers/` and `_System/_scratch/`, `.obsidian/`, `.trash/`, folders that start with `_backup`, non-`.md` files. Treat the skill's `SKILL_CONTEXT_MAP` types as a weight, not a filter. Read the frontmatter for the marks of §4 that it gives (`status`, `sensitive`, `type`, a hub's type or title, the date), rate, take, raise the block as above, and cite path and date. When the session also has the server of a repository whose folder is not on disk, ask it as under "MCP only" below and merge its list with yours by reciprocal-rank fusion. A choice cannot be remembered: say `Вибір не збережено: тут немає оболонки — пізніше: ctx search remember --q "<запит>" --pick "<шлях>"`.

**MCP only.** For each variant, `vault_search` on every reachable provider (`context-provider-protocol.md` §2): the variant's words without stop words, as written (no stemming), each in double quotes with `*` after a word of four letters or more, joined by ` OR ` (`"кошик"* OR "мобільний"*`) — plain words would be read as "all of them". Merge the lists by reciprocal-rank fusion (k = 60), one entry per path; read «прямо» with `vault_get_note` and take the section that answers. The same rating, taking, block and level 2; a choice is not remembered — say the same line as on a host without SHELL.
