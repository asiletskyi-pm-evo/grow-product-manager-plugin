---
name: feature-task-creator
version: 0.8.0
description: Creates Jira tasks for feature implementation based on requirements from a Confluence page. Use when the user asks to create tasks for a feature, create Jira issues from Confluence requirements, break down a feature into development tasks (FE/BE/Android/iOS/Design/Analytics), set up feature tasks in an Epic, or says something like "create tasks from requirements". Also trigger when the user shares a Confluence link and asks to create Jira tasks from it.
---

# Feature Task Creator

Automate creation of Jira tasks for feature implementation based on requirements from a Confluence page. Handles the full lifecycle: reading requirements, creating structured tasks per work type, filling all required fields, and linking tasks by dependency logic.

## Integration prerequisite

Before starting, read and follow the integration fallback chain in `references/integration-strategy.md`. This skill requires:

- **Confluence** — for reading feature requirements pages
- **Jira** — for creating issues, setting fields, linking tasks

For each product: check for MCP connector → search MCP registry → fall back to browser.

Before gathering any data, also read and comply with `references/data-policy.md`. Confidential data must NOT be passed to external LLMs or third parties.

## Local context prerequisite

**Before starting, follow `references/local-context-protocol.md` (Step 0).** Read `local-context.md`, select the active product, and load all product-specific context. If the file doesn't exist — redirect to Plugin Configurator for initial setup.

Key context used by this skill:
- `product.jira_project_key` — for finding Epics and creating tasks
- `user.jira_account_id` — for setting Reporter on tasks
- `team.jira_team_id` — for setting Team field
- `team.members` — for discovering assignees and roles
- `product.confluence_space` — for Confluence page links
- `user.language` — for output language

## Step T — Template Resolution

This skill creates Jira tasks (and sometimes Epics). When generating the task **description / body** and when filling Epic fields, resolve templates for each artifact.

Follow `references/template-protocol.md`. Run Step T twice:

**T-A. For each task being created:**
- `artifact_type: task`
- `subtype: {FE | BE | iOS | Android | Design | Analytics | QA | DevOps}` (map from the task's work type)
- `product_id: {from local-context.md active product}`
- `language: {from local-context.md}`

**T-B. If the Epic is being created or modified:**
- `artifact_type: epic`
- `subtype: null`
- `product_id: {from local-context.md active product}`
- `language: {from local-context.md}`

In batch mode (creating many tasks at once), resolve templates ONCE per subtype at the start of the run and reuse — do not re-ask the user per task. Use `templates.preference=auto` semantics for batch runs regardless of the global setting.

Append `<!-- template: {template_id} version: {version} -->` at the end of each generated description.

Fall back to built-in `task-builtin-default` and `epic-builtin-default` when no user template applies.

If the user says "do not use a template" → skip Step T and use the skill's internal fallback structure.

## Workflow

### Step 1: Read Requirements from Confluence

When the user provides a Confluence link:

1. Resolve the page — try `getConfluencePage` or `searchAtlassian` / `searchConfluenceUsingCql` to find it
2. Extract from the page:
   - **Feature name** — from the page title (after the code prefix, e.g. "Feature Name Description" from "PROJ-1234.5 - Feature Name Description")
   - **Feature code** — the code in the page title (e.g. `PROJ-1234.5`). Pattern: `EPICKEY-NUMBER.NUMBER`
   - **Epic link** — usually under an "Epic" heading, a link to the Epic's Confluence page or directly a Jira issue key
   - **Technical requirements** — look for mentions of "A/B Test", "під прапором", platform restrictions
   - **Functional requirements** — what needs to be built
   - **Confluence page URL** — for linking in task descriptions

If Confluence MCP is unavailable — follow integration fallback chain.

### Step 2: Find the Epic in Jira

1. Extract the Epic key from the Confluence page content (e.g. `PROJ-1234` from a Jira link or the feature code prefix)
2. Use `getJiraIssue` to fetch the Epic and confirm:
   - Epic key and title
   - Project key (e.g. PROJ)
   - Epic status

If Jira MCP is unavailable — follow integration fallback chain.

### Step 3: Identify the User

Look up the user's Jira account. The user should be set as **Reporter** on all created tasks. Their `accountId` is needed. You can find it from:
- The Epic's assignee (if it's the same user)
- `lookupJiraAccountId` by their email
- Asking the user directly if needed

### Step 4: Ask Clarifying Questions

Before creating tasks, ask the user using AskUserQuestion:

1. **Work types** — which types of tasks to create. Options (multi-select):
   - FE (Front-end WEB)
   - BE (Back-end)
   - Android
   - iOS
   - Design
   - Analytics

2. **Task purpose** — are these tasks for development ("розробка") or for grooming ("грумінг")?
   - **Development** (default) — standard tasks for implementation
   - **Grooming** — preparatory tasks for estimation and discussion. When grooming is selected:
     - Add `grooming` to Labels on all development tasks (FE, BE, Android, iOS)
     - Add "Grooming" to the title of development tasks: `[FE] - Grooming - FeatureName`
     - Design and Analytics tasks are NOT affected by grooming (they keep their standard format)

3. **A/B Test** — is this feature an A/B test? Check if the Confluence page mentions it. If yes:
   - Add `a/b_test` label to ALL tasks
   - Add "A/B Test" to task titles
   - Create 2 Analytics tasks instead of 1 (coverage + analysis)

4. **Design & Analytics** — if not already selected in work types, ask if Design and/or Analytics tasks are needed

### Step 5: Determine Components

The Components field should match the Labels from the Confluence page. Since Confluence page labels may not be directly accessible via API:
- Check existing tasks in the same Epic to see which Components are commonly used
- Ask the user to confirm if unsure

### Step 6: Discover Project Configuration

Before creating tasks, fetch project metadata to ensure correct field values:

1. **Issue Types** — use `getJiraProjectIssueTypesMetadata` to find:
   - Does the project have a "Design" issue type? If yes, use it for Design tasks
   - Does the project have an "Analytics" issue type? If yes, use it for Analytics tasks
   - Otherwise, use "Task" for everything

2. **Team field** — find the custom field ID for Team (usually `customfield_10001`):
   - Use `getJiraIssueTypeMetaWithFields` to find the field
   - Look at an existing task in the Epic to find the Team value/ID format
   - The Team field often requires a string ID (not an object), e.g. `"3eb29614-f447-45a5-8963-016f46f7dded-31"`

### Step 6b: Validate field values before creation

**Before creating any tasks, review ALL field values that will be used.** For each field, apply this decision logic:

| Confidence level | Action |
|-----------------|--------|
| **Certain** — value is explicitly stated in requirements, local-context, or confirmed by user | Use the value directly |
| **Inferred** — value is derived from context but not explicitly confirmed (e.g., Components from existing tasks, Team from Epic) | Present the inferred value to the user with explanation: "Based on [source], I plan to set [field] to [value]. Is that correct?" |
| **Uncertain** — multiple possible values, or no clear source | Ask via AskUserQuestion with proposed options: "I'm not sure which value to use for [field]. Here are the options I found: [list]. Which one should I use?" |
| **Unknown** — no data available to determine the value | Ask the user directly: "I couldn't determine the value for [field]. Could you provide it?" |

**Fields that commonly require user confirmation:**

- **Components** — if not directly available from Confluence labels, propose options from existing Epic tasks
- **Team** — if not found in `local-context.md` or existing tasks, ask the user
- **Issue Type** — if project has non-standard issue types (e.g., custom Design or Analytics types), confirm with user
- **Labels** — if uncertain about the feature code format or additional labels, propose and confirm
- **Reporter** — if multiple possible accounts found, ask user to choose
- **Sprint** — if the user wants tasks added to a specific sprint, ask which one

**Present a pre-creation summary for confirmation:**

> "Here are the field values I'll use for all tasks:"

| Field | Value | Source |
|-------|-------|--------|
| Parent (Epic) | PROJ-1234 | From Confluence page |
| Reporter | User Name | From local-context.md |
| Team | Team Name | Inferred from Epic — please confirm |
| Components | component-1, component-2 | From existing Epic tasks — please confirm |
| Labels (common) | PROJ-1234.5 | From feature code |
| ... | ... | ... |

Wait for user confirmation before proceeding to task creation.

### Step 7: Create Tasks

For each selected work type, create a Jira issue with these fields:

#### Common fields for ALL tasks:

| Field | Value |
|---|---|
| **Parent** | The Epic key |
| **Reporter** | The user's accountId |
| **Team** | As specified by user (or found from existing tasks) |
| **Components** | Matching Confluence page labels |
| **Labels** | Work-type label + feature code (e.g. `PROJ-1234.5`) + `a/b_test` if applicable + `grooming` if grooming mode (FE/BE/Android/iOS only) |

#### Task title format:

Standard development:
```
[WorkType] FeatureName
```

If Grooming (only for FE/BE/Android/iOS tasks):
```
[WorkType] - Grooming - FeatureName
```

If A/B test:
```
[WorkType] - A/B Test - FeatureName
```

If both Grooming AND A/B test (FE/BE/Android/iOS only):
```
[WorkType] - Grooming - A/B Test - FeatureName
```

Examples:
- `[FE] User Reviews - Product page review section`
- `[BE] - Grooming - User Reviews - Product page review section`
- `[iOS] - A/B Test - Compact product specs block`
- `[Android] - Grooming - A/B Test - Compact product specs block`
- `[Design] User Reviews - Product page review section` *(Design is never affected by Grooming)*

#### Description format (markdown):

```markdown
## Task

{Short summary of what needs to be done for this specific work type}

## Requirements

[{Feature page title}]({Confluence page URL})
```

> **Note:** Use the user's preferred language (`user.language`) for the task description content.

The summary under "Завдання" should be specific to the work type:
- **Design**: focus on UI&UX research, prototyping, Figma mockups
- **BE**: focus on API, business logic, data models, feature flags
- **Analytics**: focus on event tracking, metrics, data coverage (or A/B test analysis for the second analytics task)
- **FE**: focus on frontend implementation, UI components, interactions
- **Android/iOS**: focus on mobile implementation, deeplinks, native UI

#### Work-type specific fields:

| Work Type | Issue Type | Labels | +Grooming label |
|---|---|---|---|
| **FE** | Task | `frontend` | + `grooming` if grooming mode |
| **BE** | Task | `backend` | + `grooming` if grooming mode |
| **Android** | Task | `Android`, `app` | + `grooming` if grooming mode |
| **iOS** | Task | `iOS`, `app` | + `grooming` if grooming mode |
| **Design** | Design (if available) or Task | `design` | not affected |
| **Analytics** | Analytics (if available) or Task | `Analytics` | not affected |

#### Analytics special case — A/B Test:

If the feature is an A/B test, create **2** Analytics tasks:
1. `[Analytics] {FeatureName} - Analytics coverage` — for defining analytics requirements
2. `[Analytics] {FeatureName} - Test results analysis` — for analyzing test results after completion

> **Note:** Use the user's preferred language (`user.language`) for analytics task titles if required by your team's conventions.

### Step 8: Set Additional Fields via Edit

Some fields may not be settable during creation. After creating each task, use `editJiraIssue` to set:
- **Team** (custom field) — if it didn't work during creation
- **Issue Type** change — if Design/Analytics types need to be changed from Task

### Step 9: Ask About Linking

After all tasks are created, ask the user if they want to link tasks by the standard dependency logic.

### Step 10: Link Tasks (if confirmed)

Use the "Blocks" link type with this dependency chain:

1. **Design** is the first task — blocks everything else
2. **BE** and **Analytics (coverage)** — come after Design, block FE/Android/iOS
3. **FE**, **Android**, **iOS** — come after Design, BE, and Analytics (coverage)
4. **Analytics (analysis)** — comes after ALL other tasks (only for A/B tests)

Specific links to create:
- Design **blocks** → BE
- Design **blocks** → Analytics (coverage)
- BE **blocks** → FE
- BE **blocks** → Android
- BE **blocks** → iOS
- Analytics (coverage) **blocks** → FE
- Analytics (coverage) **blocks** → Android
- Analytics (coverage) **blocks** → iOS
- FE **blocks** → Analytics (analysis) *(A/B test only)*
- Android **blocks** → Analytics (analysis) *(A/B test only)*
- iOS **blocks** → Analytics (analysis) *(A/B test only)*

If a work type wasn't selected, skip its links.

### Step 11: Report Results

After creating all tasks and links, provide a summary table:

| # | Key | Title | Issue Type | Labels | Components |
|---|---|---|---|---|---|
| 1 | PROJ-XXX | [Type] Feature name | Type | labels | components |

Include:
- Common fields applied to all (Parent, Team, Reporter)
- List of created links
- Dependency chain visualization
- Any issues encountered (fields that couldn't be set, etc.)
- A JQL link to view all created tasks: `parent={EpicKey} AND labels={FeatureCode} ORDER BY created DESC`

### Step 12: Post-creation verification

**After creating all tasks, automatically verify one task** to ensure it matches the requirements, rules, and field conventions. This is a mandatory quality gate.

**12a. Select a task for verification:**

Pick one of the created tasks (preferably a development task — FE or BE — as they have the most complex field set).

**12b. Read the task back from Jira:**

Use `getJiraIssue` to fetch the created task with all fields. This ensures we verify what was actually saved, not what we intended to send.

**12c. Run verification checks:**

| Check | What to verify | How to verify |
|-------|---------------|--------------|
| **Title format** | Matches the pattern: `[WorkType] - Grooming/A/B Test - FeatureName` | Compare with the expected title from Step 7 rules |
| **Parent** | Linked to the correct Epic | Check `parent` field matches the Epic key |
| **Reporter** | Set to the user's accountId | Compare with `user.jira_account_id` |
| **Team** | Set to the correct team | Compare with the confirmed team value from Step 6b |
| **Labels** | Contains all required labels: feature code, work type label, `a/b_test` if applicable, `grooming` if applicable | Check labels array against expected values |
| **Components** | Matches the confirmed components | Compare with the confirmed values from Step 6b |
| **Description** | Contains "Task" section and "Requirements" section with Confluence link | Parse description content |
| **Issue Type** | Correct type (Task/Design/Analytics) | Check issue type field |
| **Links** | Correct dependency links created (if linking was confirmed) | Check issue links via `getJiraIssue` |

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

### Step 13: Feedback and self-improvement

After presenting the results, proactively ask:

> "Was everything created correctly? Is there anything to fix, add, or change?"

- If the user requests changes — fix the tasks (edit, re-create, re-link as needed), present updated report
- If the user confirms — proceed

**Self-improvement check** (after corrections are applied and confirmed):

If the user requested corrections during review, analyze whether the skill's algorithm can be improved to prevent similar issues in the future. Follow the full protocol in `references/self-improvement.md`. In short:
1. Analyze the root cause of the error — is this a pattern or a one-off?
2. If it's a pattern — propose a specific improvement to the skill's conditions
3. If the user agrees — update the SKILL.md, re-package the plugin, and provide the updated file

## Dry Run Mode

If the user asks for a "dry run" / "test mode" / "simulation", go through the entire workflow but:
- Don't actually create tasks in Jira
- Show what WOULD be created with all field values
- Wait for user confirmation before executing for real

## Connection with Other Skills

This skill can work together with **Write Concept / PRD** — if a PRD was just published to Confluence, the user can immediately trigger this skill to break it down into implementation tasks.

## Important Notes

- Always confirm the Confluence page content with the user before creating tasks
- If you can't access Confluence page labels directly, infer Components from existing tasks in the same Epic
- The Team field format varies by Jira instance — check an existing task to find the correct format
- Feature code goes into Labels, not into the task title prefix
- Use `contentFormat: "markdown"` when creating tasks with description

## Additional Resources

- **`references/local-context-protocol.md`** — Step 0: how to read and use local-context.md (mandatory before any skill execution)
- **`references/integration-strategy.md`** — MCP → Registry → Browser fallback chain (shared across all skills)
- **`references/data-policy.md`** — data confidentiality policy
- **`references/self-improvement.md`** — self-improvement protocol: how to learn from user corrections and improve skill algorithms
