# AGENTS.md

Standing instructions for an agent working in this repository, or running the plugin installed from it, on a host that reads `AGENTS.md` (Codex CLI and others). Claude Code reads the plugin manifests directly and does not need this file.

This is not a second README. `README.md` explains the product to a person; this file tells an agent how to behave.

## What this repository is

The **Grow Product Manager** plugin — a set of skills for a product manager's daily work, grouped in five contours: Product (research, concepts, requirements, tasks, CJM, analysis, experiments), Delivery (roadmap, quarter, sprint, reports, releases), Knowledge (library, decisions, feedback, meetings, templates), People (goals, 1-1s, reviews, hiring, delegation) and Design (diagrams, prototypes, handoff). There is no application code to build or run: the plugin is markdown protocols plus a few deterministic Python scripts.

## Where things live

| Path | What |
|---|---|
| `skills/<name>/SKILL.md` | one skill; the frontmatter `description` is what routes to it |
| `skills/<name>/references/` | protocols used by that skill alone |
| `references/*.md` | **shared protocols**, used across skills — the substance of the plugin |
| `agents/*.md` | tool-restricted subagents (checker, debater, extractor) |
| `commands/*.md` | user-invoked service commands |
| `hooks/`, `scripts/` | host hooks and the deterministic scripts they call |
| `testing/` | `validate-consistency.sh`, `skill_lint.py` and the eval sets |

A bare `references/<file>.md` in a skill means the **shared** folder at the plugin root, not the skill's own. When a relative read of it fails, resolve the plugin root through `${PLUGIN_ROOT}` → `${CLAUDE_PLUGIN_ROOT}` → the directory that contains `skills/` (`references/host-profiles.md` §6) and read it from there. Do not silently continue without a protocol the skill named.

## Step 0h — do this before the first real step of any skill

Hosts differ in what they can do. Branch on an **observed capability**, never on a brand name:

1. Look at the tool list actually available in this session.
2. Mark five capabilities present or absent: **FS** (a filesystem the user's data survives in), **SHELL** (running commands), **SUBAGENT** (spawning an independent agent), **MCP** (connector tools), **HOOKS** (host-side gates).
3. Carry that mark for the whole run; do not re-derive it per step.

Then resolve the contours that depend on it — storage mode, delegation level, quality-gate mode. The full protocol, the degradation matrix and the contours that have no meaningful degraded mode are in **`references/host-profiles.md`**. Read it before deciding anything about storage, subagents or scripts.

When a capability the user's request needs is absent, say so in one line at the start and continue. Never fail silently, and never repeat the caveat at every step.

## Before gathering any data

Read and follow **`references/data-policy.md`**. It is not optional and it is not skill-specific. Internal data — analytics, dashboards, research material, ticket contents, person profiles — stays inside the session and inside the user's own connected tools. Do not pass it to an external model or a third-party service, whichever integration path you took to obtain it.

Person profiles are stricter still: `references/people-context-protocol.md` keeps them local by design.

## Known gaps on Codex CLI

Measured, not assumed. Work with them rather than around them:

1. **Skill descriptions are truncated at roughly 530 characters.** Anything a skill needs *for routing* lives in the first 500; the rest of its triggers and boundaries are in the body of `SKILL.md`. If a skill looks wrong for the request, read its body before rejecting it.
2. **`agents/*.md` are not loaded.** Codex spawns a subagent only when the user explicitly asks for one, so treat SUBAGENT as absent by default: the quality gate runs as sequential in-session lens passes with a role reset between them, and fan-out reads run as sequential batches. See `references/artifact-style-gate.md` and `references/subagent-delegation.md`. Manual equivalents of the three agents are in `.codex/agents/`.
3. **`hooks/hooks.json` is not loaded** ([openai/codex#17331](https://github.com/openai/codex/issues/17331)). Two consequences: the SessionStart context digest is absent, so run `references/local-context-protocol.md` Step 0a in full; and there is no host write gate, so ask the user for confirmation yourself immediately before writing to Jira or Confluence, showing the three-point checklist from `references/artifact-style-gate.md`.
4. **`${CLAUDE_PLUGIN_ROOT}` is not defined here.** A literal `${...}` left in text means the host did not expand it — that is signal, not an error to hide. Use the resolution order above.

## Working in this repository

- `bash testing/validate-consistency.sh` and `python3 testing/skill_lint.py` must both stay green. Run them before proposing a change as finished.
- Version numbers live in four places at once (`plugin.json`, `marketplace.json`, `README.md`, `CHANGELOG.md`) and are bumped by the `release-manager` skill, never by hand.
- Protocol content belongs in `references/`; a skill that starts explaining a protocol inline is drifting.
