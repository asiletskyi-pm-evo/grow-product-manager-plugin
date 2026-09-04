---
description: Run the team-language lint (Gate 3 — glossary terms, avoid-list, style profile) over a file or pasted text, standalone, without generating anything
argument-hint: "[path-to-file]"
disable-model-invocation: true
allowed-tools: Read, Glob, Grep
---

# /grow-product-manager:glossary-lint

Applies `references/artifact-style-gate.md` → **Gate 3 (Team language)**, lint half only, to text the user supplies. No preamble, no rewrite, no artifact — a findings list.

## Input

- `$1` is a path → read that file.
- No argument → lint the text in the user's last message (or ask for it if the message is only the command).

## Steps

1. Load the glossary and style profile through `knowledge-library` (team-language contour: `terms`, `phrases`, `avoid`, style profile). If none is configured — say so in one line and stop; do not invent terms.
2. Lint per Gate 3b: wrong term where a glossary term exists, `avoid`-list hits, style-profile violations (`lint_mode` from the Terminology & Style section decides strict vs advisory).
3. Report as a table — location (line / heading), found, expected (glossary term or rule), severity — followed by the one-line count — "Terminology: N findings (critical: K)" — rendered in `user.language`.

Nothing is written anywhere. To fix the text, the user runs the producing skill again or edits by hand.
