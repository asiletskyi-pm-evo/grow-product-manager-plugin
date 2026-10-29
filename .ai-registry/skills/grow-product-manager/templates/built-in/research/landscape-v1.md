---
template_id: research-builtin-landscape
schema_version: 1
name: "Product Landscape Map"
artifact_type: research
subtype: landscape
scope: built-in
products: []
default_language: en
available_languages: [en]
version: "1.1.0"
author: "grow-pm"
created: 2026-09-11
updated: 2026-10-06
tags: [research, landscape, competitors, category]
description: "Category map of competitor and adjacent products: product table, us vs them, gaps, candidates for research"
status: active
min_plugin_version: "3.3.0"
variables:
  - name: category
    type: string
    required: true
    label: "Category (store genre or free tag)"
  - name: market
    type: string
    required: true
    label: "Market (ISO country code)"
  - name: our_product
    type: string
    required: true
    label: "Our product"
  - name: products
    type: list
    required: true
    label: "Registry products included (slugs)"
  - name: sources
    type: list
    required: false
    label: "Sources"
---

<!-- lang:en -->
# Landscape: {{category}} — {{market}}

## 1. Scope

- Our product: {{our_product}}
- Registry products: {{#each products}}`{{this}}`{{#unless @last}}, {{/unless}}{{/each}}
- Registry: `~/.grow-pm/landscape/` (local, internal data)

## 2. Product table

<!-- Each fact takes the evidence class of the source it cites (pm-mental-model.md §4): a store, web, traffic or design-library source `external` (source, date), a walkthrough `observed`, the user `reported (user)`, a note `[assumed — …]`. One label may cover a column whose cells share class and source; a cell's own label overrides it. -->

| Product | Kind | Role | Platforms | Walkable surfaces | Size signals | Key flows | Notable | Last researched |
|---------|------|------|-----------|-------------------|--------------|-----------|---------|-----------------|
| {{our_product}} (ours) | | — | | | | | | |
| | | | | | | | | |

Roles: direct-competitor · adjacent · benchmark · inspiration. Size signals: store rating and ratings count, traffic rank when a connector answered — `external`, with source and date (`Evidence: external — <store lookup>, <market>, <date>` when the whole column shares them).

## 3. Us vs them

| Characteristic | {{our_product}} | Direct competitors | Adjacent / benchmark |
|----------------|-----------------|--------------------|----------------------|
| | | | |

## 4. Gaps and opportunities

- 

## 5. Candidates for research

Ranked by role, category match, size, walkable surfaces and staleness (not researched in 12 months first). The user picks any subset or names other products — no cap.

| # | Product | Why now | Suggested run |
|---|---------|---------|---------------|
| 1 | | | flow-walkthrough compare / product-research / brainstorm-features |

## 6. Sources

<!-- Each source with its evidence class — a store, web, traffic or design-library source `external` (source, date), a walkthrough pack `observed`, the user `reported (user)`. Machine scans and bookmarks record how a product was found and are never listed here. -->
{{#each sources}}
- {{this}}
{{/each}}
- Registry records cited as `landscape:<slug>` — each fact takes the class of the source the record cites

<!-- template: research-builtin-landscape version: 1.1.0 -->
