#!/usr/bin/env python3
"""Grow PM — what the plugin knows about you, and what wants looking after (since v3.21.0): `ctx show`, `ctx health`.

Both read only: no lock, no network, nothing written, and a file iCloud has not downloaded is never opened (sizes come
from stat). Semantics: references/context-protocol.md §5j. The commands themselves live in ctx.py.

- records(store, today)         one row a record: title, type, who wrote it last, when, verified, stale/invalid, read_by
- memories(store)               what your answers hold: slots, same/not-same, bridges, the inbox
- repos(text, home, store)      one row a registered repository: blocks held, base version, last check, the last sync
- backups(home, context, text, budget)  the copies outside the snapshots: ~/.grow-pm/backups/**, *.bak* beside
                                local-context.md, `_backup_*` folders at a vault's root — path and size, within a budget
- health(...)                   the lines of `ctx health`, each (level, text, fix): ok ✅ · warn ⚠ · act ✋

Stdlib only.
"""
import glob
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx_common as cc  # noqa: E402
import ctx_inbox as ci_  # noqa: E402
import ctx_schema as sc  # noqa: E402
import ctx_store as cs  # noqa: E402

OK, WARN, ACT = "ok", "warn", "act"
MARK = {OK: "✅", WARN: "⚠", ACT: "✋"}
BACKUP_BUDGET_S = 2.0
INDEX_OLD_H = 36


def records(store, today):
    state = store.state()
    out = []
    for r in store.load():
        stale = sc.is_stale(r, state, today)
        out.append({"id": r["id"], "type": r["type"], "title": r["title"], "source": r.get("source") or "—",
                    "modified": (r.get("modified") or "")[:10] or "—", "verified": sc.verified_of(r, state) or "—",
                    "ttl": sc.ttl_of(r), "stale": stale, "invalid": cs.has_status_region(r["body"]),
                    "read_by": r.get("read_by")})
    return out


def _count(mem):
    return sum(len(v) for k, v in (mem or {}).items() if k != "schema" and isinstance(v, (list, dict)))


def memories(store, today):
    """{name: count or the error text} — one memory that does not read is said, the others still counted."""
    import ctx_bridges as cbr
    import ctx_entity as ce
    import ctx_hints as ch
    import ctx_slots as sl
    out = {}
    for name, load in (("slots", sl.load_memory), ("entities", ce.load_memory), ("search", ch.load),
                       ("bridges", cbr.load_ledger)):
        try:
            mem = load(store)
            out[name] = len(mem.get("written") or []) if name == "bridges" else _count(mem)
        except cs.StoreError as e:
            out[name] = str(e)
    try:
        out["inbox"] = ci_.counts(ci_.load(store), today)
    except cs.StoreError as e:
        out["inbox"] = str(e)
    return out


def repos(text, home, store):
    import ctx_blocks as cb
    import ctx_repos as crp
    out = []
    for r in crp.load_repos(text, home, skipped=[]):
        row = {"id": r["id"], "kind": r.get("kind"), "sync": r.get("sync"), "paused": r.get("status") == "paused",
               "blocks": None, "version": None, "checked": None, "outcome": None, "error": None}
        if store.exists():
            try:
                st = cb.load_state(store, r["id"])
                row.update(blocks=cb.based_count(st), version=cb.base_version(st))
                ch = st.get("checked")
                row["checked"] = ch[:10] if isinstance(ch, str) and ch else None
                res = st.get("sync_result")
                row["outcome"] = res.get("outcome") if isinstance(res, dict) else None
            except cs.StoreError as e:
                row["error"] = str(e)
        out.append(row)
    return out


def _size(path, deadline):
    """(bytes, complete) of a file or a folder by stat alone; a folder walked until `deadline`."""
    try:
        if not os.path.isdir(path) or os.path.islink(path):
            return os.lstat(path).st_size, True
    except OSError:
        return 0, True
    total = 0
    for root, dirs, files in os.walk(path):
        for f in files:
            try:
                total += os.lstat(os.path.join(root, f)).st_size
            except OSError:
                pass
            if time.monotonic() > deadline:
                return total, False
    return total, True


def backups(home, context, text, budget=BACKUP_BUDGET_S):
    """[{path, size, complete, kind}] — the copies outside the snapshots, trash and archive (concept §5.2 F, plan R6)."""
    deadline = time.monotonic() + budget
    found = []
    gp = os.path.join(home, ".grow-pm")
    bk = os.path.join(gp, "backups")
    if os.path.isdir(bk):
        for name in sorted(os.listdir(bk)):
            found.append((os.path.join(bk, name), "backups"))
    for folder in sorted({os.path.realpath(gp), os.path.dirname(os.path.realpath(context))}):
        for p in sorted(glob.glob(os.path.join(glob.escape(folder), "local-context.md.bak*"))):
            found.append((p, "bak"))
    for root, _folder in cc.vault_entries(text):
        root = os.path.expanduser(root)
        if root and os.path.isdir(root):
            try:
                names = sorted(os.listdir(root))
            except OSError:
                continue
            for name in names:
                if name.startswith("_backup_") and os.path.isdir(os.path.join(root, name)):
                    found.append((os.path.join(root, name), "vault"))
    out, seen = [], set()
    for p, kind in found:
        if os.path.realpath(p) in seen:
            continue
        seen.add(os.path.realpath(p))
        size, complete = _size(p, deadline) if time.monotonic() <= deadline else (None, False)
        out.append({"path": p, "kind": kind, "size": size, "complete": complete})
    return out


def human(n):
    if n is None:
        return "не пораховано"
    for unit in ("Б", "КБ", "МБ", "ГБ"):
        if n < 1024 or unit == "ГБ":
            return ("%d %s" % (n, unit)) if unit == "Б" else ("%.1f %s" % (n, unit))
        n /= 1024.0


def index_state(home):
    import json
    p = os.path.join(home, ".grow-pm", "index", "index.json")
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def snapshots(home):
    root = os.path.join(home, ".grow-pm", "snapshots")
    try:
        names = sorted(n for n in os.listdir(root) if os.path.isdir(os.path.join(root, n)))
    except OSError:
        names = []
    return names


def _hours_since(iso):
    import datetime
    try:
        t = datetime.datetime.fromisoformat(iso)
        now = datetime.datetime.now(t.tzinfo) if t.tzinfo else datetime.datetime.now()
        return (now - t).total_seconds() / 3600.0
    except (TypeError, ValueError):
        return None


def health(recs, mem, repo_rows, pending, conflicts, missing, stray, warnings, errors, idx, snaps, baks, today):
    """The lines of `ctx health`: (level, text, fix)."""
    out = []
    stale = [r["id"] for r in recs if r["stale"]]
    invalid = [r["id"] for r in recs if r["invalid"]]
    out.append((WARN, "застарілі записи: %d (%s)" % (len(stale), ", ".join(stale[:5])), "ctx verify --stale")
               if stale else (OK, "записів: %d, усі свіжі" % len(recs), None))
    if invalid:
        out.append((WARN, "неактуальні записи: %d (%s)" % (len(invalid), ", ".join(invalid[:5])),
                    "ctx archive <id> або ctx restore <id>"))
    if errors:
        out.append((ACT, "помилки сховища: %d — %s" % (len(errors), errors[0]), "ctx validate"))
    if pending or conflicts or missing:
        bits = ([("правок чекає імпорту: %d" % pending)] if pending else []) + \
               ([("конфліктів: %d" % conflicts)] if conflicts else []) + \
               ([("файлів записів немає: %d" % missing)] if missing else [])
        out.append((ACT if conflicts or missing else WARN, ", ".join(bits), "ctx sync"))
    secret = [w for w in warnings if "таке не варто тримати" in w]
    if secret:
        out.append((ACT, "у записах схоже на секрет чи ідентифікатор: %s" % ", ".join(w.split(":")[0] for w in secret),
                    "прибери це з запису (ctx validate каже вид)"))
    other = [w for w in warnings if w not in secret and not w.startswith("stale:")]
    if other:
        out.append((WARN, "попереджень validate: %d" % len(other), "ctx validate"))
    if stray:
        out.append((WARN, "сторонні файли у сховищі: %d" % stray, "ctx status"))
    ib = mem.get("inbox")
    if isinstance(ib, str):
        out.append((ACT, "скринька не читається: %s" % ib, "ctx inbox list"))
    elif ib and ib["entries"]:
        out.append((ACT if ib["urgent"] else WARN, "у скриньці %d%s%s" % (
            ib["entries"], (", термінових %d" % ib["urgent"]) if ib["urgent"] else "",
            (", старших за %d днів: %d" % (ci_.OLD_DAYS, ib["old"])) if ib["old"] else ""), "/context inbox"))
    else:
        out.append((OK, "скринька порожня", None))
    for name in ("slots", "entities", "search", "bridges"):
        if isinstance(mem.get(name), str):
            out.append((ACT, "пам'ять %s не читається: %s" % (name, mem[name]), "ctx status"))
    for r in repo_rows:
        if r["error"]:
            out.append((ACT, "репозиторій %s: стан не читається — %s" % (r["id"], r["error"]), "ctx repo list"))
        elif r["paused"]:
            out.append((WARN, "репозиторій %s призупинено" % r["id"], None))
        elif r["outcome"] in ("unreachable", "broken", "held", "import-conflict", "timeout", "error"):
            out.append((WARN, "репозиторій %s: останній синк — %s (перевірено %s)" % (r["id"], r["outcome"],
                        r["checked"] or "—"), "ctx provider plan %s" % r["id"]))
        else:
            out.append((OK, "репозиторій %s: перевірено %s" % (r["id"], r["checked"] or "—"), None))
    if idx is None:
        out.append((WARN, "індексу пошуку немає", "ctx index rebuild"))
    else:
        h = _hours_since(idx.get("updated"))
        dl = idx.get("skipped_dataless") or 0
        old = h is not None and h > INDEX_OLD_H
        text = "індекс пошуку: оновлено %s%s" % ((idx.get("updated") or "—")[:16].replace("T", " "),
                                                 ("; не завантажено з iCloud: %d" % dl) if dl else "")
        out.append((WARN if old or dl else OK, text,
                    "ctx index status" if old else ("ctx index rebuild --download" if dl else None)))
    out.append((OK if snaps else WARN, "знімків: %d%s" % (len(snaps), (", найновіший %s" % snaps[-1]) if snaps else ""),
                None if snaps else "ctx snapshot"))
    if baks:
        out.append((WARN, "копій поза знімками: %d — %s" % (len(baks), "; ".join(
            "%s (%s%s)" % (b["path"], human(b["size"]), "" if b["complete"] or b["size"] is None else "+")
            for b in baks[:8])), "ctx snapshot import (копії форми local-context; теки вейлта лише названо)"))
    return out
