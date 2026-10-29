# .codex/agents

Codex-format ports of the three plugin agents in `agents/`. They exist because Codex does not load `agents/*.md` from a plugin — the definitions would otherwise be unreachable on that host.

## How they are used

**Codex spawns a subagent only when the user explicitly asks for one.** Nothing here runs automatically, and no skill can rely on it: for skills, the default on Codex is that the SUBAGENT capability is absent (`references/host-profiles.md` §1), which routes the quality gate to sequential in-session lens passes and fan-out reads to sequential batches. These files are for a user who wants to run one of the three roles by hand.

| Agent | Run it when |
|---|---|
| `artifact-checker` | you want an independent pass over a finished draft against the gate checklists (`references/artifact-style-gate.md`) |
| `debater` | you are running a role debate by hand (`references/debate-protocol.md`) — one invocation per role, per round |
| `extractor` | you want one batch of many items read into a fixed row schema (`references/subagent-delegation.md`) |

## Independence is weaker here than on Claude

On Claude the checker's `tools: Read` and the debater's empty tool list are enforced by the host, so their independence is a property of the runtime rather than a promise in prose. Codex has no equivalent per-agent tool restriction; `sandbox_mode = "read-only"` blocks writes but does not narrow the tool set. Treat a finding produced here as one notch less independent, and say so in the gate report line the same way the sequential in-session mode does.

## Regenerating

These files are generated from `agents/*.md` — the frontmatter `description` and the body, with a host note prepended about resolving `${PLUGIN_ROOT}`. `agents/*.md` stays the source of truth: change it there, then regenerate, and never let the two drift.
