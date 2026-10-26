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
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx_common as cc  # noqa: E402
import ctx_entity as ce  # noqa: E402
import ctx_index as ci  # noqa: E402
import ctx_resolve as rv  # noqa: E402
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
UNREAD = "нотатку не прочитано (iCloud ще не завантажив?)"
NOT_LAYER = "не в твоєму шарі — нотатка прийшла лише з локального індексу"
NO_FM = "нотатка без frontmatter"
DENIED = "міст, який заперечує твоє not-same (лише показ — прибери сам або ctx undo)"
SKIP_ORDER = (BRIDGED, FOREIGN, OUTSIDE, UNLINKABLE, UNREAD, NOT_LAYER, NO_FM)
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


# ------------------------------------------------------------------ one line of a frontmatter
_FM_KEY = re.compile(r"^%s[ \t]*:" % re.escape(FIELD), re.I)


def frontmatter(text):
    """(start, end, eol) of a note's frontmatter: `start` — the index after the opening `---` line, `end` — the index
    where the closing `---` line begins, `eol` — the opening line's line ending; None for a note without one. A BOM
    before the opening line is allowed."""
    t = text or ""
    i = 1 if t.startswith("﻿") else 0
    m = re.match(r"---[ \t]*(\r\n|\n)", t[i:])
    if not m:
        return None
    start = i + m.end()
    pos = start
    while pos < len(t):
        nl = t.find("\n", pos)
        line_end = len(t) if nl < 0 else nl + 1
        if t[pos:line_end].rstrip("\r\n").rstrip(" \t") == "---":
            return start, pos, m.group(1)
        pos = line_end
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
    label = re.sub(r'[\[\]|"\\\n\r]', "", N(label or "")).strip()
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


def _reg_rank(sctx):
    ranks = {r.get("id"): rv._rank(r) for r in sctx.get("repos") or ()}

    def key(card):
        r = ranks.get(card.get("source"))
        return (ce._rank(card), (1, 0) if r is None else (0, -r), card["path"])
    return key


def _sha(data):
    return hashlib.sha1(data).hexdigest()


def bridge_plan(sctx, idx, reg, ledger, mem, kind=None, timeout=None):
    """What `ctx entity apply` would write (plan C2–C4): {rows: [{path, target, label, line, key, kind, entity, sha}],
    skipped: {reason: [path]}, foreign: [path], denied: [(path, target)], code}. A row is a card of your layer, held by
    the plugin's index, whose entity holds a card of another source that your `same` or an e-mail joins it to directly,
    and that has no bridge to its entity yet; its target — the strongest such card (a core's by rank, then a local
    index's) whose file lies in the same vault. A `same_as` of your layer the ledger does not hold makes the field
    someone else's: then no row at all. Reads each row's note (within `timeout`), never writes."""
    mine = ours(ledger)
    our_paths = {p for p, _ in mine}
    same = {tuple(ce._pair(x[0], x[1])) for x in mem.get("same", [])}
    apart = {tuple(ce._pair(x[0], x[1])) for x in mem.get("not_same", [])}
    foreign = {p for p in idx.field_links(FIELD, "own") if p not in our_paths}
    rows, skipped, denied = [], {}, []
    rank = _reg_rank(sctx)

    def skip(why, path):
        skipped.setdefault(why, [])
        if path not in skipped[why]:
            skipped[why].append(path)

    for e in reg.entities:
        for c in e["cards"]:                         # a bridge your note keeps that your not-same denies: shown only
            if c.get("source") == "own":
                for target in c.get("bridges", {}).values():
                    hit = reg.resolver.resolve(target)
                    if isinstance(hit, str) and tuple(ce._pair(c["path"], hit)) in apart:
                        denied.append((c["path"], hit))
        if kind and e["kind"] != kind:
            continue
        homes = [c for c in e["cards"] if c.get("home")]
        others = [o for o in homes if o.get("source") != "own"]
        if not others:
            continue
        for c in homes:
            if c.get("source") != "own":
                continue
            if c.get("origin") != "index":
                skip(NOT_LAYER, c["path"])
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
            path, vault = own_file(sctx, c["path"])
            if not path:
                skip(NOT_LAYER, c["path"])
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
            try:
                data = cs.read_bytes(path, timeout=timeout if timeout is not None else cs.read_timeout())
                text = data.decode("utf-8")
            except (OSError, UnicodeDecodeError, cs.StoreError):
                skip(UNREAD, c["path"])
                continue
            if not frontmatter(text):
                skip(NO_FM, c["path"])
                continue
            if any((c["path"], x) not in mine for x in fm_lines(text)):
                foreign.add(c["path"])
                continue
            rows.append({"path": c["path"], "target": target["path"], "label": target.get("label") or "",
                         "line": line, "key": KEY_EMAIL if set(c["emails"]) & set(target["emails"]) else KEY_SAME,
                         "kind": e["kind"], "entity": e["label"], "sha": _sha(data)})
    foreign = sorted(foreign)
    if foreign:
        rows = []
        skipped[FOREIGN] = foreign
    rows.sort(key=lambda r: r["path"])
    blob = json.dumps([[r["path"], r["line"], r["sha"]] for r in rows] + [foreign], ensure_ascii=False)
    return {"rows": rows, "skipped": skipped, "foreign": foreign, "denied": sorted(set(denied)),
            "code": hashlib.sha1(blob.encode("utf-8")).hexdigest()[:8]}


def plan_result(sctx, store, kind=None, budget=None):
    """`ctx entity apply` without --apply: {command, action, rows, skipped, foreign, denied, code, notes, read,
    pending}. Refreshes the index (as `ctx entity`); reads your answers and the ledger (a ledger that cannot be read
    stops the run: cs.StoreError)."""
    idx, reg, notes, read, pending = ce._prepare(sctx, store, budget)
    ledger = load_ledger(store, timeout=None)
    try:
        mem = ce.load_memory(store, timeout=None)
    except cs.StoreError:
        mem = ce.empty_memory()             # _prepare said so in `notes`
    plan = bridge_plan(sctx, idx, reg, ledger, mem, kind=kind)
    if idx.problem and idx.problem not in notes:
        notes.append(idx.problem)
    return dict(plan, command="entity", action="apply", notes=list(notes), read=read and not idx.problem,
                pending=pending)


# ------------------------------------------------------------------ the write (plan C6–C8)
CHANGED = "звіт змінився — переглянь ще раз: ctx entity apply"
MOVED = "нотатку змінено під час запису — пропущено"
BOUNDARY = "межа запису: %s — не пишу"
OP = "entity-apply"


def write_refusal(sctx, regs, store_root, home, rel):
    """Why the note `rel` of your layer may not be written (plan C7), or None: it must lie in the plugin folder of its
    vault, under no registered repository's folder (`core_root`, `paths`, a registration's read-only roots), the store,
    `_System/` or `~/.grow-pm`, and be no link — nor lie, links resolved, outside the plugin folder."""
    path, _ = own_file(sctx, rel)
    if not path:
        return "не в теці плагіна"
    root = next(os.path.normpath(r["path"]) for r in sctx["roots"] if r.get("source") == "own"
                and ci._within(path, os.path.normpath(r["path"])))
    real_root = os.path.realpath(root)
    if os.path.islink(path) or not ci._within(os.path.realpath(path), real_root):   # a linked folder on the way too
        return "посилання (symlink)"
    parts = os.path.relpath(path, root).split(os.sep)
    if "_System" in parts[:-1]:
        return "_System/"
    for repo in sctx.get("repos") or ():
        for d in [repo.get("core_root")] + list(repo.get("paths") or ()):
            if d and (ci._within(path, os.path.normpath(d))
                      or ci._within(os.path.realpath(path), os.path.realpath(d))):
                return "тека репозиторію %s" % (repo.get("id") or "?")
    if cc.boundary_hit(path, regs):
        return "тека провайдера %s" % (cc.boundary_hit(path, regs).get("id") or "?")
    for d, why in ((store_root, "сховище"), (os.path.join(home, ".grow-pm"), "~/.grow-pm")):
        if d and ci._within(os.path.realpath(path), os.path.realpath(d)):
            return why
    return None


def apply_plan(sctx, store, copies, home, plan, regs, day, snapshot, journal, now):
    """Write the rows of `plan` (plan_result, its code checked by the caller): each note checked against plan C7 and
    read again — bytes other than the plan's → skipped (MOVED); a snapshot of the notes about to change first
    (`snapshot(notes)` → its folder), then each line, then the ledger and one journal line {op entity-apply, notes:
    [{path, line, before, after}], snapshot} — written even when a later note fails, for the notes already written.
    Returns {written: [row], skipped: {reason: [path]}, snapshot}."""
    skipped, ready = {}, []
    for r in plan["rows"]:
        why = write_refusal(sctx, regs, store.root, home, r["path"])
        if why:
            skipped.setdefault(BOUNDARY % why, []).append(r["path"])
            continue
        path, _ = own_file(sctx, r["path"])
        try:
            data = cs.read_bytes(path)
        except (OSError, cs.StoreError):
            skipped.setdefault(UNREAD, []).append(r["path"])
            continue
        if _sha(data) != r["sha"]:
            skipped.setdefault(MOVED, []).append(r["path"])
            continue
        ready.append((r, path, data.decode("utf-8")))
    if not ready:
        return {"written": [], "skipped": skipped, "snapshot": None}
    snap = snapshot([(r["path"], path) for r, path, _ in ready])
    written, notes = [], []
    try:
        for r, path, text in ready:
            new = insert_line(text, r["line"])
            cs.atomic_write(path, new)
            written.append(r)
            notes.append({"path": r["path"], "line": r["line"], "before": r["sha"],
                          "after": _sha(new.encode("utf-8"))})
    finally:
        if written:
            ledger = load_ledger(store)
            ledger["written"].extend([r["path"], FIELD, r["line"], day] for r in written)
            save_ledger(store, ledger)
            journal({"ts": now, "op": OP, "ids": [], "source": "ctx-entity-apply", "reason": "", "snapshot": snap,
                     "notes": notes})
    return {"written": written, "skipped": skipped, "snapshot": snap}


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
    if skipped:
        out.append("пропущено:")
        for why in SKIP_ORDER:
            paths = skipped.get(why) or []
            if paths:
                out.append("  %s: %d %s (%s%s)" % (why, len(paths), notes_word(len(paths)), ", ".join(paths[:3]),
                                                     ", …" if len(paths) > 3 else ""))
    for path, target in res.get("denied") or []:
        out.append("%s: %s → %s" % (DENIED, path, target))
    for n in res.get("notes") or []:
        out.append(n)
    if not written:
        out.append("код звіту: %s" % res.get("code", ""))
        if rows:
            out.append("записати: ctx entity apply --apply --code %s" % res.get("code", ""))
    return "\n".join(out) + "\n"
