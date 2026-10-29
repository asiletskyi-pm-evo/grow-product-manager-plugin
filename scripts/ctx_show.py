#!/usr/bin/env python3
"""Grow PM — what the plugin knows about you, and what wants looking after (since v3.21.0): `ctx show`, `ctx health`.

Both read only: no lock, no network, nothing written. The copies outside the snapshots are measured by stat alone,
so a backup iCloud evicted is never brought down; the store itself (records, card, state, registrations) is read as
every `ctx` command reads it. Semantics: references/context-protocol.md §5j. The commands themselves live in ctx.py.

- records(store, today)         one row a record: title, type, who wrote it last, when, verified, stale/invalid, read_by
- memories(store)               what your answers hold: slots, same/not-same, bridges, the inbox
- repos(text, home, store)      one row a registered repository: blocks held, base version, last check, the last sync
- backups(home, context, text, budget)  the copies outside the snapshots: ~/.grow-pm/backups/**, *.bak* beside
                                local-context.md, `_backup_*` folders at a vault's root — path and size, within a budget
- health(...)                   the lines of `ctx health`, each (level, text, fix): ok ✅ · warn ⚠ · act ✋

Stdlib only.
"""
import datetime
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
    import ctx_sources as csrc
    for name, load in (("slots", sl.load_memory), ("entities", ce.load_memory), ("search", ch.load),
                       ("bridges", cbr.load_ledger), ("sources", csrc.load)):
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


def repos(text, home, store, skipped=None):
    import ctx_blocks as cb
    import ctx_repos as crp
    out = []
    for r in crp.load_repos(text, home, skipped=skipped if skipped is not None else []):
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
        facts = copy_facts(home, r["id"]) if r.get("core_from") == "copy" or not (r.get("paths") or r.get("core_root")) else None
        if facts:                                       # since v3.24.0; a row with no copy is as it was
            row["copy"] = facts
        out.append(row)
    return out


COPY_OLD_DAYS = 3                       # a copy of a `sync: daily` repository older than this is a warning


def copy_facts(home, rid):
    """{complete_at, notes, outcome, reason, held_in_row, conflicts, local_only} of the plugin's copy of a core (since
    v3.24.0, ctx_copy), {"error"} for a state that cannot be read, None for no copy. `conflicts`: the files waiting in
    ~/.grow-pm/conflicts/<id>/."""
    import ctx_copy as ccp
    folder = ccp.copy_dir(home, rid)
    if not ccp.SAFE_ID.match(rid or "") or not os.path.isdir(folder) or os.path.islink(folder):
        return None
    try:
        st = ccp.load_state(folder)
    except ccp.CopyError as e:
        return {"error": str(e)}
    if st is None:
        return None
    waiting = 0
    for _, _, files in os.walk(ccp.conflicts_dir(home, rid)):
        waiting += sum(1 for f in files if f.endswith(".md"))
    return {"complete_at": (st.get("complete_at") or "")[:10], "notes": len(st.get("notes") or {}),
            "outcome": st.get("outcome") or "", "reason": st.get("reason") or "", "held_in_row": st.get("held_in_row") or 0,
            "conflicts": waiting, "local_only": ccp.local_only(st)}


def copy_line(c):
    """`копія: <day of the last complete pass> · N нотаток · <last attempt>` (and `· лише локально: N`)."""
    if c.get("error"):
        return "копія: стан не читається — %s" % c["error"]
    return "копія: %s · %d нотаток · %s%s" % (c["complete_at"] or "ще не повна", c["notes"], c["outcome"] or "—",
                                              (" · лише локально: %d" % c["local_only"]) if c["local_only"] else "")


def copy_health(r, today):
    """The health lines of a repository's copy (since v3.24.0): ✋ held twice in a row; ⚠ older than COPY_OLD_DAYS with
    `sync: daily`; ⚠ conflicts waiting; else ✅."""
    c, rid = r.get("copy"), r["id"]
    if not c:
        return []
    if c.get("error"):
        return [(ACT, "копія %s: стан не читається — %s" % (rid, c["error"]), "перенеси теку ~/.grow-pm/cores/%s в кошик і "
                 "зроби копію знову: ctx repo copy %s" % (rid, rid))]
    out = []
    if c["held_in_row"] >= 2:
        out.append((ACT, "копія %s: сервер %d рази поспіль віддав неповний список — копію не оновлено (%s)"
                    % (rid, c["held_in_row"], c["reason"]), "ctx repo copy %s (коли сервер віддасть усе)" % rid))
    try:
        age = (datetime.date.fromisoformat(today[:10]) - datetime.date.fromisoformat(c["complete_at"])).days
    except ValueError:
        age = None
    if r.get("sync") == "daily" and age is not None and age > COPY_OLD_DAYS:
        out.append((WARN, "копія %s від %s — старша за %d дні" % (rid, c["complete_at"], COPY_OLD_DAYS), "ctx repo copy %s" % rid))
    if c["conflicts"]:
        out.append((WARN, "копія %s: конфліктів %d — твоє лишилось, серверне в ~/.grow-pm/conflicts/%s/" % (
            rid, c["conflicts"], rid), "порівняй, перенеси потрібне й прибери теку конфліктів"))
    if not out:
        out.append((OK, "копія %s: від %s · %d нотаток" % (rid, c["complete_at"] or "—", c["notes"]), None))
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
        if time.monotonic() > deadline:
            return total, False
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
            v = json.load(f)
        return v if isinstance(v, dict) else None
    except (OSError, ValueError):
        return None


def snapshots(home):
    root = os.path.join(home, ".grow-pm", "snapshots")
    try:
        names = sorted(n for n in os.listdir(root) if os.path.isdir(os.path.join(root, n)))
    except OSError:
        names = []
    import ctx_backups as cbk
    return [n for n in names if not cbk.IMPORTED_RE.match(n)]


def _hours_since(iso):
    import datetime
    try:
        t = datetime.datetime.fromisoformat(iso)
        now = datetime.datetime.now(t.tzinfo) if t.tzinfo else datetime.datetime.now()
        return (now - t).total_seconds() / 3600.0
    except (TypeError, ValueError):
        return None


_FROM_PLAN = ("change(s) waiting", "conflict:", "stray file", "is missing on disk")


def health(recs, mem, repo_rows, pending, conflicts, missing, stray, warnings, errors, idx, snaps, baks, today,
           unread_regs=(), recheck=None, consolidate=None, overlays=()):
    """The lines of `ctx health`: (level, text, fix). What the sync plan already counts (edits waiting, conflicts,
    stray and missing files) is said once, not again among validate's warnings and errors."""
    out = []
    stale = [r["id"] for r in recs if r["stale"]]
    invalid = [r["id"] for r in recs if r["invalid"]]
    errors = [e for e in errors if not any(x in e for x in _FROM_PLAN)]
    warnings = [w for w in warnings if not any(x in w for x in _FROM_PLAN)]
    if stale:
        out.append((WARN, "застарілі записи: %d (%s)" % (len(stale), ", ".join(stale[:5])), "ctx verify --stale"))
    elif recs:
        out.append((OK, "записів: %d, усі свіжі" % len(recs), None))
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
    for path, why in list(unread_regs)[:5]:
        out.append((ACT, "реєстрацію репозиторію не прочитано: %s — %s" % (os.path.basename(str(path)), why), "ctx repo list"))
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
    if isinstance(recheck, str):                        # since v3.22.0: the records against the connectors
        out.append((ACT, "пам'ять recheck не читається: %s" % recheck, "ctx status"))
    elif recheck is not None:
        if recheck["age"] is None:
            out.append((WARN, "записи ще не звірялись із конекторами", "/context recheck"))
        else:
            out.append((WARN if recheck["age"] > recheck["old"] else OK, "звірка з конекторами: %s" % (
                "сьогодні" if recheck["age"] <= 0 else "%d дн тому" % recheck["age"]),
                "/context recheck" if recheck["age"] > recheck["old"] else None))
        if recheck["noticed"]:
            out.append((WARN, "помічено при звірці: %d — перевірю ще раз через тиждень" % recheck["noticed"], None))
    if isinstance(consolidate, str):
        out.append((ACT, "consolidate не порахувався: %s" % consolidate, "ctx status"))
    elif consolidate:
        out.append((WARN, "consolidate знайде %d (дублі, відносні дати, минулі строки)" % consolidate,
                    "/context consolidate"))
    for o in overlays:                                  # since v3.23.0: your declared corrections to a core
        if o.get("error"):
            out.append((ACT, "оверлей не прочитано: %s" % o["error"], "/context overlay"))
        elif o["held"]:
            n = len(o["held"])
            out.append((ACT, "оверлей %s: %d %s рішення (%s)" % (o["repo"], n, "поправка чекає" if n == 1 else "поправки чекають"
                        if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14 else "поправок чекають", ", ".join(o["held"][:5])),
                        "/context overlay"))
        else:
            out.append((OK, "оверлей %s: поправок діє %d" % (o["repo"], o["applied"]), None))
        if not o.get("error") and o.get("edited"):
            out.append((WARN, "оверлей %s не накладено: твої правки в %s" % (o["repo"], ", ".join(o["edited"][:5])),
                        "ctx provider plan %s" % o["repo"]))
    for name in ("slots", "entities", "search", "bridges", "sources"):
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
        out.extend(copy_health(r, today))
    if idx is None:
        out.append((WARN, "індексу пошуку немає", "ctx index rebuild"))
    else:
        h = _hours_since(idx.get("updated"))
        dl = idx.get("skipped_dataless") or 0
        old = h is not None and h > INDEX_OLD_H
        text = "індекс пошуку: оновлено %s%s" % ((idx.get("updated") or "—")[:16].replace("T", " "),
                                                 ("; не завантажено з iCloud: %d" % dl) if dl else "")
        out.append((WARN if old or dl else OK, text,
                    "ctx index status (оновлює його)" if old else ("ctx index rebuild --download" if dl else None)))
    out.append((OK if snaps else WARN, "знімків: %d%s" % (len(snaps), (", найновіший %s" % snaps[-1]) if snaps else ""),
                None if snaps else "ctx snapshot"))
    for kind, title, fix in (("backups", "копій у ~/.grow-pm/backups", "ctx snapshot import бере копії local-context; "
                                                                         "решту, як zip чи yaml, прибери сам"),
                             ("bak", "копій local-context.md.bak* поруч із файлом",
                              "ctx snapshot import (лише ті, що в ~/.grow-pm)"),
                             ("vault", "тек _backup_* у вейлті", "лише названо — прибери, коли вони більше не потрібні")):
        rows = [b for b in baks if b["kind"] == kind]
        if not rows:
            continue
        sizes = [b["size"] for b in rows if b["size"] is not None]
        partial = any(not b["complete"] for b in rows)
        names = "; ".join("%s (%s)" % (os.path.basename(b["path"]), human(b["size"])) for b in rows[:6]) + \
            ("; +%d" % (len(rows) - 6) if len(rows) > 6 else "")
        out.append((WARN, "%s: %d, %s%s — %s" % (title, len(rows), human(sum(sizes)) if sizes else "не пораховано",
                                                 "+" if partial else "", names), fix))
    return out
