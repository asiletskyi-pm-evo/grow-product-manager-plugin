---
description: Typed command /grow-product-manager:context only — never for a conversational «що ти про мене знаєш» (that is context-navigator). show · health · inbox (what waits for your «так») · recheck (records against the connectors) · consolidate (tidying as proposals).
argument-hint: "show [запис] | health | inbox | recheck | consolidate"
disable-model-invocation: true
---

# /grow-product-manager:context

> **Path rule.** A bare `references/<file>.md` in this file is read from the **shared** `references/` at the plugin root. Resolve the root as `${PLUGIN_ROOT}`, else `${CLAUDE_PLUGIN_ROOT}`, else the directory that contains `skills/`, found by walking up from this folder (`references/host-profiles.md` §6). A bare `skills/<name>/SKILL.md` is read from the same root. Never continue without a protocol named here.

Your context, typed — what `context-navigator` does with the same words (`references/context-protocol.md` §5i–§5m). No record is written before your «так».

## What was typed

The first word is the action:

- `show` — what the plugin knows about you: `ctx show`, one line a record, then your answers and the inbox. `show <id …>` adds those records' text.
- `health` — what wants looking after: `ctx health`, ✅ / ⚠ / ✋ a line, each with the command that fixes it.
- `inbox` — what skills proposed: `ctx inbox list`, then one question.
- `recheck`, `consolidate` (since v3.22.0) — below.
- nothing — `health`, then the inbox's one line.

Any other first word → one line, `Невідома дія: <слово> — /grow-product-manager:context show [запис] | health | inbox | recheck | consolidate`, and stop.

## Run

Step 0-host (`references/host-profiles.md` §3). Without SHELL, or without a context store (no `context: records …` digest line; without the digest, no `{storage_root}/_System/context/.state/`; `ctx health` exit 3 `no store at …`) — one line, `Сховища контексту немає — /context працює зі сховищем; твій local-context.md: <шлях>`, then show `local-context.md`'s section headings and stop.

Otherwise run `python3 "<plugin root>/scripts/ctx.py" <show|health|inbox list>` and give its lines as they are (they are Ukrainian already), with nothing added but, for `inbox`, the question below.

**inbox.** An empty inbox → `Скринька порожня.` and stop. Otherwise show the numbered lines, then ask **one** question: «Прийняти всі / номери (наприклад 1, 3) / відхилити номери / пізніше?» On the answer:
- «так» / «всі» → `ctx inbox accept all --code <код зі списку>`;
- numbers → `ctx inbox accept <номери> --code <код>`;
- «відхилити <номери>» (with a reason if given) → `ctx inbox reject <номери> --code <код> [--reason "<причина>"]`;
- «пізніше» / no answer → nothing.

Exit 4 «скринька змінилась» → run `ctx inbox list` again and ask again; never retry with another code you did not show. After an accept, say what was taken and `Скасувати: ctx undo`. A line «№N не прийнято: …» is said as it is.

**recheck** — as §5l: the connectors read-only by `references/context-observe.md` §4, `ctx validate --recheck --observed <file>`, its lines; urgent → the §5i question; then `ctx verify` for the records it names. **consolidate** — `ctx consolidate` (§5m), its lines, then the inbox's question; `ctx archive` is said, never run unasked.

Beyond what these two hand to the inbox, the command never proposes a delta and never accepts what the user did not choose.
