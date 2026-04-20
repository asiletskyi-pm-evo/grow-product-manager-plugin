# Template Protocol

This document defines how skills locate, rank, request, and render artifact templates. **All skills that produce user-facing artifacts MUST follow this protocol.**

The template system gives users a way to shape the structure of generated artifacts (concepts, requirements, research reports, CJM reports, epics, tasks, presentations) to match their team's conventions. Three scopes coexist:

1. **built-in** — ships with the plugin, read-only
2. **user-global** — user's own templates, applied to any product
3. **product-specific** — user templates scoped to a product from `local-context.md`

The registry at `{storage_root}/Templates/_registry.json` is the single source of truth. Built-in templates live under `{plugin-root}/templates/built-in/` and are referenced by `builtin://` URIs.

---

## Template format

A template is a Markdown file with YAML frontmatter and a body that may include variable substitution, conditional blocks, loops, and language-tagged sections.

### Frontmatter schema

```yaml
---
template_id: requirements-ab-test-v1     # unique across the registry
schema_version: 1                        # format version
name: "A/B Test Requirements"            # or map: {uk: "...", en: "..."}
artifact_type: requirements              # concept | requirements | research
                                         # | cjm | epic | task | presentation
                                         # | partial
subtype: ab-test                         # optional specialization
scope: user-global                       # built-in | user-global | product
products: []                             # [] = all products; else list
default_language: uk
available_languages: [uk, en]
version: "1.0.0"
author: "Andrii"
created: 2026-04-17
updated: 2026-04-17
tags: [ab-test, growth]
description: "A/B test requirements focused on checkout"
status: active                           # active | draft | deprecated
min_plugin_version: "1.9.0"
variables:
  - name: feature_name
    type: string                         # string | text | list | boolean
                                         # | number | date | reference | enum
    required: true
    label: "Feature name"                # or map {uk, en}
    hint: "Short — what we're testing"   # or map {uk, en}
  - name: has_baseline
    type: boolean
    default: false
  - name: baseline_source
    type: reference
    required: false
sections_include: [success-metrics-block]  # includes from _partials/
---
```

### Body syntax

Light Handlebars-style syntax, Obsidian-friendly:

| Construct | Example | Meaning |
|-----------|---------|---------|
| Variable | `{{feature_name}}` | Substitute variable |
| Conditional | `{{#if has_baseline}} … {{/if}}` | Render only if truthy |
| Loop | `{{#each success_metrics}} - {{this}} {{/each}}` | Iterate over list |
| Partial | `{{> success-metrics-block}}` | Include partial from `_partials/` |
| Lang block (HTML) | `<!-- lang:uk --> … <!-- /lang:uk -->` | Multilingual body block |
| Lang block (fenced) | `::: lang uk` … `:::` | Alt syntax, also supported |

Unknown directives are ignored with a warning. Missing partials become `<!-- partial {name} not found -->` comments.

### Multilingual

A single `.md` file can carry multiple language variants. If the body contains any `lang:xx` block, multilingual mode is active: the renderer extracts the block that matches the request language. If the body has no `lang:xx` blocks, the whole body is the default-language content.

Frontmatter string fields (`name`, `description`, `variables[*].label`, `variables[*].hint`) can be either scalars (one value for all languages) or maps `lang -> string`.

---

## Resolution protocol (Step T-0 … T-5)

Standard flow any consumer skill runs before writing the artifact.

### Step T-0. Declare context

The skill declares:

- `artifact_type` (required) — e.g. `requirements`
- `subtype` (optional) — e.g. `ab-test`
- `product_id` (optional) — from `local-context.md` active product
- `language` (required) — from `local-context.md` or explicit request

### Step T-1. Load registry

Read `{storage_root}/Templates/_registry.json`. Use `references/persistent-storage.md` resolution to locate `storage_root`. If the registry is missing or malformed, run `template-library: rebuild-registry` on the fly (walk `Templates/` and rebuild) before continuing.

Filter candidates: `artifact_type` matches AND `status=active` AND `min_plugin_version ≤ current_plugin_version`.

### Step T-2. Score and rank

Every candidate gets a score:

| Criterion | Bonus |
|-----------|-------|
| `scope=product` + `product_id ∈ products` | +5 |
| `scope=user-global` | +3 |
| `scope=built-in` | +1 |
| Exact `subtype` match | +3 |
| Both `subtype=null` (request and candidate) | +1 |
| Request `language ∈ available_languages` | +2 |
| `default_language == request language` | +1 |
| `usage_count > 0` | +min(usage_count/5, 2) |

Sort descending: first by scope (product > user-global > built-in), then by total score, then by `updated` (newer first).

### Step T-3. Decide

- **Zero candidates** → fall back to `builtin://{artifact_type}/default-v1.md`. If the built-in default is also missing, warn the user and proceed without a template (skill renders its own structure).
- **Exactly one candidate** → use it silently. Append `<!-- template: {template_id} -->` at the end of the rendered artifact.
- **Multiple candidates** → ask the user via `AskUserQuestion`:
  > "I found {N} templates for {artifact_type}. Which one should I use?"
  >  1. {top.name} — {scope}, updated {date}
  >  2. {second.name} — {scope}, updated {date}
  >  3. Do not use a template (free form)

Behaviour is configurable via `local-context.md → templates.preference`:

| Value | Behaviour |
|-------|-----------|
| `auto` | Always use top-ranked silently |
| `always_ask` | Always ask, even with one candidate |
| `smart` (default) | Auto when top beats #2 by ≥3 points, otherwise ask |

### Step T-4. Collect variables

Parse `variables:` from the chosen template's frontmatter. For each required variable not already in the skill's context, ask the user via `AskUserQuestion`, batched by 1–4 variables per question, with type-aware UI:

- `string` / `text` → text input
- `list` → multi-line with one item per line (or multiSelect when `options` is provided)
- `boolean` → Yes / No options
- `enum` → options list from `options`
- `reference` → resolve against user vault (show matching Obsidian notes)
- `number`, `date` → typed input

Optional variables may be pre-populated or left unset.

### Step T-5. Render and record

1. Substitute variables in the body.
2. Resolve the language block (match `request.language` → else `default_language` → else first available, with warning).
3. Expand `{{#if}}`, `{{#each}}`, `{{> partial}}`.
4. Write the rendered artifact via `references/vault-protocol.md` to the vault (if configured) or to workspace.
5. Append `<!-- template: {template_id} version: {version} -->` at the end.
6. Increment `usage_count` and update `last_used` in the registry.
7. Append one line to `Templates/_System/usage.log`:
   `[2026-04-17T12:34:56Z] {template_id} → {output_path}`

---

## Skill integration pattern

Every consumer skill that produces artifacts inserts the following block between its Step 0 (config / vault context) and Step 1 (actual work):

```
## Step T — Template resolution

Follow `references/template-protocol.md`.

Declare:
- artifact_type: {e.g. requirements}
- subtype: {inferred from user input, e.g. ab-test, bugfix, default}
- product_id: {from local-context.md active product}
- language: {from local-context.md, or user's explicit choice}

Run Steps T-1 → T-5. The output of T-5 is the rendered artifact (or the skill's internal fallback structure if no template applied).

If the user explicitly says "do not use a template", skip to Step 1 with the skill's internal structure.
```

Skills MUST NOT reimplement template search logic. All ranking / ask / render logic lives in the `template-library` skill's helper routines referenced via this protocol.

---

## Edge cases

- **Duplicate `template_id`.** Registry MUST NOT contain duplicates. `template-library: validate` detects and prompts for rename or archive.
- **Missing partial.** Replaced by `<!-- partial {name} not found -->`, logged as a warning, rendering continues.
- **`min_plugin_version` > current.** Hidden from resolution. `template-library: list` marks it with a warning.
- **Language missing in selected template.** Fall back to `default_language`, warn the user.
- **Registry schema version older than current plugin.** `template-library: rebuild-registry` is invoked; migration adds new fields with defaults.
- **`storage_root` unreachable.** Fall back to `builtin://` via the registry's seed file embedded in the plugin.
- **User edits built-in path directly.** Prevented by readonly flag; if detected, show a clone flow ("Copy to user-global and edit?").

---

## Registry schema

```json
{
  "schema_version": "1.0.0",
  "updated": "2026-04-17T12:00:00Z",
  "templates": [
    {
      "template_id": "requirements-ab-test-v1",
      "artifact_type": "requirements",
      "subtype": "ab-test",
      "scope": "user-global",
      "products": [],
      "default_language": "uk",
      "available_languages": ["uk", "en"],
      "path": "user-global/requirements/ab-test-v1.md",
      "status": "active",
      "version": "1.0.0",
      "tags": ["ab-test", "growth"],
      "name": {
        "en": "A/B Test Requirements"
      },
      "description": "A/B test requirements focused on checkout",
      "updated": "2026-04-17",
      "usage_count": 0,
      "last_used": null
    },
    {
      "template_id": "concept-builtin-default",
      "artifact_type": "concept",
      "subtype": null,
      "scope": "built-in",
      "products": [],
      "default_language": "uk",
      "available_languages": ["uk", "en"],
      "path": "builtin://concept/default-v1.md",
      "status": "active",
      "version": "1.0.0",
      "tags": [],
      "name": "Default Concept",
      "description": "Standard PRD / concept template"
    }
  ]
}
```

`path` uses either a relative path from `Templates/` (for user scopes) or a `builtin://` URI (for plugin-shipped templates). The `builtin://` URI resolves to `{plugin-root}/templates/built-in/{rest-of-path}`.

---

## Configuration in `local-context.md`

A new section controls template behavior:

```yaml
## Templates

templates:
  preference: smart            # auto | always_ask | smart
  default_language: uk
  favorite_templates: []       # list of template_id that rise to the top
  auto_save_to_vault: true
```

`plugin-configurator` writes this section during Step O-T of onboarding; users can change it via Update mode.

---

## Backup invariants

Templates are user data. They MUST survive plugin lifecycle events. See `references/persistent-storage.md` for the general contract. Template-specific rules:

- Automatic per-template archive: before `update` or `delete`, copy current file to `Templates/_archive/{template_id}/v{old_version}-{YYYY-MM-DD-HHmm}.md`. Keep the last 10 per template_id.
- Pack backup: before `rebuild-registry`, mass `import` (>5 files), schema migration, or "start fresh" during onboarding, snapshot the entire `Templates/` folder to `{storage_root}/backups/templates-{YYYY-MM-DD-HHmm}-{trigger}/`. Keep the last 5.
- Manual backup / restore: `template-library: backup` and `template-library: restore --from {name}`.
- Recovery: if `Templates/` is missing at the pointer-resolved path, run legacy-location scan (`~/.grow-pm/template-library/`, workspace/outputs, known vaults) before creating an empty structure.

---

## References

- `references/persistent-storage.md` — storage pointer, vault vs custom mode, recovery
- `references/vault-protocol.md` — writing artifacts into Obsidian vault
- `references/local-context-protocol.md` — reading active product, language, preferences
- `skills/template-library/SKILL.md` — CRUD actions, wizards, helper routines
- `skills/plugin-configurator/SKILL.md` — Step O-T onboarding flow
