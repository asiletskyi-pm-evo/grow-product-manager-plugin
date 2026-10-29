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
version: "1.2.0"
author: "grow-pm"
created: 2026-09-28
updated: 2026-10-06
tags: [partial, footer, altitude, confidence, judgment]
description: "Closing lines of every Product-contour artifact: the altitude line (v3.5.0) and, where references/judgment-points.md §1 names one, the confidence-and-falsifier line above it (v3.7.0)."
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
  - name: confidence
    type: enum
    required: false
    label: "Confidence in the lead recommendation or verdict"
    options: [known, likely, uncertain, unknown]
    hint: "Since v3.7.0, only where references/judgment-points.md §1 names a confidence line for this skill and mode — derived, never asked; unset → no confidence line. Scale: known ≈ ≥ 0.8 (high) · likely ≈ 0.6 to < 0.8 (medium) · uncertain ≈ < 0.6 (low) · unknown = no number; never above the no-inflation cap (judgment-points.md §3); frontmatter confidence fields keep their own types"
  - name: sensitive_to
    type: string
    required: false
    label: "most sensitive to"
    hint: "The one assumption or input whose change would move the call most — not a list; an assumed or simulated input is named with its class label (judgment-points.md §3)"
  - name: would_change_if
    type: string
    required: false
    label: "would change if"
    hint: "Observable information that would change the call — a metric crossing a value, a segment result, an interview finding, a date; never 'more data'"
---

{{#if confidence}}Confidence: {{confidence}} · most sensitive to: {{sensitive_to}} · would change if: {{would_change_if}}
{{/if}}Altitude: {{altitude}} · ↑ serves: {{serves}} · ↓ next: {{next}}
