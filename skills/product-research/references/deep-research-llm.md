# Deep Research via ChatGPT / Gemini — Step 2

> Part of `product-research`. Loaded on demand in Step 2 when the user enabled ChatGPT and/or Gemini Deep Research in Step 1. The Step 1 question about each LLM, the `deep-research-llm` source marker and the Sources-section labelling stay in SKILL.md.

## Deep Research via ChatGPT (if confirmed by user in Step 1)

1. Open ChatGPT via browser (`navigate` to `https://chatgpt.com`)
2. Select the strongest model available in the user's interface (e.g., GPT-4o, o3)
3. Activate **Deep Research** mode if available in the interface
4. Compose a detailed research prompt based on the agreed scope from Step 1 — include specific questions, competitors, market segments, and what data points are needed.
   **`data-policy.md` applies here:** the prompt goes to a third-party LLM, so it carries **public information only**. Step 1's scope may include internal documents, metrics and hypotheses — generalize them ("a marketplace of our size" rather than the figure) or leave them out. Never paste Tableau numbers, internal URLs, or unreleased plans.
5. Submit the prompt and wait for the full response
6. Read and extract the findings using `read_page` / `get_page_text`
7. Use the extracted data as additional context — cross-reference with other sources, note any contradictions or unique insights

## Deep Research via Google Gemini (if confirmed by user in Step 1)

1. Open Gemini via browser (`navigate` to `https://gemini.google.com`)
2. Select the strongest model available in the user's interface (e.g., Gemini 2.5 Pro)
3. Activate **Deep Research** mode if available in the interface
4. Compose a detailed research prompt — can be the same as for ChatGPT, or adjusted based on ChatGPT's results if it was run first (to fill gaps or verify claims). **Same `data-policy.md` rule: public information only** — generalize anything internal from Step 1.
5. Submit the prompt and wait for the full response
6. Read and extract the findings using `read_page` / `get_page_text`
7. Use the extracted data as additional context — cross-reference with ChatGPT results (if both are used) and other sources

## If both ChatGPT and Gemini are used
- Run both Deep Research sessions
- Cross-reference findings — note where both LLMs agree (higher confidence) and where they diverge (flag for verification)
- Present a unified view in the research output, citing which LLM provided each insight

## Important guidelines for LLM-sourced data
- Always cross-verify claims from LLMs against web search or internal data
- Mark LLM-sourced insights in the final output (e.g., "Source: ChatGPT Deep Research" or "Source: Gemini Deep Research")
- If LLMs provide conflicting information, present both perspectives with a note
- Do NOT treat LLM output as primary source — use it to enrich and deepen the analysis
