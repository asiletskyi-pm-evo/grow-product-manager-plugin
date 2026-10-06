# Minutes of meeting — gold exemplar (meeting-processor)

> Gold exemplar for testing/output-evals.md (meeting-processor rubric). Fixture: testing/fixtures/meeting-processor/brief-v1.md.

<!-- Golden exemplar for the meeting-processor skill (Process mode → Structured MoM, meeting type Status / Agreements).
     Purpose: the ideal MoM for the fixture transcript — the quality bar the judge scores against and a few-shot pattern for the skill.
     Generic/anonymized: Product 1, Person1…Person5, PROJ-1234. NO org-specific data; the meeting is fictional.
     Written in English as a neutral reference; a real run writes in the user's `user.language`.
     Illustrates rigor and shape, not a rigid template — a matched meeting-notes template (Step T) takes precedence over this layout. -->

## Meeting Notes — Product 1 weekly product sync

**Date:** 2026-10-06 (Tue) | **Duration:** 30 min | **Type:** Status / Agreements

**Source:** transcript pasted in chat, 00:00–00:29 · no calendar lookup, so emails are not in the source · notes kept by Person1

**Evidence:** reported — meeting transcript 2026-10-06 (every figure and statement as its named speaker said it)

---

### Participants
| Name | Role | Email | Status |
|------|------|-------|--------|
| Person1 | Product Manager (facilitator, notes) | — | Attended, spoke |
| Person2 | Product Designer | — | Attended, spoke |
| Person3 | Data Analyst | — | Attended, spoke |
| Person4 | Backend Tech Lead | — | Attended, spoke |
| Person5 | Frontend Engineer | — | Attended, spoke |

---

### Topics Discussed
1. **Status: search-filter fix** — Person5: live for 100% of users since Monday (2026-10-05), no new errors in the logs. Person1 closed the item.
2. **Delivery cost is shown too late** — Person3: 41% of sessions that reach the delivery step leave checkout there, and "unexpected delivery cost" is the top exit-survey reason at 27% of answers (both for 2026-09-07 – 2026-10-04, four weeks). Person2: usability sessions show the same — buyers see the price only on checkout step 3.
3. **Options for showing the cost earlier** — Person2 proposed a "Delivery from X" estimate under the price on the product page, based on the buyer's city; Person4 proposed moving the delivery step to the start of checkout. The reorder was dropped (see Decisions). The estimate can be calculated only for sellers on integrated carriers, because custom delivery rates are entered as free text; integrated carriers cover about 70% of orders in the same four weeks (Person3).
4. **Test or ship** — Person3 argued for an A/B test: an estimate higher than buyers expect could lower add-to-cart on the product page, so both effects must be measured. The team agreed (Decision 1).
5. **Parked idea** — Person2 suggested showing the delivery date next to the cost. Person1 parked it: not in this test, so the experiment does not mix two changes.
6. **Tariff API capacity** — Person4 does not know whether the carrier tariff API can take a call on every product-page view; if not, a cache is needed, probably one extra sprint. Checking it comes first (Action 2).
7. **Estimate for guests** — three options raised, none chosen (see Open Questions).

---

### Decisions
| # | Decision | Context | Owner |
|---|----------|---------|-------|
| 1 | Show an estimated delivery cost on the product page, for sellers on integrated carriers only, as a 50/50 A/B test. Primary metric: checkout completion from the delivery step. Guardrail: product-page add-to-cart rate. | Buyers learn the delivery cost too late: 41% leave at the delivery step, and "unexpected delivery cost" is the top exit reason at 27% (Person3, 2026-09-07 – 2026-10-04). Integrated carriers only, because custom rates are free text; they still cover ~70% of orders in that period (Person3). A test rather than a direct ship, because a high estimate may lower add-to-cart. **Rejected alternative:** move the delivery step to the start of checkout (Person4). Rejected because buyers would still see the cost only after committing to checkout (Person3), and checkout is frozen for the payment-provider migration until mid-November (Person5); Person4 withdrew it. No numeric ship threshold was set in the meeting. | Person1 — stated the decision; Person2, Person3, Person4 and Person5 agreed, no objections |

Not decisions: the delivery-date idea (parked, Topic 5) and the 2026-10-26 launch date (tentative, see Deadlines).

---

### Action Items
| # | Action | Owner | Deadline | Status |
|---|--------|-------|----------|--------|
| 1 | Person3 will split the delivery-step drop-off by carrier type (integrated vs. custom rates) for 2026-09-07 – 2026-10-04 and post the result in the team channel. | Person3 | 2026-10-08 (Thu) | Open |
| 2 | Person4 will confirm with the carrier-integration owners whether the tariff API supports per-city estimates and what its rate limits are, and will say whether the 2026-10-26 launch still holds. | Person4 | 2026-10-09 (Fri) | Open |
| 3 | Person2 will prepare product-page mockups of the estimate line for a logged-in buyer with a saved address, with a placeholder for the guest state. | Person2 | 2026-10-12 (Mon) | Open |
| 4 | Person5 will write the analytics event spec — estimate shown, estimate expanded, delivery step reached — and get it reviewed by Person3. | Person5 | 2026-10-14 (Wed) | Open |
| 5 | Person1 will write the A/B test requirements and link them to epic PROJ-1234. | Person1 | 2026-10-15 (Thu) | Open |

One owner per action. Action 2 was first offered as a joint check by Person4 and Person5; Person1 asked for one name and Person4 took it. In Action 4, Person3 reviews — the spec is Person5's.

---

### Status / Agreements

**Progress updates**
- Search-filter fix — at 100% of users since 2026-10-05, no new errors (Person5). Closed.

**Agreements**
- Captured as Action Items 1–5 above — each with one owner and a date.

**Risks**
- The carrier tariff API may not handle a call on every product-page view. Then a cache is needed (probably one extra sprint) and the 2026-10-26 launch will not hold (Person4). The answer is due with Action 2.
- An estimate higher than buyers expect may lower product-page add-to-cart (Person3). The A/B test and its guardrail cover this.

**Blockers**
- None for the chosen option. Constraint: checkout is frozen for the payment-provider migration until mid-November (Person5), which rules out checkout changes, including the rejected reorder.

**Deadlines**
| Item | Date | Status |
|------|------|--------|
| A/B test launch | 2026-10-26 | Tentative — depends on the API answer (Action 2, 2026-10-09) |
| Action Items 1–5 | 2026-10-08 → 2026-10-15 | Open |

---

### Open Questions
- **Which city should the estimate use when a buyer has no saved address (guests)?** Options raised: IP-based city — often wrong on mobile networks (Person3); a city field on the product page (Person5); the most frequent delivery city, clearly labelled as an estimate (Person4). Not decided — Person1: come back to it once the mockups are ready (Action 3, 2026-10-12). No owner was assigned in the meeting.

Altitude: L2 · ↑ serves: — (no linked goal) · ↓ next: create Jira tasks for Action Items 1–5 under epic PROJ-1234 via task-creator

---

Here are the meeting notes. Please review — are there any corrections or additions?

**Publishing:** kept in chat, as requested — nothing written to Confluence.

**Next steps — shall I:**
1. Create Jira tasks for Action Items 1–5 under epic PROJ-1234? I'll pass the actions with owners and deadlines, the participants with roles, and these notes as the source to `task-creator`.
2. Log Decision 1 in the decision log — with the rejected checkout reorder and both reasons — so the "why" survives? That goes to `decision-log` (log mode).
3. Draft the A/B test requirements for Action 5 now? I'll pass the decision, the metrics, the integrated-carrier scope and the open guest question to `requirements-creator`.

<!-- Judge notes — not part of the skill output. Where each rubric point comes from in the fixture transcript:
     decisions_extracted: Decision 1 stated at 00:12, agreed 00:13; rejected alternative 00:06, its two reasons 00:07, withdrawn 00:08;
       scope 00:09–00:10; test rationale 00:11. The parked idea (00:14) and the tentative date (00:26) are deliberately not decisions.
     action_items_with_owner: A1 00:18 · A2 00:16–00:17 (one owner after Person1 asked for one name) · A3 00:20 · A4 00:24 · A5 00:25.
       Every action date is stated in the transcript; the one derived date ("Monday" -> 2026-10-05, Topic 1)
       and all weekdays resolve against the meeting date 2026-10-06.
     no_hallucinated_content: no emails (none in the source), no numeric thresholds, no owner for the open question,
       "mid-November" kept as said, no extra topics beyond the transcript.
     evidence labels (since v3.8.0): one artifact-level Evidence line — everything here was said in the meeting, so it is
       `reported`; Person3's figures (00:02–00:03, 00:10) keep their speaker and stay `reported`, not `measured` — a number said
       aloud is a statement, whatever it was read from. The label adds no content; no quote is taken from a summary. The two quote-marked
       strings are names said in the meeting, verbatim: "unexpected delivery cost" (Person3, 00:03), "Delivery from X" (Person2, 00:05).
     structured_summary: the skill's Structured MoM skeleton (Step M6a) plus the Status / Agreements blocks (Step M5b).
     chain_offer: task-creator for agreements with deadlines and decision-log for the decision (Step M9); requirements-creator for Action 5. -->
