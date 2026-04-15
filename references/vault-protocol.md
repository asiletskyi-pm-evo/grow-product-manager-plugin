# Vault Protocol

## Overview

This document defines how every skill in the Grow Product Manager Plugin interacts with Obsidian Vault for persistent knowledge accumulation. All skills **SHOULD** follow this protocol, but Vault is **OPTIONAL** — if not configured, skills work normally without any vault functionality.

**Related documentation:**
- For Vault schema (frontmatter, types, tags): see `references/vault-schema.md`
- For local configuration reading: see `references/local-context-protocol.md`

---

## Vault Level Detection

Vault detection is executed during **Step 0** (after reading `local-context.md`). Detection establishes one of three operational levels:

### Levels

- **L0: No vault configured** → Skip all vault operations silently
- **L1: Vault path configured, file system access only** → Read/write `.md` files, search via glob + grep
- **L2: Vault path + Obsidian MCP available** → L1 + full-text search, Dataview, graph traversal

### Detection Algorithm

```
1. Read local-context.md section "Obsidian Vaults"
2. If section missing OR no vault paths found
   → return L0
3. For each vault in list:
   a. Check directory exists: stat(path)
   b. Check plugin folder exists: stat(path/{plugin_folder}/)
   c. If either fails → skip this vault
4. If valid vault(s) found AND MCP detection != "disabled"
   → try Obsidian MCP call (test_mcp_connection)
   → if responds successfully → L2
   → if no response or error → L1
5. Store vault_level and vault_configs in session context
6. If no valid vaults found → downgrade to L0
```

### Session Context Storage

After detection, store in session:
```
session.vault = {
  level: L0 | L1 | L2,
  vaults: [
    {
      path: string,
      product_binding: "product_key" | "all",
      mcp_available: boolean
    }
  ]
}
```

---

## Multi-Vault Resolution

The plugin supports multiple vaults with intelligent routing:

### When Saving

```
resolve_vault(product) → vault_config:
1. For each vault in vault_configs:
   a. If vault.product_binding == product → return vault
2. If no exact match:
   a. Find vault with product_binding == "all"
   b. If found → return it (default vault)
3. If no default vault:
   a. Return first vault in list (fallback)
4. If no vaults → return null (L0 behavior)
```

### When Searching

```
search_all_vaults(criteria):
1. For each vault in vault_configs:
   a. Execute search (L1 or L2) against vault
   b. Collect results with vault_path metadata
2. Merge results across vaults
3. Deduplicate by artifact path
4. Sort by relevance/date
5. Return merged result set
```

---

## Step 0.5 — Vault Context Search (OPTIONAL)

Vault context search is inserted between **Step 0** and **Step 1** of every skill execution. This optional step enriches the skill context with relevant knowledge from the vault.

### Precondition
If `vault_level == L0` → **skip silently**, continue to Step 1 normally.

### Algorithm

```
1. Determine relevant artifact types
   → Use SKILL_CONTEXT_MAP (see section below)
   → Interpret user's input for product/topic keywords

2. Build search criteria:
   - artifact_types: from SKILL_CONTEXT_MAP
   - product: from local-context or user input
   - tags: inferred from skill topic + user keywords
   - status: [active, draft]
   - sort: created DESC
   - limit: 10 results

3. Execute search:
   IF vault_level == L1:
     → file_search(criteria)
   ELSE IF vault_level == L2:
     → mcp_search(criteria)

4. Display results (if found):
   - Show max 5 in summary
   - Ask user: "Use as context? [Yes / Select specific / Skip]"

5. Handle user response:
   IF user selects "Yes" OR "Select specific":
     → read full content of selected artifacts
     → include in prompt context as "Vault Context"
   ELSE IF "Skip":
     → continue normally to Step 1

6. If no results found:
   → continue silently to Step 1
```

### SKILL_CONTEXT_MAP

Defines which artifact types are relevant to each skill:

| Skill | Relevant Types |
|-------|---|
| cjm-research | cjm-analysis, cjm-health-check, funnel-anomaly, ab-test-results, hypothesis |
| write-concept | competitive-analysis, market-research, ux-benchmark, hypothesis, decision, requirements |
| product-analysis | cjm-analysis, ab-test-results, metrics-review, post-release, hypothesis |
| brainstorm-features | cjm-analysis, competitive-analysis, ab-test-results, ux-benchmark, decision |
| requirements-creator | concept, hypothesis, competitive-analysis, decision, ab-test-results |
| meeting-processor | meeting-notes, decision, concept, requirements |
| product-research | competitive-analysis, market-research, ux-benchmark, knowledge-source |
| knowledge-library | knowledge-source |

---

## File Search (L1)

Detailed algorithm for searching vault via file system (no external tools required):

```
file_search(criteria: SearchCriteria) → [ArtifactSummary]:

1. Map artifact types to folders
   → Use TYPE_FOLDER_MAP from vault-schema.md

2. Build glob patterns:
   FOR each type in criteria.artifact_types:
     glob_pattern = "{vault_path}/artifacts/{type}/**/*.md"
     IF criteria.product specified:
       glob_pattern += "{vault_path}/artifacts/{type}/{product_slug}/**/*.md"

3. Find files:
   files = glob(glob_pattern, recursive=true)

4. Optimization - check MOC first:
   IF file exists: {vault_path}/dashboard/MOC-Dashboard.md
     → parse Recent Activity table
     → collect artifact paths from recent items (if within date range)
     → prioritize these files in next step

5. Parse each file:
   FOR each file in files:
     a. Open file
     b. Extract YAML frontmatter (up to closing ---)
     c. Extract ## Summary section (next 2-5 paragraphs)
     d. Parse frontmatter fields: type, product, tags, status, created

6. Filter against criteria:
   KEEP artifact IF:
     - artifact.type in criteria.artifact_types
     - artifact.status in criteria.status
     - artifact.product == criteria.product (if specified)
     - artifact.tags overlap with criteria.tags (if specified)

7. Sort and limit:
   - Sort by: created DESC
   - Keep first N results (default N=10)

8. Build summary:
   FOR each artifact:
     return {
       path: file_path,
       title: frontmatter.title,
       type: frontmatter.type,
       summary: extracted_summary,
       created: frontmatter.created,
       status: frontmatter.status
     }

9. Return results
```

---

## MCP Search (L2)

Enhancement over L1 using Obsidian MCP for richer search capabilities:

```
mcp_search(criteria: SearchCriteria) → [ArtifactSummary]:

1. Execute L1 file_search as baseline
   baseline_results = file_search(criteria)

2. Build MCP full-text search query:
   mcp_query = {
     text: criteria.tags + product keyword,
     path_filter: "{vault_path}/{plugin_folder}/",
     scope: "content + frontmatter"
   }

3. Execute MCP search (with timeout):
   TRY:
     mcp_results = mcp_full_text_search(mcp_query) TIMEOUT 3s
   CATCH timeout:
     → log info "MCP search timed out"
     → return baseline_results (graceful degradation)
   CATCH error:
     → log info "MCP unavailable"
     → return baseline_results

4. Merge results:
   merged = deduplicate(baseline_results + mcp_results)
   → by artifact file_path (canonical path)
   → keep highest relevance score if duplicated

5. Get backlinks for top-5:
   FOR each artifact in merged[0:5]:
     backlinks = mcp_get_backlinks(artifact.path)
     artifact.related_count = len(backlinks)

6. Re-sort by relevance + related_count
   Sort by: (relevance_score * 0.7) + (related_count * 0.3)

7. Return merged results
```

---

## Vault Save

Called after a skill completes its main work to persist the output artifact.

### Algorithm

```
vault_save(artifact, product, options):

1. Precondition checks:
   IF vault_level == L0 → return (skip silently)
   IF sync_mode == "off" → return (read-only, skip silently)
   IF sync_mode == "manual":
     → ask user: "Save to vault? [Yes / No]"
     → if No → return

2. Resolve target vault:
   target_vault = resolve_vault(product)
   IF null → log warning, return

3. Build file path:
   type_folder = TYPE_FOLDER_MAP[artifact.type]
   product_slug = slugify(product)
   filename = "{artifact_type}-{topic_slug}-{YYYY-MM-DD}.md"
     Examples:
       - competitive-checkout-flow-2026-04-14.md
       - cjm-health-check-2026-04-14.md
       - hypothesis-ai-personalization-2026-04-14.md
   
   file_path = {target_vault.path}/artifacts/{type_folder}/{product_slug}/{filename}

4. Create directory structure:
   mkdir -p {file_path_parent_dir}

5. Build frontmatter (see vault-schema.md for schema):
   frontmatter = {
     type: artifact.type,
     product: product,
     title: artifact.title,
     tags: artifact.tags,
     status: "active",
     created: today ISO8601,
     last_updated: today ISO8601,
     related: [],
     linked_hypothesis: null (if applicable),
     test_result: null (if applicable),
     ...
   }

6. Build content:
   REQUIRE: ## Summary section at start
     - 2-5 sentences
     - Captures key findings/output
     - Written for someone discovering vault artifact cold
   
   content = "## Summary\n\n{summary_text}\n\n{full_artifact_content}"

7. Find and link related artifacts (if auto-link enabled):
   FOR each related_type in REVERSE_CONTEXT_MAP[artifact.type]:
     search_results = file_search({
       artifact_types: [related_type],
       product: product,
       status: [active],
       limit: 5
     })
     FOR each result in search_results:
       - Add result.path to frontmatter.related[]
       - Read result file
       - Add [[{current_artifact_path}]] to result.related[]
       - Write result file back

8. Write artifact file:
   write_file(file_path, frontmatter + content)

9. Update MOC indexes (if auto-update enabled):
   - update_dashboard_moc(artifact, target_vault)
   - update_product_moc(artifact, target_vault)
   - update_timeline_moc(artifact, target_vault)

10. Inform user:
    log: "Saved to Vault: {relative_path}"
```

### Special Cases

**Hypothesis Lifecycle**: If skill is `product-analysis` saving `ab-test-results` with linked hypothesis:
- See [Hypothesis Lifecycle Updates](#hypothesis-lifecycle-updates) section

**Duplicate Prevention**: If file already exists:
- Append incrementing suffix: `-2`, `-3`, etc.
- Example: `competitive-checkout-flow-2026-04-14-2.md`

---

## Vault Initialization

Called once by Plugin Configurator when Vault is first connected.

### Algorithm

```
vault_init(vault_path, plugin_folder_name):

1. Create complete folder structure:
   - artifacts/
     - competitive-analysis/
     - cjm-analysis/
     - ab-test-results/
     - decision/
     - hypothesis/
     - meeting-notes/
     - knowledge-source/
     - metrics-review/
     - post-release/
     - ux-benchmark/
     - market-research/
     - concept/
     - requirements/
     - cjm-health-check/
     - funnel-anomaly/
   
   - dashboard/
   - templates/
   - archive/

2. Create product subfolders:
   FOR each product in local-context.products:
     product_slug = slugify(product)
     FOR each artifact type:
       mkdir -p {vault_path}/artifacts/{type}/{product_slug}/

3. Write template files to templates/ folder:
   - template-competitive-analysis.md
   - template-cjm-analysis.md
   - template-hypothesis.md
   - template-decision.md
   - template-meeting-notes.md
   (Use templates from vault-schema.md)

4. Create initial Dashboard MOC:
   Write: {vault_path}/dashboard/MOC-Dashboard.md
     - Section: Recent Activity (empty table)
     - Section: Product Stats (table with product names)
     - Section: Quick Links (to Templates, Archive, Timeline)

5. Copy local-context as reference:
   Copy local-context.md → {vault_path}/REFERENCE-local-context.md
   Mark as read-only

6. Migrate existing knowledge-library:
   IF knowledge-library/ folder exists in vault:
     FOR each .md file:
       - Move to artifacts/knowledge-source/{product}/
       - Update frontmatter with type: knowledge-source
       - Add to MOC Dashboard

7. Create schema version file:
   Write: {vault_path}/.vault-schema-version
   Content: {current_version} (e.g., "1.0")

8. Return success
```

---

## MOC Update Protocol

MOC (Map of Contents) files provide navigation and overview of vault artifacts. They are updated automatically by vault_save.

### Dashboard.md Update

```
update_dashboard_moc(artifact, vault):

1. Open: {vault_path}/dashboard/MOC-Dashboard.md

2. Update Recent Activity table:
   - Prepend new artifact entry to table (at top)
   - Format: | date | type | product | title_link |
   - Example: | 2026-04-14 | hypothesis | MyApp | [[hypothesis-ai-personalization-2026-04-14]] |
   - Keep last 20 entries only (prune old ones)

3. Update product stats:
   - Find product row in "Product Stats" section
   - Increment artifact_count
   - Update last_activity date

4. Update quick links:
   - Add link to recently updated product MOC if new

5. Write file back
```

### Product MOC Update

```
update_product_moc(artifact, vault):

1. Determine MOC path:
   product_slug = slugify(product)
   moc_path = {vault_path}/dashboard/MOC-{product_slug}.md

2. If MOC doesn't exist:
   → Create new MOC with standard sections (see below)

3. Update based on artifact type:
   
   IF artifact.type == cjm-analysis:
     → Update "CJM Artifacts" section
     → Add entry to recent CJM analyses
   
   IF artifact.type == hypothesis:
     → Update "Hypothesis Pipeline" section
     → Add entry under status (active/validated/rejected)
   
   IF artifact.type == ab-test-results:
     → Update "Test Results" section
     → Link to hypothesis (if applicable)
   
   IF artifact.type == decision:
     → Update "Recent Decisions" section
     → Prepend to decision list

4. Write file back

### MOC Structure (for new MOC creation):

---
type: moc
product: {product_name}
created: {today}
---

## {Product Name} Map of Contents

### Active Work
| Type | Latest | Status |
|------|--------|--------|

### CJM Health
- Latest health check: [none]

### Hypothesis Pipeline
- Active: [none]
- Validated: [none]
- Rejected: [none]

### Recent Decisions
[none]

### Test Results
[none]

### Related MOCs
- [[MOC-Dashboard]]
```

### Timeline.md Update

```
update_timeline_moc(artifact, vault):

1. Open or create: {vault_path}/dashboard/Timeline.md

2. Append chronological entry:
   Format: {YYYY-MM-DD} | {type} | {product} | {title_link}
   Example: 2026-04-14 | hypothesis | MyApp | [[hypothesis-ai-personalization-2026-04-14]]

3. Keep entries in reverse chronological order (newest first)

4. Write file back
```

---

## Backlink Management

Backlinking creates explicit relationship between artifacts in the vault.

### Algorithm

```
add_backlinks(source_artifact_path, target_artifact_paths):

FOR each target_path in target_artifact_paths:
  1. Read target file
  2. Parse frontmatter
  3. Check if source_path already in related[] → if yes, skip
  4. Add source_path to related[] in frontmatter
  5. Rewrite target file with updated frontmatter
  6. Store relative wikilink path (from plugin folder)
     Format: [[CJM/MyApp/health-checks/2026-04-14]]
     (no .md extension, relative from vault plugin folder root)
```

### Wikilink Format

- **Format**: `[[relative_path_from_plugin_root]]`
- **No file extension**: `.md` is omitted
- **Example paths**:
  - `[[competitive-analysis/MyApp/competitive-checkout-flow-2026-04-14]]`
  - `[[hypothesis/MyApp/ai-personalization-2026-04-14]]`
  - `[[dashboard/MOC-MyApp]]`

---

## Hypothesis Lifecycle Updates

Special handling for hypothesis artifacts when linked test results are saved.

### Algorithm

```
update_hypothesis_lifecycle(hypothesis_artifact_path, test_result_artifact):

1. Read hypothesis file
2. Parse frontmatter
3. Read test_result frontmatter:
   - Get test_result.winner_id or test_result.loser_id
   - If test_result.winner_id == hypothesis.id:
       hypothesis.hypothesis_status = "validated"
       hypothesis.confidence = 0.95
   - Else if test_result.loser_id == hypothesis.id:
       hypothesis.hypothesis_status = "rejected"
       hypothesis.confidence = 0.2
   - Else:
       hypothesis.hypothesis_status = "inconclusive"

4. Update hypothesis frontmatter:
   - hypothesis_status: updated (see above)
   - test_result: {test_result_artifact_path}
   - validated_by: {test_result artifact}
   - last_reviewed: {today ISO8601}

5. Write hypothesis file back

6. Update hypothesis status in Product MOC
```

---

## Error Handling

All vault errors are **NON-BLOCKING**. The main skill workflow must never fail due to vault issues. Graceful degradation applies throughout.

### Error Handling Table

| Scenario | Behavior |
|----------|----------|
| Vault path doesn't exist | Log warning, fallback to L0 (no vault) |
| No write permissions on vault | Log warning, fallback to L0 |
| MCP unavailable (connection fails) | Log info, fallback to L1 (file search only) |
| MCP timeout (>3s on any call) | Abort MCP call, use L1 results |
| Frontmatter parse error in artifact | Log error with file path, skip broken file, continue search |
| File write error (disk full, permissions) | Log error, inform user "Could not save to vault", skip vault save |
| MOC update fails | Log warning, artifact still saved (MOC update non-critical) |
| Duplicate filename on save | Append suffix: `-2`, `-3`, etc., retry write |
| Directory creation fails | Log error, fallback to L0 |
| Backlink write fails | Log warning, continue (non-critical) |
| Multi-vault merge fails | Use single vault results, continue |

### User Notification

Vault errors are communicated to user only if they block the skill's primary output:

```
IF artifact saved successfully:
  → Show: "Saved to Vault: {relative_path}"
  
IF vault save failed but artifact generated:
  → Show warning: "Could not save to vault (reason). Your artifact is ready above."
  
IF MCP degraded to L1:
  → Silent (no user notification, automatic graceful downgrade)
```

---

## Vault Structure Check

Performed on each skill start as part of **Step 0** vault detection.

### Algorithm

```
vault_structure_check(vault_path, plugin_folder):

1. Check vault root directory:
   IF NOT exists(vault_path):
     → log warning "Vault path does not exist"
     → fallback to L0
     → return

2. Check plugin folder:
   IF NOT exists({vault_path}/{plugin_folder}):
     → create directory

3. For each expected artifact type folder:
   IF NOT exists({vault_path}/artifacts/{type}):
     → create directory silently

4. For each product in local-context:
   FOR each artifact type:
     IF NOT exists({vault_path}/artifacts/{type}/{product_slug}):
       → create directory silently

5. Check dashboard folder:
   IF NOT exists({vault_path}/dashboard):
     → create directory

6. Do NOT delete unexpected files/folders:
   → User may have created custom structure
   → Log info only if unexpected folders detected

7. Return success
```

---

## Context Mirror to Vault

When Obsidian Vault is configured, the plugin MUST maintain a mirror copy of all user context data in the vault. This serves as a **secondary backup** and enables recovery when `~/.grow-pm/` is lost (e.g., during plugin update).

### Mirror folder structure

```
{vault}/{plugin_folder}/
├── _System/                          # Mirrored system files
│   ├── local-context.md              # Copy of ~/.grow-pm/local-context.md
│   └── .schema-version               # Copy of ~/.grow-pm/.schema-version
├── Knowledge/                        # Mirrored knowledge library
│   ├── library.md                    # Copy of ~/.grow-pm/knowledge-library/library.md
│   ├── categories.md                 # Copy of ~/.grow-pm/knowledge-library/categories.md
│   ├── trust-scores.yaml             # Copy of ~/.grow-pm/knowledge-library/trust-scores.yaml
│   └── sources/                      # Copy of ~/.grow-pm/knowledge-library/sources/*
│       ├── source-1.md
│       └── ...
└── ... (existing artifact folders)
```

### Sync triggers

Mirror sync MUST happen after:
1. **Any write to `~/.grow-pm/local-context.md`** — Plugin Configurator (Onboarding, Update, View, Enrichment)
2. **Any write to `~/.grow-pm/knowledge-library/`** — Knowledge Library skill (Add, Import, Manage, Verify)
3. **Migration completion** — after schema migration or legacy data migration
4. **Backup restore** — after restoring from backup
5. **User request** — explicit "sync to vault" command

### Sync algorithm

```
vault_mirror_sync(source_path, vault_config):

1. Resolve vault path and plugin folder
2. Ensure _System/ directory exists in vault
3. Ensure Knowledge/ directory exists in vault

4. For each file in mirror map (see persistent-storage.md VM-1):
   a. Read source file from ~/.grow-pm/
   b. If source exists:
      - Write to vault mirror location
      - Preserve file content exactly (no transformation)
   c. If source does NOT exist but vault copy exists:
      - Do NOT delete vault copy (it may be the only remaining copy)
      - Log warning: "Source file missing but vault copy preserved"

5. For knowledge-library/sources/:
   a. List all .md files in ~/.grow-pm/knowledge-library/sources/
   b. Copy each to {vault}/Knowledge/sources/
   c. Do NOT delete vault files that don't have a source counterpart
      (user may have manually added files to vault)

6. Write sync timestamp to {vault}/{plugin_folder}/_System/.last-sync
   Content: ISO timestamp + source version
```

### Recovery from vault

See **Vault Recovery Protocol (VR-1 through VR-3)** in `references/persistent-storage.md`. This protocol is the primary defense against data loss during plugin updates.

**Key principle:** The vault mirror is a **write-through replica** — every write to `~/.grow-pm/` is immediately followed by a write to the vault. During recovery, the vault → `~/.grow-pm/` direction is used.

---

## Related Documents

- **vault-schema.md** — Frontmatter schema, artifact types, folder structure, templates
- **local-context-protocol.md** — How skills read configuration and local context
- **persistent-storage.md** — Persistent storage protocol, backup, mirror, and recovery protocols
- **SKILL.md** — Individual skill documentation (includes Step 0.5 vault context integration)

---

**Version**: 1.1  
**Last Updated**: 2026-04-15
# Vault Protocol

## Overview

This document defines how every skill in the Grow Product Manager Plugin interacts with Obsidian Vault for persistent knowledge accumulation. All skills **SHOULD** follow this protocol, but Vault is **OPTIONAL** — if not configured, skills work normally without any vault functionality.

**Related documentation:**
- For Vault schema (frontmatter, types, tags): see `references/vault-schema.md`
- For local configuration reading: see `references/local-context-protocol.md`

---

## Vault Level Detection

Vault detection is executed during **Step 0** (after reading `local-context.md`). Detection establishes one of three operational levels:

### Levels

- **L0: No vault configured** → Skip all vault operations silently
- **L1: Vault path configured, file system access only** → Read/write `.md` files, search via glob + grep
- **L2: Vault path + Obsidian MCP available** → L1 + full-text search, Dataview, graph traversal

### Detection Algorithm

```
1. Read local-context.md section "Obsidian Vaults"
2. If section missing OR no vault paths found
   → return L0
3. For each vault in list:
   a. Check directory exists: stat(path)
   b. Check plugin folder exists: stat(path/{plugin_folder}/)
   c. If either fails → skip this vault
4. If valid vault(s) found AND MCP detection != "disabled"
   → try Obsidian MCP call (test_mcp_connection)
   → if responds successfully → L2
   → if no response or error → L1
5. Store vault_level and vault_configs in session context
6. If no valid vaults found → downgrade to L0
```

### Session Context Storage

After detection, store in session:
```
session.vault = {
  level: L0 | L1 | L2,
  vaults: [
    {
      path: string,
      product_binding: "product_key" | "all",
      mcp_available: boolean
    }
  ]
}
```

---

## Multi-Vault Resolution

The plugin supports multiple vaults with intelligent routing:

### When Saving

```
resolve_vault(product) → vault_config:
1. For each vault in vault_configs:
   a. If vault.product_binding == product → return vault
2. If no exact match:
   a. Find vault with product_binding == "all"
   b. If found → return it (default vault)
3. If no default vault:
   a. Return first vault in list (fallback)
4. If no vaults → return null (L0 behavior)
```

### When Searching

```
search_all_vaults(criteria):
1. For each vault in vault_configs:
   a. Execute search (L1 or L2) against vault
   b. Collect results with vault_path metadata
2. Merge results across vaults
3. Deduplicate by artifact path
4. Sort by relevance/date
5. Return merged result set
```

---

## Step 0.5 — Vault Context Search (OPTIONAL)

Vault context search is inserted between **Step 0** and **Step 1** of every skill execution. This optional step enriches the skill context with relevant knowledge from the vault.

### Precondition
If `vault_level == L0` → **skip silently**, continue to Step 1 normally.

### Algorithm

```
1. Determine relevant artifact types
   → Use SKILL_CONTEXT_MAP (see section below)
   → Interpret user's input for product/topic keywords

2. Build search criteria:
   - artifact_types: from SKILL_CONTEXT_MAP
   - product: from local-context or user input
   - tags: inferred from skill topic + user keywords
   - status: [active, draft]
   - sort: created DESC
   - limit: 10 results

3. Execute search:
   IF vault_level == L1:
     → file_search(criteria)
   ELSE IF vault_level == L2:
     → mcp_search(criteria)

4. Display results (if found):
   - Show max 5 in summary
   - Ask user: "Use as context? [Yes / Select specific / Skip]"

5. Handle user response:
   IF user selects "Yes" OR "Select specific":
     → read full content of selected artifacts
     → include in prompt context as "Vault Context"
   ELSE IF "Skip":
     → continue normally to Step 1

6. If no results found:
   → continue silently to Step 1
```

### SKILL_CONTEXT_MAP

Defines which artifact types are relevant to each skill:

| Skill | Relevant Types |
|-------|---|
| cjm-research | cjm-analysis, cjm-health-check, funnel-anomaly, ab-test-results, hypothesis |
| write-concept | competitive-analysis, market-research, ux-benchmark, hypothesis, decision, requirements |
| product-analysis | cjm-analysis, ab-test-results, metrics-review, post-release, hypothesis |
| brainstorm-features | cjm-analysis, competitive-analysis, ab-test-results, ux-benchmark, decision |
| requirements-creator | concept, hypothesis, competitive-analysis, decision, ab-test-results |
| meeting-processor | meeting-notes, decision, concept, requirements |
| product-research | competitive-analysis, market-research, ux-benchmark, knowledge-source |
| knowledge-library | knowledge-source |

---

## File Search (L1)

Detailed algorithm for searching vault via file system (no external tools required):

```
file_search(criteria: SearchCriteria) → [ArtifactSummary]:

1. Map artifact types to folders
   → Use TYPE_FOLDER_MAP from vault-schema.md

2. Build glob patterns:
   FOR each type in criteria.artifact_types:
     glob_pattern = "{vault_path}/artifacts/{type}/**/*.md"
     IF criteria.product specified:
       glob_pattern += "{vault_path}/artifacts/{type}/{product_slug}/**/*.md"

3. Find files:
   files = glob(glob_pattern, recursive=true)

4. Optimization - check MOC first:
   IF file exists: {vault_path}/dashboard/MOC-Dashboard.md
     → parse Recent Activity table
     → collect artifact paths from recent items (if within date range)
     → prioritize these files in next step

5. Parse each file:
   FOR each file in files:
     a. Open file
     b. Extract YAML frontmatter (up to closing ---)
     c. Extract ## Summary section (next 2-5 paragraphs)
     d. Parse frontmatter fields: type, product, tags, status, created

6. Filter against criteria:
   KEEP artifact IF:
     - artifact.type in criteria.artifact_types
     - artifact.status in criteria.status
     - artifact.product == criteria.product (if specified)
     - artifact.tags overlap with criteria.tags (if specified)

7. Sort and limit:
   - Sort by: created DESC
   - Keep first N results (default N=10)

8. Build summary:
   FOR each artifact:
     return {
       path: file_path,
       title: frontmatter.title,
       type: frontmatter.type,
       summary: extracted_summary,
       created: frontmatter.created,
       status: frontmatter.status
     }

9. Return results
```

---

## MCP Search (L2)

Enhancement over L1 using Obsidian MCP for richer search capabilities:

```
mcp_search(criteria: SearchCriteria) → [ArtifactSummary]:

1. Execute L1 file_search as baseline
   baseline_results = file_search(criteria)

2. Build MCP full-text search query:
   mcp_query = {
     text: criteria.tags + product keyword,
     path_filter: "{vault_path}/{plugin_folder}/",
     scope: "content + frontmatter"
   }

3. Execute MCP search (with timeout):
   TRY:
     mcp_results = mcp_full_text_search(mcp_query) TIMEOUT 3s
   CATCH timeout:
     → log info "MCP search timed out"
     → return baseline_results (graceful degradation)
   CATCH error:
     → log info "MCP unavailable"
     → return baseline_results

4. Merge results:
   merged = deduplicate(baseline_results + mcp_results)
   → by artifact file_path (canonical path)
   → keep highest relevance score if duplicated

5. Get backlinks for top-5:
   FOR each artifact in merged[0:5]:
     backlinks = mcp_get_backlinks(artifact.path)
     artifact.related_count = len(backlinks)

6. Re-sort by relevance + related_count
   Sort by: (relevance_score * 0.7) + (related_count * 0.3)

7. Return merged results
```

---

## Vault Save

Called after a skill completes its main work to persist the output artifact.

### Algorithm

```
vault_save(artifact, product, options):

1. Precondition checks:
   IF vault_level == L0 → return (skip silently)
   IF sync_mode == "off" → return (read-only, skip silently)
   IF sync_mode == "manual":
     → ask user: "Save to vault? [Yes / No]"
     → if No → return

2. Resolve target vault:
   target_vault = resolve_vault(product)
   IF null → log warning, return

3. Build file path:
   type_folder = TYPE_FOLDER_MAP[artifact.type]
   product_slug = slugify(product)
   filename = "{artifact_type}-{topic_slug}-{YYYY-MM-DD}.md"
     Examples:
       - competitive-checkout-flow-2026-04-14.md
       - cjm-health-check-2026-04-14.md
       - hypothesis-ai-personalization-2026-04-14.md
   
   file_path = {target_vault.path}/artifacts/{type_folder}/{product_slug}/{filename}

4. Create directory structure:
   mkdir -p {file_path_parent_dir}

5. Build frontmatter (see vault-schema.md for schema):
   frontmatter = {
     type: artifact.type,
     product: product,
     title: artifact.title,
     tags: artifact.tags,
     status: "active",
     created: today ISO8601,
     last_updated: today ISO8601,
     related: [],
     linked_hypothesis: null (if applicable),
     test_result: null (if applicable),
     ...
   }

6. Build content:
   REQUIRE: ## Summary section at start
     - 2-5 sentences
     - Captures key findings/output
     - Written for someone discovering vault artifact cold
   
   content = "## Summary\n\n{summary_text}\n\n{full_artifact_content}"

7. Find and link related artifacts (if auto-link enabled):
   FOR each related_type in REVERSE_CONTEXT_MAP[artifact.type]:
     search_results = file_search({
       artifact_types: [related_type],
       product: product,
       status: [active],
       limit: 5
     })
     FOR each result in search_results:
       - Add result.path to frontmatter.related[]
       - Read result file
       - Add [[{current_artifact_path}]] to result.related[]
       - Write result file back

8. Write artifact file:
   write_file(file_path, frontmatter + content)

9. Update MOC indexes (if auto-update enabled):
   - update_dashboard_moc(artifact, target_vault)
   - update_product_moc(artifact, target_vault)
   - update_timeline_moc(artifact, target_vault)

10. Inform user:
    log: "Saved to Vault: {relative_path}"
```

### Special Cases

**Hypothesis Lifecycle**: If skill is `product-analysis` saving `ab-test-results` with linked hypothesis:
- See [Hypothesis Lifecycle Updates](#hypothesis-lifecycle-updates) section

**Duplicate Prevention**: If file already exists:
- Append incrementing suffix: `-2`, `-3`, etc.
- Example: `competitive-checkout-flow-2026-04-14-2.md`

---

## Vault Initialization

Called once by Plugin Configurator when Vault is first connected.

### Algorithm

```
vault_init(vault_path, plugin_folder_name):

1. Create complete folder structure:
   - artifacts/
     - competitive-analysis/
     - cjm-analysis/
     - ab-test-results/
     - decision/
     - hypothesis/
     - meeting-notes/
     - knowledge-source/
     - metrics-review/
     - post-release/
     - ux-benchmark/
     - market-research/
     - concept/
     - requirements/
     - cjm-health-check/
     - funnel-anomaly/
   
   - dashboard/
   - templates/
   - archive/

2. Create product subfolders:
   FOR each product in local-context.products:
     product_slug = slugify(product)
     FOR each artifact type:
       mkdir -p {vault_path}/artifacts/{type}/{product_slug}/

3. Write template files to templates/ folder:
   - template-competitive-analysis.md
   - template-cjm-analysis.md
   - template-hypothesis.md
   - template-decision.md
   - template-meeting-notes.md
   (Use templates from vault-schema.md)

4. Create initial Dashboard MOC:
   Write: {vault_path}/dashboard/MOC-Dashboard.md
     - Section: Recent Activity (empty table)
     - Section: Product Stats (table with product names)
     - Section: Quick Links (to Templates, Archive, Timeline)

5. Copy local-context as reference:
   Copy local-context.md → {vault_path}/REFERENCE-local-context.md
   Mark as read-only

6. Migrate existing knowledge-library:
   IF knowledge-library/ folder exists in vault:
     FOR each .md file:
       - Move to artifacts/knowledge-source/{product}/
       - Update frontmatter with type: knowledge-source
       - Add to MOC Dashboard

7. Create schema version file:
   Write: {vault_path}/.vault-schema-version
   Content: {current_version} (e.g., "1.0")

8. Return success
```

---

## MOC Update Protocol

MOC (Map of Contents) files provide navigation and overview of vault artifacts. They are updated automatically by vault_save.

### Dashboard.md Update

```
update_dashboard_moc(artifact, vault):

1. Open: {vault_path}/dashboard/MOC-Dashboard.md

2. Update Recent Activity table:
   - Prepend new artifact entry to table (at top)
   - Format: | date | type | product | title_link |
   - Example: | 2026-04-14 | hypothesis | MyApp | [[hypothesis-ai-personalization-2026-04-14]] |
   - Keep last 20 entries only (prune old ones)

3. Update product stats:
   - Find product row in "Product Stats" section
   - Increment artifact_count
   - Update last_activity date

4. Update quick links:
   - Add link to recently updated product MOC if new

5. Write file back
```

### Product MOC Update

```
update_product_moc(artifact, vault):

1. Determine MOC path:
   product_slug = slugify(product)
   moc_path = {vault_path}/dashboard/MOC-{product_slug}.md

2. If MOC doesn't exist:
   → Create new MOC with standard sections (see below)

3. Update based on artifact type:
   
   IF artifact.type == cjm-analysis:
     → Update "CJM Artifacts" section
     → Add entry to recent CJM analyses
   
   IF artifact.type == hypothesis:
     → Update "Hypothesis Pipeline" section
     → Add entry under status (active/validated/rejected)
   
   IF artifact.type == ab-test-results:
     → Update "Test Results" section
     → Link to hypothesis (if applicable)
   
   IF artifact.type == decision:
     → Update "Recent Decisions" section
     → Prepend to decision list

4. Write file back

### MOC Structure (for new MOC creation):

---
type: moc
product: {product_name}
created: {today}
---

## {Product Name} Map of Contents

### Active Work
| Type | Latest | Status |
|------|--------|--------|

### CJM Health
- Latest health check: [none]

### Hypothesis Pipeline
- Active: [none]
- Validated: [none]
- Rejected: [none]

### Recent Decisions
[none]

### Test Results
[none]

### Related MOCs
- [[MOC-Dashboard]]
```

### Timeline.md Update

```
update_timeline_moc(artifact, vault):

1. Open or create: {vault_path}/dashboard/Timeline.md

2. Append chronological entry:
   Format: {YYYY-MM-DD} | {type} | {product} | {title_link}
   Example: 2026-04-14 | hypothesis | MyApp | [[hypothesis-ai-personalization-2026-04-14]]

3. Keep entries in reverse chronological order (newest first)

4. Write file back
```

---

## Backlink Management

Backlinking creates explicit relationship between artifacts in the vault.

### Algorithm

```
add_backlinks(source_artifact_path, target_artifact_paths):

FOR each target_path in target_artifact_paths:
  1. Read target file
  2. Parse frontmatter
  3. Check if source_path already in related[] → if yes, skip
  4. Add source_path to related[] in frontmatter
  5. Rewrite target file with updated frontmatter
  6. Store relative wikilink path (from plugin folder)
     Format: [[CJM/MyApp/health-checks/2026-04-14]]
     (no .md extension, relative from vault plugin folder root)
```

### Wikilink Format

- **Format**: `[[relative_path_from_plugin_root]]`
- **No file extension**: `.md` is omitted
- **Example paths**:
  - `[[competitive-analysis/MyApp/competitive-checkout-flow-2026-04-14]]`
  - `[[hypothesis/MyApp/ai-personalization-2026-04-14]]`
  - `[[dashboard/MOC-MyApp]]`

---

## Hypothesis Lifecycle Updates

Special handling for hypothesis artifacts when linked test results are saved.

### Algorithm

```
update_hypothesis_lifecycle(hypothesis_artifact_path, test_result_artifact):

1. Read hypothesis file
2. Parse frontmatter
3. Read test_result frontmatter:
   - Get test_result.winner_id or test_result.loser_id
   - If test_result.winner_id == hypothesis.id:
       hypothesis.hypothesis_status = "validated"
       hypothesis.confidence = 0.95
   - Else if test_result.loser_id == hypothesis.id:
       hypothesis.hypothesis_status = "rejected"
       hypothesis.confidence = 0.2
   - Else:
       hypothesis.hypothesis_status = "inconclusive"

4. Update hypothesis frontmatter:
   - hypothesis_status: updated (see above)
   - test_result: {test_result_artifact_path}
   - validated_by: {test_result artifact}
   - last_reviewed: {today ISO8601}

5. Write hypothesis file back

6. Update hypothesis status in Product MOC
```

---

## Error Handling

All vault errors are **NON-BLOCKING**. The main skill workflow must never fail due to vault issues. Graceful degradation applies throughout.

### Error Handling Table

| Scenario | Behavior |
|----------|----------|
| Vault path doesn't exist | Log warning, fallback to L0 (no vault) |
| No write permissions on vault | Log warning, fallback to L0 |
| MCP unavailable (connection fails) | Log info, fallback to L1 (file search only) |
| MCP timeout (>3s on any call) | Abort MCP call, use L1 results |
| Frontmatter parse error in artifact | Log error with file path, skip broken file, continue search |
| File write error (disk full, permissions) | Log error, inform user "Could not save to vault", skip vault save |
| MOC update fails | Log warning, artifact still saved (MOC update non-critical) |
| Duplicate filename on save | Append suffix: `-2`, `-3`, etc., retry write |
| Directory creation fails | Log error, fallback to L0 |
| Backlink write fails | Log warning, continue (non-critical) |
| Multi-vault merge fails | Use single vault results, continue |

### User Notification

Vault errors are communicated to user only if they block the skill's primary output:

```
IF artifact saved successfully:
  → Show: "Saved to Vault: {relative_path}"
  
IF vault save failed but artifact generated:
  → Show warning: "Could not save to vault (reason). Your artifact is ready above."
  
IF MCP degraded to L1:
  → Silent (no user notification, automatic graceful downgrade)
```

---

## Vault Structure Check

Performed on each skill start as part of **Step 0** vault detection.

### Algorithm

```
vault_structure_check(vault_path, plugin_folder):

1. Check vault root directory:
   IF NOT exists(vault_path):
     → log warning "Vault path does not exist"
     → fallback to L0
     → return

2. Check plugin folder:
   IF NOT exists({vault_path}/{plugin_folder}):
     → create directory

3. For each expected artifact type folder:
   IF NOT exists({vault_path}/artifacts/{type}):
     → create directory silently

4. For each product in local-context:
   FOR each artifact type:
     IF NOT exists({vault_path}/artifacts/{type}/{product_slug}):
       → create directory silently

5. Check dashboard folder:
   IF NOT exists({vault_path}/dashboard):
     → create directory

6. Do NOT delete unexpected files/folders:
   → User may have created custom structure
   → Log info only if unexpected folders detected

7. Return success
```

---

## Related Documents

- **vault-schema.md** — Frontmatter schema, artifact types, folder structure, templates
- **local-context-protocol.md** — How skills read configuration and local context
- **SKILL.md** — Individual skill documentation (includes Step 0.5 vault context integration)

---

**Version**: 1.0  
**Last Updated**: 2026-04-14
