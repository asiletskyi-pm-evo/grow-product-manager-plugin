#!/usr/bin/env python3
"""Grow PM — your records checked against the connectors, each finding a delta of the inbox (since v3.22.0).

`ctx validate --recheck --observed F` reads what a skill saw (ctx_observe, its `checks` and the provider's role) and
compares it with the records: a product's Jira key and Confluence space still there, a team's members still active
people of the site, the role a provider gives you. A record is never called gone on one look: a finding becomes a delta
only when a second recheck, at least CONFIRM_DAYS later, sees it again; a connector that did not answer or a list that
was cut checks nothing; a product is closed (INVALIDATE) only when every anchor it has is gone. The first sightings
wait in `<store>/.state/recheck.json` (schema context-recheck/1). Semantics: references/context-protocol.md §5l.

- SCHEMA, FILE, WHERE      the memory; load / save as the other state files (unknown key refused, never reset)
- run(obs, recs, mem, today)   {findings, checked, unchecked, noticed, confirmed, deltas, fine, unresolved} — and the
                               memory updated in place
- age(mem, today)          days since the last recheck (None: never)

Writes nothing itself: the lock, the inbox and the journal are ctx.py's. Stdlib only.
"""
import datetime
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx_common as cc  # noqa: E402
import ctx_store as cs  # noqa: E402

SCHEMA = "context-recheck/1"
FILE = "recheck.json"
WHERE = ".state/" + FILE
CONFIRM_DAYS = 6
OLD_DAYS = 10
_DAY = re.compile(r"\d{4}-\d{2}-\d{2}\Z")


def empty():
    return {"schema": SCHEMA, "last_run": None, "seen": {}}


def _clean(raw):
    if not isinstance(raw, dict) or raw.get("schema") != SCHEMA:
        raise ValueError("not of schema %s" % SCHEMA)
    unknown = sorted(set(raw) - {"schema", "last_run", "seen"})
    if unknown:
        raise ValueError("unknown key(s) %s — a newer plugin wrote it" % ", ".join(unknown))
    last, seen = raw.get("last_run"), raw.get("seen", {})
    if last is not None and not (isinstance(last, str) and _DAY.match(last)):
        raise ValueError("last_run is a date")
    if not isinstance(seen, dict):
        raise ValueError("seen is an object")
    out = empty()
    out["last_run"] = last
    for k, v in seen.items():
        if not (isinstance(k, str) and isinstance(v, dict) and set(v) == {"first", "last"}
                and all(isinstance(v[x], str) and _DAY.match(v[x]) for x in ("first", "last"))):
            raise ValueError("a sighting of another shape")
        out["seen"][k] = {"first": v["first"], "last": v["last"]}
    return out


def load(store, timeout=None):
    path = os.path.join(store.state_dir, FILE)
    if not os.path.lexists(path):
        return empty()
    try:
        raw = cs.read_text(path, timeout=timeout)
    except FileNotFoundError:
        return empty()
    except (OSError, UnicodeDecodeError, cs.StoreError) as e:
        raise cs.StoreError("recheck memory not readable: %s (%s)" % (WHERE, getattr(e, "strerror", None) or e))
    try:
        return _clean(json.loads(raw))
    except ValueError as e:
        raise cs.StoreError("recheck memory not valid: %s (%s)" % (WHERE, e))


def save(store, mem):
    cs.atomic_write(os.path.join(store.state_dir, FILE), json.dumps(_clean(mem), ensure_ascii=False, indent=1,
                                                                  sort_keys=True) + "\n")


def _days(a, b):
    try:
        return (datetime.date.fromisoformat(b[:10]) - datetime.date.fromisoformat(a[:10])).days
    except (TypeError, ValueError):
        return 0


def age(mem, today):
    return _days(mem["last_run"], today) if mem.get("last_run") else None


def _n(s):
    return " ".join((s or "").split()).casefold()


def _title(rec):
    return rec["title"].split(":", 1)[1].strip() if ":" in rec["title"] else rec["title"]


def members(body):
    """[(name, line)] of a team's Members — the first cell of each table row, or each bullet — in your own text."""
    spans = cc.managed_spans(body)
    lines = [(off, core) for off, core, _ in cs._lines(body)]
    at = next((k for k, (_, c) in enumerate(lines)
               if any(cs.heading_matches(c, n) for n in cs.section_names("Members"))), None)
    out = []
    for off, c in lines[at + 1:] if at is not None else []:
        if cs._heading_text(c) is not None:
            break
        if cs._in_region(off, spans):
            continue
        s = c.strip()
        if s.startswith("|"):
            cell = s.strip("|").split("|")[0].strip()
            if cell and not set(cell) <= set("-: ") and _n(cell) not in ("name", "ім'я", "імʼя"):
                out.append((cell, c))
        elif s.startswith(("- ", "* ")):
            out.append((re.split(r"\s+[—–-]\s+|\(|,", s[2:].strip())[0].strip(), c))
    return out


def _candidate(visible, f, rec):
    """The keys the connector lists under the product's own name, other than the one gone."""
    vis = visible.get("jira:visible" if f["check"] == "jira" else "confluence:visible", {})
    return [k for k, name in vis.items() if name and _n(name) == _n(_title(rec)) and k != f["item"]]


def run(obs, recs, mem, today):
    conn = obs["connectors"]
    chk = obs["checks"]
    atl = conn.get("atlassian") == "ok"
    runs = {"jira": atl and chk.get("jira:visible", {}).get("complete") is True,
            "confluence": atl and chk.get("confluence:visible", {}).get("complete") is True,
            "member": atl and "atlassian:people" in chk,
            "role": any(f["from"] == "provider:identity" and f["field"] == "Role" for f in obs["facts"])}
    visible = {k: {v["key"]: v["name"] for v in chk[k]["values"]} for k in ("jira:visible", "confluence:visible")
               if k in chk}
    inactive = {_n(x) for x in chk.get("atlassian:people", {}).get("inactive", [])}
    role = next((f["value"] for f in obs["facts"] if f["from"] == "provider:identity" and f["field"] == "Role"), None)
    found = {}                                          # key → {record, check, item, line?}
    live = [r for r in recs if not cs.has_status_region(r["body"])]
    checked = {}
    for r in live:
        if r["type"] == "product":
            for check, field, vis in (("jira", "Jira Project Key", "jira:visible"),
                                      ("confluence", "Confluence Space", "confluence:visible")):
                value = cs.field_get(r["body"], field)
                if not value or not runs[check]:
                    continue
                checked.setdefault(r["id"], []).append(check)
                if value not in visible.get(vis, {}):
                    found["%s|%s|%s" % (r["id"], check, value)] = {"record": r["id"], "check": check, "item": value}
        elif r["type"] == "team" and runs["member"]:
            ms = members(r["body"])
            if ms:
                checked.setdefault(r["id"], []).append("member")
            for name, line in ms:
                if _n(name) in inactive:
                    found["%s|member|%s" % (r["id"], name)] = {"record": r["id"], "check": "member", "item": name,
                                                              "line": line}
        elif r["type"] == "profile" and runs["role"]:
            checked.setdefault(r["id"], []).append("role")
            now_role = cs.field_get(r["body"], "Role")
            if role and _n(now_role) != _n(role):
                found["%s|role|%s" % (r["id"], role)] = {"record": r["id"], "check": "role", "item": role}
    seen = mem["seen"]
    for k in list(seen):                                # resolved: its check ran and it is not found again
        if runs.get(k.split("|")[1]) and k not in found:
            del seen[k]
    noticed, confirmed = [], []
    for k, f in found.items():
        if k not in seen:
            seen[k] = {"first": today, "last": today}
            noticed.append(dict(f, first=today))
        else:
            seen[k]["last"] = today
            (confirmed if _days(seen[k]["first"], today) >= CONFIRM_DAYS else noticed).append(dict(f, first=seen[k]["first"]))
    mem["last_run"] = today
    by_id = {r["id"]: r for r in recs}
    deltas, unresolved = [], []
    src = {"kind": "derived:recheck", "ref": None, "at": obs.get("at") or today}
    gone = {}
    for f in confirmed:
        gone.setdefault(f["record"], []).append(f)
    for rid, fs in gone.items():
        rec = by_id[rid]
        if rec["type"] == "product":
            anchors = [c for c, field in (("jira", "Jira Project Key"), ("confluence", "Confluence Space"))
                       if cs.field_get(rec["body"], field)]
            lost = {f["check"] for f in fs}
            renamed = any(_candidate(visible, f, rec) for f in fs)     # a project of its name under a new key: moved
            if anchors and set(anchors) <= lost and not renamed:
                deltas.append({"op": "INVALIDATE", "record": rid, "source": dict(src, ref="; ".join(
                    "%s %s" % (f["check"], f["item"]) for f in fs)), "reason": "у %s більше немає %s — двічі поспіль "
                    "(%s і %s)" % (" і ".join("Jira" if f["check"] == "jira" else "Confluence" for f in fs),
                                   ", ".join(f["item"] for f in fs), fs[0]["first"], today)})
                continue
            for f in fs:
                field = "Jira Project Key" if f["check"] == "jira" else "Confluence Space"
                cand = _candidate(visible, f, rec)
                if len(cand) == 1:
                    deltas.append({"op": "UPDATE", "record": rid, "field": field, "value": cand[0],
                                   "reason": "%s %s більше немає; «%s» тепер %s" % (field, f["item"], _title(rec), cand[0]),
                                   "source": dict(src, ref="%s %s" % (f["check"], cand[0]))})
                else:
                    unresolved.append(dict(f, why="%s %s не видно з %s — перевір сам" % (field, f["item"], f["first"])))
        else:
            for f in fs:
                if f["check"] == "member":
                    deltas.append({"op": "REPLACE", "record": rid, "text": f["line"].strip(), "value": "",
                                   "reason": "%s — немає серед активних людей Atlassian з %s" % (f["item"], f["first"]),
                                   "source": dict(src, ref="lookupJiraAccountId")})
                elif f["check"] == "role":
                    deltas.append({"op": "UPDATE", "record": rid, "field": "Role", "value": f["item"],
                                   "reason": "провайдер дає роль %s з %s" % (f["item"], f["first"]),
                                   "source": dict(src, kind="derived:provider:identity", ref="access bundle")})
    flagged = {f["record"] for f in found.values()}
    fine = sorted(rid for rid in checked if rid not in flagged)
    unchecked = [c for c, on in runs.items() if not on]
    return {"checked": checked, "unchecked": unchecked, "noticed": noticed, "confirmed": confirmed, "deltas": deltas,
            "fine": fine, "unresolved": unresolved}
