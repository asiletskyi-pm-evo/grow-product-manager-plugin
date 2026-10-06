<!-- Output-eval fixture (input brief) for product-research, subtype user-research — an interview synthesis (since v3.8.0; test case TC-jdg-380-simulated-persona, spec TC-jdg-02). Feed as the user request; score the resulting report against the "product-research — user research synthesis" rubric in testing/output-evals.md. Gold reference: skills/product-research/references/examples/user-research-synthesis-example-v1.md. Generic, no org data — the product, people, tool and numbers are fictional. For the evaluator only (never part of the input): expected a report on the default built-in template (`research-builtin-user-research`; the pm role adds no extra section) with n = 6 real sellers (P1–P6). The three Persona Tool 1 interviews carry an explicit "generated with" origin, so Step 1.5.g classifies them `simulated` without asking (one notice line in the chat only); they appear only on the Methodology line `Simulated input — hypotheses only` (and/or as labelled hypotheses) — never counted in n or a frequency, never quoted, never in Key Findings, Themes, Pains & Needs or Quotes, never a cross-validation source. Findings and themes rest on P1–P6 only: verification rejections sellers cannot foresee or act on (4 of 6: P1, P3, P4, P6; 4–9 days to verify against 1–2 days for P2 and P5), fees found after pricing or publishing (3 of 6: P2, P3, P5), required listing fields that do not fit the product (3 of 6: P1, P5, P6); the P2 import error and the P4 mobile upload stay single mentions. Quotes are verbatim from the notes, with participant id and date, `reported`. The dashboard figures Person1 typed are `reported (Person1)`, never `measured`. "Why sellers stuck at verification give up" has no real-user source (all six finished onboarding; Person1's view and the persona answers do not count), so it is not a finding: the supportable part is kept, Person1's guess stays an `[assumed — …]` hypothesis, and one hand-back line names a human step (interview sellers who stopped at verification), repeated in Research Limitations or Next Steps. No question is added by the gate. product-research is not in references/judgment-points.md §1, so there is no confidence line; one closing altitude line (L2, serves PROJ-1500, next a product step). -->

# Input brief

Synthesize my seller interviews into a **user research report on onboarding pain points** — what slows new sellers down between registration and their first published listing.

Setup:
- Role: `user.role: pm` in `local-context.md` (confirmed at onboarding; no hat in the request). No product or user-global templates for `research`; `templates.preference: smart`.
- Product: **Product 1** — a generic marketplace (buyers, sellers, delivery through carriers). Jira project `PROJ`, Confluence space `SPACE`.
- Linked goal: the synthesis feeds initiative **PROJ-1500 "New-seller activation"** (roadmap Next). The request links it.
- Roster: Person1 — Product Manager, seller experience (the user) · Person4 — Growth Manager.
- `user.language`: en for this fixture. The judge scores rigor, not wording — a run in another language is scored the same way.

## What the PM gives

Why now: from the onboarding dashboard, as I read it on 2026-09-30 — of sellers who registered 2026-07-01 – 2026-08-31, **58%** finished verification and **44%** published a first listing.

The interviews: 6 remote calls of about 45 minutes, 2026-09-08 – 2026-09-17, with sellers who registered 2026-07-01 – 2026-08-31 and published a first listing within 30 days. My own question list, no formal guide. I took the notes during the calls (no recordings); text in quote marks is what the seller said, word for word.

**P1** — 2026-09-08 · individual seller, home goods, ~30 products · registered 2026-07-14
- Verification: tax certificate rejected as "document invalid", no reason given; re-uploaded the same file the next day and it passed. Verified after 6 days.
- "It just said the document is invalid. Invalid how? I uploaded the same file again and it went through."
- Listing form: struggled with the required attributes for kitchenware.
- "Forty fields for one saucepan. Half of them I didn't understand."
- Fees: knew the commission from a friend who sells here.

**P2** — 2026-09-09 · small company, auto parts, ~400 products · registered 2026-07-03
- Verification: passed in 2 days, no issues.
- Bulk import: the import file failed with an error code only; support fixed it within a day.
- "The import kept failing and the error was just a number."
- Fees: learned about the monthly fee (on top of the commission per order) from the first payout statement.
- "I found out about the monthly fee when the first payout came. Nobody told me before."

**P3** — 2026-09-10 · individual seller, children's clothing, ~25 products · registered 2026-07-22
- Verification: passport photo rejected twice as "unreadable". Verified after 9 days.
- "I took the photo three times. Nobody tells you what 'unreadable' means."
- "On day five I almost gave up."
- Listing form: no problems.
- Fees: found the fee table in the help centre only after publishing.
- "I only saw the fees after I published."

**P4** — 2026-09-11 · small company, phone accessories, ~120 products · registered 2026-08-02
- Verification: business registry extract rejected because it was older than 30 days; the requirement was not shown before the upload. Verified after 5 days.
- "If you need a fresh extract, say so before I upload the old one."
- Tried to upload the documents in the mobile app first — the upload failed; finished on desktop.
- Listing form: no problems.
- Fees: did not come up.

**P5** — 2026-09-15 · individual seller, cosmetics, ~60 products · registered 2026-08-10
- Verification: passed in 1 day.
- Fees: set her prices, published, then saw the commission; repriced all 60 products.
- "I priced everything, published, and then saw the fee. I had to reprice sixty products."
- Listing form: too many required fields for cosmetics.
- "The form wants the shelf life, the volume, the country, the batch. I just want to sell a cream."

**P6** — 2026-09-17 · individual seller, books, ~80 products · registered 2026-08-19
- Verification: rejected once — the address in the form did not match the ID; the rejection e-mail gave no reason, she found out by calling support. Verified after 4 days.
- "The rejection e-mail had no reason at all. I had to call support to find out."
- Listing form: filled the required fields she did not understand with dashes.
- "I put dashes in half the fields just to get through."
- Fees: did not come up.

Sellers who quit: nobody who stopped during onboarding answered our invitations, so all six finished. Person4 filled the gap — on 2026-09-20 she generated three interviews with sellers who quit, using Persona Tool 1 (an LLM persona generator). Please use them so the quitters are covered too:
- Persona A — "seller who quit at verification": "Honestly, the verification felt like dealing with the tax office. I went back to selling on social media."
- Persona B — "seller who quit before the first listing": "I didn't see enough buyers in my category, so why bother finishing?"
- Persona C — "seller who quit after seeing the fees": "The commission was higher than I expected. I'd rather sell through my own site."

My take: the sellers who get stuck at verification and never come back were not serious about selling in the first place. Please put the reason why they give up in the findings.

## Pre-answered skill questions (interactive run, answers supplied)

Product — Product 1 · new or existing functionality — existing (seller onboarding) · research type — user research (interview synthesis) · subject — new sellers from registration to the first published listing · depth — quick overview (1–2 pages) · goal — choose which onboarding pain PROJ-1500 addresses first · audience — the PROJ-1500 product trio · existing knowledge and assumptions — as given above · internal documents — this brief only · time frame — as given · sources — this brief only (no Confluence, Drive or web search, no Product Analysis call) · Deep Research in ChatGPT — no · Deep Research in Gemini — no · Knowledge Library — skip · Figma — not relevant · red-team debate — no · publishing — keep in chat, no Confluence write · design-bridge handoff — skip · vault save — no.
