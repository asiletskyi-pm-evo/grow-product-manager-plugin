# Connect steps — the full procedure

Skill-local reference of `context-connect`. Contract and manifest: `references/context-provider-protocol.md`. The builder is `scripts/provider_bundle.py` at the plugin root (resolve it like a shared reference: `${PLUGIN_ROOT}`, else `${CLAUDE_PLUGIN_ROOT}`, else the directory that contains `skills/`). `--version` prints its version; a provider may ship its own copy — use the newer one and tell the provider's owner when they differ.

Talk about teams, roles, bundles and context — not about paths, regular expressions or field names, unless the user must act on one.

## §0 Where the provider, the target and the context are

1. **The user's context.** The digest's `local-context.md: FOUND at …` line; otherwise `~/.grow-pm/local-context.md`, then connected folders (`$HOME/mnt/*/`). Found → **merge mode** (the builder gets `--existing-context`). Not found → **new-context mode**: a minimal context from the provider's skeleton, extended later by `plugin-configurator`. "Not found from this shell" is not "not configured" when the digest says otherwise — ask.
2. **The provider.** In order: (a) a folder with `_System/provider-manifest.yaml` at its root or one level below; (b) a registration already in `{vault}/{plugin_folder}/_System/providers/`; (c) an MCP server in the session exposing `vault_search` and `vault_get_note` — then §7. A folder with a role model but no manifest is not a provider yet: tell the user its owner has to add `_System/provider-manifest.yaml` (protocol §9) and stop.
3. **Placement.** Two layouts are supported:
   - **Separate folder** (recommended): the core is its own Obsidian vault next to the user's; no link collisions.
   - **Nested** in the user's vault (`<vault>/<core folder>/`): one graph, but Obsidian resolves `[[basename]]` across the whole vault, so notes with the same name outside the core (`_index`, `README`, `Dashboard`) can capture the core's links. Say so once when you see this layout.
4. **Target.** The core unpacked as the user's own copy (no `_System/bundle-manifest.md` yet) → in-place (`--in-place`, `--out` = the same folder). A separate core and a separate target → a selective copy into `--out`. A target that already has `_System/bundle-manifest.md` → **refresh**: read team, role and core version from it.

When `~/.grow-pm/` is not visible from the shell (hosted sessions see the user's files through connected folders), ask the user to place a copy of their context as `<target>/<plugin_folder>/_System/local-context.existing.md` — the builder picks it up without a flag — or read it through device tools.

## §1 Identity — dry run

```
python3 "<plugin root>/scripts/provider_bundle.py" --core "<core>" --out "<target>" --email <e-mail> --dry-run
```

- The first line, `email … → team … · role …`, becomes one sentence for the user; the role is inferred from the registry card's role title (`role_hints`) — the user may correct it.
- `UNKNOWN_TEAM {json}` (exit 2) — the e-mail is not in the role model: (1) look it up in the provider's directory (`directory_label`) if the user has access, and map the unit to a team card; (2) otherwise one question with the team titles and the role profiles from the JSON; (3) repeat with `--team <slug> --role <profile>`; (4) at the end, a line for the owner to add the person to the registry.
- An umbrella team (a department lead) means the union of its teams: warn that the bundle is large.

## §2 Jira write scope

One question with three answers: "yes — <key from the team card>" · "yes — another key" (typed) · "no — read only". Yes → `--jira-write own` (a key that differs from the card: pass `--team`, and tell the owner to fix the card's `jira` field); no → `--jira-write none`. The answer lands in the team block (`jira_write_scope`), the bundle manifest and the registration; changing it later is the same run with another flag.

## §3 Bundle and proposal

```
python3 "<plugin root>/scripts/provider_bundle.py" --core "<core>" --out "<target>" --email <e-mail> \
        [--in-place] [--team <slug>] [--role <profile>] [--name "Name Surname"] \
        [--existing-context "<copy of local-context.md>"] --jira-write own|none [--no-personal-overlay]
```

Run `--dry-run` first when the user has a context: it already writes the merge report and the proposal, so duplicates and discrepancies show before anything is copied. Use `--no-personal-overlay` when building an archive for others (focus and to-do notes are created on the user's machine instead). `--force` rewrites the user's notes in the bundle — only on request.

What the builder does:
- copies the role-filtered part of the core (shared files, the team's files by the role's layers, the manifest), never the owner's personal layer (`exclude`, `personal_overlay`), registry cards with registry fields only;
- turns links into the owner's personal layer into plain text, adds one note per changed file, prunes the entry note's links to files outside the bundle;
- writes `_System/team-context.md`, copies the context blocks, and prepares `local-context.proposed.md`, `context-merge-report.md` and `provider-registration.proposed.yaml`;
- places blocks: `team` right after the user's own `### Team:` section (or updates it where it is); every other block in one reference section before `## Custom Sections`; Product / Competitors / OKR / CJM / Key Metrics blocks never replace the user's sections (`reference_only` in the report); a block the user moved keeps its place and is updated there;
- adds the provider to `## Obsidian Vaults` → `### Vault Search MCP`;
- is **not** a discrepancy: `Work Email` = the work e-mail; a transliterated name; any alias on the team card;
- refuses (exit 4, nothing written) when a deny pattern or nested markers would reach the proposal.

## §4 Apply

1. One question per discrepancy from the report (keep mine · take the core's · same thing → alias). Typical: e-mail (another account?), product (the user works on another one → add the provider's as one more), Jira key (fix the card through the owner, or the user's context), team (alias, or another card with `--team`).
2. Five lines of what changes. Nothing of the user's text disappears.
3. After "yes":
   ```
   mkdir -p ~/.grow-pm/backups/pre-<provider id>-<YYYY-MM-DD>
   cp ~/.grow-pm/local-context.md ~/.grow-pm/backups/pre-<provider id>-<YYYY-MM-DD>/
   cp "<target>/<plugin_folder>/_System/local-context.proposed.md" ~/.grow-pm/local-context.md
   ```
   Keep the last 5 backups (`references/persistent-storage.md`). Refresh the vault mirror (`{vault}/{plugin_folder}/_System/local-context.md`) when the user keeps one, and compare it with `cmp`.
4. Jira accountId shown as "look up by e-mail" → with the user's consent, look it up through the Atlassian connector (read-only) and write it into the profile.

## §5 Focus note

`focus-interview.md` (skill-local). Five questions, one at a time, each answer written right away.

## §6 Register and finish

1. Copy `provider-registration.proposed.yaml` to `{vault}/{plugin_folder}/_System/providers/<id>.yaml` (no vault: `~/.grow-pm/providers/<id>.yaml`). `paths` lists the provider root as the user's machine sees it; in a hosted session add the mounted spelling too — both are checked by the write boundary. `writable` comes from the manifest's `personal_overlay`.
2. Entry points, a test question through the context-navigator skill, lines for the owner, the `people_resolver` check — as in the skill's Step 6.
3. Project memory, when the host has one: team, role, provider id, target path, core version, date, whether a context existed and what was done with it.

## §7 MCP-only providers

A provider reachable only as a server (no folder on the user's machine):
1. Read its manifest when it serves one (`vault_get_note` on `_System/provider-manifest.yaml`), else ask for the id and title.
2. Show the host configuration entry the user adds themselves — a remote server behind a VPN is usually bridged locally, for example `npx -y mcp-remote@latest <url> --transport http-only`. Never edit the host configuration file.
3. After the user restarts the session, probe with `brain_status` or `vault_list_by_folder("")` (3 s); say plainly when it does not answer (VPN off, server down).
4. Register it (`kind: mcp`, no `paths`) and add the `### Vault Search MCP` bullet through the same backup-and-changelog apply as §4.
