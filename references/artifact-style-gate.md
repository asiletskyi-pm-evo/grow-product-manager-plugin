# artifact-style-gate.md

> Shared reference. A quality gate that artifact-producing skills run on a finished draft **before** presenting it to the user (and before creating Jira issues). Born from stakeholder feedback on v2.2.0 artifacts: ungrounded technical content sneaks into business/functional requirements and tasks, and requirements/stages drift into paragraph prose instead of lists. Primary consumers: `requirements-creator`, `task-creator`, `write-concept`. Opt-in: `meeting-processor` and any future artifact skill. Gate 4 reaches every Product-contour artifact through the `template-protocol.md` T-5 self-checks (step 3a footer, step 3c evidence labels).

## When the gate runs

- After the draft is fully generated and **before** the "Review with the user" step (or, for `task-creator`, before the pre-creation summary and after task creation as the Step 12 verification).
- Only on the final draft of an artifact — never on intermediate brainstorm text, clarifying questions, or conversational replies.
- Gates 1–2 and 4 are self-contained checklists. Gate 3 (Team language) additionally has a **pre-generation touch** — the style preamble — because lively text must be born lively; fixing stilted prose post-hoc makes it worse.

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

Apply to every technical statement in the draft: *"Can I point to where this came from — the user, a document, a ticket?"* If not, the statement does not belong in business requirements, functional requirements, or a task body. Drop it, or move it to the AI recommendations block (below) if the user asked for one. A statement that fails the source test is a Gate 1 finding only — Gate 4b does not relabel it as `assumed` to keep it.

### AI recommendations on explicit request only

When the user explicitly asks for technical recommendations ("додай технічні рекомендації", "suggest a technical approach"):

1. Place them in a **separate block titled "Технічні рекомендації (AI)" / "Technical recommendations (AI)"** at the end of the document or task description — never inside the functional requirements table, never inside the task's "How" section.
2. Open the block with a mandatory callout (Confluence: warning panel; Jira/markdown: blockquote), rendered in `user.language`:

   > ⚠️ **Згенеровано ШІ** на основі загальних практик, без валідації з командою розробки. Використовуйте як відправну точку для обговорення, а не як вимоги. Перед взяттям у роботу — перевірити з інженерами.

   English equivalent: *"⚠️ AI-generated from general practices, not validated with the engineering team. Use as a discussion starting point, not as requirements. Verify with engineers before acting on it."*

3. Mark each item's confidence: `general practice` or `assumption from context`. These marks are the block's own; Gate 4b is `n/a` inside it.

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

Candidate terms: offer in one line to add as `status: candidate` to the glossary — never block the flow on it. Replacements never touch text inside quote marks (a verbatim quote), evidence-class words or labels, nor the `Altitude:` / `Confidence:` lines.

### Gate report extension

> "Гейт якості (checker): N виправлень (техвставки: X, формат: Y[, термінологія: Z][, футер: F — only when F > 0][, докази: E — only when E > 0]), спірних: W."

## Gate 4 — Judgment footer and evidence labels (since v3.5.0)

The defect: an artifact that does not say what it serves and what comes next is read at the wrong altitude — a leader reads a delivery slice as strategy, an IC reads a bet as a commitment; and a number or quote without its evidence class lets a guess or a synthetic answer pass for a finding (`pm-mental-model.md` §3: fabricated evidence, synthetic users as findings). Gate 4 grows in three parts; each part is checked only from the version that implements it (`pm-mental-model.md` §5 — a principle acts only through a step that implements it).

| Part | Checks | From |
|------|--------|------|
| **4a — Altitude line** | Only where `template-protocol.md` T-5 step 3a places the line (never on a Jira task body or a task batch, an Analyze & Improve document, a 1-1, a prototype or handoff, a deck for an external audience (outline companion only), a Q&A reply, a search-result list, a quick summary or escape-hatch notes, or a return payload — there 4a is `n/a`): the delivered Product-contour artifact ends with exactly one `Altitude: L1–L4 · ↑ serves: … · ↓ next: …` line, placed per `template-protocol.md` T-5 step 3a (last content before the template marker; closing slide for decks; epic and report for task-creator). `serves` names a product or direction goal, OKR, intent, or parent initiative / epic that the request or the sources explicitly link, or says `— (no linked goal)` — never invented, never a person's goal; `next` is a product or delivery step or `— (no product step)`. (The `Hat: … (profile: …)` line of a hat run is shown in the chat only and is not part of Gate 4a.) | v3.5.0 |
| **4b — Evidence labels** | Every evidence claim carries its class (`pm-mental-model.md` §4) consistent with its source; quotes are verbatim; `simulated` never stands as a finding, `assumed` only labelled — scope, grammar, severity and `n/a` in *Gate 4b* below. | v3.8.0 |
| **4c — Confidence and falsifier** | Only where `judgment-points.md` §1 names a confidence line (elsewhere `n/a`): the lead recommendation or verdict carries exactly one `Confidence: known / likely / uncertain / unknown · most sensitive to: … · would change if: …` line — directly above the altitude line in the footer, or under the Decision section of a decision record. `most sensitive to` is one specific assumption or input; `would change if` is observable information (a metric crossing a value, a segment result, a finding, a date), never "more data"; the level respects the no-inflation cap of `judgment-points.md` §3 (an inconclusive verdict, a ❌ Blocked or not cross-validated metric, or an estimate by analogy → at most `uncertain`); since v3.8.0 a lead recommendation that rests on a claim Gate Check 6 marked as frontier (however rendered) or on a `simulated` input is at most `uncertain` too; in a decision record the owner's level is kept (§6). | v3.7.0 |

Two tiers of execution:

1. **Self-check at T-5 — every Product-contour skill.** Before presenting, the skill confirms the footer — and, since v3.7.0, the confidence line where `judgment-points.md` §1 names one; since v3.8.0 also Gate 4b through `template-protocol.md` T-5 step 3c — and fixes a missing or malformed line or label silently (labels only toward a weaker class); a line in the P3 format (`Confidence: … · most sensitive to: … · would change if: …`) where §1 names none is removed — a skill's own confidence field or label (a hypothesis's Confidence, a research plan's confidence label) stays. Skills that already print a gate report line count it there (`футер: F`, `докази: E`, each shown only when above 0); skills without one print nothing new. The self-checks run on the delivered artifact whether or not Step T ran, and independently of `review_mode`. This is the whole Gate 4 for skills without a maker–checker step (for example product-analysis, cjm-research, product-research).
2. **Checker — where maker–checker already runs** (requirements-creator Step 4.5, write-concept 4.5, task-creator "Batch quality gate before creation", meeting-processor only when its opt-in gate runs). The **form** lens adds Gate 4a — the maker passes `artifact_type` and mode in the checker input, and the checker reports `4a: n/a` wherever step 3a places no line; the **groundedness** lens adds Gate 4b and reports `4b: n/a` per its `n/a` list. There is no third lens. No lens checks 4c: none of these four skills renders a confidence line (`judgment-points.md` §1); decision-log checks its record's line at its own save gate.

People-contour artifacts are out of scope for Gate 4.

### Gate 4b — Evidence labels (since v3.8.0)

**1. Scope.** An *evidence claim* is any of:
- a number stated as what is or was about users, the market, the product or the business;
- a quote;
- a benchmark;
- a "users want X".

Exempt:
- targets, thresholds, decision rules, splits, sample sizes, MDE;
- dates, IDs, versions, plan totals;
- counts of the artifact's own structure — tasks, ideas, sections (counts of evidence items, such as theme counts, are not exempt);
- hypothesis statements;
- Gate 1 process parameters;
- the AI recommendations block;
- forward-looking numbers (`pm-mental-model.md` §4).

**2. Classes and grammar.** The label grammar is `pm-mental-model.md` §4: the class goes first inside the claim's existing annotation, and a group label is allowed only when every claim it covers shares class and source. The full assignment table is `data-integrity-protocol.md` Gate Check 6 (6a); its compact form for a checker that reads only this file:

| Class | Source markers |
|---|---|
| `measured` | `tableau-*`, `internal-live`, `ga-snapshot` — fetched by the skill after its data gate; `csv-upload` raw rows the skill computes on; a count the skill computed from a system of record (Jira counts included) |
| `observed` | `walkthrough-local`, a session recording, a screenshot of the product's own UI |
| `reported` | `user-text`, a prepared report the user hands over (`pdf-upload`, a dashboard or report screenshot), `confluence-internal`, `jira-internal` ticket content, verbatim user research, a Figma / design file or prototype (a claim about users made on it alone is `assumed`), a figure read without a data gate (`· not gate-checked`) — always with who or what |
| `external` | `baymard-premium`, `web-search`, `competitor-website`; a named third-party source cited in user text ("via <who>") |
| `simulated` | persona, synthetic-user or scenario output; an untraceable `deep-research-llm` claim; a knowledge source tagged `model-generated` |
| `assumed` | no resolvable source; a figure given from memory; the planning marker "pending TL / PM confirmation" (`planning-core.md` §6) reads as this label; a frontier claim in a headless run reads `[assumed — frontier: <human step>]` |
| *as the source* | `kb-source` → its knowledge-library type; `landscape:<slug>` → the record's cited source; a traced `deep-research-llm` claim → the traced source; a claim from an earlier plugin artifact → the label it carries (unlabelled → its cited source's class, else `reported`) |

Label forms: the class first inside the existing annotation — `(measured · …)`, `«…» — P3, 12.09 · reported` — or the bracket form `[class: source]` / `[assumed — note]`, or a group label `Evidence: class — source`.

**3. Rules.**
- An unsourced claim is labelled `[assumed — …]`.
- A quote is verbatim or loses its quote marks. Masking personal data as `[name]` / `[order]`, a marked ellipsis `[…]`, and a translation marked `(translated)` with the original kept count as verbatim.
- A label never upgrades the class its source supports, and a label received from upstream is kept.
- `simulated` never stands in a findings or evidence section (by role, not by heading) and is never counted or quoted.
- `assumed` appears in such a section only with its label.

**4. Severity.**
- **Critical:** a fabricated quote or a paraphrase inside quote marks; `simulated` presented as a finding, counted or quoted; an upgraded class; an unlabelled `simulated` claim anywhere; an unlabelled `assumed` claim in a findings or evidence section.
- **Minor:** a sourced claim with no class; an unlabelled `assumed` claim elsewhere; a malformed label.

**5. `n/a`.** Gate 4b does not apply to status boards and registry lists (a board may embed a delivered brief as it was delivered), or to:
- a Jira task body or task batch, an existing epic;
- People-contour artifacts, prototypes and handoffs, a 1-1;
- Q&A replies, search-result lists, quick summaries and escape-hatch notes.

Partial cases (4a's other exclusions — 4b applies in part):
- An Analyze & Improve document gets 4b as advisory findings only, prefixed `advisory:` in the checker output — the user's document is never edited without the existing approval.
- A return payload keeps its labels and is checked in the caller's artifact.
- On a deck for an external audience the class sits in the source caption, internal source names are dropped, and hand-back lines go only to the outline companion.
- A Q&A reply adds no label of its own, but a number it quotes from a labelled artifact keeps that label as written.

**6. Fixes.** The self-check fixes only toward a weaker class — `measured` or `observed` → `reported` (the skill did not read or see it itself) → `assumed` (no resolvable source); `simulated` is never upgraded. It may add to a sourced claim that lost its label the class its source supports (restoring is not an upgrade), and removes the quote marks from a non-verbatim quote. It never restores a label the user removed at the run's review step (a one-off, `self-improvement.md`) — except `simulated` / `assumed`, which stay labelled or the item is dropped, said in one line. Otherwise it:
- it adds `[assumed — …]`;
- it moves `simulated` content out of a findings section;
- it downgrades a label.

It never invents a source and never upgrades a class.

## Execution model: maker–checker

**The agent that produced the artifact does not check its own work.** The same context that generated the text is biased toward justifying its own decisions, so the gate is executed by a separate subagent.

| Role | Who | Does |
|------|-----|------|
| **Maker** | The skill's main flow | Generates the draft; applies fixes |
| **Checker** | A subagent with a fresh context | Runs the gate checklists over the draft; returns structured findings |

**The checker is the plugin agent `grow-product-manager:artifact-checker`** (`agents/artifact-checker.md`, since v2.5.0) — invoked through the Agent tool with `subagent_type: "grow-product-manager:artifact-checker"`. It is defined with `tools: Read` only, so its independence is enforced by the host, not by prose: it cannot browse, write, or spawn. Pass in the prompt exactly the checker input below plus `lens`; it reads this reference itself, so the checklists are never copied into the call.

Resolution order when the named agent is not available in the session: (1) `grow-product-manager:artifact-checker` → (2) a `general-purpose` subagent given the same input and told to read this reference → (3) inline self-check with the reduced-independence marker (see *Limits and fallback*). Steps 2 and 3 are fallbacks, not alternatives — always try 1 first.

**On a host without SUBAGENT** (`host-profiles.md` §1 — Codex CLI by default, ChatGPT) the resolution above lands on level 2, not level 3: the checker runs as **sequential passes in the same session**, one per lens, with a role reset between them — the checker input below is re-stated from scratch and the maker's reasoning is not carried over. Where two lenses are required they therefore run one after the other rather than in parallel. The level is fixed once at Step 0-host and held for the whole run.

### Checker input — and nothing else

The checker receives ONLY: (1) the draft artifact with its `artifact_type` (and, since v3.5.0, `mode` — for Gate 4a / 4b applicability), (2) the list of sources (user statements from the brief, concept, tickets, documents — as content or links; since v3.8.0 each may carry its Gate Check 5 marker, e.g. `user-text`, `tableau-mcp`, `confluence-internal` — a fact, not a class: the checker confirms that no label upgrades what the source shows, infers from the source text when there is no marker, and treats "Sources: none" as every evidence claim being `assumed`), (3) the gate checklists. The checker must NOT see the maker's reasoning or the conversation history — otherwise it inherits the very biases it is meant to catch.

### Checker output

A structured findings list — the checker **reports, it does not rewrite** (two authors would drift the style and structure):

```
{ gate: 0|1|2|3|4a|4b, location: "section / row / task field", finding: "what violates the gate",
  severity: critical|minor, proposed_fix: "one-line suggestion" }
not_applicable: ["4a", "4b"]   # the Gate 4 parts that do not apply to this artifact_type / mode
```

or an explicit "no findings" **per section**. An empty report with no per-section commentary is invalid — the checker must walk every section explicitly.

### Anti-rubber-stamping

The checker prompt is adversarial: "find violations of these checklists"; when uncertain — flag it, do not silently pass. (Same principle as the Debate Mode anti-sycophancy guard.)

### The cycle

maker → checker → maker applies fixes → **one** re-check pass by the checker over the fixed locations only (not the whole document) → present to user. No open-ended loops.

**Disputed findings:** if the maker believes a finding is wrong, it does not silently ignore it — the disputed item is surfaced to the user alongside the draft.

### Escalation for critical artifacts

For artifacts about to be **published** (Confluence page) or **materialized** (Jira issues), use **two checkers with distinct lenses** instead of one:

- **(a) Form lens** — Gate 2 + template-structure conformance + Gate 4a (since v3.5.0);
- **(b) Groundedness/language lens** — Gate 1 + spot-checking claims against the sources + Gate 3 lint findings (terminology and style) + Gate 4b (since v3.8.0).

Two identical checkers add almost nothing over one; distinct perspectives catch distinct failure classes.

### Limits and fallback

- ≤ 2 checkers per artifact; 1 re-check pass.
- Checkers that read Atlassian MCP run **sequentially** (parallel subagents on one Atlassian MCP are known to cross-wire responses).
- If the named agent is unavailable → a `general-purpose` subagent with the same input; if subagents are unavailable at all → inline self-check with an explicit marker in the gate report: **"незалежність перевірки знижена (inline)"** — same pattern as the Debate Mode inline-simulation marker. A `general-purpose` fallback is reported as **"checker: general-purpose"** so the user knows the tool restriction was not enforced.
- **Markers are per level.** Sequential in-session lens passes with a role reset carry **"checker: sequential in-session"** — the check did happen, only its isolation is weaker. The reduced-independence marker **"незалежність перевірки знижена (inline)"** belongs to level 3 alone, where a single self-check runs without a role reset. Do not use the level-3 marker for level 2.

### Configuration

Optional `local-context.md` section (defaults apply when absent):

```markdown
### Artifact Quality Gate
- review_mode: subagent   # subagent (default) | inline | off
```

Gate 3 reads its own keys (`lint_mode`, `style_preamble`) from the **Terminology & Style** section — schema in `skills/plugin-configurator/references/context-schema.md`.

`off` skips the maker–checker (the user opts out) — the T-5 self-checks of Gate 4 still run; `inline` forces the fallback mode without the subagent cost.

### Gate report to the user

One line, attached to the draft presentation:

> "Гейт якості (checker): N виправлень (техвставки: X, формат: Y[, термінологія: Z][, футер: F — only when F > 0][, докази: E — only when E > 0]), спірних: W."

With the inline fallback, append the reduced-independence marker.

## Host write gate (since v2.6.0)

`hooks/hooks.json` registers a PreToolUse hook on `createJiraIssue`, `editJiraIssue`, `createConfluencePage`, `updateConfluencePage` (any connector). Before a content-bearing write the host **asks the user** to confirm, showing a three-point checklist: the gate report line is in the chat, the user has said "publish", the target is not a sandbox. Metadata-only edits pass silently. Consequence for skills: **present the gate report and get the user's go-ahead before the write step**, not after — otherwise the user meets the prompt without the information it asks for. The hook does not read the artifact (a hook sees only the tool call); the gate itself stays in the skill. Opt-out: `/grow-product-manager:setup --write-gate off`.

**On a host without HOOKS** (`host-profiles.md` §1 — Codex CLI, where plugin hooks are not loaded, and ChatGPT) there is no host-side gate at all: the hook is simply absent, and its absence is silent. The skill therefore asks for the confirmation itself, immediately before the write step, showing the same three-point checklist — the gate report line is in the chat, the user has said "publish", the target is not a sandbox. Same decision, one level up: the model asks where the host would have.

## Boundary with Debate Mode

Maker–checker is the light, everyday check of every artifact against fixed checklists. Debate Mode (`references/debate-protocol.md`, D0–D5) is the heavy instrument for contested decisions with conflicting interest groups. The gate neither replaces nor invokes debates.

## Hook snippet for skills

A consuming skill adds one short step before its user-review step:

```
### Step G — Artifact quality gate
Run `references/artifact-style-gate.md` on the draft: spawn `grow-product-manager:artifact-checker`
(one call per lens; two lenses if the artifact will be published or materialized in Jira)
with the draft + source list (each with its Gate Check 5 marker where known) + artifact_type / mode + lens — never this conversation. Apply fixes, surface
disputed findings, include the one-line gate report when presenting the draft.
```
