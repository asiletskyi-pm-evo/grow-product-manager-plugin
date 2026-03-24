# Implementation Approach Recommendation Logic

Use this guide to provide a reasoned recommendation for the implementation approach when creating feature requirements.

## Decision Matrix

| Signal | Recommended approach | Reasoning |
|--------|---------------------|-----------|
| Feature impacts key business metrics (conversion, revenue, retention) | **A/B Test** | Need to measure actual impact before full rollout. Rollback is instant |
| Multiple alternative solutions exist and we need data to choose | **A/B/C Test** | Compare alternatives on real traffic to pick the winner |
| Moderate risk, changes to existing functionality, new UX flows | **Feature flag** | Safe rollout with ability to disable instantly if issues arise |
| Low risk, infrastructure change, backend optimization | **Feature flag** | Minimal user impact but still want a safety net |
| Bug fix, critical fix, zero-risk change | **Without feature flag** | Speed of deployment is more important than safety net |
| Cosmetic change with no metric impact | **Without feature flag** | Overhead of feature flag setup outweighs the risk |

## Detailed Recommendation Logic

### When to recommend A/B Test

- The feature directly targets a key product metric (conversion rate, average order value, retention, engagement)
- The hypothesis is not yet validated by data
- There is uncertainty about user reaction
- The change affects a high-traffic user flow (e.g., checkout, product page, search)
- Stakeholders need data to make a go/no-go decision
- The feature has potential negative side effects on other metrics

### When to recommend A/B/C Test

- Two or more alternative UX/functionality approaches exist
- The team cannot decide between options without user data
- Each option has distinct trade-offs that need real-world validation
- The product area has enough traffic to support 3+ test groups

### When to recommend Feature Flag

- The feature changes existing functionality and has moderate risk
- The change is significant but metric impact is predictable
- The team wants to ship incrementally (dark launch → beta → GA)
- The feature needs to be controllable per locale/platform
- The change involves backend + frontend coordination and may need phased rollout

### When to recommend Without Feature Flag

- ⚠️ **Always warn the user about risks:**
  > "Реалізація без фіча прапора несе ризики: якщо функціонал зламає систему, відкат потребуватиме нового релізу. Рекомендуємо feature flag для безпечнішого розгортання."

- Bug fixes that restore expected behavior
- Infrastructure/performance improvements invisible to users
- Copy changes, minor cosmetic fixes
- Changes that are trivially reversible
- Mandatory compliance/legal changes that must ship as-is

## Recommendation Format

When presenting the recommendation to the user:

```
Рекомендований підхід: [approach name]

Обґрунтування:
- [reason 1 based on the feature context]
- [reason 2]

Альтернатива: [alternative approach] — [why it could also work or why it's less suitable]
```

Always let the user make the final decision. The recommendation is advisory.
