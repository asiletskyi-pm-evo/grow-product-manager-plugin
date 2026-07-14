---
template_id: vacancy-profile-builtin-default
schema_version: 1
name: "Vacancy Profile"
artifact_type: vacancy-profile
subtype: null
scope: built-in
products: []
default_language: en
available_languages: [en]
version: "1.0.0"
author: "grow-pm"
created: 2026-07-14
updated: 2026-07-14
tags: [hiring, vacancy, people]
description: "Universal vacancy profile — Request, Role goals (SMARTCBP), Description, Conditions, Selection process"
status: active
min_plugin_version: "2.0.0"
variables:
  - name: position
    type: string
    required: true
    label: "Position"
  - name: team
    type: string
    required: false
    label: "Team"
  - name: role_goals
    type: list
    required: true
    label: "Role goals (SMARTCBP on 3/6/12 months)"
  - name: must_have
    type: list
    required: false
    label: "Requirements — must have"
  - name: nice_to_have
    type: list
    required: false
    label: "Requirements — nice to have"
  - name: killer_questions
    type: list
    required: false
    label: "Killer questions (numeric / yes-no + If/Then)"
---

<!-- lang:en -->
# Vacancy Profile — {{position}}

## 1. Request
- Budget: TBD · Country of employment: TBD · Team: {{#if team}}{{team}}{{else}}TBD{{/if}}
- Position: {{position}}
- Team composition (roles, headcount, team goals, most-frequent interactions; if the role is new — why it appeared): TBD
- Reason for opening: TBD · Direct manager: TBD · Workplace: TBD · Equipment/software: TBD

## 2. Role goals (the heart — SMARTCBP)
<!-- Written BEFORE the vacancy. For a new role, Comparable = 0. -->
{{#each role_goals}}
- {{this}}
{{/each}}

## 3. Vacancy description
- Open date: TBD · Team tools: TBD
- **Requirements — must have:**
{{#if must_have}}{{#each must_have}}
  - {{this}}
{{/each}}{{else}}
  - TBD
{{/if}}
- **Requirements — nice to have:**
{{#if nice_to_have}}{{#each nice_to_have}}
  - {{this}}
{{/each}}{{else}}
  - TBD
{{/if}}
- Core duties/tasks: TBD
- Extra info (KPIs, financial motivation, potential candidates): TBD
- Ideal candidate profiles (4–5 LinkedIn links): TBD

## 4. Hiring conditions
- Employment type: TBD
- Salary Gross/Net — probation / after + currency: TBD
- Probation duration: TBD

## 5. Selection process
- Test task / candidate documents: TBD
- Process participants: TBD
- **Killer questions:**
{{#if killer_questions}}{{#each killer_questions}}
  - {{this}}
{{/each}}{{else}}
  - TBD (numeric / yes-no about past experience + If/Then rule)
{{/if}}

<!-- Map these sections onto the employer's HR-form fields from local-context (people.hr_form). -->
<!-- /lang:en -->
