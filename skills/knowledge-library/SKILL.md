---
name: knowledge-library
version: 0.7.0
description: Manage a local library of curated knowledge sources (articles, benchmarks, research) with trust scoring and multi-mode search, AND the team-language contour — glossary of team terms with synonyms and a writing style profile. Use for "manage sources", "add to library", "search knowledge", "import sources", "show library", "add this article", "what sources do we have on [topic]" — and for "build a glossary", "add a term", "how do we call X", "check terminology", "learn our writing style", or when another skill needs enrichment search or a terminology lint. Українською — "керувати джерелами", "додати в бібліотеку", "пошук у знаннях", "показати бібліотеку", "додай цю статтю", "які джерела маємо по темі", "збери глосарій", "додай термін", "як ми називаємо…", "перевір термінологію", "навчись нашого стилю". Do NOT use for artifact templates — use template-library.
---

# Knowledge Library

Manage a local library of curated knowledge sources with categorization, trust scoring, and multi-mode search. Acts as a knowledge layer that other skills query during enrichment.

This is a **service skill** — it provides search capabilities to other skills (primarily `cjm-research`) and also supports direct user management of the library.

## Prerequisites

Before any operation, follow these shared references:
- **`references/local-context-protocol.md`** — read `local-context.md` for Knowledge Library configuration
- **`references/persistent-storage.md`** — persistent storage protocol (`~/.grow-pm/`)
- **`references/integration-strategy.md`** — MCP → Registry → Browser fallback chain
- **`references/data-policy.md`** — confidentiality rules (internal sources stay internal)
- **`references/template-protocol.md`** — when the user asks about templates, delegate to `template-library`

## Routing: knowledge-library vs template-library

Starting with v1.9.0, the plugin has two sibling service skills:

- **`knowledge-library`** (this skill) — curated **source material** (articles, benchmarks, research insights, internal docs)
- **`template-library`** — **artifact templates** that shape generated outputs (concept, requirements, research, CJM, epic, task, presentation)

If the user says anything about **templates** ("templates", "template for requirements"), delegate to `template-library`. If the user says anything about **sources / knowledge** ("sources", "knowledge", "add this article"), stay here. Since v0.7.0 this skill also owns **terms / team language** ("глосарій", "додай термін", "як ми називаємо", "перевір термінологію", "стиль команди") — the glossary + style contour, also here.

When ambiguous (e.g. "add this") ask one question via `AskUserQuestion`:
> "Is this a **source** (article / research / benchmark), a **term** for the team glossary, or a **template** for the Template Library?"

## Library Storage

The library is stored in the user's **persistent home directory** to survive plugin reinstalls:

```
~/.grow-pm/knowledge-library/
├── library.md            # Master index — markdown table of all sources
├── categories.md         # Category definitions (default + custom)
├── trust-scores.yaml     # Trust scores and metadata for auto-calculation
├── sources/              # Individual source detail files (for rich insights)
│   ├── baymard-checkout-flow.md
│   └── ...
├── health-checks/        # Stored CJM health-check snapshots
│   ├── 2026-04-07.md
│   └── ...
├── glossary/             # Team-language contour (v0.7.0): terms + phrases
│   ├── _org.yaml
│   └── {product_id}.yaml
└── style/                # Style profiles (v0.7.0)
    ├── _org.md
    └── {product_id}.md
```

**Legacy location:** `workspace/knowledge-library/`. If data is found here but not in `~/.grow-pm/`, offer migration (see `references/persistent-storage.md`).

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
| **Glossary Build** (+ Style Build) | User: "збери глосарій", "build a glossary", "навчись нашого стилю"; Gate 3 first-run opt-in | Mine term candidates from Confluence/Jira/Fireflies/documents, confirm in batches, build the style profile from reference texts |
| **Glossary Manage** | User: "додай термін", "як ми називаємо…", "покажи глосарій", "add a term" | CRUD terms, phrases, and style rules; answer "how do we call X" |
| **Glossary Lint** | Service call from `artifact-style-gate.md` Gate 3; user: "перевір термінологію" | Scan a draft: avoid→canonical replacements, style deviations, glossary candidates |

If the user says "template" or asks about generated artifact structure — delegate to `template-library` immediately. Do NOT add templates as "sources".

---

## Mode workflows

The eight mode workflows — Add (A-1..A-6), Search local (S-1..S-3), Search Confluence (SC-1..SC-5), Search Google Drive (GD-1..GD-3), Search Baymard (B-1..B-4), Manage (M-1..M-3), Import (I-1..I-4), Verify (V-1..V-4) — live in `references/library-workflows.md` (skill-local). Read ONLY the workflow for the active mode.

Trust score calculation (formula, type base scores, freshness, citation bonus, user override, monthly re-evaluation), the default category taxonomy, and the Configurator-invoked onboarding (KL-1..KL-6) live in `references/trust-and-categories.md` (skill-local). Add/Import/Verify workflows require the trust section.

The **team-language contour** — Glossary Build (GB-1..GB-6), Style Build (SB-1..SB-4), Glossary Manage (GM), Glossary Lint (GL-1..GL-3), storage schemas, and the Terminology & Style config — lives in `references/glossary-workflows.md` (skill-local). Read ONLY for the glossary/style modes. Key rule: read Atlassian MCP **sequentially** when mining.

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
- When called from `product-research` or `brainstorm-features` → only when user explicitly requested or approved
- When the user interacts directly → perform the requested operation

### Proposing enrichment to other skills

When `product-research` or `brainstorm-features` are running and Knowledge Library is initialized:
1. Check if library contains sources relevant to the current topic
2. If relevant sources exist (>= 3 sources matching the topic), inform the calling skill
3. The calling skill then proposes to the user: "Knowledge Library has [N] sources on [topic]. Use them for enrichment?"
4. Only proceed with library search if user confirms

### As the Gate 3 lint service

`references/artifact-style-gate.md` (Gate 3b) calls Glossary Lint with a draft text. Return the structured payload `{replacements, style_findings, candidates}` (see `references/glossary-workflows.md` → GL-3); the calling gate applies it per `lint_mode`. No glossary configured → return "lint skipped" instantly, never block the caller.

### Sibling skill: `template-library`

`template-library` handles artifact templates (concept, requirements, research, CJM, epic, task, presentation). This skill handles source material. When routing is ambiguous, ask one clarifying question (see Routing section at the top).

---

## Vault Mirror Sync (Mandatory when Vault configured)

After **every write operation** to `~/.grow-pm/knowledge-library/` (Add, Import, Manage, Verify modes), the Knowledge Library MUST sync changes to the Obsidian Vault mirror. This is the primary defense against data loss during plugin updates.

### Post-write sync procedure

```
After writing to ~/.grow-pm/knowledge-library/:

1. Check if Obsidian Vault is configured (local-context.md → Obsidian Vaults section)
   → NOT configured: skip sync silently
   → Configured: proceed

2. Resolve target vault (use Multi-Vault Resolution from vault-protocol.md)

3. Sync changed files:
   - library.md → {vault}/{plugin_folder}/Knowledge/library.md
   - categories.md → {vault}/{plugin_folder}/Knowledge/categories.md
   - trust-scores.yaml → {vault}/{plugin_folder}/Knowledge/trust-scores.yaml
   - sources/{new-or-changed}.md → {vault}/{plugin_folder}/Knowledge/sources/
   - glossary/{changed}.yaml → {vault}/{plugin_folder}/Knowledge/glossary/
   - style/{changed}.md → {vault}/{plugin_folder}/Knowledge/style/

4. Do NOT delete vault files that don't have source counterpart
   (vault may contain user's manual additions)

5. Update {vault}/{plugin_folder}/_System/.last-sync timestamp

6. Log (silently, don't inform user unless error):
   "Knowledge Library synced to vault: [N] files updated"
```

### Recovery check at skill start

At the beginning of Knowledge Library skill execution (after Step 0 context load):

```
1. Check ~/.grow-pm/knowledge-library/library.md exists
   → EXISTS: proceed normally
   → MISSING: check vault mirror

2. If vault mirror has Knowledge/library.md:
   → Inform user: "Knowledge Library data is missing from ~/.grow-pm/ but found in Obsidian Vault. Restoring..."
   → Copy vault Knowledge/ files → ~/.grow-pm/knowledge-library/
   → Proceed normally

3. If vault mirror also empty:
   → Inform user: "Knowledge Library is not initialized. Would you like to set it up?"
   → Proceed to onboarding workflow
```

---

## Quality Standards

- Never delete sources without user confirmation
- Always show auto-categorization for user review before saving
- Preserve user trust overrides during verification/recalculation
- Use the user's preferred language for all communications (from `local-context.md`)
- Follow `data-policy.md` — internal source content (Confluence, GDrive) is confidential and must not be sent to external LLMs
- When Baymard requires login — always inform the user, never attempt to bypass authentication
- **Always sync to Obsidian Vault after write operations** (when Vault is configured)
- Route template-related requests to `template-library` (see Routing section)
- Glossary authority is the user: only user-confirmed entries get `status: approved`; mined-but-unconfirmed stay `candidate` and never drive auto-replacements

## Additional Resources

- **`references/library-workflows.md`** (skill-local) — all eight mode workflows in full
- **`references/trust-and-categories.md`** (skill-local) — trust formula, category taxonomy, KL onboarding
- **`references/glossary-workflows.md`** (skill-local) — team-language contour: glossary + style profile workflows (GB/SB/GM/GL), schemas, config

- **`references/persistent-storage.md`** — persistent storage protocol (`~/.grow-pm/`), mirror, backup, recovery
- **`references/vault-protocol.md`** — Vault mirror sync, context mirror, recovery protocol
- **`references/cjm-protocol.md`** — anomaly severity, funnel impact formulas, health score
- **`references/funnel-templates.md`** — standard funnel stage templates
- **`references/integration-strategy.md`** — MCP → Registry → Browser fallback chain
- **`references/data-policy.md`** — data confidentiality rules
- **`references/self-improvement.md`** — self-improvement protocol
- **`references/template-protocol.md`** — artifact template protocol (sibling skill `template-library`)
