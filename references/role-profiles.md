# role-profiles.md

> Shared reference. The plugin's **role layer**: who is using it (an IC Product Manager, a product leader, a designer, an analyst, a researcher, an engineering lead, a business owner) and how that changes *defaults* — altitude, horizon, artifact templates, evidence emphasis, vocabulary, data sources — while the **core stays the Product Manager model** (`pm-mental-model.md`) and every skill, gate and protocol stays the same for everyone. Consumed by `local-context-protocol.md` (Step 0i), `template-protocol.md` (judgment footer; template ranking and extra sections since v3.6.0), `planning-core.md` (altitude views, since v3.6.0), `data-integrity-protocol.md` (gate emphasis, since v3.6.0), `artifact-style-gate.md` (Gate 4a), `plugin-configurator` (User Profile step) and every skill's Step 0. Like the principles, **a role field acts only through a step that implements it** — the version in brackets in §5 says when; until then the field is resolved and carried, and changes nothing.

## 0. The one rule

**Role changes defaults, never capabilities.** Same skills, same gates, same routing, same decision-record format, same ten principles for everyone. A role sets where a run *starts* — its altitude (since v3.5.0), its horizon, template, sources and vocabulary (since v3.6.0) — and which evidence gate is stricter (since v3.6.0). Nothing is hidden behind a role, and no role ever relaxes a gate. Role is never injected as a persona prompt ("You are a CPO…") — persona prompting does not improve quality and shifts judgment unpredictably (Zheng et al. 2023; PLOS One 2025); altitude + evidence + template do the work. `testing/skill_lint.py` enforces both halves: check 19 `role-branching` (no skill branches on a role name) and check 20 `persona-prompt`.

## 1. Altitude model (levels of abstraction)

A delivered Product-contour artifact ends with an **altitude line** wherever `template-protocol.md` T-5 step 3a places it (from v3.5.0; rendered by `templates/built-in/partial/judgment-footer-v1.md`). Roles map onto a *home altitude* plus a *reach*; the request can move the run to any altitude L1–L4 ("infer altitude from the request, not from the role"); the reach is informational and never clamps it. Altitude L1–L4 is **not** the vault level L0–L2 (`vault_level`, `vault-protocol.md`) — the two scales never mix.

| Altitude | Horizon | Unit of work | Decision type | Evidence that counts most |
|----------|---------|--------------|---------------|---------------------------|
| **L4 Portfolio / vision** | 2–5 y | vision, strategic bets, product lines, funding, org design | where to play, what to stop, investment allocation | market, margin/P&L, portfolio scorecard, hard-to-copy advantage |
| **L3 Product strategy** | 1–3 y; annual/quarterly cycle | strategic intents, product OKRs, roadmap "Later" | which problems, proxy metrics, resourcing | product scorecard, trends, competitive/market research |
| **L2 Initiative / discovery** | 1–2 quarters | opportunities, initiatives, team OKRs, roadmap "Next" | which opportunity/solution, go/no-go, experiment design | research synthesis, CJM/funnel data, A/B readouts, feedback themes |
| **L1 Delivery / solution** | sprint–month | epics, stories, specs, prototypes, tests, roadmap "Now" | scope, sequencing, ship/hold | usage/adoption metrics, QA, usability findings, ticket evidence |

Rules of altitude: detail decreases as altitude rises (Now/Next/Later — applied by the planning suite, `planning-core.md` §7); alignment is bidirectional (teams derive from strategy, leaders review for intelligence, not approval); the altitude line — `Altitude: L2 · ↑ serves: <OKR / intent> · ↓ next: <concrete step>` — lets a CPO and an IC PM read the same artifact.

## 2. Role profiles

`user.role` enum: `pm` · `head_of_product` · `cpo` · `product_designer` · `product_analyst` · `ux_researcher` · `eng_lead` · `business_owner` · `other` (free text kept in `user.role_label`, treated as `pm`).

| Role | Home / reach | Default horizon | Unit of work | Default artifacts (type/subtype) | Evidence emphasis (gate stricter on) | Vocabulary & sources |
|------|--------------|-----------------|--------------|-----------------------------------------------|---------------------------------------------------|----------------------|
| **pm** (core) | L2 / L1–L3 | quarter | initiative → spec → experiment | — (each skill's own defaults, as in v3.5.0) | — (the baseline Gate Checks 1–5) | JTBD, hypothesis, ICE, CR, readout; Jira, analytics dashboards, Confluence, feedback |
| **head_of_product** | L3 / L2–L4 | quarter–year | team objectives, domain strategy, PM development | concept/strategy-memo, ops-report/quarter-review, goal-letter, performance-review | `comparability`, `trend-vs-objective` | objectives not features, team topology, competencies, coaching; Jira plans, OKR store, people profiles |
| **cpo** | L4 / L3–L4 | year–3 y | portfolio of bets, org, P&L | concept/strategy-memo, concept/decision-memo, ops-report/board-update | `market-recency`, `base-rates` | bets, investment/return, kill criteria, stage (explore/expand/extract), AI strategy; finance, market, board context |
| **product_designer** | L1 / L1–L2 | 1–2 sprints + discovery loop | brief → explorations → prototype → usability round → handoff | concept/design-brief, research/research-plan, research/insight-report, presentation/feature | `triangulation` (n of real users, method; synthetic = hypothesis only) | flows, states (empty/error/loading), DS components/tokens, a11y, copy; Figma, DS, session replays, usability tests |
| **product_analyst** | L2 evidence layer / L1–L3 | days–experiment cycle | analysis request → insight memo; experiment spec → readout | presentation/ab-test-readout, research/insight-memo (by explicit request); requirements with partial/tracking-plan (A/B specs through the skill's own ab-test inference) | `instrumentation`, `srm-exposure-peeking`, `ci-vs-point` | metric dictionary, cohorts, guardrails, MDE, causal vs correlational; warehouse/semantic layer, dashboards, experiment platform |
| **ux_researcher** | L2 / L1–L3 | study = 1–4 weeks | plan → guide → sessions → synthesis → readout | research/research-plan, research/discussion-guide, research/insight-report, partial/repository-entry | `triangulation`, `human-validated` | study, participants, method, confidence, screener, repository tags; transcripts, repository, NPS/analytics for triangulation |
| **eng_lead** | L1 / L1–L2 | sprint–quarter | epic → tech design → tasks; capacity plan | requirements/default (+ partial/nfr), task/default, ops-report/sprint-plan; ADR *offered, never filled as PM* | `spec-readiness`, `nfr-present` | capacity, throughput, DORA four keys, rework, tech-debt %, NFR, ADR, evals as acceptance; Jira, CI, incidents |
| **business_owner** | L3 / L3–L4 | month–quarter–year | bet with business case; 3–5 binding decisions per quarter | concept/business-case, concept/decision-memo, ops-report/qbr, ops-report/board-update | `money-bridge`, `hippo-check` | P&L, targets, unit economics, invest/continue/kill; finance, pipeline, market |

**Gate-emphasis tokens** (closed list; each maps to one extra check in `data-integrity-protocol.md` → Gate emphasis; `period-completeness` and `source-type` are reserved — no profile carries them in v3.6.0): `period-completeness`, `source-type`, `comparability`, `trend-vs-objective`, `market-recency`, `base-rates`, `triangulation`, `human-validated`, `instrumentation`, `srm-exposure-peeking`, `ci-vs-point`, `spec-readiness`, `nfr-present`, `money-bridge`, `hippo-check`. A token names an *extra* check; it never switches a check off.

### 2b. Session defaults per role

| Role | `level_home` | `reach` | `quick_wins` | `planning_view` | `vocabulary_set` | `extra_sections` (artifact_type → partials) | `question_defaults` |
|------|--------------|---------|--------------|-----------------|------------------|---------------------------------------------|---------------------|
| pm | L2 | L1–L3 | brainstorm-features, requirements-creator, product-analysis | — (the skills' own order, as in v3.5.0) | core | — | — |
| head_of_product | L3 | L2–L4 | quarterly-planning, goal-setter, one-on-one, performance-review | rollup | leader | — | — |
| cpo | L4 | L3–L4 | product-landscape (category map), focus-advisor (strategic focus), decision-log, goal-setter | rollup | leader | — | — |
| product_designer | L1 | L1–L2 | design-bridge, flow-walkthrough, product-research, diagram-prototyper | slice | design | — | design |
| product_analyst | L2 | L1–L3 | product-analysis, experiment-tracker, cjm-research | slice | data | requirements → tracking-plan | — |
| ux_researcher | L2 | L1–L3 | product-research, feedback-triage, meeting-processor (discovery / interview meetings) | slice | research | research → repository-entry | — |
| eng_lead | L1 | L1–L2 | task-creator, sprint-planning, delegation-coach, one-on-one | slice | engineering | requirements → nfr | — |
| business_owner | L3 | L3–L4 | product-reporter (quarter review), focus-advisor (strategic focus), decision-log, quarterly-planning | rollup | business | — | — |

Cross-cutting: the **pm profile is the fallback** for any undefined default, and it overrides nothing — a user without a role, or with `pm`, gets exactly the v3.5.0 defaults (no `template_defaults`, `gate_emphasis`, `planning_view`, `sources_priority` or `question_defaults`); `template_defaults[artifact_type]` is the **first** subtype §2 lists for that Product-contour type (People-contour entries in that column are informational); `question_defaults: design` lets design-bridge, diagram-prototyper and flow-walkthrough order and pre-select their existing options (their own steps say how); a role never removes a template from the wizard — it reorders the candidates within their scope (Step T ranks the role's default first among templates of the same scope; the user's own templates stay above the built-ins). The money bridge is not an extra section: `qbr`, `board-update` and `business-case` include it themselves — a table when `Revenue driver` mappings exist in Key Metrics, otherwise the single line "No revenue mapping configured".

## 3. What a role changes — and what it never changes

| Changes (defaults) | Never changes |
|--------------------|---------------|
| Home altitude; horizon and roll-up/drill-down default direction | The PM mental model and the ten principles (`pm-mental-model.md`) |
| Template ranked first in Step T; extra sections switched on — tracking plan, NFR, repository entry | Data Integrity Gate checks, evidence classes, decision-record (ADR) format, vault schema |
| Which evidence gate is emphasised (stricter), never which is relaxed | Skill routing and "Do NOT use" rules; skill availability |
| Vocabulary in prompts, questions and headings; data sources tried first | Tone, identity, honesty, anti-sycophancy stance |
| Quick-wins list after onboarding; ordering of options in questions (only where a skill step implements it) | Alarms (stale experiments, gate failures, spec not ready) — never hidden for any role |

Anti-stereotype rule: a role never encodes a *stance* ("CPO cares only about margin", "designers ignore data"). It encodes defaults of *form*. Judgment stays with the user.

## 4. Hats — wearing another role for one run

A per-task override: UA «як CPO, …», «як аналітик, перевір readout», «очима дизайнера …»; EN "as a CPO, …", "as an analyst, …", `hat: cpo`. Put the task in the same sentence — routing is decided by the task, the hat only changes that run's defaults. The idiom "wear the … hat" is recognised by Step 0i but routes less reliably (measured 2026-09-28: 1/3 vs 3/3 for "as a …"), so docs and examples use the "as a …" / «як …» form. Effect: the draft as presented in the chat starts with `Hat: cpo (profile: pm)` — never inside slides, Jira fields or a published page — and, since v3.6.0, the hat supplies that role's `template_defaults`, `extra_sections`, `gate_emphasis`, `vocabulary_set` and `question_defaults` for this output only — also for a `pm` or role-less user, which is the point of a hat; `level_home`, `reach`, `quick_wins`, `planning_view` and `horizon` stay the profile's, and the altitude line still follows the request. The profile is never rewritten. A role word that describes another person ("goals for Person1 as an analyst") is not a hat. `hats_allowed` in `## Judgment` (`all` by default) lets an organisation limit which hats are accepted; the plugin never proposes a hat on its own.

**Hats vs debate.** A debate role card in `debate-protocol.md` is a stakeholder *argued* inside a debate (`You are {role}. Mandate: …` is a card template, not a persona prompt about the user). A hat changes the *defaults of one run* for the user's own output. `brainstorm-features` Debate mode is the multi-role form: its cards are not hats, and `hats_allowed` never limits them. Neither rewrites the user's identity, and neither is a system prompt.

## 5. Resolution protocol — Step 0i (in `local-context-protocol.md`)

1. Read `user.role` (and optional `user.role_scope`: product | area | org). If absent or not in the enum:
   - **interactive run, no role:** ask **once** — a two-level picker (group: Product · Design & research · Data & engineering · Business, then the role inside the group; "Other" = free text; scope is asked only by onboarding Step 4a and `set role`), or on a host without structured questions a numbered list of the eight roles + "other" (`host-profiles.md` §4);
   - **interactive run, free-text role:** one question — the keyword-mapped role (Recommended) · `other` (keep my wording, `pm` defaults); scope stays unset;
   - ask only when that file can be written; otherwise use the keyword-mapped role or `pm` for the session and print one notice line with the role lines to paste;
   - write the answer into the `local-context.md` Step 0a resolved (`- **Role:**`, `- **Role label:**`, `- **Role scope:**`, `- **Level home:**`); never re-ask — a role holding an enum value counts as confirmed; a skipped question means `pm` for this session and a new question next session;
   - **automated run** (scheduled or headless, or a skill invoked only for a return payload): never ask; use `pm` for this run and write nothing. `plugin-configurator` never asks at Step 0i — its Step 4a owns the question.
2. Resolve the profile rows (§2, §2b) into the session object `role_defaults`:
   - since v3.5.0 — `role`, `hat`, `level_home`, `reach`, `quick_wins`;
   - since v3.6.0, in interactive runs only (automated runs — scheduled, headless, a return payload — render exactly as in v3.5.0) — `horizon`, `template_defaults{artifact_type→subtype}`, `extra_sections{artifact_type→[partial]}`, `gate_emphasis[]`, `planning_view`, `vocabulary_set`, `question_defaults`, `sources_priority[]` (the order of the sources in the §2 "Vocabulary & sources" column; none for pm; used by focus-advisor only). These fields apply only when the role is confirmed (an enum value in the file) — a role used for one session without being written (read-only file, skipped question) applies the v3.5.0 fields only.
3. Parse a hat override from the request (§4) — interactive runs only; if present and accepted by `hats_allowed`, mark the header and overlay that role's `template_defaults`, `extra_sections`, `gate_emphasis`, `vocabulary_set` and `question_defaults` for this run (since v3.6.0); `level_home`, `reach`, `quick_wins`, `planning_view` and `horizon` stay the profile's.
4. Infer the artifact's altitude from the request and the artifact (e.g., "which tests await a decision" is L2 whoever asks); `level_home` is only the fallback. If it lies outside the reach, proceed anyway — the altitude line simply shows it.
5. Print one line, once per session in an interactive run and only when no `GROW_PM_SESSION` digest is in context (hosts without the hook) — `Role: <role>[ (hat: <hat>)] · Altitude home: <Lx>` — then expose `role_defaults` to the artifact footer (altitude line), Step T, planning-core and data-integrity.

**Existing users.** A free-text `role` from an earlier onboarding ("Senior PM", "Head of Growth") is mapped by keyword and confirmed once — in an interactive run only:

| Keyword (case-insensitive, whole words; `*` = word prefix) | Role |
|---|---|
| `engineering`, `eng lead`, `tech lead`, `cto`, `техлід`, `розробк*`, `інженер*` | eng_lead |
| `cpo`, `chief product`, `vp product`, `vp of product` | cpo |
| `head of product`, `director of product`, `product director`, `lead pm`, `group pm`, `керівник продукту`, `директор з продукту` | head_of_product |
| `design*`, `дизайн*` | product_designer |
| `analy*`, `аналіт*` | product_analyst |
| `research*`, `дослідн*` | ux_researcher |
| `product owner`, `po`, `власник продукту`, `продакт-оунер` | pm |
| `owner`, `general manager`, `gm`, `business`, `власник`, `бізнес*`, `керівник напряму` | business_owner |
| anything else (incl. `pm`, `product manager`, `продакт`) | pm |

Rows are tried top to bottom; the first match wins (so "Head of Engineering" and "VP Engineering" map to `eng_lead`, "Engagement PM" to `pm`). A free-text answer to the confirmation question is mapped again and confirmed once. The original text is kept as `Role label`. The same map serves Step 0i and the configurator's RM-4d migration.

## 6. How skills consume the profile

- **Step 0** (every skill): after Step 0i, read `role_defaults`; never branch on the role name in a SKILL.md — branch only on `role_defaults.*` fields (§5 step 2), never on `role_defaults.role` or `hat` (lint check 19 `role-branching`).
- **Artifact footer** (v3.5.0): delivered Product-contour artifacts end with the altitude line where `template-protocol.md` T-5 step 3a places it (`artifact-style-gate.md` Gate 4a).
- **Onboarding** (v3.5.0): `plugin-configurator` Step 17 offers `role_defaults.quick_wins` first.
- **Step T** (since v3.6.0): in the skills whose Step T opts in (write-concept, requirements-creator, product-reporter's quarter mode) and only when the skill declares no subtype, `template_defaults[artifact_type]` becomes the request subtype; elsewhere the new subtypes are reached by the user's words. `extra_sections[artifact_type]` are appended at T-5 step 3b in requirements-creator (requirements) and in product-research and feedback-triage (research) when the body lacks them; the user can still pick any template.
- **Planning suite** (since v3.6.0, `planning-core.md` §7): `planning_view: rollup` shows roll-ups first, `slice` the delivery slice first (and the tech-debt reserve as its own line), no view (pm, no or unconfirmed role, automated runs) keeps the pre-v3.6.0 order; `horizon` sets project-planning's default arc window.
- **Analytical and spec skills** (since v3.6.0): each `gate_emphasis` token adds the one extra check mapped in `data-integrity-protocol.md` → Gate emphasis, where the skill has a step for it; the check only adds a caveat line — never a question, never a relaxed check.
- **Questions** (since v3.6.0, only in skills whose step implements it): `vocabulary_set` words headings and option labels (`references/vocabulary-sets.md`) — brainstorm-features, flow-walkthrough; `question_defaults` orders and pre-selects existing options — design-bridge, diagram-prototyper, flow-walkthrough. Neither adds or removes a question.
- **People contour**: unchanged; people skills appear in quick wins for `head_of_product` and `cpo`, `delegation-coach` and `one-on-one` for `eng_lead`.

## 7. Versioning

Adding a role or an altitude = MINOR; changing a default = PATCH; changing the enum values or the altitude line format = MAJOR. Skills reference field names of `role_defaults`, never role names.
