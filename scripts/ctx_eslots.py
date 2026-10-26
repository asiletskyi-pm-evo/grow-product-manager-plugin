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
LEVEL_RANK = {"mine": 0, "rule": 0, "repo": 1, "local": 2, "derived": 3}
PERSON_IDENTITY = ("person.role", "person.team", "person.email")   # all a person's slots may give outside People
_MARKER = re.compile(r"^\s*(?:>\s*)*(?:[-*+]|\d+[.)])\s+")
_SEPARATORS = re.compile(r"\s+[—–-]\s+|:|,|\(")
_TABLE_RULE = re.compile(r"^\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?\s*$|^\|\s*:?-+:?\s*\|\s*$")
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
        ids = {e["id"] for e in (reg.of(p) for p in ([hit] if isinstance(hit, str) else hit or [])) if e and e["kind"] == kind}
        if len(ids) == 1:                     # a link several people's notes answer names nobody (a namesake is no join)
            return ids.pop(), "link"
    m = _EMAIL.search(t)
    if m:
        found, how = reg.find(m.group(0).lower(), kind)
        if how == "email" and len(found) == 1:
            return found[0]["id"], "email"
    name = _name_part(ci._WIKI.sub(lambda m_: ce.Resolver.clean(m_.group(1)).rsplit("/", 1)[-1], _MARKER.sub("", t)))
    if name:
        found, how = reg.find(name, kind)
        if how == "name" and len(found) == 1:
            return found[0]["id"], "name"
    return None, "text"


def split_items(text):
    """The items of a section's text: each list item (its marker gone), each row of a table but its header and its rule.
    Other lines are no item."""
    lines = (text or "").split("\n")
    out, table = [], False
    for k, line in enumerate(lines):
        s = line.strip()
        nxt = lines[k + 1].strip() if k + 1 < len(lines) else ""
        if not s:
            table = False
        elif ci._LIST_ITEM.match(line) and not table:
            out.append(_MARKER.sub("", line).strip())
        elif "|" in s and _TABLE_RULE.match(nxt):
            table = True                          # the header row: the one right above the rule — no item
        elif _TABLE_RULE.match(s):
            continue
        elif table or s.startswith("|"):
            out.append(s)
    return [x for x in out if x]


def _part_slot(cat, kind, part):
    """(slot, exact) a card of `kind` answers by one heading: its name exactly, or a name followed by a qualifier in
    brackets or after a colon (`Місії (матриця …)`, `Owner: 2025`) — never a hyphen (`Команди-партнери`) nor a word
    (`Owner history`)."""
    part = part.strip().lstrip("#").strip()
    if not part:
        return None, False
    hit = sl.card_slot_for(cat, kind, part)
    if hit:
        return hit, True
    low = part.casefold()
    for slot in sl.card_slots(cat, kind):
        for n in sl._card_names(sl.card_slot_info(cat, slot)):
            n = n.casefold()
            if low.startswith(n) and re.match(r"\s*[(:]", low[len(n):]):
                return slot, False
    return None, False


def _heading_slot(cat, kind, heading):
    """(slot, exact) a section answers by its heading path (`H1 › H2 › H3`, the index's): the deepest part that names a
    slot — so `Склад команди › Backend` is a part of the members — compared without regard to case."""
    for part in reversed((heading or "").split(" › ")):
        hit = _part_slot(cat, kind, part)
        if hit[0]:
            return hit
    return None, False


class _Slots:
    """One assembly over a registry: the ranks of the registrations and the candidates found, each once."""

    def __init__(self, reg, idx, cat, sctx, people=False):
        self.reg, self.idx, self.cat, self.people = reg, idx, cat, people
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
            private = bool(c.get("sensitive")) and c["kind"] != "person" and not self.people
            if private and info.get("kind") != "list":
                continue                    # a sensitive team's or mission's value: never outside People (review I1)
            fields = c.get("fields")
            if fields is None:                          # not read yet (a card iCloud evicted since the upgrade):
                fields = {"person.role": c.get("role"), "person.team": c.get("team"),   # the identity columns say it
                          "person.email": (c.get("emails") or [None])[0]} if c["kind"] == "person" else {}
            v = fields.get(slot)
            items = list(v if isinstance(v, list) else [v]) if v else []
            listing = info.get("kind") == "list"
            if (listing or not items) and c["kind"] != "person" and not c.get("sensitive") and c.get("origin") == "index":
                got = self.idx.note(c["path"])           # a person's card is a profile: its body is never read (C3)
                exact, loose = [], []                    # a list: the field's items AND every section's (a count in
                for heading, text in (got[1] if got else ()):     # `members: 12` hides no list); the strict join keeps
                    hit, is_exact = _heading_slot(self.cat, c["kind"], heading)   # what names an entity
                    if hit != slot:
                        continue
                    if listing:
                        items += split_items(text)
                    else:                                # a value: an exact heading before a qualified one
                        first = next((_MARKER.sub("", x).strip() for x in text.split("\n") if x.strip()), "")
                        (exact if is_exact else loose).append(first)
                if not listing and not items:
                    items = (exact or loose)[:1]
            items = [N(str(x)).strip() for x in items or () if N(str(x)).strip()]
            if not items:
                continue
            level, rank = self.level(c)
            out.append({"slot": slot, "level": level, "source": "mine" if level == "mine" else c["source"],
                        "card_source": c["source"], "rank": rank, "placed": True, "path": c["path"],
                        "date": c.get("date") or "", "text": "\n".join(items), "items": items,
                        "private": private, "strict": private})   # private: names and sources only, no row
        self._own[key] = out
        return out

    def winners(self, ent, slot):
        """([candidates], contested) that win a value slot of the entity by the cascade (its own cards only): one, or —
        two repositories of one rank saying different values — each side, `contested` True."""
        key = (ent["id"], slot)
        if key not in self._values:
            r = rv.resolve(slot, self.cat, self.own(ent, slot), None)
            self._values[key] = (list(r["shown"]) if r["diverges"] else r["shown"][:1], bool(r["diverges"]))
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
            contested = False
            if info.get("kind") == "value":
                ws, contested = self.winners(other, src)
                naming = [w for w in ws if self.entity(w["text"], ent["kind"])[0] == ent["id"]]
            else:
                naming = [c for c in self.own(other, src)
                          if any(self.entity(x, ent["kind"])[0] == ent["id"] for x in c["items"])]
            for c in naming:
                out.append({"slot": slot, "level": "derived", "source": c["path"], "card_source": c["card_source"],
                            "rank": None, "placed": True, "path": c["path"], "date": c["date"], "contested": contested,
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
    if c.get("contested"):                  # derived from one side of a value two repositories dispute (review M2)
        d["contested"] = True
    return d


def join_items(cands, reg, kind, strict, entity_of=None):
    """The items of a list's candidates, one per entity (plan C4, C7): {entity (its id, or None), label, origins:
    [{level, source, path, date, how}] — one per candidate that names it —, rows: [{level, source, text}] — the item's own
    line in each card that is not derived —, derived_only}. `strict` (a card's list): an item that names no entity of
    `kind` is no item; else it stays a text item, never joined with another by its words. Items with a row of yours
    first, then by the strongest origin, then by label. `entity_of(text, kind)` — item_entity by default."""
    entity_of = entity_of or (lambda text, k: item_entity(reg, text, k))
    groups, order = {}, []
    for k, c in enumerate(cands):
        seen = set()
        for text in c["items"]:
            eid, how = entity_of(text, kind)
            if eid is None and (strict or c.get("strict")) and kind:
                continue
            key = eid or ("text", k, " ".join(text.split()).casefold())   # a text item is never joined by its words
            if key not in groups:
                e = reg.of(eid) if eid else None            # an entity's id is the path of its first card
                groups[key] = {"entity": eid, "label": e["label"] if e else text, "kind": kind, "origins": [], "rows": []}
                order.append(key)
            g = groups[key]
            if key not in seen:                             # one origin per candidate, every row of it kept
                seen.add(key)
                g["origins"].append(_origin(c, how))
            if c["level"] != "derived" and not c.get("private"):
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
    s = _Slots(reg, idx, cat, sctx, people=people)
    out = {}
    for slot in sl.card_slots(cat, ent["kind"]):
        if only and slot not in only:
            continue
        if ent["kind"] == "person" and not people and slot not in PERSON_IDENTITY:
            continue                                    # outside People: a person's identity alone (review M8)
        info = sl.card_slot_info(cat, slot)
        cands = candidates(reg, idx, ent, slot, cat, sctx, _s=s)
        if not cands:
            continue
        unread = [c["path"] for c in ent["cards"] if c.get("home", True) and c.get("fields") is None]
        if info["kind"] == "list":
            items = join_items(cands, reg, item_kind(slot), strict=True, entity_of=s.entity)
            if items:
                out[slot] = {"slot": slot, "kind": "list", "items": items, "count": len(items), "why": rv.WHY_JOINED}
                if unread:                              # a card whose fields no walk read yet (review M3)
                    out[slot]["unread"] = unread
            continue
        r = rv.resolve(slot, cat, cands, None)
        if not r["shown"]:
            continue
        win = r["shown"][0]
        ans = {"slot": slot, "kind": "value", "origin": _origin(win), "why": r["why"],
               "diverges": [c["card_source"] for c in r["shown"]] if r["diverges"] else []}
        ans.update(_value(reg, slot, win))
        ans["also"] = [dict(_value(reg, slot, c), **_origin(c)) for c in list(r["shown"][1:]) + list(r["also"])]
        if unread:
            ans["unread"] = unread
        out[slot] = ans
    return out


# ------------------------------------------------------------------ `ctx read`: team.members one line per person (C8)
NOT_JOINED = "пункти не склеєно: %s"
NOT_MATCHED = "команду «%s» не зіставлено з карткою: %s"
FROM_CARDS = "з карток ще %d — ctx entity \"%s\" --slot team.members"
JOINED = "склеєно за сутністю: %d"
_TEAM_TITLE = re.compile(r"^\s*team\s*:\s*", re.I)


def team_entity(reg, title):
    """(entity, why) of the team card a store's team record is: its name, the name without its `(…)`, the short name in
    it — by a file name, title, slug or alias (exactly), else by the team's normalised names; exactly one team, else
    (None, why). A record is no card: this matches, it never merges (plan C8)."""
    name = _TEAM_TITLE.sub("", N(title or "")).strip()
    tries = [name]
    m = re.match(r"^(.*?)\s*\(([^)]*)\)\s*$", name)
    if m:
        tries += [m.group(1).strip(), m.group(2).strip()]
    ids = []
    for q in [t for t in tries if t]:
        found, how = reg.find(q, "team")
        if how in ("name", "similar"):
            ids += [e["id"] for e in found if e["id"] not in ids]
        if len(ids) == 1 and how == "name":
            break
    if len(ids) == 1:
        return reg.of(ids[0]), None
    if not ids:
        return None, "картки такої команди немає"
    return None, "кілька карток: " + ", ".join(sorted(ids)[:5])


def _who_short(o):
    return {"mine": "твоє", "derived": "виведене"}.get(o["level"], o["source"])


def _clean_row(text):
    t = ce._row(text)
    if t.startswith("|"):
        t = " | ".join(c.strip() for c in t.replace("\\|", "\x00").strip().strip("|").split("|")).replace("\x00", "|")
    return t


def member_lines(items, reg, idx, cat, sctx, limit=None):
    """One line per item: the strongest source's row (else the label, and for a person found only by derivation their
    role and e-mail), every source, `за назвою` for a join by name, `лише виведене`; a row another source writes
    differently is «також»."""
    out = []
    for it in items[:limit] if limit else items:
        rows = sorted(it.get("rows") or (), key=lambda r: LEVEL_RANK.get(r["level"], 9))
        head = _clean_row(rows[0]["text"]) if rows else it["label"]
        if not rows and it.get("entity"):
            ent = reg.of(it["entity"])
            sl_ = slots_of(reg, idx, ent, cat, sctx, only=["person.role", "person.email"]) if ent else {}
            extra = [sl_[k]["value"] for k in ("person.role", "person.email") if k in sl_]
            if extra:
                head += " — " + " · ".join(extra)
        marks = list(dict.fromkeys(_who_short(o) for o in it["origins"]))
        if any(o.get("how") == "name" for o in it["origins"]):
            marks.append("за назвою")
        if it.get("derived_only"):
            marks.append("лише виведене")
        out.append("- %s · %s" % (head, " · ".join(marks)))
        for r in rows[1:]:
            t = _clean_row(r["text"])
            if t != head:
                out.append("  також: %s (%s)" % (t, _who_short(r)))
    if limit and len(items) > limit:
        out.append("- ще %d" % (len(items) - limit))
    return out


def read_members(result, rec, origin, entities, cat):
    """The text `ctx read` prints for team.members of the record `rec` (plan C8, C8a): the origin line of each source,
    then one line per person — the record's items (yours, a bound block's), the matched team card's and the derived ones
    joined by entity. A core rule or your `prefer repo:` print as before, with `з карток ще N`; a busy or unbuilt index:
    as before, with `пункти не склеєно: …`; a record no team card matches: its own items joined, with `команду «…» не
    зіставлено з карткою: …`. `result` — ctx_resolve.resolve's answer (None: the record has no candidate); `entities()`
    gives ((registry, index, search context), why); `origin` — ctx_read's _Origin."""
    shown = list((result or {}).get("shown") or ())
    got, why = entities()
    if not got:
        return (rv.render_slot(result, origin) if result else "") + NOT_JOINED % why + "\n" if result else None
    reg, idx, sctx = got
    ent, unmatched = team_entity(reg, rec.get("title"))
    s = _Slots(reg, idx, cat, sctx)
    cards = s.own(ent, "team.members") + s.derived(ent, "team.members") if ent else []
    for c in cards:
        c["strict"] = True
    if result and (result["why"] == rv.WHY_RULE or str(result.get("prefer", "")).startswith("repo:")):
        n = len(join_items(cards, reg, "person", strict=True, entity_of=s.entity))
        return rv.render_slot(result, origin) + (FROM_CARDS % (n, ent["label"]) + "\n" if n else "")
    if not shown and not cards:
        return None
    recs = [dict(c, card_source=c["source"] if c.get("level") != "mine" else "own", path=c.get("record") or "",
                 date=c.get("checked") or "", items=split_items(c["text"])) for c in shown]
    items = join_items(recs + cards, reg, "person", strict=False, entity_of=s.entity)
    head = []
    for c in shown:
        if c.get("level") == "mine":
            head.append("> [твоє · %s]" % origin.clip(c["record"]))
        else:
            head.append(origin.line(c["ns"], c["block"], c.get("version") or "", [], slots=["team.members"]))
    for c in cards:
        if c["level"] != "derived":
            head.append("> [картка %s · %s%s]" % (c["card_source"] if c["level"] != "mine" else "твоя", c["path"],
                                                  " · " + c["date"][:10] if c.get("date") else ""))
    if any(c["level"] == "derived" for c in cards):
        head.append("> [виведене з карток людей: %d]" % sum(1 for c in cards if c["level"] == "derived"))
    lines = head + ["#### Members", JOINED % len(items)] + member_lines(items, reg, idx, cat, sctx)
    if unmatched:
        lines.append(NOT_MATCHED % (_TEAM_TITLE.sub("", rec.get("title") or ""), unmatched))
    return "\n".join(lines) + "\n"
