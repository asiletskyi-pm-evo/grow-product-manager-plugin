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

### artifact_type enum (canonical list)

Every `artifact_type` a skill may declare in Step T. A type absent from this list cannot be created through the `template-library` wizard, so a skill declaring one has no path to a custom template.

**Product contour:** `concept` · `requirements` · `research` · `cjm` · `epic` · `task` · `presentation` · `ops-report` · `roadmap` · `meeting-notes` · `focus` · `partial`

**People contour:** `goal-letter` · `report-3t5f` · `one-on-one-notes` · `followup-arcv` · `vacancy-profile` · `performance-review` · `offboarding-plan` · `delegation-audit`

> `roadmap` (planning suite), `meeting-notes` (meeting-processor), `focus` (focus-advisor) and `delegation-audit` (delegation-coach) were declared by their skills but missing from this enum until v2.0.2 — the wizard's type list and this enum must both be updated when a skill starts producing a new artifact. `testing/skill_lint.py` → `artifact-types` enforces it.
>
> Not every enum member ships a built-in template — see "Zero-candidate fallback" below for what happens then.

### Frontmatter schema

```yaml
---
template_id: requirements-ab-test-v1     # unique across the registry
schema_version: 1                        # format version
name: "A/B Test Requirements"            # or map: {uk: "...", en: "..."}
artifact_type: requirements              # one of the artifact_type enum above
subtype: ab-test                         # optional specialization
scope: user-global                       # built-in | user-global | product
products: []                             # [] = all products; else list
match: subtype                           # optional (since v3.6.0): a candidate only when the request subtype equals this subtype
default_language: uk
available_languages: [uk, en]
version: "1.0.0"
author: "<author>"
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
| Partial | `{{> success-metrics-block}}` | Include a partial: `{storage_root}/Templates/_partials/{name}.md` first, then the built-in `builtin://partial/{name}-v1.md` (since v3.5.0) |
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
- `subtype` (optional) — e.g. `ab-test`, the skill's own inference; when the skill declares none and its Step T opts in (write-concept, requirements-creator, product-reporter's quarter mode), `role_defaults.template_defaults[artifact_type]` (Step 0i; a hat overlays it) becomes the request subtype (since v3.6.0; a value `default` or none keeps the subtype null; not in automated runs). A role-derived or explicit subtype brings that type's `match: subtype` built-in into T-1 and makes it decisive among the built-ins (T-3); the user's own templates still sort first by scope. A skill may let the role subtype replace one of its generic mode subtypes only where its own step says so (product-reporter's quarter mode is the one such place)
- `product_id` (optional) — from `local-context.md` active product
- `language` (required) — from `local-context.md` or explicit request

### Step T-1. Load registry

Read `{storage_root}/Templates/_registry.json`. Use `references/persistent-storage.md` resolution to locate `storage_root`. If the registry is missing or malformed, run `template-library: rebuild-registry` on the fly (walk `Templates/` and rebuild) before continuing.

Built-ins are always read from `{plugin-root}/templates/built-in/` (except `partial/`) — a built-in missing from an older registry is still a candidate; the registry adds only usage stats and the user's own templates, and `match` is read from the template's frontmatter. Filter candidates: `artifact_type` matches AND `status=active` AND `min_plugin_version ≤ current_plugin_version` AND (no `match: subtype`, or the request subtype equals the candidate's subtype). The role-specific built-ins of v3.6.0 carry `match: subtype`, so a request without that subtype resolves exactly as in v3.5.0 — no new candidate, no new question; they remain listable and pickable in the `template-library` wizard.

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

- **Zero candidates** → walk the built-in ladder for `artifact_type`, first hit wins:
  1. `builtin://{artifact_type}/{subtype}-v1.md` — the requested subtype, when one was declared.
     Example: `artifact_type: research`, `subtype: walkthrough` → `builtin://research/walkthrough-v1.md` (flow-walkthrough report, since v3.1.0).
  2. `builtin://{artifact_type}/default-v1.md` — the type's generic default.
  3. The type's **only** built-in, if it ships exactly one (e.g. `cjm/funnel-v1.md`).
  4. Nothing matched → warn the user and proceed template-free (the skill renders its own structure). This is a normal outcome, not an error.

  > Rungs 1 and 3 exist because several types deliberately ship **no** `default-v1`: `ops-report`, `presentation`, `research` and `cjm` are meaningful only per subtype — a generic "default ops report" is not a document anyone wants. Until v2.0.2 the rule named only `default-v1`, so those four types always fell through to the warning even though a perfectly good built-in existed.
- **Exactly one candidate** → use it silently. (The artifact is marked in T-5, which defines the one marker format — do not restate it here.)
- **An exact `match: subtype` hit** (since v3.6.0) — a built-in carrying `match: subtype` whose subtype equals the request subtype, when no user-global or product template of this `artifact_type` is a candidate → use it silently under `smart` and `auto` (language and usage bonuses never outrank it); `always_ask` still asks, listing it first. With a user or product template among the candidates, the rules below apply as before (scope sorts first).
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

Parse `variables:` from the chosen template's frontmatter. For each required variable not already in the skill's context, ask the user via `AskUserQuestion`, batched by 1–4 variables per question, with type-aware UI (a variable whose hint says it is derived by a skill step — the judgment footer's, `simulated_input` — is never asked):

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
3. Expand `{{#if}}`, `{{#each}}`, `{{> partial}}` (user `_partials/` first, then `builtin://partial/`).
3a. **Judgment footer (since v3.5.0).** When `artifact_type` belongs to the Product contour (the enum above; not `partial`), close the body with the judgment footer: a user override `_partials/judgment-footer.md` if present, else `builtin://partial/judgment-footer-v1.md`. Its variables are **derived by the skill, never asked** (T-4 does not apply to the footer): `altitude` from Step 0i step 5 (`local-context-protocol.md`); `serves` = a product or direction goal, OKR, strategic intent, or the parent initiative / epic that the request or the artifact's sources explicitly link — never a person's goal or profile (People-contour data stays local), and the OKR list in `local-context.md` alone is not a link; `— (no linked goal)` otherwise; `next` from the step the skill proposes — a product or delivery step, never a People-contour action about a person; `— (no product step)` when there is none. **Confidence line (since v3.7.0):** where `references/judgment-points.md` §1 names one for the skill and mode, the skill also sets `confidence`, `sensitive_to` and `would_change_if` — derived, never asked (§3 of that file) — and the line renders directly above the altitude line; elsewhere they stay unset and no line is rendered. A user override without these placeholders gets the built-in confidence line above its content. The footer is the last content before the step-5 marker. It goes on the artifact the skill delivers, wherever it is kept (chat, file, vault, Confluence) and also when no template applied — but not on answers that are not the skill's artifact (a Q&A reply, a search-result list, a quick summary or escape-hatch notes, a clarifying reply) and not on a return payload to a calling skill (the caller's artifact carries it). Placement exceptions: a `presentation` puts it on the closing slide, or in the speaker notes of the last slide — for an external audience (customer, partner, external users, social media) only in the vault / outline companion, never on a slide or in speaker notes; `task-creator` puts it on the epic only when this run creates the epic (T-B) — an existing epic is never edited to add it — and on its Step 11 report, never on each task. People-contour artifacts carry no footer.
3b. **Role extra sections (since v3.6.0; interactive runs; only in skills whose step implements it — requirements-creator for `requirements`, product-research and feedback-triage for `research`).** For each partial in `role_defaults.extra_sections[artifact_type]`, insert the expanded partial (user `_partials/` first, then `builtin://partial/{name}-v1.md`) above the judgment footer (the footer of 3a stays the last content) — only when the rendered body has no section with the same meaning — compared in the rendered language, case-insensitively, ignoring numbering, and matching headings that start with a synonym: `nfr` ↔ "Non-Functional Requirements"; `tracking-plan` ↔ "Tracking plan", "Analytics / Tracking", "Analytics coverage (requirements)"; `repository-entry` ↔ "Repository entry" (and their translations in `user.language`) (the built-in `requirements/default` already has NFR, `requirements/ab-test` already has Analytics / Tracking).
3c. **Evidence labels (since v3.8.0).** When `artifact_type` belongs to the Product contour, confirm `artifact-style-gate.md` Gate 4b on the rendered body and fix silently, only toward a weaker class (add `[assumed — …]`, move `simulated` content out of a findings section, downgrade a label, restore the class a source supports to a claim that lost its label — never one the user removed at the run's review step, except `simulated` / `assumed` — remove quote marks from a non-verbatim quote; never invent a source or upgrade a class; Gate 4b §6). The classes come from `data-integrity-protocol.md` Gate Check 6 where the skill ran its data gate, else from the source markers the body cites. Never on a Jira task body or batch (copied requirement text keeps its own labels; none is added) or an existing epic, a prototype or handoff, a 1-1, a Q&A reply, a search-result list, a status board or registry list, a quick summary or escape-hatch notes, or a return payload (it keeps its labels; the caller's artifact is checked). Partial cases (`artifact-style-gate.md` Gate 4b §5): an Analyze & Improve document gets advisory findings only (from the checker when it runs, so they are not reported twice), and slides for an external audience carry the class in the source caption without internal source names, with hand-back lines only in the outline companion. It runs whether or not a template applied and independently of `review_mode`, in automated runs too (labels and the 6b handling of synthetic input, never a hand-back line — `data-integrity-protocol.md` 6d), and before step 4, so the vault keys are derived from the labels the body carries. People-contour artifacts carry no labels.
3d. **Hint comments (since v3.8.0).** After steps 2–3c, drop the authoring hint comments (`<!-- … -->`) of the template and its expanded partials from the rendered artifact — they are guidance for the skill. Language markers are resolved in step 2 and are not hint comments; the step-5 marker and a missing-partial notice stay.
4. Write the rendered artifact via `references/vault-protocol.md` to the vault (if configured) or to workspace.
5. Append `<!-- template: {template_id} version: {version} -->` at the end — after the judgment footer, so the order is always body → footer → marker.
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
- **Missing partial.** Looked up in the user `_partials/` and then as `builtin://partial/{name}-v1.md`; if neither exists it is replaced by `<!-- partial {name} not found -->`, logged as a warning, rendering continues.
- **`min_plugin_version` > current.** Hidden from resolution. `template-library: list` marks it with a warning.
- **Language missing in selected template.** Fall back to `default_language`, warn the user.
- **Registry schema version older than current plugin.** `template-library: rebuild-registry` is invoked; migration adds new fields with defaults.
- **`storage_root` unreachable.** Resolve `builtin://` URIs directly against `{plugin-root}/templates/built-in/` — the built-ins ship with the plugin and need no registry. Custom templates are simply unavailable until storage is reachable; say so rather than failing the skill. (Until v2.0.2 this rule pointed at "the registry's seed file embedded in the plugin", which does not exist.)
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
      "match": null,
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
  storage_root: "~/.grow-pm"   # or {vault}/{plugin_folder}
  setup_completed: true
```

`plugin-configurator` writes this section during Step O-T of onboarding; users can change it via Update mode. **The canonical key set lives in `skills/plugin-configurator/references/context-schema.md` → "Templates section format"** — this block mirrors it for convenience; if they ever disagree, the schema wins.

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
