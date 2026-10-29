---
template_id: requirements-builtin-ai-feature
schema_version: 1
name: "AI Feature Requirements"
artifact_type: requirements
subtype: ai-feature
match: subtype
scope: built-in
products: []
default_language: en
available_languages: [en]
version: "1.0.0"
author: "grow-pm"
created: 2026-10-06
updated: 2026-10-06
tags: [requirements, ai-feature, evals, behaviour-spec, kill-criteria]
description: "Requirements for an AI-driven feature (since v3.9.0, P6 — build before you argue): a behaviour spec, an eval set, an acceptable error rate and kill criteria instead of a feature list; includes the tracking plan. Reached only by an explicit AI-feature request (AI / ШІ, LLM, ML model, GPT, chatbot, generative)."
status: active
min_plugin_version: "3.9.0"
variables:
  - name: feature_name
    type: string
    required: true
    label: "Feature name"
  - name: problem_outcome
    type: text
    required: false
    label: "Problem and outcome"
    hint: "Derived from the brief or concept, never asked: the user problem and the measurable outcome — not the model or the solution"
  - name: behaviour_rules
    type: list
    required: false
    label: "Behaviour spec"
    hint: "Derived, never asked: items written '<input or situation> | <must> | <must not> | <fallback / refusal>'; a cell the brief does not state is '⚠️ TBD'"
  - name: eval_cases
    type: list
    required: false
    label: "Eval set"
    hint: "Derived, never asked: items written '<case> | <expected behaviour> | <type: typical / edge / adversarial / refusal> | <origin> | <pass rule>'; origin is a class of pm-mental-model.md §4 — real cases `observed` or `reported` (personal data masked), invented cases `simulated`; expected outputs carry no class"
  - name: eval_set_plan
    type: string
    required: false
    label: "Eval set size and owner"
    hint: "Derived, never asked: the planned number of cases and who maintains the set, when the brief states them; else left empty and rendered '⚠️ TBD'"
  - name: error_rates
    type: list
    required: false
    label: "Acceptable error rate"
    hint: "Derived, never asked: items written '<error class> | <acceptable rate> | <how measured>'; '⚠️ TBD' when the brief states none"
  - name: kill_criteria
    type: list
    required: false
    label: "Kill criteria"
    hint: "Derived, never asked: items written '<observable signal> | <threshold> | <date> | <then: stop / pivot / descope / roll back>'; only the threshold may be '⚠️ TBD' — an unstated date is derived from the launch and the window the spec states (e.g. '4 weeks after launch'), an unstated then defaults to switching the AI behaviour off (roll back)"
  - name: functional_requirements
    type: list
    required: false
    label: "Functional requirements (non-model parts)"
  - name: acceptance_criteria
    type: list
    required: false
    label: "Acceptance criteria"
    hint: "Given/When/Then for the deterministic parts, plus one criterion: the eval set passes at or below the acceptable error rate"
  - name: out_of_scope
    type: list
    required: false
    label: "Out of scope"
  - name: open_questions
    type: list
    required: false
    label: "Open questions"
---

# {{feature_name}} — AI feature requirements

## 1. Problem and outcome

{{problem_outcome}}

<!-- State the user problem and the outcome, not the model. If this section already prescribes a solution, requirements-creator shows its one-line "not solution-shaped" note at review. -->

## 2. AI feature: behaviour and evaluation

### 2.1 Behaviour spec

| Input / situation | Must | Must not | Fallback / refusal |
|-------------------|------|----------|--------------------|
{{#each behaviour_rules}}
| {{this}} |
{{/each}}

### 2.2 Eval set

| Case | Expected behaviour | Type | Origin | Pass rule |
|------|--------------------|------|--------|-----------|
{{#each eval_cases}}
| {{this}} |
{{/each}}

Planned size and owner: {{#if eval_set_plan}}{{eval_set_plan}}{{else}}⚠️ TBD{{/if}}. The set is re-run on every model or prompt change.

<!-- Typical, edge, adversarial and refusal cases. Real cases keep personal data masked; invented cases are `simulated` and never stand in for production behaviour. -->

### 2.3 Acceptable error rate

| Error class | Acceptable rate | How measured |
|-------------|-----------------|--------------|
{{#each error_rates}}
| {{this}} |
{{/each}}

### 2.4 Kill criteria

| Signal | Threshold | Date | Then |
|--------|-----------|------|------|
{{#each kill_criteria}}
| {{this}} |
{{/each}}

## 3. Functional requirements (non-model parts)

{{#each functional_requirements}}
{{@index}}. {{this}}
{{/each}}

## 4. Acceptance criteria

{{#each acceptance_criteria}}
- **AC-{{@index}}:** {{this}}
{{/each}}
- **AC-eval:** the eval set (2.2) passes at or below the acceptable error rate (2.3).

{{> tracking-plan}}

<!-- For an AI feature, add events that measure the error rate and the kill criteria in production: user feedback, fallback / refusal, human override. -->

## 5. Out of scope

{{#each out_of_scope}}
- {{this}}
{{/each}}

## 6. Open questions

{{#each open_questions}}
- {{this}}
{{/each}}
