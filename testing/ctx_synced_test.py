#!/usr/bin/env python3
"""TC-ctx-3140-decide — scripts/ctx_synced.py `decide`: what the unattended sync does with each row of a plan (since v3.14.0).

A pure function on the fictional "Zorg", with no store: a plan is built here as plain rows ({"block", "sign", "rejected"?}) and
the repository's texts as a plain {block: text} dict. The cases are the table of the spec's §5.1 in its order — a text you
rejected by undoing a sync pass is held whatever else it is (a rule included); more than one removal in a pass is held, none
goes through (§6.1); `⚠` keeps yours unless the repository's text is a core rule, and an edited block the repository removed
keeps your text; `?` waits (the base does not move) or takes a rule; `+` is added; every other sign is left to `apply`.
Also: the answer is only ever about the rows of the plan, the plan's own dict and a bare list of rows are the same input, and
the rule is read from the repository's text, never from the row. Semantics: Context-Core-v3.14-Spec §5.1, §5.2, §6.1.
Then `due` (Task 4), the table of when a repository is synced: never for `sync: off`, no key or a paused registration; 24 h
after the last successful check, no sooner than an hour after a failed attempt that came after it; a time more than a day
ahead (another Mac's clock) counts as unknown (§4.1–§4.3). And `sentence`, the one line a skill repeats (§8). The pass
itself (`run`) is tested end to end in ctx_cli_test.py.
Stdlib only; run from the repo root.
"""
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import ctx_blocks as cb  # noqa: E402
import ctx_synced as sy  # noqa: E402
from ctx_synced import decide  # noqa: E402

fails = 0


def check(name, cond, detail=""):
    global fails
    fails += not cond
    print(("✅" if cond else "❌"), name, ("" if cond else "-> " + str(detail)[:700]))


NS = "zorg-core"


def region(bid, v, body, attrs=""):
    return "<!-- %s:begin id=%s v=%s%s -->\n%s\n<!-- %s:end id=%s -->" % (NS, bid, v, (" " + attrs) if attrs else "", body, NS, bid)


PLAIN = region("a", "2", "Zorg growth scope, as the core has it now.")
RULE = region("a", "2", "Zorg growth scope, as the core has it now.", "policy=rule")
BODY_RULE = region("a", "2", "A line that says policy=rule, which is only text.")   # the word inside the text is no rule


def P(*rows):
    """A plan: ("a", "⚠") or ("a", "⚠", True) — the third is the rejected mark."""
    return {"repo": "zorg-core", "rows": [dict(block=r[0], sign=r[1], host="custom.zorg-core-notes", source="folder", note="",
                                               **({"rejected": True} if len(r) > 2 and r[2] else {})) for r in rows]}


def T(**blocks):
    """The repository's texts: a block it no longer offers is absent."""
    return dict(blocks)


EMPTY = {"choose": {}, "add": [], "hold": [], "held_removals": [], "awaiting": [], "rejected": [], "kept_yours": [], "took_rule": []}

# ------------------------------------------------------------------ the shape
d = decide(P(), T())
check("the answer has exactly the keys of the contract, all empty for an empty plan", d == EMPTY, d)
check("the module is the one named in the plan", sy.__name__ == "ctx_synced" and callable(sy.decide))

# ------------------------------------------------------------------ the table, row by row (spec §5.1)
check("⚠ keeps yours", decide(P(("a", "⚠")), T(a=PLAIN))["choose"] == {"a": "mine"})
check("…and says so (kept_yours), not a rule", decide(P(("a", "⚠")), T(a=PLAIN))["kept_yours"] == ["a"]
      and decide(P(("a", "⚠")), T(a=PLAIN))["took_rule"] == [])
check("⚠ of a rule takes theirs", decide(P(("a", "⚠")), T(a=RULE))["choose"] == {"a": "theirs"})
check("…and says so (took_rule), not kept_yours", decide(P(("a", "⚠")), T(a=RULE))["took_rule"] == ["a"]
      and decide(P(("a", "⚠")), T(a=RULE))["kept_yours"] == [])
check("? waits, or takes a rule", decide(P(("a", "?")), T(a=PLAIN))["awaiting"] == ["a"]
      and decide(P(("a", "?")), T(a=RULE))["choose"] == {"a": "theirs"})
check("a ? that waits is no answer: it is not in choose, so apply leaves it pending and the base does not move",
      decide(P(("a", "?")), T(a=PLAIN))["choose"] == {} and decide(P(("a", "?")), T(a=PLAIN))["hold"] == [])
check("a ? of a rule is took_rule and is not awaiting", decide(P(("a", "?")), T(a=RULE))["took_rule"] == ["a"]
      and decide(P(("a", "?")), T(a=RULE))["awaiting"] == [])
check("+ is added", decide(P(("n", "+")), T(n=PLAIN))["add"] == ["n"])
check("a + that is a rule is added all the same (the rule only decides a conflict)",
      decide(P(("n", "+")), T(n=RULE)) == dict(EMPTY, add=["n"]), decide(P(("n", "+")), T(n=RULE)))
check("one removal goes through, two are held",
      decide(P(("a", "−")), T())["hold"] == [] and sorted(decide(P(("a", "−"), ("b", "−")), T())["held_removals"]) == ["a", "b"])
check("a single − is left to apply: nothing is chosen, nothing held",
      decide(P(("a", "−")), T()) == EMPTY, decide(P(("a", "−")), T()))
check("an edited block the repository removed keeps your text", decide(P(("a", "⚠")), T())["choose"] == {"a": "mine"})
check("…and is kept_yours", decide(P(("a", "⚠")), T())["kept_yours"] == ["a"])
check("a ? of a removed block waits (awaiting), it is not chosen", decide(P(("a", "?")), T()) ==
      dict(EMPTY, awaiting=["a"]), decide(P(("a", "?")), T()))
check("= ~ ✎ ✂ · are left to apply: nothing chosen, added, held or noted",
      all(decide(P(("a", s)), T(a=PLAIN)) == EMPTY for s in ("=", "~", "✎", "✂", "·")),
      [(s, decide(P(("a", s)), T(a=PLAIN))) for s in ("=", "~", "✎", "✂", "·")])
check("a ~ that is a rule needs no answer either (nothing of yours is overruled)",
      decide(P(("a", "~")), T(a=RULE)) == EMPTY, decide(P(("a", "~")), T(a=RULE)))
check("an unknown sign is left alone", decide(P(("a", "§")), T(a=PLAIN)) == EMPTY)

# ------------------------------------------------------------------ a text you rejected (spec §5.4)
check("rejected wins over a rule", decide(P(("a", "⚠", True)), T(a=RULE))["hold"] == ["a"]
      and decide(P(("a", "⚠", True)), T(a=RULE))["choose"] == {})
check("…and is named rejected, not took_rule", decide(P(("a", "⚠", True)), T(a=RULE))["rejected"] == ["a"]
      and decide(P(("a", "⚠", True)), T(a=RULE))["took_rule"] == []
      and decide(P(("a", "⚠", True)), T(a=RULE))["kept_yours"] == [])
check("a rejected ? of a rule is held, not taken", decide(P(("a", "?", True)), T(a=RULE)) == dict(EMPTY, hold=["a"], rejected=["a"]),
      decide(P(("a", "?", True)), T(a=RULE)))
check("a rejected + is not added", decide(P(("n", "+", True)), T(n=PLAIN)) == dict(EMPTY, hold=["n"], rejected=["n"]),
      decide(P(("n", "+", True)), T(n=PLAIN)))
check("a rejected ~ is held", decide(P(("a", "~", True)), T(a=PLAIN)) == dict(EMPTY, hold=["a"], rejected=["a"]))
check("a rejected ⚠ is held and not kept_yours or awaiting", decide(P(("a", "⚠", True)), T(a=PLAIN)) == dict(EMPTY, hold=["a"], rejected=["a"]))
check("a rejected − is held and is not a held removal", decide(P(("a", "−", True)), T()) == dict(EMPTY, hold=["a"], rejected=["a"]),
      decide(P(("a", "−", True)), T()))
check("a rejected ⚠ of a removed block is held", decide(P(("a", "⚠", True)), T()) == dict(EMPTY, hold=["a"], rejected=["a"]))
check("a block that is not rejected is untouched by a rejected neighbour",
      decide(P(("a", "⚠", True), ("b", "⚠")), T(a=RULE, b=PLAIN)) ==
      dict(EMPTY, choose={"b": "mine"}, hold=["a"], rejected=["a"], kept_yours=["b"]))

# ------------------------------------------------------------------ the removal guard (spec §6.1)
d = decide(P(("a", "−"), ("b", "−"), ("c", "~"), ("n", "+")), T(c=PLAIN, n=PLAIN))
check("two removals held, the rest of the signs go on", d["held_removals"] == ["a", "b"] and d["hold"] == ["a", "b"]
      and d["add"] == ["n"] and d["choose"] == {}, d)
d = decide(P(("a", "−"), ("b", "⚠")), T())
check("a − and a ⚠ of a removed block (no text in the repository) are two removals: both held, no choice",
      d["held_removals"] == ["a", "b"] and d["hold"] == ["a", "b"] and d["choose"] == {} and d["kept_yours"] == [], d)
d = decide(P(("a", "−"), ("b", "?")), T())
check("a − and a ? of a removed block are two removals: both held, the ? is not awaiting then",
      d["held_removals"] == ["a", "b"] and d["hold"] == ["a", "b"] and d["awaiting"] == [], d)
d = decide(P(("a", "⚠"), ("b", "⚠"), ("c", "?")), T())
check("three blocks the repository removed, none a −: all held", d["held_removals"] == ["a", "b", "c"] and d["choose"] == {}, d)
d = decide(P(("a", "−"), ("b", "⚠")), T(b=PLAIN))
check("a ⚠ with a repository text is no removal: the one − goes through, the ⚠ keeps yours",
      d == dict(EMPTY, choose={"b": "mine"}, kept_yours=["b"]), d)
d = decide(P(("a", "−"), ("b", "?")), T(b=PLAIN))
check("a ? with a repository text is no removal either: it waits, the − goes through",
      d == dict(EMPTY, awaiting=["b"]), d)
d = decide(P(("a", "−"), ("b", "−", True)), T())
check("a rejected − is held already and does not count: the other − is the only removal and goes through",
      d == dict(EMPTY, hold=["b"], rejected=["b"]), d)
d = decide(P(("a", "−"), ("b", "−"), ("c", "−", True)), T())
check("…two removals that are not rejected are held beside a rejected one; hold lists the rows in plan order",
      d["hold"] == ["a", "b", "c"] and d["held_removals"] == ["a", "b"] and d["rejected"] == ["c"], d)
d = decide(P(("a", "−"), ("b", "−")), T())
check("a block held as a removal is never also chosen, added or awaiting",
      d["choose"] == {} and d["add"] == [] and d["awaiting"] == [], d)
d = decide(P(("a", "−"), ("b", "⚠"), ("c", "⚠")), T(b=PLAIN, c=RULE))
check("the guard counts removals only: two ⚠ with a repository text beside one − are all decided as usual",
      d["held_removals"] == [] and d["choose"] == {"b": "mine", "c": "theirs"}, d)

# ------------------------------------------------------------------ a rule is read from the repository's text
check("a rule is read from the begin marker only, not from a word in the text", decide(P(("a", "⚠")), T(a=BODY_RULE))["choose"] == {"a": "mine"})
check("is_rule on the same texts agrees", cb.is_rule(RULE) and not cb.is_rule(PLAIN) and not cb.is_rule(BODY_RULE))
row = P(("a", "⚠"))
row["rows"][0]["rule"] = True
check("a row's own `rule` key is not what decides: the text of the repository is",
      decide(row, T(a=PLAIN))["choose"] == {"a": "mine"} and decide(P(("a", "⚠")), T(a=RULE))["choose"] == {"a": "theirs"})
check("a mixed plan: each ⚠ by its own text", decide(P(("a", "⚠"), ("b", "⚠")), T(a=RULE, b=PLAIN))["choose"] == {"a": "theirs", "b": "mine"})
check("a block missing from theirs is no rule (None never counts)", decide(P(("a", "⚠")), {})["took_rule"] == [])

# ------------------------------------------------------------------ the whole table at once, in plan order
plan = P(("eq", "="), ("new", "~"), ("mine", "✎"), ("both", "⚠"), ("law", "⚠"), ("q", "?"), ("qlaw", "?"), ("add", "+"), ("gone", "−"),
         ("cut", "✂"), ("skip", "·"), ("again", "~", True))
tx = T(eq=PLAIN, new=PLAIN, mine=PLAIN, both=PLAIN, law=RULE, q=PLAIN, qlaw=RULE, add=PLAIN, again=PLAIN)
d = decide(plan, tx)
check("every sign at once", d == {"choose": {"both": "mine", "law": "theirs", "qlaw": "theirs"}, "add": ["add"], "hold": ["again"],
                                  "held_removals": [], "awaiting": ["q"], "rejected": ["again"], "kept_yours": ["both"],
                                  "took_rule": ["law", "qlaw"]}, d)
check("hold only names rows of the plan", set(d["hold"]) <= {r["block"] for r in plan["rows"]}
      and set(d["add"]) <= {r["block"] for r in plan["rows"]})
check("the same plan as a bare list of rows is the same answer", decide(plan["rows"], tx) == d)
check("the plan and the texts are not changed", plan == P(("eq", "="), ("new", "~"), ("mine", "✎"), ("both", "⚠"), ("law", "⚠"), ("q", "?"),
                                                          ("qlaw", "?"), ("add", "+"), ("gone", "−"), ("cut", "✂"), ("skip", "·"),
                                                          ("again", "~", True)) and tx == T(eq=PLAIN, new=PLAIN, mine=PLAIN, both=PLAIN, law=RULE,
                                                                                            q=PLAIN, qlaw=RULE, add=PLAIN, again=PLAIN))
check("a choice is only ever mine or theirs", set(d["choose"].values()) <= {"mine", "theirs"})
check("every block is in at most one of choose / add / hold", all(sum(b in x for x in (d["choose"], d["add"], d["hold"])) <= 1
                                                                  for b in {r["block"] for r in plan["rows"]}))
check("decide is the same twice (nothing is kept between calls)", decide(plan, tx) == decide(plan, tx) == d)

# ------------------------------------------------------------------ due: once a day, a failed attempt once an hour (Task 4)
import datetime  # noqa: E402

NOW = "2026-10-17T09:00:00+03:00"
DAILY = {"id": "zorg-growth", "sync": "daily", "status": "active"}


def ago(**kw):
    return (datetime.datetime.fromisoformat(NOW) - datetime.timedelta(**kw)).isoformat()


def ahead(**kw):
    return (datetime.datetime.fromisoformat(NOW) + datetime.timedelta(**kw)).isoformat()


check("the numbers of the spec: 24 h from the last successful check, 1 h after a failed attempt, a 20 s budget",
      sy.DUE_AFTER == datetime.timedelta(hours=24) and sy.RETRY_AFTER == datetime.timedelta(hours=1) and sy.BUDGET_S == 20
      and sy.APPLY_MIN_S == 3)
check("never checked, never tried: due", sy.due(DAILY, {}, NOW) is True)
check("an empty state (load_state's shape, checked None) is due", sy.due(DAILY, {"checked": None, "blocks": {}}, NOW) is True)
check("checked 23 h ago: not due", sy.due(DAILY, {"checked": ago(hours=23)}, NOW) is False)
check("checked 25 h ago: due", sy.due(DAILY, {"checked": ago(hours=25)}, NOW) is True)
check("checked 24 h ago exactly: due (24 h have passed)", sy.due(DAILY, {"checked": ago(hours=24)}, NOW) is True)
check("…but an attempt 30 min ago failed: not due", sy.due(DAILY, {"checked": ago(hours=25), "sync_attempt": ago(minutes=30)}, NOW) is False)
check("…an attempt 2 h ago: due again", sy.due(DAILY, {"checked": ago(hours=25), "sync_attempt": ago(hours=2)}, NOW) is True)
check("…an attempt 1 h ago exactly: due again", sy.due(DAILY, {"checked": ago(hours=25), "sync_attempt": ago(hours=1)}, NOW) is True)
check("never checked, an attempt 30 min ago: not due", sy.due(DAILY, {"sync_attempt": ago(minutes=30)}, NOW) is False)
check("an attempt not later than the last check is no failed attempt: due",
      sy.due(DAILY, {"checked": ago(hours=25), "sync_attempt": ago(hours=25)}, NOW) is True
      and sy.due(DAILY, {"checked": ago(hours=25), "sync_attempt": ago(hours=26)}, NOW) is True)
check("checked 2 days in the future (another Mac's clock, iCloud): unknown, so due",
      sy.due(DAILY, {"checked": ahead(days=2)}, NOW) is True)
check("checked 2 h in the future (a clock a little ahead): not due", sy.due(DAILY, {"checked": ahead(hours=2)}, NOW) is False)
check("an attempt 2 days in the future is unknown too: due", sy.due(DAILY, {"checked": ago(hours=25), "sync_attempt": ahead(days=2)}, NOW) is True)
check("a check that is no time is unknown: due", sy.due(DAILY, {"checked": "yesterday"}, NOW) is True
      and sy.due(DAILY, {"checked": 5}, NOW) is True)
check("sync: off — never due", sy.due(dict(DAILY, sync="off"), {}, NOW) is False)
check("no sync key — never due (off is the default)", sy.due({"id": "zorg-growth", "status": "active"}, {}, NOW) is False)
check("a paused registration — never due", sy.due(dict(DAILY, status="paused"), {}, NOW) is False)
check("now as a datetime, and a time in UTC with Z, are read the same",
      sy.due(DAILY, {"checked": ago(hours=23)}, datetime.datetime.fromisoformat(NOW)) is False
      and sy.due(DAILY, {"checked": "2026-10-16T07:00:00Z"}, NOW) is False          # 23 h before 06:00Z
      and sy.due(DAILY, {"checked": "2026-10-16T07:00:00Z"}, "2026-10-17T08:00:00Z") is True)
state = {"checked": ago(hours=25), "sync_attempt": ago(minutes=30)}
sy.due(DAILY, state, NOW)
check("due reads only: the state is not changed", state == {"checked": ago(hours=25), "sync_attempt": ago(minutes=30)})

# ------------------------------------------------------------------ the sentence for the skill (Task 4; the report path is Task 5's)
R = {"repo": "zorg-growth", "updated": 1, "added": 0, "removed": 0, "kept_yours": [], "report": None}
check("one block, no conflict, no report yet: the sentence without the report clause",
      sy.sentence(R) == "Ядро оновило 1 блок у zorg-growth, конфліктів 0 (лишено твоє)", sy.sentence(R))
check("updated, added and removed count together; the plural is cs.blocks_word's; the conflicts kept yours are K",
      sy.sentence(dict(R, updated=2, added=2, removed=1, kept_yours=["a"])) == "Ядро оновило 5 блоків у zorg-growth, конфліктів 1 (лишено твоє)"
      and sy.sentence(dict(R, updated=1, added=1)) == "Ядро оновило 2 блоки у zorg-growth, конфліктів 0 (лишено твоє)")
check("with a report: ' — звіт: <path from the storage root>'",
      sy.sentence(dict(R, report="_System/context/sync/2026-10-17.md"))
      == "Ядро оновило 1 блок у zorg-growth, конфліктів 0 (лишено твоє) — звіт: _System/context/sync/2026-10-17.md")
check("the result's keys are the contract's", sy.RESULT_KEYS == ("at", "outcome", "updated", "added", "removed", "kept_yours", "took_rule",
                                                                 "awaiting", "held", "rejected", "reason", "report", "snapshot"))
check("the outcomes are the contract's (and error, since fix round 1)", set(sy.OUTCOMES) == {"changed", "no-changes", "unreachable", "broken", "held", "import-conflict", "timeout", "error"})

print("RESULT: GREEN ✅" if not fails else "RESULT: RED ❌")
sys.exit(1 if fails else 0)
