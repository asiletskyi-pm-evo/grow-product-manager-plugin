#!/usr/bin/env python3
"""Grow PM — old backups of local-context.md become snapshots (since v3.21.0): `ctx snapshot import`.

Before the context store, every rewrite left a copy: `~/.grow-pm/backups/**`, `local-context.md.bak*` beside the file.
Those of local-context.md's form become snapshots `~/.grow-pm/snapshots/<their time>-imported/` (kept out of the
rotation), and the originals go to the trash (30 days) — only on `--apply` with the code of the report the user saw.
Anything else (a zip, a section, a yaml, a vault's `_backup_*` folder) is named and left where it is. Semantics:
references/context-protocol.md §8.

- plan(home, context)        what an import would do: {import: [...], known: [...], left: [...]} — reads only
- code(p)                    8 hex of the plan: an apply with another code is refused
- apply(p, home)             write the snapshots, move the originals to the trash; returns the moves and the snapshots
- revert(moves, snaps, home) `ctx undo` of an import: the originals back from the trash, the imported snapshots gone
- IMPORTED_RE                the snapshot names rotate() leaves alone

Stdlib only.
"""
import datetime
import hashlib
import json
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx_store as cs  # noqa: E402

LABEL = "imported"
IMPORTED_RE = re.compile(r"^\d{8}T\d{6}-%s(?:-\d+)?$" % LABEL)
MAX_BYTES = 4 * 1024 * 1024
_FORM = re.compile(r"^## User Profile\b|^> Configurator version", re.M)


def _grow(home):
    return os.path.join(home, ".grow-pm")


def candidates(home, context):
    """[path] of the files to look at: every file under ~/.grow-pm/backups/, and local-context.md.bak* beside the
    canonical copy and beside `context`. Links are not followed."""
    out = []
    bk = os.path.join(_grow(home), "backups")
    if os.path.isdir(bk) and not os.path.islink(bk):
        for root, dirs, files in os.walk(bk):
            dirs[:] = sorted(d for d in dirs if not os.path.islink(os.path.join(root, d)))
            for f in sorted(files):
                p = os.path.join(root, f)
                if not os.path.islink(p):
                    out.append(p)
    seen = {os.path.realpath(x) for x in out}
    for folder in sorted({os.path.realpath(_grow(home)), os.path.dirname(os.path.realpath(context))}):
        try:
            names = sorted(os.listdir(folder))
        except OSError:
            continue
        for n in names:
            p = os.path.join(folder, n)
            if n.startswith("local-context.md.bak") and os.path.isfile(p) and not os.path.islink(p) \
                    and os.path.realpath(p) not in seen:
                seen.add(os.path.realpath(p))
                out.append(p)
    return out


def _form(data):
    """Is this a local-context.md: text whose first line is a `# ` title, with its profile heading or the version line."""
    if len(data) > MAX_BYTES:
        return False
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return False
    first = next((l for l in text.splitlines() if l.strip()), "")
    return first.startswith("# ") and bool(_FORM.search(text))


def _known(home):
    """{sha256 of a compiled copy: snapshot name} over the existing snapshots (their copies/0.md)."""
    root, out = os.path.join(_grow(home), "snapshots"), {}
    try:
        names = sorted(os.listdir(root))
    except OSError:
        return out
    for n in names:
        p = os.path.join(root, n, "copies", "0.md")
        try:
            with open(p, "rb") as f:
                out.setdefault(hashlib.sha256(f.read()).hexdigest(), n)
        except OSError:
            continue
    return out


def plan(home, context):
    known = _known(home)
    out = {"import": [], "known": [], "left": []}
    seen = {}
    for p in candidates(home, context):
        try:
            st = os.lstat(p)
            data = cs.read_bytes(p) if st.st_size <= MAX_BYTES else b""
        except (OSError, cs.StoreError) as e:
            out["left"].append({"path": p, "size": None, "why": "не читається (%s)" % (getattr(e, "strerror", None) or e)})
            continue
        if not _form(data):
            out["left"].append({"path": p, "size": st.st_size, "why": "не схоже на local-context"})
            continue
        sha = hashlib.sha256(data).hexdigest()
        when = datetime.datetime.fromtimestamp(st.st_mtime).strftime("%Y%m%dT%H%M%S")
        row = {"path": p, "size": st.st_size, "sha": sha, "when": when}
        if sha in known or sha in seen:
            out["known"].append(dict(row, snapshot=known.get(sha) or seen[sha]))
        else:
            seen[sha] = "%s-%s" % (when, LABEL)
            out["import"].append(row)
    return out


def code(p):
    rows = sorted([r["path"], r.get("sha")] for r in p["import"] + p["known"])
    return hashlib.sha1(json.dumps(rows).encode("utf-8")).hexdigest()[:8]


def _trash_target(home, path, when):
    root = os.path.join(_grow(home), "trash")
    base = when + "-" + os.path.basename(path).replace(os.sep, "_")
    target, k = os.path.join(root, base + ".md"), 2
    while os.path.exists(target):
        target, k = os.path.join(root, "%s-%d.md" % (base, k)), k + 1
    return target


def apply(p, home, context, now):
    """Write a snapshot per row of `import` (copies/0.md + manifest, mode 0600), then move every original of `import` and
    `known` to the trash. Returns {snapshots: [name], moves: [[original, trash path]]}. A file that changed since the
    plan (another hash) is left, said by the caller through `changed`."""
    root = os.path.join(_grow(home), "snapshots")
    os.makedirs(root, exist_ok=True)
    stamp = now.strftime("%Y%m%dT%H%M%S")
    made, moves, changed = [], [], []
    for row in p["import"] + p["known"]:
        try:
            data = cs.read_bytes(row["path"])
        except (OSError, cs.StoreError):
            changed.append(row["path"])
            continue
        if hashlib.sha256(data).hexdigest() != row["sha"]:
            changed.append(row["path"])
            continue
        if row in p["import"]:
            base = "%s-%s" % (row["when"], LABEL)
            name, k = base, 2
            while os.path.exists(os.path.join(root, name)):
                name, k = "%s-%d" % (base, k), k + 1
            snap = os.path.join(root, name)
            cs.check_target(snap)
            os.makedirs(os.path.join(snap, "copies"))
            target = os.path.join(snap, "copies", "0.md")
            fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "wb") as f:
                f.write(data)
            manifest = {"label": LABEL, "imported": True, "from": row["path"], "sha": row["sha"],
                        "created": datetime.datetime.strptime(row["when"], "%Y%m%dT%H%M%S").astimezone()
                        .isoformat(timespec="seconds"), "store_existed": None,
                        "copies": [{"path": os.path.abspath(context), "file": "copies/0.md", "existed": True}]}
            with open(os.path.join(snap, "manifest.json"), "w", encoding="utf-8") as f:
                json.dump(manifest, f, ensure_ascii=False, indent=1)
            made.append(name)
        target = _trash_target(home, row["path"], stamp)
        cs.check_target(target)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        try:
            os.rename(row["path"], target)
        except OSError:
            shutil.copy2(row["path"], target)
            os.remove(row["path"])
        moves.append([row["path"], target])
    return {"snapshots": made, "moves": moves, "changed": changed}


def revert(moves, snaps, home):
    """The originals back from the trash (only to a free place), the imported snapshots removed. Returns
    (back, kept: [(path, why)])."""
    back, kept = [], []
    for orig, target in moves:
        if not os.path.isfile(target):
            kept.append((orig, "його вже немає в кошику"))
            continue
        if os.path.exists(orig):
            kept.append((orig, "на його місці вже інший файл"))
            continue
        cs.check_target(orig)
        os.makedirs(os.path.dirname(orig), exist_ok=True)
        os.rename(target, orig)
        back.append(orig)
    root = os.path.join(_grow(home), "snapshots")
    for name in snaps:
        if IMPORTED_RE.match(name) and os.path.isdir(os.path.join(root, name)):
            cs.check_target(os.path.join(root, name))
            shutil.rmtree(os.path.join(root, name))
    return back, kept
