#!/usr/bin/env python3
"""Grow PM — bridges in your notes (since v3.20.0): `ctx entity apply`.

The registry (ctx_entity) joins your note and a core's card into one entity by your answer or an e-mail — and nothing in
your note says so, so Obsidian, your scripts and other tools do not see the join. `ctx entity apply` reports the bridges
it would write — one frontmatter line `same_as: "[[<card>|<label>]]"`, the shape the registry itself reads as a bridge —
and, with `--apply --code <the report's code>`, writes them into your layer alone, with a snapshot, a journal line and
`ctx undo`. A name never makes a bridge, nor does a «maybe the same» pair. A `same_as` the plugin did not write is
someone else's field (your own scripts): then the plugin writes it nowhere and says so.

- FIELD                         the field a bridge is written under
- SCHEMA, FILE, WHERE           what the plugin wrote: `<store>/.state/bridges.json` (schema context-bridges/1)
                                {"schema", "written": [[path, field, line, day]]} — with the discipline of
                                `.state/entities.json`: a key this build does not know is refused, a file that cannot be
                                read is never reset. It is in the store's state, so a snapshot holds it and `ctx undo`
                                puts it back with the rest.
- empty_ledger, load_ledger, save_ledger      read and write it
- frontmatter, fm_lines, insert_line, remove_line   one line of a note's frontmatter, the rest byte for byte
- bridge_line                   the line for a card
- bridge_plan, plan_result      what a dry run reports: the rows to write, what is skipped and why, the report's code
- render                        the lines to print

Reads the index (ctx_index), the registry (ctx_entity), `.state/bridges.json`, `.state/entities.json` and the notes a
row names; writes nothing but `run`'s index refresh (ctx_entity._prepare). Stdlib only.
"""
import glob
import hashlib
import json
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx_common as cc  # noqa: E402
import ctx_entity as ce  # noqa: E402
import ctx_index as ci  # noqa: E402
import ctx_resolve as rv  # noqa: E402
import ctx_search as cs_  # noqa: E402
import ctx_store as cs  # noqa: E402

N = cc.N
FIELD = "same_as"
SCHEMA = "context-bridges/1"
FILE = "bridges.json"
WHERE = ".state/" + FILE
_KEYS = ("schema", "written")
_DAY = re.compile(r"\d{4}-\d{2}-\d{2}\Z")
SHOWN = 20                                 # the rows a report lists, at most
BRIDGED = "уже мають міст"
FOREIGN = "поле `%s` веде хтось інший — пропущено" % FIELD
OUTSIDE = "картка поза вейлтом — Obsidian не відкриє посилання"
UNLINKABLE = "назву картки не записати посиланням"
UNREAD = "нотатку не прочитано (iCloud ще не завантажив?) — завантаж: ctx index rebuild --download"
NOT_LAYER = "не в твоєму шарі"
EVICTED = "нотатку не завантажено з iCloud (її дає лише локальний індекс) — завантаж: ctx index rebuild --download"
NO_FM = "нотатка без frontmatter"
HAS_FIELD = "уже має `%s`, але його ціль не знайдено — онови сам або ctx undo" % FIELD
MEMORY_UNREAD = "твої відповіді same/not-same не прочитано — коду звіту немає, мости не пишуться (%s)"
EVICTED_BLOCK = ("%d нотаток твого шару iCloud не завантажив, і жоден локальний індекс їх не дає — чуже `" + FIELD
                 + "` у них не перевірено, коду звіту немає: ctx index rebuild --download")
EVICTED_NOTE = ("%d нотаток твого шару iCloud не завантажив — їхній frontmatter перевірено за локальним індексом; "
                "завантажити: ctx index rebuild --download")
PENDING_FOREIGN = "%d нотаток індекс ще не прочитав — чуже `" + FIELD + "` у них не перевірено"
DENIED = "міст, який заперечує твоє not-same (лише показ — прибери сам або ctx undo)"
SKIP_ORDER = (BRIDGED, HAS_FIELD, FOREIGN, OUTSIDE, UNLINKABLE, UNREAD, EVICTED, NOT_LAYER, NO_FM)
KEY_EMAIL = "e-mail"
KEY_SAME = "твоє same"


# ------------------------------------------------------------------ what the plugin wrote
def empty_ledger():
    return {"schema": SCHEMA, "written": []}


def _clean(data):
    """`data` as the canonical ledger — each (path, field, line) once, the later day; a schema that is not SCHEMA, a
    part of the wrong shape or an unknown key is a ValueError that says which."""
    if not isinstance(data, dict):
        raise ValueError("not an object")
    if data.get("schema") != SCHEMA:
        raise ValueError("schema is %r, not %r" % (data.get("schema"), SCHEMA))
    extra = sorted(str(k) for k in data if k not in _KEYS)
    if extra:
        raise ValueError("unknown key: %s" % ", ".join(extra))
    items = data.get("written", [])
    if not isinstance(items, list):
        raise ValueError("written is not a list")
    best = {}
    for i, x in enumerate(items, 1):
        if not (isinstance(x, list) and len(x) == 4 and all(isinstance(v, str) and v.strip() for v in x)
                and _DAY.match(x[3])):
            raise ValueError("written %d is not [path, field, line, YYYY-MM-DD]" % i)
        key = (N(x[0]).strip(), x[1].strip(), x[2])
        if key not in best or x[3] > best[key]:
            best[key] = x[3]
    out = empty_ledger()
    out["written"] = [[p, f, line, day] for (p, f, line), day in sorted(best.items())]
    return out


def _error(kind, why):
    return cs.StoreError("bridges ledger %s: %s (%s)" % (kind, WHERE, " ".join(str(why).split())[:300]))


def load_ledger(store, timeout=None):
    """What the plugin wrote, from `store` (a ctx_store.Store), canonical. No file: nothing. A file that cannot be read
    → cs.StoreError «bridges ledger not readable: …»; one of another shape → «… not valid: …». Never reset silently."""
    path = os.path.join(store.state_dir, FILE)
    if not os.path.lexists(path):
        return empty_ledger()
    try:
        raw = cs.read_text(path, timeout=timeout)
    except FileNotFoundError:
        return empty_ledger()
    except (OSError, UnicodeDecodeError, cs.StoreError) as e:
        raise _error("not readable", getattr(e, "strerror", None) or e)
    try:
        return _clean(json.loads(raw))
    except ValueError as e:
        raise _error("not valid", e)


def save_ledger(store, ledger):
    """Write the ledger (canonical, atomic) and return what was written; one of the wrong shape → cs.StoreError."""
    try:
        clean = _clean(ledger)
    except ValueError as e:
        raise _error("not valid", e)
    cs.atomic_write(os.path.join(store.state_dir, FILE), json.dumps(clean, ensure_ascii=False, indent=1) + "\n")
    cs.remove_stale_tmp(store.state_dir)
    return clean


def ours(ledger):
    """{(path, line)} of the bridges the plugin wrote."""
    return {(N(p), line) for p, f, line, _ in ledger.get("written", []) if f == FIELD}


_LINK_TARGET = re.compile(r"\[\[([^|\]#^]+)")


def _target_key(text):
    """A link's target as a comparable key: no `.md`, `/` separators, case folded."""
    t = N(text or "").strip().replace("\\", "/")
    t = t[:-3] if t.lower().endswith(".md") else t
    return t.casefold()


def _line_target(line):
    m = _LINK_TARGET.search(line or "")
    return _target_key(m.group(1)) if m else ""


# ------------------------------------------------------------------ one line of a frontmatter
_FM_KEY = re.compile(r"^%s[ \t]*:" % re.escape(FIELD), re.I)


def frontmatter(text):
    """(start, end, eol) of a note's frontmatter by the index's own rules (ctx_index._frontmatter): BOMs before it, an
    opening line `---` (trailing spaces allowed), closed by the first line `---` or `...`. `start` — the index after the
    opening line, `end` — where the closing line begins, `eol` — the ending of the line before the closing one (the
    opening line's when the frontmatter is empty); None for a note without one, or one never closed."""
    t = text or ""
    i = len(t) - len(t.lstrip("\ufeff"))
    nl = t.find("\n", i)
    if nl < 0 or t[i:nl].rstrip("\r ") != "---":
        return None
    start = pos = nl + 1
    while pos <= len(t):
        nl = t.find("\n", pos)
        line = t[pos:] if nl < 0 else t[pos:nl]
        if line.rstrip("\r ") in ("---", "..."):
            prev = t[:pos] if pos > start else t[:start]
            return start, pos, "\r\n" if prev.endswith("\r\n") else "\n"
        if nl < 0:
            return None
        pos = nl + 1
    return None


def fm_lines(text, pattern=_FM_KEY):
    """The lines of the frontmatter (no line ending) whose key matches `pattern` (by default `same_as`, any case)."""
    fm = frontmatter(text)
    if not fm:
        return []
    return [line.rstrip("\r") for line in text[fm[0]:fm[1]].split("\n") if pattern.match(line)]


def insert_line(text, line):
    """The note with `line` as the last line of its frontmatter, in the opening line's line ending; everything else byte
    for byte. A note without a frontmatter → ValueError."""
    fm = frontmatter(text)
    if not fm:
        raise ValueError("no frontmatter")
    start, end, eol = fm
    return text[:end] + line + eol + text[end:]


def remove_line(text, line):
    """The note without the first frontmatter line that is exactly `line` (its line ending gone with it), or None when
    the frontmatter has no such line."""
    fm = frontmatter(text)
    if not fm:
        return None
    start, end, _ = fm
    pos = start
    while pos < end:
        nl = text.find("\n", pos)
        line_end = end if nl < 0 or nl >= end else nl + 1
        if text[pos:line_end].rstrip("\r\n") == line:
            return text[:pos] + text[line_end:]
        pos = line_end
    return None


_UNSAFE_LINK = re.compile(r'[\[\]|#^"\\\n\r]')


def bridge_line(target, label):
    """`same_as: "[[<target without .md>|<label>]]"` — the label without the characters a link or a YAML string would
    choke on; None when the target's own path cannot be a wiki link."""
    link = N(target)[:-3] if N(target).lower().endswith(".md") else N(target)
    if not link or _UNSAFE_LINK.search(link):
        return None
    label = "".join(ch for ch in re.sub(r'[\[\]|"\\]', "", N(label or ""))
                    if unicodedata.category(ch) not in ("Cc", "Cf", "Zl", "Zp")).strip()
    return '%s: "[[%s]]"' % (FIELD, link + ("|" + label if label else ""))


# ------------------------------------------------------------------ the plan
def own_file(sctx, rel):
    """(absolute path, vault) of a note of your layer — inside the plugin folder (an `own` root) of its vault — or
    (None, None)."""
    for root in sctx.get("roots") or ():
        if root.get("source") != "own":
            continue
        vault = root.get("vault") or root["path"]
        p = os.path.normpath(os.path.join(vault, N(rel)))
        if ci._within(p, os.path.normpath(root["path"])):
            return p, vault
    return None, None


def _fold(p):
    return N(os.path.normpath(os.path.abspath(p))).casefold()


def _under(path, folder):
    """Is `path` in `folder` — as written or with links resolved, without regard to case (APFS ignores it)?"""
    if not folder:
        return False
    return any(ci._within(_fold(a), _fold(b)) for a in (path, os.path.realpath(path))
               for b in (folder, os.path.realpath(folder)))


_REG_PATH = re.compile(r"""^\s*(?:core_root|paths?)\s*:\s*['"]?([^'"\n#]+?)['"]?\s*$|^\s*-\s*['"]?(/[^'"\n#]+?)['"]?\s*$""", re.M)


def _registration_folders(sctx):
    """Every folder a registration file names — parsed or not (one that does not parse is no repository of sctx, and
    its core may lie inside your plugin folder): `core_root`, `path(s)` and the list items under them, read raw."""
    files = []
    for root in sctx.get("roots") or ():
        if root.get("source") == "own":
            files += glob.glob(os.path.join(root["path"], "_System", "providers", "*.yaml"))
    files += glob.glob(os.path.join(sctx.get("home") or os.path.expanduser("~"), ".grow-pm", "providers", "*.yaml"))
    out = []
    for f in files:
        try:
            text = cs.read_text(f, timeout=cc.BOUNDARY_READ_S)[:65536]   # one iCloud keeps never hangs a dry run
        except (OSError, UnicodeDecodeError, cs.StoreError):
            continue
        for m in _REG_PATH.finditer(text):
            d = (m.group(1) or m.group(2) or "").strip()
            if d.startswith(("/", "~")):
                out.append((os.path.expanduser(d), os.path.basename(f)))
    return out


def write_refusal(sctx, regs, store_root, home, rel):
    """Why the note `rel` of your layer may not be written (plan C7, review I1/I4), or None. It must lie in the plugin
    folder of its vault and in the storage root (`ctx` writes nowhere else), with its real path there too (no symlink,
    no linked folder) — and in no repository's folder (a registered one, a registration file that does not parse, a
    folder with a core's manifest or `.git` between it and the plugin folder), not in `_System/`, the store or
    `~/.grow-pm`. Every comparison ignores letter case."""
    path, _ = own_file(sctx, rel)
    if not path:
        return "не в теці плагіна"
    root = next(os.path.normpath(r["path"]) for r in sctx["roots"] if r.get("source") == "own"
                and ci._within(path, os.path.normpath(r["path"])))
    if os.path.islink(path) or not ci._within(_fold(os.path.realpath(path)), _fold(os.path.realpath(root))):
        return "посилання (symlink)"
    storage = cc.storage_root(sctx.get("text") or "", home)
    if _fold(storage) == _fold(os.path.join(home, ".grow-pm")):
        return "сховище в ~/.grow-pm (синк вейлту off) — мости пишуться лише у вейлт зі сховищем"
    if not _under(path, storage):
        return "інший вейлт — поза коренем сховища"
    inner = os.path.relpath(path, root).split(os.sep)
    if "_system" in [x.casefold() for x in inner[:-1]] and [x.casefold() for x in inner] != ["_system", "agents.md"]:
        return "_System/"                    # since v4.0.0 its AGENTS.md is written (ctx vault normalize --only agents)
    for repo in sctx.get("repos") or ():
        for d in [repo.get("core_root")] + list(repo.get("paths") or ()):
            if d and _under(path, d):
                return "тека репозиторію %s" % (repo.get("id") or "?")
    for d, name in _registration_folders(sctx):
        if _under(path, d):
            return "тека з реєстрації %s" % name
    probe = os.path.dirname(path)
    while ci._within(probe, root) and probe != root:
        if os.path.isfile(os.path.join(probe, "_System", "provider-manifest.yaml")) or os.path.exists(os.path.join(probe, ".git")):
            return "тека ядра (%s)" % os.path.relpath(probe, root)
        probe = os.path.dirname(probe)
    hit = cc.boundary_hit(path, regs or [])
    if hit:
        return "тека провайдера %s" % (hit.get("id") or "?")
    for d, why in ((store_root, "сховище"), (os.path.join(home, ".grow-pm"), "~/.grow-pm")):
        if d and _under(path, d):
            return why
    return None


def _reg_rank(sctx):
    ranks = {r.get("id"): rv._rank(r) for r in sctx.get("repos") or ()}

    def key(card):
        r = ranks.get(card.get("source"))
        return (ce._rank(card), (1, 0) if r is None else (0, -r), card["path"])
    return key


def _sha(data):
    return hashlib.sha1(data).hexdigest()


def bridge_plan(sctx, idx, reg, ledger, mem, kind=None, regs=None, store_root=None, timeout=None):
    """What `ctx entity apply` would write (plan C2–C4): {rows: [{path, target, label, line, key, kind, entity, sha}],
    skipped: {reason: [path]}, foreign: [path], denied: [(path, target)], code}. A row is a card of your layer, held by
    the plugin's index, whose entity holds a card of another source that your `same` or an e-mail joins it to directly,
    and that has no bridge to its entity yet nor any `same_as`; its target — the strongest such card (a core's by rank,
    then a local index's) whose file lies in the same vault; its note one plan C7 lets be written (write_refusal: the
    report is what --apply writes). A `same_as` of your layer the ledger does not hold — by path and target — makes the
    field someone else's: then no row at all. Reads each row's note (all within one `timeout`), never writes."""
    mine = ours(ledger)
    mine_lines = {line for _, line in mine}          # a line is ours whatever its note is called now (a rename)
    our_targets = {_line_target(line) for line in mine_lines}
    same = {tuple(ce._pair(x[0], x[1])) for x in mem.get("same", [])}
    apart = {tuple(ce._pair(x[0], x[1])) for x in mem.get("not_same", [])}
    foreign = {d["path"] for d in idx.field_links(FIELD, "own") if _target_key(d["target"]) not in our_targets}
    rows, skipped, denied = [], {}, []
    rank = _reg_rank(sctx)
    home = sctx.get("home") or os.path.expanduser("~")
    prefixes = [p for p in getattr(reg.resolver, "prefixes", ()) if p]

    def yours(card):        # a note of your plugin folder — a local index's too, while iCloud keeps the file (v3.19.0);
        if card.get("source") == "own":                     # a registered core inside the plugin folder is a core
            return True
        return card.get("origin") == "local" and any(card["path"] == p or card["path"].startswith(p + "/") for p in prefixes)

    def skip(why, path):
        skipped.setdefault(why, [])
        if path not in skipped[why]:
            skipped[why].append(path)

    with cs.read_budget(timeout if timeout is not None else cs.read_timeout()):    # every note in one budget (M2)
        for e in reg.entities:
            for c in e["cards"]:
                if yours(c) and c.get("origin") != "index":   # a note iCloud keeps: its `same_as` by the local index
                    t = (c.get("bridges") or {}).get(FIELD)
                    if t and _target_key(t) not in our_targets:
                        foreign.add(c["path"])
                if c.get("source") == "own":         # a bridge your note keeps that your not-same denies: shown only
                    for target in c.get("bridges", {}).values():
                        hit = reg.resolver.resolve(target)
                        if isinstance(hit, str) and tuple(ce._pair(c["path"], hit)) in apart:
                            denied.append((c["path"], hit))
            if kind and e["kind"] != kind:
                continue
            homes = [c for c in e["cards"] if c.get("home")]
            others = [o for o in homes if not yours(o)]     # a note of yours is never a bridge's target
            if not others:
                continue
            for c in homes:
                if not yours(c):
                    continue
                linked = set()
                for target in c.get("bridges", {}).values():
                    hit = reg.resolver.resolve(target)
                    if isinstance(hit, str) and hit != c["path"] and reg.of(hit) is e:
                        linked.add(hit)
                if any(p in linked for p in (o["path"] for o in others)):
                    skip(BRIDGED, c["path"])
                    continue
                direct = [o for o in others if set(c["emails"]) & set(o["emails"])
                          or tuple(ce._pair(c["path"], o["path"])) in same]
                if not direct:
                    continue
                if c.get("origin") != "index":         # only a note that would be a row is sent to download (M4)
                    skip(EVICTED, c["path"])
                    continue
                path, vault = own_file(sctx, c["path"])
                if not path:
                    skip(NOT_LAYER, c["path"])
                    continue
                why = write_refusal(sctx, regs, store_root, home, c["path"])
                if why:
                    skip(BOUNDARY % why, c["path"])
                    continue
                direct.sort(key=rank)
                inside = [o for o in direct if not o["path"].startswith("@") and not os.path.isabs(o["path"])
                          and os.path.lexists(os.path.join(vault, o["path"]))]
                if not inside:
                    skip(OUTSIDE, c["path"])
                    continue
                target = inside[0]
                line = bridge_line(target["path"], target.get("label"))
                if not line:
                    skip(UNLINKABLE, c["path"])
                    continue
                if ci.is_dataless(path):             # never a download started by a dry run (final M3)
                    skip(EVICTED, c["path"])
                    continue
                try:
                    data = cs.read_bytes(path)
                    text = data.decode("utf-8")
                except (OSError, UnicodeDecodeError, cs.StoreError):
                    skip(UNREAD, c["path"])
                    continue
                if not frontmatter(text):
                    skip(NO_FM, c["path"])
                    continue
                have = fm_lines(text)
                if any(x not in mine_lines for x in have):
                    foreign.add(c["path"])
                    continue
                if have:                             # ours, its card gone: never a second key (review I3)
                    skip(HAS_FIELD, c["path"])
                    continue
                rows.append({"path": c["path"], "target": target["path"], "label": target.get("label") or "",
                             "line": line, "key": KEY_EMAIL if set(c["emails"]) & set(target["emails"]) else KEY_SAME,
                             "kind": e["kind"], "entity": e["label"], "sha": _sha(data)})
    foreign = sorted(foreign)
    if foreign:
        rows = []
        skipped[FOREIGN] = foreign
        if skipped.get(BRIDGED):                     # someone else's field: said once, there (final M5)
            skipped[BRIDGED] = [x for x in skipped[BRIDGED] if x not in foreign]
    rows.sort(key=lambda r: r["path"])
    blob = json.dumps([[r["path"], r["line"], r["sha"]] for r in rows] + [foreign], ensure_ascii=False)
    return {"rows": rows, "skipped": skipped, "foreign": foreign, "denied": sorted(set(denied)),
            "code": hashlib.sha1(blob.encode("utf-8")).hexdigest()[:8]}


def plan_result(sctx, store, kind=None, budget=None):
    """`ctx entity apply`'s plan: {command, action, rows, skipped, foreign, denied, code, notes, read, pending,
    blocked}. Refreshes the index (as `ctx entity`); your answers are the ones the registry was built with — when they
    could not be read, `blocked` says why and `code` is "" (review I5: a `not-same` of yours never ignored); a ledger
    that cannot be read stops the run (cs.StoreError)."""
    idx, reg, notes, read, pending = ce._prepare(sctx, store, budget)
    ledger = load_ledger(store, timeout=None)
    regs, _ = cc.boundary_registrations(cc.vault_entries(sctx.get("text") or ""),
                                        extra_dirs=[os.path.join(sctx.get("home") or "", ".grow-pm", "providers")])
    plan = bridge_plan(sctx, idx, reg, ledger, getattr(reg, "memory", None) or ce.empty_memory(), kind=kind,
                       regs=regs, store_root=store.root)
    if idx.problem and idx.problem not in notes:
        notes.append(idx.problem)
    blocked = MEMORY_UNREAD % reg.memory_problem if getattr(reg, "memory_problem", None) else None
    evicted = ci.evicted(sctx.get("roots") or [], sctx.get("store_rel"), sctx.get("blocks_rels")) if sctx.get("roots") else []
    if evicted:                                      # what nobody read cannot be checked for `same_as` (final I1)
        if cs_.sources(sctx.get("text") or "", sctx.get("repos") or [], ("local",)):
            notes.append(EVICTED_NOTE % len(evicted))
        else:
            blocked = blocked or EVICTED_BLOCK % len(evicted)
    if blocked:
        plan["code"] = ""
    if pending:
        notes.append(PENDING_FOREIGN % pending)
    return dict(plan, command="entity", action="apply", notes=list(notes), read=read and not idx.problem,
                pending=pending, blocked=blocked)


# ------------------------------------------------------------------ the write (plan C6–C8)
CHANGED = "звіт змінився — переглянь ще раз: ctx entity apply"
MOVED = "нотатку змінено під час запису — пропущено"
NOT_WRITTEN = "нотатку не записано: %s"
BOUNDARY = "межа запису: %s — не пишу"
OP = "entity-apply"


def write_note(path, text, original=None):
    """Write a note of yours in place — the same file, its mode, extended attributes and creation date kept (review
    I7: a new file through a temp one would make a 0600 profile 0644 and lose its Finder tags; the standard library on
    macOS cannot copy extended attributes). The guard of `ctx` (cs.check_target) first; then flushed to disk. Not
    atomic: a write that fails half-way puts `original` (the bytes the caller read) back before it raises; the
    snapshot taken before holds them too."""
    cs.check_target(path)
    data = text.encode("utf-8")
    with open(path, "r+b") as f:
        try:
            f.seek(0)
            f.write(data)
            f.truncate()
            f.flush()
            os.fsync(f.fileno())
        except BaseException:
            if original is not None:
                try:
                    f.seek(0)
                    f.write(original)
                    f.truncate()
                    f.flush()
                except OSError:
                    pass
            raise


def _snapshot_copies(snap):
    """{index name: sha1} of the notes a snapshot keeps, or None when `snap` is no snapshot folder."""
    if not snap or not os.path.isdir(snap):
        return None
    try:
        with open(os.path.join(snap, "manifest.json"), encoding="utf-8") as f:
            entries = json.load(f).get("notes") or []
        return {N(k["path"]): _sha(cs.read_bytes(os.path.join(snap, k["file"]))) for k in entries}
    except (OSError, ValueError, KeyError, TypeError, cs.StoreError):
        return {}


def apply_plan(sctx, store, copies, home, plan, regs, day, snapshot, journal, now):
    """Write the rows of `plan` (plan_result, its code checked by the caller). The ledger is read first (one that cannot
    be read: nothing written). Each note is checked against plan C7 and read — bytes other than the plan's → MOVED;
    a snapshot of those notes (`snapshot(notes)` → its folder) whose copy of a note is not those bytes → MOVED too
    (a save while it ran, review I6); each note read once more right before its line is written. Then one journal
    line {op entity-apply, notes: [{path, line, before, after}], snapshot} and the ledger — for the notes written, even
    when a later one fails (journal first). Returns {written: [row], skipped: {reason: [path]}, snapshot}."""
    ledger = load_ledger(store)
    skipped, ready = {}, []

    def skip(why, path):
        skipped.setdefault(why, []).append(path)

    for r in plan["rows"]:
        why = write_refusal(sctx, regs, store.root, home, r["path"])
        if why:
            skip(BOUNDARY % why, r["path"])
            continue
        path, _ = own_file(sctx, r["path"])
        try:
            data = cs.read_bytes(path)
        except (OSError, cs.StoreError):
            skip(UNREAD, r["path"])
            continue
        if _sha(data) != r["sha"]:
            skip(MOVED, r["path"])
            continue
        ready.append((r, path))
    if not ready:
        return {"written": [], "skipped": skipped, "snapshot": None}
    snap = snapshot([(r["path"], path) for r, path in ready])
    kept = _snapshot_copies(snap)
    written, notes = [], []
    try:
        for r, path in ready:
            if kept is not None and kept.get(r["path"]) != r["sha"]:
                skip(MOVED, r["path"])
                continue
            try:
                data = cs.read_bytes(path)
            except (OSError, cs.StoreError):
                skip(UNREAD, r["path"])
                continue
            if _sha(data) != r["sha"]:
                skip(MOVED, r["path"])
                continue
            new = insert_line(data.decode("utf-8"), r["line"])
            try:
                write_note(path, new, original=data)
            except cs.PathRefused as e:
                skip(BOUNDARY % e, r["path"])
                continue
            except OSError as e:                     # a read-only note, a full disk: this one skipped, the rest goes on
                skip(NOT_WRITTEN % (e.strerror or e), r["path"])
                continue
            written.append(r)
            notes.append({"path": r["path"], "line": r["line"], "before": r["sha"],
                          "after": _sha(new.encode("utf-8"))})
    finally:
        if written:
            journal({"ts": now, "op": OP, "ids": [], "source": "ctx-entity-apply", "reason": "", "snapshot": snap,
                     "notes": notes})
            ledger["written"].extend([r["path"], FIELD, r["line"], day] for r in written)
            save_ledger(store, ledger)
    return {"written": written, "skipped": skipped, "snapshot": snap}


# ------------------------------------------------------------------ `ctx undo` (plan C9, R4)
GONE = "файлу немає"
EDITED = "змінено після запису"
ROTATED = "знімка вже немає — нотатку змінено після запису, не чіпаю"


def undo_notes(marks):
    """The notes the journal lines `marks` (the ones an undo takes back, oldest first) changed: [(rel, mark, note)],
    the newest line first, each note of a line in its order."""
    out = []
    for m in reversed(marks):
        for n in m.get("notes") or ():
            if isinstance(n, dict) and isinstance(n.get("path"), str) and n["path"].strip():
                out.append((N(n["path"]), m, n))
    return out


def _kept_copy(mark, rel):
    """The bytes the snapshot of a journal line kept of the note `rel` before that change, or None (a rotated snapshot,
    no copy)."""
    snap = mark.get("snapshot")
    try:
        with open(os.path.join(snap, "manifest.json"), encoding="utf-8") as f:
            entry = next((k for k in json.load(f).get("notes") or () if N(k.get("path", "")) == rel), None)
        if entry:
            return cs.read_bytes(os.path.join(snap, entry["file"]))
    except (OSError, ValueError, TypeError, cs.StoreError):
        pass
    return None


def revert_notes(sctx, regs, store_root, home, items):
    """Take back the changes `items` (undo_notes) made to your notes, the newest first (R4): a note whose bytes are what
    the change left (`after`) gets the snapshot's copy (its sha1 must be `before`); a note changed since loses our line
    alone when its frontmatter still holds it exactly and the change added it (`entity apply`, or an undo that put it
    back); a note that no longer holds it is left quietly — our line is gone already; anything else — a note gone, our
    line changed, a write plan C7 refuses, a note that cannot be written — is left and said, once per note. Returns
    (journal notes [{path, line, before, after, added}] of what was written — `ctx undo` of this undo uses them —,
    [path reverted], [(path, why)] not reverted)."""
    done, reverted, kept = [], [], {}
    for rel, mark, n in items:
        why = write_refusal(sctx, regs, store_root, home, rel)
        if why:
            kept[rel] = BOUNDARY % why
            continue
        path, _ = own_file(sctx, rel)
        if n.get("removed") and not os.path.lexists(path):       # since v4.0.0: a file an undo removed comes back
            copy = _kept_copy(mark, rel)
            if copy is None or _sha(copy) != n.get("before"):
                kept[rel] = ROTATED
                continue
            try:
                cs.check_target(path)
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "xb") as f:
                    f.write(copy)
            except (OSError, cs.PathRefused) as e:
                kept[rel] = NOT_WRITTEN % (getattr(e, "strerror", None) or e)
                continue
            done.append({"path": rel, "line": "", "before": None, "after": _sha(copy), "created": True})
            kept.pop(rel, None)
            if rel not in reverted:
                reverted.append(rel)
            continue
        if not os.path.lexists(path):
            kept[rel] = GONE
            continue
        if ci.is_dataless(path):
            kept[rel] = UNREAD
            continue
        try:
            cur = cs.read_bytes(path)
        except (OSError, cs.StoreError) as e:
            kept[rel] = "%s (%s)" % (UNREAD, getattr(e, "strerror", None) or e)
            continue
        if n.get("created"):                                     # since v4.0.0: a file the change created goes,
            if _sha(cur) != n.get("after"):                      # only while it holds what the change wrote
                kept[rel] = EDITED
                continue
            try:
                cs.check_target(path)
                os.remove(path)
            except (OSError, cs.PathRefused) as e:
                kept[rel] = NOT_WRITTEN % (getattr(e, "strerror", None) or e)
                continue
            done.append({"path": rel, "line": "", "before": _sha(cur), "after": None, "removed": True})
            kept.pop(rel, None)
            if rel not in reverted:
                reverted.append(rel)
            continue
        line = n.get("line") if isinstance(n.get("line"), str) else ""
        adds = mark.get("op") == OP or bool(n.get("added"))       # the change put our line in
        copy = _kept_copy(mark, rel) if _sha(cur) == n.get("after") else None
        new = copy if copy is not None and _sha(copy) == n.get("before") else None
        if new is None and adds and line:
            try:
                text = cur.decode("utf-8")
            except UnicodeDecodeError:
                text = None
            if text is not None and line not in fm_lines(text):
                if fm_lines(text) and rel not in reverted:
                    kept[rel] = EDITED                     # another `same_as` there now: yours, left as it is
                continue                                   # else our line is gone already: nothing to take back
            out = remove_line(text, line) if text is not None else None
            new = out.encode("utf-8") if out is not None else None
        if new is None:
            if rel not in reverted:
                kept[rel] = ROTATED if _sha(cur) == n.get("after") else EDITED
            continue
        try:
            write_note(path, new.decode("utf-8"), original=cur)
        except (OSError, cs.PathRefused) as e:
            kept[rel] = NOT_WRITTEN % (getattr(e, "strerror", None) or e)
            continue
        done.append({"path": rel, "line": line, "before": _sha(cur), "after": _sha(new),
                     "added": bool(line) and line in fm_lines(new.decode("utf-8"))})
        kept.pop(rel, None)
        if rel not in reverted:
            reverted.append(rel)
    return done, reverted, [(r, w) for r, w in kept.items() if r not in reverted]


def keep_ours(sctx, store, items, day, previous=None, reverted=()):
    """After an undo restored the store: a note of `items` that still holds our line exactly (one undo could not take
    it out, or put it back) has it in the ledger again — and so has one undo did not revert whose file is gone (renamed,
    moved: our line lives on under another path, and the ledger's line is matched under any path) when the ledger
    before the undo (`previous`) held it — never «someone else's» for a line the plugin wrote (review I3, final I2).
    Returns the paths added back."""
    ledger = load_ledger(store)
    have = {(N(p), line) for p, f, line, _ in ledger["written"] if f == FIELD}
    before = {(N(p), line) for p, f, line, _ in (previous or {}).get("written", []) if f == FIELD}
    added = []
    for rel, _, n in items:
        line = n.get("line")
        if not isinstance(line, str) or not line or (rel, line) in have:
            continue
        path, _ = own_file(sctx, rel)
        if rel not in reverted and (rel, line) in before and not (path and os.path.lexists(path)):
            ledger["written"].append([rel, FIELD, line, day])
            have.add((rel, line))
            added.append(rel)
            continue
        if not path or not os.path.isfile(path) or ci.is_dataless(path):
            continue
        try:
            text = cs.read_bytes(path).decode("utf-8")
        except (OSError, UnicodeDecodeError, cs.StoreError):
            continue
        if line in fm_lines(text):
            ledger["written"].append([rel, FIELD, line, day])
            have.add((rel, line))
            added.append(rel)
    if added:
        save_ledger(store, ledger)
    return added


# ------------------------------------------------------------------ the report
def bridges_word(n):
    """«міст», «мости», «мостів» for n."""
    if n % 10 == 1 and n % 100 != 11:
        return "міст"
    if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
        return "мости"
    return "мостів"


def notes_word(n):
    if n % 10 == 1 and n % 100 != 11:
        return "нотатка"
    if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
        return "нотатки"
    return "нотаток"


def render(res, written=False):
    """The lines of a dry run (or, `written`, of what --apply wrote)."""
    out = []
    rows = res.get("rows") or []
    if rows:
        out.append("%s %d %s:" % ("записано" if written else "запишу", len(rows), bridges_word(len(rows))))
        for r in rows[:SHOWN]:
            out.append("  %s → %s (%s)" % (r["path"], r["target"], r["key"]))
        if len(rows) > SHOWN:
            out.append("  … і ще %d" % (len(rows) - SHOWN))
    else:
        out.append("мостів записати нічого" if not written else "нічого не записано")
    skipped = res.get("skipped") or {}
    if any(skipped.values()):
        out.append("пропущено:")
        for why in list(SKIP_ORDER) + sorted(w for w in skipped if w not in SKIP_ORDER):    # every reason (review M1)
            paths = skipped.get(why) or []
            if paths:
                out.append("  %s: %d %s (%s%s)" % (why, len(paths), notes_word(len(paths)), ", ".join(paths[:3]),
                                                     ", …" if len(paths) > 3 else ""))
    for path, target in res.get("denied") or []:
        out.append("%s: %s → %s" % (DENIED, path, target))
    for n in res.get("notes") or []:
        out.append(n)
    if res.get("blocked"):
        out.append(res["blocked"])
    elif not written:
        out.append("код звіту: %s" % res.get("code", ""))
        if rows:
            out.append("записати: ctx entity apply --apply --code %s" % res.get("code", ""))
    return "\n".join(out) + "\n"
