---
template_id: concept-builtin-decision-memo
schema_version: 1
name: "Decision Memo"
artifact_type: concept
subtype: decision-memo
scope: built-in
products: []
match: subtype
default_language: en
available_languages: [en]
version: "1.0.0"
author: "grow-pm"
created: 2026-09-29
updated: 2026-09-29
tags: [concept, decision-memo, decision, options, evidence]
description: "Decision memo (since v3.6.0): problem, options with rejected alternatives, evidence with its source, the ask, risks, owner, revisit trigger — the ask before a decision; the record after it is a decision-log ADR"
status: active
min_plugin_version: "3.6.0"
variables:
  - { name: feature_name, type: string, required: true, label: "Decision to take" }
  - { name: problem_statement, type: text, required: true, label: "Problem and why now" }
  - { name: options, type: list, required: false, label: "Options considered" }
  - { name: the_ask, type: text, required: false, label: "The ask" }
  - { name: decision_owner, type: string, required: false, label: "Decision owner" }
  - { name: revisit_trigger, type: string, required: false, label: "Revisit trigger" }
---

<!-- lang:en -->
# Decision memo: {{feature_name}}

## Problem

{{problem_statement}}

<!-- What breaks or is lost if nothing is decided, and by when. -->

## Options

<!-- Two to four real options, "do nothing" included. Mark the recommended one; every rejected one keeps its reason, so the choice can be audited later. -->

| Option | Pros | Cons | Cost | Recommended / rejected — why |
|--------|------|------|------|------------------------------|
{{#each options}}
| {{this}} | TBD | TBD | TBD | TBD |
{{/each}}

## Evidence

<!-- Each item: claim — source — source-type marker (data-integrity Gate Check 5). An input that rests on an opinion rather than evidence is labelled `assumed`. -->
- TBD

## The ask

<!-- The one decision requested, from whom, by when — and what happens by default if no decision is taken. -->
{{#if the_ask}}{{the_ask}}{{else}}TBD{{/if}}

## Risks

<!-- Risk of the recommended option · likelihood · impact · mitigation. -->
- TBD

## Owner

- {{#if decision_owner}}{{decision_owner}}{{else}}TBD{{/if}}

## Revisit trigger

<!-- The observable signal or date that reopens this decision. Once decided, record it with decision-log — this memo is the ask, not the record. -->
- {{#if revisit_trigger}}{{revisit_trigger}}{{else}}TBD{{/if}}
<!-- /lang:en -->
