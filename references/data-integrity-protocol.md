# Data Integrity Protocol

Universal gate for analytical skills in the Grow PM plugin. Referenced by `cjm-research` (Step 3.5), `product-analysis` (Step 1.5), `product-research` (Step 1.5), and `feedback-triage`.

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

**Ukraine** (apply when local-context → `product.primary_market` is UA):
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
- Tableau + an internal live-metrics query
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
- `internal-live` — internal live-metrics tool query
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

## Anti-patterns

Each is a real failure shape, illustrated on a **fictional** product with two revenue streams (Marketplace and Storefront). Substitute your own metrics — the arithmetic is the lesson, the numbers are not data.

### Anti-pattern 1: Incomplete-period extrapolation

> "Sessions 01.06.2026 = 1.10M vs May 4.60M = -76% PoP — organic catastrophe"

**Reality:** 01.06.2026 held 7 days of data (the extract ran on 8.06.2026). Normalized: 1.10M × 30/7 = 4.71M ≈ May's 4.60M. No catastrophe — the period was incomplete, not the traffic.

### Anti-pattern 2: Week-1 YoY trap

> "Marketplace GMV -29% YoY vs Storefront GMV -8.6% YoY. Marketplace is degrading 3.4× faster."

**Reality:** that window is Week 1 (Jan 1-7) — a holiday cut. Across 18 of the year's other 19 weeks, **both** streams grow YoY. The real story is a share shift (Marketplace 19.6% → 16.4% of the mix), not an absolute decline — and a ratio of two holiday artifacts ("3.4× faster") is an artifact squared.

### Anti-pattern 3: Cascading derived claim

A single unverified "-29% / -8.6% / 3.4×" propagated into 5+ artifacts: CJM diagnostics v.1-v.3, the project mission deck v.3-v.5, the triangulation doc v.1-v.3, the phase plan v.1-v.3, plus local vault copies. Re-verification at each propagation step would have caught it at step 1 instead of step 5.

### Anti-pattern 4: Missing inline-period annotation

> "Checkout CR 0.99%" — no period, no source, no methodology

**Reality:** the reader cannot tell whether this is 12-month rolling, one quarter, a snapshot, or an all-time average. The number loses its meaning the moment it is copied out of the document it was born in.

---

## Correct patterns

The same four claims, written so they survive being copied out of context (same fictional product).

### Pattern 1: Verified period
> "Sessions June 2026 normalized: 1.10M × 30/7 = 4.71M (full-month equivalent from a 7-day extract on 8.06.2026, `<sessions workbook>`)"

### Pattern 2: Holiday-aware YoY
> "Marketplace GMV +20% YoY (June 2025 → June 2026, weeks 22-23 of both years, non-holiday window). Cross-validated: `<GMV workbook>` YtoY view + `<orders dashboard>` (order count +51% YoY in the same week)."

### Pattern 3: Re-verified derived claim
> "Marketplace grows +20% YoY but slower than Storefront (+42% YoY) — mix share 19.6% → 16.4% (`<GMV workbook>` YtoY, cross-validated). NOT '3.4× faster degradation' — that was a Week-1 holiday cut, not a trend."

### Pattern 4: Inline-period annotation
> "Checkout CR 0.99% (12mo rolling, 1.06.2025 → 7.06.2026, `<funnel workbook>` Overview view, cross-validation pending on `<CJM master dashboard>`)"

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

## Reference sources catalog

Gate Check 3 (Multi-Source Cross-Validation) needs to know **which second source** validates a given metric. That mapping is product-specific and lives in `local-context.md` under `data_sources_catalog` — never in this file. Build it once per product; the skills read it.

Shape (one row per metric that matters, filled with your own sources):

| Metric | Primary source | Cross-validation | Methodology doc |
|--------|----------------|------------------|-----------------|
| `<GMV YoY>` | `<workbook + view>` | `<a second, independently-built source>` | `<attribution/methodology page>` |
| `<Conversion rate>` | `<workbook + view>` | `<funnel dashboard>` | — |
| `<Traffic mix>` | `<acquisition workbook>` | `<web analytics>` | — |
| `<Stage drop-off>` | `<CJM funnel>` | `<same funnel, sub-segments>` | — |

Rules for a usable catalog:
- The cross-validation source must be **independently built** — the same workbook under a different filter is not a second source (it inherits the same methodology error).
- Name the **view**, not just the workbook: "workbook X, YtoY view" and "workbook X, Overview view" can disagree, and Gate Check 3 needs to know which one the number came from.
- A metric with no second source is not blocked — it is ⚠️ Caveat, and the caveat travels with it into the report (Gate Check 3).
- Where a methodology doc exists (attribution rules, metric definitions), link it: it is what resolves a cross-validation disagreement.
