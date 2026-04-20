# Figma Playbook

Practical recipes for how `design-bridge` works with the Figma MCP.

## Auth & permissions

- Authenticate check: `whoami` (tool: `mcp__figma__whoami`).
- Response includes: `email`, `handle`, `plans[]` (team keys, seat).
- Seat levels:
  - **View** — read-only: `get_screenshot`, `get_design_context`, `get_metadata`, `get_libraries`, `search_design_system`, `get_variable_defs`. No editing.
  - **Full / Editor** — all of the above plus `use_figma` (create frames), `add_code_connect_map`, `create_new_file`.
- If your seat in the brand workspace is **View**, hi-fi prototypes require either a seat upgrade to Full or doing the work in your personal "My drafts" space.

## Finding a `fileKey`

**The Figma MCP does not expose `list_team_files`.** Every tool requires a known `fileKey`.

Ways to get a `fileKey`:

1. **Manual** (main path): open the file in a browser → URL looks like `https://www.figma.com/design/<FILE_KEY>/<file-name>` or `/file/<FILE_KEY>/` → copy the segment after `/design/` or `/file/`.
2. **Web search** — works only if the file is public in the Figma Community (most private DS files won't qualify).
3. **Ask a human** — a designer or design lead.

Once obtained, add it to `local-context.md` under the active product's Design System section:
```
- **Design System file key:** <FILE_KEY>
- **Last DS sync:** YYYY-MM-DD
```

## Common patterns

### Sync brand tokens from the DS

```
# Step 1: find libraries
get_libraries(fileKey=DS_FILE_KEY) → returns list of libraries with library_key
# Step 2: search colors / typography
search_design_system(query="colors", fileKey=DS_FILE_KEY,
                     includeLibraryKeys=[DS_LIB_KEY],
                     includeVariables=true, includeStyles=true)
# Step 3: get value defs
get_variable_defs(fileKey=DS_FILE_KEY, variableIds=[...])
```
Compare with the DS yaml at `product.design_system_spec` → status `confirmed` if values match; `placeholder` if drift → open a PR-style update against the yaml.

### Embed a screenshot in a deck

```
get_design_context(nodeId=<node>, fileKey=<key>)  → TEXT context (layer names, variants)
get_screenshot(nodeId=<node>, fileKey=<key>)      → PNG, 2x resolution
→ store in temp, path passed to pptx add_picture()
```

Recommendation: alongside `get_screenshot`, always call `get_design_context` for speaker-notes generation (layer names are great context for what's on the slide).

### Concept → Prototype (hi-fi)

Full seat only.
```
use_figma(command="create_frame",
          fileKey=<target_file>,
          content=<generated spec>)
```
If seat = View → skip and propose a mid-fi HTML prototype instead (fallback via `diagram-prototyper`).

### Handoff context

```
get_metadata(fileKey=<key>, nodeId=<frame>)     → component names, variables used, styles
get_variable_defs(fileKey=<key>, variableIds)   → exact tokens
```

Pipe the output into `design:design-handoff` as structured context.

## Policy nuances

- **Private files**: embed screenshots only in internal decks. Never publish to external-facing deliverables.
- **Competitor decks**: never embed Figma frames from competitive research, even if a link is provided.
- **Permission errors (403/404)** → graceful fallback placeholder: `[Design: see Figma {{url}}]` + warning in the outline footer.
- **Rate limits**: cache `get_screenshot` results in temp; do not call twice for the same `nodeId`.

## Brand DS configuration

Brand-specific values live in `local-context.md` (not in this repo). The expected schema:

- `product.figma.ds_file_key` — the Figma `fileKey` of the brand Design System file
- `product.figma.library_key` — obtained via `get_libraries(fileKey)` on first sync
- `product.brand.primary`, `product.brand.dark`, `product.brand.font_primary`, `product.brand.font_display` — brand tokens used when the DS yaml is unavailable or missing fields

See `local-context.example.md` → Design System section for the full schema.

## Known limitations

- `use_figma` does not support every property setter; check the docs for each call.
- `get_screenshot` sometimes returns low-res output for large frames → prefer calling it on compact nodes rather than an entire page.
- Components with variants need a `variant` prop — if unset, Figma returns the default.
- Non-Latin characters: verify that the brand font covers the target language's glyph set (e.g., Cyrillic, Greek, CJK). If the font falls back to a system default, screenshots may not match the design.
