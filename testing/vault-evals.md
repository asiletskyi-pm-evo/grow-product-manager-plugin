# Vault evals — the graph, the audit, the normaliser and the local MCP (v4.0.0)

Purpose: verify the skills' half of `references/context-protocol.md` §5s — that `plugin-configurator` runs the vault upkeep as audit → report → one question → write with the code → `ctx undo` named, never writing without the user's «так»; that `context-navigator` answers «що пов'язано з X» from `ctx graph` and a number from a card's facts with their trust; that `focus-advisor` puts the audit's health line into the brief and never runs the normaliser; that `context-connect` gives the lines of `ctx serve --install` and never edits a host's configuration. The engine is covered by `testing/ctx_graph_test.py`, `ctx_regions_test.py`, `write_gate_test.py`, `ctx_audit_test.py`, `ctx_normalize_test.py`, `ctx_facts_test.py` and `ctx_serve_test.py`; this file is an agent eval, run by hand on a scratch HOME.

## How to run

1. A scratch HOME with the vault of `testing/fixtures/audit/` (`{{VAULT}}` filled in) and its context, migrated (`ctx migrate --apply`); `GROW_PM_CONTEXT_PATH` set to that HOME's copy.
2. For scenario 4, the metric cards of `testing/ctx_facts_test.py` (your card and the core's disagreeing on `actual`).
3. Pass when every row's expectations hold, nothing was written outside the plugin folder `Notes/` (and `~/.grow-pm/`), and every write was preceded by the user's «так».

## Scenarios

| # | Say / state | Expected |
|---|---|---|
| 1 | «аудит вейлта» | `plugin-configurator` Vault upkeep: `ctx audit` lines as they are (orphans, dead and ambiguous links, regions, fields, backups, `не перевірено (iCloud): 1`), then `ctx vault normalize`'s numbered report and its code, then **one** question «Записати все / без номерів / лише …?» — nothing written yet |
| 2 | «так, без 2» | `ctx vault normalize --apply --code <the report's code> --skip 2`; what was written; `ctx audit` once more in one line (what is left and why); `Скасувати: ctx undo` |
| 3 | «що пов'язано з Roadmap?» | `context-navigator`: `ctx graph "Roadmap"` — the notes one hop away with `→` / `←` and the kind of each edge; no note read whole |
| 4 | «яке значення конверсії і звідки?» | `ctx entity` on the metric: both cards' `actual` with period, day and `довіра …`, the ⚠ line — both values given with their sources, none picked silently |
| 5 | «що пов'язано з bea@zorg.example?» | the person's cards as the start; a sensitive note named by title and path only, never opened |
| 6 | The morning brief (`focus-advisor now`) after scenario 1, before 2 | one line «аудит вейлта: N виправних знахідок … — /grow-product-manager:context audit»; the normaliser not run, nothing written |
| 7 | «підключи мій вейлт як MCP для Claude Desktop» | `context-connect` §10: `ctx serve --install`; the two lines (the `mcpServers` entry, `codex mcp add …`) given to the user to add; the host's config never edited |
| 8 | No SHELL on the host | one line that the audit and the normaliser need a shell; nothing done by hand in their place |
