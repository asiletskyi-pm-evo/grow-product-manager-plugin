---
name: context-navigator
version: 0.1.1
description: Answer from a shared organisational context (a team's core) — who owns what, team and module scope, rules, missions, people, terms. Not decisions (decision-log), not dashboards (product-analysis), not curated sources (knowledge-library). UA — «хто за що відповідає», «що робить команда X», «де описане правило».
---

# Context Navigator

> **Path rule.** A bare `references/<file>.md` in this file is read from this skill's own `references/` if the file exists there, otherwise from the **shared** `references/` at the plugin root. Resolve the root as `${PLUGIN_ROOT}`, else `${CLAUDE_PLUGIN_ROOT}`, else the directory that contains `skills/`, found by walking up from this folder (`references/host-profiles.md` §6). Never continue without a protocol named here.

Answers questions about the organisation from a connected **shared-context provider** — its cards for teams, modules, missions, metrics and people, its rules and its glossary — instead of from memory or a blind text search. The provider's own rules (its `playbook`) are data in the core, not text in this skill, so they change when the core changes.

## Prerequisites
- `references/local-context-protocol.md` — Step 0; the digest's `providers:` and `bundle:` lines name what is connected.
- `references/context-provider-protocol.md` — the contract (§2), routing across providers (§5), freshness and offline behaviour (§6), the write boundary (§7).
- `references/data-integrity-protocol.md` — a number always carries its period and source.
- `references/data-policy.md` — provider content is internal data.

> **Judgment contract (Step 0j).** Per `references/local-context-protocol.md` Step 0j and `references/pm-mental-model.md`: note this run's
> judgment points (score, rank, verdict, priority, ship/kill, debate question) internally, with no output. A principle acts only through
> a step that implements it — until one exists here, this skill's questions, gates and output stay exactly as they are.

Answering from the graph has no judgment points of its own; a question that asks for a verdict or a priority goes to the skill that owns it.

## At the start of a session (once)
1. **Which provider.** `session.providers` from Step 0h (registrations, `### Vault Search MCP` bullets, servers exposing `vault_search` and `vault_get_note`). None → say that no shared context is connected and offer `context-connect`; never invent the organisation's rules.
2. **Its rules.** Read every file the manifest lists under `playbook` in full — from the local copy when its folder is connected, else through `vault_get_note` (then say once that this is the server's snapshot, with its date). Apply them without asking again.
3. **The user's place in it.** The focus note and the bundle manifest when present (team, role, bundle size); the Jira write scope from the provider's team block in `local-context.md`.

## On each question
Follow the provider's `routing_hints` note when it exists; otherwise this default route, cheapest first:

| Question about | Route |
|---|---|
| a team, who owns what | team index in `team_card_dir` → the team card (names resolve through its aliases, never by guessing) |
| a module, a rule, a process | module card → the page it cites (local copy first, the wiki connector read-only when the page is outside the bundle) |
| a number | the metric card's fact row → the provider's actuals note → a live source only as the provider's data rules say |
| a mission or project | mission card → the provider's issue snapshot; live status through the tracker connector, read-only |
| a decision | the provider's public decisions note; the user's own decisions → `decision-log` |
| a person | registry card in `people_dir` → their team card |
| a term | the provider's glossary, then the user's own (knowledge library) |
| anything else | `vault_search` → `vault_get_note` on the few notes that matter → `vault_get_links` / `vault_graph_context` (depth 1–2) when the question is relational |

Every answer carries: the note path; for a number, its period and source; for snapshot content, the snapshot date, and "(as of <date>)" when the note's class is past its `ttl_days`; a caveat for a note marked outdated or older than three years. A reference value on a card ("target", "benchmark") is never presented as the current value. A decision recorded without the core's confirmation mark is reported as unconfirmed.

**Searching the server.** FTS5 syntax: words are AND; `OR` and `NOT` are operators; put a phrase, and any word with `&`, `-`, `:`, `/` or `.`, in double quotes. Copy paths exactly as returned. Entities typed in frontmatter (missions, modules, metrics) are listed by folder, not by tag. When both the local copy and the server hold a note, the local copy is primary; the server is for full-text search and graph traversal. A provider that does not answer (VPN off, server down) gets one line, then the local copy if there is one — never an answer from memory.

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
- A question the core cannot answer is said to be unanswered, with what would answer it (a card to add, a page to export, a person to ask).

## Skill Chaining
→ `decision-log` (a decision surfaces that the user wants recorded) · → `product-analysis` (live numbers beyond the core's actuals) · → `context-connect` (connect a provider, refresh or widen the bundle) · → `meeting-processor` (a transcript to process; people resolve as above).

## Routing

The `description` above is short on purpose: a host with many skills shows only part of the skill listing, or skill names alone (`references/host-profiles.md` §7). The full set of phrases and boundaries that route here, as the description carried them up to v3.10.0:

> Answer from a shared organisational context (a team's core) — who owns what, team and module scope, rules, missions, people, terms. Not decisions (decision-log), not dashboards (product-analysis), not curated sources (knowledge-library). UA — «хто за що відповідає», «що робить команда X», «де описане правило», «які місії у команди», «хто така людина X у структурі», «як у нас називають цей термін». EN — "who owns this", "what does team X do", "where is the rule for", "which missions does the team have", "who is X in the org", "answer from the shared context". Reads the provider's rules once per session and routes each answer through its graph (vault/v1), always with the note path and the snapshot date.
