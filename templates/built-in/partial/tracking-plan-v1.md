---
template_id: partial-builtin-tracking-plan
schema_version: 1
name: "Tracking plan"
artifact_type: partial
subtype: tracking-plan
scope: built-in
products: []
default_language: en
available_languages: [en]
version: "1.0.0"
author: "grow-pm"
created: 2026-09-29
updated: 2026-09-29
tags: [partial, tracking-plan, analytics, events, instrumentation]
description: "Tracking-plan section (since v3.6.0): event, trigger, properties, owner, verification. Included by name, or inserted by template-protocol T-5 step 3b when role_defaults.extra_sections lists it and the body has no such section."
status: active
min_plugin_version: "3.6.0"
variables: []
---

## Tracking plan

<!-- One row per event the feature must emit. The skill fills rows from the spec and the event dictionary already in context and never asks for them; a cell it cannot fill stays TBD. -->

| Event | Trigger | Properties | Owner | Verification |
|-------|---------|------------|-------|--------------|
| TBD | TBD | TBD | TBD | TBD |

<!-- Event: object_action name as in the event dictionary (e.g. checkout_started). Trigger: the user or system action that fires it, and on which surface. Properties: name:type, required ones first; no personal data. Owner: the team that maintains the event. Verification: how firing is confirmed before a metric built on it is trusted — QA check, debug stream, or dashboard count against the backend count. -->

- **Metrics these events feed:** TBD
