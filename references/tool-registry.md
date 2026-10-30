# tool-registry.md

> Shared reference (since v4.2.0). The **tools registry** keeps what helps the user's work and is not part of the plugin — other plugins, skills, MCP connectors, apps, CLIs, sites, portals, courses — with what each one is for, whether it is on this machine, how to connect it and what the user thinks of it. `knowledge-library` owns it (section «Інструменти», workflows in `skills/knowledge-library/references/tools-workflows.md`); `scripts/tools_scan.py` reads and writes it; three skills offer a missing tool at their step (§4). A team's core may publish its own list (§5).
>
> **Rule of the file:** a tool is a name, a job and a way to connect — never a value from a host's configuration. The scan reads names only (§3), and nothing here is ever published or connected without the user.

## 1. A record

| Field | What | Written by |
|---|---|---|
| `id`, `name` | slug and name | the scan, the seed or the user |
| `kind` | `plugin` · `skill` · `mcp` · `app` · `cli` · `site` · `portal` · `course` | the scan, the seed or the user |
| `job`, `skills`, `contours` | the PM work it does, and the skills and contours whose steps it serves | the seed or the user |
| `hosts` | where it was seen: `claude-code`, `claude-desktop`, `codex`, `agents` (a cross-host skills folder), `session`, `account`, `standalone` | the scan |
| `access` | `free` · `paid` · `corporate` · `unknown` | the seed or the user |
| `connect` | how to connect it, in one line — never a key, a token or a URL with credentials | the seed or the user |
| `state`, `seen`, `seen_by` | what the last observation found: `connected` (its tools are in this session) · `needs-auth` · `installed` · `not-installed` · `not-seen` (seen before, absent now); the day; the sources that saw it. Only an observation of the same kind sets it — an installed app never makes a connector `installed`; it counts for an app, a site or a CLI | the scan only |
| `verdict` | the user's own word: `tried` · `recommended` · `deprecated` | the user only |
| `declined` | `{skill, date}` — the user's «ні» to the suggestion in that skill | the suggesting skill, on the «ні» |
| `recommended_by` | `я`, a colleague's name (identity only — `people-context-protocol.md`), or `team:<core id>` | the user or a core |
| `checked` | the day the user last checked the record | the user |
| `aliases`, `needs` | other names a host lists it under; what a step can ask it for (`mind-map`, `transcript`, `market-data` …, §4) | the seed |
| `notes`, `cleared` | the user's own note; the seed fields the user emptied, which a seed never fills back | the user |
| `via` | another record that brings this one (FigJam comes with the Figma connector): when that one is installed or connected, this one is not suggested | the seed or the user |
| `publishes` | what a result can become there: `board` · `page` · `document` · `deck` · `dashboard` · `design` (read by publishing skills) | the seed or the user |
| `shared` | goes into the export for the team (§5) | the user only |
| `sources` | every way the record arrived: `seed`, `scan-<source>`, `registry-search`, `catalog`, `user`, `team:<id>` | the script |

The observed `state` and the user's `verdict` are separate on purpose: a scan never touches `verdict`, `declined`, `recommended_by`, `shared` or the user's notes, and it never deletes a record — what it no longer sees becomes `not-seen`, and only when the very file or the session that saw it was read this time. A `registry.json` that is there and does not read is never reset: every command that writes stops with exit 1 and leaves it as it is, for the user to restore from the vault mirror.

## 2. Where it lives

`~/.grow-pm/knowledge-library/tools/` — `registry.json` (written by `tools_scan.py` only), «tools.md» (the same records as a table, rendered on every write, with the team's records in their own section), `scans/<date>.jsonl` (what each scan saw), `team/<core id>.json` (read-only copies of the cores' lists), `export/` (files for a core's owner). `knowledge-library` mirrors «tools.md» and `registry.json` into the vault's `Knowledge/tools/` after every write, as it mirrors the rest of the library. No FS → the registry lives in the chat for the session (`persistent-storage.md`). No SHELL → the registry is read-only: the skill can show the table, a scan shows the session's own listing in the chat and writes nothing, and no step suggests anything (§4).

## 3. How it is filled

1. **The seed** — `references/tools-seed.yaml`: the tools the plugin already names (the declared connectors, the products found by pattern, the external tools of `diagram-prototyper`, the meeting sources). A seed record claims nothing about the machine: its state stays «not installed» until something sees it.
2. **The scan** (`tools_scan.py scan`) — what is installed, by itself, with no question and no manual input. It reads **names only**:
   - the plugins a host installed locally, and the skill folders a host loads (a skill's `name` and the start of its `description`);
   - the **names** of the MCP servers in each host's configuration — the keys of its server map, or the table headers and keys of a TOML file, never a value under them: never a command, an argument, an environment variable, a header or a URL; a line inside a multi-line string or array is never looked at, and a name that looks like a key, an opaque id or anything but a plain name is refused;
   - installed apps through `landscape_scan.sh` (never with `--bookmarks`), kept only when an app matches a seed record's `app_names` / `app_bundle_ids`.

   Which file belongs to which host is the script's business; a skill says «the host files on this machine». Each file is its own source (`scan-claude-code-mcp`, `scan-codex-plugins` …), named as read only when it was there and read. The plugin itself and its own skills are not records.
3. **The session and the account** — what the scan cannot see, the agent adds as observed rows (`merge --observed`): the MCP servers whose tools are in its own tool list (`connected`; `needs-auth` when the host lists a server that waits for authorisation), the skills and plugins loaded in the session, and the plugins and skills of the host account when the session has a tool that lists them. A server with an opaque id is named by the product its tools reveal or left out; the host's own servers are capabilities, not tools (`skills/knowledge-library/references/tools-workflows.md` TS-3). Every field of a row comes from a closed list or passes the filter (§6); a row that does not is dropped and counted, never written — the scan journal included.
4. **On request** — «знайди інструмент для …»: the MCP registry search (`integration-strategy.md` Step 2) and the host's catalogue of its organisation's plugins, when the session has a tool for either. The keywords leave the session, so they are public words only (`data-policy.md`). The results are a list; only what the user picks becomes a record (`source: registry-search` or `catalog`, with the `state` the search gave — `connected` or `not-installed`). Connecting is always the user's action — a connection card the host draws is fine; the skill never configures anything itself.
5. **By hand** — a site, a portal, a course, a colleague's recommendation (`tools_scan.py add`).

## 4. The suggestion at a step

A skill that a tool would help at one of its steps asks `tools_scan.py suggest --skill <name> --need <what the step needs>` and gets at most one record: one whose `skills` name the skill, whose `needs` carry the tag (when one is given), that is neither `installed` nor `connected`, that the user has not declined for this skill, whose `verdict` is not `deprecated` and whose `via` tool the user does not already have — the user's own `recommended` first, then what the team recommends, then the seed's; among equals, a tool that names the skill first in its `skills`, then the seed's order. Then it says **one line**, in the user's language, and goes on with the step:

> «Для цього кроку є NotebookLM (mind maps із публічних матеріалів) — у тебе не підключений. Як: у браузері, notebooklm.google.com. Не пропонувати — скажи «ні».»

- **Once per run**, never as a question, never blocking the step.
- **Never in a scheduled or headless run** (`native-surfaces.md` §4) — nobody reads the line there.
- **«Ні»** → `tools_scan.py decline --skill <name> --id <id>`: not offered again in this skill; other skills may still offer it.
- **No registry, nothing to suggest, or no SHELL → no line.** The suggestion is an addition: its absence changes nothing (`native-surfaces.md` §5, «No line for an addition»).

| Skill | Step | The work | `--need` |
|---|---|---|---|
| `diagram-prototyper` | Step 4 — tool selection | boards and visuals | the visualization type |
| `product-research` | Step 2 — gather data | market data | «market-data» |
| `meeting-processor` | M1 — the meeting source | transcripts | «transcript» |

Other skills do not suggest yet.

## 5. The team's registry

A core may publish its own list: the optional key `tools_file` of its provider manifest (`context-provider-protocol.md` §3a) names a file in the format of the export below. The bundle builder copies it with the manifest for every role; the plugin's own copy of a server-only core carries it as the server serves it (§12.12 there).

- `tools_scan.py team` finds the user's cores through the registration resolver of `ctx` — never a path built from parts — reads each core's `tools_file` and keeps its records in `team/<core id>.json`, marked `recommended_by: team:<core id>`. They are **read-only** and stay separate: the table shows them as «Від команди», `suggest` counts them after the user's own `recommended` (a «ні» to one is kept beside them, in `team-declined.json`), and «взяти собі» (`add --from-team`) copies one into the user's registry. A core's record is checked as an export is — closed lists, real skills, texts through the filter; one that is not sound is dropped. A list no core publishes any more (the key gone, the registration gone, the file outside the core) is removed at the next `team`.
- **The export** — `tools_scan.py export` writes `export/tools-shared-<date>.yaml` with the records the user marked `shared`, and only the fields `name`, `kind`, `job`, `skills`, `contours`, `access`, `connect`, `verdict`, `recommended_by`, `checked`, `publishes` — never `state`, `seen_by`, `hosts`, `sources`, `declined` or notes. With no shared record no file is written. The result names each registered core with its `owner_label`; the skill says one line: give the file to the core's owner, who puts it at the path `tools_file` names.
- **The plugin never writes into a core** (`context-provider-protocol.md` §7). Only the owner adds the file.

## 6. What never happens

- A value from a host's configuration is never read, kept or shown — only a name (§3).
- A text the script writes passes the never-store filter of `ctx` (`data-policy.md`, «What the context store never keeps»): a `connect` line that holds a key is refused, by kind, never echoed.
- Nothing is connected, installed or configured by a skill.
- The registry is internal data: it stays on the machine and in the vault. Showing it on a hosted surface is a publication and takes the question of `native-surfaces.md` §3; no skill does it in v4.2.0.
- A person's profile is never a tool record; `recommended_by` holds a name, never a judgement.

## 7. The script

`python3 scripts/tools_scan.py <command>` — Python 3.9 stdlib; every command ends with one `TOOLS_RESULT {json}` line; `--store DIR` (default `~/.grow-pm/knowledge-library/tools`) and `--home DIR` (default the user's home: its host files and its own `local-context.md`) are accepted by each. Installed apps are always this machine's — pass `--no-apps` where that matters.

| Command | Does |
|---|---|
| `scan [--no-apps]` | the names of §3.2, one JSON line each |
| `merge [--scan FILE] [--observed FILE] [--rescan]` | seed + scan + observed rows → `registry.json`, «tools.md», `scans/<date>.jsonl` |
| `suggest --skill S [--need TAG]` | at most one record (§4); `S` must be a skill of the plugin |
| `decline --skill S --id ID [--undo]` | the user's «ні» for one skill |
| `add --name N --kind K [--source user\|registry-search\|catalog] [--state connected\|not-installed] [field=value …]` · `add --from-team NAME` | a record by hand or from a search the user asked for · a team's record taken over |
| `set --id ID field=value …` | the user's fields: `verdict`, `shared`, `recommended_by`, `connect`, `job`, `access`, `skills`, `contours`, `publishes`, `checked`, `notes` |
| `team [--context PATH]` | the cores' lists (§5), read-only |
| `export [--context PATH]` | the shared records, one file for a core's owner (§5) |
