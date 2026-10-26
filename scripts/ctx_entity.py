#!/usr/bin/env python3
"""Grow PM — who is who: one registry of the people, teams, missions, modules, metrics and work your notes, the cores and
a local index of yours hold (since v3.18.0).

A card is a note whose type makes it one (ctx_index.ENTITY_KINDS): a person note of your layer, a core's registry card,
a card another team keeps that a local index of yours holds. The registry joins the cards of one entity by three keys, the strongest
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
- run, pairs_result, render     `ctx entity <request>` and `ctx entity pairs`: the index refreshed, the entity (or the
                                several, or a Jira key's mentions), who links to it — a sensitive note outside the People
                                contour as its title and path with ` · sensitive`, never its field or text (plan C8) —,
                                and the lines to print. Never a note's text, never a field beyond the identity.

Reads the index (ctx_index), a registered local index (mode=ro) and `.state/entities.json`; writes the index (`run`
refreshes it) and that file (`save_memory`, for the writing commands of ctx.py) — nothing else. Stdlib only.
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
import ctx_slots as sl  # noqa: E402
import provider_bundle as pb  # noqa: E402

N = cc.N
SCHEMA = "context-entity-memory/1"
FILE = "entities.json"
WHERE = ".state/" + FILE
_KEYS = ("schema", "same", "not_same")
_DAY = re.compile(r"\d{4}-\d{2}-\d{2}\Z")
KINDS = ("person", "team", "mission", "module", "metric", "work")
PEOPLE_SKILLS = ("goal-setter", "one-on-one", "performance-review", "hiring-designer", "offboarding-guide",
                 "delegation-coach")      # data-policy.md: the People contour sees a sensitive line's field (C8)
SHOWN = 20                              # the lines of who links to an entity, or mentions a key, at most
SEVERAL = 5                             # the entities a request that names several lists, at most
UNKNOWN = "Не знаю такої сутності: «%s»"
UNKNOWN_YET = "Поки не знаю «%s» — %s"
SIMILAR = "схоже на «%s» — не точний збіг:"
MENTION = "%s — картки немає, згадується в %d нотатках:"
UNREAD_MEMORY = "пам'ять сутностей не прочитано (%s) — без твоїх відповідей"
NOT_APPLIED = "твою відповідь same %s ↔ %s від %s не застосовано: %s"
NOT_APPLIED_WHY = {"not-same": "її заперечує твоє not-same", "kinds": "картки різних видів"}
NOT_READ = "Базу не прочитано: %s"
HINT_SCHEMA = "%s: підказок немає — незнайома схема"        # v3.19.0: a local index whose entities/edges are not (key,
                                                            # kind, path) / (src, dst, kind)
HINT = "підказка %s"
HINT_TABLE = "%s: таблиця %s незнайомої схеми — без неї"
HINT_CUT = "%s: підказки прочитано не повністю (%s)"
EDGE_LINKS = ("wikilink", "link", "embed")       # a local index's edge kinds that are links (`fm:<field>` too)
BUSY_ANSWER = "індекс зайнятий — спробуй за хвилину; відповідь не збережено"
SLOT_WORDS = {"person.role": "роль", "person.team": "команда", "person.email": "e-mail", "team.members": "склад",
              "team.missions": "місії", "team.parent": "батьківська команда", "mission.teams": "команди",
              "mission.jira_projects": "проєкти Jira", "module.owner": "власник", "metric.owner": "власник"}


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
            "home": True, "fields": None if d.get("fields") is None else dict(d["fields"])}
                                    # fields: the card's slot fields (v3.19.0); None — the index has not read them yet


def local_cards(sctx, own_paths):
    """(cards, notes) of every registered local index: the notes of a card's type whose index name the own index does
    not hold (`own_paths`) and the search keeps — their identity from the frontmatter JSON alone; a sensitive note by the
    rules of the search. An index that cannot be opened → `<id> не відповів — без нього`; one of another shape (no
    `notes` table with a `path` column) → `індекс <id> має незнайому схему — без нього` (cs_.SCHEMA_NOTE)."""
    cards, notes = [], []
    vaults = sctx.get("vaults") or []
    own_folded = {p.casefold() for p in own_paths}    # one note under another case on a case-insensitive disk (v3.19.0)
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
            if not cs_._usable(rel) or rel.casefold() in own_folded or not cs_._keep(sctx, rel):
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


# ------------------------------------------------------------------ the hints of a local index (since v3.19.0, plan C10)
def _hint_sources(sctx, notes):
    """[(src id, connection, folder, root, has entities, has edges)] of every registered local index that keeps tables of
    its own entities (`entities(key, kind, path)`) or edges (`edges(src, dst, kind)`); one of neither says nothing, one
    whose table has other columns gets one line (HINT_SCHEMA) in `notes`. The caller closes the connections."""
    out = []
    for src in cs_.sources(sctx["text"], sctx["repos"], ("local",)):
        con = None
        try:
            con = sqlite3.connect("file:%s?mode=ro" % urllib.parse.quote(src["path"]), uri=True, timeout=cs_.OPEN_S)
            until = time.monotonic() + cs_.SOURCE_S
            con.set_progress_handler(lambda until=until: time.monotonic() > until, 10000)
            tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
            ents = "entities" in tables and {"key", "kind", "path"} <= set(cs_._columns(con, "entities"))
            edges = "edges" in tables and {"src", "dst", "kind"} <= set(cs_._columns(con, "edges"))
            odd = [t for t, ok in (("entities", ents), ("edges", edges)) if t in tables and not ok]
            if odd and not (ents or edges):
                notes.append(HINT_SCHEMA % src["id"])
            elif odd:
                notes.append(HINT_TABLE % (src["id"], odd[0]))
            if not (ents or edges):
                con.close()
                continue
            folder = cs_._local_root(con)
        except sqlite3.Error:
            if con is not None:
                con.close()
            continue                                  # local_cards says it did not answer
        out.append((src["id"], con, folder, ci.Root(src["id"], folder) if folder else None, ents, edges))
    return out


def _hint_pairs(sctx, reg, mem, notes):
    """Add to `reg` the pairs a local index's `entities` offer (plan C10): two cards of one kind the plugin keeps in two
    entities, under one key there, that you have not answered and that are no open pair yet — `hint`: the index's id.
    Never a merge: your `same` decides."""
    vaults = sctx.get("vaults") or []
    answered = {tuple(_pair(x[0], x[1])) for w in ("same", "not_same") for x in (mem or {}).get(w, [])}
    have = {tuple(_pair(a["path"], b["path"])) for a, b in reg._pairs}
    for sid, con, folder, root, ents, _ in _hint_sources(sctx, notes):
        try:
            rows = con.execute("SELECT key, path FROM entities").fetchall() if ents else []
        except sqlite3.Error:
            rows = []
        finally:
            con.close()
        groups = {}
        for key, path in rows:
            if not key or not cs_._usable(path):
                continue
            rel = cs_._local_name(path, vaults, folder, root)
            card = next((c for c in (reg.of(rel) or {}).get("cards", []) if c["path"] == rel and c.get("home", True)), None)
            if card and card not in groups.setdefault(key, []):
                groups[key].append(card)
        for cards in groups.values():
            for i in range(len(cards)):
                for j in range(i + 1, len(cards)):
                    a, b = cards[i], cards[j]
                    k = tuple(_pair(a["path"], b["path"]))
                    if a["kind"] != b["kind"] or reg.of(a["path"]) is reg.of(b["path"]) or k in answered or k in have \
                            or a["source"] == b["source"]:      # one source's two cards: never a pair (as build)
                        continue
                    if a["kind"] == "person":                   # two different e-mails are two people (v3.18.0)
                        ma = {m for c in reg.of(a["path"])["cards"] for m in c["emails"]}
                        mb = {m for c in reg.of(b["path"])["cards"] for m in c["emails"]}
                        if ma and mb and not ma & mb:
                            continue
                    have.add(k)
                    reg._pairs.append((a, b))
                    reg.hints[k] = sid
                    reg.of(a["path"])["maybe"].append(dict(b, mine=a["path"], hint=sid))
                    reg.of(b["path"])["maybe"].append(dict(a, mine=b["path"], hint=sid))


def local_edges(sctx, ent, own_paths, people=False, notes=None, cache=None):
    """The notes a local index's `edges` link to a card of `ent` from (plan C10): only a note the plugin's own index does
    not hold (its own links decide for its notes), never the store, a blocks file or a scratch folder (the search's
    rules), never the entity's own cards — {path, title, date, sensitive, via[, field]}, a sensitive one's field only for
    the People contour."""
    vaults = sctx.get("vaults") or []
    targets = {c["path"] for c in ent["cards"]}
    own = {p.casefold() for p in own_paths}
    out = {}
    cache = {} if cache is None else cache            # src id → {name: [dst]}: every dst mapped once per run
    for sid, con, folder, root, _, edges in _hint_sources(sctx, []):    # load() said what a schema lacks
        try:
            if not edges:
                continue
            name = lambda p_: cs_._local_name(p_, vaults, folder, root)   # noqa: E731
            if sid not in cache:
                by = cache[sid] = {}
                for (d,) in con.execute("SELECT DISTINCT dst FROM edges"):
                    if cs_._usable(d):
                        by.setdefault(name(d), []).append(d)
            dsts = [d for t in targets for d in cache[sid].get(t, ())]
            if not dsts:
                continue
            cols = cs_._columns(con, "notes")
            fm_col = next((c for c in ("fm_json", "frontmatter_json") if c in cols), None)
            pick = [c for c in ("title", "type", "date", "mtime") if c in cols] + ([fm_col] if fm_col else [])
            for src, kind in con.execute("SELECT src, kind FROM edges WHERE dst IN (%s)" % ",".join("?" * len(dsts)), dsts):
                if not (str(kind or "") in EDGE_LINKS or str(kind or "").startswith("fm:")):
                    continue                            # a mention or a typed key is no link (review M3)
                rel = name(src) if cs_._usable(src) else None
                if not rel or not cs_._usable(rel) or not cs_._keep(sctx, rel) or rel in targets or rel.casefold() in own \
                        or rel in out:
                    continue
                row = con.execute("SELECT %s FROM notes WHERE path = ?" % ", ".join(pick), (src,)).fetchone() if pick else None
                meta = dict(zip(pick, row)) if row else {}
                fm = {str(k).lower(): v for k, v in cs_._fm(meta.get(fm_col)).items()} if fm_col else {}
                title = ci._text(meta.get("title")) or ci._text(fm.get("title")) or _stem(rel)
                ntype = (ci._text(meta.get("type")) or ci._text(fm.get("type")) or "").lower()
                field = kind[3:] if str(kind or "").startswith("fm:") else ""
                d = _line({"path": rel, "title": title, "field": field,
                           "date": cs_._first_date(fm, ci.DATE_KEYS) or cs_._file_day(meta.get("date") or meta.get("mtime")) or "",
                           "sensitive": ci.sensitive_of(fm) or ntype in ci.PEOPLE_TYPES or ci.one_on_one(rel, title)}, people)
                if not d.get("field"):
                    d.pop("field", None)
                d["via"] = sid
                out[rel] = d
        except sqlite3.Error as e:
            if notes is not None:
                notes.append(HINT_CUT % (sid, cc.clip(str(e), 80)))
            continue
        finally:
            con.close()
    return list(out.values())


# ------------------------------------------------------------------ links
class Resolver:
    """The note a link's target means (plan C5, the rules of `ctx search --get`). `notes`: {path: title, or {title,
    source, sensitive, date}} — every note a link may land on; `plugin_prefixes`: the index names of the plugin folders."""

    def __init__(self, notes, plugin_prefixes=()):
        self.meta = {}
        for p, v in (notes or {}).items():
            self.meta[N(p)] = dict(v) if isinstance(v, dict) else {"title": v}
        self.prefixes = [N(p).strip("/") for p in plugin_prefixes or () if p]
        self.exact, self.tails, self.names, self.local = {}, {}, {}, set()
        for p in self.meta:
            cf = p.casefold()
            self.exact.setdefault(cf, []).append(p)
            parts = cf.split("/")
            for i in range(1, len(parts)):
                self.tails.setdefault("/".join(parts[i:]), []).append(p)
            self.names.setdefault(ci.name_key(p), []).append(p)
            if self.meta[p].get("origin") == "local":
                self.local.add(p)

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
        if "/" not in base:                     # a name: the own index's notes first, as --get looks (`_by_name`)
            hits = self.names.get(ci.name_key(base)) or []
            return self._one([p for p in hits if p not in self.local] or hits)
        for pre in self.prefixes:               # a path: the plugin folder's, then the end of a path (`_by_tail`)
            hit = self.exact.get((pre + "/" + base + ".md").casefold())
            if hit:
                return self._one(hit)
        return self._one(self.tails.get(want))

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


def _names_of(ent):
    """Every name an entity's cards carry: their titles, file names, slugs."""
    return list(dict.fromkeys(x for c in ent["cards"] for x in _names(c)))


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
    unread = None                        # load(): why the own index's cards were not read (busy, damaged), or None

    def __init__(self, entities, by_path, pairs, resolver, skipped=()):
        self.entities, self._by_path, self._pairs, self.resolver = entities, by_path, pairs, resolver
        self.skipped = list(skipped)     # your `same` answers that could not be applied: {cards, day, why}
        self.hints = {}                  # (path, path) → the local index whose `entities` offered the pair (v3.19.0)
        self.edge_cache = {}             # a local index's edges, their targets mapped once (local_edges)

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
        if "/" in Resolver.clean(q) or Resolver.clean(q).lower().endswith(".md"):
            hit = self.resolver.resolve(q)       # a path names its note or nothing — never another note by its name
            paths = [hit] if isinstance(hit, str) else hit or []
            return out([self.of(p) for p in paths if self.of(p) and (kind is None or self.of(p)["kind"] == kind)], "path")
        if q.startswith("[["):
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
        """Join the entities of a and b; False when a `not-same` answer keeps them apart."""
        ra, rb = find(a), find(b)
        if ra == rb:
            return True
        for x, y in apart:
            if x in by_path and y in by_path and {find(x), find(y)} == {ra, rb}:
                return False
        if len(members[ra]) < len(members[rb]):
            ra, rb = rb, ra
        parent[rb] = ra
        members[ra] |= members.pop(rb)
        return True

    skipped = []
    for x in sorted(mem.get("same", []), key=lambda x: (x[2], x[0], x[1]), reverse=True):   # the newest answer first
        a, b = _pair(x[0], x[1])
        if a not in by_path or b not in by_path:
            continue
        if by_path[a]["kind"] != by_path[b]["kind"]:
            skipped.append({"cards": [a, b], "day": x[2], "why": "kinds"})
        elif not union(a, b):
            skipped.append({"cards": [a, b], "day": x[2], "why": "not-same"})
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
            if c["kind"] == "work" and c["key"]:      # one Jira key in two sources (spec §3: the key of work)
                by_kind.setdefault(("work", "key:" + c["key"]), []).append(c)
    for (kind, _), group in sorted(by_kind.items(), key=lambda kv: kv[0]):
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                a, b = group[i], group[j]
                key = tuple(_pair(a["path"], b["path"]))
                if key in seen or key in answered or a["source"] == b["source"] or of[a["path"]] is of[b["path"]]:
                    continue
                if kind == "person" and not _same_person(a, b):
                    continue
                if kind == "person":                 # two different e-mails are two people (v3.18.0 acceptance)
                    ma = {m for c in of[a["path"]]["cards"] for m in c["emails"]}
                    mb = {m for c in of[b["path"]]["cards"] for m in c["emails"]}
                    if ma and mb and not ma & mb:
                        continue
                seen.add(key)
                pairs.append((by_path[key[0]], by_path[key[1]]))
                of[a["path"]]["maybe"].append(dict(b, mine=a["path"]))    # `mine`: the card of this entity that paired
                of[b["path"]]["maybe"].append(dict(a, mine=b["path"]))
    return Registry(entities, of, pairs, resolver, skipped)


def known_prefixes(cards):
    """The Jira project prefixes the cards name: a team's or a mission's prefixes, a work card's key (plan C6)."""
    out = set()
    for c in cards:
        out.update(c.get("prefixes") or [])
        if c.get("key"):
            out.add(c["key"].rsplit("-", 1)[0])
    return out


def load(sctx, idx, mem, hints=True):
    """(Registry, notes) of a search context and an Index already refreshed: the own index's cards, the cards of the
    local indexes it does not hold, your answers `mem`; `notes` — the lines to show (an index that could not be read, a
    local index that did not answer or has another shape)."""
    notes = []
    own = idx.cards()
    unread = idx.problem                     # the cards' own read: busy or damaged, the index has not answered
    if unread:
        notes.append(unread)
    metas = {}
    for n in idx.notes():
        metas[N(n["path"])] = {"title": n["title"], "source": n["source"], "sensitive": n["sensitive"], "date": n["date"]}
    unread_fields = {N(d["path"]) for d in own if d.get("fields") is None}
    local, lnotes = local_cards(sctx, idx.identity_paths() - unread_fields)   # a card the own index has not read yet
    notes.extend(lnotes)
    by_path = {c["path"]: c for c in local}
    for d in own:                                   # a card whose slot fields no walk read (its file evicted since the
        twin = by_path.pop(N(d["path"]), None) if d.get("fields") is None else None   # upgrade): the same note's
        if twin is not None:                        # frontmatter in a local index gives them (final review M4)
            d["fields"] = twin["fields"]
    local = list(by_path.values())
    for c in local:
        metas[c["path"]] = {"title": c["label"], "source": c["source"], "sensitive": c["sensitive"], "date": c["date"],
                            "origin": "local"}
    vaults = sctx.get("vaults") or []
    prefixes = [ci.rel_path(r["path"], vaults, r) for r in sctx.get("roots") or [] if r.get("source") == "own"]
    resolver = Resolver(metas, prefixes)
    reg = build([_card(d, "index") for d in own] + local, mem, resolver)
    reg.unread = unread
    if hints:
        _hint_pairs(sctx, reg, mem, notes)
    return reg, notes


# ------------------------------------------------------------------ `ctx entity`
def _line(row, people):
    """One note that links to an entity or mentions a key: {path, title, date, sensitive[, field]} — the field (where the
    link stands, "" for the text) only when the note is not sensitive or the reader is the People contour (C8)."""
    d = {"path": row["path"], "title": row.get("title") or _stem(row["path"]), "date": (row.get("date") or "")[:10],
         "sensitive": bool(row.get("sensitive"))}
    if not d["sensitive"] or people:
        d["field"] = row.get("field", "")
    if row.get("via"):
        d["via"] = row["via"]
    return d


def _newest(items):
    return sorted(items, key=lambda d: (d["date"], d["path"]), reverse=True)


def backlinks(idx, reg, ent, people=False, extra=()):
    """{count, items}: the notes that link to a card (or a home page) of `ent` — each link's target resolved as `--get`
    would, so a note of the same name elsewhere is never counted —, the entity's own cards left out; then `extra` (the
    edges of a local index, local_edges) for notes not among them; newest first, at most SHOWN items, `count` all."""
    homes = {c["path"] for c in ent["cards"]}
    found = {}
    for row in idx.links_to({ci.name_key(p) for p in homes}):
        if row["path"] in homes or row["path"] in found:
            continue
        hit = reg.resolver.resolve(row["target"])
        if isinstance(hit, str) and hit in homes:      # several notes answer the link: it counts for none of them
            found[row["path"]] = _line(row, people)
    for d in extra:
        found.setdefault(d["path"], d)
    items = _newest(found.values())
    return {"count": len(items), "items": items[:SHOWN]}


def mentions(idx, key, skip=(), people=False):
    """{count, items}: the notes that carry the Jira key `key`, those of `skip` left out; newest first, at most SHOWN."""
    found = {}
    for row in idx.mentions({key}):
        if row["path"] not in skip and row["path"] not in found:
            found[row["path"]] = _line(dict(row, field=""), people)
    items = _newest(found.values())
    return {"count": len(items), "items": items[:SHOWN]}


def _public_card(c):
    return {"path": c["path"], "source": c["source"], "label": c["label"], "emails": c["emails"], "team": c["team"],
            "role": c["role"], "sensitive": c["sensitive"], "home": c.get("home", True)}


def _brief(c):
    return {"path": c["path"], "label": c["label"], "source": c["source"], "kind": c["kind"]}


def _prepare(sctx, store, budget):
    """(idx, registry, notes, read, pending): the index refreshed (as `ctx search` does), your answers, the registry.
    `read` — did any base answer (a built own index, or a card from a local index)."""
    notes, pending = [], 0
    idx = ci.Index(sctx["home"])
    idx.busy_once = True                 # v3.20.0: a busy index is said once, not waited for at every read
    built = None
    if sctx.get("roots"):
        done, why = cs_._refresh(idx, sctx, ci.REFRESH_S if budget is None else budget, notes)
        if why and ci._busy(why):
            idx.probe()                  # held by another connection: the reads of this run do not wait for it
        pending = (done or {}).get("pending") or 0
        if why:
            notes.append(cs_.REFRESH_NOTE % why)
        built = idx.built()
        if built is False:
            notes.append(cs_.BUILDING_NOTE if idx.lock_held() or (done or {}).get("locked")
                         else cs_.NO_INDEX_NOTE % (why or "збудуй його: ctx index rebuild"))
        if pending:
            notes.append(cs_.PENDING_NOTE % pending)
    mem = empty_memory()
    if store is not None and store.exists():
        try:
            mem = load_memory(store, timeout=cs_.OPEN_S)
        except cs.StoreError as e:
            notes.append(UNREAD_MEMORY % e)
    reg, more = load(sctx, idx, mem)
    notes.extend(n for n in more if n not in notes)
    notes.extend(NOT_APPLIED % (s["cards"][0], s["cards"][1], s["day"], NOT_APPLIED_WHY[s["why"]]) for s in reg.skipped)
    read = (built is True and not reg.unread) or any(c["origin"] == "local" for e in reg.entities for c in e["cards"])
    return idx, reg, notes, read, pending


def run(sctx, query, kind=None, skill=None, store=None, budget=None, slots=None, prepared=None, records=None):
    """`ctx entity <request>` (plan C13–C14): {command, query, how, entities, mention, notes, read, pending}. One entity
    → its cards (identity only), related, maybe, its slots (v3.19.0, ctx_eslots — `slots`: the ids asked for, then
    nothing but them: no backlinks, no mentions), backlinks (with a local index's edges, plan C10), mentions (a work
    entity's key); several → at most SEVERAL of them, without backlinks; a Jira key no card holds → its mentions, when
    its prefix is known or a /browse/ link names it; `read` False → no base answered (the caller exits 5). Refreshes the
    index (`prepared`: what _prepare gave, for several requests at once); writes nothing else."""
    import ctx_eslots as es     # it builds on this module: imported here, not at the top
    idx, reg, notes, read, pending = prepared or _prepare(sctx, store, budget)
    notes = list(notes)
    people = skill in PEOPLE_SKILLS
    found, how = reg.find(query, kind)
    out = {"command": "entity", "query": query, "how": how, "entities": [], "mention": None, "notes": notes,
           "read": read, "pending": pending, "unread": reg.unread}
    for e in found[:SEVERAL]:
        one = {"id": e["id"], "kind": e["kind"], "label": e["label"], "key": e["key"],
               "cards": [_public_card(c) for c in e["cards"]], "related": [_brief(c) for c in e["related"]],
               "maybe": [dict(_brief(c), mine=c["mine"], **({"hint": c["hint"]} if c.get("hint") else {}))
                         for c in e["maybe"]]}
        if len(found) == 1:
            one["slots"] = es.slots_of(reg, idx, e, sl.load_catalogue(), sctx, people=people, only=slots or None,
                                       records=(lambda ent: records(reg).get(ent["id"], {})) if records else None)
            if idx.problem and idx.problem not in notes:   # a busy index: a section's members are missing (review M6)
                notes.append(idx.problem)
            if slots:
                one["slots_asked"] = list(slots)          # one of another kind is «—» too (review M2)
                out["entities"].append(one)
                continue
            extra = local_edges(sctx, e, {N(p) for p in idx.paths() or ()}, people, notes, cache=reg.edge_cache)
            one["backlinks"] = backlinks(idx, reg, e, people, extra)
            if idx.problem and idx.problem not in notes:      # a busy index: the lines are missing, and the user is told
                notes.append(idx.problem)
            one["mentions"] = mentions(idx, e["key"], {c["path"] for c in e["cards"]}, people) if e["key"] else \
                {"count": 0, "items": []}
            if idx.problem and idx.problem not in notes:
                notes.append(idx.problem)
        out["entities"].append(one)
    out["several"] = len(found)
    if how == "key" and not found and not reg.find(query)[0]:     # no card of any kind holds the key
        key = N(query).strip().upper()
        rows = idx.mentions({key})
        prefix = key.rsplit("-", 1)[0]
        if rows and (prefix in known_prefixes([c for e in reg.entities for c in e["cards"]]) or any(r["browse"] for r in rows)):
            out["mention"] = dict(mentions(idx, key, (), people), key=key)
    return out


def run_many(sctx, queries, kind=None, skill=None, store=None, budget=None, slots=None, records=None):
    """`ctx entity --q A --q B …` (v3.19.0, plan C9c): the index refreshed once, one `run` per request —
    {command, requests: [run result], notes, read}."""
    prepared = _prepare(sctx, store, budget)
    reqs = [run(sctx, q, kind=kind, skill=skill, slots=slots, prepared=prepared, records=records) for q in queries]
    return {"command": "entity", "requests": reqs, "notes": list(prepared[2]), "read": prepared[3]}


def pairs_result(sctx, kind=None, store=None, budget=None):
    """`ctx entity pairs`: {command, action, pairs: [{a, b[, hint]}], count, notes, read} — every open «maybe the same»
    pair; `hint` — the local index whose `entities` offered it (v3.19.0)."""
    _, reg, notes, read, _ = _prepare(sctx, store, budget)
    pairs = [dict({"a": _brief(a), "b": _brief(b)}, **({"hint": reg.hints[tuple(_pair(a["path"], b["path"]))]}
                                                       if tuple(_pair(a["path"], b["path"])) in reg.hints else {}))
             for a, b in reg.pairs() if kind is None or a["kind"] == kind]
    return {"command": "entity", "action": "pairs", "pairs": pairs, "count": len(pairs), "notes": notes, "read": read}


def _plain(v):
    """A frontmatter value as it reads: a wiki link as its label (else its target's name)."""
    s = N(v or "").strip()
    m = ci._WIKI.fullmatch(s)
    if m:
        target, _, label = ci._link_parts(m.group(1))
        return label or _stem(target)
    return s


def _values(cards, field):
    """The values of `field` over the cards, each once; when they differ, each with the source that says it."""
    seen = []
    for c in cards:
        vals = c[field] if isinstance(c[field], list) else [c[field]]
        for v in vals:
            v = _plain(v) if field != "emails" else v
            if v and v not in [x for x, _ in seen]:
                seen.append((v, c["source"]))
    if len(seen) <= 1:
        return ", ".join(v for v, _ in seen)
    return ", ".join("%s (%s)" % (v, s) for v, s in seen)


def _note_line(d):
    return "%s — %s%s%s%s%s" % (d["title"], d["path"], " · " + d["date"] if d["date"] else "",
                                " · поле " + d["field"] if d.get("field") else "", " · sensitive" if d["sensitive"] else "",
                                " · " + d["via"] if d.get("via") else "")


def _who(o):
    """An origin in words: yours, a repository's or a local index's id, or what it was derived from."""
    if o["level"] == "derived":
        return "виведене (%s%s)" % (o["path"], ", спірне" if o.get("contested") else "")
    return "твоє" if o["level"] == "mine" else o["source"]


def _where(o):
    return " · ".join(x for x in (_who(o) if o["level"] != "derived" else "виведене", o["path"], (o.get("date") or "")[:10])
                      if x)


def _row(text):
    """An item's row as it reads: a link as its label."""
    return ci._WIKI.sub(lambda m: _plain("[[%s]]" % m.group(1).replace("\\|", "|")), text).strip()


def _slot_lines(slots):
    """The lines of an entity's slots (v3.19.0): a value with its origin and «також», a list one item a line."""
    lines = []
    for sid, a in slots.items():
        name = SLOT_WORDS.get(sid, sid)
        if a["kind"] == "value":
            line = "    %s: %s (%s)" % (name, a["value"], _where(a["origin"]))
            if a.get("diverges"):
                line += " · різні значення: " + " · ".join(a["diverges"])
            if a.get("also"):
                line += " · також: " + ", ".join("%s (%s)" % (x["value"], _where(x)) for x in a["also"])
            if a.get("unread"):
                line += " · не прочитано: " + ", ".join(a["unread"])
            lines.append(line)
            continue
        lines.append("    %s (%d):%s" % (name, a["count"], " не прочитано: " + ", ".join(a["unread"]) if a.get("unread") else ""))
        for it in a["items"][:SHOWN]:
            rows = sorted(it.get("rows") or (), key=lambda r: {"mine": 0, "repo": 1, "local": 2}.get(r["level"], 3))
            row = _row(rows[0]["text"]) if rows else ""     # the strongest source's row: yours first (review I3)
            lines.append("      %s — %s%s%s" % (it["label"], " · ".join(_who(o) for o in it["origins"]),
                                              " · лише виведене" if it.get("derived_only") else "",
                                              " · «%s»" % row if row and row != it["label"] else ""))
            for r in rows[1:]:
                if _row(r["text"]) != row:
                    lines.append("        також: «%s» (%s)" % (_row(r["text"]), "твоє" if r["level"] == "mine" else r["source"]))
        if a["count"] > SHOWN:
            lines.append("      ще %d" % (a["count"] - SHOWN))
    return lines


def render(res):
    """The human lines of `run` / `run_many` / `pairs_result`."""
    if "requests" in res:
        blocks = ["\n".join(res.get("notes") or [])] if res.get("notes") else []
        for r in res["requests"]:
            blocks.append("— «%s»\n" % r["query"] + render(dict(r, notes=[n for n in r["notes"] if n not in res["notes"]])).rstrip("\n"))
        return "\n\n".join(blocks) + "\n"
    lines = list(res.get("notes") or [])
    if res.get("action") == "pairs":
        for p in res["pairs"]:
            lines.append("можливо той самий: %s ↔ %s%s — ctx entity same|not-same \"%s\" \"%s\""
                         % (p["a"]["path"], p["b"]["path"], " (%s)" % (HINT % p["hint"]) if p.get("hint") else "",
                            p["a"]["path"], p["b"]["path"]))
        lines.append("відкритих пар: %d" % res["count"])
        return "\n".join(lines) + "\n"
    ents = res["entities"]
    if ents and res.get("how") == "similar":           # a near match, never presented as the one asked about (C14)
        lines.append(SIMILAR % res["query"])
    if res.get("several", len(ents)) > 1:
        lines.append("кілька сутностей «%s»:" % res["query"])
        for e in ents:
            lines.append("%s · %s — ctx entity \"%s\"" % (e["label"], e["kind"], e["id"]))
        if res["several"] > len(ents):
            lines.append("ще %d — уточни запит або --kind" % (res["several"] - len(ents)))
        return "\n".join(lines) + "\n"
    if ents:
        e = ents[0]
        cards = e["cards"]
        lines.append("%s · %s%s" % (e["label"], e["kind"], " · " + e["key"] if e["key"] else ""))
        lines.append("  картки: " + " · ".join("%s · %s%s" % (c["source"], c["path"], " · sensitive" if c["sensitive"] else "")
                                               for c in cards))
        if e.get("slots") or e.get("slots_asked"):     # v3.19.0: the slots say the identity, with its origins
            lines.append("  слоти:")
            lines.extend(_slot_lines(e["slots"]))
            lines.extend("    %s: —" % SLOT_WORDS.get(s_, s_) for s_ in e.get("slots_asked") or () if s_ not in e["slots"])
        else:
            ident = [(n, _values(cards, f)) for n, f in (("e-mail", "emails"), ("команда", "team"), ("роль", "role"))]
            ident = [(n, v) for n, v in ident if v]
            if ident:
                lines.append("  " + " · ".join("%s: %s" % (n, v) for n, v in ident))
        for r in e["related"]:
            lines.append("  пов'язана з: %s — %s" % (r["label"], r["path"]))
        for m in e["maybe"]:
            lines.append("  можливо той самий: %s%s — ctx entity same|not-same \"%s\" \"%s\""
                         % (m["path"], " (%s)" % (HINT % m["hint"]) if m.get("hint") else "", m["mine"], m["path"]))
        for name, part in (("хто посилається", e.get("backlinks")), ("згадки", e.get("mentions"))):
            if part is None:                            # --slot: no backlinks, no mentions
                continue
            if part["count"]:
                lines.append("  %s (%d):" % (name, part["count"]))
                lines.extend("    " + _note_line(d) for d in part["items"])
                if part["count"] > len(part["items"]):
                    lines.append("    ще %d" % (part["count"] - len(part["items"])))
        return "\n".join(lines) + "\n"
    if res.get("mention"):
        m = res["mention"]
        lines.append(MENTION % (m["key"], m["count"]))
        lines.extend("  " + _note_line(d) for d in m["items"])
        if m["count"] > len(m["items"]):
            lines.append("  ще %d" % (m["count"] - len(m["items"])))
        return "\n".join(lines) + "\n"
    if res.get("pending"):
        lines.append(UNKNOWN_YET % (res["query"], cs_.PENDING_NOTE % res["pending"]))
    elif res.get("unread"):                            # the own index did not answer: never the bare «Не знаю»
        lines.append(UNKNOWN_YET % (res["query"], res["unread"]))
    else:
        lines.append(UNKNOWN % res["query"])
    return "\n".join(lines) + "\n"


def card_of(reg, arg):
    """The one card `arg` names for an answer — its path (or a link), or a name one card alone carries — else a
    ValueError that says what it names instead."""
    hit = reg.resolver.resolve(arg)
    if isinstance(hit, str):
        e = reg.of(hit)
        card = next((c for c in (e or {}).get("cards", []) if c["path"] == hit and c.get("home", True)), None)
        if card:
            return card
    q = Resolver.clean(arg)
    if "/" in q or q.lower().endswith(".md"):    # a path names its card or nothing — never another card by its name
        raise ValueError("«%s» — не картка сутності" % arg)
    nk = ci.name_key(q)
    cards = [c for e in reg.entities for c in e["cards"] if c.get("home", True)
             and nk in {ci.name_key(x) for x in _names(c) + list(c.get("aliases") or [])}]
    if len(cards) == 1:
        return cards[0]
    if cards:
        raise ValueError("«%s» — кілька карток: %s — назви шлях" % (arg, ", ".join(sorted(c["path"] for c in cards)[:SEVERAL])))
    raise ValueError("«%s» — не картка сутності" % arg)
