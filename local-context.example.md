# Local Context Configuration

This file provides organization-specific context for the Grow Product Manager plugin. Copy this file as `local-context.md` and fill in your values. The plugin will use this context to adapt skill behavior to your specific tools, projects, and products.

**Important:** `local-context.md` is gitignored and should NOT be committed to the repository. It contains internal URLs, project names, and other organization-specific information.

## Product Context

### Product Names
<!-- List your products/marketplaces that the plugin works with -->
- Product 1: `Your Product Name`
- Product 2: `Your Second Product Name`
<!-- Example: Prom.ua, Satu.kz -->

### Default Locales
<!-- List locales/countries your products operate in -->
- Locale 1: `your-locale-1`
- Locale 2: `your-locale-2`

## Jira Configuration

### Project Keys
<!-- Your Jira project keys used in examples and defaults -->
- Primary project key: `PROJ`
<!-- Example: SHOPEX -->

### Team Field
<!-- Custom field ID for Team in your Jira instance -->
- Team field ID: `customfield_10001`
- Example Team value: `"your-team-uuid"`

## Confluence Configuration

### Requirements Template
<!-- URL to your organization's requirements template in Confluence -->
- Template URL: `https://your-domain.atlassian.net/wiki/x/YOUR_ID`
- Template name: `Your Template Name`
<!-- Example: "Шаблон Фіча - YourProject" -->

### Spaces
<!-- Default Confluence spaces for publishing -->
- Default space: `YOUR_SPACE`

## Analytics Configuration

### Tableau Dashboards
<!-- URLs to your Tableau dashboards used for A/B test analysis -->
- A/B Test Dashboard 1 (e.g., Web): `https://your-tableau-instance/#/workbooks/XXX/views`
- A/B Test Dashboard 2 (e.g., Mobile): `https://your-tableau-instance/#/workbooks/YYY/views`

### Other Analytics Tools
<!-- Add URLs to other analytics tools your organization uses -->
- Analytics tool: `URL`

## Feature Naming Examples
<!-- Examples of feature names used in your organization for reference -->
- Example feature title: `[PROJ-1234.5] - Feature Name Description`
- Example feature name pattern: `EPICKEY-NUMBER.NUMBER`
