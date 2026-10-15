# Context Provider Protocol

**Overview:** how the plugin connects a user's own context to **shared-context providers** — a team's or an organisation's core knowledge (a folder of notes, a bundle copied from it, or an MCP server that indexes it). This document is the contract: the tool surface every provider speaks (`vault/v1`), the manifest that declares a provider, how skills detect, route, cite and refresh providers, and where a skill may write. Read it with `vault-protocol.md` (the user's own vault, levels L0–L2), `local-context-protocol.md` (Step 0h discovers providers) and `data-policy.md` (provider content is internal data).

Since v3.10.0; the registration `provider-registration/2` (§3b) and the blocks-and-merge contract (§12) since v3.13.0. Nothing here is organisation-specific: a provider's names, folders, labels and note templates come from its manifest, never from this repository.

---

## 1. Terms

| Term | Meaning |
|---|---|
| **Provider** | A source of shared context the user does not own: a core folder, a bundle copied from it, or an MCP server. Identified by an `id` (kebab-case). |
| **Own layer** | Everything the user owns: `local-context.md`, the vault folders of `vault-schema.md` → TYPE_FOLDER_MAP, the knowledge library, person profiles. Skills write only here. |
| **Bundle** | A role-filtered copy of a core folder placed on the user's machine, plus the user's personal overlay notes inside it (§9). |
| **Snapshot / live** | A provider's `mode`. `snapshot` — content as of a date (`synced_at`); `live` — the server reflects its source continuously. |
| **Authority** | Whose word wins by default: `org` (policy, metric definitions, team cards), `team`, or `personal`. Facts *about the user* (e-mail, team, own Jira project) default to the user; org policy is annotated, never overridden. |
| **Managed region** | Text between `<!-- <namespace>:begin id=<id> … -->` and `<!-- <namespace>:end id=<id> -->`, written by a script or generator; a skill or the agent never writes inside one (`vault-schema.md` → Generated regions and layers). A provider's context blocks in `local-context.md` are managed regions whose namespace is the provider's; with a context store a human's edit inside one is kept (§12). |
| **Write boundary** | A provider's local folders are read-only for skills and for the agent; only the paths the provider declares as the user's overlay stay writable (§7). |

---

## 2. Contract `vault/v1`

A provider speaks this tool surface over MCP. A local index built by the plugin or by the user answers the same calls. Tool names are exact; a server may expose more.

| Tool | Parameters | Returns |
|---|---|---|
| `vault_search` | `query` (FTS5 syntax), `tags?` (list), `folder?` (path prefix), `limit` (default 20) | list of `{path, title, snippet, score, tags?}`, best first |
| `vault_get_note` | `path` (exactly as returned by search) | `{path, title, frontmatter, tags, headings, content, outgoing_links: [{target, resolved_path}]}` |
| `vault_get_links` | `path`, `direction`: `in` \| `out` \| `both` | `{path, in: [{path, title}], out: [{path, title, resolved}]}` |
| `vault_graph_context` | `entity` (a path or a title), `depth`: `1` \| `2` | `{nodes: [{path, title, hop}], edges: [{src, dst, kind}]}` |
| `vault_list_by_tag` | `tag` | list of `{path, title}` |
| `vault_list_by_folder` | `folder` (path prefix; `""` = root) | list of `{path, title}` |
| `brain_status` *(optional)* | — | `{last_index, notes, edges, vault_root, snapshot_date?, schema}` |
| `brain_find_entity` *(optional)* | `query` (an issue key, a person, a mission, a feature) | `{hub: {path, title}, related: [{path, title, kind}]}` |
| `brain_recent_changes` *(optional)* | `days` | list of `{path, change: added \| changed \| removed, at}` |

**Recommended aliases.** A server that also serves generic connector clients may expose `search(query)` → `{results: [{id, title, url}]}` and `fetch(id)` → `{id, title, text, url, metadata}`; skills always call the `vault_*` names.

**Query hints (FTS5).** Space-separated words are AND; `OR` and `NOT` are operators; a phrase, and any word with `&`, `-`, `:`, `/` or `.`, goes in double quotes (`"Q&A"`, `"PROJ-1234"`). Paths are returned with their real spelling (spaces, non-Latin letters, `.md`) — copy them verbatim into `vault_get_note`. Entities typed in frontmatter (`type: mission`) are listed with `vault_list_by_folder`, not by tag.

**Usage chain.** `vault_search` → `vault_get_note` on the few notes that matter (frontmatter + `outgoing_links`) → `vault_get_links` / `vault_graph_context` (depth 1–2) when the question is relational → answer. Never paste a whole note into the answer; cite its path.

---

## 3. Manifests

### 3a. Provider manifest (shipped by the provider)

A provider that ships a folder (a core or a bundle) places one manifest in it: `_System/provider-manifest.yaml` at the core root or one folder below it (the provider's own plugin folder). Every path in it is relative to the **core root**. The format is a YAML subset — scalars, lists, one level of nesting — so the plugin reads it without third-party libraries.

```yaml
schema: provider-manifest/1
id: zorg-core                       # kebab-case; also the marker namespace unless `namespace` is set
title: Zorg shared product core
namespace: zorg-core
plugin_folder: Core                 # the provider's own folder inside the core root
contract: vault/v1
authority: org
mode: snapshot
mcp:
  url: https://context.zorg.example/mcp
  transport: mcp-remote --transport http-only
  access: vpn                       # vpn | local | open
bundles_file: Core/_System/access-bundles.json
blocks_file: Core/_System/context-blocks.md
team_card_dir: Core/Teams
people_dir: Core/People
missions_dir: Core/Products/Zorg App/Missions
pages_dir: Wiki/SPACE/Pages
templates_dir: Core/_System/provider-templates
playbook:
  - Core/Playbook/01 Rules.md
  - Core/Playbook/03 Routes.md
routing_hints: Core/Playbook/03 Routes.md
people_resolver: python3 "Tools/people_resolve.py"
personal_overlay:
  - Core/Now.md
  - Core/TODO*
  - Core/_personal/
exclude:
  - Tools/_archive/
deny_patterns:
  - owner-private-marker
role_hints:
  leadership: "\\bCPO\\b|head of"
  analyst: "analyst|data scien"
directory_label: company directory
owner_label: core owner
write_scope:
  jira: own-project
  confluence: read
ttl_days:
  playbook: 30
  teams: 14
  people: 14
  metrics: 7
  missions: 30
  pages: 90
```

| Key | Required | Meaning |
|---|---|---|
| `schema`, `id`, `title`, `contract` | ✅ | Identity and contract version (`vault/v1`). |
| `namespace` | — | Marker namespace of the context blocks; defaults to `id`. |
| `plugin_folder` | ✅ | The provider's folder under the core root (holds `_System/`). |
| `authority`, `mode` | ✅ | §1. |
| `mcp.url`, `mcp.transport`, `mcp.access` | — | How to reach the provider's server. Informational: the plugin never declares a provider server in its own connector list — the user adds it to the host once (`context-connect` gives the exact entry). |
| `bundles_file` | for bundles | The role model: e-mail → team, role → layers, team → files (§9). |
| `blocks_file` | — | Context blocks offered to the user's `local-context.md` (§9). |
| `team_card_dir`, `people_dir`, `missions_dir`, `pages_dir` | — | Where the bundle builder finds team cards, the people registry, missions and exported pages. |
| `templates_dir` | — | The provider's own note templates for the user's overlay (focus note, to-do note, bundle manifest, team block, person card). Absent → the plugin's English defaults. |
| `playbook`, `routing_hints` | — | Rules the agent reads once per session, and the note that routes questions to cards. |
| `people_resolver` | — | A command that resolves meeting participants to registry cards (`emails <list>`, `names <list> --emails <list>`). |
| `personal_overlay` | — | Globs inside the core that belong to the user (stay writable, never overwritten by an update). |
| `exclude`, `deny_patterns` | — | Never copied; a proposed context containing a deny pattern is refused. |
| `role_hints` | — | Role profile → regex over the registry's role title, used when the user's role is not set. |
| `directory_label`, `owner_label` | — | Words the plugin uses in its questions ("not found in the company directory", "ask the core owner"). |
| `write_scope` | — | What the provider allows the user to write outside the core (`own-project` = only the user's own project, through the plugin's write gate). |
| `ttl_days` | — | Freshness per folder class, used when a note from that class is cited (§6). |
| `product_name` | — | The product the core describes; a user context naming only other products raises one question. |
| `dashboard_file` | — | The core's entry note; the bundle builder prunes its links to files outside the bundle. |
| `delink_targets`, `delink_note`, `delink_labels` | — | Link targets (regular expressions) that point into the owner's personal layer: in the bundle such links become plain text, and the note is added once per changed file; a line made only of `delink_labels` words is dropped. |
| `people_private_fields`, `people_card_note` | — | Registry cards are copied with registry fields only: these frontmatter keys and everything after the first `##` section are dropped, and the note is added. |
| `card_fields` | — | Frontmatter keys of a team card that hold the team head and the directory node (`head`, `node` by default). |
| `head_label`, `head_role_label`, `jira_other_label` | — | How the team block names the head (`head:` by default), a member whose only registry role is being the head (`head`), and the team's other Jira keys (`others:`). |
| `dashboard_rewrites` | — | `"old => new"` phrases rewritten in the entry note (the owner's wording → the reader's). |
| `personal_notes` | — | Where the user's focus and to-do notes go (`now`, `todo`; `{{NAME}}` allowed); defaults `<plugin_folder>/Now.md` and `<plugin_folder>/TODO — {{NAME}}.md`. |
| `role_enum_map`, `jira_write_labels` | — | Role profile → the plugin's role enum for a new context; the wording of the three write scopes. |

Templates in `templates_dir` (all optional, the plugin ships English defaults): `now.md`, `todo.md`, `person-card.md` (whole notes), `bundle-manifest.md` (the body; the frontmatter the digest reads is always written by the builder), `team-block.md`, `context-section.md`, `context-skeleton.md`. Placeholders are `{{UPPER_CASE}}` names; the defaults show every one.

### 3b. Registration (kept by the user)

When the user connects a provider, the plugin writes one registration file in the user's vault: `{vault}/{plugin_folder}/_System/providers/<id>.yaml` (without a vault: `~/.grow-pm/providers/<id>.yaml`). The schema is `provider-registration/2` since v3.13.0; a `/1` file is read as before and every key it lacks takes the default below. A registration is a **repository** to `ctx` (`ctx repo list`, `ctx provider …`): the place the provider's context blocks come from (§12). An id met twice keeps the first file; one that does not parse is left out (§4).

```yaml
schema: provider-registration/2
id: zorg-core
title: Zorg shared product core
kind: bundle                        # bundle | folder | mcp
contract: vault/v1
authority: org
rank: 1000                          # a higher rank is the more authoritative; default from authority
mode: snapshot
access: vpn
paths:                              # local roots that are the provider's (read-only)
  - /Users/name/Vault/ZorgCore
core_root: /Users/name/Vault/ZorgCore
namespace: zorg-core                # the marker namespace of the blocks
blocks_file: Core/_System/context-blocks.md
endpoint:                           # an MCP server that serves the blocks file
  url: https://context.zorg.example/mcp
  root: "ZorgCore/"                 # where the core sits on the server, with the trailing slash
  headers_env: ZORG_MCP_HEADERS     # an environment variable holding `Name: value` — never the value itself
products: []                        # product names or ids this repository serves; empty = every product
blocks_source: auto                 # auto | mcp | paths
home_record: ""                     # the record that receives new blocks; empty = the one holding most of them
writable:                           # globs under those roots that stay the user's
  - Core/Now.md
  - Core/TODO*
  - Core/_personal/
index: ""                           # path to a local index answering vault/v1, if any
synced_at: 2026-09-15
source_version: core 0.2, bundle 0.4.0
stale_after_days: 30
skip_blocks: []                     # block ids the user declined; never proposed again
team: team-alpha
role: pm
jira_write: own
status: active                      # active | paused
```

| Key | Default | Meaning |
|---|---|---|
| `schema`, `id` | required | `id` is kebab-case; it names the repository's state (`.state/blocks/<id>.json`, §12.3) and the journal source `repo:<id>`. |
| `title` | the `id` | The title of the record a first block with no home is put in (`provider apply --add`, §12.6); plans, the card and `ctx read` name the repository by its `id`. |
| `kind` | — | `bundle` — a role-filtered copy of a core on this machine; `folder` — the core folder itself (its path is the core); `mcp` — a server only, no `paths`. |
| `contract`, `authority`, `mode`, `access`, `synced_at`, `source_version`, `stale_after_days`, `index`, `paths`, `writable` | as in v1 | Unchanged: §1, §6, §7. `authority` defaults to `org`. |
| `core_root` | `paths[0]` for `bundle` and `folder`; none for `mcp` | The core folder on this machine: where the provider manifest, the team card, the people registry and — without a server — the blocks file are read. `~` is expanded. |
| `namespace` | the `namespace` of the core's manifest when the registration names none and the core folder is here; else the `id` | The marker namespace of the repository's blocks in the user's records. A registration without it, whose manifest says another, earns the line `warning: registration has no namespace — the core's manifest says <ns>; add `namespace: <ns>`` in `ctx repo list`, `repo status` and `provider plan`; the commands work meanwhile because a fetch reads the manifest. The card line and the provenance line of `ctx read` (§12.9) read no manifest: they need the key in the registration. |
| `blocks_file` | the `blocks_file` of the core's manifest | The blocks file of the repository, relative to the core root. On a server its path is `endpoint.root` + `blocks_file` (plain concatenation; `root` may be empty). |
| `rank` | from `authority`: personal 100, team 500, org 1000 (any other authority 500) | A whole number, quoted or not; a malformed one falls back to the authority's. A higher rank wins when two repositories disagree; v3.13.0 stores and shows it (`ctx repo list`), no command decides by it yet. |
| `products` | `[]` — every product | Product names or record ids (`Zorg App`, `product.zorg-app`). `ctx provider plan\|apply --product P` takes the repositories that name P and those that name none. |
| `endpoint.url` | — | The server's URL (http or https). The manifest's `mcp.url` proposes it. |
| `endpoint.root` | `""` | The prefix of the core on the server: set when the server serves the user's whole vault and the core is one folder in it. |
| `endpoint.headers_env` | — | The name of an environment variable that holds the request header as `Name: value`. The registration never holds the value; a variable that is unset or not `Name: value` is named in the error. |
| `blocks_source` | `auto` | Where `ctx` reads the blocks from: `mcp` — the server only; `paths` — the core folder only; `auto` — the server when it answers the handshake, otherwise the folder. |
| `home_record` | — | The id of the record that receives a new block (`ctx provider apply --add`); when it names no record the default rule applies (§12.6). |
| `skip_blocks` | `[]` | Block ids the user declined: never proposed, never planned, never touched (listed by `provider plan --all` with the sign `·`). |
| `team`, `role`, `jira_write` | — | The user's team slug, role and Jira write scope. `team` decides whether the repository's `team` block is built for this user (§12.2). |
| `status` | `active` | `paused` — left out of `provider plan\|apply` without a repository id; an explicit id still works. |

A user's own index over their vault registers the same way with `kind: mcp`, `authority: personal`, `mode: live`, `access: local`, `index: <path>` and **no `paths`** — the user's vault is never behind the write boundary. Such a registration, like a server registered for search only (`skills/context-connect/references/connect-steps.md` §7), names no `blocks_file` and has no core folder to take one from: it is **search-only** and publishes no blocks — `ctx provider plan|apply` without a repository id leave it out with one line `лише пошук: <id>`, and naming it in `provider adopt|plan|apply` is exit 3 (§12.6).

The registration is the user's file. The connect flow writes it once, and a refresh changes only `synced_at`, `source_version` and any v2 key the file lacks, never one that is present (`skills/context-connect/references/connect-steps.md` §6).

### 3c. Interim declaration in `local-context.md`

Until context records arrive (v3.11.0), providers are also declared in one subsection of `## Obsidian Vaults`, one bullet per provider:

```markdown
### Vault Search MCP
- zorg-brain: scope = own vault (Notes/, ZorgCore/), tools = vault_* + brain_*, index = ~/.zorg-brain/brain.sqlite
- zorg-core: scope = shared core snapshot, mode = snapshot, VPN only, read-only
```

Grammar: `- <id>: <items>`. Items are separated by `,` or `;` outside parentheses and double quotes — a value that holds either separator is written in double quotes (`scope = "Core, shared; v2" (bundle team-alpha)`, since v3.10.1). An item is `key = value` (keys `scope`, `tools`, `index`, `mode`, `access`) or a flag (`read-only`, `VPN only` → `access = vpn`, `live`, `snapshot`). Defaults: `mode = live`; `access = local` when `index` names a path, else `open`. A registration file with the same `id` wins over the bullet. The bullet carries no local paths: the write boundary reads registrations only.

---

## 4. Detection and the L2 binding

Step 0h (`local-context-protocol.md`) builds `session.providers` once per session: registrations found under every configured vault (and `~/.grow-pm/providers/`), plus the bullets of §3c, plus any MCP server in the session that exposes `vault_search` and `vault_get_note`. Each entry: `{id, kind, mode, access, paths, index, synced_at, last_index, stale, reachable}`. A registration file that does not parse is left out and named once in the digest — `provider registration unreadable: <file> (<reason>)` (since v3.10.1); say so when the user asks about that provider.

The vault level L2 of `vault-protocol.md` is reached when at least one provider answers the contract:

| Abstract operation | Call |
|---|---|
| test | `brain_status`; a server without it: `vault_list_by_folder("")` |
| full-text search | `vault_search` |
| backlinks | `vault_get_links(direction="in")` |
| graph traversal | `vault_graph_context` |

Each probe has a 3-second budget. A provider that does not answer is marked `reachable: false` for the session; the skill continues at L1 and says so once (§6).

---

## 5. Routing across providers

1. **Order.** The user's own vault (L1 file search) → a local index (`kind: mcp`, `access: local`) → snapshot providers → live remote providers. A question about the user's own work starts in the own layer; a question about the organisation (who owns what, rules, numbers, people) starts at the provider whose `playbook` covers it.
2. **Merge.** Results from several sources are deduplicated by `provider + path` (the same note reached through a local mirror and through the server counts once). When two ranked lists are merged, use reciprocal-rank fusion with k = 60: `score = Σ 1 / (60 + rank)`.
3. **Conflict.** The local state wins over a remote snapshot of the same note (it is newer by construction). An org-authority fact wins over a personal note that contradicts it, unless the fact is about the user; both are shown with their source when they disagree.
4. **Citation.** Every answer built on provider content names the note path and, for a snapshot, its date. A number also carries its period and source (`data-integrity-protocol.md`).

---

## 6. Freshness and offline behaviour

- **Index age.** `brain_status.last_index` older than **36 hours** → one line in Step 0.5: "Index of <id> is from <date>; results may miss recent notes."
- **Snapshot age.** `synced_at` older than `stale_after_days` (default 30) → one line: "Working from the <id> snapshot dated <date>." With a context store (since v3.13.0) the day `ctx provider plan|apply|adopt` last checked the repository counts instead when it is later than `synced_at`; the SessionStart digest reads it from the block state (§12.3) and never goes to the network.
- **Per class.** When a skill cites a provider note whose folder class has a `ttl_days` value, and the note's own date (`updated`, `snapshot`, `generated` in frontmatter) is older than it, the citation carries "(as of <date>)".
- **Unreachable.** A provider that does not answer (VPN off, server down) → one line naming it, then work from its local paths if any, else without it. Never answer from memory in its place.
- **Once.** Each line appears at most once per session.

---

## 7. Write boundary

- Skills never create, edit or delete files under a registered provider's `paths`, except under its `writable` globs.
- New notes go to the own layer by type (`vault-schema.md` → TYPE_FOLDER_MAP). A correction to a provider fact goes to the user's overlay note for that provider (one note per provider in the own layer, or a `writable` path), never into the provider's card. Upstream changes go to the provider's owner.
- **Host gate (since v3.10.0).** On hosts with hooks, a PreToolUse hook on file-writing tools (`scripts/write_gate.py`) asks for confirmation when the target path is under a provider root and outside its `writable` globs; the reason names the provider and the alternative. Paths are compared component by component, so a sibling folder that shares a name prefix is not affected. `/grow-product-manager:setup --write-gate off` turns it off with the Jira/Confluence gate. Without hooks the skill applies the same rule itself.
- Provider scripts (sync jobs, generators) are outside this boundary: they run on the user's machine under the user's own control.

---

## 8. Generated regions

Managed regions — provider blocks in `local-context.md`, generated sections in notes and maps of content — follow one marker grammar and one rule: a skill or the agent never writes inside one (`vault-schema.md` → Generated regions and layers). Generated sections and maps of content belong to their script, which rewrites them; a provider's block is the exception when a context store exists — a human's edit inside it is kept by `ctx provider apply` (§12, `context-protocol.md` §5e). Readers that count or match headings (the SessionStart digest, the bundle builder) ignore text inside managed regions, so a provider block that repeats a `### Team:` or `### Product:` heading never duplicates the user's own.

---

## 9. Provider kit — what a team ships

A team that wants its colleagues' plugins to share its context ships a folder (synced by any means — a git repository, a shared drive, a sync job) with this layout under its plugin folder, plus, optionally, an MCP server answering `vault/v1` over the same notes:

| Path (under the plugin folder) | Contents |
|---|---|
| `_System/provider-manifest.yaml` | §3a. |
| `_System/access-bundles.json` | The role model: `version` (the core version), `emails` (e-mail → team slug), `teams` (slug → `title`, `files`, `modules`, `missions`, `metrics`, `dashboards`, `umbrella`, `union_of`, `department`), `roles` (profile → layers), `layer_prefixes`, `shared`, `always`, `people_role`. |
| `_System/context-blocks.md` | Context blocks for the user's `local-context.md`, each between `<!-- <namespace>:begin id=<block> v=<version> -->` and `<!-- <namespace>:end id=<block> -->`. Blocks are reference material: they never replace the user's own sections. |
| `Teams/`, `People/` | Team cards (`aliases`, owner, modules, missions) and registry cards (`name`, `email`, `team`, `role`) — the identity source for e-mail → team → role. |
| `Playbook/` | Rules for the agent and the routing note (`playbook`, `routing_hints`). |
| `_System/provider-templates/` | Optional note templates (§3a `templates_dir`). |

The bundle builder (`scripts/provider_bundle.py`) reads only this layout and the manifest. A new core version is a new `version` in the role model and a new `v=` on every block (a release stamps it on all of them, whether their words changed or not). The user refreshes the bundle and the context blocks in **one pass**: with a context store, the builder refreshes the bundle and `ctx provider plan <repo>` → one message about the rows that need an answer (`⚠`, `+`, `?`) → `ctx provider apply <repo>` (§12); the rows that need none (`~`, `−`) are applied and said in one line, and the user's own edits inside blocks stay. Without a store the proposal replaces the file after one confirmation (`skills/context-connect/references/connect-steps.md` §4b). Either way the registration's `synced_at` and `source_version` move and nothing else of it does (§3b). A provider that serves its core over MCP must answer `vault_get_note` for the blocks file at `endpoint.root` + `blocks_file`; that is the one note the plugin reads from the server (§12.8).

---

## 10. Index schema v1

A local index that answers `vault/v1` (built by the user, a provider or a later plugin release) is one SQLite file with this schema, so any of them can read another's:

| Table | Columns |
|---|---|
| `notes` | `id INTEGER PRIMARY KEY`, `path TEXT UNIQUE`, `vault TEXT`, `title TEXT`, `type TEXT`, `hash TEXT`, `mtime REAL`, `frontmatter_json TEXT` |
| `notes_fts` | FTS5 over `title`, `headings`, `body`; `tokenize='unicode61 remove_diacritics 2'` |
| `links` | `src_id`, `dst_id` (NULL when unresolved), `kind` (`wikilink` \| `embed` \| `frontmatter:<field>` \| `tag`), `anchor` |
| `aliases` | `entity_id`, `alias`, `alias_norm`, `source` |
| `unresolved` | `src_id`, `target_text` |
| `tags` | `note_id`, `tag` |
| `meta` | `key`, `value` — keys `schema` (`1`), `last_index` (ISO 8601), `vault_root`, `snapshot_date`. Readers also accept `k`, `v` (a legacy spelling seen in the wild, v3.10.1); new indexes write `key`, `value` |

Rebuild incrementally by content hash; a deleted file leaves a row with `hash = ''` until the next full rebuild, so broken links stay reportable. The index is always rebuildable from the files and never the only copy of anything.

---

## 11. Hosts

| Capability absent (`host-profiles.md`) | Effect |
|---|---|
| **MCP** | Providers are reached only through their local `paths` (L1 file search); no L2. |
| **SHELL** | No bundle builder, no digest and no `ctx`: the connect flow is followed by hand from the provider's manifest, Step 0h reads registrations as files, and the blocks are not merged (a blocks file can still be read with the host's `vault_get_note`, §12.8). |
| **HOOKS** | No host gate: skills apply §7 themselves. |
| **FS** | No registrations and no bundle: a provider can still be used through MCP for the session only. |

---

## 12. Blocks and merge (since v3.13.0)

A provider's **context blocks** (§9, `_System/context-blocks.md`) are managed regions in the user's context records. With a context store (`context-protocol.md`), `ctx provider plan|apply|adopt` keeps them current by a three-way comparison of the block in the user's records ("mine"), the block the repository publishes now ("theirs") and the text the two started from (the "base", §12.3). A refresh therefore updates what the user did not touch, keeps what only the user changed, and asks about what both changed. Without a store the connect flow's proposal path applies instead (`skills/context-connect/references/connect-steps.md` §4b). The engine only **reads** a repository — its core folder or its server — and writes only under `~/.grow-pm/` and the storage root (the write allow-list of `context-protocol.md` §3).

### 12.1 Blocks in the records

A block is the text between `<!-- <namespace>:begin id=<block> v=<version> -->` and `<!-- <namespace>:end id=<block> -->` (§1, *Managed region*), anywhere in a record's body: in a section of its own, or inside the `<namespace>:section:begin` … `:end` wrapper the connect flow puts around the reference section (the wrapper is not a block). The block is found in whichever record holds it now, so moving it to another record changes nothing. `v=` is the version the repository stamped on it. Texts are compared after normalising line endings, trailing spaces and trailing blank lines; the begin marker, `v=` included, is part of the text.

Only the namespaces of registered repositories are read. A block with a **structure error** is left out of the plan, listed as `помилка: <block> — <why>` and never touched:

| Error | Meaning |
|---|---|
| `duplicate` | the id is met again, in the same record or in another (every occurrence after the first) |
| `broken marker` | a begin without its end, an end without its begin, an end whose id differs, a marker that does not parse |
| `nested` | a block begins inside another one (both are reported) |

The reading is strict, so a marker typed into your own text counts: the syntax quoted in inline code is read as a marker (a broken one when it has no partner) and a fenced example as a real block. Quote an example with a namespace no repository uses, or without the angle brackets.

### 12.2 What the repository publishes

`ctx` reads the repository's blocks file as `blocks_source` says (§3b): from the server — `vault_get_note` on `endpoint.root` + `blocks_file` (§12.8) — or from the core folder, `core_root`/`blocks_file` (a path that leaves the core is refused). The blocks are the regions of the registration's `namespace` in that file, in file order; an id met twice keeps the first, and `skip_blocks` are dropped. The repository's version is the `v=` most blocks carry. Under `auto`, a server that does not answer, answers an error or sends a bad answer counts as unavailable for this read and the core folder is tried.

**A file that cannot be the repository's blocks is no source.** A file that holds no region of the namespace — empty (a 0-byte save, an iCloud placeholder, a server note whose `content` is `""`), cut before its first block ends, or another repository's file served under the wrong path — reads `the blocks file holds no <ns> block (empty, cut, or another namespace)`; a begin marker of the namespace whose end never follows it reads `the blocks file is cut at block <id>`. From a server both start with `MCP: ` and count as a bad answer, so `auto` tries the core folder. A file that holds **none of the blocks you have a base for** (§12.3), while your context still holds one of them, reads `the blocks file holds none of the N blocks you have a base for (<ids>) — a wrong, stale or cut file, not removals`; your skipped blocks do not count, nor does the `team` block when the core folder builds it (it proves nothing about the file). Each of them makes the repository unavailable (exit 5, nothing written, the plan prints no row), never "the repository removed every block": a genuine removal leaves the other blocks in the file and plans `−` for the one removed. A repository that really retires all its blocks is taken off by hand: remove its regions from your context (the plan then has nothing to remove) and its registration — or set `status: paused` to keep the regions as they are.

**The `team` block** is not read from the file. It is built, as the connect flow builds it, from the core folder alone — the team card, the people registry and the role model — for the `team` and `jira_write` of the registration, whichever source the other blocks came from. It is **not offered** only when that is known: the registration names no team; or the readable role model does not list the team; or the registration names no core folder and the blocks file carries its own `team` region (that region is then the block). A team region you hold is, when the block is not offered, a block the repository removed (§12.5). When a team was due and cannot be built — no core folder in the registration, a core folder that is not on this machine, a provider manifest that is missing, unreadable or unparsable, a role model that is missing, unreadable or has no `teams`, a card or people file that does not arrive, or any file iCloud has evicted (a `.<name>.icloud` placeholder in the team-card, people or templates folder) — the read says `team block: not available (<why>)`; the plan shows the row `·` with that reason and the region you hold is never touched. A block that cannot be built is not "removed".

A repository that cannot be read at all — no answer, an error, a file that does not arrive, a path outside the core, a file that is no source (above) — is **unreachable**: its plan says why and `apply` writes nothing (§12.7).

### 12.3 State and bases

What the store remembers of a repository lives under `<store>/.state/blocks/`. Snapshots keep it (`.state/` is copied with its subfolders), so `ctx undo` brings it back.

- `<repo-id>.json` — `checked` (the time of the last check), `source` (`mcp` or `folder`), `version`, and per block: `base_sha` (the hash of the base text), `bases` (the hashes of the last ten bases, the newest last), `v` (the version at the base), `host` (the record that holds the block), `checked`, and `user_removed` (the date you removed the block, else null).
- `<repo-id>/<sha>.md` — the base texts, named by the SHA-256 of their normalised form. Texts that no block's `bases` refers to any more are pruned together with the history.

The **base** of a block is the repository's text the last time your copy was made equal to it. It is what lets the plan tell who moved: a block whose text is the base, or one of the last ten bases, has not been changed by its holder. A state file that cannot be read or is not valid stops `provider adopt|plan|apply` (exit 3) and is named; it is never reset silently. The commands that only describe go on without it: `repo list` marks the row with `!` and names the state under the table, `repo status` names it on its own line, the card leaves out the version and the day it would have given, and `ctx read` the day.

### 12.4 The first base — `ctx provider adopt`

A context that already holds a repository's blocks (merged by the old proposal path) has no bases. `ctx provider adopt <repo> [--apply]` sets them, block by block, for the blocks of the repository that are in your records. It is a dry run without `--apply`.

| Outcome | When | Effect |
|---|---|---|
| `base` | your text equals the repository's once normalised | the repository's text is the base |
| `edit` | the same known `v=` and your text differs | the repository's text is the base; yours counts as your edit (`✎` in the next plan) |
| `none` | the repository does not offer the block; another version; or a version nobody knows and the texts differ; or a `team` block that cannot be built | no base; the plan shows `?` and asks |
| `has-base` | the state already holds a base | left exactly as it is — re-running never hides an edit (an entry with no base, such as the removal mark of a region you put back, gets one and loses the mark) |

An unknown version with different text is never taken for an edit: a false `edit` would later hide a repository update as `✎`. Blocks the repository offers and your context lacks are listed as the `+` rows of the next plan. `adopt --apply` imports the edits waiting first, as every writing command does — in `local-context.md` or in a record file (a conflict there is exit 2 with `CTX_CONFLICT`, and nothing else is written) — so the adopt's own snapshot holds them and a later `ctx undo --steps N` across the adopt never takes back an edit made before it. Then it writes the block state (`.state/blocks/**`) — after a snapshot (`adopt`) and with one journal line, `provider-adopt` — and refreshes the card's `Repos` line when it changes; it never writes a block's text, and with nothing to adopt it writes no state. The dry run imports nothing: it names the edits waiting, which it does not see.

### 12.5 The plan — what each block is

`ctx provider plan [<repo>] [--product P] [--all]` prints one table per repository and writes nothing (no lock). Its header is `<repo> · джерело: MCP (<host>)|тека · ядро v<version> · база v<version>`; then one line per block — sign, block id, the record that holds it, a note — and for a `⚠` the lines each side changed since the base (`Ядро тепер каже` / `Ви писали` / `Раніше обидва казали`; a side that changed only the `v=` says `(лише версія v<a> → v<b>)`); then the errors (§12.1); then `Питань: N · зміниться записів: M`. Everything a server sent is stripped of control characters and clipped before it is printed.

**Structural changes — which side has the block.** The first line that matches decides (a block that neither side has gets no row):

| Yours | The repository's | Base | Sign |
|---|---|---|---|
| present | present, equal once normalised | any | `=` |
| absent | present | none | `+` — a new block |
| absent | present | held, or your removal mark | `✂` — you removed it |
| present | absent | none | `?` |
| present | absent | yours is the base, or one of the last ten | `−` — the repository removed a block you never changed |
| present | absent | yours is none of them | `⚠` — the repository removed a block you edited |
| present | present, different | none | `?` |
| present | present, different | yours is the base itself, the repository's an older base | `=` — the source lags behind yours (a mirror not updated yet): note `джерело позаду вашої бази (v<theirs> < v<yours>)` |
| present | present, different | yours is the base (or older) | `~` — only the repository moved |
| present | present, different | the repository's is the base (or older) | `✎` — only you moved |
| present | present, different | neither is | `⚠` — both moved |

**Signs, and what `apply` does with each.**

| Sign | Meaning | `apply` | Asks |
|---|---|---|---|
| `=` | no change — or a source behind your base | nothing in the records; the base becomes the repository's text if it was not — except behind your base: then the base stays, and nothing is written but the time of the check | no |
| `~` | the repository changed a block you did not touch | the region becomes the repository's text; so does the base | no |
| `✎` | you changed a block the repository did not | your region stays, so does the base | no |
| `−` | the repository removed a block you did not edit | the region is removed (its text stays in the snapshot) and the state entry with it | no |
| `✂` | you removed a block | stays removed; the state marks the date (`user_removed`) and the block is never offered again | no |
| `⚠` | both changed | waits for `--choose <block>=theirs\|mine\|both` | yes |
| `?` | no base: nothing says who changed | waits for `--choose <block>=theirs\|mine\|both` | yes |
| `+` | the repository has a block your context lacks | waits for `--add <block>` | yes |
| `·` | not checked: a block of `skip_blocks` (shown only with `--all`, note `пропущено`), or a `team` block that cannot be built (the reason is the note) | untouched | no |

**The answers.** `theirs` — the region becomes the repository's text. `mine` — your region stays. `both` — one region with the repository's markers (its `v=` too) holding the repository's text under `<!-- ctx:both theirs -->` and yours under `<!-- ctx:both mine -->`. In all three the base becomes the repository's text, so the next plan does not ask again: after `theirs` it says `=`, after `mine` or `both` it reads your text as your edit (`✎`). A block the **repository removed** (a `⚠` or a `?` whose repository side is missing) is different: `theirs` removes the region; `mine` **detaches** it — the markers go, the text stays in place as your own, and the state entry is dropped so the block is never asked about again; `both` is refused (exit 3). A user's edit of the `v=` inside a marker is compared as content, not refused.

### 12.6 Apply

`ctx provider apply [<repo>] [--product P] [--choose BLOCK=theirs|mine|both …] [--add BLOCK …]` is one pass per repository. It acts on what needs no answer and leaves the rest waiting; an answer for a block that needs none is dropped and listed (`не потрібне`); an unknown block in `--choose` or `--add` stops before anything is written (exit 3).

**Scope.** With `<repo>` that repository, paused or not (a search-only registration is exit 3). Without it, the repositories that serve the product `--product` names (matched among the product records as `ctx read` matches it) and those that name none, else all — paused ones left out with one line `призупинено: <id>`, and search-only registrations (§3b: no `blocks_file`, no core folder) with one line `лише пошук: <id>`; neither is unreachable. `--choose` and `--add` need `<repo>` when more than one repository is in scope.

**One repository's pass, in this order:** the plan is made on the records as they are now → a snapshot (`provider-apply`) → the new base texts → the host records (verified today, source `repo:<id>`) → the state → the base texts nobody refers to are pruned → one journal line `{op: provider-apply, source: repo:<id>, from_v, to_v, ids: the records written, decisions, pending, snapshot}` → the compiled copies. A block's text goes into a record only when the repository's text is one well-formed region of that block; otherwise the block is reported as an error and left alone. A new block (`--add`) goes at the end of `home_record`, or of the record that holds most of the repository's blocks (inside its `<namespace>:section` wrapper when it has one), or the custom record already titled as the repository, or — with none of them — a new custom record `## <title>` at the end of the context.

**A pass that changes nothing** except the time of the check (and the service fields `checked` and `host`) writes the state file alone: no snapshot, no journal line, no record; the output is the header and `без змін`.

**Several repositories.** Every repository in scope is read first, and its file checked against your bases (§12.2); if any is unreachable or its file is no source, the run stops before the lock (exit 5) and nothing is written (`plan` still prints the others). Then, under the lock, the edits waiting in `local-context.md` are imported first, as for every writing command (a conflict there is exit 2 with `CTX_CONFLICT`, and nothing else is written), and the repositories are applied one after another. Each takes **its own snapshot and journal line**, so `ctx undo` takes back the last repository's pass only; `ctx undo --steps N` goes back N passes.

**A crash.** The order above is the recovery plan. A crash among the base texts leaves orphan texts, which are harmless and pruned later. A crash after the record writes and before the state leaves the records written with the old bases: run `ctx provider plan` again — it reads the records as they are, and at worst a block that was not re-based is asked about again. A crash between the record writes and the journal line leaves a snapshot on disk with no journal line: `ctx undo` follows the journal, so it steps back to the operation before it.

### 12.7 Commands, exit codes, results

| Command | Does | Writes |
|---|---|---|
| `ctx repo list` | the registered repositories: kind, products, rank, access, and from the block state (§12.3) the number of blocks you hold a base for, their base version and the day of the last check — `—` before `provider adopt`, or without a store; `!` when the state cannot be read (one line under the table names it, exit 0) | nothing; local files only, no lock |
| `ctx repo status [<id>]` | is each repository reachable (a server answers the handshake within 3 s; a core folder is there), and its version on the source against the base. The version on the source is the one read from the blocks file now; when the repository answers and the file could not be read it is `—`, with the reason on a `  blocks file: <reason>` line — the registration's own `source_version` is never shown in its place | nothing; the only `repo` command that goes to the network |
| `ctx provider adopt <repo> [--apply]` | the first bases (§12.4) | with `--apply`: first the import of the edits waiting (as every writing command), then a snapshot, the block state, its base texts, one journal line and the card's `Repos` line when it changes; never a block's text |
| `ctx provider plan [<repo>] [--product P] [--all]` | the plan (§12.5) | nothing |
| `ctx provider apply [<repo>] …` | one pass per repository (§12.6) | first the import of the edits waiting; then, per repository that changed something, a snapshot, the base texts, the host records, the block state, one journal line, the compiled copies — and the card's `Repos` line when it changes; a pass that changed nothing writes the block state alone (the time of the check) |

**Exit codes of `ctx provider …`:**

| Code | Meaning |
|---|---|
| 0 | done, or nothing to change |
| 2 | `apply` only: decisions are waiting (the rest was applied); also, for `apply` and `adopt --apply` as for every writing command, a conflict among the edits waiting to be imported (`CTX_CONFLICT`, nothing written). `plan` never exits 2: it exits 0, or 5 when a repository is unavailable |
| 3 | a bad call or something not found: an unknown repository or block, a search-only registration named (§3b), `both` for a removed block, no store, an unreadable state or a record missing on disk |
| 4 | refused: only refused blocks remain (a broken marker, a repository text that is not one well-formed region), a store inside a provider's folder, a busy lock |
| 5 | a repository is unreachable, or its blocks file is no source (§12.2: empty, cut, foreign, or none of your based blocks); nothing is written |

`repo status` and `repo list` exit 0 also when a repository is unreachable (they inform; they are not gates).

**`CTX_RESULT`** (the last stdout line; `--json` is accepted and changes nothing, the line is always there):

- `repo list` — `{repos: [the registrations, normalised, each with `namespace_warning`, `blocks` (the blocks with a base that you have not removed, or null when there is none or no store), `base_version` (or null), `checked` (the ISO time of the last check, or null) and, only when the state cannot be read, `state_error`], unreadable: [{file, reason}]}`; `repo status` — `{repos: [{id, kind, status, url, reachable, reason, source_version, registration_version, base_version, namespace_warning, fetch_error?, state_error?}], unreadable}` (`url` without credentials, query or fragment; `source_version` is what the blocks file carries now, null when it was not read; `registration_version` is the registration's own `source_version`; `fetch_error` is there only when the repository answers and its blocks could not be read; `reason` and `fetch_error` are one line of at most 300 characters).
- `provider plan <repo>` — the plan itself: `{repo, source, source_label, version, base_version, rows: [{block, sign, host, source, note, diff?, behind?}], questions, changes, errors, namespace_warning}` (`behind: true` on a `=` whose source lags behind your base). Without `<repo>`: `{repos: [plan …], paused: [ids], search_only: [ids], questions, changes}` — `questions` and `changes` are the sums of the plans'. A repository that cannot be read, or whose file is no source, appears as `{repo, error}` (and the exit is 5).
- `provider apply <repo>` — the plan's keys plus `applied` `{block: sign}`, `decisions` `{block: sign or "sign answer"}`, `pending` `[block]`, `ignored`, `changed`, `written` `[record ids]`, `snapshot`, `compiled`; its `errors` also hold the blocks refused at the write. Without `<repo>`: `{repos: [that …], paused, search_only, questions: the number of blocks waiting, changes: the number of records written}`. Unreachable: `{unreachable: [{repo, error}], paused, search_only, written: []}` (with `repo` and `error` when a repository was named).
- `provider adopt` — `{repo, blocks: {block: outcome}, why, new, problems, written, snapshot, pending, imported}` (`pending` counts the edits waiting that a dry run does not see — 0 after `--apply`, which imports them first; `imported` the record ids that import changed or added); an unreachable repository: `{repo, written: false, error}`.

### 12.8 The MCP client and its allow-list

`scripts/ctx_mcp.py` is a small client on the standard library (Streamable HTTP: a JSON-RPC 2.0 POST, answered as JSON or as an event stream; the session id goes back in `Mcp-Session-Id`). It speaks to a repository's server and nothing else:

- **Tools.** Only `vault_get_note`, `vault_list_by_folder`, `vault_search`, `brain_status` and `brain_recent_changes` — read tools of the contract table (§2); any other name is refused before a request is made, and the contract has no write tool. A fetch calls `vault_get_note` once, for the blocks file. The validator keeps the allow-list inside the §2 table (check 17).
- **Time.** A handshake probe of 3 seconds, one attempt; a call of 30 seconds, tried again twice on a network failure (not on an HTTP status, a JSON-RPC error or `isError`).
- **No redirect is followed** (a header meant for one host never travels to another), only `http` and `https` are spoken, and a response is capped at 32 MiB.
- **No secret in a message.** An error never carries a header value or the URL (it may hold credentials) — and nothing of them is chained to it; a URL that is shown has no credentials, query or fragment. The header a server wants comes from the environment variable `endpoint.headers_env` names, as `Name: value`, and the value is never stored.
- **Where the network is used.** Only `ctx repo status` and `ctx provider adopt|plan|apply`. `ctx repo list`, `ctx read`, `status`, `card` and the SessionStart hook read local files: the hook never goes to the network.

### 12.9 Reading blocks

- **`ctx read`** looks for a field or a subsection in your own text first — outside the managed regions — and only then inside the blocks. Every block's text is preceded by `> [<repo-id> · v<version> · станом на <date>]`: the repository whose `namespace` the block carries (the namespace itself when nobody registered it), the block's `v=`, and the day the store last checked that block (left out when it never did). A record whose file and record disagree is headed `⚠ конфлікт: файл і запис різняться — ctx sync`.
- **The context card** gets one line about the registered repositories that have blocks in the records, one entry each, joined by `; `: `- **Repos:** <id>: <N> блок/блоки/блоків · v<version> · перевірено <date>; <id>: …` (the version most blocks have a base at; a version or a date nobody knows is left out). `provider apply` and `adopt --apply` refresh it, though no record changed. A team's member count is taken from the `team` block when your own team section has no table.
- **The SessionStart digest** dates a repository on its `providers:` line by the store's last check when that is later than `synced_at` (§6). The dates are read after the store's facts, with half a second of their own: a block state that does not arrive (iCloud) costs the dates — the line falls back to `synced_at` — never the digest's `context:` line.

### 12.10 Hosts

`ctx` needs SHELL; the network is used only as §12.8 says. On a host without SHELL the blocks file can be read with the host's own `vault_get_note` (when MCP is present), but nothing merges it: the user's edits stay in `local-context.md`, and the next `ctx` run on a host with a shell does the comparison.
