# Release pitfalls — known failure modes and guards

Every entry below happened for real during the v1.26.1–v1.27.0 releases (2026-07-02/03). Check this list before and during every release.

## P1 — iCloud-evicted files break git

**Symptom:** `Resource deadlock avoided` on reads through mounts; `error reading from .git/objects/pack/…: Operation timed out`; `file …pack is far too short to be a packfile`; interrupted commits leaving lock files.
**Cause:** repo lives under an iCloud-synced folder (`~/Documents`, `~/Desktop` with "Optimize Mac Storage") — file contents are evicted to the cloud; git hits dataless placeholder files.
**Guard:** before any git work: `brctl download <repo>` then force materialization: `find <repo> -type f -print0 | while IFS= read -r -d '' f; do cat "$f" >/dev/null 2>&1 || true; done`. Verify with `git cat-file -e HEAD`.
**Fix long-term:** keep the repo outside iCloud (e.g. `~/dev/`) or disable Optimize Mac Storage.

## P2 — Stale git lock files

**Symptom:** `.git/HEAD.lock`, `.git/index.lock` present; git refuses operations.
**Cause:** an earlier git process was interrupted (often by P1).
**Guard:** delete locks older than 60 minutes: `find .git -maxdepth 1 -name '*.lock' -mmin +60 -delete`. Never delete fresh locks — a live process may own them.

## P3 — Editorial placeholders shipped in CHANGELOG

**Symptom:** `<!-- Препенди цей блок… -->` instructions left in the released CHANGELOG (lines 15–19 pre-v1.26.1).
**Cause:** manual prepend workflow — the instruction comment shipped instead of being replaced.
**Guard:** write final CHANGELOG text directly; the validator rejects `^<!-- Препенди` at line start. Historical entries may mention the pattern in prose — that's fine.

## P4 — GitHub token lacks `workflow` scope

**Symptom:** `! [remote rejected] … (refusing to allow a Personal Access Token to create or update workflow .github/workflows/… without workflow scope)`.
**Cause:** pushing changes to `.github/workflows/` requires the Workflows permission.
**Guard:** fine-grained PAT with **Contents: Read and write** + **Workflows: Read and write** (Metadata is implicit). Replace keychain credential: `printf "protocol=https\nhost=github.com\n" | git credential-osxkeychain erase`, then push again and enter username + new token.

## P5 — Mirror host requires VPN

**Symptom:** `Could not resolve host: internal-gitlab-host`.
**Cause:** internal GitLab is reachable only under VPN.
**Guard:** list such hosts in `plugin_release.vpn_required_hosts`; remind before the mirror-push step; the push is retryable at any time — nothing is lost.

## P6 — Mirror main diverged / protected

**Symptom:** `! [rejected] main -> main (fetch first)` on the mirror; then `You are not allowed to force push code to a protected branch`.
**Cause:** the same feature branch was merged separately on the mirror (its own MR merge commit) → histories diverge; mirror main is protected, so force push is blocked.
**Guard:** merge PRs **only on the canonical remote**; mirrors receive plain `git push <mirror> main --tags` (fast-forward).
**Recovery (reconciliation merge):**
```
git fetch <mirror>
git log --oneline main..<mirror>/main     # inspect what's unique — must be only parallel merges of known content
git merge <mirror>/main -m "Merge parallel mirror merge of vX.Y.Z (mirror reconciliation)"
git push <mirror> main && git push <canonical> main
```
One service merge commit joins the histories permanently; never rewrite a protected branch.

## P7 — Stale CDN on raw.githubusercontent.com

**Symptom:** `raw.githubusercontent.com/...` serves an old file version minutes-to-hours after merge, while the repo UI shows the new one.
**Cause:** raw CDN caching.
**Guard:** verify releases via `releases/latest` page or the repo file view, not raw URLs; don't re-push on a stale raw read.

## P8 — GitHub comment editor auto-continues lists

**Symptom:** pasted/typed markdown bullets become `- - item` in Release notes / PR bodies.
**Cause:** the web editor auto-inserts `- ` on Enter after a list line.
**Guard:** when automating via browser, set the textarea value directly (form input), don't simulate typing line by line.

## P9 — New terminal window ≠ repo directory

**Symptom:** `fatal: not a git repository … .git` right after opening a fresh terminal.
**Cause:** command run from `~` instead of the repo.
**Guard:** every generated terminal block starts with `cd <repo>`.
