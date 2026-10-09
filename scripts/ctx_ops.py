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
