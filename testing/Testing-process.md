# Grow PM Plugin Testing Process

> Goal: ship changes incrementally **without breaking the plugin** in Claude. Every version goes through the same loop: backup → apply → stage-by-stage tests → debug → version bump. Skills are prompt artifacts, so a "test" = static validation + trigger eval (trajectory) + scenario walk + **output eval (artifact quality)** + integration + regression. Execution runs in subagent mode.

## Testing stages

| # | Stage | What it checks | How | Blocker? |
|---|--------|--------------|-----|---------|
| 0 | **Backup** | snapshot of the version before changes | `git tag` + copy of the folder into `_backups/<version>/` | — |
| 1 | **Static lint** | 18 named checks — see the table below | `testing/skill_lint.py` (automated, in CI/locally) | yes |
| 1b | **Seeded-leak test** | that the org-leak checks actually fire — 10 known-bad lines injected one at a time, linter must go RED on each | `testing/seeded_leak_test.py` (automated, in CI/locally) | yes |
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
| `vault-paths` | an example vault path that contradicts TYPE_FOLDER_MAP | the schema's own MOC templates put the product above the area subfolder, and linked an `archive/` folder the same file forbids |
| `builtin-subtypes` | a subtype that does not resolve to its own filename; a marker citing someone else's id | all five ops-report built-ins were unreachable through the ladder; 4 of 5 carried the wrong template id |
| `org-signature` | a team/org name cited as the authority behind a rule, or an example signed with a team + quarter | four lines that made one team's habits read as the plugin's rules: `per <Team> convention`, `(<Team> formatting rules)`, `Reference example (<Team> Q3 2026…)`, `validated by a run of Q3 <Team>` |
| `example-locale` | a localized sample value inside a code block; an output language hardcoded in a doc | the glossary schema example shipped its terms, synonyms and definitions in one team's language; `Language: <Lang> by default` in a skill that has `user.language` |
| `example-keys` | an example issue/space key outside the placeholder vocabulary | a real project key in place of `PROJ-1234`, or a real space key in place of `SPACE` — both an org leak and an example the reader cannot run (this very row was written with a real-looking key first, and the check rejected it) |

Validator checks added for the cross-host release (v3.0.0), in `validate-consistency.sh`:

| Check | Catches | Shipped example it would have caught |
|-------|---------|--------------------------------------|
| 12 `description routing order` | a routing guard that does not survive Codex's ~190-character cut; a guard naming a non-existent skill; a description with no Ukrainian keywords | the v2.x order put "Do NOT use" and every Ukrainian trigger after character 400 — cut on every real Codex host |
| 13 `commands typed-only` | `$1` / `$ARGUMENTS` in a command body (Codex skips the command); a command description that does not open with the typed-only guard | 4 of 5 commands never migrated; once they did, `«який статус плагіна»` routed to `source-command-status` (trigger-evals L 4/9) |
| 14 `host packaging` | a skill or command without the Path rule; an `agents/*.md` without its `.codex/agents/*.toml` port; a skill missing from `testing/host-matrix.md` | Codex resolved `references/data-policy.md` against the skill folder — 3 of 4 shared protocols unreachable from write-concept |

Two design rules keep the linter honest: it is **stdlib-only** (PyYAML only adds an extra strict parse — CI installs it and sets `GROW_LINT_REQUIRE_YAML=1` so its absence is a blocker there, while a local run without it degrades to a warning), and the `ghost-skill` vocabulary is **auto-derived from `templates/built-in/`** rather than hand-listed, so new template types do not create false positives.

## Every example in the plugin is universal

The plugin ships to other people's organizations, and its own manifest promises that it "ships no hardcoded brand or organization data". So an example is written for a reader who knows nothing about the team that wrote it:

- **Placeholders, not real values.** `PROJ-1234` for an issue, `SPACE` for a Confluence space, `example.com` for a host, `Product 1` for a product, `Surname1` for a person. If a doc needs a new placeholder, it joins that vocabulary rather than inventing a real-looking one.
- **The authority behind a rule is nameable.** Either the plugin itself, a config key in `local-context.md`, or a named vendor — never a team the reader cannot look up. `per <Team> convention` becomes "follow the team's convention from `local-context.md` (`planning.link_convention`); default when unset — …".
- **An example is never signed with a team.** `Reference example (<Team> Q3 2026, verified by a run)` becomes "anonymized from a real quarterly run". Signed examples read as the plugin's rules to anyone inside that team, and as unverifiable claims to everyone else.
- **Code blocks are language-neutral.** Trigger phrases in prose stay bilingual by design — that is the plugin's routing surface. A fenced block is a format spec the model copies literally, so its sample values are English. Localized wording belongs in `templates/` and in the user's own `~/.grow-pm/` files.
- **No hardcoded output language.** Read it from `user.language`.
- **Domain detail is generic.** "Primary action button moves above the details block", not the name of a button on one marketplace's product page.

Checks `org-signature`, `example-locale` and `example-keys` catch the shapes above mechanically. They cannot judge whether a plausible-sounding example is domain-specific — that stays a review question, and it belongs in the checker's brief for any doc change.

### `org-data`: set up your local denylist (do this once per machine)

The org-leak defense has three layers:

1. **Generic shapes — always on, including CI.** Real Atlassian hosts, real-looking email domains, literal UUIDs (cloud/team ids), company registry ids (ЄДРПОУ/EDRPOU), internal hostnames (`*.corp`, `*.internal`, `gitlab.<domain>`), and non-placeholder names in the example roster.
2. **Positional shapes — always on, including CI.** `org-signature`, `example-locale`, `example-keys`: a leak that is an ordinary word ("per <Team> convention") has no lexical signature, only a position.
3. **Your organization's own tokens — only if you create the file.** `testing/org-tokens.local`, one token per line, case-insensitive substring match.

That third layer is **gitignored on purpose**: a denylist that ships would put the very strings it forbids into the repo (the pre-v2.1.0 linter did exactly that). The cost is that it protects nothing until you create it — CI never has it, and audits #2 and #3 both found the file missing on the author's machine, so a re-injected leak passed green for two full release cycles. Its absence is now a WARN on every run, and layer 2 exists because layer 3 cannot be relied on.

```bash
cp testing/org-tokens.local.example testing/org-tokens.local
$EDITOR testing/org-tokens.local   # team names, project keys, hosts, cloud id, surnames
python3 testing/skill_lint.py      # now RED on anything that leaks them
```

Tokens are matched **case-insensitively with word boundaries**, not as bare substrings: a short team acronym is a substring of ordinary English (a token like `SET` lives inside "offset", "settings", "asset"), and a denylist that fires forty times on its first run is a denylist you delete by lunchtime. Two hits are expected and correct — the author line and the marketplace install path in README name the repository owner, which is attribution, not a leak.

**Rule:** whenever you purge an identifier from the tree, add it to `org-tokens.local` **in the same commit** — that is what stops it from coming back. Everything the shape-based layers cannot recognize (a surname, a product codename, an internal tool) exists only in this file.

## Stage 1b — the seeded-leak test

A check nobody has watched fail is a promise, not a test: a regex that matches nothing reads exactly like a clean repo. `testing/seeded_leak_test.py` copies the tree to a temp dir, injects one known-bad line at a time, and asserts the linter goes RED with the expected check tag — ten seeds, one per defect class that actually shipped, written with a fictional org (`Zorg`, `ZORG`) so no real identifier enters the repository. It runs in both CI workflows and after any edit to `skill_lint.py`.

```
baseline: GREEN ✅   seeds: 10
  ✅ authority: per <Org> convention  → expected [org-signature]
  …
caught 10/10 seeded leaks
```

**Rule:** a new check lands with its seed in the same commit. If you cannot write a line that the check must reject, the check does not describe anything.

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

## Stage 1c — the two-host smoke (`testing/host-smoke.sh`)

Static checks prove the tree is consistent; they cannot prove a host still loads it — v3.0.0's `git-subdir` source was valid JSON and Codex listed zero plugins. `host-smoke.sh` installs the working tree on both hosts and fails on the first regression: Claude Code must validate the manifest, load every skill on disk, run the SessionStart hook and state the current version; Codex CLI must list every skill plus every migrated command and carry `references/` and `.codex-plugin/plugin.json` in its cache. Its summary line is pasted into every release PR. Add a host here when the plugin starts supporting one.

## Version Definition of Done

- `bash testing/host-smoke.sh` green on the release machine, summary line in the release PR (since v3.0.2).

- Lint: 0 FAIL.
- Seeded-leak test: 10/10 caught (and a new seed for every new check).
- Every example added or touched this version is universal — placeholders, no team signature, language-neutral code blocks, no domain-specific detail.
- Trigger: all target phrases trigger the target skill; 0 false hijacks of neighbors.
- Scenario: for every changed skill the key steps/gates/format are present.
- Integration: all chains and references resolve.
- Regression: neighboring skills behave as before the change.
- CHANGELOG + README + frontmatter versions are consistent; test-cases.md updated.
- Backup and tag in place.

> All changes stay **additive/safe for Claude**: keep trigger phrases; remove nothing without a regression check of dependents.
