# Local Context Schema

This document defines the complete structure of `local-context.md` — the organization-specific configuration file that all plugin skills read from.

## Structure Overview

```
local-context.md
├── User Profile
├── Onboarding Status (auto-managed)
├── Organizations (1+)
│   ├── Organization metadata
│   ├── Integrations & Data Sources
│   ├── Products (1+)
│   │   ├── Product metadata
│   │   ├── Platforms
│   │   ├── Locales
│   │   ├── Key Metrics & OKRs
│   │   ├── Analytics Dashboards
│   │   ├── Confluence Configuration
│   │   ├── Jira Configuration
│   │   ├── Competitors
│   │   └── Repositories
│   └── Teams (1+)
│       ├── Team metadata
│       └── Members with roles
└── Custom Sections (0+)
```

## Section Definitions

### User Profile (required)

| Field | Required | Used by | Description |
|-------|----------|---------|-------------|
| name | ✅ | All skills | User's display name |
| role | ✅ | All skills | User's role (e.g., Product Manager, Senior PM) |
| email | ✅ | Task Creator | For Jira account lookup |
| jira_account_id | optional | Task Creator | Jira accountId (auto-discovered if Jira MCP available) |
| language | ✅ | All skills | Preferred language for skill output (uk/en) |

### Onboarding Status (required, auto-managed by Configurator)

| Field | Required | Used by | Description |
|-------|----------|---------|-------------|
| onboarding.mode | ✅ | All skills | `basic` or `extended` (managed by Configurator) |
| onboarding.basic_completed_at | ✅ | Configurator | Timestamp when Basic onboarding finished |
| onboarding.extended_completed_at | optional | Configurator | Timestamp when Extended onboarding finished |
| onboarding.last_test_run_at | optional | Configurator | Timestamp of last Test (sandbox) run |
| onboarding.deferred_steps | optional | All skills | List of step keys deferred during Basic — the enum below |
| onboarding.skip_nudges | optional | All skills | If `true`, suppress upgrade-to-Extended nudges from skills (default `false`) |

Skills check `onboarding.mode` and `onboarding.deferred_steps` to decide whether to nudge the user toward Extended setup before running. The Configurator manages this section automatically — users do not edit it directly.

#### `deferred_steps` enum

Every key an onboarding step may append, and the step that writes it. A skill checking for a key that no step writes gets a silent false negative; a step writing a key not listed here makes the check undecidable. Keep this table and `references/onboarding-steps.md` in sync.

| Key | Written by | Deferred section |
|---|---|---|
| `key-metrics` | Step 8 | Product key metrics |
| `teams` | Step 9 | Teams |
| `repos` | Step 10 | Repositories |
| `cjm` | Step 11 | CJM configuration |
| `knowledge-library` | Step 12 | Knowledge Library |
| `templates` | Step 13 | Template Library |
| `obsidian-vault` | Step 14 | Obsidian Vaults |
| `custom-sections` | Step 15 | Custom sections |
| `tableau-full` | Step 7b | Extended Tableau fields (datasources, Pulse IDs, A/B dashboards) |
| `analytics-extended` | Step 7a | Non-Tableau analytics (Amplitude / Mixpanel / Sheets / custom BI) |
| `tableau-mcp-required` | Step 7b | Fields that need Tableau MCP to be useful — recorded even in Extended |
| `planning` | Planning setup | Planning suite (capacity, sprints, goal map, dev flow) |
| `focus` | Focus setup | Focus (sources, zones, VIP, cadence, scheduled) |
| `design-toolkits` | Design Toolkit setup | External design toolkits |
| `people` | People setup | People-contour (roster, cadences, HR form) |

> `okrs` and `competitors` were listed here until v2.1.0 but no step ever wrote them (both are collected inside Step 6, which has no defer path); `key-metrics`, `analytics-extended`, `tableau-mcp-required`, `planning`, `focus` and `people` were written but unlisted — for five sections the "is it deferred?" check could not be answered.

### Organization (required, 1+)

| Field | Required | Used by | Description |
|-------|----------|---------|-------------|
| name | ✅ | All skills | Organization name |
| domain | optional | Product Research | Company domain (e.g., company.com) |
| jira_instance | optional | Task Creator, Requirements Creator | Jira cloud URL (e.g., company.atlassian.net) |
| confluence_instance | optional | All publishing skills | Confluence cloud URL |
| atlassian_cloud_id | optional | Product Reporter, Planning Suite | Atlassian cloud id — required by the Atlassian MCP's per-key calls. Auto-discoverable via `getAccessibleAtlassianResources`; collect at onboarding when Jira is connected. |

### Integrations & Data Sources (per organization)

| Field | Required | Used by | Description |
|-------|----------|---------|-------------|
| tableau_base_url | optional | Product Analysis | Tableau server URL (e.g., https://tableau.company.dev) |
| tableau_site_name | optional | Product Analysis | Tableau site name (only if non-default site is used) |
| tableau_datasource_urls | optional | Product Analysis | Map of datasource name → URL (used by `query-datasource`) |
| tableau_pulse_metric_ids | optional | Product Analysis | Map of metric name → Pulse metric ID (used by `list-pulse-metrics-*`, `generate-pulse-insight-brief`) |
| ab_test_dashboards | optional | Product Analysis (A/B Test mode) | List of A/B test dashboard URLs with platform labels |
| google_sheets_sources | optional | Product Analysis | Key Google Sheets with metrics |
| figma_workspace | optional | Product Research, Write Concept, Brainstorm | Figma workspace/team URL |
| google_drive_folders | optional | Product Research, Write Concept | Key Google Drive folders with research/docs |
| notion_workspace | optional | All publishing skills | Notion workspace URL |
| other_analytics | optional | Product Analysis | Other analytics tools (Amplitude, Mixpanel, etc.) |

### Product (required, 1+ per organization)

| Field | Required | Used by | Description |
|-------|----------|---------|-------------|
| name | ✅ | All skills | Product name (e.g., "Marketplace App") |
| description | ✅ | Product Research, Write Concept | Brief product description |
| url | optional | Product Research | Product URL |
| platforms | ✅ | Requirements Creator, Task Creator | List: Android, iOS, Web Portal, Web CMS, Admin, etc. |
| locales | optional | Requirements Creator | Countries/locales where product operates |
| jira_project_key | ✅ | Task Creator, Requirements Creator | Jira project key (e.g., PROJ) |
| confluence_space | optional | All publishing skills | Default Confluence space for this product |
| confluence_template_url | optional | Requirements Creator | URL to requirements template in Confluence |
| confluence_template_name | optional | Requirements Creator | Template display name |

#### Key Metrics & OKRs (per product)

| Field | Required | Used by | Description |
|-------|----------|---------|-------------|
| key_metrics | optional | Product Analysis, Brainstorm, Write Concept | List of primary product metrics with descriptions |
| current_okrs | optional | Product Analysis, Write Concept | Current quarter OKRs |
| metric_targets | optional | Product Analysis, Requirements Creator | Target values for key metrics |

#### Analytics Dashboards (per product)

| Field | Required | Used by | Description |
|-------|----------|---------|-------------|
| main_dashboard | optional | Product Analysis | URL to main product metrics dashboard |
| funnel_dashboard | optional | Product Analysis | URL to conversion funnel dashboard |
| ab_test_dashboards | optional | Product Analysis | Override org-level A/B dashboards for this product |
| custom_dashboards | optional | Product Analysis | Other product-specific dashboards |

#### Competitors (per product)

| Field | Required | Used by | Description |
|-------|----------|---------|-------------|
| competitors | optional | Product Research, Brainstorm | List of main competitors with URLs |

#### Repositories (per product)

| Field | Required | Used by | Description |
|-------|----------|---------|-------------|
| repositories | optional | Future skills | List of code repositories (GitHub/GitLab URLs) |
| ci_cd | optional | Future skills | CI/CD pipeline URLs |
| environments | optional | Future skills | Staging/prod environment URLs |

#### Design Toolkits (per product or user-global)

External design solutions that `design-bridge` delegates hi-fi / screen-generation work to. Full semantics: `references/design-toolkit-protocol.md`. The plugin ships no concrete toolkit — every entry is user-declared.

| Field | Required | Used by | Description |
|-------|----------|---------|-------------|
| design_toolkits[].id | ✅ | design-bridge | Stable slug (e.g., `my-design-toolkit`) |
| design_toolkits[].label | optional | design-bridge | Human name shown in prompts |
| design_toolkits[].entry.type | ✅ | design-bridge | `skill` / `mcp_tool` / `command` / `browser` |
| design_toolkits[].entry.ref | ✅ | design-bridge | Invocation reference for the entry type |
| design_toolkits[].capabilities | ✅ | design-bridge | Core-enum (`hi-fi-prototype`, `screen-generation`, `ds-tokens`, `figma-write`, `code-first-research`, `design-review`) + custom tags |
| design_toolkits[].scope | optional | design-bridge | Free applicability tags (e.g., `[mobile, b2c]`) |
| design_toolkits[].input_contract | optional | design-bridge | `feature_name` / `platform` / `requirements_doc` / `jira_key` |
| design_toolkits[].returns | optional | design-bridge | `figma_url` / `branch` / `files` |
| design_toolkits[].setup_hint | optional | design-bridge | How to (re)configure the toolkit |
| design_toolkits[].data_locality | optional | design-bridge | `local` / `external` (default `external`) — for data-policy |
| design_toolkits[].contract_version | optional | design-bridge | Protocol semver the toolkit targets |

### Team (optional, per organization)

| Field | Required | Used by | Description |
|-------|----------|---------|-------------|
| name | ✅ | Task Creator | Team name |
| jira_team_id | optional | Task Creator | Team ID in Jira custom field |
| members | optional | Task Creator | List of members with name, role, jira_account_id |

### Custom Sections

Users can add any additional sections with free-form markdown content. The configurator preserves these during updates.

## Which Skills Read What

| Skill | Required context | Optional context |
|-------|-----------------|-----------------|
| **Product Analysis** | product.name | tableau URLs, ab_test_dashboards, key_metrics, OKRs |
| **Requirements Creator** | product.name, jira_project_key, platforms | confluence_template_url, locales, key_metrics |
| **Task Creator** | product.name, jira_project_key | team, members with jira_account_id, confluence_space |
| **Product Research** | product.name | competitors, domain, product.url |
| **Write Concept** | product.name | confluence_space, key_metrics, OKRs |
| **Brainstorm Features** | product.name | key_metrics, competitors, OKRs |
| **Plugin Configurator** | — | reads/writes everything |
| **Focus Advisor** | product.name, planning (sprint anchor/cadence) | focus section (sources, VIP senders, PM goals, cadence overrides, scheduled) |
| **Design Bridge** | product.name | design_system_spec, pptx_theme, brand.*, **design_toolkits[]** (external hi-fi delegation) |
| **Product Reporter** | product.name, jira_project_key | team, custom-field map; for goal-report: people.* (goal + cadence) |
| **Goal Setter** | — | people.* (roster, cadences), product.current_okrs, planning goal map |
| **One-on-One** | — | people.* (roster, 1-1 cadence), Fireflies/Calendar |
| **Performance Review** | — | people.* (roster, review template), product-reporter data |
| **Hiring Designer** | — | people.hr_form (employer vacancy-form fields), team |
| **Offboarding Guide** | — | people.* (roster), goals/reports evidence |
| **Delegation Coach** | — | people.* (roster, d_type, gtd, delegation), calendar/Jira |
| **Sprint Planning** | product.name, planning | people.* (d_type/delegation for assignee fit; writes gtd_index) |
| **CJM Research** | product.name, cjm (stages + thresholds) | data_sources_catalog, knowledge_library.*, ab_test_dashboards |
| **Meeting Processor** | — | product.name, confluence_space, Fireflies/Calendar connectors |
| **Knowledge Library** | — | knowledge_library.* (path, default_search_modes, confluence_spaces, gdrive_folders) |
| **Diagram Prototyper** | — | product.name, figma_workspace |
| **Experiment Tracker** | — | experiments.stale.* (threshold overrides), product.name |
| **Decision Log** | — | product.name |
| **Feedback Triage** | — | feedback.* (sources, segments, default_period) |
| **Roadmap Architect** | product.name | planning (goal map), product.current_okrs |
| **Project Planning** | product.name, planning | jira_project_key, team |
| **Quarterly Planning** | product.name, planning | product.current_okrs, team |
| **Template Library** | — | templates.* (preference, default_language, favorite_templates, storage_root) |
| **Release Manager** | — | plugin_release.* (repo path, remotes, protected branches) |

> Every skill sent to Step 0e must have a row here — the step tells a skill to check "its required fields" against this table, so a missing row silently means "nothing required". 12 skills had no row until v2.1.1.

## Validation Rules

### Required fields (Onboarding must collect these)
1. User profile: name, role, email, language
2. At least 1 organization with name
3. At least 1 product with: name, description, platforms, jira_project_key
4. Onboarding Status: `mode` (basic/extended) and `basic_completed_at` (auto-set by Configurator)

### Optional but recommended
1. Confluence space (for publishing)
2. At least 1 competitor per product (for research)
3. Key metrics list (for analysis and concept work)
4. Team info (for task creation)

### Validate mode checks
1. All required fields are populated
2. MCP connectors are available (Jira, Confluence, Figma)
3. Test queries succeed (Jira project exists, Confluence space accessible)
4. Dashboard URLs are reachable (if configured)
5. Completeness score: X/Y fields populated

## local-context.md Section Formats

The blocks below are the exact `local-context.md` output formats the Plugin Configurator writes when generating the file (Onboarding Step 16). They are referenced from `skills/plugin-configurator/SKILL.md`. Moved here verbatim from the skill in v1.25 (pass 2 refactor).

### CJM Configuration section format

```markdown
### CJM Configuration

#### Funnel Template
- Template: [e-commerce / saas / marketplace / custom]
- Custom template name: [if custom, user-provided name]

#### Funnel Stages
| Stage | Name | Dashboard URL | Baseline Conversion |
|-------|------|---------------|-------------------|
| 1 | [name] | [URL] | [%] |
| 2 | [name] | [URL] | [%] |
| ... | ... | ... | ... |

#### Anomaly Thresholds
- Warning: [X]% deviation from baseline
- Critical: [Y]% deviation from baseline

#### Default Analysis Settings
- Comparison baseline: [previous period / previous year / target]
- Default platforms: [all / specific list]
- Default search modes: [library, internet, confluence, gdrive]

#### Health-Check Notifications
- Channels: [slack / email / local / confluence]
- Frequency: [weekly / custom]
```

### Knowledge Library Configuration section format

```markdown
### Knowledge Library

#### Settings
- Library path: [~/.grow-pm/knowledge-library/]
- Default search modes: [library, internet]
- Trust re-evaluation schedule: monthly
- Minimum trust threshold: 0.5

#### Baymard Premium
- Access: [yes/no]
- URL: [if yes]

#### Configured Confluence Spaces (for CJM search)
- [Space key]: [description]

#### Configured Google Drive Folders (for CJM search)
- [Folder ID]: [description]
```

### Templates section format

Written by Step 13 (O-T.7); read by `template-library` and by every skill's Step T. Full semantics: root `references/template-protocol.md`.

**This block is the canonical key set.** `template-protocol.md`, `onboarding-steps.md` and `local-context.example.md` cite it; they must not define a competing one. (Until v2.1.1 there were two: the write side used `default_language`/`favorite_templates`/`auto_save_to_vault`, this schema used `storage_root`/`setup_completed`, and each side was missing the other's keys — so half the config was read but undefined and the other half defined but unwritten.)

```yaml
templates:
  preference: smart                  # auto | always_ask | smart — T-3 decision mode (default: smart)
  default_language: uk               # default render language when the request names none
  favorite_templates: []             # template_id values that rise to the top of T-2 ranking
  storage_root: "~/.grow-pm"         # or {vault}/{plugin_folder} — resolved per persistent-storage.md
  setup_completed: true              # read by Step 16g's final invitation
```

Derived, not configured: the registry always lives at `{storage_root}/Templates/_registry.json` — do not store the path.

> Removed in v2.1.1: `auto_save_to_vault`. It was written by onboarding and read by nothing — vault saving is governed by `vault.sync_mode`, and a second switch that silently did not work is worse than no switch.

### Planning section format

Written by the Planning setup step; read by the planning suite (`quarterly-planning`, `project-planning`, `sprint-planning`, `roadmap-architect`) and by `focus-advisor` (sprint anchor/cadence). Full field semantics: `references/capacity-model.md`, `references/planning-core.md`; a filled example: `local-context.example.md` → Planning.

```yaml
planning:
  jira_board_id: [board id for sprints/velocity]
  sprint:
    cadence_weeks: [2]
    anchor: { name: "[Sprint N]", start: "[YYYY-MM-DD]" }
  capacity:
    baseline_sp_per_sprint: [10]      # per engineer
    availability_default: [0.9]
    techdebt_reserve: [0.15]
    gate_target: [0.85]
    team:
      [Platform]: { members: [...], note: "[who is not counted and why]" }
  goal_map:                           # epic → Goal (Atlas Goals not queryable via MCP)
    [GOAL-KEY]: [epic ids]
  estimate_tshirt: { S: 3, M: 5, L: 8, XL: 13 }
  development_flow:
    work_types: [...]
    sequence: { [type]: [prerequisites] }
    parallel: [[...]]
    ready_threshold: [...]
    platform_notes: ""
    exceptions: ""
```

> Both sections are written by onboarding and read by skills, but were defined in no schema until v2.1.0 — `context-schema.md` calls itself "the complete schema definition", and Planning's format was delegated to the example file, which is illustrative, not normative.

### Focus Configuration section format

Written by the Focus setup step; read by `focus-advisor`. Full field semantics: `references/focus-signals.md` §8.

```markdown
### Focus (focus-advisor)

#### Sources
- Mail: [on/off], window: [7] days, thresholds: [24]h VIP / [48]h others
- Calendar: [on/off]; prep keywords: [demo, review, планування, ...]
- Jira: [on/off]; Release flags: [off]

#### Zones
- [the PM's areas of responsibility — read by strategy collectors for white spaces, NPS themes, knowledge scoping]

#### VIP senders
- [Name <email>] — [role]

#### PM goals (scoring weights)
- [goal / mission commitment — permanent weight in focus scoring]

#### Goals source
- [URL — pinned product goals/missions source for strategy collectors]

#### Cadence Overrides
| Cycle position | Ritual | Chain |
|---|---|---|
| [day/week] | [ritual or "off"] | [skill + mode] |

#### Scheduled
- Daily brief: [on/off], [cron], mode now, headless
- Tactical brief: [on/off], [cron], mode tactics, headless
- Strategy memo: [on/off], quarterly, mode strategy, headless
- Metrics health-check in scheduled runs: [off]
```

> Subsection order and placement here must match `references/focus-signals.md` §8 — this is the write side of that contract, focus-advisor is the read side. `Metrics health-check` belongs under **Scheduled** (the skill reads `Focus → Scheduled → healthcheck`); it sat under Sources until v2.1.0, so the lookup found nothing in a schema-conformant file. `Goals source` precedes `Cadence Overrides` in both files.

### Obsidian Vaults Configuration section format

```markdown
### Obsidian Vaults (Optional)

#### Status
- Connected: [yes/no]
- Total vaults: [N]

#### Vaults
| # | Vault Path | Folder Name | Products | Sync Mode | Last Artifact |
|---|------------|------------|----------|-----------|--------------|
| 1 | [path] | [folder] | [all/specific] | [auto/manual/read-only/off] | [date or never] |
| 2 | [path] | [folder] | [all/specific] | [auto/manual/read-only/off] | [date or never] |

#### Vault Initialization
- Status: [initialized / pending / error]
- Templates created: [N]
- MOC created: [yes/no]
- Knowledge library migrated: [yes/no]
- Schema version: [X.Y.Z]
```

### Design Toolkits section format

Read by `design-bridge` (Step 0.5). Generic — no concrete toolkit is shipped; the user declares their own. Full semantics: `references/design-toolkit-protocol.md`.

```yaml
design_toolkits:
  - id: <slug>
    label: <human name>
    entry:
      type: skill | mcp_tool | command | browser
      ref: <invocation reference>
    capabilities: [hi-fi-prototype, screen-generation, ds-tokens, figma-write, code-first-research, design-review]
    scope: [<free tags>]
    input_contract:
      feature_name: required
      platform: [<options>]
      requirements_doc: optional
      jira_key: optional
    returns: [figma_url, branch, files]
    setup_hint: <ref>
    data_locality: local | external
    contract_version: <semver>
```

### People Configuration section format

Read by the People-contour skills (`goal-setter`, `one-on-one`, `performance-review`, `hiring-designer`, `offboarding-guide`, `delegation-coach`) and, read-mostly, by `product-reporter` (goal-report), `sprint-planning`, and `focus-advisor`. Written by `plugin-configurator` → People setup. Full semantics: `references/people-context-protocol.md`.

> **Highest-sensitivity data.** Person profiles live in the vault `People/` area or `~/.grow-pm/people/` — never Confluence/Jira/external LLMs (`references/data-policy.md`).

```yaml
people:
  vault_area: "People"            # vault area for profiles; else ~/.grow-pm/people/
  roster_index: "People/_roster.md"
  cadence:
    one_on_one: monthly           # weekly | biweekly | monthly | quarterly (default rule per person tenure)
    goal_report: weekly           # weekly | biweekly | monthly — enum per people-context-protocol.md
  review_template_id: performance-review-builtin-default   # or the employer's registered template_id
  hr_form:                        # employer vacancy-form field map for hiring-designer (employer-specific)
    budget: [<controlled values>]
    team: [<controlled values>]
    position: [<controlled values>]
    employment_type: [<controlled values>]
    probation_length: [<controlled values>]
    # …any other employer form selects; hiring-designer maps the universal vacancy profile onto these
```

Person profiles themselves are **not** stored in `local-context.md` — only this pointer/config block is. Profiles are separate files per `people-context-protocol.md`.

---

## Sections added in v2.1.1

Each of these was **read by a skill but defined in no schema and no example** — the
same defect class v2.1.0 closed for Planning and Focus. A skill that reads an
undefined key has no way for the user to set it: the feature is dead on arrival
and the "override" it advertises never happens.

### Experiments section format

Optional. Written by the user (or `plugin-configurator` → Update); read by `experiment-tracker` to override its built-in stale thresholds. Absent → the defaults below apply silently.

```yaml
experiments:
  stale:
    readout_pending_days: 3        # awaiting-readout older than this → "📊 readout pending"
    idle_high_ice_days: 30         # proposed with ICE >= idle_high_ice_min, older than this → "💤 idle"
    idle_high_ice_min: 8           # the ICE score that makes an idle hypothesis worth surfacing
  registry_path: "{storage_root}/experiments/registry.yaml"   # derived; override only for a custom layout
```

### Feedback section format

Optional. Read by `feedback-triage` (Step 1 Intake) to prefill sources and scope. Absent → the skill collects ad-hoc and offers to save the answers via Enrichment.

```yaml
feedback:
  sources:                          # where the raw feedback normally comes from
    - { type: gdrive, ref: "[folder id or URL]", label: "support exports" }
    - { type: confluence, ref: "[space or page id]", label: "NPS verbatims" }
    - { type: jira, ref: "[JQL for complaint-labelled issues]", label: "complaints" }
  segments: [<segment>, <segment>]  # your product's user segments — e.g. [buyers, sellers], [free, paid]
  default_period: last_full_month   # last_full_month | last_30d | last_quarter
```

> `segments` has no universal default: two-sided marketplaces split buyers/sellers, SaaS splits by plan or role. `feedback-triage` asks when this key is absent rather than assuming.

### plugin_release section format

Optional; all keys optional. Read by `release-manager` (Step 0); collected interactively and offered for saving on first run. Relevant only if you are releasing **this plugin's repository**, not your product.

```yaml
plugin_release:
  repo_path: "[absolute path to the plugin repo]"
  canonical_remote: origin          # default: origin
  mirror_remotes: [<remote>, ...]   # additional remotes to sync tags/branches to
  vpn_required_hosts: [<host>, ...] # hosts reachable only on VPN — pre-flight warns
  protected_branches: [main]        # default: [main]
  confluence_changelog_page_id: "[page id]"
  versioning_table: null            # null → PATCH/MINOR/MAJOR rules from the CHANGELOG header
```

### data_sources_catalog section format

Optional but strongly recommended for products with dashboards. Read by `cjm-research` and `product-analysis` via `data-integrity-protocol.md` → Gate Check 3 (Multi-Source Cross-Validation): it is how the skill knows which **second, independently-built** source validates a given metric. Absent → every metric that needs cross-validation is ⚠️ Caveat rather than ✅ Verified.

```yaml
data_sources_catalog:
  - metric: "[GMV YoY]"
    primary: "[workbook + view]"
    cross_validation: "[a second, independently-built source]"
    methodology_doc: "[attribution/metric-definition page]"   # optional
  - metric: "[Checkout CR]"
    primary: "[funnel workbook + view]"
    cross_validation: "[CJM master dashboard]"
```

> Name the **view**, not just the workbook: two views of one workbook can disagree, and Gate Check 3 needs to know which produced the number. The same workbook under a different filter is **not** a second source — it inherits the same methodology error.
