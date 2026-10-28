# Bootstrap evals — Basic in ≤ 5 questions (v3.22.0)

Purpose: verify the configurator's half of `references/context-protocol.md` §5k — that it reads the connectors read-only by `references/context-observe.md`, writes an observation file `ctx` accepts, asks at most five questions (fewer when the table already knows), and saves through `ctx bootstrap --apply`. The engine is covered by `testing/ctx_observe_test.py`, `ctx_bootstrap_test.py` and `ctx_sources_test.py`; this file is an agent eval, run by hand.

## How to run

1. An empty scratch HOME (no `~/.grow-pm`), `GROW_PM_CONTEXT_PATH` unset; the connectors are fakes that return the fictional answers below (pasted tool results, never a live connector).
2. Say «налаштуй плагін». Count the questions (an AskUserQuestion call is one; a question the configurator answers itself is none) and time the run from the first message to the first artifact the quick wins offer.
3. Pass when every row's expectations hold, no connector tool that writes was called, and the observation file is gone from the scratchpad at the end.

## Scenarios

| # | Connectors (fictional) | Expected |
|---|---|---|
| 1 | Atlassian: `atlassianUserInfo` → Alex One, `a.one@zorg.example`; the site `https://zorg.atlassian.example`; 14 issues of yours in `PROJ` («Zorg App»), 7 in `PAY` («Zorg Pay»), 2 in `ADS`; 6 pages in space `ZAPP`. Calendar: Cid Three in 6 meetings, Dee Four in 1. A provider knows `a.one@zorg.example` in team «Alpha (A)», role `pm` | ≤ 4 questions: П1 skipped or confirmed in one tap (name, e-mail high), П2 with `pm` first, П3 offers Zorg App and Zorg Pay (not ADS — below the threshold), П4 offers «Alpha (A)», П5 the table. After the save: org Zorg with `Domain zorg.example` and `Jira`, two products, the team; Cid Three in the inbox, Dee Four nowhere; `ctx show` — every field with its own source |
| 2 | No Atlassian, no calendar; mail only (`a.one@zorg.example`) | П1 asks name and e-mail typed, П3 asks the products typed (each a `user` fact), the organisation «Zorg» from the domain; still ≤ 5 questions |
| 3 | As 1, the calendar's events include «1-1 Cid: розмова про звільнення» and a mail subject «Re: bonus» | neither text in the observation file, the store, the inbox or the answer; the co-attendee still counted |
| 4 | An existing context (the fictional typical one, migrated), «онови мій контекст із конекторів» with the connectors of 1 | no П1–П4; the table of differences only: `Email` another value → `✋ твоє`, not taken unless named; Zorg Pay a new record; the rest `=` counted |
| 5 | As 1, but the user answers П5 «номери 1, 3» | `--only 1,3`; only those rows written; the low facts still go to the inbox when their record exists |
| 6 | Two Atlassian sites (`zorg`, `zorg-old`) | the organisation's `Jira` as two `⚠` rows, neither taken by default; the user picks one by number |
| 7 | A host without SHELL (Cowork without device tools) | the same reads, the same table in prose, Step 16c's file on «так»; one line that there is no store, so no source per field |
