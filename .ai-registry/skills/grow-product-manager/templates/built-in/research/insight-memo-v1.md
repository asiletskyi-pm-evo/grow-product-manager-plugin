---
template_id: research-builtin-insight-memo
schema_version: 1
name: "Insight Memo"
artifact_type: research
subtype: insight-memo
scope: built-in
products: []
match: subtype
default_language: en
available_languages: [en]
version: "1.0.0"
author: "grow-pm"
created: 2026-09-29
updated: 2026-09-29
tags: [research, insight-memo, analytics, analysis]
description: "Short analysis answer (since v3.6.0): the decision, the question, the answer, confidence interval vs point estimate, caveats, SQL / semantic-layer flag, next step"
status: active
min_plugin_version: "3.6.0"
variables:
  - name: metrics
    type: list
    required: true
    label: "Metrics analysed"
  - name: period
    type: string
    required: true
    label: "Period"
  - name: question
    type: text
    required: false
    label: "Question"
    hint: "The analysis request as asked"
  - name: decision
    type: text
    required: false
    label: "Decision this answer feeds"
  - name: query_source
    type: enum
    required: false
    options: [semantic-layer, sql, dashboard, spreadsheet]
    label: "Where the numbers come from"
---

<!-- lang:en -->
# Insight Memo: {{#each metrics}}{{this}}{{#unless @last}}, {{/unless}}{{/each}} · {{period}}

## 1. The decision

<!-- The decision this answer feeds. When the request names none, say so — never invent one. -->
{{#if decision}}{{decision}}{{else}}— (no decision named in the request){{/if}}

## 2. The question

- **Question:** {{#if question}}{{question}}{{else}}TBD{{/if}}
- **Period:** {{period}} · **Baseline / comparison:** TBD

## 3. The answer

<!-- Lead with the answer in one or two sentences, then the evidence. State whether it is causal (experiment) or correlational (observational data). Give an effect with its confidence interval and level where the data allows; a point estimate alone is labelled "point estimate only". -->
- **Answer:** TBD
- **Estimate:** TBD (value, confidence interval and level — or "point estimate only")
- **Causal or correlational:** TBD

## 4. Caveats

<!-- One per line, each with its effect on the answer: period completeness, metric definitions, excluded segments, seasonality, instrumentation gaps, sample size. -->
- TBD

## 5. Source of the numbers

<!-- Flag ad-hoc SQL that bypasses the semantic layer or metric dictionary: its number may not match the dashboards. -->
- **Source:** {{#if query_source}}{{query_source}}{{else}}TBD (semantic-layer · sql · dashboard · spreadsheet){{/if}}
- **Query or metric definition:** TBD (link or metric-dictionary entry)
- **Semantic-layer definition used:** TBD (yes · no — ad-hoc SQL)

## 6. Next step

<!-- One concrete product step: decide, run an experiment, instrument an event, or dig deeper. -->
- TBD

<!-- /lang:en -->
