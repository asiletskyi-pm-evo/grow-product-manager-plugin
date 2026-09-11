# product-landscape (v3.3.0) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A registry of products/apps/sites (scan the user's machine, discover competitors and adjacent products, categorise, characterise, map) that feeds cross-product research through flow-walkthrough, product-research and brainstorm-features, plus six optional research connectors.

**Architecture:** New skill `skills/product-landscape/` with modes scan / discover / add / update / characterize / map / research over a shared registry `~/.grow-pm/landscape/` (registry.yaml + products/<slug>.md); `scripts/landscape_scan.sh` lists installed Mac apps, iPhone apps on the Mac and adb packages as JSON lines; six URL-matched optional connectors in `.mcp.json`; consumers (product-research, flow-walkthrough, cjm-research, brainstorm-features, plugin-configurator) read the registry, auto-register products they touch, and offer landscape runs.

**Tech Stack:** Markdown skills/references, POSIX sh scan script, public iTunes Search/Lookup API (no auth), existing Python linters, git.

**Spec:** `docs/superpowers/specs/2026-09-11-product-landscape-design.md` (UK mirror `.uk.md`)

## Global Constraints

- Plugin version **3.2.0 → 3.3.0** in the six bump places; manifests and README must state **31 skills** and **12 connectors** (validate-consistency check 10 greps `"$N_CONNECTORS connectors"`); historical "New in" paragraphs keep their old counts.
- New skill frontmatter: `name: product-landscape`, `version: 0.1.0`, routing guard ("Not …") inside the first 192 characters, then UA keywords, EN triggers, chains.
- Skill bumps (patch): `product-research` 0.10.5 → 0.10.6, `flow-walkthrough` 0.2.0 → 0.2.1, `cjm-research` 0.7.5 → 0.7.6, `brainstorm-features` 0.10.2 → 0.10.3, `plugin-configurator` 2.9.4 → 2.9.5 (README lines follow).
- Registry vocabulary (exact strings): roles `direct-competitor | adjacent | benchmark | inspiration`; status `candidate | confirmed | auto | archived`; kinds `app | site | desktop | service`; source types `scan-mac | scan-adb | bookmarks | appstore-api | play-web | websearch | similarweb | semrush | lazyweb | mobbin | apify | user`.
- Connector keys and URLs (exact): `lazyweb` https://www.lazyweb.com/mcp · `similarweb` https://mcp.similarweb.com/ · `mobbin` https://api.mobbin.com/mcp · `semrush` https://mcp.semrush.com/claude/v1/mcp · `tavily` https://mcp.tavily.com/mcp · `apify` https://mcp.apify.com — all `type: http`, no headers, no tokens.
- No Cyrillic in fenced code blocks under `references/`, `skills/`, `templates/`; placeholders only; never a token; bookmarks are read only after an explicit per-scan "yes" and never copied raw.
- `python3 testing/skill_lint.py` GREEN after every task; `bash testing/validate-consistency.sh` green by Task 6; commits end with the Co-Authored-By line.

---

### Task 1: Six optional connectors

**Files:** `.mcp.json`, `references/integration-strategy.md` (1a table + a new paragraph after "Not declared on purpose"), `README.md` line "**Connectors — `.mcp.json` (6).**", `testing/skill_lint.py` (vocabulary).

- [ ] **Step 1: `.mcp.json`** — append after `fireflies` the six entries, and extend `_comment` with: "Since v3.3.0 six OPTIONAL research connectors are declared (lazyweb, similarweb, mobbin, semrush, tavily, apify): URL-matched, each user connects their own account/key in the host; every skill works without them."
- [ ] **Step 2: integration-strategy 1a** — six table rows: `| \`lazyweb\` | Lazyweb | \`mcp__lazyweb__*\` (measured, Cowork 2026-09-10) | TBD | \`lazyweb_health\` |`, `| \`similarweb\` | Similarweb | TBD | TBD | \`get-websites-website-rank\` |`, `| \`mobbin\` | Mobbin | TBD | TBD | \`search_screens\` |`, `| \`semrush\` | Semrush | TBD | TBD | \`domain_overview\` |`, `| \`tavily\` | Tavily | TBD | TBD | \`tavily_search\` |`, `| \`apify\` | Apify | TBD | TBD | \`search-actors\` |`. After the "Not declared on purpose" paragraph add "**Optional research connectors (v3.3.0).** `lazyweb`, `similarweb`, `mobbin`, `semrush`, `tavily`, `apify` are declared so the Connectors tab shows them, but no skill requires them: `product-landscape` and `flow-walkthrough` say in one line which optional sources are present and continue without the rest. Each is a paid or account service the user registers for; keys live in the host's connector configuration, never in the plugin. `tavily` matters on hosts without a built-in web search (Codex, ChatGPT); `apify` is the only route to Google Play charts and reviews."
- [ ] **Step 3: README line 734** — `(6)` → `(12)`, and append: "Since v3.3.0 six **optional** research connectors are declared as well — `lazyweb`, `similarweb`, `mobbin`, `semrush`, `tavily`, `apify` — used by `product-landscape` and `flow-walkthrough` when present, never required; each is your own account."
- [ ] **Step 4: lint vocabulary** — add `"direct-competitor", "scan-mac", "scan-adb", "appstore-api", "play-web"` to KNOWN_NON_SKILL_TOKENS (comment: product-landscape roles and source types).
- [ ] **Step 5** — `bash testing/validate-consistency.sh` (check 9 must pass; check 10 will fail until Task 6 — expected) → commit `feat(connectors): six optional research connectors (lazyweb, similarweb, mobbin, semrush, tavily, apify)`.

---

### Task 2: Storage, vault type, template

**Files:** `references/persistent-storage.md` (tree after `walkthroughs/`), `references/vault-schema.md` (row after `walkthrough`, TYPE_FOLDER_MAP, filename table, "35 artifact types" → 36 ×2), `references/vault-protocol.md` (skill→types table: `product-landscape | landscape, competitive-analysis, ux-benchmark`), `templates/built-in/research/landscape-v1.md`.

- [ ] **Step 1** — tree line: `├── landscape/                    # product-landscape registry: registry.yaml, products/<slug>.md, scans/, maps/`.
- [ ] **Step 2** — vault row `| landscape | product-landscape | Research/landscape/ | Category map of competitors and adjacent products (registry stays local in ~/.grow-pm/landscape/) |`; map entry `"landscape": "Research/landscape/",`; filename row `| landscape | \`landscape-shopping-apps-xx-2026-09-11.md\` | Category and market mapped |`; counts 35 → 36.
- [ ] **Step 3: template** — `template_id: research-builtin-landscape`, `subtype: landscape`, variables `category` (string), `market` (string), `our_product` (string), `products` (list), `sources` (list); body: `# Landscape: {{category}} — {{market}}`; §1 Scope; §2 Product table (`| Product | Kind | Role | Platforms | Walkable surfaces | Size signals | Key flows | Notable | Last researched |`); §3 Us vs them (our product highlighted); §4 Gaps and opportunities; §5 Candidates for research (not researched in 12 months first); §6 Sources; trailing marker `<!-- template: research-builtin-landscape version: 1.0.0 -->`; `min_plugin_version: "3.3.0"`.
- [ ] **Step 4** — lint GREEN → commit `feat(storage): landscape registry folder, vault type landscape, research/landscape-v1 template`.

---

### Task 3: `scripts/landscape_scan.sh`

**Files:** create `scripts/landscape_scan.sh` (executable).

- [ ] **Step 1: script** — POSIX sh, fail-open (exit 0), prints one JSON line per candidate `{"source":"scan-mac|scan-iphone-on-mac|scan-adb|bookmarks","name":…,"bundle_id":…,"path":…,"domain":…}`:

```sh
#!/bin/sh
# landscape_scan.sh — candidates for the product-landscape registry, one JSON line each.
# Sources: Mac apps in /Applications (scan-mac), iPhone apps installed from the Mac App Store
# (scan-iphone-on-mac: /Applications/*.app/Wrapper/*.app), packages of an attached Android
# device (scan-adb), and — ONLY with --bookmarks, i.e. after the user said yes in this scan —
# Chrome/Safari bookmark domains (bookmarks). Never reads browser history. Fail-open: exit 0.
want_bm=0; [ "${1:-}" = "--bookmarks" ] && want_bm=1
esc() { printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'; }
bid() { defaults read "$1/Info.plist" CFBundleIdentifier 2>/dev/null; }
for app in /Applications/*.app; do
  [ -d "$app" ] || continue
  name=$(basename "$app" .app)
  if [ -d "$app/Wrapper" ]; then
    inner=$(ls -d "$app/Wrapper/"*.app 2>/dev/null | head -1)
    printf '{"source":"scan-iphone-on-mac","name":"%s","bundle_id":"%s","path":"%s"}\n' "$(esc "$name")" "$(esc "$(bid "$inner")")" "$(esc "$app")"
  else
    printf '{"source":"scan-mac","name":"%s","bundle_id":"%s","path":"%s"}\n' "$(esc "$name")" "$(esc "$(bid "$app")")" "$(esc "$app")"
  fi
done
adb=$(command -v adb 2>/dev/null); [ -z "$adb" ] && [ -x "$HOME/Library/Android/sdk/platform-tools/adb" ] && adb="$HOME/Library/Android/sdk/platform-tools/adb"
if [ -n "$adb" ] && [ "$("$adb" devices 2>/dev/null | awk 'NR>1 && $2=="device"' | wc -l | tr -d ' ')" = "1" ]; then
  "$adb" shell pm list packages -3 2>/dev/null | sed 's/^package://' | while read -r pkg; do
    printf '{"source":"scan-adb","name":"%s","bundle_id":"%s","path":""}\n' "$(esc "$pkg")" "$(esc "$pkg")"
  done
fi
if [ "$want_bm" = "1" ]; then
  ch="$HOME/Library/Application Support/Google/Chrome/Default/Bookmarks"
  [ -f "$ch" ] && python3 - "$ch" <<'PY' 2>/dev/null
import json,sys,re
def walk(n):
    if isinstance(n,dict):
        u=n.get("url")
        if u:
            m=re.match(r"https?://([^/]+)",u)
            if m: print(json.dumps({"source":"bookmarks","name":n.get("name",""),"bundle_id":"","path":"","domain":m.group(1)}, ensure_ascii=False))
        for c in n.get("children",[]): walk(c)
d=json.load(open(sys.argv[1]))
for r in d.get("roots",{}).values(): walk(r)
PY
  sf="$HOME/Library/Safari/Bookmarks.plist"
  [ -f "$sf" ] && plutil -convert json -o - "$sf" 2>/dev/null | python3 -c '
import json,sys,re
def walk(n):
    if isinstance(n,dict):
        u=n.get("URLString")
        if u:
            m=re.match(r"https?://([^/]+)",u)
            if m: print(json.dumps({"source":"bookmarks","name":n.get("URIDictionary",{}).get("title",""),"bundle_id":"","path":"","domain":m.group(1)}, ensure_ascii=False))
        for c in n.get("Children",[]): walk(c)
try: walk(json.load(sys.stdin))
except Exception: pass' 2>/dev/null
fi
exit 0
```

- [ ] **Step 2** — `sh -n`, `chmod +x`, run without flags on the dev machine: expect ≥ 49 `scan-iphone-on-mac` lines with bundle ids (the marketplace app among them) and Mac apps; every line must parse as JSON (`python3 -c 'import sys,json; [json.loads(l) for l in sys.stdin]'`). Commit `feat(scripts): landscape_scan.sh — Mac apps, iPhone apps on the Mac, adb packages, consent-gated bookmarks`.

---

### Task 4: Skill `product-landscape` + example

**Files:** create `skills/product-landscape/SKILL.md`, `skills/product-landscape/examples/shopping-category-scan.md`.

- [ ] **Step 1: SKILL.md** — frontmatter description (≤1024 chars): `Registry and map of competitor, adjacent and benchmark products — scan installed apps, discover by category and market, categorise, characterise, and start the same-flow research across products. Not a single competitive report (product-research), not a curated source library (knowledge-library), not the walk itself (flow-walkthrough). UA — «карта конкурентів», «реєстр продуктів», «просканируй мої застосунки», «хто конкуренти й дотичні у сфері …», «додай продукт у реєстр», «досліди однакове флоу на конкурентах». EN — "competitor map", "product registry", "scan my apps", "who are the competitors and adjacent players", "add product to the registry", "research the same flow across products". Modes scan / discover / add / update / characterize / map / research; chains to flow-walkthrough, product-research, brainstorm-features.` Body sections: Path rule; Integration prerequisite (free baseline: App Store lookup/search API via SHELL `curl https://itunes.apple.com/lookup?bundleId=…&country=<primary market>` and `…/search?term=…&genreId=…&country=…&entity=software`, Play pages via browser tools, WebSearch when the host has it; optional connectors observed by tool pattern `mcp__*__lazyweb_*`, `*similarweb*`, `*mobbin*`, `*semrush*`, `*tavily*`, `*apify*` — say in one line which are present; data-policy: registry local, bookmarks never copied raw, competitors read-only); Local context (products, `product.category`, `product.competitors`, `primary_market`, `user.language`; storage root; consent setting `landscape.bookmarks_consent: ask | never`); Step T (`artifact_type: research`, `subtype: landscape` for `map` only); Step 1 Mode (table from the spec §3.2); Step 2 Sources present (one line); Step 3 per mode — **scan** (run `scripts/landscape_scan.sh`, add `--bookmarks` only after an explicit yes in this session; group by source; for each bundle id call the App Store lookup for genre/rating/count/seller; rank by genre match to `product.category`; present batches of 10–15 with proposed role; the user confirms / re-roles / drops), **discover** (App Store search by genre id + country, top charts via `apify` when present, similar sites via `similarweb`, `semrush` `competitors_research` by domain, Lazyweb/Mobbin product lists, web search; dedupe by domain and bundle id; batches), **add/update/characterize** (one record; characterize from the store listing, product page, Lazyweb/Mobbin flows, web; every fact with a source), **map** (render the template; highlight the user's product; stale = `last_researched` older than 12 months or null), **research** (rank candidates: role weight direct 3 / benchmark 2 / adjacent 1 / inspiration 1, + category match, + `ios_ratings_count` band, + walkable surfaces, − researched in the last 90 days; show the ranked list with reasons, **no cap**; the user picks any subset or names others (auto-registered as `status: auto`); then chain per spec: flow-walkthrough compare (read-only on competitors), product-research (registry as competitor list), brainstorm-features (hypotheses with registry refs); write back `last_researched`, `walkthroughs[]`); Step 4 Write (registry.yaml index + products/<slug>.md, scans/<date>-<source>.yaml with decisions); Step 5 Vault save (`type: "landscape"` for maps); Skill Chaining (→ flow-walkthrough, product-research, brainstorm-features, cjm-research; ← product-research, flow-walkthrough, cjm-research, brainstorm-features, plugin-configurator); Quality standards (nothing confirmed without the user; every record has ≥1 source; roles per user product, never global; competitor products read-only). Include the record frontmatter from the spec as a code block (English values only).
- [ ] **Step 2: example** — `examples/shopping-category-scan.md`: a Mac with ~50 shopping apps from the App Store → scan output sample (3 JSON lines with placeholder bundle ids), lookup results (genre Shopping, ratings), one confirmation batch table (10 rows: name, proposed role, category, walkable surfaces, decision), a discover pass for the category and market, a map excerpt, a research proposal list (7 candidates ranked with reasons, "pick any or name others").
- [ ] **Step 3** — lint GREEN → commit `feat(skill): product-landscape v0.1.0 — registry, scan, discover, characterize, map, research initiation`.

---

### Task 5: Consumers

**Files:** `skills/plugin-configurator/SKILL.md` + `references/onboarding-steps.md` + `references/context-schema.md` (Landscape section + deferred id `landscape`), `skills/product-research/SKILL.md`, `skills/flow-walkthrough/SKILL.md`, `skills/cjm-research/SKILL.md`, `skills/brainstorm-features/SKILL.md`, `references/local-context-protocol.md` (line 192), `README.md` (version lines).

- [ ] **Step 1: configurator** — context-schema: `### Landscape section format` → `## Landscape` with `- bookmarks_consent: ask | never` and per product `- category: <App Store / Play genre or free tag>`; deferred row `| \`landscape\` | Landscape setup | Landscape (bookmarks consent, product category, competitors import) |`; onboarding add-on "Step — Landscape setup (Extended, since v3.3.0)": consent default, product category seed, import `product.competitors` into the registry as `direct-competitor` candidates (calls product-landscape `add`), standalone `add Landscape` / `налаштуй карту конкурентів`; SKILL.md bullet + UA keyword «налаштуй карту конкурентів»; version 2.9.5.
- [ ] **Step 2: product-research** — in Step 1 (discovery) add: "Competitor list: read `~/.grow-pm/landscape/registry.yaml` links for the active product (roles `direct-competitor`, `benchmark`) when the registry exists, else `product.competitors`; competitors found during research are registered through **Product Landscape** `add` with `status: auto` and source `websearch`/`appstore-api`." Chaining: `→ **Product Landscape** — "Map this category and pick products for a hands-on comparison"`. Version 0.10.6.
- [ ] **Step 3: flow-walkthrough** — Step 4 compare: "Candidates come from the landscape registry (walkable `surfaces` decide the surface); every walked product is registered (`status: auto`, `walkthroughs[]` updated) via **Product Landscape** `add`/`update`." Step 5 audit: "a Lazyweb/Mobbin reference the user acts on registers that product as `inspiration`." Chaining line `→ **Product Landscape** — "Register this product / propose more products for the same flow"`; `← \`product-landscape\` (research mode picks candidates and starts compare)`. Version 0.2.1.
- [ ] **Step 4: cjm-research, brainstorm-features** — one chaining line each: `→ **Product Landscape** — "Run the same stage / idea hunt on the landscape products"`; brainstorm-features Step (idea sources) adds "registry records as evidence, cite `landscape:<slug>`". Versions 0.7.6 / 0.10.3.
- [ ] **Step 5: local-context-protocol line 192** → `- Use \`product.competitors\` when building comparison matrices (always include user's product); since v3.3.0 prefer the landscape registry links (\`~/.grow-pm/landscape/registry.yaml\`, roles direct-competitor / benchmark) when it exists — \`product.competitors\` is the seed the registry imported.`
- [ ] **Step 6** — README version lines; lint GREEN (chain-contracts satisfied both ways) → commit `feat(chains): wire product-landscape into configurator, product-research, flow-walkthrough, cjm-research, brainstorm-features`.

---

### Task 6: Release chores v3.3.0

**Files:** three manifests, `README.md`, `CHANGELOG.md`, `AGENTS.md`, `testing/host-matrix.md`, `testing/trigger-evals.md` (Group O), `testing/test-cases.md`.

- [ ] manifests: `3.3.0`, `31 skills`, `12 connectors`, description adds `product landscape registry (scan, discover, map, cross-product research)`, tail `— v3.3.0 (released 2026-09-11)`; `.codex-plugin` longDescription `31 skills`.
- [ ] README: header/footer 3.3.0; "New in v3.3.0" paragraph (31 skills, 3 agents, 5 commands, 12 connectors, 2 hooks); `### 31. Product Landscape (v0.1.0) — NEW in v3.3.0` section before "Skills Summary"; summary row; `## 30 skills`-style counts → 31 where the current state is stated (`grep -n "30 skills"` and fix only non-historical lines); seed templates 25 → 26 + list line `research/landscape-v1`.
- [ ] CHANGELOG `## v3.3.0 (2026-09-11)`: Added (skill, registry, scan script, template + vault type, six optional connectors, Landscape setup, Group O), Changed (five patch bumps; competitors derived from the registry), Not in this version (periodic re-scans, price monitoring, review sentiment, Play install automation), Backwards compatibility (no registry → skills behave as before; connectors optional).
- [ ] AGENTS.md row: `| \`skills/product-landscape\`, \`scripts/landscape_scan.sh\`, \`~/.grow-pm/landscape/\` | the product registry and the machine scan behind it |`. host-matrix row: `| \`product-landscape\` | full | degraded | degraded | degraded | scan needs SHELL (else the user pastes the app list); optional connectors observed per session; storage: session mode, export at the end |`.
- [ ] trigger-evals Group O (8): O1 «просканируй мої застосунки і скажи, які з них конкуренти» → product-landscape; O2 «хто конкуренти й дотичні у сфері онлайн-покупок» → product-landscape; O3 «додай продукт у реєстр конкурентів» → product-landscape; O4 «досліди однакове флоу оформлення замовлення на конкурентах» → product-landscape; O5 «досліди конкурентів для картки товару» → product-research; O6 «які джерела маємо по Q&A» → knowledge-library; O7 «пройди флоу відгуку в застосунку» → flow-walkthrough; O8 «налаштуй карту конкурентів» → plugin-configurator.
- [ ] test-cases: TC-product-landscape-scan-1 (script + lookup + batches, bookmarks only after yes), -discover-1, -map-1, -research-1 (no cap, user picks, auto-register), TC-product-research-regression-3 (no registry → `product.competitors`).
- [ ] validate + lint green → commit `chore(release): v3.3.0 — product-landscape, optional research connectors`.

---

### Task 7: Acceptance

- [ ] seeded-leak, host-smoke both hosts, Group O via `claude -p` (log), scan script on the dev machine (count lines, JSON parse), App Store lookup for 3 scanned bundle ids.
- [ ] Real run of `scan` on the dev machine through the skill: candidates ranked, first batch presented to the user (their confirmation is the only manual part); `discover` for the reference product's category/market; `map` rendered to `~/.grow-pm/landscape/maps/`; `research` proposal list produced (no cap). Record in test-cases.

### Task 8: PR

- [ ] push, `gh pr create` "v3.3.0 — product-landscape registry, optional research connectors", base = main after #50 merges (rebase the branch onto main first).
