---
name: context-navigator
version: 0.3.2
description: Answer and search your context — notes, cores, local indexes. Not decisions (decision-log), dashboards (product-analysis), curated sources (knowledge-library). UA — «знайди в моєму контексті», «що в мене є про…», «хто за що відповідає», «де описане правило»; with source and date, live sources on request.
---

# Context Navigator

> **Path rule.** A bare `references/<file>.md` in this file is read from this skill's own `references/` if the file exists there, otherwise from the **shared** `references/` at the plugin root. Resolve the root as `${PLUGIN_ROOT}`, else `${CLAUDE_PLUGIN_ROOT}`, else the directory that contains `skills/`, found by walking up from this folder (`references/host-profiles.md` §6). Never continue without a protocol named here.

Answers and searches from the user's own context — their notes in the plugin folder of their vault (the rest of the vault through a local index of it), the core of every connected repository, their local indexes and, when asked or when the base has nothing direct, the session's live sources (since v3.17.0, `references/search-protocol.md` §13) — and, when a **shared-context provider** is connected, from its cards for teams, modules, missions, metrics and people, its rules and its glossary: never from memory or a blind text search. The provider's own rules (its `playbook`) are data in the core, not text in this skill, so they change when the core changes. The typed `/grow-product-manager:find` runs the same search.

## Prerequisites
- `references/local-context-protocol.md` — Step 0; the digest's `providers:` and `bundle:` lines name what is connected.
- `references/context-provider-protocol.md` — the contract (§2), routing across providers (§5), freshness and offline behaviour (§6), the write boundary (§7).
- `references/data-integrity-protocol.md` — a number always carries its period and source.
- `references/data-policy.md` — provider content is internal data.
- `references/search-protocol.md` — Step 0.5 (since v3.16.0) and §13, the search the user asks for (since v3.17.0): with SHELL the search is `ctx search`; the rating, what is taken, the two forms (an answer or a list), level 2 and the block of variants.

> **Judgment contract (Step 0j).** Per `references/local-context-protocol.md` Step 0j and `references/pm-mental-model.md`: note this run's
> judgment points (score, rank, verdict, priority, ship/kill, debate question) internally, with no output. A principle acts only through
> a step that implements it — until one exists here, this skill's questions, gates and output stay exactly as they are.

Answering from the graph has no judgment points of its own; a question that asks for a verdict or a priority goes to the skill that owns it.

## At the start of a session (once)
1. **Which provider.** `session.providers` from Step 0h (registrations, `### Vault Search MCP` bullets, servers exposing `vault_search` and `vault_get_note`). None → one line, `Спільне ядро не підключене — шукаю у твоїй базі` (not when §13's `Немає де шукати: …` applies: then that line alone), and every question goes to §13 over the user's own base; offer `context-connect` only when the question is about the organisation, and never invent the organisation's rules.
2. **Its rules** (with a provider). Read every file the manifest lists under `playbook` in full — from the local copy when its folder is connected, else through `vault_get_note` (then say once that this is the server's snapshot, with its date). Apply them without asking again.
3. **The user's place in it** (with a provider). The focus note and the bundle manifest when present (team, role, bundle size); the Jira write scope from the provider's team block in `local-context.md`.

## On each question
**Who or what it is (since v3.18.0).** With SHELL, a question about a person, a team, a mission, a module, a metric, a work item or a Jira key — «хто такий X», «що за команда X», «що таке PROJ-1234», «хто посилається на X» — first runs `python3 "<plugin root>/scripts/ctx.py" entity "<X>" --skill context-navigator` (`ctx entity "<X>" --skill context-navigator`, `references/search-protocol.md` §13): its lines say who it is, where its cards are and who links to it, and the route below answers the rest of the question. Since v3.19.0 they also hold its slots — a person's role, team and e-mail, a team's members («хто в команді X»), missions and parent, a mission's teams, an owner — each with where it comes from; quote them with their source (`references/people-context-protocol.md` → Find a person for a person's identity).

**First the form** (`references/search-protocol.md` §13): a request for a fact gets an answer; a request for the notes themselves — «знайди нотатки про…», «що в мене є про…», «де в моїх нотатках…», «покажи нотатки про…», `--list` — gets a list. Then, with a provider, follow its `routing_hints` note when it exists, otherwise this default route, cheapest first. Without a provider every question takes the last row, except recording or revisiting a decision and a person, whose rows hold either way:

| Question about | Route |
|---|---|
| a team, who owns what | team index in `team_card_dir` → the team card (names resolve through its aliases, never by guessing) |
| a module, a rule, a process | module card → the page it cites (local copy first, the wiki connector read-only when the page is outside the bundle) |
| a number | the metric card's fact row → the provider's actuals note → a live source only as the provider's data rules say |
| a mission or project | mission card → the provider's issue snapshot; live status through the tracker connector, read-only |
| a decision | recording a decision, or revisiting one the user names → `decision-log`, with or without a provider; what was decided about something → §13 (it finds the decision records and the meeting notes alike), with a provider its public decisions note too |
| a person | identity only (`references/search-protocol.md` §13): the registry card in `people_dir` → its frontmatter name, e-mail, team and role and the card's path, never its body → their team card; without a provider, §13 finds the card; a profile → `one-on-one` / `performance-review` |
| a term | the provider's glossary, then the user's own (knowledge library) |
| anything else, and the user's own notes | §13 — SHELL: `ctx search` (below) → `ctx search --get` on the sections rated «прямо» for an answer, none for a list; without SHELL: §12 — the files on an FS host, `vault_search` → `vault_get_note` on an MCP host (for a list, neither `--get` nor `vault_get_note`). Then `vault_get_links` / `vault_graph_context` (depth 1–2) when the question is relational |

Every answer carries: the note path; for a number, its period and source; for snapshot content, the snapshot date, and "(as of <date>)" when the note's class is past its `ttl_days`; a caveat for a note marked outdated or older than three years. A reference value on a card ("target", "benchmark") is never presented as the current value. A decision recorded without the core's confirmation mark is reported as unconfirmed.

**Searching with SHELL (since v3.16.0; §13 since v3.17.0).** The "anything else" route and every search the user asks for follow `references/search-protocol.md` §13, which is Step 0.5 as the task itself. A card or note one of the routes above reads directly is neither taken by it nor counted as a doubt (§1). There, the question is the request of `references/search-protocol.md`, and Step 0.5 is that one search — not a second one: `python3 "<plugin root>/scripts/ctx.py" search --q "<the question's topic>" --q "<variant>" … --skill context-navigator --json`. It asks the plugin's section index — which holds the core folder of every registered repository on this machine, so the local copy comes first by construction — the user's own local index, and the server only of a repository whose core folder is not on disk; plain words, no FTS5 syntax. Rate the candidates. For an answer, read the «прямо» ones with `ctx search --get <id>` (its first line is the path and the date to cite), take at most five sections and answer from them; for a list, call no `--get` and list the notes as §13 says. When the search was unsure or two notes disagree, end an answer with the block of variants and a list with §13's unnumbered lines, and both last with the line `Де шукав: …`. Exit 5 means the base was not read: say so — never that it holds nothing.

**Searching the server** (without SHELL, or for the graph tools). FTS5 syntax: words are AND; `OR` and `NOT` are operators; put a phrase, and any word with `&`, `-`, `:`, `/` or `.`, in double quotes. Copy paths exactly as returned. Entities typed in frontmatter (missions, modules, metrics) are listed by folder, not by tag. When both the local copy and the server hold a note, the local copy is primary; the server is for full-text search and graph traversal. A provider that does not answer (VPN off, server down) gets one line, then the local copy if there is one — never an answer from memory.

**A page outside the bundle** (a dead link in a selective copy): say that it is outside the bundle and offer to read it through the wiki connector (read-only) or to widen the bundle with `context-connect` (another team or role).

## Meetings → people (when the provider declares a `people_resolver`)
Before a meeting note that names people is written into the user's vault: resolve the participants' e-mails with the resolver (`emails <list>`); every name in decisions, positions and actions with `names <list> --emails <list>` — resolved → a link to the registry card, ambiguous → keep the name and show the candidates, unresolved → ask. A short first name resolves only among the meeting's participants. Never guess a person by a similar surname. The note goes to the user's own layer, never into the core.

## What not to do
- Write anything under the provider's folders outside its `writable` paths (`references/context-provider-protocol.md` §7); a correction goes to the user's overlay note for that provider and, upstream, to the provider's owner.
- Edit generated sections of the core's cards, or rank missions by the number of tickets.
- Present the bundle as a security boundary — it is relevance only.
- Write to Jira or the wiki outside the user's own project and the write gate.

## Quality Standards
- Answers in `user.language`, short, with the path and the date; the user can open every cited note.
- One line when a provider is stale or unreachable, once per session.
- Every search ends with `Де шукав: …` — each source asked, and the one that did not answer named (`references/search-protocol.md` §13).
- A question the base cannot answer is said to be unanswered, with what would answer it (a card to add, a page to export, a person to ask).

## Skill Chaining
→ `decision-log` (a decision surfaces that the user wants recorded) · → `product-analysis` (live numbers beyond the core's actuals) · → `context-connect` (connect a provider, refresh or widen the bundle) · → `meeting-processor` (a transcript to process; people resolve as above) · → `one-on-one` / `performance-review` (a person's profile — this skill gives a person's identity only, §13).

## Routing

The `description` above is short on purpose: a host with many skills shows only part of the skill listing, or skill names alone (`references/host-profiles.md` §7). The full set of phrases and boundaries that route here, as the description carried them up to v3.10.0:

> Answer from a shared organisational context (a team's core) — who owns what, team and module scope, rules, missions, people, terms. Not decisions (decision-log), not dashboards (product-analysis), not curated sources (knowledge-library). UA — «хто за що відповідає», «що робить команда X», «де описане правило», «які місії у команди», «хто така людина X у структурі», «як у нас називають цей термін». EN — "who owns this", "what does team X do", "where is the rule for", "which missions does the team have", "who is X in the org", "answer from the shared context". Reads the provider's rules once per session and routes each answer through its graph (vault/v1), always with the note path and the snapshot date.

Since v3.18.0 (who is who, `ctx entity`): UA — «хто такий X», «що за команда X», «що таке PROJ-1234», «хто посилається на X»; EN — "who is X", "what is PROJ-1234", "what links to X".

Since v3.17.0 (the search the user asks for, `references/search-protocol.md` §13) also: UA — «знайди в моєму контексті…», «що в мене є про…», «де в моїх нотатках ми обговорювали…», «пошукай у Confluence і в моїх нотатках…», «що ми обговорювали про…»; EN — "search my notes for…", "what do I have on…", "find in my context". Typed: `/grow-product-manager:find <запит> [--list] [--all]`. The boundaries stay: recording a decision → decision-log, the curated library → knowledge-library, the web → product-research, a person's profile → the People contour.
