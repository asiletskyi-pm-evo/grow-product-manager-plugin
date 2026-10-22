#!/usr/bin/env python3
"""Grow PM — who is who: one registry of the people, teams, missions, modules, metrics and work your notes, the cores and
a local index of yours hold (since v3.18.0).

A card is a note whose type makes it one (ctx_index.ENTITY_KINDS): a person note of your layer, a core's registry card,
a Growth card a local index of yours holds. The registry joins the cards of one entity by three keys, the strongest
first — your answer (`ctx entity same`), the e-mail, a bridge recognised by its shape — and by nothing else: a name or a
title never merges two cards, it only offers them as «maybe the same» for your answer. `ctx entity not-same` keeps two
cards apart whatever the keys say. Nothing is written into a note.

- SCHEMA, FILE, WHERE           your answers: `<store>/.state/entities.json` (schema context-entity-memory/1)
                                {"schema", "same": [[a, b, day]], "not_same": [[a, b, day]]} — a and b the cards' paths,
                                in order; with the discipline of `.state/search.json`: a key this build does not know is
                                refused, never dropped; a file that cannot be read is never reset
- empty_memory, load_memory, save_memory, answer   read, write and change it (`ctx entity same|not-same`)
- local_cards                   the cards of every registered local index the plugin's own index does not hold —
                                their frontmatter alone (ctx_index.identity_of), read only, as `ctx search` opens one
- Resolver                      a link's target as written → the note it means, by the rules of `ctx search --get`:
                                the exact path, the plugin folder's path, the end of a path, the name; several → a list
- build, Registry               the entities: cards joined by the keys, the related teams (a link under another name),
                                the open pairs; `find` — a request as an e-mail, a Jira key, a path, a name, then alike
- known_prefixes                the Jira project prefixes the cards name (a team's or a mission's `…jira…` fields, a
                                work card's key): a key-shaped token is a mention only with one of them (or a /browse/ link)
- load                          the registry of a search context: the own index's cards, the local ones, the memory

Reads the index (ctx_index), a registered local index (mode=ro) and `.state/entities.json`; writes only that file
(`save_memory`, for the writing commands of ctx.py). Stdlib only.
"""
import json
import os
import re
import sqlite3
import sys
import time
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx_common as cc  # noqa: E402
import ctx_index as ci  # noqa: E402
import ctx_search as cs_  # noqa: E402
import ctx_store as cs  # noqa: E402
import provider_bundle as pb  # noqa: E402

N = cc.N
SCHEMA = "context-entity-memory/1"
FILE = "entities.json"
WHERE = ".state/" + FILE
_KEYS = ("schema", "same", "not_same")
_DAY = re.compile(r"\d{4}-\d{2}-\d{2}\Z")


# ------------------------------------------------------------------ your answers
def empty_memory():
    return {"schema": SCHEMA, "same": [], "not_same": []}


def _pair(a, b):
    return sorted((N(a).strip(), N(b).strip()))


def _clean(data):
    """`data` as the canonical memory: each pair once, in order, the later answer's day; a pair in both lists keeps the
    later answer (`not_same` on the same day). A schema that is not SCHEMA, a part of the wrong shape or a key nobody
    knows is a ValueError that says which."""
    if not isinstance(data, dict):
        raise ValueError("not an object")
    if data.get("schema") != SCHEMA:
        raise ValueError("schema is %r, not %r" % (data.get("schema"), SCHEMA))
    extra = sorted(str(k) for k in data if k not in _KEYS)
    if extra:
        raise ValueError("unknown key: %s" % ", ".join(extra))
    best = {}
    for which in ("same", "not_same"):
        items = data.get(which, [])
        if not isinstance(items, list):
            raise ValueError("%s is not a list" % which)
        for i, x in enumerate(items, 1):
            if not (isinstance(x, list) and len(x) == 3 and all(isinstance(v, str) and v.strip() for v in x)
                    and _DAY.match(x[2])):
                raise ValueError("%s %d is not [path, path, YYYY-MM-DD]" % (which, i))
            a, b = _pair(x[0], x[1])
            if a == b:
                raise ValueError("%s %d names one card twice" % (which, i))
            old = best.get((a, b))
            if old is None or x[2] > old[1] or (x[2] == old[1] and which == "not_same"):
                best[(a, b)] = (which, x[2])
    out = empty_memory()
    for (a, b), (which, day) in sorted(best.items()):
        out[which].append([a, b, day])
    return out


def _error(kind, why):
    return cs.StoreError("entity memory %s: %s (%s)" % (kind, WHERE, " ".join(str(why).split())[:300]))


def load_memory(store, timeout=None):
    """Your answers in `store` (a ctx_store.Store), canonical. No file: none. A file that cannot be read →
    cs.StoreError «entity memory not readable: .state/entities.json (<why>)»; one that is not JSON, is of another schema
    or not of the shape → «entity memory not valid: …». Never reset silently."""
    path = os.path.join(store.state_dir, FILE)
    if not os.path.lexists(path):
        return empty_memory()
    try:
        raw = cs.read_text(path, timeout=timeout)
    except FileNotFoundError:
        return empty_memory()
    except (OSError, UnicodeDecodeError, cs.StoreError) as e:
        raise _error("not readable", getattr(e, "strerror", None) or e)
    try:
        return _clean(json.loads(raw))
    except ValueError as e:
        raise _error("not valid", e)


def save_memory(store, mem):
    """Write your answers (canonical, indented, atomic) and return what was written; a memory of the wrong shape →
    cs.StoreError, nothing written."""
    try:
        clean = _clean(mem)
    except ValueError as e:
        raise _error("not valid", e)
    cs.atomic_write(os.path.join(store.state_dir, FILE), json.dumps(clean, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
    cs.remove_stale_tmp(store.state_dir)
    return clean


def answer(mem, a, b, same, day):
    """Record «a and b are the same» (`same`) or «not the same» in a loaded memory, in place: the opposite answer goes.
    True when the memory changed."""
    pair = _pair(a, b)
    mine, other = ("same", "not_same") if same else ("not_same", "same")
    before = len(mem[other])
    mem[other] = [x for x in mem[other] if _pair(x[0], x[1]) != pair]
    changed = len(mem[other]) != before
    if not any(_pair(x[0], x[1]) == pair for x in mem[mine]):
        mem[mine].append(pair + [day])
        changed = True
    return changed


# ------------------------------------------------------------------ cards
def _stem(path):
    name = path.rsplit("/", 1)[-1]
    return name[:-3] if name.lower().endswith(".md") else name


def _card(d, origin):
    """A card as the registry keeps it, from Index.cards() (origin "index") or a local index (origin "local")."""
    return {"path": N(d["path"]), "source": d.get("source") or "", "origin": origin, "kind": d["kind"],
            "label": d.get("label") or d.get("title") or _stem(d["path"]), "emails": list(d.get("emails") or []),
            "team": d.get("team") or "", "role": d.get("role") or "", "slug": d.get("slug") or "",
            "aliases": list(d.get("aliases") or []), "key": d.get("key") or "", "bridges": dict(d.get("bridges") or {}),
            "prefixes": list(d.get("prefixes") or []), "sensitive": bool(d.get("sensitive")), "date": d.get("date") or "",
            "home": True}


def local_cards(sctx, own_paths):
    """(cards, notes) of every registered local index: the notes of a card's type whose index name the own index does
    not hold (`own_paths`) and the search keeps — their identity from the frontmatter JSON alone; a sensitive note by the
    rules of the search. An index that cannot be opened → `<id> не відповів — без нього`; one of another shape (no
    `notes` table with a `path` column) → `індекс <id> має незнайому схему — без нього` (cs_.SCHEMA_NOTE)."""
    cards, notes = [], []
    vaults = sctx.get("vaults") or []
    for src in cs_.sources(sctx["text"], sctx["repos"], ("local",)):
        try:
            con = sqlite3.connect("file:%s?mode=ro" % urllib.parse.quote(src["path"]), uri=True, timeout=cs_.OPEN_S)
        except sqlite3.Error:
            notes.append(cs_.SILENT_NOTE % src["id"])
            continue
        until = time.monotonic() + cs_.SOURCE_S
        con.set_progress_handler(lambda: time.monotonic() > until, 10000)
        try:
            cols = cs_._columns(con, "notes")
            if "path" not in cols:
                notes.append(cs_.SCHEMA_NOTE % src["id"])
                continue
            fm_col = next((c for c in ("fm_json", "frontmatter_json") if c in cols), None)
            pick = ["path"] + [c for c in ("type", "title", "date", "mtime") if c in cols] + ([fm_col] if fm_col else [])
            rows = con.execute("SELECT %s FROM notes" % ", ".join(pick)).fetchall()
            folder = cs_._local_root(con)
        except sqlite3.Error as e:
            notes.append((cs_.SILENT_NOTE if cs_._busy(e) else cs_.SCHEMA_NOTE) % src["id"])
            continue
        finally:
            con.close()
        root = ci.Root(src["id"], folder) if folder else None
        for r in rows:
            row = dict(zip(pick, r))
            if not cs_._usable(row["path"]):
                continue
            rel = cs_._local_name(row["path"], vaults, folder, root)
            if not cs_._usable(rel) or rel in own_paths or not cs_._keep(sctx, rel):
                continue
            fm = {str(k).lower(): v for k, v in cs_._fm(row.get(fm_col)).items()} if fm_col else {}
            if row.get("type") and not fm.get("type"):
                fm["type"] = row["type"]
            title = ci._text(row.get("title")) or ci._text(fm.get("title")) or _stem(rel)
            ident = ci.identity_of(rel, fm, title)
            if not ident:
                continue
            ntype = (ci._text(fm.get("type")) or "").lower()
            ident.update(path=rel, source=src["id"], title=title,
                         sensitive=ci.sensitive_of(fm) or ntype in ci.PEOPLE_TYPES or ci.one_on_one(rel, title),
                         date=cs_._first_date(fm, ci.DATE_KEYS) or cs_._file_day(row.get("date") or row.get("mtime")) or "")
            cards.append(_card(ident, "local"))
    return cards, notes


# ------------------------------------------------------------------ links
class Resolver:
    """The note a link's target means (plan C5, the rules of `ctx search --get`). `notes`: {path: title, or {title,
    source, sensitive, date}} — every note a link may land on; `plugin_prefixes`: the index names of the plugin folders."""

    def __init__(self, notes, plugin_prefixes=()):
        self.meta = {}
        for p, v in (notes or {}).items():
            self.meta[N(p)] = dict(v) if isinstance(v, dict) else {"title": v}
        self.prefixes = [N(p).strip("/") for p in plugin_prefixes or () if p]
        self.exact, self.tails, self.names = {}, {}, {}
        for p in self.meta:
            cf = p.casefold()
            self.exact.setdefault(cf, []).append(p)
            parts = cf.split("/")
            for i in range(1, len(parts)):
                self.tails.setdefault("/".join(parts[i:]), []).append(p)
            self.names.setdefault(ci.name_key(p), []).append(p)

    @staticmethod
    def clean(target):
        """A target as a path to look up: `[[…]]`, `|label`, `#anchor`, `\\`, `./` and `../` gone."""
        t = N(target or "").strip()
        if t.startswith("[[") and t.endswith("]]"):
            t = t[2:-2]
        t = t.split("|", 1)[0].split("#", 1)[0].replace("\\", "/").strip()
        while t.startswith(("../", "./")):
            t = t[3:] if t.startswith("../") else t[2:]
        return t.lstrip("/")

    @staticmethod
    def _one(found):
        found = sorted(set(found or ()))
        return None if not found else found[0] if len(found) == 1 else found

    def resolve(self, target):
        """The path of the one note `target` means, a sorted list when several do, None when none does."""
        t = self.clean(target)
        if not t:
            return None
        base = t[:-3] if t.lower().endswith(".md") else t
        want = (base + ".md").casefold()
        if want in self.exact:
            return self._one(self.exact[want])
        for pre in self.prefixes:
            hit = self.exact.get((pre + "/" + base + ".md").casefold())
            if hit:
                return self._one(hit)
        if "/" in base:
            return self._one(self.tails.get(want))
        return self._one(self.names.get(ci.name_key(base)))

    def title(self, path):
        return (self.meta.get(path) or {}).get("title") or _stem(path)


# ------------------------------------------------------------------ the registry
def _rank(card):
    """The order of a card in its entity: a core's card first, then yours, then a local index's; a page a work card
    links to (no card itself) last."""
    if not card.get("home"):
        return 3
    if card["origin"] == "local":
        return 2
    return 1 if card["source"] == "own" else 0


def _names(card):
    return [x for x in (card["label"], _stem(card["path"]), card.get("slug")) if x]


def _norms(card):
    return {pb.norm_team(x) for x in _names(card) + list(card.get("aliases") or [])} - {""}


def _same_person(a, b):
    return any(pb.same_person(x, y) for x in _names(a) for y in _names(b))


def _corroborated(a, b):
    """Does nothing say no to a bridge between two cards of one kind (plan C3)?"""
    if a["kind"] == "person":
        if a["emails"] and b["emails"]:
            return bool(set(a["emails"]) & set(b["emails"]))
        return _same_person(a, b)
    if a["kind"] == "work":
        return bool(a["key"]) and a["key"] == b["key"]
    return bool(_norms(a) & _norms(b))


def _person_bucket(card):
    """The cards `same_person` may join share this: their longest name token, its first five letters when longer."""
    out = set()
    for x in _names(card):
        toks = pb.norm_name(x).split()
        if toks:
            t = max(toks, key=len)
            out.add(t if len(t) <= 4 else t[:5])
    return out


class Registry:
    def __init__(self, entities, by_path, pairs, resolver):
        self.entities, self._by_path, self._pairs, self.resolver = entities, by_path, pairs, resolver

    def of(self, path):
        """The entity a card (or a page a work card links to) belongs to, or None."""
        return self._by_path.get(N(path or ""))

    def pairs(self):
        """The open pairs «maybe the same»: (card, card), each once."""
        return list(self._pairs)

    def find(self, query, kind=None):
        """([entity], how) for a request (plan C14): an e-mail, a Jira key (any case), a path or a link, a name (a file's
        name, a title, an alias, a slug), then a card alike (`same_person` for people, the team's normalised names for
        the rest); `kind` keeps one kind. how: email | key | path | name | similar | none (key also when no entity holds
        that key: then the caller looks for mentions)."""
        q = N(query or "").strip()
        ents = [e for e in self.entities if kind is None or e["kind"] == kind]

        def out(found, how):
            seen, res = set(), []
            for e in found:
                if e["id"] not in seen:
                    seen.add(e["id"])
                    res.append(e)
            return res, how

        if not q:
            return [], "none"
        low = q.lower()
        if "@" in low and ci._EMAIL.match(low):
            return out([e for e in ents if any(low in c["emails"] for c in e["cards"])], "email")
        if ci.ISSUE_KEY.fullmatch(q.upper()):
            return out([e for e in ents if e["key"] == q.upper()], "key")
        if "/" in q or low.endswith(".md") or q.startswith("[["):
            hit = self.resolver.resolve(q)
            paths = [hit] if isinstance(hit, str) else hit or []
            found = [self.of(p) for p in paths if self.of(p) and (kind is None or self.of(p)["kind"] == kind)]
            if found:
                return out(found, "path")
            q = Resolver.clean(q)
        nk = ci.name_key(q)
        found = [e for e in ents for c in e["cards"]
                 if nk in {ci.name_key(x) for x in _names(c) + list(c.get("aliases") or [])}]
        if found:
            return out(found, "name")
        norm = pb.norm_team(q)
        found = [e for e in ents for c in e["cards"] if c.get("home")
                 and (any(pb.same_person(q, x) for x in _names(c)) if c["kind"] == "person" else norm in _norms(c))]
        return out(found, "similar") if found else ([], "none")


def build(cards, mem, resolver):
    """The registry of `cards` (plan C3–C4, C7): your `same` answers, then the e-mails, then the bridges by shape join
    them — any join that would put a pair you answered `not-same` in one entity is skipped. A work card's bridge to a
    note of another source whose name carries the same key makes that note a home of the work (never its id). A bridge
    between two cards of one kind (a person excepted) that nothing corroborates relates them instead."""
    by_path, order = {}, []
    for c in cards:
        if c["path"] not in by_path:
            by_path[c["path"]] = c
            order.append(c)
    parent = {p: p for p in by_path}
    members = {p: {p} for p in by_path}
    apart = [tuple(_pair(x[0], x[1])) for x in mem.get("not_same", [])]
    answered = {tuple(_pair(x[0], x[1])) for w in ("same", "not_same") for x in mem.get(w, [])}

    def find(p):
        while parent[p] != p:
            parent[p] = parent[parent[p]]
            p = parent[p]
        return p

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra == rb:
            return
        for x, y in apart:
            if x in by_path and y in by_path and {find(x), find(y)} == {ra, rb}:
                return
        if len(members[ra]) < len(members[rb]):
            ra, rb = rb, ra
        parent[rb] = ra
        members[ra] |= members.pop(rb)

    for x in mem.get("same", []):
        a, b = _pair(x[0], x[1])
        if a in by_path and b in by_path and by_path[a]["kind"] == by_path[b]["kind"]:
            union(a, b)
    groups = {}
    for c in sorted(order, key=lambda c: (_rank(c), c["path"])):
        if c["kind"] == "person":
            for e in c["emails"]:
                groups.setdefault(e, []).append(c["path"])
    for paths in groups.values():
        for i in range(len(paths)):
            for j in range(i + 1, len(paths)):
                union(paths[i], paths[j])
    related, pages = [], {}
    for c in order:
        for target in c["bridges"].values():
            hit = resolver.resolve(target)
            if not isinstance(hit, str) or hit == c["path"]:
                continue
            o = by_path.get(hit)
            if o is not None:
                if o["kind"] != c["kind"] or o["source"] == c["source"]:
                    continue
                if _corroborated(c, o):
                    union(c["path"], o["path"])
                elif c["kind"] not in ("person", "work"):
                    related.append((c["path"], o["path"]))
            elif c["kind"] == "work" and c["key"]:
                meta = resolver.meta.get(hit) or {}
                title = meta.get("title") or _stem(hit)
                if meta.get("source") != c["source"] and (ci.ISSUE_KEY.search(_stem(hit)) or ci.ISSUE_KEY.search(title)) \
                        and c["key"] in {m.group(0) for m in ci.ISSUE_KEY.finditer(_stem(hit) + " " + title)}:
                    pages.setdefault(c["path"], []).append({
                        "path": hit, "source": meta.get("source") or "", "origin": "index", "kind": "work",
                        "label": title, "emails": [], "team": "", "role": "", "slug": "", "aliases": [], "key": c["key"],
                        "bridges": {}, "prefixes": [], "sensitive": bool(meta.get("sensitive")),
                        "date": meta.get("date") or "", "home": False})
    entities, of = [], {}
    for root, paths in sorted(members.items(), key=lambda kv: min(kv[1])):
        cs_list = sorted((by_path[p] for p in paths), key=lambda c: (_rank(c), c["path"]))
        for c in list(cs_list):
            for page in pages.get(c["path"], []):
                if page["path"] not in {x["path"] for x in cs_list} and page["path"] not in by_path:
                    cs_list.append(page)
        head = cs_list[0]
        ent = {"id": head["path"], "kind": head["kind"], "label": head["label"],
               "key": next((c["key"] for c in cs_list if c["key"]), ""), "cards": cs_list, "related": [], "maybe": []}
        entities.append(ent)
        for c in cs_list:
            of.setdefault(c["path"], ent)
    for a, b in related:
        ea, eb = of[a], of[b]
        if ea is not eb:
            if b not in {c["path"] for c in ea["related"]}:
                ea["related"].append(by_path[b])
            if a not in {c["path"] for c in eb["related"]}:
                eb["related"].append(by_path[a])
    pairs, seen = [], set()
    by_kind = {}
    for c in order:
        if c["kind"] == "person":
            for k in _person_bucket(c):
                by_kind.setdefault(("person", k), []).append(c)
        else:
            for k in _norms(c):
                by_kind.setdefault((c["kind"], k), []).append(c)
    for (kind, _), group in sorted(by_kind.items(), key=lambda kv: kv[0]):
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                a, b = group[i], group[j]
                key = tuple(_pair(a["path"], b["path"]))
                if key in seen or key in answered or a["source"] == b["source"] or of[a["path"]] is of[b["path"]]:
                    continue
                if kind == "person" and not _same_person(a, b):
                    continue
                seen.add(key)
                pairs.append((by_path[key[0]], by_path[key[1]]))
                of[a["path"]]["maybe"].append(b)
                of[b["path"]]["maybe"].append(a)
    return Registry(entities, of, pairs, resolver)


def known_prefixes(cards):
    """The Jira project prefixes the cards name: a team's or a mission's prefixes, a work card's key (plan C6)."""
    out = set()
    for c in cards:
        out.update(c.get("prefixes") or [])
        if c.get("key"):
            out.add(c["key"].rsplit("-", 1)[0])
    return out


def load(sctx, idx, mem):
    """(Registry, notes) of a search context and an Index already refreshed: the own index's cards, the cards of the
    local indexes it does not hold, your answers `mem`; `notes` — the lines to show (an index that could not be read, a
    local index that did not answer or has another shape)."""
    notes = []
    own = idx.cards()
    if idx.problem:
        notes.append(idx.problem)
    metas = {}
    for n in idx.notes():
        metas[N(n["path"])] = {"title": n["title"], "source": n["source"], "sensitive": n["sensitive"], "date": n["date"]}
    local, lnotes = local_cards(sctx, set(metas))
    notes.extend(lnotes)
    for c in local:
        metas[c["path"]] = {"title": c["label"], "source": c["source"], "sensitive": c["sensitive"], "date": c["date"]}
    vaults = sctx.get("vaults") or []
    prefixes = [ci.rel_path(r["path"], vaults, r) for r in sctx.get("roots") or [] if r.get("source") == "own"]
    resolver = Resolver(metas, prefixes)
    return build([_card(d, "index") for d in own] + local, mem, resolver), notes
