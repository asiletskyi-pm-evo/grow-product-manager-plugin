---
description: Typed command /grow-product-manager:context only — never for a conversational «що ти про мене знаєш» (that is context-navigator). show — what the plugin knows and where from; health — what wants looking after; inbox — what waits for your «так»; recheck — records against the connectors; consolidate — tidying as proposals.
argument-hint: "show [запис] | health | inbox | recheck | consolidate"
disable-model-invocation: true
---

# /grow-product-manager:context

> **Path rule.** A bare `references/<file>.md` in this file is read from the **shared** `references/` at the plugin root. Resolve the root as `${PLUGIN_ROOT}`, else `${CLAUDE_PLUGIN_ROOT}`, else the directory that contains `skills/`, found by walking up from this folder (`references/host-profiles.md` §6). A bare `skills/<name>/SKILL.md` is read from the same root. Never continue without a protocol named here.

Your context, typed. It does what `context-navigator` does with the same words in conversation (`references/context-protocol.md` §5i–§5m). `show` and `health` read only; `inbox` writes only your answer; `recheck` and `consolidate` write only the inbox (and the recheck's memory) — never a record before your «так».

## What was typed

The first word is the action:

- `show` — what the plugin knows about you: `ctx show`, one line a record, then your answers and the inbox. `show <id …>` adds those records' text.
- `health` — what wants looking after: `ctx health`, ✅ / ⚠ / ✋ a line, each with the command that fixes it.
- `inbox` — what skills proposed: `ctx inbox list`, then one question.
- `recheck` (since v3.22.0) — your records against the connectors (§5l), then the inbox's question for what it proposed.
- `consolidate` (since v3.22.0) — duplicates, relative dates, passed deadlines as proposals (§5m), then the inbox's question.
- nothing — `health`, then the inbox's one line.

Any other first word → one line, `Невідома дія: <слово> — /grow-product-manager:context show [запис] | health | inbox | recheck | consolidate`, and stop.

## Run

Step 0-host (`references/host-profiles.md` §3). Without SHELL, or without a context store — the session digest shows no `context: records …` line, or, on a host without the digest (Codex CLI), `{storage_root}/_System/context/.state/` does not exist; `ctx health` exiting 3 with `no store at …` says the same — one line, `Сховища контексту немає — /context працює зі сховищем; твій local-context.md: <шлях>`, then show `local-context.md`'s section headings and stop.

Otherwise run `python3 "<plugin root>/scripts/ctx.py" <show|health|inbox list>` and give its lines as they are (they are Ukrainian already), with nothing added but, for `inbox`, the question below.

**inbox.** An empty inbox → `Скринька порожня.` and stop. Otherwise show the numbered lines, then ask **one** question: «Прийняти всі / номери (наприклад 1, 3) / відхилити номери / пізніше?» On the answer:
- «так» / «всі» → `ctx inbox accept all --code <код зі списку>`;
- numbers → `ctx inbox accept <номери> --code <код>`;
- «відхилити <номери>» (with a reason if given) → `ctx inbox reject <номери> --code <код> [--reason "<причина>"]`;
- «пізніше» / no answer → nothing.

Exit 4 «скринька змінилась» → run `ctx inbox list` again and ask again; never retry with another code you did not show. After an accept, say what was taken and `Скасувати: ctx undo`. A line «№N не прийнято: …» is said as it is.

**recheck.** Read the connectors **read-only** by `references/context-observe.md` §4 (the visible Jira projects and Confluence spaces in full, each team member's account, a registered provider's role); write the observation file in the session's scratchpad, every connector tried in `connectors`; run `ctx validate --recheck --observed <file>` and give its lines. Urgent proposals → one question as §5i says, with the code it printed; the rest → its «У скриньці +N» line. Then `ctx verify <ids>` for the records it named as they should be, and delete the file. No connector at all → `Немає конекторів для звірки — підключи Atlassian` and stop.

**consolidate.** `ctx consolidate`, its lines as they are; when it proposed something, `ctx inbox list` and the inbox's one question above. A line `ctx archive <id>` is said, never run unasked.

Apart from what `recheck` and `consolidate` hand to the inbox, the command never proposes a delta and never accepts what the user did not choose.
