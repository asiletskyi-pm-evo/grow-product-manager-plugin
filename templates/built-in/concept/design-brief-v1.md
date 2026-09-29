---
template_id: concept-builtin-design-brief
schema_version: 1
name: "Design Brief"
artifact_type: concept
subtype: design-brief
scope: built-in
products: []
match: subtype
default_language: en
available_languages: [en]
version: "1.0.0"
author: "grow-pm"
created: 2026-09-29
updated: 2026-09-29
tags: [concept, design-brief, design, jtbd, discovery]
description: "Design brief (since v3.6.0): problem, jobs to be done, users and segments, constraints, success metric, out of scope, open questions — frames the problem space, never a solution spec"
status: active
min_plugin_version: "3.6.0"
variables:
  - { name: feature_name, type: string, required: true, label: "Feature or flow name" }
  - { name: problem_statement, type: text, required: true, label: "Problem we are solving" }
  - { name: target_audience, type: text, required: true, label: "Users and segments affected" }
  - { name: jobs_to_be_done, type: list, required: false, label: "Jobs to be done" }
  - { name: success_metric, type: string, required: false, label: "Success metric" }
  - { name: related_research, type: reference, required: false, label: "Related research" }
---

<!-- lang:en -->
# Design brief: {{feature_name}}

<!-- The brief frames the problem for design exploration. It never prescribes screens, components or a solution — those come out of the explorations and the usability round. -->

## Problem

{{problem_statement}}

<!-- Who hits it, when, and what it costs them today — each claim with its source. If the flow exists, its current state (screenshot or walkthrough step). -->

## Jobs to be done

<!-- One line per job: "When <situation>, I want to <motivation>, so I can <outcome>." -->
{{#each jobs_to_be_done}}
- {{this}}
{{/each}}

## Users and segments

{{target_audience}}

<!-- Per segment: context of use, platform, frequency, accessibility needs. State how many real users the evidence covers. -->

## Constraints

<!-- Confirmed constraints only — platform, Design System components and tokens, accessibility level, legal, technical dependencies — each with its source. -->
- TBD

## Success metric

<!-- One primary metric with baseline and target, one guardrail, and how the usability round will judge the explorations. -->
- {{#if success_metric}}{{success_metric}}{{else}}TBD{{/if}}

## Out of scope

- TBD

## Open questions

<!-- What the explorations or research must answer before handoff, one owner per question. -->
- TBD

## Related materials

{{#if related_research}}- {{related_research}}{{/if}}
<!-- /lang:en -->
