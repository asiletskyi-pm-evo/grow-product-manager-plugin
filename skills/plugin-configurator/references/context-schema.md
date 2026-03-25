# Local Context Schema

This document defines the complete structure of `local-context.md` — the organization-specific configuration file that all plugin skills read from.

## Structure Overview

```
local-context.md
├── User Profile
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
| email | ✅ | Feature Task Creator | For Jira account lookup |
| jira_account_id | optional | Feature Task Creator | Jira accountId (auto-discovered if Jira MCP available) |
| language | ✅ | All skills | Preferred language for skill output (uk/en) |

### Organization (required, 1+)

| Field | Required | Used by | Description |
|-------|----------|---------|-------------|
| name | ✅ | All skills | Organization name |
| domain | optional | Product Research | Company domain (e.g., company.com) |
| jira_instance | optional | Feature Task Creator, Requirements Creator | Jira cloud URL (e.g., company.atlassian.net) |
| confluence_instance | optional | All publishing skills | Confluence cloud URL |

### Integrations & Data Sources (per organization)

| Field | Required | Used by | Description |
|-------|----------|---------|-------------|
| tableau_base_url | optional | Product Analysis | Tableau server URL (e.g., https://tableau.company.dev) |
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
| platforms | ✅ | Requirements Creator, Feature Task Creator | List: Android, iOS, Web Portal, Web CMS, Admin, etc. |
| locales | optional | Requirements Creator | Countries/locales where product operates |
| jira_project_key | ✅ | Feature Task Creator, Requirements Creator | Jira project key (e.g., PROJ) |
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

### Team (optional, per organization)

| Field | Required | Used by | Description |
|-------|----------|---------|-------------|
| name | ✅ | Feature Task Creator | Team name |
| jira_team_id | optional | Feature Task Creator | Team ID in Jira custom field |
| members | optional | Feature Task Creator | List of members with name, role, jira_account_id |

### Custom Sections

Users can add any additional sections with free-form markdown content. The configurator preserves these during updates.

## Which Skills Read What

| Skill | Required context | Optional context |
|-------|-----------------|-----------------|
| **Product Analysis** | product.name | tableau URLs, ab_test_dashboards, key_metrics, OKRs |
| **Requirements Creator** | product.name, jira_project_key, platforms | confluence_template_url, locales, key_metrics |
| **Feature Task Creator** | product.name, jira_project_key | team, members with jira_account_id, confluence_space |
| **Product Research** | product.name | competitors, domain, product.url |
| **Write Concept** | product.name | confluence_space, key_metrics, OKRs |
| **Brainstorm Features** | product.name | key_metrics, competitors, OKRs |
| **Plugin Configurator** | — | reads/writes everything |

## Validation Rules

### Required fields (Onboarding must collect these)
1. User profile: name, role, email, language
2. At least 1 organization with name
3. At least 1 product with: name, description, platforms, jira_project_key

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
