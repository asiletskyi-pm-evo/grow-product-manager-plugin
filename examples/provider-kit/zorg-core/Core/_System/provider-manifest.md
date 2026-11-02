---
kind: provider-file
file: provider-manifest.yaml
---
# Provider manifest — `provider-manifest.yaml`

A copy of `provider-manifest.yaml` beside it, for a notes server that serves `.md` only: a colleague's plugin unpacks this block into its own copy of the core (references/context-provider-protocol.md §9). Keep the two equal — `ctx repo kit-check` checks it.

```yaml
# The provider manifest of a team's shared core (references/context-provider-protocol.md §3a).
# Everything here is fictional: Zorg is the plugin's example company.
schema: provider-manifest/1
id: zorg-core
title: Zorg shared product core
namespace: zorg-core
plugin_folder: Core
contract: vault/v1
authority: org
mode: snapshot
product_name: Zorg App
bundles_file: Core/_System/access-bundles.json
blocks_file: Core/_System/context-blocks.md
tools_file: Core/_System/tools.yaml
team_card_dir: Core/Teams
people_dir: Core/People
missions_dir: Core/Products/Zorg App/Missions
dashboard_file: Core/Dashboard.md
playbook:
  - Core/Playbook/01 Rules.md
routing_hints: Core/Playbook/01 Rules.md
personal_overlay:
  - Core/Now.md
  - Core/TODO*
  - Core/_personal/
exclude:
  - "(^|/)_drafts/"
people_private_fields:
  - meetings_count
directory_label: company directory
owner_label: core owner
write_scope:
  jira: own-project
  confluence: read
```
