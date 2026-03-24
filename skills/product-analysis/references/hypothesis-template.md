# Hypothesis Template for Data-Driven Hypotheses

Guidelines for generating and scoring hypotheses from Product Analysis findings.

---

## Hypothesis Card Format

Every hypothesis generated from data analysis must follow this structure:

```
Назва: [Short descriptive name]

Знахідка: [The specific data point, trend, or anomaly that triggered this hypothesis]
Проблема: [What problem this hypothesis addresses — grounded in data]
Рішення: [Proposed action, experiment, or feature change]
Очікуваний результат: [Expected outcome — with numbers where data supports it]
Цільова метрика: [Primary metric, expected change direction and estimated magnitude]
Метод валідації: [How to validate — A/B test, deeper analysis, user research, etc.]

ICE Score: Impact [X] × Confidence [X] × Ease [X] = [Score]

Дані на підтримку: [Specific values, calculations, chart observations from the analysis]
Ризики: [What could go wrong, potential negative side effects]
```

---

## ICE Scoring — Adapted for Data-Driven Hypotheses

### Impact (1–10)

How much will this move the target metric if the hypothesis is correct?

| Score | Criteria |
|-------|----------|
| 9–10 | Expected to move a primary business metric (revenue, conversion) by >10% |
| 7–8 | Expected to move a primary metric by 5–10%, or a secondary metric significantly |
| 5–6 | Expected to move a primary metric by 2–5%, or a secondary metric moderately |
| 3–4 | Expected to move a secondary metric by 1–5% |
| 1–2 | Minor improvement, quality-of-life change, or unclear metric impact |

**Data-driven adjustment:** If the analysis provides concrete numbers (e.g., "conversion at step X is 15% below benchmark"), use these to estimate impact more precisely.

### Confidence (1–10)

How confident are we that the hypothesis is correct, based on the available data?

| Score | Criteria |
|-------|----------|
| 9–10 | Strong data support: clear trend, large sample, multiple confirming data points |
| 7–8 | Good data support: visible pattern, adequate sample, consistent across segments |
| 5–6 | Moderate support: pattern exists but sample is small, or data has quality issues |
| 3–4 | Weak support: based on correlation, analogy, or limited data points |
| 1–2 | Mostly intuition or extrapolation, very limited data backing |

**Data-driven adjustment:**
- +1 if the finding is confirmed by multiple independent data sources
- +1 if there's a benchmark confirming the opportunity (industry data shows higher is achievable)
- -1 if data quality issues were noted (missing data, small sample, potential bias)
- -1 if the finding could be explained by a confounding variable

### Ease (1–10)

How easy is it to implement the proposed solution and validate the hypothesis?

| Score | Criteria |
|-------|----------|
| 9–10 | Configuration change, copy change, or existing feature toggle |
| 7–8 | Small frontend change, minor backend adjustment, <1 sprint |
| 5–6 | Medium feature, 1–2 sprints, single team |
| 3–4 | Large feature, 2–4 sprints, or requires multiple teams |
| 1–2 | Major initiative, >1 month, significant infrastructure or cross-team coordination |

---

## Hypothesis Categories

Group generated hypotheses by data confidence:

### Data-Confirmed (Confidence 7+)
Strong data support. The analysis clearly shows the pattern, and the proposed action has a logical connection to the finding. These are the highest-priority hypotheses.

### Data-Suggested (Confidence 4–6)
The data hints at an opportunity or problem, but the signal is not strong enough for high confidence. May need additional analysis or a small experiment to validate before committing resources.

### Exploratory (Confidence 1–3)
Based on weak signals, correlations, or analogies with other products/markets. Worth discussing and potentially investigating further, but not ready for direct implementation.

---

## ICE Summary Table Format

Present all hypotheses in a summary table sorted by total ICE score:

| # | Назва | Знахідка | Цільова метрика | I | C | E | ICE | Категорія |
|---|-------|----------|-----------------|---|---|---|-----|-----------|
| 1 | ... | ... | ... | X | X | X | XXX | Data-Confirmed |
| 2 | ... | ... | ... | X | X | X | XXX | Data-Suggested |
| ... | | | | | | | | |

---

## Connecting Hypotheses to Analysis Findings

Every hypothesis MUST trace back to a specific finding from the analysis. This creates an evidence chain:

```
Data source → Finding → Hypothesis → Proposed action → Expected impact
```

When presenting hypotheses, always include the "Знахідка" field that links back to the specific section of the analysis (e.g., "See Anomaly #2 in the Anomalies section" or "Based on Funnel Analysis: 45% drop-off at checkout step").

This traceability ensures:
1. Hypotheses are grounded in real data, not assumptions
2. The user can verify the reasoning
3. When the hypothesis is passed to another skill (Brainstorm, Requirements Creator), the data context travels with it
