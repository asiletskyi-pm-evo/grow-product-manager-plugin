# Verification Checklist

Reference document for CJM Research Step 10 — Independent Verification. Used by the verification subagent to objectively challenge hypotheses generated in earlier pipeline steps.

## Purpose

The verification step exists to ensure objectivity. The main agent generates hypotheses (Steps 5-7); the verification subagent challenges them from an independent perspective. This separation reduces confirmation bias and improves hypothesis quality.

## Subagent Setup

The verification subagent receives:
- Full hypothesis list with all fields (Data Trigger, Feedback Match, Heuristic Match, Solution, Expected Impact, ICE scores)
- Raw anomaly data from product-analysis (unprocessed numbers, not interpretations)
- Internal enrichment data (experiment history, user feedback, previous CJM reports)
- External enrichment data (benchmarks, best practices, knowledge library sources)
- Funnel baseline conversions from CJM configuration

The subagent does NOT receive: the main agent's reasoning about why hypotheses were generated, priority assessments, or subjective commentary. This ensures the verifier works from data, not from the generator's narrative.

## Verification Criteria

For each hypothesis, evaluate all six criteria below. Each criterion results in a pass / fail / inconclusive assessment.

### 1. Anomaly Confirmation

**Question:** Does the anomaly persist after additional segmentation?

**Check:**
- Segment the anomaly by platform (Web, iOS, Android) — is it present across platforms or only one?
- Segment by user type (new vs returning) — does the pattern hold for both segments?
- Segment by traffic source (organic, paid, direct, referral) — is one source driving the anomaly?
- Check for data quality issues: missing data, tracking errors, recent instrumentation changes

**Pass:** Anomaly is consistent across multiple segments, no data quality issues found.
**Fail:** Anomaly disappears after segmentation (e.g., only present in one traffic source with known tracking issues).
**Inconclusive:** Segmented data not available or insufficient for conclusive assessment.

### 2. Evidence Alignment

**Question:** Do internal and external sources support the hypothesis?

**Check:**
- Do knowledge library sources with trust_score ≥ 0.7 support the proposed solution direction?
- Do internal documents (previous research, strategy docs) align with the hypothesis?
- Are there contradicting sources? If yes, which have higher trust scores?
- Does the proposed solution match the evidence, or does it extrapolate beyond what evidence supports?

**Pass:** Multiple sources (trust_score ≥ 0.7) support both the problem identification and solution direction.
**Fail:** High-trust sources directly contradict the hypothesis or proposed solution.
**Inconclusive:** Limited evidence available, or evidence is mixed (some support, some contradict).

### 3. Experiment History

**Question:** Were similar hypotheses tested before? What happened?

**Check:**
- Search internal enrichment for previous A/B tests targeting the same funnel stage and metric
- If found: what was the result? (positive / negative / inconclusive)
- If a similar experiment succeeded: this boosts confidence but raises the question — why is the anomaly still present? (implementation may have been reverted or incomplete)
- If a similar experiment failed: this is a strong signal — the hypothesis needs substantial differentiation from the previous attempt to justify retesting
- If no previous experiments: note this as a gap (neither positive nor negative)

**Pass:** No contradicting experiments, or previous experiments support the direction.
**Fail:** A similar experiment was run and failed, and the current hypothesis does not substantially differ.
**Inconclusive:** Previous experiments had inconclusive results, or the similarity to current hypothesis is partial.

### 4. Benchmark Plausibility

**Question:** Is the expected impact within realistic ranges?

**Check:**
- Compare expected conversion lift with industry benchmarks for similar changes
- Typical ranges (e-commerce context):
  - Copy/microcopy changes: 1-5% lift
  - Form optimization: 5-15% lift
  - Checkout flow redesign: 10-25% lift
  - Navigation/filtering overhaul: 5-20% lift
  - Mobile UX optimization: 5-15% lift
  - Page speed improvement: 1-3% lift per 100ms reduction
- If expected lift exceeds benchmark range by >50%: flag as potentially overestimated
- If expected lift is below benchmark range: verify that the hypothesis is ambitious enough

**Pass:** Expected impact falls within or slightly above industry benchmark ranges.
**Fail:** Expected impact exceeds benchmark ranges by >2× with no justification.
**Inconclusive:** No comparable benchmarks available for the specific type of change proposed.

### 5. Alternative Explanations

**Question:** Could external factors explain the anomaly without the proposed solution?

**Check:**
- Seasonality: is this a seasonal pattern? Compare with same period last year
- Marketing campaigns: were there campaign changes that could affect the funnel stage?
- Technical issues: were there outages, deployments, or performance regressions in the analyzed period?
- External events: market shifts, competitor actions, regulatory changes
- Product changes: were other features shipped that could affect the same funnel stage?

**Pass:** No plausible external explanation found; the anomaly is likely structural.
**Fail:** A clear external factor explains the anomaly (e.g., a campaign ended, causing traffic quality to drop).
**Inconclusive:** Some external factors are present but their contribution is unclear.

### 6. Implementation Risk

**Question:** Are there technical or organizational risks not accounted for in the hypothesis?

**Check:**
- Does the solution require changes to multiple systems/services?
- Are there known technical debt or architectural constraints in the affected area?
- Does the solution conflict with other in-progress work or planned features?
- Are there regulatory or compliance considerations?
- Is the Ease score in ICE realistic given the technical assessment?

**Pass:** Implementation risks are minimal and accounted for in the ICE Ease score.
**Fail:** Significant unaccounted risks that would substantially reduce feasibility.
**Inconclusive:** Technical assessment insufficient to evaluate implementation risks.

## Verification Status Assignment

Based on the six criteria assessments, assign one of three statuses:

### Confirmed
- **Criteria:** ≥4 criteria pass, 0 criteria fail
- **Meaning:** Strong evidence support, anomaly verified, no contradicting data. Ready for implementation planning.
- **Action:** Maintain or increase ICE Confidence score

### Needs-More-Data
- **Criteria:** ≥2 criteria inconclusive, OR exactly 1 criterion fails with reasonable mitigation
- **Meaning:** Partial evidence, some gaps remain. Recommend additional investigation before committing development resources.
- **Action:** Reduce ICE Confidence score by 1-2 points. Note specific data gaps to fill.

### Contradicted
- **Criteria:** ≥2 criteria fail, OR Experiment History fails with no substantial differentiation
- **Meaning:** Evidence contradicts the hypothesis or previous attempts failed. Not recommended for implementation without major revision.
- **Action:** Reduce ICE Confidence score by 3-4 points. Recommend revision or removal.

## Output Format

The subagent returns a structured verification report:

```
Hypothesis: [name]
Status: [confirmed / needs-more-data / contradicted]

Criteria Results:
  1. Anomaly Confirmation: [pass/fail/inconclusive] — [1-sentence justification]
  2. Evidence Alignment: [pass/fail/inconclusive] — [1-sentence justification]
  3. Experiment History: [pass/fail/inconclusive] — [1-sentence justification]
  4. Benchmark Plausibility: [pass/fail/inconclusive] — [1-sentence justification]
  5. Alternative Explanations: [pass/fail/inconclusive] — [1-sentence justification]
  6. Implementation Risk: [pass/fail/inconclusive] — [1-sentence justification]

Confidence Adjustment: [+N / -N / unchanged]
Updated Confidence: [new score]

Recommendations: [specific action items if status is needs-more-data or contradicted]
```

## Handling Edge Cases

- **Insufficient data for verification:** If the subagent cannot evaluate 3+ criteria due to missing data, assign "needs-more-data" and list specific data requirements.
- **Borderline cases:** If the assessment is genuinely 50/50 between confirmed and needs-more-data, choose "needs-more-data" — it's safer to investigate further than to proceed with false confidence.
- **High-impact contradicted hypotheses:** If a contradicted hypothesis has very high potential impact (ICE Impact ≥ 8), recommend a revised approach rather than outright removal. The underlying problem may still be valid even if the specific solution is wrong.
