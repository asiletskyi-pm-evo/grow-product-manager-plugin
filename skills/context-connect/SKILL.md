---
name: context-connect
version: 0.1.0
description: Connect to, refresh or enrich from a shared organisational context — a team's core folder or a provider MCP. Not the plugin's own setup (plugin-configurator), not curated sources (knowledge-library). UA — «підключи мене до спільного контексту», «підключи мене до вейлта команди», «онови мій пакет з ядра», «збагати мій контекст блоками ядра», «додай провайдер контексту». EN — "connect shared context", "connect me to the team vault", "refresh my bundle", "enrich my context from the core", "add a context provider", "register a context MCP". Resolves your team and role from your e-mail, copies the bundle that is relevant to you, proposes the core's context blocks for your local-context.md (never overwrites it; every discrepancy is a question), and registers the provider so every skill can search it.
---

# Context Connect

> **Path rule.** A bare `references/<file>.md` in this file is read from this skill's own `references/` if the file exists there, otherwise from the **shared** `references/` at the plugin root. Resolve the root as `${PLUGIN_ROOT}`, else `${CLAUDE_PLUGIN_ROOT}`, else the directory that contains `skills/`, found by walking up from this folder (`references/host-profiles.md` §6). Never continue without a protocol named here.

Connects the user's own context to a **shared-context provider** — a team's or an organisation's core knowledge — so that within ten minutes the user has the part of the core that is relevant to their team and role, the core's context blocks proposed into their `local-context.md`, a focus note, and a provider registration every other skill can search. Works for any provider that follows `references/context-provider-protocol.md`; everything provider-specific (folders, labels, note templates, what is personal) comes from the provider's manifest.

This is a model of **relevance, not security**: never promise that the bundle "hides" anything from the user.

## Prerequisites
- `references/local-context-protocol.md` — Step 0; the `GROW_PM_SESSION` digest's `providers:` and `bundle:` lines say what is already connected.
- `references/context-provider-protocol.md` — contract `vault/v1`, the provider manifest (§3a), the registration (§3b), the `### Vault Search MCP` declaration (§3c), the write boundary (§7), the provider kit (§9).
- `references/persistent-storage.md` — backups before `local-context.md` is written (last 5 kept).
- `references/data-policy.md` — provider content is internal data.
- `references/connect-steps.md` (skill-local) — the full procedure with every command; `references/focus-interview.md` (skill-local) — the five-question interview.

> **Judgment contract (Step 0j).** Per `references/local-context-protocol.md` Step 0j and `references/pm-mental-model.md`: note this run's
> judgment points (score, rank, verdict, priority, ship/kill, debate question) internally, with no output. A principle acts only through
> a step that implements it — until one exists here, this skill's questions, gates and output stay exactly as they are.

The connect run has no judgment points: it copies, proposes and records what the user confirms.

## Three rules about the user's context

1. **The context is the user's.** The skill never generates `local-context.md` "from the core" and never overwrites it. The core supplies **blocks** between markers (`<!-- <namespace>:begin id=… -->`); a refresh updates only those.
2. **A discrepancy is a question, not an edit.** A different e-mail, product, Jira project or team name in the user's context goes to the merge report; the skill asks, and only the answer decides: keep the user's value, take the core's (the core is fixed by its owner), or record an alias. The user's context is presumed right.
3. **Backup before writing, changelog after.** Before the proposal replaces `local-context.md`, the old file is copied to `~/.grow-pm/backups/`; the proposal already ends with a `Section | Was | Became` table.

## Modes

| Mode | Trigger | What happens |
|---|---|---|
| **Connect** | first connection to a provider | Steps 0–6 |
| **Refresh** | «онови мій пакет з ядра» / "refresh my bundle"; a newer core version; the digest marks the provider stale | Steps 0, 3, 4, 6 — the same run without `--force`: new files added, the user's notes kept, the blocks proposed again (usually one confirmation) |
| **Enrich** | only the context blocks, no bundle | Steps 0, 3 (`--dry-run` with the user's context), 4 |
| **Register an MCP provider** | a provider reachable only as an MCP server (no folder) | Step 0, then `references/connect-steps.md` §7 |

## Step 0 — where things are
Run Step 0-host and Step 0. Then locate: (a) the **provider** — a connected folder holding `_System/provider-manifest.yaml` (at its root or one level down), or the digest's `providers:` line, or a server in the session exposing `vault_search` and `vault_get_note`; (b) the **target** — the provider folder itself when the user unpacked the core as their copy (in-place), or a separate folder for the bundle; (c) the **user's context** — the digest path. No provider found → say that the core folder (or its server) is not connected, name how to connect it, and stop. Details and the two placements (a separate folder vs a folder nested in the user's vault, with its link-collision warning): `references/connect-steps.md` §0.

## Step 1 — e-mail → team → role (dry run)
Take the e-mail from the host account, else from the User Profile (`Work Email`, then `Email`); ask only when neither exists. Run the bundle builder in dry-run mode (`references/connect-steps.md` §1) and say in one sentence: "I see you as `<role>` in team `<title>`; the bundle is N files (pages M). Correct?" When the line says the inferred role is not in the role model, name the profile used and offer another. `UNKNOWN_TEAM` → the provider's directory (its `directory_label`), else one question with the teams and roles from the role model; then repeat with `--team` / `--role`.

## Step 2 — Jira write scope (ask, never guess)
One question: "Do you have your own Jira project where you create tasks yourself?" — yes, the key on the team card · yes, another key · no, read only. The answer becomes `--jira-write own|none` and the `jira_write_scope` line of the team block; plugin skills write to Jira only inside that project, through the write gate.

## Step 3 — bundle and proposal
Run the builder for real (`references/connect-steps.md` §3): it copies the bundle (in-place: copies nothing), writes the user's focus and to-do notes when absent, and prepares the proposal in `<target>/<plugin_folder>/_System/` — or, when the target is a core that syncs back to others, in a private folder passed as `--proposal-dir`, because the proposal holds the user's whole context: `local-context.proposed.md`, `context-merge-report.md`, `team-context.md`, `provider-registration.proposed.yaml`. Its `CONTEXT_REPORT` line says what was added, updated, kept as reference only, and every discrepancy. Exit 3 (the core, its manifest or role model cannot be used) or exit 4 (a provider block matches a deny pattern, or nested markers) → nothing was written; show the builder's one line — it names the file, key or block — and stop.

## Step 4 — discrepancies → questions → apply
1. One question per discrepancy (keep mine · take the core's · same thing, add an alias); batch them in one message when the host allows.
2. Show in five lines what will change: blocks added and updated, the provider entry, the changelog.
3. After "yes": backup, copy the proposal over `~/.grow-pm/local-context.md`, refresh the vault mirror if one exists (`references/connect-steps.md` §4). When the shell cannot reach `~/.grow-pm/`, give the user the one command to run.
4. A new context (none existed) → after copying, recommend `plugin-configurator` Validate / Update — never start it yourself.

## Step 5 — focus note (five questions, one at a time)
`references/focus-interview.md`. Write each answer into the focus note right away; link every mission the user names to the provider's mission cards; never invent one.

## Step 6 — register and finish
1. Write the registration from the proposed file to `{vault}/{plugin_folder}/_System/providers/<id>.yaml` (no vault: `~/.grow-pm/providers/`), with the provider root as the user's machine sees it (and the mounted path too in a hosted session).
2. Three entry points in three lines: the provider's dashboard → its rules (`playbook`) → the focus note. One test question answered from the graph through `context-navigator`.
3. E-mail missing from the provider's registry, or team members missing → one line per person for the provider's owner (`owner_label`): e-mail · name · team · role. Only the owner writes into the core.
4. The provider's `people_resolver`, when declared: check that the user's e-mail resolves to a registry card.

## What is forbidden
- Writing into the provider's core or the provider's copy outside its `writable` paths (`references/context-provider-protocol.md` §7).
- Overwriting the user's `local-context.md`, focus note or to-do note without an explicit "yes" after the changes are shown.
- Copying the owner's personal layer, even when asked for "everything".
- Inventing a team, a role or a mission; editing the provider's role model or blocks (only the owner's generators do that).
- Writing an MCP server into the host's configuration — show the entry; the user adds it.

## Quality Standards
- One sentence per finding, in `user.language`; paths and field names only when the user must act on them.
- Every question offers the recommended answer first.
- The proposal, the report and the registration always exist before anything is applied.
- Refresh never re-asks a discrepancy the user already answered with "keep mine" unless the core changed that field again.

## Skill Chaining
→ `plugin-configurator` (Validate / Update after a new context; the provider row in Validate) · → `context-navigator` (answers from the provider's graph) · → `task-creator` (writes only into the project the Jira write scope names).
