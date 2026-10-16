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

# ------------------------------------------------------------------ the report (Task 5, spec §7): the pure part
import re  # noqa: E402
import shutil  # noqa: E402
import tempfile  # noqa: E402
import ctx_ops as co  # noqa: E402
import ctx_store as cs  # noqa: E402

SNAP = "/home/zorg/.grow-pm/snapshots/20261016T090000-provider-sync"
AT = "2026-10-16T09:00:00+03:00"


def reg(ns, bid, v, text):
    return "<!-- %s:begin id=%s v=%s -->\n%s\n<!-- %s:end id=%s -->" % (ns, bid, v, text, ns, bid)


def lines_of(tag, n):
    return "\n".join("%s %d" % (tag, i) for i in range(1, n + 1))


def row(block, sign, host="product.zorg-app", source="mcp", note="", **kw):
    return dict(block=block, sign=sign, host=host, source=source, note=note, **kw)


def plan_of(*rows, **kw):
    return dict({"repo": "zorg-growth", "source": "mcp", "source_label": "MCP (zorg.example)", "version": "0.2",
                 "base_version": "0.1", "rows": list(rows)}, **kw)


def applied(plan, decisions, pending=(), snapshot=SNAP, held=None, errors=()):
    return {"repo": "zorg-growth", "plan": plan, "applied": {}, "decisions": decisions, "pending": list(pending), "ignored": {},
            "held": held or {}, "errors": list(errors), "written": [], "snapshot": snapshot}


def result_of(outcome="changed", **kw):
    base = {"repo": "zorg-growth", "at": AT, "outcome": outcome, "updated": 0, "added": 0, "removed": 0, "kept_yours": [], "took_rule": [],
            "awaiting": [], "held": [], "rejected": [], "reason": None, "report": None, "snapshot": SNAP}
    base.update(kw)
    return base


M_TEXT = reg("zorg-growth", "growth-metrics", "0.1", "#### Growth metrics\n- **North star:** weekly active shoppers (mine)")
T_TEXT = reg("zorg-growth", "growth-metrics", "0.2", "#### Growth metrics\n- **North star:** weekly buyers")
DIFF = {"theirs": ["- **North star:** weekly buyers"], "mine": ["- **North star:** weekly active shoppers (mine)"],
        "base": ["- **North star:** weekly active shoppers"]}
THREE = plan_of(row("growth-metrics", "⚠", note="змінили обидва — потрібне рішення", diff=DIFF),
                row("team", "~", host="product.zorg-lite", note="оновлено з репозиторію (v0.1 → v0.2)"),
                row("growth-okr", "+", host=None, note="новий блок у репозиторії"),
                row("scope", "=", note="без змін"), row("mine-only", "✎", note="лишаються ваші правки"))
THREE_RES = applied(THREE, {"growth-metrics": "⚠ mine", "team": "~", "growth-okr": "+", "scope": "=", "mine-only": "✎"})
THREE_R = result_of(updated=1, added=1, kept_yours=["growth-metrics"])
SEC = sy.render_section(THREE_R, THREE_RES, {"mine": {"growth-metrics": M_TEXT}, "theirs": {"growth-metrics": T_TEXT}},
                        {"growth-okr": "product.zorg-app"}, "0.2")
SEC_LINES = SEC.splitlines()

check("the report's numbers: 90 days, 40 lines a side; the folder from the storage root",
      sy.REPORT_DAYS == 90 and sy.REPORT_LINES == 40 and sy.REPORT_DIR == "_System/context/sync")
check("a section opens with `## <id> · HH:MM · джерело <label> · ядро v<v> · база v<a> → v<b>`",
      SEC_LINES[0] == "## zorg-growth · 09:00 · джерело MCP (zorg.example) · ядро v0.2 · база v0.1 → v0.2", SEC_LINES[0])
check("…the table has the columns Блок, Знак, Рішення, Чому, Запис in this order",
      "| Блок | Знак | Рішення | Чому | Запис |" in SEC_LINES, SEC)
table = [l for l in SEC_LINES if l.startswith("| `")]
check("…and one row for each of ⚠ ~ + — the signs that need no decision of the sync (= ✎) are not listed", len(table) == 3, table)
check("…⚠ kept yours: the cascade's own words",
      any("`growth-metrics`" in l and "⚠" in l and "лишено твоє" in l and "змінили обидва → лишено твоє: блок не є правилом ядра" in l
          and "`product.zorg-app`" in l for l in table), table)
check("…~ updated: the core's text, the record it lives in, the version it moved by",
      any("`team`" in l and "~" in l and "текст ядра" in l and "`product.zorg-lite`" in l and "(v0.1 → v0.2)" in l for l in table), table)
check("…+ added: «новий блок у ядрі → додано», the record the block went into (read after the write)",
      any("`growth-okr`" in l and "+" in l and "додано" in l and "новий блок у ядрі → додано" in l and "`product.zorg-app`" in l
          for l in table), table)
check("…a summary of the pass above the table", "Оновлено 1 · додано 1 · прибрано 0 · лишено твоє 1" in SEC, SEC)
check("a conflict kept yours has its own part, with BOTH texts in full", "### Конфлікт: `growth-metrics`" in SEC
      and "weekly active shoppers (mine)" in SEC and "weekly buyers" in SEC and "Твій текст" in SEC and "Текст ядра" in SEC, SEC)
check("…the markers of the regions are not in the shown text, their versions are in the captions",
      "<!-- zorg-growth:begin" not in SEC and "Твій текст (v0.1)" in SEC and "Текст ядра (v0.2)" in SEC, SEC)
check("…the plan's three lines of difference (what the core says, what you wrote, what both said before)",
      "Ядро тепер каже: - **North star:** weekly buyers" in SEC and "Ви писали: - **North star:** weekly active shoppers (mine)" in SEC
      and "Раніше обидва казали" in SEC, SEC)
check("…the command to take the core's text, ready", "Взяти текст ядра: ctx provider apply zorg-growth --choose growth-metrics=theirs" in SEC_LINES, SEC)
check("the last line is the way back, with the snapshot folder",
      SEC_LINES[-1] == "Відкотити цей прохід: ctx undo (знімок %s)" % SNAP, SEC_LINES[-3:])
check("the section has no trailing blank line", SEC == SEC.rstrip("\n"))
check("the texts are fenced code (what a server sends is never live Markdown)", SEC.count("\n```\n") >= 4, SEC)

# 100 lines a side: 40 shown, then «… ще 60 рядків — …»
BIG_M = reg("zorg-growth", "big", "0.1", lines_of("mine", 100))
BIG_T = reg("zorg-growth", "big", "0.2", lines_of("theirs", 100))
BIG = plan_of(row("big", "⚠", diff=DIFF))
big = sy.render_section(result_of(kept_yours=["big"]), applied(BIG, {"big": "⚠ mine"}), {"mine": {"big": BIG_M}, "theirs": {"big": BIG_T}})
check("a text of 100 lines is cut to 40: line 40 is there, line 41 is not", "mine 40" in big and "mine 41" not in big
      and "theirs 40" in big and "theirs 41" not in big, big)
check("…«… ще 60 рядків» for each side", big.count("… ще 60 рядків") == 2, big)
check("…yours is whole in the snapshot, the core's text at the core",
      "… ще 60 рядків — повністю у знімку %s" % SNAP in big and "… ще 60 рядків — повністю у джерелі ядра" in big, big)
few = sy.render_section(result_of(kept_yours=["big"]), applied(BIG, {"big": "⚠ mine"}),
                        {"mine": {"big": reg("zorg-growth", "big", "0.1", lines_of("m", 40))}, "theirs": {"big": reg("zorg-growth", "big", "0.2", lines_of("t", 41))}})
check("…40 lines are shown whole; 41 are 40 and «… ще 1 рядок» (the form follows the number)",
      "m 40" in few and "t 40" in few and "t 41" not in few and "… ще 1 рядок — повністю у джерелі ядра" in few
      and "ще 0" not in few, few)
tick = sy.render_section(result_of(kept_yours=["big"]), applied(BIG, {"big": "⚠ mine"}),
                         {"mine": {"big": reg("zorg-growth", "big", "0.1", "a ``` b\n```\nc")}, "theirs": {"big": T_TEXT}})
check("a text with a fence in it is fenced by a longer one, so it cannot break out", "````\na ``` b\n```\nc\n````" in tick, tick)
ctl = sy.render_section(result_of(kept_yours=["big"]), applied(BIG, {"big": "⚠ mine"}),
                        {"mine": {"big": reg("zorg-growth", "big", "0.1", "ok\x1b[31mred\x07")}, "theirs": {"big": T_TEXT}})
check("control characters of a server's text never reach the report", "\x1b" not in ctl and "\x07" not in ctl and "ok [31mred" in ctl, repr(ctl))

# a core rule, a ? that waits, a block the core removed after you edited it
RULE_P = plan_of(row("law", "⚠", source="mcp", diff=DIFF, rule=True), row("q", "?", note="бази немає"),
                 row("qlaw", "?", rule=True), row("cut", "⚠", source=None, diff={"theirs": ["(репозиторій прибрав цей блок)"], "mine": ["x"], "base": ["x"]}))
rule = sy.render_section(
    result_of(took_rule=["law", "qlaw"], awaiting=["q"], kept_yours=["cut"], updated=2),
    applied(RULE_P, {"law": "⚠ theirs", "qlaw": "? theirs", "cut": "⚠ mine"}, pending=["q"]),
    {"mine": {"law": reg("zorg-growth", "law", "0.1", "my law"), "q": reg("zorg-growth", "q", "0.1", "my q"), "qlaw": reg("zorg-growth", "qlaw", "0.1", "my qlaw"),
              "cut": reg("zorg-growth", "cut", "0.1", "my cut")},
     "theirs": {"law": reg("zorg-growth", "law", "0.2", "core law"), "q": reg("zorg-growth", "q", "0.2", "core q"),
                "qlaw": reg("zorg-growth", "qlaw", "0.2", "core qlaw"), "cut": None}})
rtable = [l for l in rule.splitlines() if l.startswith("| `")]
check("a ⚠ that is a core rule: «правило ядра → текст ядра», and your text is shown (it is gone from the records)",
      any("`law`" in l and "текст ядра" in l and "правило ядра → текст ядра" in l for l in rtable) and "my law" in rule and "core law" in rule, rule)
check("…its part says the rule won and that your text is in the snapshot; no «take the core's text» for what was taken already",
      "правило ядра" in rule and "Взяти текст ядра: ctx provider apply zorg-growth --choose law=theirs" not in rule, rule)
check("a ? of a rule is the core's text", any("`qlaw`" in l and "текст ядра" in l and "правило ядра → текст ядра" in l for l in rtable), rtable)
check("a ? that waits: «чекає рішення», yours stays, the base does not move; both commands are given",
      any("`q`" in l and "чекає рішення" in l for l in rtable) and "ctx provider apply zorg-growth --choose q=theirs" in rule
      and "ctx provider apply zorg-growth --choose q=mine" in rule and "my q" in rule and "core q" in rule, rule)
check("a block the core removed after you edited it: yours is kept without its markers, nothing to take",
      any("`cut`" in l and "лишено твоє" in l and "ядро прибрало блок" in l for l in rtable)
      and "ctx provider apply zorg-growth --choose cut=theirs" not in rule and "Ядро прибрало цей блок" in rule, rule)

# the safeguard: two removals held
HELD_P = plan_of(row("a", "−", source=None), row("b", "−", source=None), row("c", "~", note="оновлено з репозиторію"))
held = sy.render_section(result_of("held", updated=1, held=["a", "b"], reason="the core removed 2 blocks you hold — …"),
                         applied(HELD_P, {"c": "~"}, held={"a": "−", "b": "−"}))
check("two removals held: «Не застосовано: ядро прибрало 2 блоки», the blocks, and what to do",
      "### Не застосовано: ядро прибрало 2 блоки" in held and "- `a`" in held and "- `b`" in held
      and "ctx provider plan zorg-growth" in held and "ctx provider apply zorg-growth" in held, held)
check("…the table says it too: «запобіжник: ядро прибрало 2 блоки — не прибрано»",
      sum("запобіжник: ядро прибрало 2 блоки — не прибрано" in l for l in held.splitlines() if l.startswith("| `")) == 2, held)
held_only = sy.render_section(result_of("held", held=["a", "b"], snapshot=None), applied(plan_of(row("a", "−", source=None), row("b", "−", source=None)), {},
                                                                                         held={"a": "−", "b": "−"}, snapshot=None))
check("a held pass that wrote nothing: no way back to offer", held_only.splitlines()[-1] == "Знімка цього проходу немає: відкочувати нічого."
      and "ctx undo" not in held_only, held_only)

# a text you rejected
REJ_P = plan_of(row("a", "~", rejected=True, note="відкинуто вами — не застосовується, доки ядро не змінить блок"), row("b", "+", host=None))
rej = sy.render_section(result_of(added=1, rejected=["a"]), applied(REJ_P, {"b": "+"}, held={"a": "~"}), None, {"b": "product.zorg-app"})
check("a rejected text: «відкинуто вами раніше», held, and the way to take it",
      any("`a`" in l and "утримано" in l and "відкинуто вами раніше" in l for l in rej.splitlines() if l.startswith("| `"))
      and "Взяти текст ядра: ctx provider apply zorg-growth --choose a=theirs" in rej, rej)

# nothing known beyond the plan: no texts, no hosts, no apply
bare = sy.render_section(result_of(updated=1), applied(plan_of(row("a", "~", host=None)), {"a": "~"}), None, None, None)
check("no texts, no hosts and no base version known: the section is still whole (— for what is unknown)",
      "база v0.1 → v—" in bare and "| `a` | ~ | текст ядра |" in bare and bare.splitlines()[-1].startswith("Відкотити цей прохід"), bare)
empty = sy.render_section(result_of(), applied(plan_of(row("a", "="), row("b", "✎")), {"a": "=", "b": "✎"}))
check("a pass that moved only bases (nothing to list): a line says so, not an empty table", "Тексти не змінились" in empty
      and "| Блок |" not in empty, empty)

# passes with no plan: a source that is no source, an import that needs ctx sync, an unexpected failure
brk = sy.render_section(result_of("broken", snapshot=None, reason="every source answered with no blocks of zorg-growth"), None)
check("broken: the heading is only id and time; the reason is quoted; nothing was written; the check counts",
      brk.splitlines()[0] == "## zorg-growth · 09:00" and "### Джерело ядра не прийнято" in brk
      and "every source answered with no blocks of zorg-growth" in brk and "пропущено" in brk, brk)
imp = sy.render_section(result_of("import-conflict", snapshot=None, reason="the edits waiting to be imported need a decision (a) — `ctx sync` first"), None)
check("import-conflict: «спершу `ctx sync`», nothing written", "спершу `ctx sync`" in imp and "### Спершу `ctx sync`" in imp, imp)
err = sy.render_section(result_of("error", snapshot=None, reason="boom in the plan"), None)
check("error: the reason, a retry in an hour", "### Несподівана помилка" in err and "boom in the plan" in err and "за годину" in err, err)
check("every section ends with the way back, or says there is none",
      all(x.splitlines()[-1].startswith(("Відкотити цей прохід: ctx undo (знімок ", "Знімка цього проходу немає")) for x in (brk, imp, held_only, SEC)))
check("an unexpected failure may have written before it failed: the snapshot is unknown, `ctx status` shows the journal — not «nothing to undo»",
      err.splitlines()[-1].startswith("Знімок цього проходу невідомий") and "`ctx status`" in err.splitlines()[-1]
      and "відкочувати нічого" not in err and "Знімка цього проходу немає" not in err, err)
check("…an error that did leave a snapshot offers the way back as any pass does",
      sy.render_section(result_of("error", reason="boom"), None).splitlines()[-1] == "Відкотити цей прохід: ctx undo (знімок %s)" % SNAP)

# which outcomes write, and when a repeat is no news (§6.6)
check("changed, held, broken, import-conflict and error write a section; no-changes, unreachable and timeout do not",
      all(sy.reported(result_of(o)) for o in ("changed", "held", "broken", "import-conflict", "error"))
      and not any(sy.reported(result_of(o)) for o in ("no-changes", "unreachable", "timeout")))
prev = {"outcome": "held", "held": ["b", "a"], "reason": "R"}
check("a safeguard going off again with the same set (in any order) and the same reason is a repeat",
      sy.repeats(prev, result_of("held", held=["a", "b"], reason="R", snapshot=None)))
check("…a new block in the set, another reason, another outcome or a first time are not",
      not sy.repeats(prev, result_of("held", held=["a", "b", "c"], reason="R", snapshot=None))
      and not sy.repeats(prev, result_of("held", held=["a", "b"], reason="R2", snapshot=None))
      and not sy.repeats(dict(prev, outcome="changed"), result_of("held", held=["a", "b"], reason="R", snapshot=None))
      and not sy.repeats(None, result_of("held", held=["a", "b"], reason="R", snapshot=None)))
check("…a pass that wrote something else (a snapshot) is news all the same",
      not sy.repeats(prev, result_of("held", held=["a", "b"], reason="R", snapshot=SNAP)))
check("broken, import-conflict and error repeat by reason; changed never repeats",
      all(sy.repeats({"outcome": o, "held": [], "reason": "why"}, result_of(o, reason="why", snapshot=None)) for o in ("broken", "import-conflict", "error"))
      and not sy.repeats({"outcome": "changed", "held": [], "reason": None}, result_of("changed", snapshot=None)))
check("a hand-edited state (not an object, held not a list) is no repeat and does not raise",
      not sy.repeats("x", result_of("held", held=["a"], snapshot=None)) and not sy.repeats({"outcome": "held", "held": 3}, result_of("held", held=["a"], snapshot=None)))

# render_report / write_report
doc = sy.render_report("2026-10-16", [("zorg-growth", SEC), ("zorg-core", "## zorg-core · 09:01\n\nsecond\n")])
check("a report: frontmatter type system, kind context-sync, date, repos; the title; the sections in order",
      doc.startswith("---\ntype: system\nkind: context-sync\ndate: 2026-10-16\nrepos: [zorg-growth, zorg-core]\n---\n\n# Синк контексту — 2026-10-16\n\n## zorg-growth · 09:00")
      and doc.index("## zorg-growth") < doc.index("## zorg-core") and doc.endswith("second\n"), doc[:260])
check("…sections as plain texts name their repository by the heading; a repeated id is listed once",
      sy.render_report("2026-10-16", [SEC, SEC]).count("repos: [zorg-growth]") == 1)

with tempfile.TemporaryDirectory() as d:
    store = cs.Store(os.path.join(d, "Notes", "_System", "context"))
    check("the store knows its report folder: <root>/sync", store.sync_dir == os.path.join(store.root, "sync"))
    path = os.path.join(store.sync_dir, "2026-10-16.md")
    rel = sy.write_report(store, "2026-10-16", SEC)
    check("write_report: the path from the storage root", rel == "_System/context/sync/2026-10-16.md", rel)
    first = open(path, encoding="utf-8", newline="").read()
    check("…a new day's file: frontmatter, title, the section", first == sy.render_report("2026-10-16", [("zorg-growth", SEC)]), first[:200])
    sec2 = "## zorg-core · 09:01\n\nthe second pass of the day\n"
    sy.write_report(store, "2026-10-16", sec2)
    second = open(path, encoding="utf-8", newline="").read()
    check("…the same day again appends a section and completes `repos` in the frontmatter",
          second.startswith(first.replace("repos: [zorg-growth]", "repos: [zorg-growth, zorg-core]").rstrip("\n"))
          and second.endswith("the second pass of the day\n") and "repos: [zorg-growth, zorg-core]" in second, second)
    sy.write_report(store, "2026-10-16", "## zorg-growth · 10:00\n\nthird\n")
    third = open(path, encoding="utf-8", newline="").read()
    check("…a repository already listed is not listed twice; the earlier sections are untouched",
          "repos: [zorg-growth, zorg-core]\n" in third and third.startswith(second.rstrip("\n")) and third.count("## zorg-growth") == 2, third)
    check("…the section is separated from the one before by a blank line", "\n\n## zorg-core · 09:01" in third and "\n\n## zorg-growth · 10:00" in third)
    check("…no temp file is left behind", [n for n in os.listdir(store.sync_dir)] == ["2026-10-16.md"], os.listdir(store.sync_dir))
    open(path, "w", encoding="utf-8").write("my own note, no frontmatter\n")
    sy.write_report(store, "2026-10-16", sec2)
    check("a file you rewrote by hand (no frontmatter): the section is appended and your text is kept",
          open(path, encoding="utf-8").read() == "my own note, no frontmatter\n\n" + sec2, open(path, encoding="utf-8").read())
    try:
        sy.write_report(store, "../../escape", SEC)
        escaped = True
    except ValueError:
        escaped = False
    check("a date that is no date is refused (it names a file)", not escaped and not os.path.exists(os.path.join(d, "escape.md")))
    stray = store.stray_files()
    check("the store's stray files do not include the report folder", stray == [], stray)

# prune_reports: older than 90 days into ~/.grow-pm/trash/
with tempfile.TemporaryDirectory() as d:
    store = cs.Store(os.path.join(d, "Notes", "_System", "context"))
    home = os.path.join(d, "home")
    os.makedirs(os.path.join(home, ".grow-pm"))
    today = datetime.date(2026, 10, 16)
    names = {k: (today - datetime.timedelta(days=k)).isoformat() for k in (0, 89, 90, 91, 400)}
    os.makedirs(store.sync_dir)
    for k, n in names.items():
        open(os.path.join(store.sync_dir, n + ".md"), "w", encoding="utf-8").write("report %d\n" % k)
    open(os.path.join(store.sync_dir, "notes.md"), "w", encoding="utf-8").write("mine\n")
    open(os.path.join(store.sync_dir, "2020-01-01.txt"), "w", encoding="utf-8").write("mine\n")
    gone = sy.prune_reports(store, home, AT)
    left = sorted(os.listdir(store.sync_dir))
    trash = sorted(os.listdir(co.trash_root(home)))
    check("a report 91 days old goes to the trash, 89 stays (90 is not older than 90)",
          sorted(gone) == sorted([names[91] + ".md", names[400] + ".md"])
          and names[89] + ".md" in left and names[90] + ".md" in left and names[0] + ".md" in left
          and names[91] + ".md" not in left and names[400] + ".md" not in left, (gone, left))
    check("…only files named for a day are touched: notes.md and a .txt stay", "notes.md" in left and "2020-01-01.txt" in left, left)
    check("…the trash holds them under the trash's own naming (<time>-<name>.md), their text intact",
          len(trash) == 2 and all(co.TRASH_RE.match(n) for n in trash)
          and sorted(open(os.path.join(co.trash_root(home), n), encoding="utf-8").read() for n in trash) == ["report 400\n", "report 91\n"], trash)
    check("…and the trash's own 30-day purge sees them as its own", co.purge_trash(home, datetime.datetime(2026, 10, 16, 12, 0)) == [], trash)
    check("…a second pass finds nothing more", sy.prune_reports(store, home, AT) == [])
    empty_store = cs.Store(os.path.join(d, "none", "context"))
    check("a store with no report folder: nothing to do, no error", sy.prune_reports(empty_store, home, AT) == [])
    check("a now that is no time prunes nothing and raises nothing", sy.prune_reports(store, home, "yesterday") == [])

# ------------------------------------------------------------------ fix round 1
import errno  # noqa: E402

# (1) a ? that begins to wait is reported once (§5.1: «звіт називає блок один раз»), though the pass changed nothing
WAIT_P = plan_of(row("q", "?"), row("old", "?"), row("r", "~", rejected=True, note="відкинуто вами"))
WAIT_TX = {"mine": {"q": reg("zorg-growth", "q", "0.1", "my q"), "old": reg("zorg-growth", "old", "0.1", "my old")},
           "theirs": {"q": reg("zorg-growth", "q", "0.2", "core q"), "old": reg("zorg-growth", "old", "0.2", "core old")}}
WAIT_R = result_of("no-changes", awaiting=["q", "old"], snapshot=None)
check("a pass that changed nothing but left a block waiting for a decision is reported; one with nothing waiting is not",
      sy.reported(WAIT_R) and not sy.reported(result_of("no-changes", snapshot=None)) and not sy.reported(result_of("unreachable", awaiting=["q"])))
check("new_waiting: the waiting blocks the last sync_result did not have, in order; a state that is no object names none, so all are new",
      sy.new_waiting(None, WAIT_R) == ["q", "old"] and sy.new_waiting({"awaiting": ["old"]}, WAIT_R) == ["q"]
      and sy.new_waiting({"awaiting": ["q", "old", "x"]}, WAIT_R) == [] and sy.new_waiting({"awaiting": 3}, WAIT_R) == ["q", "old"]
      and sy.new_waiting("x", WAIT_R) == ["q", "old"])
check("the same waiting set on a later pass is a repeat; a new block in the set is not; a block gone from the set is nothing new",
      sy.repeats({"outcome": "no-changes", "awaiting": ["old", "q"]}, WAIT_R)
      and not sy.repeats({"outcome": "no-changes", "awaiting": ["q"]}, WAIT_R)
      and sy.repeats({"outcome": "no-changes", "awaiting": ["q", "old", "x"]}, WAIT_R)
      and not sy.repeats(None, WAIT_R) and not sy.repeats("x", WAIT_R))
check("a safeguard that repeats is news again when a new block waits beside it; a changed pass never repeats",
      not sy.repeats({"outcome": "held", "held": ["a", "b"], "reason": "R", "awaiting": []}, result_of("held", held=["a", "b"], reason="R", awaiting=["q"], snapshot=None))
      and sy.repeats({"outcome": "held", "held": ["a", "b"], "reason": "R", "awaiting": ["q"]}, result_of("held", held=["a", "b"], reason="R", awaiting=["q"], snapshot=None))
      and not sy.repeats({"outcome": "changed", "awaiting": ["q"]}, result_of("changed", awaiting=["q"])))
wait = sy.render_section(WAIT_R, applied(WAIT_P, {}, pending=["q", "old"], snapshot=None, held={"r": "~"}), WAIT_TX, None, "0.1", only=["q"])
check("the part of a pass that only began to wait: the heading, a line saying nothing changed, ONE row — the new block (`old` was named before)",
      wait.splitlines()[0].startswith("## zorg-growth · 09:00 · джерело") and "Прохід нічого не змінив; блоків, що чекають твого рішення: 1." in wait, wait)
wrows = [l for l in wait.splitlines() if l.startswith("| `")]
check("…the table has the one row, «чекає рішення»; `old` and the rejected `r` are not in the part",
      len(wrows) == 1 and "`q`" in wrows[0] and "чекає рішення" in wrows[0] and "`old`" not in wait and "`r`" not in wait
      and "Відкинуто" not in wait, wait)
check("…both texts and both commands, the block named once",
      wait.count("### Конфлікт: `q` — чекає рішення") == 1 and "my q" in wait and "core q" in wait
      and "Взяти текст ядра: ctx provider apply zorg-growth --choose q=theirs" in wait
      and "Лишити своє: ctx provider apply zorg-growth --choose q=mine" in wait, wait)
check("…nothing was written, so it ends by saying there is nothing to undo", wait.splitlines()[-1] == "Знімка цього проходу немає: відкочувати нічого.")
every = sy.render_section(WAIT_R, applied(WAIT_P, {}, pending=["q", "old"], snapshot=None, held={"r": "~"}), WAIT_TX, None, "0.1")
check("without `only` every waiting block is in the part", len([l for l in every.splitlines() if l.startswith("| `")]) == 3 and "`old`" in every)

# (3) one huge line of a server's text must not bloat the note
HUGE = sy.render_section(result_of(kept_yours=["big"]), applied(BIG, {"big": "⚠ mine"}),
                         {"mine": {"big": reg("zorg-growth", "big", "0.1", "x" * 10000 + "\nnext line")},
                          "theirs": {"big": reg("zorg-growth", "big", "0.2", "y" * 500 + "\n" + "z" * 501 + "\n  indented")}})
check("a line of 10 000 characters shows 500 at most, the last one «…», and the lines after it are still there",
      max(len(l) for l in HUGE.splitlines()) <= 500 and ("x" * 499 + "…") in HUGE and ("x" * 500) not in HUGE and "next line" in HUGE, [len(l) for l in HUGE.splitlines()])
check("…a line of exactly 500 stays whole, one of 501 is cut; the indentation of a short line is kept",
      ("y" * 500) in HUGE and ("y" * 499 + "…") not in HUGE and ("z" * 499 + "…") in HUGE and "\n  indented\n" in HUGE)

# (2) the trash: check the target first, never two copies, never through a link
def old_report(store, k, text="an old report\n"):
    day = (datetime.date(2026, 10, 16) - datetime.timedelta(days=k)).isoformat()
    os.makedirs(store.sync_dir, exist_ok=True)
    path = os.path.join(store.sync_dir, day + ".md")
    open(path, "w", encoding="utf-8").write(text)
    return day, path


def trash_files(home):
    root = co.trash_root(home)
    return sorted(os.listdir(root)) if os.path.isdir(root) else []


if os.geteuid() != 0:
    with tempfile.TemporaryDirectory() as d:
        store, home = cs.Store(os.path.join(d, "Notes", "_System", "context")), os.path.join(d, "home")
        os.makedirs(os.path.join(home, ".grow-pm"))
        day, path = old_report(store, 100)
        os.chmod(store.sync_dir, 0o555)                     # the original cannot be moved or removed
        try:
            first, second = sy.prune_reports(store, home, AT), sy.prune_reports(store, home, AT)
        finally:
            os.chmod(store.sync_dir, 0o755)
        check("a report that cannot be removed is left where it is and is not put in the trash — not once, not on the second sync",
              first == [] and second == [] and os.path.exists(path) and trash_files(home) == [], (first, second, trash_files(home)))
        check("…and when the folder is writable again the next sync moves it, once", sy.prune_reports(store, home, AT) == [day + ".md"]
              and not os.path.exists(path) and len(trash_files(home)) == 1)

real_rename, real_remove = os.rename, os.remove


def across_volumes(src, dst):
    raise OSError(errno.EXDEV, "Invalid cross-device link", src)


with tempfile.TemporaryDirectory() as d:                     # the vault and ~/.grow-pm on different volumes: copy, then remove
    store, home = cs.Store(os.path.join(d, "Notes", "_System", "context")), os.path.join(d, "home")
    os.makedirs(os.path.join(home, ".grow-pm"))
    day, path = old_report(store, 100, "across\n")
    os.rename = across_volumes
    try:
        gone = sy.prune_reports(store, home, AT)
    finally:
        os.rename = real_rename
    check("across volumes the report is copied and the original removed: one copy, in the trash, whole",
          gone == [day + ".md"] and not os.path.exists(path) and len(trash_files(home)) == 1
          and open(os.path.join(co.trash_root(home), trash_files(home)[0]), encoding="utf-8").read() == "across\n", (gone, trash_files(home)))

with tempfile.TemporaryDirectory() as d:                     # …and the remove fails: the copy is taken back out
    store, home = cs.Store(os.path.join(d, "Notes", "_System", "context")), os.path.join(d, "home")
    os.makedirs(os.path.join(home, ".grow-pm"))
    day, path = old_report(store, 100, "stays\n")

    def refusing_remove(p, *a, **k):
        if str(p).startswith(store.sync_dir):
            raise PermissionError(errno.EACCES, "Permission denied", p)
        return real_remove(p, *a, **k)

    os.rename, os.remove = across_volumes, refusing_remove
    try:
        first, second = sy.prune_reports(store, home, AT), sy.prune_reports(store, home, AT)
    finally:
        os.rename, os.remove = real_rename, real_remove
    check("…a remove that fails takes its copy back out of the trash: the trash is empty after the first sync and after the second",
          first == [] and second == [] and os.path.exists(path) and trash_files(home) == [], (first, second, trash_files(home)))

with tempfile.TemporaryDirectory() as d:                     # a symlinked report folder leads outside: nothing of it is copied
    outside = os.path.join(d, "Elsewhere")
    os.makedirs(outside)
    secret = os.path.join(outside, "2020-01-01.md")
    open(secret, "w", encoding="utf-8").write("not a report of the sync\n")
    store, home = cs.Store(os.path.join(d, "Notes", "_System", "context")), os.path.join(d, "home")
    os.makedirs(store.root)
    os.makedirs(os.path.join(home, ".grow-pm"))
    os.symlink(outside, store.sync_dir)
    guard_ok = sy.prune_reports(store, home, AT)
    with cs.guard_roots([store.root, os.path.join(home, ".grow-pm")]):
        guarded = sy.prune_reports(store, home, AT)
    check("a report folder that is a symlink to somewhere else: nothing is read, copied to the trash or removed — with the write guard or without",
          guard_ok == [] and guarded == [] and os.path.exists(secret) and trash_files(home) == [], (guard_ok, guarded, trash_files(home)))
    os.remove(store.sync_dir)
    os.makedirs(store.sync_dir)
    day = (datetime.date(2026, 10, 16) - datetime.timedelta(days=100)).isoformat()
    os.symlink(secret, os.path.join(store.sync_dir, day + ".md"))
    with cs.guard_roots([store.root, os.path.join(home, ".grow-pm")]):
        guarded = sy.prune_reports(store, home, AT)
    check("…and a report that is itself a link to a file outside the guarded roots is refused before it is read",
          guarded == [] and os.path.exists(secret) and trash_files(home) == [], (guarded, trash_files(home)))

print("RESULT: GREEN ✅" if not fails else "RESULT: RED ❌")
sys.exit(1 if fails else 0)
