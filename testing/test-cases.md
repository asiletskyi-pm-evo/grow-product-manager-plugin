# Test Case Registry — Grow PM Plugin

> Updated EVERY release: new cases for new/changed skills + regression for affected ones. Format — see `Testing-process.md`. Status is filled in when a stage runs.

## Release v1.15.0 — planning suite + Task Creator rename

> **Run 2026-06-29 — verdict: GREEN** (condition: final lint TC-lint-002/003 on the full clone before push).
> - Stage 1 lint: 0 FAIL (4 new skills); WARN = external references (resolved after merge).
> - Stage 2 trigger: 19/20 pass; 1 LOW risk (quarterly "quarter retro" ↔ team-ops `quarter-review` on a short phrase).
> - Stage 3 scenario: 4/4 pass (all key steps/gates/artifacts present).
> - Stage 4 integration: pass — chains to `task-creator`; team-ops-reporter delegation consistent; project↔quarterly bidirectional; team-ops-reporter+jira-data-protocol confirmed in repo v1.14.0 (web_fetch), absent from the local session cache (stale snapshot).
> - Stage 5 regression: pass — 0 mentions of feature-task-creator in the new files.
> - Backup: `_backups/v1.15.0-snapshot-*` (workspace); git tag pre-v1.15.0 — user step.
> - Deferred to v1.15.1: minor roadmap-architect numbering inconsistency (0-5 vs 4 modes); clarify the "retro" trigger.


### Stage 1 — Static lint
- **TC-lint-001** | all skills/*/SKILL.md | frontmatter+semver+name==folder → `skill_lint.py` | expected: 0 FAIL | **pass** (4 new: GREEN; external references = WARN, expected)
- **TC-lint-002** | full repo after merge | all references of cited skills resolve | expected: 0 unresolved | status: run in the repo
- **TC-lint-003** | repo | skill_version in the body == frontmatter (catches audit bugs) | expected: 0 mismatch | status: run in the repo (expected to catch cjm/product-analysis/write-concept)

### Stage 2 — Trigger eval (new skills)
- **TC-trig-quarterly-01** | quarterly-planning | "build a roadmap for the quarter" / "what the team can deliver" | expected: triggers quarterly-planning |
- **TC-trig-quarterly-02 (neg)** | quarterly-planning | "report on the quarter, what got done" | expected: does NOT hijack; this is team-ops-reporter quarter-review |
- **TC-trig-project-01** | project-planning | "how long will the project take", "critical path", "replan" | expected: project-planning |
- **TC-trig-sprint-01** | sprint-planning | "what can we pull into the sprint", "who takes the tasks" | expected: sprint-planning |
- **TC-trig-sprint-02 (neg)** | sprint-planning | "sprint report, what we closed" | expected: team-ops-reporter sprint-review |
- **TC-trig-arch-01** | roadmap-architect | "tidy up the structure", "roadmap tree" | expected: roadmap-architect |

### Stage 3 — Scenario walk (new skills)
- **TC-scn-quarterly-01** | quarterly-planning full | mock local-context Planning + quarter retro | expected: steps 0-6 present, capacity-gate on platform slices, quarter-review delegation, artifacts after approval |
- **TC-scn-project-01** | project-planning replan | mock arc + actuals | expected: backlog=remaining−committed, re-sequence for the critical path, drift vs baseline |
- **TC-scn-sprint-01** | sprint-planning groom | mock Development Flow + previous sprint | expected: focuses, per-member capacity, carryover-risk, readiness scan (work-type DAG), violation detection, assignee proposals |
- **TC-scn-arch-01** | roadmap-architect audit | mock layout with gaps | expected: gap report (missing quarter/goal/code, orphans), write only after approval |

### Stage 4 — Integration
- **TC-int-01** | quarterly-planning → task-creator | approved plan → tasks | expected: chain exists, task-creator (not feature-task-creator) |
- **TC-int-02** | planning ↔ team-ops-reporter | delegation of quarter/sprint/member/initiative review | expected: reuse of jira-data-protocol, no duplicate fetch |
- **TC-int-03** | project-planning ↔ quarterly-planning | arcs+% allocation downward, actuals+carryover → replan upward | expected: bidirectional link |
- **TC-int-04** | all new skills | resolution of shared references (capacity/dependency/planning-core/roadmap-artifacts + external) | expected: all resolve in the full repo |

### Stage 5 — Regression (affected rename + neighbors)
- **TC-reg-rename-01** | task-creator | name==folder, H1, description updated; old folder gone | expected: pass |
- **TC-reg-rename-02** | write-concept, requirements-creator, cjm-research, meeting-processor, diagram-prototyper, plugin-configurator, local-context-protocol, README, CHANGELOG | all feature-task-creator mentions → task-creator (except CHANGELOG history) | expected: 0 leftovers outside CHANGELOG history |
- **TC-reg-trig-01** | task-creator | old trigger phrases ("create tasks from requirements") still trigger | expected: pass (invocation not broken) |
- **TC-reg-existing-01** | top-5 existing skills (cjm, product-analysis, requirements, meeting, design-bridge) | behavior as before v1.15 (planning suite additive) | expected: no regressions |

---

## Future releases (placeholders)
- **v1.16.0 quick fixes** — cases for the 8 bugfixes from the audit (design-bridge subtype, product-analysis Step 0h, skill_version ×3, team-ops-reporter sprint-id, configurator duplicates, template-library count).
- **v1.17.0 dedup** — regression on the skills whose canon was extracted into references.
- **v1.18.0 configurator refactor** — full plugin-configurator regression + subagent processes.
