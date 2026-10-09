---
name: task-creator
version: 0.15.1
description: Create Jira tasks from requirements (usually a Confluence page) — FE/BE/Android/iOS/Design/Analytics breakdown inside an Epic. Not writing the requirements (requirements-creator). UA — «створи задачі для фічі», «розбий вимоги на задачі». EN — "break this spec into Jira tasks".
---

# Task Creator

> **Path rule.** A bare `references/<file>.md` in this file is read from this skill's own `references/` if the file exists there, otherwise from the **shared** `references/` at the plugin root. Resolve the root as `${PLUGIN_ROOT}`, else `${CLAUDE_PLUGIN_ROOT}`, else the directory that contains `skills/`, found by walking up from this folder (`references/host-profiles.md` §6). Never continue without a protocol named here.

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

> **Judgment contract (Step 0j).** Per `references/local-context-protocol.md` Step 0j and `references/pm-mental-model.md`: note this run's
> judgment points (score, rank, verdict, priority, ship/kill, debate question) internally, with no output. A principle acts only through
> a step that implements it — until one exists here, this skill's questions, gates and output stay exactly as they are.

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

**Judgment footer (since v3.5.0).** The artifact closes with the altitude line from `templates/built-in/partial/judgment-footer-v1.md` (`references/template-protocol.md` T-5 step 3a; checked by `references/artifact-style-gate.md` Gate 4a) — on the epic only when this run creates it (T-B; an existing epic is never edited to add it) and on the Step 11 report; never on each task.

## Workflow

### Step 1: Read Requirements from Confluence

When the user provides a Confluence link:

1. Resolve the page — try `getConfluencePage`, or `search` / `searchConfluenceUsingCql` to find it
2. Extract from the page:
   - **Feature name** — from the page title (after the code prefix, e.g. "Feature Name Description" from "PROJ-1234.5 - Feature Name Description")
   - **Feature code** — the code in the page title (e.g. `PROJ-1234.5`). Pattern: `EPICKEY-NUMBER.NUMBER`
   - **Epic link** — usually under an "Epic" heading, a link to the Epic's Confluence page or directly a Jira issue key
   - **Technical requirements** — look for mentions of "A/B Test", "feature flag", platform restrictions
   - **Functional requirements** — what needs to be built
   - **Confluence page URL** — for linking in task descriptions
3. **Spec readiness (since v3.9.0).** For a feature spec, score the six elements of `references/artifact-style-gate.md` → Spec readiness and show one line, `Spec readiness: n/6 — missing: …`, with this extraction (in the message that carries the Step 4 questions — no new turn); the same line is a row of the Step 6b summary and an item of the Step 11 report. It never blocks, is never asked and never edits the spec. A concept or PRD source gets one pointer line to `requirements-creator` instead; action items, rollout or cleanup tasks, hand-offs and feedback quick fixes get nothing.
4. **AI-driven spec (since v3.9.0)** — the page carries the AI-feature sections or says explicitly that the output is produced by an AI or ML model, never on the bare word "model". It sets up the Step 4 eval-set option. Source scope, where each element is found, non-testable AC: `references/spec-readiness.md` (skill-local).

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
   - QA — Eval set *(since v3.9.0; only for an AI-driven spec, Step 1 — offered pre-selected: listed first and marked "(recommended for an AI-driven spec)" in this question, which is a numbered list in chat when its options exceed the host's option picker (2–4 per question, `references/host-profiles.md` §4); the task is created unless the user drops it in the answer; dropped → no eval-set task)*

2. **Task purpose** — are these tasks for development or for grooming?
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
   - Does the project have a "QA" issue type? If yes, use it for QA tasks (since v3.9.0)
   - Otherwise, use "Task" for everything

2. **Team field** — find the custom field ID for Team (usually `customfield_10001`):
   - Use `getJiraIssueTypeMetaWithFields` to find the field
   - Look at an existing task in the Epic to find the Team value/ID format
   - The Team field often requires a string ID (not an object) — a UUID with a numeric suffix, e.g. `"<team-uuid>-NN"`; take the value from local-context (`product.jira_team_id`) or from an existing task in the Epic

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
- **Eval-set task (since v3.9.0)** — never asked: its fields come from the QA row of `references/task-format.md` and the common fields; one that would need a question here drops the task, with one notice line in this summary and in Step 11

**Present a pre-creation summary for confirmation:**

> "Here are the field values I'll use for all tasks:"

| Field | Value | Source |
|-------|-------|--------|
| Parent (Epic) | PROJ-1234 | From Confluence page |
| Reporter | User Name | From local-context.md |
| Team | Team Name | Inferred from Epic — please confirm |
| Components | component-1, component-2 | From existing Epic tasks — please confirm |
| Labels (common) | PROJ-1234.5 | From feature code |
| Spec readiness | 5/6 — missing: out of scope | Requirements page (Step 1) — shown, not asked |
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

`[WorkType] FeatureName`, or `[WorkType] - Grooming - A/B Test - FeatureName` keeping only the qualifiers that apply (Grooming only for FE/BE/Android/iOS; Design and Analytics are never affected by it).

The full format — every title variant with worked examples, the work-type fields table (issue type + labels per work type) and the A/B-test Analytics pair — lives in `references/task-format.md` (skill-local). Read it before drafting task titles and labels in Step 7, every run.

#### Description format (markdown):

Apply the **task-formulation quality gate** (`references/communication-frameworks.md` → task formulation). Every task body carries **why + what + how**, and — for critical tasks — a Definition of Done:

```markdown
## Why

{The meaning/motivation — why this task matters and how it ladders to the feature's goal. A missing "why" produces formal execution and demotivation.}

## What

{The result, as clear and short as possible — specific to this work type. If it's already in the title, don't duplicate.}

## How

{Depth adapts to the assignee's level — see the note below. For a senior (D4): only non-obvious points + audit checkpoints. For a junior (D1): a step-by-step checklist "how I'd do it".}

## Definition of Done
{Acceptance criteria — for critical / important tasks. Omit for routine ones. Since v3.9.0 each spec AC the task must pass is cited by id (`AC-N`, or `AC 3` by position when unnumbered) — ids only, never the AC text.}

## Requirements

[{Feature page title}]({Confluence page URL})
```

> **"How" is built ONLY from the requirements and confirmed context** (`references/artifact-style-gate.md`, Gate 1). Do not invent engineering steps that are not in the requirements: no technology choices, no API/schema design, no architecture decisions. For a D1 checklist, keep the steps process-level ("read the spec section X", "sync the contract with BE", "cover states A/B/C"), not invented implementation detail. If the user explicitly asked for technical recommendations — put them in a separate "Технічні рекомендації (AI)" section at the end of the description, opened with the mandatory AI callout (never inside "How").

> **"How"-depth by D-level (people-profile aware).** If the assignee has a person profile (`references/people-context-protocol.md`, `d_type`), tune the "How" depth to it: **D4 → minimal "how"** (or a goal instead of a task); **D1 → detailed checklist**. If no profile exists, default to a moderate checklist and note the assumption. This uses the profile **read-only** — task-creator never creates profiles.

> **Title:** perfective, result-oriented verb, full essence in the title (`references/communication-frameworks.md`). "You don't pay per character."

> **Deliberately NOT enforced: a single responsible per task.** The classic task-formulation rule of "one responsible" is intentionally **omitted** here — it conflicts with the team's process (a task may legitimately carry FE/BE/QA roles). Do not add or warn about multiple owners.

> **Note:** Use the user's preferred language (`user.language`) for the task description content.

The summary under "What" should be specific to the work type:
- **Design**: focus on UI&UX research, prototyping, Figma mockups
- **BE**: focus on API, business logic, data models, feature flags
- **Analytics**: focus on event tracking, metrics, data coverage (or A/B test analysis for the second analytics task)
- **FE**: focus on frontend implementation, UI components, interactions
- **Android/iOS**: focus on mobile implementation, deeplinks, native UI

#### Style preamble

Before drafting descriptions, load the team style preamble (`references/artifact-style-gate.md` Gate 3a) — task text follows the team's language; skip silently if no profile is configured.

#### Batch quality gate before creation

After drafting all task descriptions and BEFORE creating issues in Jira, run `references/artifact-style-gate.md` over the batch (maker–checker; tasks are a critical artifact → two lenses: form / groundedness). The checker is the `grow-product-manager:artifact-checker` agent (one call per lens); it receives the drafted descriptions with `artifact_type: task batch` (Gate 4a and 4b report `n/a`: a task body gets no altitude line and no evidence label — requirement text copied into it keeps any label it carries, verbatim) + the requirements page content + the lens. Typical catches: engineering steps in "How" that are absent from the requirements (Gate 1), "What"/"How" written as paragraph prose instead of lists (Gate 2). Apply fixes, surface disputed findings, include the one-line gate report in the pre-creation summary.

#### Work-type specific fields:

Issue Type and work-type labels per work type (+ `grooming` for FE/BE/Android/iOS in grooming mode) — the table is in `references/task-format.md` (skill-local).

#### Analytics special case — A/B Test:

An A/B test gets **2** Analytics tasks (coverage + test results analysis) — titles in `references/task-format.md` (skill-local).

#### QA special case — AI-driven spec (since v3.9.0):

When the QA — Eval set option stays ticked (Step 4), one `[QA] {FeatureName} - Eval set` task cites the spec's eval set, adds a `draft` case for each behaviour-spec rule no case covers, and cites the eval criterion by id in its DoD (`references/pm-mental-model.md` P6) — fields and body in `references/task-format.md` (skill-local).

### Step 8: Set Additional Fields via Edit

Some fields may not be settable during creation. After creating each task, use `editJiraIssue` to set:
- **Team** (custom field) — if it didn't work during creation
- **Issue Type** change — if Design/Analytics types need to be changed from Task

### Step 8.5: Attach Annotated Screenshots

If the source requirements carry annotated screenshots (created by `requirements-creator` Step 4.2), or the user asks to visualize the tasks: attach the relevant `{feature-code}-screen-{N}.png` to the **Design and FE tasks** (the ones with UI changes) via `references/visual-annotation-protocol.md` Step V-6 (REST chain → browser → manual placeholder), and put the legend table into the task description. Markers on the image = functional requirement numbers the task implements. Prefer `steps/NN.png` from a `flow-walkthrough` evidence pack when one exists for the feature's flow (already verified, already local). Skip silently when there are none.

### Step 9: Ask About Linking

After all tasks are created, ask the user if they want to link tasks by the standard dependency logic.

### Step 10: Link Tasks (if confirmed)

Use the "Blocks" link type with this dependency chain:

1. **Design** is the first task — blocks everything else
2. **BE** and **Analytics (coverage)** — come after Design, block FE/Android/iOS
3. **FE**, **Android**, **iOS** — come after Design, BE, and Analytics (coverage)
4. **Analytics (analysis)** — comes after ALL other tasks (only for A/B tests)
5. **QA (eval set)** — comes after BE, FE, Android and iOS (AI-driven spec only)

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
- BE, FE, Android, iOS **block** → QA (eval set) *(AI-driven spec only)*

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
- The Step 1 spec readiness line, or the concept pointer (since v3.9.0); a dropped eval-set task with its reason
- A JQL link to view all created tasks: `parent={EpicKey} AND labels={FeatureCode} ORDER BY created DESC`

### Step 12: Post-creation verification

**After creating all tasks, automatically verify one task** to ensure it matches the requirements, rules, and field conventions. This is a mandatory quality gate.

Pick one created task (preferably FE or BE), read it back from Jira and hand it — with the requirements content and the check table — to the `grow-product-manager:artifact-checker` agent (maker–checker, `references/artifact-style-gate.md`); report discrepancies, apply confirmed fixes to ALL created tasks, re-verify.

The full procedure — task selection (12a), read-back and the maker–checker hand-off with its inline fallback (12b), the verification check table (12c), the result report and fix proposal (12d), cross-task fix propagation (12e) — lives in `references/post-creation-verification.md` (skill-local). Read it after the Jira issues are created, every run.

### Step 13: Feedback and self-improvement

After presenting the results, proactively ask:

> "Was everything created correctly? Is there anything to fix, add, or change?"

- If the user requests changes — fix the tasks (edit, re-create, re-link as needed), present updated report
- If the user confirms — proceed

**Self-improvement check** (after corrections are applied and confirmed): follow `references/self-improvement.md` — analyze whether the correction is a pattern, and if so propose a SKILL.md improvement (version bump + CHANGELOG).

### Step 14 — Save to Vault (Optional)

> Requires: `references/vault-protocol.md` → Vault Save

IF vault_level > L0 AND vault sync_mode != "off":

1. `vault_save({ type: "task-breakdown", product: active_product, skill: "task-creator", skill_version: "0.15.1", tags: [feature area, platforms], content: created task list (keys, titles, work types, assignees) + epic link + requirements source, related: [[requirements artifact]], extra_frontmatter: { epic_key, jira_keys: [...] } })`
2. Display: "Saved to Vault: Projects/task-breakdowns/{product}/…"

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

- **`references/spec-readiness.md`** (skill-local) — Step 1 (since v3.9.0): source scope, where each of the six elements is found, the line, non-testable AC, AI-driven detection
- **`references/task-format.md`** (skill-local) — Step 7 title variants with examples, work-type fields table (QA row since v3.9.0), A/B-test Analytics pair, AI-driven eval-set task
- **`references/post-creation-verification.md`** (skill-local) — Step 12 (12a–12e): read-back, maker–checker check table, fix report, cross-task propagation
- **`references/local-context-protocol.md`** — Step 0: how to read and use local-context.md (mandatory before any skill execution)
- **`references/integration-strategy.md`** — MCP → Registry → Browser fallback chain (shared across all skills)
- **`references/data-policy.md`** — data confidentiality policy
- **`references/communication-frameworks.md`** — task-formulation quality gate (why/what/how + DoD + D-level depth)
- **`references/artifact-style-gate.md`** — artifact quality gate: Gate 1 (ungrounded technical content), Gate 2 (lists over prose), Gate 4 (`n/a` on task bodies), maker–checker execution (batch gate before creation + Step 12), Spec readiness (Step 1)
- **`references/people-context-protocol.md`** — read-only D-type of the assignee to tune "How"-depth
- **`references/self-improvement.md`** — self-improvement protocol: how to learn from user corrections and improve skill algorithms

## Routing

The `description` above is short on purpose: a host with many skills shows only part of the skill listing, or skill names alone (`references/host-profiles.md` §7). The full set of phrases and boundaries that route here, as the description carried them up to v3.10.0:

> Create Jira tasks from requirements (usually a Confluence page) — FE/BE/Android/iOS/Design/Analytics breakdown inside an Epic. Not writing the requirements (requirements-creator). UA — «створи задачі для фічі», «Jira-задачі з вимог у Confluence», «розбий фічу на задачі», «заведи задачі в Epic». EN — "create tasks from requirements", "create Jira issues from Confluence requirements", "break down a feature into development tasks", or a shared Confluence link with a request for Jira tasks.
