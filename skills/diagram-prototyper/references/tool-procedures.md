# Tool procedures — Step 3b, Steps 6a2–6f, Steps 8b–8f

> Part of `diagram-prototyper`. Loaded on demand: the infographic style table when the visualization type is Infographic (Step 3b), the per-tool generation runs when the selected tool is not Mermaid (Steps 6a2–6f), and the per-destination publishing and export steps once the user picks where to save (Steps 8b–8f). Mermaid generation (6a), the quality check (6g), presenting the result (Step 7) and the publishing choice (8a) stay in SKILL.md.

## Step 3b — Infographic style selection (for infographics only)

If the user chose "Infographic" in Step 1, ask for the visual style via AskUserQuestion:

> "What style should the infographic have?"

| Style | When to recommend | Description |
|-------|------------------|-------------|
| **Data-driven** | Metrics, KPIs, A/B test results, analytics | Charts, numbers, progress bars, comparisons. Focus on quantitative data storytelling |
| **Process / timeline** | Onboarding flows, roadmaps, release timelines, step-by-step guides | Sequential steps, numbered stages, timeline with milestones. Focus on progression |
| **Comparison** | Feature comparison, competitive analysis, before/after, plan tiers | Side-by-side layouts, comparison tables, pros/cons. Focus on evaluating options |
| **Informational / educational** | Product overviews, how-it-works explanations, market research summaries | Icons, illustrations, text blocks, visual hierarchy. Focus on communicating a concept |
| **Statistical / report** | Quarterly reports, market size, survey results | Pie charts, bar charts, stat callouts, percentages. Focus on presenting research findings |

Provide a recommendation based on context:
- Analytics data, metrics review → recommend Data-driven
- User journey, onboarding, roadmap → recommend Process / timeline
- Competitive research, feature evaluation → recommend Comparison
- Concept explanation, product overview → recommend Informational / educational
- Research results, survey data, quarterly numbers → recommend Statistical / report

## Step 6 — Generation: HTML/CSS and external tools (6a2–6f)

**6a2. HTML/CSS (built-in) — for infographics:**

1. Generate a single self-contained HTML file with:
   - Inline CSS for styling (no external dependencies)
   - SVG elements for charts and icons (or use simple CSS shapes)
   - Responsive layout that looks good at the target dimensions
   - Print-friendly styles (if the infographic is for A4/PDF)
2. **HTML structure guidelines for infographics:**
   - Use a fixed-width container (e.g., `max-width: 800px; margin: 0 auto`)
   - Structure with semantic sections: header (title + subtitle), body sections, footer
   - Use CSS Grid or Flexbox for layout
   - For charts: use inline SVG with `<rect>`, `<circle>`, `<text>`, `<path>` elements — no external charting libraries required
   - For icons: use simple SVG icons or Unicode symbols (e.g., ✓, ✗, ▲, ▼, ●)
   - For progress bars: use simple `<div>` elements with percentage-based widths
   - Include `@media print` styles for clean printing
3. **Color and typography:**
   - Define a color palette at the top of the `<style>` block as CSS variables (`--color-primary`, `--color-secondary`, `--color-accent`, `--color-bg`, `--color-text`)
   - Use system fonts or Google Fonts (import via `<link>`)
   - Minimum font size: 12px for body, 14px for labels, 24px+ for headline stats
4. Validate the HTML (check for unclosed tags, valid CSS)
5. Save as `.html` file in the user's workspace
6. Present the result to the user (the HTML file will render in the chat)
7. Skip to Step 7 (no LLM quality loop needed)

**6b. Google Gemini (via browser):**

1. Open browser → navigate to `gemini.google.com`
2. Ensure the strongest available model is selected
3. Activate **Nano Banana mode** for image generation (if applicable, enable the canvas/image generation feature)
4. Paste the constructed prompt
5. Wait for the result to generate
6. Take a screenshot of the result
7. Proceed to Step 6g (Quality check)

**6c. ChatGPT (via browser):**

1. Open browser → navigate to `chatgpt.com`
2. Ensure the strongest available model is selected (GPT-4o or newer)
3. If image generation is needed — use DALL-E or the canvas mode
4. Paste the constructed prompt
5. Wait for the result to generate
6. Take a screenshot or download the generated image
7. Proceed to Step 6g (Quality check)

**6d. NotebookLM (via browser):**

1. Open browser → navigate to `notebooklm.google.com`
2. Create a new notebook or use an existing one
3. Add the context as a source (paste text or provide document)
4. For **Mind Map**: use the Mind Map feature to generate a visual map
5. For **Presentation**: use the Presentation feature to generate slides
6. Take a screenshot of the result
7. Proceed to Step 6g (Quality check)

**6e. Figma (via MCP or browser):**

1. If Figma MCP is available — use `create_new_file` to create a new Figma file, then use Figma MCP tools to build the prototype
2. If Figma MCP is not available — open browser → navigate to `figma.com`, create a new file, and build the prototype using the browser UI
3. Take a screenshot of the result using `get_screenshot` (MCP) or browser screenshot
4. Proceed to Step 6g (Quality check)

**6f. Draw.io:**

**Priority: local XML generation**
1. Generate the diagram as Draw.io XML format based on the prompt
2. Validate the XML structure
3. Save as `.drawio` file in the user's workspace
4. Provide the file to the user

**Fallback: browser**
If the diagram is too complex for XML generation or the user requests browser mode:
1. Open browser → navigate to `app.diagrams.net`
2. Create a new diagram
3. Build the diagram using the browser UI
4. Export as image (PNG/SVG)
5. Proceed to Step 6g (Quality check)

For Draw.io XML — offer to also export as PNG/SVG for preview.

## Step 8 — Publishing: destinations and export (8b–8f)

**8b. Confluence publishing:**

- Ask which page to attach the image to (existing page or create new)
- Upload the image as an attachment
- Add inline image with caption using Confluence markup
- If publishing alongside a concept or requirements page — offer to embed on that page

**8c. Notion publishing:**

- Ask which page or database to add the image to
- Upload and embed the image block
- Add caption

**8d. Figma publishing:**

- If the artifact was already created in Figma — provide the link
- If created elsewhere — upload the image to the user's Figma workspace as a new file or frame

**8e. Local file:**

- Save the file to the user's workspace folder
- Provide a download link
- Format: PNG for raster images, SVG for vector diagrams, .drawio for Draw.io files, .mermaid for Mermaid code, .html for infographics

**8f. Additional export for infographics:**

After saving the primary format, offer additional export options:
> "Would you also like to export this infographic as a different format?"

| Format | When useful |
|--------|------------|
| **PNG** | For embedding in presentations, Confluence pages, or sharing via chat |
| **PDF** | For printing or formal document attachments |
| **HTML** | For interactive viewing in a browser (if not already HTML) |

If the user selects PNG or PDF — use browser rendering or a conversion tool to generate from HTML.
