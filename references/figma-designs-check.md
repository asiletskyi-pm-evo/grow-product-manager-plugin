# figma-designs-check.md

> Shared reference. The "Figma designs check" that artifact skills run when the work touches a product or feature that already exists. The calling skill keeps two lines of its own next to the pointer: what the designs are **used as context for**, and **where confirmed designs go** in its output. Callers: `write-concept`, `requirements-creator`, `brainstorm-features`, `product-research`.

## When it runs

Only when the product, feature or UI/UX being worked on already exists — not when it is built from scratch. The calling skill states its own trigger in the line that points here.

## Procedure

Ask via AskUserQuestion:

> "Are there current designs / mockups / prototypes of this functionality in Figma?"

- **If the user provides a link** — open it via Figma MCP (`get_design_context`, `get_screenshot`) or browser fallback, read and extract: current UX flows, screens, key UI patterns. Use this as context for the calling skill's work (its *use as context for* line).
- **If the user believes designs should exist but cannot provide a link** — offer to search:
  > "I can search for relevant mockups in Figma from your account. Would you like me to search?"
  - If agreed — search via Figma MCP or browser (`https://www.figma.com`):
    - Try to understand the structure of the design system: look for sections like "Current design", "Production", "Live", "Ready for dev", "Latest state"
    - Show the user the found files/frames and ask them to confirm which are relevant and up-to-date
  - If Figma MCP is unavailable — follow `references/integration-strategy.md` fallback chain
- **If no designs exist** — note this and proceed without design context
- **If relevant designs are confirmed** — use them as the calling skill's *when designs are confirmed* line says.

**Evidence class (since v3.8.0).** A design describes the intended UI — even a frame marked "Production" or "Live". A claim drawn from it is `reported` with the file and frame as its source (`pm-mental-model.md` §4), never `observed` product or user behaviour; for what users actually see or do, cite production data, a `flow-walkthrough` evidence pack or a screenshot of the live product.
