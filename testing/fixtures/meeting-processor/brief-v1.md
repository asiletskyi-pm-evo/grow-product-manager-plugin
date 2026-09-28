<!-- Output-eval fixture (input brief) for meeting-processor. Feed as the user request; score the resulting MoM against the meeting-processor rubric in testing/output-evals.md. Gold reference: skills/meeting-processor/references/examples/mom-example-v1.md. Generic, no org data — the transcript is fictional. -->

# Input brief

Process this meeting into **minutes of meeting (MoM)** with decisions and ARCV action items.

Context the PM gives:
- Product: **Product 1** — a generic marketplace (buyers, sellers, delivery through carriers). Jira project `PROJ`, Confluence space `SPACE`.
- Meeting: "Product 1 — weekly product sync", Tue 2026-10-06, 30 min. The PM (Person1) facilitated and kept the notes.
- Source: transcript pasted in chat (the excerpt below is the whole meeting). No meeting-tool or calendar lookup for this run.
- Team roster (as in `team.members`): Person1 — Product Manager · Person2 — Product Designer · Person3 — Data Analyst · Person4 — Backend Tech Lead · Person5 — Frontend Engineer.
- `user.language`: en for this fixture. The judge scores rigor, not wording — a run in another language is scored the same way.

Pre-answered skill questions (automated run): calendar enrichment — no · meeting type — accept the skill's classification · format — Structured MoM · publishing — keep in chat, no Confluence write.

## Transcript (pasted)

```text
[00:00] Person1: Morning, everyone. Three things today: a quick status, the delivery-cost problem in checkout, and next steps. I'll keep the notes.
[00:01] Person5: Status from my side: the search-filter fix went to 100% of users on Monday. No new errors in the logs so far.
[00:01] Person1: Great, then I'm closing that item. Person3, you have the checkout numbers?
[00:02] Person3: Yes. Over the last four weeks, September 7 to October 4, 41% of sessions that reach the delivery step leave checkout there.
[00:03] Person3: In the exit survey for the same period, "unexpected delivery cost" is the top reason, 27% of answers.
[00:03] Person2: That matches the usability sessions. People see the delivery price only on step three, and then they bounce.
[00:04] Person1: So the problem is that buyers learn the delivery cost too late. What are our options?
[00:05] Person2: Show an estimated delivery cost on the product page, right under the price. "Delivery from X", based on the buyer's city.
[00:06] Person4: Alternative: we reorder checkout so the delivery step comes first. No new estimate logic, we reuse the existing calculation.
[00:07] Person3: But then buyers still find out only after they've committed to checkout. The decision to buy happens on the product page.
[00:07] Person5: Also, checkout is frozen for the payment-provider migration until mid-November. Any reorder collides with that.
[00:08] Person4: Fair. I withdraw it. Reordering checkout doesn't fix the timing, and it's blocked anyway.
[00:09] Person1: Okay, the reorder is off the table. Now the product-page estimate: can we calculate it for every seller?
[00:09] Person4: Not for everyone. Sellers with custom delivery rates enter them as free text. We can only calculate it for sellers on the integrated carriers.
[00:10] Person3: Integrated carriers cover about 70% of orders over the same four weeks. That's enough to see an effect.
[00:11] Person1: Do we ship it straight away or test it?
[00:11] Person3: Test. If the estimate shows a higher price than people expect, add-to-cart on the product page could drop. We need to see both sides.
[00:12] Person1: Agreed. So the decision: we show a delivery-cost estimate on the product page, for integrated-carrier sellers only, as a 50/50 A/B test.
[00:12] Person1: Primary metric is checkout completion from the delivery step; product-page add-to-cart rate is the guardrail. Any objections?
[00:13] Person2: None.
[00:13] Person3: Agreed.
[00:13] Person4: None from me.
[00:13] Person5: Fine by me.
[00:14] Person2: Side idea: we could also show the delivery date next to the cost.
[00:14] Person1: Good one, but not in this test. I'm parking it so we don't mix two changes in one experiment.
[00:15] Person4: One risk. I don't know if the carrier tariff API can take a call on every product-page view. If it can't, we need a cache, and that's probably an extra sprint.
[00:16] Person1: Then that's the first thing to find out. Person4, can you check the tariff API limits?
[00:16] Person4: Person5 and I can look at it together.
[00:17] Person1: I need one name on it, otherwise nobody owns it.
[00:17] Person4: Me, then. I'll confirm per-city support and the rate limits with the carrier-integration owners by Friday, October 9.
[00:18] Person1: Thanks. Person3, what do you need before we can size the test?
[00:18] Person3: I'll split the delivery-step drop-off by carrier type, integrated versus custom rates, for the same four weeks. I'll post it in the team channel by Thursday, October 8.
[00:19] Person1: Person2, mockups?
[00:20] Person2: I'll prepare the product-page mockups for the estimate line: a logged-in buyer with a saved address, plus a placeholder for guests. By Monday, October 12.
[00:21] Person2: Which brings up guests. What city do we use for someone with no saved address?
[00:21] Person3: IP-based city could work, but it's often wrong on mobile networks.
[00:22] Person5: Or we ask for the city in a small field on the product page.
[00:22] Person4: Or we default to the most frequent delivery city and label it clearly as an estimate.
[00:23] Person1: I don't want to guess this today. Let's leave it open and come back to it when we have the mockups.
[00:24] Person5: For tracking, I'll write the analytics event spec: estimate shown, estimate expanded, delivery step reached. Person3 reviews it. Done by Wednesday, October 14.
[00:24] Person3: Works for me, I'll review whatever you send.
[00:25] Person1: And I'll write the A/B test requirements and link them to epic PROJ-1234 by Thursday, October 15.
[00:26] Person1: Tentative launch date for the test is October 26, but that depends on Person4's answer about the API.
[00:27] Person4: If we need the cache, October 26 won't hold. I'll say so on Friday together with the API answer.
[00:28] Person1: Understood. That's everything on my list. Anything I missed?
[00:28] Person2: No.
[00:29] Person5: Nothing from me.
[00:29] Person1: Thanks, everyone.
```

Expected: a Structured MoM in which every decision carries its rationale and any alternative that was rejected (with the reason); ARCV action items — numbered, exactly one owner each, an active verb and a date; open questions kept open, with no invented owner; ideas that were parked and dates that are only tentative kept out of Decisions; nothing the transcript does not say; the type-specific section for the meeting type; and a chain offer for the follow-up work.
