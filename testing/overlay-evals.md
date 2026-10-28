# Overlay evals — your corrections to a core, the changelog, a kit in one command (v3.23.0)

Purpose: verify the skills' half of `references/context-protocol.md` §5n–§5r — that `context-connect` drafts a prose note of corrections into operations without copying a value into a block, that a held correction is one question, that the brief and `/context` say what waits, and that a kit connects in one command. The engine is covered by `testing/ctx_overlay_test.py`, `ctx_overlay_merge_test.py`, `ctx_overlay_read_test.py`, `ctx_overlay_cli_test.py`, `ctx_core_suggest_test.py`, `ctx_history_test.py`, `ctx_identity_test.py` and `provider_kit_test.py`; this file is an agent eval, run by hand on a scratch HOME.

## How to run

1. A scratch HOME with the fixture context of `testing/fixtures/ctx-repos/context.md` migrated, `zorg-core` registered on a copy of `examples/provider-kit/zorg-core/` and its blocks adopted; `GROW_PM_CONTEXT_PATH` set to that HOME's copy.
2. Put the note below at `<vault>/Notes/_personal/Overlay Alpha — corrections to the core.md` (fictional).
3. Pass when every row's expectations hold, no file of the core folder changed, and every write the skill made was preceded by the user's «так».

```markdown
# Overlay Alpha — corrections to the core
## 1. Members
The core's table lists stubs; my Team Members table is the source.
## 2. Missions
«Reviews everywhere» is active, the core shows no quarter.
## 3. Epics
Statuses as in Jira on 2026-10-01 — nothing to fix.
## 4. Scope
The core says «Zorg App» only; Zorg Lite too.
## 5. Dead links
Dashboard links to the owner's personal notes.
```

## Scenarios

| # | Say / state | Expected |
|---|---|---|
| 1 | «перенеси мої поправки до ядра в оверлей» | `context-connect` §8: a draft with `replace` of `team › #Members` by `value_ref` to the user's own subsection and an operation on `scope` (an `append` of «Zorg Lite too», or an `ignore` with `match:"Zorg App"`); `ctx overlay plan --file` shown in one message with «не стали операціями»: missions (no block), epics (nothing to fix), dead links (not context); one «так» → `ctx overlay apply … --code`; the note unchanged |
| 2 | The core releases v0.2 with `scope` changed so that the ignored words are gone; then «онови мій пакет з ядра» | the refresh applies with no question about blocks; one question «ядро виправило — прибрати поправку?» for the held operation, `прибрати` recommended → `ctx overlay answer zorg-core <id> drop` |
| 3 | The same release, but through the daily sync; next morning «на чому сфокусуватись» | the brief has one line «оверлей … чекає рішення — /grow-product-manager:context overlay»; nothing is asked or written in the brief |
| 4 | `/grow-product-manager:context history` | `ctx history --write`; three lines: the core's release with its blocks, the user's own changes, what waits |
| 5 | «хто я за ядром» with the role in the profile `pm` and the core's card saying «Data analyst» | `ctx identity check`: two lines with both sources; one question; «лишити моє» → `ctx identity keep zorg-core role …`; asked again only after the core's card changes |
| 6 | «підключи набір провайдера» with the kit folder of `examples/provider-kit/zorg-core/` and no registration | `ctx repo kit-check`, then `ctx repo add … --email pat.moss@zorg.example` in one message (team, role, registration, blocks); «так» → `--apply --code`; then the daily-sync question |
| 7 | A host without SHELL, «що в мене поправлено в ядрі» | the skill reads `overlays/zorg-core.yaml` as text and says per operation what it does; nothing laid, nothing asked |
