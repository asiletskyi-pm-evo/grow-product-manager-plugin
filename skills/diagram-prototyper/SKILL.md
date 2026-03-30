---
name: diagram-prototyper
version: 0.6.0
description: Create diagrams, flowcharts, BPMN processes, and UI prototypes to visualize product concepts and hypotheses. Use when the user asks to "create a diagram", "draw a flowchart", "visualize this process", "make a prototype", "BPMN diagram", "wireframe", "mockup", or when another skill suggests visualizing a concept. Supports generation via Gemini, ChatGPT, NotebookLM, Figma, Draw.io, and built-in Mermaid.
---

# Diagram & Prototype Creator

Create diagrams, flowcharts, BPMN processes, mind maps, and UI prototypes to improve understanding of product concepts and hypotheses. The skill acts as a visual communication assistant — it gathers context, selects the right tool, generates the visual artifact, validates quality, and publishes the result.

## Integration prerequisite

Before starting, read and follow the integration fallback chain in `references/integration-strategy.md`. For this skill, the typical external products needed are:

- **Figma** — for creating and publishing design prototypes and diagrams
- **Confluence** — for publishing diagrams as images on documentation pages
- **Notion** — alternative publishing destination
- **Claude in Chrome** — for interacting with external LLMs (Gemini, ChatGPT, NotebookLM) and Draw.io via browser
- **Web** — always available via WebSearch

Before gathering any data, also read and comply with `references/data-policy.md`. Confidential data must NOT be passed to external LLMs in a way that violates the policy. When constructing prompts for external LLMs, **exclude** any confidential metrics, internal URLs, or sensitive business data — describe the concept in general terms.

## Local context prerequisite

**Before starting, follow `references/local-context-protocol.md` (Step 0).** Read `local-context.md`, select the active product, and load all product-specific context. If the file doesn't exist — redirect to Plugin Configurator for initial setup.

Key context used by this skill:
- `product.name`, `product.platforms` — understand the product scope for prototypes
- `product.confluence_space` — for publishing diagrams to Confluence
- `user.language` — for text localization on diagrams and prototypes

---

## Workflow

### Step 1 — Context gathering

**1a. Determine the context source:**

- **Transition from another skill** (write-concept, brainstorm-features, requirements-creator, product-research, product-analysis) → context was passed from the previous skill. Summarize the passed context and confirm with the user what exactly needs to be visualized
- **Standalone launch** → gather context from scratch

**1b. Clarify the visualization goal — ask via AskUserQuestion:**

> "What would you like to visualize?"

| Type | When to use | Examples |
|------|------------|---------|
| **Diagram** | Processes, logic, flows, architecture | User flow, order lifecycle, system interaction, decision tree |
| **Prototype** | UI screens, interface layouts, components | Product page layout, new feature mockup, checkout flow screens |
| **Mind Map** | Concept exploration, idea mapping, brainstorming results | Feature decomposition, stakeholder map, competitive landscape |
| **Presentation** | Visual summary of a concept or research | Concept pitch slides, research highlights |

**1c. Gather detailed requirements:**

Based on the visualization type, ask targeted questions:

**For diagrams:**
- What process or flow needs to be visualized?
- Who are the actors (users, systems, services)?
- What are the start and end conditions?
- Are there decision points or branches?
- What level of detail is needed?

**For prototypes:**
- Which screen(s) or feature area?
- Which platform? (Web, iOS, Android — from `product.platforms`)
- What elements should be present? (buttons, forms, lists, navigation, etc.)
- Are there existing designs in Figma to reference?

**For mind maps:**
- What is the central topic?
- What are the main branches?
- What level of depth is needed?

**For presentations:**
- What concept or research to visualize?
- How many slides approximately?
- What is the target audience?

**1d. Ask about text localization:**

> "What language should be used for text labels on the diagram/prototype?"

- Use `user.language` from `local-context.md` as default suggestion
- Allow any language the user specifies
- Store the chosen locale for prompt construction

### Step 2 — Diagram type selection (for diagrams only)

If the user chose "Diagram" in Step 1, ask for the notation type via AskUserQuestion:

> "Which diagram notation would you like to use?"

| Notation | When to recommend | Description |
|----------|------------------|-------------|
| **Flowchart** | General processes, user flows, decision trees | Standard boxes, diamonds, arrows. Simplest and most universal |
| **BPMN 2.0** | Business processes with lanes, events, gateways | Professional process notation with pools, lanes, events, gateways. Best for cross-team processes |
| **Simple schema** | Architecture, data flow, system interaction | Free-form boxes and arrows, no strict notation rules. Best for technical overviews |

Provide a recommendation based on context:
- User flow or decision logic → recommend Flowchart
- Cross-team or cross-system process → recommend BPMN 2.0
- Architecture or data overview → recommend Simple schema

### Step 3 — Fidelity selection (for prototypes only)

If the user chose "Prototype" in Step 1, ask for the fidelity level via AskUserQuestion:

> "What level of detail should the prototype have?"

| Fidelity | When to recommend | Description |
|----------|------------------|-------------|
| **Lo-fi wireframe** | Early concept validation, quick iteration | Simple block layouts, placeholder text, no styling. Focus on structure and flow |
| **Mid-fi mockup** | Stakeholder presentations, concept approval | Schematic screens with real text, buttons, and basic UI patterns. Not pixel-perfect, but recognizable |

Provide a recommendation based on context:
- Concept phase, brainstorming → recommend Lo-fi
- Requirements phase, stakeholder review → recommend Mid-fi

### Step 4 — Tool selection

Ask the user which tool to use via AskUserQuestion:

> "Which tool should I use to create this?"

Present options based on the visualization type. Not all tools are suitable for all types:

| Tool | Best for | How it works |
|------|----------|-------------|
| **Mermaid (built-in)** | Flowcharts, BPMN, simple diagrams | Generated locally by the skill as Mermaid code → rendered as SVG/image. No external LLM needed. Fastest option |
| **Google Gemini** | Prototypes, complex diagrams, mind maps | Browser → gemini.google.com (Nano Banana mode for image generation). Uses the strongest available model |
| **ChatGPT** | Prototypes, diagrams, mind maps | Browser → chatgpt.com. Uses the strongest available model (GPT-4o or newer) |
| **NotebookLM** | Mind maps, presentations | Browser → notebooklm.google.com. Uses Presentations and Mind Map features |
| **Figma** | Prototypes, design mockups | Via Figma MCP or browser → figma.com. Best for high-fidelity prototypes |
| **Draw.io** | Flowcharts, BPMN, architecture diagrams | Priority: generate .drawio XML file locally. Fallback: browser → app.diagrams.net |

**Tool recommendation logic:**

| Visualization type | Recommended tool | Reason |
|-------------------|-----------------|--------|
| Flowchart / BPMN / simple diagram (standard) | Mermaid (built-in) | Fastest, no external dependencies |
| Complex or large diagram | Draw.io | Better control over layout and export |
| Lo-fi wireframe | Gemini or ChatGPT | Image generation with structure |
| Mid-fi mockup | Figma or Gemini | Higher fidelity capability |
| Mind map | NotebookLM or Gemini | Built-in mind map features |
| Presentation | NotebookLM | Built-in presentation generation |

Mark the recommended option with "(Recommended)" in the AskUserQuestion options.

### Step 5 — Prompt construction

Based on all gathered context, construct a detailed prompt for the selected tool. The prompt must include:

**5a. Core elements for every prompt:**

1. **Goal** — what is being visualized and why (concept pitch, technical flow, user journey, etc.)
2. **Type** — diagram / prototype / mind map / presentation
3. **Notation** (for diagrams) — flowchart / BPMN 2.0 / simple schema
4. **Fidelity** (for prototypes) — lo-fi / mid-fi
5. **Content** — the actual information to visualize (process steps, screen elements, nodes, etc.)
6. **Text locale** — language for all labels and text on the image
7. **Visual style** — clean, professional, minimalistic. Consistent color scheme. High contrast for readability

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

**5d. Data confidentiality in prompts:**

When constructing prompts for external LLMs:
- **DO NOT include**: internal URLs, API endpoints, Tableau dashboard links, internal metric values, employee names, Jira project keys, Confluence page IDs
- **DO include**: general product descriptions, feature concepts described in abstract terms, user flow logic, UI structure descriptions
- If the user's requirements contain confidential data — generalize it before including in the prompt. Inform the user: "I've generalized some internal details for the prompt to comply with the data policy."

### Step 6 — Generation

Execute the generation based on the selected tool:

**6a. Mermaid (built-in):**

1. Generate Mermaid code based on the constructed prompt
2. Validate the Mermaid syntax (test by rendering)
3. Render as `.mermaid` file and/or `.svg` image
4. Present the result to the user in the chat
5. Skip to Step 7 (no LLM quality loop needed)

For BPMN 2.0 in Mermaid — use `flowchart` with subgraphs for lanes and styled nodes for events/gateways.

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

**6g. Quality check (for LLM-generated results):**

After receiving the result from any external tool (Gemini, ChatGPT, NotebookLM, Figma, Draw.io browser):

1. **Review the generated image** — take a screenshot and analyze it
2. **Check against requirements:**

| Check | What to verify |
|-------|---------------|
| **Content accuracy** | All required elements present? Process steps match? UI elements correct? |
| **Text correctness** | All labels in the correct locale? No truncated or garbled text? |
| **Visual quality** | Clean layout? No overlapping elements? Readable text? Consistent styling? |
| **Notation compliance** | (For BPMN/flowcharts) Correct symbols used? Proper flow direction? |
| **Completeness** | No missing branches, screens, or nodes? Start/end conditions present? |

3. **If issues found — auto-correct:**
   - Construct a follow-up prompt describing exactly what needs to be fixed
   - Send the correction to the LLM / tool
   - Re-check the result

4. **Iteration limit:**
   - Maximum **3 auto-correction iterations**
   - After iteration 3, if the result still doesn't pass quality check:

   > "I've tried to improve the result 3 times, but there are still issues: [list issues]. Would you like to: (a) Accept the current result as-is, (b) Continue iterating, (c) Switch to a different tool?"

   Ask via AskUserQuestion and proceed based on the user's choice.

### Step 7 — Present result to user

**7a. Show the result in the chat:**

- Display the generated image/diagram/prototype
- Provide a brief description of what was created
- Highlight key elements

**7b. Ask for feedback:**

> "Here is the result. Does it match your expectations? Would you like any changes?"

- If the user requests changes — apply corrections (re-enter Step 6 with updated prompt)
- If the user confirms "OK" — proceed to Step 8

### Step 8 — Publishing

**8a. Ask if the user wants to save/publish:**

> "Would you like to publish or save this? You can publish to Confluence, Notion, or Figma, or save as a local file."

Present options via AskUserQuestion:

| Destination | What happens |
|-------------|-------------|
| **Confluence** | Upload image to a Confluence page (existing or new). Add caption and context |
| **Notion** | Upload image to a Notion page (existing or new) |
| **Figma** | Upload to Figma workspace (if not already created there) |
| **Local file** | Save as PNG/SVG/drawio/mermaid in the user's workspace folder |
| **No** | End the skill, result stays in the chat |

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
- Format: PNG for raster images, SVG for vector diagrams, .drawio for Draw.io files, .mermaid for Mermaid code

### Step 9 — Skill chaining

After publishing (or if the user decided not to save), offer the next step based on context:

**If the visualization was for a concept:**
> "Would you like to continue writing requirements for this concept? I'll pass the context to the Requirements Creator skill."

**If the visualization was for requirements:**
> "Would you like to create Jira tasks for this feature? I'll pass the context to the Feature Task Creator skill."

**If standalone:**
> "Would you like to create another diagram or prototype? Or continue with a different task?"

---

## Skill Chaining — Inbound (for other skills)

**This section defines how other skills should invoke this skill.**

After completing their main workflow, the following skills should offer visualization:

| Source skill | When to offer | Suggested visualization |
|-------------|--------------|----------------------|
| **write-concept** | After concept is published | Flowchart of the main user flow, prototype of key screens |
| **brainstorm-features** | After hypotheses are scored | Mind map of feature ideas, diagrams of top hypotheses |
| **requirements-creator** | After requirements are published | BPMN of the process, prototype of UI changes |
| **product-research** | After research is published | Mind map of competitive landscape, diagram of market positioning |
| **product-analysis** | After analysis is complete | Flowchart of user funnel, diagram of metric relationships |

**Transition prompt template:**
> "Would you like to create a visual diagram or prototype for [brief description]? This can help communicate the concept more effectively."

When invoking this skill from another skill, pass:
- Full context from the parent skill (concept, requirements, research results, hypotheses)
- Suggested visualization type (diagram / prototype / mind map)
- The specific element to visualize

---

## Quality standards

- Every generated visual must be reviewed for accuracy, completeness, and readability
- Text on diagrams/prototypes must match the user's chosen locale
- Prompts for external LLMs must comply with `references/data-policy.md` — no confidential data in prompts
- Mermaid code must be syntactically valid before presenting to the user
- Draw.io XML must be structurally valid and openable in Draw.io
- BPMN 2.0 diagrams must use correct notation (events, gateways, lanes)
- Prototype fidelity must match the selected level (lo-fi or mid-fi)
- Maximum 3 auto-correction iterations before asking the user
- Always present the result to the user before publishing

## Additional Resources

- **`references/local-context-protocol.md`** — Step 0: how to read and use local-context.md (mandatory before any skill execution)
- **`references/integration-strategy.md`** — MCP → Registry → Browser fallback chain (shared across all skills)
- **`references/data-policy.md`** — data confidentiality policy: what data can and cannot be shared externally (mandatory reading before any data gathering)
- **`references/self-improvement.md`** — self-improvement protocol: how to learn from user corrections and improve skill algorithms
