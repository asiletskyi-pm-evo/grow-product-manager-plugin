# Research Frameworks

Detailed templates for structuring product research output. Use these as the foundation for Confluence pages. Since v3.8.0 every cited number, quote and benchmark carries its evidence class (`references/pm-mental-model.md` §4, assigned in Step 1.5.g): the class goes first in the claim's annotation, one `Evidence: <class> — <source>` label may cover a table, column or section whose claims share class and source, and `simulated` / `assumed` are labelled on the item.

---

## Competitive Analysis

### Page structure

```
## TL;DR
[2-3 sentence summary of competitive landscape and key insight]

## Competitors Overview
| Company | Founded | HQ | Funding | Employees | Target Segment |
|---------|---------|-----|---------|-----------|----------------|

## Feature Comparison
| Feature / Capability | Our Product | Competitor A | Competitor B | Competitor C |
|---------------------|-------------|-------------|-------------|-------------|
| [Feature 1]         | ✅ / ❌ / 🟡  | ...         | ...         | ...         |

Legend: ✅ Full support | 🟡 Partial / Beta | ❌ Not available
Evidence: external — competitor websites, snapshot [date] (a hands-on column from Flow Walkthrough: `observed · walkthrough [date]`; label per column when sources differ)

## Pricing Comparison
| Plan / Tier | Our Product | Competitor A | Competitor B |
|------------|-------------|-------------|-------------|
| Free       | ...         | ...         | ...         |
| Pro        | ...         | ...         | ...         |
| Enterprise | ...         | ...         | ...         |

## SWOT Analysis

### Strengths
- [Strength 1]: [evidence/data (class · source)]

### Weaknesses
- [Weakness 1]: [evidence/data (class · source)]

### Opportunities
- [Opportunity 1]: [market signal or trend (class · source)]

### Threats
- [Threat 1]: [competitive move or external risk (class · source)]

## Positioning Map
[Describe 2 axes and where each player sits — e.g., "Price (low→high) vs. Feature depth (basic→advanced)"]

## Key Takeaways
1. [Takeaway with implication for our product]
2. ...
3. ...

## Recommended Actions
- [ ] [Action 1]
- [ ] [Action 2]

## Sources
- [Source title](URL) — `source-type marker` · class — accessed [date]
```

### Tips for competitive analysis
- Compare at least 3 direct competitors and 1-2 indirect/emerging ones
- Check G2, Capterra, TrustRadius for user sentiment
- Look at job postings to infer competitor priorities
- Check ProductHunt, TechCrunch, Crunchbase for recent moves
- Review competitor changelogs/release notes for feature velocity

---

## User Research Synthesis

### Page structure

```
## TL;DR
[2-3 sentence summary of top findings]

## Research Overview
- **Method**: [interviews / surveys / usability tests / support tickets]
- **Sample size**: [N real participants — `simulated` input is never counted]
- **Period**: [date range]
- **Segments**: [user types represented]

## Key Themes
### Theme 1: [Name]
- **Frequency**: mentioned by X/N participants (real users only)
- **Severity**: [High / Medium / Low]
- **Description**: [what users experience]
- **Representative quotes**:
  > "Quote 1" — [Participant ID / segment], [session date] · reported
  > "Quote 2" — [Participant ID / segment], [session date] · reported

### Theme 2: [Name]
...

## Pain Points (ranked)
| # | Pain Point | Frequency | Severity | Impact |
|---|-----------|-----------|----------|--------|
| 1 | ...       | X/N       | High     | [business impact] |

## User Segments
### Segment A: [Name]
- **Profile**: [who they are]
- **Goals**: [what they want to achieve]
- **Pain points**: [top 2-3]
- **Current workarounds**: [how they cope]

## Insights → Recommendations
| Insight | Recommendation | Effort | Impact |
|---------|---------------|--------|--------|
| [Finding] | [What to do] | S/M/L  | High/Med/Low |

## Research Gaps
- [What we still don't know]
- [Suggested follow-up research — including the human step of each hand-back line (Step 1.5.g)]
- [Simulated input — hypotheses only: what and how many (`simulated`) → the study that would check it; this line only when such input exists, never in themes, counts or quotes]

## Sources
- [Research artifacts, links to recordings, raw data — each with its source-type marker and class]
```

### Tips for user research synthesis
- Group by theme, not by participant
- Use exact quotes to bring findings to life — verbatim only; masking `[name]`, a marked `[…]` and a `(translated)` quote with the original kept still count as verbatim, a paraphrase loses its quote marks
- Rank pain points by frequency × severity
- Always separate observations (`observed` / `reported`) from interpretations (hypotheses, or `[assumed — …]` when kept as a claim)
- Note sample limitations honestly

---

## Market Research

### Page structure

```
## TL;DR
[2-3 sentence summary of market opportunity]

## Market Sizing
| Metric | Value | Source (class) | Year |
|--------|-------|----------------|------|
| TAM (Total Addressable Market) | $X | [source] (external) | 20XX |
| SAM (Serviceable Addressable Market) | $X | [source] (external) | 20XX |
| SOM (Serviceable Obtainable Market) | $X | [estimate basis — an estimate: no class of its own; each unsourced input `[assumed — …]`] | 20XX |

### Calculation methodology
[How TAM/SAM/SOM were derived — top-down, bottom-up, or value-theory; each input with its class, an unsourced one `[assumed — …]`]

## Market Trends
### Trend 1: [Name]
- **Direction**: [growing / declining / shifting]
- **Evidence**: [data points, reports — each with its class and source]
- **Implication for us**: [what it means]

## PESTEL Analysis
| Factor | Key Finding | Impact | Timeframe |
|--------|------------|--------|-----------|
| Political | ... | High/Med/Low | Short/Mid/Long |
| Economic | ... | ... | ... |
| Social | ... | ... | ... |
| Technological | ... | ... | ... |
| Environmental | ... | ... | ... |
| Legal | ... | ... | ... |

## Growth Drivers
1. [Driver 1]: [explanation + data]
2. ...

## Risks & Barriers
1. [Risk 1]: [explanation + likelihood]
2. ...

## Opportunities
| Opportunity | Market Size | Competition | Our Fit | Priority |
|------------|------------|------------|---------|----------|
| [Opp 1]   | $X         | Low/Med/High | Strong/Weak | P1/P2/P3 |

## Recommended Strategy
[1-2 paragraphs summarizing recommended market approach]

## Sources
- [Source title](URL) — `source-type marker` · class — accessed [date]
```

### Tips for market research
- Use multiple sources for market sizing — cross-reference analyst reports
- Clearly state assumptions in calculations — each unsourced input labelled `[assumed — …]`
- Distinguish between addressable and obtainable market realistically
- Look at adjacent markets for emerging threats
- Include geographic breakdown if relevant

---

## Combined Research

When the user requests multiple types, create sections for each and add a unified synthesis:

```
## Unified Insights
[Cross-reference findings from competitive, user, and market research]

## Strategic Implications
| Area | Finding | So What? | Now What? |
|------|---------|----------|-----------|

## Priority Recommendations
1. [Highest-impact recommendation backed by multiple research streams]
2. ...
```
