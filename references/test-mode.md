> Reference: Test Mode (sandbox) workflow for plugin-configurator. Extracted from SKILL.md in v1.24.

## Workflow — Test Mode (sandbox)

Test Mode lets the maintainer (and any user who wants to preview onboarding) walk through the full configuration flow without touching real plugin data. All writes are redirected to `~/.grow-pm-sandbox/`. The real `~/.grow-pm/` directory is **never** read or modified during a Test Mode run.

### TM-0. Trigger detection

Test Mode is entered when:
- The user types one of: `dry-run onboarding`, `test mode`, `sandbox onboarding`, `тестовий режим`, `пройти налаштування без змін`.
- The user picks **Test mode (sandbox)** in Onboarding Step 2.
- The user explicitly invokes `configure plugin → test mode` from the Configurator menu.

When Test Mode is detected, set `selected_mode = test` in session memory. Show a banner that persists across all subsequent steps:

> "🧪 **TEST RUN** — All writes redirected to `~/.grow-pm-sandbox/`. Your real `~/.grow-pm/` is not touched."

### TM-1. Sandbox isolation rules

The following invariants MUST hold throughout a Test Mode session:

| Operation | Production path | Test path |
|-----------|----------------|-----------|
| `local-context.md` | `~/.grow-pm/local-context.md` | `~/.grow-pm-sandbox/local-context.md` |
| `.schema-version` | `~/.grow-pm/.schema-version` | `~/.grow-pm-sandbox/.schema-version` |
| Knowledge Library | `~/.grow-pm/knowledge-library/` | `~/.grow-pm-sandbox/knowledge-library/` |
| Template Library | `~/.grow-pm/template-library/` | `~/.grow-pm-sandbox/template-library/` |
| Backups | `~/.grow-pm/backups/` | `~/.grow-pm-sandbox/backups/` |
| Vault Mirror | enabled (mirrors to user's vault) | **fully skipped** — no Vault writes occur in Test Mode |

Real `~/.grow-pm/` must NOT be read during Test Mode (otherwise Reinstall mode would trigger unwanted recovery flows). The sandbox is fully self-contained.

The `local-context.md` produced in Test Mode has its title changed to:

```markdown
# Local Context — Grow Product Manager (TEST RUN)
```

so it is visually unambiguous if the user opens the file later.

### TM-2. Walk through Onboarding (steps 1-16)

Run the full Onboarding workflow (Steps 1-16) exactly as in production, but with the path mapping from TM-1. The user experiences the real flow — same questions, same connector pre-checks, same validation — only writes go to the sandbox.

In Step 16 (Review + Save), the storage root is `~/.grow-pm-sandbox/`. The `Onboarding Status` section is populated with `last_test_run_at: {now}` (instead of `basic_completed_at` / `extended_completed_at`).

**Skip Step 17 (Quick Wins)** in Test Mode — instead, proceed to TM-3 (the Test Mode finale).

### TM-3. Test Mode finale — diff and decision

After save:

1. **Compute diff** vs. real config (if `~/.grow-pm/local-context.md` exists):
   - Run `diff -u ~/.grow-pm/local-context.md ~/.grow-pm-sandbox/local-context.md` (or equivalent reading via the Read tool).
   - Render the diff as a readable markdown block with `+` / `-` / context lines.
   - Highlight high-impact differences: any change to required fields (`User Profile`, `Organization`, core `Product` fields, `Onboarding Status.mode`).

2. **Present three options** via `AskUserQuestion`:

   - **Discard sandbox (Recommended)** — delete `~/.grow-pm-sandbox/` entirely. Real config is unchanged. Inform: "Sandbox discarded. Your real configuration is unchanged."
   - **Promote to real** — replace `~/.grow-pm/` content with sandbox content. **Before promoting, create a safety backup** at `~/.grow-pm/backups/pre-promote-{timestamp}/` containing the current real config. Then copy sandbox files over. Inform: "Promoted sandbox to `~/.grow-pm/`. A safety backup of your previous config is at `~/.grow-pm/backups/pre-promote-{timestamp}/`."
   - **Keep sandbox for later** — leave `~/.grow-pm-sandbox/` in place. Future `dry-run onboarding` calls can re-use or re-overwrite it. Inform: "Sandbox kept at `~/.grow-pm-sandbox/`. You can re-run Test Mode any time."

3. **Reset session memory** — clear `selected_mode = test` flag at the end so subsequent Configurator runs do not accidentally inherit Test Mode behavior.

### TM-4. Safety guarantees

- If any step in TM-2 fails, the failure must be confined to the sandbox. Real config remains intact.
- If the user aborts mid-flow (Cancel / Quit), the sandbox is left as-is and the user is informed they can resume later or run `discard sandbox` to clean up.
- The "TEST RUN" banner must be shown at least once in every visible message during Test Mode so the user never confuses Test Mode for a real run.
- If Test Mode is invoked while a previous sandbox already exists, ask up front: "Continue from existing sandbox / Start fresh sandbox / Cancel".

### TM-5. Verification matrix (for maintainers)

After implementing or modifying Test Mode, verify each invariant:

| # | Invariant | How to check |
|---|-----------|--------------|
| 1 | Real `~/.grow-pm/` is not modified | `stat -c %y ~/.grow-pm/local-context.md` before and after Test Mode — timestamp unchanged |
| 2 | Sandbox `~/.grow-pm-sandbox/` exists after run | `test -d ~/.grow-pm-sandbox/` returns 0 |
| 3 | Sandbox `local-context.md` has TEST RUN title | `grep "TEST RUN" ~/.grow-pm-sandbox/local-context.md` matches |
| 4 | Onboarding Status mode = `last_test_run_at` set | `grep "Last test run at" ~/.grow-pm-sandbox/local-context.md` shows recent timestamp |
| 5 | Vault Mirror was skipped | No new files in user's vault `_System/` folder |
| 6 | Discard removes sandbox cleanly | `! test -e ~/.grow-pm-sandbox/` returns 0 |
| 7 | Promote creates safety backup | `ls ~/.grow-pm/backups/pre-promote-*` shows new folder |
