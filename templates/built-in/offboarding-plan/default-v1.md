---
template_id: offboarding-plan-builtin-default
schema_version: 1
name: "Offboarding Plan"
artifact_type: offboarding-plan
subtype: null
scope: built-in
products: []
default_language: en
available_languages: [en]
version: "1.0.0"
author: "grow-pm"
created: 2026-07-14
updated: 2026-07-14
tags: [offboarding, people]
description: "Four-meeting offboarding plan with evidence gate. Strictly local — highest-sensitivity People-data."
status: active
min_plugin_version: "2.0.0"
variables:
  - name: person
    type: string
    required: true
    label: "Person"
  - name: evidence
    type: text
    required: true
    label: "Evidence base (goals + reports showing non-achievement)"
  - name: diagnosis
    type: enum
    required: true
    options: [cant, doesnt-want, immediate]
    label: "Diagnosis"
---

<!-- lang:en -->
# Offboarding Plan — {{person}}

> **Strictly local.** Highest-sensitivity People-data — never Confluence/Jira/external services. Delicate, factual, respectful. Don't drag it out (≈1 in 4 reanimate).

## Gate — Evidence base
{{evidence}}
<!-- No goals/reports → STOP: set goals (goal-setter) + 3T5F reporting first; the conversation must not be "by feel". -->

## Diagnosis
**{{diagnosis}}** — "can't" → maybe development, reconsider · "doesn't-want" → the four-meeting algorithm · "immediate" → theft/unlawful/ethics only.
Pre-screen: which motivation tools are still untried (career ladder, incentives, 1-1s, sabbatical…)?

## Four-meeting algorithm (each ends with an ARCV follow-up)
1. **Meeting 1 — critical issues.** Results are unsatisfactory (not personality); ≥45 min, a dialogue; **no mention of dismissal**. Follow-up on problem areas. ~1 month, no change → Meeting 2.
2. **Meeting 2 — warning + measurable probation.** Exactly what to fix / achieve by which date; clear probation term; book the results meeting now; the person understands dismissal follows if unchanged (no euphemisms).
3. **Meeting 3 — probation results.** Passed → congratulate, expect it sustained. Not passed → dismiss, no further chances.
4. **Meeting 4 — sustainability check (~3 months).** Relapse → dismiss (plain narrative). Sustained → congratulate (the manager's win).

## The dismissal conversation & team message
- Script (≥30 min): thank for the contribution; explain reasons with facts/KPIs (not personal qualities); agree wording + team message; agree last working day.
- Team message (manager-written, agreed): reasons + last day + reassign the person's open tasks.
- Optional softening for hard circumstances: advance notice, a month or two of pay, outplacement, temporary part-time.
<!-- /lang:en -->
