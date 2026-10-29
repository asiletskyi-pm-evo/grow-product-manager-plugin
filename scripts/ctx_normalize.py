#!/usr/bin/env python3
"""Grow PM — `ctx vault normalize`: what the audit finds and a machine can fix, in your layer alone (since v4.0.0).

A dry run reports the rows it would write and a code; `--apply --code <the code>` writes them — after a snapshot of every
file it changes, with one journal line, so `ctx undo` takes them back byte for byte. Only the plugin folder of every
vault, only notes iCloud has downloaded; never a core's folder, the plugin's copy of a core, the store, `_System/` (but
its AGENTS.md), a code block, or a region another script owns. A value already there is never changed and a key never
removed; a file is never renamed.

Six operations (`--only`):
- frontmatter   a missing `type` (its folder, TYPE_FOLDER_MAP) and `created` (its `date`, `created_at`, a date in its
                file name); a note with no frontmatter gets one only when both are known
- links         a link whose name two notes bear → the full path of the one in your layer, else in the same folder,
                else the shortest path; a link to a path that is not there → the one note of its name; the text a
                reader sees stays (`[[path|as written]]`)
- hubs          an orphan listed in the region `ctx:hub-<type>` of the hub of its type — the `type: moc` note that
                already links most notes of that type (3 at least), else a new `_MOC/<type> — хаб.md`; the hub keeps
                every note it listed before (so the next run does not take it back)
- related       a region `ctx:related` at a note's end: the work card of a Jira key it mentions and the person card of a
                participant the registry knows by an e-mail, an alias or a link — a name alone never; not where the
                note has a «related» region of your own scripts
- agents        the region `ctx:agents` of `<plugin folder>/_System/AGENTS.md`: the rules for an agent that writes in
                this vault; the text outside the region is yours
- bases         `<folder>/<name>.base` — an Obsidian Bases table of a TYPE_FOLDER_MAP folder with 5 notes or more; a
                `.base` without the first line «# ctx:generated» is yours and stays

- plan(sctx, context, store, home, only, today)   {rows, files, skipped, notes, code, read}
- rewrite(rel, text, rows, today)   a file's new text from its rows — the dry run's preview and the write are one code
- apply(...)                  the write; revert support lives in ctx_bridges.revert_notes (created files too)

Reads the index (refreshed through ctx_audit) and the downloaded notes of your layer; writes only on apply. Stdlib only.
"""
import collections
import datetime
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx_audit as ca  # noqa: E402
import ctx_bridges as cbr  # noqa: E402
import ctx_common as cc  # noqa: E402
import ctx_index as ci  # noqa: E402
import ctx_regions as rg  # noqa: E402
import ctx_store as cs  # noqa: E402

N = cc.N
OP = "vault-normalize"
OPS = ("frontmatter", "links", "hubs", "related", "agents", "bases")
MIN_BASE = 5                               # the notes a folder needs for a .base
MIN_HUB = 3                                # the notes of a type a moc must link to be that type's hub
BASE_MARK = "# ctx:generated — плагін переписує цей файл (ctx vault normalize --only bases)"
PEOPLE_FIELDS = ("participants", "attendees", "organizer")
AGENTS = "_System/AGENTS.md"
_WIKI = re.compile(r"(!?)\[\[([^\]\n]+?)\]\]")
SKIP = {"no-fm": "без frontmatter, а виводиться не все — не пишу",
        "outside": "кандидат поза вейлтом — Obsidian його не відкриє",
        "in-region": "лінк лише в чужому регіоні або в коді",
        "hub-unread": "хаб не завантажено з iCloud",
        "own-related": "у нотатці вже є «related» твого скрипта",
        "base-yours": ".base без позначки ctx — твій",
        "refused": "межа запису"}


def _sha(data):
    return hashlib.sha1(data).hexdigest()


def _day(today):
    return (today or datetime.date.today().isoformat())[:10]


# ------------------------------------------------------------------ what each operation writes
def _fm_text(adds):
    return "".join("%s: %s\n" % (k, adds[k]) for k in ("type", "created") if k in adds)


def _link_target(path):
    return path[:-3] if path.lower().endswith(".md") else path


def _safe_label(s):
    return re.sub(r"[\[\]|\n\r]", " ", s or "").strip()


def _fix_links(text, fixes):
    """`text` with each link whose target (as written) is a key of `fixes` pointed at fixes[target] — its anchor kept,
    the text a reader sees kept (`|as written` when it had no label; an embed keeps what follows `|`); never inside a
    code block, a code span or a region."""
    masked = rg._masked(text)
    regions = rg.parse(text)[0]
    out, last = [], 0
    for m in _WIKI.finditer(masked):
        if any(r["start"] <= m.start() < r["end"] for r in regions):
            continue
        inner = text[m.start(2):m.end(2)]
        target, anchor, label = ci._link_parts(inner)
        if target not in fixes:
            continue
        new = fixes[target] + (("#" + anchor) if anchor else "")
        if label is not None and label != "":
            new += "|" + label
        elif not m.group(1):
            new += "|" + target
        out.append(text[last:m.start(2)])
        out.append(new)
        last = m.end(2)
    out.append(text[last:])
    return "".join(out)


def _region_text(rid, body):
    return "<!-- ctx:begin id=%s -->\n%s<!-- ctx:end id=%s -->\n" % (rid, body, rid)


def _set_region(text, rid, body):
    """`text` with the region ctx:<rid> holding `body` — replaced in place when it is there, else added at the end;
    body None removes it."""
    for r in rg.parse(text)[0]:
        if r["ns"] == "ctx" and r["id"] == rid:
            end = r["end"] + (1 if text[r["end"]:r["end"] + 1] == "\n" else 0)
            if body is None:
                return text[:r["start"]] + text[end:]
            return text[:r["start"]] + _region_text(rid, body) + text[end:]
    if body is None:
        return text
    sep = "" if text.endswith("\n\n") or not text else ("\n" if text.endswith("\n") else "\n\n")
    return text + sep + _region_text(rid, body)


def _region_body(text, rid):
    for r in rg.parse(text)[0]:
        if r["ns"] == "ctx" and r["id"] == rid:
            return r["inner"].lstrip("\n")
    return None


def _list_body(title, links):
    return "**%s**\n" % title + "".join("- [[%s|%s]]\n" % (t, _safe_label(l)) for t, l in links)


def _listed(body):
    """The targets a ctx list region holds."""
    return [ci._link_parts(m.group(2))[0] for m in _WIKI.finditer(body or "")]


def agents_body(sctx, tmap):
    cores = sorted({os.path.basename(os.path.normpath(r.get("core_root") or next(iter(r.get("paths") or []), "")))
                    for r in sctx.get("repos") or [] if r.get("core_root") or r.get("paths")} - {""})
    lines = ["Правила для агента, що пише в цей вейлт (згенеровано Grow PM; текст поза регіоном — твій).", "",
             "- Не пиши всередині регіонів `<!-- <простір>:begin … -->` — їх переписує їхній скрипт "
             "(простори: %s; реєстр — vault-schema.md)." % ", ".join(sorted(rg.NAMESPACES)),
             "- Не пиши в теки спільного ядра: %s." % (", ".join(cores) if cores else "—"),
             "- Назва нової нотатки має бути унікальною у вейлті: `[[назва]]` не повинна вести у дві нотатки.",
             "- Обов'язкові поля frontmatter: `type`, `product`, `created` (YYYY-MM-DD), `skill`, `skill_version`.",
             "- Сховище контексту (`_System/context/`) пише лише `ctx`.", "", "Куди який тип:"]
    lines += ["- `%s` → `%s`" % (t, f) for t, f in sorted(tmap.items())]
    return "\n".join(lines) + "\n"


def base_text(folder_rel, name):
    return ("%s\nfilters:\n  and:\n    - file.inFolder(\"%s\")\nviews:\n  - type: table\n    name: %s\n    order:\n"
            "      - file.name\n      - type\n      - created\n      - status\n    sort:\n      - property: created\n"
            "        direction: DESC\n" % (BASE_MARK, folder_rel.rstrip("/"), json.dumps(name, ensure_ascii=False)))


def rewrite(rel, text, rows, today=None):
    """The new text of the file `rel` (None: a new file) after its rows, in the order frontmatter, links, related, hubs,
    agents, bases."""
    by = collections.defaultdict(list)
    for r in rows:
        by[r["op"]].append(r)
    t = text or ""
    for r in by["frontmatter"]:
        if cbr.frontmatter(t):
            for k in ("type", "created"):
                if k in r["add"]:
                    t = cbr.insert_line(t, "%s: %s" % (k, r["add"][k]))
        else:
            t = "---\n" + _fm_text(r["add"]) + "---\n" + t
    if by["links"]:
        t = _fix_links(t, {r["target"]: r["new"] for r in by["links"]})
    for r in by["related"]:
        t = _set_region(t, "related", _list_body("Пов'язане", r["links"]) if r["links"] else None)
    for r in by["hubs"]:
        if text is None and not t:
            t = "---\ntype: moc\ncreated: %s\n---\n# %s — хаб\n\nНотатки без зв'язків, які додав `ctx vault normalize`.\n\n" \
                % (_day(today), r["type"])
        t = _set_region(t, "hub-" + r["type"], _list_body("Без зв'язків (додав ctx)", r["links"]))
    for r in by["agents"]:
        if text is None and not t:
            t = "# AGENTS\n\n"
        t = _set_region(t, "agents", r["body"])
    for r in by["bases"]:
        t = r["body"]
    return t


# ------------------------------------------------------------------ the plan
def _choose(cands, src, roots):
    """The one of an ambiguous link's candidates Obsidian means for us: in your layer, then the source's folder, then
    the shortest path; never one outside every vault (`@…`)."""
    inside = [c for c in cands if not c.startswith("@")]
    if not inside:
        return None
    folder = src.rsplit("/", 1)[0]
    return sorted(inside, key=lambda c: (0 if ca._inside(c, roots) else 1,
                                         0 if c.rsplit("/", 1)[0] == folder else 1, len(c), c))[0]


def _texts(rows, roots):
    """{index name: text} of the downloaded notes of your layer (not `_System/` but its AGENTS.md, not Templates/)."""
    out = {}
    for nid, path, title, typ, source in rows:
        w = ca._inside(path, roots) if source == "own" else None
        if not w or (w[1].startswith(ca.SKIP) and w[1] != AGENTS):
            continue
        try:
            if ci.is_dataless(w[2]) or os.path.getsize(w[2]) > ci.MAX_BYTES:
                continue
            with open(w[2], "rb") as f:
                out[path] = f.read().decode("utf-8")
        except (OSError, UnicodeDecodeError):
            continue
    return out


def _disk(sctx, rel):
    path, _ = cbr.own_file(sctx, rel)
    return path


def _strings(v):
    if isinstance(v, list):
        return [x for item in v for x in _strings(item)]
    if isinstance(v, dict):
        return []
    return [ci._text(v)] if ci._text(v).strip() else []


def _person(reg, s):
    """The person entity a participant's text names by an e-mail, a link or an exact alias — never a name alone."""
    s = s.strip()
    if "[[" in s:
        hit = reg.resolver.resolve(s)
        e = reg.of(hit) if isinstance(hit, str) else None
        return e if e and e["kind"] == "person" else None
    low = s.lower()
    if "@" in low and ci._EMAIL.match(low):
        found, _ = reg.find(low, "person")
        return found[0] if len(found) == 1 else None
    hits = [e for e in reg.entities if e["kind"] == "person"
            and any(s.casefold() == a.casefold() for c in e["cards"] for a in (c.get("aliases") or []))]
    return hits[0] if len(hits) == 1 else None


def _card_link(ent):
    """(link target, label) of an entity: its id card, else any of its cards inside a vault."""
    for c in [next((c for c in ent["cards"] if c["path"] == ent["id"]), None)] + list(ent["cards"]):
        if c and not c["path"].startswith("@"):
            return _link_target(c["path"]), ent.get("key") or ent.get("label") or c.get("label")
    return None


def plan(sctx, context, store, home, only=None, today=None):
    """The rows of a normalisation (see the module's doc)."""
    import ctx_entity as ce
    only = [o for o in (only or OPS)]
    audit = ca.run(sctx, context, store=store, save=False)
    out = {"command": "vault", "action": "normalize", "rows": [], "files": {}, "skipped": {}, "notes": audit["notes"],
           "read": audit["read"], "code": None, "only": only}
    if not audit["read"]:
        return out
    idx, reg = audit["_idx"], audit["_reg"]
    roots = ca.own_roots(sctx)
    got = idx._read(lambda con: (con.execute("SELECT id, path, title, type, source FROM notes").fetchall(),
                                 con.execute("SELECT n.path, e.dst, e.kind FROM edges e JOIN notes n ON n.id = e.src_id")
                                 .fetchall(),
                                 con.execute("SELECT path FROM names").fetchall()), None)
    if got is None:
        out["read"] = False
        return out
    rows, edges, names = got
    texts = _texts(rows, roots)
    types = {p: (t or "") for _, p, _, t, _ in rows}
    links_of = collections.defaultdict(set)
    for src, dst, kind in edges:
        if kind != "mention":
            links_of[src].add(dst)
    mentions = collections.defaultdict(set)
    for src, dst, kind in edges:
        if kind == "mention":
            mentions[src].add(dst)
    tmap = ca.type_folder_map()
    regs, _ = cc.boundary_registrations(cc.vault_entries(sctx["text"]),
                                        extra_dirs=[os.path.join(home, ".grow-pm", "providers")])
    plan_rows, skipped = [], collections.defaultdict(list)

    def refused(rel):
        return cbr.write_refusal(sctx, regs, sctx["store_root"], home, rel)

    def add(row):
        why = refused(row["path"])
        if why:
            skipped["%s: %s" % (SKIP["refused"], why)].append(row["path"])
            return
        plan_rows.append(row)

    findings = audit["findings"]
    if "frontmatter" in only:
        for f in findings:
            if f["kind"] != "schema" or not f["fixable"] or f["path"] not in texts:
                continue
            adds = f["detail"]["derived"]
            if not cbr.frontmatter(texts[f["path"]]) and set(adds) != {"type", "created"}:
                skipped[SKIP["no-fm"]].append(f["path"])
                continue
            add({"op": "frontmatter", "path": f["path"], "add": adds})
    if "links" in only:
        for f in findings:
            if f["kind"] not in ("dead", "ambiguous") or not f["fixable"] or f["path"] not in texts:
                continue
            d = f["detail"]
            new = _choose(d["candidates"], f["path"], roots) if f["kind"] == "ambiguous" else (
                d["candidates"][0] if d["candidates"] and not d["candidates"][0].startswith("@") else None)
            if not new:
                skipped[SKIP["outside"]].append(f["path"])
                continue
            fixed = _fix_links(texts[f["path"]], {d["target"]: _link_target(new)})
            if fixed == texts[f["path"]]:
                skipped[SKIP["in-region"]].append(f["path"])
                continue
            add({"op": "links", "path": f["path"], "target": d["target"], "new": _link_target(new), "why": f["kind"],
                 "candidates": d["candidates"]})
    if "hubs" in only:
        by_type = collections.defaultdict(list)
        for f in findings:
            if f["kind"] == "orphan":
                w = ca._inside(f["path"], roots)
                t = types.get(f["path"]) or (ca.type_of(w[1], tmap) if w else None) or "note"
                by_type[t].append(f["path"])
        for t, orphans in sorted(by_type.items()):
            root_rel = ca._inside(orphans[0], roots)[0]
            counts = collections.Counter()
            for src, dsts in links_of.items():
                if types.get(src) == "moc" and ca._inside(src, roots):
                    counts[src] = sum(1 for d_ in dsts if types.get(d_) == t)
            ours = sorted(h for h, tx in texts.items() if _region_body(tx, "hub-" + t) is not None)
            best = [h for h, n in counts.most_common() if n >= MIN_HUB]
            hub = ours[0] if ours else sorted(best, key=lambda h: (-counts[h], h))[0] if best else None
            new_file = hub is None
            if new_file:
                base = "%s/_MOC/%s — хаб" % (root_rel, t) if root_rel else "_MOC/%s — хаб" % t
                taken = {ci.name_key(p) for p, in names}
                hub = base + ".md" if ci.name_key(base) not in taken else base + " (ctx).md"
            elif hub not in texts:
                skipped[SKIP["hub-unread"]].extend(orphans)
                continue
            have = _listed(_region_body(texts.get(hub, ""), "hub-" + t)) if not new_file else []
            keep = [(x, "") for x in have]
            wanted = [(_link_target(o), o.rsplit("/", 1)[-1][:-3]) for o in sorted(orphans)
                      if _link_target(o) not in have]
            if not wanted:
                continue
            labels = {x: x.rsplit("/", 1)[-1] for x in have}
            links = [(x, labels[x]) for x, _ in keep] + wanted
            add({"op": "hubs", "path": hub, "type": t, "new_file": new_file, "add": [o for o in sorted(orphans)],
                 "links": links})
    if "related" in only:
        for path, text in sorted(texts.items()):
            w = ca._inside(path, roots)
            if not w or w[1].startswith(ca.SKIP):
                continue
            regions = rg.parse(text)[0]
            if any(r["ns"] == "related" for r in regions):
                skipped[SKIP["own-related"]].append(path)
                continue
            mine = _region_body(text, "related")
            listed = set(_listed(mine)) if mine is not None else set()
            own_links = {d_ for d_ in links_of.get(path, set()) if _link_target(d_) not in listed}
            links = []
            by_key = collections.defaultdict(set)          # a work's cards by its key: your hub first, else the core's
            for dst in mentions.get(path) or ():
                e = reg.of(dst)
                by_key[(e or {}).get("key") or dst].add(dst)
            mine_key = (reg.of(path) or {}).get("key")
            for key, cards in sorted(by_key.items()):
                if path in cards or own_links & cards or key == mine_key:
                    continue                                # the note is a card of that key, or links one itself
                pick = sorted((c for c in cards if not c.startswith("@")),
                              key=lambda c: (0 if ca._inside(c, roots) else 1, c))
                if pick:
                    links.append((_link_target(pick[0]), key))
            fm, _ = ci._frontmatter(text.replace("\r\n", "\n"))
            seen = set()
            for field in PEOPLE_FIELDS:
                for s_ in _strings((fm or {}).get(field)):
                    e = _person(reg, s_)
                    if not e or e["id"] in seen:
                        continue
                    seen.add(e["id"])
                    cards = {c["path"] for c in e["cards"]}
                    if path in cards or own_links & cards:
                        continue
                    lk = _card_link(e)
                    if lk:
                        links.append(lk)
            body = _list_body("Пов'язане", links) if links else None
            if body == mine or (body is None and mine is None):
                continue
            add({"op": "related", "path": path, "links": links})
    if "agents" in only:
        for root_rel, _disk_path in roots:
            rel = (root_rel + "/" if root_rel else "") + AGENTS
            body = agents_body(sctx, tmap)
            cur = texts.get(rel)
            exists = cur is not None or os.path.exists(_disk(sctx, rel) or "")
            if exists and cur is None:
                continue                         # there but not readable (evicted): left as it is
            if cur is not None and _region_body(cur, "agents") == body:
                continue
            add({"op": "agents", "path": rel, "new_file": not exists, "body": body})
    if "bases" in only:
        md_names = [p for p, in names if p.lower().endswith(".md")]
        for root_rel, disk in roots:
            for t, folder in sorted(tmap.items()):
                f = folder.strip("/")
                if not os.path.isdir(os.path.join(disk, *f.split("/"))):
                    continue
                pre = (root_rel + "/" if root_rel else "") + f + "/"
                if sum(1 for p in md_names if p.startswith(pre)) < MIN_BASE:
                    continue
                name = f.rsplit("/", 1)[-1]
                rel = pre + name + ".base"
                body = base_text(pre, name)
                disk_path = _disk(sctx, rel)
                if disk_path and os.path.isfile(disk_path):
                    try:
                        cur = open(disk_path, encoding="utf-8").read()
                    except (OSError, UnicodeDecodeError):
                        continue
                    if not cur.startswith(BASE_MARK):
                        skipped[SKIP["base-yours"]].append(rel)
                        continue
                    if cur == body:
                        continue
                    add({"op": "bases", "path": rel, "new_file": False, "body": body})
                elif not any(r["op"] == "bases" and r["path"] == rel for r in plan_rows):
                    add({"op": "bases", "path": rel, "new_file": True, "body": body})
    order = {o: i for i, o in enumerate(OPS)}
    plan_rows.sort(key=lambda r: (order[r["op"]], r["path"], r.get("target", "")))
    for i, r in enumerate(plan_rows, 1):
        r["n"] = i
    files = {}
    for r in plan_rows:
        if r["path"] not in files:
            files[r["path"]] = _sha(texts[r["path"]].encode("utf-8")) if r["path"] in texts else None
            if files[r["path"]] is None and not r.get("new_file"):
                disk_path = _disk(sctx, r["path"])
                try:
                    files[r["path"]] = _sha(cs.read_bytes(disk_path)) if disk_path and os.path.isfile(disk_path) else None
                except (OSError, cs.StoreError):
                    files[r["path"]] = None
    out.update(rows=plan_rows, files=files, skipped={k: sorted(set(v)) for k, v in skipped.items()})
    out["code"] = code(out)
    return out


def code(p):
    raw = json.dumps([[{k: v for k, v in r.items() if k != "n"} for r in p["rows"]], p["files"]], ensure_ascii=False,
                     sort_keys=True)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:8]


# ------------------------------------------------------------------ the write
MOVED = "файл змінено після звіту — пропущено"
NOT_WRITTEN = "не записано: %s"


def create_note(path, text):
    """A new file of yours: refused when it is there already (written meanwhile)."""
    cs.check_target(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "xb") as f:
        f.write(text.encode("utf-8"))
        f.flush()
        os.fsync(f.fileno())


def apply(sctx, p, skip, snapshot, journal, now):
    """Write the rows of plan `p` (its code checked by the caller), but the numbers `skip`: per file, the bytes must be
    the plan's (MOVED otherwise); one snapshot of the files changed; each file written; one journal line {op
    vault-normalize, snapshot, notes: [{path, line "", before, after, created}]}. Returns {written, skipped, snapshot}."""
    rows = [r for r in p["rows"] if r["n"] not in set(skip or ())]
    by_file = collections.OrderedDict()
    for r in rows:
        by_file.setdefault(r["path"], []).append(r)
    skipped, ready = collections.defaultdict(list), []
    for rel, rs in by_file.items():
        path = _disk(sctx, rel)
        if not path:
            skipped[NOT_WRITTEN % "не в теці плагіна"].append(rel)
            continue
        want = p["files"].get(rel)
        if want is None:
            if os.path.lexists(path):
                skipped[MOVED].append(rel)
                continue
            ready.append((rel, path, rs, None))
            continue
        try:
            data = cs.read_bytes(path)
        except (OSError, cs.StoreError):
            skipped[MOVED].append(rel)
            continue
        if _sha(data) != want:
            skipped[MOVED].append(rel)
            continue
        ready.append((rel, path, rs, data))
    if not ready:
        return {"written": [], "skipped": dict(skipped), "snapshot": None}
    snap = snapshot([(rel, path) for rel, path, rs, data in ready if data is not None])
    written, notes = [], []
    try:
        for rel, path, rs, data in ready:
            text = data.decode("utf-8") if data is not None else None
            new = rewrite(rel, text, rs, now)
            try:
                if data is None:
                    create_note(path, new)
                else:
                    if _sha(cs.read_bytes(path)) != _sha(data):
                        skipped[MOVED].append(rel)
                        continue
                    cbr.write_note(path, new, original=data)
            except FileExistsError:
                skipped[MOVED].append(rel)
                continue
            except cs.PathRefused as e:
                skipped[NOT_WRITTEN % e].append(rel)
                continue
            except OSError as e:
                skipped[NOT_WRITTEN % (e.strerror or e)].append(rel)
                continue
            written.extend(rs)
            notes.append(dict({"path": rel, "line": "", "before": _sha(data) if data is not None else None,
                               "after": _sha(new.encode("utf-8"))}, **({"created": True} if data is None else {})))
    finally:
        if notes:
            journal({"ts": now, "op": OP, "ids": [], "source": "ctx-vault-normalize", "reason": "", "snapshot": snap,
                     "notes": notes})
    return {"written": written, "skipped": dict(skipped), "snapshot": snap}


# ------------------------------------------------------------------ the lines
def _row_line(r):
    if r["op"] == "frontmatter":
        return "%d. %s: + %s" % (r["n"], r["path"], ", ".join("%s: %s" % kv for kv in r["add"].items()))
    if r["op"] == "links":
        return "%d. %s: [[%s]] → [[%s]] (%s)" % (r["n"], r["path"], r["target"], r["new"],
                                                  "неоднозначний" if r["why"] == "ambiguous" else "мертвий")
    if r["op"] == "hubs":
        return "%d. %s%s: + %s" % (r["n"], r["path"], " (новий хаб)" if r["new_file"] else "", ", ".join(r["add"][:5]))
    if r["op"] == "related":
        return "%d. %s: «Пов'язане» — %s" % (r["n"], r["path"], ", ".join(l for _, l in r["links"][:5]) or "прибрати")
    return "%d. %s%s" % (r["n"], r["path"], " (новий)" if r.get("new_file") else " (оновити)")


def render(res, written=False):
    out = []
    rows = res.get("rows") or []
    titles = {"frontmatter": "поля frontmatter", "links": "лінки", "hubs": "хаби", "related": "«Пов'язане»",
              "agents": "AGENTS.md", "bases": "Bases"}
    if not rows:
        out.append("нічого не записано" if written else "нормалізувати нічого")
    for op in OPS:
        rs = [r for r in rows if r["op"] == op]
        if rs:
            out.append("%s (%d):" % (titles[op], len(rs)))
            out.extend("  " + _row_line(r) for r in rs[:20])
            if len(rs) > 20:
                out.append("  · ще %d" % (len(rs) - 20))
    if any(res.get("skipped", {}).values()):
        out.append("пропущено:")
        for why, paths in sorted(res["skipped"].items()):
            out.append("  %s: %d (%s%s)" % (why, len(paths), ", ".join(paths[:3]), ", …" if len(paths) > 3 else ""))
    out.extend(res.get("notes") or [])
    if not written:
        out.append("код звіту: %s" % res.get("code"))
        if rows:
            out.append("записати: ctx vault normalize --apply --code %s [--skip N,…]%s" % (
                res.get("code"), (" --only " + ",".join(res["only"])) if res.get("only") and len(res["only"]) < len(OPS)
                else ""))
    return "\n".join(out) + "\n"
