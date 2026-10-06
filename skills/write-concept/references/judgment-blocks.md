# Judgment blocks — write-concept

> Skill-local (since v3.9.0). How `write-concept` applies two shared rules: the build-first line of Step 1 (P6, `references/judgment-points.md` §8) and the pre-mortem and kill criteria of Step 4 (P4, §7). The rules themselves live there; this file adds no question, gate or switch of its own. Loaded at Step 1 when the line may show, at Step 4 when the pre-mortem renders, and at Step 8 when a build-first prototype exists.

## 1. The riskiest assumption — derived once

The one assumption the concept's case rests on: if it is false, the concept is not worth building. It is derived from the brief (problem, who it is for, proposed change, success metric) and the inputs at hand — never asked. One derivation serves both blocks: the Step 1 line names it, and the Step 4 pre-mortem takes it as a cause (§4). With the line switched off or left out, it is still derived for the pre-mortem.

| Kind | What would make the concept wrong | Build path (§3) |
|---|---|---|
| Value | users do not want or need the change | lo-fi prototype shown to 3–5 real users |
| Usability | users cannot find or use the new interaction | lo-fi prototype shown to 3–5 real users |
| Current behaviour | the product today does not behave, or users do not get stuck, the way the problem statement says | walk of the as-is flow |
| AI behaviour | a model-produced output is not good enough, safe enough or consistent enough | eval set |
| Demand, feasibility, viability | not enough volume; it cannot be built; the economics, legal or platform terms do not hold | none from this line — demand is a Step 2 data question (product-analysis), feasibility and viability go to Technical Considerations and Risks |

AI behaviour is inferred only from the brief's own words (AI / ШІ, LLM, ML model, GPT, chatbot, generative), never from a bare "model", and never from a new question — the existing Step 1 feature-type question keeps its wording and options. The concept never gains AI behaviour or eval sections of its own: those belong to the requirements document.

## 2. The build-first line (Step 1)

**Shown** inside the existing brief summary, once per run, only when all of these hold:
- `judgment.build_first` reads `on` (the default; the value is read without a trailing note in brackets, any other value reads as `on`);
- the run is interactive — never a scheduled, headless or return-payload run;
- the concept proposes a product change — the default concept, or a user subtype whose body proposes a solution; never a design brief, strategy memo, decision memo, business case or a release-notes draft (the release-manager chain);
- the riskiest assumption has a build path (§1 table);
- no `observed` / `measured` / `reported` evidence covers it, and its path was not already taken. The only inputs that can cover it at Step 1 are a Step 0.5 hit (taken as context or not) of type `walkthrough`, `ab-test-results`, `competitive-analysis`, `market-research` or `ux-benchmark` whose summary addresses the assumption, and a source the user named in the request or in a Step 1 answer that addresses it (a study, a test readout, interview notes, a walkthrough) — a page named only as general context does not. A `simulated` or `assumed` source never covers it. A `prototype` hit, or a `requirements` hit of subtype `ai-feature` with an eval set, suppresses the line because that path was already taken, not because it settles anything: the prototype stays `reported` (file, frame), and the assumption stays open in the pre-mortem until real-user sessions on it, or a run of the eval set, exist.

**Form.** One line in `user.language`, not a question — the summary's existing confirmation stays the only question. It names the assumption, the cheapest path and the words that take it, for example: "Riskiest assumption: buyers will park items instead of carting them. Cheapest check before the PRD: a lo-fi prototype shown to 3–5 real buyers — «спершу прототип» / "build first" takes it; confirming the brief continues to the PRD." Its first appearance in a session adds how to switch it off: answer «вимкни» / "turn off", or set `Build first: off` in `## Judgment`.

**Answers to the confirmation.**
- Confirms or edits the brief → Step 2 exactly as before; the line is not repeated in this run.
- «спершу прототип» / "build first" → §3.
- «вимкни» / "turn off" → write `- **Build first:** off` under the write rules of `references/judgment-points.md` §2 step 4 (only when the file can be written, with the one-row changelog `Judgment → Build first | on | off`; otherwise off for this session and the line to paste is printed), then continue as for a confirmation.

The line is not a P2 point: nothing is kept as an estimate and nothing travels as `pm_estimate`.

## 3. Taking the path

The confirmed brief and the assumption go to the target skill. The write-concept run then ends, with the confirmed brief and the assumption printed in the chat so the user can resume ("continue the concept from this brief"). The creation steps of the target skills are unchanged.

| Kind | Build | Evidence step | Hand-off and payload | What comes back · class |
|---|---|---|---|---|
| Value, usability | lo-fi prototype scoped to the screens the assumption needs | 3–5 real users try it — design-bridge's Step 9 line suggests product-research | `design-bridge`: `intent: prototype`, `fidelity: lo-fi`, `source: brief`, `assumption` (design-bridge playbook, source f) | the prototype — `reported` (file, frame), never validation; session findings with the class product-research gives them |
| Current behaviour | walk of the as-is flow, the 3–5 steps around the assumption | the walk itself | `flow-walkthrough`, walk mode: the flow and surface from the brief, the assumption as the walk's question | the walk report and evidence pack — `observed`; without APP-DRIVE the user-driven variant, still `observed` |
| AI behaviour | eval set: behaviour rules, cases, an acceptable error rate | the cases run against the model or prompt | `requirements-creator`: `subtype: ai-feature`, `source: brief`, `assumption` | the AI-feature spec; case origins keep their class, expected outputs carry none; only a run of the cases is evidence |

**On resume** the new run reads the brief as its source. Step 0.5 finds the `prototype`, `walkthrough` or `ai-feature` spec the path produced (or the user names it), so the line stays suppressed (§2). The results the user brings back, or a Step 0.5 hit the user takes as context, land in the PRD (a hit not taken only suppresses the line and links the prototype):
- the prototype link → §9 Design & UX, "Prototype link";
- real-user session findings and walk steps → §2 Problem Statement, Evidence, each with its class;
- the eval set and its acceptable error rate → §11 "How we'll verify", and the error rate as a kill-criteria threshold (§4).

A claim about users made on the prototype alone ("users will understand X") stays `[assumed — …]` (`references/pm-mental-model.md` §3, Prototype-as-validation).

## 4. Pre-mortem and kill criteria (Step 4)

**Where.** `references/template-protocol.md` T-5 step 3b inserts `templates/built-in/partial/pre-mortem-v1.md` (a user `_partials/pre-mortem.md` first) right after the Risks section ("Risks & Mitigations", "Risks & Assumptions", "Risks"), else where the skill's own structure puts it, else above the role extra sections and the judgment footer. With no template (the internal structure, `references/prd-structure.md`) it renders the same way, right after block 12; a template with no Risks section, such as the strategy memo, gets it last, its kill criteria pointing to the "Kill criteria" section above.

**When.** Block 15 of the Step 1 list, pre-selected. Deselected there → not rendered, and the T-5 self-check does not insert it. Never on a design brief, a release-notes draft or a return payload; otherwise in any run where Step 4 runs, automated ones included — it asks nothing. A user-global or product template gets it only when it includes `{{> pre-mortem}}`. It is derived and never asked: a missing threshold or date is `⚠️ TBD`, counted in the block, and never filled by a question.

**Kill criteria per subtype.**

| Concept | Kill criteria |
|---|---|
| Default concept, a user subtype | its own table — signal, threshold, date, then |
| Concept shipping behind an experiment whose §11 decision rule states a kill or stop branch with a threshold and a date | a pointer to "Verification & decision rule" — the decision rule is the kill criterion; a rule without them (the template's "kill if [...]") gets its own table, as above |
| Strategy memo, business case | a pointer to their "Kill criteria" section |
| Decision memo | a pointer to its "Revisit trigger"; the causes draw on its Risks |

**Variables** (all derived):
- `judged_on` — the concept's own date: the Phase 1 release target plus the §11 "After 1 quarter" checkpoint, or the success metric's window ("30 days after launch"); `⚠️ TBD` when the concept states none.
- `failure_causes` — 2–3, in the order of `references/judgment-points.md` §7:
  1. the unresolved Skeptic objections and the minority report of a Step 5 debate — when a debate runs after drafting, the block is re-rendered with them first;
  2. the `assumed` / `simulated` inputs, keeping their labels, and the riskiest assumption (§1);
  3. the Risks rows, the guardrail metrics and a base rate (from the `base-rates` gate emphasis when it ran);
  4. the concept's Open Questions, dependencies and timeline.

  Each cause names the section or input it rests on and an observable early signal.
- `kill_criteria` — the signal from Success Metrics or a guardrail; the threshold the concept states (a target's lower bound, a guardrail limit, an eval set's acceptable error rate); the date from `judged_on` or the timeline; then stop, pivot, descope or roll back.

**Evidence.** Causes, early signals and kill rows carry no evidence class (`references/artifact-style-gate.md` Gate 4b §1); a baseline they cite keeps its own, and an `assumed` input keeps its label.

**At review (Step 5).** The PM edits the block like any other. A deletion is respected for this artifact: the self-check does not restore it, and the self-improvement check treats it as a judgment-guard correction — applied here only, never proposed as a skill change, said in one chat line (`references/self-improvement.md`). When the concept has no pre-mortem (a design brief, or the block deselected in Step 1), unresolved debate objections land in Risks / Open Questions as before; a deletion at review moves nothing elsewhere.

## 5. Step 8 with a build-first prototype

When this concept came from a build-first run — the prototype found at Step 0.5 or named by the user — its link is already in §9 from Step 4. Step 8 keeps its three options and their order; option 2 then reads "iterate the build-first prototype" and passes `prototype_ref` (the vault path or URL) to `design-bridge` with `source: confluence_page_url`, so design-bridge reads the Prototype IR from that prototype and 5b edits it in place — no second prototype is drawn. Without a build-first prototype, option 2 is unchanged.
