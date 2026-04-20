# Figma MCP — Config & Playbook for Grow PM

> **Статус автентифікації** (станом на 2026-04-20): ✅ авторизовано як `a.siletskyi@smartweb.com.ua`, плани: `UAPROM LLC, EDRPOU 36507036` (Pro, View seat), `Prom+` (Starter, View seat), `My drafts` (Full seat).
> **Наслідок:** read-тулзи Figma MCP доступні; для write-операцій у Prom-командах — seat обмежений (треба ескалювати).

---

## 1. Доступні Figma MCP інструменти (що реально вмикаємо)

| Tool | Коли використовуємо у Grow PM | Обмеження |
|------|------------------------------|-----------|
| `whoami` | diagnostics: перевірити, що залогінений Prom-акаунт | — |
| `get_libraries(fileKey)` | Step 3 design-bridge: знайти Prom DS library keys | потрібен **будь-який** fileKey у команді |
| `search_design_system(query, fileKey, ...)` | пошук компонентів / токенів / стилів | можна звузити `includeLibraryKeys` |
| `get_variable_defs(nodeId, fileKey)` | витягти точні токени (color, spacing) з вибраного frame | може вимагати Full seat |
| `get_design_context(nodeId, fileKey)` | отримати структуру layout + компонентів | — |
| `get_metadata(fileKey)` | назва файлу, дата, команда | — |
| `get_screenshot(nodeId, fileKey)` | eталонний скрін компонента для assets/ | — |
| `get_code_connect_map` | mapping компонент ↔ код | Prom має бути підключений до Code Connect |
| `generate_diagram(...)` | генерація діаграм на FigJam | альтернатива diagram-prototyper |
| `get_figjam(fileKey)` | читати FigJam дошки | — |
| `search_plugins` (meta) | знайти сторонні Figma плагіни (не наш кейс) | — |

---

## 2. Як знайти `prom_ds_file_key`

Один з трьох шляхів:

### Шлях A — з браузера
1. Відкрий https://www.figma.com/files/team/1021675057377943036/all-projects
2. Зайди у проєкт `Design System` (або подібний — `Prom DS`, `UI Kit Prom`).
3. Відкрий файл бібліотеки → URL: `https://www.figma.com/file/{fileKey}/...`
4. Скопіюй `{fileKey}`.

### Шлях B — через будь-який інший файл команди
1. Візьми fileKey будь-якого поточного проєкту Prom (наприклад, з макета Q&A).
2. Виклич `get_libraries(fileKey)` — отримаєш список subscribed libraries.
3. Знайди ту, що має `"name"` типу "Prom DS" / "Prom Library" — її `key` і є шуканим `library_key`; `sourceFileKey` (якщо повертається) — це `prom_ds_file_key`.

### Шлях C — пошук по пошуку компонента
1. Виклич `search_design_system(query="Button", fileKey=<будь-який>)`.
2. Серед результатів будуть `libraryKey` і `fileKey` — фіксуй.

**Як тільки знайшов — внеси у:**
- `local-context.md` → секція `Figma → Design System`: `ds_file_key`, `ds_library_key`
- `design-integration/02-prom-design-system-spec.yaml` → `meta.source`

---

## 3. Mapping: design-skill → Figma MCP calls

### design:design-system (аудит)
```
Input: Figma frame URL (fileKey + nodeId) + prom_ds_library_key
Steps:
  1. get_design_context(nodeId, fileKey)     → структура фрейма
  2. get_variable_defs(nodeId, fileKey)       → використані токени
  3. search_design_system(query, fileKey,
       includeLibraryKeys=[prom_ds_library_key]) → каноничні токени
  4. diff → які значення захардкоджені (не токени)
Output: consistency-report.md
```

### design:design-handoff
```
Input: final frame URL
Steps:
  1. get_metadata(fileKey) → назва, дата
  2. get_design_context(nodeId, fileKey) → layout tree
  3. get_variable_defs(nodeId, fileKey) → tokens в hand-off
  4. get_screenshot(nodeId, fileKey) → прев'ю
  5. get_code_connect_map → mapping на існуючий код (опціонально)
Output: handoff.md (per Part 1 §4, Step 4)
```

### design:accessibility-review
```
Input: frame URL + context
Steps:
  1. get_screenshot(nodeId, fileKey) → capture
  2. get_design_context(nodeId, fileKey) → label associations, roles
  3. get_variable_defs → перевірити contrast ratios для text-bg пар
Output: a11y-report.md (WCAG 2.1 AA чек-ліст, Part 2 §7)
```

### design:design-critique
```
Input: frame URL + (optional) user-flow context
Steps:
  1. get_screenshot(nodeId, fileKey) → capture
  2. get_design_context(nodeId, fileKey) → ієрархія
  3. search_design_system("Product Card" etc.) → canonical ref
Output: critique з хірургічним фокусом на hierarchy / consistency / usability
```

### design:ux-copy
```
Input: concept/requirements doc + (optional) frame URL
Steps:
  1. IF frame URL: get_design_context → список текстових вузлів
  2. Застосувати tone-of-voice з local-context + copy_library (Part 2 §8)
Output: copy-draft.md (CTA, empty-states, errors — українською)
```

### diagram-prototyper (Prototype type)
```
Input: concept summary + flow description + Prom DS
Steps (automatic):
  1. get_libraries(fileKey) → заселив library_key
  2. search_design_system("Button", "Card", "Input", fileKey,
       includeLibraryKeys=[prom_ds_library_key])
  3. get_screenshot для еталонів компонентів
  4. Створити:
       - low-fi: Mermaid/HTML з token-кольорами
       - mid-fi: FigJam (generate_diagram)
       - hi-fi: інструкція для дизайнера (add_code_connect_map, якщо є код)
Output: prototype artifact (файл + посилання)
```

---

## 4. Готові промпти (копіюй у Claude)

### 4.1. Виявити та закешувати Prom DS library
```
Користуючись Figma MCP:
1. Викличи whoami і переконайся, що залогінений у команді Prom (team::1021675057377943036).
2. Візьми будь-який fileKey з команди (можу дати URL конкретного файлу: <PASTE>).
3. Викличи get_libraries(fileKey).
4. Знайди бібліотеку з назвою, що містить "Prom" / "DS" / "UI Kit".
5. Запиши library key і sourceFileKey.
6. Онови файл design-integration/02-prom-design-system-spec.yaml:
   meta.source.figma_ds_file_key та figma_ds_library_key.
7. Запропонуй patch для local-context.md, секція Figma.
```

### 4.2. Синкнути токени кольору
```
Використовуючи Figma MCP:
1. search_design_system(query="color", fileKey="<DS_FILE_KEY>",
   includeVariables=true, includeStyles=true,
   includeLibraryKeys=["<DS_LIBRARY_KEY>"])
2. Для кожного токена-кольору випиши:
   - name, value (hex / variable alias), mode (light/dark)
3. Збий у секцію `colors.*` у Part 2 (design-integration/02-prom-design-system-spec.yaml).
4. Там, де є невідповідність із теперішнім observed — познач `status: changed` і додай old value у коментарі.
```

### 4.3. Аудит конкретного макета на DS compliance
```
Файл Figma: <PASTE FRAME URL>
Задача: перевірити, наскільки макет слідує Prom DS.
Кроки:
1. Парсинг URL → fileKey, nodeId.
2. get_design_context(nodeId, fileKey).
3. get_variable_defs(nodeId, fileKey).
4. search_design_system для перевірки канону (кольори, spacing, тип).
5. Запусти design:design-system → згенеруй consistency report.
6. Додатково запусти design:accessibility-review на тому ж nodeId.
7. Винось результат у Obsidian Vault:
   GrowPM/design/prom/audits/YYYY-MM-DD-<frame-name>.md
```

### 4.4. "Концепт → Прототип із Prom DS"
```
Я працюю над концептом: <PASTE_CONCEPT_SUMMARY>
Active epic: SHOPEX-<KEY>
Потрібен low-fi прототип на основі Prom DS.

Дії:
1. Запусти diagram-prototyper (type=Prototype).
2. У Step 3 (Resolution) використай Prom DS:
   - fileKey: <DS_FILE_KEY>
   - libraryKey: <DS_LIBRARY_KEY>
3. search_design_system для ключових компонентів (Product Card, Button, Input)
   — візьми реальні токени.
4. Згенеруй HTML-мок із Prom кольорами (колірні токени з Part 2 §2).
5. Передай мок у design:design-critique.
6. Передай у design:accessibility-review (перевір contrast, target size).
7. Онови concept doc із доданими посиланнями.
```

### 4.5. "Вимоги → Handoff із токенами"
```
Стара вимога: <JIRA_URL або Confluence URL>
Нові макети (Figma): <PASTE>

Дії:
1. Спарси вимогу через requirements-creator (Step: read existing).
2. design:design-critique на макет.
3. design:ux-copy — копірайт для всіх станів (per Prom tone-of-voice, Part 2 §1).
4. design:design-handoff:
   - get_variable_defs для всіх nodeIds
   - включи token names (не hex) у handoff.md
   - додай стан-матрицю (default/hover/pressed/focused/disabled/loading)
5. Прикріпи handoff.md як attachment у Jira до tasks у епіку.
```

---

## 5. Error handling

| Ситуація | Що робимо |
|----------|-----------|
| `whoami` повертає не-Prom акаунт | вивести warning, попросити юзера перепідключитись |
| `get_libraries` не повертає Prom DS | попросити вручну додати library у target file, або використати ds_file_key напряму |
| `get_variable_defs` дає 403 | seat обмежений, fallback на `search_design_system` + ручне мапінг |
| fileKey не знайдено | graceful fallback на YAML-кеш (Part 2) + warning |
| Figma MCP недоступний | off-line режим: повний цикл через Part 2 YAML + design-skills без Figma context |

---

## 6. Data policy reminders (з `references/data-policy.md`)

- Не передавати у зовнішні LLM (ChatGPT/Gemini deep research) **конфіденційні** Figma frames з прототипами невипущених фіч.
- Скріншоти, отримані через `get_screenshot`, можна зберігати локально у Vault, **не публікувати** у public Figma community.
- Handoff документи з Figma — приватні, прикріплюємо лише до Jira/Confluence (не у public share).

---

## 7. Installation checklist

- [ ] `design` плагін встановлено (через `/plugin install`).
- [ ] Figma MCP connector активний (видно у tool list `mcp__389697dc...`).
- [ ] `whoami` повертає `a.siletskyi@smartweb.com.ua` + Prom команди.
- [ ] `prom_ds_file_key` знайдено і записано у:
  - `local-context.md`
  - `design-integration/02-prom-design-system-spec.yaml`
- [ ] Обраний файл DS відкривається через `get_metadata` без помилок.
- [ ] Пробний виклик `search_design_system(query="button", fileKey=...)` повертає ≥ 1 компонент.
- [ ] Обновлено `MEMORY.md` з reference memory: "Figma MCP authenticated on a.siletskyi@smartweb.com.ua, Prom DS file key = ..."
