# roadmap-artifacts.md

> Спільний reference planning-suite. Формати **планувальних** артефактів (рішення/прогноз). Це НЕ звіти team-ops-reporter (ops-report templates) — ті описують факт; ці фіксують план. Споживають: `quarterly-planning`, `project-planning`, `sprint-planning`, `roadmap-architect`.

---

## 1. Квартальний roadmap (Confluence-сторінка)

Секції (валідовано прогоном Q3 FET):
1. **Панель-шапка** — артефакт/команда/період/автор + метод (CQL за лейбою + статуси Jira + capacity).
2. **Capacity кварталу** — таблиця по платформах: demand / стеля / стан (status-лозенги green/yellow/red); панель про платформну гранулярність (FE-слайси → наступний квартал).
3. **Основні фокуси** — таблиця фокус / чому.
4. **Roadmap-таймлайн** — Gantt-таблиця по спринтах (`<td colspan>` = смуга напрямку; status-лозенга «у роботі»/«план»).
5. **Основні напрямки** — дерево Ціль → Initiative → Епік → Фіча; **фічі списком `код — назва`** у клітинці (`<ul><li>`), не голими номерами; колонка статусу — лозенги.
6. **Перенесено в наступний період** — таблиця фіч (списком) + причина.
7. **Метод** — панель-note.

HTML через `updateConfluencePage`/`createConfluencePage` (`contentFormat: html`): status — `<span data-type="status" data-color="...">`, панелі — `<div data-type="panel-info|success|note">`, `colspan` у таблицях працює.

## 2. Живий дашборд (cowork artifact)

Self-contained HTML (light mode, `:root{color-scheme:light}`). Статичне: capacity-смуги (ціль 85% / стеля 100% мітки), Gantt-таймлайн. Живе (при відкритті): статуси епіків ← `getJiraIssue` per-key; інвентар фіч ← CQL за лейбою кварталу. Реєструється через `create_artifact` з `mcp_tools`; кнопка оновлення — у шапці панелі (не дублювати).

## 3. Roadmap проєкту (арка, project-planning)

Мульти-квартальний Gantt однієї ініціативи: епіки/фічі смугами через квартали, **критичний шлях** виділено, прогнозна дата завершення, **дрейф vs baseline** (для `replan`), what-if по % allocation. Формат — HTML-дашборд або Confluence-таблиця.

## 4. Дерево структури (roadmap-architect)

Ціль → Initiative → Епік → Фіча (вся структура, без квартального скоупу). Плюс **звіт розривів розмітки** (фічі/епіки без кварталу/цілі/коду). Формат — Confluence-сторінка або markdown.

## 5. Інтерактивний capacity-gate (corrections)

Екран зі смугами завантаження по платформах + перемикачі фіч/платформних слайсів у наступний період; перерахунок наживо; кнопка «зафіксувати скоуп» (через `sendPrompt`). Для фази корекції скоупу.

## 6. Конвенції (усі артефакти)

- Фічі — завжди `код — назва` списком, не голі номери/діапазони.
- Кожне число — з inline-періодом (квартал/спринт, к-сть спринтів, нормалізовано/ні).
- AI-оцінки — маркер «на підтвердження TL»; рішення PM.
- **Драфт ≠ фінал:** запис у Confluence/Jira — лише після явного апруву PM; драфт і фінал — окремі файли.
- Збереження: workspace + бібліотека (`persistent-storage.md`).
- Мова — `user.language`.

## 7. Демаркація з team-ops-reporter

| Артефакт | Чий |
| --- | --- |
| ops-report (sprint/quarter/initiative/member review) | team-ops-reporter (факт) |
| quarterly roadmap, project arc, structure tree, capacity-gate, живий дашборд | planning-suite (план/прогноз) |

Спільне джерело Jira-даних — `jira-data-protocol.md`. Планувальний артефакт може містити блок «факт», зрендерений делегуванням у team-ops-reporter.
