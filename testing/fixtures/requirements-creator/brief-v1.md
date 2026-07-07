<!-- Output-eval fixture (input brief) for requirements-creator. Feed as the user request; score the resulting requirements doc against the requirements-creator rubric in testing/output-evals.md. Gold reference: skills/requirements-creator/references/examples/feature-spec-example-v1.md. Generic, no org data. -->

# Input brief

Write requirements for a **"recently viewed products" strip** (Phase 1 MVP), to run as an **A/B test**.

Context the PM gives:
- Show up to 10 recently viewed products in a horizontal strip on the home page and product pages, for logged-in buyers.
- Goal: increase return-to-purchase without hurting checkout conversion.
- Approach: A/B, 50/50, logged-in only.
- Needs to be implementable by FE/BE without guessing.

Expected: functional requirements, Given/When/Then acceptance criteria, an A/B decision rule (ship/iterate/kill), primary + guardrail metrics, analytics events, and explicit out-of-scope.
