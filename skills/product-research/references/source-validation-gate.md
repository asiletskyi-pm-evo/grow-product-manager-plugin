# Source Validation Gate — Step 1.5 sub-checks (1.5.a–1.5.e)

> Part of `product-research`. Loaded on demand when Step 1.5 validates the sources gathered in Step 2. The gate itself — its purpose, the ✅ Verified / ⚠️ Caveat / ❌ Blocked output and the Blocked-source rule — stays in SKILL.md; the universal gate checks are in `references/data-integrity-protocol.md`.

## 1.5.a — Recency Check (date relevance)

For each external source, determine publication / data collection date. Apply recency thresholds:

| Data type | Recency threshold |
|-----------|-------------------|
| E-commerce CR / AOV benchmarks | ≤ 2 years |
| UX best practices, fundamental research | ≤ 5 years |
| Market trends, sizing | ≤ 1 year |
| Competitor pricing / UX details | ≤ 6 months |
| Technology stacks, platform changes | ≤ 6 months |

- ✅ Recent → use freely
- ⚠️ Aging → use for stable patterns only (UX best practices); cite with year caveat
- ❌ Stale → do not cite; request newer source

**Special case — Baymard guidelines:** check `research_id` and year. Foundational UX patterns (#253, #261, etc.) stay valid for 5+ years; specific metric values need recency check.

## 1.5.b — Geographic/Cultural Context Check

For each external source — determine geography and cultural relevance to the active product's market.

Rank each source against the product's own market (local-context → `product.primary_market`), not against a fixed list:
- ✅ **Direct fit** — players in the same market and category as the product
- ✅ **Regional comparable** — neighbouring markets with similar buying behaviour and payment/delivery norms
- ⚠️ **Global with adaptation** — global giants; cite with an adaptation note (their scale distorts CR/AOV benchmarks)
- ⚠️ **Mature-market reference** — good for **UX patterns**, caveat every CR/AOV number
- ❌ **Heavily local elsewhere** — a market whose norms don't transfer; do not use as-is

*Worked example, `primary_market: UA` e-commerce:* direct fit = the local marketplaces and category leaders; regional comparable = Allegro (PL), eMag (RO); global with adaptation = Amazon, eBay, AliExpress; mature-market reference = ASOS, IKEA; heavily local = US-only retailers. Keep your own per-market list in local-context (`product.competitors`) rather than re-deriving it each run.

**Action when citing non-target geography:** explicit caveat about cultural fit + propose A/B-validation for the target market.

## 1.5.c — Multi-Source Cross-Validation (especially for extreme claims)

For every critical research finding that will appear in the final report:
- ≥ 2 independent sources (Knowledge Library + web, Baymard + Confluence, 2 competitor sources, etc.)
- Variance > 25% between sources → flag for resolution
- Avoid double-citing: 2 articles from the same site = 1 source

**Special case — sensational claims:**
- "X has 25% CR" (extreme for e-commerce)
- "Y grew 10× in N months"
- "Best practice: do Z" (new claim, not from Baymard)
- "#1 in industry" / "only player"

→ Auto-promote to ≥ 3 sources, original primary source check (not secondhand reporting), date + methodology + sample-size verification.

## 1.5.d — Bias Screening

Detect potential bias sources:
- Vendor reports = marketing, not neutral analysis (e.g., Shopify state-of-commerce reports)
- Industry-sponsored research = conflict of interest
- Single competitor PR = biased self-reporting
- Social-media data = selection bias (loud minority)

**Action:** when citing the above — explicit caveat about potential bias in the final report.

## 1.5.e — Source Type Marker + Inline Annotation

Tag every external source by type:
- `baymard-premium` — Baymard Premium UX-Query / guidelines (include guideline #N)
- `web-search` — general web search (include domain, year)
- `kb-source` — Knowledge Library source (include trust score)
- `competitor-website` — direct from competitor's site (include URL snapshot date)
- `user-research` — user research synthesis (include N interviews, date, persona type)
- `deep-research-llm` — ChatGPT/Gemini Deep Research (cross-checked with second source)

Inline-annotation convention:
- `(Baymard Premium, Guideline #N, YYYY research)`
- `(Source domain, YYYY, geography)`
- `(Competitor name, YYYY snapshot, source URL)`
- `(N interviews YYYY-MM, persona-type)`
