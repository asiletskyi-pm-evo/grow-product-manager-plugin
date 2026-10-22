---
description: Typed command /grow-product-manager:find only — never for a conversational request (that is context-navigator, which answers the same way). Searches your context — your vault, every connected core, local indexes — and answers with sources and dates; --list gives notes instead of an answer, --all adds the session's live sources.
argument-hint: "<запит> [--list] [--all]"
disable-model-invocation: true
---

# /grow-product-manager:find

> **Path rule.** A bare `references/<file>.md` in this file is read from the **shared** `references/` at the plugin root. Resolve the root as `${PLUGIN_ROOT}`, else `${CLAUDE_PLUGIN_ROOT}`, else the directory that contains `skills/`, found by walking up from this folder (`references/host-profiles.md` §6). Never continue without a protocol named here.

The search the user asks for, typed. It does exactly what `context-navigator` does with the same words in conversation (`references/search-protocol.md` §13); the command only fixes the form and the reach up front.

## What was typed

The words after the command are the request. Two flags may stand anywhere among them and are not part of the request:

- `--list` — the list of notes instead of an answer (§13, the list);
- `--all` — the session's live sources too, at once (§13, level 2), with the questions of §8 still asked first.

No words besides the flags → one line, `Що шукати? /grow-product-manager:find <запит> [--list] [--all]`, and stop.

## Run

Follow `skills/context-navigator/SKILL.md`: its Step 0 and its start-of-session steps as it says, then `references/search-protocol.md` §13 with this request — the list form when `--list` was typed, else the form the wording asks for; level 2 at once when `--all` was typed. End, as §13 says, with `Де шукав: …`.

This command writes nothing but what §13 itself may: the remembered pick when the user opens a line of the list (§10).
