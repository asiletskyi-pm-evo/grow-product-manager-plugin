---
name: knowledge-library
version: 0.2.0
description: Manage a local library of curated knowledge sources (articles, benchmarks, research) with categorization, trust scoring, and multi-mode search. Use when the user asks to "manage sources", "add to library", "search knowledge", "import sources", "show library", or when another skill needs to search for enrichment data. Also triggers when user says "add this article", "save this source", "what sources do we have on [topic]".
---

# Knowledge Library

Manage a local library of curated knowledge sources with categorization, trust scoring, and multi-mode search. Acts as a knowledge layer that other skills query during enrichment.

This is a **service skill** — it provides search capabilities to other skills (primarily `cjm-research`) and also supports direct user management of the library.

## Prerequisites

Before any operation, follow these shared references:
- **`references/local-context-protocol.md`** — read `local-context.md` for Knowledge Library configuration
- **`references/integration-strategy.md`** — MCP → Registry → Browser fallback chain
- **`references/data-policy.md`** — confidentiality rules (internal sources stay internal)

## Library Storage

The library is stored in the user's workspace folder:

```
workspace/knowledge-library/
├── library.md            # Master index — markdown table of all sources
├── categories.md         # Category definitions (default + custom)
├── trust-scores.yaml     # Trust scores and metadata for auto-calculation
├── sources/              # Individual source detail files (for rich insights)
│   ├── baymard-checkout-flow.md
│   └── ...
├── trust-reports/        # Monthly trust re-evaluation reports
│   ├── 2026-04-07.md
│   └── ...
└── health-checks/        # Stored CJM health-check snapshots
    ├── 2026-04-07.md
    └── ...
```

### library.md format

The master index uses a markdown table for human readability:

```markdown
# Knowledge Library

> Last updated: [date]. Sources: [count]. Average trust: [score].

## Sources

| ID | Title | URL | Category | Type | Trust | Tags | Added |
|----|-------|-----|----------|------|-------|------|-------|
| baymard-checkout-flow | Checkout Flow Design | https://baymard.com/... | cart-checkout | baymard | 0.85 | checkout, abandonment | 2026-04-10 |
| ... | ... | ... | ... | ... | ... | ... | ... |
```

### trust-scores.yaml format

Machine-readable metadata for automated calculations:

```yaml
# Auto-generated. Do not edit manually — use Knowledge Library skill to manage.
last_recalculated: 2026-04-10

sources:
  - id: baymard-checkout-flow
    trust_score: 0.85
    trust_override: null
    last_verified: 2026-04-10
    publication_date: 2023-06-15
    citation_count: 3
    freshness_penalty: -0.05
    type_base_score: 0.9
```

### Source detail files (sources/*.md)

Optional — created for sources with rich insights:

```markdown
# Checkout Flow Design

- **Source:** https://baymard.com/blog/checkout-flow-design
- **Type:** baymard
- **Trust:** 0.85
- **Added:** 2026-04-10

## Key Insights

1. Single-page checkout reduces abandonment by 20-30%
2. Guest checkout is critical for first-time buyers
3. Progress indicators reduce perceived complexity

## Applicable Stages

- cart-checkout
- payment-post-purchase

## Notes

[User or skill-added notes about this source]
```

---

## Modes of Operation

| Mode | Trigger | Description |
|------|---------|-------------|
| **Add** | User: "add source", "save this article"; Skill: auto-add during research | Add new source(s) with auto-categorization and trust scoring |
| **Search** | Skill delegation or user: "what sources do we have on checkout?" | Search library by category, tags, keywords; return matching sources |
| **Search Confluence** | Skill delegation or user: "search confluence for..." | Search Confluence via MCP for internal documents |
| **Search Google Drive** | Skill delegation or user: "search drive for..." | Search Google Drive via MCP for internal files |
| **Search Web** | Skill delegation | Web search via delegation to `product-research` |
| **Search Baymard** | Skill delegation or user: "search baymard for..." | Search Baymard Premium via browser (requires user login) or local library |
| **Manage** | User: "show library", "edit source", "remove source" | List, edit, remove sources; update trust scores; manage categories |
| **Import** | User: "import sources", "add these URLs" | Bulk import from URL list, CSV, or structured text |
| **Export** | User: "export library" | Export as markdown table, CSV, or YAML |
| **Verify** | Scheduled or user: "check sources" | Re-check freshness, validate URLs, recalculate trust |
| **Scheduled Trust Re-evaluation** | Auto: monthly task (via `schedule` skill) | Monthly automated recalculation of trust scores for all sources; validates URLs, applies freshness decay, generates report. No user intervention needed; results delivered as report. |

---

## Workflow — Add Mode

### A-1. Receive source

Source can come from:
- User provides URL(s) or text
- User uploads a file (PDF, DOCX, screenshot)
- Another skill passes a discovered source
- User pastes article content directly

### A-2. Extract metadata

For URL sources:
- Fetch page title, description, publication date (via browser or web search)
- If fetch fails — ask user for title and date

For uploaded files:
- Extract title from file name or content
- Ask user for URL (if applicable) and publication date

### A-3. Auto-categorize

Match the source to existing categories based on:
1. URL domain (e.g., `baymard.com` → type: `baymard`)
2. Title keywords (e.g., "checkout" → category: `cart-checkout`)
3. Content analysis (if available)

Present the auto-categorization to the user for confirmation:
> "I categorized this source as: **[category]**, type: **[type]**, tags: **[tags]**. Is this correct?"

Allow the user to adjust before saving.

### A-4. Calculate trust score

Apply the trust score formula (see Trust Score Calculation below).

Show the calculated score to the user:
> "Trust score: **[score]** (based on: [type] base [X] + freshness [Y] + citations [Z])."

### A-5. Save to library

1. Add row to `library.md` table
2. Add entry to `trust-scores.yaml`
3. If source has rich insights — create `sources/[id].md` detail file
4. Update the header stats in `library.md` (source count, average trust)

### A-6. Confirm

> "Source added to Knowledge Library: **[title]** (trust: [score], category: [category])."

---

## Workflow — Search Mode

Search is the primary mode used by other skills. It can be invoked directly or via delegation.

### S-1. Receive search query

Query comes as:
- Keywords (e.g., "checkout optimization")
- Category (e.g., `cart-checkout`)
- Tags (e.g., `abandonment, mobile`)
- Combination of the above
- Anomaly context (from `cjm-research`: stage + metric + deviation)

### S-2. Search local library

Filter `library.md` entries by:
1. Category match (exact or parent category)
2. Tag match (any tag overlap)
3. Keyword match in title
4. Trust threshold: only include sources with trust_score >= configured minimum (default 0.5)

Rank results by:
1. Category relevance (exact match > parent match)
2. Trust score (higher first)
3. Freshness (newer first, as tiebreaker)

### S-3. Return results

Return to calling skill or user:

```markdown
### Knowledge Library Results for "[query]"

Found **[N]** matching sources (trust threshold: [min]):

| # | Title | Trust | Category | Key Insight |
|---|-------|-------|----------|-------------|
| 1 | [Title] | 0.85 | cart-checkout | [Top insight from source] |
| 2 | [Title] | 0.78 | cart-checkout | [Top insight from source] |
| ... | ... | ... | ... | ... |

Sources: Knowledge Library (local)
```

If no results found:
> "No matching sources found in the Knowledge Library for '[query]'. Consider: adding relevant sources, or expanding search to internet/Confluence."

---

## Workflow — Search Confluence Mode

### SC-1. Check Confluence MCP availability

Follow `integration-strategy.md`:
1. Check for Confluence MCP tools (`searchConfluenceUsingCql`, `getConfluencePage`)
2. If not available → search MCP registry → suggest connector
3. If still not available → browser fallback

### SC-2. Build search query

Use CQL (Confluence Query Language):
```
type = page AND space IN ([configured_spaces]) AND text ~ "[search_terms]"
```

Configured spaces come from `local-context.md` → Knowledge Library Configuration → Configured Confluence Spaces.

If no spaces configured — search all accessible spaces, but warn user:
> "No Confluence spaces configured for CJM search. Searching all accessible spaces. You can configure specific spaces via Plugin Configurator."

### SC-3. Filter and rank results

- Prioritize pages from configured spaces
- Prioritize pages with recent updates
- Exclude pages with `noindex` label (Confluence convention for draft/deprecated content)
- Limit to top 10 results

### SC-4. Extract insights

For top results, read the page content (`getConfluencePage`) and extract:
- Key findings relevant to the search query
- Data points, metrics, experiment results
- Dates (to assess freshness)

### SC-5. Return results

```markdown
### Confluence Search Results for "[query]"

Found **[N]** relevant pages:

| # | Title | Space | Updated | Key Finding |
|---|-------|-------|---------|-------------|
| 1 | [Page title] | [Space] | [Date] | [Relevant excerpt] |
| ... | ... | ... | ... | ... |

Sources: Confluence (internal)
```

---

## Workflow — Search Google Drive Mode

### GD-1. Check Google Drive MCP availability

Follow `integration-strategy.md`:
1. Check for Google Drive MCP tools
2. If not available → search MCP registry → suggest connector
3. If still not available → browser fallback (navigate to drive.google.com)

### GD-2. Search within configured folders

Configured folders come from `local-context.md` → Knowledge Library Configuration → Configured Google Drive Folders.

Search by:
- File name keywords
- File content (if supported by MCP)
- File type (presentations, documents, spreadsheets)

### GD-3. Extract and return results

For document/presentation results:
- Read title and summary
- If accessible, extract key content relevant to the query
- Note file type and last modified date

```markdown
### Google Drive Search Results for "[query]"

Found **[N]** relevant files:

| # | Title | Type | Folder | Modified | Key Content |
|---|-------|------|--------|----------|-------------|
| 1 | [File name] | Presentation | [Folder] | [Date] | [Relevant excerpt] |
| ... | ... | ... | ... | ... | ... |

Sources: Google Drive (internal)
```

---

## Workflow — Search Baymard Mode

### B-1. Check Baymard access

Read `local-context.md` → Knowledge Library Configuration → Baymard Premium:
- If `access: yes` → proceed with browser-based search
- If `access: no` → search local library only (sources tagged `baymard`)

### B-2. Browser-based search (if access configured)

1. Navigate to Baymard Premium URL
2. Check if logged in — if not, inform user:
   > "Baymard Premium requires login. Please log in to your Baymard account in the browser, then tell me to continue."
3. Wait for user confirmation
4. Search Baymard for the query topic
5. Extract relevant article titles, URLs, and key findings

### B-3. User-provided content

The user can also provide Baymard content directly:
- Paste article URLs → skill fetches and extracts insights
- Upload exported files → skill reads and extracts
- Paste article text → skill extracts key insights

In all cases, add extracted sources to the local library for future reuse.

### B-4. Return results

```markdown
### Baymard Search Results for "[query]"

Found **[N]** relevant articles:

| # | Title | Trust | Key Insight |
|---|-------|-------|-------------|
| 1 | [Article title] | 0.90 | [Key finding] |
| ... | ... | ... | ... |

Sources: Baymard Premium
```

---

## Workflow — Manage Mode

### M-1. Show library overview

Display:
- Total sources count
- Sources by category (count per category)
- Sources by type (count per type)
- Average trust score
- Last verification date
- Sources flagged as stale

### M-2. User actions

Support these management actions:
- **List** — show all sources (with pagination for large libraries)
- **Filter** — filter by category, type, trust score range, tags
- **Edit** — modify source metadata (title, category, tags, notes)
- **Remove** — delete a source (with confirmation)
- **Override trust** — manually set trust score for a source
- **Add category** — create a new custom category
- **Edit category** — rename or merge categories

### M-3. Save changes

After any modification:
1. Update `library.md`
2. Update `trust-scores.yaml`
3. Update source detail files if applicable
4. Show changelog of modifications

---

## Workflow — Import Mode

### I-1. Receive import data

Accept sources in these formats:
- **URL list** — one URL per line, or comma-separated
- **CSV** — columns: URL, Title (optional), Category (optional), Tags (optional)
- **Structured text** — markdown list with URLs and descriptions
- **Pasted content** — free-form text with URLs that will be extracted

### I-2. Process each source

For each URL in the import:
1. Fetch metadata (title, publication date)
2. Auto-categorize
3. Calculate trust score
4. Check for duplicates (URL match against existing library)

### I-3. Present summary for review

> "Import preview: **[N]** new sources found ([M] duplicates skipped):"

Show a table with: Title, URL, Category, Type, Trust Score (auto-calculated).

Allow the user to:
- Confirm all
- Remove specific sources before import
- Adjust categories or tags

### I-4. Save all confirmed sources

Batch-add all confirmed sources to library.md and trust-scores.yaml.

> "Imported **[N]** sources to Knowledge Library. Categories: [breakdown]."

---

## Workflow — Verify Mode

### V-1. Load all sources

Read `library.md` and `trust-scores.yaml`.

### V-2. For each source

1. **Check URL** — attempt to reach the URL (via web fetch or browser)
   - If unreachable → mark as `broken_link`
2. **Check freshness** — calculate time since publication
   - Apply freshness decay: -0.05 per year (minimum trust: 0.3)
3. **Recalculate trust** — apply full trust formula with updated data
4. **Check citation count** — scan other sources for references to this URL

### V-3. Update scores

Update `trust-scores.yaml` with recalculated values.
Update `library.md` trust column.

### V-4. Report

```markdown
### Knowledge Library Verification Report — [date]

| Metric | Value |
|--------|-------|
| Total sources | [N] |
| Verified | [N] |
| Broken links | [N] |
| Trust updated | [N] |
| Flagged as stale (trust < 0.5) | [N] |

#### Sources with changes:
| Source | Old Trust | New Trust | Reason |
|--------|-----------|-----------|--------|
| [Title] | 0.80 | 0.75 | Freshness decay |
| [Title] | 0.70 | 0.00 | Broken link |
| ... | ... | ... | ... |
```

---

## Workflow — Scheduled Trust Re-evaluation Mode

Auto-triggered monthly via `schedule` skill. This is an extended verification that includes:
- Automated freshness decay recalculation for all sources
- URL validation with HTTP HEAD requests
- Trust score recomputation using adjusted formula
- Automated report generation
- User notification of changes

### TR-1. Load all sources

1. Read `library.md` — extract all source rows into a working set
2. Read `trust-scores.yaml` — load all source metadata
3. Validate that both files are synchronized (same source IDs); warn if mismatches found

**Prerequisites check:**
- Confirm `knowledge-library/` directory exists
- Confirm `library.md` and `trust-scores.yaml` exist and are readable

### TR-2. Recalculate freshness component

For each source, compute freshness decay:

```
days_since_added = (today - date_added)
freshness = max(0, 1 - (days_since_added / 730))
```

Where:
- `date_added` is the source's "Added" date from `library.md`
- 730 days = 2 year decay window
- Freshness ranges from 1.0 (just added) to 0.0 (2+ years old)

Store intermediate freshness value for use in TR-4.

### TR-3. Validate URLs

For each source:

1. **Fetch URL** — attempt HTTP HEAD request to the source URL
   - Use browser fetch (preferred) or web fetch tool
   - Timeout: 5 seconds per URL
   - Log success/failure for each URL

2. **Mark broken links** — if URL unreachable (404, 500, timeout, DNS failure):
   - Set flag `url_broken: true` in `trust-scores.yaml`
   - Note the failure reason (404, timeout, DNS error, etc.) in `failure_reason` field
   - **Do not delete the source** — keep it in library with broken flag

3. **Apply penalty** — if URL broken, reduce trust by 0.2 (applied in TR-4)

### TR-4. Recalculate final trust score

For each source, apply adjusted trust formula:

```
trust = (source_authority × 0.4) + (evidence_quality × 0.3) + (freshness × 0.2) + (citation_count × 0.1)
```

Where:
- **source_authority** = type base score (from Trust Score Calculation section) minus any URL broken penalty (−0.2 if broken)
- **evidence_quality** = from type base score (same as source_authority in this context)
- **freshness** = computed value from TR-2
- **citation_count** = number of other sources in library that reference this source's URL (from TR-3 validation or manual count from sources/*.md files)

**Special handling:**
- If `trust_override` exists in `trust-scores.yaml` → skip recalculation, preserve override
- Clamp final trust to [0.0, 1.0]
- Track "old trust" and "new trust" separately for the report

### TR-5. Update trust-scores.yaml

For each source, update:
1. `trust_score` → new calculated value (or preserve override)
2. `last_verified` → today's date
3. `url_broken` → true/false from TR-3
4. `failure_reason` → (optional) failure details if URL broken
5. `freshness_component` → computed freshness value from TR-2

Update file header:
```yaml
last_recalculated: [today's date in YYYY-MM-DD format]
```

### TR-6. Update library.md

For each source row in the table:
1. Update the `Trust` column with new trust score from TR-4
2. If URL broken → append ⚠️ symbol to the Trust cell (e.g., `0.65 ⚠️`)
3. Update header stats:
   - Last updated: [today's date]
   - Average trust: [recalculated average of all sources]

### TR-7. Flag sources below threshold

For each source where trust_score < 0.5 after recalculation:
1. Add tag `stale` to the source in `library.md` (in the Tags column)
2. In `trust-scores.yaml`, set `needs_review: true`
3. Collect these sources for the report (see TR-8)

### TR-8. Generate re-evaluation report

Create a new markdown file: `knowledge-library/trust-reports/[YYYY-MM-DD].md`

**Report template:**

```markdown
# Knowledge Library Trust Re-evaluation Report

**Run date:** [YYYY-MM-DD HH:MM UTC]  
**Frequency:** Monthly (auto-triggered)

---

## Summary

| Metric | Value |
|--------|-------|
| Total sources evaluated | [N] |
| Sources with updated trust | [N] |
| URLs validated | [N] |
| Broken links found | [N] |
| Sources flagged as stale (trust < 0.5) | [N] |
| Average trust score (before) | [X.XX] |
| Average trust score (after) | [X.XX] |

---

## Sources with changes

Only sources where `old_trust ≠ new_trust` are listed:

| Source | Category | Old Trust | New Trust | Reason | Status |
|--------|----------|-----------|-----------|--------|--------|
| [Title] | [cat] | 0.80 | 0.76 | Freshness decay (−0.04) | — |
| [Title] | [cat] | 0.70 | 0.50 | Broken link (−0.2), freshness (−0.0) | ⚠️ Flagged for review |
| [Title] | [cat] | 0.75 | 0.75 | No change | — |

---

## Broken links

[N] URLs could not be reached:

| Source | URL | Failure | |
|--------|-----|---------|---|
| [Title] | [url] | 404 Not Found | Recommend removing or finding updated URL |
| [Title] | [url] | Connection timeout | May be temporary; check manually |

---

## Sources flagged for review

These sources dropped below the 0.5 threshold and should be reviewed for removal or curation:

- [Source 1] (trust: 0.48, reason: freshness + broken URL)
- [Source 2] (trust: 0.42, reason: freshness decay)

---

## Recommendations

1. Remove sources with trust < 0.3 (low confidence)
2. Investigate broken links — try finding updated URLs
3. For sources flagged as stale (0.5 < trust < 0.6) — review relevance and consider refreshing

---

## Next run

Next scheduled re-evaluation: [date + 1 month]  
To adjust frequency: user can reconfigure the scheduled task via the `schedule` skill or Plugin Configurator.
```

### TR-9. Notify user

After report generation:

1. **Save report to disk** at `knowledge-library/trust-reports/[YYYY-MM-DD].md`
2. **Display summary** in user-facing output (if task is triggered during a session):
   ```
   Knowledge Library: Monthly Trust Re-evaluation Complete
   
   Evaluated [N] sources — [M] updated, [K] broken links found.
   Flagged [Z] sources for review (trust < 0.5).
   
   Full report: knowledge-library/trust-reports/[YYYY-MM-DD].md
   ```
3. **If triggered as background task** (scheduled) — still save report; if task is configured to notify, include the summary above

---

## Workflow — Scheduled Trust Re-evaluation (user-initiated "check sources" vs. monthly auto)

### User-initiated verification:

When user says "check sources", "verify library", or "run verification":
1. Run the full Scheduled Trust Re-evaluation workflow (TR-1 through TR-9)
2. Display final summary in chat
3. Offer to show full report or specific sections (broken links, sources flagged, etc.)

### Monthly auto-triggered:

When the scheduled task runs (via `schedule` skill):
1. Run full workflow in background
2. Save report to `trust-reports/[date].md`
3. Send notification to user (if configured in Schedule setup section)

---

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

## Integration with Other Skills

### As a service (called by other skills)

When another skill calls `knowledge-library`, it passes:
- **Query** — keywords, category, or anomaly context
- **Search modes** — which modes to use (library / confluence / gdrive / baymard / internet)
- **Trust threshold** — minimum trust score for results (default 0.5)
- **Max results** — maximum number of results to return (default 10)

The skill returns:
- List of matching sources with: title, URL, trust score, key insight, source type
- Search metadata: modes used, total results found, threshold applied

### Cross-skill enrichment behavior

- When called from `cjm-research` → **always** perform search in all requested modes (mandatory part of pipeline)
- When called from `product-research` or `brainstorm-features` → only when user explicitly requested or approved (see architecture proposal, decision #6)
- When the user interacts directly → perform the requested operation

### Proposing enrichment to other skills

When `product-research` or `brainstorm-features` are running and Knowledge Library is initialized:
1. Check if library contains sources relevant to the current topic
2. If relevant sources exist (>= 3 sources matching the topic), inform the calling skill
3. The calling skill then proposes to the user: "Knowledge Library has [N] sources on [topic]. Use them for enrichment?"
4. Only proceed with library search if user confirms

---

## Onboarding (integrated with Plugin Configurator)

When Plugin Configurator runs CJM onboarding (Step 8+), it delegates Knowledge Library setup:

### KL-1. Ask about library setup

> "Would you like to set up a Knowledge Library for CJM research? This lets you save and search curated sources (articles, benchmarks, best practices)."

If no → skip, library can be set up later.

### KL-2. Initialize directory structure

Create the `knowledge-library/` directory with empty `library.md`, `categories.md` (with defaults), and `trust-scores.yaml`.

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

---

## Schedule Setup (Automated Monthly Trust Re-evaluation)

On first initialization or when the user requests "set up monthly verification", the Knowledge Library offers to establish a recurring automated trust re-evaluation task.

### KL-7. Propose schedule setup

When Knowledge Library is first initialized (Step 5 of Onboarding), after confirming the library is ready, ask:

> "Would you like to set up **monthly automated trust re-evaluation**? This will:"
> - Recalculate trust scores for all sources based on freshness decay
> - Validate that all source URLs are still reachable
> - Flag sources below the minimum trust threshold
> - Generate a monthly report
>
> This runs automatically every month at no cost to your interaction budget. **Recommended: yes.**

If user declines → note in config, can be enabled later.

### KL-8. Configure schedule parameters

If user says yes, present configuration options:

> "Configure the monthly trust re-evaluation:"

**Frequency** (default: monthly, i.e., "0 9 * * 0" = every Sunday at 9 AM)
- Monthly (recommended)
- Bi-weekly
- Weekly
- Custom (user provides cron expression)

**Notification channel** (default: report saved, no active notification)
- Save report only (silent background run)
- Notify me of summary (user receives notification with summary)
- Notify me + show full report (user sees full report in chat)

**Auto-remove stale sources** (default: no)
- No — flag for review, keep in library (recommended for safety)
- Yes — automatically remove sources with trust < 0.3 (aggressive)

### KL-9. Create scheduled task

Call `schedule` skill to create a recurring task:

**Task details:**
- **Task ID:** `knowledge-library-monthly-trust-reeval`
- **Description:** "Monthly automated trust re-evaluation for Knowledge Library"
- **Trigger:** cron expression (from KL-8 Frequency selection)
- **Prompt:** See block below
- **Notify on completion:** yes (if user selected notification in KL-8)

**Scheduled task prompt template:**

```
You are running the monthly Knowledge Library trust re-evaluation.

**Context:**
- User workspace folder: [path from local-context.md]
- Library location: workspace/knowledge-library/
- Config: See local-context.md → Knowledge Library Configuration

**Task:**

Run the **Scheduled Trust Re-evaluation workflow** from the Knowledge Library skill:

1. Load all sources from library.md and trust-scores.yaml
2. For each source:
   - Recalculate freshness: freshness = max(0, 1 - (days_since_added / 730))
   - Validate URLs with HTTP HEAD requests; mark broken ones
   - Recalculate trust using adjusted formula: 
     trust = (source_authority × 0.4) + (evidence_quality × 0.3) + (freshness × 0.2) + (citation_count × 0.1)
   - If trust < 0.5 → flag as stale; if trust < 0.3 and auto-remove enabled → remove source
3. Update trust-scores.yaml and library.md
4. Generate report at knowledge-library/trust-reports/[YYYY-MM-DD].md
5. [If notification enabled] Display summary to user

See SKILL.md → Scheduled Trust Re-evaluation Mode for detailed step-by-step (TR-1 through TR-9).

**Report location:** workspace/knowledge-library/trust-reports/[date].md

[End of prompt]
```

### KL-10. Confirm setup

After task creation:

> "Monthly trust re-evaluation scheduled ✓
>
> - **Frequency:** [selected frequency]
> - **Notification:** [selected notification level]
> - **Auto-remove stale:** [yes/no]
> - **First run:** [date of next scheduled run]
>
> You can reconfigure anytime via: _"Reconfigure trust re-evaluation"_ or Plugin Configurator."

---

## Reconfiguring the schedule

If user later requests to adjust the schedule:

1. List current schedule config (frequency, notification, auto-remove)
2. Ask which settings to change
3. Call `schedule` skill with `update_scheduled_task` to modify:
   - `cronExpression` for frequency changes
   - `notifyOnCompletion` for notification changes
   - Update prompt if auto-remove setting changed
4. Confirm new settings

---

## Quality Standards

- Never delete sources without user confirmation (except when auto-remove enabled in scheduled task, which requires prior explicit user config)
- Always show auto-categorization for user review before saving
- Preserve user trust overrides during verification/recalculation
- Use the user's preferred language for all communications (from `local-context.md`)
- Follow `data-policy.md` — internal source content (Confluence, GDrive) is confidential and must not be sent to external LLMs
- When Baymard requires login — always inform the user, never attempt to bypass authentication
- Scheduled trust re-evaluation runs non-intrusively in background; save reports to `trust-reports/` directory without blocking user workflows
- URL validation in scheduled tasks uses lightweight HEAD requests (no full page fetch) to minimize bandwidth

## Additional Resources

- **`references/cjm-protocol.md`** — anomaly severity, funnel impact formulas, health score
- **`references/funnel-templates.md`** — standard funnel stage templates
- **`references/integration-strategy.md`** — MCP → Registry → Browser fallback chain
- **`references/data-policy.md`** — data confidentiality rules
- **`references/self-improvement.md`** — self-improvement protocol
- **`references/context-schema.md`** — complete schema definition for local-context.md fields
