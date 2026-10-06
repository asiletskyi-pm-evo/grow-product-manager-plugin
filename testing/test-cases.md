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
covered are now **automated** in `skill_lint.py` (24 checks as of v3.8.0) — the rename regression that
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

### v3.2.0 — test accounts and legs (added 2026-09-11)

- **TC-flow-walkthrough-scenario-3** | walk mode, 3 legs | `examples/marketplace-order-to-review-flow.md`, test buyer + test seller, sandbox-confirm | expected: leg summary in the report, four one-line confirmations (place order, confirm, ship, publish), `run.yaml.legs[]` with `order_id` and `tracking` hand-offs, screenshots `steps/L<leg>-<NN>.png`, worst-leg verdict; real-payment-only checkout → `blocked_reason: real money` | status: manual, needs the user's logins
- **TC-plugin-configurator-test-accounts-1** | Test accounts setup | `додай тестові акаунти` with two accounts, then a pasted password | expected: `#### Test Accounts` table written with labels/roles/surfaces/access/sandbox; the password is not written anywhere and the skill says so | **pass** (2026-09-11: table written for the reference product with three labelled accounts — buyer, two sellers — access as links only; trigger N3/N4 → plugin-configurator 2/2 after the description fix)
- **TC-flow-walkthrough-regression-2** | walk mode, single leg, own account | the v3.1.0 review scenario | expected: identical behaviour to v3.1.0 (`leg: 1`, `stop-before-irreversible`, stop at Publish) | status: scenario read-through

### v3.3.0 — product-landscape (added 2026-09-11)

- **TC-product-landscape-scan-1** | scan mode | dev machine with iPhone apps from the Mac App Store; user says no to bookmarks | expected: `landscape_scan.sh` lines parse as JSON with bundle ids, App Store lookup fills genre/rating/seller, candidates ranked by category match, first batch of 10–15 presented, bookmarks not read | **pass** (2026-09-11, dev machine: 96 candidates — 47 Mac apps, 49 iPhone apps from the Mac App Store, all with bundle ids; 49/49 App Store lookups answered, genre Shopping; the user's own product excluded; 48 candidates written to `scans/2026-09-11-scan.yaml` as pending; batch 1 of 15 presented with proposed roles; bookmarks not read — consent pending)
- **TC-product-landscape-discover-1** | discover mode | product category + primary market | expected: App Store genre search candidates deduplicated against the registry, proposed roles, batches | status: run at release
- **TC-product-landscape-map-1** | map mode | ≥ 3 confirmed records | expected: `research/landscape` artifact rendered from the built-in template, user's product highlighted, stale list | status: run at release
- **TC-product-landscape-research-1** | research mode | registry with ≥ 5 records | expected: ranked list with reasons and no cap, the user picks or names products, unknown ones registered as `auto`, chains offered (flow-walkthrough compare / product-research / brainstorm-features) | status: scenario read-through
- **TC-product-research-regression-3** | product-research | no landscape registry on disk | expected: competitor list from `product.competitors` exactly as in v3.2.0 | status: scenario read-through


### v3.4.0 — judgment contract + thin core (added 2026-09-25)

Ids follow `TC-<area>-<release>-<slug>`; the JCRL specification's ids are given as aliases.

- **TC-reg-340-step0j** | all 31 skills | grep `> **Judgment contract (Step 0j).**` | expected: exactly one block per `SKILL.md`, identical text, pointing at `local-context-protocol.md` Step 0j and `pm-mental-model.md` | **pass** (2026-09-25: 31/31, one block each)
- **TC-reg-340-no-new-question** | Step 0j + `pm-mental-model.md` | a v3.3.0 `local-context.md` (`local-context.example.md`); brainstorm-features ICE, product-analysis A/B verdict, experiment-tracker readout, decision-log log (standalone and chained from experiment-tracker decide), focus-advisor headless brief, cjm-research automated health-check, write-concept, requirements-creator, meeting-processor, product-research — old vs new | expected: no new question, no removed question or gate, no new output | **pass** (2026-09-25, round 3: two independent adversarial refuters, 0 blocking). Rounds 1–2 failed on wording that would have added questions (principles read as live rules) or dropped existing ones in chained runs; fixed by "a principle acts only through a step that implements it", a version on every *Binds* list, and moving the no-user-present rule to the version that adds the P2 question
- **TC-reg-340-slim-{meeting-processor, diagram-prototyper, product-research, task-creator, design-bridge, requirements-creator, cjm-research, brainstorm-features, write-concept}** | scenario walk, two scenarios per skill (the common mode + a branch that reaches moved text), old vs new | expected: same steps, gates, questions, tool calls and output structure; every pointer resolves; no lost instruction | **pass** 9/9 (2026-09-25); moved lines verified verbatim by script (every removed non-blank line found in the new references, headings re-levelled only)
- **TC-reg-340-output-evals** | write-concept, requirements-creator, cjm-research, meeting-processor, task-creator | fixture → maker on main and on the branch → one blind judge | expected: after ≥ pass_threshold and no material regression | **pass** 5/5 — see `output-evals.md` → Results log
- **TC-val-340-thin-core** | validator check 15 | a `SKILL.md` over 400 lines | expected: FAIL naming the file | **pass** (fired on design-bridge 445 and meeting-processor 617 mid-slimming; green at 380 max)
- **TC-trig-340-regression** | trigger-evals Groups A–O | descriptions-only simulation, 2 runs | expected: no regression | **pass** (100 % every group, both runs)

### v3.5.0 — role layer core (added 2026-09-28)

Ids follow `TC-<area>-<release>-<slug>`; the JCRL specification's ids (TC-role-01…05, TC-host-01) are aliases.

- **TC-role-350-onboarding-{pm, head_of_product, cpo, product_designer, product_analyst, ux_researcher, eng_lead, business_owner, other}** (alias TC-role-01) | plugin-configurator Basic onboarding, Steps 4 → 4a → 4b → 16 → 17 per role | expected: every structured question has 2–4 options; Role / Role label / Role scope / Level home written and valid against context-schema; `Level home` = role-profiles §2b; `## Judgment` defaults; `judgment` deferred; Step 17 offers `role_defaults.quick_wins` first | **pass** 9/9 (2026-09-28, scenario walk); follow-ups applied: quick wins whose section is deferred become "add X, then …" pairs, the 16g summary no longer hard-codes PM suggestions
- **TC-role-350-onboarding-extended** | Extended, Step 4b | expected: only `hats_allowed` is asked; the other two switches shown with "(from v3.7.0)" / "(from v3.9.0)" | **pass** (2026-09-28)
- **TC-role-350-legacy-map** (alias TC-role-02) | Step 0i and RM-4d with `Role: Senior PM` / `Head of Growth` / `Senior Product Designer` / `Tech Lead` / a Ukrainian job title | expected: one question with the keyword-mapped enum, written with a one-row changelog; the second run asks nothing | **pass** (2026-09-28)
- **TC-role-350-absent** (alias TC-role-03) | no Role line; interactive product-analysis vs headless focus-advisor and an automated cjm-research health-check | expected: one two-level-picker question interactively; none in automated runs, `pm` used, nothing written | **pass** (2026-09-28)
- **TC-role-350-hat** (alias TC-role-04) | profile `pm`; «подивись як CPO: …» | expected: header `Hat: cpo (profile: pm)`, altitude line present, profile unchanged, no v3.6.0 effect (template, emphasis) | **pass** (2026-09-28); template part moves to TC-role-360-template
- **TC-role-350-same-request** (alias TC-role-05) | the same concept request from `cpo` and from `pm` | expected: same skill, same questions and gates; altitude from the request, not the role | **pass** (2026-09-28)
- **TC-host-350-step0i** (alias TC-host-01) | a host without the SessionStart hook and without structured questions | expected: a numbered list (then scopes); one `Role: … · Altitude home: …` line once per interactive session; not printed when the digest shows `user.role` | **pass** (2026-09-28)
- **TC-hook-350-role** | `python3 testing/session_start_test.py` | expected: `user.role` enum / legacy / absent, trailing comment ignored, never the free-text label | **pass** 4/4 (2026-09-28)
- **TC-lint-350-{role-branching, persona-prompt, judgment-footer, role-enum}** | `skill_lint.py` checks 19–22 + `seeded_leak_test.py` | expected: green tree; each seed caught | **pass** (22 checks, 0 FAIL; seeds 16/16)
- **TC-trig-350-group-r** | trigger-evals Group R, live Claude, majority of 3 | expected: ≥ 90 % | **pass** 13/14 (R4 "wear the … hat" idiom 1/3 — see Results log); Group N 7/8 is pre-existing on v3.4.0 (N8)
- **TC-reg-350-output-evals** | write-concept, requirements-creator, cjm-research, meeting-processor, task-creator — branch only | expected: ≥ threshold, Gate 4a altitude line present and correct | **pass** 5/5, altitude line `present-correct` 5/5
- **TC-reg-350-no-new-question** | adversarial, two lenses: only the claimed v3.5.0 effects appear; no role question in automated runs; no carried field applied early; no People data in `serves`; no unrequested Jira write | **pass after fixes** (2026-09-28): four adversarial rounds, two lenses each; blocking defects found and fixed per round 5 → 3 → 3 → 5, each round narrower (round 4: external-audience decks, return payloads, read-only files — all placement or claim precision). Round-4 fixes are verified by the static gates only; no fifth round was run.

### v3.6.0 — role defaults and templates (added 2026-09-29)

- **TC-role-360-template** | the same concept request from pm / product_designer / cpo / business_owner, and a pm with «як CPO, …» | expected: pm → concept/default exactly as v3.5.0 (no new candidate, no new question); design-brief / strategy-memo / business-case for the roles; strategy-memo for the hat run only | **pass after fixes** (2026-09-29): first run failed on an upgraded registry (new built-ins invisible) and on a usage bonus re-opening the T-3 question → built-ins always read from the plugin folder, an exact `match: subtype` hit is decisive
- **TC-role-360-template-explicit** | a pm says «дизайн-бриф для фічі X» | expected: design-brief by the explicit subtype | **pass after fixes** (same two fixes)
- **TC-role-360-extra-sections** | eng_lead / product_analyst requirements, ux_researcher research | expected: no duplicate NFR; tracking-plan only without an analytics section; repository-entry inserted | **pass** (heading matching extended to the rendered language and to "Analytics coverage requirements")
- **TC-role-360-gate-emphasis** | analyst A/B readout, head_of_product quarter review, pm | expected: caveat lines only; none for pm | **pass**
- **TC-role-360-planning-view** | quarterly-planning for head_of_product, eng_lead, pm | expected: rollup order; slice + tech-debt row; pm exactly v3.5.0 | **pass** (pm row now has no planning view)
- **TC-role-360-automated** | focus-advisor headless brief, cjm-research health-check for a cpo | expected: exactly v3.5.0 | **pass**
- **TC-role-360-money-bridge** | business_owner QBR with and without Revenue driver | expected: table, or one "No revenue mapping configured" line; no question | **pass after fixes** (uk ties removed by the decisive exact-match rule; one line, no per-claim caveats)
- **TC-reg-360-pm-unchanged** | pm / no role / automated runs across 15 skills | expected: v3.5.0 behaviour | **pass after fixes**: pm row emptied (no template default, gate emphasis, planning view, source order); focus-advisor keeps its collector order for pm; explicit requests for the new artifact types are an intended change, listed in the CHANGELOG
- **TC-reg-360-output-evals** | design-brief, strategy-memo, research-plan, qbr (new) + write-concept PRD, requirements-creator, cjm-research, meeting-processor, task-creator (regression) | expected: ≥ threshold, right template, Gate 4a line | **pass** 9/9
- **TC-trig-360** | all groups live, Group R 20 rows | expected: ≥ 90 % per group | **pass** (R 19/20 — R4 is the known weak idiom; N 9/9 with N8 reworded and N9 added)
- **TC-reg-360-adversarial** | whole diff | **pass after fixes** (2026-09-29): two adversarial rounds (2 lenses each) — round 1: 5 blocking + 6 in the pm-unchanged walk (stale registry, language ties, pm defaults, keyword subtypes, People data in the board update); round 2: 2 blocking + 11 minor (hat effects and a routing change missing from the claim, board-readout hand-off asking product-reporter's questions, role default turning a research run into a plan) — all fixed; round-2 fixes verified by the static gates

### v3.7.0 — judgment points (added 2026-09-29)

- **TC-jdg-370-hypothesis-first** (spec TC-jdg-01) | brainstorm-features with 6 ideas: `Hypothesis first: on`, the line absent, `off`; the same request in a headless / return-payload run | expected: `on` and absent → the ideas listed by name, one "which 3 first?" question before any ICE / PRO score, the "Your estimate vs mine" block after the scores; `off` → no question and no comparison, even with an estimate in the request; the output gains only the confidence line (§3); automated → never asked | **pass after fixes** (2026-09-29): Step 3B idea cards showed ICE before the question → ideas named first, cards after the answer; the legacy `on (acts from v3.7.0)` value reads as `on`, `off (…)` as `off`
- **TC-jdg-370-first-line** | two P2 points in one session (experiment readout, then decision-log) | expected: only the first P2 question carries the why / how-to-switch-off line | **pass**
- **TC-jdg-370-skip** | answers «пропусти», "skip", «не знаю», «вимкни» to the P2 question | expected: skip words → the run continues exactly as without the question, with no comparison; «вимкни» → `Hypothesis first: off` written only when the file can be written, with a one-row changelog, then as skip | **pass** (the «вимкни» answer is the consent — no Context-Enrichment confirmation)
- **TC-jdg-370-known-estimate** | «думаю, B виграв — зроби readout» in experiment-tracker; a registry entry that already has `prediction` | expected: no question; the estimate travels as `pm_estimate`; product-analysis compares and never asks | **pass after fixes**: `skipped` / `off` mean no comparison; a partial estimate is used and the missing part never asked; chained skills with their own gate count as interactive
- **TC-jdg-370-falsifier** (spec TC-jdg-03) | product-analysis A/B report for the output-eval fixture; the same report with the confidence line removed, or with a "would change if: more data" clause | expected: the report carries `Confidence: … · most sensitive to: … · would change if: …` above the altitude line; the T-5 self-check (Gate 4c) restores a missing line or rejects a vague clause; an inconclusive verdict is at most `uncertain` | **pass after fixes**: half-open scale bands; the no-inflation cap outranks a frontmatter value; output eval A/B 1.00 with an `uncertain` line and an observable falsifier
- **TC-jdg-370-no-line-elsewhere** | write-concept PRD, requirements-creator spec, product-research report, cjm-research report | expected: no confidence line (`judgment-points.md` §1 names none); Gate 4c `n/a` | **pass**: PRD and MoM regressions carry no confidence line; the self-check removes only a P3-format line, never a skill's own confidence field
- **TC-jdg-370-decision-fields** (spec TC-jdg-04) | decision-log log mode chained from meeting-processor (one decision with a named dissenter and a rejected option) and from experiment-tracker decide (registry with ≥ 5 verdicts) | expected: `owner`, `rejected_alternatives`, `minority_report`, `revisit_trigger`, `base_rate` (the registry win rate with n) filled only from what was said or recorded; `not recorded` / `none found` otherwise; one P2 question for the batch; `evidence_classes` left out | **pass after fixes**: meeting-processor hands all chosen decisions to decision-log at once (one question); the v3.7.0 fields are never asked; unstated fields are left out of the payload, `not recorded` / `none found` in the body
- **TC-jdg-370-resulting** (spec TC-jdg-04) | decision-log revisit of a record whose outcome was bad after a sound, well-documented decision | expected: step 1b prints decision quality (`sound`), outcome (`bad`) and a "resulting" line naming variance, and asks nothing; step 2 asks the P2 question once for the new decision; the lines land in the new record's Context; the old record is only marked superseded | **pass after fixes**: the resulting line is always present; revisit step 2 asks the P2 question once for the new decision
- **TC-jdg-370-status-theater** | product-reporter quarter-review without any decision; the QBR fixture (has Decisions taken) | expected: one ⚠️ chat line for the first, none for the second; no question; the report body unchanged | **pass after fixes**: follow-up statuses do not count as a decision; no note when another skill asks for the report only for its data
- **TC-cfg-370-judgment-4b** | Extended onboarding, Basic onboarding, `update config → Judgment`, and a legacy file with `off (acts from v3.7.0)` | expected: Extended and update ask `hats_allowed` and `hypothesis_first` in one message; Basic asks nothing and records `on`; the legacy value reads as `off` and Validate raises no finding | **pass after fixes** (reviewed by adversarial lens 1, not walked separately): the claims now name the Extended-onboarding question; Basic unchanged
- **TC-reg-370-one-new-question** | adversarial: the P2 question is the only new question in a skill run (Extended onboarding offers the switch — TC-cfg-370-judgment-4b); it is switchable, skippable and never asked in automated runs; no other v3.6.0 question moves | **pass after fixes**: two adversarial lenses + two scenario walks (round 1: 3 blocking + 36 minor, all fixed or deliberately left with a reason); round 2 on the final diff: 0 blocking, 14 minor (contradictory comparison with `off`, decision-log's question suppressed by a context trigger, a gold verdict outside the AB-4 set, lint 23 false negatives) — all fixed, verified by the static gates and a scratch-copy lint probe
- **TC-reg-370-output-evals** | product-analysis A/B (new) + meeting-processor, write-concept PRD (regression, with the judgment criteria) | expected: ≥ threshold; the confidence line only where §1 names it | **pass**: product-analysis A/B 1.00 (new, threshold 0.85), write-concept PRD 1.00, meeting-processor 0.83 (regression, with the judgment criteria)
- **TC-trig-370** | Group H (decision-log) + regression groups live | expected: ≥ 90 % per group (no description changed in v3.7.0) | **pass**: A 8/8 · G 10/10 · H 16/16 (H15–H16 new) · I 8/8, live; no description changed

### v3.8.0 — evidence classes (added 2026-10-06)

- **TC-jdg-380-simulated-persona** (spec TC-jdg-02) | product-research synthesis, pm role, default template: 6 real seller interviews + 3 persona "interviews" marked as tool-generated (output-eval fixture `testing/fixtures/product-research/synthesis-v1.md`) | expected: personas `simulated` on one `Simulated input` line or in hypotheses; absent from Key findings and themes; not in n; never quoted; no question; Gate 4b self-check passes | **pass** (2026-10-06): output eval 1.00 and scenario walk — no origin question; the notice line now appears only for `simulated` input
- **TC-jdg-380-simulated-p7** | feedback-triage with LLM-generated sample reviews and an AI summary of a real ticket; brainstorm-features ideas "validated" by a persona panel and a Debate with Buyer / Seller cards; cjm-research enrichment with a Deep Research claim that traces to no source | expected: generated reviews excluded from counts and clusters (simulated count shown), the AI summary of a real ticket stays `reported` and is not quoted; persona validation = `simulated`, role claims outside the pack are open questions, the consensus boost needs a cited E#; the untraceable claim is `simulated`, never a finding; no question anywhere | **pass after fixes**: feedback-triage `origin` vocabulary aligned with the fan-out schema (every non-`generated` item clustered); a user's report of persona output stays `simulated` in the debate pack; a persona panel's "validation" goes under Validation method
- **TC-jdg-380-frontier** | product-analysis post-release with no control; product-analysis Q&A "prove the redesign caused the drop"; cjm-research root cause with no qualitative source; quarterly-planning capacity that needs tacit context | expected: "coincides with" + one hand-back line in `user.language`; the supportable part answered, one line, no question; hand-back in the report; the existing "pending TL confirmation" marker reads as `assumed` and names whom to ask — never ❌ Blocked, never a halt | **pass after fixes**: one shared hand-back line under the post-release Metrics Impact table; a segment "why" in an A/B readout still gets the line
- **TC-jdg-380-frontier-ab-exempt** | a randomised A/B readout | expected: its causal verdict stands, no hand-back line; figures the PM pasted are `reported`, figures the skill read from the dashboard `measured` | **pass**
- **TC-jdg-380-gate4b-selfcheck** | the A/B fixture plus one guardrail figure stated from memory; the same report with one label stripped and one label upgraded | expected: `[assumed — …]` on the remembered figure, named in `most sensitive to`, level capped per judgment-points §3; T-5 step 3c restores the stripped label and downgrades the upgraded one — never upgrades, never invents a source | **pass after fixes**: a figure from memory is `[assumed — <who>, from memory]`; the self-check restores the class a source supports and removes quote marks from a paraphrase; it never restores a label the user removed, except `simulated` / `assumed`
- **TC-jdg-380-gate4b-checker** | write-concept PRD and requirements-creator drafts seeded with an unlabelled number, a `measured` label on a stakeholder-stated figure, a paraphrase in quote marks and a persona quote in the Problem | expected: the groundedness lens reports 4b findings (critical: the upgrade, the paraphrase, the persona; minor: the missing class); the form lens reports 4a only; the gate line shows `докази: E`; the checker output uses `gate: 4b` and `not_applicable` | **pass after fixes**: severity aligned between the gate and the agent (unlabelled `simulated` anywhere and a quoted `simulated` are critical); the Codex port regenerated
- **TC-jdg-380-n-a** | task-creator batch; requirements-creator Analyze & Improve; one-on-one; product-analysis return payload to cjm-research; an external-audience deck | expected: `not_applicable: [4a, 4b]`, no labels added to Jira bodies (copied requirement text keeps its own); 4b advisory (`advisory:`), the user's document unchanged without approval; no labels or vault keys in People artifacts; classes in the payload's data-quality notes; class in the slide caption without internal source names, no hand-back line on a slide | **pass after fixes**: status boards and registry lists added to the `n/a` list; copied requirement text in Jira bodies keeps its own labels, none added
- **TC-jdg-380-decision-classes** (supersedes the `evidence_classes` expectation of TC-jdg-370-decision-fields) | decision-log from experiment-tracker decide (pasted readout), from meeting-processor, from a debate with a `simulated` A#, and a senior-opinion decision | expected: `reported` (pasted readout), `reported` (meeting), the pack's classes with the A# kept `simulated`, `assumed`; never asked; the key left out when nothing states a class; v3.7.0 records stay valid | **pass after fixes**: a `simulated` A# stays on one `Simulated input — not evidence` line under the Rationale and still counts in `evidence_classes`; the debate chain passes the pack's classes
- **TC-vault-380-frontmatter** | vault_save of a PRD, an A/B report and a MoM; a People-contour save; a decision; a backlink rewrite of a pre-v3.8.0 note; a user's own `evidence: "[[link]]"` property | expected: `altitude` = the footer value, `evidence_classes` = the body's classes in §4 order and never `[]`; no `altitude` on People notes or decisions; the rewrite adds no key; the user property is preserved; `.vault-schema-version` unchanged; the Summary keeps `simulated` / `assumed` labels | **pass after fixes**: the Summary keeps the labels of the items it mentions and a 6c claim's "coincides with" wording
- **TC-jdg-380-automated** | scheduled cjm health-check, headless focus-advisor brief, monthly feedback-triage, experiment-tracker `mode=stale headless=true`, product-analysis for cjm-research, brainstorm Step 3C, a Debate return | expected: no question, no halt or Blocked, no hand-back line in scheduled / headless runs (a frontier claim reads `[assumed — frontier: <human step>]`), payloads carry classes and frontier flags in their notes, the health-check group label names its dashboard and that baselines are `reported (local-context.md)`; the status board and stale list carry no labels | **pass after fixes**: automated runs get labels and the 6b handling, the frontier form `[assumed — frontier: …]`, and no new line; the scheduled feedback-triage adds no comparability line and asks nothing when publishing
- **TC-jdg-380-role-invariance** | the same synthesis as pm, ux_researcher and product_designer | expected: identical `simulated` handling; `triangulation` / `human-validated` add only their remaining caveats, no second ⚠️ line | **pass**
- **TC-jdg-380-upload-origin** | a persona PDF with a "generated by" line, a persona document written by the team, and an interview transcript, uploaded without comment | expected: the first `simulated` with one notice line; the second `reported (document)` with its unsourced claims `assumed`; the third `reported`; no question | **pass after fixes**: input of unclear origin takes the class of what it contains; a team persona document's quotes are the document's wording; the notice line only for `simulated`
- **TC-jdg-380-skill-labels** | flow-walkthrough walk, knowledge-library search + A-3 add, product-landscape map, design-bridge deck (internal and external), diagram-prototyper infographic, product-reporter quarter review | expected: steps `observed`; a class field in results and the derived class inside the existing A-3 confirmation (no picker); facts with their source's class, no scan provenance cited; caption classes per audience; footer class; actuals `measured` when computed from Jira, pasted finance `reported`; an inferred cause of deviation `assumed` + hand-back | **pass after fixes**: product-reporter's example label names the Jira count, not `jira-internal`; a prototype is `reported` and a claim about users on it alone `assumed`
- **TC-jdg-380-confidence-cap** | an A/B report whose lead recommendation rests on a handed-back segment claim; a decision record whose owner states `likely` on a `simulated` input | expected: the report reads at most `uncertain`; the record keeps `likely` and the comparison names the cap | **pass after fixes**: the headless frontier form is distinct (`frontier:`), so the cap is visible; a decision record keeps the owner's level
- **TC-jdg-380-guard** | a user correction deleting evidence labels in meeting-processor M7 and product-reporter Step 7 | expected: never proposed as a skill change; treated as a one-off | **pass**
- **TC-reg-380-no-new-question** | adversarial review of the whole diff (two lenses) | expected: no new question in any skill or run kind; no persona prompt; no role-dependent branch; every SKILL.md ≤ 400 | **pass after fixes**: round 1 (two lenses + three walks + ten evals) found 2 blocking (an Analyze & Improve gap turning into a new question; a ⚠️ line added to the scheduled feedback-triage) and ~45 minor — all fixed or left with a reason; round 2 on the final diff
- **TC-reg-380-golds-label-only** | the relabelled golds | expected: with labels stripped, every old line is still present, apart from these allowed edits — cjm gold: one hand-back line on the A1 scope claim (a frontier claim per 6c); PRD gold: the "return searching" assumption moved onto its claim, the motivation sentence labelled `[assumed — …]`; research plan: "(guide rehearsal only)" on the simulated field; design brief: "and visit frequency" added to a source line; QBR: Jira counts relabelled `reported` (pasted in the dry run); MoM: speaker attributions on two figures; A/B gold: the pooled-guardrail note in the confidence line turned into an `[assumed — …]` label; strategy memo: the unnamed industry report attributed ("cited by Person1"); PRD gold: the Product Analysis Sources line says no figures yet; flow-walkthrough and product-landscape examples: version notes removed from example output; evaluator comments extended; cjm fixture: the trap described as a complete-period check (it contradicted the gold), with the trap text moved into the evaluator comment | **pass** — the allowed edits are listed above
- **TC-reg-380-output-evals** | product-research synthesis (new) + the changed golds' rubrics | expected: ≥ threshold, evidence criteria scored or `n/a` correctly | **pass** 10/10: synthesis 1.00, spec 1.00, QBR 0.97, A/B 0.96, design brief 0.96, MoM 0.95, strategy memo 0.93, research plan 0.93, PRD 0.93, cjm 0.92
- **TC-lint-380-evidence-classes** | lint check 24 and seeds | expected: green tree, 23/23 seeds caught | **pass** (2026-10-06): 24 checks, 0 FAIL / 4 WARN, 23/23 seeds |
- **TC-host-380-checker-port** | validate check 14 on the agent and its Codex port | expected: bodies identical apart from the host note; a drifted copy fails | **pass after fixes**: bodies identical; a drifted copy fails; the check now prints its ok line only when it raised nothing
- **TC-trig-380** | live groups A, E, G, H, I + B, M, O as regression (no description changed) | expected: ≥ 90 % per group | **pass** (2026-10-06): 72/72
