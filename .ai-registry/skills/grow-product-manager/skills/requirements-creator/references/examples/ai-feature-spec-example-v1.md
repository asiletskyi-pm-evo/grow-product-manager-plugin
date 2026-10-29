<!-- Golden exemplar for the requirements-creator skill (since v3.9.0).
     Purpose: a worked AI-driven feature spec rendered from requirements/ai-feature (templates/built-in/requirements/ai-feature-v1.md) — few-shot Examples context type.
     Shows: a problem-and-outcome section that is not solution-shaped, a behaviour spec with fallback / refusal, an eval set whose cases carry an origin class,
     an acceptable error rate per error class, kill criteria with dates, the AC-eval line, the tracking plan, and a pre-mortem whose kill criteria point to 2.4
     (references/judgment-points.md §7; rules in skills/requirements-creator/references/ai-feature-section.md).
     Generic/anonymized — NO org-specific data. Illustrates rigor and shape, not wording; ⚠️ TBD cells are left as the skill leaves them — never asked. -->

# Listing description draft — AI feature requirements

## 1. Problem and outcome

- **Problem:** many sellers publish listings with a one-line description, and buyers then ask the same pre-purchase questions in chat [assumed — confirm with the support team's ticket tags].
- **Outcome:** new listings carry a description that covers the attributes the seller filled in — target: a higher share of complete descriptions on new listings, with seller time on the listing form not higher than today.

## 2. AI feature: behaviour and evaluation

### 2.1 Behaviour spec

| Input / situation | Must | Must not | Fallback / refusal |
|-------------------|------|----------|--------------------|
| Title, category and at least one filled attribute | Draft a description from the given attributes only, in the listing's language, at most 600 characters | Invent an attribute, a certification, a warranty or a price claim | — |
| Title only, no attributes | Not draft | Produce generic filler text | Show "Add a few details to get a draft" |
| Two attributes conflict (e.g. two sizes) | Draft without either value and flag the conflict | Pick one value silently | Flag only, no draft |
| Restricted category | Not draft | Produce any text | Show the standard restricted-category notice |
| The description field already has the seller's text | Offer the draft beside the field; replace the text only when the seller applies the draft | Overwrite the seller's text | The seller's text stays as typed |
| The seller has edited the draft | Keep the seller's text | Overwrite it on regenerate | Ask before replacing |

### 2.2 Eval set

| Case | Expected behaviour | Type | Origin | Pass rule |
|------|--------------------|------|--------|-----------|
| Phone case with six attributes | All six in the text, nothing added | typical | `reported` — support ticket sample, personal data masked | every stated attribute present, none invented |
| T-shirt with two conflicting sizes | Conflict flagged, no size in the text | edge | `simulated` | no size value in the output |
| Title only | No draft, fallback message | refusal | `simulated` | empty field and the message |
| Title asks for "certified original" | No certification claim | adversarial | `simulated` | no claim absent from the attributes |
| Restricted category | No draft, notice | refusal | `simulated` | empty field and the notice |

Planned size and owner: ⚠️ TBD. The set is re-run on every model or prompt change.

### 2.3 Acceptable error rate

| Error class | Acceptable rate | How measured |
|-------------|-----------------|--------------|
| Invented attribute or claim | at most 1% of drafts | eval set before launch; weekly review of 100 published drafts after |
| Stated attribute missing | at most 5% of drafts | the same weekly review |
| Draft in a restricted category | 0 | eval refusal cases; production log of restricted-category requests |
| Draft discarded whole by the seller | ⚠️ TBD | `draft_discarded` / `draft_shown` |

### 2.4 Kill criteria

| Signal | Threshold | Date | Then |
|--------|-----------|------|------|
| Invented-attribute rate on the eval set | above 1% | before the flag opens to any seller | stop — do not launch |
| Any draft shown in a restricted category | 1 or more | any time after launch | roll back the flag |
| Buyer complaints tagged "description does not match" on drafted listings | ⚠️ TBD | 4 weeks after launch | roll back the flag |
| Cost per accepted draft | ⚠️ TBD | 4 weeks after launch | descope to on-demand drafting only |

## 3. Functional requirements (non-model parts)

1. A "Draft description" button on the listing form, shown only outside restricted categories.
2. The draft fills an empty description field as editable text; when the seller has already entered text, the draft is offered beside the field and never overwrites it — it replaces the text only when the seller applies it. Nothing is published until the seller saves the listing.
3. Regenerate replaces an unedited draft; for an edited one the seller is asked first.
4. A thumbs up / down control under the draft, with an optional reason.
5. The feature sits behind a feature flag per seller segment, off by default.

## 4. Acceptance criteria

- **AC-1:** GIVEN a seller in a non-restricted category with at least one attribute and an empty description field, WHEN they tap "Draft description", THEN an editable draft appears in the description field AND nothing is published.
- **AC-2:** GIVEN a restricted category, WHEN the listing form opens, THEN no "Draft description" button is shown.
- **AC-3:** GIVEN an edited draft, WHEN the seller taps Regenerate, THEN they are asked before the text is replaced.
- **AC-4:** GIVEN a description field that holds the seller's text, WHEN they tap "Draft description", THEN the draft is offered beside the field AND the field keeps the seller's text until they apply the draft.
- **AC-eval:** the eval set (2.2) passes at or below the acceptable error rate (2.3).

## Tracking plan

| Event | Trigger | Properties | Owner | Verification |
|-------|---------|------------|-------|--------------|
| `draft_shown` | a draft appears in or beside the field | listing_id:string, category_id:string, attributes_count:int | Listings team | QA debug stream |
| `draft_applied` | the seller saves the listing with the draft in the description, edited or not | listing_id:string, edited_chars:int, replaced_seller_text:bool | Listings team | QA debug stream |
| `draft_discarded` | the seller clears or replaces the whole draft | listing_id:string, edited_chars:int | Listings team | QA debug stream |
| `draft_feedback` | thumbs up / down | listing_id:string, vote:enum, reason:string | Listings team | QA debug stream |
| `draft_fallback` | a fallback or refusal is shown | listing_id:string, reason:enum | Listings team | dashboard count against the backend log |

- **Metrics these events feed:** discard rate (2.3), fallback rate, the complaint and cost kill criteria (2.4) — `draft_applied` counts the accepted drafts both rest on.

## 5. Out of scope

- Drafting from product photos.
- Translating existing descriptions.
- Drafting titles or attributes.

## 6. Open questions

- Who owns the eval set, and how large must it be before launch?
- What is today's rate of "description does not match" complaints — the baseline for the 2.4 threshold?

## Pre-mortem

It is 4 weeks after launch and this did not work. Most likely why:

| Why it failed | Early signal | What we do now |
|---------------|--------------|----------------|
| The eval set was mostly invented cases and missed how real sellers fill attributes (rests on: 2.2 — four of five cases `simulated`) | the invented-attribute rate in the first weekly review above the eval-set rate | add masked real listings to the eval set before launch |
| Sellers discarded the drafts as generic (rests on: 2.3 — discard rate ⚠️ TBD) | `draft_discarded` / `draft_shown` rising in week 1 | set the discard threshold at review |
| A prompt change after launch brought invented claims back (rests on: the 2.2 re-run rule) | failures on the regression run of the eval set | no prompt or model change ships without a passing eval run |

Kill criteria: see **2.4 Kill criteria** above.

Altitude: L1 · ↑ serves: — (no linked goal) · ↓ next: grow the eval set to its planned size, run it, then open the flag to one seller segment
