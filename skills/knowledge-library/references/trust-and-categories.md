# Trust scoring, default categories, and Knowledge Library onboarding (KL-1..KL-6)

> Part of `knowledge-library`. Trust formula and categories are needed by Add/Import/Verify workflows; the onboarding section is invoked by plugin-configurator Step 12.

## Trust Score Calculation

### Formula

```
trust_score = type_base_score + freshness_adjustment + citation_bonus
```

Clamped to range [0.0, 1.0].

### Type base scores

| Source type | Base score | Examples |
|------------|-----------|---------|
| `internal-experiment` | 0.95 | Internal A/B test results, post-mortems |
| `baymard` | 0.90 | Baymard Institute articles and guidelines |
| `academic` | 0.85 | Peer-reviewed papers, university research |
| `industry-report` | 0.80 | Nielsen Norman, Forrester, McKinsey reports |
| `user-feedback` | 0.70 | NPS verbatims, support tickets, app reviews |
| `blog-article` | 0.60 | Expert blog posts, Medium articles, tech blogs |
| `internal-confluence` | 0.75 | Internal Confluence pages (research, analysis) |
| `internal-gdrive` | 0.70 | Internal Google Drive documents |
| `external` | 0.60 | General external sources |

### Freshness adjustment

```
years_since_publication = (current_date - publication_date) / 365
freshness_adjustment = -(years_since_publication × 0.05)
```

Minimum freshness adjustment: -0.30 (so a 6+ year old source loses max 0.30).

If publication date unknown — apply -0.10 as default penalty.

### Citation bonus

```
citation_bonus = min(citation_count × 0.05, 0.15)
```

A source cited by 3+ other sources in the library gets the maximum +0.15 bonus.

### User override

If `trust_override` is set in `trust-scores.yaml`, it replaces the calculated score entirely. The skill should note this:
> "Trust score: **0.90** (user override; auto-calculated would be 0.75)."

### Monthly re-evaluation

A scheduled task (via `schedule` skill) triggers Verify mode monthly:
1. Recalculate freshness decay for all sources
2. Validate URLs
3. Update citation counts
4. Flag sources that dropped below the minimum trust threshold
5. Generate verification report

---

## Default Categories

### By funnel stage

| Category ID | Name | Description |
|------------|------|-------------|
| `start-listing` | Start / Listing | Homepage, search results, category pages, initial browsing |
| `product-page` | Product Page | Product detail pages, gallery, reviews, specifications |
| `cart-checkout` | Cart / Checkout | Shopping cart, checkout flow, forms, shipping |
| `payment-post-purchase` | Payment / Post-Purchase | Payment processing, order confirmation, returns, support |

### By UX area

| Category ID | Name | Description |
|------------|------|-------------|
| `navigation` | Navigation | Menu, breadcrumbs, site structure, wayfinding |
| `filtering` | Filtering & Sorting | Faceted search, filters, sorting options |
| `search` | Search | Site search, autocomplete, search results |
| `forms` | Forms & Input | Form design, validation, error handling, input types |
| `mobile` | Mobile UX | Responsive design, touch interactions, mobile-specific patterns |
| `accessibility` | Accessibility | WCAG compliance, screen readers, keyboard navigation |

### By business area

| Category ID | Name | Description |
|------------|------|-------------|
| `pricing` | Pricing | Pricing strategy, pricing display, discounts |
| `promotions` | Promotions | Sales, coupons, loyalty programs |
| `personalization` | Personalization | Recommendations, personalized content |
| `retention` | Retention | Re-engagement, email, push notifications |
| `onboarding` | Onboarding | First-time user experience, tutorials, getting started |

### By research type

| Category ID | Name | Description |
|------------|------|-------------|
| `best-practices` | Best Practices | Industry standards, guidelines, heuristics |
| `benchmark` | Benchmark | Quantitative data, conversion benchmarks, industry averages |
| `case-study` | Case Study | Company-specific implementations and results |
| `experiment` | Experiment | A/B tests, experiments with measured outcomes |
| `user-research` | User Research | Interviews, surveys, usability tests |

---

---

## Onboarding (integrated with Plugin Configurator)

When Plugin Configurator runs CJM onboarding (Step 8+), it delegates Knowledge Library setup:

### KL-1. Ask about library setup

> "Would you like to set up a Knowledge Library for CJM research? This lets you save and search curated sources (articles, benchmarks, best practices)."

If no → skip, library can be set up later.

### KL-2. Initialize directory structure

Create the `~/.grow-pm/knowledge-library/` directory with empty `library.md`, `categories.md` (with defaults), and `trust-scores.yaml`.

### KL-3. Source import

> "Would you like to import initial sources?"
>
> Options:
> - **Paste URLs** — I'll fetch metadata and categorize them
> - **Upload a file** — CSV, text file with URLs
> - **Skip** — start with an empty library

If the user provides sources → run Import workflow.

### KL-4. Baymard configuration

> "Do you have access to Baymard Premium (UX research platform)?"

- If yes → collect Baymard URL, save to config
- If no → note that Baymard mode will search local library only

### KL-5. Default search modes

> "Which search modes should be active by default for CJM research?"
>
> - Library (local sources) — recommended, always fast
> - Internet (web search + external LLMs) — recommended for enrichment
> - Confluence (internal docs) — recommended if configured
> - Google Drive (internal files) — recommended if configured
> - Baymard Premium — only if access configured

### KL-6. Validate

- Test Confluence search (if configured)
- Test Google Drive search (if configured)
- Confirm library is ready

> "Knowledge Library initialized: [N] sources, [M] categories, default search modes: [list]."

Plugin Configurator's Step O-T (template onboarding) runs separately — see `plugin-configurator/SKILL.md`.

---
