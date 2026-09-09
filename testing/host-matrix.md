# host-matrix.md — skill × host

> What each of the 29 skills can do on each host profile from `references/host-profiles.md`. **Derived, not hand-typed:** the mode follows from the capabilities the skill's `SKILL.md` actually invokes (quality gate, fan-out reads, debate, Jira/Confluence writes, local storage) crossed with the profile's capability set. Regenerate when a skill gains or drops one of those; validator check 14 requires every skill to appear exactly once.

Legend: **full** — as designed on the reference host · **degraded** — same result through the degraded mode named in the last column (`host-profiles.md` §4) · **n/a** — the skill says so in one line and stops (`host-profiles.md` §5); read-only use still works when the user pastes the data.

**claude-cowork** 29 full / 0 degraded / 0 n/a · **codex-cli** 15 full / 14 degraded / 0 n/a · **chatgpt** 0 full / 19 degraded / 10 n/a · **codex-cloud** 0 full / 20 degraded / 9 n/a

Profiles: `claude-cowork` = Claude Code / Cowork (reference). `codex-cli` = Codex CLI and the Codex desktop app (the app additionally matches connectors by name). `chatgpt` = ChatGPT on web / mobile — skills and connectors only, no filesystem, no shell, no subagents (derived, not measured); the ChatGPT desktop app with a *Local Project* attaches folders read/write — treat it as `codex-cli`. `codex-cloud` = sandbox filesystem that is not the user's `~/.grow-pm/`.

| Skill | claude-cowork | codex-cli | chatgpt | codex-cloud | Degraded mode / reason |
|---|---|---|---|---|---|
| `brainstorm-features` | full | degraded | degraded | degraded | debate: inline role simulation; storage: session mode, export at the end; debate: inline role simulation; config/storage: via connector or the repo, never assume prior state; subagents: as codex-cli |
| `cjm-research` | full | degraded | degraded | degraded | debate: inline role simulation; storage: session mode, export at the end; debate: inline role simulation; config/storage: via connector or the repo, never assume prior state; subagents: as codex-cli |
| `decision-log` | full | degraded | degraded | degraded | debate: inline role simulation; storage: session mode, export at the end; debate: inline role simulation; config/storage: via connector or the repo, never assume prior state; subagents: as codex-cli |
| `delegation-coach` | full | full | n/a | n/a | needs the user's ~/.grow-pm/, not a sandbox FS; needs FS — read-only when the user pastes the data |
| `design-bridge` | full | full | degraded | degraded | storage: session mode, export at the end; config/storage: via connector or the repo, never assume prior state |
| `diagram-prototyper` | full | full | degraded | degraded | storage: session mode, export at the end; config/storage: via connector or the repo, never assume prior state |
| `experiment-tracker` | full | full | n/a | n/a | needs the user's ~/.grow-pm/, not a sandbox FS; needs FS — read-only when the user pastes the data |
| `feedback-triage` | full | degraded | degraded | degraded | fan-out: sequential batches; storage: session mode, export at the end; fan-out: sequential batches; config/storage: via connector or the repo, never assume prior state; subagents: as codex-cli |
| `focus-advisor` | full | degraded | n/a | n/a | fan-out: sequential batches; needs the user's ~/.grow-pm/, not a sandbox FS; needs FS — read-only when the user pastes the data |
| `goal-setter` | full | full | degraded | degraded | storage: session mode, export at the end; config/storage: via connector or the repo, never assume prior state |
| `hiring-designer` | full | full | n/a | n/a | needs the user's ~/.grow-pm/, not a sandbox FS; needs FS — read-only when the user pastes the data |
| `knowledge-library` | full | degraded | n/a | n/a | gate: sequential in-session lenses; needs the user's ~/.grow-pm/, not a sandbox FS; needs FS — read-only when the user pastes the data |
| `meeting-processor` | full | degraded | degraded | degraded | gate: sequential in-session lenses; fan-out: sequential batches; write gate: in-skill confirmation; config/storage: via connector or the repo, never assume prior state; subagents: as codex-cli; write gate: in-skill confirmation; storage: session mode, export at the end; gate: sequential in-session lenses; fan-out: sequential batches; write gate: in-skill confirmation |
| `offboarding-guide` | full | full | n/a | n/a | needs the user's ~/.grow-pm/, not a sandbox FS; needs FS — read-only when the user pastes the data |
| `one-on-one` | full | full | n/a | n/a | needs the user's ~/.grow-pm/, not a sandbox FS; needs FS — read-only when the user pastes the data |
| `performance-review` | full | full | n/a | n/a | needs the user's ~/.grow-pm/, not a sandbox FS; needs FS — read-only when the user pastes the data |
| `plugin-configurator` | full | full | degraded | degraded | storage: session mode, export at the end; config/storage: via connector or the repo, never assume prior state |
| `product-analysis` | full | degraded | degraded | degraded | fan-out: sequential batches; storage: session mode, export at the end; fan-out: sequential batches; config/storage: via connector or the repo, never assume prior state; subagents: as codex-cli |
| `product-reporter` | full | degraded | degraded | degraded | fan-out: sequential batches; storage: session mode, export at the end; fan-out: sequential batches; config/storage: via connector or the repo, never assume prior state; subagents: as codex-cli |
| `product-research` | full | degraded | degraded | degraded | fan-out: sequential batches; debate: inline role simulation; write gate: in-skill confirmation; config/storage: via connector or the repo, never assume prior state; subagents: as codex-cli; write gate: in-skill confirmation; storage: session mode, export at the end; fan-out: sequential batches; debate: inline role simulation; write gate: in-skill confirmation |
| `project-planning` | full | full | degraded | degraded | storage: session mode, export at the end; config/storage: via connector or the repo, never assume prior state |
| `quarterly-planning` | full | degraded | degraded | degraded | write gate: in-skill confirmation; storage: session mode, export at the end; write gate: in-skill confirmation; config/storage: via connector or the repo, never assume prior state; write gate: in-skill confirmation |
| `release-manager` | full | full | n/a | degraded | git/gh from the shell; needs the repository and a shell; config/storage: via connector or the repo, never assume prior state |
| `requirements-creator` | full | degraded | degraded | degraded | gate: sequential in-session lenses; write gate: in-skill confirmation; storage: session mode, export at the end; gate: sequential in-session lenses; write gate: in-skill confirmation; config/storage: via connector or the repo, never assume prior state; subagents: as codex-cli; write gate: in-skill confirmation |
| `roadmap-architect` | full | full | degraded | degraded | storage: session mode, export at the end; config/storage: via connector or the repo, never assume prior state |
| `sprint-planning` | full | full | degraded | degraded | storage: session mode, export at the end; config/storage: via connector or the repo, never assume prior state |
| `task-creator` | full | degraded | degraded | degraded | gate: sequential in-session lenses; write gate: in-skill confirmation; storage: session mode, export at the end; gate: sequential in-session lenses; write gate: in-skill confirmation; config/storage: via connector or the repo, never assume prior state; subagents: as codex-cli; write gate: in-skill confirmation |
| `template-library` | full | full | n/a | n/a | needs the user's ~/.grow-pm/, not a sandbox FS; needs FS — read-only when the user pastes the data |
| `write-concept` | full | degraded | degraded | degraded | gate: sequential in-session lenses; debate: inline role simulation; write gate: in-skill confirmation; config/storage: via connector or the repo, never assume prior state; subagents: as codex-cli; write gate: in-skill confirmation; storage: session mode, export at the end; gate: sequential in-session lenses; debate: inline role simulation; write gate: in-skill confirmation |

## Measured in the v3.0.0 pilot (Codex CLI 0.153.2)

- Shared `references/` resolution from a skill with its own `references/` (write-concept), without (task-creator), a migrated command (status), a different cwd, and a natural activation — 7/7, `Codex-Compat-Findings.md` → Етап 3b.
- Routing: trigger-evals, 102 phrases, on a host listing 80 skills (~190 characters shown per description) — 100 % in two consecutive runs, identical answers.
- Not yet measured per skill: a full artifact run of the `write-concept → requirements-creator → task-creator` chain on Codex with an authorized Atlassian connector (real MCP namespaces).
