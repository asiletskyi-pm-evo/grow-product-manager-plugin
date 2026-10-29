---
template_id: research-builtin-discussion-guide
schema_version: 1
name: "Discussion Guide"
artifact_type: research
subtype: discussion-guide
scope: built-in
products: []
match: subtype
default_language: en
available_languages: [en]
version: "1.0.0"
author: "grow-pm"
created: 2026-09-29
updated: 2026-09-29
tags: [research, discussion-guide, interviews, usability-test, jtbd]
description: "Session guide for interviews or usability tests (since v3.6.0): warm-up, context, task and JTBD probes, wrap-up, and notes on avoiding leading questions"
status: active
min_plugin_version: "3.6.0"
variables:
  - name: research_topic
    type: string
    required: true
    label: "Study topic"
  - name: research_question
    type: text
    required: false
    label: "Research question"
  - name: method
    type: enum
    required: false
    options: [interviews, usability-test, mixed]
    label: "Session format"
  - name: research_plan
    type: reference
    required: false
    label: "Research plan"
---

<!-- lang:en -->
# Discussion Guide: {{research_topic}}

- **Research question:** {{#if research_question}}{{research_question}}{{else}}TBD{{/if}}
- **Format:** {{#if method}}{{method}}{{else}}TBD{{/if}} · **Length:** TBD
- **Research plan:** {{#if research_plan}}{{research_plan}}{{else}}TBD{{/if}}

<!-- Before each session: consent and recording confirmed; notes name the participant by id (P1, P2 …), never by name. -->

## 1. Warm-up (≈5 min)

<!-- Build rapport and learn the participant's context; nothing about the product yet. -->
- TBD

## 2. Context (≈10 min)

<!-- How they do the job today — tools, frequency, who else is involved. Ask for the last concrete occasion, not the typical one. -->
- "Walk me through the last time you …" TBD

## 3. Tasks / JTBD probes (≈25 min)

<!-- Usability test: each task states a goal and a success criterion, never the steps. Interviews: JTBD probes — trigger, desired outcome, alternatives tried, anxieties, what made them switch. -->

| # | Task or probe | What we want to learn | Success / signal | Follow-ups |
|---|---------------|-----------------------|------------------|------------|
| 1 | TBD | TBD | TBD | "What happened next?" · "Why was that?" |

## 4. Wrap-up (≈5 min)

<!-- Close the loop and leave room for what the guide missed. -->
- "Is there anything we did not ask that we should have?"
- Thanks, incentive, next steps

## 5. Notes on leading questions

<!-- Read before every session; rewrite any probe above that breaks one of these. -->
- Ask about past behaviour, not hypothetical future use ("would you use …?").
- Neutral, open wording: "How did you …?" rather than "Was it easy to …?".
- One question at a time; offer no answer options before the participant answers.
- Do not name the feature or the solution before the participant does.
- Let silence work; reflect back instead of agreeing or explaining.
- A simulated participant may rehearse this guide; its answers are labelled simulated and never quoted as findings.

<!-- /lang:en -->
