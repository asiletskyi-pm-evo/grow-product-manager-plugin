# Data Integrity Protocol

Universal gate for analytical skills in the Grow PM plugin. Referenced by `cjm-research` (Step 3.5), `product-analysis` (Step 1.5), and `product-research` (Step 1.5).

> **Dependencies**: Also read `data-policy.md` (confidentiality), `integration-strategy.md` (MCP fallback chain), and skill-specific protocols before any data operation.

---

## Why this exists

> "Users may make wrong business decisions."

Every number / benchmark / claim in a final report is a potential business decision (priority, budget, timeline, strategy). Verification is a baseline requirement, not optional. This protocol exists to systematically prevent four failure patterns that have caused cascading errors in past CJM research.

## Root-cause patterns (from May 2026 incident)

A single CJM research project produced four progressive errors, each propagated into 5+ derived artifacts before user-side detection. All four share the same root cause class: **uncritical citation of raw data points without period verification, multi-source cross-validation, or context annotation**.

| # | Pattern | Example | Impact |
|---|---------|---------|--------|
| 1 | Incomplete-period extrapolation | Tableau monthly extract on day 7 of month treated as full month → "-77% PoP" | False anomaly investigation, false hypotheses generated |
| 2 | Holiday-week zriz cited as YoY trend | Week 1 (Jan 1-7) deviation cited as full-year trend | False urgency framing, wrong-priority recommendations |
| 3 | Derived claims propagate uncritically | "3.4× faster degradation" propagated to 5+ artifacts before verification | Stakeholders receive false project framing |
| 4 | Missing inline period annotation | "CR 0.99%" cited without period context | Numbers lose meaning when copied (Slack, slides) |

## The 5 Universal Gate Checks

This protocol is implemented as a gate step in each analytical skill. The gate is **MANDATORY** before any output that cites data.

### Gate Check 1: Period/Context Completeness

For internal data (Tableau, CSV, A/B test reports, dashboard screenshots):
- **Verify extract date** vs last data point in the timeseries
- Detect incomplete period: if `last_point_date + period_length > extract_date`, the last point is incomplete
- **Action**: normalize (raw × full_days / actual_days) OR exclude from analysis OR wait for end-of-period

For external data (web research, market reports, competitor data, Baymard guidelines):
- **Verify publication date** / data collection date
- Apply recency thresholds per data type:

| Data type | Recency threshold |
|-----------|-------------------|
| E-commerce CR / AOV benchmarks | ≤ 2 years |
| UX best practices, fundamental research | ≤ 5 years (stable patterns OK longer) |
| Market trends, sizing | ≤ 1 year |
| Competitor pricing, UX details | ≤ 6 months |
| Technology stacks, platform changes | ≤ 6 months |

### Gate Check 2: Seasonal/Cultural Screening

For internal data — detect anomaly weeks/months that overlap with holiday windows:

**Ukraine (default for Prom-context products):**
| Window | Effect |
|--------|--------|
| Week 1 (Jan 1-7) | Heavy holiday effect, low purchase activity |
| Mar 7-8 | Gift-purchase spike |
| Easter ± 1 week (variable date) | Seasonal shift |
| May 1-3 | Holiday effect |
| BF week (4th Thursday of November) | Promotional spike |
| Dec 22-31 | Pre-New Year spike, then drop |

**Global windows (for cross-locale products):**
- Chinese New Year (variable date)
- Diwali (variable date, India)
- Ramadan (variable date)
- US Thanksgiving / Black Friday / Cyber Monday
- Boxing Day (UK/Commonwealth)

**Action when anomaly week aligns with holiday window:**
- ⚠️ FLAG: "Holiday-affected period — interpretation is week-specific, not a trend"
- Search for sustained pattern in non-holiday weeks for cross-confirmation
- For post-release / A/B test: check if test period overlapped holidays → if yes, extrapolation is risky

For external data — verify geographic/cultural relevance:

| Geography fit for Ukraine market | Examples |
|----------------------------------|----------|
| ✅ Direct fit (UA-specific) | Rozetka, OLX, Allo, Epicentrk, Kasta, Makeup.com.ua |
| ✅ CIS/EE comparable | Allegro (PL), eMag (RO), Wildberries/Ozon (RU — political caveat) |
| ⚠️ Global with adaptation | Amazon, eBay, AliExpress |
| ⚠️ Western mature markets | ASOS, Sephora, IKEA (good for UX patterns, but caveat CR/AOV) |
| ❌ Heavily local (do not use as-is) | US-only retailers (Wayfair, Etsy without adaptation) |

### Gate Check 3: Multi-Source Cross-Validation

**Critical metrics** (CR, GMV, Order, Revenue, Retention, Conversion, or any number that will appear in a final report):
- Require **≥ 2 independent sources**
- Acceptable variance: ≤ 15% between sources (accounts for AOV differences, attribution model differences)
- Variance > 15% → ⚠️ FLAG, resolve before reporting

**Source examples:**

For product-analysis / cjm-research:
- 2 different Tableau workbooks
- Tableau + Glint live query
- Tableau + GA Acquisition
- Tableau + A/B test dashboard
- CSV/uploaded report + Tableau dashboard cross-check

For product-research:
- Knowledge Library + web search
- Baymard + Confluence internal experiment
- 2 different competitor sources (their PR + 3rd-party analysis)
- Web search across ≥2 different domains (avoid 2 articles from the same site)
- User research: ≥2 user types / personas with same finding

**Special case — extreme values:**

If any of the following triggers, **auto-promote to ≥3 sources + deep verification**:
- Drop > 25% (negative anomaly)
- Lift > 50% (positive anomaly)
- Sensational claims: "10× growth", "+200% improvement", "#1 in industry", "only player"
- Methodology change suspicion (attribution change, tracking change, dashboard rebuild)

Deep verification adds:
- Methodology change check (read DT-* / DATA-* tickets, Jira release notes for the period)
- Reference week analysis (full YoY table, not single cell)
- Original primary source check (avoid second-hand reporting)
- Date of publication verification

### Gate Check 4: Period/Context Definition Lock + Inline Annotation

**Inline annotation is MANDATORY** for every cited metric in:
- TL;DR / Executive Summary
- Tables
- Bullets
- Charts
- Presentations
- Stakeholder reports
- Slack/chat replies that include numbers

Methodology section at the top is **not sufficient** — readers copy individual numbers into Slack, slides, follow-up docs without surrounding context.

**Annotation convention:**

| Metric type | Inline format |
|-------------|---------------|
| Rolling timeframe | `(12mo rolling, DD.MM.YYYY → DD.MM.YYYY)` |
| Point-in-time snapshot | `(snapshot DD.MM.YYYY)` |
| YoY / PoP comparison | `(YoY, period A vs period B)` |
| Normalized period | `(normalized to N days from K-day extract)` |
| Pilot / A/B test | `(pilot Q1 YYYY, on P% audience, duration D days)` |
| External benchmark | `(Source name, YYYY, geography)` |
| Competitor data | `(Competitor name, YYYY snapshot, source URL)` |

### Gate Check 5: Source Type Marker

Every cited number / claim in the Sources section is marked with type:

**Internal sources:**
- `tableau-mcp` — Tableau retrieved via MCP connector
- `tableau-web` — Tableau retrieved via browser fallback
- `glint-live` — Glint live query
- `ga-snapshot` — Google Analytics snapshot
- `csv-upload` — User-uploaded CSV file
- `screenshot-user` — User-provided screenshot
- `confluence-internal` — Internal Confluence page
- `jira-internal` — Internal Jira tickets

**External sources:**
- `baymard-premium` — Baymard Premium UX-Query / guidelines
- `web-search` — General web search
- `kb-source` — Knowledge Library source (include trust score)
- `competitor-website` — Direct from competitor's site
- `user-research` — User research synthesis (interviews, surveys)
- `deep-research-llm` — ChatGPT/Gemini Deep Research (cross-checked)

This audit trail enables users to verify which retrieval method produced each datapoint.

---

## Output statuses

After running all 5 gate checks, each metric/source gets a status:

- ✅ **Verified** — passed all 5 checks; ready for use in any output
- ⚠️ **Caveat** — passed with limitations (incomplete-period normalized, holiday-affected, single-source pending cross-validation, aging external source, cultural-fit caveat); inherit caveat into report
- ❌ **Blocked** — failed a critical check; do not use in final report without resolution; either gather additional source, exclude metric, or inform user

**If Blocked metrics > 0:**
- Return to data acquisition step to gather missing sources
- Or inform the user that analysis cannot complete without additional inputs
- Never silently drop blocked metrics — surface them explicitly

---

## Mandatory disclosures in final reports

For any metric / claim cited in the final report:

1. **Inline period/context annotation** (Gate Check 4)
2. **Source count** in Sources section, with type markers (Gate Check 5)
3. **Caveat inheritance** — if metric was ⚠️ Caveat, the caveat must be visible in the section that cites it
4. **Holiday/period flag** for any metric where Gate Check 2 raised a flag
5. **Methodology change disclosure** for any metric where Gate Check 3 deep verification was triggered

---

## Anti-patterns (from real incidents)

### Anti-pattern 1: Incomplete-period extrapolation

> "Sessions 01.05.2026 = 1.28M vs квітень 5.69M = -77% PoP organic catastrophe"

**Reality:** 01.05.2026 = 7 days of data (extract was 8.05.2026). Normalized: 1.28M × 30/7 = 5.49M ≈ April 5.69M. No catastrophe.

### Anti-pattern 2: Week-1 YoY trap

> "Listing GMV -29% YoY proти Portal GMV -8.6% YoY. Каталог деградує 3.4× швидше за маркетплейс."

**Reality:** This is Week 1 (Jan 1-7) holiday zriz from Listing metrics workbook 285 YtoY view. Across 18 of 19 weeks in 2026, both Listing and Portal GMV are **growing** YoY (+20% / +42% in May). Listings lose share (19.6% → 16.4%), not absolute volume.

### Anti-pattern 3: Cascading derived claim

A single uncritical "-29%/-8.6%/3.4×" propagated into 5+ artifacts:
- CJM diagnostics v.1-v.3
- Project Mission v.3-v.5
- Triangulation v.1-v.3
- Phase 3 v.1-v.3
- Various Obsidian local copies

Re-verification at each propagation step would have caught this earlier.

### Anti-pattern 4: Missing inline-period annotation

> "Catalog CR 0.99%" — without period, source, methodology

**Reality:** Reader cannot tell if this is 12mo rolling, Q1 2026, snapshot, or all-time average. Number loses meaning the moment it is copied out of the original document.

---

## Correct patterns

### Pattern 1: Verified period
> "Sessions May 2026 normalized: 1.28M × 30/7 = 5.49M (full-month equivalent from 7-day extract on 8.05.2026, Tableau workbook 397)"

### Pattern 2: Holiday-aware YoY
> "Listing GMV +20% YoY (May 2025 → May 2026, weeks 18-19 of both years, non-holiday window). Cross-validated: workbook 285 YtoY view + Orders Dashboard v2 Portal vs Sites (order count +51% YoY in same week)."

### Pattern 3: Re-verified derived claim
> "Catalog grows +20% YoY but slower than Portal (+42% YoY) — share decline 19.6% → 16.4% (workbook 285 YtoY, cross-validated). NOT '3.4× faster degradation' (that was Week 1 holiday-zriz, not a trend)."

### Pattern 4: Inline-period annotation
> "Catalog CR 0.99% (12mo rolling, 1.05.2025 → 7.05.2026, Listing metrics workbook 285 Overview view, cross-validation pending on Master CJM 125)"

---

## Cross-skill applicability

| Skill | Step name | Trigger |
|-------|-----------|---------|
| `cjm-research` | Step 3.5 — Data Integrity Gate | Between Step 3 (Load CJM data) and Step 4 (Anomaly detection) |
| `product-analysis` | Step 1.5 — Data Integrity Gate | Between Step 1 (Initialization and data acquisition) and Step 2 (Analysis engine) |
| `product-research` | Step 1.5 — Source Validation Gate | Between Step 1 (Deep discovery) and Step 2 (Research execution) |
| `brainstorm-features` (optional) | ICE Confidence adjustment | Apply trigger-data status to Confidence score (Verified = no adjustment, Caveat = -1 to -2, Blocked = -3 + warning) |

---

## Implementation order

When a skill invokes this protocol:

1. Acquire all candidate metrics / sources (skill-specific step)
2. Apply Gate Check 1 (Period/Context Completeness) to each → mark as Pass/Fail
3. Apply Gate Check 2 (Seasonal/Cultural Screening) to each → mark as Pass/Flag
4. Apply Gate Check 3 (Multi-Source Cross-Validation) to each → mark as Pass/Caveat/Fail
5. Apply Gate Check 4 (Inline Annotation) format → prepare annotated strings
6. Apply Gate Check 5 (Source Type Marker) → tag each source
7. Compute status per metric: ✅ Verified / ⚠️ Caveat / ❌ Blocked
8. If any Blocked → halt or inform user before proceeding
9. Pass Verified/Caveat metrics to the next analysis step
10. Carry caveats through to the final report

---

## Recommended Prom.ua reference sources catalog

For Prom.ua-specific cross-validation (extend in `cjm-protocol.md`):

| Метрика | Primary source | Cross-validation | Methodology doc |
|---------|----------------|------------------|-----------------|
| Listing GMV YoY | Listing metrics workbook 285 YtoY view | Orders Dashboard v2 Portal vs Sites | DT-1773 attribution |
| Portal GMV YoY | Listing metrics workbook 285 YtoY view | Orders Dashboard v2 | — |
| Catalog CR | Listing metrics workbook 285 Overview | Master CJM 125 funnel + Glint live | — |
| Search CR | Listing metrics workbook 285 Overview | Master CJM 125 funnel | — |
| Direct/Paid/Organic mix | Workbook 533 (First Page) | Master CJM 125 + GA Acquisition | — |
| Stage drop-off | Master CJM 125 funnel | CJM listing workbook 285 sub-segments | — |
| App vs Web CR | Master CJM 125 by platform | Listing metrics_app workbook | — |
| Auto Exit Rate | AutoMoto Metrics workbook | Master CJM 125 Auto segment | — |

This catalog is product-specific; other organizations should build their own in `local-context.md` under a `data_sources_catalog` section.
