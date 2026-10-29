#!/usr/bin/env python3
"""Grow PM — `ctx audit`: what breaks the links of your layer (since v4.0.0).

Reads the index (refreshed as `ctx entity` does: its edges and unresolved links, ctx_graph) and the downloaded notes of
your layer — the plugin folder of every vault —, never a file iCloud has not downloaded. A finding {kind, path, detail,
fixable, sig}:

- orphan      a note with no link either way (a wiki link, an embed, a frontmatter link, a bridge — a Jira key's mention
              is no link Obsidian draws) — fixable: `ctx vault normalize` lists it in the hub of its type
- dead        a link that lands nowhere — fixable only when exactly one note bears its name (a moved note)
- ambiguous   a link whose name two notes or more bear — fixable: the full path of the one Obsidian means
- region      a generated region that is not sound (ctx_regions: unclosed, stray-end, dup-id, no-id, unknown-ns, nested,
              heading-twice) — never fixed: its script owns it
- schema      `type` or `created` missing (references/vault-schema.md, Base Frontmatter) — fixable when the folder
              (TYPE_FOLDER_MAP) or a date (the note's `date`, `created_at`, its file name) says it
- backup      a `_backup_*` folder of a vault, a `.bak` file of your layer — named, never touched
- facts       two cards of one entity that disagree on a fact (since task 7, ctx_facts)

Information, never a finding: the notes no link reaches, the names your layer shares with another layer or repeats, the
types outside the taxonomy, the evicted notes (`unchecked`). `_System/` and `Templates/` of the plugin folder are the
plugin's own: not checked.

- run(sctx, context, store, all_, save)   the audit: {command, scope, findings, counts, info, cores, new, at, notes,
                              read}
- render(res)                 the lines it prints
- health(home, has_vault, today)   the lines of `ctx health` from the last result
- type_folder_map / type_of / created_of   what the schema findings derive (shared with ctx_normalize)

Writes only its last result, `<home>/.grow-pm/audit/last.json` (schema context-audit/1: at, counts, sigs) — a cache:
no snapshot, no journal, no `undo`. Stdlib only.
"""
import collections
import datetime
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx_common as cc  # noqa: E402
import ctx_index as ci  # noqa: E402
import ctx_regions as rg  # noqa: E402
import ctx_store as cs  # noqa: E402

N = cc.N
SCHEMA = "context-audit/1"
KINDS = ("orphan", "dead", "ambiguous", "region", "schema", "backup", "facts")
TITLES = {"orphan": "орфани", "dead": "мертві лінки", "ambiguous": "неоднозначні лінки", "region": "регіони",
          "schema": "поля frontmatter", "backup": "бекапи у вейлті", "facts": "розбіжні факти"}
SKIP = ("_System/", "Templates/")          # the plugin folder's own: not checked
LINK_KINDS = "kind != 'mention'"          # an edge Obsidian draws
SHOWN = 5                                  # the examples of a kind the lines show
OLD_DAYS = 30
TAXONOMY_EXTRA = ("moc", "person", "team", "mission", "module", "metric", "epic", "feature", "project", "glossary")
_DAY = re.compile(r"(\d{4}-\d{2}-\d{2})")
_BAK = re.compile(r"\.bak(?:[._-][^/]*)?$", re.I)
PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ------------------------------------------------------------------ what the schema findings derive
def type_folder_map(root=PLUGIN_ROOT):
    """{type: folder} of the TYPE_FOLDER_MAP block of references/vault-schema.md."""
    try:
        text = open(os.path.join(root, "references", "vault-schema.md"), encoding="utf-8").read()
    except OSError:
        return {}
    at = text.find("### TYPE_FOLDER_MAP Reference")
    m = re.search(r"```json\n(.*?)\n```", text[at:], re.S) if at >= 0 else None
    try:
        return json.loads(m.group(1)) if m else {}
    except ValueError:
        return {}


def type_of(rel, tmap):
    """The type a note's folder says (its path inside the plugin folder): the longest TYPE_FOLDER_MAP folder that holds
    it, when exactly one type has that folder; else None."""
    best, types = "", []
    for t, folder in tmap.items():
        f = folder.strip("/") + "/"
        if rel.startswith(f) and len(f) >= len(best):
            if len(f) > len(best):
                best, types = f, []
            types.append(t)
    return types[0] if len(types) == 1 else None


def created_of(fm, rel):
    """The day a note's `created` would be: its `date`, its `created_at`, a date in its file name; else None."""
    for key in ("date", "created_at"):
        m = _DAY.match(ci._text((fm or {}).get(key)).strip())
        if m:
            return m.group(1)
    m = _DAY.search(rel.rsplit("/", 1)[-1])
    return m.group(1) if m else None


def taxonomy(tmap):
    return set(tmap) | set(TAXONOMY_EXTRA)


# ------------------------------------------------------------------ the audit
def own_roots(sctx):
    """[(index name of the plugin folder, its path on disk)] of every vault."""
    out = []
    for r in sctx.get("roots") or []:
        if r.get("source") == "own":
            out.append((ci.rel_path(r["path"], sctx.get("vaults") or [], r), r["path"]))
    return out


def _inside(path, roots):
    """(the plugin folder's name, the path inside it, the file on disk) of an index name of your layer, or None."""
    for rel, disk in roots:
        if not rel or path.startswith(rel + "/"):
            inner = path[len(rel) + 1:] if rel else path
            return rel, inner, os.path.join(disk, *inner.split("/"))
    return None


def vault_of(sctx):
    """A function: the vault an index name lies in (the root with the longest name that holds it), or None — a link
    is a path from its own vault's root, so a fix never points into another vault (review I-5 of tasks 4–6)."""
    pairs = sorted(((ci.rel_path(r["path"], sctx.get("vaults") or [], r), r.get("vault") or "")
                    for r in sctx.get("roots") or []), key=lambda x: -len(x[0]))

    def of(path):
        if path.startswith("@"):
            return None
        for rel, vault in pairs:
            if not rel or path == rel or path.startswith(rel + "/"):
                return vault or None
        return None
    return of


def _filled(v):
    """Has a frontmatter key a value — a text, a number, a list or a map; never None or blanks."""
    if isinstance(v, (list, dict)):
        return bool(v)
    return bool(ci._text(v).strip())


def _sig(f):
    raw = "%s|%s|%s" % (f["kind"], f["path"], json.dumps(f["detail"], ensure_ascii=False, sort_keys=True))
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def _graph(con, roots):
    """Everything the audit reads from the index: own notes, their links either way, unresolved links, names."""
    rows = con.execute("SELECT id, path, title, type, source FROM notes").fetchall()
    out_ids = {r[0] for r in con.execute("SELECT DISTINCT src_id FROM edges WHERE %s" % LINK_KINDS)}
    in_paths = {r[0] for r in con.execute("SELECT DISTINCT dst FROM edges WHERE %s" % LINK_KINDS)}
    dead = con.execute("SELECT n.path, n.source, u.target, u.field, u.why, u.candidates_json FROM unresolved u "
                       "JOIN notes n ON n.id = u.src_id ORDER BY n.path, u.target").fetchall()
    names = con.execute("SELECT path, source, dataless, md FROM names").fetchall()
    return rows, out_ids, in_paths, dead, names


def run(sctx, context, store=None, all_=False, budget=None, now=None, save=True):
    """The audit (see the module's doc); `context` the path of local-context.md (the backups beside it). `save` False
    (`ctx vault normalize`): the last result is not written, and `_idx` and `_reg` — the index and the registry it
    read — come with the result for the caller."""
    import ctx_entity as ce                       # it builds on ctx_graph, which this one reads through
    import ctx_show as csh
    now = now or datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    idx, reg, notes, read, pending = ce._prepare(sctx, store, budget)
    res = {"command": "audit", "scope": "all" if all_ else "own", "findings": [], "counts": {}, "info": {},
           "cores": {}, "new": None, "at": now, "notes": list(notes), "read": read, "pending": pending}
    roots = own_roots(sctx)
    got = idx._read(lambda con: _graph(con, roots), None)
    if got is None:
        if idx.problem:
            res["notes"].append(idx.problem)
        res["read"] = False
        return res
    rows, out_ids, in_paths, dead, names = got
    tmap = type_folder_map()
    tax = taxonomy(tmap)
    providers = [r.get("id") for r in sctx.get("repos") or [] if r.get("id")]
    import ctx_bridges as cbr
    vault = vault_of(sctx)
    findings, types, no_inbound = [], collections.Counter(), 0
    checked, outside = 0, {}                     # outside: {path: the link targets outside every region and code}
    broken = set()                               # the notes normalize never writes: regions not sound, an open fence
    for nid, path, title, typ, source in rows:
        where = _inside(path, roots) if source == "own" else None
        if not where or where[1].startswith(SKIP):
            continue
        _, inner, disk = where
        checked += 1
        linked_out, linked_in = nid in out_ids, path in in_paths
        if not linked_in:
            no_inbound += 1
        if not linked_out and not linked_in:
            findings.append({"kind": "orphan", "path": path, "detail": {"type": typ or ""}, "fixable": True})
        try:
            if ci.is_dataless(disk) or os.path.getsize(disk) > ci.MAX_BYTES:
                continue
            with open(disk, encoding="utf-8", errors="replace") as fh:
                text = fh.read().replace("\r\n", "\n")
        except OSError:
            continue
        outside[path] = rg.outside_targets(text)
        _, problems = rg.parse(text, providers=providers)
        if problems or rg.ends_in_fence(text):
            broken.add(path)
        for p in problems:
            findings.append({"kind": "region", "path": path, "detail": {"why": p["why"], "ns": p["ns"], "id": p["id"]},
                             "fixable": False})
        fm, _ = ci._frontmatter(text)
        block = cbr.frontmatter(text) is not None
        if block and fm is None:                 # a frontmatter the reader does not trust: never written into
            findings.append({"kind": "schema", "path": path, "detail": {"missing": [], "derived": {},
                                                                         "unreadable": True}, "fixable": False})
            continue
        fm = fm or {}
        t = ci._text(fm.get("type")).strip()
        if t and t not in tax:
            types[t] += 1
        missing = [k for k in ("type", "created") if not _filled(fm.get(k))]
        if missing:
            derived = {}
            if "type" in missing and type_of(inner, tmap):
                derived["type"] = type_of(inner, tmap)
            if "created" in missing and created_of(fm, inner):
                derived["created"] = created_of(fm, inner)
            d = {"missing": missing, "derived": derived}
            empty = [k for k in missing if k in fm]
            if empty:
                d["empty"] = empty               # the key is there with no value: filled in place, never a second key
            findings.append({"kind": "schema", "path": path, "detail": d,
                             "fixable": bool(derived) and (block or set(derived) == {"type", "created"})
                             and path not in broken})
    for path, source, target, field, why, cands in dead:
        where = _inside(path, roots) if source == "own" else None
        if not where or where[1].startswith(SKIP):
            continue
        try:
            cands = json.loads(cands or "[]")
        except ValueError:
            cands = []
        kind = "ambiguous" if why == "ambiguous" else "dead"
        free = target in outside.get(path, ()) or bool(field)      # a frontmatter field is never in a region
        d = {"target": target, "field": field or "", "candidates": cands}
        if not free:
            d["where"] = "region"                # only inside a region of a script, or the note is not read: left
        here = [c for c in cands if vault(c) is not None and vault(c) == vault(path)]
        findings.append({"kind": kind, "path": path, "detail": d,
                         "fixable": free and path not in broken
                         and (bool(here) if kind == "ambiguous" else len(cands) == 1 and len(here) == 1)})
    own_names = [(p, dl, md) for p, src, dl, md in names if src == "own" and _inside(p, roots)
                 and not _inside(p, roots)[1].startswith(SKIP)]     # _System/, Templates/: not checked (review M-7)
    for p, dl, md in own_names:
        if not md and _BAK.search(p):
            findings.append({"kind": "backup", "path": p, "detail": {"what": "bak"}, "fixable": False})
    for b in csh.backups(sctx["home"], context, sctx["text"]):
        if b["kind"] == "vault":
            findings.append({"kind": "backup", "path": os.path.basename(b["path"]), "detail": {"what": "folder",
                             "size": b["size"]}, "fixable": False})
    try:
        import ctx_facts as cf                    # task 7: the facts two cards of one entity disagree on
        findings.extend(cf.audit_findings(idx, reg, roots))
    except ImportError:
        pass
    order = {k: i for i, k in enumerate(KINDS)}
    findings.sort(key=lambda f: (order[f["kind"]], f["path"], json.dumps(f["detail"], sort_keys=True, ensure_ascii=False)))
    for f in findings:
        f["sig"] = _sig(f)
    keys = collections.Counter(ci.name_key(p) for p, src, dl, md in names if md)
    own_keys = collections.Counter(ci.name_key(p) for p, dl, md in own_names if md)
    shared = sorted({p.rsplit("/", 1)[-1] for p, dl, md in own_names if md and keys[ci.name_key(p)] > own_keys[ci.name_key(p)]})
    repeated = sorted({p.rsplit("/", 1)[-1] for p, dl, md in own_names if md and own_keys[ci.name_key(p)] > 1})
    counts = {k: sum(1 for f in findings if f["kind"] == k) for k in KINDS}
    counts.update(fixable=sum(1 for f in findings if f["fixable"]), notes=checked,
                  unchecked=sum(1 for p, dl, md in own_names if md and dl))
    res.update(findings=findings, counts=counts,
               info={"no_inbound": no_inbound, "shared_names": shared, "repeated_names": repeated,
                     "types": dict(types.most_common())})
    if all_:
        res["cores"] = _cores(rows, out_ids, in_paths, dead)
    if not save:
        res.update(_idx=idx, _reg=reg)
        return res
    prev = load(sctx["home"])
    if prev is not None:
        old = set(prev.get("sigs") or [])
        res["new"] = sum(1 for f in findings if f["sig"] not in old)
    keep(sctx["home"], {"schema": SCHEMA, "at": now, "counts": counts, "sigs": [f["sig"] for f in findings]})
    return res


def _cores(rows, out_ids, in_paths, dead):
    """{repository: {notes, orphan, dead, ambiguous}} of every source but your layer — counts, never findings."""
    out = {}
    for nid, path, title, typ, source in rows:
        if source == "own":
            continue
        c = out.setdefault(source, {"notes": 0, "orphan": 0, "dead": 0, "ambiguous": 0})
        c["notes"] += 1
        if nid not in out_ids and path not in in_paths:
            c["orphan"] += 1
    for path, source, target, field, why, cands in dead:
        if source != "own" and source in out:
            out[source]["ambiguous" if why == "ambiguous" else "dead"] += 1
    return out


# ------------------------------------------------------------------ the last result
def where(home):
    return os.path.join(home or os.path.expanduser("~"), ".grow-pm", "audit", "last.json")


def load(home):
    """The last result, or None (none yet, or one that cannot be read — a cache: it is written again)."""
    try:
        with open(where(home), encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) and data.get("schema") == SCHEMA else None
    except (OSError, ValueError):
        return None


def keep(home, data):
    path = where(home)
    cs.check_target(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    os.replace(tmp, path)


def health(home, has_vault, today):
    """The lines of `ctx health` (level, text, fix) from the last result (csh levels)."""
    import ctx_show as csh
    if not has_vault:
        return []
    last = load(home)
    if last is None:
        return [(csh.WARN, "аудит вейлта ще не запускався", "ctx audit")]
    out, day = [], str(last.get("at") or "")[:10]
    try:
        age = (datetime.date.fromisoformat(today) - datetime.date.fromisoformat(day)).days
    except ValueError:
        age = None
    counts = last.get("counts") or {}
    if age is not None and age > OLD_DAYS:
        out.append((csh.WARN, "аудит вейлта не запускався %d дн" % age, "ctx audit"))
    if counts.get("fixable"):
        out.append((csh.WARN, "аудит вейлта: %d виправних знахідок (від %s)" % (counts["fixable"], day),
                    "ctx vault normalize"))
    if counts.get("region"):
        out.append((csh.ACT, "регіони зламані: %d (аудит від %s)" % (counts["region"], day), "ctx audit"))
    if not out:
        out.append((csh.OK, "аудит вейлта: виправних немає (від %s)" % day, None))
    return out


# ------------------------------------------------------------------ the lines
def _example(f):
    d = f["detail"]
    if f["kind"] in ("dead", "ambiguous"):
        return "%s → «%s»%s" % (f["path"], d["target"], (" (є: %s)" % ", ".join(d["candidates"][:3])) if d["candidates"] else "")
    if f["kind"] == "region":
        return "%s: %s%s" % (f["path"], d["why"], (" %s" % d["ns"]) if d.get("ns") else "")
    if f["kind"] == "schema":
        return "%s: немає %s%s" % (f["path"], ", ".join(d["missing"]),
                                  (" — буде %s" % ", ".join("%s %s" % kv for kv in d["derived"].items())) if d["derived"] else "")
    return f["path"]


def render(res):
    c, info = res["counts"], res["info"]
    out = ["аудит вейлта (%s): нотаток %d, не перевірено (iCloud): %d\n" % (
        "твій шар" if res["scope"] == "own" else "твій шар і ядра", c.get("notes", 0), c.get("unchecked", 0))]
    for k in KINDS:
        rows = [f for f in res["findings"] if f["kind"] == k]
        if not rows:
            continue
        fix = sum(1 for f in rows if f["fixable"])
        out.append("  %s: %d%s\n" % (TITLES[k], len(rows), (" (виправних %d)" % fix) if fix and fix < len(rows) else ""))
        out.extend("    %s\n" % _example(f) for f in rows[:SHOWN])
        if len(rows) > SHOWN:
            out.append("    · ще %d\n" % (len(rows) - SHOWN))
    bits = ["без вхідних лінків %d" % info.get("no_inbound", 0)]
    if info.get("shared_names"):
        bits.append("назви, що є й в іншому шарі: %s" % ", ".join(info["shared_names"][:SHOWN]))
    if info.get("repeated_names"):
        bits.append("назви, повторені у твоєму шарі: %s" % ", ".join(info["repeated_names"][:SHOWN]))
    if info.get("types"):
        bits.append("типи поза таксономією: %s" % ", ".join("%s %d" % kv for kv in list(info["types"].items())[:SHOWN]))
    out.append("  інформація: %s\n" % "; ".join(bits))
    for repo, n in sorted((res.get("cores") or {}).items()):
        out.append("  ядро %s: нотаток %d, орфанів %d, мертвих лінків %d, неоднозначних %d (лише лічильники)\n"
                   % (repo, n["notes"], n["orphan"], n["dead"], n["ambiguous"]))
    if res.get("new") is not None:
        out.append("нових від минулого аудиту: %d\n" % res["new"])
    out.extend("  %s\n" % n for n in res["notes"])
    if c.get("fixable"):
        out.append("виправних: %d — ctx vault normalize (спершу покаже, що змінить)\n" % c["fixable"])
    else:
        out.append("виправних немає\n")
    return "".join(out)
