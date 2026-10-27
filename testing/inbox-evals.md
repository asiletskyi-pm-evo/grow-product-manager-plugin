# Inbox evals — the end-of-run deltas of 10 skills (v3.21.0)

Purpose: verify the end-of-run step of `references/context-protocol.md` §5i — that a skill which learned something about the user's context proposes the right delta, the inbox calls it urgent or not by its own table, and the user takes the batch in one answer. The concept's criterion (`Context-Core-Concept-v1.md` §8, phase 4): «дельти від 10 скілів потрапляють у inbox і приймаються пакетно».

The engine is covered by `testing/ctx_inbox_test.py` (schema, dedup, urgency, codes, accept/reject, undo). This file covers the skills' half: what they propose. It is an agent eval, run by hand on a scratch store (the fictional typical context of `testing/fixtures/ctx/typical.md`, migrated), never on the user's own store.

## How to run

1. A scratch HOME: `testing/ctx_testenv.py`'s `Env`, `ctx migrate --apply`, `ctx compile`; `GROW_PM_CONTEXT_PATH` pointed at its `local-context.md`.
2. For each row: run the skill on the input (pasted, never a live connector), let it finish, read `ctx inbox list`.
3. Pass when the expected delta is in the inbox (op, record, the field or the line — the wording of a line may differ), the urgency matches, and nothing else was proposed; a row with «NOOP» passes when the inbox gained nothing.
4. At the end: `ctx inbox list` → `ctx inbox accept all --code <код>` → every accepted line is in its record, `ctx undo` puts the store back byte for byte.

## Scenarios

| # | Skill | Input (fictional) | Expected delta | Urgent |
|---|---|---|---|---|
| 1 | `focus-advisor` | mode `now`; the pasted calendar shows a weekly «Zorg App — funnel review» with a Tableau link `https://tableau.zorg.example/funnel` the product record lacks | `ADD product.zorg-app` `- Zorg funnel — https://tableau.zorg.example/funnel` under its analytics | no |
| 2 | `meeting-processor` | a transcript: «Zorg Lite is closed since Q3, the team moved to Zorg App» | `INVALIDATE product.zorg-lite` reason «closed in Q3» | yes |
| 3 | `requirements-creator` | the spec is published to Confluence space `ZAPP2`, the record says `ZAPP` | `UPDATE product.zorg-app` `Confluence Space` → `ZAPP2` | yes |
| 4 | `write-concept` | the concept names a competitor «Zorg Rival» the product record does not list | `ADD product.zorg-app` `- Zorg Rival` under competitors (or `UPDATE Competitors`) | no |
| 5 | `task-creator` | the epic lives in Jira project `ZORG`, the record says `PROJ` | `UPDATE product.zorg-app` `Jira Project Key` → `ZORG` | yes |
| 6 | `product-research` | the research finds «Zorg Other» as a direct competitor | `ADD product.zorg-app` `- Zorg Other` | no |
| 7 | `product-analysis` | the pasted dashboard shows the conversion baseline 3.1 % on `https://tableau.zorg.example/conv` | `ADD product.zorg-app` `- Zorg conversion — https://tableau.zorg.example/conv` | no |
| 8 | `cjm-research` | the funnel's baseline for checkout changed from 41 % to 38 % per the pasted report | `ADD setting.cjm-configuration` (or `UPDATE` of its baseline line) with the new baseline and its source | no |
| 9 | `product-reporter` | the sprint report shows a new member «Zorg Dev (BE)» in team Alpha | `ADD team.alpha-a` `| Zorg Dev | BE |` under `#### Members` | yes |
| 10 | `sprint-planning` | the plan finds nothing new: the team, the board and the products are as recorded | NOOP — the inbox gains nothing | — |

## Must never be proposed

| Input | Why |
|---|---|
| a 1-1 note saying «Zorg Dev is on sick leave» (any skill) | health, a person — `data-policy.md` «What the context store never keeps» |
| an API key pasted in a meeting transcript | `ctx propose` refuses it (exit 4), the skill must not try |
| `one-on-one`, `performance-review`, … on any input | the People contour proposes nothing |
| a heading «## Zorg Ghost» as an ADD | a new record is the configurator's (v3.22.0), `ctx` refuses it |
