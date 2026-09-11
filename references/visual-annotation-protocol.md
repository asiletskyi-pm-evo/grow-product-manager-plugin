# visual-annotation-protocol.md

> Shared reference. "Screenshot with an arrow" — how to obtain a screenshot of existing UI, annotate it with numbered markers tied to requirement numbers, and attach it to the artifact. Born from stakeholder feedback: requirements and tasks describing UI changes are much faster to analyze when the reader can SEE where each change lands. Consumers: `requirements-creator` (Requirements visualization sub-step), `task-creator` (Design/FE task attachments), `write-concept` ("What Changes for Users"), `diagram-prototyper` (standalone `annotate` mode).

## Core idea: the screenshot is a visual index of requirements

An annotated screenshot is NOT an illustration. Each numbered marker on the image corresponds to a numbered row in the functional-requirements table (or a numbered change in the concept). The reader looks at marker (2), finds row 2 in the legend, and knows exactly what changes where.

Every annotated screenshot ships with a **legend table** directly below it:

| Marker | Requirement | What changes |
|--------|-------------|--------------|
| 1 | FR-3 | Primary action button moves above the details block |
| 2 | FR-5 | Counter badge added next to the title |

## When to offer annotation

Offer (do not force) an annotated screenshot when the artifact describes changes to **existing UI**: "change X on screen Y", modifications of current flows, A/B variants of an existing page. Skip for brand-new screens with no current state (route those to `diagram-prototyper` wireframes or `design-bridge` prototypes instead).

## Step V-1 — Obtain the screenshot (source priority)

0. **Walkthrough pack**: if `~/.grow-pm/walkthroughs/*/steps.yaml` has a run for this flow, use its `steps/NN.png` — already verified against the intent, already local (`app-drive-protocol.md` §7).
1. **User-provided** (fastest): the user pastes or uploads a screenshot. Use it as-is.
2. **Figma**: if a Figma link to the current design exists in context (e.g. requirements-creator Step 1c found it) — `get_screenshot` via Figma MCP for the specific frame.
3. **Live product via browser**: navigate to the page (Claude in Chrome / browser fallback per `references/integration-strategy.md`) and capture the current state. Ask the user for the exact URL and state (logged in / specific product page) before capturing.

If none is available — ask the user via AskUserQuestion which source to use, offering all three. If the user declines annotation — proceed without it; never block the artifact.

## Step V-2 — Plan the annotations

1. List the requirements/changes that are visible on this screen (not every requirement is visual).
2. Assign marker numbers = requirement numbers. If requirement numbering does not exist yet (concept stage), number the changes sequentially and keep that numbering in the artifact text.
3. For each marker, decide the element it points to and the annotation type: **marker circle** (default), **arrow** (when pointing into dense UI), **box** (when an area, not a point, changes).

## Step V-3 — Render (Python + Pillow, fully local)

Screenshots of the product are internal data — render locally, never send to external services (`references/data-policy.md`). Write a small Python script with Pillow on the fly:

- **Marker circles:** filled circle, white bold number centered; diameter ≈ 3.5% of image width (min 28 px); accent color `#E53E3E` (red), white 2 px outer stroke for contrast on any background.
- **Arrows:** 3 px line + solid triangular head, same red; start at the marker circle edge, end at the target element.
- **Boxes:** 3 px red rectangle, corner radius 6 px, NO fill (never obscure the UI); the marker circle sits on the box's top-left corner.
- **Labels (optional):** short text (≤ 3 words) in a white rounded chip with a thin gray border next to the marker — only when the legend alone is not enough.
- Determine coordinates from the image (vision). Save as PNG, same resolution as the source — never downscale.

Practical notes: load a TrueType font (`DejaVuSans-Bold.ttf` ships with Pillow on most systems) — the default bitmap font is too small; draw the white stroke as a slightly larger circle underneath the red one.

## Step V-4 — Preview cycle (mandatory)

Show the annotated image to the user BEFORE attaching anywhere:

> "Here is the annotated screenshot — check that each marker points to the right element. Say e.g. 'move marker 2 to the left, onto the price' and I'll re-render."

Vision-placed coordinates can miss on dense UI; iterate until the user confirms. Only a confirmed image proceeds to storage/attachment.

## Step V-5 — Store locally

Annotated screenshots live **in the project repository/folder**, not in `~/.grow-pm/`:

- Path: `product.annotations_path` from `local-context.md` if set; else the first `product.repositories` entry + `/annotations/`; else `./annotations/` in the current project folder.
- Naming: `{feature-code}-screen-{N}.png` (e.g. `PROJ-1234.3-screen-1.png`); concept stage without a feature code: `{slug}-screen-{N}.png`.

## Step V-6 — Attach to the artifact

**The Atlassian MCP has NO attachment-upload tools** (verified 2026-07-29 against the full Rovo MCP tool list). Chain, in order:

**1. Atlassian REST API via curl (primary).** Requires a configured API token — see Token setup below. The runtime (Claude Code / Cowork on the user's machine) has network access:

```bash
# Confluence: attach to a page
curl -sS -X POST \
  -H "Authorization: Basic $(printf '%s:%s' "$ATLASSIAN_EMAIL" "$ATLASSIAN_API_TOKEN" | base64)" \
  -H "X-Atlassian-Token: nocheck" \
  -F "file=@PROJ-1234.3-screen-1.png" \
  "https://{site}/wiki/rest/api/content/{pageId}/child/attachment"

# Jira: attach to an issue
curl -sS -X POST \
  -H "Authorization: Basic $(printf '%s:%s' "$ATLASSIAN_EMAIL" "$ATLASSIAN_API_TOKEN" | base64)" \
  -H "X-Atlassian-Token: nocheck" \
  -F "file=@PROJ-1234.3-screen-1.png" \
  "https://{site}/rest/api/3/issue/{issueKey}/attachments"
```

After a successful Confluence upload, embed the image in the page body via `updateConfluencePage` using the attachment/media id **from the REST response** (media nodes only reference existing ids — never invent one). In Jira, reference the attachment by filename (`!PROJ-1234.3-screen-1.png!` in wiki-markup contexts) or leave it in the attachments panel with the legend in the description.

**2. Browser upload (fallback):** open the page/issue in the browser and attach through the UI.

**3. Manual (last resort):** hand the PNG files to the user with a one-line instruction and leave a placeholder in the document: `[Attach: PROJ-1234.3-screen-1.png — annotated current state]`.

Whichever path attached the image, the legend table always goes into the artifact text itself.

### Token setup (one-time, via plugin-configurator)

- `local-context.md` stores the **site URL, account email, and the NAME of the env variable** — never the token value itself:

  ```markdown
  #### Attachments (REST API)
  - atlassian_site: https://example.atlassian.net
  - atlassian_email: user@example.com
  - api_token_env: ATLASSIAN_API_TOKEN
  ```

- The token value lives in the environment (shell profile / keychain-backed export). Created at https://id.atlassian.com/manage-profile/security/api-tokens.
- Verification after setup: a GET to `/wiki/rest/api/space?limit=1` returning 200 confirms the token works.
- If the env variable is missing at attach time — say so, offer the browser fallback, and point to `plugin-configurator` for setup. Never ask the user to paste the token into the chat.

## Failure modes

| Situation | Behavior |
|-----------|----------|
| No screenshot source available | Proceed without annotation; note it in the artifact |
| Vision coordinates repeatedly wrong | After 3 failed preview iterations, offer the box style (more forgiving) or manual cropping by the user |
| REST upload 401/403 | Token invalid/expired — report, fall back to browser; suggest re-running token setup |
| Image > 10 MB | Re-encode PNG (optipng/quality) — never downscale below source resolution unless the user agrees |
