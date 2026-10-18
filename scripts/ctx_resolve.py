#!/usr/bin/env python3
"""Grow PM — the resolver: what may answer a slot, and from where (since v3.15.0).

A slot (scripts/ctx_slots.py, references/context-slots.yaml) is answered by candidates of three kinds (spec §4):

- your text   in the records of the slot's kind — the active product, the teams a skill reads, the organisation, the
              profile — outside the managed regions, under any of the slot's catalogue names, or a heading you mapped
              to it (`ctx slot map`); a heading you mapped to another slot is not this slot's
- a bound block   from any record, when a binding (ctx_slots.bindings_of: yours, the `slot=` of the block's base, the
              plugin's own for the `team` block) ties it to the slot; where it belongs is decided as spec §4.4 says,
              and what text it gives as §4.5 says
- a block found by name   an unbound block of the same product, team (or profile) record, read as v3.14.1 read it
              (ctx_read._lookup: the first block that has a name) — only when your text in that record has nothing

- candidates    every candidate of one slot, each a dict that says whose it is, where, which version, when it was
                checked, whether you edited it, whether it is a core rule, and whether it can be placed at all

Reads only: no lock, no network, nothing written. Semantics: references/context-protocol.md. Stdlib only.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx_blocks as cb  # noqa: E402
import ctx_common as cc  # noqa: E402
import ctx_read as cr  # noqa: E402
import ctx_repos as crp  # noqa: E402
import ctx_schema as sc  # noqa: E402
import ctx_slots as sl  # noqa: E402
import ctx_store as cs  # noqa: E402

BY_NAME = "name"                      # the `how` of an unbound block found by a heading's name, as v3.14.1 found it
NAME_PLACES = ("product", "team", "profile")   # the records whose unbound blocks answer by name (ctx_read._lookup looked there)


def _rank(reg):
    r = reg.get("rank") if reg else None
    return r if isinstance(r, int) and not isinstance(r, bool) else None


class _Repos:
    """The registrations by namespace, and the block state of each repository, read once, never written. A state or a
    base that cannot be read is no state (ctx_slots.bindings_of names it)."""

    def __init__(self, store, repos):
        self.store = store
        self.by_ns = {}
        for r in repos or ():
            self.by_ns.setdefault(r.get("namespace") or r["id"], r)
        self._states = {}

    def reg(self, ns):
        return self.by_ns.get(ns)

    def entry(self, ns, bid):
        reg = self.by_ns.get(ns)
        if reg is None or not bid:
            return {}
        if reg["id"] not in self._states:
            try:
                self._states[reg["id"]] = cb.load_state(self.store, reg["id"])["blocks"]
            except (cs.StoreError, OSError):
                self._states[reg["id"]] = {}
        return self._states[reg["id"]].get(bid) or {}

    def base(self, ns, bid):
        sha = self.entry(ns, bid).get("base_sha")
        if not sha:
            return None
        try:
            return cb.get_base(self.store, self.by_ns[ns]["id"], sha)
        except (cs.StoreError, OSError):
            return None

    def block(self, slot, rec, ns, bid, v, region, text, how, placed, place):
        """A block's candidate: `region` is the whole region text (markers included) when it is sound, else None."""
        reg, entry = self.reg(ns), self.entry(ns, bid)
        rule = cb.is_rule(self.base(ns, bid))
        known = [h for h in [entry.get("base_sha")] + list(entry.get("bases") or []) if h]
        version = v or entry.get("v")
        checked = entry.get("checked")
        return {"slot": slot, "source": reg["id"] if reg else ns, "level": "rule" if rule and how != BY_NAME else "repo",
                "record": rec["id"], "block": bid, "ns": ns, "version": str(version) if version else None,
                "checked": checked[:10] if isinstance(checked, str) and checked else None,
                "edited": bool(known and region is not None and cs.sha_text(cb.norm(region)) not in known),
                "rule": rule, "how": how, "heading": _heading(text), "text": text, "rank": _rank(reg),
                "placed": placed, "place": place}


def _heading(text):
    """The heading text of the first line of `text` that is not blank, or the field's name when it is a field line."""
    for core in (text or "").splitlines():
        if not core.strip():
            continue
        if cs._level(core):
            return cs._heading_text(core)
        m = cs.FIELD_RE.match(core)
        return m.group("name").strip() if m else None
    return None


def _squash(s):
    return " ".join(str(s).split())


def _heading_answers(core, name, loose):
    """Does the heading line `core` answer `name` — the text, or its start followed by a non-word character
    (cs.heading_matches)? `loose` (a name you mapped) also ignores the spacing inside both."""
    if not loose:
        return cs.heading_matches(core, name)
    lvl = cs._level(core)
    return bool(lvl) and cs.heading_matches("#" * lvl + " " + _squash(cs._heading_text(core) or ""), _squash(name))


def _field_answers(field, name, loose):
    return sl._norm(field) == sl._norm(name) if loose else field.strip() == name


def _occurrences(lines, cores, name, field, loose):
    """[(first line, end line, is a field line, text)] of `name` in a body, in the order ctx_read._field_text tries them
    (`field`: the field lines named `name` first) and then every subsection whose heading answers it, each to the next
    heading of the same or a higher level (ctx_read._subsection) — the first of them is what those two return."""
    out = []
    if field:
        for k, core in enumerate(cores):
            m = cs.FIELD_RE.match(core)
            if m and _field_answers(m.group("name"), name, loose):
                out.append((k, k + 1, True, core + "\n"))
    for k, core in enumerate(cores):
        if _heading_answers(core, name, loose):
            lvl = cs._level(core)
            end = next((j for j in range(k + 1, len(cores)) if 0 < cs._level(cores[j]) <= lvl), len(cores))
            out.append((k, end, False, "".join(lines[k:end]).rstrip("\n") + "\n"))
    return out


def _answers_any(core, is_field, names):
    if is_field:
        m = cs.FIELD_RE.match(core)
        return bool(m) and any(_field_answers(m.group("name"), n, True) for n in names)
    return any(_heading_answers(core, n, True) for n in names)


def _own(slot, rec, kind, names, aliases, place):
    """Your candidates of `slot` in `rec`: outside the managed regions, the first place each catalogue name answers (a
    field line for a value or a list, else the subsection), then each heading you mapped to the slot in this record.
    A heading you mapped to another slot in this record does not answer a catalogue name (unless you mapped it to this
    slot too); a text already taken — the same heading found twice, or one inside another — is one candidate."""
    body = cc.strip_managed_regions(rec.get("body") or "")
    lines = body.splitlines(keepends=True)
    cores = [line.rstrip("\r\n") for line in lines]
    mine = [a["heading"] for a in aliases if a.get("record") == rec["id"] and a.get("slot") == slot]
    other = [a["heading"] for a in aliases if a.get("record") == rec["id"] and a.get("slot") != slot]
    field = kind != "text"
    taken, out = [], []
    for name, loose in [(n, False) for n in names] + [(h, True) for h in mine]:
        for start, end, is_field, text in _occurrences(lines, cores, name, field, loose):
            if not loose and _answers_any(cores[start], is_field, other) and not _answers_any(cores[start], is_field, mine):
                continue
            if not any(start < e and s < end for s, e in taken):
                taken.append((start, end))
                out.append({"slot": slot, "source": "mine", "level": "mine", "record": rec["id"], "block": None, "ns": None,
                            "version": None, "checked": sc.verified_of(rec, None), "edited": False, "rule": False,
                            "how": None, "heading": _heading(text), "text": text, "rank": None, "placed": True,
                            "place": place})
            break
    return out


def _inner(region):
    """A region's text without its two markers, ending in one newline."""
    return cb._detach(region).strip("\n") + "\n"


def _first(find, body, names):
    for n in names:
        t = find(body, n)
        if t is not None:
            return t
    return None


def _bound_text(inner, sub, kind, names, several):
    """The text a bound block gives its slot (spec §4.5): the subsection `sub` the binding names; for a block bound to
    several slots, the part that answers the slot's names; else the whole block. A value slot takes the field line
    (ctx_read._field_text) inside that text. None when the block has no such part: then it is no candidate."""
    find = cr._subsection if kind == "text" else cr._field_text
    if sub:
        part = cr._subsection(inner, sub)
        if part is not None and kind == "value":
            part = _first(cr._field_text, part, names)
    elif kind == "value" or several:
        part = _first(find, inner, names)
    else:
        part = inner
    return part if part and part.strip() else None


def _placement(rkind, rec, binding, prod, team_ids, reg):
    """(placed, place) of a bound block in `rec` for a slot of record kind `rkind` (spec §4.4) — or None when the block
    answers for another product or team, and so is no candidate here. A block in a product or team record belongs to
    it; one elsewhere fills a product slot for the products its repository serves (crp.serves_product: none named — all;
    a registration not read — all) and a team slot for the team a binding names, else for the one team there is; with
    several teams and none named it is unplaced (placed False, place None). A binding that names a team places the block
    with that team wherever it sits. An org or profile slot takes a bound block from anywhere (place None)."""
    host = rec.get("type")
    if rkind == "product":
        if host == "product":
            return (True, prod["id"]) if prod is not None and rec["id"] == prod["id"] else None
        if prod is None:
            return (True, None) if reg is None or not reg.get("products") else None
        return (True, prod["id"]) if reg is None or crp.serves_product(reg, prod) else None
    if rkind == "team":
        team = binding.get("team")
        if team:
            return (True, team) if team in team_ids else None
        if host == "team":
            return (True, rec["id"]) if rec["id"] in team_ids else None
        if host == "product" and prod is not None and rec["id"] != prod["id"]:
            return None
        return (True, team_ids[0]) if len(team_ids) == 1 else (False, None)
    return (True, None)


def candidates(slot, cat, records, prod, teams, repos, mem, store, bindings):
    """Every candidate of `slot` (an id of the catalogue `cat`; an unknown one has none), as a list of dicts:

      slot, source ("mine" or the repository id: the registration whose namespace the block carries, else the namespace),
      level ("rule": a bound block whose base says policy=rule · "mine" · "repo"), record (the id of the record the
      text sits in), block and ns (None for your text), version (the marker's v=, else the state's), checked (the day the
      store last checked the block — for your text, the record's `verified` date), edited (the region differs from every
      base the state keeps of it; a block with no base is no edit), rule (cb.is_rule of its base), how ("memory",
      "marker", "plugin", "name" — found by name without a binding — or None for your text), heading (of the text, or
      the field's name), text, rank (the registration's; None when it was not read), placed (False: a block outside
      a team record that cannot be given to one team — the skill does not get it, explain shows it), place (the id of
      the product or team record the candidate answers for; None for an org or profile slot and when not placed).

    `records` are the live records (ctx_read._live_view), `prod` the active product record (or None), `teams` the team
    records the skill reads, `repos` the registrations (crp.load_repos), `mem` the slots memory (its `aliases`; None —
    an empty memory), `bindings` the first item of ctx_slots.bindings_of. A block that is not one sound region
    (cb.find_regions: repeated, nested, broken) is no bound candidate; a block any binding names is never found by name.
    In order: your text, place by place; the bound blocks, in record order; the blocks found by name. Reads only."""
    info = sl.slot_info(cat, slot)
    if info is None:
        return []
    kind, rkind, names = info.get("kind"), info.get("record"), sl._names(info)
    aliases = (mem or {}).get("aliases") or []
    bindings = bindings or {}
    team_ids = [t["id"] for t in teams or ()]
    regs = _Repos(store, repos)

    def place_of(rec):
        return rec["id"] if rkind in ("product", "team") else None

    if rkind == "product":
        places = [prod] if prod is not None else []
    elif rkind == "team":
        places = list(teams or ())
    else:
        places = [r for r in records if r.get("type") == rkind]
    out, own_in = [], set()
    for rec in places:
        found = _own(slot, rec, kind, names, aliases, place_of(rec))
        out += found
        if found:
            own_in.add(rec["id"])

    sound = {}

    def region_of(ns, bid, host):
        if ns not in sound:
            sound[ns] = cb.find_regions(records, ns)[0]
        reg = sound[ns].get(bid)
        return reg["text"] if reg and reg["host"] == host else None

    seen = set()
    for rec in records:
        for ns, bid, v, _, _ in cr._blocks(rec.get("body") or ""):
            tied = bindings.get((ns, bid)) if bid else None
            ours = [b for b in tied or () if b.get("slot") == slot]
            region = region_of(ns, bid, rec["id"]) if ours else None
            if region is None:
                continue                    # unbound, bound elsewhere, or broken / repeated: find_regions left it out
            several = len({b.get("slot") for b in tied}) > 1
            for b in ours:
                text = _bound_text(_inner(region), b.get("sub"), kind, names, several)
                where = _placement(rkind, rec, b, prod, team_ids, regs.reg(ns)) if text is not None else None
                if where is None or (ns, bid, text) in seen:
                    continue
                seen.add((ns, bid, text))
                out.append(regs.block(slot, rec, ns, bid, v, region, text, b.get("how"), where[0], where[1]))

    if rkind in NAME_PLACES:
        find = cr._subsection if kind == "text" else cr._field_text
        for rec in places:
            if rec["id"] in own_in:
                continue
            hit = None
            for ns, bid, v, _, inner in cr._blocks(rec.get("body") or ""):
                if bid and bindings.get((ns, bid)):
                    continue
                text = _first(find, inner, names)
                if text is not None:
                    hit = regs.block(slot, rec, ns, bid, v, region_of(ns, bid, rec["id"]) if bid else None, text,
                                     BY_NAME, True, place_of(rec))
                    break
            if hit:
                out.append(hit)
    return out
