---
description: Typed command /grow-product-manager:context only — never for a conversational «що ти про мене знаєш» (that is context-navigator). show — what the plugin knows about you and where from; health — what wants looking after; inbox — what skills learned, waiting for your «так».
argument-hint: "show [запис] | health | inbox"
disable-model-invocation: true
---

# /grow-product-manager:context

> **Path rule.** A bare `references/<file>.md` in this file is read from the **shared** `references/` at the plugin root. Resolve the root as `${PLUGIN_ROOT}`, else `${CLAUDE_PLUGIN_ROOT}`, else the directory that contains `skills/`, found by walking up from this folder (`references/host-profiles.md` §6). A bare `skills/<name>/SKILL.md` is read from the same root. Never continue without a protocol named here.

Your context, typed. It does what `context-navigator` does with the same words in conversation (`references/context-protocol.md` §5i, §5j). Every action reads only, except an answer you give to `inbox`.

## What was typed

The first word is the action:

- `show` — what the plugin knows about you: `ctx show`, one line a record, then your answers and the inbox. `show <id …>` adds those records' text.
- `health` — what wants looking after: `ctx health`, ✅ / ⚠ / ✋ a line, each with the command that fixes it.
- `inbox` — what skills proposed: `ctx inbox list`, then one question.
- nothing — `health`, then the inbox's one line.

Any other first word → one line, `Невідома дія: <слово> — /grow-product-manager:context show [запис] | health | inbox`, and stop.

## Run

Step 0-host (`references/host-profiles.md` §3). Without SHELL or without a context store (the session digest shows no `context: records …` line) → one line, `Сховища контексту немає — /context працює зі сховищем; твій local-context.md: <шлях>`, then show `local-context.md`'s section headings and stop.

Otherwise run `python3 "<plugin root>/scripts/ctx.py" <show|health|inbox list>` and give its lines as they are (they are Ukrainian already), with nothing added but, for `inbox`, the question below.

**inbox.** An empty inbox → `Скринька порожня.` and stop. Otherwise show the numbered lines, then ask **one** question: «Прийняти всі / номери (наприклад 1, 3) / відхилити номери / пізніше?» On the answer:
- «так» / «всі» → `ctx inbox accept all --code <код зі списку>`;
- numbers → `ctx inbox accept <номери> --code <код>`;
- «відхилити <номери>» (with a reason if given) → `ctx inbox reject <номери> --code <код> [--reason "<причина>"]`;
- «пізніше» / no answer → nothing.

Exit 4 «скринька змінилась» → run `ctx inbox list` again and ask again; never retry with another code you did not show. After an accept, say what was taken and `Скасувати: ctx undo`. A line «№N не прийнято: …» is said as it is.

The command never proposes a delta itself and never accepts what the user did not choose.
