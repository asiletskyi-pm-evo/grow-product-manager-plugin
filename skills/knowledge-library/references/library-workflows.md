# Library workflows — Add, Search (local/Confluence/GDrive/Baymard), Manage, Import, Verify

> Part of `knowledge-library`. Loaded on demand when entering a mode — read ONLY the workflow for the active mode. Storage model, mode map, service contract, and Vault Mirror Sync live in SKILL.md.

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

> **Subagent delegation (large fan-out).** For many sources or several independent search modes, delegate per `references/subagent-delegation.md`: split by source group / mode into batches, spawn subagents in parallel, each returns a compact structured result (per-source title, key insight, trust score, link), and the main agent aggregates (merge, dedupe, rank). Falls back to inline if subagents are unavailable.

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
