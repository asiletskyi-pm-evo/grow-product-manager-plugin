---
description: Typed command /grow-product-manager:context only — never for a conversational «що ти про мене знаєш» (that is context-navigator). show · health · inbox · recheck · consolidate · overlay (your corrections to a core) · history (what changed, a note a month) · audit (your vault's links).
argument-hint: "show [запис] | health | inbox | recheck | consolidate | overlay | history [YYYY-MM] | audit"
disable-model-invocation: true
---

# /grow-product-manager:context

> **Path rule.** A bare `references/<file>.md` in this file is read from the **shared** `references/` at the plugin root. Resolve the root as `${PLUGIN_ROOT}`, else `${CLAUDE_PLUGIN_ROOT}`, else the directory that contains `skills/`, found by walking up from this folder (`references/host-profiles.md` §6). Never continue without a protocol named here.

Your context, typed — what `context-navigator` does with the same words. No record is written before your «так».

## What was typed

The first word is the action — `show [id …]`, `health`, `inbox`, `recheck`, `consolidate`, `overlay`, `history [YYYY-MM]`, `audit`; nothing → `health`, then the inbox's one line. What each runs, the one question it may ask and what it never does: **`references/context-protocol.md` §5q** — read it before the first step.

Any other first word → one line, `Невідома дія: <слово> — /grow-product-manager:context show [запис] | health | inbox | recheck | consolidate | overlay | history | audit`, and stop.

## Run

Step 0-host (`references/host-profiles.md` §3). Without SHELL, or without a context store (no `context: records …` digest line; without the digest, no `{storage_root}/_System/context/.state/`; `ctx health` exit 3 `no store at …`) — one line, `Сховища контексту немає — /context працює зі сховищем; твій local-context.md: <шлях>`, then show `local-context.md`'s section headings and stop. `overlay` without SHELL reads `{store}/overlays/*.yaml` as text and says what each correction does (§5q).

Otherwise run `python3 "<plugin root>/scripts/ctx.py" …` as §5q says for the action and give its lines as they are (they are Ukrainian already), with nothing added but the action's one question.

Every write waits for the user's answer to that question and goes with the code the command printed; exit 4 («змінилась») → show again and ask again, never retry with a code you did not show. After a write, say what changed and `Скасувати: ctx undo`.

Beyond what `recheck` and `consolidate` hand to the inbox, the command never proposes a delta, never accepts what the user did not choose, and never writes into a repository's folder.
