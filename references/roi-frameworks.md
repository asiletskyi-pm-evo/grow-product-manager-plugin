# ROI Frameworks — ROAIP / PRO economics

Methodology reference for pricing improvements and decisions in money. Consumed by `brainstorm-features` (PRO scoring alongside ICE), `delegation-coach` (hiring/delegation ROI), `decision-log` and `experiment-tracker` (cost-of-decision / cost-of-test). ROAIP and RICE-Confidence are the plugin's working terms.

---

## ROAIP — ROI-Oriented Approach to the Improvement Process

The idea: **quantify every improvement in money** so ideas can be prioritized, feasibility judged, and a PM's own impact measured without waiting for a manager's feedback. An *improvement* (incremental: faster/cheaper/more convenient) and an *innovation* (rule-changing) are both "improvements" here and are costed the same way.

**Base formula:** `ROI = (gain − cost) / cost × 100%`.
Report **both** ROI (relative — compares efficiency across ideas) and the **absolute** profit (a different comparison scale). Neither alone is enough.

### Calculation model (the fields, and how they compute)

| # | Input | Note |
|---|-------|------|
| 1 | Hours saved per month, per specialist | The core lever for efficiency improvements. |
| 2 | Specialist's fully-loaded monthly salary | Incl. taxes / overtime. |
| 3 | Hourly rate = monthly salary / **productive hours** | Default productive hours ≈ **126/mo** (≈6 productive h/day × 21 days); substitute your own. |
| 4 | Number of specialists at this position/rate | Scales the saving. |
| 5 | *(auto)* Saving per month and per year | = (1) × (3) × (4) × 12. |
| 6 | Amortization period (years) | Minimum years the improvement will keep paying off. |
| 7 | Cost to implement | One-off build/integration cost. |
| 8 | *(auto)* Net Profit (year 1 and over amortization), ROI (year 1 and over amortization), **annual % return** | The annual % return (simple, no compounding) is the cross-idea comparison key. |

For improvements with **no revenue** (corporate media, gifts, extra sick days): set gain = 0, count only cost → a deliberate negative-ROI investment. **Everything is countable** — ~9 of 10 cases by revenue, the rest by cost.

### "Task as credit" logic (the PRO verdict)
Treat each task's budget as a loan. If the task's **annual return > the cost of capital** (loan rate / deposit / central-bank rate), it's worth doing. E.g. capital at 18%/yr, task returns 35%/yr → +17% profit/yr → do it. Sort the backlog from highest to lowest annual return.

> **PRO model** (as used by `brainstorm-features`): cost-in-hours × rate → effect → **% annual return**, then the task-as-credit verdict against the cost of capital. It is the money-based counterpart to ICE and is computed *alongside* ICE by default (one on explicit request only).

### Confidence (RICE-style add-on)
ROAIP ignores forecast certainty. Attach a **Confidence %** (80 / 90 / 100). A $1,000 idea at high confidence can beat a $10,000 idea at low probability. This mirrors the **C** in RICE and prevents chasing attractive-but-unlikely ideas.

---

## Practical decision recipes

- **Buy a service vs not:** compare service cost to the cost of the work-time it saves. Service cost < saved-time value → buy.
- **In-house vs external API:** cost of own build + a year of support vs external API + integration for a year; take the pessimistic Net Profit and ROI. If not a core competency and cheaper to buy — buy.
- **Hiring / delegation ROI** (`delegation-coach`): monthly hours freed × rate vs the cost of the resource; positive payback → open the role / outsource. "Saving" by *not* hiring is not a saving if it blocks a project worth far more.

---

## Reporting improvements (ties to 3T5F)

In a 3T5F report's **Top-3 Highlights**, state literally how much each highlight brings per year and its ROI. E.g. "1. Auto-import of CVs — $10k profit over 4 yrs, 300% ROI. 2. Auto-sorting of candidates — $2k over 3 yrs, 90% ROI."

---

## Scope & typical errors
- **Scope:** ROAIP/PRO is for grounded, practical improvements — **not** strategic business-paradigm shifts (those compare different orders of magnitude and don't belong in the table).
- Not costing improvements at all (deciding on emotion/intuition).
- Looking only at ROI% without the absolute profit, or vice versa.
- Ignoring Confidence.
- Counting only "what it costs", not "what it brings".
- Building in-house what isn't a core competency and is cheaper to buy.

---

## References
- `references/reporting-3t5f.md` — Top-3 Highlights with $ / ROI
- `references/people-frameworks.md` — delegation/hiring ROI in the 7-levels audit
- `skills/brainstorm-features/SKILL.md` — PRO + ICE scoring
- `skills/decision-log/SKILL.md`, `skills/experiment-tracker/SKILL.md` — cost-of-decision / cost-of-test
