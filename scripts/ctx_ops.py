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
import ctx_schema as sc  # noqa: E402


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
    """{prefix + relative path: bytes} of the files under `folder`, subfolders too (the block bases live in
    `state/blocks/<repo>/`). A hidden name — a file or a folder — and a linked folder are skipped."""
    out = {}
    if os.path.isdir(folder):
        for name in sorted(os.listdir(folder)):
            p = os.path.join(folder, name)
            if name.startswith("."):
                continue
            if os.path.isfile(p):
                with open(p, "rb") as f:
                    out[prefix + name] = f.read()
            elif os.path.isdir(p) and not os.path.islink(p):
                out.update(_files(p, prefix + name + "/"))
    return out


def snapshot(store, copies, home, label):
    """Copy the store and the compiled copies to ~/.grow-pm/snapshots/<time>-<label>/; an identical
    newest snapshot is reused. Returns the snapshot folder."""
    root = os.path.join(_grow(home), "snapshots")
    os.makedirs(root, exist_ok=True)
    files = _files(store.records_dir, "records/")
    files.update(_files(store.state_dir, "state/"))
    if os.path.isdir(store.archive_dir):
        for year in sorted(os.listdir(store.archive_dir)):
            files.update(_files(os.path.join(store.archive_dir, year), "archive/%s/" % year))
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
    cs.check_target(snap)
    for rel, data in files.items():
        p = os.path.join(snap, rel)
        cs.check_target(p)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            f.write(data)
    manifest = {"label": label, "created": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
                "store": store.root, "store_existed": existed, "copies": cps, "hash": digest}
    os.makedirs(snap, exist_ok=True)
    with open(os.path.join(snap, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    rotate(root, protect=snap)
    return snap


def rotate(snap_root, keep_last=20, keep_daily_days=14, now=None, protect=None):
    """Keep the newest `keep_last` snapshots and the newest of each day in the last `keep_daily_days`
    days, and `protect`; remove the rest. Returns the removed folders."""
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
    if protect:
        keep.add(os.path.basename(protect))
    removed = []
    for _, name in dated:
        if name not in keep:
            cs.check_target(os.path.join(snap_root, name))
            shutil.rmtree(os.path.join(snap_root, name))
            removed.append(os.path.join(snap_root, name))
    return removed


def restore(snap_dir, store, copies):
    """Put the store and the compiled copies back as the snapshot holds them. The copies are the current
    ones, matched by position (0 = home copy, 1 = vault mirror): a path in the manifest is never written
    or deleted. Returns the manifest entries with no current copy (skipped)."""
    with open(os.path.join(snap_dir, "manifest.json"), encoding="utf-8") as f:
        manifest = json.load(f)
    entries = manifest.get("copies", [])
    for p in [store.records_dir, store.state_dir, store.archive_dir, store.card_path] + list(copies[:len(entries)]):
        cs.check_target(p)
    for folder in (store.records_dir, store.state_dir, store.archive_dir):
        if os.path.isdir(folder):
            shutil.rmtree(folder)
    if os.path.isfile(store.card_path):
        os.remove(store.card_path)
    if manifest.get("store_existed"):
        for sub, target in (("records", store.records_dir), ("state", store.state_dir), ("archive", store.archive_dir)):
            src = os.path.join(snap_dir, sub)
            if os.path.isdir(src):
                shutil.copytree(src, target)
        if os.path.isfile(os.path.join(snap_dir, "INDEX.md")):
            shutil.copy2(os.path.join(snap_dir, "INDEX.md"), store.card_path)
    skipped = []
    for n, c in enumerate(entries):
        if n >= len(copies):
            skipped.append(c.get("path") or "?")
            continue
        if c.get("existed"):
            with open(os.path.join(snap_dir, c["file"]), encoding="utf-8", newline="") as f:
                cs.atomic_write(copies[n], f.read())
        elif os.path.exists(copies[n]):
            os.remove(copies[n])
    return skipped


def consistent_records(store, copies):
    """After `restore`: a record whose text is not the one the last compile saved a hash for was already edited
    in its file (Obsidian) when the snapshot was taken — an import's snapshot holds the edit in the records and
    the previous compile in the copies. Put its body back to the section of the home copy (copy 0) whose hash is
    the saved one; the frontmatter stays. A record with no such section — no home copy, or the copy was edited
    too — and a record the last compile did not know are left as they are, never guessed. Returns the ids changed."""
    saved = store.state().get("records", {})
    if not saved or not copies or not os.path.isfile(copies[0]):
        return []
    off = [r for r in store.load() if r["id"] in saved and cs.sha_text(r["body"]) != saved[r["id"]]]
    if not off:
        return []
    sections = {cs.sha_text(f["text"]): f["text"] for f in cs.split_sections(_read(copies[0]))}
    changed = []
    for r in off:
        text = sections.get(saved[r["id"]])
        if text is not None:
            store.write(dict(r, body=text))
            changed.append(r["id"])
    return changed


# ------------------------------------------------------- store and copies
def _read(path):
    return cs.read_text(path)


def allowed_roots(home, context_text):
    """Where ctx may write: ~/.grow-pm and the storage root (spec §7a)."""
    return (_grow(home), cc.storage_root(context_text, home))


def store_root_for(context_text, home=None):
    """{storage_root}/_System/context."""
    return os.path.join(cc.storage_root(context_text, home), "_System", "context")


def copies_for(context_path, context_text, home=None):
    """The compiled copies as real paths — links resolved, so a file linked to the mirror is one copy and
    stays a link: the context file, plus {storage_root}/_System/local-context.md when a vault holds it."""
    first = os.path.realpath(context_path)
    out = [first]
    root = cc.storage_root(context_text, home)
    if os.path.normpath(root) != os.path.normpath(_grow(home)):
        mirror = os.path.realpath(os.path.join(root, "_System", "local-context.md"))
        if mirror != first:
            out.append(mirror)
    return out


def _baseline(state, path):
    """The last compile's hashes for a copy, under whatever spelling of its path they were saved."""
    saved = state.get("copies", {})
    if path in saved:
        return saved[path]
    return next((v for k, v in saved.items() if os.path.realpath(k) == os.path.realpath(path)), None)


def _state_for(recs, text, copies):
    sections = {r["id"]: cs.sha_text(r["body"]) for r in recs}
    return {"records": sections, "order": [r["id"] for r in recs],
            "copies": {p: {"sha": cs.sha_text(text), "sections": dict(sections)} for p in copies}}


def compile_store(store, copies, now, home, snap=None):
    """Write each copy that differs from the compiled records, then the card and the state.
    Nothing changed (records, copies, card present) → nothing is written. A copy is never replaced or
    created without a snapshot: when the caller took none (`snap`), one is taken here and the rewrite
    gets its own journal line."""
    recs = store.load()
    text = cs.compile_records(recs)
    written = [p for p in copies if not os.path.isfile(p) or _read(p) != text]
    new = _state_for(recs, text, copies)
    old = store.state()
    new["freshness_since"] = old.get("freshness_since") or now[:10]
    stale, archived = card_marks(store, recs, now[:10], state=new)
    new["stale"] = sorted(stale)
    if not written and os.path.isfile(store.card_path) and {k: old.get(k) for k in new} == new:
        return {"written": [], "card_lines": _read(store.card_path).count("\n"), "changed": False, "snapshot": None}
    own = bool(written) and snap is None
    if own:
        snap = snapshot(store, copies, home, "compile")
    for p in written:
        cs.atomic_write(p, text)
    card = cs.build_card(recs, text, now[:10], stale=stale, archived=archived, repos=card_repos(store, recs, text, home))
    if not os.path.isfile(store.card_path) or _read(store.card_path) != card:
        cs.atomic_write(store.card_path, card)
    new["compiled_at"] = now
    store.save_state(new)
    note_store(home, store.root)
    if own:
        what = ["the home copy" if p == copies[0] else "the vault mirror" for p in written]
        store.journal({"ts": now, "op": "compile", "ids": [], "source": "compile", "snapshot": snap,
                       "reason": "rewrote %s to match the records" % " and ".join(what)})
    return {"written": written, "card_lines": card.count("\n"), "changed": True, "snapshot": snap if own else None}


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
    home_copy, others = copies[0], copies[1:]
    report = {"store": store_root, "identical": identical, "applied": False,
              "records": [{"id": r["id"], "type": r["type"], "lines": r["text"].count("\n")} for r in recs],
              "custom": [r["id"] for r in recs if r["type"] == "custom"],
              "mirror_differs": any(os.path.isfile(p) and _read(p) != text for p in others)}
    if not apply:
        return report
    if not store.exists() and os.path.isdir(store.records_dir):
        raise Refused(half_migrated(store_root))
    if store.exists():
        raise Refused("a context store already exists at %s — see `ctx status`" % store_root)
    if not identical:
        raise Refused("the split does not give the file back byte for byte — nothing migrated")
    vault = cc.vault_root(text)
    if vault and not os.path.isdir(os.path.expanduser(vault)):
        raise cs.StoreError("the vault folder %s does not exist — check ## Obsidian Vaults" % vault)
    snap = snapshot(store, copies, home, "pre-migrate")
    written = []
    for r in recs:
        rec = {k: r[k] for k in ("id", "type", "title", "parent", "order")}
        written.append(store.write(dict(rec, ctx=1, owner="user", source="migrated", modified=now, body=r["text"])))
    same = [home_copy] + [p for p in others if os.path.isfile(p) and _read(p) == text]
    state = _state_for(written, text, same)
    state["compiled_at"] = now
    state["freshness_since"] = now[:10]
    state["stale"] = []
    store.save_state(state)
    note_store(home, store_root)
    cs.atomic_write(store.card_path, cs.build_card(written, text, now[:10], repos=card_repos(store, written, text, home)))
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
    adds [(fragment, preceding id)], and the ids in the copy's order."""
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
                renames[rid] = (f["text"], f["title"], f["type"])
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
    return edits, removes, renames, adds, [rid for rid in matched if rid is not None]


def plan_sync(store, copies):
    """What the copies changed since the last compile, merged across copies and against direct record edits."""
    recs = store.load()
    state = store.state()
    rec_by = {r["id"]: r for r in recs}
    order = state.get("order", [])
    missing = [rid for rid in order if rid not in rec_by]
    base_records = state.get("records", {})
    record_changes = sorted(rid for rid, r in rec_by.items() if base_records.get(rid) != cs.sha_text(r["body"]))
    changes, adds, reorders = {}, [], {}
    for p in copies:
        base = _baseline(state, p)
        if not base or not os.path.isfile(p):
            continue
        text = _read(p)
        if cs.sha_text(text) == base.get("sha"):
            continue
        ed, rm, rn, ad, seq = _copy_changes(text, rec_by, base, order)
        kept = set(seq)
        if seq != [rid for rid in order if rid in kept]:
            reorders[p] = seq
        for rid, t in ed.items():
            changes.setdefault(rid, {})[p] = ("edit", t)
        for rid in rm:
            changes.setdefault(rid, {})[p] = ("remove", None)
        for rid, v in rn.items():
            changes.setdefault(rid, {})[p] = ("rename", v)
        gone = {base_records.get(rid) for rid in missing}   # a missing record's own unchanged section is not new
        for f, prev in ad:
            if cs.sha_text(f["text"]) not in gone and not any(a["text"] == f["text"] for a in adds):
                adds.append({"text": f["text"], "type": f["type"], "title": f["title"], "after": prev, "copy": p})
    plan = {"edits": [], "removes": [], "renames": [], "adds": adds, "record_changes": record_changes,
            "conflicts": [], "suspicious_removal": False, "missing": missing,
            "reorder": reorders.get(copies[0]) or next(iter(reorders.values()), [])}
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
            plan["renames"].append({"id": rid, "text": val[0], "title": val[1], "type": val[2], "copy": copy})
    plan["conflicts"].sort(key=lambda c: c["id"])
    plan["suspicious_removal"] = len(plan["removes"]) >= 3
    return plan


PENDING = ("edits", "adds", "removes", "renames", "record_changes")


def pending(plan):
    """{kind: count} of what a sync would import; a changed order counts once."""
    out = {k: len(plan[k]) for k in PENDING}
    out["reorder"] = 1 if plan.get("reorder") else 0
    return out


def _missing_message(ids, home):
    return ("records not available locally: %s — still downloading or syncing (iCloud, Obsidian Sync), or "
            "deleted; nothing was compiled and local-context.md is untouched. Open the vault so they download, "
            "or restore them (Obsidian's trash, or a snapshot in %s), then run again; to drop them for good: "
            "`ctx sync --accept-removals`" % (", ".join(i + ".md" for i in ids), os.path.join(_grow(home), "snapshots")))


def _reorder(store, seq):
    """Records follow the copy's order; a record the copy does not hold stays after its old predecessor.
    Orders renumbered 10, 20, …; returns the ids whose order changed."""
    recs = {r["id"]: r for r in store.load()}
    old = [r["id"] for r in sorted(recs.values(), key=lambda r: r["order"])]
    final = [i for i in seq if i in recs]
    for k, rid in enumerate(old):
        if rid not in final:
            prev = next((old[j] for j in range(k - 1, -1, -1) if old[j] in final), None)
            final.insert(final.index(prev) + 1 if prev else 0, rid)
    moved = []
    for k, rid in enumerate(final):
        if recs[rid]["order"] != (k + 1) * 10:
            store.write(dict(recs[rid], order=(k + 1) * 10))
            moved.append(rid)
    return moved


def _insert(store, adds, source, now):
    """New records for added sections, placed after their preceding record; orders renumbered 10, 20, …"""
    recs = {r["id"]: r for r in store.load()}
    ids = [rid for rid in sorted(recs, key=lambda i: recs[i]["order"])]
    chain, new_ids = {}, []
    for a in adds:
        frag = {"type": a["type"], "title": a["title"], "heading": None, "parent_index": None, "text": a["text"]}
        rec = cs.assign_ids([frag], set(recs) | store.reserved_ids())[0]
        anchor = chain.get(a["after"], a["after"])
        pos = ids.index(anchor) + 1 if anchor in ids else 0
        ids.insert(pos, rec["id"])
        chain[a["after"]] = rec["id"]
        parent = None
        if rec["type"] in ("product", "team"):
            parent = next((i for i in reversed(ids[:pos]) if recs[i]["type"] == "org"), None)
        recs[rec["id"]] = {"id": rec["id"], "type": rec["type"], "title": rec["title"], "parent": parent, "order": 0,
                           "verified": now[:10],
                           "ctx": 1, "owner": "user", "source": a.get("source") or source or "import", "modified": now,
                           "body": a["text"]}
        new_ids.append(rec["id"])
    ended = set()
    for rid in new_ids:
        k = ids.index(rid)
        if k and not recs[ids[k - 1]]["body"].endswith("\n"):
            recs[ids[k - 1]] = dict(recs[ids[k - 1]], body=recs[ids[k - 1]]["body"] + "\n")
            ended.add(ids[k - 1])
    for k, rid in enumerate(ids):
        if recs[rid]["order"] != (k + 1) * 10 or rid in new_ids or rid in ended:
            store.write(dict(recs[rid], order=(k + 1) * 10))
    return new_ids


def touch(rec, now):
    """The record verified today."""
    return dict(rec, verified=now[:10])


def verify(store, copies, home, ids, now, stale=False):
    """Mark records verified today — the given ids, or with `stale` every stale record; snapshot, write,
    one journal line, compile. The lock and the import are the caller's. Returns the ids verified."""
    recs = {r["id"]: r for r in store.load()}
    if stale:
        ids = sc.stale_ids(list(recs.values()), store.state(), now[:10])
    unknown = [i for i in ids if i not in recs]
    if unknown:
        raise cs.StoreError("no record %s — `ctx list` shows the ids" % ", ".join(unknown))
    if not ids:
        return []
    snap = snapshot(store, copies, home, "verify")
    for rid in ids:
        store.write(touch(recs[rid], now))
    store.journal({"ts": now, "op": "verify", "ids": list(ids), "source": "ctx-verify", "reason": "", "snapshot": snap})
    compile_store(store, copies, now, home, snap)
    return list(ids)


def apply_sync(store, plan, copies, home, source, reason, now, resolve=None, accept_removals=False):
    """Apply a plan from plan_sync: snapshot, records, journal, compile. Unresolved conflicts, or three and
    more removals without `accept_removals`, raise Conflict and change nothing."""
    resolve = resolve or {}
    if plan["missing"] and not accept_removals:
        raise cs.StoreError(_missing_message(plan["missing"], home))
    open_conflicts = [c for c in plan["conflicts"] if c["id"] not in resolve]
    removal_gate = plan["suspicious_removal"] and not accept_removals
    if open_conflicts or removal_gate:
        raise Conflict("a decision is needed before the sync",
                       {"conflicts": open_conflicts, "suspicious_removal": removal_gate, "removes": plan["removes"]})
    if not any(plan[k] for k in ("edits", "removes", "renames", "adds", "record_changes", "conflicts", "missing", "reorder")):
        comp = compile_store(store, copies, now, home)
        return {"changed": [], "removed": [], "added": [], "moved": [], "snapshot": comp["snapshot"], "compiled": comp}
    snap = snapshot(store, copies, home, "sync")
    recs = {r["id"]: r for r in store.load()}
    src = lambda p: (source if source not in (None, "compile") else
                     ("import:home" if p == copies[0] else "import:mirror"))
    changed, removed = [], []
    for e in plan["edits"]:
        store.write(touch(dict(recs[e["id"]], body=e["text"], source=src(e["copy"]), modified=now), now))
        changed.append(e["id"])
    for r in plan["renames"]:
        store.write(touch(dict(recs[r["id"]], body=r["text"], title=r["title"], type=r.get("type") or recs[r["id"]]["type"],
                               source=src(r["copy"]), modified=now), now))
        changed.append(r["id"])
    for c in plan["conflicts"]:
        if resolve[c["id"]] == "file":
            ver = next((c["versions"][p] for p in copies if p in c["versions"]), None)
            if ver is None:
                put_in_trash(home, recs[c["id"]], _before(store.state().get("order", []), c["id"]), now)
                store.remove(c["id"])
                removed.append(c["id"])
            else:
                store.write(touch(dict(recs[c["id"]], body=ver, source=source or "import:resolve", modified=now), now))
                changed.append(c["id"])
    order = store.state().get("order", [])
    for rid in plan["removes"] + plan["missing"]:
        rec = recs.get(rid) or _from_copy(store, copies, rid, now)
        if rec:
            put_in_trash(home, rec, _before(order, rid), now)
        store.remove(rid)
        removed.append(rid)
    for rid in plan["record_changes"]:                  # edited in Obsidian: the body stays, verified moves
        if rid in recs and rid not in changed and rid not in removed:
            store.write(touch(recs[rid], now))
    moved = _reorder(store, plan["reorder"]) if plan["reorder"] else []
    added = _insert(store, [dict(a, source=src(a.get("copy"))) for a in plan["adds"]], source, now) if plan["adds"] else []
    _reparent(store)
    ids = changed + removed + [i for i in moved if i not in changed] + added
    ids += [i for i in plan["record_changes"] if i not in ids]
    store.journal({"ts": now, "op": "sync", "ids": ids, "source": source or "import", "reason": reason, "snapshot": snap})
    return {"changed": changed, "removed": removed, "added": added, "moved": moved, "snapshot": snap,
            "compiled": compile_store(store, copies, now, home, snap)}


def _reparent(store):
    """Products and teams belong to the organisation above them in the file; returns the ids re-parented."""
    moved, org = [], None
    for r in store.load():
        if r["type"] == "org":
            org = r["id"]
        elif r["type"] in ("product", "team") and r.get("parent") != org:
            store.write(dict(r, parent=org))
            moved.append(r["id"])
    return moved


def half_migrated(root):
    return ("half-migrated store at %s: remove %s to start over, or restore the pre-migrate snapshot"
            % (root, os.path.join(root, "records")))


def _last_store_path(home):
    return os.path.join(_grow(home), ".ctx-last-store")


def note_store(home, root):
    """Remember the store's root (diagnosis only: never used to find the store)."""
    path = _last_store_path(home)
    if not os.path.isfile(path) or _read(path).strip() != root:
        cs.atomic_write(path, root + "\n")


def store_unavailable(context_text, home=None):
    """The last store root, when the context's own root has no store but a store was used before — a vault
    not mounted, moved, or switched off; else None. Reads only."""
    path = _last_store_path(home)
    if not os.path.isfile(path):
        return None
    last = _read(path).strip()
    current = store_root_for(context_text, home)
    if not last or cs.Store(current).exists():
        return None
    if last != current:
        return last                                    # the store lives elsewhere (a vault switched off)
    vault = cc.vault_root(context_text)
    return last if vault and not os.path.isdir(os.path.expanduser(vault)) else None


def forget_store(home):
    """Drop the note of the last store (after `undo` removed the store on purpose)."""
    path = _last_store_path(home)
    if os.path.isfile(path):
        cs.check_target(path)
        os.remove(path)


# ---------------------------------------------------------------- lifecycle
TRASH_DAYS = 30
TRASH_RE = re.compile(r"^(\d{8}T\d{6})-(.+)\.md$")


def _before(order, rid):
    k = order.index(rid) if rid in order else -1
    return order[k - 1] if k > 0 else None


def _from_copy(store, copies, rid, now):
    """A record missing on disk, rebuilt from the canonical copy's section with its last compiled hash."""
    base = store.state().get("records", {}).get(rid)
    if not base or not copies or not os.path.isfile(copies[0]):
        return None
    frag = next((f for f in cs.split_sections(_read(copies[0])) if cs.sha_text(f["text"]) == base), None)
    if not frag:
        return None
    return {"ctx": 1, "id": rid, "type": frag["type"], "title": frag["title"], "parent": None, "order": 0,
            "owner": "user", "source": "import:home", "modified": now, "body": frag["text"]}


def trash_root(home):
    return os.path.join(_grow(home), "trash")


def put_in_trash(home, rec, former_after, now):
    """A removed record into ~/.grow-pm/trash/<time>-<id>.md (kept TRASH_DAYS days)."""
    root = trash_root(home)
    base = time.strftime("%Y%m%dT%H%M%S") + "-" + rec["id"]
    path, k = os.path.join(root, base + ".md"), 2
    while os.path.exists(path):
        path, k = os.path.join(root, "%s-%d.md" % (base, k)), k + 1
    keep = {k2: v for k2, v in rec.items() if k2 not in ("path", "archived", "archived_reason")}
    cs.atomic_write(path, cs.render_record(dict(keep, trashed=now, former_after=former_after)))
    return path


def trash_entries(home):
    """[(path, record)] in the trash, newest first; unreadable files are skipped."""
    root, out = trash_root(home), []
    for name in sorted(os.listdir(root), reverse=True) if os.path.isdir(root) else []:
        if TRASH_RE.match(name):
            try:
                out.append((os.path.join(root, name), cs.parse_record(_read(os.path.join(root, name)))))
            except (OSError, UnicodeDecodeError, ValueError, cs.StoreError):
                continue
    return out


def purge_trash(home, now=None):
    """Remove trash entries older than TRASH_DAYS days; returns the removed paths."""
    now = now or datetime.datetime.now()
    root, gone = trash_root(home), []
    for name in sorted(os.listdir(root)) if os.path.isdir(root) else []:
        m = TRASH_RE.match(name)
        if m and now - datetime.datetime.strptime(m.group(1), "%Y%m%dT%H%M%S") > datetime.timedelta(days=TRASH_DAYS):
            path = os.path.join(root, name)
            cs.check_target(path)
            os.remove(path)
            gone.append(path)
    return gone


def _live(store, copies, home, now):
    """Import direct edits first, then the live records by id."""
    apply_sync(store, plan_sync(store, copies), copies, home, None, "", now)
    return {r["id"]: r for r in store.load()}


def invalidate(store, copies, home, rid, reason, now):
    """Mark a record no longer current: the ctx status region after its heading; it stays in the copies."""
    if not (reason or "").strip():
        raise ValueError("invalidate needs --reason")
    recs = _live(store, copies, home, now)
    if rid not in recs:
        raise cs.StoreError("no record %s — `ctx list` shows the ids" % rid)
    if recs[rid]["type"] == "header":
        raise Refused("the file header cannot be marked invalid")
    snap = snapshot(store, copies, home, "invalidate")
    body = cs.set_status_region(recs[rid]["body"], now[:10], reason.strip())
    store.write(dict(recs[rid], body=body, source="ctx-invalidate", modified=now))
    store.journal({"ts": now, "op": "invalidate", "ids": [rid], "source": "ctx-invalidate", "reason": reason,
                   "snapshot": snap})
    comp = compile_store(store, copies, now, home, snap)
    return {"id": rid, "snapshot": snap, "written": comp["written"]}


def archive(store, copies, home, rid, reason, now):
    """Move a record to {store}/archive/<year>/<id>.md; it leaves the copies, its id stays reserved."""
    recs = _live(store, copies, home, now)
    if rid not in recs:
        raise cs.StoreError("no record %s — `ctx list` shows the ids" % rid)
    if recs[rid]["type"] == "header":
        raise Refused("the file header cannot be archived")
    order = [r["id"] for r in sorted(recs.values(), key=lambda r: r["order"])]
    snap = snapshot(store, copies, home, "archive")
    rec = dict(recs[rid], status="archived", archived=now[:10], archived_reason=(reason or "").strip() or None,
               former_after=_before(order, rid))
    cs.atomic_write(os.path.join(store.archive_dir, now[:4], rid + ".md"), cs.render_record(rec))
    store.remove(rid)
    store.journal({"ts": now, "op": "archive", "ids": [rid], "source": "ctx-archive", "reason": reason or "",
                   "snapshot": snap})
    comp = compile_store(store, copies, now, home, snap)
    return {"id": rid, "snapshot": snap, "written": comp["written"]}


def _place_after(recs, ids, rec):
    """Where a record whose predecessor is gone goes back: a product or a team stays inside an organisation
    (after the last product/team of its organisation, else after the organisation itself, else in the last
    organisation); anything else at the end."""
    if rec["type"] in ("product", "team"):
        orgs = [i for i in ids if recs[i]["type"] == "org"]
        org = rec.get("parent") if rec.get("parent") in orgs else (orgs[-1] if orgs else None)
        if org:
            kids = [i for i in ids if recs[i]["type"] in ("product", "team") and recs[i].get("parent") == org]
            return kids[-1] if kids else org
    return ids[-1] if ids else None


def restore_record(store, copies, home, rid, now):
    """Bring a record back: an invalid one becomes current; else from the archive, else the newest in the
    trash, at its former place (after `former_after`, else after its last sibling, else at the end)."""
    recs = _live(store, copies, home, now)
    source, origin = None, None
    if rid in recs:
        if not cs.has_status_region(recs[rid]["body"]):
            arch = rid in store.reserved_ids() or any(r["id"] == rid for _, r in trash_entries(home))
            raise Refused("id %s is taken by a current record — archive or rename it first" % rid if arch else
                          "%s is current — nothing to restore" % rid)
        snap = snapshot(store, copies, home, "restore")
        store.write(touch(dict(recs[rid], body=cs.clear_status_region(recs[rid]["body"]), source="ctx-restore",
                               modified=now), now))
    else:
        found = next((r for r in store.archived() if r["id"] == rid), None)
        if found:
            source, origin = found, found["path"]
        else:
            hit = next(((p, r) for p, r in trash_entries(home) if r["id"] == rid), None)
            if not hit:
                raise cs.StoreError("nothing to restore for %s — not invalid, not in the archive or the trash" % rid)
            origin, source = hit
        snap = snapshot(store, copies, home, "restore")
        ids = [r["id"] for r in sorted(recs.values(), key=lambda r: r["order"])]
        after = source.get("former_after")
        if after not in ids:
            after = _place_after(recs, ids, source)
        pos = ids.index(after) + 1 if after in ids else len(ids)
        ids.insert(pos, rid)
        rec = {k: v for k, v in source.items() if k not in ("path", "archived", "archived_reason", "former_after", "trashed")}
        rec = touch(dict(rec, status=None), now)
        if pos < len(ids) - 1 and not rec["body"].endswith("\n"):
            rec["body"] += "\n"                      # a former last record without a final newline
        recs[rid] = rec
        ended = set()
        if pos and not recs[ids[pos - 1]]["body"].endswith("\n"):
            recs[ids[pos - 1]] = dict(recs[ids[pos - 1]], body=recs[ids[pos - 1]]["body"] + "\n")
            ended.add(ids[pos - 1])
        for k, i in enumerate(ids):
            if recs[i]["order"] != (k + 1) * 10 or i == rid or i in ended:
                store.write(dict(recs[i], order=(k + 1) * 10))
        _reparent(store)
        cs.check_target(origin)
        os.remove(origin)
    store.journal({"ts": now, "op": "restore", "ids": [rid], "source": "ctx-restore", "reason": origin or "invalid",
                   "snapshot": snap})
    comp = compile_store(store, copies, now, home, snap)
    return {"id": rid, "snapshot": snap, "written": comp["written"]}


# ------------------------------------------------------- digest (read-only)
def card_marks(store, recs, today, state=None):
    """({stale record id: its verified date}, number of archived records) for the card."""
    st = store.state() if state is None else state
    return ({r["id"]: sc.verified_of(r, st) for r in recs if sc.is_stale(r, st, today)}, len(store.archived()))


def card_repos(store, recs, text, home):
    """[{"id", "blocks", "v", "checked"}] for the card, in registration order: each registered repository that has
    blocks in `recs` — how many, the version most of them have a base at (None when none has) and when the store last
    checked the repository (None when never). A repository whose state cannot be read is listed without the last two;
    what a repository's markers or a state carry is cleaned of control characters before it reaches the card.
    Reads only, and never fails: a card line is not worth a compile."""
    try:
        import ctx_blocks as cb                  # here: both import this module
        import ctx_repos as crp
        repos = crp.load_repos(text, home or os.path.expanduser("~"))
    except Exception:  # noqa: BLE001 — a registration nobody can read must not stop a compile
        return []
    out = []
    for r in repos:
        try:
            n = len(cb.find_regions(recs, r["namespace"])[0])
            if not n:
                continue
            v = checked = None
            try:
                state = cb.load_state(store, r["id"])
                v, checked = cb.base_version(state), state.get("checked")
            except Exception:  # noqa: BLE001 — a state nobody can read or make sense of: listed without a version and a day
                pass
            out.append({"id": cb.clip(r["id"], 60), "blocks": n, "v": cb.clip(v, 40) if v else None,
                        "checked": cb.clip(checked, 40) if isinstance(checked, str) and checked else None})
        except Exception:  # noqa: BLE001 — one repository that cannot be described is left out, the others stay
            continue
    return out


REPOS_LINE = "- **Repos:**"


def refresh_card_repos(store, home, today):
    """Rewrite the card when its line about the repositories is not what the store says now. A check or an adopt
    moves a repository's state without touching a record, so no compile follows and the line would stay as it was.
    Everything else on the card is as `ctx card` makes it; a card that is not there is left for the next compile.
    Returns True when the card was written."""
    if not os.path.isfile(store.card_path):
        return False
    recs = store.load()
    text = cs.compile_records(recs)
    stale, archived = card_marks(store, recs, today)
    card = cs.build_card(recs, text, today, stale=stale, archived=archived, repos=card_repos(store, recs, text, home))
    line = lambda c: next((l for l in c.splitlines() if l.startswith(REPOS_LINE)), None)
    if line(card) == line(_read(store.card_path)):
        return False
    cs.atomic_write(store.card_path, card)
    return True


def checked_by_repo(store_root):
    """{repository id: when it was last checked} from the block states in the store at `store_root`, for the
    SessionStart digest. Read only, and never fails: whatever cannot be read — the folder, a state, the module that
    reads it — gives no date, and the digest falls back to the registration's own. A store with no block state never
    imports it. A state iCloud has evicted is read within the store's time budget (30 s), so the digest calls this
    after the store's facts, on a budget of its own (scripts/session_start.py `_store_summary`)."""
    try:
        store = cs.Store(store_root)
        folder = os.path.join(store.state_dir, "blocks")
        ids = sorted(n[:-5] for n in os.listdir(folder) if n.endswith(".json"))
        if not ids:
            return {}
        import ctx_blocks as cb                  # here: it imports this module
        got = {rid: cb.last_checked(store.root, rid) for rid in ids}
        return {rid: when for rid, when in got.items() if when}
    except Exception:  # noqa: BLE001 — a digest line is not worth the summary
        return {}


def status_summary(context_path, home=None, checked=True):
    """{records, card_lines, pending, conflicts, stale, unassigned, checked, store} for the SessionStart digest
    (`checked`: {repository id: when the store last checked it}, read last — with `checked` False it is {} and the
    caller reads it on its own budget from `store`, the store root, with `checked_by_repo`); {unavailable: root} when
    the store used before cannot be reached; None without a store or on any error. Reads only. The home
    defaults to the one the context file lives in (~/.grow-pm/local-context.md)."""
    try:
        if home is None and os.path.basename(os.path.dirname(os.path.abspath(context_path))) == ".grow-pm":
            home = os.path.dirname(os.path.dirname(os.path.abspath(context_path)))
        text = _read(context_path)
        store = cs.Store(store_root_for(text, home))
        if not store.exists():
            gone = store_unavailable(text, home)
            return {"unavailable": gone} if gone else None
        recs = store.load()
        plan = plan_sync(store, copies_for(context_path, text, home))
        card = _read(store.card_path).count("\n") if os.path.isfile(store.card_path) else 0
        facts = {"records": len(recs), "card_lines": card, "pending": sum(pending(plan).values()),
                 "conflicts": len(plan["conflicts"]) + (1 if plan["suspicious_removal"] else 0) + len(plan["missing"]),
                 "stale": len(sc.stale_ids(recs, store.state(), datetime.date.today().isoformat())),
                 "unassigned": len(cs.unassigned_ids(recs)), "unavailable": None, "store": store.root}
    except Exception:
        return None
    facts["checked"] = checked_by_repo(store.root) if checked else {}   # last, and never the reason the facts are lost
    return facts
