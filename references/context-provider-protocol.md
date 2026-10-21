# Context Provider Protocol

**Overview:** how the plugin connects a user's own context to **shared-context providers** — a team's or an organisation's core knowledge (a folder of notes, a bundle copied from it, or an MCP server that indexes it). This document is the contract: the tool surface every provider speaks (`vault/v1`), the manifest that declares a provider, how skills detect, route, cite and refresh providers, and where a skill may write. Read it with `vault-protocol.md` (the user's own vault, levels L0–L2), `local-context-protocol.md` (Step 0h discovers providers) and `data-policy.md` (provider content is internal data).

Since v3.10.0; the registration `provider-registration/2` (§3b) and the blocks-and-merge contract (§12) since v3.13.0; the `sync` key and the daily core sync (§12.11) since v3.14.0. Nothing here is organisation-specific: a provider's names, folders, labels and note templates come from its manifest, never from this repository.

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

**Query hints (FTS5).** Space-separated words are AND; `OR` and `NOT` are operators; a phrase, and any word with `&`, `-`, `:`, `/` or `.`, goes in double quotes (`"Q&A"`, `"PROJ-1234"`). Paths are returned with their real spelling (spaces, non-Latin letters, `.md`) — copy them verbatim into `vault_get_note`. Entities typed in frontmatter (`type: mission`) are listed with `vault_list_by_folder`, not by tag. Since v3.16.0 `ctx search` sends one expression per variant of a request — every word in double quotes, with `*` after a word of four letters or more, joined by `OR` (`"кошик"* OR "мобільний"*`) — because plain words would be read as "all of them" (`search-protocol.md` §12).

**What `vault_search` returns — the shapes a client reads (since v3.16.0).** The contract says a list, one object per hit, best first. Servers built on the Python MCP SDK send that list in more than one way, so the plugin's client (`McpClient.call_list`, §12.8) takes the first of these that fits: `structuredContent` — a list, or an object with a `results` list or a `result` list (how a server built on the Python MCP SDK wraps a list it returns; `{"result": []}` is zero hits); one text item holding such a list or object as JSON, or one hit (a JSON object with no `results` key); several text items, each one hit as a JSON object. An empty `content` with no `structuredContent` and no `isError` is zero hits, not a failure. Anything else — plain text such as "No results found.", a non-empty list with no object in it — is no answer (`<id> не відповів — без нього`). A hit without a usable `path` is skipped. Besides `path`, `title`, `snippet` and `score`, the search reads a hit's `type`, its date (`date`, `updated` or `modified`) and, for the age of its class (§6), `updated`, `snapshot` or `generated`, when the server gives them. The search does not read `status` or `sensitive` from a hit, so in the list a server's note is never marked `застаріле` by its status or `sensitive` — only by the age of its class. `ctx search --get` reads them from the note's frontmatter (`vault_get_note`'s `frontmatter`, else the frontmatter its `content` starts with) and puts ` · sensitive`, ` · застаріле` and the note's type at the end of its provenance line (`search-protocol.md` §4); until that read, `search-protocol.md` §6 treats a server's note under a people folder as sensitive.

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
sync: off                           # off | daily — the daily core sync (§12.11); off unless you say daily
status: active                      # active | paused
```

| Key | Default | Meaning |
|---|---|---|
| `schema`, `id` | required | `id` is kebab-case, at most 64 characters (since v3.14.0); it names the repository's state (`.state/blocks/<id>.json`, §12.3) and the journal source `repo:<id>`. |
| `title` | the `id` | The title of the record a first block with no home is put in (`provider apply --add`, §12.6); plans, the card and `ctx read` name the repository by its `id`. |
| `kind` | — | `bundle` — a role-filtered copy of a core on this machine; `folder` — the core folder itself (its path is the core); `mcp` — a server only, no `paths`. |
| `contract`, `authority`, `mode`, `access`, `synced_at`, `source_version`, `stale_after_days`, `index`, `paths`, `writable` | as in v1 | Unchanged: §1, §6, §7. `authority` defaults to `org`. |
| `core_root` | `paths[0]` for `bundle` and `folder`; none for `mcp` | The core folder on this machine: where the provider manifest, the team card, the people registry and — without a server — the blocks file are read. `~` is expanded. |
| `namespace` | the `namespace` of the core's manifest when the registration names none and the core folder is here; else the `id` | The marker namespace of the repository's blocks in the user's records. A registration without it, whose manifest says another, earns the line `warning: registration has no namespace — the core's manifest says <ns>; add `namespace: <ns>`` in `ctx repo list`, `repo status` and `provider plan`; the commands work meanwhile because a fetch reads the manifest. The card line and the provenance line of `ctx read` (§12.9) read no manifest: they need the key in the registration. |
| `blocks_file` | the `blocks_file` of the core's manifest | The blocks file of the repository, relative to the core root. On a server its path is `endpoint.root` + `blocks_file` (plain concatenation; `root` may be empty). |
| `rank` | from `authority`: personal 100, team 500, org 1000 (any other authority 500) | A whole number, quoted or not, of at most nine digits; a longer one falls back to the authority's, and so does a malformed one. A higher rank wins when two repositories disagree: v3.13.0 stores and shows it (`ctx repo list`); since v3.15.0 `ctx read` and `ctx explain` decide a slot by it (`context-protocol.md` §5f). |
| `products` | `[]` — every product | Product names or record ids (`Zorg App`, `product.zorg-app`). `ctx provider plan\|apply --product P` takes the repositories that name P and those that name none. |
| `endpoint.url` | — | The server's URL (http or https). The manifest's `mcp.url` proposes it. |
| `endpoint.root` | `""` | The prefix of the core on the server: set when the server serves the user's whole vault and the core is one folder in it. |
| `endpoint.headers_env` | — | The name of an environment variable that holds the request header as `Name: value`. The registration never holds the value; a variable that is unset or not `Name: value` is named in the error, and so is one whose name is not a header token (RFC 7230) or is `Host`, `Content-Length`, `Transfer-Encoding` or `Connection` — such a header is never sent. |
| `blocks_source` | `auto` | Where `ctx` reads the blocks from: `mcp` — the server only; `paths` — the core folder only; `auto` — the server when it answers the handshake, otherwise the folder. |
| `home_record` | — | The id of the record that receives a new block (`ctx provider apply --add`); when it names no record the default rule applies (§12.6). |
| `skip_blocks` | `[]` | Block ids the user declined: never proposed, never planned, never touched (listed by `provider plan --all` with the sign `·`). Since v3.15.0 `ctx explain` also lists them (`Вимкнені блоки`), and `context-connect` may take an id out of the list — only on the user's explicit yes for that block (below). |
| `team`, `role`, `jira_write` | — | The user's team slug, role and Jira write scope. `team` decides whether the repository's `team` block is built for this user (§12.2). |
| `status` | `active` | `paused` — left out of `provider plan\|apply` without a repository id; an explicit id still works; the daily sync never touches it. |
| `sync` | `off` | `daily` (since v3.14.0) — `ctx provider sync` brings the repository up to date once a day without asking (§12.11). Any other value and a missing key read `off`; the schema number does not matter — a `provider-registration/1` file that says `sync: daily` is synced. It is the one switch for writing without a question, so it is set per repository by an explicit yes — `context-connect` asks once (`skills/context-connect/references/connect-steps.md` §6) — and the plugin never adds it by itself. |

A user's own index over their vault registers the same way with `kind: mcp`, `authority: personal`, `mode: live`, `access: local`, `index: <path>` and **no `paths`** — the user's vault is never behind the write boundary. Such a registration, like a server registered for search only (`skills/context-connect/references/connect-steps.md` §7), names no `blocks_file` and has no core folder to take one from: it is **search-only** and publishes no blocks — `ctx provider plan|apply` without a repository id leave it out with one line `лише пошук: <id>`, and naming it in `provider adopt|plan|apply` is exit 3 (§12.6).

The registration is the user's file. The connect flow writes it once, and a refresh changes only `synced_at`, `source_version` and any v2 key the file lacks, never one that is present (`skills/context-connect/references/connect-steps.md` §6). One key is the exception, and only by your own word: `sync`. `context-connect` writes `sync: daily` (or `sync: off`) after the question of its Step 6 and when you ask it to turn the daily sync on or off, and never otherwise. The proposal a refresh builds carries no `sync`, so the refresh's own merge neither adds nor changes it; the question of Step 6 item 2 may still add it, on your yes.

**A second, narrower exception since v3.15.0: `skip_blocks`.** When a block you switched off now has a slot (`context-protocol.md` §5f), `context-connect` offers to bring it back (one message on a refresh), and only on your explicit yes for that block does it take that one id out of the list — touching nothing else of the file — and write the binding with `ctx slot bind`. It never removes an id without that yes, and it adds none: an id is added as before, from the blocks you declined at the first connection or by you.

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

1. **Order.** The user's own vault (L1 file search) → a local index (`kind: mcp`, `access: local`) → snapshot providers → live remote providers. A question about the user's own work starts in the own layer; a question about the organisation (who owns what, rules, numbers, people) starts at the provider whose `playbook` covers it. Since v3.16.0 Step 0.5 asks them all at once through `ctx search` (`search-protocol.md`): the plugin's own section index (the plugin folder of every vault and the local core folder of every registration — `core_root`, else its `paths`), every local index (a registration's `index:` or an `index = …` item of §3c, opened read only), and the server of a repository whose core folder is not on disk (or every server, with `--sources mcp`). A repository whose folder is on disk is not asked over MCP: its notes are already in the section index, and the local copy is primary.
2. **Merge.** Every variant of a request, in every source, is a ranked list of its own; reciprocal-rank fusion makes one score of them, k = 60: `score = Σ w / (60 + rank)`, with `w = 1` for a list and `w = 0.5` for a **glossary list** — the other names of a thing a variant names (the approved terms of the team glossary, `_org.yaml` and the product's file under `~/.grow-pm/knowledge-library/glossary/`; `skills/knowledge-library/references/glossary-workflows.md`). The priors then multiply the score: the skill's artifact types (`search_types` of `references/context-manifest.yaml`) × 1.2 — a weight, never a filter; the same product × 1.1, another product × 0.7; a hub × 0.5; an outdated note × 0.5 (§6). A remembered choice of the user weighs × 1.5 (`search-protocol.md` §10).
3. **Identity — no duplicates.** One candidate per note, at most two of its sections inside it. The keys, in this order:
   1. **the same file** — the same path from the root of its vault (NFC); a server's path maps through `endpoint.root` → `core_root`. One candidate, the local copy, with the list of the sources that found it. **"The local state wins over a remote snapshot of the same note"** holds for this key, exactly as before (it is newer by construction);
   2. **the same Confluence page on disk twice** — the same `confluence_id` (from the frontmatter, else the number of six or more digits in brackets before `.md`) in two local files: the newer by the page's own date stays, the other is its `двійник <шлях>`;
   3. **the same content** — the same hash: one stays, the other is its `двійник`;
   4. **a twin of your layer and the core** (new since v3.16.0) — the same title once normalised, and one note links to the other (a wiki-link or a `core_page` field): two different notes, so "local wins" does not apply — the one with more text stays (a generated hub of an epic in your layer is short), the other is its `двійник`. When they say different things about one fact, that is a conflict to show (`search-protocol.md` §7), not a duplicate to hide;
   5. **versions** (new since v3.16.0) — the same version key in one folder (a title with a version, draft or revision mark — `v3`, `draft`, `rev5` — without the mark and the date): the newer stays with `є старіші версії: N`; a version older than one the index holds is marked `старіша версія <шлях>`. Titles that differ only by a date are a series, not versions, and are never folded.

   A candidate that stays keeps the best score of those it stands for, and their `sensitive` mark.
4. **Conflict.** An org-authority fact wins over a personal note that contradicts it, unless the fact is about the user; both are shown with their source when they disagree.
5. **Citation.** Every answer built on provider content names the note path and, for a snapshot, its date. A number also carries its period and source (`data-integrity-protocol.md`). What Step 0.5 takes is cited `(<джерело>, <дата>)` (`search-protocol.md` §5).

---

## 6. Freshness and offline behaviour

- **Index age.** `brain_status.last_index` older than **36 hours** → one line in Step 0.5: "Index of <id> is from <date>; results may miss recent notes." The plugin's own section index is refreshed by every `ctx search` (30 s at most); when the time runs out the search goes on with what is there and says `індекс оновлюється: N файлів ще не переглянуто` (since v3.16.0).
- **Snapshot age.** `synced_at` older than `stale_after_days` (default 30) → one line: "Working from the <id> snapshot dated <date>." With a context store (since v3.13.0) the day `ctx provider plan|apply|adopt` last checked the repository counts instead when it is later than `synced_at`; the SessionStart digest reads it from the block state (§12.3) and never goes to the network. Since v3.16.0 the age of a snapshot does not devalue its notes in a search: their candidates carry `знімок від <день>`, they may be taken, and taking one is a doubt (`search-protocol.md` §7).
- **Per class.** When a skill cites a provider note whose folder class has a `ttl_days` value, and the note's own date (`updated`, `snapshot`, `generated` in frontmatter) is older than it, the citation carries "(as of <date>)". Since v3.16.0 the same rule marks a search candidate `застаріле` (× 0.5, never taken silently) — only for a class whose folder the core's manifest names, and only from those three dates: a note with none of them is not outdated by age. A `status` of `outdated`, `archived`, `deprecated`, `former` or `superseded` marks it the same way, whatever its date. A decision about one note, never about the whole repository.
- **Unreachable.** A provider that does not answer (VPN off, server down) → one line naming it, then work from its local paths if any, else without it. Never answer from memory in its place. In `ctx search` the line is `<id> не відповів — без нього`, and a local index of another shape says `індекс <id> має незнайому схему — без нього`; the search goes on with the other sources. It is a doubt only for a source with no copy on disk (`search-protocol.md` §7).
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

The bundle builder (`scripts/provider_bundle.py`) reads only this layout and the manifest. A new core version is a new `version` in the role model and a new `v=` on every block (a release stamps it on all of them, whether their words changed or not). The user refreshes the bundle and the context blocks in **one pass**: with a context store, the builder refreshes the bundle and `ctx provider plan <repo>` → one message about the rows that need an answer (`⚠`, `+`, `?`) → `ctx provider apply <repo>` (§12); the rows that need none (`~`, `−`) are applied and said in one line, and the user's own edits inside blocks stay. Without a store the proposal replaces the file after one confirmation (`skills/context-connect/references/connect-steps.md` §4b). Either way the registration's `synced_at` and `source_version` move and nothing else of it does (§3b). A provider that serves its core over MCP must answer `vault_get_note` for the blocks file at `endpoint.root` + `blocks_file`; that is the one note the plugin reads from the server (§12.8). A user who switched on the daily sync (§12.11) gets the blocks without that pass; the bundle's files, and the registration's `synced_at` and `source_version`, still change only when the builder runs.

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

`notes_fts` is joined to `notes` by `notes_fts.rowid = notes.id` (written out since v3.16.0: the schema always meant it, and a reader needs it). Rebuild incrementally by content hash; a deleted file leaves a row with `hash = ''` until the next full rebuild, so broken links stay reportable. The index is always rebuildable from the files and never the only copy of anything.

**Two shapes are read (since v3.16.0).** `ctx search` opens a registered local index read only (`mode=ro`, 5 s to open, 20 s for its queries) in either shape: this schema, and the shape seen in the wild — `notes_fts` with a `path` column of its own (and `notes` joined by `path` when it has one). Title, type, date, status and product come from `notes` when it has them, else from `notes_fts`, the rest from the frontmatter JSON. An index of any other shape is left out with one line, `індекс <id> має незнайому схему — без нього`. Its query is the variant's words as written, each in double quotes (with `*` after a word of four letters or more), joined by `OR`. A hit the section index would leave out — under the context store, a blocks file, `_System/providers/` — is dropped, from a server's answer as well.

**The plugin's own section index** (since v3.16.0, schema `search-index/1`) is a different file and is not this schema: `<home>/.grow-pm/index/sections.sqlite`, with `index.json` (its state — the session digest reads only this) and `index.lock`, outside every vault. One row per section — a heading of level 1–3 and the text under it — of every `.md` file under the plugin folder of each vault and the local core folder of each registration; not the context store, the blocks files, `_System/providers/`, `.obsidian/`, `.trash/`, `_backup*` folders, files over 2 000 000 bytes, or a file iCloud has not downloaded. Its FTS5 columns — `title`, `heading`, `tags`, `aliases`, `body` — are stemmed by the same light stemmer as a request (`unicode61 remove_diacritics 2`) and ranked by bm25 with the weights 10, 6, 4, 4, 1. It is a cache: no snapshot, no journal line and no `undo`; deleting the folder is safe and `ctx index rebuild` builds it again; a file of another schema, or one SQLite cannot read, is set aside and built again. `ctx index status` refreshes it and prints its counts.

---

## 11. Hosts

| Capability absent (`host-profiles.md`) | Effect |
|---|---|
| **MCP** | Providers are reached only through their local `paths` (L1 file search); no L2. |
| **SHELL** | No bundle builder, no digest and no `ctx`: the connect flow is followed by hand from the provider's manifest, Step 0h reads registrations as files, and the blocks are not merged (a blocks file can still be read with the host's `vault_get_note`, §12.8). |
| **HOOKS** | No host gate: skills apply §7 themselves. |
| **FS** | No registrations and no bundle: a provider can still be used through MCP for the session only. |

**Search (since v3.16.0, `search-protocol.md` §12).** With SHELL, Step 0.5 is `ctx search` over every source of §5 — the rating is done by the session's model, so no subagent is needed. SHELL without a context store: the same search, without the memory of choices. FS without SHELL: the request's words looked for in the plugin folder and the core folders, file by file. MCP only: `vault_search` of each reachable provider, one call per variant, merged by reciprocal-rank fusion — no section index.

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

**A file that cannot be the repository's blocks is no source.** A file that holds no region of the namespace — empty (a 0-byte save, an iCloud placeholder, a server note whose `content` is `""`), cut before its first block ends, or another repository's file served under the wrong path — reads `the blocks file holds no <ns> block (empty, cut, or another namespace)`; a begin marker of the namespace whose end never follows it reads `the blocks file is cut at block <id>`. From a server both start with `MCP: ` and count as a bad answer, so `auto` tries the core folder. A file that holds **none of the blocks you have a base for** (§12.3), while your context still holds one of them, reads `the blocks file holds none of the N blocks you have a base for (<ids>) — a wrong, stale or cut file, not removals; if the repository really retired them, remove those regions by hand (context-provider-protocol.md §12.2)`, where N and `<ids>` count only the blocks you still hold (one you removed yourself is not among them; a long list is cut); your skipped blocks do not count, nor does the `team` block when the core folder builds it (it proves nothing about the file). Each of them makes the repository unavailable (exit 5, nothing written, the plan prints no row), never "the repository removed every block": a genuine removal leaves the other blocks in the file and plans `−` for the one removed. A repository that really retires all its blocks is taken off by hand: remove its regions from your context (the plan then has nothing to remove) and its registration — or set `status: paused` to keep the regions as they are. The same holds when the repository retired every block you hold but still publishes others: that looks exactly like a lost source (exit 5), so remove those regions by hand — they are the ones the message names.

**The `team` block** is not read from the file. It is built, as the connect flow builds it, from the core folder alone — the team card, the people registry and the role model — for the `team` and `jira_write` of the registration, whichever source the other blocks came from. It is **not offered** only when that is known: the registration names no team; or the readable role model does not list the team; or the registration names no core folder and the blocks file carries its own `team` region (that region is then the block). A team region you hold is, when the block is not offered, a block the repository removed (§12.5). When a team was due and cannot be built — no core folder in the registration, a core folder that is not on this machine, a provider manifest that is missing, unreadable or unparsable, a role model that is missing, unreadable or has no `teams`, a card or people file that does not arrive, or any file iCloud has evicted (a `.<name>.icloud` placeholder in the team-card, people or templates folder), and since v3.14.0 a team card or people folder that is not there and a team or person card that cannot be read (`team card not found`, `team card cannot be read`, `people folder not found`, `a person card cannot be read: <name>`, with ` — not downloaded yet` after a card that did not arrive in time — the connect flow would build a block without them, and the daily sync would apply it unattended) — the read says `team block: not available (<why>)`; the plan shows the row `·` with that reason and the region you hold is never touched. A block that cannot be built is not "removed". Since v3.15.0 the plugin binds the block itself, because it builds it by its own template: the `Members` subsection answers the slot `team.members` (`team#Members`, `context-protocol.md` §5f), and nothing else of the block is bound — not its `jira_project_key` line and not `jira_team_field`: the `jira_project_key` line can carry more than a product's own `Jira Project Key` (the team's other projects, when the team has more than one), so its value can differ whatever the label, and a bound line would then put a «також» into every skill that reads the key, and `jira_team_field` is a team's name, not a Jira Team ID. The template does not change, so no `~` appears on a sync.

**A core rule — `policy=rule`** (since v3.14.0). A publisher marks a block that every holder is to follow as published by putting the word `policy=rule` among the attributes of its begin marker: `<!-- <namespace>:begin id=<block> v=<version> policy=rule -->` (after `id=`, before or after `v=`). It must be a whole word there — `policy=rules` or `xpolicy=rule` is no mark — and words inside the region never count. The mark is read from the repository's text, never from yours. `ctx provider plan` and `apply` show it: the row carries `rule: true` and its note ends with ` (правило ядра)` (§12.5). A manual `apply` still asks about a `⚠` of a rule — you answer it yourself; it is the daily sync (`ctx provider sync`) that takes the repository's text of a rule where it would otherwise keep yours. The mark is part of the text, so adding or removing it changes the block like any other edit of the publisher's (a `~` for a holder who did not edit it).

**A slot — `slot=`** (since v3.15.0). A publisher says which slot of the catalogue (`references/context-slots.yaml`) a block answers by putting `slot=<slot>[,<slot>…]` among the attributes of its begin marker: `<!-- <namespace>:begin id=<block> v=<version> slot=<slot> -->` (after `id=`, before or after `v=`; several slots are separated by a comma, each `<record>.<name>`). Like `policy=rule` it must be a whole word there — `xslot=` is no attribute — words inside the region never count, and it is read from the repository's text, never from yours: from the block's base in your store (§12.3), so a block with no base has no `slot=`. The begin marker is part of the text, so adding or removing `slot=` changes the block like any other edit of the publisher's (a `~` for a holder who did not edit it) and is read from the base the next pass writes. A holder's own binding of the block (`ctx slot bind`) wins over the attribute for the whole block; a slot the catalogue lacks does nothing and `ctx validate` names it — neither the attribute nor a binding of yours to such a slot sets the next source aside (`context-protocol.md` §5f). What a skill gets from a bound block, from which record and for whom: `context-protocol.md` §5f.

**For the owner of a core** (since v3.14.0). To make a block a rule, put `policy=rule` into its begin marker in the blocks file you publish: the daily sync of every holder who switched it on then takes your text where it would otherwise keep theirs (§12.11), and a text a holder rejected by undoing a pass stays rejected until you change the block. The `team` block is another matter: it is built from the core folder on the holder's machine — `_System/provider-manifest.yaml`, `access-bundles.json`, the team card and the people registry — and this version never reads those through a server, so a holder who has only your server gets `·` (not available) for it — unless your blocks note carries a `team` region itself, which is then the block — and never a block built from half a source. For the block ever to follow your server, the server must serve the manifest and `access-bundles.json`, and many serve notes only and refuse `.yaml`/`.json` files. Everything else a holder needs is the one blocks note, which a server answering `vault_get_note` already serves. To make a block answer a slot of the catalogue, put `slot=<slot>` into its begin marker (above): holders then see the block in that slot, with the slot's `about`, with no binding of their own.

A repository that cannot be read at all — no answer, an error, a file that does not arrive, a path outside the core, a file that is no source (above) — is **unreachable**: its plan says why and `apply` writes nothing (§12.7).

### 12.3 State and bases

What the store remembers of a repository lives under `<store>/.state/blocks/`. Snapshots keep it (`.state/` is copied with its subfolders), so `ctx undo` brings it back.

- `<repo-id>.json` — `checked` (the time of the last check), `source` (`mcp` or `folder`), `version`, and per block: `base_sha` (the hash of the base text), `bases` (the hashes of the last ten bases, the newest last), `v` (the version at the base), `host` (the record that holds the block), `checked`, and `user_removed` (the date you removed the block, else null). Since v3.14.0 it may also hold `rejected` — `{block: [hash | "removed", …]}`: the repository texts you rejected by undoing a pass of the daily sync, at most ten per block, the oldest dropped first (`"removed"` stands for a removal). A plan row that offers one of them (`~`, `+`, `−`, `⚠`, `?`) carries `rejected: true` and the note `відкинуто вами — не застосовується, доки ядро не змінить блок`, its sign unchanged, and counts in neither `Питань` nor `зміниться записів`; neither the sync nor `ctx provider apply` takes it again unless you take it yourself (§12.6). A new text in the block (a new hash) is no longer rejected. A `rejected` that is not an object of lists of strings makes the state invalid. Since v3.14.0 the daily sync also keeps in it `sync_attempt` — the time of its last pass, which decides when the next may come — and `sync_result` — that pass's result (§12.11, its keys listed there), which the digest's `repos:` line shows; a state without them is a repository the sync has not touched, and a `sync_result` written before `held_behind` existed (the v3.14.0 final review) is read as holding none.
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

`ctx provider plan [<repo>] [--product P] [--all]` prints one table per repository and writes nothing (no lock). Its header is `<repo> · джерело: MCP (<host>)|тека · ядро v<version> · база v<version>`; then one line per block — sign, block id, the record that holds it, a note — and for a `⚠` the lines each side changed since the base (`Ядро тепер каже` / `Ви писали` / `Раніше обидва казали`; a side that changed only the `v=` says `(лише версія v<a> → v<b>)`; since v3.14.0 each side is compared on its first 2000 lines, and a longer one adds `(порівняно перші 2000 рядків)`); then the errors (§12.1); then `Питань: N · зміниться записів: M`. Everything a server sent is stripped of control characters and clipped before it is printed.

**Structural changes — which side has the block.** The first line that matches decides (a block that neither side has gets no row):

| Yours | The repository's | Base | Sign |
|---|---|---|---|
| present | present, equal once normalised | any | `=` |
| absent | present | none | `+` — a new block |
| absent | present | held, or your removal mark | `✂` — you removed it |
| present | absent | none | `?` |
| present | absent, and the source's copy lags (since v3.14.0): a block it carries is at an older `v=` than your base of it, and none at a newer one (skipped blocks and a team block built from the core folder do not count) | yours is the base, or one of the last ten | `=` — a copy made before the block came (a mirror not updated yet): note `джерело позаду вашої бази`, never `−`. The plan is marked `lagging`, and the daily sync holds every row of it that would change a block (`~ + − ⚠ ?`): nothing is taken from such a copy |
| present | absent, the copy lags (as above) | yours is none of them | `✎` — your edit stays, with the same note |
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
| `✎` | you changed a block the repository did not | your region stays, so does the base — unless you answer `--choose <block>=theirs` (since v3.14.0): then the region becomes the repository's text, and so does the base | no |
| `−` | the repository removed a block you did not edit | the region is removed (its text stays in the snapshot) and the state entry with it | no |
| `✂` | you removed a block | stays removed; the state marks the date (`user_removed`) and the block is never offered again | no |
| `⚠` | both changed | waits for `--choose <block>=theirs\|mine\|both` | yes |
| `?` | no base: nothing says who changed | waits for `--choose <block>=theirs\|mine\|both` | yes |
| `+` | the repository has a block your context lacks | waits for `--add <block>` | yes |
| `·` | not checked: a block of `skip_blocks` (shown only with `--all`, note `пропущено`), or a `team` block that cannot be built (the reason is the note) | untouched | no |

**The answers.** `theirs` — the region becomes the repository's text. `mine` — your region stays. `both` — one region with the repository's markers (its `v=` too) holding the repository's text under `<!-- ctx:both theirs -->` and yours under `<!-- ctx:both mine -->`. In all three the base becomes the repository's text, so the next plan does not ask again: after `theirs` it says `=`, after `mine` or `both` it reads your text as your edit (`✎`). A block the **repository removed** (a `⚠` or a `?` whose repository side is missing) is different: `theirs` removes the region; `mine` **detaches** it — the markers go, the text stays in place as your own, and the state entry is dropped so the block is never asked about again; `both` is refused (exit 3). A user's edit of the `v=` inside a marker is compared as content, not refused. Since v3.14.0 `theirs` is also an answer for a `✎`: the block you edited takes the repository's text after all (its region and its base), the decision is recorded as `✎ theirs`, and the next plan says `=`; `mine` and `both` for a `✎` stay `не потрібне`.

**Marks on a row** (since v3.14.0). A block the repository holds as a rule (§12.2) ends its note with ` (правило ядра)` and carries `rule: true`. A row whose offer you rejected by undoing a sync pass (§12.3) has the note `відкинуто вами — не застосовується, доки ядро не змінить блок` and `rejected: true`, and `apply` holds it (§12.6). Neither mark changes the sign; a rule changes nothing in `apply`.

### 12.6 Apply

`ctx provider apply [<repo>] [--product P] [--choose BLOCK=theirs|mine|both [BLOCK=… …]] [--add BLOCK [BLOCK …]]` is one pass per repository. One `--choose` takes several answers and one `--add` several blocks (repeating the flag works too), so the repository goes first: a word with `=` in its place stops with `'<word>' looks like an answer, not a repository — put the repository first` (exit 3), and a repository named after the answers is read as one of them (`--choose takes BLOCK=…`, exit 3). It acts on what needs no answer and leaves the rest waiting; an answer for a block that needs none is dropped and listed (`не потрібне`), and so is one for a block whose markers are broken (`не застосовано`, `ignored` holds `"!"` for it); an unknown block in `--choose` or `--add` stops before anything is written (exit 3). `--choose <block>=theirs` on a `✎` is an answer since v3.14.0, not `не потрібне`: it takes the repository's text for a block only you changed (§12.5) — the way to take one block the daily sync left as yours without undoing its whole pass.

**A text you rejected** (since v3.14.0) — one a sync pass took and you undid (§12.3, `rejected`) — is not repeated: `ctx provider apply` does not take it again either. Its block is held: listed in `held`, untouched but for the time of the check, shown as `утримано: <sign> <block> — цей прохід його не чіпав · взяти текст ядра: --choose <block>=theirs`, neither awaited nor counted as a change (exit 0 when nothing else waits). You take it explicitly: `--choose <block>=theirs` on a rejected row of any sign that offers (`~` and `−` too, where `theirs` would otherwise be `не потрібне`; for a `+` it is its `--add`), `--add` of a rejected `+`, or any answer to a rejected `⚠` or `?`. The text (or the removal) is then applied as the sign says, the decision reads `<sign> theirs` (a `+` reads `+`, as any `--add`), and the base moves, so the next plan has no mark. `mine` or `both` on a rejected `~`, `−` or `+` takes nothing: the block stays held.

**Scope.** With `<repo>` that repository, paused or not (a search-only registration is exit 3). Without it, the repositories that serve the product `--product` names (matched among the product records as `ctx read` matches it) and those that name none, else all — paused ones left out with one line `призупинено: <id>`, and search-only registrations (§3b: no `blocks_file`, no core folder) with one line `лише пошук: <id>`; neither is unreachable. `--choose` and `--add` need `<repo>` when more than one repository is in scope.

**One repository's pass, in this order:** the plan is made on the records as they are now → a snapshot (`provider-apply`) → the new base texts → the host records (verified today, source `repo:<id>`) → the state → the base texts nobody refers to are pruned → one journal line `{op: provider-apply, source: repo:<id>, from_v, to_v, ids: the records written, decisions, pending, taken, snapshot}` → the compiled copies. A block's text goes into a record only when the repository's text is one well-formed region of that block; otherwise the block is reported as an error and left alone. A new block (`--add`) goes at the end of `home_record`, or of the record that holds most of the repository's blocks (inside its `<namespace>:section` wrapper when it has one), or the custom record already titled as the repository, or — with none of them — a new custom record `## <title>` at the end of the context. `taken` (since v3.14.0) names what the pass took from the repository: `{block: hash}` for every block whose repository text went into your records — `~`, `+`, `theirs`, `both` (the hash of the repository's text, normalised as for the bases, not of the joined region) — and `{block: "removed"}` for every block it removed (`−`, `theirs` for a block the repository removed); a block kept as yours (`mine`, `✎`) is not in it. Undoing a pass of the daily sync reads it (§12.3, `rejected`).

**The daily sync's pass** (since v3.14.0) is this same pass with two more inputs. `op` labels it: the snapshot and the journal line say `provider-sync` instead of `provider-apply`. `hold` names the blocks it must not touch, whatever their sign: each is listed in the result's `held` `{block: sign}` — not in `pending`, `ignored`, `applied` or the journal's decisions — and only the time its entry was checked moves; a block in `hold` the plan does not have is a programming error and nothing is written. `ctx provider apply` labels its pass `provider-apply` and holds only the texts you rejected (above); a text that has held blocks shows each as `утримано: <sign> <block> — цей прохід його не чіпав`.

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
| `ctx provider sync [<repo>] [--if-due] [--now ISO]` | the daily sync (§12.11) | under the lock, the import of the edits waiting, then per repository a pass like `apply`'s (a snapshot and a journal line only when it writes a record), the block state with the pass's result, a part of the day's report in `sync/`, the card's `Repos` line; `--if-due` first reads the block states alone — no lock, no network |

**Exit codes of `ctx provider …`:**

| Code | Meaning |
|---|---|
| 0 | done, or nothing to change |
| 2 | `apply` only: decisions are waiting (the rest was applied); also, for `apply` and `adopt --apply` as for every writing command, a conflict among the edits waiting to be imported (`CTX_CONFLICT`, nothing written). `plan` never exits 2: it exits 0, or 5 when a repository is unavailable |
| 3 | a bad call or something not found: an unknown repository or block, a search-only registration named (§3b), `both` for a removed block, no store, an unreadable state or a record missing on disk |
| 4 | refused: only refused blocks remain (a broken marker, a repository text that is not one well-formed region), a store inside a provider's folder, a busy lock |
| 5 | a repository is unreachable, or its blocks file is no source (§12.2: empty, cut, foreign, or none of your based blocks); nothing is written |

`repo status` and `repo list` exit 0 also when a repository is unreachable (they inform; they are not gates). So does `provider sync`: it exits 0 whatever its repositories did — unreachable, broken, timed out, held — because a sync must never stop a skill; only a bad call is exit 3 (§12.11).

**`CTX_RESULT`** (the last stdout line; `--json` is accepted and changes nothing, the line is always there):

- `repo list` — `{repos: [the registrations, normalised, each with `namespace_warning`, `blocks` (the blocks with a base that you have not removed, or null when there is none or no store), `base_version` (or null), `checked` (the ISO time of the last check, or null) and, only when the state cannot be read, `state_error`], unreadable: [{file, reason}]}`; `repo status` — `{repos: [{id, kind, status, url, reachable, reason, source_version, registration_version, base_version, namespace_warning, fetch_error?, state_error?}], unreadable}` (`url` without credentials, query or fragment; `source_version` is what the blocks file carries now, null when it was not read; `registration_version` is the registration's own `source_version`; `fetch_error` is there only when the repository answers and its blocks could not be read; `reason` and `fetch_error` are one line of at most 300 characters).
- `provider plan <repo>` — the plan itself: `{repo, source, source_label, version, base_version, rows: [{block, sign, host, source, note, diff?, behind?, rejected?, rule?}], questions, changes, errors, namespace_warning}` (`behind: true` on a `=` whose source lags behind your base; `rejected: true` on a row that offers a text you rejected, §12.3; `rule: true` on a block the repository holds as a rule, §12.2). Without `<repo>`: `{repos: [plan …], paused: [ids], search_only: [ids], questions, changes}` — `questions` and `changes` are the sums of the plans'. A repository that cannot be read, or whose file is no source, appears as `{repo, error}` (and the exit is 5).
- `provider apply <repo>` — the plan's keys plus `applied` `{block: sign}`, `decisions` `{block: sign or "sign answer"}` (`"✎ theirs"` for a `✎` you took the repository's text for), `pending` `[block]`, `ignored` `{block: sign, or "!" for a block with broken markers}`, `held` `{block: sign}` (the blocks that offer a text you rejected and this run did not take, §12.6; `{}` when there are none), `changed`, `written` `[record ids]`, `snapshot`, `compiled`; its `errors` also hold the blocks refused at the write. Without `<repo>`: `{repos: [that …], paused, search_only, questions: the number of blocks waiting, changes: the number of records written}`. Unreachable: `{unreachable: [{repo, error}], paused, search_only, written: []}` (with `repo` and `error` when a repository was named).
- `provider sync` — `{synced: [ids of the repositories the run passed over], results: [{repo, at, outcome, updated, added, removed, kept_yours, took_rule, awaiting, held, held_behind, rejected, reason, report, snapshot}], skipped?}` — the same objects the block state keeps as `sync_result` (§12.3); `results` is absent when nothing was due before the lock, `skipped` (`busy`, `lock: <why>`, `guard: <why>`) is there when the lock or the guard stopped the run. See §12.11.
- `provider adopt` — `{repo, blocks: {block: outcome}, why, new, problems, written, snapshot, pending, imported}` (`pending` counts the edits waiting that a dry run does not see — 0 after `--apply`, which imports them first; `imported` the record ids that import changed or added); an unreachable repository: `{repo, written: false, error}`.

### 12.8 The MCP client and its allow-list

`scripts/ctx_mcp.py` is a small client on the standard library (Streamable HTTP: a JSON-RPC 2.0 POST, answered as JSON or as an event stream; the session id goes back in `Mcp-Session-Id`). It speaks to a repository's server and nothing else:

- **Tools.** Only `vault_get_note`, `vault_list_by_folder`, `vault_search`, `brain_status` and `brain_recent_changes` — read tools of the contract table (§2); any other name is refused before a request is made — by the call and again at the transport every message passes — and the contract has no write tool. A fetch calls `vault_get_note` once, for the blocks file. The validator keeps the allow-list inside the §2 table (check 17).
- **Two ways to read an answer (since v3.16.0).** `call` reads one JSON object — the first text item — and refuses anything else: what `vault_get_note` returns. `call_list` reads a list of results — what `vault_search` returns — in the shapes of §2 (`structuredContent` as a list, `{results}` or `{result}`; one text item with a list, `{results}` or one hit; several text items with one hit each; an empty `content` is zero hits); no shape that fits is an error that carries nothing of the answer. Both keep the same allow-list, handshake, retries, deadline and errors. `ctx search` gives one server 20 s for all its lists and the whole search 60 s.
- **Time.** A handshake of 3 seconds a step (`initialize`, then the notification, each with its own 3 seconds); a probe is one attempt; a call of 30 seconds, tried again twice on a network failure (not on an HTTP status, a JSON-RPC error or `isError`). Given a deadline (`fetch(…, deadline=)`), every request gets at most what is left of it, a retry starts only when it leaves room, none is made once it has passed (`deadline reached`), and the core folder is read within the same remainder.
- **The answer is the message with the request's id** — a message with another id, or with none, is no answer.
- **No redirect is followed** (a header meant for one host never travels to another), only `http` and `https` are spoken, and a response is capped at 32 MiB.
- **No secret in a message.** An error never carries a header value or the URL (it may hold credentials) — and nothing of them is chained to it; a URL that is shown has no credentials, query or fragment. The header a server wants comes from the environment variable `endpoint.headers_env` names, as `Name: value`, and the value is never stored; a header whose name would steer the request itself (`Host`, `Content-Length`, `Transfer-Encoding`, `Connection`) or is not a token is never sent.
- **Where the network is used.** Only `ctx repo status` and `ctx provider adopt|plan|apply|sync`, and since v3.16.0 `ctx search` (and its `--get` and `eval`) for the server of a repository whose core folder is not on disk (`vault_search`, `vault_get_note`). `ctx repo list`, `ctx read`, `ctx explain` (since v3.15.0), `ctx slot …`, `ctx validate`, `ctx index …`, `status`, `card` and the SessionStart hook read local files: the hook never goes to the network, and `read` and `explain` also take no lock and write nothing.

### 12.9 Reading blocks

- **`ctx read`** looks for a field or a subsection in your own text first — outside the managed regions — and only then inside the blocks. Every block's text is preceded by `> [<repo-id> · v<version> · станом на <date>]`: the repository whose `namespace` the block carries (the namespace itself when nobody registered it), the block's `v=`, and the day the store last checked that block (left out when it never did). A record whose file and record disagree is headed `⚠ конфлікт: файл і запис різняться — ctx sync`.
- **The provenance line since v3.15.0** (`context-protocol.md` §5f). A name that has a slot is resolved by the cascade, not by the order above. The line of a block gets these additions after the day, each after ` · ` and in this order: `слот <slot> — <about>` (on every block bound to a slot: in a slot, the slot shown; in a record read whole — through `read_by` too — one for each slot the block answers) · `за назвою, без прив'язки` (a block found by its heading: neither you nor its publisher bound it, and the plugin's `team#Members` gives this slot no text) · `з твоїми правками` (the region differs from every base the store keeps) · `правило ядра` (the base says `policy=rule`) · `перевага: <mine|repo:<id>|all>` (your preference for the slot shaped the answer). Your own text is headed `> [твоє · <id запису>]` only when the slot shows more than one candidate or has a «також» line, a note or a divergence; alone it has no line. Under a rule the user's text follows the line `твоя примітка до правила`; under a winner whose text others contradict, one line `також: <repo або «твоє»> каже інакше — ctx explain <slot>` for each of them; a divergence between repositories of the same rank is `⚠ розбіжність між репозиторіями — вирішити: ctx slot decide <slot> <repo>`.
- **The context card** gets one line about the registered repositories that have blocks in the records, one entry each, joined by `; `: `- **Repos:** <id>: <N> блок/блоки/блоків · v<version> · перевірено <date>; <id>: …` (the version most blocks have a base at; a version or a date nobody knows is left out). `provider apply` and `adopt --apply` refresh it, though no record changed. A team's member count is taken from the `team` block when your own team section has no table (under a `Members` heading — or, since v3.14.1, `Team Members`).
- **The SessionStart digest** dates a repository on its `providers:` line by the store's last check when that is later than `synced_at` (§6). The dates are read after the store's facts, with half a second of their own: a block state that does not arrive (iCloud) costs the dates — the line falls back to `synced_at` — never the digest's `context:` line.

### 12.10 Hosts

`ctx` needs SHELL; the network is used only as §12.8 says. On a host without SHELL the blocks file can be read with the host's own `vault_get_note` (when MCP is present), but nothing merges it: the user's edits stay in `local-context.md`, and the next `ctx` run on a host with a shell does the comparison.

`ctx provider sync` (§12.11) needs SHELL and the network as well, and runs where Step 0c of `local-context-protocol.md` runs. A host without hooks (Codex CLI) shows no `repos:` line in a digest it does not have, so the skill's closing sentence is what tells the user there; a Cowork sandbox usually has no VPN, so a repository behind one ends `unreachable` and is skipped.

### 12.11 The daily sync (since v3.14.0)

A repository whose registration says `sync: daily` (§3b) is brought up to date once a day with no one at the keyboard. `ctx provider sync [REPO] [--if-due] [--now ISO]` is `ctx provider apply` (§12.6) with every answer given in advance by one fixed cascade, plus the safeguards an unattended write needs. It is the one place the plugin writes into your context without asking, so it is on only where you said yes (`context-connect`, Step 6), every pass that changes something can be taken back (`ctx undo`) and is explained in a report. It changes the context blocks only: never the bundle's files, never the registration, and nothing of a repository that does not say `sync: daily` (a search-only registration has no blocks to sync).

**When.** In the first skill of the day: Step 0c of every skill runs `python3 "<plugin root>/scripts/ctx.py" provider sync --if-due` before `ctx read`, and the digest's `Skills:` line says the same. Not the SessionStart hook (it never goes to the network) and not a timer of the operating system (a `python3` started by `launchd` has no access to `~/Documents`, where a vault often lives, and a session has). A day with no skill is a day with no sync — and with no read of the context either.

- **Due** — all of: `sync: daily`; not `status: paused`; no successful check yet, or the last one (`checked` in the block state, §12.3) is 24 h old or more; and the last attempt (`sync_attempt`) is absent, an hour old or more, or no later than that check. A pass that read the source is a successful check — `changed`, `no-changes`, `held`, `broken` — and moves `checked`; a pass that did not (`unreachable`, `timeout`, `import-conflict`, `error`) records only `sync_attempt`, so the next try is an hour away and not at every skill start. A manual `provider apply` or `adopt --apply` moves `checked` too. A `checked` or `sync_attempt` more than a day ahead of now is another Mac's clock: unknown, so the repository is due.
- **`--if-due`** reads the block states alone — no lock, no network, 2 s for all of them — and when no repository is due prints only the `CTX_RESULT` line and writes nothing, not even the digest's summary. Without it, `ctx provider sync [REPO]` syncs now every repository that says `sync: daily` (or REPO). A REPO that is unknown, says no `sync: daily`, or is paused is exit 3: the boundary of this kind of write is the key in the registration, not the command. `--now ISO` acts as if it were that time (the tests use it).

**The time.** The whole run is 20 s, every repository together, and the last 1 s of it is kept for writing the results down. Each fetch runs in a helper thread joined against what is left, so a lookup that hangs (VPN off) or a server that trickles costs the budget and never the skill; no fetch, plan or write begins with less than 3 s of the work time left, and a write, once begun, has at least those 3 s for its reads — a half-written pass would leave records without their journal line; a repository stopped by the floor is `timeout`, nothing written. The card that a write compiles, and the card's `Repos` line refreshed at the end (only with at least 1 s left), read the registrations within the same budget — a registration not read in time leaves the card's `Repos` line as it was — never on a fresh 6 s of their own. The sync never waits for a lock: held by another session, it does nothing at once (`skipped: busy`), and `--if-due` checks the due state again under the lock, so two sessions starting together make one pass and one report, never two. A registration still downloading — the provider boundary cannot be checked, which refuses the other writing commands with exit 4 (`context-protocol.md` §3) — is `skipped: guard: <why>`; a lock that cannot be taken at all is `skipped: lock: <why>`. The exit code is 0 whatever the repositories did, and a skill goes on after any of it.

**One pass, in order.** The lock → the import of the edits waiting in `local-context.md` (as every writing command; one that needs a decision makes every repository `import-conflict`, and nothing is written) → reports older than 90 days into the trash → for each repository: its block state is read (one that cannot be read stops the pass before the network), the source is fetched (§12.2), a source that is no source is `broken`, then the plan (§12.5) → the cascade → `apply` labelled `provider-sync` (§12.6: a snapshot, the records, the state, one journal line `provider-sync`, the compile) → its part of the report → the pass's result into the block state (`sync_result`, `sync_attempt`, and `checked` for a successful check no apply wrote) → the card's `Repos` line. One repository's failure never stops the next; manual `plan` and `apply` keep their v3.13 behaviour (one unreachable repository is exit 5 and nothing is written), because a person is there to decide.

**What it decides** — by the signs of §12.5; `rule` is a block marked `policy=rule` in the repository's text (§12.2):

| Sign | The sync does | The base becomes |
|---|---|---|
| `=` | nothing | as `apply` does |
| `~` | takes the repository's text | the repository's text |
| `✎` | keeps yours | unchanged |
| `⚠` | keeps yours (`mine`) — unless the block is a rule: then the repository's text (`theirs`); yours stays in the snapshot and in the report | the repository's text, so tomorrow's sync does not ask again |
| `?` | nothing: your text stays, the base does not move and the block does not freeze; the digest says `awaits a decision` and the report names it once — unless the block is a rule: then the repository's text | unchanged (a rule: the repository's text) |
| `?` of a block the repository no longer offers | nothing, as above | unchanged |
| `+` | adds the block, as `apply --add` | the repository's text |
| `−` | removes the block (its text stays in the snapshot) — but see the first safeguard | the state entry goes |
| `⚠` of a block the repository removed (you edited it) | your text stays as your own, the markers removed, as `--choose <block>=mine` does | the entry is dropped |
| `✂` | nothing; never offered again | unchanged |
| `·` | nothing | unchanged |

Two kinds of row are decided before the table is read — they are held whatever their sign: a text you rejected by undoing a pass (`rejected`, §12.3; a rule too) and, when the source lags behind your bases (`lagging`, §12.5), every row that would change a block (`~ + − ⚠ ?`) — a copy older than what you hold is never a reason to take a block back or remove one. Such a pass names the blocks in `held_behind`, and a `?` held so that is no rule still counts in `awaiting`: the question is yours whatever the copy. A rule changes only a `⚠` or `?`: it never overrides a rejected text.

**Safeguards.**
1. **Mass removal.** When the repository removes more than one block you hold in one pass (a `−`, or a `⚠`/`?` of a removed block), the sync removes none of them and applies the rest of the signs as usual. Outcome `held`: the report has a section «Не застосовано: ядро прибрало N блоків» with `ctx provider plan <repo>` to look and `ctx provider apply <repo>` to remove them by hand, and the digest a mark. A single removal goes through. This is what stops a blocks file cut exactly at a block boundary.
2. **A broken source.** A blocks file that is empty, cut or another repository's, or that holds none of the blocks you have a base for, is no source (§12.2): outcome `broken`, nothing written, the reason in the report and the digest. It counts as a successful check, so the next try is a day away — hourly retries against the same file would only cost the start of a skill. A server that does not answer is not that: it is `unreachable`.
3. **Edits that cannot be imported.** A conflict among the edits waiting in `local-context.md` is outcome `import-conflict`: the sync writes nothing, and the report and the digest say `ctx sync` first. A store failure at the import (a record missing or still downloading) is outcome `error` (`store: <why>`).
4. **Idempotence.** A pass that changes nothing writes only the time of the check into the state: no snapshot, no journal line, no report. A safeguard that goes off again with the same blocks and the same reason as the last pass adds nothing to the report (`held`, `broken`, `import-conflict`, `error`; the digest keeps the mark); nor does a lagging source with the same blocks held behind as the last pass; a new `?` waiting is named once.

**Outcomes** (`outcome` in the result and in `sync_result`):

| Outcome | Means | Next try |
|---|---|---|
| `changed` | the pass wrote: a snapshot and a journal line | a day |
| `no-changes` | only the time of the check moved (also a pass that held everything because the source lags: `held_behind` names the blocks, the digest marks it) | a day |
| `held` | more than one removal held | a day |
| `broken` | the source is no source | a day |
| `unreachable` | no answer, or a server error | an hour |
| `timeout` | the budget ran out, the client gave up at its deadline, or too little was left | an hour |
| `import-conflict` | edits waiting need a decision | an hour |
| `error` | something failed unexpectedly (the store, a bug); the message is the reason | an hour |

`sync_result` holds `at`, `outcome`, `updated`, `added`, `removed` (counts), `kept_yours`, `took_rule`, `awaiting`, `held`, `held_behind` (the blocks a source behind your bases offered and the pass held), `rejected` (lists of blocks), `reason`, `report` (the path from the storage root, or null) and `snapshot`; `CTX_RESULT` carries the same objects (§12.7).

**The sentence.** For each repository whose pass updated, added or removed a block, or kept your text in a conflict, the command prints one line: `Ядро оновило <N> <блок|блоки|блоків> у <repo>, конфліктів <K> (лишено твоє) — звіт: <path>` — `<N>` the blocks updated, added and removed, `<K>` the conflicts decided for your text, the report clause only when there is a report. A skill repeats it at the end of its answer (Step 0c); nothing is asked in the middle of work.

**The report.** `{storage_root}/_System/context/sync/YYYY-MM-DD.md`, in the vault where Obsidian shows it (`context-protocol.md` §1); the day's later passes append a part to the same file. A pass writes a part when it was `changed`, `held`, `broken`, an `import-conflict` or an `error` (not a repeat, safeguard 4), when a new `?` began to wait, or when its source lags behind your bases with a new set of blocks held — the part «Джерело позаду вашої бази» names them, once for the same blocks held behind; `unreachable`, `timeout` and a plain `no-changes` write nothing. The file has the frontmatter `type: system`, `kind: context-sync`, `date`, `repos`, the title `# Синк контексту — YYYY-MM-DD`, and per repository a part headed `## <id> · HH:MM · джерело <label> · ядро v<v> · база v<a> → v<b>` with a one-line count, a table of the blocks the repository offered something for (block, sign, decision, why — in the cascade's words, e.g. «змінили обидва → лишено твоє: блок не є правилом ядра» — and the record that holds it), and for every conflict (`⚠`, `?`): what was done, the lines each side changed since the base, and **both texts** — up to 40 lines each side, each line clipped to 500 characters, then `… ще N рядків — <where in full>`; what the server sent is shown as code, never as Markdown — the versions in the heading and the captions, and the reason of a part with no plan (`Причина: …`), too. Under a conflict kept as yours, the command that takes the core's text, ready: `Взяти текст ядра: ctx provider apply <repo> --choose <block>=theirs` — not under a `⚠` of a block the core removed (there is no core text to take) and not under a rule (the core's text is already in); a waiting `?` gets it (`Прибрати блок, як у ядра: …=theirs` when the core removed the block) and `Лишити своє: …=mine`. A part ends with the way back, `Відкотити цей прохід: ctx undo (знімок <folder>)`, when its pass has a snapshot; a part without one (a broken source, an import conflict, a pass that wrote nothing) ends `Знімка цього проходу немає: відкочувати нічого.`, and the part of an `error` says the snapshot is unknown (`ctx status` shows the journal). A report older than 90 days moves to `~/.grow-pm/trash/` at the start of a pass; it is data in your own vault only (`data-policy.md`). A report that cannot be written is said in the pass's `reason`; the pass stands.

**The way back.** `ctx undo` takes the pass back and makes the sync remember what it took as rejected (`context-protocol.md` §8): neither the sync nor `ctx provider apply` applies that text again until the repository publishes a new one in the block, and a plan marks the row «відкинуто вами — не застосовується, доки ядро не змінить блок». `ctx undo` takes back the last change in the journal, not a named snapshot: when anything was written after the pass, prefer `ctx provider apply <repo> --choose <block>=theirs` to `ctx undo` to take the core's text for one block the sync kept as yours (`theirs` is an answer for a `✎` since v3.14.0, §12.5), and edit a block the sync updated if you want it in your own words — an edit inside a block is kept.

**The digest.** The `repos:` line and the `Skills:` line are described in `context-protocol.md` §7.
