---
name: template-library
version: 0.1.0
description: Manage artifact templates (concepts, requirements, research, CJM, epics, tasks, presentations) — create, clone, update, delete, import, export, validate. Use when the user asks to "manage templates", "add a template", "create a template", "edit a template", "import templates from a folder", "show templates", "backup templates", or when another skill needs to render an artifact with Step T of `references/template-protocol.md`. Also triggers on "shablone", "шаблон", "темплейт".
---

# Template Library

Manage the plugin's template library — the set of templates that skills use to produce user-facing artifacts (concepts, requirements, research reports, CJM reports, epics, tasks, presentations).

Three scopes coexist:

1. **built-in** — ships with the plugin, read-only
2. **user-global** — user's own templates, applied to any product
3. **product-specific** — user templates scoped to a product from `local-context.md`

This is a **service skill** — it also exposes helper routines (resolve, render) that other skills invoke via `references/template-protocol.md`.

## Prerequisites

Before any operation, follow these shared references:

- **`references/local-context-protocol.md`** — read `local-context.md` for active product, language, `templates.preference`, `templates.favorite_templates`
- **`references/persistent-storage.md`** — locate `{storage_root}/Templates/` via the storage pointer; handle vault vs custom mode
- **`references/template-protocol.md`** — template format, resolution protocol, registry schema
- **`references/vault-protocol.md`** — write rendered artifacts into the vault with YAML frontmatter and wikilinks
- **`references/data-policy.md`** — confidentiality rules for template body content

## Actions

The skill dispatches on the user's request into one of 11 actions. If ambiguous, ask via `AskUserQuestion`.

| Action | Trigger phrases | Purpose |
|--------|-----------------|---------|
| `list` | "show templates", "list templates", "what templates do we have" | Print the registry table with filters |
| `show` | "show template X", "open template X" | Full content + metadata for one template |
| `add` | "add a template", "create a template", "new template" | Wizard: artifact_type → scope → base → edit |
| `clone` | "clone template X", "copy template X" | Copy built-in / user-global into new user scope |
| `update` | "update template X", "edit template X" | Edit frontmatter and/or body; auto-archive old version |
| `delete` | "delete template X", "remove template X" | Soft delete: move to `_archive/deleted/` |
| `restore` | "restore template X", "undelete X" | From `_archive/deleted/` back to active |
| `import` | "import templates from {path}" | Scan a folder, validate, add to registry |
| `export` | "export templates", "backup templates to a file" | Package into a `.zip` with manifest |
| `validate` | "validate templates", "check templates" | Re-read all files, rebuild registry, detect issues |
| `rebuild-registry` | "rebuild template registry", "fix template registry" | Walk `Templates/` and regenerate `_registry.json` |
| `backup` / `restore --from` | "backup templates", "restore templates from {name}" | Manual snapshot / rollback |

## Wizard: `add`

1. **Artifact type** — via `AskUserQuestion`:
   - `concept`, `requirements`, `research`, `cjm`, `epic`, `task`, `presentation`, `partial`
2. **Scope** — via `AskUserQuestion`:
   - `user-global` (all products)
   - `product` (pick one from `local-context.md` products list)
3. **Base** — via `AskUserQuestion`:
   - Clone a built-in template (pick one)
   - Clone an existing user template (pick one)
   - Start blank (use minimal frontmatter seed)
4. **Languages** — via `AskUserQuestion` (multiSelect):
   - Default from `local-context.locales` (e.g. `[uk, en]`)
   - Each chosen language seeds a `<!-- lang:xx --> … <!-- /lang:xx -->` block in the body
5. **Template identity** — via `AskUserQuestion` or free text:
   - `template_id` (slug) — auto-suggest from `{artifact_type}-{subtype}-v1`
   - `name` (per-language or single)
   - `description`
   - `subtype` (optional, free text)
   - `tags` (comma-separated)
6. **Draft file** — write to `Templates/{scope}/{artifact_type}/{slug}-draft.md`, tell the user the path, open-hint for Obsidian if vault mode.
7. **Done signal** — `AskUserQuestion`: "I'll wait. Let me know when done editing."
8. **Validate** — parse YAML, check required frontmatter keys, scan body for balanced `lang:xx` blocks, missing partial references, unknown variables.
9. **Commit** — rename `{slug}-draft.md` → `{slug}.md`, add registry entry, set `created`/`updated`, set `status=active`.
10. **Confirmation** — show user the registry delta and the new file path.

## Wizard: `add-language` (extend existing template to a new language)

1. Pick an existing template (via registry filter).
2. `AskUserQuestion`: "Which language to add?"
3. Read the current template body.
4. Create a new `<!-- lang:{new_lang} -->` block seeded from the body of the existing `default_language` block (user must translate).
5. Update frontmatter: append to `available_languages`.
6. If `name`/`description`/`variables.*.label` are scalars, convert them to maps with the new language set to the same value (user can translate later).
7. Archive old file version before saving.
8. Tell the user what was added and prompt them to translate.

## Wizard: `import`

1. `AskUserQuestion`: "Path to folder with templates?"
2. Scan `*.md` in the folder.
3. For each file:
   - Parse frontmatter. If missing, try to infer from filename + ask user.
   - Check for `template_id` collision with registry. If collision → ask: rename / skip / replace (with archive).
   - Validate required fields.
4. Present summary to user: `{N}` to add, `{K}` to skip, `{M}` collisions.
5. On confirm: copy files into `Templates/user-global/{artifact_type}/` (or product scope per user choice), update registry, log actions.
6. If >5 templates imported: create pack backup before starting (per `references/template-protocol.md` backup rules).

## Wizard: `update`

1. Pick target template.
2. `AskUserQuestion`: "What do you want to change?"
   - Frontmatter field (pick one)
   - Body
   - Add a language (→ routes to `add-language`)
   - Variables (add / remove / change)
3. Auto-archive: copy current file to `Templates/_archive/{template_id}/v{old_version}-{YYYY-MM-DD-HHmm}.md`. Keep last 10 per template_id.
4. Apply edit. Bump `version` (patch for body edits, minor for variable additions, major for breaking changes) and update `updated:`.
5. Update registry entry.
6. Show a summary.

## Delete / restore

`delete` is soft by default:

1. Copy file to `Templates/_archive/deleted/{template_id}-{YYYY-MM-DD-HHmm}.md`.
2. Remove original.
3. In registry, set `status=deleted` and `deleted_at=<timestamp>`.
4. Keep in registry for 30 days, then purge on next `validate` pass.

`restore` moves back from `_archive/deleted/` and sets `status=active`.

Hard delete requires explicit `delete --permanent`; always show a confirmation with `AskUserQuestion`.

## Validate

Full pass:

1. For each file in `Templates/` (excluding `_archive/`, `_partials/`, `_System/`):
   - Parse YAML frontmatter. Report errors.
   - Check required keys: `template_id`, `artifact_type`, `scope`, `default_language`, `available_languages`, `version`.
   - Validate `template_id` uniqueness.
   - Check that `available_languages` matches the `<!-- lang:xx -->` blocks in the body.
   - Check that `sections_include:` partials exist in `_partials/`.
   - Check that `min_plugin_version` is a valid semver.
2. Compare against registry. Find orphans (in registry but file missing) and unregistered (file present but not in registry).
3. Ask user how to reconcile (rebuild / prompt per item).
4. Report summary.

## Rebuild-registry

Walk `Templates/` recursively:

- For each `*.md` file outside `_archive/`, `_partials/`, `_System/`: parse frontmatter, build a registry entry.
- Include built-in templates by scanning `{plugin-root}/templates/built-in/` and using `builtin://` URIs.
- Preserve `usage_count` and `last_used` from the previous registry (match by `template_id`).
- Write new `_registry.json` atomically (write to `.tmp`, rename).

Always snapshot the old registry to `Templates/_archive/_registry-pre-rebuild-{timestamp}.json` before overwriting.

## Helper routine: `resolve(artifact_type, subtype, product_id, language)`

Implements Step T-0 through T-3 of `references/template-protocol.md`. Returns one of:

- `{ template_id, path, version, frontmatter }` — chosen template
- `{ fallback: "builtin-default" }` — no user template matched
- `{ fallback: "no-template" }` — user explicitly declined

## Helper routine: `render(template_id, variables, language)`

Implements Step T-4 and T-5. Returns the rendered markdown string, plus a `metadata` block with `template_id`, `version`, `rendered_at`.

After successful render, updates `usage_count`, `last_used`, and appends to `Templates/_System/usage.log`.

## Backup logic

Three levels, all documented in `references/template-protocol.md`:

1. **Per-template archive** — on every `update` or `delete`: copy current file to `Templates/_archive/{template_id}/v{old_version}-{YYYY-MM-DD-HHmm}.md`. Keep last 10.
2. **Pack backup** — before: `rebuild-registry`, mass `import` (>5 files), schema migration, "start fresh" during onboarding, `restore --from` (creates a safety pack of current state first). Snapshot to `{storage_root}/backups/templates-{YYYY-MM-DD-HHmm}-{trigger}/`. Keep last 5.
3. **Manual** — `backup` and `restore --from {name}` with diff preview and explicit confirmation.

## Integration with other skills

`template-library` is the implementation of `references/template-protocol.md`. Other skills that produce artifacts reference the protocol and invoke `resolve()` / `render()` helpers conceptually. The skill does NOT execute steps on their behalf — each skill declares its Step T explicitly.

Routing with `knowledge-library`:

- If the user asks about templates while in `knowledge-library` context, `knowledge-library` delegates to this skill.
- If the user asks about sources / insights while in this skill context, this skill delegates to `knowledge-library`.

## Output format

Default output — concise markdown tables and short confirmations. Always include template paths in messages so users know exactly where their data lives.

Example `list` output:

```
Templates (12 total — 4 built-in, 6 user-global, 2 product-specific)

| ID                            | Type         | Scope         | Lang   | Updated    |
|-------------------------------|--------------|---------------|--------|------------|
| concept-builtin-default       | concept      | built-in      | uk, en | 2026-04-17 |
| requirements-builtin-default  | requirements | built-in      | uk, en | 2026-04-17 |
| requirements-ab-test-v1       | requirements | user-global   | uk, en | 2026-04-17 |
| requirements-prom-marketplace | requirements | product:prom  | uk     | 2026-04-17 |
| …                             | …            | …             | …      | …          |

Registry: {storage_root}/Templates/_registry.json (last rebuilt 2026-04-17)
```

Example `show` output:

```
Template: requirements-ab-test-v1
Scope: user-global   Product: (any)
Languages: uk (default), en
Version: 1.0.0      Status: active
Updated: 2026-04-17 by Andrii
Used: 7 times, last 2026-04-15
Path: {storage_root}/Templates/user-global/requirements/ab-test-v1.md

Variables: feature_name, hypothesis, success_metrics, has_baseline, baseline_source
Tags: ab-test, growth

Preview (uk):
  # {{feature_name}}
  ## Гіпотеза
  {{hypothesis}}
  …
```

## Configuration in `local-context.md`

Read and respect:

```yaml
## Templates

templates:
  preference: smart            # auto | always_ask | smart
  default_language: uk
  favorite_templates: []
  auto_save_to_vault: true
```

Write operations update `onboarding.templates_setup_completed` when `add` first runs via `plugin-configurator` Step O-T.

## See also

- `references/template-protocol.md` — the full resolution protocol
- `skills/plugin-configurator/SKILL.md` — Step O-T onboarding flow invites this skill
- `skills/knowledge-library/SKILL.md` — sibling skill; routing rules documented there
- `references/persistent-storage.md` — where templates physically live
