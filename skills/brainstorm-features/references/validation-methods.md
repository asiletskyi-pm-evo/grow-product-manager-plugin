# Validation Methods

Methods for validating hypotheses, ranked by cost (from cheapest to most expensive). Recommend the **safest and cheapest** method that provides sufficient confidence.

---

## 1. Desk Research / Data Analysis

**Cost**: Minimal
**Time**: Hours to 1-2 days
**Confidence gain**: Low-Medium

- Analyze existing product data, funnels, user behavior
- Research benchmarks, competitor implementations
- Review existing user feedback (support tickets, reviews, NPS)

**When to use**: When existing data can answer the question. Always start here before more expensive methods.

**Limitations**: Cannot validate new concepts that have no existing data.

---

## 2. User Interviews (5-10 interviews)

**Cost**: Low
**Time**: 1-2 weeks
**Confidence gain**: Medium

- Talk to 5-10 users from the target segment
- Show mockups, describe the concept, gather reactions
- Understand pain points, willingness to use, concerns

**When to use**: When you need to understand user needs, validate problem existence, or get qualitative feedback on a solution direction.

**Limitations**: What users say ≠ what users do. Small sample, potential bias.

---

## 3. Prototype / Fake Door Test

**Cost**: Low-Medium
**Time**: 1-3 weeks
**Confidence gain**: Medium-High

- **Prototype**: Clickable mockup (Figma prototype) tested with users
- **Fake door**: Real button/link in the product that measures interest but doesn't deliver the feature yet (shows "coming soon" or waitlist)

**When to use**: When you want to measure actual user interest without building the full feature. Good for validating demand.

**Limitations**: Fake door only measures initial interest, not sustained usage.

---

## 4. Feature Flag (Limited Rollout)

**Cost**: Medium
**Time**: 2-4 weeks build + 1-2 weeks measurement
**Confidence gain**: High

- Build a minimal version of the feature
- Release to a small % of users (5-10%) under a feature flag
- Monitor metrics: adoption, engagement, impact on target metric

**When to use**: When the feature is relatively simple to build and you want real usage data before full rollout.

**Limitations**: Requires development effort. Small sample may not be statistically significant.

---

## 5. A/B Test (Full Validation)

**Cost**: High
**Time**: 2-4 weeks build + 2-4 weeks measurement
**Confidence gain**: Very High

- Build the feature fully
- Split traffic: control group (no feature) vs. test group (with feature)
- Measure with statistical significance (p < 0.05)

**When to use**: When the feature has significant business impact and you need conclusive evidence. When the risk of a wrong decision is high.

**Limitations**: Most expensive method. Requires sufficient traffic for statistical significance.

---

## Decision Guide

```
Is there existing data that can answer the question?
├─ YES → Desk Research (Method 1)
└─ NO ↓

Is the main risk "users don't want this"?
├─ YES → User Interviews (Method 2) or Fake Door (Method 3)
└─ NO ↓

Is it cheap to build a minimal version?
├─ YES → Feature Flag rollout (Method 4)
└─ NO ↓

Is the potential impact high and risk of wrong decision significant?
├─ YES → A/B Test (Method 5)
└─ NO → Start with cheapest viable option and iterate
```

---

## Combining Methods

For high-stakes hypotheses, combine methods in sequence:

1. **Desk Research** → confirms the problem exists and is worth solving
2. **User Interviews** → validates the solution direction
3. **Prototype / Fake Door** → measures demand
4. **Feature Flag** → validates with real usage
5. **A/B Test** → full statistical proof before scaling

Not every hypothesis needs all 5 steps. Match the validation cost to the risk level.
