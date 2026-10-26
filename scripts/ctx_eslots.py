#!/usr/bin/env python3
"""Grow PM — the slots of one entity, assembled from its cards (since v3.19.0).

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
import provider_bundle as pb  # noqa: E402

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
_LABEL_LINE = re.compile(r"^\*\*([^*\n]{1,40}?)(?::\*\*|\*\*[ \t]*:)[ \t]*(.+)$")   # `**Lead:** A, B` (v3.20.0): a colon
                                                                                 # makes a label — `**A, B** — роль` is names
_NAME_SPLIT = re.compile(r"\s*(?:,|;|&|\s+(?:і|та|й|and)\s+)\s*")              # never `/`: a link's path has it
UNRANKED = -10 ** 9                 # the rank of a repository card whose registration gives none: below every rank


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
    return re.sub(r"^[\W_]+|[\W_]+$", "", t).strip()      # `**Bea Two**`, `Bea Two ◌`, `⭐ Bea Two`


def _listed_names(text):
    """The names an item lists before its role (v3.20.0, v3.19.0 known limits): a table row's first cell, the text after
    an inline `**Label:**`, else the text before the first ` — `, ` – `, ` - ` or `(` — split at `,`, `;`, `&`, « і »,
    « та », « й », « and ». (names, labelled): [] when the item lists one name and has no label."""
    t = _MARKER.sub("", N(text or "")).strip()
    labelled = False
    if t.startswith("|"):
        cells = [c.strip() for c in t.replace("\\|", "\x00").strip("|").split("|")]
        t = cells[0].replace("\x00", "|") if cells else ""
    else:
        m = _LABEL_LINE.match(t)
        if m:
            t, labelled = m.group(2), True
        t = re.split(r"\s+[—–-]\s+|\(", t, 1)[0]
    parts = [x.strip() for x in _NAME_SPLIT.split(t) if x.strip()]
    return (parts if len(parts) > 1 or (labelled and parts) else []), labelled


def expand_items(text, kind, entity_of):
    """[(row text, item text)] of one item of a people list: one per person it lists — a row «A, B — роль», an inline
    `**Lead:** A, B` — when every name names exactly one person, each a different one; else the item as it is. A name two
    people carry keeps the whole line one item, so nobody is joined from it by a guess."""
    if kind == "person":
        names, _ = _listed_names(text)
        if names:
            hits = [entity_of(x, kind)[0] for x in names]
            if all(hits) and len(set(hits)) == len(hits):
                return [(text, x) for x in names]
    return [(text, text)]


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
        self.problem = None
        self.ranks = {r.get("id"): rv._rank(r) for r in (sctx or {}).get("repos") or ()}
        self._own, self._derived, self._values, self._items = {}, {}, {}, {}

    def in_plugin_folder(self, path):
        """Is `path` under a plugin folder of yours (the index names of the own roots)?"""
        return any(path == p or path.startswith(p + "/") for p in self.reg.resolver.prefixes if p)

    def entity(self, text, kind):
        """item_entity, each (text, kind) once: hundreds of people name a few dozen teams."""
        key = (text, kind)
        if key not in self._items:
            self._items[key] = item_entity(self.reg, text, kind)
        return self._items[key]

    def level(self, card):
        if card["source"] == "own" or self.in_plugin_folder(card["path"]):
            return "mine", None             # your note, read through a local index while iCloud keeps its file: yours
        if card.get("origin") == "local":
            return "local", None
        rank = self.ranks.get(card["source"])
        return "repo", UNRANKED if rank is None else rank   # a registration that gives no rank: last of the repositories

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
                if self.idx.problem:
                    self.problem = self.idx.problem       # a busy read among good ones: said, never half a list
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
                        "private": private, "strict": True})   # a card's list keeps what names an entity; private: no row
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


def record_candidates(shown):
    """The candidates a store's team record gives team.members (ctx_resolve's `shown`) as the join takes them: your text
    `mine`, a bound block its repository's; its items are the list's lines, kept as text when they name no card."""
    return [dict(c, card_source=c["source"] if c.get("level") != "mine" else "own", path=c.get("record") or "",
                 date=c.get("checked") or "", items=split_items(c["text"]), strict=False, from_record=True)
            for c in shown or ()]


def _origin(c, how=None):
    d = {"level": c["level"], "source": c["card_source"], "path": c["path"], "date": c["date"]}
    if how:
        d["how"] = how
    if c.get("contested"):                  # derived from one side of a value two repositories dispute (review M2)
        d["contested"] = True
    if c.get("from_record"):                # a store record's or its block's item (ctx read), not a card's
        d["record"] = True
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
        for row, text in (x for t in c["items"] for x in expand_items(t, kind, entity_of)):
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
                g["rows"].append(dict({"level": c["level"], "source": c["card_source"], "text": row},
                                      **({"part": text} if row != text else {})))   # one person of a row of several
    if kind == "person":                                # a text item in another spelling of a person the list's other
        named = {k: reg.of(k) for k in order if not isinstance(k, tuple)}   # sources name: one line with them
        for k in [k for k in order if isinstance(k, tuple)]:
            name = _name_part(groups[k]["label"])
            hits = [e for e in named.values() if e and name and any(pb.same_person(name, x) for x in ce._names_of(e))]
            if len(hits) == 1:
                g, into = groups.pop(k), groups[hits[0]["id"]]
                order.remove(k)
                into["origins"] += [dict(o, how="alike") for o in g["origins"]]
                into["rows"] += g["rows"]
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


def slots_of(reg, idx, ent, cat, sctx, people=False, only=None, records=None):
    """{slot: answer} of the slots the cards of `ent` answer (ctx_slots.card_slots; `only` keeps those asked for), a slot
    with no candidate left out. A value: {slot, kind, value, entity?, origin, also: [{value, entity?, level, source, path,
    date}], diverges: [sources], why}; a list: {slot, kind, items (join_items), count, why}. Outside the People contour
    (`people` False) a person's slots are its identity alone — role, team, e-mail — which is all the catalogue gives a
    person; nothing of a profile's body or judgement is ever read. `records(ent)` — the candidates of team.members the
    store's team records matched with this team give (record_candidates), so `ctx entity` and `ctx read` say one
    composition (plan C8)."""
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
        exclusive, from_cards = False, 0
        if slot == "team.members" and records is not None:
            got = records(ent) or {}
            got = got if isinstance(got, dict) else {"cands": list(got), "exclusive": False}
            if got.get("exclusive"):            # a core rule or your `prefer repo:` — its list alone, as `ctx read`
                both = join_items(list(got["cands"]) + cands, reg, "person", strict=False, entity_of=s.entity)
                from_cards = sum(1 for i in both if not any(o.get("record") for o in i["origins"]))
                cands, exclusive = list(got["cands"]), True
            else:
                cands = list(got.get("cands") or ()) + cands
        if not cands:
            continue
        unread = [c["path"] for c in ent["cards"] if c.get("home", True) and c.get("fields") is None]
        if info["kind"] == "list":
            items = join_items(cands, reg, item_kind(slot), strict=False, entity_of=s.entity)
            if items:
                out[slot] = {"slot": slot, "kind": "list", "items": items, "count": len(items), "why": rv.WHY_JOINED}
                if exclusive:
                    out[slot].update(why=rv.WHY_RULE, from_cards=from_cards)
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
    """(entity, why) of the team card a store's team record is: its name, else the name without its `(…)` — never what
    the brackets hold alone (a parent team or a product) — by a file name, title, slug or alias (exactly), else by the
    team's normalised names; of several, the one card of an index before another team's card in a local index; exactly
    one team, else (None, why; two cards: the `ctx entity same` that would make them one). A record is no card: this
    matches, it never merges (plan C8)."""
    name = _TEAM_TITLE.sub("", N(title or "")).strip()
    tries = [name]
    m = re.match(r"^(.*?)\s*\(([^)]*)\)\s*$", name)
    if m:
        tries.append(m.group(1).strip())    # never the bracket alone: «Checkout (Zorg Pay)» is no Zorg Pay (review I2)
    by_how = {"name": [], "similar": []}
    for q in [t for t in tries if t]:
        found, how = reg.find(q, "team")
        if how in by_how:
            by_how[how] += [e["id"] for e in found if e["id"] not in by_how[how]]
    for how in ("name", "similar"):                     # an exact name first, a name alike only when none is exact
        ids = by_how[how]
        indexed = [i for i in ids if any(c.get("origin") == "index" for c in (reg.of(i) or {}).get("cards", []))]
        if len(ids) == 1:
            return reg.of(ids[0]), None
        if len(indexed) == 1:                           # a core's or your card before another team's in a local index
            return reg.of(indexed[0]), None
        if ids:
            ids = sorted(ids)
            return None, "кілька карток: " + ", ".join(ids[:5]) + (
                " — це одна команда? ctx entity same \"%s\" \"%s\"" % (ids[0], ids[1]) if len(ids) == 2 else "")
    return None, "картки такої команди немає"


def _who_short(o):
    return {"mine": "твоє", "derived": "виведене"}.get(o["level"], o["source"])


def _clean_row(text):
    t = ce._row(text)
    if t.startswith("|"):
        t = " | ".join(c.strip() for c in t.replace("\\|", "\x00").strip().strip("|").split("|")).replace("\x00", "|")
    return t


DERIVED_SHOWN = 20                      # the people only derivation names, at most, in a joined list (review M7)


def member_lines(items, reg, idx, cat, sctx, limit=None, team=None):
    """One line per item: the strongest source's row (else the label, and for a person found only by derivation their
    role and e-mail), every source, `за назвою` for a join by name, `лише виведене`; a row another source writes
    differently is «також»."""
    out, derived = [], 0
    for it in items[:limit] if limit else items:
        if it.get("derived_only"):
            derived += 1
            if derived > DERIVED_SHOWN:
                continue
        rows = sorted(it.get("rows") or (), key=lambda r: LEVEL_RANK.get(r["level"], 9))
        head = _clean_row(rows[0]["text"]) if rows else it["label"]
        if rows and rows[0].get("part"):                   # a row of several people: whose line this is (review M5)
            head = "%s — з рядка «%s»" % (it["label"], head)
        if not rows and it.get("entity"):
            ent = reg.of(it["entity"])
            sl_ = slots_of(reg, idx, ent, cat, sctx, only=["person.role", "person.email"]) if ent else {}
            extra = [sl_[k]["value"] for k in ("person.role", "person.email") if k in sl_]
            if extra:
                head += " — " + " · ".join(extra)
        marks = list(dict.fromkeys(_who_short(o) for o in it["origins"]))
        if any(o.get("how") == "name" for o in it["origins"]):
            marks.append("за назвою")
        if any(o.get("how") == "alike" for o in it["origins"]):
            marks.append("схоже ім'я")
        if it.get("derived_only"):
            marks.append("лише виведене")
        out.append("- %s · %s" % (head, " · ".join(marks)))
        for r in rows[1:]:
            t = _clean_row(r["text"])
            if t != head:
                out.append("  також: %s (%s)" % (t, _who_short(r)))
    if derived > DERIVED_SHOWN:
        out.append("- ще %d лише виведених — ctx entity \"%s\" --slot team.members" % (derived - DERIVED_SHOWN, team or "<команда>"))
    if limit and len(items) > limit:
        out.append("- ще %d" % (len(items) - limit))
    return out


def _non_items(text):
    """The lines of a members section that are no item — its prose, sub-headings, notes — in their order (the section's
    own heading aside): a joined list never loses them (Task 4 review I1)."""
    lines = (text or "").split("\n")
    items = set(split_items(text))
    out = []
    for k, line in enumerate(lines):
        s_ = line.strip()
        if not s_ or (k == next((i for i, x in enumerate(lines) if x.strip()), -1) and s_.startswith("#")):
            continue
        if _TABLE_RULE.match(s_) or s_ in items or _MARKER.sub("", line).strip() in items:
            continue
        if "|" in s_ and k + 1 < len(lines) and _TABLE_RULE.match(lines[k + 1].strip()):
            continue                                    # a table's header row
        out.append(line.rstrip())
    return out


_SHARED = {}


def _slots_for(reg, idx, cat, sctx):
    """One _Slots for every team record of one read (Task 4 review M7): each person's team is decided once."""
    if _SHARED.get("reg") is not reg:
        _SHARED.update(reg=reg, s=_Slots(reg, idx, cat, sctx))
    return _SHARED["s"]


def _block_marks(c):
    return ([rv.BY_NAME_MARK] if c.get("how") == rv.BY_NAME else []) + ([rv.EDITED_MARK] if c.get("edited") else []) \
        + ([rv.RULE_MARK] if c.get("level") == "rule" else [])


def read_members(result, rec, origin, entities, cat):
    """The text `ctx read` prints for team.members of the record `rec` (plan C8, C8a): the origin line of each source,
    then one line per person — the record's items (yours, a bound block's), the matched team card's and the derived ones
    joined by entity —, then each source's lines that are no item (prose, sub-headings, notes) as they are. A core rule,
    your `prefer repo:` or `prefer all` print as before (a rule and `repo:` with `з карток ще N` — the people the cards
    name and the list does not); a busy index: as before with `пункти не склеєно: …`; no index to join by (no vault):
    as before; a record no team card matches: its own items joined, with `команду «…» не зіставлено з карткою: …`.
    `result` — ctx_resolve.resolve's answer (None: the record has no candidate); `entities()` gives ((registry, index,
    search context), why); `origin` — ctx_read's _Origin."""
    shown = list((result or {}).get("shown") or ())
    got, why = entities()
    if not got:
        if not result:
            return None
        return rv.render_slot(result, origin) + (NOT_JOINED % why + "\n" if why else "")
    reg, idx, sctx = got
    if result and result.get("prefer") == "all":
        return rv.render_slot(result, origin)           # every candidate in full, as `prefer all` says
    ent, unmatched = team_entity(reg, rec.get("title"))
    s = _slots_for(reg, idx, cat, sctx)
    cards = s.own(ent, "team.members") + s.derived(ent, "team.members") if ent else []
    if idx.problem or s.problem:                        # the index went busy during the read: nothing joined by halves
        return (rv.render_slot(result, origin) if result else "") + NOT_JOINED % (idx.problem or s.problem) + "\n" if result else None
    recs = record_candidates(shown)
    if result and (result["why"] == rv.WHY_RULE or str(result.get("prefer", "")).startswith("repo:")):
        both = join_items(recs + cards, reg, "person", strict=False, entity_of=s.entity)
        n = sum(1 for i in both if not any(o.get("record") for o in i["origins"]))
        return rv.render_slot(result, origin) + (FROM_CARDS % (n, ent["label"]) + "\n" if n else "")
    if not shown and not cards:
        return None
    items = join_items(recs + cards, reg, "person", strict=False, entity_of=s.entity)
    head = []
    for c in shown:
        if c.get("level") == "mine":
            head.append("> [твоє · %s]" % origin.clip(c["record"]))
        else:
            head.append(origin.line(c["ns"], c["block"], c.get("version") or "", _block_marks(c), slots=["team.members"]))
    for c in cards:
        if c["level"] != "derived":
            head.append("> [картка %s · %s%s]" % (c["card_source"] if c["level"] != "mine" else "твоя", c["path"],
                                                  " · " + c["date"][:10] if c.get("date") else ""))
    if any(c["level"] == "derived" for c in cards):
        head.append("> [виведене з карток людей: %d]" % sum(1 for c in cards if c["level"] == "derived"))
    heading = next((c.get("heading") for c in shown if c.get("heading")), None) or "Members"
    lines = head + ["#### " + heading, JOINED % len(items)] + member_lines(items, reg, idx, cat, sctx,
                                                                           team=ent["label"] if ent else None)
    for c in shown:                                     # what is no item stays, under its source (review I1)
        rest = _non_items(c["text"])
        if rest:
            lines.append("> [%s — інший текст секції]" % ("твоє" if c.get("level") == "mine" else c["source"]))
            lines.extend(rest)
    if unmatched:
        lines.append(NOT_MATCHED % (_TEAM_TITLE.sub("", rec.get("title") or ""), unmatched))
    return "\n".join(lines) + "\n"
