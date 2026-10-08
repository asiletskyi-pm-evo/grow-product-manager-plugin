<!-- {{NAMESPACE}}:begin id=team v={{BLOCK_VERSION}} -->
### Team: {{TEAM_CANONICAL}}

- **Team card (source of truth):** `{{TEAM_CARD_PATH}}` — aliases, responsibility, modules, missions
- **Directory node:** `{{NODE}}`{{HEAD_SUFFIX}}
- **Jira:** {{JIRA}}
- **jira_project_key:** {{JIRA_KEY}}{{JIRA_OTHER}}
- **jira_team_field:** {{JIRA_TEAM_FIELD}}
- **jira_write_scope:** {{JIRA_WRITE_SCOPE}}
- **Team missions:** {{MISSIONS}}
- **Modules (owner and co-owner):** {{MODULES}}
- **Team metrics:** {{METRICS}}

#### Members (registry `{{PEOPLE_DIR}}/`, field `team`; ◌ — registry stub)

| Name | Role (registry) | Position | Email | Card |
|---|---|---|---|---|
{{MEMBERS_ROWS}}

> Members' Jira accountIds are looked up by e-mail when needed (task creation does it itself).
<!-- {{NAMESPACE}}:end id=team -->
