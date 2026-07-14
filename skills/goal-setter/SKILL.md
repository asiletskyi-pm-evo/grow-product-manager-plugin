---
name: goal-setter
version: 0.1.1
description: Set and audit goals for a person, team, product, direction, project, or a candidate offer — using SMARTCBP for personal goals and OKR for product/direction goals. Use when the user asks to "set a goal", "write goals for <person>", "audit this goal", "is this goal SMART", "goal letter", "cascade goals", "OKR for the quarter", "objectives and key results", "review goals for the period". Українською — "постав ціль", "сформулюй цілі для <людини>", "проведи аудит цілі", "ціль за SMARTCBP", "лист цілей", "каскад цілей", "OKR на квартал", "цілі напрямку", "переглянути цілі за період". Do NOT use to report progress against an existing goal (product-reporter goal-report / 3T5F), to review a person's overall performance (performance-review), or to build a delivery roadmap (quarterly-planning / project-planning). This skill formulates and commits goals; other skills track and report them.
---

# Goal Setter

Formulates and audits **goals** — the foundation of the People-contour. Without a well-set goal, neither reporting (3T5F), nor performance review, nor a hiring offer works. The skill chooses the right methodology (SMARTCBP for personal goals, OKR for product/direction), produces or audits the goal, drives it to **commitment** (Tell and Sell), and records it on the person's profile.

The PM decides; the skill formulates, audits, and records. It never invents a baseline or a link it cannot source.

## Prerequisites
- `references/local-context-protocol.md` — Step 0. Context used: active product, `product.current_okrs`, Planning `goal_map`/Mission Atlas, `user.language`.
- `references/people-context-protocol.md` — **Step P**, when the goal is for a specific person (load/create profile; write `active_goal_letter`, commitment).
- `references/goal-frameworks.md` — SMARTCBP (8 checks), MBO vs OKR selection, Tell and Sell, goal letter, cascade.
- `references/planning-core.md` — Mission/Goal Atlas as the top of the cascade.
- `references/reporting-3t5f.md` — Comparable baseline source; chain to set up reporting.
- `references/roi-frameworks.md` — quantify goal value where relevant.
- `references/template-protocol.md` — **Step T** (`goal-letter` template).
- `references/data-policy.md` — a person's goals are People-data (local/vault).
- `references/self-improvement.md` — learn from corrections.

## Objects & methodology

| Goal object | Default methodology |
|-------------|---------------------|
| A person / individual accountability | **SMARTCBP** |
| A candidate offer (goal letter) | **SMARTCBP** on a 3/6/12-month horizon |
| A team | SMARTCBP (per-person) or OKR — ask |
| A product / direction (ambitious, public, quarterly) | **OKR** (Objective + 2–5 Key Results) |
| A project / initiative | OKR at the top, SMARTCBP for owners |

Selection follows the MBO-vs-OKR table in `goal-frameworks.md`. When both could apply, prefer SMARTCBP for the individual and cascade it under the OKR/Mission.

## Modes

| Mode | Trigger | What it does |
|------|---------|--------------|
| `formulate` (default) | "постав ціль", "set a goal" | Draft **2–3 variants** of a goal from the user's intent, each passing all 8 SMARTCBP checks (or an OKR set). |
| `audit` | "проведи аудит цілі", "is this goal SMART" | Score a draft goal against the 8 checks in a **requirement / status / fix** table; return the corrected one-sentence goal. |
| `cascade` | "каскад цілей", "cascade goals" | Ladder Mission/Goal (Atlas) → direction → team → person; flag marking gaps, don't invent links. |
| `goal-letter` | "лист цілей", "goal for the offer" | Build a full goal letter (purpose, 3–5 SMARTCBP results, traits, culture) for an offer or a periodic review. |

## Pipeline

### Step 0 — Local context
Per `local-context-protocol.md`. Load the active product, Mission Atlas / `goal_map`, and `product.current_okrs`.

### Step P — Person context (when the goal is for a person)
Per `people-context-protocol.md`. Load or offer to create the profile; read `d_type` (a D4 gets a goal, not tasks — confirm scope fits), reporting cadence, and any existing `active_goal_letter`.

### Step T — Template resolution
For `goal-letter` (and optionally `formulate`): `artifact_type: goal-letter`, resolve per `template-protocol.md`.

### Step 1 — Object & methodology
Confirm the goal object and pick the methodology (table above). State the choice and why ("Personal goal → SMARTCBP: realistic, personal accountability, bonus-compatible").

### Step 2 — Comparable baseline
For **C (Comparable)**, offer to pull the prior-period fact:
- Chain to `product-reporter` / Tableau for the person's or direction's last-period number.
- If no history → benchmark the market, or use "+N p.p. on the measured KPI".
Never leave C empty; never fabricate the number — mark it "to confirm" if unsourced.

### Step 3 — Formulate / audit
- **formulate:** produce 2–3 one-sentence variants; each verified against all 8 letters + the common-sense filter; confirm each goal sits **outside** the performer's process.
- **audit:** render the before→after table (requirement / status / issue / rewrite), then the single corrected sentence. Run the AI self-check ("can progress be judged unambiguously from a report?").
- **cascade:** build the tree; every child ladders to its parent (SMARTCBP-P traceability); surface any gap as "pending PM confirmation".
- **OKR path:** 1 Objective + 2–5 measurable Key Results; ambitious (70–80% = success), public, decoupled from bonuses.

Keep it to **3 goals per person, max 5**. Each goal one sentence.

### Step 4 — Commitment (Tell and Sell)
Run the Tell-and-Sell checklist (`goal-frameworks.md`): participation, restatement, baseline acceptance, risk named, explicit "I commit". Record commitment status.

### Step 5 — Record & chain
- **Step P write:** save `active_goal_letter`, `goal_methodology`, commitment to the person's profile (gated show-before-save). People-data stays local/vault.
- Chain: → `product-reporter` (set up 3T5F reporting at the chosen cadence) · → `one-on-one` (discuss/commit the goal) · → `hiring-designer` (goal letter into the offer) · → `decision-log` (if a strategic goal decision was made).

### Step 6 — Feedback + self-improvement
Per `self-improvement.md`.

## Quality standards
- A goal is **one sentence**; 3 per person (max 5); always outside the performer's process.
- All 8 SMARTCBP letters pass, or the gap is named — never a silent partial.
- Comparable is sourced or explicitly marked "to confirm"; never fabricated.
- Personal goals → SMARTCBP (realistic, <100% = miss); product/direction → OKR (stretch, public). State the choice.
- Commitment is explicit before a goal is marked committed.
- People-data locality: a person's goals live in the vault/local only.
- Language — `user.language`.

## Skill chaining
→ `product-reporter` (3T5F reporting) · → `one-on-one` (commit/review) · → `hiring-designer` (offer goal letter) · → `performance-review` (goals become review inputs) · → `decision-log` (strategic goal decisions) · ← `focus-advisor`, `performance-review`, `offboarding-guide` (request goals be set/revised).

## Example dialogues
- *"Постав ціль аналітику Олені на друге півріччя"* → Step P loads Olena (D3, weekly reporting) → SMARTCBP → pulls her H1 fact via product-reporter for Comparable → 2–3 variants → Tell-and-Sell → writes `active_goal_letter`, offers to set up her 3T5F cadence.
- *"Це нормальна ціль: 'покращити конверсію'?"* → `audit` mode → 8-check table shows S/M/C/T failures → returns "increase checkout conversion from 2.1% to 3.0% (+0.9 p.p. vs H1) by 2026-12-31".
- *"Зроби OKR для напрямку Q&A на квартал"* → OKR path: 1 Objective + 3 Key Results, public, stretch → offers to cascade personal SMARTCBP goals for the owners underneath.
