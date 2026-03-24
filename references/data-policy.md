# Data Confidentiality Policy

This policy applies to ALL skills in the Grow Product Manager plugin without exception.

---

## Protected Data Categories

The following data types are considered confidential and are subject to this policy:

- Data obtained from **Tableau** and other analytics platforms (dashboards, reports, metrics, funnels, cohorts)
- **Business analytics** and internal KPI data
- **Research materials** containing internal findings, user interviews, survey results
- **Strategy documents**, roadmaps, OKRs, and business plans
- Any data that constitutes a **trade secret** or is marked as confidential/secret within the organization
- **User data** and personally identifiable information (PII)

---

## Restrictions

### Prohibition on LLM training use

Confidential data obtained during a session **must NOT** be submitted to any external LLM (ChatGPT, Gemini, or other) as training data or in a way that could result in it being stored or used to train models.

**Allowed**: Using external LLMs (ChatGPT, Gemini) for general research, market analysis, and publicly available information via Deep Research mode.

**Not allowed**: Pasting internal metrics, analytics reports, research findings, or any confidential data into external LLM interfaces.

### Prohibition on third-party sharing

Confidential data **must NOT** be transmitted to third parties in any form — including via integrations, API calls to external services, or browser interactions with external platforms.

### Scope of use

Confidential data may be used **exclusively**:
- By the current user within their own account
- For the tasks set by that user within the current session
- For generating documents that remain within the organization's internal tools (Confluence, Jira, internal systems)

---

## Practical Guidelines for Skills

When working with potentially confidential data, every skill must follow these rules:

1. **Tableau and analytics data** — use only within the session for analysis and document generation. Do not pass raw metrics or dashboard data to external LLMs or services.

2. **Deep Research via ChatGPT / Gemini** — formulate prompts using only **publicly available** information (product names, market trends, general feature descriptions). Never include internal metrics, research findings, or confidential business data in prompts sent to external LLMs.

3. **Confluence and Jira data** — internal documents read from Confluence or Jira remain internal. Do not export or transmit this data to external services beyond what is needed to complete the current task.

4. **Uploaded files** — treat all user-uploaded files as potentially confidential. Do not forward their content to external services without explicit user confirmation.

5. **When in doubt** — treat the data as confidential. Ask the user if you are unsure whether specific data can be shared externally.

---

## Reference

This policy applies in addition to (not instead of) the integration strategy described in `integration-strategy.md`. Both documents must be read and followed before any skill begins data gathering.
