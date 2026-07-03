---
name: release-manager
version: 0.1.0
description: Release a Claude plugin end-to-end — version bump across all manifests, CHANGELOG entry, README sync, consistency validation, commit/PR/merge, GitHub Release with tag, mirror sync, and post-release verification. Use when the user asks to "release the plugin", "prepare a release", "bump plugin version", "ship vX.Y.Z", "cut a release", "publish plugin release", or after a batch of plugin changes is ready to ship. Українською: "зарелізити плагін", "підготуй реліз", "bump версії плагіна", "випусти vX.Y.Z", "опублікуй реліз плагіна". Do NOT use for releasing product features in Jira (use team-ops-reporter / sprint-planning) — this skill releases the plugin repository itself.
---

# Release Manager

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

### Step 3 — Apply the bump (the 4 mandatory places)
1. `.claude-plugin/plugin.json` — `"version"` field + description tail `— vX.Y.Z (released YYYY-MM-DD)`.
2. `.claude-plugin/marketplace.json` — plugin entry `"version"` + both description tails.
3. `README.md` — header + footer `**Version:**`; if skills changed: section headers, Skills Summary rows, "New in vX.Y.Z" overview paragraph.
4. `CHANGELOG.md` — prepend the entry (Added/Changed/Fixed, files table with skill version bumps, Backwards compatibility note). No editorial placeholders — write the final text directly (pitfall P3).

Skill frontmatter versions are normally bumped in the feature PRs themselves; verify they match the CHANGELOG claims.

### Step 4 — Validate
Run `bash testing/validate-consistency.sh` locally. Any `FAIL:` → fix before proceeding. Never ship with a red validator — CI will reject the PR anyway.

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
3. **Step V — Vault Save:** per `vault-protocol.md`, save a release record (version, date, scope, links to Release and CHANGELOG) to the vault `Decisions/Releases` area with `skill_version` frontmatter.
4. Remind the user to update their installed plugin from the marketplace.

## Quality Standards
- Version is read and written only via the structured `"version"` fields; description tails are derived, never the source of truth.
- Explicit `git add` file lists; never `-A` (protects unrelated WIP).
- Every push/merge/publish — user-gated; Claude prepares, the user (or their browser session) executes.
- Force push is never used on protected branches; mirror divergence is resolved by merge, not history rewrite.
- All numbers and versions in the CHANGELOG entry must match frontmatter reality — the validator is the referee.

## Skill Chaining
← any skill-changing work (feature PRs) · → `write-concept` (release notes draft for major releases) · → Confluence changelog page · → vault release record.
