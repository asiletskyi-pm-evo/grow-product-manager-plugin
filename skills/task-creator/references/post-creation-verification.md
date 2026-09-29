# Post-creation verification — Step 12 (12a–12e)

> Part of `task-creator`. Loaded on demand after the Jira issues are created. The step heading, the mandatory-gate rule and a one-line summary stay in SKILL.md.

**12a. Select a task for verification:**

Pick one of the created tasks (preferably a development task — FE or BE — as they have the most complex field set).

**12b. Read the task back from Jira:**

Use `getJiraIssue` to fetch the created task with all fields. This ensures we verify what was actually saved, not what we intended to send.

**Maker–checker separation (v0.11.0):** the agent that created the tasks does not evaluate them. The maker fetches the raw task data (this step), then passes it — together with the requirements content and the check table below — to the **`grow-product-manager:artifact-checker`** agent (`references/artifact-style-gate.md` → Execution model) that has no access to this conversation's reasoning. The checker returns findings; the maker applies fixes (12d). If subagents are unavailable — run inline and mark the report "незалежність перевірки знижена (inline)".

**12c. Run verification checks:**

| Check | What to verify | How to verify |
|-------|---------------|--------------|
| **Title format** | Matches the pattern: `[WorkType] - Grooming/A/B Test - FeatureName` | Compare with the expected title from Step 7 rules |
| **Parent** | Linked to the correct Epic | Check `parent` field matches the Epic key |
| **No altitude line** (since v3.5.0) | A task body carries no `Altitude:` line — the judgment footer belongs on an epic this run created and on the Step 11 report only | Scan the description; a hit is reported, and the line is removed only after the user confirms — never propose an edit that adds one |
| **Reporter** | Set to the user's accountId | Compare with `user.jira_account_id` |
| **Team** | Set to the correct team | Compare with the confirmed team value from Step 6b |
| **Labels** | Contains all required labels: feature code, work type label, `a/b_test` if applicable, `grooming` if applicable | Check labels array against expected values |
| **Components** | Matches the confirmed components | Compare with the confirmed values from Step 6b |
| **Description** | Contains "Why", "What", "How", "Definition of Done" and "Requirements" (with Confluence link) sections — the Step 7 format | Parse description content |
| **Issue Type** | Correct type (Task/Design/Analytics) | Check issue type field |
| **Links** | Correct dependency links created (if linking was confirmed) | Check issue links via `getJiraIssue` |
| **List formatting** | "What"/"How"/DoD are lists or short structured blocks, not paragraph prose | Gate 2 checklist (`references/artifact-style-gate.md`) |
| **No ungrounded tech content** | No technical assumptions outside the "Технічні рекомендації (AI)" section; that section (if present) opens with the AI callout | Gate 1 source test against the requirements page |

**12d. Report verification results:**

**If all checks pass:**
> "I verified task [KEY] and all fields are correct: title format, parent, reporter, team, labels, components, description, and links all match the expected values."

**If issues are found:**

Present a clear report to the user:

> "I verified task [KEY] and found the following discrepancies:"

| # | Field | Expected | Actual | Severity |
|---|-------|----------|--------|----------|
| 1 | Labels | `frontend`, `PROJ-1234.5` | `frontend` (missing feature code) | Critical |
| 2 | Team | Team Name | (not set) | Critical |
| 3 | Title | `[FE] Feature Name` | `[FE] - Feature Name` (extra dash) | Minor |

Then propose fixes:

> "I can fix these issues automatically. Here is what I'll do:
> 1. Add missing label `PROJ-1234.5` to [KEY] and all other created tasks
> 2. Set Team field on [KEY] and all other created tasks
> 3. Update title on [KEY]
>
> Should I apply these fixes?"

- If user confirms → apply fixes using `editJiraIssue` for ALL affected tasks (not just the verified one — the same issues likely affect all tasks)
- If user wants to review first → show the proposed changes for each task before applying
- After fixes are applied → re-verify the same task to confirm the fixes worked

**12e. Cross-task fix propagation:**

If an issue is found in the verified task, assume it may affect ALL created tasks (since they were created with the same logic). When fixing:
- Fix the verified task first
- Apply the same fix to all other tasks
- Report how many tasks were fixed
