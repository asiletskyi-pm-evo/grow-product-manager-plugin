# Local Context — fictional Zorg (journey fixture)

> Configurator version: 1.36.0
> Generated: 2026-11-01 · Updated: 2026-11-01

## User

- **Language:** uk
- **Role:** pm

## Organization: Zorg

### Product: Zorg Market

- category: Shopping

#### CJM Configuration

> Zorg's funnel, fictional: five stages, thresholds 10 / 25 %.

##### Funnel Template
- Template: marketplace

##### Funnel Stages
| Stage | Name | Dashboard | Baseline conversion |
|---|---|---|---|
| 1 | Візит | zorg-dash/visit | visit -> search 45% |
| 2 | Пошук | zorg-dash/search | search -> cart 35% |
| 3 | Кошик | zorg-dash/cart | cart -> checkout 50% |
| 4 | Оформлення | zorg-dash/checkout | checkout -> payment 72% |
| 5 | Оплата | zorg-dash/payment | payment -> order 90% |

##### Thresholds
- Warning: 10%
- Critical: 25%

### Team: Zorg Checkout (ZC)

## Terminology & Style (team language)

#### Settings
- lint_mode: suggest
