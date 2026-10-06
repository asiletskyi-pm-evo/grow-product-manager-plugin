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

### PM-first pass (interview synthesis, since v3.9.0)

`references/judgment-points.md` §9 at this skill's step (SKILL.md, end of Step 2): `user-research`, `insight-report` or `insight-memo` on real interview or session material, an interactive run, and `judgment.learning_mode` `pm_first` or `explain`. Not for competitive, market, UX-benchmark, research-plan or discussion-guide work, and never in a return payload or a scheduled run.

- **Excerpts (`pm_first`).** 10 verbatim passages, at most 2 per participant id, drawn round-robin across participants in session order after 1.5.g: only real users' `reported` / `observed` items — never `simulated` input, a stakeholder's `reported (<who>)` view, a Deep Research claim or an AI summary. Personal data masked (`[name]`, a marked `[…]`), as the quotes tip above allows; each passage shown with its participant id. With fewer eligible passages, show those there are; with none, ask nothing.
- **The question.** One free-text message in `user.language`: tag each excerpt with your own theme words. Partial tags count; a skip word skips; «вимкни» / "turn off" writes `- **Learning mode:** off` (§9). The first such question in a session adds one line on how to skip or switch it off. Not asked when the caller passed `pm_first` (`done`, `skipped` or `off` — e.g. from meeting-processor on the same transcript), nor when the PM already stated their themes for this material in the request or at Step 1: those count as their tags (an interpretation already given counts as the answer, `references/judgment-points.md` §9), and the comparison runs at theme level.
- **A tag is an interpretation, never a finding.** Step 3 synthesises from the material alone. A PM tag is never a theme, a count, a quote source or a finding; it never moves a theme, frequency, severity or rank, never enters the page, and never sets `human-validated: yes` (`references/source-validation-gate.md` 1.5.f).
- **Your tags vs mine.** After Step 3, in chat before Step 4 publishes (before its location question when it asks one): per excerpt, the PM's tag next to the theme Step 3 put it in (or "no theme"); which PM tag was matched to which theme — the matching is this skill's, shown so the PM can check it; agreements; and for each difference the evidence that separates them (the other participants' passages on that theme, n of real users), or "no evidence decides this — your call". Changes go through the Step 5 re-publish loop, and its self-improvement check treats them as `references/self-improvement.md` says, its judgment-guard rule included.
- **`explain`.** Instead of the question and the comparison, one chat block "How I got here" at the same point: the inputs used (sources with their class, n real participants), the grouping rule applied (themes across participants, ranked by frequency × severity) and the two closest alternatives rejected (a theme merged or split differently). It asks nothing and never enters the page.

### Prototype sessions — build-first inbound (since v3.9.0)

The path `references/judgment-points.md` §8 names for an assumption a prototype can settle: write-concept's build-first line (its Step 1) leads to a lo-fi prototype in design-bridge, and design-bridge Step 9 suggests showing it to 3–5 real users here. The prototype stays `reported` (file, frame); only real users' sessions on it are evidence (`references/data-integrity-protocol.md` Gate Check 6a).

- **Payload in.** The prototype link (file, frames), the assumption it tests, the concept brief (product, new or existing functionality, target user or segment), and the upstream — design-bridge, plus write-concept when the path started there.
- **Not asked at Step 1.** Product, new or existing functionality, research type (user research by usability test), subject (the prototype and the assumption), depth (quick), goal (the decision the assumption informs) and audience (team) come from the payload. The Deep Research questions are not asked — a test of the team's own prototype has no external material — and the Figma designs check uses the passed prototype. Still asked, inside the existing Step 1 confirmation: who the 3–5 participants are (segment, recruiting) when the brief does not say, and where any existing session notes are. The Knowledge Library check runs as usual.
- **Before the sessions.** Render the `research-plan` subtype — method usability-test, n = 3–5 real users, research question = the assumption, the prototype frames as stimulus — and a `discussion-guide` only when the PM asks for one. The skill never runs or simulates the sessions: a persona walk of the prototype is `simulated` and never counts toward n (1.5.g).
- **After the sessions.** The PM's notes or transcripts are synthesised as `user-research`, with the PM-first pass above when it is on. Each finding about the assumption carries its class — what participants did in the session `observed`, what they said `reported` — and n counts real participants only.
- **Return.** Step 6 offers first the return to the concept: the findings that bear on the assumption, with their labels and the page link, go back to write-concept, which resumes from the brief it printed and takes them as Step 2 evidence. The findings say what the sessions showed about the assumption, with n; whether to go ahead stays the PM's call in the concept.

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
