---
description: Typed command /grow-product-manager:release only — never for a conversational «зарелізь плагін» (that is release-manager) and never for product feature releases in Jira. Starts the plugin release pipeline (release-manager) with the bump class already chosen.
argument-hint: "[patch|minor|major]"
disable-model-invocation: true
allowed-tools: Read, Glob, Grep, Bash(git:*), Bash(bash:*), Bash(python3:*), Skill, AskUserQuestion
---

# /grow-product-manager:release

Invokes the `release-manager` skill. The only thing this command adds is the bump class the user typed after the command name, which answers release-manager's Step 2 (classification) up front; every other step — pre-flight guards, the four mandatory version places, CHANGELOG, validator run, gated commit / PR / merge / GitHub Release / mirror sync — runs exactly as the skill defines it.

- The user typed one of `patch | minor | major` → pass it as the pre-selected classification; release-manager still shows the diff summary and asks the user to confirm the class.
- The user typed nothing → let release-manager classify from the diff.
- Anything else → list the three accepted values and stop.

This command is user-only (`disable-model-invocation: true`) on purpose: "release the feature" in a product conversation must never land here.
