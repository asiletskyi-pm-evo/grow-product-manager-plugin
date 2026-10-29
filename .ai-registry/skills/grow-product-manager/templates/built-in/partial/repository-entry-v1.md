---
template_id: partial-builtin-repository-entry
schema_version: 1
name: "Repository entry"
artifact_type: partial
subtype: repository-entry
scope: built-in
products: []
default_language: en
available_languages: [en]
version: "1.0.0"
author: "grow-pm"
created: 2026-09-29
updated: 2026-09-29
tags: [partial, repository-entry, research, repository]
description: "Research-repository index card (since v3.6.0): study, date, participants, method, tags, confidence, human-validated flag, link. Included by name, or inserted by template-protocol T-5 step 3b when role_defaults.extra_sections lists it and the body has no such section."
status: active
min_plugin_version: "3.6.0"
variables: []
---

## Repository entry

<!-- A compact index card so the study can be found and reused later. The skill fills it from the artifact above and never asks; a field it cannot fill stays TBD. -->

| Field | Value |
|-------|-------|
| Study | TBD |
| Date | TBD |
| Participants | TBD |
| Method | TBD |
| Tags | TBD |
| Confidence | TBD (high · medium · low) |
| Human-validated | no |
| Link | TBD |

<!-- Study: title and research question. Date: fieldwork or publication date. Participants: n of real users and segment, as ids (P1–P6) — never names or contacts; simulated input is listed as "simulated" and not counted. Method: interviews, usability-test, survey, diary-study, analytics or desk research. Tags: product area, journey stage, job to be done — from the team's repository tag set. Human-validated: yes only after a researcher reviewed the synthesis; model-synthesised findings stay no. Link: vault path or page URL (e.g. https://example.com/research/study-1). -->
