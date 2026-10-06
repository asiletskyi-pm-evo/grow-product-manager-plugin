# Self-Improvement Protocol

This protocol applies to ALL skills in the Grow Product Manager plugin. It runs at the very end of a skill's execution, after the main workflow is complete and the user has confirmed the final result. The Step 2 judgment guard (since v3.9.0) applies at the review step of every skill outside the People contour, also one whose SKILL.md names no self-improvement check.

---

## Purpose

Continuously improve the quality of the plugin's skills by learning from user corrections. When a user points out an error or asks for changes, analyze whether the skill's algorithm can be improved to prevent similar issues in the future.

---

## When to Trigger

This protocol activates **only when the user provides corrections or feedback** during the final review step of any skill. It does NOT trigger if the user confirms the result without changes.

**Trigger conditions:**
- The user asks to fix something in the output
- The user points out a mistake or omission
- The user asks for changes to the structure, format, or content
- The user provides feedback that suggests the skill missed something it should have caught

**Do NOT trigger if:**
- The user simply confirms "OK" / "all good"
- The corrections are purely content-specific (unique to this particular task, not a pattern)
- The user explicitly says not to change the plugin

---

## Protocol Steps

### 1. Apply the corrections

First and foremost — fix what the user asked to fix. Complete all requested changes and get user confirmation that the result is now correct.

### 2. Analyze the root cause

After the corrections are applied and confirmed, internally analyze:

- **What went wrong?** — What did the skill produce incorrectly or miss?
- **Why did it go wrong?** — Is this a gap in the skill's instructions, a missing step, an unclear condition, or an edge case not covered?
- **Is this a pattern?** — Could this same issue occur in future runs of this skill, or was it a one-off situation unique to this task?
- **Is it a judgment-guard correction?** (since v3.9.0, Principle 5 of `pm-mental-model.md`) — a correction whose only effect is to remove or soften a counter-argument (a pre-mortem, kill criteria, a minority report, a Skeptic objection), a hand-back line, a confidence line or an evidence label; to turn a `simulated` / `assumed` item into a finding; or to move the skill's score, rank, verdict, theme, extraction or hypothesis to the PM's — including the PM's tags after a "Your tags vs mine" comparison — without new evidence ("agree more"). It is applied to this artifact only and never proposed as a skill change. Say so in one chat line in `user.language` that names the removed kinds, never their content (e.g. "Applied here only — removing a pre-mortem is not learned as a rule"). There is no other log. A removed footer or confidence line is not re-added on a re-render of this artifact (`template-protocol.md` T-5 step 3a).
  - **A mixed correction is split:** its guarded part is a one-off with the chat line; the rest follows the normal flow.
  - **`assumed` / `simulated` labels are the exception:** the label stays, or its item is dropped, and `simulated` content stays out of a findings section (`artifact-style-gate.md` Gate 4b §6, `template-protocol.md` T-5 step 3c). That gate's one line is the chat line — no second line, and no "applied here only" claim for it.
  - **A confidence line** also covers raising its level above the no-inflation cap: an artifact keeps the cap (Gate 4c, `judgment-points.md` §6) and the chat line says so; a decision record keeps the owner's level.
  - **Not in People-contour skills:** their corrections follow Steps 2–4 as before.
- **Scope of improvement** — Would the fix improve only this skill, or should it apply to multiple skills?

#### Harness-first diagnosis (run before proposing a fix)

Most agent failures are **configuration failures**, not model failures — the fix usually lives in the harness around the skill, not in "smarter" prose. Before proposing an improvement, classify the failure by harness layer and route the fix to the right place. See `references/harness-map.md` for the plugin's full harness anatomy.

| Harness layer | Diagnostic question | Where the fix goes |
|---------------|---------------------|--------------------|
| **Instructions** | Was the skill's core/description too loose or ambiguous? | SKILL.md description / core step wording |
| **Tools** | Was an MCP/tool missing, or its "when to call" prose unclear? | `integration-strategy.md` / tool-usage prose in the skill |
| **Context** | Wrong static/dynamic split — a needed field missing, or context overloaded with noise? | `local-context-protocol.md` (static-dynamic boundary) |
| **Guardrails** | Was a gate/check skipped (e.g. Data Integrity, data-policy)? | `data-integrity-protocol.md` / add a gate step |
| **Orchestration** | Did the wrong skill fire, or did delegation misroute? | description "Do NOT use" hints / `subagent-delegation.md` |
| **Observability** | Would we have caught this at all before the user did? | add/extend an output-eval rubric (`testing/output-evals.md`) |

Pick the **single** layer that is the true root cause (not the symptom). If the honest answer is "we had no way to catch this," the fix is an observability fix (an eval), even when a prose tweak also helps.

### 3. Propose improvement (if applicable)

If the analysis reveals a **pattern-level issue** (something that could recur), propose a specific improvement to the user:

> "During execution I made an error in [X]. To reduce the likelihood of this error in the future, I can improve the conditions of the [Skill Name] skill:
>
> **Current behavior:** [what the skill does now]
> **Proposed improvement:** [what should change]
> **How this helps:** [why this prevents the error]
>
> Would you like me to apply this improvement to the plugin?"

**Important guidelines for proposals:**
- Be specific — describe the exact change to the skill's algorithm, not vague "improve quality"
- Be minimal — propose the smallest change that fixes the pattern, don't over-engineer
- Be honest — if the correction was a one-off (user preference, unique context), say so and don't propose a skill change
- Judgment guards are never unlearned (Principle 5 of `pm-mental-model.md`; evidence labels since v3.8.0, the rest since v3.9.0) — a judgment-guard correction (Step 2) is never proposed as a skill change, in this protocol or in any skill's own self-improvement check; treat it as a one-off under the rule above, with the one chat line of Step 2. A correction that adds evidence, or fixes a wrong number, is a normal correction
- Multiple improvements — if several improvements are identified, present them as a numbered list and let the user choose which to apply

### 4. Implement improvement (if user agrees)

If the user agrees to the proposed improvement:

1. **Identify the target file(s)** — which SKILL.md file(s) need to change
2. **Make the edit** — update the specific section of the skill's algorithm (workflow step, condition, quality standard, or formatting requirement)
3. **Bump the skill version** — update the `version:` field in the frontmatter of each changed SKILL.md according to the versioning rules:
   - `PATCH` (x.x.X+1) — wording fix, small content addition, formatting change
   - `MINOR` (x.X+1.0) — new step, new section, significant workflow addition
   - `MAJOR` (X+1.0.0) — full workflow restructure, breaking change in logic
4. **Bump the plugin version** in `plugin.json` — use the highest-impact rule among all changed skills:
   - Any skill PATCH → plugin PATCH
   - Any skill MINOR → plugin MINOR
   - Any skill MAJOR → plugin MAJOR
5. **Update CHANGELOG.md** — add a new entry at the top in the format:

```
## [X.Y.Z] — YYYY-MM-DD

### What changed
- [brief description of improvement and why it was needed]

### Skills changed
| Skill | From | To | Change type |
|-------|------|----|-------------|
| skill-name | old-version | new-version | patch/minor/major — what was changed |
```

6. **Show the change** — briefly describe what was changed and where
7. **Re-package the plugin** — create an updated `.plugin` file and provide it to the user

If the user agrees to some improvements but not others — apply only the approved ones, bump versions only for the applied changes.

If the user declines — respect the decision and end the workflow.

---

## Types of Improvements

Common categories of improvements that may emerge:

| Category | Example |
|----------|---------|
| **Missing step** | Skill didn't check for X before proceeding → add a check step |
| **Unclear condition** | Skill applied rule A when rule B was appropriate → clarify the condition |
| **Formatting issue** | Output didn't match expected format → add explicit formatting requirement |
| **Missing context** | Skill didn't ask about Y, which turned out to be important → add Y to context gathering |
| **Wrong default** | Skill assumed X by default, but user always changes it → change the default |
| **Edge case** | Skill failed on a specific scenario → add handling for that scenario |
| **Integration gap** | Skill didn't use tool Z when it should have → add Z to the workflow |
| **Quality standard** | Output quality was below expectation in area X → add quality check for X |

---

## Important Constraints

- **Never change skills without user approval** — always ask first
- **Never remove existing functionality** — improvements should add or refine, not remove
- **Preserve skill structure** — keep the same step numbering and overall flow unless the user explicitly wants restructuring
- **Document the change** — when editing a SKILL.md, make the change clear and traceable
- **Cross-skill awareness** — if the improvement applies to multiple skills (e.g., a shared pattern like Confluence formatting), propose updating all relevant skills
