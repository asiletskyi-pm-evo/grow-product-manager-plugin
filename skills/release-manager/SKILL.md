---
name: release-manager
version: 0.2.3
description: Release the plugin repository itself — version bump, CHANGELOG, validation, PR, GitHub Release, mirror sync. Not product feature releases in Jira (product-reporter / sprint-planning). UA — «зарелізь плагін», «підготуй реліз v…», «bump версії плагіна». EN — "release the plugin", "prepare a release", "bump plugin version", "ship vX.Y.Z", "cut a release", "publish plugin release". Also UA — «випусти vX.Y.Z», «опублікуй реліз плагіна». Conversational "release the plugin" routes here; the user-typed /release command is a shortcut into the same skill.
---

# Release Manager

> **Path rule.** A bare `references/<file>.md` in this file is read from this skill's own `references/` if the file exists there, otherwise from the **shared** `references/` at the plugin root. Resolve the root as `${PLUGIN_ROOT}`, else `${CLAUDE_PLUGIN_ROOT}`, else the directory that contains `skills/`, found by walking up from this folder (`references/host-profiles.md` §6). Never continue without a protocol named here.

Releases the plugin repository itself: one guided pipeline from "changes are ready" to "both remotes tagged, Release published, docs consistent". Built from the real v1.26.1–v1.27.0 release experience — every known pitfall has a guard. **The user stays in the loop:** every irreversible step (commit, push, merge, publish) is gated.

Generic by design: works for any Claude plugin repo with `.claude-plugin/` manifests + CHANGELOG + README. Org-specific details (mirrors, VPN hosts, Confluence changelog page) come from `local-context.md`, never hardcoded.

## Prerequisites
- `references/local-context-protocol.md` — Step 0.
- `skills/release-manager/references/release-pitfalls.md` — known failure modes and their guards. **Read before Step 1.**
- `references/persistent-storage.md`, `references/vault-protocol.md` — for the post-release vault record.

Release config in local-context (`plugin_release` section, all optional — ask and offer to save on first run):
`repo_path`, `canonical_remote` (default `origin`), `mirror_remotes` (e.g. `gitlab`), `vpn_required_hosts`, `protected_branches` (default `main`), `confluence_changelog_page_id`, `versioning_table` (defaults to PATCH/MINOR/MAJOR rules from CHANGELOG header).

## Pipeline

### Step 0 — Local context
Per `local-context-protocol.md`. Load `plugin_release` config; if absent, collect repo path + remotes interactively and offer to save.

### Step 1 — Pre-flight (guards)
1. Repo reachable? If the path is under an iCloud-synced folder (macOS `~/Documents`, `~/Desktop`) — materialize first: `brctl download <repo>` + bulk-read sweep (pitfall P1).
2. Stale git locks: delete `.git/*.lock` older than 60 min (pitfall P2).
3. `git status` — working tree must contain only the expected release changes; anything unexpected → show and gate.
4. `git fetch <canonical>`; local main behind → offer `git pull --ff-only`.
5. Read current version from `plugin.json` `"version"` field (structured — never parse description text).

### Step 2 — Scope & version decision
1. Collect changes since the last tag (`git log <last-tag>..HEAD --oneline` + working tree diff summary) or from the user's description.
2. Classify per the versioning table: wording/formatting → PATCH; new skill/step/section → MINOR; workflow restructure/breaking → MAJOR.
3. Propose `vX.Y.Z` + draft scope summary. **Gate: user confirms version and scope.**

### Step 3 — Apply the bump (the 6 mandatory places)
1. `.claude-plugin/plugin.json` — `"version"` field + description tail `— vX.Y.Z (released YYYY-MM-DD)`.
2. `.claude-plugin/marketplace.json` — plugin entry `"version"` + both description tails.
2a. `.codex-plugin/plugin.json` (since v3.0.1) — `"version"` + the same description as plugin.json; validator check 1 compares them.
3. `README.md` — header + footer `**Version:**`; if skills changed: section headers, Skills Summary rows, "New in vX.Y.Z" overview paragraph.
4. `CHANGELOG.md` — prepend the entry (Added/Changed/Fixed, files table with skill version bumps, Backwards compatibility note). No editorial placeholders — write the final text directly (pitfall P3).
5. **Component counts** (since v2.5.0) — the phrase `N skills, N agents, N commands, N connectors` in `plugin.json`, `marketplace.json` and README must equal what is on disk (`skills/*/`, `agents/*.md`, `commands/*.md`, `.mcp.json` keys). Validator check 10 fails the release otherwise. Adding an agent, a command or a connector is a MINOR bump.

This pipeline is also reachable as `/grow-product-manager:release [patch|minor|major]` — the command pre-answers Step 2's classification and changes nothing else.

Skill frontmatter versions are normally bumped in the feature PRs themselves; verify they match the CHANGELOG claims.

### Step 4 — Validate (static + both hosts)
1. `bash testing/validate-consistency.sh` and `python3 testing/skill_lint.py` locally. Any `FAIL:` → fix before proceeding. Never ship with a red validator — CI will reject the PR anyway.
2. **`bash testing/host-smoke.sh`** (since v3.0.2) — loads the working tree on **both hosts** and fails if either breaks: Claude Code (`claude plugin validate .`, then a headless `claude -p --plugin-dir` run that must report every skill on disk, the SessionStart digest and this version) and Codex CLI (a throw-away marketplace install that must list every skill + every migrated command, carry `references/` and the Codex manifest in its cache). CI cannot run it (no host auth), so its final line — `✅ host-smoke passed (vX.Y.Z: Claude + Codex)` — goes verbatim into the release PR body. A red host-smoke is a release blocker exactly like a red validator; `SKIP_CLAUDE=1` / `SKIP_CODEX=1` only for a host that is not installed on the release machine, and say so in the PR.

3. **Host claims carry a source.** Every sentence in README, CHANGELOG, `references/host-profiles.md` or `testing/host-matrix.md` that says what a host *does* (update cadence, filesystem, connectors, subagents) is either **measured** in this release (name the host version and the command) or **vendor-documented** (link the doc, issue or PR). A claim with neither is not shipped — rewrite it as "not verified" or drop it. Two wrong claims reached stakeholders in v3.0.0 because stage-0 assumptions ("Codex has no auto-update", "ChatGPT has no filesystem") were never re-checked against the vendor docs.

### Step 5 — Commit & push (terminal block, gated)
Claude's sandbox has no user git credentials — generate one copy-paste terminal block and wait for the result:
```
cd <repo>
git checkout -b release/vX.Y.Z
git add <explicit file list — never git add -A>
git commit -F - <<'MSG' … MSG
git push -u <canonical> release/vX.Y.Z
```
Guards: push rejected with "workflow scope" → token lacks Workflows permission (pitfall P4); "could not resolve host" → VPN (pitfall P5).

### Step 6 — PR → merge → Release (GitHub)
Via browser (user's session) or `gh` CLI if available:
1. PR `release/vX.Y.Z` → main; wait for the CI check to pass.
2. Merge (merge commit), delete branch. **Merge on the canonical remote only** — never merge the same branch on a mirror (pitfall P6).
3. Release: tag `vX.Y.Z`, target `main`, title `vX.Y.Z — <headline>`, notes from the CHANGELOG entry. Publishing creates the tag — no local tagging needed.

> **Merging ≠ releasing.** A merged PR does NOT create the tag or the Release — observed twice in live runs ("зарелізив" turned out to mean "merged"). After the merge, always verify `releases/latest` shows the new version; if not, the Release step still needs to happen.

### Step 7 — Sync local + mirrors (terminal block, gated)
```
git checkout main && git pull --ff-only <canonical> main
git fetch <canonical> --tags
git push <mirror> main --tags        # per mirror; VPN reminder if host is in vpn_required_hosts
git branch -d release/vX.Y.Z
```
Mirror push rejected non-fast-forward → mirror diverged: never force into a protected main; use the reconciliation-merge recipe from release-pitfalls.md (P6).

### Step 8 — Post-release
1. **Verify:** fetch `releases/latest` on the canonical host → must show `vX.Y.Z`. Raw-file CDN may lag a few minutes — don't panic on stale `raw.githubusercontent.com` (pitfall P7).
2. Confluence: if `confluence_changelog_page_id` is set — append the release entry via Atlassian MCP (gate before writing).
3. **Step V — Vault Save:** per `vault-protocol.md`, `vault_save({ type: "decision", product: "general", skill: "release-manager", tags: ["release"], … })` → `Decisions/general/decision-release-vX-Y-Z-<date>.md` (version, date, scope, links to Release and CHANGELOG). There is no `Decisions/Releases/` area — the release record IS a decision, tagged `release`.
4. Remind the user to update their installed plugin from the marketplace.

## Quality Standards
- Version is read and written only via the structured `"version"` fields; description tails are derived, never the source of truth.
- Explicit `git add` file lists; never `-A` (protects unrelated WIP).
- Every push/merge/publish — user-gated; Claude prepares, the user (or their browser session) executes.
- Force push is never used on protected branches; mirror divergence is resolved by merge, not history rewrite.
- All numbers and versions in the CHANGELOG entry must match frontmatter reality — the validator is the referee.

## Skill Chaining
← any skill-changing work (feature PRs) · → `write-concept` (release notes draft for major releases) · → Confluence changelog page · → vault release record.
