---
template_id: partial-builtin-money-bridge
schema_version: 1
name: "Money bridge"
artifact_type: partial
subtype: money-bridge
scope: built-in
products: []
default_language: en
available_languages: [en]
version: "1.0.0"
author: "grow-pm"
created: 2026-09-29
updated: 2026-09-29
tags: [partial, money-bridge, revenue, business]
description: "Money bridge section (since v3.6.0), included by the qbr, board-update and business-case built-ins: key metric → revenue driver → expected effect, from the Key Metrics rows that carry a Revenue driver"
status: active
min_plugin_version: "3.6.0"
variables:
  - name: money_bridge_rows
    type: list
    required: false
    label: "Money bridge rows"
    hint: "Derived by the skill, never asked: one item per product.key_metrics row whose Revenue driver is set and is not '—', written '<metric> | <revenue driver> | <expected effect>'; the expected effect comes from the including artifact's own numbers with their source, '— (not estimated)' when it gives none — never invented; empty when no row carries a Revenue driver"
---

## Money bridge

{{#if money_bridge_rows}}
<!-- One row per Key Metrics row with a Revenue driver (local-context.md → Key Metrics). The expected effect cites the number behind it; a metric claim without a row here stays unlinked, it is not guessed. -->

| Metric | Revenue driver | Expected effect |
|--------|----------------|-----------------|
{{#each money_bridge_rows}}
| {{this}} |
{{/each}}
{{else}}
No revenue mapping configured — add a Revenue driver column to Key Metrics
{{/if}}
