---
description: Show the plugin's health in one screen — version, where local-context.md was found and its schema version, vault level, declared connectors vs tools actually present in this session, deferred onboarding steps
argument-hint: "[--verbose]"
disable-model-invocation: true
allowed-tools: Read, Glob, Grep
---

# /grow-product-manager:status

A read-only diagnostic. It never launches `plugin-configurator`, never writes, never asks questions — it reports what it can see and stops.

## Collect

1. **Plugin version** — read `${PLUGIN_ROOT}/.claude-plugin/plugin.json` (`${CLAUDE_PLUGIN_ROOT}` on Claude; if neither variable expands, walk up to the directory that contains `skills/` — `references/host-profiles.md` §6) → `version`. The same resolution applies to every `${PLUGIN_ROOT}` path below.
2. **Local context** — search in the order defined by `references/local-context-protocol.md` Step 0a (`~/.grow-pm/local-context.md` → legacy locations → session cwd). Also look under connected folders (`$HOME/mnt/*/local-context.md`, `$HOME/mnt/*/.grow-pm/local-context.md`) — in a hosted session the user's home is not visible and the context arrives through a connected folder. Report the path found, or "not found in this environment". If found, read only the header: schema version, `user.language`, product names. Do **not** parse or validate the rest.
3. **Vault level** — L0 / L1 / L2 per `references/persistent-storage.md` (folder present? Obsidian MCP tools present?).
4. **Connectors** — read `${PLUGIN_ROOT}/.mcp.json`; for each declared server, check whether tools with the namespace listed in `references/integration-strategy.md` → *Declared connectors* are present in this session. Add the undeclared-but-relevant ones (Tableau, Notion, Obsidian, Slack) as "not declared — detected by pattern" rows.
5. **Deferred onboarding** — if the context has `onboarding.deferred_steps` / `deferred_connectors`, list them.
6. With `--verbose`: also list the agents (`${PLUGIN_ROOT}/agents/*.md`) and commands (`${PLUGIN_ROOT}/commands/*.md`) this plugin ships, and the skill versions from `skills/*/SKILL.md` frontmatter.

## Report

One table, in the user's language (`user.language` if the context was found, otherwise the language of the user's last message):

| Component | Status | Detail |
|---|---|---|
| Plugin | vX.Y.Z | — |
| local-context.md | found / not found | path, schema vN, products |
| Vault | L0 / L1 / L2 | path |
| Connector: atlassian | ✅ connected / ⚠️ not in session | tool namespace seen |
| … | | |
| Deferred | n items | list |

Then one line: the single most useful next action (e.g. "run `/grow-product-manager:config validate`", "connect Atlassian in the plugin's Connectors tab", "nothing to do"). Nothing else.
