# Funnel Templates

This document defines standard funnel stage templates by product type. Used by `cjm-research` and `plugin-configurator` (CJM onboarding).

> **Important**: The skill MUST always communicate to the user which template is being used:
> "For this analysis I'm using the **[template name]** template with stages: [stage list]."
>
> The user can change the template at any time during a CJM session or via Plugin Configurator.

---

## Available Templates

### E-commerce

The default template for online retail, marketplaces with product catalogs, and transactional platforms.

| Stage | Name | Typical metrics | Recommended anomaly thresholds |
|-------|------|----------------|-------------------------------|
| 1 | Start / Listing | Sessions, page views, bounce rate, search usage rate | Warning: 10%, Critical: 25% |
| 2 | Product Page | PDP view rate, add-to-cart rate, time on page, image interactions | Warning: 10%, Critical: 25% |
| 3 | Cart / Checkout | Cart abandonment rate, checkout start rate, form completion rate | Warning: 8%, Critical: 20% |
| 4 | Payment / Post-Purchase | Payment success rate, order completion rate, return rate | Warning: 5%, Critical: 15% |

**Typical dashboard mapping:**
- Stage 1: Traffic / acquisition dashboard
- Stage 2: Product engagement dashboard
- Stage 3: Cart / checkout funnel dashboard
- Stage 4: Revenue / transactions dashboard

---

### SaaS

For subscription-based software products with trial/freemium flows.

| Stage | Name | Typical metrics | Recommended anomaly thresholds |
|-------|------|----------------|-------------------------------|
| 1 | Awareness | Website visits, landing page conversion, signup page views | Warning: 10%, Critical: 25% |
| 2 | Signup / Trial | Registration rate, trial start rate, email verification rate | Warning: 10%, Critical: 20% |
| 3 | Activation | Onboarding completion, key action completion (aha moment), time-to-value | Warning: 10%, Critical: 25% |
| 4 | Engagement | DAU/MAU ratio, feature adoption, session frequency, retention D7/D30 | Warning: 10%, Critical: 20% |
| 5 | Conversion | Trial-to-paid rate, upgrade rate, plan selection distribution | Warning: 8%, Critical: 20% |
| 6 | Retention | Churn rate, renewal rate, NPS, expansion revenue | Warning: 5%, Critical: 15% |

**Typical dashboard mapping:**
- Stages 1-2: Acquisition / growth dashboard
- Stage 3: Activation / onboarding dashboard
- Stages 4-5: Product usage / engagement dashboard
- Stage 6: Retention / revenue dashboard

---

### Marketplace

For two-sided or multi-sided platforms connecting buyers and sellers/providers.

| Stage | Name | Typical metrics | Recommended anomaly thresholds |
|-------|------|----------------|-------------------------------|
| 1 | Search / Browse | Search query rate, filter usage, browse-to-listing rate | Warning: 10%, Critical: 25% |
| 2 | Listing Page | Listing view rate, contact/inquiry rate, save/favorite rate | Warning: 10%, Critical: 25% |
| 3 | Contact / Booking | Message rate, booking initiation rate, form submission rate | Warning: 8%, Critical: 20% |
| 4 | Transaction | Transaction completion rate, payment success rate, GMV per transaction | Warning: 5%, Critical: 15% |
| 5 | Review / Repeat | Review submission rate, repeat usage rate, time-to-repeat | Warning: 10%, Critical: 25% |

**Notes:**
- Marketplace funnels often need to be analyzed separately for each side (buyer vs seller)
- The skill should ask which side to analyze, or run both and compare

**Typical dashboard mapping:**
- Stage 1: Search / discovery dashboard
- Stage 2: Listing performance dashboard
- Stage 3: Lead / booking dashboard
- Stage 4: Transactions / revenue dashboard
- Stage 5: Retention / loyalty dashboard

---

### Custom

The user defines stages entirely from scratch. This template is used when:
- The product type doesn't match any preset
- The user has a unique funnel structure
- The user wants to analyze a sub-funnel (e.g., only the checkout flow in detail)

**Collection flow (during onboarding or CJM setup):**

1. Ask: "How many stages does your funnel have?"
2. For each stage, collect:
   - Stage name
   - Key metrics (at least 1)
   - Dashboard URL (optional)
   - Anomaly thresholds (offer defaults: Warning 10%, Critical 25%)
3. Confirm the complete funnel with the user before saving

**Custom templates are saved** in the CJM Configuration section of `local-context.md` and can be reused across sessions.

---

## Template Management

### Switching templates

The user can switch templates at any time:
- During CJM onboarding: "I want to use the SaaS template instead"
- During a CJM research session: "Switch to custom stages"
- Via Plugin Configurator Update mode: modify CJM Configuration section

When switching templates, the skill must:
1. Confirm the switch: "Switching from [old template] to [new template]. This will change the funnel stages to: [new stage list]."
2. If dashboard mappings exist for the old template — ask if they should be remapped or cleared
3. Save the new template choice to `local-context.md`

### Multiple templates per product

A product can have only ONE active funnel template at a time. However:
- Different products in the same context can use different templates
- The user can save custom templates for future reuse (stored in CJM config)

### Template communication

Every CJM-related operation MUST communicate the active template. Examples:

**At the start of analysis:**
> "Starting CJM analysis for **[Product Name]** using the **E-commerce** template (4 stages: Start/Listing → Product Page → Cart/Checkout → Payment/Post-Purchase)."

**When results reference stages:**
> "Stage 3 (Cart / Checkout) shows a critical anomaly: checkout start rate dropped 28% vs previous period."

**When suggesting actions:**
> "Based on the E-commerce template, the highest-impact stage for this product is Stage 2 (Product Page)."
