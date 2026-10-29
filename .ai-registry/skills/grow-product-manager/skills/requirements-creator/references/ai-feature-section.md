# ai-feature-section.md

> Skill-local reference for `requirements-creator` (since v3.9.0). It holds the rules SKILL.md cites for the `ai-feature` subtype (Step T), the AI-feature sections and the pre-mortem of an A/B or AI-driven spec (Step 4), the not-solution-shaped note (Step 5), the Analyze & Improve advisories, and the two inbound build-first paths.

Principle 6 of `references/pm-mental-model.md`: for an AI-driven feature the spec is a behaviour spec, an eval set, an acceptable error rate and kill criteria, not a feature list. The pre-mortem and kill criteria follow `references/judgment-points.md` §7; the inbound paths follow its §8. Everything in this file is **derived, never asked**: it adds no question to Steps 1–3, no T-4 variable and no Analyze & Improve question.

## 1. When a feature is AI-driven

A feature is AI-driven when the request, the source concept or brief, or the inbound payload names it so in explicit, AI-qualified words:

- EN: "AI" (an AI feature, an AI assistant), "LLM", "GPT", "ML model" (a machine-learning model, an ML classifier or ranking model), "chatbot", "generative" / "GenAI";
- UA: «AI» / «ШІ» («AI-фіча», «ШІ-асистент»), «LLM», «GPT», «ML-модель», «чат-бот» / «чатбот», «генеративний».

Never on a bare "model" / «модель» — a data model, a business, pricing or subscription model, a 3D model, a device model. Never on "smart", "automatic", "algorithm", "personalised" or "recommendations" alone. Never on a request for the optional AI recommendations block («Технічні рекомендації (AI)», "AI technical recommendations") — it names who drafts that block, not what the feature does. When unsure, the feature is not AI-driven. It is never asked.

## 2. Subtype and template (Step T)

- **Inferred** (§1 words in a request that does not ask for an AI-feature format): declare `subtype: ai-feature` only when no user-global or product `requirements` template is a candidate in T-1. Step T then ends in the silent `match: subtype` hit of `references/template-protocol.md` T-3, and the run asks nothing it did not ask before. With such a template among the candidates, the subtype stays what it would be without the AI words, and that template renders as its owner built it.
- **Requested by name** (the user asks for an AI-feature spec or an eval set by name, or the inbound payload of §6a carries `subtype: ai-feature`): declared like any explicit subtype — T-3 applies its existing rules, exactly as for an explicit A/B request.
- **Precedence:** `ab-test` keeps winning when both apply; the AI sections are then inserted into the A/B document (§3). `ai-feature` wins over `bugfix` and over the role default of T-0.
- `requirements/ai-feature` (`templates/built-in/requirements/ai-feature-v1.md`) is the canonical skeleton: Problem and outcome, the AI sections 2.1–2.4, functional requirements for the non-model parts, acceptance criteria with AC-eval, the tracking plan, Out of scope, Open questions.

## 3. The AI sections on other templates (Step 4)

**When.** Create mode only, the feature is AI-driven (§1), and the rendered document is a built-in (`requirements/default`, `requirements/ab-test`) or the skill's internal structure, with no section of the same meaning (a heading that starts with "AI feature", "Behaviour spec" or "Eval set", or its `user.language` translation). They are never inserted into a user-global or product template — its owner decides its sections, as with the pre-mortem without its include — and never into a document in Analyze & Improve (§7).

**What.** Section 2 of `templates/built-in/requirements/ai-feature-v1.md`, with its headings and columns — there is no second skeleton:

| Section | Content |
|---------|---------|
| AI feature: behaviour and evaluation | The H2 heading; never named "AI recommendations" or "Технічні рекомендації (AI)" — that is the optional Gate 1 block, which Gate 4b does not check |
| Behaviour spec | Input or situation → must → must not → fallback / refusal |
| Eval set | Case → expected behaviour → type (typical / edge / adversarial / refusal) → origin → pass rule; then the planned size and owner (else `⚠️ TBD`) and the re-run rule: re-run on every model or prompt change |
| Acceptable error rate | Per error class: the acceptable rate and how it is measured |
| Kill criteria | Observable signal → threshold → date → then stop, pivot, descope or roll back (`references/judgment-points.md` §7) |

Acceptance criteria gain one line: "AC-eval: the eval set passes at or below the acceptable error rate". The tracking plan is not added for this reason — `requirements/ai-feature` includes it by name; elsewhere it stays a role extra section (T-5 step 3b).

**Where.** Directly after the section that says what is built — Functional requirements (default "Functional Requirements", internal 5.2), or "Variants" in `requirements/ab-test` — so they sit above the role extra sections, the pre-mortem's fallback place and the footer. The heading is unnumbered; the T-5 step 3b comparison ignores numbering.

**Fill.** From the request, the source concept or brief, the prototype or the debate. A cell nothing states reads `⚠️ TBD`, except a kill row's date and then, which are derived (see Content rules below). The PM fills it at the Step 5 review or later; it is never a Step 2 question, a Step 3 question or a T-4 variable, and the Quality-standard "ask to fill gaps" rule does not apply to it.

**Content rules.**
- Behaviour rules are requirements content. Gate 1 still applies: no model, vendor, prompt or architecture choice — those belong only in the optional AI recommendations block, on explicit request.
- Each eval case carries its origin as an evidence class (`references/pm-mental-model.md` §4): `observed` (a production log or trace, personal data masked per `references/data-policy.md`), `reported` (a user, a ticket, a stakeholder), `simulated` (invented). A `simulated` case is a test input, never evidence of what users do (Principle 7). Expected outputs carry no class.
- Acceptable error rates and kill thresholds are targets: no class, `⚠️ TBD` when unstated. Behaviour rules, expected outputs and kill rows are exempt from Gate 4b; a cited baseline or input in them keeps its class (`references/artifact-style-gate.md` Gate 4b §1).
- Kill criteria cover the launch gate (the eval set below its pass rule) and production (error, complaint or cost thresholds, a guardrail regression), each with a date. Only the threshold may read `⚠️ TBD`: a date the sources do not give is derived from the launch and the window the spec states (e.g. "4 weeks after launch"), and a then they do not give defaults to switching the AI behaviour off (roll back).

## 4. The pre-mortem of an A/B or AI-driven spec (Step 4)

`references/judgment-points.md` §7 binds two rows of this skill. The section is rendered from `templates/built-in/partial/pre-mortem-v1.md` by `references/template-protocol.md` T-5 step 3b — for a built-in or the internal structure; a user-global or product template only when it includes `{{> pre-mortem}}`. Not for a feature-flag or no-flag spec without AI sections; never in Analyze & Improve or a return payload.

**A/B spec** (subtype `ab-test`, or A/B / A/B/C chosen at Step 3a). Causes are test-validity causes, 2–3 of them, each with a pre-launch check in "What we do now":

| Cause | Early signal | Pre-launch check |
|-------|--------------|------------------|
| Under-powered for the MDE at this traffic and duration | the planned duration ends before the required sample | sample size against traffic and duration before launch |
| Sample-ratio mismatch or exposure not logged | group sizes off the split on day 1–2 | an SRM check on day 1–2; exposure event in QA |
| Novelty or primacy effect | the lift fades week over week | plan the readout by week, not only cumulatively |
| Events not firing as specified | event counts off the backend count | event QA before launch (tracking plan) |
| A guardrail missing or untracked | no guardrail row in Success criteria | name and instrument the guardrails before launch |

Pick the causes the spec itself makes most likely, in the §7 source order: unresolved debate objections and a minority report; `assumed` / `simulated` inputs; the Risks section, guardrails and base rate; the skill's own signals (⚠️ TBD parameters such as MDE or duration, open questions). Kill criteria are a pointer only: `kill_criteria_at` names the decision rule — "Stopping / Decision Criteria" in `requirements/ab-test`, "Decision rule" in the A/B sections.

**AI-driven spec** (`requirements/ai-feature`, or §3 inserted). Causes come from the AI sections — an eval set too thin or all `simulated`, an error class with no acceptable rate, refusal behaviour unspecified, drift after a model or prompt change — each with its early signal. `kill_criteria_at` names "Kill criteria" (2.4); there is no second table.

**Both** (an A/B test of an AI-driven feature): one pre-mortem, 2–3 causes in total, the pointer naming both sections.

**Placement and edits.** T-5 step 3b places it after the Risks section ("Risks" in `requirements/ab-test`), else above the role extra sections and the footer; the internal structure has its own place, before Tasks (`references/requirements-template.md`). `⚠️ TBD` cells are counted in the partial, never asked. The PM edits or deletes it at the Step 5 review; a deletion holds for this artifact, is never learned and is not restored (`references/self-improvement.md`).

## 5. The not-solution-shaped note (Step 5)

- **Scope.** Problem and outcome statements only: a hypothesis's problem (IF) and outcome (THEN) parts, Goals, the Overview of `requirements/default`, "Problem and outcome" of `requirements/ai-feature`, the outcome part of an A/B hypothesis.
- **Fires** when such a statement names the solution instead of the problem or the outcome — a goal "add an AI chat to the help page" instead of "buyers resolve delivery questions without a support ticket"; a problem "there is no smart search" instead of what users fail to do.
- **Never fires** on the change part of a hypothesis ("WE DO"), business or functional requirements, the behaviour spec or Variants — they are solution-shaped by design.
- **Form.** One line in the chat, in `user.language`, beside the gate report when the draft is presented, outside the document: `⚠️ not solution-shaped: <section, item> names a solution — problem-shaped: "<rewording>"`. Several statements share the line (the clearest one reworded, the others counted).
- **Never a question**, never a confirmation, never in the document. The body changes only when the user takes the rewording as an ordinary Step 5 edit. Interactive Create runs only.

## 6. Inbound build-first paths (`references/judgment-points.md` §8)

The creation steps these paths route to are unchanged: Steps 2–9 run as in any Create run, fed by the payload. The only differences are the Step 1 questions the payload already answers (skipped) and, for a prototype source, Step 8's option 2 (left out).

### 6a. ← write-concept Step 1: an eval set for an AI behaviour

- **Payload:** the confirmed brief (problem, users, outcome), the riskiest assumption (an AI behaviour), the concept title, `subtype: ai-feature`.
- **Step 1:** 1a and 1b ask nothing the brief answers — the product is the active one, new or existing comes from the brief (asked only when it does not say), and the feature is the brief's (no "which feature?" question). 1c runs only when the brief changes existing UI.
- **Step T:** the subtype requested by name (§2).
- **Steps 3d, 3e, 6:** the eval-set path is a full Create run, so Step 3d (Epic key and feature number), Step 3e (the ROI and ICE offer) and Step 6 (whether and where to publish) ask as in any Create run.
- **Draft:** the behaviour spec and the eval set start from the riskiest assumption; eval cases are `simulated` unless the brief cites real ones; the rest follows §3 and §4.
- **Return:** write-concept printed the brief for resuming; the PM brings back the spec link and, once the eval set has run, its results.

### 6b. ← design-bridge Step 9: the prototype as the spec

- **Payload** (design-bridge's prototype-as-spec section): the prototype reference (file, frames), its screens, the states it shows, its flows, the upstream brief or concept and the assumption it tests.
- **Step 1:** 1a and 1b ask nothing the payload answers — the product is the active one, new or existing comes from the upstream (asked only when it does not say), and the feature is the prototype's. 1c runs as usual when the feature changes existing UI.
- **Mapping:**
  - each screen → a Functional requirements row (the screen is the block; marker № = FR №);
  - each shown state → a Given/When/Then acceptance criterion;
  - a state the prototype does not show (empty, error, loading, no permission, offline) or a Design System issue flagged upstream → an Open questions item, never an invented requirement or criterion; where the document has no Open questions section, a short "Open questions" list closes the Functional requirements;
  - UI&UX links the prototype frames as the proposed design (the designer still owns the section); Step 4.2, when offered, annotates the prototype frames.
- **Never validation.** The prototype is a source, cited as `reported (file, frame)`; only real-user sessions on it are evidence (`references/judgment-points.md` §8).
- **Step 8:** option 2 (low-fi UI prototype) is left out — the prototype exists; option 1 (developer handoff) is recommended; the other options keep their wording and order (`references/design-bridge-handoff.md`).

## 7. Analyze & Improve

Advisory only (`references/analyze-improve-mode.md` A2–A3):
- an AI-driven document (§1) without a behaviour spec, an eval set, an acceptable error rate or kill criteria;
- a solution-shaped problem or outcome statement (§5 scope).

Each is a content issue in A3 and may become an A5 improvement proposal — an existing question. It is never an A4 question, and nothing is added to the user's document unless the user accepts it at A5. The completeness score keeps its nine sections.
