---
name: feedback-triage
version: 0.1.0
description: Triage a stream of user feedback — support tickets, complaints, reviews, Q&A, NPS verbatims — into clustered themes with frequency, severity, and trend scoring, producing a prioritized pain list and hypothesis candidates. Use when the user asks to "triage feedback", "cluster support tickets", "top user complaints for the period", "what hurts buyers/sellers", "feedback themes trend". Українською: "розбери відгуки/скарги", "тріаж фідбеку", "що болить покупцям/продавцям", "кластеризуй support-тікети", "топ проблем за місяць", "тренди тем фідбеку". Do NOT use for deep interview synthesis (product-research or design research-synthesis), saving individual sources (knowledge-library), or ideation (brainstorm-features — chain there after triage).
---

# Feedback Triage

Turns a raw pile of feedback (hundreds of tickets, reviews, Q&A entries) into a ranked map of pains: clustered themes, how often each hurts, how badly, and whether it's growing — with direct chains to hypothesis generation. Built for feedback-ecosystem work where the stream never stops and the question is always "що болить найбільше ЗАРАЗ".

## Prerequisites
- `references/local-context-protocol.md` — Step 0. Optional `Feedback` section in local-context (sources, default folders, segments); if absent — collect ad-hoc and offer to save via the Enrichment Protocol.
- `references/integration-strategy.md` — Google Drive / Confluence / Jira access chains.
- `references/data-policy.md` — **feedback texts are internal data**; clustering and scoring run locally, nothing goes to external LLMs.
- `references/data-integrity-protocol.md` — period completeness applies to trend claims.
- `references/subagent-delegation.md` — large intakes fan out.
- `references/vault-protocol.md` + `references/vault-schema.md` — artifact type `feedback-triage` (Research/feedback/).

## Pipeline

### Step 1 — Intake
1. **Sources** (any mix): uploaded CSV/XLSX exports, Google Drive folders (support tickets), Confluence pages, pasted text, Jira issues (complaint labels). Prefill from the `Feedback` section when configured.
2. **Scope:** period (default: last full month), segment (buyers / sellers / both), product area filter (optional).
3. **Baseline for trends:** search vault for the previous `feedback-triage` artifact of the same segment — if found, this run computes trends against it; if not, this run becomes the baseline (say so).

> **Subagent delegation (large fan-out).** For many files/sources, delegate per `subagent-delegation.md`: batch by source/file, each subagent returns normalized rows (date, channel, segment, text, severity-if-present) — never raw dumps. `data-policy.md` applies to subagents. Inline fallback if unavailable.

### Step 2 — Normalize (Python)
Pandas: dedupe (near-identical texts), parse dates, unify fields, drop empty/noise rows. Report intake stats: total received → usable after cleaning (coverage %). **Gate 2 (data-integrity):** if the period is only partially covered by the data (e.g., export ends mid-month) — flag it; trend claims for that period are blocked or annotated.

### Step 3 — Cluster into themes
Group semantically similar items into themes (language-agnostic — UA/RU/EN feedback lands in one theme). For each theme: name (user's words, not internal jargon), item count, share %, 2-3 verbatim examples, affected segment/platforms, funnel stage guess (per `funnel-templates.md` stages when applicable). Items may belong to one primary theme only; an `other/unclustered` bucket is honest, target < 15 %.

### Step 4 — Score and rank
`pain_score = frequency (share %) × severity (1-3: annoyance / blocks task / money-or-trust loss) × trend multiplier (×1.5 growing, ×1 flat, ×0.7 declining — only when a baseline exists)`.
Rank themes; mark **new** themes (absent in baseline) explicitly — new+growing is the alarm quadrant.

### Step 5 — Report (Step T applies)
Template: `artifact_type: research`, `subtype: feedback-triage`. Structure (fallback):
1. Executive summary — top-3 pains, one alarm insight
2. Intake & coverage (sources, period, usable %, gate flags)
3. Theme map — ranked table: theme, count, share, severity, trend, pain score
4. Top themes in detail — verbatims, segments, platforms, funnel stage
5. Trends vs baseline — new / growing / declining themes
6. Hypothesis candidates — 1-line seed per top theme (full ICE happens in brainstorm-features)
7. Glossary + Sources (source-type markers per `data-integrity-protocol.md`)

Publishing: Confluence (default) / local — ask. Every number carries inline period annotation.

### Step 6 — Chains
- → **`brainstorm-features`**: top pains as hypothesis input (the natural next step — offer first)
- → **design `research-synthesis`**: when themes need deep qualitative synthesis
- → **`cjm-research`**: when pains map to funnel stages with metric impact
- → **`decision-log`**: when triage triggers a priority decision
- → **`task-creator`**: quick-fix themes straight to Jira

### Step V — Save to Vault
`vault_save({type: "feedback-triage", product, skill: "feedback-triage", skill_version: "0.1.0", tags: [segment, period, top theme slugs], content: full report, related: [previous triage artifact, spawned hypotheses], extra_frontmatter: {period, segment, sources_count, items_total, items_usable, top_pain_score}})` → Research/feedback/. This artifact is the baseline for the next run's trends.

## Quality Standards
- Theme names in the users' language of pain, verbatims verbatim (PII stripped: names, emails, order numbers masked).
- Never extrapolate trends without a baseline or from a gate-flagged partial period.
- Counts are computed (Python), not estimated; unclustered share reported honestly.
- Feedback text never leaves the session (`data-policy.md`).
- Language — `user.language`.

## Skill Chaining
← scheduled/manual intake · → brainstorm-features · → research-synthesis (design) · → cjm-research · → decision-log · → task-creator. Monthly scheduled triage — offer via the `schedule` skill after the first successful run.
