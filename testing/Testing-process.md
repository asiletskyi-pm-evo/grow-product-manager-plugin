# Grow PM Plugin Testing Process

> Goal: ship changes incrementally **without breaking the plugin** in Claude. Every version goes through the same loop: backup → apply → stage-by-stage tests → debug → version bump. Skills are prompt artifacts, so a "test" = static validation + trigger eval (trajectory) + scenario walk + **output eval (artifact quality)** + integration + regression. Execution runs in subagent mode.

## Testing stages

| # | Stage | What it checks | How | Blocker? |
|---|--------|--------------|-----|---------|
| 0 | **Backup** | snapshot of the version before changes | `git tag` + copy of the folder into `_backups/<version>/` | — |
| 1 | **Static lint** | 25 named checks — see the table below | `testing/skill_lint.py` (automated, in CI/locally) | yes |
| 1b | **Seeded-leak test** | that the checks whose failure mode is silence actually fire — 26 known-bad edits (a line appended, removed or replaced) applied one at a time, linter must go RED on each | `testing/seeded_leak_test.py` (automated, in CI/locally) | yes |
| 2 | **Trigger eval** | description triggers on target phrases and does NOT hijack others | `testing/trigger-evals.md` positive/negative phrases per group, run live on each supported host (Claude Code, Codex CLI) from a neutral working directory; host and version recorded | yes |
| 3a | **Trajectory / scenario walk** | skill takes the right steps: key steps, gates, tool calls, artifact structure | 1-2 scenarios per skill + mock local-context; subagent "dry run" verifies | yes (for changed skills) |
| 3b | **Output eval** | artifact **quality** against a rubric (weighted 0/1/2, pass ≥ threshold) | `testing/output-evals.md` rubric + fixture + gold exemplar; maker subagent + blind LM-judge subagent | yes (for changed artifact-producing skills) |
| 4 | **Integration** | chaining between skills, resolution of shared references, delegation (e.g. planning→product-reporter) | chain scenario; subagent | yes |
| 5 | **Regression** | the change did not break existing skills (especially after rename/dedup) | re-run 1-4 on neighboring/dependent skills | yes |
| 6 | **Sign-off** | all green → version bump + CHANGELOG + README; otherwise → debug loop | main agent consolidates | — |

**Gate principle:** if any blocker stage is not "green" → do not proceed. On error → stage 6 debug → fix → re-run the affected stages.

## Stage 1 — what static lint actually checks

Checks 1–18 exist because the defect class each one catches actually shipped; checks 19–25 are the declared exception — preventive guards for the JCRL role layer (v3.5.0), judgment points (v3.7.0), evidence classes (v3.8.0) and judgment binds (v3.9.0), written before any defect of their class could ship. The v2.0.0 audit found 5 critical + 14 major defects while both validators reported green; each became a named check in v2.0.1. **When a new defect class is found, add a check here — do not rely on a manual step.** The rename regression `TC-reg-rename-02` was hand-run and reported *pass* while the stale name was still live; `stale-names` now answers that question mechanically.

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
| `role-branching` | a `SKILL.md` that branches on a role name (`if role == cpo`, `when the user's role is …`, `role in [...]`), or reads a `role_defaults.<field>` that `role-profiles.md` §5 step 2 does not list — the allowed set is parsed from that step, so it cannot drift | preventive (JCRL v3.5.0): nothing has shipped yet. It guards "a role changes defaults, never capabilities" — a skill that gates a step on `cpo` silently skips every other role, including every role added later |
| `persona-prompt` | a product-role identity handed to the model — "You are a CPO / product manager / tech lead …", or the Ukrainian «Ти — продакт-менеджер» form — in skills, references, agents and their Codex ports. Functional identities ("You are the **checker**", "You are one voice…") and the debate card's `You are {role}` placeholder pass, and so do a quoted counter-example on a line that forbids it and a condition ("if you are a PM") | preventive (JCRL v3.5.0): `role-profiles.md` §0 bans persona prompting; without the check that ban rests on every reviewer remembering it |
| `judgment-footer` | a skill that declares a Product-contour `artifact_type` in Step T (types parsed from the `**Product contour:**` line of `template-protocol.md`, `partial` ignored) but never cites `partial/judgment-footer`; People-contour skills are exempt | preventive (JCRL v3.5.0): the altitude line lands in every Product-contour skill in one release — the next skill to add a Step T would ship without it |
| `role-enum` | the `user.role` enum in `role-profiles.md` §2 ≠ the `role` enum in `context-schema.md`, or either line missing | preventive (JCRL v3.5.0): one enum kept in two files — drift means onboarding offers a role that Step 0i treats as "not in the enum" and asks about again, or the reverse |
| `judgment-points` | a skill listed in `judgment-points.md` §1 that never cites it, or a skill outside §1 that asks the P2 question or renders the P3 confidence line (a negated mention passes) | preventive (JCRL v3.7.0): §1 is the complete list of judgment points — a question or line outside it has no switch, skip rule or test |
| `evidence-classes` | the six-class enum of `pm-mental-model.md` §4 drifting from its canonical copies (vault-schema, Gate 4b), an invented class word inside a label, a P7-bound skill that never cites Gate Check 6, or a live "5 universal gate checks" count | preventive (JCRL v3.8.0): one vocabulary read by the gate, the checker, the vault and every artifact skill |
| `judgment-binds` | a skill that the P4 / P6 / P8 *Binds* of `pm-mental-model.md` (since v3.9.0) or a `judgment-points.md` §7–§9 table names, but whose `SKILL.md` and `references/` never cite that section; a §7–§9 table row or a Binds token next to a § citation that is not a skill; a live forward marker ("from / arrives in / lands in vX.Y.Z") at or below the version in `plugin.json` — a shipped behaviour reads "since vX.Y.Z" | preventive (JCRL v3.9.0): a principle acts only through a step that implements it (`pm-mental-model.md` §5) — a Binds entry with no implementing text is a promise Step 0j reads as a live rule, and a "from v3.9.0" left in the tree after the release reads as not shipped yet |

Validator checks added for the cross-host release (v3.0.0) and later, in `validate-consistency.sh`:

| Check | Catches | Shipped example it would have caught |
|-------|---------|--------------------------------------|
| 12 `description routing order` | a routing guard that does not survive Codex's ~190-character cut; a guard naming a non-existent skill; a description with no Ukrainian keywords | the v2.x order put "Do NOT use" and every Ukrainian trigger after character 400 — cut on every real Codex host |
| 13 `commands typed-only` | `$1` / `$ARGUMENTS` in a command body (Codex skips the command); a command description that does not open with the typed-only guard | 4 of 5 commands never migrated; once they did, `«який статус плагіна»` routed to `source-command-status` (trigger-evals L 4/9) |
| 14 `host packaging` | a skill or command without the Path rule; an `agents/*.md` without its `.codex/agents/*.toml` port, or (since v3.8.0) a port whose instructions drift from the agent body beyond the host note; a skill missing from `testing/host-matrix.md` | Codex resolved `references/data-policy.md` against the skill folder — 3 of 4 shared protocols unreachable from write-concept |
| 15 `thin core` (v3.4.0) | a `SKILL.md` longer than 400 lines — the thin-core rule | seven skill cores had drifted to 405–617 lines while `harness-map.md` still described them as "thin ≤400"; nothing measured it |

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

A check nobody has watched fail is a promise, not a test: a regex that matches nothing reads exactly like a clean repo. `testing/seeded_leak_test.py` copies the tree to a temp dir, applies one known-bad edit at a time, and asserts the linter goes RED with the expected check tag. Twenty-seven seeds: twelve org-leak seeds, one per defect class that actually shipped, written with a fictional org (`Zorg`, `ZORG`) so no real identifier enters the repository; four preventive role-layer seeds for checks 19–22 (JCRL v3.5.0) — a role-name branch appended to a `SKILL.md`, a persona prompt appended to a reference, the `partial/judgment-footer` citation removed from `write-concept`, `eng_lead` dropped from one of the two role enums; four judgment-point seeds for check 23 (three in v3.7.0, and since v3.9.0 `quarterly-planning` losing its §1 / §2 citation while it still cites §7); four evidence-class seeds for check 24 (v3.8.0); and two judgment-binds seeds for check 25 (v3.9.0) — `quarterly-planning` losing every citation of `judgment-points.md` §7, and a `from v<plugin version>` marker put back into the P6 *Binds* (the seed reads the version from `plugin.json`, so it proves the rule before and after the release bump); and one provider-contract seed for check 26 (v3.10.0) — a `vault_get_backlinks` call appended to `vault-protocol.md`, the class of invented tool names the L2 level carried until then. A seed appends a line, removes the first line matching a regex (or, since v3.8.0, every matching line — `remove-all`, for a citation repeated in one file), or replaces a regex once; a seed that changes nothing is reported as missed, never as caught. It runs in both CI workflows and after any edit to `skill_lint.py`.

```
baseline: GREEN ✅   seeds: 27
  ✅ authority: per <Org> convention  → expected [org-signature]
  …
caught 27/27 seeded defects
```

**Rule:** a new check lands with its seed in the same commit. If you cannot write a line that the check must reject, the check does not describe anything.

## Test case format

```yaml
- id: TC-<area>-<release>-<slug>
  skill: <skill>
  stage: lint | trigger | scenario | output | integration | regression | host
  input: <phrase / scenario / mock-context / fixture>
  expected: <expected behavior/structure/resolution>
  actual: <filled in during the run>
  status: pass | fail | blocked | n/a | _pending_
  notes: <details, link to bug; for a pass after fixes — "fixed: …">
```

In `testing/test-cases.md` a case is one line: `- **<id>** (alias) | <input> | expected: … | <status> — <notes>`.

- **Id** (since v3.4.0): `TC-<area>-<release>-<slug>` — `area` is the kind of behaviour (`lint`, `val`, `seed`, `trig`, `scn`, `int`, `reg`, `host`, `hook`, `role`, `jdg`, `cfg`, `vault`, …), `release` the version without dots (`390` for v3.9.0), `slug` what the case is about; for example `TC-jdg-390-build-first`. A specification's own id (`TC-jdg-05`) is kept as an alias in brackets. Older ids (`TC-<skill>-<stage>-<n>`, `TC-lint-001`) stay as they shipped.
- **Status rule.** `pass` means the expected behaviour holds on the final tree, with its evidence (a date, a count, a run). A case that went green only after fixes is still `pass`, with the fixes as a note: `**pass** — fixed: <what failed and what changed>` — never a separate "pass after fixes" status. `fail`, `blocked` and `n/a` name their reason; `_pending_` until the case runs.
- **History is not rewritten.** When a later release changes an expectation, the new case says what it supersedes, and the old row gets a short "superseded by …" note; its recorded result stays.

The case registry is `testing/test-cases.md`; updated EVERY release (new cases for new skills/fixes + regression cases for affected skills), releases newest first, with "Coverage gaps" at the bottom.

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
6. Commit, PR, merge on the canonical remote. release.yml validates, then creates the tag and the
   GitHub Release from the CHANGELOG section — do not create them by hand. Then push main and the
   tag to each mirror remote (release-manager Step 7). Move on to the next version.
```

## Subagent orchestration

| Work | Executor |
|--------|-----------|
| Static lint | script (bash) — deterministic, no agent |
| Trigger eval (per group) | live runs on each host (Claude Code, Codex CLI) from a neutral working directory — `trigger-evals.md` → How to run |
| Scenario walk (per skill) | "dry run" subagent per skill |
| Integration / Regression | subagent per chain/group of dependents |
| Consolidation, debug decisions, version | main agent |

Rule: heavy read/eval passes — by subagents (keep the main context clean); fix and bump decisions — main agent, with PM confirmation on risky ones.

## Stage 1c — the two-host smoke (`testing/host-smoke.sh`)

Static checks prove the tree is consistent; they cannot prove a host still loads it — v3.0.0's `git-subdir` source was valid JSON and Codex listed zero plugins. `host-smoke.sh` installs the plugin on both hosts and fails on the first regression: Claude Code must validate the manifest, load every skill on disk, run the SessionStart hook and state the current version; Codex CLI must list every skill plus every migrated command and carry `references/` and `.codex-plugin/plugin.json` in its cache. Its summary line is pasted into every release PR. Add a host here when the plugin starts supporting one.

- **What each leg installs.** The Claude leg loads the working tree; the Codex leg installs a `git archive HEAD` copy, so it proves only what is committed — run it after the release commit.
- **Both legs run from a neutral directory.** The Claude leg always has (a temp dir); since v3.9.0 every `codex` call does too — an empty temp dir, removed at the end. Codex merges a project-local `.codex/config.toml` from its working directory into its config, so an untracked one in the repo root — the developer's own, never the plugin's — can break the config load and fail the leg for a reason that has nothing to do with the plugin; the v3.8.0 release run failed on exactly that and passed from a neutral directory. `CODEX_HOME` is deliberately not moved: it would also move the plugin cache the leg reads and drop the login. The trigger-eval live runs use a neutral directory for the same reason.

## Version Definition of Done

- `bash testing/host-smoke.sh` green on the release machine — both legs, the Codex leg after the release commit — summary line in the release PR (since v3.0.2).
- `bash testing/validate-consistency.sh`: every check group green.
- Lint: 0 FAIL (26 checks as of v3.10.0).
- Seeded-leak test: 27/27 caught (and a new seed for every new check).
- `python3 testing/session_start_test.py`: every digest case passes (12/12 as of v3.10.0) — it is not in CI, so it runs here.
- `python3 testing/ctx_common_test.py` (8/8) and `python3 testing/provider_bundle_test.py` (since v3.10.0): the provider helpers and the bundle builder on the fictional fixture core — not in CI, so they run here.
- `python3 testing/branch_leak_scan.py --base main` (since v3.10.0): clean — no organisation identifier in any line the branch adds or in its commit messages; `python3 testing/branch_leak_scan_test.py` proves the scan fires.
- `python3 testing/write_gate_test.py` (since v3.10.0): every gate case passes — the provider boundary and the Jira/Confluence branch; not in CI, so it runs here.
- Every example added or touched this version is universal — placeholders, no team signature, language-neutral code blocks, no domain-specific detail.
- Trigger: ≥ 90 % per group — positive and neighbour rows alike — on each supported host (Claude Code and Codex CLI, live, from a neutral directory; a host not re-run must be named in the release notes).
- Output eval (3b): every artifact-producing skill changed in the release scores ≥ its rubric's pass_threshold, with host and model recorded.
- Scenario: for every changed skill the key steps/gates/format are present.
- Integration: all chains and references resolve.
- Regression: neighboring skills behave as before the change.
- CHANGELOG + README + frontmatter versions are consistent; test-cases.md updated, and every case of the release has a status (`_pending_` is not a release status).
- Backup and tag in place.

> All changes stay **additive/safe for Claude**: keep trigger phrases; remove nothing without a regression check of dependents.
