---
template_id: partial-builtin-judgment-footer
schema_version: 1
name: "Judgment footer"
artifact_type: partial
subtype: judgment-footer
scope: built-in
products: []
default_language: en
available_languages: [en]
version: "1.0.0"
author: "grow-pm"
created: 2026-09-28
updated: 2026-09-28
tags: [partial, footer, altitude, judgment]
description: "Closing line of every Product-contour artifact: the altitude line (v3.5.0). The confidence-and-falsifier line joins it in v3.7.0."
status: active
min_plugin_version: "3.5.0"
variables:
  - name: altitude
    type: enum
    required: true
    label: "Altitude of this artifact"
    options: [L1, L2, L3, L4]
    hint: "Derived by the skill at Step 0i from the request (role-profiles.md §1, §5 step 4) — never asked"
  - name: serves
    type: string
    required: true
    label: "↑ serves"
    hint: "A product or direction goal, OKR, strategic intent, or the parent initiative / epic that the request or the artifact's sources explicitly link — never a person's goal or profile; the OKR list in local-context.md alone is not a link; '— (no linked goal)' otherwise — never invented"
  - name: next
    type: string
    required: true
    label: "↓ next"
    hint: "The concrete next step the skill proposes at the end of this artifact — a product or delivery step, never a People-contour action about a person; '— (no product step)' when there is none"
---

Altitude: {{altitude}} · ↑ serves: {{serves}} · ↓ next: {{next}}
