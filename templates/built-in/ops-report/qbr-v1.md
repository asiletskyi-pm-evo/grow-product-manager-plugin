---
template_id: ops-report-builtin-qbr
schema_version: 1
name: "Quarterly Business Review"
artifact_type: ops-report
subtype: qbr
scope: built-in
products: []
match: subtype
default_language: en
available_languages: [en]
version: "1.0.0"
author: "grow-pm"
created: 2026-09-29
updated: 2026-09-29
tags: [ops, qbr, quarter, financials, business]
description: "Quarterly business review (since v3.6.0): financials, money bridge, initiatives, market, org health, risks, decisions taken, commitments for next quarter"
status: active
min_plugin_version: "3.6.0"
variables:
  - { name: team_name, type: string, required: true, label: "Team or direction" }
  - { name: quarter, type: string, required: true, label: "Quarter" }
  - { name: quarter_dates, type: string, required: false, label: "Quarter period" }
---

<!-- lang:en -->
# QBR: {{team_name}} · {{quarter}}{{#if quarter_dates}} ({{quarter_dates}}){{/if}}

## Summary

<!-- Three to five lines: the quarter against its objectives, the biggest win, the biggest miss, the one decision needed. -->

## Financials

<!-- Plan vs actual for the revenue, margin and cost lines the direction owns; full-year forecast at the current trend; each deviation with its cause. Every number carries its period and source marker. -->

| Line | Plan | Actual | Δ | Full-year forecast | Cause of deviation |
|------|-----:|-------:|--:|-------------------:|--------------------|
| TBD | | | | | |

{{> money-bridge}}

## Initiatives

<!-- Per initiative: objective served, status, planned vs delivered, next step. Features as `code — name`. Delivery numbers come from the quarter review when one exists. -->

| Initiative | Objective served | Status | Planned vs delivered | Next |
|------------|------------------|--------|----------------------|------|
| TBD | | | | |

## Market

<!-- Market and competitor moves this quarter that change a bet or a plan — each with its source and date. -->
- TBD

## Org health

<!-- Aggregate only: headcount, open roles, attrition, capacity vs plan, tech-debt share; counts below 3 are written as "fewer than 3" so no person is identifiable. Never content from person profiles, 1-1 notes, reviews or offboarding. -->
- TBD

## Risks

<!-- Risk · likelihood · impact · owner · mitigation. -->
- TBD

## Decisions taken

<!-- Decisions made this quarter, each linked to its decision-log record where one exists. -->
- TBD

## Commitments for next quarter

<!-- Three to five measurable commitments, each with an owner and a date — the first thing the next QBR checks. -->
- TBD
<!-- /lang:en -->
