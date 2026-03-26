---
name: feature-task-creator
version: 0.4.0
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

### Step 12: Feedback and self-improvement

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
