#!/usr/bin/env python3
"""Grow PM — the configurator's first pass: what the connectors say about you, as a table to confirm (since v3.22.0).

`ctx bootstrap --observed F` compares an observation file (ctx_observe, schema context-observed/1) with your context
and prints one table: the record, the field, what it says now, what it would say, where that came from and how sure
it is. `--apply --code C` writes what you took — with a store a snapshot first, without one (a new user) the file
`local-context.md` itself from the onboarding skeleton, moved into records at once. Semantics:
references/context-protocol.md §5k.

- diff(obs, recs, srcs)   {rows, inbox, same, orphans}: a numbered row per fact worth confirming (high and medium:
                          `+` absent, `~` another value — `✋ твоє` when the value now is yours —, a new record with its
                          fields); a fact low in confidence goes to the inbox instead; a fact that agrees is counted
- code(d, recs)           8 hex of the rows shown and the records they touch: an apply with another is refused
- chosen(d, take, skip, only)  the rows an apply takes — by default every row but `✋ твоє` and two values for one field
- render(d, connectors, dropped)   the lines `ctx bootstrap` prints
- new_body(row), skeleton(rows, today, ts, version)   the text of a new record, of a whole new local-context.md
- list_line(body, name, value)   a line for `#### <name>` (a table row where the subsection is a table)
- deltas(facts, recs)     the inbox's deltas for the low facts whose record exists (source derived:<from>)

Writes nothing itself: the lock, the snapshot, the journal and the records are ctx.py's. Stdlib only.
"""
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx_sources as csrc  # noqa: E402
import ctx_store as cs  # noqa: E402

TYPE_ORDER = {"profile": 0, "org": 1, "product": 2, "team": 3}
PREFIX = {"org": "Organization", "product": "Product", "team": "Team"}
LEVEL_UA = {"high": "висока", "medium": "середня", "low": "низька"}
_RANK = {"high": 3, "medium": 2, "low": 1}
# The sections Basic leaves for later (onboarding-steps.md Steps 4b–15 and the Extended add-ons); a team the table
# created is no longer deferred.
DEFERRED = ("judgment", "key-metrics", "teams", "repos", "cjm", "knowledge-library", "templates", "obsidian-vault",
            "custom-sections", "planning", "focus", "people", "design-toolkits", "test-accounts", "landscape",
            "tableau-full", "analytics-extended")
LISTS = {"product": ("Dashboards",), "team": ("Members",)}       # the subsections a new record gets, empty


def _n(s):
    return " ".join((s or "").split()).casefold()


def kind_of(frm):
    """The source a written field keeps: what you said or your file is yours; the rest is derived."""
    return frm if frm in ("user", "local-context") else "derived:" + frm


def _mine(kind):
    return not str(kind or "").startswith(("derived:", "inbox:ctx-", "ctx-bootstrap"))


def bare_title(rec):
    t = rec["title"]
    return t.split(":", 1)[1].strip() if ":" in t and rec["type"] in PREFIX else t


def find(recs, typ, title):
    """The record a fact is about: the profile; an organisation, product or team by its name (case aside); an
    organisation named otherwise when there is exactly one."""
    same = [r for r in recs if r["type"] == typ]
    if typ == "profile":
        return same[0] if same else None
    hit = [r for r in same if _n(bare_title(r)) == _n(title)]
    if hit:
        return hit[0]
    return same[0] if typ == "org" and len(same) == 1 else None


def _has_line(body, value):
    v = _n(value)
    for _, core, _ in cs._lines(body):
        c = _n(core.strip().lstrip("-*").strip().strip("|"))
        if c == v or c.split("|")[0].strip() == v or v in _n(core) and len(v) >= 6:
            return True
    return False


def diff(obs, recs, srcs=None):
    srcs = srcs or csrc.empty()
    best = {}
    for f in obs["facts"]:
        key = (f["type"], _n(f["title"]), f["field"] or ("list:" + f["list"] if f["list"] else ""),
               _n(f["value"]) if f["list"] else "")
        best.setdefault(key, []).append(f)
    rows, inbox, same, news = [], [], 0, {}
    for key in sorted(best, key=lambda k: (TYPE_ORDER[k[0]], k[1], k[2], k[3])):
        group = sorted(best[key], key=lambda f: -_RANK[f["confidence"]])
        top = [f for f in group if f["confidence"] == group[0]["confidence"]]
        values = []
        for f in top:
            if _n(f["value"]) not in [_n(v["value"]) for v in values]:
                values.append(f)
        for f in values:
            rec = find(recs, f["type"], f["title"])
            if f["field"]:
                now = cs.field_get(rec["body"], f["field"]) if rec else None
                sign = "=" if now is not None and _n(now) == _n(f["value"]) else ("+" if now is None else "~")
            elif f["list"]:
                now = None
                sign = "=" if rec and _has_line(rec["body"], f["value"]) else "+"
            else:
                now = None
                sign = "=" if rec else "+"
            if sign == "=":
                same += 1
                continue
            if f["confidence"] == "low":
                inbox.append(f)
                continue
            if rec is None and f["type"] != "profile":
                nk = (f["type"], _n(f["title"]))
                row = news.get(nk)
                if row is None:
                    row = news[nk] = {"new": True, "type": f["type"], "title": f["title"], "record": None,
                                      "fields": [], "from": f["from"], "confidence": f["confidence"], "ref": f["ref"],
                                      "sign": "+", "mine": False, "clash": False}
                    rows.append(row)
                if f["field"]:
                    row["fields"].append({"field": f["field"], "value": f["value"], "from": f["from"],
                                          "confidence": f["confidence"], "ref": f["ref"], "clash": len(values) > 1})
                    row["clash"] = row["clash"] or len(values) > 1
                if _RANK[f["confidence"]] > _RANK[row["confidence"]]:
                    row.update(**{"from": f["from"], "confidence": f["confidence"], "ref": f["ref"]})
                continue
            if not f["field"]:                          # the profile alone, a list line of high/medium: shown as is
                if not f["list"]:
                    continue
            kind = None
            if rec and f["field"] and now is not None:
                own = [x for x in csrc.of(srcs, rec) if x["key"] == csrc.field_key(f["field"])]
                kind = own[0]["kind"] if own else rec.get("source")
            rows.append({"new": False, "type": f["type"], "title": f["title"], "record": rec["id"] if rec else None,
                         "field": f["field"], "list": f["list"], "now": now, "value": f["value"], "from": f["from"],
                         "confidence": f["confidence"], "ref": f["ref"], "sign": sign,
                         "mine": sign == "~" and _mine(kind), "clash": len(values) > 1})
    for k, r in enumerate(rows, 1):
        r["n"] = k
        r["default"] = not r["mine"] and not r["clash"]
    return {"rows": rows, "inbox": inbox, "same": same}


def code(d, recs):
    sha = {r["id"]: cs.sha_text(r["body"]) for r in recs}
    shown = [[r["n"], r["type"], r["title"], r.get("field"), r.get("list"), r.get("now"), r.get("value"),
              r.get("fields"), r["sign"], r["default"], sha.get(r.get("record") or "", "")] for r in d["rows"]]
    shown.append([[f["type"], f["title"], f["field"], f["list"], f["value"]] for f in d["inbox"]])
    return hashlib.sha1(json.dumps(shown, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:8]


def _nums(spec):
    if not spec:
        return set()
    out = set()
    for x in re.split(r"[,\s]+", " ".join(spec) if isinstance(spec, (list, tuple)) else str(spec)):
        if x:
            if not x.isdigit():
                raise ValueError("номери рядків таблиці, через кому")
            out.add(int(x))
    return out


def chosen(d, take=None, skip=None, only=None):
    """The rows an apply writes: `only` exactly those; else the default ones (not ✋ твоє, not ⚠) plus `take`, less
    `skip`. A number the table does not have → ValueError."""
    have = {r["n"] for r in d["rows"]}
    t, s, o = _nums(take), _nums(skip), _nums(only)
    bad = sorted((t | s | o) - have)
    if bad:
        raise ValueError("у таблиці немає рядка №%s" % ", ".join(map(str, bad)))
    if o:
        want = o
    else:
        want = ({r["n"] for r in d["rows"] if r["default"]} | t) - s
    return [r for r in d["rows"] if r["n"] in want]


def _where(r):
    return "%s · %s" % ((r.get("record") or r["type"]) if r["type"] == "profile" or r.get("record") else
                        "%s %s" % (PREFIX.get(r["type"], r["type"]), r["title"]), r.get("field") or ("#### " + r["list"]))


def render(d, connectors=None, dropped=None):
    out = []
    for r in d["rows"]:
        src = r["from"] + ((" (%s)" % r["ref"]) if r.get("ref") else "")
        marks = [m for m, on in (("✋ твоє — лише номером", r["mine"]), ("⚠ два значення — лише номером", r["clash"]))
                 if on]
        if r["new"]:
            what = "новий запис %s: %s" % (PREFIX.get(r["type"], r["type"]), r["title"])
            if r["fields"]:
                what += " (%s)" % "; ".join("%s: %s" % (f["field"], f["value"]) for f in r["fields"])
        elif r.get("list"):
            what = "%s · + «%s»" % (_where(r), r["value"])
        else:
            what = "%s: %s → %s" % (_where(r), r["now"] if r["now"] is not None else "—", r["value"])
        out.append("%d. %s %s · %s · %s%s" % (r["n"], r["sign"], what, src, LEVEL_UA[r["confidence"]],
                                              (" · " + " · ".join(marks)) if marks else ""))
    tail = ["збігається: %d" % d["same"], "у скриньку піде: %d (низька певність)" % len(d["inbox"])]
    if dropped:
        tail.append("відкинуто: %d (%s)" % (len(dropped), "; ".join(sorted({x["why"].split(":")[0] for x in dropped}))))
    silent = sorted(k for k, v in (connectors or {}).items() if v != "ok")
    if silent:
        tail.append("не відповіли: %s" % ", ".join("%s (%s)" % (k, connectors[k]) for k in silent))
    out.append(" · ".join(tail))
    if d["rows"]:
        dflt = [str(r["n"]) for r in d["rows"] if r["default"]]
        held = [str(r["n"]) for r in d["rows"] if not r["default"]]
        out.append("візьму: %s%s" % (", ".join(dflt) or "нічого",
                                     (" · лише номером (--take): %s" % ", ".join(held)) if held else ""))
    return out


# ------------------------------------------------------------------ texts
def _field_lines(fields):
    return "".join("- **%s:** %s\n" % (f["field"], f["value"]) for f in fields)


def new_body(row):
    """The text of a new organisation, product or team: its heading, its fields, the empty subsections it gets."""
    level = "##" if row["type"] == "org" else "###"
    text = "%s %s: %s\n\n" % (level, PREFIX[row["type"]], row["title"])
    if row["fields"]:
        text += _field_lines(row["fields"]) + "\n"
    for name in LISTS.get(row["type"], ()):
        text += "#### %s\n\n" % name
    return text


def plugin_version():
    p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".claude-plugin", "plugin.json")
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f).get("version") or "unknown"
    except (OSError, ValueError):
        return "unknown"


SKELETON_HEADINGS = ("# Local Context — Grow Product Manager", "## User Profile", "## Judgment", "## Onboarding Status",
                     "## Organization:", "### Product:", "### Team:")


def skeleton(rows, today, ts, version):
    """A whole local-context.md for a new user (onboarding-steps.md Step 16c, Basic): the profile fields taken, the
    Judgment defaults Basic records silently (Step 4b), the onboarding status, then each organisation with its
    products and teams. A product or a team needs an organisation — ValueError when none was taken."""
    prof = [r for r in rows if r["type"] == "profile" and r.get("field")]
    orgs = [r for r in rows if r["new"] and r["type"] == "org"]
    kids = [r for r in rows if r["new"] and r["type"] in ("product", "team")]
    if kids and not orgs:
        raise ValueError("продукт чи команда потребує організації — візьми рядок організації або додай її відповіддю "
                         "(type org, from user)")
    deferred = [s for s in DEFERRED if not (s == "teams" and any(r["type"] == "team" for r in kids))]
    out = ["# Local Context — Grow Product Manager\n\n> Generated: %s. Updated: %s.\n> Configurator version: %s\n\n"
           % (today, today, version)]
    out.append("## User Profile\n\n" + _field_lines([{"field": r["field"], "value": r["value"]} for r in prof]) + "\n")
    out.append("## Judgment\n\n- **Hypothesis first:** on\n- **Learning mode:** off\n- **Hats allowed:** all\n"
               "- **Build first:** on\n\n")
    out.append("## Onboarding Status\n\n- **Mode:** basic\n- **Basic completed at:** %s\n"
               "- **Extended completed at:** not yet\n- **Deferred steps:** %s\n- **Skip nudges:** false\n\n"
               % (ts, ", ".join(deferred)))
    for k, org in enumerate(orgs):
        out.append(new_body(org))
        mine = kids if k == 0 else []                   # several organisations: products go under the first
        for r in sorted(mine, key=lambda r: TYPE_ORDER[r["type"]]):
            out.append(new_body(r))
    return "".join(out).rstrip("\n") + "\n"


def list_line(body, name, value):
    """(line, under): a table row where `#### name` holds a table (as many cells as its header), else a bullet;
    `under` None when the record has no such subsection — the line then ends the record."""
    lines = [core for _, core, _ in cs._lines(body)]
    at = next((k for k, c in enumerate(lines) if any(cs.heading_matches(c, n) for n in cs.section_names(name))), None)
    if at is None:
        return "- " + value, None
    under = lines[at].strip()
    for c in lines[at + 1:]:
        if cs._heading_text(c) is not None:
            break
        if c.strip().startswith("|"):
            cells = max(c.strip().strip("|").count("|") + 1, 1)
            return "| " + value + " |" + " |" * (cells - 1), under
    return "- " + value, under


def deltas(facts, recs, at):
    """The inbox's deltas for low facts whose record exists: a field → UPDATE, a list line → ADD."""
    out = []
    for f in facts:
        rec = find(recs, f["type"], f["title"])
        if rec is None:
            continue
        src = {"kind": kind_of(f["from"]), "ref": f["ref"], "at": at}
        if f["field"]:
            out.append({"op": "UPDATE", "record": rec["id"], "field": f["field"], "value": f["value"],
                        "reason": "знайдено в конекторах при налаштуванні (низька певність)", "source": src})
        elif f["list"]:
            line, under = list_line(rec["body"], f["list"], f["value"])
            d = {"op": "ADD", "record": rec["id"], "text": line, "reason": "знайдено в конекторах при налаштуванні "
                 "(низька певність)", "source": src}
            if under:
                d["under"] = under
            out.append(d)
    return out
