# Prompt construction — Step 5 (5a–5d)

> Part of `diagram-prototyper`. Loaded on demand every time Step 5 runs — after the tool is chosen in Step 4 and before generation in Step 6. Context gathering, notation / fidelity / style / tool selection, generation, the quality check and publishing stay in SKILL.md.

## Step 5 — Prompt construction

Based on all gathered context, construct a detailed prompt for the selected tool. The prompt must include:

**5a. Core elements for every prompt:**

1. **Goal** — what is being visualized and why (concept pitch, technical flow, user journey, etc.)
2. **Type** — diagram / prototype / mind map / infographic / presentation
3. **Notation** (for diagrams) — flowchart / BPMN 2.0 / simple schema
4. **Fidelity** (for prototypes) — lo-fi / mid-fi
5. **Style** (for infographics) — data-driven / process / comparison / informational / statistical
6. **Content** — the actual information to visualize (process steps, screen elements, nodes, data points, etc.)
7. **Text locale** — language for all labels and text on the image
8. **Visual style** — clean, professional, minimalistic. Consistent color scheme. High contrast for readability

**5b. Additional elements based on type:**

**For diagrams:**
- List all actors, steps, decision points, branches
- Describe start and end conditions
- For BPMN: specify pools, lanes, events, gateways
- For flowcharts: specify decision diamonds, process boxes, connectors

**For prototypes:**
- Platform (Web / iOS / Android)
- Screen dimensions guidance (e.g., "desktop viewport 1440px wide" or "mobile 390px wide")
- UI elements to include (navigation, buttons, forms, cards, modals, etc.)
- Placeholder content or real content
- For mid-fi: specify basic styling (light/dark, brand colors if known)

**For mind maps:**
- Central topic and branch hierarchy
- Level of depth (2-3 levels typical)
- Key relationships between nodes

**For infographics:**
- **Main headline / title** — the key takeaway or topic
- **Data points and metrics** — specific numbers, percentages, KPIs to display
- **Visual hierarchy** — what should be the most prominent element, secondary elements, supporting details
- **Section structure** — logical sections of the infographic (e.g., "Problem → Solution → Results" or "Before → After")
- **Chart types** (for data-driven/statistical) — bar charts, pie charts, donut charts, progress bars, stat callouts, sparklines
- **Icons and visual elements** — use simple geometric icons or emoji-style markers; describe each icon's meaning
- **Color scheme** — suggest 2-3 primary colors that match the topic or brand; use color to encode meaning (e.g., green = positive, red = negative)
- **Dimensions / format** — vertical scroll (800px wide), A4-like (portrait), slide-sized (16:9), social media format (1080x1080)
- **Footer** — source attribution, date, product name if applicable; since v3.8.0 each number's evidence class goes first in its attribution (`measured` / `observed` / `reported` / `external`, `references/pm-mental-model.md` §4 — e.g. `Source: measured · checkout funnel, 12mo rolling`), as the upstream labelled it, never upgraded; a figure the user typed or pasted here is `reported` (who) — this skill runs no data gate, so `measured` comes only with an upstream skill's label. Internal source names appear only for an internal audience and never in a prompt to an external LLM (5d) — the class stays in every case. `simulated` and `assumed` figures carry their label on the figure itself, not only in the footer
- **Style-specific guidance:**
  - Data-driven: emphasize numbers with large font sizes, use progress bars and chart visualizations, include trend indicators (arrows up/down)
  - Process / timeline: use numbered steps or timeline dots, clear directional flow (top-to-bottom or left-to-right), connector lines between stages
  - Comparison: use columns or side-by-side blocks, checkmarks/crosses for feature presence, consistent structure across compared items
  - Informational: balance text and visuals, use icon+text pairs, group related information in visual blocks
  - Statistical: lead with the most impactful stat, use chart diversity (don't repeat the same chart type), include context for numbers (benchmarks, periods)

**For presentations:**
- Number of slides
- Key messages per slide
- Visual style (corporate, creative, minimal)

**5c. Quality instructions in the prompt:**

Always include:
- "Use clean, professional visual style"
- "Ensure all text is legible and in [specified locale]"
- "Use consistent color coding for different types of elements"
- "White or light background for readability"
- "No decorative elements that don't convey information"

**Additional quality instructions for infographics:**
- "Maintain clear visual hierarchy — the most important data/message should be the most visually prominent"
- "Use whitespace generously to avoid visual clutter"
- "Ensure all data visualizations are accurately proportioned (e.g., bar heights match actual values)"
- "Include units and labels for all data points"
- "Use a consistent icon style throughout (all outline, all filled, or all emoji)"

**5d. Data confidentiality in prompts:**

When constructing prompts for external LLMs:
- **DO NOT include**: internal URLs, API endpoints, Tableau dashboard links, internal metric values, employee names, Jira project keys, Confluence page IDs
- **DO include**: general product descriptions, feature concepts described in abstract terms, user flow logic, UI structure descriptions
- If the user's requirements contain confidential data — generalize it before including in the prompt. Inform the user: "I've generalized some internal details for the prompt to comply with the data policy."

**Note for infographics with confidential data:** If the user wants to include internal metrics or KPIs in the infographic and the selected tool is an external LLM (Gemini/ChatGPT), warn the user and recommend switching to the **HTML/CSS (built-in)** tool, which processes data locally and does not send it externally. If the user insists on using an external tool — replace real numbers with placeholder values and note this in the output: the infographic marks them `illustrative placeholder — not data`, and a placeholder carries no evidence class (it is not a claim).
