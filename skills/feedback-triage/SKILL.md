---
name: feedback-triage
version: 0.7.1
description: Triage a feedback stream — tickets, complaints, reviews, NPS — into themes with frequency, severity and trend. Not interview synthesis (product-research), not ideation (brainstorm-features). UA — «розбери скарги/відгуки», «кластеризуй тікети», «тренд тем скарг». EN — "triage feedback".
---

# Feedback Triage

> **Path rule.** A bare `references/<file>.md` in this file is read from this skill's own `references/` if the file exists there, otherwise from the **shared** `references/` at the plugin root. Resolve the root as `${PLUGIN_ROOT}`, else `${CLAUDE_PLUGIN_ROOT}`, else the directory that contains `skills/`, found by walking up from this folder (`references/host-profiles.md` §6). Never continue without a protocol named here.

Turns a raw pile of feedback (hundreds of tickets, reviews, Q&A entries) into a ranked map of pains: clustered themes, how often each hurts, how badly, and whether it's growing — with direct chains to hypothesis generation. Built for feedback-ecosystem work where the stream never stops and the question is always "що болить найбільше ЗАРАЗ".

## Prerequisites
- `references/local-context-protocol.md` — Step 0. Optional `Feedback` section in local-context (sources, default folders, segments); if absent — collect ad-hoc and offer to save via the Enrichment Protocol.
- `references/integration-strategy.md` — Google Drive / Confluence / Jira access chains.
- `references/data-policy.md` — **feedback texts are internal data**; clustering and scoring run locally, nothing goes to external LLMs.
- `references/data-integrity-protocol.md` — Gate Check 1 (period completeness) applies to trend claims (Step 2); since v3.8.0 Gate Check 6 (evidence class + frontier) runs in Step 4.
- `references/subagent-delegation.md` — large intakes fan out.
- `references/communication-frameworks.md` — task-formulation standard for the SH step.
- `references/vault-protocol.md` + `references/vault-schema.md` — artifact type `feedback-triage` (Research/feedback/).

> **Judgment contract (Step 0j).** Per `references/local-context-protocol.md` Step 0j and `references/pm-mental-model.md`: note this run's
> judgment points (score, rank, verdict, priority, ship/kill, debate question) internally, with no output. A principle acts only through
> a step that implements it — until one exists here, this skill's questions, gates and output stay exactly as they are.

## Pipeline

### Step 1 — Intake
1. **Sources** (any mix): uploaded CSV/XLSX exports, Google Drive folders (support tickets), Confluence pages, pasted text, Jira issues (complaint labels). Prefill from the `Feedback` section when configured. Each item keeps its `origin`, read from what the material shows and never asked (Gate Check 6a): `user` (a real user's own text), `summary` (an AI or agent summary of an identifiable real ticket) or `generated` (no real originating user — sample or synthetic reviews, persona answers; only on an explicit marker); an item that shows nothing counts as `user`; an interactive run prints one notice line when it sets items aside as `generated`.
2. **Scope:** period (default: `feedback.default_period`, else last full month), segment (from `feedback.segments`; ask when unset — a two-sided marketplace splits buyers/sellers, SaaS splits by plan or role, so there is no universal default), product area filter (optional).
3. **Baseline for trends:** search vault for the previous `feedback-triage` artifact of the same segment — if found, this run computes trends against it; if not, this run becomes the baseline (say so).

> **Subagent delegation (large fan-out).** For many files/sources, delegate per `subagent-delegation.md`: batch by source/file, each subagent returns normalized rows (date, channel, segment, text, severity-if-present, origin, item id) — never raw dumps; the main agent derives classes. `data-policy.md` applies to subagents. Inline fallback if unavailable.

### Step 2 — Normalize (Python)
Pandas: dedupe (near-identical texts), parse dates, unify fields, drop empty/noise rows. Report intake stats: total received → usable after cleaning (coverage %); `generated` items are counted on their own, outside usable %. **Gate Check 1 (data-integrity):** if the period is only partially covered by the data (e.g., export ends mid-month) — flag it; trend claims for that period are blocked or annotated.

**PM-first pass (since v3.9.0)** (`references/judgment-points.md` §9): with `judgment.learning_mode` `pm_first`, in an interactive run, the intake-stats message ends with one free-text question — tag these items with your own theme words; partial tags count, a skip word skips, «вимкни» / "turn off" writes `- **Learning mode:** off` (§9). The items: 10 drawn round-robin across channels, oldest first within a channel — `user` items only, never `summary` (AI summaries) or `generated` ones — masked as Quality Standards require; with fewer than 20 `user` items the sample is half of them, and below 10 there is no question. The first such question in a session adds one line on how to skip or switch it off. The monthly scheduled run never asks; `explain` asks nothing here.

### Step 3 — Cluster into themes
Group semantically similar items into themes (language-agnostic — UA/RU/EN feedback lands in one theme). Every item except `generated` ones is clustered. For each theme: name (user's words, not internal jargon), item count, share %, 2-3 verbatim examples (`user` items only — channel, date, item id · `reported`), affected segment/platforms, funnel stage guess (`[assumed — …]`, per `funnel-templates.md` stages when applicable). Items may belong to one primary theme only; an `other/unclustered` bucket is honest, target < 15 %. Themes come from the items alone: a PM-first tag changes no theme, count, share, verbatim, pain score or rank (`references/judgment-points.md` §9).

### Step 4 — Score and rank
`pain_score = frequency (share %) × severity (1-3: annoyance / blocks task / money-or-trust loss) × trend multiplier (×1.5 growing, ×1 flat, ×0.7 declining — only when a baseline exists)`.
Rank themes; mark **new** themes (absent in baseline) explicitly — new+growing is the alarm quadrant.
**Gate emphasis (since v3.6.0)** (`references/data-integrity-protocol.md` → Gate emphasis): with `triangulation` in `role_defaults.gate_emphasis`, a theme carried by one source type only (e.g. tickets but not reviews) gets a ⚠️ caveat line — indicative, not conclusive (n = its items, or distinct users when the data has them; method = its channels); with `human-validated`, each theme carries `human-validated: yes` only when the user explicitly named or confirmed that theme in this session — a PM-first tag never counts (`references/judgment-points.md` §9) — `no` otherwise. Caveat lines and flags only — never a question, never a changed pain score or rank.
**Evidence classes and frontier (since v3.8.0)** (`references/data-integrity-protocol.md` Gate Check 6): item counts, shares and trends computed in Steps 2–4 are `measured`, verbatims and summaries of real tickets `reported`; `generated` items are `simulated` — never in a theme, a theme count, share, verbatim or pain score, only on one `Simulated input — hypotheses only` line under Hypothesis candidates, shown only when such items exist. A cause the report attributes to a theme that its items do not state (a release, a policy change, a motive) gets one hand-back line; a theme with no attributed cause gets none. The line sits in the theme's detail, worded in `user.language` with the human step (read the full tickets, call 5 users of the segment, check the release log with the team) — never a question, never a changed pain score or rank. The monthly scheduled run writes labels only: such a claim reads `[assumed — frontier: <human step>]`. When the baseline predates v3.8.0 and an interactive run set `generated` items aside, Trends carries one comparability ⚠️ line; the scheduled run adds none.

### Step 5 — Report (Step T applies)
Template: `artifact_type: research`, `subtype: feedback-triage`. Structure (fallback):
1. Executive summary — top-3 pains, one alarm insight
2. Intake & coverage (sources, period, usable %, gate flags, `generated` items set aside)
3. Theme map — ranked table: theme, count, share, severity, trend, pain score; one group label for its counts (`Evidence: measured — <sources>, <period>`)
4. Top themes in detail — verbatims, segments, platforms, funnel stage
5. Trends vs baseline — new / growing / declining themes
6. Hypothesis candidates — 1-line seed per top theme, worded as a hypothesis (full ICE + PRO happens in brainstorm-features)
7. **SH step — pain → well-formulated task.** For each **priority** pain, reframe it as "an insufficiently well-formulated task" and produce a task formulation to the **task-creator standard** (`references/communication-frameworks.md` → task formulation: perfective-verb title + why/what/how, DoD for critical ones). Turns raw complaint into an actionable, verb-first statement ready for `task-creator`.
8. Glossary + Sources (source-type markers per `data-integrity-protocol.md`, each with its evidence class)
9. Role extra sections (since v3.6.0) — each `role_defaults.extra_sections.research` partial (e.g. `repository-entry`) the report lacks, inserted by T-5 step 3b above the judgment footer, with a custom template too; derived, never asked

**Your tags vs mine / How I got here (since v3.9.0)** (`references/judgment-points.md` §9): in chat after Step 4 and before the publishing question, never in the report, never in a scheduled, headless or return-payload run. Under `pm_first` with an answer, "Your tags vs mine": per tagged item, the PM's tag next to the theme Step 3 gave it; which PM tag was matched to which theme (the matching is this skill's, shown so the PM can check it); agreements; and for each difference the items that separate them, or "no evidence decides this — your call". Under `explain`, "How I got here": the inputs used (sources, period, usable items), the grouping rule and the pain-score formula applied, and the two closest alternatives rejected (a merge or a split of themes). Neither asks anything, and neither moves a theme, count or rank toward the PM's.

Publishing: Confluence (default) / local — ask (a scheduled run asks nothing: it publishes where its schedule prompt names a destination, else saves locally; a Confluence write still meets the host write gate). Every number carries inline period annotation; every count, share, trend and verbatim also carries its evidence class (Step 4).

**Judgment footer (since v3.5.0).** The artifact closes with the altitude line from `templates/built-in/partial/judgment-footer-v1.md` (`references/template-protocol.md` T-5 step 3a; checked by `references/artifact-style-gate.md` Gate 4a).

### Step 6 — Chains
- → **`brainstorm-features`**: top pains as hypothesis input (the natural next step — offer first)
- → **design `research-synthesis`**: when themes need deep qualitative synthesis
- → **`cjm-research`**: when pains map to funnel stages with metric impact (no `pm_first` is passed — funnel anomalies are not this run's material, `references/judgment-points.md` §9)
- → **`decision-log`**: when triage triggers a priority decision
- → **`task-creator`**: quick-fix themes straight to Jira (the SH-step formulations feed directly in)

### Step V — Save to Vault
`vault_save({type: "feedback-triage", product, skill: "feedback-triage", skill_version: "0.7.1", tags: [segment, period, top theme slugs], content: full report, related: [previous triage artifact, spawned hypotheses], extra_frontmatter: {period, segment, sources_count, items_total, items_usable, top_pain_score}})` → Research/feedback/. This artifact is the baseline for the next run's trends.

## Quality Standards
- Theme names in the users' language of pain, verbatims verbatim (PII stripped: names, emails, order numbers masked) — a masked `[name]` / `[order]`, a marked `[…]` or a `(translated)` verbatim stays `reported`; a paraphrase or a ticket summary is never shown in quote marks.
- Never extrapolate trends without a baseline or from a gate-flagged partial period.
- Counts are computed (Python), not estimated; unclustered share reported honestly.
- Feedback text never leaves the session (`data-policy.md`).
- Language — `user.language`.

## Skill Chaining
← scheduled/manual intake · → brainstorm-features · → research-synthesis (design) · → cjm-research · → decision-log · → task-creator. Monthly scheduled triage — offer via the `schedule` skill after the first successful run.

## Routing

The `description` above is short on purpose: a host with many skills shows only part of the skill listing, or skill names alone (`references/host-profiles.md` §7). The full set of phrases and boundaries that route here, as the description carried them up to v3.10.0:

> Triage a feedback stream — tickets, complaints, reviews, NPS — into themes with frequency, severity and trend. Not interview synthesis (product-research), not ideation (brainstorm-features). UA — «розбери скарги/відгуки», «кластеризуй тікети», «що болить сегменту», «тренд тем скарг». EN — "triage feedback", "cluster support tickets", "top user complaints for the period", "what hurts a given user segment", "feedback themes trend". Also UA — «тріаж фідбеку», «топ проблем за місяць». Produces a pain list and hypothesis candidates; do NOT use to save individual sources (knowledge-library); chain to brainstorm-features after triage.
