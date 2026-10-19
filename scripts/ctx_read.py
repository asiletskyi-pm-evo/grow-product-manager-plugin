#!/usr/bin/env python3
"""Grow PM — what a skill reads from the context store (since v3.12.0).

references/context-manifest.yaml says, per skill, which records, fields and subsections Step 0c
needs; `read_view` gives the context card plus exactly those parts — read only, no lock, no
writes. Edits not imported yet and records missing on disk are read from the canonical copy,
with a note. A field or a subsection is looked for in your own text first, outside the managed regions,
and only then inside them. Every block a repository put in a record is read with the line that says
whose it is, which version and when it was last checked (since v3.13.0). Since v3.15.0 a name with a slot
(references/context-slots.yaml) is answered by the resolver (scripts/ctx_resolve.py): your text and the blocks bound
to the slot, wherever they sit, in the order of the cascade — and a block a slot already gave is not read twice.
Semantics: references/context-protocol.md.

- load_manifest / manifest_for    the manifest
- read_view                       the text of `ctx read --skill <name>` and its result
- check_manifest                  validator check 16: the manifest against the skills, the schema and the slot catalogue

Stdlib only.
"""
import datetime
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx_common as cc  # noqa: E402
import ctx_store as cs  # noqa: E402
import ctx_schema as sc  # noqa: E402
import ctx_ops as co  # noqa: E402
import ctx_slots as sl  # noqa: E402

PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST_PATH = os.path.join(PLUGIN_ROOT, "references", "context-manifest.yaml")
_INVALID = re.compile(r"> ⚠ Неактуально з [0-9-]+: (.*)")
# "Which Skills Read What" required context → where the manifest must carry it
REQUIRED_MAP = {"product.name": ("product", None), "jira_project_key": ("product", "Jira Project Key"),
                "platforms": ("product", "Platforms"), "planning": ("required_settings", "Planning"),
                "cjm": ("required_settings", "CJM Configuration"), "user.email": ("profile", "Email")}


def load_manifest(path=None):
    with open(path or MANIFEST_PATH, encoding="utf-8") as f:
        return cc.read_yaml_tree(f.read())


def manifest_for(manifest, skill):
    """The skill's entry merged with `every_skill`; an unknown skill → KeyError."""
    entry = (manifest.get("skills") or {})[skill]
    base = manifest.get("every_skill") or {}
    out = dict(entry or {})
    out["records"] = list(base.get("records") or []) + [r for r in (out.get("records") or []) if r not in (base.get("records") or [])]
    out["settings"] = list(base.get("settings") or []) + list(out.get("settings") or [])
    return out


BUDGET_TOKENS = 8000


readers = cs.readers   # who reads a custom or setting record (read_by); lives in ctx_store for ctx_ops


def tokens_est(text):
    return int(math.ceil(len(text) / 3.2))


def _lines(body):
    return [core for _, core, _ in cs._lines(body)]


CONFLICT_NOTE = "⚠ конфлікт: файл і запис різняться — ctx sync"
_VERSION = re.compile(r"(?:^|\s)v=([^\s>]+)")


def _blocks(text, at=0):
    """[(namespace, block id or None, version, start of the begin marker, inner text)] of the managed blocks of `text`,
    in order, read the way that leaves them out of your own text (ctx_common.REGION_RE: a begin and its own end). A
    `<ns>:section` wrapper is not a block, the blocks inside it are; a begin with no end is not one (its text is
    yours). `start` counts from `at`."""
    out = []
    for m in cc.REGION_RE.finditer(text):
        opened = text.index(">", m.start()) + 1
        inner = text[opened:text.rindex("<!--", m.start(), m.end())]
        if m.group(1).endswith(":section"):
            out += _blocks(inner, at + opened)
        else:
            v = _VERSION.search(text[m.start():opened])
            out.append((m.group(1), m.group(2), v.group(1) if v else "", at + m.start(), inner))
    return out


def _blocks_module():
    import ctx_blocks                        # here: ctx_blocks imports this module
    return ctx_blocks


class _Origin:
    """The line before a repository's text, `> [<repository> · v<version> · станом на <date>]`: the repository is the
    registration whose namespace the block carries (the namespace itself when nobody registered it), the version is
    the block's marker, the date the day the store last checked that block against its repository — none when it never
    did or the state cannot be read. Since v3.15.0 a bound block's line also names its slots, `слот <slot> — <about>`
    (spec §5.2): `tags` {(namespace, block id): [slot, …]} (ctx_resolve.bound_slots), the `about` from the catalogue `cat`."""

    def __init__(self, store, repos, tags=None, cat=None):
        self.store = store
        self.repo_of = {}
        for r in repos or ():
            self.repo_of.setdefault(r.get("namespace") or r["id"], r["id"])
        self._blocks = {}
        self.tags = tags or {}
        self.cat = cat or {}

    @staticmethod
    def clip(text, n=60):
        return _blocks_module().clip(text, n)

    def _state(self, repo_id):
        if repo_id not in self._blocks:
            try:
                self._blocks[repo_id] = _blocks_module().load_state(self.store, repo_id)["blocks"]
            except (cs.StoreError, OSError):
                self._blocks[repo_id] = {}
        return self._blocks[repo_id]

    def line(self, ns, bid, v, extra=(), slots=None):
        """The line; `slots` — the slots it names (None: every slot `tags` gives the block); `extra` — the marks after them."""
        clip = _blocks_module().clip
        repo = self.repo_of.get(ns)
        entry = (self._state(repo).get(bid) if repo else None) or {}
        marks = [clip(repo or ns, 60)]
        if v or entry.get("v"):
            marks.append("v" + clip(v or entry["v"], 40))
        day = clip(entry.get("checked") or "", 40)[:10]
        if day:
            marks.append("станом на " + day)
        for slot in self.tags.get((ns, bid), ()) if slots is None else slots:
            marks.append("слот %s — %s" % (clip(slot, 60), clip((sl.slot_info(self.cat, slot) or {}).get("about") or "", 120)))
        return "> [" + " · ".join(marks + list(extra)) + "]"

    def label(self, text):
        """`text` with the line put before each block of it."""
        pieces, at = [], 0
        for ns, bid, v, start, _ in _blocks(text):
            lead = text.rfind("\n", 0, start) + 1
            pos = lead if not text[lead:start].strip() else start
            pieces += [text[at:pos], "" if pos == lead else "\n", self.line(ns, bid, v), "\n"]
            at = pos
        return "".join(pieces) + text[at:]


def _subsection(body, name):
    """The `#…# name` subsection (heading to the next heading of the same or a higher level), or None; the
    heading may carry a qualifier after the name."""
    lines = body.splitlines(keepends=True)
    cores = [l.rstrip("\r\n") for l in lines]
    at = next((k for k, c in enumerate(cores) if cs.heading_matches(c, name)), None)
    if at is None:
        return None
    lvl, end = cs._level(cores[at]), len(lines)
    for k in range(at + 1, len(lines)):
        if 0 < cs._level(cores[k]) <= lvl:
            end = k
            break
    return "".join(lines[at:end]).rstrip("\n") + "\n"


def _field_text(body, name):
    """The field's own line, else its `#### name` subsection."""
    for core in _lines(body):
        m = cs.FIELD_RE.match(core)
        if m and m.group("name").strip() == name:
            return core + "\n"
    return _subsection(body, name)


def _lookup(body, name, field=True):
    """(text, block) of a field (its line, else its `####` subsection; `field=False`: the subsection alone). Your own
    text is read first, with the managed regions left out; failing that, the first block that has it, and then
    `block` is (namespace, id, version) — a subsection ends with its block. A subsection is also found under the other
    headings of cs.SECTION_ALIASES (since v3.14.1: `Team Members` answers `Members`), your own text still before any
    block. (None, None) when nothing has it."""
    find = _field_text if field else _subsection
    names = cs.section_names(name)
    own = cc.strip_managed_regions(body)
    for n in names:
        text = find(own, n)
        if text is not None:
            return text, None
    for ns, bid, v, _, inner in _blocks(body):
        for n in names:
            text = find(inner, n)
            if text is not None:
                return text, (ns, bid, v)
    return None, None


def _without_heading(body):
    lines = body.splitlines(keepends=True)
    return "".join(lines[1:] if lines and lines[0].startswith("#") else lines).strip("\n") + "\n"


def _head(rec, state, today, note=""):
    seen = sc.verified_of(rec, state)
    marks = ["%s · %s" % (rec["title"], rec["id"])]
    if seen:
        marks.append("перевірено %s" % seen)
    if sc.is_stale(rec, state, today):
        marks.append("⚠ застаріле (TTL %s д)" % sc.ttl_of(rec))
    m = _INVALID.search(rec["body"]) if cs.has_status_region(rec["body"]) else None
    if m:
        marks.append("⚠ неактуально: %s" % m.group(1).strip())
    if note:
        marks.append(note)
    return "## " + " · ".join(marks)


def _live_view(store, copies, now):
    """Records as the canonical copy has them now: imported records, with bodies of edits not imported yet
    and records missing on disk taken from the copy. Returns (records, notes by id, pending count)."""
    recs = {r["id"]: r for r in store.load()}
    plan = co.plan_sync(store, copies)
    notes = {}
    for e in plan["edits"] + plan["renames"]:
        recs[e["id"]] = dict(recs[e["id"]], body=e["text"], title=e.get("title") or recs[e["id"]]["title"])
        notes[e["id"]] = "з файлу, ще не підхоплено — ctx sync"
    for rid in plan["missing"]:
        rec = co._from_copy(store, copies, rid, now)
        if rec:
            prev = store.state().get("order", [])
            rec["order"] = (prev.index(rid) + 1) * 10 if rid in prev else 10 ** 6
            recs[rid] = rec
            notes[rid] = "запису немає на диску — ctx sync"
    for rid in plan["removes"]:
        recs.pop(rid, None)
    for x in plan["conflicts"]:
        if x["id"] in recs:
            notes[x["id"]] = CONFLICT_NOTE
    taken = set(recs) | store.reserved_ids()
    for k, a in enumerate(plan["adds"]):
        frag = {"type": a["type"], "title": a["title"], "heading": None, "parent_index": None, "text": a["text"]}
        rid = cs.assign_ids([frag], taken)[0]["id"]
        taken.add(rid)
        prev = recs.get(a.get("after"))
        parent = None
        if a["type"] in ("product", "team") and prev:
            parent = prev["id"] if prev["type"] == "org" else prev.get("parent")
        recs[rid] = {"id": rid, "type": a["type"], "title": a["title"], "parent": parent, "body": a["text"],
                     "order": (prev["order"] if prev else 0) + 0.5 + k / 1000.0}
        notes[rid] = "нова секція з файлу, ще не підхоплено — ctx sync"
    pending = sum(co.pending(plan).values()) + len(plan["missing"]) + len(plan["conflicts"])
    return sorted(recs.values(), key=lambda r: r["order"]), notes, pending


def _pick_product(products, wanted):
    """(product or None, needs_choice)."""
    if not products:
        return None, False
    if wanted:
        w = wanted.strip().lower()
        exact = [p for p in products if p["id"] == wanted or p["title"].split(":", 1)[-1].strip().lower() == w]
        if len(exact) == 1:
            return exact[0], False
        part = [p for p in products if w in p["title"].lower()]
        return (part[0], False) if len(part) == 1 else (None, True)
    if len(products) == 1:
        return products[0], False
    return None, len(products) > 1


def read_view(store, copies, skill, product=None, today=None, manifest=None, repos=None, skipped=None, catalogue=None):
    """The text of `ctx read --skill <skill>` and its result (records, missing, chars, tokens_est, pending,
    needs_product, slots). Reads only: no lock, no network, nothing written. `repos` are the registrations
    (ctx_repos.load_repos): they name the repository of each block and give its rank; without them a block is named by
    its namespace. `skipped` — the registrations load_repos could not read, as (path, reason). `catalogue` — the slot
    catalogue as ctx_slots.load_catalogue reads it (None: the plugin's own; one that cannot be read: no slots).

    Since v3.15.0 every name the manifest reads from a product, a team or the profile that has a slot goes through the
    resolver — ctx_resolve.candidates → resolve → render_slot — over the one assembly ctx_resolve.slot_context; a name
    with no slot is read as v3.14.1 read it. A slot nothing answers is in «Відсутнє» with where it was looked for, while
    `missing` keeps the short form (`Members`, `Members (Team: Beta (B))`); when a bound block for the slot exists but
    cannot be given to one team, it says `є нерозміщений блок — ctx explain <slot>` instead of `блоків із цим слотом немає`.
    What a slot of this view used from a bound block (in full or as a «також» line) is not repeated in a record read whole
    (ctx_resolve.without_shown): the whole region is `> [блок <block> — у слоті <slot> вище]`, a subsection
    `> [блок <block> › <Підсекція> — у слоті <slot> вище]` with the rest of the block kept, a value slot's block stays
    whole. A bound block's origin line names its slot wherever it is printed. A registration not read while a block in the
    records has a namespace no registration read has, a slots memory and a block state that cannot be read are one line
    each, before «Відсутнє». `slots` is {slot: {"shown", "also", "diverges"}} — the sources, for `explain` and the tests."""
    import ctx_resolve as rv                     # here: ctx_resolve imports this module
    spec = manifest_for(manifest or load_manifest(), skill)
    today = (today or datetime.date.today().isoformat())[:10]
    state = store.state()
    card = co._read(store.card_path) if os.path.isfile(store.card_path) else ""
    if catalogue is None:
        try:
            catalogue = sl.load_catalogue()
        except ValueError:
            catalogue = {}                       # validator check 16 names it; meanwhile every name is read as in v3.14.1
    sctx = rv.slot_context(store, copies, repos, product, today + "T00:00:00", cat=catalogue)
    recs, notes, pending = sctx["records"], sctx["notes"], sctx["pending"]
    origin = _Origin(store, repos, tags=rv.bound_slots(catalogue, recs, sctx["bindings"]), cat=catalogue)
    blocks, used, missing, sizes, unassigned = [], [], [], {}, []
    res = {"records": used, "missing": missing, "pending": pending, "needs_product": False,
           "unassigned": unassigned, "over_budget": False, "largest": None, "slots": {}}
    given, whole, answers = {}, [], {}   # what a slot used of each bound block; records read whole (printed last); answers

    def add(rec, text):
        blocks.append(_head(rec, state, today, notes.get(rec["id"], "")) + "\n" + origin.label(text).rstrip("\n") + "\n")
        used.append(rec["id"])
        sizes[rec["id"]] = tokens_est(blocks[-1])

    def add_whole(rec):
        used.append(rec["id"])
        whole.append((len(blocks), rec))
        blocks.append(None)

    absent = []

    def miss(name, required, looked=None, base=None):
        missing.append(name)
        absent.append((base or name) + (" (обов'язкове)" if required else "") + (" " + looked if looked else ""))

    def entry_of(slot, field, place):
        if (slot, field) not in answers:
            unplaced = []
            answers[(slot, field)] = (rv.slot_answers(sctx, slot, field=field, unplaced=unplaced), bool(unplaced))
        return next((e for e in answers[(slot, field)][0] if e["place"] == place), None)

    def looked(slot, rec, field):
        """Where `slot` was looked for — after entry_of(slot, field, …) answered it."""
        return "(шукав: %s у %s; %s)" % (", ".join(rv.looked_for(catalogue, slot, rec, sctx["mem"])), rec["title"],
                                         rv.UNPLACED_BLOCK % slot if answers[(slot, field)][1] else rv.NO_BLOCKS)

    def slot_text(rkind, rec, name, field):
        """(the slot printed, None), (None, where it looked) — or None: the name has no slot."""
        slot = sl.slot_for(catalogue, rkind, name)
        if slot is None:
            return None
        found = entry_of(slot, field, rec["id"] if rkind in ("product", "team") else None)
        if found is None:
            return None, looked(slot, rec, field)
        result = found["result"]
        got = res["slots"].setdefault(slot, {"shown": [], "also": [], "diverges": []})
        for key, items in (("shown", [c["source"] for c in result["shown"]]),
                           ("also", [c["source"] for c in result["also"]]), ("diverges", result["diverges"])):
            got[key] += [x for x in items if x not in got[key]]
        for c in result["shown"] + result["also"]:
            used_part = (slot, result["kind"], c["text"])
            if c.get("ns") and c.get("block") and used_part not in given.get((c["ns"], c["block"]), ()):
                given.setdefault((c["ns"], c["block"]), []).append(used_part)
        return rv.render_slot(result, origin), None

    def present(rkind, rec, name):
        """(is it there, where it looked) of a required field of a record read whole."""
        slot = sl.slot_for(catalogue, rkind, name)
        if slot is None:
            return _lookup(rec["body"], name)[0] is not None, None
        return entry_of(slot, True, rec["id"] if rkind in ("product", "team") else None) is not None, looked(slot, rec, True)

    if spec.get("full"):
        blocks.append("Цей скіл редагує local-context.md і читає його цілком.")
    else:
        prod = None
        if spec.get("product") is not None or spec.get("team") is not None:
            prod = sctx["product"]
            if sctx["needs_product"]:
                res["needs_product"] = True
                res["products"] = sctx["products"]
                blocks = ["Продукти: %s. Повтори з назвою продукту із запиту, або спитай користувача (крок 0d):\n"
                          'python3 "<plugin root>/scripts/ctx.py" read --skill %s --product "<назва>"\n'
                          "Не читай local-context.md цілком." % (", ".join(res["products"]), skill)]
        if not res["needs_product"]:
            for kind in spec["records"]:
                rec = next((r for r in recs if r["id"] == kind or r["type"] == kind), None)
                if rec:
                    add_whole(rec)
                    for f in ((spec.get(kind) or {}).get("required") or []):
                        there, where = present(kind, rec, f)
                        if not there:
                            miss(f, True, where)
                else:
                    miss(kind, False)
            want = spec.get("product")
            if want is not None:
                if prod is None:
                    miss("продукт", bool(want.get("required")))
                else:
                    _parts(add, miss, prod, want, origin, slot_text=lambda r, n, f: slot_text("product", r, n, f))
            want = spec.get("team")
            if want is not None:
                teams = sctx["teams"]
                for t in teams:
                    if want.get("whole"):
                        add_whole(t)
                    else:
                        _parts(add, miss, t, want, origin, where=t["title"] if len(teams) > 1 else None,
                               slot_text=lambda r, n, f: slot_text("team", r, n, f))
            req = list(spec.get("required_settings") or [])
            for name in req + [n for n in spec["settings"] if n not in req]:
                rec = next((r for r in recs if r["type"] == "setting" and r["title"].lower().startswith(name.lower())), None)
                if rec:
                    add_whole(rec)
                else:
                    miss("налаштування %s" % name, name in req)
            for rec in recs:
                who = readers(rec) if rec["type"] in ("custom", "setting") else None
                if who and rec["id"] not in used and ("all" in who or skill.lower() in who):
                    add_whole(rec)
            unassigned.extend(cs.unassigned_ids(recs))
            if unassigned:
                byid = {r["id"]: r for r in recs}
                blocks.append("Власні секції без призначення: %s — ctx get <id>, якщо запит їх стосується"
                              % ", ".join("%s (%s)" % (byid[i]["title"], i) for i in unassigned))
            known = {r.get("namespace") or r["id"] for r in repos or ()}
            stray = any(ns not in known for r in recs for ns, _, _, _, _ in _blocks(r.get("body") or ""))
            if skipped and stray:                # every candidate of an unread registration is in a namespace not read
                blocks += [rv.UNREAD_REGISTRATION % _Origin.clip(path, 200) for path, _ in skipped]
            if sctx["mem_error"]:
                blocks.append(rv.UNREAD_MEMORY % sctx["mem_error"])
            blocks += sctx["problems"]
    for at, rec in whole:
        blocks[at] = (_head(rec, state, today, notes.get(rec["id"], "")) + "\n"
                      + origin.label(rv.without_shown(_without_heading(rec["body"]), given)).rstrip("\n") + "\n")
        sizes[rec["id"]] = tokens_est(blocks[at])
    if absent:
        blocks.append("Відсутнє: %s — для решти діють типові значення" % ", ".join(absent))
    head = "# Контекст для %s · записів %d · %s" % (skill, len(used), "%d правок не підхоплено — ctx sync" % pending if pending else "in sync")
    tail = "Більше з запису: ctx get <id> --section \"…\""
    text = "\n".join([head, "", card.rstrip("\n"), ""] + blocks + ["", tail]) + "\n"
    if tokens_est(text) > BUDGET_TOKENS and sizes:
        big = max(sizes, key=sizes.get)
        res.update(over_budget=True, largest=big)
        warn = "⚠ ≈%d токенів — більше за %d; найбільший запис: %s (≈%d)" % (tokens_est(text), BUDGET_TOKENS, big, sizes[big])
        text = "\n".join([head, "", card.rstrip("\n"), ""] + blocks + ["", warn, tail]) + "\n"
    res.update(chars=len(text), tokens_est=tokens_est(text))
    return text, res


def _parts(add, miss, rec, want, origin, where=None, slot_text=None):
    """The fields and subsections `want` names from `rec`; what it lacks goes to `miss` — a subsection too (since
    v3.14.1), never as obligatory — named `<name> (<where>)` when `where` is given (one of several teams). Since v3.15.0
    `slot_text(rec, name, field)` answers a name that has a slot — (the slot as ctx_resolve.render_slot prints it, None) or
    (None, where it looked) — and gives None for a name with no slot, which is read as v3.14.1 read it (ctx_read._lookup,
    the origin line naming no slot: the text is not a slot's). `field` is the manifest's lookup mode: True for `required`
    and `fields`, False for `sections`."""
    parts = []

    def shown(text, block):
        return text.rstrip("\n") if block is None else origin.line(*block, slots=()) + "\n" + text.rstrip("\n")

    def named(name):
        return "%s (%s)" % (name, where) if where else name

    def one(name, field, required):
        got = slot_text(rec, name, field) if slot_text else None
        if got is not None:
            text, looked = got
            if text is None:
                miss(named(name), required, looked, name)
            else:
                parts.append(text.rstrip("\n"))
            return
        t, block = _lookup(rec["body"], name, field)
        if t is None:
            miss(named(name), required)
        else:
            parts.append(shown(t, block))

    required = want.get("required") or []
    for name in required + (want.get("fields") or []):
        one(name, True, name in required)
    for name in want.get("sections") or []:
        one(name, False, False)
    add(rec, "\n".join(parts) + "\n")


# ------------------------------------------------------------ manifest check
def _table_rows(root):
    """{skill dir name: [required context tokens]} from "Which Skills Read What"."""
    text = co._read(os.path.join(root, "skills", "plugin-configurator", "references", "context-schema.md"))
    sec = text.split("## Which Skills Read What", 1)[-1].split("\n## ", 1)[0]
    rows = {}
    for m in re.finditer(r"^\| \*\*(.+?)\*\* \| ([^|]*) \|", sec, re.M):
        name = m.group(1).strip()
        if name.lower().startswith("every skill"):
            continue
        toks = [re.split(r"\s*\(", t.strip())[0].strip() for t in m.group(2).split(",")]
        rows[re.sub(r"\s+", "-", name.lower())] = [t for t in toks if t and t != "—"]
    return rows


def _manifest_names(man):
    """[(skill, record, name)] — each name the manifest reads from a product, a team or the profile (`required`,
    `fields`, `sections`), once per skill, in the order the manifest gives them. `every_skill` is named as such."""
    out, seen = [], set()
    entries = [("every_skill", man.get("every_skill"))] + list((man.get("skills") or {}).items())
    for skill, entry in entries:
        for record in ("product", "team", "profile"):
            want = entry.get(record) if isinstance(entry, dict) else None
            for key in ("required", "fields", "sections") if isinstance(want, dict) else ():
                names = want.get(key)
                for name in names if isinstance(names, list) else ():
                    if (skill, record, name) not in seen:
                        seen.add((skill, record, name))
                        out.append((skill, record, name))
    return out


def check_manifest(root, manifest_path=None, catalogue_path=None):
    """Errors: a skill without an entry or an entry without a skill, a setting name no setting title starts
    with, a required field of "Which Skills Read What" the manifest does not carry; the slot catalogue
    (references/context-slots.yaml, `catalogue_path`) that cannot be read or has an error of its own, and a name of
    a product, a team or the profile that the manifest reads and the catalogue gives no slot (since v3.15.0)."""
    errs = []
    try:
        man = load_manifest(manifest_path or os.path.join(root, "references", "context-manifest.yaml"))
    except (OSError, ValueError) as e:
        return ["context-manifest.yaml: %s" % e]
    entries = man.get("skills") or {}
    skills = sorted(n for n in os.listdir(os.path.join(root, "skills")) if os.path.isdir(os.path.join(root, "skills", n)))
    errs += ["skill %s has no entry in context-manifest.yaml" % s for s in skills if s not in entries]
    errs += ["context-manifest.yaml names %s, which is not a skill" % s for s in entries if s not in skills]
    titles = [t.lower() for t in cs.SETTING_TITLES]
    names = list((man.get("every_skill") or {}).get("settings") or [])
    for e in entries.values():
        names += list((e or {}).get("settings") or []) + list((e or {}).get("required_settings") or [])
    errs += ["setting %r starts no known setting title" % n for n in sorted(set(names)) if n.lower() not in titles]
    for skill, toks in _table_rows(root).items():
        if skill not in skills:
            errs.append("Which Skills Read What row %s is not a skill" % skill)
            continue
        if skill not in entries:
            continue                                    # reported above
        e = entries[skill] or {}
        for tok in toks:
            if tok not in REQUIRED_MAP:
                errs.append("%s: required context %r has no manifest mapping (ctx_read.REQUIRED_MAP)" % (skill, tok))
                continue
            where, field = REQUIRED_MAP[tok]
            if where == "required_settings":
                ok = field in (e.get("required_settings") or [])
            elif field is None:
                ok = e.get(where) is not None or e.get("full")
            else:
                ok = field in ((e.get(where) or {}).get("required") or []) or e.get("full")
            if not ok:
                errs.append("%s: required %s is not under %s in context-manifest.yaml" % (skill, tok, where))
    try:
        cat = sl.load_catalogue(catalogue_path or os.path.join(root, "references", "context-slots.yaml"))
    except ValueError as e:
        return errs + ["context-slots.yaml: %s" % e]
    errs += ["context-slots.yaml: %s" % e for e in sl.check_catalogue(cat)]
    errs += ["%s: %s name %r has no slot in context-slots.yaml" % (skill, record, name)
             for skill, record, name in _manifest_names(man) if sl.slot_for(cat, record, name) is None]
    return errs
