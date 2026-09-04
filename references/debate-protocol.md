# debate-protocol.md

> Shared reference. Role-based adversarial debate engine: a skill runs it directly on already-gathered context (hypotheses, research findings, a concept, a pending decision) to break single-agent self-agreement. Same pattern as `subagent-delegation.md` — a shared protocol executed by the calling skill, no separate skill. Primary human entry point: `brainstorm-features` → Step 3D (Debate mode); Debate hooks live in `product-research`, `cjm-research`, `write-concept`, `decision-log`.

## Why this exists

A single brainstorming agent both generates ideas and approves them: trade-offs between interest groups (buyer / seller / business / risk) go unnoticed and ICE Confidence inflates. A structured debate between roles with conflicting mandates surfaces those trade-offs, produces a verdict with an explicit minority report, and calibrates Confidence before anything is committed.

Trigger phrases — EN: "run a debate", "role debate", "red team this idea", "have agents argue / discuss from different roles", "stress-test via debate". UA: «проведи дебати», «нехай агенти подискутують», «розглянь з різних ролей», «red team цю ідею», «круглий стіл ролей».

## Step D0 — Applicability check

Run a debate only when ALL three hold:

1. **The decision is contested** — real trade-offs, not a factual question with one right answer.
2. **≥ 2 interest groups are affected** (e.g., buyers vs sellers, target metric vs UX honesty, speed vs compliance).
3. **An evidence base already exists** — research findings, analysis output, funnel data gathered before the debate.

Do NOT debate: factual questions (research them), routine backlog ranking (ICE/PRO handles it), or topics with no gathered data yet — run `product-research` / `product-analysis` first, then debate. If the check fails, say which criterion failed and route to the right skill instead.

## Step D1 — Setup

**Debate question.** Exactly one, binary or limited-choice: "Should we do X?", "X or Y for goal Z?". Never open-ended ("what do we think about X"). Confirm the wording with the user — a fuzzy question produces a fuzzy verdict.

**Roles.** 3–5 debaters (default 4), chosen via AskUserQuestion from the presets below (multiSelect). The user may describe a custom role ("the seller's chief accountant") — build its card with the same four fields. **The Skeptic / Risk-officer is always included — non-negotiable.** Default quartet: PM-growth + UX advocate + representative of the most affected side (seller or buyer) + Skeptic.

| # | Role | Mandate / maximizes | Typical lenses | Must attack |
|---|------|---------------------|----------------|-------------|
| 1 | **PM-growth** | Business; target metric, GMV | Funnel impact, validation speed, opportunity cost | Ideas without a measurable effect |
| 2 | **UX advocate** | User; interface clarity and honesty | Cognitive load, market patterns, accessibility | Solutions that complicate UI for a metric's sake |
| 3 | **Seller representative** | Supply side; platform fairness | Ranking equality, seller costs, churn risk | Mechanics that discriminate a seller segment |
| 4 | **Buyer representative** | Demand side; value and trust | Expectations, deceptive patterns, NPS | Dark patterns, hidden conditions |
| 5 | **Skeptic / Risk-officer** ⚠️ mandatory | Nobody; hunts failure causes | Measurability, negative side effects, reputation risk | The strongest "for" argument |
| 6 | **Tech lead** | Feasibility | Complexity, dependencies, performance, maintainability | Underestimated effort |
| 7 | **Analyst** | Measurability | MDE, A/B duration, metric contamination | Hypotheses that cannot be measured correctly |
| 8 | **Finance** | Unit economics | ROI/PRO, cannibalization, cost of capital | Effects without a monetary estimate |
| 9 | **Legal / compliance** | Legal boundaries | Consumer-credit advertising rules, consumer protection, regulation | Solutions in a legal grey zone |
| 10 | **Support / ops** | Operational consequences | Tickets, edge cases, support load | Ideas that generate complaint streams |

**Evidence pack.** Numbered facts `E1…En` taken ONLY from research/analysis already performed in this session or loaded from the vault — and, where the source skill applies it, only data that passed the Data Integrity Gate (`references/data-integrity-protocol.md`). Everything else enters as explicitly marked assumptions `A1…An`. The pack is the debaters' ONLY source of facts. Show the pack to the user before Round 1 and let them add or strike items.

## Step D2 — Round 1: parallel opening positions

One subagent per role, all spawned in a single parallel dispatch. **Each debater is the plugin agent `grow-product-manager:debater`** (`agents/debater.md`, since v2.5.0) — Agent tool with `subagent_type: "grow-product-manager:debater"`. It is defined with `tools: []`, so the "no web, no vault, no files" guardrail is enforced by the host. Each receives its role card + the debate question + the full evidence pack + `round: 1` — and nothing else (no other roles' output). If the named agent is not available, spawn `general-purpose` with the same prompt and note **"debater: general-purpose (tool restriction not enforced)"** in the report; if no subagents at all — inline simulation (see Guardrails).

Subagent prompt template:

```
You are {role}. Mandate: {mandate}. You maximize: {maximizes}. Lenses: {lenses}.
Debate question: {question}
Evidence pack — your ONLY source of facts:
{E1…En}
Marked assumptions: {A1…An}
Rules: argue strictly from your mandate; cite E# or A# for every argument;
do not invent facts — a missing fact becomes an "open question"; do not
seek consensus with anyone.
Return exactly this structure, compact:
Position: for / against / conditionally-for (conditions)
Top-3 arguments: each with its E# / A# reference
Main risk I see: …
What would change my position: …
```

Guardrail: debater subagents do NOT gather new data — no web, no vault, no files. A fact the pack lacks is stated as an open question, never fabricated.

## Step D3 — Round 2: cross-examination

Each role receives all other roles' opening positions and must, again in one parallel dispatch:

- **(a)** attack the opponents' single strongest argument;
- **(b)** defend its own most vulnerable argument;
- **(c)** state whether its position shifted and why — citing the exact argument or E#/A# that moved it.

**Round 3** — considered only if ≥ 2 roles materially shifted position in Round 2 (flipped for↔against, or added/removed conditions). When that condition is met, ASK the user via AskUserQuestion: run Round 3 or go to synthesis. Hard maximum: 3 rounds, no exceptions.

## Step D4 — Facilitator synthesis (main agent)

The main agent — the one that spawned the debaters — synthesizes:

- **Consensus points** — what ALL roles agreed on.
- **Live disagreements** — what stays unresolved and why (missing data? conflicting values?). Missing-data items become open questions / research tasks.
- **Position shifts** — who moved, under pressure of which argument. This is the most valuable signal of the whole debate — record it explicitly.
- **Verdict** — recommendation + facilitator confidence (high / medium / low).
- **Minority report** — the dissenting role ALWAYS gets 2–3 sentences in the final artifact, even (especially) when overruled.
- **ICE Confidence correction** for the affected hypotheses:
  - all roles converge in support → Confidence **+1…+2**;
  - the Skeptic's objection stays unresolved → Confidence **−1…−2**;
  - new risks surfaced by the debate → append to the hypothesis's Risks field.

Validity check before synthesis: every role attacked at least one opposing argument in Round 2. A role that only agreed gets its round returned and re-run once (see Guardrails).

## Step D5 — Output & save

**Artifact.** A «Debates» section embedded in the parent document (research report, brainstorm output, concept, ADR): round transcripts inside collapsed expand-blocks; the verdict table open:

| Question | Roles | Verdict | Confidence | Minority report | ICE corrections |
|----------|-------|---------|------------|-----------------|-----------------|

A standalone page only when the user asks for one.

**Vault** (only IF vault_level > L0 AND sync_mode != "off" — standard gate):

```
vault_save({
  type: "debate",
  product: active_product,
  skill: <calling skill>,
  tags: [topic keywords, role names],
  content: full «Debates» section (rounds + synthesis),
  related: [affected hypotheses, source research/analysis, resulting decision],
  extra_frontmatter: { debate_question, roles, verdict, confidence,
                       minority_report, rounds, inline_simulation }
})
```

Saved under `Debates/{product}/` per `references/vault-schema.md`.

**Chains — always offer:**
- "Record the verdict as a decision?" → `decision-log` (the ADR inherits the verdict + minority report).
- "Register the winning hypotheses?" → `experiment-tracker` (register mode, state `proposed`).

## Guardrails

- **Anti-sycophancy:** roles are forbidden to converge before Round 2. The facilitator verifies every role attacked at least one opposing argument in Round 2 — otherwise that role's round is returned and re-run (once per role, within the cost cap).
- **No new facts:** only the evidence pack; anything beyond it must be a marked assumption A#. Debaters get no web, vault, or file access.
- **Data policy:** debaters are local subagents without web access — internal data never leaves the session (`references/data-policy.md`).
- **Cost cap:** default 4 roles × 2 rounds = 8 subagent calls; hard cap **12** total (covers 4×3 rounds, or 5 roles × 2 + re-runs). Responses are compact structured payloads per `subagent-delegation.md`, never free-form essays.
- **Mid-debate role addition:** if an affected interest group turns out uncovered, the facilitator MAY add exactly **one** role mid-debate — with the user's confirmation and within the cost cap. The new role receives the evidence pack + all prior rounds' outputs and joins the current round.
- **Fallback chain:** `grow-product-manager:debater` → `general-purpose` with the same prompt (report notes the unenforced restriction) → inline simulation. **Fallback without the Agent tool:** inline simulation — the main agent plays the roles sequentially in one context, same prompts, same response formats, same caps. The report MUST carry the visible note **"inline simulation: role independence reduced"** and the vault frontmatter MUST set `inline_simulation: true`.
