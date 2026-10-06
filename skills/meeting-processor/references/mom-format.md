# Structured MoM format — Step M6a

> Part of `meeting-processor`. Loaded on demand at Step M6 when the user chose the Structured MoM format; a template selected at Step T takes precedence over this skeleton. The short-summary format (M6b), review and publishing stay in SKILL.md.

Generate the meeting report using the user's preferred language (`user.language`):

```markdown
## Meeting Notes — [Title]

**Date:** [date] | **Duration:** [duration] | **Type:** [grooming, discovery, ...]

**Evidence:** reported — meeting [transcript | notes | recording] [date] (every figure and statement as its named speaker said it; an item of another class carries its own label)

---

### Participants
| Name | Role | Email | Status |
|------|------|-------|--------|
| [name] | [role or "—"] | [email] | Attended / Invited, did not speak / Not on invite |

---

### Topics Discussed
1. **[Topic title]** — [2-3 sentence summary]
2. **[Topic title]** — [2-3 sentence summary]

---

### Decisions
| # | Decision | Context | Owner |
|---|----------|---------|-------|
| 1 | [what was decided] | [why / context] | [who] |

---

### Action Items
| # | Action | Owner | Deadline | Status |
|---|--------|-------|----------|--------|
| 1 | [what needs to be done] | [who] | [when, if mentioned] | Open |

---

### [Type-specific section(s)]
[Content based on meeting type — see M5b; quotes verbatim with speaker and timestamp]

---

### Open Questions
- [unresolved item 1]
- [unresolved item 2]
```
