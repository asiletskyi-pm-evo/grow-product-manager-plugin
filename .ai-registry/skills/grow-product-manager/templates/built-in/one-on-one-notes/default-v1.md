---
template_id: one-on-one-notes-builtin-default
schema_version: 1
name: "1-1 Notes"
artifact_type: one-on-one-notes
subtype: null
scope: built-in
products: []
default_language: en
available_languages: [en]
version: "1.0.0"
author: "grow-pm"
created: 2026-07-14
updated: 2026-07-14
tags: [1-1, people, notes]
description: "1-1 meeting notes — agenda (prepare) and signals + plain notes (analyze)"
status: active
min_plugin_version: "2.0.0"
variables:
  - name: person
    type: string
    required: true
    label: "Person"
  - name: date
    type: date
    required: true
    label: "Date"
  - name: questions
    type: list
    required: false
    label: "Personalized questions"
  - name: signals
    type: list
    required: false
    label: "Signals (motivation / burnout / conflict / career)"
  - name: plain_notes
    type: text
    required: false
    label: "Plain notes (observations, facts about the person)"
---

<!-- lang:en -->
# 1-1 — {{person}} · {{date}}

> A meeting for the person and about the person: feedback, growth, trust — not tasks/status. The manager prepares and writes the follow-up. Kept strictly local.

## Agenda (6 stages)
1. **Intro** — start from last follow-up's action items (seven "how" questions for guarded people).
2. **Person's questions** — the person leads; what's uncomfortable to say publicly.
3. **Manager's questions** — how they're doing + work effectiveness; align personal goals.
4. **Follow-up** — written by the manager (see the ARCV follow-up).
5. **Next meeting** — schedule (Friday preferred; reschedule, never cancel).
6. **Thanks.**

## Personalized questions
{{#if questions}}
{{#each questions}}
- {{this}}
{{/each}}
{{else}}
- TBD
{{/if}}

## Signals
{{#if signals}}
{{#each signals}}
- {{this}}
{{/each}}
{{else}}
- TBD (separate facts from assumptions; route colleague complaints via "Did you tell them yourself?")
{{/if}}

## Plain notes
{{#if plain_notes}}
{{plain_notes}}
{{else}}
- TBD
{{/if}}

## Follow-up
→ see the ARCV actionable follow-up (manager-owned).
<!-- /lang:en -->
