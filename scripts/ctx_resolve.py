#!/usr/bin/env python3
"""Grow PM — the resolver: what may answer a slot, and from where (since v3.15.0).

A slot (scripts/ctx_slots.py, references/context-slots.yaml) is answered by candidates of three kinds (spec §4):

- your text   in the records of the slot's kind — the active product, the teams a skill reads, the organisation, the
              profile — outside the managed regions, under the first of the slot's catalogue names that answers, else a
              heading you mapped to it (`ctx slot map`): one per record; a heading you mapped to another slot is not
              this slot's
- a bound block   from any record, when a binding (ctx_slots.bindings_of: yours, the `slot=` of the block's base, the
              plugin's own for the `team` block) ties it to the slot; where it belongs is decided as spec §4.4 says,
              and what text it gives as §4.5 says
- a block found by name   a block of the same product, team (or profile) record that does not answer through a
              binding (unbound, or bound but not one sound region), read as v3.14.1 read it (ctx_read._lookup: the
              first block that has a name) — only when your text in that record has nothing

The lookup mode follows the manifest (`field`: a field line, else its subsection — or the subsection only), as
ctx_read._lookup reads a `fields`/`required` name and a `sections` one.

- candidates    every candidate of one slot, each a dict that says whose it is, where, which version, when it was
                checked, whether you edited it, whether it is a core rule, and whether it can be placed at all
- resolve       what the cascade makes of them (spec §5.1, §6): a core rule, else yours, else the repositories by rank —
                with the «також» candidates, a divergence between repositories at an equal rank, your preference for the
                slot and your decision on a divergence. Pure: candidates and memory in, an answer out.
- compare_key, divergence_hashes   what two texts are compared by (a value slot: the value, not the line) and what a
                decision keeps of each side
- slot_context, slot_answers   the one assembly `ctx read`, `ctx explain` and `ctx slot decide` share: the live records,
                the product, its teams, the registrations, the memory and the bindings — and the answer of a slot per place

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


def _own(slot, rec, names, aliases, place, field):
    """Your candidate of `slot` in `rec`, or None — one per record, as ctx_read._lookup took the first name only: outside
    the managed regions, the first catalogue name that answers, in the catalogue's order (`field`: a field line, else its
    subsection; else the subsection), then the headings you mapped to the slot in this record. A heading you mapped to
    another slot in this record does not answer a catalogue name (unless you mapped it to this slot too): the name's next
    place answers, if it has one."""
    body = cc.strip_managed_regions(rec.get("body") or "")
    lines = body.splitlines(keepends=True)
    cores = [line.rstrip("\r\n") for line in lines]
    mine = [a["heading"] for a in aliases if a.get("record") == rec["id"] and a.get("slot") == slot]
    other = [a["heading"] for a in aliases if a.get("record") == rec["id"] and a.get("slot") != slot]
    for name, loose in [(n, False) for n in names] + [(h, True) for h in mine]:
        for start, _, is_field, text in _occurrences(lines, cores, name, field, loose):
            if not loose and _answers_any(cores[start], is_field, other) and not _answers_any(cores[start], is_field, mine):
                continue
            return {"slot": slot, "source": "mine", "level": "mine", "record": rec["id"], "block": None, "ns": None,
                    "version": None, "checked": sc.verified_of(rec, None), "edited": False, "rule": False, "how": None,
                    "heading": _heading(text), "text": text, "rank": None, "placed": True, "place": place}
    return None


def _inner(region):
    """A region's text without its two markers, ending in one newline."""
    return cb._detach(region).strip("\n") + "\n"


def _first(find, body, names):
    for n in names:
        t = find(body, n)
        if t is not None:
            return t
    return None


def _bound_text(inner, sub, kind, names, several, find):
    """The text a bound block gives its slot (spec §4.5): the subsection `sub` the binding names; for a block bound to
    several slots, the part that answers the slot's names; else the whole block. A value slot takes the part that
    answers its names inside that text. `find` is the lookup mode (ctx_read._field_text or _subsection). None when the
    block has no such part: then it is no candidate."""
    if sub:
        part = cr._subsection(inner, sub)
        if part is not None and kind == "value":
            part = _first(find, part, names)
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
    with that team wherever it sits. A product slot's block in a team record answers only when that team is read
    (`team_ids`). An org or profile slot takes a bound block from anywhere (place None)."""
    host = rec.get("type")
    if rkind == "product":
        if host == "product":
            return (True, prod["id"]) if prod is not None and rec["id"] == prod["id"] else None
        if host == "team":
            return (True, prod["id"] if prod is not None else None) if rec["id"] in team_ids else None
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


def candidates(slot, cat, records, prod, teams, repos, mem, store, bindings, field=None):
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
    an empty memory), `bindings` the first item of ctx_slots.bindings_of. `field` is the lookup mode, as the manifest
    asks the name: True (`fields`, `required`) — a field line, else its `####` subsection, as ctx_read._lookup(body, name);
    False (`sections`) — the subsection only, as _lookup(body, name, field=False); None — by the slot's kind (a value or a
    list: the field line first; a text: the subsection). It holds for your text, the blocks found by name and the part a
    bound block gives. Your text gives at most one candidate per record (the first name that answers). A block that is
    not one sound region (cb.find_regions: repeated, nested, broken) is no bound candidate but may still answer by name;
    a bound, sound block is never found by name. In order: your text, place by place; the bound blocks, in record order;
    the blocks found by name. Reads only."""
    info = sl.slot_info(cat, slot)
    if info is None:
        return []
    kind, rkind, names = info.get("kind"), info.get("record"), sl._names(info)
    field = (kind != "text") if field is None else bool(field)
    find = cr._field_text if field else cr._subsection
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
        found = _own(slot, rec, names, aliases, place_of(rec), field)
        if found:
            out.append(found)
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
                text = _bound_text(_inner(region), b.get("sub"), kind, names, several, find)
                where = _placement(rkind, rec, b, prod, team_ids, regs.reg(ns)) if text is not None else None
                if where is None or (ns, bid, text) in seen:
                    continue
                seen.add((ns, bid, text))
                out.append(regs.block(slot, rec, ns, bid, v, region, text, b.get("how"), where[0], where[1]))

    if rkind in NAME_PLACES:
        for rec in places:
            if rec["id"] in own_in:
                continue
            hit = None
            for ns, bid, v, _, inner in cr._blocks(rec.get("body") or ""):
                if bid and bindings.get((ns, bid)) and region_of(ns, bid, rec["id"]) is not None:
                    continue                # bound and sound: it answers through its bindings, never by name
                text = _first(find, inner, names)
                if text is not None:
                    hit = regs.block(slot, rec, ns, bid, v, region_of(ns, bid, rec["id"]) if bid else None, text,
                                     BY_NAME, True, place_of(rec))
                    break
            if hit:
                out.append(hit)
    return out


# ------------------------------------------------------------------ the cascade (spec §5.1, §5.2, §6)
LEVEL_ORDER = {"rule": 0, "mine": 1, "repo": 2}
WHY_RULE = "правило ядра"
WHY_MINE = "твоє перемагає (блок не є правилом ядра)"
WHY_LIST = "список — виводяться всі кандидати; склеювання пунктів — у v3.16"
WHY_ONLY = "єдиний кандидат"


def compare_key(kind, text):
    """What two candidates' texts are compared by, to tell whether they say the same: a value slot compares the VALUE —
    the text after the `**<label>:**` of a field line, or the text of a subsection without its heading — stripped and
    normalised, so the same value under two labels is no disagreement; a text or a list compares `cb.norm(text)` (CRLF,
    trailing blanks and trailing blank lines do not count)."""
    if kind == "value":
        lines = (text or "").splitlines(keepends=True)
        at = next((k for k, line in enumerate(lines) if line.strip()), None)
        if at is not None:
            core = lines[at].rstrip("\r\n")
            m = cs.FIELD_RE.match(core)
            if m:
                return cb.norm(m.group("value")).strip()
            if cs._level(core):
                return cb.norm("".join(lines[at + 1:])).strip()
    return cb.norm(text)


def _rank_key(c):
    """Smaller is stronger: a higher rank first, a rank that was not read (None) below every rank read."""
    r = c.get("rank")
    return (1, 0) if r is None else (0, -r)


def _cascade(cands):
    """The candidates that can be placed, in the order of the cascade: core rules, then yours, then the repositories —
    the rules and the repositories by rank (high first, a rank not read last), then by repository id; ties keep the order
    they came in."""
    live = [c for c in cands or () if c.get("placed")]
    return sorted(live, key=lambda c: (LEVEL_ORDER.get(c.get("level"), 2),
                                       (0, 0) if c.get("level") == "mine" else _rank_key(c),
                                       "" if c.get("level") == "mine" else str(c.get("source") or "")))


def _rank_text(c):
    return "?" if c.get("rank") is None else str(c["rank"])


def _firsts(cands):
    """One candidate per source, the first, in order."""
    seen, out = set(), []
    for c in cands:
        if c["source"] not in seen:
            seen.add(c["source"])
            out.append(c)
    return out


def divergence_hashes(kind, cands):
    """{source: sha256 of compare_key(kind, text)} — the first candidate of each source in `cands`: what a decision on a
    divergence keeps of each side, and what `resolve` checks it against."""
    return {c["source"]: cs.sha_text(compare_key(kind, c["text"])) for c in _firsts(cands)}


def resolve(slot, cat, cands, mem):
    """What the cascade makes of the candidates of `slot` (`candidates`; one place — one product's or one team's — at a
    time) given the memory `mem` (its `prefer` and `decisions`; None — an empty one). A candidate that is not `placed` is
    ignored. Returns {"slot", "kind", "shown", "note", "also", "diverges", "why", "decision", "prefer"}:

      shown      the candidates the skill gets in full, in the order of the cascade
      note       your candidate under a core rule (printed after «твоя примітка до правила»), else None
      also       the other candidates whose text differs from every shown one — one «також» line each (a value slot
                 compares values, not lines: compare_key)
      diverges   the repository ids that tie at the highest rank with different text, when no rule, text of yours,
                 preference or decision settles it (then all of them are `shown`); else []
      why        the cascade in words: «правило ядра» · «перевага: …» · «список — …» · «твоє перемагає (…)» · «більший
                 ранг: <repo> <rank> > <repo> <rank>» · «рівний ранг <rank>, різний текст: <repos>» · «твоє рішення від
                 <день>» · «єдиний кандидат»; "" when there is no candidate
      decision   the decision of yours that settled a divergence, else None
      prefer     the preference that shaped the answer: "all", "repo:<id>" (only when that repository has a candidate),
                 else "mine"

    The order: `all` (every candidate, the rule first; no note, no «також») · a core rule (shown; yours is the note) ·
    `repo:<id>` (that repository's candidate — all of them for a list) · a list (every candidate) · yours · the
    repositories: the highest rank; several at it with different text → a divergence, unless a decision of yours has the
    same hash for every one of them (ctx slot decide) — then its winner. Pure: nothing it is given is changed."""
    kind = (sl.slot_info(cat, slot) or {}).get("kind")
    mem = mem or {}
    pref = (mem.get("prefer") or {}).get(slot) or "mine"
    out = {"slot": slot, "kind": kind, "shown": [], "note": None, "also": [], "diverges": [], "why": "", "decision": None,
           "prefer": "mine"}
    live = _cascade(cands)
    if not live:
        return out

    def key(c):
        return compare_key(kind, c["text"])

    def settle(shown, why, note=None, prefer="mine", diverges=(), decision=None):
        keys = {key(c) for c in shown}
        rest = [c for c in live if not any(c is s for s in shown) and c is not note and key(c) not in keys]
        out.update(shown=list(shown), note=note, also=rest, diverges=list(diverges), why=why, decision=decision, prefer=prefer)
        return out

    if pref == "all":
        out.update(shown=list(live), why="перевага: all", prefer="all")
        return out
    mines = [c for c in live if c["level"] == "mine"]
    rules = [c for c in live if c["level"] == "rule"]
    if rules:
        return settle([rules[0]], WHY_RULE, note=mines[0] if mines else None)
    if pref.startswith("repo:"):
        theirs = [c for c in live if c["level"] == "repo" and c["source"] == pref[5:]]
        if theirs:
            return settle(theirs if kind == "list" else theirs[:1], "перевага: " + pref, prefer=pref)
    if kind == "list":
        out.update(shown=list(live), why=WHY_LIST)
        return out
    if mines:
        return settle([mines[0]], WHY_MINE if len(live) > 1 else WHY_ONLY)
    top = [c for c in live if _rank_key(c) == _rank_key(live[0])]
    sides = _firsts(top)
    if len(sides) > 1 and len({key(c) for c in sides}) > 1:
        hashes = divergence_hashes(kind, top)
        dec = (mem.get("decisions") or {}).get(slot)
        if isinstance(dec, dict) and dec.get("winner") in hashes and dec.get("hashes") == hashes:
            win = next(c for c in sides if c["source"] == dec["winner"])
            return settle([win], "твоє рішення від " + dec["at"] if dec.get("at") else "твоє рішення",
                          decision=dict(dec, hashes=dict(dec["hashes"])))
        ids = [c["source"] for c in sides]
        return settle(sides, "рівний ранг %s, різний текст: %s" % (_rank_text(top[0]), ", ".join(ids)), diverges=ids)
    win = top[0]
    lower = [c for c in live if _rank_key(c) != _rank_key(win) and key(c) != key(win)]
    if lower:
        why = "більший ранг: %s %s > %s %s" % (win["source"], _rank_text(win), lower[0]["source"], _rank_text(lower[0]))
    elif all(key(c) == key(win) for c in live):
        why = WHY_ONLY if len(live) == 1 else "однаковий текст у: " + ", ".join(c["source"] for c in _firsts(live))
    else:
        why = "перший з блоків %s" % win["source"]
    return settle([win], why)


# ------------------------------------------------------------------ the assembly the readers and `decide` share
def slot_context(store, copies, repos, product, now, mem=None):
    """Everything the resolver needs to answer slots, assembled as `ctx read` assembles it — reads only, no lock, no
    network, nothing written: the live records (ctx_read._live_view: a direct edit not yet imported counts), the active
    product (`product` — a name or id, or None: the one there is), its teams (the team records under the same parent, as
    ctx_read.read_view takes them), the registrations `repos` (ctx_repos.load_repos, as given), the slots memory (`mem`
    when a writing command already holds it, else read here) and the bindings. Returns {"store", "cat", "records", "notes",
    "pending", "product", "needs_product", "products", "teams", "repos", "mem", "mem_error", "bindings", "problems"}:
    `needs_product` is True (and `product` None) when several products and none asked for, or none that matches, `products`
    then being their names; a memory that cannot be read is an empty one and `mem_error` the line that says why (a reader
    goes on without it; a writing command stops on it). `cat` is the catalogue (a file that cannot be read is a
    ValueError); `problems` are the lines of ctx_slots.bindings_of."""
    cat = sl.load_catalogue()
    recs, notes, pending = cr._live_view(store, copies, now)
    products = [r for r in recs if r["type"] == "product"]
    prod, needs = cr._pick_product(products, product)
    teams = [r for r in recs if r["type"] == "team" and (prod is None or r.get("parent") == prod.get("parent"))]
    mem_error = None
    if mem is None:
        try:
            mem = sl.load_memory(store)
        except cs.StoreError as e:
            mem, mem_error = sl.empty_memory(), str(e)
    bindings, problems = sl.bindings_of(store, repos, mem)
    return {"store": store, "cat": cat, "records": recs, "notes": notes, "pending": pending, "product": prod,
            "needs_product": needs, "products": [p["title"].split(":", 1)[-1].strip() for p in products], "teams": teams,
            "repos": repos, "mem": mem, "mem_error": mem_error, "bindings": bindings, "problems": problems}


def slot_answers(sctx, slot, field=None):
    """The answer of `slot` per place, from a `slot_context`: [{"place", "candidates", "result"}] — one entry for each
    product or team record (or None: an organisation or profile slot) that has a candidate placed for it, in the order they
    first appear, `result` being `resolve` over that place's candidates. `field` is the lookup mode of `candidates`.
    A candidate that is not placed (a block that cannot be given to one team) is in no entry; `candidates` has it."""
    cands = candidates(slot, sctx["cat"], sctx["records"], sctx["product"], sctx["teams"], sctx["repos"], sctx["mem"],
                       sctx["store"], sctx["bindings"], field=field)
    groups = []
    for c in cands:
        if not c["placed"]:
            continue
        for place, members in groups:
            if place == c["place"]:
                members.append(c)
                break
        else:
            groups.append((c["place"], [c]))
    return [{"place": place, "candidates": members, "result": resolve(slot, sctx["cat"], members, sctx["mem"])}
            for place, members in groups]
