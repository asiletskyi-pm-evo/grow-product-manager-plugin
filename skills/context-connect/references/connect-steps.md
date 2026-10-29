# Connect steps — the full procedure

Skill-local reference of `context-connect`. Contract and manifest: `references/context-provider-protocol.md`. The builder is `scripts/provider_bundle.py` at the plugin root (resolve it like a shared reference: `${PLUGIN_ROOT}`, else `${CLAUDE_PLUGIN_ROOT}`, else the directory that contains `skills/`). `--version` prints its version; a provider may ship its own copy — use the newer one and tell the provider's owner when they differ.

Talk about teams, roles, bundles and context — not about paths, regular expressions or field names, unless the user must act on one.

## §0 Where the provider, the target and the context are

1. **The user's context.** The digest's `local-context.md: FOUND at …` line; otherwise `~/.grow-pm/local-context.md`, then connected folders (`$HOME/mnt/*/`). Found → **merge mode** (the builder gets `--existing-context`). Not found → **new-context mode**: a minimal context from the provider's skeleton, extended later by `plugin-configurator`. "Not found from this shell" is not "not configured" when the digest says otherwise — ask.
2. **The provider.** In order: (a) a folder with `_System/provider-manifest.yaml` at its root or one level below; (b) a registration already in `{vault}/{plugin_folder}/_System/providers/`; (c) an MCP server in the session exposing `vault_search` and `vault_get_note` — then §7. A folder with a role model but no manifest is not a provider yet: tell the user its owner has to add `_System/provider-manifest.yaml` (protocol §9) and stop.
3. **Placement.** Two layouts are supported:
   - **Separate folder** (recommended): the core is its own Obsidian vault next to the user's; no link collisions.
   - **Nested** in the user's vault (`<vault>/<core folder>/`): one graph, but Obsidian resolves `[[basename]]` across the whole vault, so notes with the same name outside the core (`_index`, `README`, `Dashboard`) can capture the core's links. Say so once when you see this layout.
4. **Declined blocks.** A user who already merged only some of the core's blocks (others duplicate their own sections) keeps that choice: ask once which block ids to skip, or read `skip_blocks` from the registration. A block that now has a slot may be offered back on a refresh (§4c item 4).
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
- **Your words against the core's (since v3.23.0, with a store and a registration).** Save the JSON the dry run prints (from its first `{`) to a file in the session's scratchpad and run `ctx identity check <repo> --bundle <file>` (`references/context-protocol.md` §5r). A row that differs is two lines — the core's value with where it came from, yours with its source — and the two commands; ask once, the recommended answer first (keep yours unless the user says the core is right): `ctx identity keep <repo> <team|role> --bundle <file>` · `ctx identity take <repo> role --bundle <file>`. Taking the core's team is a rebuild with `--team <slug>` (§3), not an identity answer. A row already answered (`лишено твоє …`) is not asked.

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
2. Ask **once**, in one message, and only about `⚠`, `+` and `?` rows — the recommended answer first: `⚠` → mine (keep your edit; the core's version of that block is dropped) · `+` → add · `?` with the block still offered → theirs. Other answers: `⚠` → theirs (the core's text) or both (yours, then the core's, marked); `?` → mine or both; `+` → leave it (it is asked again next time; to stop, add its id to the registration's `skip_blocks`). A block the core **removed** (a `⚠` or `?` row whose core text is missing) is different — recommended: mine, which keeps the text as your own without the markers; theirs removes it; both is refused. Say `~`, `✎`, `−` and `✂` rows in one line; they are never asked — whether or not there is a question about other rows. No `⚠`, `+` or `?` row → no question at all: the plan was shown and `apply` is snapshot-backed (`ctx undo` takes it back), so the order is the plan in one line → `apply` → the report, the `~` and `−` rows said in one message.
3. Apply the answers.
   ```
   python3 "<plugin root>/scripts/ctx.py" provider apply <repo> [--choose <block>=theirs|mine|both [<block>=… …]] [--add <block> [<block> …]]
   ```
   The form is `--choose <block>=theirs|mine|both [<block>=… …]` and `--add <block> [<block> …]`. One `--choose` takes several answers and one `--add` several blocks (`--choose okr=theirs teams=mine --add kpi`); repeating a flag works too. The repository goes first — a word with `=` in its place, or a repository named after the answers, stops with exit 3 — and so does a block the plan does not have, before anything is imported. A block with no answer stays a question; the rows that need none are applied anyway; an answer for a block that needs none is dropped and listed (`не потрібне`). `--choose <block>=theirs` is also an answer for a `✎` (since v3.14.0): it takes the core's text for a block only the user changed — how a block the daily sync left as the user's is taken (the sync's report prints that command ready under a conflict it kept as the user's, `context-provider-protocol.md` §12.11). Say what was written and that `ctx undo` takes it back.
4. Exit codes. `plan` exits 0, or 5 — never 2: it asks nothing itself. `apply`: 0 done, or nothing to do · 2 an answer is still awaited (the rest was applied — ask only about the blocks the output names), or edits waiting to be imported conflict (`CTX_CONFLICT`: show both versions, as for `ctx sync`) · 3 a block named in `--choose` or `--add` is not in the plan, a search-only registration was named, or the call is wrong · 4 a block was refused (its markers are broken) and nothing else changed, or the run itself was refused (a store inside a provider's folder, a busy lock). Both: **exit 5, the repository is unavailable** — the core folder is not here and its server does not answer, or its blocks file is empty, cut, another repository's, or holds none of the blocks the context has a base for (a wrong or stale copy is never read as "the core removed every block"): say so in one line with the reason the output gives, say that nothing changed, and do not retry in a loop. When the core moved — a kept `core_root` or `endpoint` that differs from the proposal (§6 item 1) — point to that line and offer the replacement on a yes.

A refresh through the store **never** stamps `Updated:`, never appends a `### Changelog — <namespace>` table and never rewrites the `### Vault Search MCP` bullet: the snapshot is the backup, the plan is the changelog, and the digest counts the provider's age from the store's last check. A line `warning: registration has no namespace — the core's manifest says <ns>; add …` means a registration without the key: the plan still works because the core's manifest is read. A v1 file is the user's until they say yes — say it in one line and offer, after a yes, to add the `namespace: <ns>` line, or to replace the registration with the v2 file the builder proposes, after showing the differences (§6). A v2 file that lacks only the key gets it from the manifest on the Refresh, silently, like any missing v2 key (§6 item 1). Until the key is there, the card line and the provenance line of `ctx read` do not name the repository.

**Connect** — a first connection, the user's context may already hold some of the provider's blocks:

1. After the user's "yes" on the five lines (§4 item 2): write the registration (§6 item 1). Blocks the user declined are its `skip_blocks`.
2. Add the blocks the report lists as `added` (`team` among them when listed) — the blocks the user did not decline, one `--add` each. The blocks the report lists as `reference_only` are not added here: they show as `+` in the next plan, and the user decides then:
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

### §4c Slots after a refresh (with a store, since v3.15.0)

A slot is the place in a record where an answer lives (`references/context-protocol.md` §5f). A block of the core answers a slot only when it is **bound** to it — by the user (`ctx slot bind`), by the publisher (`slot=` in the block's marker) or by the plugin (the `team` block's `Members`). This skill binds nothing without the user's yes (`ctx slot bind`; the publisher's `slot=` and the plugin's `team#Members` bind without one), and what the user answers is remembered in the store's `.state/slots.json` by `ctx slot …` — a snapshot, a journal line, and `ctx undo` takes it back. After the apply of §4a (a refresh), in this order:

1. **Read.** `python3 "<plugin root>/scripts/ctx.py" validate` writes nothing. Take from its lines and from `CTX_RESULT` (`slot_proposals`: `[{repo, block, sub, slot}]`):
   - `warning: proposal: ctx slot bind <repo> <block>[#<sub>] <slot>` — a block of a registered repository that nothing binds and whose heading answers the names of a slot (a block with any binding, and the `team` block, are never proposed);
   - `warning: slot <slot> diverges between <a>, <b> — ctx slot decide <slot> <repo>` — two repositories of the same rank say different things for the slot, and there is no text of the user's own for it, no core rule, no preference and no remembered answer;
   - `warning: slot binding: <repo> <block>[#<sub>] → <slot> — <why>` — a binding that does nothing (a slot the catalogue lacks, a block the core took away, a block that gives its slot no text, a publisher's `slot=` the user's own binding set aside) or a block that cannot be given to one team. Say each in one line and ask nothing about it; for the second kind keep `ctx slot bind <repo> <block> <slot> --team <team record>` ready, for the user may want it.
   A line that says a registration, the slots memory or a block state was not read (`реєстрацію … не прочитано`, `пам'ять слотів не прочитано …`, `стан блоків … не прочитано …`) — say it in one line and stop: ranks, rules or decisions are unknown. A slots memory that cannot be read is an error of `validate` (exit 3): the other slot checks were skipped, and `ctx slot …` stops on it too.
2. **Bindings to confirm — one message.** For each proposal: the block, the slot, what the slot holds (its `about` in `references/context-slots.yaml`) and, when the proposal names a subsection (`#<Підсекція>`), which. The options: bind all (recommended) · bind some · not now. A yes runs `ctx slot bind <repo> <block>[#<sub>] <slot>` for each confirmed proposal, exactly as `validate` printed it (a name with a space is in quotes there, so the command pastes as it stands). What is declined stays a proposal and comes back at the next refresh. Say that no text of the user's changes.
3. **Divergences — one screen.** For each divergent slot: the slot, what it holds, and the text of each side with its repository (the rows of `ctx explain <slot>` name the record and the block; read the text with `ctx get <record id>`). The options per slot: each repository, or not now (every skill keeps getting both texts, with their sources named). Show the texts with their sources and the day each was last checked (`станом на`, as `ctx explain <slot>` prints it) and recommend no side. The answer is `ctx slot decide <slot> <repo>` (`--product <name>` for a product or team slot when the context has several products). It is kept with the hash of every side's text, so the question returns once, when a repository publishes a new text.
4. **Blocks the user switched off — at a refresh, one message.** `ctx explain` with no arguments ends with `Вимкнені блоки (skip_blocks) — ядро пропонує, ти вимкнув:` and one `<repo> · блок <id>` line each (`CTX_RESULT.skipped_blocks`). For each, read the block in the core — the registration's `core_root` + `blocks_file`, or the note on its server; reading only — and keep those that now have a slot: its begin marker names one in `slot=`, or a heading in it answers the `names` of a slot in `references/context-slots.yaml`. Offer them in one message: what each holds, the slot it would answer, and the plain consequence — «твоє й далі перемагає; ядро буде видно рядком «також» і в `ctx explain`». The options per block: return it · leave it off (recommended when the user switched it off because it duplicates their own section). On a yes **for a block**:
   1. `ctx slot bind <repo> <block>[#<Підсекція>] <slot>` first, so that a refusal (exit 3) has changed nothing else;
   2. take that one id out of `skip_blocks` in the registration (`{vault}/{plugin_folder}/_System/providers/<id>.yaml`, else `~/.grow-pm/providers/<id>.yaml`): one line of the file, nothing else touched, shown before it is written. This is the second exception of `references/context-provider-protocol.md` §3b and it needs the yes for this block;
   3. the block is now a `+` row of `ctx provider plan <repo>`. The yes covers it: `ctx provider apply <repo> --add <block>` writes it (a snapshot; `ctx undo` takes it back) with no further question, or the daily sync adds it (§6 item 2) if the user prefers to wait. Say which.
   A no changes nothing: the block stays in `skip_blocks` and is offered again at the next refresh. An id is never added to `skip_blocks` here.
5. A "not now" applies nothing: the user's context, the registration and the memory stay as they were.

## §5 Focus note

`focus-interview.md` (skill-local). Five questions, one at a time, each answer written right away.

## §6 Register and finish

1. **No registration for the provider yet:** copy `provider-registration.proposed.yaml` to `{vault}/{plugin_folder}/_System/providers/<id>.yaml` (no vault: `~/.grow-pm/providers/<id>.yaml`). `paths` lists the provider root as the user's machine sees it; in a hosted session add the mounted spelling too — both are checked by the write boundary. `writable` comes from the manifest's `personal_overlay`.
   **A registration already there is the user's, and a Refresh keeps it.** The proposal is regenerated from the core on every run. Three keys the user finishes by hand are not in it at all — `endpoint.headers_env`, `blocks_source`, `home_record` — and two are in it as defaults that would overwrite theirs: `products: []` and `status: active` (the user may have set `status: paused`). `skip_blocks` is not among them: the run passes the registration's own list (`--skip-blocks`, §3), so the proposal repeats it. A refresh therefore updates only `synced_at` and `source_version`, and — for a v2 file — adds a v2 key the file lacks; it never changes a key that is present. A nested key counts: a missing `endpoint.root` inside an `endpoint:` that is there is a missing key and is added, while an `endpoint.headers_env` that is there stays. A v2 file with no `namespace` gets it from the manifest the same way, silently. A v1 file gets only the two dates until the user says yes (no silent upgrade).
   **One key is the exception: `sync`** (since v3.14.0). The rule above — a key that is present is never changed — holds for every key except `sync` (and, since v3.15.0, the taking of one id out of `skip_blocks`, below). The proposal a refresh builds carries no `sync`, so the refresh's own merge never adds, changes or removes it; it changes only on the user's own yes — after the question of item 2, or when the user asks to turn the daily sync on («увімкни щоденний синк ядра») or off («вимкни синк ядра»), a request that goes to item 2 whatever the key says — and then it is one line of the registration, nothing else of the file.
   **The second exception: one id out of `skip_blocks`** (since v3.15.0). On the user's explicit yes for a block they had switched off and that now has a slot (§4c item 4), that one id is taken out of the registration's `skip_blocks` — one line of the file, nothing else touched — and nothing is ever added to the list here. The proposal a refresh builds repeats the list the registration holds (`--skip-blocks`, §3), so the refresh's own merge changes nothing of it.
   **Keys the core decides.** `core_root`, `namespace`, `blocks_file`, `paths`, `endpoint.url`, `endpoint.root` and `rank` come from the core, and a refresh keeps them too when they are present. It compares them with the proposal and reports every one that differs, one line per key — `<key>: yours <value> · the core now says <value>` — and offers the replacement of those keys on a yes (after the core folder moved or the server changed, say). An exit 5 (§4a) points to these lines when the core moved. Replacing the whole file by the proposal happens only on the user's explicit yes, after the differences between the two are shown.
   The proposal is `provider-registration/2`, the schema `ctx provider` reads: besides the v1 keys it holds `core_root` (the core folder, `--core`), `namespace` and `blocks_file` (from the manifest), `rank` (from the authority: personal 100, team 500, org 1000) and `products: []` (empty = serves every product). When the manifest names a server (`mcp.url`) it adds `endpoint.url`, and `endpoint.root` — the core's folder with a trailing slash — when the core sits inside a vault listed in the user's context (the server serves that vault; pass `--existing-context`, §3, for the builder to see it). A server that needs a header is the user's to finish: `endpoint.headers_env` names the environment variable holding `Name: value`, never the value. An older v1 registration keeps working.
2. **Turn on the daily sync (since v3.14.0)** — with a context store and SHELL, for a registration that publishes blocks (not search-only), is not `status: paused` and does not yet say `sync: daily` or `sync: off` (the user has answered once: a refresh never asks again). An explicit request to turn the daily sync on or off comes here whatever the key says; turning it off needs no `?` settling and no question — write `sync: off` and say so. With no store, or no shell, there is nothing to sync and nothing is asked. In order:
   a. **Settle every `?` first.** Read `ctx provider plan <repo>` (§4a). A `?` row has no base to compare with: unless the block is a core rule (`policy=rule`, where the sync takes the core's text), the sync does not decide it — it leaves the user's text as it is and the block waits for an answer — so every `?` is settled with the user before the sync is switched on. Ask about each one as in §4a item 2 — one message, the recommended answer first (`theirs` when the core still offers the block, `mine` when the core removed it) — apply the answers with `--choose` (several in one flag, §4a item 3) and read the plan again. Go on to b only when no `?` row is left; if the user leaves one unanswered, say that the daily sync waits for it and ask again at the next refresh.
   b. **Ask the daily sync question** — one question, in `user.language`, the recommended answer first, that tells the user plainly what the sync will do without asking. The facts to say (the rules behind them are `context-provider-protocol.md` §12.11 — do not restate more):
      - it runs once a day, in the first skill the user opens after 24 hours, when the core's server or folder answers; with the VPN off it is skipped and tried again at the first skill start an hour or more later, and it never holds a skill for more than 20 seconds;
      - it updates the blocks the user did not touch, adds blocks that are new in the core (to leave one out, its id goes into the registration's `skip_blocks`), and removes a block the core dropped that the user did not edit (never more than one in a pass); when both changed a block, the user's text stays unless the core marked the block a rule (`policy=rule`);
      - it asks nothing in the middle of work: the skill closes its answer with one sentence, and a note in the vault, `_System/context/sync/YYYY-MM-DD.md`, shows both texts of every conflict; every pass that changes something has a snapshot, `ctx undo` takes it back, and a text the user undid is not applied again;
      - to switch it off the user says so, or sets `sync: off`.
      The answers: **yes** (`sync: daily`) · **no** (stays as it is, and the answer is kept as `sync: off` so that nobody asks again).
   c. **After a yes** write `sync: daily` into the registration — one line: add it, or change `sync: off` — in `{vault}/{plugin_folder}/_System/providers/<id>.yaml` (no vault: `~/.grow-pm/providers/<id>.yaml`) and touch nothing else of the file. Say when the first pass will come: a day after the last check, which this run's apply just made; `ctx provider sync <repo>` (the `ctx.py` command of §4a) runs one now. **After a no** write `sync: off`.
3. Entry points, a test question through `context-navigator`, lines for the owner, the `people_resolver` check — as in the skill's Step 6.
4. Project memory, when the host has one: team, role, provider id, target path, core version, date, whether a context existed and what was done with it.

## §8 Overlay — your corrections to a core (since v3.23.0, with a store)

A prose note of corrections to a core («Оверлей … — поправки до ядра», in the user's layer or a `writable` path of the core) becomes declared operations (`references/context-protocol.md` §5n). The note is read, never changed.

1. `ctx provider plan <repo>` must show no `⚠` or `?` for the blocks the note speaks of — settle those first (§4a).
2. Read the note and the regions the store holds (`ctx explain`, `ctx read`). For each item that names something a **block in the records** says, draft one operation with `reason` in the note's own words: a list the user replaces with their own table → `replace` with `value_ref "<record id>#<their subsection>"`; a value the user disputes while their own text already wins the slot → `ignore` with a `match:"<the core's words>"` path, so the operation is held — one question «ядро виправили — прибрати поправку?» — the day the core's words change; a line the core should not carry → `remove`; a name the core uses for the user's team or product → `alias`. Never a value copied from the note into a block (a `value_ref` points at the user's own text).
3. Write the draft (`schema: context-overlay/1`, `repo: <id>`) to the session's scratchpad and run `ctx overlay plan --file <draft>`. One message: the plan's lines, then **«не стали операціями»** — every item of the note that is no block in the records (missions, epics, dead links, empty folders of the core), each with why, in one line.
4. On «так» → `ctx overlay apply <repo> --file <draft> --code <code>`; then `Скасувати: ctx undo` and one line the user may add to the note («перенесено в overlays/<repo>.yaml <date>») — never written by the skill.
5. A secret in the draft (`увага:` in the plan, exit 4 on apply) → drop that text from the operation and plan again.

**A held correction** (✋ `оверлей … чекають рішення` in `ctx health`, a part of a sync report, `ctx overlay show`): one question per held operation, as §5n words it; answer with `ctx overlay answer <repo> <id> drop|retarget --path …|expects --expects N`.

## §9 A provider kit in one command (since v3.23.0, with a store)

For a folder that is a provider kit (`references/context-provider-protocol.md` §9; the plugin's example: `examples/provider-kit/zorg-core/`) and is not registered yet:

1. `ctx repo kit-check <folder>` — a fault (exit 3) is said as it is and goes to the kit's owner; a warning is one line.
2. `ctx repo add <folder> --email <e-mail>` — one message from its dry run: team and role with their sources, the registration path, the blocks and where they go. `UNKNOWN`-like exit 3 (the e-mail is not in the role model) → one question with the teams it names, then `--team <key>`.
3. On «так» → `ctx repo add <folder> --email <e-mail> --apply --code <code>`; then Step 6 item 2 (the daily sync, asked once) and, when the user keeps a prose note of corrections to this core, §8.

## §7 MCP-only providers

A provider reachable only as a server (no folder on the user's machine):
1. Read its manifest when it serves one (`vault_get_note` on `_System/provider-manifest.yaml`), else ask for the id and title.
2. Show the host configuration entry the user adds themselves — a remote server behind a VPN is usually bridged locally, for example `npx -y mcp-remote@latest <url> --transport http-only`. Never edit the host configuration file.
3. After the user restarts the session, probe with `brain_status` or `vault_list_by_folder("")` (3 s); say plainly when it does not answer (VPN off, server down).
4. Register it (`kind: mcp`, no `paths`) and add the `### Vault Search MCP` bullet through the same backup-and-changelog apply as §4. With no `blocks_file` (and no core folder) the registration is search-only: `ctx provider plan|apply` leave it out with one line `лише пошук: <id>` and are not stopped by it. When its manifest names a `blocks_file`, put it in the registration with `endpoint.url` and `endpoint.root`, so `ctx provider` merges its blocks (§4a).
5. **The plugin's own copy** (since v3.24.0, with SHELL; `references/context-provider-protocol.md` §12.12). Right after registering a server with a `blocks_file`, offer once, in one line, with the count `vault_list_by_folder(endpoint.root)` gave: «Зробити власну копію ядра? ~N нотаток, ~1 хв, `~/.grow-pm/cores/<id>` — блоки, команда й пошук працюватимуть без VPN». On «так» → `ctx repo copy <id>`, then its one summary line. With `sync: daily` (Step 6 item 2) the copy is brought up to date by the daily sync in the background; without it say `ctx repo copy <id>` updates it. On a refresh of an MCP-only registration that has no copy, offer again — at most once in 30 days: a «ні» is kept in `{store}/.state/copy-offers.json` (`context-copy-offers/1`: `{"schema", "declined": {<id>: "YYYY-MM-DD"}}`; a key this build does not know is refused, never dropped; a file that cannot be read is never reset — then do not offer), never in the registration.
6. **The team block through the copy.** When the copy is made and `provider plan` shows the team row `·` with «сервер не віддає provider-manifest», give the user the request for the core's owner, ready to send: «Щоб командний блок працював і через сервер, додай, будь ласка, у ядро дві нотатки поруч із файлами: `_System/provider-manifest.md` і `_System/access-bundles.md` — frontmatter `kind: provider-file` і `file: provider-manifest.yaml` (відповідно `access-bundles.json`), а в тексті один блок коду ```yaml / ```json з умістом файлу. Опис — context-provider-protocol §9; перевірка — `ctx repo kit-check <тека ядра>`.» Never send it yourself. A `·` «обгортка … не розгорнулась: <why>» goes to the owner with the reason.
