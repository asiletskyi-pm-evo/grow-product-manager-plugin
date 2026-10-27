#!/usr/bin/env python3
"""Grow PM — the configurator's first pass: what the connectors say about you, as a table to confirm (since v3.22.0).

`ctx bootstrap --observed F` compares an observation file (ctx_observe, schema context-observed/1) with your context
and prints one table: the record, the field, what it says now, what it would say, where that came from and how sure
it is. `--apply --code C` writes what you took — with a store a snapshot first, without one (a new user) the file
`local-context.md` itself from the onboarding skeleton, moved into records at once. Semantics:
references/context-protocol.md §5k.

- diff(obs, recs, srcs)   {rows, inbox, later, same}: a numbered row per fact worth confirming (high and medium:
                          `+` absent, `~` another value, a new record with its fields and lines); marks that keep a
                          row out of the defaults — `✋ твоє` (the value now is yours), `⚠` (two values for one field),
                          `≠ назва` (an organisation named otherwise), `немає організації` (a product or a team with
                          none to go under). A low fact goes to the inbox (`inbox`: its record exists; `later`: it
                          waits for a new record of the table); a fact that agrees is counted
- code(d, recs)           8 hex of the rows shown — sources too — and the records they touch
- chosen(d, take, skip, only)  the rows an apply takes; two values for one field, or a product with no organisation,
                          → ValueError
- render(d, connectors, dropped)   the lines `ctx bootstrap` prints
- new_body(row), skeleton(rows, today, ts, version)   the text of a new record, of a whole new local-context.md
- put_field(body, name, value)   a field set in place, or — absent — right under the record's heading
- list_line(body, name, value)   a line for `#### <name>` (a table row where the subsection is a table)
- deltas(facts, recs, at) the inbox's deltas for the low facts whose record exists (source derived:<from>)

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
LISTS = {"product": ("Dashboards",), "team": ("Members",)}       # the subsections a new record gets
PROFILE_ORDER = ("Name", "Role", "Role label", "Role scope", "Level home", "Email", "Work Email", "Language")
# A field a record may hold under another name (Step 16c writes `Jira`; files from before say `Jira instance`).
FIELD_ALIASES = {"Jira": ("Jira instance",), "Confluence": ("Confluence instance",), "Email": ("Work Email",)}
MARKS = {"mine": "✋ твоє — лише номером", "clash": "⚠ два значення — лише номером",
         "renamed": "≠ назва організації — лише номером", "orphan": "немає організації — візьми й організацію"}


def _n(s):
    return " ".join((s or "").split()).casefold()


def _same(a, b):
    """Equal values, a link and a bare host alike: `https://x.example/` is `x.example`."""
    norm = lambda s: re.sub(r"^https?://", "", _n(s)).rstrip("/")
    return norm(a) == norm(b)





def kind_of(frm):
    """The source a written field keeps: what you said or your file is yours; the rest is derived."""
    return frm if frm in ("user", "local-context") else "derived:" + frm


def _mine(kind):
    return not str(kind or "").startswith(("derived:", "inbox:ctx-", "ctx-bootstrap"))


def bare_title(rec):
    t = rec["title"]
    return t.split(":", 1)[1].strip() if ":" in t and rec["type"] in PREFIX else t


def find(recs, typ, title, fallback=True):
    """The record a fact is about: the profile; an organisation, product or team by its name (case aside); with
    `fallback`, an organisation named otherwise when there is exactly one."""
    same = [r for r in recs if r["type"] == typ and not cs.has_status_region(r["body"])]
    if typ == "profile":
        return same[0] if same else None
    hit = [r for r in same if _n(bare_title(r)) == _n(title)]
    if hit:
        return hit[0]
    return same[0] if fallback and typ == "org" and len(same) == 1 else None


def _under(body, name):
    """The lines of the subsection `#### <name>` (its aliases too), outside regions; None when there is none."""
    lines = [core for _, core, _ in cs._lines(body)]
    at = next((k for k, c in enumerate(lines) if any(cs.heading_matches(c, n) for n in cs.section_names(name))), None)
    if at is None:
        return None
    out = []
    for c in lines[at + 1:]:
        if cs._heading_text(c) is not None:
            break
        out.append(c)
    return out


def has_line(body, name, value):
    """Is `value` already a line of `#### <name>` — the whole line (a bullet's text) or a table row's first cell?"""
    v = _n(value)
    for c in _under(body, name) or ():
        s = c.strip()
        if s.startswith("|"):
            if _n(s.strip("|").split("|")[0]) == v:
                return True
        elif _n(s.lstrip("-*").strip()) == v or _n(s) == v:
            return True
    return False


def diff(obs, recs, srcs=None):
    srcs = srcs or csrc.empty()
    orgs = [r for r in recs if r["type"] == "org" and not cs.has_status_region(r["body"])]
    resolved = []
    for f in obs["facts"]:
        rec = find(recs, f["type"], f["title"])
        renamed = bool(rec) and f["type"] == "org" and _n(bare_title(rec)) != _n(f["title"])
        where = rec["id"] if rec else "%s:%s" % (f["type"], _n(f["title"]))
        what = f["field"] or ("list:" + f["list"] if f["list"] else "")
        resolved.append((where, what, _n(f["value"]) if f["list"] else "", f, rec, renamed))
    groups = {}
    for where, what, line, f, rec, renamed in resolved:
        groups.setdefault((where, what, line), []).append((f, rec, renamed))
    rows, inbox, later, same, news = [], [], [], 0, {}
    order = lambda k: (TYPE_ORDER[groups[k][0][0]["type"]], k[0], k[1], k[2])
    for key in sorted(groups, key=order):
        group = sorted(groups[key], key=lambda x: -_RANK[x[0]["confidence"]])
        top = [x for x in group if x[0]["confidence"] == group[0][0]["confidence"]]
        values = []
        for x in top:
            if _n(x[0]["value"]) not in [_n(v[0]["value"]) for v in values]:
                values.append(x)
        clash = len(values) > 1
        for f, rec, renamed in values:
            if f["field"]:
                held = [v for v in [cs.field_get(rec["body"], n) for n in (f["field"],) + FIELD_ALIASES.get(f["field"], ())]
                        if v is not None] if rec else []
                now = (cs.field_get(rec["body"], f["field"]) if rec else None)
                if now is None and held:
                    now = held[0]
                sign = "=" if any(_same(v, f["value"]) for v in held) else ("+" if now is None else "~")
            elif f["list"]:
                now = None
                sign = "=" if rec and has_line(rec["body"], f["list"], f["value"]) else "+"
            else:
                now = None
                sign = "=" if rec else "+"
            if sign == "=":
                same += 1
                continue
            if f["confidence"] == "low":
                (inbox if rec else later).append(f)
                continue
            if rec is None and f["type"] != "profile":
                nk = (f["type"], _n(f["title"]))
                row = news.get(nk)
                if row is None:
                    row = news[nk] = {"new": True, "type": f["type"], "title": f["title"], "record": None,
                                      "fields": [], "lists": [], "from": f["from"], "confidence": f["confidence"],
                                      "ref": f["ref"], "sign": "+", "mine": False, "clash": False, "renamed": False,
                                      "orphan": False}
                    rows.append(row)
                if f["field"]:
                    row["fields"].append({"field": f["field"], "value": f["value"], "from": f["from"],
                                          "confidence": f["confidence"], "ref": f["ref"]})
                elif f["list"]:
                    row["lists"].append({"list": f["list"], "value": f["value"], "from": f["from"],
                                         "confidence": f["confidence"], "ref": f["ref"]})
                row["clash"] = row["clash"] or clash
                if _RANK[f["confidence"]] > _RANK[row["confidence"]]:
                    row.update(**{"from": f["from"], "confidence": f["confidence"], "ref": f["ref"]})
                continue
            if not f["field"] and not f["list"]:        # the profile itself: nothing to show
                continue
            kind = None
            if rec and f["field"] and now is not None:
                own = [x for x in csrc.of(srcs, rec) if x["key"] == csrc.field_key(f["field"])]
                kind = own[0]["kind"] if own else rec.get("source")
            rows.append({"new": False, "type": f["type"], "title": f["title"], "record": rec["id"] if rec else None,
                         "field": f["field"], "list": f["list"], "now": now, "value": f["value"], "from": f["from"],
                         "confidence": f["confidence"], "ref": f["ref"], "sign": sign,
                         "mine": sign == "~" and _mine(kind), "clash": clash, "renamed": renamed, "orphan": False})
    new_org = any(r["new"] and r["type"] == "org" for r in rows)
    for r in rows:
        if r["new"] and r["type"] in ("product", "team") and not orgs and not new_org:
            r["orphan"] = True
    for k, r in enumerate(rows, 1):
        r["n"] = k
        r["default"] = not (r["mine"] or r["clash"] or r["renamed"] or r["orphan"])
    titles = {(r["type"], _n(r["title"])): r["n"] for r in rows if r["new"]}
    for f in later:
        f["waits_for"] = titles.get((f["type"], _n(f["title"])))
    return {"rows": rows, "inbox": inbox, "later": [f for f in later if f["waits_for"]], "same": same,
            "orphans": [f for f in later if not f["waits_for"]]}


def _src(x):
    return [x.get("from"), x.get("confidence"), x.get("ref")]


def code(d, recs):
    sha = {r["id"]: cs.sha_text(r["body"]) for r in recs}
    shown = [[r["n"], r["type"], r["title"], r.get("field"), r.get("list"), r.get("now"), r.get("value"), _src(r),
              [[f["field"], f["value"]] + _src(f) for f in r.get("fields") or ()],
              [[x["list"], x["value"]] + _src(x) for x in r.get("lists") or ()],
              r["sign"], r["default"], sha.get(r.get("record") or "", "")] for r in d["rows"]]
    shown.append([[f["type"], f["title"], f["field"], f["list"], f["value"]] + _src(f) for f in d["inbox"] + d["later"]])
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
    """The rows an apply writes: `only` exactly those; else the default ones plus `take`, less `skip`. A number the
    table does not have, `only` with `take`/`skip`, two values for one field, a product or a team with no organisation
    taken → ValueError (before anything is written)."""
    have = {r["n"] for r in d["rows"]}
    t, s, o = _nums(take), _nums(skip), _nums(only)
    bad = sorted((t | s | o) - have)
    if bad:
        raise ValueError("у таблиці немає рядка №%s" % ", ".join(map(str, bad)))
    if o and (t or s):
        raise ValueError("--only — це саме ці рядки; без --take і --skip")
    want = o or ({r["n"] for r in d["rows"] if r["default"]} | t) - s
    rows = [r for r in d["rows"] if r["n"] in want]
    seen = {}
    for r in rows:
        if r["new"] or not r.get("field"):
            continue
        k = (r.get("record") or r["type"], r["field"])
        if k in seen:
            raise ValueError("рядки №%d і №%d — два значення одного поля; візьми одне" % (seen[k], r["n"]))
        seen[k] = r["n"]
    if any(r["new"] and r["type"] in ("product", "team") for r in rows) and \
            any(r["orphan"] for r in rows) and not any(r["new"] and r["type"] == "org" for r in rows):
        raise ValueError("продукт чи команда потребує організації — візьми рядок організації або додай її відповіддю "
                         "(type org, from user)")
    return rows


def _where(r):
    return "%s · %s" % ((r.get("record") or r["type"]) if r["type"] == "profile" or r.get("record") else
                        "%s %s" % (PREFIX.get(r["type"], r["type"]), r["title"]), r.get("field") or ("#### " + r["list"]))


def render(d, connectors=None, dropped=None):
    out = []
    for r in d["rows"]:
        src = r["from"] + ((" (%s)" % r["ref"]) if r.get("ref") else "")
        marks = [MARKS[m] for m in ("mine", "clash", "renamed", "orphan") if r.get(m)]
        if r["new"]:
            what = "новий запис %s: %s" % (PREFIX.get(r["type"], r["type"]), r["title"])
            bits = ["%s: %s" % (f["field"], f["value"]) for f in r["fields"]] + \
                   ["%s: %s" % (x["list"], x["value"]) for x in r["lists"]]
            if bits:
                what += " (%s)" % "; ".join(bits)
        elif r.get("list"):
            what = "%s · + «%s»" % (_where(r), r["value"])
        else:
            what = "%s: %s → %s" % (_where(r), r["now"] if r["now"] is not None else "—", r["value"])
            if r.get("renamed"):
                what += " (факт про «%s»)" % r["title"]
        out.append("%d. %s %s · %s · %s%s" % (r["n"], r["sign"], what, src, LEVEL_UA[r["confidence"]],
                                              (" · " + " · ".join(marks)) if marks else ""))
    tail = ["збігається: %d" % d["same"], "у скриньку піде: %d (низька певність)" % len(d["inbox"])]
    if d["later"]:
        tail.append("ще %d — коли візьмеш нові записи" % len(d["later"]))
    if d["orphans"]:
        tail.append("без запису, не піде нікуди: %d" % len(d["orphans"]))
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
    """The text of a new organisation, product or team: its heading, its fields, its subsections with their lines."""
    level = "##" if row["type"] == "org" else "###"
    text = "%s %s: %s\n\n" % (level, PREFIX[row["type"]], row["title"])
    if row["fields"]:
        text += _field_lines(row["fields"]) + "\n"
    names = list(LISTS.get(row["type"], ())) + [x["list"] for x in row.get("lists") or ()
                                                if x["list"] not in LISTS.get(row["type"], ())]
    for name in dict.fromkeys(names):
        lines = [x["value"] for x in row.get("lists") or () if x["list"] == name]
        text += "#### %s\n\n" % name + ("".join("- %s\n" % v for v in lines) + "\n" if lines else "")
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
    """A whole local-context.md for a new user (onboarding-steps.md Step 16c, Basic): the profile fields taken in Step
    16c's order, the Judgment defaults Basic records silently (Step 4b), the onboarding status, then each organisation
    with its products and teams. A product or a team needs an organisation — ValueError when none was taken."""
    prof = sorted([r for r in rows if r["type"] == "profile" and r.get("field")],
                  key=lambda r: (PROFILE_ORDER.index(r["field"]) if r["field"] in PROFILE_ORDER else 99, r["field"]))
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
               "- **Extended completed at:** not yet\n- **Last test run at:** never\n- **Deferred steps:** %s\n"
               "- **Skip nudges:** false\n\n" % (ts, ", ".join(deferred)))
    for k, org in enumerate(orgs):
        out.append(new_body(org))
        mine = kids if k == 0 else []                   # several organisations: products go under the first
        for r in sorted(mine, key=lambda r: TYPE_ORDER[r["type"]]):
            out.append(new_body(r))
    return "".join(out).rstrip("\n") + "\n"


def put_field(body, name, value):
    """The field set where it is; an absent one right under the record's heading when the first bullet list sits under
    a subheading (an organisation's `#### Tableau`) — not inside that subsection."""
    if cs.field_get(body, name) is not None:
        return cs.field_set(body, name, value)
    lines = cs._lines(body)
    first_head = next((k for k, (_, c, _) in enumerate(lines) if cs._heading_text(c) is not None), None)
    first_bullet = next((k for k, (_, c, _) in enumerate(lines) if c.startswith("- ")), None)
    sub = next((k for k, (_, c, _) in enumerate(lines) if first_head is not None and k > first_head
                and cs._heading_text(c) is not None), None)
    if first_head is None or first_bullet is None or sub is None or first_bullet < sub:
        return cs.field_set(body, name, value)
    off, core, end = lines[first_head]
    at = off + len(core) + len(end)
    return body[:at] + "\n- **%s:** %s\n" % (name, value) + body[at:]


def list_line(body, name, value):
    """(line, under): a table row where `#### name` holds a table (as many cells as its header), else a bullet;
    `under` None when the record has no such subsection."""
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


def add_line(body, name, value):
    """`value` into `#### <name>`, the subsection made at the record's end when it has none."""
    line, under = list_line(body, name, value)
    if under:
        return cs.append_line(body, line, under=under), line
    return body.rstrip("\n") + "\n\n#### %s\n\n%s\n" % (name, line), line


def deltas(facts, recs, at):
    """The inbox's deltas for low facts whose record exists: a field → UPDATE, a list line → ADD (under its
    subsection; a record without one gets the line at its end)."""
    out = []
    for f in facts:
        rec = find(recs, f["type"], f["title"], fallback=False) or find(recs, f["type"], f["title"])
        if rec is None:
            continue
        src = {"kind": kind_of(f["from"]), "ref": f["ref"], "at": at}
        why = "знайдено в конекторах при налаштуванні (низька певність)"
        if f["field"]:
            out.append({"op": "UPDATE", "record": rec["id"], "field": f["field"], "value": f["value"], "reason": why,
                        "source": src})
        elif f["list"]:
            line, under = list_line(rec["body"], f["list"], f["value"])
            d = {"op": "ADD", "record": rec["id"], "text": line, "reason": why, "source": src}
            if under:
                d["under"] = under
            out.append(d)
    return out
