# Figma Playbook

Практичні рецепти, як design-bridge працює з Figma MCP. Deep-dive див. `design-integration/03-figma-mcp-config.md`.

## Auth & permissions

- Authenticate check: `whoami` (tool: `mcp__figma__whoami`).
- Kiosk output містить: `email`, `handle`, `plans[]` (team keys, seat).
- Seat levels:
  - **View** — читання: `get_screenshot`, `get_design_context`, `get_metadata`, `get_libraries`, `search_design_system`, `get_variable_defs`. Немає редагування.
  - **Full / Editor** — усе вище + `use_figma` (створення frames), `add_code_connect_map`, `create_new_file`.
- Andrii зараз має View на Prom + UAPROM LLC, Full на My drafts.
- Для hi-fi prototype у Prom workspace → потрібна ескалація до Full seat або робота у My drafts.

## Знайти fileKey

**Figma MCP не має `list_team_files`.** Усі інструменти потребують вже відомого `fileKey`.

Шляхи отримати `fileKey`:

1. **Manual** (основний путь): відкрий файл у браузері → URL вигляду `https://www.figma.com/design/<FILE_KEY>/<file-name>` або `/file/<FILE_KEY>/` → скопіюй сегмент після `/design/` чи `/file/`.
2. **З web search** — спрацьовує тільки якщо файл публічний у Figma Community (Prom DS — приватний, не підійде).
3. **Від людини** — попроси дизайнера/дизайн-ліда.

Коли отримаєш — додай у `local-context.md`:
```
- **Design System file key:** ABC123xyz...
- **Last DS sync:** YYYY-MM-DD
```

## Поширені виклики

### Sync brand tokens з DS
```
# Step 1: знайти libraries
get_libraries(fileKey=DS_FILE_KEY) → повертає list libraries з library_key
# Step 2: шукати colors / typography
search_design_system(query="colors", fileKey=DS_FILE_KEY,
                     includeLibraryKeys=[DS_LIB_KEY],
                     includeVariables=true, includeStyles=true)
# Step 3: отримати value defs
get_variable_defs(fileKey=DS_FILE_KEY, variableIds=[...])
```
Порівняй з `02-prom-design-system-spec.yaml` → статус `confirmed` якщо match; `placeholder` якщо розходиться → підніми PR-apдейт у yaml.

### Embed screenshot у deck

```
get_design_context(nodeId=<node>, fileKey=<key>)  → TEXT контекст (layer names, variants)
get_screenshot(nodeId=<node>, fileKey=<key>)      → PNG, 2x resolution
→ store in temp, path passed to pptx add_picture()
```

Рекомендація — разом з `get_screenshot` завжди запитати `get_design_context` для speaker-notes generation (назви шарів = контекст, що на слайді).

### Concept → Prototype (hi-fi)

Тільки з Full seat.
```
use_figma(command="create_frame",
          fileKey=<target_file>,
          content=<generated spec>)
```
Якщо seat=View → пропустити, запропонувати mid-fi HTML прототип (fallback через `diagram-prototyper`).

### Handoff context

```
get_metadata(fileKey=<key>, nodeId=<frame>)     → component names, variables used, styles
get_variable_defs(fileKey=<key>, variableIds)   → точні tokens
```

Output → включаємо у `design:design-handoff` input як structured context.

## Policy nuances

- **Private files**: embed screenshots тільки у internal decks. Не публікуємо у external-facing deliverables.
- **Competitor decks**: ніколи не ембедимо Figma з конкурентних досліджень, навіть якщо є посилання.
- **Permission errors (403/404)** → graceful fallback placeholder: `[Дизайн: див. Figma {{url}}]` + warning у outline footer.
- **Rate limits**: кешуй результати `get_screenshot` у temp; не викликай двічі для того самого `nodeId`.

## Prom DS specifics

- `fileKey`: _TODO_ (див. local-context.md, потребує manual input)
- `library_key`: _TODO_ (отримується після fileKey через `get_libraries`)
- Brand invariants (підтверджені з `base_prom.pptx`):
  - Primary: `#7B04DF`
  - Dark: `#222223`
  - Font primary: Montserrat
  - Font display: Montserrat ExtraBold
- Ці значення вже hardcoded у `02-prom-design-system-spec.yaml` зі статусом `confirmed`, тому відсутність fileKey НЕ блокує MVP.

## Known limitations

- `use_figma` не підтримує всі property сетти; перевіряй у docs на кожен виклик.
- `get_screenshot` іноді повертає низький res для великих frames → використовуй `get_screenshot` для компактних node, а не entire page.
- Components з variants потребують `variant` prop — якщо не заданий, фігма поверне default.
- Ukrainian font characters: Montserrat + ExtraBold мають повний Cyrillic set, але іноді Figma підставляє Arial fallback — перевіряй screenshot на мові зберігання.
