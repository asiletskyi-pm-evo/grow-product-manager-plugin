# Provider kit — example «Zorg»

A team that wants its colleagues' Grow PM plugins to share its context ships a folder like this one: its **core**.
Everything here is fictional (Zorg, `@zorg.example`, PROJ). Copy the folder, replace the content, keep the layout.
The full contract is `references/context-provider-protocol.md` §9.

## What is in it

| Path | What it is |
|---|---|
| `Core/_System/provider-manifest.yaml` | Who the core is: `id`, `namespace` of its blocks, where the role model, the blocks, the team cards and the people cards are, what is the owner's personal layer (`personal_overlay`), which card fields stay private. |
| `Core/_System/access-bundles.json` | The role model: `emails` (e-mail → team), `teams` (title, files, modules, missions, metrics), `roles` (role → layers), `layer_prefixes`, `shared`, `always`, `people_role` (person card → role title). The plugin resolves a colleague's e-mail → team → role from it. |
| `Core/_System/context-blocks.md` | The blocks a colleague's context receives, each between `<!-- zorg-core:begin id=… v=… -->` and its end marker. `slot=product.key_metrics` tells the plugin which slot a block answers; `policy=rule` makes a block a rule — annotated by the colleague (an overlay may `append` to it or `alias` it), never overridden (its `replace`, `remove` and `ignore` are held). |
| `Core/Teams/team-<key>.md` | One card per team of the role model (`title`, `aliases`, `head`, `jira`). The plugin builds the colleague's team block from it. |
| `Core/People/<name>.md` | Registry cards: `name`, `email`, `team`, `role`. The file name is the e-mail's part before `@` with `.` → `-` (`pat.moss@…` → `pat-moss.md`). |
| `Core/Playbook/` | Rules for the agent, read by every colleague. |
| `overlay.example.yaml` | Not part of the core: what a colleague may write in their own store to correct the core (`overlays/zorg-core.yaml`). |

## Releasing a version

A release changes `version` in `access-bundles.json` and `v=` on **every** block, whether its words changed or not.
Colleagues get it in one pass: `ctx provider plan zorg-core` → `ctx provider apply zorg-core`. A block they did not
edit is updated without a question; their declared corrections (the overlay) are applied again; a value the core
changed that a colleague copied into their own sections arrives in their inbox as a proposal.

## Checking and connecting

```bash
python3 scripts/ctx.py repo kit-check examples/provider-kit/zorg-core
python3 scripts/ctx.py repo add examples/provider-kit/zorg-core --email pat.moss@zorg.example
```

`kit-check` names every fault (a team with no card, an e-mail pointing to no team, a broken block marker, a person card
without an e-mail) and warns about what a shared folder shows to anyone who opens it (private fields, the owner's
personal layer). `repo add` shows the team, the role, the registration and the blocks with a code; the same command
with `--apply --code <code>` connects the kit. The daily sync is switched on separately, by a yes in `context-connect`.
