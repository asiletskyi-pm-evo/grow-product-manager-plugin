#!/usr/bin/env python3
"""Grow PM — the slots of one entity, assembled from its cards (since v3.18.1).

A person's role, a team's members, a mission's teams: the answer is put together from every card of one entity
(ctx_entity: your note, a core's card, a card a local index of yours holds) and from what other cards say of it — a
person whose winning `team` names the team is one of its members. Each piece keeps its origin: whose it is, the card it
sits in, its date. The cascade is the one of the records (ctx_resolve.resolve): yours, then the repositories by rank,
then a local index's card, then the derived; `ctx slot prefer|decide` do not reach a card's slot (plan C6a: the memory
keeps one decision per slot, not per entity). A list is the union of its candidates, one item per entity (plan C4, C7).

- ITEM_KIND, DERIVED            the kind of entity a slot's items (or value) name, and the slot of another entity a list
                                slot is derived from (team.members ← person.team, mission.teams ↔ team.missions)
- item_kind, item_entity        what a slot's items are, and the entity one item or value names: its first link, else
                                its e-mail, else its name — a file name, title, slug or alias of exactly one card of the
                                kind (a namesake is no entity: the item stays text)
- split_items                   the items of a section: a list's items, a table's rows (not its header nor its rule)
- candidates                    the candidates of one slot of one entity: a card's field, else (not on a person's card,
                                nor a sensitive note) its section of that name; and the derived ones
- join_items                    a list's candidates as items, one per entity, every origin and every row kept
- slots_of                      {slot: answer} of an entity — a value with its origin and its «також», or a list of items

Reads only: the index (ctx_index.Index.note for a card's sections) and the registry ctx_entity.load built — nothing is
written. Stdlib only.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx_common as cc  # noqa: E402
import ctx_entity as ce  # noqa: E402
import ctx_index as ci  # noqa: E402
import ctx_resolve as rv  # noqa: E402
import ctx_slots as sl  # noqa: E402

N = cc.N
ITEM_KIND = {"team.members": "person", "team.missions": "mission", "team.parent": "team", "mission.teams": "team",
             "person.team": "team", "module.owner": "person", "metric.owner": "person"}
DERIVED = {"team.members": "person.team", "mission.teams": "team.missions", "team.missions": "mission.teams"}
                                    # a list slot of E ← the slot of another entity whose winning value (or items) names E
LEVEL_RANK = {"mine": 0, "repo": 1, "local": 2, "derived": 3}
_SEPARATORS = re.compile(r"\s+[—–-]\s+|:|,|\(")
_TABLE_RULE = re.compile(r"^\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")
_EMAIL = re.compile(r"[^@\s<>()\[\],;:\"|`*]+@[^@\s<>()\[\],;:\"|`*]+\.[A-Za-z]{2,}")


def item_kind(slot):
    """The kind of entity the items (or the value) of `slot` name, or None (a role, an e-mail, a Jira project)."""
    return ITEM_KIND.get(slot)


def _name_part(text):
    """The name in an item that has no link and no e-mail (plan C4a): a table row's first cell, else the text before the
    first separator (` — `, ` – `, ` - `, `:`, `,`, `(`); no markup."""
    t = N(text or "").strip()
    if t.startswith("|"):
        cells = [c.strip() for c in t.replace("\\|", "\x00").strip("|").split("|")]
        t = cells[0].replace("\x00", "|") if cells else ""
    else:
        t = _SEPARATORS.split(t, 1)[0]
    return t.strip(" *_`").strip()


def item_entity(reg, text, kind):
    """(entity id, how) of the entity of `kind` one item or value names: its first link that lands on a card of that
    kind ("link"), else its e-mail ("email"), else its name when exactly one card of the kind carries it ("name") —
    else (None, "text"). `kind` None: (None, "text")."""
    if not kind:
        return None, "text"
    t = N(text or "")
    for m in ci._WIKI.finditer(t):
        hit = reg.resolver.resolve(m.group(1).replace("\\|", "|"))
        for p in ([hit] if isinstance(hit, str) else hit or []):
            e = reg.of(p)
            if e and e["kind"] == kind:
                return e["id"], "link"
    m = _EMAIL.search(t)
    if m:
        found, how = reg.find(m.group(0).lower(), kind)
        if how == "email" and len(found) == 1:
            return found[0]["id"], "email"
    name = _name_part(ci._WIKI.sub(lambda m_: ce.Resolver.clean(m_.group(1)).rsplit("/", 1)[-1], t))
    if name:
        found, how = reg.find(name, kind)
        if how == "name" and len(found) == 1:
            return found[0]["id"], "name"
    return None, "text"


def split_items(text):
    """The items of a section's text: each list item (its marker gone), each row of a table but its header and its rule.
    Other lines are no item."""
    lines = (text or "").split("\n")
    out = []
    for k, line in enumerate(lines):
        s = line.strip()
        if ci._LIST_ITEM.match(line):
            out.append(re.sub(r"^\s*(?:>\s*)*(?:[-*+]|\d+[.)])\s+", "", line).strip())
        elif s.startswith("|") and not _TABLE_RULE.match(s):
            nxt = lines[k + 1].strip() if k + 1 < len(lines) else ""
            if not _TABLE_RULE.match(nxt):        # the header row is the one right above the rule
                out.append(s)
    return [x for x in out if x]


def _heading_slot(cat, kind, heading):
    """The slot a card of `kind` answers by a section heading: a name, or a name followed by a qualifier (`Місії
    (матриця …)`), compared without regard to case — the last part of the index's heading path."""
    last = (heading or "").split(" › ")[-1].strip().lstrip("#").strip()
    if not last:
        return None
    hit = sl.card_slot_for(cat, kind, last)
    if hit:
        return hit
    low = last.casefold()
    for slot in sl.card_slots(cat, kind):
        for n in sl._card_names(sl.card_slot_info(cat, slot)):
            n = n.casefold()
            if low.startswith(n) and len(low) > len(n) and not (low[len(n)].isalnum() or low[len(n)] == "_"):
                return slot
    return None


class _Slots:
    """One assembly over a registry: the ranks of the registrations and the candidates found, each once."""

    def __init__(self, reg, idx, cat, sctx):
        self.reg, self.idx, self.cat = reg, idx, cat
        self.ranks = {r.get("id"): rv._rank(r) for r in (sctx or {}).get("repos") or ()}
        self._own, self._derived, self._values, self._items = {}, {}, {}, {}

    def entity(self, text, kind):
        """item_entity, each (text, kind) once: hundreds of people name a few dozen teams."""
        key = (text, kind)
        if key not in self._items:
            self._items[key] = item_entity(self.reg, text, kind)
        return self._items[key]

    def level(self, card):
        if card["source"] == "own":
            return "mine", None
        if card.get("origin") == "local":
            return "local", None
        return "repo", self.ranks.get(card["source"])

    def own(self, ent, slot):
        """The candidates of `slot` the entity's own cards give (no derived one)."""
        key = (ent["id"], slot)
        if key in self._own:
            return self._own[key]
        info = sl.card_slot_info(self.cat, slot) or {}
        out = []
        for c in ent["cards"]:
            if not c.get("home", True) or c["kind"] != info.get("record"):
                continue
            fields = c.get("fields")
            if fields is None:                          # not read yet (a card iCloud evicted since the upgrade):
                fields = {"person.role": c.get("role"), "person.team": c.get("team"),   # the identity columns say it
                          "person.email": (c.get("emails") or [None])[0]} if c["kind"] == "person" else {}
            v = fields.get(slot)
            items = (v if isinstance(v, list) else [v]) if v else None
            if not items and c["kind"] != "person" and not c.get("sensitive") and c.get("origin") == "index":
                got = self.idx.note(c["path"])           # a person's card is a profile: its body is never read (C3)
                items = []
                for heading, text in (got[1] if got else ()):    # a list: every section of the slot's names (a table
                    if _heading_slot(self.cat, c["kind"], heading) != slot:     # of roles under «Люди», the people
                        continue                                                # under «Склад команди»); a value: the first
                    if info.get("kind") == "list":
                        items += split_items(text)
                    else:
                        items = [next((x.strip() for x in text.split("\n") if x.strip()), "")]
                        break
            items = [N(str(x)).strip() for x in items or () if N(str(x)).strip()]
            if not items:
                continue
            level, rank = self.level(c)
            out.append({"slot": slot, "level": level, "source": "mine" if level == "mine" else c["source"],
                        "card_source": c["source"], "rank": rank, "placed": True, "path": c["path"],
                        "date": c.get("date") or "", "text": "\n".join(items), "items": items})
        self._own[key] = out
        return out

    def winner(self, ent, slot):
        """The candidate that wins a value slot of the entity by the cascade (its own cards only), or None."""
        key = (ent["id"], slot)
        if key not in self._values:
            r = rv.resolve(slot, self.cat, self.own(ent, slot), None)
            self._values[key] = r["shown"][0] if r["shown"] else None
        return self._values[key]

    def derived(self, ent, slot):
        """The derived candidates of a list slot of `ent` (plan C5, R9): one per card of another entity whose winning
        value — or whose list — names `ent`."""
        src = DERIVED.get(slot)
        key = (ent["id"], slot)
        if not src or key in self._derived:
            return self._derived.get(key, [])
        info = sl.card_slot_info(self.cat, src) or {}
        out = []
        for other in self.reg.entities:
            if other["kind"] != info.get("record") or other["id"] == ent["id"]:
                continue
            if info.get("kind") == "value":
                w = self.winner(other, src)
                naming = [w] if w and self.entity(w["text"], ent["kind"])[0] == ent["id"] else []
            else:
                naming = [c for c in self.own(other, src)
                          if any(self.entity(x, ent["kind"])[0] == ent["id"] for x in c["items"])]
            for c in naming:
                out.append({"slot": slot, "level": "derived", "source": c["path"], "card_source": c["card_source"],
                            "rank": None, "placed": True, "path": c["path"], "date": c["date"],
                            "text": "[[%s]]" % other["id"], "items": ["[[%s]]" % other["id"]]})
        self._derived[key] = out
        return out


def candidates(reg, idx, ent, slot, cat, sctx, _s=None):
    """Every candidate of `slot` of the entity `ent`: its cards' (a field, else a section of that name) and the derived
    ones — dicts {slot, level, source, card_source, rank, placed, path, date, text, items}."""
    s = _s or _Slots(reg, idx, cat, sctx)
    return s.own(ent, slot) + s.derived(ent, slot)


def _origin(c, how=None):
    d = {"level": c["level"], "source": c["card_source"], "path": c["path"], "date": c["date"]}
    if how:
        d["how"] = how
    return d


def join_items(cands, reg, kind, strict, entity_of=None):
    """The items of a list's candidates, one per entity (plan C4, C7): {entity (its id, or None), label, origins:
    [{level, source, path, date, how}] — one per candidate that names it —, rows: [{level, source, text}] — the item's own
    line in each card that is not derived —, derived_only}. `strict` (a card's list): an item that names no entity of
    `kind` is no item; else it stays a text item, never joined with another by its words. Items with a row of yours
    first, then by the strongest origin, then by label. `entity_of(text, kind)` — item_entity by default."""
    entity_of = entity_of or (lambda text, k: item_entity(reg, text, k))
    groups, order = {}, []
    for c in cands:
        seen = set()
        for text in c["items"]:
            eid, how = entity_of(text, kind)
            if eid is None and strict and kind:
                continue
            key = eid or ("text", " ".join(text.split()).casefold())
            if key in seen:
                continue
            seen.add(key)
            if key not in groups:
                e = reg.of(eid) if eid else None            # an entity's id is the path of its first card
                groups[key] = {"entity": eid, "label": e["label"] if e else text, "origins": [], "rows": []}
                order.append(key)
            g = groups[key]
            g["origins"].append(_origin(c, how))
            if c["level"] != "derived":
                g["rows"].append({"level": c["level"], "source": c["card_source"], "text": text})
    items = [groups[k] for k in order]
    for g in items:
        g["derived_only"] = all(o["level"] == "derived" for o in g["origins"])
    items.sort(key=lambda g: (0 if any(o["level"] == "mine" for o in g["origins"]) else 1,
                              min(LEVEL_RANK.get(o["level"], 9) for o in g["origins"]), g["label"].casefold()))
    return items


def _value(reg, slot, c):
    """{value, entity?} of a value candidate: a link or a name of an entity of the slot's kind → its label and id."""
    eid, _ = item_entity(reg, c["text"], item_kind(slot))
    if eid:
        e = reg.of(eid)
        return {"value": e["label"] if e else c["text"], "entity": eid}
    return {"value": ce._plain(c["text"])}


def slots_of(reg, idx, ent, cat, sctx, people=False, only=None):
    """{slot: answer} of the slots the cards of `ent` answer (ctx_slots.card_slots; `only` keeps those asked for), a slot
    with no candidate left out. A value: {slot, kind, value, entity?, origin, also: [{value, entity?, level, source, path,
    date}], diverges: [sources], why}; a list: {slot, kind, items (join_items), count, why}. Outside the People contour
    (`people` False) a person's slots are its identity alone — role, team, e-mail — which is all the catalogue gives a
    person; nothing of a profile's body or judgement is ever read."""
    if not ent:
        return {}
    s = _Slots(reg, idx, cat, sctx)
    out = {}
    for slot in sl.card_slots(cat, ent["kind"]):
        if only and slot not in only:
            continue
        info = sl.card_slot_info(cat, slot)
        cands = candidates(reg, idx, ent, slot, cat, sctx, _s=s)
        if not cands:
            continue
        if info["kind"] == "list":
            items = join_items(cands, reg, item_kind(slot), strict=True, entity_of=s.entity)
            if items:
                out[slot] = {"slot": slot, "kind": "list", "items": items, "count": len(items), "why": rv.WHY_JOINED}
            continue
        r = rv.resolve(slot, cat, cands, None)
        if not r["shown"]:
            continue
        win = r["shown"][0]
        ans = {"slot": slot, "kind": "value", "origin": _origin(win), "why": r["why"],
               "diverges": [c["card_source"] for c in r["shown"]] if r["diverges"] else []}
        ans.update(_value(reg, slot, win))
        ans["also"] = [dict(_value(reg, slot, c), **_origin(c)) for c in list(r["shown"][1:]) + list(r["also"])]
        out[slot] = ans
    return out
