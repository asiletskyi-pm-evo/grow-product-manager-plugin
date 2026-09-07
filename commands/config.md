---
description: Open plugin-configurator directly in Validate or View mode without going through mode detection
argument-hint: "[validate|view]"
disable-model-invocation: true
allowed-tools: Read, Glob, Grep, Skill, AskUserQuestion
---

# /grow-product-manager:config

Thin entry point into `plugin-configurator`'s maintenance modes. It exists so the user can reach a specific mode by name instead of describing it — and so that a phrase like "show my config" is never routed here automatically.

## Routing

If the user typed a mode after the command name, use it; if they typed nothing, treat it as `view`.

- `validate` → invoke the `plugin-configurator` skill and state up front: **mode = Validate** (`references/maintenance-modes.md` → V-1..V-6). Produce the readiness report.
- `view`, or nothing typed → invoke `plugin-configurator`, **mode = View** (VW-1..VW-4).
- Anything else → answer with the two accepted values and stop.

## Rules

- Never start Onboarding or Reinstall from here. If `local-context.md` is missing, say so and tell the user to run `plugin-configurator` itself — its own rule ordering decides between recovery and fresh onboarding (`references/local-context-protocol.md` Step 0b).
- Pass no other assumptions into the skill; the skill's Changelog Protocol and gates apply unchanged.
