# Context Provider Protocol

**Overview:** how the plugin connects a user's own context to **shared-context providers** — a team's or an organisation's core knowledge (a folder of notes, a bundle copied from it, or an MCP server that indexes it). This document is the contract: the tool surface every provider speaks (`vault/v1`), the manifest that declares a provider, how skills detect, route, cite and refresh providers, and where a skill may write. Read it with `vault-protocol.md` (the user's own vault, levels L0–L2), `local-context-protocol.md` (Step 0h discovers providers) and `data-policy.md` (provider content is internal data).

Since v3.10.0. Nothing here is organisation-specific: a provider's names, folders, labels and note templates come from its manifest, never from this repository.

---

## 1. Terms

| Term | Meaning |
|---|---|
| **Provider** | A source of shared context the user does not own: a core folder, a bundle copied from it, or an MCP server. Identified by an `id` (kebab-case). |
| **Own layer** | Everything the user owns: `local-context.md`, the vault folders of `vault-schema.md` → TYPE_FOLDER_MAP, the knowledge library, person profiles. Skills write only here. |
| **Bundle** | A role-filtered copy of a core folder placed on the user's machine, plus the user's personal overlay notes inside it (§9). |
| **Snapshot / live** | A provider's `mode`. `snapshot` — content as of a date (`synced_at`); `live` — the server reflects its source continuously. |
| **Authority** | Whose word wins by default: `org` (policy, metric definitions, team cards), `team`, or `personal`. Facts *about the user* (e-mail, team, own Jira project) default to the user; org policy is annotated, never overridden. |
| **Managed region** | Text between `<!-- <namespace>:begin id=<id> … -->` and `<!-- <namespace>:end id=<id> -->`, written only by a script or generator (`vault-schema.md` → Generated regions and layers). A provider's context blocks in `local-context.md` are managed regions whose namespace is the provider's. |
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
| `head_label`, `head_role_label` | — | How the team block names the head (`head:` by default) and a member whose only registry role is being the head (`head`). |
| `dashboard_rewrites` | — | `"old => new"` phrases rewritten in the entry note (the owner's wording → the reader's). |
| `personal_notes` | — | Where the user's focus and to-do notes go (`now`, `todo`; `{{NAME}}` allowed); defaults `<plugin_folder>/Now.md` and `<plugin_folder>/TODO — {{NAME}}.md`. |
| `role_enum_map`, `jira_write_labels` | — | Role profile → the plugin's role enum for a new context; the wording of the three write scopes. |

Templates in `templates_dir` (all optional, the plugin ships English defaults): `now.md`, `todo.md`, `person-card.md` (whole notes), `bundle-manifest.md` (the body; the frontmatter the digest reads is always written by the builder), `team-block.md`, `context-section.md`, `context-skeleton.md`. Placeholders are `{{UPPER_CASE}}` names; the defaults show every one.

### 3b. Registration (kept by the user)

When the user connects a provider, the plugin writes one registration file in the user's vault: `{vault}/{plugin_folder}/_System/providers/<id>.yaml` (without a vault: `~/.grow-pm/providers/<id>.yaml`).

```yaml
schema: provider-registration/1
id: zorg-core
title: Zorg shared product core
kind: bundle                        # bundle | folder | mcp
contract: vault/v1
authority: org
mode: snapshot
access: vpn
paths:                              # local roots that are the provider's (read-only)
  - /Users/name/Vault/ZorgCore
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

A user's own index over their vault registers the same way with `kind: mcp`, `authority: personal`, `mode: live`, `access: local`, `index: <path>` and **no `paths`** — the user's vault is never behind the write boundary.

### 3c. Interim declaration in `local-context.md`

Until context records arrive (v3.11.0), providers are also declared in one subsection of `## Obsidian Vaults`, one bullet per provider:

```markdown
### Vault Search MCP
- zorg-brain: scope = own vault (Notes/, ZorgCore/), tools = vault_* + brain_*, index = ~/.zorg-brain/brain.sqlite
- zorg-core: scope = shared core snapshot, mode = snapshot, VPN only, read-only
```

Grammar: `- <id>: <items>`. Items are separated by `,` or `;` outside parentheses. An item is `key = value` (keys `scope`, `tools`, `index`, `mode`, `access`) or a flag (`read-only`, `VPN only` → `access = vpn`, `live`, `snapshot`). Defaults: `mode = live`; `access = local` when `index` names a path, else `open`. A registration file with the same `id` wins over the bullet. The bullet carries no local paths: the write boundary reads registrations only.

---

## 4. Detection and the L2 binding

Step 0h (`local-context-protocol.md`) builds `session.providers` once per session: registrations found under every configured vault (and `~/.grow-pm/providers/`), plus the bullets of §3c, plus any MCP server in the session that exposes `vault_search` and `vault_get_note`. Each entry: `{id, kind, mode, access, paths, index, synced_at, last_index, stale, reachable}`.

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
- **Snapshot age.** `synced_at` older than `stale_after_days` (default 30) → one line: "Working from the <id> snapshot dated <date>."
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

Managed regions — provider blocks in `local-context.md`, generated sections in notes and maps of content — follow one marker grammar and one rule (written only by scripts and generators): `vault-schema.md` → Generated regions and layers. Readers that count or match headings (the SessionStart digest, the bundle builder) ignore text inside managed regions, so a provider block that repeats a `### Team:` or `### Product:` heading never duplicates the user's own.

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

The bundle builder (`scripts/provider_bundle.py`) reads only this layout and the manifest. A new core version is a new `version` in the role model; the user refreshes the bundle and the context blocks with one confirmation (§3b `synced_at`, `source_version`).

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
| `meta` | `key`, `value` — keys `schema` (`1`), `last_index` (ISO 8601), `vault_root`, `snapshot_date` |

Rebuild incrementally by content hash; a deleted file leaves a row with `hash = ''` until the next full rebuild, so broken links stay reportable. The index is always rebuildable from the files and never the only copy of anything.

---

## 11. Hosts

| Capability absent (`host-profiles.md`) | Effect |
|---|---|
| **MCP** | Providers are reached only through their local `paths` (L1 file search); no L2. |
| **SHELL** | No bundle builder and no digest: the connect flow is followed by hand from the provider's manifest, and Step 0h reads registrations as files. |
| **HOOKS** | No host gate: skills apply §7 themselves. |
| **FS** | No registrations and no bundle: a provider can still be used through MCP for the session only. |
