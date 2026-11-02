---
kind: provider-file
file: tools.yaml
---
# Tools list — `tools.yaml`

A copy of `tools.yaml` beside it, for a notes server that serves `.md` only: a colleague's plugin unpacks this block into its own copy of the core (references/context-provider-protocol.md §9, references/tool-registry.md §5). Keep the two equal — `ctx repo kit-check` checks it.

```yaml
# The tools list of the Zorg team (references/tool-registry.md §5): what colleagues use and recommend.
# The core's owner adds it from the exports colleagues send; the plugin reads it, never writes it.
# Everything here is fictional: Zorg is the plugin's example company.
tools:
  - name: "Zorg Board"
    kind: "mcp"
    job: "the team's whiteboard for discovery maps"
    skills: ["diagram-prototyper", "brainstorm-features"]
    access: "corporate"
    connect: "ask the core owner for the server entry"
    verdict: "recommended"
    recommended_by: "Pat Moss"
    publishes: "board"
  - name: "Zorg Research Notes"
    kind: "site"
    job: "the team's interview notes portal"
    skills: ["product-research"]
    access: "corporate"
    connect: "open it in the browser with the work account"
    recommended_by: "Ana Lyst"
```
