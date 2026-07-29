# glossary-workflows.md

> Skill-local reference for `knowledge-library` — the **Team language contour**: glossary (terms + phrases) and style profile. Workflows: Glossary Build (GB), Style Build (SB), Glossary Manage (GM), Glossary Lint (GL). Read ONLY the workflow for the active mode. Consumed by every artifact-producing skill through `references/artifact-style-gate.md` → Gate 3.

## Storage & schemas

```
~/.grow-pm/knowledge-library/
├── glossary/
│   ├── _org.yaml          # organization-wide terms
│   └── {product_id}.yaml  # product terms (override _org on conflict)
└── style/
    ├── _org.md            # organization style profile
    └── {product_id}.md    # product profile (only if it differs)
```

Vault mirror (when configured): `Knowledge/glossary/` and `Knowledge/style/` — same post-write sync procedure as the library files.

### Glossary YAML schema — two levels

```yaml
terms:
  - term: "картка товару"          # canonical name the team uses
    en: "product card"             # English equivalent (market-standard)
    variants: ["КТ"]               # accepted synonyms/abbreviations
    avoid:                         # foreign phrasings AI tends to use
      - "продуктова картка"
      - "картка продукту"
      - "product page"
    definition: "Сторінка товару на маркетплейсі"   # one sentence
    source: "confluence:SPACE/Page"                 # where it was mined from
    status: approved               # candidate | approved | deprecated
    added: 2026-08-01

phrases:                           # dead officialese → living replacements
  - avoid: "здійснити імплементацію"
    use: "впровадити"
  - avoid: "в рамках даного функціоналу"
    use: "у цій функції"
```

`terms` fixes WHAT things are called; `phrases` fixes HOW sentences sound. Both feed Glossary Lint. Only `approved` entries drive replacements; `candidate` entries are shown as suggestions only.

### Style profile schema (markdown)

```markdown
# Style profile — {product|org}
## Tone & register        ← address form (ти/ви), formality, person
## Syntax                 ← sentence length, active voice, clause density
## Do / Don't             ← team-specific rules ("висновок першим", "не нумерувати заголовки")
## Reference fragments    ← 3–5 verbatim excerpts of human-written team text (few-shot; the strongest mechanism)
## AI anti-patterns       ← accumulated from feedback and lint findings
```

---

## GB — Glossary Build

Triggers: "збери глосарій", "побудуй бібліотеку термінів", "build a glossary", first-run when Gate 3 finds no glossary and the user opts in.

**GB-1. Scope.** Read the Terminology & Style config (`local-context.md`); if absent, ask which sources to mine: Confluence space, Jira project, Fireflies meetings, user-provided documents. Write the config section afterwards (or route to `plugin-configurator`).

**GB-2. Mine candidates.** For each configured source — respecting `references/data-policy.md` (nothing leaves the session):

- **Confluence:** top-N pages of the space by recency/relevance (default N=30). Extract recurring domain nouns/noun-phrases and their variants.
- **Jira:** summaries + descriptions of the last ~200 issues of the project.
- **Fireflies:** transcripts of the last N meetings (default 20) — the richest source of how the team actually speaks.
- **Documents:** any files the user points at.

**Read Atlassian MCP sequentially** — parallel subagents on one Atlassian MCP cross-wire responses. Fan-out per `references/subagent-delegation.md` is allowed for non-Atlassian sources; each subagent returns `{term, variants_seen, frequency, sample_context, source}` — never raw dumps.

**GB-3. Rank & dedupe.** Merge candidates across sources; rank by frequency × source diversity. Detect variant clusters (same concept, different phrasings) — the most frequent phrasing becomes the proposed canonical `term`, the rest become `variants` or `avoid`.

**GB-4. Confirm in batches.** Present candidates via AskUserQuestion, 10–15 per batch: proposed canonical form, variants, the `avoid` list, one-line definition. The user approves / edits / rejects. Approved → `status: approved`; unsure → `status: candidate`.

**GB-5. Phrases pass.** Offer the built-in seed list of officialese→living replacements (uk) and ask for team-specific additions. **One-time sync with the user's project instructions / style guide:** if the user's assistant preferences contain a style dictionary (e.g. «юзер → користувач»), import those pairs and flag any conflicts to the user instead of silently overriding.

**GB-6. Write & mirror.** Write the YAML, sync the vault mirror, report totals: "Glossary: X approved terms, Y candidates, Z phrases."

## SB — Style Build

Runs together with GB (a shared "Team language" onboarding) or standalone: "навчись нашого стилю", "learn our writing style".

**SB-1.** Ask for 3–10 reference texts written by humans that the user considers well-written (Confluence pages, tickets, messages). Read them.
**SB-2.** Draft the profile per the schema above: tone/register, syntax, do/don't, and pick 3–5 short verbatim fragments as few-shot references (with the user's confirmation — fragments may contain sensitive data; strip specifics if asked).
**SB-3.** One-time sync with project-instruction style rules (same as GB-5 — one merged pass).
**SB-4.** Confirm with the user, write the product profile (or the org one) under `~/.grow-pm/knowledge-library/style/`, sync mirror.

## GM — Glossary Manage

Triggers: "додай термін", "як ми називаємо…", "покажи глосарій", "застарілий термін", "онови стильовий профіль", "add a term", "show the glossary".

- **Add/edit:** collect term fields conversationally, default `status: approved` when the user states it directly (they ARE the authority), `candidate` when inferred.
- **Deprecate:** set `status: deprecated`, optionally add the term to another entry's `avoid`.
- **Answer "how do we call X":** look up across `term`/`variants`/`avoid`/`en`, answer with the canonical form + definition.
- **Show:** render the glossary as a table (term / variants / avoid / status) and the style profile on request.
- Every write → vault mirror sync.

## GL — Glossary Lint (service mode)

Called by `artifact-style-gate.md` Gate 3b with a draft text; directly by the user: "перевір термінологію в цьому тексті", "check terminology".

**GL-1. Load** the product glossary (+ `_org`) and style profile. Empty/missing → return "lint skipped: no glossary" immediately.
**GL-2. Scan** the text:

- occurrences of any `avoid` entry (terms and phrases) → replacement finding `{found, replace_with, count, locations}`;
- `variants` used where the canonical `term` fits better in formal artifacts → soft suggestion;
- style-profile deviations (do/don't violations, anti-patterns) → style finding;
- frequent domain terms (≥3 occurrences) absent from the glossary → candidate list.

**GL-3. Return** a structured payload to the caller: `{replacements: [...], style_findings: [...], candidates: [...]}` — the caller (gate/checker) decides how to apply per `lint_mode`. When called directly by the user — present the same as a readable table and offer to apply.

## Config (local-context.md section)

```markdown
### Terminology & Style
#### Settings
- lint_mode: suggest        # suggest | auto | off
- style_preamble: on        # on | off
#### Extraction Sources (per product)
- confluence_space: SPACE
- jira_project: PROJ
- fireflies: last_20_meetings
```

Schema documented in `skills/plugin-configurator/references/context-schema.md`; filled by `plugin-configurator` or by GB-1 on first run.
