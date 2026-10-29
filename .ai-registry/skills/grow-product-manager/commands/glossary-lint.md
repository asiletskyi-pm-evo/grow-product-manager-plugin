---
description: Typed command /grow-product-manager:glossary-lint only — never for a conversational «перевір термінологію» or "check terminology" (that is knowledge-library). Runs the team-language lint (Gate 3 — glossary terms, avoid-list, style profile) over a file or pasted text, standalone.
argument-hint: "[path-to-file]"
disable-model-invocation: true
allowed-tools: Read, Glob, Grep
---

# /grow-product-manager:glossary-lint

> **Path rule.** A bare `references/<file>.md` in this file is read from the **shared** `references/` at the plugin root. Resolve the root as `${PLUGIN_ROOT}`, else `${CLAUDE_PLUGIN_ROOT}`, else the directory that contains `skills/`, found by walking up from this folder (`references/host-profiles.md` §6). Never continue without a protocol named here.

Applies `references/artifact-style-gate.md` → **Gate 3 (Team language)**, lint half only, to text the user supplies. No preamble, no rewrite, no artifact — a findings list.

## Input

- If the user typed a file path after the command name → read that file.
- If they typed nothing → lint the text in the user's last message (or ask for it if the message is only the command).

## Steps

1. Load the glossary and style profile through `knowledge-library` (team-language contour: `terms`, `phrases`, `avoid`, style profile). If none is configured — say so in one line and stop; do not invent terms.
2. Lint per Gate 3b: wrong term where a glossary term exists, `avoid`-list hits, style-profile violations (`lint_mode` from the Terminology & Style section decides strict vs advisory).
3. Report as a table — location (line / heading), found, expected (glossary term or rule), severity — followed by the one-line count — "Terminology: N findings (critical: K)" — rendered in `user.language`.

Nothing is written anywhere. To fix the text, the user runs the producing skill again or edits by hand.
