# product-landscape — design spec (v3.3.0)

**Date:** 2026-09-11 · **Status:** approved in chat, pending implementation plan · **Target release:** v3.3.0 (after v3.2.0) · Ukrainian mirror: `2026-09-11-product-landscape-design.uk.md` · Related: `2026-09-10-flow-walkthrough-design.md`, `2026-09-11-test-accounts-and-legs-design.md`.

## 1. Problem and goal

The plugin knows the user's competitors as a flat list in `local-context.md` (`product.competitors`). It does not know which apps the user has installed to study, which products are adjacent rather than direct competitors, what each one is (category, platforms, surfaces that can be walked, size), or which of them were already researched. The user studies a whole category (for Prom: dozens of Shopping apps installed from the App Store) and wants the plugin to **scan, discover, categorise, characterise and keep a registry** of products, apps, programs and sites — their own products' competitors and adjacent players — and to **initiate cross-product research** from it: the same flow walked on several products, insights, ideas and hypotheses mined from competitors and adjacent products, on the user's request or as an offer from a skill.

## 2. Decisions taken (with the user)

| # | Decision | Choice |
|---|---|---|
| D1 | Where | new skill `product-landscape` (registry CRUD, scanning, discovery, category map, research initiation); other skills read the registry and *offer* landscape runs, never start them on their own |
| D2 | Shape | one **shared registry** `~/.grow-pm/landscape/` with one record per product/app/site, plus **links** from each of the user's products with a role: `direct-competitor | adjacent | benchmark | inspiration`; `product.competitors` in local-context becomes derived (first run imports it) |
| D3 | Scanning the user's machine | installed Mac apps and iPhone apps from the Mac App Store, a phone/emulator via adb, explicit lists the user gives; **browser bookmarks only with an explicit "yes" in each scan** (Chrome, Safari); browser history never |
| D4 | Discovery sources | free baseline: public App Store lookup/search API (genre, rating, ratings count, seller, Mac availability), Google Play pages via browser tools, WebSearch; optional connectors when present: Similarweb, Semrush, Tavily (search on hosts without WebSearch), Mobbin, Lazyweb, Apify app-data actors (Play/App Store charts, reviews) |
| D5 | Optional connectors declared by the plugin | `.mcp.json` gains six URL-matched entries: `lazyweb`, `similarweb`, `mobbin`, `semrush`, `tavily`, `apify`; each user connects their own account/key in the host; every skill works without them |
| D6 | Candidate selection for research | **no fixed cap**: the skill ranks and proposes the best candidates (role, category match, size, surfaces available, staleness), the user picks any subset or names other products |
| D7 | Auto-registration | any product the plugin interacts with (a walk, a compare, a competitive analysis, a Lazyweb/Mobbin reference the user acts on) is added to the registry as `status: auto` with the source noted; the user can confirm, re-role or archive it later |
| D8 | Confirmation UX | scan/discover results are shown in batches of 10–15 (as the glossary does): the user confirms, re-categorises, sets the role or drops each; nothing enters `status: confirmed` without the user |

Out of v3.3.0: periodic re-scans and change alerts, price monitoring, review-sentiment mining across stores (feedback-triage territory), automatic install of apps, competitor account creation (never).

## 3. Components

### 3.1 Storage — `~/.grow-pm/landscape/` (new in `persistent-storage.md`)

```
landscape/
├── registry.yaml            # index: slug → {name, kind, category, status, links[], updated}
├── products/<slug>.md       # one record per product (frontmatter + notes)
├── scans/<YYYY-MM-DD>-<source>.yaml   # raw scan/discover results, candidate lists, user decisions
└── maps/<category>-<YYYY-MM-DD>.md    # rendered category maps (also the research/landscape artifact)
```

Record frontmatter (`products/<slug>.md`):

```yaml
slug: product-1-competitor-a
name: "Competitor A"
kind: app | site | desktop | service
category: "Shopping"            # App Store / Play genre name or a free tag
subcategory: "marketplace"      # free tag(s)
markets: [xx, yy]               # ISO country codes
developer: "Company A"
platforms: [ios, android, web, macos]
surfaces:                       # what flow-walkthrough can drive
  web_url: https://example.com
  ios_app_id: 000000000
  ios_bundle_id: com.example.app
  mac_available: true | false | unknown
  android_package: com.example.app
  desktop_bundle_id: null
size_signals:
  ios_rating: 4.7
  ios_ratings_count: 120000
  play_rating: null
  similarweb_rank: null         # only when the connector answered
characterization:
  model: "C2C marketplace with escrow"
  audience: "…"
  key_flows: [search, product card, checkout, reviews]
  notable: ["stars first in the review form", "…"]
links:
  - product: product-1           # the user's product slug from local-context
    role: direct-competitor | adjacent | benchmark | inspiration
    note: "…"
sources: [{type: scan-mac | scan-adb | bookmarks | appstore-api | play-web | websearch | similarweb | semrush | lazyweb | mobbin | apify | user, ref: "…", date: 2026-09-11}]
status: candidate | confirmed | auto | archived
first_seen: 2026-09-11
last_researched: null
walkthroughs: []                 # run ids from ~/.grow-pm/walkthroughs
```

Vault type `landscape` → `Research/landscape/` (36 types); built-in template `research/landscape-v1.md` (category map: table of products × characteristics, "us vs them" rows, gaps, candidates for research). Registry data is internal (`data-policy.md`): local only; bookmark files are read, never copied — only chosen candidates are stored.

### 3.2 Skill `skills/product-landscape/SKILL.md` — modes

| Mode | Trigger shape | What happens |
|---|---|---|
| `scan` | "просканируй мої застосунки", "які застосунки я встановив у категорії …", "scan my apps" | `scripts/landscape_scan.sh` lists Mac apps (`/Applications/*.app`, bundle id), iPhone apps on the Mac (`/Applications/*.app/Wrapper/*.app/Info.plist`, bundle id), adb packages when a device is attached; bundle ids → App Store lookup (genre, rating, count, seller); Mac apps without a store record → name + category guess; optional bookmarks after per-scan consent → domains; candidates ranked by category match to the user's products; batches of 10–15 for confirmation (D8) |
| `discover` | "хто конкуренти й дотичні у сфері …", "find competitors and adjacent products for …" | sources per D4, deduplicated by domain / bundle id, each with a proposed role; the user's own product's category and markets seed the queries; batches for confirmation |
| `add` / `update` / `characterize` | "додай продукт X у реєстр", "охарактеризуй X", "постав X як дотичний до Prom" | CRUD on one record; `characterize` fills `characterization` from the product page, store listing, Lazyweb/Mobbin flows, web — with sources |
| `map` | "карта конкурентів по категорії …", "покажи реєстр" | the `research/landscape` artifact: products × characteristics, the user's product highlighted, gaps, "not researched yet" list; published like product-research or kept local |
| `research` | "досліди однакове флоу на конкурентах", "знайди ідеї у конкурентів для …", or an offer accepted from another skill | ranks candidates (D6) and asks the user to pick or name products; then chains: same flow across the chosen products → **flow-walkthrough** `compare` (competitors read-only; unknown products auto-registered D7); desk comparison → **product-research** (competitive / ux-benchmark with the registry as the competitor list); ideas and hypotheses → **brainstorm-features** with registry references; results write `last_researched` and `walkthroughs[]` back |

Steps: 0 (context + host, APP-DRIVE not required except for `research` walks) → 1 mode → 2 sources available (connectors observed; say in one line which optional sources are present) → 3 run the mode → 4 confirmation batches → 5 write registry + scan file → 6 artifact (map) or chaining. Proactive offers live in the consumer skills (3.4), phrased as chaining lines.

### 3.3 Connectors (`.mcp.json`, `integration-strategy.md`, Setup Guide)

| key | URL | Used for | Without it |
|---|---|---|---|
| `lazyweb` | https://www.lazyweb.com/mcp | product DB, screens, flows, experiments; references per friction in flow-walkthrough audit | skip references |
| `similarweb` | https://mcp.similarweb.com/ | similar sites, traffic rank, audience overlap → discovery + size signals | App Store API + web search only |
| `mobbin` | https://api.mobbin.com/mcp | flows / screens / sections of real apps → characterize, references | skip |
| `semrush` | https://mcp.semrush.com/claude/v1/mcp | `competitors_research`, `domain_overview` → discovery by domain | skip |
| `tavily` | https://mcp.tavily.com/mcp | web search + extract on hosts without WebSearch (Codex, ChatGPT) | Claude WebSearch; on other hosts: user-provided lists |
| `apify` | https://mcp.apify.com | App Store / Google Play charts, rankings, reviews via app-data actors (pay per result) | Play via browser pages |

All six are URL-matched, `type: http`; the user's keys live in the host's connector config, never in the plugin. `integration-strategy.md` 1a table gains six rows (namespace columns "TBD until measured" except `lazyweb`, measured on Cowork 2026-09-10). `validate-consistency.sh` check 9 keeps `.mcp.json` ↔ table in sync; component counts become "12 connectors". Setup Guide: a step "Optional research connectors" (what each gives, that each is a paid/account service the user registers for, how to connect, how to verify).

### 3.4 Consumers and local-context

- **plugin-configurator**: Extended add-on **Landscape setup** — bookmark-scan consent default (`ask each time | never`), import `product.competitors` into the registry as `direct-competitor` candidates on first run, category seed per product (`product.category`, e.g. App Store genre); standalone `add Landscape` / `налаштуй карту конкурентів`.
- **product-research**: the competitor list for comparisons comes from the registry links (role `direct-competitor` + `benchmark`), falling back to `product.competitors`; new competitors found during research are auto-registered (D7); offers `product-landscape research` after a competitive study.
- **flow-walkthrough**: `compare` candidates come from the registry (`surfaces` decide what can be walked); every walked product is auto-registered with `walkthroughs[]` updated; audit references (Lazyweb/Mobbin) can auto-register the referenced product as `inspiration`.
- **cjm-research**, **brainstorm-features**: one chaining offer each — "run the same stage / idea hunt on the landscape products" → `product-landscape research`.
- `references/local-context-protocol.md`: `product.competitors` documented as derived from the registry when the registry exists.
- Scripts: `scripts/landscape_scan.sh` (SHELL hosts; prints one JSON line per candidate: source, name, bundle id / domain, path) — on hosts without SHELL the skill asks the user to paste their app list.

### 3.5 Docs, tests, release

README (new skill #31, "New in v3.3.0", connectors 12), CHANGELOG, three manifests (v3.3.0, 31 skills, 12 connectors), AGENTS.md, host-matrix row, `testing/trigger-evals.md` Group O (landscape phrases vs product-research / knowledge-library / flow-walkthrough), `testing/test-cases.md`, Confluence: new skill article + hubs (catalogue, Overview, Setup Guide connectors step, PM instruction scenario, Changelog).

## 4. Testing

- Lint GREEN (new vault type + template + skill), validate-consistency green (12 connectors), host-smoke both hosts.
- `landscape_scan.sh` on the dev machine: finds the iPhone apps installed from the Mac App Store (49 on 2026-09-11, Shopping-heavy) with bundle ids; App Store lookup fills genre/rating for them.
- Acceptance: `scan` → candidates in batches → confirm a subset with roles; `discover` for the user's product category and market → new candidates; `map` renders the category map; `research` proposes candidates without a cap, the user picks two, flow-walkthrough `compare` runs read-only and both products land in the registry with `walkthroughs[]`.

## 5. Risks

Store and web sources have terms of use — the skill uses official APIs, connectors and normal browser reading, never bulk scraping. Bookmarks are personal: consent per scan, no raw copy. Registry growth: `archived` status and the `status` filter keep proposals relevant; candidates older than 12 months without research are flagged stale in `map`.
