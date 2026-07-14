---
name: hiring-designer
version: 0.1.1
description: Design a role and a vacancy profile the way strong hiring is done — the goal letter (SMARTCBP goals on a 3/6/12-month horizon) is written BEFORE the vacancy, and the offer = goals + conditions. Produces a universal vacancy profile, killer questions, screening criteria based strictly on past experience vs goals, interview questions from the role goals, a candidate-evaluation table, and an offer draft. Use when the user asks to "open a vacancy", "design a role", "write a job profile", "hiring", "killer questions", "screening criteria", "evaluate candidates", "draft an offer". Українською — "відкрити вакансію", "спроєктувати посаду", "профіль вакансії", "найм", "вітальні запитання", "критерії скринінгу", "оцінити кандидатів", "чернетка оферу". Do NOT use to write product/feature requirements (requirements-creator) or to set an existing employee's goals outside a hire (goal-setter — which this skill chains to for the role goals).
---

# Hiring Designer

Hiring is the manager's most important skill — a well-hired specialist "pulls everything out of any swamp". The base principle is **"designing the role"**: the goal letter (SMARTCBP goals) is prepared **before** the vacancy opens, and the offer = goals + conditions. Screening evaluates **past experience against the role's goals** — never impressions or "voodoo recruiting".

## Prerequisites
- `references/local-context-protocol.md` — Step 0. Context: active product, team, `user.language`, and the **employer HR-form field map** (`people.hr_form` — selects for Budget/Team/Position/Employment type/Probation length, etc.; set up by plugin-configurator).
- `references/people-context-protocol.md` — **Step P** on hire (create the new person's profile: curator, S1 style, probation = offer goals).
- `references/goal-frameworks.md` — SMARTCBP goal letter (3/6/12-month), goals vs tasks.
- `references/people-frameworks.md` — D-type of the target, S1 onboarding.
- `references/roi-frameworks.md` — hiring cost/ROI framing.
- `references/template-protocol.md` — **Step T** (`vacancy-profile` built-in template).
- `references/integration-strategy.md` — LinkedIn/job boards via browser fallback (sourcing ideal profiles).
- `references/self-improvement.md`.

## The universal vacancy profile (the `vacancy-profile` template)

A synthesis of the role-design framework and a typical HR form. Five sections:

1. **Request** — budget; country of employment; team; position; team composition (roles, headcount, team goals, most-frequent interactions; if the role is new — why it appeared); reason for opening; direct manager; workplace; equipment/software.
2. **Role goals** (the heart) — a SMARTCBP goal letter on **3 / 6 / 12 months**, tasks separated from goals. For a brand-new role, Comparable = 0.
3. **Vacancy description** — open date; team tools; candidate requirements split into **must-have** and **nice-to-have**; core duties/tasks; extra info (KPIs, financial motivation, potential candidates); 4–5 ideal candidate LinkedIn profiles.
4. **Hiring conditions** — employment type; Gross/Net salary for the probation period and after + currency; probation duration.
5. **Selection process** — test task; participants in the process; **killer questions** (welcome questions).

The skill maps this universal profile onto the **employer's HR-form fields** (from `local-context.md → people.hr_form`) so the text can be pasted field-by-field into the employer's form.

## Pipeline

### Step 0 — Local context
Per `local-context-protocol.md`. Load the HR-form field map; if absent, offer to set it up via `plugin-configurator` → People-setup (or collect ad-hoc for this vacancy).

### Step T — Template resolution
`artifact_type: vacancy-profile`, resolve per `template-protocol.md`.

### Step 1 — Design the role (goals first)
Start from **"what results must the new hire achieve for me to call this a successful hire?"** — results, not processes; realistic minimum-satisfactory. Chain to `goal-setter` (goal-letter mode) to produce the SMARTCBP goals on 3/6/12 months (Comparable = 0 for new roles). Name a **role model** (a concrete reference person / archetype) so requesters align.

### Step 2 — Screening criteria & killer questions
- **Widen the funnel:** drop needless requirements (English if no client contact, a degree, "N years of experience").
- **Killer questions** — about *past experience* (not theory), answered with a number or yes/no, each with an If/Then rule for the recruiter. Purpose: unambiguously screen **out**. Avoid open questions ("tell me about your best case").
- **Screening rubric:** past experience vs the role goals — which similar goals were already achieved, which behavior patterns predict success. Not language confidence or a handshake.

### Step 3 — Test task or candidate documents
- **Test task:** ultra-short (≤1h), exactly from the future work, no "creative starred tasks", no hint of unpaid work; purpose = a positive decision. Don't lower the bar under mass review.
- **Candidate documents** (preferred): ask for 4–5 real work artifacts (manual, roadmap, concept, spec, analytics, client letter) without NDA data, and check: (1) meaning (is there substance vs water), (2) structure/form (headings, numbering, checklists, care for the reader), (3) quality of decisions (formulas vs manual, funnel completeness, SMART goals). Final question: "would I be happy if they made such documents for my manager or investor?"

### Step 4 — Interview questions & evaluation
- Interview questions derive **from the role goals** (similar goals achieved, how, details; don't let it drift to generalities). Probe negative-feedback experience; check grit ("tell me about a project that wasn't working — what did you do?").
- **Candidate evaluation table** — structured **goal × candidate experience**, not impressions:

| Role goal | Candidate A evidence | Fit % | Candidate B evidence | Fit % |
|-----------|---------------------|-------|---------------------|-------|

Below ~30% similar experience/goals → decline.

### Step 5 — Offer draft
Assemble the offer = probation & post-probation goals + tasks + conditions + salary/bonuses + team list, presented (not emailed cold). Map to the employer's HR-form fields.

### Step 6 — On hire → create the profile (Step P)
When a candidate is hired, create their person profile: assign a **curator**, start at **S1 style**, and set the **probation plan = the offer's goals** (plus small 1–2-week deliverables to see early whether they "carry"). Chain to `goal-setter` to commit the probation goals.

### Step 7 — Feedback + self-improvement
Per `self-improvement.md`.

## Quality standards
- The goal letter is written **before** the vacancy; the offer = goals + conditions.
- Screening is strictly past experience vs goals — no voodoo recruiting; killer questions are numeric/yes-no with If/Then.
- Candidate evaluation is a goal × experience table, not impressions; <~30% fit → decline.
- The universal profile is mapped to the employer's HR-form fields from local-context.
- On hire, a person profile is created (curator, S1, probation = offer goals).
- Language — `user.language`.

## Skill chaining
→ `goal-setter` (role/probation goal letter — the heart of the process) · Step P per `references/people-context-protocol.md` (create the new-hire profile) · → `one-on-one` (onboarding 1-1s) · ← `offboarding-guide` (re-design a role after parting ways). Boundary: not `requirements-creator` (that's product requirements, not job profiles).

## Example dialogues
- *"Відкриваємо вакансію продуктового аналітика"* → Step 1 chains to goal-setter for the 3/6/12-month goal letter → builds the 5-section vacancy profile mapped to the employer HR-form → 3 killer questions with numeric thresholds + If/Then → candidate-documents checklist.
- *"Оціни трьох кандидатів на цю роль"* → builds the goal × experience table from their artifacts/answers → flags Candidate B at 22% fit (decline) → drafts the offer for Candidate A with probation goals.
