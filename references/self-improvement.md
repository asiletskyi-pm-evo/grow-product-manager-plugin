# Self-Improvement Protocol

This protocol applies to ALL skills in the Grow Product Manager plugin. It runs at the very end of a skill's execution, after the main workflow is complete and the user has confirmed the final result.

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
- The user simply confirms "OK" / "все добре"
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
- **Scope of improvement** — Would the fix improve only this skill, or should it apply to multiple skills?

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
