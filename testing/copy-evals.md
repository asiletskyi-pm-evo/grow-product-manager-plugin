# Copy evals — the plugin's own copy of a core that lives only on a server (v3.24.0)

Purpose: verify the skills' half of `references/context-provider-protocol.md` §12.12 — that `context-connect` offers the copy once after registering an MCP-only repository with a blocks file and runs `ctx repo copy` only on «так», that a «ні» is remembered for 30 days outside the registration, that the request to the core's owner for the two `.md` wrappers is given ready to send and never sent, and that `context-navigator` cites a note of the copy with «копія від <day>». The engine is covered by `testing/ctx_copy_test.py`, `ctx_copy_pass_test.py`, `ctx_copy_wrap_test.py`, `ctx_copy_folder_test.py`, `ctx_copy_sync_test.py` and `provider_kit_test.py`; this file is an agent eval, run by hand on a scratch HOME.

## How to run

1. A scratch HOME with the fixture context of `testing/fixtures/ctx-repos/context.md` migrated; `GROW_PM_CONTEXT_PATH` set to that HOME's copy.
2. The fake server of `testing/mcp_fake.py` serving the `.md` notes of `examples/provider-kit/zorg-core/` under `Zorg/` (frontmatter apart from the text) — without the two wrappers for scenarios 1–3, with them for 4–5.
3. Pass when every row's expectations hold, nothing was written outside `~/.grow-pm/cores/zorg-core/`, `~/.grow-pm/conflicts/zorg-core/` and the store, and every write the skill made was preceded by the user's «так».

## Scenarios

| # | Say / state | Expected |
|---|---|---|
| 1 | «додай провайдер контексту» for the server, with `blocks_file: Core/_System/context-blocks.md` | `context-connect` §7: the registration (`kind: mcp`, no `paths`), then one line «Зробити власну копію ядра? ~13 нотаток, ~1 хв, `~/.grow-pm/cores/zorg-core` …»; on «так» → `ctx repo copy zorg-core` and its one summary line; no second question |
| 2 | The same, answered «ні»; then «онови мій пакет з ядра» the next day | the «ні» is in `{store}/.state/copy-offers.json` (`context-copy-offers/1`), not in the registration; the refresh does not offer again (under 30 days) |
| 3 | After the copy, `ctx provider plan zorg-core` | the team row `·` «сервер не віддає provider-manifest …»; the skill gives the request for the core's owner (the two wrappers, §9, `ctx repo kit-check`) ready to send and does not send it |
| 4 | The server now serves both wrappers; «онови мій пакет з ядра» | `ctx repo copy zorg-core` (or the daily sync) unpacks them; the plan's team row is offered from the copy (`джерело: копія від <day>`); nothing is asked about the copy itself |
| 5 | The server down (VPN off); «що робить команда Alpha?» | `context-navigator`: `ctx search` answers from the copy, no server asked; the answer cites `@zorg-core/Core/Teams/team-alpha.md` with «копія від <day>» |
| 6 | No SHELL on the host | no offer of a copy; the server is read in prose, as before; one line that the copy needs a shell |
