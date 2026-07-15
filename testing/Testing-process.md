# Grow PM Plugin Testing Process

> Goal: ship changes incrementally **without breaking the plugin** in Claude. Every version goes through the same loop: backup → apply → stage-by-stage tests → debug → version bump. Skills are prompt artifacts, so a "test" = static validation + trigger eval (trajectory) + scenario walk + **output eval (artifact quality)** + integration + regression. Execution runs in subagent mode.

## Testing stages

| # | Stage | What it checks | How | Blocker? |
|---|--------|--------------|-----|---------|
| 0 | **Backup** | snapshot of the version before changes | `git tag` + copy of the folder into `_backups/<version>/` | — |
| 1 | **Static lint** | 13 named checks — see the table below | `testing/skill_lint.py` (automated, in CI/locally) | yes |
| 2 | **Trigger eval** | description triggers on target phrases and does NOT hijack others | a set of positive/negative phrases per skill; judge subagent | yes |
| 3a | **Trajectory / scenario walk** | skill takes the right steps: key steps, gates, tool calls, artifact structure | 1-2 scenarios per skill + mock local-context; subagent "dry run" verifies | yes (for changed skills) |
| 3b | **Output eval** | artifact **quality** against a rubric (weighted 0/1/2, pass ≥ threshold) | `testing/output-evals.md` rubric + fixture + gold exemplar; LM-judge subagent | yes (for changed artifact-producing skills) |
| 4 | **Integration** | chaining between skills, resolution of shared references, delegation (e.g. planning→product-reporter) | chain scenario; subagent | yes |
| 5 | **Regression** | the change did not break existing skills (especially after rename/dedup) | re-run 1-4 on neighboring/dependent skills | yes |
| 6 | **Sign-off** | all green → version bump + CHANGELOG + README; otherwise → debug loop | main agent consolidates | — |

**Gate principle:** if any blocker stage is not "green" → do not proceed. On error → stage 6 debug → fix → re-run the affected stages.

## Stage 1 — what static lint actually checks

Every check exists because the defect class it catches actually shipped. The v2.0.0 audit found 5 critical + 14 major defects while both validators reported green; each became a named check in v2.0.1. **When a new defect class is found, add a check here — do not rely on a manual step.** The rename regression `TC-reg-rename-02` was hand-run and reported *pass* while the stale name was still live; `stale-names` now answers that question mechanically.

| Check | Catches | Shipped example it would have caught |
|-------|---------|--------------------------------------|
| `frontmatter-yaml` | frontmatter that only a lenient parser accepts | unquoted `Українською: ` broke strict YAML in 28/29 skills |
| `frontmatter-fields` | name≠folder, bad semver, description missing or >1024 | 4 descriptions over the spec limit for the routing field |
| `skill-version-sync` | body `skill_version` drifting from frontmatter | vault-save blocks citing an old version |
| `ref-paths` | any cited path that does not resolve | `references/builtin-templates/<subtype>.md` — never existed |
| `ghost-skill` | a chain target that is not a real skill | `people-context` (a protocol), `write-spec` (nothing) |
| `stale-names` | an incomplete rename outside CHANGELOG history | `Feature-task-creator`, 8 months after the rename |
| `duplicate-h1` | a doc containing itself twice | vault-protocol.md and persistent-storage.md |
| `readme-versions` | README claims ≠ frontmatter | 16 stale skill versions |
| `org-data` | real org identifiers in shipped files | real roster + board id + VIP email in the example file; team UUID + cloud id + internal KPI data (audit #2) |
| `deck-subtypes` | yaml keys ≠ template subtypes | `feature-concept` vs `feature` |
| `vault-types` | a saved type with no folder in TYPE_FOLDER_MAP | feedback-triage, report-3t5f, presentation/prototype/handoff, all People types |
| `artifact-types` | a Step T type outside the protocol enum | roadmap, meeting-notes, focus, delegation-audit |
| `chain-contracts` | a claimed `← X` edge that X knows nothing about | experiment-tracker was unreachable by chaining |

Two design rules keep the linter honest: it is **stdlib-only** (PyYAML only adds an extra strict parse — CI installs it and sets `GROW_LINT_REQUIRE_YAML=1` so its absence is a blocker there, while a local run without it degrades to a warning), and the `ghost-skill` vocabulary is **auto-derived from `templates/built-in/`** rather than hand-listed, so new template types do not create false positives.

### `org-data`: set up your local denylist (do this once per machine)

The `org-data` check has two layers:

1. **Generic shapes — always on, including CI.** Real Atlassian hosts, real-looking email domains, literal UUIDs (cloud/team ids), company registry ids (ЄДРПОУ/EDRPOU), internal hostnames (`*.corp`, `*.internal`, `gitlab.<domain>`), and non-placeholder names in the example roster.
2. **Your organization's own tokens — only if you create the file.** `testing/org-tokens.local`, one token per line, case-insensitive substring match.

That second layer is **gitignored on purpose**: a denylist that ships would put the very strings it forbids into the repo (the pre-v2.1.0 linter did exactly that). The cost is that it protects nothing until you create it — CI never has it, and audit #2 found the file did not exist on the author's machine either, so re-injecting the original v2.0.0 leak passed green for a full release cycle.

```bash
cat > testing/org-tokens.local <<'EOF'
# one token per line; '#' comments ignored
acme-internal.example            # your hosts
4a0df834-655a-4a18-8b2a-...      # your Atlassian cloud id
PROJKEY                          # your Jira project/board keys
Surname                          # real colleagues' names
EOF
python3 testing/skill_lint.py    # now RED on anything that leaks them
```

**Rule:** whenever you purge an identifier from the tree, add it to `org-tokens.local` **in the same commit** — that is what stops it from coming back. Everything the generic layer cannot recognize (a surname, a product codename, an internal tool) exists only in this file.

## Test case format

```yaml
- id: TC-<skill>-<stage>-<n>
  skill: <skill>
  stage: lint | trigger | scenario | integration | regression
  input: <phrase / scenario / mock-context>
  expected: <expected behavior/structure/resolution>
  actual: <filled in during the run>
  status: pass | fail | blocked | n/a
  notes: <details, link to bug>
```

The case registry is `testing/test-cases.md`; updated EVERY release (new cases for new skills/fixes + regression cases for affected skills).

## Backup protocol

- Before any change: `git tag pre-v<next>` + copy of the full plugin folder into `_backups/<current-version>-<timestamp>/` (outside git or into a gitignored folder).
- Keep the backup until a green release is confirmed; rollback = `git reset --hard pre-v<next>` or restore from `_backups/`.
- Every version has its own tag → there is always a rollback point.

## Release loop (per version)

```
1. Backup (stage 0): tag + copy.
2. Apply: introduce this version's changes (new/modified files).
3. Test: stages 1→5 (blockers). Each one — subagent(s).
4. Debug: failures → root-cause → fix → re-run affected stages (until green).
5. Sign-off (stage 6): version bump in frontmatter + CHANGELOG entry + README; update test-cases.md.
6. Commit + tag v<version>. Move on to the next version.
```

## Subagent orchestration

| Work | Executor |
|--------|-----------|
| Static lint | script (bash) — deterministic, no agent |
| Trigger eval (per skill) | judge subagent per skill (in parallel batches) |
| Scenario walk (per skill) | "dry run" subagent per skill |
| Integration / Regression | subagent per chain/group of dependents |
| Consolidation, debug decisions, version | main agent |

Rule: heavy read/eval passes — by subagents (keep the main context clean); fix and bump decisions — main agent, with PM confirmation on risky ones.

## Version Definition of Done

- Lint: 0 FAIL.
- Trigger: all target phrases trigger the target skill; 0 false hijacks of neighbors.
- Scenario: for every changed skill the key steps/gates/format are present.
- Integration: all chains and references resolve.
- Regression: neighboring skills behave as before the change.
- CHANGELOG + README + frontmatter versions are consistent; test-cases.md updated.
- Backup and tag in place.

> All changes stay **additive/safe for Claude**: keep trigger phrases; remove nothing without a regression check of dependents.
