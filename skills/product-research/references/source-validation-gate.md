# Source Validation Gate — Step 1.5 sub-checks (1.5.a–1.5.g)

> Part of `product-research`. Loaded on demand when Step 1.5 validates the sources gathered in Step 2. The gate itself — its purpose, the ✅ Verified / ⚠️ Caveat / ❌ Blocked output and the Blocked-source rule — stays in SKILL.md; the universal gate checks are in `references/data-integrity-protocol.md`. 1.5.a–1.5.e set the status, 1.5.f adds role caveats, and 1.5.g (since v3.8.0) adds the evidence class and the frontier hand-back — neither of the last two ever changes the status.

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
- `user-research` — user research synthesis (include N real users, date, segment)
- `deep-research-llm` — ChatGPT/Gemini Deep Research (cross-checked with second source)

Inline-annotation convention — since v3.8.0 the class from 1.5.g goes first inside the annotation (`references/pm-mental-model.md` §4):
- `(external · Baymard Premium, Guideline #N, YYYY research)`
- `(external · Source domain, YYYY, geography)`
- `(external · Competitor name, YYYY snapshot, source URL)`
- `(reported · N interviews YYYY-MM, segment)`; a quote: `«…» — P3, interview YYYY-MM-DD · reported`

## 1.5.f — Role gate emphasis (since v3.6.0)

`role_defaults.gate_emphasis` (Step 0i of `references/local-context-protocol.md`; a hat overlays it) can name extra checks that run **on top of** 1.5.a–1.5.e and 1.5.g — the mapping is `references/data-integrity-protocol.md` → Gate emphasis. This skill applies the four tokens below; any other token is ignored in this run, and with none of them present the gate runs exactly as 1.5.a–1.5.e and 1.5.g describe.

Every extra check only adds: a ⚠️ caveat line next to the source, finding or theme it concerns, or a flag on a theme. It never asks a question, never changes the ✅ / ⚠️ / ❌ status that 1.5.a–1.5.e gave a source or the class 1.5.g gives it, never drops a source and never blocks the run.

| Token | Extra check in this skill | Added when the check fails |
|-------|---------------------------|----------------------------|
| `market-recency` | Every external **market** datum — market sizing, trends, CR / AOV and other market benchmarks, pricing, competitor metrics — dated more than 12 months before the run, even when it is inside its 1.5.a threshold. UX guidelines and fundamental research are not market data. | `⚠️ Stale market data: (source, YYYY-MM) — older than 12 months` |
| `triangulation` | A qualitative finding (interviews, usability sessions, reviews, open survey answers) is called conclusive only when two independent **source types** agree — e.g. interviews and support tickets, usability sessions and analytics. Each qualitative finding states the number of real users and the method. Keeping `simulated` input out of findings is baseline 1.5.g since v3.8.0 — the token adds no second ⚠️ line for it. | `⚠️ One source type — indicative, not conclusive (n = N real users, method)` |
| `human-validated` | Every theme a model synthesised (Step 3 user-research themes, a design research-synthesis appendix) carries `human-validated: yes` or `human-validated: no`. `yes` only when a person has confirmed the theme — the source says a researcher coded or reviewed it, or the user confirmed it in this session; `no` otherwise. The flag is derived, never asked for. | `human-validated: no` on the theme |
| `source-type` | Already met by this skill: 1.5.e marks every external source, and the Sources section (Step 4) marks the type of every source, internal and context ones included. The token adds nothing here — it is the `pm` baseline. | — |

The caveat lines follow the caveat-propagation rule of the Quality standards: they stay visible in the section that cites the source or finding, never folded into a generic "based on research".

## 1.5.g — Evidence class and frontier (since v3.8.0)

`references/data-integrity-protocol.md` Gate Check 6 (6a–6d) applied by this skill; the classes and the label grammar are `references/pm-mental-model.md` §4. It runs after 1.5.a–1.5.e have set the status, on every cited source, finding and quote — external, internal and uploaded alike — and adds labels and hand-back lines only: never a question, never a changed status, never a dropped source, never a blocked run.

How this skill's inputs map onto 6a (the full table is there):

| Input | Class |
|-------|-------|
| Interview or usability transcript, open survey answer, review — verbatim, with participant id | `reported` |
| Session recording, usability observation, a Flow Walkthrough step or `compare.yaml` cell | `observed` |
| A number returned by Product Analysis | the class it carries (`measured`) — kept, never upgraded |
| A figure the user typed or pasted (`user-text`) | `reported (<who>)` — even after 1.5.a–1.5.e |
| A stakeholder's or the PM's own view | `reported (<who>)` — not a real-user source |
| `deep-research-llm` | the class of the resolvable, recency-checked source a claim traces to; untraceable → `simulated` (two LLMs agreeing are not a second source) |
| Persona or synthetic-user answers, simulated interviews, model-written "user" answers | `simulated` |

- **Synthesis keeps the class** of what it synthesises: a theme drawn from six interviews is `reported`; a design research-synthesis appendix keeps the class of the notes it was given.
- **P7 (6b).** `simulated` input never reaches the TL;DR, Key Themes, Pain Points, Insights or key findings, is never counted in n or "X/N participants", never quoted and never a cross-validation source (1.5.c) or a debate E#. It goes to Hypotheses or the one `Simulated input — hypotheses only` line, shown only when such input exists; that line's content (what, how many) is the user-research template's `simulated_input` variable — derived here, never asked, unset when there is none.
- **Upload origin (6a).** Never asked: an upload is `simulated` only on an explicit marker; a persona document otherwise is `reported (document)` and its unsourced claims `[assumed — …]`. An interactive run prints one notice line only when it classifies an upload as `simulated`.
- **Frontier (6c).** A finding about why users act or what they need with no real-user source, a causal claim on observational data, or a claim that needs tacit organisational context keeps its supportable part, keeps the guess only as an `[assumed — …]` hypothesis and gets one hand-back line next to it in `user.language` naming the human step (interview N users of the segment, a holdout, ask the owning team); Research Limitations / Next Steps list the same step. Once per claim; never on a labelled hypothesis.
- **Run kinds (6d).** Interactive: labels plus hand-back lines. Invoked for a return payload (e.g. UX benchmark research for cjm-research enrichment): classes and frontier flags in the payload's data-quality notes. Scheduled or headless: labels and the 6b handling of synthetic input, never a hand-back line — a frontier claim reads `[assumed — frontier: <human step>]`.
