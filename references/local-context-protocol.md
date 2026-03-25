# Local Context Protocol

This document defines how every skill in the plugin reads and uses `local-context.md`. **All skills MUST follow this protocol at the start of execution.**

## Step 0 — Check and read local-context.md (MANDATORY)

Before any other action, the skill MUST:

### 0a. Search for local-context.md

Search in the following locations (in order):
1. Plugin root directory (relative: `../../local-context.md` from skill folder)
2. User's workspace/outputs folder (the mounted folder or outputs directory)
3. Session working directory

### 0b. If NOT found → redirect to Plugin Configurator

Stop the current skill workflow and inform the user:

> "Для ефективної роботи плагіну потрібно налаштувати контекст вашої організації, продуктів та інструментів. Давайте пройдемо швидке налаштування (~5-10 хв)."

Launch the **Plugin Configurator** skill in **Onboarding** mode. After Onboarding completes — return to the original skill and continue its workflow with the newly created context.

### 0c. If found → read and parse

Read `local-context.md` and extract:
- Active user profile (name, role, email, language, jira_account_id)
- List of organizations and their products
- Integration details for the current context

### 0d. Select active product

If the file contains **multiple products**:
1. If the user explicitly mentioned a product name in their request → use it
2. If only one product exists → use it automatically
3. If multiple products exist and none was mentioned → ask via AskUserQuestion:
   > "У контексті є декілька продуктів: [list names]. Для якого продукту працюємо зараз?"

The selected product becomes the **active product** for the current skill session. All product-specific fields (platforms, locales, jira_project_key, Confluence space, dashboards, competitors, etc.) are read from the active product's section.

### 0e. Check for missing required fields

Each skill has specific required fields (see `references/context-schema.md` → "Which Skills Read What"). If required fields are missing for the current skill:
- Inform the user which fields are missing
- Offer two options:
  1. Run **Plugin Configurator** in Update mode to add missing data
  2. Proceed without the missing context (skill will ask for this info manually during execution)

## Context Enrichment

During execution, skills may discover new information that should be saved to `local-context.md`. When this happens:

1. Inform the user: "Я знайшов нову інформацію: [description]. Бажаєте зберегти у контекст плагіна?"
2. If the user agrees:
   - Read the current `local-context.md`
   - Add the new information to the appropriate section
   - Update the "Updated:" timestamp
   - Save the file

Examples of discoverable context:
- **Product Research** → new competitors found during research
- **Product Analysis** → current metric values from dashboards
- **Feature Task Creator** → Jira team IDs, member accountIds discovered from existing tasks
- **Requirements Creator** → Confluence template URL discovered during publishing

## Using context in skills

Once the context is loaded and active product selected, skills should:

- Use `product.name` when asking about product context (skip the "which product?" question)
- Use `product.platforms` when presenting platform options (pre-fill the list)
- Use `product.locales` as defaults for locale questions
- Use `product.jira_project_key` for Jira queries
- Use `product.confluence_space` as default publishing destination
- Use `product.competitors` when building comparison matrices (always include user's product)
- Use `product.key_metrics` when discussing metrics (pre-fill known metrics)
- Use `product.current_okrs` to align hypotheses and analysis with strategic goals
- Use `organization.tableau_base_url` and `product.ab_test_dashboards` for analytics access
- Use `user.language` for output language preference
- Use `user.jira_account_id` for setting Reporter on Jira tasks
- Use `team.jira_team_id` for setting Team field on Jira tasks
