# Test Case Registry — Grow PM Plugin

> Cases for new/changed skills + regression for affected ones; format — see `Testing-process.md`. Status is filled in when a stage runs.
>
> **This registry is not exhaustive** — see "Coverage gaps" at the bottom. A defect class belongs in `skill_lint.py` as a check, not here as a case: a hand-run case can report "pass" while the defect is live (that is how `TC-reg-rename-02` missed a stale name). Add cases only for what a static check genuinely cannot see.

## Release v2.6.0 — host hooks (SessionStart digest, PreToolUse write gate)

> **Static stages run 2026-09-04 — verdict: fill after the local run.** Stage 3 needs the `.plugin` installed; hooks are the one component whose behavior depends on *where* the session runs (local VM vs hosted container), so the same test is run in both.

### Stage 1 — Static lint (new checks)
- **TC-val-260-hooks** | `hooks/hooks.json` + `scripts/` | valid JSON, events from the official list, every hook has `timeout`, every command points at an existing executable script, `.py` files compile | validator check 11 | expected: 2 hooks wired, 0 FAIL
- **TC-val-260-counts** | manifests + README | `29 skills, 3 agents, 5 commands, 6 connectors, 2 hooks` | check 10 | expected: 0 FAIL
- **TC-lint-260-scope** | `scripts/*.py`, `scripts/*.sh` | org-data / org-signature / locale rules apply | `skill_lint.py` | expected: 0 FAIL

### Stage 2 — Script fixtures (run in the cloud clone, 2026-09-04 — pass)
- **TC-hook-260-found** | `session_start.py` with `local-context.example.md` at `$HOME/mnt/grow-pm/` | digest lists path, mode, language, 2 products, 1 team, flags, deferred steps; `GROW_PM_CONTEXT_PATH` appended to `$CLAUDE_ENV_FILE` | **pass**
- **TC-hook-260-rank** | two connected copies (`$HOME/mnt/a-docs/` stale export, `$HOME/mnt/grow-pm/` store) | the `grow-pm` copy wins; the other is listed as "Other copies seen" — found live on the Mac VM, where the workspace folder held a v1.6.0 export | **pass**
- **TC-hook-260-notfound** | no file anywhere | 3-line NOT VISIBLE digest naming searched locations; exit 0 | **pass**
- **TC-hook-260-failopen** | garbage on stdin | exit 0, still emits a digest | **pass**
- **TC-gate-260-create** | `createConfluencePage` | `permissionDecision: ask` with the 3-point reason | **pass**
- **TC-gate-260-meta** | `editJiraIssue` with labels only | no output (allow) | **pass**
- **TC-gate-260-content** | `editJiraIssue` with a 300-char description | `ask` | **pass**
- **TC-gate-260-off** | `setup.py --write-gate off` then `createJiraIssue` | no output; `--write-gate on` restores | **pass**
- **TC-gate-260-other** | tool `Bash` | no output (defensive against a loose matcher) | **pass**

### Stage 3 — Host behavior (install the `.plugin`)
- **TC-host-260-tab** | plugin card | **Hooks · 2** tab lists "Session start" and a PreToolUse entry | expected: visible
- **TC-host-260-local** | a local Cowork session with the `grow-pm` folder connected | the first assistant turn has the `GROW_PM_SESSION … FOUND at $HOME/mnt/grow-pm/local-context.md` digest; a skill's Step 0a takes the path without searching | expected: FOUND
- **TC-host-260-hosted** | a hosted (cloud) session | digest says NOT VISIBLE; a skill still reads the context through device tools and does **not** start onboarding | expected: no false onboarding
- **TC-host-260-compact** | a long session that compacts | the digest re-appears after compaction (matcher `compact`) | expected: re-injected
- **TC-host-260-ask** | `createConfluencePage` in the sandbox space | the host shows the write-gate prompt with the checklist; Cancel aborts the write | expected: prompt shown
- **TC-host-260-setup** | `/grow-product-manager:setup --write-gate off` → same write | no prompt; `--show` reports `write_gate: off` and the hooks env flags | expected: silent
- **TC-host-260-cli** | Claude Code CLI on the Mac | both hooks behave as in the local Cowork session (`~/.grow-pm/` found directly) | expected: FOUND, prompt shown

### Stage 5 — Regression
- **TC-reg-260** | Groups B / D / F / L | no routing change (no skill description edited) | expected: 100%

## Release v2.5.0 — plugin components (connectors, agents, commands)

> **Static stages run 2026-09-04 in the dev repo — verdict: GREEN.** Validator 10 check groups 0 FAIL; `skill_lint.py` 18 checks GREEN with the org denylist active; seeded-leak test 12/12. Trigger eval Group L and Stages 3–4 are pending the `.plugin` install. Stages 3–4 need the `.plugin` installed in a Cowork desktop: they verify what the host does with the manifest, which no lint can.

### Stage 1 — Static lint (new checks)
- **TC-val-250-agents** | `agents/*.md` | frontmatter: name == file, description, tools or disallowedTools, model ∈ enum | validator check 7 | expected: 3 checked, 0 FAIL
- **TC-val-250-commands** | `commands/*.md` | description, argument-hint, `disable-model-invocation: true` on every command | validator check 8 | expected: 4 checked, 0 FAIL
- **TC-val-250-mcp** | `.mcp.json` ↔ `integration-strategy.md` *Declared connectors* | same key set both sides; valid JSON | validator check 9 | expected: 6 servers, 0 FAIL
- **TC-val-250-counts** | plugin.json, marketplace.json, README | `29 skills, 3 agents, 4 commands, 6 connectors` matches disk | validator check 10 | expected: 0 FAIL
- **TC-lint-250-scope** | `agents/`, `commands/` | org-data / org-signature / locale / stale-name rules apply to component files | `skill_lint.py` (component_files) | expected: 0 FAIL on the clean tree

### Stage 1b — Seeded-leak test
- **TC-seed-250** | temp copy | two new seeds (an Atlassian host inside `agents/artifact-checker.md`; an authority citation inside `commands/status.md`) make the linter RED with `org-data` / `org-signature` | expected: 12/12

### Stage 2 — Trigger eval
- **TC-trig-250-L** | Group L (8 negative rows) | no phrase routes to a command; L8 reaches `status` only by explicit invocation | expected: 8/8

### Stage 3 — Host behavior (install the `.plugin` in Cowork desktop)
- **TC-host-250-tabs** | plugin card | tabs show **Connectors · 6**, **Agents · 3**, **Commands · 4**; Skills stays 29 | expected: all four counts visible
- **TC-host-250-connectors** | Connectors tab | `atlassian` and `figma` show as *Connected* against the user's existing connections (no second Atlassian / Figma entry appears in the org connector list); `gmail` / `google calendar` / `google drive` / `fireflies` resolve by name | expected: 6 rows, no duplicates
- **TC-host-250-namespace** | a fresh session | tools of declared connectors appear under the connector's namespace (`mcp__Atlassian_Rovo__*`, `mcp__Figma__*`, …), never under a plugin-prefixed one | expected: matches the *Declared connectors* table
- **TC-host-250-notools** | `debater` | `Agent(subagent_type: "grow-product-manager:debater")` with an evidence pack: the agent answers in the Round-1 structure and, when asked to "check the vault first", reports it has no tools rather than trying | expected: no tool calls in its transcript. **If `tools: []` is ignored by the host** → switch to `disallowedTools` only (already present) and record it here
- **TC-host-250-checker** | `artifact-checker` | spawned from requirements-creator Step 4.5 with lens=form on a draft with one prose-formatted requirement | expected: one Gate-2 finding with location + proposed_fix; no rewrite
- **TC-host-250-cmd-hidden** | `/grow-product-manager:status` | "який статус плагіна" does NOT invoke it; typing the command does | expected: L1 and L8 pass live

### Stage 4 — Integration
- **TC-int-250-onboarding** | plugin-configurator Step 3a | with the six connectors connected, no registry search is proposed; Tableau/Notion still pinged by pattern | expected: readiness table lists 6 declared + pattern rows
- **TC-int-250-fallback** | any host without plugin agents | gate/debate/fan-out fall back to `general-purpose`, report says so | expected: marker present, behavior unchanged

### Stage 5 — Regression
- **TC-reg-250** | Groups B / D / F / I re-run | no routing change from the description edits in four skills | expected: 100%

## Release v2.4.1 — org-leak audit (examples that were not universal)

> **Run 2026-07-31 — verdict: GREEN.** 18 checks, 0 FAIL; seeded-leak test 10/10. The nine defects here were all green under the previous 15 checks: none of them is a host, an id or an email, so no shape-based rule saw them, and the one layer that would have — the gitignored `org-tokens.local` denylist — did not exist on any machine. The lesson is written into the linter's own comments: an optional layer that nobody notices is absent is a layer that does not run.

### Stage 1 — Static lint (new checks)
- **TC-lint-241-signature** | references + skills | no rule cites a team as its authority; no example is signed with a team + quarter | check `org-signature` | expected: 0 FAIL | **pass** (was 4: a link convention, report formatting rules, and two reference examples carrying a team name and a quarter)
- **TC-lint-241-locale** | references + skills, fenced blocks | sample values inside code blocks are language-neutral | check `example-locale` | expected: 0 FAIL | **pass** (was 5: the glossary schema example in one team's language, two config blocks with a localized keyword, a signal example, a style-profile note assuming a specific language's address forms)
- **TC-lint-241-lang** | references + skills | no output language hardcoded where `user.language` exists | check `example-locale` | expected: 0 FAIL | **pass** (was 1: `Language: <Lang> by default` in product-reporter)
- **TC-lint-241-keys** | references + skills + templates | example issue/space keys come from the placeholder vocabulary | check `example-keys` | expected: 0 FAIL | **pass** (0 in the tree; the check caught its own documentation row in `Testing-process.md`, which was rewritten)
- **TC-lint-241-denylist** | repo | absence of `testing/org-tokens.local` is reported | expected: WARN, not silence | **pass**

### Stage 1b — Seeded-leak test (new stage)
- **TC-seed-241** | temp copy of the tree | each of 10 known-bad lines makes the linter RED with the expected tag; the clean copy is GREEN | `testing/seeded_leak_test.py` | expected: 10/10 | **pass** (5 signature shapes, 2 locale, 2 keys, 1 denylist)
- **TC-seed-241-ci** | validate.yml ↔ release.yml | the seeded test runs in both, and gate parity covers it | expected: 3 validators, identical | **pass**

### Stage 5 — Regression
- **TC-reg-241-triggers** | 3 touched skills | no description changed, so routing is untouched | expected: no trigger-eval re-run needed | **pass** (all three edits are in bodies and skill-local references; frontmatter `description` byte-identical)
- **TC-reg-241-bilingual** | references + skills | the bilingual trigger surface in prose survives the locale check | expected: 0 FAIL on ~30 lines of intentional non-Latin trigger phrases and status synonyms | **pass** (that is why the check is scoped to fenced blocks)

### Coverage gap this release leaves open
- A plausible-sounding but domain-specific example ("the Buy button moves above the specs block") is invisible to a regex. It is caught by review only — the rule is stated in `Testing-process.md` and belongs in the checker's brief for any doc change.

---

## Release v2.1.0 — audit remediation P3 + P4 (behavioural defects)

> **Run 2026-07-14 — verdict: GREEN.** 13 checks, 0 FAIL. P3/P4 defects are mostly *semantic* (a gate that skips, a mode with no flow, weights that don't sum) — a linter cannot catch these, so they are covered by scenario cases below. This is the honest boundary of static lint.

### Stage 3a — Trajectory / scenario walk
- **TC-scn-210-a11y** | design-bridge | `intent=handoff`, `audience=team` | expected: a11y audit RUNS and blocker findings block Step 6 | **pass** (previously skipped: 4e required c-level/dev_handoff, so Step 6's "if Step 4e ran" never fired)
- **TC-scn-210-handoff-route** | design-bridge | "make a handoff" with a declared toolkit | expected: Q4a decides document-vs-generate; Step 0.5 routes only on "generate" | **pass** (route was undecidable — no question collected the input)
- **TC-scn-210-journal** | focus-advisor | `journal` mode with 2 chosen + 1 snoozed focus | expected: non-terminal focuses shown, per-item done/snooze/drop/keep, gated write, summary | **pass** (mode had no workflow at all)
- **TC-scn-210-chosen** | focus-advisor | daily brief with a `chosen` focus in the log | expected: pinned to top, not re-scored, nudge after 2 cycles | **pass** (fell through dedup and was re-ranked as a fresh signal)
- **TC-scn-210-recovery** | plugin-configurator | `local-context.md` deleted, `~/.grow-pm/` + vault mirror intact | expected: Reinstall/Migration with RM-0 backup, RM-1 restores from mirror | **pass** (both rules matched; textual order chose Onboarding and would have started fresh over live data)
- **TC-scn-210-kl-skip** | plugin-configurator | decline the Knowledge Library at Step 12 | expected: continue to Step 13 (Templates), `templates_setup_completed` set | **pass** (jumped to Step 14; 16g then nudged a user who was never asked)

### Stage 1 — Static lint (regression)
- **TC-lint-210** | repo | all 13 checks after P3/P4 | expected: 0 FAIL | **pass**

### Stage 4 — Integration
- **TC-int-210-cjm-weights** | cjm-protocol × funnel-templates | health score sums to 100% for every shipped template | expected: 4-stage=100, 5-stage=100, 6-stage=100 | **pass** (was 100 / 125 / 150 — Marketplace and SaaS scores were silently deflated)
- **TC-int-210-focus-config** | context-schema (write) ↔ focus-signals §8 (read) ↔ example | same subsections, same order, same placement | expected: `healthcheck` under Scheduled everywhere; `zones` defined | **pass**
- **TC-int-210-deferred** | onboarding-steps ↔ context-schema | every written `deferred_steps` key is in the enum and vice versa | expected: exact match | **pass** (6 written-but-unlisted, 2 listed-but-never-written)

---

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

## Coverage gaps (known, deliberate)

This registry holds cases for **v1.15.0 and v2.0.1+**. v1.16.0–v1.40.0 and v2.0.0 shipped
without entries — including v2.0.0, the largest release (6 new skills + the
`team-ops-reporter` → `product-reporter` rename). Do not read an absent case as a passing
one.

Rather than backfill 25 releases of prose, the defect classes those cases would have
covered are now **automated** in `skill_lint.py` (15 checks) — the rename regression that
`TC-reg-rename-02` reported as "pass" while a stale name was live is exactly what
`stale-names` answers mechanically. What remains genuinely manual (trajectory walks,
output evals) belongs in `trigger-evals.md` / `output-evals.md`, not here.

### v3.1.0 — flow-walkthrough (added 2026-09-10)

- **TC-flow-walkthrough-lint-1** | skills/flow-walkthrough | frontmatter, path rule, Step T subtype `walkthrough` resolves to `research/walkthrough-v1.md`, vault type `walkthrough` in TYPE_FOLDER_MAP | expected: `skill_lint.py` 0 FAIL | **pass** (2026-09-10: skill_lint GREEN, validate-consistency green, seeded-leak 12/12, host-smoke: Claude lists 30 skills incl. flow-walkthrough, Codex 35 entries)
- **TC-flow-walkthrough-trigger-1..8** | flow-walkthrough | trigger-evals Group M (M1–M4 positive, M5–M8 neighbours) | expected: 8/8 | **pass** (2026-09-10, Claude Code live, 8/8)
- **TC-flow-walkthrough-scenario-1** | walk mode | `examples/marketplace-review-flow.md` as the scenario, iphone-on-mac, test account, default write boundary | expected: preflight table, overlay warning, `steps/00.png` read back, ≥ 8 steps in `steps.yaml`, verdict `blocked_at:N` with `write boundary`, `findings.md` lists the six expected frictions, report through `research-builtin-walkthrough` | **pass** (2026-09-11, Claude Cowork, own account: preflight table printed, LanguageTool quit and relaunched, `steps/00.png` read back, 9 steps + 10 window-scoped screenshots, verdict `blocked_at:7` write boundary, findings 3 major / 3 minor / 1 cosmetic incl. all six expected, report rendered from the built-in template; nothing published)
- **TC-flow-walkthrough-scenario-2** | setup mode | android-adb on a machine without adb | expected: preflight row `missing`, the brew step proposed and NOT run before the user confirms, user-only rows handed over as numbered instructions | status: manual
- **TC-flow-walkthrough-integration-1** | cjm-research → flow-walkthrough | anomaly on a stage, user asks to see it | expected: chain offered, source marker `walkthrough-local` in Sources | status: scenario read-through
- **TC-flow-walkthrough-regression-1** | requirements-creator Step 4.2 | no walkthrough pack exists | expected: source chain unchanged from v3.0.1 (upload → Figma → browser), no error | status: scenario read-through
