# Example — scan a Mac full of shopping apps, map the category, propose research

Context: the user's product is "Product 1" (a marketplace, category Shopping, market xx). They installed about fifty shopping apps from the Mac App Store to study the category.

## 1. scan

`scripts/landscape_scan.sh` output (excerpt):

```json
{"source":"scan-iphone-on-mac","name":"Competitor A","bundle_id":"com.example.competitor-a","path":"/Applications/Competitor A.app"}
{"source":"scan-iphone-on-mac","name":"Fashion Shop B","bundle_id":"com.example.fashion-b","path":"/Applications/Fashion Shop B.app"}
{"source":"scan-mac","name":"Price Tracker","bundle_id":"com.example.pricetracker","path":"/Applications/Price Tracker.app"}
```

App Store lookup per bundle id (primary market xx): genre, rating, ratings count, seller, app id. Ranking: genre = Shopping first, then ratings count.

First confirmation batch (10 of 49):

| # | Name | Source | Category | Proposed role | Walkable surfaces | Decision |
|---|------|--------|----------|---------------|-------------------|----------|
| 1 | Competitor A | iPhone on Mac | Shopping / marketplace | direct-competitor | iphone-on-mac, web | confirm |
| 2 | Fashion Shop B | iPhone on Mac | Shopping / fashion | adjacent | iphone-on-mac, web | confirm |
| 3 | Global Marketplace C | iPhone on Mac | Shopping / cross-border | benchmark | iphone-on-mac, web | confirm |
| 4 | Grocery D | iPhone on Mac | Shopping / grocery | adjacent | iphone-on-mac | re-role: inspiration |
| 5 | Price Tracker | Mac app | Utilities | — | desktop | drop |
| … | | | | | | |

## 2. discover

App Store search, genre Shopping, market xx, top 50 by ratings count → 12 new candidates not on the machine; `similarweb` similar-sites for the product's domain (when connected) → 4 more; deduplicated by domain / bundle id; second batch presented the same way.

## 3. map (excerpt)

| Product | Kind | Role | Platforms | Walkable surfaces | Size signals | Key flows | Notable | Last researched |
|---------|------|------|-----------|-------------------|--------------|-----------|---------|-----------------|
| Product 1 (ours) | app | — | ios, android, web | iphone-on-mac, web | 4.9 / 480k | search, card, checkout, reviews | rating asked on exit of the review form | 2026-09-11 |
| Competitor A | app | direct-competitor | ios, android, web | iphone-on-mac, web | 4.8 / 1.2M | search, card, checkout, reviews | stars first in the review form | null |
| Global Marketplace C | app | benchmark | ios, android, web | iphone-on-mac, web | 4.7 / 3.5M | … | photo-first reviews | null |

## 4. research proposal (no cap)

| # | Product | Why now | Suggested run |
|---|---------|---------|---------------|
| 1 | Competitor A | direct competitor, same market, never researched, walkable here | flow-walkthrough compare: "leave a review" |
| 2 | Global Marketplace C | benchmark with the largest review volume | flow-walkthrough compare + product-research ux-benchmark |
| 3 | Fashion Shop B | adjacent, strong product-card patterns | product-research competitive (card) |
| 4 | Electronics Retailer E | direct competitor, researched 14 months ago (stale) | flow-walkthrough compare: checkout |
| 5 | Marketplace F (Play only) | direct competitor, Android-only surface | needs adb — setup first |
| 6 | Cross-border G | benchmark, cross-border checkout | brainstorm-features from registry notes |
| 7 | Classifieds H | adjacent, C2C review model | product-research competitive |

"Pick any of these, or name other products — I will register the new ones and start the runs."
