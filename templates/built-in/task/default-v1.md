---
template_id: task-builtin-default
schema_version: 1
name: "Task (default)"
artifact_type: task
subtype: null
scope: built-in
products: []
default_language: en
available_languages: [en]
version: "1.0.0"
author: "grow-pm"
created: 2026-04-17
updated: 2026-04-17
tags: [task, jira]
description: "Standard Jira task template (FE / BE / Mobile / Design / Analytics)"
status: active
min_plugin_version: "1.9.0"
variables:
  - name: task_title
    type: string
    required: true
    label: "Task title"
  - name: task_type
    type: enum
    required: true
    options: [FE, BE, iOS, Android, Design, Analytics, QA, DevOps]
    label: "Task type"
  - name: parent_epic
    type: reference
    required: false
    label: "Epic"
  - name: description
    type: text
    required: true
    label: "Description"
  - name: acceptance_criteria
    type: list
    required: true
    label: "Acceptance criteria"
  - name: dependencies
    type: list
    required: false
    label: "Dependencies"
---

<!-- lang:en -->
# [{{task_type}}] {{task_title}}

{{#if parent_epic}}
**Epic:** {{parent_epic}}
{{/if}}

## Description

{{description}}

## Context / Links

- Concept: TBD
- Requirements: TBD
- Design: TBD
- Analytics (events): TBD

## What to do

- TBD

## Acceptance Criteria

{{#each acceptance_criteria}}
- [ ] {{this}}
{{/each}}

## Dependencies

{{#if dependencies}}
{{#each dependencies}}
- {{this}}
{{/each}}
{{else}}
- None
{{/if}}

## Estimate

- SP / hours: TBD

## Definition of Done

- [ ] Code reviewed and merged
- [ ] Analytics validated
- [ ] QA passed
- [ ] Documentation updated (if applicable)

<!-- /lang:en -->
