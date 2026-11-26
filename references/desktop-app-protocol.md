# desktop-app-protocol.md

> Shared reference (since v4.13.0). A page the plugin already publishes becomes an app a person installs from the Claude desktop app (the vendor offers the install for Mac and Windows, [launch article](https://claude.com/resources/articles/install-as-app); measured on macOS only, Windows not measured yet, `native-surfaces.md` §7): its own window, icon and menu, a badge, notifications, a menu-bar item, live numbers through the viewer's connectors. One shell for the whole plugin (`scripts/app_shell.py` and `scripts/app_shell/`), one profile per app (`references/app-profiles.yaml`); the page's data lives in the artifact's database, so a new snapshot updates the app without a new version of the page. The procedure of `cjm-research` Step J4a (the app «CJM»); a second profile, PM OS, follows its own protocol on the same shell (§2).
>
> **Rule of the file:** the repository holds shell code and placeholders only; a user's values go into the published page or its database, never into the plugin's files (§12, lint check 33). An app is a publication: every page version and every snapshot goes through `artifact-publishing.md` after its one question; a scheduled run never writes to the database (§8). Permissions are asked one at a time, only from a button press (§7).

## 1. Three levels

| Level | What it is | Status |
|---|---|---|
| `page` | the artifact in a browser, as before (v4.12.0): its snapshot, the shared edits; a wrapped page adds the button «Встановити як застосунок» where the platform can install it | since v4.13.0 |
| `app` | the installed app's window: its own window, icon and title, the application menu, the badge on the icon, notifications, the menu-bar (tray) item, live numbers from connectors — no files, no commands | since v4.13.0 |
| full access | files and the plugin's commands on the owner's own computer | **not available yet** — v4.13.1 |

A profile with `level: full`, the permission `full-access` or a non-empty `commands` is refused by `app_shell.py check` and by `wrap` with «arrives in v4.13.1»; `shortcuts` and `overlay` are refused as unknown for now (a later release). The skill says it in one line and builds nothing. In a browser or on a phone a wrapped page works as in v4.12.0: every part of the shell that is absent or refused switches itself off silently, with no console error.

## 2. Profiles

`references/app-profiles.yaml` — read only by `app_shell.py` (its own reader of exactly that shape), never written; `python3 scripts/app_shell.py check` checks it (`[--profiles PATH]` for another file), `schema` prints the constants a profile may use. **Placeholders only:** a profile names what a role needs as `<jira_project>`, `<dashboard_id>`, `<product>`; `check` refuses a URL, an e-mail, a UUID or a tracker key in any of its strings («value in a template»), and lint check 33 keeps the profiles and the shell's files clean in the repository.

- **Keys** — `level`, `title` (`uk` and `en`), `layout` (`tabs`, the default: the modules as a row of tabs under the header · `rail`: the header as a column beside the modules, each module with a counter of its rows that ask for attention — shell 2), `icon` (`glyph`: `journey` · `os` · `chart`; `image: plugin` — the plugin's own mark `assets/app-icon.png` in the header and as the installed app's icon, the glyph staying the fallback), `permissions` (`notifications` · `menu-bar`), `modules`, `menu`, `badge`, `tray`, `notify`, `connectors` (`{role, needs}`, `needs` a placeholder), `commands` (empty until v4.13.1). An unknown key is an error.
- **A module, two forms** — short `{id, block, source, title, home?}` or composed `{id, title, home?, blocks: [{block, source, title?, place?}]}` (up to 8 blocks, rendered one under another, each with its title; `place: aside` puts a block into a side column beside the others on a wide window); never both in one module. `block` is one of `table` · `list` · `number` · `chart` · `feed` · `map` and, since shell 2, `lead` · `bars` · `line` · `day` (`scripts/app_shell/charts.js`; their shapes and the cells a table may draw are in `references/pm-os-protocol.md` §2); `map` is the single block of a composed module when it is in one. `source` is a section name (`^[a-z0-9][a-z0-9.-]{0,63}$`, §5), `@edits` — the live `edits` collection (§10), never a section — or `@summary`, the sentence the shell counts from the modules it shows (a `lead` block only). One module at most is `home`; titles in `uk` and `en`.
- **The menu** — module ids and the actions `edit` (with an `accel` such as `CmdOrCtrl+E`) and `open-in-claude`. The shell leaves `open-in-claude` out: the platform gives a page no call for it (§12).
- **The owner's `config/app`** (§5) — the base the profile gives, rebuilt by its owner: `{v: 1, modules: [{id, on, order}], custom: [...]}`, at most 64 module entries and 20 custom modules, a custom module in either form with a plain-text title of 1–80 characters and never the block `map`. `python3 scripts/app_shell.py check --config <file>` before it is written; the page reads it as foreign input all the same.
- **A second profile** — `pm-os` stands in the file as a placeholder with no modules. Its screens, sources and questions belong to its own protocol, added by its own release; this file stays the rules of the shell, the data channel, the permissions and the publication for every profile.

## 3. Before the first build — one question

Before the first build of an app, one question with options where the host can ask one (`native-surfaces.md` §3 is still the publication's own, §4). It is built from the user's context, never a list read out:

- **The modules of the profile**, each with one line on what it gives **this** PM — from what the run knows: how many maps the product has and which need attention (the portfolio), whether colleagues already edit the published maps (their `edits`), which connectors are connected (live numbers, §6). A module the PM turns off or moves goes into `config/app` (§2).
- **The theme** — 2–3 candidates: `python3 scripts/app_shell.py theme --tokens <tokens of a product> [--tokens <tokens of another>] --out <scratch>/themes.json` — one candidate per token file in the order given, the built-in `neutral` always last. A token file is `{product, light: {the nine tokens}, dark?, font?, radius?}` (or the nine tokens at the top level): `bg`, `surface`, `text`, `muted`, `accent`, `border`, `ok`, `warn`, `crit`, each `#rrggbb`; `font` `""` (the system font) or one of the Google Fonts with Cyrillic in `app_shell.py`'s `FONTS` (Inter, Roboto, Open Sans, Montserrat, Manrope, Rubik, Nunito, PT Sans, Fira Sans, IBM Plex Sans, Noto Sans, Golos Text); `radius` a whole number 0–24; a missing `dark` is derived. The tokens come from the product's design system in the user's context (as `design-bridge` reads it), never invented. A candidate's `weak` lists every token under its contrast threshold in either mode with a suggested replacement — the question names it so («акцент у темній темі 2.8 < 3 — заміна #6aa0f5»). The pick: `theme --tokens … --pick <id> --out <scratch>/theme.json`, refused while a token of that candidate is weak (the replacement goes into the token file first).
- **The products** — from the user's context, each with a short label and a colour: `--product <id>:<label>[:#rrggbb]` (§4), the id lower-case `[a-z0-9-]`, the label 1–24 characters without a colon.

The answers are the app's: a later run reads them back from `snapshot/meta`, `snapshot/theme` and `config/app` and asks again only what changed.

## 4. Build and publish

Everything local is built first, then one question, then the writes. Each step runs only after the one before it succeeded — except a map the database cannot hold, which only leaves that map out (step 3, §9):

1. **The data**, into a scratch folder of the session — per product the producers of its profile (for `cjm`: `journey_portfolio.py app-data` and `journey_map.py app-data` for every map, `journey-protocol.md` §9 and §13). A map `app-data` refuses as too large stays out (§9); the rest goes on.
2. **The theme** (first build, or when the PM picks another) — `theme … --pick <id> --out <scratch>/theme.json` (§3).
3. **The snapshot** — `python3 scripts/app_shell.py snapshot --profile <name> --section <section>:<product>:<file> … --product <id>:<label>[:#rrggbb] … [--theme <scratch>/theme.json] [--connectors <scratch>/bindings.json] [--prev-meta <file>] [--at <ISO time>] --out <scratch>/db` — local files only, never the database: one JSON file per database document under `<scratch>/db/<collection>/<id>.json`. A refusal (a wrong product, section, theme or binding) writes nothing. A section document over 256 KiB is not a refusal: `snapshot` exits 1 with `ok: false`, names it in `over: [{path, bytes}]` and leaves it out of DIR and of `meta.sections`; the documents that fit are in DIR, and they are the ones written in step 6 (§9).
4. **The page** — `python3 scripts/app_shell.py wrap --page <page> --profile <name> --out <scratch>/<name>-app.html [--lang uk|en] [--connector '<server>:<tool>[,<tool>]' …]`. A profile's protocol names its page; for `cjm` it is a **data-free page** the skill writes into the scratch folder — a complete small HTML document whose `<title>` is the profile's title in the run's language («CJM») and whose `<body>` holds one line: «Дані застосунку завантажуються з бази артефакту, коли його відкриває людина, що увійшла в обліковий запис.» / "The app's data loads from the artifact's database for a signed-in viewer." No product's data goes into the page's own HTML: the data lives apart from the shell, so a data update never needs a new version of the page. `wrap` puts the permission manifest, the shell (`shell.css`, then `shell.js`, `blocks.js`, `map.js` only for a profile with a `map` block, `desk.js`, `live.js`, each byte for byte) and the profile as JSON into the page; the page's own body stays inside it and shows whenever there is no snapshot to read. It refuses a page with a `<script src>` (a published page takes inline scripts only), a page without `<head>` or `<body>`, one that is already an app, and a profile that does not pass `check`; it writes nothing then. Its `APP_RESULT` gives `shell`, `permissions` and `capabilities`.
5. **The one question** of `artifact-publishing.md` §3–§4, after `python3 scripts/publications.py find --key <key>` (for `cjm`: `cjm-research/app/cjm`): it names exactly what will be published — the app, its permissions in words, that each person installs it themselves, and, when a map was refused by `app-data` or named in `over`, that the app goes without that map, with §9's line.
6. **On «так»** — the publication: the wrapped file as a page on the host's ARTIFACT with the `capabilities` that `wrap` printed, verbatim, never composed by hand (`desktop`, `db` with the rules of §5, `user` with the scope `profile`, and `mcp` only when `--connector` was given, §6). The host's publishing tool puts the wrapped document inside its own page skeleton; that works (measured 2026-11-26 on a saved published version: the title, the manifest, the tabs and the database read). Then **one batch write** into that artifact's database — the host's database tool, as the person: each file of DIR as the document `<collection>/<id>`, and `config/app` when the PM changed the modules. Nothing else is written.
7. **The record** — `python3 scripts/publications.py record --key <key> --surface artifact --kind page --level page --id <id> --url <url> --app <profile>:<shell>[:<permission>,<permission>]`, the profile, the shell number and the permissions those `wrap` printed (`artifact-publishing.md` §5).
8. **One line** to the user, from the profile's protocol (for `cjm`: «Натисни «Встановити як застосунок» на сторінці, а потім дозволь сповіщення й меню-бар по одному»). Claude cannot install an app for anyone: the person presses the button on the page or installs it from the page's sharing menu.

An update without a new page is the same without step 4 and without the page's publication: steps 1–3, the question, the batch write, the record.

Without SHELL — no app: the page of the skill as before, and one line that the app needs a shell. Without the host's ARTIFACT with a database — the page only, with that line.

## 5. The data channel

The page's data lives in the artifact's database, never in its HTML. The rules `wrap` gives the publication:

| Path | Read | Write | What |
|---|---|---|---|
| `""` (the rest) | view | admin — the artifact's editors and its owner | `edits`, the team's shared edits of the maps (§10) |
| `snapshot` | view | owner | `meta`, `theme`, one document per section and product |
| `config` | view | owner | `app`, the owner's modules (§2) |
| `runs` | view | owner | one document per snapshot run |

- **`snapshot/meta`** — `{v: 1, made, products: [{id, label, color}], thresholds: {warning: 0.10, critical: 0.25}, sections: {<section>--<product>: made}, connectors?}`; **`snapshot/theme`** — the one picked theme `{v: 1, id, light, dark, font, radius}`; **`snapshot/<section>--<product>`** — `{v: 1, product, section, made, data}`, `data` in its block's shape; a map is the section `map.<slug>`, and a module whose source is `map` gathers `map` and every `map.*`. **`runs/<made>`** — `{at, sections, ok}`, the log of every write; its id is the `made` time made path-safe (every character outside `A-Za-z0-9._-` a `-`).
- **Limits** — a document at most 256 KiB serialized, a path segment at most 200 bytes, a section name `^[a-z0-9][a-z0-9.-]{0,63}$`, a product id `^[a-z0-9][a-z0-9-]{0,63}$`. A key that names a person (`email`, `e-mail`, `author`, `assignee`, `person`, `owner`, `reporter`, at any depth) is dropped from a section and named in the result's `dropped`. A theme under its contrast threshold is refused.
- **Foreign input** — whatever the page reads from the database it treats as another person's input: a colour only `#rrggbb`, a font only from `FONTS`, a number only when finite, a size a whole px 0–24, text only as text; nothing from the database becomes HTML, CSS, a script or a link.
- **A partial update** — one map refreshed, one product's numbers: `--prev-meta <file>` with the previous `snapshot/meta` read back from the database. It carries over the dates of the sections not written in this run, while their product is still among the `--product`s, and the connectors when no `--connectors` is given. Without it `meta` keeps only the sections written now: the dates of the others vanish, and their blocks show no freshness. Every run names every product the app shows.

## 6. Connectors — a binding is data

The page cannot know a connector tool's arguments or answer, and the repository may not name one. So the binding of a role to a tool is **data composed in the user's session** from the tool's own schema as the session sees it — never guessed, never written into the repository:

- **The manifest** — `wrap --connector '<server>:<tool>[,<tool>]'` (the server's display name as the host shows it, or `host:<name>`; the tools after the last colon) becomes `capabilities.mcp`. Only the tools the bindings use.
- **The binding** — `snapshot --connectors <scratch>/bindings.json`: `{<role>: {server, tool, input, pick}}`, a role the profile declares (`cjm`: `issue-status`, `funnel-numbers`). `input` is the tool's arguments as plain JSON (at most 4 KiB, 6 levels) where a string may hold `{codes}` and a value that is exactly `{codes[]}` stands for the array of codes; no other brace. `pick` is exactly `{items, key, value}`, dot-paths of up to 8 names into the tool's answer (`items` may be empty). It goes into `snapshot/meta.connectors`.
- **The codes** — the codes of the map sections in the snapshot (every product's) for `issue-status`, the funnel's stage ids for `funnel-numbers`, each passing the code rule; nothing the snapshot does not already show is asked.
- **No binding, or a binding that does not fit** — the snapshot's own numbers with their date, and the line «живі числа недоступні: <причина словами>». The page never polls: live numbers are asked once when the data arrives and again on each press of «Оновити».

## 7. Permissions

- Asked **one at a time**, **only from a button press** in the panel «Дозволи» of the app's window, each with a 30 s wait («немає відповіді — спробуй ще раз»); never on load. Asking three permissions in one call hung the app (measured, `native-surfaces.md` §7).
- A feature whose permission is not granted stays off silently and switches on when it is granted; the states are read again when the window regains focus.
- The platform treats a refusal as final for that page load.
- **A new version of the page asks every permission again** — so a new version is published only when the shell or the profile changed (§8), and the user is told so before the question.

## 8. Updating

- **A new snapshot is a publication** — the same one question (`artifact-publishing.md` §4: what goes, where, who can open it) before every write into the database, then §4's update without a new page.
- **A new version of the page** only when the shell or the profile changed — the profile's name, the `shell` number or the `permissions` `wrap` prints differ from the record's `app` (`publications.py find`), or the user asks for one; a plugin release that changes the shell's files or a profile's modules or menu bumps `SHELL_VERSION`, so the skill sees it — and then, before the question, one line that the app will ask its permissions again.
- **Default: a scheduled run never writes to the database**, never wraps and never publishes; it may refresh the notes and the pages locally as its own protocol says.
- A profile's own protocol may replace the per-write question with **one recorded standing consent** of the user; that protocol must then state its bounds — which documents, only while the artifact is private (checked before each write), every write logged in `runs`, the words that revoke it. `cjm` has no standing consent.

## 9. A map too large for one database document

A map too large for one database document stays out of the app, refused in one of two places. `journey_map.py app-data` refuses a map whose data is over its own limit (`APP_DATA_MAX`, 1 KiB under 256 KiB, the rest left to the document's own fields) — exit 1, `ok: false`, the size in its message («the map's data is N bytes — over the 256 KiB of one database document: it stays out of the app, open its page») and `bytes`, nothing written. `snapshot` names any section document still over 256 KiB in `over: [{path, bytes}]` — exit 1, `ok: false`; that document is not in DIR nor in `meta.sections`, and every document that fits is in DIR and is written (§4 step 3). Either way the skill says one line — «карта «<назва>» завелика для застосунку: <N> КБ при межі 256 КБ — винеси частину кроків у дочірню карту або прибери зайві рядки; поки що вона відкривається своєю сторінкою» — and the one question (§4 step 5) names the app without that map.

## 10. The team's edits in the app

The map inside the app is the map's page of v4.12.0: the same switch «Редагувати», the same `edits` collection and document format, written by the same editing script (`journey-protocol.md` §9 «Shared edits»). Editors and the owner write it (the rule `""` of §5); a viewer sees the marks. The feed «Правки команди» and the badge read the same collection. The edits are still a draft: `cjm-research` J9 reads the app's artifact's `edits` too, and they reach the note only through its preview (`journey-protocol.md` §12).

## 11. The script

`scripts/app_shell.py`, stdlib (Python 3.9). Every command ends with one `APP_RESULT {json}` line; exit 0, 1 when a check fails or a command refuses, 2 for a wrong argument.

| Command | What |
|---|---|
| `schema` | the levels, permissions, later permissions, blocks, glyphs and menu actions a profile may use |
| `check [--profiles PATH] [--config FILE]` | the profiles file (or an owner's `config/app`) against them: `{ok, errors}` |
| `wrap --page P --profile NAME --out O [--lang uk\|en] [--connector SERVER:TOOL[,TOOL] …] [--profiles PATH]` | the page as an app (§4); `capabilities` for the publication |
| `theme --tokens FILE … [--pick ID] --out FILE` | the theme candidates with their weak tokens, or the one picked theme (§3) |
| `snapshot --profile NAME --section NAME:PRODUCT:FILE … --product ID:LABEL[:#rrggbb] … [--theme FILE] [--connectors FILE] [--prev-meta FILE] [--at ISO] --out DIR [--profiles PATH]` | the database documents of one snapshot (§5), `{ok, docs, over, dropped, made}` |

## 12. What never happens

- No value of a user in the repository: no product, project, dashboard, person, link or id in a profile, the shell's code or an example (Zorg and `zorg-pay` only); `app_shell.py` never reads `local-context.md` and never writes into the plugin's files.
- No person's name, e-mail or avatar in the app, a notification or the menu-bar item; a section never carries a person (§5); the edits keep an opaque id only.
- Nothing installed on the user's behalf — the person presses «Встановити як застосунок».
- No permission asked on load, none asked several in one call.
- No `full-access`, `shortcuts`, `overlay`, no commands and no files before v4.13.1.
- No polling of a connector, no binding guessed or kept in the repository.
- No HTML, CSS, script or link taken from the database.
- No «Open in Claude» menu item — the platform gives a page no call for it.
- No write into the database by a scheduled run (§8), and no snapshot without its question.

## 13. Measured, and what the acceptance run still shows

What was measured on the host (install, permissions, notifications, the menu-bar item, the badge, the database read, a new version, the icon) is in `native-surfaces.md` §7, with its date. The acceptance run on the user's computer still has to show: the whole list on Windows too (install, the permissions one by one, the tray item, notifications — none of it measured there); the editing script of the map under the published page's real content-security policy; the theme's fonts on a real network; the first database snapshot read by the installed app; a real connector binding (the cache replay, the consent prompt); the icon after a reinstall; the permissions asked one by one; a snapshot update without a new version, the permissions not asked again; an editor who is not the owner cannot write `snapshot`.
