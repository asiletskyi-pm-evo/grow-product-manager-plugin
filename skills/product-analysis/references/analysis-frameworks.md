# Analysis Frameworks

Detailed descriptions and application guidelines for each analysis framework available in the Product Analysis skill.

---

## Trend Analysis

**When to use:** Always — this is the baseline framework for any data analysis.

**What to look for:**
- **Direction**: Is the metric going up, down, or sideways?
- **Magnitude**: How much has it changed? (absolute values and %)
- **Acceleration**: Is the rate of change increasing, stable, or decreasing?
- **Inflection points**: Where did the trend change direction? What happened at that time?
- **Seasonality**: Are there recurring patterns (weekly, monthly, quarterly)?

**How to present:**
- State the trend in one sentence: "[Metric] has [increased/decreased] by [X%] from [period A] to [period B]"
- Compare with target/OKR: "This is [above/below] the quarterly target of [Y]"
- Note acceleration: "The rate of [growth/decline] is [accelerating/stable/decelerating]"

**Python helpers:**
```python
# Period-over-period change
df['pct_change'] = df['metric'].pct_change()

# Rolling average to smooth noise
df['rolling_7d'] = df['metric'].rolling(7).mean()

# Trend direction via linear regression slope
from numpy.polynomial import polynomial as P
slope = np.polyfit(range(len(df)), df['metric'], 1)[0]
```

---

## Anomaly Detection

**When to use:** Always — run alongside trend analysis to surface unexpected changes.

**What to look for:**
- **Spikes**: Sudden large increases (>2 standard deviations from rolling mean)
- **Drops**: Sudden large decreases
- **Pattern breaks**: Change in the usual weekly/monthly pattern
- **Missing data**: Gaps that might indicate logging issues
- **Flatlines**: Suspiciously constant values (potential data pipeline issues)

**Classification by severity:**

| Severity | Criteria | Action |
|----------|----------|--------|
| Critical | >3σ deviation OR key metric drop >20% | Immediate investigation, escalate |
| Significant | 2-3σ deviation OR notable metric change 10-20% | Investigate within this analysis |
| Minor | 1-2σ deviation OR small change <10% | Note and monitor |

**Root cause investigation checklist:**
1. Was there a product release at this time?
2. Was there a marketing campaign or promotion?
3. Is there a known bug or outage?
4. Is there a seasonal or calendar effect (holiday, end of month)?
5. Was there an external event (competitor action, market shift)?
6. Is the data pipeline healthy? (check for logging changes)

**Python helpers:**
```python
# Z-score based anomaly detection
rolling_mean = df['metric'].rolling(14).mean()
rolling_std = df['metric'].rolling(14).std()
df['z_score'] = (df['metric'] - rolling_mean) / rolling_std
df['is_anomaly'] = df['z_score'].abs() > 2
```

---

## Cohort Analysis

**When to use:** When understanding user behavior over time matters — retention, LTV, feature adoption.

**Types:**
- **Acquisition cohorts**: Users grouped by signup/first purchase date
- **Behavioral cohorts**: Users grouped by first action (e.g., first search, first add-to-cart)
- **Feature cohorts**: Users who did/didn't use a specific feature

**What to look for:**
- **Retention curves**: How quickly do users drop off? Where is the steepest drop?
- **Cohort quality trends**: Are newer cohorts retaining better or worse than older ones?
- **Behavioral differences**: Do users who perform action X retain better than those who don't?
- **Monetization by cohort**: How does revenue/LTV differ across cohorts?

**How to present:**
- Cohort retention table (rows = cohorts, columns = periods since acquisition)
- Highlight: best and worst cohorts, typical retention curve shape
- Note: any cohorts that break the pattern and possible explanations

---

## Funnel Analysis

**When to use:** When analyzing conversion flows — purchase funnel, onboarding, feature adoption.

**What to look for:**
- **Step-by-step conversion rates**: What % of users progress from step N to step N+1?
- **Bottlenecks**: Which step has the largest drop-off?
- **Absolute numbers**: Not just rates — absolute user counts matter for business impact
- **Segment differences**: Do conversion rates differ by platform, country, user type?
- **Time to convert**: How long does it take users to move through the funnel?

**How to present:**
- Funnel table: Step | Users | Conversion from previous step | Conversion from top
- Highlight the biggest drop-off point
- Calculate: "If we improve step X conversion by Y%, that's Z additional [conversions/purchases/signups]"

**Python helpers:**
```python
# Funnel conversion calculation
funnel_data = [('Visit', 100000), ('Search', 65000), ('Product page', 40000), ('Add to cart', 12000), ('Purchase', 5000)]
for i in range(1, len(funnel_data)):
    step, users = funnel_data[i]
    prev_users = funnel_data[i-1][1]
    print(f"{step}: {users:,} ({users/prev_users*100:.1f}% from prev, {users/funnel_data[0][1]*100:.1f}% from top)")
```

---

## Segment Comparison

**When to use:** When different user groups may behave differently — platform comparison, country breakdown, user type analysis.

**Common segmentation dimensions:**
- Platform (iOS, Android, Web, Desktop)
- Country / locale
- User type (new vs returning, free vs paid, buyer vs seller)
- Traffic source (organic, paid, referral, direct)
- Device type
- User activity level

**What to look for:**
- **Performance gaps**: Which segment performs best/worst?
- **Trend divergence**: Are segments trending in different directions?
- **Size vs performance trade-off**: A small high-performing segment may be less impactful than improving a large mediocre segment
- **Anomaly isolation**: Is an overall metric change driven by one segment?

**How to present:**
- Comparison table: Segment | Metric A | Metric B | Trend
- Highlight: biggest gaps, fastest growing/declining segments
- Impact calculation: "Segment X represents Y% of total users but drives Z% of the metric change"

---

## Metric Decomposition

**When to use:** When a high-level metric needs unpacking to understand what's driving it.

**Decomposition approaches:**
- **Multiplicative**: Revenue = Users × Conversion × AOV
- **Additive**: Total revenue = Revenue_segment_A + Revenue_segment_B + ...
- **Funnel**: Overall conversion = Step1_rate × Step2_rate × Step3_rate × ...

**What to look for:**
- Which sub-metric is driving the overall change?
- Are sub-metrics moving in the same or opposite directions?
- Which sub-metric has the most leverage for improvement?

**How to present:**
- Decomposition tree: show how the top-level metric breaks down
- For each component: current value, change vs previous period, contribution to overall change
- Highlight: the component with the largest absolute contribution to the change

---

## Correlation Analysis

**When to use:** When looking for relationships between metrics — does metric A move when metric B moves?

**Important caveats (always state):**
- Correlation ≠ causation — always note this
- Spurious correlations are common — use domain knowledge to filter
- Time-lagged correlations may be more meaningful than same-period

**What to look for:**
- **Strong correlations** (|r| > 0.7): Likely a real relationship worth investigating
- **Moderate correlations** (0.4 < |r| < 0.7): Possible relationship, investigate further
- **Weak correlations** (|r| < 0.4): Likely noise unless domain knowledge suggests otherwise
- **Negative correlations**: When one metric goes up, the other goes down — can indicate trade-offs

**Python helpers:**
```python
# Correlation matrix
corr_matrix = df[['metric_a', 'metric_b', 'metric_c']].corr()

# Time-lagged correlation
from scipy.stats import pearsonr
for lag in range(1, 8):
    r, p = pearsonr(df['metric_a'].iloc[lag:], df['metric_b'].iloc[:-lag])
    print(f"Lag {lag} days: r={r:.3f}, p={p:.4f}")
```

---

## Benchmarking

**When to use:** When external context is needed — how do our metrics compare to industry standards?

**Sources for benchmarks:**
- Industry reports (search via WebSearch)
- Competitor public data (earnings reports, press releases)
- Platform benchmarks (Google, Apple marketplace averages)
- SaaS/e-commerce benchmark databases

**How to present:**
- Our metric | Industry median | Industry top quartile | Our position
- Note: benchmark data freshness and source reliability
- Context: are we comparing apples to apples? (market size, maturity, model differences)

**Important guidelines:**
- Always cite benchmark sources with links
- Note the date of benchmark data
- Acknowledge differences between our product and benchmark cohort
- Use benchmarks as directional guidance, not absolute targets
