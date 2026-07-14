---
name: experiment-tracker
version: 0.2.1
description: Track the full lifecycle of product experiments and hypotheses — a living registry of what is proposed, specced, running, awaiting readout, and decided, with stale-test reminders. Use when the user asks "what experiments are running", "experiment status", "register an experiment", "log the test launch", "which tests await a decision", "remind me about stale tests", "experiment tracker". Українською — "які тести зараз біжать", "статус експериментів", "заведи експеримент", "зафіксуй запуск тесту", "які тести чекають рішення", "нагадай про завислі тести", "трекер експериментів". Do NOT use for analyzing A/B results (product-analysis), writing an A/B spec (requirements-creator), or generating hypotheses (brainstorm-features) — this skill tracks state and chains to those skills.
---

# Experiment Tracker

Closes the loop the pipeline used to drop after the A/B spec was written: hypothesis → spec → **launch → running → readout → decision**. The skill owns experiment *state*, not analysis — every verdict comes from `product-analysis` (with its Data Integrity Gate), every decision is the PM's and gets recorded via `decision-log`.

## Prerequisites
- `references/local-context-protocol.md` — Step 0. Context used: `product.ab_test_dashboards`, `product.jira_project_key`, `user.language`.
- `references/persistent-storage.md` — registry lives in `~/.grow-pm/experiments/`.
- `references/vault-protocol.md` + `references/vault-schema.md` — hypothesis lifecycle updates and mirror sync.
- `references/data-policy.md` — experiment metrics are internal data.
- `references/roi-frameworks.md` — optional cost-of-test / decision ROI (ROAIP).
- `references/goal-frameworks.md` — optional Tell-and-Sell commitment status.

## Experiment lifecycle

`proposed → specced → running → awaiting-readout → decided (rollout | rollout-with-caveats | iterate | extend | rollback)`

State transitions are recorded with dates; nothing moves backward silently — corrections are logged as new transitions.

## Registry (Step R — always first after Step 0)

Source of truth: `~/.grow-pm/experiments/registry.yaml`. Create on first run:

```yaml
schema_version: 1.0.0
experiments:
  - id: exp-{slug}-{yyyymmdd}
    title: ""
    product: ""
    status: proposed          # lifecycle above
    hypothesis_ref: ""        # vault wikilink or free text
    spec_ref: ""              # Confluence URL of the A/B spec (requirements-creator)
    flag: ""                  # feature flag = test name (Jira FLAG field)
    platforms: []
    traffic_split: ""
    dashboards: []            # from product.ab_test_dashboards or per-test
    start_date: null
    planned_end: null
    readout_ref: ""           # vault link / Confluence URL of the product-analysis readout
    verdict: null             # winner | loser | inconclusive (from readout only)
    decision: null            # rollout | rollout-with-caveats | iterate | extend | rollback
    decision_ref: ""          # decision-log record link
    # Economics & commitment (optional — references/roi-frameworks.md, references/goal-frameworks.md)
    cost: null                # cost of running the test (hours × rate, or $)
    roi: null                 # ROI / annual % return of the decision (ROAIP)
    commitment: ""            # Tell and Sell: who committed to the decision, and how
    history: []               # {date, from, to, note}
```

**After every registry write:** mirror to vault `_System/experiments-registry.yaml` per `vault-protocol.md` (VM-1..VM-3). If vault_level == L0 — registry works standalone, mirror skips silently.

## Modes

| Mode | Trigger examples | What it does |
|------|-----------------|--------------|
| `status` (default) | "які тести біжать", "experiment status" | Board of all experiments grouped by lifecycle state + stale flags |
| `register` | "заведи експеримент" | New entry from a hypothesis (vault link or text) + optional spec link |
| `start` | "зафіксуй запуск тесту" | Record launch: flag, platforms, split, dates, dashboards |
| `readout` | "тест закінчився, зроби readout" | Chain to product-analysis A/B mode; record verdict |
| `decide` | "фіксуємо рішення по тесту" | Record the PM's decision; chain to decision-log |
| `stale` | "нагадай про завислі тести" | Only the stale list (also the headless payload) |

## Pipeline

### Step 0 — Local context
Per `local-context-protocol.md`. Then **Step R** — load/create the registry.

### Mode: status
1. Read registry; if vault_level > L0 — cross-check `Hypotheses/` artifacts with `status: proposed|testing` that are missing from the registry → offer to import.
2. Render the board: one table per lifecycle state (id, title, flag, platforms, key dates, days in state).
3. **Stale detection** (always appended):
   - `running` past `planned_end` → "⏰ overdue by N days — extend or readout?"
   - `awaiting-readout` > 3 days → "📊 readout pending N days"
   - `proposed` with ICE ≥ 8 older than 30 days → "💤 high-ICE hypothesis idle"
   - `decided: extend` without a new `planned_end` → "❓ extension not scheduled"
4. Offer per-item actions (start / readout / decide / archive).

### Mode: register
1. Input: hypothesis (vault `[[Hypotheses/…]]` link, brainstorm-features output, or free text) + optional A/B spec URL.
2. Create entry (`status: proposed`, or `specced` if spec_ref given). **Gate: show the entry before saving.**
3. If no spec exists → offer chaining to `requirements-creator` (A/B test spec).

### Mode: start
1. Pick the experiment (from registry, or register on the fly).
2. Collect: `flag` (offer lookup from Jira FLAG field via `jira_project_key` when available), platforms, traffic split, `start_date` (default today), `planned_end` (from spec duration or ask), dashboards (prefill from `product.ab_test_dashboards`).
3. **Gate**, then write: `status: running`, history entry. If vault hypothesis linked → update its frontmatter `hypothesis_status: testing` per `vault-protocol.md` → Hypothesis Lifecycle Updates.
4. Offer a scheduled stale-check (see Headless below) if none exists yet.

### Mode: readout
1. Pick the running/overdue experiment.
2. **Chain to `product-analysis` → A/B Test Results mode**, passing: flag/test name, dashboards, start/end dates, platforms, traffic split, spec link. product-analysis runs its own Data Integrity Gate and returns the verdict.
3. Record `verdict` + `readout_ref`; the experiment stays in `awaiting-readout` until the PM decides (Mode: decide). The linked hypothesis artifact's status is updated by product-analysis' own Vault Save (winner → validated, loser → rejected, inconclusive → inconclusive).
4. Never compute or adjust the verdict here — the tracker records what product-analysis concluded, including "inconclusive".

### Mode: decide
1. Pick an experiment with a recorded verdict.
2. Ask the PM's decision: rollout / rollout-with-caveats (name the caveats) / iterate (what changes) / extend (new planned_end) / rollback (why).
2b. **Economics & commitment (optional):** capture the test **cost** and the decision's **ROI / annual return** (`references/roi-frameworks.md`), and the **commitment** status (`references/goal-frameworks.md` → Tell and Sell: who committed and how). These flow into the decision-log record.
3. **Gate**, then write `decision`, `status: decided`, `cost`/`roi`/`commitment` if provided, history.
4. **Chain to `decision-log`** with full context (experiment, verdict, options considered, decision, rationale) — the ADR record link comes back into `decision_ref`.
5. Follow-ups: rollout → offer `task-creator` (cleanup/rollout tasks, «Випилити прапор …» convention); iterate → offer `brainstorm-features`/`requirements-creator`; extend → update planned_end.

### Step V — Vault Save
Registry mirror after every write (see above). No separate artifact — experiments live as registry entries + linked `hypothesis`/`ab-test-results`/`decision` artifacts owned by their source skills.

## Headless (scheduled stale-check)
Contract for scheduled runs (analogous to focus-advisor): `mode=stale headless=true` → no questions; output = compact stale list with per-item recommended action, or "all experiments healthy". Offer creating the schedule (weekly, Monday) via the platform's `schedule` skill during `start` mode.

## Quality Standards
- The tracker never declares winners — verdicts only via product-analysis readout (Gate included).
- Every state transition carries a date and lands in `history`; the PM decides, the tracker records.
- Registry writes are gated (show before save) and always mirrored to vault when configured.
- Stale thresholds are defaults — override via a `Experiments` section in local-context if present.
- Language — `user.language`.

## Skill Chaining
← `brainstorm-features` (new hypotheses → register) · ← `requirements-creator` (A/B spec → specced) · → `product-analysis` A/B mode (readout) · → `decision-log` (decide) · → `task-creator` (rollout/cleanup tasks) · → `product-reporter` (flags report cross-check) · → `schedule` (weekly stale-check).
