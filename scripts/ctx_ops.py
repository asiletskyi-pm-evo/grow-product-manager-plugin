#!/usr/bin/env python3
"""Grow PM — operations on the context store (since v3.11.0).

Everything here that writes takes a snapshot first and leaves a journal line after.
Semantics: references/context-protocol.md. Used by the `ctx` command line and, read-only,
by the SessionStart digest.

- lock                       one writer at a time (~/.grow-pm/.ctx.lock, stale after 120 s)
- snapshot / rotate / restore  ~/.grow-pm/snapshots/ — outside any vault

Stdlib only.
"""
import contextlib
import datetime
import hashlib
import json
import os
import re
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx_common as cc  # noqa: E402
import ctx_store as cs  # noqa: E402


class Busy(Exception):
    """Another ctx run holds the lock (exit 4)."""


class Refused(Exception):
    """The change is not allowed: the store exists, a managed region, the provider boundary (exit 4)."""


class Conflict(Exception):
    """A decision is needed (exit 2); `payload` carries the versions."""

    def __init__(self, message, payload=None):
        super().__init__(message)
        self.payload = payload or {}


def _grow(home):
    return os.path.join(home or os.path.expanduser("~"), ".grow-pm")


# -------------------------------------------------------------------- lock
def _alive(pid):
    try:
        os.kill(int(pid), 0)
        return True
    except ProcessLookupError:
        return False
    except (PermissionError, OSError, ValueError, TypeError):
        return True


@contextlib.contextmanager
def lock(home, stale_s=120):
    """Hold `~/.grow-pm/.ctx.lock` for the block; a live lock younger than `stale_s` → Busy."""
    path = os.path.join(_grow(home), ".ctx.lock")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    for attempt in (1, 2):
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
            break
        except FileExistsError:
            try:
                with open(path, encoding="utf-8") as f:
                    held = json.load(f)
            except (OSError, ValueError):
                held = {}
            fresh = time.time() - float(held.get("at") or 0) < stale_s
            if attempt == 2 or (fresh and _alive(held.get("pid"))):
                raise Busy("another ctx run holds %s (pid %s)" % (path, held.get("pid")))
            os.remove(path)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump({"pid": os.getpid(), "at": time.time()}, f)
    try:
        yield path
    finally:
        if os.path.exists(path):
            os.remove(path)


# --------------------------------------------------------------- snapshots
SNAP_RE = re.compile(r"^(\d{8}T\d{6})")


def _files(folder, prefix):
    out = {}
    if os.path.isdir(folder):
        for name in sorted(os.listdir(folder)):
            p = os.path.join(folder, name)
            if os.path.isfile(p) and not name.startswith("."):
                with open(p, "rb") as f:
                    out[prefix + name] = f.read()
    return out


def snapshot(store, copies, home, label):
    """Copy the store and the compiled copies to ~/.grow-pm/snapshots/<time>-<label>/; an identical
    newest snapshot is reused. Returns the snapshot folder."""
    root = os.path.join(_grow(home), "snapshots")
    os.makedirs(root, exist_ok=True)
    files = _files(store.records_dir, "records/")
    files.update(_files(store.state_dir, "state/"))
    if os.path.isfile(store.card_path):
        files["INDEX.md"] = open(store.card_path, "rb").read()
    existed = os.path.isdir(store.records_dir) or os.path.isdir(store.state_dir)
    cps = []
    for n, path in enumerate(copies):
        rel = "copies/%d.md" % n
        if os.path.isfile(path):
            files[rel] = open(path, "rb").read()
        cps.append({"path": path, "file": rel, "existed": os.path.isfile(path)})
    h = hashlib.sha256()
    for rel in sorted(files):
        h.update(rel.encode("utf-8") + b"\0" + files[rel] + b"\0")
    h.update(json.dumps([existed, [(c["path"], c["existed"]) for c in cps]]).encode("utf-8"))
    digest = h.hexdigest()
    newest = sorted(n for n in os.listdir(root) if SNAP_RE.match(n))
    if newest:
        try:
            with open(os.path.join(root, newest[-1], "manifest.json"), encoding="utf-8") as f:
                if json.load(f).get("hash") == digest:
                    return os.path.join(root, newest[-1])
        except (OSError, ValueError):
            pass
    base = time.strftime("%Y%m%dT%H%M%S") + "-" + (cc.slugify(label) or "op")
    name, k = base, 2
    while os.path.exists(os.path.join(root, name)):
        name, k = "%s-%d" % (base, k), k + 1
    snap = os.path.join(root, name)
    for rel, data in files.items():
        p = os.path.join(snap, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            f.write(data)
    manifest = {"label": label, "created": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
                "store": store.root, "store_existed": existed, "copies": cps, "hash": digest}
    os.makedirs(snap, exist_ok=True)
    with open(os.path.join(snap, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    return snap


def rotate(snap_root, keep_last=20, keep_daily_days=14, now=None):
    """Keep the newest `keep_last` snapshots and the newest of each day in the last `keep_daily_days`
    days; remove the rest. Returns the removed folders."""
    now = now or datetime.datetime.now()
    dated = []
    for name in os.listdir(snap_root) if os.path.isdir(snap_root) else []:
        m = SNAP_RE.match(name)
        if m:
            dated.append((datetime.datetime.strptime(m.group(1), "%Y%m%dT%H%M%S"), name))
    dated.sort(reverse=True)
    keep = {name for _, name in dated[:keep_last]}
    first_day = now.date() - datetime.timedelta(days=keep_daily_days - 1)
    seen = set()
    for t, name in dated:
        if t.date() >= first_day and t.date() not in seen:
            seen.add(t.date())
            keep.add(name)
    removed = []
    for _, name in dated:
        if name not in keep:
            shutil.rmtree(os.path.join(snap_root, name))
            removed.append(os.path.join(snap_root, name))
    return removed


def restore(snap_dir, store, copies):
    """Put the store and the compiled copies back exactly as the snapshot holds them."""
    with open(os.path.join(snap_dir, "manifest.json"), encoding="utf-8") as f:
        manifest = json.load(f)
    for folder in (store.records_dir, store.state_dir):
        if os.path.isdir(folder):
            shutil.rmtree(folder)
    if os.path.isfile(store.card_path):
        os.remove(store.card_path)
    if manifest.get("store_existed"):
        for sub, target in (("records", store.records_dir), ("state", store.state_dir)):
            src = os.path.join(snap_dir, sub)
            if os.path.isdir(src):
                shutil.copytree(src, target)
        if os.path.isfile(os.path.join(snap_dir, "INDEX.md")):
            shutil.copy2(os.path.join(snap_dir, "INDEX.md"), store.card_path)
    for c in manifest.get("copies", []):
        if c.get("existed"):
            with open(os.path.join(snap_dir, c["file"]), encoding="utf-8", newline="") as f:
                cs.atomic_write(c["path"], f.read())
        elif os.path.exists(c["path"]):
            os.remove(c["path"])


# ------------------------------------------------------- store and copies
def _read(path):
    with open(path, encoding="utf-8", newline="") as f:
        return f.read()


def store_root_for(context_text, home=None):
    """{storage_root}/_System/context."""
    return os.path.join(cc.storage_root(context_text, home), "_System", "context")


def copies_for(context_path, context_text, home=None):
    """The compiled copies: the context file, plus {storage_root}/_System/local-context.md when a vault holds it."""
    out = [context_path]
    root = cc.storage_root(context_text, home)
    if os.path.normpath(root) != os.path.normpath(_grow(home)):
        mirror = os.path.join(root, "_System", "local-context.md")
        if os.path.normpath(os.path.abspath(mirror)) != os.path.normpath(os.path.abspath(context_path)):
            out.append(mirror)
    return out


def _state_for(recs, text, copies):
    sections = {r["id"]: cs.sha_text(r["body"]) for r in recs}
    return {"records": sections, "order": [r["id"] for r in recs],
            "copies": {p: {"sha": cs.sha_text(text), "sections": dict(sections)} for p in copies}}


def compile_store(store, copies, now):
    """Write each copy that differs from the compiled records, then the card and the state.
    Nothing changed (records, copies, card present) → nothing is written."""
    recs = store.load()
    text = cs.compile_records(recs)
    written = [p for p in copies if not os.path.isfile(p) or _read(p) != text]
    new = _state_for(recs, text, copies)
    old = store.state()
    if not written and os.path.isfile(store.card_path) and {k: old.get(k) for k in new} == new:
        return {"written": [], "card_lines": _read(store.card_path).count("\n"), "changed": False}
    for p in written:
        cs.atomic_write(p, text)
    card = cs.build_card(recs, text, now[:10])
    if not os.path.isfile(store.card_path) or _read(store.card_path) != card:
        cs.atomic_write(store.card_path, card)
    new["compiled_at"] = now
    store.save_state(new)
    return {"written": written, "card_lines": card.count("\n"), "changed": True}


# ------------------------------------------------------------------ migrate
def migrate(context_path, store_root, copies, home, apply, now):
    """Split the context into records and prove the compile gives it back byte for byte; with `apply`,
    snapshot, then write records, state, card and a journal line. The copies are not touched."""
    store = cs.Store(store_root)
    text = _read(context_path)
    frags = cs.split_sections(text)
    recs = cs.assign_ids(frags)
    identical = "".join(f["text"] for f in frags) == text and \
        cs.compile_records([dict(r, body=r["text"]) for r in recs]) == text
    others = [p for p in copies if p != context_path]
    report = {"store": store_root, "identical": identical, "applied": False,
              "records": [{"id": r["id"], "type": r["type"], "lines": r["text"].count("\n")} for r in recs],
              "custom": [r["id"] for r in recs if r["type"] == "custom"],
              "mirror_differs": any(os.path.isfile(p) and _read(p) != text for p in others)}
    if not apply:
        return report
    if store.exists() or os.path.isdir(store.records_dir):
        raise Refused("a context store already exists at %s — see `ctx status`" % store_root)
    if not identical:
        raise Refused("the split does not give the file back byte for byte — nothing migrated")
    snap = snapshot(store, copies, home, "pre-migrate")
    written = []
    for r in recs:
        rec = {k: r[k] for k in ("id", "type", "title", "parent", "order")}
        written.append(store.write(dict(rec, ctx=1, owner="user", source="migrated", modified=now, body=r["text"])))
    same = [context_path] + [p for p in others if os.path.isfile(p) and _read(p) == text]
    state = _state_for(written, text, same)
    state["compiled_at"] = now
    store.save_state(state)
    cs.atomic_write(store.card_path, cs.build_card(written, text, now[:10]))
    store.journal({"ts": now, "op": "migrate", "ids": [r["id"] for r in written], "source": "migrate",
                   "reason": "", "snapshot": snap})
    report.update(applied=True, snapshot=snap)
    return report


# --------------------------------------------------------------------- sync
def _key(x):
    return (x["type"], x["title"])


def _similar(old_body, new_text):
    old = [l.strip() for l in old_body.splitlines() if l.strip()]
    new = {l.strip() for l in new_text.splitlines() if l.strip()}
    return bool(old) and sum(l in new for l in old) * 2 >= len(old)


def _copy_changes(text, rec_by, base, order):
    """One copy against its last compile: edits {id: text}, removes [id], renames {id: (text, title)},
    adds [(fragment, preceding id)]."""
    frags = cs.split_sections(text)
    sections = base.get("sections", {})
    by_key = {}
    for rid in sections:
        if rid in rec_by:
            by_key.setdefault(_key(rec_by[rid]), []).append(rid)
    taken, matched = set(), []
    for f in frags:
        rid = next((i for i in by_key.get(_key(f), []) if i not in taken), None)
        if rid:
            taken.add(rid)
        matched.append(rid)
    loose = [rid for rid in sections if rid in rec_by and rid not in taken]
    prev_old = {rid: (order[k - 1] if k else None) for k, rid in enumerate(order)}
    renames, edits, adds = {}, {}, []
    for k, f in enumerate(frags):
        if matched[k] is not None:
            continue
        prev_new = next((matched[j] for j in range(k - 1, -1, -1) if matched[j] is not None), None)
        for rid in loose:
            if rid not in renames and prev_old.get(rid) == prev_new and _similar(rec_by[rid]["body"], f["text"]):
                renames[rid] = (f["text"], f["title"])
                matched[k] = rid
                break
    for k, f in enumerate(frags):
        rid = matched[k]
        if rid is None:
            prev = next((matched[j] for j in range(k - 1, -1, -1) if matched[j] is not None), None)
            adds.append((f, prev))
        elif rid not in renames and cs.sha_text(f["text"]) != sections.get(rid):
            edits[rid] = f["text"]
    removes = [rid for rid in loose if rid not in renames]
    return edits, removes, renames, adds


def plan_sync(store, copies):
    """What the copies changed since the last compile, merged across copies and against direct record edits."""
    recs = store.load()
    state = store.state()
    rec_by = {r["id"]: r for r in recs}
    base_records = state.get("records", {})
    record_changes = sorted(rid for rid, r in rec_by.items() if base_records.get(rid) != cs.sha_text(r["body"]))
    changes, adds = {}, []
    for p in copies:
        base = state.get("copies", {}).get(p)
        if not base or not os.path.isfile(p):
            continue
        text = _read(p)
        if cs.sha_text(text) == base.get("sha"):
            continue
        ed, rm, rn, ad = _copy_changes(text, rec_by, base, state.get("order", []))
        for rid, t in ed.items():
            changes.setdefault(rid, {})[p] = ("edit", t)
        for rid in rm:
            changes.setdefault(rid, {})[p] = ("remove", None)
        for rid, v in rn.items():
            changes.setdefault(rid, {})[p] = ("rename", v)
        for f, prev in ad:
            if not any(a["text"] == f["text"] for a in adds):
                adds.append({"text": f["text"], "type": f["type"], "title": f["title"], "after": prev, "copy": p})
    plan = {"edits": [], "removes": [], "renames": [], "adds": adds, "record_changes": record_changes,
            "conflicts": [], "suspicious_removal": False}
    for rid, per in changes.items():
        versions = {p: (v[1] if v[0] == "edit" else v[1][0] if v[0] == "rename" else None) for p, v in per.items()}
        kinds = set(per.values())
        if len(kinds) > 1:
            plan["conflicts"].append({"id": rid, "reasons": ["the copies disagree"],
                                      "versions": dict(versions, record=rec_by[rid]["body"])})
            continue
        kind, val = next(iter(kinds))
        if rid in record_changes:
            if versions[next(iter(per))] != rec_by[rid]["body"]:
                plan["conflicts"].append({"id": rid, "reasons": ["changed in the record and in a copy"],
                                          "versions": dict(versions, record=rec_by[rid]["body"])})
            continue
        copy = next(iter(per))
        if kind == "edit":
            plan["edits"].append({"id": rid, "text": val, "copy": copy})
        elif kind == "remove":
            plan["removes"].append(rid)
        else:
            plan["renames"].append({"id": rid, "text": val[0], "title": val[1], "copy": copy})
    plan["conflicts"].sort(key=lambda c: c["id"])
    plan["suspicious_removal"] = len(plan["removes"]) >= 3
    return plan


def _insert(store, adds, source, now):
    """New records for added sections, placed after their preceding record; orders renumbered 10, 20, …"""
    recs = {r["id"]: r for r in store.load()}
    ids = [rid for rid in sorted(recs, key=lambda i: recs[i]["order"])]
    chain, new_ids = {}, []
    for a in adds:
        frag = {"type": a["type"], "title": a["title"], "heading": None, "parent_index": None, "text": a["text"]}
        rec = cs.assign_ids([frag], set(recs))[0]
        anchor = chain.get(a["after"], a["after"])
        pos = ids.index(anchor) + 1 if anchor in ids else 0
        ids.insert(pos, rec["id"])
        chain[a["after"]] = rec["id"]
        parent = None
        if rec["type"] in ("product", "team"):
            parent = next((i for i in reversed(ids[:pos]) if recs[i]["type"] == "org"), None)
        recs[rec["id"]] = {"id": rec["id"], "type": rec["type"], "title": rec["title"], "parent": parent, "order": 0,
                           "ctx": 1, "owner": "user", "source": source or "import", "modified": now, "body": a["text"]}
        new_ids.append(rec["id"])
    for k, rid in enumerate(ids):
        if recs[rid]["order"] != (k + 1) * 10 or rid in new_ids:
            store.write(dict(recs[rid], order=(k + 1) * 10))
    return new_ids


def apply_sync(store, plan, copies, home, source, reason, now, resolve=None, accept_removals=False):
    """Apply a plan from plan_sync: snapshot, records, journal, compile. Unresolved conflicts, or three and
    more removals without `accept_removals`, raise Conflict and change nothing."""
    resolve = resolve or {}
    open_conflicts = [c for c in plan["conflicts"] if c["id"] not in resolve]
    removal_gate = plan["suspicious_removal"] and not accept_removals
    if open_conflicts or removal_gate:
        raise Conflict("a decision is needed before the sync",
                       {"conflicts": open_conflicts, "suspicious_removal": removal_gate, "removes": plan["removes"]})
    if not any(plan[k] for k in ("edits", "removes", "renames", "adds", "record_changes", "conflicts")):
        return {"changed": [], "removed": [], "added": [], "snapshot": None, "compiled": compile_store(store, copies, now)}
    snap = snapshot(store, copies, home, "sync")
    recs = {r["id"]: r for r in store.load()}
    src = lambda p: source or ("import:home" if p == copies[0] else "import:mirror")
    changed, removed = [], []
    for e in plan["edits"]:
        store.write(dict(recs[e["id"]], body=e["text"], source=src(e["copy"]), modified=now))
        changed.append(e["id"])
    for r in plan["renames"]:
        store.write(dict(recs[r["id"]], body=r["text"], title=r["title"], source=src(r["copy"]), modified=now))
        changed.append(r["id"])
    for c in plan["conflicts"]:
        if resolve[c["id"]] == "file":
            ver = next((c["versions"][p] for p in copies if p in c["versions"]), None)
            if ver is None:
                store.remove(c["id"])
                removed.append(c["id"])
            else:
                store.write(dict(recs[c["id"]], body=ver, source=source or "import:resolve", modified=now))
                changed.append(c["id"])
    for rid in plan["removes"]:
        store.remove(rid)
        removed.append(rid)
    added = _insert(store, plan["adds"], source, now) if plan["adds"] else []
    store.journal({"ts": now, "op": "sync", "ids": changed + removed + added, "source": source or "import",
                   "reason": reason, "snapshot": snap})
    return {"changed": changed, "removed": removed, "added": added, "snapshot": snap,
            "compiled": compile_store(store, copies, now)}


# ------------------------------------------------------- digest (read-only)
def status_summary(context_path, home=None):
    """{records, card_lines, pending, conflicts} for the SessionStart digest; None without a store or on any
    error. Reads only."""
    try:
        text = _read(context_path)
        store = cs.Store(store_root_for(text, home))
        if not store.exists():
            return None
        recs = store.load()
        plan = plan_sync(store, copies_for(context_path, text, home))
        card = _read(store.card_path).count("\n") if os.path.isfile(store.card_path) else 0
        return {"records": len(recs), "card_lines": card,
                "pending": sum(len(plan[k]) for k in ("edits", "adds", "removes", "renames", "record_changes")),
                "conflicts": len(plan["conflicts"]) + (1 if plan["suspicious_removal"] else 0)}
    except Exception:
        return None
