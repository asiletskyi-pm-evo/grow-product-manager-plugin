# CJM research pipeline — Steps 4–11 (anomalies → enrichment → hypotheses → impact → verification → risk)

> Part of `cjm-research`. Loaded on demand after the Step 3.5 Data Integrity Gate passes. Initialization, scope, data loading, the gate, report assembly, vault save, and chaining live in SKILL.md.

### Step 4 — Anomaly detection

**Pre-condition:** Step 3.5 (Data Integrity Gate) must be completed. Skip anomaly detection on metrics with status ❌ Blocked. For metrics with status ⚠️ Caveat — inherit the caveat into the anomaly report (do not silently drop the qualifier).

**Continue delegation to `product-analysis` (CJM mode).**

`product-analysis` applies anomaly detection per funnel stage:

1. **Calculate deviation** from baseline for each stage:
   ```
   deviation = ((actual - baseline) / baseline) × 100
   ```

2. **Classify severity** per `references/cjm-protocol.md`:

   | Severity | Condition | Action |
   |----------|-----------|--------|
   | **Critical** | deviation > 25% (negative) | Immediate attention required |
   | **Warning** | deviation 10–25% (negative) | Monitor and investigate |
   | **Info** | deviation < 10% (negative) | Note for context |
   | **Positive** | deviation > 10% (positive) | Highlight as improvement |

3. **Structure output:**

   For each anomaly:
   - Stage name and position in funnel
   - Metric affected (conversion rate, drop-off, absolute value)
   - Baseline value vs actual value (each with its Step 3.5.d annotation and 3.5.g class)
   - Deviation percentage
   - Severity classification
   - Trend direction (worsening / improving / stable)

**Mode branching after Step 4:**

- For `anomalies` mode → **go to Step 11** (assemble Anomalies Report)
- For `health-check` mode → **go to Step 11** (assemble Health-Check Summary)
- For `comparison` mode → **go to Step 11** (assemble Comparison Report) after running Steps 3–4 for all selected platforms
- For `hypotheses` and `full` modes → **continue to Step 5**

### Step 5 — Enrich with WORLD sources

> **Subagent delegation (large fan-out).** For many world enrichment sources (library + internet + Baymard across all detected anomalies), delegate per `references/subagent-delegation.md`: split into batches (by anomaly / funnel stage / search mode), spawn subagents in parallel, each returns a compact structured result (per source: key insight, source type, trust score + source link), and the main agent aggregates (group by stage, dedupe, rank) and derives each source's class from its type (SKILL.md 3.5.g) — a subagent never assigns it. The same pattern applies to Step 6 INTERNAL enrichment (Confluence + GDrive). Falls back to inline if subagents are unavailable.


**Delegate to `knowledge-library` (search modes: library + internet + baymard) and `product-research`.**

**5a. Knowledge Library — local search:**

Call `knowledge-library` in Search mode:
- Query: for each detected anomaly, search by funnel stage category and relevant tags
- Example: anomaly in Cart/Checkout → search categories `cart-checkout`, tags `abandonment, checkout, forms`
- Trust threshold: minimum 0.5 (configurable)
- Return: matching sources with key insights and trust scores

**5b. Web search for benchmarks:**

Delegate to `product-research` for targeted web research:
- Search for industry benchmarks related to each anomaly (e.g., "e-commerce checkout abandonment rate benchmark 2026")
- Search for competitor approaches to the affected funnel stages
- Search for UX best practices relevant to detected problems
- **Important:** Per `data-policy.md`, only use public product names and generic feature descriptions in external searches — never send internal analytics data

**5c. Baymard Premium (if configured):**

If Baymard access is configured in Knowledge Library settings:
- Call `knowledge-library` in Search Baymard mode
- Search for Baymard guidelines matching each anomaly's funnel stage
- Baymard sources get high trust scores (base 0.90)

**5d. Collate world sources:**

Merge all results into a structured enrichment dataset:
- Group sources by funnel stage
- Rank by trust score within each stage
- Note source type (library / web / baymard) and class for the final report's Sources section — `external` for web and Baymard, a library source per its type; a Deep Research claim takes the class of the source it traces to, and an untraceable one is `simulated` (a hypothesis input, never a benchmark)

### Step 6 — Enrich with INTERNAL sources

**Delegate to `knowledge-library` (search modes: confluence + gdrive).**

**6a. Confluence search:**

Call `knowledge-library` in Search Confluence mode:
- Search configured Confluence spaces for: previous CJM research, A/B test results, post-mortems, feature experiment outcomes related to the affected funnel stages
- Extract: experiment results, decisions, metric changes

**6b. Google Drive search:**

Call `knowledge-library` in Search Google Drive mode:
- Search configured folders for: NPS reports, user feedback exports, research presentations, strategy documents
- Extract: relevant findings, quotes (verbatim, `reported` with who and where), data points (`reported` with the document; `measured` only when re-verified through Step 3.5 in this run)

**6c. Merge internal enrichment:**

Combine Confluence and Google Drive findings:
- Match to specific anomalies where possible
- Note: user feedback that correlates with a detected anomaly is strong evidence for hypothesis building — real-user feedback only (a `reported` end-user or customer statement with its source); a PM's or stakeholder's view, or a persona answer, is not user feedback
- All internal data stays internal per `data-policy.md`

### Step 7 — Build hypotheses

**7.0 PM-first hypotheses (since v3.9.0).** `references/judgment-points.md` §9 at this step: `hypotheses` / `full` modes, an interactive run, `judgment.learning_mode` `pm_first` or `explain`; never in `health-check`, `anomalies` or `comparison`. Only this run's own switch counts: a `pm_first` value a caller passes (e.g. feedback-triage) is not read, since a chain passes it only on the same material (§9).
- **The anomalies (`pm_first`).** List the top 3 gated anomalies from Step 4 — fewer when fewer exist; metrics ✅ / ⚠️ from Step 3.5 only; negative ones by severity (Critical, Warning, Info), larger deviation first within a level: stage, metric, deviation with its 3.5.d annotation and 3.5.g class. Inputs only — no cause, hypothesis or score of this skill yet.
- **The question.** One free-text message in `user.language`: for each anomaly, your likely cause → the change you would try. Partial answers count; a skip word skips; «вимкни» / "turn off" writes `- **Learning mode:** off` (§9). The first such question in a session adds one line on how to skip or switch it off.
- **Withheld.** The PM's hypotheses stay in the chat. They are not part of the context passed to the CJM Hypotheses delegation below (its 3C return), so the two sets stay independent; they are never a Feedback Match (a PM's view is not user feedback, Step 6c), never in a debate evidence pack, and never scored, verified (Step 10) or added to the backlog.
- **Your hypotheses vs mine.** Once the report is assembled, in chat before publishing (`references/cjm-reports.md` → Publishing): per anomaly, matched (the same cause and a similar change), differing (with the evidence that separates them — the Feedback / Heuristic Match, enrichment items — or "no evidence decides this — your call") and only yours (listed, not scored). ICE scores and ranks never move toward the PM's.
- **`explain`.** Nothing is asked here; at the same point before publishing, one chat block "How I got here": the anomalies and enrichment used (with their classes), the rule applied (Data Trigger → Feedback / Heuristic Match → hypothesis, ICE with the CJM weighting) and the two closest hypotheses not kept, with why. It asks nothing and never enters the report.

**Delegate to `brainstorm-features` in CJM Hypotheses mode.**

Pass context:
- Structured anomaly list (from Step 4)
- World enrichment data (from Step 5) — benchmarks, best practices, Baymard guidelines
- Internal enrichment data (from Step 6) — experiment results, user feedback, previous research
- Funnel stage configuration (from CJM config)

Receive from `brainstorm-features`:
- Hypothesis list with:
  - **Data Trigger** — the detected anomaly (stage, metric, deviation)
  - **Feedback Match** — correlated user feedback or support tickets (real-user `reported` sources only; never `simulated`)
  - **Heuristic Match** — matching UX best practice from Knowledge Library
  - **Solution** — proposed change
  - **Expected Impact** — estimated conversion lift for the affected stage (a projection: no class; an unsourced lift is `assumed`)
  - **ICE Score** — Impact × Confidence × Ease (with CJM-specific weighting)
  - **Category** — Low-hanging fruit / Structural changes / Business logic changes

For `hypotheses` mode → **continue to Step 8, then go to Step 11** (skip Steps 10–11 risk assessment)

### Step 8 — Calculate impact per hypothesis

**Delegate to `brainstorm-features` (CJM mode) or calculate internally.**

For each hypothesis, calculate per-stage impact:

```
new_stage_conversion = current_stage_conversion × (1 + expected_lift_percent / 100)
```

Per `references/cjm-protocol.md`, apply stage position multipliers for ICE Impact scoring:

| Stage position | Multiplier | Rationale |
|---------------|-----------|-----------|
| Stage 1 (entry) | ×1.5 | Improvements at entry affect all downstream stages |
| Stage 2 | ×1.3 | High leverage — feeds middle funnel |
| Stage 3 | ×1.1 | Important but narrower audience |
| Stage 4+ | ×1.0 | Baseline — affects only late-stage users |

### Step 9 — Calculate impact on overall conversion

**Internal logic (cjm-research).**

Aggregate per-stage impacts into end-to-end funnel impact:

```
current_overall_conversion = stage_1_conv × stage_2_conv × ... × stage_N_conv
new_overall_conversion = new_stage_1_conv × new_stage_2_conv × ... × new_stage_N_conv
absolute_impact = new_overall_conversion - current_overall_conversion
relative_impact = (absolute_impact / current_overall_conversion) × 100
```

Current conversions keep their `measured` class; new and projected ones are projections, marked illustrative and given no class (`references/pm-mental-model.md` §4).

**Rank hypotheses by:**
1. Overall conversion impact (primary)
2. ICE score (secondary)
3. Category — Low-hanging fruit first for quick wins

**Categorize hypotheses:**

| Category | Criteria | Typical timeline |
|----------|----------|-----------------|
| **Low-hanging fruit** | High Ease (7+), moderate Impact | 1–2 sprints |
| **Structural changes** | High Impact, lower Ease, requires significant dev work | 1–2 quarters |
| **Business logic changes** | Requires stakeholder alignment, pricing/policy changes | Cross-functional initiative |

For `hypotheses` mode → **go to Step 12** (assemble report)

### Step 10 — Independent verification

**Internal logic (cjm-research) — uses subagent for objectivity.**

For each hypothesis from Step 7, run verification checks per `references/cjm-protocol.md`:

**10a. Data validity:**
- Does the anomaly still hold after segmenting by platform / locale / user type?
- Is the sample size sufficient for the detected deviation?
- Is the data fresh (collected within the analysis period)?

**10b. Internal evidence cross-check:**
- Do Confluence/GDrive sources support or contradict the hypothesis?
- Were there previous A/B tests that already tested a similar solution?
- If tested before — what were the results? (If negative — hypothesis needs strong new evidence)

**10c. Confidence calibration:**
- If Baymard/industry benchmark supports the hypothesis → Confidence +1–2 points
- If internal experiment supports → Confidence +2–3 points
- If contradicting evidence found → Confidence -2–3 points, flag for discussion
- If the only support is `simulated` or `assumed` → +0 (no boost)

**10d. Dependency and cannibalization analysis:**
- Would implementing hypothesis A invalidate the conditions for hypothesis B?
- Are there hypotheses that must be implemented in a specific order?
- Flag dependent pairs

**10e. Assign verification status:**

| Status | Meaning |
|--------|---------|
| **Confirmed** | Multiple evidence sources support (`simulated` and `assumed` items never count), no contradictions — supported, not a proven cause: stated as the anomaly's cause, it keeps the 3.5.g hand-back line until an A/B test or holdout settles it |
| **Needs more data** | Promising but insufficient evidence — suggest specific data to gather, or the human step (interviews, an experiment) when data cannot settle it |
| **Contradicted** | Evidence found against the hypothesis — recommend not pursuing or re-framing |

### Step 11 — Risk assessment

**Internal logic (cjm-research).**

For each confirmed or needs-more-data hypothesis:

**11a. Technical risk:**
- Implementation complexity
- Dependencies on other systems/teams
- Performance impact potential

**11b. Business risk:**
- Revenue impact if hypothesis is wrong
- User segment affected (new vs returning, high-value vs low-value)
- Reversibility — can we roll back easily? (Feature flag vs permanent change)

**11c. UX risk:**
- Could the change negatively affect other parts of the user journey?
- Is the change consistent with the overall product design language?
- Are there accessibility implications?

**11d. Compile risk matrix:**

| Hypothesis | Technical | Business | UX | Overall | Mitigation |
|------------|-----------|----------|-----|---------|------------|
| [Name] | Low | Medium | Low | Medium | Feature flag, 10% rollout |
| ... | ... | ... | ... | ... | ... |

