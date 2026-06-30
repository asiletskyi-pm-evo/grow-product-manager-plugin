# Grow PM Plugin Testing Process

> Goal: ship changes incrementally **without breaking the plugin** in Claude. Every version goes through the same loop: backup → apply → stage-by-stage tests → debug → version bump. Skills are prompt artifacts, so a "test" = static validation + trigger eval + scenario walk + integration + regression. Execution runs in subagent mode.

## Testing stages

| # | Stage | What it checks | How | Blocker? |
|---|--------|--------------|-----|---------|
| 0 | **Backup** | snapshot of the version before changes | `git tag` + copy of the folder into `_backups/<version>/` | — |
| 1 | **Static lint** | frontmatter, name==folder, semver, resolution of `references/*`, cross-skill links, skill_version ↔ frontmatter, CHANGELOG/README mentions | `testing/skill_lint.py` (automated, in CI/locally) | yes |
| 2 | **Trigger eval** | description triggers on target phrases and does NOT hijack others | a set of positive/negative phrases per skill; judge subagent | yes |
| 3 | **Scenario walk** | skill produces the correct structure: key steps, gates, artifact format | 1-2 scenarios per skill + mock local-context; subagent does a "dry run" and verifies | yes (for changed skills) |
| 4 | **Integration** | chaining between skills, resolution of shared references, delegation (e.g. planning→team-ops-reporter) | chain scenario; subagent | yes |
| 5 | **Regression** | the change did not break existing skills (especially after rename/dedup) | re-run 1-4 on neighboring/dependent skills | yes |
| 6 | **Sign-off** | all green → version bump + CHANGELOG + README; otherwise → debug loop | main agent consolidates | — |

**Gate principle:** if any blocker stage is not "green" → do not proceed. On error → stage 6 debug → fix → re-run the affected stages.

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
