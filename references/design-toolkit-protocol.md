# Design Toolkit Provider Protocol

This document defines how the Grow PM plugin delegates **hi-fi design / prototype / screen-generation** work to an **external design toolkit** — a separate, org-specific solution (another plugin, an MCP server, a CLI, or a web app) that is better at code-first, design-system-native screen production than the plugin's built-in path.

The plugin ships **no** reference to any concrete toolkit. Every toolkit is declared by the user in `local-context.md`. Grow PM stays universal: one company plugs in one toolkit, another company plugs in a different one, and the plugin core never changes. This mirrors `integration-strategy.md` (MCP → Registry → Browser) — the same idea, applied to design toolkits, one tier earlier.

> **Ownership:** `design-bridge` is the single **routing host** for design/prototype delegation. Other Grow PM skills (`brainstorm-features`, `cjm-research`, `write-concept`, `requirements-creator`, `product-research`, `meeting-processor`) never call a toolkit directly — they hand the design/prototype step to `design-bridge`, which applies this protocol.

---

## 1. Config schema — `design_toolkits[]` in local-context.md

A product (or the global `user` block) may declare zero or more toolkits:

```yaml
design_toolkits:
  - id: <slug>                     # stable identifier, e.g. "my-design-toolkit"
    label: <human name>            # shown to the user in prompts
    entry:
      type: skill | mcp_tool | command | browser
      ref: <invocation reference>  # see §4 per type
    capabilities: [<capability>, ...]   # see §3
    scope: [<free tags>]           # org-specific applicability, e.g. [mobile, prom-b2c]
    input_contract:                # what Grow PM passes in — see §5
      feature_name: required
      platform: [<options>]
      requirements_doc: optional
      jira_key: optional
    returns: [<artifact ref>, ...] # what the toolkit hands back — see §5
    setup_hint: <ref>              # optional: how to (re)configure the toolkit
    data_locality: local | external   # for data-policy.md — default: external
    contract_version: <semver>     # version of THIS protocol the toolkit targets
```

Only `id`, `entry`, and `capabilities` are required. Everything else has safe defaults. If `design_toolkits` is absent or empty, Grow PM behaves exactly as before this protocol existed (zero regression).

---

## 2. Routing — the tier-0 fallback

Before running any built-in hi-fi path, `design-bridge` runs a **provider check** as tier-0 of the integration chain:

```
Need a hi-fi prototype / design screen
    │
    ├─ tier-0: does any design_toolkits[] entry cover the requested capability?
    │     ├─ YES → confirm with the user → delegate via entry (§4)
    │     │        with an input payload (§5) → ingest returns (§5) → publish/link/vault
    │     └─ NO ↓
    │
    ├─ tier-1..3 (integration-strategy.md): Figma MCP → Registry → Browser  [unchanged]
    │
    └─ lo-fi / quick / local visuals → diagram-prototyper  [unchanged]
```

**Match rule:** a toolkit "covers" a request when its `capabilities` include every capability the request needs (request capabilities are derived from `intent` + `fidelity`, see §6). If two toolkits match, ask the user which to use.

**User confirmation is mandatory** before delegating — never hand a task to an external toolkit silently. If the user declines, fall back to tier-1.

---

## 3. Capability vocabulary — core enum + custom

Grow PM recognises a fixed **core enum**. Toolkits may also declare **custom** capabilities (any string not in the enum) — Grow PM treats those as opaque tags: they never trigger built-in routing on their own, but the user may reference them explicitly ("use <toolkit> for X").

**Core enum:**

| Capability | Meaning |
|---|---|
| `hi-fi-prototype` | Production-grade screen/prototype, beyond lo-fi/mid-fi |
| `screen-generation` | Generates full screens (not single diagrams) |
| `ds-tokens` | Builds on real design-system tokens/components |
| `figma-write` | Writes the result into Figma |
| `code-first-research` | Research grounded in the product's real code |
| `design-review` | Owns platform-aware QA (a11y, touch targets, guidelines) |

**Custom example:** `capabilities: [hi-fi-prototype, ds-tokens, mobbin-benchmark]` — `mobbin-benchmark` is custom; it won't auto-route but is discoverable to the user.

Routing decisions (§2, §6) consider **only core-enum** capabilities.

---

## 4. Entry types — how Grow PM invokes a toolkit

| `entry.type` | `entry.ref` example | How `design-bridge` invokes it |
|---|---|---|
| `skill` | `"some-plugin:flow"` | Skill tool, by name. For co-installed sibling plugins. |
| `mcp_tool` | `"mcp__<id>__<tool>"` | Call the MCP tool with the payload as arguments. |
| `command` | `"designgen --brief {brief_path}"` | Run via bash; pass the payload as a file/args. |
| `browser` | `"https://toolkit.example.com"` | Claude in Chrome — navigate + drive the web UI. |

If the declared entry is unavailable at runtime (skill not installed, MCP disconnected, command missing, site unreachable) → note it, offer `setup_hint`, and fall back to tier-1. Never hard-fail the whole task.

---

## 5. Delegation contract (bidirectional)

**Grow PM → toolkit** (built from `input_contract`):

| Field | Meaning |
|---|---|
| `feature_name` | Short name of the feature/screen |
| `platform` | iOS / Android / both / web (per toolkit's options) |
| `requirements_doc` | Live session context OR a file path the toolkit reads |
| `jira_key` | Optional ticket key for traceability |

These are exactly the artifacts Grow PM already produces (`requirements-creator`, `cjm-research`, `brainstorm-features`, `write-concept`). A conforming toolkit must also work with an **empty** payload (self-sufficient — research from scratch).

**Toolkit → Grow PM** (declared in `returns`):

| Return | Grow PM does with it |
|---|---|
| `figma_url` | Link from concept/requirements; embed screenshot if allowed |
| `branch` | Record in the artifact frontmatter for traceability |
| `files` | Reference paths; attach where relevant |

`design-bridge` ingests these in its publish/link step and vault save (§ vault below).

---

## 6. Request → capability mapping (for design-bridge)

| design-bridge request | Required core capabilities | Routing |
|---|---|---|
| `intent=prototype, fidelity=hi-fi` | `hi-fi-prototype` (+ `ds-tokens` preferred) | tier-0 if covered, else Figma path |
| `intent=prototype, fidelity=lo-fi/mid-fi` | — | built-in (diagram-prototyper / HTML) |
| `intent=handoff`, Q4a = "generate the screens" | `screen-generation` | tier-0 if covered, else `design:design-handoff` |
| `intent=handoff`, Q4a = "document existing designs" | — | built-in (`design:design-handoff`) |
| any of the above **and** the user wants the result landed in Figma | `+ figma-write` | tier-0 if covered, else Grow PM's own `use_figma` path (Full seat) |
| `intent=research-enrichment` on an existing codebase | `code-first-research` | tier-0 if covered, else `design:research-synthesis` (docs/web only) |
| `intent=deck` | — | built-in (no toolkit delegation) |

> Every core-enum capability must appear in this table, or it is unreachable: a toolkit could declare it and nothing would ever ask for it. `figma-write` and `code-first-research` were declared in §3 but absent here until v2.1.0 — §3's "the user may reference them explicitly" escape covers only *custom* capabilities, so those two had no route at all.

---

## 7. QA ownership (no double work)

When a task is delegated to a toolkit that declares `design-review`, `design-bridge` **must not** re-run its own a11y / design-system checks (Step 4d/4e) on the toolkit's output — the toolkit owns generation and its own review. Grow PM keeps ownership of **upstream** (requirements/research) and **downstream** (publish, link, vault). If the toolkit does **not** declare `design-review`, Grow PM's Step 6 QA gate still applies to whatever artifact came back.

---

## 8. Vault save

Delegated results are saved using the **existing** vault types `prototype` / `handoff` (no new artifact type), with a marker so they are distinguishable:

```
extra_frontmatter:
  design_delivery: true
  toolkit_id: <id>
  toolkit_returns: [figma_url, branch, files]
```

See `vault-schema.md`.

---

## 9. Data policy

If `data_locality: external`, the toolkit is a third party — `data-policy.md` applies: do not pass confidential internal data (Tableau numbers, internal URLs, trade secrets) into the payload beyond what the policy allows. If `data_locality: local` (co-installed skill running in the same session, e.g. a sibling plugin), data stays in-session and the payload may include internal context.

---

## 10. Contract versioning

`contract_version` in a toolkit entry states which version of **this** protocol the toolkit was built against. Grow PM supports the current major and warns (does not block) on a mismatch:

> "Toolkit <id> targets protocol vX.Y; this plugin implements vA.B. Delegating anyway — verify the payload/return shape."

This protocol starts at **v1.0**. Breaking changes to the schema or contract bump the major.

---

## 11. Universality guard

The plugin repository must contain **no** reference to any concrete toolkit. Only generic examples (in `local-context.example.md`) are allowed. CI/`grep` check: `grep -ri "<any concrete toolkit name>" skills/ references/` → must be empty. Concrete toolkits live **only** in the user's `local-context.md`.
