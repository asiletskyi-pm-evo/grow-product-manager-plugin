#!/usr/bin/env python3
"""Grow PM — old backups of local-context.md become snapshots (since v3.21.0): `ctx snapshot import`.

Before the context store, every rewrite left a copy: `~/.grow-pm/backups/**`, `~/.grow-pm/local-context.md.bak*`.
Those of local-context.md's form become snapshots `~/.grow-pm/snapshots/<their time>-imported/` (kept out of the
rotation), and the originals go to the trash (30 days) — only on `--apply` with the code of the report the user saw.
Anything else (a zip, a section, a yaml, a file holding what the store never keeps, anything outside ~/.grow-pm — a
vault's `_backup_*` folder, a `.bak` beside a context file elsewhere) is named and left where it is. Semantics:
references/context-protocol.md §8.

- plan(home)                 what an import would do: {import: [...], known: [...], left: [...]} — reads ~/.grow-pm only
- code(p)                    8 hex of the plan: an apply with another code is refused
- planned_moves(p, home, now)  each row's trash path and snapshot name, decided before anything moves — the journal
                             line carries them, so `ctx undo` can take back whatever part of an apply was done
- apply(moves, home, context)  the snapshots, then the moves; a row that fails is said and the rest goes on
- revert(moves, home)        `ctx undo` of an import: an original back from the trash; its snapshot is removed only
                             when the original's own text is back in its place — else the snapshot stays (the text
                             survives in one place at least)
- IMPORTED_RE                the snapshot names rotate() leaves alone

Stdlib only.
"""
import datetime
import errno
import hashlib
import json
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx_never as cn  # noqa: E402
import ctx_store as cs  # noqa: E402

LABEL = "imported"
IMPORTED_RE = re.compile(r"^\d{8}T\d{6}-%s(?:-\d+)?$" % LABEL)
MAX_BYTES = 4 * 1024 * 1024
_PROFILE = re.compile(r"^## User Profile\b", re.M)
_SECOND = re.compile(r"^> Configurator version|^## Onboarding Status\b|^## Organization:|^> Generated", re.M)


def _grow(home):
    return os.path.join(home, ".grow-pm")


def candidates(home):
    """[path] of the files to look at: every file under ~/.grow-pm/backups/ and ~/.grow-pm/local-context.md.bak*.
    Links are not followed, and nothing outside ~/.grow-pm is looked at."""
    out = []
    bk = os.path.join(_grow(home), "backups")
    if os.path.isdir(bk) and not os.path.islink(bk):
        for root, dirs, files in os.walk(bk):
            dirs[:] = sorted(d for d in dirs if not os.path.islink(os.path.join(root, d)))
            for f in sorted(files):
                p = os.path.join(root, f)
                if not os.path.islink(p):
                    out.append(p)
    try:
        names = sorted(os.listdir(_grow(home)))
    except OSError:
        names = []
    for n in names:
        p = os.path.join(_grow(home), n)
        if n.startswith("local-context.md.bak") and os.path.isfile(p) and not os.path.islink(p):
            out.append(p)
    return out


def _form(text):
    """Is this a local-context.md: a `# ` title first, the profile heading, and one more of its marks (the version
    line, the onboarding or an organisation section) — a note that only has a «## User Profile» is not one."""
    first = next((l for l in text.splitlines() if l.strip()), "")
    return first.startswith("# ") and bool(_PROFILE.search(text)) and bool(_SECOND.search(text))


def _known(home):
    """{sha256 of the text: snapshot name} over the imported snapshots only — a regular one rotates away."""
    root, out = os.path.join(_grow(home), "snapshots"), {}
    try:
        names = sorted(n for n in os.listdir(root) if IMPORTED_RE.match(n))
    except OSError:
        return out
    for n in names:
        try:
            with open(os.path.join(root, n, "copies", "0.md"), "rb") as f:
                out.setdefault(hashlib.sha256(f.read()).hexdigest(), n)
        except OSError:
            continue
    return out


_NAMED = re.compile(r"(?<!\d)(20\d{2})-?([01]\d)-?([0-3]\d)(?:[-T_]?([0-2]\d)([0-5]\d)([0-5]\d))?(?!\d)")


def _named_time(path):
    """The time a backup's own name (or its folder's) carries — `….bak.20260825-104702`, `pre-x-2026-10-08/` — else None:
    a copy's mtime is the copy's, the name says when the backup was made."""
    for part in (os.path.basename(path), os.path.basename(os.path.dirname(path))):
        m = _NAMED.search(part)
        if m:
            y, mo, d, hh, mm, ss = m.groups()
            try:
                t = datetime.datetime(int(y), int(mo), int(d), int(hh or 0), int(mm or 0), int(ss or 0))
            except ValueError:
                continue
            return t.strftime("%Y%m%dT%H%M%S")
    return None


def plan(home):
    known = _known(home)
    out = {"import": [], "known": [], "left": []}
    seen = {}
    for p in candidates(home):
        try:
            st = os.lstat(p)
        except OSError as e:
            out["left"].append({"path": p, "size": None, "why": "не читається (%s)" % (e.strerror or e)})
            continue
        if st.st_size > MAX_BYTES:
            out["left"].append({"path": p, "size": st.st_size, "why": "завеликий для local-context"})
            continue
        try:
            data = cs.read_bytes(p)
        except (OSError, cs.StoreError) as e:
            out["left"].append({"path": p, "size": st.st_size,
                                "why": "не читається (%s)" % (getattr(e, "strerror", None) or e)})
            continue
        try:
            text = data.decode("utf-8").lstrip("﻿")
        except UnicodeDecodeError:
            text = None
        if text is None or not _form(text):
            out["left"].append({"path": p, "size": st.st_size, "why": "не схоже на local-context"})
            continue
        kinds = cn.scan(text)
        if kinds:                       # a snapshot never rotates: it must not keep what the store never keeps
            out["left"].append({"path": p, "size": st.st_size,
                                "why": "схоже на %s — не імпортую, прибери сам" % cn._names(kinds)})
            continue
        sha = hashlib.sha256(data).hexdigest()
        when = _named_time(p) or datetime.datetime.fromtimestamp(st.st_mtime).strftime("%Y%m%dT%H%M%S")
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


def planned_moves(p, home, now):
    """[{path, sha, trash, snapshot, made}] — each original's trash path (free now, distinct within the plan) and, for a
    row of `import`, the snapshot it becomes (`made`); for a row of `known`, the imported snapshot holding its text."""
    stamp = now.strftime("%Y%m%dT%H%M%S")
    troot, sroot = os.path.join(_grow(home), "trash"), os.path.join(_grow(home), "snapshots")
    taken_t, taken_s, out, first = set(), set(), [], {}
    for row in p["import"] + p["known"]:
        base = stamp + "-" + os.path.basename(row["path"])
        t, k = os.path.join(troot, base + ".md"), 2
        while os.path.exists(t) or t in taken_t:
            t, k = os.path.join(troot, "%s-%d.md" % (base, k)), k + 1
        taken_t.add(t)
        if row in p["import"]:
            sbase = "%s-%s" % (row["when"], LABEL)
            s, k = sbase, 2
            while os.path.exists(os.path.join(sroot, s)) or s in taken_s:
                s, k = "%s-%d" % (sbase, k), k + 1
            taken_s.add(s)
            first[row["sha"]] = s
            out.append({"path": row["path"], "sha": row["sha"], "trash": t, "snapshot": s, "made": True})
        else:
            out.append({"path": row["path"], "sha": row["sha"], "trash": t,
                        "snapshot": first.get(row["sha"]) or row["snapshot"], "made": False})
    return out


def _sha(path):
    try:
        return hashlib.sha256(cs.read_bytes(path)).hexdigest()
    except (OSError, cs.StoreError):
        return None


def _move(src, dst):
    """Move a file; across volumes copy then remove, and when the remove fails take the copy back — never two copies."""
    try:
        os.rename(src, dst)
        return
    except OSError as e:
        if e.errno != errno.EXDEV:
            raise
    shutil.copy2(src, dst)
    try:
        os.remove(src)
    except OSError:
        try:
            os.remove(dst)
        except OSError:
            pass
        raise


def _write_snapshot(sroot, m, data, context):
    snap = os.path.join(sroot, m["snapshot"])
    cs.check_target(snap)
    os.makedirs(os.path.join(snap, "copies"))
    target = os.path.join(snap, "copies", "0.md")
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    manifest = {"label": LABEL, "imported": True, "from": m["path"], "sha": m["sha"],
                "created": datetime.datetime.strptime(m["snapshot"][:15], "%Y%m%dT%H%M%S").astimezone()
                .isoformat(timespec="seconds"),
                "copies": [{"path": os.path.abspath(context), "file": "copies/0.md", "existed": True}]}
    with open(os.path.join(snap, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    if _sha(target) != m["sha"]:
        raise OSError("знімок %s записано не так" % m["snapshot"])


def apply(moves, home, context):
    """Each move in turn: its snapshot first (a row of `import`), then the original to the trash — never a move whose
    text is in no snapshot. A row whose file changed since the plan, or that fails, is said in `failed` and left; the
    rest goes on. Returns {done: [move], failed: [(path, why)]}."""
    sroot = os.path.join(_grow(home), "snapshots")
    os.makedirs(sroot, exist_ok=True)
    done, failed, written = [], [], set()
    for m in moves:
        try:
            cs.check_target(m["path"])
            data = cs.read_bytes(m["path"])
            if hashlib.sha256(data).hexdigest() != m["sha"]:
                failed.append((m["path"], "змінився після звіту"))
                continue
            if m["made"]:
                _write_snapshot(sroot, m, data, context)
                written.add(m["snapshot"])
            elif m["snapshot"] not in written and not os.path.isfile(os.path.join(sroot, m["snapshot"], "copies", "0.md")):
                failed.append((m["path"], "знімка з його текстом немає — лишаю на місці"))
                continue
            cs.check_target(m["trash"])
            os.makedirs(os.path.dirname(m["trash"]), exist_ok=True)
            if os.path.lexists(m["trash"]):
                raise OSError("у кошику вже є %s" % os.path.basename(m["trash"]))
            _move(m["path"], m["trash"])
            done.append(m)
        except (OSError, cs.StoreError, cs.PathRefused) as e:
            failed.append((m["path"], str(getattr(e, "strerror", None) or e)))
    return {"done": done, "failed": failed}


def revert(moves, home):
    """`ctx undo` of an import. Per move: the original back from the trash when its place is free; a snapshot the
    import made removed only when the original's own text is in its place now — and no other original that shares it
    is still away. Returns (back, kept: [(path, why)])."""
    back, kept = [], []
    sroot = os.path.join(_grow(home), "snapshots")
    for m in moves:
        orig, target = m["path"], m["trash"]
        if os.path.isfile(target) and not os.path.lexists(orig):
            try:
                cs.check_target(orig)
                os.makedirs(os.path.dirname(orig), exist_ok=True)
                _move(target, orig)
                back.append(orig)
            except (OSError, cs.PathRefused) as e:
                kept.append((orig, "не повернуто: %s" % (getattr(e, "strerror", None) or e)))
        elif os.path.isfile(target):
            kept.append((orig, "на його місці інший файл — оригінал лишився в кошику: %s" % target))
    home_again = {}
    for m in moves:
        home_again.setdefault(m.get("snapshot"), []).append(os.path.isfile(m["path"]) and _sha(m["path"]) == m["sha"])
    for m in moves:
        snap = m.get("snapshot")
        if not (m.get("made") and snap and IMPORTED_RE.match(snap) and os.path.isdir(os.path.join(sroot, snap))):
            continue
        if all(home_again.get(snap) or [False]):
            cs.check_target(os.path.join(sroot, snap))
            shutil.rmtree(os.path.join(sroot, snap))
        else:
            kept.append((m["path"], "знімок %s лишився — у ньому текст цього бекапа" % snap))
    return back, kept
