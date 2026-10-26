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
- **People data (highest-sensitivity tier)** — performance assessments, 1-1 notes, person profiles (situational-leadership type, GTD-index, career/motivation signals), offboarding cases, and any manager evaluation of a specific team member. See the dedicated tier rules below.

---

## People data — highest-sensitivity tier

The People-contour skills (`goal-setter`, `one-on-one`, `performance-review`, `hiring-designer`, `offboarding-guide`, `delegation-coach`) and the person profiles they maintain (`references/people-context-protocol.md`) handle the **most sensitive** data in the plugin. Beyond the general restrictions below, these hard rules apply:

1. **Local / vault only.** Person profiles, 1-1 notes, performance reviews, and offboarding materials are stored **only** in the vault (`People/…`) or `~/.grow-pm/people/…`. They are **never** published to Confluence, Jira, or any shared workspace.
2. **Never to external LLMs / third parties.** Do not send a person's name-linked performance data, review, 1-1 content, or offboarding case to any external LLM (ChatGPT/Gemini/etc.) or third-party service — not for "deep research", not for phrasing help. Draft such text with the in-session model only.
3. **Minimal in chat.** Surface only the minimum necessary in the chat transcript; prefer references to the stored artifact over pasting full evaluations.
4. **Factual, not characterizing.** Record working performance in factual, NVC terms (`references/communication-frameworks.md`), not personal judgments — the record describes the work, not the person's worth.
5. **Offboarding especially.** Termination/PIP materials are strictly local, gated before every write, and never leave the machine.

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

## Search (Step 0.5, since v3.16.0)

Step 0.5 of every skill searches the user's own base and, when it is not enough, the live sources of the session (`references/search-protocol.md`). Three rules keep it inside this policy:

1. **Sensitive notes stay with the People contour.** A note marked `sensitive: true`, a note of a people type (`people`, `person`, `one-on-one-notes`, `one-on-one`, `performance-review`, `offboarding-plan`, `delegation-audit`, `followup-arcv`), a 1-1 note — its title or a folder of its path names a 1-1 (`1-1 …`, `1:1 …`, `1on1 …`, `1-1-Logs/`, one-on-one), whatever its type — and, since v3.17.0, a note that carries a person profile's judgement field (`d_type`, `d_history`, `recommended_style`, `signals`, `one_on_one`, `gtd_index`, `forecast_qa`, `delegation`, `active_goal_letter`) — whatever its type and whatever `sensitive` says — are taken into a skill's work only by the People-contour skills. The search marks all of these `sensitive` itself — a judgement field one map down too (`reporting: forecast_qa`) — so a skill reads the mark, not the type. The one exception is a person's identity — name, e-mail, team and role as a registry card's frontmatter states them, and the card's path — which `context-navigator` may name to answer who someone is (`search-protocol.md` §13) and, since v3.19.0, any skill may use as `ctx entity` and `ctx read`'s `team.members` give it (`people-context-protocol.md` → Find a person, `context-protocol.md` §5h) — never the card's body or a judgement field; a sensitive team's, mission's, module's or metric's card gives its members' names and its path only, never its text; a server's note it has not read yet carries the mark only by the type the server gives (`search-protocol.md` §6 says what to do until then). Beyond that identity, any other skill never takes one, never reads its section, and never repeats its content (a cross-contour reader of `people-context-protocol.md` takes its listed profile fields, read-mostly) — in its block of variants it may name such a note by its title only. `ctx entity` (since v3.18.0) follows the same rule: a card's identity alone (name, e-mail, team, role, path — never a judgement field, which its registry does not even hold), and a sensitive note that links to the entity or carries its key as its title, path and day with ` · sensitive` — the field it links from only for a People-contour `--skill`, its text never.
2. **Live sources are read in the session, with a question where the data is sensitive.** Level 2 reads Confluence, Jira, meeting transcripts, Drive or mail only through the user's own connectors, and asks the user first before it reads person profiles, private channels or mail. What it reads stays in the session, like any data under this policy.
3. **Nothing from a live source is indexed or stored.** The search's own index (`~/.grow-pm/index/`, outside every vault) holds only the user's vault folders and the cores registered on this machine; what level 2 finds goes into no index, no record and no store, and the user's choices keep the request and the paths chosen, never a note's content. A remote repository's server is asked only for a repository whose folder is not on disk, and only with the words of the request.

## Bridges in your notes (since v3.20.0)

`ctx entity apply` writes one frontmatter line into a note of the user's own plugin folder — a link to another card of the same entity and that card's title, identity alone, never a field, a value or a line of a profile — only after the user's «так» to the report, never into a core's folder; `ctx undo` takes it back (`references/context-protocol.md` §5h).

---

## Reference

This policy applies in addition to (not instead of) the integration strategy described in `integration-strategy.md`. Both documents must be read and followed before any skill begins data gathering.
