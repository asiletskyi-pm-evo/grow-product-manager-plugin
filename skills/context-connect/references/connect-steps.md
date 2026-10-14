# Connect steps — the full procedure

Skill-local reference of `context-connect`. Contract and manifest: `references/context-provider-protocol.md`. The builder is `scripts/provider_bundle.py` at the plugin root (resolve it like a shared reference: `${PLUGIN_ROOT}`, else `${CLAUDE_PLUGIN_ROOT}`, else the directory that contains `skills/`). `--version` prints its version; a provider may ship its own copy — use the newer one and tell the provider's owner when they differ.

Talk about teams, roles, bundles and context — not about paths, regular expressions or field names, unless the user must act on one.

## §0 Where the provider, the target and the context are

1. **The user's context.** The digest's `local-context.md: FOUND at …` line; otherwise `~/.grow-pm/local-context.md`, then connected folders (`$HOME/mnt/*/`). Found → **merge mode** (the builder gets `--existing-context`). Not found → **new-context mode**: a minimal context from the provider's skeleton, extended later by `plugin-configurator`. "Not found from this shell" is not "not configured" when the digest says otherwise — ask.
2. **The provider.** In order: (a) a folder with `_System/provider-manifest.yaml` at its root or one level below; (b) a registration already in `{vault}/{plugin_folder}/_System/providers/`; (c) an MCP server in the session exposing `vault_search` and `vault_get_note` — then §7. A folder with a role model but no manifest is not a provider yet: tell the user its owner has to add `_System/provider-manifest.yaml` (protocol §9) and stop.
3. **Placement.** Two layouts are supported:
   - **Separate folder** (recommended): the core is its own Obsidian vault next to the user's; no link collisions.
   - **Nested** in the user's vault (`<vault>/<core folder>/`): one graph, but Obsidian resolves `[[basename]]` across the whole vault, so notes with the same name outside the core (`_index`, `README`, `Dashboard`) can capture the core's links. Say so once when you see this layout.
4. **Declined blocks.** A user who already merged only some of the core's blocks (others duplicate their own sections) keeps that choice: ask once which block ids to skip, or read `skip_blocks` from the registration.
5. **Target.** The core unpacked as the user's own copy (no `_System/bundle-manifest.md` yet) → in-place (`--in-place`, `--out` = the same folder). A separate core and a separate target → a selective copy into `--out`. A target that already has `_System/bundle-manifest.md` → **refresh**: read team, role and core version from it. Never ask where the bundle goes: a core folder without a bundle manifest is in-place unless the user names another target, and the placement note in item 3 is said only for a core nested in the user's vault.

When `~/.grow-pm/` is not visible from the shell (hosted sessions see the user's files through connected folders), ask the user to place a copy of their context as `local-context.existing.md` in the proposal folder (`--proposal-dir`, §3), or in `<target>/<plugin_folder>/_System/` when the target is the user's own — the builder picks it up without a flag — or read it through device tools.

## §1 Identity — dry run

```
python3 "<plugin root>/scripts/provider_bundle.py" --core "<core>" --out "<target>" --email <e-mail> --propose-only
```

- The first line, `email … → team … · role …`, becomes one sentence for the user; the role is inferred from the registry card's role title (`role_hints`) — the user may correct it.
- `UNKNOWN_TEAM {json}` (exit 2) — the e-mail is not in the role model: (1) look it up in the provider's directory (`directory_label`) if the user has access, and map the unit to a team card; (2) otherwise one question with the team titles and the role profiles from the JSON; (3) repeat with `--team <slug> --role <profile>`; (4) at the end, a line for the owner to add the person to the registry.
- An umbrella team (a department lead) means the union of its teams: warn that the bundle is large.
- The first line ends with `inferred '<role>' is not in the role model, using '<profile>'` — say which profile was used in the same sentence and offer to pick another (`--role`).
- Exit 3 prints one line naming the file, the line or the key: the core or its manifest is missing or does not parse, a pattern does not compile, the role model does not load, or an explicit `--role` is not in it. Show the line, nothing was written; a defect in the core goes to its owner.

## §2 Jira write scope

One question with three answers: "yes — <key from the team card>" · "yes — another key" (typed) · "no — read only". Yes → `--jira-write own` (a key that differs from the card: pass `--team`, and tell the owner to fix the card's `jira` field); no → `--jira-write none`. The answer lands in the team block (`jira_write_scope`), the bundle manifest and the registration; changing it later is the same run with another flag.

## §3 Bundle and proposal

```
python3 "<plugin root>/scripts/provider_bundle.py" --core "<core>" --out "<target>" --email <e-mail> \
        [--in-place] [--team <slug>] [--role <profile>] [--name "Name Surname"] \
        [--existing-context "<copy of local-context.md>"] --jira-write own|none [--no-personal-overlay] \
        [--skip-blocks <id,id>] [--proposal-dir "<private folder>"]
```

Pass `--skip-blocks <id,id>` with the blocks the user declined (a refresh reads them from the registration's `skip_blocks`): they are never proposed, the report lists them, and the proposed registration keeps the list. Run `--dry-run` first when the user has a context: it already writes the merge report and the proposal, so duplicates and discrepancies show before anything is copied. Use `--no-personal-overlay` when building an archive for others (focus and to-do notes are created on the user's machine instead). `--force` rewrites the user's notes in the bundle — only on request.

**Where the proposal goes.** The proposal and the report hold the user's whole context. By default they land in `<target>/<plugin_folder>/_System/`, which is right for a target the user owns. When the target is the core itself (in-place) and the core folder syncs back to others — a shared drive, a team repository, a sync job — pass `--proposal-dir` with a folder only the user sees: `{vault}/{plugin_folder}/_System/` in their own vault, else `~/.grow-pm/proposals/<provider id>/`.

What the builder does:
- copies the role-filtered part of the core (shared files, the team's files by the role's layers, the manifest), never the owner's personal layer (`exclude`, `personal_overlay`), registry cards with registry fields only;
- turns links into the owner's personal layer into plain text, adds one note per changed file, prunes the entry note's links to files outside the bundle;
- writes `team-context.md` and prepares `local-context.proposed.md`, `context-merge-report.md` and `provider-registration.proposed.yaml` (schema `provider-registration/2`, §6) in the proposal folder;
- places blocks: `team` right after the user's own `### Team:` section (or updates it where it is); every other block in one reference section before `## Custom Sections`; Product / Competitors / OKR / CJM / Key Metrics blocks never replace the user's sections (`reference_only` in the report); a block the user moved keeps its place and is updated there;
- adds the provider to `## Obsidian Vaults` → `### Vault Search MCP`;
- reports every block as added, updated, unchanged or reference only, and lists blocks the core no longer offers (left where they are); a refresh with nothing new returns your file byte for byte — no changelog, no new date;
- is **not** a discrepancy: `Work Email` = the work e-mail; a transliterated name; any alias on the team card;
- refuses (exit 4, nothing written) when a block the provider contributes matches a deny pattern — the line names the block and the core's owner fixes it; the user's own text is never checked — or when nested markers would reach the proposal.

## §4 Apply

1. One question per discrepancy from the report (keep mine · take the core's · same thing → alias). Typical: e-mail (another account?), product (the user works on another one → add the provider's as one more), Jira key (fix the card through the owner, or the user's context), team (alias, or another card with `--team`).
2. Five lines of what changes. Nothing of the user's text disappears.
3. After "yes", by path. A context store exists when the session digest shows a `context: records …` line — on a host without the digest (Codex CLI): when `{storage_root}/_System/context/.state/` exists — and SHELL is available. With a store the provider's blocks go in through `ctx` (§4a) and the builder's `local-context.proposed.md` is **not** copied over the context; without a store, or without a shell, the proposal path (§4b) stays as it was.
4. Jira accountId shown as "look up by e-mail" → with the user's consent, look it up through the Atlassian connector (read-only) and write it into the profile.

### §4a With a context store (since v3.13.0)

`ctx provider …` names a repository by its registration id, so the provider is registered first (§6 item 1: after the user's "yes" on a first connection; already there on a refresh). Every command below is `python3 "<plugin root>/scripts/ctx.py" …`; `plan` writes nothing, `apply` and `adopt --apply` take a snapshot before they write. The bundle files and the discrepancy questions are the builder's, as in §3 and §4 items 1–2; only where the **blocks** go changes.

**Refresh** — the blocks of a provider the user is already connected to:

1. Read the plan.
   ```
   python3 "<plugin root>/scripts/ctx.py" provider plan <repo>
   ```
   One row per block, with a sign: `=` no change · `~` the core changed a block you did not touch (apply updates it) · `✎` you edited a block the core did not change (your edit stays) · `⚠` both changed · `+` a block your context does not have · `−` the core dropped a block you did not edit (apply removes it) · `✂` you removed a block (it stays removed) · `?` no base to compare with · `·` not checked (a skipped block, or a team block that cannot be built — the reason follows). `⚠` rows show the lines each side changed; the last line counts the questions and the records an apply would rewrite. Without `<repo>` it covers every registered repository (`--product <name>` limits it to one product's), `--all` lists the skipped blocks too.
2. Ask **once**, in one message, and only about `⚠`, `+` and `?` rows — the recommended answer first: `⚠` → mine (keep your edit; the core's version of that block is dropped) · `+` → add · `?` with the block still offered → theirs. Other answers: `⚠` → theirs (the core's text) or both (yours, then the core's, marked); `?` → mine or both; `+` → leave it (it is asked again next time; to stop, add its id to the registration's `skip_blocks`). A block the core **removed** (a `⚠` or `?` row whose core text is missing) is different — recommended: mine, which keeps the text as your own without the markers; theirs removes it; both is refused. Say `~`, `✎`, `−` and `✂` rows in one line; they are never asked. No `⚠`, `+` or `?` row → no question at all: the plan was shown and `apply` is snapshot-backed (`ctx undo` takes it back), so apply the `~` and `−` rows and report them in one message.
3. Apply the answers.
   ```
   python3 "<plugin root>/scripts/ctx.py" provider apply <repo> [--choose <block>=theirs|mine|both ...] [--add <block> ...]
   ```
   One flag per block. A block with no answer stays a question; the rows that need none are applied anyway. Say what was written and that `ctx undo` takes it back.
4. Exit codes of `plan` and `apply`: 0 done, or nothing to do · 2 an answer is still awaited (the rest was applied — ask only about the blocks the output names) · 3 a block named in `--choose` or `--add` is not in the plan, or the call is wrong · 4 a block was refused (its markers are broken) and nothing else changed · **exit 5, the repository is unreachable** (the core folder is not here and its server does not answer): say so in one line with the reason the output gives, say that nothing changed, and do not retry in a loop.

A refresh through the store **never** stamps `Updated:`, never appends a `### Changelog — <namespace>` table and never rewrites the `### Vault Search MCP` bullet: the snapshot is the backup, the plan is the changelog, and the digest counts the provider's age from the store's last check. A line `warning: registration has no namespace — the core's manifest says <ns>; add …` means an old (v1) registration: the plan still works because the core's manifest is read — say it in one line and offer, after a yes, to add the `namespace: <ns>` line to the registration, or to replace the registration with the v2 file the builder proposes, after showing the differences (§6).

**Connect** — a first connection, the user's context may already hold some of the provider's blocks:

1. After the user's "yes" on the five lines (§4 item 2): write the registration (§6 item 1). Blocks the user declined are its `skip_blocks`.
2. Add the blocks the report lists as `added` (`team` among them when listed) — the blocks the user did not decline, one `--add` each:
   ```
   python3 "<plugin root>/scripts/ctx.py" provider apply <repo> --add <block> [--add <block> ...]
   ```
   Exit 2 is expected when the context already holds blocks of the provider that have no base yet: the next command settles them.
3. Set the bases of the blocks the context already holds — `provider adopt --apply`:
   ```
   python3 "<plugin root>/scripts/ctx.py" provider adopt <repo> --apply
   ```
   Without `--apply` it only shows what it would do. A block whose text equals the repository's, or differs only by the user's edits at the same version, gets a base; any other stays a question for the next plan.
4. Read `provider plan <repo>` once more. All rows `=` or `✎` → connected; anything else is asked as in a Refresh. Exit 5 at any step: the repository is unreachable and that step wrote nothing.

`ctx` only reads the core and the server; it never writes into the core's folder or the provider's copy.

### §4b Without a context store

The proposal replaces the file:
```
mkdir -p ~/.grow-pm/backups/pre-<provider id>-<YYYY-MM-DD>
cp ~/.grow-pm/local-context.md ~/.grow-pm/backups/pre-<provider id>-<YYYY-MM-DD>/
cp "<target>/<plugin_folder>/_System/local-context.proposed.md" ~/.grow-pm/local-context.md
```
Keep the last 5 backups (`references/persistent-storage.md`). Refresh the vault mirror (`{vault}/{plugin_folder}/_System/local-context.md`) when the user keeps one, and compare it with `cmp`.

With a store, a discrepancy answered "take the core's" edits the context itself: after saving it run `python3 "<plugin root>/scripts/ctx.py" sync --source context-connect --reason "<what was saved>"` to bring that edit into the records (exit 2: show the two versions from `CTX_CONFLICT`, ask which to keep, re-run with `--resolve <id>=file|record`; `references/context-protocol.md`). No store or no shell: nothing more.

## §5 Focus note

`focus-interview.md` (skill-local). Five questions, one at a time, each answer written right away.

## §6 Register and finish

1. **No registration for the provider yet:** copy `provider-registration.proposed.yaml` to `{vault}/{plugin_folder}/_System/providers/<id>.yaml` (no vault: `~/.grow-pm/providers/<id>.yaml`). `paths` lists the provider root as the user's machine sees it; in a hosted session add the mounted spelling too — both are checked by the write boundary. `writable` comes from the manifest's `personal_overlay`.
   **A registration already there is the user's, and a Refresh keeps it.** The proposal is regenerated from the core on every run, so it always says `status: active`, `products: []` and never carries what the user finished by hand — `endpoint.headers_env`, `products`, `blocks_source`, `home_record`, `skip_blocks`, `status: paused`, a rank they set. A refresh therefore updates only `synced_at` and `source_version`, and — for a v2 file — adds a v2 key the file lacks; it never changes a key that is present. A v1 file gets only the two dates until the user says yes (no silent upgrade). Replacing the file by the proposal happens only on the user's explicit yes, after the differences between the two are shown.
   The proposal is `provider-registration/2`, the schema `ctx provider` reads: besides the v1 keys it holds `core_root` (the core folder, `--core`), `namespace` and `blocks_file` (from the manifest), `rank` (from the authority: personal 100, team 500, org 1000) and `products: []` (empty = serves every product). When the manifest names a server (`mcp.url`) it adds `endpoint.url`, and `endpoint.root` — the core's folder with a trailing slash — when the core sits inside a vault listed in the user's context (the server serves that vault; pass `--existing-context`, §3, for the builder to see it). A server that needs a header is the user's to finish: `endpoint.headers_env` names the environment variable holding `Name: value`, never the value. An older v1 registration keeps working.
2. Entry points, a test question through `context-navigator`, lines for the owner, the `people_resolver` check — as in the skill's Step 6.
3. Project memory, when the host has one: team, role, provider id, target path, core version, date, whether a context existed and what was done with it.

## §7 MCP-only providers

A provider reachable only as a server (no folder on the user's machine):
1. Read its manifest when it serves one (`vault_get_note` on `_System/provider-manifest.yaml`), else ask for the id and title.
2. Show the host configuration entry the user adds themselves — a remote server behind a VPN is usually bridged locally, for example `npx -y mcp-remote@latest <url> --transport http-only`. Never edit the host configuration file.
3. After the user restarts the session, probe with `brain_status` or `vault_list_by_folder("")` (3 s); say plainly when it does not answer (VPN off, server down).
4. Register it (`kind: mcp`, no `paths`) and add the `### Vault Search MCP` bullet through the same backup-and-changelog apply as §4.
