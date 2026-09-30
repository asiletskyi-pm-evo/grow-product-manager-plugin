# judgment-points.md

> Shared protocol (since v3.7.0). Implements three principles of `pm-mental-model.md` at the judgment points of six skills: **P2 — human hypothesis first** (§2), **P3 — calibrated confidence with a falsifier** (§3) and **P9 — decision ownership and hygiene** (§4–§5). A skill applies this file only at the steps that cite it. The §1 table is the complete list: no other skill, step or mode asks the P2 question or renders the confidence line (`pm-mental-model.md` §5 — a principle acts only through a step that implements it).

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
6. **Nothing else changes.** The P2 question is the only question v3.7.0 adds to a skill run (the configurator's Extended onboarding also offers the switch itself). It is not a gate, and every question a skill already asks keeps its wording and order — except that brainstorm-features' "Choose one" starts from a P2 answer when there is one. When the question is not asked and no estimate is known (step 1), the skill runs as in v3.6.0 apart from the outputs of §3–§5.

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
- **No inflation.** The level is at most `uncertain` when the verdict the lead recommendation acts on is inconclusive, when a metric it rests on is ❌ Blocked or was not cross-validated by the Data Integrity Gate (a single source included), or when the estimate is by analogy. A segment the recommendation explicitly leaves out of its action does not cap it.
- **Weak inputs are named.** A recommendation resting on an assumed or simulated input says so in `most sensitive to`; the evidence labels themselves arrive in v3.8.0.
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
| `evidence_classes` | the evidence classes of the inputs (`pm-mental-model.md` §4) | — | filled from v3.8.0; left out until then |

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
- **Artifacts** — the T-5 self-check, which also fixes a missing or malformed line silently.
- **Decision records** — decision-log's save gate. The level there is the owner's and the gate never changes it: a level above the no-inflation cap is kept, and a "Your estimate vs mine" comparison, when one is shown, names the cap; `unknown (not stated)` and `not recorded` clauses are well-formed in a record (§4).

A line is well-formed when:
- it uses one of the four levels;
- both clauses are specific enough to pass §3;
- the level respects the no-inflation rule.

The artifact-checker has no 4c in v3.7.0, because no maker–checker skill renders the line.
