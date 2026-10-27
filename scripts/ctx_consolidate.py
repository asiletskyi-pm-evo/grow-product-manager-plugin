#!/usr/bin/env python3
"""Grow PM — tidying your context, as proposals (since v3.22.0): `ctx consolidate`.

The phases of consolidate-memory, deterministic and read-only on the records: a line written twice in one record, a
relative date («вчора», «минулого тижня», "next month") that means nothing a month later, a line whose deadline has
passed. Each becomes a REPLACE delta of the inbox (proposer ctx-consolidate) — nothing is written to a record until you
take it; archiving is no delta, so a record no longer current for long, or a card over its budget, is named with the
command that would do it. Semantics: references/context-protocol.md §5m.

- find(recs, today)       {deltas, archive: [(id, since)], card_over: lines or None}
- RELATIVE                the relative dates it knows, uk and en

Writes nothing itself. Stdlib only.
"""
import datetime
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx_common as cc  # noqa: E402
import ctx_store as cs  # noqa: E402

ARCHIVE_AFTER_DAYS = 90
# phrase → (unit, offset): day — that day; week — the Monday of that week; month — that month
RELATIVE = {"позавчора": ("day", -2), "вчора": ("day", -1), "сьогодні": ("day", 0), "завтра": ("day", 1),
            "минулого тижня": ("week", -1), "цього тижня": ("week", 0), "наступного тижня": ("week", 1),
            "минулого місяця": ("month", -1), "цього місяця": ("month", 0), "наступного місяця": ("month", 1),
            "yesterday": ("day", -1), "today": ("day", 0), "tomorrow": ("day", 1),
            "last week": ("week", -1), "this week": ("week", 0), "next week": ("week", 1),
            "last month": ("month", -1), "this month": ("month", 0), "next month": ("month", 1)}
_REL = re.compile(r"(?<![\w-])(%s)(?![\w-])" % "|".join(sorted((re.escape(k) for k in RELATIVE), key=len, reverse=True)),
                  re.I)
_UK = re.compile(r"[а-яіїєґ]", re.I)
_DEADLINE = re.compile(r"(?<![\w-])(?:до|until|by|due|deadline:?|дедлайн:?|строк:?)\s+(\d{4}-\d{2}-\d{2})(?![\d-])", re.I)
_QUARTER = re.compile(r"(?<![\w-])(?:до|у|в|in|by|until)\s+Q([1-4])\s*'?(\d{4})(?!\d)", re.I)
_SINCE = re.compile(r"Неактуально з (\d{4}-\d{2}-\d{2})")


def _day(s):
    try:
        return datetime.date.fromisoformat((s or "")[:10])
    except ValueError:
        return None


def _norm(line):
    return " ".join(line.split()).casefold().rstrip(".;,")


def _shift(base, unit, k):
    if unit == "day":
        return (base + datetime.timedelta(days=k)).isoformat()
    if unit == "week":
        monday = base - datetime.timedelta(days=base.weekday()) + datetime.timedelta(weeks=k)
        return monday.isoformat()
    y, m = base.year, base.month + k
    y, m = y + (m - 1) // 12, (m - 1) % 12 + 1
    return "%04d-%02d" % (y, m)


def absolute(line, base):
    """The line with each relative date made absolute from `base` (a date), or None when it holds none."""
    def sub(m):
        unit, k = RELATIVE[m.group(1).lower()]
        when = _shift(base, unit, k)
        if unit == "week":
            return ("тиждень з %s" if _UK.search(m.group(1)) else "week of %s") % when
        return when
    new = _REL.sub(sub, line)
    return new if new != line else None


def passed(line, today):
    """A deadline the line names that is before today — the date as text — or None."""
    for m in _DEADLINE.finditer(line):
        d = _day(m.group(1))
        if d and d < today:
            return m.group(1)
    for m in _QUARTER.finditer(line):
        q, y = int(m.group(1)), int(m.group(2))
        end = datetime.date(y + (q == 4), 1 if q == 4 else 3 * q + 1, 1) - datetime.timedelta(days=1)
        if end < today:
            return "Q%d %d" % (q, y)
    return None


def _lines(body):
    """[(core)] of the body's own lines: outside managed regions and fenced code, not headings, not empty, not a
    table's rule."""
    spans, fence, out = cc.managed_spans(body), False, []
    for off, core, _ in cs._lines(body):
        s = core.strip()
        if s.startswith("```") or s.startswith("~~~"):
            fence = not fence
            continue
        if fence or not s or cs._in_region(off, spans) or cs._heading_text(core) is not None:
            continue
        if set(s) <= set("|-: "):
            continue
        out.append(core)
    return out


def find(recs, today, card_lines=None, card_max=cs.CARD_MAX):
    t = _day(today)
    deltas, archive = [], []
    for r in recs:
        if r["type"] == "header" or str(r.get("owner") or "").startswith("provider:"):
            continue
        if cs.has_status_region(r["body"]):
            m = _SINCE.search(r["body"])
            since = _day(m.group(1)) if m else None
            if since and (t - since).days > ARCHIVE_AFTER_DAYS:
                archive.append((r["id"], since.isoformat()))
            continue
        base = _day(r.get("modified")) or t
        seen, gone = set(), set()
        for core in _lines(r["body"]):
            line = core.strip()
            key = _norm(line)
            if key in seen:
                if line not in gone:
                    gone.add(line)
                    deltas.append({"op": "REPLACE", "record": r["id"], "text": line, "value": "",
                                   "reason": "рядок двічі в записі — лишаю перший",
                                   "source": {"kind": "derived:consolidate", "ref": "дубль", "at": today}})
                continue
            seen.add(key)
            when = passed(line, t)
            if when:
                deltas.append({"op": "REPLACE", "record": r["id"], "text": line, "value": "",
                               "reason": "строк минув (%s) — якщо це ще треба, лиши рядок і зміни дату" % when,
                               "source": {"kind": "derived:consolidate", "ref": "строк %s" % when, "at": today}})
                continue
            new = absolute(line, base)
            if new:
                deltas.append({"op": "REPLACE", "record": r["id"], "text": line, "value": new,
                               "reason": "відносна дата — від останньої зміни запису (%s); перевір" % base.isoformat(),
                               "source": {"kind": "derived:consolidate", "ref": "відносна дата", "at": today}})
    over = card_lines if card_lines is not None and card_lines > card_max else None
    return {"deltas": deltas, "archive": archive, "card_over": over}
