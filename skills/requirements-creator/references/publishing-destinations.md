# Publishing destinations — Step 6 (6a–6g)

> Part of `requirements-creator`. Loaded on demand at Step 6, after the user confirms the draft in Step 5 (and reused by Analyze & Improve A8). The Step 6 heading and a one-paragraph summary stay in SKILL.md.

**6a. Ask if the user wants to save the document:**

> "Would you like to save the requirements document? If yes — which tool should I use?"

- If no — end the skill, results stay in the dialogue
- If yes — ask where:
  - **Confluence** (default)
  - **Notion**
  - **Google Doc**
  - **Other** — user specifies

**6b. Ask for location:**

- Which **space** (Confluence) / **workspace** (Notion) / **folder** (Google Drive)?
- Which **parent page/document** to nest under?
- Should the article be a **child page** of the specified location?
- Offer to search existing pages to help decide

**6c. Document title — template:**

`[Feature number] - [A/B Test type if applicable] - [Feature name]`

Rules:
- Feature number = Epic key + `.` + sequential number (e.g., PROJ-1234.3)
- If no feature number — skip this part
- Add "A/B Test" or "A/B/C Test" only if this approach was selected
- Feature name = concise description of the feature

Examples:
- `PROJ-1234.3 - A/B Test - Add wishlist button to product comparison`
- `PROJ-5678.1 - Move Buy button higher on product page`
- `PROJ-5678.1 - A/B/C Test - Promo block layout on product page`

**6d. Publishing to Confluence:**

Use Confluence-native elements:
- **Table of Contents macro** (heading levels 1-6)
- **Jira work items macro** with JQL filter: `parent = EPIC-KEY AND labels = FEATURE-CODE`, sorted by Sprint
- **Horizontal rule/divider** between sections
- **Panels** where appropriate
- **Bold**, headings H1/H2/H3, tables

Publish via Confluence MCP (`createConfluencePage`). If unavailable — follow integration fallback chain.

**6e. Publishing to Notion:**

Adapt structure to Notion elements:
- Table of Contents block
- Dividers between sections
- Toggle headings for collapsible sections where appropriate
- Tables, bold text, headings hierarchy

Publish via Notion MCP. If unavailable — follow integration fallback chain.

**6f. Publishing to Google Docs:**

Adapt structure to Google Docs:
- Table of Contents
- Horizontal lines between sections
- Tables, bold text, headings hierarchy

Follow integration fallback chain: Google Docs MCP → registry → browser.

**6g. Publishing to other destinations:**

Follow integration fallback chain for the specified tool. Adapt format to platform capabilities.

As a last resort for any destination — generate a local document and provide to the user for manual publishing.
