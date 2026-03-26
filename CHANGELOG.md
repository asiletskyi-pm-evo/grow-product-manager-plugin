# Changelog — Grow Product Manager Plugin

All notable changes to this plugin are documented here.

Version format: `MAJOR.MINOR.PATCH`
- **MAJOR** — breaking changes, full workflow restructure across multiple skills
- **MINOR** — new skill added, new step/section in existing skill, significant workflow addition
- **PATCH** — wording fix, small content addition, formatting change, bug fix in skill logic

Each skill also carries its own version in the frontmatter (`version:` field in SKILL.md).
When a skill changes, its version is bumped independently. The plugin version is bumped to reflect the highest-impact change among all updated skills.

---

## [0.4.0] — 2026-03-26

### Plugin
- Added versioning system for skills and plugin: `version` field in all SKILL.md frontmatter
- Added `CHANGELOG.md` (this file)
- Added versioning rules to `references/self-improvement.md`
- Added versioning protocol to `skills/plugin-configurator/SKILL.md` (step 4 — Implement improvement)

### Skills changed
| Skill | From | To | Change type |
|-------|------|----|-------------|
| brainstorm-features | 0.3.0 | 0.4.0 | minor — version field added |
| feature-task-creator | 0.3.0 | 0.4.0 | minor — version field added |
| plugin-configurator | 0.3.0 | 0.4.0 | minor — versioning protocol added |
| product-analysis | 0.3.0 | 0.4.0 | minor — version field added |
| product-research | 0.3.0 | 0.4.0 | minor — version field added |
| requirements-creator | 0.3.0 | 0.4.0 | minor — version field added |
| write-concept | 0.3.0 | 0.4.0 | minor — version field added |

---

## [0.3.0] — 2026-03-25

### Plugin
- Translated all skill instructions and reference files to English
- Output language remains controlled by `user.language` in `local-context.md`

### Skills changed
| Skill | From | To | Change type |
|-------|------|----|-------------|
| brainstorm-features | 0.2.0 | 0.3.0 | minor — full EN translation of workflow instructions |
| feature-task-creator | 0.2.0 | 0.3.0 | minor — full EN translation of workflow instructions |
| plugin-configurator | 0.2.0 | 0.3.0 | minor — full EN translation of all UI strings |
| product-analysis | 0.2.0 | 0.3.0 | minor — full EN translation of workflow instructions |
| product-research | 0.2.0 | 0.3.0 | minor — full EN translation of workflow instructions |
| requirements-creator | 0.2.0 | 0.3.0 | minor — full EN translation, requirements template translated |
| write-concept | 0.2.0 | 0.3.0 | minor — full EN translation of workflow instructions |

---

## [0.2.0] — 2026-03-25

### Plugin
- Added `plugin-configurator` skill with onboarding, update, validate, and view modes
- Added `local-context.md` support (org-specific config, gitignored)
- Added `references/local-context-protocol.md` — auto-trigger and enrichment protocol
- Added `references/self-improvement.md` — self-improvement protocol for all skills
- Added `references/context-schema.md` — full schema for `local-context.md`

### Skills changed
| Skill | From | To | Change type |
|-------|------|----|-------------|
| plugin-configurator | — | 0.2.0 | new skill |
| brainstorm-features | 0.1.0 | 0.2.0 | minor — local-context integration |
| feature-task-creator | 0.1.0 | 0.2.0 | minor — local-context integration |
| product-analysis | 0.1.0 | 0.2.0 | minor — local-context integration |
| product-research | 0.1.0 | 0.2.0 | minor — local-context integration |
| requirements-creator | 0.1.0 | 0.2.0 | minor — local-context integration |
| write-concept | 0.1.0 | 0.2.0 | minor — local-context integration |

---

## [0.1.0] — initial release

### Skills
- brainstorm-features
- feature-task-creator
- product-analysis
- product-research
- requirements-creator
- write-concept
