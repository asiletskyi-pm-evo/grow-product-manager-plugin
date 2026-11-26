# Apps from artifacts — design spec (v4.13.0)

**Date:** 2026-11-26 · **Status:** approved in chat on 2026-11-26, implemented by the v4.13.0 release plan · **Target release:** v4.13.0 «Застосунки» (full access — v4.13.1) · Ukrainian original: `2026-11-26-desktop-apps-design.uk.md` · Rules: `references/desktop-app-protocol.md`

> **Decided after the design:** one app for every product, with a switch; the app's data lives in the artifact's database, not in its HTML; full access (files and commands) is postponed to v4.13.1; the menu item «Open in Claude» is left out — the platform gives a page no call for it; connector bindings are data the skill composes in the user's session from the tool's own schema, never values in the repository.

## In short

I propose that release v4.13.0 «Застосунки» adds a shared app shell to the plugin: any page the plugin already publishes as an artifact (the journey map, the map portfolio, the funnel, the focus board, later PM OS) can be installed as an app for Mac and Windows. The first consumer is CJM: one app «CJM» for every product, with the portfolio, the maps and the funnel, its own window and menu, a badge on the icon counting the team's new edits, notifications about health thresholds, and — on your Mac — writing the edits into the note straight from the app, after a review.

What you need to decide: whether the app gets access to the files and commands of the computer (I recommend yes, only for the owner and only a fixed set of commands). My decisions, which you can correct: one app for every product with a switch, not one per map; the data apart from the shell, so that updates do not ask the permissions every time. The first step is a measurement on your account, because on Enterprise an admin may switch off access to the computer.

## What «Install as app» can do

An app is an ordinary artifact that declares the capability `desktop` and a list of permissions in its HTML. In the window of the installed app the page gets extra capabilities; in a browser or on a phone it works as before.

| Capability | What it needs | Note |
| --- | --- | --- |
| Own window, icon, title | nothing | the title from `<title>`, the page draws the icon itself (PNG up to 256 KB) |
| Application menu and context menu | nothing | Windows has no top menu |
| A badge on the Dock icon | nothing | up to 24 characters |
| Notifications | permission `notifications` | text up to 300 characters |
| A menu-bar item (the tray on Windows) | permission `menu-bar` | an icon, a short text, its own menu |
| Global shortcuts, a floating window | `shortcuts`, `overlay` | not needed in CJM |
| Files, commands, terminal | permission `full-access` | only for the organization's own artifacts; on Enterprise the admin switches it on |
| Connectors (the task tracker, dashboards and so on) | capability `mcp` | on behalf of whoever opened it, with consent |
| Ask Claude | capability `sample` | counts against the plan's limits |
| Data shared between people | `db`, `user` | we have it since v4.12.0 (shared edits) |

Three limits shape the design:

- The app works only while its window is open, and only online. It gives no background runs on a schedule: the schedule stays in Claude's scheduled tasks.
- Every new version of the artifact asks the permissions again, even after your own edits.
- A person installs it themselves: with the button on the page or Share → Install as app. Claude cannot install the app for them.

Sources: [the launch article](https://claude.com/resources/articles/install-as-app) and the description of the capability `desktop` in the artifact platform (contract version 0.2.99). In your Claude for Mac 8.9912.0 the menu item is there (checked 26.11).

## One mechanism «artifact → app»

One shell for the whole plugin: a skill renders its page as now, and the shell turns it into an app by a profile. CJM is the first profile, PM OS the second; the skills need not know about windows, menus or permissions.

The page's data lives in the artifact's database, so the app updates without a new version; a bridge to the files exists only in full access.

Three levels, each adding to the one before:

1. **Page** — as now: an artifact in a browser, a data snapshot, shared edits. Now also the button «Встановити як застосунок», when it is available.
2. **App** — its own window, icon, menu, badge, notifications, a menu-bar item, live numbers from connectors. No access to files.
3. **Full access** — only for the owner on their own computer: the app reads the notes from the vault and `~/.grow-pm` directly and runs only the plugin's commands from its profile's list.

| Part | What it does |
| --- | --- |
| `references/desktop-app-protocol.md` | the rules: levels, permissions, the question before publishing, what never happens |
| `references/app-profiles.yaml` | a profile per app: title, icon, permissions, menu, what the menu bar shows, when to notify, which commands are allowed |
| `scripts/app_shell.py wrap` | takes the skill's page and the profile, inserts the manifest with the exact list of permissions and the embedded shell code; no dependencies, like the other scripts |
| The shell code in the page | the install button, the icon, the window, the menu, the badge, notifications; each part switches itself off silently when it is absent or refused |
| The data channel | the data lives in the artifact's database (the collection `snapshot`), not in the HTML: a new snapshot after your «так» updates the app without a new version of the page, so the permissions are not asked again |
| A record in `publications.py` | the field `app` in the place's record (profile, permissions, shell version), so that the next run knows it is an app |
| A local bridge (level 3) | the file `~/.grow-pm/apps/<key>/bridge.yaml` with the paths to the plugin and the notes; the skill writes it locally, it never reaches the publication |

What PM OS takes: the same `wrap`, its own profile `pm-os` and the same data channel. Its screens and sources stay with its own thread.

What the shell must be able to do for PM OS (a request of the PM OS thread, 26.11):

- several modules in one window with navigation (the list `modules` in the profile, the tab remembered);
- connectors and the Mac's local servers at the same time; where they are absent — the last snapshot with its date;
- buttons «Запитати Claude», if the profile switches them on;
- a snapshot of several sections plus `config`, written by the owner only; a log `runs`, a section's freshness = the date of its last write;
- the badge and notifications while the app runs (with a menu-bar item, closing the window only hides it);
- team profiles — only with full access and only shown in the window: never into the database, files, a request to Claude or to a connector.

**Theme, products and settings** (requirements of 26.11, shared by CJM and PM OS)

- **The product's design system.** The theme is not hard-coded: the tokens (colours, fonts, radii) lie in `snapshot/theme` and update without a new version. The source is the product's design system from the user's context (as in design-bridge). Several products — the skill offers 2–3 options to choose from. The shell takes from the database only values from a list (a colour `#rrggbb`, a font from the Google Fonts list, a number in px), no arbitrary CSS or links: data from the database is foreign input.
- **Light and dark theme.** A switch in the header: light, dark, as the system. The choice is remembered for this viewer. Contrast is checked in both themes before publishing; the skill names a token with weak contrast and offers a replacement.
- **Several products.** Every data document has a field `product`; every card carries the product's label (a short name and a colour); the header has a product switch and «Усі». This changes my decision for CJM: one app for all your products with a switch, not a separate one per product.
- **A base you rebuild.** The profile gives the base; modules are switched on, hidden and reordered in the settings (`config` in the database), custom ones are assembled from the shell's ready blocks (list, table, number with a trend, chart, event feed). A block is data, not code: `config` holds no HTML and no scripts.
- **Built together with you.** The app's first run is a short interview in the chat: the skill reads your context (products, connectors, existing maps), proposes modules and explains what each one gives you in particular, and builds `config` from your answers.

## The CJM app

One app «CJM» for all your products, with a product switch in the header and the product's label on every card: everything cjm-research already does as separate pages comes together in one window. One app instead of one per map is my decision: otherwise ten maps make ten icons, and each would ask the permissions separately.

**Screens**

1. **Portfolio** (home) — all the product's maps, their health and trend, thresholds warning 10% and critical 25% from the baseline.
2. **Map** — the v4.12.0 page with the tree of child maps, the switch «Редагувати» and shared edits.
3. **Funnel** — the 6-stage funnel dashboard.
4. **Team edits** — what colleagues changed and what waits for your review.

**What the app's window adds**

- Menu: Portfolio, Maps, Funnel, Edit (Cmd+E), Team edits, Open in Claude.
- A badge on the icon: how many team edits wait for review.
- A menu-bar item: the weakest map and its score, the list of maps in the menu.
- Notifications while the window is open: a colleague changed a map; a stage's number crossed a threshold.
- Live numbers from connectors: the statuses of tasks from the task tracker by the initiative codes on the map, and the funnel's numbers from dashboards. Only what the map already shows, no new queries (dashboards rule §9).

**Full access, only on your Mac**

- The button «Переглянути й записати»: the app itself runs `page-diff` and `board-take --dry-run`, shows the same preview as in the chat now, asks the evidence class for the new rows and writes the note with one button.
- Before writing it makes a backup; after writing it removes the taken edits from the artifact's database.
- It reads the notes straight from the vault, so your map is always fresh, without a new publication.

**What changes in cjm-research**

- A new step J4a «Застосунок» after J4: it offers to build the product's app from the portfolio, the maps and the funnel.
- The same one publication question now says that this is an app, which permissions it will ask and who can install it.
- After the publication one line: «Натисни «Встановити як застосунок» на сторінці». For full access the skill also writes the local `bridge.yaml`.
- Colleagues in a browser or on a phone see the same page as in v4.12.0.

## Approaches, safety and decisions

I recommend approach B: it closes the loop «team edits → note» without the chat, and keeps the risk within a fixed list of commands.

| Approach | What it gives | Cost |
| --- | --- | --- |
| A. An app without access to the computer | window, menu, notifications, live numbers; the least new attack surface | edits still reach the note only through the chat |
| **B. A for everyone + full access for the owner only** (recommended) | reviewing and writing edits right in the app, the map always fresh | a new channel for running commands: needs a measurement and a repeated audit |
| C. A separate local server with arbitrary actions | any action from the app | rejected: more code, the server lives outside the window, contradicts the findings of the v4.11.1 audit «Ядро — це дані» |

**Safeguards for full access**

- The commands are fixed in the profile: only `python3 <plugin>/scripts/journey_map.py` with subcommands from the list, the arguments as an array without a shell.
- Colleagues' edits are foreign data: they reach a command only as a file that `page-diff` checks, never as part of a command.
- Writing only after your press, only into the maps' notes and `~/.grow-pm`, with a backup.
- Full access switches off if someone outside the organization wrote into the artifact. Whether colleagues' edits in the database count here, a measurement will show.

**Rules that stay**

- A new data snapshot in the artifact's database is a publication too: the same question before every update, a scheduled run does not publish.
- A person's profile never reaches the app; the database holds only opaque ids.
- Sharing — a separate question and only with named people, as now.

| Decision | Whose | Proposal |
| --- | --- | --- |
| Give the app full access | yours | decided 26.11: yes, only for the owner (approach B), in v4.13.1 after the measurement and the audit |
| One app per product or per map | mine, revised 26.11 | one for all products, with a switch and product labels |
| Data apart from the shell (the `snapshot` channel) | mine | yes, so as not to ask the permissions after every update |
| The button «Запитати Claude про карту» | mine | not in the first release: it spends limits and opens a new data path |

## Your data does not get into the templates

Only the shell code and profiles with placeholders go into the repository; everything of yours is filled in only at run time, in your account and on your computer (requirement of 26.11, shared by CJM and PM OS).

| What | Where it lives | In the repository |
| --- | --- | --- |
| The shell code, the protocol, `app_shell.py` | the repository | yes, without any values |
| The profiles `cjm`, `pm-os` | the repository | yes, only placeholders such as `<product>`, `<jira_project>`, `<dashboard_id>` |
| The product's name, the task tracker's project, dashboards, the team, the directions | `local-context.md` and `~/.grow-pm` on your Mac | no |
| The paths to the plugin and the notes | `~/.grow-pm/apps/<key>/bridge.yaml` | no |
| The app's data and `config` | your artifact's database | no |
| Links to your artifacts | the publications record in `~/.grow-pm` | no |
| Examples and tests | the repository | only the fictional product Zorg, as in the existing fixtures |

How we guarantee it:

- `app_shell.py wrap` does not read `local-context.md` and writes no values into the plugin's files: values reach only the published page or its database.
- The new files (profiles, shell code) fall under the plugin's existing checks for leaks of organization data (`skill_lint.py` checks 9 and 16–18), and one more check: no artifact links, e-mail addresses or server ids in the templates.
- Before every push — `branch_leak_scan.py` with your word list in `testing/org-tokens.local`. The cloud does not have that list, so the apps release passes this scan on your Mac.
- This design goes into the repository scrubbed: placeholders and Zorg instead of the names of your product and company.

## Stages

The plugin's code starts only after v4.11.2 and v4.12.0 are merged and after your «так» on this design.

1. **A measurement on your Mac** (about 15 minutes, no plugin code). A test artifact with `desktop` will show: whether installing is available in the organization's account, which permissions are open (full access above all), whether the app updates through the database without a new version, and whether colleagues' edits in the database take full access away. The result goes into the host capability table (native-surfaces §6–§7) with its date.
2. **v4.13.0 «Застосунки»** — the shell, the protocol, the CJM profile at level «App», the data channel, the field `app` in the publications, step J4a. Acceptance — a live run on your Mac, as for v4.12.0.
3. **v4.13.1 «Повний доступ»** — the local bridge and writing edits from the app. Only if the measurement shows that the organization allows it, and after a repeated security audit.
4. **PM OS** on the same shell — a separate thread, its own profile `pm-os`.

**The measurement, 26.11, Mac (darwin/arm64), Claude 8.9912.0:** everything works, full access is allowed in the organization's account.

| What | Result |
| --- | --- |
| Installing the app | yes |
| The permissions notifications, menu-bar, full-access | all granted |
| Notifications, the menu-bar item, the badge | work |
| Files and commands | sees `~/.grow-pm`, runs python3 (3.9.6) |
| Data from the artifact's database | the app sees it |
| A new version of the page | the app picked it up itself after reopening; the permissions back in the state «ask» |
| The app's icon | not written into the already installed copy (`written: false`), to be checked after a reinstall |
| Asking three permissions in one call | hung; one at a time — works. The shell asks the permissions only one at a time and with a timeout |

A lesson for the interface: the buttons of the test page did not show that they had worked. In the shell every action shows its state at once: the button «виконується…», then a short message «Готово» or the reason of the refusal in words.

After your «так» this design goes into the repository beside the release plan.
