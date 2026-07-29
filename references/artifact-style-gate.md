# artifact-style-gate.md

> Shared reference. A quality gate that artifact-producing skills run on a finished draft **before** presenting it to the user (and before creating Jira issues). Born from stakeholder feedback on v2.2.0 artifacts: ungrounded technical content sneaks into business/functional requirements and tasks, and requirements/stages drift into paragraph prose instead of lists. Primary consumers: `requirements-creator`, `task-creator`, `write-concept`. Opt-in: `meeting-processor` and any future artifact skill.

## When the gate runs

- After the draft is fully generated and **before** the "Review with the user" step (or, for `task-creator`, before the pre-creation summary and after task creation as the Step 12 verification).
- Only on the final draft of an artifact — never on intermediate brainstorm text, clarifying questions, or conversational replies.
- Gates 1–2 are self-contained checklists. Gate 3 (Team language) additionally has a **pre-generation touch** — the style preamble — because lively text must be born lively; fixing stilted prose post-hoc makes it worse.

---

## Gate 1 — Ungrounded technical content

The defect: AI-invented technical decisions land inside business/functional requirements and task bodies, and the team burns time analyzing content nobody asked for.

### Classification

| Category | Examples | Policy |
|----------|----------|--------|
| **Process parameters** | feature flag / A/B / A/B/C choice, platforms, locales, Epic numbering | Always allowed — these are user-confirmed workflow parameters (e.g. requirements-creator Step 3) |
| **Sourced technical facts** | constraints, system names, existing APIs — stated by the user or present in the concept / ticket / linked document | Allowed, with the source identifiable |
| **AI technical assumptions** | technology/library choices, API and data-schema design, architecture decisions, complexity/effort estimates, engineering implementation steps | **Prohibited by default** |

### The source test

Apply to every technical statement in the draft: *"Can I point to where this came from — the user, a document, a ticket?"* If not, the statement does not belong in business requirements, functional requirements, or a task body. Drop it, or move it to the AI recommendations block (below) if the user asked for one.

### AI recommendations on explicit request only

When the user explicitly asks for technical recommendations ("додай технічні рекомендації", "suggest a technical approach"):

1. Place them in a **separate block titled "Технічні рекомендації (AI)" / "Technical recommendations (AI)"** at the end of the document or task description — never inside the functional requirements table, never inside the task's "How" section.
2. Open the block with a mandatory callout (Confluence: warning panel; Jira/markdown: blockquote), rendered in `user.language`:

   > ⚠️ **Згенеровано ШІ** на основі загальних практик, без валідації з командою розробки. Використовуйте як відправну точку для обговорення, а не як вимоги. Перед взяттям у роботу — перевірити з інженерами.

   English equivalent: *"⚠️ AI-generated from general practices, not validated with the engineering team. Use as a discussion starting point, not as requirements. Verify with engineers before acting on it."*

3. Mark each item's confidence: `general practice` or `assumption from context`.

---

## Gate 2 — Lists over prose

The defect: requirements and stages written as paragraph prose are hard to scan and hide individual requirements.

### Structure rule

Any sequence — steps, stages, requirements, criteria, changes, risks, options — is formatted as a numbered/bulleted list or a table. Never as a paragraph.

Paragraphs are allowed only for context, motivation, and conclusions — at most 3–4 sentences in a row.

### Prose-enumeration markers (found one → rewrite as a list)

- "first…, then…, after which…" / "спочатку…, потім…, після чого…" constructions;
- three or more comma-separated items in one sentence where each item is a distinct requirement/step;
- a single sentence carrying a condition, an action, and an exception at once.

---

## Gate 3 — Team language (terminology + style) — since v2.4.0

The defect: AI-generated text reads stilted and uses terms the team does not use, causing misunderstandings in decks, concepts, requirements, and tasks. The cure lives in `knowledge-library` (glossary + style profile); this gate wires it into every artifact. Both parts degrade gracefully: no glossary and no style profile configured → Gate 3 silently skips.

### 3a. Style preamble — BEFORE generation (maker side)

Before the maker starts writing the artifact, load the product's style profile (`~/.grow-pm/knowledge-library/style/{product_id}.md`, falling back to `style/_org.md`) and follow it while writing: tone and register, syntax rules, do/don't list, and — most powerful — imitate the reference fragments (few-shot). Controlled by `style_preamble: on|off` in the Terminology & Style config (default `on` when a profile exists).

### 3b. Terminology + style lint — AFTER generation (checker side)

After Gates 1–2, if the product glossary exists and is non-empty, call `knowledge-library` **Glossary Lint** (service mode) with the draft text. The lint returns: replacements (`avoid` → canonical term; dead-phrase → living phrase), style-profile deviations, and candidate terms (frequent terms in the draft that are absent from the glossary). These findings merge into the **groundedness/language checker lens** report — no separate agent.

Apply replacements per `lint_mode` from the Terminology & Style config:

- `suggest` (default) — show the replacement list to the user, apply the confirmed ones;
- `auto` — apply silently, report the count in the gate report line;
- `off` — skip the lint.

Candidate terms: offer in one line to add as `status: candidate` to the glossary — never block the flow on it.

### Gate report extension

> "Гейт якості (checker): N виправлень (техвставки: X, формат: Y, термінологія: Z), спірних: W."

## Execution model: maker–checker

**The agent that produced the artifact does not check its own work.** The same context that generated the text is biased toward justifying its own decisions, so the gate is executed by a separate subagent.

| Role | Who | Does |
|------|-----|------|
| **Maker** | The skill's main flow | Generates the draft; applies fixes |
| **Checker** | A subagent with a fresh context | Runs the gate checklists over the draft; returns structured findings |

### Checker input — and nothing else

The checker receives ONLY: (1) the draft artifact, (2) the list of sources (user statements from the brief, concept, tickets, documents — as content or links), (3) the gate checklists. The checker must NOT see the maker's reasoning or the conversation history — otherwise it inherits the very biases it is meant to catch.

### Checker output

A structured findings list — the checker **reports, it does not rewrite** (two authors would drift the style and structure):

```
{ gate: 1|2, location: "section / row / task field", finding: "what violates the gate",
  severity: critical|minor, proposed_fix: "one-line suggestion" }
```

or an explicit "no findings" **per section**. An empty report with no per-section commentary is invalid — the checker must walk every section explicitly.

### Anti-rubber-stamping

The checker prompt is adversarial: "find violations of these checklists"; when uncertain — flag it, do not silently pass. (Same principle as the Debate Mode anti-sycophancy guard.)

### The cycle

maker → checker → maker applies fixes → **one** re-check pass by the checker over the fixed locations only (not the whole document) → present to user. No open-ended loops.

**Disputed findings:** if the maker believes a finding is wrong, it does not silently ignore it — the disputed item is surfaced to the user alongside the draft.

### Escalation for critical artifacts

For artifacts about to be **published** (Confluence page) or **materialized** (Jira issues), use **two checkers with distinct lenses** instead of one:

- **(a) Form lens** — Gate 2 + template-structure conformance;
- **(b) Groundedness/language lens** — Gate 1 + spot-checking claims against the sources + Gate 3 lint findings (terminology and style).

Two identical checkers add almost nothing over one; distinct perspectives catch distinct failure classes.

### Limits and fallback

- ≤ 2 checkers per artifact; 1 re-check pass.
- Checkers that read Atlassian MCP run **sequentially** (parallel subagents on one Atlassian MCP are known to cross-wire responses).
- If subagents are unavailable → inline self-check with an explicit marker in the gate report: **"незалежність перевірки знижена (inline)"** — same pattern as the Debate Mode inline-simulation marker.

### Configuration

Optional `local-context.md` section (defaults apply when absent):

```markdown
### Artifact Quality Gate
- review_mode: subagent   # subagent (default) | inline | off
```

Gate 3 reads its own keys (`lint_mode`, `style_preamble`) from the **Terminology & Style** section — schema in `skills/plugin-configurator/references/context-schema.md`.

`off` skips the gate entirely (the user opts out); `inline` forces the fallback mode without the subagent cost.

### Gate report to the user

One line, attached to the draft presentation:

> "Гейт якості (checker): N виправлень (техвставки: X, формат: Y), спірних: Z."

With the inline fallback, append the reduced-independence marker.

## Boundary with Debate Mode

Maker–checker is the light, everyday check of every artifact against fixed checklists. Debate Mode (`references/debate-protocol.md`, D0–D5) is the heavy instrument for contested decisions with conflicting interest groups. The gate neither replaces nor invokes debates.

## Hook snippet for skills

A consuming skill adds one short step before its user-review step:

```
### Step G — Artifact quality gate
Run `references/artifact-style-gate.md` on the draft (maker–checker; two lenses if the
artifact will be published or materialized in Jira). Apply fixes, surface disputed
findings, include the one-line gate report when presenting the draft.
```
