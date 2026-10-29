> Gold exemplar for testing/output-evals.md (product-research — user research synthesis rubric). Fixture: testing/fixtures/product-research/synthesis-v1.md.

<!-- Golden exemplar for the product-research skill, subtype user-research (since v3.8.0; template builtin://research/user-research-v1.md, reached by the built-in ladder for a pm user with no template of their own).
     Purpose: the ideal interview synthesis for the fixture — the quality bar the judge scores against and a few-shot pattern for the skill (test case TC-jdg-380-simulated-persona, spec TC-jdg-02).
     Generic/anonymized: Product 1, Person1, Person4, P1–P6, Persona Tool 1, PROJ-1500. NO org-specific data; the numbers are fictional.
     Written in English as a neutral reference; a real run writes in the user's `user.language`.
     Evidence classes (since v3.8.0, Step 1.5.g): the interview notes are verbatim user research, so findings, themes, pains, needs and quotes are
     `reported`, and one group label per section covers them; the dashboard figures Person1 typed are `user-text` → `reported (Person1)`, not `measured`.
     The three Persona Tool 1 interviews say they were generated, so they are `simulated` without a question (one notice line in the chat, not in
     the report): their content sits only on the Simulated input line — never in n, a finding, a theme, a pain, a need or a quote.
     Why sellers stuck at verification give up has no real-user source (all six participants finished onboarding; Person1's view and the persona
     answers do not count), so Key Findings keeps the supportable part, keeps Person1's guess as an `[assumed — …]` hypothesis and adds one
     hand-back line, whose human step Research Limitations and Next Steps repeat.
     §11 Sources follows SKILL.md Step 4 and the source-count disclosure of references/data-integrity-protocol.md (the template has no Sources section).
     The pm role adds no extra section, and product-research is not in references/judgment-points.md §1, so there is no confidence line — the altitude line closes the report.
     A real run appends the template marker after the altitude line (template-protocol T-5 step 5); it is left out here. -->

# User Research: Seller onboarding pain points

## 1. Research Question

What slows new sellers down between registration and their first published listing on Product 1 — and which pain should the activation work (PROJ-1500) address first?

Why now: of sellers who registered 2026-07-01 – 2026-08-31, 58% finished verification and 44% published a first listing (reported · Person1, onboarding dashboard as read on 2026-09-30).

## 2. Methodology

- **Method:** interviews — 6 remote calls of about 45 minutes
- **Participants (n = real users only):** 6 (P1–P6)
- **Segments:**
  - Individual sellers — P1, P3, P5, P6
  - Small companies — P2, P4
  - All registered 2026-07-01 – 2026-08-31 and published a first listing within 30 days; no seller who stopped during onboarding took part.
- **Period:** 2026-09-08 – 2026-09-17
- **Simulated input — hypotheses only** (`simulated`): 3 interviews generated with Persona Tool 1 by Person4 on 2026-09-20, standing in for sellers who quit. They suggest three reasons to quit — verification that feels bureaucratic, too few buyers in the category, a commission above expectations. Not counted in n and not quoted; no finding rests on them. The study that would check them: interviews with sellers who stopped during onboarding (§10).

## 3. Protocol

- Script / guide: Person1's own question list (no formal discussion guide)
- Tools: remote calls; notes taken by Person1 during the calls, no recordings — text in quote marks is verbatim as noted
- Analysis: thematic coding / affinity mapping

## 4. Key Findings

Evidence: reported — interview notes P1–P6 (Person1, 2026-09-08 – 2026-09-17).

1. **Verification rejections are the most common and the costliest pain — 4 of 6.** P1, P3, P4 and P6 were rejected at least once, with a message they could not act on or for a requirement they saw only after uploading. They waited 4–9 days to be verified; P2 and P5, never rejected, took 1–2 days.
   - ⚠️ The data cannot settle why sellers stuck at verification give up: all six participants finished onboarding, and no seller who quit was interviewed. What the interviews do show is the cost — days of waiting, and P3 nearly gave up on day five. Person1's view that these sellers were not serious about selling stays a hypothesis [assumed — Person1's view; no seller who quit was asked]. Human step: interview 5 sellers who stopped at verification among the 2026-07-01 – 2026-08-31 registrations.
2. **Sellers learn the fees after pricing or publishing — 3 of 6.** P2 found the monthly fee on the first payout statement; P3 and P5 saw the fees only after publishing, and P5 repriced all 60 products.
3. **The listing form asks for required fields that do not fit the product — 3 of 6.** P1, P5 and P6 met fields they did not understand or did not need; P6 filled half of them with dashes to get through.

## 5. Themes & Patterns

### Verification rejections sellers cannot foresee or act on

- Evidence: reported — interviews P1, P3, P4, P6
- Quotes:
  - "It just said the document is invalid. Invalid how? I uploaded the same file again and it went through." — P1, interview 2026-09-08 · reported
  - "The rejection e-mail had no reason at all. I had to call support to find out." — P6, interview 2026-09-17 · reported
- Frequency: 4 of 6 real users

### Fees found after pricing or publishing

- Evidence: reported — interviews P2, P3, P5
- Quotes:
  - "I priced everything, published, and then saw the fee. I had to reprice sixty products." — P5, interview 2026-09-15 · reported
- Frequency: 3 of 6 real users (P1 knew the commission from a friend; P4 and P6 did not raise fees)

### Required listing fields that do not fit the product

- Evidence: reported — interviews P1, P5, P6
- Quotes:
  - "Forty fields for one saucepan. Half of them I didn't understand." — P1, interview 2026-09-08 · reported
  - "I put dashes in half the fields just to get through." — P6, interview 2026-09-17 · reported
- Frequency: 3 of 6 real users

**Single mentions — not themes** (reported · P2 and P4, 1 of 6 each): bulk-import errors shown only as a code (P2); a document upload that failed in the mobile app (P4).

## 6. Pains & Needs

Evidence: reported — interview notes P1–P6, as in §5.

### Pains
- A rejection with no usable reason, then days of waiting (P1, P3, P4, P6).
- Fees discovered after the prices are set (P2, P3, P5).
- Required fields that do not fit the product (P1, P5, P6).

### Needs
- Know the document requirements before uploading, and why a document failed (P1, P3, P4, P6).
- See the full cost — commission per order and the monthly fee — before setting prices (P2, P3, P5).
- Fill only the fields that matter for the product (P1, P5, P6).

### Jobs that are met
- Verification is quick when the documents pass the first time — 1–2 days for P2 and P5.
- Support fixes or explains a problem once a seller reaches it — P2's import within a day, P6's rejection reason by phone.

## 7. Quotes

Further quotes, verbatim as Person1 noted them during the calls (no recordings); those in §5 are not repeated.

> "I took the photo three times. Nobody tells you what 'unreadable' means." — P3, interview 2026-09-10 · reported

> "On day five I almost gave up." — P3, interview 2026-09-10 · reported

> "If you need a fresh extract, say so before I upload the old one." — P4, interview 2026-09-11 · reported

> "I found out about the monthly fee when the first payout came. Nobody told me before." — P2, interview 2026-09-09 · reported

> "I only saw the fees after I published." — P3, interview 2026-09-10 · reported

> "The form wants the shelf life, the volume, the country, the batch. I just want to sell a cream." — P5, interview 2026-09-15 · reported

> "The import kept failing and the error was just a number." — P2, interview 2026-09-09 · reported

## 8. Recommendations

- Show each document requirement before the upload (for example, a registry extract no older than 30 days and a readable ID photo), and the reason in every rejection message — finding 1.
- Show the commission per order and the monthly fee before the seller sets the first price — finding 2.
- Keep as required only the fields each category needs, and make the rest optional — finding 3.

## 9. Research Limitations

- **Only sellers who finished onboarding.** All six got through; no seller who stopped took part. The study shows what slows sellers down, not why others give up. Human step: interview 5 sellers who stopped at verification (the ⚠️ line in §4).
- **Small sample, one source type.** n = 6, interviews only: the frequencies describe this sample, not how common each pain is among new sellers. The dashboard figures in §1 are Person1's reading, not checked against a second source in this run.
- **Notes, not recordings.** Quotes are verbatim as Person1 wrote them during the calls.
- **Segments.** 4 individual sellers and 2 small companies (§2).

## 10. Next Steps

- Interview 5 sellers who stopped at verification among the 2026-07-01 – 2026-08-31 registrations; test Person1's hypothesis (§4) and the reasons on the Simulated input line (§2) there.
- Split the onboarding dashboard by rejection reason and by step for the same registrations, to see how common each pain is.
- Draft the onboarding concept for PROJ-1500 from findings 1–3 (write-concept).

## 11. Sources

| Source | Marker | Class |
|--------|--------|-------|
| Interview notes P1–P6, remote calls 2026-09-08 – 2026-09-17, written by Person1 and pasted in the request | `user-research` | `reported` (P1–P6, via Person1's notes) |
| Onboarding dashboard figures for registrations 2026-07-01 – 2026-08-31, as read by Person1 on 2026-09-30 | `user-text` | `reported` (Person1) — not read by this run |
| Person1's view on why sellers stuck at verification give up | `user-text` | `reported` (Person1) — not a real-user source; kept only as an `[assumed — …]` hypothesis |
| 3 interviews generated with Persona Tool 1 by Person4, 2026-09-20 | `user-text`, marked as generated | `simulated` — the §2 line only |

Altitude: L2 · ↑ serves: PROJ-1500 "New-seller activation" · ↓ next: interview 5 sellers who stopped at verification, then draft the onboarding concept for PROJ-1500 from findings 1–3
