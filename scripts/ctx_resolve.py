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
- a block found by name   a block of the same product, team (or profile) record that neither you nor its publisher
              bound (`ctx slot bind`, `slot=` — to any slot) and that the plugin's `team#Members` gives no text for the
              slot (a `Team Members` heading), read as v3.14.1 read it (ctx_read._lookup: the first block that has a
              name) — only when your text in that record has nothing

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
- render_slot   how `ctx read` prints one answer (spec §5.2): the shown candidates with their origin lines, the note under a
                rule, one «також» line for each other text, the divergence line
- without_shown, bound_slots, looked_for   no duplicates in a whole record (spec §5.2), the slots a bound block's origin
                line names in a record read whole (in a slot it names the slot shown), and the names a slot was looked for
                under (spec §5.3)
- unread_lines   the lines that say what a reader could not read (an unread registration, the slots memory, a block state)
- binding_problems   the bindings that do nothing, and why (a slot the catalogue lacks, a block that is gone, a repository nobody
                registered, a region that is not whole, a binding with nothing to give, a publisher's `slot=` your own binding set aside)
- validate_slots   what `ctx validate` says about slots: the memory that cannot be read, those bindings, the blocks that cannot be
                given to one team, the divergences between repositories, and the bindings worth proposing (ctx_slots.proposals)
- explain       what `ctx explain` prints (spec §7): for each slot its candidates and why the winner won, what it looked for
                where nothing answered, what you decided about it and the command that takes that back

Reads only: no lock, no network, nothing written. Semantics: references/context-protocol.md. Stdlib only.
"""
import datetime
import os
import re
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
EXPLICIT = ("memory", "marker")       # a binding that says what a block is (yours, the publisher's slot=): never found by name
NAME_PLACES = ("product", "team", "profile")   # the records whose unbound blocks answer by name (ctx_read._lookup looked there)


def _rank(reg):
    r = reg.get("rank") if reg else None
    return r if isinstance(r, int) and not isinstance(r, bool) else None


class _Repos:
    """The registrations by namespace, the block state of each repository and the bases it keeps — each read once, never
    written — and the sound regions of each namespace in `records` (cb.find_regions), found once. One is made by
    slot_context and shared by everything a read or an explanation does (ctx_slots.bindings_of, candidates, bound_slots,
    binding_problems, the origin lines of ctx_read): a read reads each block state and each base once. A state or a base
    that cannot be read is no state here (ctx_slots.bindings_of names it)."""

    def __init__(self, store, repos, records=None):
        self.store = store
        self.by_ns = {}
        for r in repos or ():
            self.by_ns.setdefault(r.get("namespace") or r["id"], r)
        self.records = records
        self._states, self._bases, self._regions = {}, {}, {}

    def reg(self, ns):
        return self.by_ns.get(ns)

    @staticmethod
    def _once(cache, key, read):
        """read() the first time `key` is asked, its result (or the error it raised, raised again) every time after."""
        if key not in cache:
            try:
                cache[key] = (read(), None)
            except (cs.StoreError, OSError) as e:
                cache[key] = (None, e)
        got, err = cache[key]
        if err is not None:
            raise err
        return got

    def load_state(self, repo_id):
        """cb.load_state of the repository `repo_id`, read once: one that cannot be read raises its error each time."""
        return self._once(self._states, repo_id, lambda: cb.load_state(self.store, repo_id))

    def get_base(self, repo_id, sha):
        """cb.get_base of the repository `repo_id`, read once per hash: one that cannot be read raises its error each time."""
        return self._once(self._bases, (repo_id, sha), lambda: cb.get_base(self.store, repo_id, sha))

    def entry(self, ns, bid):
        reg = self.by_ns.get(ns)
        if reg is None or not bid:
            return {}
        try:
            return self.load_state(reg["id"])["blocks"].get(bid) or {}
        except (cs.StoreError, OSError):
            return {}

    def base(self, ns, bid):
        sha = self.entry(ns, bid).get("base_sha")
        if not sha:
            return None
        try:
            return self.get_base(self.by_ns[ns]["id"], sha)
        except (cs.StoreError, OSError):
            return None

    def regions(self, records, ns):
        """cb.find_regions(records, ns)[0] — found once per namespace for the records this was made for (other records:
        found afresh)."""
        if records is not self.records:
            return cb.find_regions(records, ns)[0]
        if ns not in self._regions:
            self._regions[ns] = cb.find_regions(records, ns)[0]
        return self._regions[ns]

    def block(self, slot, rec, ns, bid, v, region, text, how, placed, place, sub=None):
        """A block's candidate: `region` is the whole region text (markers included) when it is sound, else None; `sub` the
        subsection its binding names."""
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
                "placed": placed, "place": place, "sub": sub}


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
                    "heading": _heading(text), "text": text, "rank": None, "placed": True, "place": place, "sub": None}
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


def candidates(slot, cat, records, prod, teams, repos, mem, store, bindings, field=None, regs=None):
    """Every candidate of `slot` (an id of the catalogue `cat`; an unknown one has none), as a list of dicts:

      slot, source ("mine" or the repository id: the registration whose namespace the block carries, else the namespace),
      level ("rule": a bound block whose base says policy=rule · "mine" · "repo"), record (the id of the record the
      text sits in), block and ns (None for your text), version (the marker's v=, else the state's), checked (the day the
      store last checked the block — for your text, the record's `verified` date), edited (the region differs from every
      base the state keeps of it; a block with no base is no edit), rule (cb.is_rule of its base), how ("memory",
      "marker", "plugin", "name" — found by name without a binding — or None for your text), heading (of the text, or
      the field's name), text, rank (the registration's; None when it was not read), placed (False: a block outside
      a team record that cannot be given to one team — the skill does not get it, explain shows it), place (the id of
      the product or team record the candidate answers for; None for an org or profile slot and when not placed), sub (the
      subsection the binding names; None for your text, a block found by name and a binding of the whole block).

    `records` are the live records (ctx_read._live_view), `prod` the active product record (or None), `teams` the team
    records the skill reads, `repos` the registrations (crp.load_repos), `mem` the slots memory (its `aliases`; None —
    an empty memory), `bindings` the first item of ctx_slots.bindings_of. `field` is the lookup mode, as the manifest
    asks the name: True (`fields`, `required`) — a field line, else its `####` subsection, as ctx_read._lookup(body, name);
    False (`sections`) — the subsection only, as _lookup(body, name, field=False); None — by the slot's kind (a value or a
    list: the field line first; a text: the subsection). It holds for your text, the blocks found by name and the part a
    bound block gives. Your text gives at most one candidate per record (the first name that answers). A block that is
    not one sound region (cb.find_regions: repeated, nested, broken) is no bound candidate but may still answer by name,
    and so may a block the plugin's own `team#Members` gives this slot no text (a `Team Members` heading). Never found by
    name: a block a binding gives this slot a text — not even where the binding does not place it (another team's,
    another product's) — and a block you or its publisher bound (`how` memory, marker) to any slot of the catalogue: an
    explicit binding says what the block is, as a heading you mapped to another slot is no candidate of this one (spec
    §4.1, §4.2); a binding to a slot the catalogue lacks does nothing (`validate` names it `unknown`), so it keeps no
    block from answering by name.
    In order: your text, place by place; the bound blocks, in record order; the blocks found by name. `regs` is the
    _Repos of slot_context (None: one is made here). Reads only."""
    info = sl.slot_info(cat, slot)
    if info is None:
        return []
    kind, rkind, names = info.get("kind"), info.get("record"), sl._names(info)
    field = (kind != "text") if field is None else bool(field)
    find = cr._field_text if field else cr._subsection
    aliases = (mem or {}).get("aliases") or []
    bindings = bindings or {}
    team_ids = [t["id"] for t in teams or ()]
    regs = _Repos(store, repos, records) if regs is None else regs

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

    def region_of(ns, bid, host):
        reg = regs.regions(records, ns).get(bid)
        return reg["text"] if reg and reg["host"] == host else None

    seen, answered = set(), set()        # answered: the blocks a binding gives this slot a text — never found by name
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
                if text is None:
                    continue                # this binding gives the slot nothing: no candidate through it
                answered.add((ns, bid))
                where = _placement(rkind, rec, b, prod, team_ids, regs.reg(ns))
                if where is None or (ns, bid, text) in seen:
                    continue
                seen.add((ns, bid, text))
                out.append(regs.block(slot, rec, ns, bid, v, region, text, b.get("how"), where[0], where[1], sub=b.get("sub")))

    if rkind in NAME_PLACES:
        for rec in places:
            if rec["id"] in own_in:
                continue
            hit = None
            for ns, bid, v, _, inner in cr._blocks(rec.get("body") or ""):
                if bid and ((ns, bid) in answered or any(b.get("how") in EXPLICIT and sl.slot_info(cat, b.get("slot")) is not None
                                                         for b in bindings.get((ns, bid)) or ())):
                    continue                # it answers through a binding, or yours / the publisher's says what it is
                text = _first(find, inner, names)
                if text is not None:
                    hit = regs.block(slot, rec, ns, bid, v, region_of(ns, bid, rec["id"]) if bid else None, text,
                                     BY_NAME, True, place_of(rec))
                    break
            if hit:
                out.append(hit)
    return out


# ------------------------------------------------------------------ the cascade (spec §5.1, §5.2, §6)
LEVEL_ORDER = {"rule": 0, "mine": 1, "repo": 2, "local": 3, "derived": 4}
                                      # local, derived: an entity's cards (v3.19.0, ctx_eslots) — a card a local index
                                      # holds, then what another entity's card says of this one
WHY_RULE = "правило ядра"
WHY_MINE = "твоє перемагає (блок не є правилом ядра)"
WHY_LIST = "список — виводяться всі кандидати; team.members у ctx read склеєно за сутністю"
LEVEL_WORDS = {"repo": "репозиторій", "local": "локальний індекс", "derived": "виведене"}
WHY_JOINED = "список — пункти склеєно за сутністю"      # v3.19.0: one item per person, team or mission (ctx_eslots)
WHY_ONLY = "єдиний кандидат"
WHY_UNREAD = "реєстрацію не прочитано — показано без каскаду"


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


def unread_registration(c):
    """A repository's candidate whose registration was not read (no rank): its rank and its rules are unknown. A card of
    a local index or a derived candidate (v3.19.0) has no rank by nature: it is no such candidate."""
    return c.get("level") in ("repo", "rule") and c.get("rank") is None


def resolve(slot, cat, cands, mem):
    """What the cascade makes of the candidates of `slot` (`candidates`; one place — one product's or one team's — at a
    time) given the memory `mem` (its `prefer` and `decisions`; None — an empty one). A candidate that is not `placed` is
    ignored. A repository's candidate whose registration was not read (rank None) takes no part in the cascade: it is
    shown after the cascade's own shown candidates, never as «також» (spec §4.6: «кандидати з неї показано без каскаду»).
    Returns {"slot", "kind", "shown", "note", "also", "diverges", "why", "decision", "prefer"}:

      shown      the candidates the skill gets in full, in the order of the cascade, then those of a registration not read
      note       your candidate under a core rule (printed after «твоя примітка до правила»), else None
      also       the other candidates whose text differs from every shown one — one «також» line each (a value slot
                 compares values, not lines: compare_key)
      diverges   the repository ids that tie at the highest rank with different text, when no rule, text of yours,
                 preference or decision settles it (then all of them are `shown`); else []
      why        the cascade in words: «правило ядра» · «перевага: …» · «список — …» · «твоє перемагає (…)» · «більший
                 ранг: <repo> <rank> > <repo> <rank>» · «рівний ранг <rank>, різний текст: <repos>» · «твоє рішення від
                 <день>» · «єдиний кандидат»; WHY_UNREAD when only candidates of a registration not read are left; "" when
                 there is no candidate
      decision   the decision of yours that settled a divergence, else None
      prefer     the preference that shaped the answer: "all", "repo:<id>" (only when that repository has a candidate),
                 else "mine"

    The order: `all` (every candidate, the rule first; no note, no «також») · a core rule (shown; yours is the note) ·
    `repo:<id>` (that repository's candidate — all of them for a list) · a list (every candidate) · yours · the
    repositories: the highest rank; several at it with different text → a divergence, unless a decision of yours has the
    same hash for every one of them (ctx slot decide) — then its winner. Pure: nothing it is given is changed."""
    cands = list(cands or ())
    unread = [c for c in cands if c.get("placed") and unread_registration(c)]
    out = _resolve_ranked(slot, cat, [c for c in cands if not unread_registration(c)], mem)
    if unread:
        out.update(shown=out["shown"] + unread, why=out["why"] or WHY_UNREAD)
    return out


def _resolve_ranked(slot, cat, cands, mem):
    """`resolve` over your candidates and those whose registration was read (their rank is known)."""
    kind = (sl.slot_info(cat, slot) or sl.card_slot_info(cat, slot) or {}).get("kind")
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
    top = [c for c in live if c.get("level") == live[0].get("level") and _rank_key(c) == _rank_key(live[0])]
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
    lower = [c for c in live if (c.get("level"), _rank_key(c)) != (win.get("level"), _rank_key(win)) and key(c) != key(win)]
    if lower and lower[0].get("level") != win.get("level"):      # a card of a lower level (v3.19.0): no rank to compare
        why = "вищий рівень: %s перед %s" % (LEVEL_WORDS.get(win.get("level"), win.get("level")),
                                             LEVEL_WORDS.get(lower[0].get("level"), lower[0].get("level")))
    elif lower:
        why = "більший ранг: %s %s > %s %s" % (win["source"], _rank_text(win), lower[0]["source"], _rank_text(lower[0]))
    elif all(key(c) == key(win) for c in live):
        why = WHY_ONLY if len(live) == 1 else "однаковий текст у: " + ", ".join(c["source"] for c in _firsts(live))
    else:
        why = "перший з блоків %s" % win["source"]
    return settle([win], why)


# ------------------------------------------------------------------ the assembly the readers and `decide` share
def slot_context(store, copies, repos, product, now, mem=None, cat=None):
    """Everything the resolver needs to answer slots, assembled as `ctx read` assembles it — reads only, no lock, no
    network, nothing written: the live records (ctx_read._live_view: a direct edit not yet imported counts), the active
    product (`product` — a name or id, or None: the one there is), its teams (the team records under the same parent, as
    ctx_read.read_view takes them), the registrations `repos` (ctx_repos.load_repos, as given), the slots memory (`mem`
    when a writing command already holds it, else read here) and the bindings. Returns {"store", "cat", "records", "notes",
    "pending", "product", "needs_product", "products", "teams", "repos", "mem", "mem_error", "bindings", "dropped",
    "problems", "regs"}:
    `needs_product` is True (and `product` None) when several products and none asked for, or none that matches, `products`
    then being their names; a memory that cannot be read is an empty one and `mem_error` the line that says why (a reader
    goes on without it; a writing command stops on it). `cat` is the catalogue (a file that cannot be read is a
    ValueError) — `cat` when the caller already holds one; `dropped` the bindings to a slot the catalogue lacks, which bind
    nothing (ctx_slots.bindings_of); `problems` are the lines of ctx_slots.bindings_of; `regs` the one
    _Repos everything built on this assembly shares (the bindings, the candidates, the origin lines): each block state and
    each base is read once."""
    cat = sl.load_catalogue() if cat is None else cat
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
    regs, dropped = _Repos(store, repos, recs), []
    bindings, problems = sl.bindings_of(store, repos, mem, reads=regs, cat=cat, dropped=dropped)
    return {"store": store, "cat": cat, "records": recs, "notes": notes, "pending": pending, "product": prod,
            "needs_product": needs, "products": [p["title"].split(":", 1)[-1].strip() for p in products], "teams": teams,
            "repos": repos, "mem": mem, "mem_error": mem_error, "bindings": bindings, "dropped": dropped,
            "problems": problems, "regs": regs}


def slot_answers(sctx, slot, field=None, unplaced=None):
    """The answer of `slot` per place, from a `slot_context`: [{"place", "candidates", "result"}] — one entry for each
    product or team record (or None: an organisation or profile slot) that has a candidate placed for it, in the order they
    first appear, `result` being `resolve` over that place's candidates. `field` is the lookup mode of `candidates`.
    A candidate that is not placed (a block that cannot be given to one team) is in no entry; `candidates` has it, and so
    does `unplaced` when it is a list (it is appended there)."""
    cands = candidates(slot, sctx["cat"], sctx["records"], sctx["product"], sctx["teams"], sctx["repos"], sctx["mem"],
                       sctx["store"], sctx["bindings"], field=field, regs=sctx.get("regs"))
    groups = []
    for c in cands:
        if not c["placed"]:
            if unplaced is not None:
                unplaced.append(c)
            continue
        for place, members in groups:
            if place == c["place"]:
                members.append(c)
                break
        else:
            groups.append((c["place"], [c]))
    return [{"place": place, "candidates": members, "result": resolve(slot, sctx["cat"], members, sctx["mem"])}
            for place, members in groups]


# ------------------------------------------------------------------ what `ctx read` prints (spec §5.2, §5.3)
NOTE_LINE = "твоя примітка до правила"
BY_NAME_MARK = "за назвою, без прив'язки"
EDITED_MARK = "з твоїми правками"
RULE_MARK = "правило ядра"
ALSO_LINE = "також: %s каже інакше — ctx explain %s"
DIVERGE_LINE = "⚠ розбіжність між репозиторіями — вирішити: ctx slot decide %s %s"
SHOWN_LINE = "> [блок %s — у слоті %s вище]"
SHOWN_SUB_LINE = "> [блок %s › %s — у слоті %s вище]"
MINE_WORD = "твоє"
NO_BLOCKS = "блоків із цим слотом немає"
UNPLACED_BLOCK = "є нерозміщений блок — ctx explain %s"
ELSEWHERE_BLOCK = "є блок в іншому записі — ctx explain %s"      # a required field of a record read whole, a block elsewhere
UNREAD_REGISTRATION = "реєстрацію %s не прочитано — ранги й правила її блоків невідомі; кандидати з неї показано без каскаду"
UNREAD_MEMORY = "пам'ять слотів не прочитано (%s) — прив'язки й рішення не застосовано"


def render_slot(res, origin):
    """One answer (`resolve`) as `ctx read` prints it, ending in a newline:

      the divergence line first, when repositories diverge (`ctx slot decide <slot> <the first of them by id>`);
      each shown candidate — a block after its origin line (origin.line: `> [<repo> · v<v> · станом на <day>]`, then
        `слот <slot> — <about>` for a bound block, `за назвою, без прив'язки`, `з твоїми правками`, `правило ядра`,
        `перевага: <who>` when a preference shaped the answer, never on a candidate of a registration not read); your
        text after `> [твоє · <record id>]` only when the slot shows more than one candidate or has a «також» line, a
        note or a divergence — alone, it is printed as v3.14.1 printed it, with no line (ruling P4);
      under a rule, `твоя примітка до правила` and your text in full;
      one «також: <repo or «твоє»> каже інакше — ctx explain <slot>» line for each other source with another text.

    `origin` is a ctx_read._Origin (it knows the repositories, their block states and the slots' `about`)."""
    slot = res["slot"]
    lined = len(res["shown"]) > 1 or bool(res["also"] or res["note"] or res["diverges"])
    prefer = [] if res.get("prefer", "mine") == "mine" else ["перевага: " + res["prefer"]]
    out = []
    if res["diverges"]:
        out.append(DIVERGE_LINE % (slot, origin.clip(sorted(res["diverges"])[0])))

    def piece(c, extra):
        if c.get("level") == "mine":
            head = ("> [" + " · ".join([MINE_WORD, origin.clip(c["record"])] + extra) + "]") if lined else None
        else:
            marks = ([BY_NAME_MARK] if c.get("how") == BY_NAME else []) + ([EDITED_MARK] if c.get("edited") else []) \
                + ([RULE_MARK] if c.get("level") == "rule" else [])
            head = origin.line(c["ns"], c["block"], c.get("version") or "", marks + extra,
                               slots=[] if c.get("how") == BY_NAME else [slot])
        return ([head] if head else []) + [c["text"].rstrip("\n")]

    for c in res["shown"]:
        out += piece(c, [] if unread_registration(c) else prefer)       # the preference did not place an unread one
    if res["note"]:
        out += [NOTE_LINE] + piece(res["note"], [])
    for c in res["also"]:
        line = ALSO_LINE % (MINE_WORD if c.get("level") == "mine" else origin.clip(c["source"]), slot)
        if line not in out:
            out.append(line)
    return "\n".join(out) + "\n"


def without_shown(text, shown):
    """`text` — a record a skill reads whole (read_by, a whole team) — with what a slot of the same view already used taken
    out (spec §5.2: no duplicates; criterion 5: never more than it used). `shown` is {(namespace, block id): [(slot, kind,
    the text the slot used)]}, for each bound block a slot gave in full or as a «також» line:

      a slot that used the whole region (a binding with no `#Sub`, to one slot, of a text or a list): the region is the one
        line `> [блок <block> — у слоті <slot> вище]`;
      a slot that used a subsection (a `#Sub` binding — the plugin's `team#Members` among them — or the part of a block
        bound to several slots): the region, its markers and its origin line stay; that subsection, heading to the next
        heading of the same or a higher level, is the one line `> [блок <block> › <Підсекція> — у слоті <slot> вище]`
        (the heading text without the hashes);
      a value slot (a field line): nothing goes — the block stays whole.

    Regions inside a `<ns>:section` wrapper are found; the wrapper stays. A region with no id is never touched, and a
    subsection that cannot be found again in the region is left as it is."""
    if not shown:
        return text

    def cut(region, bid, uses):
        inner = _inner(region)                      # as _bound_text gave it: a blank line after the begin marker is no part
        whole = next((slot for slot, kind, part in uses if kind != "value" and cb.norm(part) == cb.norm(inner)), None)
        if whole:
            return SHOWN_LINE % (bid, whole)
        lines = region.splitlines(keepends=True)
        for slot, kind, part in uses:
            head = next((line.rstrip("\r\n") for line in (part or "").splitlines() if line.strip()), "")
            if kind == "value" or not cs._level(head):
                continue                            # a field line: the block stays whole
            cores = [line.rstrip("\r\n") for line in lines]
            at = next((k for k in range(1, len(cores) - 1) if cores[k] == head), None)
            if at is None:
                continue
            level = cs._level(head)
            end = next((j for j in range(at + 1, len(cores) - 1) if 0 < cs._level(cores[j]) <= level), len(cores) - 1)
            while end > at + 1 and not cores[end - 1].strip():
                end -= 1                            # the blank lines before the next heading stay
            lines[at:end] = [SHOWN_SUB_LINE % (bid, cs._heading_text(head), slot) + "\n"]
        return "".join(lines)

    def walk(t):
        out, at = [], 0
        for m in cc.REGION_RE.finditer(t):
            if m.group(1).endswith(":section"):
                opened = t.index(">", m.start()) + 1
                closing = t.rindex("<!--", m.start(), m.end())
                out += [t[at:opened], walk(t[opened:closing]), t[closing:m.end()]]
            else:
                uses = shown.get((m.group(1), m.group(2))) if m.group(2) else None
                out.append(t[at:m.end()] if not uses else t[at:m.start()] + cut(m.group(0), m.group(2), uses))
            at = m.end()
        return "".join(out) + t[at:]
    return walk(text)


def bound_slots(cat, records, bindings, regs=None):
    """{(namespace, block id): [slot, …]} — the slots each bound block answers (`bindings`, the first item of
    ctx_slots.bindings_of), in the order its bindings give them: a block that is one sound region (cb.find_regions) and
    gives the slot a text (spec §4.5, in the lookup mode of the slot's kind) — a binding with no such part names no slot. Its
    origin line names them all in a record read whole (spec §5.2, criterion 3); in a slot it names the slot shown
    (render_slot). A slot the catalogue lacks is left out. `regs` — the _Repos of slot_context (None: one is made here)."""
    out = {}
    regs = _Repos(None, None, records) if regs is None else regs
    for rec in records or ():
        for ns, bid, _, _, _ in cr._blocks(rec.get("body") or ""):
            tied = (bindings or {}).get((ns, bid)) if bid else None
            if not tied:
                continue
            reg = regs.regions(records, ns).get(bid)
            if not reg or reg["host"] != rec["id"]:
                continue
            several = len({b.get("slot") for b in tied}) > 1
            for b in tied:
                info = sl.slot_info(cat, b.get("slot"))
                if info is None or b["slot"] in out.get((ns, bid), ()):
                    continue
                kind = info.get("kind")
                find = cr._subsection if kind == "text" else cr._field_text
                if _bound_text(_inner(reg["text"]), b.get("sub"), kind, sl._names(info), several, find) is not None:
                    out.setdefault((ns, bid), []).append(b["slot"])
    return out


def looked_for(cat, slot, rec, mem):
    """The names `slot` was looked for under in the record `rec`: the catalogue's names, then the headings you mapped to the
    slot in that record (ctx slot map) — what «Відсутнє» and `explain` say it looked for (spec §5.3)."""
    mapped = [a["heading"] for a in (mem or {}).get("aliases") or () if a.get("record") == rec["id"] and a.get("slot") == slot]
    names = sl._names(sl.slot_info(cat, slot) or {})
    return names + [h for h in mapped if sl._norm(h) not in {sl._norm(n) for n in names}]


# ------------------------------------------------------------------ what a reader could not read, and the bindings that do nothing
def unread_lines(sctx, skipped):
    """The lines that say what a reader could not read, from a `slot_context` and the registrations `skipped` (as
    ctx_repos.load_repos reports them, (path, reason)): one line for each registration file not read — only when a block in the
    records has a namespace no registration read has, for then its ranks and rules are what the file would have said (spec
    §4.6) —, the slots memory that could not be read, and the block state of each repository that could not be. `ctx read` and
    `ctx explain` print them; an empty list says everything was read."""
    known = {r.get("namespace") or r["id"] for r in sctx["repos"] or ()}
    stray = any(ns not in known for r in sctx["records"] for ns, _, _, _, _ in cr._blocks(r.get("body") or ""))
    out = [UNREAD_REGISTRATION % cc.clip(path, 200) for path, _ in skipped or ()] if stray else []
    if sctx["mem_error"]:
        out.append(UNREAD_MEMORY % sctx["mem_error"])
    return out + list(sctx["problems"])


GONE_BLOCK = "прив'язка до блоку, якого немає в записах: %s %s → %s"
UNKNOWN_REPO = "прив'язка до репозиторію, якого не зареєстровано (чи реєстрацію не прочитано): %s %s → %s"
BROKEN_BLOCK = "блок %s (%s) не є одним цілим регіоном — повторений, вкладений чи зламаний; прив'язка до %s не діє"
EMPTY_BINDING = "прив'язка %s %s → %s недійсна: у блоці немає %s"
IGNORED_MARKER = "атрибут slot=%s блоку %s %s ігноровано — блок прив'язано твоєю прив'язкою (до %s)"
UNKNOWN_SLOT = "прив'язка до слоту, якого немає в каталозі: %s %s → %s"
WHY_UNKNOWN = "слота немає в каталозі (references/context-slots.yaml)"
WHY_UNREGISTERED = "репозиторій не зареєстровано (чи реєстрацію не прочитано)"
WHY_GONE = "блоку немає в записах"
WHY_BROKEN = "блок не є одним цілим регіоном — повторений, вкладений чи зламаний; прив'язка не діє"
WHY_EMPTY = "у блоці немає %s"
WHY_IGNORED = "атрибут slot= видавця ігноровано — блок прив'язано твоєю прив'язкою (до %s)"


def binding_problems(sctx):
    """The bindings of a `slot_context` that do not do what they say, [{"kind", "slot", "repo", "block", "sub", "how", "text", "why"}],
    `text` being the line that tells it (spec §4.5, and what a core that took a block away leaves behind) and `why` the short
    reason that follows the binding in `ctx validate`. `kind`:

      "unknown"       the binding (yours, or the `slot=` attribute of the block's base) names a slot the catalogue lacks — a
                      catalogue that changed, a publisher ahead of the plugin; it binds nothing (the next source binds the
                      block: `dropped` of the slot_context) and nothing else is judged of it
      "unregistered"  your binding names a repository nobody registered (or whose registration was not read)
      "missing"       your binding names a block that is in none of the records — the core took it away, the binding stayed
      "broken"        the block is there but is not one sound region (repeated, nested, a marker broken): no binding applies
      "empty"         the block is sound and the slot is in the catalogue, but the block has no part for it — the subsection
                      the binding names, or (a block of several slots, a value slot) none that answers the slot's names
      "ignored"       the `slot=` attribute of the block's base names a slot your own binding of the block set aside — your
                      binding wins for the whole block (spec §4.2); `slot` is the slot the attribute names

    The plugin's own binding of the `team` block is not a problem when its block lacks the part (a growth squad's team block
    has no Members; a heading `Team Members` — then the block answers by name, `candidates`). Reads only."""
    cat, recs = sctx["cat"], sctx["records"]
    regs = sctx.get("regs") or _Repos(sctx["store"], sctx["repos"], recs)
    present = {(ns, bid) for rec in recs for ns, bid, _, _, _ in cr._blocks(rec.get("body") or "") if bid}

    def region(ns, bid):
        return regs.regions(recs, ns).get(bid)

    out = []

    def add(kind, slot, repo, bid, sub, how, text, why):
        out.append({"kind": kind, "slot": slot, "repo": repo, "block": bid, "sub": sub, "how": how, "text": text, "why": why})

    for d in sctx.get("dropped") or ():
        reg = regs.reg(d["ns"])
        repo, where = reg["id"] if reg else d["ns"], d["block"] + ("#" + d["sub"] if d.get("sub") else "")
        add("unknown", d["slot"], repo, d["block"], d.get("sub"), d["how"], UNKNOWN_SLOT % (repo, where, d["slot"]), WHY_UNKNOWN)
    for (ns, bid), tied in (sctx["bindings"] or {}).items():
        reg = regs.reg(ns)
        repo = reg["id"] if reg else ns
        several = len({b.get("slot") for b in tied}) > 1
        for b in tied:
            slot, sub, how = b.get("slot"), b.get("sub"), b.get("how")
            info = sl.slot_info(cat, slot)
            where = bid + ("#" + sub if sub else "")
            if how == "plugin":
                continue
            whole = region(ns, bid)
            if info is None:
                add("unknown", slot, repo, bid, sub, how, UNKNOWN_SLOT % (repo, where, slot), WHY_UNKNOWN)
            elif how == "memory" and reg is None:
                add("unregistered", slot, repo, bid, sub, how, UNKNOWN_REPO % (repo, where, slot), WHY_UNREGISTERED)
            elif (ns, bid) not in present:
                if how == "memory":
                    add("missing", slot, repo, bid, sub, how, GONE_BLOCK % (repo, where, slot), WHY_GONE)
            elif whole is None:
                add("broken", slot, repo, bid, sub, how, BROKEN_BLOCK % (bid, repo, slot), WHY_BROKEN)
            else:
                kind = info.get("kind")
                find = cr._subsection if kind == "text" else cr._field_text
                if _bound_text(_inner(whole["text"]), sub, kind, sl._names(info), several, find) is None:
                    lacks = "підсекції «%s»" % sub if sub else "підсекції чи рядка за назвами слоту"
                    add("empty", slot, repo, bid, sub, how, EMPTY_BINDING % (repo, where, slot, lacks), WHY_EMPTY % lacks)
        yours = [b.get("slot") for b in tied if b.get("how") == "memory"]
        for slot in sl.marker_slots(regs.base(ns, bid)) if yours else ():
            if slot not in yours and sl.slot_info(cat, slot) is not None:
                add("ignored", slot, repo, bid, None, "marker", IGNORED_MARKER % (slot, repo, bid, ", ".join(yours)),
                    WHY_IGNORED % ", ".join(yours))
    return out


# ------------------------------------------------------------------ what `ctx explain` prints (spec §7)
KIND_WORDS = {"value": "одне значення", "text": "текст", "list": "список"}
OUTCOME_MARKS = {"won": "✔", "shown": "✔", "lost": "✗", "diverges": "⚠", "unplaced": "·"}
HOW_WORDS = {"memory": "прив'язка: твоя", "marker": "прив'язка: slot= видавця", "plugin": "прив'язка: плагіна"}
COMMAND_WORDS = {"diverges": "вирішити: ", "unplaced": "прив'язати: "}
NOT_FOUND = "не знайдено"
LOOKED_LINE = "шукав: %s — у %s; %s"
UNPLACED_ABOVE = "є нерозміщений блок — рядок вище"
MAP_LINE = "прив'язати свою підсекцію: "
MAP_COMMAND = 'ctx slot map %s "<Назва>" %s'
BIND_COMMAND = "ctx slot bind %s %s %s --team %s"
DECIDE_COMMAND = "ctx slot decide %s %s"
FORGET_COMMAND = "ctx slot forget %s"
UNPLACED_WHY = "не розміщено: блок поза записом команди, а команд не одна"
TIE_WHY = "розбіжність: рівний ранг %s, різний текст"
STALE_DECISION = " (зараз не діє: тексти змінилися)"
NEEDS_PRODUCT = "Продукти: %s. Слоти продукту й команди — для одного продукту: ctx explain … --product \"<назва>\""
WHOLE_SKILL = "Цей скіл редагує local-context.md і читає його цілком — слотів не просить."
UNMAPPED_HEAD = "Блоки без прив'язки — репозиторій їх публікує, але жоден слот їх не бере (прив'язати: ctx slot bind <repo> <block>[#<Підсекція>] <slot>):"
SKIPPED_HEAD = "Вимкнені блоки (skip_blocks) — ядро пропонує, ти вимкнув:"
NO_SLOTS = "Слотів із кандидатами немає."


def _asked(spec, cat):
    """[(slot, field)] a skill's manifest entry (ctx_read.manifest_for) asks, in the order `ctx read` reads them — the profile,
    the product, the team; in each `required`, then `fields` (field=True: a field line, else its subsection), then `sections`
    (field=False: the subsection only) — each name through the catalogue: a name with no slot is left out, a slot comes once."""
    out = []
    for record in ("profile", "product", "team"):
        want = spec.get(record)
        for key, field in (("required", True), ("fields", True), ("sections", False)) if isinstance(want, dict) else ():
            names = want.get(key)
            for name in names if isinstance(names, list) else ():
                slot = sl.slot_for(cat, record, name)
                if slot and slot not in [s for s, _ in out]:
                    out.append((slot, field))
    return out


def _row(c, outcome, reason=None, command=None):
    """One candidate as the `candidates` item of an explained slot: source, record and outcome; the heading it sits under;
    when it was checked; for a block also its id, `sub` (the subsection its binding names), version, whether you edited it,
    whether it acts as a core rule, how it was bound (`how`) and the rank of its repository; `reason` and `command` when the
    outcome has them."""
    row = {"source": c["source"], "record": c["record"], "outcome": outcome}
    if c.get("heading"):
        row["heading"] = c["heading"]
    if c.get("checked"):
        row["checked"] = c["checked"]
    if c.get("level") != "mine":
        row.update(block=c["block"], edited=bool(c.get("edited")), rule=c.get("level") == "rule", how=c.get("how"), rank=c.get("rank"))
        if c.get("sub"):
            row["sub"] = c["sub"]
        if c.get("version"):
            row["version"] = c["version"]
    if reason:
        row["reason"] = reason
    if command:
        row["command"] = command
    return row


def _rows(res, cands, unplaced, team):
    """The rows of one place: the candidates the skill gets (`shown`, in the order of the cascade), your text under a rule (the
    note), the others in the order of the cascade — and then the blocks that cannot be placed. `res` is `resolve` over `cands`.
    A shown candidate is `won` when the cascade chose it alone (a list shows every candidate, so only a rule or a preference
    chooses one of a list), `diverges` when repositories tie, `shown` otherwise — your text under a rule too, as the note. Every
    other is `lost`, with the reason the cascade gives (`why`); one that says what a shown one says lost to it by saying it
    once."""
    shown, kind = res["shown"], res["kind"]
    core = [c for c in shown if not unread_registration(c)]
    lone = len(core) == 1 and not res["diverges"] and res["prefer"] != "all" and res["why"] != WHY_LIST

    def lost(c):
        text = compare_key(kind, c["text"])
        same = next((s for s in shown if compare_key(kind, s["text"]) == text), None)
        if same is not None:
            return "той самий текст, що й у " + (MINE_WORD if same.get("level") == "mine" else same["source"])
        if res["diverges"] and c.get("level") == "repo" and _rank_key(c) != _rank_key(shown[0]):
            return "нижчий ранг: %s %s < %s %s" % (c["source"], _rank_text(c), shown[0]["source"], _rank_text(shown[0]))
        if c.get("level") == "rule":
            return "інше правило ядра сильніше: %s %s" % (shown[0]["source"], _rank_text(shown[0]))
        return res["why"]

    rows = []
    first = list(shown) + ([res["note"]] if res["note"] else [])
    for c in first + [c for c in _cascade(cands) if not any(c is f for f in first)]:
        if any(c is s for s in shown):
            if res["diverges"]:
                rows.append(_row(c, "diverges", TIE_WHY % _rank_text(c), DECIDE_COMMAND % (res["slot"], c["source"])))
            elif unread_registration(c):
                rows.append(_row(c, "shown", WHY_UNREAD))
            else:
                rows.append(_row(c, "won" if lone else "shown"))
        elif c is res["note"]:
            rows.append(_row(c, "shown", NOTE_LINE))
        else:
            rows.append(_row(c, "lost", "програв: " + lost(c)))
    for c in unplaced:
        rows.append(_row(c, "unplaced", UNPLACED_WHY, BIND_COMMAND % (c["source"], c["block"] + ("#" + c["sub"] if c.get("sub") else ""),
                                                                      res["slot"], team or "<запис>")))
    return rows


def _row_line(row):
    """A row as one line: the mark of its outcome, whose it is and where, the marks that matter, the reason, the command."""
    clip = cc.clip
    if "block" not in row:
        bits = [MINE_WORD + " · " + clip(row["record"], 80) + (" › " + clip(row["heading"], 80) if row.get("heading") else "")]
        if row.get("checked"):
            bits.append("перевірено " + row["checked"])
    else:
        bits = [clip(row["source"], 60), "блок %s%s%s у записі %s" % (
            clip(row["block"], 60), "#" + clip(row["sub"], 60) if row.get("sub") else "",
            " v" + clip(row["version"], 40) if row.get("version") else "", clip(row["record"], 80))]
        if row.get("checked"):
            bits.append("станом на " + row["checked"])
        bits += [BY_NAME_MARK] if row.get("how") == BY_NAME else [HOW_WORDS[row["how"]]] if row.get("how") in HOW_WORDS else []
        bits += [EDITED_MARK] if row.get("edited") else []
        bits += [RULE_MARK] if row.get("rule") else []
    line = OUTCOME_MARKS[row["outcome"]] + " " + " · ".join(bits)
    if row.get("reason"):
        line += " — " + row["reason"]
    if row.get("command"):
        line += " — " + COMMAND_WORDS.get(row["outcome"], "") + row["command"]
    return line


def _remembered(mem, slot, record_id):
    """What the memory holds about `slot` — its bindings, the names you gave it in this record (`record_id`; every record when
    None), the preference, the decision — as {"bindings", "aliases", "prefer", "decision"}, or None when it holds nothing."""
    out = {"bindings": [dict(b) for b in mem.get("bindings") or () if b["slot"] == slot],
           "aliases": [dict(a) for a in mem.get("aliases") or () if a["slot"] == slot and record_id in (None, a["record"])],
           "prefer": (mem.get("prefer") or {}).get(slot), "decision": (mem.get("decisions") or {}).get(slot)}
    return out if any(out.values()) else None


def _remembered_words(m, acts):
    words = ["прив'язка %s %s%s%s" % (b["repo"], b["block"], "#" + b["sub"] if b.get("sub") else "",
                                      " --team " + b["team"] if b.get("team") else "") for b in m["bindings"]]
    words += ["назва “%s” у %s" % (a["heading"], a["record"]) for a in m["aliases"]]
    if m["prefer"]:
        words.append("перевага: " + m["prefer"])
    if m["decision"]:
        d = m["decision"]
        words.append("рішення про розбіжність: %s%s%s" % (d["winner"], " від " + d["at"] if d.get("at") else "",
                                                        "" if acts else STALE_DECISION))
    return words


def _explain_slot(sctx, slot, field, strict, problems):
    """The explanation of one slot, [entry] — one for each place (the product, a team; an organisation or profile slot has one).
    A place with no candidate is an entry only when the run is `strict` (a skill's or named slots: say what was looked for), or
    when the slot has an unplaced block, a note or something in the memory (then every place is: that is what to act on)."""
    cat, mem, recs = sctx["cat"], sctx["mem"] or {}, sctx["records"]
    info = sl.slot_info(cat, slot)
    kind, rkind = info.get("kind"), info.get("record")
    unplaced = []
    by_place = {a["place"]: a for a in slot_answers(sctx, slot, field=field, unplaced=unplaced)}
    if rkind == "product":
        places = [sctx["product"]] if sctx["product"] is not None else [None]
    elif rkind == "team":
        places = list(sctx["teams"]) or [None]
    else:
        places = [None]
    notes = [p["text"] for p in problems if p["slot"] == slot]
    strict = strict or bool(unplaced or notes or sl.in_memory(mem, slot))
    out = []
    for rec in places:
        got = by_place.get(rec["id"] if rec is not None else None)
        if not (strict or got):
            continue
        home = rec if rec is not None else next((r for r in recs if r.get("type") == rkind), None)
        cands = got["candidates"] if got else []
        res = got["result"] if got else resolve(slot, cat, [], mem)
        rows = _rows(res, cands, unplaced, home["id"] if home is not None and rkind == "team" else None)
        found = any(r["outcome"] != "unplaced" for r in rows)
        names = []
        for r in [home] if home is not None else [{"id": None}]:
            names += [n for n in looked_for(cat, slot, r, mem) if n not in names]
        entry = {"slot": slot, "kind": kind, "about": info.get("about"), "record": home["id"] if home is not None else None,
                 "title": home["title"] if home is not None else None,
                 "winner": next((r["source"] for r in rows if r["outcome"] == "won"), None), "candidates": rows,
                 "why": res["why"], "prefer": res["prefer"], "looked_in": {"names": names, "records": [home["title"]] if home is not None else []},
                 "commands": [r["command"] for r in rows if r.get("command")]}
        if res["decision"]:
            entry["decision"] = res["decision"]
        if not found:
            entry["commands"].append(MAP_COMMAND % (home["id"] if home is not None else "<запис>", slot))
        kept = _remembered(mem, slot, home["id"] if home is not None else None)
        if kept:
            entry["memory"] = kept
            entry["commands"].append(FORGET_COMMAND % slot)
        if notes:
            entry["notes"] = list(notes)
        out.append(entry)
    return out


def _slot_lines(s):
    """An explained slot as text: the header, a line for each candidate, why, and — nothing found — what was looked for and the
    command that maps your own name; what you decided and the way back; the notes."""
    found = any(r["outcome"] != "unplaced" for r in s["candidates"])
    out = [" · ".join([s["slot"], KIND_WORDS.get(s["kind"], s["kind"])] + ([s["title"]] if s["title"] else []) + ([] if found else [NOT_FOUND]))]
    out += ["  " + _row_line(r) for r in s["candidates"]]
    if s["why"]:
        out.append("  чому: " + s["why"])
    if not found:
        where = ", ".join(s["looked_in"]["records"]) or "записах"
        out.append("  " + LOOKED_LINE % (", ".join(s["looked_in"]["names"]), where,
                                        UNPLACED_ABOVE if s["candidates"] else NO_BLOCKS))
        out.append("  " + MAP_LINE + [c for c in s["commands"] if c.startswith("ctx slot map")][0])
    if s.get("memory"):
        out.append("  у твоїй пам'яті слотів: " + "; ".join(_remembered_words(s["memory"], "decision" in s)))
        out.append("  зняти: " + FORGET_COMMAND % s["slot"])
    out += ["  увага: " + n for n in s.get("notes") or ()]
    return out


def _held(sctx):
    """{(namespace, block id)} — the blocks some binding names: those it binds (`bindings`) and those bound only to a slot the
    catalogue lacks (`dropped`, which bind nothing). A block in it is never proposed nor listed as no slot's: the `unknown`
    line of `validate` and `explain` already says what is wrong with its binding."""
    return set(sctx["bindings"] or ()) | {(d["ns"], d["block"]) for d in sctx.get("dropped") or ()}


def _unmapped(sctx):
    """The blocks of a registered repository that no slot takes — [{"repo", "block", "record", "version", "heading"}], once each,
    in the order of the records: regions with an id and no binding at all (the plugin's own binding of the `team` block counts,
    and so does a binding to a slot the catalogue lacks: _held)."""
    regs = sctx.get("regs") or _Repos(sctx["store"], sctx["repos"], sctx["records"])
    out, seen, held = [], set(), _held(sctx)
    for rec in sctx["records"]:
        for ns, bid, v, _, inner in cr._blocks(rec.get("body") or ""):
            reg = regs.reg(ns)
            if bid and reg is not None and (ns, bid) not in held and (ns, bid) not in seen:
                seen.add((ns, bid))
                out.append({"repo": reg["id"], "block": bid, "record": rec["id"], "version": v or None, "heading": _heading(inner)})
    return out


def explain(store, copies, repos, skipped, slots=None, skill=None, product=None, today=None, catalogue=None, manifest=None):
    """(text, result) of `ctx explain`: where each slot came from and why it won (spec §7). Reads only — no lock, no network,
    nothing written; it is built on the one assembly `ctx read` uses (slot_context) and the candidates and the cascade it
    resolves with (slot_answers).

    Which slots: the ones `slots` names, in that order, none twice (an unknown one is a ValueError); else those the manifest
    entry of `skill` asks, in the order `ctx read` reads them (an unknown skill is a KeyError; one that reads the whole file asks
    none) — and the lookup mode of each is the manifest's, as `ctx read` has it (`slots` and `skill` together: the skill's mode
    for the slots it asks); else every slot of the catalogue that has a candidate, a note or something in the memory, followed
    by `unmapped_blocks` and `skipped_blocks`. A named or a skill's slot is explained for every place, found or not. With
    several products and none named (`product`), the slots of a product and of a team are not explained: `needs_product`.

    `result`: {"slots": [{"slot", "kind", "about", "record", "title", "winner", "candidates": [{"source", "record", "outcome": won
    | lost | shown | diverges | unplaced, …}], "why", "prefer", "looked_in": {"names", "records"}, "commands", and, when there is
    something to say, "decision" (the one that settled a divergence), "memory" (what you decided about the slot) and "notes"
    (the bindings that do nothing)}], "unmapped_blocks", "skipped_blocks", "needs_product", "products", "warnings" (what could
    not be read: `unread_lines`)}. A slot has one entry for each place — a team is one — so a team slot with several teams
    appears once for each; `record` tells which. Every file is read within one time budget (cs.read_timeout, or what is
    left of the caller's cs.read_budget), as `ctx read` reads."""
    with cs.read_budget(cs.read_timeout()):
        return _explain(store, copies, repos, skipped, slots, skill, product, today, catalogue, manifest)


def _explain(store, copies, repos, skipped, slots, skill, product, today, catalogue, manifest):
    today = (today or datetime.date.today().isoformat())[:10]
    cat = sl.load_catalogue() if catalogue is None else catalogue
    asked, whole = [], False
    if skill:
        spec = cr.manifest_for(manifest or cr.load_manifest(), skill)
        whole = bool(spec.get("full"))
        asked = [] if whole else _asked(spec, cat)
    modes = dict(asked)
    named = list(dict.fromkeys(slots or ()))
    for s in named:
        if sl.slot_info(cat, s) is None:
            raise ValueError("no slot %r in the catalogue (references/context-slots.yaml)" % s)
    strict = bool(named or skill)
    order = named or ([s for s, _ in asked] if skill else list(sl._slots(cat)))
    sctx = slot_context(store, copies, repos, product, today + "T00:00:00", cat=cat)
    problems = binding_problems(sctx)
    entries = []
    for slot in order:
        if sctx["needs_product"] and sl.slot_info(cat, slot).get("record") in ("product", "team"):
            continue
        entries += _explain_slot(sctx, slot, modes.get(slot), strict, problems)
    unmapped = [] if strict else _unmapped(sctx)
    off = [] if strict else [{"repo": r["id"], "block": b} for r in repos or () for b in r.get("skip_blocks") or ()]
    warnings = unread_lines(sctx, skipped)

    head = ["# Звідки слоти"] + (["скіл " + skill] if skill else []) + (["слоти " + ", ".join(named)] if named else []) \
        + (["продукт " + cc.clip(sctx["product"]["title"].split(":", 1)[-1].strip(), 80)] if sctx["product"] is not None else [])
    lines = [" · ".join(head)]
    if whole:
        lines.append(WHOLE_SKILL)
    if sctx["needs_product"]:
        lines.append(NEEDS_PRODUCT % ", ".join(sctx["products"]))
    lines += warnings
    for s in entries:
        lines += [""] + _slot_lines(s)
    if not entries and not whole and not sctx["needs_product"]:
        lines += ["", NO_SLOTS]
    if unmapped:
        lines += ["", UNMAPPED_HEAD]
        lines += ["  %s · блок %s%s у записі %s%s" % (cc.clip(b["repo"], 60), cc.clip(b["block"], 60), " v" + cc.clip(b["version"], 40) if b["version"] else "",
                                                     cc.clip(b["record"], 80), " · " + cc.clip(b["heading"], 80) if b["heading"] else "") for b in unmapped]
    if off:
        lines += ["", SKIPPED_HEAD] + ["  %s · блок %s" % (cc.clip(b["repo"], 60), cc.clip(b["block"], 60)) for b in off]
    result = {"slots": entries, "unmapped_blocks": unmapped, "skipped_blocks": off, "needs_product": bool(sctx["needs_product"]),
              "warnings": warnings}
    if sctx["needs_product"]:
        result["products"] = sctx["products"]
    return "\n".join(lines) + "\n", result


# ------------------------------------------------------------------ what `ctx validate` says about slots (spec §4.2, §4.4, §6, §8)
BINDING_WARNING = "slot binding: %s %s → %s — %s"
DIVERGES_WARNING = "slot %s diverges between %s — " + DECIDE_COMMAND
PROPOSAL_WARNING = "proposal: ctx slot bind %s %s %s"
CATALOGUE_UNREAD = "слоти не перевірено — каталог не прочитано: %s"
RECORDS_UNREAD = "слоти не перевірено — записи не прочитано: %s"


def _shell_arg(arg):
    """`arg` as one word of a command line: as it is when nothing in it needs quoting (a `#` inside is no comment), else in
    double quotes — so that the line `validate` prints can be pasted and runs."""
    if arg and not re.search(r"[\s\"'\\$`&|;<>()*?!{}\[\]~]", arg):
        return arg
    return '"%s"' % re.sub(r'(["\\$`])', r"\\\1", arg)


def validate_slots(store, copies, repos, skipped, now, cat=None):
    """(errors, warnings, proposals) of `ctx validate` for slots — reads only, as `ctx read` reads: the live records, the
    registrations `repos` (`skipped` — those that could not be read, as ctx_repos.load_repos reports them), the slots memory, the
    block states. Nothing is written.

    `errors`: the slots memory cannot be read (`slots memory not readable|not valid: .state/slots.json (…)`) — and then nothing
    else is said: bindings, divergences and proposals judged against an empty memory would be wrong. `warnings`, in this order:
    what a reader could not read (unread_lines); each binding that does nothing (binding_problems) and each block that cannot be
    given to one team (a team slot, several teams, no `--team`), as `slot binding: <repo> <block>[#<sub>] → <slot> — <why>`;
    each divergence between repositories, as `slot <slot> diverges between <a>, <b> — ctx slot decide <slot> <repo>`; and one
    `proposal: ctx slot bind <repo> <block>[#<sub>] <slot>` for each of `proposals` (ctx_slots.proposals). With several products
    every product is checked (a divergence or an unplaced block in any of them is named, once). A catalogue or records that
    cannot be read: one warning, the slots are not checked. Every file is read within one time budget (cs.read_timeout, or
    what is left of the caller's cs.read_budget), as `ctx read` reads."""
    with cs.read_budget(cs.read_timeout()):
        return _validate_slots(store, copies, repos, skipped, now, cat)


def _validate_slots(store, copies, repos, skipped, now, cat):
    try:
        cat = sl.load_catalogue() if cat is None else cat
    except ValueError as e:
        return [], [CATALOGUE_UNREAD % cc.clip(e, 200)], []
    try:
        mem = sl.load_memory(store)
    except cs.StoreError as e:
        return [str(e)], [], []
    try:
        first = slot_context(store, copies, repos, None, now, mem=mem, cat=cat)
        views = [first]
        if first["needs_product"]:
            views = [slot_context(store, copies, repos, r["id"], now, mem=mem, cat=cat) for r in first["records"] if r["type"] == "product"]
    except (cs.StoreError, OSError) as e:
        return [], [RECORDS_UNREAD % cc.clip(e, 200)], []
    clip = cc.clip

    def named(repo, block, sub):
        return clip(repo, 60), clip(block + ("#" + sub if sub else ""), 120)

    bound, diverging = [], []

    def put(into, line):
        if line not in into:
            into.append(line)

    for p in binding_problems(first):
        repo, where = named(p["repo"], p["block"], p["sub"])
        put(bound, BINDING_WARNING % (repo, where, clip(p["slot"], 80), p["why"]))
    for view in views:
        teams = ", ".join(clip(t["id"], 80) for t in view["teams"])
        for slot in sl._slots(cat):
            if sl.slot_info(cat, slot) is None:
                continue
            unplaced = []
            for x in slot_answers(view, slot, unplaced=unplaced):
                ids = sorted(clip(i, 60) for i in x["result"]["diverges"])
                if ids:
                    put(diverging, DIVERGES_WARNING % (slot, ", ".join(ids), slot, ids[0]))
            for c in unplaced:
                repo, where = named(c["source"], c["block"], c.get("sub"))
                why = UNPLACED_WHY + (" (%s)" % teams if teams else "") + " — " + BIND_COMMAND % (repo, _shell_arg(where), slot, "<запис>")
                put(bound, BINDING_WARNING % (repo, where, slot, why))
    found = sl.proposals(first["records"], repos, _held(first), cat)
    proposed = [PROPOSAL_WARNING % (clip(q["repo"], 60), _shell_arg(clip(q["block"] + ("#" + q["sub"] if q["sub"] else ""), 120)), q["slot"])
                for q in found]
    return [], unread_lines(first, skipped) + bound + diverging + proposed, found
