#!/usr/bin/env python3
"""Grow PM — the daily core sync (since v3.14.0): `ctx provider sync [REPO] [--if-due] [--now ISO]`.

A repository registered with `sync: daily` is brought up to date once a day without a person at the keyboard
(spec Context-Core-v3.14 §3–§8). The sync is `ctx provider apply` with the answers given in advance, and the
answers come from one place:

- decide    the plan's rows in, the pass's answers out: `choose` (block → "mine" | "theirs", exactly what `apply`
            takes), `add` (the "+" blocks), `hold` (the blocks `apply` must not touch), and the names the report and
            the digest speak in — `held_removals`, `held_behind`, `awaiting`, `rejected`, `kept_yours`, `took_rule`
- due       is a repository due: `sync: daily`, not paused, a day since its last successful check (`checked`) and an hour
            since a failed attempt after it (`sync_attempt`); a time more than a day ahead is another clock's — unknown
- pick_due  the repositories that are due, read from their block states without the lock and without the network
- run       the pass over the repositories given: the lock (busy → nothing, at once), the due check again under it, the
            guard, the import of the edits waiting, then each repository — fetched in a helper thread held to the budget,
            planned, decided, applied (op "provider-sync") — and its result written into its block state (`sync_result`,
            `sync_attempt`)
- sentence  the one line a skill repeats at the end of its answer when a pass changed something
- the report `{storage_root}/_System/context/sync/YYYY-MM-DD.md` (spec §7), written into the vault for the person to read:
            render_section (one repository's part: the table of decisions in the cascade's words, both texts of every
            conflict, the way back), render_report / write_report (the day's file: frontmatter, title, parts appended),
            prune_reports (older than 90 days into ~/.grow-pm/trash/), reported / repeats (which passes write a part)

`decide` reads nothing and writes nothing: the plan is `ctx_blocks.plan`'s, the repository's texts are
`{block: text}` from `ctx_blocks._theirs(fetched)[0]` (a block the repository removed is absent). Rules, in this order
(§5.1, §5.2, §6.1):

1. a text you rejected by undoing a sync pass (`rejected: True`) is held, whatever else it is — a rule included
1a. a plan whose source lags behind your bases (`lagging`, since v3.14.0) holds every other row that would change a block
   (~ + − ⚠ ?), a rule included: nothing is taken from a copy older than what you hold — and a "?" so held that is no core
   rule still awaits your decision (`awaiting`), as it would from a current copy
2. more than one block the repository removed in a pass (a "−", or a "⚠" / "?" whose repository text is None) is held,
   none of them goes through; a rejected row is held already and is not counted
3. "⚠" takes the repository's text when it is a core rule (`ctx_blocks.is_rule`, read from the begin marker of the
   repository's text), else keeps yours — and keeps yours when the repository removed the block
4. "?" takes a rule, else waits: not in `choose`, so `apply` leaves it pending and the base does not move
5. "+" is added
6. "=", "~", "✎", a lone "−", "✂", "·": nothing — `apply` acts by itself

The outcome of a repository's pass (§4.3, §6):
- "changed"          the pass wrote: a snapshot and a journal line
- "no-changes"       only the time of the check moved
- "held"             more than one removal held — a successful check all the same
- "broken"           the source answered with no source: every source tried gave an empty, cut or foreign blocks file
                     (`fetch`'s `unsound`), or the file holds none of your based blocks — a successful check: next in a day
- "unreachable"      the fetch failed otherwise (no answer, a server error); retried in an hour
- "timeout"          the budget ran out before or during the pass, the client gave up at its deadline, or less than
                     APPLY_MIN_S was left before the fetch, the plan or the write; retried in an hour, nothing written
- "import-conflict"  the edits waiting in local-context.md need a decision (`ctx sync`); nothing written to the records
- "error"            something failed unexpectedly — the store (a record missing or not downloaded: "store: <why>"), a
                     fetch that raised (a bug, never blamed on the network), or anything else (its message); retried in
                     an hour

A pass over a source that lags behind your bases (the plan's `lagging`) holds every block it would have changed
(`decide` 1a): it writes no record, its reason says the source is behind and `held_behind` names the blocks — "no-changes"
(or "changed" when only the block state moved), a successful check. It is never silent: the report names a new set of
blocks held behind once (`reported`, `repeats`), and the digest marks the repository "⚠ source behind — nothing taken".

Stdlib only.
"""
import contextlib
import datetime
import errno
import os
import re
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
CHANGES = ("~", "+", "−", "⚠", "?")                 # the signs whose row would change a block: a lagging copy holds them all


def _rows(plan):
    """The rows of a plan: `ctx_blocks.plan`'s dict, or the bare list of its rows."""
    return list(plan.get("rows") or []) if isinstance(plan, dict) else list(plan or [])


def decide(plan, theirs):
    """The pass's answers for every row of `plan` (spec §5.1); `theirs` is `{block: the repository's text}`, a removed
    block absent from it (or None). Nothing is read or written, and nothing passed in is changed.

    Returns {"choose": {block: "mine" | "theirs"}, "add": [block], "hold": [block], "held_removals": [block],
    "held_behind": [block], "awaiting": [block], "rejected": [block], "kept_yours": [block], "took_rule": [block]} — the
    lists in plan order. `hold` names only blocks that are rows of the plan, and no block is in more than one of
    `choose`, `add` and `hold`. Whether a block is a core rule is read from the repository's text (`theirs`), never from
    the row. A plan that says its source lags (`lagging`, since v3.14.0: `ctx_blocks.source_lags`) holds every row that
    would change something ("~", "+", "−", "⚠", "?") — `held_behind`, a rule included, a rejected one still `rejected`:
    a copy older than your bases never takes a block back to an older text, never removes or re-adds one. A "?" so held
    that is no core rule is in `awaiting` too: a person's question all the same, which the digest goes on counting."""
    theirs = theirs or {}
    rows = _rows(plan)
    behind = isinstance(plan, dict) and bool(plan.get("lagging"))
    removed = [r["block"] for r in rows if not r.get("rejected") and not behind
               and (r["sign"] == "−" or (r["sign"] in QUESTIONS and theirs.get(r["block"]) is None))]
    guarded = set(removed) if len(removed) > 1 else set()          # §6.1: the repository removed more than one block
    out = {"choose": {}, "add": [], "hold": [], "held_removals": [], "held_behind": [], "awaiting": [], "rejected": [],
           "kept_yours": [], "took_rule": []}
    for row in rows:
        bid, sign = row["block"], row["sign"]
        text = theirs.get(bid)
        if row.get("rejected"):
            out["hold"].append(bid)
            out["rejected"].append(bid)
        elif behind and (sign in CHANGES or row.get("reoverlay")):     # since v3.23.0: nor the overlay laid again
            out["hold"].append(bid)
            out["held_behind"].append(bid)
            if sign == "?" and not cb.is_rule(text):    # held, and still a question for you: the digest counts it
                out["awaiting"].append(bid)
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
APPLY_MIN_S = 3.0                               # no fetch, plan or write starts with less of the budget left, and a write once
                                                # begun has at least this for its reads: records written without their journal
                                                # line would make `ctx undo` take back the wrong change
CARD_MIN_S = 1.0                                # the card's Repos line is refreshed at the end only with this much of it left
DUE_READ_S = 2.0                                # the block states --if-due reads, all of them together
OUTCOMES = ("changed", "no-changes", "unreachable", "broken", "held", "import-conflict", "timeout", "error")
RESULT_KEYS = ("at", "outcome", "updated", "added", "removed", "kept_yours", "took_rule", "awaiting", "held", "held_behind",
               "rejected", "reason", "report", "snapshot")
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
    """A repository's result as the state keeps it (`sync_result`): every key of RESULT_KEYS. `held_behind` (since the
    v3.14.0 final review) is absent from a result written before it — read as none held."""
    out = {"at": now, "outcome": outcome, "updated": 0, "added": 0, "removed": 0, "kept_yours": [], "took_rule": [],
           "awaiting": [], "held": [], "held_behind": [], "rejected": [],
           "reason": cb.clip(reason, cb.NOTE_CLIP) if reason else None,
           "report": None, "snapshot": None}
    out.update(fields)
    return out


def public(result):
    """A result of `run` as CTX_RESULT carries it: the repository's id and the keys of the state's `sync_result`."""
    return dict([("repo", result["repo"])] + [(k, result[k]) for k in RESULT_KEYS])


def _fetch_within(repo, now, until):
    """(fetched, late, raised) of one repository. The fetch runs in a daemon thread joined against what is left until
    `until`, and the client keeps `until` as its deadline: a DNS lookup that hangs (VPN off) or a server that trickles
    costs the budget and no more (late True; the thread is left behind — it only reads, and the command ends soon).
    A fetch that raised (it is documented never to: a bug) is (None, False, the exception)."""
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
        return None, True, None
    return box.get("fetched"), False, box.get("error")


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


def _conflicts(store, repo, fetched, plan, theirs):
    """The full texts of the blocks the plan asks about ("⚠" and "?", but not a text you rejected): {"mine": {block: your
    region}, "theirs": {block: the repository's region, None when it removed the block}}. Taken before the write, because a
    rule overwrites yours and the report shows it. Yours that cannot be read is left out (the report says where to look)."""
    asked = [r["block"] for r in _rows(plan) if r["sign"] in QUESTIONS and not r.get("rejected")]
    out = {"mine": {}, "theirs": {b: theirs.get(b) for b in asked}}
    if asked:
        try:
            regions = cb.find_regions(store.load(), cb.namespace_of(repo, fetched))[0]
            out["mine"] = {b: regions[b]["text"] for b in asked if b in regions}
        except (cs.StoreError, OSError, ValueError):
            pass
    return out


def _pass(c, repo, now, until, facts=None):
    """(result, the apply's result or None, did the check succeed without an apply) of one repository, by `until`.
    The block state is read first (one that cannot be read stops the pass before the network); then the fetch. A fetch
    that is late, or whose error says the deadline was reached, is "timeout"; one that raised is "error" (a bug: fetch
    never raises — never blamed on the network); one where every source answered an empty, cut or foreign text
    (`unsound`) is "broken"; any other fetch error is "unreachable". Less than APPLY_MIN_S left of the work time then
    (`until`: the budget less its last RESERVE_S) is "timeout" with nothing planned or written. A blocks file that holds
    none of your based blocks is "broken"; else plan → decide, and less than APPLY_MIN_S left after them is "timeout"
    with nothing written; else apply, which writes the state's `checked` itself. Store reads run within what is left of
    the budget — the apply's within no less than APPLY_MIN_S, so a write once begun never runs out of time for its
    reads between its records and its journal line (and the card it compiles reads the registrations on that budget,
    `co.card_repos`). `facts`, when a dict, gets what the report needs and only the pass has in hand before the write:
    `_conflicts`' full texts."""
    rid = repo["id"]
    with cs.read_budget(_left(until)):
        cb.load_state(c.store, rid)
    fetched, late, raised = _fetch_within(repo, now, until)
    if late:
        return _result(now, "timeout", "no answer within the sync's %g s budget" % BUDGET_S), None, False
    if raised is not None:
        return _result(now, "error", "the fetch failed unexpectedly — %s: %s"
                       % (type(raised).__name__, str(raised) or "no message")), None, False
    error = fetched.get("error")
    if error and fetched.get("unsound"):
        return _result(now, "broken", fetched["unsound"]), None, True
    if error:
        return _result(now, "timeout" if cm.DEADLINE in error else "unreachable", error), None, False
    if _left(until) < APPLY_MIN_S:
        return _result(now, "timeout", _short("after the fetch — nothing planned, nothing written")), None, False
    with cs.read_budget(_left(until)):
        lost = cb.source_lost(c.store, c.copies, repo, fetched, now)
        if lost:
            return _result(now, "broken", lost), None, True
        theirs = cb._theirs(fetched)[0]
        plan = cb.plan(c.store, c.copies, repo, fetched, now)
        answers = decide(plan, theirs)
        if facts is not None:
            facts.update(_conflicts(c.store, repo, fetched, plan, theirs))
    if _left(until) < APPLY_MIN_S:                  # the plan took the time: no write starts without its floor
        return _result(now, "timeout", _short("after the plan — nothing written")), None, False
    with cs.read_budget(max(_left(until), APPLY_MIN_S)):     # …and a write once begun keeps the floor for its reads
        res = cb.apply(c.store, c.copies, c.home, repo, fetched, answers["choose"], answers["add"], now, op=OP,
                       hold=answers["hold"])
    gone, lag = answers["held_removals"], answers["held_behind"]
    outcome = "held" if gone else ("changed" if res["changed"] else "no-changes")
    shown = cb.clip(rid, cb.HEADER_CLIP)
    reason = ("the core removed %d blocks you hold — none removed (§6.1); `ctx provider plan %s` shows them, "
              "`ctx provider apply %s` removes them" % (len(gone), shown, shown)) if gone else None
    if plan.get("lagging"):                         # a copy older than your bases: nothing of it was taken
        reason = ("the source is behind your bases (a copy older than the blocks you hold) — %d block%s not taken, nothing "
                  "written to your records; `ctx provider plan %s` shows them" % (len(lag), "" if len(lag) == 1 else "s", shown))
    return _result(now, outcome, reason, snapshot=res["snapshot"], kept_yours=answers["kept_yours"],
                   took_rule=answers["took_rule"], awaiting=answers["awaiting"], held=gone, held_behind=lag,
                   rejected=answers["rejected"], **_counts(res, theirs)), res, False


def _short(when):
    """The reason of the floor: what is actually checked — the work time left (`until`), which is the budget less its
    last RESERVE_S — against APPLY_MIN_S."""
    return ("less than %g s left of the sync's %g s budget once its last %g s, kept for writing down the results, is set "
            "aside, %s" % (APPLY_MIN_S, BUDGET_S, RESERVE_S, when))


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


def _conflict_reason(e):
    """The reason of an import that needs a decision (co.Conflict): the records it disagrees on, and `ctx sync` first."""
    ids = [x.get("id") for x in (e.payload.get("conflicts") or []) if isinstance(x, dict) and x.get("id")]
    what = ", ".join(ids) if ids else ("removals to confirm" if e.payload.get("suspicious_removal") else str(e))
    return "%s — `ctx sync` first" % cb.clip("the edits waiting to be imported need a decision (%s)" % what, cb.NOTE_CLIP - 20)


def _failure(e):
    """The reason of an unexpected failure: "store: <message>" for the store's own (a record missing or not downloaded),
    else the message (or the kind of the exception when it has none)."""
    said = str(e) or type(e).__name__
    return "store: " + said if isinstance(e, cs.StoreError) else said


# ------------------------------------------------------------------ the report (spec §6.6, §7)
REPORT_DIR = "_System/context/sync"             # from the storage root: where a result's `report` points, in the vault
REPORT_DAYS = 90                                # a report older than this is moved to ~/.grow-pm/trash/
REPORT_LINES = 40                               # lines of a conflict's text shown for each side
REPORT_LINE_CHARS = 500                         # …and characters of a line of it
REPORTED = ("changed", "held", "broken", "import-conflict", "error")   # the outcomes that write a part of the report
REPEATS = ("held", "broken", "import-conflict", "error")               # …and write none again for the same set and reason (§6.6)
PRUNE_S = 1.0                                   # the most the clearing of old reports takes of the budget
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
REPORT_FILE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.md$")
SECTION_REPO = re.compile(r"^##[ \t]+(\S+)[ \t]+·", re.M)
FRONT = re.compile(r"\A---\n(.*?\n)---\n", re.S)
REPOS_LINE = re.compile(r"^repos: \[(.*)\]$", re.M)
VERSION_MOVE = re.compile(r"\(v[^()]* → v[^()]*\)")


def reported(result):
    """Does a pass with this outcome write a part of the report? Those that changed something, kept a safeguard on or
    failed in a way the person should see — and a pass that changed nothing but left a block waiting for a decision (a "?":
    `awaiting`), which §5.1 says the report names, or held blocks because its source lags behind your bases
    (`held_behind`: a lasting lag must not look like a quiet success); whether either is new is `repeats`' question. A pass
    that only moved the time of the check, or could not reach the server, leaves nothing to read. A result without
    `held_behind` (written before it existed) holds none."""
    return result["outcome"] in REPORTED or (result["outcome"] == "no-changes"
                                             and bool(result["awaiting"] or result.get("held_behind")))


def new_waiting(prev, result):
    """The blocks waiting for a decision in `result` that the previous `sync_result` (`prev`) did not have waiting, in the
    result's order — the ones not yet named in a report (§5.1: "звіт називає блок один раз"). A `prev` that is not what the
    state keeps names none: every waiting block is new."""
    seen = prev.get("awaiting") if isinstance(prev, dict) else None
    seen = set(map(str, seen)) if isinstance(seen, list) else set()
    return [b for b in result["awaiting"] if b not in seen]


def new_behind(prev, result):
    """The blocks `result` held because its source lags behind your bases (`held_behind`), when the previous
    `sync_result` (`prev`) did not hold the same set (in any order) — [] when it did, or when none is held. Like a
    safeguard: a lag is told once, and again only when the set changes. A `prev` that is not what the state keeps, or
    one written before `held_behind` existed, held none: the set is new."""
    lag = [str(b) for b in (result.get("held_behind") or [])]
    seen = prev.get("held_behind") if isinstance(prev, dict) else None
    if not lag or (isinstance(seen, list) and sorted(map(str, seen)) == sorted(lag)):
        return []
    return lag


def repeats(prev, result):
    """Is `result` news that the report already told (§6.6, §5.1)? Never when a block waits that the previous `sync_result`
    (`prev`) did not have waiting (`new_waiting`), nor when a lagging source holds a set of blocks it did not hold
    (`new_behind`). A pass that changed nothing then (`no-changes`) with every waiting block named before and the same set
    held behind is a repeat. A safeguard going off again is one when `prev` has the same outcome, the same set of blocks
    held and the same reason, and this pass wrote nothing else (no snapshot): the report says it once, and the digest goes
    on showing the mark. Only the outcomes in REPEATS repeat. A `prev` that is not what the state keeps is no repeat."""
    if not isinstance(prev, dict) or new_waiting(prev, result) or new_behind(prev, result):
        return False
    if result["outcome"] == "no-changes":
        return True
    if result["outcome"] not in REPEATS or result.get("snapshot"):
        return False
    held = prev.get("held")
    return (prev.get("outcome") == result["outcome"] and isinstance(held, list) and sorted(map(str, held)) == sorted(result["held"])
            and prev.get("reason") == result["reason"])


def _lines_word(n):
    """The form of "рядок" after the number `n` (as cs.blocks_word does for "блок")."""
    if n % 10 == 1 and n % 100 != 11:
        return "рядок"
    return "рядки" if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14) else "рядків"


def _code(text, limit=cb.HEADER_CLIP):
    """`text` as inline code, one line of at most `limit` characters, a backtick in it made a quote: what a server sent
    (a block id, a version, a reason) never renders as Markdown or a live link in Obsidian."""
    return "`%s`" % cb.clip(text, limit).replace("`", "'")


def _ver(value):
    """A version for a heading: as code, or "—" when there is none."""
    return _code(value) if value and value != "—" else "—"


def _cell(text):
    return cb.clip(text, cb.NOTE_CLIP).replace("|", "\\|")


def _text_lines(text):
    """The lines of a region without its two marker lines, with every control character a server may have sent made a space
    and no line longer than REPORT_LINE_CHARS (the last character "…"): one huge line must not bloat a note in the vault."""
    out = []
    for line in cb._body_lines(text):
        line = cb.CONTROLS.sub(" ", line).rstrip()
        out.append(line if len(line) <= REPORT_LINE_CHARS else line[:REPORT_LINE_CHARS - 1].rstrip() + "…")
    return out


def _fenced(lines):
    """`lines` as a fenced code block whose fence is longer than any run of backticks in them: what a server sent is code
    in the report, never Markdown or a link that comes alive in Obsidian."""
    longest = max([len(m) for line in lines for m in re.findall(r"`+", line)] or [0])
    fence = "`" * max(3, longest + 1)
    return [fence] + list(lines) + [fence]


def _side(caption, text, where):
    """One side of a conflict: its caption (with the version in the begin marker), the text in a fence — the first
    REPORT_LINES lines — and, when there are more, `… ще N рядків — <where>`."""
    lines = _text_lines(text)
    version = cb._marker_version(text)
    out = ["%s%s:" % (caption, " (v%s)" % _code(version) if version else ""), ""]
    out += _fenced(lines[:REPORT_LINES] or ["(порожньо)"])
    if len(lines) > REPORT_LINES:
        left = len(lines) - REPORT_LINES
        out += ["", "… ще %d %s — %s" % (left, _lines_word(left), where)]
    return out


def _verdict(row, apply, result):
    """(decision, why, kind) of one row of the plan that offers something, in the cascade's own words (§5.1, §5.2, §6.1).
    `kind` is what became of the block: "rejected", "held", "lagging" (held: the source lags behind your bases), "mine",
    "theirs", "added", "removed", "taken" (a "~"), "waits" or "refused"."""
    bid, sign, gone = row["block"], row["sign"], row.get("source") is None
    if row.get("rejected") or bid in result["rejected"]:
        return "утримано", "відкинуто вами раніше", "rejected"
    if bid in result["held"]:
        n = len(result["held"])
        return "не прибрано", "запобіжник: ядро прибрало %d %s — не прибрано" % (n, cs.blocks_word(n)), "held"
    if (apply.get("plan") or {}).get("lagging") and bid in (apply.get("held") or {}):
        return "утримано", "джерело позаду вашої бази — з нього нічого не взято", "lagging"
    decided = (apply.get("decisions") or {}).get(bid)
    if decided is None:
        if bid in (apply.get("pending") or ()):
            return ("чекає рішення", "%s → лишається твій текст, база не зсувається; блок чекає твого рішення"
                    % ("ядро прибрало блок, а бази немає" if gone else "бази немає, тексти різні"), "waits")
        return "не застосовано", "текст ядра не прийнято: у блоці зіпсовані маркери", "refused"
    how = decided.partition(" ")[2]
    if sign == "+":
        return "додано", "новий блок у ядрі → додано", "added"
    if sign == "−":
        return "прибрано", "ядро прибрало блок, ти його не правив → прибрано (текст лишається у знімку)", "removed"
    if sign == "~":
        moved = VERSION_MOVE.search(row.get("note") or "")
        return "текст ядра", "змінило лише ядро → текст ядра" + (" " + moved.group(0) if moved else ""), "taken"
    first = "змінили обидва" if sign == "⚠" else "бази немає, тексти різні"
    if how == "theirs":
        return "текст ядра", "%s → правило ядра → текст ядра" % first, "theirs"
    if gone:
        return "лишено твоє", "ядро прибрало блок, а ти його правив → лишено твоє: маркери ядра знято", "mine"
    return "лишено твоє", "змінили обидва → лишено твоє: блок не є правилом ядра", "mine"


def _take(row, rid):
    """The line that takes the repository's side of a block with one command."""
    label = "Прибрати блок, як у ядра" if row.get("source") is None else "Взяти текст ядра"
    return "%s: ctx provider apply %s --choose %s=theirs" % (label, cb.clip(rid, cb.HEADER_CLIP), row["block"])


def _conflict(row, kind, apply, texts, rid, record):
    """The part of a "⚠" or a "?": what was done and why, the plan's lines of difference, BOTH texts and the commands."""
    bid, snapshot = row["block"], cb.clip(apply.get("snapshot") or "", 1000)
    gone = row.get("source") is None
    title = {"mine": "лишено твоє", "theirs": "правило ядра, взято текст ядра", "waits": "чекає рішення"}.get(kind, "не застосовано")
    where = "у записі %s" % _code(record) if record else "у записі"
    said = {"mine": ("Ядро прибрало блок; твій текст лишився %s як твій, без маркерів ядра." % where) if gone else
                    ("Твій текст лишився %s. Базою стала версія ядра, тож наступний синк про цей блок не питає." % where),
            "theirs": "Блок — правило ядра, тож %s тепер текст ядра. %s" % (where, ("Твій текст збережено у знімку %s і показано нижче." % snapshot)
                                                                        if snapshot else "Твій текст показано нижче."),
            "waits": "%s лишається твій текст, база не зсунулась: блок чекає твого рішення." % where.capitalize()}.get(kind, "")
    out = ["### Конфлікт: %s — %s" % (_code(bid), title), ""] + ([said, ""] if said else [])
    if row.get("diff"):
        out += ["Що змінилось відносно бази:", ""] + _fenced([line[4:] for line in cb._detail_lines(row["diff"])]) + [""]
    mine, theirs = (texts or {}).get("mine") or {}, (texts or {}).get("theirs") or {}
    mine_where = "повністю у знімку %s" % snapshot if snapshot else "повністю у записі %s" % (record or "—")
    out += _side("Твій текст", mine[bid], mine_where) if bid in mine else ["Твій текст: недоступний під час звіту%s." %
                                                                         (" — шукай у знімку %s" % snapshot if snapshot else "")]
    out.append("")
    if theirs.get(bid) is not None:
        out += _side("Текст ядра", theirs[bid], "повністю у джерелі ядра")
    else:
        out.append("Ядро прибрало цей блок." if gone else "Текст ядра: недоступний під час звіту.")
    if kind == "mine" and not gone:
        out += ["", _take(row, rid)]
    elif kind == "waits":
        out += ["", _take(row, rid), "", "Лишити своє: ctx provider apply %s --choose %s=mine" % (cb.clip(rid, cb.HEADER_CLIP), bid)]
    return out


def render_section(result, apply=None, texts=None, hosts=None, base_after=None, only=None):
    """One repository's part of the day's report (spec §7), Markdown for Obsidian, no trailing newline.

    `result` is a pass's result (`run`'s: `public` keys and `repo`); `apply` the apply's result with its `plan` (None for
    a pass that never planned: broken, import-conflict, error); `texts` the full texts taken before the write
    (`_conflicts`); `hosts` {block: record} read after it (a "+" has no record in the plan); `base_after` the version the
    bases stood at after the pass; `only`, when given, the blocks the table and the parts are limited to (a pass that changed
    nothing names just the blocks that began to wait for a decision).

    The heading is `## <id> · HH:MM · джерело <label> · ядро v<v> · база v<a> → v<b>` (only `## <id> · HH:MM` with no
    plan); each version — and the reason of a pass with no plan — is inline code (`_code`), as every text a server sent.
    Then the table `| Блок | Знак | Рішення | Чому | Запис |` — a row for every block the repository offered something
    for (~ + − ⚠ ?), in the cascade's words; the part of every ⚠ and ? with both texts (REPORT_LINES lines each)
    and the command that takes the core's; what the safeguard held and what to do; what a source behind your bases held
    (since v3.14.0); the texts you rejected before; and the last line, the way back (`Відкотити цей прохід: ctx undo
    (знімок <folder>)`) or that there is none — or, for an unexpected failure that may have written before it failed, that the snapshot is unknown and `ctx status` shows the journal."""
    rid = cb.clip(result["repo"], cb.HEADER_CLIP)
    at = result.get("at") or ""
    plan = (apply or {}).get("plan")
    head = "## %s · %s" % (rid, at[11:16] if len(at) >= 16 else "—")
    if plan:
        head += " · джерело %s · ядро v%s · база v%s → v%s" % (cb.clip(plan["source_label"], cb.HEADER_CLIP),
                                                              _ver(plan["version"]), _ver(plan["base_version"]), _ver(base_after))
    blocks = [[head]]
    outcome, reason = result["outcome"], _code(result.get("reason") or "—", cb.NOTE_CLIP)
    if plan and outcome in ("changed", "held", "no-changes"):
        rows = [r for r in plan["rows"] if r["sign"] in cb.OFFERS and (only is None or r["block"] in only)]
        verdicts = {r["block"]: _verdict(r, apply, result) for r in rows}
        if outcome == "no-changes":
            summary = "Прохід нічого не змінив; блоків, що чекають твого рішення: %d." % len(
                [r for r in rows if r["block"] in result["awaiting"]])
        else:
            summary = ("Оновлено %d · додано %d · прибрано %d · лишено твоє %d · чекає рішення %d"
                       % (result["updated"], result["added"], result["removed"], len(result["kept_yours"]), len(result["awaiting"])))
            if result["held"]:
                summary += " · не прибрано %d" % len(result["held"])
        blocks.append([summary])
        if rows:
            table = ["| Блок | Знак | Рішення | Чому | Запис |", "|---|---|---|---|---|"]
            for r in rows:
                record = r.get("host") or (hosts or {}).get(r["block"])
                table.append("| %s | %s | %s | %s | %s |" % (_code(r["block"]), r["sign"], _cell(verdicts[r["block"]][0]),
                                                           _cell(verdicts[r["block"]][1]), _code(record) if record else "—"))
            blocks.append(table)
        else:
            relaid = [r["block"] for r in plan["rows"] if r.get("reoverlay")]
            blocks.append(["Тексти ядра не змінились; твій оверлей накладено знову на: %s." % ", ".join(_code(b) for b in relaid)]
                          if relaid else ["Тексти не змінились: пройшло лише оновлення бази порівняння."])
        for r in rows:
            kind = verdicts[r["block"]][2]
            if r["sign"] in QUESTIONS and kind not in ("rejected", "held", "lagging"):
                blocks.append(_conflict(r, kind, apply, texts, result["repo"], r.get("host") or (hosts or {}).get(r["block"])))
        if result["held"]:
            n = len(result["held"])
            blocks.append(["### Не застосовано: ядро прибрало %d %s" % (n, cs.blocks_word(n)), "",
                           "За один прохід ядро прибрало більше одного блоку, який ти тримаєш, тож жодного не прибрано; решту знаків "
                           "застосовано як зазвичай.", ""] + ["- %s" % _code(b) for b in result["held"]])
            blocks.append(["Подивитись: ctx provider plan %s" % rid])
            blocks.append(["Прибрати руками: ctx provider apply %s" % rid])
        lagged = [r["block"] for r in rows if verdicts[r["block"]][2] == "lagging"]
        if lagged:
            blocks.append(["### Джерело позаду вашої бази", "",
                           "Копія ядра старша за твої бази, тож синк нічого з неї не взяв: блоки, які вона змінила б, утримано. "
                           "Наступний синк перевірить знову.", ""] + ["- %s" % _code(b) for b in lagged])
        back = [r for r in rows if verdicts[r["block"]][2] == "rejected"]
        if back:
            blocks.append(["### Відкинуто вами раніше", "", "Ці тексти ядра не застосовуються, доки ядро не змінить блок:"] + [""] +
                          ["- %s" % _code(r["block"]) for r in back])
            blocks.extend([_take(r, result["repo"])] for r in back)
        held_ov = cb.overlay_lines(plan)
        if held_ov:                                 # since v3.23.0: your overlay — a held correction, a file not read
            blocks.append(["### Оверлей чекає рішення", ""] + ["- %s" % _cell(x) for x in held_ov])
            blocks.append(["Відповісти: /context overlay (або ctx overlay show %s)" % rid])
    elif outcome == "broken":
        blocks.append(["### Джерело ядра не прийнято", "", "Причина: %s" % reason])
        blocks.append(["Репозиторій пропущено: нічого не записано. Перевірку зараховано, наступна — через добу."])
    elif outcome == "import-conflict":
        blocks.append(["### Спершу `ctx sync`", "", "Причина: %s" % reason])
        blocks.append(["У local-context.md є правки, які потребують рішення, тому синк нічого не записав: спершу `ctx sync`, "
                       "потім синк пройде сам."])
    else:
        blocks.append(["### Несподівана помилка" if outcome == "error" else "### Прохід не завершено", "", "Причина: %s" % reason])
        blocks.append(["Прохід не завершено; нова спроба — не раніше ніж за годину."])
    snapshot = (apply or {}).get("snapshot") or result.get("snapshot")
    if snapshot:
        blocks.append(["Відкотити цей прохід: ctx undo (знімок %s)" % cb.clip(snapshot, 1000)])
    elif outcome == "error":                        # the pass may have written before it failed: nobody knows
        blocks.append(["Знімок цього проходу невідомий: до помилки прохід міг щось записати — останні рядки журналу покажуть "
                       "це в `ctx status`."])
    else:
        blocks.append(["Знімка цього проходу немає: відкочувати нічого."])
    return "\n\n".join("\n".join(b) for b in blocks)


def _section_repo(text):
    """The repository a part of the report is about: the id in its `## <id> · …` heading, or None."""
    found = SECTION_REPO.search(text or "")
    return found.group(1) if found else None


def render_report(date, sections):
    """The text of a day's report: the frontmatter (`type: system`, `kind: context-sync`, `date`, `repos`), the title
    `# Синк контексту — YYYY-MM-DD` and the parts, a blank line between. `sections` are part texts — the repository named
    by the heading — or (repository id, text) pairs; a repository is listed once."""
    if not isinstance(date, str) or not DATE.match(date):
        raise ValueError("a report is named for a day, YYYY-MM-DD, not %r" % (date,))
    ids, parts = [], []
    for item in sections:
        rid, text = item if isinstance(item, tuple) else (_section_repo(item), item)
        if rid and rid not in ids:
            ids.append(rid)
        parts.append(text.strip("\n"))
    return ("---\ntype: system\nkind: context-sync\ndate: %s\nrepos: [%s]\n---\n\n# Синк контексту — %s\n%s"
            % (date, ", ".join(ids), date, "".join("\n%s\n" % part for part in parts)))


def _with_repo(text, rid):
    """`text` (a report) with `rid` added to the `repos:` list of its frontmatter; unchanged when it has no such list
    (a file you rewrote by hand) or already names it."""
    front = FRONT.match(text)
    line = REPOS_LINE.search(front.group(1)) if front and rid else None
    if not line:
        return text
    ids = [x.strip() for x in line.group(1).split(",") if x.strip()]
    if rid in ids:
        return text
    body = front.group(1)[:line.start()] + "repos: [%s]" % ", ".join(ids + [rid]) + front.group(1)[line.end():]
    return "---\n" + body + "---\n" + text[front.end():]


def write_report(store, date, section_text, repo=None):
    """Put a part into the day's report `{store}/sync/<date>.md`: a new file (frontmatter, title, the part) or, when the
    day has one, the part appended and the repository added to `repos` — whatever else the file holds is kept. Atomic.
    Returns the path from the storage root, `_System/context/sync/<date>.md`. `repo` names the repository (else the
    part's heading does). A date that is no date → ValueError; a file that cannot be read in time → StoreError."""
    if not isinstance(date, str) or not DATE.match(date):
        raise ValueError("a report is named for a day, YYYY-MM-DD, not %r" % (date,))
    rid = repo or _section_repo(section_text)
    path = os.path.join(store.sync_dir, date + ".md")
    if os.path.isfile(path):
        text = _with_repo(cs.read_text(path), rid).rstrip("\n") + "\n\n" + section_text.strip("\n") + "\n"
    else:
        text = render_report(date, [(rid, section_text)])
    cs.atomic_write(path, text)
    return "%s/%s.md" % (REPORT_DIR, date)


def _trash_path(home, name, when):
    """A free path ~/.grow-pm/trash/<time>-<name>.md, where the trash's own purge finds the file (30 days)."""
    root = co.trash_root(home)
    base = when.astimezone().strftime("%Y%m%dT%H%M%S") + "-" + name
    path, k = os.path.join(root, base + ".md"), 2
    while os.path.exists(path):
        path, k = os.path.join(root, "%s-%d.md" % (base, k)), k + 1
    return path


def _move_to_trash(home, name, path, when):
    """Move the report `path` to the trash so that it is never left in both places. The target is checked first — a path
    that leads outside the guarded roots (a symlinked folder), or is itself a link, is neither read nor moved. On one volume
    it is a single rename, and the report is not read (an old report iCloud has evicted costs no download). Across volumes
    (the vault is not always where ~/.grow-pm is) it is read then, the copy is written first and the original removed
    after; an original that cannot be removed takes its copy back out of the trash, so the next sync does not find a
    second one. Raises what failed (OSError, StoreError, PathRefused, UnicodeDecodeError); the original is then where it
    was."""
    cs.check_target(path)
    if os.path.islink(path) or os.path.islink(os.path.dirname(path)):
        raise cs.PathRefused("%s is a link: a report is not moved through one" % path)
    target = _trash_path(home, name, when)
    cs.check_target(target)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    try:
        os.rename(path, target)
        return target
    except OSError as e:
        if e.errno != errno.EXDEV:
            raise
    cs.atomic_write(target, cs.read_text(path))
    try:
        os.remove(path)
    except OSError:
        try:
            os.remove(target)
        except OSError:
            pass
        raise
    return target


def prune_reports(store, home, now):
    """Move the reports older than REPORT_DAYS days (by the day in the name) from `{store}/sync/` to ~/.grow-pm/trash/,
    where they stay another 30 days (`_move_to_trash`: the target is checked first, one copy at any time). Only
    `YYYY-MM-DD.md` files are touched — a note of yours in that folder is not; and a folder that is a link is not entered. A
    report that cannot be read or moved is left for the next time. Returns the names moved; a `now` that is no time, or a
    folder that is not there, moves nothing. Since v3.14.0 the temp file a report write cut short left there
    (`.<YYYY-MM-DD>.md.tmp`, hidden) is removed once it is 24 h old (`cs.remove_stale_tmp`); it is no report moved."""
    when, gone = instant(now), []
    if when is None or os.path.islink(store.sync_dir):
        return gone
    cs.remove_stale_tmp(store.sync_dir)
    try:
        names = sorted(os.listdir(store.sync_dir))
    except OSError:
        return gone
    for name in names:
        found = REPORT_FILE.match(name)
        try:
            age = (when.date() - datetime.date.fromisoformat(found.group(1))).days if found else 0
        except ValueError:
            continue
        if age <= REPORT_DAYS:
            continue
        try:
            _move_to_trash(home, "sync-report-" + found.group(1), os.path.join(store.sync_dir, name), when)
        except (OSError, UnicodeDecodeError, cs.StoreError, cs.PathRefused):
            continue
        gone.append(name)
    return gone


def _write_report(c, result, apply, facts, deadline):
    """The path of the part this pass wrote into the day's report, or None: the pass is not one that writes (`reported`),
    or it is news already told — a safeguard going off again as before, a block still waiting that the last pass named
    (`repeats`, from the state's `sync_result` as the last pass left it — read here, before `_record` replaces it). What the render needs of the state the pass left (the record a "+" went
    into, the version the bases stand at) is read after the write, within what is left of the budget; what cannot be read
    is shown as unknown. A pass that changed nothing names only what is new: the blocks that began to wait and a new
    set held behind a lagging source."""
    if not reported(result):
        return None
    rid = result["repo"]
    hosts, base_after, prev = {}, None, None
    with cs.read_budget(max(RECORD_S, _left(deadline))):
        try:
            state = cb.load_state(c.store, rid)
        except (cs.StoreError, OSError, ValueError):
            state = None
        if state is not None:
            prev = state.get("sync_result")
            if repeats(prev, result):
                return None
            hosts = {b: e.get("host") for b, e in state["blocks"].items()}
            base_after = cb.base_version(state)
        only = (new_waiting(prev, result) + new_behind(prev, result)) if result["outcome"] == "no-changes" else None
        section = render_section(result, apply, facts, hosts, base_after, only)
        return write_report(c.store, result["at"][:10], section, rid)


def run(c, repos, now, deadline, only_due=False, skipped=None):
    """One sync pass over `repos` (repository dicts, `sync: daily`) at `now` (ISO text), by `deadline` (a time.monotonic()
    moment; the command gives BUDGET_S). `c` is the command line's context (`ctx.Ctx`: store, copies, home, guard,
    import_first). Returns one result per repository — `public`'s keys and `apply` (the apply's result, its plan with the
    rows, or None), for the report — and writes each into the repository's block state (`sync_result`, `sync_attempt`).

    1. The lock: held by another session (co.Busy) → [] at once, nothing written — and so is a lock that cannot be taken
       at all (OSError) and a guard that refuses (a registration still downloading: the provider boundary cannot be
       checked). When `skipped` is a list it gets why: "busy", "lock: <why>" or "guard: <why>".
    2. With `only_due` (the command's --if-due, whose choice was made before the lock) the repositories are checked
       again under the lock, from their states as they are now: another session that synced them meanwhile leaves
       none due, and [] is returned — no second pass, no second result over the first one.
    3. The edits waiting in local-context.md are imported first, as by every writing command. A conflict for `ctx sync`
       makes every repository "import-conflict"; any other failure (the store: a record missing or not downloaded)
       "error" ("store: <why>"). Nothing is written to the records then.
    4. Each repository in turn, while the budget lasts (its last RESERVE_S kept for the writing down): `_pass`. Less
       than APPLY_MIN_S left before a repository is "timeout" (not started); an unexpected failure in a pass is
       "error" with its message (the check does not move: retried in an hour). One repository's failure never stops
       the next.
    5. The report (spec §7): a pass that changed something, kept a safeguard on or failed in a way worth reading
       (`reported`) puts its part into `{storage_root}/_System/context/sync/<day>.md` — unless it is a safeguard going off
       again with the same set and reason (`repeats`) — and its path is the result's `report`, in the state's
       `sync_result` too. A report that cannot be written is said in the result's `reason`; the pass stands. At the
       start, the reports older than 90 days go to the trash (`prune_reports`).
    6. The card's line about the repositories, when a check moved and at least CARD_MIN_S of the budget is left: its
       registrations are read by the deadline (`co.refresh_card_repos`); one not read in time keeps the line the card has."""
    stack = contextlib.ExitStack()
    try:
        stack.enter_context(co.lock(c.home))
    except co.Busy:
        if skipped is not None:
            skipped.append("busy")
        return []
    except OSError as e:                            # ~/.grow-pm not writable, say: no lock can be taken — not another session
        if skipped is not None:
            skipped.append("lock: " + cb.clip(str(e) or type(e).__name__, cb.NOTE_CLIP))
        return []
    with stack:
        if only_due:
            repos = pick_due(c.store, repos, now)
            if not repos:
                return []
        try:
            c.guard()
        except (co.Refused, cs.PathRefused, cs.StoreError, OSError) as e:
            if skipped is not None:
                skipped.append("guard: " + cb.clip(str(e) or type(e).__name__, cb.NOTE_CLIP))
            return []
        until = deadline - RESERVE_S
        failed = None
        try:
            with cs.read_budget(_left(until)):
                c.import_first()
        except co.Conflict as e:
            failed = _result(now, "import-conflict", _conflict_reason(e))
        except Exception as e:  # noqa: BLE001 — an import that cannot go through stops the writing, never the skill
            failed = _result(now, "error", _failure(e))
        try:                                        # reports older than 90 days go to the trash; never a reason to stop
            with cs.read_budget(min(PRUNE_S, _left(until))):
                prune_reports(c.store, c.home, now)
        except Exception:  # noqa: BLE001
            pass
        results = []
        for repo in repos:
            rid, res, checked, facts = repo["id"], None, False, {}
            if failed:
                result = dict(failed)
            elif _left(until) < APPLY_MIN_S:
                result = _result(now, "timeout", _short("before this repository — not started"))
            else:
                try:
                    result, res, checked = _pass(c, repo, now, until, facts)
                except cb.SourceLost as e:          # the state moved between the check and the plan
                    result, checked = _result(now, "broken", str(e)), True
                except Exception as e:  # noqa: BLE001 — one repository's failure never stops the next (§6.4)
                    result = _result(now, "error", _failure(e))
            try:                                    # the report first: the result written into the state names it
                result["report"] = _write_report(c, dict(result, repo=rid), res, facts, deadline)
            except Exception as e:  # noqa: BLE001 — a report that cannot be written never hides what the pass did
                said = "звіт не записано: %s" % (str(e) or type(e).__name__)
                result["reason"] = cb.clip("%s; %s" % (result["reason"], said) if result["reason"] else said, cb.NOTE_CLIP)
            _record(c.store, rid, result, now if checked else None, deadline)
            results.append(dict(result, repo=rid, apply=res))
        if any(r["outcome"] in MOVED for r in results) and _left(deadline) >= CARD_MIN_S:
            try:                                    # the card's Repos line says when each repository was checked
                with cs.read_budget(_left(deadline)):
                    co.refresh_card_repos(c.store, c.home, now[:10], deadline=deadline)
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
