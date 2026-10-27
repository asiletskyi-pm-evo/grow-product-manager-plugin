#!/usr/bin/env python3
"""Grow PM — the observation file: what a skill saw in your connectors, handed to ctx (since v3.22.0).

`ctx` calls no connector. The configurator, the morning brief or `/context recheck` read them — read-only, by the map
in references/context-observe.md — and write one JSON file (schema context-observed/1, in the session's scratchpad,
never in the store); `ctx bootstrap` and `ctx validate --recheck` read it. Everything a test can hold is decided here,
not by the skill: how sure a fact is, which facts are too thin to show, what of a meeting or a mail is never kept.

- SCHEMA                 the file's schema; CONNECTORS the connectors it may name (and `provider:<id>`)
- FROM                   where a fact may come from → the connector that must have answered (None: no connector)
- MIN_COUNT              the activity a fact needs to be shown — below it the fact is dropped, with why
- level_of(from, field)  high · medium · low — decided by where it came from, never passed by the skill
- parse(raw)             the file → {at, connectors, facts, dropped, checks}; ValueError when the file itself is not of
                         the shape (one bad fact is dropped with why, the others kept)

A fact: {type: profile|org|product|team, title (not for the profile), field | list (or neither: the record itself),
value, from, ref, evidence, count}. Of a calendar, Fireflies or mail fact only the count is kept, worded by ctx: the
title of a meeting or the subject of a letter may carry what nobody should keep, and no pattern can tell.
Stdlib only.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx_never as cn  # noqa: E402

SCHEMA = "context-observed/1"
CONNECTORS = ("atlassian", "calendar", "mail", "fireflies", "tableau")
TYPES = ("profile", "org", "product", "team")
LEVELS = ("high", "medium", "low")
FROM = {"atlassian:user": "atlassian", "atlassian:site": "atlassian",
        "jira:active": "atlassian", "jira:visible": "atlassian",
        "confluence:active": "atlassian", "confluence:visible": "atlassian",
        "calendar:owner": "calendar", "calendar:co-attendee": "calendar",
        "mail:domain": "mail", "fireflies:participant": "fireflies", "tableau:owned": "tableau",
        "provider:identity": "provider", "local-context": None, "user": None}
_LEVEL = {"atlassian:user": "high", "atlassian:site": "high", "calendar:owner": "high", "mail:domain": "high",
          "local-context": "high", "user": "high", "provider:identity": "high",
          "jira:active": "medium", "confluence:active": "medium",
          "jira:visible": "low", "confluence:visible": "low", "calendar:co-attendee": "low",
          "fireflies:participant": "low", "tableau:owned": "low"}
MIN_COUNT = {"jira:active": 5, "confluence:active": 3, "calendar:co-attendee": 3}
_COUNTED = {"jira:active": "%d твоїх задач за 90 днів", "confluence:active": "%d твоїх сторінок за 90 днів",
            "calendar:co-attendee": "%d спільних зустрічей за 30 днів", "fireflies:participant": "%d записаних зустрічей"}
QUIET = ("calendar:", "fireflies:", "mail:")        # only the count is kept: no title, no subject, no text
# What each source may give (type, field | "list:<name>" | None for the record itself); `local-context` and `user` any.
ALLOWED = {"atlassian:user": {("profile", "Name"), ("profile", "Email")},
           "atlassian:site": {("org", "Jira"), ("org", "Confluence")},
           "mail:domain": {("org", "Domain")},
           "calendar:owner": {("profile", "Email")},
           "provider:identity": {("team", None), ("profile", "Role")},
           "jira:active": {("product", None), ("product", "Jira Project Key")},
           "jira:visible": {("product", None), ("product", "Jira Project Key")},
           "confluence:active": {("product", "Confluence Space")},
           "confluence:visible": {("product", "Confluence Space")},
           "calendar:co-attendee": {("team", "list:Members")},
           "fireflies:participant": {("team", "list:Members")},
           "tableau:owned": {("product", "list:Dashboards")}}
# The shape a value of these fields must have — a meeting's title or a letter's subject has none of them.
_NAME = re.compile(r"^(?:[^\W\d_][\w'’.-]*)(?: [^\W\d_][\w'’.-]*){0,4}\Z")
SHAPES = {"Email": re.compile(r"^[^@\s:]+@[a-z0-9.-]+\.[a-z]{2,}\Z", re.I),
          "Domain": re.compile(r"^[a-z0-9-]+(?:\.[a-z0-9-]+)+\Z", re.I),
          "Jira": re.compile(r"^https?://[^\s/]+/?\Z"), "Confluence": re.compile(r"^https?://[^\s/]+(?:/wiki)?/?\Z"),
          "Jira Project Key": re.compile(r"^[A-Z][A-Z0-9_]{1,19}\Z"),
          "Confluence Space": re.compile(r"^~?[A-Za-z0-9_-]{1,40}\Z"),
          "list:Dashboards": re.compile(r"^[^\n]{1,120}https?://\S+\Z")}
CHECKS = {"jira:visible": "values", "confluence:visible": "values", "atlassian:people": "people"}
_FACT_KEYS = ("type", "title", "field", "list", "value", "from", "ref", "evidence", "count")
_TOP_KEYS = ("schema", "at", "connectors", "facts", "checks")
_MARKUP = re.compile(r"<!--|-->")
_DAY = re.compile(r"\d{4}-\d{2}-\d{2}\Z")
EVIDENCE_MAX = 200


def level_of(frm, field):
    """How sure a fact is, by where it came from: a provider knows your team for sure, your role only by inference."""
    if frm == "provider:identity" and field == "Role":
        return "medium"
    return _LEVEL.get(frm)


def _connector_ok(frm, connectors):
    need = FROM[frm]
    if need is None:
        return True
    if frm == "mail:domain":                            # your address comes from Atlassian or from the mail connector
        return connectors.get("mail") == "ok" or connectors.get("atlassian") == "ok"
    if need == "provider":
        return any(k.startswith("provider:") and v == "ok" for k, v in connectors.items())
    return connectors.get(need) == "ok"


def _line(v, key):
    if v is None:
        return None
    if not isinstance(v, str):
        raise ValueError("%s is not text" % key)
    if len(v.strip().splitlines()) > 1:                 # every line break splitlines() knows, U+2028 too
        raise ValueError("%s takes one line" % key)
    v = " ".join(v.split()) if key != "value" else v.strip()
    return v or None


def _fact(raw, connectors):
    """One fact → its canonical dict; ValueError naming what is wrong (the fact is then dropped)."""
    if not isinstance(raw, dict):
        raise ValueError("факт — JSON-об'єкт")
    if "confidence" in raw:
        raise ValueError("певність вирішує ctx, не скіл — без ключа confidence")
    unknown = sorted(set(raw) - set(_FACT_KEYS))
    if unknown:
        raise ValueError("невідомі ключі %s" % ", ".join(unknown))
    t = raw.get("type")
    if not isinstance(t, str) or t not in TYPES:
        raise ValueError("type — один із %s" % ", ".join(TYPES))
    frm = raw.get("from")
    if not isinstance(frm, str) or frm not in FROM:
        raise ValueError("from — один із %s" % ", ".join(sorted(FROM)))
    if not _connector_ok(frm, connectors):
        raise ValueError("%s: конектор не відповів (connectors)" % frm)
    f = {"type": t, "from": frm}
    f["title"] = _line(raw.get("title"), "title")
    if t == "profile":
        if f["title"]:
            raise ValueError("у профілю немає title")
    elif not f["title"]:
        raise ValueError("%s потребує title" % t)
    f["field"], f["list"] = _line(raw.get("field"), "field"), _line(raw.get("list"), "list")
    if f["field"] and f["list"]:
        raise ValueError("field або list, не обидва")
    f["value"] = _line(raw.get("value"), "value") or ""
    if (f["field"] or f["list"]) and not f["value"]:
        raise ValueError("value порожнє")
    if f["value"] and not (f["field"] or f["list"]):
        raise ValueError("value без field чи list — факт про сам запис значення не має")
    what = f["field"] or (("list:" + f["list"]) if f["list"] else None)
    if frm in ALLOWED and (t, what) not in ALLOWED[frm]:
        raise ValueError("%s не дає %s%s" % (frm, t, (" · " + what) if what else ""))
    shape = SHAPES.get(what) or (_NAME if what in ("Name", "list:Members") else None)
    if shape and not (shape.match(f["value"]) and (shape is not _NAME or all(w[0].isupper() for w in f["value"].split()))):
        raise ValueError("%s не схоже на %s" % (what, "ім'я" if shape is _NAME else what))
    if frm in ("mail:domain", "atlassian:site"):        # the organisation's name: the domain's or the site's own word
        host = f["value"].split("://")[-1].split("/")[0]
        if f["title"].casefold() not in (host.split(".")[0].casefold(), host.casefold()):
            raise ValueError("%s: назва організації — слово з домену чи сайту (%s); іншу назву дає відповідь (user)"
                             % (frm, host.split(".")[0]))
    for k in ("title", "field", "list"):
        if f[k] and (_MARKUP.search(f[k]) or "*" in f[k] or f[k].startswith("#")):
            raise ValueError("%s — назва, не розмітка" % k)
    if _MARKUP.search(f["value"]) or f["value"].lstrip().startswith("#") or f["value"].strip() in ("---", "..."):
        raise ValueError("value — рядок запису, не заголовок, маркер регіону чи лінія")
    count = raw.get("count")
    if count is not None and (not isinstance(count, int) or isinstance(count, bool) or count < 0):
        raise ValueError("count — ціле число")
    f["count"] = count
    if frm in MIN_COUNT and (count or 0) < MIN_COUNT[frm]:
        raise ValueError("нижче порогу: %s потребує ≥ %d, є %d" % (frm, MIN_COUNT[frm], count or 0))
    f["ref"], f["evidence"] = _line(raw.get("ref"), "ref"), _line(raw.get("evidence"), "evidence")
    if frm.startswith(QUIET):
        f["evidence"] = None
        f["ref"] = (_COUNTED[frm] % count) if frm in _COUNTED and count is not None else None
    if f["evidence"] and len(f["evidence"]) > EVIDENCE_MAX:
        raise ValueError("evidence — до %d знаків" % EVIDENCE_MAX)
    kinds = cn.scan(" \n".join(x for x in (f["title"], f["field"], f["list"], f["value"], f["ref"], f["evidence"]) if x))
    if f["field"] and f["value"]:
        kinds = kinds or cn.scan("%s: %s" % (f["field"], f["value"]))
    if kinds:
        raise ValueError(cn.message(kinds))
    f["confidence"] = level_of(frm, f["field"])
    return f


def _checks(raw):
    out = {}
    if raw is None:
        return out
    if not isinstance(raw, dict):
        raise ValueError("checks is an object")
    for name, body in raw.items():
        if name not in CHECKS:
            raise ValueError("unknown check %s — one of %s" % (name, ", ".join(CHECKS)))
        if not isinstance(body, dict):
            raise ValueError("check %s is an object" % name)
        c = {"complete": body.get("complete") is True}
        if CHECKS[name] == "values":
            vals = body.get("values")
            if not isinstance(vals, list):
                raise ValueError("check %s takes values: a list" % name)
            c["values"] = []
            for v in vals:
                if isinstance(v, str) and v.strip():
                    c["values"].append({"key": v.strip(), "name": None})
                elif isinstance(v, dict) and isinstance(v.get("key"), str) and v["key"].strip() \
                        and (v.get("name") is None or isinstance(v.get("name"), str)):
                    c["values"].append({"key": v["key"].strip(), "name": (v.get("name") or "").strip() or None})
                else:
                    raise ValueError("check %s: a value is a key or {key, name}" % name)
        else:
            for k in ("active", "inactive", "unknown"):
                vals = body.get(k, [])
                if not isinstance(vals, list) or not all(isinstance(x, str) and x.strip() for x in vals):
                    raise ValueError("check %s: %s is a list of names" % (name, k))
                c[k] = [" ".join(x.split()) for x in vals]
        out[name] = c
    return out


def parse(raw):
    """The observation file (already JSON-decoded) → {at, connectors, facts, dropped, checks}. The file of another
    shape → ValueError; a fact that is wrong, too thin or holds a secret → `dropped` [{i, why}], never its value."""
    if not isinstance(raw, dict) or raw.get("schema") != SCHEMA:
        raise ValueError("not of schema %s" % SCHEMA)
    unknown = sorted(set(raw) - set(_TOP_KEYS))
    if unknown:
        raise ValueError("unknown key(s) %s" % ", ".join(unknown))
    at = raw.get("at")
    if at is not None and not (isinstance(at, str) and _DAY.match(at)):
        raise ValueError("at is a date, YYYY-MM-DD")
    conn = raw.get("connectors")
    if not isinstance(conn, dict):
        raise ValueError("connectors is an object {name: ok | absent | error: …}")
    for k, v in conn.items():
        if k not in CONNECTORS and not (isinstance(k, str) and re.match(r"provider:[a-z0-9][a-z0-9-]*\Z", k)):
            raise ValueError("unknown connector %s — one of %s or provider:<id>" % (k, ", ".join(CONNECTORS)))
        if not isinstance(v, str) or not (v in ("ok", "absent", "error") or v.startswith("error:")):
            raise ValueError("connector %s: ok, absent or error: …" % k)
    facts = raw.get("facts", [])
    if not isinstance(facts, list):
        raise ValueError("facts is a list")
    out, dropped = [], []
    for i, f in enumerate(facts, 1):
        try:
            out.append(_fact(f, conn))
        except ValueError as e:
            dropped.append({"i": i, "why": str(e)})
    return {"at": at, "connectors": dict(conn), "facts": out, "dropped": dropped, "checks": _checks(raw.get("checks"))}


def load(path):
    """parse() of the file at `path`; ValueError when it does not read as JSON."""
    import json
    try:
        with open(path, encoding="utf-8") as f:
            return parse(json.load(f))
    except OSError as e:
        raise ValueError("observation file %s: %s" % (path, e.strerror or e))
    except ValueError as e:
        raise ValueError("observation file %s: %s" % (path, e))
