# ICE Scoring Framework

## Overview

ICE = **Impact** × **Confidence** × **Ease**

Each factor is scored 1-10. The final ICE Score ranges from 1 to 1000.

---

## Impact (1-10)

How much will this idea move the target metric?

| Score | Meaning | Example |
|-------|---------|---------|
| 1-2 | Negligible | Minor text change, no measurable effect |
| 3-4 | Low | Small UX tweak, <2% metric improvement |
| 5-6 | Medium | Noticeable improvement, 2-5% metric change |
| 7-8 | High | Significant feature, 5-15% metric improvement |
| 9-10 | Transformative | Core flow redesign, >15% metric improvement |

**How to assess:**
- What metric does this directly affect?
- What is the realistic range of improvement?
- Are there benchmarks from competitors or industry?
- How many users will be affected? (reach)

---

## Confidence (1-10)

How confident are we that this will work?

| Score | Meaning | Evidence basis |
|-------|---------|---------------|
| 1-2 | Gut feeling | No data, pure intuition |
| 3-4 | Weak signal | Anecdotal feedback, 1-2 support tickets |
| 5-6 | Some evidence | User interviews (5-10), competitor has it |
| 7-8 | Strong evidence | Research data, A/B test from similar product, multiple benchmarks |
| 9-10 | Near certain | Own A/B test data, proven in same product, strong quantitative evidence |

**How to assess:**
- Do we have data supporting this hypothesis?
- Have competitors validated this approach?
- Are there industry benchmarks?
- How similar is our context to the evidence source?

---

## Ease (1-10)

How easy is this to implement?

| Score | Meaning | Typical effort |
|-------|---------|---------------|
| 1-2 | Very hard | 3+ months, multiple teams, new infrastructure |
| 3-4 | Hard | 1-3 months, cross-team dependencies |
| 5-6 | Medium | 2-4 weeks, single team, some complexity |
| 7-8 | Easy | 1-2 weeks, single team, straightforward |
| 9-10 | Trivial | Days, config change, copy update, feature flag |

**How to assess:**
- How many teams are involved?
- Are there technical dependencies or blockers?
- Does it require new infrastructure?
- Can it be done incrementally (feature flag, A/B test)?

---

## ICE Summary Table Template

Use this format when presenting scored ideas:

```
| # | Idea | Impact | Confidence | Ease | ICE Score | Category | Validation |
|---|------|--------|-----------|------|-----------|----------|------------|
| 1 | [Name] | 8 | 7 | 9 | 504 | Quick Win | A/B test |
| 2 | [Name] | 9 | 5 | 4 | 180 | Growth | User interviews |
| 3 | [Name] | 6 | 8 | 8 | 384 | UX | Feature flag |
```

Sort by ICE Score descending. This gives the user a clear priority ranking.

---

## Common Pitfalls

- **Overscoring Impact** — be realistic, most ideas won't move metrics by >10%
- **Underscoring Confidence** — if there are benchmarks, it's at least 5-6
- **Ignoring hidden effort** — design, QA, data migration, documentation all count toward Ease
- **Not re-scoring** — after discussion, ICE scores may change. Always offer to re-score after new information surfaces
