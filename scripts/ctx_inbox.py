#!/usr/bin/env python3
"""Grow PM — the inbox: what skills learned about your context, waiting for your «так» (since v3.21.0).

A skill ends its run with deltas — ADD a line, UPDATE a field, INVALIDATE a record, NOOP «checked, still so» — and
`ctx propose` keeps them in `<store>/.state/inbox.json` (schema context-inbox/1). The urgent ones (who you are, your
team, a product's keys, anything closed) the skill asks about at once; the rest wait for `ctx inbox list` — in the
morning brief or `/context inbox` — and are taken in one batch. Semantics: references/context-protocol.md §5i.

- SCHEMA, FILE, WHERE      the inbox file; DELTA_SCHEMA the shape of one delta
- load / save              read and write the inbox: a key this build does not know is refused, a file that cannot be
                           read stops the run — never reset
- normalize(raw)           one delta as given → its canonical dict, or ValueError naming what is wrong
- sig(delta)               the delta's identity: the same change from two skills is one entry
- urgent(delta, rec)       asked at once (URGENT): every INVALIDATE, a profile's identity fields, an organisation's
                           domain, a product's keys, any change to a team
- apply_to(delta, rec, today)  the record's body after the delta — raises cs.RegionError inside a provider's region,
                           ValueError for a value outside its type; the body unchanged = «уже так»
- propose(mem, deltas, skill, recs, today)  the deltas into the inbox, in place: per delta one status
- code(mem, recs)          8 hex of what `inbox list` shows (number, identity, the record's current hash): an accept or
                           a reject with another code is refused — the inbox changed since it was shown
- render(mem, recs, today) the list, one line an entry
- pick(mem, which)         `all` or numbers → entries; take(mem, entries) drops them; reject(mem, entries, day, why)
- merge_back(mem, before, sigs)  after `ctx undo`: the entries proposed later than the undone change come back

Writes nothing itself: the lock, the snapshot, the journal and the records are ctx.py's. Stdlib only.
"""
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx_never as cn  # noqa: E402
import ctx_schema as sc  # noqa: E402
import ctx_store as cs  # noqa: E402

SCHEMA = "context-inbox/1"
DELTA_SCHEMA = "context-delta/1"
FILE = "inbox.json"
WHERE = ".state/" + FILE
OPS = ("ADD", "UPDATE", "INVALIDATE", "NOOP")
_KEYS = ("schema", "next", "entries", "rejected")
_ENTRY_KEYS = ("n", "sig", "delta", "skills", "at", "record_sha", "was", "urgent")
_DELTA_KEYS = ("op", "record", "field", "value", "text", "under", "reason", "evidence", "source")
_SOURCE_KEYS = ("kind", "ref", "at")
EVIDENCE_MAX = 200
REJECT_DAYS = 180
OLD_DAYS = 30
_DAY = re.compile(r"\d{4}-\d{2}-\d{2}\Z")
_MARKUP = re.compile(r"<!--|-->")
_SKILL = re.compile(r"^(?:[a-z0-9-]+:)?([a-z0-9][a-z0-9-]*)$")
PEOPLE_SKILLS = ("goal-setter", "one-on-one", "performance-review", "hiring-designer", "offboarding-guide",
                 "delegation-coach")
# Asked at once (plan C3): field names as references/context-fields.yaml and onboarding-steps.md Step 16c give them.
URGENT = {"profile": ("Name", "Role", "Role label", "Role scope", "Level home", "Email", "Work Email", "Language"),
          "org": ("Domain", "Jira", "Confluence", "Jira instance", "Confluence instance"),
          "product": ("Jira Project Key", "Confluence Space", "URL")}


def empty():
    return {"schema": SCHEMA, "next": 1, "entries": [], "rejected": []}


def _error(kind, why):
    return cs.StoreError("inbox %s: %s (%s)" % (kind, WHERE, " ".join(str(why).split())[:300]))


def _clean(raw):
    if not isinstance(raw, dict) or raw.get("schema") != SCHEMA:
        raise ValueError("not of schema %s" % SCHEMA)
    unknown = sorted(set(raw) - set(_KEYS))
    if unknown:
        raise ValueError("unknown key(s) %s — a newer plugin wrote it" % ", ".join(unknown))
    nxt = raw.get("next", 1)
    entries, rejected = raw.get("entries", []), raw.get("rejected", [])
    if not isinstance(nxt, int) or nxt < 1 or not isinstance(entries, list) or not isinstance(rejected, list):
        raise ValueError("not of the shape {schema, next, entries, rejected}")
    out = empty()
    seen = set()
    for e in entries:
        if not isinstance(e, dict) or sorted(set(e) - set(_ENTRY_KEYS)):
            raise ValueError("an entry of another shape")
        d = normalize(e.get("delta"))
        if not isinstance(e.get("n"), int) or e["n"] < 1 or e["n"] in seen or e.get("sig") != sig(d):
            raise ValueError("an entry whose number or identity does not hold")
        seen.add(e["n"])
        skills = e.get("skills")
        if not isinstance(skills, list) or not skills or not all(isinstance(s, str) and s for s in skills):
            raise ValueError("an entry with no skill")
        out["entries"].append({"n": e["n"], "sig": e["sig"], "delta": d, "skills": list(skills),
                               "at": str(e.get("at") or ""), "record_sha": str(e.get("record_sha") or ""),
                               "was": e.get("was") if isinstance(e.get("was"), str) else None,
                               "urgent": bool(e.get("urgent"))})
    for r in rejected:
        if not (isinstance(r, list) and len(r) == 3 and isinstance(r[0], str) and isinstance(r[1], str)
                and _DAY.match(r[1]) and isinstance(r[2], str)):
            raise ValueError("a rejected entry of another shape")
        out["rejected"].append([r[0], r[1], r[2]])
    out["next"] = max([nxt] + [e["n"] + 1 for e in out["entries"]])
    return out


def load(store, timeout=None):
    """The inbox of `store` (a ctx_store.Store). No file: empty. One that cannot be read or is not valid →
    cs.StoreError; never reset silently."""
    path = os.path.join(store.state_dir, FILE)
    if not os.path.lexists(path):
        return empty()
    try:
        raw = cs.read_text(path, timeout=timeout)
    except FileNotFoundError:
        return empty()
    except (OSError, UnicodeDecodeError, cs.StoreError) as e:
        raise _error("not readable", getattr(e, "strerror", None) or e)
    try:
        return _clean(json.loads(raw))
    except ValueError as e:
        raise _error("not valid", e)


def save(store, mem, today):
    """Write the inbox (canonical, atomic); rejections older than REJECT_DAYS are forgotten."""
    mem = dict(mem, rejected=[r for r in mem["rejected"] if _age(r[1], today) <= REJECT_DAYS])
    try:
        clean = _clean(mem)
    except ValueError as e:
        raise _error("not valid", e)
    cs.atomic_write(os.path.join(store.state_dir, FILE), json.dumps(clean, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
    cs.remove_stale_tmp(store.state_dir)
    return clean


def _age(day, today):
    import datetime
    try:
        return (datetime.date.fromisoformat(today[:10]) - datetime.date.fromisoformat(day[:10])).days
    except (TypeError, ValueError):
        return 0


# ------------------------------------------------------------------ one delta
def _text(d, key, need=False, one_line=True):
    v = d.get(key)
    if v is None:
        if need:
            raise ValueError("%s is required" % key)
        return None
    if not isinstance(v, str):
        raise ValueError("%s is not text" % key)
    v = v.strip()
    if need and not v:
        raise ValueError("%s is empty" % key)
    if one_line and len(v.splitlines()) > 1:            # every break splitlines() knows (U+2028 too), as the records do
        raise ValueError("%s takes one line" % key)
    return v or None


def normalize(raw):
    """One delta as a skill gave it → the canonical dict (schema context-delta/1), or ValueError."""
    if not isinstance(raw, dict):
        raise ValueError("a delta is a JSON object")
    unknown = sorted(set(raw) - set(_DELTA_KEYS) - {"schema"})
    if unknown:
        raise ValueError("unknown key(s) %s — the delta's keys are %s" % (", ".join(unknown), ", ".join(_DELTA_KEYS)))
    if raw.get("schema") not in (None, DELTA_SCHEMA):
        raise ValueError("a delta of schema %s" % DELTA_SCHEMA)
    op = str(raw.get("op") or "").strip().upper()
    if op not in OPS:
        raise ValueError("op is one of %s" % ", ".join(OPS))
    d = {"op": op, "record": _text(raw, "record", need=True)}
    if op == "UPDATE":
        d["field"] = _text(raw, "field", need=True)
        d["value"] = _text(raw, "value", need=True)
        if _MARKUP.search(d["field"]) or "*" in d["field"] or _MARKUP.search(d["value"]):
            raise ValueError("an UPDATE carries a field and a value, not a heading, a region marker or a rule")
    elif op == "ADD":
        d["text"] = _text(raw, "text", need=True)
        if _MARKUP.search(d["text"]) or d["text"].lstrip().startswith("#") or d["text"].strip() in ("---", "..."):
            raise ValueError("an ADD is one line of a record — not a heading, a region marker or a rule "
                             "(a new record comes from the configurator)")
        under = _text(raw, "under")
        if under is not None and not under.startswith("#"):
            raise ValueError("under is a heading line, e.g. «#### Metrics»")
        d["under"] = under
    for k in ("field", "value", "text", "under"):
        if k not in d and raw.get(k) is not None:
            raise ValueError("%s does not go with %s" % (k, op))
    d["reason"] = _text(raw, "reason", need=op != "NOOP")
    ev = _text(raw, "evidence", one_line=False)
    if ev is not None and len(ev) > EVIDENCE_MAX:
        raise ValueError("evidence is at most %d characters — a quote or a path, not a text" % EVIDENCE_MAX)
    d["evidence"] = ev
    src = raw.get("source")
    if not isinstance(src, dict) or sorted(set(src) - set(_SOURCE_KEYS)):
        raise ValueError("source is {kind, ref, at}")
    s = {"kind": _text(src, "kind", need=True), "ref": _text(src, "ref"), "at": _text(src, "at")}
    if s["at"] is not None and not _DAY.match(s["at"]):
        raise ValueError("source.at is a date, YYYY-MM-DD")
    d["source"] = s
    return d


def sig(d):
    key = [d.get("op"), d.get("record"), d.get("field"), d.get("value"), d.get("text"), d.get("under")]
    return hashlib.sha1(json.dumps(key, ensure_ascii=False).encode("utf-8")).hexdigest()


def texts(d):
    """Every text of a delta the store would keep — what the never-store filter reads."""
    s = d.get("source") or {}
    pair = ["%s: %s" % (d["field"], d["value"])] if d.get("field") and d.get("value") else []
    return [d.get(k) for k in ("record", "field", "value", "text", "under", "reason", "evidence")] + \
           [s.get("kind"), s.get("ref"), s.get("at")] + pair


def skill_name(raw):
    """The skill's own name: `grow-product-manager:one-on-one` → `one-on-one`; anything else → ValueError."""
    m = _SKILL.match((raw or "").strip())
    if not m:
        raise ValueError("--skill is a skill's name, e.g. focus-advisor")
    return m.group(1)


def urgent(d, rec):
    if d["op"] == "INVALIDATE" or (rec and rec["type"] == "team" and d["op"] != "NOOP"):
        return True
    return d["op"] == "UPDATE" and bool(rec) and d["field"] in URGENT.get(rec["type"], ())


def _kind(rec):
    if rec["type"] in ("profile", "product", "onboarding"):
        return rec["type"]
    return "judgment" if rec["type"] == "setting" and rec["title"].startswith("Judgment") else None


def apply_to(d, rec, today):
    """The record's body after the delta. cs.RegionError inside a provider's region; ValueError for a value outside
    its type or a header record."""
    body = rec["body"]
    if rec["type"] == "header":
        raise ValueError("the file header takes no delta")
    if d["op"] == "UPDATE":
        spec = (sc.load_fields().get(_kind(rec)) or {}).get(d["field"])
        err = sc.check_value(spec, d["value"]) if spec else None
        if err:
            raise ValueError("%s: %s" % (d["field"], err))
        return cs.field_set(body, d["field"], d["value"])
    if d["op"] == "ADD":
        return cs.append_line(body, d["text"], under=d["under"])
    if d["op"] == "INVALIDATE":
        return body if cs.has_status_region(body) else cs.set_status_region(body, today, d["reason"])
    return body


# ------------------------------------------------------------------ the inbox
ADDED, MERGED, ALREADY, NOOP, BEFORE, REFUSED, SECRET, BLOCK = "added", "merged", "already", "noop", \
    "rejected-before", "refused", "never-store", "provider-block"


def propose(mem, raws, skill, recs, today):
    """The deltas into `mem`, in place. Returns one {status, n?, record?, why?} per delta, in order. A refusal names
    what is wrong and never a value the filter caught."""
    by_id = {r["id"]: r for r in recs}
    rejected = {r[0] for r in mem["rejected"] if _age(r[1], today) <= REJECT_DAYS}
    out = []
    for raw in raws:
        try:
            d = normalize(raw)
        except ValueError as e:
            out.append({"status": REFUSED, "why": "дельта не така: %s" % e})
            continue
        try:
            cn.check(*texts(d))
        except cn.NeverStore as e:
            out.append({"status": SECRET, "why": str(e)})          # not even the record id: it may be what was caught
            continue
        if skill in PEOPLE_SKILLS:
            out.append({"status": REFUSED, "record": d["record"],
                        "why": "скіли People-контуру дельт не пропонують — їхній контекст у профілях людей"})
            continue
        rec = by_id.get(d["record"])
        if rec is None:
            out.append({"status": REFUSED, "record": d["record"], "why": "немає запису %s — ctx list" % d["record"]})
            continue
        if d["op"] == "NOOP":
            out.append({"status": NOOP, "record": d["record"]})
            continue
        try:
            body = apply_to(d, rec, today)
        except cs.RegionError:
            out.append({"status": BLOCK, "record": d["record"],
                        "why": "це блок ядра — пропозиції ядру прийдуть у v3.23.0"})
            continue
        except ValueError as e:
            out.append({"status": REFUSED, "record": d["record"], "why": str(e)})
            continue
        if body == rec["body"]:
            out.append({"status": ALREADY, "record": d["record"]})
            continue
        s = sig(d)
        if s in rejected:
            out.append({"status": BEFORE, "record": d["record"]})
            continue
        same = next((e for e in mem["entries"] if e["sig"] == s), None)
        if same:
            if skill not in same["skills"]:
                same["skills"].append(skill)
            same["delta"] = dict(same["delta"], evidence=d["evidence"] or same["delta"]["evidence"],
                                 source=d["source"], reason=d["reason"])
            same["at"] = today
            out.append({"status": MERGED, "n": same["n"], "record": d["record"], "urgent": same["urgent"]})
            continue
        n = mem["next"]
        mem["next"] = n + 1
        entry = {"n": n, "sig": s, "delta": d, "skills": [skill], "at": today, "record_sha": cs.sha_text(rec["body"]),
                 "was": cs.field_get(rec["body"], d["field"]) if d["op"] == "UPDATE" else None,
                 "urgent": urgent(d, rec)}
        mem["entries"].append(entry)
        out.append({"status": ADDED, "n": n, "record": d["record"], "urgent": entry["urgent"]})
    return out


def code(mem, recs):
    by_id = {r["id"]: cs.sha_text(r["body"]) for r in recs}
    shown = [[e["n"], e["sig"], by_id.get(e["delta"]["record"], ""), json.dumps(e["delta"], sort_keys=True)]
             for e in sorted(mem["entries"], key=lambda e: e["n"])]
    return hashlib.sha1(json.dumps(shown).encode("utf-8")).hexdigest()[:8]


def clashes(mem):
    """Numbers of the UPDATE entries that set one field of one record to different values."""
    groups = {}
    for e in mem["entries"]:
        d = e["delta"]
        if d["op"] == "UPDATE":
            groups.setdefault((d["record"], d["field"]), set()).add(d["value"])
    return {e["n"] for e in mem["entries"] if e["delta"]["op"] == "UPDATE"
            and len(groups[(e["delta"]["record"], e["delta"]["field"])]) > 1}


def moved(e, recs):
    """True when the record changed since the delta was proposed."""
    rec = next((r for r in recs if r["id"] == e["delta"]["record"]), None)
    return rec is None or cs.sha_text(rec["body"]) != e["record_sha"]


def what(d):
    if d["op"] == "UPDATE":
        return "%s → %s" % (d["field"], d["value"])
    if d["op"] == "ADD":
        return "+ «%s»%s" % (d["text"], (" під %s" % d["under"]) if d["under"] else "")
    return "неактуальний: %s" % d["reason"]


def render(mem, recs, today):
    """The list `ctx inbox list` prints, newest last; marks: терміново · ⚠ two values for one field · ! the record
    changed since."""
    clash = clashes(mem)
    lines = []
    for e in sorted(mem["entries"], key=lambda e: e["n"]):
        d = e["delta"]
        marks = [m for m, on in (("терміново", e["urgent"]), ("⚠", e["n"] in clash), ("!", moved(e, recs))) if on]
        src = d["source"]["kind"] + ((" " + d["source"]["ref"]) if d["source"]["ref"] else "")
        age = _age(e["at"], today)
        lines.append("%d. %s %s · %s%s · %s · %s · %s%s" % (
            e["n"], d["op"], d["record"], what(d), (" · «%s»" % d["evidence"]) if d["evidence"] else "", src,
            ", ".join(e["skills"]), "сьогодні" if age <= 0 else "%d дн" % age,
            (" · " + " ".join(marks)) if marks else ""))
    return lines


def pick(mem, which):
    """`all` or numbers (`3,5` / `3 5`) → the entries, in number order; an unknown number → ValueError."""
    entries = sorted(mem["entries"], key=lambda e: e["n"])
    w = " ".join(which).strip() if isinstance(which, (list, tuple)) else str(which).strip()
    if w == "all":
        return entries
    try:
        nums = [int(x) for x in re.split(r"[,\s]+", w) if x]
    except ValueError:
        raise ValueError("номери записів скриньки або all")
    if not nums:
        raise ValueError("номери записів скриньки або all")
    by_n = {e["n"]: e for e in entries}
    missing = [n for n in nums if n not in by_n]
    if missing:
        raise ValueError("у скриньці немає №%s — ctx inbox list" % ", ".join(map(str, missing)))
    return [by_n[n] for n in sorted(set(nums))]


def take(mem, entries):
    gone = {e["n"] for e in entries}
    mem["entries"] = [e for e in mem["entries"] if e["n"] not in gone]


def reject(mem, entries, day, why):
    take(mem, entries)
    have = {r[0] for r in mem["rejected"]}
    for e in entries:
        if e["sig"] not in have:
            mem["rejected"].append([e["sig"], day, why or ""])


def load_path(path):
    """An inbox file at `path` (a snapshot's state/inbox.json); None when it is not there or does not read."""
    try:
        with open(path, encoding="utf-8") as f:
            return _clean(json.load(f))
    except (OSError, ValueError):
        return None


def union(mems):
    """One inbox of every entry the given inboxes hold (the newest copy of an identity wins), for merge_back."""
    out = empty()
    by_sig = {}
    for m in mems:
        if not m:
            continue
        out["next"] = max(out["next"], m["next"])
        for e in m["entries"]:
            by_sig[e["sig"]] = e
    out["entries"] = sorted(by_sig.values(), key=lambda e: e["n"])
    return out


def merge_back(mem, before, sigs):
    """After `ctx undo` restored `mem`: the entries of `before` (the inbox just before the undo) whose identity is in
    `sigs` (proposed after the undone change) come back, under their numbers when free. Returns how many."""
    have = {e["sig"] for e in mem["entries"]} | {r[0] for r in mem["rejected"]}
    nums = {e["n"] for e in mem["entries"]}
    back = 0
    mem["next"] = max(mem["next"], before["next"])
    for e in sorted(before["entries"], key=lambda e: e["n"]):
        if e["sig"] in sigs and e["sig"] not in have:
            if e["n"] in nums:
                e = dict(e, n=mem["next"])
                mem["next"] += 1
            nums.add(e["n"])
            mem["entries"].append(e)
            back += 1
    return back


def counts(mem, today):
    return {"entries": len(mem["entries"]), "urgent": sum(1 for e in mem["entries"] if e["urgent"]),
            "old": sum(1 for e in mem["entries"] if _age(e["at"], today) > OLD_DAYS)}
