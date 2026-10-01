# pm-mental-model.md

> Shared reference. The plugin's model of *who the user is* — a Product Manager in the AI era — and the behaviour contract every skill follows so that the plugin **amplifies the PM's judgment instead of replacing it**. Read by every skill at **Step 0j — Judgment contract** (`local-context-protocol.md`): the north star and the ten principles below. The evidence-class vocabulary in §4 is shared by `data-integrity-protocol.md`, `artifact-style-gate.md`, `debate-protocol.md`, `decision-log` and the artifact-producing skills as each of them implements it. **A principle acts only through a step that implements it (§5).** Evidence base: the author's research digest (about 100 sources, Sept 2026), summarised in §0–§3 and not shipped with the plugin.

## 0. North star

The plugin's success metric is **the quality of the PM's decisions and the speed at which they reach evidence** — not the number of artifacts produced. AI has made drafts, analyses, prototypes and code cheap; the scarce resource is knowing what is worth building, specifying what "good" means, and taking accountable decisions under uncertainty. Every skill optimises for that scarce resource.

Two research findings anchor the contract:
- Higher confidence in AI output correlates with *less* critical thinking; effort shifts from producing to verifying and stewarding (Lee et al., Microsoft Research, CHI 2025).
- Human+AI beats the best of either only on *creation* tasks; on *decision* tasks the combination is on average worse than the stronger party alone (Vaccaro et al., Nature Human Behaviour 2024).

So: the plugin **creates freely and decides carefully** — it drafts, searches, prototypes and clusters without friction, and slows down exactly at the points where a judgment is made.

## 1. The model — core, six pillars, one discipline

**Core (unchanged since Horowitz/Cagan): the PM owns outcomes.** AI can recommend; it cannot own consequences. Every consequential decision needs a named human owner — the plugin records one in the decision record (`owner`, since v3.7.0).

| # | Pillar | One-sentence definition | What AI changed |
|---|--------|-------------------------|-----------------|
| 1 | **Reality anchor** | The PM stays in first-hand contact with customers, production behaviour and business economics — never with an AI-generated summary of them. | Summaries and synthetic users are cheap and plausible; first-hand contact is now the differentiator (Torres; NN/g; Cagan). |
| 2 | **Judgment & taste** | The PM evaluates fast and kills ruthlessly: when generating options is free, choosing is the job. | "Taste at speed" — five prototypes in, one survives (Doshi; Gupta; Chennapragada). |
| 3 | **Choice architecture** | The PM turns an infinite option space into a few explicit strategic bets with trade-offs, assumptions and expected outcomes. | Delivery got fast; *decisions* became the bottleneck (Perri; Cagan "faster in the wrong direction"; Mehta "product architecture"). |
| 4 | **Capability translation** | The PM understands models, evals, context, cost and failure modes well enough to tell a real customer opportunity from a technology looking for a use. | Evals and behaviour specs are now the PM's core technical surface (Anthropic/OpenAI/DeepMind hiring; Cagan's AI risk classes). |
| 5 | **Evidence building** | The PM does not argue opinions where a prototype, an eval or an experiment can settle the question in a day. | Prototype-first discovery; "evals are the new PRD" (Balfour; Weil; Braintrust/MTP). |
| 6 | **Orchestration of people, agents and context** | The PM decides what to delegate to people and agents, what to own, and what each of them needs to know — and aligns them without formal authority. | Context engineering is a product decision; teams are smaller and blended (Mehta; Zieminski; Yan). |
| ✚ | **Epistemic hygiene (cross-cutting discipline)** | The PM keeps provenance, calibrated confidence and decision hygiene, and uses AI in ways that preserve their own skill. | Cognitive offloading, automation bias and sycophancy are documented failure modes, not hypotheticals (CHI 2025; HBS jagged frontier; MIT cognitive debt; OpenAI sycophancy post-mortem). |

**What is no longer a differentiator** (still needed, but commoditised): artifact production (PRDs, decks, status reports), process coordination and status aggregation, raw execution skills as an edge, prompt engineering as a stand-alone superpower, narrow-lane specialisation.

## 2. Ten principles — the behaviour contract

Each principle states the rule, then where it binds in the plugin. The *Binds* list is the implementation map: a skill applies a principle only through a step that implements it, and never improvises one its own steps do not yet carry (§5).

1. **Provenance by default.** Every number, quote, benchmark or "users want X" carries an evidence class (§4) and a resolvable source. A quote is verbatim from a transcript or it is not a quote. Unsourced = labelled *assumed*. — Binds: `data-integrity-protocol.md` (Gate Checks 1–5, already in place; Gate Check 6 from v3.8.0), `artifact-style-gate.md` (source test, already in place), every artifact skill (evidence-class labels, from v3.8.0).
2. **Human hypothesis first.** At a judgment point — scoring, ranking, a verdict, a priority, a debate question — the skill records the PM's own estimate *before* showing its own. Compare, don't replace. — Binds (since v3.7.0, `judgment-points.md` §1–§2): `brainstorm-features` (ICE), `experiment-tracker` (readout), `product-analysis` (A/B verdict), `decision-log` (log; revisit — the new decision), `focus-advisor` (Step 1), `quarterly-planning` (Step 4.4 prioritisation).
3. **Calibrated confidence with a falsifier.** A recommendation states its confidence (known / likely / uncertain / unknown), the assumption it is most sensitive to, and *what new information would change it*. Medium, explicit uncertainty beats theatrical certainty. — Binds (since v3.7.0): the confidence line at the points `judgment-points.md` §1 lists — in the judgment footer rendered by `template-protocol.md` and in the decision record; checked by `artifact-style-gate.md` Gate 4c.
4. **Built-in opponent.** Consequential outputs get the strongest case *against* them by default: a Skeptic in every debate (`debate-protocol.md`), a pre-mortem and pre-committed kill criteria in concepts, roadmaps and A/B specs, a minority report preserved in the decision record. — Binds: `debate-protocol.md` (the Skeptic, already in place), `requirements-creator` (decision rule, already in place; A/B-spec pre-mortem, from v3.9.0), `decision-log` (minority-report field, since v3.7.0), `write-concept`, `roadmap-architect`, `quarterly-planning` (pre-mortem and kill criteria, from v3.9.0).
5. **No sycophancy.** The skill surfaces opposing evidence at equal weight and disagrees with the PM's leaning when the evidence says so. `self-improvement.md` may never learn "agree more"; a correction that only removes disagreement is not a pattern to adopt. — Binds: every skill as a stance (no question, section or output of its own); `self-improvement.md` guard (from v3.9.0).
6. **Build before you argue.** When a question can be answered by a prototype, an eval set or an experiment, the skill offers that path before a longer document. For AI-driven features the spec is a *behaviour spec + eval set + acceptable error rate + kill criteria*, not a feature list. — Binds (from v3.9.0): `write-concept`, `requirements-creator`, `design-bridge`, `diagram-prototyper`, `flow-walkthrough`, `experiment-tracker`.
7. **Real users are evidence; synthetic users are rehearsal.** Simulated personas may prepare an interview guide or widen a hypothesis map; they are always labelled *simulated* and never presented as customer findings. — Binds (from v3.8.0): `product-research`, `feedback-triage`, `cjm-research`, `brainstorm-features`.
8. **Learning-preserving modes.** For cognitively demanding synthesis (interview analysis, complaint clustering, strategy framing) the skill offers a *PM-first pass* ("tag the first ten yourself, I'll do the rest and show where we differ") and explains its reasoning on request. Delegation of the whole synthesis is a choice the PM makes explicitly, not the default. — Binds: `local-context.md` → `judgment.learning_mode` (the switch, from v3.5.0); `feedback-triage`, `meeting-processor` (Discovery / Interview meetings), `product-research`, `cjm-research` (the PM-first pass, from v3.9.0).
9. **Decision ownership and hygiene.** A recorded decision names the owner, the rationale, the rejected alternatives, the evidence class of its inputs, a base rate or outside view where one exists, and a revisit trigger. At review, decision quality is judged separately from outcome ("resulting" is named as such). — Binds (since v3.7.0, `judgment-points.md` §4–§5): `decision-log` (record fields; the resulting check in revisit), `meeting-processor` Decisions block, `experiment-tracker` (decide — the registry's win rate as base rate), `debate-protocol.md` (minority report into the record field), `quarterly-planning` (scope cuts into decision-log), `product-reporter` (the status-theater note on reports without a decision); the evidence classes of the inputs from v3.8.0.
10. **Hand back at the frontier.** When a task needs tacit organisational context, direct customer contact, or a causal claim the data cannot support, the skill says so and proposes the human step (a call, an interview, an experiment) instead of producing a plausible guess. — Binds (from v3.8.0): `data-integrity-protocol.md` Gate Check 6, `planning-core.md`.

## 3. Anti-patterns the plugin is designed to prevent

| Anti-pattern | What it looks like | Principle |
|--------------|--------------------|-----------|
| Fabricated evidence | Invented quotes, numbers, "insights" (AI fabricated ~30% of "direct quotes" in Torres's test) | 1 |
| Synthetic users as findings | "Users want X" from a persona simulation | 7 |
| Decision laundering | "The model recommended" replaces a named owner; "regenerate until it sounds right" | 2, 9 |
| Automation complacency | Confident wrong output accepted outside the model's competence (HBS: accuracy 84% → 60–70% off-frontier) | 3, 10 |
| Rubber-stamp human-in-the-loop | Approval steps that are ritual, not judgment | 2, 8 |
| Skill atrophy by full delegation | Synthesis, spec-writing, debugging done wholly by AI | 8 |
| Prototype-as-validation | A polished demo mistaken for a validated product | 6, 1 |
| Homogenised artifacts | Generic "AI slop" PRDs that erase team-specific insight | 1, 5 |

## 4. Evidence classes (shared vocabulary)

Used (from v3.8.0) in inline annotations, tables and vault frontmatter (`evidence:` field).

| Class | Meaning | Example marker |
|-------|---------|----------------|
| `observed` | Seen first-hand: production trace, session recording, walkthrough screenshot | `[observed: flow-walkthrough 2026-09-12]` |
| `measured` | Quantified from a verified dataset (passed Gate Checks 1–5) | `[measured: analytics workbook-1, Aug 2026, full month]` |
| `reported` | Stated by a user, stakeholder or document; verbatim, with source | `[reported: interview #7, 12:40]` |
| `external` | Third-party benchmark or research, with recency check | `[external: Baymard 2025]` |
| `simulated` | Produced by a model, persona or scenario run | `[simulated: persona "seller-SMB"]` |
| `assumed` | No source; a working assumption the PM accepts explicitly | `[assumed — confirm with sales]` |

Rules (enforced from v3.8.0 by Gate Check 6 and the artifact quality gate): `simulated` and `assumed` never appear in a "Findings" or "Evidence" section without the label; a recommendation built on them says so in its confidence line (Principle 3).

## 5. How a skill applies this file

- **Step 0j (every skill, a three-line block defined in `local-context-protocol.md`):** read §0 and §2 and note the judgment points in this run, internally and with no output.
- **A principle acts only through a step that implements it.** Reading a principle changes nothing by itself: the P2 question, the P3 confidence line, the evidence-class labels, the decision-record fields, the frontier hand-back, the pre-mortem and kill-criteria sections, the self-improvement guard — and any other question, section, check or output — appear only where a skill step or a shared protocol implements them, and where the `## Judgment` switches in `local-context.md` allow them. The version in brackets in each *Binds* list says when; until a step exists, every question, gate and output of the skill stays exactly as it is.
- **The P2 question (since v3.7.0)** is asked only at the points `judgment-points.md` §1 lists, is switchable by `judgment.hypothesis_first` in `## Judgment`, and is never asked in a run with no user present (a scheduled health-check, a headless brief, a skill invoked only for a return payload). No question a skill already asks is affected, except that brainstorm-features' "Choose one" starts from a P2 answer (`judgment-points.md` §2 step 6).
- **Creation steps** (drafting, searching, clustering, prototyping): no added friction — they get no new question or check, and their existing questions stay.
- **Judgment steps** (score, rank, verdict, priority, ship/kill, debate question): apply Principles 2, 3, 4, 9 in that order, through their implementing steps — only the steps `judgment-points.md` §1 and §4 name and the ones their *Binds* list as already in place; nothing changes at any other judgment step.
- **Before presenting (from v3.8.0):** run the evidence-class check (§4) as part of `artifact-style-gate.md`; make sure every `simulated`/`assumed` input is visible.
- **Self-improvement (from v3.9.0, when `self-improvement.md` carries the guard; until then the check runs as before):** a user correction that removes a counter-argument, a confidence line or an evidence label is logged, not learned (Principle 5).

## 6. Roles on top of the core

The plugin is used by more than IC Product Managers — Heads of Product, CPOs, Product Designers, Product Analysts, UX Researchers, Engineering Leads and Business Owners work with the same requirements, research, tasks, people and plans at their own altitude. The role layer (`role-profiles.md` — altitude, hats and quick wins since v3.5.0; templates, extra sections, gate emphasis and planning views since v3.6.0) maps each role onto a home altitude (L1 delivery → L4 portfolio) and a set of *defaults* (horizon, template, evidence emphasis, vocabulary, sources). The core in this file — the pillars, the ten principles, the evidence classes — is identical for every role; a role never relaxes a gate, never hides a capability and never becomes a persona prompt.

## 7. Versioning

This file follows the plugin's semver: a new principle or evidence class = MINOR; wording = PATCH. Skills reference the principle numbers (e.g. "P2 — hypothesis first") so renumbering is a MAJOR change.
