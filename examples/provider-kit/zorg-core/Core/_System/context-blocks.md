# Context blocks — Zorg shared core

Each block lands in a colleague's context between its two markers. `v=` is the core's release; `slot=` tells the
plugin which slot the block answers; `policy=rule` makes it a rule the colleague annotates but never overrides.

<!-- zorg-core:begin id=scope v=0.1 -->
### Scope of work
Zorg App: the marketplace web app and the iOS and Android apps.
<!-- zorg-core:end id=scope -->

<!-- zorg-core:begin id=key-metrics v=0.1 slot=product.key_metrics -->
#### Key Metrics
| Metric | Definition | Owner |
|---|---|---|
| Review rate | orders with a review / delivered orders | Alpha |
| Checkout CR | paid orders / checkout starts | Beta |
<!-- zorg-core:end id=key-metrics -->

<!-- zorg-core:begin id=metric-rules v=0.1 policy=rule -->
### Metric rules
- A metric is counted on delivered orders unless its definition says otherwise.
- A metric has one owning team.
<!-- zorg-core:end id=metric-rules -->

<!-- zorg-core:begin id=teams v=0.1 -->
### Teams map
- Alpha — reviews and catalog
- Beta — checkout
<!-- zorg-core:end id=teams -->
