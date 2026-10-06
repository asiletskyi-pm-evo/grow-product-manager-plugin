---
template_id: concept-builtin-strategy-memo
schema_version: 1
name: "Strategy Memo"
artifact_type: concept
subtype: strategy-memo
scope: built-in
products: []
match: subtype
default_language: en
available_languages: [en]
version: "1.1.0"
author: "grow-pm"
created: 2026-09-29
updated: 2026-10-06
tags: [concept, strategy-memo, strategy, bets, kill-criteria]
description: "Strategy memo (since v3.6.0): strategic intents, bets, proxy metrics, what we stop, kill criteria, base rates / outside view"
status: active
min_plugin_version: "3.6.0"
variables:
  - { name: feature_name, type: string, required: true, label: "Strategy or theme" }
  - { name: problem_statement, type: text, required: true, label: "Strategic question we are answering" }
  - { name: horizon, type: string, required: false, label: "Horizon", hint: "The period the bets are judged over, e.g. 1–3 years" }
  - { name: bets, type: list, required: false, label: "Bets" }
  - { name: kill_criteria, type: list, required: false, label: "Kill criteria" }
  - { name: related_research, type: reference, required: false, label: "Related research" }
---

<!-- lang:en -->
# Strategy memo: {{feature_name}}

{{#if horizon}}**Horizon:** {{horizon}}{{/if}}

## Context

{{problem_statement}}

<!-- Why this question now: the market, product and business facts that force it — each with its evidence class, source and date (pm-mental-model.md §4), e.g. "reported · finance dashboard · H1 2026" for a figure from the brief; a fact with no source reads `[assumed — …]`. -->

## Strategic intents

<!-- Two to four intents: the problem or outcome we commit to, not a feature list. Link each to the product objective or OKR it serves, where one exists. -->
- TBD

## Bets

<!-- Per bet: what we invest (people, money, time), the expected return, the stage (explore / expand / extract) and the intent it serves. The expected return is forward-looking: no evidence class, only its basis (model, owner, date); an unsourced input inside it reads `[assumed — …]`. -->

| Bet | Investment | Expected return | Stage | Intent served |
|-----|------------|-----------------|-------|---------------|
{{#each bets}}
| {{this}} | TBD | TBD | TBD | TBD |
{{/each}}

## Proxy metrics

<!-- Leading indicators that tell early whether a bet works: metric · baseline (with its evidence class and period) · target (no class) · review cadence · source. -->
- TBD

## What we stop

<!-- The work this strategy stops or deprioritises, and what that frees. A strategy that stops nothing is a wish list. -->
- TBD

## Kill criteria

<!-- Per bet: the signal and the date at which we stop or pivot — fixed now, before the data arrives. -->
{{#each kill_criteria}}
- {{this}}
{{/each}}

## Base rates / outside view

<!-- How often comparable bets succeed: the reference class, its success rate, its evidence class and its source — internal history or external data (`external`). Say "none known" rather than invent one. -->
- TBD

## Related materials

{{#if related_research}}- {{related_research}}{{/if}}
<!-- /lang:en -->
