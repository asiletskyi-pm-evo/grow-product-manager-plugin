# Test Case Registry — Grow PM Plugin

> Updated EVERY release: new cases for new/changed skills + regression for affected ones. Format — see `Testing-process.md`. Status is filled in when a stage runs.

## Release v2.0.2 — audit remediation P2 (structural drift)

> **Run 2026-07-14 — verdict: GREEN.** 13 checks, 0 FAIL. The three new checks were verified by injection (one defect per class into a repo copy): all three caught, clean repo stays green.

### Stage 1 — Static lint (new checks)
- **TC-lint-vault-types** | all skills + vault-schema | every `vault_save` type exists in the taxonomy AND TYPE_FOLDER_MAP | check `vault-types` | expected: 0 FAIL | **pass** (was: `feedback-triage` in the taxonomy but unmapped — no resolvable folder; `report-3t5f`, `presentation`, `prototype`, `handoff`, `vacancy-profile` and all 7 People types undefined)
- **TC-lint-artifact-types** | all skills + template-protocol | every Step T `artifact_type` is in the enum | check `artifact-types` | expected: 0 FAIL | **pass** (was: `roadmap`, `meeting-notes`, `focus`, `delegation-audit` declared but absent — no wizard path to a custom template)
- **TC-lint-chain-contracts** | all skills | a claimed `← X` edge exists on X's side, or X is one this skill calls | check `chain-contracts` | expected: 0 FAIL | **pass** (was: experiment-tracker unreachable; found 3 further one-sided claims on first run)

### Stage 4 — Integration (the contracts the new checks now guard)
- **TC-int-202-tracker** | brainstorm-features / requirements-creator / focus-advisor → experiment-tracker | the tracker is reachable from the pipeline | expected: all three chain in | **pass** (register after ICE ranking; A/B spec → `specced` with its Decision Rule; focus-advisor routes readout through the state owner instead of past it)
- **TC-int-202-decisions** | meeting-processor / quarterly-planning / project-planning → decision-log | decisions reach the log | expected: all three chain in | **pass** (meeting-processor no longer hand-writes `Decisions/`)
- **TC-int-202-vault** | vault-protocol ↔ vault-schema ↔ obsidian-setup-guide | one layout, one path rule | expected: init, save, search and the smoke tests all agree | **pass** (setup guide's four smoke tests previously tested a layout the init algorithm never produced)

### Stage 5 — Regression
- **TC-reg-202-paths** | 13 changed skills | every save target resolves under the new layout | expected: no orphaned path | **pass** (People skills already wrote `People/…`; the protocol's wikilinks were the outlier and now match)

---

## Release v2.0.1 — audit remediation + validator hardening

> **Run 2026-07-14 — verdict: GREEN.** Both validators pass; every case below is now automated in `skill_lint.py`, so it re-runs on every PR rather than being re-checked by hand.
>
> **Why this section exists.** The v2.0.0 audit found 5 critical + 14 major defects that both validators passed green. Worse, `TC-reg-rename-02` below was marked **pass** in v1.15.0 while `Feature-task-creator` was still live in `meeting-processor` — a hand-run check that reported the wrong answer. Every case here is therefore stated as a *linter check name*, not as a manual step.

### Stage 1 — Static lint (each case = one `skill_lint.py` check)
- **TC-lint-fm-yaml** | all 29 SKILL.md | frontmatter parses under a STRICT YAML parser, not just Claude Code's lenient one | check `frontmatter-yaml` | expected: 0 FAIL | **pass** (was 28/29 failing: unquoted `Українською: ` terminates a plain scalar)
- **TC-lint-fm-desc** | all 29 SKILL.md | `description` ≤ 1024 chars (the field the model routes on) | check `frontmatter-fields` | expected: 0 FAIL | **pass** (was 4 over: product-reporter 1289, focus-advisor 1210, hiring-designer 1121, performance-review 1077)
- **TC-lint-paths** | SKILL.md + all reference bodies | every cited path resolves, incl. multi-segment, `.yaml`, placeholders, skill-local, and `references/examples/**` | check `ref-paths` | expected: 0 FAIL | **pass** (was blind to `references/builtin-templates/<subtype>.md` — a dir that never existed)
- **TC-lint-ghost** | SKILL.md + references | no chain target that is not a real skill | check `ghost-skill` | expected: 0 FAIL | **pass** (was: `people-context` in hiring-designer, `write-spec` ×2 in onboarding-steps)
- **TC-lint-stale** | repo minus CHANGELOG history | renames are complete | check `stale-names` | expected: 0 FAIL | **pass** (was: `Feature-task-creator` in meeting-processor — the defect TC-reg-rename-02 missed)
- **TC-lint-dup-h1** | all reference docs | no doc contains itself twice | check `duplicate-h1` | expected: 0 FAIL | **pass** (was: vault-protocol.md 1435→751, persistent-storage.md 699→426)
- **TC-lint-readme** | README ↔ frontmatter | per-skill versions agree | check `readme-versions` | expected: 0 FAIL | **pass** (was 16 stale + a section contradicting the summary table in the same file)
- **TC-lint-org** | example file, templates, references, skills | no real org identifiers, Atlassian hosts, or non-placeholder emails | check `org-data` | expected: 0 FAIL | **pass** (was: real roster, board id, epic keys, VIP name+email in `local-context.example.md`)
- **TC-lint-deck** | deck-subtypes.yaml ↔ built-in templates | subtype keys agree | check `deck-subtypes` | expected: 0 FAIL | **pass** (was: yaml `feature-concept` vs template `feature`, callers passing the yaml's name)

### Stage 5 — Regression
- **TC-reg-201-fm** | all 29 skills | trigger phrases and "Do NOT use" boundaries preserved after the frontmatter rewrite | expected: no trigger lost | **pass** (rephrasing only — `Українською: ` → `Українською — `; the 4 trimmed descriptions kept every phrase)
- **TC-reg-201-subtype** | write-concept, requirements-creator, design-bridge, deck-subtypes.yaml, presentation/feature-v1 | one canonical deck subtype end-to-end | expected: `feature` everywhere | **pass**
- **TC-reg-201-ci** | validate.yml ↔ release.yml | the PR gate runs exactly what the release gate runs | expected: both run consistency + lint | **pass** (validate.yml previously omitted skill_lint.py — a PR could go green and fail the auto-release)

---

## Release v1.15.0 — planning suite + Task Creator rename

> **Run 2026-06-29 — verdict: GREEN** (condition: final lint TC-lint-002/003 on the full clone before push).
> - Stage 1 lint: 0 FAIL (4 new skills); WARN = external references (resolved after merge).
> - Stage 2 trigger: 19/20 pass; 1 LOW risk (quarterly "quarter retro" ↔ product-reporter `quarter-review` on a short phrase).
> - Stage 3 scenario: 4/4 pass (all key steps/gates/artifacts present).
> - Stage 4 integration: pass — chains to `task-creator`; product-reporter delegation consistent; project↔quarterly bidirectional; product-reporter+jira-data-protocol confirmed in repo v1.14.0 (web_fetch), absent from the local session cache (stale snapshot).
> - Stage 5 regression: pass — 0 mentions of feature-task-creator in the new files.
> - Backup: `_backups/v1.15.0-snapshot-*` (workspace); git tag pre-v1.15.0 — user step.
> - Deferred to v1.15.1: minor roadmap-architect numbering inconsistency (0-5 vs 4 modes); clarify the "retro" trigger.


### Stage 1 — Static lint
- **TC-lint-001** | all skills/*/SKILL.md | frontmatter+semver+name==folder → `skill_lint.py` | expected: 0 FAIL | **pass** (4 new: GREEN; external references = WARN, expected)
- **TC-lint-002** | full repo after merge | all references of cited skills resolve | expected: 0 unresolved | status: run in the repo
- **TC-lint-003** | repo | skill_version in the body == frontmatter (catches audit bugs) | expected: 0 mismatch | status: run in the repo (expected to catch cjm/product-analysis/write-concept)

### Stage 2 — Trigger eval (new skills)
- **TC-trig-quarterly-01** | quarterly-planning | "build a roadmap for the quarter" / "what the team can deliver" | expected: triggers quarterly-planning |
- **TC-trig-quarterly-02 (neg)** | quarterly-planning | "report on the quarter, what got done" | expected: does NOT hijack; this is product-reporter quarter-review |
- **TC-trig-project-01** | project-planning | "how long will the project take", "critical path", "replan" | expected: project-planning |
- **TC-trig-sprint-01** | sprint-planning | "what can we pull into the sprint", "who takes the tasks" | expected: sprint-planning |
- **TC-trig-sprint-02 (neg)** | sprint-planning | "sprint report, what we closed" | expected: product-reporter sprint-review |
- **TC-trig-arch-01** | roadmap-architect | "tidy up the structure", "roadmap tree" | expected: roadmap-architect |

### Stage 3 — Scenario walk (new skills)
- **TC-scn-quarterly-01** | quarterly-planning full | mock local-context Planning + quarter retro | expected: steps 0-6 present, capacity-gate on platform slices, quarter-review delegation, artifacts after approval |
- **TC-scn-project-01** | project-planning replan | mock arc + actuals | expected: backlog=remaining−committed, re-sequence for the critical path, drift vs baseline |
- **TC-scn-sprint-01** | sprint-planning groom | mock Development Flow + previous sprint | expected: focuses, per-member capacity, carryover-risk, readiness scan (work-type DAG), violation detection, assignee proposals |
- **TC-scn-arch-01** | roadmap-architect audit | mock layout with gaps | expected: gap report (missing quarter/goal/code, orphans), write only after approval |

### Stage 4 — Integration
- **TC-int-01** | quarterly-planning → task-creator | approved plan → tasks | expected: chain exists, task-creator (not feature-task-creator) |
- **TC-int-02** | planning ↔ product-reporter | delegation of quarter/sprint/member/initiative review | expected: reuse of jira-data-protocol, no duplicate fetch |
- **TC-int-03** | project-planning ↔ quarterly-planning | arcs+% allocation downward, actuals+carryover → replan upward | expected: bidirectional link |
- **TC-int-04** | all new skills | resolution of shared references (capacity/dependency/planning-core/roadmap-artifacts + external) | expected: all resolve in the full repo |

### Stage 5 — Regression (affected rename + neighbors)
- **TC-reg-rename-01** | task-creator | name==folder, H1, description updated; old folder gone | expected: pass |
- **TC-reg-rename-02** | write-concept, requirements-creator, cjm-research, meeting-processor, diagram-prototyper, plugin-configurator, local-context-protocol, README, CHANGELOG | all feature-task-creator mentions → task-creator (except CHANGELOG history) | expected: 0 leftovers outside CHANGELOG history |
- **TC-reg-trig-01** | task-creator | old trigger phrases ("create tasks from requirements") still trigger | expected: pass (invocation not broken) |
- **TC-reg-existing-01** | top-5 existing skills (cjm, product-analysis, requirements, meeting, design-bridge) | behavior as before v1.15 (planning suite additive) | expected: no regressions |

---

## Future releases (placeholders)
- **v1.16.0 quick fixes** — cases for the 8 bugfixes from the audit (design-bridge subtype, product-analysis Step 0h, skill_version ×3, product-reporter sprint-id, configurator duplicates, template-library count).
- **v1.17.0 dedup** — regression on the skills whose canon was extracted into references.
- **v1.18.0 configurator refactor** — full plugin-configurator regression + subagent processes.
