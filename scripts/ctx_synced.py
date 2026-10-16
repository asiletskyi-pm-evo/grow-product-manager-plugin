#!/usr/bin/env python3
"""Grow PM — the daily core sync: what it does with each row of a plan (since v3.14.0).

A repository registered with `sync: daily` is brought up to date once a day without a person at the keyboard
(spec Context-Core-v3.14 §3–§8). The sync is `ctx provider apply` with the answers given in advance, and the
answers come from one place:

- decide    the plan's rows in, the pass's answers out: `choose` (block → "mine" | "theirs", exactly what `apply`
            takes), `add` (the "+" blocks), `hold` (the blocks `apply` must not touch), and the names the report and
            the digest speak in — `held_removals`, `awaiting`, `rejected`, `kept_yours`, `took_rule`

It reads nothing and writes nothing: the plan is `ctx_blocks.plan`'s, the repository's texts are
`{block: text}` from `ctx_blocks._theirs(fetched)[0]` (a block the repository removed is absent). Rules, in this order
(§5.1, §5.2, §6.1):

1. a text you rejected by undoing a sync pass (`rejected: True`) is held, whatever else it is — a rule included
2. more than one block the repository removed in a pass (a "−", or a "⚠" / "?" whose repository text is None) is held,
   none of them goes through; a rejected row is held already and is not counted
3. "⚠" takes the repository's text when it is a core rule (`ctx_blocks.is_rule`, read from the begin marker of the
   repository's text), else keeps yours — and keeps yours when the repository removed the block
4. "?" takes a rule, else waits: not in `choose`, so `apply` leaves it pending and the base does not move
5. "+" is added
6. "=", "~", "✎", a lone "−", "✂", "·": nothing — `apply` acts by itself

Stdlib only.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx_blocks as cb  # noqa: E402

MINE, THEIRS = "mine", "theirs"
QUESTIONS = ("⚠", "?")                              # the signs that need an answer when apply is not told one


def _rows(plan):
    """The rows of a plan: `ctx_blocks.plan`'s dict, or the bare list of its rows."""
    return list(plan.get("rows") or []) if isinstance(plan, dict) else list(plan or [])


def decide(plan, theirs):
    """The pass's answers for every row of `plan` (spec §5.1); `theirs` is `{block: the repository's text}`, a removed
    block absent from it (or None). Nothing is read or written, and nothing passed in is changed.

    Returns {"choose": {block: "mine" | "theirs"}, "add": [block], "hold": [block], "held_removals": [block],
    "awaiting": [block], "rejected": [block], "kept_yours": [block], "took_rule": [block]} — the lists in plan order.
    `hold` names only blocks that are rows of the plan, and no block is in more than one of `choose`, `add` and
    `hold`. Whether a block is a core rule is read from the repository's text (`theirs`), never from the row."""
    theirs = theirs or {}
    rows = _rows(plan)
    removed = [r["block"] for r in rows if not r.get("rejected")
               and (r["sign"] == "−" or (r["sign"] in QUESTIONS and theirs.get(r["block"]) is None))]
    guarded = set(removed) if len(removed) > 1 else set()          # §6.1: the repository removed more than one block
    out = {"choose": {}, "add": [], "hold": [], "held_removals": [], "awaiting": [], "rejected": [],
           "kept_yours": [], "took_rule": []}
    for row in rows:
        bid, sign = row["block"], row["sign"]
        text = theirs.get(bid)
        if row.get("rejected"):
            out["hold"].append(bid)
            out["rejected"].append(bid)
        elif bid in guarded:
            out["hold"].append(bid)
            out["held_removals"].append(bid)
        elif sign == "⚠":
            if cb.is_rule(text):
                out["choose"][bid] = THEIRS
                out["took_rule"].append(bid)
            else:
                out["choose"][bid] = MINE
                out["kept_yours"].append(bid)
        elif sign == "?":
            if cb.is_rule(text):
                out["choose"][bid] = THEIRS
                out["took_rule"].append(bid)
            else:
                out["awaiting"].append(bid)
        elif sign == "+":
            out["add"].append(bid)
    return out
