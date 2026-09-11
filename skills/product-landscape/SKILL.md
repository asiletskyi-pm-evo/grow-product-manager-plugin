---
name: product-landscape
version: 0.1.0
description: Registry and map of competitor, adjacent and benchmark products — scan installed apps, discover by category and market, categorise, characterise, start same-flow research across products. Not a single competitive report (product-research), not a source library (knowledge-library), not the walk itself (flow-walkthrough); setup of consent and category is plugin-configurator. UA — «карта конкурентів», «реєстр продуктів», «просканируй мої застосунки», «хто конкуренти й дотичні у сфері …», «додай продукт у реєстр», «досліди однакове флоу на конкурентах». EN — "competitor map", "product registry", "scan my apps", "who are the competitors and adjacent players", "add product to the registry", "research the same flow across products". Modes scan / discover / add / update / characterize / map / research; chains to flow-walkthrough, product-research, brainstorm-features.
---

# Product Landscape

> **Path rule.** A bare `references/<file>.md` in this file is read from this skill's own `references/` if the file exists there, otherwise from the **shared** `references/` at the plugin root. Resolve the root as `${PLUGIN_ROOT}`, else `${CLAUDE_PLUGIN_ROOT}`, else the directory that contains `skills/`, found by walking up from this folder (`references/host-profiles.md` §6). Never continue without a protocol named here.

Keep one registry of the products, apps, programs and sites around the user's products — direct competitors, adjacent players, benchmarks, inspiration — with what each one is, where it can be walked, and when it was last researched. Feed that registry into research: the same flow across several products (`flow-walkthrough` compare), desk comparisons (`product-research`), ideas and hypotheses (`brainstorm-features`). Other skills *offer* landscape runs; only the user starts them.

## Integration prerequisite

Read `references/integration-strategy.md`. Free baseline, always available: the public App Store lookup and search API through SHELL (`curl "https://itunes.apple.com/lookup?bundleId=<id>&country=<market>"` and `curl "https://itunes.apple.com/search?term=<query>&genreId=<genre>&country=<market>&entity=software&limit=50"`), Google Play pages through browser tools, web search when the host has it. Optional sources, observed by tool pattern and stated in one line at the start of the run: Lazyweb (`mcp__*__lazyweb_*`), Similarweb (`*similarweb*`), Mobbin (`*mobbin*`), Semrush (`*semrush*`), Tavily (`*tavily*`), Apify (`*apify*`) — declared optional connectors per `references/integration-strategy.md` 1a; the run continues without any of them.

Read `references/data-policy.md`: the registry is internal data (local only); browser bookmark files are read only after an explicit "yes" in the current scan and are never copied — only chosen candidates are stored; competitor products are read-only in every downstream run (`references/app-drive-protocol.md` §5).

## Local context prerequisite

**Before starting, follow `references/local-context-protocol.md` (Step 0).** Then `references/host-profiles.md` §3 (SHELL decides whether `scan` runs the script or asks the user to paste their app list; APP-DRIVE matters only for `research` runs that walk).

Key context used by this skill: the user's products (`product.name`, `product.category`, `product.primary_market`, `product.platforms`, `product.competitors` as the seed), `landscape.bookmarks_consent` (`ask` | `never`), `user.language`, `storage_root`.

## Storage — `{storage_root}/landscape/`

```
landscape/
├── registry.yaml            # index: slug -> {name, kind, category, status, links[], updated}
├── products/<slug>.md       # one record per product (frontmatter + notes)
├── scans/<YYYY-MM-DD>-<source>.yaml   # raw scan/discover results, candidates, user decisions
└── maps/<category>-<YYYY-MM-DD>.md    # rendered maps (the research/landscape artifact)
```

Record frontmatter (`products/<slug>.md`):

```yaml
slug: competitor-a
name: "Competitor A"
kind: app                    # app | site | desktop | service
category: "Shopping"         # store genre name or a free tag
subcategory: "marketplace"
markets: [xx]
developer: "Company A"
platforms: [ios, android, web]
surfaces:
  web_url: https://example.com
  ios_app_id: 000000000
  ios_bundle_id: com.example.app
  mac_available: unknown     # true | false | unknown — the App Store page lists Mac under Compatibility
  android_package: com.example.app
  desktop_bundle_id: null
size_signals: {ios_rating: 4.7, ios_ratings_count: 120000, play_rating: null, similarweb_rank: null}
characterization:
  model: "C2C marketplace with escrow"
  audience: "buyers in market xx"
  key_flows: [search, product card, checkout, reviews]
  notable: ["stars first in the review form"]
links:
  - {product: product-1, role: direct-competitor, note: "same category, same market"}
sources: [{type: scan-iphone-on-mac, ref: "/Applications/Competitor A.app", date: 2026-09-11}, {type: appstore-api, ref: "lookup bundleId", date: 2026-09-11}]
status: candidate            # candidate | confirmed | auto | archived
first_seen: 2026-09-11
last_researched: null
walkthroughs: []
```

Roles are **per user product** (`links[].product`), never global: the same app may be a direct competitor of one product and adjacent to another. No FS → the registry lives in the chat for the session and is exported at the end (`references/persistent-storage.md`).

## Step T — Template Resolution (map only)

For `map`: `artifact_type: research`, `subtype: landscape`, built-in fallback `builtin://research/landscape-v1.md`. Other modes produce no document artifact.

## Step 1 — Mode

| Mode | Trigger shape | Output |
|---|---|---|
| `scan` | "scan my apps", "what did I install in category …" | candidates from the user's machine, confirmed in batches |
| `discover` | "who are the competitors and adjacent players in …" | candidates from stores, web and connectors, confirmed in batches |
| `add` / `update` / `characterize` | "add X to the registry", "characterize X", "set X as adjacent to <product>" | one record written or updated |
| `map` | "competitor map for category …", "show the registry" | the `research/landscape` artifact |
| `research` | "research the same flow on competitors", "find ideas at competitors for …", or an accepted offer from another skill | ranked candidate list → the user picks → chained runs |

A request phrased as setup — "set up the competitor map", "налаштуй карту конкурентів", consent or category questions — is **Landscape setup** in `plugin-configurator`: hand over there instead of starting a scan.

## Step 2 — Sources present

One line: which optional connectors are in the session, whether SHELL is present (script vs pasted list), whether the registry exists and how many records it holds.

## Step 3 — Run the mode

**scan.** Run `scripts/landscape_scan.sh` (add `--bookmarks` **only** after the user answered "yes" to "May I read your Chrome/Safari bookmarks for this scan?" — skip the question when `landscape.bookmarks_consent: never`). Group by source. For every bundle id call the App Store lookup for the primary market (genre, rating, ratings count, seller, app id); for Mac apps without a store record keep name + a category guess; for bookmark domains keep the domain only. Rank by genre match with `product.category`, then ratings count. Present **batches of 10–15** — name, source, category, proposed role, walkable surfaces — and for each the user confirms, changes the role or category, or drops it. Confirmed → `status: confirmed`; the rest are kept in the scan file as `dropped`, never in `products/`.

**discover.** Seed with the user's product category and primary market. Sources in order: App Store search by genre id + country (and the market's top charts through `apify` when present), Google Play category pages through browser tools, similar sites through `similarweb` and `semrush` `competitors_research` by the product's domain, Lazyweb/Mobbin product lists, web search (built-in, or `tavily` on hosts without it). Deduplicate by domain and bundle id against the registry; propose a role; present batches as in `scan`.

**add / update / characterize.** One record. `characterize` fills `characterization` from the store listing, the product page, Lazyweb/Mobbin flows and web — every fact carries a source; a claim without a source is a note, not a field. `mac_available` comes from the App Store page's Compatibility list.

**map.** Render the template: all confirmed and auto records linked to the chosen product (or category), the user's product highlighted, gaps, and a candidates-for-research list; a record is **stale** when `last_researched` is null or older than 12 months. Publish like product-research or keep in `maps/`.

**research.** Rank candidates: role weight (direct-competitor 3, benchmark 2, adjacent 1, inspiration 1) + category match + ratings-count band + walkable surfaces available on this machine − researched in the last 90 days. Show the whole ranked list with one reason per line — **no cap**; the user picks any subset or names other products (unknown ones are registered as `status: auto`, source `user`). Then chain:

- same flow across products → **flow-walkthrough** `compare` (competitors `read-only`; every walked product is updated with `walkthroughs[]`);
- desk comparison → **product-research** (competitive / ux-benchmark with the picked products as the competitor list);
- ideas and hypotheses → **brainstorm-features**, citing `landscape:<slug>` as evidence.

Write back `last_researched` on every product touched.

## Step 4 — Write the registry

Update `registry.yaml` (index) and `products/<slug>.md`; append the run to `scans/<date>-<mode>.yaml` with candidates and the user's decisions. Any product the plugin interacts with anywhere (a walk, a compare, a competitive analysis, a Lazyweb/Mobbin reference the user acts on) is registered with `status: auto` and the source; the user confirms, re-roles or archives later.

## Step 5 — Save to Vault (map only, optional)

> Requires: `references/vault-protocol.md` → Vault Save

IF vault_level > L0 AND sync_mode != "off": `vault_save({ type: "landscape", product: active_product, skill: "product-landscape", skill_version: "0.1.0", tags: [category, market], content: the map, related: [registry slugs] })`. Display: "Saved to Vault: Research/landscape/{product}/…".

## Skill Chaining

- → **Flow Walkthrough** — "Walk [flow] on the picked products (compare)"
- → **Product Research** — "Competitive / UX-benchmark study with these products"
- → **Brainstorm Features** — "Hypotheses from what the landscape products do differently"
- → **CJM Research** — "Use the landscape for stage benchmarks"
- ← `product-research` (competitor list from the registry; new competitors registered as auto)
- ← `flow-walkthrough` (compare candidates; walked products registered)
- ← `cjm-research` and `brainstorm-features` (offer a landscape run)
- ← `plugin-configurator` (Landscape setup imports `product.competitors`)

## Quality standards

- Nothing becomes `confirmed` without the user; every record has at least one source.
- Roles are per user product; the user's own products are never registry records.
- Bookmarks: consent per scan, domains only, nothing copied raw.
- Competitor products are read-only in every downstream run.
- Output language from `user.language`.

## Example

`examples/shopping-category-scan.md` — a scan of a Mac with ~50 shopping apps from the App Store, one confirmation batch, a discover pass, a map excerpt and a research proposal list.
