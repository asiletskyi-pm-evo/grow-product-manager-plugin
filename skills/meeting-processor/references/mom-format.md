# Structured MoM format — Step M6a

> Part of `meeting-processor`. Loaded on demand at Step M6 when the user chose the Structured MoM format; a template selected at Step T takes precedence over this skeleton. The short-summary format (M6b), review and publishing stay in SKILL.md.

Generate the meeting report using the user's preferred language (`user.language`):

```markdown
## Meeting Notes — [Title]

**Date:** [date] | **Duration:** [duration] | **Type:** [grooming, discovery, ...]

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
[Content based on meeting type — see M5b]

---

### Open Questions
- [unresolved item 1]
- [unresolved item 2]
```
