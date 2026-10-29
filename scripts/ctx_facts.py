#!/usr/bin/env python3
"""Grow PM — the facts of an entity: the numbers its cards carry, with where and when (since v4.0.0).

A fact is a field of a card's frontmatter (ctx_index.FACT_FIELDS: actual, target, value, baseline, current) with its
period and the day it was observed — what the walk keeps in the `facts` table of the index beside the card. Text in a
note's body never becomes a fact. Two cards of one entity (the registry joined them) that give one attribute of one
period two values disagree: `ctx entity` shows both with ⚠ and `ctx audit` names it.

- rows(idx, paths)            the facts of those cards — only those whose hash is their note's (an older build's are
                              never read)
- of_entity(sctx, idx, ent, today)   [{attribute, value, period, observed_at, path, source, trust, conflict}]
- audit_findings(idx, reg, roots)    the `facts` findings of `ctx audit`
- lines(facts)                the lines of `ctx entity`

Reads the index. Stdlib only.
"""
import collections
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx_common as cc  # noqa: E402
import ctx_trust as ct  # noqa: E402

N = cc.N


def rows(idx, paths):
    """[{path, source, attribute, value, period, observed_at, status, date, confluence_id}] of the cards `paths`."""
    paths = sorted({N(p) for p in paths or ()})
    if not paths:
        return []

    def read(con):
        if "facts" not in {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}:
            return []
        out = []
        for i in range(0, len(paths), 400):
            part = paths[i:i + 400]
            out += con.execute("SELECT n.path, n.source, f.attribute, f.value, f.period, f.observed_at, n.status, "
                               "n.date, n.confluence_id, n.type, n.sensitive, n.title FROM facts f JOIN notes n ON n.id = f.note_id "
                               "AND f.hash = n.hash WHERE n.path IN (%s) ORDER BY f.attribute, n.path"
                               % ",".join("?" * len(part)),
                               part).fetchall()
        return out

    import ctx_index as ci
    keys = ("path", "source", "attribute", "value", "period", "observed_at", "status", "date", "confluence_id", "type",
            "sensitive", "title")
    out = []
    for r in idx._read(read, []):
        d = dict(zip(keys, r))
        if d["sensitive"] or (d["type"] or "").lower() in ci.PEOPLE_TYPES or ci.one_on_one(d["path"], d["title"]):
            continue                             # a person's or a sensitive card's numbers are never shown (review B1)
        out.append(d)
    return out


_Q = re.compile(r"^(?:(\d{4})\W*[qк]\s*([1-4])|[qк]\s*([1-4])\W*(\d{4}))$", re.I)


def period_key(p):
    """A period as two cards are compared by it: `Q3 2026`, `2026-Q3`, `q3-2026` → `2026-Q3`; else spaces folded."""
    s = re.sub(r"\s+", " ", str(p or "")).strip()
    m = _Q.match(s)
    if m:
        return "%s-Q%s" % (m.group(1) or m.group(4), m.group(2) or m.group(3))
    return s.casefold()


def _same(v):
    return re.sub(r"\s+", " ", str(v or "")).strip().casefold()


def _conflicts(facts):
    """{(attribute, period)} that two cards give two values of."""
    seen = collections.defaultdict(set)
    for f in facts:
        seen[(f["attribute"], period_key(f["period"]))].add(_same(f["value"]))
    return {k for k, v in seen.items() if len(v) > 1}


def of_entity(sctx, idx, ent, today=None):
    """The facts of an entity's cards, each with its trust (ctx_trust) and `conflict`."""
    facts = rows(idx, [c["path"] for c in ent.get("cards") or ()])
    bad = _conflicts(facts)
    out = []
    for f in facts:
        kind = ct.kind_of(sctx, f["source"], f["path"], f.get("confluence_id"))
        t = ct.score(kind, f["observed_at"] or None, ct.ttl_of(sctx, f["path"]), f["status"], "", today)
        out.append({"attribute": f["attribute"], "value": f["value"], "period": f["period"],
                    "observed_at": f["observed_at"], "path": f["path"], "source": f["source"], "trust": t,
                    "conflict": (f["attribute"], period_key(f["period"])) in bad})
    return out


def audit_findings(idx, reg, roots):
    """A `facts` finding for every attribute and period two cards of one entity disagree on — on the card of your layer
    when there is one, else the entity's first card; never fixable (which value is right is yours to say)."""
    import ctx_audit as ca
    out = []
    for ent in getattr(reg, "entities", None) or []:
        if len(ent.get("cards") or ()) < 2:
            continue
        facts = rows(idx, [c["path"] for c in ent["cards"]])
        for attr, period in sorted(_conflicts(facts)):
            vals = [{"value": f["value"], "path": f["path"]} for f in facts
                    if f["attribute"] == attr and period_key(f["period"]) == period]
            mine = next((v["path"] for v in vals if ca._inside(v["path"], roots)), vals[0]["path"])
            out.append({"kind": "facts", "path": mine, "detail": {"entity": ent["id"], "attribute": attr,
                                                                  "period": period, "values": vals}, "fixable": False})
    return out


def lines(facts):
    out = []
    for f in facts:
        out.append("    %s%s: %s%s · %s · %s" % ("⚠ " if f["conflict"] else "", f["attribute"], f["value"],
                                                 (" · " + f["period"]) if f["period"] else "",
                                                 ("станом на " + f["observed_at"]) if f["observed_at"] else "без дати",
                                                 f["path"]) + " · " + ct.line(f["trust"]))
    if any(f["conflict"] for f in facts):
        out.append("    ⚠ картки дають різні значення — котре правильне, вирішуєш ти")
    return out
