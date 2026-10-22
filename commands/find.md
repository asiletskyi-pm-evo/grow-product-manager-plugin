---
description: Typed command /grow-product-manager:find only — never for a conversational «знайди…» or "search my notes" (that is context-navigator). Searches your notes, connected cores and local indexes; --list for notes, --all adds live sources.
argument-hint: "<запит> [--list] [--all]"
disable-model-invocation: true
---

# /grow-product-manager:find

> **Path rule.** A bare `references/<file>.md` in this file is read from the **shared** `references/` at the plugin root. Resolve the root as `${PLUGIN_ROOT}`, else `${CLAUDE_PLUGIN_ROOT}`, else the directory that contains `skills/`, found by walking up from this folder (`references/host-profiles.md` §6). A bare `skills/<name>/SKILL.md` is read from the same root. Never continue without a protocol named here.

The search the user asks for, typed. It does what `context-navigator` does with the same words in conversation (`references/search-protocol.md` §13). The command only fixes the form and the reach up front.

## What was typed

The words after the command are the request. A flag is one of two exact words standing on its own — inside quotes it is part of the request:

- `--list` — the list of notes instead of an answer (§13, the list);
- `--all` — the session's live sources too, at once (§13, level 2). Typing it answers §8's question about the breadth. A VPN or a login the session lacks, and mail, person profiles or private channels, are still asked about first.

Any other word that starts with `--` or `—` → one line, `Невідомий прапорець: <слово> — /grow-product-manager:find <запит> [--list] [--all]`, and stop. No words besides the flags → `Що шукати? /grow-product-manager:find <запит> [--list] [--all]`, and stop.

## Run

Follow `skills/context-navigator/SKILL.md` whole, with this request as the question: Step 0 and the start-of-session steps, «On each question», the Quality Standards and «What not to do». The flags fix two things there:
- the form: the list when `--list` was typed, else the form the wording asks for;
- the reach: level 2 at once when `--all` was typed.

End, as §13 says, with `Де шукав: …`.

The command writes nothing but what that search writes: the choices §10 remembers (an opened line of the list, a number or «не те» answered in the block of variants, a `forget`), and the search's own index, refreshed as §3 says.
