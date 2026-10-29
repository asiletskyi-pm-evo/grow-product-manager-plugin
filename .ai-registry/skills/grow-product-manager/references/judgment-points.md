# judgment-points.md

> Shared protocol (since v3.7.0). Implements principles of `pm-mental-model.md` at the judgment points of the skills that cite it: **P2 — human hypothesis first** (§2), **P3 — calibrated confidence with a falsifier** (§3), **P9 — decision ownership and hygiene** (§4–§5), and since v3.9.0 **P4 — the built-in opponent** (§7, pre-mortem and kill criteria), **P6 — build before you argue** (§8, the build-first offer) and **P8 — learning-preserving modes** (§9). A skill applies this file only at the steps that cite it. The §1 table is the complete list: no other skill, step or mode asks the P2 question or renders the confidence line (`pm-mental-model.md` §5 — a principle acts only through a step that implements it).

## 1. Implementing steps

| Skill · step | Judgment point | P2 question (§2) | P3 confidence line (§3) | Where the estimate is kept |
|---|---|---|---|---|
| `brainstorm-features` · before the first ICE / PRO scores of the run (the Step 3A evaluation, or the Step 3B idea cards — the ideas are named first, the cards with their scores follow the answer) | ranking of ideas | "Which N would you do first?" — N = 3, or 2 when there are three ideas or fewer; not asked for a single idea | the ranked result's top pick — judgment footer | chat comparison |
| `experiment-tracker` · readout, before the chain to product-analysis | the test outcome | "Your prediction: which variant wins, and by roughly how much?" — not asked when the entry already has a `prediction` | — (the product-analysis report carries it) | registry `prediction`; passed to product-analysis as `pm_estimate` |
| `product-analysis` · A/B mode, after AB-3 and before AB-4 | the A/B verdict | "Your call before mine: roll out / roll out with caveats / extend / iterate / roll back?" — in a standalone run; chained, it takes the caller's `pm_estimate` and never asks | the report's Recommendation — judgment footer | chat comparison |
| `quarterly-planning` · Step 4.4, before ICE / RICE | priority of the candidates above the ceiling | "Which of these would you keep in the quarter first?" — not asked when only one candidate is above the ceiling | the prioritised list — judgment footer of the plan | chat comparison |
| `focus-advisor` · Step 1, in the same message as the horizon gate | the focus pick | "What do you think matters most in this horizon?" | the brief's lead focus — judgment footer (headless runs too) | chat comparison in Step 5 |
| `decision-log` · log mode step 1a; revisit step 2 (the new decision) | the owner's confidence and revisit trigger | "How sure are you — known / likely / uncertain / unknown — and what would make you revisit it?" — one question for a batch of decisions | the record's `Confidence:` line (§4) | record fields |

## 2. P2 — "your estimate first"

1. **When it is asked** — all three hold:
   - the run is **interactive** (the user is present in the chat). Never in an **automated** run: a scheduled or headless run, or a skill invoked by another skill only for a return payload — the same test as `local-context-protocol.md` Step 0i step 2. A skill chained with the user present that shows its own gate or report is interactive (decision-log from experiment-tracker, meeting-processor or a planning skill; the product-analysis readout from experiment-tracker); "only for a return payload" means the result goes straight into the caller's output (brainstorm Step 3C, a Debate-mode return, product-analysis for cjm-research);
   - `judgment.hypothesis_first` is `on`. The value is read without any trailing note in brackets (a legacy `on (acts from v3.7.0)` reads as `on`, `off (…)` as `off`); an absent `## Judgment` section or line, or any other value, reads as `on`;
   - the user has not already given their estimate for this point: in the request ("I think B wins", «думаю, топ — ідеї 2 і 5»), earlier in this run, in a record field §1 names, or in a `pm_estimate` passed by the caller (an answer, `skipped` or `off` — each means "do not ask"; `skipped` and `off` also mean no comparison). A known estimate — also a partial one, such as the winner without the size — is used without the question and kept where §1 says, and the comparison (step 5) still follows. Never ask for the missing part. For decision-log the estimate is the owner's level: a `revisit_trigger` from the context or a caller is not an estimate, so the question is still asked, for the level only.

   With the switch `off`, nothing of this section runs — no question and no comparison, even when an estimate is known.
2. **Order.** Ask before the skill shows its own estimate for that point — its score, rank, verdict or priority. The inputs may be shown (the idea list, the metrics, the candidates); only the skill's own judgment waits for the answer.
3. **Form.** One question in `user.language`, worded as in §1, asked once per run for its point. A choice answer gets the choices plus **Skip** — as a structured question when they fit the host's picker (2–4 options, `host-profiles.md` §4), otherwise as a numbered list in the chat with Skip last, never dropping or merging a choice; a free-form answer (a top-N, a prediction, decision-log's level and trigger) is asked in plain text and accepts a skip word. A reply that answers only the rest of the message it came in (for example, confirms focus-advisor's horizon) counts as a skip. The first P2 question in a session carries one extra line: why ("so my numbers don't anchor your call") and how to switch it off ("answer «вимкни» / "turn off", or set `Hypothesis first: off` in `## Judgment`"). Later P2 questions in the same session leave that line out.
4. **Answers.**
   - **An estimate** → keep it where §1 says.
   - **Skip** («пропусти», «не знаю», "skip", "don't know", "just show yours", an empty answer) → continue exactly as without the question; no comparison.
   - **Turn off** («вимкни», "turn off", "stop asking") → write `- **Hypothesis first:** off` into `## Judgment` of the `local-context.md` that Step 0a resolved (create the section with the defaults when it is absent) under the write rules of Step 0i step 2: only when the file can be written, with a one-row changelog `Judgment → Hypothesis first | on | off`. The answer is the consent — no further confirmation (Context Enrichment does not apply). When it cannot be written, keep it off for this session and print the line to paste. Then continue as for skip.
5. **Compare, don't replace.** After the skill's own result, one short block — "Your estimate vs mine", in `user.language` — where they agree, where they differ, and for each difference the evidence that separates them, or "no evidence decides this — your call". The skill never moves its own score, rank or verdict toward the user's (P5), never withholds it, and never takes the decision for the user. The block stays in the chat; it enters an artifact only through a field §1 names.
6. **Nothing else changes.** The P2 question is the only question v3.7.0 adds to a skill run (the configurator's Extended onboarding also offers the switch itself). It is not a gate, and every question a skill already asks keeps its wording and order — except that brainstorm-features' "Choose one" starts from a P2 answer when there is one. When the question is not asked and no estimate is known (step 1), the skill runs as in v3.6.0 apart from the outputs of §3–§5. v3.9.0 adds no P2 point: its build-first line (§8) is not a question, and its PM-first question (§9) exists only under `learning_mode: pm_first` — neither is a §1 point, and neither travels as `pm_estimate`.

## 3. P3 — the confidence line

```
Confidence: <level> · most sensitive to: <one assumption or input> · would change if: <observable information>
```

The labels and the level word stay in English, like the altitude line; the two clauses are written in `user.language`.

| Level | Meaning | Numeric `confidence` (0–1) | Debate `confidence` |
|---|---|---|---|
| `known` | established by measured or observed evidence that passed the skill's gates; only a real surprise would overturn it | ≥ 0.8 | high |
| `likely` | the evidence points one way, with a named gap | 0.6 to < 0.8 | medium |
| `uncertain` | the evidence is mixed, thin or indirect | < 0.6 | low |
| `unknown` | no basis to assign a level yet | no number | — |

Frontmatter fields keep their types: the lifecycle `confidence` float and the debate `confidence` high / medium / low. When a skill writes one of them on the same artifact and for the same claim as the line, the two agree through this table — except that the line never reads above the no-inflation cap below: when the field reads higher, the line keeps the cap and names the gap in `most sensitive to`. The hypothesis-lifecycle float (`vault-protocol.md` → Hypothesis Lifecycle Updates) is the chance a hypothesis holds, not a confidence in a recommendation, and is outside this table.

Rules:
- **Derived, never asked.** One line per artifact, for its lead recommendation or verdict — the one §1 names. The decision record carries its own line (§4).
- **`most sensitive to`** names the single assumption or input whose change would move the call most, for example "the novelty effect has faded by week 2" or "the Android segment is representative". It is not a list.
- **`would change if`** names information someone can observe: a metric crossing a value, a segment result, an interview finding, a date passing. "More data" or "further research" does not pass.
- **No inflation.** The level is at most `uncertain` when the verdict the lead recommendation acts on is inconclusive, when a metric it rests on is ❌ Blocked or was not cross-validated by the Data Integrity Gate (a single source included), or when the estimate is by analogy — and, since v3.8.0, when it rests on a claim `data-integrity-protocol.md` Gate Check 6 marked as frontier (however rendered: a hand-back line or `[assumed — frontier: <human step>]`) or on a `simulated` input. An `assumed` working assumption does not cap the level — it is named (next rule); an `assumed` metric is one that was not cross-validated and caps as above. A segment the recommendation explicitly leaves out of its action does not cap it.
- **Weak inputs are named.** A recommendation resting on an `assumed` or `simulated` input names that input, with its class label, in `most sensitive to` (`pm-mental-model.md` §4); when there are several, the one the call is most sensitive to — the others keep their labels in the body.
- **Placement.** In a Step T artifact, the judgment footer renders the line directly above the altitude line (`template-protocol.md` T-5 step 3a). A user override of the footer without the confidence placeholders gets the built-in line above its content. Where §1 names no line, none is rendered and Gate 4c is `n/a`.

## 4. Decision record fields (P9)

`decision-log` owns the record. The frontmatter keys are in `vault-schema.md` → `decision`; the body layout is in the decision-log record format.

| Field | Meaning | Taken from | When nothing states it |
|---|---|---|---|
| `owner` | the one person accountable (`decided_by` stays the list of people who took the decision) | the user, the meeting notes, the calling skill | `not recorded`; never guessed from seniority |
| `rejected_alternatives` | each option considered and not chosen, with a one-line reason (`alternatives_considered` stays the count) | Options considered | `not recorded` |
| `base_rate` | an outside view: how often decisions or launches of this kind worked, here (e.g. the experiment registry's win rate) or in a named external source | the evidence, a vault search, the user | `none found` |
| `revisit_trigger` | the observable event that reopens the decision (`revisit_by` stays the date) | the P2 answer, the context | `not recorded` |
| `minority_report` | the strongest dissent in 2–3 sentences, with who held it | a debate synthesis, a named dissenter in the notes | the key is left out |
| `evidence_classes` | the evidence classes of the inputs (`pm-mental-model.md` §4) | since v3.8.0: the labels of the evidence linked in the Rationale (the vault `evidence_classes` of artifacts saved since v3.8.0) plus the classes the calling skill's payload states — an experiment readout gives the classes of its labels (`measured` when the skill read the raw data itself, `reported` when the figures were pasted), what was said in a meeting `reported`, a debate its pack's classes with each A# as labelled (`assumed` or `simulated`), a senior opinion `assumed`, an unsourced Rationale input the record labels `assumed`; never asked | the key is left out |

The record's **`Confidence:` line** sits under its Decision section. It records the **owner's** confidence from the P2 answer — when the person answering is not the recorded owner, the level is labelled with their name (`likely (stated by <name>)`); its `would change if` is the revisit trigger. When the owner did not state a level, the line reads `Confidence: unknown (not stated)`. Its `most sensitive to` is the assumption the Rationale rests on, as stated, or `not recorded`.

Nothing is inferred beyond what the user, the invoking skill or the linked evidence states. A calling skill leaves an unstated field out of its payload; the record's body then shows `not recorded` / `none found`, and its frontmatter leaves the key out. The only question these fields add is the §1 P2 question.

## 5. The resulting check (decision-log revisit, step 1b)

When revisit mode opens an existing record, and before it collects the new decision, show three lines in the chat:

1. **Decision quality**, judged only on what was known at the time: were the options, rationale, evidence and base rate in the record adequate for the stakes and the reversibility? Answer `sound`, `mixed` or `flawed`, with one reason. A record from before v3.7.0 without these fields is judged on what it has, and says so.
2. **Outcome**: `good`, `bad` or `too early`, with the evidence (a readout, a metric with its period), and whether the revisit trigger fired.
3. **Resulting**: always one line. When quality and outcome disagree, name it: a good outcome from a flawed decision is luck, not a pattern to repeat; a bad outcome from a sound decision is variance, not a mistake to learn from. When they agree, say so.

The three lines go into the new record's Context. They add no question: the owner corrects them at the mode's existing gate. The old record is not edited beyond the existing `superseded` marking.

## 6. Gate 4c — where it is checked

`artifact-style-gate.md` Gate 4c checks the confidence line wherever §1 names one:
- **Artifacts** — the T-5 self-check, which also fixes a missing or malformed line silently — but never re-adds a confidence line the user removed at this run's review step (since v3.9.0; `self-improvement.md`).
- **Decision records** — decision-log's save gate. The level there is the owner's and the gate never changes it; a clause that names nothing observable is shown as `not recorded` (v3.7.0) and never replaced by an invented one, and no v3.8.0 check edits the owner's clauses: a level above the no-inflation cap (the v3.8.0 frontier and `simulated` caps included) is kept, and a "Your estimate vs mine" comparison, when one is shown, names the cap or the unnamed weak input; `unknown (not stated)` and `not recorded` clauses are well-formed in a record (§4).

A line is well-formed when:
- it uses one of the four levels;
- both clauses are specific enough to pass §3;
- the level respects the no-inflation rule (artifacts only — a decision record keeps the owner's level).

The artifact-checker has no 4c lens, because no maker–checker skill renders the line.

## 7. P4 — pre-mortem and kill criteria (since v3.9.0)

The strongest case against a consequential artifact, written as if it already failed, with pre-committed conditions to stop. Rendered from `templates/built-in/partial/pre-mortem-v1.md` by `template-protocol.md` T-5 step 3b ("Inserted sections"), or directly where the table says so. Derived from the artifact and its inputs — never a question, never a P2 point.

| Skill · step | Artifact | Kill criteria |
|---|---|---|
| `write-concept` · Step 4, through T-5 3b | every concept except the design brief and a release-notes draft; "Pre-mortem & kill criteria" is a pre-selected item of the Step 1 block list (deselected there → none) | its own table, or a pointer to the Kill criteria / Decision rule / Revisit trigger the subtype already has (strategy memo, business case, decision memo) |
| `requirements-creator` · Step 4, A/B sections | an A/B-test spec | the existing decision rule (`Stopping / Decision Criteria`) — pointer only; causes are test-validity causes, each with a pre-launch check |
| `requirements-creator` · Step 4, AI-feature sections | an AI-driven spec (`requirements/ai-feature`, or AI sections inserted) | the spec's own Kill criteria (2.4) — no second table |
| `quarterly-planning` · at scope lock (end of Step 5 in plan mode; the published plan of Step 6 in full mode) | the quarter plan | one per main focus |
| `roadmap-architect` · Step 4b (`onboard`) | a new mission or initiative; an epic only when the request carries goal or outcome text | one per entity, inside the existing approval preview and write |

**Causes** (2–3), in this order of sources:
1. the debate's unresolved Skeptic objections and minority report;
2. `assumed` / `simulated` inputs and the riskiest assumption named in §8;
3. the artifact's Risks section, guardrails and base rate;
4. the skill's own signals (capacity, dependencies, open questions).

Each cause names the input or section it rests on and has an observable early signal.

**Kill criteria** use the same observable-signal rule as P3's `would change if`, plus a date. Each row:
- an observable signal (never "more data");
- a threshold from the artifact, else `⚠️ TBD`;
- a date from the artifact, else derived: the launch or decision date plus the measurement window the artifact states (e.g. "4 weeks after launch"); for a plan, no later than its end;
- then: from the artifact, else the default for the kind — roll back or switch off a shipped change, stop an experiment, descope a plan focus or a new roadmap entity.

Only the threshold may be `⚠️ TBD` — the date too, only when the artifact states no date, window or end to derive it from (a roadmap-architect onboard entity, `roadmap-artifacts.md` §8).

**Rules.**
- Never asked; a `⚠️ TBD` cell is counted, not filled by a question.
- Renders in any run where its step runs; it is never in a return payload or a People-contour artifact.
- A user's or product's own template gets it only when the template includes `{{> pre-mortem}}`; built-ins get it inserted.
- The PM edits it at the existing review. A deletion is respected for this artifact and never learned (`self-improvement.md`), and the self-check does not restore it.
- `quarterly-planning` refresh keeps an existing pre-mortem verbatim and never adds one.
- **Read-back:** the quarterly-planning retro (Step 2, in `retro` and `full` modes) and the project-planning replan show each earlier kill criterion whose date has passed as fired / not fired / not measurable. Reading the earlier plan's criteria is allowed; judging them uses only data that step already fetched — anything else is not measurable. A fired criterion joins the step's existing decision-log offer when that offer is made — it never opens one, and asks nothing.
- No other skill or step renders a pre-mortem: not project-planning arcs, sprint plans, the roadmap tree or gap report, focus briefs, task bodies or release notes.

## 8. P6 — the build-first offer (since v3.9.0)

Switch `judgment.build_first` (default `on`; the value is read without a trailing note in brackets, any other value reads as `on`). Two sites only:

| Skill · step | Line |
|---|---|
| `write-concept` · Step 1, inside the brief summary | when no `observed` / `measured` / `reported` evidence covers the concept's riskiest assumption (derived — it also feeds the pre-mortem), names it and the cheapest path that would settle it: a lo-fi prototype shown to 3–5 real users (design-bridge, then product-research), a walk of the as-is flow (flow-walkthrough), or an eval set for an AI behaviour (requirements-creator `ai-feature`); «спершу прототип» / "build first" takes that path |
| `design-bridge` · Step 9, in the closing summary after a prototype is built — only for a build-first upstream or a standalone mid-fi or hi-fi prototype (a standalone lo-fi prototype is drawn by diagram-prototyper without `return_to`, so no Prototype IR describes it) | suggests the prototype as the spec → requirements-creator (screens → functional requirements, shown states → acceptance criteria, missing states → open questions); when the prototype tests an assumption, it first suggests showing it to 3–5 real users |

**Rules.**
- **One line, not a question.** It sits inside the existing confirmation or closing summary, once per run, and its first appearance in a session adds how to switch it off.
- **When it is suppressed.** The line is left out when:
  - (a) evidence covers the assumption — a Step 0.5 hit (taken as context or not) of type `walkthrough`, `ab-test-results` or a research type whose summary addresses it, or a non-`simulated` source the user named that addresses it;
  - (b) the build path was already taken — a `prototype` hit, or a `requirements` hit of subtype `ai-feature` with an eval set (the assumption stays open in the pre-mortem until real-user sessions or eval results exist);
  - (c) the assumption has no cheap build path (e.g. a market-size, pricing or legal question);
  - (d) the concept is not a product change;
  - (e) the run is automated or a return payload;
  - (f) `judgment.build_first` is `off`.

  Step 9 shows it only for a build-first upstream or a standalone mid-fi or hi-fi prototype (a standalone lo-fi one has no Prototype IR) — never after requirements-creator or write-concept Step 8.
- **A prototype is never validation.** It stays `reported (file, frame)` (`data-integrity-protocol.md` 6a), and only real-user sessions on it are evidence.
- **Turning it off.** «вимкни» / "turn off" writes `- **Build first:** off` under the write rules of §2 step 4.
- **The creation steps it routes to are unchanged**, except their hand-off payloads:
  - design-bridge asks none of its Step 1–2 questions for the build-first brief (its values are in the playbook → Step 3 f);
  - requirements-creator skips the Step 1 questions a prototype or the brief already answers and, for a prototype source, leaves out Step 8 option 2 (the low-fi prototype);
  - flow-walkthrough takes the flow, surface and assumption from the payload into its Step 1 scope and asks only what it leaves open;
  - product-research receives the prototype for 3–5 real-user sessions;
  - diagram-prototyper returns a lo-fi prototype to design-bridge on an explicit `return_to: design-bridge` (passed only for the build-first hand-off) and receives the platform with it.

## 9. P8 — learning-preserving modes (since v3.9.0)

Switch `judgment.learning_mode`: `off` (default) · `pm_first` · `explain` (stored since v3.5.0, acts since v3.9.0; read without a trailing note in brackets).

| Skill · step | `pm_first` asks the PM to… |
|---|---|
| `feedback-triage` · end of Step 2 | tag a sample of up to 10 real items (round-robin across channels; not asked below 10 items) with their theme words |
| `meeting-processor` · after the M4 format choice, Discovery / Interview meetings with a verbatim transcript, Structured MoM only | tag 5 interviewee excerpts |
| `product-research` · before Step 3, interview synthesis | tag 10 excerpts, at most 2 per participant |
| `cjm-research` · before pipeline Step 7 | write their own hypothesis (cause → change) for the top 3 gated anomalies — withheld from brainstorm-features 3C so the two sets stay independent |

**Rules.**
- **The question.** One free-text question per run per step, in `user.language`, only in an interactive run under `pm_first`. Never in a scheduled, headless or return-payload run. Its first appearance in a session adds one line on how to skip or switch it off. An interpretation the PM already gave for this material (themes or tags they named in the request or earlier in the run) counts as the answer and is not asked for again, as in §2 step 1.
- **What the PM sees.** Only real items, with personal data masked — never `simulated` or `generated` ones.
- **Answers.** Skip words, partial tags and «вимкни» (writes `- **Learning mode:** off` under §2 step 4) work as in P2.
- **Compare, don't replace.** After the skill's synthesis, one chat block — "Your tags vs mine" (cjm-research names it "Your hypotheses vs mine"), in `user.language` — shows agreement and differences, with the evidence for each. The PM's tags never change a theme, count, rank, ICE score or verdict, never enter the artifact — unless the PM edits the artifact at the existing review, which is a guarded correction (`self-improvement.md` Step 2) — and never set `human-validated: yes`; only the existing explicit confirmation of a theme does that.
- **Chains.** A run chained on the same material (meeting-processor → product-research) passes `pm_first: done | skipped | off` and is never asked twice about it.
- **`explain`.** At the same four steps, one chat-only block, "How I got here": the inputs used, the grouping or scoring rule applied, and the two closest alternatives the skill rejected. It asks nothing and never enters the artifact.
