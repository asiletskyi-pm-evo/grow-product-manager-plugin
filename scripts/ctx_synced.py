#!/usr/bin/env python3
"""Grow PM — the daily core sync (since v3.14.0): `ctx provider sync [REPO] [--if-due] [--now ISO]`.

A repository registered with `sync: daily` is brought up to date once a day without a person at the keyboard
(spec Context-Core-v3.14 §3–§8). The sync is `ctx provider apply` with the answers given in advance, and the
answers come from one place:

- decide    the plan's rows in, the pass's answers out: `choose` (block → "mine" | "theirs", exactly what `apply`
            takes), `add` (the "+" blocks), `hold` (the blocks `apply` must not touch), and the names the report and
            the digest speak in — `held_removals`, `awaiting`, `rejected`, `kept_yours`, `took_rule`
- due       is a repository due: `sync: daily`, not paused, a day since its last successful check (`checked`) and an hour
            since a failed attempt after it (`sync_attempt`); a time more than a day ahead is another clock's — unknown
- pick_due  the repositories that are due, read from their block states without the lock and without the network
- run       the pass over the repositories given: the lock (busy → nothing, at once), the guard, the import of the edits
            waiting, then each repository — fetched in a helper thread held to the budget, planned, decided, applied
            (op "provider-sync") — and its result written into its block state (`sync_result`, `sync_attempt`)
- sentence  the one line a skill repeats at the end of its answer when a pass changed something

`decide` reads nothing and writes nothing: the plan is `ctx_blocks.plan`'s, the repository's texts are
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

The outcome of a repository's pass (§4.3, §6): "changed" (the pass wrote: a snapshot and a journal line), "no-changes"
(only the time of the check moved), "held" (more than one removal held — a successful check all the same), "broken"
(the blocks file holds none of your based blocks, or something of the store failed — see `run`), "unreachable" (the
fetch failed; retried in an hour), "timeout" (the budget ran out before or during the pass, or the client gave up at
its deadline; retried in an hour), "import-conflict" (the edits waiting in local-context.md could not be imported;
nothing is written to the records).

Stdlib only.
"""
import contextlib
import datetime
import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx_blocks as cb  # noqa: E402
import ctx_mcp as cm  # noqa: E402
import ctx_ops as co  # noqa: E402
import ctx_repos as crp  # noqa: E402
import ctx_store as cs  # noqa: E402

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


# ------------------------------------------------------------------ when (spec §4.1–§4.3)
OP = "provider-sync"                            # the journal's op and the snapshot's label of a sync pass
DUE_AFTER = datetime.timedelta(hours=24)        # due a day after the last successful check
RETRY_AFTER = datetime.timedelta(hours=1)       # …and no sooner than an hour after a failed attempt that came after it
AHEAD = datetime.timedelta(days=1)              # a time further ahead than this is another Mac's clock: unknown
BUDGET_S = 20.0                                 # the whole sync, every repository together
RESERVE_S = 1.0                                 # the last second of it is kept for writing down what happened
RECORD_S = 0.5                                  # the least a result's write waits for the block state (a small local file)
DUE_READ_S = 2.0                                # the block states --if-due reads, all of them together
OUTCOMES = ("changed", "no-changes", "unreachable", "broken", "held", "import-conflict", "timeout")
RESULT_KEYS = ("at", "outcome", "updated", "added", "removed", "kept_yours", "took_rule", "awaiting", "held", "rejected",
               "reason", "report", "snapshot")
MOVED = ("changed", "no-changes", "held", "broken")     # the outcomes of a successful check: the state's `checked` moved


def instant(value):
    """`value` — an ISO text (a final Z is UTC; with no offset it is local time) or a datetime — as an aware datetime;
    None when it is neither."""
    if isinstance(value, datetime.datetime):
        t = value
    elif isinstance(value, str) and value.strip():
        text = value.strip()
        if text[-1] in "Zz":
            text = text[:-1] + "+00:00"
        try:
            t = datetime.datetime.fromisoformat(text)
        except ValueError:
            return None
    else:
        return None
    return t if t.tzinfo is not None else t.astimezone()


def _known(value, now):
    """The time `value` names, or None: none, not a time, or more than a day after `now` (another clock — unknown)."""
    t = instant(value)
    return None if t is None or t - now > AHEAD else t


def due(repo, state, now):
    """Is the repository due at `now` (an ISO text or a datetime)? Never for a registration without `sync: daily` or a
    paused one. Otherwise when there is no successful check (`state["checked"]`), or it is 24 h old or more — and the last
    attempt (`state["sync_attempt"]`) is absent, an hour old or more, or no later than that check. A time more than a
    day after `now` counts as absent: unknown, so due (§4.3, two Macs). Reads `state` only."""
    repo, state = repo or {}, state or {}
    if repo.get("sync") != crp.SYNC_DAILY or repo.get("status") == "paused":
        return False
    t = instant(now)
    if t is None:
        raise ValueError("not a time: %r" % (now,))
    checked = _known(state.get("checked"), t)
    if checked is not None and t - checked < DUE_AFTER:
        return False
    attempt = _known(state.get("sync_attempt"), t)
    if attempt is not None and (checked is None or attempt > checked) and t - attempt < RETRY_AFTER:
        return False
    return True


def pick_due(store, repos, now):
    """The repositories of `repos` that are due at `now`, in their order — from their block states alone: no lock, no
    network, every state read within DUE_READ_S in all. A state that cannot be read (in time, or at all) is unknown:
    the repository is due, and its pass says why."""
    out = []
    with cs.read_budget(DUE_READ_S):
        for repo in repos:
            try:
                state = cb.load_state(store, repo["id"])
            except (cs.StoreError, OSError, ValueError):
                state = {}
            if due(repo, state, now):
                out.append(repo)
    return out


# ------------------------------------------------------------------ the pass
def _left(until):
    """Seconds left until `until` (a time.monotonic() moment), never below 0."""
    return max(0.0, until - time.monotonic())


def _result(now, outcome, reason=None, **fields):
    """A repository's result as the state keeps it (`sync_result`): every key of RESULT_KEYS."""
    out = {"at": now, "outcome": outcome, "updated": 0, "added": 0, "removed": 0, "kept_yours": [], "took_rule": [],
           "awaiting": [], "held": [], "rejected": [], "reason": cb.clip(reason, cb.NOTE_CLIP) if reason else None,
           "report": None, "snapshot": None}
    out.update(fields)
    return out


def public(result):
    """A result of `run` as CTX_RESULT carries it: the repository's id and the keys of the state's `sync_result`."""
    return dict([("repo", result["repo"])] + [(k, result[k]) for k in RESULT_KEYS])


def _fetch_within(repo, now, until):
    """(fetched, late, why) of one repository. The fetch runs in a daemon thread joined against what is left until
    `until`, and the client keeps `until` as its deadline: a DNS lookup that hangs (VPN off) or a server that trickles
    costs the budget and no more (late True; the thread is left behind — it only reads, and the command ends soon).
    A fetch that raised is (None, False, why)."""
    box = {}

    def work():
        try:
            box["fetched"] = crp.fetch(repo, now=now, deadline=until)
        except BaseException as e:  # noqa: BLE001 — handed back below
            box["error"] = e

    worker = threading.Thread(target=work, name="ctx-sync-fetch", daemon=True)
    worker.start()
    worker.join(_left(until))
    if worker.is_alive():
        return None, True, "no answer within the sync's %g s budget" % BUDGET_S
    if "error" in box:
        return None, False, "the fetch failed unexpectedly (%s)" % type(box["error"]).__name__
    return box["fetched"], False, None


def _counts(res, theirs):
    """{"updated", "added", "removed"} of an apply: the blocks whose text became the repository's ("~", theirs, both),
    the "+" added and the blocks removed ("−", theirs for a block the repository no longer has). A block kept as yours
    is none of them."""
    out = {"updated": 0, "added": 0, "removed": 0}
    for bid, decision in res["decisions"].items():
        sign, _, how = decision.partition(" ")
        if sign == "+":
            out["added"] += 1
        elif sign == "−" or (how == THEIRS and theirs.get(bid) is None):
            out["removed"] += 1
        elif sign == "~" or how in (THEIRS, "both"):
            out["updated"] += 1
    return out


def _pass(c, repo, now, until):
    """(result, the apply's result or None, did the check succeed without an apply) of one repository, by `until`.
    The block state is read first (one that cannot be read stops the pass before the network); then the fetch; a fetch
    error is "timeout" when it says the deadline was reached, else "unreachable"; a blocks file that holds none of your
    based blocks is "broken"; else plan → decide → apply, which writes the state's `checked` itself. Store reads run
    within what is left of the budget."""
    rid = repo["id"]
    with cs.read_budget(_left(until)):
        cb.load_state(c.store, rid)
    fetched, late, why = _fetch_within(repo, now, until)
    error = why if fetched is None else fetched.get("error")
    if late or (error and cm.DEADLINE in error):
        return _result(now, "timeout", error), None, False
    if error:
        return _result(now, "unreachable", error), None, False
    with cs.read_budget(_left(until)):
        lost = cb.source_lost(c.store, c.copies, repo, fetched, now)
        if lost:
            return _result(now, "broken", lost), None, True
        theirs = cb._theirs(fetched)[0]
        answers = decide(cb.plan(c.store, c.copies, repo, fetched, now), theirs)
        res = cb.apply(c.store, c.copies, c.home, repo, fetched, answers["choose"], answers["add"], now, op=OP,
                       hold=answers["hold"])
    gone = answers["held_removals"]
    outcome = "held" if gone else ("changed" if res["changed"] else "no-changes")
    shown = cb.clip(rid, cb.HEADER_CLIP)
    reason = ("the core removed %d blocks you hold — none removed (§6.1); `ctx provider plan %s` shows them, "
              "`ctx provider apply %s` removes them" % (len(gone), shown, shown)) if gone else None
    return _result(now, outcome, reason, snapshot=res["snapshot"], kept_yours=answers["kept_yours"],
                   took_rule=answers["took_rule"], awaiting=answers["awaiting"], held=gone, rejected=answers["rejected"],
                   **_counts(res, theirs)), res, False


def _record(store, rid, result, checked, deadline):
    """Write `result` into the repository's block state: `sync_result`, `sync_attempt` (the pass's time) and — for a
    successful check that no apply wrote (a broken source) — `checked`. Within what is left of the budget, and never
    less than RECORD_S. A state that cannot be read or written is left as it is (False)."""
    try:
        with cs.read_budget(max(RECORD_S, _left(deadline))):
            state = cb.load_state(store, rid)
            state["sync_attempt"] = result["at"]
            state["sync_result"] = {k: result[k] for k in RESULT_KEYS}
            if checked:
                state["checked"] = checked
            cb.save_state(store, rid, state)
    except (cs.StoreError, cs.PathRefused, OSError, ValueError, TypeError):
        return False
    return True


def _import_failed(e):
    """The reason of an import that did not go through: the records it disagrees on, and `ctx sync` first."""
    if isinstance(e, co.Conflict):
        ids = [x.get("id") for x in (e.payload.get("conflicts") or []) if isinstance(x, dict) and x.get("id")]
        what = ", ".join(ids) if ids else ("removals to confirm" if e.payload.get("suspicious_removal") else str(e))
        what = "the edits waiting to be imported need a decision (%s)" % what
    else:
        what = "the edits waiting could not be imported (%s)" % (str(e) or type(e).__name__)
    return "%s — `ctx sync` first" % cb.clip(what, cb.NOTE_CLIP - 20)


def run(c, repos, now, deadline):
    """One sync pass over `repos` (repository dicts, `sync: daily`) at `now` (ISO text), by `deadline` (a time.monotonic()
    moment; the command gives BUDGET_S). `c` is the command line's context (`ctx.Ctx`: store, copies, home, guard,
    import_first). Returns one result per repository — `public`'s keys and `apply` (the apply's result, its plan with the
    rows, or None), for the report — and writes each into the repository's block state (`sync_result`, `sync_attempt`).

    1. The lock: held by another session (co.Busy) → [] at once, nothing written — so is a guard that refuses (a
       registration still downloading: the provider boundary cannot be checked).
    2. The edits waiting in local-context.md are imported first, as by every writing command; when they cannot be (a
       conflict for `ctx sync`), every repository is "import-conflict" and nothing is written to the records.
    3. Each repository in turn, while the budget lasts (its last RESERVE_S kept for the writing down): `_pass`. The
       budget gone before a repository, or during its pass, is "timeout"; a failure of the store in a pass is "broken"
       with its reason (the check does not move: retried in an hour). One repository's failure never stops the next.
    4. The card's line about the repositories, when a check moved and time is left."""
    stack = contextlib.ExitStack()
    try:
        stack.enter_context(co.lock(c.home))
    except (co.Busy, OSError):
        return []
    with stack:
        try:
            c.guard()
        except (co.Refused, cs.PathRefused, cs.StoreError, OSError):
            return []
        until = deadline - RESERVE_S
        failed = None
        try:
            with cs.read_budget(_left(until)):
                c.import_first()
        except Exception as e:  # noqa: BLE001 — an import that cannot go through stops the writing, never the skill
            failed = _result(now, "timeout" if not isinstance(e, co.Conflict) and _left(until) <= 0 else "import-conflict",
                             _import_failed(e))
        results = []
        for repo in repos:
            rid, res, checked = repo["id"], None, False
            if failed:
                result = dict(failed)
            elif _left(until) <= 0:
                result = _result(now, "timeout", "the sync's %g s budget ran out before this repository" % BUDGET_S)
            else:
                try:
                    result, res, checked = _pass(c, repo, now, until)
                except cb.SourceLost as e:          # the state moved between the check and the plan
                    result, checked = _result(now, "broken", str(e)), True
                except Exception as e:  # noqa: BLE001 — one repository's failure never stops the next (§6.4)
                    result = _result(now, "timeout" if _left(until) <= 0 else "broken", str(e) or type(e).__name__)
            _record(c.store, rid, result, now if checked else None, deadline)
            results.append(dict(result, repo=rid, apply=res))
        if any(r["outcome"] in MOVED for r in results) and _left(deadline) > 0:
            try:                                    # the card's Repos line says when each repository was checked
                with cs.read_budget(_left(deadline)):
                    co.refresh_card_repos(c.store, c.home, now[:10])
            except Exception:  # noqa: BLE001 — a card line is not worth a sync's result
                pass
        return results


def news(result):
    """Did the pass change a block of yours or decide a conflict — so the skill says one sentence?"""
    return bool(result["updated"] + result["added"] + result["removed"] + len(result["kept_yours"]))


def sentence(result):
    """`Ядро оновило <N> <блок|блоки|блоків> у <repo>, конфліктів <K> (лишено твоє) — звіт: <path>`: N the blocks
    updated, added and removed, K the conflicts kept yours; the report clause only when there is a report."""
    n = result["updated"] + result["added"] + result["removed"]
    text = "Ядро оновило %d %s у %s, конфліктів %d (лишено твоє)" % (n, cs.blocks_word(n), cb.clip(result["repo"], cb.HEADER_CLIP),
                                                                    len(result["kept_yours"]))
    return text + (" — звіт: %s" % result["report"] if result.get("report") else "")
